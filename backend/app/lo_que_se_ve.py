"""**Lo que de verdad se ve en la pantalla** (contrato comun, 17/10/2026).

El contrato comun de la cola lo pide asi, en la linea 31 y en las 235-236:

    Barra: controles totalmente dentro de viewport y de cualquier ancestro que recorte. Verificar
    ***rectangulo completo, nombre legible, foco visible y activacion***. ***Un rectangulo con ancho
    positivo fuera de la pantalla no es visible.*** Considerar zoom y scrollbars, ***no asumir ancho util
    = viewport***.

    Medir recorte completo. Contar clics y filas utiles, no solo px.

***Y aqui esta la idea, que es la misma del resto del programa***: **«esta en el DOM» no es «se ve»**. *Un
boton puede existir, tener texto, y estar **fuera de la pantalla** -o tapado por un recorte de su padre-, y
entonces **el agricultor no lo puede pulsar** por mucho que la prueba del DOM lo encuentre.*

***Por que se puede medir sin navegador***: *es **geometria**. Un rectangulo y una lista de recortes son
numeros, y si el rectangulo cabe dentro de todos, se ve. **Lo unico que no se puede hacer aqui es mirarlo con
los ojos**, y eso el contrato manda decirlo -«si solo hay DOM, marcar el limite»-.*
"""

from __future__ import annotations

# ***Un rectangulo***, como lo da el navegador: la esquina y el tamaño.
def un_rectangulo(*, x: float, y: float, ancho: float, alto: float) -> dict:
    return {"x": float(x), "y": float(y), "ancho": float(ancho), "alto": float(alto)}


def _cabe_dentro(suyo: dict, marco: dict) -> bool:
    """***Si el rectangulo esta entero dentro del marco***, tocando los cuatro bordes.

    ***Y se mira el rectangulo COMPLETO, no su esquina***: *un control con la esquina dentro y la mitad fuera
    esta **cortado**, y lo que se ve a medias no se puede pulsar entero.*
    """
    return (
        suyo["x"] >= marco["x"]
        and suyo["y"] >= marco["y"]
        and suyo["x"] + suyo["ancho"] <= marco["x"] + marco["ancho"]
        and suyo["y"] + suyo["alto"] <= marco["y"] + marco["alto"]
    )


def se_ve_entero(control: dict, *, recortes: list[dict]) -> dict:
    """***Si un control se ve entero, y si no, quien lo tapa.***

    ***Los recortes son el viewport Y todos los ancestros que recortan*** -una barra con `overflow: hidden`,
    un panel con scroll-: *mirar solo el viewport es el error que el contrato nombra: **«no asumir ancho util
    = viewport»**.*

    ***Y `ancho_positivo_no_basta`***: *un rectangulo puede tener 200 px de ancho y estar **entero** fuera de
    la pantalla. El navegador dice que mide 200; el agricultor no lo ve.*
    """
    if control["ancho"] <= 0 or control["alto"] <= 0:
        return {
            "se_ve": False,
            "lo_que_lo_tapa": "no tiene tamaño",
            "ancho_positivo_no_basta": False,
        }
    for marco in recortes:
        if not _cabe_dentro(control, marco):
            return {
                "se_ve": False,
                # ***«Quien lo tapa», no «no se ve»***: *es lo que permite arreglarlo.*
                "lo_que_lo_tapa": marco.get("nombre") or "un recorte",
                # ***Y la trampa que el contrato nombra***: mide bien y no se ve.
                "ancho_positivo_no_basta": control["ancho"] > 0,
            }
    return {"se_ve": True, "lo_que_lo_tapa": None, "ancho_positivo_no_basta": False}


def cabe_en_el_viewport(control: dict, *, viewport: dict, zoom: float = 1.0) -> dict:
    """***Y con el zoom puesto***, que es lo que el contrato pide medir: *«zoom real 200 %»*.

    ***Con zoom, todo el doble***: *el mismo control que cabe al 100% puede no caber al 200%, y eso hay que
    saberlo **antes** de que le pase a alguien que necesita el zoom para leer.*
    """
    if zoom <= 0:
        raise ValueError("el zoom tiene que ser mayor que cero")
    el_doble = {
        **control,
        "x": control["x"] * zoom,
        "y": control["y"] * zoom,
        "ancho": control["ancho"] * zoom,
        "alto": control["alto"] * zoom,
    }
    dentro = se_ve_entero(el_doble, recortes=[viewport])
    return {"se_ve_con_zoom": dentro["se_ve"], "zoom": zoom, "lo_que_lo_tapa": dentro["lo_que_lo_tapa"]}


def los_clics(*, pasos: list[str]) -> dict:
    """***«Contar clics y filas utiles, no solo px.»***

    ***Por que se cuentan***: *un recado que se hace en 3 clics y en 40 filas de scroll se hace; uno que
    necesita 12 clics y 300 filas **no se hace en el campo**, y la pantalla «funciona» igual.*

    ***Y se devuelven los pasos, no solo el numero***: *«12 clics» no se puede arreglar; «12 clics, y estos
    son» si.*
    """
    return {
        "clics": len(pasos),
        "los_pasos": list(pasos),
        # ***Un limite que se puede nombrar***: *a partir de aqui, el recado no se hace de pie en el campo.*
        "es_demasiado_largo": len(pasos) > 5,
    }


def las_filas(suyas: list, *, cuantas_utiles: int | None = None) -> dict:
    """***Cuantas filas hay que mirar, y cuantas sirven.***

    ***«Filas utiles» no es «filas»***: *una lista de 300 con 12 que sirven obliga a recorrer las 300 para
    encontrar las 12. **Y eso es lo que se mide**, no los pixeles.*
    """
    total = len(suyas)
    utiles = total if cuantas_utiles is None else int(cuantas_utiles)
    return {
        "filas": total,
        "utiles": utiles,
        # ***Y lo que de verdad cuesta***: *lo que hay que recorrer para llegar a lo que sirve.*
        "hay_que_recorrer": max(0, total - utiles),
    }


def el_limite_de_la_evidencia(*, hay_imagen: bool) -> dict:
    """***«Si solo hay DOM, marcar el limite.»***

    ***Y se dice, no se calla***: *una prueba que mira el DOM **no ha visto la pantalla**. Puede estar todo en
    su sitio y el color no contrastar, o el texto no caber. **Decir «se ve» cuando solo se ha mirado el DOM es
    la clase de afirmacion que el contrato no quiere.**
    """
    if hay_imagen:
        return {"evidencia": "imagen", "limite": None, "se_puede_decir_que_se_ve": True}
    return {
        "evidencia": "solo_dom",
        # ***El limite, dicho con sus palabras***.
        "limite": "esto dice donde esta cada cosa, no como se ve",
        "se_puede_decir_que_se_ve": False,
    }
