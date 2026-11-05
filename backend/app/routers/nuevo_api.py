"""**Las dos puertas del armazón nuevo** (`IMP-1`, 05/11/2026).

La interfaz nueva se sirve aparte, en `/nuevo/`, y la vieja sigue viva en `/`. Estas dos puertas son
todo lo que la app nueva necesita para abrir: **qué hay hoy** (`/api/nuevo/hoy`) y **cuáles son mis
tierras** (`/api/nuevo/tierras`). La cuenta de cada una está en `app/nuevo.py`; aquí solo se pone la
puerta, con su autorización, que es lo que no se puede dejar en la pantalla.

**Las dos piden sesión y finca**, con las dependencias de `app/deps.py`: `UsuarioActual` valida el
vale y comprueba que esa cuenta puede entrar en la finca, y `ExplotacionActual` fija la finca en la
que se está trabajando. Sin ellas, la dirección a mano devolvería los datos de cualquiera.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import nuevo
from ..deps import Db, ExplotacionActual, UsuarioActual

router = APIRouter(prefix="/api/nuevo", tags=["nuevo"])


@router.get("/hoy")
def lo_de_hoy(explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db) -> dict:
    """**La finca, la campaña, las tierras y los últimos apuntes, en una sola llamada.**

    Es lo que pinta la pantalla de inicio de la app nueva: el saludo con el nombre del agricultor, el
    año que está llevando, cuántas tierras tiene y qué es lo último que apuntó. **Nada de esto se
    inventa**: sin tierras son cero tierras y cero hectáreas de verdad, y sin apuntes la lista va
    vacía (el motivo está contado en `app/nuevo.py`).
    """
    return nuevo.hoy(db, explotacion=explotacion, usuario=usuario)


@router.get("/tierras")
def mis_tierras(explotacion: ExplotacionActual, db: Db, campana_id: int | None = None) -> dict:
    """**Las tierras de la finca, agrupadas por municipio, con su forma y lo que hay sembrado.**

    La campaña es la que se está llevando; se puede pedir otra con `?campana_id=`, y una campaña de
    otra finca contesta **404** (`nuevo.la_campana_activa`), como en el resto del programa.

    El `anillo` de cada tierra son los puntos de su forma en `[longitud, latitud]` y va en `None` si la
    tierra no tiene forma: una parcela apuntada a mano no se dibuja, y la pantalla lo dice en vez de
    pintar un cuadro que no existe. `coef_regadio`, `region` y `admisibilidad` son atributos del
    SIGPAC que están llegando en paralelo; mientras no estén, valen `None`.
    """
    return nuevo.tierras(db, explotacion=explotacion, campana_id=campana_id)
