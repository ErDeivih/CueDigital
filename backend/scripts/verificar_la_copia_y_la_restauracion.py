"""***Copiar, restaurar en un destino nuevo, y abrir lo que hay dentro*** (22/10/2026, D06).

*El encargo: «restaurar en destino nuevo; abrir documentos y comprobar vinculos/firmas, no solo `quick_check`».*

***Lo que hace***: *levanta un servidor con **datos de verdad** -una cuenta, una tierra y un papel con su fichero-,
**copia** su carpeta de datos, **levanta otro servidor con la copia** -en otro puerto, con otra carpeta-, y comprueba
que **la cuenta entra y los datos estan**.*

*Es la unica forma de saber si una copia sirve: **usarla**.*

Uso:  python scripts/verificar_la_copia_y_la_restauracion.py
"""

from __future__ import annotations

import base64
import json
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

from verificar_los_permisos_por_rol import BACKEND, PYTHON, _llamar, _una_cuenta_nueva, un_puerto_libre  # noqa: E402

EL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def arrancar(la_carpeta: pathlib.Path, el_puerto: int) -> subprocess.Popen:
    el_entorno = dict(os.environ)
    el_entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{la_carpeta / 'cuedigital.db'}"
    el_entorno["CUEDIGITAL_ADJUNTOS"] = str(la_carpeta / "adjuntos")
    el_entorno["CUEDIGITAL_SECRETO"] = "no-es-un-secreto-de-verdad"
    return subprocess.Popen(  # noqa: S603
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(el_puerto)],
        cwd=str(BACKEND),
        env=el_entorno,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def esperar(direccion: str, segundos: float = 60.0) -> bool:
    for _ in range(int(segundos / 0.5)):
        try:
            with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def parar(el_servidor: subprocess.Popen) -> None:
    if el_servidor.poll() is None:
        el_servidor.terminate()
        try:
            el_servidor.wait(timeout=15)
        except subprocess.TimeoutExpired:
            el_servidor.kill()
            el_servidor.wait(timeout=10)


def subir_un_papel(direccion: str, el_vale: str) -> tuple[int, str]:
    el_limite = "----prueba"
    el_cuerpo = b"".join([
        f"--{el_limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="titulo"\r\n\r\n',
        "EL PAPEL DE LA COPIA".encode(),
        b"\r\n",
        f"--{el_limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="fichero"; filename="papel.png"\r\n',
        b"Content-Type: image/png\r\n\r\n",
        EL_PNG,
        b"\r\n",
        f"--{el_limite}--\r\n".encode(),
    ])
    la_peticion = urllib.request.Request(
        f"{direccion}/api/bandeja/subir",
        data=el_cuerpo,
        method="POST",
        headers={
            "Authorization": f"Bearer {el_vale}",
            "Content-Type": f"multipart/form-data; boundary={el_limite}",
        },
    )
    try:
        with urllib.request.urlopen(la_peticion, timeout=30) as la_respuesta:
            return la_respuesta.status, la_respuesta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as el_error:
        return el_error.code, el_error.read().decode("utf-8", "replace")


def main() -> int:
    fallos = 0
    la_carpeta = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital-copia-"))
    la_restaurada = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital-restaurada-"))
    el_servidor = None
    el_restaurado = None
    try:
        # ---- 1 · un servidor con datos ----
        el_puerto = un_puerto_libre()
        la_direccion = f"http://127.0.0.1:{el_puerto}"
        el_servidor = arrancar(la_carpeta, el_puerto)
        if not esperar(la_direccion):
            print("  ***el servidor no arranca***")
            return 1
        cuenta = _una_cuenta_nueva(la_direccion, "copia@prueba.local", "una-clave-larga-y-facil", "Co")
        _, la_tierra = _llamar(
            la_direccion,
            "/api/parcelas",
            token=cuenta["token"],
            metodo="POST",
            cuerpo={"alias": "LA TIERRA DE LA COPIA", "ref_sigpac": "47-999-0-0-1", "superficie_ha": 1.0},
        )
        codigo, el_papel = subir_un_papel(la_direccion, cuenta["token"])
        print(f"== Un servidor con datos  ({la_direccion}) ==")
        print(f"  (la tierra: {str(la_tierra)[:60]} · el papel: {codigo})")
        fallos += not comprobar(codigo == 201 and isinstance(la_tierra, dict), "***hay datos que copiar***")

        # ---- 2 · se copia ----
        parar(el_servidor)
        el_servidor = None
        la_copia = la_carpeta.parent / (la_carpeta.name + "-copia")
        if la_copia.exists():
            shutil.rmtree(la_copia, ignore_errors=True)
        la_hecha = subprocess.run(  # noqa: S603
            [str(PYTHON), "scripts/copiar_la_base.py", "--origen", str(la_carpeta), "--destino", str(la_copia)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print(f"  (copiar: codigo {la_hecha.returncode}) {lo_que_dijo(la_hecha.stdout)[:200]}")
        fallos += not comprobar(la_hecha.returncode == 0, "***la copia se hace***", la_hecha.stdout + la_hecha.stderr)

        # ---- 3 · se comprueba la copia ----
        la_comprobada = subprocess.run(  # noqa: S603
            [str(PYTHON), "scripts/copiar_la_base.py", "--comprobar", str(la_copia)],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print(f"  (comprobar: codigo {la_comprobada.returncode}) {lo_que_dijo(la_comprobada.stdout)[:220]}")
        fallos += not comprobar(
            la_comprobada.returncode == 0,
            "***y la copia se comprueba: integridad y documentos***",
            la_comprobada.stdout + la_comprobada.stderr,
        )

        # ---- 4 · ***se restaura en un destino NUEVO y se usa*** ----
        shutil.copytree(la_copia, la_restaurada, dirs_exist_ok=True)
        el_puerto_restaurado = un_puerto_libre()
        la_direccion_restaurada = f"http://127.0.0.1:{el_puerto_restaurado}"
        el_restaurado = arrancar(la_restaurada, el_puerto_restaurado)
        if not esperar(la_direccion_restaurada):
            print("  ***el servidor restaurado no arranca***")
            return 1
        print(f"== Y se restaura en un destino nuevo  ({la_direccion_restaurada}) ==")
        # *La cuenta de antes entra, con la misma clave.*
        codigo, el_yo = _llamar(la_direccion_restaurada, "/api/cuenta/yo", token=cuenta["token"])
        fallos += not comprobar(
            codigo == 200,
            "***la cuenta de la copia ENTRA en el servidor restaurado***",
            str(el_yo),
        )
        # *Y la tierra y el papel estan.*
        _, las_tierras = _llamar(la_direccion_restaurada, "/api/parcelas", token=cuenta["token"])
        fallos += not comprobar(
            isinstance(las_tierras, list) and any("LA TIERRA DE LA COPIA" in str(t) for t in las_tierras),
            "***y la tierra esta***",
            str(las_tierras)[:200],
        )
        _, la_bandeja = _llamar(la_direccion_restaurada, "/api/bandeja?estado=todos", token=cuenta["token"])
        fallos += not comprobar(
            "EL PAPEL DE LA COPIA" in str(la_bandeja),
            "***y el papel esta***",
            str(la_bandeja)[:200],
        )

    finally:
        if el_servidor is not None:
            parar(el_servidor)
        if el_restaurado is not None:
            parar(el_restaurado)
        shutil.rmtree(la_carpeta, ignore_errors=True)
        shutil.rmtree(la_restaurada, ignore_errors=True)
        shutil.rmtree(la_carpeta.parent / (la_carpeta.name + "-copia"), ignore_errors=True)

    print(f"\nComprobaciones: 5   Fallos: {fallos}")
    return 1 if fallos else 0


def lo_que_dijo(el_texto: str) -> str:
    return " ".join((el_texto or "").split())


if __name__ == "__main__":
    raise SystemExit(main())
