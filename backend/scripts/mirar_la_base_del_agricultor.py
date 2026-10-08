"""Mirar la base del agricultor **sin tocarla**: en solo lectura y sobre una copia.

## Por qué existe este fichero

El 07/10/2026 hice una comprobación de una línea con `python -c` que importaba `app.main` y abría un
`TestClient` **sin `CUEDIGITAL_DATABASE_URL`**. Al importar la aplicación, sus **migraciones de arranque se
ejecutaron contra la base de verdad**: creó índices y reconstruyó tablas. No se perdió nada —la aplicación
guarda su copia antes de migrar, y los datos eran idénticos en las dos— pero **la base del agricultor no se
toca**, y esa orden la tocó.

Este guion es lo que había que haber usado. Hace tres cosas, y ninguna escribe:

  1. **copia** la base a una carpeta temporal;
  2. abre **la copia** en modo solo lectura (`file:…?mode=ro`);
  3. cuenta filas y comprueba la integridad, y lo dice.

**Lo que este guion NO hace, a propósito**: importar `app.main`, usar SQLAlchemy ni abrir la base original
en escritura. Si algún día alguien le añade eso, deja de servir para lo que está escrito aquí.

Uso:  python scripts/mirar_la_base_del_agricultor.py [ruta-de-la-base]
"""

from __future__ import annotations

import pathlib
import shutil
import sqlite3
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
POR_DEFECTO = RAIZ / "cuedigital.db"

LO_QUE_SE_CUENTA = (
    "explotaciones",
    "usuarios",
    "campanas",
    "parcelas",
    "parcela_cultivos",
    "labores",
    "gastos",
    "documentos_anexos",
    "contactos",
    "maquinas",
)


def main() -> int:
    original = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else POR_DEFECTO
    if not original.exists():
        print(f"no está esa base: {original}")
        return 1

    tamano = original.stat().st_size
    print(f"la base: {original} ({tamano:,} bytes)".replace(",", "."))

    with tempfile.TemporaryDirectory(prefix="cuedigital-mirar-la-base-") as temporal:
        copia = pathlib.Path(temporal) / "copia.db"
        shutil.copyfile(original, copia)
        # **Solo lectura, y sobre la copia**: así, aunque alguien se equivoque de orden, la de verdad no se
        # abre en escritura ni por accidente.
        con = sqlite3.connect(f"file:{copia}?mode=ro", uri=True)
        cur = con.cursor()
        tablas = [
            fila[0]
            for fila in cur.execute("select name from sqlite_master where type = 'table' order by name")
        ]
        print(f"tablas: {len(tablas)}")
        for nombre in LO_QUE_SE_CUENTA:
            if nombre in tablas:
                cuantas = cur.execute(f"select count(*) from {nombre}").fetchone()[0]
                print(f"  {nombre}: {cuantas}")
        print("integridad:", cur.execute("pragma integrity_check").fetchone()[0])
        problemas = cur.execute("pragma foreign_key_check").fetchall()
        print("claves ajenas:", "sin problemas" if not problemas else problemas[:5])
        con.close()

    print("\nEsto solo ha mirado una copia: la base de verdad no se ha abierto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
