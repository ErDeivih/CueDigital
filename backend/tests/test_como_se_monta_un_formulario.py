"""**Como se monta un formulario** (contrato comun, 17/10/2026).

El contrato comun de la cola lo dice asi: *«Formulario: ***agrupacion por tarea***, ***original al lado cuando
hay documento***, borrador conservado, ***errores junto a datos***, ***estado de guardado/reenvio***,
confirmacion clara.»*
"""

from __future__ import annotations

from app import el_formulario as f


# ---------------------------------------------------------------------------
# 1 · ***«Agrupacion por tarea»***
# ---------------------------------------------------------------------------


def test_los_campos_van_agrupados_por_lo_que_se_esta_haciendo():
    """***No por tipo de dato*** -que es lo facil-: *«fecha, numero, importe» no dice nada; «¿que has
    comprado? / ¿cuanto?» si.*
    """
    grupos = f.agrupar_por_tarea(
        [
            {"nombre": "producto", "tarea": "Que has comprado"},
            {"nombre": "total", "tarea": "Cuanto"},
            {"nombre": "fecha", "tarea": "Cuando"},
        ],
        orden_de_las_tareas=["Que has comprado", "Cuanto", "Cuando"],
    )

    assert [g["tarea"] for g in grupos] == ["Que has comprado", "Cuanto", "Cuando"]
    assert grupos[0]["campos"] == [{"nombre": "producto", "tarea": "Que has comprado"}]


def test_un_campo_sin_tarea_no_se_pierde():
    """***Un campo que no sale es un campo que no se rellena.***

    *Al grupo de «Otros datos», que se ve, en vez de desaparecer del formulario.*
    """
    grupos = f.agrupar_por_tarea(
        [{"nombre": "suelto"}, {"nombre": "producto", "tarea": "Que"}], orden_de_las_tareas=["Que"]
    )

    assert [g["tarea"] for g in grupos] == ["Que", "Otros datos"], "***el suelto tiene su grupo***"
    assert grupos[1]["campos"] == [{"nombre": "suelto"}], "***y esta dentro, no fuera***"


def test_las_tareas_que_se_piden_van_primero_y_las_demas_al_final():
    """*Si el orden de las tareas importa -y en un formulario importa-, se respeta.*"""
    grupos = f.agrupar_por_tarea(
        [{"nombre": "a", "tarea": "Tercera"}, {"nombre": "b", "tarea": "Primera"}],
        orden_de_las_tareas=["Primera", "Segunda", "Tercera"],
    )
    assert [g["tarea"] for g in grupos] == ["Primera", "Tercera"]


# ---------------------------------------------------------------------------
# 2 · ***«Errores junto a datos»***
# ---------------------------------------------------------------------------


def test_cada_error_va_pegado_al_campo_que_lo_tiene():
    """***Y no en un aviso arriba***: *«hay 3 errores» obliga a buscar **cuales** de los catorce campos son.*"""
    puesto = f.poner_los_errores_junto_a_los_datos(
        [{"nombre": "total"}, {"nombre": "nif"}], {"total": "no cuadra con las lineas"}
    )

    assert puesto["campos"][0]["error"] == "no cuadra con las lineas", "***al lado del total***"
    assert puesto["campos"][1]["error"] is None, "***y el que esta bien, sin error***"
    assert puesto["se_puede_enviar"] is False


def test_un_error_de_un_campo_que_no_esta_se_dice_aparte():
    """*Un error que no se enseña es un formulario que no se puede enviar y no dice por que.*

    ***Y se dice aparte, no se pierde***: *puede ser de un campo que la pantalla no tiene -una regla del
    servidor-, y entonces es lo unico que explica el bloqueo.*
    """
    puesto = f.poner_los_errores_junto_a_los_datos(
        [{"nombre": "total"}], {"lo_del_servidor": "esa parcela no es tuya"}
    )

    assert puesto["campos"][0]["error"] is None
    assert puesto["sueltos"] == {"lo_del_servidor": "esa parcela no es tuya"}, "***no se pierde***"
    assert puesto["se_puede_enviar"] is False


def test_sin_errores_se_puede_enviar():
    puesto = f.poner_los_errores_junto_a_los_datos([{"nombre": "total"}], {})
    assert puesto["se_puede_enviar"] is True


# ---------------------------------------------------------------------------
# 3 · ***«Estado de guardado/reenvio»***
# ---------------------------------------------------------------------------


def test_en_la_cola_NO_es_guardado():
    """***Y es la distincion que importa.***

    *«Guardado» quiere decir que ha llegado. «En la cola» quiere decir que **aun no** -y confundirlas es lo que
    hace que alguien cierre la aplicacion creyendo que su trabajo esta a salvo.*
    """
    en_la_cola = f.el_estado_de_guardado(hay_cambios=True, en_la_cola=True)
    guardado = f.el_estado_de_guardado(hay_cambios=False, guardado=True)

    assert en_la_cola["estado"] == f.EN_LA_COLA
    assert en_la_cola["estado"] != guardado["estado"], "***son dos cosas distintas***"
    assert en_la_cola["tranquilo"] is False, "***y no se puede decir «tranquilo»***"
    assert guardado["tranquilo"] is True


def test_un_fallo_dice_que_lo_escrito_sigue_ahi():
    """*Es lo primero que piensa el agricultor cuando ve «no se ha podido guardar»: **¿he perdido lo que
    llevaba?***

    *Y la respuesta tiene que estar en el mismo sitio que el aviso.*
    """
    fallo = f.el_estado_de_guardado(hay_cambios=True, fallo="sin conexion")

    assert fallo["estado"] == f.FALLO
    assert fallo["lo_que_habia"] == "sigue aqui", "***y se dice, no se deja suponer***"
    assert "sin conexion" in fallo["detalle"]


def test_sin_cambios_no_hay_nada_que_guardar():
    """*Aunque el ultimo intento fallara: si no hay cambios, no hay nada pendiente.*"""
    assert f.el_estado_de_guardado(hay_cambios=False)["estado"] == f.SIN_CAMBIOS
    assert f.el_estado_de_guardado(hay_cambios=True)["estado"] == f.CAMBIOS_SIN_GUARDAR
    assert f.el_estado_de_guardado(hay_cambios=True, guardando=True)["estado"] == f.GUARDANDO


# ---------------------------------------------------------------------------
# 4 · ***«Original al lado cuando hay documento»***
# ---------------------------------------------------------------------------


def test_el_original_va_al_lado_de_lo_leido():
    """***Para poder comparar sin memorizar.***

    *Quien confirma una factura esta mirando la foto y el formulario a la vez; con el original en otra
    pantalla, se compara de memoria, y **de memoria se confirman cosas que no son**.*
    """
    al_lado = f.el_original_al_lado(lo_leido={"total": 205.7}, el_original="foto-de-la-factura.jpg")

    assert al_lado["hay_original"] is True
    assert al_lado["original"] == "foto-de-la-factura.jpg"
    assert al_lado["al_lado"] is True
    assert al_lado["campos"] == {"total": 205.7}


def test_sin_original_se_dice_que_no_se_puede_comprobar():
    """*Un formulario sin papel al lado no puede pretender que se compruebe nada.*"""
    sin = f.el_original_al_lado(lo_leido={"total": 205.7}, el_original=None)

    assert sin["hay_original"] is False
    assert sin["que_hacer"], "***y se dice que hacer***"
