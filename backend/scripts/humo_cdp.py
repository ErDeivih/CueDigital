"""Comprobación rápida de que `navegador_cdp.py` sirve: teclas, escala y descargas.

No es un test del proyecto (los tests no levantan navegadores): es la comprobación de la herramienta, para
no darle a nadie una pieza que no funciona.

Uso:  python scripts/humo_cdp.py http://127.0.0.1:8013
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8013"

with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    # **Se entra por `/`, no por `#/entrar`**: esa dirección **no está en la tabla de rutas a propósito**
    # (la pantalla de entrar es un paso, y una dirección que al recargar deja a medias es peor que no
    # tenerla: lo defiende `tests_js/rutas.test.js`). Este humo la usaba y por eso salía «esa dirección no
    # lleva a ninguna parte»; lo encontró la comprobación de teclado el 06/10/2026.
    nav.abrir(f"{DIRECCION}/")
    print("titulo:", nav.evaluar("document.title"))
    print("pantalla montada:", nav.evaluar("Boolean(document.querySelector('#pantalla'))"))

    # El teclado, de verdad: Tab mueve el foco.
    nav.evaluar("document.body.focus()")
    antes = nav.evaluar("document.activeElement.tagName + '#' + (document.activeElement.id || '')")
    nav.tecla("Tab")
    despues = nav.evaluar("document.activeElement.tagName + '#' + (document.activeElement.id || '')")
    print(f"foco antes={antes!r} despues={despues!r} cambia={antes != despues}")

    # El ratón, de verdad: se pulsa un botón y contesta el manejador.
    nav.evaluar("window.__pulsado = 0; document.addEventListener('click', () => window.__pulsado += 1)")
    cuantos = nav.evaluar("document.querySelectorAll('button, a').length")
    print("elementos pulsables:", cuantos)
    if cuantos:
        try:
            nav.pulsar("button, a")
            print("clics recibidos:", nav.evaluar("window.__pulsado"))
        except Exception as fallo:
            print("no se ha podido pulsar:", fallo)

    # La escala del dispositivo: 2.0 tiene que verse en `devicePixelRatio`.
    nav.medir(1440, 900, escala=2.0)
    print("devicePixelRatio a escala 2:", nav.evaluar("window.devicePixelRatio"))
    print("ancho interior:", nav.evaluar("window.innerWidth"))

    # El zoom del navegador.
    nav.medir(1440, 900, escala=1.0)
    nav.zoom(2.0)
    print("tras el zoom, visualViewport.scale:", nav.evaluar("window.visualViewport && window.visualViewport.scale"))

    # Las descargas: se descarga un fichero que sirve el propio servidor y se mira que llegue.
    carpeta = tempfile.mkdtemp(prefix="cuedigital-descargas-")
    nav.descargas_en(carpeta)
    for destino in ("/api/cuaderno/export.csv", "/"):
        # Se pulsa un enlace de descarga de verdad (no un `window.open`, que abre otra pestaña). La
        # expresión acaba en `null` porque el helper no puede traerse un objeto del navegador a Python.
        nav.evaluar(
            f"""(() => {{
                const a = document.createElement('a');
                a.href = {DIRECCION!r} + {destino!r};
                a.download = '';
                document.body.appendChild(a);
                a.click();
                return null;
            }})()"""
        )
        llegado = nav.lo_descargado(segundos=8)
        print(f"descarga de {destino}:", llegado.name if llegado else "nada")
    print("en la carpeta:", [f.name for f in pathlib.Path(carpeta).iterdir()])
    print("estado de las descargas:", nav.evaluar("navigator.userAgent.slice(0, 40)"))

print("fin del humo")
