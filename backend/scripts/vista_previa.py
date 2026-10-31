"""Arrancar una vista previa de CUE Digital sin tocar los datos de nadie.

Para qué sirve
--------------
El portal de David enseña el producto en marcha. Este guion arranca la aplicación
en `127.0.0.1` con una base de datos y una carpeta de adjuntos **de demostración**
(no las de verdad), deja la salida en la consola y **no termina hasta que lo
paren**. Si falta el entorno, lo prepara: crea `.venv` la primera vez e instala
las dependencias que falten.

Cómo se usa
-----------
    python scripts/vista_previa.py
    python scripts/vista_previa.py --puerto 8123
    python scripts/vista_previa.py --datos C:\\temp\\vista-previa

El puerto también se puede dar con la variable `PORT`, que es lo que usan los
portales. Manda el argumento. Los datos también se pueden cambiar con
`CUEDIGITAL_VISTA_PREVIA_DATOS`.

Lo que escribe en la consola
----------------------------
Una línea `[vista-previa] escuchando en http://127.0.0.1:<puerto>` cuando el
servidor está arrancando, y el resto de la salida del propio servidor. Cuando se
para con Ctrl+C o con una señal, termina con código 0. Si no puede arrancar,
termina con un código distinto de 0 y dice por qué.

Lo que NO hace
--------------
No usa los datos de la explotación de nadie, no se conecta a PostgreSQL y no
copia `cuedigital.db`. Lo que se apunte en la vista previa se queda en
`backend/datos/vista-previa/`, que está fuera del repositorio.
"""

from __future__ import annotations

import argparse
import os
import secrets
import signal
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORIO = BACKEND.parent
DATOS_POR_DEFECTO = BACKEND / "datos" / "vista-previa"

# Estas variables cambian el comportamiento del programa o apuntan a datos de
# verdad. Se quitan siempre: una vista previa no puede acabar escribiendo en la
# base de la explotación por una variable que quedó puesta en la consola.
VARIABLES_QUE_SE_QUITAN = (
    "CUEDIGITAL_ENTORNO",
    "CUEDIGITAL_SECRETO",
    "CUEDIGITAL_SECRETO_ANTERIOR",
    "CUEDIGITAL_CONFIAR_EN_CABECERAS",
    "CUEDIGITAL_DATABASE_URL",
    "CUEDIGITAL_ADJUNTOS",
    "CUEDIGITAL_ITERACIONES_PBKDF2",
    "CUEDIGITAL_VISTA_PREVIA_DATOS",
)


def decir(texto: str) -> None:
    print(f"[vista-previa] {texto}", flush=True)


def el_python_del_venv() -> Path:
    if os.name == "nt":
        return REPOSITORIO / ".venv" / "Scripts" / "python.exe"
    return REPOSITORIO / ".venv" / "bin" / "python"


def estamos_dentro_de_un_venv() -> bool:
    return Path(sys.prefix).resolve() != Path(sys.base_prefix).resolve()


def probar_la_importacion(python: Path, entorno: dict[str, str]) -> tuple[bool, str]:
    """Una sola prueba cubre todas las dependencias: si `app.main` importa, están."""
    prueba = subprocess.run(  # noqa: S603 - es el propio proyecto
        [str(python), "-c", "import app.main"],
        cwd=str(BACKEND),
        env=entorno,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return prueba.returncode == 0, (prueba.stdout or "").strip()


def crear_el_venv() -> Path:
    python = el_python_del_venv()
    decir(f"preparando el entorno en {REPOSITORIO / '.venv'} (solo la primera vez)")
    subprocess.run(  # noqa: S603 - es el propio proyecto
        [sys.executable, "-m", "venv", str(REPOSITORIO / ".venv")],
        check=True,
    )
    if not python.exists():
        raise RuntimeError(f"se creó el entorno pero no aparece {python}")
    return python


def instalar_lo_que_falta(python: Path, entorno: dict[str, str]) -> None:
    requisitos = BACKEND / "requirements.txt"
    if not requisitos.is_file():
        raise RuntimeError(f"faltan dependencias y no está {requisitos}")
    decir("faltan dependencias; instalando requirements.txt (puede tardar un poco)")
    subprocess.run(  # noqa: S603 - es el propio proyecto
        [str(python), "-m", "pip", "install", "-r", str(requisitos)],
        cwd=str(BACKEND),
        env=entorno,
        check=True,
    )


def elegir_python(entorno: dict[str, str]) -> Path:
    """El intérprete que ya funciona, o uno preparado para que funcione."""
    candidato = el_python_del_venv()
    if candidato.exists():
        listo, _ = probar_la_importacion(candidato, entorno)
        if listo:
            return candidato

    actual = Path(sys.executable)
    listo, salida = probar_la_importacion(actual, entorno)
    if listo:
        return actual

    if candidato.exists():
        instalar_lo_que_falta(candidato, entorno)
        listo, salida = probar_la_importacion(candidato, entorno)
        if listo:
            return candidato
        if salida:
            print(salida[-3000:], flush=True)
        raise RuntimeError("siguen faltando dependencias después de instalarlas")

    if estamos_dentro_de_un_venv():
        instalar_lo_que_falta(actual, entorno)
        listo, salida = probar_la_importacion(actual, entorno)
        if listo:
            return actual
        if salida:
            print(salida[-3000:], flush=True)
        raise RuntimeError("siguen faltando dependencias después de instalarlas")

    candidato = crear_el_venv()
    instalar_lo_que_falta(candidato, entorno)
    listo, salida = probar_la_importacion(candidato, entorno)
    if listo:
        return candidato
    if salida:
        print(salida[-3000:], flush=True)
    raise RuntimeError("siguen faltando dependencias después de instalarlas")


def preparar_el_entorno(datos: Path) -> tuple[dict[str, str], Path, Path]:
    """Variables limpias y las dos rutas de demostración, ya creadas."""
    base = datos / "cuaderno.db"
    adjuntos = datos / "adjuntos"
    datos.mkdir(parents=True, exist_ok=True)
    adjuntos.mkdir(parents=True, exist_ok=True)

    entorno = dict(os.environ)
    for clave in VARIABLES_QUE_SE_QUITAN:
        entorno.pop(clave, None)

    # SQLite quiere barras normales también en Windows.
    direccion = "sqlite:///" + str(base.resolve()).replace("\\", "/")
    entorno.update(
        {
            "CUEDIGITAL_DATABASE_URL": direccion,
            "CUEDIGITAL_ADJUNTOS": str(adjuntos.resolve()),
            # Una clave nueva en cada arranque: no se reutiliza la de producción
            # ni la de la base de demostración anterior.
            "CUEDIGITAL_SECRETO": secrets.token_hex(32),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUNBUFFERED": "1",
        }
    )
    return entorno, base, adjuntos


def el_puerto(valor: str) -> int:
    try:
        puerto = int(valor)
    except ValueError as fallo:
        raise argparse.ArgumentTypeError(f"«{valor}» no es un número de puerto") from fallo
    if not 1 <= puerto <= 65535:
        raise argparse.ArgumentTypeError(f"el puerto {puerto} no está entre 1 y 65535")
    return puerto


def los_argumentos() -> argparse.Namespace:
    analizador = argparse.ArgumentParser(
        description="Arranca CUE Digital con datos de demostración, sin tocar los de verdad.",
    )
    analizador.add_argument(
        "--puerto",
        type=el_puerto,
        default=None,
        help="puerto de 127.0.0.1 (por defecto, PORT o 8000)",
    )
    analizador.add_argument(
        "--datos",
        type=Path,
        default=None,
        help="carpeta de la base y los adjuntos de demostración",
    )
    argumentos = analizador.parse_args()
    if argumentos.puerto is None:
        try:
            argumentos.puerto = el_puerto(os.environ.get("PORT", "8000"))
        except argparse.ArgumentTypeError as fallo:
            analizador.error(f"PORT no sirve: {fallo}")
    if argumentos.datos is None:
        argumentos.datos = Path(
            os.environ.get("CUEDIGITAL_VISTA_PREVIA_DATOS", str(DATOS_POR_DEFECTO)),
        )
    return argumentos


def main() -> int:
    argumentos = los_argumentos()
    datos = argumentos.datos
    if not datos.is_absolute():
        datos = BACKEND / datos

    decir(f"datos de demostración en {datos.resolve()}")
    try:
        entorno, base, adjuntos = preparar_el_entorno(datos)
        python = elegir_python(entorno)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as fallo:
        decir(f"no se pudo preparar la vista previa: {fallo}")
        return 1

    decir(f"base: {base}")
    decir(f"adjuntos: {adjuntos}")
    decir(f"escuchando en http://127.0.0.1:{argumentos.puerto}")

    orden = [
        str(python),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(argumentos.puerto),
    ]
    servidor = subprocess.Popen(  # noqa: S603 - es el propio proyecto
        orden,
        cwd=str(BACKEND),
        env=entorno,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    detenido_por_nosotros = False

    def parar(signum: int, _marco: object) -> None:
        nonlocal detenido_por_nosotros
        detenido_por_nosotros = True
        if servidor.poll() is None:
            decir("parando…")
            servidor.terminate()

    for nombre in ("SIGINT", "SIGTERM", "SIGHUP"):
        senal = getattr(signal, nombre, None)
        if senal is not None:
            try:
                signal.signal(senal, parar)
            except (OSError, ValueError):
                # En Windows algunas señales no se pueden manejar; la terminal
                # sigue enviando Ctrl+C y el servidor se para igualmente.
                pass

    try:
        codigo = servidor.wait()
    except KeyboardInterrupt:
        detenido_por_nosotros = True
        if servidor.poll() is None:
            servidor.terminate()
        codigo = servidor.wait()

    if detenido_por_nosotros:
        decir("vista previa parada")
        return 0
    if codigo != 0:
        decir(f"el servidor terminó con código {codigo}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
