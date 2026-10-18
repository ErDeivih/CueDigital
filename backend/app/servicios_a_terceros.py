"""**El trabajo que se le hace a un tercero** (CRM-04, 17/10/2026).

***Este modulo faltaba entero.*** La tabla `trabajos_para_terceros` **existe desde el 14/10** -con sus
columnas, su clave de reenvio y su indice unico-, y **no habia ni una linea de logica que la usara**: ni una
puerta, ni un servicio, ni una prueba. *La mitad de una funcionalidad es la clase de cosa que parece hecha
desde fuera: la tabla esta, la pantalla no.*

***Y las reglas estaban todas escritas***, en el propio comentario del modelo y en el contrato. Aqui estan,
en codigo y probadas:

    ***10 ha de un tercero NO suman superficie propia***     -> `la_superficie_del_tercero`
    ***el insumo del cliente no descuenta almacen propio; el propio si***  -> `de_quien_es_el_insumo`
    ***cambiar la tarifa no reescribe los partes aceptados***  -> `aceptar` copia la tarifa
    ***el margen marca los costes desconocidos***              -> `lo_que_se_sabe_del_margen`
    ***propuesto -> aceptado -> hecho***, y cancelado          -> `se_puede_pasar_a`
"""

from __future__ import annotations

from decimal import Decimal

from . import superficies

# ***Los cuatro estados, y son los del modelo***.
PROPUESTO = "propuesto"
ACEPTADO = "aceptado"
HECHO = "hecho"
CANCELADO = "cancelado"

# ***Y de quien es el insumo***, que es lo que decide si toca el almacen propio.
DEL_CLIENTE = "cliente"
PROPIO = "propio"

# ***El recorrido, y no hay mas***: *lo que se propone no es un trabajo, y lo aceptado no es lo hecho.*
LOS_QUE_SE_PUEDEN = {
    PROPUESTO: (ACEPTADO, CANCELADO),
    ACEPTADO: (HECHO, CANCELADO),
    HECHO: (),          # ***lo hecho no se deshace: se corrige, y queda el rastro***
    CANCELADO: (),      # ***y lo cancelado no vuelve: se hace otro***
}


class NoSePuedePasar(ValueError):
    """***Un paso que el recorrido no permite.*** *Se para y se dice desde donde y hasta donde.*"""


def se_puede_pasar_a(*, desde: str, hasta: str) -> bool:
    """***Si el recorrido permite ese paso.***

    ***Y no se «arregla» pasando por en medio***: *un trabajo cancelado que se convierte en hecho sin pasar
    por aceptado seria un parte que nadie acepto.*
    """
    return hasta in LOS_QUE_SE_PUEDEN.get(desde, ())


def el_paso(*, desde: str, hasta: str) -> str:
    """***El paso, comprobado***, o el error que dice por que no."""
    if desde not in LOS_QUE_SE_PUEDEN:
        raise NoSePuedePasar(f"«{desde}» no es un estado de los de aqui: {', '.join(LOS_QUE_SE_PUEDEN)}")
    if not se_puede_pasar_a(desde=desde, hasta=hasta):
        posibles = LOS_QUE_SE_PUEDEN[desde]
        raise NoSePuedePasar(
            f"de «{desde}» no se pasa a «{hasta}»: "
            + (f"solo a {', '.join(posibles)}" if posibles else "***de ahi no se sale***")
        )
    return hasta


# ---------------------------------------------------------------------------
# ***1 · «10 ha de un tercero no suman superficie propia»***
# ---------------------------------------------------------------------------


def la_superficie_del_tercero(superficie_ha) -> dict:
    """***La superficie de un trabajo externo, y por que NO se suma a la de casa.***

    El modelo lo dice con estas palabras: *«10 ha de un tercero no suman superficie propia»*. ***Y por eso la
    ubicacion y la superficie viven en su tabla***, no en `parcelas`: *si estuvieran alli, cualquier suma de
    superficie del agricultor -y el volcado de la PAC- **contaria tierras que no son suyas***.*

    ***No se suma, pero se dice***: *el trabajo existe, ocupa la maquina y da dinero; lo que no hace es
    cambiar de dueño a la tierra.*
    """
    return {
        "superficie_ha": superficie_ha,
        # ***Y la magnitud con la que se cuenta***, que es la que impide que se sume por descuido.
        "magnitud": superficies.LO_DE_UN_TERCERO,
        "suma_a_lo_propio": False,
        # ***Y el porque, dentro del dato***: *quien lo lea sin el comentario no lo va a adivinar.*
        "motivo": "es tierra de un tercero: se trabaja, no se posee",
    }


def se_puede_sumar_a_lo_propio(*, magnitud: str) -> bool:
    """***La comprobacion, hecha con la regla de siempre.***

    ***Una sola regla en todo el programa***: *`superficies.se_pueden_sumar`. **No hay una segunda** que diga
    lo mismo de otra forma, porque dos reglas que tienen que coincidir acaban no coincidiendo.*
    """
    return superficies.se_pueden_sumar(magnitud, superficies.LO_QUE_SE_CULTIVA)


# ---------------------------------------------------------------------------
# ***2 · El insumo, y de quien es***
# ---------------------------------------------------------------------------


def de_quien_es_el_insumo(cual: str) -> dict:
    """***El insumo del cliente NO descuenta almacen propio; el propio SI.***

    ***Y la decision se copia en el parte EN EL MOMENTO de apuntarlo*** -lo dice el modelo-: *si despues
    alguien cambia de quien era, **un parte ya firmado no puede cambiar de significado**.*

    *Lo que se guarda en el parte es una **copia** de la decision, no una referencia: es la diferencia entre
    un documento y un borrador.*
    """
    if cual not in (DEL_CLIENTE, PROPIO):
        raise ValueError(f"«{cual}» no es de nadie: es `{DEL_CLIENTE}` o `{PROPIO}`")
    return {
        "de_quien_es": cual,
        # ***Y lo que hace con el almacen, que es la unica consecuencia***.
        "descuenta_el_almacen_propio": cual == PROPIO,
        # ***Y el porque, para que nadie lo «arregle»***.
        "motivo": (
            "el insumo es del cliente: no sale del almacen de casa"
            if cual == DEL_CLIENTE
            else "el insumo es propio: sale del almacen y hay que descontarlo"
        ),
    }


# ---------------------------------------------------------------------------
# ***3 · ***«Cambiar la tarifa no reescribe los partes aceptados»******
# ---------------------------------------------------------------------------


def aceptar(*, trabajo: dict, tarifa, quien: int, cuando) -> dict:
    """***Se acepta el trabajo, y a partir de aqui el parte lleva SU tarifa.***

    ***Es la regla que el modelo escribe con mas fuerza***: *«cambiar la tarifa no reescribe los partes
    aceptados anteriores»*. **El precio de un trabajo aceptado es el que se acepto, no el que la casa tenga
    hoy en la lista** -y por eso el parte lleva la tarifa, las horas, la maquina, el operario y el
    desplazamiento **copiados**-.*

    ***Y solo desde `propuesto`***: *aceptar dos veces lo mismo no es aceptar; es reescribir lo que ya se
    acepto, que es justo lo que no se puede.*
    """
    el_paso(desde=trabajo.get("estado", PROPUESTO), hasta=ACEPTADO)
    return {
        **trabajo,
        "estado": ACEPTADO,
        # ***La tarifa se COPIA***: queda congelada con el parte.
        "tarifa_aceptada": tarifa if tarifa is not None else trabajo.get("tarifa_por_hora"),
        "aceptado_por": quien,
        "aceptado_en": cuando,
    }


def cambiar_la_tarifa_de_la_casa(*, trabajo: dict, tarifa_nueva) -> dict:
    """***Cambiar la tarifa de la casa NO toca un trabajo ya aceptado.***

    ***Y tampoco lanza un error***: *cambiar la tarifa es una operacion legitima; lo que no puede es
    **reescribir hacia atras**. Se devuelve el trabajo **igual**, y se dice que no se ha tocado.*

    *Un error aqui obligaria a no poder cambiar la tarifa mientras haya un parte abierto, que es peor.*
    """
    if trabajo.get("estado") in (ACEPTADO, HECHO):
        return {
            **trabajo,
            "tarifa_por_hora": trabajo.get("tarifa_por_hora"),
            "no_se_toca": "el parte ya esta aceptado: su tarifa es la que se acepto",
            "tarifa_aceptada": trabajo.get("tarifa_aceptada"),
        }
    return {**trabajo, "tarifa_por_hora": tarifa_nueva, "no_se_toca": None}


# ---------------------------------------------------------------------------
# ***4 · El margen, con los costes que no constan***
# ---------------------------------------------------------------------------


def lo_que_se_sabe_del_margen(*, cobrado, coste_conocido, horas: list | None = None) -> dict:
    """***El margen, y «hay costes que no constan».***

    El modelo: *«el contrato pide que el margen **marque los costes desconocidos**… esto es anulable, y quien
    sume tiene que decir «hay costes que no constan» **en vez de contar un cero**»*.

    ***Y es la misma regla del contador y de los paneles***: *un cero y un «no lo se» son cosas distintas.*
    **Un margen calculado con un cero que no era cero sale mejor de lo que es** -y ese es el error que hace
    tomar decisiones malas-.
    """
    if coste_conocido is None:
        return {
            "cobrado": cobrado,
            "coste": None,
            "margen": None,
            # ***Y se dice, no se calcula con cero.***
            "hay_costes_que_no_constan": True,
            "aviso": "no se sabe el coste, asi que no hay margen que dar",
        }
    return {
        "cobrado": cobrado,
        "coste": coste_conocido,
        "margen": (cobrado or 0) - coste_conocido,
        "hay_costes_que_no_constan": bool(horas is not None and any(h is None for h in horas)),
        "aviso": None,
    }


def lo_que_cuesta_el_trabajo(*, tarifa, horas, desplazamiento_km=None, precio_del_km=None) -> dict:
    """***Mano de obra y desplazamiento, contados por separado.***

    El contrato: *«maquina, horas, operario, **desplazamiento y coste conocido por separado**»*. *Juntarlos en
    un numero hace imposible saber si el trabajo salio caro por las horas o por el viaje.*
    """
    if tarifa is None or horas is None:
        return {
            "mano_de_obra": None,
            "desplazamiento": None,
            "coste": None,
            "hay_costes_que_no_constan": True,
        }
    mano = tarifa * horas
    viaje = None
    if desplazamiento_km is not None and precio_del_km is not None:
        viaje = desplazamiento_km * precio_del_km
    return {
        "mano_de_obra": mano,
        "desplazamiento": viaje,
        # ***Y el total, sumando lo que se sabe***: *el viaje puede no saberse, y entonces se dice.*
        "coste": mano + viaje if viaje is not None else None,
        "hay_costes_que_no_constan": viaje is None,
    }
