"""La clave ajena que le faltaba a `ventas_de_cosecha` (14/10/2026).

POR QUÉ. El inventario que se hizo para la fusión lo midió y lo reprodujo: en la base del agricultor,
`ventas_de_cosecha.contacto_id` **no tiene clave ajena**. En una base nueva sí; en la migrada no, porque
`asegurar_columnas` usa `ALTER TABLE ADD COLUMN` —y SQLite **no puede añadir una clave ajena así**—. De las seis
columnas de dinero que una fusión tendría que repuntar, es **la única cuyo error no caza la base**: una venta puede
quedarse apuntando a una ficha que no existe, en silencio.

**Qué se prueba aquí, y qué no.** Se prueba **lo que es de esta herramienta**: que sabe **mirar** qué claves ajenas
faltan (leyendo `PRAGMA foreign_key_list`, que da la columna local en el índice 3 y no en el 2) y que en una base
sana **no tiene nada que hacer** — que es lo que decide si hay que tocar la base del agricultor y lo que hace que se
pueda llamar en cada arranque sin miedo.

**Lo que NO se prueba aquí, y por qué** (medido, 14/10/2026): el trozo que reconstruye la tabla es
`_reconstruir_tabla`, que es **de la casa** y ya tiene sus pruebas en la migración de las columnas. Y **simular aquí
una base migrada destrozando la tabla en su sitio no se puede**: `CREATE TABLE … AS SELECT` copia las filas pero
**pierde la clave primaria**, y hay otras tablas que apuntan a `ventas_de_cosecha` (`lineas_de_factura_emitida`), así
que la base se queda con un `foreign key mismatch` y **el desmontaje de la propia prueba revienta**. Lo intenté y es
lo que pasó; queda dicho aquí para que nadie lo repita. Lo que eso sí demuestra es que la reconstrucción de la casa
**no** tiene ese problema: construye la tabla **con el esquema del modelo**, con su clave primaria, y copia las filas.
"""

from __future__ import annotations

from app import database


def _las_claves_ajenas(motor, tabla: str) -> set[str]:
    """Las columnas de esa tabla que HOY tienen clave ajena en la base.

    `PRAGMA foreign_key_list` da la tabla referenciada en el índice **2** y **la columna local en el 3**. La primera
    vez leí el 2, así que comparaba nombres de columna contra nombres de tabla, la resta salía siempre con algo y la
    tabla se habría reconstruido **en cada arranque** — lo contrario de lo que hace falta.
    """
    with motor.connect() as conexion:
        return {fila[3] for fila in conexion.exec_driver_sql(f'PRAGMA foreign_key_list("{tabla}")')}


def test_en_una_base_sana_no_falta_ninguna_clave(base_creada, db_sesion):
    """**De partida no falta nada.** Es lo que decide si hay que tocar la base del agricultor."""
    motor = db_sesion.get_bind()
    assert "contacto_id" in _las_claves_ajenas(motor, "ventas_de_cosecha"), (
        "el modelo declara esa clave ajena: en una base recién creada tiene que estar"
    )
    assert database.las_claves_ajenas_que_faltan(motor, "ventas_de_cosecha") == set(), "y entonces no falta ninguna"
    # Y las otras tablas con dinero de un contacto, que sí están protegidas en la base del agricultor.
    for tabla in ("tareas", "gastos"):
        assert database.las_claves_ajenas_que_faltan(motor, tabla) == set(), f"a {tabla} tampoco le falta nada"


def test_la_herramienta_no_tiene_nada_que_hacer_y_no_toca_la_base(base_creada, db_sesion):
    """**Idempotente de verdad**: con la clave puesta, no reconstruye nada.

    Es lo que hace que esto se pueda llamar en **cada arranque** sin miedo: `crear_tablas` corre todas las veces, y a
    partir de la segunda no puede hacer nada. Si esta prueba no pasara, el programa reconstruiría tablas del
    agricultor en cada arranque — justo lo que no se puede permitir.
    """
    motor = db_sesion.get_bind()
    antes = _las_claves_ajenas(motor, "ventas_de_cosecha")
    assert database.reconstruir_para_que_nazcan_las_claves_ajenas(motor) == [], "no hay nada que reconstruir"
    assert database.reconstruir_para_que_nazcan_las_claves_ajenas(motor) == [], "ni la segunda vez"
    assert _las_claves_ajenas(motor, "ventas_de_cosecha") == antes, "y el esquema sigue exactamente igual"
