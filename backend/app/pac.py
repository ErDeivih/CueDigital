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
