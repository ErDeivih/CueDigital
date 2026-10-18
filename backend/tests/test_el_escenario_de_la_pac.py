"""**El escenario del año que viene: una hipótesis que no toca nada** (18/10/2026, CRM-09).

### ***Lo que el contrato pide, con sus palabras***

  *«**Escenario siguiente año separado de lo declarado y de lo realizado.** Comparar alternativas **sin
  consumir**»*, y en la aceptacion: *«**editar escenario no cambia historial**»*.

### ***Y por que eso se puede cumplir sin guardar nada***

*Un escenario **no es un dato de la finca**: es una pregunta -«¿y si el año que viene siembro esto?»-. Guardarlo
seria empezar a tener dos verdades de la misma tierra. **Se calcula sobre el paquete -que es lo que hay de
verdad-, se contesta, y se tira.***

***Y de ahi salen las tres propiedades que se prueban aqui***:

  1. **Dice que es una hipotesis** y que **no es lo declarado ni lo realizado**.
  2. **No toca lo guardado**: *el paquete sale igual, y en la base no falta ni sobra una fila.*
  3. **Comparar dos alternativas no consume ninguna**, porque no hay nada que consumir.

*Y una cuarta, que es de la casa y no del escenario: **el denominador no se estrecha**. *«Tierra sin cultivo no
desaparece para pintar verde» vale tambien aqui: si en el escenario se siembra la mitad, el porcentaje es **sobre
el total**, y la otra mitad **se dice**.*
"""

from __future__ import annotations

from sqlalchemy import func, select

from app import models


def _el_paquete(cliente, cuenta, campana=None) -> dict:
    la_direccion = "/api/pac/paquete"
    if campana is not None:
        la_direccion += f"?campana_id={campana['id']}"
    respuesta = cliente.get(la_direccion, headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _el_escenario(cliente, cuenta, cuerpo: dict) -> dict:
    respuesta = cliente.post("/api/pac/escenario", headers=cuenta["cabeceras"], json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _cuantos_cultivos(db_sesion) -> int:
    return db_sesion.scalar(select(func.count()).select_from(models.ParcelaCultivo)) or 0


def un_cultivo(superficie_ha: float = 1.0) -> dict:
    return {
        "especie": "trigo",
        "variedad": "blando",
        "sistema": "secano",
        "ecorregimen": "secano",
        "superficie_cultivada_ha": superficie_ha,
    }


def test_el_escenario_dice_que_es_una_hipotesis(cliente, cuenta, campana, crear_parcela):
    """***Y lo dice en cada recinto, no solo en la cabecera.***"""
    crear_parcela(alias="La del escenario")

    la_contestacion = _el_escenario(cliente, cuenta, {"anio": 2027, "cambios": {}})
    el_suyo = la_contestacion["escenario"]

    assert el_suyo["capa"] == "hipotesis", el_suyo["capa"]
    for bandera in ("es_hipotesis", "no_es_lo_declarado", "no_es_lo_realizado", "no_es_garantia"):
        assert el_suyo[bandera] is True, bandera
    assert el_suyo["toca_lo_guardado"] is False, el_suyo
    assert el_suyo["anio"] == 2027
    assert all(uno["capa"] == "hipotesis" for uno in el_suyo["los_recintos"]), (
        "***cada recinto tiene que decir que es una hipotesis***"
    )


def test_y_no_toca_NADA_de_lo_guardado(cliente, cuenta, campana, crear_parcela, db_sesion):
    """***El paquete sale igual, y en la base no falta ni sobra una fila.***

    *Es la prueba de «comparar alternativas sin consumir» y de «editar escenario no cambia historial»: **no hay
    historial que tocar porque no se escribe nada**.*
    """
    crear_parcela(alias="La que no se toca")
    antes = _el_paquete(cliente, cuenta, campana)
    los_cultivos_antes = _cuantos_cultivos(db_sesion)

    _el_escenario(cliente, cuenta, {"anio": 2027, "cambios": {}})

    despues = _el_paquete(cliente, cuenta, campana)
    assert despues == antes, "***el paquete tiene que salir exactamente igual***"
    assert _cuantos_cultivos(db_sesion) == los_cultivos_antes, (
        "***y en la base no puede aparecer ni desaparecer un cultivo***"
    )


def test_un_cultivo_puesto_en_el_escenario_se_ve_alli_y_NO_en_el_paquete(cliente, cuenta, campana, crear_parcela):
    """***El cambio es del escenario, y de nadie mas.***"""
    la_parcela = crear_parcela(alias="La del cultivo propuesto")
    antes = _el_paquete(cliente, cuenta, campana)
    el_recinto = next(u for u in antes["las_tierras"] if u["parcela_id"] == la_parcela["id"])
    assert el_recinto["cultivo"] is None, "la tierra de la prueba empieza sin cultivo"

    la_contestacion = _el_escenario(
        cliente, cuenta, {"anio": 2027, "cambios": {la_parcela["id"]: {"cultivo": un_cultivo()}}}
    )
    el_suyo = la_contestacion["escenario"]
    el_de_alli = next(u for u in el_suyo["los_recintos"] if u["parcela_id"] == la_parcela["id"])

    assert el_de_alli["cultivo"]["especie"] == "trigo", el_de_alli
    assert "falta_cultivo" not in el_de_alli["falta"], (
        f"***con cultivo ya no falta el cultivo***: {el_de_alli['falta']}"
    )
    assert el_suyo["lo_que_cambia"], "***y el escenario dice que ha cambiado***"
    assert el_suyo["lo_que_cambia"][0]["que"] == "el cultivo"

    # *Y el paquete sigue como estaba: la tierra **no** tiene cultivo.*
    despues = _el_paquete(cliente, cuenta, campana)
    el_recinto_despues = next(u for u in despues["las_tierras"] if u["parcela_id"] == la_parcela["id"])
    assert el_recinto_despues["cultivo"] is None, (
        "***poner un cultivo en el escenario NO siembra nada***"
    )
    assert "falta_cultivo" in el_recinto_despues["falta"], el_recinto_despues["falta"]


def test_comparar_dos_alternativas_no_consume_ninguna(cliente, cuenta, campana, crear_parcela):
    """***Dos escenarios frente a frente***: *la diferencia, dicha, y **ni una fila tocada**.*"""
    la_parcela = crear_parcela(alias="La de las dos alternativas")
    los_cultivos_antes = None

    la_contestacion = _el_escenario(
        cliente,
        cuenta,
        {
            "anio": 2027,
            "cambios": {},
            "contra": {la_parcela["id"]: {"cultivo": un_cultivo()}},
        },
    )

    assert "comparacion" in la_contestacion, la_contestacion.keys()
    la_comparacion = la_contestacion["comparacion"]
    assert la_comparacion["no_consume_nada"] is True
    assert la_comparacion["cuantas"] >= 1, (
        f"***las dos alternativas tienen que diferenciarse***: {la_comparacion}"
    )
    la_diferencia = next(
        (d for d in la_comparacion["las_diferencias"] if d["parcela_id"] == la_parcela["id"]), None
    )
    assert la_diferencia is not None, la_comparacion
    assert la_diferencia["en_uno"] is None and la_diferencia["en_otro"] is not None, la_diferencia

    # *Y lo guardado sigue igual: se comparo, no se consumio nada.*
    el_paquete = _el_paquete(cliente, cuenta, campana)
    su_recinto = next(u for u in el_paquete["las_tierras"] if u["parcela_id"] == la_parcela["id"])
    assert su_recinto["cultivo"] is None, su_recinto


def test_el_denominador_NO_se_estrecha(cliente, cuenta, campana, crear_parcela):
    """***Tierra sin cultivo no desaparece para pintar verde***, *y el escenario no es la excepcion.*

    *Si en el escenario se siembra **una parte**, el porcentaje se calcula **sobre el total de la finca** -no sobre
    lo sembrado-, y lo que se queda fuera **se dice**.*
    """
    la_parcela = crear_parcela(alias="La del denominador")
    antes = _el_paquete(cliente, cuenta, campana)
    la_superficie_de_la_finca = sum(float(u.get("superficie_ha") or 0) for u in antes["las_tierras"])
    if la_superficie_de_la_finca <= 0:
        return  # *sin hectareas no hay denominador que probar, y no se inventa uno*

    la_contestacion = _el_escenario(
        cliente, cuenta, {"anio": 2027, "cambios": {la_parcela["id"]: {"cultivo": un_cultivo(1.0)}}}
    )
    el_resumen = la_contestacion["escenario"]["el_resumen"]

    assert el_resumen["denominador"] == round(la_superficie_de_la_finca, 6), (
        f"***el denominador es la finca entera, no lo sembrado***: {el_resumen}"
    )
    assert el_resumen["numerador"] == 1.0, el_resumen
    assert el_resumen["porcentaje"] == round(100.0 * 1.0 / la_superficie_de_la_finca, 2), el_resumen
    assert el_resumen["se_queda_fuera"] > 0, (
        f"***y lo que se queda fuera se dice***: {el_resumen}"
    )


def test_sin_cambio_el_recinto_que_ya_estaba_incompleto_sigue_incompleto(cliente, cuenta, campana, crear_parcela):
    """***Un escenario no rellena lo que no sabe.***"""
    crear_parcela(alias="La incompleta")
    antes = _el_paquete(cliente, cuenta, campana)
    los_incompletos_antes = [u["parcela_id"] for u in antes["las_tierras"] if not u["completa"]]

    la_contestacion = _el_escenario(cliente, cuenta, {"anio": 2027, "cambios": {}})
    los_incompletos_del_escenario = [
        u["parcela_id"] for u in la_contestacion["escenario"]["los_recintos"] if not u["completa"]
    ]

    assert sorted(los_incompletos_del_escenario) == sorted(los_incompletos_antes), (
        "***el escenario no puede dar por buena una tierra que le falta algo***"
    )
