"""**Lo que cada uno puede cambiar de su pantalla** (CRM-11, 17/10/2026).

El contrato de la cola lo pide asi: *«Preferencias por usuario: orden de tarjetas, vistas/columnas/filtros
guardados, pantalla inicial, restablecer vista; ***no personalizar limites legales ni alterar datos
compartidos***»*.

***Y esas dos mitades son la misma frase***: se puede cambiar **como se mira**, y **no** se puede cambiar **lo
que hay**. *Es la diferencia entre mover los muebles de casa y mover las paredes.*
"""

from __future__ import annotations

import pytest

from app import preferencias


# ---------------------------------------------------------------------------
# 1 · ***Lo que NO se personaliza***
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cual",
    ["plazo_de_seguridad", "limites_legales", "dosis_maxima", "superficie_declarada", "datos_compartidos"],
)
def test_un_limite_legal_o_un_dato_compartido_no_se_personaliza(cual):
    """***La regla de oro del ticket***: *«no personalizar limites legales ni alterar datos compartidos»*.

    ***Y se para, no se ignora en silencio***: si alguien intenta guardar eso, tiene que enterarse. *Un
    limite legal que se pudiera cambiar desde la pantalla de uno seria una ley distinta para cada
    agricultor.*
    """
    with pytest.raises(preferencias.PreferenciaQueNoSeToca) as fallo:
        preferencias.guardar_la_preferencia(cual, "lo que sea")

    assert "no se personaliza" in str(fallo.value), str(fallo.value)


def test_se_mira_por_el_nombre_y_no_por_una_lista_cerrada():
    """*Una lista de campos exactos se queda corta en cuanto alguien añade `plazo_de_entrada`.*

    ***Por eso se mira el nombre***: lo que se prohibe es **la clase de cosa**, no las cinco que se
    acordaron el primer dia.
    """
    # `plazo_de_entrada` no esta en ninguna lista, y tiene que parar igual.
    with pytest.raises(preferencias.PreferenciaQueNoSeToca):
        preferencias.guardar_la_preferencia("mi_plazo_de_entrada", 30)


def test_una_preferencia_que_no_es_de_las_de_aqui_tampoco():
    """Y una que ni toca la ley ni es de la vista: se dice **cuales** son, para no dejar a nadie adivinando."""
    with pytest.raises(preferencias.PreferenciaQueNoSeToca) as fallo:
        preferencias.guardar_la_preferencia("color_del_boton", "verde")

    assert "no es una preferencia" in str(fallo.value), str(fallo.value)


# ---------------------------------------------------------------------------
# 2 · Lo que si, y sin llevarse por delante lo demas
# ---------------------------------------------------------------------------


def test_una_preferencia_buena_se_guarda_sin_tocar_las_demas():
    """***«Lo que no se ha tocado, no se toca.»***

    *Guardar el orden de las tarjetas no puede borrar las columnas que ya estaban elegidas.*
    """
    antes = {"columnas": ["fecha", "importe"], "pantalla_inicial": "hoy"}
    despues = preferencias.guardar_la_preferencia(
        preferencias.ORDEN_DE_TARJETAS, ["trabajo", "economia"], las_de_antes=antes
    )

    assert despues[preferencias.ORDEN_DE_TARJETAS] == ["trabajo", "economia"]
    assert despues["columnas"] == ["fecha", "importe"], "***las columnas de antes siguen ahi***"
    assert despues["pantalla_inicial"] == "hoy"
    assert antes == {"columnas": ["fecha", "importe"], "pantalla_inicial": "hoy"}, (
        "y lo que le pasaron no se ha modificado"
    )


# ---------------------------------------------------------------------------
# 3 · ***El orden, que no puede esconder una tarjeta nueva***
# ---------------------------------------------------------------------------


def test_el_orden_no_puede_esconder_una_tarjeta_que_no_estaba():
    """***La peor forma de perder un dato es que no salga y nadie lo note.***

    *Una preferencia guardada hace meses no puede hacer que una tarjeta nueva no salga nunca: las que no
    estaban en el orden van **al final**, en el suyo.*
    """
    ordenadas = preferencias.el_orden_de_las_tarjetas(
        ["economia", "trabajo"], todas=["trabajo", "economia", "campana"]
    )

    assert ordenadas == ["economia", "trabajo", "campana"], ordenadas
    assert set(ordenadas) == {"trabajo", "economia", "campana"}, "***no se ha perdido ninguna***"


def test_una_tarjeta_del_orden_que_ya_no_existe_se_ignora():
    """*Al contrario: una tarjeta que ya no existe se cae del orden **sin romper nada**.*"""
    ordenadas = preferencias.el_orden_de_las_tarjetas(["economia", "ya_no_existe"], todas=["trabajo", "economia"])
    assert ordenadas == ["economia", "trabajo"]


@pytest.mark.parametrize("roto", [None, "", {}, 7, "economia"])
def test_un_orden_roto_devuelve_todas_las_tarjetas(roto):
    """***Ante la duda, todo***: una preferencia rota no puede dejar la pantalla vacia.

    *Es la misma regla que el resto del programa: lo que no se entiende **no se convierte en nada**, se
    ignora y se sigue.*
    """
    assert preferencias.el_orden_de_las_tarjetas(roto, todas=["a", "b", "c"]) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# 4 · Restablecer
# ---------------------------------------------------------------------------


def test_restablecer_deja_la_vista_como_venia_de_fabrica():
    """***«Restablecer vista»***: se olvida **todo** lo de la vista. *Y solo la vista.*"""
    assert preferencias.restablecer({"columnas": ["a"], "pantalla_inicial": "hoy"}) == {}
    assert preferencias.restablecer(None) == {}
