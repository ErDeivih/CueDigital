"""La migración del reenvío de facturas, **ensayada sobre una copia con la forma vieja** (09/10/2026).

**Por qué existe.** El 09/10/2026 cambió la regla de la clave de reenvío de las facturas, a petición de
David, y el cambio toca **datos que ya existen** en cualquier instalación:

  · Antes el índice único **excluía las anuladas** (`WHERE anulada = 0`), así que una instalación puede
    tener perfectamente **dos facturas con la misma clave** —una viva y otra anulada—. Con el índice nuevo
    (único siempre) esas filas **no lo cumplen**, y `asegurar_indices` no puede crearlo: el programa **no
    arrancaría**. Hay que resolverlo antes, y sin borrar nada.
  · Y las facturas de antes **no tienen huella del comando**, que es lo que ahora distingue el reenvío de
    siempre de otra petición con la misma clave.

Lo que se exige aquí, y es lo que pidió David con «ensayar la migración sobre copia y conservar los
históricos»:

  1. **No se pierde ni una fila** y no se toca ningún dato del papel: la anulada sigue anulada con su
     motivo, y la viva con sus números.
  2. La clave se queda en **la factura más antigua** de cada petición (la que la atendió) y las demás la
     sueltan, que es lo que permite crear el índice nuevo.
  3. Las huellas que faltan **se rellenan** con lo que cada factura dice hoy.
  4. Y después de la migración, el índice único **muerde**: dos veces la misma clave ya no entra, ni
     siquiera con una anulada por medio.

La copia se monta aquí a mano, con la forma vieja de verdad (el índice con su `WHERE`), porque es lo que
tiene una instalación que viene de antes.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app import database, servicios


def _una_copia_con_la_forma_vieja(ruta) -> "object":
    """Una base con facturas y el índice de antes (el que excluía las anuladas)."""
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "CREATE TABLE facturas ("
                "id INTEGER PRIMARY KEY, explotacion_id INTEGER, campana_id INTEGER, "
                "fecha DATE, proveedor VARCHAR(200), proveedor_nif VARCHAR(20), "
                "numero_factura VARCHAR(80), base_imponible FLOAT, cuota_iva FLOAT, "
                "tipo_iva_pct FLOAT, total FLOAT, notas TEXT, leida_por VARCHAR(20), "
                "huella VARCHAR(64), clave_de_reenvio VARCHAR(120), "
                "fichero_nombre VARCHAR(200), fichero_ruta VARCHAR(300), "
                "fichero_tipo VARCHAR(120), fichero_bytes INTEGER, "
                "anulada BOOLEAN, motivo_anulacion TEXT, creada_en DATETIME)"
            )
        )
        conexion.execute(
            text(
                "CREATE TABLE lineas_de_factura ("
                "id INTEGER PRIMARY KEY, explotacion_id INTEGER, factura_id INTEGER, "
                "descripcion VARCHAR(200), cantidad FLOAT, unidad VARCHAR(20), "
                "precio_unitario FLOAT, importe FLOAT, numero_registro VARCHAR(40), "
                "lote VARCHAR(60), producto_id INTEGER, fertilizante_id INTEGER)"
            )
        )
        # **El índice de antes**, tal cual: único solo entre las vivas.
        conexion.execute(
            text(
                "CREATE UNIQUE INDEX uq_factura_reenvio ON facturas "
                "(explotacion_id, clave_de_reenvio) WHERE anulada = 0"
            )
        )
        # Dos facturas con la MISMA clave: una viva y otra anulada. Es lo que la regla vieja permitía.
        conexion.execute(
            text(
                "INSERT INTO facturas (id, explotacion_id, fecha, proveedor, proveedor_nif, "
                "numero_factura, base_imponible, cuota_iva, tipo_iva_pct, total, "
                "clave_de_reenvio, anulada, motivo_anulacion) VALUES "
                "(1, 1, '2026-03-15', 'COOPERATIVA', 'F37012345', '2026/00123', "
                " 170.0, 35.7, 21.0, 205.7, 'peticion-vieja', 0, NULL), "
                "(2, 1, '2026-03-15', 'COOPERATIVA', 'F37012345', '2026/00123', "
                " 170.0, 35.7, 21.0, 205.7, 'peticion-vieja', 1, 'me equivoqué'), "
                "(3, 1, '2026-03-16', 'OTRO PROVEEDOR', NULL, 'B-9', "
                " 100.0, 21.0, 21.0, 121.0, 'peticion-sola', 0, NULL)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO lineas_de_factura (id, explotacion_id, factura_id, descripcion, "
                "cantidad, unidad, precio_unitario, importe) VALUES "
                "(1, 1, 1, 'GLIFOSATO', 5.0, 'L', 34.0, 170.0), "
                "(2, 1, 3, 'ABONO', 500.0, 'kg', 0.2, 100.0)"
            )
        )
    return motor


def _el_indice(motor) -> str:
    with motor.connect() as conexion:
        for nombre, sql in conexion.execute(
            text("SELECT name, sql FROM sqlite_master WHERE type = 'index' AND name = 'uq_factura_reenvio'")
        ):
            return sql or ""
    return ""


def _las_facturas(motor) -> list[dict]:
    with motor.connect() as conexion:
        return [
            dict(fila)
            for fila in conexion.execute(
                text(
                    "SELECT id, clave_de_reenvio, anulada, motivo_anulacion, total, "
                    "huella_de_la_peticion FROM facturas ORDER BY id"
                )
            ).mappings()
        ]


def test_la_migracion_resuelve_las_claves_repetidas_sin_perder_una_fila(tmp_path):
    """Dos facturas con la misma clave (una anulada): la clave se queda en la antigua, y no se borra nada.

    Sin esto, el índice nuevo no se puede crear y **el programa no arranca** —y el mensaje que daría
    hablaría de «datos repetidos», sin decir de qué—.
    """
    motor = _una_copia_con_la_forma_vieja(tmp_path / "vieja.db")
    # **En el orden del arranque** (`crear_tablas`): primero las columnas que falten y después los datos.
    # La copia vieja no tiene `huella_de_la_peticion`, que es lo que le pasa a una instalación de antes.
    database.asegurar_columnas(motor)
    antes = _las_facturas(motor)
    assert len(antes) == 3, "la copia de partida tiene que tener tres facturas"

    sueltas, rellenadas = database.rellenar_la_huella_del_comando(motor)

    despues = _las_facturas(motor)
    assert len(despues) == 3, "la migración no puede perder ni una fila"
    assert sueltas == 1, f"tenía que soltar una clave repetida, soltó {sueltas}"
    assert rellenadas == 2, f"tenía que rellenar dos huellas (las de clave), rellenó {rellenadas}"

    # **La clave se queda en la más antigua** (id 1) y la anulada la suelta.
    por_id = {fila["id"]: fila for fila in despues}
    assert por_id[1]["clave_de_reenvio"] == "peticion-vieja"
    assert por_id[2]["clave_de_reenvio"] is None
    assert por_id[3]["clave_de_reenvio"] == "peticion-sola"
    # Y **la anulada sigue anulada con su motivo**: se le ha quitado una clave, no su historia.
    assert por_id[2]["anulada"] == 1
    assert por_id[2]["motivo_anulacion"] == "me equivoqué"
    assert por_id[1]["total"] == antes[0]["total"], "no se toca ningún dato del papel"

    # Y las huellas: la de la factura viva coincide con **la de su contenido**, que es lo que permite
    # reconocer su reenvío después de migrar.
    with motor.connect() as conexion:
        la_factura = conexion.execute(
            text("SELECT * FROM facturas WHERE id = 1")
        ).mappings().first()
        sus_lineas = conexion.execute(
            text("SELECT * FROM lineas_de_factura WHERE factura_id = 1 ORDER BY id")
        ).mappings().all()
    assert por_id[1]["huella_de_la_peticion"] == servicios.la_huella_de_una_factura_guardada(
        la_factura, sus_lineas
    )


def test_despues_de_migrar_el_indice_nuevo_se_crea_y_muerde(tmp_path):
    """Y la migración deja la base en condiciones: `crear_tablas` crea el índice nuevo y ya no pasa nadie.

    Es el final del camino: si esto no se cumpliera, la migración sería un arreglo a medias —el índice
    seguiría excluyendo las anuladas y el reenvío de un comando anulado volvería a crear otra factura—.
    """
    motor = _una_copia_con_la_forma_vieja(tmp_path / "vieja.db")
    assert "WHERE anulada = 0" in _el_indice(motor), (
        "la copia tiene que empezar con el índice viejo, o esta prueba no prueba nada"
    )

    database.crear_tablas(motor)

    el_nuevo = _el_indice(motor)
    assert "WHERE" not in el_nuevo.upper(), f"el índice sigue siendo parcial: {el_nuevo}"
    assert "uq_factura_reenvio" in el_nuevo

    # Y muerde **también con una anulada por medio**: es la regla nueva.
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "INSERT INTO facturas (id, explotacion_id, clave_de_reenvio, anulada) "
                "VALUES (10, 1, 'peticion-nueva', 1)"
            )
        )
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    "INSERT INTO facturas (id, explotacion_id, clave_de_reenvio, anulada) "
                    "VALUES (11, 1, 'peticion-nueva', 0)"
                )
            )


def test_la_migracion_se_puede_correr_dos_veces(tmp_path):
    """Como todas las del arranque: la segunda pasada **no hace nada** y no rompe nada.

    El programa llama a esto en cada arranque, así que una migración que no fuera idempotente estaría
    tocando datos cada vez que alguien abre la aplicación.
    """
    motor = _una_copia_con_la_forma_vieja(tmp_path / "vieja.db")
    database.asegurar_columnas(motor)
    database.rellenar_la_huella_del_comando(motor)
    las_huellas = {fila["id"]: fila["huella_de_la_peticion"] for fila in _las_facturas(motor)}

    sueltas, rellenadas = database.rellenar_la_huella_del_comando(motor)

    assert (sueltas, rellenadas) == (0, 0), "la segunda pasada no tiene nada que hacer"
    assert {fila["id"]: fila["huella_de_la_peticion"] for fila in _las_facturas(motor)} == las_huellas
