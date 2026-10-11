"""Propone fichas de contacto a partir de los nombres que ya están escritos, y las apunta si se lo piden.

Es la **migración de los textos** del ticket T11 (`docs/T11_CONTACTOS.md`). Va aparte del programa por
el mismo motivo que la del T02 (`scripts/migrar_zona_de_nitratos.py`): el arranque ya deja las tablas
nuevas puestas, pero **decidir de quién es un nombre que el agricultor escribió a mano es una decisión
de datos**, y una decisión se toma con los números delante, no porque el programa se reinicie.

Uso:

    python scripts/migrar_contactos.py --base <fichero>              # informe, no toca nada
    python scripts/migrar_contactos.py --base <fichero> --migrar     # apunta las fichas seguras
    python scripts/migrar_contactos.py --base <fichero> --deshacer   # vuelve atrás

## Lo que hace, y lo que NO hace

* **Propone** una ficha por cada nombre escrito, agrupando los que **están escritos igual** y los que
  **comparten NIF** (que es una prueba). Eso es todo: la agrupación la hace `app/contactos.py`, que es
  la misma función que usa la pantalla, así que el guion y la pantalla **no pueden decir cosas distintas**.
* **No fusiona nada que no se pueda asegurar.** Los nombres que se parecen (una tilde de menos, un
  «S.L.» de más, una letra cambiada) y los que tienen el mismo nombre con dos NIF **se listan y no se
  tocan**. El guion ni siquiera se los ofrece.
* **No borra ni reescribe ni un texto.** En todo el guion no hay ni un `UPDATE`: lo único que se escribe
  son fichas nuevas y enlaces nuevos, en las tres tablas del T11. El informe lo cuenta al final
  (`textos escritos tocados: 0`), y hay una prueba que lo comprueba por el otro lado comparando el texto
  de una factura antes y después.

## Para volver atrás

`--deshacer` quita lo que apuntó la migración: **borra las fichas que creó y sus enlaces, y deja las
que el agricultor haya corregido o enlazado él**, que ya son suyas (lo dice con su nombre). Y antes de
tocar nada, el guion hace **una copia del fichero de la base** al lado y comprueba que SQLite puede
abrirla; si esa comprobación falla, no se migra nada. Para volver atrás del todo, esa copia se pone
encima del original (con el WAL borrado, que si no SQLite vuelve a aplicar lo escrito después).
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app import contactos as logica  # noqa: E402
from app import database, models, textos  # noqa: E402
from app.routers import contactos_api as api  # noqa: E402
from app.schemas import ConfirmacionDeLaMigracion  # noqa: E402

# **La lista de tablas donde está escrito un nombre no se escribe aquí**: vive en `app/contactos.py`
# (`ENLACES`) y es la misma que usa la pantalla. Si se copiara, el día que se añada una puerta nueva el
# guion se quedaría mirando las de antes y el agricultor no entendería por qué faltan facturas.


class SinCuenta:
    """Lo que se le pasa a las puertas como «quien hace esto», cuando lo hace un guion.

    Existe porque la auditoría guarda **quién** borró algo y aquí no hay nadie: el `usuario_id` se queda
    vacío, que es la verdad. Poner el de una cuenta cualquiera sería escribir en la auditoría algo que no
    pasó.
    """

    id: int | None = None


def _las_fincas(sesion) -> list[models.Explotacion]:
    return list(sesion.scalars(select(models.Explotacion).order_by(models.Explotacion.id)))


# Las tres tablas del T11. **Mirar si están no es un detalle**: en el informe (sin `--migrar`) el guion
# **no puede crear nada**, y sin ellas no se pueden leer los enlaces. Se descubrió ensayando sobre una
# copia de la base de verdad: el informe decía «no se ha tocado nada» y por debajo había puesto el
# esquema al día (`crear_tablas`), que reconstruye tablas. Un guion que dice una cosa y hace otra es
# justo lo que este proyecto no se puede permitir.
TABLAS_DEL_T11 = ("contactos", "papeles_de_un_contacto", "enlaces_de_contacto")


def _estan_las_tablas(motor) -> bool:
    from sqlalchemy import inspect as inspeccionar

    nombres = set(inspeccionar(motor).get_table_names())
    return all(tabla in nombres for tabla in TABLAS_DEL_T11)


def _el_informe(sesion, explotacion: models.Explotacion, *, con_enlaces: bool = True) -> dict:
    """Qué hay escrito en esa finca y qué se propone, **sin tocar nada**.

    `con_enlaces` va en falso cuando la base todavía no tiene las tablas del T11: entonces no hay ningún
    enlace que leer, y todo lo escrito sale como «sin dueño», que es la verdad de esa base.
    """
    escritos = api._los_escritos(sesion, explotacion.id, con_enlaces=con_enlaces)
    libres = [uno for uno in escritos if not uno["enlace_id"]]
    propuestas = logica.proponer([api._como_escrito(uno) for uno in libres])
    return {
        "explotacion": explotacion,
        "escritos": escritos,
        "libres": libres,
        "propuestas": propuestas,
        "resumen": logica.resumen_de_la_propuesta(propuestas),
    }


def _ensenar(informe: dict) -> None:
    finca = informe["explotacion"]
    print(f"\n  Finca {finca.id}: {finca.nombre}")
    print(f"    nombres escritos a mano: {len(informe['escritos'])}")
    print(f"    ...de esos, ya enlazados con una ficha: {len(informe['escritos']) - len(informe['libres'])}")
    print(f"    ...sin dueño todavía: {len(informe['libres'])}")
    if not informe["libres"]:
        print("    no hay nada que proponer")
        return

    resumen = informe["resumen"]
    print(
        f"    se proponen {_cuantos(resumen['fichas'], 'ficha')}, "
        f"con {_cuantos(resumen['nombres'], 'nombre')} escrito"
        f"{'s' if resumen['nombres'] != 1 else ''}"
    )

    seguras = [p for p in informe["propuestas"] if p.segura]
    for propuesta in seguras:
        papeles = ", ".join(textos.CONTACTOS["papeles"].get(p, p) for p in propuesta.papeles)
        print(
            f"\n    · «{propuesta.nombre}»  ({_cuantos(len(propuesta.escritos), 'nombre')}, "
            f"{papeles or 'sin papel'})"
        )
        print(f"        por qué: {_el_motivo(propuesta)}")
        for escrito in propuesta.escritos:
            donde = _donde(escrito)
            print(f"        - {donde}: «{escrito.texto}»")

    dudosas = [p for p in informe["propuestas"] if not p.segura]
    if dudosas:
        print("\n    ESTOS NO SE TOCAN, y hay que mirarlos a mano:")
        for propuesta in dudosas:
            if propuesta.motivo == "se_parecen":
                print("      · se parecen, y no se pueden juntar sin asegurarlo:")
                if propuesta.pareja:
                    print(f"          «{propuesta.pareja[0]}» y «{propuesta.pareja[1]}»")
                # Y las demás formas de escribirlo que están en juego (una con el «S.L.» de más, otra
                # toda en mayúsculas): el agricultor las necesita para decidir, pero no son la pareja
                # que ha hecho saltar el aviso.
                for nombre in propuesta.nombres:
                    if nombre not in propuesta.pareja:
                        print(f"          (también está escrito así: «{nombre}»)")
            elif propuesta.motivo == "mismo_nif_nombres_distintos":
                # **El caso que la revisión independiente cazó, y el guion lo dice con estas palabras
                # porque es justo el que antes apuntaba solo.** Un NIF tecleado mal fundía a dos
                # personas distintas: ahora ni se propone como segura ni se apunta con `--migrar`.
                print(
                    "      · el NIF es el mismo, pero los nombres no se parecen en nada "
                    f"({', '.join(propuesta.nifs)}): uno de los dos papeles está mal escrito"
                )
            else:
                print(
                    f"      · «{propuesta.nombre}»: el mismo nombre con dos NIF distintos "
                    f"({', '.join(propuesta.nifs)})"
                )
            for escrito in propuesta.escritos:
                print(f"          - {_donde(escrito)}: «{escrito.texto}»")
    print(
        "\n    Nada de esto toca los papeles: los nombres siguen escritos donde estaban. Lo único que"
        "\n    se apunta son las fichas y los enlaces."
    )


def _cuantos(cantidad: int, que: str) -> str:
    """«1 nombre» y «3 nombres»: hasta en la salida de un guion se nota un plural mal puesto."""
    return f"{cantidad} {que}" if cantidad == 1 else f"{cantidad} {que}s"


def _el_motivo(propuesta: logica.Propuesta) -> str:
    """Por qué esa ficha se puede apuntar, dicho sin claves de máquina."""
    if propuesta.motivo == "mismo_nif":
        nif = propuesta.nifs[0] if propuesta.nifs else ""
        return f"los papeles comparten el mismo NIF ({nif}), y eso es una prueba"
    return "el nombre está escrito igual en todas partes"


def _donde(escrito: logica.Escrito) -> str:
    """De dónde es ese nombre, en palabras del agricultor y con el dato de la tabla."""
    campo = logica.el_campo(escrito.tabla, escrito.campo)
    etiqueta = textos.CONTACTOS.get(f"tabla_{campo.clave}", campo.clave) if campo else escrito.tabla
    referencia = " · ".join(str(trozo) for trozo in escrito.referencia if trozo)
    return f"{etiqueta} ({referencia})" if referencia else str(etiqueta)


def _migrar(sesion, informe: dict) -> dict:
    """Apunta las fichas seguras de esa finca **por la misma puerta que la pantalla**.

    Se llama a `contactos_api.aplicar_la_migracion` en vez de escribir las fichas aquí, y eso es lo
    importante de este guion: **la regla de qué se puede juntar vive en un solo sitio**. Si el guion
    tuviera su propia copia, un día la pantalla diría una cosa y el guion otra.
    """
    claves = [api._la_clave(propuesta) for propuesta in informe["propuestas"] if propuesta.segura]
    if not claves:
        print("\n    no hay ninguna ficha segura que apuntar: no se hace nada")
        return {"fichas": 0, "enlaces": 0}
    resultado = api.aplicar_la_migracion(
        ConfirmacionDeLaMigracion(claves=claves),
        db=sesion,
        explotacion=informe["explotacion"],
        # El parámetro se llamaba `_usuario` porque no se usaba; desde el 11/10/2026 la migración **sí** lo
        # usa: deja rastro con quién la hizo. El guion no corre con una cuenta, así que pasa esa misma.
        usuario=SinCuenta(),
    )
    print(
        f"\n    apuntadas {_cuantos(resultado['fichas'], 'ficha')} y "
        f"{_cuantos(resultado['enlaces'], 'enlace')} "
        f"(textos escritos tocados: {resultado['textos_tocados']})"
    )
    for nombre in resultado["nombres"]:
        print(f"      · {nombre}")
    return resultado


def _deshacer(sesion, explotacion: models.Explotacion) -> dict:
    """Quita lo que apuntó la migración, por la misma puerta que la pantalla."""
    resultado = api.deshacer_la_migracion(
        db=sesion, explotacion=explotacion, usuario=SinCuenta()
    )
    print(
        f"\n    quitadas {_cuantos(resultado['fichas'], 'ficha')} y "
        f"{_cuantos(resultado['enlaces'], 'enlace')} deshecho"
        f"{'s' if resultado['enlaces'] != 1 else ''} "
        f"(textos escritos tocados: {resultado['textos_tocados']})"
    )
    for linea in resultado["se_quedan"]:
        print(f"      · se queda: {linea}")
    return resultado


def _huella_del_texto(ruta: pathlib.Path) -> str:
    """La huella de **todos los nombres escritos a mano** de la base, leídos con SQL en crudo.

    Es la comprobación que da sentido a este guion: se mide antes y después, y si cambiara una letra
    de un papel, el guion se para y lo dice. Se lee con SQLite directo (y no con los modelos) para que
    sea una medida **independiente** de la lógica que se está probando: si se midiera con el mismo
    código que escribe, no mediría nada.
    """
    conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
    try:
        trozos: list[str] = []
        for enlace in logica.ENLACES:
            try:
                filas = conexion.execute(
                    f'SELECT id, "{enlace.campo}" FROM "{enlace.tabla}" ORDER BY id'
                )
            except sqlite3.Error:
                continue
            for identificador, valor in filas:
                trozos.append(f"{enlace.tabla}:{enlace.campo}:{identificador}:{valor!r}")
        return hashlib.sha256("\n".join(trozos).encode("utf-8")).hexdigest()
    finally:
        conexion.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Propone fichas de contacto a partir de los nombres escritos a mano, sin fusionar nada "
            "que no se pueda asegurar."
        )
    )
    parser.add_argument("--base", required=True, help="el fichero de la base de datos")
    parser.add_argument(
        "--migrar",
        action="store_true",
        help="apunta las fichas seguras (sin esto solo enseña lo que haría, sin tocar nada)",
    )
    parser.add_argument(
        "--deshacer",
        action="store_true",
        help="quita las fichas y los enlaces que apuntó la migración",
    )
    parser.add_argument(
        "--finca",
        type=int,
        default=None,
        help="hacerlo solo en esa finca (por defecto, en todas las que haya)",
    )
    argumentos = parser.parse_args()

    if argumentos.migrar and argumentos.deshacer:
        print("Elige una cosa: --migrar o --deshacer, no las dos.")
        return 1

    ruta = pathlib.Path(argumentos.base).resolve()
    if not ruta.exists():
        print(f"No encuentro la base de datos en {ruta}.")
        return 1

    print(f"Base de datos: {ruta}")
    print(f"Tamaño: {ruta.stat().st_size:,} bytes")

    try:
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
    except Exception as fallo:  # noqa: BLE001 — se cuenta en cristiano, no con una traza
        print(f"\nNo se puede abrir esa base: {fallo}")
        return 1

    # 1. La copia, antes de nada. `crear_tablas` reconstruye tablas cuando hace falta, y **no lo hace
    # sin una copia que se pueda abrir**: si no se puede copiar, levanta `RuntimeError` y aquí se
    # cuenta en cristiano en vez de dejar salir una traza de Python.
    copia = None
    if argumentos.migrar or argumentos.deshacer:
        try:
            copia = database._copia_de_seguridad_del_fichero(motor)
        except (RuntimeError, sqlite3.Error, OSError) as fallo:
            print(f"\nNo se toca nada: {fallo}")
            print("La base de datos se queda exactamente como estaba.")
            return 1
        print(f"\nCopia de antes de empezar: {copia}")

    antes = _huella_del_texto(ruta)

    from sqlalchemy.orm import Session

    with Session(motor) as sesion:
        toca_el_esquema = argumentos.migrar or argumentos.deshacer
        ya_estan_las_tablas = _estan_las_tablas(motor)
        if toca_el_esquema:
            # 2. El esquema: las tres tablas del T11 tienen que existir. Se crean como al arrancar el
            # programa (`crear_tablas` añade lo que falte y no toca ninguna fila). **Y solo se hace
            # cuando se va a escribir**: en el informe, mirar no puede cambiar nada.
            creadas, columnas = database.crear_tablas(motor)
            if creadas or columnas:
                print(f"\nEsquema puesto al día: tablas {creadas}, columnas {columnas}")
            ya_estan_las_tablas = True
        elif not ya_estan_las_tablas:
            print(
                "\nOjo: esta base todavía no tiene las tablas de los contactos, así que no hay ningún"
                "\nenlace que leer y todo lo escrito sale como «sin dueño». Se crean al migrar (con su"
                "\ncopia hecha antes), no al mirar."
            )

        fincas = _las_fincas(sesion)
        if argumentos.finca is not None:
            fincas = [f for f in fincas if f.id == argumentos.finca]
            if not fincas:
                print(f"\nNo hay ninguna finca con el identificador {argumentos.finca}.")
                return 1
        if not fincas:
            print("\nEsta base no tiene ninguna finca: no hay nada que mirar.")
            return 0

        print(f"\nFincas en esta base: {len(fincas)}")
        if argumentos.deshacer:
            print("\nDeshaciendo lo que apuntó la migración:")
            for finca in fincas:
                _deshacer(sesion, finca)
        else:
            informes = []
            for finca in fincas:
                informe = _el_informe(sesion, finca, con_enlaces=ya_estan_las_tablas)
                _ensenar(informe)
                informes.append(informe)

            if not argumentos.migrar:
                print("\nEsto es solo el informe: no se ha tocado nada.")
                print("Para apuntar las fichas seguras, añade --migrar.")
                return 0

            print("\nApuntando las fichas seguras:")
            total_fichas = 0
            total_enlaces = 0
            for informe in informes:
                resultado = _migrar(sesion, informe)
                total_fichas += resultado["fichas"]
                total_enlaces += resultado["enlaces"]
            print(
                f"\nEn total: {total_fichas} fichas y {total_enlaces} enlaces. "
                "Ni un texto escrito se ha tocado."
            )

    despues = _huella_del_texto(ruta)
    if antes != despues:
        print(
            "\n¡Los nombres escritos a mano han cambiado! Esto no puede pasar en esta migración."
            f"\nVuelve a poner la copia: {copia} encima de {ruta} (y borra {ruta}-wal y {ruta}-shm)."
        )
        return 1
    print(
        f"\nComprobado: los nombres escritos a mano están igual que antes"
        f"\n  huella de antes:  {antes}"
        f"\n  huella de después: {despues}"
    )
    if argumentos.migrar:
        print(f"\nPara volver atrás: `python scripts/migrar_contactos.py --base {ruta} --deshacer`")
    if copia:
        print(f"O, a mano: copia {copia} encima de {ruta} y borra {ruta}-wal y {ruta}-shm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
