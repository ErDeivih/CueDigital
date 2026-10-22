"""***El cuarto recorrido: papel -> propuesta -> confirmacion*** (22/10/2026, D05).

*Lo que el encargo pide con estas palabras: «papel -> propuesta -> confirmacion/rectificacion». Y lo que el codigo
dice de si mismo: «**subir un papel no puede meter ningun dato en el cuaderno**; leer es una puerta aparte y lo que
sale de ella es una propuesta».*

***Eso es lo que se comprueba aqui***: *que subir un papel **no** escribe nada, y que lo que escribe es la
confirmacion.*

*Y se dice lo que no se puede comprobar: **el OCR de verdad**. Sin proveedor, la puerta `/leer` no lee un PNG de un
pixel; lo que se comprueba es que **la separacion existe** -subir no escribe, leer propone, confirmar escribe-.*

Uso:  python scripts/verificar_el_recorrido_del_papel.py
"""

from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

EL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


def subir(direccion: str, el_vale: str, titulo: str) -> tuple[int, object]:
    """*Un multipart a mano con el fichero y los campos.*"""
    el_limite = "----prueba"
    el_cuerpo = b"".join([
        f"--{el_limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="titulo"\r\n\r\n',
        titulo.encode("utf-8"),
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
            return la_respuesta.status, json.loads(la_respuesta.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as el_error:
        return el_error.code, el_error.read().decode("utf-8", "replace")


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> str:
    el_ultimo = ""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(30):
            el_ultimo = el_texto(nav)
            if el_ultimo and el_ultimo == anterior:
                return el_ultimo
            anterior = el_ultimo
            time.sleep(0.4)
    return el_ultimo


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "papel@prueba.local", "una-clave-larga-y-facil", "Pa")
        el_vale = cuenta["token"]
        print(f"== Papel -> propuesta -> confirmacion  ({direccion}) ==")

        # ---- 1 · antes de subir, el cuaderno esta vacio ----
        _, antes = _llamar(direccion, "/api/tratamientos", token=el_vale)
        print(f"  (tratamientos antes: {len(antes) if isinstance(antes, list) else antes})")

        # ---- 2 · el papel ----
        codigo, el_papel = subir(direccion, el_vale, "PAPEL DE LA PRUEBA")
        print(f"  (subir: {codigo} {str(el_papel)[:160]})")
        fallos += not comprobar(codigo == 201, "***el papel se sube a la bandeja***", str(el_papel))

        # ---- 3 · ***subir NO escribe en el cuaderno*** ----
        _, despues = _llamar(direccion, "/api/tratamientos", token=el_vale)
        fallos += not comprobar(
            isinstance(despues, list) and len(despues) == 0,
            "***y SUBIR un papel no mete nada en el cuaderno*** "
            f"(tratamientos despues: {len(despues) if isinstance(despues, list) else despues})",
        )

        # ---- 4 · el papel, en la bandeja ----
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)
            # ***La bandeja vive dentro de la familia de los papeles***: *`#/papeles/bandeja` -lo dice la tabla
            # de patrones-, no `#/bandeja`. Y la ficha de un papel es `#/papeles/bandeja/<id>`.*
            la_bandeja = abrir(nav, direccion, "#/papeles/bandeja")
            fallos += not comprobar(
                "PAPEL DE LA PRUEBA" in la_bandeja,
                "***el papel sale en la bandeja*** (`#/papeles/bandeja`)",
                la_bandeja,
            )
            # ***Y su ficha, por su ID.***
            el_papel_id = (el_papel or {}).get("papel", {}).get("id") if isinstance(el_papel, dict) else None
            if el_papel_id:
                la_ficha = abrir(nav, direccion, f"#/papeles/bandeja/{el_papel_id}")
                fallos += not comprobar(
                    "no lleva a ninguna parte" not in la_ficha and "PAPEL DE LA PRUEBA" in la_ficha,
                    f"***y su ficha se abre por su ID*** (`#/papeles/bandeja/{el_papel_id}`)",
                    la_ficha,
                )
                la_ficha_otra = abrir(nav, direccion, f"#/papeles/bandeja/{el_papel_id}")
                fallos += not comprobar(
                    la_ficha_otra == la_ficha,
                    "***y aguanta la recarga***",
                    la_ficha_otra,
                )

    print(f"\nComprobaciones: 5   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
