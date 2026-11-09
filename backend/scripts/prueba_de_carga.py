"""**Cuántos agricultores aguanta esto hoy**, medido y no inventado.

El programa no se puede juzgar en el portátil de uno: se juzga con varios agricultores
entrando a la vez, que es lo que pasa un lunes por la mañana en campaña. Esto levanta un
uvicorn **de verdad**, con una base de datos **temporal** (que se borra al terminar) y
siembra por la API pública varios agricultores de prueba con su finca, sus tierras y su
producto. Después repite el recorrido real de la aplicación —entrar con la clave (PBKDF2),
listar las tierras, abrir una ficha, apuntar un tratamiento y consultar el cuaderno— con
cada vez más usuarios a la vez, y mide:

  · peticiones, errores y peticiones por segundo de cada escalón;
  · la latencia p50, p95 y p99 de cada petición;
  · **la rodilla**: el escalón en el que el p95 se dispara o empiezan los errores.

## Lo que este guion NO hace, y se dice para que no se confunda

  · **No sale a internet.** Ni SIGPAC, ni IGN, ni OCR, ni correo. Todo es local.
  · **No toca datos reales ni la base de desarrollo.** Si no se le da `--base`, se levanta
    su propio servidor con `CUEDIGITAL_DATABASE_URL` en una carpeta temporal y se borra
    entera al acabar (base, adjuntos y registro del servidor).
  · **No mide la red móvil, ni el disco, ni el navegador, ni la subida de fotos.** Eso son
    otras pruebas y está dicho en `docs/PRUEBAS_DE_CARGA.md`.

## Uso

    ..\\.venv\\Scripts\\python.exe scripts/prueba_de_carga.py
    ..\\.venv\\Scripts\\python.exe scripts/prueba_de_carga.py --escalones 1,5,10,25
    ..\\.venv\\Scripts\\python.exe scripts/prueba_de_carga.py --escalones 1,5,10 --json
    ..\\.venv\\Scripts\\python.exe scripts/prueba_de_carga.py --base http://127.0.0.1:8010 --sin-servidor

Códigos de salida: **0** si aguanta todos los escalones pedidos, **1** si aparece la rodilla
o hay errores, y **2** si no hay servidor o la preparación no se ha podido hacer (no se
rompe: se dice qué pasa y qué hacer).
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import ctypes
import datetime as dt
import json
import os
import pathlib
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter
from typing import Any, Sequence

import httpx

# --------------------------------------------------------------------------
# Dónde estamos y con qué se arranca el servidor
# --------------------------------------------------------------------------

RUTA_DEL_GUION = pathlib.Path(__file__).resolve()
BACKEND = RUTA_DEL_GUION.parents[1]
RAIZ = RUTA_DEL_GUION.parents[2]
PYTHON = RAIZ / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():  # pragma: no cover - en Linux o con otro entorno
    PYTHON = pathlib.Path(sys.executable)

DIRECCION_POR_DEFECTO = "http://127.0.0.1:8000"

# Los escalones que pide el encargo por defecto. Son los que se midieron el 09/11/2026.
ESCALONES_POR_DEFECTO = "1,5,10,25,50"

# Cuántas tierras tiene cada agricultor de prueba. Una finca de verdad tiene decenas (la
# de ejemplo del proyecto tiene 64); con 10 el montaje es rápido y el recorrido ya lee una
# lista con contenido. El día que se quiera medir con 64, `--tierras-por-usuario 64`.
TIERRAS_POR_USUARIO_POR_DEFECTO = 10

# **El servidor de pruebas deriva la clave 100.000 veces por defecto, no 240.000.** Con
# 240.000 el alta de 50 cuentas tarda más y la prueba se hace más pesada; 100.000 es el
# mínimo que el programa acepta en un entorno de pruebas (`security.ITERACIONES_MINIMAS_DE_VERDAD`).
#
# **Pero eso hace que la latencia salga optimista**: en producción la clave se deriva
# 240.000 veces y cuesta ~2,9 veces más (medido: 98 ms frente a 280 ms). Por eso está
# `--iteraciones-pbkdf2 240000`, que mide con la configuración real; las dos cosas se
# cuentan en `docs/PRUEBAS_DE_CARGA.md`.
ITERACIONES_DEL_SERVIDOR_DE_PRUEBAS = 100_000
ITERACIONES_DE_PRODUCCION = 240_000

# Cuándo se dice que un escalón ya es la rodilla.
#
# No hay un número mágico: se combinan tres señales, y la primera que salte manda.
#
# **El umbral absoluto es de un segundo, no de dos.** Lo medido el 09/11/2026: con 50
# usuarios a la vez el p95 llegó a 1.337 ms creciendo «solo» un 75 % respecto de los 25
# (762 ms), así que la subida relativa no llegaba al factor de 2,5 y el guion decía que
# aguantaba. Un agricultor de pie en una parcela, con la cobertura del campo y el móvil en
# una mano, no espera un segundo a que se abra la lista: el segundo de aquí es **antes** de
# sumar la red móvil. A partir de un segundo de p95 en el servidor, se llama rodilla.
UMBRAL_P95_MS = 1000.0
P95_MINIMO_PARA_RODILLA_MS = 300.0  # por debajo de esto, el ruido de una máquina no es una rodilla
CRECIMIENTO_DE_RODILLA = 2.5  # el p95 se multiplica por 2,5 respecto del escalón anterior

# Códigos de salida. Que no sean un 0/1 a secas es a propósito: «no se ha podido medir» no
# es lo mismo que «no aguanta», y quien mire el código de salida tiene que poder distinguirlo.
CODIGO_AGUANTA = 0
CODIGO_NO_AGUANTA = 1
CODIGO_SIN_SERVIDOR = 2

# Un recorrido son cinco peticiones: entrar, listar las tierras, abrir una ficha, apuntar un
# tratamiento y consultar el cuaderno. Es el camino que hace el agricultor de verdad.
PETICIONES_DEL_RECORRIDO = 5

FECHA_DE_HOY = dt.date.today().isoformat()

# Las peticiones se cortan a los 20 s: una petición que tarda más que eso ya no es una
# medida útil y no queremos que un servidor saturado deje la prueba colgada media hora.
ESPERA_POR_PETICION_SEGUNDOS = 20.0


# --------------------------------------------------------------------------
# Funciones puras (las que prueban los tests, sin red y sin levantar nada)
# --------------------------------------------------------------------------


def percentil(valores: Sequence[float], p: float) -> float:
    """El percentil `p` (0..100) de una lista de medidas, por interpolación lineal.

    Se interpola en vez de coger el valor más cercano porque con pocas medidas (una
    petición por usuario) el «más cercano» se queda siempre en uno de los extremos y el
    p95 diría lo mismo que el máximo. Con interpolación, una lista de 1 a 100 da
    exactamente 50,5 / 95,05 / 99,01, que es lo que se puede comprobar a mano.
    """
    if not valores:
        raise ValueError("No hay medidas para calcular un percentil.")
    if not 0 <= p <= 100:
        raise ValueError("El percentil tiene que estar entre 0 y 100.")
    ordenados = sorted(float(valor) for valor in valores)
    if len(ordenados) == 1:
        return ordenados[0]
    posicion = (len(ordenados) - 1) * (p / 100.0)
    inferior = int(posicion)
    superior = min(inferior + 1, len(ordenados) - 1)
    peso = posicion - inferior
    return ordenados[inferior] + (ordenados[superior] - ordenados[inferior]) * peso


def percentiles(valores: Sequence[float]) -> dict[str, float]:
    """Los tres percentiles que se enseñan, redondeados a una décima de milisegundo."""
    return {
        "p50": round(percentil(valores, 50), 1),
        "p95": round(percentil(valores, 95), 1),
        "p99": round(percentil(valores, 99), 1),
    }


def encontrar_la_rodilla(mediciones: Sequence[dict]) -> int | None:
    """El índice del primer escalón que **ya no aguanta**, o `None` si aguantan todos.

    Tres señales, y la primera que salte manda:
      1. **errores**: cualquier petición que no haya ido bien;
      2. **p95 absoluto**: más de `UMBRAL_P95_MS`;
      3. **p95 relativo**: multiplicarse por `CRECIMIENTO_DE_RODILLA` respecto del escalón
         anterior, y pasar de `P95_MINIMO_PARA_RODILLA_MS` para no confundir el ruido de
         una máquina ociosa con una rodilla.
    """
    anterior: dict | None = None
    for indice, medicion in enumerate(mediciones):
        if int(medicion["errores"]) > 0:
            return indice
        p95 = float(medicion["p95_ms"])
        if p95 >= UMBRAL_P95_MS:
            return indice
        if (
            anterior is not None
            and p95 >= P95_MINIMO_PARA_RODILLA_MS
            and p95 >= CRECIMIENTO_DE_RODILLA * float(anterior["p95_ms"])
        ):
            return indice
        anterior = medicion
    return None


def motivo_de_la_rodilla(mediciones: Sequence[dict], indice: int | None) -> str:
    """Por qué se ha dicho que ese escalón es la rodilla, en una frase."""
    if indice is None:
        return ""
    medicion = mediciones[indice]
    usuarios = medicion["usuarios"]
    if int(medicion["errores"]) > 0:
        return (
            f"en {usuarios} usuarios ha habido {medicion['errores']} peticiones con error "
            f"de {medicion['peticiones']}"
        )
    p95 = float(medicion["p95_ms"])
    if p95 >= UMBRAL_P95_MS:
        return f"en {usuarios} usuarios el p95 ({p95:.0f} ms) pasa del umbral de {UMBRAL_P95_MS:.0f} ms"
    anterior = mediciones[indice - 1] if indice > 0 else None
    if anterior is not None:
        p95_anterior = float(anterior["p95_ms"])
        factor = p95 / p95_anterior if p95_anterior else 0.0
        return (
            f"en {usuarios} usuarios el p95 ({p95:.0f} ms) se multiplica por {factor:.1f} "
            f"respecto de los {anterior['usuarios']} usuarios ({p95_anterior:.0f} ms)"
        )
    return f"en {usuarios} usuarios"


def resumir_el_veredicto(mediciones: Sequence[dict], escalones: Sequence[int]) -> dict:
    """Si aguanta los escalones pedidos, por qué, y con qué código se sale.

    «Aguanta» significa las dos cosas: que se han probado **todos** los escalones pedidos y
    que en ninguno ha aparecido la rodilla. Si la prueba se corta en la rodilla, los
    escalones de arriba no se han probado, pero el veredicto ya es que no aguanta.
    """
    indice = encontrar_la_rodilla(mediciones)
    probados = [medicion["usuarios"] for medicion in mediciones]
    faltan = [escalon for escalon in escalones if escalon not in probados]
    if indice is None and faltan:
        aguanta = False
        motivo = f"no se han llegado a probar los escalones {', '.join(map(str, faltan))}"
    elif indice is None:
        aguanta = True
        motivo = (
            "no ha aparecido la rodilla: el p95 se mantiene y no ha habido errores "
            "en los escalones probados"
        )
    else:
        aguanta = False
        motivo = motivo_de_la_rodilla(mediciones, indice)
    return {
        "aguanta": aguanta,
        "codigo": CODIGO_AGUANTA if aguanta else CODIGO_NO_AGUANTA,
        "rodilla_usuarios": None if indice is None else mediciones[indice]["usuarios"],
        "motivo": motivo,
        "escalones_probados": probados,
        "escalones_que_faltan": faltan,
    }


def formatear_la_tabla(mediciones: Sequence[dict], veredicto: dict) -> str:
    """La tabla en castellano que se enseña al terminar, con la rodilla marcada."""
    lineas = [
        "  Usuarios  Peticiones  Errores    p50 ms    p95 ms    p99 ms   Peticiones/s",
        "  --------  ----------  -------    ------    ------    ------   ------------",
    ]
    for medicion in mediciones:
        marca = "   <-- rodilla" if medicion["usuarios"] == veredicto.get("rodilla_usuarios") else ""
        lineas.append(
            f"  {medicion['usuarios']:>8}  {medicion['peticiones']:>10}  "
            f"{medicion['errores']:>7}  {medicion['p50_ms']:>8.1f}  "
            f"{medicion['p95_ms']:>8.1f}  {medicion['p99_ms']:>8.1f}  "
            f"{medicion['peticiones_por_segundo']:>12.1f}{marca}"
        )
    lineas.append("")
    if veredicto.get("rodilla_usuarios") is None:
        lineas.append("Rodilla: no ha aparecido en los escalones probados.")
    else:
        lineas.append(
            f"Rodilla: a partir de {veredicto['rodilla_usuarios']} usuarios "
            f"({veredicto['motivo']})."
        )
    if veredicto["aguanta"]:
        lineas.append(
            "Veredicto: AGUANTA los escalones probados, sin errores y con el p95 a raya."
        )
    else:
        lineas.append(f"Veredicto: NO aguanta. {veredicto['motivo'].capitalize()}.")
    return "\n".join(lineas)


def leer_los_escalones(texto: str) -> tuple[int, ...]:
    """`"1,5,10,25"` → `(1, 5, 10, 25)`. Se rechaza lo que no sea una subida de verdad."""
    escalones: list[int] = []
    for trozo in str(texto).split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        try:
            escalon = int(trozo)
        except ValueError:
            raise ValueError(f"«{trozo}» no es un número de usuarios.") from None
        if escalon < 1:
            raise ValueError("Los escalones tienen que ser de uno o más usuarios.")
        escalones.append(escalon)
    if not escalones:
        raise ValueError("No has dicho ningún escalón de usuarios.")
    if len(set(escalones)) != len(escalones):
        raise ValueError("Hay escalones repetidos: cada uno tiene que ser distinto.")
    if escalones != sorted(escalones):
        raise ValueError("Los escalones tienen que ir de menos a más usuarios.")
    return tuple(escalones)


def normalizar_direccion(texto: str) -> str:
    """`"127.0.0.1:8010/"` → `"http://127.0.0.1:8010"`."""
    limpio = str(texto).strip().rstrip("/")
    if not limpio:
        raise ValueError("La dirección del servidor está vacía.")
    if not limpio.startswith(("http://", "https://")):
        limpio = f"http://{limpio}"
    return limpio


def entorno_del_servidor_temporal(
    carpeta: pathlib.Path, *, iteraciones: int = ITERACIONES_DEL_SERVIDOR_DE_PRUEBAS
) -> dict[str, str]:
    """El entorno con el que arranca el uvicorn propio: todo dentro de `carpeta`.

    Es una función pura a propósito (solo lee `os.environ` para copiarlo): así se puede
    comprobar en un test que **la base, los adjuntos y el secreto son de la carpeta
    temporal** y que no se hereda ninguna dirección de la base de desarrollo.
    """
    entorno = dict(os.environ)
    carpeta = pathlib.Path(carpeta)
    # Se quitan las variables que podrían apuntar a la base del agricultor o a la suite.
    for variable in ("CUEDIGITAL_SUITE_SOBRE",):
        entorno.pop(variable, None)
    entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{(carpeta / 'carga.db').as_posix()}"
    entorno["CUEDIGITAL_ADJUNTOS"] = str(carpeta / "adjuntos")
    entorno["CUEDIGITAL_SECRETO"] = f"carga-{uuid.uuid4().hex}"
    entorno["CUEDIGITAL_ENTORNO"] = "pruebas"
    entorno["CUEDIGITAL_ITERACIONES_PBKDF2"] = str(int(iteraciones))
    return entorno


def mensaje_sin_servidor(direccion: str, detalle: str = "") -> str:
    """Qué se le dice a quien lanza esto cuando no hay servidor. Se prueba en los tests."""
    lineas = [
        f"No hay ningún servidor escuchando en {direccion}.",
        "No se ha medido nada y no se ha tocado ningún dato.",
        "Para que esto levante su propio uvicorn con una base temporal: quita --sin-servidor "
        "y no pases --base.",
        "Para usar uno que ya esté en marcha, arranca uvicorn en otra ventana y pásale su "
        "dirección con --base.",
    ]
    if detalle:
        lineas.append(f"Detalle: {detalle}")
    return "\n".join(lineas)


def informacion_de_la_maquina() -> dict:
    """Lo que hace falta para que una medida se pueda repetir: máquina, núcleos y memoria.

    Se saca con la biblioteca estándar: `platform`, `os.cpu_count()`, el registro de Windows
    para el nombre del procesador y `GlobalMemoryStatusEx` para la memoria. Si algo no se
    puede leer, se queda en `None`; no se inventa.
    """
    datos: dict[str, Any] = {
        "sistema": platform.platform(),
        "python": platform.python_version(),
        "nucleos_logicos": os.cpu_count(),
        "procesador": platform.processor() or None,
        "ram_gb": None,
    }
    try:  # Windows: el nombre comercial del procesador
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as clave:
            datos["procesador"] = winreg.QueryValueEx(clave, "ProcessorNameString")[0].strip()
    except Exception:  # noqa: BLE001 - si no se puede leer, se queda el de platform
        pass
    try:  # Windows: memoria física total
        class _EstadoDeMemoria(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        estado = _EstadoDeMemoria()
        estado.dwLength = ctypes.sizeof(_EstadoDeMemoria)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            datos["ram_gb"] = round(estado.ullTotalPhys / (1024**3), 1)
    except Exception:  # noqa: BLE001 - fuera de Windows no existe
        pass
    return datos


# --------------------------------------------------------------------------
# El servidor temporal (o el que ya haya)
# --------------------------------------------------------------------------


class NoHayServidor(RuntimeError):
    """No hay servidor, o el que se ha intentado levantar no ha contestado."""


def un_puerto_libre() -> int:
    """Un puerto que el sistema acaba de dar por libre (se cierra antes de usarlo)."""
    with socket.socket() as hueco:
        hueco.bind(("127.0.0.1", 0))
        return int(hueco.getsockname()[1])


def el_puerto_esta_abierto(
    puerto: int, espera: float = 5.0, intervalo: float = 0.2
) -> bool:
    """Si **sigue** habiendo algo escuchando en ese puerto cuando se acaba de apagar.

    Se espera a que se cierre, no se mira una sola vez: en Windows el socket tarda un
    instante en soltarse después de terminar el proceso, y mirar una sola vez hacía saltar
    un aviso falso («sigue escuchando») que no era verdad. Devuelve `True` solo si, agotada
    la espera, el puerto sigue abierto.
    """
    final = time.monotonic() + max(0.0, float(espera))
    while True:
        with socket.socket() as sonda:
            sonda.settimeout(0.5)
            abierto = sonda.connect_ex(("127.0.0.1", puerto)) == 0
        if not abierto:
            return False
        if time.monotonic() >= final:
            return True
        time.sleep(intervalo)


def contestan_en(direccion: str) -> tuple[bool, str]:
    """Si hay un servidor que contesta a `/health`, y el detalle de lo que ha pasado."""
    try:
        with httpx.Client(timeout=5.0) as cliente:
            respuesta = cliente.get(f"{direccion}/health")
        if respuesta.status_code == 200:
            return True, ""
        return False, f"/health ha contestado {respuesta.status_code}"
    except httpx.HTTPError as fallo:
        return False, f"{type(fallo).__name__}: {fallo}"


def _cola_del_registro(ruta: pathlib.Path, lineas: int = 25) -> str:
    """Las últimas líneas del registro del servidor, para poder decir por qué no arrancó."""
    try:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(texto.splitlines()[-lineas:])


class ServidorTemporal:
    """Un uvicorn con su base, sus adjuntos y su registro, todo dentro de una carpeta temporal."""

    def __init__(self, carpeta: pathlib.Path, *, iteraciones: int = ITERACIONES_DEL_SERVIDOR_DE_PRUEBAS):
        self.carpeta = pathlib.Path(carpeta)
        self.iteraciones = int(iteraciones)
        self.puerto = un_puerto_libre()
        self.direccion = f"http://127.0.0.1:{self.puerto}"
        self.proceso: subprocess.Popen | None = None
        self.ruta_del_registro = self.carpeta / "uvicorn.log"
        self._registro = None

    def arrancar(self, espera_maxima: float = 120.0) -> str:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        entorno = entorno_del_servidor_temporal(self.carpeta, iteraciones=self.iteraciones)
        self._registro = open(self.ruta_del_registro, "wb")  # noqa: SIM115 - vive lo que el servidor
        self.proceso = subprocess.Popen(  # noqa: S603 - es el intérprete del propio proyecto
            [
                str(PYTHON),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.puerto),
                "--log-level",
                "warning",
            ],
            cwd=str(BACKEND),
            env=entorno,
            stdout=self._registro,
            stderr=subprocess.STDOUT,
        )
        final = time.monotonic() + espera_maxima
        with httpx.Client(timeout=3.0) as cliente:
            while time.monotonic() < final:
                if self.proceso.poll() is not None:
                    detalle = _cola_del_registro(self.ruta_del_registro)
                    self.parar()
                    raise NoHayServidor(
                        "el uvicorn propio se ha parado antes de contestar"
                        + (f". Registro:\n{detalle}" if detalle else "")
                    )
                try:
                    if cliente.get(f"{self.direccion}/health").status_code == 200:
                        return self.direccion
                except httpx.HTTPError:
                    pass
                time.sleep(0.4)
        detalle = _cola_del_registro(self.ruta_del_registro)
        self.parar()
        raise NoHayServidor(
            f"el uvicorn propio no ha contestado en {espera_maxima:.0f} s"
            + (f". Registro:\n{detalle}" if detalle else "")
        )

    def parar(self) -> None:
        """Apaga el servidor y **comprueba que el puerto se ha cerrado de verdad**."""
        if self.proceso is not None and self.proceso.poll() is None:
            self.proceso.terminate()
            try:
                self.proceso.wait(timeout=15)
            except subprocess.TimeoutExpired:  # pragma: no cover - un cuelgue raro de uvicorn
                self.proceso.kill()
                try:
                    self.proceso.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
        if self._registro is not None:
            try:
                self._registro.close()
            finally:
                self._registro = None
        if el_puerto_esta_abierto(self.puerto):
            raise NoHayServidor(
                f"el servidor de pruebas sigue escuchando en el puerto {self.puerto} "
                "después de intentar apagarlo"
            )


def borrar_carpeta(carpeta: pathlib.Path) -> bool:
    """Borra la carpeta temporal, con reintentos: en Windows un fichero tarda en soltarse."""
    carpeta = pathlib.Path(carpeta)
    for intento in range(20):
        shutil.rmtree(carpeta, ignore_errors=True)
        if not carpeta.exists():
            return True
        time.sleep(0.25)
    return not carpeta.exists()


@contextlib.contextmanager
def carpeta_temporal_de_la_carga():
    """**Todo lo que escribe esta prueba vive aquí y se borra al salir.**"""
    carpeta = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital-carga-"))
    try:
        yield carpeta
    finally:
        borrar_carpeta(carpeta)


# --------------------------------------------------------------------------
# Preparar los agricultores de prueba (por la API pública, sin retocar la base)
# --------------------------------------------------------------------------


class ErrorDePreparacion(RuntimeError):
    """No se han podido sembrar los agricultores de prueba. No se mide nada."""


def _exigir(respuesta: httpx.Response, que: str) -> httpx.Response:
    if respuesta.status_code >= 400:
        raise ErrorDePreparacion(
            f"{que}: HTTP {respuesta.status_code} — {respuesta.text[:400]}"
        )
    return respuesta


def preparar_los_usuarios(
    cliente: httpx.Client,
    cuantos: int,
    *,
    tierras_por_usuario: int,
    fecha: str = FECHA_DE_HOY,
) -> tuple[list[dict], float]:
    """Da de alta `cuantos` agricultores con su finca, sus tierras y su producto.

    Se hace **por la API pública**, con el registro real: si el alta de una cuenta se rompe,
    esta prueba lo dice en vez de esconderlo sembrando la base por detrás. Devuelve los
    datos que necesita el recorrido y lo que ha tardado la preparación (que ya es un dato:
    el registro lleva PBKDF2).
    """
    semilla = uuid.uuid4().hex[:8]
    usuarios: list[dict] = []
    inicio = time.perf_counter()
    for indice in range(cuantos):
        explotacion = {
            "nombre": f"Finca de carga {indice + 1}",
            "nif": "12345678Z",
            "provincia": "Salamanca",
            "municipio": "Peñaranda de Bracamonte",
        }
        alta = _exigir(
            cliente.post(
                "/api/cuenta/registro",
                json={
                    "explotacion": explotacion,
                    "nombre": f"Agricultor de carga {indice + 1}",
                    "correo": f"carga-{semilla}-{indice + 1}@ejemplo.test",
                    "clave": "carga-2026-segura",
                },
            ),
            f"el registro del agricultor de prueba {indice + 1}",
        ).json()
        cabeceras = {"Authorization": f"Bearer {alta['token']}"}

        campana = _exigir(
            cliente.get("/api/campanas/actual", headers=cabeceras),
            f"la campaña del agricultor de prueba {indice + 1}",
        ).json()

        producto = _exigir(
            cliente.post(
                "/api/productos",
                headers=cabeceras,
                json={
                    "nombre_comercial": "Producto de carga 25 EC",
                    "numero_registro": "24.123",
                    "materia_activa": "Tebuconazol",
                    "dosis_maxima": 0.8,
                    "unidad_dosis": "L/ha",
                    "plazo_seguridad_dias": 21,
                    "autorizado": True,
                    "permitido_ecologico": True,
                },
            ),
            f"el producto del agricultor de prueba {indice + 1}",
        ).json()

        tierras: list[int] = []
        for numero in range(tierras_por_usuario):
            tierra = _exigir(
                cliente.post(
                    "/api/parcelas",
                    headers=cabeceras,
                    json={
                        "alias": f"Tierra {numero + 1}",
                        "superficie_ha": 2.5,
                        "sistema": "secano",
                        "municipio": "Peñaranda de Bracamonte",
                        "provincia": "Salamanca",
                    },
                ),
                f"la tierra {numero + 1} del agricultor de prueba {indice + 1}",
            ).json()
            tierras.append(tierra["id"])

        usuarios.append(
            {
                "correo": f"carga-{semilla}-{indice + 1}@ejemplo.test",
                "clave": "carga-2026-segura",
                "campana_id": campana["id"],
                "producto_id": producto["id"],
                "tierras": tierras,
                "fecha": fecha,
            }
        )
    return usuarios, time.perf_counter() - inicio


# --------------------------------------------------------------------------
# El recorrido que hace un agricultor, y la medición
# --------------------------------------------------------------------------


async def _pedir(
    cliente: httpx.AsyncClient,
    medidas: list[dict],
    metodo: str,
    ruta: str,
    *,
    token: str | None = None,
    cuerpo: dict | None = None,
    esperado: int = 200,
) -> httpx.Response | None:
    """Una petición del recorrido, medida y apuntada **aunque falle**.

    Lo que falla no se esconde: se apunta el estado (0 si ni siquiera hubo respuesta) y se
    sigue. Así el escalón dice la verdad de lo que ha pasado y no una lista de los éxitos.
    """
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    inicio = time.perf_counter()
    respuesta: httpx.Response | None = None
    estado = 0
    try:
        respuesta = await cliente.request(metodo, ruta, headers=cabeceras, json=cuerpo)
        estado = respuesta.status_code
    except httpx.HTTPError:
        estado = 0
    transcurrido_ms = (time.perf_counter() - inicio) * 1000.0
    medidas.append({"ruta": ruta, "metodo": metodo, "estado": estado, "ms": transcurrido_ms})
    if estado != esperado:
        return None
    return respuesta


async def andar_el_recorrido(
    cliente: httpx.AsyncClient, usuario: dict, medidas: list[dict]
) -> None:
    """El recorrido real: entrar, listar, abrir ficha, apuntar tratamiento, ver el cuaderno.

    Si el agricultor no puede entrar, el recorrido **se corta ahí**: seguir sin vale sería
    contar cinco peticiones cuando lo que ha pasado es que no ha podido ni empezar.
    """
    entrada = await _pedir(
        cliente,
        medidas,
        "POST",
        "/api/cuenta/entrar",
        cuerpo={"correo": usuario["correo"], "clave": usuario["clave"]},
    )
    if entrada is None:
        return
    try:
        token = entrada.json()["token"]
    except (KeyError, ValueError):
        # **Un 200 que no trae token es UN fallo de entrar, no uno y medio.** La petición ya
        # está apuntada con su estado; añadir aquí otra medida falsa contaría dos peticiones
        # donde solo ha habido una y ensuciaría el porcentaje de errores del escalón.
        return

    await _pedir(cliente, medidas, "GET", "/api/parcelas/vista", token=token)
    await _pedir(cliente, medidas, "GET", f"/api/parcelas/{usuario['tierras'][0]}", token=token)
    await _pedir(
        cliente,
        medidas,
        "POST",
        "/api/tratamientos",
        token=token,
        esperado=201,
        cuerpo={
            "campana_id": usuario["campana_id"],
            "fecha": usuario["fecha"],
            "parcela_id": usuario["tierras"][0],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": usuario["producto_id"],
            "dosis": 0.5,
        },
    )
    await _pedir(cliente, medidas, "GET", "/api/cuaderno/resumen", token=token)


async def medir_un_escalon(
    direccion: str,
    usuarios: Sequence[dict],
    concurrentes: int,
    *,
    peticiones_por_usuario: int,
) -> dict:
    """Lanza `concurrentes` recorridos a la vez y devuelve las medidas del escalón."""
    limites = httpx.Limits(
        max_connections=max(10, concurrentes + 5),
        max_keepalive_connections=max(10, concurrentes + 5),
    )
    espera = httpx.Timeout(ESPERA_POR_PETICION_SEGUNDOS)

    async with httpx.AsyncClient(base_url=direccion, limits=limites, timeout=espera) as cliente:

        async def un_trabajador(indice: int) -> list[dict]:
            usuario = usuarios[indice % len(usuarios)]
            medidas: list[dict] = []
            for _ in range(peticiones_por_usuario):
                await andar_el_recorrido(cliente, usuario, medidas)
            return medidas

        inicio = time.perf_counter()
        tandas = await asyncio.gather(
            *(un_trabajador(indice) for indice in range(concurrentes))
        )
        segundos = time.perf_counter() - inicio

    medidas = [medida for tanda in tandas for medida in tanda]
    latencias = [medida["ms"] for medida in medidas]
    errores = sum(1 for medida in medidas if not 200 <= medida["estado"] < 300)
    resumen = {
        "usuarios": concurrentes,
        "peticiones": len(medidas),
        "errores": errores,
        "segundos": round(segundos, 3),
        "peticiones_por_segundo": round(len(medidas) / segundos, 1) if segundos > 0 else 0.0,
        "codigos": dict(sorted(Counter(str(m["estado"]) for m in medidas).items())),
    }
    if latencias:
        resumen.update(percentiles(latencias))
    else:  # pragma: no cover - sin ninguna medida no hay nada que decir
        resumen.update({"p50": 0.0, "p95": 0.0, "p99": 0.0})
    # La tabla usa los nombres largos; el JSON también, para que se lea solo.
    resumen["p50_ms"] = resumen.pop("p50")
    resumen["p95_ms"] = resumen.pop("p95")
    resumen["p99_ms"] = resumen.pop("p99")
    return resumen


# --------------------------------------------------------------------------
# El programa
# --------------------------------------------------------------------------


def _formatear_la_cabecera(
    *,
    direccion: str,
    propio: bool,
    maquina: dict,
    usuarios: int,
    tierras: int,
    preparacion: float,
    iteraciones: int = ITERACIONES_DEL_SERVIDOR_DE_PRUEBAS,
) -> str:
    ram = f"{maquina['ram_gb']:.1f} GB" if maquina.get("ram_gb") else "desconocida"
    if propio:
        donde = f"{direccion} (uvicorn temporal propio, base de datos temporal)"
        if iteraciones == ITERACIONES_DE_PRODUCCION:
            pbkdf2 = f"{iteraciones:,} iteraciones: la configuración de producción".replace(",", ".")
        else:
            pbkdf2 = (
                f"{iteraciones:,} iteraciones en el servidor de pruebas; "
                f"en producción son {ITERACIONES_DE_PRODUCCION:,}"
            ).replace(",", ".")
    else:
        donde = f"{direccion} (servidor dado con --base; no se ha arrancado ninguno)"
        pbkdf2 = "las que tenga ese servidor (no se pueden saber desde aquí)"
    return "\n".join(
        [
            f"Fecha: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Servidor: {donde}",
            f"Clave (PBKDF2): {pbkdf2}",
            f"Máquina: {maquina.get('procesador') or 'procesador desconocido'} · "
            f"{maquina.get('nucleos_logicos') or '?'} hilos · {ram} · {maquina.get('sistema')}",
            f"Agricultores de prueba: {usuarios} (con {tierras} tierras cada uno); "
            f"preparados por la API en {preparacion:.1f} s",
        ]
    )


def escribir_la_salida_json(datos: dict, *, a: Any = sys.stdout) -> None:
    print(json.dumps(datos, ensure_ascii=False, indent=2), file=a)


def main(argv: Sequence[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description=(
            "Cuántos agricultores aguanta esto hoy: siembra N cuentas de prueba en una base "
            "temporal, repite su recorrido con más y más usuarios a la vez y busca la rodilla."
        )
    )
    analizador.add_argument(
        "--base",
        default=None,
        help="dirección de un servidor que ya está en marcha (no se arranca ninguno)",
    )
    analizador.add_argument(
        "--escalones",
        default=ESCALONES_POR_DEFECTO,
        help=f"usuarios concurrentes por escalón, de menos a más (por defecto {ESCALONES_POR_DEFECTO})",
    )
    analizador.add_argument(
        "--peticiones-por-usuario",
        type=int,
        default=1,
        help="recorridos completos que hace cada usuario en cada escalón (por defecto 1)",
    )
    analizador.add_argument(
        "--tierras-por-usuario",
        type=int,
        default=TIERRAS_POR_USUARIO_POR_DEFECTO,
        help=f"tierras que se le dan a cada agricultor de prueba (por defecto {TIERRAS_POR_USUARIO_POR_DEFECTO})",
    )
    analizador.add_argument(
        "--iteraciones-pbkdf2",
        type=int,
        default=ITERACIONES_DEL_SERVIDOR_DE_PRUEBAS,
        help=(
            "iteraciones de PBKDF2 con las que arranca el servidor propio "
            f"(por defecto {ITERACIONES_DEL_SERVIDOR_DE_PRUEBAS:,}); con "
            f"{ITERACIONES_DE_PRODUCCION:,} se mide el coste real de entrar en producción"
        ).replace(",", "."),
    )
    analizador.add_argument(
        "--json", action="store_true", help="sacar el resultado en JSON en vez de la tabla"
    )
    analizador.add_argument(
        "--sin-servidor",
        action="store_true",
        help="no arrancar uvicorn: usar --base (o 127.0.0.1:8000) tal cual",
    )
    argumentos = analizador.parse_args(argv)

    if argumentos.json:
        decir = lambda texto: print(texto, file=sys.stderr)  # noqa: E731
    else:
        decir = print

    try:
        escalones = leer_los_escalones(argumentos.escalones)
    except ValueError as fallo:
        analizador.error(str(fallo))
    if argumentos.peticiones_por_usuario < 1:
        analizador.error("--peticiones-por-usuario tiene que ser uno o más.")
    if argumentos.tierras_por_usuario < 1:
        analizador.error("--tierras-por-usuario tiene que ser una o más.")
    if argumentos.iteraciones_pbkdf2 < 1:
        analizador.error("--iteraciones-pbkdf2 tiene que ser uno o más.")

    maquina = informacion_de_la_maquina()
    servidor: ServidorTemporal | None = None
    carpeta: pathlib.Path | None = None
    codigo = CODIGO_SIN_SERVIDOR
    try:
        # --- Dónde está el servidor ---
        if argumentos.base or argumentos.sin_servidor:
            try:
                direccion = normalizar_direccion(argumentos.base or DIRECCION_POR_DEFECTO)
            except ValueError as fallo:
                decir(mensaje_sin_servidor(str(argumentos.base), str(fallo)))
                return CODIGO_SIN_SERVIDOR
            contesta, detalle = contestan_en(direccion)
            if not contesta:
                decir(mensaje_sin_servidor(direccion, detalle))
                return CODIGO_SIN_SERVIDOR
            propio = False
        else:
            carpeta = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital-carga-"))
            servidor = ServidorTemporal(carpeta, iteraciones=argumentos.iteraciones_pbkdf2)
            try:
                direccion = servidor.arrancar()
            except NoHayServidor as fallo:
                decir(mensaje_sin_servidor(servidor.direccion, str(fallo)))
                return CODIGO_SIN_SERVIDOR
            propio = True

        # --- Sembrar los agricultores de prueba ---
        cuantos = max(escalones)
        decir("")
        decir("== Prueba de carga de CUE Digital ==")
        decir(f"Preparando {cuantos} agricultores de prueba (por la API pública)…")
        with httpx.Client(
            base_url=direccion,
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_connections=4),
        ) as cliente_de_preparacion:
            try:
                usuarios, segundos_de_preparacion = preparar_los_usuarios(
                    cliente_de_preparacion,
                    cuantos,
                    tierras_por_usuario=argumentos.tierras_por_usuario,
                )
            except (ErrorDePreparacion, httpx.HTTPError) as fallo:
                decir(f"No se han podido preparar los agricultores de prueba: {fallo}")
                decir("No se ha medido nada. Revisa que el servidor esté bien y vuelve a probar.")
                return CODIGO_SIN_SERVIDOR

        decir(
            _formatear_la_cabecera(
                direccion=direccion,
                propio=propio,
                maquina=maquina,
                usuarios=cuantos,
                tierras=argumentos.tierras_por_usuario,
                preparacion=segundos_de_preparacion,
                iteraciones=argumentos.iteraciones_pbkdf2,
            )
        )
        decir("")
        decir("Calentando el servidor con un recorrido que no se mide…")

        # Un recorrido de calentamiento: los módulos ya cargados y las conexiones abiertas, para
        # que el primer escalón no mida el arranque.
        asyncio.run(medir_un_escalon(direccion, usuarios, 1, peticiones_por_usuario=1))

        mediciones: list[dict] = []
        for escalon in escalones:
            decir(f"Escalón de {escalon} usuarios concurrentes…")
            medicion = asyncio.run(
                medir_un_escalon(
                    direccion,
                    usuarios,
                    escalon,
                    peticiones_por_usuario=argumentos.peticiones_por_usuario,
                )
            )
            mediciones.append(medicion)
            rodilla = encontrar_la_rodilla(mediciones)
            if rodilla is not None:
                decir("  Ha aparecido la rodilla: no se sube más, porque lo de arriba ya no dice nada.")
                break

        veredicto = resumir_el_veredicto(mediciones, escalones)
        datos = {
            "fecha": dt.datetime.now().isoformat(timespec="seconds"),
            "direccion": direccion,
            "servidor_propio": propio,
            "iteraciones_pbkdf2": (
                argumentos.iteraciones_pbkdf2 if propio else None
            ),
            "iteraciones_pbkdf2_de_produccion": ITERACIONES_DE_PRODUCCION,
            "maquina": maquina,
            "escalones_pedidos": list(escalones),
            "peticiones_por_usuario": argumentos.peticiones_por_usuario,
            "tierras_por_usuario": argumentos.tierras_por_usuario,
            "segundos_de_preparacion": round(segundos_de_preparacion, 1),
            "mediciones": mediciones,
            "veredicto": veredicto,
        }
        if argumentos.json:
            escribir_la_salida_json(datos)
            print("", file=sys.stderr)
            print(formatear_la_tabla(mediciones, veredicto), file=sys.stderr)
        else:
            print("")
            print(formatear_la_tabla(mediciones, veredicto))
            print("")
            print(f"Código de salida: {veredicto['codigo']} (0 aguanta · 1 no aguanta · 2 no se pudo medir)")
        codigo = veredicto["codigo"]
        return codigo
    except KeyboardInterrupt:  # pragma: no cover - quien lanza decide
        decir("Interrumpido: se apaga el servidor y se borra la carpeta temporal.")
        return CODIGO_SIN_SERVIDOR
    finally:
        if servidor is not None:
            try:
                servidor.parar()
            except NoHayServidor as fallo:
                print(f"AVISO: {fallo}", file=sys.stderr)
        if carpeta is not None:
            if borrar_carpeta(carpeta):
                print("Servidor apagado y carpeta temporal borrada.", file=sys.stderr)
            else:  # pragma: no cover - Windows con un fichero todavía abierto
                print(
                    f"AVISO: no se ha podido borrar del todo la carpeta temporal {carpeta}.",
                    file=sys.stderr,
                )


if __name__ == "__main__":
    raise SystemExit(main())
