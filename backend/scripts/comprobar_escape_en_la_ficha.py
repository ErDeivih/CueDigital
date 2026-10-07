"""¿A dónde lleva Escape desde la ficha de una tierra? (07/10/2026)

La revisión del recorrido lo señaló (E4): la ficha de una tierra tenía un solo botón de vuelta —«VOLVER A
LOS TRABAJOS»— y **Escape hacía lo mismo**, así que el agricultor que entraba a mirar su tierra acababa en
la agenda de trabajos, sin camino de vuelta a la lista de donde salió. Ahora Escape vuelve a la lista de
tierras, que es lo que cierra esa pantalla.

Uso:  python comprobar_escape_en_la_ficha.py http://127.0.0.1:8032
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8032"
FALLOS: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {descripcion}")
    if not condicion:
        FALLOS.append(descripcion)


escenario = preparar(DIRECCION)
la_tierra = escenario.tierras[0]
with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.8)
    nav.esperar("Boolean(document.querySelector('#buscar_tierra_mis_cosas'))", segundos=12)
    nav.pulsar("[data-accion='elegir-fila']")
    nav.esperar("Boolean(document.querySelector(\"[data-accion='tierra-historia']\"))", segundos=8)
    nav.pulsar("[data-accion='tierra-historia']")
    nav.esperar("location.hash.includes('/historial')", segundos=10)
    print(f"  (en el historial: {nav.evaluar('location.hash')})")
    comprobar(
        "trabajos" not in str(nav.evaluar("location.hash")),
        "se está en el historial de la tierra, no en la agenda",
    )
    nav.tecla("Escape")
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=8)
    destino = str(nav.evaluar("location.hash"))
    print(f"  (después de Escape: {destino})")
    comprobar(
        "trabajos" not in destino,
        "Escape NO lleva a la agenda de trabajos (que era el defecto)",
    )

print(f"\nComprobaciones: {len(FALLOS) + 2}   Fallos: {len(FALLOS)}")
for fallo in FALLOS:
    print(f"  · {fallo}")
raise SystemExit(1 if FALLOS else 0)
