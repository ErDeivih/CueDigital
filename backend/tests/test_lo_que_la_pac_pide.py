"""**La preparacion de la PAC: la fuente manda, y lo que falta se dice** (CRM-09, 17/10/2026).

El contrato de la cola, con sus palabras:

    ***fuente de otra campaña/comunidad no se aplica***; falta area/cultivo/evidencia -> incompleto
    ***Porcentajes con numerador/denominador; tierra sin cultivo no desaparece para pintar verde.***
    ***ninguna competencia autoriza usar su interpretacion como norma***.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import pac

UN_DIA = dt.date(2026, 6, 1)


def una_fuente(**cambios):
    cuerpo = {
        "referencia": "Orden de la Junta, campaña 2026",
        "ambito": "autonomico",
        "anio": 2026,
        "desde": dt.date(2026, 1, 1),
        "hasta": dt.date(2026, 12, 31),
        "version": "1",
    }
    cuerpo.update(cambios)
    return pac.la_fuente(**cuerpo)


# ---------------------------------------------------------------------------
# 1 · ***«Fuente de otra campaña o de otra comunidad no se aplica»***
# ---------------------------------------------------------------------------


def test_una_fuente_de_OTRA_campana_no_se_aplica():
    """***El caso del contrato, tal cual.*** *Una ayuda de 2023 no se pide en 2026 con las reglas de 2023.*"""
    la_de_2026 = una_fuente(anio=2026)

    assert pac.se_aplica_a(la_de_2026, ambito="autonomico", campana=2026, cuando=UN_DIA)
    assert not pac.se_aplica_a(la_de_2026, ambito="autonomico", campana=2027, cuando=UN_DIA), (
        "***una fuente de otra campaña no se aplica***"
    )


def test_una_fuente_de_OTRA_comunidad_tampoco():
    """*«Es de mi comunidad» no basta: tiene que ser **de mi comunidad, y de mi año**.*"""
    la_mia = una_fuente(ambito="autonomico")
    assert not pac.se_aplica_a(la_mia, ambito="estatal", campana=2026, cuando=UN_DIA)


def test_y_una_caducada_o_que_aun_no_ha_entrado_tampoco():
    """***Las fechas de vigencia son parte de la fuente***, no un adorno.

    *Una norma que ya ha caducado no se puede citar como si mandara hoy, y una que aun no ha entrado en
    vigor, menos.*
    """
    caducada = una_fuente(desde=dt.date(2024, 1, 1), hasta=dt.date(2024, 12, 31), anio=2026)
    assert not pac.se_aplica_a(caducada, ambito="autonomico", campana=2026, cuando=UN_DIA)

    futura = una_fuente(desde=dt.date(2026, 9, 1), hasta=dt.date(2026, 12, 31))
    assert not pac.se_aplica_a(futura, ambito="autonomico", campana=2026, cuando=UN_DIA), (
        "***una norma que aun no ha entrado en vigor no manda todavia***"
    )


def test_la_que_manda_es_la_de_version_mas_nueva():
    """*La que deroga a la anterior es la que vale.* Y si no hay ninguna, **se dice que no hay ninguna**."""
    vieja = una_fuente(version="1")
    nueva = una_fuente(version="3", referencia="Orden que modifica la anterior")

    assert pac.la_que_aplica(
        [vieja, nueva], ambito="autonomico", campana=2026, cuando=UN_DIA
    )["version"] == "3"
    assert pac.la_que_aplica([vieja], ambito="autonomico", campana=2030, cuando=UN_DIA) is None, (
        "sin fuente que aplique, se dice que no hay: **no se coge la que haya**"
    )


def test_una_fuente_sin_ambito_no_se_sabe_a_quien_aplica():
    with pytest.raises(pac.FuenteQueNoAplica) as fallo:
        una_fuente(ambito="donde sea")
    assert "no es un ambito" in str(fallo.value), str(fallo.value)


def test_la_fuente_lleva_dentro_el_aviso_de_que_no_es_la_norma():
    """*«Ninguna competencia autoriza usar su interpretacion como norma.»*

    ***Y el aviso viaja con la fuente***, para que no se pueda citar una sin el otro.
    """
    assert "no es la norma" in una_fuente()["aviso"], una_fuente()["aviso"]


# ---------------------------------------------------------------------------
# 2 · ***«Porcentajes con numerador/denominador»***
# ---------------------------------------------------------------------------


def test_un_porcentaje_sin_denominador_no_se_da():
    """***«El 80%» no dice el 80% de que.*** *Y en la PAC eso es la diferencia entre una parcela y toda la
    comarca.*"""
    with pytest.raises(pac.PorcentajeSinDenominador):
        pac.el_porcentaje(numerador=80, denominador=None, de_que="lo que sea")


def test_un_porcentaje_lleva_sus_dos_numeros_a_la_vista():
    """*Para poder discutirlo: un porcentaje del que no se ven las partes no se puede comprobar.*"""
    suyo = pac.el_porcentaje(numerador=30, denominador=60, de_que="parcelas con cultivo")
    assert suyo["numerador"] == 30
    assert suyo["denominador"] == 60
    assert suyo["porcentaje"] == 50.0
    assert suyo["de_que"] == "parcelas con cultivo", "y se dice **de que** es"


def test_cero_de_cero_no_es_cero_por_ciento():
    """***Es que no hay nada que medir.*** *Un cero ahi pintaria un mapa de un color que no es verdad.*"""
    suyo = pac.el_porcentaje(numerador=0, denominador=0, de_que="sin datos")
    assert suyo["porcentaje"] is None, "***0 de 0 no es 0%***"
    assert "no hay denominador" in suyo["aviso"]


# ---------------------------------------------------------------------------
# 3 · ***«Tierra sin cultivo no desaparece para pintar verde»***
# ---------------------------------------------------------------------------


def test_la_tierra_sin_cultivo_no_desaparece():
    """***El caso del contrato, y el mas facil de hacer mal.***

    *Con el denominador tramposo -solo las 60 con cultivo-, esto saldria al **100%** y nadie veria las 40
    que se han quedado fuera. Un panel que se hace el mapa mas bonito es un panel que engaña.*
    """
    suyo = pac.tierra_sin_cultivo_no_se_pinta_de_verde(
        superficie_total=100.0, superficie_con_cultivo=60.0
    )

    assert suyo["denominador"] == 100.0, "***el denominador es la finca entera, no lo sembrado***"
    assert suyo["porcentaje"] == 60.0, "***y por eso sale 60%, no 100%***"
    assert suyo["sin_cultivo"] == 40.0, "***y las 40 que se quedan fuera se dicen***"
    assert suyo["se_queda_fuera"] == 40.0


def test_si_toda_la_finca_tiene_cultivo_no_hay_nada_que_decir():
    """*El otro lado: cuando no falta nada, no se inventa un aviso.*"""
    suyo = pac.tierra_sin_cultivo_no_se_pinta_de_verde(
        superficie_total=50.0, superficie_con_cultivo=50.0
    )
    assert suyo["porcentaje"] == 100.0
    assert suyo["se_queda_fuera"] == 0
