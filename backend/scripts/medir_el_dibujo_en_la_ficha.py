"""¿Enseña la ficha la forma de su tierra? (07/10/2026)

La última comprobación del dibujo de la parcela, y la que faltaba: se crea una tierra **con su geometría** —las
del escenario no tienen forma— y se abre **su ficha** para ver si sale **el dibujo**.

Es la comprobación que dijo que **no** salía, la que después dijo que pedir la tierra a su propia puerta
tampoco bastaba, y la que ahora tiene que decir **sí**: el fallo era de nivel —la ficha lee su tierra de dentro
de un envoltorio (`datos.tierra`) y el dibujo se escribía fuera—, y eso ya está corregido.

Uso:  python medir_el_dibujo_en_la_ficha.py http://127.0.0.1:8089
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8089"
GEOMETRIA = "POLYGON((-5.70 40.85, -5.692 40.85, -5.692 40.858, -5.70 40.858, -5.70 40.85))"


def main() -> int:
    escenario = preparar(DIRECCION)
    cabeceras = {"Authorization": f"Bearer {escenario.volumen.token}"}
    creada = httpx.post(
        f"{DIRECCION}/api/parcelas",
        json={"alias": "La de la forma, para medir la ficha", "geometria": GEOMETRIA},
        headers=cabeceras,
        timeout=30.0,
    ).json()
    print(f"tierra con forma: id {creada['id']} · dibujo de {len(creada.get('dibujo') or '')} caracteres")

    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + repr(escenario.volumen.token).replace("'", '"')
                + ");"
            },
        )
        nav.abrir(f"{DIRECCION}/#/tierras/{creada['id']}", esperar=2.5)
        nav.esperar("Boolean(document.querySelector('#pantalla .barra-acciones'))", segundos=25)
        hay_dibujo = bool(nav.evaluar("Boolean(document.querySelector('#pantalla .panel-dibujo'))"))
        dentro = nav.evaluar(
            "(() => { const p = document.querySelector('#pantalla .panel-dibujo');"
            " return p ? { etiqueta: (p.getAttribute('aria-label') || ''),"
            "   trazos: p.querySelectorAll('path, polygon, polyline, svg').length,"
            "   alto: Math.round(p.getBoundingClientRect().height) } : null; })()"
        )
        print(f"la ficha (id {creada['id']}): .panel-dibujo = {hay_dibujo}")
        if dentro:
            print(f"  (dentro: {dentro})")
        print()
        print("=> EL DIBUJO ESTA EN LA FICHA" if hay_dibujo else "=> EL DIBUJO NO SALE TODAVIA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
