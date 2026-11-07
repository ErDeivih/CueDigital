"""**Abrir el GeoPackage del SIGPAC y rellenar los contornos** (IMP-12, 05/11/2026).

Lo que se prueba, y por qué:

  · **Que se lee el fichero de verdad**: un GeoPackage es un SQLite con una tabla de geometrías.
    Aquí se fabrica uno **sintético** con `sqlite3` y blobs escritos a mano (cabecera `GP` + WKB),
    así que las pruebas **no salen a internet** y no dependen de que el FEGA publique nada.
  · **Que la geometría se traduce bien**: el WKT y los anillos salen de lo que se metió en el blob,
    y un `MultiPolygon` también.
  · **Que lo que no se sabe se dice**: una columna imprescindible que falta, un tipo de geometría
    que no se lee y un fichero que no es un GeoPackage dan un error claro, no un dato inventado.
  · **Que la puerta rellena solo lo suyo**: la parcela de esta finca que casa se queda con su forma,
    la que no está en el mapa se dice aparte, y **la parcela de otra finca no se toca**.

Los blobs se escriben a mano a propósito: probar el lector con un fichero hecho por el propio lector
solo demostraría que es coherente consigo mismo.
"""

from __future__ import annotations

import json
import os
import sqlite3
import struct
import time
import zipfile
from types import SimpleNamespace

import pytest

from app import geopackage_sigpac
from test_los_permisos_por_materia import _sin_capacidad  # noqa: E402 — el andamiaje, prestado

# El nombre del mapa dentro del ZIP, con la pinta del de verdad (`0837_SALAMANCA_…gpkg`).
MIEMBRO = "0837_SALAMANCA_rec_2026_20251215.gpkg"

# La parcela de ejemplo: 37 / 70 / 0 / 0 / 503 / 51 / 1 (Salamanca, Calvarrasa de Arriba).
PROVINCIA, MUNICIPIO = 37, 70
POLIGONO, PARCELA, RECINTO = 503, 51, 1
CODIGO_INE = "37070"
MUNICIPIO_NOMBRE = "Calvarrasa de Arriba"

# Un cuadrado de un grado de lado, en Salamanca. Se redondea a cuatro decimales para que el WKT que
# se espera se pueda escribir a mano y se vea a simple vista si el lector cambia algo.
ANILLO = [(-5.5, 40.9), (-5.49, 40.9), (-5.49, 40.91), (-5.5, 40.91), (-5.5, 40.9)]
WKT_ESPERADO = (
    "POLYGON(("
    "-5.5000000 40.9000000,-5.4900000 40.9000000,-5.4900000 40.9100000,"
    "-5.5000000 40.9100000,-5.5000000 40.9000000))"
)


# --------------------------------------------------------------------------- los blobs, a mano


def _wkb_de_un_poligono(anillos, *, tipo=3):
    """El WKB de un polígono (o de una geometría del tipo que se diga), little endian."""
    trozos = [struct.pack("<B", 1), struct.pack("<I", tipo), struct.pack("<I", len(anillos))]
    for anillo in anillos:
        trozos.append(struct.pack("<I", len(anillo)))
        for x, y in anillo:
            trozos.append(struct.pack("<dd", x, y))
    return b"".join(trozos)


def _blob(geometria: bytes, *, srs=4258, envolvente=True, vacia=False):
    """La cabecera del GeoPackage delante del WKB, que es como lo guarda el fichero.

    `GP`, versión, banderas (bit 0 = little endian, bits 1-3 = envolvente, bit 4 = vacía), `srs_id` y,
    si la lleva, la envolvente de cuatro dobles.
    """
    banderas = 0x01
    if envolvente:
        banderas |= 1 << 1
    if vacia:
        banderas |= 0x10
    cabecera = b"GP" + bytes([0, banderas]) + struct.pack("<i", srs)
    if envolvente and not vacia:
        xs = [x for x, _ in ANILLO]
        ys = [y for _, y in ANILLO]
        cabecera += struct.pack("<4d", min(xs), min(ys), max(xs), max(ys))
    return cabecera + (b"" if vacia else geometria)


def _blob_multi(poligonos, *, srs=4258):
    """El blob de un MultiPolygon, con cada polígono con su propia cabecera de WKB."""
    partes = [struct.pack("<B", 1), struct.pack("<I", 6), struct.pack("<I", len(poligonos))]
    for poligono in poligonos:
        partes.append(_wkb_de_un_poligono(poligono))
    return _blob(b"".join(partes), srs=srs, envolvente=False)


# --------------------------------------------------------------------------- el gpkg sintético


def _un_gpkg(
    ruta,
    filas,
    *,
    tabla="recintos",
    columna="geom",
    sin_columnas=(),
    una_geometria=False,
    srs=4258,
    nombres=None,
    fila_superficie=None,
):
    """Fabrica un GeoPackage con su tabla de geometrías y las filas que se le digan.

    `sin_columnas` quita columnas a la tabla (para probar que un esquema desconocido se dice),
    `una_geometria` declara en `gpkg_geometry_columns` un tipo distinto de POLYGON, `srs` es el
    sistema de coordenadas **declarado en el fichero** (el que manda) y `nombres` permite escribir
    las columnas con el nombre de verdad del SIGPAC (`dn_surface`, `csp`…). `fila_superficie` cambia
    el número de la superficie de todas las filas (para probar la unidad).
    """
    columnas = {
        "provincia": "INTEGER",
        "municipio": "INTEGER",
        "agregado": "INTEGER",
        "zona": "INTEGER",
        "poligono": "INTEGER",
        "parcela": "INTEGER",
        "recinto": "INTEGER",
        "uso_sigpac": "TEXT",
        "coef_regadio": "REAL",
        "region": "INTEGER",
        "admisibilidad": "REAL",
        "superficie": "REAL",
    }
    for fuera in sin_columnas:
        columnas.pop(fuera, None)
    reales = {clave: (nombres or {}).get(clave, clave) for clave in columnas}
    definicion = ", ".join(f'"{reales[clave]}" {tipo}' for clave, tipo in columnas.items())
    conexion = sqlite3.connect(ruta)
    try:
        conexion.execute(
            "CREATE TABLE gpkg_geometry_columns (table_name TEXT, column_name TEXT, "
            "geometry_type_name TEXT, srs_id INTEGER, z INTEGER, m INTEGER)"
        )
        conexion.execute(
            f'CREATE TABLE "{tabla}" (fid INTEGER PRIMARY KEY, {definicion}, "{columna}" BLOB)'
        )
        conexion.execute(
            "INSERT INTO gpkg_geometry_columns VALUES (?, ?, ?, ?, 0, 0)",
            (tabla, columna, "POINT" if una_geometria else "POLYGON", srs),
        )
        for fila in filas:
            if fila_superficie is not None:
                fila = {**fila, "superficie": fila_superficie}
            nombres_reales = [reales[clave] for clave in columnas if clave in fila]
            huecos = ", ".join("?" for _ in nombres_reales)
            conexion.execute(
                f'INSERT INTO "{tabla}" ({", ".join(nombres_reales)}, "{columna}") '
                f"VALUES ({huecos}, ?)",
                [fila[clave] for clave in columnas if clave in fila] + [fila.get("geom")],
            )
        conexion.commit()
    finally:
        conexion.close()
    return ruta


def _una_fila(**cambios):
    fila = {
        "provincia": PROVINCIA,
        "municipio": MUNICIPIO,
        "agregado": 0,
        "zona": 0,
        "poligono": POLIGONO,
        "parcela": PARCELA,
        "recinto": RECINTO,
        "uso_sigpac": "TA",
        "coef_regadio": 0.0,
        "region": 2,
        "admisibilidad": None,
        "superficie": 4.9016,
        "geom": _blob(_wkb_de_un_poligono([ANILLO])),
    }
    fila.update(cambios)
    return fila


# --------------------------------------------------------------------------- leer el fichero


def test_lee_los_atributos_y_la_geometria_de_un_recinto(tmp_path):
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila()])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        encontrados = lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)

    assert len(encontrados) == 1
    recinto = encontrados[0]
    assert (recinto["provincia"], recinto["municipio"]) == (PROVINCIA, MUNICIPIO)
    assert (recinto["poligono"], recinto["parcela"], recinto["recinto"]) == (POLIGONO, PARCELA, RECINTO)
    assert recinto["uso_sigpac"] == "TA"
    assert recinto["region"] == 2
    assert recinto["superficie_ha"] == 4.9016
    assert recinto["wkt"] == WKT_ESPERADO
    assert recinto["puntos"] == [[x, y] for x, y in ANILLO]
    assert len(recinto["anillos"]) == 1 and len(recinto["anillos"][0]) == 5


def test_el_anillo_va_en_longitud_latitud(tmp_path):
    """El primer número es la longitud y el segundo la latitud: al revés, el mapa sale en otro sitio."""
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila()])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        recinto = lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)[0]
    longitud, latitud = recinto["puntos"][0]
    assert round(longitud, 2) == -5.5  # Salamanca está al oeste de Greenwich
    assert round(latitud, 2) == 40.9


def test_filtra_por_los_codigos(tmp_path):
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila(), _una_fila(recinto=2)])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        assert len(lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)) == 1
        assert len(lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA)) == 2
        assert lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, 999) == []
        assert lector.buscar(99, MUNICIPIO, POLIGONO, PARCELA) == []


def test_un_multipolygon_tambien_se_lee(tmp_path):
    """Un recinto partido en dos trozos viene como MultiPolygon: se lee entero y sin perder ninguno."""
    otro = [(-5.4, 40.8), (-5.39, 40.8), (-5.39, 40.81), (-5.4, 40.81), (-5.4, 40.8)]
    ruta = _un_gpkg(
        tmp_path / "mapa.gpkg",
        [_una_fila(geom=_blob_multi([[ANILLO], [otro]]))],
    )
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        recinto = lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)[0]

    assert recinto["wkt"].startswith("MULTIPOLYGON(")
    assert len(recinto["anillos"]) == 2
    assert recinto["puntos"] == [[x, y] for x, y in ANILLO]


def test_un_recinto_sin_forma_no_se_inventa(tmp_path):
    """Blob vacío (bandera de «geometría vacía»): se dice que no hay forma, no se pone un cuadro."""
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila(geom=_blob(b"", vacia=True))])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        recinto = lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)[0]
    assert recinto["wkt"] is None
    assert recinto["puntos"] is None


# --------------------------------------------------------------------------- lo que no se sabe


def test_una_columna_imprescindible_que_falta_se_dice(tmp_path):
    """Sin la columna `parcela` no se sabe con qué casar el recinto: error claro, no adivinar."""
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [], sin_columnas=("parcela",))
    with pytest.raises(geopackage_sigpac.GeopackageDesconocido) as problema:
        with geopackage_sigpac.abrir_recintos(ruta):
            pass
    assert "parcela" in str(problema.value)


def test_un_tipo_de_geometria_que_no_se_lee_se_dice(tmp_path):
    """Un punto no es una superficie: se dice qué tipo viene en vez de devolver algo parecido."""
    punto = struct.pack("<B", 1) + struct.pack("<I", 1) + struct.pack("<dd", -5.5, 40.9)
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila(geom=_blob(punto))])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        with pytest.raises(geopackage_sigpac.GeopackageDesconocido) as problema:
            lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)
    assert "tipo 1" in str(problema.value)


def test_una_geometria_con_altura_se_rechaza_en_vez_de_leerse_mal(tmp_path):
    """Un polígono con Z lleva tres números por punto: leerlo como plano daría coordenadas falsas."""
    con_z = _wkb_de_un_poligono([ANILLO], tipo=1003)
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila(geom=_blob(con_z))])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        with pytest.raises(geopackage_sigpac.GeopackageDesconocido) as problema:
            lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)
    assert "altura" in str(problema.value)


def test_un_fichero_que_no_es_un_geopackage_se_dice(tmp_path):
    ruta = tmp_path / "cualquiera.gpkg"
    ruta.write_bytes(b"esto no es un sqlite")
    with pytest.raises(geopackage_sigpac.GeopackageDesconocido):
        with geopackage_sigpac.abrir_recintos(ruta):
            pass


def test_otro_sistema_de_coordenadas_se_rechaza(tmp_path):
    """Si el mapa no viene en longitud/latitud, no se guardan coordenadas que el mapa no leería."""
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila(geom=_blob(_wkb_de_un_poligono([ANILLO]), srs=25830))])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        with pytest.raises(geopackage_sigpac.GeopackageDesconocido) as problema:
            lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)
    assert "25830" in str(problema.value)


def test_un_blob_que_no_dice_su_sistema_usa_el_que_declara_el_fichero(tmp_path):
    """**El caso del fichero de verdad del SIGPAC**: el blob dice `srs_id` 0 y el sistema está en
    `gpkg_geometry_columns`. Antes se rechazaba el mapa entero por eso."""
    ruta = _un_gpkg(
        tmp_path / "mapa.gpkg",
        [_una_fila(geom=_blob(_wkb_de_un_poligono([ANILLO]), srs=0))],
        srs=4258,
    )
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        recinto = lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)[0]
    assert recinto["wkt"] == WKT_ESPERADO


def test_si_el_fichero_declara_otro_sistema_se_rechaza(tmp_path):
    """Y si el que declara el fichero no es longitud/latitud, se dice aunque el blob calle."""
    ruta = _un_gpkg(
        tmp_path / "mapa.gpkg",
        [_una_fila(geom=_blob(_wkb_de_un_poligono([ANILLO]), srs=0))],
        srs=25830,
    )
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        with pytest.raises(geopackage_sigpac.GeopackageDesconocido) as problema:
            lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)
    assert "25830" in str(problema.value)


def test_si_nadie_dice_el_sistema_no_se_adivina(tmp_path):
    """Ni el blob ni el fichero: no se puede saber si son grados. Se dice en vez de suponerlo."""
    ruta = _un_gpkg(
        tmp_path / "mapa.gpkg",
        [_una_fila(geom=_blob(_wkb_de_un_poligono([ANILLO]), srs=0))],
        srs=0,
    )
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        with pytest.raises(geopackage_sigpac.GeopackageDesconocido):
            lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)


def test_las_columnas_del_fichero_de_verdad_se_encuentran(tmp_path):
    """El GeoPackage del SIGPAC llama `recinto` a la tabla, `dn_geom` a la geometría, `dn_surface` a
    la superficie y `csp` al coeficiente de subvencionabilidad. Si no se reconocen esos nombres, la
    superficie y el CSP llegan vacíos sin que nadie se entere."""
    ruta = _un_gpkg(
        tmp_path / "real.gpkg",
        [_una_fila()],
        tabla="recinto",
        columna="dn_geom",
        nombres={"superficie": "dn_surface", "admisibilidad": "csp"},
        fila_superficie=49015.5907,  # metros cuadrados, como los escribe el fichero de verdad
    )
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        assert lector.tabla == "recinto" and lector.columna == "dn_geom"
        recinto = lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)[0]
    # **Y la superficie viene en metros cuadrados**: 49.015,59 m² son 4,9016 ha, no 49.015 ha.
    assert recinto["superficie_ha"] == 4.9016
    assert recinto["admisibilidad"] is None  # el ejemplo trae nulo y se queda nulo


def test_una_superficie_ya_en_hectareas_no_se_convierte(tmp_path):
    """Si la columna se llama `superficie` (o `superficie_ha`), el número ya viene en hectáreas.

    La conversión depende del nombre de la columna **a propósito**: el fichero del SIGPAC no dice en
    qué unidad está, y dividir por 10.000 una cifra que ya venía en hectáreas dejaría la parcela
    10.000 veces más pequeña.
    """
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila(superficie=4.9016)])
    with geopackage_sigpac.abrir_recintos(ruta) as lector:
        recinto = lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)[0]
    assert recinto["superficie_ha"] == 4.9016


# --------------------------------------------------------------------------- el ZIP y su caché


def _un_zip_con_mapa(tmp_path, *, filas=None, nombre=None):
    """Fabrica el ZIP **como lo deja la caché**: el `.gpkg` dentro, con su nombre oficial."""
    filas = [_una_fila()] if filas is None else filas
    gpkg = tmp_path / "para_el_zip.gpkg"
    gpkg.unlink(missing_ok=True)  # se fabrica de cero cada vez (si no, las tablas ya están)
    gpkg = _un_gpkg(gpkg, filas)
    ruta_zip = tmp_path / (nombre or "37_SALAMANCA_rec_2026_20251215_gpkg.zip")
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.write(gpkg, arcname=MIEMBRO)
    return ruta_zip


def _el_guardado_de(ruta_zip):
    """Dónde tiene que quedar el `.gpkg` sacado (la misma regla que usa el lector)."""
    return geopackage_sigpac._la_ruta_del_gpkg_guardado(ruta_zip, MIEMBRO)


def _buscar_aqui(lector):
    return lector.buscar(PROVINCIA, MUNICIPIO, POLIGONO, PARCELA, RECINTO)


def test_la_primera_apertura_deja_el_mapa_sacado_junto_al_zip(tmp_path):
    """**Antes se descomprimía 1 GB en cada llamada.** Ahora la primera vez se saca al lado del ZIP."""
    ruta_zip = _un_zip_con_mapa(tmp_path)
    guardado = _el_guardado_de(ruta_zip)
    assert not guardado.exists(), "de entrada no hay nada sacado"

    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        assert lector.cacheado is False, "esta primera vez se acaba de sacar"
        assert _buscar_aqui(lector)[0]["wkt"] == WKT_ESPERADO

    assert guardado.is_file(), "el mapa tiene que quedar sacado para la próxima"
    assert guardado.stat().st_size > 0
    assert not list(tmp_path.glob(".*extrayendo")), "no puede quedar un temporal a medias"


def test_la_segunda_apertura_no_vuelve_a_descomprimir(tmp_path, monkeypatch):
    """La segunda vez **se abre el `.gpkg` guardado**: ni se descomprime ni se reescribe."""
    ruta_zip = _un_zip_con_mapa(tmp_path)
    with geopackage_sigpac.abrir_recintos(ruta_zip):
        pass
    guardado = _el_guardado_de(ruta_zip)
    antes = guardado.stat().st_mtime_ns

    def _no_se_debe_descomprimir(*args, **kwargs):
        raise AssertionError("ha vuelto a descomprimir el ZIP en la segunda apertura")

    monkeypatch.setattr(geopackage_sigpac, "_extraer_al_lado", _no_se_debe_descomprimir)
    monkeypatch.setattr(geopackage_sigpac, "_sacar_al_temporal", _no_se_debe_descomprimir)

    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        assert lector.cacheado is True
        assert _buscar_aqui(lector)[0]["wkt"] == WKT_ESPERADO
    assert guardado.stat().st_mtime_ns == antes, "el guardado no se ha tocado"


def test_si_el_zip_cambia_se_vuelve_a_sacar(tmp_path):
    """Mapa nuevo encima del mismo nombre: el ZIP es más nuevo y el guardado deja de valer."""
    ruta_zip = _un_zip_con_mapa(tmp_path, filas=[_una_fila()])
    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        assert _buscar_aqui(lector)[0]["uso_sigpac"] == "TA"
    guardado = _el_guardado_de(ruta_zip)
    antes = guardado.stat().st_mtime_ns

    # El mismo ZIP, con otro contenido y con la fecha delante (como una descarga nueva).
    _un_zip_con_mapa(tmp_path, filas=[_una_fila(uso_sigpac="PA")])
    futuro = time.time() + 60
    os.utime(ruta_zip, (futuro, futuro))

    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        assert _buscar_aqui(lector)[0]["uso_sigpac"] == "PA", "se ha abierto el mapa viejo"
    assert guardado.stat().st_mtime_ns != antes, "el guardado se ha vuelto a sacar"


def test_un_mapa_guardado_cortado_se_vuelve_a_sacar(tmp_path):
    """Un apagón a mitad de la extracción deja un `.gpkg` cortado: se tira y se saca otra vez."""
    ruta_zip = _un_zip_con_mapa(tmp_path)
    with geopackage_sigpac.abrir_recintos(ruta_zip):
        pass
    guardado = _el_guardado_de(ruta_zip)
    guardado.write_bytes(b"GP")  # cortado: el tamaño no cuadra con el del ZIP

    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        assert _buscar_aqui(lector)[0]["wkt"] == WKT_ESPERADO
    assert guardado.stat().st_size > 2, "y queda uno bueno para la próxima"


def test_un_mapa_guardado_ilegible_se_vuelve_a_sacar(tmp_path):
    """Con el tamaño correcto pero basura dentro, el que lo delata es sqlite: también se recupera."""
    ruta_zip = _un_zip_con_mapa(tmp_path)
    with geopackage_sigpac.abrir_recintos(ruta_zip):
        pass
    guardado = _el_guardado_de(ruta_zip)
    guardado.write_bytes(b"\x00" * guardado.stat().st_size)

    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        # El tamaño no lo delataba, así que se ha tenido que volver a descomprimir.
        assert lector.cacheado is False
        assert _buscar_aqui(lector)[0]["wkt"] == WKT_ESPERADO

    # Y el que ha quedado ya sí sirve: la siguiente apertura no descomprime.
    with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
        assert lector.cacheado is True
        assert _buscar_aqui(lector)[0]["wkt"] == WKT_ESPERADO


def test_si_la_carpeta_no_se_puede_escribir_sigue_funcionando(tmp_path, monkeypatch):
    """**No se rompe por no poder cachear**: se saca al temporal de siempre y se dice (`cacheado`)."""

    def _sin_permiso(*args, **kwargs):
        raise PermissionError("la carpeta del mapa es de solo lectura")

    ruta_zip = _un_zip_con_mapa(tmp_path)
    monkeypatch.setattr(geopackage_sigpac, "_extraer_al_lado", _sin_permiso)

    for _ in range(2):  # y la segunda tampoco falla, aunque vuelva a descomprimir
        with geopackage_sigpac.abrir_recintos(ruta_zip) as lector:
            assert lector.cacheado is False
            assert _buscar_aqui(lector)[0]["wkt"] == WKT_ESPERADO
    assert not _el_guardado_de(ruta_zip).exists(), "no se ha dejado nada escrito al lado del ZIP"


def test_un_zip_que_no_lleva_mapa_dentro_se_dice(tmp_path):
    ruta_zip = tmp_path / "sin_mapa.zip"
    with zipfile.ZipFile(ruta_zip, "w") as paquete:
        paquete.writestr("leeme.txt", "aquí no hay ningún mapa")
    with pytest.raises(geopackage_sigpac.GeopackageDesconocido) as problema:
        with geopackage_sigpac.abrir_recintos(ruta_zip):
            pass
    assert "ningún mapa" in str(problema.value)


# --------------------------------------------------------------------------- los contornos


def _una_parcela_de_mentira(**cambios):
    datos = {
        "id": 1,
        "alias": "El Prado",
        "ref_sigpac": "37-70-0-0-503-51-1",
        "codigo_ine": CODIGO_INE,
        "provincia": "Salamanca",
        "municipio": MUNICIPIO_NOMBRE,
        "poligono": POLIGONO,
        "numero_parcela": PARCELA,
        "numero_recinto": RECINTO,
    }
    datos.update(cambios)
    return SimpleNamespace(**datos)


def test_contornos_de_las_parcelas_casa_la_que_esta_y_dice_la_que_no(tmp_path):
    ruta = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila()])
    resultado = geopackage_sigpac.contornos_de_las_parcelas(
        [
            _una_parcela_de_mentira(),
            _una_parcela_de_mentira(id=2, alias="La Era", numero_recinto=2),
            _una_parcela_de_mentira(id=3, alias="Sin pueblo", municipio="PUEBLO QUE NO EXISTE", codigo_ine=None),
        ],
        ruta,
    )

    assert resultado["n"] == 3
    assert [una["id"] for una in resultado["actualizadas"]] == [1]
    assert resultado["actualizadas"][0]["wkt"] == WKT_ESPERADO
    # El recinto 2 no está en el mapa: se dice, no se busca «el más parecido».
    assert [una["id"] for una in resultado["no_encontradas"]] == [2]
    # Y el pueblo que no está en el catálogo se cuenta aparte: no se adivina un código.
    assert [una["id"] for una in resultado["sin_codigos"]] == [3]


def test_el_nombre_del_municipio_se_casa_con_su_codigo():
    """El nombre viene escrito por el agricultor o por el cuaderno: se casa con el catálogo oficial."""
    codigos = geopackage_sigpac.codigos_de_una_parcela(
        _una_parcela_de_mentira(codigo_ine=None)
    )
    assert codigos == (PROVINCIA, MUNICIPIO)


# --------------------------------------------------------------------------- la puerta


def _en_la_cache(carpeta, gpkg, *, campana=2026):
    """Deja el ZIP y su ficha en la caché, como los deja la descarga de verdad."""
    nombre = f"37_SALAMANCA_rec_{campana}_20251215_gpkg.zip"
    with zipfile.ZipFile(carpeta / nombre, "w") as paquete:
        paquete.write(gpkg, arcname="37_SALAMANCA_recintos.gpkg")
    ficha = {
        "provincia": PROVINCIA,
        "nombre_provincia": "SALAMANCA",
        "campana": campana,
        "fecha_validez": "2025-12-15",
        "fichero": nombre,
        "bytes": (carpeta / nombre).stat().st_size,
        "sha256": "0" * 64,
        "url": "https://sigpac-hubcloud.es/geopackage.zip",
        "licencia": "CC BY 4.0 — FEGA",
        "atribucion": "Fuente: FEGA",
        "descargado_en": "2026-11-05T00:00:00+00:00",
    }
    (carpeta / f"{PROVINCIA}_{campana}.json").write_text(json.dumps(ficha), encoding="utf-8")
    return ficha


@pytest.fixture
def cache_con_mapa(tmp_path, monkeypatch):
    carpeta = tmp_path / "sigpac_cache"
    carpeta.mkdir()
    monkeypatch.setenv("CUEDIGITAL_SIGPAC_CACHE", str(carpeta))
    gpkg = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila()])
    _en_la_cache(carpeta, gpkg)
    return carpeta


def _la_tierra(crear_parcela, **cambios):
    datos = {
        "alias": "El Prado",
        "superficie_ha": 4.0,
        "provincia": "Salamanca",
        "municipio": MUNICIPIO_NOMBRE,
        "codigo_ine": CODIGO_INE,
        "poligono": POLIGONO,
        "numero_parcela": PARCELA,
        "numero_recinto": RECINTO,
    }
    datos.update(cambios)
    return crear_parcela(**datos)


def _los_contornos(cliente, cabeceras, **cambios):
    return cliente.post(
        f"/api/sigpac/cache/{PROVINCIA}/contornos", headers=cabeceras, params=cambios
    )


def test_la_puerta_rellena_la_geometria_y_el_dibujo(cliente, cuenta, crear_parcela, db_sesion, cache_con_mapa):
    tierra = _la_tierra(crear_parcela)
    respuesta = _los_contornos(cliente, cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert [una["id"] for una in datos["actualizadas"]] == [tierra["id"]]
    assert datos["actualizadas"][0]["wkt"] == WKT_ESPERADO
    assert datos["n"] == 1

    db_sesion.expire_all()
    from app import models

    parcela = db_sesion.get(models.Parcela, tierra["id"])
    assert parcela.geometria == WKT_ESPERADO
    # El dibujo no se guarda: se calcula del WKT, y por eso ahora ya se puede pintar.
    assert parcela.dibujo is not None
    assert parcela.dibujo.startswith("M")


def test_repetirlo_no_rompe_nada(cliente, cuenta, crear_parcela, db_sesion, cache_con_mapa):
    """Idempotente: la segunda vez la forma es la misma y no se duplica nada."""
    tierra = _la_tierra(crear_parcela)
    primera = _los_contornos(cliente, cuenta["cabeceras"]).json()
    segunda = _los_contornos(cliente, cuenta["cabeceras"]).json()

    assert primera == segunda
    db_sesion.expire_all()
    from app import models

    assert db_sesion.get(models.Parcela, tierra["id"]).geometria == WKT_ESPERADO


def test_las_parcelas_que_no_estan_se_dicen_en_la_respuesta(cliente, cuenta, crear_parcela, cache_con_mapa):
    _la_tierra(crear_parcela, alias="La Era", numero_recinto=2)
    datos = _los_contornos(cliente, cuenta["cabeceras"]).json()

    assert datos["actualizadas"] == []
    assert [una["alias"] for una in datos["no_encontradas"]] == ["La Era"]


def test_sin_sesion_no_se_abre_nada(cliente, cache_con_mapa):
    respuesta = cliente.post(f"/api/sigpac/cache/{PROVINCIA}/contornos")
    assert respuesta.status_code == 401, respuesta.text


def test_sin_permiso_de_modificar_contesta_403_antes_de_abrir_el_mapa(
    cliente, cuenta, db_sesion, tmp_path, monkeypatch
):
    """**403 y antes de mirar el fichero**: no hay caché ninguna y aun así contesta 403.

    Si el orden estuviera al revés, esta prueba recibiría un 404 de «no está descargado».
    """
    monkeypatch.setenv("CUEDIGITAL_SIGPAC_CACHE", str(tmp_path / "vacia"))
    _sin_capacidad(db_sesion, cuenta, "puede_modificar")
    respuesta = _los_contornos(cliente, cuenta["cabeceras"])
    assert respuesta.status_code == 403, respuesta.text


def test_sin_el_mapa_descargado_contesta_404(cliente, cuenta, tmp_path, monkeypatch):
    monkeypatch.setenv("CUEDIGITAL_SIGPAC_CACHE", str(tmp_path / "vacia"))
    respuesta = _los_contornos(cliente, cuenta["cabeceras"])
    assert respuesta.status_code == 404, respuesta.text
    assert "no está descargado" in respuesta.json()["detail"]


def test_la_ficha_sin_el_fichero_contesta_409(cliente, cuenta, tmp_path, monkeypatch):
    """La ficha está pero el ZIP ya no: se dice, no se trata como si nunca se hubiera descargado."""
    carpeta = tmp_path / "sigpac_cache"
    carpeta.mkdir()
    monkeypatch.setenv("CUEDIGITAL_SIGPAC_CACHE", str(carpeta))
    gpkg = _un_gpkg(tmp_path / "mapa.gpkg", [_una_fila()])
    ficha = _en_la_cache(carpeta, gpkg)
    (carpeta / ficha["fichero"]).unlink()

    respuesta = _los_contornos(cliente, cuenta["cabeceras"])
    assert respuesta.status_code == 409, respuesta.text


def test_un_mapa_que_no_se_entiende_contesta_422(cliente, cuenta, tmp_path, monkeypatch):
    """El fichero está, pero no es el GeoPackage que se espera: 422 con el motivo, sin escribir nada."""
    carpeta = tmp_path / "sigpac_cache"
    carpeta.mkdir()
    monkeypatch.setenv("CUEDIGITAL_SIGPAC_CACHE", str(carpeta))
    malo = _un_gpkg(tmp_path / "malo.gpkg", [], sin_columnas=("recinto",))
    _en_la_cache(carpeta, malo)

    respuesta = _los_contornos(cliente, cuenta["cabeceras"])
    assert respuesta.status_code == 422, respuesta.text
    assert "recinto" in respuesta.json()["detail"]


def test_la_parcela_de_otra_finca_no_se_toca(
    cliente, cuenta, crear_parcela, crear_cuenta, db_sesion, cache_con_mapa
):
    """Aislamiento: la misma referencia, en dos fincas; el mapa rellena la de quien lo pide y la otra no."""
    mia = _la_tierra(crear_parcela)
    otro = crear_cuenta("otro@ejemplo.test")
    suya = cliente.post(
        "/api/parcelas",
        headers=otro["cabeceras"],
        json={
            "alias": "La del vecino",
            "superficie_ha": 4.0,
            "provincia": "Salamanca",
            "municipio": MUNICIPIO_NOMBRE,
            "codigo_ine": CODIGO_INE,
            "poligono": POLIGONO,
            "numero_parcela": PARCELA,
            "numero_recinto": RECINTO,
        },
    )
    assert suya.status_code == 201, suya.text

    respuesta = _los_contornos(cliente, cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    assert [una["id"] for una in respuesta.json()["actualizadas"]] == [mia["id"]]

    db_sesion.expire_all()
    from app import models

    assert db_sesion.get(models.Parcela, mia["id"]).geometria == WKT_ESPERADO
    assert db_sesion.get(models.Parcela, suya.json()["id"]).geometria is None
