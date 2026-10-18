"""**Lo que cada uno puede cambiar de su pantalla** (CRM-11, 17/10/2026).

El contrato de la cola lo pide asi:

    Preferencias por usuario: orden de tarjetas, vistas/columnas/filtros guardados, pantalla inicial,
    restablecer vista; ***no personalizar limites legales ni alterar datos compartidos***.

***Y esas dos mitades son la misma frase***: se puede cambiar **como se mira**, y **no** se puede cambiar
**lo que hay**. *Es la diferencia entre mover los muebles de casa y mover las paredes: una la hace cualquiera
y la otra tira el edificio.*

***Por que esto no es una pantalla, es una regla***: si el «orden de tarjetas» pudiera meter un limite legal,
o una «vista guardada» pudiera cambiar un dato compartido, **cada agricultor veria una ley distinta**. *Lo
que se guarda aqui es **la vista**, y lo que se ve sigue saliendo del servidor.*
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Lo que SI se puede guardar
# ---------------------------------------------------------------------------

ORDEN_DE_TARJETAS = "orden_de_tarjetas"
COLUMNAS = "columnas"
FILTROS = "filtros"
PANTALLA_INICIAL = "pantalla_inicial"

LO_QUE_SE_PUEDE_GUARDAR = (ORDEN_DE_TARJETAS, COLUMNAS, FILTROS, PANTALLA_INICIAL)

# ***Y lo que NO, dicho con nombres***: no es una lista de campos prohibidos -que se quedaria corta-, es
# **la clase de cosa** que no se toca. *Un limite legal y un dato compartido no se personalizan, se miren
# como se miren.*
NO_SE_PERSONALIZA = (
    "limite_legal",
    "limites_legales",
    "plazo",
    "plazos",
    "dosis_maxima",
    "superficie_declarada",
    "datos_compartidos",
    "datos_de_la_finca",
)


class PreferenciaQueNoSeToca(ValueError):
    """***Alguien ha intentado personalizar lo que no se personaliza.*** *Se para y se dice cual.*"""


def se_puede_guardar(cual: str) -> bool:
    """***Si esa preferencia es de las que se pueden guardar.***"""
    return cual in LO_QUE_SE_PUEDE_GUARDAR


def _lo_que_no_se_toca(cual: str) -> str | None:
    """***Si el nombre de una preferencia huele a algo que no se toca.***

    *Y se mira por el **nombre** a proposito*: una lista de campos exactos se queda corta en cuanto alguien
    añade `plazo_de_seguridad` con otro nombre, y esto tiene que seguir parando.
    """
    minusculas = str(cual).lower()
    for prohibido in NO_SE_PERSONALIZA:
        if prohibido in minusculas:
            return prohibido
    return None


def guardar_la_preferencia(cual: str, valor, *, las_de_antes: dict | None = None) -> dict:
    """***Guarda una preferencia, si es de las que se pueden guardar.***

    ***Y no toca nada mas***: devuelve las preferencias **de antes con esta cambiada**, que es lo que hace
    que una preferencia no pueda llevarse por delante a las demas. *Lo que no se ha tocado, no se toca.*
    """
    guardadas = dict(las_de_antes or {})

    if not se_puede_guardar(cual):
        sospechoso = _lo_que_no_se_toca(cual)
        if sospechoso:
            raise PreferenciaQueNoSeToca(
                f"«{cual}» no se personaliza: toca «{sospechoso}», y un limite legal o un dato compartido "
                "no se cambia desde la pantalla de uno. *Se puede cambiar como se mira, no lo que hay.*"
            )
        raise PreferenciaQueNoSeToca(
            f"«{cual}» no es una preferencia de las de aqui: {', '.join(LO_QUE_SE_PUEDE_GUARDAR)}"
        )

    guardadas[cual] = valor
    return guardadas


def el_orden_de_las_tarjetas(orden, *, todas: list[str]) -> list[str]:
    """***Aplica el orden que ha elegido el agricultor, sin perder ninguna tarjeta por el camino.***

    ***Las tres cosas que puede pasar, y las tres se resuelven***:

      - una tarjeta **del orden** que ya no existe -> se ignora
      - una tarjeta **nueva** que no estaba en el orden -> ***se añade al final***, no se esconde
      - y si el orden viene vacio o roto -> se devuelven **todas**, en el suyo

    *Lo ultimo importa mas de lo que parece*: una preferencia guardada hace meses no puede hacer que una
    tarjeta nueva **no salga nunca**. *Esconder un dato por una preferencia vieja es la peor forma de
    perderlo: sin que nadie lo note.*
    """
    if not isinstance(orden, (list, tuple)):
        return list(todas)
    puestas = [c for c in orden if c in todas]
    # Y las que no estaban en el orden: al final, en el suyo. ***Ninguna se pierde.***
    return puestas + [c for c in todas if c not in puestas]


def restablecer(las_de_antes: dict | None) -> dict:
    """***«Restablecer vista»***: se olvida **todo** lo de la vista y se vuelve a lo de fabrica.

    *Y solo la vista: restablecer no puede tocar ni un dato.*
    """
    return {}
