"""Deshace una migración: vuelve a poner una copia **como base**, con lo que hay que borrar además.

**Por qué no basta con «copiar la copia encima».** Lo encontró la revisión independiente del 02/10/2026, y
es de los fallos que se ven tarde: si al lado de la base hay un fichero `-wal` (SQLite en modo WAL, con
cambios confirmados que todavía no han bajado al fichero principal), copiar la copia **encima del principal
no deshace nada**: SQLite reaplica el `-wal` en cuanto abre la base y todo lo escrito después de la copia
vuelve a estar ahí. Medido: la copia tenía 2 tratamientos, la base 3, se copiaba la copia encima y la base
seguía con 3. La vuelta atrás de verdad son **tres cosas**: el fichero, y quitar el `-wal` y el `-shm`.

Uso:

    python scripts/deshacer_la_migracion.py --base <fichero>                 # la copia más nueva de al lado
    python scripts/deshacer_la_migracion.py --base <fichero> --copia <otra>  # una copia concreta
    python scripts/deshacer_la_migracion.py --base <fichero> --mirar         # solo enseña qué haría

Lo que hace, en este orden, y sin saltarse ningún paso:

1. Comprueba que la copia se puede abrir y está entera (`PRAGMA quick_check`). Sin eso, no se toca nada.
2. Guarda **el estado de ahora** en `<base>.antes-de-deshacer-<marca>`: deshacer un deshacer también tiene
   que ser posible (si alguien se equivoca de copia, no se queda sin la de ahora).
3. Pone la copia encima del fichero principal y **borra el `-wal` y el `-shm`** que hubiera al lado.
4. Comprueba el resultado: que abre, que está entera y que tiene **las mismas filas** que la copia.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import shutil
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import database  # noqa: E402  (va después de ajustar la ruta, a propósito)

# El nombre que deja la migración al lado de la base, y el que deja este guion al deshacer.
MARCA_DE_LA_MIGRACION = ".antes-de-migrar-"
MARCA_DE_ESTE_GUION = ".antes-de-deshacer-"


def _la_copia_mas_nueva(base: pathlib.Path) -> pathlib.Path | None:
    """La copia más reciente que dejó la migración, prefiriendo la que es idéntica byte a byte.

    La copia byte a byte es la que deja el fichero **exactamente** como estaba; la otra (la coherente) tiene
    los mismos datos pero reorganizados. Si están las dos, se usa la primera, y si solo está la coherente,
    esa sirve igual.
    """
    copias = sorted(base.parent.glob(f"{base.name}{MARCA_DE_LA_MIGRACION}*"))
    identicas = [copia for copia in copias if copia.name.endswith("-byte-a-byte")]
    if identicas:
        return identicas[-1]
    return copias[-1] if copias else None


def _esta_entera(ruta: pathlib.Path) -> bool:
    """Si el fichero se puede abrir **y** SQLite lo da por bueno.

    Se recogen todos los errores de SQLite, no solo el de abrir: un fichero que no es una base de datos se
    abre sin problema y revienta al ejecutar el `PRAGMA`, que es lo que pasaba con un fichero cualquiera con
    el nombre de una copia (lo encontró la prueba de «una copia que no sirve»).
    """
    try:
        conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        return conexion.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    except sqlite3.Error:
        return False
    finally:
        conexion.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vuelve a poner una copia como base y limpia el WAL que dejaría la vuelta atrás a medias."
    )
    parser.add_argument("--base", required=True, help="el fichero de la base de datos")
    parser.add_argument("--copia", default="", help="la copia que hay que volver a poner")
    parser.add_argument(
        "--mirar", action="store_true", help="solo enseña qué haría, sin tocar nada"
    )
    argumentos = parser.parse_args()

    base = pathlib.Path(argumentos.base).resolve()
    if not base.exists():
        print(f"No encuentro la base de datos en {base}.")
        return 1
    copia = pathlib.Path(argumentos.copia).resolve() if argumentos.copia else _la_copia_mas_nueva(base)
    if copia is None or not copia.exists():
        print(f"No encuentro ninguna copia de antes de migrar al lado de {base}.")
        print("Pásala con --copia. Las copias se llaman «<base>.antes-de-migrar-<fecha>».")
        return 1

    print(f"Base de datos: {base}")
    print(f"Copia que se va a poner: {copia}")
    if not _esta_entera(copia):
        print("\nEsa copia no se puede abrir o no está entera: no se toca nada.")
        return 1

    al_lado = [
        pathlib.Path(f"{base}{sufijo}")
        for sufijo in ("-wal", "-shm")
        if pathlib.Path(f"{base}{sufijo}").exists()
    ]
    print(f"Ficheros que hay que borrar además del principal: {[p.name for p in al_lado] or 'ninguno'}")
    if argumentos.mirar:
        print("\nEsto es solo el aviso: no se ha tocado nada. Quita --mirar para hacerlo.")
        return 0

    # Pasar de WAL a DELETE exige que SQLite pueda cerrar el WAL: si otro proceso lo
    # usa, falla ANTES de copiar o borrar nada, también en Linux (donde unlink sí deja
    # borrar un WAL abierto). Recupera además el WAL de un proceso caído antes del backup.
    try:
        conexion = sqlite3.connect(f"file:{base.as_posix()}?mode=rw", uri=True, timeout=0)
        try:
            conexion.execute("PRAGMA journal_mode=DELETE").fetchone()
        finally:
            conexion.close()
    except sqlite3.Error:
        print(
            "No se ha podido terminar: otro programa está usando la base o no se puede preparar. "
            "La vuelta atrás no está hecha. Cierra la aplicación y cualquier visor de SQLite "
            "y vuelve a ejecutar este guion. No se ha sustituido la base."
        )
        return 1

    # El estado de ahora, guardado antes de pisarlo: deshacer un deshacer tiene que ser posible.
    marca = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    guardada = base.with_name(f"{base.name}{MARCA_DE_ESTE_GUION}{marca}")
    shutil.copy2(base, guardada)
    print(f"\nEl estado de ahora queda guardado en: {guardada}")

    shutil.copy2(copia, base)
    pendientes = []
    for fichero in al_lado:
        try:
            fichero.unlink(missing_ok=True)
            print(f"Borrado: {fichero.name} (si se queda, SQLite reaplica encima lo de después)")
        except OSError:
            # En Windows, un fichero de WAL **abierto por otro proceso** no se puede borrar. Y sin borrarlo
            # la vuelta atrás no está hecha: el WAL reaplicaría lo de después. Así que no se dice «hecho»:
            # se para, se explica y se deja dicho cómo terminar.
            pendientes.append(fichero.name)
    if pendientes:
        print(
            f"\nNo se ha podido terminar: {', '.join(pendientes)} está en uso, así que hay **otro programa**"
            " abierto usando esta base (otra ventana del cuaderno, un visor de SQLite).\n"
            "La vuelta atrás **no está hecha**: mientras quede el WAL, SQLite reaplicará encima lo escrito"
            " después de la copia. Cierra ese programa y vuelve a ejecutar este guion."
        )
        print(f"Para dejarlo como estaba antes de este intento: copia {guardada} encima de {base}")
        return 1

    # Y se comprueba el resultado, que es lo que hace que esto no sea «copiar y cruzar los dedos».
    if not _esta_entera(base):
        print("\nLa base restaurada NO está entera. Vuelve a poner el estado de ahora:")
        print(f"  copia {guardada} encima de {base}")
        return 1
    motor = database.crear_engine(f"sqlite:///{base.as_posix()}")
    if not database._copia_tiene_lo_mismo(copia, base):
        print("\nLa base restaurada tiene menos filas que la copia. Vuelve a poner el estado de ahora:")
        print(f"  copia {guardada} encima de {base}")
        return 1

    print("\nHecho: la base es la de la copia, y sin ficheros de WAL al lado que la deshagan.")
    print(f"Si te has equivocado de copia: copia {guardada} encima de {base} y borra {base}-wal y {base}-shm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
