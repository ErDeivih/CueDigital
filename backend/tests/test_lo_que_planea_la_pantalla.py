"""Lo que la pantalla manda al **planificar** tiene que ser lo que el plan espera (07/10/2026).

## El defecto que esto vigila

La pantalla de un trabajo mandaba, al planificar, lo que iba a gastar del almacén como `insumos`:

    insumos: [{ lote_id, cantidad, unidad }]

Y el esquema del **plan** (`TrabajoPrevistoEntrada`) no tiene `insumos`: tiene **`lineas`** — «esta tierra,
esta cantidad de este envase»—, porque un plan se reparte por tierras. El servidor **ignora lo que no
conoce**, así que no fallaba nada: el plan se guardaba **sin lo que iba a gastar**, y después, al marcarlo
hecho, no había nada que traer y **el almacén no se enteraba nunca**. Silencioso de punta a punta.

Lo encontró el recorrido automático comprobando el consumo de existencias: el plan volvía con
`insumos: []` después de haber elegido el envase.

## Qué se comprueba

Que el cuerpo del **plan** lleve `lineas` con su `parcela_id`, que el de **lo hecho** siga llevando
`insumos`, y que sea **eso** lo que el servidor declara: si mañana alguien cambia el nombre de un lado y no
del otro, esto lo dice — en vez de perderse un dato en silencio.
"""

from __future__ import annotations

import os
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def el_fichero_de_la_aplicacion() -> pathlib.Path:
    """`app.js` — o el que diga `CUEDIGITAL_APP_JS`, **para poder comprobar que esta prueba muerde**.

    Con esa variable se le puede dar una copia con el defecto dentro y ver que se queja **sin tocar el
    fichero de verdad** (que es como se comprobó: la primera versión de esta prueba pasaba con la rama del
    plan desactivada, y eso es un guardián de mentira).
    """
    return pathlib.Path(os.environ.get("CUEDIGITAL_APP_JS", str(RAIZ / "web" / "app.js")))


ESQUEMAS = RAIZ / "app" / "schemas.py"


def el_cuerpo_del_formulario() -> str:
    """El trozo de `app.js` que arma el cuerpo que se manda al guardar un trabajo."""
    texto = el_fichero_de_la_aplicacion().read_text(encoding="utf-8")
    empieza = texto.index("function loEscritoEnLaFicha(")
    return texto[empieza : texto.index("\n}", empieza)]


def los_campos_de_una_clase(nombre: str) -> set[str]:
    """Los nombres de campo que declara una clase de `schemas.py`."""
    texto = ESQUEMAS.read_text(encoding="utf-8")
    empieza = texto.index(f"class {nombre}(")
    cuerpo = texto[empieza : texto.index("\nclass ", empieza + 1)]
    return {
        linea.split(":")[0].strip()
        for linea in cuerpo.splitlines()
        if re.match(r"^    [a-z_]+ *:", linea)
    }


def test_el_plan_manda_lo_que_el_plan_espera() -> None:
    cuerpo = el_cuerpo_del_formulario()
    # 0. **La rama del plan tiene que estar, y con su condición de verdad.** Esto se añadió después de
    #    descubrir que la primera versión de esta prueba pasaba con la rama desactivada (`if (false &&
    #    esPlan)`): mirar que el texto exista no es mirar que el camino se recorra.
    assert "if (esPlan)" in cuerpo, (
        "la rama del plan no está, o su condición ha cambiado: lo que se va a gastar se perdería"
    )
    # 1. El plan dice lo que va a gastar **por tierra**, y con su tierra.
    assert "lineas" in cuerpo, (
        "el formulario no manda `lineas` al planificar: lo que se va a gastar se perdería en silencio"
    )
    assert "parcela_id: laTierraDelFormulario" in cuerpo, (
        "la línea del plan tiene que decir **en qué tierra**, o el servidor no la puede guardar"
    )
    # 2. Y el servidor tiene que esperar eso mismo.
    campos_del_plan = los_campos_de_una_clase("TrabajoPrevistoEntrada")
    assert "lineas" in campos_del_plan, "el plan del servidor ya no espera `lineas`: mira el contrato"
    assert "insumos" not in campos_del_plan, (
        "el plan del servidor ahora espera `insumos`: entonces el formulario tiene que mandarlos así"
    )


def test_lo_hecho_sigue_mandando_sus_insumos() -> None:
    """Un trabajo **hecho** sí lleva `insumos` (lo que salió de verdad del almacén), y eso no se toca."""
    cuerpo = el_cuerpo_del_formulario()
    assert "insumos: [{ lote_id: lote, cantidad, unidad" in cuerpo, (
        "el formulario de lo hecho tiene que seguir mandando sus `insumos`: son los que descuentan del "
        "almacén"
    )
    assert "insumos" in los_campos_de_una_clase("TrabajoEntrada"), (
        "el trabajo hecho del servidor ya no espera `insumos`: mira el contrato"
    )


def test_la_comprobacion_reconoce_el_cuerpo_equivocado() -> None:
    """Y la prueba se comprueba a sí misma: con el cuerpo que estaba mal, tiene que quejarse.

    Sin esto, la prueba podría estar pasando por no mirar donde cree.
    """
    malo = "return lote && cantidad ? { ...comun, insumos: [{ lote_id: lote, cantidad, unidad }] } : comun;"
    assert "lineas" not in malo, "el detector no distingue un cuerpo sin `lineas`"
    assert "insumos: [{ lote_id: lote, cantidad, unidad" in malo, (
        "el detector no reconoce el cuerpo que se mandaba antes (el defecto)"
    )
