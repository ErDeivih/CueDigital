"""***La cabecera de escritorio, sin solapes*** (22/10/2026, C1 de la revision con vision).

*Lo que decia la revision: «**Los textos de finca/campana se superponen y el contexto de cuenta se recorta**. La cabecera
no conserva una jerarquia legible al entrar en el breakpoint de escritorio».*

***Y su aceptacion***: *«a 1024, 1100 y 1440 **no hay intersecciones de texto ni controles tapados**; cuenta, finca y
campana se identifican, con nombres largos. Reorganizar o abreviar con etiqueta accesible, **sin reducir el suelo
tipografico ni el area de los controles**».*

*Esto mide **intersecciones de verdad** -las cajas de los textos y los controles de la barra-, y **el suelo**: que ningun
texto baje de 15 px ni ningun control de 44 px.*

Uso:  python scripts/verificar_la_cabecera_de_escritorio.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# ***Las cajas de lo que hay en la barra***: *textos y controles, con su caja y su tamano de letra.*
LAS_CAJAS = (
    "(() => {"
    " const barra = document.querySelector('.marco .barra') || document.querySelector('.cabecera');"
    " if (!barra) return 'no hay barra';"
    " const dentro = Array.from(barra.querySelectorAll('*')).filter((n) => {"
    "   const r = n.getBoundingClientRect();"
    "   const texto = (n.textContent || '').trim();"
    "   const esControl = ['BUTTON', 'SELECT', 'INPUT', 'A'].includes(n.tagName);"
    "   return r.width > 0 && r.height > 0 && (texto.length > 0 || esControl);"
    " }).filter((n) => !Array.from(n.children).some((h) => (h.textContent || '').trim().length > 0));"
    " return dentro.map((n) => { const r = n.getBoundingClientRect();"
    "   const cs = getComputedStyle(n);"
    "   return { t: (n.textContent || '').trim().slice(0, 24), x: Math.round(r.left), y: Math.round(r.top),"
    "            w: Math.round(r.width), h: Math.round(r.height), letra: parseFloat(cs.fontSize),"
    "            control: ['BUTTON', 'SELECT', 'INPUT', 'A'].includes(n.tagName) }; });"
    "})()"
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


def se_pisan(a: dict, b: dict) -> bool:
    """*Dos cajas se pisan si sus rectangulos se cruzan con holgura de un pixel.*"""
    return not (
        a["x"] + a["w"] <= b["x"] + 1
        or b["x"] + b["w"] <= a["x"] + 1
        or a["y"] + a["h"] <= b["y"] + 1
        or b["y"] + b["h"] <= a["y"] + 1
    )


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        # ***Nombres largos a proposito***: *es el caso que hay que aceptar.*
        cuenta = _una_cuenta_nueva(
            direccion, "cabecera@prueba.local", "una-clave-larga-y-facil", "Maria del Carmen Fernandez de la Vega"
        )
        with NavegadorDeVerdad(ancho=1024, alto=768) as nav:
            _poner_la_sesion(nav, direccion, cuenta["token"])
            for ancho, alto in ((1024, 768), (1100, 800), (1440, 900)):
                nav.orden(
                    "Emulation.setDeviceMetricsOverride",
                    {"width": ancho, "height": alto, "deviceScaleFactor": 1, "mobile": False},
                )
                time.sleep(0.6)
                nav.abrir(f"{direccion}/#/", esperar=3.0)
                time.sleep(2.5)
                las_cajas = nav.evaluar(LAS_CAJAS)
                print(f"\n== La cabecera a {ancho}x{alto} ==")
                if not isinstance(las_cajas, list):
                    fallos += not comprobar(False, f"***hay barra a {ancho}***", str(las_cajas))
                    continue
                # *Las cajas que se pisan, si hay alguna.*
                los_solapes = [
                    f"{a['t']!r} con {b['t']!r}"
                    for i, a in enumerate(las_cajas)
                    for b in las_cajas[i + 1 :]
                    if se_pisan(a, b)
                ]
                print(f"  (cajas en la barra: {len(las_cajas)})")
                fallos += not comprobar(
                    not los_solapes,
                    f"***a {ancho} no hay dos cosas pisandose***",
                    "; ".join(los_solapes) or f"ninguna, {len(las_cajas)} cajas",
                )
                # *Y el suelo: ni letra pequena ni controles diminutos.*
                la_letra = min((c["letra"] for c in las_cajas if not c["control"]), default=99)
                los_controles = [c for c in las_cajas if c["control"]]
                el_mas_bajo = min((min(c["w"], c["h"]) for c in los_controles), default=99)
                print(f"  (letra mas pequena {la_letra:.0f} px · control mas pequeno {el_mas_bajo:.0f} px)")
                # ***Y si algo baja del suelo, se DICE CUAL***: *un minimo sin nombre no se puede arreglar, y ademas
                # puede ser una caja invisible o de otro sitio -un instrumento que no dice quien falla no vale-.*
                los_bajos = [
                    f"{c['t']!r} ({'control' if c['control'] else 'texto'} {c['letra']:.0f} px, "
                    f"{c['w']}x{c['h']})"
                    for c in las_cajas
                    if (c["control"] and min(c["w"], c["h"]) < 44) or (not c["control"] and c["letra"] < 15)
                ]
                fallos += not comprobar(
                    la_letra >= 15,
                    f"***y ningun texto baja de 15 px*** ({la_letra:.0f})",
                    "; ".join(los_bajos) or "ninguno",
                )
                fallos += not comprobar(
                    el_mas_bajo >= 44,
                    f"***y ningun control baja de 44 px*** ({el_mas_bajo:.0f})",
                    "; ".join(los_bajos) or "ninguno",
                )

    print(f"\nComprobaciones: 9   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
