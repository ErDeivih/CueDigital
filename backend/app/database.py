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
)


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


def crear_tablas(destino_engine: Engine | None = None) -> tuple[list[str], list[str]]:
    """Deja la base de datos lista para funcionar, y la pone al día si venía de antes."""
    from . import models  # importación tardía: evita dependencia circular

    motor = destino_engine or engine
    models.Base.metadata.create_all(bind=motor)
    anadidas, imposibles = asegurar_columnas(motor)
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
    reconstruidas = reconstruir_para_poder_decir_no_se(motor)
    if reconstruidas:
        print(
            "Columnas que ahora pueden decir «no se sabe» (se han reconstruido sus tablas, "
            f"sin tocar ningún dato): {', '.join(reconstruidas)}"
        )
    return anadidas, imposibles
