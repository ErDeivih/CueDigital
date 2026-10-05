"""Pone en «no comprobado» los apuntes a los que se les puso un «no» que nadie había comprobado.

Es la **migración de datos** del apartado A2 de `docs/T02_VALORES_POR_DEFECTO.md`. Va aparte del
programa a propósito: el arranque ya deja la columna admitiendo el tercer estado (ver
`app/database.py`, `reconstruir_para_poder_decir_no_se`), pero **reescribir lo que ya está
guardado es una decisión**, y una decisión se toma con los números delante, no porque el programa
se reinicie.

Uso:

    python scripts/migrar_zona_de_nitratos.py --base <fichero>              # informe, no toca nada
    python scripts/migrar_zona_de_nitratos.py --base <fichero> --migrar     # hace el cambio

Qué cambia exactamente, y qué no:

* **Sí cambia** el `en_zona_vulnerable` de un apunte cuando el valor guardado era `0` («no está en
  zona») y la tierra dice «no lo sé», o cuando el apunte es de un grupo de tierras sin tierra
  concreta. Ese `0` no lo comprobó nadie: lo puso el programa.
* **No cambia** ningún apunte que esté dentro de una firma. Una firma es la prueba de lo que había,
  y reescribir lo firmado haría que su huella dejara de cuadrar: el programa diría que el cuaderno
  se ha tocado. Eso incluye las firmas del apunte suelto y las del cuaderno entero de la campaña.
* **No cambia** ningún `True` ni ningún `False` de una tierra que sí tiene la zona comprobada.

Antes de tocar nada hace una copia del fichero al lado de la base y comprueba que
SQLite puede abrirla. Si falla esa comprobación, no se migra nada. Para volver atrás
se copia esa copia encima del original; se imprimen los números antes y después.

**Lo que este guion NO toca, y por qué.** La autorización de los productos del catálogo (el otro
defecto alto del mismo documento, A1) **no se migra**, y no por olvido: en esas fichas no hay forma
de distinguir un «sí está autorizado» que escribió el agricultor de un «sí» que puso el programa por
defecto —el alta de un producto no deja rastro en la auditoría—, así que cambiarlo a «no comprobado»
borraría información que sí era un dato. Lo que hace es **listarlas** (apartado «A1 · el catálogo de
productos») para que esa revisión se pueda hacer a mano, ficha a ficha, desde la pantalla; mientras
tanto el programa dice que no lo sabe en vez de dar por bueno lo que no ha comprobado. Lo que sí hace
falta en la base —que la columna admita el tercer estado— lo hace el programa al arrancar
(`app/database.py`).
"""

from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app import database  # noqa: E402  (va después de ajustar la ruta, a propósito)

# Las dos tablas que tienen el campo, con el nombre que se les da en el cuaderno.
TABLAS = (
    ("tratamientos", "productos aplicados"),
    ("fertilizaciones", "abonos"),
)

# **La columna de este guion, y solo esta.** Es la zona de nitratos (A2). `database.py` tiene más columnas
# que dejaron de ser obligatorias —la autorización de un producto (A1), la composición de un abono (A6), la
# superficie de una tierra (A7)—, pero **cada una tiene su propia decisión de datos**, y meterlas aquí sería
# reescribir cuatro cosas distintas con la misma regla. Se escribe a mano para que el día que crezca la lista
# de `database.py` este guion **no** empiece a informar de columnas que no son suyas (pasó el 03/10/2026: el
# informe salió diciendo «fertilizaciones (uf_k_total)»).
COLUMNA = dict.fromkeys(("tratamientos", "fertilizaciones"), "en_zona_vulnerable")


def _existe(conexion: sqlite3.Connection, tabla: str) -> bool:
    return bool(
        conexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
        ).fetchone()
    )


def _admite_no_se(conexion: sqlite3.Connection, tabla: str, columna: str) -> bool:
    """`True` si la columna puede guardar el tercer estado (`NULL`), es decir, si ya está migrada."""
    for fila in conexion.execute(f'PRAGMA table_info("{tabla}")'):
        if fila[1] == columna:
            return not fila[3]
    return False


def _dicen_no_sin_saberlo(tabla: str, *, hay_parcelas: bool) -> str:
    """La condición que describe el defecto: el apunte dice «no» y nadie pudo comprobarlo.

    Dos maneras de no poder comprobarlo: la tierra dice «no lo sé», o el apunte es de un grupo de
    tierras y no de una tierra concreta (un grupo puede tener tierras dentro y fuera de la zona).
    """
    columna = COLUMNA[tabla]
    if not hay_parcelas:
        return f"{columna} = 0"
    return (
        f"{columna} = 0 AND ({tabla}.parcela_id IS NULL OR "
        f"(SELECT zona_vulnerable_nitratos FROM parcelas WHERE parcelas.id = {tabla}.parcela_id)"
        " IS NULL)"
    )


def _esta_firmado(tabla: str, *, hay_firmas: bool) -> str:
    """La condición que dice si una fila está dentro de una firma.

    Dos formas de estarlo, y las dos cuentan: la firma del apunte suelto y la del cuaderno entero
    de la campaña a la que pertenece el apunte. Ver `models.Firma`.
    """
    if not hay_firmas:
        return "0"
    entidad = "tratamiento" if tabla == "tratamientos" else "fertilizacion"
    return (
        f"EXISTS (SELECT 1 FROM firmas f WHERE "
        f"(f.entidad = '{entidad}' AND f.entidad_id = {tabla}.id) OR "
        f"(f.entidad = 'cuaderno' AND f.campana_id = {tabla}.campana_id "
        f" AND f.explotacion_id = {tabla}.explotacion_id))"
    )


def _condiciones(conexion: sqlite3.Connection, tabla: str) -> tuple[str, str, str]:
    """Las tres condiciones que usa el informe: sin saberlo, firmado, y las dos juntas."""
    sin_saberlo = _dicen_no_sin_saberlo(tabla, hay_parcelas=_existe(conexion, "parcelas"))
    firmado = _esta_firmado(tabla, hay_firmas=_existe(conexion, "firmas"))
    return sin_saberlo, firmado, f"({sin_saberlo}) AND {firmado}"


def _contar(conexion: sqlite3.Connection, tabla: str, condicion: str) -> int:
    return conexion.execute(f'SELECT COUNT(*) FROM "{tabla}" WHERE {condicion}').fetchone()[0]


def _informe(conexion: sqlite3.Connection, tabla: str) -> dict:
    """Cuenta, sin tocar nada, cuántos apuntes están en cada caso."""
    columna = COLUMNA[tabla]
    sin_saberlo, _firmado, firmadas = _condiciones(conexion, tabla)
    return {
        "tabla": tabla,
        "columna": columna,
        "ya_migrada": _admite_no_se(conexion, tabla, columna),
        "filas": _contar(conexion, tabla, "1"),
        "dicen_no": _contar(conexion, tabla, f"{columna} = 0"),
        "sin_saberlo": _contar(conexion, tabla, sin_saberlo),
        "y_firmadas": _contar(conexion, tabla, firmadas),
    }


def _ensenar(informe: dict) -> None:
    print(f"\n  {informe['tabla']}  ({informe['columna']})")
    print(f"    apuntes en total: {informe['filas']}")
    print(f"    dicen «no está en zona»: {informe['dicen_no']}")
    print(f"    ...y lo dicen sin que nadie lo haya comprobado: {informe['sin_saberlo']}")
    print(f"    ...de esos, están dentro de una firma (no se tocan): {informe['y_firmadas']}")
    if not informe["ya_migrada"]:
        print("    la columna aún no admite «no se sabe»: el programa lo arregla al arrancar")


def _ids_que_cambian(conexion: sqlite3.Connection, tabla: str) -> list[int]:
    """Los apuntes que hay que pasar a «no comprobado»: dicen «no» sin saberlo y **sin firma encima**.

    **El paréntesis del `NOT` no es un detalle** (encontrado por la revisión independiente del
    02/10/2026). `firmadas` es ya una condición compuesta —`(sin saberlo) AND firmado`—, así que escribirlo
    como `AND NOT {firmadas}` dejaba la consulta en `A AND NOT (A) AND …`: **no podía devolver nunca una
    fila**. El informe decía «hay 1 apunte que cambiar» y la lista salía vacía, así que el guion terminaba
    en error después de haber migrado el esquema y **sin cambiar ni un dato**. Se escribe el paréntesis a
    propósito, y hay una prueba que lo comprueba con un apunte que de verdad cambia.
    """
    sin_saberlo, _firmado, firmadas = _condiciones(conexion, tabla)
    return [
        fila[0]
        for fila in conexion.execute(
            f'SELECT id FROM "{tabla}" WHERE {sin_saberlo} AND NOT ({firmadas}) ORDER BY id'
        )
    ]


def _tablas_utiles(conexion: sqlite3.Connection) -> list[tuple[str, dict]]:
    utiles: list[tuple[str, dict]] = []
    for tabla, _nombre in TABLAS:
        if not _existe(conexion, tabla):
            print(f"\n  {tabla}: no existe en esta base, se ignora")
            continue
        if COLUMNA[tabla] not in {f[1] for f in conexion.execute(f'PRAGMA table_info("{tabla}")')}:
            print(f"\n  {tabla}: no tiene la columna, se ignora")
            continue
        informe = _informe(conexion, tabla)
        _ensenar(informe)
        utiles.append((tabla, informe))
    return utiles


# El otro defecto alto del mismo documento, A1: la autorización de un producto del catálogo.
#
# **Este guion NO lo cambia, y es a propósito.** En esas fichas no hay forma de distinguir un «sí está
# autorizado» que escribió el agricultor de un «sí» que puso el programa por defecto: el alta de un
# producto no deja rastro en la auditoría. Cambiarlo a «no comprobado» borraría un dato que sí era un
# dato, así que lo que hace este guion es **poner la lista delante** para que lo revise una persona,
# ficha a ficha, desde la pantalla del producto (allí las dos preguntas ya tienen sus tres respuestas).
def _revision_de_los_productos(conexion: sqlite3.Connection) -> None:
    if not _existe(conexion, "productos_fitosanitarios"):
        return
    columnas = {f[1] for f in conexion.execute('PRAGMA table_info("productos_fitosanitarios")')}
    if not {"autorizado", "permitido_ecologico"} <= columnas:
        return

    filas = list(
        conexion.execute(
            "SELECT id, nombre_comercial, autorizado, permitido_ecologico, numero_registro "
            "FROM productos_fitosanitarios ORDER BY id"
        )
    )
    print("\n  A1 · el catálogo de productos, para revisar a mano (esto NO se toca aquí)")
    if not filas:
        print("    no hay ningún producto dado de alta")
        return

    def como_texto(valor) -> str:
        if valor is None:
            return "NO COMPROBADO"
        return "sí" if valor else "no"

    revisar = [
        fila for fila in filas if fila[2] is None or fila[3] is None
    ]
    for identificador, nombre, autorizado, ecologico, registro in filas:
        print(
            f"    · {identificador}: {nombre or '(sin nombre)'} "
            f"({registro or 'sin nº de registro'}) → autorizado: {como_texto(autorizado)}, "
            f"en ecológico: {como_texto(ecologico)}"
        )
    print(
        f"    {len(filas)} {'producto' if len(filas) == 1 else 'productos'} en total; "
        f"{len(revisar)} ya dicen «no comprobado» y no hay que tocar nada en ellos."
    )
    print(
        "    Los que dicen «sí» pueden ser un «sí» de verdad o el valor que ponía el programa por\n"
        "    defecto antes del 02/10/2026, y eso NO se puede saber desde aquí. Si quieres\n"
        "    comprobarlo, abre cada uno en «Mis cosas → corregir» y contesta las dos preguntas:\n"
        "    mientras no lo hagas, el programa no afirmará nada de los productos nuevos."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pone en «no comprobado» los apuntes a los que se les puso un «no» inventado."
    )
    parser.add_argument("--base", required=True, help="el fichero de la base de datos")
    parser.add_argument(
        "--migrar",
        action="store_true",
        help="hace el cambio (sin esto solo enseña lo que haría, sin tocar nada)",
    )
    argumentos = parser.parse_args()

    ruta = pathlib.Path(argumentos.base).resolve()
    if not ruta.exists():
        print(f"No encuentro la base de datos en {ruta}.")
        return 1

    print(f"Base de datos: {ruta}")
    print(f"Tamaño: {ruta.stat().st_size:,} bytes")

    conexion = sqlite3.connect(ruta)
    conexion.execute("PRAGMA foreign_keys=OFF")
    try:
        if not _existe(conexion, "firmas"):
            print("\nOjo: esta base no tiene la tabla de firmas, así que no se puede saber qué")
            print("apuntes están firmados. No se cambiará ningún dato.")

        utiles = _tablas_utiles(conexion)
        _revision_de_los_productos(conexion)

        if not argumentos.migrar:
            print("\nEsto es solo el informe: no se ha tocado nada.")
            print("Para hacer el cambio de verdad, añade --migrar.")
            return 0

        if not _existe(conexion, "firmas"):
            print("\nNo se migra: sin la tabla de firmas no se sabe qué se puede tocar.")
            return 1

        # 1. La copia, antes de nada. Si la copia no se puede comprobar, `database` levanta
        # `RuntimeError` y **no se reconstruye ninguna tabla**: aquí se enseña el motivo en
        # cristiano en vez de dejar salir una traza de Python. Se recogen también los fallos de SQLite
        # y del disco (un fichero que no es una base, una carpeta sin permiso): un guion que se cae con
        # una traza no le dice a nadie qué hacer.
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        try:
            copia = database._copia_de_seguridad_del_fichero(motor)
        except (RuntimeError, sqlite3.Error, OSError) as fallo:
            print(f"\nNo se migra: {fallo}")
            print("La base de datos se queda exactamente como estaba.")
            return 1
        print(f"\nCopia de antes de empezar: {copia}")

        # 2. El esquema: la columna tiene que admitir «no se sabe» para poder guardarlo. **Se le pasa la
        # copia que ya está hecha**: si no, la reconstrucción haría otra (y ya van dos por ejecución, cuatro
        # ficheros con los datos del agricultor que nadie borra después).
        try:
            hechas = database.reconstruir_para_poder_decir_no_se(motor, copia_ya_hecha=copia)
        except (RuntimeError, sqlite3.Error, OSError) as fallo:
            print(f"\nNo se ha podido poner al día el esquema: {fallo}")
            print(f"La base se queda como estaba. La copia de antes de empezar: {copia}")
            return 1
        if hechas:
            print(f"Columnas que ahora admiten «no se sabe»: {', '.join(hechas)}")
        else:
            print("El esquema ya estaba al día: no ha hecho falta reconstruir ninguna tabla.")

        # 3. Los datos: solo lo que dice «no» sin que nadie lo comprobara y sin firma encima.
        cambiadas = 0
        for tabla, _informe_de_antes in utiles:
            ids = _ids_que_cambian(conexion, tabla)
            if not ids:
                print(f"\n  {tabla}: no hay ningún apunte que cambiar")
                continue
            conexion.executemany(
                f'UPDATE "{tabla}" SET en_zona_vulnerable = NULL WHERE id = ?',
                [(identificador,) for identificador in ids],
            )
            conexion.commit()
            cambiadas += len(ids)
            print(f"\n  {tabla}: {len(ids)} apuntes pasan a «no se ha podido comprobar»")
            print(f"    identificadores: {ids[:20]}{' ...' if len(ids) > 20 else ''}")

        # 4. Los números de después, y la comprobación de que no se ha tocado nada firmado.
        print("\nDespués del cambio:")
        for tabla, antes in utiles:
            despues = _informe(conexion, tabla)
            _ensenar(despues)
            if despues["y_firmadas"] != antes["y_firmadas"]:
                print("    ¡Se ha tocado la zona de un apunte firmado! Vuelve a poner la copia.")
                return 1
            if despues["sin_saberlo"] - despues["y_firmadas"] != 0:
                print("    Quedan apuntes que dicen «no» sin saberlo y sin firma: revisa el informe.")
                return 1
        print(f"\nApuntes que han pasado a «no se ha podido comprobar»: {cambiadas}")
        if cambiadas == 0 and any(antes["sin_saberlo"] for _t, antes in utiles):
            # Si el informe decía que había apuntes que cambiar y no se ha cambiado ninguno, algo no cuadra:
            # mejor decirlo que terminar como si todo hubiera ido bien.
            print("Ojo: el informe decía que había apuntes que cambiar y no se ha cambiado ninguno.")
            print("Revisa el informe de arriba antes de dar la migración por buena.")
            return 1
        print(f"Para volver atrás: `python scripts/deshacer_la_migracion.py --base {ruta}`")
        print(f"(o, a mano: copia {copia} encima de {ruta} **y borra {ruta}-wal y {ruta}-shm**,")
        print(" porque si queda el WAL, SQLite vuelve a aplicar encima lo escrito después)")
        return 0
    finally:
        conexion.close()


if __name__ == "__main__":
    raise SystemExit(main())
