"""**La tabla y la ficha** (contrato comun, 17/10/2026).

El contrato comun de la cola lo dice asi:

    227  Finca/campaña visibles, busqueda, navegacion coherente y ***ficha unica por entidad***.
    228  Tabla: busqueda, filtros activos, orden, columnas, ***pie X de Y*** y ***seleccion explicita***;
         ***acciones contextuales*** y exportacion que declare si incluye filtrados o todos.
"""

from __future__ import annotations

import pytest

from app import la_tabla as t


# ---------------------------------------------------------------------------
# 1 · ***«Seleccion explicita»***
# ---------------------------------------------------------------------------


def test_lo_marcado_que_ya_no_esta_se_dice_y_no_cuenta():
    """***La accion no se puede hacer sobre algo que no existe.***

    *Si algo se ha borrado, o ya no esta en la lista filtrada, no puede seguir contando como marcado -pero
    **tampoco se pierde en silencio**: se dice cual.*
    """
    seleccion = t.la_seleccion([1, 2, 99], de_los_que_hay=[1, 2, 3])

    assert seleccion["marcados"] == [1, 2], "***lo que ya no esta no cuenta***"
    assert seleccion["cuantos"] == 2
    assert seleccion["ya_no_estan"] == [99], "***y se dice cual, en vez de perderse***"


def test_ordenar_por_otra_columna_no_pierde_la_seleccion():
    """***El error que mas duele.***

    *El agricultor marca doce cosas, ordena por otra columna -que repinta la tabla- y la accion se hace sobre
    tres. **Sin enterarse.** Por eso, si no se dice nada nuevo, lo de antes se respeta.*
    """
    primera = t.la_seleccion([7, 8], de_los_que_hay=[7, 8, 9])

    # Al repintar, la pantalla no vuelve a decir que hay marcado: **se le pasa lo de antes**.
    despues = t.la_seleccion(None, de_los_que_hay=[9, 8, 7], lo_de_antes=primera["marcados"])

    assert sorted(despues["marcados"]) == [7, 8], "***ordenar no desmarca***"
    assert despues["cuantos"] == 2


def test_sin_nada_marcado_se_dice_que_no_hay_seleccion():
    """*«Accion sobre 0 elementos» es peor que no ofrecer la accion.*"""
    vacia = t.la_seleccion([], de_los_que_hay=[1, 2])
    assert vacia["hay_seleccion"] is False
    assert vacia["cuantos"] == 0


# ---------------------------------------------------------------------------
# 2 · ***«Acciones contextuales»***
# ---------------------------------------------------------------------------


def test_una_accion_que_exige_seleccion_se_apaga_con_su_motivo():
    """***«Apagada, no escondida.»***

    *Una accion que no se puede hacer y **no esta**, se busca; una que **esta apagada**, se entiende.* **Y con
    el motivo**: «Elige uno de la lista» es una instruccion; «no se puede» es un muro.*
    """
    acciones = t.las_acciones_que_aplican(
        [{"nombre": "borrar", "cuantos": 1}, {"nombre": "exportar", "cuantos": 0}], cuantos_marcados=0
    )

    borrar = next(a for a in acciones if a["nombre"] == "borrar")
    exportar = next(a for a in acciones if a["nombre"] == "exportar")

    assert borrar["activa"] is False, "***exige uno y no hay ninguno***"
    assert borrar["motivo"] == "Elige uno de la lista", "***y se dice que hacer***"
    assert exportar["activa"] is True, "***exportar no exige nada***"
    assert len(acciones) == 2, "***las dos siguen ahi: ninguna se ha escondido***"


def test_con_lo_que_hace_falta_la_accion_se_activa():
    """*Y el motivo desaparece: una accion activa con un motivo viejo confunde.*"""
    acciones = t.las_acciones_que_aplican(
        [{"nombre": "unir", "cuantos": 2}], cuantos_marcados=2
    )
    assert acciones[0]["activa"] is True
    assert acciones[0]["motivo"] is None


def test_una_que_pide_varios_dice_cuantos():
    """*«Elige al menos 2» es mas util que «no se puede».*"""
    acciones = t.las_acciones_que_aplican([{"nombre": "unir", "cuantos": 2}], cuantos_marcados=1)
    assert acciones[0]["activa"] is False
    assert "2" in acciones[0]["motivo"], acciones[0]["motivo"]


# ---------------------------------------------------------------------------
# 3 · ***«Ficha unica por entidad»***
# ---------------------------------------------------------------------------


def test_una_entidad_tiene_una_ficha_y_se_entra_por_donde_se_entra():
    """***Y por que no vale una ficha por pantalla***: *si la parcela tiene una ficha en «Tierras» y otra
    distinta en «Cuaderno», la mitad de lo que se sabe de esa tierra **no sale** en la otra -y el agricultor
    cree que el programa no lo sabe-.*
    """
    desde_tierras = t.la_ficha_unica(tipo="tierra", de_donde_viene="tierras")
    desde_cuaderno = t.la_ficha_unica(tipo="tierra", de_donde_viene="cuaderno")

    assert desde_tierras["la_ficha"] == desde_cuaderno["la_ficha"], (
        "***la misma tierra abre la misma ficha, venga de donde venga***"
    )


def test_dos_formas_de_llegar_a_lo_mismo_son_la_misma_ficha():
    """*Es la comprobacion que se hace en la pantalla: dos enlaces a la misma tierra abren **lo mismo**.*"""
    assert t.la_misma_ficha(una={"tipo": "tierra", "id": 7}, otra={"tipo": "tierra", "id": 7})
    assert not t.la_misma_ficha(una={"tipo": "tierra", "id": 7}, otra={"tipo": "tierra", "id": 8})
    assert not t.la_misma_ficha(una={"tipo": "tierra", "id": 7}, otra={"tipo": "maquina", "id": 7}), (
        "***el 7 de una tierra no es el 7 de una maquina***"
    )


def test_una_entidad_sin_ficha_propia_se_para():
    """*Una entidad sin ficha propia se mira dentro de la de al lado, y eso hay que decirlo.*"""
    with pytest.raises(ValueError) as fallo:
        t.la_ficha_unica(tipo="lo_que_sea", de_donde_viene="aqui")
    assert "no es una de las entidades con ficha" in str(fallo.value)


# ---------------------------------------------------------------------------
# 4 · ***«Finca/campaña visibles»***
# ---------------------------------------------------------------------------


def test_sin_campana_elegida_se_dice_y_no_se_pone_la_de_hoy():
    """***Y en el campo no es un adorno***: *con dos fincas y tres años abiertos, apuntar en el año que no es
    mete el trabajo donde no va, y eso **no se ve** hasta que se buscan las cuentas.*

    ***Y no se elige por el agricultor***: *si no hay campaña, se dice que hay que elegirla. Poner la de hoy
    por defecto es decidir por el, y el año que viene el trabajo esta en el año que no era.*
    """
    sin = t.la_finca_y_la_campana(finca="La finca", campana=None, campanas=[2025, 2026])

    assert sin["se_ve"] is False
    assert sin["hay_que_elegir_campana"] is True
    assert sin["campanas"] == [2025, 2026], "***y se ofrecen, para poder elegir***"


def test_con_las_dos_cosas_se_ve_donde_se_esta_trabajando():
    con = t.la_finca_y_la_campana(finca="La finca", campana=2026)
    assert con["se_ve"] is True
    assert con["hay_que_elegir_campana"] is False
