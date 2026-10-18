"""**La preparacion de la PAC: la fuente manda, y lo que falta se dice** (CRM-09, 17/10/2026).

El contrato de la cola lo pide asi, y cada linea es una decision:

    Fuente legal por ambito/año/fecha de vigencia y version. Consultar BOE, FEGA, MAPA, Junta y BOCyL…
    ***ninguna competencia autoriza usar su interpretacion como norma***.
    ***Porcentajes con numerador/denominador; tierra sin cultivo no desaparece para pintar verde.***
    ***Escenario siguiente año separado de lo declarado y de lo realizado.***
    ***No envio directo ni garantia de elegibilidad.***
    Aceptacion: ***fuente de otra campaña/comunidad no se aplica***; falta area/cultivo/evidencia ->
    incompleto; ***editar escenario no cambia historial***.

***Y aqui esta lo que este modulo defiende, en una frase***: **preparar no es declarar**. Lo que sale de aqui
es un **paquete para revisar**, con lo que falta dicho, y **nunca** un documento que se manda solo ni una
promesa de que vaya a valer.

***Por que la vigencia es lo primero***: una ayuda de 2023 no se pide en 2026 con las reglas de 2023. *Y no
basta con «es de mi comunidad»: tiene que ser **de mi comunidad, de mi año, y vigente ese dia**.*
"""

from __future__ import annotations

import datetime as dt

# ---------------------------------------------------------------------------
# La fuente, con su vigencia
# ---------------------------------------------------------------------------
#
# ***Una fuente legal no es un texto: es un texto CON FECHAS.*** La misma norma cambia de un año a otro, y
# aplicarla fuera de su ventana es exactamente el error que el contrato prohibe.

AMBITOS = ("estatal", "autonomico", "comarcal")

# ***Y lo que NO autoriza el contrato***: que una administracion publique su lectura de la norma **no**
# convierte esa lectura en la norma. *Se cita la fuente, no la interpretacion de quien la publico.*
NO_ES_NORMA = "la interpretacion de una administracion no es la norma: se cita la fuente, y se revisa"


class FuenteQueNoAplica(ValueError):
    """***Una fuente de otro año o de otro sitio.*** *No se aplica: se para y se dice por que.*"""


def la_fuente(
    *,
    referencia: str,
    ambito: str,
    anio: int,
    desde: dt.date,
    hasta: dt.date,
    version: str = "",
    url: str = "",
) -> dict:
    """***Una fuente legal, con lo que hace falta para saber si vale hoy.***

    `referencia` es **lo que se cita** -«Orden…», «Real Decreto…»-, y `ambito` + `anio` + `desde`/`hasta` es
    **cuando y donde manda**. *Sin esas cuatro cosas, una fuente es un texto suelto.*
    """
    if ambito not in AMBITOS:
        raise FuenteQueNoAplica(
            f"«{ambito}» no es un ambito de los de aqui: {', '.join(AMBITOS)}. *Una fuente sin ambito no se "
            "sabe a quien aplica.*"
        )
    if hasta < desde:
        raise FuenteQueNoAplica(f"la vigencia acaba antes de empezar: {desde} .. {hasta}")
    return {
        "referencia": referencia,
        "ambito": ambito,
        "anio": int(anio),
        "desde": desde,
        "hasta": hasta,
        "version": version,
        "url": url,
        # ***Y la advertencia, dentro de la propia fuente***: *que no se confunda lo que dice la norma con lo
        # que una administracion entiende que dice.*
        "aviso": NO_ES_NORMA,
    }


def se_aplica_a(fuente: dict, *, ambito: str, campana: int, cuando: dt.date) -> bool:
    """***Si esa fuente se puede usar para esa campaña, en ese ambito, ese dia.***

    ***Y las tres cosas tienen que cuadrar***: el **ambito**, el **año** y el **dia**. *Una fuente de otra
    campaña o de otra comunidad no se aplica -lo dice el contrato-, y una que aun no ha entrado en vigor o
    que ya ha caducado, tampoco.*
    """
    return (
        fuente.get("ambito") == ambito
        and int(fuente.get("anio") or 0) == int(campana)
        and fuente.get("desde") is not None
        and fuente.get("hasta") is not None
        and fuente["desde"] <= cuando <= fuente["hasta"]
    )


def la_que_aplica(fuentes: list[dict], *, ambito: str, campana: int, cuando: dt.date) -> dict | None:
    """***La que vale, o nada.*** *Y si hay mas de una, se coge la de version mas nueva: la que deroga a la
    anterior es la que manda.*"""
    validas = [f for f in fuentes if se_aplica_a(f, ambito=ambito, campana=campana, cuando=cuando)]
    if not validas:
        return None
    return sorted(validas, key=lambda f: str(f.get("version") or ""))[-1]


# ---------------------------------------------------------------------------
# ***El porcentaje, que sin denominador no es nada***
# ---------------------------------------------------------------------------


class PorcentajeSinDenominador(ValueError):
    """***Un porcentaje sin denominador.*** *«El 80%» no dice el 80% **de que**.*"""


def el_porcentaje(*, numerador, denominador, de_que: str, unidad: str = "ha") -> dict:
    """***Un porcentaje, con su numerador y su denominador a la vista.***

    ***Por que no se devuelve un numero y ya***: *«el 80% de la ayuda» no significa nada si no se sabe el 80%
    de que, y en la PAC eso es la diferencia entre una parcela y la comarca entera.* El contrato lo pide asi:
    *«porcentajes con numerador/denominador»*.

    ***Y `None` cuando no hay denominador, en vez de cero***: *cero por ciento y «no se sabe» son cosas
    distintas, y un cero pinta un mapa de verde que no es verdad.*
    """
    if denominador is None:
        raise PorcentajeSinDenominador(
            f"«{de_que}» no tiene denominador, asi que no hay porcentaje que dar: *un porcentaje sin "
            "denominador no dice de que es.*"
        )
    if denominador == 0:
        # ***Cero de cero no es cero por ciento***: es que no hay nada que medir.
        return {
            "de_que": de_que,
            "unidad": unidad,
            "numerador": numerador,
            "denominador": 0,
            "porcentaje": None,
            "aviso": "no hay denominador que medir, asi que no hay porcentaje",
        }
    return {
        "de_que": de_que,
        "unidad": unidad,
        "numerador": numerador,
        "denominador": denominador,
        "porcentaje": round(100.0 * (numerador or 0) / denominador, 2),
    }


def tierra_sin_cultivo_no_se_pinta_de_verde(*, superficie_total, superficie_con_cultivo) -> dict:
    """***La tierra sin cultivo no desaparece para pintar verde.***

    El contrato, con estas palabras: *«tierra sin cultivo no desaparece para pintar verde»*. *Traducido: si en
    la finca hay 100 ha y solo 60 tienen cultivo, el porcentaje **que se enseña es sobre las 100**, y las
    otras 40 **se dicen**.*

    ***Y por que importa tanto***: con el denominador tramposo -solo las 60-, un año malo sale al 100% y
    nadie ve lo que se ha quedado fuera. *Un panel que se hace el mapa mas bonito es un panel que engaña.*
    """
    sin_cultivo = (superficie_total or 0) - (superficie_con_cultivo or 0)
    return {
        **el_porcentaje(
            numerador=superficie_con_cultivo,
            denominador=superficie_total,
            de_que="superficie con cultivo sobre el total de la finca",
        ),
        # ***Y las hectareas que se han quedado fuera, dichas***: no se esconden en el numerador.
        "sin_cultivo": sin_cultivo,
        "se_queda_fuera": sin_cultivo if sin_cultivo > 0 else 0,
    }

# ---------------------------------------------------------------------------
# ***Lo que le falta a un recinto***, en un solo sitio
# ---------------------------------------------------------------------------


def lo_que_falta_para_la_pac(*, superficie_ha, referencia, cultivo) -> list[str]:
    """***Las cuestiones pendientes de un recinto***, dichas con su clave.

    *Es la mitad del contrato: «falta area/cultivo/evidencia -> **incompleto**». Y vive **aqui** -no en la
    puerta- porque **la usa tambien el escenario del año que viene**: si hubiera dos copias de la regla, un dia
    dirian cosas distintas de la misma tierra.*

    *Una tierra sin superficie no es una tierra de cero hectareas, y una sin cultivo no es una tierra sin
    sembrar: es una tierra de la que **no consta**.*
    """
    falta = []
    if superficie_ha is None:
        falta.append("falta_superficie")
    if not (referencia or "").strip():
        falta.append("falta_referencia")
    if cultivo is None:
        falta.append("falta_cultivo")
    elif not ((cultivo or {}).get("ecorregimen") or "").strip():
        falta.append("falta_ecorregimen")
    return falta


# ---------------------------------------------------------------------------
# ***El escenario del año que viene***
# ---------------------------------------------------------------------------


def el_escenario(el_paquete: dict, *, anio: int, cambios: dict | None = None) -> dict:
    """***Un escenario del año que viene: una HIPOTESIS, no lo declarado ni lo realizado.***

    *El contrato lo pide con estas palabras: «**escenario siguiente año separado de lo declarado y de lo
    realizado**. Comparar alternativas **sin consumir**».*

    ***Y por eso esta funcion no escribe ni puede escribir***: *recibe el paquete -que es lo que la finca tiene
    de verdad- y devuelve **otra cosa**, con su capa dicha. **Editar un escenario no cambia el historial porque no
    hay historial que tocar**; y comparar dos alternativas **no consume ninguna de las dos**, porque no hay nada
    que consumir.*

    ### Lo que NO hace, y se dice

      · **No dice si es elegible.** *Un escenario no es una solicitud, y este programa no envia nada.*
      · **No inventa el cultivo que falta**: *si no se le pasa, el recinto sigue **incompleto**, con su clave.*
      · **No cambia las hectareas de la finca**: *la superficie es la que consta; lo que cambia es lo que se
        propone sembrar.*

    `cambios` es `{parcela_id: {"cultivo": {...}}}` -lo mismo que lleva un recinto del paquete, con `especie`,
    `variedad`, `ecorregimen` y `superficie_cultivada_ha`-.
    """
    # ***Las claves llegan como TEXTO cuando vienen de un JSON*** (18/10/2026): *`{"5": {...}}`, no
    # `{5: {...}}`. Buscar `5` en ese diccionario **no encontraba nada**, y el cambio **se perdia en silencio**:
    # el escenario salia igual que el paquete y no habia forma de saber por que. Se normalizan a numero.*
    los_cambios = {}
    for la_clave, el_valor in (cambios or {}).items():
        try:
            los_cambios[int(la_clave)] = el_valor
        except (TypeError, ValueError):
            los_cambios[la_clave] = el_valor
    los_recintos: list[dict] = []
    lo_que_cambia: list[dict] = []

    # ***`las_tierras` es como llama el paquete a sus recintos*** -se comprobo leyendo su `return`, no
    # suponiendolo-.
    for uno in el_paquete.get("las_tierras") or []:
        suyo = dict(uno)
        el_cambio = los_cambios.get(uno.get("parcela_id"))
        if isinstance(el_cambio, dict) and "cultivo" in el_cambio:
            lo_que_cambia.append(
                {
                    "parcela_id": uno.get("parcela_id"),
                    "alias": uno.get("alias"),
                    "que": "el cultivo",
                    "antes": uno.get("cultivo"),
                    "ahora": el_cambio["cultivo"],
                }
            )
            suyo["cultivo"] = el_cambio["cultivo"]
        suyo["falta"] = lo_que_falta_para_la_pac(
            superficie_ha=suyo.get("superficie_ha"),
            referencia=suyo.get("referencia"),
            cultivo=suyo.get("cultivo"),
        )
        suyo["completa"] = not suyo["falta"]
        # ***La capa, dicha en cada recinto***: *esto es una hipotesis, y no se confunde con lo que hay.*
        suyo["capa"] = "hipotesis"
        los_recintos.append(suyo)

    con_cultivo = sum(
        float((uno.get("cultivo") or {}).get("superficie_cultivada_ha") or 0) for uno in los_recintos
    )
    la_superficie = sum(float(uno.get("superficie_ha") or 0) for uno in los_recintos)
    # ***El denominador NO se estrecha***: *las hectareas sin cultivo siguen contando -«tierra sin cultivo no
    # desaparece para pintar verde»-, y el escenario no es la excepcion.*
    # ***Se le pasa el numero, aunque sea cero.*** *`or None` convertia «no hay hectareas» en «no hay
    # denominador», y eso **lanza**: `el_porcentaje` ya sabe que hacer con un cero -no hay nada que medir, y el
    # porcentaje es `None`-, pero con `None` no puede.*
    el_resumen = tierra_sin_cultivo_no_se_pinta_de_verde(
        superficie_total=la_superficie, superficie_con_cultivo=con_cultivo
    )

    return {
        "anio": anio,
        "capa": "hipotesis",
        "es_hipotesis": True,
        "no_es_lo_declarado": True,
        "no_es_lo_realizado": True,
        "toca_lo_guardado": False,
        "no_es_garantia": True,
        "los_recintos": los_recintos,
        "lo_que_cambia": lo_que_cambia,
        "el_resumen": el_resumen,
        "los_incompletos": [uno for uno in los_recintos if not uno["completa"]],
    }


def comparar_alternativas(uno: dict, otro: dict) -> dict:
    """***Dos escenarios, frente a frente, sin consumir ninguno.***

    *Devuelve **en que se diferencian**, recinto a recinto, y **los dos totales con su porcentaje**. No toca la
    base, no guarda nada y no elige: **comparar no es decidir**.*
    """
    por_id_uno = {u.get("parcela_id"): u for u in uno.get("los_recintos") or []}
    por_id_otro = {u.get("parcela_id"): u for u in otro.get("los_recintos") or []}
    las_diferencias = []
    for el_id in sorted(set(por_id_uno) | set(por_id_otro)):
        el_de_uno = por_id_uno.get(el_id) or {}
        el_de_otro = por_id_otro.get(el_id) or {}
        if (el_de_uno.get("cultivo"), el_de_uno.get("completa")) != (
            el_de_otro.get("cultivo"),
            el_de_otro.get("completa"),
        ):
            las_diferencias.append(
                {
                    "parcela_id": el_id,
                    "alias": el_de_uno.get("alias") or el_de_otro.get("alias"),
                    "en_uno": el_de_uno.get("cultivo"),
                    "en_otro": el_de_otro.get("cultivo"),
                    "completa_en_uno": el_de_uno.get("completa"),
                    "completa_en_otro": el_de_otro.get("completa"),
                }
            )
    return {
        "no_consume_nada": True,
        "las_diferencias": las_diferencias,
        "cuantas": len(las_diferencias),
        "el_total_en_uno": (uno.get("el_resumen") or {}).get("porcentaje"),
        "el_total_en_otro": (otro.get("el_resumen") or {}).get("porcentaje"),
    }
