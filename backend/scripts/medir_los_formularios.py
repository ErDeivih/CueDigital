"""Cuánto miden los campos de un formulario en el ordenador (encargo: «formularios de escritorio», 07/10/2026).

La queja del encargo es que los formularios no están hechos para el escritorio. «No están hechos» no es una
medida: lo que hay que saber es **cuánto ocupa un campo** en una pantalla ancha, porque un campo de texto de
700 px de ancho no se lee mejor —se lee peor: el ojo pierde el renglón—.

Mide el formulario de un trabajo (el más largo del programa) en tres anchos: el ancho de la pantalla, el del
formulario y el de sus campos.

Uso:  python medir_los_formularios.py http://127.0.0.1:8071
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8071"

MEDIDA = (
    "(() => {"
    " const campos = [...document.querySelectorAll('#pantalla input, #pantalla select, #pantalla textarea')]"
    "   .filter((e) => e.type !== 'hidden');"
    " const anchos = campos.map((e) => Math.round(e.getBoundingClientRect().width));"
    " const pantalla = document.querySelector('#pantalla');"
    " return {"
    "  ancho: window.innerWidth,"
    "  cuantos: campos.length,"
    "  el_mas_ancho: anchos.length ? Math.max(...anchos) : null,"
    "  el_mas_estrecho: anchos.length ? Math.min(...anchos) : null,"
    "  pantalla: pantalla ? Math.round(pantalla.getBoundingClientRect().width) : null,"
    "  texto_mas_largo: campos.reduce((largo, e) => {"
    "   const v = (e.innerText || e.value || '').length; return v > largo ? v : largo; }, 0)"
    " }; })()"
)


def main() -> int:
    escenario = preparar(DIRECCION)
    print(f"{'ancho':>6}  {'pantalla':>8}  {'campos':>6}  {'más ancho':>9}  {'más estrecho':>12}")
    with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + repr(escenario.volumen.token).replace("'", '"')
                + ");"
            },
        )
        for ancho in (1440, 1024, 712):
            nav.orden(
                "Emulation.setDeviceMetricsOverride",
                {"width": ancho, "height": 1000, "deviceScaleFactor": 1, "mobile": False},
            )
            nav.abrir(f"{DIRECCION}/#/trabajos", esperar=1.8)
            nav.esperar("Boolean(document.querySelector(\"[data-accion='trabajo-planificar']\"))", segundos=20)
            nav.evaluar(
                "(() => { const b = document.querySelector(\"[data-accion='trabajo-planificar']\");"
                " if (b) b.click(); return null; })()"
            )
            nav.esperar("Boolean(document.querySelector('#trabajo-tipo'))", segundos=20)
            m = nav.evaluar(MEDIDA) or {}
            print(
                f"{m.get('ancho'):>6}  {str(m.get('pantalla')):>8}  {str(m.get('cuantos')):>6}"
                f"  {str(m.get('el_mas_ancho')):>9}  {str(m.get('el_mas_estrecho')):>12}"
            )
        nav.orden("Emulation.clearDeviceMetricsOverride")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
