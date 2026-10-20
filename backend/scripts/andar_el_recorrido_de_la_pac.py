"""***Andar el recorrido de la PAC*** contra un servidor temporal (18/10/2026).

*Como el de los roles: **la base del agricultor no se toca**. Se levanta uvicorn con
`CUEDIGITAL_DATABASE_URL` a una base de un directorio temporal, se anda el recorrido y se tira todo.*

*Y no se reutiliza `con_su_propio_servidor` del guion de los roles porque **ese levanta el servidor Y anda su
recorrido**, devolviendo el codigo: aqui hace falta **solo el servidor**.*

Uso:  python scripts/andar_el_recorrido_de_la_pac.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager

sys.path.insert(0, "scripts")

import capturar_la_pantalla_del_reparto as el_reparto  # noqa: E402
import verificar_el_recorrido_de_la_pac as el_recorrido  # noqa: E402
from verificar_los_permisos_por_rol import BACKEND, PYTHON, un_puerto_libre  # noqa: E402


@contextmanager
def el_servidor_temporal():
    """***El servidor de verdad, con su base temporal***: *nada de esto toca la base del agricultor.*"""
    puerto = un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    temporal = tempfile.mkdtemp(prefix="cuedigital-pac-")
    servidor = None
    try:
        base = pathlib.Path(temporal) / "prueba.db"
        entorno = dict(os.environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        servidor = subprocess.Popen(  # noqa: S603
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
            cwd=str(BACKEND),
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        listo = False
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                    listo = True
                    break
            except (urllib.error.URLError, OSError):
                if servidor.poll() is not None:
                    raise SystemExit("el servidor no ha arrancado")
                time.sleep(0.5)
        if not listo:
            raise SystemExit("el servidor no ha contestado a /api/interfaz")
        yield direccion
    finally:
        if servidor is not None and servidor.poll() is None:
            servidor.terminate()
            try:
                servidor.wait(timeout=15)
            except subprocess.TimeoutExpired:
                servidor.kill()
                servidor.wait(timeout=10)
        time.sleep(1.0)
        shutil.rmtree(temporal, ignore_errors=True)


def main() -> int:
    with el_servidor_temporal() as la_direccion:
        # ***La direccion vive en DOS modulos***: *`verificar_el_recorrido_de_la_pac` la tiene para el navegador y
        # `capturar_la_pantalla_del_reparto` para `_api` -que llama a la puerta para contrastar la pantalla-. Si se
        # cambia una y no la otra, `_api` se va al 8029 de por defecto, que no esta levantado, y el recorrido muere
        # con «conexion rechazada» antes de empezar.*
        el_recorrido.DIRECCION = la_direccion
        el_reparto.DIRECCION = la_direccion
        return el_recorrido.main()


if __name__ == "__main__":
    raise SystemExit(main())
