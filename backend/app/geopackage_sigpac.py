"""**Abrir el GeoPackage del SIGPAC sin GDAL**: los recintos y sus contornos (IMP-12, 05/11/2026).

El SIGPAC publica los recintos de cada provincia en un **GeoPackage** (`.gpkg`), que por dentro es
un SQLite con una tabla de geometrías. El programa ya baja ese fichero y lo guarda con su ficha
(`app/sigpac_cache.py`); lo que faltaba era **abrirlo**. Y se abre aquí, a mano, porque en este
proyecto no hay GDAL, ni shapely, ni fiona, ni pyogrio: **solo `sqlite3` de la biblioteca estándar**,
y eso basta para leer una tabla y traducir un blob de geometría.

## Las tres cosas que hace, y las que no

1. **Descubre** la tabla de recintos y su columna de geometría en `gpkg_geometry_columns`, y las
   columnas de atributos **por su nombre normalizado** (sin tildes y sin mayúsculas): un GeoPackage
   del SIGPAC de otra campaña puede cambiar de orden de columnas o de mayúsculas, y buscar «la
   columna 4» se rompería en silencio y devolvería el dato de al lado.
2. **Traduce la geometría**: cabecera `GP` del GeoPackage (versión, banderas, `srs_id`, envolvente
   opcional) y después el **WKB** de dentro. Se soportan `Polygon` y `MultiPolygon`, que es lo que
   publica el SIGPAC para un recinto. Cualquier otro tipo **se dice**: no se convierte en un cuadro
   ni se salta en silencio.
3. **Casa las parcelas con los recintos** por sus códigos (provincia, municipio, polígono, parcela,
   recinto) y devuelve el WKT y los anillos. **Lo que no se encuentra se dice**, y una parcela cuyo
   municipio no se puede casar con el catálogo oficial se cuenta aparte (`sin_codigos`): nunca se
   adivina un código.

## Lo que NO se hace, dicho aquí y no en un comentario

  · **No se reproyecta.** El contorno se guarda en el sistema de coordenadas del fichero, que para
    el SIGPAC es longitud/latitud (ETRS89 o WGS84, que a estos efectos es lo mismo). Si el mapa
    viniera en otro sistema, se para con un error claro en vez de guardar coordenadas que no son ni
    una cosa ni la otra.
  · **No se rellena la provincia entera en memoria.** `buscar` devuelve los recintos de **una**
    parcela (con un tope), y el recorrido de una finca va parcela a parcela. Cargar los cientos de
    miles de recintos de una provincia no cabe en un servidor modesto y no hace falta para nada.
  · **No se guarda nada en la base de datos desde aquí.** Este módulo es lectura; quien escribe la
    geometría de las parcelas es la puerta (`routers/parcelas.py`), que además es la que comprueba
    el aislamiento entre fincas.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sqlite3
import struct
import tempfile
import unicodedata
import zipfile
from contextlib import contextmanager

from . import catalogos

# El GeoPackage puede venir en ETRS89 (4258) o en WGS84 (4326). Los dos son longitud/latitud, que
# es lo que guarda el programa (`Parcela.geometria`, WKT) y lo que leen `geo.centroide_wkt` y
# `geo.dibujo_svg`. Cualquier otro sistema se rechaza: guardar coordenadas proyectadas en una
# columna que todo el programa lee como grados daría un mapa en otro sitio.
SRS_ADMITIDOS = (4326, 4258)

# Los tipos de WKB que se saben leer, por su código numérico. Un recinto del SIGPAC es un polígono
# (o varios, cuando el recinto tiene islas o trozos separados).
POLYGON = 3
MULTIPOLYGON = 6

# Los decimales con los que se escribe el WKT: siete, que es un centímetro. El SIGPAC publica más y
# no aportan nada a un contorno de parcela; con siete el texto no se hincha y la forma es la misma.
DECIMALES = 7

# Los nombres canónicos de las columnas que se buscan, con los nombres aceptados para cada uno. La
# comparación es por nombre normalizado (sin tildes, sin mayúsculas y con los separadores iguales).
COLUMNAS = {
    "provincia": ("provincia", "codigo_provincia", "prov"),
    "municipio": ("municipio", "codigo_municipio", "mun"),
    "agregado": ("agregado", "codigo_agregado"),
    "zona": ("zona",),
    "poligono": ("poligono", "numero_poligono"),
    "parcela": ("parcela", "numero_parcela"),
    "recinto": ("recinto", "numero_recinto"),
    "uso_sigpac": ("uso_sigpac", "uso"),
    "coef_regadio": ("coef_regadio", "coeficiente_regadio"),
    "region": ("region",),
    # El CSP: el GeoPackage del SIGPAC lo llama **`csp`** y el servicio REST `admisibilidad`. Son el
    # mismo número (0–100) con dos nombres, y si no se reconoce el del fichero, el CSP llega vacío.
    "admisibilidad": ("admisibilidad", "csp"),
    # Y la superficie del recinto es **`dn_surface`** en el fichero de verdad (en hectáreas, aunque el
    # nombre no lo diga): sin este nombre, `superficie_ha` salía en blanco con el mapa real.
    "superficie": ("superficie", "superficie_ha", "dn_surface", "dn_superficie", "area"),
}

# **Sin estas columnas no hay nada que hacer.** Con ellas se puede casar un recinto con una parcela;
# el resto (uso, coeficiente, región, admisibilidad, superficie) es información añadida y, si no está,
# el recinto se devuelve igual, sin ese dato. Faltando una de estas, se para: adivinar con qué se
# casa un recinto sería devolver el contorno de otra tierra.
IMPRESCINDIBLES = ("provincia", "municipio", "poligono", "parcela", "recinto")

# La superficie del recinto **no viene siempre en la misma unidad**, y el fichero no lo dice en
# ningún sitio: `dn_surface`, que es como la llama el GeoPackage de verdad del SIGPAC, viene en
# **metros cuadrados** (el recinto 37-70-0-0-503-51-1 trae 49.015,59 → 4,9016 ha), mientras que el
# servicio del SIGPAC la da en **hectáreas**. Se descubrió con el fichero real de Salamanca: sin este
# factor, cada parcela salía 10.000 veces más grande. La unidad se decide **por el nombre de la
# columna** y no adivinando por el tamaño: dividir por 10.000 una cifra que ya venía en hectáreas
# dejaría la parcela 10.000 veces más pequeña, que es el mismo error al revés.
FACTOR_DE_SUPERFICIE = {
    "dn_surface": 0.0001,
    "dn_superficie": 0.0001,
    "shape_area": 0.0001,
    "area_m2": 0.0001,
    "superficie_m2": 0.0001,
}

# El tope de recintos que devuelve una búsqueda. Una parcela tiene pocos recintos; este número está
# para que una consulta mal formada no se lleve la tabla entera por delante.
MAXIMO_POR_BUSQUEDA = 200


class GeopackageDesconocido(RuntimeError):
    """El fichero no es un GeoPackage que este programa sepa leer.

    Es un error **del fichero o del esquema**, no de los datos: se dice qué se esperaba y qué hay,
    en vez de seguir adelante y devolver contornos de otra cosa.
    """


# ---------------------------------------------------------------------------
# Nombres: normalizar para buscar columnas y para casar municipios
# ---------------------------------------------------------------------------


def _normaliza(texto: str) -> str:
    """El nombre en minúsculas, sin tildes y con los separadores como `_`."""
    sin_tildes = unicodedata.normalize("NFKD", str(texto or ""))
    limpio = "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()
    return "_".join(parte for parte in limpio.replace("-", "_").replace(" ", "_").split("_") if parte)


# ---------------------------------------------------------------------------
# La geometría: cabecera del GeoPackage + WKB
# ---------------------------------------------------------------------------


class _Wkb:
    """Un lector de WKB con su posición, que respeta el orden de bytes de cada geometría.

    El orden de bytes se repite **en cada geometría** del WKB (una MultiPolygon puede traer sus
    polígonos con órdenes distintos), así que no se puede leer una vez y suponer el resto.
    """

    def __init__(self, datos: bytes):
        self.datos = datos
        self.pos = 0

    def _toma(self, cuantos: int) -> bytes:
        if self.pos + cuantos > len(self.datos):
            raise GeopackageDesconocido(
                "La geometría del recinto está cortada: el fichero no está completo."
            )
        trozo = self.datos[self.pos : self.pos + cuantos]
        self.pos += cuantos
        return trozo

    def doble(self, orden: str) -> float:
        return struct.unpack(orden + "d", self._toma(8))[0]

    def entero(self, orden: str) -> int:
        return struct.unpack(orden + "I", self._toma(4))[0]

    def cabecera(self) -> tuple[str, int]:
        """El orden de bytes y el tipo de la geometría que empieza aquí."""
        (bandera,) = struct.unpack("B", self._toma(1))
        if bandera not in (0, 1):
            raise GeopackageDesconocido(
                f"La geometría del recinto lleva un orden de bytes que no existe ({bandera})."
            )
        orden = "<" if bandera == 1 else ">"
        tipo = self.entero(orden)
        return orden, tipo


def _el_anillo(cursor: _Wkb, orden: str, cuantos: int) -> list[tuple[float, float]]:
    return [(cursor.doble(orden), cursor.doble(orden)) for _ in range(cuantos)]


def _tipo_sin_dimension(tipo: int) -> tuple[int, bool]:
    """El tipo de WKB sin la dimensión, y si la traía.

    El tipo se codifica de tres maneras según quién escribió el fichero, y las tres aparecen en la
    naturaleza: la de toda la vida (3 = polígono), la **ISO** que suma 1000 por cada dimensión
    (1003 = polígono con Z) y la **EWKB** de PostGIS, que pone la Z y la M en los bits altos. Se
    aceptan las tres formas de *leer* para poder decir «esto trae altura», pero **solo se leen las
    planas**: un punto con Z lleva un número más por punto y leerlo como plano daría coordenadas de
    otro sitio.
    """
    trae_dimension = False
    if tipo & 0x80000000:  # EWKB: Z
        tipo &= 0x0FFFFFFF
        trae_dimension = True
    if tipo & 0x40000000:  # EWKB: M
        tipo &= 0x0FFFFFFF
        trae_dimension = True
    if tipo >= 1000:  # ISO: 1000 + tipo (Z), 2000 (M), 3000 (ZM)
        tipo = tipo % 1000
        trae_dimension = True
    return tipo, trae_dimension


def _lee_wkb(cursor: _Wkb) -> tuple[str, list[list[tuple[float, float]]]]:
    """Una geometría en WKT y sus anillos, en `[longitud, latitud]`.

    Soporta `Polygon` y `MultiPolygon`, que es lo que publica el SIGPAC. **Cualquier otro tipo se
    dice con su código**: convertir una línea en un polígono, o saltársela, sería devolver un
    contorno que no es el del recinto.
    """
    orden, tipo = cursor.cabecera()
    base, trae_dimension = _tipo_sin_dimension(tipo)
    if trae_dimension:
        raise GeopackageDesconocido(
            f"El recinto trae una geometría con altura o medida (tipo {tipo}), "
            "que este programa no sabe leer: cada punto llevaría más números de los que se esperan."
        )
    if base not in (POLYGON, MULTIPOLYGON):
        raise GeopackageDesconocido(
            f"El recinto trae una geometría de tipo {tipo}, que este programa no sabe leer. "
            "Solo se leen polígonos y multipolígonos (un recinto del SIGPAC es una superficie)."
        )
    if base == POLYGON:
        anillos = []
        (cuantos_anillos,) = struct.unpack(orden + "I", cursor._toma(4))
        for _ in range(cuantos_anillos):
            (cuantos_puntos,) = struct.unpack(orden + "I", cursor._toma(4))
            anillos.append(_el_anillo(cursor, orden, cuantos_puntos))
        wkt = "POLYGON(" + ",".join(_un_anillo(anillo) for anillo in anillos) + ")"
        return wkt, anillos
    if tipo == MULTIPOLYGON:
        (cuantos,) = struct.unpack(orden + "I", cursor._toma(4))
        partes = []
        anillos: list[list[tuple[float, float]]] = []
        for _ in range(cuantos):
            suyo_wkt, sus_anillos = _lee_wkb(cursor)
            # `suyo_wkt` empieza por «POLYGON(» y lo que va dentro es lo que va dentro del
            # MULTIPOLYGON; se quita la envoltura para volver a envolverla una sola vez.
            partes.append(suyo_wkt[len("POLYGON") :])
            anillos.extend(sus_anillos)
        return "MULTIPOLYGON(" + ",".join(partes) + ")", anillos
    # No se puede llegar aquí: el tipo ya se ha comprobado arriba. Se deja dicho por si alguien
    # añade un tipo nuevo y se olvida de su rama.
    raise GeopackageDesconocido(
        f"El recinto trae una geometría de tipo {tipo}, que este programa no sabe leer."
    )


def _un_numero(valor: float) -> str:
    return f"{valor:.{DECIMALES}f}"


def _un_anillo(anillo: list[tuple[float, float]]) -> str:
    return "(" + ",".join(f"{_un_numero(x)} {_un_numero(y)}" for x, y in anillo) + ")"


def leer_geometria(
    blob: bytes | None, srs_declarado: int | None = None
) -> tuple[str | None, list[list[tuple[float, float]]]]:
    """El blob de geometría de un GeoPackage a `(WKT, anillos)`, o `(None, [])` si viene vacío.

    **El formato, contado entero** (es lo único que hay que saber para leerlo sin GDAL): los bytes
    empiezan por `GP`, luego la versión, luego una bandera en la que el bit 0 dice el orden de bytes
    (1 = little endian), los bits 1-3 la **envolvente** que viene antes de la geometría (0 = ninguna,
    1 = x/y, 2 = x/y/z, 3 = x/y/m, 4 = x/y/z/m) y el bit 4 que la geometría está vacía. Después, el
    `srs_id` (entero de 32 bits) y, si hay, los dobles de la envolvente. Detrás va el **WKB**.

    **El `srs_id` del blob puede ser 0**, y en el fichero de verdad del SIGPAC **lo es**: significa
    «el sistema de coordenadas no se dice aquí», y el que vale es el que declara el fichero en
    `gpkg_geometry_columns` (que es lo que se pasa en `srs_declarado`). Antes se rechazaba el mapa
    entero por ese cero: se descubrió con el GeoPackage real de Salamanca. Si el blob **sí** dice un
    sistema, manda el suyo; y si ni uno ni otro lo dicen, no se adivina.
    """
    if not blob:
        return None, []
    if len(blob) < 8 or blob[:2] != b"GP":
        raise GeopackageDesconocido(
            "El recinto trae una geometría que no está en el formato de un GeoPackage "
            "(le falta la cabecera «GP»)."
        )
    version = blob[2]
    banderas = blob[3]
    if version != 0:
        raise GeopackageDesconocido(
            f"El GeoPackage es de una versión de geometría que no se sabe leer ({version})."
        )
    orden_cabecera = "<" if banderas & 0x01 else ">"
    tipo_de_envolvente = (banderas >> 1) & 0x07
    if tipo_de_envolvente not in (0, 1, 2, 3, 4):
        raise GeopackageDesconocido(
            f"El GeoPackage dice una envolvente que no existe ({tipo_de_envolvente})."
        )
    if banderas & 0x10:
        # «Geometry vacía»: no hay forma que dar. No es un error: se dice que no hay dibujo.
        return None, []
    (srs_del_blob,) = struct.unpack(orden_cabecera + "i", blob[4:8])
    # **El del blob manda si dice algo; si calla (0), el del fichero.**
    srs_id = srs_del_blob or srs_declarado
    if srs_id is None or srs_id == 0:
        raise GeopackageDesconocido(
            "La geometría del recinto no dice en qué sistema de coordenadas está, y el fichero "
            "tampoco. No se puede saber si son grados, así que no se lee."
        )
    if srs_id not in SRS_ADMITIDOS:
        raise GeopackageDesconocido(
            f"El mapa viene en un sistema de coordenadas que no es longitud/latitud "
            f"(srs_id {srs_id}). No se guarda para no dejar coordenadas que el mapa no sabría leer."
        )
    dobles = {0: 0, 1: 4, 2: 6, 3: 6, 4: 8}[tipo_de_envolvente]
    inicio_wkb = 8 + dobles * 8
    if len(blob) <= inicio_wkb:
        raise GeopackageDesconocido("El recinto trae la cabecera de la geometría y nada más.")
    wkt, anillos = _lee_wkb(_Wkb(blob[inicio_wkb:]))
    if not anillos:
        return None, []
    return wkt, anillos


# ---------------------------------------------------------------------------
# Abrir el fichero: la tabla, sus columnas y sus recintos
# ---------------------------------------------------------------------------


def _la_ruta_del_gpkg_guardado(ruta_zip: pathlib.Path, miembro: str) -> pathlib.Path:
    """Dónde se guarda el `.gpkg` extraído: **al lado del ZIP y con un nombre que sale del ZIP**.

    El nombre se deriva del ZIP (sin su extensión) y del miembro que lleva dentro, así que dos
    campañas distintas del mismo año, o un ZIP con otro mapa, no comparten fichero: cambiar el ZIP
    cambia la ruta y no hay manera de abrir el mapa viejo creyendo que es el nuevo.
    """
    nombre_del_miembro = pathlib.PurePosixPath(miembro).name
    return ruta_zip.with_name(f"{ruta_zip.stem}__{nombre_del_miembro}")


def _el_miembro_del_mapa(ruta_zip: pathlib.Path) -> tuple[str, int]:
    """El `.gpkg` que lleva dentro el ZIP y **lo que ocupa sin comprimir**, sin sacarlo.

    El tamaño se lee del índice del ZIP (el directorio central, al final del fichero): eso son unos
    kilobytes y milisegundos, y es lo que después permite saber si el `.gpkg` guardado al lado está
    entero sin volver a descomprimir 1 GB para comprobarlo.
    """
    try:
        with zipfile.ZipFile(ruta_zip) as paquete:
            mapas = [info for info in paquete.infolist() if info.filename.lower().endswith(".gpkg")]
            if not mapas:
                raise GeopackageDesconocido(
                    f"«{ruta_zip.name}» no lleva dentro ningún mapa (.gpkg). No se puede abrir."
                )
            return mapas[0].filename, mapas[0].file_size
    except zipfile.BadZipFile as error:
        raise GeopackageDesconocido(
            f"«{ruta_zip.name}» no es un ZIP válido: no se puede sacar el mapa de dentro."
        ) from error


def _el_guardado_sirve(guardado: pathlib.Path, ruta_zip: pathlib.Path, tamano: int) -> bool:
    """¿El `.gpkg` que hay al lado es el de **este** ZIP y está entero?

    Tres comprobaciones, todas baratas (ninguna descomprime nada):

      1. **El tamaño**: tiene que ser exactamente el que dice el índice del ZIP. Un fichero cortado
         por un apagón, o una extracción que se quedó a medias, no pasa de aquí.
      2. **La fecha**: el `.gpkg` no puede ser más viejo que el ZIP. Si han vuelto a bajar el mapa
         encima (mismo nombre, contenido nuevo), el ZIP es más nuevo y esto lo detecta.
      3. **Que se pueda leer**: de eso se encarga `abrir_recintos`, que si el fichero guardado no se
         abre con sqlite lo tira y lo extrae otra vez.
    """
    try:
        datos = guardado.stat()
        del_zip = ruta_zip.stat()
    except OSError:
        return False
    if not guardado.is_file() or datos.st_size != tamano:
        return False
    return del_zip.st_mtime <= datos.st_mtime


def _extraer_al_lado(ruta_zip: pathlib.Path, miembro: str, destino: pathlib.Path) -> None:
    """Saca el mapa del ZIP **a un temporal en la misma carpeta** y lo mueve a su sitio.

    Se escribe primero con otro nombre y se mueve con `os.replace` (que en el mismo disco es un
    cambio de nombre, atómico): así en la carpeta de la caché **nunca** queda un `.gpkg` a medias que
    después parezca bueno. Y se saca por trozos de 1 MB, no de golpe: el mapa de una provincia son
    1.070 MB y no tienen por qué pasar por la memoria del programa.
    """
    temporal = destino.with_name(f".{destino.name}.extrayendo")
    try:
        with zipfile.ZipFile(ruta_zip) as paquete:
            with paquete.open(miembro) as origen, temporal.open("wb") as salida:
                shutil.copyfileobj(origen, salida, 1024 * 1024)
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)


def _sacar_al_temporal(ruta_zip: pathlib.Path, miembro: str) -> tuple[pathlib.Path, pathlib.Path]:
    """El camino de siempre: extraer a una carpeta temporal (que se borra al cerrar)."""
    carpeta = pathlib.Path(tempfile.mkdtemp(prefix="sigpac_gpkg_"))
    destino = carpeta / "mapa.gpkg"
    try:
        with zipfile.ZipFile(ruta_zip) as paquete:
            with paquete.open(miembro) as origen, destino.open("wb") as salida:
                shutil.copyfileobj(origen, salida, 1024 * 1024)
    except OSError:
        _borrar_la_carpeta(carpeta)
        raise
    return destino, carpeta


def _borrar_la_carpeta(carpeta: pathlib.Path | None) -> None:
    """Borra la carpeta temporal de la extracción, sin protestar si ya no está."""
    if carpeta is None:
        return
    for fichero in carpeta.glob("*"):
        try:
            fichero.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        carpeta.rmdir()
    except OSError:
        pass


def _el_fichero(
    ruta: pathlib.Path, *, volver_a_extraer: bool = False
) -> tuple[pathlib.Path, pathlib.Path | None, bool]:
    """El `.gpkg` que hay que abrir, la carpeta temporal a borrar (o `None`) y si salió del guardado.

    La caché del SIGPAC guarda **el ZIP oficial** tal y como lo publica el FEGA (con el `.gpkg`
    dentro). `sqlite3` necesita un fichero de verdad, no un miembro de un ZIP, y descomprimir 1.070
    MB en cada llamada costaba entre 6 y 56 segundos (medido con el mapa de Salamanca). Así que:

      1. Si el `.gpkg` **ya está sacado al lado del ZIP** y sirve (ver `_el_guardado_sirve`), se abre
         ese directamente. **No se descomprime nada.**
      2. Si no está o no sirve, se saca al lado (por un temporal y con `os.replace`) y se usa. Las
         siguientes aperturas ya no descomprimen.
      3. **Si la carpeta del ZIP no se puede escribir** (solo lectura, sin permisos, sin sitio), se
         saca al temporal de siempre y se borra al cerrar: se pierde la mejora, pero **nunca se
         rompe** por no poder cachear. Eso se nota en `LectorDeRecintos.cacheado`, que sale en falso.

    Dos procesos abriendo a la vez no se pisan: la extracción se hace a un temporal con otro nombre
    y se mueve con `os.replace`; y si el sistema no deja mover el fichero porque otro lo tiene
    abierto (en Windows, un fichero abierto no se puede reemplazar), ese caso cae en el punto 3 y se
    abre desde el temporal. Lo peor que puede pasar es descomprimir dos veces, no leer un mapa roto.
    """
    if ruta.suffix.lower() == ".gpkg":
        return ruta, None, False
    if ruta.suffix.lower() != ".zip":
        raise GeopackageDesconocido(
            f"«{ruta.name}» no es un GeoPackage ni el ZIP que lo trae. No se puede abrir."
        )

    miembro, tamano = _el_miembro_del_mapa(ruta)
    guardado = _la_ruta_del_gpkg_guardado(ruta, miembro)
    if not volver_a_extraer and _el_guardado_sirve(guardado, ruta, tamano):
        return guardado, None, True

    try:
        _extraer_al_lado(ruta, miembro, guardado)
        # `False` porque **en esta apertura sí se ha descomprimido** (la mejora es para las
        # siguientes): el que se acaba de sacar no se está «cacheando», se está pagando.
        return guardado, None, False
    except zipfile.BadZipFile as error:
        raise GeopackageDesconocido(
            f"«{ruta.name}» no es un ZIP válido: no se puede sacar el mapa de dentro."
        ) from error
    except OSError:
        # La carpeta de la caché es de solo lectura o no hay sitio: al temporal de siempre.
        destino, carpeta = _sacar_al_temporal(ruta, miembro)
        return destino, carpeta, False


def _tabla_y_geometria(conexion: sqlite3.Connection) -> tuple[str, str, int | None]:
    """La tabla de recintos, su columna de geometría y el sistema de coordenadas que declara.

    No se da por hecho que la tabla se llame `recintos`: se miran las que el GeoPackage declara como
    geométricas y se elige la primera que tenga las columnas imprescindibles. Si no hay ninguna, se
    dice lo que hay.

    El **sistema de coordenadas** sale de aquí y no del blob de cada recinto porque el fichero real
    del SIGPAC lo deja a 0 en todas las geometrías (son 1.011.578 recintos en Salamanca, y ninguno lo
    dice): el que vale es el que declara el fichero, y por eso se lee aquí una sola vez.
    """
    try:
        filas = conexion.execute(
            "SELECT table_name, column_name, srs_id FROM gpkg_geometry_columns"
        ).fetchall()
    except sqlite3.DatabaseError as error:
        raise GeopackageDesconocido(
            "El fichero no es un GeoPackage: no tiene la tabla de geometrías "
            "(gpkg_geometry_columns)."
        ) from error
    if not filas:
        raise GeopackageDesconocido(
            "El GeoPackage no declara ninguna tabla con geometría: no hay recintos que leer."
        )
    revisadas: list[str] = []
    for tabla, columna, srs_id in filas:
        columnas = _columnas_de(conexion, tabla)
        faltan = [clave for clave in IMPRESCINDIBLES if clave not in columnas]
        if not faltan:
            return tabla, columna, srs_id
        revisadas.append(f"{tabla} (le faltan: {', '.join(faltan)})")
    raise GeopackageDesconocido(
        "Ninguna tabla del GeoPackage tiene las columnas de un recinto del SIGPAC. "
        f"Revisadas: {'; '.join(revisadas)}."
    )


def _columnas_de(conexion: sqlite3.Connection, tabla: str) -> dict[str, str]:
    """Las columnas de la tabla, con el nombre canónico de cada una.

    Se busca **por el nombre normalizado** y no por la posición: un GeoPackage de otra campaña puede
    cambiar el orden de las columnas, y leer «la cuarta» devolvería el dato de al lado sin avisar.
    """
    try:
        nombres = [fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')]
    except sqlite3.DatabaseError as error:
        raise GeopackageDesconocido(f"No se puede leer la tabla «{tabla}» del GeoPackage.") from error
    normalizados = {_normaliza(nombre): nombre for nombre in nombres}
    encontradas: dict[str, str] = {}
    for clave, aceptados in COLUMNAS.items():
        for aceptado in aceptados:
            if _normaliza(aceptado) in normalizados:
                encontradas[clave] = normalizados[_normaliza(aceptado)]
                break
    return encontradas


class LectorDeRecintos:
    """Los recintos de un GeoPackage del SIGPAC, leídos por sus códigos.

    Se abre con `abrir_recintos(ruta)` y se cierra solo (context manager): el fichero, la conexión y,
    si el mapa venía en un ZIP, la carpeta temporal que se sacó.
    """

    def __init__(
        self,
        conexion: sqlite3.Connection,
        tabla: str,
        columna: str,
        columnas: dict[str, str],
        srs: int | None = None,
        cacheado: bool = False,
    ):
        self.conexion = conexion
        self.tabla = tabla
        self.columna = columna
        self.columnas = columnas
        # **El sistema de coordenadas que declara el fichero.** Hace falta porque las geometrías del
        # SIGPAC de verdad lo dejan a 0 en su cabecera (ver `leer_geometria`).
        self.srs = srs
        # `True` si en esta apertura **no se ha descomprimido nada**: se ha abierto el `.gpkg` que ya
        # estaba sacado al lado del ZIP. `False` si se ha tenido que sacar ahora, o si la carpeta no
        # dejaba cachear y se ha ido al temporal de siempre.
        self.cacheado = cacheado

    def buscar(
        self,
        provincia: int,
        municipio: int,
        poligono: int,
        parcela: int,
        recinto: int | None = None,
        *,
        limite: int = MAXIMO_POR_BUSQUEDA,
    ) -> list[dict]:
        """Los recintos que contestan a esos códigos, con su WKT y sus anillos.

        **Se pregunta por los códigos, no por el texto**: los nombres de municipio de una parcela
        pueden venir escritos de tres maneras y los códigos son los mismos en el visor, en el
        cuaderno de la Junta y en el GeoPackage.
        """
        condiciones = [
            f'"{self.columnas["provincia"]}" = ?',
            f'"{self.columnas["municipio"]}" = ?',
            f'"{self.columnas["poligono"]}" = ?',
            f'"{self.columnas["parcela"]}" = ?',
        ]
        valores: list[object] = [int(provincia), int(municipio), int(poligono), int(parcela)]
        if recinto is not None:
            condiciones.append(f'"{self.columnas["recinto"]}" = ?')
            valores.append(int(recinto))
        columnas = ", ".join(
            f'"{self.columnas[clave]}"' for clave in COLUMNAS if clave in self.columnas
        )
        orden = ""
        if recinto is None and "recinto" in self.columnas:
            orden = f' ORDER BY "{self.columnas["recinto"]}"'
        consulta = (
            f'SELECT {columnas}, "{self.columna}" FROM "{self.tabla}" '
            f"WHERE {' AND '.join(condiciones)}{orden} LIMIT ?"
        )
        try:
            filas = self.conexion.execute(consulta, [*valores, int(limite)]).fetchall()
        except sqlite3.DatabaseError as error:
            raise GeopackageDesconocido(
                f"No se han podido leer los recintos de la tabla «{self.tabla}»."
            ) from error
        claves = [clave for clave in COLUMNAS if clave in self.columnas]
        # **En qué unidad viene la superficie lo dice el nombre de su columna** (ver
        # `FACTOR_DE_SUPERFICIE`): el fichero real la llama `dn_surface` y la da en metros cuadrados.
        columna_de_superficie = _normaliza(self.columnas.get("superficie", ""))
        factor_de_superficie = FACTOR_DE_SUPERFICIE.get(columna_de_superficie, 1.0)
        salida = []
        for fila in filas:
            recinto_crudo = dict(zip(claves, fila[: len(claves)]))
            wkt, anillos = leer_geometria(fila[-1], self.srs)
            superficie = recinto_crudo.get("superficie")
            if superficie is not None:
                # Redondeada a cuatro decimales de hectárea (un metro cuadrado): el servicio da cuatro.
                superficie = round(float(superficie) * factor_de_superficie, 4)
            salida.append(
                {
                    **_los_codigos(recinto_crudo),
                    "uso_sigpac": recinto_crudo.get("uso_sigpac"),
                    "coef_regadio": recinto_crudo.get("coef_regadio"),
                    "region": recinto_crudo.get("region"),
                    "admisibilidad": recinto_crudo.get("admisibilidad"),
                    "superficie_ha": superficie,
                    "wkt": wkt,
                    "puntos": [[x, y] for x, y in anillos[0]] if anillos else None,
                    "anillos": [[[x, y] for x, y in anillo] for anillo in anillos],
                }
            )
        return salida


def _los_codigos(fila: dict) -> dict:
    """Los cinco códigos del recinto como enteros (o `None` si el fichero los trae vacíos)."""

    def _entero(clave):
        valor = fila.get(clave)
        try:
            return int(valor)
        except (TypeError, ValueError):
            return None

    return {
        "provincia": _entero("provincia"),
        "municipio": _entero("municipio"),
        "agregado": _entero("agregado"),
        "zona": _entero("zona"),
        "poligono": _entero("poligono"),
        "parcela": _entero("parcela"),
        "recinto": _entero("recinto"),
    }


def _la_conexion(
    mapa: pathlib.Path,
) -> tuple[sqlite3.Connection, str, str, dict[str, str], int | None]:
    """Abre el `.gpkg` con sqlite y mira dentro: tabla, columna de geometría, columnas y sistema.

    Todo junto porque es lo que hace falta para leer, y porque **abrir mal un fichero casi nunca falla
    al abrirlo**: sqlite es perezoso y el «no es un fichero de base de datos» sale en la primera
    consulta. Aquí se ve en un sitio y se traduce a `GeopackageDesconocido`.
    """
    conexion = sqlite3.connect(f"file:{mapa}?mode=ro", uri=True)
    try:
        tabla, columna, srs = _tabla_y_geometria(conexion)
        columnas = _columnas_de(conexion, tabla)
    except GeopackageDesconocido:
        conexion.close()
        raise
    except sqlite3.DatabaseError as error:
        conexion.close()
        raise GeopackageDesconocido(
            "El fichero del SIGPAC no se puede abrir como GeoPackage: está dañado o cortado."
        ) from error
    return conexion, tabla, columna, columnas, srs


@contextmanager
def abrir_recintos(ruta: str | os.PathLike):
    """Abre el GeoPackage (o el ZIP que lo trae) y deja un `LectorDeRecintos` listo para buscar.

    **Si viene en ZIP no se descomprime en cada llamada**: la primera vez se saca el `.gpkg` al lado
    del ZIP (por un temporal y con `os.replace`) y las siguientes se abre ese directamente. Ver
    `_el_fichero` para las tres comprobaciones que hacen que el guardado sea el de este ZIP y esté
    entero, y para lo que pasa si la carpeta no se puede escribir.
    """
    camino = pathlib.Path(ruta)
    if not camino.is_file():
        raise GeopackageDesconocido(
            f"No está el fichero del SIGPAC: «{camino.name}». Descárgalo antes de pedir contornos."
        )
    temporal: pathlib.Path | None = None
    conexion: sqlite3.Connection | None = None
    try:
        for intento in (0, 1):
            mapa, temporal, cacheado = _el_fichero(
                camino, volver_a_extraer=(intento == 1)
            )
            try:
                conexion, tabla, columna, columnas, srs = _la_conexion(mapa)
            except GeopackageDesconocido:
                conexion = None
                _borrar_la_carpeta(temporal)
                temporal = None
                # **Si el que fallaba era el `.gpkg` guardado, se tira y se extrae otra vez**: un
                # fichero cortado (un apagón a mitad de la extracción) no puede dejar el mapa sin
                # abrir para siempre. Solo se reintenta una vez, y solo si venía del guardado.
                if intento == 0 and cacheado:
                    continue
                raise
            break
        assert conexion is not None  # el bucle o saca conexión o lanza
        yield LectorDeRecintos(conexion, tabla, columna, columnas, srs, cacheado)
    finally:
        if conexion is not None:
            conexion.close()
        _borrar_la_carpeta(temporal)


# ---------------------------------------------------------------------------
# De la parcela al recinto: los códigos y los contornos
# ---------------------------------------------------------------------------


def _el_municipio(provincia: str | None, municipio: str | None):
    """El municipio oficial que **coincide exactamente** con ese nombre, o `None`.

    Se reutiliza el catálogo que ya usa el programa (`catalogos.busca_municipios`, cargado del
    diccionario del INE) y se exige que el nombre coincida **entero**: una búsqueda por parecido
    casaría «Villanueva» con «Villanueva de la Serena» y la parcela acabaría con el contorno de otra
    tierra. Si no hay coincidencia, no se adivina: se dice.
    """
    buscado = _normaliza(municipio or "")
    if not buscado:
        return None
    candidatos = catalogos.busca_municipios(str(municipio or ""), provincia, limite=25)
    for candidato in candidatos:
        if _normaliza(candidato.nombre) != buscado:
            continue
        if provincia and _normaliza(candidato.provincia) != _normaliza(provincia):
            continue
        return candidato
    return None


def _la_busqueda_guardada(parcela) -> "sigpac.Busqueda | None":
    """La referencia del SIGPAC de la parcela, leída, o `None` si no la tiene o no se entiende.

    Sirve para las tierras **que ya estaban guardadas** antes de que el alta rellenara los códigos
    (IMP-25): su referencia lleva dentro los siete números aunque las columnas estén en blanco. Se
    lee aquí y no se escribe nada: mirar no cambia el dato del agricultor.
    """
    from . import sigpac

    try:
        return sigpac.lee_busqueda(str(getattr(parcela, "ref_sigpac", None) or "").strip())
    except sigpac.ReferenciaInvalida:
        return None


def codigos_de_una_parcela(parcela) -> tuple[int, int] | None:
    """Los códigos `(provincia, municipio)` con los que buscar su recinto, o `None`.

    **Primero el código INE que la parcela ya trae** (cinco cifras: dos de provincia y tres de
    municipio), que es el dato bueno y no hay que deducirlo. Si no lo tiene, se casa su
    provincia/municipio con el catálogo oficial. Y si tampoco hay manera por ahí, **se mira su
    referencia del SIGPAC** (IMP-25), que lleva los códigos dentro: es lo que hace que una tierra
    apuntada solo con la referencia del papel también reciba su contorno. Si nada de eso vale,
    `None`: la parcela se cuenta aparte.
    """
    ine = str(getattr(parcela, "codigo_ine", None) or "").strip()
    if len(ine) == 5 and ine.isdigit():
        return int(ine[:2]), int(ine[2:])
    municipio = _el_municipio(getattr(parcela, "provincia", None), getattr(parcela, "municipio", None))
    if municipio is not None:
        try:
            return int(municipio.codigo_provincia), int(municipio.codigo_municipio)
        except (TypeError, ValueError):
            pass
    # **Y la referencia, que es el último sitio donde están los códigos** (IMP-25).
    guardada = _la_busqueda_guardada(parcela)
    if guardada is None:
        return None
    try:
        return int(guardada.provincia), int(guardada.municipio)
    except (TypeError, ValueError):
        return None


def _los_numeros_de_la_parcela(parcela) -> tuple[int, int, int, int, int | None] | None:
    """`(provincia, municipio, polígono, parcela, recinto o None)` para buscar en el mapa.

    Los códigos de municipio salen de `codigos_de_una_parcela` (INE, catálogo o referencia) y los
    números del polígono y de la parcela, de sus columnas; **si alguna columna está en blanco se
    toma de la referencia** (IMP-25), que es lo que arregla las tierras guardadas antes sin migrar.
    El **recinto puede faltar**: la referencia del visor trae seis números y no dice cuál de los
    recintos de esa parcela es. Se devuelve `None` en esa posición y el que llama decide con el
    mapa: si solo hay un recinto, se coge; si hay varios, se pide elegir. **No se adivina.**
    """
    codigos = codigos_de_una_parcela(parcela)
    poligono = getattr(parcela, "poligono", None)
    numero_parcela = getattr(parcela, "numero_parcela", None)
    numero_recinto = getattr(parcela, "numero_recinto", None)
    if codigos is None or None in (poligono, numero_parcela):
        guardada = _la_busqueda_guardada(parcela)
        if guardada is not None:
            if codigos is None:
                codigos = (int(guardada.provincia), int(guardada.municipio))
            if poligono is None:
                poligono = guardada.poligono
            if numero_parcela is None:
                numero_parcela = guardada.parcela
            if numero_recinto is None:
                numero_recinto = guardada.recinto
    if codigos is None or poligono is None or numero_parcela is None:
        return None
    return (
        int(codigos[0]),
        int(codigos[1]),
        int(poligono),
        int(numero_parcela),
        int(numero_recinto) if numero_recinto is not None else None,
    )


def contornos_de_las_parcelas(parcelas, ruta: str | os.PathLike) -> dict:
    """**El contorno de cada parcela**, sacado del mapa, y lo que no se ha podido hacer.

    Devuelve cuatro listas y el total mirado:

      · `actualizadas`: las que tienen su recinto y su forma, con el WKT y los puntos del contorno.
      · `sin_forma`: las que se han encontrado pero el recinto viene **sin geometría** (o vacía). No
        se les pone un cuadro: se dice, y la parcela se queda como estaba.
      · `no_encontradas`: las que tienen códigos pero ese recinto **no está en el mapa**. Puede ser
        que el mapa sea de otra campaña o que la referencia esté mal copiada.
      · `sin_codigos`: las que no se pueden casar con ningún municipio del catálogo (o les falta el
        polígono, la parcela o el recinto). **Nunca se adivina un código.** Los que falten se buscan
        antes en la referencia del SIGPAC de la propia tierra (IMP-25), así que una tierra apuntada
        solo con la referencia también casa.

    El orden de las listas es el de las parcelas que se pasan, para que la respuesta sea la misma
    entre dos llamadas.
    """
    actualizadas: list[dict] = []
    sin_forma: list[dict] = []
    no_encontradas: list[dict] = []
    sin_codigos: list[dict] = []
    parcelas = list(parcelas)
    with abrir_recintos(ruta) as lector:
        for parcela in parcelas:
            ficha = {"id": parcela.id, "alias": parcela.alias, "ref_sigpac": parcela.ref_sigpac}
            numeros = _los_numeros_de_la_parcela(parcela)
            if numeros is None:
                motivo = (
                    "le falta el polígono, la parcela o el recinto"
                    if codigos_de_una_parcela(parcela) is not None
                    or _la_busqueda_guardada(parcela) is not None
                    else "su municipio no está en el catálogo oficial"
                )
                sin_codigos.append({**ficha, "motivo": motivo})
                continue
            provincia, municipio, poligono, numero_parcela, numero_recinto = numeros
            if numero_recinto is None:
                # La referencia del visor no dice el recinto. Si esa parcela tiene **uno solo**,
                # no hay nada que elegir; si tiene varios, se dice y no se adivina (IMP-27).
                candidatos = lector.buscar(
                    provincia,
                    municipio,
                    poligono,
                    numero_parcela,
                    None,
                    limite=MAXIMO_POR_BUSQUEDA,
                )
                if len(candidatos) > 1:
                    sin_codigos.append(
                        {
                            **ficha,
                            "motivo": (
                                "la referencia no dice el recinto y esa parcela tiene "
                                f"{len(candidatos)} recintos; elige uno"
                            ),
                        }
                    )
                    continue
                if not candidatos:
                    no_encontradas.append({**ficha, "motivo": "esa parcela no está en el mapa"})
                    continue
                numero_recinto = candidatos[0]["recinto"]
            encontrados = lector.buscar(
                provincia,
                municipio,
                poligono,
                numero_parcela,
                numero_recinto,
                limite=1,
            )
            if not encontrados:
                no_encontradas.append(ficha)
                continue
            encontrado = encontrados[0]
            if not encontrado["wkt"]:
                sin_forma.append({**ficha, "motivo": "su recinto no trae la forma"})
                continue
            actualizadas.append(
                {
                    **ficha,
                    "wkt": encontrado["wkt"],
                    "puntos": encontrado["puntos"],
                    "uso_sigpac": encontrado["uso_sigpac"],
                }
            )
    return {
        "n": len(parcelas),
        "actualizadas": actualizadas,
        "sin_forma": sin_forma,
        "no_encontradas": no_encontradas,
        "sin_codigos": sin_codigos,
    }
