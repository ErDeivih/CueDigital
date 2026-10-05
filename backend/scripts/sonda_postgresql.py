"""Sonda: ¿arranca y atiende CUE Digital contra **PostgreSQL de verdad**?

POR QUÉ EXISTE (02/10/2026)

`README.md:63` y `AGENTS.md:583` dicen que **la base de producción es PostgreSQL** («SQLite en
local, PostgreSQL/PostGIS en producción»), y `docs/REVISION_T05_Y_T09.md:166` lo repite al hablar
del defecto D2: *«la base de producción es PostgreSQL»*. Y sin embargo **no se había probado nunca
contra un servidor de verdad**: lo único medido era el SQL compilado en los dos dialectos.

Eso importa porque ya ha mordido dos veces en ese camino exacto:

  * **D2** — el arreglo de la clave de reenvío usaba solo `sqlite_where=`, así que en PostgreSQL el
    índice nacía único a secas y el fallo del reenvío del móvil volvía en producción.
  * **D3** — `crear_tablas()` no recreaba los índices de una instalación que ya tenía la tabla.

Esta sonda levanta el esquema con el **código real** (`app.database.crear_tablas`) contra un
PostgreSQL de verdad y comprueba lo que solo se ve ahí: que el esquema se crea entero, que los
índices con condición **llevan su condición**, y que la aplicación atiende un alta, una campaña y
una parcela, y las lee.

CÓMO SE USA

    # 1. Un servidor desechable (no toca nada del proyecto):
    docker run -d --name cuedigital-pg -e POSTGRES_PASSWORD=pruebas \
        -e POSTGRES_DB=cuedigital_pruebas -p 55432:5432 postgres:16-alpine

    # 2. La sonda:
    ..\\.venv\\Scripts\\python.exe scripts\\sonda_postgresql.py

    # 3. Y al terminar, se tira:
    docker rm -f cuedigital-pg

**No toca `backend/cuedigital.db`**: la dirección se fija aquí, antes de importar `app`, y apunta a
la sonda. Los adjuntos van a una carpeta temporal que se borra al final.

Hace falta el driver de producción (`pip install "psycopg[binary]"`), que **no está en
`requirements.txt`** aunque el README documente PostgreSQL como producción.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile

_URL_DE_LA_SONDA = os.environ.get(
    "CUEDIGITAL_SONDA_PG",
    "postgresql+psycopg://postgres:pruebas@127.0.0.1:55432/cuedigital_pruebas",
)

# Las variables se fijan ANTES de importar `app`: `app.database` crea el motor al importarse.
# Es el mismo cuidado que explica `tests/conftest.py`, y aquí es más importante todavía, porque
# esta sonda habla con un servidor de verdad.
_CARPETA_TEMPORAL = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital_sonda_pg_"))
os.environ["CUEDIGITAL_DATABASE_URL"] = _URL_DE_LA_SONDA
os.environ["CUEDIGITAL_SECRETO"] = "secreto-solo-para-la-sonda"
os.environ["CUEDIGITAL_ADJUNTOS"] = str(_CARPETA_TEMPORAL / "adjuntos")
os.environ["CUEDIGITAL_ENTORNO"] = "pruebas"
os.environ["CUEDIGITAL_ITERACIONES_PBKDF2"] = "1000"
os.environ["CUEDIGITAL_ZV_CYL_RUTA"] = str(_CARPETA_TEMPORAL / "zv_no_cargado.csv")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import crear_tablas, engine  # noqa: E402
from app.main import app  # noqa: E402

FALLOS: list[str] = []


def comprobar(condicion: bool, frase: str) -> None:
    print(("[OK]    " if condicion else "[FALLO] ") + frase)
    if not condicion:
        FALLOS.append(frase)


def main() -> int:
    if not _URL_DE_LA_SONDA.startswith("postgresql"):
        print(f"Esta sonda es para PostgreSQL y le han dado: {_URL_DE_LA_SONDA!r}")
        return 2

    print(f"Servidor: {_URL_DE_LA_SONDA.split('@')[-1]}")
    with engine.connect() as conexion:
        version = conexion.execute(text("select version()")).scalar()
    print(f"Versión:  {str(version).split(' on ')[0]}")

    # 1. El esquema entero, con el código real de la aplicación.
    #
    # Se atrapa el fallo a propósito: si el esquema no se puede crear, eso **es** el hallazgo, y la
    # sonda tiene que seguir midiendo lo demás en vez de morirse en la primera línea.
    try:
        crear_tablas()
        comprobar(True, "crear_tablas() deja el esquema listo")
    except Exception as fallo:  # noqa: BLE001 - es lo que se viene a medir
        comprobar(False, f"crear_tablas() deja el esquema listo: {type(fallo).__name__}: {fallo}")
    with engine.connect() as conexion:
        tablas = conexion.execute(
            text("select tablename from pg_tables where schemaname = 'public' order by 1")
        ).scalars().all()
    comprobar(len(tablas) > 30, f"el esquema se crea entero en PostgreSQL: {len(tablas)} tablas")

    # 2. Los índices, con su condición. Es exactamente lo que falló en D2: en PostgreSQL el
    #    índice nacía único a secas y el reenvío del móvil volvía a reventar en producción.
    with engine.connect() as conexion:
        indices = dict(
            conexion.execute(
                text("select indexname, indexdef from pg_indexes where schemaname = 'public'")
            ).all()
        )
    condicionados = {nombre: definicion for nombre, definicion in indices.items() if " WHERE " in definicion}
    comprobar(
        bool(condicionados),
        f"hay {len(condicionados)} índice(s) con condición en PostgreSQL (WHERE en su definición)",
    )
    for nombre, definicion in sorted(condicionados.items()):
        print(f"          · {nombre}: {definicion.split(' USING ')[-1]}")

    # Los dos que ya se arreglaron en su día tienen que estar, y con condición.
    for esperado in ("uq_recepcion_reenvio",):
        comprobar(
            any(esperado in nombre for nombre in condicionados),
            f"el índice {esperado} existe en PostgreSQL **con su condición**",
        )

    # 3. La aplicación, atendiendo de verdad: alta, campaña, parcela y lectura.
    with TestClient(app) as cliente:
        comprobar(cliente.get("/health").status_code == 200, "GET /health contesta")

        alta = cliente.post(
            "/api/cuenta/registro",
            json={
                "explotacion": {
                    "nombre": "Finca de la sonda",
                    "nif": "70922320A",
                    "provincia": "Salamanca",
                    "municipio": "Peñaranda de Bracamonte",
                },
                "nombre": "Sonda",
                "correo": "sonda@ejemplo.test",
                "clave": "una-clave-larga-de-verdad",
            },
        )
        comprobar(alta.status_code == 201, f"el alta de cuenta funciona: {alta.status_code}")
        if alta.status_code != 201:
            return 1
        cabeceras = {"Authorization": f"Bearer {alta.json()['token']}"}

        campana = cliente.get("/api/campanas/actual", headers=cabeceras)
        comprobar(campana.status_code == 200, f"la campaña en curso se lee: {campana.status_code}")

        parcela = cliente.post(
            "/api/parcelas",
            headers=cabeceras,
            json={
                "alias": "El Prado",
                "ref_sigpac": "37-455-12-3",
                "superficie_ha": 2.43,
                "superficie_oficial": True,
                "sistema": "secano",
                "uso_sigpac": "Labor secano",
                "municipio": "Peñaranda de Bracamonte",
                "provincia": "Salamanca",
            },
        )
        comprobar(parcela.status_code == 201, f"la parcela se guarda: {parcela.status_code}")
        if parcela.status_code == 201:
            listado = cliente.get("/api/parcelas", headers=cabeceras)
            comprobar(
                listado.status_code == 200 and len(listado.json() or []) == 1,
                f"y se vuelve a leer: {listado.status_code}, {len(listado.json() or [])} parcela(s)",
            )
            # La vista del mapa (T06) es la consulta más compuesta del proyecto: si hay SQL de
            # SQLite escondido en algún sitio, suele salir por aquí.
            vista = cliente.get("/api/parcelas/vista", headers=cabeceras)
            comprobar(vista.status_code == 200, f"la vista de tierras y mapa contesta: {vista.status_code}")

    print()
    if FALLOS:
        print(f"{len(FALLOS)} comprobación(es) en rojo:")
        for fallo in FALLOS:
            print(f"  - {fallo}")
        return 1
    print("Todo en verde contra PostgreSQL.")
    return 0


if __name__ == "__main__":
    try:
        codigo = main()
    finally:
        engine.dispose()
        shutil.rmtree(_CARPETA_TEMPORAL, ignore_errors=True)
        print(f"carpeta temporal borrada: {not _CARPETA_TEMPORAL.exists()}")
    raise SystemExit(codigo)
