"""**Las reservas de una maquina** (CRM-07 #9, 17/10/2026).

El encargo lo pide asi: *«reservas con maquina, intervalo, responsable, trabajo y estado; **conflictos de
solape en servidor**, anulaciones e **indisponibilidad por averia**»*. Aqui se prueba la parte **pura** -la
que decide si un hueco esta libre-, que es donde vive el solape y donde se puede probar de verdad: sin base,
sin pantalla y sin adivinar.

Lo que se comprueba, y por que cada cosa:

  1. **Los limites del intervalo**, que el encargo manda definir: `hasta` despues de `desde`, y ***los
     extremos NO se pisan*** (9-11 y 11-13 caben las dos).
  2. **El solape**, con sus cuatro formas: uno dentro de otro, uno que contiene, uno que empieza dentro y
     uno que acaba dentro. Y los que **no** se solapan.
  3. **Anular no es borrar**: una reserva anulada se queda en el cuaderno y **deja de ocupar**.
  4. **Corregir una reserva no choca consigo misma**, que es el fallo clasico de estas cosas.
  5. **Otra maquina no choca**: de eso se trata, de poder tener dos tractores reservados a la vez.
  6. **La averia**, con los cuatro estados que admite la casa, incluido ***«no se sabe»***, que **no es lo
     mismo** que dejarlo pasar.
  7. **El orden de las preguntas**: intervalo, luego averia, luego solape; y **con cual** se choca, que es lo
     unico que le permite decidir al agricultor.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import reservas


def _cuando(dia: int, hora: int) -> dt.datetime:
    return dt.datetime(2026, 3, dia, hora, 0)


def _una_reserva(desde, hasta, *, id=1, maquina_id=7, anulada=False):
    return {"id": id, "maquina_id": maquina_id, "desde": desde, "hasta": hasta, "anulada": anulada}


def _una_averia(*, fecha, resuelta, fecha_resuelta=None):
    return {"fecha": fecha, "resuelta": resuelta, "fecha_resuelta": fecha_resuelta}


# ---------------------------------------------------------------------------
# 1 · Los limites del intervalo
# ---------------------------------------------------------------------------


def test_hasta_tiene_que_ser_DESPUES_de_desde():
    """Una reserva de duracion cero -o al reves- no es una reserva."""
    assert reservas.el_intervalo_esta_bien(_cuando(2, 9), _cuando(2, 11)) is None
    assert reservas.el_intervalo_esta_bien(_cuando(2, 11), _cuando(2, 9)) == reservas.NO_SE_PUEDE_POR_LA_FECHA
    assert reservas.el_intervalo_esta_bien(_cuando(2, 9), _cuando(2, 9)) == reservas.NO_SE_PUEDE_POR_LA_FECHA
    assert reservas.el_intervalo_esta_bien(None, _cuando(2, 9)) == reservas.NO_SE_PUEDE_POR_LA_FECHA


def test_los_extremos_NO_se_pisan():
    """***9-11 y 11-13 caben las dos.***

    Es lo que espera cualquiera que apunte dos cosas seguidas; al contrario habria que inventarse un minuto
    entre las dos, y ese minuto no existe en la realidad.
    """
    assert not reservas.se_solapan(_cuando(2, 9), _cuando(2, 11), _cuando(2, 11), _cuando(2, 13))
    assert not reservas.se_solapan(_cuando(2, 11), _cuando(2, 13), _cuando(2, 9), _cuando(2, 11))


# ---------------------------------------------------------------------------
# 2 · El solape, en sus cuatro formas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "otra_desde, otra_hasta, cuanto",
    [
        (10, 12, "empieza dentro"),
        (8, 10, "acaba dentro"),
        (9, 13, "la contiene"),
        (10, 11, "esta dentro"),
        (9, 11, "es la misma"),
    ],
)
def test_se_solapan_las_cuatro_formas(otra_desde, otra_hasta, cuanto):
    """No basta con mirar si una empieza dentro de la otra: hay cuatro formas de pisarse."""
    assert reservas.se_solapan(
        _cuando(2, 9), _cuando(2, 12), _cuando(2, otra_desde), _cuando(2, otra_hasta)
    ), f"tendrian que solaparse: {cuanto}"


@pytest.mark.parametrize(
    "otra_desde, otra_hasta, cuanto",
    [(7, 9, "acaba justo al empezar"), (12, 14, "empieza justo al acabar"), (7, 8, "es anterior")],
)
def test_NO_se_solapan_cuando_no_comparten_tiempo(otra_desde, otra_hasta, cuanto):
    assert not reservas.se_solapan(
        _cuando(2, 9), _cuando(2, 12), _cuando(2, otra_desde), _cuando(2, otra_hasta)
    ), f"NO tendrian que solaparse: {cuanto}"


# ---------------------------------------------------------------------------
# 3 · Anular no es borrar
# ---------------------------------------------------------------------------


def test_una_reserva_ANULADA_no_ocupa_la_maquina():
    """Se queda en el cuaderno, tachada, y deja de ocupar. Como todo lo anulado de esta casa."""
    ocupada = _una_reserva(_cuando(2, 9), _cuando(2, 11), anulada=True)

    assert reservas.la_que_choca([ocupada], desde=_cuando(2, 10), hasta=_cuando(2, 12), maquina_id=7) is None


# ---------------------------------------------------------------------------
# 4 y 5 · Corregir no choca consigo misma, y otra maquina no choca
# ---------------------------------------------------------------------------


def test_corregir_una_reserva_no_choca_CONSIGO_MISMA():
    """***El fallo clasico***: mover una reserva media hora contra si misma."""
    suya = _una_reserva(_cuando(2, 9), _cuando(2, 11), id=5)

    choca = reservas.la_que_choca(
        [suya], desde=_cuando(2, 9), hasta=_cuando(2, 11, ), maquina_id=7, saltando=5
    )

    assert choca is None


def test_otra_maquina_NO_choca():
    """***De eso se trata***: poder tener dos tractores reservados a la misma hora."""
    el_otro = _una_reserva(_cuando(2, 9), _cuando(2, 11), maquina_id=8)

    assert reservas.la_que_choca([el_otro], desde=_cuando(2, 10), hasta=_cuando(2, 12), maquina_id=7) is None


# ---------------------------------------------------------------------------
# 6 · La averia, con sus cuatro estados
# ---------------------------------------------------------------------------


def test_una_averia_SIN_arreglar_impide_reservar():
    la_averia = _una_averia(fecha=_cuando(1, 8), resuelta=False)

    motivo = reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11))

    assert motivo == reservas.NO_SE_PUEDE_POR_AVERIA


def test_una_averia_arreglada_ANTES_no_impide_nada():
    """Se arreglo antes de empezar la reserva: la maquina estaba bien."""
    la_averia = _una_averia(
        fecha=_cuando(1, 8), resuelta=True, fecha_resuelta=_cuando(1, 20)
    )

    assert reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11)) is None


def test_una_averia_arreglada_DESPUES_impide_reservar():
    """***Estaba averiada durante la reserva***, aunque hoy ya este arreglada."""
    la_averia = _una_averia(
        fecha=_cuando(1, 8), resuelta=True, fecha_resuelta=_cuando(2, 20)
    )

    motivo = reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11))

    assert motivo == reservas.NO_SE_PUEDE_POR_AVERIA


@pytest.mark.parametrize(
    "la_averia, cuanto",
    [
        (_una_averia(fecha=dt.datetime(2026, 1, 8), resuelta=True, fecha_resuelta=None),
         "arreglada pero SIN decir cuando"),
        (_una_averia(fecha=dt.datetime(2026, 1, 8), resuelta=None, fecha_resuelta=None),
         "no se sabe si sigue"),
    ],
)
def test_cuando_NO_SE_SABE_se_dice_que_no_se_sabe(la_averia, cuanto):
    """***«No lo se» no es un «si».***

    Es la regla de la casa -«fecha desconocida no significa vigente»- y callarla convertiria un dato que
    nadie ha comprobado en un permiso. Y se distingue de «no se puede», porque el agricultor decide cosas
    distintas con cada respuesta.
    """
    motivo = reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11))

    assert motivo == reservas.NO_SE_SABE_POR_AVERIA, cuanto
    assert motivo != reservas.NO_SE_PUEDE_POR_AVERIA, "***y NO es lo mismo que «no se puede»***"


def test_una_averia_que_empieza_DESPUES_no_afecta():
    """Reservar el martes cuando la averia fue el jueves no tiene nada que ver."""
    la_averia = _una_averia(fecha=_cuando(5, 8), resuelta=False)

    assert reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11)) is None


# ---------------------------------------------------------------------------
# 7 · El orden de las preguntas, y con cual se choca
# ---------------------------------------------------------------------------


def test_lo_que_impide_dice_el_motivo_Y_CON_CUAL_se_choca():
    """Decir «no puedes» sin decir **con cual** no le deja decidir al agricultor."""
    la_suya = _una_reserva(_cuando(2, 9), _cuando(2, 11), id=3)
    la_que_llega = _una_reserva(_cuando(2, 10), _cuando(2, 12), id=99)

    motivo, choca = reservas.lo_que_impide(
        [la_suya], [], desde=la_que_llega["desde"], hasta=la_que_llega["hasta"], maquina_id=7
    )

    assert motivo == reservas.NO_SE_PUEDE_POR_OTRA_RESERVA
    assert choca is la_suya, "***y con cual: es el dato que le permite decidir***"


def test_el_intervalo_se_mira_ANTES_que_nada():
    """Si el intervalo esta mal, no se puede comparar con el: se dice eso y no un solape inventado."""
    motivo, choca = reservas.lo_que_impide(
        [_una_reserva(_cuando(2, 9), _cuando(2, 11))],
        [],
        desde=_cuando(2, 11),
        hasta=_cuando(2, 9),
        maquina_id=7,
    )

    assert motivo == reservas.NO_SE_PUEDE_POR_LA_FECHA
    assert choca is None


def test_la_averia_se_mira_antes_que_el_solape():
    """***Si la maquina no estaba, da igual quien la pidio***: el motivo util es el otro."""
    motivo, choca = reservas.lo_que_impide(
        [_una_reserva(_cuando(2, 9), _cuando(2, 11))],
        [_una_averia(fecha=_cuando(1, 1), resuelta=False)],
        desde=_cuando(2, 10),
        hasta=_cuando(2, 12),
        maquina_id=7,
    )

    assert motivo == reservas.NO_SE_PUEDE_POR_AVERIA
    assert choca is None


def test_los_estados_son_los_que_dice_el_modulo():
    """`anulada` **no** es un estado: en esta casa lo anulado es una columna aparte."""
    assert reservas.LOS_ESTADOS_DE_UNA_RESERVA == ("pedida", "en_curso", "hecha")
    assert "anulada" not in reservas.LOS_ESTADOS_DE_UNA_RESERVA


# ---------------------------------------------------------------------------
# 8 · La averia se apunta por DIA y la reserva por HORA
# ---------------------------------------------------------------------------
#
# ***Esto salio al correr las puertas, no al pensar*** (17/10/2026): comparar la fecha de una averia -que es
# un `date`- con el intervalo de una reserva -que es un `datetime`- revienta con un `TypeError`. Y al
# resolverlo hay que **decidir** algo que el encargo no dice: cuanto dura una averia. Se decide lo unico
# honesto con el dato que hay: **el dia entero**.


def test_una_averia_de_un_dia_cubre_ESE_DIA_ENTERO():
    """La averia es del 2, y la reserva tambien: **impide**."""
    la_averia = _una_averia(fecha=dt.date(2026, 3, 2), resuelta=False)

    motivo = reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11))

    assert motivo == reservas.NO_SE_PUEDE_POR_AVERIA


def test_una_averia_de_un_dia_NO_toca_al_SIGUIENTE():
    """La averia es del 1, **y se arreglo ese dia**: la reserva del 2 no la sufre.

    ***Ojo con lo que se espera***, que esto lo escribi mal la primera vez: una averia con `resuelta=False`
    **sigue sin arreglar**, asi que una del dia 1 **si** impide reservar el dia 2 -la maquina sigue
    averiada-. Para que no la afecte tiene que estar **arreglada antes** de la reserva.
    """
    la_averia = _una_averia(
        fecha=dt.date(2026, 3, 1), resuelta=True, fecha_resuelta=dt.date(2026, 3, 1)
    )

    assert reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11)) is None


def test_una_averia_resuelta_ESE_MISMO_dia_todavia_impide():
    """***Al cerrar el dia***: si se arreglo el 2, la maquina estuvo averiada **todo el 2**.

    Es lo conservador, y es lo que el dato permite afirmar: la averia sabe el dia, no la hora, y dar por
    buena la maquina a las 9:00 de un dia en que estaba averiada seria inventarse una hora.
    """
    la_averia = _una_averia(
        fecha=dt.date(2026, 3, 1), resuelta=True, fecha_resuelta=dt.date(2026, 3, 2)
    )

    motivo = reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11))

    assert motivo == reservas.NO_SE_PUEDE_POR_AVERIA


def test_una_averia_resuelta_ANTES_no_impide_con_fechas_de_dia():
    la_averia = _una_averia(
        fecha=dt.date(2026, 2, 1), resuelta=True, fecha_resuelta=dt.date(2026, 2, 20)
    )

    assert reservas.lo_que_impide_reservar([la_averia], desde=_cuando(2, 9), hasta=_cuando(2, 11)) is None
