"""¿Abre la tarjeta del móvil la ficha de la tierra? (07/10/2026)

La misma tierra llevaba a **dos pantallas distintas según el aparato**: en el móvil la tarjeta abría «lo que
hay sembrado» y en el ordenador la fila abría el panel con su historia. Eso es lo contrario de la ficha
única que pide el encargo, y el cultivo ya se ve dentro de la ficha. Ahora la tarjeta abre la ficha.

Esto lo mide en un navegador de verdad, a 390 px, que es donde vive esa tarjeta.

Uso:  python comprobar_la_ficha_en_el_movil.py http://127.0.0.1:8033
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8033"
FALLOS: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {descripcion}")
    if not condicion:
        FALLOS.append(descripcion)


escenario = preparar(DIRECCION)
with NavegadorDeVerdad(ancho=390, alto=844) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    nav.medir(390, 844)
    nav.abrir(f"{DIRECCION}/#/tierras", esperar=2.0)
    nav.esperar("Boolean(document.querySelector('.tarjeta-con-acciones'))", segundos=12)
    la_tarjeta = nav.evaluar(
        """(() => {
            const tarjeta = document.querySelector('.tarjeta-con-acciones [data-accion]');
            return tarjeta ? {accion: tarjeta.dataset.accion, texto: tarjeta.innerText.trim().slice(0, 60)} : null;
        })()"""
    )
    print(f"  (la tarjeta del móvil: {la_tarjeta})")
    comprobar(bool(la_tarjeta), "la tarjeta del móvil está y se ve")
    comprobar(
        bool(la_tarjeta) and la_tarjeta["accion"] == "tierra-historia",
        "la tarjeta del móvil abre la ficha de la tierra (no otra pantalla distinta)",
    )
    # Y se pulsa de verdad: tiene que acabar en el historial de esa tierra.
    nav.pulsar(".tarjeta-con-acciones [data-accion='tierra-historia']")
    llego = nav.esperar("location.hash.includes('/historial')", segundos=10)
    print(f"  (después de tocar la tarjeta: {nav.evaluar('location.hash')})")
    comprobar(llego, "y al tocarla se entra en el historial de esa tierra")
    # Y en el móvil no se pinta el botón de «su historia» debajo: la tarjeta ya lo hace.
    comprobar(
        not bool(
            nav.evaluar(
                "[...document.querySelectorAll('.tarjeta-con-acciones [data-accion]')]"
                ".some((e) => e.dataset.accion === 'tierra-historia' && e.tagName === 'BUTTON')"
            )
        ),
        "no se repite el botón de «su historia» debajo de la tarjeta",
    )

print(f"\nComprobaciones: {len(FALLOS) + 4}   Fallos: {len(FALLOS)}")
for fallo in FALLOS:
    print(f"  · {fallo}")
raise SystemExit(1 if FALLOS else 0)
