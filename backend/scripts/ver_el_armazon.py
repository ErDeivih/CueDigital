"""¿Qué pasa con el armazón a cada ancho? (07/10/2026)

El encargo pide «en cualquier ancho intermedio, Menú siempre ofrece todas las secciones, incluidas Cuentas
y Normativa». Antes de tocar nada hay que saber qué hay hoy: si el menú se ve, si está oculto, y si sus
renglones se pueden alcanzar con el teclado.

Uso:  python ver_el_armazon.py http://127.0.0.1:8025
"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8025"


def una_cuenta() -> str:
    with httpx.Client(base_url=DIRECCION, timeout=30.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba del armazón",
                "correo": "armazon@ejemplo.test",
                "clave": "una-clave-larga",
                "explotacion": {"nombre": "La finca del armazón", "nif": "12345678Z"},
            },
        )
        if respuesta.status_code == 409:
            respuesta = cliente.post(
                "/api/cuenta/entrar", json={"correo": "armazon@ejemplo.test", "clave": "una-clave-larga"}
            )
        respuesta.raise_for_status()
        return respuesta.json()["token"]


with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(una_cuenta()) + ");"},
    )
    for ancho in (390, 712, 1024, 1440):
        nav.medir(ancho, 900)
        nav.orden("Page.navigate", {"url": "about:blank"})
        nav.abrir(f"{DIRECCION}/#/", esperar=1.6)
        datos = nav.evaluar(
            """(() => {
                const marco = document.getElementById('marco');
                const menu = document.querySelector('#marco .menu');
                const barra = document.querySelector('#marco .barra');
                const enlaces = [...document.querySelectorAll('#marco .menu-enlace')];
                const visibles = enlaces.filter((e) => e.checkVisibility({checkVisibilityCSS: true}));
                const rect = (el) => { if (!el) return null; const c = el.getBoundingClientRect();
                    return {x: Math.round(c.x), y: Math.round(c.y), w: Math.round(c.width), h: Math.round(c.height)}; };
                return {
                    marco: rect(marco), menu: rect(menu), barra: rect(barra),
                    enlaces: enlaces.length,
                    visibles: visibles.length,
                    grupos: [...document.querySelectorAll('#marco .menu-grupo-nombre')]
                        .map((g) => g.innerText.trim()),
                    hayBotonAbrir: Boolean(document.querySelector('[data-accion="menu-abrir"]')),
                };
            })()"""
        )
        print(f"\n=== a {ancho} px (menú cerrado)")
        print(f"  #marco {datos['marco']} · .menu {datos['menu']}")
        print(f"  renglones: {datos['enlaces']} (visibles {datos['visibles']}) · grupos {datos['grupos']}")
        print(f"  ¿hay botón de abrir el menú? {datos['hayBotonAbrir']}")
        # **Y ahora se abre pulsando el botón de verdad**, que es lo que hace el agricultor en el móvil.
        if datos["hayBotonAbrir"] and datos["visibles"] == 0:
            nav.pulsar('[data-accion="menu-abrir"]')
            nav.esperar(
                "document.querySelectorAll('#marco .menu-enlace').length === "
                "document.querySelectorAll('#marco .menu-enlace')"
                ".length && [...document.querySelectorAll('#marco .menu-enlace')]"
                ".every((e) => e.checkVisibility({checkVisibilityCSS: true}))",
                segundos=5,
            )
            abierto = nav.evaluar(
                """(() => ({
                    visibles: [...document.querySelectorAll('#marco .menu-enlace')]
                        .filter((e) => e.checkVisibility({checkVisibilityCSS: true})).length,
                    grupos: [...document.querySelectorAll('#marco .menu-grupo-nombre')]
                        .map((g) => g.innerText.trim()),
                    hayCerrar: Boolean(document.querySelector('[data-accion="menu-cerrar"]')),
                    cuentas: Boolean(document.querySelector('#menu-cuentas')),
                }))()"""
            )
            print(f"  MENÚ ABIERTO: renglones visibles {abierto['visibles']} · grupos {abierto['grupos']}")
            print(f"    ¿botón de cerrar? {abierto['hayCerrar']} · ¿el renglón de cuentas está? {abierto['cuentas']}")
            # ¿Se llega a las cuentas **tabulando**? Es la mitad del encargo a 712 px.
            nav.evaluar("(() => { document.querySelector('[data-accion=\"menu-abrir\"]').focus(); return null; })()")
            for paso in range(1, 40):
                nav.tecla("Tab")
                accion = nav.evaluar(
                    "(() => { const e = document.activeElement; return e && e.dataset ? (e.dataset.accion || '') : ''; })()"
                )
                if accion == "gastos-ver":
                    print(f"    se llega a CUENTAS tabulando: {paso} pulsaciones")
                    break
            else:
                print("    NO se llega a CUENTAS tabulando")
            nav.pulsar('[data-accion="menu-cerrar"]')
            cerrado = nav.evaluar(
                "[...document.querySelectorAll('#marco .menu-enlace')]"
                ".filter((e) => e.checkVisibility({checkVisibilityCSS: true})).length"
            )
            print(f"  y al cerrarlo: renglones visibles {cerrado}")
