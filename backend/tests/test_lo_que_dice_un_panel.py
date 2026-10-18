"""**Un panel: un numero que dice de donde sale** (CRM-11, 17/10/2026).

El contrato de la cola, con sus palabras:

    Contrato: valor nullable, unidad, periodo, finca/campana, filtros, cobertura, fuente y enlace.
    ***Hectareas de trabajo acumulado distintas de superficie unica; kg distintos de EUR.***
    ***Sin cumplimiento global que tape una regla critica no comprobada.***
"""

from __future__ import annotations

import pytest

from app import paneles


# ---------------------------------------------------------------------------
# 1 · Un numero sin unidad, o sin fuente, no es una metrica
# ---------------------------------------------------------------------------


def test_un_numero_sin_unidad_no_se_puede_enseñar():
    """***«3.500» no es una metrica; «3.500 kg» si.***

    *Y no es un tecnicismo: sin unidad no se sabe **con que se suma**, y un panel que suma cosas que no
    miden lo mismo esta mal aunque las cuentas salgan.*
    """
    with pytest.raises(paneles.MetricaSinOrigen) as fallo:
        paneles.la_metrica(
            clave="cosecha",
            titulo="Lo que se ha cogido",
            valor=3500,
            magnitud="fanegas",
            fuente="cuaderno",
            periodo="2026",
        )
    assert "no es una magnitud" in str(fallo.value), str(fallo.value)


def test_un_numero_sin_fuente_no_se_puede_discutir():
    """***«De donde sale» no es opcional.***

    *Un numero que no puede decir su fuente no se puede discutir, y lo que no se puede discutir no se puede
    corregir.*
    """
    with pytest.raises(paneles.MetricaSinOrigen) as fallo:
        paneles.la_metrica(
            clave="gasto",
            titulo="Lo que se ha gastado",
            valor=1200.0,
            magnitud=paneles.EUROS,
            fuente="",
            periodo="2026",
        )
    assert "no dice de donde sale" in str(fallo.value), str(fallo.value)


def test_una_metrica_buena_lleva_todo_lo_que_hace_falta():
    """Las ocho cosas del contrato, en una sola: *valor, unidad, periodo, finca, filtros, cobertura, fuente
    y enlace*."""
    suya = paneles.la_metrica(
        clave="tratamientos",
        titulo="Tratamientos del año",
        valor=12,
        magnitud=paneles.HECTAREAS_DE_TRABAJO,
        fuente="cuaderno",
        periodo="2026",
        cobertura={"contadas": 12, "de": 15},
        filtros={"campana": "2026"},
        finca_id=1,
        campana_id=2,
        enlace="#/cuaderno?tipo=tratamiento",
    )

    for campo in (
        "valor",
        "unidad",
        "periodo",
        "finca_id",
        "filtros",
        "cobertura",
        "fuente",
        "enlace",
    ):
        assert campo in suya, f"a la metrica le falta `{campo}`"
    assert suya["cobertura"] == {"contadas": 12, "de": 15}, "la cobertura no dice cuanto se ha mirado"


# ---------------------------------------------------------------------------
# 2 · ***Lo que NO se puede sumar***, que es la mitad del contrato
# ---------------------------------------------------------------------------


def test_las_hectareas_de_trabajo_no_son_las_de_superficie():
    """***El caso del contrato, tal cual***: *«hectareas de trabajo acumulado distintas de superficie unica»*.

    *Cinco labores en la misma parcela son **cinco veces** su superficie en trabajo y **una sola** en
    superficie. Sumarlas daria un numero que no existe.*
    """
    assert not paneles.se_pueden_sumar(
        paneles.HECTAREAS_DE_TRABAJO, paneles.HECTAREAS_DE_SUPERFICIE
    ), "***el trabajo acumulado y la superficie unica no se suman***"


def test_los_kilos_no_son_los_euros():
    """*«kg distintos de EUR»*: se parecen en que los dos son numeros grandes, y ahi se acaba."""
    assert not paneles.se_pueden_sumar(paneles.KILOS, paneles.EUROS)


def test_lo_mismo_si_se_suma():
    """Y lo que mide lo mismo, si: *sin esto, la regla de arriba no serviria para nada.*"""
    assert paneles.se_pueden_sumar(paneles.KILOS, paneles.KILOS)
    assert paneles.se_pueden_sumar(paneles.EUROS, paneles.EUROS)


def test_sumar_junta_lo_que_mide_lo_mismo_y_avisa_de_lo_que_no():
    """***No falla: avisa.*** *Un panel con dos metricas que no se pueden sumar no es un error del
    programa: es una pregunta mal hecha, y lo util es decir **cuales** se han quedado fuera.*"""
    kilos = paneles.la_metrica(
        clave="abono", titulo="Abono", valor=120.0, magnitud=paneles.KILOS, fuente="almacen",
        periodo="2026",
    )
    litros = paneles.la_metrica(
        clave="caldo", titulo="Caldo", valor=80.0, magnitud=paneles.LITROS, fuente="cuaderno",
        periodo="2026",
    )

    total = paneles.sumar(kilos, litros)

    assert total["valor"] == 120.0, "***solo se ha sumado lo que mide lo mismo***"
    assert total["sin_sumar"] == ["caldo"], f"y se dice cual se ha quedado fuera: {total}"


# ---------------------------------------------------------------------------
# 3 · ***Un cero y un «no lo se» no son lo mismo***
# ---------------------------------------------------------------------------


def test_un_valor_que_no_se_sabe_es_None_y_no_cero():
    """*`valor: null` es un valor legitimo, y la pantalla dice que no se sabe.*

    ***Y en una suma, un sumando que no se sabe hace que el total no se sepa***: *un total al que le falta un
    sumando no es un total mas pequeño, es un total que no se sabe.*
    """
    no_se_sabe = paneles.la_metrica(
        clave="cosecha", titulo="Cosecha", valor=None, magnitud=paneles.KILOS, fuente="cuaderno",
        periodo="2026",
    )
    assert no_se_sabe["valor"] is None, "***un cero y un «no lo se» son cosas distintas***"

    se_sabe = paneles.la_metrica(
        clave="abono", titulo="Abono", valor=120.0, magnitud=paneles.KILOS, fuente="almacen",
        periodo="2026",
    )
    total = paneles.sumar(no_se_sabe, se_sabe)
    assert total["valor"] is None, (
        "***con un sumando que no se sabe, el total NO se sabe (no es 120)***"
    )


# ---------------------------------------------------------------------------
# 4 · Y ninguna comprobacion que no se ha hecho se tapa
# ---------------------------------------------------------------------------


def test_lo_que_no_se_ha_comprobado_se_dice():
    """*«Sin cumplimiento global que tape una regla critica no comprobada.»*

    *Un panel que enseña un total verde con una regla sin comprobar debajo es peor que uno que no enseña
    nada.*
    """
    buena = paneles.la_metrica(
        clave="gasto", titulo="Gasto", valor=100.0, magnitud=paneles.EUROS, fuente="facturas",
        periodo="2026",
    )
    sin_dato = paneles.la_metrica(
        clave="cosecha", titulo="Cosecha", valor=None, magnitud=paneles.KILOS, fuente="cuaderno",
        periodo="2026",
    )

    pendientes = paneles.lo_que_no_se_ha_comprobado([buena, sin_dato])
    assert [m["clave"] for m in pendientes] == ["cosecha"], (
        f"***lo que no se ha comprobado tiene que salir: {pendientes}***"
    )


def test_las_dos_hermanas_salen_separadas_y_con_su_misma_fuente():
    """***El caso del contrato, montado y listo para un panel.***

    *Las dos metricas salen juntas -para poder enseñarlas al lado- y **con unidades distintas**, que es lo
    que impide que nadie las sume por descuido.*
    """
    superficie, trabajo = paneles.lo_de_una_superficie(
        12.5, hectarea_de_trabajo=40.0, fuente="cuaderno", periodo="2026"
    )

    assert superficie["unidad"] == paneles.HECTAREAS_DE_SUPERFICIE
    assert trabajo["unidad"] == paneles.HECTAREAS_DE_TRABAJO
    assert not paneles.se_pueden_sumar(superficie["unidad"], trabajo["unidad"]), (
        "***las dos salen del mismo sitio y NO se suman***"
    )
    assert superficie["fuente"] == trabajo["fuente"] == "cuaderno"


def test_lo_trabajado_para_un_tercero_NO_se_suma_con_lo_tuyo():
    """***10 ha de un tercero son trabajo, pero no son tu finca*** (CRM-11 con CRM-04, 17/10/2026).

    *La magnitud faltaba, y la falta se vio al querer enseñar las superficies en un panel: si las 10 ha de un
    trabajo para otro se apuntaran como `ha_de_trabajo`, `sumar` las juntaria con las tuyas **y la regla que
    existe para impedirlo quedaria saltada por arriba** -`superficies.py` lo dice con esas palabras: «10 ha de
    un tercero no suman superficie propia»-.*
    """
    from app import paneles

    assert paneles.HECTAREAS_DE_TERCERO in paneles.LAS_MAGNITUDES, (
        "***la magnitud tiene que estar, o no se puede enseñar sin mentir***"
    )
    assert not paneles.se_pueden_sumar(paneles.HECTAREAS_DE_TERCERO, paneles.HECTAREAS_DE_TRABAJO), (
        "***y no se suma con el trabajo de tu finca***"
    )
    assert not paneles.se_pueden_sumar(paneles.HECTAREAS_DE_TERCERO, paneles.HECTAREAS_DE_SUPERFICIE)

    # **Y `sumar` no falla: avisa**, que es lo que hace un panel -dice cuales se han quedado fuera-.
    tuyo = paneles.la_metrica(
        clave="trabajo", titulo="Trabajo", valor=30.0,
        magnitud=paneles.HECTAREAS_DE_TRABAJO, fuente="labores", periodo="2026",
    )
    ajeno = paneles.la_metrica(
        clave="de_tercero", titulo="De un tercero", valor=10.0,
        magnitud=paneles.HECTAREAS_DE_TERCERO, fuente="terceros", periodo="2026",
    )
    total = paneles.sumar(tuyo, ajeno)
    assert total["valor"] == 30.0, f"***el de un tercero NO entra en el total***: {total['valor']}"
    assert total["sin_sumar"] == ["de_tercero"], (
        f"***y se dice que se ha quedado fuera***: {total['sin_sumar']}"
    )
