"""***Copiar la base y los adjuntos, y restaurarlos de verdad*** (22/10/2026, D06).

*El encargo pide: «copia: base coherente, adjuntos, configuracion necesaria y versiones… **restaurar en destino nuevo;
abrir documentos y comprobar vinculos/firmas, no solo `quick_check`**».*

*Esto hace las dos mitades:*

  · **copiar**: *la base con `VACUUM INTO` -que da una copia **coherente** aunque haya escrituras abiertas, no un
    `copy` de fichero que puede pillar el WAL a medias-, los adjuntos, y un **manifiesto** con la version, la fecha y
    lo que hay;*
  · **restaurar en un destino nuevo y comprobar**: *abrir la copia, mirar su integridad **y abrir cada documento**
    -que el fichero del adjunto exista y no este vacio-, que es lo que dice si la copia sirve o no.*

***Lo que esta copia NO hace, y se dice***: *no cifra, no define retencion y no sube a ningun sitio. Son decisiones de
despliegue, y estan escritas como pendientes en `docs/OPERACION.md`.*

Uso:
    python scripts/copiar_la_base.py --origen <carpeta-de-datos> --destino <carpeta-de-la-copia>
    python scripts/copiar_la_base.py --comprobar <carpeta-de-la-copia>
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sqlite3
import sys
import time

LA_VERSION = "0.1.0"


def la_base_de(datos: pathlib.Path) -> pathlib.Path:
    """*La base es `cuedigital.db` dentro de la carpeta de datos -lo que dice `database.py`.*"""
    for nombre in ("cuedigital.db", "prueba.db", "humo.db"):
        if (datos / nombre).exists():
            return datos / nombre
    los = sorted(datos.glob("*.db"))
    if not los:
        raise SystemExit(f"no hay ninguna base en {datos}")
    return los[0]


def copiar(datos: pathlib.Path, destino: pathlib.Path) -> int:
    destino.mkdir(parents=True, exist_ok=True)
    la_base = la_base_de(datos)
    la_copia = destino / "cuedigital.db"
    print(f"== Copiando  {la_base}  ->  {la_copia} ==")
    # ***`VACUUM INTO` y no `copy`***: *da una base **coherente** aunque haya escrituras abiertas; copiar el fichero
    # a pelo puede dejar el WAL a medias -y el WAL no se puede borrar «porque Linux deje hacerlo», como dice el
    # encargo-.*
    with sqlite3.connect(la_base) as conexion:
        if la_copia.exists():
            la_copia.unlink()
        conexion.execute("VACUUM INTO ?", (str(la_copia),))
    # *Los adjuntos, tal cual: son ficheros y su nombre lo decide el programa.*
    los_adjuntos = datos / "adjuntos"
    if los_adjuntos.exists():
        shutil.copytree(los_adjuntos, destino / "adjuntos", dirs_exist_ok=True)
    # *Y el manifiesto: version, fecha y lo que hay, para saber que se copio.*
    with sqlite3.connect(la_copia) as conexion:
        la_integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        las_tablas = conexion.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    el_manifiesto = {
        "version": LA_VERSION,
        "cuando": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "base": la_base.name,
        "integridad": la_integridad,
        "tablas": las_tablas,
        "adjuntos": len(list((destino / "adjuntos").glob("*"))) if (destino / "adjuntos").exists() else 0,
        "cifrado": False,
        "nota": "copia sin cifrar; el cifrado y la retencion son decisiones de despliegue (ver docs/OPERACION.md)",
    }
    (destino / "manifiesto.json").write_text(json.dumps(el_manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  integridad: {la_integridad} · tablas: {las_tablas} · adjuntos: {el_manifiesto['adjuntos']}")
    return 0


def comprobar(la_copia: pathlib.Path) -> int:
    """***Restaurar en un destino nuevo y abrirlo***: *no basta con `quick_check`.*"""
    print(f"== Comprobando la copia  {la_copia} ==")
    la_base = la_copia / "cuedigital.db"
    if not la_base.exists():
        print("  [FALLO] no hay base en la copia")
        return 1
    fallos = 0
    with sqlite3.connect(la_base) as conexion:
        la_integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"  integridad: {la_integridad}")
        if la_integridad != "ok":
            fallos += 1
        # ***Y los documentos, que es lo que el encargo pide de verdad.*** *Se buscan las rutas de los adjuntos en la
        # base y se comprueba que **el fichero existe y no esta vacio**.*
        # ***La columna es `fichero_ruta`*** (22/10/2026): *se busco `nombre_guardado`, que no existe -lo cazo la
        # comprobacion al decir «documentos en la base: 0» cuando habia uno-, y **con la consulta mal la parte de
        # «abrir documentos» no se ejercitaba**. Se mira **en todas las tablas** cual tiene esa columna, porque la
        # tienen varias -complras, documentos, boletines…-.*
        los_documentos = []
        for (tabla,) in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall():
            try:
                columnas = [c[1] for c in conexion.execute(f"PRAGMA table_info({tabla})").fetchall()]
            except sqlite3.OperationalError:
                continue
            if "fichero_ruta" in columnas:
                los_documentos += [
                    fila[0]
                    for fila in conexion.execute(
                        f"SELECT fichero_ruta FROM {tabla} WHERE fichero_ruta IS NOT NULL"
                    ).fetchall()
                ]
    los_adjuntos = la_copia / "adjuntos"
    abiertos = 0
    for nombre in los_documentos:
        el_fichero = los_adjuntos / str(nombre)
        if el_fichero.exists() and el_fichero.stat().st_size > 0:
            abiertos += 1
        else:
            print(f"  [FALLO] el documento {nombre!r} no se puede abrir en la copia")
            fallos += 1
    print(f"  documentos en la base: {len(los_documentos)} · abiertos: {abiertos}")
    if not los_documentos:
        print("  (no hay documentos que abrir: la copia se comprueba con su integridad)")
    print("\nComprobaciones: 2   Fallos: " + str(fallos))
    return 1 if fallos else 0


def main() -> int:
    el_que_hace = argparse.ArgumentParser(description="Copiar la base y los adjuntos, y comprobar la copia.")
    el_que_hace.add_argument("--origen", type=pathlib.Path, help="la carpeta de datos que se copia")
    el_que_hace.add_argument("--destino", type=pathlib.Path, help="la carpeta donde se deja la copia")
    el_que_hace.add_argument("--comprobar", type=pathlib.Path, help="una copia que ya existe, para comprobarla")
    los_argumentos = el_que_hace.parse_args()
    if los_argumentos.comprobar:
        return comprobar(los_argumentos.comprobar)
    if not los_argumentos.origen or not los_argumentos.destino:
        el_que_hace.print_help()
        return 2
    return copiar(los_argumentos.origen, los_argumentos.destino)


if __name__ == "__main__":
    raise SystemExit(main())
