"""**Los cinco estados de una pantalla** (contrato comun, 17/10/2026).

El contrato comun de la cola lo dice en una linea:

    ***Vacio explica que hacer; cargando no muestra 0; error conserva datos; offline muestra antiguedad;
    conflicto muestra dos versiones. Volver y recargar conservan contexto.***

***Y las seis cosas son la misma idea repetida***: *una pantalla nunca miente sobre lo que sabe.*
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import estados_de_la_pantalla as est


# ---------------------------------------------------------------------------
# 1 · ***«Cargando no muestra 0»***, que es el error numero uno
# ---------------------------------------------------------------------------


def test_cargando_no_muestra_cero():
    """***El error mas facil de cometer de todo el programa.***

    *Enseñar `0` mientras carga es lo mas natural del mundo -la variable empieza en cero-, y es **mentira**:
    el agricultor lee «tengo 0», no «aun no lo se».*

    ***Y es la misma regla que el desconocido del contador***: *lo que no se sabe no se convierte en cero.*
    """
    pintando = est.el_estado(cargando=True)

    assert pintando["estado"] == est.CARGANDO
    assert pintando["valor"] is None, "***mientras carga, el valor NO es cero***"
    assert pintando["enseña_algo"] is False


def test_y_si_alguien_le_pone_un_valor_cargando_se_le_dice():
    """*El modulo no lo deja pasar: `lo_que_falta_para_pintar` lo dice con el nombre del campo.*"""
    mal = {"estado": est.CARGANDO, "valor": 0}
    assert est.lo_que_falta_para_pintar(mal) == ["valor"]


# ---------------------------------------------------------------------------
# 2 · ***«Vacio explica que hacer»***
# ---------------------------------------------------------------------------


def test_vacio_explica_que_hacer():
    """*Una pantalla vacia sin salida deja al agricultor mirando.*"""
    vacia = est.el_estado(valor=None, que_hacer="Apunta tu primer trabajo")

    assert vacia["estado"] == est.VACIO
    assert vacia["que_hacer"] == "Apunta tu primer trabajo"


def test_y_si_no_le_dicen_que_hacer_se_le_dice_que_falta():
    """*«Mal» no se puede arreglar; «le falta decir que hacer» si.*"""
    sin_salida = est.el_estado(valor=None)
    assert est.lo_que_falta_para_pintar(sin_salida) == ["que_hacer"]


# ---------------------------------------------------------------------------
# 3 · ***«Error conserva datos»***
# ---------------------------------------------------------------------------


def test_un_error_no_borra_lo_que_estaba_escrito():
    """***Lo que mas duele y lo que menos se perdona.***

    *Un fallo de red no puede llevarse por delante lo que el agricultor llevaba media hora escribiendo. El
    error se enseña **al lado** de lo que habia, no en su lugar.*
    """
    fallo = est.el_estado(error="No se pudo guardar", lo_que_habia={"dosis": 0.5})

    assert fallo["estado"] == est.ERROR
    assert fallo["lo_que_habia"] == {"dosis": 0.5}, "***lo que habia sigue ahi***"
    assert fallo["valor"] == {"dosis": 0.5}, "y se devuelve, no se pierde"
    assert fallo["enseña_algo"] is True
    assert fallo["que_hacer"], "***y se dice que hacer: un error sin salida es un callejon***"


# ---------------------------------------------------------------------------
# 4 · ***«Offline muestra antiguedad»***
# ---------------------------------------------------------------------------


def test_sin_conexion_dice_de_cuando_son_los_datos():
    """*«Sin conexion» y nada mas no dice si lo que se ve es de hace un minuto o de anteayer.*

    ***Y se dice como se dice en el campo***: «hace 3 horas» se entiende; una marca de tiempo, no.
    """
    ahora = dt.datetime(2026, 10, 17, 12, 0)
    pintando = est.el_estado(
        sin_conexion=True, valor=5, de_cuando=dt.datetime(2026, 10, 17, 9, 0), ahora=ahora
    )

    assert pintando["estado"] == est.SIN_CONEXION
    assert pintando["de_cuando"] is not None
    assert pintando["antiguedad"] == "hace 3 horas", pintando["antiguedad"]
    assert pintando["valor"] == 5, "***y el dato se sigue viendo: es viejo, no inexistente***"


@pytest.mark.parametrize(
    "cuanto, esperado",
    [
        (dt.timedelta(seconds=30), "hace un momento"),
        (dt.timedelta(minutes=5), "hace 5 minutos"),
        (dt.timedelta(hours=2), "hace 2 horas"),
        (dt.timedelta(days=3), "hace 3 dias"),
    ],
)
def test_la_antiguedad_se_dice_como_se_dice_en_el_campo(cuanto, esperado):
    ahora = dt.datetime(2026, 10, 17, 12, 0)
    assert est._la_antiguedad(ahora - cuanto, ahora) == esperado


def test_sin_conexion_sin_decir_de_cuando_esta_incompleto():
    sin_fecha = est.el_estado(sin_conexion=True, valor=5)
    assert est.lo_que_falta_para_pintar(sin_fecha) == ["de_cuando"]


# ---------------------------------------------------------------------------
# 5 · ***«Conflicto muestra dos versiones»***
# ---------------------------------------------------------------------------


def test_un_conflicto_enseña_las_dos_versiones_y_no_elige():
    """***Quien decide es el agricultor, no el programa.***

    *Es la mitad que le faltaba a la edicion concurrente: el servidor ya contesta **409 con quien y cuando**;
    lo que hace esto es **no tirar ninguna de las dos**.*
    """
    choque = est.el_estado(
        conflicto=True,
        la_mia={"dosis": 0.5},
        la_de_otro={"dosis": 0.75},
        quien=7,
        cuando=dt.datetime(2026, 10, 17, 10, 0),
    )

    assert choque["estado"] == est.CONFLICTO
    assert choque["la_mia"] == {"dosis": 0.5}, "***la mia no se pierde***"
    assert choque["la_de_otro"] == {"dosis": 0.75}, "***ni la del otro***"
    assert choque["quien"] == 7 and choque["cuando"] is not None, "y se dice quien y cuando"


def test_y_un_conflicto_con_una_sola_version_esta_incompleto():
    a_medias = est.el_estado(conflicto=True, la_mia={"dosis": 0.5})
    assert est.lo_que_falta_para_pintar(a_medias) == ["las_dos_versiones"]


# ---------------------------------------------------------------------------
# 6 · ***«Volver y recargar conservan contexto»***
# ---------------------------------------------------------------------------


def test_volver_conserva_el_contexto():
    """*Si un agricultor ha filtrado, ordenado y esta en la pagina 4, volver a entrar y encontrarse la lista
    entera es perder su trabajo de navegacion.*"""
    contexto = est.el_contexto(
        filtros={"campana": 2026}, orden="fecha", columnas=["fecha", "importe"], pagina=4, busqueda="coop"
    )

    assert contexto["filtros"] == {"campana": 2026}
    assert contexto["orden"] == "fecha"
    assert contexto["pagina"] == 4
    assert contexto["busqueda"] == "coop"


# ---------------------------------------------------------------------------
# 7 · ***«Pie X de Y», y la exportacion que declara lo que lleva***
# ---------------------------------------------------------------------------


def test_el_pie_dice_cuantos_se_ven_de_cuantos_hay():
    """*Un pie que dice «12» sin decir «de 300» hace creer que hay doce.*"""
    pie = est.el_pie_de_la_tabla(cuantos_se_ven=12, cuantos_hay=300)

    assert pie["texto"] == "12 de 300"
    assert pie["hay_filtro"] is False
    assert pie["la_exportacion_lleva"] == "todo"


def test_y_si_hay_filtro_la_exportacion_lo_declara():
    """***Una exportacion que no dice que lleva no se puede usar para nada serio***: *ni para reclamar, ni
    para comparar dos descargas.*"""
    pie = est.el_pie_de_la_tabla(cuantos_se_ven=12, cuantos_hay=300, filtrados=True)

    assert pie["texto"] == "12 de 300"
    assert pie["hay_filtro"] is True
    assert pie["la_exportacion_lleva"] == "lo filtrado", "***y lo dice***"


def test_si_no_se_sabe_cuantos_hay_no_se_inventa():
    """*Un total inventado es peor que no tenerlo.*"""
    pie = est.el_pie_de_la_tabla(cuantos_se_ven=12, cuantos_hay=None)

    assert pie["hay"] is None
    assert "no se sabe" in pie["texto"], pie["texto"]


# ---------------------------------------------------------------------------
# 8 · Y un estado que no es ninguno se para
# ---------------------------------------------------------------------------


def test_un_estado_que_no_es_ninguno_de_los_cinco_se_para():
    with pytest.raises(est.EstadoQueNoSeSabeCualEs):
        est.lo_que_falta_para_pintar({"estado": "lo_que_sea"})
