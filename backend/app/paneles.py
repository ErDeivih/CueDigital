"""**Los paneles: una metrica que dice de donde sale** (CRM-11, 17/10/2026).

El contrato de la cola lo pide con estas palabras:

    Contrato: ***valor nullable, unidad, periodo, finca/campana, filtros, cobertura, fuente y enlace***.
    ***Hectareas de trabajo acumulado distintas de superficie unica; kg distintos de EUR.***
    ***Sin cumplimiento global que tape una regla critica no comprobada.***

***Y aqui esta la idea entera***: un panel no es una pantalla con numeros, es **un numero que se puede
defender**. Cada metrica tiene que poder decir **que mide** -su unidad-, **de donde sale** -su fuente-, y
**cuanto de lo que habia ha mirado** -su cobertura-. *Un numero sin esas tres cosas no se enseña: se
esconde, y se dice por que.*

***Por que esto no es papeleo***: el 90% de los errores de un panel son los mismos tres -sumar peras con
manzanas, dar por bueno lo que no se ha comprobado, y enseñar un cero donde no hay dato-. Las tres se
cierran aqui, **antes** de que el numero llegue a una pantalla.
"""

from __future__ import annotations

from . import nutrientes, superficies

# ---------------------------------------------------------------------------
# Las magnitudes: ***lo que NO se puede sumar entre si***
# ---------------------------------------------------------------------------
#
# ***La regla, en una linea***: dos numeros solo se suman si miden **lo mismo**. El contrato lo dice con dos
# ejemplos que son los que se equivocan de verdad:
#
#   - ***hectareas de trabajo acumulado*** NO son ***superficie unica***: cinco labores en la misma parcela
#     son cinco veces su superficie en trabajo y **una sola** en superficie.
#   - ***kilos*** NO son ***euros***: se parecen en que los dos son numeros grandes, y ahi se acaba.

HECTAREAS_DE_TRABAJO = "ha_de_trabajo"          # lo que se ha pasado por encima de la tierra, sumando veces
HECTAREAS_DE_SUPERFICIE = "ha_de_superficie"    # la tierra que hay, contada una vez
# ***Y las que se trabajaron en tierras que NO son tuyas*** (CRM-11 con CRM-04, 17/10/2026).
#
# *Faltaba, y la falta se vio al querer enseñar las superficies en un panel*: *10 ha de un trabajo para un
# tercero **son hectareas de trabajo**, pero **no son tu finca** -lo dice `superficies.py` con esas palabras:
# «10 ha de un tercero no suman superficie propia»-. Si se apuntaran con `ha_de_trabajo`, `sumar` las juntaria
# con las tuyas **y la regla que existe para impedirlo quedaria saltada por arriba**.*
#
# *No es «superficie» ni es «trabajo tuyo»: **es su propia pregunta**, y por eso su propia magnitud.*
HECTAREAS_DE_TERCERO = "ha_de_tercero"          # lo que se trabajo en tierras de otro
KILOS = nutrientes.KILOS                        # lo que pesa
LITROS = nutrientes.LITROS                      # lo que cabe
EUROS = "EUR"                                   # lo que vale
HORAS = "h"                                     # lo que tarda

LAS_MAGNITUDES = (
    HECTAREAS_DE_TRABAJO,
    HECTAREAS_DE_SUPERFICIE,
    HECTAREAS_DE_TERCERO,
    KILOS,
    LITROS,
    EUROS,
    HORAS,
)

# ***Y las que se confunden***, escritas para que nadie tenga que deducirlo:
LAS_QUE_SE_CONFUNDEN = {
    HECTAREAS_DE_TRABAJO: HECTAREAS_DE_SUPERFICIE,
    # *Y estas dos, que se parecen en todo menos en lo que importa*: **las dos son trabajo y las dos se miden
    # en hectareas**, y una es tu finca y la otra no. *Es el mismo error que el de «superficie unica» y
    # «trabajo acumulado», un paso mas alla.*
    HECTAREAS_DE_TERCERO: HECTAREAS_DE_TRABAJO,
    KILOS: EUROS,
}


def se_pueden_sumar(una: str, otra: str) -> bool:
    """***Dos metricas se pueden sumar solo si miden lo mismo.***

    *Es la misma regla que `superficies.se_pueden_sumar`, y a proposito: **una sola** en todo el programa.*
    """
    return una == otra


# ---------------------------------------------------------------------------
# La metrica, que no se puede construir sin decir de donde sale
# ---------------------------------------------------------------------------


class MetricaSinOrigen(ValueError):
    """***Un numero que no puede decir de donde sale.*** *No se enseña: se esconde y se dice por que.*"""


def la_misma_cosa(una: dict, otra: dict) -> bool:
    """***Dos metricas se pueden sumar solo si miden LO MISMO***: la misma unidad **y** la misma pregunta.

    *`se_pueden_sumar` mira la unidad, que es la mitad. La otra mitad es la pregunta*: **«30 ha» de lo que hay
    plantado y «30 ha» de lo que se trato se miden en hectareas las dos**, y sumarlas da un numero que no
    contesta a nada. *Es el error que `superficies.py` persigue con cinco magnitudes, visto desde el panel.*
    """
    return se_pueden_sumar(una["unidad"], otra["unidad"]) and (una.get("pregunta") or "") == (
        otra.get("pregunta") or ""
    )


def la_metrica(
    *,
    clave: str,
    titulo: str,
    valor,
    magnitud: str,
    fuente: str,
    periodo: str,
    cobertura: dict | None = None,
    filtros: dict | None = None,
    pregunta: str | None = None,
    finca_id: int | None = None,
    campana_id: int | None = None,
    enlace: str | None = None,
) -> dict:
    """***Una metrica de panel, con todo lo que hace falta para poder creersela.***

    ***Y las cuatro cosas que NO deja hacer***:

    1. **Un numero sin unidad** -`magnitud` es obligatoria, y tiene que ser una de `LAS_MAGNITUDES`-.
       *«3.500» no es una metrica; «3.500 kg» si.*
    2. **Un numero sin fuente** -`fuente` es obligatoria-. ***De donde sale***: `cuaderno`, `facturas`,
       `sigpac`… *Un numero que no puede decir de donde sale no se puede discutir, y lo que no se puede
       discutir no se puede corregir.*
    3. **Un cero donde no hay dato** -si `valor` es `None`, la metrica sale **sin valor**, y la pantalla
       dice que no se sabe-. *Un cero y un «no lo se» son cosas distintas, y confundirlas es como se
       enseña un panel que miente.*
    4. **Una suma que no se puede hacer** -ver `sumar`-.

    `cobertura` dice **cuanto de lo que habia se ha mirado**: `{"contadas": 12, "de": 15}`. *Sin eso, un
    total parece completo aunque le falten tres pueblos.*
    """
    if magnitud not in LAS_MAGNITUDES:
        raise MetricaSinOrigen(
            f"«{magnitud}» no es una magnitud de las de aqui, asi que no se sabe con que se suma: "
            f"{', '.join(LAS_MAGNITUDES)}"
        )
    if not fuente:
        raise MetricaSinOrigen(
            f"la metrica «{clave}» no dice de donde sale. *Un numero que no puede decir su fuente no se "
            "puede discutir, y lo que no se puede discutir no se puede corregir.*"
        )
    return {
        "clave": clave,
        "titulo": titulo,
        # ***`None` es «no se sabe», y es un valor legitimo***: nunca se convierte en cero.
        "valor": valor,
        "unidad": magnitud,
        # ***Y LA PREGUNTA, que es lo otro que hay que saber*** (CRM-11 con CRM-06, 17/10/2026).
        #
        # *Hasta hoy `magnitud` hacia **dos trabajos a la vez**: decia **en que se mide** -y por eso dos
        # metricas con la misma `magnitud` se podian sumar- y, al mismo tiempo, **que mide**. Con las seis
        # magnitudes de antes eso cuadraba. **Con las superficies no**: dos metricas en hectareas pueden
        # contestar a preguntas distintas -lo que hay plantado y lo que se trato-, y sumarlas es el error
        # que `superficies.py` existe para impedir.*
        #
        # *Vacia es «no hace falta decirla»: las metricas de una sola pregunta -los euros, los kilos- no la
        # llevan, y las que la llevan **no se suman con las que no** salvo que coincida.*
        "pregunta": (pregunta or "").strip(),
        "fuente": fuente,
        "periodo": periodo,
        "cobertura": dict(cobertura or {}),
        "filtros": dict(filtros or {}),
        "finca_id": finca_id,
        "campana_id": campana_id,
        # ***El enlace a la lista***: cada tarjeta abre el detalle con los mismos filtros.
        "enlace": enlace,
    }


def sumar(*metricas: dict) -> dict:
    """***Suma lo que se puede sumar, y de lo que no, lo dice.***

    ***No falla: avisa.*** Un panel con dos metricas que no se pueden sumar **no es un error del programa**:
    es una pregunta mal hecha, y lo util es decir **cuales** no se han sumado.

    Devuelve la primera metrica con el total, mas `sin_sumar` -las claves que se han quedado fuera-.
    """
    if not metricas:
        raise MetricaSinOrigen("no hay ninguna metrica que sumar")
    primero = metricas[0]

    # ***Por `la_misma_cosa`, no solo por la unidad***: *dos metricas en hectareas con preguntas distintas no
    # se suman. Antes esta linea miraba solo `m["unidad"]`, y con las superficies eso dejaba pasar justo la
    # suma que hay que impedir.*
    sumables = [m for m in metricas if la_misma_cosa(m, primero)]
    sin_sumar = [m["clave"] for m in metricas if not la_misma_cosa(m, primero)]

    # ***Si alguna no tiene valor, el total NO se sabe***: *un total al que le falta un sumando no es un
    # total mas pequeño, es un total que no se sabe.*
    valores = [m["valor"] for m in sumables]
    total = None if any(v is None for v in valores) else sum(valores)

    return {
        **primero,
        "clave": " + ".join(m["clave"] for m in sumables),
        "valor": total,
        "cobertura": {
            "sumadas": len(sumables),
            "sin_sumar": sin_sumar,
        },
        "sin_sumar": sin_sumar,
    }


def lo_que_no_se_ha_comprobado(metricas: list[dict]) -> list[dict]:
    """***Las metricas que no se pueden dar por buenas.***

    El contrato: *«sin cumplimiento global que tape una regla critica no comprobada»*. *Traducido: si hay
    algo que no se ha podido comprobar, el panel **lo dice**, aunque el total salga bien.* Un panel que
    enseña un total verde con una regla sin comprobar debajo es peor que uno que no enseña nada.
    """
    return [m for m in metricas if m.get("valor") is None or not m.get("fuente")]


def lo_de_una_superficie(ha_de_superficie, *, hectarea_de_trabajo=None, fuente: str, periodo: str, **resto):
    """***Dos metricas hermanas, y separadas a proposito***: la tierra que hay y lo que se ha trabajado.

    ***Es el caso 207 del contrato***: *cinco labores en la misma parcela son cinco veces su superficie en
    **trabajo** y **una sola** en **superficie**.* Ponerlas juntas en un panel esta bien; **sumarlas, no**.
    """
    comun = {"fuente": fuente, "periodo": periodo, **resto}
    return (
        la_metrica(
            clave="superficie",
            titulo="Superficie de la finca",
            valor=superficies.suma_lo_mismo(magnitud="superficie", valores=[ha_de_superficie]),
            magnitud=HECTAREAS_DE_SUPERFICIE,
            **comun,
        ),
        la_metrica(
            clave="trabajo",
            titulo="Trabajo acumulado",
            valor=hectarea_de_trabajo,
            magnitud=HECTAREAS_DE_TRABAJO,
            **comun,
        ),
    )
