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
    "admisibilidad": ("admisibilidad",),
    "superficie": ("superficie", "superficie_ha", "area"),
}

# **Sin estas columnas no hay nada que hacer.** Con ellas se puede casar un recinto con una parcela;
# el resto (uso, coeficiente, región, admisibilidad, superficie) es información añadida y, si no está,
# el recinto se devuelve igual, sin ese dato. Faltando una de estas, se para: adivinar con qué se
# casa un recinto sería devolver el contorno de otra tierra.
IMPRESCINDIBLES = ("provincia", "municipio", "poligono", "parcela", "recinto")

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


def leer_geometria(blob: bytes | None) -> tuple[str | None, list[list[tuple[float, float]]]]:
    """El blob de geometría de un GeoPackage a `(WKT, anillos)`, o `(None, [])` si viene vacío.

    **El formato, contado entero** (es lo único que hay que saber para leerlo sin GDAL): los bytes
    empiezan por `GP`, luego la versión, luego una bandera en la que el bit 0 dice el orden de bytes
    (1 = little endian), los bits 1-3 la **envolvente** que viene antes de la geometría (0 = ninguna,
    1 = x/y, 2 = x/y/z, 3 = x/y/m, 4 = x/y/z/m) y el bit 4 que la geometría está vacía. Después, el
    `srs_id` (entero de 32 bits) y, si hay, los dobles de la envolvente. Detrás va el **WKB**.
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
    (srs_id,) = struct.unpack(orden_cabecera + "i", blob[4:8])
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


def _el_fichero(ruta: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path | None]:
    """El `.gpkg` que hay que abrir y, si venía en un ZIP, la carpeta temporal que hay que borrar.

    La caché del SIGPAC guarda **el ZIP oficial** tal y como lo publica el FEGA (con el `.gpkg`
    dentro). `sqlite3` necesita un fichero de verdad, no un miembro de un ZIP, así que cuando viene
    comprimido se saca a una carpeta temporal y se borra al cerrar. Se saca **solo ese fichero**, no
    el ZIP entero: lo que ocupa es el mapa, y no hay más que sacar.
    """
    if ruta.suffix.lower() == ".gpkg":
        return ruta, None
    if ruta.suffix.lower() != ".zip":
        raise GeopackageDesconocido(
            f"«{ruta.name}» no es un GeoPackage ni el ZIP que lo trae. No se puede abrir."
        )
    try:
        with zipfile.ZipFile(ruta) as paquete:
            mapas = [nombre for nombre in paquete.namelist() if nombre.lower().endswith(".gpkg")]
            if not mapas:
                raise GeopackageDesconocido(
                    f"«{ruta.name}» no lleva dentro ningún mapa (.gpkg). No se puede abrir."
                )
            carpeta = pathlib.Path(tempfile.mkdtemp(prefix="sigpac_gpkg_"))
            destino = carpeta / "mapa.gpkg"
            with paquete.open(mapas[0]) as origen, destino.open("wb") as salida:
                while True:
                    trozo = origen.read(1024 * 1024)
                    if not trozo:
                        break
                    salida.write(trozo)
            return destino, carpeta
    except zipfile.BadZipFile as error:
        raise GeopackageDesconocido(
            f"«{ruta.name}» no es un ZIP válido: no se puede sacar el mapa de dentro."
        ) from error


def _tabla_y_geometria(conexion: sqlite3.Connection) -> tuple[str, str]:
    """La tabla de recintos y su columna de geometría, **preguntando al fichero**.

    No se da por hecho que la tabla se llame `recintos`: se miran las que el GeoPackage declara como
    geométricas y se elige la primera que tenga las columnas imprescindibles. Si no hay ninguna, se
    dice lo que hay.
    """
    try:
        filas = conexion.execute(
            "SELECT table_name, column_name FROM gpkg_geometry_columns"
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
    for tabla, columna in filas:
        columnas = _columnas_de(conexion, tabla)
        faltan = [clave for clave in IMPRESCINDIBLES if clave not in columnas]
        if not faltan:
            return tabla, columna
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

    def __init__(self, conexion: sqlite3.Connection, tabla: str, columna: str, columnas: dict[str, str]):
        self.conexion = conexion
        self.tabla = tabla
        self.columna = columna
        self.columnas = columnas

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
        salida = []
        for fila in filas:
            recinto_crudo = dict(zip(claves, fila[: len(claves)]))
            wkt, anillos = leer_geometria(fila[-1])
            salida.append(
                {
                    **_los_codigos(recinto_crudo),
                    "uso_sigpac": recinto_crudo.get("uso_sigpac"),
                    "coef_regadio": recinto_crudo.get("coef_regadio"),
                    "region": recinto_crudo.get("region"),
                    "admisibilidad": recinto_crudo.get("admisibilidad"),
                    "superficie_ha": recinto_crudo.get("superficie"),
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


@contextmanager
def abrir_recintos(ruta: str | os.PathLike):
    """Abre el GeoPackage (o el ZIP que lo trae) y deja un `LectorDeRecintos` listo para buscar."""
    camino = pathlib.Path(ruta)
    if not camino.is_file():
        raise GeopackageDesconocido(
            f"No está el fichero del SIGPAC: «{camino.name}». Descárgalo antes de pedir contornos."
        )
    mapa, temporal = _el_fichero(camino)
    try:
        conexion = sqlite3.connect(f"file:{mapa}?mode=ro", uri=True)
        try:
            tabla, columna = _tabla_y_geometria(conexion)
            columnas = _columnas_de(conexion, tabla)
            yield LectorDeRecintos(conexion, tabla, columna, columnas)
        finally:
            conexion.close()
    finally:
        if temporal is not None:
            for fichero in temporal.glob("*"):
                fichero.unlink(missing_ok=True)
            temporal.rmdir()


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


def codigos_de_una_parcela(parcela) -> tuple[int, int] | None:
    """Los códigos `(provincia, municipio)` con los que buscar su recinto, o `None`.

    **Primero el código INE que la parcela ya trae** (cinco cifras: dos de provincia y tres de
    municipio), que es el dato bueno y no hay que deducirlo. Si no lo tiene, se casa su
    provincia/municipio con el catálogo oficial. Si tampoco, `None`: la parcela se cuenta aparte.
    """
    ine = str(getattr(parcela, "codigo_ine", None) or "").strip()
    if len(ine) == 5 and ine.isdigit():
        return int(ine[:2]), int(ine[2:])
    municipio = _el_municipio(getattr(parcela, "provincia", None), getattr(parcela, "municipio", None))
    if municipio is None:
        return None
    try:
        return int(municipio.codigo_provincia), int(municipio.codigo_municipio)
    except (TypeError, ValueError):
        return None


def contornos_de_las_parcelas(parcelas, ruta: str | os.PathLike) -> dict:
    """**El contorno de cada parcela**, sacado del mapa, y lo que no se ha podido hacer.

    Devuelve cuatro listas y el total mirado:

      · `actualizadas`: las que tienen su recinto y su forma, con el WKT y los puntos del contorno.
      · `sin_forma`: las que se han encontrado pero el recinto viene **sin geometría** (o vacía). No
        se les pone un cuadro: se dice, y la parcela se queda como estaba.
      · `no_encontradas`: las que tienen códigos pero ese recinto **no está en el mapa**. Puede ser
        que el mapa sea de otra campaña o que la referencia esté mal copiada.
      · `sin_codigos`: las que no se pueden casar con ningún municipio del catálogo (o les falta el
        polígono, la parcela o el recinto). **Nunca se adivina un código.**

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
            if parcela.poligono is None or parcela.numero_parcela is None or parcela.numero_recinto is None:
                sin_codigos.append(
                    {**ficha, "motivo": "le falta el polígono, la parcela o el recinto"}
                )
                continue
            codigos = codigos_de_una_parcela(parcela)
            if codigos is None:
                sin_codigos.append(
                    {**ficha, "motivo": "su municipio no está en el catálogo oficial"}
                )
                continue
            provincia, municipio = codigos
            encontrados = lector.buscar(
                provincia,
                municipio,
                parcela.poligono,
                parcela.numero_parcela,
                parcela.numero_recinto,
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
        "n": len(list(parcelas)),
        "actualizadas": actualizadas,
        "sin_forma": sin_forma,
        "no_encontradas": no_encontradas,
        "sin_codigos": sin_codigos,
    }
