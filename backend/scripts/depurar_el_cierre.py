"""¿Cierra el menú su botón? (07/10/2026)"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8026"

with httpx.Client(base_url=D, timeout=30.0) as cliente:
    respuesta = cliente.post(
        "/api/cuenta/entrar", json={"correo": "menudep@ejemplo.test", "clave": "una-clave-larga"}
    )
    token = respuesta.json()["token"]

with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
    )
    nav.medir(712, 900)
    nav.abrir(f"{D}/#/", esperar=1.6)
    nav.pulsar('[data-accion="menu-abrir"]')
    print("abierto:", nav.evaluar("document.getElementById('marco').className"))
    print("visibles:", nav.evaluar(
        "[...document.querySelectorAll('#marco .menu-enlace')]"
        ".filter((x) => x.checkVisibility({checkVisibilityCSS: true})).length"
    ))
    # Un click del DOM, que dispara el manejador delegado sin depender de las coordenadas.
    nav.evaluar(
        "(() => { document.querySelector('[data-accion=\"menu-cerrar\"]').click(); return null; })()"
    )
    print("tras click() del DOM:", nav.evaluar("document.getElementById('marco').className"))
    print("visibles:", nav.evaluar(
        "[...document.querySelectorAll('#marco .menu-enlace')]"
        ".filter((x) => x.checkVisibility({checkVisibilityCSS: true})).length"
    ))
