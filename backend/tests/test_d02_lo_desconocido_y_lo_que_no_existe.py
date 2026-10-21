"""**D02: lo desconocido no es cero, y lo que no existe no se evalua** (21/10/2026).

### ***Las dos reproducciones del encargo, con sus palabras***

1. *«Con tierras sin superficie, el paquete devuelve denominador/porcentaje `null`, pero **el escenario suma los
   valores conocidos ignorando las ausencias y muestra total `290` y `0 %`**. Desconocido no es cero ni un total
   completo.»*
2. *«Una campaña inexistente (`campana_id=999999`) **permite evaluar y guardar una foto**, ambos con 200. Si se pide
   una campaña explícita inexistente o ajena, **rechazar sin revelar datos (404)** antes de evaluar/guardar;
   distinguirlo de no enviar campaña.»*

***Estas pruebas están escritas para FALLAR antes del arreglo***, y quedan como regresión después.
"""

from __future__ import annotations


def _el_escenario(cliente, cuenta, cuerpo: dict):
    return cliente.post("/api/pac/escenario", headers=cuenta["cabeceras"], json=cuerpo)


def _la_foto(cliente, cuenta, cuerpo: dict):
    return cliente.post("/api/pac/foto", headers=cuenta["cabeceras"], json=cuerpo)


# -----------------------------------------------------------------------------------------------------------
# 1 · Lo desconocido no es cero
# -----------------------------------------------------------------------------------------------------------


def test_una_tierra_sin_superficie_no_deja_publicar_un_porcentaje_completo(cliente, cuenta, campana, crear_parcela):
    """***Si falta una superficie, el total de la finca no se sabe.***

    *El escenario sumaba las conocidas (`or 0`) y publicaba `290` y `0 %`: **el agricultor leia «no he sembrado
    nada» cuando lo que pasaba es que **no consta** la superficie de una tierra.*
    """
    # *Una tierra **con** superficie y otra **sin** ella.* **La fixture acepta cambios**: *su tierra por defecto
    # tiene 2.43 ha -y al crearla «sin superficie» salía con esa, así que la prueba no probaba nada-.*
    crear_parcela(alias="Con superficie", superficie_ha=10.0)
    crear_parcela(alias="Sin superficie", superficie_ha=None)

    la_contestacion = _el_escenario(cliente, cuenta, {"anio": 2027})
    assert la_contestacion.status_code == 200, la_contestacion.text
    el_resumen = la_contestacion.json()["escenario"]["el_resumen"]

    assert el_resumen["conocido"] is False, (
        f"***falta la superficie de una tierra: el total NO se sabe***: {el_resumen}"
    )
    assert el_resumen["porcentaje"] is None, (
        f"***un porcentaje completo seria mentira***: {el_resumen}"
    )
    assert el_resumen["denominador"] is None, el_resumen
    assert el_resumen["las_tierras_sin_superficie"] >= 1, el_resumen
    assert el_resumen["aviso"], "***y tiene que decir por que***"


def test_y_sin_faltas_el_porcentaje_si_se_da(cliente, cuenta, campana, crear_parcela):
    """***El control positivo***: *con todas las superficies, el porcentaje se publica como siempre.*"""
    crear_parcela(alias="La completa", superficie_ha=10.0)

    la_contestacion = _el_escenario(cliente, cuenta, {"anio": 2027})
    el_resumen = la_contestacion.json()["escenario"]["el_resumen"]

    assert el_resumen["conocido"] is True, el_resumen
    # *El total es el de la finca -la fixture puede dejar más tierras-, pero **tiene que cuadrar con las que hay**.*
    assert el_resumen["denominador"] > 0, el_resumen
    assert el_resumen["porcentaje"] is not None, (
        f"***con todas las superficies si hay porcentaje***: {el_resumen}"
    )


# -----------------------------------------------------------------------------------------------------------
# 2 · Una campaña que no existe (o es de otra finca) se rechaza sin evaluar ni guardar
# -----------------------------------------------------------------------------------------------------------


def test_una_campana_que_no_existe_da_404_y_no_evalua(cliente, cuenta, campana, crear_parcela):
    """***404, y sin evaluar***: *no se puede calcular sobre un año que no es de esta finca.*"""
    crear_parcela(alias="La de la campaña fantasma")

    la_contestacion = _el_escenario(cliente, cuenta, {"anio": 2027, "campana_id": 999999})
    assert la_contestacion.status_code == 404, (
        f"***una campaña inexistente tiene que dar 404, no {la_contestacion.status_code}***: "
        f"{la_contestacion.text[:300]}"
    )


def test_y_una_campana_que_no_existe_no_guarda_foto(cliente, cuenta, campana, crear_parcela):
    """***Y tampoco guarda***: *el «sin revelar datos» vale para las dos puertas.*"""
    crear_parcela(alias="La de la foto fantasma")

    la_foto = _la_foto(cliente, cuenta, {"anio": 2027, "campana_id": 999999})
    assert la_foto.status_code == 404, (
        f"***no se puede guardar sobre una campaña inexistente***: {la_foto.status_code} {la_foto.text[:300]}"
    )

    # *Y no se ha escrito nada: el historial sigue vacío.*
    el_historial = cliente.get("/api/pac/foto/historial", headers=cuenta["cabeceras"])
    if el_historial.status_code == 200:
        assert not el_historial.json().get("las_fotos"), el_historial.text[:300]


def test_y_la_campana_de_OTRA_finca_tambien_da_404(cliente, cuenta, campana, crear_parcela, crear_cuenta):
    """***De otra finca, igual***: *y **sin decir que existe**, que es lo que pide «sin revelar datos».*"""
    crear_parcela(alias="La de la campaña ajena")
    la_otra = crear_cuenta("la-de-la-campana-ajena@ejemplo.test")

    # *La campaña de la otra finca, pedida desde esta.*
    la_contestacion = cliente.post(
        "/api/pac/escenario",
        headers=la_otra["cabeceras"],
        json={"anio": 2027, "campana_id": campana["id"]},
    )
    assert la_contestacion.status_code == 404, (
        f"***la campaña de otra finca no se puede usar***: {la_contestacion.status_code}"
    )


def test_sin_campana_explicita_se_sigue_usando_la_ultima(cliente, cuenta, campana, crear_parcela):
    """***Y no mandar campaña NO es un error***: *se usa la última, como siempre. Distinguirlo es lo que pide el
    encargo.*"""
    crear_parcela(alias="La de la campaña por defecto")
    la_contestacion = _el_escenario(cliente, cuenta, {"anio": 2027})
    assert la_contestacion.status_code == 200, la_contestacion.text
    assert la_contestacion.json()["escenario"]["anio"] == 2027
