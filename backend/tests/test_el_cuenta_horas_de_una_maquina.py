"""**El cuenta-horas de una máquina**: lecturas, no un número suelto (CRM-07 #8, 14/10/2026).

El encargo lo pide con estas palabras: *«lecturas de contador **fechadas y unidad**; correcciones
auditadas, **sustitución del contador**, datos faltantes. ***No inventar horas ni reducir acumulados
silenciosamente***»*. Y esto fija las cinco, sobre la función pura `maquinaria.lo_que_marca_el_contador`.

La unidad y la fecha no son adorno: **«1.200» no dice nada** -ni de cuándo es, ni si son horas o
kilómetros-, y un contador de horas y uno de kilómetros **no se suman ni se comparan**.
"""

import datetime as dt

import pytest

from app import maquinaria


def _una_lectura(cuando: str, valor, **cambios) -> dict:
    """Una lectura como la leerá la puerta: fecha, valor, unidad y lo que haga falta."""
    suya = {
        "id": 0,
        "fecha": dt.date.fromisoformat(cuando),
        "valor": valor,
        "unidad": "horas",
        "anulado": False,
        "es_sustitucion": False,
    }
    suya.update(cambios)
    return suya


def test_sin_ninguna_lectura_el_contador_no_ha_subido_cero():
    """***No se sabe***, y se dice: `subido` sale 0 porque es una suma, **y `sin_decir` cuenta el tramo**
    que no se sabe. Es lo que impide que la pantalla diga «0 horas»."""
    suyo = maquinaria.lo_que_marca_el_contador([])

    assert suyo["subido"] == 0
    assert suyo["cuantas"] == 0
    assert suyo["sin_decir"] == 1, "el tramo que falta es el de todo el historial"
    assert "no_hay_ninguna_lectura" in suyo["lo_que_falta"]
    assert suyo["marca"] is None, "y no se sabe lo que marca"


def test_con_dos_lecturas_se_sabe_lo_que_ha_subido():
    suyo = maquinaria.lo_que_marca_el_contador(
        [_una_lectura("2026-03-01", 1000), _una_lectura("2026-06-01", 1200, id=2)]
    )

    assert suyo["subido"] == 200
    assert suyo["marca"] == 1200
    assert suyo["unidad"] == "horas"
    assert suyo["sin_decir"] == 0
    assert len(suyo["tramos"]) == 1


def test_con_una_sola_lectura_se_sabe_lo_que_marca_pero_no_lo_que_ha_subido():
    suyo = maquinaria.lo_que_marca_el_contador([_una_lectura("2026-03-01", 1000)])

    assert suyo["marca"] == 1000, "lo que marca, sí"
    assert suyo["subido"] == 0, "lo que ha subido, no: no hay con qué compararlo"
    assert "hace_falta_otra_lectura_para_saber_cuanto_ha_subido" in suyo["lo_que_falta"]


def test_una_lectura_sin_valor_deja_el_tramo_sin_decir_y_no_lo_inventa():
    """Un hueco en medio **corta el tramo**: no se puede decir que subió 300, porque de la de en medio
    no consta lo que marcaba."""
    suyo = maquinaria.lo_que_marca_el_contador(
        [
            _una_lectura("2026-03-01", 1000),
            _una_lectura("2026-04-01", None, id=2),
            _una_lectura("2026-05-01", 1300, id=3),
        ]
    )

    assert suyo["subido"] == 0, "***no se inventa el tramo: ni 300 ni 0***"
    assert suyo["sin_decir"] >= 1, "y el hueco se cuenta"
    assert suyo["marca"] == 1300


def test_una_sustitucion_del_contador_NO_BAJA_el_acumulado():
    """***Es la regla que el encargo prohíbe saltarse.***

    La máquina se cambió el contador: venía de 1.000 y **el nuevo empieza en 50**. Restar cruzaría el
    cambio y daría **menos de lo que se hizo**, y el acumulado de la máquina no puede bajar porque le
    hayan puesto un contador nuevo. El tramo viejo era **una sola lectura**, así que no se puede medir y
    **se dice**; el tramo nuevo -de 50 a 200- sí, y son 150.
    """
    suyo = maquinaria.lo_que_marca_el_contador(
        [
            _una_lectura("2026-03-01", 1000),
            _una_lectura("2026-06-01", 50, id=2, es_sustitucion=True),
            _una_lectura("2026-09-01", 200, id=3),
        ]
    )

    assert suyo["subido"] == 150, (
        "***solo cuenta el tramo del contador nuevo (50 -> 200): la resta NO cruza el cambio***"
    )
    assert suyo["subido"] > 0, "***un acumulado que baja solo es lo que el encargo prohíbe***"
    assert suyo["sin_decir"] >= 1, "y el tramo viejo, que era una sola lectura, se dice que no se sabe"
    assert any(tramo.get("por_sustitucion") for tramo in suyo["tramos"])


def test_una_lectura_anulada_no_cuenta():
    """Como todo lo anulado de esta casa: se queda en el cuaderno, pero no suma."""
    suyo = maquinaria.lo_que_marca_el_contador(
        [
            _una_lectura("2026-03-01", 1000),
            _una_lectura("2026-04-01", 99_999, id=2, anulado=True),
            _una_lectura("2026-06-01", 1200, id=3),
        ]
    )

    assert suyo["subido"] == 200, "la anulada no entra en la cuenta"
    assert suyo["cuantas"] == 2


def test_las_unidades_no_se_mezclan_y_se_dice():
    """Un contador de horas y uno de kilómetros **no se suman**: se dice, en vez de sumar peras con
    manzanas."""
    suyo = maquinaria.lo_que_marca_el_contador(
        [
            _una_lectura("2026-03-01", 1000),
            _una_lectura("2026-06-01", 1200, id=2, unidad="kilometros"),
        ]
    )

    assert suyo["subido"] is None, "***no se suma: no se sabe***"
    assert "las_lecturas_no_son_de_la_misma_unidad" in suyo["lo_que_falta"]


# ---------------------------------------------------------------------------
# El retroceso y los valores que no son un contador (15/10/2026)
# ---------------------------------------------------------------------------
#
# Los dos los reprodujo la revision independiente del 15/10/2026, y los dos son de la misma familia: la
# funcion **afirmaba** cosas que nadie ha dicho.


def test_una_lectura_que_va_para_atras_sin_sustitucion_NO_se_resta():
    """***Un contador no puede ir para atras.***

    1.200 y luego 1.000, sin una sustitucion declarada, **no son -200 horas**: eso seria actividad
    negativa, y el encargo lo que prohibe es justamente reducir acumulados. Son **dos lecturas que no
    cuadran**, y lo que corresponde es decirselo al agricultor para que las revise o declare la
    sustitucion. No se disimula con `abs()`, ni con `max(0, ...)`, ni dando por hecho un cambio de
    contador que nadie ha dicho.
    """
    suyo = maquinaria.lo_que_marca_el_contador(
        [_una_lectura("2026-01-01", 1200), _una_lectura("2026-02-01", 1000, id=2)]
    )

    assert suyo["subido"] >= 0, "***nunca actividad negativa***"
    assert suyo["subido"] == 0, "no se resta: lo que no cuadra no se suma"
    assert len(suyo["incoherentes"]) == 1, "y el tramo queda marcado"
    assert suyo["incoherentes"][0]["motivo"] == "una_lectura_va_para_atras_sin_sustitucion"
    assert "una_lectura_va_para_atras_sin_sustitucion" in suyo["lo_que_falta"], (
        "y se pide revisarlo, que es lo unico util"
    )
    assert suyo["cobertura_incompleta"] is True


def test_el_subtotal_conocido_y_la_cobertura_incompleta_son_dos_cosas_distintas():
    """Con un tramo que cuadra y otro que no, se ensena **lo que se sabe** y se dice que falta trozo.

    Es la diferencia entre «ha subido 200» y «ha subido 200 de lo que se puede afirmar»: callar la
    segunda mitad es ensenar un subtotal como si fuera el total.

    **Un tramo va de la primera lectura a la ultima, y lo cortan dos cosas**: un hueco -una lectura sin
    valor- y una sustitucion declarada. Aqui el hueco del 15/02 parte la historia en dos: el primer tramo
    cuadra (1.000 -> 1.200, +200) y el segundo va para atras (900 -> 800), asi que hay **subtotal
    conocido** (200) y **cobertura incompleta** a la vez. Sin el hueco, la funcion mediria de 1.000 a 800
    como un solo tramo y el caso no seria este.
    """
    suyo = maquinaria.lo_que_marca_el_contador(
        [
            _una_lectura("2026-01-01", 1000),
            _una_lectura("2026-02-01", 1200, id=2),
            _una_lectura("2026-02-15", None, id=3),
            _una_lectura("2026-03-01", 900, id=4),
            _una_lectura("2026-04-01", 800, id=5),
        ]
    )

    assert suyo["subido"] == 200, "el tramo que cuadra se suma"
    assert suyo["cobertura_incompleta"] is True, "***y se dice que hay trozo sin poder afirmar***"
    assert len(suyo["incoherentes"]) == 1, "y el tramo que no cuadra queda marcado, no restado"
    assert suyo["sin_decir"] >= 1, "y el hueco se cuenta aparte"


def test_un_valor_que_no_es_un_numero_de_contador_se_rechaza():
    """Un contador no marca -3 ni infinito: eso no es una lectura, y no se suma."""
    suyo = maquinaria.lo_que_marca_el_contador(
        [
            _una_lectura("2026-01-01", 1000),
            _una_lectura("2026-02-01", -5, id=2),
            _una_lectura("2026-03-01", float("inf"), id=3),
            _una_lectura("2026-04-01", 1200, id=4),
        ]
    )

    assert suyo["subido"] >= 0, "***nunca un negativo***"
    assert "hay_lecturas_que_no_son_un_numero_de_contador" in suyo["lo_que_falta"]
    assert suyo["cobertura_incompleta"] is True


def test_un_retroceso_ENTRE_LECTURAS_CONSECUTIVAS_no_pasa_inadvertido():
    """***Mirar solo los extremos esconde una bajada en medio.***

    1.000 -> 1.200 -> 1.100 -> 1.300 **acaba mas arriba** de donde empezo, asi que restando los extremos
    salen 300 horas **y ninguna incidencia**. Pero **por el medio ha bajado**, y un contador no puede
    hacer eso. Lo reprodujo la revision del 16/10/2026, y es justo el caso que se cuela cuando se mira el
    final en vez del camino.
    """
    suyo = maquinaria.lo_que_marca_el_contador(
        [
            _una_lectura("2026-01-01", 1000),
            _una_lectura("2026-02-01", 1200, id=2),
            _una_lectura("2026-03-01", 1100, id=3),
            _una_lectura("2026-04-01", 1300, id=4),
        ]
    )

    assert suyo["subido"] == 0, "***ni 300 ni 400: el tramo no se puede afirmar***"
    assert len(suyo["incoherentes"]) == 1, "y la bajada queda marcada"
    assert suyo["incoherentes"][0]["subido"] == -100, "con el paso concreto que no cuadra"
    assert "una_lectura_va_para_atras_sin_sustitucion" in suyo["lo_que_falta"]
    assert suyo["cobertura_incompleta"] is True
    assert suyo["marca"] == 1300, "lo que marca se sigue sabiendo"
