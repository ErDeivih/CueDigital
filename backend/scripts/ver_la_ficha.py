"""¿Cómo se abre el historial de una tierra a 1440 px? (07/10/2026)

La comprobación del recorrido se paró aquí: `tierra-historia` existe 64 veces y **no se ve ninguna**, y
`elegir-fila` también está. Esto mira qué se ve de verdad en la tabla de tierras y qué pasa al pulsarlo.

Uso:  python ver_la_ficha.py http://127.0.0.1:8029
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
escenario = preparar(DIRECCION)
print(f"tierra de la prueba: {escenario.tierras[0].alias}")

with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.8)
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=12)
    visto = nav.evaluar(
        """(() => {
            const salida = {};
            for (const el of document.querySelectorAll('#pantalla [data-accion]')) {
                const accion = el.dataset.accion;
                const visible = el.checkVisibility({checkVisibilityCSS: true});
                if (!salida[accion]) salida[accion] = {cuantos: 0, visibles: 0, ejemplo: ''};
                salida[accion].cuantos += 1;
                if (visible) {
                    salida[accion].visibles += 1;
                    if (!salida[accion].ejemplo) salida[accion].ejemplo = (el.innerText || '').trim().slice(0, 40);
                }
            }
            return salida;
        })()"""
    )
    print("\na 1440 px, en la lista de tierras:")
    for accion, datos in sorted(visto.items()):
        print(f"  {accion:26} {datos['cuantos']:3} en total · {datos['visibles']:3} visibles · «{datos['ejemplo']}»")

    # Y qué pasa al pulsar lo que sí se ve para abrir una tierra.
    for selector in ("[data-accion='elegir-fila']", "[data-accion='tierra-historia']"):
        hay_visible = nav.evaluar(
            f"[...document.querySelectorAll({json.dumps(selector)})]"
            ".some((e) => e.checkVisibility({checkVisibilityCSS: true}))"
        )
        print(f"\n¿se ve algún {selector}? {hay_visible}")
        if not hay_visible:
            continue
        nav.pulsar(selector)
        nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=10)
        despues = nav.evaluar(
            """(() => ({
                hash: location.hash,
                h1: (document.querySelector('#pantalla h1') || {}).innerText || '',
                acciones: [...new Set([...document.querySelectorAll('#pantalla [data-accion]')]
                    .map((e) => e.dataset.accion))].slice(0, 16),
                texto: (document.querySelector('#pantalla').innerText || '').replace(/\\n+/g, ' | ').slice(0, 160),
            }))()"""
        )
        print(f"  tras pulsarlo: hash={despues['hash']}")
        print(f"  h1={despues['h1']}")
        print(f"  acciones={despues['acciones']}")
        print(f"  texto={despues['texto']}")
        nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.4)
        nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=10)
