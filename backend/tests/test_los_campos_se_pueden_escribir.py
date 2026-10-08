"""Un `<input>` con `value=` y sin `onChange` **no se puede escribir** (07/10/2026).

## Por qué existe esta prueba

La pantalla de la búsqueda global salió con esto:

    <input id="buscar_global" type="search" value=${suyo.texto} />

Y parecía inofensivo: el valor salía del servidor, y el manejador lee el cuadro del DOM al pulsar BUSCAR. Pero
React trata `value` sin `onChange` como un **campo controlado**: en cada suceso de entrada **restaura** el
valor de la prop, así que lo que el agricultor escribe **se borra solo**. En la casa los campos se escriben
con `defaultValue` (`banco-buscar`, `bandeja-buscar`, el `<select>` de la bandeja…), que es un campo normal y
corriente: se teclea y el valor se queda.

**Lo encontró el recorrido automático** al entrar por la puerta de verdad de la búsqueda —con los tests
verdes, porque las pruebas de dibujo no ven la diferencia: `value` y `defaultValue` pintan lo mismo en el
HTML—. Es exactamente la clase de defecto que no se ve leyendo, sino pulsando.

## Qué se comprueba

Todos los ficheros de pantalla y de piezas de React: **ningún `<input>` con `value=` se queda sin
`onChange=`**. Un campo controlado de verdad (con su `onChange`) es legítimo; lo que no lo es es un campo que
el agricultor no puede escribir.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
CARPETAS = (RAIZ / "web" / "react" / "pantallas", RAIZ / "web" / "react" / "piezas")

# Un `<input …>` entero, incluso repartido en varias líneas (htm los escribe así).
UN_INPUT = re.compile(r"<input\b[^>]*>", re.IGNORECASE | re.DOTALL)


def los_ficheros() -> list[pathlib.Path]:
    return sorted(fichero for carpeta in CARPETAS for fichero in carpeta.glob("*.js"))


def campos_que_no_se_pueden_escribir(texto: str) -> list[str]:
    """Los `<input>` con `value=` y sin `onChange=`: los que React deja de solo lectura."""
    malos = []
    for etiqueta in UN_INPUT.findall(texto):
        # Ojo: `defaultValue=` **contiene** la palabra «value» y es justo lo correcto, así que se mira con
        # una expresión que no se deje engañar por ella.
        if re.search(r"(?<!default)\bvalue\s*=", etiqueta) and "onChange" not in etiqueta:
            malos.append(" ".join(etiqueta.split()))
    return malos


def test_ningun_campo_se_queda_de_solo_lectura_sin_querer() -> None:
    malos: dict[str, list[str]] = {}
    for fichero in los_ficheros():
        suyos = campos_que_no_se_pueden_escribir(fichero.read_text(encoding="utf-8"))
        if suyos:
            malos[fichero.name] = suyos

    assert malos == {}, (
        "hay campos que el agricultor no podría escribir (value sin onChange: React los revierte al "
        f"teclear). Se escriben con `defaultValue` y el manejador los lee del DOM: {malos}"
    )


def test_la_comprobacion_reconoce_un_campo_de_solo_lectura() -> None:
    """Y la prueba se comprueba a sí misma: si un campo así se colara, esto lo diría.

    Sin esto, la prueba de arriba podría estar pasando por no mirar donde cree (un patrón que no casa con
    nada pasa siempre, y eso es un guardián de mentira).
    """
    malo = '<input id="buscar_global" type="search" value=${suyo.texto} />'
    assert campos_que_no_se_pueden_escribir(malo) == [
        '<input id="buscar_global" type="search" value=${suyo.texto} />'
    ], "la comprobación no reconoce un campo que no se puede escribir"

    bueno = '<input id="buscar_global" type="search" defaultValue=${suyo.texto} />'
    assert campos_que_no_se_pueden_escribir(bueno) == [], (
        "la comprobación se queja de un campo corriente (defaultValue), que es el que se usa en la casa"
    )

    controlado = '<input id="lo-que-sea" value=${algo} onChange=${(e) => apuntar(e)} />'
    assert campos_que_no_se_pueden_escribir(controlado) == [], (
        "un campo controlado de verdad, con su onChange, es legítimo"
    )
