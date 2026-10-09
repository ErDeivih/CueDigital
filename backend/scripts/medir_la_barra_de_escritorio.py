"""¿Cuánto ocupa la barra de ESCRITORIO, y qué pasa con nombres largos? (07/10/2026)

Tarea 2 del encargo. La medida de 83 → 64 px era de **`.cabecera`**, y en el ordenador esa cabecera **está
oculta**: su trabajo lo hace la **barra** (`#marco .barra`). Por eso aquella medida no arreglaba nada aquí.

Esto mide la barra de verdad a 1440:
  1. tal y como está;
  2. y con **los textos alargados** -nombres de finca y de cuenta largos, que es lo que David pidió probar-.

Uso:  python medir_la_barra_de_escritorio.py http://127.0.0.1:8095
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8095"
# **El ancho, por parámetro** (07/10/2026): la barra hay que probarla a 1440 **y** a 1024, que es donde el
# nombre largo de la explotación aprieta.
ANCHO = int(sys.argv[2]) if len(sys.argv) > 2 else 1440

LA_BARRA = """(() => {
  const barra = document.querySelector('#marco .barra');
  if (!barra) return null;
  const caja = barra.getBoundingClientRect();
  const hijos = [...barra.children].map((uno) => Math.round(uno.getBoundingClientRect().top));
  // **El detalle, para saber POR QUE no cabe** (07/10/2026): alto de cada hijo, si su contenido desborda, y
  // cuantas lineas ocupa cada uno. Sin esto, se toca el CSS a ciegas.
  const detalle = [...barra.children].map((uno) => {
    const c = uno.getBoundingClientRect();
    return {
      clase: (uno.className || '').toString().slice(0, 24),
      alto: Math.round(c.height),
      desborda: Math.round(uno.scrollHeight) > Math.round(c.height) + 1,
      lineas: [...uno.querySelectorAll('.barra-valor, .barra-rotulo, .boton')]
        .map((cual) => Math.round(cual.getBoundingClientRect().top))
        .filter((v, i, todos) => todos.indexOf(v) === i).length,
    };
  });
  return {
    alto: Math.round(caja.height),
    ancho: Math.round(caja.width),
    filas: new Set(hijos).size,
    cuantos: barra.children.length,
    detalle,
    // **Y dentro de la caja de acciones** (07/10/2026): es la que mide 112 px y la unica que mantiene la barra
    // por encima de 64. Aqui se ve que boton es alto y por que, en vez de tocar CSS a ojo.
    botones: [...barra.querySelectorAll('.barra-acciones > *')].map((uno) => {
      const c = uno.getBoundingClientRect();
      return {
        clase: (uno.className || '').toString().slice(0, 22),
        alto: Math.round(c.height),
        ancho: Math.round(c.width),
        letras: (uno.textContent || '').trim().length,
      };
    }),
    // **Qué se está recortando** (07/10/2026): lo accesorio puede recortarse -el nombre de la explotación-,
    // pero la **campaña** y las **acciones** no. Aquí se dice cuáles se están cortando, en vez de mirarlo a ojo
    // en una captura.
    recortados: [
      ...barra.querySelectorAll('.barra-valor, .barra-acciones .boton, .barra-acciones .boton-letra'),
    ]
      .filter((uno) => uno.scrollWidth > uno.clientWidth + 1)
      .map((uno) => (uno.textContent || '').trim().slice(0, 26)),
    texto: (barra.textContent || '').trim().slice(0, 90),
  };
})()"""

ALARGAR = """(() => {
  const barra = document.querySelector('#marco .barra');
  if (!barra) return 0;
  let tocados = 0;
  // **Solo los NOMBRES** (07/10/2026): alargando todo -incluidos los botones- lo que se medía era un botón
  // con un texto larguísimo, no un nombre de finca largo. Aquí se alarga lo que David pidió probar.
  for (const uno of barra.querySelectorAll('.barra-valor')) {
    const suyo = (uno.textContent || '').trim();
    if (suyo) {
      uno.textContent = suyo + ' de la Dehesa Grande del Valle';
      tocados += 1;
    }
  }
  return tocados;
})()"""


def main() -> int:
    escenario = preparar(DIRECCION)
    with NavegadorDeVerdad(ancho=ANCHO, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + repr(escenario.volumen.token).replace("'", '"')
                + ");"
            },
        )
        nav.abrir(f"{DIRECCION}/#/inicio", esperar=3.0)
        nav.esperar("Boolean(document.querySelector('#marco .barra'))", segundos=25)

        antes = nav.evaluar(LA_BARRA)
        print(f"la barra de escritorio ({ANCHO}): {antes}")
        # **0 px no es «cabe»** (07/10/2026): a 1024 el armazón no pinta esta barra y el guion decía «CABE EN
        # 64 px» porque 0 <= 64. Un falso aprobado en el propio instrumento. Si no hay barra, se dice.
        if not antes or not antes.get("alto"):
            print(f"=> NO HAY BARRA a {ANCHO} px: mira qué cabecera usa el armazón a este ancho")
            return 1

        tocados = nav.evaluar(ALARGAR)
        despues = nav.evaluar(LA_BARRA)
        print(f"con nombres largos ({tocados} nombres alargados): {despues}")
        print()
        print(f"ALTO: {antes['alto']} px → {despues['alto']} px")
        # **Qué se recorta, en su propia línea** (07/10/2026): leerlo dentro del volcado del diccionario no
        # funcionaba -mi filtro cortaba la línea-, así que se dice aparte. Lo accesorio puede recortarse; la
        # campaña y las acciones, no.
        print(f"RECORTADOS con los nombres de siempre: {antes.get('recortados')}")
        print(f"RECORTADOS con nombres largos:         {despues.get('recortados')}")
        # **Se mide el alto, no la posicion de los hijos** (07/10/2026): dos hijos de distinta altura, centrados,
        # ya dan dos posiciones distintas aunque esten en la misma fila. Lo que importa es que quepa.
        cabe = despues["alto"] <= 64
        print("=> LA BARRA CABE EN 64 px, con nombres largos" if cabe else "=> LA BARRA NO CABE: hay que compactarla")
        return 0 if cabe else 2


if __name__ == "__main__":
    raise SystemExit(main())
