"""**El panel: las metricas, con su fuente y su cobertura** (CRM-11, 17/10/2026).

### ***Por que existe esta prueba***

`app/paneles.py` tenia **el contrato entero** -la metrica con su unidad, la negativa a sumar peras con
manzanas, el aviso de lo que no se ha comprobado- y ***no lo llamaba nadie***: ni una referencia en `app/`, y
ninguna puerta que sirviera una metrica. *Es el mayor «solo existe en servidor» de esta sesion: **ni siquiera
estaba en el servidor**, estaba en un fichero que nadie importaba.*

Lo que defiende esta prueba, y es lo que el contrato pide con sus palabras -«***valor nullable, unidad,
periodo, finca/campana, filtros, cobertura, fuente y enlace***»-:

  1. Que la puerta **conteste**, y con las metricas **enteras**: cada una dice **en que se mide**, **de donde
     sale** y **cuanto ha mirado**.
  2. Que ***lo que no se sabe vaya como `None` y no como cero***: *un gasto sin importe hace que el total de
     gastos **no se sepa**, y eso es distinto de «no se ha gastado nada».*
  3. Que ***lo de un tercero sea su propia magnitud*** y no se cuele en el trabajo de la finca.
  4. Que la puerta **diga lo que no se puede dar por bueno** (`sin_comprobar`), que es la regla «sin
     cumplimiento global que tape una regla critica no comprobada».
"""

from __future__ import annotations


def el_panel(cliente, cuenta) -> dict:
    respuesta = cliente.get("/api/panel", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_la_puerta_contesta_y_cada_metrica_dice_lo_que_hace_falta(cliente, cuenta, crear_parcela):
    crear_parcela(alias="El Prado", superficie_ha=2.43)

    datos = el_panel(cliente, cuenta)
    las = datos["las_metricas"]

    assert len(las) >= 5, f"***el panel tiene que traer sus metricas***: {[m['clave'] for m in las]}"
    for una in las:
        assert una.get("fuente"), f"***un numero sin fuente no se puede discutir***: {una['clave']}"
        assert una.get("unidad"), f"sin unidad no es una metrica: {una['clave']}"
        assert "cobertura" in una, f"sin cobertura un total parece completo: {una['clave']}"
        assert una.get("pregunta") is not None, f"sin pregunta no se sabe que mide: {una['clave']}"
        assert "valor" in una, f"`valor` tiene que venir, aunque sea `None`: {una['clave']}"


def test_la_superficie_de_la_finca_sale_con_su_cobertura(cliente, cuenta, crear_parcela):
    crear_parcela(alias="Con hectáreas", superficie_ha=2.43)
    crear_parcela(alias="Sin hectáreas", superficie_ha=None)

    la_superficie = next(
        una for una in el_panel(cliente, cuenta)["las_metricas"] if una["clave"] == "superficie"
    )

    assert la_superficie["unidad"] == "ha_de_superficie"
    # ***Una tierra sin superficie hace que el total NO SE SEPA***, y la cobertura lo dice.
    assert la_superficie["valor"] is None, (
        f"***con una tierra sin medir, el total no se puede afirmar***: {la_superficie['valor']}"
    )
    assert la_superficie["cobertura"] == {"contadas": 1, "de": 2}


def test_un_gasto_sin_importe_hace_que_el_total_de_gastos_NO_SE_SEPA(cliente, cuenta, campana):
    cliente.post(
        "/api/gastos",
        headers=cuenta["cabeceras"],
        json={"campana_id": campana["id"], "concepto": "Gasóleo", "importe": "100.00"},
    )
    # **El segundo, sin importe**: «no me acuerdo de cuánto» es un estado de verdad.
    assert (
        cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "concepto": "La reparación"},
        ).status_code
        in (200, 201)
    )

    los_gastos = next(
        una for una in el_panel(cliente, cuenta)["las_metricas"] if una["clave"] == "gastos"
    )

    assert los_gastos["unidad"] == "EUR", "los euros no son kilos"
    assert los_gastos["valor"] is None, (
        f"***un total al que le falta un sumando NO es un total mas pequeño***: {los_gastos['valor']}"
    )
    assert los_gastos["cobertura"]["contadas"] == 1, los_gastos["cobertura"]
    assert los_gastos["cobertura"]["de"] == 2


def test_lo_de_un_tercero_es_su_propia_magnitud_y_no_se_cuela_en_lo_tuyo():
    """*La magnitud que faltaba*: **10 ha de un tercero son trabajo, pero no son tu finca**."""
    from app import paneles

    assert paneles.HECTAREAS_DE_TERCERO in paneles.LAS_MAGNITUDES
    assert not paneles.se_pueden_sumar(paneles.HECTAREAS_DE_TERCERO, paneles.HECTAREAS_DE_TRABAJO)


def test_la_puerta_dice_lo_que_no_se_puede_dar_por_bueno(cliente, cuenta, crear_parcela):
    """*«Sin cumplimiento global que tape una regla critica no comprobada».*"""
    crear_parcela(alias="Sin hectáreas", superficie_ha=None)

    datos = el_panel(cliente, cuenta)

    assert "sin_comprobar" in datos, "el panel tiene que decir lo que no se puede dar por bueno"
    claves = [una["clave"] for una in datos["sin_comprobar"]]
    assert "superficie" in claves, (
        f"***una metrica sin valor es una metrica que no se puede dar por buena***: {claves}"
    )


def test_el_panel_dice_que_parejas_de_cifras_no_se_suman(cliente, cuenta):
    """*«Hectareas de trabajo acumulado distintas de superficie unica; kg distintos de EUR».*"""
    datos = el_panel(cliente, cuenta)
    parejas = {(una["una"], una["otra"]) for una in datos["lo_que_no_se_suma"]}

    assert ("ha_de_trabajo", "ha_de_superficie") in parejas, "el trabajo no es la superficie"
    assert ("kg", "EUR") in parejas, "los kilos no son euros"
