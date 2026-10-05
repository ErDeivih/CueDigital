"""El arranque en PostgreSQL: los índices que ya están no se crean otra vez.

POR QUÉ EXISTE ESTE FICHERO (02/10/2026)

`README.md:63` y `AGENTS.md:583` dicen que **la base de producción es PostgreSQL**, y
`docs/REVISION_T05_Y_T09.md:166` lo repite al hablar del defecto D2. Sin embargo **no se había probado
nunca contra un servidor de verdad**, y al probarlo por primera vez —con PostgreSQL 16, en
`scripts/sonda_postgresql.py`— salió esto:

    RuntimeError: No se han podido poner al día los índices de la base de datos
    (ix_explotaciones_nif, ix_aplicadores_explotacion_id, …)
    Detalle: (psycopg.errors.DuplicateTable) relation "ix_explotaciones_nif" already exists

**El programa no arrancaba en PostgreSQL.** Ni en la segunda vez ni en la primera: sobre una base
recién creada, `create_all` crea las tablas **con sus índices** y después `asegurar_indices` los
intentaba crear todos otra vez, porque solo leía los que ya había cuando el motor era SQLite. Su
propio docstring decía lo contrario —«en otro motor no hay forma de leer la definición guardada, así
que solo se crean los que falten por su nombre»—: la intención estaba escrita y el código no la hacía.

Estas pruebas sujetan el arreglo **sin necesidad de un servidor**: el inspector de SQLAlchemy se
sustituye por uno de mentira que dice qué índices hay, y el motor por uno que solo apunta lo que se le
manda ejecutar. La prueba del apartado 1 **falla con el código de antes** (y así se comprobó: devolvía
la lista entera de índices como «creados»), que es lo que hace que sirva de guardián.

La comprobación contra PostgreSQL de verdad es `scripts/sonda_postgresql.py`, que no se puede correr
en la suite porque necesita un servidor; se corre a mano y se apunta en el documento de seguimiento.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from sqlalchemy.dialects import postgresql

from app import database, models


class InspectorDeMentira:
    """Dice qué índices hay en cada tabla, sin base de datos ninguna."""

    def __init__(self, indices_por_tabla: dict[str, list[str]]):
        self._indices = indices_por_tabla
        self.tablas_preguntadas: list[str] = []
        self.tablas_con_indices_preguntadas: list[str] = []

    def has_table(self, nombre: str) -> bool:
        self.tablas_preguntadas.append(nombre)
        return True

    def get_indexes(self, nombre: str) -> list[dict]:
        self.tablas_con_indices_preguntadas.append(nombre)
        return [{"name": indice} for indice in self._indices.get(nombre, [])]


class MotorDeMentira:
    """Un motor que no ejecuta nada: apunta lo que le mandan.

    El dialecto **sí es el de verdad** (`postgresql.dialect()`): `asegurar_indices` compila el
    `CREATE INDEX` con él, así que un dialecto de mentira no serviría —y de hecho no sirvió: la
    primera versión de esta prueba se cayó con «no attribute 'ddl_compiler'»—. Y así lo que se
    compila es el DDL de PostgreSQL de verdad, que es lo que se quiere medir.
    """

    def __init__(self, dialecto: str = "postgresql", revienta_al_empezar: bool = False):
        self.dialect = postgresql.dialect() if dialecto == "postgresql" else None
        assert dialecto == "postgresql", "esta prueba solo tiene sentido en el otro motor"
        self.ejecutado: list[str] = []
        self.empezado = 0
        self._revienta = revienta_al_empezar

    @contextmanager
    def begin(self):
        self.empezado += 1
        if self._revienta:
            raise RuntimeError("la base ha dicho que no")

        class Conexion:
            def __init__(self, apuntes: list[str]):
                self._apuntes = apuntes

            def execute(self, sentencia):
                self._apuntes.append(str(sentencia))

        yield Conexion(self.ejecutado)


def _todos_los_indices_del_modelo() -> dict[str, list[str]]:
    """Los nombres de índice que el modelo espera, tabla por tabla. Se leen del modelo, no a mano."""
    return {
        tabla.name: [indice.name for indice in tabla.indexes if indice.name]
        for tabla in models.Base.metadata.sorted_tables
    }


@pytest.fixture
def inspector_siempre_de_mentira(monkeypatch):
    """Sustituye el inspector que usa `asegurar_indices` (`from sqlalchemy import inspect`)."""

    def _poner(indices_por_tabla: dict[str, list[str]]) -> InspectorDeMentira:
        inspector = InspectorDeMentira(indices_por_tabla)
        import sqlalchemy

        monkeypatch.setattr(sqlalchemy, "inspect", lambda _motor: inspector)
        return inspector

    return _poner


class TestLosIndicesQueYaEstanNoSeCreanOtraVez:
    """El fallo que impedía arrancar en PostgreSQL."""

    def test_con_todos_los_indices_puestos_no_hay_nada_que_hacer(self, inspector_siempre_de_mentira):
        """**Esta es la prueba del fallo.** Antes de arreglarlo, en PostgreSQL devolvía los 100 y pico
        índices como «creados» y los intentaba crear: `relation … already exists` y el programa no
        arrancaba. Ahora, si ya están todos, no se toca nada."""
        inspector = inspector_siempre_de_mentira(_todos_los_indices_del_modelo())
        motor = MotorDeMentira(dialecto="postgresql")

        creados, cambiados = database.asegurar_indices(motor)

        assert creados == [], f"no había que crear nada y ha querido crear: {creados[:5]}…"
        assert cambiados == [], f"en otro motor no se rehace ningún índice: {cambiados[:5]}…"
        assert motor.empezado == 0, "no tenía que abrir ni una transacción"
        assert motor.ejecutado == [], f"no tenía que ejecutar nada: {motor.ejecutado[:3]}"
        # Y de verdad ha mirado los índices que hay, tabla por tabla: si no preguntara, la prueba
        # pasaría por casualidad el día que alguien quite la consulta.
        assert inspector.tablas_con_indices_preguntadas, "no ha preguntado qué índices hay"

    def test_un_indice_que_falta_si_se_crea(self, inspector_siempre_de_mentira):
        """La otra mitad: una instalación a la que le falta un índice lo recibe.

        Es para lo que existe `asegurar_indices`. Si el arreglo hubiera sido «en otro motor no mires
        nada», esta prueba lo cazaría.
        """
        indices = _todos_los_indices_del_modelo()
        el_que_falta = "ix_explotaciones_nif"
        assert el_que_falta in indices["explotaciones"], "el índice de la prueba ya no existe"
        indices["explotaciones"] = [i for i in indices["explotaciones"] if i != el_que_falta]
        inspector_siempre_de_mentira(indices)
        motor = MotorDeMentira(dialecto="postgresql")

        creados, cambiados = database.asegurar_indices(motor)

        assert creados == [el_que_falta], f"se esperaba crear solo el que faltaba: {creados}"
        assert cambiados == []
        assert any(
            el_que_falta in sentencia and sentencia.upper().startswith("CREATE INDEX")
            for sentencia in motor.ejecutado
        ), f"no se ha mandado crear el índice que faltaba: {motor.ejecutado}"

    def test_el_aviso_dice_sobre_que_motor_ha_pasado(self, inspector_siempre_de_mentira):
        """El aviso de antes mandaba a cerrar «un visor de SQLite» pasara lo que pasara.

        En PostgreSQL eso no le dice nada a quien ha puesto el programa en marcha, así que el aviso
        tiene que decir sobre qué motor ha fallado y no dar por hecho que el motivo son datos
        repetidos: en este fallo el motivo era que el índice **ya estaba**.
        """
        inspector_siempre_de_mentira({})  # como si no hubiera ningún índice: hay que crearlos todos
        motor = MotorDeMentira(dialecto="postgresql", revienta_al_empezar=True)

        with pytest.raises(RuntimeError) as fallo:
            database.asegurar_indices(motor)

        texto = str(fallo.value)
        assert "postgresql" in texto, f"el aviso no dice sobre qué motor ha fallado: {texto}"
        assert "índice ya está en la base con otro nombre" in texto, (
            f"el aviso sigue dando por hecho que el motivo son datos repetidos: {texto}"
        )
        assert "se ha quedado como estaba" in texto, "el aviso tiene que decir que no queda a medias"


class TestEnSqliteSeSigueMirandoSqliteMaster:
    """Que el arreglo no haya cambiado lo que ya funcionaba en el motor de David."""

    def test_una_base_recien_creada_no_necesita_tocar_indices(self, tmp_path):
        motor = database.crear_engine(f"sqlite:///{(tmp_path / 'recien.db').as_posix()}")
        try:
            database.crear_tablas(motor)
            assert database.asegurar_indices(motor) == ([], [])
            # Y repetirlo tampoco hace nada: es lo que pasa en cada arranque del programa.
            assert database.asegurar_indices(motor) == ([], [])
        finally:
            motor.dispose()

    def test_en_sqlite_si_se_rehace_un_indice_cuya_definicion_cambio(self, tmp_path):
        """La capacidad que **solo** tiene SQLite (leer la definición guardada) sigue en pie."""
        import sqlite3

        ruta = tmp_path / "definicion_vieja.db"
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        try:
            database.crear_tablas(motor)
            with sqlite3.connect(str(ruta)) as cruda:
                cruda.execute("DROP INDEX ix_explotaciones_nif")
                cruda.execute("CREATE INDEX ix_explotaciones_nif ON explotaciones (id)")
                cruda.commit()

            creados, cambiados = database.asegurar_indices(motor)

            assert cambiados == ["ix_explotaciones_nif"], (
                f"el índice con la definición cambiada tenía que rehacerse: {cambiados}"
            )
            assert creados == []
        finally:
            motor.dispose()
