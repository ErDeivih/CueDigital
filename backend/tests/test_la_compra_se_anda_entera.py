"""La compra de punta a punta, **corrida de verdad** por la suite (08/10/2026).

**Por qué existe.** El encargo lo pide con estas palabras: *convertir los comportamientos exigidos en pruebas
obligatorias, no en hallazgos que permitan un cierre verde*. El guion
(`scripts/comprobar_la_compra_de_punta_a_punta.py`) acredita la compra entera -proveedor, factura de 663 con
líneas, recepción en las mismas unidades, lote, gasto vinculado y pagos **por identificador**-, pero un guion
**nadie lo ejecuta**: es el mismo hueco por el que se colaron los defectos que solo se ven andando, y que
`test_el_recorrido_se_anda.py` ya cerró para el otro recorrido.

Esta prueba lo corre **entero**: levanta el servidor en una **base temporal**, deja que el guion prepare su
explotación y sus documentos ficticios, y exige las **cifras** del encargo. Si la compra se rompe, esto se pone
rojo.

**No necesita navegador**: este caso va por la API, que es lo que acredita los vínculos y las cifras. Lo que
falta -la ficha de compra y sus capturas- es otra parte del encargo y tendrá su prueba cuando exista.

**Y se demostró que puede ponerse roja** (09/10/2026), que es lo que distingue una prueba de un adorno: se
cambió a mano el primer pago de 200 a 100 -una línea, `PRIMER_PAGO`- y la prueba se puso roja **por la cifra**
(`falta(n): queda pagada: pendiente 663.0 -> 463.0 -> 0.0, y su estado lo dice ('pagado')`, con el guion
diciendo `Fallos: 3`); después se restauró el guion **byte a byte** (sha256 comprobado) y volvió a verde.
"""

from __future__ import annotations

import os
import pathlib
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
# El mismo intérprete que corre las pruebas: pytest ya vive en el entorno del proyecto.
PYTHON = sys.executable
GUION = BACKEND / "scripts" / "comprobar_la_compra_de_punta_a_punta.py"

# **Las cifras que el encargo exige ver, escritas como las dice el guion** (09/10/2026). La salida se lee
# literal: la primera versión de esta prueba pedía `estado 'pagado'`, que **no es** el texto que el guion
# imprime —imprime `y su estado lo dice ('pagado')`—, y el rojo lo causaba mi cadena inventada y no la
# compra. Se comprobó en el servidor antes de escribirla: `gastos.estado_de_un_gasto` devuelve la constante
# `gastos.PAGADO` (`"pagado"`), no `"pago"`.
LAS_CIFRAS = (
    # **Por identificador, no por el total.** Es la corrección que el encargo aceptó: el pendiente de ESA
    # factura en su cadena entera -663, luego 463 tras aplicar 200, y 0 tras aplicar los 463-. Un total
    # global que baje no demuestra cuál se pagó; esta cadena sí.
    "queda pagada: pendiente 663.0 -> 463.0 -> 0.0",
    # Y su estado, calculado por el servidor.
    "y su estado lo dice ('pagado')",
    "1000.0 -> 1000.0",        # A15: enganchar la factura no mete ni un kilo
    # **El pago agrupado** (09/10/2026): un solo dinero de 350 que salda **dos** facturas -100 y 250-, cada
    # una por su identificador, con sus dos aplicaciones y sin perder un céntimo por el camino.
    "cada una por su identificador ([0.0, 0.0])",
    "lo aplicado es el dinero entero (350.0 de 350.00)",
    # **Y la separación, medida** (09/10/2026): anular el albarán devuelve exactamente lo que metió, y anular
    # la factura no vacía el almacén, porque la mercancía no la metió la factura.
    "anular el albaran devuelve **exactamente lo que metio** (300.0 de 300)",
    "anular la factura no vacia el almacen",
)


def un_puerto_libre() -> int:
    with socket.socket() as suyo:
        suyo.bind(("127.0.0.1", 0))
        return int(suyo.getsockname()[1])


def esperar_a_que_responda(direccion: str, segundos: float = 60.0) -> bool:
    """Se pregunta por `/api/interfaz`, que **es la puerta que existe** (09/10/2026).

    La primera versión preguntaba por `/api/salud`: **ese camino no existe en este proyecto** (lo comprobé
    con una búsqueda: no hay ni una ruta «salud» en `app/`), así que el servidor arrancaba bien y la sonda
    lo daba por muerto a los 40 segundos. El servidor quedaba vivo sujetando la base temporal, y encima eso
    hacía fallar la limpieza de la carpeta con `WinError 32`, tapando el motivo real. Se pregunta por
    `/api/interfaz`, que es la misma puerta que usa `test_el_recorrido_se_anda.py`.

    **Sesenta segundos y no cuarenta** (09/10/2026): con la máquina cargada —justo después de otra corrida
    de la suite— el arranque se pasó de los cuarenta y la prueba se puso roja **sin que la compra tuviera
    nada roto**: el mismo día, la misma prueba, roja por el arranque y verde por lo que juzga. El margen no
    esconde nada, porque cuando no arranca la prueba **enseña la salida del servidor** (ver abajo).
    """
    final = time.time() + segundos
    while time.time() < final:
        try:
            with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                return True
        except (urllib.error.URLError, OSError):  # cualquier fallo aqui es «todavia no»
            time.sleep(0.3)
    return False


def test_la_compra_se_anda_entera():
    """Se levanta el servidor en base temporal, se corre el guion y se exigen sus cifras."""
    puerto = un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    with tempfile.TemporaryDirectory(
        prefix="cuedigital-compra-",
        # **`ignore_cleanup_errors` porque Windows tarda en soltar la base** (09/10/2026): es el mismo
        # tropiezo que ya documentó `test_el_recorrido_se_anda.py`. Se soltó el servidor y el fichero de
        # SQLite seguía abierto un instante, así que borrar la carpeta temporal fallaba con
        # `PermissionError: [WinError 32]` **después** de lo que importa, y el rojo quedaba tapado por la
        # limpieza. Lo que se juzga es lo que pasó dentro; la carpeta temporal la limpia el sistema.
        ignore_cleanup_errors=True,
    ) as carpeta:
        base = pathlib.Path(carpeta) / "compra.db"
        # **La salida del servidor va a un fichero, no a la basura** (09/10/2026). Estaba en `DEVNULL`, así
        # que cuando el servidor no arrancó la prueba esperó sesenta segundos a ciegas y no pudo decir por
        # qué: un fallo de arranque —un puerto ocupado, una migración que revienta— era indistinguible de
        # «va lento». Con esto, si no arranca, la prueba **enseña lo que dijo el servidor**.
        diario = pathlib.Path(carpeta) / "servidor.log"
        entorno = dict(os.environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        entorno["PYTHONIOENCODING"] = "utf-8"
        with open(diario, "w", encoding="utf-8", errors="replace") as el_diario:
            servidor = subprocess.Popen(  # noqa: S603 - es el propio proyecto
                [PYTHON, "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
                cwd=str(BACKEND), env=entorno, stdout=el_diario, stderr=subprocess.STDOUT,
            )
            try:
                if not esperar_a_que_responda(direccion):
                    raise AssertionError(
                        "el servidor de pruebas no ha llegado a responder en " + direccion
                        + "\n\n--- lo que dijo el servidor ---\n"
                        + diario.read_text(encoding="utf-8", errors="replace")[-3000:]
                    )
                suyo = subprocess.run(  # noqa: S603 - es el propio proyecto
                    [PYTHON, str(GUION), direccion, carpeta, str(base)],
                    cwd=str(BACKEND), env=entorno, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=600,
                )
                salida = (suyo.stdout or "") + (suyo.stderr or "")
                faltan = [cifra for cifra in LAS_CIFRAS if cifra not in salida]
                assert not faltan, (
                    "la compra de punta a punta no cuadra; falta(n): "
                    + ", ".join(faltan)
                    + "\n\n--- la salida entera del guion ---\n"
                    + salida[-4000:]
                )
                assert suyo.returncode == 0, (
                    "el guion de la compra ha salido con codigo " + str(suyo.returncode) + ":\n" + salida[-2000:]
                )
                assert "Fallos: 0" in salida, "el guion no dice que no haya fallos:\n" + salida[-2000:]
                # **Que no se quede a medias, medido de verdad** (09/10/2026). Aquí NO se fija el recuento a
                # mano: el mismo tropiezo ya está documentado en `test_el_recorrido_se_anda.py` —allí se
                # exigía que la cifra empezara por «1» o por «2» y eso se rompió **solo porque el recorrido
                # creció a 44**—. Se lee la cifra y se pide un mínimo: lo que importa es que la compra haga
                # su trabajo.
                cuantas = re.search(r"Comprobaciones:\s*(\d+)", salida)
                assert cuantas, "el guion no dice cuantas comprobaciones ha hecho:\n" + salida[-800:]
                # **Cuarenta, y hoy hace cuarenta y nueve** (09/10/2026): el mínimo queda por debajo a
                # propósito —lo que importa es que la compra haga su trabajo, no cuántos dígitos tenga la
                # cifra—, pero **alto**, para que quitarle secciones al guion se note en vez de pasar en
                # silencio por el hueco que dejó el «30» escrito a mano.
                assert int(cuantas.group(1)) >= 40, (
                    f"la compra ha hecho muy pocas comprobaciones ({cuantas.group(1)}): ¿se ha quedado a medias?"
                )
            finally:
                servidor.terminate()
                try:
                    servidor.wait(timeout=15)
                except subprocess.TimeoutExpired:  # pragma: no cover - solo si se atasca al cerrar
                    servidor.kill()
