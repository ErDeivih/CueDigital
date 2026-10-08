"""¿Se ve la pantalla de normativa? (07/10/2026)

La suite dice que el armazon esta bien montado, pero **una pantalla no se da por buena con las pruebas verdes**:
se abre en un navegador y se mira. Aqui se abre `#/normativa` de verdad y se cuentan las reglas, sus enlaces
oficiales y los avisos de las que no estan clasificadas.

Uso:  python medir_la_pantalla_de_normativa.py http://127.0.0.1:8090
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"

CUENTA = """(() => {
  const lista = document.querySelector('#pantalla .lista-de-normativa');
  const reglas = document.querySelectorAll('#pantalla .regla-de-normativa');
  const enlaces = document.querySelectorAll('#pantalla .fuentes-de-la-regla a');
  // Los avisos van **con su frase entera**, no con la palabra del rotulo: el aviso dice «Todavia no se ha
  // clasificado esta regla: puede ser una obligacion o una recomendacion» -y eso es lo que hay que buscar-.
  const sinClasificar = [...document.querySelectorAll('#pantalla .regla-de-normativa p')].filter(
    (uno) => /no se ha clasificado/i.test(uno.textContent || ''),
  ).length;
  return {
    hayLista: Boolean(lista),
    reglas: reglas.length,
    enlaces: enlaces.length,
    sinClasificar,
    primera: reglas[0] ? (reglas[0].querySelector('h2') || {}).textContent || '' : '',
    primerEnlace: enlaces[0] ? enlaces[0].getAttribute('href') || '' : '',
    titulo: (document.querySelector('#pantalla h1') || {}).textContent || '',
  };
})()"""


def main() -> int:
    escenario = preparar(DIRECCION)
    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + repr(escenario.volumen.token).replace("'", '"')
                + ");"
            },
        )
        nav.abrir(f"{DIRECCION}/#/normativa", esperar=3.0)
        nav.esperar("Boolean(document.querySelector('#pantalla .lista-de-normativa'))", segundos=30)
        suyo = nav.evaluar(CUENTA)
        print(f"titulo: {suyo['titulo']!r}")
        print(f"la lista de la normativa: {suyo['hayLista']}")
        print(f"reglas pintadas: {suyo['reglas']}")
        print(f"enlaces oficiales: {suyo['enlaces']}")
        print(f"avisos de sin clasificar: {suyo['sinClasificar']}")
        print(f"la primera: {suyo['primera'][:70]!r}")
        print(f"su primer enlace: {suyo['primerEnlace'][:70]!r}")
        print()
        bien = suyo["reglas"] == 10 and suyo["enlaces"] >= 10 and suyo["sinClasificar"] == 10
        print("=> LA PANTALLA DE NORMATIVA SE VE" if bien else "=> ALGO NO CUADRA")
        return 0 if bien else 1


if __name__ == "__main__":
    raise SystemExit(main())
