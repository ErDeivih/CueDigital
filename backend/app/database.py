"""Conexión a base de datos.

Decisión: SQLite por defecto para desarrollo y para los tests, PostgreSQL +
PostGIS en producción, con la MISMA capa SQLAlchemy. El motivo es que los tests
tienen que poder correr en cualquier sitio sin levantar un servidor, y el
cuaderno de campo se tiene que poder probar sin Docker.

Decisión: la geometría de la parcela se guarda como texto WKT en `Parcela.geometria`.
Es deliberado: así el mismo código funciona en SQLite y en PostgreSQL. Cuando se
pase a PostGIS se cambia esa columna por `Geometry("POLYGON", srid=4326)` y las
consultas espaciales se añaden encima, sin tocar los servicios ni las validaciones.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import String, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

URL_POR_DEFECTO = "sqlite:///./cuedigital.db"


def url_base_datos() -> str:
    return os.environ.get("CUEDIGITAL_DATABASE_URL", URL_POR_DEFECTO)


def _es_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def crear_engine(url: str | None = None) -> Engine:
    url = url or url_base_datos()
    argumentos: dict = {"future": True}

    if _es_sqlite(url):
        # check_same_thread=False: FastAPI atiende peticiones en hilos distintos y
        # SQLite por defecto lo prohíbe. Con un fichero por proceso es seguro.
        argumentos["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            # Base de datos en memoria compartida entre conexiones: sin StaticPool
            # cada conexión vería una base distinta y los tests fallarían de forma
            # desconcertante.
            argumentos["poolclass"] = StaticPool

    return create_engine(url, **argumentos)


engine = crear_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _activar_claves_foraneas(dbapi_connection, _registro) -> None:
    """SQLite ignora las claves foráneas salvo que se le diga lo contrario.

    Sin esto, un borrado dejaría registros huérfanos y el aislamiento entre
    explotaciones se podría romper sin que salte ningún aviso.
    """
    modulo = type(dbapi_connection).__module__
    if "sqlite3" not in modulo:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TextoQueNoCabe(RuntimeError):
    """Un texto que se iba a guardar **no cabe en su columna**.

    Se levanta **antes** de mandar nada a la base, así que la operación no se pierde a medias y el aviso
    dice qué texto, dónde y cuánto cabe. Ver `_comprobar_que_los_textos_caben`.
    """


# **La comprobación que faltaba, y que era un defecto de producción de 170 campos** (02/10/2026).
#
# El problema: un `VARCHAR(n)` en SQLite **no comprueba nada** —guarda un texto de 300 caracteres en una
# columna de 200 tan contento— y en PostgreSQL **sí**: la fila se rechaza con
# `StringDataRightTruncation`, y como el rastro y el apunte van en la misma transacción, **lo que se
# pierde es la operación entera**. Medido: los esquemas de entrada de este programa dejan meter texto sin
# tope en **170 campos** que acaban en columnas con tope, así que el mismo cuerpo que se apunta en el
# ordenador del agricultor **no se puede apuntar en producción**. Y como el móvil reintenta los 5xx, cada
# uno de esos casos es un bucle.
#
# Se podía haber arreglado escribiendo 170 `max_length` a mano en los esquemas, y se habrían quedado
# viejos igual que se quedó el `varchar(30)` del rastro: el día que alguien añada una columna o cambie un
# ancho, nadie se acuerda. **Se comprueba donde no se puede olvidar: justo antes de escribir.**
#
# Y de paso arregla la otra mitad del problema: **las dos bases dejan de comportarse distinto**. Hasta
# hoy, lo que SQLite guardaba y PostgreSQL rechazaba hacía que el mismo programa tuviera dos
# comportamientos según dónde corra; ahora los dos dicen lo mismo, y lo dice el programa, en castellano.
@event.listens_for(Session, "before_flush")
def _comprobar_que_los_textos_caben(sesion: Session, _contexto, _instancias) -> None:
    """Antes de escribir: ningún texto puede ser más largo que su columna.

    Se mira lo que se va a **crear** y lo que se va a **modificar** (lo que solo se lee no se toca), y
    solo las columnas de texto que declaran un tope: las que no lo declaran (`Text`) admiten lo que sea.
    """
    for objeto in [*sesion.new, *sesion.dirty]:
        tabla = getattr(type(objeto), "__table__", None)
        if tabla is None:
            continue
        for columna in tabla.columns:
            tope = getattr(columna.type, "length", None)
            if not isinstance(columna.type, String) or not tope:
                continue
            valor = getattr(objeto, columna.key, None)
            if isinstance(valor, str) and len(valor) > tope:
                raise TextoQueNoCabe(
                    f"El texto de «{tabla.name}.{columna.name}» mide {len(valor)} caracteres y su "
                    f"columna admite {tope}. No se ha guardado nada. Acorta el texto, o ensancha la "
                    "columna con una migración de verdad: en SQLite no se nota —no comprueba la "
                    "longitud—, pero en PostgreSQL la operación entera se pierde."
                )


def asegurar_columnas(destino_engine: Engine | None = None) -> tuple[list[str], list[str]]:
    """Añade a las tablas que ya existen las columnas que les falten.

    **Hace falta de verdad, y es el fallo que aparece al actualizar.** `create_all` crea
    las tablas que no están, pero **no toca las que ya existen**: si se añade un campo a
    una tabla, en una base de datos con datos dentro el programa revienta con un
    «no such column» y el agricultor se queda sin poder entrar.

    Devuelve dos listas: las columnas que se han añadido y las que no se han podido.
    Una columna no se puede añadir en SQLite si es obligatoria y no trae valor por
    defecto; esas se devuelven en la segunda lista para que quien arranque el programa
    pueda avisar, en vez de fallar en silencio.
    """
    from sqlalchemy import inspect, text

    from . import models

    motor = destino_engine or engine
    inspector = inspect(motor)
    anadidas: list[str] = []
    imposibles: list[str] = []

    for tabla in models.Base.metadata.sorted_tables:
        if not inspector.has_table(tabla.name):
            continue
        existentes = {columna["name"] for columna in inspector.get_columns(tabla.name)}
        for columna in tabla.columns:
            if columna.name in existentes:
                continue

            tipo = columna.type.compile(motor.dialect)
            defecto = _valor_por_defecto(columna)
            if not columna.nullable and defecto is None:
                imposibles.append(f"{tabla.name}.{columna.name}")
                continue

            sentencia = f'ALTER TABLE "{tabla.name}" ADD COLUMN "{columna.name}" {tipo}'
            if defecto is not None:
                sentencia += f" DEFAULT {defecto}"
            try:
                with motor.begin() as conexion:
                    conexion.execute(text(sentencia))
                anadidas.append(f"{tabla.name}.{columna.name}")
            except Exception:
                imposibles.append(f"{tabla.name}.{columna.name}")

    return anadidas, imposibles


def _valor_por_defecto(columna) -> str | None:
    """El DEFAULT que hay que ponerle a una columna nueva, en SQL.

    Se mira en dos sitios, por este orden:

    1. **El valor por defecto de la base de datos** (`server_default`). `func.now()` se
       traduce a CURRENT_TIMESTAMP, que es lo que entiende SQLite.
    2. **El valor por defecto de Python** (`default=0.0`, `default="almacen"`). Hace falta
       porque SQLite **no deja añadir una columna obligatoria sin valor por defecto**, y
       sin esto habría columnas que no se podrían añadir nunca. Poner el mismo valor que
       habría puesto Python es lo correcto: las filas que ya existían se quedan igual que
       si se hubieran creado con el modelo de ahora.
    """
    defecto = columna.server_default
    if defecto is not None:
        crudo = str(getattr(defecto, "arg", defecto)).strip()
        if crudo.lower() in ("now()", "current_timestamp", "current_timestamp()"):
            return "CURRENT_TIMESTAMP"
        if crudo.lower() in ("true", "false"):
            return crudo.upper()
        if crudo.replace(".", "", 1).replace("-", "", 1).isdigit():
            return crudo
        return _cita(crudo.strip("'"))

    por_defecto = columna.default
    if por_defecto is not None and not por_defecto.is_callable and not por_defecto.is_sequence:
        valor = por_defecto.arg
        if isinstance(valor, bool):
            return "1" if valor else "0"
        if isinstance(valor, (int, float)):
            return str(valor)
        if isinstance(valor, str):
            return _cita(valor)

    # Una columna que admite nada siempre se puede añadir, aunque sea vacía.
    return "NULL" if columna.nullable else None


def _cita(texto: str) -> str:
    """Un texto listo para meterlo en SQL, con las comillas dobladas."""
    return "'" + str(texto).replace("'", "''") + "'"


# Las columnas que en su día se crearon como un «sí o no» obligatorio y que hoy tienen que poder
# decir **«no se ha podido comprobar»**.
#
# **Por qué esto necesita una reconstrucción de la tabla y `asegurar_columnas` no basta.** SQLite
# no sabe cambiar la nulabilidad de una columna que ya está creada: no existe un
# `ALTER TABLE ... ALTER COLUMN`. La única forma que da el manual de SQLite es crear la tabla de
# nuevo con el esquema bueno, copiar las filas, tirar la vieja y renombrar. Y hay que hacerlo en el
# arranque, por el mismo motivo por el que se añaden columnas al arrancar: si no, el agricultor que
# actualiza el programa se encuentra con que apuntar un abono en una tierra cuya zona de nitratos no
# se conoce revienta, y no sabría por qué.
#
# Se dice el nombre en parejas (tabla, columna) a propósito, en vez de mirar el modelo entero: una
# reconstrucción toca una tabla entera, y eso solo se hace donde hace falta y sabiendo por qué.
COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS: tuple[tuple[str, str], ...] = (
    ("tratamientos", "en_zona_vulnerable"),
    ("fertilizaciones", "en_zona_vulnerable"),
    # La autorización de un producto del catálogo (A1 de `docs/T02_VALORES_POR_DEFECTO.md`): nació
    # como `True` por defecto, es decir, «autorizado y permitido en ecológico» sin que nadie lo
    # hubiera dicho. Pasa a tres estados, con `None` = «no comprobado».
    ("productos_fitosanitarios", "autorizado"),
    ("productos_fitosanitarios", "permitido_ecologico"),
    # **A6 (03/10/2026): la composición de un abono puede ser «no consta».** Nació con `0.0` por defecto, y
    # un 0 % de nitrógeno, fósforo y potasio no es «no lo sé»: es afirmar que el abono no lleva nada, y eso
    # entraba en el cálculo, en el volcado de la Junta y en el documento que se firma. Tres estados también
    # aquí, en la ficha del abono y en la copia que guarda cada apunte.
    ("fertilizantes", "riqueza_n"),
    ("fertilizantes", "riqueza_p"),
    ("fertilizantes", "riqueza_k"),
    ("fertilizaciones", "riqueza_n"),
    ("fertilizaciones", "riqueza_p"),
    ("fertilizaciones", "riqueza_k"),
    # Y las unidades fertilizantes se **calculan** desde la riqueza (`uf = kg/ha × riqueza / 100`): sin
    # riqueza no hay cifra, así que no pueden guardar un 0 que parezca calculado. Son las seis de la tabla
    # de abonos; las superficies de abonos y labores son datos conocidos y siguen obligatorias.
    ("fertilizaciones", "uf_n_ha"),
    ("fertilizaciones", "uf_p_ha"),
    ("fertilizaciones", "uf_k_ha"),
    ("fertilizaciones", "uf_n_total"),
    ("fertilizaciones", "uf_p_total"),
    ("fertilizaciones", "uf_k_total"),
    # **A7 (03/10/2026): la superficie de una tierra puede ser «no lo sé».** Al importar el cuaderno de la
    # Junta sin la casilla de la superficie cultivada, la tierra quedaba con 0 hectáreas; y como la
    # comprobación `V4_superficie_excedida` compara con eso, **la tierra dejaba de poder tratarse** (cualquier
    # superficie la superaba). Con la columna anulable, la tierra se puede tratar y el programa dice que
    # falta el dato y cómo ponerlo (proponiendo la del recinto del SIGPAC, sin escribirla).
    ("parcelas", "superficie_ha"),
    # **A12 y A13 (05/10/2026): tres campos más que pueden decir «no lo sé».** Los tres nacieron con un
    # `False` por defecto, y ese «no» que nadie había dicho tenía consecuencias de verdad: `produccion_ecologica`
    # **apagaba la comprobación ecológica** y salía en el documento que se firma; y `masa_agua_cerca` y
    # `captacion_consumo_humano` **aligeraban las restricciones de abonado** y la franja de seguridad de un
    # tratamiento, porque el programa leía «aquí no hay agua». Sin esta reconstrucción, en una base ya creada
    # las columnas seguirían siendo obligatorias y guardar un «no lo sé» fallaría.
    ("explotaciones", "produccion_ecologica"),
    ("parcelas", "masa_agua_cerca"),
    ("parcelas", "captacion_consumo_humano"),
    # **A10 y A11 (05/10/2026): el sistema de una tierra y de quién es una máquina también pueden decir
    # «no lo sé».** Los cuatro nacieron con un valor por defecto que **afirmaba algo que nadie había
    # dicho**: `sistema = "secano"` declaraba de secano una tierra de regadío (y la exportación de la
    # Junta escribía «S» en su casilla, además de comparar el abonado contra el límite que no es), y
    # `titularidad = "propia"` ponía la máquina de la empresa de servicios en la lista de las propias, con
    # su ITEAF como si fuera una obligación del agricultor. Sin esta reconstrucción, en una base ya creada
    # las columnas seguirían siendo obligatorias y guardar un «no lo sé» fallaría. Las filas que ya existen
    # **se copian tal cual**: lo que cambia es lo de adelante.
    ("parcelas", "sistema"),
    ("parcela_cultivos", "sistema"),
    ("grupos_parcelas", "sistema"),
    ("equipos_aplicacion", "titularidad"),
)

# **Tablas que hay que reconstruir para que nazca una CLAVE AJENA** (14/10/2026).
#
# POR QUÉ ES UNA LISTA APARTE. La de arriba se llama «columnas que dejaron de ser obligatorias» y sirve para
# poder guardar un «no se sabe»; esto es otra cosa: aquí falta una **clave ajena que el modelo declara y la
# base del agricultor no tiene**. Se dice con su nombre para que nadie tenga que adivinar por qué está aquí una
# tabla que no tiene ninguna columna anulable.
#
# EL CASO, medido (`CRM-04-FUSION-INVENTARIO.md`): `ventas_de_cosecha.contacto_id` **no tiene clave ajena en la
# base del agricultor**. En una base nueva sí; en la migrada no, porque `asegurar_columnas` usa `ALTER TABLE ADD
# COLUMN` —y SQLite **no puede añadir una clave ajena así**—. De las seis columnas de dinero que una fusión
# tendría que repuntar, es **la única cuyo error no caza la base**: una venta puede quedarse apuntando a una
# ficha que no existe y nadie se entera.
TABLAS_QUE_NECESITAN_RECONSTRUIRSE_POR_UNA_CLAVE_AJENA: tuple[str, ...] = (
    "ventas_de_cosecha",
)


def las_claves_ajenas_que_faltan(motor: Engine, tabla: str) -> set[str]:
    """Las columnas de esa tabla que el modelo declara con clave ajena y la base **no** tiene (solo SQLite)."""
    if motor.dialect.name != "sqlite":
        return set()
    # **El import va aquí dentro a propósito**: `database.py` no importa los modelos arriba (sería un círculo,
    # porque los modelos necesitan la base para declararse), así que se pide dentro, que es cuando ya está todo.
    from . import models  # noqa: PLC0415

    # **`PRAGMA foreign_key_list` da la tabla referenciada en el índice 2 y la columna LOCAL en el 3.** La
    # primera vez leí el 2, así que comparaba nombres de COLUMNA contra nombres de TABLA: la resta salía
    # siempre con algo y la tabla se habría reconstruido **en cada arranque** — que es justo lo contrario de lo
    # que hace falta. Lo cazó la prueba de idempotencia.
    with motor.connect() as conexion:
        declaradas = {fila[3] for fila in conexion.exec_driver_sql(f'PRAGMA foreign_key_list("{tabla}")')}
    del_modelo = {
        columna.name
        for columna in models.Base.metadata.tables[tabla].columns
        if columna.foreign_keys
    }
    return del_modelo - declaradas


def reconstruir_para_que_nazcan_las_claves_ajenas(motor: Engine) -> list[str]:
    """**Reconstruye las tablas a las que les falta una clave ajena**, sin tocar ni una fila.

    `_reconstruir_tabla` copia todas las filas y las deja igual: lo que cambia es el esquema de delante. Y es
    **idempotente**: si la clave ya está, no se toca nada.
    """
    pendientes = [
        tabla
        for tabla in TABLAS_QUE_NECESITAN_RECONSTRUIRSE_POR_UNA_CLAVE_AJENA
        if las_claves_ajenas_que_faltan(motor, tabla)
    ]
    if not pendientes:
        return []

    # **Sin copia no se reconstruye**, con las mismas palabras y el mismo motivo que la función de al lado: una
    # base en memoria o PostgreSQL no se pueden copiar aquí, y lo honesto es **parar y decirlo** en vez de
    # reconstruir sin vuelta atrás. Lo LEÍ antes de escribir esto, en vez de suponerlo.
    if _ruta_del_fichero(motor) is None:
        raise RuntimeError(
            "Esta base no es un fichero de SQLite, así que no se puede guardar una copia antes de "
            "reconstruir tablas, y sin copia no se reconstruye nada. En PostgreSQL (o en una base en "
            "memoria) hace falta una migración de verdad, con su copia y su herramienta. No se ha tocado nada."
        )
    copia = _copia_de_seguridad_del_fichero(motor)

    reconstruidas: list[str] = []
    for tabla in pendientes:
        # **Se pasa el objeto de la tabla**, no su nombre: así lo hace la función de al lado. (La primera vez pasé
        # el nombre; se habría visto al llamarla de verdad, y por eso la pruebo suelta antes de armarla.)
        _reconstruir_tabla(motor, models.Base.metadata.tables[tabla], copia=copia)
        reconstruidas.append(tabla)
    return reconstruidas


def reconstruir_para_poder_decir_no_se(
    destino_engine: Engine | None = None, *, copia_ya_hecha: str | None = None
) -> list[str]:
    """Deja que esas columnas admitan el tercer estado: `True`, `False` o «no se sabe».

    Devuelve las columnas que ha tenido que reconstruir (`tabla.columna`), y la lista vacía si ya
    estaban bien. Es idempotente: la segunda vez no encuentra nada que hacer.

    **Esto no convierte ningún dato.** Las filas que ya existen se copian tal cual, con el valor
    que tenían; lo que cambia es que la columna admite desde ahora el tercer estado. Los datos
    viejos —incluidos los `False` que en su día se inventaron— se quedan como están hasta que
    alguien decida lo contrario con la migración de datos a la vista, que va aparte y a propósito
    (`backend/scripts/migrar_zona_de_nitratos.py`): reescribir historia es una decisión, no algo
    que deba pasar solo porque el programa arranque.

    `copia_ya_hecha` es la copia que ya ha hecho quien llama (el guion de migración, que necesita su
    camino para poder decirle al agricultor cómo volver atrás). Sirve para **no hacer dos copias** de la
    base del agricultor en la misma ejecución: con la copia coherente y la byte a byte, dos llamadas
    dejaban cuatro ficheros con sus datos que nadie borra después.
    """
    from sqlalchemy import inspect

    from . import models

    motor = destino_engine or engine
    inspector = inspect(motor)

    pendientes: list[tuple[str, str]] = []
    for nombre_tabla, nombre_columna in COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS:
        if not inspector.has_table(nombre_tabla):
            continue
        columnas = {c["name"]: c for c in inspector.get_columns(nombre_tabla)}
        columna = columnas.get(nombre_columna)
        if columna is None or columna["nullable"]:
            continue
        pendientes.append((nombre_tabla, nombre_columna))

    if not pendientes:
        return []

    # **Sin copia no se reconstruye.** Y no hay copia posible si la base no es un fichero: una base en
    # memoria (las pruebas, y nada más) o PostgreSQL (que el proyecto dice que es la de producción). En
    # esos dos casos lo honesto es **parar y decirlo**, no reconstruir sin vuelta atrás: en PostgreSQL esta
    # reconstrucción además no sabría hacerlo (usa `PRAGMA` y `ALTER TABLE … RENAME`, que son de SQLite), y
    # allí esto tiene que ser una migración de verdad, con su herramienta.
    copia = copia_ya_hecha
    if not copia:
        if _ruta_del_fichero(motor) is None:
            raise RuntimeError(
                "Esta base no es un fichero de SQLite, así que no se puede guardar una copia antes de "
                "reconstruir tablas, y sin copia no se reconstruye nada. En PostgreSQL (o en una base en "
                "memoria) hace falta una migración de verdad, con su copia y su herramienta. No se ha "
                "tocado nada."
            )
        copia = _copia_de_seguridad_del_fichero(motor)

    # **Una tabla se reconstruye UNA vez**, aunque tenga dos columnas pendientes: la reconstrucción
    # toca la tabla entera, así que hacerla dos veces sería pasar dos veces por la ventana de
    # riesgo sin ganar nada.
    reconstruidas: list[str] = []
    for nombre_tabla in dict.fromkeys(tabla for tabla, _columna in pendientes):
        _reconstruir_tabla(
            motor, models.Base.metadata.tables[nombre_tabla], copia=copia
        )
        reconstruidas.extend(
            f"{tabla}.{columna}" for tabla, columna in pendientes if tabla == nombre_tabla
        )
    return reconstruidas


def _ruta_del_fichero(motor: Engine):
    """El fichero de la base de datos, si es SQLite en un fichero. `None` si es en memoria."""
    from pathlib import Path

    url = motor.url
    if url.get_backend_name() != "sqlite":
        return None
    fichero = url.database
    if not fichero or fichero == ":memory:":
        return None
    return Path(fichero).resolve()


def _copia_de_seguridad_del_fichero(motor: Engine) -> str | None:
    """Guarda una copia **coherente** de la base al lado, antes de reconstruir nada.

    **Por qué no se copia el fichero sin más.** Hay dos trampas, y las dos se descubrieron
    ensayando:

    1. **El WAL.** Si la base está en modo WAL (lo que deja, por ejemplo, abrirla con un visor de
       SQLite), los cambios **confirmados** pueden seguir en el fichero `-wal` y no estar en el
       principal. Una copia del principal **pasa `quick_check`** —el fichero está entero— y sin
       embargo **le faltan filas**: parecería una vuelta atrás y perdería datos. Por eso la copia se
       hace con la **API de copia de SQLite** (`Connection.backup`), que lee la base entera, WAL
       incluido, y además se comprueba que tiene **las mismas tablas y las mismas filas** que el
       original (`_copia_tiene_lo_mismo`). Si eso no se cumple, **no se reconstruye nada**.
    2. **`VACUUM INTO`.** Saca una copia coherente pero **reorganizada**, así que devolverla al sitio
       no deja el fichero como estaba —y «volver atrás» tiene que querer decir exactamente eso—.
       Por eso, cuando el fichero principal **por sí solo** ya tiene todos los datos (el caso
       normal: no hay nada pendiente en el WAL), se guarda además una copia **byte a byte** y es esa
       la que se devuelve para restaurar. Cuando no los tiene, no se deja una copia incompleta que
       parezca buena: se borra y se devuelve la coherente.

    En el arranque del programa no hay nadie escribiendo todavía (`crear_tablas` va antes de
    atender la primera petición), así que la copia se hace con la base quieta.

    Devuelve el camino de la copia que hay que volver a poner, o `None` si la base no es un fichero.
    """
    import datetime as dt
    import shutil

    ruta = _ruta_del_fichero(motor)
    if ruta is None or not ruta.exists():
        return None
    marca = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    coherente = ruta.with_name(f"{ruta.name}.antes-de-migrar-{marca}")
    if coherente.exists():
        coherente = ruta.with_name(f"{ruta.name}.antes-de-migrar-{marca}-{os.getpid()}")

    _copiar_con_sqlite(ruta, coherente)
    # Una copia que no supera esta comprobación no permite reconstruir tablas.
    if not _la_copia_esta_entera(coherente):
        raise RuntimeError(
            f"La copia previa a la migración no se puede comprobar: {coherente}. "
            "No se ha cambiado la estructura de la base de datos."
        )
    # Y que **tenga los mismos datos**, que es lo que `quick_check` no demuestra.
    #
    # Se intenta **dos veces** (revisión independiente, 02/10/2026): la comprobación se hace contra la base
    # **viva**, así que si otro proceso escribe justo entre la copia y la comprobación, lo que falla no es
    # la copia, es el momento. En vez de decirle al agricultor que su copia está mal —que no es verdad— se
    # vuelve a copiar y se comprueba otra vez; si vuelve a fallar, se le dice **qué está pasando y qué
    # hacer** (cerrar el programa y repetirlo), que es lo único que puede arreglarlo.
    if not _copia_tiene_lo_mismo(ruta, coherente):
        _borrar_copia(coherente)
        _copiar_con_sqlite(ruta, coherente)
        if not _la_copia_esta_entera(coherente) or not _copia_tiene_lo_mismo(ruta, coherente):
            _borrar_copia(coherente)
            raise RuntimeError(
                "No se ha podido guardar una copia con los mismos datos que la base de datos. "
                "Lo más probable es que haya **otro programa escribiendo en ella** (otra ventana del "
                "cuaderno, un visor de SQLite…): ciérralo y vuelve a intentarlo. "
                "No se ha cambiado la estructura de la base de datos."
            )
    _limpiar_los_ficheros_de_al_lado(coherente)

    byte_a_byte = ruta.with_name(f"{coherente.name}-byte-a-byte")
    shutil.copy2(ruta, byte_a_byte)
    if _copia_tiene_lo_mismo(ruta, byte_a_byte) and not _hay_algo_pendiente_en_el_wal(ruta):
        _limpiar_los_ficheros_de_al_lado(byte_a_byte)
        return str(byte_a_byte)
    # El fichero principal no tiene todo por sí solo: se quita la copia que solo lo parece y se
    # devuelve la coherente, que es la que sirve de verdad para volver atrás.
    _borrar_copia(byte_a_byte)
    return str(coherente)


def _limpiar_los_ficheros_de_al_lado(ruta) -> None:
    """Quita el `-wal` y el `-shm` de una copia **cuando están vacíos**.

    Hacen falta porque abrir una copia para comprobarla se los crea si la base viene en modo WAL, y dejarlos
    ahí es basura en la carpeta del agricultor (y una carpeta con `…-byte-a-byte-shm` dentro parece que hay
    una copia cuando ya no la hay). **Si el `-wal` tiene algo dentro NO se toca**: ahí puede haber datos
    confirmados de esa copia, y borrarlo sería perderlos. Se borra solo lo que está vacío, que es lo que
    crea la propia comprobación.
    """
    from pathlib import Path

    wal = Path(f"{ruta}-wal")
    try:
        if wal.exists() and wal.stat().st_size > 0:
            return
    except OSError:  # pragma: no cover - si no se puede mirar, se deja todo como está
        return
    for sufijo in ("-wal", "-shm"):
        try:
            Path(f"{ruta}{sufijo}").unlink(missing_ok=True)
        except OSError:  # pragma: no cover - si no se puede borrar, no se para por eso
            pass


def _borrar_copia(ruta) -> None:
    """Borra una copia **con sus ficheros de al lado** (`-wal`, `-shm`, `-journal`).

    Hace falta borrarlos: al abrir una copia para comprobarla, SQLite le crea sus propios ficheros
    auxiliares, y si se dejan ahí queda media copia suelta en la carpeta del agricultor (y una
    carpeta con `…-byte-a-byte-wal` dentro parece que hay una copia cuando ya no la hay).
    """
    from pathlib import Path

    for sufijo in ("", "-wal", "-shm", "-journal"):
        try:
            Path(f"{ruta}{sufijo}").unlink(missing_ok=True)
        except OSError:  # pragma: no cover - si no se puede borrar, no se para por eso
            pass


def ensayar_la_restauracion(destino, *, motor: Engine | None = None) -> dict:
    """***Restaurar la base en un DESTINO NUEVO, y comprobar que ha llegado entera*** (17/10/2026).

    El ticket de la cola lo pide asi: *«Restauracion: base+adjuntos+configuracion necesaria, **ensayo sobre
    destino nuevo**, integridad…»*. Esto es **la mitad de la base**; los adjuntos son ficheros aparte.

    ***Por que un destino NUEVO, y no la base de siempre***: un ensayo que escribiera encima de la base no
    probaria nada. *La cola lo dice con estas palabras: «nunca restaurar sobre la base real en las pruebas».*

    ***Y por que no basta con copiar***: la copia puede salir bien y quedarse corta -un `-wal` sin leer, un
    fichero a medias-; asi que aqui **se compara tabla por tabla y valor por valor** con
    `_copia_tiene_lo_mismo`. *Copiar sin comprobar no es restaurar: es haber movido bytes.*

    Devuelve lo que hay que poder decir despues: **cuantas tablas**, **si tiene lo mismo** y **si esta
    entera**.
    """
    from pathlib import Path

    motor = motor if motor is not None else crear_engine()
    ruta = _ruta_del_fichero(motor)
    if ruta is None:
        raise RuntimeError(
            "Esta base no es un fichero de SQLite, asi que no se puede ensayar una restauracion sobre un "
            "destino nuevo: en PostgreSQL esto se hace con su herramienta. No se ha tocado nada."
        )
    destino = Path(destino)
    if destino.exists():
        # ***Un destino que ya existe no es un destino nuevo***: escribir encima de algo es justo lo que el
        # ensayo tiene que no hacer.
        raise FileExistsError(f"el destino del ensayo ya existe: {destino}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    _copiar_con_sqlite(ruta, destino)
    return {
        "destino": str(destino),
        "tablas": len(_tablas_de_una_base(destino)),
        "igual": _copia_tiene_lo_mismo(ruta, destino),
        "entera": _la_copia_esta_entera(destino),
    }


def _tablas_de_una_base(ruta) -> list:
    """Los nombres de las tablas de una base, sin las de dentro de SQLite."""
    import sqlite3

    conexion = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    try:
        return [
            fila[0]
            for fila in conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
    finally:
        conexion.close()


def _copiar_con_sqlite(ruta, destino) -> None:
    """Copia la base con la API de copia de SQLite: lee la base entera, **WAL incluido**.

    Es la forma que da SQLite de sacar una copia coherente de una base abierta sin depender de que
    el fichero principal tenga ya todo lo confirmado.
    """
    import sqlite3

    fuente = sqlite3.connect(str(ruta))
    try:
        copia = sqlite3.connect(str(destino))
        try:
            fuente.backup(copia)
        finally:
            copia.close()
    finally:
        fuente.close()


def _hay_algo_pendiente_en_el_wal(ruta) -> bool:
    """Si hay cambios confirmados que todavía viven en el fichero `-wal` y no en el principal."""
    from pathlib import Path

    wal = Path(f"{ruta}-wal")
    try:
        return wal.exists() and wal.stat().st_size > 0
    except OSError:  # pragma: no cover - si no se puede mirar, se da por pendiente
        return True


def _copia_tiene_lo_mismo(ruta, copia) -> bool:
    """Si la copia tiene **las mismas tablas y los mismos datos** que la base.

    Es la comprobación que `quick_check` no hace: un fichero puede estar entero y tener menos filas
    que la base (ver el porqué en `_copia_de_seguridad_del_fichero`).

    **Y no basta con contar las filas** (revisión independiente, 03/10/2026): dos bases con el mismo
    número de filas y **valores distintos** pasaban por buenas, y en una migración eso es justo lo que
    no puede pasar. Ahora se guarda, por tabla, **cuántas filas hay y la huella de sus valores**
    (`_huella_de_una_tabla`): si una sola fila cambia, la huella cambia. Cuesta leer la base entera dos
    veces, y se hace solo cuando hay que reconstruir tablas (una vez, y con la base quieta).

    Se comparan además **las columnas** de cada tabla: un `SELECT *` de dos bases con las columnas en
    otro orden daría filas distintas sin que los datos hayan cambiado (la reconstrucción reordena las
    columnas, y eso es legítimo), así que la huella se calcula **con los nombres delante**.
    """
    import sqlite3

    def retrato(donde) -> dict[str, str] | None:
        try:
            conexion = sqlite3.connect(f"file:{str(donde)}?mode=ro", uri=True)
        except sqlite3.Error:  # pragma: no cover - una copia que no se puede ni abrir
            return None
        try:
            tablas = [
                fila[0]
                for fila in conexion.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            retrato: dict[str, str] = {}
            for tabla in tablas:
                columnas = [c[1] for c in conexion.execute(f'PRAGMA table_info("{tabla}")')]
                retrato[tabla] = _huella_de_una_tabla(conexion, tabla, columnas)
            return retrato
        except sqlite3.Error:  # pragma: no cover - una base a medio copiar
            return None
        finally:
            conexion.close()

    de_la_base = retrato(ruta)
    de_la_copia = retrato(copia)
    return de_la_base is not None and de_la_base == de_la_copia


def _huella_de_una_tabla(conexion, tabla: str, columnas: list[str]) -> str:
    """La huella de todo lo que hay en una tabla: cuántas filas y qué valores.

    Se recorre la tabla **ordenada por `rowid`** (que es estable y lo copia igual la reconstrucción) y se
    van metiendo en el resumen el **nombre de cada columna y el valor de cada fila**, para que el orden
    físico de las columnas no cambie la huella (dos tablas con los mismos datos y las columnas en otro
    orden son la misma tabla). Los valores van con `repr`, que distingue `0` de `0.0` y de `None` y de
    `"0"`, que es exactamente lo que hay que distinguir aquí.
    """
    import hashlib

    resumen = hashlib.sha256()
    resumen.update("|".join(columnas).encode("utf-8"))
    cuantas = 0
    for fila in conexion.execute(f'SELECT * FROM "{tabla}" ORDER BY rowid'):
        resumen.update(b"\x1e")
        resumen.update("|".join(repr(valor) for valor in fila).encode("utf-8", "replace"))
        cuantas += 1
    resumen.update(b"\x1d")
    resumen.update(str(cuantas).encode("utf-8"))
    return resumen.hexdigest()


def _la_copia_esta_entera(ruta) -> bool:
    """Comprueba que la copia se puede abrir y que SQLite la da por buena."""
    import sqlite3

    try:
        conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
        try:
            return conexion.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        finally:
            conexion.close()
    except Exception:  # pragma: no cover - una copia que no se puede ni abrir
        return False


def _donde_esta_la_copia(copia: str | None) -> str:
    """Un recordatorio de dónde quedó la copia, para el mensaje de un fallo."""
    return f" La copia de antes de empezar está en {copia}." if copia else ""


def _huerfanas(cursor, tabla: str) -> list:
    """Las filas de esa tabla que apuntan a un sitio que no existe.

    Se cuentan **antes y después**, y no solo después: una base que ya venía con una fila
    apuntando a nada (pasa: una tierra borrada a mano, un traspaso a medias) no puede impedir que
    el programa se ponga al día. Lo que no se admite es que la reconstrucción **añada** huérfanas.
    """
    return cursor.execute(f'PRAGMA foreign_key_check("{tabla}")').fetchall()


def _reconstruir_tabla(motor: Engine, tabla, *, copia: str | None) -> None:
    """Reconstruye una tabla con el esquema que dice el modelo, conservando todas las filas.

    Son los pasos que manda el manual de SQLite, en este orden: apagar las claves foráneas, crear
    la tabla nueva al lado, copiar las filas, tirar la vieja y renombrar la nueva.

    **Todo va dentro de una transacción**, y eso es lo que hace que sea seguro: SQLite sí sabe
    deshacer estas órdenes (el DDL es transaccional), así que si algo sale mal —un índice que no se
    puede crear, una fila que no cuadra, un fichero lleno— la base se queda exactamente como
    estaba. Y antes de dar el cambio por bueno se comprueba que no hayan aparecido filas apuntando
    a nada que antes no estuvieran.
    """
    from sqlalchemy.schema import CreateIndex, CreateTable

    nombre_temporal = f"{tabla.name}_reconstruida"
    ddl = str(CreateTable(tabla).compile(dialect=motor.dialect))
    cabecera = f"CREATE TABLE {tabla.name} ("
    if cabecera not in ddl:  # pragma: no cover - si SQLAlchemy cambia el DDL, mejor parar
        raise RuntimeError(
            f"no se ha podido reconstruir «{tabla.name}»: el CREATE TABLE no tiene la forma "
            f"esperada. No se ha tocado nada.{_donde_esta_la_copia(copia)}"
        )
    ddl = ddl.replace(cabecera, f'CREATE TABLE "{nombre_temporal}" (', 1)

    columnas = ", ".join(f'"{columna.name}"' for columna in tabla.columns)
    indices = sorted(tabla.indexes, key=lambda indice: indice.name or "")

    cruda = motor.raw_connection()
    try:
        cursor = cruda.cursor()
        # Las claves foráneas se apagan ANTES de abrir la transacción: dentro, SQLite ignora esta
        # orden, y sin apagarlas el `DROP TABLE` de una tabla a la que apuntan otras fallaría.
        cursor.execute("PRAGMA foreign_keys=OFF")
        try:
            huerfanas_antes = len(_huerfanas(cursor, tabla.name))
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(f'DROP TABLE IF EXISTS "{nombre_temporal}"')
            cursor.execute(ddl)
            cursor.execute(
                f'INSERT INTO "{nombre_temporal}" ({columnas}) '
                f'SELECT {columnas} FROM "{tabla.name}"'
            )
            cursor.execute(f'DROP TABLE "{tabla.name}"')
            cursor.execute(f'ALTER TABLE "{nombre_temporal}" RENAME TO "{tabla.name}"')
            # Los índices se van con la tabla vieja, así que hay que volver a crearlos.
            for indice in indices:
                cursor.execute(str(CreateIndex(indice).compile(dialect=motor.dialect)))
            huerfanas_despues = _huerfanas(cursor, tabla.name)
            if len(huerfanas_despues) > huerfanas_antes:
                cursor.execute("ROLLBACK")
                raise RuntimeError(
                    f"«{tabla.name}» se ha quedado con filas que apuntan a nada "
                    f"({huerfanas_despues[:5]}), que antes no estaban. Se ha deshecho el cambio."
                    f"{_donde_esta_la_copia(copia)}"
                )
            cursor.execute("COMMIT")
        except Exception:
            try:
                cursor.execute("ROLLBACK")
            except Exception:  # pragma: no cover - si la transacción ya no está, no hay nada que hacer
                pass
            raise
        finally:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    finally:
        cruda.close()


def asegurar_indices(destino_engine: Engine | None = None) -> tuple[list[str], list[str]]:
    """Pone al día los **índices** de las tablas que ya existen: los que falten y los que cambiaron.

    **Hace falta por lo mismo que `asegurar_columnas`, y es un fallo que se encontró de verdad.**
    `create_all` crea los índices de una tabla **nueva**, pero de una tabla que ya existe no toca
    nada: si la definición de un índice cambia, la instalación que ya tenía esa tabla **se queda con
    el índice viejo** y no recibe el arreglo, en silencio. Pasó con la clave de reenvío de las
    recepciones y los movimientos: pasó a ser única **solo entre las filas vivas** (`WHERE anulada =
    0`) para que un albarán anulado no bloqueara volver a apuntarlo desde el móvil, y una instalación
    que ya hubiera arrancado con la versión anterior se habría quedado con el índice de antes —el que
    provocaba el error—. Lo destapó la revisión independiente (D3, 03/10/2026).

    **No se toca ni una fila.** Un índice se tira y se vuelve a crear sin mirar los datos (medido: las
    huellas de todas las tablas quedan iguales). Por eso esto es seguro donde reconstruir una tabla no
    lo sería.

    Devuelve `(creados, cambiados)` con los nombres, para poder decirlo al arrancar. En SQLite —que es
    donde corre esto— se comparan las definiciones tal y como están guardadas en `sqlite_master`
    contra las que genera el modelo, que salen **idénticas** carácter a carácter. En otro motor no hay
    forma de leer la definición guardada, así que solo se crean los que falten por su nombre: es una
    limitación conocida y se dice, en vez de dar por hecho que están al día.

    **Y si un índice no se puede crear, se dice en castellano y no se deja la base a medias**
    (03/10/2026, lo encontró la revisión independiente). Se puede dar de verdad: una instalación con
    filas repetidas de antes de que el índice único existiera —o después de una restauración a
    medias— se encuentra al arrancar con que hay que crear un índice único que esos datos no cumplen.
    Antes eso salía como una traza de Python en inglés y **el programa no se abría**, porque quien
    llama (`main.py`) solo atrapa `RuntimeError` para contar qué ha pasado y qué hacer. Es la misma
    regla que ya está escrita para el otro caso: «una traza de Python en la consola no le dice nada a
    quien lo ha puesto en marcha». **Y todo el trabajo va en una sola transacción**, así que o quedan
    todos los índices al día o no queda ninguno: nunca la mitad.
    """
    from . import models  # importación tardía: evita dependencia circular

    from sqlalchemy import inspect as sqlalchemy_inspect
    from sqlalchemy import text
    from sqlalchemy.schema import CreateIndex

    motor = destino_engine or engine
    inspector = sqlalchemy_inspect(motor)
    es_sqlite = motor.dialect.name == "sqlite"

    # Primero se mira qué hay (solo lectura) y se decide qué hacer; después se hace todo junto.
    que_hacer: list[tuple[str, object]] = []  # (indice, "crear" | "rehacer")
    creados: list[str] = []
    cambiados: list[str] = []
    for tabla in models.Base.metadata.sorted_tables:
        if not inspector.has_table(tabla.name):
            continue  # una tabla que no existe la crea `create_all` con sus índices
        guardados: dict[str, str | None] = {}
        if es_sqlite:
            with motor.connect() as conexion:
                for nombre, sql in conexion.execute(
                    text(
                        "SELECT name, sql FROM sqlite_master "
                        "WHERE type = 'index' AND tbl_name = :tabla"
                    ),
                    {"tabla": tabla.name},
                ):
                    guardados[nombre] = sql
        else:
            # **En otro motor también se mira qué índices hay, por su nombre** (02/10/2026).
            # Esto no se hacía y era un fallo de los gordos: `guardados` se quedaba vacío, así que
            # **todos** los índices del modelo parecían faltar y se intentaban crear otra vez. En
            # SQLite no se notaba —`sqlite_master` sí se leía—, pero en **PostgreSQL, que es la base
            # de producción**, `crear_tablas()` reventaba con «relation "ix_explotaciones_nif" already
            # exists» y **el programa no arrancaba**: medido con PostgreSQL 16 de verdad, en la
            # primera llamada y sobre una base recién creada (`scripts/sonda_postgresql.py`).
            #
            # Los nombres los da el inspector de SQLAlchemy en cualquier dialecto; lo que no se puede
            # leer fuera de SQLite es la **definición** guardada, y por eso más abajo, en otro motor,
            # solo se crea lo que falta y no se rehace nada.
            for indice_guardado in inspector.get_indexes(tabla.name):
                nombre_guardado = indice_guardado.get("name")
                if nombre_guardado:
                    guardados[nombre_guardado] = None
        for indice in tabla.indexes:
            definicion = str(CreateIndex(indice).compile(dialect=motor.dialect)).strip()
            if indice.name not in guardados:
                que_hacer.append((indice, "crear"))
                creados.append(indice.name)
                continue
            if not es_sqlite:
                continue
            if (guardados[indice.name] or "").strip() == definicion:
                continue
            que_hacer.append((indice, "rehacer"))
            cambiados.append(indice.name)

    if que_hacer:
        try:
            # **Una sola transacción para todo.** SQLite deshace el DDL, así que un fallo a mitad deja
            # la base exactamente como estaba: ni un índice a medio hacer, ni una fila tocada.
            with motor.begin() as conexion:
                for indice, que in que_hacer:
                    if que == "rehacer":
                        conexion.execute(text(f'DROP INDEX IF EXISTS "{indice.name}"'))
                    conexion.execute(CreateIndex(indice))
        except Exception as fallo:  # noqa: BLE001 - se traduce a un aviso en castellano
            nombres = ", ".join(str(indice.name) for indice, _ in que_hacer)
            raise RuntimeError(
                "No se han podido poner al día los índices de la base de datos "
                f"({nombres}), y la base se ha quedado como estaba. Se ha intentado sobre "
                f"«{motor.dialect.name}». Suele pasar por dos motivos: porque hay datos repetidos "
                "que un índice único no admite —por ejemplo dos albaranes con la misma clave de "
                "reenvío—, o porque el índice ya está en la base con otro nombre. "
                f"El programa no ha arrancado. Detalle: {fallo}"
            ) from fallo

    return creados, cambiados


def rellenar_la_huella_del_comando(destino_engine: Engine | None = None) -> tuple[int, int, int]:
    """Deja las facturas que ya existían en condiciones para la clave que no se recicla (09/10/2026).

    **Por qué hace falta, y por qué antes de los índices.** Tres cosas cambiaron el 09/10/2026, a
    petición de David, y las tres necesitan tocar datos de una instalación que ya venía de antes:

      1. **`facturas.clave_de_reenvio` pasa a ser única siempre** (antes se excluían las anuladas). Si una
         instalación tiene dos facturas con la misma clave —una de ellas anulada, que es justo lo que la
         regla vieja permitía—, el índice único **no se puede crear** y el programa no arranca. Se resuelve
         dejando la clave en la **más antigua** (la que atendió la petición) y **quitándosela a las
         demás**. No se borra ni una fila ni se toca ningún dato del papel: se suelta una clave, y esas
         facturas quedan como cualquier otra sin clave. Se dice cuántas, para que no sea un cambio mudo.
      2. **La huella del comando** (`huella_de_la_peticion`) no existe en las facturas de antes. Se
         rellena con la huella de **lo que la factura dice hoy**: así el reenvío de su comando se reconoce
         si nadie la ha corregido, y si se corrigió, lo que llegue distinto será un conflicto —que es la
         parte prudente de la duda, y se prefiere a aceptar en silencio algo que no se puede comprobar—.
      3. **La clave del papel** (`clave_del_papel`), la que hace que **la base** impida que el mismo
         documento entre dos veces. Se rellena con lo que cada factura dice, y si aparecen **dos facturas
         vivas del mismo papel** —que es un duplicado de verdad, de los que la regla vieja dejaba pasar— se
         le deja la clave a la **más antigua** y las demás la sueltan. **No se borra ninguna**: el
         duplicado sigue a la vista para que lo resuelva el agricultor, y a partir de ahí ya no entra otro
         igual.

    Devuelve `(claves_soltadas, huellas_rellenadas, papeles_soltados)`.
    """
    from sqlalchemy import inspect, text

    motor = destino_engine or engine
    inspector = inspect(motor)
    if not inspector.has_table("facturas"):
        return 0, 0, 0
    columnas = {columna["name"] for columna in inspector.get_columns("facturas")}
    if "clave_de_reenvio" not in columnas:
        return 0, 0, 0

    # **`anulada` no se escribe igual en los dos motores** (CRM-00, 11/10/2026). Esta migración lleva SQL a
    # mano, y el SQL de antes decía `anulada = 0` en todas partes: en SQLite una columna booleana es un
    # entero y eso vale, pero en PostgreSQL es un `boolean` de verdad y `= 0` **no compila**. El revisor lo
    # señaló («la migración nueva contiene SQL `anulada = 0`: revisar la portabilidad con booleanos reales
    # antes de activar ese motor») y esto es ese repaso: la condición se escribe una vez, según el motor.
    # Se dice lo que se ha comprobado —que el SQL es el de cada motor— y **no** que se haya probado contra
    # PostgreSQL, porque aquí no hay ninguno (ver el límite declarado en el contrato).
    no_anulada = "anulada = false" if motor.dialect.name.startswith("postgres") else "anulada = 0"

    # Las claves repetidas: se queda con ella la más antigua (el identificador más bajo, que es el orden
    # en que se apuntaron) y las demás la sueltan.
    soltadas = 0
    with motor.begin() as conexion:
        repetidas = conexion.execute(
            text(
                "SELECT explotacion_id, clave_de_reenvio, COUNT(*) AS cuantas, MIN(id) AS la_primera "
                "FROM facturas WHERE clave_de_reenvio IS NOT NULL "
                "GROUP BY explotacion_id, clave_de_reenvio HAVING COUNT(*) > 1"
            )
        ).fetchall()
        for fila in repetidas:
            resultado = conexion.execute(
                text(
                    "UPDATE facturas SET clave_de_reenvio = NULL "
                    "WHERE explotacion_id = :explotacion AND clave_de_reenvio = :clave AND id <> :primera"
                ),
                {
                    "explotacion": fila[0],
                    "clave": fila[1],
                    "primera": fila[3],
                },
            )
            soltadas += resultado.rowcount or 0

    # Y las huellas que falten, con lo que la factura dice hoy.
    rellenadas = 0
    if "huella_de_la_peticion" in columnas:
        from . import servicios  # importación tardía: evita dependencia circular

        with motor.begin() as conexion:
            pendientes = conexion.execute(
                text(
                    "SELECT id FROM facturas "
                    "WHERE clave_de_reenvio IS NOT NULL AND huella_de_la_peticion IS NULL"
                )
            ).fetchall()
        for (factura_id,) in pendientes:
            with motor.begin() as conexion:
                la_factura = conexion.execute(
                    text("SELECT * FROM facturas WHERE id = :id"), {"id": factura_id}
                ).mappings().first()
                if la_factura is None:
                    continue
                lineas = conexion.execute(
                    text(
                        "SELECT descripcion, cantidad, unidad, precio_unitario, importe, "
                        "numero_registro, lote, producto_id, fertilizante_id "
                        "FROM lineas_de_factura WHERE factura_id = :id ORDER BY id"
                    ),
                    {"id": factura_id},
                ).mappings().all()
                huella = servicios.la_huella_de_una_factura_guardada(la_factura, lineas)
                conexion.execute(
                    text("UPDATE facturas SET huella_de_la_peticion = :huella WHERE id = :id"),
                    {"huella": huella, "id": factura_id},
                )
                rellenadas += 1

    # **Y la clave del papel**, que es la que hace que la base impida dos veces el mismo documento. Se
    # decide **de una vez y por orden**: la primera factura viva de cada papel se queda con la clave y las
    # siguientes del mismo papel se quedan sin ella. Así se llega siempre al mismo estado —la segunda
    # pasada no cambia nada, que es lo que se le pide a algo que corre en cada arranque—, el duplicado
    # **se queda a la vista** (no se borra ninguna fila) y a partir de ahí ya no entra otro igual.
    papeles = 0
    if "clave_del_papel" in columnas:
        from . import servicios  # importación tardía: evita dependencia circular

        with motor.connect() as conexion:
            vivas = conexion.execute(
                text(
                    "SELECT id, explotacion_id, proveedor, proveedor_nif, numero_factura, fecha, total, "
                    "clave_del_papel FROM facturas WHERE " + no_anulada + " ORDER BY id"
                )
            ).mappings().all()
        # **El papel se reconoce dentro de una finca** —la misma factura en dos explotaciones son dos
        # documentos de dos agricultores—, y por eso la finca entra en lo que ya se ha visto.
        ya_vistos: set[str] = set()
        for fila in vivas:
            la_clave = servicios.clave_del_papel_de_una_factura(
                fila["proveedor"],
                fila["proveedor_nif"],
                fila["numero_factura"],
                fila["fecha"],
                fila["total"],
            )
            if la_clave is None:
                continue
            suyo = f"{fila['explotacion_id']}|{la_clave}"
            if suyo in ya_vistos:
                # Es el segundo del mismo papel: se queda sin clave del papel. Se cuenta **solo si de
                # verdad había que cambiarlo**, para que la segunda pasada no diga que ha hecho algo.
                if fila["clave_del_papel"] is not None:
                    with motor.begin() as conexion:
                        conexion.execute(
                            text("UPDATE facturas SET clave_del_papel = NULL WHERE id = :id"),
                            {"id": fila["id"]},
                        )
                    papeles += 1
                continue
            ya_vistos.add(suyo)
            if fila["clave_del_papel"] != la_clave:
                with motor.begin() as conexion:
                    conexion.execute(
                        text("UPDATE facturas SET clave_del_papel = :clave WHERE id = :id"),
                        {"clave": la_clave, "id": fila["id"]},
                    )

    return soltadas, rellenadas, papeles


def llevar_los_canales_de_los_contactos_a_su_tabla(destino_engine: Engine | None = None) -> int:
    """Pasa a la tabla de canales **lo que ya estaba apuntado** en la ficha (Entrega 2, 13/10/2026).

    **Por qué hace falta.** Hasta hoy la ficha tenía **un** teléfono, **un** correo y **una** dirección. A partir de
    ahora puede tener varios, con su etiqueta y su principal. Si lo que ya estaba apuntado se quedara solo en las
    columnas de siempre, la pantalla nueva saldría **vacía** para todas las fichas que ya existen —y el agricultor
    creería que se ha perdido lo que tenía—.

    **La regla, y es la que no pierde nada:** cada valor que haya en la ficha pasa a ser el canal **principal** de
    su clase, **tal cual está guardado** —sin arreglar el teléfono, sin poner prefijos, sin tocar el texto—. La
    dirección se lleva con su localidad, que es como se apunta en el campo. Un valor vacío **no** crea canal: no
    hay nada que llevar.

    **Los cuatro campos de `Contacto` se quedan como están**: los leen cinco sitios (la exportación, la búsqueda,
    la ficha, la tabla y la corrección) y lo que ya estaba apuntado **no se mueve de sitio**. Esto **copia**, no
    traslada.

    Se puede correr dos veces: **solo mira las fichas que no tienen ningún canal todavía**.
    """
    from sqlalchemy import inspect, text

    motor = destino_engine or engine
    inspector = inspect(motor)
    if not inspector.has_table("contactos") or not inspector.has_table("canales_de_un_contacto"):
        return 0

    with motor.begin() as conexion:
        # Las fichas con algo que llevar **y sin ningún canal todavía**. Los paréntesis del `OR` no son adorno: sin
        # ellos, el `AND` se comería las dos primeras condiciones y se llevarían canales de fichas ya hechas.
        las_que_faltan = conexion.execute(
            text(
                """
                SELECT id, explotacion_id, telefono, correo, direccion, localidad
                  FROM contactos
                 WHERE (
                       (telefono IS NOT NULL AND TRIM(telefono) <> '')
                    OR (correo IS NOT NULL AND TRIM(correo) <> '')
                    OR (direccion IS NOT NULL AND TRIM(direccion) <> '')
                       )
                   AND id NOT IN (SELECT contacto_id FROM canales_de_un_contacto)
                """
            )
        ).fetchall()

        llevados = 0
        for ficha in las_que_faltan:
            # Una fila por clase con valor. El teléfono y el correo van tal cual; la dirección, con su localidad.
            suyos = []
            if ficha.telefono and ficha.telefono.strip():
                suyos.append(("telefono", ficha.telefono, None, None, None))
            if ficha.correo and ficha.correo.strip():
                suyos.append(("correo", None, ficha.correo, None, None))
            if ficha.direccion and ficha.direccion.strip():
                suyos.append(("direccion", None, None, ficha.direccion, ficha.localidad))
            for clase, telefono, correo, direccion, localidad in suyos:
                conexion.execute(
                    text(
                        """
                        INSERT INTO canales_de_un_contacto
                            (explotacion_id, contacto_id, clase, etiqueta, telefono, correo, direccion,
                             localidad, principal)
                        VALUES (:explotacion_id, :contacto_id, :clase, NULL, :telefono, :correo, :direccion,
                                :localidad, 1)
                        """
                    ),
                    {
                        "explotacion_id": ficha.explotacion_id,
                        "contacto_id": ficha.id,
                        "clase": clase,
                        "telefono": telefono,
                        "correo": correo,
                        "direccion": direccion,
                        "localidad": localidad,
                    },
                )
                llevados += 1
    return llevados


def repartir_lo_cobrado_que_ya_estaba(destino_engine: Engine | None = None) -> int:
    """Pasa a la tabla de aplicaciones **lo que ya estaba imputado** en los cobros de antes (CRM-01).

    **Por qué hace falta.** Hasta el 11/10/2026 un cobro decía a qué factura iba con **una columna**
    (`factura_emitida_id`) y cuánto con otra (`importe_imputado`). A partir de ahora eso vive en
    `aplicaciones_de_cobro`, que es lo que permite repartir un ingreso entre **varias** deudas. Si un cobro
    que ya existía se quedara sin su aplicación, su dinero **desaparecería de la factura**: la factura
    volvería a estar pendiente y el cobro seguiría apuntado, que es la peor de las mentiras posibles en un
    cuaderno de cuentas.

    **La regla, y es la que conserva las cuentas idénticas:** se crea **una** aplicación por cada cobro vivo
    que tenga factura **e** `importe_imputado` con valor —que es exactamente lo que sumaba
    `lo_cobrado_de_una_factura`—, con el importe **tal cual está guardado**, sin recalcularlo. Un cobro sin
    factura (dinero sin conciliar) o con el imputado vacío **no** genera aplicación: hoy no aportaba nada a
    ninguna factura y después tampoco.

    Se puede correr dos veces: solo mira los cobros que **no** tienen ya su aplicación.
    """
    from sqlalchemy import inspect, text

    motor = destino_engine or engine
    inspector = inspect(motor)
    if not inspector.has_table("cobros") or not inspector.has_table("aplicaciones_de_cobro"):
        return 0

    with motor.begin() as conexion:
        los_que_faltan = conexion.execute(
            text(
                "SELECT c.id, c.explotacion_id, c.factura_emitida_id, c.importe_imputado "
                "FROM cobros c WHERE c.factura_emitida_id IS NOT NULL "
                "AND c.importe_imputado IS NOT NULL AND NOT EXISTS ("
                "  SELECT 1 FROM aplicaciones_de_cobro a WHERE a.cobro_id = c.id"
                ")"
            )
        ).fetchall()
        for fila in los_que_faltan:
            conexion.execute(
                text(
                    "INSERT INTO aplicaciones_de_cobro "
                    "(explotacion_id, cobro_id, factura_emitida_id, importe, anulado) "
                    "VALUES (:explotacion, :cobro, :factura, :importe, :no)"
                ),
                {
                    "explotacion": fila[1],
                    "cobro": fila[0],
                    "factura": fila[2],
                    "importe": fila[3],
                    # El booleano, en lo que entiende cada motor: en PostgreSQL `anulado` es un boolean de
                    # verdad y un 0 no vale (lo mismo que en el reenvío de facturas).
                    "no": False if motor.dialect.name.startswith("postgres") else 0,
                },
            )
    return len(los_que_faltan)


def crear_tablas(destino_engine: Engine | None = None) -> tuple[list[str], list[str]]:
    """Deja la base de datos lista para funcionar, y la pone al día si venía de antes."""
    from . import models  # importación tardía: evita dependencia circular

    motor = destino_engine or engine
    models.Base.metadata.create_all(bind=motor)
    anadidas, imposibles = asegurar_columnas(motor)
    # **Los datos antes que los índices** (09/10/2026): el índice único de la clave de reenvío de las
    # facturas no se puede crear si quedan claves repetidas de la regla vieja, así que primero se sueltan
    # las de las facturas que no eran la petición original y se rellenan las huellas del comando.
    sueltas, rellenadas, papeles = rellenar_la_huella_del_comando(motor)
    if sueltas:
        print(
            f"Claves de reenvío de factura repetidas: se han soltado {sueltas} "
            "(la clave se queda en la factura más antigua de cada petición; no se ha borrado nada)."
        )
    if rellenadas:
        print(
            f"Huellas del comando de factura rellenadas: {rellenadas} "
            "(con lo que cada factura dice hoy)."
        )
    if papeles:
        print(
            f"Facturas vivas del mismo papel: se ha soltado la clave del papel en {papeles} "
            "(la clave se queda en la más antigua; las dos siguen ahí, míralas y anula la que sobre)."
        )
    # **Y lo que ya estaba imputado, a la tabla de aplicaciones** (CRM-01, 11/10/2026): un cobro de antes
    # tiene que conservar el dinero que ya tenía asignado a su factura, o la factura volvería a estar
    # pendiente sin que nadie hubiera cobrado nada.
    repartidos = repartir_lo_cobrado_que_ya_estaba(motor)
    if repartidos:
        print(
            f"Cobros con dinero ya imputado: {repartidos} pasados a la tabla de aplicaciones "
            "(una aplicación por cobro, con el importe que ya tenían; no se recalcula nada)."
        )
    # Los índices, después de las columnas: un índice puede ser sobre una columna recién añadida.
    indices_creados, indices_cambiados = asegurar_indices(motor)
    if indices_creados or indices_cambiados:
        partes = []
        if indices_creados:
            partes.append(f"creados: {', '.join(indices_creados)}")
        if indices_cambiados:
            partes.append(f"puestos al día: {', '.join(indices_cambiados)}")
        print(f"Índices de la base de datos ({'; '.join(partes)}).")
    # Y después de añadir lo que falte, se quita la obligación de decir «sí o no» donde el tercer
    # estado («no se sabe») es la respuesta buena. Ver `COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS`.
    # **Y las claves ajenas que falten** (14/10/2026). Una tabla que nació sin la suya —porque `ALTER TABLE
    # ADD COLUMN` no puede añadir una clave ajena en SQLite— se reconstruye aquí, **con el esquema del modelo**
    # (con su clave primaria, que es lo que hace que las tablas que apuntan a ella sigan valiendo) y copiando
    # las filas tal cual. Hace **su propia copia** antes de tocar nada, y si la base no es un fichero **para y lo
    # dice** en vez de reconstruir sin vuelta atrás. Es **idempotente**: si la clave ya está —que es el caso
    # normal, en todos los arranques menos el primero— no hace absolutamente nada. Las tres cosas están
    # probadas en `tests/test_las_claves_ajenas_que_faltan.py`.
    claves = reconstruir_para_que_nazcan_las_claves_ajenas(motor)
    if claves:
        print(f"Tablas reconstruidas para que nazca su clave ajena: {', '.join(claves)}")
    reconstruidas = reconstruir_para_poder_decir_no_se(motor)
    if reconstruidas:
        print(
            "Columnas que ahora pueden decir «no se sabe» (se han reconstruido sus tablas, "
            f"sin tocar ningún dato): {', '.join(reconstruidas)}"
        )
    # **Y los canales de las fichas que ya existían** (Entrega 2, 13/10/2026): va **después** de los
    # índices, porque el índice parcial que garantiza un solo principal por clase tiene que existir ya
    # cuando se escriben los principales que se llevan.
    canales = llevar_los_canales_de_los_contactos_a_su_tabla(motor)
    if canales:
        print(
            f"Canales de las fichas que ya existían: {canales} llevados a la tabla de canales "
            "(el principal de cada clase, tal cual estaban apuntados; no se toca ni un texto)."
        )
    return anadidas, imposibles
