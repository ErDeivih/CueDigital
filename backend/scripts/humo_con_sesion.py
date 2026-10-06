"""Comprueba que la aplicación arranca **con sesión** después de los cambios de descargas (06/10/2026).

Los cuatro arreglos del cuaderno (`conLaCampana`) tocan el arranque de la aplicación: si `estado.campana`
no está cuando se piden, la ruta tiene que salir igual que antes. Esto abre el navegador de verdad, entra
con una cuenta y mira que las pantallas se dibujen y que no haya errores de JavaScript.

Uso:  python scripts/humo_con_sesion.py http://127.0.0.1:8013
"""

from __future__ import annotations

import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8013"


def una_cuenta() -> str:
    with httpx.Client(base_url=DIRECCION, timeout=30.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba de las descargas",
                "correo": "descargas@ejemplo.test",
                "clave": "una-clave-larga",
                "explotacion": {"nombre": "La finca de las descargas", "nif": "12345678Z"},
            },
        )
        if respuesta.status_code == 409:
            respuesta = cliente.post(
                "/api/cuenta/entrar",
                json={"correo": "descargas@ejemplo.test", "clave": "una-clave-larga"},
            )
        respuesta.raise_for_status()
        return respuesta.json()["token"]


token = una_cuenta()
with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.abrir(f"{DIRECCION}/")
    # Un `return` suelto no vale en `Runtime.evaluate` (es un `SyntaxError: Illegal return statement`): se
    # envuelve en una función, que es la forma que usa el resto de este guion.
    nav.evaluar(
        f"(() => {{ localStorage.setItem('cuedigital.token', {token!r}); return null; }})()"
    )
    nav.abrir(f"{DIRECCION}/#/mi-cuaderno")
    print("titulo:", nav.evaluar("document.title"))
    print("hay pantalla:", nav.evaluar("Boolean(document.querySelector('#pantalla'))"))
    print(
        "el cuaderno se ha dibujado:",
        nav.evaluar("document.body.innerText.includes('cuaderno')"),
    )
    # Los errores de JavaScript se cazan escuchando el suceso, que es lo que dejaría la pantalla a medias.
    nav.evaluar(
        "(() => { window.__errores = []; window.addEventListener('error', (e) => window.__errores.push(String(e.message))); return null; })()"
    )
    nav.abrir(f"{DIRECCION}/#/cuaderno-de-la-junta")
    print("junta:", nav.evaluar("document.body.innerText.slice(0, 80).replace(/\\n/g, ' | ')"))
    print("errores:", nav.evaluar("JSON.stringify(window.__errores || [])"))

    # **Y sin sesión, una dirección de dentro no pinta la pantalla: pide entrar** (06/10/2026). Antes la
    # pintaba (vacía, con un error de permiso detrás) porque el `popstate` no miraba si había token; solo
    # lo miraba el arranque.
    nav.evaluar("(() => { localStorage.removeItem('cuedigital.token'); return null; })()")
    nav.abrir(f"{DIRECCION}/#/tierras")
    texto = nav.evaluar("document.body.innerText.slice(0, 120).replace(/\\n/g, ' | ')")
    print("sin sesion, #/tierras:", texto)
    print("pide entrar:", nav.evaluar("Boolean(document.querySelector('#correo'))"))
    print("errores:", nav.evaluar("JSON.stringify(window.__errores || [])"))
