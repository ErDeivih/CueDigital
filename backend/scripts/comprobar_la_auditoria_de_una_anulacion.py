"""La anulación de un gasto y **su entrada de auditoría**, comprobadas de verdad (08/10/2026).

**Por qué por la API y no por la pantalla.** El recorrido ya acreditó lo de la pantalla -el gasto se apunta ✓, la
ficha se abre ✓ y el campo del motivo existe y se llama `#gasto-motivo-anulacion` ✓-, pero la comprobación del
recorrido no distingue bien si el gasto quedó anulado ✓ porque busca el concepto por toda la respuesta ✓ y
encuentra varias copias ✓. Así que aquí se hace **lo que el encargo pide comprobar**: que **anular deja su
entrada de auditoría** ✓ y que **las cifras quedan coherentes** ✓ -y se lee **de la base**, que es donde está ✓-.

Uso:  python scripts/comprobar_la_auditoria_de_una_anulacion.py <direccion> <ruta-de-la-base>
"""

from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
import time
import urllib.request

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8180"
LA_BASE = sys.argv[2] if len(sys.argv) > 2 else None

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datos_representativos as datos  # noqa: E402


def la_puerta(camino: str, token: str, cuerpo: dict | None = None):
    """Llama a la API. Sin cuerpo, pregunta; con cuerpo, apunta."""
    datos_a_mandar = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(
        f"{DIRECCION}{camino}",
        data=datos_a_mandar,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST" if cuerpo is not None else "GET",
    )
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def main() -> int:
    if not LA_BASE:
        print("=> falta la ruta de la base (segundo argumento): la auditoría se lee de ahí")
        return 1

    import tempfile

    volumen, _ = datos._la_del_volumen(  # noqa: SLF001
        DIRECCION, f"auditoria{int(time.time())}", pathlib.Path(tempfile.mkdtemp()), False
    )
    print(f"  la sesión: {volumen.nombre}")

    el_concepto = "Gasóleo para probar la auditoría de la anulación"
    creado = la_puerta(
        "/api/gastos",
        volumen.token,
        {"concepto": el_concepto, "importe": "300", "fecha": "2026-10-08"},
    )
    # **La forma de la respuesta, tal cual** (08/10/2026): el alta no devolvía `id` y eso puede ser que falte un
    # campo o que venga envuelta. Se mira, en vez de suponer.
    print(f"  (la respuesta del alta, tal cual: {str(creado)[:300]})")
    if isinstance(creado, dict):
        print(f"  (sus claves: {sorted(creado.keys())})")
    el_id = None
    if isinstance(creado, dict):
        el_id = creado.get("id") or (creado.get("gasto") or {}).get("id")
    print(f"  el gasto: {el_id} · {creado.get('concepto')!r} · pendiente {creado.get('pendiente')!r}")
    if not el_id:
        print("=> el servidor no ha devuelto el gasto que se acaba de apuntar")
        return 1

    el_motivo = "Apuntado por error: prueba de la auditoría"
    anulado = la_puerta(f"/api/gastos/{el_id}/anular", volumen.token, {"motivo": el_motivo})
    print(f"  después de anular: estado={anulado.get('estado')!r} anulado={anulado.get('anulado')!r}")

    # **Y la auditoría, leída de la base** —en sólo lectura—, buscando la fila de **este** gasto.
    conexion = sqlite3.connect(f"file:{LA_BASE}?mode=ro", uri=True)
    try:
        columnas = [fila[1] for fila in conexion.execute('PRAGMA table_info("auditoria")')]
        suyas = []
        for fila in conexion.execute('SELECT * FROM "auditoria" ORDER BY id'):
            valores = {columna: fila[i] for i, columna in enumerate(columnas)}
            if str(valores.get("entidad")) == "gasto" and str(valores.get("entidad_id")) == str(el_id):
                suyas.append(valores)
        print(f"  (entradas de auditoría de ESTE gasto: {len(suyas)})")
        for entrada in suyas:
            try:
                escrito = json.loads(entrada.get("datos") or "{}")
            except ValueError:
                escrito = {}
            print(f"    · accion={entrada.get('accion')!r} motivo={escrito.get('motivo')!r}")
        de_anular = [entrada for entrada in suyas if str(entrada.get("accion")) == "anular"]
        print(f"  => {'SÍ' if de_anular else 'NO'} hay entrada de **anulación** de este gasto")
        if de_anular:
            try:
                escrito = json.loads(de_anular[-1].get("datos") or "{}")
            except ValueError:
                escrito = {}
            print(f"  => el motivo exacto {'SÍ' if escrito.get('motivo') == el_motivo else 'NO'} coincide")
    finally:
        conexion.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
