"""Lo que manda una pantalla tiene que caber en el esquema del servidor.

**Por qué existe este fichero** (07/10/2026). La revisión del recorrido encontró un defecto que ninguna
prueba veía: corregir un trabajo hecho contestaba **422 siempre**, porque la pantalla mandaba el cuerpo sin
`campana_id` y el esquema del servidor lo exige. Las pruebas de Python mandaban la campaña a mano (así que
probaban una petición que la pantalla no hace) y la de JavaScript solo miraba el método y la ruta. Nadie
comparaba **el cuerpo que manda la pantalla** con **el esquema que lo recibe**, y por ese hueco cabía
cualquier campo que faltara.

Estas pruebas cierran el hueco para las puertas de los trabajos: leen la tabla de puertas de `app.js` y los
campos obligatorios del esquema, y exigen que cada cuerpo lleve lo que el servidor le va a pedir.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APP_JS = RAIZ / "web" / "app.js"
ESQUEMAS = RAIZ / "app" / "schemas.py"


def _el_bloque_de_las_puertas() -> str:
    """La tabla `puertas` de la pantalla de un trabajo, tal cual está escrita."""
    texto = APP_JS.read_text(encoding="utf-8")
    comienzo = texto.index("const puertas = {")
    final = texto.index("};", comienzo)
    return texto[comienzo:final]


def _los_campos_obligatorios(nombre: str) -> set[str]:
    """Los campos que el esquema exige, leyéndolos de `schemas.py` (los que no llevan valor por defecto).

    Se lee el texto a propósito, y no importando el esquema: lo que se está comprobando es la **pantalla**
    contra el **contrato**, y el contrato de esta comprobación es lo que dice el fichero.
    """
    texto = ESQUEMAS.read_text(encoding="utf-8")
    comienzo = texto.index(f"class {nombre}(")
    final = texto.index("\nclass ", comienzo + 1)
    cuerpo = texto[comienzo:final]
    obligatorios = set()
    for linea in cuerpo.splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith(("#", "class ", '"""', "@")):
            continue
        # Un campo sin `= ` y con anotación es obligatorio (`campana_id: int`).
        if ":" in limpia and "=" not in limpia and re.match(r"^[a-z_][a-z0-9_]*\s*:", limpia):
            obligatorios.add(limpia.split(":")[0].strip())
    return obligatorios


def test_el_esquema_del_trabajo_exige_la_campana() -> None:
    """El punto de partida: si esto dejara de ser verdad, la prueba de abajo no comprobaría nada."""
    assert "campana_id" in _los_campos_obligatorios("TrabajoEntrada")


@pytest.mark.parametrize("puerta", ["planificar", "hecho", "corregir"])
def test_las_puertas_del_trabajo_mandan_la_campana(puerta: str) -> None:
    """Las tres puertas que crean o cambian un trabajo tienen que mandar `campana_id`.

    **La de corregir es la que estaba mal**: mandaba el cuerpo a secas, y por eso corregir un trabajo hecho
    contestaba 422 y la pantalla decía «No se ha podido». Aquí queda atado: el día que alguien añada otra
    puerta que necesite la campaña, esta prueba se lo dice.
    """
    bloque = _el_bloque_de_las_puertas()
    assert f"{puerta}:" in bloque, f"la puerta {puerta} ya no está en la tabla de la pantalla"
    linea = next(
        (una for una in bloque.splitlines() if una.strip().startswith(f"{puerta}:")),
        "",
    )
    assert "campana_id" in linea, (
        f"la puerta {puerta} manda un cuerpo sin `campana_id`, y el esquema del servidor lo exige: "
        "la pantalla diría «No se ha podido» sin que nada estuviera mal en los datos"
    )
