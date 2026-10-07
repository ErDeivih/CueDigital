"""¿Qué pasa al pulsar «decir el cultivo» desde la ficha de una tierra? (07/10/2026)

Es la medición que quedó escrita en `docs/ESTADO_DEL_REDISENO.md`: **antes de tocar nada**, ver en qué
pantalla se queda. Se entra a la ficha **por su dirección** (`#/tierras/<id>/historial`), que es donde el
defecto se esconde; por la lista puede que no aparezca.

Uso:  python medir_el_cultivo_desde_la_ficha.py http://127.0.0.1:8035
"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8035"
escenario = preparar(DIRECCION)
la_tierra = escenario.tierras[0]
print(f"tierra: «{la_tierra.alias}» (id {la_tierra.id})")

with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    # **Por su dirección**, no por la lista.
    nav.abrir(f"{DIRECCION}/#/tierras/{la_tierra.id}/historial", esperar=2.0)
    nav.esperar("Boolean(document.querySelector(\"[data-accion='trabajo-planificar']\"))", segundos=12)
    print(f"  en la ficha: {nav.evaluar('location.hash')}")
    hay_boton = nav.evaluar(
        "Boolean(document.querySelector(\"[data-accion='cultivo-decir']\"))"
    )
    print(f"  ¿hay botón de decir el cultivo? {bool(hay_boton)}")
    # Se pulsa de verdad y se mira dónde acaba. **El botón se inyecta** porque ahora la ficha no lo tiene
    # (se quitó en la ronda 15 justo porque no funcionaba): lo que se está midiendo es la **acción**
    # `cultivo-decir` lanzada desde la ficha, con un clic de ratón de verdad sobre un elemento de verdad.
    nav.evaluar(
        "(() => { const b = document.createElement('button');"
        " b.dataset.accion = 'cultivo-decir';"
        f" b.dataset.id = '{la_tierra.id}'; b.textContent = 'decir el cultivo (prueba)';"
        " document.querySelector('#pantalla').appendChild(b); return null; })()"
    )
    nav.pulsar("#pantalla [data-accion='cultivo-decir']")
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=10)
    despues = nav.evaluar(
        """(() => ({
            hash: location.hash,
            h1: (document.querySelector('#pantalla h1') || {}).innerText || '',
            acciones: [...new Set([...document.querySelectorAll('#pantalla [data-accion]')]
                .map((e) => e.dataset.accion))],
            campos: document.querySelectorAll('#pantalla input, #pantalla select, #pantalla textarea').length,
            texto: (document.querySelector('#pantalla').innerText || '').replace(/\\n+/g, ' | ').slice(0, 180),
        }))()"""
    )
    print("\n=== después de pulsar «decir el cultivo» desde la ficha")
    print(f"  dirección: {despues['hash']}")
    print(f"  h1: {despues['h1']}")
    print(f"  acciones: {despues['acciones']}")
    print(f"  campos de formulario: {despues['campos']}")
    print(f"  texto: {despues['texto']}")
    # Y lo mismo entrando por la lista, para comparar los dos caminos.
    nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.8)
    nav.esperar("Boolean(document.querySelector('#buscar_tierra_mis_cosas'))", segundos=12)
    nav.pulsar("[data-accion='cultivo-decir']")
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=10)
    por_la_lista = nav.evaluar(
        "(() => ({ hash: location.hash, h1: (document.querySelector('#pantalla h1') || {}).innerText || '',"
        " campos: document.querySelectorAll('#pantalla input, #pantalla select, #pantalla textarea').length }))()"
    )
    print("\n=== lo mismo entrando por la LISTA (para comparar)")
    print(f"  dirección: {por_la_lista['hash']} · h1: {por_la_lista['h1']} · campos: {por_la_lista['campos']}")
