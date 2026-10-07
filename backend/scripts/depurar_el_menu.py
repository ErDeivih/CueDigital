"""Depuración: ¿qué pasa al pulsar el botón del menú? (07/10/2026)"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8026"

with httpx.Client(base_url=DIRECCION, timeout=30.0) as cliente:
    respuesta = cliente.post(
        "/api/cuenta/registro",
        json={
            "nombre": "Prueba del menú",
            "correo": "menudep@ejemplo.test",
            "clave": "una-clave-larga",
            "explotacion": {"nombre": "La finca del menú", "nif": "12345678Z"},
        },
    )
    if respuesta.status_code == 409:
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
    nav.abrir(f"{DIRECCION}/#/", esperar=1.8)
    print("antes:", nav.evaluar("document.getElementById('marco').className"))
    print("¿el botón existe y se ve?:", nav.evaluar(
        """(() => { const b = document.querySelector('[data-accion="menu-abrir"]');
            return b ? `sí, visible=${b.checkVisibility({checkVisibilityCSS: true})}` : 'no'; })()"""
    ))
    # Se pulsa por el manejador de verdad (un click de verdad en el centro del botón).
    nav.pulsar('[data-accion="menu-abrir"]')
    print("después de pulsar:", nav.evaluar("document.getElementById('marco').className"))
    print("estado del menú:", nav.evaluar(
        """(() => { const m = document.querySelector('#marco .menu');
            if (!m) return 'no hay menú';
            const e = getComputedStyle(m);
            return JSON.stringify({display: e.display, visibles: [...document.querySelectorAll('#marco .menu-enlace')]
                .filter((x) => x.checkVisibility({checkVisibilityCSS: true})).length}); })()"""
    ))
    # Y ahora se cierra con su botón.
    nav.pulsar('[data-accion="menu-cerrar"]')
    print("después de cerrar:", nav.evaluar("document.getElementById('marco').className"))
    print("renglones visibles al cerrar:", nav.evaluar(
        "[...document.querySelectorAll('#marco .menu-enlace')]"
        ".filter((x) => x.checkVisibility({checkVisibilityCSS: true})).length"
    ))
    print("¿sigue habiendo botón de cerrar?:", nav.evaluar(
        "Boolean(document.querySelector('[data-accion=\"menu-cerrar\"]'))"
    ))
    print("los antepasados del primer renglón:", nav.evaluar(
        """(() => {
            const enlace = document.querySelector('#marco .menu-enlace');
            if (!enlace) return 'no hay ningún renglón';
            const cadena = [];
            let el = enlace;
            while (el && el !== document.documentElement) {
                const e = getComputedStyle(el);
                const caja = el.getBoundingClientRect();
                cadena.push(`${el.tagName}.${el.className || ''}: display=${e.display} vis=${e.visibility}`
                    + ` op=${e.opacity} ${Math.round(caja.width)}x${Math.round(caja.height)}`
                    + ` check=${el.checkVisibility({checkVisibilityCSS: true})}`);
                el = el.parentElement;
            }
            return cadena;
        })()"""
    ))
