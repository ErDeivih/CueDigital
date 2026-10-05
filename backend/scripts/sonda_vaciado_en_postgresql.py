"""Sonda: ¿por qué la suite no vacía la base entre pruebas cuando corre contra PostgreSQL?

**AVISO GRAVE, APRENDIDO A LA MALA (02/10/2026).** La primera versión de esta sonda ponía la dirección
en `CUEDIGITAL_SUITE_SOBRE`, que es una variable que **solo lee `tests/conftest.py`**. Como este guion no
importa el conftest, `app.database` no veía ninguna dirección, se iba al valor por defecto
(`sqlite:///./cuedigital.db`) y **la sonda se ejecutó contra la base de verdad de David**: le vació las 37
tablas y le metió una cuenta de prueba. No se perdió ni una fila —el programa había dejado dos copias al
lado y se restauró byte a byte desde la copia—, pero es exactamente el susto que este proyecto prohíbe.

Por eso la sonda **no tiene dirección por defecto**, **solo acepta PostgreSQL** y **comprueba el motor de
verdad** antes de tocar nada.

**La hipótesis que mide esta sonda.** En `_vaciar_todo()` (de `tests/conftest.py`) los borrados y el
reinicio del contador de identificadores van **en la misma transacción**:

    with engine.begin() as conexion:
        for tabla in reversed(...sorted_tables):
            conexion.execute(tabla.delete())
        try:
            conexion.exec_driver_sql("DELETE FROM sqlite_sequence")
        except Exception:
            pass

En SQLite, `sqlite_sequence` puede no existir y el error es inofensivo: la transacción sigue y los
borrados se confirman. **En PostgreSQL, cualquier error dentro de una transacción la deja abortada**: el
`COMMIT` se convierte en `ROLLBACK` y **se deshacen todos los borrados**. Si eso es verdad, la suite no
limpia nada en PostgreSQL (y todo lo que viene detrás se encuentra la cuenta de pruebas ya creada).

Esta sonda lo comprueba en dos pasadas, la de ahora y la corregida, sobre la misma base.

    $env:CUEDIGITAL_SONDA_PG = "postgresql+psycopg://postgres:pruebas@127.0.0.1:55432/cuedigital_pruebas"
    ..\\.venv\\Scripts\\python.exe scripts\\sonda_vaciado_en_postgresql.py
"""

from __future__ import annotations

import os
import pathlib
import sys

_DIRECCION = os.environ.get("CUEDIGITAL_SONDA_PG")
if not _DIRECCION:
    raise SystemExit(
        "Esta sonda NO tiene dirección por defecto, y es a propósito: su primera versión se ejecutó "
        "sin querer contra la base de verdad del agricultor y la vació. Pon la dirección de un "
        "PostgreSQL desechable en CUEDIGITAL_SONDA_PG."
    )
if not _DIRECCION.startswith(("postgresql", "postgres")):
    raise SystemExit(
        f"Esta sonda solo vale para PostgreSQL y le han dado {_DIRECCION!r}. Si lo que se quiere es "
        "vaciar una base de SQLite, eso no se hace aquí: la base del agricultor no se toca."
    )

os.environ["CUEDIGITAL_DATABASE_URL"] = _DIRECCION
os.environ["CUEDIGITAL_SUITE_SOBRE"] = _DIRECCION
os.environ["CUEDIGITAL_SECRETO"] = "secreto-solo-para-la-sonda"
os.environ["CUEDIGITAL_ENTORNO"] = "pruebas"
os.environ["CUEDIGITAL_ITERACIONES_PBKDF2"] = "1000"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app import models  # noqa: E402
from app.database import crear_tablas, engine, url_base_datos  # noqa: E402

if engine.dialect.name != "postgresql":
    raise SystemExit(
        f"El motor de la base es «{engine.dialect.name}» y esta sonda es solo para PostgreSQL. "
        f"Dirección: {url_base_datos()!r}. No se ha tocado nada."
    )

DATOS_CUENTA = {
    "explotacion": {
        "nombre": "Finca de la sonda",
        "nif": "70922320A",
        "provincia": "Salamanca",
        "municipio": "Peñaranda de Bracamonte",
    },
    "nombre": "Sonda",
    "correo": "sonda@ejemplo.test",
    "clave": "una-clave-larga-de-verdad",
}


def cuantas(tabla: str) -> int:
    with engine.connect() as conexion:
        return conexion.execute(
            select(func.count()).select_from(models.Base.metadata.tables[tabla])
        ).scalar()


def alta() -> int:
    """Da de alta la cuenta de pruebas por la API, como hace la suite, y devuelve el código."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as cliente:
        return cliente.post("/api/cuenta/registro", json=DATOS_CUENTA).status_code


def vaciar(*, reiniciar_el_contador: bool) -> None:
    """El vaciado de `_vaciar_todo()`, con y sin el paso que solo vale para SQLite."""
    with engine.begin() as conexion:
        for tabla in reversed(models.Base.metadata.sorted_tables):
            conexion.execute(tabla.delete())
        if reiniciar_el_contador:
            try:
                conexion.exec_driver_sql("DELETE FROM sqlite_sequence")
            except Exception as fallo:  # noqa: BLE001 - es justo lo que se quiere ver
                print(f"          (el paso de SQLite falló: {type(fallo).__name__})")


def main() -> int:
    print(f"Servidor: {_DIRECCION.split('@')[-1]}")
    print(f"Motor:    {engine.dialect.name}")
    crear_tablas()

    print("\n=== PASADA 1: el vaciado tal y como está hoy (con el paso de SQLite dentro) ===")
    print(f"  usuarios antes de nada: {cuantas('usuarios')}")
    print(f"  alta de la cuenta: {alta()}")
    print(f"  usuarios después del alta: {cuantas('usuarios')}")
    vaciar(reiniciar_el_contador=True)
    tras_la_primera = cuantas("usuarios")
    print(f"  usuarios después del vaciado: {tras_la_primera}")

    print("\n=== PASADA 2: el vaciado sin el paso de SQLite (o sea, en su dialecto) ===")
    print(f"  alta de la cuenta otra vez: {alta()}")
    print(f"  usuarios después del alta: {cuantas('usuarios')}")
    vaciar(reiniciar_el_contador=False)
    tras_la_segunda = cuantas("usuarios")
    print(f"  usuarios después del vaciado: {tras_la_segunda}")

    print("\n=== VEREDICTO ===")
    print(f"  con el paso de SQLite dentro: {'NO vacía' if tras_la_primera else 'vacía'}")
    print(f"  sin ese paso:                 {'NO vacía' if tras_la_segunda else 'vacía'}")
    if tras_la_primera and not tras_la_segunda:
        print(
            "  CONFIRMADO: en PostgreSQL, el error de `sqlite_sequence` aborta la transacción y se "
            "deshacen los borrados."
        )
        return 0
    print("  La hipótesis NO queda confirmada con esta medida: hay que seguir mirando.")
    return 1


if __name__ == "__main__":
    try:
        codigo = main()
    finally:
        engine.dispose()
    raise SystemExit(codigo)
