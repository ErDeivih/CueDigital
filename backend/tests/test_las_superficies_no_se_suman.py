"""**Las superficies, y por que no se suman entre si** (CRM-06, 17/10/2026).

El caso de aceptacion es del COLA, literal: ***«trabajo externo 10 ha no suma superficie propia»***. Y los
criterios de la revision: *«No sobreescribir una con otra ni sumarlas como si fueran la misma magnitud. Dosis
kg/ha usa la **superficie tratada de ese hecho**… **desconocido no es cero**»*.
"""

from __future__ import annotations

from app import superficies


# ---------------------------------------------------------------------------
# 1 · El caso de aceptacion, y es el que importa
# ---------------------------------------------------------------------------


def test_un_tercero_de_10_ha_NO_suma_superficie_propia():
    """***«trabajo externo 10 ha no suma superficie propia»***, literal del COLA.

    Las dos cuentas **existen** -la finca tiene 50 ha y al tercero le hiciste 10-, y las dos se pueden decir.
    Lo que **no** se puede es sumarlas: *tu finca no crece porque hayas arado la del vecino*.
    """
    finca = [{"superficie_ha": 30.0}, {"superficie_ha": 20.0}]
    suya = superficies.la_superficie_de_la_finca(finca)
    del_tercero = superficies.lo_de_un_tercero([{"superficie_ha": 10.0}])

    assert suya["total"] == 50.0, "***la finca son 50 ha***"
    assert del_tercero["total"] == 10.0, "y al tercero se le hicieron 10"

    assert (
        superficies.se_pueden_sumar(superficies.LO_QUE_SE_CULTIVA, superficies.LO_DE_UN_TERCERO)
        is False
    ), "***y las dos NO son la misma magnitud***"
    assert superficies.LO_DE_UN_TERCERO in superficies.LAS_MAGNITUDES


def test_lo_de_un_tercero_tiene_su_propia_pregunta():
    """Y esta escrita, para que el error se pueda **explicar** y no sea un numero raro."""
    assert "no son tuyas" in superficies.LA_PREGUNTA[superficies.LO_DE_UN_TERCERO]
    assert "plantado" in superficies.LA_PREGUNTA[superficies.LO_QUE_SE_CULTIVA]


def test_dos_trozos_de_lo_mismo_SI_se_suman():
    """Lo que si se suma: dos parcelas, para saber lo que se cultiva. Es la **misma** pregunta."""
    assert superficies.se_pueden_sumar(superficies.LO_QUE_SE_CULTIVA, superficies.LO_QUE_SE_CULTIVA)
    assert superficies.se_pueden_sumar(
        superficies.LO_TRATADO_DE_UN_HECHO, superficies.LO_TRATADO_DE_UN_HECHO
    )
    # Y lo que no.
    assert not superficies.se_pueden_sumar(
        superficies.LO_QUE_DICE_EL_SIGPAC, superficies.LO_QUE_SE_CULTIVA
    )


# ---------------------------------------------------------------------------
# 2 · «Desconocido no es cero», aplicado a las hectareas
# ---------------------------------------------------------------------------


def test_una_parcela_sin_superficie_hace_que_el_total_SEA_DESCONOCIDO():
    """***Un total al que le falta un trozo no es el total.***

    Sumar saltandose la parcela que no tiene superficie da un numero **mas pequeno que el de verdad**, y en
    una declaracion eso no es un redondeo: es una cifra falsa. Se dice **que falta**, y `None`.
    """
    suyo = superficies.la_superficie_de_la_finca(
        [{"superficie_ha": 30.0}, {"superficie_ha": None}, {"superficie_ha": 20.0}]
    )

    assert suyo["total"] is None, "***no es 50: es que no se sabe***"
    assert suyo["sin_superficie"] == 1, "y se dice cuantas faltan"
    assert suyo["sumandos"] == 2
    assert superficies.FALTA_UNA_SUPERFICIE in suyo["lo_que_falta"]


def test_y_un_CERO_de_verdad_si_cuenta_como_cero():
    """Un `0.0` declarado es un dato -esa tierra no se cultiva-, y **no** es lo mismo que un hueco."""
    suyo = superficies.la_superficie_de_la_finca([{"superficie_ha": 30.0}, {"superficie_ha": 0.0}])

    assert suyo["total"] == 30.0
    assert suyo["sin_superficie"] == 0
    assert suyo["lo_que_falta"] == []


def test_una_magnitud_que_no_existe_se_dice():
    suyo = superficies.suma_lo_mismo(magnitud="hectareas_de_lo_que_sea", valores=[1.0])

    assert suyo["total"] is None
    assert superficies.NO_ES_UNA_MAGNITUD in suyo["lo_que_falta"]


# ---------------------------------------------------------------------------
# 3 · La tratada es la del HECHO, no la de la tierra
# ---------------------------------------------------------------------------


def test_lo_tratado_sale_de_cada_hecho_y_no_de_la_ficha_de_la_tierra():
    """***«Dosis kg/ha usa la superficie tratada de ESE hecho.»***

    Si un tratamiento se hizo en media parcela, entra **media**. Coger la superficie de la tierra entera
    daria el doble de producto, y eso se declara.
    """
    suyo = superficies.lo_tratado(
        [
            {"superficie_tratada_ha": 1.5, "superficie_ha": 3.0},
            {"superficie_tratada_ha": 2.0, "superficie_ha": 8.0},
        ]
    )

    assert suyo["total"] == 3.5, "***1,5 + 2,0: lo que se trato, no lo que mide la tierra***"
    assert superficies.LO_TRATADO_DE_UN_HECHO != superficies.LO_QUE_SE_CULTIVA


def test_la_dosis_usa_la_superficie_del_hecho_y_no_la_de_la_parcela():
    """El caso del contrato: 2 L en 4 ha -> 0,5 L/ha. **Y sin superficie, desconocido.**"""
    assert superficies.la_dosis_por_hectarea(cantidad=2.0, superficie_tratada_ha=4.0) == 0.5
    assert superficies.la_dosis_por_hectarea(cantidad=2.0, superficie_tratada_ha=None) is None, (
        "***sin area, desconocido: NO cero***"
    )
    assert superficies.la_dosis_por_hectarea(cantidad=2.0, superficie_tratada_ha=0.0) is None
    assert superficies.la_dosis_por_hectarea(cantidad=None, superficie_tratada_ha=4.0) is None
