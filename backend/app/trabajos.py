"""Los trabajos por tierra: lo previsto, lo hecho, el historial y el estado (T15, 05/10/2026).

## Qué hay aquí, y por qué está aquí y no en un router

Este fichero es **la lógica pura** del T15: se le pasan listas de hechos y de trabajos previstos, y
devuelve lo que se puede decir de ellos. Ni base de datos, ni navegador, ni FastAPI. El motivo no es
estético: **las reglas del encargo se pueden probar hoy**, antes de que existan las tablas nuevas, y una
regla del negocio que solo vive dentro de una ruta se prueba con un servidor levantado y una base de
datos, o no se prueba.

Las cuatro reglas que este fichero existe para no dejar romper son las que el encargo nombra:

  1. **Un trabajo previsto no consume existencias ni acredita trabajo hecho.** Se ve en
     `acredita_un_trabajo_hecho` y en `consume_existencias`: lo que no está hecho **no gasta**, y un
     trabajo del que **no consta** si se hizo tampoco (no se supone que sí, ni que no).
  2. **Un rodillo después de sembrar no borra el estado de siembra.** El cultivo que se enseña sale de
     la última siembra o plantación que cuenta, y **de nada más** (`cambia_el_cultivo`). Ni una labor
     de suelo, ni una cosecha, ni una lluvia cambian lo sembrado.
  3. **Una lluvia no acredita nascencia ni salud del cultivo.** La nascencia solo sale de una
     observación de alguien que la haya visto. Que una estación diga que llovió no dice nada de la
     planta, y aquí se dice por qué con su código de frase.
  4. **Anular y corregir no duplican consumos.** Un trabajo anulado deja de contar —y sus salidas del
     almacén con él— y una corrección **anula la salida vieja y apunta la nueva**: nunca quedan dos
     vivas, y nunca se reescribe por detrás la cantidad de un movimiento que alguien apuntó.

## Las tres decisiones que sostienen todo lo demás

### 1. «No consta» es un estado, y es distinto de «no»

`estado` de un trabajo vale `previsto`, `en_curso`, `realizado`, `cancelado`… **y `None`**, que quiere
decir «no consta». Lo ausente **no se rellena**: un trabajo sin estado declarado no acredita trabajo
hecho, no gasta existencias y sale en la lista de lo que no se sabe.

Esto es exactamente lo que hay que evitar: una columna `estado` en la tabla de labores con el valor por
defecto «previsto» convertiría en **planificado** todo el cuaderno que el agricultor ya tiene apuntado
—que son hechos: los apuntó pulsando «HE SEMBRADO»—. Por eso lo previsto vive en **su propia tabla**
(ver `docs/T15_TRABAJOS.md`) y quien la lee pasa `estado` con lo que allí conste.

Y al revés: quien lee la tabla de labores pasa `estado="realizado"` (para eso está `un_hecho`), porque
**una fila de ahí es un hecho**: no hay ninguna forma de apuntar en ella algo que no ha pasado. Ese es
el único sitio del programa donde «realizado» se puede afirmar sin que nadie lo haya escrito, y está
dicho aquí, en `un_hecho`, con su motivo.

### 2. Lo previsto y lo hecho se emparejan **solo** cuando alguien lo dice

Un trabajo previsto no se marca como hecho por parecerse a un hecho. Se empareja por **el vínculo
explícito** (`previsto_id`), que es lo que el agricultor dice al pulsar «esto es lo que se hizo». Lo
demás —misma tierra, mismo tipo, fechas cercanas— es adivinar, y una adivinación aquí diría que un
trabajo está hecho cuando no lo está. Eso es el caso A05 del contrato: un plan de siembra confirmado
como plan **no añade una labor realizada ni consume semillas**.

### 3. Las cifras salen de un solo sitio

`cifras_de_una_tierra` es **la única** cuenta de hectáreas, horas e insumos de una tierra, y el
historial y el estado la llevan dentro tal cual. Hay una prueba que lo exige («el historial y el estado
sacan las mismas cifras»): si alguien vuelve a sumar por su cuenta en otra parte, esa prueba se pone
roja. Es la regla del encargo —«el cuaderno y los paneles usan los mismos hechos»— escrita como un solo
camino.

## Y lo que este módulo **no** hace

- **No mira el reloj.** `hoy` se pasa. Sin día de hoy no se cuentan los días que faltan, y se dice.
- **No escribe en ninguna tabla.** Devuelve lo que habría que escribir, y quien escribe es el router y
  por las puertas que ya existen (la salida del almacén es `almacen_api.sacar_de_un_lote`: no hay una
  segunda forma de descontar).
- **No devuelve frases para el agricultor: devuelve códigos.** Los textos viven en `app/textos.py`, que
  es compartido, y aquí no se escribe ni una frase que vea el agricultor. Los códigos que este módulo
  puede devolver están todos en `CODIGOS_QUE_SE_DICEN`, con la frase que hay que poner en
  `textos.MENSAJES` (el informe del ticket las lleva enteras).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable, Mapping, Sequence

from . import textos

# --------------------------------------------------------------------------
# Lo que es un trabajo
# --------------------------------------------------------------------------

# Los cuatro estados del contrato (§4, S04): «Estados: previsto, en curso, realizado, cancelado;
# anulado pertenece a hechos registrados». Por eso `anulado` **no** está en esta lista: es una columna
# aparte, y un apunte anulado sigue siendo un hecho que existió.
ESTADOS_DE_UN_TRABAJO = ("previsto", "en_curso", "realizado", "cancelado")

# Los que **no** son un trabajo de la tierra, aunque sean hechos del cuaderno y salgan en el historial.
# La lluvia es el caso: es un hecho y sale en el historial de la tierra, y no es algo que el agricultor
# haya hecho. T17 es el ticket que traerá la fuente de la lluvia; aquí está el hecho, para poder decir
# con pruebas que **de una lluvia no se deduce nada del cultivo**.
HECHOS_DEL_TIEMPO = ("lluvia",)

# Las labores de suelo del contrato (§4, S05, paso 1: «laboreo + rodillo/cultivador/arado/otro»).
# **Ninguna de ellas cambia lo que hay sembrado**, y esa es la mitad del caso A04. `otro` es «una labor
# de suelo que no sé nombrar», y tampoco cambia nada: no saber qué apero era no es saber que sembró.
SUBTIPOS_DE_LABOREO = ("rodillo", "cultivador", "arado", "grada", "fresadora", "otro")

# Los tipos de trabajo que el programa ya conoce, **sacados de `textos.py`** y no escritos otra vez: son
# los botones que el agricultor tiene desde siempre («HE SEMBRADO», «HE LABRADO LA TIERRA»…) y el
# contrato pide «conservar tipos históricos». Si mañana se añade uno allí, sale aquí solo.
#
# `observacion` se añade porque el contrato la nombra como un trabajo más (§4, S05) y porque **es la
# única puerta por la que una nascencia puede darse por buena**: alguien que la ha visto.
TIPOS_DE_TRABAJO: tuple[str, ...] = tuple(
    dict.fromkeys(
        [trabajo["id"] for trabajo in textos.TRABAJOS]
        + [trabajo["id"] for trabajo in textos.TRABAJOS_DE_LABOR]
        + ["observacion"]
    )
)

# **Los únicos dos tipos que cambian lo que hay sembrado en una tierra.** Y «cambiar» quiere decir
# ponerlo: una siembra dice qué se sembró. Cualquier otro trabajo —el rodillo, el cultivador, el arado,
# la escarda, la poda, el riego, la cosecha— **no lo toca**, ni para ponerlo ni para quitarlo.
TIPOS_QUE_SIEMBRAN = ("siembra", "plantacion")

# Los campos de un trabajo, con el significado de cada uno. Un campo ausente es `None` = «no consta»:
# lo único que cae a `False` son `anulado` y `firmado`, y con motivo: en la tabla son columnas que
# existen, no admiten nulo y su valor por defecto es «no» (un apunte recién creado no está anulado ni
# firmado). Un estado, una superficie o unas horas **no** tienen esa propiedad: su ausencia se queda
# ausente, y por eso un `or 0` en cualquier sitio de este fichero sería un defecto.
CAMPOS_DE_UN_TRABAJO = (
    "id",  # el identificador de la fila de la que sale
    "de_donde",  # "hecho" (la tabla de labores) o "previsto" (el plan)
    "campana_id",
    "tipo",  # siembra, plantacion, riego, cosecha, laboreo, cubierta, poda, desbroce, escarda, pastoreo, observacion, otra
    "subtipo",  # rodillo, cultivador, arado… (solo tiene sentido en `laboreo`)
    "estado",  # None = «no consta» | previsto | en_curso | realizado | cancelado
    "fecha",  # el día en que se hizo
    "fecha_prevista",  # el día para el que está puesto (lo previsto)
    "fecha_fin_prevista",
    "fecha_prevista_antes",  # el día que tenía antes de reprogramarlo
    "parcela_id",
    "grupo_id",
    "superficie_ha",
    "cultivo",  # lo que dice el apunte: de qué cultivo era el trabajo
    "variedad",
    "equipo_id",  # la máquina con la que se hizo
    "persona",  # quién lo hizo
    "horas",
    "insumos",  # lo que se gastó (o lo que se piensa gastar): ver `normaliza_insumo`
    "anulado",
    "motivo_anulacion",
    "clave_de_reenvio",  # la clave del móvil, para no apuntar dos veces lo mismo
    "id_local",
    "firmado",
    "firma_huella",
    "firma_entidad_id",
    "firmado_en",
    "previsto_id",  # el trabajo previsto que este hecho cumple, cuando alguien lo ha dicho
    "nascencia",  # True/False/None, **solo** en una observación de quien la ha visto
    "en_el_suelo",  # True/False/None: lo que queda en la tierra, **solo** si alguien lo ha dicho
    "lluvia_mm",  # lo que dice una estación o un pluviómetro (hecho del tiempo, no trabajo)
    "observaciones",
    "revisado",  # si alguien lo ha corregido después
    "revision_de",  # de qué apunte es esta revisión, cuando lo de antes estaba firmado
)

CAMPOS_DE_UN_INSUMO = (
    "articulo_id",
    "articulo",
    "lote_id",
    "numero_lote",
    "cantidad",
    "unidad",
    "dosis_por_ha",  # lo de cada hectárea, para poder estimar lo que gastaría un trabajo previsto
    "clave_de_reenvio",
    "anulado",
    "movimiento_id",
    "fecha",
    "origen_tipo",  # "labor" o "trabajo_previsto": de qué apunte sale esta salida
    "origen_id",
)

# De qué apunte del cuaderno sale una salida del almacén, y a qué tabla corresponde. Lo escribe el
# programa, no una persona: se saca de aquí para que no haya dos formas de restar (ver `servicios.py`).
DE_DONDE_SALE_UN_APUNTE = {"labor": "hecho", "trabajo_previsto": "previsto"}

# --------------------------------------------------------------------------
# Los códigos de lo que se dice, con el texto que hay que poner en `textos.py`
# --------------------------------------------------------------------------
#
# **Este módulo no escribe ni una frase para el agricultor.** `app/textos.py` es compartido y lo integra
# el coordinador, así que aquí se devuelve el **código** y la frase la pide el router con
# `textos.mensaje(codigo)`. Esta lista está completa y es la que el informe del ticket pide añadir: hay
# una prueba que exige que todos los códigos que el módulo puede devolver estén aquí (y al revés), para
# que no se cuele un código sin frase y salga un hueco en la pantalla, que es el fallo que este proyecto
# ya ha tenido tres veces.
CODIGOS_QUE_SE_DICEN: dict[str, str] = {
    "TJ1_el_previsto_no_gasta": (
        "Este trabajo está previsto y todavía no se ha hecho: no ha gastado nada del almacén."
    ),
    "TJ2_no_consta_si_se_hizo": (
        "De este trabajo no consta si se llegó a hacer, así que no cuenta como trabajo hecho. "
        "Dilo y queda apuntado."
    ),
    "TJ3_el_apunte_esta_anulado": (
        "Este apunte está anulado: lo que había salido del almacén vuelve a contar."
    ),
    "TJ4_lo_que_salio_cambio": (
        "Se corrigió el trabajo: la salida de antes ya no cuenta y se ha apuntado la nueva."
    ),
    "TJ5_falta_el_motivo_para_anular": (
        "Para anular un trabajo hace falta decir por qué. Escríbelo y vuelve a pulsar."
    ),
    "TJ6_el_trabajo_ya_estaba_anulado": (
        "Este trabajo ya estaba anulado, así que no ha cambiado nada."
    ),
    "TJ7_de_la_lluvia_no_sale_la_nascencia": (
        "Que haya llovido no quiere decir que la planta haya nacido: eso se mira en el campo y se "
        "apunta como una observación."
    ),
    "TJ8_un_rodillo_no_cambia_lo_sembrado": (
        "Pasar el rodillo no cambia lo que tienes sembrado: la siembra sigue apuntada."
    ),
    "TJ9_no_se_reprograma_lo_ya_hecho": (
        "Este trabajo ya se hizo, así que su fecha es la del día en que se hizo. Si hiciste otro, "
        "apúntalo."
    ),
    "TJ10_lo_firmado_no_se_borra": (
        "Este apunte está firmado y no se puede borrar: se anula, con su motivo, y queda el rastro."
    ),
    "TJ11_el_trabajo_ya_estaba": (
        "Este trabajo ya estaba apuntado: no se ha vuelto a descontar del almacén."
    ),
    "TJ12_no_se_pudo_comprobar_si_ya_estaba": (
        "Esta petición no trae la clave para saber si ya se había apuntado, así que no he podido "
        "comprobarlo."
    ),
    "TJ13_faltan_las_hectareas": (
        "Hay trabajos de este año que no dicen cuántas hectáreas se trabajaron, así que las que se "
        "ven son solo las que constan."
    ),
    "TJ14_faltan_las_horas": (
        "Hay trabajos de este año que no dicen cuántas horas se estuvo, así que las que se ven son "
        "solo las que constan."
    ),
    "TJ15_la_tierra_quedo_o_no": (
        "Se cogió la cosecha, pero no consta si la tierra quedó con algo o vacía: eso se mira en el "
        "campo y se apunta como una observación."
    ),
    "TJ16_sin_maquina": "Hay trabajos apuntados sin decir con qué máquina se hicieron.",
    "TJ17_un_plan_no_es_un_trabajo": (
        "Esto está planificado y todavía no es un trabajo hecho: cuando lo hagas, apunta lo que de "
        "verdad pasó, con su día y lo que gastaste."
    ),
    "TJ18_sin_tierra": (
        "Hay trabajos que no dicen de qué tierra eran, así que no salen en el historial de ninguna."
    ),
    "TJ19_la_revision_de_lo_firmado": (
        "Lo firmado no se cambia: queda la revisión nueva, y la firma de antes sigue valiendo para lo "
        "que se firmó."
    ),
    "TJ20_no_se_pueden_sumar_unidades": (
        "Hay cantidades en unidades distintas, así que no se pueden juntar en una sola cifra."
    ),
    "TJ21_falta_la_cantidad": (
        "Hay un consumo apuntado sin cantidad, así que no se puede saber lo que queda."
    ),
    "TJ22_falta_la_unidad": (
        "Hay un consumo apuntado sin decir en qué se mide, así que no se puede hacer la cuenta."
    ),
    "TJ23_faltan_las_hectareas_de_la_tierra": (
        "Esta tierra no dice cuántas hectáreas tiene, así que no se puede comparar con lo trabajado."
    ),
    "TJ24_no_hay_fecha_de_hoy": (
        "No sé qué día es hoy, así que no te puedo decir cuánto falta ni cuánto se ha pasado."
    ),
    "TJ25_la_fecha_prevista_no_se_sabe": (
        "Este trabajo está planificado sin día, así que no se puede decir cuándo toca."
    ),
    "TJ26_el_apunte_del_consumo_no_esta": (
        "Hay una salida del almacén que dice venir de un trabajo que no encuentro, así que no la he "
        "podido comprobar."
    ),
    "TJ27_no_se_sabe_si_nacio": (
        "No consta si la planta ha nacido: eso se mira en el campo y se apunta como una observación."
    ),
    "TJ28_no_se_sabe_que_se_sembro": (
        "La siembra está apuntada, pero no dice qué se sembró. Apúntalo y el estado de la tierra "
        "quedará completo."
    ),
}


# --------------------------------------------------------------------------
# Normalizar: de una fila a un trabajo
# --------------------------------------------------------------------------


def normaliza_insumo(fila: Mapping[str, Any] | None) -> dict:
    """Un insumo en su forma de siempre. Lo que no venga se queda en `None` = «no consta».

    `anulado` es la excepción, y por el mismo motivo que en el trabajo: es una columna que existe y que
    no admite nulo, así que su ausencia quiere decir «no está anulado».
    """
    fila = dict(fila or {})
    devuelto = {campo: fila.get(campo) for campo in CAMPOS_DE_UN_INSUMO}
    devuelto["anulado"] = bool(fila.get("anulado", False))
    return devuelto


def normaliza_trabajo(fila: Mapping[str, Any] | None) -> dict:
    """Un trabajo en su forma de siempre: todos los campos, y los que no vengan en `None`.

    **No se rellena ningún hueco.** Este es el punto del fichero donde el defecto que el proyecto
    persigue («un dato que no se sabe se queda en blanco, nunca un cero y nunca un valor por defecto»)
    se podría colar de una vez por todas: un `superficie_ha or 0` aquí haría que todas las superficies
    que no constan fueran cero en el historial, en las sumas y en el papel.
    """
    fila = dict(fila or {})
    devuelto = {campo: fila.get(campo) for campo in CAMPOS_DE_UN_TRABAJO}
    devuelto["insumos"] = [normaliza_insumo(insumo) for insumo in (fila.get("insumos") or [])]
    # Las dos únicas que caen a `False`, y está dicho arriba por qué.
    devuelto["anulado"] = bool(fila.get("anulado", False))
    devuelto["firmado"] = bool(fila.get("firmado", False))
    # Una forma de decir «esto es un hecho» o «esto está planificado», para que el resto del módulo no
    # tenga que adivinar de qué tabla viene una fila. Lo que no lo diga se queda sin decir.
    if devuelto["de_donde"] not in ("hecho", "previsto"):
        devuelto["de_donde"] = None
    return devuelto


def normaliza_trabajos(filas: Iterable[Mapping[str, Any]] | None) -> list[dict]:
    return [normaliza_trabajo(fila) for fila in (filas or [])]


def un_trabajo(**campos: Any) -> dict:
    """Un trabajo escrito a mano (para las pruebas y para el router). Pasa por `normaliza_trabajo`.

    Existe para que haya **una sola** forma de construir un trabajo: si el router y las pruebas lo
    armaran cada uno a su manera, la mitad de las reglas de este fichero se probarían contra una forma
    que no es la que se usa de verdad.
    """
    return normaliza_trabajo(campos)


def un_hecho(**campos: Any) -> dict:
    """Un hecho del cuaderno: lo que pasó. Marca `de_donde="hecho"` y, si no lo dice, `realizado`.

    **Este es el único sitio donde «realizado» se pone sin que nadie lo haya escrito**, y está
    justificado: un apunte de la tabla de labores es un hecho por construcción —el agricultor apuntó
    algo que ya había pasado— y esa tabla no tiene ninguna forma de guardar un plan. Si algún día
    tuviera estados, esta función es la que hay que cambiar, y aquí está el comentario que lo dice.
    """
    campos.setdefault("de_donde", "hecho")
    campos.setdefault("estado", "realizado")
    return normaliza_trabajo(campos)


def un_previsto(**campos: Any) -> dict:
    """Un trabajo planificado: lo que se piensa hacer.

    El estado por defecto es `previsto` **y aquí sí es correcto**, al revés que en la tabla de hechos:
    una fila de la tabla de lo previsto es un plan porque es donde se apuntan los planes. Lo que sería
    un defecto es poner ese valor por defecto en la tabla de labores, donde convertiría en
    «planificado» todo lo que el agricultor ya tiene apuntado.
    """
    campos.setdefault("de_donde", "previsto")
    campos.setdefault("estado", "previsto")
    return normaliza_trabajo(campos)


def un_insumo(**campos: Any) -> dict:
    """Un insumo escrito a mano. Ver `normaliza_insumo`."""
    return normaliza_insumo(campos)


# --------------------------------------------------------------------------
# Qué es cada cosa: estado, trabajo hecho, consumo
# --------------------------------------------------------------------------


def estado_de(trabajo: Mapping[str, Any] | None) -> str | None:
    """El estado de un trabajo, **con `None` para «no consta»**.

    Un estado que el programa no conoce se devuelve como `None`: guardar un estado raro no puede
    convertirse en «realizado» al leerlo, que es la forma de que un dato sin sentido acabe acreditando
    trabajo hecho.
    """
    estado = (trabajo or {}).get("estado")
    if estado is None:
        return None
    limpio = str(estado).strip().lower()
    return limpio if limpio in ESTADOS_DE_UN_TRABAJO else None


def esta_anulado(trabajo: Mapping[str, Any] | None) -> bool:
    return bool((trabajo or {}).get("anulado"))


def es_un_trabajo_de_la_tierra(trabajo: Mapping[str, Any] | None) -> bool:
    """Si esto es algo que se hizo **en la tierra**. La lluvia no lo es (es un hecho del tiempo)."""
    return (trabajo or {}).get("tipo") not in HECHOS_DEL_TIEMPO


def tipo_y_subtipo(trabajo: Mapping[str, Any] | None) -> str:
    """El nombre del trabajo para agrupar y para contar: `laboreo:rodillo`, `siembra`, `lluvia`.

    Se usa `:subtipo` solo cuando hay subtipo, para que «laboreo» a secas y «laboreo:rodillo» no se
    confundan en un recuento: son la misma familia y no son el mismo trabajo.
    """
    tipo = ((trabajo or {}).get("tipo") or "").strip() or "sin_tipo"
    subtipo = ((trabajo or {}).get("subtipo") or "").strip()
    return f"{tipo}:{subtipo}" if subtipo else tipo


def acredita_un_trabajo_hecho(trabajo: Mapping[str, Any] | None) -> bool:
    """**Si esto cuenta como trabajo hecho.** Solo `realizado`, y solo si no está anulado.

    Lo demás no cuenta, y cada cosa por su motivo: lo previsto no se ha hecho, lo cancelado no se hizo,
    lo que está en curso no se ha terminado (contarlo como hecho es apuntar el resultado antes de
    tenerlo) y **lo que no consta no se supone**. `None` —no saberlo— no es un «sí» ni un «no».
    """
    return not esta_anulado(trabajo) and estado_de(trabajo) == "realizado"


def consume_existencias(trabajo: Mapping[str, Any] | None) -> tuple[bool, str]:
    """**Si este trabajo ha gastado producto del almacén, y si no, por qué.**

    Devuelve `(consume, codigo_del_motivo)`. El código va vacío cuando sí consume.

    Esta es la primera regla del encargo escrita en un solo sitio: **lo previsto no consume
    existencias**. Y tampoco consume lo que no ha pasado, ni lo anulado (anular devuelve al almacén lo
    que salió sin tocar el libro: el movimiento se queda y deja de contar).
    """
    if esta_anulado(trabajo):
        return False, "TJ3_el_apunte_esta_anulado"
    estado = estado_de(trabajo)
    if estado == "realizado":
        return True, ""
    if estado is None:
        return False, "TJ2_no_consta_si_se_hizo"
    if estado in ("previsto", "en_curso"):
        return False, "TJ1_el_previsto_no_gasta"
    return False, "TJ17_un_plan_no_es_un_trabajo"


def cambia_el_cultivo(trabajo: Mapping[str, Any] | None) -> bool:
    """**Si este trabajo cambia lo que hay sembrado en la tierra.** Solo sembrar y plantar.

    El caso A04 del contrato, entero, en una línea: *«rodillo después de siembra → el historial contiene
    ambos; el cultivo permanece; sin inferir nascencia»*. Un apero no siembra y no desiembra, y ninguna
    otra labor toca el cultivo declarado: ni el arado, ni la escarda, ni la poda, ni el riego, ni la
    cosecha (coger el grano no borra el apunte de que se sembró).
    """
    return (trabajo or {}).get("tipo") in TIPOS_QUE_SIEMBRAN and acredita_un_trabajo_hecho(trabajo)


# --------------------------------------------------------------------------
# La fecha: lo que falta y lo que se ha pasado
# --------------------------------------------------------------------------


def dias_que_faltan(fecha: dt.date | str | None, hoy: dt.date | str | None) -> int | None:
    """Los días que faltan para esa fecha (negativo si ya pasó), o `None` si no se puede saber.

    Se devuelve `None` cuando falta la fecha **o** cuando falta el día de hoy, y no un cero: un cero es
    «es hoy», que es una afirmación distinta de «no sé cuándo es». Sin día de hoy no se cuenta nada, y
    el motivo está en `TJ24_no_hay_fecha_de_hoy`.
    """
    una = como_fecha(fecha)
    otra = como_fecha(hoy)
    if una is None or otra is None:
        return None
    return (una - otra).days


def como_fecha(valor: dt.date | str | None) -> dt.date | None:
    """Una fecha de verdad, venga como venga. Lo que no se puede entender se queda en `None`."""
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    if valor is None:
        return None
    try:
        return dt.date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _cronologico(trabajo: Mapping[str, Any]) -> tuple[dt.date, int]:
    """Lo que ordena el historial: la fecha del trabajo o, si no la hay, la fecha prevista.

    Un trabajo sin ninguna fecha **no se tira**: se queda al principio y consta en `sin_fecha`. Un
    historial que esconde lo que no tiene fecha es un historial que miente por omisión.
    """
    fecha = como_fecha(trabajo.get("fecha")) or como_fecha(trabajo.get("fecha_prevista"))
    return (fecha or dt.date.min, int(trabajo.get("id") or 0))


# --------------------------------------------------------------------------
# Las sumas: «sumando lo que se sabe», que es la regla de la casa
# --------------------------------------------------------------------------


def sumando_lo_que_se_sabe(valores: Iterable[float | None]) -> dict:
    """Suma **solo lo que consta** y dice cuántos no lo dicen. Es la regla del panel de mando.

    Devuelve `{"suma", "cuantos", "sin_decir"}`. No es un descuido que `suma` pueda ser 0 con
    `sin_decir` en 3: la suma es de lo que se sabe y el hueco se cuenta aparte, para poder decir en
    pantalla «sin hectáreas dichas: 3». Lo que no se hace nunca es `(valor or 0)`, que convertiría tres
    huecos en tres ceros y haría creer que se trabajaron cero hectáreas.
    """
    cuantos = 0
    sin_decir = 0
    suma = 0.0
    for valor in valores:
        cuantos += 1
        if valor is None:
            sin_decir += 1
            continue
        suma += float(valor)
    return {"suma": round(suma, 6), "cuantos": cuantos, "sin_decir": sin_decir}


def saldo_de_los_consumos(consumos: Sequence[Mapping[str, Any]]) -> dict:
    """Lo que suman unos consumos, **o `None` con el motivo** si no se puede sumar.

    Es la regla del almacén (`servicios.saldo_de_un_conjunto`), y es distinta de la de arriba a
    propósito: en un panel interesa «lo que consta y cuántos huecos hay», pero **un saldo no se puede
    dar a medias**. Si un consumo no dice la cantidad, no se puede saber lo que queda, y decir «queda lo
    que suman los demás» sería un número que no es el saldo de nada.
    """
    unidades = {str(c.get("unidad")).strip() for c in consumos if (c.get("unidad") or "").strip()}
    faltan_cantidad = [c for c in consumos if c.get("cantidad") is None]
    faltan_unidad = [
        c for c in consumos if c.get("cantidad") is not None and not (c.get("unidad") or "").strip()
    ]
    devuelto = {
        "cuantos": len(consumos),
        "sin_decir": len(faltan_cantidad) + len(faltan_unidad),
        "unidades": sorted(unidades),
        "suma": None,
        "motivo_codigo": "",
    }
    if faltan_cantidad:
        devuelto["motivo_codigo"] = "TJ21_falta_la_cantidad"
        return devuelto
    if faltan_unidad:
        devuelto["motivo_codigo"] = "TJ22_falta_la_unidad"
        return devuelto
    if len(unidades) > 1:
        devuelto["motivo_codigo"] = "TJ20_no_se_pueden_sumar_unidades"
        return devuelto
    if not consumos:
        # Sin consumos, el saldo es cero **de verdad**: no hay nada que no se sepa. Es distinto de un
        # consumo cuya cantidad no consta, y por eso se distinguen (arriba, con su motivo).
        devuelto["suma"] = 0.0
        return devuelto
    devuelto["suma"] = round(sum(float(c["cantidad"]) for c in consumos), 6)
    return devuelto


# --------------------------------------------------------------------------
# Las cifras de una tierra: un solo sitio para el cuaderno y para los paneles
# --------------------------------------------------------------------------


def cifras_de_una_tierra(
    trabajos: Iterable[Mapping[str, Any]] | None,
    *,
    campana_id: int | None = None,
) -> dict:
    """Las cuentas de una tierra: hectáreas, horas, insumos y cuántos huecos hay.

    **Es la única cuenta de este módulo**, y el historial y el estado la llevan dentro tal cual (hay una
    prueba que lo exige). El motivo es la regla del encargo: «el cuaderno y los paneles usan los mismos
    hechos: si una cifra sale en una pantalla y en el cuaderno, sale del mismo sitio». Dos sumas
    distintas de lo mismo no se quedan iguales mucho tiempo.

    Solo cuentan los trabajos que **acreditan** (hechos y no anulados). Lo previsto no entra aquí: es lo
    que se piensa hacer, y en `estimacion_de_lo_previsto` está lo que gastaría, **dicho como estimación**
    y sin tocar ninguna cifra de estas.
    """
    todos = normaliza_trabajos(trabajos)
    if campana_id is not None:
        todos = [t for t in todos if t.get("campana_id") == campana_id]
    de_la_tierra = [t for t in todos if es_un_trabajo_de_la_tierra(t)]
    cuentan = [t for t in de_la_tierra if acredita_un_trabajo_hecho(t)]

    hectareas = sumando_lo_que_se_sabe(t.get("superficie_ha") for t in cuentan)
    horas = sumando_lo_que_se_sabe(t.get("horas") for t in cuentan)

    por_tipo: dict[str, int] = {}
    for trabajo in cuentan:
        nombre = tipo_y_subtipo(trabajo)
        por_tipo[nombre] = por_tipo.get(nombre, 0) + 1

    insumos = [
        insumo for trabajo in cuentan for insumo in trabajo["insumos"] if not insumo.get("anulado")
    ]
    return {
        "trabajos_hechos": len(cuentan),
        "trabajos_anulados": len([t for t in todos if esta_anulado(t)]),
        "por_tipo": por_tipo,
        "superficie_ha": hectareas["suma"],
        "superficie_sin_decir": hectareas["sin_decir"],
        "horas": horas["suma"],
        "horas_sin_decir": horas["sin_decir"],
        "insumos": insumos,
        "insumos_sin_cantidad": len([i for i in insumos if i.get("cantidad") is None]),
        "sin_maquina": len([t for t in cuentan if t.get("equipo_id") is None]),
        "sin_tierra": len([t for t in de_la_tierra if t.get("parcela_id") is None]),
        "lo_que_no_se_sabe": _lo_que_no_se_sabe(hectareas, horas, cuentan, de_la_tierra),
    }


def _lo_que_no_se_sabe(
    hectareas: dict, horas: dict, cuentan: Sequence[Mapping[str, Any]], todos: Sequence[Mapping[str, Any]]
) -> list[dict]:
    """Lo que falta por saber, con su código y **con cuántos son**. Nunca en blanco y nunca un cero.

    Se devuelve una lista de `{"codigo", "cuantos"}`: la frase la pone `textos.py` y el número va
    aparte, para no tener que inventarse una frase distinta por cada cuenta («1 trabajo», «2 trabajos»)
    dentro de un mensaje que se escribe una vez.
    """
    faltas: list[dict] = []
    if hectareas["sin_decir"]:
        faltas.append({"codigo": "TJ13_faltan_las_hectareas", "cuantos": hectareas["sin_decir"]})
    if horas["sin_decir"]:
        faltas.append({"codigo": "TJ14_faltan_las_horas", "cuantos": horas["sin_decir"]})
    sin_maquina = len([t for t in cuentan if t.get("equipo_id") is None])
    if sin_maquina:
        faltas.append({"codigo": "TJ16_sin_maquina", "cuantos": sin_maquina})
    sin_tierra = len([t for t in todos if t.get("parcela_id") is None])
    if sin_tierra:
        faltas.append({"codigo": "TJ18_sin_tierra", "cuantos": sin_tierra})
    return faltas


# --------------------------------------------------------------------------
# El historial de una tierra (S03: «Historia»)
# --------------------------------------------------------------------------


def historial_de_una_tierra(
    trabajos: Iterable[Mapping[str, Any]] | None,
    *,
    parcela_id: int | None = None,
    campana_id: int | None = None,
    incluir_anulados: bool = True,
    hoy: dt.date | None = None,
) -> dict:
    """**Todo lo que ha pasado en una tierra, en orden, sin tirar nada.**

    Aquí está la segunda regla del encargo: *todos los eventos se conservan*. El rodillo, el cultivador,
    la siembra y las demás labores **permanecen**: lo anulado no desaparece —se queda con su motivo,
    diciendo que no cuenta— y lo que no tiene fecha se queda al principio en vez de esfumarse.
    `incluir_anulados=False` existe para una pantalla que quiera enseñar solo lo que cuenta, y aun así
    devuelve cuántos se ha dejado fuera: una lista filtrada que no dice que está filtrada es la forma de
    que el agricultor crea que le falta un apunte.

    Cada línea dice, además de lo que pasó: si **cuenta** como trabajo hecho, por qué no cuenta cuando
    no cuenta, si **gasta** del almacén, y **qué cambió** en lo que hay sembrado, que es lo que permite
    leer el historial como una historia y no como una lista.
    """
    todos = normaliza_trabajos(trabajos)
    if parcela_id is not None:
        todos = [t for t in todos if t.get("parcela_id") == parcela_id]
    if campana_id is not None:
        todos = [t for t in todos if t.get("campana_id") == campana_id]

    ordenados = sorted(todos, key=_cronologico)
    lineas: list[dict] = []
    sembrado: dict | None = None
    for trabajo in ordenados:
        if cambia_el_cultivo(trabajo):
            sembrado = {
                "tipo": trabajo.get("tipo"),
                "cultivo": trabajo.get("cultivo"),
                "variedad": trabajo.get("variedad"),
                "fecha": trabajo.get("fecha"),
                "trabajo_id": trabajo.get("id"),
            }
        cuenta = acredita_un_trabajo_hecho(trabajo)
        consume, porque_no_consume = consume_existencias(trabajo)
        lineas.append(
            {
                "trabajo": trabajo,
                "id": trabajo.get("id"),
                "fecha": trabajo.get("fecha") or trabajo.get("fecha_prevista"),
                "tipo_y_subtipo": tipo_y_subtipo(trabajo),
                "estado": estado_de(trabajo),
                "anulado": esta_anulado(trabajo),
                "motivo_anulacion": trabajo.get("motivo_anulacion"),
                "cuenta_como_hecho": cuenta,
                # El mismo código que dice por qué no gasta: es la misma pregunta.
                "no_cuenta_porque_codigo": "" if cuenta else porque_no_consume,
                "consume": consume,
                "no_consume_porque_codigo": porque_no_consume,
                "que_cambio": "se_sembro" if cambia_el_cultivo(trabajo) else "",
                "lo_que_hay_sembrado_despues": dict(sembrado) if sembrado else None,
                "revisado": bool(trabajo.get("revisado")),
                "firmado": bool(trabajo.get("firmado")),
                "insumos": list(trabajo["insumos"]),
            }
        )

    se_dejan_fuera = 0
    if not incluir_anulados:
        se_dejan_fuera = len([linea for linea in lineas if linea["anulado"]])
        lineas = [linea for linea in lineas if not linea["anulado"]]

    return {
        "parcela_id": parcela_id,
        "lineas": lineas,
        "cuantos": len(lineas),
        "anulados": len([linea for linea in lineas if linea["anulado"]]),
        "se_dejan_fuera": se_dejan_fuera,
        "sin_fecha": len([linea for linea in lineas if not linea["fecha"]]),
        # **Las mismas cifras que el estado**, sacadas de la misma función.
        "cifras": cifras_de_una_tierra(todos, campana_id=campana_id),
        "hoy": como_fecha(hoy),
    }


# --------------------------------------------------------------------------
# El estado derivado: qué tiene sembrado, qué se ha hecho, qué queda
# --------------------------------------------------------------------------


def estado_de_una_tierra(
    trabajos: Iterable[Mapping[str, Any]] | None,
    previstos: Iterable[Mapping[str, Any]] | None = None,
    *,
    parcela_id: int | None = None,
    campana_id: int | None = None,
    hoy: dt.date | None = None,
) -> dict:
    """**Qué tiene sembrado, qué se ha hecho y qué queda previsto**, sacado de los hechos.

    Lo que este estado **no** hace, que es lo que más importa:

      · **No deduce nada del tiempo.** `nascencia` solo tiene valor si alguien la apuntó como
        observación; si llovió y nadie ha mirado el campo, la nascencia es `None` y se dice por qué
        (`TJ7`). Una estación dice que llovió, no que la planta haya nacido.
      · **No borra lo sembrado por una labor de suelo.** El cultivo sale de la última siembra o
        plantación que cuenta y de nada más: pasar el rodillo después de sembrar deja el estado de
        siembra donde estaba, y `TJ8` lo explica para que nadie lo tome por un olvido.
      · **No afirma que la tierra quedó vacía después de la cosecha.** `en_el_suelo` es `None` hasta que
        alguien lo diga: coger el grano no dice si quedó rastrojo, cubierta o nada.
      · **No supone que lo previsto se ha hecho.** Lo que queda pendiente sale en `que_queda_previsto`,
        aparte de lo hecho, y con los días que faltan (o sin ellos, si no tiene día).

    El estado se separa, como pide el contrato (S03), en **cuatro cosas distintas**: la última labor, el
    cultivo declarado, las observaciones de campo y las estimaciones. Mezclarlas es exactamente lo que
    hace que un programa parezca saber más de lo que sabe.
    """
    todos = normaliza_trabajos(trabajos)
    planes = normaliza_trabajos(previstos)
    if parcela_id is not None:
        todos = [t for t in todos if t.get("parcela_id") == parcela_id]
        planes = [t for t in planes if t.get("parcela_id") == parcela_id]
    if campana_id is not None:
        todos = [t for t in todos if t.get("campana_id") == campana_id]
        planes = [t for t in planes if t.get("campana_id") == campana_id]

    ordenados = sorted(todos, key=_cronologico)
    cuentan = [t for t in ordenados if acredita_un_trabajo_hecho(t)]
    cifras = cifras_de_una_tierra(todos, campana_id=campana_id)

    # ── Lo que hay sembrado: la última siembra o plantación que cuenta, y nada más ──
    siembras = [t for t in cuentan if cambia_el_cultivo(t)]
    ultima_siembra = siembras[-1] if siembras else None
    cultivo = None
    if ultima_siembra is not None:
        cultivo = {
            "tipo": ultima_siembra.get("tipo"),
            "cultivo": ultima_siembra.get("cultivo"),
            "variedad": ultima_siembra.get("variedad"),
            "fecha": ultima_siembra.get("fecha"),
            "trabajo_id": ultima_siembra.get("id"),
            "superficie_ha": ultima_siembra.get("superficie_ha"),
        }

    # ── La última labor: el último trabajo de la tierra, sea del tipo que sea ──
    ultima_labor = None
    if cuentan:
        ultimo = cuentan[-1]
        ultima_labor = {
            "tipo": ultimo.get("tipo"),
            "subtipo": ultimo.get("subtipo"),
            "tipo_y_subtipo": tipo_y_subtipo(ultimo),
            "fecha": ultimo.get("fecha"),
            "trabajo_id": ultimo.get("id"),
            "equipo_id": ultimo.get("equipo_id"),
            "superficie_ha": ultimo.get("superficie_ha"),
        }

    # ── Las observaciones de campo: lo que alguien ha visto, con su fecha ──
    observaciones = [
        {
            "trabajo_id": t.get("id"),
            "fecha": t.get("fecha"),
            "tipo": t.get("tipo"),
            "nascencia": t.get("nascencia"),
            "en_el_suelo": t.get("en_el_suelo"),
            "observaciones": t.get("observaciones"),
        }
        for t in cuentan
        if t.get("tipo") == "observacion"
        or t.get("nascencia") is not None
        or t.get("en_el_suelo") is not None
    ]

    # ── La nascencia: **solo** de una observación, nunca del tiempo ──
    con_nascencia = [o for o in observaciones if o["nascencia"] is not None]
    ultima_nascencia = con_nascencia[-1] if con_nascencia else None
    lluvias = [t for t in cuentan if t.get("tipo") in HECHOS_DEL_TIEMPO]
    porque_nascencia = ""
    if ultima_nascencia is None and siembras:
        # Hay algo sembrado y nadie ha dicho si nació. Si además ha llovido, se dice con su frase
        # entera, porque es justo lo que se tiende a deducir.
        porque_nascencia = (
            "TJ7_de_la_lluvia_no_sale_la_nascencia" if lluvias else "TJ27_no_se_sabe_si_nacio"
        )

    # ── Lo que queda en el suelo, después de una cosecha: se dice, no se supone ──
    se_cosecho = [t for t in cuentan if t.get("tipo") == "cosecha"]
    dichos_del_suelo = [o for o in observaciones if o["en_el_suelo"] is not None]
    en_el_suelo = dichos_del_suelo[-1]["en_el_suelo"] if dichos_del_suelo else None
    porque_en_el_suelo = ""
    if en_el_suelo is None and se_cosecho:
        porque_en_el_suelo = "TJ15_la_tierra_quedo_o_no"

    # ── Lo que queda previsto, con sus días ──
    planes_vivos = [p for p in planes if estado_de(p) in ("previsto", "en_curso")]
    planes_vivos = sorted(
        planes_vivos,
        key=lambda p: (como_fecha(p.get("fecha_prevista")) or dt.date.max, int(p.get("id") or 0)),
    )
    quedan: list[dict] = []
    sin_dia = 0
    retrasados = 0
    for plan in planes_vivos:
        dias = dias_que_faltan(plan.get("fecha_prevista"), hoy)
        if dias is None:
            sin_dia += 1
        elif dias < 0:
            retrasados += 1
        quedan.append(
            {
                "previsto": plan,
                "id": plan.get("id"),
                "tipo_y_subtipo": tipo_y_subtipo(plan),
                "fecha_prevista": plan.get("fecha_prevista"),
                "dias_que_faltan": dias,
                "sin_dia_porque_codigo": _por_que_no_hay_dias(plan, hoy),
                "estado": estado_de(plan),
                "gastaria": estimacion_de_lo_previsto(plan),
            }
        )

    # Un apero detrás de una siembra: se dice que no cambia nada, porque es lo que se pregunta.
    aperos_despues_de_sembrar = [
        t
        for t in cuentan
        if t.get("tipo") == "laboreo"
        and ultima_siembra is not None
        and _cronologico(t) >= _cronologico(ultima_siembra)
    ]

    return {
        "parcela_id": parcela_id,
        # 1. La última labor
        "ultima_labor": ultima_labor,
        # 2. El cultivo declarado (lo que hay sembrado)
        "cultivo_declarado": cultivo,
        "se_ha_sembrado": bool(siembras),
        "cuantas_siembras": len(siembras),
        "no_se_sabe_que_se_sembro_codigo": (
            "TJ28_no_se_sabe_que_se_sembro"
            if ultima_siembra is not None and not (ultima_siembra.get("cultivo") or "").strip()
            else ""
        ),
        # 3. Las observaciones de campo
        "observaciones": observaciones,
        "nascencia": ultima_nascencia["nascencia"] if ultima_nascencia else None,
        "nascencia_dicha_por": ultima_nascencia,
        "no_se_puede_deducir_la_nascencia_porque_codigo": porque_nascencia,
        "en_el_suelo": en_el_suelo,
        "no_se_puede_deducir_el_suelo_porque_codigo": porque_en_el_suelo,
        "hubo_lluvia": bool(lluvias),
        "lluvias": [
            {"trabajo_id": t.get("id"), "fecha": t.get("fecha"), "milimetros": t.get("lluvia_mm")}
            for t in lluvias
        ],
        # 4. Las estimaciones (lo que es una cuenta nuestra, dicha como tal)
        "estimaciones": [
            {"trabajo_id": linea["id"], "gastaria": linea["gastaria"]}
            for linea in quedan
            if linea["gastaria"]["se_puede_estimar"]
        ],
        # Lo que queda previsto
        "que_queda_previsto": quedan,
        "cuantos_previstos": len(quedan),
        "previstos_sin_dia": sin_dia,
        "previstos_retrasados": retrasados if hoy is not None else None,
        # Lo que se ha hecho
        "que_se_ha_hecho": cifras["por_tipo"],
        "aperos_despues_de_sembrar": [t.get("id") for t in aperos_despues_de_sembrar],
        "un_apero_no_cambia_lo_sembrado_codigo": (
            "TJ8_un_rodillo_no_cambia_lo_sembrado" if aperos_despues_de_sembrar else ""
        ),
        # Y lo que no consta, dicho
        "cifras": cifras,
        "hoy": como_fecha(hoy),
    }


def _por_que_no_hay_dias(plan: Mapping[str, Any], hoy: dt.date | None) -> str:
    """Por qué no se pueden contar los días que faltan: sin fecha prevista, o sin fecha de hoy."""
    if como_fecha(plan.get("fecha_prevista")) is None:
        return "TJ25_la_fecha_prevista_no_se_sabe"
    if como_fecha(hoy) is None:
        return "TJ24_no_hay_fecha_de_hoy"
    return ""


# --------------------------------------------------------------------------
# Lo previsto y lo hecho, juntos y separados
# --------------------------------------------------------------------------


def lo_previsto_y_lo_hecho(
    previstos: Iterable[Mapping[str, Any]] | None,
    hechos: Iterable[Mapping[str, Any]] | None,
) -> dict:
    """Lo planificado y lo que de verdad pasó, **sin emparejar nada por parecido**.

    El vínculo es `previsto_id`: el hecho dice de qué plan salió porque alguien lo dijo. Emparejar por
    «misma tierra y mismo tipo en fechas parecidas» sería adivinar, y la adivinación aquí tiene un
    precio concreto: dar por hecho un trabajo que no se hizo (o al revés), que es justo lo que el
    contrato prohíbe en A05.
    """
    planes = normaliza_trabajos(previstos)
    trabajos = normaliza_trabajos(hechos)

    cumplidos: list[dict] = []
    sin_cumplir: list[dict] = []
    cancelados: list[dict] = []
    for plan in planes:
        del_plan = [h for h in trabajos if h.get("previsto_id") == plan.get("id")]
        vivos = [h for h in del_plan if acredita_un_trabajo_hecho(h)]
        if vivos:
            cumplidos.append({"previsto": plan, "hechos": vivos})
        elif estado_de(plan) == "cancelado":
            cancelados.append({"previsto": plan})
        else:
            sin_cumplir.append({"previsto": plan, "hechos_que_no_cuentan": del_plan})

    return {
        "previstos": planes,
        "hechos": trabajos,
        "cumplidos": cumplidos,
        "sin_cumplir": sin_cumplir,
        "cancelados": cancelados,
        "hechos_sin_plan": [h for h in trabajos if h.get("previsto_id") is None],
        "cuantos_previstos": len(planes),
        "cuantos_hechos": len([h for h in trabajos if acredita_un_trabajo_hecho(h)]),
    }


def estimacion_de_lo_previsto(previsto: Mapping[str, Any] | None) -> dict:
    """**Lo que gastaría** un trabajo previsto, dicho como estimación y sin tocar ninguna existencia.

    Es la primera regla del encargo dicha al derecho: se puede enseñar al agricultor lo que va a
    necesitar —dosis × hectáreas, con sus dos números— y eso **no es un consumo**. Devuelve
    `se_puede_estimar: False` con lo que falta cuando la cantidad y la dosis no constan, y **no calcula
    nada a medias**: sin hectáreas no hay total, y un total inventado aquí es una compra que el
    agricultor no necesita.
    """
    trabajo = normaliza_trabajo(previsto)
    superficie = trabajo.get("superficie_ha")
    falta: list[str] = []
    if superficie is None:
        falta.append("superficie_ha")
    estimados: list[dict] = []
    for insumo in trabajo["insumos"]:
        if insumo.get("cantidad") is not None:
            # Cuando el plan ya dice la cantidad total, esa es la estimación: no se recalcula.
            estimados.append(
                {
                    "articulo_id": insumo.get("articulo_id"),
                    "articulo": insumo.get("articulo"),
                    "unidad": insumo.get("unidad"),
                    "cantidad_estimada": insumo["cantidad"],
                    "calculada": False,
                }
            )
            continue
        dosis = insumo.get("dosis_por_ha")
        if dosis is None:
            falta.append("dosis_por_ha")
            continue
        if superficie is None:
            continue
        estimados.append(
            {
                "articulo_id": insumo.get("articulo_id"),
                "articulo": insumo.get("articulo"),
                "unidad": insumo.get("unidad"),
                "cantidad_estimada": round(float(dosis) * float(superficie), 6),
                "calculada": True,
            }
        )
    return {
        "se_puede_estimar": bool(estimados),
        "completa": not falta,
        "estimados": estimados,
        "falta": falta,
        "es_una_estimacion": True,
        # Escrito en el dato y no en un comentario: esto **no** ha salido del almacén.
        "consume_existencias": False,
        "porque_codigo": "TJ1_el_previsto_no_gasta",
    }


def reprogramar(
    previsto: Mapping[str, Any] | None,
    fecha_nueva: dt.date | str | None,
    *,
    motivo: str | None = None,
) -> dict:
    """Mover un trabajo **previsto** a otro día. Lo ya hecho no se mueve, y se dice por qué.

    El contrato lo dice con esas palabras: «Reprogramar no cambia fecha de un trabajo ya realizado». Un
    trabajo hecho tiene la fecha del día en que se hizo, y esa fecha es la que va al cuaderno; si se
    pudiera mover, el cuaderno diría que se sembró un día que no se sembró.

    Y lo que se mueve es `fecha_prevista`, dejando **la fecha de antes** en `fecha_prevista_antes`:
    cambiar un día sin dejar el anterior es de las cosas que después nadie puede explicar.
    """
    trabajo = normaliza_trabajo(previsto)
    estado = estado_de(trabajo)
    if estado == "realizado":
        return {
            "cambiado": False,
            "motivo_codigo": "TJ9_no_se_reprograma_lo_ya_hecho",
            "trabajo": trabajo,
        }
    if estado == "cancelado":
        return {"cambiado": False, "motivo_codigo": "TJ17_un_plan_no_es_un_trabajo", "trabajo": trabajo}
    nueva = como_fecha(fecha_nueva)
    if nueva is None:
        return {
            "cambiado": False,
            "motivo_codigo": "TJ25_la_fecha_prevista_no_se_sabe",
            "trabajo": trabajo,
        }
    antes = trabajo.get("fecha_prevista")
    devuelto = dict(trabajo)
    devuelto["fecha_prevista"] = nueva
    devuelto["fecha_prevista_antes"] = antes
    devuelto["revisado"] = True
    return {
        "cambiado": True,
        "motivo_codigo": "",
        "motivo": (motivo or "").strip()[:500] or None,
        "trabajo": devuelto,
        "cambios": {"fecha_prevista": [_fecha_texto(antes), _fecha_texto(nueva)]},
    }


def marcar_como_hecho(previsto: Mapping[str, Any] | None, hecho: Mapping[str, Any] | None) -> dict:
    """Ata un hecho al plan del que salió. **El hecho lo crea el router**, con lo que de verdad pasó.

    Devuelve las dos filas preparadas: el plan pasa a `realizado` y el hecho apunta al plan. Y devuelve
    también lo que hay que decir cuando no se puede hacer: un plan ya cumplido no se cumple dos veces
    (si se hizo otra vez, es **otro** trabajo) y un plan cancelado no se convierte en hecho —lo que
    hubo fue otra cosa—.

    Aquí está A05 otra vez, al derecho: **un plan no añade una labor realizada**. La labor existe cuando
    el agricultor dice qué pasó, con su día, sus hectáreas y lo que se gastó de verdad.
    """
    plan = normaliza_trabajo(previsto)
    trabajo = normaliza_trabajo(hecho)
    if estado_de(plan) == "realizado":
        return {"se_puede": False, "motivo_codigo": "TJ11_el_trabajo_ya_estaba", "previsto": plan}
    if estado_de(plan) == "cancelado":
        return {"se_puede": False, "motivo_codigo": "TJ17_un_plan_no_es_un_trabajo", "previsto": plan}
    if not acredita_un_trabajo_hecho(trabajo):
        # Lo que se marca como hecho es lo que pasó: un hecho sin estado de hecho no cumple nada.
        return {"se_puede": False, "motivo_codigo": "TJ2_no_consta_si_se_hizo", "previsto": plan}
    plan_nuevo = dict(plan)
    plan_nuevo["estado"] = "realizado"
    trabajo_nuevo = dict(trabajo)
    trabajo_nuevo["previsto_id"] = plan.get("id")
    return {
        "se_puede": True,
        "motivo_codigo": "",
        "previsto": plan_nuevo,
        "hecho": trabajo_nuevo,
        "lo_que_cambia": {"estado_del_previsto": [estado_de(plan), "realizado"]},
    }


# --------------------------------------------------------------------------
# Corregir y anular: nada se borra y nada se duplica
# --------------------------------------------------------------------------


def anular(trabajo: Mapping[str, Any] | None, motivo: str | None) -> dict:
    """Anula un trabajo: **se queda, tachado, con su motivo**. No se borra ni se esconde.

    Devuelve el trabajo anulado (una copia: el original sigue donde estaba, porque el original es lo que
    hay en el cuaderno) y **los consumos que dejan de contar**, que es la mitad de la tercera regla:
    anular un trabajo devuelve al almacén lo que gastó *sin tocar el libro*. El movimiento se queda con
    su fecha y su cantidad y deja de contar; no se borra y no hay que deshacer ninguna resta.

    Un motivo es obligatorio y tiene que tener al menos tres letras: dentro de dos años, el motivo es lo
    único que explica por qué ese trabajo no se hizo. Y anular dos veces no hace nada nuevo, pero
    tampoco falla: devuelve que ya estaba.
    """
    devuelto: dict[str, Any] = {
        "anulado": False,
        "ya_estaba": False,
        "motivo_codigo": "",
        "trabajo": dict(trabajo or {}),
        "consumos_que_dejan_de_contar": [],
        "el_apunte_sigue_en_el_historial": True,
    }
    if trabajo is None:
        return devuelto
    if esta_anulado(trabajo):
        devuelto["ya_estaba"] = True
        devuelto["motivo_codigo"] = "TJ6_el_trabajo_ya_estaba_anulado"
        return devuelto
    limpio = (motivo or "").strip()
    if len(limpio) < 3:
        devuelto["motivo_codigo"] = "TJ5_falta_el_motivo_para_anular"
        return devuelto

    devuelto["anulado"] = True
    nuevo = dict(normaliza_trabajo(trabajo))
    nuevo["anulado"] = True
    nuevo["motivo_anulacion"] = limpio[:500]
    devuelto["trabajo"] = nuevo
    devuelto["consumos_que_dejan_de_contar"] = [
        {**insumo, "motivo_codigo": "TJ3_el_apunte_esta_anulado"}
        for insumo in nuevo["insumos"]
        if not insumo.get("anulado")
    ]
    return devuelto


def corregir(
    trabajo: Mapping[str, Any] | None,
    cambios: Mapping[str, Any] | None,
    *,
    motivo: str | None = None,
) -> dict:
    """Corrige un trabajo **en la misma fila**, dejando lo que decía antes, y sin duplicar consumos.

    Devuelve tres cosas, que son las tres reglas de este apartado:

      1. `cambios`: campo por campo, `[antes, ahora]`. Es lo que se guarda en el rastro y lo que permite
         contestar «¿y esto por qué está así?» dentro de dos años.
      2. `consumos_que_hay_que_anular` y `consumos_que_hay_que_apuntar`: si lo que cambia es **lo que
         salió del almacén** (la cantidad, la unidad, el envase, el artículo o el día), la salida vieja
         se anula y se apunta la nueva. **Nunca se reescribe la cantidad de un movimiento por detrás**
         y nunca quedan dos vivas: la anulada sigue en el libro, tachada, y no cuenta. Si nada de eso
         cambia, `hay_que_tocar_el_almacen` es `False` y el almacén no se toca: corregir unas horas no
         puede mover existencias.
      3. `revision_nueva` y `lo_firmado_no_se_toca`: **un apunte firmado no se cambia por detrás**. Lo
         que se firmó sigue siendo lo que se firmó (`firma_que_sigue_valiendo`, con sus bytes idénticos)
         y la corrección queda como una revisión nueva. El contrato lo pide en A14: «editar registro
         firmado → revisión nueva, firma antigua verificable y bytes idénticos».
    """
    original = normaliza_trabajo(trabajo)
    cambios = dict(cambios or {})
    devuelto: dict[str, Any] = {
        "corregido": False,
        "motivo_codigo": "",
        "trabajo": original,
        "cambios": {},
        "revisado": False,
        "hay_que_tocar_el_almacen": False,
        "consumos_que_hay_que_anular": [],
        "consumos_que_hay_que_apuntar": [],
        "lo_firmado_no_se_toca": bool(original.get("firmado")),
        "firma_que_sigue_valiendo": None,
        "revision_nueva": None,
    }
    if origen_que_no_se_corrige(original):
        # Un plan no se «corrige»: se reprograma o se cancela. Y un hecho anulado tampoco: para eso está
        # volver a apuntarlo, que es lo que dice la frase de `TJ3`.
        devuelto["motivo_codigo"] = (
            "TJ17_un_plan_no_es_un_trabajo"
            if original.get("de_donde") == "previsto"
            else "TJ3_el_apunte_esta_anulado"
        )
        return devuelto

    nuevo = dict(original)
    antes_y_ahora: dict[str, list] = {}
    for campo, valor in cambios.items():
        if campo not in CAMPOS_DE_UN_TRABAJO:
            continue
        if campo in ("id", "de_donde", "anulado", "motivo_anulacion", "firmado", "firma_huella"):
            # Lo que no se toca corrigiendo: de qué fila es, si está anulado (corregir no resucita un
            # apunte anulado) y la firma, que es la prueba de lo que había.
            continue
        viejo = nuevo.get(campo)
        if viejo == valor:
            continue
        antes_y_ahora[campo] = [_como_json(viejo), _como_json(valor)]
        nuevo[campo] = valor
    if not antes_y_ahora:
        # Corregir sin cambiar nada no es un cambio: no se apunta en el rastro ni se toca el almacén.
        return devuelto

    nuevo["revisado"] = True
    devuelto["corregido"] = True
    devuelto["revisado"] = True
    devuelto["cambios"] = antes_y_ahora
    devuelto["trabajo"] = nuevo
    devuelto["motivo"] = (motivo or "").strip()[:500] or None

    # ¿Hay que mover el almacén? Solo si lo que cambia es lo que salió: la cantidad, la unidad, el
    # envase, el artículo o el día. Un cambio de horas, de hectáreas o de observaciones no toca nada.
    de_lo_que_sale = {"cantidad", "unidad", "lote_id", "articulo_id", "fecha"}
    if de_lo_que_sale & set(antes_y_ahora):
        devuelto["hay_que_tocar_el_almacen"] = True
        devuelto["consumos_que_hay_que_anular"] = [
            {**insumo, "motivo_codigo": "TJ4_lo_que_salio_cambio"}
            for insumo in original["insumos"]
            if not insumo.get("anulado")
        ]
        # **La clave de reenvío no viaja a la salida nueva**: si viajara, el movimiento nuevo chocaría
        # con el viejo y la puerta del almacén lo daría por repetido, y el trabajo corregido se quedaría
        # sin descontar nada. Es el defecto que el T10 encontró en la siembra, con su comentario.
        devuelto["consumos_que_hay_que_apuntar"] = [
            {**insumo, "clave_de_reenvio": None} for insumo in nuevo["insumos"]
        ]

    if original.get("firmado"):
        # **Lo firmado no se cambia: se revisa.** La revisión nueva es la que lleva los cambios, y la
        # firma antigua sigue valiendo para lo que se firmó, que es lo que hace que siga sirviendo en
        # una inspección.
        devuelto["firma_que_sigue_valiendo"] = {
            "huella": original.get("firma_huella"),
            "entidad_id": original.get("firma_entidad_id") or original.get("id"),
            "firmado_en": original.get("firmado_en"),
            "bytes_identicos": True,
            "motivo_codigo": "TJ19_la_revision_de_lo_firmado",
        }
        revision = dict(nuevo)
        revision["revisado"] = True
        revision["revision_de"] = original.get("id")
        devuelto["revision_nueva"] = revision
    return devuelto


def origen_que_no_se_corrige(trabajo: Mapping[str, Any] | None) -> bool:
    """Si esto no es un hecho que se pueda corregir: un plan, o algo ya anulado."""
    return (trabajo or {}).get("de_donde") == "previsto" or esta_anulado(trabajo)


def se_puede_borrar(trabajo: Mapping[str, Any] | None) -> tuple[bool, str]:
    """Si este apunte se puede borrar y, si no, por qué. **Lo firmado no se borra: se anula.**

    Es la regla que ya tiene el programa (`correcciones.borrar` y `models.Firma`): la firma es la prueba
    de lo que había en un momento dado, y borrar lo firmado dejaría la firma apuntando a algo que ya no
    existe —parecería que el cuaderno está respaldado cuando no lo está—. Lo que sí se puede hacer,
    siempre, es anularlo: queda tachado, con su motivo, y la firma sigue cuadrando.
    """
    if bool((trabajo or {}).get("firmado")):
        return False, "TJ10_lo_firmado_no_se_borra"
    return True, ""


# --------------------------------------------------------------------------
# Los consumos: qué cuenta, qué no, y qué se ha repetido
# --------------------------------------------------------------------------


def consumos_que_cuentan(
    trabajos: Iterable[Mapping[str, Any]] | None,
    consumos: Iterable[Mapping[str, Any]] | None,
) -> dict:
    """Qué salidas del almacén cuentan, cuáles no y por qué, y lo que suman.

    **Esta es la función donde se ve que anular no duplica consumos y que lo previsto no gasta.** Una
    salida cuenta cuando se cumplen las tres cosas:

      1. **Su apunte existe y acredita trabajo hecho.** Si el apunte está anulado, la salida deja de
         contar (el movimiento sigue en el libro, con su fecha y su autor, y no cuenta: eso es «anular
         devuelve lo que salió»). Si el apunte es un plan, la salida no debería existir siquiera —un
         plan no gasta— y si existe se queda fuera, con su motivo, en vez de contarla.
      2. **No está anulada ella misma.**
      3. **No es la segunda salida del mismo apunte y el mismo envase.** Dos vivas del mismo apunte y
         envase es un apunte repetido —el móvil que reintenta, un botón pulsado dos veces—, y contarlas
         las dos es descontar dos veces lo mismo. Se cuenta la primera y las demás se devuelven en
         `repetidos`, dichas, sin borrarlas.

    `por_articulo` da la suma **por artículo**, y no se da a medias: si falta una cantidad o hay dos
    unidades, la suma es `None` con su motivo (`saldo_de_los_consumos`).
    """
    del_cuaderno = normaliza_trabajos(trabajos)
    indice: dict[tuple[str, Any], dict] = {}
    for trabajo in del_cuaderno:
        de_donde = trabajo.get("de_donde")
        if de_donde and trabajo.get("id") is not None:
            indice[(de_donde, trabajo.get("id"))] = trabajo

    cuentan: list[dict] = []
    no_cuentan: list[dict] = []
    repetidos: list[dict] = []
    vistos: set[tuple] = set()
    de_otros: list[dict] = []
    for fila in consumos or []:
        consumo = normaliza_insumo(fila)
        de_donde = DE_DONDE_SALE_UN_APUNTE.get(str(consumo.get("origen_tipo") or ""))
        if de_donde is None:
            # Una salida de otro sitio (un tratamiento, un abono, una siembra). No es de este ticket y
            # **no se tira**: se devuelve aparte, para que quien sume sepa que hay más libro.
            de_otros.append(consumo)
            continue
        trabajo = indice.get((de_donde, consumo.get("origen_id")))
        if trabajo is None:
            no_cuentan.append({**consumo, "motivo_codigo": "TJ26_el_apunte_del_consumo_no_esta"})
            continue
        if consumo.get("anulado"):
            no_cuentan.append({**consumo, "motivo_codigo": "TJ3_el_apunte_esta_anulado"})
            continue
        if not acredita_un_trabajo_hecho(trabajo):
            _, porque = consume_existencias(trabajo)
            no_cuentan.append({**consumo, "motivo_codigo": porque})
            continue
        llave = (
            de_donde,
            consumo.get("origen_id"),
            consumo.get("lote_id"),
            consumo.get("articulo_id"),
        )
        if llave in vistos:
            repetidos.append({**consumo, "motivo_codigo": "TJ11_el_trabajo_ya_estaba"})
            continue
        vistos.add(llave)
        cuentan.append(consumo)

    por_articulo: dict[str, list[dict]] = {}
    for consumo in cuentan:
        clave = str(consumo.get("articulo_id") or consumo.get("articulo") or "sin_articulo")
        por_articulo.setdefault(clave, []).append(consumo)
    resumen: dict[str, dict] = {}
    for clave, lista in por_articulo.items():
        resumen[clave] = {
            **saldo_de_los_consumos(lista),
            "articulo": lista[0].get("articulo"),
            "lotes": sorted({c.get("lote_id") for c in lista if c.get("lote_id") is not None}),
        }

    return {
        "cuentan": cuentan,
        "cuantos_cuentan": len(cuentan),
        "no_cuentan": no_cuentan,
        "repetidos": repetidos,
        "de_otros_apuntes": de_otros,
        "por_articulo": resumen,
        "sin_decir": len([c for c in cuentan if c.get("cantidad") is None]),
    }


def quita_los_reenvios(trabajos: Iterable[Mapping[str, Any]] | None) -> dict:
    """Quita los reenvíos del móvil: **la misma petición dos veces es un trabajo, no dos**.

    La cola del móvil reintenta al volver la cobertura y un botón se pulsa dos veces. La clave de
    reenvío (`clave_de_reenvio`, que en el resto del programa ya existe para tratamientos, albaranes y
    movimientos) es lo que permite reconocerlo. Se queda **el primero** y los demás se devuelven en
    `reenviados`, con su identificador, en vez de desaparecer sin decirlo.

    Y lo que **no se puede comprobar se dice**: un trabajo sin clave no se puede reconocer como repetido,
    así que se cuenta en `sin_clave` con su código. Dar por bueno que no está duplicado porque no hay
    con qué comprobarlo es lo mismo que inventarse el dato.
    """
    vistos: dict[str, dict] = {}
    unicos: list[dict] = []
    reenviados: list[dict] = []
    sin_clave = 0
    for trabajo in normaliza_trabajos(trabajos):
        clave = (trabajo.get("clave_de_reenvio") or trabajo.get("id_local") or "").strip()
        if not clave:
            sin_clave += 1
            unicos.append(trabajo)
            continue
        if clave in vistos:
            reenviados.append(
                {
                    "trabajo": trabajo,
                    "de_la_clave_de": vistos[clave].get("id"),
                    "motivo_codigo": "TJ11_el_trabajo_ya_estaba",
                }
            )
            continue
        vistos[clave] = trabajo
        unicos.append(trabajo)
    return {
        "trabajos": unicos,
        "cuantos": len(unicos),
        "reenviados": reenviados,
        "cuantos_reenviados": len(reenviados),
        "sin_clave": sin_clave,
        "sin_clave_porque_codigo": (
            "TJ12_no_se_pudo_comprobar_si_ya_estaba" if sin_clave else ""
        ),
    }


# --------------------------------------------------------------------------
# Lo que este ticket no hace, dicho en el dato y no en un comentario
# --------------------------------------------------------------------------

# Lo mismo que `maquinaria.QUE_FALTA` y `iuws.QUE_FALTA`: lo que el programa no sabe se **declara** con
# lo que es, para qué hace falta y de quién depende, y eso viaja a la pantalla. Un hueco que no se dice
# se convierte en un hueco que alguien rellena con lo que le parece.
QUE_FALTA: tuple[dict, ...] = (
    {
        "codigo": "T15_sin_fuente_de_lluvia",
        "que_es": "La lluvia de cada tierra y cada día.",
        "para_que": (
            "Para poder enseñar lo que ha llovido junto al historial de la tierra. Hoy se puede apuntar "
            "a mano, y una estación no dice nada del cultivo."
        ),
        "de_quien_depende": (
            "De elegir y contratar una estación o un proveedor: es el T17, que está bloqueado por eso."
        ),
    },
    {
        "codigo": "T15_sin_nascencia_medida",
        "que_es": "Si la planta ha nacido, medido.",
        "para_que": (
            "Hoy la nascencia solo se apunta si alguien la ha visto en el campo. De la lluvia no se "
            "deduce, y de una foto de satélite tampoco sin más (T18)."
        ),
        "de_quien_depende": "De una observación de campo, hoy a mano.",
    },
    {
        "codigo": "T15_sin_horas_del_cuenta_horas",
        "que_es": "Las horas del cuenta-horas de la máquina al hacer un trabajo.",
        "para_que": "Para poder cruzar las horas del trabajo con las del cuenta-horas de la máquina.",
        "de_quien_depende": "De que el agricultor las apunte; el programa ya guarda las horas del trabajo.",
    },
    {
        "codigo": "T15_sin_panel_de_costes",
        "que_es": "Lo que ha costado cada trabajo.",
        "para_que": "Para los paneles con cifras contrastadas (T19), que no se empiezan antes que esto.",
        "de_quien_depende": "De T13 (gastos y repartos), que es otro ticket.",
    },
)


def fichero_de_codigos() -> dict[str, str]:
    """Los códigos que este módulo puede devolver, con su frase. Es lo que el ticket pide entregar.

    Se expone como función para que las pruebas puedan comprobarlo: hay una que exige que **todo** código
    que aparece en este fichero esté en `CODIGOS_QUE_SE_DICEN` (nada puede salir sin frase) y otra que
    exige que ninguno sobre. Un código sin frase no revienta: sale un hueco en la pantalla, que es el
    fallo que este proyecto ya ha tenido tres veces.
    """
    return dict(CODIGOS_QUE_SE_DICEN)


def _fecha_texto(valor: Any) -> str | None:
    fecha = como_fecha(valor)
    if fecha is not None:
        return fecha.isoformat()
    return str(valor) if valor else None


def _como_json(valor: Any) -> Any:
    """Un valor en algo que se pueda escribir en el rastro (que es una columna JSON)."""
    if isinstance(valor, (dt.date, dt.datetime)):
        return valor.isoformat()
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    return str(valor)
