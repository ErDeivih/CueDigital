"""El dictado: de una frase dicha en voz alta a un apunte a medio hacer.

Se separa de `borradores.py` por el mismo motivo que `validaciones.py` se separa de
`legal.py`: allí está la lógica, que se prueba sin servidor, y aquí solo se resuelve
el texto que se enseña y se comprueba que los datos sean de esta finca.

**Aviso importante sobre lo que esto NO hace:** no guarda nada. Devuelve un borrador
para que el agricultor lo mire y lo confirme. Un modelo de lenguaje, hoy o mañana,
nunca escribe directamente en un cuaderno de campo: se equivoca, y aquí un error es
una sanción.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from sqlalchemy import select

from .. import borradores, legal, models, textos
from ..deps import Db, ExplotacionActual
from ..schemas import BorradorEntrada, BorradorSalida, EntendidoSalida, FaltaSalida

router = APIRouter(prefix="/api", tags=["borradores"])

# Campos que son fechas, para enseñarlos como los lee una persona y no como los guarda
# la base de datos: "2026-05-01" no se lee, "01/05/2026" sí.
CAMPOS_DE_FECHA = {"fecha"}


def _pregunta(etiqueta: str) -> str:
    """La pregunta que hay que hacer por un dato, la misma que en el asistente."""
    datos = textos.ETIQUETAS.get(etiqueta) or {}
    return datos.get("pregunta", "")


def _para_leer(campo: str, valor) -> str:
    if campo in CAMPOS_DE_FECHA:
        try:
            return legal.formatea_fecha(dt.date.fromisoformat(str(valor)))
        except ValueError:
            return str(valor)
    # Ojo con los enteros: "dos litros" se entiende como el entero 2, y sin esto
    # saldría "2" en pantalla mientras "2,5" saldría como "2,50". Los dos van igual.
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, (int, float)):
        return legal.formatea_numero(float(valor), 2)
    return str(valor)


@router.post("/borradores/desde-texto", response_model=BorradorSalida)
def desde_texto(
    datos: BorradorEntrada, explotacion: ExplotacionActual, db: Db
) -> BorradorSalida:
    """Entiende una frase dictada y devuelve el apunte a medio hacer.

    Los catálogos que se le pasan son SOLO los de esta finca: así el borrador no puede
    proponer un producto o una parcela de otro agricultor.
    """
    parcelas = list(
        db.scalars(
            select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
        )
    )
    productos = list(
        db.scalars(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == explotacion.id
            )
        )
    )
    abonos = list(
        db.scalars(
            select(models.Fertilizante).where(
                models.Fertilizante.explotacion_id == explotacion.id
            )
        )
    )

    bruto = borradores.redacta_borrador(
        datos.texto, parcelas=parcelas, productos=productos, abonos=abonos
    )

    entendido = [
        EntendidoSalida(
            etiqueta=entrada["etiqueta"],
            pregunta=_pregunta(entrada["etiqueta"]),
            valor=_para_leer(entrada.get("campo") or "", entrada["valor"]),
            campo=entrada.get("campo"),
            bruto=entrada.get("bruto"),
        )
        for entrada in bruto["entendido"]
    ]

    return BorradorSalida(
        tipo=bruto["tipo"],
        datos=bruto["datos"],
        entendido=entendido,
        falta=[
            FaltaSalida(campo=item["campo"], pregunta=_pregunta(item["etiqueta"]))
            for item in bruto["falta"]
        ],
        fuente=bruto["fuente"],
        titulo=textos.BORRADOR["titulo"],
        intro=textos.BORRADOR["intro"],
        falta_intro=textos.BORRADOR["falta_intro"],
        nada_entendido=None if entendido else textos.BORRADOR["nada_entendido"],
    )
