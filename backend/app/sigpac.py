"""El conector con el SIGPAC: traer los datos de una parcela sin teclearlos.

El SIGPAC es el catastro del campo: el registro oficial de los recintos. Hasta ahora el
agricultor tenía que escribir a mano la provincia, el municipio, el polígono, la parcela, el
recinto, la superficie, la pendiente, el uso y el dibujo del trozo. Eso son cuarenta parcelas
por ocho datos, y es justo el momento en el que la gente abandona una aplicación nueva.

**De dónde sale todo esto, y por qué no está inventado.** Los servicios son públicos, no piden
autenticación, y están documentados en el documento del FEGA «Publicación de nuevos servicios
SIGPAC de consulta y divulgación de datos del SIGC» (`06_FEGA_servicios_SIGPAC_nube.pdf`):

    Consultas de un recinto:  https://sigpac-hubcloud.es/servicioconsultassigpac/query/...
    Listas de códigos:        https://sigpac-hubcloud.es/codigossigpac/...
    OGC API Features:         https://sigpac-hubcloud.es/ogcapi

El ejemplo que da el propio documento es:

    https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfo/6/60/0/0/41/126/1.json

y los parámetros, en ese orden, son **provincia, municipio, agregado, zona, polígono, parcela y
recinto**. Ese orden no está deducido: el documento lo escribe así.

**Lo que devuelve el servicio es exactamente lo que guarda `Parcela`**: los siete códigos, la
superficie en hectáreas, la pendiente media, el uso SIGPAC, la altitud, **el coeficiente de
regadío, la región de la PAC y el coeficiente de subvencionabilidad en pastos (el CSP, que la
consulta llama `admisibilidad`)** y **el dibujo del trozo en WKT**, que es el mismo formato que
usa nuestra columna `geometria`. Se puede ver una respuesta de verdad en
`data/sigpac/recinto_de_ejemplo.json`, bajada con `backend/scripts/bajar_sigpac.py`.

Dos decisiones que conviene no deshacer:

1. **Los datos de códigos se guardan en `data/sigpac/`, no se piden en cada arranque.** Los
   recintos cambian cada campaña y los códigos casi nunca; y si el servicio del FEGA se cae un
   domingo, el agricultor tiene que poder seguir apuntando. La aplicación funciona sin
   internet; lo único que pide a la red es traer una parcela nueva.
2. **Si el SIGPAC no contesta, no se inventa nada.** Se dice que no se ha podido y se deja
   meter los datos a mano, que es como se hacía antes. Un conector que rellena la superficie
   con lo que le parece sería peor que no tenerlo.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import textos

# --------------------------------------------------------------------------
# Las direcciones, tal y como las documenta el FEGA
# --------------------------------------------------------------------------

BASE_CONSULTAS = "https://sigpac-hubcloud.es/servicioconsultassigpac"
BASE_CODIGOS = "https://sigpac-hubcloud.es/codigossigpac"
BASE_OGC = "https://sigpac-hubcloud.es/ogcapi"

# La carpeta con los datos oficiales descargados. Está en el repositorio a propósito: son
# datos públicos (Creative Commons BY 4.0) y los tests no pueden depender de que haya internet.
RUTA_DATOS = Path(__file__).resolve().parents[2] / "data" / "sigpac"

# Cuánto se espera al SIGPAC. Diez segundos: si el servicio no contesta en ese tiempo, lo que
# hace falta saber es que no contesta.
ESPERA_SEGUNDOS = 10.0

# Las imágenes se esperan menos: una foto que tarda veinte segundos ya no sirve para nada, y el
# agricultor está mirando una pantalla parada. Con seis segundos, o llega o se dice que no.
ESPERA_IMAGEN_SEGUNDOS = 6.0

# Cuántas imágenes se guardan en memoria. Veinte cubre de sobra lo que se ve mientras se mueve el
# mapa, y no crece sin fin.
TAMANO_DE_LA_CACHE_DE_IMAGENES = 20
_CACHE_DE_IMAGENES: dict[str, tuple[bytes, str]] = {}


# --------------------------------------------------------------------------
# La referencia SIGPAC
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Referencia:
    """La referencia de un recinto: los siete números que lo identifican sin lugar a dudas.

    Se lee como se escribe en el campo («37-22-0-0-501-427-1») y también con guiones, espacios
    o puntos, porque cada uno lo copia de donde puede: del papel del SIGPAC, del visor o de un
    correo del técnico.
    """

    provincia: int
    municipio: int
    agregado: int
    zona: int
    poligono: int
    parcela: int
    recinto: int

    def como_texto(self) -> str:
        return (
            f"{self.provincia}-{self.municipio}-{self.agregado}-{self.zona}"
            f"-{self.poligono}-{self.parcela}-{self.recinto}"
        )

    def como_consulta(self) -> str:
        """Los siete números en el orden que pide el servicio, separados por barras."""
        return (
            f"{self.provincia}/{self.municipio}/{self.agregado}/{self.zona}"
            f"/{self.poligono}/{self.parcela}/{self.recinto}"
        )


class ReferenciaInvalida(ValueError):
    """La referencia no tiene la forma que tiene una referencia SIGPAC."""


def lee_referencia(texto: str) -> Referencia:
    """Convierte lo que escribe el agricultor en una referencia.

    Falla si no tiene los siete números, y lo dice: es mejor que un mensaje que no explica qué
    falta. Se aceptan guiones, espacios, puntos y barras como separadores.
    """
    if not texto or not str(texto).strip():
        raise ReferenciaInvalida("No has escrito la referencia.")
    numeros = re.findall(r"\d+", str(texto))
    if len(numeros) != 7:
        raise ReferenciaInvalida(
            "Una referencia SIGPAC son siete números: provincia, municipio, agregado, zona, "
            f"polígono, parcela y recinto. Aquí hay {len(numeros)}."
        )
    return Referencia(*(int(numero) for numero in numeros))


# --------------------------------------------------------------------------
# La referencia catastral y la búsqueda a medias
# --------------------------------------------------------------------------
#
# **Por qué hay dos formas más de escribir esto.** Los siete números de la referencia SIGPAC
# son los que usa la administración, pero el agricultor casi nunca los tiene a mano escritos
# así. Lo que ve en su pantalla es una de estas dos cosas:
#
#   1. El **visor del SIGPAC**, que pone los seis primeros separados por dos puntos y el
#      recinto aparte, en otra columna: `37:70:0:0:503:51` (y recinto 1). Seis números, no
#      siete.
#   2. La **Sede del Catastro**, que da la **referencia catastral** de 20 caracteres, por
#      ejemplo `37070A50300051000AQ`.
#
# La referencia catastral de una finca rústica lleva dentro los cuatro datos que hacen falta
# para buscar el recinto. Eso **no se supone**: está comprobado con las dos referencias
# catastrales que el agricultor tiene en su papel, cotejadas contra la consulta del visor del
# SIGPAC de la misma parcela, y con el listado municipal del INE que usa el programa (ver
# `backend/tests/test_parcelas_por_codigos.py`). El reparto de cifras es este:
#
#       37   070   A   503   00051   0000   AQ
#       │    │     │   │     │       │      └─ dos dígitos de control
#       │    │     │   │     │       └──────── cuatro de control
#       │    │     │   │     └──────────────── parcela (cinco cifras)
#       │    │     │   └────────────────────── polígono (tres cifras)
#       │    │     └────────────────────────── sector (una letra)
#       │    └──────────────────────────────── municipio (tres cifras: el mismo del visor)
#       └───────────────────────────────────── provincia (dos cifras)
#
# Las dos referencias comprobadas son de la misma parcela que sale en el visor, y el municipio
# (070) y la provincia (37) están además en el listado oficial del INE, que es el que usa el
# programa para elegir el pueblo. Si la referencia no encaja con esa forma, **no se adivina**:
# se dice que no se ha podido leer.

# Provincia y municipio de la referencia catastral, que son el código municipal del INE.
#
# **Lo que se lee y lo que no.** De la referencia catastral solo se usan las **14 primeras
# cifras** (provincia, municipio, sector, polígono y parcela), que es lo que hace falta para
# buscar el recinto. Lo que va detrás son cuatro cifras de control y dos de verificación, y
# esas **no se usan para nada**: no se comprueban ni se exigen. Por eso la cola se admite con
# cuatro, cinco o seis caracteres: cuando el agricultor copia la referencia de una pantalla
# puede perder un carácter de la cola sin que eso cambie dónde está su parcela, y negarle la
# búsqueda por eso sería negársela por un dato que no se usa.
PATRON_CATASTRAL = re.compile(
    r"^\s*(?P<provincia>\d{2})(?P<municipio>\d{3})(?P<sector>[A-Za-z])"
    r"(?P<poligono>\d{3})(?P<parcela>\d{5})(?P<control>[A-Za-z0-9]{4,6})\s*$"
)


@dataclass(frozen=True)
class ReferenciaCatastral:
    """La referencia catastral de una finca rústica, con lo que lleva dentro.

    El sector y la parte de control se guardan porque forman parte de la referencia, pero no
    se usan para buscar el recinto: en el SIGPAC el recinto no está en la referencia catastral
    (una parcela catastral puede tener varios recintos).
    """

    provincia: int
    municipio: int
    sector: str
    poligono: int
    parcela: int
    control: str

    def como_texto(self) -> str:
        return (
            f"{self.provincia:02d}{self.municipio:03d}{self.sector.upper()}"
            f"{self.poligono:03d}{self.parcela:05d}{self.control.upper()}"
        )


def lee_referencia_catastral(texto: str) -> ReferenciaCatastral | None:
    """Lee una referencia catastral de finca rústica. `None` si no tiene esa forma.

    Devuelve `None` en vez de fallar porque esto se llama con lo que el agricultor ha escrito
    en una casilla que admite varias formas: quien decide qué hacer con un «no» es quien llama.
    """
    encontrado = PATRON_CATASTRAL.match(str(texto or ""))
    if not encontrado:
        return None
    return ReferenciaCatastral(
        provincia=int(encontrado.group("provincia")),
        municipio=int(encontrado.group("municipio")),
        sector=encontrado.group("sector").upper(),
        poligono=int(encontrado.group("poligono")),
        parcela=int(encontrado.group("parcela")),
        control=encontrado.group("control").upper(),
    )


@dataclass(frozen=True)
class Busqueda:
    """Lo que hace falta para **buscar** los recintos de una parcela.

    Es lo que piden las aplicaciones oficiales del FEGA para añadir recintos del SIGPAC
    (SgaRex, SgaCap): provincia, municipio, agregado, zona, polígono y parcela, con el
    agregado y la zona opcionales. El **recinto no se busca**: se elige de la lista que
    devuelve el SIGPAC, que es lo que hace el agricultor en esas aplicaciones («se marcan las
    casillas de los recintos y se incorporan»).

    `agregado` y `zona` se quedan en `None` cuando el agricultor no los ha dicho, y eso es
    distinto de 0: si no se dicen, no se filtran en la búsqueda; al construir la referencia
    completa sí van como 0, que es como los escribe el SIGPAC cuando no hay agregado ni zona.
    """

    provincia: int
    municipio: int
    poligono: int
    parcela: int
    agregado: int | None = None
    zona: int | None = None
    recinto: int | None = None
    referencia_catastral: str | None = None

    @property
    def es_completa(self) -> bool:
        """¿Se puede pedir ya el recinto concreto al SIGPAC? Hace falta el número de recinto."""
        return self.recinto is not None

    def con_recinto(self, recinto: int) -> Referencia:
        """La referencia de siete números, para pedirle los datos de un recinto al SIGPAC."""
        return Referencia(
            provincia=self.provincia,
            municipio=self.municipio,
            agregado=self.agregado or 0,
            zona=self.zona or 0,
            poligono=self.poligono,
            parcela=self.parcela,
            recinto=recinto,
        )

    def como_texto(self) -> str:
        """Cómo se escribe una parcela en el visor del SIGPAC: `37:70:0:0:503:51`."""
        return (
            f"{self.provincia}:{self.municipio}:{self.agregado or 0}:{self.zona or 0}"
            f":{self.poligono}:{self.parcela}"
        )


def lee_busqueda(texto: str) -> Busqueda:
    """Lee lo que el agricultor haya copiado, en cualquiera de las tres formas que existen.

    Se acepta, por este orden:

    1. **La referencia catastral** de 20 caracteres (`37070A50300051000AQ`), que es lo que da
       la Sede del Catastro.
    2. **Los seis números del visor del SIGPAC** (`37:70:0:0:503:51`): provincia, municipio,
       agregado, zona, polígono y parcela. Sin recinto, porque en el visor el recinto va en
       otra columna: se busca y se elige de la lista.
    3. **Los siete números** de siempre (`37-70-0-0-503-51-1`), con su recinto.

    Falla si no es ninguna de las tres, y el mensaje dice las tres, porque quien lo lee
    necesita saber qué puede escribir.
    """
    crudo = str(texto or "").strip()
    if not crudo:
        raise ReferenciaInvalida(textos.SIGPAC["referencia_vacia"])

    catastral = lee_referencia_catastral(crudo)
    if catastral is not None:
        return Busqueda(
            provincia=catastral.provincia,
            municipio=catastral.municipio,
            poligono=catastral.poligono,
            parcela=catastral.parcela,
            referencia_catastral=catastral.como_texto(),
        )

    numeros = re.findall(r"\d+", crudo)
    if len(numeros) == 7:
        referencia = Referencia(*(int(numero) for numero in numeros))
        return Busqueda(
            provincia=referencia.provincia,
            municipio=referencia.municipio,
            agregado=referencia.agregado,
            zona=referencia.zona,
            poligono=referencia.poligono,
            parcela=referencia.parcela,
            recinto=referencia.recinto,
        )
    if len(numeros) == 6:
        # **El orden del visor no es el de la referencia.** En el visor del SIGPAC la parcela
        # se lee `37:70:0:0:503:51`: provincia, municipio, agregado, zona, polígono y parcela.
        # El recinto no va ahí (va en su propia columna de la tabla), así que se busca después.
        provincia, municipio, agregado, zona, poligono, parcela = (int(n) for n in numeros)
        return Busqueda(
            provincia=provincia,
            municipio=municipio,
            agregado=agregado,
            zona=zona,
            poligono=poligono,
            parcela=parcela,
        )
    raise ReferenciaInvalida(textos.SIGPAC["referencia_no_entendida"].format(cuantos=len(numeros)))


def url_recinto(referencia: Referencia, base: str | None = None) -> str:
    """La dirección de la consulta de las propiedades de un recinto."""
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_BASE") or BASE_CONSULTAS).rstrip("/")
    return f"{base}/query/recinfo/{referencia.como_consulta()}.json"


def url_codigos(nombre: str, base: str | None = None) -> str:
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_CODIGOS_BASE") or BASE_CODIGOS).rstrip("/")
    return f"{base}/{nombre}.json"


def url_recintos(busqueda: Busqueda, base: str | None = None, limite: int = 50) -> str:
    """La dirección que devuelve **todos los recintos de una parcela**.

    Es la otra mitad del SIGPAC: la consulta de un recinto pide los siete números, y el
    agricultor casi nunca sabe el recinto. La API de descarga (OGC API Features) sí sabe
    buscar por provincia, municipio, agregado, zona, polígono y parcela —los mismos campos
    que piden las aplicaciones oficiales del FEGA para «Añadir recintos de SigPac»— y
    devuelve la lista, que es lo que hay que enseñarle para que marque los suyos.

    Se comprobó contra el servicio de verdad el 24/09/2026: la parcela 37/70/503/51 devuelve
    un recinto con pendiente 1 y altitud 837, que es lo mismo que enseñaba el visor del
    agricultor. La respuesta de verdad está guardada en
    `data/sigpac/recintos_de_ejemplo.json`.
    """
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_OGC_BASE") or BASE_OGC).rstrip("/")
    parametros = [
        ("provincia", busqueda.provincia),
        ("municipio", busqueda.municipio),
        ("poligono", busqueda.poligono),
        ("parcela", busqueda.parcela),
        ("limit", limite),
        ("f", "json"),
    ]
    # El agregado y la zona solo se filtran si el agricultor los ha dicho: la mayoría de las
    # parcelas no tienen (van en 0) y filtrar por un 0 supuesto dejaría fuera las que sí tienen.
    if busqueda.agregado is not None:
        parametros.append(("agregado", busqueda.agregado))
    if busqueda.zona is not None:
        parametros.append(("zona", busqueda.zona))
    consulta = "&".join(f"{clave}={valor}" for clave, valor in parametros)
    return f"{base}/collections/recintos/items?{consulta}"


# --------------------------------------------------------------------------
# Las otras consultas del servicio oficial
#
# **Once consultas, y las once tienen su dirección documentada** en el catálogo del FEGA
# (`https://sigpac-hubcloud.es/html/csp/descServicio.html`), cada una con su página de ejemplo.
# Aquí están las que hacen falta para el mapa y para rellenar la ficha de una parcela:
#
#   query/recinfobypoint/[srid]/[x]/[y]        propiedades del recinto que CONTIENE un punto
#   query/refrecinbycoord/[srid]/[x]/[y]       referencia del recinto que contiene un punto
#   query/refcatparcela/[pr]/[mu]/[ag]/[zo]/[po]/[pa]
#                                              referencia catastral de una parcela
#   query/recinfoparc/[pr]/[mu]/[ag]/[zo]/[po]/[pa]
#                                              propiedades de TODOS los recintos de una parcela
#   intersection/<capa>/[pr]/[mu]/[ag]/[zo]/[po]/[pa]/[re]
#                                              cuánto del recinto cae en una capa oficial
#
# Las dos de coordenadas son las que permiten **elegir la parcela tocando el mapa**: se manda el
# punto donde ha tocado el agricultor y el SIGPAC dice qué recinto lo contiene. Comprobado el
# 24/09/2026 con las coordenadas de su parcela: devuelve sus propiedades y su referencia.
# --------------------------------------------------------------------------

# Las cinco capas contra las que el SIGPAC sabe cruzar un recinto. Los nombres son los de la
# dirección (en `pastos` está la capa de pastos permanentes, que en la web se llama así).
CAPAS_DE_INTERSECCION = ("nitratos", "red_natura", "montanera", "fitosanitarios", "pastos")

# El sistema de referencia con el que se piden las coordenadas. 4326 es el de las coordenadas del
# mapa y del móvil (grados), y es el que usa el navegador: mandar otra cosa obligaría a convertir
# y una conversión mal hecha pondría al agricultor en otra parcela.
SRID_POR_DEFECTO = 4326


def url_recinto_por_punto(x: float, y: float, srid: int = SRID_POR_DEFECTO, base: str | None = None) -> str:
    """Las propiedades del recinto que contiene un punto. Es «tocar el mapa»."""
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_BASE") or BASE_CONSULTAS).rstrip("/")
    return f"{base}/query/recinfobypoint/{srid}/{x}/{y}.json"


def url_referencia_por_punto(x: float, y: float, srid: int = SRID_POR_DEFECTO, base: str | None = None) -> str:
    """La referencia del recinto que contiene un punto, sin sus propiedades (más ligera)."""
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_BASE") or BASE_CONSULTAS).rstrip("/")
    return f"{base}/query/refrecinbycoord/{srid}/{x}/{y}.json"


def url_referencia_catastral(busqueda: Busqueda, base: str | None = None) -> str:
    """La referencia catastral de una parcela, a partir de sus códigos del SIGPAC.

    Es un dato que el agricultor casi nunca tiene a mano y que el contenido mínimo del CUE pide
    por su nombre (`ReferenciaCatastral`). Hasta ahora solo se guardaba si él la pegaba; con esta
    consulta la pone el SIGPAC, que es quien manda.
    """
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_BASE") or BASE_CONSULTAS).rstrip("/")
    return (
        f"{base}/query/refcatparcela/{busqueda.provincia}/{busqueda.municipio}"
        f"/{busqueda.agregado or 0}/{busqueda.zona or 0}/{busqueda.poligono}/{busqueda.parcela}.json"
    )


def url_recintos_de_la_parcela(busqueda: Busqueda, base: str | None = None) -> str:
    """Todos los recintos de una parcela, con sus propiedades (la consulta oficial)."""
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_BASE") or BASE_CONSULTAS).rstrip("/")
    return (
        f"{base}/query/recinfoparc/{busqueda.provincia}/{busqueda.municipio}"
        f"/{busqueda.agregado or 0}/{busqueda.zona or 0}/{busqueda.poligono}/{busqueda.parcela}.json"
    )


def url_interseccion(capa: str, referencia: Referencia, base: str | None = None) -> str:
    """Cuánto de un recinto cae dentro de una capa oficial (nitratos, Red Natura…)."""
    if capa not in CAPAS_DE_INTERSECCION:
        raise ValueError(f"Esa capa no existe en el SIGPAC: {capa!r}")
    base = (base or os.environ.get("CUEDIGITAL_SIGPAC_BASE") or BASE_CONSULTAS).rstrip("/")
    return f"{base}/intersection/{capa}/{referencia.como_consulta()}.json"


# --------------------------------------------------------------------------
# Las imágenes del mapa
#
# Los dos servicios que dan las imágenes son WMS 1.3.0, y los dos están comprobados:
#
#   La foto del campo     https://www.ign.es/wms-inspire/pnoa-ma     (OI.OrthoimageCoverage)
#   Los linderos          https://sigpac-hubcloud.es/wms             (recinto)
#   Lo que se declaró     el mismo, capa cultivo_declarado
#
# **Ojo con el orden de la caja en WMS 1.3.0**: con `EPSG:4326` la caja se escribe
# `sur,oeste,norte,este` (latitud primero), al revés que en las versiones anteriores. Equivocar
# ese orden no da un error: da **otra zona del país**, y el agricultor vería un mapa que no es
# el suyo. Por eso hay un test que lo comprueba con números.
#
# Las imágenes **no las pide el navegador**: las pide el programa y las sirve él. Así las
# direcciones oficiales están en un solo sitio (aquí), el navegador no necesita saber nada del
# SIGPAC, y si el servicio no contesta se puede decir en castellano en vez de dejar una imagen
# rota.
# --------------------------------------------------------------------------

CAPAS_DEL_MAPA = {
    # La foto aérea del IGN (PNOA), que es lo que el agricultor reconoce de un vistazo.
    "foto": ("https://www.ign.es/wms-inspire/pnoa-ma", "OI.OrthoimageCoverage", "image/jpeg"),
    # Los linderos de los recintos del SIGPAC, encima de la foto.
    "linderos": ("https://sigpac-hubcloud.es/wms", "recinto", "image/png"),
    # Lo que se declaró como cultivo en la campaña anterior: ayuda a reconocer la tierra.
    "cultivo": ("https://sigpac-hubcloud.es/wms", "cultivo_declarado", "image/png"),
}


def url_imagen_del_mapa(
    capa: str, oeste: float, sur: float, este: float, norte: float, ancho: int, alto: int
) -> str:
    """La dirección de una imagen del mapa (una capa, una caja, un tamaño).

    El tamaño se pide en píxeles y se le pone un tope: una imagen enorme tarda y gasta datos del
    agricultor sin darle nada mejor en la pantalla de un móvil.
    """
    if capa not in CAPAS_DEL_MAPA:
        raise ValueError(f"Esa capa de mapa no existe: {capa!r}")
    base, nombre_de_la_capa, formato = CAPAS_DEL_MAPA[capa]
    ancho = max(64, min(int(ancho), 1600))
    alto = max(64, min(int(alto), 1600))
    parametros = [
        ("service", "WMS"),
        ("version", "1.3.0"),
        ("request", "GetMap"),
        ("layers", nombre_de_la_capa),
        ("styles", ""),
        ("crs", "EPSG:4326"),
        # Latitud primero: es la norma de WMS 1.3.0 con EPSG:4326.
        ("bbox", f"{sur},{oeste},{norte},{este}"),
        ("width", ancho),
        ("height", alto),
        ("format", formato),
    ]
    if capa != "foto":
        # Las capas del SIGPAC se piden transparentes para poder ponerlas encima de la foto.
        parametros.append(("transparent", "true"))
    consulta = "&".join(f"{clave}={valor}" for clave, valor in parametros)
    return f"{base}?{consulta}"


# --------------------------------------------------------------------------
# La respuesta del SIGPAC
# --------------------------------------------------------------------------


@dataclass
class Recinto:
    """Las propiedades de un recinto, tal y como las devuelve el SIGPAC.

    Los nombres de los campos son **los que devuelve el servicio**, no los nuestros: así se
    puede comparar esta clase con una respuesta de verdad sin traducir nada por medio. Hay un
    fichero con una respuesta real en `data/sigpac/recinto_de_ejemplo.json`.
    """

    provincia: int | None = None
    municipio: int | None = None
    agregado: int | None = None
    zona: int | None = None
    poligono: int | None = None
    parcela: int | None = None
    recinto: int | None = None
    superficie: float | None = None
    pendiente_media: float | None = None
    coef_regadio: float | None = None
    uso_sigpac: str | None = None
    region: int | None = None
    altitud: int | None = None
    srid: int | None = None
    wkt: str | None = None
    incidencias: object = None
    # **El CSP: «coeficiente de subvencionabilidad en pastos»** (0–100), que en la consulta REST
    # se llama `admisibilidad`. Es `float | None` porque el servicio devuelve `null` cuando ese
    # recinto no es pasto o no consta —el ejemplo real de `data/sigpac/recinto_de_ejemplo.json`
    # trae `"admisibilidad": null`—, y ese nulo **no es un cero**: un 0 afirmaría que ese pasto no
    # se puede cobrar. Estuvo tipado como `object`, sin convertir y sin documentar, y así el texto
    # que mandara el servicio se colaba tal cual hasta la parcela.
    # Los nombres y el significado están verificados en `docs/INVESTIGACION-AGRICOLA.md` §1.3.
    admisibilidad: float | None = None
    crudo: dict = field(default_factory=dict)

    @property
    def referencia(self) -> Referencia | None:
        numeros = (
            self.provincia,
            self.municipio,
            self.agregado,
            self.zona,
            self.poligono,
            self.parcela,
            self.recinto,
        )
        if any(numero is None for numero in numeros):
            return None
        return Referencia(*(int(numero) for numero in numeros))

    @property
    def ref_sigpac(self) -> str:
        """La referencia como la guardamos en la parcela. Cadena vacía si falta algo."""
        referencia = self.referencia
        return referencia.como_texto() if referencia else ""


def lee_recinto(cuerpo) -> Recinto | None:
    """Interpreta lo que devuelve la consulta de un recinto.

    Decisión: **no se lanza una excepción por una respuesta rara.** Si el SIGPAC contesta algo
    que no se entiende, se devuelve `None` y quien llama dice que no se ha podido traer, en vez
    de reventar delante del agricultor. Y si el recinto no existe, el servicio devuelve una
    lista vacía: eso **no es un error de la aplicación**, es que esa referencia no es de nadie.
    """
    if isinstance(cuerpo, str):
        try:
            cuerpo = json.loads(cuerpo)
        except (TypeError, ValueError):
            return None

    if isinstance(cuerpo, list):
        if not cuerpo:
            return None
        cuerpo = cuerpo[0]
    if not isinstance(cuerpo, dict):
        return None

    def numero(clave):
        valor = cuerpo.get(clave)
        try:
            return float(valor) if valor is not None else None
        except (TypeError, ValueError):
            return None

    def entero(clave):
        valor = numero(clave)
        return int(valor) if valor is not None else None

    return Recinto(
        provincia=entero("provincia"),
        municipio=entero("municipio"),
        agregado=entero("agregado"),
        zona=entero("zona"),
        poligono=entero("poligono"),
        parcela=entero("parcela"),
        recinto=entero("recinto"),
        superficie=numero("superficie"),
        pendiente_media=numero("pendiente_media"),
        coef_regadio=numero("coef_regadio"),
        uso_sigpac=(cuerpo.get("uso_sigpac") or None),
        region=entero("region"),
        altitud=entero("altitud"),
        srid=entero("srid"),
        wkt=(cuerpo.get("wkt") or None),
        incidencias=cuerpo.get("incidencias"),
        # El CSP se lee como número, igual que el resto. Si viene `null` o texto que no es un
        # número, se queda en `None` («no consta»): **nunca se convierte en 0**.
        admisibilidad=numero("admisibilidad"),
        crudo=cuerpo,
    )


def lee_recintos(cuerpo) -> list[Recinto]:
    """Interpreta la lista de recintos de una parcela (respuesta de la API de descarga).

    Devuelve una lista vacía si la respuesta no se entiende o si no hay ninguno: en los dos
    casos lo que tiene que pasar es lo mismo —que el agricultor vea que ahí no hay nada y
    pueda corregir los números—, y no que le salte un error técnico.

    Los datos que trae esta consulta son **el número de recinto, la pendiente y la altitud**;
    la superficie, el uso y el dibujo vienen en la consulta de cada recinto, que se pide
    después, cuando el agricultor ya ha marcado el que es suyo. Así no se piden datos de
    recintos que no le interesan a nadie.
    """
    if isinstance(cuerpo, str):
        try:
            cuerpo = json.loads(cuerpo)
        except (TypeError, ValueError):
            return []

    if not isinstance(cuerpo, dict):
        return []
    elementos = cuerpo.get("features")
    if not isinstance(elementos, list):
        return []

    salida: list[Recinto] = []
    for elemento in elementos:
        if not isinstance(elemento, dict):
            continue
        propiedades = elemento.get("properties")
        if not isinstance(propiedades, dict):
            continue

        def entero(clave):
            valor = propiedades.get(clave)
            try:
                return int(valor) if valor is not None else None
            except (TypeError, ValueError):
                return None

        def numero(clave):
            valor = propiedades.get(clave)
            try:
                return float(valor) if valor is not None else None
            except (TypeError, ValueError):
                return None

        if entero("recinto") is None:
            continue
        salida.append(
            Recinto(
                provincia=entero("provincia"),
                municipio=entero("municipio"),
                agregado=entero("agregado"),
                zona=entero("zona"),
                poligono=entero("poligono"),
                parcela=entero("parcela"),
                recinto=entero("recinto"),
                pendiente_media=numero("pendiente_media"),
                altitud=entero("altitud"),
                # El dibujo viene como geometría de la API, no como WKT. No se traduce aquí a
                # mano: la consulta del recinto ya devuelve el WKT, y esa es la que se usa.
                crudo=propiedades,
            )
        )
    return sorted(salida, key=lambda recinto: recinto.recinto or 0)


# --------------------------------------------------------------------------
# Las consultas por coordenadas y las intersecciones
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Interseccion:
    """Cuánto de un recinto cae dentro de una capa oficial (nitratos, Red Natura…).

    Los nombres de los dos números son **los que usa el servicio**, porque el significado es suyo
    y está documentado en su página de ejemplo: `surface_intersection` es la superficie de la
    intersección **en metros cuadrados** y `surface_tpc` es **el porcentaje de la superficie del
    recinto** que cae dentro de la capa. Una lista vacía significa que no hay intersección
    ninguna, y eso es un dato tan bueno como el otro: quiere decir que ese recinto **no** está en
    la zona (por ejemplo, que no está en zona vulnerable a nitratos).
    """

    referencia: Referencia
    superficie_m2: float | None = None
    porcentaje: float | None = None
    crudo: dict = field(default_factory=dict)


def lee_referencias(cuerpo) -> list[Referencia]:
    """Lee las referencias que devuelven las consultas por coordenadas.

    La respuesta es del tipo `[{"refrecinto": "37:70:0:0:503:53:1"}]`, y puede traer más de una
    cuando el punto cae justo en una linde (el servicio devuelve los recintos que lo contienen).
    Si alguna no se entiende, se descarta: es mejor devolver las que sí se entienden que
    reventar por una respuesta rara.
    """
    if isinstance(cuerpo, str):
        try:
            cuerpo = json.loads(cuerpo)
        except (TypeError, ValueError):
            return []
    if isinstance(cuerpo, dict):
        cuerpo = [cuerpo]
    if not isinstance(cuerpo, list):
        return []

    salida: list[Referencia] = []
    for elemento in cuerpo:
        if not isinstance(elemento, dict):
            continue
        crudo = elemento.get("refrecinto") or elemento.get("referencia") or ""
        try:
            salida.append(lee_referencia(str(crudo)))
        except ReferenciaInvalida:
            continue
    return salida


def lee_referencia_catastral_de_una_parcela(cuerpo) -> str | None:
    """La referencia catastral que devuelve el SIGPAC para una parcela, o `None` si no la da."""
    if isinstance(cuerpo, str):
        try:
            cuerpo = json.loads(cuerpo)
        except (TypeError, ValueError):
            return None
    if isinstance(cuerpo, dict):
        cuerpo = [cuerpo]
    if not isinstance(cuerpo, list) or not cuerpo:
        return None
    primero = cuerpo[0]
    if not isinstance(primero, dict):
        return None
    referencia = str(primero.get("referencia_cat") or "").strip()
    return referencia or None


def lee_interseccion(cuerpo) -> list[Interseccion] | None:
    """Lee la intersección de un recinto con una capa oficial.

    **Tres respuestas que no son lo mismo, y confundirlas sería afirmar algo falso:**

    * Una lista **con** elementos: el recinto está en esa capa, y se sabe cuánto de él.
    * Una lista **vacía**: el recinto **no** está en esa capa. Es un dato tan bueno como el otro.
    * Cualquier otra cosa (`None`): **no se ha entendido la respuesta**, así que no se sabe. Esto
      es lo que impide el fallo grave: si un día el servicio contesta otra cosa y se tomara por
      una lista vacía, el programa diría «tu parcela no está en zona de nitratos» sin saberlo.
    """
    if isinstance(cuerpo, str):
        try:
            cuerpo = json.loads(cuerpo)
        except (TypeError, ValueError):
            return None
    if isinstance(cuerpo, dict):
        # El servicio devuelve siempre una colección; un objeto suelto solo se admite si tiene
        # pinta de intersección (el propio ejemplo de la documentación es una lista de uno).
        if "provincia" not in cuerpo:
            return None
        cuerpo = [cuerpo]
    if not isinstance(cuerpo, list):
        return None

    salida: list[Interseccion] = []
    for elemento in cuerpo:
        if not isinstance(elemento, dict):
            return None
        # Los dos campos que solo tiene una intersección. Sin esta comprobación, la respuesta de
        # la consulta de un recinto —que también trae `provincia` y `recinto`— se colaría como si
        # fuera una intersección, y el recinto quedaría apuntado como «está en la capa» sin
        # saberlo. Lo cazó un test con la respuesta de verdad de un recinto.
        if "surface_tpc" not in elemento or "surface_intersection" not in elemento:
            return None
        if "provincia" not in elemento or "recinto" not in elemento:
            return None
        try:
            referencia = Referencia(
                provincia=int(elemento["provincia"]),
                municipio=int(elemento["municipio"]),
                agregado=int(elemento.get("agregado") or 0),
                zona=int(elemento.get("zona") or 0),
                poligono=int(elemento["poligono"]),
                parcela=int(elemento["parcela"]),
                recinto=int(elemento["recinto"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

        def numero(clave):
            valor = elemento.get(clave)
            try:
                return float(valor) if valor is not None else None
            except (TypeError, ValueError):
                return None

        salida.append(
            Interseccion(
                referencia=referencia,
                superficie_m2=numero("surface_intersection"),
                porcentaje=numero("surface_tpc"),
                crudo=elemento,
            )
        )
    return salida


def pedir_recinto_por_punto(x: float, y: float, srid: int = SRID_POR_DEFECTO) -> Recinto | None:
    """Las propiedades del recinto que contiene un punto: es lo que hace «tocar el mapa».

    `None` si en ese punto no hay ningún recinto (un camino, un pueblo, el monte): eso no es un
    fallo, es que ahí no hay tierra de nadie.
    """
    import httpx

    try:
        respuesta = httpx.get(
            url_recinto_por_punto(x, y, srid), timeout=ESPERA_SEGUNDOS, follow_redirects=True
        )
    except Exception as error:  # noqa: BLE001
        raise SigpacNoContesta(type(error).__name__) from None
    if respuesta.status_code != 200:
        raise SigpacNoContesta(f"HTTP {respuesta.status_code}")
    return lee_recinto(respuesta.text)


def pedir_referencia_catastral(busqueda: Busqueda) -> str | None:
    """La referencia catastral de una parcela según el SIGPAC. `None` si no la tiene."""
    import httpx

    try:
        respuesta = httpx.get(
            url_referencia_catastral(busqueda), timeout=ESPERA_SEGUNDOS, follow_redirects=True
        )
    except Exception as error:  # noqa: BLE001
        raise SigpacNoContesta(type(error).__name__) from None
    if respuesta.status_code != 200:
        raise SigpacNoContesta(f"HTTP {respuesta.status_code}")
    return lee_referencia_catastral_de_una_parcela(respuesta.text)


def pedir_interseccion(capa: str, referencia: Referencia) -> list[Interseccion] | None:
    """Cuánto de un recinto cae en una capa oficial.

    Lista vacía = no está en esa capa. `None` = la respuesta no se ha entendido, o sea que no se
    sabe (y entonces **no se puede decir que no está**).
    """
    import httpx

    try:
        respuesta = httpx.get(
            url_interseccion(capa, referencia), timeout=ESPERA_SEGUNDOS, follow_redirects=True
        )
    except Exception as error:  # noqa: BLE001
        raise SigpacNoContesta(type(error).__name__) from None
    if respuesta.status_code != 200:
        raise SigpacNoContesta(f"HTTP {respuesta.status_code}")
    return lee_interseccion(respuesta.text)


def zona_de_nitratos(referencia: Referencia) -> tuple[bool, float | None] | None:
    """¿Está este recinto en zona vulnerable a nitratos, según la capa oficial del SIGPAC?

    Devuelve `(en_zona, porcentaje)` o **`None` si no se ha podido saber** (el servicio no
    contesta o contesta algo que no se entiende). Es la respuesta buena y no la que se deduce del
    municipio: la lista de municipios dice que el **pueblo** está en una zona declarada, y esto
    dice si **este trozo de tierra** cae dentro. Y el porcentaje importa: hay recintos que solo
    están dentro a medias, y eso se le tiene que poder decir al agricultor en vez de darle un «sí»
    o un «no» redondos.
    """
    intersecciones = pedir_interseccion("nitratos", referencia)
    if intersecciones is None:
        return None
    if not intersecciones:
        return (False, 0.0)
    return (True, intersecciones[0].porcentaje)


def pedir_imagen_del_mapa(
    capa: str, oeste: float, sur: float, este: float, norte: float, ancho: int, alto: int
) -> tuple[bytes, str]:
    """Trae una imagen del mapa del servicio oficial. Devuelve `(bytes, tipo)`.

    Se guardan las últimas imágenes en memoria porque al mover el mapa se vuelve a pedir lo
    mismo: sin eso, ir y volver con el dedo serían cuatro viajes al IGN para ver lo mismo. La
    caché es pequeña a propósito (unas veinte imágenes): esto no es un servidor de mapas, es un
    agricultor mirando su finca.
    """
    import httpx

    url = url_imagen_del_mapa(capa, oeste, sur, este, norte, ancho, alto)
    guardada = _CACHE_DE_IMAGENES.get(url)
    if guardada is not None:
        return guardada

    try:
        respuesta = httpx.get(url, timeout=ESPERA_IMAGEN_SEGUNDOS, follow_redirects=True)
    except Exception as error:  # noqa: BLE001
        raise SigpacNoContesta(type(error).__name__) from None
    if respuesta.status_code != 200:
        raise SigpacNoContesta(f"HTTP {respuesta.status_code}")

    tipo = (respuesta.headers.get("content-type") or "").split(";")[0].strip()
    if tipo not in ("image/png", "image/jpeg", "image/jpg"):
        raise SigpacNoContesta(f"El servicio ha contestado {tipo or 'sin tipo'}")
    if not respuesta.content:
        raise SigpacNoContesta("imagen vacía")

    if len(_CACHE_DE_IMAGENES) >= TAMANO_DE_LA_CACHE_DE_IMAGENES:
        _CACHE_DE_IMAGENES.clear()
    _CACHE_DE_IMAGENES[url] = (respuesta.content, tipo)
    return (respuesta.content, tipo)


def olvidar_las_imagenes() -> None:
    """Vacía la caché de imágenes. Existe para los tests, como el de los catálogos."""
    _CACHE_DE_IMAGENES.clear()


# --------------------------------------------------------------------------
# Las listas de códigos oficiales
# --------------------------------------------------------------------------



def cargar_codigos(nombre: str, ruta: Path | str | None = None) -> dict:
    """Lee una lista de códigos oficial del SIGPAC. Devuelve `{codigo: descripcion}`.

    Devuelve un diccionario vacío si el fichero no está: los nombres de los usos y de los
    productos son un adorno, y no tenerlos no puede impedir apuntar en el cuaderno.
    """
    carpeta = Path(ruta) if ruta else RUTA_DATOS
    fichero = carpeta / f"{nombre}.json"
    if not fichero.exists():
        return {}
    try:
        datos = json.loads(fichero.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    salida: dict = {}
    for entrada in datos.get("codigos") or []:
        if not isinstance(entrada, dict):
            continue
        codigo = entrada.get("codigo")
        if codigo is None:
            continue
        salida[codigo] = entrada.get("descripcion") or ""
    return salida


def etiqueta_uso(codigo: str | None) -> str:
    """Cómo se llama un uso SIGPAC, según la lista oficial.

    Sin fichero de códigos se devuelve el código tal cual, y no una traducción inventada: «TA»
    es lo que pone el papel del agricultor, y es mejor que una palabra que nos hayamos sacado.
    """
    if not codigo:
        return ""
    return cargar_codigos("cod_uso_sigpac").get(codigo) or codigo


def productos_oficiales() -> dict:
    """El catálogo oficial de productos: `{codigo: nombre}`. Son 933, del FEGA.

    Esto es lo que el volcado oficial llama «Producto vegetal (según catálogo)»: hasta ahora
    ese campo salía vacío porque no teníamos los códigos, y los tenemos aquí.
    """
    return cargar_codigos("cod_producto")


def usos_oficiales() -> dict:
    return cargar_codigos("cod_uso_sigpac")


def aprovechamientos_oficiales() -> dict:
    return cargar_codigos("cod_aprovechamiento")


def incidencias_oficiales() -> dict:
    return cargar_codigos("cod_incidencia")


def busca_producto(texto: str, catalogo: dict | None = None) -> tuple[int | None, str | None]:
    """Busca un producto por su nombre, para poder mandar el código en vez del texto.

    Devuelve `(codigo, nombre_oficial)` o `(None, None)`. Busca por nombre exacto y, si no,
    por nombre contenido: el agricultor escribe «trigo blando» y en el catálogo pone «TRIGO
    BLANDO». Si hay varias coincidencias, se queda la primera por código, que es la más
    antigua y la más probable.
    """
    from . import servicios

    catalogo = catalogo if catalogo is not None else productos_oficiales()
    if not texto or not catalogo:
        return (None, None)
    buscado = servicios.clave_de_producto(texto)
    if not buscado:
        return (None, None)

    # 1. Nombre exacto.
    for codigo, nombre in catalogo.items():
        if servicios.clave_de_producto(nombre) == buscado:
            return (codigo, nombre)
    # 2. El nombre del catálogo contiene lo que ha escrito.
    candidatos = [
        (codigo, nombre)
        for codigo, nombre in catalogo.items()
        if buscado and buscado in servicios.clave_de_producto(nombre)
    ]
    if candidatos:
        codigo, nombre = min(candidatos, key=lambda pareja: str(pareja[0]))
        return (codigo, nombre)
    return (None, None)


def datos_disponibles() -> dict:
    """Qué datos oficiales hay cargados. Es lo que se enseña para saber qué se puede traer.

    **Sin la `ruta` de la carpeta de datos** (03/10/2026). Hasta hoy devolvía
    `"ruta": str(RUTA_DATOS)`, es decir **la ruta absoluta de una carpeta del servidor**, y esta
    función la sirve `GET /api/sigpac/estado`, que **es una ruta sin sesión** (`parcelas.py`):
    cualquiera podía preguntarle al programa dónde tiene los datos y con qué usuario corre.
    Lo apuntó la revisión de rutas sin sesión (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.13:
    «quitar `ruta` de la respuesta») y no se había hecho.

    Se puede quitar sin quitar nada útil: la ruta **no la lee nadie** —ni la pantalla, ni el
    recorrido, ni ninguna prueba—, era una comodidad de quien administra la instalación, y quien
    administra la instalación tiene la carpeta delante. Lo que sí sigue saliendo es **qué** hay
    cargado, que es lo que la pantalla necesita para decir «traer los datos del SIGPAC».
    """
    productos = productos_oficiales()
    return {
        "cargados": RUTA_DATOS.is_dir() and bool(productos),
        "productos": len(productos),
        "usos": len(usos_oficiales()),
        "aprovechamientos": len(aprovechamientos_oficiales()),
        "incidencias": len(incidencias_oficiales()),
        "como_actualizarlos": "python scripts/bajar_sigpac.py",
        "licencia": (
            "Datos del SIGPAC (FEGA), publicados bajo licencia Creative Commons BY 4.0 según "
            "el documento «Publicación de nuevos servicios SIGPAC de consulta y divulgación de "
            "datos del SIGC»."
        ),
    }


# --------------------------------------------------------------------------
# Las dos preguntas que se le hacen al SIGPAC
#
# Están juntas aquí, y no repartidas por los routers, porque son la frontera con el exterior:
# es lo único de todo el programa que necesita internet, y tenerlo en un solo sitio es lo que
# permite probarlo sustituyendo `httpx.get` por una respuesta de verdad guardada en el
# repositorio, sin salir a la red en los tests.
# --------------------------------------------------------------------------


class SigpacNoContesta(RuntimeError):
    """El SIGPAC no ha contestado: ni un recinto, ni un error suyo, ni nada.

    Se distingue de «no hay ningún recinto con esa referencia», que es una respuesta legítima y
    significa otra cosa: que el agricultor tiene que mirar los números. Confundir las dos deja al
    agricultor sin saber si el problema es su papel o su cobertura.
    """


def pedir_recinto(referencia: Referencia) -> Recinto | None:
    """Pide los datos de un recinto. `None` si el SIGPAC no tiene ningún recinto con esa referencia."""
    import httpx

    try:
        respuesta = httpx.get(
            url_recinto(referencia), timeout=ESPERA_SEGUNDOS, follow_redirects=True
        )
    except Exception as error:  # noqa: BLE001 — cualquier fallo de red es el mismo caso
        raise SigpacNoContesta(type(error).__name__) from None
    if respuesta.status_code != 200:
        # Se mira el código a mano y no con `raise_for_status` porque aquí **todo** lo que no sea
        # un 200 es lo mismo: que el servicio no ha dado el dato. Un 500 suyo y un 404 de una
        # dirección mal formada no se pueden tratar distinto desde aquí.
        raise SigpacNoContesta(f"HTTP {respuesta.status_code}")
    return lee_recinto(respuesta.text)


def pedir_recintos(busqueda: Busqueda, limite: int = 50) -> list[Recinto]:
    """Pide **todos los trozos** de una parcela. Lista vacía si esa parcela no tiene ninguno."""
    import httpx

    try:
        respuesta = httpx.get(
            url_recintos(busqueda, limite=limite), timeout=ESPERA_SEGUNDOS, follow_redirects=True
        )
    except Exception as error:  # noqa: BLE001
        raise SigpacNoContesta(type(error).__name__) from None
    if respuesta.status_code != 200:
        raise SigpacNoContesta(f"HTTP {respuesta.status_code}")
    return lee_recintos(respuesta.text)
