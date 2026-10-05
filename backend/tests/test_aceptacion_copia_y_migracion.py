"""Aceptación de la copia que se hace antes de reconstruir tablas.

**Qué es esto.** Pruebas de aceptación escritas por un revisor **independiente**, desde cero, para
intentar romper —no para confirmar— la entrega del 02/10/2026: `_copia_de_seguridad_del_fichero` y
sus ayudantes (`app/database.py`), su uso en `reconstruir_para_poder_decir_no_se` y en
`scripts/migrar_zona_de_nitratos.py`.

No repiten lo que ya cubre `tests/test_zona_de_nitratos_no_comprobado.py` (del coordinador, que no se
toca). Lo que se comprueba aquí, y que allí no está:

1. Que la copia con cambios confirmados en el WAL lleva esas filas, **y que la comprobación de
   entereza (`quick_check`) por sí sola no las echaría de menos**: una copia del fichero principal
   hecha a mano pasa `quick_check` y pierde datos.
2. La **vuelta atrás de verdad**: qué pasa cuando se restaura la copia y hay un `-wal` al lado, que
   es justo el caso para el que se escribió la copia coherente. Aquí está el defecto que se ha
   encontrado, con la medida delante (ver `TestLaVueltaAtras`).
3. Que cuando la copia no se puede comprobar **no se reconstruye ninguna tabla**, provocado de dos
   formas: una de verdad (el nombre de la copia está ocupado y no se puede ni crear) y las dos
   comprobaciones concretas (parcheadas, y **se dice** que van parcheadas, porque provocarlas de
   verdad no está al alcance de una prueba: ver el comentario de cada una).
4. La copia con una **base realista**: las 26 tablas del modelo, no una tabla de dos columnas.
5. Los **caminos en los que se reconstruye sin copia válida**: base en memoria y PostgreSQL.
6. El **guion de migración**, ejecutado entero: la copia que deja, el aviso en cristiano y —esto es
   un defecto— que nunca cambia ni una fila (ver `test_el_guion_dice_que_hay_apuntes_que_cambiar...`).

**Lo que NO se ha podido comprobar aquí** (está contado en `docs/ACEPTACION_COPIA_Y_MIGRACION.md`):
un disco lleno, PostgreSQL de verdad, y una carpeta en la que no se pueda escribir.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import os
import pathlib
import shutil
import sqlite3
import sys

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateTable

from app import database, models

RAIZ_BACKEND = pathlib.Path(__file__).resolve().parents[1]
GUION_DE_MIGRACION = RAIZ_BACKEND / "scripts" / "migrar_zona_de_nitratos.py"

# La plantilla del esquema de una instalación vieja, creada una vez por módulo. Ver
# `_motor_con_las_columnas_todavia_obligatorias`.
_PLANTILLA: dict[str, pathlib.Path] = {}


@pytest.fixture(scope="module", autouse=True)
def _plantilla_del_esquema_viejo(tmp_path_factory):
    """Crea el esquema de una instalación vieja **una vez** para todas las pruebas del fichero."""
    carpeta = tmp_path_factory.mktemp("instalacion_vieja")
    ruta = carpeta / "plantilla.db"
    motor = _crear_el_esquema_de_una_instalacion_vieja(ruta)
    motor.dispose()
    _PLANTILLA["ruta"] = ruta
    yield
    _PLANTILLA.clear()


# --------------------------------------------------------------------------
# Herramientas de las pruebas
# --------------------------------------------------------------------------


def _motor_con_las_columnas_todavia_obligatorias(ruta: pathlib.Path):
    """Una base como la de una instalación de antes: **las 26 tablas del modelo**, con las columnas
    de `COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS` otra vez `NOT NULL`.

    Las columnas se sacan de la lista del programa, no de una copia escrita a mano: si mañana se
    añade una columna a esa lista, esta prueba la incluye sola. El `NOT NULL` se le devuelve al DDL
    que genera el modelo, así que la tabla sigue siendo la de verdad (con sus columnas, sus índices
    y sus claves foráneas); lo único que cambia es lo que cambia entre una instalación vieja y una
    nueva.

    **El esquema se crea UNA vez por módulo** y cada prueba trabaja sobre una copia del fichero. Son
    26 tablas y unos 400 ms de reloj por creación: hacerlo en cada prueba sería poner la suite lenta,
    y `AGENTS.md` avisa de que una suite lenta se deja de ejecutar. Si la plantilla no está (por
    ejemplo, si alguien llama a esta función fuera de pytest), se crea igual.
    """
    plantilla = _PLANTILLA.get("ruta")
    if plantilla is not None:
        shutil.copy2(plantilla, ruta)
        return create_engine(f"sqlite:///{ruta.as_posix()}")
    return _crear_el_esquema_de_una_instalacion_vieja(ruta)


def _crear_el_esquema_de_una_instalacion_vieja(ruta: pathlib.Path):
    """El esquema de las 26 tablas del modelo, con las columnas de la lista otra vez obligatorias.

    **El tipo se saca del modelo, no se escribe a mano.** Estaba fijado en `BOOLEAN`, y la lista creció con
    columnas que no lo son (`fertilizaciones.riqueza_n` es `FLOAT`, `parcelas.superficie_ha` también), así que
    la prueba se caía con «el modelo ya no la escribe así». Se lee el tipo de la columna del modelo y se
    quita el `NOT NULL` de **esa** columna, que es lo que de verdad describe una instalación vieja.
    """
    motor = create_engine(f"sqlite:///{ruta.as_posix()}")
    por_tabla: dict[str, list[str]] = {}
    for tabla, columna in database.COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS:
        por_tabla.setdefault(tabla, []).append(columna)
    for tabla, columnas in por_tabla.items():
        tabla_del_modelo = models.Base.metadata.tables[tabla]
        ddl = str(CreateTable(tabla_del_modelo).compile(dialect=motor.dialect))
        for columna in columnas:
            tipo = str(tabla_del_modelo.columns[columna].type.compile(dialect=motor.dialect)).upper()
            ddl = ddl.replace(f"{columna} {tipo},", f"{columna} {tipo} NOT NULL,")
            assert f"{columna} {tipo} NOT NULL" in ddl, (
                f"la prueba necesita «{tabla}.{columna}» obligatoria y el modelo ya no la escribe así"
            )
        with motor.begin() as conexion:
            conexion.execute(text(ddl))
    # Y todas las demás tablas del modelo: una base realista, no un banco de pruebas de juguete.
    models.Base.metadata.create_all(motor)
    return motor


def _meter_una_finca_de_verdad(motor, *, la_tierra_sabe_si_esta_en_zona: bool | None = None) -> None:
    """Una finca con su campaña, su tierra, su producto, su abono y su tratamiento.

    Los datos son los de un agricultor cualquiera (2,43 ha en Peñaranda), no ceros de relleno: lo
    que se comprueba después es si la migración mueve **alguna** fila, y para eso hacen falta filas.
    """
    with motor.begin() as conexion:
        conexion.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conexion.execute(models.Explotacion.__table__.insert().values(
            id=1, nombre="David Pérez Velasco", nif="70922320A",
            provincia="Salamanca", municipio="Peñaranda de Bracamonte",
            # **El valor que el programa ponía solo, y que la migración tiene que poder cambiar** (A13,
            # 05/10/2026). Antes se omitía esta columna y la rellenaba el valor por defecto del modelo
            # (`False`); ahora el modelo **no tiene defecto a propósito** —nadie debe recibir un «no soy
            # ecológico» que no ha dicho—, así que la instalación vieja tiene que decir lo que de verdad
            # tenía: en una base antigua esta columna es `NOT NULL` y valía `0`, porque el programa lo
            # escribía él. Es lo mismo que ya se hace unas líneas más abajo con `autorizado=0` y
            # `permitido_ecologico=0`, y por el mismo motivo.
            produccion_ecologica=0,
        ))
        conexion.execute(models.Campana.__table__.insert().values(
            id=1, explotacion_id=1, anio=2026,
            fecha_inicio=dt.date(2025, 10, 1), fecha_fin=dt.date(2026, 9, 30),
        ))
        conexion.execute(models.Parcela.__table__.insert().values(
            id=1, explotacion_id=1, alias="La Vega", provincia="Salamanca",
            municipio="Peñaranda de Bracamonte", superficie_ha=2.43,
            zona_vulnerable_nitratos=la_tierra_sabe_si_esta_en_zona,
            # Y aquí lo mismo (A12): en una instalación vieja las dos columnas del agua son `NOT NULL` y
            # valían `0`, porque el programa las ponía él. Es exactamente el «no» que nadie había dicho y
            # que la migración tiene que dejar pasar a «no lo sé».
            masa_agua_cerca=0, captacion_consumo_humano=0,
            # El sistema (A10, 05/10/2026): en una instalación vieja esta columna es `NOT NULL` y el
            # programa la escribía él con `"secano"` cuando nadie decía nada, así que la tierra vieja
            # tiene que decir «secano» —es lo que de verdad tenía— y la migración no la toca.
            sistema="secano",
        ))
        conexion.execute(models.ParcelaCultivo.__table__.insert().values(
            id=1, explotacion_id=1, parcela_id=1, campana_id=1, especie="Trigo blando",
            # Lo mismo que en la tierra: el cultivo de la campaña viejo decía «secano» porque lo ponía
            # el programa, no porque nadie lo hubiera declarado (A10).
            sistema="secano", superficie_cultivada_ha=2.43, fecha_inicio=dt.date(2025, 11, 1),
        ))
        conexion.execute(models.GrupoParcelas.__table__.insert().values(
            id=1, explotacion_id=1, nombre="Trigo (1 parcela)", campana_id=1,
            cultivo="Trigo blando", sistema="secano", creado_automaticamente=0,
        ))
        conexion.execute(models.EquipoAplicacion.__table__.insert().values(
            id=1, explotacion_id=1, nombre="Pulverizador del tractor", tipo="pulverizador",
            # **Y la titularidad (A11, 05/10/2026)**: una instalación vieja la tiene `NOT NULL` y valía
            # `"propia"` porque lo ponía el programa, que es justo el defecto que se arregla —la máquina
            # de otro quedaba como tuya—. La fila vieja se queda como estaba.
            titularidad="propia", numero_roma="ROMA-37070-001",
        ))
        conexion.execute(models.Fertilizante.__table__.insert().values(
            id=1, explotacion_id=1, nombre="Nitrato amónico 33,5%", tipo="mineral",
            # Las tres riquezas, como las guarda el formulario de verdad (03/10/2026): desde A6 son
            # anulables a propósito —«no consta la composición»—, y una instalación vieja tiene sus tres
            # columnas con valor (el nitrato amónico no lleva fósforo ni potasio: 0 es un dato, no un hueco).
            riqueza_n=33.5, riqueza_p=0.0, riqueza_k=0.0,
        ))
        conexion.execute(models.ProductoFitosanitario.__table__.insert().values(
            id=1, explotacion_id=1, nombre_comercial="Ejemplo 25 EC", numero_registro="24.123",
            unidad_dosis="L/ha", unidad_compra="L", autorizado=0, permitido_ecologico=0,
        ))
        conexion.execute(models.TratamientoFitosanitario.__table__.insert().values(
            id=1, explotacion_id=1, campana_id=1, parcela_id=1, fecha=dt.date(2026, 5, 1),
            tipo="parcela", superficie_tratada_ha=2.43, unidad_dosis="L/ha",
            en_zona_vulnerable=0, anulado=False,
        ))
        conexion.execute(models.RegistroFertilizacion.__table__.insert().values(
            id=1, explotacion_id=1, campana_id=1, parcela_id=1, fecha=dt.date(2026, 2, 20),
            superficie_ha=2.43, tipo="organico", kg_ha_producto=1000.0,
            # La copia de la composición y sus unidades fertilizantes, como las guarda el alta de verdad
            # (A6, 03/10/2026): en una instalación vieja estas columnas tienen valor, y con la migración
            # pasan a poder decir «no se ha podido calcular». El purín al 4 % son 40 kg de N por hectárea.
            riqueza_n=4.0, riqueza_p=0.0, riqueza_k=0.0,
            uf_n_ha=40.0, uf_p_ha=0.0, uf_k_ha=0.0,
            uf_n_total=97.2, uf_p_total=0.0, uf_k_total=0.0,
            cantidad_total_kg=2430.0, en_zona_vulnerable=1, anulado=False,
        ))


APUNTE_DE_DESPUES = (
    "INSERT INTO tratamientos (id, explotacion_id, campana_id, parcela_id, fecha, tipo, "
    "superficie_tratada_ha, unidad_dosis, en_zona_vulnerable, anulado) "
    "VALUES ({id}, 1, 1, 1, '2026-05-0{id}', 'parcela', 1.0, 'L/ha', 0, 0)"
)


def _retrato(ruta) -> dict[str, list[str]]:
    """Todas las tablas y **todas sus filas**, para poder decir «ni una fila cambia».

    Contar filas no basta: se compara el contenido de cada fila, así que un cambio de valor, una
    fila que se va y otra que entra con el mismo número, también salen aquí.
    """
    conexion = sqlite3.connect(f"file:{pathlib.Path(ruta).as_posix()}?mode=ro", uri=True)
    try:
        tablas = [
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            tabla: sorted(repr(fila) for fila in conexion.execute(f'SELECT * FROM "{tabla}"'))
            for tabla in tablas
        }
    finally:
        conexion.close()


def _cuantas_filas(ruta, tabla: str) -> int:
    conexion = sqlite3.connect(f"file:{pathlib.Path(ruta).as_posix()}?mode=ro", uri=True)
    try:
        return conexion.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
    finally:
        conexion.close()


def _es_obligatoria(ruta, tabla: str, columna: str) -> bool:
    """Si la columna sigue sin admitir el tercer estado (`NOT NULL`)."""
    conexion = sqlite3.connect(f"file:{pathlib.Path(ruta).as_posix()}?mode=ro", uri=True)
    try:
        for fila in conexion.execute(f'PRAGMA table_info("{tabla}")'):
            if fila[1] == columna:
                return bool(fila[3])
        raise AssertionError(f"«{tabla}» no tiene la columna «{columna}»")
    finally:
        conexion.close()


def _base_pequena(ruta: pathlib.Path) -> pathlib.Path:
    """Una base de dos columnas: para las pruebas de mecánica de ficheros, no de modelo."""
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.execute("CREATE TABLE cosas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('La Vega')")
        conexion.commit()
    finally:
        conexion.close()
    return ruta


def _leer_cosas(ruta) -> list[str]:
    conexion = sqlite3.connect(f"file:{pathlib.Path(ruta).as_posix()}?mode=ro", uri=True)
    try:
        return [fila[0] for fila in conexion.execute("SELECT nombre FROM cosas ORDER BY id")]
    finally:
        conexion.close()


def _guion_de_migracion():
    """El guion de migración, cargado como módulo. Se importa, no se ejecuta."""
    especificacion = importlib.util.spec_from_file_location(
        "migrar_zona_de_nitratos_para_las_pruebas", GUION_DE_MIGRACION
    )
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def _nombres_de_la_copia(ruta: pathlib.Path) -> list[str]:
    """Los nombres que puede tener la copia, con la marca del reloj y con el proceso detrás.

    `_copia_de_seguridad_del_fichero` usa `{nombre}.antes-de-migrar-{marca}` y, si ese nombre ya
    existe, le añade `-{pid}`. Para ocuparle el nombre a la copia hay que ocupar los dos, y como la
    marca sale del reloj (y la prueba tarda un instante en llegar), se ocupan los de un par de
    segundos alrededor.
    """
    nombres = []
    for desfase in (-1, 0, 1, 2):
        momento = dt.datetime.now() + dt.timedelta(seconds=desfase)
        marca = momento.strftime("%Y%m%d-%H%M%S")
        base = f"{ruta.name}.antes-de-migrar-{marca}"
        nombres.extend([base, f"{base}-{os.getpid()}"])
    return nombres


# --------------------------------------------------------------------------
# 1. La copia que lleva lo que está confirmado en el WAL
# --------------------------------------------------------------------------


class TestLaCopiaLlevaLoQueEstaEnElWal:
    def test_la_copia_lleva_las_filas_confirmadas_que_siguen_en_el_wal(self, tmp_path):
        """**El motivo de que no se copie el fichero sin más.**

        Se deja la conexión que escribió **abierta** a propósito: mientras esté abierta, lo
        confirmado vive en el `-wal` y no baja al fichero principal (en cuanto se cierra, SQLite lo
        vuelca y borra el `-wal`, así que cerrarla sería hacer trampa). Con la base así:

        1. Se comprueba **que el problema es real**: una copia del fichero principal, tal cual, no
           lleva el apunte del WAL.
        2. Se comprueba que esa copia **pasa `quick_check`**: el fichero está entero, lo que falta
           son filas. Por eso hace falta la segunda comprobación, la de los datos.
        3. Y que la copia que hace el programa **sí las lleva**, y que tiene las mismas tablas y las
           mismas filas que la base.
        """
        ruta = tmp_path / "con_wal.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        escritor = sqlite3.connect(str(ruta))
        try:
            assert escritor.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
            escritor.execute(APUNTE_DE_DESPUES.format(id=2))
            escritor.commit()
            assert pathlib.Path(f"{ruta}-wal").stat().st_size > 0, (
                "la prueba necesita cambios confirmados viviendo en el WAL"
            )

            # 1. El problema, demostrado con una copia del fichero principal hecha a mano.
            a_mano = tmp_path / "a-mano.db"
            shutil.copy2(ruta, a_mano)
            assert _cuantas_filas(a_mano, "tratamientos") == 1, (
                "si el fichero principal ya tuviera el apunte, esta prueba no probaría nada"
            )

            # 2. Y esa copia está «entera»: el defecto no lo caza la comprobación de entereza.
            assert database._la_copia_esta_entera(a_mano) is True, (
                "una copia incompleta puede pasar quick_check: es exactamente el caso del WAL"
            )
            assert database._copia_tiene_lo_mismo(ruta, a_mano) is False, (
                "la comprobación de los datos es la única que echa de menos la fila del WAL"
            )

            # 3. La copia del programa.
            copia = database._copia_de_seguridad_del_fichero(motor)
        finally:
            escritor.close()

        assert copia, "el programa tiene que dejar una copia antes de tocar una tabla"
        assert not copia.endswith("-byte-a-byte"), (
            f"con datos pendientes en el WAL no vale la copia del principal: {copia}"
        )
        assert _cuantas_filas(copia, "tratamientos") == 2, (
            "la copia tiene que llevar el apunte que estaba confirmado en el WAL"
        )
        assert _retrato(copia) == _retrato(ruta), (
            "la copia tiene que tener las mismas tablas y las mismas filas que la base"
        )

    def test_una_base_que_quedo_con_el_wal_de_una_caida_se_copia_entera_y_exacta(self, tmp_path):
        """Lo que queda en el disco cuando el programa muere de golpe, copiado tal cual.

        Cuando un proceso muere a lo bruto (un apagón, un `kill`) deja los **tres** ficheros: el
        principal, el `-wal` con lo confirmado y el `-shm`. Aquí se cogen esos tres ficheros tal y
        como están (copiados byte a byte mientras el escritor sigue abierto: eso es exactamente lo
        que hay en el disco después de la caída) y se le pide la copia al programa.

        El resultado es una sorpresa que conviene tener escrita: **la propia copia vacía el WAL**. Al
        abrir la base, SQLite vuelca al principal lo que estaba confirmado en el `-wal` y lo trunca
        (medido en esta máquina: 4.152 bytes → 0), así que la copia que se devuelve es la **byte a
        byte**, entera y exacta. Es decir: el peligro del WAL del que habla el código existe
        **mientras haya otra conexión abierta** (como en la prueba de arriba); con la base quieta,
        copiar el fichero principal sin más habría bastado, porque el programa lo ha puesto al día
        antes de copiarlo.
        """
        origen = tmp_path / "vivo.db"
        escritor = sqlite3.connect(str(origen))
        try:
            escritor.execute("CREATE TABLE cosas (id INTEGER PRIMARY KEY, nombre TEXT)")
            escritor.execute("INSERT INTO cosas (nombre) VALUES ('La Vega')")
            escritor.commit()
            escritor.execute("PRAGMA journal_mode=WAL")
            escritor.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")
            escritor.commit()

            despues_de_la_caida = tmp_path / "caida"
            despues_de_la_caida.mkdir()
            for sufijo in ("", "-wal", "-shm"):
                shutil.copy2(f"{origen}{sufijo}", despues_de_la_caida / f"caida.db{sufijo}")

            ruta = despues_de_la_caida / "caida.db"
            assert _leer_cosas(ruta) == ["La Vega", "El Prado"]
            wal = despues_de_la_caida / "caida.db-wal"
            assert wal.stat().st_size > 0, "la caída tiene que dejar un -wal con datos"

            copia = database._copia_de_seguridad_del_fichero(
                database.crear_engine(f"sqlite:///{ruta.as_posix()}")
            )
        finally:
            escritor.close()

        assert copia and copia.endswith("-byte-a-byte"), (
            "con la base quieta, la copia vacía el WAL y la copia byte a byte ya es completa"
        )
        assert _leer_cosas(copia) == ["La Vega", "El Prado"]
        assert pathlib.Path(copia).read_bytes() == ruta.read_bytes()
        assert wal.stat().st_size == 0, (
            "la copia ha volcado el WAL al principal: por eso la copia byte a byte sirve"
        )

    def test_un_wal_que_existe_y_esta_vacio_se_trata_como_que_no_hay_nada(self, tmp_path):
        """Un `-wal` de 0 bytes: existe el fichero, pero no hay nada dentro.

        Es el caso que deja el propio programa al copiar (ver la prueba de la caída) y el que deja
        un checkpoint con `TRUNCATE`. La cuenta que hace el programa es «existe y pesa más de cero»,
        así que un `-wal` vacío cuenta como «no hay nada pendiente»: se devuelve la copia byte a byte
        y **es correcta**, porque no había nada que volcar. Se comprueba de verdad: la copia lleva
        las filas y es idéntica al original.
        """
        ruta = tmp_path / "wal_vacio.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        escritor = sqlite3.connect(str(ruta))
        try:
            escritor.execute("PRAGMA journal_mode=WAL")
            escritor.execute(APUNTE_DE_DESPUES.format(id=2))
            escritor.commit()
            escritor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            wal = pathlib.Path(f"{ruta}-wal")
            assert wal.exists() and wal.stat().st_size == 0, (
                "la prueba necesita el fichero -wal vacío, no que no exista"
            )

            copia = database._copia_de_seguridad_del_fichero(motor)
        finally:
            escritor.close()

        assert copia and copia.endswith("-byte-a-byte")
        assert pathlib.Path(copia).read_bytes() == ruta.read_bytes()
        assert _cuantas_filas(copia, "tratamientos") == 2, (
            "la copia byte a byte de un -wal vacío no pierde nada"
        )

    def test_la_copia_se_puede_abrir_despues_y_cuenta_lo_mismo_que_la_base(self, tmp_path):
        """Que la copia no solo «exista»: que se abra y que cuente lo mismo.

        Se hace con la base realista y con su `-wal` cargado, que es el caso difícil.
        """
        ruta = tmp_path / "se_abre.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        escritor = sqlite3.connect(str(ruta))
        try:
            escritor.execute("PRAGMA journal_mode=WAL")
            escritor.execute(APUNTE_DE_DESPUES.format(id=2))
            escritor.execute(APUNTE_DE_DESPUES.format(id=3))
            escritor.commit()
            copia = database._copia_de_seguridad_del_fichero(motor)
        finally:
            escritor.close()

        assert pathlib.Path(copia).exists()
        de_la_base = _retrato(ruta)
        de_la_copia = _retrato(copia)
        assert de_la_copia == de_la_base, "la copia se tiene que poder abrir y contar lo mismo"
        assert de_la_copia["tratamientos"] and len(de_la_copia["tratamientos"]) == 3
        assert len(de_la_copia) == len(de_la_base) == len(models.Base.metadata.tables), (
            "la base realista tiene que traer todas las tablas del modelo"
        )


# --------------------------------------------------------------------------
# 2. La vuelta atrás
# --------------------------------------------------------------------------


class TestLaVueltaAtras:
    def test_sin_nada_en_el_wal_la_copia_es_byte_a_byte_y_el_fichero_queda_igual(self, tmp_path):
        """El caso normal: no hay `-wal`, así que volver atrás deja el fichero **exactamente**
        como estaba (mismo `sha256`), y no solo «una base con los mismos datos».
        """
        ruta = tmp_path / "sin_wal.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        antes = ruta.read_bytes()
        copia = database._copia_de_seguridad_del_fichero(motor)

        assert copia and copia.endswith("-byte-a-byte"), (
            f"sin nada pendiente se espera la copia byte a byte: {copia}"
        )
        assert pathlib.Path(copia).read_bytes() == antes, "tiene que ser idéntica, byte a byte"
        assert hashlib.sha256(pathlib.Path(copia).read_bytes()).hexdigest() == (
            hashlib.sha256(antes).hexdigest()
        )

        # Y la vuelta atrás, de verdad: se pone la copia encima y se mira.
        shutil.copy2(copia, ruta)
        assert ruta.read_bytes() == antes, "volver atrás tiene que dejar el fichero como estaba"
        assert _retrato(ruta) == _retrato(copia)

    def test_volver_atras_solo_copiando_la_copia_no_deshace_lo_escrito_despues(
        self, tmp_path
    ):
        """**El defecto que se ha encontrado.** La vuelta atrás que cuenta el programa no vuelve.

        El guion de migración imprime «Para volver atrás: copia {copia} encima de {ruta}», y el
        docstring de `_copia_de_seguridad_del_fichero` dice lo mismo. Eso es un `shutil.copy2` del
        fichero principal **dejando el `-wal` y el `-shm` donde están**. Y resulta que el `-wal` de
        la base que se está restaurando contiene lo que se apuntó *después* de la copia: SQLite lo
        vuelve a aplicar encima, así que la base **no vuelve atrás**. Aquí se deja medido: lo que se
        apuntó después sigue estando.

        Esta prueba describe lo que hace hoy el programa a propósito: **el día que se arregle (que
        el aviso diga también que hay que quitar el `-wal` y el `-shm`, o que se borren), esta prueba
        tiene que fallar**, y ese fallo es la buena noticia.
        """
        ruta = tmp_path / "vuelta.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        escritor = sqlite3.connect(str(ruta))
        try:
            assert escritor.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
            escritor.execute(APUNTE_DE_DESPUES.format(id=2))
            escritor.commit()

            copia = database._copia_de_seguridad_del_fichero(motor)
            assert copia and not copia.endswith("-byte-a-byte"), (
                "el caso que importa es el de la copia coherente con un -wal al lado"
            )
            assert _cuantas_filas(copia, "tratamientos") == 2

            # Y el programa sigue funcionando: se apunta un tratamiento más.
            escritor.execute(APUNTE_DE_DESPUES.format(id=3))
            escritor.commit()
            assert pathlib.Path(f"{ruta}-wal").exists(), (
                "la prueba necesita que el -wal siga al lado de la base"
            )

            # La vuelta atrás, tal y como la cuenta el propio programa.
            shutil.copy2(copia, ruta)

            assert _cuantas_filas(copia, "tratamientos") == 2
            assert _cuantas_filas(ruta, "tratamientos") == 3, (
                "el apunte escrito después de la copia sigue ahí: esa vuelta atrás no vuelve"
            )
        finally:
            escritor.close()

    def test_volver_atras_quitando_tambien_el_wal_si_deshace_lo_de_despues(self, tmp_path):
        """Y la vuelta atrás que **sí** funciona: la misma, quitando antes el `-wal` y el `-shm`.

        Es la prueba de que el defecto de arriba es el `-wal` de al lado y no otra cosa.
        """
        ruta = tmp_path / "vuelta_bien.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        escritor = sqlite3.connect(str(ruta))
        try:
            escritor.execute("PRAGMA journal_mode=WAL")
            escritor.execute(APUNTE_DE_DESPUES.format(id=2))
            escritor.commit()
            copia = database._copia_de_seguridad_del_fichero(motor)
            escritor.execute(APUNTE_DE_DESPUES.format(id=3))
            escritor.commit()
            assert _cuantas_filas(ruta, "tratamientos") == 3
        finally:
            escritor.close()

        for sufijo in ("-wal", "-shm"):
            sobrante = pathlib.Path(f"{ruta}{sufijo}")
            if sobrante.exists():
                sobrante.unlink()
        shutil.copy2(copia, ruta)

        assert _cuantas_filas(ruta, "tratamientos") == 2, (
            "quitando el -wal y el -shm, la base vuelve a lo que había en la copia"
        )
        assert _retrato(ruta) == _retrato(copia)

    def test_lo_que_el_programa_deja_al_lado_de_la_base(self, tmp_path):
        """Lo que queda en la carpeta del agricultor después de la copia, medido.

        **Cambiado el 02/10/2026, y esto decía lo contrario.** La revisión independiente midió que, con la
        base en modo WAL, las dos comprobaciones abren la copia y SQLite le crea **su** `-wal` y **su**
        `-shm`, que se quedaban ahí para siempre: basura en la carpeta del agricultor, y una carpeta con
        `…-byte-a-byte-shm` dentro parece que tiene una copia cuando ya no la tiene.

        Ahora se limpian, pero **solo cuando están vacíos**: si el `-wal` de una copia tuviera algo dentro,
        ahí puede haber datos confirmados de esa copia y borrarlo sería perderlos
        (`database._limpiar_los_ficheros_de_al_lado`). Esta prueba exige las dos cosas: que no quede basura
        y que la limpieza no se lleve por delante un `-wal` con contenido.
        """
        ruta = tmp_path / "basura.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        escritor = sqlite3.connect(str(ruta))
        try:
            escritor.execute("PRAGMA journal_mode=WAL")
            escritor.execute(APUNTE_DE_DESPUES.format(id=2))
            escritor.commit()
            copia = database._copia_de_seguridad_del_fichero(motor)

            con_la_base_abierta = sorted(p.name for p in tmp_path.iterdir())
            assert con_la_base_abierta == sorted(
                [
                    # De la base viva: su fichero y sus dos de al lado, que son suyos y no se tocan.
                    "basura.db", "basura.db-wal", "basura.db-shm",
                    # Y la copia, **sola**: sin `-shm` ni `-wal` de la comprobación.
                    pathlib.Path(copia).name,
                ]
            ), f"lo que queda al lado de la base ha cambiado: {con_la_base_abierta}"
            assert not pathlib.Path(f"{copia}-shm").exists()
            assert not pathlib.Path(f"{copia}-wal").exists()
        finally:
            escritor.close()

        # Y cuando la aplicación se cierra (que es el caso de siempre), tampoco queda nada de la copia.
        al_cerrar = sorted(p.name for p in tmp_path.iterdir())
        assert al_cerrar == sorted(["basura.db", pathlib.Path(copia).name]), (
            f"queda basura de la copia: {al_cerrar}"
        )


# --------------------------------------------------------------------------
# 3. Si la copia no se puede comprobar, no se reconstruye ninguna tabla
# --------------------------------------------------------------------------


class TestSiLaCopiaNoSePuedeComprobar:
    def test_si_la_copia_no_se_puede_ni_crear_la_tabla_no_se_reconstruye(self, tmp_path):
        """Provocado **de verdad**, sin parchear nada: se le ocupa el nombre a la copia.

        `_copia_de_seguridad_del_fichero` pone la copia al lado de la base, con un nombre que
        empieza por el de la base. Si en ese nombre hay una carpeta, SQLite no puede abrir ahí la
        copia y salta un error. Lo que se comprueba es lo que de verdad importa: que **no se
        reconstruye ninguna tabla** y que la base se queda como estaba.

        Y de paso sale un defecto: el error que se levanta es un `sqlite3.OperationalError`, no el
        `RuntimeError` que el guion de migración sabe contar en cristiano (ver
        `test_el_guion_no_avisa_en_cristiano_cuando_la_copia_no_se_puede_ni_crear`).
        """
        ruta = tmp_path / "ocupado.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        antes = _retrato(ruta)

        for nombre in _nombres_de_la_copia(ruta):
            (tmp_path / nombre).mkdir()

        with pytest.raises(Exception) as fallo:
            database.reconstruir_para_poder_decir_no_se(motor)

        assert isinstance(fallo.value, sqlite3.Error), (
            f"se esperaba un fallo de SQLite al no poder crear la copia: {fallo.value!r}"
        )
        assert not isinstance(fallo.value, RuntimeError), (
            "el guion solo cuenta en cristiano los RuntimeError: este se le escapa"
        )
        assert _es_obligatoria(ruta, "tratamientos", "en_zona_vulnerable") is True, (
            "sin copia comprobable no se puede reconstruir nada"
        )
        assert _retrato(ruta) == antes, "y la base tiene que quedarse intacta"

    def test_si_la_copia_no_esta_entera_no_se_reconstruye_ninguna_tabla(self, tmp_path, monkeypatch):
        """**Va parcheado, y se dice.** Provocar de verdad que `PRAGMA quick_check` falle en una
        copia recién hecha por SQLite no está al alcance de una prueba (haría falta un fichero que se
        corrompa solo). Lo que sí se puede comprobar de verdad es que, **si esa comprobación dice
        que no**, el arranque del programa (`crear_tablas`, que es por donde pasa) levanta el error y
        no toca ninguna tabla.

        El parcheo es el mínimo: se cambia solo el resultado de la comprobación, no el camino.
        """
        ruta = tmp_path / "no_entera.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        antes = _retrato(ruta)
        monkeypatch.setattr(database, "_la_copia_esta_entera", lambda _ruta: False)

        with pytest.raises(RuntimeError, match="no se puede comprobar"):
            database.crear_tablas(motor)

        assert _es_obligatoria(ruta, "tratamientos", "en_zona_vulnerable") is True
        assert _es_obligatoria(ruta, "productos_fitosanitarios", "autorizado") is True
        assert _retrato(ruta) == antes

    def test_si_la_copia_no_tiene_los_mismos_datos_no_se_reconstruye_ninguna_tabla(
        self, tmp_path, monkeypatch
    ):
        """La segunda comprobación, la de los datos. **También va parcheada, y se dice**, por el
        mismo motivo que la de arriba: la copia la hace SQLite y sale bien.

        Aquí sí importa que la comprobación que falla sea **esta** y no la de entereza: el mensaje
        tiene que ser el otro, porque son dos problemas distintos y quien lo lee necesita saber cuál.

        **Cambiado el 02/10/2026, y esto pedía el mensaje viejo** («no tiene los mismos datos»). La
        revisión independiente puso en duda que culpar a la copia fuera justo: la comprobación se hace
        contra la base **viva**, así que si otro proceso escribe entre la copia y la comprobación, la copia
        estaba bien y el mensaje mentía. Ahora se **vuelve a copiar y a comprobar una vez** y, si tampoco
        cuadra, el mensaje dice lo que de verdad pasa y lo único que puede arreglarlo: **que hay otro
        programa escribiendo en la base y hay que cerrarlo**. Sigue sin reconstruirse ninguna tabla.
        """
        ruta = tmp_path / "no_mismos.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        antes = _retrato(ruta)
        monkeypatch.setattr(database, "_copia_tiene_lo_mismo", lambda _ruta, _copia: False)

        with pytest.raises(RuntimeError, match="otro programa escribiendo"):
            database.reconstruir_para_poder_decir_no_se(motor)

        assert _es_obligatoria(ruta, "tratamientos", "en_zona_vulnerable") is True
        assert _retrato(ruta) == antes

    def test_el_aviso_del_fallo_dice_donde_esta_la_copia_y_que_no_se_ha_tocado_nada(
        self, tmp_path, monkeypatch
    ):
        """Si el arranque se para, el mensaje tiene que servir para algo: decir **dónde** quedó la
        copia y que **no** se ha cambiado la estructura.

        Lo que el mensaje **no** dice es qué hacer a continuación (no dice «no arranques el
        programa», ni «mira el disco», ni a quién avisar). Está apuntado en
        `docs/ACEPTACION_COPIA_Y_MIGRACION.md`.
        """
        ruta = tmp_path / "con_mensaje.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        monkeypatch.setattr(database, "_la_copia_esta_entera", lambda _ruta: False)

        with pytest.raises(RuntimeError) as fallo:
            database.reconstruir_para_poder_decir_no_se(motor)

        mensaje = str(fallo.value)
        assert "No se ha cambiado la estructura de la base de datos" in mensaje
        copias = [p for p in tmp_path.iterdir() if ".antes-de-migrar-" in p.name]
        assert len(copias) == 1, f"tenía que quedar la copia y solo una: {copias}"
        assert str(copias[0]) in mensaje, (
            "el mensaje tiene que decir dónde está la copia, o no sirve de nada"
        )


# --------------------------------------------------------------------------
# 4. La comprobación de «los mismos datos»
# --------------------------------------------------------------------------


class TestLaComprobacionDeLosMismosDatos:
    def test_detecta_una_copia_a_la_que_le_sobra_una_fila(self, tmp_path):
        """Una copia **entera** y con una fila de más también se nota.

        Es el otro lado de lo mismo, y no es un caso de laboratorio: una copia que se quedara con
        datos de más devolvería al agricultor un cuaderno con apuntes que había borrado.
        """
        base = _base_pequena(tmp_path / "base.db")
        copia = tmp_path / "copia.db"
        shutil.copy2(base, copia)
        with sqlite3.connect(str(copia)) as conexion:
            conexion.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")

        assert database._la_copia_esta_entera(copia) is True, "la copia está entera"
        assert _leer_cosas(copia) == ["La Vega", "El Prado"]
        assert _leer_cosas(base) == ["La Vega"]
        assert database._copia_tiene_lo_mismo(base, copia) is False, (
            "una fila de más también es «no tener los mismos datos»"
        )

    def test_no_da_por_buena_una_copia_con_menos_filas_que_la_base(self, tmp_path):
        """Al revés: la copia tiene menos filas que la base y se tiene que notar."""
        base = _base_pequena(tmp_path / "base2.db")
        with sqlite3.connect(str(base)) as conexion:
            conexion.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")
        copia = tmp_path / "copia2.db"
        shutil.copy2(base, copia)
        with sqlite3.connect(str(copia)) as conexion:
            conexion.execute("DELETE FROM cosas WHERE nombre = 'El Prado'")

        assert database._la_copia_esta_entera(copia) is True
        assert database._copia_tiene_lo_mismo(base, copia) is False, (
            "una copia con menos filas no puede darse por buena"
        )

    def test_la_copia_se_compara_con_la_base_viva_y_una_escritura_posterior_la_invalida(
        self, tmp_path
    ):
        """Lo que pasa si alguien escribe **después** de que se haga la copia.

        La comprobación no compara la copia con la foto que había al copiarla, sino con la base
        **de ahora mismo**: si alguien apunta algo entre la copia y la comprobación, los números no
        cuadran y la migración se rechaza. Es el lado seguro (mejor no migrar que migrar sin red),
        pero el mensaje que sale —«la copia no tiene los mismos datos que la base»— es engañoso: la
        copia estaba bien, la que se ha movido es la base.
        """
        ruta = tmp_path / "se_mueve.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)

        copia = database._copia_de_seguridad_del_fichero(motor)
        assert database._copia_tiene_lo_mismo(ruta, copia) is True

        with sqlite3.connect(str(ruta)) as conexion:
            conexion.execute(APUNTE_DE_DESPUES.format(id=9))

        assert database._copia_tiene_lo_mismo(ruta, copia) is False, (
            "una escritura posterior a la copia tiene que hacer saltar la comprobación"
        )

    def test_dos_bases_con_las_mismas_filas_y_datos_distintos_no_pasan_la_comprobacion(self, tmp_path):
        """**Cambiado el 03/10/2026, y esto exigía lo contrario.** Decía que la comprobación solo miraba
        **el número de filas**: una copia con las mismas filas y los valores cambiados la pasaba. El
        revisor lo dejó escrito como el límite de lo que aquello demostraba, y tenía razón en que era el
        límite — pero un límite que se puede quitar no se deja puesto: en una migración, una copia con
        **los mismos recuentos y otros valores** es justo lo que no puede parecer buena.

        Ahora `_copia_tiene_lo_mismo` guarda, por tabla, **la huella de los valores** además del número de
        filas (con los nombres de las columnas delante, para que el orden físico no confunda), así que una
        sola fila cambiada se nota.
        """
        base = _base_pequena(tmp_path / "mismos.db")
        copia = tmp_path / "mismos-copia.db"
        shutil.copy2(base, copia)
        with sqlite3.connect(str(copia)) as conexion:
            conexion.execute("UPDATE cosas SET nombre = 'OTRA COSA' WHERE id = 1")

        assert _leer_cosas(base) == ["La Vega"]
        assert _leer_cosas(copia) == ["OTRA COSA"]
        assert database._copia_tiene_lo_mismo(base, copia) is False, (
            "las mismas filas con otros valores no son «los mismos datos»"
        )

    def test_una_copia_igual_pasa_la_comprobacion(self, tmp_path):
        """Y la otra mitad: una copia de verdad, sin tocar nada, **sí** la pasa (si no, todo esto no
        serviría de nada y la migración no podría avanzar nunca)."""
        base = _base_pequena(tmp_path / "igual.db")
        copia = tmp_path / "igual-copia.db"
        shutil.copy2(base, copia)

        assert database._copia_tiene_lo_mismo(base, copia) is True

    def test_una_tabla_que_falta_se_nota(self, tmp_path):
        """Y una tabla que no está también: la comprobación compara el mapa entero, no un total."""
        base = _base_pequena(tmp_path / "tablas.db")
        with sqlite3.connect(str(base)) as conexion:
            conexion.execute("CREATE TABLE otras (id INTEGER PRIMARY KEY)")
        copia = tmp_path / "tablas-copia.db"
        shutil.copy2(base, copia)
        with sqlite3.connect(str(copia)) as conexion:
            conexion.execute("DROP TABLE otras")

        assert database._la_copia_esta_entera(copia) is True
        assert database._copia_tiene_lo_mismo(base, copia) is False


# --------------------------------------------------------------------------
# 5. La migración con una base realista
# --------------------------------------------------------------------------


class TestLaMigracionConUnaBaseRealista:
    def test_la_reconstruccion_no_cambia_ni_una_fila(self, tmp_path):
        """Las 26 tablas del modelo, la finca de verdad dentro, y ni una fila cambia.

        No se cuentan filas: se compara el **contenido** de todas las filas de todas las tablas
        antes y después. Copiar las filas es copiarlas, no arreglarlas.
        """
        ruta = tmp_path / "realista.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        antes = _retrato(ruta)
        assert len(antes) == len(models.Base.metadata.tables), (
            "la base tiene que traer todas las tablas del modelo"
        )

        hechas = database.reconstruir_para_poder_decir_no_se(motor)

        assert sorted(hechas) == sorted(
            f"{tabla}.{columna}"
            for tabla, columna in database.COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS
        ), "se tienen que reconstruir todas las columnas de la lista, y solo esas"
        for tabla, columna in database.COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS:
            assert _es_obligatoria(ruta, tabla, columna) is False, f"{tabla}.{columna}"
        assert _retrato(ruta) == antes, "ni una fila puede cambiar"
        assert database.reconstruir_para_poder_decir_no_se(motor) == [], "es idempotente"

    def test_la_vuelta_atras_devuelve_la_base_como_estaba_antes_de_migrar(self, tmp_path):
        """La copia, la reconstrucción y la vuelta atrás, con la base realista.

        La vuelta atrás tiene que deshacer **también el esquema**: después de poner la copia encima,
        la columna vuelve a ser obligatoria y las filas son las mismas. Si la vuelta atrás dejara el
        esquema tocado, no sería una vuelta atrás.
        """
        ruta = tmp_path / "vuelta_realista.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        antes = _retrato(ruta)
        bytes_de_antes = ruta.read_bytes()

        copia = database._copia_de_seguridad_del_fichero(motor)
        assert copia and copia.endswith("-byte-a-byte")
        assert pathlib.Path(copia).read_bytes() == bytes_de_antes

        hechas = database.reconstruir_para_poder_decir_no_se(motor)
        assert hechas, "tenía que migrar el esquema"

        # Y ahora, la vuelta atrás.
        shutil.copy2(copia, ruta)

        assert ruta.read_bytes() == bytes_de_antes, "el fichero tiene que quedar igual"
        for tabla, columna in database.COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS:
            assert _es_obligatoria(ruta, tabla, columna) is True, (
                f"la vuelta atrás tiene que devolver «{tabla}.{columna}» a obligatoria"
            )
        assert _retrato(ruta) == antes
        # Y la base vuelve a estar utilizable: se puede leer por una conexión normal.
        assert _cuantas_filas(ruta, "tratamientos") == 1


# --------------------------------------------------------------------------
# 6. Caminos en los que se reconstruye sin copia válida
# --------------------------------------------------------------------------


class TestCaminosSinCopiaValida:
    def test_en_memoria_no_se_hace_ninguna_copia_y_la_tabla_se_reconstruye_igual(self, tmp_path):
        """**Un camino real sin copia: una base en memoria.**

        `_ruta_del_fichero` devuelve `None` cuando no hay fichero, y entonces
        `_copia_de_seguridad_del_fichero` devuelve `None` sin decir nada.

        **Cambiado el 02/10/2026, y esto decía lo contrario.** Antes, aun sin copia, la tabla se
        reconstruía: tirar abajo una tabla **sin red** es justo lo que la copia viene a impedir, así que
        ahora **se para y se dice por qué** (un mensaje que además explica que en PostgreSQL —la base de
        producción del proyecto— esto tiene que ser una migración de verdad: la reconstrucción usa `PRAGMA`
        y `ALTER TABLE … RENAME`, que son de SQLite). Sin copia no se reconstruye nada, tampoco en memoria.
        """
        motor = database.crear_engine("sqlite://")
        ddl = str(CreateTable(models.Base.metadata.tables["fertilizaciones"]).compile(
            dialect=motor.dialect
        )).replace("en_zona_vulnerable BOOLEAN,", "en_zona_vulnerable BOOLEAN NOT NULL,")
        assert "en_zona_vulnerable BOOLEAN NOT NULL" in ddl
        with motor.begin() as conexion:
            conexion.exec_driver_sql("PRAGMA foreign_keys=OFF")
            conexion.execute(text(ddl))
            conexion.execute(text(
                "INSERT INTO fertilizaciones (id, explotacion_id, campana_id, fecha, "
                "superficie_ha, tipo, riqueza_n, riqueza_p, riqueza_k, kg_ha_producto, "
                "cantidad_total_kg, uf_n_ha, uf_p_ha, uf_k_ha, uf_n_total, uf_p_total, "
                "uf_k_total, en_zona_vulnerable, anulado) "
                "VALUES (1, 1, 1, '2026-02-20', 2.43, 'organico', 4.0, 0.0, 0.0, 1000.0, "
                "2430.0, 40.0, 0.0, 0.0, 972.0, 0.0, 0.0, 1, 0)"
            ))

        assert database._copia_de_seguridad_del_fichero(motor) is None, (
            "en memoria no hay fichero que copiar"
        )

        with pytest.raises(RuntimeError, match="no es un fichero de SQLite"):
            database.reconstruir_para_poder_decir_no_se(motor)

        # Y la tabla sigue exactamente como estaba: sin copia no se toca nada.
        columnas = {c["name"]: c for c in inspect(motor).get_columns("fertilizaciones")}
        assert columnas["en_zona_vulnerable"]["nullable"] is False
        with motor.begin() as conexion:
            assert conexion.execute(
                text("SELECT COUNT(*) FROM fertilizaciones")
            ).scalar_one() == 1

    def test_con_postgresql_no_se_hace_copia_ninguna(self):
        """**El otro camino sin copia: PostgreSQL, el de producción.**

        Aquí no se puede levantar un PostgreSQL (no hay servidor en esta máquina y no se puede
        pedir), así que lo que se comprueba es **la puerta**: `_ruta_del_fichero` no devuelve
        fichero ninguno para una dirección de PostgreSQL, y por tanto
        `_copia_de_seguridad_del_fichero` no copia nada y sigue adelante. Lo que haría la
        reconstrucción en PostgreSQL de verdad (`PRAGMA foreign_keys`, `ALTER TABLE ... RENAME`)
        **no se ha podido comprobar** y está apuntado en el documento.
        """

        class MotorDeMentira:
            """Solo tiene lo que mira `_ruta_del_fichero`: la dirección."""

            def __init__(self, url: str):
                from sqlalchemy.engine import make_url

                self.url = make_url(url)

        de_postgres = MotorDeMentira("postgresql+psycopg2://usuario:clave@servidor/cuedigital")

        assert database._ruta_del_fichero(de_postgres) is None
        assert database._copia_de_seguridad_del_fichero(de_postgres) is None, (
            "en PostgreSQL no se hace copia: la reconstrucción iría sin red"
        )


# --------------------------------------------------------------------------
# 7. El guion de migración
# --------------------------------------------------------------------------


class TestElGuionDeMigracion:
    def test_el_guion_deja_la_columna_admitiendo_no_se_y_no_cambia_ninguna_fila(
        self, tmp_path, monkeypatch
    ):
        """El guion entero, con una base realista, cuando **no** hay nada que reescribir.

        La tierra sabe si está en zona, así que ningún apunte dice «no» sin saberlo y el guion sale
        con 0. Lo que se comprueba: que las columnas quedan admitiendo el tercer estado, que no se
        mueve ni una fila, y **cuántas copias de la base del agricultor se quedan en la carpeta**.

        **Cambiado el 02/10/2026, y esto pedía cuatro copias.** La revisión independiente midió que una
        sola ejecución dejaba **cuatro** ficheros con los datos del agricultor: el guion hacía su copia y la
        reconstrucción hacía otra, cada una con su versión byte a byte, y nadie las borra nunca. Ahora el
        guion le pasa su copia a la reconstrucción (`copia_ya_hecha`), así que quedan **dos**: la coherente
        y la idéntica, que son las que sirven para volver atrás.
        """
        ruta = tmp_path / "guion.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor, la_tierra_sabe_si_esta_en_zona=True)
        antes = _retrato(ruta)
        migrar = _guion_de_migracion()
        monkeypatch.setattr(sys, "argv", ["migrar", "--base", str(ruta), "--migrar"])

        codigo = migrar.main()

        assert codigo == 0, "sin nada que reescribir el guion tiene que salir con 0"
        for tabla, columna in database.COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS:
            assert _es_obligatoria(ruta, tabla, columna) is False, f"{tabla}.{columna}"
        assert _retrato(ruta) == antes, "el guion no puede cambiar ni una fila"
        copias = sorted(p.name for p in tmp_path.iterdir() if ".antes-de-migrar-" in p.name)
        assert len(copias) == 2, (
            "una ejecución del guion tiene que dejar DOS copias (la coherente y la idéntica), "
            f"no cuatro: {copias}"
        )
        assert any(nombre.endswith("-byte-a-byte") for nombre in copias), copias

    def test_el_guion_avisa_en_cristiano_y_sale_con_1_cuando_la_copia_no_se_comprueba(
        self, tmp_path, monkeypatch, capsys
    ):
        """La mitad buena de lo que se afirma: si la comprobación falla, el guion lo cuenta en
        cristiano (sin traza de Python), dice que la base se queda como estaba y sale con 1.

        **Va parcheado, y se dice**, por lo mismo que las pruebas de arriba: hacer fallar de verdad
        la comprobación de entereza no está al alcance de una prueba.
        """
        ruta = tmp_path / "guion_parado.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        antes = _retrato(ruta)
        migrar = _guion_de_migracion()
        monkeypatch.setattr(database, "_la_copia_esta_entera", lambda _ruta: False)
        monkeypatch.setattr(sys, "argv", ["migrar", "--base", str(ruta), "--migrar"])

        codigo = migrar.main()
        salida = capsys.readouterr().out

        assert codigo == 1, "el guion tiene que salir con 1 para que se note"
        assert "No se migra" in salida
        assert "se queda exactamente como estaba" in salida
        assert "Traceback" not in salida
        assert _es_obligatoria(ruta, "tratamientos", "en_zona_vulnerable") is True
        assert _retrato(ruta) == antes

    def test_el_guion_no_avisa_en_cristiano_cuando_la_copia_no_se_puede_ni_crear(
        self, tmp_path, monkeypatch, capsys
    ):
        """**Cuando la copia no se puede ni crear, el guion lo cuenta en cristiano.**

        **Cambiado el 02/10/2026, y esto decía lo contrario.** Provocado de verdad: se le ocupa el nombre a
        la copia con una carpeta. El guion solo recogía `RuntimeError`, y esto es un error de SQLite, así que
        salía una traza de Python de veinte líneas en vez del aviso en castellano. Ahora recoge también los
        errores de SQLite y del disco (`sqlite3.Error`, `OSError`), dice qué ha pasado, dice que la base se
        queda como estaba, y sale con 1 sin volcar nada.
        """
        ruta = tmp_path / "guion_sin_copia.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor)
        antes = _retrato(ruta)
        for nombre in _nombres_de_la_copia(ruta):
            (tmp_path / nombre).mkdir()
        migrar = _guion_de_migracion()
        monkeypatch.setattr(sys, "argv", ["migrar", "--base", str(ruta), "--migrar"])

        codigo = migrar.main()
        salida = capsys.readouterr().out

        assert codigo == 1, "el guion tiene que salir con 1 para que se note"
        assert "No se migra" in salida, f"no avisa en cristiano: {salida[-400:]}"
        assert "se queda exactamente como estaba" in salida
        assert "Traceback" not in salida
        assert _es_obligatoria(ruta, "tratamientos", "en_zona_vulnerable") is True
        assert _retrato(ruta) == antes

    def test_el_guion_dice_que_hay_apuntes_que_cambiar_y_los_cambia(
        self, tmp_path, monkeypatch
    ):
        """**El defecto de precedencia, arreglado y comprobado desde fuera.**

        **Cambiado el 02/10/2026, y esto exigía el fallo.** El informe contaba un apunte que dice «no» sin
        que nadie lo haya comprobado, y la lista de los que iba a cambiar estaba **siempre vacía**: en
        `_ids_que_cambian`, `firmadas` ya es una condición compuesta (`(sin saberlo) AND firmado`) y el `NOT`
        sin paréntesis dejaba la consulta en `A AND NOT (A) AND B`, que no puede devolver nada. El guion
        terminaba en error **después** de haber migrado el esquema: esquema migrado y datos sin tocar.

        Ahora el paréntesis está puesto, la lista trae el apunte, se cambia a «no comprobado» y el guion sale
        con 0 diciendo cuántos ha cambiado.
        """
        ruta = tmp_path / "guion_datos.db"
        motor = _motor_con_las_columnas_todavia_obligatorias(ruta)
        _meter_una_finca_de_verdad(motor, la_tierra_sabe_si_esta_en_zona=None)
        migrar = _guion_de_migracion()

        conexion = sqlite3.connect(str(ruta))
        try:
            condicion, _firmado, firmadas = migrar._condiciones(conexion, "tratamientos")
            sin_saberlo = migrar._contar(conexion, "tratamientos", condicion)
            sus_firmas = migrar._contar(conexion, "tratamientos", firmadas)
            ids = migrar._ids_que_cambian(conexion, "tratamientos")
        finally:
            conexion.close()

        assert sin_saberlo == 1, "la prueba necesita un apunte que diga «no» sin saberlo"
        assert sus_firmas == 0, "y que no esté dentro de una firma"
        assert ids == [1], (
            "el informe dice que hay uno que cambiar y la lista tiene que traerlo: "
            f"«WHERE A AND NOT (A) AND B» no puede devolver nada, y esto trae {ids}"
        )

        monkeypatch.setattr(sys, "argv", ["migrar", "--base", str(ruta), "--migrar"])
        codigo = migrar.main()

        assert codigo == 0, "el guion tiene que terminar bien: ha hecho lo que decía"
        assert _es_obligatoria(ruta, "tratamientos", "en_zona_vulnerable") is False
        conexion = sqlite3.connect(str(ruta))
        try:
            valores = conexion.execute("SELECT en_zona_vulnerable FROM tratamientos").fetchall()
        finally:
            conexion.close()
        assert valores == [(None,)], (
            "el apunte tiene que quedarse en «no se ha podido comprobar», no seguir diciendo «no»"
        )
