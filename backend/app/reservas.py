"""**Las reservas de una maquina** (CRM-07 #9, 17/10/2026).

El encargo lo pide asi:

    reservas con **maquina, intervalo, responsable, trabajo y estado**; **conflictos de solape en
    servidor**, anulaciones e **indisponibilidad por averia**. ***Cambios concurrentes no producen dos
    reservas incompatibles***. Definir **zona horaria y limites del intervalo**.

Esto es la parte **pura**: entran datos y sale lo que se puede afirmar, sin base de datos de por medio, que
es lo que se puede probar de verdad. Las puertas y el modelo viven al lado.

--------------------------------------------------------------------------------------------------
***LA ZONA HORARIA, DECIDIDA Y ESCRITA*** (que es lo que pide el encargo)
--------------------------------------------------------------------------------------------------

Esta casa guarda `DateTime` **sin huso** (`server_default=func.now()`), y no hay `ZoneInfo` en ninguna
parte. Eso no se arregla aqui, pero **tampoco se disimula**, asi que queda dicho:

  * **El intervalo de una reserva es hora LOCAL DE LA FINCA**, y se guarda **naive**. Un agricultor dice
    «el tractor el martes de 9 a 11» y eso es lo que se guarda: cambiarlo a UTC haria que la reserva se
    viera movida una hora en verano y dos veces al ano habria reservas que «empiezan antes» de lo que el
    agricultor escribio.
  * **La zona NO viaja en el dato.** Dos explotaciones en husos distintos compararian sus horas como si
    fueran la misma, y **comparar horas de husos distintos esta mal**. Se asume una finca = un huso, que es
    lo cierto en esta casa (una explotacion es de un sitio), y **si algun dia deja de serlo, esto es lo
    primero que hay que cambiar**. Queda escrito para que nadie lo descubra por su cuenta.

***Y LOS LIMITES DEL INTERVALO***, tambien decididos y escritos:

  * `hasta` tiene que ser **estrictamente posterior** a `desde`: una reserva de duracion cero no es una
    reserva, es un apunte.
  * **Los extremos NO se pisan**: una reserva de 9:00 a 11:00 y otra de 11:00 a 13:00 **no se solapan**.
    Es lo que espera cualquiera que apunte dos cosas seguidas, y lo contrario obligaria a inventarse un
    minuto entre las dos.
  * **No se pone tope de duracion a proposito**: un tractor se puede reservar para una semana de siega, y
    un numero elegido aqui seria un numero inventado.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable, Mapping, Sequence

# **Los estados de una reserva**, y el nombre de cada uno. `anulada` **no** esta aqui: en esta casa lo
# anulado es una **columna aparte** -como en las lecturas del contador y en las recepciones-, porque una
# reserva anulada sigue existiendo y tiene que poder ensenarse tachada.
LOS_ESTADOS_DE_UNA_RESERVA = ("pedida", "en_curso", "hecha")

# Lo que se le dice a quien pregunta por que no se puede: **motivos**, no un si o un no.
NO_SE_PUEDE_POR_LA_FECHA = "la_reserva_termina_antes_de_empezar"
NO_SE_PUEDE_POR_OTRA_RESERVA = "esa_maquina_ya_esta_reservada_esas_horas"
NO_SE_PUEDE_POR_AVERIA = "la_maquina_esta_averiada_esas_horas"
NO_SE_SABE_POR_AVERIA = "no_se_sabe_si_estaba_averiada_esas_horas"


def el_intervalo_esta_bien(desde, hasta) -> str | None:
    """El motivo por el que el intervalo **no** vale, o `None` si vale.

    Ver los **limites** en la cabecera del modulo: `hasta` estrictamente despues de `desde`.
    """
    if desde is None or hasta is None:
        return NO_SE_PUEDE_POR_LA_FECHA
    if hasta <= desde:
        return NO_SE_PUEDE_POR_LA_FECHA
    return None


def se_solapan(desde_una, hasta_una, desde_otra, hasta_otra) -> bool:
    """***Dos intervalos que comparten algo mas que la frontera.***

    Se comparan **intervalos semiabiertos**: `[desde, hasta)`. Los extremos **no se pisan**, asi que 9-11 y
    11-13 no se solapan (ver los limites, arriba). Escribirlo aqui, en una funcion con sus pruebas, es lo
    que impide que cada puerta lo haga a su manera.
    """
    return desde_una < hasta_otra and desde_otra < hasta_una


def las_vivas(reservas: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Las que **cuentan**: una reserva anulada no ocupa la maquina.

    *Anular no es borrar*: la reserva se queda en el cuaderno, tachada, y deja de ocupar. Es la misma regla
    que la de una lectura del contador o la de una averia.
    """
    return [una for una in reservas if not una.get("anulada")]


def la_que_choca(
    reservas: Iterable[Mapping[str, Any]],
    *,
    desde,
    hasta,
    maquina_id: int | None = None,
    saltando: int | None = None,
) -> Mapping[str, Any] | None:
    """La reserva **viva** que se solapa con la que llega, o `None` si el hueco esta libre.

    `maquina_id` acota a una maquina -dos maquinas distintas pueden estar reservadas a la vez, que es de lo
    que se trata-; si no se pasa, se miran todas las que lleguen.

    `saltando` es el identificador de la reserva que se esta **corrigiendo**: la que se corrige **no se
    choca consigo misma**. Sin esto, mover una reserva media hora fallaria siempre contra si misma.
    """
    for otra in las_vivas(reservas):
        if maquina_id is not None and otra.get("maquina_id") != maquina_id:
            continue
        if saltando is not None and otra.get("id") == saltando:
            continue
        if se_solapan(desde, hasta, otra.get("desde"), otra.get("hasta")):
            return otra
    return None


def _como_instante(cuando, *, al_cerrar: bool = False):
    """Un `date` o un `datetime`, como **instante comparable**.

    ***Las averias se apuntan por DIA y las reservas por HORA*** (17/10/2026), y comparar las dos cosas
    directamente **revienta** -lo caza la primera prueba que mete una averia de verdad, y salio al correr las
    puertas-.

    Lo que se hace aqui es lo unico honesto con el dato que hay: **una averia cubre el DIA ENTERO**, porque el
    dato sabe el dia y no la hora, y decir menos seria **afirmar una hora que nadie apunto**. `al_cerrar`
    distingue el final del dia del principio.
    """
    if isinstance(cuando, dt.datetime):
        return cuando
    if isinstance(cuando, dt.date):
        return dt.datetime.combine(cuando, dt.time.max if al_cerrar else dt.time.min)
    return cuando


def lo_que_impide_reservar(averias: Iterable[Mapping[str, Any]], *, desde, hasta) -> str | None:
    """***Una maquina averiada no se reserva***, y si no se sabe, se dice que no se sabe.

    La regla la marca el propio dato de la casa: `AveriaDeMaquina.resuelta` admite **tres** valores. Aqui se
    traducen a lo que se puede afirmar sobre el intervalo que se quiere reservar:

      * **`resuelta` es `False`** -sigue sin arreglar-: si la averia empezo antes de que acabe la reserva,
        la maquina **no estaba disponible**. Devuelve `NO_SE_PUEDE_POR_AVERIA`.
      * **`resuelta` es `True`** con fecha, y esa fecha es **posterior** al final de la reserva: durante la
        reserva la maquina **estaba averiada**. Devuelve `NO_SE_PUEDE_POR_AVERIA`.
      * **`resuelta` es `True`** con fecha **anterior** al principio: arreglada antes de empezar, **no
        impide nada**.
      * **`resuelta` es `True` SIN fecha**, o **`resuelta` es `None`**: **no se sabe**. Devuelve
        `NO_SE_SABE_POR_AVERIA`, que **no es lo mismo** que dejarlo pasar: es la regla de la casa -«fecha
        desconocida no significa vigente»-, y callarla convertiria un «no lo se» en un «si» que nadie ha
        comprobado.

    Se devuelve **el motivo**, no un booleano, porque «no se puede» y «no se sabe» tienen que poder decirse
    distinto: son dos respuestas y el agricultor decide cosas distintas con cada una.
    """
    desde = _como_instante(desde)
    hasta = _como_instante(hasta)
    for averia in averias or ():
        arranque = _como_instante(averia.get("fecha"))
        if arranque is None:
            # Una averia sin fecha no se puede situar en el tiempo. Si **no** esta resuelta, la maquina
            # sigue sin arreglar y eso vale para cualquier intervalo; si esta resuelta o no se sabe, no hay
            # forma de afirmar nada sobre estas horas.
            if averia.get("resuelta") is False:
                return NO_SE_PUEDE_POR_AVERIA
            return NO_SE_SABE_POR_AVERIA
        if arranque >= hasta:
            # Empezo despues de la reserva: no la afecta.
            continue
        # **Al cerrar el dia**: si se arreglo el 20, la maquina estuvo averiada **todo el 20**. Es lo
        # conservador, y es lo que el dato permite afirmar.
        arreglada = _como_instante(averia.get("fecha_resuelta"), al_cerrar=True)
        if averia.get("resuelta") is False:
            return NO_SE_PUEDE_POR_AVERIA
        if averia.get("resuelta") is True:
            if arreglada is None:
                return NO_SE_SABE_POR_AVERIA
            if arreglada > desde:
                # Seguia averiada cuando empezo la reserva. (Si se arreglo justo al empezar, se considera
                # arreglada: el limite es el mismo criterio que el de los extremos de un intervalo.)
                return NO_SE_PUEDE_POR_AVERIA
            continue
        # `resuelta is None`: no se sabe si sigue averiada.
        return NO_SE_SABE_POR_AVERIA
    return None


def lo_que_impide(
    reservas: Sequence[Mapping[str, Any]],
    averias: Sequence[Mapping[str, Any]],
    *,
    desde,
    hasta,
    maquina_id: int,
    saltando: int | None = None,
) -> tuple[str | None, Mapping[str, Any] | None]:
    """***La pregunta entera, en un sitio***: `(motivo, la_reserva_que_choca)`.

    El orden importa y es el del encargo: primero **el intervalo** -si esta mal formado no se puede
    comparar nada con el-, luego **la averia** -si la maquina no estaba, dar igual quien la pidio- y
    despues **el solape**. Se devuelve **la reserva que choca** para poder decirle al agricultor **con
    cual** se esta topando, que es lo unico que le permite decidir.
    """
    motivo_del_intervalo = el_intervalo_esta_bien(desde, hasta)
    if motivo_del_intervalo:
        return motivo_del_intervalo, None
    motivo_de_la_averia = lo_que_impide_reservar(averias, desde=desde, hasta=hasta)
    if motivo_de_la_averia:
        return motivo_de_la_averia, None
    choca = la_que_choca(reservas, desde=desde, hasta=hasta, maquina_id=maquina_id, saltando=saltando)
    if choca is not None:
        return NO_SE_PUEDE_POR_OTRA_RESERVA, choca
    return None, None
