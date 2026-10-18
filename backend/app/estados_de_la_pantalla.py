"""**Los cinco estados de una pantalla, y las dos cosas que conservan** (contrato comun, 17/10/2026).

El contrato comun de la cola lo dice en una linea, y es la mas densa de todo el documento:

    ***Vacio explica que hacer; cargando no muestra 0; error conserva datos; offline muestra antiguedad;
    conflicto muestra dos versiones. Volver y recargar conservan contexto.***

***Y las seis cosas son la misma idea repetida***: **una pantalla nunca miente sobre lo que sabe**. *Si no hay
nada, lo dice y dice que hacer. Si esta cargando, no enseña un cero que parece un dato. Si fallo, no borra lo
que el agricultor habia escrito. Si no hay conexion, dice de cuando son los datos. Si dos han cambiado lo
mismo, enseña las dos versiones.*

***Por que esto es un modulo y no un estilo***: **los cinco errores se cometen igual en las sesenta
pantallas**, y se cometen **sin querer** -enseñar `0` mientras carga es lo mas natural del mundo-. Tenerlos
escritos en un sitio es lo que hace que la pantalla sesenta se acuerde.
"""

from __future__ import annotations

import datetime as dt

# ---------------------------------------------------------------------------
# ***Los cinco estados***
# ---------------------------------------------------------------------------

VACIO = "vacio"
CARGANDO = "cargando"
CON_DATOS = "con_datos"
ERROR = "error"
SIN_CONEXION = "sin_conexion"
CONFLICTO = "conflicto"

LOS_ESTADOS = (VACIO, CARGANDO, CON_DATOS, ERROR, SIN_CONEXION, CONFLICTO)


class EstadoQueNoSeSabeCualEs(ValueError):
    """***Un estado que no es ninguno de los cinco.*** *Se para y se dice, en vez de pintar algo.*"""


def el_estado(**datos) -> dict:
    """***Como hay que pintar ahora mismo, con la regla del contrato detras.***

    ***Y las cuatro correcciones que hace sola***, que son los cuatro errores de siempre:

    1. **Cargando -> `valor: None`.** *No `0`: un cero **parece un dato** y el agricultor se lo cree.*
       ***Es la misma regla que el desconocido del contador***: lo que no se sabe, no se convierte en cero.
    2. **Vacio -> con `que_hacer` obligatorio.** *Una pantalla vacia sin salida deja al agricultor mirando.*
    3. **Error -> con `lo_que_habia` conservado.** *Un fallo de red **no puede borrar** lo que estaba
       escrito: es lo que mas duele y lo que menos se perdona.*
    4. **Sin conexion -> con `de_cuando` obligatorio.** *«Sin conexion» y nada mas no dice si lo que se ve es
       de hace un minuto o de anteayer.*
    """
    cargando = bool(datos.get("cargando"))
    hay_error = datos.get("error")
    sin_conexion = bool(datos.get("sin_conexion"))
    hay_valor = datos.get("valor") is not None
    hay_conflicto = bool(datos.get("conflicto"))

    if cargando:
        return {
            "estado": CARGANDO,
            # ***Aqui esta el error numero uno de las pantallas***, y por eso lo arregla el modulo.
            "valor": None,
            "que_hacer": None,
            "enseña_algo": False,
        }
    if hay_error:
        return {
            "estado": ERROR,
            # ***El error NO borra lo que habia***: se devuelve junto al error.
            "valor": datos.get("lo_que_habia"),
            "lo_que_habia": datos.get("lo_que_habia"),
            "mensaje": str(hay_error),
            "que_hacer": datos.get("que_hacer") or "Volver a intentarlo",
            "enseña_algo": datos.get("lo_que_habia") is not None,
        }
    if hay_conflicto:
        # ***Dos versiones, no una elegida por el programa.*** *Quien decide es el agricultor.*
        return {
            "estado": CONFLICTO,
            "valor": None,
            "la_mia": datos.get("la_mia"),
            "la_de_otro": datos.get("la_de_otro"),
            "quien": datos.get("quien"),
            "cuando": datos.get("cuando"),
            "enseña_algo": True,
        }
    if sin_conexion:
        return {
            "estado": SIN_CONEXION,
            "valor": datos.get("valor"),
            # ***Y de cuando son los datos***: sin eso, «sin conexion» no dice nada util.
            "de_cuando": datos.get("de_cuando"),
            "antiguedad": _la_antiguedad(datos.get("de_cuando"), datos.get("ahora")),
            "enseña_algo": hay_valor,
        }
    if not hay_valor:
        return {
            "estado": VACIO,
            "valor": None,
            # ***«Vacio explica que hacer»***: y si no se le pasa, se dice que falta.
            "que_hacer": datos.get("que_hacer") or None,
            "enseña_algo": False,
        }
    return {"estado": CON_DATOS, "valor": datos.get("valor"), "enseña_algo": True}


def _la_antiguedad(de_cuando, ahora=None):
    """***Cuanto hace de esos datos***, dicho como se dice en el campo.

    *«Hace 2 horas» se entiende; una marca de tiempo no.*
    """
    if de_cuando is None:
        return None
    ahora = ahora or dt.datetime.now()
    if isinstance(de_cuando, dt.date) and not isinstance(de_cuando, dt.datetime):
        de_cuando = dt.datetime(de_cuando.year, de_cuando.month, de_cuando.day)
    segundos = max(0, (ahora - de_cuando).total_seconds())
    if segundos < 90:
        return "hace un momento"
    if segundos < 3600:
        return f"hace {int(segundos // 60)} minutos"
    if segundos < 86400:
        return f"hace {int(segundos // 3600)} horas"
    return f"hace {int(segundos // 86400)} dias"


def lo_que_falta_para_pintar(estado: dict) -> list[str]:
    """***Lo que a ese estado le falta para cumplir el contrato.***

    ***Y devuelve lo que falta, no un `True`/`False`***: *«mal» no se puede arreglar; «le falta decir que
    hacer» si.*
    """
    cual = estado.get("estado")
    if cual not in LOS_ESTADOS:
        raise EstadoQueNoSeSabeCualEs(f"«{cual}» no es un estado de los de aqui: {', '.join(LOS_ESTADOS)}")

    falta = []
    if cual == VACIO and not estado.get("que_hacer"):
        falta.append("que_hacer")
    if cual == CARGANDO and estado.get("valor") is not None:
        falta.append("valor")  # ***un cero mientras carga: el error que el contrato nombra***
    if cual == ERROR and estado.get("lo_que_habia") is None and estado.get("enseña_algo"):
        falta.append("lo_que_habia")
    if cual == SIN_CONEXION and not estado.get("de_cuando"):
        falta.append("de_cuando")
    if cual == CONFLICTO and (estado.get("la_mia") is None or estado.get("la_de_otro") is None):
        falta.append("las_dos_versiones")
    return falta


# ---------------------------------------------------------------------------
# ***Volver y recargar conservan contexto***
# ---------------------------------------------------------------------------


def el_contexto(*, filtros=None, orden=None, columnas=None, pagina=None, busqueda: str = "") -> dict:
    """***Lo que hay que devolver al volver, o despues de recargar***.

    *«Volver y recargar conservan contexto»: si un agricultor ha filtrado, ordenado y esta en la pagina 4,
    volver a entrar y encontrarse la lista entera es perder su trabajo de navegacion.*
    """
    return {
        "filtros": dict(filtros or {}),
        "orden": orden,
        "columnas": list(columnas or []),
        "pagina": pagina,
        "busqueda": busqueda or "",
    }


def el_pie_de_la_tabla(*, cuantos_se_ven: int, cuantos_hay, filtrados: bool = False) -> dict:
    """***«Pie X de Y»***, y **la exportacion declara si lleva lo filtrado o todo**.

    ***Por que las dos cosas juntas***: *un pie que dice «12» sin decir «de 300» hace creer que hay doce, y
    una exportacion que no dice que lleva **no se puede usar para nada serio** -ni para reclamar, ni para
    comparar dos descargas-.*
    """
    if cuantos_hay is None:
        # ***Si no se sabe cuantos hay, no se inventa***: se dice que no se sabe.
        return {"se_ven": cuantos_se_ven, "hay": None, "texto": f"{cuantos_se_ven} (no se sabe cuantos hay)"}
    return {
        "se_ven": cuantos_se_ven,
        "hay": cuantos_hay,
        "texto": f"{cuantos_se_ven} de {cuantos_hay}",
        "hay_filtro": bool(filtrados),
        # ***Y la exportacion lo dice***: *«incluye los filtrados» o «incluye todo».*
        "la_exportacion_lleva": "lo filtrado" if filtrados else "todo",
    }
