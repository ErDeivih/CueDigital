"""**La tabla y la ficha, con las reglas del contrato comun** (17/10/2026).

El contrato comun de la cola lo dice asi, en dos lineas:

    227  Finca/campaña visibles, busqueda, navegacion coherente y ***ficha unica por entidad***.
    228  Tabla de escritorio: busqueda, filtros activos, orden, columnas, pie X de Y y ***seleccion
         explicita***; ***acciones contextuales*** y exportacion que declare si incluye filtrados o todos.

***Y las tres ideas que hay aqui dentro son las tres que se hacen mal sin querer***:

  - ***la seleccion explicita***: *lo marcado tiene que **verse** y **sobrevivir al repintado**; si se pierde
    al ordenar, el agricultor marca doce cosas y hace la accion sobre tres sin enterarse.*
  - ***las acciones contextuales***: *las que aplican **a lo que hay delante**, y apagadas -no escondidas-
    cuando no aplican. Una accion que no se puede hacer y no esta, se busca; una que esta apagada, se
    entiende.*
  - ***la ficha unica***: *una parcela **es una**, y se entra por donde se entre. Con dos fichas, la mitad de
    lo que se sabe de una tierra no sale en la otra.*
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# ***La seleccion explicita***
# ---------------------------------------------------------------------------


def la_seleccion(marcados, *, de_los_que_hay: list, lo_de_antes=None) -> dict:
    """***Lo marcado, dicho y conservado.***

    ***Las tres cosas que hace, y las tres importan***:

    1. **Solo cuenta lo que sigue estando**: *si algo se ha borrado o ya no esta en la lista, no puede seguir
       contando como marcado -la accion se haria sobre algo que no existe-.*
    2. **Lo de antes se respeta**: si ya habia algo marcado y no se dice nada, **no se desmarca**. *Es el
       error que mas duele: ordenar por otra columna y perder la seleccion.*
    3. **Y se dice cuantos hay**: `cuantos`. *«Accion sobre 0 elementos» es peor que no ofrecer la accion.*
    """
    hay = list(de_los_que_hay or [])
    if marcados is None:
        marcados = lo_de_antes if lo_de_antes is not None else []
    dentro = [x for x in marcados if x in hay]
    return {
        "marcados": dentro,
        "cuantos": len(dentro),
        "hay_seleccion": bool(dentro),
        # ***Y lo que ya no esta, se dice***: *no se pierde en silencio.*
        "ya_no_estan": [x for x in (marcados or []) if x not in hay],
    }


# ---------------------------------------------------------------------------
# ***Las acciones contextuales***
# ---------------------------------------------------------------------------


def las_acciones_que_aplican(acciones: list[dict], *, cuantos_marcados: int) -> list[dict]:
    """***Que se puede hacer con lo que hay delante***, y cual esta apagada y por que.

    ***«Apagada, no escondida»***: *una accion que no se puede hacer y **no esta**, se busca; una que **esta
    apagada**, se entiende.* **Y la que exige seleccion y no la hay, se apaga con su motivo** -no
    desaparece, que es lo que hace pensar que la pantalla se ha roto-.
    """
    fuera = []
    for accion in acciones:
        cuantos = int(accion.get("cuantos") or 0)
        if cuantos == 0:
            fuera.append({**accion, "activa": True, "motivo": None})
        elif cuantos_marcados >= cuantos:
            fuera.append({**accion, "activa": True, "motivo": None})
        elif cuantos == 1:
            fuera.append(
                {
                    **accion,
                    "activa": False,
                    # ***Y se dice por que***: *«elige uno» es una instruccion; «no se puede» es un muro.*
                    "motivo": "Elige uno de la lista",
                }
            )
        else:
            fuera.append(
                {
                    **accion,
                    "activa": False,
                    "motivo": f"Elige al menos {cuantos} de la lista",
                }
            )
    return fuera


# ---------------------------------------------------------------------------
# ***La ficha unica***
# ---------------------------------------------------------------------------

LAS_QUE_ABREN_UNA_FICHA = ("tierra", "maquina", "contacto", "trabajo", "factura", "documento")


def la_ficha_unica(*, tipo: str, de_donde_viene: str) -> dict:
    """***Una entidad, una ficha, y se entra por donde se entre.***

    ***Por que no vale una ficha por pantalla***: *si la parcela tiene una ficha en «Tierras» y otra distinta
    en «Cuaderno», la mitad de lo que se sabe de esa tierra **no sale** en la otra -y el agricultor cree que
    el programa no lo sabe-.*

    Devuelve **la clave de la ficha**, que es la misma venga de donde venga: `tipo#id`.
    """
    if tipo not in LAS_QUE_ABREN_UNA_FICHA:
        raise ValueError(
            f"«{tipo}» no es una de las entidades con ficha: {', '.join(LAS_QUE_ABREN_UNA_FICHA)}. "
            "*Una entidad sin ficha propia se mira dentro de la de al lado.*"
        )
    return {"tipo": tipo, "de_donde_viene": de_donde_viene, "la_ficha": f"{tipo}#{{id}}"}


def la_misma_ficha(*, una: dict, otra: dict) -> bool:
    """***Si las dos formas de llegar llevan a la misma ficha.***

    *Es la comprobacion que se hace en la pantalla: dos enlaces a la misma tierra tienen que abrir **lo
    mismo**; si no, hay dos fichas y una de las dos se queda vieja.*
    """
    return (una.get("tipo"), una.get("id")) == (otra.get("tipo"), otra.get("id"))


# ---------------------------------------------------------------------------
# ***«Finca/campaña visibles»***
# ---------------------------------------------------------------------------


def la_finca_y_la_campana(*, finca, campana, campanas: list | None = None) -> dict:
    """***Que se vea siempre en que finca y en que año se esta trabajando.***

    ***Y en el campo no es un adorno***: *con dos fincas y tres años abiertos, apuntar en el año que no es
    mete el trabajo donde no va, y eso **no se ve** hasta que se buscan las cuentas.*

    *Si no hay campaña elegida, se dice -no se pone la de hoy por defecto-: **elegir por el agricultor es una
    cosa, y elegirlo el programa, otra**.*
    """
    return {
        "finca": finca,
        "campana": campana,
        "se_ve": bool(finca) and bool(campana),
        "hay_que_elegir_campana": not campana,
        "campanas": list(campanas or []),
    }
