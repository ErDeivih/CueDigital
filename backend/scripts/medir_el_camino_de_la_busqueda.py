"""¿Funciona el camino de la búsqueda? Se mide **sin puerta**, inyectando el cuadro y el botón.

Es la comprobación que decidió el caso del cultivo (07/10/2026) y la que hay que hacer aquí: el defecto que
se vio al intentar la dirección fue «pulsar BUSCAR no enseña los grupos», y la sospecha es que **el clic no
llegue al botón** (esa casa ya lo ha visto dos veces). Esto lo separa:

  1. se abre una pantalla cualquiera (las tierras);
  2. se **inyectan** en ella el cuadro (`#buscar_global`) y el botón (`data-accion="buscar"`), que son los
     que pinta la pantalla de la búsqueda — así se prueba el camino **sin necesitar la puerta**;
  3. se escribe la tierra de la prueba y **se pulsa con un clic de verdad**;
  4. se dice dónde acaba, qué acciones ofrece la pantalla y si salen los grupos.

Si los grupos salen, el camino está bien y lo que fallaba era **dónde aterrizaba el clic** (un problema del
guion, como el del cultivo). Si no salen, el defecto está en la pantalla y hay que mirarla.

Uso:  python medir_el_camino_de_la_busqueda.py http://127.0.0.1:8038
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8038"
escenario = preparar(DIRECCION)
la_tierra = escenario.tierras[0]
print(f"tierra: «{la_tierra.alias}»")

with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.8)
    nav.esperar("Boolean(document.querySelector('#buscar_tierra_mis_cosas'))", segundos=12)

    # 2. Se inyectan el cuadro y el botón **igual que los pinta la pantalla de la búsqueda**.
    nav.evaluar(
        "(() => {"
        " const caja = document.createElement('input');"
        " caja.id = 'buscar_global';"
        " caja.type = 'search';"
        f" caja.value = {json.dumps(la_tierra.alias[:24])};"
        " const boton = document.createElement('button');"
        " boton.dataset.accion = 'buscar';"
        " boton.textContent = 'BUSCAR';"
        " const donde = document.querySelector('#pantalla');"
        " donde.appendChild(caja); donde.appendChild(boton);"
        " return null; })()"
    )
    print(f"  (el cuadro lleva: {la_tierra.alias[:24]!r})")

    # 3. Y se pulsa con un clic de verdad.
    nav.pulsar("#pantalla [data-accion='buscar']")
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=10)
    despues = nav.evaluar(
        """(() => ({
            hash: location.hash,
            h1: (document.querySelector('#pantalla h1') || {}).innerText || '',
            tarjetas: document.querySelectorAll('#pantalla .tarjeta').length,
            acciones: [...new Set([...document.querySelectorAll('#pantalla [data-accion]')]
                .map((e) => e.dataset.accion))],
            texto: (document.querySelector('#pantalla').innerText || '').replace(/\\n+/g, ' | ').slice(0, 200),
        }))()"""
    )
    print("\n=== después de pulsar BUSCAR")
    print(f"  dirección: {despues['hash']}")
    print(f"  h1: {despues['h1']}")
    print(f"  tarjetas (grupos): {despues['tarjetas']}")
    print(f"  acciones: {despues['acciones']}")
    print(f"  texto: {despues['texto']}")
    print()
    if despues["tarjetas"]:
        print("=> EL CAMINO FUNCIONA: la pantalla pinta los grupos. Lo que fallaba era el clic del guion.")
    elif despues["h1"] == "Buscar":
        print("=> La pantalla se abre pero NO pinta grupos: el defecto está en lo que llega o en lo que pinta.")
    else:
        print("=> Al pulsar no se abre la pantalla de la búsqueda: el clic o el manejador.")
