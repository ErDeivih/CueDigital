"""Baja el inventario de catálogos públicos de SIEX, sin certificado.

El portal público de SIEX publica la **estructura** de sus catálogos —el nombre de cada tabla y
sus columnas— en una dirección que no pide certificado. Lo que **no** publica son los valores de
cada tabla: eso está detrás de un captcha y este script no lo intenta.

¿Para qué sirve tener los nombres? Porque el descriptor del cuaderno nombra los catálogos en
prosa («Catálogo de Eficacia del tratamiento») y de ahí no se puede sacar qué tabla hay que
mirar. Cruzando los dos nombres, los que coinciden **exactamente** dan una correspondencia que
es un dato y no una suposición: 15 de los 40. Los otros 25 se quedan sin emparejar y se dicen,
porque emparejarlos «por parecido» sería inventar.

Se ejecuta desde `backend`:

    ../.venv/Scripts/python.exe scripts/bajar_catalogos_siex.py
"""

from __future__ import annotations

import json
import pathlib
import unicodedata

DIRECCION = "https://www3.sede.fega.gob.es/bdcsixpor/tablas/configJson"

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "data" / "siex_catalogos.json"


def normaliza(texto: str) -> str:
    """Sin mayúsculas, sin acentos y con los espacios de dentro colapsados."""
    sin_acentos = unicodedata.normalize("NFKD", texto or "")
    limpio = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return " ".join(limpio.lower().split())


def main() -> int:
    import httpx

    respuesta = httpx.get(DIRECCION, timeout=90.0)
    respuesta.raise_for_status()
    catalogos = respuesta.json()["catalogos"]

    salida = {
        "_leeme": (
            "DERIVADO de la direccion publica de catalogos de SIEX, que no pide certificado. "
            "Son los NOMBRES y las columnas de cada tabla: los VALORES de cada tabla estan "
            "detras de un captcha y no se han bajado. Se rehace con "
            "scripts/bajar_catalogos_siex.py"
        ),
        "direccion": DIRECCION,
        "catalogos": [
            {
                "id": c.get("id"),
                "nombre": c.get("nombreCatalogo"),
                "publico": bool(c.get("visiblePortal")),
                # `fields` viene como lista de nombres de columna, en texto.
                "columnas": [str(columna) for columna in (c.get("fields") or [])],
            }
            for c in catalogos
        ],
    }
    SALIDA.write_text(
        json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    publicos = sum(1 for c in salida["catalogos"] if c["publico"])
    print(f"catalogos: {len(salida['catalogos'])}  (publicos: {publicos})")
    print(f"escrito: {SALIDA}")
    print()
    print("Primeros cinco, para ver que trae:")
    for c in salida["catalogos"][:5]:
        print(f"   {c['id']:<28} {c['nombre']!r}  columnas={len(c['columnas'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
