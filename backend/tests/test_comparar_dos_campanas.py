"""Comparar dos campanas, y decir cuando NO se pueden comparar (CRM-05, 14/10/2026).

El contrato lo pide con estas palabras: *«comparar campanas declara areas y cobertura distintas»*. Lo que se
prueba aqui es eso: que la puerta **no deja restar** dos campanas que no son comparables, que **dice por que**
(en palabras, no con un «no» seco), y que cuando no se puede restar **no devuelve un cero** que parezca una
respuesta.

Y el caso mas claro del criterio es este: **dos veces el mismo ano no es una comparacion de campanas** — es
la misma campana mirada dos veces.
"""

from __future__ import annotations


def _comparar(cliente, cuenta_o_quien, una, otra):
    return cliente.get(
        f"/api/campanas/comparar?una_id={una}&otra_id={otra}", headers=cuenta_o_quien["cabeceras"]
    )


def test_la_misma_campana_dos_veces_NO_es_comparable_y_lo_dice_con_palabras(cliente, cuenta, campana):
    # **El corazon del criterio**: comparar una campana consigo misma no es una comparacion, y la puerta tiene
    # que negarse — y decir por que, que es lo que permite al agricultor entenderlo.
    respuesta = _comparar(cliente, cuenta, campana["id"], campana["id"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["comparables"] is False, f"dos veces el mismo ano no se compara: {datos}"
    assert datos["y_por_que_no"], "y tiene que decir por que, no negarse en seco"
    assert any("ano" in m or "año" in m for m in datos["y_por_que_no"]), datos["y_por_que_no"]
    # **Y la diferencia NO es un cero**: un cero pareceria decir «no hay diferencia», que es otra cosa.
    assert datos["diferencia_de_hectareas"] is None, f"no se resta lo que no es comparable: {datos}"
    # Y las dos mitades se ensenan igual, con su cobertura al lado.
    for mitad in ("una", "otra"):
        assert datos[mitad]["hectareas"] is not None, datos
        assert "parcelas_sin_superficie" in datos[mitad], datos
        assert "la_superficie_es_parcial" in datos[mitad], "la cifra parcial se declara, no se calla"


def test_una_campana_sin_parcelas_trabajadas_tampoco_se_compara(cliente, cuenta, campana):
    # Una campana recien abierta no tiene apuntes, asi que no hay areas que comparar. Se dice, en vez de
    # ensenar 0 ha como si fuera un dato.
    datos = _comparar(cliente, cuenta, campana["id"], campana["id"]).json()
    assert any("parcela" in m for m in datos["y_por_que_no"]), datos["y_por_que_no"]
    assert datos["una"]["parcelas"] == 0, datos["una"]
    assert datos["una"]["apuntes"] == 0, datos["una"]
    assert datos["comparables"] is False, datos


def test_la_comparacion_de_otra_finca_no_se_ve(cliente, cuenta, campana, crear_cuenta):
    # **Aislamiento**: 404 sin distinguir «no existe» de «no es tuya», como en el resto de la casa.
    otra = crear_cuenta("comparar-campanas@ejemplo.test")
    respuesta = _comparar(cliente, otra, campana["id"], campana["id"])
    assert respuesta.status_code == 404, f"otra finca no deberia verla: {respuesta.status_code}"
    assert "anio" not in respuesta.text and "hectareas" not in respuesta.text, "ni filtrarse los campos"
