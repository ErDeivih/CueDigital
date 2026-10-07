"""Capturas de pantalla para **mirar** lo que se ha cambiado (06/10/2026; corregido el 07/10/2026).

Los tests dicen que el HTML sale y los guiones dicen que el foco se mueve; esto sirve para lo que no
sustituye ninguno de los dos: **ver** la pantalla. Guarda un PNG por pantalla y por ancho.

## La trampa que tenía, y por qué queda escrita aquí

La primera versión de este guion **guardaba la pantalla de entrar doce veces y decía que eran cuatro
pantallas**. Lo encontró David comparando las huellas SHA-256: las cuatro rutas de cada ancho salían
idénticas. Eran dos fallos encadenados, y los dos son los mismos que ya habían costado una vuelta en los
otros guiones:

  1. **El token se ponía después de cargar la página**, así que la primera carga era sin sesión; y navegar de
     `/` a `/#/cuaderno` **solo cambia la almohadilla**, así que el documento **no se recarga** y la
     aplicación se queda con lo que tiene en memoria (la pantalla de entrar). Se arregla como en
     `comprobar_en_un_navegador.py`: el token entra en **cada documento nuevo**
     (`Page.addScriptToEvaluateOnNewDocument`) y cada ruta se abre pasando por `about:blank`.
  2. **No se comprobaba nada de lo capturado.** Ahora cada captura tiene que llevar **un texto que solo esté
     en esa pantalla**, y si no lo lleva el guion **falla y lo dice**: una captura de la pantalla de entrar
     no acredita la revisión de una página de dentro.

Uso:
    python scripts/mirar_pantallas.py http://127.0.0.1:8023 [carpeta]
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8023"
CARPETA = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\David\AppData\Local\Temp\cd-ui")

# Cada pantalla con **un texto que solo está en ella**: sin eso, una captura de la pantalla de entrar pasaría
# por buena, que es exactamente lo que pasó. En el inicio se aceptan dos, porque **el inicio no es el mismo
# según el ancho**: en el móvil es la pantalla de siempre («Hola») y a partir de 64 rem es el panel de mando.
PANTALLAS = [
    ("inicio", "/#/", ("Hola", "Panel de mando")),
    ("cuaderno", "/#/cuaderno", ("cuaderno",)),
    ("tierras", "/#/tierras", ("parcela",)),
    ("cuentas", "/#/cuentas", ("cuenta",)),
]
ANCHOS = [(390, 844), (712, 900), (1024, 900), (1440, 900)]


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
fallos: list[str] = []
with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    # El token, en **cada documento nuevo**, antes de que corra la aplicación: así cualquier navegación
    # —y hay una por captura— empieza con sesión.
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
    )

    for nombre, ruta, contenidos in PANTALLAS:
        for ancho, alto in ANCHOS:
            nav.medir(ancho, alto)
            # Por `about:blank`: cambiar solo la almohadilla NO recarga la página.
            nav.orden("Page.navigate", {"url": "about:blank"})
            nav.abrir(f"{DIRECCION}{ruta}", esperar=1.5)
            titulo = nav.evaluar("document.title")
            # **El texto de la pantalla, no el de la página entera**: en el ordenador, el armazón (el menú
            # con sus 21 renglones) va antes en el DOM, así que los primeros 500 caracteres del cuerpo son
            # el menú y la comprobación no veía el texto de la pantalla que se estaba capturando.
            texto = nav.evaluar("(document.querySelector('#pantalla') || document.body).innerText.slice(0, 600)") or ""
            dentro = any(contiene.lower() in texto.lower() for contiene in contenidos)
            if not dentro:
                fallos.append(f"{nombre} a {ancho}: la captura no es de esa pantalla (título «{titulo}»)")
            (CARPETA / f"{nombre}-{ancho}.png").write_bytes(
                base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
            )
            cabe = nav.evaluar(
                "(() => ({ ancho: document.documentElement.scrollWidth, cabe: window.innerWidth,"
                " cuerpo: getComputedStyle(document.body).fontSize }))()"
            )
            print(
                f"{nombre} a {ancho}: título «{titulo}» · {cabe['ancho']} px en {cabe['cabe']}"
                f" · cuerpo {cabe['cuerpo']} · {'OK' if dentro else 'NO ES ESA PANTALLA'}"
            )

    # Y el anillo de foco, medido **tabulando de verdad**: un `elemento.focus()` desde el guion no activa
    # `:focus-visible` (el navegador no sabe si vienes del teclado), así que hay que mandar la tecla. Es la
    # misma razón por la que el teclado se comprueba con CDP y no con `dispatchEvent`.
    nav.medir(1440, 900)
    nav.orden("Page.navigate", {"url": "about:blank"})
    nav.abrir(f"{DIRECCION}/#/cuentas", esperar=1.5)
    print("\nEl foco, tabulando de verdad:")
    nav.evaluar("(() => { document.body.focus(); return null; })()")
    for paso in range(6):
        nav.tecla("Tab")
        quien = nav.evaluar(
            """(() => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const e = getComputedStyle(el);
                return JSON.stringify({
                  quien: el.tagName + (el.dataset && el.dataset.accion ? '[' + el.dataset.accion + ']' : ''),
                  contorno: e.outline,
                  separacion: e.outlineOffset,
                });
            })()"""
        )
        if quien:
            print(f"  Tab {paso + 1}: {quien}")

print(f"\nCapturas en {CARPETA}")
if fallos:
    print("FALLOS:")
    for fallo in fallos:
        print(f"  · {fallo}")
    raise SystemExit(1)
print("Todas las capturas son de la pantalla que dicen ser.")
