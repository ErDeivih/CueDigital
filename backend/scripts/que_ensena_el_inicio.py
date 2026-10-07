"""¿Qué enseña la cabecera del inicio a 390 px? (para saber qué se puede exigir ahí)

Uso:  python que_ensena_el_inicio.py http://127.0.0.1:8025
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8025"
escenario = preparar(DIRECCION)
print("nombre de la explotación:", escenario.volumen.nombre)
with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    for ancho in (390, 712, 1024, 1440):
        nav.medir(ancho, 900)
        nav.orden("Page.navigate", {"url": "about:blank"})
        nav.abrir(f"{DIRECCION}/#/", esperar=1.6)
        cabecera = nav.evaluar("(document.querySelector('#marco') || {}).innerText || ''")
        print(f"\n=== a {ancho} px")
        print("  cabecera:", " | ".join(cabecera.split("\n"))[:300])
