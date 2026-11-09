"""**Los booleanos del modelo y PostgreSQL**: el DDL no puede llevar `DEFAULT 1` (09/11/2026).

EL FALLO QUE CIERRA ESTE TEST
=============================

Encontrado al arrancar la imagen de producción contra un PostgreSQL 16 de verdad (prueba del
despliegue del 09/11/2026), con una base nueva:

    sqlalchemy.exc.ProgrammingError: (psycopg.errors.DatatypeMismatch)
    column "puede_modificar" is of type boolean but default expression is of type integer
    HINT: You will need to rewrite or cast the expression.
    [SQL: CREATE TABLE accesos_a_fincas (... puede_modificar BOOLEAN DEFAULT 1 NOT NULL ...)]
    ERROR: Application startup failed. Exiting.

`mapped_column(Boolean, server_default=text("1"))` en SQLite es un entero y no pasa nada; en
PostgreSQL el valor por defecto de un `boolean` **tiene que ser `true` o `false`**. La base no
se crea y la aplicación muere al arrancar, así que es un bloqueo de producción, no un aviso.

CÓMO SE COMPRUEBA, Y POR QUÉ ASÍ
===============================

**Sin servidor y sin base de datos**: se compila el mismo `CREATE TABLE` que emitiría
SQLAlchemy con el dialecto de PostgreSQL (`sqlalchemy.dialects.postgresql.dialect()`) y se
recorre **todas** las tablas del modelo. Así el test no depende de que haya un PostgreSQL
levantado (un test que necesita un servicio de fuera es una lotería) y caza la próxima columna
booleana que alguien añada con un `DEFAULT 1`, no solo las dos que se arreglaron.

El segundo test crea el esquema en un SQLite en memoria: el arreglo tiene que servir para los
dos motores, porque la instalación de desarrollo y la suite siguen siendo SQLite.
"""

from __future__ import annotations

import re

from sqlalchemy import Boolean, Column, MetaData, Table, create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app import database, models

# `BOOLEAN DEFAULT 1`, `BOOLEAN DEFAULT 0` y también `BOOLEAN DEFAULT '1'`: las tres formas en
# las que un valor por defecto entero se cuela en una columna booleana.
_DEFAULT_ENTERO_EN_UN_BOOLEANO = re.compile(
    r"\bBOOLEAN\s+DEFAULT\s+'?([01])'?(?=[\s,)]|$)", re.IGNORECASE
)


def _los_defaults_enteros_en_booleanos(dialecto) -> list[str]:
    """Las columnas booleanas cuyo `CREATE TABLE` sale con `DEFAULT 1` o `DEFAULT 0`."""
    culpables: list[str] = []
    for tabla in models.Base.metadata.sorted_tables:
        ddl = str(CreateTable(tabla).compile(dialect=dialecto))
        for coincidencia in _DEFAULT_ENTERO_EN_UN_BOOLEANO.finditer(ddl):
            culpables.append(f"{tabla.name}: {coincidencia.group(0)}")
    return culpables


class TestLosBooleanosEnPostgreSQL:
    def test_el_create_table_de_postgresql_no_lleva_default_entero_en_ningun_booleano(self):
        culpables = _los_defaults_enteros_en_booleanos(postgresql.dialect())
        assert not culpables, (
            "En PostgreSQL el valor por defecto de un boolean tiene que ser true/false; "
            "con un 1 o un 0 la base no se crea y la aplicación no arranca. "
            "Columnas culpables: " + ", ".join(culpables)
        )

    def test_las_dos_capacidades_de_acceso_nacen_en_verdadero(self):
        """Las dos columnas que rompieron el arranque, miradas por su nombre.

        El test anterior las habría cazado, pero este dice **cuál** es el valor que tienen que
        llevar, para que el mensaje del día que se rompa no deje dudas.
        """
        tabla = models.Base.metadata.tables["accesos_a_fincas"]
        for nombre in ("puede_modificar", "puede_ver_lo_economico"):
            columna = tabla.columns[nombre]
            assert columna.server_default is not None, f"{nombre} se ha quedado sin valor por defecto"
            defecto = str(getattr(columna.server_default, "arg", columna.server_default)).strip().lower()
            assert defecto == "true", (
                f"{nombre} tiene «{defecto}»; en PostgreSQL tiene que ser «true» "
                "(«1» no vale para un boolean)"
            )

    def test_sqlite_sigue_creando_el_mismo_esquema(self):
        """El arreglo no puede romper el motor de desarrollo: `DEFAULT true` también vale ahí.

        Se crea el esquema entero en un SQLite en memoria. Si la versión de SQLite del entorno
        no admitiera `DEFAULT true`, este test se pondría rojo aquí y no al arrancar la suite.
        """
        motor = create_engine("sqlite://")
        try:
            models.Base.metadata.create_all(bind=motor)
            with motor.connect() as conexion:
                filas = conexion.exec_driver_sql(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
                ).scalar()
            assert filas and filas > 60, f"el esquema de SQLite se ha quedado en {filas} tablas"
        finally:
            motor.dispose()


def _el_alter_que_emitiria_asegurar_columnas(columna) -> str:
    """El `ALTER TABLE ... ADD COLUMN` que pondría al día una base ya existente.

    Se arma con las mismas tres piezas que `database.asegurar_columnas` (el tipo compilado con
    el dialecto, `_valor_por_defecto` y la plantilla de la sentencia), sin base de datos: así se
    puede comprobar el SQL **sin un PostgreSQL levantado**, que es lo que hace falta para que
    esto sea un test y no una lotería.
    """
    dialecto = postgresql.dialect()
    tipo = columna.type.compile(dialect=dialecto)
    defecto = database._valor_por_defecto(columna)
    sentencia = f'ALTER TABLE "prueba" ADD COLUMN "{columna.name}" {tipo}'
    if defecto is not None:
        sentencia += f" DEFAULT {defecto}"
    return sentencia


class TestLaPuestaAlDiaEnPostgreSQL:
    """La otra mitad del mismo fallo: `asegurar_columnas` pone al día una base que ya existe.

    En SQLite una columna booleana es un entero y `DEFAULT 1` vale; en PostgreSQL es un
    `boolean` y `DEFAULT 1` aborta el `ALTER TABLE`. Y ese error **no se ve**: `asegurar_columnas`
    lo apunta en `imposibles` y sigue, así que la aplicación arranca y la columna **no existe**;
    el fallo aparece después, al consultarla (un «no such column» delante del agricultor).
    """

    def _una_columna_booleana(self, por_defecto_en_python: bool) -> Column:
        tabla = Table("prueba", MetaData(), Column("booleana", Boolean, default=por_defecto_en_python))
        return tabla.columns["booleana"]

    def test_el_alter_de_postgresql_no_pone_default_entero_a_un_booleano(self):
        for valor in (True, False):
            sentencia = _el_alter_que_emitiria_asegurar_columnas(self._una_columna_booleana(valor))
            assert "DEFAULT 1" not in sentencia and "DEFAULT 0" not in sentencia, (
                "En PostgreSQL un boolean no admite DEFAULT 1/0: hay que decir TRUE/FALSE. "
                f"La sentencia era: {sentencia}"
            )
            esperado = "TRUE" if valor else "FALSE"
            assert f"DEFAULT {esperado}" in sentencia, (
                f"la columna tiene que nacer con DEFAULT {esperado}; salió: {sentencia}"
            )

    def test_una_columna_booleana_del_modelo_tambien_sale_bien(self):
        """No solo la columna inventada del test: una del modelo con `default=True` de Python."""
        columna = models.Base.metadata.tables["usuarios"].columns["activo"]
        sentencia = _el_alter_que_emitiria_asegurar_columnas(columna)
        assert "DEFAULT 1" not in sentencia and "DEFAULT 0" not in sentencia, sentencia
        assert "DEFAULT TRUE" in sentencia, sentencia

    def test_el_valor_por_defecto_de_un_booleano_es_la_palabra(self):
        """`_valor_por_defecto` es la función que decide el SQL: el booleano se dice con palabra."""
        for valor, esperado in ((True, "TRUE"), (False, "FALSE")):
            defecto = database._valor_por_defecto(self._una_columna_booleana(valor))
            assert defecto == esperado, f"para {valor} devolvió «{defecto}», no «{esperado}»"
