"""Leer el cuaderno digital de explotación agrícola de Castilla y León (el Cuecyl).

## Qué es esto

La Consejería de Agricultura, Ganadería y Desarrollo Rural de Castilla y León tiene una
aplicación propia, el **Cuecyl**, para llevar el cuaderno digital. Su instrucciones oficiales
(«Instrucciones para la cumplimentación del cuaderno digital de explotación agrícola mediante la
aplicación informática desarrollada por la Comunidad de Castilla y León», enero de 2025) dicen
dos cosas que importan aquí:

1. **El cuaderno se puede llevar con esta aplicación o con cualquier otra**: «es decisión de los
   agricultores utilizar este cuaderno o bien un cuaderno digital comercial». Eso es lo que hace
   legal que este programa sirva para lo mismo (art. 10.3 del RD 1054/2022).
2. **El Cuecyl exporta el cuaderno a un libro de cálculo con 25 hojas** (el fichero que el
   agricultor descarga y guarda: `CuadernoExplotacion_<NIF>.xlsx`). Ese fichero es el que se lee
   aquí.

Las 25 hojas llevan la coletilla «(1)», «(2)»… y notas al pie numeradas. La hoja **1.1** son los
datos generales de la explotación y la **2.1** son las parcelas: esas dos son las que traen datos
de verdad, porque son las que vienen de la Solicitud Única. Las demás (fitosanitarios, semilla
tratada, análisis, comercialización, fertilización, datos agroambientales y las de ayudas
directas) son las que rellena el agricultor a lo largo de la campaña, y en un cuaderno recién
descargado están **vacías**.

## Las tres decisiones que hay que entender antes de tocar esto

1. **Se busca por la cabecera, no por la letra de la columna.** Aquí no hay ninguna tabla de
   «la columna K es la superficie». Las columnas se localizan por el texto de su cabecera
   («Superficie SIGPAC (ha)», «Especie/ Variedad»…), y si una hoja cambia de orden en otra
   versión, esto sigue funcionando. Además así se puede comprobar en un test que **todas** las
   columnas que se usan existen en el fichero oficial de verdad.
2. **Lo que está vacío se queda vacío, nunca en «no».** La casilla de «parcela ubicada en zona
   nitratos» viene marcada con «Sí» en las parcelas que lo están y **en blanco en todas las
   demás**: en blanco quiere decir «no lo han declarado», no «no está». Poner un `False` ahí
   sería inventarse una comprobación que nadie ha hecho, y es justo el error que este programa
   lleva toda la vida evitando.
3. **El fichero se lee entero antes de escribir nada.** La lectura devuelve un `CuadernoLeido`
   (una foto de lo que pone el papel) y quien lo llame decide qué hace con él. Así la pantalla
   puede enseñar «esto es lo que trae tu cuaderno» **antes** de dar de alta 54 parcelas, y los
   tests pueden comprobar la lectura sin base de datos ni servidor.

Todo lo que se lee de aquí viene **del papel que ha descargado el agricultor de la Junta**: no se
calcula, no se deduce y no se completa con lo que devolvería el SIGPAC. Lo del SIGPAC se pide en
otro sitio (`app/sigpac.py`), y solo cuando hace falta.
"""

from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata
from dataclasses import dataclass, field

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from zipfile import BadZipFile

from . import sigpac

# Los nombres de las hojas que se leen. Están tal y como los escribe la Junta, con sus puntos y
# sus espacios: el nombre se busca normalizado (sin acentos, sin mayúsculas y sin espacios de
# sobra) porque entre la versión de 2024 y la de 2026 hay hojas que se llaman «9.1 inf
# fertilización» y «9.1. INF. FERTILIZACIÓN», y no se puede depender de eso.
HOJA_GENERAL = "1.1. INF. GRAL"
HOJA_PARCELAS = "2.1. DATOS PARCELAS"

# El nombre que le da la Junta al fichero que descarga el agricultor. Se usa solo para poder dar
# un mensaje de error que se entienda cuando alguien sube otra cosa.
NOMBRE_DEL_FICHERO = "CuadernoExplotacion_<NIF>.xlsx"


class CuadernoIlegible(ValueError):
    """El fichero no es un cuaderno del Cuecyl, o no se puede abrir.

    El mensaje se enseña tal cual al agricultor, así que va en castellano y sin palabras raras.
    """


# --------------------------------------------------------------------------
# Utilidades de lectura de celdas
# --------------------------------------------------------------------------


def _sin_acentos(texto: str) -> str:
    """Quita tildes y deja el texto en minúsculas y con los espacios de sobra fuera.

    Hace falta porque el propio fichero oficial escribe «Telófono fijo» con tilde en la primera
    o (una errata de la plantilla) y «Nº Registro», y porque Windows y Linux no escriben igual
    los acentos. Comparando sin acentos, la errata deja de importar.
    """
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


def _texto(valor) -> str:
    """Una celda como texto limpio. Una celda vacía es cadena vacía, nunca `None`."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        # openpyxl devuelve 37.0 donde el papel pone 37. Un «37.0» en pantalla parece un error.
        return str(int(valor))
    return str(valor).strip()


def _numero(valor) -> float | None:
    """Una celda como número, o `None` si no hay número.

    Se acepta la coma decimal porque el agricultor puede escribir a mano en la plantilla, y lo
    que no sea un número devuelve `None` en vez de reventar: un cero sería peor que un hueco.
    """
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    limpio = str(valor).strip().replace(".", "").replace(",", ".")
    if not limpio:
        return None
    try:
        return float(limpio)
    except ValueError:
        return None


def _entero(valor) -> int | None:
    numero = _numero(valor)
    return int(numero) if numero is not None else None


def _fecha(valor) -> dt.date | None:
    """Una celda como fecha, aceptando lo que escribe una persona («14/03/2026»)."""
    if isinstance(valor, dt.datetime):
        return valor.date()
    if isinstance(valor, dt.date):
        return valor
    texto = _texto(valor)
    if not texto:
        return None
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _si_no(valor) -> bool | None:
    """«Sí» es sí, «No» es no, y **en blanco es «no lo sé»**.

    Ver la decisión 2 de la cabecera de este módulo: es la diferencia entre un dato comprobado y
    un dato inventado, y aquí se decide una vez para todo el módulo.
    """
    limpio = _sin_acentos(_texto(valor))
    if limpio in ("si", "s", "x", "1"):
        return True
    if limpio in ("no", "n", "0"):
        return False
    return None


# --------------------------------------------------------------------------
# Buscar las cosas por su etiqueta o por su cabecera
# --------------------------------------------------------------------------


def _celdas(hoja) -> list[tuple[int, int, str]]:
    """Todas las celdas con texto, como `(fila, columna, texto)`.

    Se recorre una sola vez por hoja y se guarda en memoria: las hojas del cuaderno son
    pequeñas y así no se recorre la misma hoja cinco veces buscando cinco etiquetas.
    """
    encontradas = []
    for fila in hoja.iter_rows():
        for celda in fila:
            if celda.value is None:
                continue
            texto = _texto(celda.value)
            if texto:
                encontradas.append((celda.row, celda.column, texto))
    return encontradas


def _etiquetas_conocidas(etiquetas: list[str]) -> set[str]:
    """Las etiquetas normalizadas, para no confundir una etiqueta con un valor.

    Esto es lo que evita el error clásico de este fichero: en la fila 8 de la hoja 1.1, el
    «Nº Registro de Explotaciones Nacional» **no tiene valor** y a su derecha está la etiqueta
    «Nº Registro de Explotaciones Autonómico». Leyendo «la celda de al lado» sin más, el número
    de registro autonómico acabaría siendo el nacional.
    """
    return {_sin_acentos(etiqueta) for etiqueta in etiquetas}


def _valor_de_una_etiqueta(
    celdas: list[tuple[int, int, str]],
    etiqueta: str,
    *,
    conocidas: set[str],
    desde_fila: int = 1,
    hasta_fila: int | None = None,
) -> str:
    """El valor que hay a la derecha de una etiqueta, o cadena vacía.

    Se busca la primera celda cuyo texto empiece por la etiqueta (para que «Dirección:» valga
    aunque el papel añada algo detrás) y se devuelve el primer texto a su derecha en la misma
    fila que **no sea otra etiqueta**.
    """
    objetivo = _sin_acentos(etiqueta)
    for fila, columna, texto in celdas:
        if fila < desde_fila or (hasta_fila is not None and fila > hasta_fila):
            continue
        if not _sin_acentos(texto).startswith(objetivo):
            continue
        candidatos = sorted(
            ((c, t) for f, c, t in celdas if f == fila and c > columna),
            key=lambda pareja: pareja[0],
        )
        for _columna, candidato in candidatos:
            # Si lo primero que hay a la derecha es **otra etiqueta**, es que esta no tiene
            # valor. Es el caso del «Nº Registro de Explotaciones Nacional» vacío: a su derecha
            # está la etiqueta del autonómico, y seguir buscando hacia la derecha haría que el
            # número autonómico acabara apuntado como nacional.
            if _sin_acentos(candidato) in conocidas:
                return ""
            return candidato
        return ""
    return ""


def _columna_de_la_cabecera(
    celdas: list[tuple[int, int, str]], etiqueta: str, *, filas: tuple[int, int]
) -> int | None:
    """En qué columna está una cabecera, buscándola por su texto.

    `filas` son las dos filas de cabecera del cuaderno (la de arriba y la de debajo, porque la
    plantilla parte los títulos en dos renglones). Se devuelve `None` si esa cabecera no está:
    así una hoja oficial distinta no revienta, y la lectura puede decir qué le falta.

    Se buscan dos cosas, y en este orden:

    1. Una cabecera que **empiece** por la etiqueta. Es lo que hace que «Zona» coja la columna
       «Zona» y no la de «Parcela ubicada en zona nitratos».
    2. Si no hay ninguna, una cabecera que la **contenga**. Es lo que hace falta para «zona
       nitratos», porque en el cuaderno esa columna se titula «Parcela ubicada en zona nitratos»
       y no empieza por las palabras que nos interesan.
    """
    objetivo = _sin_acentos(etiqueta)
    de_la_cabecera = [
        (fila, columna, _sin_acentos(texto))
        for fila, columna, texto in celdas
        if filas[0] <= fila <= filas[1]
    ]
    for _fila, columna, texto in de_la_cabecera:
        if texto.startswith(objetivo):
            return columna
    for _fila, columna, texto in de_la_cabecera:
        if objetivo in texto:
            return columna
    return None


# --------------------------------------------------------------------------
# Lo que se lee
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DatosGenerales:
    """La hoja 1.1: quién es el titular y cómo se llama su explotación."""

    nombre: str = ""
    nif: str = ""
    registro_nacional: str = ""
    registro_autonomico: str = ""
    direccion: str = ""
    localidad: str = ""
    codigo_postal: str = ""
    provincia: str = ""
    telefono_fijo: str = ""
    telefono_movil: str = ""
    correo: str = ""

    # El cuaderno tiene un bloque para el representante. Se lee y se dice si viene relleno,
    # porque el programa todavía no guarda esos datos (ver el aviso que se añade al leer).
    representante_nombre: str = ""
    representante_nif: str = ""

    @property
    def hay_representante(self) -> bool:
        return bool(self.representante_nombre or self.representante_nif)


@dataclass(frozen=True)
class LineaDeParcela:
    """Una línea de la hoja 2.1: una tierra con un cultivo y una superficie.

    **Es una línea, no una tierra.** El cuaderno oficial parte un mismo recinto en varias líneas
    cuando dentro de él hay cultivos distintos o distintas superficies cultivadas: en el cuaderno
    de 2026, el recinto 1 de la parcela 24 del polígono 507 aparece tres veces (barbecho 4,44 ha,
    avena 0,46 ha y avena 0,13 ha). Por eso esta clase se llama «línea» y por eso el resumen
    cuenta las dos cosas: las líneas y las tierras distintas.
    """

    orden: int
    referencia: sigpac.Referencia
    municipio_codigo: int | None
    municipio_nombre: str
    uso_sigpac: str
    superficie_sigpac_ha: float | None
    superficie_cultivada_ha: float | None
    especie: str
    variedad: str
    ecorregimen: str
    # secano | regadio | "" (en blanco en el papel: no lo han declarado)
    sistema: str
    principal_secundario: str
    fecha_inicio: dt.date | None
    fecha_fin: dt.date | None
    aire_libre_protegido: str
    # True / False / None. En blanco es None: «no lo han declarado», no «no está».
    zona_nitratos: bool | None

    @property
    def ref_sigpac(self) -> str:
        """La referencia como la guarda el cuaderno: «37-70-0-0-503-51»."""
        return self.referencia.como_texto()

    @property
    def tierra(self) -> str:
        """La clave de la tierra (el recinto), para contar cuántas hay de verdad."""
        return self.ref_sigpac

    @property
    def nombre_del_cultivo(self) -> str:
        return f"{self.especie} {self.variedad}".strip()


@dataclass
class CuadernoLeido:
    """Todo lo que trae el fichero, tal y como viene."""

    anio: int | None = None
    generales: DatosGenerales = field(default_factory=DatosGenerales)
    parcelas: list[LineaDeParcela] = field(default_factory=list)
    hojas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    # Los números de orden de las líneas que **se han leído pero no se han podido usar**, porque
    # no dicen el polígono, la parcela o el recinto. Se guardan aparte para que los números del
    # resumen cuadren: si el papel trae 8 líneas y 7 se pueden apuntar, la pantalla tiene que
    # poder decir «8 en el papel, 7 apuntadas, 1 sin poder». Un descuadre de uno, en un cuaderno,
    # es justo lo que hace que nadie se fíe del programa.
    lineas_ilegibles: list[int] = field(default_factory=list)

    @property
    def lineas_en_el_papel(self) -> int:
        return len(self.parcelas) + len(self.lineas_ilegibles)

    @property
    def tierras(self) -> int:
        return len({linea.tierra for linea in self.parcelas})

    @property
    def tierras_partidas(self) -> dict[str, int]:
        """Las tierras que el papel parte en varias líneas, con cuántas líneas tiene cada una."""
        cuantas: dict[str, int] = {}
        for linea in self.parcelas:
            cuantas[linea.tierra] = cuantas.get(linea.tierra, 0) + 1
        return {tierra: n for tierra, n in cuantas.items() if n > 1}

    @property
    def hectareas_declaradas(self) -> float:
        """La suma de la superficie cultivada, que es la que se declara.

        **Las líneas sin superficie no suman cero** (03/10/2026, la misma regla que A7): antes se hacía
        `linea.superficie_cultivada_ha or 0.0`, y una línea del cuaderno de la Junta a la que le falta la
        casilla de «Superficie Cultivada (ha)» se contaba como **0 hectáreas**. La suma salía más pequeña que
        la verdad y **parecía completa**. Ahora se suman solo las que la traen, y `lineas_sin_superficie`
        dice cuántas no la traen, para que quien lea el resumen sepa que esa cifra es parcial.
        """
        return round(
            sum(
                linea.superficie_cultivada_ha
                for linea in self.parcelas
                if linea.superficie_cultivada_ha is not None
            ),
            2,
        )

    @property
    def lineas_sin_superficie(self) -> int:
        """Las líneas del cuaderno leído que **no traen** la superficie cultivada.

        Es lo que permite decir «4,91 ha de 5 líneas, y de 2 no consta» en vez de enseñar una suma que parece
        completa cuando no lo es.
        """
        return sum(1 for linea in self.parcelas if linea.superficie_cultivada_ha is None)

    @property
    def hectareas_sigpac(self) -> float:
        return round(
            sum(
                linea.superficie_sigpac_ha
                for linea in self.parcelas
                if linea.superficie_sigpac_ha is not None
            ),
            2,
        )

    def municipios(self) -> list[str]:
        return sorted({linea.municipio_nombre for linea in self.parcelas if linea.municipio_nombre})

    def cultivos(self) -> list[str]:
        return sorted({linea.especie for linea in self.parcelas if linea.especie})

    def resumen(self) -> dict:
        """Los números que enseña la pantalla antes de dar nada de alta.

        Va aquí y no en la pantalla porque es lo mismo que se comprueba en los tests y lo mismo
        que se cuenta en la prueba de humo: una sola cuenta, un solo sitio.
        """
        return {
            "anio": self.anio,
            "lineas": self.lineas_en_el_papel,
            "lineas_leidas": len(self.parcelas),
            "lineas_ilegibles": len(self.lineas_ilegibles),
            "tierras": self.tierras,
            "tierras_partidas": len(self.tierras_partidas),
            "lineas_de_tierras_partidas": sum(self.tierras_partidas.values()),
            "hectareas_declaradas": self.hectareas_declaradas,
            "hectareas_sigpac": self.hectareas_sigpac,
            # Y **cuántas líneas no traen la superficie**, para que la suma de arriba no parezca completa
            # cuando no lo es (la misma regla que en A7: lo que no se sabe se declara, no se suma como cero).
            "lineas_sin_superficie": self.lineas_sin_superficie,
            "municipios": self.municipios(),
            "cultivos": self.cultivos(),
            "en_zona_nitratos": sum(1 for linea in self.parcelas if linea.zona_nitratos),
            "sin_secano_regadio": sum(1 for linea in self.parcelas if not linea.sistema),
            "avisos": list(self.avisos),
            "hojas": len(self.hojas),
        }


# --------------------------------------------------------------------------
# La lectura
# --------------------------------------------------------------------------

ETIQUETAS_GENERALES = [
    "NOMBRE Y APELLIDOS O RAZÓN SOCIAL:",
    "NIF:",
    "Nº Registro de Explotaciones Nacional:",
    "Nº Registro de Explotaciones Autonómico:",
    "Dirección:",
    "Localidad:",
    "C.Postal:",
    "Provincia:",
    "Telófono fijo:",
    "Telófono móvil:",
    "e-mail:",
    "Tipo de representación:",
    "Teléfono:",
    "TITULAR O REPRESENTANTE DE LA EXPLOTACIÓN",
    "1.1 DATOS GENERALES DE LA EXPLOTACIÓN",
]

CABECERAS_DE_PARCELA = {
    "orden": "Nº DE ORDEN",
    "provincia": "Código Provincia",
    "municipio": "Término municipal",
    "agregado": "Código Agregado",
    "zona": "Zona",
    "poligono": "Nº de Polígono",
    "parcela": "Nº de Parcela",
    "recinto": "Nº de Recinto",
    "uso": "Uso SIGPAC",
    "superficie_sigpac": "Superficie SIGPAC",
    "superficie_cultivada": "Superficie Cultivada",
    "especie": "Especie/ Variedad",
    "ecorregimen": "Ecoregimen/ Práctica",
    "sistema": "Secano/ Regadío",
    "principal": "Cultivo principal/ secundario",
    "fecha_inicio": "Fecha inicio cultivo",
    "fecha_fin": "Fecha fin cultivo",
    "aire_libre": "Aire libre o protegido",
    "zona_nitratos": "zona nitratos",
}

# Los dos renglones de cabecera de la hoja 2.1. No se fijan a mano: se localizan buscando la
# cabecera «Nº DE ORDEN», y de ahí salen las dos filas en las que se buscan las demás.
TEXTO_CABECERA_DE_ORDEN = "Nº DE ORDEN"


def _abrir(contenido: bytes):
    """Abre el libro de cálculo, con un mensaje claro si lo que han subido no es eso.

    `BadZipFile` se caza a propósito y no es un detalle: un fichero que no es un Excel (una foto
    de la factura, un PDF, un `.csv`) **no da un error de openpyxl, da un error de zip**, porque
    un `.xlsx` es un ZIP por dentro. Sin esta línea, subir el fichero que no era soltaba un
    «File is not a zip file» en inglés delante del agricultor.
    """
    try:
        return load_workbook(io.BytesIO(contenido), data_only=True)
    except (
        InvalidFileException,
        BadZipFile,
        KeyError,
        OSError,
        ValueError,
        TypeError,
    ) as fallo:
        raise CuadernoIlegible(
            "Ese fichero no se puede abrir. Sube el cuaderno que descargas de la Junta "
            f"({NOMBRE_DEL_FICHERO}), que es un fichero de Excel."
        ) from fallo


def _hoja(libro, nombre_buscado: str):
    """Una hoja por su nombre, comparando sin acentos ni mayúsculas."""
    objetivo = _sin_acentos(nombre_buscado)
    for nombre in libro.sheetnames:
        if _sin_acentos(nombre) == objetivo:
            return libro[nombre]
    return None


def _leer_generales(hoja) -> tuple[DatosGenerales, list[str]]:
    """La hoja 1.1: los datos del titular y de la explotación, y el representante si lo hay."""
    celdas = _celdas(hoja)
    conocidas = _etiquetas_conocidas(ETIQUETAS_GENERALES)

    # La fila donde empieza el bloque del representante. Se busca porque los dos bloques tienen
    # la misma etiqueta («NIF:», «Dirección:»…) y sin separarlos se leería el del titular dos
    # veces y el del representante ninguna.
    fila_representante = next(
        (
            fila
            for fila, _columna, texto in celdas
            if _sin_acentos(texto).startswith("titular o representante")
        ),
        None,
    )

    def valor(etiqueta: str, desde: int = 1, hasta: int | None = None) -> str:
        return _valor_de_una_etiqueta(
            celdas, etiqueta, conocidas=conocidas, desde_fila=desde, hasta_fila=hasta
        )

    avisos: list[str] = []
    if fila_representante is not None:
        representante_nombre = valor("Nombre y apellidos:", desde=fila_representante)
        representante_nif = valor("NIF:", desde=fila_representante)
    else:
        # Sin encabezado de representante, el bloque no está: se lee el nombre del titular y ya.
        representante_nombre = ""
        representante_nif = ""

    generales = DatosGenerales(
        nombre=valor("NOMBRE Y APELLIDOS O RAZÓN SOCIAL:"),
        nif=valor("NIF:"),
        registro_nacional=valor("Nº Registro de Explotaciones Nacional:"),
        registro_autonomico=valor("Nº Registro de Explotaciones Autonómico:"),
        direccion=valor("Dirección:"),
        localidad=valor("Localidad:"),
        codigo_postal=valor("C.Postal:"),
        provincia=valor("Provincia:"),
        # El fichero oficial escribe «Telófono» con tilde en la primera o: es una errata de la
        # plantilla, así que se busca sin acentos y la errata deja de importar.
        telefono_fijo=valor("Telófono fijo:") or valor("Teléfono fijo:"),
        telefono_movil=valor("Telófono móvil:") or valor("Teléfono móvil:"),
        correo=valor("e-mail:"),
        representante_nombre=representante_nombre,
        representante_nif=representante_nif,
    )

    if not generales.nombre and not generales.nif:
        avisos.append(
            "En la hoja de datos generales no he encontrado ni el nombre ni el NIF. "
            "Se importan las parcelas igual."
        )
    if generales.hay_representante:
        avisos.append(
            "Tu cuaderno trae un representante de la explotación. El programa todavía no guarda "
            "esos datos: apúntalos a mano si los necesitas."
        )
    return generales, avisos


def _leer_anio(celdas: list[tuple[int, int, str]]) -> int | None:
    """El año de la campaña, de la casilla «AÑO» del cuaderno.

    Es la casilla que el Cuecyl pone arriba de cada hoja de registro. Se acepta cualquier valor
    de cuatro cifras que esté entre 2000 y 2100: si no, es que no hay año que leer.
    """
    for fila, columna, texto in celdas:
        if _sin_acentos(texto) != "ano":
            continue
        candidatos = sorted(
            (c, t) for f, c, t in celdas if f == fila and c > columna
        )
        if not candidatos:
            continue
        numero = _entero(candidatos[0][1])
        if numero is not None and 2000 <= numero <= 2100:
            return numero
    return None


def _lee_municipio(texto: str) -> tuple[int | None, str]:
    """«70-CALVARRASA DE ARRIBA» son el código y el nombre del pueblo.

    El cuaderno los escribe juntos, con un guion en medio. Si algún día viniera sin código, se
    devuelve el nombre tal cual y el código vacío: lo que no se hace es inventarse el código.
    """
    limpio = _texto(texto)
    encontrado = re.match(r"^(\d{1,5})\s*-\s*(.+)$", limpio)
    if encontrado:
        return int(encontrado.group(1)), encontrado.group(2).strip()
    return None, limpio


def _lee_especie_y_variedad(texto: str) -> tuple[str, str]:
    """«VEZA VELLOSA.VILLANA» es la especie y, detrás del punto, la variedad.

    Es la convención del cuaderno oficial: en una sola casilla («Especie/ Variedad») pone las dos
    cosas separadas por un punto. Se parte por el **primer** punto porque la variedad puede
    llevar puntos detrás, y si no hay punto es que solo hay especie.
    """
    limpio = _texto(texto)
    if "." in limpio:
        especie, variedad = limpio.split(".", 1)
        return especie.strip(), variedad.strip()
    return limpio, ""


def _lee_sistema(texto: str) -> str:
    """«S» es secano y «R» es regadío. En blanco se queda en blanco.

    Ojo: **no** se pone «secano» por defecto aquí. Quien dé de alta la parcela decidirá qué hacer
    con una línea que no lo dice, y lo hará sabiendo cuántas son (el resumen las cuenta).
    """
    limpio = _sin_acentos(_texto(texto))
    if limpio.startswith("s"):
        return "secano"
    if limpio.startswith("r"):
        return "regadio"
    return ""


def _leer_parcelas(hoja, avisos: list[str]) -> tuple[list[LineaDeParcela], list[int]]:
    """La hoja 2.1: las líneas de parcela, con su cultivo y su superficie.

    Devuelve las líneas buenas **y los números de orden de las que no se han podido usar**, para
    que quien lo llame pueda decir cuántas traía el papel y cuántas se han leído.
    """
    celdas = _celdas(hoja)

    # Dónde está la cabecera. Se busca la celda «Nº DE ORDEN», que es la primera de la tabla.
    fila_cabecera = next(
        (
            fila
            for fila, _columna, texto in celdas
            if _sin_acentos(texto).startswith(_sin_acentos(TEXTO_CABECERA_DE_ORDEN))
        ),
        None,
    )
    if fila_cabecera is None:
        raise CuadernoIlegible(
            "En la hoja de parcelas no encuentro la tabla de parcelas. ¿Es el cuaderno que "
            "descargas de la Junta?"
        )

    filas_cabecera = (fila_cabecera, fila_cabecera + 1)
    columnas = {
        campo: _columna_de_la_cabecera(celdas, etiqueta, filas=filas_cabecera)
        for campo, etiqueta in CABECERAS_DE_PARCELA.items()
    }
    faltan = [campo for campo, columna in columnas.items() if columna is None]
    if columnas["orden"] is None or columnas["poligono"] is None or columnas["parcela"] is None:
        raise CuadernoIlegible(
            "La tabla de parcelas del cuaderno no tiene las columnas que hacen falta para "
            "identificar la tierra (el número de orden, el polígono y la parcela)."
        )
    if faltan:
        avisos.append(
            "Estas columnas del cuaderno no las he encontrado y se quedan sin leer: "
            + ", ".join(sorted(faltan))
            + "."
        )

    def valor(celdas_de_la_fila: dict[int, object], campo: str):
        columna = columnas.get(campo)
        return celdas_de_la_fila.get(columna) if columna is not None else None

    lineas: list[LineaDeParcela] = []
    sin_referencia: list[int] = []
    empezada = False
    for fila in hoja.iter_rows(min_row=fila_cabecera + 1):
        de_la_fila = {celda.column: celda.value for celda in fila}
        orden = _entero(valor(de_la_fila, "orden"))
        if orden is None:
            # La cabecera del cuaderno ocupa dos renglones, así que la primera fila después de
            # la cabecera todavía no es un dato. Las filas vacías de arriba se saltan.
            if not empezada:
                continue
            # Y en cuanto hay una fila con número y luego una sin él, la tabla se ha acabado:
            # debajo van las notas al pie («El titular podrá añadir nuevas parcelas…»).
            break
        empezada = True

        provincia = _entero(valor(de_la_fila, "provincia")) or 0
        municipio_codigo, municipio_nombre = _lee_municipio(_texto(valor(de_la_fila, "municipio")))
        agregado = _entero(valor(de_la_fila, "agregado")) or 0
        zona = _entero(valor(de_la_fila, "zona")) or 0
        poligono = _entero(valor(de_la_fila, "poligono"))
        parcela = _entero(valor(de_la_fila, "parcela"))
        recinto = _entero(valor(de_la_fila, "recinto"))
        if None in (poligono, parcela, recinto):
            sin_referencia.append(orden)
            continue

        especie, variedad = _lee_especie_y_variedad(_texto(valor(de_la_fila, "especie")))
        lineas.append(
            LineaDeParcela(
                orden=orden,
                referencia=sigpac.Referencia(
                    provincia=provincia,
                    municipio=municipio_codigo or 0,
                    agregado=agregado,
                    zona=zona,
                    poligono=int(poligono),
                    parcela=int(parcela),
                    recinto=int(recinto),
                ),
                municipio_codigo=municipio_codigo,
                municipio_nombre=municipio_nombre,
                uso_sigpac=_texto(valor(de_la_fila, "uso")),
                superficie_sigpac_ha=_numero(valor(de_la_fila, "superficie_sigpac")),
                superficie_cultivada_ha=_numero(valor(de_la_fila, "superficie_cultivada")),
                especie=especie,
                variedad=variedad,
                ecorregimen=_texto(valor(de_la_fila, "ecorregimen")),
                sistema=_lee_sistema(_texto(valor(de_la_fila, "sistema"))),
                principal_secundario=_texto(valor(de_la_fila, "principal")),
                fecha_inicio=_fecha(valor(de_la_fila, "fecha_inicio")),
                fecha_fin=_fecha(valor(de_la_fila, "fecha_fin")),
                aire_libre_protegido=_texto(valor(de_la_fila, "aire_libre")),
                zona_nitratos=_si_no(valor(de_la_fila, "zona_nitratos")),
            )
        )

    if sin_referencia:
        avisos.append(
            "Estas líneas del cuaderno no dicen el polígono, la parcela o el recinto, así que no "
            "se pueden dar de alta: "
            + ", ".join(str(orden) for orden in sin_referencia)
            + "."
        )
    if not lineas:
        avisos.append(
            "El cuaderno no trae ninguna línea de parcela. Mira si has descargado el cuaderno "
            "de la campaña que quieres, o si le falta actualizar las parcelas en el Reacyl."
        )
    return lineas, sin_referencia


def leer_cuaderno(contenido: bytes) -> CuadernoLeido:
    """Lee el cuaderno del Cuecyl y devuelve lo que trae. **No escribe nada.**

    Es la única puerta de entrada: la pantalla la usa para enseñar el resumen antes de importar,
    y la importación la usa después para dar de alta. Así lo que se enseña y lo que se guarda
    salen siempre de la misma lectura.
    """
    if not contenido:
        raise CuadernoIlegible("No has subido ningún fichero.")

    libro = _abrir(contenido)
    try:
        hoja_general = _hoja(libro, HOJA_GENERAL)
        hoja_parcelas = _hoja(libro, HOJA_PARCELAS)
        if hoja_parcelas is None:
            raise CuadernoIlegible(
                "Este fichero no parece el cuaderno de la Junta: no tiene la hoja de parcelas "
                f"«{HOJA_PARCELAS}». Sube el cuaderno que descargas del Cuecyl "
                f"({NOMBRE_DEL_FICHERO})."
            )

        avisos: list[str] = []
        generales = DatosGenerales()
        if hoja_general is None:
            avisos.append(
                "No tiene la hoja de datos generales, así que no se importan tus datos de "
                "titular. Las parcelas se importan igual."
            )
        else:
            generales, avisos = _leer_generales(hoja_general)

        celdas_parcelas = _celdas(hoja_parcelas)
        anio = _leer_anio(celdas_parcelas)
        parcelas, ilegibles = _leer_parcelas(hoja_parcelas, avisos)

        if anio is None:
            avisos.append(
                "El cuaderno no dice de qué año es. Se importan las parcelas igual, pero mira "
                "que sea el cuaderno de la campaña que quieres."
            )

        return CuadernoLeido(
            anio=anio,
            generales=generales,
            parcelas=parcelas,
            hojas=list(libro.sheetnames),
            avisos=avisos,
            lineas_ilegibles=ilegibles,
        )
    finally:
        libro.close()
