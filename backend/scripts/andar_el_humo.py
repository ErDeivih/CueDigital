"""***Andar el humo*** contra un servidor temporal (21/10/2026).

*`scripts/humo.py` comprueba lo que pytest no puede -que uvicorn arranca, que la API responde por HTTP y que el PDF
se abre-, pero **necesita el servidor levantado con cuatro variables**: base nueva, secreto, carpeta de adjuntos y
`CONFIAR_EN_CABECERAS`. Esto se las pone, usa **solo datos temporales** y lo tira todo al terminar.*

Uso:  python scripts/andar_el_humo.py
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

sys.path.insert(0, "scripts")

from verificar_los_permisos_por_rol import BACKEND, PYTHON, un_puerto_libre  # noqa: E402


def main() -> int:
    puerto = un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    temporal = tempfile.mkdtemp(prefix="cuedigital-humo-")
    servidor = None
    try:
        entorno = dict(os.environ)
        # ***Cuatro variables, y todas temporales***: *la base, el secreto, los adjuntos y el permiso del
        # certificado. La base del agricultor no se toca.*
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{pathlib.Path(temporal, 'humo.db')}"
        entorno["CUEDIGITAL_SECRETO"] = "no-es-un-secreto-de-verdad"
        entorno["CUEDIGITAL_ADJUNTOS"] = str(pathlib.Path(temporal, "adjuntos"))
        entorno["CUEDIGITAL_CONFIAR_EN_CABECERAS"] = "1"
        servidor = subprocess.Popen(  # noqa: S603
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
            cwd=str(BACKEND),
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        listo = False
        for _ in range(160):
            try:
                with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                    listo = True
                    break
            except (urllib.error.URLError, OSError):
                if servidor.poll() is not None:
                    raise SystemExit("el servidor no ha arrancado")
                time.sleep(0.5)
        if not listo:
            raise SystemExit("el servidor no ha contestado")
        print(f"== Humo contra {direccion} ==")
        sys.stdout.flush()
        la_prueba = subprocess.run(  # noqa: S603
            [str(PYTHON), "scripts/humo.py", direccion], cwd=str(BACKEND)
        )
        return la_prueba.returncode
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


if __name__ == "__main__":
    raise SystemExit(main())
