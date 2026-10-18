"""**Lo que de verdad se ve** (contrato comun, 17/10/2026).

El contrato comun lo pide asi: *«Verificar rectangulo completo, nombre legible, foco visible y activacion.
***Un rectangulo con ancho positivo fuera de la pantalla no es visible.*** Considerar zoom y scrollbars,
***no asumir ancho util = viewport***»*, y en las 235-236: *«Medir recorte completo. ***Contar clics y filas
utiles, no solo px.***»*

***Y la idea es la del resto del programa***: **«esta en el DOM» no es «se ve».**
"""

from __future__ import annotations

import pytest

from app import lo_que_se_ve as v

EL_MOVIL = v.un_rectangulo(x=0, y=0, ancho=390, alto=800)


# ---------------------------------------------------------------------------
# 1 · ***«Un rectangulo con ancho positivo fuera de la pantalla no es visible»***
# ---------------------------------------------------------------------------


def test_un_rectangulo_de_200_px_fuera_de_la_pantalla_no_se_ve():
    """***El caso literal del contrato, y el mas facil de dar por bueno.***

    *Un boton a 500 px de una pantalla de 390 **mide 200 px** -el navegador lo dice- y **no se ve**. Una prueba
    del DOM lo encuentra, tiene su texto y su accion, y **el agricultor no lo puede pulsar**.*
    """
    fuera = v.un_rectangulo(x=500, y=10, ancho=200, alto=40)
    visto = v.se_ve_entero(fuera, recortes=[EL_MOVIL])

    assert visto["se_ve"] is False, "***mide bien y no se ve***"
    assert visto["ancho_positivo_no_basta"] is True, "***y se dice por que: el ancho no basta***"


def test_lo_que_esta_dentro_se_ve():
    """*El otro lado, para que la regla de arriba signifique algo.*"""
    dentro = v.un_rectangulo(x=10, y=10, ancho=200, alto=40)
    assert v.se_ve_entero(dentro, recortes=[EL_MOVIL])["se_ve"] is True


def test_un_control_justo_en_el_borde_se_ve():
    """***Tocando el borde, si***: *390 de ancho y el boton empieza en 190 con 200 de ancho acaba justo en
    390. **Cabe**, y decir que no seria un falso aviso.*"""
    al_borde = v.un_rectangulo(x=190, y=0, ancho=200, alto=40)
    assert v.se_ve_entero(al_borde, recortes=[EL_MOVIL])["se_ve"] is True


# ---------------------------------------------------------------------------
# 2 · ***«Rectangulo completo»***, no la esquina
# ---------------------------------------------------------------------------


def test_medio_boton_fuera_esta_cortado():
    """***Y lo que se ve a medias no se puede pulsar entero.***

    *Con la esquina dentro y la mitad fuera, el control **esta cortado**: se mira el rectangulo **completo**,
    no donde empieza.*
    """
    cortado = v.un_rectangulo(x=300, y=10, ancho=200, alto=40)  # 300 + 200 = 500 > 390
    visto = v.se_ve_entero(cortado, recortes=[EL_MOVIL])

    assert visto["se_ve"] is False, "***empieza dentro y acaba fuera***"


def test_un_control_sin_tamaño_no_se_ve():
    """*Un rectangulo de 0x0 es un control que no esta.*"""
    nada = v.un_rectangulo(x=10, y=10, ancho=0, alto=0)
    assert v.se_ve_entero(nada, recortes=[EL_MOVIL])["se_ve"] is False
    assert v.se_ve_entero(nada, recortes=[EL_MOVIL])["lo_que_lo_tapa"] == "no tiene tamaño"


# ---------------------------------------------------------------------------
# 3 · ***«No asumir ancho util = viewport»***
# ---------------------------------------------------------------------------


def test_un_ancestro_que_recorta_tapa_aunque_quepa_en_la_pantalla():
    """***El error que el contrato nombra con esas palabras.***

    *Una barra con `overflow: hidden` recorta a sus hijos: un boton puede caber **de sobra** en la pantalla y
    estar **cortado** por el panel donde vive. Mirar solo el viewport dice que se ve, y no se ve.*
    """
    el_panel = v.un_rectangulo(x=0, y=0, ancho=300, alto=600)
    dentro_del_viewport_pero_fuera_del_panel = v.un_rectangulo(x=320, y=10, ancho=50, alto=40)

    visto = v.se_ve_entero(dentro_del_viewport_pero_fuera_del_panel, recortes=[EL_MOVIL, el_panel])

    assert visto["se_ve"] is False, "***cabe en la pantalla y lo tapa el panel***"
    assert visto["lo_que_lo_tapa"] == "un recorte"


def test_se_dice_QUIEN_lo_tapa():
    """*«No se ve» no se puede arreglar; «lo tapa la barra de abajo» si.*"""
    # ***El panel recorta de verdad***: va de 700 a 800, y el control esta en 810 -fuera de el y **dentro** de
    # la pantalla, que es el caso interesante-. *La primera version de esta prueba los puso uno dentro del
    # otro y el modulo dijo la verdad: cabia.*
    # ***`y=700` con `alto=50` acaba en 750***, y la pantalla llega a 800: *asi el control cabe en la pantalla
    # y lo tapa **el panel**, que es lo que se quiere probar. (En el primer intento el panel llegaba al borde,
    # y el que tapaba era el viewport: el modulo lo dijo bien y la prueba estaba mal.)*
    el_panel = {"nombre": "la barra de abajo", **v.un_rectangulo(x=0, y=700, ancho=390, alto=50)}
    fuera_del_panel = v.un_rectangulo(x=10, y=760, ancho=50, alto=40)

    visto = v.se_ve_entero(fuera_del_panel, recortes=[EL_MOVIL, el_panel])
    assert visto["se_ve"] is False, "***el panel lo recorta***"
    assert visto["lo_que_lo_tapa"] == "la barra de abajo", (
        f"***y se dice QUIEN lo tapa: {visto}***"
    )


# ---------------------------------------------------------------------------
# 4 · ***El zoom real***
# ---------------------------------------------------------------------------


def test_con_zoom_al_200_lo_que_cabia_puede_no_caber():
    """***«Zoom real 200 %»***, y esto importa: *quien necesita el zoom para leer es justo quien se queda sin
    el boton.*

    *El mismo control que cabe al 100% puede no caber al 200%, y eso hay que saberlo **antes**.*
    """
    ancho = v.un_rectangulo(x=100, y=10, ancho=200, alto=40)

    assert v.cabe_en_el_viewport(ancho, viewport=EL_MOVIL, zoom=1.0)["se_ve_con_zoom"] is True
    assert v.cabe_en_el_viewport(ancho, viewport=EL_MOVIL, zoom=2.0)["se_ve_con_zoom"] is False, (
        "***al 200% ya no cabe: 100+200 se va a 600 en una pantalla de 390***"
    )


def test_un_zoom_que_no_tiene_sentido_se_para():
    with pytest.raises(ValueError):
        v.cabe_en_el_viewport(v.un_rectangulo(x=0, y=0, ancho=10, alto=10), viewport=EL_MOVIL, zoom=0)


# ---------------------------------------------------------------------------
# 5 · ***«Contar clics y filas utiles, no solo px»***
# ---------------------------------------------------------------------------


def test_se_cuentan_los_clics_y_se_dicen_cuales():
    """*«12 clics» no se puede arreglar; «12 clics, y estos son» si.*"""
    pasos = ["abrir", "buscar", "elegir", "editar", "confirmar", "guardar"]
    contados = v.los_clics(pasos=pasos)

    assert contados["clics"] == 6
    assert contados["los_pasos"] == pasos, "***y se dicen, para poder acortarlos***"
    assert contados["es_demasiado_largo"] is True, "***un recado asi no se hace de pie en el campo***"


def test_un_recado_corto_no_es_demasiado_largo():
    assert v.los_clics(pasos=["abrir", "confirmar"])["es_demasiado_largo"] is False


def test_las_filas_utiles_no_son_las_filas():
    """***«Filas utiles» no es «filas»***: *una lista de 300 con 12 que sirven obliga a recorrer las 300 para
    encontrar las 12 -y **eso** es lo que cuesta, no los pixeles-.*
    """
    contadas = v.las_filas(list(range(300)), cuantas_utiles=12)

    assert contadas["filas"] == 300
    assert contadas["utiles"] == 12
    assert contadas["hay_que_recorrer"] == 288, "***y se dice lo que hay que recorrer***"


# ---------------------------------------------------------------------------
# 6 · ***«Si solo hay DOM, marcar el limite»***
# ---------------------------------------------------------------------------


def test_sin_imagen_no_se_puede_decir_que_se_ve():
    """***Y se dice, no se calla.***

    *Una prueba que mira el DOM **no ha visto la pantalla**: puede estar todo en su sitio y el texto no caber,
    o el color no contrastar. **Decir «se ve» cuando solo se ha mirado el DOM es la clase de afirmacion que el
    contrato no quiere.***
    """
    sin = v.el_limite_de_la_evidencia(hay_imagen=False)

    assert sin["evidencia"] == "solo_dom"
    assert sin["limite"], "***el limite se marca***"
    assert sin["se_puede_decir_que_se_ve"] is False


def test_con_imagen_si_se_puede_decir():
    con = v.el_limite_de_la_evidencia(hay_imagen=True)
    assert con["se_puede_decir_que_se_ve"] is True
    assert con["limite"] is None
