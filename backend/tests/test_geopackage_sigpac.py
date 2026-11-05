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
import sqlite3
import struct
import zipfile
from types import SimpleNamespace

import pytest

from app import geopackage_sigpac
from test_los_permisos_por_materia import _sin_capacidad  # noqa: E402 — el andamiaje, prestado

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


def _un_gpkg(ruta, filas, *, tabla="recintos", columna="geom", sin_columnas=(), una_geometria=False):
    """Fabrica un GeoPackage con su tabla de geometrías y las filas que se le digan.

    `sin_columnas` quita columnas a la tabla (para probar que un esquema desconocido se dice) y
    `una_geometria` declara en `gpkg_geometry_columns` un tipo distinto de POLYGON.
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
    definicion = ", ".join(f"{nombre} {tipo}" for nombre, tipo in columnas.items())
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
            (tabla, columna, "POINT" if una_geometria else "POLYGON", 4258),
        )
        for fila in filas:
            nombres = [nombre for nombre in columnas if nombre in fila]
            huecos = ", ".join("?" for _ in nombres)
            conexion.execute(
                f'INSERT INTO "{tabla}" ({", ".join(nombres)}, "{columna}") '
                f"VALUES ({huecos}, ?)",
                [fila[nombre] for nombre in nombres] + [fila.get("geom")],
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
