"""La maquinaria de la finca: qué máquinas hay, qué le toca a cada una y qué no se sabe.

POR QUÉ ESTE FICHERO EXISTE

`EquipoAplicacion` es **una máquina de echar producto** —el pulverizador, el atomizador, la
mochila—, y existe para rellenar la hoja 1.3 del cuaderno de la Junta y para decir con qué se
echó cada tratamiento. **No es «la maquinaria de la finca»**, y el contrato lo dice por su nombre
(§9: «`EquipoAplicacion` no cubre toda la maquinaria»): un apero, un remolque o la cosechadora no
caben ahí, y además dar de alta un remolque como «equipo de aplicación» habría acabado pidiéndole
un número de ROMA y una ITEAF que no tiene. Por eso hay un registro nuevo (`models.Maquina`) y el
de echar producto se **enlaza** desde él cuando la máquina es la misma, en vez de duplicarla a
ciegas. Lo que queda del cuaderno —la hoja 1.3 y `equipo_id` de tratamientos y labores— sigue
funcionando igual: no se ha tocado.

LA TRAMPA DEL TICKET, QUE ES EL MOTIVO DE CASI TODO LO QUE HAY AQUÍ

El contrato dice, literal: «No calcular plazo solo por "tractor" o "sulfatadora"; pedir la
clasificación técnica necesaria». Traducido a código: **en este fichero no hay ni una línea que
deduzca qué inspección le toca a una máquina por su nombre, su clase o su marca.** Lo que hay es
justo lo contrario:

  · La **aplicabilidad** de cada obligación (ITV, ITEAF, mantenimiento, seguro y ROMA) la declara
    el agricultor, y se guarda con **tres estados** (`si`, `no`, `no_se`). Sin declarar nada vale
    `no_se` («no se sabe»), **nunca «no le hace falta»**: ese es exactamente el valor por defecto
    permisivo que este ticket no puede repetir, porque convierte «no lo sé» en «cumple».
  · La **clasificación técnica** se pide y se guarda tal cual, en texto. El programa no tiene
    transcrita la regla que dice qué clasificación lleva cada máquina (es el trabajo legal **L07**
    de `docs/MATRIZ_NORMATIVA_CRM.md`, y sigue pendiente), así que **no la supone**.
  · La **próxima fecha** de una inspección es **la que dice el papel**, copiada. No se calcula
    sumando un plazo a la última: sin la fuente del plazo, una fecha calculada es un dato
    inventado con la misma cara que uno verdadero, y el agricultor se entera el día que se la
    piden. Cuando no hay fecha, se dice que no se sabe y qué falta para saberlo.
  · El **resultado** de una inspección tiene tres estados y el de partida es `no_consta`, no
    `favorable`: una inspección apuntada hoy sin decir cómo salió no es una máquina que pasó.

Y el **aviso de que no se sabe**: cuando una obligación aplica y no hay ni una inspección
apuntada, el programa no enseña una fecha ni se calla: dice que no lo sabe y pide la clasificación
técnica y la fecha del papel. Ese es el «lo dice y lo pregunta» del contrato.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
import datetime as dt
import math

# --------------------------------------------------------------------------
# Las cinco obligaciones, y sus estados
# --------------------------------------------------------------------------

# **Las cinco que la ficha tiene que separar** (contrato §4, S16): ITV, ITEAF, mantenimiento,
# seguro y ROMA. El orden es el de la ficha y **no se saca de las claves de un diccionario**: aquí
# se eligen cinco cosas que se parecen mucho, y unos botones que cambian de sitio se pulsan mal.
#
# Y no son la misma cosa: la **ITV** es la inspección técnica del vehículo, la **ITEAF** es la
# inspección de los equipos de aplicación de productos, el **mantenimiento** es lo que hace el
# agricultor por su cuenta, el **seguro** es un contrato y el **ROMA** es la inscripción en el
# registro oficial de maquinaria. El propio documento de la casa lo avisa: «No llamar a ITEAF
# "ITV" en las etiquetas» (`docs/MATRIZ_NORMATIVA_CRM.md`, N09).
OBLIGACIONES: tuple[str, ...] = ("itv", "iteaf", "mantenimiento", "seguro", "roma")

# Los tres estados de la aplicabilidad. `NO_SE` es el de partida **a propósito**: ver la cabecera.
SI = "si"
NO = "no"
NO_SE = "no_se"
APLICABILIDADES: tuple[str, ...] = (SI, NO, NO_SE)

# De dónde sale lo que el agricultor ha declarado sobre la aplicabilidad. Existe porque una
# declaración sin origen no vale nada el día de una inspección: no es lo mismo «lo dice el papel
# de la ITV» que «me lo parece a mí».
ORIGEN_EL_PAPEL = "documento"
ORIGEN_EL_AGRICULTOR = "el_agricultor"
ORIGENES_DE_LA_APLICABILIDAD: tuple[str, ...] = (
    ORIGEN_EL_PAPEL,
    ORIGEN_EL_AGRICULTOR,
    NO_SE,
)

# Cómo salió una inspección. `NO_CONSTA` **no** es `FAVORABLE`: una inspección apuntada sin decir
# el resultado deja la máquina en «no se sabe», que es lo que es.
FAVORABLE = "favorable"
DESFAVORABLE = "desfavorable"
NO_CONSTA = "no_consta"
RESULTADOS_DE_UNA_INSPECCION: tuple[str, ...] = (FAVORABLE, DESFAVORABLE, NO_CONSTA)

# De quién es la máquina: **propiedad o alquiler**, que es lo que pide la tabla del contrato.
PROPIA = "propia"
ALQUILADA = "alquilada"
PROPIEDADES: tuple[str, ...] = (PROPIA, ALQUILADA, NO_SE)

# Si se puede contar con ella para trabajar. Tres estados otra vez, y `NO_SE` de partida: una
# máquina de la que nadie ha dicho nada no está «disponible», está «sin decir».
DISPONIBLE = "disponible"
NO_DISPONIBLE = "no_disponible"
DISPONIBILIDADES: tuple[str, ...] = (DISPONIBLE, NO_DISPONIBLE, NO_SE)

# **La clase de máquina es NUESTRA y no sirve para calcular nada.** Es lo que agrupa la tabla y lo
# que permite decir «tractor» o «remolque» en una lista. La clasificación que decide qué
# inspecciones le tocan es la **clasificación técnica**, que se pide aparte y se guarda tal cual:
# son dos campos distintos justo para que nadie pueda usar esta lista como si fuera la otra.
CLASES_DE_MAQUINA: tuple[str, ...] = (
    "tractor",
    "remolque",
    "apero",
    "cosechadora",
    "equipo_de_aplicacion",
    "otro",
)

# Cuando una inspección está a punto de vencer se avisa con dos meses: es el margen que da tiempo a
# pedir cita y a que la máquina esté libre (una ITV agrícola no se pasa el mismo día). Se escribe
# aquí, con su motivo, y **no se usa para calcular ninguna fecha**: solo para decir «esto está al
# caer» de una fecha que ya existía.
DIAS_DE_AVISO_ANTES_DE_VENCER = 60

# Las situaciones en que puede estar una obligación. Se devuelven como código y las palabras las
# pone `textos.py`, como todo lo que lee el agricultor.
SITUACION_NO_SE_SI_TOCA = "no_se_si_toca"
SITUACION_NO_APLICA = "no_aplica"
SITUACION_SIN_INSPECCION = "sin_inspeccion"
# Hay una fecha de la próxima escrita **y ninguna inspección apuntada**: se sabe cuándo toca y no cuándo
# fue la última. Es el caso del equipo del cuaderno que traía la fecha de la próxima ITEAF sin la de la
# última, y es distinto de «no hay nada apuntado».
SITUACION_SIN_LA_ULTIMA = "sin_la_ultima"
SITUACION_NO_FAVORABLE = "no_favorable"
SITUACION_SIN_FECHA = "sin_fecha"
SITUACION_VENCIDA = "vencida"
SITUACION_PROXIMA = "proxima"
SITUACION_VIGENTE = "vigente"


# --------------------------------------------------------------------------
# De dónde sale cada obligación, y lo que falta para poder calcular plazos
# --------------------------------------------------------------------------
#
# **Esto es la «fuente» que pide el contrato, y se dice entera: la que tenemos y la que no.** De
# las cinco obligaciones, de dos tenemos la norma localizada (los dos reales decretos que cita la
# matriz normativa), de una tenemos el sitio donde se pide el dato (la hoja 1.3 del cuaderno de la
# Junta) y de dos **no tenemos ninguna norma transcrita**, así que se dice eso mismo en vez de
# rellenarlo con algo que suene bien. Y en las cinco falta lo mismo: **el plazo** (cada cuánto
# toca), que depende de la clasificación técnica de cada máquina y es el trabajo legal **L07**, que
# sigue pendiente. Por eso el programa no calcula ninguna fecha de vencimiento: la que enseña es la
# que trae el papel.
FUENTE_DE_LA_OBLIGACION: dict[str, dict] = {
    "itv": {
        "norma": "Real Decreto 920/2017, la inspección técnica de los vehículos agrícolas",
        "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2017-12841",
        "que_falta": (
            "Cada cuánto toca la ITV depende de la clasificación técnica de la máquina, y esa "
            "tabla no está transcrita en el programa, así que no se calcula: se copia la fecha "
            "que traiga tu papel."
        ),
    },
    "iteaf": {
        "norma": "Real Decreto 1702/2011, la inspección de los equipos de aplicación",
        "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2011-19296",
        "que_falta": (
            "Qué equipos están obligados y cada cuánto, por su clasificación técnica, tampoco "
            "está transcrito: se copia la fecha del certificado de la inspección."
        ),
    },
    "roma": {
        "norma": "La hoja 1.3 del cuaderno de la Junta pide el nº de inscripción en el ROMA",
        "url": None,
        "que_falta": (
            "La norma que obliga a inscribir una máquina en el ROMA y con qué clasificación no "
            "está transcrita aquí. El número se guarda tal cual lo escribas."
        ),
    },
    "mantenimiento": {
        "norma": None,
        "url": None,
        "que_falta": (
            "No tenemos ninguna norma transcrita que obligue a un mantenimiento con plazo. Esto "
            "es lo que tú decides: se apunta la fecha que tú pongas y se avisa cuando llegue."
        ),
    },
    "seguro": {
        "norma": None,
        "url": None,
        "que_falta": (
            "No tenemos transcrita la norma del seguro, y el de circulación y el de la cosecha "
            "no son lo mismo, así que no se mezclan: se apunta la fecha de tu póliza."
        ),
    },
}

# **Lo que el programa NO puede hacer todavía, dicho para que se lea en la pantalla** (la receta
# de `AGENTS.md`: lo que falta se declara con lo que es, para qué hace falta y de quién depende).
QUE_FALTA: tuple[dict, ...] = (
    {
        "clave": "plazos_de_las_inspecciones",
        "que": "Cada cuánto toca pasar la ITV y la ITEAF, por clasificación técnica de la máquina.",
        "para_que": (
            "Poder calcular la próxima fecha en vez de copiarla del papel, y avisar de un "
            "vencimiento que no esté escrito en ningún sitio."
        ),
        "de_quien_depende": (
            "Es el trabajo legal L07 de la matriz normativa (clasificación ITV/ITEAF por máquina "
            "real). Hasta que esté transcrito con su fuente, el programa no calcula fechas."
        ),
    },
    {
        "clave": "clasificacion_tecnica_de_cada_maquina",
        "que": "La clasificación técnica que le corresponde a cada máquina de verdad.",
        "para_que": "Saber qué obligaciones le aplican sin preguntárselo al agricultor.",
        "de_quien_depende": (
            "De la revisión legal L07 y de los papeles de la máquina (la ficha del ROMA o el "
            "certificado de la última inspección). Mientras no esté, lo pide la pantalla."
        ),
    },
)


# --------------------------------------------------------------------------
# Las inspecciones
# --------------------------------------------------------------------------


def _fecha(valor) -> dt.date | None:
    """La fecha de un campo, admitiendo el objeto, el texto ISO y el vacío."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    try:
        return dt.date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def inspecciones_que_cuentan(inspecciones) -> list:
    """Las inspecciones que se miran: todas menos las anuladas.

    Una inspección anulada sigue en el cuaderno (nada se borra sin rastro), pero **no cuenta** ni
    para la última inspección ni para la próxima fecha: si contara, anular una inspección apuntada
    por error no arreglaría nada.
    """
    return [una for una in (inspecciones or []) if not getattr(una, "anulado", False)]


def ultima_inspeccion(inspecciones, tipo: str | None = None):
    """La inspección más nueva, por la **fecha de la inspección** (no la del apunte).

    La fecha del papel manda: una inspección de marzo apuntada en junio es de marzo. Y si hay dos
    el mismo día, gana la última que se apuntó, que es la que el agricultor tenía delante.
    """
    candidatas = [
        una
        for una in inspecciones_que_cuentan(inspecciones)
        if tipo is None or getattr(una, "tipo", None) == tipo
    ]
    if not candidatas:
        return None
    return max(candidatas, key=lambda una: (_fecha(una.fecha) or dt.date.min, una.id or 0))


def inspecciones_de(inspecciones, tipo: str) -> list:
    """Todas las inspecciones de una obligación, de la más nueva a la más vieja."""
    suyas = [una for una in inspecciones_que_cuentan(inspecciones) if getattr(una, "tipo", None) == tipo]
    return sorted(suyas, key=lambda una: (_fecha(una.fecha) or dt.date.min, una.id or 0), reverse=True)


def resultado_de(inspeccion) -> str:
    """Cómo salió una inspección, con `no_consta` cuando no se ha dicho.

    **No se devuelve `favorable` por defecto en ningún caso.** Es el mismo cuidado que con la
    aplicabilidad: una inspección sin resultado es una inspección de la que no se sabe cómo salió.
    """
    if inspeccion is None:
        return NO_CONSTA
    return getattr(inspeccion, "resultado", None) or NO_CONSTA


# --------------------------------------------------------------------------
# El estado de una obligación
# --------------------------------------------------------------------------


def estado_de_una_obligacion(
    tipo: str,
    *,
    obligacion=None,
    inspecciones=(),
    referencia: dt.date | None = None,
) -> dict:
    """Todo lo que la ficha tiene que enseñar de una obligación, ya decidido.

    Devuelve, para la obligación `tipo` de una máquina:

      · `aplicabilidad` — `si`, `no` o `no_se`, y su `fuente`. **Sin fila guardada es `no_se`**:
        nadie ha dicho nada, y eso no es «no le aplica».
      · `ultima_inspeccion`, `resultado`, `proxima_fecha` y `trae_papel` — la última inspección de
        esa obligación, **con la fecha que traía el papel**: aquí no se calcula ni un día.
      · `situacion` — el estado, en un código que `textos.py` convierte en palabras.
      · `dias` — los días que quedan hasta la próxima fecha apuntada, o `None` si no hay fecha.
      · `fuente` — de dónde sale la obligación (la norma que tenemos, o lo que falta).
      · `decidido_por_usuario_id` y `decidido_en` — **quién lo decidió y cuándo**, tal cual salen de
        la fila. **El nombre no se resuelve aquí**: esta función es pura y no tiene base de datos, así
        que el nombre lo pone el router (CRM-07 #6, 14/10/2026).

    La `situacion` se decide **solo con lo que está apuntado**: la aplicabilidad, el resultado y la
    fecha del papel. Ni el nombre de la máquina, ni su clase, ni su marca entran aquí — y hay una
    prueba que lo exige, porque es la trampa que el contrato señala.
    """
    referencia = referencia or dt.date.today()
    aplicabilidad = getattr(obligacion, "aplicabilidad", None) or NO_SE
    if aplicabilidad not in APLICABILIDADES:
        aplicabilidad = NO_SE

    ultima = ultima_inspeccion(inspecciones, tipo)
    resultado = resultado_de(ultima)
    # **La fecha puede venir de dos sitios, y los dos son del agricultor**: de la última inspección
    # apuntada, o de la obligación (el caso del equipo del cuaderno que traía la fecha de la próxima
    # sin la de la última). No hay un tercero: no se calcula ninguna.
    proxima = _fecha(getattr(ultima, "proxima_fecha", None)) if ultima else None
    de_la_obligacion = False
    if proxima is None and obligacion is not None:
        declarada = _fecha(getattr(obligacion, "proxima_fecha_declarada", None))
        if declarada is not None:
            proxima = declarada
            de_la_obligacion = True
    documento = getattr(ultima, "documento_id", None) if ultima else None

    if aplicabilidad == NO_SE:
        situacion = SITUACION_NO_SE_SI_TOCA
    elif aplicabilidad == NO:
        situacion = SITUACION_NO_APLICA
    elif ultima is None and de_la_obligacion:
        # Hay una fecha de la próxima y **no hay ninguna inspección apuntada**: se sabe cuándo toca y no
        # se sabe cuándo fue la última. Decirlo así es lo único honesto, y es distinto de «no hay nada
        # apuntado» (que es lo que decía antes y hacía desaparecer la fecha del agricultor).
        situacion = SITUACION_SIN_LA_ULTIMA
    elif ultima is None:
        situacion = SITUACION_SIN_INSPECCION
    elif resultado == DESFAVORABLE:
        # Manda lo que dice el papel: si la última salió desfavorable, la máquina no está en
        # regla aunque traiga una fecha futura, y decirlo es lo único honesto.
        situacion = SITUACION_NO_FAVORABLE
    elif proxima is None:
        situacion = SITUACION_SIN_FECHA
    elif proxima < referencia:
        situacion = SITUACION_VENCIDA
    elif (proxima - referencia).days <= DIAS_DE_AVISO_ANTES_DE_VENCER:
        situacion = SITUACION_PROXIMA
    else:
        situacion = SITUACION_VIGENTE

    return {
        "tipo": tipo,
        "aplicabilidad": aplicabilidad,
        "origen_de_la_aplicabilidad": getattr(obligacion, "origen", None) or NO_SE,
        "notas": getattr(obligacion, "notas", None),
        "situacion": situacion,
        # La inspección entera, tal cual: la ficha enseña su fecha y su papel, y quien la lea ve lo
        # que hay apuntado sin que nadie lo haya resumido.
        "ultima_inspeccion": ultima,
        "resultado": resultado,
        # **Tal cual venía del papel.** Nunca una fecha sumada por el programa.
        "proxima_fecha": proxima,
        "dias": (proxima - referencia).days if proxima else None,
        "documento_id": documento,
        "trae_papel": documento is not None,
        # **Y el papel de la APLICABILIDAD, que es otra cosa que el de la última inspección**
        # (CRM-07, 14/10/2026). Este dice **por qué se sabe que la obligación le toca** —la ficha del
        # ITV, el papel que trajo el agricultor—; el `documento_id` de arriba es el de la **última
        # inspección**, que dice **cómo salió**. Se llaman distinto a propósito: si compartieran nombre,
        # la ficha enseñaría un papel creyendo que es el otro, y los dos son plausibles.
        "documento_de_la_aplicabilidad_id": getattr(obligacion, "documento_id", None),
        "la_aplicabilidad_trae_papel": getattr(obligacion, "documento_id", None) is not None,
        # **De cuándo es esa evidencia**, que no es cuándo se apuntó (eso es `creado_en`, y no sale).
        "fecha_de_la_evidencia": getattr(obligacion, "fecha_de_la_evidencia", None),
        # **Quién lo decidió y el día que lo dijo** (CRM-07 #6, 14/10/2026). Salen **tal cual están
        # en la fila**: aquí se devuelve el identificador y **no se resuelve el nombre**, porque esta
        # función es pura y no tiene base de datos; el nombre lo pone el router, que es quien puede
        # leer `Usuario` (ver `_quien_lo_decidio` en `routers/maquinaria_api.py`). Y `decidido_en` no
        # es `creado_en`: esa es cuándo se apuntó esto; esta, el día en que se decidió.
        "decidido_por_usuario_id": getattr(obligacion, "decidido_por_usuario_id", None),
        "decidido_en": getattr(obligacion, "decidido_en", None),
        # **Una fecha que ya pasó es un hecho, y se dice aunque nadie haya declarado si le toca.** Si el
        # agricultor escribió «próxima: 12/05/2024» y esa fecha pasó, esconderlo porque falta por
        # contestar otra pregunta es dejarle comparar fechas de cabeza (lo encontró la revisión del
        # ticket). Lo único que NO se hace es decir que le toca: eso sigue en «no lo sé».
        "fecha_pasada": bool(proxima is not None and proxima < referencia),
        "fuente": FUENTE_DE_LA_OBLIGACION.get(tipo, {"norma": None, "url": None, "que_falta": ""}),
    }


def estado_de_todas_las_obligaciones(
    *,
    obligaciones=(),
    inspecciones=(),
    referencia: dt.date | None = None,
) -> dict[str, dict]:
    """Las cinco obligaciones de una máquina, en el orden de la ficha.

    Las que no tienen fila guardada salen igualmente, con `no_se`: **la ficha enseña siempre las
    cinco**, que es como el agricultor se entera de que existen las cinco. Si solo salieran las
    declaradas, una máquina nueva tendría una ficha vacía y nadie sabría qué hay que contestar.
    """
    por_tipo = {getattr(una, "tipo", None): una for una in (obligaciones or [])}
    return {
        tipo: estado_de_una_obligacion(
            tipo,
            obligacion=por_tipo.get(tipo),
            inspecciones=inspecciones,
            referencia=referencia,
        )
        for tipo in OBLIGACIONES
    }


# --------------------------------------------------------------------------
# Los avisos (antes de coger la máquina, y en la lista)
# --------------------------------------------------------------------------


def _aviso(codigo: str, tipo: str, *, urgente: bool = False, **datos) -> dict:
    """Un aviso, con su código y sus datos. Las palabras las pone `textos.py`.

    La regla de la casa vale aquí igual: el aviso dice **qué pasa y qué hacer ahora**, y el texto
    se pide por código (`textos.mensaje`), nunca se escribe en el router.
    """
    return {"codigo": codigo, "tipo": tipo, "urgente": urgente, "datos": datos}


def avisos_de_una_maquina(
    *,
    maquina,
    obligaciones=(),
    inspecciones=(),
    averias=(),
    referencia: dt.date | None = None,
) -> list[dict]:
    """Lo que hay que saber de esta máquina antes de contar con ella.

    Salen tres familias de avisos, y el orden es el de urgencia:

      1. **No se puede trabajar con ella** — su disponibilidad dice que no, o tiene una avería sin
         resolver apuntada.
      2. **Una obligación vencida o al caer** — con la fecha que traía el papel, jamás una
         calculada. Y una inspección desfavorable cuenta como vencida, porque lo está.
      3. **Lo que no se sabe** — de una obligación que aplica no hay ni inspección, no trae fecha o
         no se ha declarado si aplica. Esto **no es un aviso rojo**: es la petición de un dato, con
         la clasificación técnica delante, que es lo que el contrato manda pedir.

    `maquina` puede ser `None` (una máquina que no está en la lista), y entonces solo se cuentan
    las obligaciones: la pantalla del inventario enseña esas igual.
    """
    referencia = referencia or dt.date.today()
    avisos: list[dict] = []
    nombre = getattr(maquina, "nombre", "") if maquina is not None else ""

    if maquina is not None:
        disponibilidad = getattr(maquina, "disponibilidad", None) or NO_SE
        if disponibilidad == NO_DISPONIBLE:
            avisos.append(
                _aviso(
                    "M1_la_maquina_no_esta_disponible",
                    "disponibilidad",
                    urgente=True,
                    maquina=nombre,
                )
            )
        elif disponibilidad == NO_SE:
            avisos.append(
                _aviso("M2_no_se_si_esta_disponible", "disponibilidad", maquina=nombre)
            )

        for averia in averias or []:
            if getattr(averia, "anulado", False):
                continue
            if getattr(averia, "resuelta", None) is False:
                avisos.append(
                    _aviso(
                        "M3_tiene_una_averia_sin_arreglar",
                        "averia",
                        urgente=True,
                        maquina=nombre,
                        fecha=formatea(_fecha(getattr(averia, "fecha", None))),
                        que=getattr(averia, "que_paso", "") or "",
                    )
                )

    estados = estado_de_todas_las_obligaciones(
        obligaciones=obligaciones, inspecciones=inspecciones, referencia=referencia
    )
    for tipo, estado in estados.items():
        situacion = estado["situacion"]
        if situacion in (SITUACION_VENCIDA, SITUACION_PROXIMA, SITUACION_NO_FAVORABLE):
            avisos.append(
                _aviso(
                    {
                        SITUACION_VENCIDA: "M4_una_inspeccion_esta_vencida",
                        SITUACION_PROXIMA: "M5_una_inspeccion_caduca_pronto",
                        SITUACION_NO_FAVORABLE: "M6_la_ultima_inspeccion_no_fue_favorable",
                    }[situacion],
                    tipo,
                    urgente=situacion != SITUACION_PROXIMA,
                    maquina=nombre,
                    obligacion=tipo,
                    fecha=formatea(estado["proxima_fecha"]),
                    dias=estado["dias"],
                )
            )
        elif situacion == SITUACION_SIN_INSPECCION:
            avisos.append(
                _aviso(
                    "M7_no_hay_ninguna_inspeccion_apuntada",
                    tipo,
                    maquina=nombre,
                    obligacion=tipo,
                )
            )
        elif situacion == SITUACION_SIN_FECHA:
            avisos.append(
                _aviso(
                    "M8_la_inspeccion_no_trae_la_proxima_fecha",
                    tipo,
                    maquina=nombre,
                    obligacion=tipo,
                )
            )
        elif situacion == SITUACION_SIN_LA_ULTIMA:
            avisos.append(
                _aviso(
                    "M20_esta_la_proxima_pero_no_la_ultima",
                    tipo,
                    maquina=nombre,
                    obligacion=tipo,
                    fecha=formatea(estado["proxima_fecha"]),
                )
            )
        elif situacion == SITUACION_NO_SE_SI_TOCA:
            avisos.append(
                _aviso(
                    "M9_no_se_si_esa_inspeccion_le_toca",
                    tipo,
                    maquina=nombre,
                    obligacion=tipo,
                )
            )
            # **Y si además la fecha que hay escrita ya pasó, se dice.** La fecha es un hecho —la
            # escribió el agricultor— y esconderlo porque falta por contestar otra pregunta le deja
            # comparando fechas de cabeza. Lo que NO se dice es que le toque: eso sigue siendo «no lo sé».
            if estado.get("fecha_pasada"):
                avisos.append(
                    _aviso(
                        "M4_una_inspeccion_esta_vencida",
                        tipo,
                        urgente=True,
                        maquina=nombre,
                        obligacion=tipo,
                        fecha=formatea(estado["proxima_fecha"]),
                        dias=estado["dias"],
                    )
                )

    for estado in estados.values():
        if estado["situacion"] == SITUACION_NO_APLICA and estado["origen_de_la_aplicabilidad"] == NO_SE:
            # «No le aplica» dicho sin decir de dónde sale es una afirmación sin respaldo: no
            # bloquea nada, pero se dice, porque es justo lo que se pregunta en una inspección.
            avisos.append(
                _aviso(
                    "M10_dice_que_no_aplica_sin_decir_de_donde_sale",
                    estado["tipo"],
                    maquina=nombre,
                    obligacion=estado["tipo"],
                )
            )
    return avisos


def avisos_al_planificar(los_avisos) -> list[dict]:
    """Los que importan **antes de coger la máquina para un trabajo**.

    El contrato pide, con estas palabras: «Avisos al planificar trabajo». Son dos familias: que la
    máquina no esté para trabajar (disponibilidad o avería), y que una inspección esté vencida o al
    caer. Los demás avisos —lo que no se sabe— se quedan en la ficha: aquí, delante de un trabajo
    que hay que hacer hoy, lo que hay que decidir es si la máquina puede o no puede.
    """
    return [
        aviso
        for aviso in los_avisos
        if aviso["tipo"] in ("disponibilidad", "averia")
        or aviso["codigo"] in ("M4_una_inspeccion_esta_vencida", "M5_una_inspeccion_caduca_pronto", "M6_la_ultima_inspeccion_no_fue_favorable")
    ]


# --------------------------------------------------------------------------
# Lo que enseña la tabla
# --------------------------------------------------------------------------


def proxima_revision(*, obligaciones=(), inspecciones=(), referencia: dt.date | None = None) -> dict:
    """La fecha más próxima de las que están escritas en un papel, con su obligación.

    **Esto no es un cálculo de plazo**: es elegir, entre las fechas que ya existen, la que llega
    antes, para poder ponerla en la tabla. Se devuelve también `de_las_que_no_se_sabe`, que es
    cuántas obligaciones aplican y no tienen fecha apuntada: sin ese número, la tabla diría «próxima
    revisión: 12/05/2027» y el agricultor creería que con eso está todo mirado.
    """
    estados = estado_de_todas_las_obligaciones(
        obligaciones=obligaciones, inspecciones=inspecciones, referencia=referencia
    )
    con_fecha = [
        (estado["proxima_fecha"], estado["tipo"], estado["situacion"])
        for estado in estados.values()
        if estado["proxima_fecha"] is not None
    ]
    if con_fecha:
        fecha, tipo, situacion = min(con_fecha)
        # **Una fecha que ya pasó manda sobre el «no lo sé» de la obligación** para lo que la tabla dice.
        # Si el agricultor tiene escrito «próxima ITV: 12/05/2024» y esa fecha pasó, la celda lleva la
        # palabra «Vencida» aunque le falte contestar si la ITV le toca: la fecha es un hecho y la
        # palabra avisa de algo que hay que mirar. En la ficha se siguen leyendo las dos cosas (que no
        # se sabe si le toca **y** que la fecha pasó), que es la verdad completa.
        if situacion == SITUACION_NO_SE_SI_TOCA and fecha < (referencia or dt.date.today()):
            situacion = SITUACION_VENCIDA
    else:
        fecha, tipo, situacion = None, None, None
    hoy = referencia or dt.date.today()
    sin_saber = sum(
        1
        for estado in estados.values()
        if estado["situacion"]
        in (SITUACION_SIN_INSPECCION, SITUACION_SIN_FECHA, SITUACION_NO_SE_SI_TOCA)
        # Una obligación «sin declarar» cuya fecha ya pasó **no cuenta como un hueco sin fecha**: tiene
        # fecha, y lo que le falta es la respuesta a si le toca (que es lo que dice M9).
        and not estado.get("fecha_pasada")
    )
    return {
        "fecha": fecha,
        "tipo": tipo,
        # La situación de la obligación que ha dado la fecha, para que la pantalla pueda poner su palabra
        # («Vencida», «Desfavorable») **sin volver a decidirlo por su cuenta**: el margen de «caduca
        # pronto» se decide en un solo sitio, aquí.
        "situacion": situacion,
        "sin_fecha": sin_saber,
        # Si hay alguna obligación vencida, la tabla lo dice aunque haya otra fecha futura. Y cuenta
        # también la fecha que pasó sin que nadie haya declarado si la obligación le toca: es un hecho.
        "vencidas": sum(
            1
            for estado in estados.values()
            if estado["situacion"] == SITUACION_VENCIDA
            or (
                estado["situacion"] == SITUACION_NO_SE_SI_TOCA
                and estado["proxima_fecha"] is not None
                and estado["proxima_fecha"] < hoy
            )
        ),
        "no_favorables": sum(
            1 for estado in estados.values() if estado["situacion"] == SITUACION_NO_FAVORABLE
        ),
    }


def documentacion(*, inspecciones=()) -> dict:
    """Qué papeles hay de las inspecciones, y cuántas se apuntaron **sin papel**.

    El caso que importa es el segundo: el contrato pide que una inspección **sin documento** se
    pueda apuntar y que se diga que no lo trae. Se cuenta para poder decirlo, y no cuenta como
    falta grave: hay máquinas cuyo certificado está en el taller o en el móvil del mecánico.
    """
    vigentes = inspecciones_que_cuentan(inspecciones)
    return {
        "inspecciones": len(vigentes),
        "con_papel": sum(1 for una in vigentes if getattr(una, "documento_id", None) is not None),
        "sin_papel": sum(1 for una in vigentes if getattr(una, "documento_id", None) is None),
    }


def resumen_de_una_maquina(
    *,
    maquina,
    obligaciones=(),
    inspecciones=(),
    averias=(),
    referencia: dt.date | None = None,
) -> dict:
    """Lo que la tabla enseña de una máquina en una fila: disponibilidad, próxima revisión y papeles.

    Se compone aquí, y no en el router ni en el JavaScript, porque es **lo mismo** que mira la
    ficha: si se calculara dos veces, la tabla y la ficha podrían decir cosas distintas de la misma
    máquina, que es la peor forma de perder la confianza en un programa.
    """
    avisos = avisos_de_una_maquina(
        maquina=maquina,
        obligaciones=obligaciones,
        inspecciones=inspecciones,
        averias=averias,
        referencia=referencia,
    )
    return {
        "proxima_revision": proxima_revision(
            obligaciones=obligaciones, inspecciones=inspecciones, referencia=referencia
        ),
        "documentacion": documentacion(inspecciones=inspecciones),
        "avisos": len(avisos),
        "avisos_urgentes": sum(1 for aviso in avisos if aviso["urgente"]),
        # La disponibilidad **se copia de lo que está declarado**, no se deduce de las averías ni de
        # las inspecciones: una máquina con una avería sin arreglar puede estar trabajando igual
        # (con el apero que sí funciona), y el que lo sabe es el agricultor.
        "disponibilidad": getattr(maquina, "disponibilidad", None) or NO_SE,
    }


def formatea_con_hora(cuando) -> str:
    """La fecha **y la hora**, como las lee una persona: `17/10/2026 a las 9:00`.

    Hace falta para las **reservas** (CRM-07 #9): un intervalo sin hora no dice nada -«el martes» no es una
    reserva, son muchas-, y `formatea` solo saca el dia. Se pone al lado de `formatea` para que las dos
    fechas de esta casa se escriban en el mismo sitio y no cada una a su manera.
    """
    if cuando is None:
        return ""
    return f"{cuando.day:02d}/{cuando.month:02d}/{cuando.year} a las {cuando.hour}:{cuando.minute:02d}"


def formatea(fecha: dt.date | None) -> str:
    """La fecha como se lee en España, o el texto vacío si no hay."""
    return fecha.strftime("%d/%m/%Y") if fecha else ""

# ---------------------------------------------------------------------------
# El cuenta-horas: lecturas, no un numero suelto (CRM-07 #8)
# ---------------------------------------------------------------------------


# Las unidades que admite un contador de maquina. **La unidad forma parte del dato**: «1.200» no dice
# nada, y un contador de horas y uno de kilometros no se suman ni se comparan.
UNIDADES_DEL_CONTADOR = ("horas", "kilometros")


def _es_un_valor_de_contador(valor: Any) -> bool:
    """Un valor de contador: un numero **finito y no negativo**. Lo demas no es una lectura.

    Un contador no marca -3 ni infinito. Se comprueba **aqui** -y no solo en el esquema- porque esta
    funcion es la que suma, y sumar un disparate es la forma mas rapida de ensenar un numero que nadie ha
    dicho.
    """
    if valor is None or isinstance(valor, bool):
        return False
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numero) and numero >= 0


def lo_que_marca_el_contador(lecturas: Sequence[Mapping[str, Any]]) -> dict:
    """**Cuanto ha subido el contador**, y que falta para poder decirlo (CRM-07 #8, 14/10/2026).

    El encargo lo pide con estas palabras: *«lecturas de contador fechadas y unidad; correcciones
    auditadas, sustitucion del contador, datos faltantes. ***No inventar horas ni reducir acumulados
    silenciosamente***»*. Y esto es eso, sin base de datos de por medio: entra una lista de lecturas y
    sale lo que se puede afirmar.

    **Una lectura es fecha + valor + unidad**, y el acumulado de un tramo es `ultima - primera`, que
    **solo se puede decir si las dos constan y el tramo cuadra**. Los casos que importan son los que casi
    nadie trata:

      * **Sin ninguna lectura** el contador no ha subido cero: **no se sabe**. `subido` sale 0 porque es
        una suma y una suma de nada es nada, **y `cobertura_incompleta` lo dice**, que es lo que impide
        que la pantalla ensene un «0 horas» como si fuera un dato. Es la regla de
        `sumando_lo_que_se_sabe`: ***nunca `(valor or 0)`***.
      * **Con una sola lectura** se sabe lo que **marca**, pero no lo que ha subido.
      * ***Un contador no puede ir para atras, y se mira PASO A PASO***: 1.000, 1.200, 1.100, 1.300
        termina **mas arriba** de donde empezo **y por el medio ha bajado**, que es imposible. Comparando
        solo los extremos salian 300 horas **y ninguna incidencia** (lo reprodujo la revision del
        16/10/2026). Un tramo asi **no se suma**: podria ser un error de tecleo o un contador cambiado sin
        decirlo, y elegir una de las dos historias es inventarsela.
      * ***Una sustitucion del contador corta el tramo***: la maquina paso a marcar desde cero y el
        acumulado **no baja** -lo de antes se suma y se dice, que es justo lo que el encargo prohibe que
        pase solo-.
      * ***Una lectura que no vale CIERRA el tramo donde estaba***, no lo tira: con 1.000, 1.200 y un
        hueco, las 200 horas del tramo anterior **se conservan**, y el trecho que queda sin medir se
        cuenta aparte.
      * **Una lectura anulada no cuenta**, como todo lo anulado de esta casa.
      * **Y las unidades no se mezclan**: si no son todas la misma se dice, en vez de sumar peras con
        manzanas.

    Devuelve `{"subido", "cuantas", "sin_decir", "cobertura_incompleta", "incoherentes", "unidad",
    "marca", "tramos", "lo_que_falta"}`. **El subtotal y su cobertura son dos cosas distintas**: lo que
    se puede afirmar viaja en `subido`, y `cobertura_incompleta` dice que hay tramos que se quedan fuera.
    """
    suyas = [una for una in (lecturas or []) if not una.get("anulado")]
    cuantas = len(suyas)
    if not suyas:
        return {
            "subido": 0.0,
            "cuantas": 0,
            "sin_decir": 1,
            "cobertura_incompleta": True,
            "incoherentes": [],
            "unidad": None,
            "marca": None,
            "tramos": [],
            "lo_que_falta": ["no_hay_ninguna_lectura"],
        }

    unidades = {str(una.get("unidad") or "").strip() for una in suyas}
    unidades.discard("")
    if len(unidades) > 1:
        return {
            "subido": None,
            "cuantas": cuantas,
            "sin_decir": 0,
            "cobertura_incompleta": True,
            "incoherentes": [],
            "unidad": None,
            "marca": None,
            "tramos": [],
            "lo_que_falta": ["las_lecturas_no_son_de_la_misma_unidad"],
        }
    unidad = next(iter(unidades), None)

    ordenadas = sorted(
        suyas, key=lambda una: (una.get("fecha") or dt.date.min, int(una.get("id") or 0))
    )

    subido = 0.0
    sin_decir = 0
    incoherentes: list[dict] = []
    tramos: list[dict] = []

    def _apunta_el_tramo(del_tramo: list) -> None:
        """Cierra un tramo: lo suma si **cuadra entero**, y si no lo deja dicho."""
        nonlocal subido, sin_decir
        if not del_tramo:
            return
        if len(del_tramo) == 1:
            # Un tramo de **una sola lectura** no se puede medir: no hay con que compararlo.
            sin_decir += 1
            return
        # ***Paso a paso, NO solo los extremos.*** Un contador que baja en medio no cuadra aunque acabe
        # mas arriba de donde empezo, y restando los extremos eso se pierde.
        for antes, ahora in zip(del_tramo, del_tramo[1:]):
            if float(ahora["valor"]) < float(antes["valor"]):
                incoherentes.append(
                    {
                        "desde": antes.get("fecha"),
                        "hasta": ahora.get("fecha"),
                        "subido": round(float(ahora["valor"]) - float(antes["valor"]), 3),
                        "motivo": "una_lectura_va_para_atras_sin_sustitucion",
                    }
                )
                # **Y el tramo entero queda sin afirmar**: con una lectura que no cuadra, el total del
                # tramo no se puede dar por bueno.
                return
        subido += float(del_tramo[-1]["valor"]) - float(del_tramo[0]["valor"])
        tramos.append(
            {
                "desde": del_tramo[0].get("fecha"),
                "hasta": del_tramo[-1].get("fecha"),
                "subido": round(float(del_tramo[-1]["valor"]) - float(del_tramo[0]["valor"]), 3),
                "por_sustitucion": False,
            }
        )

    tramo: list = []
    for una in ordenadas:
        if not _es_un_valor_de_contador(una.get("valor")):
            if tramo:
                # ***La lectura que no vale CIERRA el tramo donde estaba*** (15/10/2026). Antes se tiraba
                # -`primera = None` y a otra cosa- y asi se perdia lo que SI se sabia de el: con 1.000,
                # 1.200 y despues un hueco, las 200 horas desaparecian. Y ademas **se cuenta el hueco**,
                # porque entre esta lectura y la siguiente que valga hay un trecho que nadie ha medido.
                _apunta_el_tramo(tramo)
                tramo = []
                sin_decir += 1
            continue
        if una.get("es_sustitucion"):
            # ***Esta lectura ya es del contador NUEVO***: cierra el tramo viejo -hasta la lectura
            # ANTERIOR, no hasta esta- y abre uno nuevo con ella.
            if tramo:
                _apunta_el_tramo(tramo)
            tramo = [una]
            tramos.append(
                {"desde": una.get("fecha"), "hasta": None, "subido": None, "por_sustitucion": True}
            )
            continue
        tramo.append(una)
    if tramo:
        _apunta_el_tramo(tramo)

    con_valor = [una for una in ordenadas if _es_un_valor_de_contador(una.get("valor"))]
    malas = [
        una
        for una in ordenadas
        if una.get("valor") is not None and not _es_un_valor_de_contador(una.get("valor"))
    ]
    falta: list[str] = []
    if len(con_valor) < 2:
        falta.append("hace_falta_otra_lectura_para_saber_cuanto_ha_subido")
    elif sin_decir:
        falta.append("hay_tramos_sin_lectura_al_final")
    if incoherentes:
        falta.append("una_lectura_va_para_atras_sin_sustitucion")
    if malas:
        falta.append("hay_lecturas_que_no_son_un_numero_de_contador")
    return {
        "subido": round(subido, 3),
        "cuantas": cuantas,
        "sin_decir": sin_decir,
        "cobertura_incompleta": bool(sin_decir or incoherentes or malas),
        "incoherentes": incoherentes,
        "unidad": unidad,
        "marca": con_valor[-1].get("valor") if con_valor else None,
        "tramos": tramos,
        "lo_que_falta": falta,
    }
