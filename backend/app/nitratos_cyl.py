"""Tablas verificadas de los anexos III y V de la Orden MAV/398/2022.

El fichero de datos es un derivado reproducible, no una lista transcrita a mano. Si
falta, devolvemos colecciones vacías: no se suplanta una norma con valores supuestos.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

RUTA_POR_DEFECTO = (
    Path(__file__).resolve().parents[2]
    / "data" / "nitratos_cyl" / "limites_y_periodos_mav_398_2022.json"
)


def cargar(ruta: Path | str | None = None) -> dict:
    ruta = Path(ruta) if ruta is not None else RUTA_POR_DEFECTO
    if not ruta.is_file():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(datos, dict) or not isinstance(datos.get("aportes_maximos"), list):
        return {}
    if not isinstance(datos.get("periodos_prohibidos"), list):
        return {}
    if not datos.get("fuente_sha256") or not datos.get("fuente_url"):
        return {}
    return datos


def aportes_maximos(ruta: Path | str | None = None) -> tuple[dict, ...]:
    return tuple(cargar(ruta).get("aportes_maximos", ()))


def periodos_prohibidos(ruta: Path | str | None = None) -> tuple[dict, ...]:
    return tuple(cargar(ruta).get("periodos_prohibidos", ()))


def _normaliza(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto or "")
    sin_acentos = "".join(letra for letra in base if not unicodedata.combining(letra))
    return " ".join(sin_acentos.casefold().split())


def aporte_de(cultivo: str, sistema: str, ruta: Path | str | None = None) -> dict | None:
    """Devuelve solo una celda que exista literalmente; no aproxima cultivos ni sistemas."""
    if sistema not in ("secano", "regadio"):
        return None
    buscado = _normaliza(cultivo)
    if not buscado:
        return None
    for fila in aportes_maximos(ruta):
        if _normaliza(fila.get("cultivo", "")) == buscado:
            return fila.get(sistema)
    return None
