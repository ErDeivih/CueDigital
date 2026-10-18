"""**Las superficies, y por que NO se suman entre si** (CRM-06, 17/10/2026).

Los criterios de la revision, literales:

    ...**superficie realmente tratada** en un trabajo. **No sobreescribir una con otra ni sumarlas como si
    fueran la misma magnitud.** Dosis kg/ha usa la **superficie tratada de ese hecho**; planificacion PAC
    usa **el recinto y superficie declarados de la campana**. Para grupos: **asignaciones por tierra,
    unidad, fuente y suma; desconocido no es cero.** No imponer relaciones rigidas entre geometrias sin
    revisar el caso de uso.

Y el caso de aceptacion del COLA, tambien literal:

    **trabajo externo 10 ha no suma superficie propia**

--------------------------------------------------------------------------------------------------
***POR QUE HACE FALTA ESTE MODULO, SI EL MODELO YA LAS SEPARA***
--------------------------------------------------------------------------------------------------

Porque separarlas en la base **no impide sumarlas en una cuenta**, y esa cuenta es de las que se hacen sin
pensar: *«¿cuantas hectareas llevo?»* y se suma todo lo que tenga `_ha` en el nombre.

**La casa ya hizo la mitad del trabajo**: `Tratamiento.superficie_tratada_ha` es **la tratada de ese hecho**
y `Parcela.superficie_ha` es **lo que se cultiva**; el trabajo de un tercero vive en **su propia tabla**
-`trabajos_para_terceros`- y el comentario del modelo lo dice: *«10 ha de un tercero no suman superficie
propia… meterlas [en `parcelas`] seria decir que son del agricultor»*.

Lo que faltaba era **una cuenta que se niegue a mezclarlas**, y aqui esta.

***Y LA REGLA DE SIEMPRE, APLICADA A LAS HECTAREAS***: *un dato que no consta no es un cero*. Sumar
saltandose la parcela que no tiene superficie da un total **mas pequeno que el de verdad**, y en una
declaracion eso no es un redondeo: es una cifra falsa. Aqui, si falta un sumando, **el total es `None`** y se
dice **cual** falta.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------- las magnitudes
#
# ***Cada una contesta a una pregunta distinta.*** El error clasico es sumarlas porque las tres se miden en
# hectareas, y las hectareas no son la magnitud: **la pregunta** es la magnitud.
LO_QUE_SE_CULTIVA = "lo_que_se_cultiva"
LO_QUE_DICE_EL_SIGPAC = "lo_que_dice_el_sigpac"
LO_TRATADO_DE_UN_HECHO = "lo_tratado_de_un_hecho"
LO_DE_UN_TERCERO = "lo_de_un_tercero"
LO_DECLARADO_EN_LA_PAC = "lo_declarado_en_la_pac"

LAS_MAGNITUDES = (
    LO_QUE_SE_CULTIVA,
    LO_QUE_DICE_EL_SIGPAC,
    LO_TRATADO_DE_UN_HECHO,
    LO_DE_UN_TERCERO,
    LO_DECLARADO_EN_LA_PAC,
)

# Y que pregunta contesta cada una, para poder decirlo en un mensaje de error.
LA_PREGUNTA = {
    LO_QUE_SE_CULTIVA: "que hay plantado en la finca",
    LO_QUE_DICE_EL_SIGPAC: "que reconoce el SIGPAC de esos recintos",
    LO_TRATADO_DE_UN_HECHO: "que se trato de verdad ese dia",
    LO_DE_UN_TERCERO: "que se hizo en tierras que no son tuyas",
    LO_DECLARADO_EN_LA_PAC: "que se declaro en la solicitud de la campana",
}

# ***Las que MAS se confunden***, para poder explicar el error con un ejemplo.
#
# ***Ojo: esto NO decide nada.*** La regla que decide es una igualdad -`se_pueden_sumar`-, porque una lista
# de pares **nunca esta completa** y la primera version, con la logica al reves, dejaba pasar
# `sigpac` + `se_cultiva`. Esta lista es **documentacion de las que se confunden**, y el primer par que
# entra en ella es el que avisa el propio modelo: `superficie_sigpac_ha` **no es** la que se cultiva.
LAS_QUE_SE_CONFUNDEN = (
    (LO_QUE_DICE_EL_SIGPAC, LO_QUE_SE_CULTIVA),
    (LO_QUE_SE_CULTIVA, LO_TRATADO_DE_UN_HECHO),
    (LO_QUE_SE_CULTIVA, LO_DE_UN_TERCERO),
    (LO_DECLARADO_EN_LA_PAC, LO_QUE_SE_CULTIVA),
    (LO_DE_UN_TERCERO, LO_QUE_DICE_EL_SIGPAC),
    (LO_DECLARADO_EN_LA_PAC, LO_TRATADO_DE_UN_HECHO),
)

NO_ES_UNA_MAGNITUD = "esa_no_es_una_de_las_magnitudes"
ESAS_DOS_NO_SE_SUMAN = "esas_dos_superficies_no_son_la_misma_cosa"
FALTA_UNA_SUPERFICIE = "falta_la_superficie_de_alguno"


def _como_numero(valor: Any) -> float | None:
    """Un numero, o `None` si no consta. **Un cero no es «no consta»**, y se respeta."""
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def se_pueden_sumar(una: str, otra: str) -> bool:
    """***Si dos magnitudes se pueden sumar***: **solo si son la misma**.

    Se suman dos trozos de la misma magnitud -dos parcelas para saber lo que se cultiva, dos tratamientos
    para saber lo tratado-. **En cuanto cambia la pregunta, no**, y da igual cuales sean: por eso esto es
    una igualdad y no una lista de pares prohibidos.

    ***La lista de pares se probo y se quito*** (17/10/2026): era una lista que **nunca esta completa**, y
    con la logica al reves dejaba pasar justo el caso que el modelo avisa -`superficie_sigpac_ha` **no es**
    la que se cultiva y *«no se copia nunca sola»*-. Lo cazo su prueba.
    """
    return una == otra


def suma_lo_mismo(*, magnitud: str, valores: Iterable[Any]) -> dict[str, Any]:
    """***Suma solo lo que es la misma magnitud***, y dice lo que falta en vez de inventarlo.

    Devuelve:

      * `total`: la suma, o **`None`** si **algun** sumando no consta. ***Un total al que le falta un trozo
        no es el total***: en una declaracion eso es una cifra falsa, no un redondeo.
      * `sumandos`: cuantos entraron.
      * `sin_superficie`: **cuantos no constan** -lo que hay que ir a mirar-.
      * `lo_que_falta`: el motivo, si falta algo.
    """
    if magnitud not in LAS_MAGNITUDES:
        return {
            "total": None,
            "sumandos": 0,
            "sin_superficie": 0,
            "lo_que_falta": [NO_ES_UNA_MAGNITUD],
        }

    numeros = [_como_numero(uno) for uno in valores]
    faltan = sum(1 for uno in numeros if uno is None)
    if faltan:
        return {
            "total": None,
            "sumandos": len(numeros) - faltan,
            "sin_superficie": faltan,
            "lo_que_falta": [FALTA_UNA_SUPERFICIE],
        }
    return {
        "total": round(sum(numeros), 4),
        "sumandos": len(numeros),
        "sin_superficie": 0,
        "lo_que_falta": [],
    }


def la_superficie_de_la_finca(parcelas: Sequence[Mapping[str, Any]] | Iterable[Any]) -> dict[str, Any]:
    """***Lo que se cultiva, y SOLO lo propio.***

    ***Es la funcion del caso de aceptacion.*** Los trabajos hechos en tierras de un tercero **no entran
    aqui**, aunque sean hectareas y aunque se hayan hecho con tu tractor: **no son tu superficie**, y
    sumarlas diria que tu finca es mas grande de lo que es -y eso se declara-.

    Un trabajo de un tercero se pasa por `lo_de_un_tercero`, que es **otra pregunta**.
    """
    def de_una(parcela: Any) -> Any:
        if isinstance(parcela, Mapping):
            return parcela.get("superficie_ha")
        return getattr(parcela, "superficie_ha", None)

    return suma_lo_mismo(magnitud=LO_QUE_SE_CULTIVA, valores=[de_una(una) for una in parcelas])


def lo_de_un_tercero(trabajos: Sequence[Mapping[str, Any]] | Iterable[Any]) -> dict[str, Any]:
    """***La superficie de los trabajos hechos para otros***, que es **otra pregunta**.

    Vive aqui y **no** en `parcelas` -lo dice el modelo-, y esta funcion existe para que se pueda decir
    *«hice 10 ha para un tercero»* **sin** que esas 10 ha entren en la finca.
    """
    def de_uno(trabajo: Any) -> Any:
        if isinstance(trabajo, Mapping):
            return trabajo.get("superficie_ha")
        return getattr(trabajo, "superficie_ha", None)

    return suma_lo_mismo(magnitud=LO_DE_UN_TERCERO, valores=[de_uno(uno) for uno in trabajos])


def lo_tratado(tratamientos: Sequence[Mapping[str, Any]] | Iterable[Any]) -> dict[str, Any]:
    """***Lo que se trato de verdad***, que sale de **cada hecho** y no de la ficha de la tierra.

    Usa `superficie_tratada_ha` -la del hecho- porque es lo que pide el criterio para la dosis: *«dosis kg/ha
    usa la **superficie tratada de ese hecho**»*. Si un tratamiento se hizo en media parcela, aqui entra
    media.
    """
    def de_uno(tratamiento: Any) -> Any:
        if isinstance(tratamiento, Mapping):
            return tratamiento.get("superficie_tratada_ha")
        return getattr(tratamiento, "superficie_tratada_ha", None)

    return suma_lo_mismo(
        magnitud=LO_TRATADO_DE_UN_HECHO, valores=[de_uno(uno) for uno in tratamientos]
    )


def la_dosis_por_hectarea(*, cantidad: float | None, superficie_tratada_ha: float | None) -> float | None:
    """***La dosis, con la superficie tratada de ESE hecho.***

    Y si la superficie no consta, **`None`**: una dosis con la superficie de la parcela entera -cuando se
    trato media- seria el doble de la de verdad.
    """
    cantidad_numero = _como_numero(cantidad)
    superficie = _como_numero(superficie_tratada_ha)
    if cantidad_numero is None or superficie is None or superficie <= 0:
        return None
    return round(cantidad_numero / superficie, 4)

def la_superficie_de_un_grupo(grupo: Any) -> float | None:
    """***La suma de las tierras de un grupo, o `None` si a alguna le falta la superficie.***

    ***Vive aqui para que haya UNA cuenta y no dos copias.*** Estaba escrita dos veces -en
    `servicios.superficie_contada_del_grupo` y en `validaciones._superficie_del_grupo`-, **letra por
    letra la misma**, y dos copias de una regla son dos sitios donde puede dejar de cumplirse.

    Y esa regla es la de esta casa: ***una suma a la que le falta un numero NO es una suma***. Devolver la
    de las demas daria un total que parece bueno, y con el se decide si un apunte cupo dentro del grupo.
    Por eso, si **alguna** tierra no trae su superficie, el total es `None` -y quien llama avisa, en vez de
    ensenar un numero que no es-.
    """
    if grupo is None:
        return None
    parcelas = getattr(grupo, "parcelas", None) or []
    if not parcelas:
        return None
    suyo = suma_lo_mismo(
        magnitud=LO_QUE_SE_CULTIVA,
        valores=[getattr(parcela, "superficie_ha", None) for parcela in parcelas],
    )
    return suyo["total"]
