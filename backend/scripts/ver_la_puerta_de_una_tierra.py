"""¿Devuelve el `dibujo` la puerta de **una** tierra? (07/10/2026)

El dibujo de la parcela no sale en la ficha y ya se sabe que la ficha lo pide a `/api/parcelas/{id}`. Antes de
tocar nada más, aquí se comprueba **la puerta**, sin navegador: se crea una tierra con forma y se pregunta por
ella **a las dos puertas** —la de una tierra y la lista— para ver cuál de las dos lleva el dibujo.

Uso:  python ver_la_puerta_de_una_tierra.py http://127.0.0.1:8087
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

from datos_representativos import preparar  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8087"
GEOMETRIA = "POLYGON((-5.70 40.85, -5.692 40.85, -5.692 40.858, -5.70 40.858, -5.70 40.85))"


def main() -> int:
    escenario = preparar(DIRECCION)
    cabeceras = {"Authorization": f"Bearer {escenario.volumen.token}"}

    creada = httpx.post(
        f"{DIRECCION}/api/parcelas",
        json={"alias": "La de la forma, para mirar la puerta", "geometria": GEOMETRIA},
        headers=cabeceras,
        timeout=30.0,
    )
    print(f"crear la tierra con forma: {creada.status_code}")
    su_id = creada.json().get("id")
    print(f"  (su id: {su_id}; el dibujo que devuelve **al crearla**: {len(creada.json().get('dibujo') or '')} caracteres)")

    una = httpx.get(f"{DIRECCION}/api/parcelas/{su_id}", headers=cabeceras, timeout=30.0)
    print(f"GET /api/parcelas/{{id}} -> {una.status_code}")
    if una.status_code == 200:
        suyo = una.json()
        print(f"  claves: {sorted(suyo.keys())[:14]}…")
        print(f"  dibujo: {len(suyo.get('dibujo') or '')} caracteres · centro: {suyo.get('centro')}")

    todas = httpx.get(f"{DIRECCION}/api/parcelas", headers=cabeceras, timeout=30.0).json()
    la_misma = [una for una in todas if str(una.get("id")) == str(su_id)]
    print(
        "en la lista: "
        + (f"{len(la_misma[0].get('dibujo') or '')} caracteres de dibujo" if la_misma else "NO está")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
