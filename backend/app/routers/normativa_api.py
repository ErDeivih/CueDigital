"""La normativa: las reglas de la matriz, servidas como estan (07/10/2026).

Lo que se sirve sale **entero** de `app.normativa`, que a su vez sale de `docs/MATRIZ_NORMATIVA_CRM.md`. Aqui
**no se decide nada**: ni se resume, ni se clasifica, ni se reordena. Si algo no esta en la matriz, no sale.

Dos cosas que van **como estan**, y que la pantalla tiene que saber leer:

- `tipo` y `estado` pueden venir **vacios**: la matriz define los cinco tipos y los cinco estados, pero no dice
  cual es cada regla, y rellenarlos aqui seria inventar una clasificacion legal.
- **`fuentes` es una lista**: hay reglas que se apoyan en cuatro normas distintas (N07).
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import normativa
from ..schemas import SalidaBase

router = APIRouter(prefix="/api", tags=["normativa"])


class FuenteSalida(SalidaBase):
    """Una direccion oficial, con el nombre con el que la matriz la cita."""

    nombre: str
    enlace: str


class ReglaSalida(SalidaBase):
    """Una regla de la normativa, tal y como la cuenta la matriz."""

    codigo: str
    titulo: str
    fuentes: list[FuenteSalida]
    texto: str
    # **La ayuda para el agricultor** (07/10/2026): `texto` es la matriz tal cual -documentacion de
    # trabajo- y esto es lo mismo dicho para el. La pantalla enseña esto.
    ayuda: str
    # Vacios a proposito, y **con su motivo escrito aqui**: la matriz no dice cual es el tipo ni el estado de
    # cada regla, y rellenarlos seria inventar una clasificacion legal. La pantalla los ensena como «sin
    # clasificar», y solo `activa` participa en comprobaciones concluyentes.
    tipo: str
    estado: str


@router.get("/normativa", response_model=list[ReglaSalida])
def las_reglas_de_la_normativa() -> list[ReglaSalida]:
    """Las diez reglas, con sus direcciones oficiales, tal y como las cuenta la matriz."""
    return [
        ReglaSalida(
            codigo=una.codigo,
            titulo=una.titulo,
            fuentes=[FuenteSalida(nombre=fuente.nombre, enlace=fuente.enlace) for fuente in una.fuentes],
            texto=una.texto,
            ayuda=una.ayuda,
            tipo=una.tipo,
            estado=una.estado,
        )
        for una in normativa.LAS_REGLAS
    ]
