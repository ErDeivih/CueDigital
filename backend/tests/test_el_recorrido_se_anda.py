"""El recorrido del encargo, **corrido de verdad**: servidor de pruebas y un navegador sin ventana.

**Por qué existe esto** (07/10/2026). El guion del recorrido (`scripts/comprobar_el_recorrido.py`) lleva
desde el 05/10 pasando a mano: hay un guardián que comprueba que está escrito y que recorre los pasos, pero
**nadie lo ejecutaba**. Y ese es el hueco por el que se colaron los defectos que solo se ven andando (un
422 al corregir un trabajo, un botón que no llevaba a ninguna parte): con todas las suites en verde, el
recorrido podía estar roto.

Esta prueba lo corre **entero**: levanta el servidor en una base temporal, prepara la explotación de 64
tierras y anda el recorrido con Chrome sin ventana. Si el recorrido se rompe, esto se pone rojo.

**Se salta diciendo por qué** si no hay navegador instalado, que es lo único que puede faltar aquí.

**Y puede fallar de vez en cuando si hay otro navegador trabajando a la vez** (07/10/2026): el guion
levanta su servidor en un puerto libre y abre su propio Chrome, así que con otra sesión de navegador en
marcha (otro guion de comprobación, por ejemplo) puede quedarse sin respuesta. Pasó una vez, corriendo
esto junto a otro servidor de pruebas. Si vuelve a pasar: córrelo **solo**, y si aun así falla, mira la
salida del guion — la prueba la imprime entera cuando se rompe, con las comprobaciones que sí habían
pasado. No es el producto: es que dos navegadores a la vez se estorban.
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

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
# **El mismo intérprete que corre las pruebas**, y no una ruta escrita a mano: pytest ya se ejecuta dentro
# del entorno virtual del proyecto, así que esto vale en Windows y en Linux, y no se rompe si el entorno
# cambia de sitio (que es lo que pasó: la primera versión apuntaba a `backend/.venv`, que no existe).
PYTHON = sys.executable
GUION = BACKEND / "scripts" / "comprobar_el_recorrido.py"

NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def _hay_navegador() -> bool:
    return any(pathlib.Path(ruta).exists() for ruta in NAVEGADORES)


def _un_puerto_libre() -> int:
    with socket.socket() as hueco:
        hueco.bind(("127.0.0.1", 0))
        return hueco.getsockname()[1]


def _lo_que_dijo_el_servidor(log: pathlib.Path) -> str:
    """***Lo que escribio el servidor, para poder leerlo en el fallo.***

    *Con `DEVNULL` el fallo decia «no ha arrancado» y ahi se acababa todo: **la causa -un import roto, un
    puerto ocupado, una columna que falta- se perdia en el vacio**.*

    ***Y si el fichero esta vacio, se dice eso***: *«no dijo nada» es un dato -uvicorn ni llego a
    arrancar-, y es distinto de «dijo esto otro».*
    """
    try:
        dicho = log.read_bytes().decode("utf-8", errors="replace").strip()
    except OSError as fallo:
        return f"(no se ha podido leer {log.name}: {fallo})"
    if not dicho:
        return "(no dijo nada: ni siquiera llego a arrancar)"
    # ***Las ultimas lineas son las que importan***: *uvicorn escribe mucho al arrancar y el fallo va al final.
    return dicho[-3000:]


def _esperar_al_servidor(direccion: str, segundos: float = 30.0) -> bool:
    import urllib.error
    import urllib.request

    final = time.time() + segundos
    while time.time() < final:
        try:
            with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.3)
    return False


@pytest.mark.skipif(not _hay_navegador(), reason="no hay Chrome ni Edge en este ordenador: el recorrido necesita un navegador de verdad")
def test_el_recorrido_se_anda_entero():
    """El recorrido del encargo, con la explotación de 64 tierras, contra un servidor de verdad."""
    puerto = _un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    with tempfile.TemporaryDirectory(
        prefix="cuedigital-recorrido-",
        # **`ignore_cleanup_errors` porque Windows tarda en soltar la base** (07/10/2026): al terminar el
        # servidor, el fichero de SQLite sigue abierto un instante y borrar la carpeta temporal fallaba con
        # `PermissionError: [WinError 32]` — **después** de que el recorrido hubiera pasado entero, así que
        # la prueba se ponía roja por la limpieza y no por lo que comprueba. Lo que importa es lo que pasó
        # dentro; la carpeta temporal la limpia el sistema.
        ignore_cleanup_errors=True,
    ) as temporal:
        base = pathlib.Path(temporal) / "prueba.db"
        entorno = dict(os.environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        # ***Lo que dice el servidor, a un fichero*** (17/10/2026). *Antes iba a `DEVNULL`, y cuando no
        # arrancaba la prueba solo podia decir **«no ha arrancado»** -sin la causa, que es lo unico que
        # permite arreglarlo-. Con el fichero, el fallo **dice por que**.*
        #
        # ***Y el `stderr` va al mismo sitio que el `stdout`***: *uvicorn escribe una cosa en cada uno, y
        # separarlos obligaria a leer dos ficheros para entender un fallo.*
        log = pathlib.Path(temporal) / "servidor.log"
        salida_del_servidor = log.open("wb")
        servidor = subprocess.Popen(  # noqa: S603 — es el propio proyecto, no una orden de fuera
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
            cwd=str(BACKEND),
            env=entorno,
            stdout=salida_del_servidor,
            stderr=subprocess.STDOUT,
        )
        try:
            assert _esperar_al_servidor(direccion), (
                "el servidor de pruebas no ha arrancado. **Lo que dijo**:\n"
                + _lo_que_dijo_el_servidor(log)
            )
            recorrido = subprocess.run(  # noqa: S603
                [
                    str(PYTHON),
                    str(GUION),
                    direccion,
                    str(pathlib.Path(temporal) / "capturas"),
                    # **La base de la prueba, para la auditoría** (07/10/2026): la comprobación de la entrada de
                    # auditoría de la anulación **la lee de la base** -la API no la expone-, así que la prueba
                    # tiene que decirle cuál es la base que ella misma ha levantado. Va en el **tercer**
                    # argumento, porque el segundo es la carpeta de capturas.
                    str(base),
                ],
                cwd=str(BACKEND),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
            assert recorrido.returncode == 0, (
                "el recorrido se ha roto:\n" + (recorrido.stdout or "")[-3000:] + (recorrido.stderr or "")[-1000:]
            )
            assert "Fallos: 0" in recorrido.stdout, "el guion no dice que no haya fallos"
            # **Que no se quede a medias**, medido de verdad (07/10/2026): aquí se exigía que el recuento
            # empezara por «1» o por «2» —que era como decir «al menos diez» cuando el recorrido hacía
            # trece— y eso se rompió **solo en cuanto el recorrido creció a 44**: la comprobación fallaba
            # por el número, no por el guion. Ahora se lee la cifra y se pide un mínimo: lo que importa es
            # que el recorrido **haga su trabajo**, no cuántos dígitos tenga la cifra.
            cuantas = re.search(r"Comprobaciones:\s*(\d+)", recorrido.stdout or "")
            assert cuantas, (
                "el guion no dice cuántas comprobaciones ha hecho:\n" + (recorrido.stdout or "")[-800:]
            )
            assert int(cuantas.group(1)) >= 20, (
                f"el recorrido ha hecho muy pocas comprobaciones ({cuantas.group(1)}): ¿se ha quedado a medias?"
            )
        finally:
            # ***Y el fichero se cierra***, para que lo que se lea despues este entero.
            servidor.terminate()
            salida_del_servidor.close()
            try:
                servidor.wait(timeout=15)
            except subprocess.TimeoutExpired:
                servidor.kill()
