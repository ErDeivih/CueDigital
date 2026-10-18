"""**Reproducir el arranque del recorrido, pero LEYENDO SU SALIDA** (17/10/2026).

`test_el_recorrido_se_anda` arranca `uvicorn` con `stdout=DEVNULL, stderr=DEVNULL`, asi que **cuando no
arranca no hay nada que leer**. Esto hace lo mismo -su `TemporaryDirectory`, su `env`, su puerto libre- pero
con la salida **capturada**, que es lo unico que falta para saber por que.
"""

import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

BACKEND = pathlib.Path(__file__).resolve().parents[1]
PYTHON = BACKEND.parent / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = pathlib.Path(sys.executable)


def un_puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


puerto = un_puerto_libre()
direccion = f"http://127.0.0.1:{puerto}"
print(f"  python    : {PYTHON}")
print(f"  puerto    : {puerto}")

with tempfile.TemporaryDirectory(prefix="cuedigital-recorrido-") as temporal:
    base = pathlib.Path(temporal) / "prueba.db"
    entorno = dict(os.environ)
    entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
    print(f"  base      : {base}")
    for clave in ("CUEDIGITAL_ENTORNO", "CUEDIGITAL_ITERACIONES_PBKDF2", "CUEDIGITAL_ADJUNTOS"):
        print(f"  {clave}: {entorno.get(clave)!r}")

    servidor = subprocess.Popen(  # noqa: S603
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
        cwd=str(BACKEND),
        env=entorno,
        # ***Y AQUI LA DIFERENCIA***: se captura, en vez de tirarla.
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    listo = False
    for intento in range(60):
        try:
            with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                listo = True
                break
        except (urllib.error.URLError, OSError):
            if servidor.poll() is not None:
                print(f"  ***el servidor MURIO, codigo {servidor.returncode}, en el intento {intento + 1}***")
                break
            time.sleep(0.5)

    print(f"  ¿respondio `/api/interfaz`?: {listo}")
    if servidor.poll() is None:
        servidor.terminate()
        try:
            salida, _ = servidor.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            servidor.kill()
            salida, _ = servidor.communicate()
    else:
        salida = servidor.stdout.read() if servidor.stdout else ""

    print("  ================ SU SALIDA ================")
    print(salida[-4000:] if salida and salida.strip() else "  (vacia)")
