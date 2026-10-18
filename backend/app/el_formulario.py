"""**Como se monta un formulario, y las cuatro cosas que el contrato exige** (contrato comun, 17/10/2026).

El contrato comun de la cola lo dice asi:

    Formulario: ***agrupacion por tarea***, ***original al lado cuando hay documento***, borrador conservado,
    ***errores junto a datos***, ***estado de guardado/reenvio***, confirmacion clara.

***Y las cuatro son la misma idea que los cinco estados***: **el formulario no deja al agricultor adivinando**.
*Ni de que va cada campo -van agrupados por lo que se esta haciendo-, ni si lo que escribio se guardo, ni
donde esta el error -al lado del campo, no en un aviso arriba-, ni que dice el papel que tiene en la mano.*

***Por que esto es un modulo***: **un error en un aviso de arriba obliga a buscar cual de los catorce campos
es**. *Y con el original al lado no hay que memorizar: se compara.*
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# ***«Agrupacion por tarea»***
# ---------------------------------------------------------------------------
#
# ***No por tipo de dato*** -que es lo facil-: *«fecha, numero, importe»* no dice nada de lo que se esta
# haciendo; *«¿que has comprado? / ¿cuanto? / ¿cuando?»* si.

TAREA = "tarea"


def agrupar_por_tarea(campos: list[dict], *, orden_de_las_tareas: list[str] | None = None) -> list[dict]:
    """***Los campos agrupados por lo que el agricultor esta haciendo***, no por como son.

    ***Y los campos que no dicen su tarea no se pierden***: van a un grupo aparte **que se ve**, no se
    esconden. *Un campo que no sale es un campo que no se rellena.*
    """
    grupos: dict[str, list] = {}
    for campo in campos:
        suya = str(campo.get(TAREA) or "").strip() or "Otros datos"
        grupos.setdefault(suya, []).append(campo)

    orden = list(orden_de_las_tareas or [])
    # ***Las tareas que se piden primero, en su orden; y las demas al final, en el suyo.***
    nombres = [t for t in orden if t in grupos] + [t for t in grupos if t not in orden]
    return [{"tarea": nombre, "campos": grupos[nombre]} for nombre in nombres]


# ---------------------------------------------------------------------------
# ***«Errores junto a datos»***
# ---------------------------------------------------------------------------


def poner_los_errores_junto_a_los_datos(campos: list[dict], errores: dict) -> list[dict]:
    """***Cada error, pegado al campo que lo tiene.***

    ***Y por que no un aviso arriba***: *«hay 3 errores» obliga a buscar **cuales** de los catorce campos son.
    Al lado del campo, se corrige sin buscar.*

    ***Y los errores de campos que no estan se dicen aparte*** -`sueltos`-, en vez de perderse: *un error que
    no se enseña es un formulario que no se puede enviar y no dice por que.*
    """
    por_campo = {k: v for k, v in (errores or {}).items()}
    puestos = []
    vistos = set()
    for campo in campos:
        nombre = campo.get("nombre")
        if nombre in por_campo:
            puestos.append({**campo, "error": por_campo[nombre]})
            vistos.add(nombre)
        else:
            puestos.append({**campo, "error": None})
    sueltos = {k: v for k, v in por_campo.items() if k not in vistos}
    return {"campos": puestos, "sueltos": sueltos, "se_puede_enviar": not por_campo}


# ---------------------------------------------------------------------------
# ***«Estado de guardado/reenvio»***
# ---------------------------------------------------------------------------

SIN_CAMBIOS = "sin_cambios"
CAMBIOS_SIN_GUARDAR = "cambios_sin_guardar"
GUARDANDO = "guardando"
GUARDADO = "guardado"
FALLO = "fallo"
EN_LA_COLA = "en_la_cola"


def el_estado_de_guardado(*, hay_cambios: bool, guardando: bool = False, guardado: bool = False, fallo=None, en_la_cola: bool = False) -> dict:
    """***En que punto va lo que el agricultor ha escrito.***

    ***Y las seis se distinguen a proposito***: *«guardado» y «en la cola» **no son lo mismo** -en la cola
    significa que **aun no ha llegado**-, y confundirlas es lo que hace que alguien cierre la aplicacion
    creyendo que su trabajo esta a salvo.*

    *Y `hay_cambios` manda*: si no hay cambios, no hay nada que guardar, aunque el ultimo intento fallara.
    """
    if guardando:
        return {"estado": GUARDANDO, "texto": "Guardando…", "tranquilo": False}
    if fallo:
        return {
            "estado": FALLO,
            "texto": "No se ha podido guardar",
            "detalle": str(fallo),
            # ***Y se dice que NO se ha perdido***: es lo primero que piensa el agricultor.
            "lo_que_habia": "sigue aqui",
            "tranquilo": False,
        }
    if en_la_cola:
        return {
            "estado": EN_LA_COLA,
            "texto": "Se mandara cuando haya cobertura",
            "tranquilo": False,  # ***aun no ha llegado***: no se puede decir «guardado»
        }
    if hay_cambios:
        return {"estado": CAMBIOS_SIN_GUARDAR, "texto": "Sin guardar", "tranquilo": False}
    if guardado:
        return {"estado": GUARDADO, "texto": "Guardado", "tranquilo": True}
    return {"estado": SIN_CAMBIOS, "texto": "", "tranquilo": True}


# ---------------------------------------------------------------------------
# ***«Original al lado cuando hay documento»***
# ---------------------------------------------------------------------------


def el_original_al_lado(*, lo_leido: dict, el_original: str | None) -> dict:
    """***El papel, al lado de lo que se ha entendido de el.***

    ***Para que se pueda comparar sin memorizar***: *quien confirma una factura esta mirando la foto y el
    formulario a la vez; si el original esta en otra pantalla, se compara de memoria, y de memoria se
    confirman cosas que no son.*

    ***Y cuando no hay original, se dice***: *un formulario sin papel al lado no puede pretender que se
    compruebe nada.*
    """
    if not el_original:
        return {
            "hay_original": False,
            "campos": lo_leido,
            "que_hacer": "Sin el papel a la vista, revisa los datos antes de guardar",
        }
    return {"hay_original": True, "campos": lo_leido, "original": el_original, "al_lado": True}
