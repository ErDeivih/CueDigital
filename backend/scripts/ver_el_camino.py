"""¿Cuál es el camino de verdad de Inicio a la ficha de una tierra? (07/10/2026)

La comprobación del recorrido se rompió aquí: al pulsar «mis-cosas» en el panel, la dirección **no cambia**
(sigue en `#/`), así que el camino no es el que suponía el guion. Esto lo mide: qué hay en pantalla después
de cada pulsación, y cómo se abre una tierra en la lista.

Uso:  python ver_el_camino.py http://127.0.0.1:8029
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
print(f"tierra de la prueba: {escenario.tierras[0].alias} (id {escenario.tierras[0].id})")


def retrato(nav: NavegadorDeVerdad, etiqueta: str) -> None:
    datos = nav.evaluar(
        """(() => ({
            hash: location.hash,
            h1: (document.querySelector('#pantalla h1') || {}).innerText || '',
            acciones: [...new Set([...document.querySelectorAll('#pantalla [data-accion]')]
                .map((e) => e.dataset.accion))],
            campos: [...new Set([...document.querySelectorAll('#pantalla input, #pantalla select')]
                .map((e) => e.id || e.name || e.type))],
            texto: (document.querySelector('#pantalla').innerText || '').replace(/\\n+/g, ' | ').slice(0, 200),
        }))()"""
    )
    print(f"\n=== {etiqueta}")
    print(f"  hash: {datos['hash']}")
    print(f"  h1: {datos['h1']}")
    print(f"  acciones: {datos['acciones']}")
    print(f"  campos: {datos['campos']}")
    print(f"  texto: {datos['texto']}")


with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    nav.abrir(f"{DIRECCION}/#/", esperar=2.0)
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=12)
    retrato(nav, "Inicio")

    nav.pulsar('[data-accion="mis-cosas"]')
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=12)
    nav.esperar("Boolean(document.querySelector('#buscar_tierra_mis_cosas'))", segundos=6)
    retrato(nav, "después de pulsar «mis-cosas»")

    # Y la pantalla de tierras por su dirección, para ver cómo se abre una tierra.
    nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.6)
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=12)
    retrato(nav, "la pantalla de tierras, por su dirección")
    filas = nav.evaluar(
        """(() => {
            const botones = [...document.querySelectorAll('#pantalla [data-accion]')];
            const cuantos = {};
            for (const b of botones) cuantos[b.dataset.accion] = (cuantos[b.dataset.accion] || 0) + 1;
            return cuantos;
        })()"""
    )
    print(f"  cuántos botones de cada acción: {filas}")
