"""Catálogos del cuaderno de campo.

Decisión: los catálogos que fija la ley (provincias, medidas preventivas, modos de
aplicación) viven en código, versionados, y no en base de datos. Así un cambio
normativo se ve en el historial de git y no se pierde en un UPDATE.

El listado municipal del Decreto 5/2020 se deriva del Excel publicado por IDECyL
en `data/zv_cyl.csv`, sin transcribir municipios a mano. Si el fichero falta,
`es_zona_vulnerable()` devuelve None: no se supone que la parcela esté fuera.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import nitratos_cyl
from . import textos

PROVINCIAS_CYL = (
    "Ávila",
    "Burgos",
    "León",
    "Palencia",
    "Salamanca",
    "Segovia",
    "Soria",
    "Valladolid",
    "Zamora",
)

SISTEMAS_EXPLOTACION = ("secano", "regadio")

# Las medidas preventivas de la gestión integrada de plagas.
# `pregunta` es lo que ve el agricultor; `etiqueta` es el nombre oficial que se
# guarda y se imprime en el cuaderno. La app nunca enseña `etiqueta` sin explicar.
@dataclass(frozen=True)
class MedidaPreventiva:
    codigo: str
    pregunta: str
    etiqueta: str


# --- semilla (CRM-07 #2, 14/10/2026) ---
# **Las categorias de una semilla**, que es lo que la etiqueta oficial dice de ella. **Y aqui NO hay
# categoria por defecto**: *no haber registrado la etiqueta **no demuestra** que el lote no este
# certificado*, y el reglamento de semillas distingue categorias y remite a reglamentos tecnicos por
# especie. La ausencia es **«No consta»** (`None`), y **«No certificada» es una de las que se
# declaran** cuando el agricultor lo sabe.
#
# *(Corregido el 14/10/2026: este comentario decia lo contrario — que «el defecto de una semilla sin
# papeles es "No certificada"» — y la revision del dueno lo tumbó. El propio proyecto ya lo tenia
# escrito en el aviso N07: «Una semilla comprada sin etiqueta no queda certificada por eso».)*
CATEGORIAS_DE_SEMILLA: dict[str, str] = {
    "no_certificada": "No certificada",
    "base": "Base",
    "certificada": "Certificada",
    "r1": "R1",
    "r2": "R2",
}

# Y **de donde salio la semilla**: se compra, o se guarda de la cosecha propia.
PROCEDENCIAS: dict[str, str] = {
    "comprada": "Comprada",
    "propia": "Guardada de la cosecha propia",
}


def etiqueta_de_categoria(valor: str | None) -> str:
    """El texto de una categoria de semilla. Lo que no se conoce se dice, no se inventa."""
    if not valor:
        return "No consta"
    return CATEGORIAS_DE_SEMILLA.get(valor, valor)


MEDIDAS_PREVENTIVAS: tuple[MedidaPreventiva, ...] = (
    MedidaPreventiva("rotacion", "¿Cambias de cultivo de un año a otro?", "Rotación de cultivos"),
    MedidaPreventiva(
        "variedades",
        "¿Usas variedades que aguantan mejor las plagas?",
        "Uso de variedades resistentes o tolerantes",
    ),
    MedidaPreventiva(
        "trampeo",
        "¿Pones trampas o cebos para saber cuántos bichos hay?",
        "Control por trampeo y confusión sexual",
    ),
    MedidaPreventiva(
        "linderos",
        "¿Dejas setos, linderos o flores para los bichos que comen plagas?",
        "Infraestructuras ecológicas y fomento de fauna auxiliar",
    ),
    MedidaPreventiva(
        "muestreo",
        "¿Miras el campo antes de decidir echar algo?",
        "Muestreo y respeto de los umbrales de tratamiento",
    ),
    MedidaPreventiva(
        "higiene",
        "¿Limpias la máquina al pasar de una parcela a otra?",
        "Higiene y limpieza de equipos y maquinaria",
    ),
    MedidaPreventiva(
        "restos",
        "¿Quitas los restos del cultivo anterior?",
        "Eliminación de restos de cultivo y poda sanitaria",
    ),
    MedidaPreventiva(
        "nutricion",
        "¿Mides bien el abono y el riego?",
        "Manejo de la nutrición y del riego",
    ),
    MedidaPreventiva(
        "avisos",
        "¿Haces caso a los avisos de la Junta?",
        "Seguimiento de boletines y avisos",
    ),
    MedidaPreventiva(
        "cuaderno",
        "¿Apuntas lo que pasa cada año para aprender?",
        "Registro y seguimiento de la parcela",
    ),
)

CODIGOS_MEDIDA = {m.codigo for m in MEDIDAS_PREVENTIVAS}

# Índice por código, para no recorrer la tupla en cada petición.
_MEDIDAS_POR_CODIGO = {m.codigo: m for m in MEDIDAS_PREVENTIVAS}


def medida_de(codigo: str) -> MedidaPreventiva | None:
    """La medida del catálogo con ese código, o None si no existe.

    Devolver None es lo que impide que se cuele una medida inventada: el router descarta
    lo que no esté aquí en vez de guardarlo tal cual. Y no es un detalle de estilo: el
    listado que se entrega a la administración lleva la `etiqueta` oficial, así que una
    medida que no esté en el catálogo saldría sin nombre.

    Ojo con el código: el catálogo oficial de medidas del SIEX se publica como «según
    catálogo» y **no viene con sus códigos en la documentación que tenemos**. Los códigos
    de aquí son internos y estables (no se cambian nunca, porque están guardados en la
    base de datos de cada agricultor); lo que se imprime y se exporta es la `etiqueta`.
    """
    return _MEDIDAS_POR_CODIGO.get(codigo)


def etiqueta_medida(codigo: str) -> str:
    for medida in MEDIDAS_PREVENTIVAS:
        if medida.codigo == codigo:
            return medida.etiqueta
    return codigo


# --------------------------------------------------------------------------
# Los tipos de labor. **Esto se corrigió en la ronda 14 leyendo el documento oficial.**
#
# Las instrucciones de la app de la Junta dicen, del apartado «Otras Prácticas Culturales»:
#
#   «permite buscar y/o anotar otras prácticas culturales en una DGC: **Laboreo, mantenimiento de
#    cubierta, pastoreo**, etc.»
#
# O sea que el documento nombra tres, y aquí faltaban dos: **no había forma de apuntar un
# mantenimiento de cubierta ni un pastoreo**. Y había un segundo problema, más gordo: esta lista
# existía pero **ninguna pantalla la ofrecía**. El agricultor pulsaba «OTRO TRABAJO» y se guardaba
# `otra`, sin decir nunca cuál. Así que la poda, el desbroce, la escarda y el laboreo estaban en
# el catálogo y no se podían elegir, y el volcado oficial mandaba «otra» para todo.
#
# Ahora la lista se le ofrece al agricultor (paso «¿qué has hecho?» del asistente) y sale de aquí,
# del servidor, para que no haya dos listas que puedan separarse.
#
# Decisión: los que ya existían se quedan con el mismo código, porque hay apuntes guardados que
# los usan y `Labor.tipo` es texto que va en el volcado.
# --------------------------------------------------------------------------

TIPOS_LABOR = (
    "siembra",
    "plantacion",
    "riego",
    "cosecha",
    "poda",
    "desbroce",
    "escarda",
    "laboreo",
    # Los dos que nombra el documento oficial y no estaban.
    "cubierta",
    "pastoreo",
    "otra",
)

ETIQUETA_LABOR = {
    "siembra": "Siembra",
    "plantacion": "Plantación",
    "riego": "Riego",
    "cosecha": "Cosecha",
    "poda": "Poda",
    "desbroce": "Desbroce",
    "escarda": "Escarda",
    "laboreo": "Laboreo",
    "cubierta": "Mantenimiento de la cubierta",
    "pastoreo": "Pastoreo",
    "otra": "Otro trabajo",
}

# Los que se le ofrecen al agricultor cuando dice «otro trabajo» están en `textos.TRABAJOS_DE_LABOR`,
# no aquí: son texto que lee el agricultor, y todo el texto que lee el agricultor vive en
# `textos.py` para que el test de jerga lo revise. Aquí queda solo lo que es código.

TIPOS_FERTILIZANTE = ("mineral", "organico", "organo-mineral")

# --------------------------------------------------------------------------
# El asesor y el agua de riego
#
# AVISO IMPORTANTE sobre estas tres listas: **no son las oficiales.** Las tres van en el
# contenido mínimo del CUE con la coletilla «(según catálogo)», y ese catálogo no lo tenemos
# (sale del servicio de catálogos de SIEX, ver `iuws.CATALOGOS_SIEX`). Son listas nuestras,
# con los nombres que se usan en Castilla y León, y sirven para dos cosas:
#
#   1. Que el agricultor **elija de una lista** en vez de escribir a mano. Escribiendo a mano
#      salen diez formas distintas de decir «pozo», y después no se pueden sumar ni comparar.
#   2. Que al volcar el cuaderno a la Junta esos campos vayan **marcados como campos de
#      catálogo y vacíos**, en vez de con un valor nuestro disfrazado de código oficial. Ver
#      `iuws_contenido.Campo.catalogo`.
#
# El día que llegue el catálogo oficial, se cambian los códigos de aquí y se rellenan los del
# volcado. Lo que no se puede hacer es presentar los de aquí como si fueran los de la Junta.
# --------------------------------------------------------------------------

# En qué está inscrito el asesor. El registro ROPO distingue estas figuras.
AMBITOS_ASESOR = ("gip", "produccion_integrada", "ecologico", "otros")

ETIQUETA_AMBITO_ASESOR = {
    "gip": "Plagas (gestión integrada)",
    "produccion_integrada": "Producción integrada",
    "ecologico": "Producción ecológica",
    "otros": "Otras cosas",
}

# Cómo de bien ha funcionado un tratamiento.
#
# **Esta lista es nuestra, no del catálogo de la Junta.** El interfaz pide un código del catálogo
# «Eficacia del tratamiento» y de ese catálogo no tenemos los valores. Se pregunta igualmente por
# dos motivos: la valoración del tratamiento es uno de los bloques que pide el Anexo II, y así el
# día que lleguen los códigos el dato ya estará recogido en el cuaderno en vez de haber que
# empezar de cero.
#
# Lo que **no** se hace es suponer la equivalencia entre estas cuatro y los códigos oficiales: eso
# está pendiente y se dice en `iuws_mapeo.py`.
EFICACIA_DEL_TRATAMIENTO = ("muy_bien", "bien", "regular", "mal")


ETIQUETA_EFICACIA = {
    "muy_bien": "Muy bien: no ha quedado nada",
    "bien": "Bien: ha quedado algo, pero poco",
    "regular": "Regular: habría que repetirlo",
    "mal": "Mal: no ha servido",
}

# De dónde sale el agua con la que se riega. Es un dato que el cuaderno pide y que además
# importa para el abono: el agua de un pozo en zona de nitratos ya trae nitrógeno.
ORIGENES_AGUA = ("pozo", "canal", "balsa", "manantial", "rio", "comunidad_regantes", "red", "otro")

ETIQUETA_ORIGEN_AGUA = {
    "pozo": "Pozo o sondeo",
    "canal": "Canal o acequia",
    "balsa": "Balsa",
    "manantial": "Manantial",
    "rio": "Río o arroyo",
    "comunidad_regantes": "Comunidad de regantes",
    "red": "Red de riego",
    "otro": "Otra procedencia",
}

# Cómo se riega.
SISTEMAS_RIEGO = ("aspersion", "goteo", "pivote", "manta", "inundacion", "localizado", "otro")

ETIQUETA_SISTEMA_RIEGO = {
    "aspersion": "Aspersión",
    "goteo": "Goteo",
    "pivote": "Pivote",
    "manta": "Manta",
    "inundacion": "Inundación o a manta",
    "localizado": "Riego localizado",
    "otro": "Otro sistema",
}

# En qué se mide el agua. El metro cúbico es lo que marca el contador; el milímetro es lo que
# dice el agricultor cuando habla de «una regada de 30»; y los m³/ha es lo que se compara
# entre parcelas de distinto tamaño.
UNIDADES_AGUA = ("m3", "m3/ha", "mm")

ETIQUETA_UNIDAD_AGUA = {
    "m3": "metros cúbicos (m³)",
    "m3/ha": "metros cúbicos por hectárea (m³/ha)",
    "mm": "milímetros (mm)",
}

# Clases de instalación, y cómo se le enseñan al agricultor.
TIPOS_INSTALACION = ("almacen", "nave", "invernadero", "balsa", "silo", "otro")

ETIQUETA_INSTALACION = {
    "almacen": "Almacén",
    "nave": "Nave",
    "invernadero": "Invernadero",
    "balsa": "Balsa de riego",
    "silo": "Silo",
    "otro": "Otra cosa",
}

# De qué clase es una aplicación de producto. La app oficial las tiene como secciones
# separadas (tratamiento, semilla tratada, postcosecha, instalaciones); aquí son el
# mismo registro con distinto «dónde», porque los datos son los mismos.
TIPOS_TRATAMIENTO = ("parcela", "semilla_tratada", "postcosecha", "instalaciones")

# Cuáles se aplican sobre la tierra (necesitan parcela) y cuáles sobre un local
# (necesitan instalación).
TRATAMIENTO_EN_PARCELA = ("parcela", "semilla_tratada")
TRATAMIENTO_EN_INSTALACION = ("instalaciones", "postcosecha")

ETIQUETA_TRATAMIENTO = {
    "parcela": "En una parcela",
    "semilla_tratada": "La semilla ya venía tratada",
    "postcosecha": "Al producto ya recogido",
    "instalaciones": "En una nave o un almacén",
}

# Cómo se le enseña al agricultor cada uno. En la base de datos van sin tilde ni
# espacios; en pantalla, como los llama él.
ETIQUETA_SISTEMA = {
    "secano": "Secano",
    "regadio": "Regadío",
}

# **Las tres respuestas** del sistema de una tierra, que es lo que se le ofrece al agricultor donde se
# elige (el mapa, la pantalla de decir el cultivo y los formularios de la tierra y del grupo).
#
# Nació con dos —secano y regadío— y **sin «no lo sé»**, y eso era el defecto A10 de
# `docs/T02_VALORES_POR_DEFECTO.md`: lo que el agricultor no elegía se guardaba como secano, así que el
# programa declaraba de secano una tierra de regadío y la casilla «Secano/Regadío» del cuaderno de la
# Junta salía con una «S». El sistema decide **contra qué columna del anexo III** se compara el abonado
# (Orden MAV/398/2022), así que no es una casilla decorativa.
#
# El valor de la tercera es `"nulo"` porque es el que viaja por la pantalla y se convierte en `null` al
# guardar (`app.js`, `valorDeEleccion`), igual que en los campos de «sí, no o no lo sé».
SISTEMAS_PARA_ELEGIR = (
    {"valor": "secano", "texto": ETIQUETA_SISTEMA["secano"]},
    {"valor": "regadio", "texto": ETIQUETA_SISTEMA["regadio"]},
    {"valor": "nulo", "texto": textos.ACCIONES["no_se"]},
)

ETIQUETA_TIPO_ABONO = {
    "mineral": "Mineral, de fábrica",
    "organico": "Orgánico: estiércol o purín",
    "organo-mineral": "Mezcla de los dos",
}

# Unidades en las que se puede expresar la dosis de un producto. Están las cinco que
# de verdad salen en las etiquetas de esta tierra.
UNIDADES_DOSIS = ("L/ha", "kg/ha", "mL/hL", "g/hL", "L/100 L")

# --------------------------------------------------------------------------
# Analíticas
#
# La app oficial tiene una sección «Otras Actividades: Analíticas» para anotar los
# análisis de los cultivos, de los productos cosechados, del suelo y del agua de riego.
# Aquí se añaden los de residuos, que son los que pide el comprador antes de comprar la
# cosecha y que, si no están apuntados, se acaban buscando en un cajón.
#
# Decisión sobre los PARÁMETROS: se guardan por clave, y las claves salen de esta lista.
# El motivo es que el plan de abono tenga de dónde tirar: si el agricultor escribe
# «fósforo» en un cuadro de texto libre, el programa no puede usar ese número para nada.
# El agricultor sigue copiando el número del boletín; lo que no teclea es el nombre.
#
# DE DÓNDE SALE CADA LISTA, y esto importa:
#
#   * **suelo**: los nueve parámetros del contenido mínimo del CUE (documento técnico
#     SIEX v3.11, bloque 13 «Analíticas»). Son materia orgánica, arena, limo, arcilla,
#     pH, fósforo asimilable, potasio asimilable, nitrógeno total y conductividad
#     eléctrica a 25 ºC. Van marcados con `oficial=True`.
#   * **agua de riego, cultivo, producto cosechado y residuos**: ninguna norma fija
#     estos parámetros. Son los que trae siempre un boletín de ese tipo, y van marcados
#     con `oficial=False` para que quede escrito que NO vienen de un listado oficial.
#     El listado oficial de la Junta, cuando llegue, se carga como los demás catálogos.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# La documentación anexa: los papeles que acompañan al cuaderno
#
# Sale del apartado «Documentación» de las instrucciones de la app de la Junta
# (`03_CastillaYLeon_CUECyL_instrucciones.pdf`), que dice con estas palabras:
#
#   «El apartado Documentación permite guardar la documentación complementaria al Cuaderno:
#    contratos, facturas, albaranes de entrega de envases a Sigfito, etc. La documentación puede
#    organizarse en distintas carpetas.»
#
# De ahí salen los tres primeros tipos: están NOMBRADOS en el documento. `otros` está porque el
# documento sigue con «etc.», y hay papeles que no son ninguno de esos tres (el carné de
# aplicador, el contrato de una subvención, el boletín de un análisis que ya está en su sección).
#
# Y las carpetas: **el documento no impone ninguna**, dice que «puede organizarse en distintas
# carpetas». Así que la carpeta la escribe el agricultor y lo que hay aquí son SUGERENCIAS, no un
# catálogo cerrado. Escribir una lista cerrada construiría una obligación que la Junta no pide, y
# el primer agricultor que archivara sus papeles de otra manera se encontraría sin sitio.
# --------------------------------------------------------------------------

# ... y los cuatro de la bandeja documental (T08, S10, 06/10/2026).
#
# Llevan aquí desde el primer día del catálogo y se apuntaban mal, cada uno por su motivo:
#
#   · **`inspeccion`**: el certificado de la ITV o de la ITEAF de una máquina. Es el que el T14 dejó
#     escrito que faltaba (`tests/test_t14_maquinaria.py`: «se apunta como "otros" porque no hay un tipo
#     de papel para un certificado de inspección (…) el día que exista ese tipo, este certificado irá al
#     suyo»).
#   · **`ticket`**: el tique del gasóleo o del taller. No es una factura —casi nunca lleva NIF— y
#     meterlo como «factura» ensucia la lista de facturas.
#   · **`albaran`**: el albarán de entrega de grano o de compra. **No es** el de envases de Sigfito, que
#     ya tenía su tipo: son dos papeles distintos y con el mismo nombre se confundirían.
#   · **`analitica`**: el boletín de un laboratorio **en papel**. Sus números tienen su sección propia
#     con su boletín; aquí está el papel, que es lo que se enseña en una inspección.
TIPOS_DOCUMENTO = (
    "contrato",
    "factura",
    "albaran_sigfito",
    "otros",
    "inspeccion",
    "ticket",
    "albaran",
    "analitica",
)

ETIQUETA_DOCUMENTO = {
    "contrato": "Un contrato",
    "factura": "Una factura",
    "albaran_sigfito": "Un albarán de envases (Sigfito)",
    "otros": "Otro papel",
    "inspeccion": "Un certificado de inspección",
    "ticket": "Un ticket de compra",
    "albaran": "Un albarán de entrega",
    "analitica": "Un boletín de análisis",
}

# Las sugerencias de carpeta, en plural porque es donde se guardan varios. El agricultor puede
# escribir otra y el programa la acepta igual.
CARPETAS_SUGERIDAS = (
    "Contratos",
    "Facturas",
    "Envases",
    "Licencias y permisos",
    "Ayudas y subvenciones",
    "Otros",
)


def etiqueta_documento(tipo: str) -> str:
    """Cómo se llama ese tipo de papel, en palabras del agricultor."""
    return ETIQUETA_DOCUMENTO.get(tipo, ETIQUETA_DOCUMENTO["otros"])


TIPOS_ANALITICA = ("suelo", "agua_riego", "cultivo", "producto_cosechado", "residuos")
ETIQUETA_ANALITICA = {
    "suelo": "La tierra",
    "agua_riego": "El agua con la que riego",
    "cultivo": "La planta",
    "producto_cosechado": "Lo que he recogido",
    "residuos": "Si lleva restos de lo que eché",
}

# Qué análisis se piden de una parcela concreta y cuáles pueden ser de cualquier sitio
# (el agua de una balsa, un lote de grano ya mezclado de varias parcelas).
ANALITICA_DE_PARCELA = ("suelo", "cultivo")


@dataclass(frozen=True)
class ParametroAnalitica:
    """Un número que puede traer un boletín de análisis.

    `etiqueta` es el nombre que se imprime en el informe; `pregunta` es lo que se le
    enseña al agricultor, que es más corto porque en pantalla el sitio es el que es.
    `unidad` va aparte y no dentro del nombre para poder sumar y comparar valores.
    """

    clave: str
    etiqueta: str
    pregunta: str
    unidad: str
    oficial: bool = True


# Los nueve del contenido mínimo del CUE, en el orden en que los pide la norma.
_PARAMETROS_SUELO: tuple[ParametroAnalitica, ...] = (
    ParametroAnalitica("materia_organica", "Materia orgánica", "Materia orgánica", "%"),
    ParametroAnalitica("arena", "Arena", "Arena", "%"),
    ParametroAnalitica("limo", "Limo", "Limo", "%"),
    ParametroAnalitica("arcilla", "Arcilla", "Arcilla", "%"),
    ParametroAnalitica("ph", "pH", "pH", ""),
    ParametroAnalitica("fosforo_asimilable", "Fósforo asimilable", "Fósforo", "ppm"),
    ParametroAnalitica("potasio_asimilable", "Potasio asimilable", "Potasio", "ppm"),
    ParametroAnalitica("nitrogeno_total", "Nitrógeno total", "Nitrógeno", "%"),
    ParametroAnalitica("conductividad", "Conductividad eléctrica a 25 ºC", "Conductividad", "dS/m"),
)

# Estos cuatro bloques NO vienen de ninguna norma: son los números que trae el boletín.
_PARAMETROS_AGUA: tuple[ParametroAnalitica, ...] = (
    ParametroAnalitica("nitratos", "Nitratos", "Nitratos", "mg/L", oficial=False),
    ParametroAnalitica(
        "conductividad", "Conductividad eléctrica a 25 ºC", "Conductividad", "dS/m", oficial=False
    ),
    ParametroAnalitica("ph", "pH", "pH", "", oficial=False),
)

_PARAMETROS_CULTIVO: tuple[ParametroAnalitica, ...] = (
    ParametroAnalitica("nitrogeno_total", "Nitrógeno total", "Nitrógeno", "%", oficial=False),
    ParametroAnalitica("fosforo_total", "Fósforo total", "Fósforo", "%", oficial=False),
    ParametroAnalitica("potasio_total", "Potasio total", "Potasio", "%", oficial=False),
    ParametroAnalitica("materia_seca", "Materia seca", "Materia seca", "%", oficial=False),
)

_PARAMETROS_COSECHA: tuple[ParametroAnalitica, ...] = (
    ParametroAnalitica("humedad", "Humedad", "Humedad", "%", oficial=False),
    ParametroAnalitica("proteina", "Proteína", "Proteína", "%", oficial=False),
    ParametroAnalitica("peso_hectolitro", "Peso por hectolitro", "Peso por hectolitro", "kg/hL", oficial=False),
    ParametroAnalitica("gluten", "Gluten", "Gluten", "%", oficial=False),
)

_PARAMETROS_RESIDUOS: tuple[ParametroAnalitica, ...] = (
    ParametroAnalitica(
        "residuo", "Residuo encontrado", "Cuánto residuo han encontrado", "mg/kg", oficial=False
    ),
)

PARAMETROS_ANALITICA: dict[str, tuple[ParametroAnalitica, ...]] = {
    "suelo": _PARAMETROS_SUELO,
    "agua_riego": _PARAMETROS_AGUA,
    "cultivo": _PARAMETROS_CULTIVO,
    "producto_cosechado": _PARAMETROS_COSECHA,
    "residuos": _PARAMETROS_RESIDUOS,
}

# Índice por tipo y clave. Se construye una vez: recorrer la tupla en cada petición para
# validar un número sería tirar tiempo en el sitio donde menos sobra, que es el móvil del
# agricultor con mala cobertura.
_PARAMETROS_POR_CLAVE: dict[str, dict[str, ParametroAnalitica]] = {
    tipo: {parametro.clave: parametro for parametro in parametros}
    for tipo, parametros in PARAMETROS_ANALITICA.items()
}


def parametros_de(tipo: str) -> tuple[ParametroAnalitica, ...]:
    """Los números que puede traer un boletín de esa clase. Vacío si el tipo no existe."""
    return PARAMETROS_ANALITICA.get(tipo, ())


def parametro_de(tipo: str, clave: str) -> ParametroAnalitica | None:
    """Un parámetro concreto, o None si esa clave no vale para ese tipo de análisis.

    Devolver None es lo que impide que se cuele un parámetro inventado: el router
    descarta lo que no esté aquí en vez de guardarlo tal cual.
    """
    return _PARAMETROS_POR_CLAVE.get(tipo, {}).get(clave)


def etiqueta_analitica(tipo: str) -> str:
    return ETIQUETA_ANALITICA.get(tipo, tipo)


MODOS_APLICACION_ABONO = (
    "al suelo",
    "enterrado",
    "con el riego",
    "foliar",
    "localizado",
)

# --------------------------------------------------------------------------
# Lo que se vende
#
# El contenido mínimo del CUE llama a esta sección «Cosecha comercializada y/o venta
# directa», y distingue **dos clases de venta**, que es lo que pide la norma:
#
#   * **comercializada**: lo que sale para el mercado, normalmente a un comprador o a una
#     cooperativa.
#   * **venta directa**: lo que se vende al consumidor sin intermediarios (a un restaurante,
#     en el mercado, en la puerta de casa).
#
# La norma no fija el catálogo de «producto vegetal» en la documentación que tenemos (dice
# «según catálogo» y no lo incluye), así que el producto se escribe y **no se inventa una
# lista**. Lo que sí se fija son las unidades, que la norma sí nombra: kilos o unidades.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# De quién es una máquina de echar producto
#
# La aplicación de la Junta tiene **tres listas de maquinaria** en su apartado «Registro Maquinaria»
# (ver las instrucciones del Cuecyl, página 13):
#
#   · **Maquinaria propia**: la inscrita en el ROMA a nombre del titular.
#   · **Maquinaria ajena**: la inscrita en el ROMA que **no es del titular** pero se ha usado; por
#     ejemplo, cuando el tratamiento lo hace una empresa de servicios.
#   · **Equipos NO ROMA**: lo que no se inscribe en el ROMA: mochilas, carretillas y aperos.
#
# Los tres nombres son los de la app oficial; el texto que se le enseña al agricultor es el de
# `textos.INTERFAZ["titularidades_equipo"]`, en palabras que se entienden.
#
# **Y una cuarta respuesta: «no lo sé»** (A11 de `docs/T02_VALORES_POR_DEFECTO.md`, 05/10/2026). Nacía
# con tres y sin ella, y el campo se guardaba con `"propia"` por defecto: dar de alta el pulverizador
# de la empresa de servicios sin tocar la casilla dejaba **la máquina de otro como tuya** y con su
# ITEAF, en la lista equivocada del cuaderno. De quién es una máquina **no se deduce de ningún dato**
# (`docs/T02`, tabla de evidencias), así que se pregunta y se puede contestar «no lo sé».
# --------------------------------------------------------------------------

TITULARIDADES_EQUIPO = (
    {"valor": "propia", "texto": "Es mía"},
    {"valor": "ajena", "texto": "Es de otro (me la deja o me la alquila)"},
    {"valor": "no_roma", "texto": "No va inscrita en el ROMA (mochila, apero…)"},
    {"valor": "nulo", "texto": textos.ACCIONES["no_se"]},
)


# --------------------------------------------------------------------------
# El tipo de carné de quien echa el producto
#
# La hoja 1.2 del cuaderno de la Junta tiene **cuatro columnas** para marcar el carné de cada
# persona que interviene: Básico, Cualificado (en el papel, «Cualif.»), Fumigador y Piloto. Hasta
# ahora esto era un texto libre, y un texto libre en una casilla que el cuaderno marca con una cruz
# acaba en que la cruz no se puede poner: nadie sabe si el agricultor escribió «cualificado»,
# «Cualificado» o «nivel 2».
#
# Los cuatro nombres son los del cuaderno. Se guarda el valor en minúsculas y sin espacios (la clave)
# y se enseña el texto de `ETIQUETA_CARNE`, que es lo que lee el agricultor en su carné.
# --------------------------------------------------------------------------

TIPOS_CARNE = ("basico", "cualificado", "fumigador", "piloto")

ETIQUETA_CARNE = {
    "basico": "Básico",
    "cualificado": "Cualificado",
    "fumigador": "Fumigador",
    "piloto": "Piloto (tratamientos aéreos)",
}


def etiqueta_carne(valor: str | None) -> str:
    """El nombre del carné tal y como se enseña. Lo que no esté en la lista se devuelve tal cual."""
    return ETIQUETA_CARNE.get((valor or "").strip().lower(), (valor or "").strip())


TIPOS_VENTA = ("comercializada", "venta_directa")

ETIQUETA_VENTA = {
    "comercializada": "Lo vendí a un comprador o a la cooperativa",
    "venta_directa": "Lo vendí yo directamente al cliente",
}

# Cómo se le enseña cada una, en corto, para las listas.
ETIQUETA_VENTA_CORTA = {
    "comercializada": "Venta a comprador",
    "venta_directa": "Venta directa",
}

# Unidades en las que se puede anotar lo vendido. Son las que nombra la norma («kg o ud») más
# la tonelada, que es como se vende el grano en Castilla y León.
#
# `a_kilos` es el factor para poder sumar y comparar. `None` significa «no se puede convertir
# a kilos»: una unidad de lechugas no es un peso, y decir que 3.000 unidades son 3.000 kg
# sería un dato falso. Los totales del informe solo convierten lo que se puede.
UNIDADES_VENTA: dict[str, dict] = {
    "kg": {"etiqueta": "kilos", "corto": "kg", "a_kilos": 1.0},
    "t": {"etiqueta": "toneladas", "corto": "t", "a_kilos": 1000.0},
    "ud": {"etiqueta": "unidades", "corto": "ud", "a_kilos": None},
}


def unidad_de_venta(unidad: str) -> dict | None:
    return UNIDADES_VENTA.get(unidad)


def kilos_de_una_venta(cantidad: float | None, unidad: str) -> float | None:
    """Los kilos de una venta, o None si esa unidad no es un peso.

    Se devuelve None y no el número tal cual porque una unidad de lechugas no pesa lo que
    dice el número: sumarla con kilos daría un total que no significa nada.
    """
    factor = (UNIDADES_VENTA.get(unidad) or {}).get("a_kilos")
    if factor is None or cantidad is None:
        return None
    return round(cantidad * factor, 4)

MOMENTOS_ABONADO = ("fondo", "cobertera")

UNIDADES_PRODUCTO = ("L", "kg", "mL", "g", "cc")

# Justificaciones admitidas para un tratamiento. La primera es la que más se usa y
# se ofrece por defecto, para que el agricultor no tenga que leer la lista entera.
JUSTIFICACIONES = (
    "Vi la plaga o la hierba en el campo",
    "Aviso de la Junta",
    "Me lo dijo mi técnico",
    "Me lo pidió el comprador",
    "Tratamiento de prevención",
    "Otra razón",
)


# --------------------------------------------------------------------------
# Los municipios de Castilla y León
#
# **Para qué hace falta esta lista.** Para dar de alta una parcela hay que decir en qué
# municipio está, y hasta ahora eso se escribía a mano. Escribir «Calvarrasa de Arriba» a mano
# tiene dos problemas: uno, que cada uno lo escribe como quiere; y dos, que si no coincide
# exactamente con el nombre oficial, la comprobación de zona vulnerable no encuentra el
# municipio y el agricultor se queda sin saber si su parcela tiene límites de abono.
#
# Esta lista es la del INE, la misma numeración que usa el visor del SIGPAC y la referencia
# catastral (ver `data/municipios_ine_fuentes/`). Con ella, el agricultor **elige su pueblo de
# una lista** y el programa rellena el municipio, la provincia y el código INE de una vez.
# --------------------------------------------------------------------------

_RUTA_MUNICIPIOS_POR_DEFECTO = Path(
    os.environ.get("CUEDIGITAL_MUNICIPIOS_RUTA")
    or Path(__file__).resolve().parents[2] / "data" / "municipios_cyl.csv"
)

_municipios: list["Municipio"] | None = None


@dataclass(frozen=True)
class Municipio:
    """Un municipio oficial: su nombre, su provincia y sus códigos.

    `codigo_municipio` es el de tres cifras que sale en el visor del SIGPAC («70 -
    CALVARRASA DE ARRIBA») y el que va dentro de la referencia del recinto; `codigo_ine` es el
    de cinco cifras (provincia + municipio), que es el que usan los listados oficiales.
    """

    codigo_ine: str
    nombre: str
    provincia: str
    codigo_provincia: str
    codigo_municipio: str


def _quita_tildes(texto: str) -> str:
    """Pasa el texto a minúsculas y sin tildes, para buscar como se busca en el móvil.

    Nadie escribe «Peñaranda» en el móvil con la tilde: escribe «penaranda». Un buscador que
    exige tildes es un buscador que no encuentra nada.
    """
    sin_tildes = unicodedata.normalize("NFKD", texto)
    return " ".join(
        "".join(caracter for caracter in sin_tildes if not unicodedata.combining(caracter))
        .strip()
        .lower()
        .split()
    )


def cargar_municipios(ruta: Path | str | None = None) -> int:
    """Carga la lista oficial de municipios. Devuelve cuántos ha cargado.

    Si el fichero no está, la lista se queda vacía y la aplicación sigue funcionando: se puede
    escribir el municipio a mano como antes. Lo que **no** se hace es inventarse municipios.
    """
    global _municipios
    ruta = Path(ruta) if ruta else _RUTA_MUNICIPIOS_POR_DEFECTO
    municipios: list[Municipio] = []

    if ruta.exists():
        with ruta.open(encoding="utf-8", newline="") as fichero:
            for fila in csv.DictReader(fichero):
                nombre = (fila.get("municipio") or "").strip()
                codigo_ine = (fila.get("codigo_ine") or "").strip()
                if not nombre or not codigo_ine:
                    continue
                municipios.append(
                    Municipio(
                        codigo_ine=codigo_ine,
                        nombre=nombre,
                        provincia=(fila.get("provincia") or "").strip(),
                        codigo_provincia=(fila.get("codigo_provincia") or "").strip(),
                        codigo_municipio=(fila.get("codigo_municipio") or "").strip(),
                    )
                )
    _municipios = municipios
    return len(municipios)


def municipios_de_cyl() -> list[Municipio]:
    if _municipios is None:
        cargar_municipios()
    return _municipios or []


def olvidar_municipios() -> None:
    """Vacía la lista cargada. Existe para los tests, como el de las zonas vulnerables."""
    global _municipios
    _municipios = None


def provincias_con_municipios() -> list[str]:
    """Las provincias que salen en la lista, en el orden en que salen. Son las nueve de aquí."""
    vistas: list[str] = []
    for municipio in municipios_de_cyl():
        if municipio.provincia and municipio.provincia not in vistas:
            vistas.append(municipio.provincia)
    return sorted(vistas)


def municipio_por_codigo_ine(codigo: str | None) -> Municipio | None:
    buscado = (codigo or "").strip()
    if not buscado:
        return None
    for municipio in municipios_de_cyl():
        if municipio.codigo_ine == buscado:
            return municipio
    return None


def busca_municipios(
    texto: str, provincia: str | None = None, limite: int = 25
) -> list[Municipio]:
    """Busca municipios por su nombre, como se busca en un móvil.

    Sin tildes y sin mayúsculas, y **los que empiezan por lo escrito van primero**: quien
    escribe «calv» quiere «Calvarrasa de Abajo» y «Calvarrasa de Arriba» antes que
    «Villanueva de Calvarrasa» o lo que sea que lo lleve en medio. Con la lista de la provincia
    delante se puede acotar, y así el que busca «santa» en Soria no ve medio España.
    """
    buscado = _quita_tildes(texto)
    if not buscado:
        return []
    prov = _quita_tildes(provincia) if provincia else ""
    empiezan: list[Municipio] = []
    contienen: list[Municipio] = []
    for municipio in municipios_de_cyl():
        if prov and _quita_tildes(municipio.provincia) != prov:
            continue
        nombre = _quita_tildes(municipio.nombre)
        if nombre.startswith(buscado):
            empiezan.append(municipio)
        elif buscado in nombre:
            contienen.append(municipio)
        if len(empiezan) + len(contienen) >= limite * 4:
            break
    ordenados = sorted(empiezan, key=lambda m: m.nombre) + sorted(
        contienen, key=lambda m: m.nombre
    )
    return ordenados[:limite]


# --------------------------------------------------------------------------
# Zona vulnerable a nitratos
# --------------------------------------------------------------------------

_RUTA_ZV_POR_DEFECTO = Path(
    os.environ.get("CUEDIGITAL_ZV_CYL_RUTA")
    or Path(__file__).resolve().parents[2] / "data" / "zv_cyl.csv"
)

# Dos claves inequívocas: código INE y pareja municipio/provincia.
_municipios_zv: set[str] | None = None
_cantidad_municipios_zv = 0


def _normaliza(texto: str) -> str:
    return " ".join(texto.strip().lower().split())


def cargar_zonas_vulnerables(ruta: Path | str | None = None) -> int:
    """Carga el listado oficial de municipios en zona vulnerable.

    Formato del CSV: `municipio,provincia,codigo_ine,zona_vulnerable`
    (la cabecera es obligatoria).
    Devuelve cuántos municipios ha cargado. Si el fichero no existe, deja el
    catálogo vacío y devuelve 0: la aplicación seguirá funcionando y preguntará
    al agricultor en vez de dar por hecho que no está en zona vulnerable.
    """
    global _municipios_zv, _cantidad_municipios_zv
    ruta = Path(ruta) if ruta else _RUTA_ZV_POR_DEFECTO
    cargados: set[str] = set()
    identificadores: set[str] = set()

    if ruta.exists():
        with ruta.open(encoding="utf-8", newline="") as fichero:
            for fila in csv.DictReader(fichero):
                municipio = (fila.get("municipio") or "").strip()
                if not municipio:
                    continue
                provincia = (fila.get("provincia") or "").strip()
                ine = (fila.get("codigo_ine") or "").strip()
                if ine:
                    cargados.add(f"ine:{ine}")
                    identificadores.add(f"ine:{ine}")
                if provincia:
                    cargados.add(f"nombre:{_normaliza(municipio)}|{_normaliza(provincia)}")
                    if not ine:
                        identificadores.add(f"nombre:{_normaliza(municipio)}|{_normaliza(provincia)}")

    _municipios_zv = cargados
    _cantidad_municipios_zv = len(identificadores)
    return _cantidad_municipios_zv


def hay_datos_zonas_vulnerables() -> bool:
    return bool(_municipios_zv)


def olvidar_zonas_vulnerables() -> None:
    """Vacía el catálogo cargado.

    Existe para los tests: uno que carga un listado de prueba no puede dejarlo puesto
    para el siguiente, o el orden de ejecución cambiaría los resultados. Un test que
    depende del orden no vale nada.
    """
    global _municipios_zv, _cantidad_municipios_zv
    _municipios_zv = None
    _cantidad_municipios_zv = 0


def es_zona_vulnerable(
    municipio: str | None, provincia: str | None = None, codigo_ine: str | None = None
) -> bool | None:
    """¿Está este municipio en zona vulnerable a nitratos?

    Devuelve True, False o None. None significa "no lo sé", y es importante que
    sea distinto de False: no se puede afirmar que una parcela no está en zona
    vulnerable si no se ha cargado el listado oficial.
    """
    if _municipios_zv is None:
        cargar_zonas_vulnerables()
    if not _municipios_zv:
        return None
    comprobaciones = []
    if codigo_ine and codigo_ine.strip():
        comprobaciones.append(f"ine:{codigo_ine.strip()}" in _municipios_zv)
    if municipio and provincia:
        comprobaciones.append(
            f"nombre:{_normaliza(municipio)}|{_normaliza(provincia)}" in _municipios_zv
        )
    # Si uno de los dos identificadores está mal escrito, la coincidencia positiva
    # del otro sigue siendo evidencia de zona vulnerable: no generar un falso negativo.
    if comprobaciones:
        return any(comprobaciones)
    return None


# --------------------------------------------------------------------------
# Plazos legales
#
# **Cada fecha lleva su norma al lado.** Estas tres fechas se le enseñan al agricultor y deciden
# cosas (si puede seguir en papel, si el registro tiene que ser electrónico), así que no pueden
# salir de un resumen ni de la memoria de nadie: están comprobadas en los textos consolidados del
# BOE el 24/09/2026 y el porqué está escrito entero, con las comillas literales y los enlaces, en
# `docs/LO_QUE_OBLIGA_LA_LEY.md`. Un test compara las dos cosas, así que cambiar una fecha aquí sin
# cambiar el documento rompe la suite.
#
# El dato que más se equivoca es el del papel: el Real Decreto 34/2025 (21/01/2025) decía «hasta el
# 31 de diciembre de 2025» y el Real Decreto 1039/2025 (19/11/2025) lo cambió a 2026. Quien lea solo
# el primero se equivoca de año.
# --------------------------------------------------------------------------

# RD 1311/2012, artículo 16.1, último párrafo (modificado por la disposición final primera del
# Real Decreto 1039/2025, de 19 de noviembre): en ámbitos agrarios se puede mantener el registro de
# tratamientos «en soporte papel hasta el 31 de diciembre de 2026».
FECHA_FIN_CUADERNO_PAPEL = dt.date(2026, 12, 31)

# El día siguiente: el Reglamento de Ejecución (UE) 2023/564, de 10 de marzo de 2023, obliga a que
# el registro de tratamientos sea electrónico para los operadores agrarios a partir del 01/01/2026,
# y el Real Decreto 34/2025 sincronizó la fecha española con la europea (dejando el papel hasta
# 31/12/2026, ver arriba).
FECHA_REGISTRO_ELECTRONICO_FITOSANITARIOS = dt.date(2027, 1, 1)

# RD 1051/2022, disposición final única: el artículo 5 (registro de las operaciones de fertilización
# en el cuaderno de explotación) surte efectos desde el 1 de enero de 2026.
FECHA_REGISTRO_OBLIGATORIO_FERTILIZACION = dt.date(2026, 1, 1)

# RD 1051/2022, artículo 4.2: el plan de abonado es obligatorio en cada unidad de producción a
# partir del 1 de septiembre de 2026; en las unidades en regadío cuyo cultivo se sembró o plantó
# entre el 1 de marzo y el 30 de junio de 2026, desde el 1 de enero de 2026.
FECHA_PLAN_DE_ABONADO_OBLIGATORIO = dt.date(2026, 9, 1)

# RD 1054/2022, artículo 10.2 (redacción del RD 34/2025): «Los titulares de explotaciones agrarias
# decidirán de forma voluntaria poner a disposición de la administración, a través de los REA
# correspondientes, la información que hayan cumplimentado en el CUE.» Es decir: **tener** el
# registro es obligatorio; **mandarlo**, no. Se guarda aquí para que la pantalla y la ayuda puedan
# decir la verdad sin escribirla a mano en cada sitio.
ENVIAR_EL_CUADERNO_A_LA_JUNTA_ES_VOLUNTARIO = True

# RD 1054/2022, artículo 10.3: se puede usar «cualquier otro sistema informático de su elección,
# siempre que cumpla con los requisitos técnicos que se establezcan y con el contenido mínimo
# establecidos en el anexo II». Sin las comillas de la norma, esto es lo que hace legal a este
# programa como cuaderno.
SE_PUEDE_USAR_UN_PROGRAMA_PROPIO = True


# --------------------------------------------------------------------------
# Las reglas de abono en zona vulnerable a nitratos
#
# Hasta la ronda 11 la aplicación decía «en tu zona hay reglas más estrictas» y no decía
# cuáles, porque los límites concretos de la Orden MAV/398/2022 no estaban cargados. Pero sí
# están: **los recoge la propia Junta**, en la presentación «Zonas Vulnerables a la
# contaminación por nitratos en Castilla y León» (Consejería de Medio Ambiente, Vivienda y
# Ordenación del Territorio, abril de 2026), que está en la carpeta de documentación de
# referencia de este proyecto.
#
# Lo que se carga aquí es **lo que ese documento dice, con sus números**, y cada regla lleva
# escrita su fuente para que nadie tenga que preguntarse de dónde sale.
#
# Los Anexos III y V de la Orden ya están extraídos en `data/nitratos_cyl/`. Son
# referencias verificables. Todavía no equivalen a una comprobación automática:
# faltan el listado municipal de zonas vulnerables y varios datos que determinan
# cuándo comienza o termina un periodo relativo. No se inventan esas fechas.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ReglaNitratos:
    """Una regla del programa de actuación de las zonas vulnerables.

    `valor` es el número de la regla cuando la regla tiene un número. `fuente` dice de dónde
    sale, literal, para poder comprobarlo.
    """

    clave: str
    que: str
    valor: float | None
    unidad: str
    fuente: str
    # Lo que la aplicación hace con esta regla: `avisa` (se puede apuntar y se dice) o
    # `consulta` (tabla disponible, pero todavía sin comprobación automática) o
    # `sin_datos` (si se retira el fichero derivado).
    que_hace_la_app: str


FUENTE_ORDEN_MAV = (
    "Orden MAV/398/2022, de 29 de abril, programa de actuación de las zonas vulnerables de "
    "Castilla y León, recogido en la presentación «Zonas Vulnerables a la contaminación por "
    "nitratos en Castilla y León» (Consejería de Medio Ambiente, Vivienda y Ordenación del "
    "Territorio, abril de 2026)"
)

REGLAS_NITRATOS: tuple[ReglaNitratos, ...] = (
    ReglaNitratos(
        clave="estiercol_170",
        que="Aporte máximo de nitrógeno en forma de estiércoles y purines",
        valor=170.0,
        unidad="kg N/ha al año",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="avisa",
    ),
    ReglaNitratos(
        clave="pendiente_15",
        que="Con más del 15 % de pendiente solo se pueden aplicar abonos orgánicos sólidos",
        valor=15.0,
        unidad="% de pendiente",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="avisa",
    ),
    ReglaNitratos(
        clave="orilla_5_m",
        que="No se puede abonar en la zona de máxima crecida ni a menos de 5 m de ella",
        valor=5.0,
        unidad="metros",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="avisa",
    ),
    ReglaNitratos(
        clave="sin_cultivo",
        que=(
            "No se puede abonar en suelos agrícolas no cultivados, salvo que lo vayan a ser en "
            "menos de un mes"
        ),
        valor=None,
        unidad="",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="avisa",
    ),
    ReglaNitratos(
        clave="riesgo_escorrentia",
        que=(
            "No se puede abonar con riesgo de escorrentía: terreno inundado, helado o cubierto "
            "de nieve, o con suelo y pendiente desfavorables"
        ),
        valor=None,
        unidad="",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="avisa",
    ),
    ReglaNitratos(
        clave="forestal",
        que="No se puede echar abono orgánico en terreno forestal",
        valor=None,
        unidad="",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="avisa",
    ),
    ReglaNitratos(
        clave="aportes_por_cultivo",
        que="Aportes máximos de nitrógeno por cultivo del Anexo III de la Orden MAV/398/2022",
        valor=None,
        unidad="kg N/ha",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="consulta",
    ),
    ReglaNitratos(
        clave="periodos_prohibidos",
        que="Períodos en los que no se puede abonar cada cultivo (Anexo V de la Orden)",
        valor=None,
        unidad="",
        fuente=FUENTE_ORDEN_MAV,
        que_hace_la_app="consulta",
    ),
)

REGLAS_POR_CLAVE = {regla.clave: regla for regla in REGLAS_NITRATOS}


def reglas_nitratos() -> tuple[ReglaNitratos, ...]:
    """Estado real de las reglas, incluso si se retira el fichero de datos."""
    from dataclasses import replace

    cargado = bool(nitratos_cyl.aportes_maximos() and nitratos_cyl.periodos_prohibidos())
    salida = []
    for regla in REGLAS_NITRATOS:
        if regla.clave in ("aportes_por_cultivo", "periodos_prohibidos") and not cargado:
            salida.append(replace(regla, que_hace_la_app="sin_datos"))
        elif regla.clave == "aportes_por_cultivo" and hay_datos_zonas_vulnerables():
            salida.append(replace(regla, que_hace_la_app="avisa"))
        else:
            salida.append(regla)
    return tuple(salida)


def limites_que_faltan() -> tuple[str, ...]:
    """Solo señala fuentes realmente ausentes; una tabla cargada ya no 'falta'."""
    faltan = []
    if not nitratos_cyl.aportes_maximos():
        faltan.append("Los aportes máximos por cultivo del Anexo III no están cargados.")
    if not nitratos_cyl.periodos_prohibidos():
        faltan.append("Los períodos del Anexo V no están cargados; no se pueden consultar.")
    return tuple(faltan)


LIMITES_QUE_FALTAN: tuple[str, ...] = limites_que_faltan()


def regla_de_nitratos(clave: str) -> ReglaNitratos | None:
    return next((regla for regla in reglas_nitratos() if regla.clave == clave), None)


def limite_de_estiercol_kg_n_ha() -> float | None:
    """El tope de nitrógeno en forma de estiércoles, en kg N/ha al año.

    Devuelve `None` si la regla no estuviera cargada, para que quien la use tenga que decir
    «no lo sé» en vez de comparar contra un cero.
    """
    regla = REGLAS_POR_CLAVE.get("estiercol_170")
    return regla.valor if regla else None


def pendiente_maxima_para_organico_liquido() -> float | None:
    regla = REGLAS_POR_CLAVE.get("pendiente_15")
    return regla.valor if regla else None


def es_abono_organico(tipo: str | None) -> bool:
    """¿Este abono es estiércol, purín o una mezcla?

    La regla de los 170 kg va sobre los estiércoles, así que hay que saber distinguirlos de los
    de fábrica. El mineral puro no cuenta; el orgánico y el órgano-mineral sí.
    """
    return (tipo or "") in ("organico", "organo-mineral")
