"""Preparación común de los tests.

IMPORTANTE: las variables de entorno se fijan ANTES de importar nada de `app`.
`app.database` crea el motor de base de datos al importarse leyendo esa variable, así
que si se importa antes, los tests escribirían en la base de datos de verdad del
agricultor. Ese fallo ya nos habría costado caro una vez.

Y lo mismo con la carpeta de adjuntos, que se descubrió después: sin fijarla aquí, cada
test que sube un boletín de laboratorio **escribía un fichero de verdad dentro del
proyecto**, y quedaban ahí para siempre. No se notaba porque los tests pasaban igual: lo
que hacía era ensuciar el disco de quien los ejecuta y, de paso, poder falsear el test que
cuenta cuántos boletines hay guardados.
"""

from __future__ import annotations

import atexit
import os
import pathlib
import shutil
import tempfile

_CARPETA_TEMPORAL = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital_tests_"))

# **La puerta explícita para correr TODA la suite contra el motor de producción.** (02/10/2026)
#
# Hasta hoy la suite solo se había corrido sobre SQLite, y PostgreSQL —que es la base de producción
# según `README.md` y `AGENTS.md`— **no se había probado nunca**: al probarlo por primera vez, el
# programa ni siquiera arrancaba (ver el apartado 20 de `docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`).
# Para poder medirlo de verdad hace falta poder apuntar la suite entera allí, y eso **no puede
# hacerse con `CUEDIGITAL_DATABASE_URL`**: esa variable sí se hereda, y la suite **vacía y reescribe
# tablas**, así que una variable olvidada en la consola apuntaría a la base del agricultor. Ese fallo
# «ya nos habría costado caro una vez», como dice arriba.
#
# Por eso se pide con una variable propia, `CUEDIGITAL_SUITE_SOBRE`, que **no existe en ningún otro
# sitio del programa** y que solo acepta PostgreSQL. Para SQLite no hay nada que pedir: la suite ya
# usa su propia base temporal. Y si alguien intenta pedir una dirección de SQLite por aquí, se para
# con un mensaje en vez de dejarlo pasar.
_DIRECCION_PEDIDA = os.environ.get("CUEDIGITAL_SUITE_SOBRE")
if _DIRECCION_PEDIDA:
    if not _DIRECCION_PEDIDA.startswith(("postgresql", "postgres")):
        raise SystemExit(
            "CUEDIGITAL_SUITE_SOBRE solo acepta una dirección de PostgreSQL (por ejemplo "
            "postgresql+psycopg://…). Para SQLite la suite ya usa su propia base temporal, y "
            "apuntarla a un fichero desde aquí es justo lo que este guardián impide."
        )
    os.environ["CUEDIGITAL_DATABASE_URL"] = _DIRECCION_PEDIDA
else:
    os.environ["CUEDIGITAL_DATABASE_URL"] = (
        f"sqlite:///{(_CARPETA_TEMPORAL / 'tests.db').as_posix()}"
    )
os.environ["CUEDIGITAL_SECRETO"] = "secreto-solo-para-los-tests"
# Los boletines de laboratorio que suben los tests van a una carpeta temporal, nunca al
# `datos/adjuntos` del proyecto.
os.environ["CUEDIGITAL_ADJUNTOS"] = str(_CARPETA_TEMPORAL / "adjuntos")
# La suite parte sin catálogo de zonas y lo carga explícitamente en las pruebas
# que comprueban la fuente oficial. El servidor de verdad usa el CSV del proyecto.
os.environ["CUEDIGITAL_ZV_CYL_RUTA"] = str(_CARPETA_TEMPORAL / "zv_no_cargado.csv")

# La suite registra una cuenta en casi todos los tests, y derivar la clave 240.000 veces por
# registro son casi seis minutos de suite. Se baja aquí, y hacen falta DOS variables para
# poder bajarlo: `CUEDIGITAL_ENTORNO=pruebas` y el número. Así un descuido en el servidor de
# verdad no deja las claves de los agricultores protegidas con mil iteraciones (lo impide
# `security.iteraciones_pbkdf2`, y hay un test que lo comprueba).
os.environ["CUEDIGITAL_ENTORNO"] = "pruebas"
os.environ["CUEDIGITAL_ITERACIONES_PBKDF2"] = "1000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import crear_tablas, engine  # noqa: E402
from app.main import app  # noqa: E402


def _borrar_la_carpeta_temporal() -> None:
    """Cierra la base de datos y borra la carpeta temporal de esta ejecución.

    Se llama dos veces a propósito: al terminar la sesión de tests y otra vez al final del
    proceso. En Windows el fichero de SQLite y los adjuntos siguen abiertos un instante después de
    terminar la sesión, así que el primer intento puede no borrar todo; el segundo, cuando el
    intérprete ya está cerrando, sí. Sin el segundo quedaba una carpeta por ejecución.
    """
    engine.dispose()
    shutil.rmtree(_CARPETA_TEMPORAL, ignore_errors=True)


def pytest_sessionfinish(session, exitstatus) -> None:
    """Borra la carpeta temporal de esta ejecución y cierra la base de datos.

    La carpeta se crea al importar este fichero y **no la borraba nadie**: cada ejecución de la
    suite dejaba una carpeta en el temporal del sistema, y el 23/09/2026 se encontraron **559
    acumuladas**. No es un fallo del programa —los tests no tocan nada del proyecto— pero es
    basura que el proyecto deja en el ordenador de quien lo usa, y eso también cuenta.

    Si el borrado falla, no se hace fallar la suite: la suite está para comprobar el programa, no
    para comprobar el borrado.
    """
    _borrar_la_carpeta_temporal()


# El segundo intento de borrado, al cerrar el intérprete. Ver `_borrar_la_carpeta_temporal`.
atexit.register(_borrar_la_carpeta_temporal)

DATOS_CUENTA = {
    "explotacion": {
        "nombre": "David Pérez Velasco",
        "nif": "70922320A",
        "provincia": "Salamanca",
        "municipio": "Peñaranda de Bracamonte",
    },
    "nombre": "David",
    "correo": "david@ejemplo.test",
    "clave": "una-clave-larga-de-verdad",
}

# Mayo de 2026: la campaña que crea el alta de cuenta es la del año en curso, así que
# estas fechas caen dentro de la campaña mientras el año siga siendo 2026.
FECHA_TRATAMIENTO = "2026-05-01"
FECHA_FIN_ESPERA = "2026-05-22"  # 1 de mayo + 21 días de espera


@pytest.fixture(scope="session", autouse=True)
def base_creada():
    """Crea la base de datos UNA vez para toda la suite.

    Antes se creaba y se tiraba en cada test, y eso son 422 ms por test: cinco minutos de
    suite solo montando y desmontando tablas. Ahora el esquema se crea una vez y cada test
    vacía las tablas (ver `base_limpia`). Tiene que ser un fixture de sesión y no de test,
    porque `crear_tablas` también pone al día las columnas que falten, y eso no hace falta
    repetirlo setecientas veces.

    Ojo: los tests que prueban la puesta al día de una instalación vieja **no usan este
    motor**, se crean el suyo en un fichero temporal (`test_plan_abonado.py`). Es a propósito:
    si tirasen tablas de aquí, romperían a los tests que vienen detrás.
    """
    models.Base.metadata.drop_all(bind=engine)
    crear_tablas()
    yield


@pytest.fixture(autouse=True)
def base_limpia(base_creada):
    """Cada test empieza con la base vacía, sin tocar el esquema.

    Se vacían las tablas en orden inverso al de dependencias (una parcela no se puede borrar
    antes que el tratamiento que la usa) y se reinicia el contador de identificadores. El
    resultado para el test es el mismo que si la base se hubiera creado de cero: ids desde 1
    y ninguna fila. Tarda unas 20 veces menos.
    """
    _vaciar_todo()
    yield
    _vaciar_todo()


def _vaciar_todo() -> None:
    """Deja todas las tablas sin filas y con los identificadores a cero.

    **El contador de identificadores va en su propia transacción, y solo en SQLite** (02/10/2026). Esto
    era un fallo que **solo se veía en PostgreSQL**, y que costaba 1.396 pruebas de la suite:

    Antes, los borrados y el `DELETE FROM sqlite_sequence` iban **dentro del mismo `with engine.begin()`**,
    y el error de esa tabla —que en SQLite puede no existir, y ahí es inofensivo— estaba envuelto en un
    `try/except` que lo daba por bueno. En SQLite eso funciona. **En PostgreSQL, cualquier error dentro de
    una transacción la deja abortada**, así que el `COMMIT` se convierte en `ROLLBACK` y **se deshacían
    todos los borrados**: la suite no limpiaba nada, y cada prueba se encontraba la cuenta de la anterior
    («Ese correo ya está usado», 409 en el alta) y se caía.

    Medido, con PostgreSQL 16 y la sonda `scripts/sonda_vaciado_en_postgresql.py`, en dos pasadas sobre la
    misma base: **con ese paso dentro, 1 usuario antes y 1 después (no vacía); sin él, 1 y 0 (vacía)**.

    La lección vale más que el arreglo: **un `try/except` que se traga un error «que no importa» no es
    inofensivo si el motor castiga ese error abortando la transacción**. Un error suposo no es lo mismo en
    todos los motores.

    **Y en PostgreSQL se vacía a su manera**: `TRUNCATE … RESTART IDENTITY CASCADE`, que deja lo mismo
    —ninguna fila y los identificadores a cero— pero en una sola orden y sin dejar los contadores por
    donde iban. Sin reiniciarlos, una prueba que da por hecho que la primera factura tiene el id 1 se
    encuentra con el 37 y falla **por un motivo que no es del programa**: es lo que le pasaba a
    `tests/test_revision_t11.py:497`, que buscaba `Factura.id <= 2` y en PostgreSQL no encontraba nada.
    """
    if engine.dialect.name == "postgresql":
        tablas = ", ".join(f'"{tabla.name}"' for tabla in models.Base.metadata.sorted_tables)
        with engine.begin() as conexion:
            conexion.exec_driver_sql(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE")
        return
    with engine.begin() as conexion:
        for tabla in reversed(models.Base.metadata.sorted_tables):
            conexion.execute(tabla.delete())
    # `sqlite_sequence` es la que lleva el «por dónde iba» de los identificadores automáticos, y **solo
    # existe en SQLite**. Sin reiniciarla, el primer id de cada test sería 732 en vez de 1, y cualquier
    # test que compare un id se volvería frágil. Fuera de la transacción de arriba, y solo donde existe.
    if engine.dialect.name == "sqlite":
        with engine.begin() as conexion:
            try:
                conexion.exec_driver_sql("DELETE FROM sqlite_sequence")
            except Exception:  # noqa: BLE001 — la tabla solo existe si hay columnas automáticas
                pass


@pytest.fixture
def cliente(base_limpia):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def cuenta(cliente):
    respuesta = cliente.post("/api/cuenta/registro", json=DATOS_CUENTA)
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    return {**datos, "cabeceras": {"Authorization": f"Bearer {datos['token']}"}}


@pytest.fixture
def crear_cuenta(cliente):
    """Para los tests de aislamiento entre fincas."""

    def _crear(correo: str, nombre: str = "Otro agricultor", nif: str = "12345678Z"):
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                **DATOS_CUENTA,
                "correo": correo,
                "nombre": nombre,
                "explotacion": {**DATOS_CUENTA["explotacion"], "nombre": nombre, "nif": nif},
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        return {**datos, "cabeceras": {"Authorization": f"Bearer {datos['token']}"}}

    return _crear


@pytest.fixture
def campana(cliente, cuenta):
    respuesta = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@pytest.fixture
def crear_parcela(cliente, cuenta):
    def _crear(**cambios):
        datos = {
            "alias": "El Prado",
            "ref_sigpac": "37-455-12-3",
            "superficie_ha": 2.43,
            "superficie_oficial": True,
            "sistema": "secano",
            "uso_sigpac": "Labor secano",
            "municipio": "Peñaranda de Bracamonte",
            "provincia": "Salamanca",
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/parcelas", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def parcela(crear_parcela):
    return crear_parcela()


@pytest.fixture
def crear_producto(cliente, cuenta):
    def _crear(**cambios):
        datos = {
            "nombre_comercial": "Ejemplo 25 EC",
            "numero_registro": "24.123",
            "materia_activa": "Tebuconazol",
            "dosis_maxima": 0.8,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 21,
            "lote": "L-2026-01",
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/productos", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def producto(crear_producto):
    return crear_producto()


@pytest.fixture
def crear_aplicador(cliente, cuenta):
    def _crear(**cambios):
        datos = {
            "nombre": "David Pérez",
            "numero_ropo": "ROPO-1234",
            "numero_carne": "C-123456",
            "tipo_carne": "Cualificado",
            "fecha_caducidad_carne": "2030-01-01",
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/aplicadores", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def aplicador(crear_aplicador):
    return crear_aplicador()


@pytest.fixture
def crear_equipo(cliente, cuenta):
    def _crear(**cambios):
        datos = {
            "nombre": "Pulverizador grande",
            "tipo": "Atomizador",
            "numero_roma": "ROMA-9876",
            "fecha_iteaf": "2024-03-01",
            "fecha_proxima_iteaf": "2029-03-01",
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/equipos", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def equipo(crear_equipo):
    return crear_equipo()


@pytest.fixture
def crear_instalacion(cliente, cuenta):
    def _crear(**cambios):
        datos = {
            "alias": "El almacén grande",
            "tipo": "almacen",
            "municipio": "Peñaranda de Bracamonte",
            "uso": "Guardar el grano",
        }
        datos.update(cambios)
        respuesta = cliente.post(
            "/api/instalaciones", headers=cuenta["cabeceras"], json=datos
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def instalacion(crear_instalacion):
    return crear_instalacion()


@pytest.fixture
def nuevo_tratamiento_en_instalacion(campana, instalacion, producto):
    """Un tratamiento de una nave: sin parcela y sin hectáreas, que es lo correcto."""

    def _crear(**cambios):
        datos = {
            "campana_id": campana["id"],
            "fecha": "2026-06-10",
            "tipo": "instalaciones",
            "instalacion_id": instalacion["id"],
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto["id"],
            "dosis": 0.5,
            "plazo_reentrada_dias": 3,
        }
        datos.update(cambios)
        return datos

    return _crear


@pytest.fixture
def fertilizante(cliente, cuenta):
    respuesta = cliente.post(
        "/api/fertilizantes",
        headers=cuenta["cabeceras"],
        json={
            "nombre": "Nitrato amónico 33,5%",
            "tipo": "mineral",
            "riqueza_n": 33.5,
            "riqueza_p": 0.0,
            "riqueza_k": 0.0,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


@pytest.fixture
def nuevo_tratamiento(campana, parcela, producto):
    """Un tratamiento completo y correcto, al que se le cambia lo que pruebe cada test."""

    def _crear(**cambios):
        datos = {
            "campana_id": campana["id"],
            "fecha": FECHA_TRATAMIENTO,
            "parcela_id": parcela["id"],
            "superficie_tratada_ha": 2.43,
            "cultivo": "Trigo blando",
            "plaga": "Roya amarilla",
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto["id"],
            "dosis": 0.8,
            "franja_seguridad_respetada": True,
        }
        datos.update(cambios)
        return datos

    return _crear


@pytest.fixture
def db_sesion():
    """Una sesión de base de datos directa, para poder mirar lo que se ha guardado.

    Hace falta cuando lo que hay que comprobar no sale por la API: por ejemplo, la geometría de
    una parcela, que se guarda pero no se devuelve en el listado.
    """
    from app.database import SessionLocal

    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def crear_asesor(cliente, cuenta):
    def _crear(**cambios):
        datos = {
            "nombre": "Ana García Ruiz",
            "nif": "12345678Z",
            "numero_ropo": "ROPO-ASESOR-778",
            "ambito": "gip",
            "entidad_certificacion": "Producción Integrada de Castilla y León",
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/asesores", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def asesor(crear_asesor):
    return crear_asesor()


@pytest.fixture
def nueva_fertilizacion(campana, parcela, fertilizante):
    def _crear(**cambios):
        datos = {
            "campana_id": campana["id"],
            "fecha": "2026-02-20",
            "parcela_id": parcela["id"],
            "superficie_ha": 2.43,
            "fertilizante_id": fertilizante["id"],
            "kg_ha_producto": 300.0,
            "modo_aplicacion": "al suelo",
            "momento": "fondo",
        }
        datos.update(cambios)
        return datos

    return _crear


# Un análisis de suelo con los nueve números del contenido mínimo del CUE, que es lo que
# de verdad trae un boletín de tierra.
PARAMETROS_SUELO = [
    {"clave": "materia_organica", "valor": 1.8},
    {"clave": "arena", "valor": 62.0},
    {"clave": "limo", "valor": 24.0},
    {"clave": "arcilla", "valor": 14.0},
    {"clave": "ph", "valor": 7.4},
    {"clave": "fosforo_asimilable", "valor": 18.0},
    {"clave": "potasio_asimilable", "valor": 210.0},
    {"clave": "nitrogeno_total", "valor": 0.12},
    {"clave": "conductividad", "valor": 0.31},
]


@pytest.fixture
def crear_analitica(cliente, cuenta):
    def _crear(**cambios):
        datos = {
            "campana_id": cambios.pop("campana_id", None),
            "tipo": "suelo",
            "fecha_toma_muestra": "2026-02-14",
            "fecha_resultado": "2026-02-28",
            "laboratorio": "Laboratorio Agrario de Villamuriel",
            "nif_laboratorio": "B34123456",
            "numero_informe": "2026/0417",
            "parametros": [dict(p) for p in PARAMETROS_SUELO],
        }
        datos.update(cambios)
        if datos["campana_id"] is None:
            campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
            datos["campana_id"] = campana["id"]
        respuesta = cliente.post("/api/analiticas", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def analitica(crear_parcela, crear_analitica):
    """Un análisis de suelo ya atado a una parcela, que es el caso que se usa de verdad."""
    parcela = crear_parcela()
    return crear_analitica(parcela_id=parcela["id"])


@pytest.fixture
def declarar_medidas(cliente, cuenta):
    """Declara las medidas preventivas de la finca, como lo hace la pantalla."""

    def _declarar(aplicadas: list[str], observaciones: dict | None = None):
        respuesta = cliente.put(
            "/api/medidas",
            headers=cuenta["cabeceras"],
            json={"aplicadas": aplicadas, "observaciones": observaciones or {}},
        )
        assert respuesta.status_code == 200, respuesta.text
        return respuesta.json()

    return _declarar


@pytest.fixture
def una_venta(campana, parcela):
    """Una venta completa y correcta, a la que se le cambia lo que pruebe cada test."""

    def _crear(**cambios):
        datos = {
            "campana_id": campana["id"],
            "tipo": "comercializada",
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "variedad": "Craklin",
            "cantidad": 42000.0,
            "unidad": "kg",
            "lote": "L-2026-07",
            "comprador": "Cooperativa Agrícola de Peñaranda",
            "numero_albaran": "ALB-2026-118",
            "parcela_id": parcela["id"],
        }
        datos.update(cambios)
        return datos

    return _crear


@pytest.fixture
def crear_venta(cliente, cuenta, una_venta):
    def _crear(**cambios):
        respuesta = cliente.post(
            "/api/ventas", headers=cuenta["cabeceras"], json=una_venta(**cambios)
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def venta(crear_venta):
    return crear_venta()

@pytest.fixture
def db():
    """**Una sesion de base de datos**, para lo que no se ve desde las puertas.

    Hay cosas que solo se pueden comprobar mirando la base: el **rastro** de la auditoria -que no tiene
    puerta de lectura-, y la **concurrencia**, que necesita **dos sesiones a la vez** para reproducir la
    ventana entre «mirar» y «escribir». Se abre con el mismo generador que usa la aplicacion, y se llama `db`
    porque es el nombre que ya usaban las pruebas de esta casa para esto.

    Vive aqui y no en un fichero de pruebas porque la usan **dos**, y dos definiciones de lo mismo es
    justamente lo que esta casa no quiere.
    """
    from app.database import SessionLocal

    with SessionLocal() as sesion:
        yield sesion
