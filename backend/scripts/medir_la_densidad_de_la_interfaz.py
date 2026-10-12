"""Medir **la densidad de la interfaz en un navegador de verdad** (11/10/2026).

POR QUÉ EXISTE. El dueño del producto miró las capturas y dijo: *«no se parece a un CRM normal, parece una UI
para niños pequeños»*. Y tiene razón, pero «parece para niños» no es una medida: es un juicio. Esto lo
convierte en **números del navegador** —tipografía, alto de fila, alto de control, radios, aire— **medidos en
la página renderizada**, no leídos del CSS, que es donde pueden mentir (una regla posterior, un `@media`, una
clase que gana).

Sirve para las dos mitades del trabajo: **antes** (para saber de dónde se parte, con cifras) y **después**
(para demostrar que la densidad ha cambiado, y cuánto). Con la misma ventana y la misma pantalla, la
comparación es de verdad y no una impresión.

Uso:  python scripts/medir_la_densidad_de_la_interfaz.py <direccion> [ruta-de-la-pantalla] [ancho]
      (la ruta por defecto es `#/contactos`, y el ancho 1440)
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
PANTALLA = sys.argv[2] if len(sys.argv) > 2 else "#/contactos"
ANCHO = int(sys.argv[3]) if len(sys.argv) > 3 else 1440

# Lo que se mide, y por qué cada cosa:
#   · `body` y los títulos: **la voz** de la aplicación (una app infantil se delata en 18 px de base y 27 de
#     título);
#   · la fila de una tabla y una fila de lista: **la densidad**, que es lo que hace que un CRM se lea como un
#     CRM (el dato manda y cabe más en la misma pantalla);
#   · el control (botón y campo): **el alto**, que en el móvil es 44-64 px por el dedo y en el escritorio
#     debería ser 28-34;
#   · los radios y el relleno: lo que hace que todo parezca una pastilla de colores en vez de una herramienta.
LO_QUE_SE_MIDE = {
    # **El ancho del contenido** (11/10/2026): estaba topado en 44 rem = 704 px y centrado, que en un monitor
    # de 1440 es menos de la mitad del ancho. Es el patrón de móvil, y sin medirlo no se ve en los números.
    "ancho_del_contenido": ".pantalla",
    "cuerpo": "body",
    "titulo": "h1",
    "subtitulo": "h2",
    # **La fila, no la celda** (11/10/2026). La primera versión medía `table tbody td` y salían 277,9 px: eso
    # es la celda **estirada** por la tabla, no el alto de la fila, que es justo el número que mide la
    # densidad. Un instrumento que da un número grande y equivocado es peor que no medir: se corrige midiendo
    # el `tr`.
    "fila_de_tabla": "table tbody tr",
    "celda_de_tabla": "table tbody td",
    "cabecera_de_tabla": "table thead th",
    "fila_de_lista": ".lista li",
    # **El botón de la PANTALLA, no el primero del documento** (11/10/2026). Medía `button.boton, .boton` a
    # secas, y el primero del documento es el de la **cabecera** (`Salir`, `A+`): así estuve tres rondas
    # creyendo que un cambio no funcionaba porque el número que leía era de otro botón. Un selector que no
    # dice **de qué** es el elemento que mide es la mitad de un instrumento.
    "boton": "#pantalla .boton",
    "boton_de_la_cabecera": ".marco .barra-acciones .boton",
    "campo": "input[type='text'], select",
    "dato_resumen": ".resumen-dato dt",
    "barra": ".marco .barra-acciones, .barra-acciones",
}

LA_MEDIDA = """
(() => {
  const lo_que_se_mide = %s;
  const salida = {};
  for (const [nombre, selector] of Object.entries(lo_que_se_mide)) {
    const nodos = document.querySelectorAll(selector);
    if (!nodos.length) { salida[nombre] = null; continue; }
    const nodo = nodos[0];
    const estilo = getComputedStyle(nodo);
    const caja = nodo.getBoundingClientRect();
    salida[nombre] = {
      selector: selector,
      cuantos: nodos.length,
      letra_px: estilo.fontSize,
      interlineado_px: estilo.lineHeight,
      alto_px: Math.round(caja.height * 10) / 10,
      ancho_px: Math.round(caja.width * 10) / 10,
      radio_px: estilo.borderRadius,
      relleno: estilo.paddingTop + " " + estilo.paddingRight,
      margen_inferior: estilo.marginBottom,
    };
  }
  salida["__ventana"] = { ancho: window.innerWidth, alto: window.innerHeight };
  return salida;
})()
""" % json.dumps(LO_QUE_SE_MIDE)


def main() -> int:
    print(f"  (direccion: {DIRECCION}   pantalla: {PANTALLA}   ancho: {ANCHO})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    with NavegadorDeVerdad(ancho=ANCHO, alto=1000) as nav:
        nav.medir(ANCHO, 1000, movil=ANCHO < 700)
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
        )
        nav.abrir(f"{DIRECCION}/{PANTALLA.lstrip('/')}", esperar=2.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        medidas = nav.evaluar(LA_MEDIDA)

    ventana = medidas.pop("__ventana", {})
    print(f"  (ventana: {ventana.get('ancho')}x{ventana.get('alto')})\n")
    print(f"  {'que':22} {'letra':>8} {'interl.':>8} {'alto':>8} {'radio':>10} {'relleno':>14}")
    print("  " + "-" * 74)
    for nombre, suyo in medidas.items():
        if suyo is None:
            print(f"  {nombre:22} {'(no hay ese elemento en esta pantalla)':>8}")
            continue
        print(
            f"  {nombre:22} {suyo['letra_px']:>8} {suyo['interlineado_px']:>8} "
            f"{suyo['alto_px']:>8} {suyo['radio_px']:>10} {suyo['relleno']:>14}"
        )
    print(
        "\n  (El «alto» de una fila de tabla o de lista es lo que mide la DENSIDAD; el del control, lo que "
        "mide si está pensado para el dedo o para el ratón.)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
