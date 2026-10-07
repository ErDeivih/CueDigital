"""¿Cuántas teclas hay que dar para llegar al primer campo, sin sesión? (H2 del 06/10/2026)

Se medía que hacían falta **24 pulsaciones de Tab** para llegar al correo, porque el menú de módulos de la
sesión anterior se quedaba pintado y en el tabulador. Esto lo cuenta, entrando como entra el agricultor
(por `/`) y también por la dirección que usaban los guiones (`#/entrar`).

Uso:  python scripts/contar_tabulaciones.py http://127.0.0.1:8023
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8023"


def cuantas_hasta_el_correo(nav, url: str) -> tuple[int | None, str]:
    nav.abrir(url, esperar=1.0)
    # Sin sesión: el token se quita **antes** de cargar, en la propia página.
    nav.evaluar("(() => { localStorage.removeItem('cuedigital.token'); return null; })()")
    nav.abrir(url, esperar=1.2)
    nav.evaluar("(() => { document.body.focus(); return null; })()")
    for pulsaciones in range(1, 40):
        nav.tecla("Tab")
        quien = nav.evaluar(
            "(() => { const e = document.activeElement; if (!e) return '';"
            " return (e.id || '') + '|' + (e.dataset && e.dataset.accion ? e.dataset.accion : '') + '|' + e.tagName; })()"
        )
        if quien.startswith("correo|"):
            return pulsaciones, quien
    return None, ""


with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    for ruta in ("/", "/#/entrar", "/#/cuentas"):
        cuantas, quien = cuantas_hasta_el_correo(nav, f"{DIRECCION}{ruta}")
        print(f"entrando por {ruta}: {cuantas if cuantas is not None else 'NO SE LLEGA'} pulsaciones"
              f" hasta el campo del correo ({quien})")
    # Y el menú de la sesión anterior no puede quedar en el tabulador.
    print("el menú de módulos está en el documento:",
          nav.evaluar("Boolean(document.querySelector('#menu-cuentas'))"))
