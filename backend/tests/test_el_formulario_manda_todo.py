"""El formulario manda **todo** lo que la API acepta.

POR QUÉ ESTA PRUEBA EXISTE, Y QUÉ FALLO PERSIGUE

Un campo que el asistente no manda es un dato que el agricultor contesta y **se pierde por el camino,
sin que salte ningún error**: él lo escribe, el programa lo guarda a medias y nadie se entera hasta que
un día falta en el cuaderno.

Ya ha pasado tres veces, y las tres se encontraron mirando el código a mano:

  · **La máquina con la que se cosechó** (ronda 91). El asistente la preguntaba desde la ronda 5 y el
    navegador la mandaba, pero `CosechaEntrada` no tenía el campo: Pydantic la descartaba en silencio.
    El contenido mínimo del CUE pide la maquinaria en su hoja de labores, así que era un dato del
    cuaderno que se quedaba vacío para siempre.
  · **El asesoramiento de un tratamiento**, la variedad y el lote del producto: se podían apuntar por la
    API y el formulario no los mandaba, así que al **corregir** un apunte se perdían.
  · **Qué se cosechó** (`producto`), que vive dentro de `detalles`: al corregir una cosecha se quedaba
    sin decir de qué era.

Esta prueba compara, campo a campo, lo que el formulario manda (`cargaTratamiento`,
`cargaFertilizacion` y `cargaLabor` en `backend/web/app.js`) con lo que acepta la API (los esquemas de
`app/schemas.py`). **Si un campo se añade a la API y no al formulario, esta prueba se pone roja** con su
nombre, en vez de dejar que se descubra dentro de un año en el cuaderno de alguien.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import schemas

APP_JS = Path(__file__).resolve().parents[1] / "web" / "app.js"


def _cuerpo_de_una_funcion(nombre: str) -> str:
    """El texto de esa función de `app.js`, desde su cabecera hasta su llave de cierre."""
    texto = APP_JS.read_text(encoding="utf-8")
    try:
        inicio = texto.index(f"function {nombre}(")
    except ValueError:  # pragma: no cover — si alguien renombra la función, la prueba lo dice
        raise AssertionError(
            f"no existe `{nombre}` en `web/app.js`: si se ha renombrado, esta prueba tiene que seguirla"
        ) from None
    fin = texto.index("\n}", inicio)
    return texto[inicio:fin]


def _campos_que_manda(cuerpo: str) -> set[str]:
    """Las claves del objeto que esa función devuelve (`campo: valor`).

    Se buscan con dos espacios o más de sangría, que es como están escritas dentro del `return {`: así no
    se cuela nada de las líneas de fuera (los `const`, los `if`).
    """
    return set(re.findall(r"^\s{2,}([a-z_][a-z0-9_]*):", cuerpo, re.MULTILINE))


def _los_que_faltan(cuerpo: str, esquema: type) -> list[str]:
    return sorted(set(esquema.model_fields) - _campos_que_manda(cuerpo))


@pytest.mark.parametrize(
    ("funcion", "esquema", "que_es"),
    [
        ("cargaTratamiento", schemas.TratamientoEntrada, "un tratamiento con producto"),
        ("cargaFertilizacion", schemas.FertilizacionEntrada, "un abono"),
        ("cargaLabor", schemas.LaborEntrada, "un trabajo del campo"),
        ("cargaLabor", schemas.CosechaEntrada, "una cosecha"),
    ],
)
def test_el_formulario_manda_todos_los_campos(funcion: str, esquema: type, que_es: str):
    faltan = _los_que_faltan(_cuerpo_de_una_funcion(funcion), esquema)
    assert faltan == [], (
        f"`{funcion}` no manda estos campos de {que_es} ({esquema.__name__}), así que lo que el "
        f"agricultor conteste en ellos se queda fuera del cuaderno sin que nadie se entere: "
        f"{', '.join(faltan)}"
    )


def test_la_prueba_lee_de_verdad_el_formulario():
    """Si el lector se equivocara de sitio, la prueba de arriba pasaría sin comprobar nada.

    Se comprueba con un campo que se manda **seguro** (la fecha, que la manda cualquier apunte) y con uno
    que no existe en ningún esquema, para que no valga cualquier cosa.
    """
    campos = _campos_que_manda(_cuerpo_de_una_funcion("cargaTratamiento"))
    assert "fecha" in campos, "no se está leyendo el objeto que devuelve `cargaTratamiento`"
    assert "producto_id" in campos
    assert "no_existe_este_campo" not in campos


def test_los_esquemas_son_los_de_verdad():
    """Y los esquemas que se comparan son los que usa el servidor para guardar."""
    from app.routers import registros

    assert registros.TratamientoEntrada is schemas.TratamientoEntrada
    assert registros.FertilizacionEntrada is schemas.FertilizacionEntrada
    assert registros.LaborEntrada is schemas.LaborEntrada
    assert registros.CosechaEntrada is schemas.CosechaEntrada
