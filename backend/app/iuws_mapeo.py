"""El mapeo del cuaderno al formato oficial: qué campo oficial sale de qué dato nuestro.

## Para qué sirve esto, y para qué no

Sirve para responder, campo por campo, a la única pregunta que importa para poder mandar el
cuaderno: **¿este dato oficial lo tenemos?**. Y la respuesta no es sí o no:

| Estado | Qué significa | De quién depende |
|---|---|---|
| `se_puede` | Está en el cuaderno y el formato oficial lo admite (con su conversión) | De nadie: ya se puede |
| `hace_falta_catalogo` | El dato está, pero el interfaz lo quiere como **código numérico** | De FEGA: los catálogos |
| `a_medias` | Tenemos una parte y falta una pieza que **la aplicación no pregunta** | De nosotros: una casilla o una pantalla |
| `no_lo_tenemos` | El cuaderno **no recoge** ese dato | De nosotros: una pantalla nueva |

Esa separación es el motivo de que este módulo exista. Decir «faltan cosas» mezcla las cuatro y
entonces no se sabe si hay que escribir a FEGA, escribir una pantalla o no hacer nada.

Lo que **no** hace: no inventa códigos. Cuando un campo necesita un código y no lo hay, el campo
**no se pone** y se dice que falta. Poner un `0` sería mandar «el producto 0», que no es «no lo
sé»: es un dato falso con formato válido, que es la peor clase de error.

## Cómo se comprueba que el mapeo no está inventado

Cada entrada lleva la **ruta del campo dentro del esquema JSON oficial**, y hay tests que
recorren esa ruta en el esquema de verdad y comprueban que el campo existe ahí, con ese nombre y
con un tipo compatible. También se comprueba que los campos marcados como obligatorios son
**exactamente** los que el esquema declara obligatorios, y que ningún catálogo que se cite aquí
es inventado: todos tienen que estar entre los que el descriptor oficial nombra.

## Ojo: el esquema no solo dice tipos

El esquema tiene, además de los tipos, **5 restricciones `oneOf`** y 45 cotas numéricas
(`minimum`/`maximum`). Las cinco `oneOf` son de dos clases:

- **El equipo de aplicación** (en tratamientos, postcosecha, instalaciones y fertilización)
  tiene que llevar **uno** de estos tres: número de ROMA, número de REGANIP o nuestro propio
  identificador de equipo. No los tres, ni ninguno: uno.
- **`CambioCultivoDGC.FechaFin`**, que admite dos formas.

Esto no se ve mirando los tipos, y es la clase de detalle que hace que un paquete «bien hecho»
lo rechacen. Se descubrió construyendo un ejemplo completo contra el validador.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from . import catalogos_siex, iuws_descriptor

# --------------------------------------------------------------------------
# Las dos conversiones que sí se pueden hacer hoy, y por qué son así
# --------------------------------------------------------------------------

# El formato de fecha del interfaz. **No es ISO**, y esto costó un rato: el esquema oficial
# declara `minLength: 10, maxLength: 10` y este patrón. Un `2026-05-01` mide 10 caracteres
# igual, pero **no cumple el patrón**: el primer grupo tiene que ser el día. Se comprobó con el
# validador del propio esquema, no a ojo.
PATRON_DE_FECHA_OFICIAL = r"^(0?[1-9]|[12][0-9]|3[01])[/\-](0?[1-9]|1[012])[/\-]\d{4}$"

# El identificador ajeno es un **número** de hasta 10 dígitos. El `CD-70922320A-T-14` que usa la
# aplicación por dentro **no vale** para el interfaz: es un identificador estupendo para
# rastrear, pero el campo oficial es `integer`. Para el interfaz se manda el número de la fila,
# que no cambia nunca y sirve para lo único que sirve ese campo: que la Junta reconozca la misma
# actividad si se vuelve a mandar, en vez de duplicarla.
MAXIMO_IDENTIFICADOR = 9_999_999_999


def fecha_oficial(valor) -> str | None:
    """La fecha en el formato que pide el interfaz (`dd/mm/aaaa`), o `None`.

    Devuelve `None` si no hay fecha o si no se entiende: **nunca** una fecha inventada. Un
    `None` aquí significa «este campo no se puede poner», y quien llama tiene que decirlo, no
    rellenarlo con la de hoy.
    """
    if valor is None or valor == "":
        return None
    if isinstance(valor, dt.datetime):
        valor = valor.date()
    if isinstance(valor, dt.date):
        return f"{valor.day:02d}/{valor.month:02d}/{valor.year:04d}"
    texto = str(valor).strip()
    # Una fecha en ISO, que es como la compara y la ordena el programa por dentro. Se parsea en
    # vez de mirar el dibujo: `2026-13-45` tiene la forma de una fecha y no es una fecha, y un
    # mes 13 mandado a la Junta es un dato falso con formato válido.
    try:
        return dt.date.fromisoformat(texto).strftime("%d/%m/%Y")
    except ValueError:
        pass
    if re.fullmatch(PATRON_DE_FECHA_OFICIAL, texto):
        return texto
    return None


def identificador_oficial(registro) -> int | None:
    """El identificador que se manda al interfaz para una actividad: su número de fila.

    Se usa la clave de la tabla porque es lo único que cumple las tres condiciones de ese campo:
    es numérico, **no cambia nunca** y es único dentro de la explotación. Un identificador que
    cambiara entre dos envíos haría que la Junta no reconociera la actividad y la duplicara, que
    es justo lo que este campo evita.

    El `CD-…` de `iuws.id_ajeno` sigue siendo el identificador de la aplicación para rastrear y
    para el volcado en el orden del contenido mínimo, pero **no es el que va aquí**.
    """
    interno = getattr(registro, "id", None)
    if not isinstance(interno, int) or interno <= 0:
        return None
    if interno > MAXIMO_IDENTIFICADOR:
        return None
    return interno


# --------------------------------------------------------------------------
# La correspondencia, campo por campo
# --------------------------------------------------------------------------

SE_PUEDE = "se_puede"
HACE_FALTA_CATALOGO = "hace_falta_catalogo"
A_MEDIAS = "a_medias"
NO_LO_TENEMOS = "no_lo_tenemos"

ESTADOS = (SE_PUEDE, HACE_FALTA_CATALOGO, A_MEDIAS, NO_LO_TENEMOS)

# Qué tipo del esquema oficial le corresponde a cada tipo nuestro, para poder comprobarlo.
TIPOS_COMPATIBLES = {
    "numero": {"integer", "number"},
    "texto": {"string"},
    "fecha": {"string"},
    "booleano": {"boolean"},
    "lista": {"array"},
    "objeto": {"object"},
}


@dataclass(frozen=True)
class Correspondencia:
    """Un campo oficial, de dónde sale y qué le falta."""

    oficial: str
    ruta: str
    estado: str
    tipo: str
    obligatorio: bool
    de: str | None = None
    catalogo: str | None = None
    nota: str = ""


# El bloque de los tratamientos fitosanitarios. Los nombres y las rutas están copiados del
# esquema oficial v3.11.4, y hay un test que los comprueba uno a uno contra el esquema.
TRATAMIENTO_FITO: tuple[Correspondencia, ...] = (
    Correspondencia(
        oficial="IdAjenaTratamFito",
        ruta="IdAjenaTratamFito",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=True,
        de="id",
        nota="El número de la fila, no el identificador `CD-…` de la aplicación.",
    ),
    Correspondencia(
        oficial="FechaInicio",
        ruta="FechaInicio",
        estado=SE_PUEDE,
        tipo="fecha",
        obligatorio=True,
        de="fecha",
        nota="Se convierte a `dd/mm/aaaa`: el interfaz no admite ISO.",
    ),
    Correspondencia(
        oficial="FechaFin",
        ruta="FechaFin",
        estado=SE_PUEDE,
        tipo="fecha",
        obligatorio=True,
        de="fecha",
        nota="El cuaderno apunta un solo día, así que fin e inicio son el mismo.",
    ),
    Correspondencia(
        oficial="HoraTratamiento",
        ruta="HoraTratamiento",
        estado=SE_PUEDE,
        tipo="texto",
        obligatorio=False,
        de="hora_inicio",
        nota="El interfaz solo tiene una hora: la de fin del cuaderno no tiene destino.",
    ),
    Correspondencia(
        oficial="Observaciones",
        ruta="Observaciones",
        estado=SE_PUEDE,
        tipo="texto",
        obligatorio=False,
        de="observaciones",
    ),
    Correspondencia(
        oficial="DGCs",
        ruta="DGCs",
        estado=NO_LO_TENEMOS,
        tipo="lista",
        obligatorio=True,
        nota=(
            "Es lo que dice **en qué parcela** se trató. El cuaderno sí sabe la superficie, pero "
            "no guarda aún la correspondencia IUWS de la DGC. El Anexo VI, apartado crear, "
            "dice que el CUE comercial genera el identificador único de una DGC nueva. Falta "
            "definir y persistir la asignación y confirmar el ámbito de unicidad."
        ),
    ),
    Correspondencia(
        oficial="ProblematicaFito",
        ruta="ProblematicaFito",
        estado=HACE_FALTA_CATALOGO,
        tipo="objeto",
        obligatorio=True,
        de="plaga",
        catalogo="Plagas",
        nota=(
            "El cuaderno guarda la plaga **como texto** («Pulgon») y el interfaz la quiere como "
            "código. Y no es un catálogo solo: este contenedor necesita **cuatro** listas —plagas, "
            "enfermedades, malas hierbas y reguladores del crecimiento—, que son las que el "
            "descriptor declara dentro. Hacen falta los catálogos **y** la equivalencia entre el "
            "texto que se escribe y el código. Con el catálogo solo, sigue sin poderse."
        ),
    ),
    Correspondencia(
        oficial="Justificaciones",
        ruta="Justificaciones",
        estado=HACE_FALTA_CATALOGO,
        tipo="lista",
        obligatorio=True,
        de="justificacion",
        catalogo="Justificación de la Actuación",
        nota="Igual que la plaga: el cuaderno la tiene escrita y el interfaz la quiere por código.",
    ),
    Correspondencia(
        oficial="IdentificadorAplicador",
        ruta="IdentificadorAplicador",
        estado=SE_PUEDE,
        tipo="lista",
        obligatorio=True,
        de="aplicador_id",
        nota=(
            "Se puede armar entero: el número de ROPO del aplicador está en el cuaderno, el "
            "equipo se identifica con el número de ROMA o de REGANIP (el esquema exige **uno** "
            "de los tres, `oneOf`), y `AplicacionManual` se pregunta desde que se mapeó esto. "
            "Siempre que el tratamiento tenga apuntados el aplicador y el equipo: si no, no hay "
            "nada que mandar, y eso es un dato que falta, no un hueco del programa."
        ),
    ),
    Correspondencia(
        oficial="Eficacia",
        ruta="Eficacia",
        estado=HACE_FALTA_CATALOGO,
        tipo="numero",
        obligatorio=True,
        de="eficacia",
        catalogo="Eficacia del tratamiento",
        nota=(
            "El cuaderno ya pregunta cómo de bien funcionó el tratamiento (`eficacia`, con "
            "cuatro respuestas nuestras para que el agricultor pueda contestar sin saber códigos). "
            "Lo que falta es el catálogo oficial **y** la equivalencia entre esas cuatro "
            "respuestas y sus códigos: con el catálogo solo, sigue sin poderse, y esa equivalencia "
            "no se supone."
        ),
    ),
    Correspondencia(
        oficial="ProductosFito",
        ruta="ProductosFito",
        estado=A_MEDIAS,
        tipo="lista",
        obligatorio=False,
        de="producto_id",
        catalogo="tipos de producto",
        nota=(
            "Del producto se tienen el número de registro, la dosis, la cantidad, el tipo y su "
            "unidad como texto. Faltan los códigos de `TipoProducto` y `Unidad` (`tipos de producto` y "
            "`Unidades de Medida`). Y `MateriaActiva` el interfaz lo quiere **numérico**, "
            "mientras el cuaderno guarda el nombre de la materia activa. Este bloque es "
            "**opcional** para el interfaz: lo que obliga a tenerlo no es el esquema, es que sin "
            "él un tratamiento no dice con qué se trató."
        ),
    ),
)


def correspondencia_del_tratamiento() -> tuple[Correspondencia, ...]:
    return TRATAMIENTO_FITO


# --------------------------------------------------------------------------
# El riego
#
# Sale de `Labor` (las labores de tipo riego). El cuaderno guarda el volumen, la unidad, el
# origen del agua, el sistema de riego y el número de contador: es uno de los bloques que más
# cerca está de poder mandarse, porque lo único que falta son **dos catálogos y el código de la
# parcela**.
# --------------------------------------------------------------------------

RIEGO: tuple[Correspondencia, ...] = (
    Correspondencia(
        oficial="IdAjenaRiego",
        ruta="IdAjenaRiego",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=True,
        de="id",
        nota="El número de la fila de la labor, no el `CD-…` de la aplicación.",
    ),
    Correspondencia(
        oficial="FechaInicio",
        ruta="FechaInicio",
        estado=SE_PUEDE,
        tipo="fecha",
        obligatorio=True,
        de="fecha",
    ),
    Correspondencia(
        oficial="FechaFin",
        ruta="FechaFin",
        estado=SE_PUEDE,
        tipo="fecha",
        obligatorio=True,
        de="fecha",
        nota="La labor de riego se apunta con un día, así que fin e inicio son el mismo.",
    ),
    Correspondencia(
        oficial="SistemaRiego",
        ruta="SistemaRiego",
        estado=HACE_FALTA_CATALOGO,
        tipo="numero",
        obligatorio=True,
        de="sistema_riego",
        catalogo="Sistema de Riego",
        nota=(
            "El cuaderno ya pregunta cómo se riega (aspersión, goteo, pivote…), con nombres "
            "nuestros. El interfaz quiere el código. El catálogo existe en SIEX "
            "(`SIST_RIEGO`); lo que falta son sus valores."
        ),
    ),
    Correspondencia(
        oficial="Cantidad",
        ruta="Cantidad",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=True,
        de="volumen_agua",
    ),
    Correspondencia(
        oficial="UnidadMedida",
        ruta="UnidadMedida",
        estado=HACE_FALTA_CATALOGO,
        tipo="numero",
        obligatorio=True,
        de="unidad_agua",
        catalogo="Unidades de Medida",
        nota="El cuaderno mide en m³, m³/ha o mm; el interfaz quiere el código (`UNIDADES_MEDIDA`).",
    ),
    Correspondencia(
        oficial="DGCs",
        ruta="DGCs",
        estado=NO_LO_TENEMOS,
        tipo="lista",
        obligatorio=True,
        nota="Es lo mismo que en los tratamientos: falta el código que dice en qué parcela se regó.",
    ),
    Correspondencia(
        oficial="NumContador",
        ruta="NumContador",
        estado=SE_PUEDE,
        tipo="texto",
        obligatorio=False,
        de="numero_contador",
        nota="El número del contador del agua, que el cuaderno ya recoge.",
    ),
    Correspondencia(
        oficial="OrigenAgua",
        ruta="OrigenAgua",
        estado=HACE_FALTA_CATALOGO,
        tipo="lista",
        obligatorio=False,
        de="origen_agua",
        catalogo="Origen del agua de riego",
        nota="Pozo, canal, balsa… con nombres nuestros; el interfaz quiere el código.",
    ),
    Correspondencia(
        oficial="TipoEnergia",
        ruta="TipoEnergia",
        estado=NO_LO_TENEMOS,
        tipo="numero",
        obligatorio=False,
        nota="Es la energía del bombeo, y el cuaderno no la recoge. Es opcional para el interfaz.",
    ),
    Correspondencia(
        oficial="BuenasPracticasRiego",
        ruta="BuenasPracticasRiego",
        estado=NO_LO_TENEMOS,
        tipo="lista",
        obligatorio=False,
        nota="El cuaderno no pregunta qué buenas prácticas de riego se siguieron. Es opcional.",
    ),
)


# --------------------------------------------------------------------------
# Siembra y plantación
#
# También sale de `Labor`. Y este es el bloque **más cerca de poder mandarse de todos**: de sus
# nueve campos obligatorios, ocho se pueden rellenar ya y **ninguno necesita un catálogo**. Lo
# único que falta es el código de la parcela.
# --------------------------------------------------------------------------

SIEMBRA_Y_PLANTACION: tuple[Correspondencia, ...] = (
    Correspondencia(
        oficial="IdAjenaSiembraPlant",
        ruta="IdAjenaSiembraPlant",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=True,
        de="id",
    ),
    Correspondencia(
        oficial="SiembraPlantacion",
        ruta="SiembraPlantacion",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=True,
        de="tipo",
        nota=(
            "**No es un catálogo**: el descriptor dice, con estas palabras, «1 Siembra 0 "
            "Plantación». El cuaderno ya distingue las labores de siembra de las de plantación, "
            "así que se traduce con esa convención y no hay que inventarse nada. Es la única "
            "convención de este tipo que se ha dado por buena, y es porque está escrita."
        ),
    ),
    Correspondencia(
        oficial="FechaInicio",
        ruta="FechaInicio",
        estado=SE_PUEDE,
        tipo="fecha",
        obligatorio=True,
        de="fecha",
    ),
    Correspondencia(
        oficial="FechaFin",
        ruta="FechaFin",
        estado=SE_PUEDE,
        tipo="fecha",
        obligatorio=True,
        de="fecha",
    ),
    Correspondencia(
        oficial="MaterialTratado",
        ruta="MaterialTratado",
        estado=SE_PUEDE,
        tipo="booleano",
        obligatorio=True,
        de="material_tratado",
    ),
    Correspondencia(
        oficial="MaterialAdquirido",
        ruta="MaterialAdquirido",
        estado=SE_PUEDE,
        tipo="booleano",
        obligatorio=True,
        de="material_adquirido",
    ),
    Correspondencia(
        oficial="FechaAdquisicion",
        ruta="FechaAdquisicion",
        estado=SE_PUEDE,
        tipo="fecha",
        obligatorio=True,
        de="fecha_adquisicion",
        nota="El esquema no le pone tipo a este campo, solo el patrón de fecha.",
    ),
    Correspondencia(
        oficial="Cantidad",
        ruta="Cantidad",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=True,
        de="cantidad_semilla_kg",
    ),
    Correspondencia(
        oficial="DGCs",
        ruta="DGCs",
        estado=NO_LO_TENEMOS,
        tipo="lista",
        obligatorio=True,
        nota=(
            "Es el **único** campo obligatorio que falta en este bloque. Con el código de la "
            "parcela, siembra y plantación se podría mandar entera."
        ),
    ),
    Correspondencia(
        oficial="SiembraDirecta",
        ruta="SiembraDirecta",
        estado=SE_PUEDE,
        tipo="booleano",
        obligatorio=False,
        de="siembra_directa",
    ),
    Correspondencia(
        oficial="DosisSiembra",
        ruta="DosisSiembra",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=False,
        de="dosis_siembra_kg_ha",
    ),
    Correspondencia(
        oficial="NumLote",
        ruta="NumLote",
        estado=SE_PUEDE,
        tipo="texto",
        obligatorio=False,
        de="lote_semilla",
    ),
    Correspondencia(
        oficial="DensidadPlantacion",
        ruta="DensidadPlantacion",
        estado=SE_PUEDE,
        tipo="numero",
        obligatorio=False,
        de="densidad_plantacion",
    ),
    Correspondencia(
        oficial="MarcoPlantacion",
        ruta="MarcoPlantacion",
        estado=SE_PUEDE,
        tipo="texto",
        obligatorio=False,
        de="marco_plantacion",
    ),
    Correspondencia(
        oficial="Maquinaria",
        ruta="Maquinaria",
        estado=A_MEDIAS,
        tipo="lista",
        obligatorio=False,
        de="equipo_id",
        nota=(
            "La siembra y la plantación son labores, así que desde la ronda 4 también dicen con "
            "qué máquina se hicieron. Faltan los mismos cinco datos de la máquina que en las "
            "labores (tipo UNE, potencia, unidades, energía, repeticiones y duración)."
        ),
    ),
)


# --------------------------------------------------------------------------
# La cosecha, el pastoreo, la cubierta y el resto de labores
#
# Los cuatro salen también de `Labor`. Y al mapearlos ha salido lo que de verdad falta en esta
# parte del cuaderno, que **no son catálogos**: son preguntas que la aplicación no hace.
# --------------------------------------------------------------------------

COSECHA: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaCosecha", "IdAjenaCosecha", SE_PUEDE, "numero", True, de="id"),
    Correspondencia(
        "CosechaSiega",
        "CosechaSiega",
        SE_PUEDE,
        "numero",
        True,
        de="tipo",
        nota=(
            "**No es un catálogo**: el descriptor dice «Indica si es cosecha/recolección (1) o "
            "siega», así que está escrito. El cuaderno tiene la labor de tipo cosecha → 1. **No "
            "tiene un tipo «siega»**: si algún día se añade, esta traducción hay que revisarla."
        ),
    ),
    Correspondencia("FechaInicio", "FechaInicio", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia("FechaFin", "FechaFin", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia(
        "SemillasSiembra",
        "SemillasSiembra",
        SE_PUEDE,
        "booleano",
        True,
        de="semillas_siembra",
        nota="Se pregunta en la cosecha; si se deja en blanco sigue siendo desconocido.",
    ),
    Correspondencia(
        "Plantas",
        "Plantas",
        SE_PUEDE,
        "booleano",
        True,
        de="plantas_cosechadas",
    ),
    Correspondencia(
        "SinCosechado",
        "SinCosechado",
        SE_PUEDE,
        "booleano",
        True,
        de="sin_cosechar_ambiental",
    ),
    Correspondencia(
        "DepositadoSuelo",
        "DepositadoSuelo",
        SE_PUEDE,
        "booleano",
        True,
        de="restos_cosecha_depositados",
    ),
    Correspondencia(
        "DGCs",
        "DGCs",
        NO_LO_TENEMOS,
        "lista",
        True,
        nota="Lo de siempre: falta el código que dice en qué parcela se cosechó.",
    ),
    Correspondencia(
        "Cantidad",
        "Cantidad",
        A_MEDIAS,
        "numero",
        False,
        de="detalles",
        nota=(
            "La cosecha permite apuntar `cantidad_kg` dentro de `detalles`, aunque sea opcional. "
            "No se sustituye por la cantidad vendida: puede quedar género en el almacén. "
            "Falta extraerla y validar la unidad oficial antes del envío."
        ),
    ),
    Correspondencia(
        "Unidad",
        "Unidad",
        HACE_FALTA_CATALOGO,
        "numero",
        False,
        catalogo="Unidades de Medida",
        nota="La cantidad de cosecha se apunta en kg; falta el código oficial de esa unidad.",
    ),
    Correspondencia(
        "GestionInsumos",
        "GestionInsumos",
        NO_LO_TENEMOS,
        "booleano",
        # El descriptor la marca obligatoria y el esquema **no**: ver el aviso del módulo.
        obligatorio=False,
        nota=(
            "El descriptor la marca como **obligatoria** y el esquema no la pide. El cuaderno no "
            "la recoge. Está apuntado como diferencia entre los dos documentos, sin decidir cuál "
            "manda: eso hay que preguntarlo."
        ),
    ),
)


PASTOREO: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaPastoreo", "IdAjenaPastoreo", SE_PUEDE, "numero", True, de="id"),
    Correspondencia("FechaInicio", "FechaInicio", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia("FechaFin", "FechaFin", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia(
        "AnimalesTerceros",
        "AnimalesTerceros",
        SE_PUEDE,
        "booleano",
        True,
        de="animales_terceros",
        nota=(
            "Se pregunta desde que se mapeó este bloque: es una de las lagunas que eran nuestras "
            "y no de nadie de fuera."
        ),
    ),
    Correspondencia(
        "AnimalesPropios",
        "AnimalesPropios",
        SE_PUEDE,
        "booleano",
        True,
        de="animales_propios",
        nota="La misma pregunta por el otro lado, en la misma pantalla del pastoreo.",
    ),
    Correspondencia(
        "DGCs",
        "DGCs",
        NO_LO_TENEMOS,
        "lista",
        True,
        nota="Falta el código que dice en qué parcela pastaron los animales.",
    ),
    Correspondencia(
        "Animales",
        "Animales",
        NO_LO_TENEMOS,
        "lista",
        False,
        nota=(
            "El detalle por animal (REGA, número y especie) es opcional, y la ganadería está "
            "fuera del alcance de esta aplicación a propósito."
        ),
    ),
)


DATOS_CUBIERTA: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaCubierta", "IdAjenaCubierta", SE_PUEDE, "numero", True, de="id"),
    Correspondencia(
        "FecEstablecimientoCub",
        "FecEstablecimientoCub",
        SE_PUEDE,
        "fecha",
        True,
        de="fecha_establecimiento_cubierta",
        nota=(
            "Se pregunta por separado la fecha de establecimiento. La fecha de la labor "
            "sigue siendo el día del mantenimiento."
        ),
    ),
    Correspondencia(
        "DGCs",
        "DGCs",
        NO_LO_TENEMOS,
        "lista",
        True,
        nota="Falta el código que dice en qué parcela se estableció la cubierta.",
    ),
    Correspondencia(
        "TipoCobertura",
        "TipoCobertura",
        HACE_FALTA_CATALOGO,
        "numero",
        False,
        catalogo="coberturas de suelo",
        de="tipo_cobertura",
        nota="Se pregunta en texto; falta cotejarlo con el código oficial.",
    ),
    Correspondencia(
        "AnchuraCubierta",
        "AnchuraCubierta",
        SE_PUEDE,
        "numero",
        False,
        de="anchura_cubierta_m",
    ),
    Correspondencia(
        "AnchuraLibreProy",
        "AnchuraLibreProy",
        SE_PUEDE,
        "numero",
        False,
        de="anchura_libre_proyeccion_m",
    ),
)


LABORES_CULTURALES: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaLabor", "IdAjenaLabor", SE_PUEDE, "numero", True, de="id"),
    Correspondencia("FechaInicio", "FechaInicio", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia("FechaFin", "FechaFin", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia(
        "TipoLabor",
        "TipoLabor",
        HACE_FALTA_CATALOGO,
        "numero",
        True,
        de="tipo",
        nota=(
            "El cuaderno sí sabe qué labor es (podar, labrar, escardar, desbrozar…). Lo que falta "
            "es el código. Y aquí hay algo raro que conviene decir: **el descriptor no cita "
            "ningún catálogo para este campo**, así que no se puede ni saber de dónde salen los "
            "códigos. Hay que preguntarlo."
        ),
    ),
    Correspondencia(
        "DGCs",
        "DGCs",
        NO_LO_TENEMOS,
        "lista",
        True,
        nota="Falta el código que dice en qué parcela se hizo la labor.",
    ),
    Correspondencia(
        "DepositadoSueloDesb",
        "DepositadoSueloDesb",
        SE_PUEDE,
        "booleano",
        False,
        de="restos_desbroce_depositados",
    ),
    Correspondencia(
        "DepositadoSueloPoda",
        "DepositadoSueloPoda",
        SE_PUEDE,
        "booleano",
        False,
        de="restos_poda_depositados",
    ),
    Correspondencia(
        "Maquinaria",
        "Maquinaria",
        A_MEDIAS,
        "lista",
        False,
        de="equipo_id",
        nota=(
            "Desde la ronda 4 la labor dice con qué máquina se hizo, y la máquina tiene ficha "
            "propia (nombre, tipo, nº ROMA, nº de serie y sus fechas de ITEAf). Sigue faltando el "
            "resto de los seis datos del anexo (tipo UNE, potencia, unidades de medida, energía, "
            "repeticiones y duración del trabajo), que el cuaderno no pregunta."
        ),
    ),
)


# --------------------------------------------------------------------------
# Tres bloques que ya tienen sus datos básicos en el cuaderno. El estado se refiere a
# si sabemos traducir el dato al tipo oficial; no supone que tengamos todos los valores
# de catálogo ni que se pueda enviar hoy el bloque completo.
MEDIDA_PREVENTIVA_CULTURAL: tuple[Correspondencia, ...] = (
    Correspondencia(
        "IdMedidaPreventCultural", "IdMedidaPreventCultural", HACE_FALTA_CATALOGO,
        "numero", True, de="medida", catalogo="Medida preventiva/cultural",
        nota="La medida se guarda con una clave propia; falta su código oficial.",
    ),
)

ANALITICA: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaAna", "IdAjenaAna", SE_PUEDE, "numero", True, de="id"),
    Correspondencia(
        "MaterialAnalizado", "MaterialAnalizado", HACE_FALTA_CATALOGO,
        "numero", True, de="tipo", catalogo="Material analizado",
        nota="El tipo de muestra se guarda con una clave propia; falta su código oficial.",
    ),
    Correspondencia("Fecha", "Fecha", SE_PUEDE, "fecha", True, de="fecha_toma_muestra"),
    Correspondencia("Laboratorio", "Laboratorio", SE_PUEDE, "texto", False, de="laboratorio"),
    Correspondencia("Nif", "Nif", SE_PUEDE, "texto", False, de="nif_laboratorio"),
    Correspondencia("NumBoletin", "NumBoletin", SE_PUEDE, "texto", False, de="numero_informe"),
    Correspondencia(
        "TiposAnalisis", "TiposAnalisis", A_MEDIAS,
        "lista", False, de="tipo_analisis",
        nota="El cuaderno guarda el nombre escrito; falta cotejar el catálogo y traducirlo a código.",
    ),
    Correspondencia(
        "TiposSustancias", "TiposSustancias", A_MEDIAS,
        "lista", False, de="sustancia_detectada",
        nota="Hay un nombre escrito, pero falta cotejar el catálogo y la estructura de cada elemento.",
    ),
    Correspondencia(
        "ParametrosSuelo", "ParametrosSuelo", A_MEDIAS,
        "objeto", False, de="parametros",
        nota="Los parámetros se guardan, pero hay que traducir sus claves y unidades.",
    ),
    Correspondencia(
        "DGCs", "DGCs", NO_LO_TENEMOS, "lista", False,
        nota="La parcela es opcional aquí; falta confirmar la codificación de DGC.",
    ),
)

COMERCIALIZACION_VD: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaVenta", "IdAjenaVenta", SE_PUEDE, "numero", True, de="id"),
    Correspondencia("FechaInicio", "FechaInicio", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia(
        "FechaFin", "FechaFin", SE_PUEDE, "fecha", True, de="fecha_fin",
        nota="Si no hay fin del intervalo, la fecha de venta es también su fin.",
    ),
    Correspondencia(
        "ProductoVegetal", "ProductoVegetal", HACE_FALTA_CATALOGO,
        "numero", True, de="producto", catalogo="Producto vegetal",
        nota="El producto se escribe por nombre; falta su código oficial.",
    ),
    Correspondencia(
        "TipoVenta", "TipoVenta", A_MEDIAS, "numero", False, de="tipo",
        nota="El cuaderno distingue venta directa y comercializada; falta la equivalencia numérica oficial.",
    ),
    Correspondencia("Cantidad", "Cantidad", SE_PUEDE, "numero", True, de="cantidad"),
    Correspondencia(
        "Unidad", "Unidad", HACE_FALTA_CATALOGO,
        "numero", True, de="unidad", catalogo="Unidades de Medida",
        nota="La unidad se guarda como texto; falta su código oficial.",
    ),
)

USO_SEMILLA_TRATADA: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaSemillaTrat", "IdAjenaSemillaTrat", SE_PUEDE, "numero", True, de="id"),
    Correspondencia(
        "Tratamiento", "Tratamiento", A_MEDIAS, "numero", True,
        de="tratamiento_semilla",
        catalogo="tipos de tratamiento de semilla",
        nota=(
            "Desde la ronda 5 la siembra dice qué le echaron a la semilla, con el nombre del "
            "producto. Falta el CÓDIGO oficial del tipo de tratamiento, que no está publicado."
        ),
    ),
    Correspondencia(
        "Fecha", "Fecha", SE_PUEDE, "fecha", True, de="fecha_tratamiento_semilla",
        nota=(
            "Es la fecha en que se trató la semilla, que desde la ronda 5 se pregunta. La fecha de "
            "adquisición sigue guardándose aparte, porque son dos cosas distintas."
        ),
    ),
    Correspondencia(
        "Producto", "Producto", HACE_FALTA_CATALOGO, "numero", True,
        de="cultivo", catalogo="Producto (Cultivo)",
        nota="El cultivo está escrito por nombre; falta su código oficial.",
    ),
    Correspondencia("Cantidad", "Cantidad", SE_PUEDE, "numero", True, de="cantidad_semilla_kg"),
    Correspondencia(
        "Eficacia", "Eficacia", HACE_FALTA_CATALOGO, "numero", True,
        de="eficacia_tratamiento_semilla", catalogo="Eficacia del tratamiento",
        nota=(
            "Desde la ronda 5 se pregunta cómo funcionó el tratamiento de la semilla, con la misma "
            "lista que la de los tratamientos del campo. Falta el código oficial."
        ),
    ),
    Correspondencia(
        "IdAjenaSiembraPlant", "IdAjenaSiembraPlant", A_MEDIAS, "numero", False, de="id",
        nota="Tenemos el identificador de la siembra, pero el esquema omite este campo del descriptor.",
    ),
    Correspondencia("NumeroLote", "NumeroLote", SE_PUEDE, "texto", False, de="lote_semilla"),
    Correspondencia(
        "ProductosFito", "ProductosFito", NO_LO_TENEMOS, "lista", False,
        nota="La labor no guarda los productos usados al tratar la semilla.",
    ),
    Correspondencia("Observaciones", "Observaciones", SE_PUEDE, "texto", False, de="observaciones"),
)

PLAN_ABONADO: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaPlan", "IdAjenaPlan", SE_PUEDE, "numero", True, de="id"),
    Correspondencia("NecesidadUFN", "NecesidadUFN", SE_PUEDE, "numero", True, de="necesidad_n"),
    Correspondencia(
        "NecesidadUFP2O5", "NecesidadUFP2O5", A_MEDIAS, "numero", True,
        de="necesidad_p",
        nota="La pantalla pregunta fósforo (P); el interfaz pide P2O5. Hay que confirmar la unidad y convertir si procede.",
    ),
    Correspondencia(
        "NecesidadUFK2O", "NecesidadUFK2O", A_MEDIAS, "numero", True,
        de="necesidad_k",
        nota="La pantalla pregunta potasio (K); el interfaz pide K2O. Hay que confirmar la unidad y convertir si procede.",
    ),
    Correspondencia(
        "ObjetivoProduccion", "ObjetivoProduccion", SE_PUEDE, "numero", True,
        de="produccion_esperada_kg_ha",
    ),
    Correspondencia(
        "CultivoPrecedente", "CultivoPrecedente", HACE_FALTA_CATALOGO, "numero", True,
        de="cultivo_precedente", catalogo="productos",
        nota=(
            "Desde la ronda 6 el plan dice qué había sembrado el año anterior en esa parcela, "
            "deducido del historial de cultivos (no se pregunta: el programa ya lo sabe). Falta el "
            "CÓDIGO oficial del producto, que no está publicado."
        ),
    ),
    Correspondencia(
        "Herramienta", "Herramienta", SE_PUEDE, "booleano", True, de="herramienta",
        nota=(
            "Desde la ronda 6 se pregunta con un sí o un no si se usó un programa o una "
            "herramienta para hacer el plan, que es exactamente como lo pide el anexo. Por eso "
            "mapea directo y no hace falta ningún catálogo."
        ),
    ),
    Correspondencia(
        "FechaGeneracion", "FechaGeneracion", SE_PUEDE, "fecha", True,
        de="creado_en", nota="La fecha de creación del plan, convertida a día/mes/año.",
    ),
    Correspondencia(
        "DGCs", "DGCs", NO_LO_TENEMOS, "lista", True,
        nota="El plan sabe la parcela, pero falta confirmar su código oficial de DGC.",
    ),
)

# El alta de una DGC no es lo mismo que la ficha de una parcela: esta guarda el recinto
# SIGPAC, pero no todos los códigos de gestión autonómicos ni la fecha efectiva de alta.
ALTA_DGC: tuple[Correspondencia, ...] = (
    Correspondencia(
        "CodigoDGCAjena", "CodigoDGCAjena", A_MEDIAS, "numero", True, de="id",
        nota="El Anexo VI permite que el CUE comercial genere el ID ajeno; falta persistir una asignación estable y confirmar el ámbito de unicidad.",
    ),
    Correspondencia(
        "Provincia", "Provincia", A_MEDIAS, "texto", True, de="codigo_ine",
        nota="El código INE está, pero hay que separar y cotejar los dígitos de provincia.",
    ),
    Correspondencia(
        "Municipio", "Municipio", A_MEDIAS, "texto", True, de="codigo_ine",
        catalogo="sin especificar en el descriptor",
        nota="El código INE está, pero el descriptor no identifica el catálogo ni el formato municipal.",
    ),
    Correspondencia(
        "Agregado", "Agregado", NO_LO_TENEMOS, "numero", True,
        nota="La ficha no guarda el agregado SIGPAC como campo propio.",
    ),
    Correspondencia(
        "Zona", "Zona", NO_LO_TENEMOS, "numero", True,
        nota="La ficha no guarda la zona SIGPAC como campo propio.",
    ),
    Correspondencia("Poligono", "Poligono", SE_PUEDE, "numero", True, de="poligono"),
    Correspondencia("Parcela", "Parcela", SE_PUEDE, "numero", True, de="numero_parcela"),
    Correspondencia("Recinto", "Recinto", SE_PUEDE, "numero", True, de="numero_recinto"),
    Correspondencia(
        "FechaInicio", "FechaInicio", NO_LO_TENEMOS, "fecha", True,
        nota="La fecha de creación de la ficha no es necesariamente la de comienzo de la DGC.",
    ),
    Correspondencia(
        "Cultivo", "Cultivo", A_MEDIAS, "numero", True,
        catalogo="sin especificar en el descriptor",
        nota="Está en el cultivo de la parcela, no en su ficha, y falta el código oficial.",
    ),
    Correspondencia(
        "Variedad", "Variedad", A_MEDIAS, "numero", True,
        catalogo="sin especificar en el descriptor",
        nota="Está en el cultivo de la parcela, no en su ficha, y falta el código oficial.",
    ),
    Correspondencia(
        "SistemaExplotacion", "SistemaExplotacion", A_MEDIAS, "texto", True,
        de="sistema", nota="Se guarda secano/regadío, pero falta confirmar los valores admitidos.",
    ),
    Correspondencia(
        "SistCultivo", "SistCultivo", NO_LO_TENEMOS, "numero", True,
        nota="El sistema de cultivo numérico no se recoge en la ficha.",
    ),
    Correspondencia(
        "ReferenciaCatastral", "ReferenciaCatastral", SE_PUEDE, "texto", False,
        de="referencia_catastral",
        nota=(
            "Se guarda desde el 24/09/2026: la columna existe y se rellena cuando el agricultor "
            "pega la referencia del Catastro (de ella salen solos el polígono y la parcela). Si "
            "no la ha pegado, va vacía: no se calcula."
        ),
    ),
    Correspondencia("Superficie", "Superficie", SE_PUEDE, "numero", False, de="superficie_ha"),
)

CAMBIO_CULTIVO_DGC: tuple[Correspondencia, ...] = (
    Correspondencia("FechaInicio", "FechaInicio", SE_PUEDE, "fecha", True, de="fecha_inicio"),
    Correspondencia(
        "Cultivo", "Cultivo", HACE_FALTA_CATALOGO, "numero", True,
        de="especie", catalogo="Producto",
    ),
    Correspondencia(
        "Variedad", "Variedad", HACE_FALTA_CATALOGO, "numero", True,
        de="variedad", catalogo="Variedad",
    ),
    Correspondencia(
        "SistemaExplotacion", "SistemaExplotacion", A_MEDIAS, "texto", True,
        de="sistema", nota="Se guarda secano/regadío, pero falta confirmar los valores admitidos.",
    ),
    Correspondencia(
        "SistCultivo", "SistCultivo", NO_LO_TENEMOS, "numero", True,
        nota="La campaña no recoge este código numérico de sistema de cultivo.",
    ),
    Correspondencia(
        "CodigoDGC", "CodigoDGC", NO_LO_TENEMOS, "numero", False,
        nota="No se guarda el código de DGC asignado por la administración.",
    ),
    Correspondencia(
        "CodigoDGCAjena", "CodigoDGCAjena", A_MEDIAS, "numero", False,
        de="parcela_id", nota="El CUE comercial genera el ID ajeno; falta persistir su asignación estable y confirmar el ámbito de unicidad.",
    ),
    Correspondencia(
        "CodigoCultivo", "CodigoCultivo", A_MEDIAS, "numero", False, de="id",
        nota="Falta confirmar si el código interno del cultivo puede ser el de origen.",
    ),
)

ENERGIA_UTILIZADA: tuple[Correspondencia, ...] = (
    Correspondencia(
        "IdAjenaEnergia", "IdAjenaEnergia", NO_LO_TENEMOS, "numero", True,
        nota="No existe un apunte de consumo de energía del que salga un identificador.",
    ),
    Correspondencia("FechaInicio", "FechaInicio", NO_LO_TENEMOS, "fecha", False,
                   nota="No hay apuntes de consumo de energía fechados."),
    Correspondencia("FechaFin", "FechaFin", NO_LO_TENEMOS, "fecha", False,
                   nota="No hay apuntes de consumo de energía fechados."),
    Correspondencia("Cultivo", "Cultivo", NO_LO_TENEMOS, "numero", False,
                   catalogo="cultivos", nota="El consumo de energía no se vincula a un cultivo."),
    Correspondencia("TipoEnergia", "TipoEnergia", NO_LO_TENEMOS, "numero", False,
                   nota="No se pregunta qué energía se consumió."),
    Correspondencia("Cantidad", "Cantidad", NO_LO_TENEMOS, "numero", False,
                   nota="No se pregunta la cantidad de energía consumida."),
    Correspondencia("Unidad", "Unidad", NO_LO_TENEMOS, "numero", False,
                   nota="No se guarda una unidad de consumo de energía."),
)

TRATAMIENTOS_POSTCOSECHA: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaTratamPostco", "IdAjenaTratamPostco", SE_PUEDE, "numero", True, de="id"),
    Correspondencia("FechaActuacion", "FechaActuacion", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia(
        "ProductoVegetal", "ProductoVegetal", HACE_FALTA_CATALOGO, "numero", True,
        de="producto_cosechado", catalogo="Productos vegetales",
    ),
    Correspondencia(
        "Cantidad", "Cantidad", NO_LO_TENEMOS, "numero", True,
        nota="El apunte guarda cuánto producto se aplicó, no los kilos vegetales tratados.",
    ),
    Correspondencia(
        "ProblematicaFito", "ProblematicaFito", HACE_FALTA_CATALOGO,
        "objeto", True, de="plaga", catalogo="Plagas",
        nota="El texto de la plaga requiere los códigos y el tipo de problema.",
    ),
    Correspondencia(
        "Justificaciones", "Justificaciones", HACE_FALTA_CATALOGO,
        "lista", True, de="justificacion", catalogo="Justificación de la Actuación",
    ),
    Correspondencia(
        "ProductosFito", "ProductosFito", A_MEDIAS, "lista", True, de="producto_id",
        catalogo="tipos de producto",
        nota="Se pregunta tipo de producto y unidad en texto; faltan sus códigos oficiales.",
    ),
    Correspondencia(
        "IdentificadorAplicador", "IdentificadorAplicador", SE_PUEDE,
        "lista", True, de="aplicador_id",
        nota="Se arma con el aplicador y el equipo relacionados, como en el tratamiento de parcela.",
    ),
    Correspondencia(
        "Eficacia", "Eficacia", HACE_FALTA_CATALOGO, "numero", True,
        de="eficacia", catalogo="Eficacia del tratamiento",
    ),
    Correspondencia("Observaciones", "Observaciones", SE_PUEDE, "texto", False, de="observaciones"),
)

TRATAMIENTOS_EDIFICACIONES: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaTratamEdif", "IdAjenaTratamEdif", SE_PUEDE, "numero", True, de="id"),
    Correspondencia(
        "Edificaciones", "Edificaciones", A_MEDIAS, "lista", True,
        de="instalacion_id", nota="Se conoce la instalación, pero falta su código oficial y la forma de la lista.",
    ),
    Correspondencia("FechaActuacion", "FechaActuacion", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia(
        "ProblematicaFito", "ProblematicaFito", HACE_FALTA_CATALOGO,
        "objeto", True, de="plaga", catalogo="Plagas",
    ),
    Correspondencia(
        "Justificaciones", "Justificaciones", HACE_FALTA_CATALOGO,
        "lista", True, de="justificacion", catalogo="Justificación de la Actuación",
    ),
    Correspondencia(
        "ProductosFito", "ProductosFito", A_MEDIAS, "lista", True, de="producto_id",
        catalogo="tipos de producto",
        nota="Se pregunta tipo de producto y unidad en texto; faltan sus códigos oficiales.",
    ),
    Correspondencia(
        "IdentificadorAplicador", "IdentificadorAplicador", SE_PUEDE,
        "lista", True, de="aplicador_id",
    ),
    Correspondencia(
        "Eficacia", "Eficacia", HACE_FALTA_CATALOGO, "numero", True,
        de="eficacia", catalogo="Eficacia del tratamiento",
    ),
    Correspondencia("Observaciones", "Observaciones", SE_PUEDE, "texto", False, de="observaciones"),
)

FERTILIZACION: tuple[Correspondencia, ...] = (
    Correspondencia("IdAjenaFerti", "IdAjenaFerti", SE_PUEDE, "numero", True, de="id"),
    Correspondencia("FechaInicio", "FechaInicio", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia("FechaFin", "FechaFin", SE_PUEDE, "fecha", True, de="fecha"),
    Correspondencia(
        "BuenasPracticas", "BuenasPracticas", NO_LO_TENEMOS, "lista", True,
        nota="No se pregunta cuáles fueron las buenas prácticas de fertilización.",
    ),
    Correspondencia(
        "DGCs", "DGCs", NO_LO_TENEMOS, "lista", True,
        nota="La parcela está identificada internamente; falta el código DGC que acepta IUWS.",
    ),
    Correspondencia(
        "MaterialFertilizante", "MaterialFertilizante", A_MEDIAS, "objeto", False,
        de="fertilizante_id", nota="Hay ficha de fertilizante, dosis y nutrientes; faltan códigos y subcampos.",
    ),
    Correspondencia(
        "AplicacionMaterialFertilizante", "AplicacionMaterialFertilizante", A_MEDIAS,
        "objeto", False, de="modo_aplicacion",
        nota="El modo está escrito por nombre; faltan la estructura y códigos de aplicación.",
    ),
    Correspondencia(
        "EquipoAplicador", "EquipoAplicador", NO_LO_TENEMOS, "objeto", False,
        nota="El apunte de abonado no registra el equipo aplicador.",
    ),
    Correspondencia(
        "Fertirrigacion", "Fertirrigacion", A_MEDIAS, "objeto", False,
        nota="El agua se apunta en las labores de riego; falta unirla con esta fertilización.",
    ),
)


# Las diferencias entre descriptor y esquema, declaradas y con su motivo
#
# Mapear los 18 bloques ha sacado dos casos en los que los documentos oficiales **no encajan entre
# sí**. Se dejan escritos aquí, en vez de esconderlos en un test o de hacer como que no están: si
# se tapan, el día que alguien mire el mapeo va a creerse que los dos documentos dicen lo mismo.
# --------------------------------------------------------------------------

# Campos que el **descriptor** enumera y el **esquema no tiene**.
#
# En `Cosecha`, el descriptor marca `GestionInsumos` («Indica si hay gestión de insumos») como
# obligatoria, y el esquema JSON no la declara: ni obligatoria ni como propiedad. Como el esquema
# es lo que se valida antes de mandar, no se puede poner en el cuerpo (el validador la rechazaría
# por sobrar si el esquema no la admite en ningún sitio)… pero el descriptor la pide, así que
# **hay que preguntarlo** antes de fiarse de que con el esquema basta.
# **Campos que se calculan y no se guardan.** No son columnas de ninguna tabla, así que no pueden
# aparecer en `de=` como si lo fueran: un campo calculado se deduce de otros datos que sí están (el
# cultivo precedente, por ejemplo, sale del historial de cultivos de la campaña anterior).
#
# Se declaran aquí para que el test que comprueba que **ninguna fuente se inventa** pueda
# distinguir un dato de verdad de un nombre que no existe en ninguna parte. Sin esta lista, o no se
# podrían usar campos calculados, o el test dejaría de comprobar lo que comprueba.
CAMPOS_CALCULADOS: set[str] = {
    # El cultivo del año anterior en esa parcela: se deduce del historial de campañas.
    "cultivo_precedente",
}

CAMPOS_QUE_EL_ESQUEMA_NO_TIENE: dict[str, tuple[str, ...]] = {
    "Cosecha": ("GestionInsumos",),
    # El descriptor ofrece enlazar la semilla tratada con la siembra, pero el esquema no
    # acepta ese identificador. Es opcional y por eso no cambia el recuento de obligatorios.
    "UsoSemillaTratada": ("IdAjenaSiembraPlant",),
}

# Campos cuyo código hace falta y para los que el descriptor **no cita ningún catálogo**, así que
# no se puede ni saber de dónde salen los códigos. Se quedan sin nombre de catálogo y con la nota
# explicando qué hay que preguntar.
CAMPOS_SIN_CATALOGO_CITADO: dict[str, tuple[str, ...]] = {
    "LaboresCulturales": ("TipoLabor",),
}


def campo_que_el_esquema_no_tiene(bloque: str, campo: str) -> bool:
    return campo in CAMPOS_QUE_EL_ESQUEMA_NO_TIENE.get(bloque, ())


def campo_sin_catalogo_citado(bloque: str, campo: str) -> bool:
    return campo in CAMPOS_SIN_CATALOGO_CITADO.get(bloque, ())


# Los bloques que están mapeados a mano, por su nombre. Los demás tienen el mapa del lado de la
# Junta (qué piden y con qué catálogo) pero todavía no el del lado nuestro.
CORRESPONDENCIAS_POR_BLOQUE: dict[str, tuple[Correspondencia, ...]] = {
    "MedidaPreventivaCultural": MEDIDA_PREVENTIVA_CULTURAL,
    "TratamFito": TRATAMIENTO_FITO,
    "Riego": RIEGO,
    "SiembraPlantacion": SIEMBRA_Y_PLANTACION,
    "Cosecha": COSECHA,
    "Pastoreo": PASTOREO,
    "DatosCubierta": DATOS_CUBIERTA,
    "LaboresCulturales": LABORES_CULTURALES,
    "Analitica": ANALITICA,
    "ComercializacionVD": COMERCIALIZACION_VD,
    "UsoSemillaTratada": USO_SEMILLA_TRATADA,
    "PlanAbonado": PLAN_ABONADO,
    "AltaDGC": ALTA_DGC,
    "CambioCultivoDGC": CAMBIO_CULTIVO_DGC,
    "EnergiaUtilizada": ENERGIA_UTILIZADA,
    "TratamientosPostCosecha": TRATAMIENTOS_POSTCOSECHA,
    "TratamientosEdifInstalaciones": TRATAMIENTOS_EDIFICACIONES,
    "Fertilizacion": FERTILIZACION,
}


def correspondencia_de_un_bloque(bloque: str) -> tuple[Correspondencia, ...]:
    """La correspondencia a mano de ese bloque. Vacío si todavía no está mapeado."""
    return CORRESPONDENCIAS_POR_BLOQUE.get(bloque.strip(), ())


def bloques_mapeados() -> tuple[str, ...]:
    return tuple(CORRESPONDENCIAS_POR_BLOQUE)


def por_estado(
    campos: tuple[Correspondencia, ...],
) -> dict[str, list[Correspondencia]]:
    """Los campos agrupados por lo que hay que hacer con ellos.

    Es lo que convierte «faltan cosas» en una lista de tareas separadas: lo que depende de FEGA
    y lo que depende de que la aplicación pregunte el dato.
    """
    salida: dict[str, list[Correspondencia]] = {estado: [] for estado in ESTADOS}
    for campo in campos:
        salida[campo.estado].append(campo)
    return salida


# --------------------------------------------------------------------------
# El mapa del cuaderno ENTERO, sacado de los dos documentos oficiales
#
# El bloque de tratamientos de arriba está mapeado a mano, campo por campo, porque hace falta
# saber de qué dato del cuaderno sale cada uno. Eso no se puede deducir de ningún documento.
#
# Lo que **sí** se puede deducir —y por eso está aquí— es qué pide la Junta para cada uno de los
# 20 bloques: el esquema dice qué campos son obligatorios y el descriptor, en el mismo bloque,
# dice contra qué catálogo valida cada uno. Nada de esto se escribe a mano, así que no se puede
# quedar viejo ni inventado: sale de los dos ficheros oficiales cada vez que se pregunta.
# --------------------------------------------------------------------------

_esquema: dict | None = None


def esquema() -> dict:
    """El esquema JSON oficial, leído una vez."""
    global _esquema
    if _esquema is None:
        import json
        from pathlib import Path

        from . import iuws

        _esquema = json.loads(Path(iuws.RUTA_ESQUEMA_OFICIAL).read_text(encoding="utf-8"))
    return _esquema


def olvidar_esquema() -> None:
    """Vacía el esquema leído. Existe para los tests, igual que los demás cargadores."""
    global _esquema
    _esquema = None


def bloques_del_cuaderno() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Los bloques del cuaderno con sus campos obligatorios, tal y como los da el esquema.

    Devuelve `(sección, nombre del bloque, campos obligatorios)`. El orden es el del documento.
    """
    raiz = esquema()["properties"]["CUADERNO"]["items"]["properties"]
    salida: list[tuple[str, str, tuple[str, ...]]] = []
    for seccion in ("DatosExplotacion", "ActividadesExplotacion"):
        for nombre, definicion in raiz[seccion]["properties"].items():
            item = definicion.get("items", {})
            salida.append((seccion, nombre, tuple(item.get("required", ()))))
    return tuple(salida)


def _catálogos_de_un_campo(bloque_en_el_descriptor: str, campo: str) -> tuple[tuple[str, ...], bool]:
    """Los catálogos que el descriptor pide para ese campo, y si es un contenedor.

    Si el campo es un **contenedor** en el descriptor (`ProblematicaFito`, `Justificaciones`…), sus
    catálogos no están en el campo: están **dentro**, en sus listas y en los campos de dentro. Se
    recogen de ahí, porque dejarlos fuera haría que la lista de lo que hay que pedir a FEGA
    estuviera incompleta justo en lo que más bloquea.
    """
    directos = {
        c.catalogo
        for c in iuws_descriptor.campos_del_bloque(bloque_en_el_descriptor)
        if c.campo == campo and c.catalogo
    }
    if directos:
        return tuple(sorted(directos)), False

    ruta_del_contenedor = f"{bloque_en_el_descriptor}.{campo}"
    if ruta_del_contenedor not in iuws_descriptor.bloques():
        return (), False

    dentro = {c.catalogo for c in iuws_descriptor.campos_del_bloque(ruta_del_contenedor) if c.catalogo}
    dentro |= {
        catalogo
        for ruta, catalogo in iuws_descriptor.bloques_con_catalogo()
        if ruta.startswith(ruta_del_contenedor + ".")
    }
    return tuple(sorted(dentro)), True


# --------------------------------------------------------------------------
# De qué tabla nuestra sale cada bloque oficial
#
# El mapeo campo por campo de arriba es el de los tratamientos y está hecho a mano, porque saber
# de qué dato sale cada campo no lo dice ningún documento. Esto es el paso de antes, y sí se puede
# afirmar con seguridad: **de qué tabla del cuaderno sale cada bloque**. Es un dato sobre nuestro
# propio programa, y hay un test que comprueba que las tablas que se nombran existen de verdad.
#
# Sirve para dos cosas: saber qué queda por mapear a mano, y ver de un vistazo dónde están los
# agujeros. El único bloque del que no tenemos nada es el de la energía, y es a propósito: la app
# oficial de Castilla y León tampoco lo pide.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DeDondeSale:
    """De qué tabla del cuaderno sale un bloque oficial."""

    bloque: str
    tabla: str | None
    por: str = ""
    nota: str = ""


DE_DONDE_SALE_CADA_BLOQUE: tuple[DeDondeSale, ...] = (
    DeDondeSale("MedidaPreventivaCultural", "MedidaPreventivaDeclarada"),
    DeDondeSale(
        "AltaDGC",
        "Parcela",
        por="una fila por parcela",
        nota="Los recintos del SIGPAC que el agricultor ha dado de alta en «Mi finca».",
    ),
    DeDondeSale(
        "CambioCultivoDGC",
        "ParcelaCultivo",
        por="una fila por campaña",
        nota="Lo que hay sembrado en cada parcela y en cada año.",
    ),
    DeDondeSale(
        "EnergiaUtilizada",
        None,
        nota=(
            "El cuaderno no recoge el consumo de energía, y la app oficial de Castilla y León "
            "tampoco lo pide. Es el único bloque del que no tenemos nada."
        ),
    ),
    DeDondeSale(
        "TratamientosPostCosecha",
        "TratamientoFitosanitario",
        por="los de tipo postcosecha",
        nota="Es la misma tabla que los tratamientos, con otro tipo.",
    ),
    DeDondeSale(
        "TratamientosEdifInstalaciones",
        "TratamientoFitosanitario",
        por="los que van con una instalación",
        nota="Misma tabla: un tratamiento de almacén o de nave es un tratamiento con instalación.",
    ),
    DeDondeSale("UsoSemillaTratada", "Labor", por="el material tratado y su lote"),
    DeDondeSale("Cosecha", "Labor", por="las labores de tipo cosecha"),
    DeDondeSale(
        "SiembraPlantacion",
        "Labor",
        por="las labores de siembra y de plantación",
        nota="Con la semilla, la dosis, el marco y la densidad, que son columnas propias de Labor.",
    ),
    DeDondeSale("TratamFito", "TratamientoFitosanitario"),
    DeDondeSale("Fertilizacion", "RegistroFertilizacion"),
    DeDondeSale("PlanAbonado", "PlanAbonado"),
    DeDondeSale("DatosCubierta", "Labor", por="las labores de mantenimiento de la cubierta"),
    DeDondeSale("Pastoreo", "Labor", por="las labores de pastoreo"),
    DeDondeSale("Analitica", "Analitica"),
    DeDondeSale("ComercializacionVD", "VentaDeCosecha"),
    DeDondeSale("LaboresCulturales", "Labor", por="el resto de labores"),
    DeDondeSale(
        "Riego",
        "Labor",
        por="las labores de riego",
        nota=(
            "Con el volumen de agua, la unidad, el origen, el sistema de riego y el contador, que "
            "son columnas propias de Labor."
        ),
    ),
)


def de_donde_sale(bloque: str) -> DeDondeSale | None:
    """La tabla del cuaderno de la que sale ese bloque oficial, o `None` si no hay ninguna."""
    buscado = bloque.strip().lower()
    for entrada in DE_DONDE_SALE_CADA_BLOQUE:
        if entrada.bloque.lower() == buscado:
            return entrada
    return None


def bloques_sin_tabla() -> tuple[str, ...]:
    """Los bloques oficiales de los que el cuaderno no tiene nada."""
    return tuple(e.bloque for e in DE_DONDE_SALE_CADA_BLOQUE if e.tabla is None)


def _tablas_que_cubren_varios_bloques() -> dict[str, tuple[str, ...]]:
    cuenta: dict[str, list[str]] = {}
    for entrada in DE_DONDE_SALE_CADA_BLOQUE:
        if entrada.tabla:
            cuenta.setdefault(entrada.tabla, []).append(entrada.bloque)
    return {tabla: tuple(bloques) for tabla, bloques in cuenta.items() if len(bloques) > 1}


def _catalogo_en_otro_bloque(bloque: str, campo: str) -> str | None:
    """Si el mismo nombre de campo lleva catálogo en **otro** bloque del descriptor.

    Es información, no una conclusión: `Riego.SistemaRiego` no dice de qué catálogo sale, y en
    cambio `Fertilizacion.Fertirrigacion.SistemaRiego` sí lo dice. Que sea el mismo catálogo es
    lo más probable y **no se puede afirmar**, así que se apunta aparte y con eso se puede ir a
    preguntar.
    """
    for candidato in iuws_descriptor.campos():
        if candidato.campo != campo or not candidato.catalogo:
            continue
        if candidato.bloque.rsplit(".", 1)[-1].lower() != bloque.strip().lower():
            return candidato.catalogo
    return None


def mapa_del_cuaderno() -> tuple[dict, ...]:
    """Qué pide la Junta en cada uno de los 20 bloques, y con qué catálogo.

    Cada renglón es un bloque con sus campos obligatorios, y cada campo dice el catálogo que el
    descriptor le da, la tabla de SIEX si se sabe cuál es, y —cuando el descriptor no lo dice en
    ese bloque— si el mismo nombre de campo lleva catálogo en otro sitio.
    """
    filas = []
    for seccion, bloque, obligatorios in bloques_del_cuaderno():
        coinciden = iuws_descriptor.bloques_que_coinciden(bloque)
        en_el_descriptor = coinciden[0] if coinciden else None
        campos = []
        for campo in obligatorios:
            catalogos, es_contenedor = (
                _catálogos_de_un_campo(en_el_descriptor, campo)
                if en_el_descriptor
                else ((), False)
            )
            campos.append(
                {
                    "campo": campo,
                    "catalogos": list(catalogos),
                    "contenedor": es_contenedor,
                    "tablas_de_siex": {
                        nombre: (catalogos_siex.catalogo_de_siex(nombre) or {}).get("id")
                        for nombre in catalogos
                    },
                    "catalogo_en_otro_bloque": None
                    if catalogos
                    else _catalogo_en_otro_bloque(bloque, campo),
                }
            )
        filas.append(
            {
                "seccion": seccion,
                "bloque": bloque,
                "bloque_en_el_descriptor": en_el_descriptor,
                "obligatorios": len(obligatorios),
                # De qué tabla del cuaderno sale este bloque. Ver `DE_DONDE_SALE_CADA_BLOQUE`: es
                # lo que dice qué queda por mapear a mano y dónde están los agujeros.
                "de_donde_sale": _de_donde_sale_para_la_fila(bloque),
                # Casi todos los bloques de actividades obligan a decir **en qué parcela** pasó,
                # y eso es lo que el cuaderno todavía no sabe traducir a código de DGC.
                "necesita_las_parcelas": "DGCs" in obligatorios,
                "campos": campos,
            }
        )
    return tuple(filas)


def _de_donde_sale_para_la_fila(bloque: str) -> dict:
    entrada = de_donde_sale(bloque)
    if entrada is None:
        return {"tabla": None, "por": "", "nota": "sin mapear"}
    return {"tabla": entrada.tabla, "por": entrada.por, "nota": entrada.nota}


def resumen_del_cuaderno() -> dict:
    """El mapa del cuaderno entero, contado, para la pantalla de estado.

    Es la lista de la compra completa: qué catálogos hacen falta para poder mandar el cuaderno
    entero, cuántos bloques dependen de cada uno y cuáles ya tienen tabla localizada en SIEX.
    """
    filas = mapa_del_cuaderno()
    por_catalogo: dict[str, int] = {}
    for fila in filas:
        for campo in fila["campos"]:
            for nombre in campo["catalogos"]:
                por_catalogo[nombre] = por_catalogo.get(nombre, 0) + 1

    catalogos = []
    for nombre in sorted(por_catalogo):
        tabla = catalogos_siex.catalogo_de_siex(nombre)
        catalogos.append(
            {
                "nombre": nombre,
                "campos": por_catalogo[nombre],
                "tabla_de_siex": tabla["id"] if tabla else None,
            }
        )

    return {
        "bloques": len(filas),
        "obligatorios": sum(fila["obligatorios"] for fila in filas),
        "bloques_que_necesitan_las_parcelas": sum(
            1 for fila in filas if fila["necesita_las_parcelas"]
        ),
        "bloques_sin_descriptor": [
            fila["bloque"] for fila in filas if not fila["bloque_en_el_descriptor"]
        ],
        # De dónde sale cada bloque, y qué tablas nuestras cubren varios a la vez: `Labor` sola
        # cubre siete bloques oficiales, porque el cuaderno apunta las labores por su tipo.
        "bloques_sin_tabla": list(bloques_sin_tabla()),
        "tablas_que_cubren_varios_bloques": {
            tabla: list(bloques) for tabla, bloques in _tablas_que_cubren_varios_bloques().items()
        },
        "catalogos": catalogos,
        "catalogos_con_tabla": [c["nombre"] for c in catalogos if c["tabla_de_siex"]],
        "catalogos_sin_tabla": [c["nombre"] for c in catalogos if not c["tabla_de_siex"]],
        "mapa": list(filas),
    }


def catalogos_que_faltan(campos: tuple[Correspondencia, ...]) -> tuple[str, ...]:
    """Los catálogos que hacen falta para esos campos, sin repetir."""
    vistos: list[str] = []
    for campo in campos:
        if campo.catalogo and campo.catalogo not in vistos:
            vistos.append(campo.catalogo)
    return tuple(vistos)


def resumen_de_un_bloque(bloque: str) -> dict:
    """El estado de un bloque mapeado a mano, contado y en corto.

    Los catálogos se cotejan con los que pide el descriptor oficial de verdad, para no
    inventarse ninguno, y se cruzan con los que publica SIEX para decir **cuáles ya tienen tabla
    localizada** y cuáles hay que preguntar. Esa diferencia es lo que convierte «faltan los
    catálogos» en una lista de recados.
    """
    campos = correspondencia_de_un_bloque(bloque)
    grupos = por_estado(campos)
    del_descriptor = {nombre for nombre, _ in iuws_descriptor.catalogos_que_pide()}
    catalogos = catalogos_que_faltan(campos)
    con_tabla = {
        nombre: (catalogos_siex.catalogo_de_siex(nombre) or {}).get("id") for nombre in catalogos
    }
    obligatorios = [c for c in campos if c.obligatorio]
    return {
        "bloque": bloque,
        "campos": len(campos),
        "obligatorios": len(obligatorios),
        "se_pueden": [c.oficial for c in grupos[SE_PUEDE]],
        "obligatorios_que_se_pueden": [c.oficial for c in grupos[SE_PUEDE] if c.obligatorio],
        "hacen_falta_catalogos": [c.oficial for c in grupos[HACE_FALTA_CATALOGO]],
        "a_medias": [c.oficial for c in grupos[A_MEDIAS]],
        "no_lo_tenemos": [c.oficial for c in grupos[NO_LO_TENEMOS]],
        "catalogos": list(catalogos),
        "catalogos_confirmados_por_el_descriptor": [
            nombre for nombre in catalogos if nombre in del_descriptor
        ],
        # De los catálogos que este bloque necesita, cuáles ya tienen tabla en SIEX (con su
        # identificador) y cuáles no. Los que no, hay que preguntarlos.
        "catalogos_con_tabla": {n: t for n, t in con_tabla.items() if t},
        "catalogos_sin_tabla_localizada": [n for n, t in con_tabla.items() if not t],
    }


def resumen_del_tratamiento() -> dict:
    """El bloque de tratamientos, que es el que está mapeado con más detalle."""
    return resumen_de_un_bloque("TratamFito")


def resumen_de_los_bloques_mapeados() -> dict:
    """Todos los bloques mapeados a mano, con el total delante.

    El total es lo que se puede leer de un vistazo: de los campos obligatorios de los bloques ya
    mapeados, cuántos se pueden mandar ya y cuántos esperan un catálogo. Los bloques que faltan
    por mapear se dicen por su nombre, para que no parezca que están hechos.
    """
    bloques = [resumen_de_un_bloque(nombre) for nombre in bloques_mapeados()]
    return {
        "bloques_mapeados": list(bloques_mapeados()),
        "bloques_sin_mapear": [
            fila["bloque"]
            for fila in mapa_del_cuaderno()
            if fila["bloque"] not in CORRESPONDENCIAS_POR_BLOQUE
        ],
        "obligatorios": sum(b["obligatorios"] for b in bloques),
        "obligatorios_que_se_pueden": sum(len(b["obligatorios_que_se_pueden"]) for b in bloques),
        "detalle": {b["bloque"]: b for b in bloques},
    }
