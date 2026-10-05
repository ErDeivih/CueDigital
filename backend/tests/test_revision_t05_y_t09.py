"""Revisión independiente de T05 (versiones del recinto) y T09 (el almacén).

## Qué es este fichero

No es la suite de las dos entregas: es la **revisión** de las dos entregas. El encargo era
intentar **demostrar que están mal**, contrato por contrato, provocándolo con el cliente de
pruebas de FastAPI sobre bases temporales (`conftest.py` fija `CUEDIGITAL_DATABASE_URL` a una
carpeta temporal antes de importar nada de `app`, así que la base del agricultor **no se abre**).

Cada clase de aquí abajo es **un contrato del encargo**, y el nombre de cada prueba dice qué
contrato protege, para que se pueda arreglar el defecto sin tener que releer este fichero:

  1. `Test1UnDatoAusenteNoEsCeroNiCumple` — un dato que no se sabe no puede acabar valiendo 0 ni
     leyéndose como «todo bien».
  2. `Test2NoSeDuplicanLasExistencias` — la misma mercancía no entra dos veces.
  3. `Test3ElTotalYLaDosisVanCadaUnoConSuNombre` — la cantidad total no es la dosis por hectárea, y
     los litros no son los kilos.
  4. `Test4NingunaRutaDevuelveDatosDeOtraFinca` — 404 y no 403.
  5. `Test5LaImportacionDeRecintosEsIdempotente`.
  6. `Test6CompararNoEscribeNada`.
  7. `Test7PrevisualizarNoEscribeNada`.
  8. `Test8LasHectareasDeclaradasNoSeSustituyen`.
  9. `Test9UnRecintoSinGeometriaEntraYLoDice`.
 10. `Test10LaMedidaDelAreaEsLaQueEs`.
 11. `Test11LosTextosVivenEnTextosPyNoLlevanJerga`.
 12. `Test12LasFirmasYLaAuditoriaSiguenIntactas`.

Las pruebas están escritas para **fallar mientras el defecto exista**: las que fallan hoy están
apuntadas en `docs/REVISION_T05_Y_T09.md`, con el fichero y la línea del código que hay que
mirar. Ninguna se ha escrito para «pasar de todas formas».
"""

from __future__ import annotations

import datetime as dt
import json
import math
import pathlib
import re

import pytest
from sqlalchemy import select

from app import geo, models, textos
from app import versiones_de_recinto as versiones

RAIZ = pathlib.Path(__file__).resolve().parents[2]
RUTA_SIGPAC = RAIZ / "data" / "sigpac"
PANTALLAS = RAIZ / "backend" / "web" / "react" / "pantallas"

# Las seis pantallas nuevas de T09. Todo el texto que enseñan sale de `textos.CESTA` (el bloque del
# almacén, que sí se sirve y que el móvil se guarda), así que se puede comprobar por su nombre.
PANTALLAS_DEL_ALMACEN = (
    "libro_del_almacen.js",
    "nuevo_albaran.js",
    "recepcion.js",
    "movimiento_de_almacen.js",
    "sacar_de_un_lote.js",
    "enganchar_la_factura.js",
)

REFERENCIA_1 = "37-70-0-0-503-51-1"
REFERENCIA_2 = "37-70-0-0-503-51-2"

# Un cuadrado de unos 100 m de lado (0,93 ha medidas por el programa), que es el trozo con el que
# trabaja media suite de T05.
CUADRADO_100_M = "POLYGON((-5.0 41.0,-4.999 41.0,-4.999 41.001,-5.0 41.001,-5.0 41.0))"


# --------------------------------------------------------------------------
# Formas de verdad, para medir el área contra un número que se sabe
# --------------------------------------------------------------------------


def _anillo(lon0: float, lat0: float, lado_m: float) -> list[tuple[float, float]]:
    """Los vértices de un cuadrado de `lado_m` metros apoyado en (lon0, lat0).

    El lado se pasa de metros a grados con la misma corrección que usa el programa (un grado de
    longitud, corregido por el coseno de la latitud). Así el cuadrado **mide lo que dice medir** y
    el área que tiene que salir se puede escribir a mano: `lado_m² / 10.000` hectáreas.
    """
    dlat = math.degrees(lado_m / geo.RADIO_TIERRA_M)
    lat_media = lat0 + dlat / 2
    dlon = math.degrees(lado_m / (geo.RADIO_TIERRA_M * math.cos(math.radians(lat_media))))
    return [
        (lon0, lat0),
        (lon0 + dlon, lat0),
        (lon0 + dlon, lat0 + dlat),
        (lon0, lat0 + dlat),
        (lon0, lat0),
    ]


def _wkt(puntos: list[tuple[float, float]]) -> str:
    return ",".join(f"{x} {y}" for x, y in puntos)


def _poligono(*anillos: list[tuple[float, float]]) -> str:
    return "POLYGON((" + "),(".join(_wkt(anillo) for anillo in anillos) + "))"


def _multipoligono(*trozos: list[list[tuple[float, float]]]) -> str:
    return "MULTIPOLYGON((" + "),(".join(
        "),(".join(_wkt(anillo) for anillo in trozo) for trozo in trozos
    ) + "))"


# --------------------------------------------------------------------------
# Herramientas del lote de recintos (T05)
# --------------------------------------------------------------------------


def _recinto(numero: int = 1, **cambios) -> dict:
    datos = {
        "provincia": "37",
        "municipio": "70",
        "agregado": 0,
        "zona": 0,
        "poligono": 503,
        "numero_parcela": 51,
        "numero_recinto": numero,
    }
    datos.update(cambios)
    return datos


def _lote(campana: dict, recintos: list[dict], fuente: str = "sigpac", **cambios) -> dict:
    lote = {"campana_id": campana["id"], "fuente": fuente, "recintos": recintos}
    lote.update(cambios)
    return lote


def _previsualizar(cliente, cabeceras, lote) -> dict:
    respuesta = cliente.post("/api/versiones/previsualizar", headers=cabeceras, json=lote)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _aplicar(cliente, cabeceras, lote) -> dict:
    respuesta = cliente.post("/api/versiones/aplicar", headers=cabeceras, json=lote)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _versiones(cliente, cabeceras, **parametros) -> list[dict]:
    respuesta = cliente.get("/api/versiones", headers=cabeceras, params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _foto_de_las_versiones(db_sesion) -> list[dict]:
    filas = db_sesion.scalars(
        select(models.VersionDeRecinto).order_by(models.VersionDeRecinto.id)
    ).all()
    columnas = (
        "id",
        "parcela_id",
        "campana_id",
        "fuente",
        "fecha_consulta",
        "clave",
        "referencia",
        "poligono_valido",
        "geometria",
        "area_geometria_ha",
        "area_sigpac_ha",
        "area_declarada_ha",
        "uso_sigpac",
        "pendiente_pct",
        "estado_revision",
    )
    return [{columna: getattr(fila, columna) for columna in columnas} for fila in filas]


def _foto_de_las_tierras(db_sesion) -> list[dict]:
    tierras = db_sesion.scalars(select(models.Parcela).order_by(models.Parcela.id)).all()
    columnas = (
        "id",
        "alias",
        "ref_sigpac",
        "superficie_ha",
        "superficie_sigpac_ha",
        "geometria",
        "agregado",
        "zona",
        "poligono",
        "numero_parcela",
        "numero_recinto",
    )
    return [{columna: getattr(tierra, columna) for columna in columnas} for tierra in tierras]


def _la_auditoria(db_sesion) -> list[tuple]:
    return [
        (apunte.entidad, apunte.accion, apunte.entidad_id)
        for apunte in db_sesion.scalars(
            select(models.Auditoria).order_by(models.Auditoria.id)
        ).all()
    ]


def _foto_completa(db_sesion) -> dict:
    """Todo lo que estas dos entregas podrían escribir, junto, para compararlo antes y después."""
    return {
        "versiones": _foto_de_las_versiones(db_sesion),
        "tierras": _foto_de_las_tierras(db_sesion),
        "auditoria": _la_auditoria(db_sesion),
    }


def _las_filas_de(motor, tablas: tuple) -> dict:
    """Todas las filas de esas tablas, tal cual, ordenadas.

    Se usa para comprobar que una operación sobre el **esquema** (tirar y volver a crear un índice)
    no toca ni una fila de los **datos**. Va por el driver y sin modelo de por medio a propósito: lo
    que se compara es lo que hay guardado, no lo que el modelo crea que hay.
    """
    foto: dict = {}
    with motor.connect() as conexion:
        for tabla in tablas:
            resultado = conexion.exec_driver_sql(f'SELECT * FROM "{tabla}" ORDER BY rowid')
            foto[tabla] = [tuple(fila) for fila in resultado.fetchall()]
    return foto


def _como_se_guarda_una_version(version: models.VersionDeRecinto) -> dict:
    """Los campos de una versión del recinto que deciden **qué recinto es**, tal cual se guardan.

    Es lo que hace falta para poder decir «en este orden se quedó guardado *este* recinto» sin que
    nadie tenga que abrir la base: la clave exacta, la referencia, los números y las tres áreas.
    """
    return {
        "clave": version.clave,
        "referencia": version.referencia,
        "poligono": version.poligono,
        "numero_parcela": version.numero_parcela,
        "numero_recinto": version.numero_recinto,
        "agregado": version.agregado,
        "zona": version.zona,
        "area_sigpac_ha": version.area_sigpac_ha,
        "area_geometria_ha": version.area_geometria_ha,
        "area_declarada_ha": version.area_declarada_ha,
        "uso_sigpac": version.uso_sigpac,
        "poligono_valido": version.poligono_valido,
        "estado_revision": version.estado_revision,
        "geometria": version.geometria,
    }


@pytest.fixture
def crear_campana(cliente, cuenta):
    def _crear(anio: int, **cambios):
        datos = {"anio": anio, "fecha_inicio": f"{anio}-01-01", "fecha_fin": f"{anio}-12-31"}
        datos.update(cambios)
        respuesta = cliente.post("/api/campanas", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def tierra(crear_parcela):
    """Una tierra con los siete números del recinto 1, para poder enlazar un lote con ella."""
    return crear_parcela(
        alias="El Prado",
        ref_sigpac=REFERENCIA_1,
        poligono=503,
        numero_parcela=51,
        numero_recinto=1,
    )


# --------------------------------------------------------------------------
# Herramientas del almacén (T09)
# --------------------------------------------------------------------------

ALBARAN_BASE = {
    "fecha": "2026-05-04",
    "proveedor": "Cooperativa Agrícola de Peñaranda",
    "proveedor_nif": "B37000000",
    "numero_albaran": "A-2026-1",
    "lineas": [
        {
            "nombre": "Glifosato 36 SL",
            "cantidad": 5.0,
            "unidad_de_la_cantidad": "L",
            "numero_lote": "4471-A",
        }
    ],
}


def _recepcion(cliente, cabeceras, **cambios):
    datos = json.loads(json.dumps(ALBARAN_BASE))
    datos.update(cambios)
    return cliente.post("/api/almacen/recepciones", headers=cabeceras, json=datos)


def _existencias(cliente, cabeceras, **parametros) -> dict:
    respuesta = cliente.get("/api/almacen/existencias", headers=cabeceras, params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _el_articulo(existencias: dict, nombre: str) -> dict:
    return [uno for uno in existencias["articulos"] if uno["nombre"] == nombre][0]


def _el_lote_de(existencias: dict, nombre: str, numero_lote: str | None) -> dict:
    return [
        lote
        for lote in _el_articulo(existencias, nombre)["lotes"]
        if lote["numero_lote"] == numero_lote
    ][0]


def _movimiento(cliente, cabeceras, **datos):
    return cliente.post("/api/almacen/movimientos", headers=cabeceras, json=datos)


def _un_tratamiento(cliente, cabeceras, campana, parcela, producto, dosis, superficie, **cambios):
    datos = {
        "campana_id": campana["id"],
        "fecha": "2026-05-01",
        "parcela_id": parcela["id"],
        "superficie_tratada_ha": superficie,
        "cultivo": "Trigo blando",
        "plaga": "Roya amarilla",
        "justificacion": "Vi la plaga o la hierba en el campo",
        "producto_id": producto,
        "dosis": dosis,
        "unidad_dosis": "L/ha",
        "franja_seguridad_respetada": True,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/tratamientos", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _una_salida(cliente, cabeceras, **datos):
    return cliente.post("/api/almacen/salidas", headers=cabeceras, json=datos)


def _factura(cliente, cabeceras, **datos):
    """Una factura, que viaja como formulario con el JSON en el campo `datos` (lleva fichero)."""
    cuerpo = {
        "proveedor": "Cooperativa Agrícola de Peñaranda",
        "numero_factura": "F-2026-1",
        "fecha": "2026-05-02",
        "base_imponible": 100.0,
        "total": 121.0,
        "lineas": [],
    }
    cuerpo.update(datos)
    return cliente.post(
        "/api/facturas", headers=cabeceras, data={"datos": json.dumps(cuerpo)}
    )


def _metros_a_grados(lon0: float, lat0: float, dx_m: float, dy_m: float):
    """Un punto desplazado `dx_m` al este y `dy_m` al norte de (lon0, lat0)."""
    dlat = math.degrees(dy_m / geo.RADIO_TIERRA_M)
    dlon = math.degrees(dx_m / (geo.RADIO_TIERRA_M * math.cos(math.radians(lat0))))
    return lon0 + dlon, lat0 + dlat


# ==========================================================================
# 1. Un dato ausente nunca es cero ni «cumple»
# ==========================================================================


class Test1UnDatoAusenteNoEsCeroNiCumple:
    def test_un_recinto_sin_ninguna_superficie_sale_vacio_y_no_sale_cero(
        self, cliente, cuenta, campana
    ):
        """Contrato T05: «lo que no se sabe se queda vacío, nunca en 0» (hallazgo A7 de T02)."""
        plan = _previsualizar(cliente, cuenta["cabeceras"], _lote(campana, [_recinto(1)]))
        uno = plan["detalle"][0]
        assert uno["area_geometria_ha"] is None
        assert uno["area_sigpac_ha"] is None
        assert uno["area_declarada_ha"] is None
        # Y la cuenta de superficies dice que no hay dos que comparar, no que cuadren.
        diferencia = plan["diferencias_de_superficie"][0]
        assert diferencia["diferencia_ha"] is None
        assert diferencia["porcentaje"] is None
        assert diferencia["aviso"] is False
        assert "R10" not in diferencia["texto"]
        assert diferencia["texto"] == textos.mensaje("R10_sin_dos_superficies")

    def test_una_entrada_sin_cantidad_deja_el_saldo_sin_saber_y_no_en_cero(
        self, cliente, cuenta
    ):
        """Contrato T09: un albarán sin la cantidad legible no dice «no quedan 0 litros»."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        assert lote["saldo"] is None
        assert lote["saldo"] != 0
        assert lote["movimientos_sin_cantidad"] == 1
        assert lote["motivo"]

    def test_lo_comprado_que_no_ha_entrado_no_se_pierde_al_anular_el_albaran(
        self, cliente, cuenta, producto
    ):
        """Contrato T09 (§1.4 del documento): lo comprado y aún sin entrar se dice, «para que nadie
        crea que el programa ha perdido producto».

        Se compra (factura), se recibe con un albarán y **se anula el albarán**: la mercancía ya no
        cuenta en las existencias, así que sigue estando «comprada y sin entrar» y hay que decirlo.
        """
        factura = _factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="F-2026-77",
            lineas=[
                {
                    "descripcion": producto["nombre_comercial"],
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad": "L",
                    "precio_unitario": 20.0,
                    "importe": 100.0,
                }
            ],
        )
        assert factura.status_code == 201, factura.text

        creada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        assert creada.status_code == 201, creada.text
        recepcion_id = creada.json()["recepcion"]["id"]

        antes = _existencias(cliente, cuenta["cabeceras"])
        assert _el_lote_de(antes, producto["nombre_comercial"], "4471-A")["saldo"] == 5.0
        # Recibido: ya no está «sin entrar».
        assert antes["comprado_sin_entrar"] == []

        anulada = cliente.post(
            f"/api/almacen/recepciones/{recepcion_id}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "el papel era de otro proveedor"},
        )
        assert anulada.status_code == 200, anulada.text

        despues = _existencias(cliente, cuenta["cabeceras"])
        lote = _el_lote_de(despues, producto["nombre_comercial"], "4471-A")
        assert lote["saldo"] == 0.0, "el albarán anulado no puede seguir contando"

        # El contrato: la compra vuelve a estar pendiente de entrar, y se dice. Si no, el almacén
        # sale vacío y el agricultor cree que el programa le ha perdido el producto.
        assert [
            uno["nombre"] for uno in despues["comprado_sin_entrar"]
        ] == [producto["nombre_comercial"]], (
            "después de anular el albarán, la compra sigue sin haber entrado y no se dice"
        )

    def test_un_movimiento_del_que_no_se_sabe_la_cantidad_no_se_cuenta_como_cero_en_el_libro(
        self, cliente, cuenta
    ):
        """Contrato T09: un movimiento sin cantidad sale con `null`, no con un 0 que parezca dato."""
        creada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        assert creada.status_code == 201, creada.text
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        assert libro[0]["cantidad"] is None

    def test_el_resumen_del_almacen_cuenta_los_que_no_se_pueden_saber(
        self, cliente, cuenta
    ):
        """El resumen dice cuántos saldos no se saben; no los esconde detrás de un cero."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        existencias = _existencias(cliente, cuenta["cabeceras"])
        assert existencias["sin_poder_saber"] == 1
        assert existencias["en_negativo"] == 0
        assert _el_lote_de(existencias, "Glifosato 36 SL", "4471-A")["saldo"] is None


# ==========================================================================
# 2. No se duplican las existencias
# ==========================================================================


class Test2NoSeDuplicanLasExistencias:
    def test_el_mismo_albaran_dos_veces_con_la_misma_clave_no_duplica(self, cliente, cuenta):
        datos = dict(ALBARAN_BASE, clave_de_reenvio="albaran-1-abc")
        primera = _recepcion(cliente, cuenta["cabeceras"], **datos)
        segunda = _recepcion(cliente, cuenta["cabeceras"], **datos)
        assert (primera.status_code, segunda.status_code) == (201, 200)
        assert segunda.json()["ya_estaba"] is True
        assert primera.json()["recepcion"]["id"] == segunda.json()["recepcion"]["id"]
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 5.0

    def test_el_mismo_albaran_sin_clave_de_reenvio_tampoco_duplica(self, cliente, cuenta):
        assert _recepcion(cliente, cuenta["cabeceras"]).status_code == 201
        segunda = _recepcion(cliente, cuenta["cabeceras"])
        assert segunda.status_code == 200
        assert segunda.json()["ya_estaba"] is True
        assert len(cliente.get("/api/almacen/recepciones", headers=cuenta["cabeceras"]).json()) == 1
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 5.0

    def test_la_factura_que_llega_despues_no_vuelve_a_meter_la_mercancia(
        self, cliente, cuenta, producto
    ):
        """El caso A15: enganchar la factura no añade ni un litro."""
        creada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        recepcion_id = creada.json()["recepcion"]["id"]
        factura = _factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="F-2026-78",
            fecha="2026-05-06",
            lineas=[
                {
                    "descripcion": producto["nombre_comercial"],
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad": "L",
                    "precio_unitario": 20.0,
                    "importe": 100.0,
                }
            ],
        )
        assert factura.status_code == 201, factura.text
        antes = _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), producto["nombre_comercial"], "4471-A"
        )
        enganche = cliente.post(
            f"/api/almacen/recepciones/{recepcion_id}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura.json()["id"]},
        )
        assert enganche.status_code == 200, enganche.text
        despues = _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), producto["nombre_comercial"], "4471-A"
        )
        assert despues["saldo"] == antes["saldo"] == 5.0
        assert despues["entradas"] == antes["entradas"] == 5.0

    def test_reenviar_desde_la_cola_el_mismo_cuerpo_no_duplica(self, cliente, cuenta):
        """La cola sin cobertura manda **el mismo cuerpo**, con `id_local` además de la clave."""
        datos = dict(ALBARAN_BASE, clave_de_reenvio="albaran-9-xyz", id_local="p7-12345")
        assert _recepcion(cliente, cuenta["cabeceras"], **datos).status_code == 201
        for _ in range(3):
            repetida = _recepcion(cliente, cuenta["cabeceras"], **datos)
            assert repetida.status_code == 200, repetida.text
            assert repetida.json()["ya_estaba"] is True
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 5.0

    def test_la_unicidad_de_la_clave_de_reenvio_lleva_su_condicion_en_los_dos_dialectos(self):
        """La protección tiene que valer **en los dos motores**: SQLite y PostgreSQL.

        La base de producción es PostgreSQL (`AGENTS.md` §7, `database.py`). Un `Index(...,
        sqlite_where=...)` solo lleva la condición en SQLite: allí el índice se crea **único a
        secas**, el albarán anulado (o la salida anulada) vuelve a ocupar su clave y el reenvío desde
        el móvil vuelve a chocar con la base. Se comprueba el SQL que saldría en cada dialecto: los
        dos tienen que llevar la condición de «no anulado», cada uno escrita en su idioma (`= 0` en
        SQLite, `= false` en PostgreSQL), que es lo mismo dicho de dos maneras.
        """
        from sqlalchemy.dialects import postgresql, sqlite as dialecto_sqlite
        from sqlalchemy.schema import CreateIndex

        casos = (
            (models.Recepcion.__table__, "uq_recepcion_reenvio", "anulada"),
            (models.MovimientoDeExistencias.__table__, "uq_movimiento_reenvio", "anulado"),
        )
        for tabla, nombre, columna in casos:
            indice = [uno for uno in tabla.indexes if uno.name == nombre]
            assert indice, f"falta el índice {nombre}"
            en_sqlite = str(CreateIndex(indice[0]).compile(dialect=dialecto_sqlite.dialect()))
            en_postgres = str(CreateIndex(indice[0]).compile(dialect=postgresql.dialect()))
            for dialecto, sql in (("SQLite", en_sqlite), ("PostgreSQL", en_postgres)):
                # Lo que se comprueba es **lo que hace** el índice, no cómo se escribe el SQL: que
                # sea único (si no, no protege de nada) y que lleve **una condición** sobre la
                # columna de anulado (si no, una fila anulada vuelve a bloquear su clave). El
                # `= 0` de SQLite y el `= false` de PostgreSQL son la misma cosa dicha en el idioma
                # de cada motor, y mañana puede escribirse de otra manera igual de buena
                # (`WHERE NOT anulada`): exigir la cadena exacta daría un aviso falso.
                assert "UNIQUE INDEX" in sql.upper(), (
                    f"en {dialecto}, {nombre} no es único, así que no protege de nada: {sql}"
                )
                assert " WHERE " in sql.upper(), (
                    f"en {dialecto}, {nombre} se crea **sin condición**, así que una fila anulada "
                    f"volverá a bloquear su clave de reenvío. SQL generado: {sql}"
                )
                assert columna in sql, f"en {dialecto}, {nombre} no filtra por {columna}: {sql}"

    def test_una_instalacion_que_ya_tenia_la_tabla_no_recibe_el_arreglo_de_la_clave(self, tmp_path):
        """`crear_tablas()` **no vuelve a crear los índices de una tabla que ya existe**.

        El arreglo de «una fila anulada no ocupa su clave de reenvío» es un **índice nuevo**
        (`uq_recepcion_reenvio` con `WHERE anulada = 0`) que sustituye a una restricción única de
        antes. En una instalación donde `recepciones` ya se creó con la restricción vieja,
        `create_all` ve la tabla, no la toca, y el arreglo no llega: el agricultor sigue con el fallo
        que se acaba de arreglar en el código. Se comprueba sobre una base **temporal**, simulando
        la instalación vieja; nunca se abre la del agricultor.
        """
        from sqlalchemy import create_engine

        from app import database

        motor = create_engine(f"sqlite:///{(tmp_path / 'vieja.db').as_posix()}")
        models.Base.metadata.create_all(bind=motor)
        with motor.begin() as conexion:
            conexion.exec_driver_sql("DROP INDEX IF EXISTS uq_recepcion_reenvio")
            conexion.exec_driver_sql(
                "CREATE UNIQUE INDEX uq_recepcion_reenvio "
                "ON recepciones (explotacion_id, clave_de_reenvio)"
            )
        database.crear_tablas(motor)
        with motor.connect() as conexion:
            ddl = conexion.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'uq_recepcion_reenvio'"
            ).scalar()
        motor.dispose()
        assert "anulada = 0" in (ddl or ""), (
            "una instalación que ya tenía la tabla se queda con el índice de antes, así que el "
            f"arreglo no le llega: {ddl}"
        )

    def test_una_instalacion_que_ya_tenia_la_tabla_no_recibe_el_arreglo_de_la_salida(self, tmp_path):
        """Lo mismo con la clave de reenvío de un movimiento de almacén."""
        from sqlalchemy import create_engine

        from app import database

        motor = create_engine(f"sqlite:///{(tmp_path / 'vieja2.db').as_posix()}")
        models.Base.metadata.create_all(bind=motor)
        with motor.begin() as conexion:
            conexion.exec_driver_sql("DROP INDEX IF EXISTS uq_movimiento_reenvio")
            conexion.exec_driver_sql(
                "CREATE UNIQUE INDEX uq_movimiento_reenvio "
                "ON movimientos_de_existencias (explotacion_id, clave_de_reenvio)"
            )
        database.crear_tablas(motor)
        with motor.connect() as conexion:
            ddl = conexion.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'uq_movimiento_reenvio'"
            ).scalar()
        motor.dispose()
        assert "anulado = 0" in (ddl or ""), (
            "una instalación que ya tenía la tabla se queda con el índice de antes: " f"{ddl}"
        )

    def test_una_base_que_no_tenia_las_tablas_nace_con_el_indice_bueno(self, tmp_path):
        """**El alcance de D3, medido: al agricultor no le pasa.**

        Su base tiene 26 tablas y `recepciones` y `movimientos_de_existencias` **no están entre
        ellas**: las seis tablas nuevas de T05 y T09 se crean al arrancar. Se comprueba sobre una
        base temporal **vacía**: después de `crear_tablas()`, el índice nace con su condición desde
        el primer día, sin depender de que nadie recree nada.

        Es la diferencia entre «el agricultor se queda sin el arreglo» y «una instalación de prueba
        que ya había arrancado con la versión anterior se queda sin el arreglo». Solo lo segundo es
        verdad.
        """
        from sqlalchemy import create_engine

        from app import database

        motor = create_engine(f"sqlite:///{(tmp_path / 'nueva.db').as_posix()}")
        database.crear_tablas(motor)
        indices = {}
        with motor.connect() as conexion:
            for fila in conexion.exec_driver_sql(
                "SELECT name, sql FROM sqlite_master WHERE type = 'index' "
                "AND name IN ('uq_recepcion_reenvio', 'uq_movimiento_reenvio')"
            ).fetchall():
                indices[fila[0]] = fila[1]
        tablas = set()
        with motor.connect() as conexion:
            for fila in conexion.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall():
                tablas.add(fila[0])
        motor.dispose()

        assert {"recepciones", "movimientos_de_existencias"} <= tablas
        for nombre, columna in (
            ("uq_recepcion_reenvio", "anulada"),
            ("uq_movimiento_reenvio", "anulado"),
        ):
            assert nombre in indices, f"la base nueva no tiene {nombre}"
            assert "UNIQUE INDEX" in indices[nombre].upper(), indices[nombre]
            assert " WHERE " in indices[nombre].upper(), (
                f"una base nueva nace con {nombre} sin condición: {indices[nombre]}"
            )
            assert columna in indices[nombre], indices[nombre]

    def test_rehacer_el_indice_de_una_instalacion_vieja_no_cambia_ninguna_fila(self, tmp_path):
        """**El argumento que hace falta para decidir si D3 es grave**: un índice no toca los datos.

        Se monta una instalación «vieja» de verdad sobre una base temporal: el esquema de columnas de
        hoy (que es lo que `crear_tablas` ya sabe poner al día) y el índice único **a secas** de
        antes. Se le meten filas —una finca, un artículo, un lote, **un albarán y su entrada**, y un
        albarán **anulado** con su clave ocupada—, se guarda la huella de todas esas filas, y se
        llama a `crear_tablas()`, que tira el índice viejo y crea el bueno.

        Lo que se mide: el índice queda con su condición **y ni una fila cambia**. Tirar y volver a
        crear un índice no es una migración de datos, y esto lo demuestra en vez de afirmarlo.
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from app import database

        motor = create_engine(f"sqlite:///{(tmp_path / 'con_datos.db').as_posix()}")
        models.Base.metadata.create_all(bind=motor)
        with motor.begin() as conexion:
            conexion.exec_driver_sql("DROP INDEX IF EXISTS uq_recepcion_reenvio")
            conexion.exec_driver_sql(
                "CREATE UNIQUE INDEX uq_recepcion_reenvio "
                "ON recepciones (explotacion_id, clave_de_reenvio)"
            )
        # Las filas se meten por el modelo (no a mano) para que los valores por defecto de Python se
        # rellenen como en el programa de verdad.
        with Session(motor) as sesion:
            finca = models.Explotacion(nombre="Una finca", nif="12345678Z")
            sesion.add(finca)
            sesion.flush()
            articulo = models.Articulo(
                explotacion_id=finca.id, nombre="Glifosato 36 SL", categoria="fitosanitario"
            )
            sesion.add(articulo)
            sesion.flush()
            lote = models.Lote(
                explotacion_id=finca.id, articulo_id=articulo.id, numero_lote="4471-A"
            )
            sesion.add(lote)
            sesion.flush()
            buena = models.Recepcion(
                explotacion_id=finca.id,
                fecha=dt.date(2026, 5, 4),
                proveedor="Cooperativa",
                numero_albaran="A-2026-1",
                clave_de_reenvio="clave-buena",
            )
            anulada = models.Recepcion(
                explotacion_id=finca.id,
                fecha=dt.date(2026, 5, 5),
                proveedor="Cooperativa",
                numero_albaran="A-2026-2",
                clave_de_reenvio="clave-anulada",
                anulada=True,
                motivo_anulacion="estaba mal",
            )
            sesion.add_all([buena, anulada])
            sesion.flush()
            for recepcion, cantidad in ((buena, 5.0), (anulada, 3.0)):
                sesion.add(
                    models.MovimientoDeExistencias(
                        explotacion_id=finca.id,
                        articulo_id=articulo.id,
                        lote_id=lote.id,
                        tipo="entrada",
                        fecha=recepcion.fecha,
                        cantidad=cantidad,
                        unidad="L",
                        origen_tipo="recepcion",
                        origen_id=recepcion.id,
                        anulado=recepcion.anulada,
                    )
                )
            sesion.commit()

        tablas = ("explotaciones", "articulos", "lotes", "recepciones", "movimientos_de_existencias")
        antes = _las_filas_de(motor, tablas)
        assert len(antes["recepciones"]) == 2
        assert len(antes["movimientos_de_existencias"]) == 2

        database.crear_tablas(motor)

        with motor.connect() as conexion:
            ddl = conexion.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'uq_recepcion_reenvio'"
            ).scalar()
        despues = _las_filas_de(motor, tablas)
        motor.dispose()

        assert " WHERE " in (ddl or "").upper(), (
            f"la instalación vieja se ha quedado con el índice de antes: {ddl}"
        )
        assert "anulada" in (ddl or ""), ddl
        assert despues == antes, (
            "rehacer el índice ha cambiado alguna fila: "
            f"{[tabla for tabla in tablas if despues[tabla] != antes[tabla]]}"
        )

    def test_volver_a_apuntar_un_albaran_anulado_con_la_misma_clave_no_revienta(
        self, cliente, cuenta
    ):
        """Contrato del reenvío: «reenviar el mismo comando devuelve su resultado».

        El camino documentado es este: un albarán se apunta sin cobertura (con su clave), se ve que
        estaba mal y **se anula**, y el móvil vuelve a mandar el mismo cuerpo mientras la cola no se
        vacíe. Anular y volver a apuntar tiene que funcionar —lo dice el propio
        `_recepcion_que_ya_estaba`—, y desde luego no puede contestar un error del servidor: la cola
        del móvil **reintenta los 5xx**, así que un 500 aquí es un envío en bucle para siempre.
        """
        datos = dict(ALBARAN_BASE, clave_de_reenvio="albaran-5-repetido")
        primera = _recepcion(cliente, cuenta["cabeceras"], **datos)
        assert primera.status_code == 201, primera.text
        recepcion_id = primera.json()["recepcion"]["id"]
        anulada = cliente.post(
            f"/api/almacen/recepciones/{recepcion_id}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué de albarán"},
        )
        assert anulada.status_code == 200, anulada.text

        # Volver a apuntar el mismo albarán es lo que arregla el error: no puede fallar.
        segunda = _recepcion(cliente, cuenta["cabeceras"], **datos)
        assert segunda.status_code in (200, 201), segunda.text
        assert segunda.status_code != 500

    def test_un_albaran_anulado_y_vuelto_a_apuntar_no_cuenta_dos_veces(self, cliente, cuenta):
        datos = dict(ALBARAN_BASE, clave_de_reenvio="albaran-6-repetido")
        primera = _recepcion(cliente, cuenta["cabeceras"], **datos)
        recepcion_id = primera.json()["recepcion"]["id"]
        cliente.post(
            f"/api/almacen/recepciones/{recepcion_id}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "el número estaba mal"},
        )
        segunda = _recepcion(
            cliente,
            cuenta["cabeceras"],
            **dict(ALBARAN_BASE, clave_de_reenvio="albaran-6-bueno"),
        )
        assert segunda.status_code == 201, segunda.text
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 5.0

    def test_la_factura_de_un_albaran_anulado_se_puede_enganchar_al_bueno(
        self, cliente, cuenta, producto
    ):
        """Una factura enganchada a un albarán **anulado** tiene que poder engancharse al bueno.

        El albarán anulado es el que el agricultor ha dicho que estaba mal. Si la factura sigue
        apuntando a él y el enganche se niega con un 409, la compra se queda sin ningún documento
        correcto al que pertenecer: la única salida que da el propio mensaje
        (`AL7_esa_factura_ya_esta_en_otro_albaran`) es «apunta el segundo con su número y engancha
        la factura al que la trajo», y esa salida tiene que estar abierta.
        """
        factura = _factura(
            cliente,
            cuenta["cabeceras"],
            numero_factura="F-2026-79",
            lineas=[
                {
                    "descripcion": producto["nombre_comercial"],
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad": "L",
                    "precio_unitario": 20.0,
                    "importe": 100.0,
                }
            ],
        )
        assert factura.status_code == 201, factura.text
        factura_id = factura.json()["id"]

        primera = _recepcion(
            cliente,
            cuenta["cabeceras"],
            clave_de_reenvio="albaran-mal-1",
            factura_id=factura_id,
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        assert primera.status_code == 201, primera.text
        recepcion_id = primera.json()["recepcion"]["id"]
        assert cliente.post(
            f"/api/almacen/recepciones/{recepcion_id}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "este albarán no es el de esa factura"},
        ).status_code == 200

        # El camino que dice el mensaje: se apunta el bueno con su número y se engancha la factura.
        buena = _recepcion(
            cliente,
            cuenta["cabeceras"],
            clave_de_reenvio="albaran-bueno-1",
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        assert buena.status_code == 201, buena.text
        enganche = cliente.post(
            f"/api/almacen/recepciones/{buena.json()['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura_id},
        )
        assert enganche.status_code == 200, (
            "la factura no se puede enganchar a ningún albarán vivo: "
            "el que la tenía está anulado y el enganche lo sigue contando: " + enganche.text
        )
        assert enganche.json()["factura_id"] == factura_id

    def test_un_albaran_sin_proveedor_dice_que_no_ha_podido_comprobar_si_ya_estaba(
        self, cliente, cuenta
    ):
        """El tercer estado, comprobado: cuando no se puede comprobar, se dice (no es un «sí»).

        Un albarán con número pero sin proveedor no se puede reconocer, así que entra igual y la
        respuesta lo declara. Es la regla del proyecto («hay tres finales, no dos»), y por eso esto
        **no** se cuenta como defecto aunque deje pasar el mismo papel dos veces: lo que no se puede
        saber, se dice.
        """
        primera = _recepcion(cliente, cuenta["cabeceras"], proveedor=None, proveedor_nif=None)
        assert primera.status_code == 201, primera.text
        assert textos.MENSAJES["AL5_no_se_pudo_comprobar_si_ya_estaba"] in primera.json()["avisos"]
        segunda = _recepcion(cliente, cuenta["cabeceras"], proveedor=None, proveedor_nif=None)
        assert segunda.status_code == 201
        # Y lo que ha pasado se ve: dos entradas, diez litros. El programa lo dijo antes de apuntar.
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 10.0

    def test_una_salida_anulada_se_puede_volver_a_apuntar_con_la_misma_clave_de_reenvio(
        self, cliente, cuenta, campana, producto, crear_parcela
    ):
        """Anular una salida devuelve el producto; reenviarla **con la misma clave** también.

        El documento dice, con estas palabras, que «si la que había está anulada, sí se puede
        apuntar otra: anular existe justo para eso». Y la cola del móvil reenvía el **mismo cuerpo**,
        con la misma clave, así que si esa clave devuelve la salida anulada, el consumo bueno no se
        apunta nunca y el almacén se queda con el producto devuelto para siempre.
        """
        parcela = crear_parcela(alias="La grande", superficie_ha=5.0)
        _recepcion(cliente, cuenta["cabeceras"])
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.5, 4.0
        )
        cuerpo = {
            "apunte_tipo": "tratamiento",
            "apunte_id": apunte["id"],
            "lote_id": lote["lote_id"],
            "clave_de_reenvio": "salida-1-abc",
        }
        primera = _una_salida(cliente, cuenta["cabeceras"], **cuerpo)
        assert primera.status_code == 201, primera.text
        movimiento = primera.json()["movimiento"]
        cliente.post(
            f"/api/almacen/movimientos/{movimiento['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "salía de otro envase"},
        )
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 5.0

        segunda = _una_salida(cliente, cuenta["cabeceras"], **cuerpo)
        assert segunda.status_code in (200, 201), segunda.text
        assert segunda.json()["movimiento"]["anulado"] is False
        assert segunda.json()["ya_estaba"] is False
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 3.0


# ==========================================================================
# 3. El total y la dosis, cada uno con su nombre
# ==========================================================================


class Test3ElTotalYLaDosisVanCadaUnoConSuNombre:
    def test_una_salida_desde_un_apunte_dice_el_total_y_la_dosis_por_separado(
        self, cliente, cuenta, campana, producto, crear_parcela
    ):
        """Contrato A02: 2 L en 4 ha son 0,5 L/ha, y las dos cifras salen con su nombre."""
        parcela = crear_parcela(alias="La grande", superficie_ha=5.0)
        _recepcion(cliente, cuenta["cabeceras"])
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.5, 4.0
        )
        respuesta = _una_salida(
            cliente, cuenta["cabeceras"], apunte_tipo="tratamiento", apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
        )
        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["cantidad_total_gastada"] == 2.0
        assert cuerpo["unidad_de_la_cantidad"] == "L"
        assert cuerpo["dosis_por_hectarea"] == 0.5
        assert cuerpo["superficie_ha"] == 4.0
        # Las dos cifras son distintas, y por eso hay que decirlas por separado.
        assert cuerpo["cantidad_total_gastada"] != cuerpo["dosis_por_hectarea"]

    def test_un_apunte_que_solo_trae_la_dosis_pide_el_total_en_vez_de_multiplicarlo(
        self, cliente, cuenta, campana, producto, nuevo_tratamiento_en_instalacion
    ):
        """La confusión de diez veces: el programa no multiplica la dosis por su cuenta.

        Es el caso de un tratamiento de una nave: se sabe la dosis (0,5 L/ha) pero **no hay
        hectáreas**, así que el total no se sabe y lo tiene que decir el agricultor.
        """
        _recepcion(cliente, cuenta["cabeceras"])
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        creado = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(producto_id=producto["id"], dosis=0.5),
        )
        assert creado.status_code == 201, creado.text
        apunte = creado.json()
        assert apunte["cantidad_total"] is None, "la nave no tiene hectáreas: el total no se sabe"

        respuesta = _una_salida(
            cliente, cuenta["cabeceras"], apunte_tipo="tratamiento", apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
        )
        assert respuesta.status_code == 409, respuesta.text
        assert textos.mensaje("AL17_el_apunte_no_dice_el_total") in respuesta.text
        # Y no ha apuntado nada a medias.
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        assert [uno for uno in libro if uno["tipo"] == "salida"] == []

    def test_si_se_dice_el_total_a_mano_la_dosis_sigue_diciendose_apartado(
        self, cliente, cuenta, crear_producto, nuevo_tratamiento_en_instalacion
    ):
        """Y cuando el agricultor escribe el total, la dosis del apunte **no** se pierde."""
        producto = crear_producto(dosis_maxima=10.0)
        _recepcion(cliente, cuenta["cabeceras"])
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        creado = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(producto_id=producto["id"], dosis=2.0),
        )
        assert creado.status_code == 201, creado.text
        apunte = creado.json()
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
            cantidad=3.5,
        )
        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["cantidad_total_gastada"] == 3.5
        assert cuerpo["dosis_por_hectarea"] != cuerpo["cantidad_total_gastada"]

    def test_un_abono_gasta_en_kilos_y_su_total_es_el_que_dice_el_apunte(
        self, cliente, cuenta, campana, parcela, fertilizante, nueva_fertilizacion
    ):
        """El abono se apunta en kg/ha y su total son kilos: 300 kg/ha en 2 ha son 600 kg."""
        creada = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(superficie_ha=2.0, kg_ha_producto=300.0),
        )
        assert creada.status_code == 201, creada.text
        abono = creada.json()
        assert abono["cantidad_total_kg"] == 600.0

        recibido = _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-ABONO-1",
            lineas=[
                {
                    "fertilizante_id": fertilizante["id"],
                    "cantidad": 600.0,
                    "unidad_de_la_cantidad": "kg",
                    "numero_lote": "SACO-1",
                }
            ],
        )
        assert recibido.status_code == 201, recibido.text
        lote = _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), fertilizante["nombre"], "SACO-1"
        )
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="fertilizacion",
            apunte_id=abono["id"],
            lote_id=lote["lote_id"],
        )
        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["cantidad_total_gastada"] == 600.0
        assert cuerpo["unidad_de_la_cantidad"] == "kg"
        assert cuerpo["dosis_por_hectarea"] == 300.0
        assert cuerpo["superficie_ha"] == 2.0

    def test_la_unidad_del_movimiento_sale_del_albaran_y_no_de_la_ficha(
        self, cliente, cuenta, producto
    ):
        """El papel manda sobre la ficha: si el albarán dice kg, el movimiento es en kg."""
        creada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 20.0,
                    "unidad_de_la_cantidad": "kg",
                    "numero_lote": "4471-B",
                }
            ],
        )
        assert creada.status_code == 201, creada.text
        lote = _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), producto["nombre_comercial"], "4471-B"
        )
        assert lote["unidad"] == "kg"
        assert lote["saldo"] == 20.0

    def test_mezclar_litros_y_kilos_no_da_un_saldo(
        self, cliente, cuenta, producto
    ):
        """Un litro y un kilo no se restan: la cuenta se calla en vez de inventarse un número."""
        creada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-C",
                }
            ],
        )
        assert creada.status_code == 201, creada.text
        lote = _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), producto["nombre_comercial"], "4471-C"
        )
        # Una merma en kilos sobre el mismo envase: las dos unidades no se pueden comparar.
        merma = _movimiento(
            cliente,
            cuenta["cabeceras"],
            tipo="merma",
            lote_id=lote["lote_id"],
            cantidad=1.0,
            unidad="kg",
            motivo="se rompió el envase",
        )
        assert merma.status_code == 201, merma.text
        lote = _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), producto["nombre_comercial"], "4471-C"
        )
        assert lote["saldo"] is None
        assert lote["unidades_que_no_cuadran"] == ["kg"]

    def test_una_salida_en_una_unidad_que_no_cuadra_con_el_envase_lo_avisa(
        self, cliente, cuenta, campana, producto, crear_parcela
    ):
        """La unidad del envase y la de lo que sale tienen que poder compararse, o se dice."""
        parcela = crear_parcela(alias="La grande", superficie_ha=5.0)
        _recepcion(cliente, cuenta["cabeceras"])
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.5, 4.0
        )
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
            cantidad=2.0,
            unidad="kg",
        )
        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["avisos"], "sacar kilos de un envase de litros tiene que avisarse"
        assert textos.MENSAJES["AL3_la_unidad_no_cuadra"].format(
            unidad="L", otra="kg"
        ) in cuerpo["avisos"]


# ==========================================================================
# 4. Aislamiento entre explotaciones (404 y no 403)
# ==========================================================================


class Test4NingunaRutaDevuelveDatosDeOtraFinca:
    @pytest.fixture
    def otra(self, cliente, cuenta, crear_cuenta, campana, crear_campana, crear_parcela):
        """Una segunda finca con datos de verdad: su campaña, su tierra y su albarán."""
        otra_cuenta = crear_cuenta("otro@ejemplo.test", "Otro Agricultor", "12345678Z")
        cabeceras = otra_cuenta["cabeceras"]
        su_campana = cliente.get("/api/campanas/actual", headers=cabeceras).json()
        su_tierra = cliente.post(
            "/api/parcelas",
            headers=cabeceras,
            json={
                "alias": "La del otro",
                "ref_sigpac": REFERENCIA_2,
                "poligono": 503,
                "numero_parcela": 51,
                "numero_recinto": 2,
                "superficie_ha": 1.5,
            },
        )
        assert su_tierra.status_code == 201, su_tierra.text
        su_tierra = su_tierra.json()
        su_albaran = cliente.post(
            "/api/almacen/recepciones",
            headers=cabeceras,
            json=ALBARAN_BASE,
        )
        assert su_albaran.status_code == 201, su_albaran.text
        su_albaran = su_albaran.json()["recepcion"]
        su_articulo = cliente.get("/api/almacen/articulos", headers=cabeceras).json()[0]
        su_lote = cliente.get(
            "/api/almacen/lotes", headers=cabeceras, params={"articulo_id": su_articulo["id"]}
        ).json()[0]
        su_movimiento = cliente.get("/api/almacen/movimientos", headers=cabeceras).json()[0]
        return {
            "cuenta": otra_cuenta,
            "cabeceras": cabeceras,
            "campana": su_campana,
            "tierra": su_tierra,
            "albaran": su_albaran,
            "articulo": su_articulo,
            "lote": su_lote,
            "movimiento": su_movimiento,
        }

    def test_las_versiones_de_otra_tierra_no_se_pueden_listar(self, cliente, cuenta, otra):
        for parametros in (
            {"parcela_id": otra["tierra"]["id"]},
            {"campana_id": otra["campana"]["id"]},
            {"parcela_id": otra["tierra"]["id"], "campana_id": otra["campana"]["id"]},
        ):
            respuesta = cliente.get("/api/versiones", headers=cuenta["cabeceras"], params=parametros)
            assert respuesta.status_code == 404, (parametros, respuesta.status_code)

    def test_no_se_puede_comparar_una_tierra_de_otra_finca(self, cliente, cuenta, otra, campana):
        respuesta = cliente.get(
            "/api/versiones/comparar",
            headers=cuenta["cabeceras"],
            params={
                "parcela_id": otra["tierra"]["id"],
                "campana_antes": campana["id"],
                "campana_despues": campana["id"],
            },
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_comparar_con_la_campana_de_otra_finca(self, cliente, cuenta, otra, campana):
        for parametros in (
            {"campana_antes": otra["campana"]["id"], "campana_despues": campana["id"]},
            {"campana_antes": campana["id"], "campana_despues": otra["campana"]["id"]},
        ):
            respuesta = cliente.get(
                "/api/versiones/comparar-explotacion",
                headers=cuenta["cabeceras"],
                params=parametros,
            )
            assert respuesta.status_code == 404, (parametros, respuesta.status_code)

    def test_no_se_puede_importar_un_lote_contra_la_tierra_de_otra_finca(
        self, cliente, cuenta, otra, campana
    ):
        lote = _lote(campana, [_recinto(1, parcela_id=otra["tierra"]["id"])])
        respuesta = cliente.post(
            "/api/versiones/aplicar", headers=cuenta["cabeceras"], json=lote
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_previsualizar_contra_la_campana_de_otra_finca(
        self, cliente, cuenta, otra
    ):
        lote = _lote(otra["campana"], [_recinto(1)])
        respuesta = cliente.post(
            "/api/versiones/previsualizar", headers=cuenta["cabeceras"], json=lote
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_ver_ni_anular_el_albaran_de_otra_finca(self, cliente, cuenta, otra):
        identificador = otra["albaran"]["id"]
        visto = cliente.get(
            f"/api/almacen/recepciones/{identificador}", headers=cuenta["cabeceras"]
        )
        anulado = cliente.post(
            f"/api/almacen/recepciones/{identificador}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no es mío"},
        )
        assert (visto.status_code, anulado.status_code) == (404, 404)

    def test_no_se_puede_preguntar_por_el_articulo_ni_el_lote_de_otra_finca(
        self, cliente, cuenta, otra
    ):
        articulo = cliente.get(
            "/api/almacen/existencias",
            headers=cuenta["cabeceras"],
            params={"articulo_id": otra["articulo"]["id"]},
        )
        lotes = cliente.get(
            "/api/almacen/lotes",
            headers=cuenta["cabeceras"],
            params={"articulo_id": otra["articulo"]["id"]},
        )
        libro = cliente.get(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            params={"lote_id": otra["lote"]["id"]},
        )
        assert [r.status_code for r in (articulo, lotes, libro)] == [404, 404, 404]

    def test_no_se_puede_anular_el_movimiento_de_otra_finca(self, cliente, cuenta, otra):
        respuesta = cliente.post(
            f"/api/almacen/movimientos/{otra['movimiento']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no es mío"},
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_sacar_de_un_lote_de_otra_finca(
        self, cliente, cuenta, otra, campana, parcela, producto
    ):
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.5, 2.0
        )
        respuesta = _una_salida(
            cliente, cuenta["cabeceras"], apunte_tipo="tratamiento", apunte_id=apunte["id"],
            lote_id=otra["lote"]["id"],
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_sacar_de_un_apunte_de_otra_finca(
        self, cliente, cuenta, otra, campana, parcela, producto
    ):
        """El apunte del que sale un consumo también tiene que ser de esta finca."""
        _recepcion(cliente, cuenta["cabeceras"])
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        su_producto = cliente.post(
            "/api/productos",
            headers=otra["cabeceras"],
            json={
                "nombre_comercial": "Suyo 25 EC",
                "numero_registro": "24.999",
                "materia_activa": "Tebuconazol",
                "dosis_maxima": 5.0,
                "unidad_dosis": "L/ha",
                "plazo_seguridad_dias": 21,
            },
        )
        assert su_producto.status_code == 201, su_producto.text
        apunte_de_otro = cliente.post(
            "/api/tratamientos",
            headers=otra["cabeceras"],
            json={
                "campana_id": otra["campana"]["id"],
                "fecha": "2026-05-01",
                "parcela_id": otra["tierra"]["id"],
                "superficie_tratada_ha": 1.0,
                "cultivo": "Trigo blando",
                "plaga": "Roya amarilla",
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": su_producto.json()["id"],
                "dosis": 1.0,
                "unidad_dosis": "L/ha",
                "franja_seguridad_respetada": True,
            },
        )
        assert apunte_de_otro.status_code == 201, apunte_de_otro.text
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte_de_otro.json()["id"],
            lote_id=lote["lote_id"],
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_abrir_un_lote_en_el_articulo_de_otra_finca(self, cliente, cuenta, otra):
        respuesta = cliente.post(
            "/api/almacen/lotes",
            headers=cuenta["cabeceras"],
            json={"articulo_id": otra["articulo"]["id"], "numero_lote": "X-1"},
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_enganchar_una_factura_de_otra_finca(self, cliente, cuenta, otra):
        mios = _recepcion(cliente, cuenta["cabeceras"])
        assert mios.status_code == 201, mios.text
        factura_de_otro = _factura(
            cliente,
            otra["cabeceras"],
            numero_factura="F-OTRO-1",
            fecha="2026-05-06",
            lineas=[],
        )
        assert factura_de_otro.status_code == 201, factura_de_otro.text
        respuesta = cliente.post(
            f"/api/almacen/recepciones/{mios.json()['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura_de_otro.json()["id"]},
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_apuntar_una_linea_de_factura_de_otra_finca(
        self, cliente, cuenta, otra, producto
    ):
        factura_de_otro = _factura(
            cliente,
            otra["cabeceras"],
            numero_factura="F-OTRO-2",
            lineas=[
                {
                    "descripcion": "algo suyo",
                    "cantidad": 1.0,
                    "unidad": "L",
                    "precio_unitario": 1.0,
                    "importe": 1.0,
                }
            ],
        )
        assert factura_de_otro.status_code == 201, factura_de_otro.text
        linea_de_otro = factura_de_otro.json()["lineas"][0]["id"]
        respuesta = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "linea_factura_id": linea_de_otro,
                }
            ],
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_no_se_puede_apuntar_una_entrada_contra_la_factura_de_otra_finca(
        self, cliente, cuenta, otra, producto
    ):
        factura_de_otro = _factura(
            cliente, otra["cabeceras"], numero_factura="F-OTRO-3", lineas=[]
        )
        assert factura_de_otro.status_code == 201, factura_de_otro.text
        respuesta = _movimiento(
            cliente,
            cuenta["cabeceras"],
            tipo="entrada",
            articulo_id=None,
            origen_tipo="factura",
            origen_id=factura_de_otro.json()["id"],
            cantidad=1.0,
            unidad="L",
        )
        assert respuesta.status_code in (404, 400), respuesta.text
        assert respuesta.status_code != 500

    def test_la_propuesta_de_albaranes_de_una_factura_de_otra_finca_no_se_ve(
        self, cliente, cuenta, otra
    ):
        factura_de_otro = _factura(
            cliente, otra["cabeceras"], numero_factura="F-OTRO-4", lineas=[]
        )
        assert factura_de_otro.status_code == 201, factura_de_otro.text
        respuesta = cliente.get(
            f"/api/almacen/facturas/{factura_de_otro.json()['id']}/posibles-recepciones",
            headers=cuenta["cabeceras"],
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_un_identificador_que_no_existe_tambien_es_404(self, cliente, cuenta, campana):
        """Un identificador que no existe y uno de otra finca contestan lo mismo: 404."""
        assert cliente.get(
            "/api/versiones", headers=cuenta["cabeceras"], params={"parcela_id": 99999}
        ).status_code == 404
        assert cliente.get(
            "/api/versiones", headers=cuenta["cabeceras"], params={"campana_id": 99999}
        ).status_code == 404
        assert cliente.get(
            "/api/almacen/recepciones/99999", headers=cuenta["cabeceras"]
        ).status_code == 404
        assert cliente.get(
            "/api/almacen/existencias", headers=cuenta["cabeceras"], params={"articulo_id": 99999}
        ).status_code == 404

    def test_la_lista_de_versiones_no_trae_lo_de_otra_finca(
        self, cliente, cuenta, otra, campana
    ):
        _aplicar(cliente, otra["cabeceras"], _lote(otra["campana"], [_recinto(1)]))
        assert _versiones(cliente, cuenta["cabeceras"]) == []
        # Y tampoco al revés.
        assert _versiones(cliente, otra["cabeceras"]) != []

    def test_nadie_sin_entrar_ve_el_almacen_ni_las_versiones(self, cliente):
        assert cliente.get("/api/almacen/existencias").status_code == 401
        assert cliente.get("/api/versiones").status_code == 401


# ==========================================================================
# 5. Idempotencia de la importación
# ==========================================================================


class Test5LaImportacionDeRecintosEsIdempotente:
    def test_aplicar_dos_veces_el_mismo_lote_no_deja_ni_un_rastro_en_la_auditoria(
        self, cliente, cuenta, campana, db_sesion
    ):
        lote = _lote(
            campana,
            [
                _recinto(1, geometria=CUADRADO_100_M, area_sigpac_ha=0.93),
                _recinto(2),
                _recinto(3),
            ],
            fecha_consulta="2026-03-01",
        )
        _aplicar(cliente, cuenta["cabeceras"], lote)
        antes = _foto_completa(db_sesion)
        _aplicar(cliente, cuenta["cabeceras"], lote)
        assert _foto_completa(db_sesion) == antes

    def test_el_mismo_lote_con_los_recintos_en_otro_orden_no_cambia_nada(
        self, cliente, cuenta, campana, db_sesion
    ):
        recintos = [
            _recinto(1, geometria=CUADRADO_100_M, area_sigpac_ha=0.93, area_declarada_ha=0.9),
            _recinto(2),
            _recinto(3),
        ]
        _aplicar(cliente, cuenta["cabeceras"], _lote(campana, recintos))
        antes = _foto_completa(db_sesion)
        for vuelta in (list(reversed(recintos)), recintos[1:] + recintos[:1]):
            _aplicar(cliente, cuenta["cabeceras"], _lote(campana, vuelta))
            assert _foto_completa(db_sesion) == antes

    def test_la_misma_clave_a_medias_en_dos_tierras_distintas_no_se_pisan(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Dos tierras distintas, cada una con su recinto: la clave a medias es la misma clave
        de texto, pero son **dos recintos de dos tierras**, y los dos tienen que entrar.

        «La misma clave a medias» es lo que pasa cuando la fuente no manda el número de recinto: la
        clave del recinto queda igual para todos (`37-70-0-0-503-51-`), y hay que poder importar el
        de cada tierra sin que uno se coma al otro.
        """
        una = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "La una", "poligono": 503, "numero_parcela": 51, "numero_recinto": 1},
        ).json()
        otra = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "La otra", "poligono": 503, "numero_parcela": 51, "numero_recinto": 2},
        ).json()
        recintos = [
            _recinto(1, numero_recinto=None, parcela_id=una["id"], area_sigpac_ha=0.93),
            _recinto(1, numero_recinto=None, parcela_id=otra["id"], area_sigpac_ha=1.2),
        ]
        primera = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, recintos))
        assert primera["problemas"] == [], primera["problemas"]
        assert primera["versiones_creadas"] == 2

        antes = _foto_completa(db_sesion)
        segunda = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, recintos))
        assert segunda["versiones_creadas"] == 0
        assert segunda["iguales"] == 2
        assert _foto_completa(db_sesion) == antes

    def test_una_importacion_repetida_no_reabre_una_tierra_que_ya_existe(
        self, cliente, cuenta, campana, db_sesion, tierra
    ):
        lote = _lote(campana, [_recinto(1, area_sigpac_ha=0.93)])
        _aplicar(cliente, cuenta["cabeceras"], lote)
        antes = _foto_de_las_tierras(db_sesion)
        plan = _aplicar(cliente, cuenta["cabeceras"], lote)
        assert (plan["tierras_creadas"], plan["tierras_nuevas"]) == ([], 0)
        assert _foto_de_las_tierras(db_sesion) == antes

    def test_un_lote_contradictorio_en_otro_orden_no_puede_cambiar_lo_guardado(
        self, cliente, cuenta, campana, db_sesion
    ):
        """El mismo lote, en otro orden, **no puede cambiar nada** — ni siquiera si es contradictorio.

        El lote trae dos recintos distintos para la misma tierra: el programa lo detecta
        (`R6_recinto_repetido`).

        **El contrato lo decidió el coordinador el 03/10/2026: no se guarda ninguno de los dos.** Las
        dos mitades del hallazgo del revisor son verdad y no se pueden tener las dos a la vez: si se
        guarda uno, cuál se guarda depende del orden en que vengan los renglones; y si no se sabe cuál
        de los dos es el bueno, no se puede elegir. Se elige **no guardar**, que es lo recuperable
        —volver a mandar el lote con un solo recinto lo arregla en un paso— y no deja una forma
        equivocada en la ficha de la tierra ni un apunte de auditoría por un cambio que nadie pidió.
        """
        uno = _recinto(1, geometria=CUADRADO_100_M, area_sigpac_ha=0.93)
        otro = _recinto(1, geometria=_poligono(_anillo(-5.0, 41.0, 1000.0)), area_sigpac_ha=99.0)

        primera = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, [uno, otro]))
        assert primera["problemas"], "el lote contradictorio tiene que decirse"
        assert primera["versiones_creadas"] == 0, (
            "se ha guardado uno de los dos recintos contradictorios: el orden ha decidido cuál"
        )
        antes = _foto_completa(db_sesion)

        segunda = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, [otro, uno]))
        assert (segunda["versiones_actualizadas"], segunda["cambiados"]) == (0, 0), (
            "el mismo lote con los renglones al revés ha reescrito la versión"
        )
        assert _foto_de_las_versiones(db_sesion) == [], (
            "el orden de los renglones ha decidido qué recinto se guarda"
        )
        assert _foto_completa(db_sesion) == antes

    def test_la_primera_importacion_del_lote_contradictorio_tampoco_depende_del_orden(
        self, cliente, cuenta, crear_cuenta, campana, db_sesion
    ):
        """La primera importación de un lote contradictorio tampoco puede depender del orden.

        Lo encontró el revisor: el arreglo de D4 solo se aplicaba cuando la tierra **ya existe**
        (`preparado.parcela_id is not None`), así que la primera importación de un lote contradictorio
        en una finca nueva **seguía quedándose con el primero que llegue**. Medido: con el lote
        `[100 m, 1 km]` quedaba 0,93 ha y con el mismo lote al revés 99,0 ha.

        **El contrato lo decidió el coordinador el 03/10/2026: no se guarda ninguno de los dos**, ni
        en una finca nueva ni en una que ya tiene la tierra. El revisor tenía razón y su propio texto
        lo dice: «si no se sabe cuál de los dos es el bueno, no puede guardarse ninguno». Con eso, las
        dos fincas acaban igual —sin ninguna versión de ese recinto— y el agricultor se entera por el
        aviso, que es lo único honesto que se puede hacer con dos recintos que se contradicen.
        """
        uno = _recinto(1, geometria=CUADRADO_100_M, area_sigpac_ha=0.93)
        otro = _recinto(1, geometria=_poligono(_anillo(-5.0, 41.0, 1000.0)), area_sigpac_ha=99.0)

        primera = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, [uno, otro]))
        assert primera["problemas"], "el lote contradictorio tiene que decirse"
        assert primera["versiones_creadas"] == 0, primera

        otra = crear_cuenta("la-otra@ejemplo.test", "Otro Agricultor", "12345678Z")
        su_campana = cliente.get("/api/campanas/actual", headers=otra["cabeceras"]).json()
        segunda = _aplicar(cliente, otra["cabeceras"], _lote(su_campana, [otro, uno]))
        assert segunda["problemas"], "el lote contradictorio tiene que decirse también aquí"
        assert segunda["versiones_creadas"] == 0, segunda

        guardadas = [
            _como_se_guarda_una_version(version)
            for version in db_sesion.scalars(
                select(models.VersionDeRecinto).order_by(models.VersionDeRecinto.id)
            ).all()
        ]
        assert guardadas == [], (
            "el mismo lote contradictorio, importado por primera vez en dos fincas, ha guardado "
            "algún recinto: el orden de los renglones ha decidido cuál. Lo que hay guardado:\n"
            f"  {guardadas}\n"
            "Si no se sabe cuál de los dos es el bueno, no puede guardarse ninguno."
        )
        # Y para que la decisión se pueda tomar con todas las cartas: cuál es cada uno de los dos
        # renglones del lote, medido por el propio programa en la previsualización.
        previsto = _previsualizar(
            cliente, cuenta["cabeceras"], _lote(campana, [uno, otro])
        )
        assert previsto["detalle"] == [], previsto["detalle"]
        assert previsto["problemas"], previsto["problemas"]

    def test_la_unicidad_de_una_version_por_tierra_campana_y_fuente_esta_en_la_base(
        self, cliente, cuenta, campana, db_sesion
    ):
        """La defensa contra dos peticiones a la vez es la restricción única de la base.

        El documento de T05 dice que no hay prueba de carrera y que la defensa es la restricción.
        Esto comprueba **que la restricción está y que la base la aplica**, que es lo que se puede
        comprobar sin disparar dos peticiones simultáneas.
        """
        _aplicar(cliente, cuenta["cabeceras"], _lote(campana, [_recinto(1)]))
        guardada = _foto_de_las_versiones(db_sesion)[0]
        repetida = models.VersionDeRecinto(
            explotacion_id=1,
            parcela_id=guardada["parcela_id"],
            campana_id=guardada["campana_id"],
            fuente=guardada["fuente"],
            clave="otra",
        )
        db_sesion.add(repetida)
        with pytest.raises(Exception) as fallo:
            db_sesion.flush()
        assert "uq_version_de_recinto" in str(fallo.value) or "UNIQUE" in str(fallo.value).upper()
        db_sesion.rollback()


# ==========================================================================
# 6. Comparar no escribe
# ==========================================================================


class Test6CompararNoEscribeNada:
    def test_comparar_dos_campanas_no_escribe_ni_deja_rastro(
        self, cliente, cuenta, campana, crear_campana, db_sesion
    ):
        otra = crear_campana(campana["anio"] + 1)
        _aplicar(cliente, cuenta["cabeceras"], _lote(campana, [_recinto(1), _recinto(2)]))
        _aplicar(cliente, cuenta["cabeceras"], _lote(otra, [_recinto(1)]))
        antes = _foto_completa(db_sesion)
        tierra = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()[0]

        for _ in range(3):
            respuesta = cliente.get(
                "/api/versiones/comparar",
                headers=cuenta["cabeceras"],
                params={
                    "parcela_id": tierra["id"],
                    "campana_antes": campana["id"],
                    "campana_despues": otra["id"],
                },
            )
            assert respuesta.status_code == 200, respuesta.text
        assert _foto_completa(db_sesion) == antes

    def test_comparar_la_finca_entera_no_escribe_ni_deja_rastro(
        self, cliente, cuenta, campana, crear_campana, db_sesion
    ):
        otra = crear_campana(campana["anio"] + 1)
        _aplicar(cliente, cuenta["cabeceras"], _lote(campana, [_recinto(1)]))
        antes = _foto_completa(db_sesion)
        for _ in range(3):
            respuesta = cliente.get(
                "/api/versiones/comparar-explotacion",
                headers=cuenta["cabeceras"],
                params={"campana_antes": campana["id"], "campana_despues": otra["id"]},
            )
            assert respuesta.status_code == 200, respuesta.text
        assert _foto_completa(db_sesion) == antes


# ==========================================================================
# 7. Previsualizar no escribe, y el plan es el mismo que el de aplicar
# ==========================================================================


class Test7PrevisualizarNoEscribeNada:
    def test_previsualizar_no_escribe_ni_deja_rastro_en_la_auditoria(
        self, cliente, cuenta, campana, db_sesion
    ):
        lote = _lote(campana, [_recinto(1), _recinto(2), _recinto(3)])
        antes = _foto_completa(db_sesion)
        for _ in range(3):
            assert _previsualizar(cliente, cuenta["cabeceras"], lote)["aplicada"] is False
        assert _foto_completa(db_sesion) == antes

    def test_el_plan_de_la_previsualizacion_es_el_mismo_que_devuelve_aplicar(
        self, cliente, cuenta, campana, tierra
    ):
        """Contrato T05: «el plan que devuelve es el mismo objeto que devuelve aplicar»."""
        lote = _lote(campana, [_recinto(1, geometria=CUADRADO_100_M, area_sigpac_ha=0.93)])
        previsto = _previsualizar(cliente, cuenta["cabeceras"], lote)
        aplicado = _aplicar(cliente, cuenta["cabeceras"], lote)
        # Lo único que puede cambiar es lo que dice «qué se ha escrito» y el identificador de una
        # tierra que en la previsualización todavía no existía.
        assert previsto["aplicada"] is False and aplicado["aplicada"] is True
        for campo in (
            "campana_id",
            "anio",
            "fuente",
            "recintos_en_el_lote",
            "nuevos",
            "cambiados",
            "iguales",
            "sin_forma",
            "tierras_nuevas",
            "problemas",
            "solapes",
            "diferencias_de_superficie",
        ):
            assert previsto[campo] == aplicado[campo], campo
        assert [
            {clave: valor for clave, valor in uno.items() if clave not in ("parcela_id", "tierra")}
            for uno in previsto["detalle"]
        ] == [
            {clave: valor for clave, valor in uno.items() if clave not in ("parcela_id", "tierra")}
            for uno in aplicado["detalle"]
        ]

    def test_una_previsualizacion_con_un_problema_tampoco_escribe(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Un lote con un renglón que no se puede apuntar: la previsualización lo dice y no escribe."""
        lote = _lote(campana, [_recinto(1), {"poligono": 503}])
        antes = _foto_completa(db_sesion)
        plan = _previsualizar(cliente, cuenta["cabeceras"], lote)
        assert plan["problemas"]
        assert _foto_completa(db_sesion) == antes


# ==========================================================================
# 8. Las hectáreas declaradas no se sustituyen
# ==========================================================================


class Test8LasHectareasDeclaradasNoSeSustituyen:
    def test_una_importacion_sin_la_declarada_no_se_lleva_por_delante_la_que_hay(
        self, cliente, cuenta, campana, db_sesion
    ):
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, geometria=CUADRADO_100_M, area_declarada_ha=1.75)]),
        )
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, geometria=CUADRADO_100_M, area_sigpac_ha=0.93)]),
        )
        guardada = _foto_de_las_versiones(db_sesion)[0]
        assert guardada["area_declarada_ha"] == 1.75
        assert guardada["area_sigpac_ha"] == 0.93
        # Y la calculada es un tercer número, distinto de los dos.
        assert guardada["area_geometria_ha"] not in (None, 1.75, 0.93)

    def test_la_declarada_de_una_tierra_nueva_sale_del_lote_y_no_del_sigpac(
        self, cliente, cuenta, campana, db_sesion
    ):
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [
                    _recinto(
                        1,
                        geometria=CUADRADO_100_M,
                        area_sigpac_ha=0.93,
                        area_declarada_ha=0.86,
                    )
                ],
            ),
        )
        assert plan["tierras_creadas"]
        tierra = [
            fila
            for fila in _foto_de_las_tierras(db_sesion)
            if fila["id"] == plan["tierras_creadas"][0]
        ][0]
        assert tierra["superficie_ha"] == 0.86
        assert tierra["superficie_sigpac_ha"] == 0.93

    def test_una_tierra_nueva_sin_declarada_se_queda_sin_superficie_de_cultivo(
        self, cliente, cuenta, campana, db_sesion
    ):
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, geometria=CUADRADO_100_M, area_sigpac_ha=0.93)]),
        )
        tierra = [
            fila
            for fila in _foto_de_las_tierras(db_sesion)
            if fila["id"] == plan["tierras_creadas"][0]
        ][0]
        assert tierra["superficie_ha"] is None
        assert tierra["superficie_ha"] != 0.0
        assert tierra["superficie_sigpac_ha"] == 0.93

    def test_una_importacion_que_no_menciona_un_dato_no_lo_borra(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Contrato T05 §3.3: «un campo que la entrada no trae se queda como estaba»."""
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [_recinto(1, uso_sigpac="TA", pendiente_pct=2.5, area_sigpac_ha=0.93)],
                fecha_consulta="2026-03-01",
            ),
        )
        # Se vuelve a importar el mismo recinto con otro dato: lo que no viene no se borra.
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, area_sigpac_ha=1.10)]),
        )
        guardada = _foto_de_las_versiones(db_sesion)[0]
        assert guardada["uso_sigpac"] == "TA"
        assert guardada["pendiente_pct"] == 2.5
        assert guardada["fecha_consulta"].isoformat() == "2026-03-01"
        assert guardada["area_sigpac_ha"] == 1.10

    def test_una_importacion_no_cambia_el_nombre_ni_la_superficie_de_una_tierra_que_ya_existe(
        self, cliente, cuenta, campana, db_sesion, tierra
    ):
        """Contrato T05: la versión **no toca** la ficha de la tierra que el agricultor ya tiene."""
        antes = _foto_de_las_tierras(db_sesion)
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [
                    _recinto(
                        1,
                        alias="El nombre que se inventa la fuente",
                        geometria=CUADRADO_100_M,
                        area_sigpac_ha=0.93,
                        area_declarada_ha=1.75,
                    )
                ],
            ),
        )
        assert _foto_de_las_tierras(db_sesion) == antes

    def test_una_importacion_que_no_dice_el_estado_de_revision_no_lo_borra(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Y lo mismo con el estado de revisión, que **no** está en la lista de lo que se protege.

        Contrato T05 §3.3, tal y como está escrito en el documento: «Al actualizar una versión, un
        campo que la entrada no trae se queda como estaba». Marcar un recinto como revisado es un
        dato del agricultor, y una importación posterior que cambie la superficie no puede
        devolverlo a «sin revisar» sin decirlo (no se compara, así que ni saldría en el porqué).
        """
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, estado_revision="revisado", area_sigpac_ha=0.93)]),
        )
        assert _foto_de_las_versiones(db_sesion)[0]["estado_revision"] == "revisado"
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, area_sigpac_ha=1.10)]),
        )
        guardada = _foto_de_las_versiones(db_sesion)[0]
        assert guardada["area_sigpac_ha"] == 1.10
        assert guardada["estado_revision"] == "revisado", (
            "la segunda importación no decía el estado de revisión y lo ha devuelto a sin_revisar: "
            f"el plan dice que cambió {plan['detalle'][0]['que_cambia']}"
        )


# ==========================================================================
# 9. Un recinto sin geometría entra, se dice y no se le inventa forma
# ==========================================================================


class Test9UnRecintoSinGeometriaEntraYLoDice:
    def test_un_recinto_sin_forma_entra_sale_en_la_lista_y_no_se_le_inventa_una_forma(
        self, cliente, cuenta, campana, db_sesion
    ):
        plan = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, [_recinto(1)]))
        assert (plan["versiones_creadas"], plan["sin_forma"]) == (1, 1)
        guardada = _foto_de_las_versiones(db_sesion)[0]
        assert guardada["geometria"] is None
        assert guardada["area_geometria_ha"] is None

        listadas = _versiones(cliente, cuenta["cabeceras"])
        assert len(listadas) == 1
        assert listadas[0]["tiene_forma"] is False
        assert listadas[0]["como_esta"] == textos.VERSIONES_DE_RECINTO["como_esta_sin_forma"]
        assert listadas[0]["area_geometria_ha"] is None

    def test_un_recinto_sin_forma_con_referencia_completa_entra_y_se_marca_como_sin_forma(
        self, cliente, cuenta, campana
    ):
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, area_sigpac_ha=0.93)]),
        )
        uno = plan["detalle"][0]
        assert uno["sin_forma"] is True
        assert uno["poligono_valido"] is True
        assert uno["area_sigpac_ha"] == 0.93


# ==========================================================================
# 10. El área que calcula el programa
# ==========================================================================


class Test10LaMedidaDelAreaEsLaQueEs:
    def test_un_cuadrado_de_un_kilometro_mide_cien_hectareas(self):
        """Una forma conocida, con el número que tiene que salir escrito a mano."""
        lado = 1000.0
        area = geo.area_ha(_poligono(_anillo(-5.0, 41.0, lado)))
        assert area == pytest.approx(lado * lado / 10_000.0, rel=1e-6)

    def test_dos_trozos_multiparte_suman_sus_dos_areas(self):
        """`MULTIPOLYGON` son dos trozos: el área es la suma, no la del primero."""
        area = geo.area_ha(
            _multipoligono(
                [_anillo(-5.0, 41.0, 1000.0)],
                [_anillo(-4.9, 41.05, 1000.0)],
            )
        )
        assert area == pytest.approx(200.0, rel=1e-6)

    def test_un_agujero_dentro_de_un_trozo_resta(self):
        """`POLYGON` con un anillo dentro de otro: el de dentro es un agujero y resta."""
        area = geo.area_ha(
            _poligono(_anillo(-5.0, 41.0, 1000.0), _anillo(-4.9995, 41.0005, 100.0))
        )
        assert area == pytest.approx(100.0 - 1.0, rel=1e-6)

    def test_una_isla_dentro_del_agujero_vuelve_a_sumar(self):
        # El agujero es un cuadrado de 100 m; la isla, otro de 20 m **dentro** de él.
        dentro = _metros_a_grados(-4.9995, 41.0005, 30.0, 30.0)
        area = geo.area_ha(
            _poligono(
                _anillo(-5.0, 41.0, 1000.0),
                _anillo(-4.9995, 41.0005, 100.0),
                _anillo(*dentro, 20.0),
            )
        )
        assert area == pytest.approx(100.0 - 1.0 + 0.04, rel=1e-4)

    def test_un_agujero_dentro_de_la_isla_vuelve_a_restar(self):
        """Tres niveles de anidamiento: 100 − 1 + 0,04 − 0,0016 = **99,0384 ha**.

        La regla del código es la par-impar («cuántos anillos envuelven a este»), y con anillos
        anidados y sin cruzarse —que es lo que exige un `POLYGON` válido— es exacta a cualquier
        profundidad: suma el de fuera, resta el agujero, suma la isla, resta el agujero de la isla.
        """
        agujero = _metros_a_grados(-4.9995, 41.0005, 30.0, 30.0)
        isla = _metros_a_grados(-4.9995, 41.0005, 40.0, 40.0)
        agujero_de_la_isla = _metros_a_grados(-4.9995, 41.0005, 44.0, 44.0)
        area = geo.area_ha(
            _poligono(
                _anillo(-5.0, 41.0, 1000.0),
                _anillo(-4.9995, 41.0005, 100.0),
                _anillo(*agujero, 20.0),
                _anillo(*isla, 10.0),
                _anillo(*agujero_de_la_isla, 4.0),
            )
        )
        assert area == pytest.approx(100.0 - 1.0 + 0.04 - 0.0016, rel=1e-4)

    def test_el_area_no_cambia_aunque_los_anillos_vengan_en_otro_orden(self):
        """Y lo que de verdad le importa al agricultor: el área no depende del **orden de los anillos**.

        Si cambiar el orden cambiara el número, el área dependería de cómo lo haya escrito la fuente
        que manda el lote, y el agricultor declararía hectáreas que no son. Se comprueban las seis
        permutaciones del caso de dos niveles (fuera, agujero, isla), todas tienen que dar 99,04 ha.
        """
        import itertools

        fuera = _anillo(-5.0, 41.0, 1000.0)
        agujero = _anillo(-4.9995, 41.0005, 100.0)
        dentro = _metros_a_grados(-4.9995, 41.0005, 30.0, 30.0)
        isla = _anillo(*dentro, 20.0)
        medidas = {round(geo.area_ha(_poligono(*orden)), 6) for orden in itertools.permutations(
            (fuera, agujero, isla)
        )}
        assert medidas == {99.04}, medidas

    def test_un_trozo_multiparte_con_un_agujero_en_uno_de_los_trozos(self):
        area = geo.area_ha(
            _multipoligono(
                [_anillo(-5.0, 41.0, 1000.0), _anillo(-4.9995, 41.0005, 100.0)],
                [_anillo(-4.9, 41.05, 1000.0)],
            )
        )
        assert area == pytest.approx(199.0, rel=1e-6)

    def test_el_recinto_de_ejemplo_del_sigpac_mide_lo_que_dice_el_sigpac(self):
        """La única comprobación con un dato **oficial**: el recinto de ejemplo del SIGPAC.

        El SIGPAC publica 2,7923 ha para ese recinto. El programa mide sobre un plano local, así que
        se espera un error pequeño y del mismo orden documentado (0,13 %), **no** un número cualquiera.
        """
        crudo = json.loads((RUTA_SIGPAC / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))
        recinto = crudo[0]
        medida = geo.area_ha(recinto["wkt"])
        assert medida is not None
        oficial = recinto["superficie"]
        error = abs(medida - oficial) / oficial
        assert error < 0.005, f"la medida se va un {error:.2%} de la oficial"
        assert medida == pytest.approx(2.788534, abs=1e-5)

    def test_un_punto_o_una_linea_no_tienen_area_y_no_devuelven_cero(self):
        assert geo.area_ha("POINT(-5.0 41.0)") is None
        assert geo.area_ha("LINESTRING(-5.0 41.0,-4.9 41.1)") is None
        assert geo.area_ha("") is None
        assert geo.area_ha(None) is None

    def test_el_area_de_un_recinto_importado_es_la_medida_y_no_la_que_dice_el_sigpac(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Contrato §2.1: las tres áreas son tres magnitudes y ninguna se deduce de otra."""
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [
                    _recinto(
                        1,
                        geometria=_poligono(_anillo(-5.0, 41.0, 1000.0)),
                        area_sigpac_ha=99.9,
                        area_declarada_ha=98.0,
                    )
                ],
            ),
        )
        guardada = _foto_de_las_versiones(db_sesion)[0]
        assert guardada["area_geometria_ha"] == pytest.approx(100.0, rel=1e-6)
        assert (guardada["area_sigpac_ha"], guardada["area_declarada_ha"]) == (99.9, 98.0)

    def test_dos_trozos_que_se_pisan_sin_ningun_vertice_dentro_se_dicen_como_puede(self):
        """`se_solapan` tiene tres respuestas y la del cruce es «puede», no «sí»."""
        # Una cruz: los rectángulos se tocan y ningún vértice cae dentro del otro trozo.
        horizontal = "POLYGON((-5.0 41.0,-4.0 41.0,-4.0 41.0001,-5.0 41.0001,-5.0 41.0))"
        vertical = "POLYGON((-4.5 40.5,-4.4999 40.5,-4.4999 41.5,-4.5 41.5,-4.5 40.5))"
        assert geo.se_solapan(horizontal, vertical) == geo.SOLAPE_POSIBLE
        assert geo.se_solapan(horizontal, None) == geo.SOLAPE_NO_SE

    def test_el_area_no_depende_de_hacia_donde_esten_dibujados_los_anillos(self):
        """Un recinto dibujado al revés mide lo mismo: el área no puede cambiar por el sentido."""
        horario = _poligono(_anillo(-5.0, 41.0, 1000.0))
        vertices = _anillo(-5.0, 41.0, 1000.0)
        antihorario = _poligono(
            [vertices[0], vertices[-2], vertices[-3], vertices[-4], vertices[0]]
        )
        assert geo.area_ha(horario) == pytest.approx(geo.area_ha(antihorario), rel=1e-9)
        # Y con el agujero, lo mismo.
        agujero = _anillo(-4.9995, 41.0005, 100.0)
        al_reves = [agujero[0], agujero[-2], agujero[-3], agujero[-4], agujero[0]]
        assert geo.area_ha(_poligono(vertices, agujero)) == pytest.approx(
            geo.area_ha(_poligono(vertices, al_reves)), rel=1e-9
        )


# ==========================================================================
# 11. Los textos viven en textos.py y no llevan jerga
# ==========================================================================


class Test11LosTextosVivenEnTextosPyNoLlevanJerga:
    def test_cada_texto_que_pide_una_pantalla_nueva_del_almacen_se_sirve(
        self, cliente, cuenta
    ):
        """Ninguna pantalla nueva escribe una frase por su cuenta: todas se piden a `textos.py`.

        Se sacan del propio JavaScript las claves `libro_…` que pide cada pantalla y se comprueba que
        llegan en `/api/interfaz` (dentro de `cesta`, que es el bloque que sí se sirve y que el móvil
        se guarda para abrir sin cobertura). Es el fallo que el propio `AGENTS.md` describe: «una
        pregunta que el test pinta en blanco».
        """
        servidos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"])
        assert servidos.status_code == 200, servidos.text
        cesta = servidos.json()["cesta"]
        patron = re.compile(r"\b(?:c|textos|cesta)\.(libro_[a-z0-9_]+)")
        faltan: dict[str, list[str]] = {}
        for nombre in PANTALLAS_DEL_ALMACEN:
            fuente = (PANTALLAS / nombre).read_text(encoding="utf-8")
            claves = sorted(set(patron.findall(fuente)))
            assert claves, f"{nombre} no pide ni un texto del almacén: ¿se ha leído bien?"
            sin_texto = [clave for clave in claves if clave not in cesta]
            if sin_texto:
                faltan[nombre] = sin_texto
        assert faltan == {}, f"hay textos que la pantalla pide y el servidor no sirve: {faltan}"

    def test_lo_que_contestan_las_rutas_nuevas_no_lleva_jerga(self, cliente, cuenta):
        """Ninguna respuesta nueva puede llevar jerga (palabras de mostrador)."""
        prohibidas = [palabra.lower() for palabra in textos.PALABRAS_PROHIBIDAS]
        textos_de_la_respuesta: list[str] = []
        respuesta = _recepcion(cliente, cuenta["cabeceras"])
        textos_de_la_respuesta.extend(respuesta.json().get("avisos", []))
        textos_de_la_respuesta.extend(respuesta.json().get("textos", {}).values())
        creada = respuesta.json()["recepcion"]
        textos_de_la_respuesta.append(creada.get("motivo_anulacion") or "")
        textos_de_la_respuesta.extend(
            valor for valor in _existencias(cliente, cuenta["cabeceras"])["textos"].values()
        )
        for texto in textos_de_la_respuesta:
            bajo = (texto or "").lower()
            for palabra in prohibidas:
                assert palabra not in bajo, f"«{palabra}» en «{texto}»"

    def test_el_libro_del_almacen_tiene_su_texto_y_no_uno_de_mentira(self, cliente, cuenta):
        """El 0 del libro no puede enseñarse: la frase que dice «no se sabe» tiene que existir."""
        cesta = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()["cesta"]
        assert "libro_no_se_sabe_lo_que_queda" in cesta
        assert cesta["libro_no_se_sabe_lo_que_queda"].strip()


# ==========================================================================
# 12. Las firmas y la auditoría siguen intactas
# ==========================================================================


class Test12LasFirmasYLaAuditoriaSiguenIntactas:
    def test_importar_versiones_no_cambia_la_huella_del_cuaderno(
        self, cliente, cuenta, campana, parcela, producto
    ):
        _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.8, 2.43
        )
        antes = cliente.get(
            "/api/firmas/estado", headers=cuenta["cabeceras"], params={"entidad": "cuaderno"}
        ).json()
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_recinto(1, geometria=CUADRADO_100_M, area_declarada_ha=1.0)]),
        )
        despues = cliente.get(
            "/api/firmas/estado", headers=cuenta["cabeceras"], params={"entidad": "cuaderno"}
        ).json()
        assert despues["huella"] == antes["huella"], (
            "importar un lote de recintos ha cambiado el cuaderno que se firma"
        )

    def test_mover_existencias_no_cambia_la_huella_del_cuaderno(
        self, cliente, cuenta, campana, parcela, producto
    ):
        _recepcion(cliente, cuenta["cabeceras"])
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.5, 2.0
        )
        antes = cliente.get(
            "/api/firmas/estado", headers=cuenta["cabeceras"], params={"entidad": "cuaderno"}
        ).json()
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        salida = _una_salida(
            cliente, cuenta["cabeceras"], apunte_tipo="tratamiento", apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
        )
        assert salida.status_code == 201, salida.text
        despues = cliente.get(
            "/api/firmas/estado", headers=cuenta["cabeceras"], params={"entidad": "cuaderno"}
        ).json()
        assert despues["huella"] == antes["huella"]

    def test_la_huella_de_un_apunte_no_cambia_al_sacar_de_un_lote(
        self, cliente, cuenta, campana, parcela, producto
    ):
        _recepcion(cliente, cuenta["cabeceras"])
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.5, 2.0
        )
        antes = cliente.get(
            "/api/firmas/estado",
            headers=cuenta["cabeceras"],
            params={"entidad": "tratamiento", "entidad_id": apunte["id"]},
        ).json()
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        _una_salida(
            cliente, cuenta["cabeceras"], apunte_tipo="tratamiento", apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
        )
        despues = cliente.get(
            "/api/firmas/estado",
            headers=cuenta["cabeceras"],
            params={"entidad": "tratamiento", "entidad_id": apunte["id"]},
        ).json()
        assert despues["huella"] == antes["huella"]
        assert despues["estado"] == "sin_firmar"

    def test_un_apunte_anulado_recupera_su_huella_al_anular_la_salida(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """Contrato A01: anular devuelve el producto, y el cuaderno vuelve a decir lo mismo.

        Es la prueba de que el movimiento de almacén **no toca** el apunte firmado: la huella del
        apunte es la misma antes de sacar, después de sacar y después de anular, porque lo que
        cambia nunca es el apunte.
        """
        _recepcion(cliente, cuenta["cabeceras"])
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto["id"], 0.5, 2.0
        )
        huella_antes = cliente.get(
            "/api/firmas/estado",
            headers=cuenta["cabeceras"],
            params={"entidad": "tratamiento", "entidad_id": apunte["id"]},
        ).json()["huella"]
        lote = _el_lote_de(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A")
        salida = _una_salida(
            cliente, cuenta["cabeceras"], apunte_tipo="tratamiento", apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
        ).json()["movimiento"]
        cliente.post(
            f"/api/almacen/movimientos/{salida['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no era ese envase"},
        )
        huella_despues = cliente.get(
            "/api/firmas/estado",
            headers=cuenta["cabeceras"],
            params={"entidad": "tratamiento", "entidad_id": apunte["id"]},
        ).json()["huella"]
        assert huella_despues == huella_antes
        assert _el_lote_de(
            _existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL", "4471-A"
        )["saldo"] == 5.0


# ==========================================================================
# 13. Una referencia COMPLETA que comparten varias tierras — el caso real
# ==========================================================================
#
# **Los números son los del agricultor, medidos sobre una copia de su base** (no sobre esta suite):
#
#   · 65 tierras;
#   · solo **52 referencias distintas**, porque `37-70-0-0-507-24-1` la comparten **9** tierras y
#     `37-70-0-0-507-91-3` la comparten **6**;
#   · y **ninguna** referencia a medias.
#
# La causa es legítima —el cuaderno de la Junta parte un mismo recinto en varias líneas de cultivo
# (trigo, barbecho, avena)—, pero la consecuencia es que **la referencia completa no identifica una
# tierra**. Todo lo de esta clase está montado con esa forma exacta: 65 tierras, dos referencias
# compartidas y 50 referencias únicas.
#
# Lo que se protege aquí, en una frase: **importar un recinto cuya referencia comparten nueve tierras
# no puede colgarle la versión a ninguna de ellas sin decirlo**, porque la historia del recinto
# acabaría contada en la tierra que no es.

COMPARTIDA_POR_NUEVE = (507, 24, 1)
COMPARTIDA_POR_SEIS = (507, 91, 3)
LAS_TIERRAS_DEL_AGRICULTOR = 65
SUS_REFERENCIAS_DISTINTAS = 52


def _la_referencia(poligono: int, parcela: int, recinto: int) -> str:
    return f"37-70-0-0-{poligono}-{parcela}-{recinto}"


def _un_recinto_de(poligono: int, parcela: int, recinto: int, **cambios) -> dict:
    """El recinto de esa referencia, como lo mandaría el SIGPAC o el cuaderno de la Junta."""
    return _recinto(
        recinto,
        provincia="37",
        municipio="70",
        poligono=poligono,
        numero_parcela=parcela,
        **cambios,
    )


def _la_tierra(cliente, cuenta, poligono: int, parcela: int, recinto: int, alias: str) -> dict:
    respuesta = cliente.post(
        "/api/parcelas",
        headers=cuenta["cabeceras"],
        json={
            "alias": alias,
            "ref_sigpac": _la_referencia(poligono, parcela, recinto),
            "provincia": "Salamanca",
            "municipio": "Peñaranda de Bracamonte",
            "agregado": 0,
            "zona": 0,
            "poligono": poligono,
            "numero_parcela": parcela,
            "numero_recinto": recinto,
            "superficie_ha": 1.0,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


@pytest.fixture
def nueve_tierras_con_la_misma_referencia(cliente, cuenta):
    """Las nueve tierras que comparten una referencia completa, más una suelta.

    Las nueve tienen **los mismos números** (mismo polígono, misma parcela, mismo recinto): son el
    mismo trozo del SIGPAC partido en nueve líneas de cultivo. Por eso la referencia no sirve para
    decir a cuál de las nueve pertenece un recinto que llega en un lote. La décima es de otra
    referencia, para poder comprobar que el lote no se la queda por error.
    """
    tierras = [_la_tierra(cliente, cuenta, *COMPARTIDA_POR_NUEVE, f"Trigo {n}") for n in range(1, 10)]
    tierras.append(_la_tierra(cliente, cuenta, 507, 77, 2, "La suelta"))
    assert len({tierra["ref_sigpac"] for tierra in tierras[:-1]}) == 1
    return tierras


@pytest.fixture
def finca_del_agricultor(cliente, cuenta):
    """Las 65 tierras con la forma que tienen de verdad: 52 referencias y dos compartidas.

    Se usa **solo** en las dos pruebas que necesitan la escala real (la cuenta entera y la
    comparación de la finca entera): montarla son 65 altas y eso se nota en lo que tarda la suite.
    """
    tierras = [_la_tierra(cliente, cuenta, *COMPARTIDA_POR_NUEVE, f"Trigo {n}") for n in range(1, 10)]
    tierras += [_la_tierra(cliente, cuenta, *COMPARTIDA_POR_SEIS, f"Avena {n}") for n in range(1, 7)]
    tierras += [_la_tierra(cliente, cuenta, 507, 100 + n, 1, f"Tierra {n}") for n in range(50)]
    assert len(tierras) == LAS_TIERRAS_DEL_AGRICULTOR
    assert len({tierra["ref_sigpac"] for tierra in tierras}) == SUS_REFERENCIAS_DISTINTAS
    return tierras


class Test13UnaReferenciaCompletaQueCompartenVariasTierras:
    def test_la_referencia_que_comparten_nueve_tierras_no_se_le_cuelga_a_ninguna_en_silencio(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia, db_sesion
    ):
        """Contrato: **no elegir una tierra al azar y no callarse**.

        La previsualización de un lote con esa referencia tiene que decir que hay varias tierras que
        podrían ser y no apuntar el recinto a ninguna. Si eligiera una —la primera, la última o la de
        más superficie—, la historia del recinto quedaría colgada de la tierra que no es y el
        agricultor lo leería como un dato suyo.
        """
        lote = _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)])
        plan = _previsualizar(cliente, cuenta["cabeceras"], lote)

        assert (plan["nuevos"], plan["cambiados"], plan["iguales"]) == (0, 0, 0), (
            "el recinto se le ha colgado a una de las nueve tierras sin decir cuál"
        )
        assert plan["detalle"] == []
        assert plan["tierras_nuevas"] == 0
        assert len(plan["problemas"]) == 1, plan["problemas"]
        assert "9 tierras que podrían ser" in plan["problemas"][0], plan["problemas"]
        # Y el aviso dice qué hacer, no solo que hay un problema (regla de `AGENTS.md` §3.1).
        assert "Dile al lote a qué tierra pertenece" in plan["problemas"][0]
        assert _foto_de_las_versiones(db_sesion) == []

    def test_el_aviso_de_las_nueve_dice_cuantas_son_pero_no_cuales(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia
    ):
        """El aviso dice «hay 9 tierras que podrían ser» y **no dice cuáles son**.

        Esto **no es un fallo con prueba roja**: es un hueco medido, y se apunta porque es la
        diferencia entre avisar y poder arreglarlo. El plan de importación no lleva ninguna lista de
        las tierras candidatas (ni sus identificadores ni sus nombres), así que ninguna pantalla
        puede ofrecer «elige cuál de estas nueve es» sin que se añada un campo: el agricultor solo
        puede saberlo si ya sabe cuál es. Y son **15 de sus 65 tierras** las que caen aquí.
        """
        plan = _previsualizar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)]),
        )
        assert len(plan["problemas"]) == 1
        todo_el_plan = json.dumps(plan, ensure_ascii=False)
        las_nueve = nueve_tierras_con_la_misma_referencia[:9]
        assert all(tierra["alias"] not in todo_el_plan for tierra in las_nueve), (
            "el plan sí nombra las tierras candidatas: entonces esto ya se puede arreglar desde "
            "una pantalla y hay que quitar esta nota"
        )

    def test_aplicarla_tampoco_le_cuelga_la_version_a_ninguna_de_las_nueve(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia, db_sesion
    ):
        """Aplicar es lo que escribe: tiene que escribir **cero**, no una de nueve."""
        tierras_antes = _foto_de_las_tierras(db_sesion)
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)]),
        )
        assert plan["aplicada"] is True
        assert (plan["versiones_creadas"], plan["versiones_actualizadas"]) == (0, 0)
        assert plan["tierras_creadas"] == []
        assert _foto_de_las_versiones(db_sesion) == []
        assert _foto_de_las_tierras(db_sesion) == tierras_antes, "ha tocado alguna de las 65 tierras"

    def test_aplicarla_dos_veces_no_crea_nueve_versiones_ni_una_ni_dieciocho(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia, db_sesion
    ):
        """La idempotencia con una referencia compartida: 0, no 1 y desde luego no 9 ni 18."""
        lote = _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)])
        for _ in range(3):
            plan = _aplicar(cliente, cuenta["cabeceras"], lote)
            assert plan["versiones_creadas"] == 0
        assert len(_foto_de_las_versiones(db_sesion)) == 0

    def test_la_lista_de_toda_la_finca_no_le_inventa_una_version_a_las_nueve(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia
    ):
        """`GET /api/versiones` sin `parcela_id`: las nueve siguen sin versión, y se ve."""
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)]),
        )
        assert _versiones(cliente, cuenta["cabeceras"]) == []
        for tierra in nueve_tierras_con_la_misma_referencia[:9]:
            assert _versiones(cliente, cuenta["cabeceras"], parcela_id=tierra["id"]) == []

    def test_comparar_dos_campanas_no_cuenta_las_nueve_como_si_tuvieran_recinto(
        self, cliente, cuenta, campana, crear_campana, nueve_tierras_con_la_misma_referencia
    ):
        """La comparación de la finca entera cuenta **tierras con versión**, no referencias."""
        otra = crear_campana(campana["anio"] + 1)
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)]),
        )
        comparacion = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": campana["id"], "campana_despues": otra["id"]},
        )
        assert comparacion.status_code == 200, comparacion.text
        cuerpo = comparacion.json()
        assert (cuerpo["nuevos"], cuerpo["cambiados"], cuerpo["desaparecidos"], cuerpo["iguales"]) == (
            0,
            0,
            0,
            0,
        ), "la comparación dice que hay recintos donde no se ha apuntado ninguno"
        assert cuerpo["cambios"] == []

    def test_diciendo_a_que_tierra_va_si_se_apunta_y_solo_a_esa(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia, db_sesion
    ):
        """La puerta que tiene el agricultor: decir a qué tierra pertenece el recinto.

        Es lo que convierte el aviso en algo que se puede arreglar, y lo que impide que la versión
        acabe en una tierra que no es: se apunta a la que dice el lote **y a ninguna otra**.
        """
        elegida = nueve_tierras_con_la_misma_referencia[3]
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [
                    _un_recinto_de(
                        *COMPARTIDA_POR_NUEVE, parcela_id=elegida["id"], area_sigpac_ha=0.93
                    )
                ],
            ),
        )
        assert plan["problemas"] == [], plan["problemas"]
        assert plan["versiones_creadas"] == 1
        guardadas = _foto_de_las_versiones(db_sesion)
        assert [guardada["parcela_id"] for guardada in guardadas] == [elegida["id"]]
        assert plan["detalle"][0]["tierra"] == elegida["alias"]
        # Y las otras ocho siguen sin versión, que es la verdad.
        assert _versiones(cliente, cuenta["cabeceras"]) == _versiones(
            cliente, cuenta["cabeceras"], parcela_id=elegida["id"]
        )

    def test_un_lote_con_nueve_recintos_de_la_misma_referencia_sin_decir_la_tierra(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia, db_sesion
    ):
        """El caso del cuaderno de la Junta: nueve renglones, la misma referencia y sin decir a qué
        tierra va cada uno. **Ninguno se puede apuntar, y se dice nueve veces.**"""
        recintos = [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93) for _ in range(9)]
        plan = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, recintos))
        assert plan["recintos_en_el_lote"] == 9
        assert plan["versiones_creadas"] == 0
        assert len(plan["problemas"]) == 9, plan["problemas"]
        assert _foto_de_las_versiones(db_sesion) == []

    def test_los_mismos_nueve_diciendo_a_que_tierra_va_cada_uno_entran_los_nueve(
        self, cliente, cuenta, campana, nueve_tierras_con_la_misma_referencia, db_sesion
    ):
        """Y cuando el lote sí dice a qué tierra va cada renglón, entran los nueve — y una vez."""
        recintos = [
            _un_recinto_de(*COMPARTIDA_POR_NUEVE, parcela_id=tierra["id"], area_sigpac_ha=0.93)
            for tierra in nueve_tierras_con_la_misma_referencia[:9]
        ]
        plan = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, recintos))
        assert plan["problemas"] == [], plan["problemas"]
        assert plan["versiones_creadas"] == 9
        assert len(_foto_de_las_versiones(db_sesion)) == 9

        antes = _foto_completa(db_sesion)
        segunda = _aplicar(cliente, cuenta["cabeceras"], _lote(campana, recintos))
        assert (segunda["versiones_creadas"], segunda["versiones_actualizadas"]) == (0, 0)
        assert segunda["iguales"] == 9
        assert _foto_completa(db_sesion) == antes

    def test_la_finca_entera_importa_lo_que_se_puede_y_dice_lo_que_no(
        self, cliente, cuenta, campana, finca_del_agricultor, db_sesion
    ):
        """La cuenta entera, con la forma real del agricultor: 65 tierras y 52 referencias.

        Se importa un lote con las 52 referencias (una por referencia). Lo que sale, medido:
        **50 versiones**, las dos referencias compartidas se dicen, y **15 tierras** (las 9 + las 6)
        se quedan sin versión. Ni 65 ni 52: 50. Y la segunda vez, las mismas 50.
        """
        recintos = [_un_recinto_de(507, 100 + numero, 1, area_sigpac_ha=1.0) for numero in range(50)]
        recintos.append(_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93))
        recintos.append(_un_recinto_de(*COMPARTIDA_POR_SEIS, area_sigpac_ha=1.1))
        lote = _lote(campana, recintos)

        plan = _aplicar(cliente, cuenta["cabeceras"], lote)
        assert plan["recintos_en_el_lote"] == SUS_REFERENCIAS_DISTINTAS
        assert plan["versiones_creadas"] == 50
        assert len(plan["problemas"]) == 2, plan["problemas"]
        assert len(_foto_de_las_versiones(db_sesion)) == 50

        guardadas = _foto_de_las_versiones(db_sesion)
        con_version = {guardada["parcela_id"] for guardada in guardadas}
        sin_version = [
            tierra for tierra in finca_del_agricultor if tierra["id"] not in con_version
        ]
        assert len(con_version) == 50
        assert len(sin_version) == 15, "deberían quedarse 15 tierras (9 + 6) sin versión"

        antes = _foto_completa(db_sesion)
        segunda = _aplicar(cliente, cuenta["cabeceras"], lote)
        assert segunda["versiones_creadas"] == 0
        assert segunda["iguales"] == 50
        assert len(_foto_de_las_versiones(db_sesion)) == 50
        assert _foto_completa(db_sesion) == antes

    def test_comparar_dos_campanas_de_la_finca_entera_cuenta_50_y_no_65_ni_52(
        self, cliente, cuenta, campana, crear_campana, finca_del_agricultor
    ):
        """La respuesta a «¿65, 52 o 9?»: **50**, que son las tierras con versión.

        La comparación reconoce cada recinto por **(tierra, fuente)**, así que una referencia
        compartida por nueve tierras no se cuenta ni nueve veces ni una: se cuenta **cero**, porque
        no se ha podido apuntar a ninguna.
        """
        recintos = [_un_recinto_de(507, 100 + numero, 1, area_sigpac_ha=1.0) for numero in range(50)]
        recintos.append(_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93))
        otra = crear_campana(campana["anio"] + 1)
        _aplicar(cliente, cuenta["cabeceras"], _lote(campana, recintos))

        comparacion = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": campana["id"], "campana_despues": otra["id"]},
        ).json()
        assert comparacion["desaparecidos"] == 50, comparacion["resumen"]
        assert (comparacion["nuevos"], comparacion["cambiados"], comparacion["iguales"]) == (0, 0, 0)
        assert len(comparacion["cambios"]) == 50
        assert comparacion["desaparecidos"] != LAS_TIERRAS_DEL_AGRICULTOR
        assert comparacion["desaparecidos"] != SUS_REFERENCIAS_DISTINTAS

        al_reves = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": otra["id"], "campana_despues": campana["id"]},
        ).json()
        assert al_reves["nuevos"] == 50

    def test_una_tierra_con_la_referencia_escrita_de_otra_manera_no_cuenta_como_candidata(
        self, cliente, cuenta, campana, db_sesion
    ):
        """La puerta que le queda al mismo fallo, y que **no** está medida en sus datos.

        La búsqueda mira primero el **texto** de `ref_sigpac`; si encuentra exactamente una tierra,
        enlaza con ella y **no llega a mirar los números**, así que no ve que otra tierra de la finca
        tiene los mismos números escritos de otra manera (aquí, con dos puntos). Es el mismo síntoma
        del fallo que se arregló el 02/10 a las 16:57 —la versión colgada de una tierra y las otras
        sin saberlo— por una puerta más estrecha. Aquí está **construido a mano**: si en su base las
        65 las escribió el mismo importador, todas tendrán el mismo texto y no pasa.
        """
        canonica = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": "Con la referencia de siempre",
                "ref_sigpac": _la_referencia(*COMPARTIDA_POR_NUEVE),
                "poligono": COMPARTIDA_POR_NUEVE[0],
                "numero_parcela": COMPARTIDA_POR_NUEVE[1],
                "numero_recinto": COMPARTIDA_POR_NUEVE[2],
                "superficie_ha": 1.0,
            },
        )
        assert canonica.status_code == 201, canonica.text
        con_dos_puntos = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": "El mismo trozo, escrito de otra manera",
                "ref_sigpac": "37:70:0:0:507:24:1",
                "poligono": COMPARTIDA_POR_NUEVE[0],
                "numero_parcela": COMPARTIDA_POR_NUEVE[1],
                "numero_recinto": COMPARTIDA_POR_NUEVE[2],
                "superficie_ha": 1.0,
            },
        )
        assert con_dos_puntos.status_code == 201, con_dos_puntos.text

        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)]),
        )
        candidatas = [canonica.json()["id"], con_dos_puntos.json()["id"]]
        apuntadas = [guardada["parcela_id"] for guardada in _foto_de_las_versiones(db_sesion)]
        assert apuntadas != [candidatas[0]] or plan["problemas"], (
            "hay dos tierras con los mismos números y el recinto se ha colgado de una sin decir nada: "
            f"la versión está en la tierra {apuntadas} y el plan no dice ningún problema"
        )

    def test_la_ambiguedad_se_ve_aunque_solo_una_tierra_tenga_la_referencia_escrita(
        self, cliente, cuenta, campana, db_sesion
    ):
        """**La puerta exacta por la que se colaba el fallo** (arreglada el 02/10 a las 17:22).

        Nueve tierras con los mismos números: **una** con la referencia escrita tal cual y las otras
        ocho sin ella. Si solo se mira el texto de `ref_sigpac`, sale **una** candidata y el recinto
        se le cuelga a esa sin decir nada, aunque las otras ocho sean el mismo trozo del SIGPAC. Es
        la comprobación que fija el arreglo: la búsqueda por el texto y la de los números se juntan,
        así que la respuesta es «no se sabe cuál de las nueve».
        """
        con_la_referencia = _la_tierra(
            cliente, cuenta, *COMPARTIDA_POR_NUEVE, "La que la tiene escrita"
        )
        for numero in range(8):
            respuesta = cliente.post(
                "/api/parcelas",
                headers=cuenta["cabeceras"],
                json={
                    "alias": f"Sin la referencia escrita {numero}",
                    "agregado": 0,
                    "zona": 0,
                    "poligono": COMPARTIDA_POR_NUEVE[0],
                    "numero_parcela": COMPARTIDA_POR_NUEVE[1],
                    "numero_recinto": COMPARTIDA_POR_NUEVE[2],
                    "superficie_ha": 1.0,
                },
            )
            assert respuesta.status_code == 201, respuesta.text
            assert respuesta.json()["ref_sigpac"] is None

        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=0.93)]),
        )
        assert plan["versiones_creadas"] == 0, (
            "solo una de las nueve tierras tiene la referencia escrita y el recinto se le ha colgado "
            "a ella sin decir nada"
        )
        assert len(plan["problemas"]) == 1, plan["problemas"]
        assert "9 tierras que podrían ser" in plan["problemas"][0], plan["problemas"]
        assert _foto_de_las_versiones(db_sesion) == []
        assert con_la_referencia["id"] is not None

    def test_la_referencia_catastral_tampoco_elige_una_de_las_nueve(
        self, cliente, cuenta, campana, db_sesion, nueve_tierras_con_la_misma_referencia
    ):
        """Otra puerta: la referencia del Catastro (no trae el número de recinto).

        Es una de las tres formas en las que el agricultor puede dar su referencia, así que la
        importación tiene que contestar lo mismo que con la del papel: **no se sabe cuál**.
        """
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [{"referencia": "37070A507000240000AQ", "area_sigpac_ha": 0.93}],
            ),
        )
        assert plan["versiones_creadas"] == 0
        assert len(plan["problemas"]) == 1, plan["problemas"]
        assert "tierras que podrían ser" in plan["problemas"][0], plan["problemas"]
        assert _foto_de_las_versiones(db_sesion) == []

    def test_la_referencia_del_visor_sin_el_recinto_tampoco_elige_una_de_las_nueve(
        self, cliente, cuenta, campana, db_sesion, nueve_tierras_con_la_misma_referencia
    ):
        """Y la tercera forma: los seis números del visor, sin el recinto."""
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [{"referencia": "37:70:0:0:507:24", "area_sigpac_ha": 0.93}]),
        )
        assert plan["versiones_creadas"] == 0
        assert len(plan["problemas"]) == 1, plan["problemas"]
        assert "tierras que podrían ser" in plan["problemas"][0], plan["problemas"]
        assert _foto_de_las_versiones(db_sesion) == []

    def test_mezclar_una_tierra_dicha_a_mano_con_la_referencia_compartida(
        self, cliente, cuenta, campana, db_sesion, nueve_tierras_con_la_misma_referencia
    ):
        """Mezclar `parcela_id` explícito con la referencia: cada renglón, por su camino.

        El que dice la tierra entra (y en **esa** tierra, en ninguna otra); el que solo trae la
        referencia compartida **no se cuela** aprovechando que el lote ya sabía de una tierra, y se
        dice por qué. Es la puerta que se pidió intentar.
        """
        tierras = nueve_tierras_con_la_misma_referencia
        elegida = tierras[2]
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [
                    _un_recinto_de(
                        *COMPARTIDA_POR_NUEVE, parcela_id=elegida["id"], area_sigpac_ha=0.93
                    ),
                    _un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=1.7),
                ],
            ),
        )
        assert plan["versiones_creadas"] == 1
        assert len(plan["problemas"]) == 1, plan["problemas"]
        assert "tierras que podrían ser" in plan["problemas"][0], plan["problemas"]
        guardadas = _foto_de_las_versiones(db_sesion)
        assert [guardada["parcela_id"] for guardada in guardadas] == [elegida["id"]]
        assert guardadas[0]["area_sigpac_ha"] == 0.93, (
            "la versión se ha quedado con la del renglón que no se podía apuntar"
        )
        assert [uno["parcela_id"] for uno in plan["detalle"]] == [elegida["id"]]

    def test_la_tierra_repetida_en_el_mismo_lote_se_dice_y_no_crea_dos_versiones(
        self, cliente, cuenta, campana, db_sesion, nueve_tierras_con_la_misma_referencia
    ):
        """La tierra repetida dentro del mismo lote: se dice y no se apunta dos veces.

        (Que **cuál** de los dos se guarda dependa del orden es el defecto D4, que tiene su propia
        prueba; lo que se comprueba aquí es que el segundo renglón no crea una segunda versión ni
        cuela el recinto en otra tierra.)
        """
        elegida = nueve_tierras_con_la_misma_referencia[4]
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [
                    _un_recinto_de(
                        *COMPARTIDA_POR_NUEVE, parcela_id=elegida["id"], area_sigpac_ha=0.93
                    ),
                    _un_recinto_de(*COMPARTIDA_POR_NUEVE, area_sigpac_ha=2.5),
                ],
            ),
        )
        # El segundo trae la misma referencia y el mismo número pero sin decir la tierra: es
        # ambiguo (nueve candidatas) y se dice, igual que en la prueba de arriba.
        assert plan["versiones_creadas"] == 1
        assert len(_foto_de_las_versiones(db_sesion)) == 1
        # Y repitiendo la tierra a mano en los dos renglones, el segundo se dice con R6.
        repetido = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(
                campana,
                [
                    _un_recinto_de(
                        *COMPARTIDA_POR_NUEVE, parcela_id=elegida["id"], area_sigpac_ha=0.93
                    ),
                    _un_recinto_de(
                        *COMPARTIDA_POR_NUEVE, parcela_id=elegida["id"], area_sigpac_ha=2.5
                    ),
                ],
            ),
        )
        assert repetido["versiones_creadas"] == 0
        assert repetido["problemas"], repetido["problemas"]
        assert "R6" not in repetido["problemas"][0]  # el mensaje va en castellano
        assert "dos recintos" in repetido["problemas"][0], repetido["problemas"]
        assert len(_foto_de_las_versiones(db_sesion)) == 1


# ==========================================================================
# 14. El cero de la referencia no es un hueco
# ==========================================================================
#
# Encontrado al escribir las pruebas de arriba: la clave del recinto sale **sin los ceros**.
#
#   · referencia completa de un recinto de verdad: `37-70-0-0-507-24-1`
#   · clave que guarda el programa:              `37-70---507-24-1`
#
# La causa está en una sola línea (`versiones_de_recinto.clave_del_recinto`):
# `str(numeros.get(campo) or "")`. Un `0` es falso en Python, así que el agregado y la zona —que en
# el SIGPAC valen **0** casi siempre— salen vacíos. Y peor: `0` (`«es cero»`) y `None`
# (`«no lo sé»`) acaban dando **la misma clave**, que es justo lo que `AGENTS.md` §3.3 y
# `docs/T02_VALORES_POR_DEFECTO.md` prohíben. `referencia_completa` no tiene ese fallo: comprueba
# `is None` en vez de la verdad del valor, y por eso la referencia sale bien y la clave no.


class Test14ElCeroDeLaReferenciaNoEsUnHueco:
    def test_la_clave_de_un_recinto_con_agregado_cero_se_guarda_como_su_referencia(
        self, cliente, cuenta, campana, db_sesion
    ):
        """La clave es lo que el agricultor lee para reconocer el recinto en el papel.

        Con los ceros borrados, `37-70---507-24-1` no se puede cotejar con nada: ni con el SIGPAC,
        ni con el cuaderno de la Junta, ni con el papel que tiene delante. Y es la clave de
        **todas** las versiones de su finca, porque el agregado y la zona valen 0.
        """
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _lote(campana, [_un_recinto_de(507, 24, 1, area_sigpac_ha=0.93)]),
        )
        guardada = _foto_de_las_versiones(db_sesion)[0]
        assert guardada["referencia"] == "37-70-0-0-507-24-1"
        assert guardada["clave"] == guardada["referencia"], (
            f"la clave guardada es «{guardada['clave']}» y la referencia es "
            f"«{guardada['referencia']}»: se han borrado el agregado y la zona por valer 0"
        )
        # Y es la misma clave que sale por la API y la que sale en el aviso R9.
        assert _versiones(cliente, cuenta["cabeceras"])[0]["clave"] == "37-70-0-0-507-24-1"

    def test_un_agregado_que_no_se_sabe_no_puede_dar_la_misma_clave_que_un_agregado_cero(self):
        """`None` («no lo sé») no es `0` («es cero») — tampoco en la clave del recinto.

        Dos recintos con los mismos números salvo que a uno le consta el agregado y la zona (0) y al
        otro no (None) acaban con la **misma** clave, así que el programa los toma por el mismo
        recinto. Es el defecto de T02 A2 en la puerta de al lado.
        """
        con_cero = {
            "provincia": "37",
            "municipio": "70",
            "agregado": 0,
            "zona": 0,
            "poligono": 507,
            "numero_parcela": 24,
            "numero_recinto": 1,
        }
        sin_saber = {**con_cero, "agregado": None, "zona": None}
        assert versiones.clave_del_recinto(sin_saber, None) != versiones.clave_del_recinto(
            con_cero, None
        ), (
            "un agregado que no se sabe y un agregado que vale 0 dan la misma clave: "
            f"«{versiones.clave_del_recinto(sin_saber, None)}»"
        )
