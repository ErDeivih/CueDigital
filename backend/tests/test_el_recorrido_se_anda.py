"""El recorrido del encargo, **corrido de verdad**: servidor de pruebas y un navegador sin ventana.

**Por qué existe esto** (07/10/2026). El guion del recorrido (`scripts/comprobar_el_recorrido.py`) lleva
desde el 05/10 pasando a mano: hay un guardián que comprueba que está escrito y que recorre los pasos, pero
**nadie lo ejecutaba**. Y ese es el hueco por el que se colaron los defectos que solo se ven andando (un
422 al corregir un trabajo, un botón que no llevaba a ninguna parte): con todas las suites en verde, el
recorrido podía estar roto.

Esta prueba lo corre **entero**: levanta el servidor en una base temporal, prepara la explotación de 64
tierras y anda el recorrido con Chrome sin ventana. Si el recorrido se rompe, esto se pone rojo.

**Se salta diciendo por qué** si no hay navegador instalado, que es lo único que puede faltar aquí.
"""

from __future__ import annotations

import os
import pathlib
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
    with tempfile.TemporaryDirectory(prefix="cuedigital-recorrido-") as temporal:
        base = pathlib.Path(temporal) / "prueba.db"
        entorno = dict(os.environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        servidor = subprocess.Popen(  # noqa: S603 — es el propio proyecto, no una orden de fuera
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
            cwd=str(BACKEND),
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            assert _esperar_al_servidor(direccion), "el servidor de pruebas no ha arrancado"
            recorrido = subprocess.run(  # noqa: S603
                [str(PYTHON), str(GUION), direccion, str(pathlib.Path(temporal) / "capturas")],
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
            assert "Comprobaciones: 1" in recorrido.stdout or "Comprobaciones: 2" in recorrido.stdout, (
                "el recorrido ha hecho muy pocas comprobaciones: ¿se ha quedado a medias?"
            )
        finally:
            servidor.terminate()
            try:
                servidor.wait(timeout=15)
            except subprocess.TimeoutExpired:
                servidor.kill()
