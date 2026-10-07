"""Capturas de pantalla para **mirar** lo que se ha cambiado (06/10/2026).

Los tests dicen que el HTML sale y los guiones dicen que el foco se mueve; esto sirve para lo que no
sustituye ninguno de los dos: **ver** la pantalla. Guarda un PNG por pantalla y por ancho en la carpeta que
se le diga, y de paso mide cuatro cosas del sistema de diseño que se pueden medir sin ojos (el anillo de
foco, los tamaños de letra de los tres niveles y el ancho de la página).

Uso:
    python scripts/mirar_pantallas.py http://127.0.0.1:8023 [carpeta]
"""

from __future__ import annotations

import base64
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8023"
CARPETA = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\David\AppData\Local\Temp\cd-ui")

PANTALLAS = [
    ("inicio", "/#/"),
    ("cuaderno", "/#/cuaderno"),
    ("tierras", "/#/tierras"),
    ("cuentas", "/#/cuentas"),
]
ANCHOS = [(390, 844), (1024, 900), (1440, 900)]


def una_cuenta() -> str:
    with httpx.Client(base_url=DIRECCION, timeout=30.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba de la mirada",
                "correo": "mirar@ejemplo.test",
                "clave": "una-clave-larga",
                "explotacion": {"nombre": "La finca de la mirada", "nif": "12345678Z"},
            },
        )
        if respuesta.status_code == 409:
            respuesta = cliente.post(
                "/api/cuenta/entrar", json={"correo": "mirar@ejemplo.test", "clave": "una-clave-larga"}
            )
        respuesta.raise_for_status()
        return respuesta.json()["token"]


CARPETA.mkdir(parents=True, exist_ok=True)
token = una_cuenta()
with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.abrir(f"{DIRECCION}/")
    nav.evaluar(f"(() => {{ localStorage.setItem('cuedigital.token', {token!r}); return null; }})()")

    for nombre, ruta in PANTALLAS:
        for ancho, alto in ANCHOS:
            nav.medir(ancho, alto)
            nav.abrir(f"{DIRECCION}{ruta}", esperar=1.2)
            fichero = CARPETA / f"{nombre}-{ancho}.png"
            captura = nav.orden("Page.captureScreenshot", {"format": "png"})
            fichero.write_bytes(base64.b64decode(captura["data"]))
            cabe = nav.evaluar(
                "(() => ({ ancho: document.documentElement.scrollWidth,"
                " cabe: window.innerWidth,"
                " h1: getComputedStyle(document.querySelector('h1') || document.body).fontSize,"
                " h2: getComputedStyle(document.querySelector('h2') || document.body).fontSize,"
                " cuerpo: getComputedStyle(document.body).fontSize }))()"
            )
            print(f"{nombre} a {ancho}: {cabe['ancho']} px de ancho en {cabe['cabe']} | "
                  f"cuerpo {cabe['cuerpo']} · h1 {cabe['h1']} · h2 {cabe['h2']}")

    # Y el anillo de foco, medido **tabulando de verdad**: un `elemento.focus()` desde el guion no activa
    # `:focus-visible` (el navegador no sabe si vienes del teclado), así que lo que hay que mandar es una
    # tecla. Es la misma razón por la que el teclado se comprueba con CDP y no con `dispatchEvent`.
    nav.medir(1440, 900)
    nav.abrir(f"{DIRECCION}/#/cuentas", esperar=1.2)
    print("\nEl foco, tabulando de verdad:")
    nav.evaluar("(() => { document.body.focus(); return null; })()")
    for paso in range(12):
        nav.tecla("Tab")
        quien = nav.evaluar(
            """(() => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const e = getComputedStyle(el);
                return JSON.stringify({
                  quien: el.tagName + (el.dataset && el.dataset.accion ? '[' + el.dataset.accion + ']' : '') + (el.id ? '#' + el.id : ''),
                  contorno: e.outline,
                  separacion: e.outlineOffset,
                  borde: e.borderColor,
                });
            })()"""
        )
        if quien:
            print(f"  Tab {paso + 1}: {quien}")
            if paso >= 5:
                break
print(f"\nCapturas en {CARPETA}")
