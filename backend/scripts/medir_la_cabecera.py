"""Cuánto ocupa la cabecera, y qué letra se usa (encargo: «la cabecera enorme», 07/10/2026).

Mide **antes y después** de tocar el CSS, en cuatro anchos, porque «enorme» no es una medida: lo que hay que
saber es cuántos píxeles se lleva la cabecera de la pantalla antes de que el agricultor vea nada, y con qué
tamaño de letra. Los números de referencia del encargo son **18 px de cuerpo, títulos 24/20 y márgenes 24**.

Uso:  python medir_la_cabecera.py http://127.0.0.1:8067
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8067"

MEDIDA = (
    "(() => {"
    " const cabecera = document.querySelector('.cabecera');"
    " const titulo = document.querySelector('.cabecera-titulo');"
    " const cuerpo = getComputedStyle(document.body);"
    " const h1 = document.querySelector('#pantalla h1');"
    " const h2 = document.querySelector('#pantalla h2');"
    " const pantalla = document.querySelector('#pantalla');"
    " const suyo = pantalla ? getComputedStyle(pantalla) : null;"
    " return {"
    "  ancho: window.innerWidth,"
    "  cabecera: cabecera ? Math.round(cabecera.getBoundingClientRect().height) : null,"
    "  titulo: titulo ? Math.round(titulo.getBoundingClientRect().height) : null,"
    "  cuerpo: cuerpo.fontSize,"
    "  h1: h1 ? getComputedStyle(h1).fontSize : null,"
    "  h2: h2 ? getComputedStyle(h2).fontSize : null,"
    "  margen: suyo ? suyo.paddingLeft : null,"
    "  arriba: cabecera ? Math.round(cabecera.getBoundingClientRect().bottom) : null"
    " }; })()"
)


def main() -> int:
    escenario = preparar(DIRECCION)
    print(f"{'ancho':>6}  {'cabecera':>9}  {'arriba':>7}  {'cuerpo':>7}  {'h1':>7}  {'h2':>7}  {'margen':>7}")
    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + repr(escenario.volumen.token).replace("'", '"')
                + ");"
            },
        )
        for ancho in (1440, 1024, 712, 390):
            nav.orden(
                "Emulation.setDeviceMetricsOverride",
                {"width": ancho, "height": 900, "deviceScaleFactor": 1, "mobile": False},
            )
            nav.abrir(f"{DIRECCION}/#/", esperar=1.6)
            nav.esperar("Boolean(document.querySelector('.cabecera'))", segundos=12)
            m = nav.evaluar(MEDIDA) or {}
            print(
                f"{m.get('ancho'):>6}  {str(m.get('cabecera')):>9}  {str(m.get('arriba')):>7}"
                f"  {str(m.get('cuerpo')):>7}  {str(m.get('h1')):>7}  {str(m.get('h2')):>7}"
                f"  {str(m.get('margen')):>7}"
            )
        nav.orden("Emulation.clearDeviceMetricsOverride")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
