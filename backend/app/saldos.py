"""El saldo de un contacto: **cuánto nos debe y cuánto le debemos, cada uno por su lado**.

POR QUÉ ESTE FICHERO (13/10/2026). La ficha de un contacto decía con quién se trabaja y qué papeles tiene
enlazados, pero **no cuánto dinero hay en juego**, que es la primera cosa que se mira antes de llamar a alguien.
Aquí se calcula, y se calcula **sin inventar nada**: se apoya en la regla única del dinero (`app/servicios.py`)
y en los enlaces que ya existen.

LAS DECISIONES, que son las que hacen que esto sea de fiar:

1. **Por `contacto_id`, jamás por el nombre.** El encargo lo prohíbe con estas palabras: *«No adjudicar documentos
   a un contacto por coincidencia de nombres»*. Y hay una consecuencia que conviene tener delante: la factura de
   compra (`models.Factura`) **no tiene `contacto_id`** —su proveedor es texto—, así que **no entra** en el saldo
   de nadie. La obligación de una compra vive en su **gasto** (`Gasto.contacto_id`), que es el que sí dice de
   quién es; por eso una compra con factura **y** gasto cuenta **una sola vez**, y no por una resta afortunada
   sino porque la factura no se cuenta nunca.
2. **Los dos sentidos van separados y no se compensan.** Que a la misma persona se le venda y se le compre es lo
   normal, y restar una deuda de otra esconde las dos. Se dan `nos_debe` y `le_debemos` por separado.
3. **Lo que no se debe todavía no es deuda.** Una entrega **sin facturar** sí se debe (el género está entregado),
   así que cuenta; lo que no puede pasar es contarla **dos veces** cuando ya está en una factura: se excluyen las
   entregas con línea viva en una factura, que es además lo que impide el índice único parcial de la base.
4. **El dinero sin asignar se enseña, no se suma.** Un cobro que no está aplicado a ninguna factura no rebaja lo
   que nos deben (no se sabe de qué es), pero **tampoco se esconde**: va en su lista. Y **un exceso no es un
   anticipo**: que alguien haya pagado más de lo que debía se marca **para revisar**, porque puede ser un error de
   tecleo, un pago de otra cosa o una devolución pendiente. El encargo lo dice: *«No interpretar todo exceso de
   cobro como anticipo»*.
5. **Un importe que no se sabe no es un cero.** Si falta un importe, el pendiente va en `None` y el documento
   aparece en la cobertura. Sumar ceros daría un total falso con toda la apariencia de ser verdad.
6. **La moneda se dice.** No hay ninguna columna de moneda en la base (lo comprobó la revisión) y `dinero.py`
   deja escrito que aquí todo es euro y no hay tabla de cambios; así que el saldo **lo declara** en vez de
   suponerlo en silencio. No se suman monedas distintas porque **no hay** monedas distintas.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import dinero, gastos as logica_de_gastos, models, servicios, ventas as logica_de_ventas

# El programa es todo-euro y lo tiene escrito (`dinero.py`): aquí **se declara**, no se supone.
MONEDA = "EUR"


def el_saldo_de_un_contacto(db: Session, *, explotacion_id: int, contacto_id: int) -> dict:
    """Lo que nos debe y lo que le debemos, con sus documentos y su cobertura."""
    nos_debe = _lo_que_nos_debe(db, explotacion_id=explotacion_id, contacto_id=contacto_id)
    le_debemos = _lo_que_le_debemos(db, explotacion_id=explotacion_id, contacto_id=contacto_id)
    sin_asignar = _el_dinero_sin_asignar(db, explotacion_id=explotacion_id, contacto_id=contacto_id)
    los_dos_lados = {"nos_debe": nos_debe, "le_debemos": le_debemos}
    return {
        "contacto_id": contacto_id,
        "moneda": MONEDA,
        "nos_debe": nos_debe,
        "le_debemos": le_debemos,
        "sin_asignar": sin_asignar,
        # **Lo que hay que mirar con ojos**, junto y no mezclado con los totales de arriba.
        "para_revisar": _lo_que_hay_que_revisar(los_dos_lados),
        "cobertura": _la_cobertura(db, explotacion_id=explotacion_id, contacto_id=contacto_id),
    }


def _lo_que_nos_debe(db: Session, *, explotacion_id: int, contacto_id: int) -> dict:
    """Las facturas que le hemos hecho y las entregas que aún no están facturadas."""
    facturas = list(
        db.scalars(
            select(models.FacturaEmitida).where(
                models.FacturaEmitida.explotacion_id == explotacion_id,
                models.FacturaEmitida.contacto_id == contacto_id,
                models.FacturaEmitida.anulada.is_(False),
            )
        )
    )
    # **De una vez y no una por una**: la regla del dinero tiene su forma para lotes, y con esto no se hace una
    # consulta por factura.
    cobrado_por_factura = servicios.lo_cobrado_por_factura(db, explotacion_id=explotacion_id)
    documentos: list[dict] = []
    sin_importe = 0
    for factura in facturas:
        cobrado = cobrado_por_factura.get(factura.id, Decimal("0"))
        pendiente = logica_de_ventas.pendiente_de(factura.importe_total, cobrado)
        if factura.importe_total is None:
            sin_importe += 1
        documentos.append(
            {
                "clase": "factura_emitida",
                "id": factura.id,
                "referencia": getattr(factura, "numero", None) or f"Factura {factura.id}",
                "fecha": factura.fecha,
                "vencimiento": getattr(factura, "vencimiento", None),
                "importe": factura.importe_total,
                "cobrado": cobrado,
                "pendiente": pendiente,
                # Lo que excede del importe: **para revisar**, no para llamarlo anticipo.
                "exceso": (cobrado - factura.importe_total)
                if (factura.importe_total is not None and cobrado > factura.importe_total)
                else None,
            }
        )

    # Las entregas **que todavía no están en ninguna factura viva**: se deben, pero contarlas junto a su factura
    # sería contarlas dos veces. El índice único parcial de la base impide la otra mitad de ese error.
    ya_facturadas = select(models.LineaDeFacturaEmitida.venta_id).where(
        models.LineaDeFacturaEmitida.explotacion_id == explotacion_id,
        models.LineaDeFacturaEmitida.anulada.is_(False),
    )
    entregas = list(
        db.scalars(
            select(models.VentaDeCosecha).where(
                models.VentaDeCosecha.explotacion_id == explotacion_id,
                models.VentaDeCosecha.contacto_id == contacto_id,
                models.VentaDeCosecha.anulado.is_(False),
                models.VentaDeCosecha.id.not_in(ya_facturadas),
            )
        )
    )
    for entrega in entregas:
        # **Con sus ajustes**, que es lo que la entrega vale de verdad (una merma, un descuento del día). La
        # firma es de solo-palabra-clave a propósito, para que no se pueda llamar sin decir qué es cada número.
        los_ajustes = list(
            db.scalars(
                select(models.AjusteDeEntrega.importe).where(
                    models.AjusteDeEntrega.venta_id == entrega.id,
                    models.AjusteDeEntrega.anulado.is_(False),
                )
            )
        )
        su_importe = logica_de_ventas.importe_de_una_entrega(
            importe=entrega.importe,
            cantidad=entrega.cantidad,
            precio_unitario=entrega.precio_unitario,
            ajustes=los_ajustes,
        )
        if su_importe is None:
            sin_importe += 1
        documentos.append(
            {
                "clase": "entrega_sin_facturar",
                "id": entrega.id,
                "referencia": getattr(entrega, "numero_albaran", None) or f"Entrega {entrega.id}",
                "fecha": entrega.fecha,
                "vencimiento": getattr(entrega, "vencimiento", None),
                "importe": su_importe,
                "cobrado": Decimal("0"),
                "pendiente": su_importe,
                "exceso": None,
            }
        )
    return {
        "total": dinero.suma(*(documento["pendiente"] for documento in documentos)),
        "documentos": documentos,
        "sin_importe": sin_importe,
    }


def _lo_que_le_debemos(db: Session, *, explotacion_id: int, contacto_id: int) -> dict:
    """Los gastos que le hemos comprado y lo que queda por pagar de cada uno."""
    suyos = list(
        db.scalars(
            select(models.Gasto).where(
                models.Gasto.explotacion_id == explotacion_id,
                models.Gasto.contacto_id == contacto_id,
                models.Gasto.anulado.is_(False),
            )
        )
    )
    documentos: list[dict] = []
    sin_importe = 0
    for gasto in suyos:
        pagado = servicios.lo_pagado_de_un_gasto(db, explotacion_id=explotacion_id, gasto_id=gasto.id)
        pendiente = logica_de_gastos.pendiente_de(gasto.importe, pagado)
        if gasto.importe is None:
            sin_importe += 1
        documentos.append(
            {
                "clase": "gasto",
                "id": gasto.id,
                "referencia": getattr(gasto, "concepto", None) or getattr(gasto, "numero_factura", None)
                or f"Gasto {gasto.id}",
                "fecha": gasto.fecha,
                "vencimiento": getattr(gasto, "vencimiento", None),
                "importe": gasto.importe,
                "pagado": pagado,
                "pendiente": pendiente,
                "exceso": (pagado - gasto.importe)
                if (gasto.importe is not None and pagado > gasto.importe)
                else None,
            }
        )
    return {
        "total": dinero.suma(*(documento["pendiente"] for documento in documentos)),
        "documentos": documentos,
        "sin_importe": sin_importe,
    }


def _el_dinero_sin_asignar(db: Session, *, explotacion_id: int, contacto_id: int) -> dict:
    """Cobros y pagos que **no están aplicados a nada**: se enseñan, pero no rebajan ninguna deuda.

    Un cobro sin aplicar puede ser de esta factura o de otra, o de algo que aún no está apuntado; darlo por
    cobrado sería inventar. Y una aplicación **deshecha** en un pago se borra (esa tabla no tiene anulación), así
    que aquí no hay nada que filtrar por ese lado.
    """
    cobros_aplicados = select(models.AplicacionDeUnCobro.cobro_id).where(
        models.AplicacionDeUnCobro.anulado.is_(False)
    )
    sin_aplicar = list(
        db.scalars(
            select(models.Cobro).where(
                models.Cobro.explotacion_id == explotacion_id,
                models.Cobro.contacto_id == contacto_id,
                models.Cobro.anulado.is_(False),
                models.Cobro.id.not_in(cobros_aplicados),
            )
        )
    )
    pagos_aplicados = select(models.AplicacionDeUnPago.pago_id)
    pagos_sin_aplicar = list(
        db.scalars(
            select(models.PagoDeGasto).where(
                models.PagoDeGasto.explotacion_id == explotacion_id,
                models.PagoDeGasto.contacto_id == contacto_id,
                models.PagoDeGasto.anulado.is_(False),
                models.PagoDeGasto.id.not_in(pagos_aplicados),
            )
        )
    )
    return {
        "cobros": [
            {"id": cobro.id, "fecha": cobro.fecha, "importe": cobro.importe} for cobro in sin_aplicar
        ],
        "pagos": [
            {"id": pago.id, "fecha": pago.fecha, "importe": pago.importe} for pago in pagos_sin_aplicar
        ],
        # **No es un anticipo**: es dinero que está y no se sabe de qué. El nombre importa.
        "nota": "sin_asignar_no_es_un_anticipo",
    }


def _lo_que_hay_que_revisar(los_dos_lados: dict) -> list[dict]:
    """Los excesos: se ha cobrado o pagado **más** de lo que valía el documento.

    No se llama anticipo a propósito (el encargo lo prohíbe): puede ser un tecleo, un pago de otra cosa o una
    devolución pendiente, y quien lo mire lo sabrá. Aquí solo se avisa, con el documento delante.
    """
    return [
        documento
        for lado in ("nos_debe", "le_debemos")
        for documento in los_dos_lados[lado]["documentos"]
        if documento.get("exceso") is not None
    ]


def _la_cobertura(db: Session, *, explotacion_id: int, contacto_id: int) -> dict:
    """Hasta dónde llega este saldo: **lo que no se puede atribuir se dice**.

    La factura de compra no tiene `contacto_id` (su proveedor es texto), así que **no se adjudica por nombre**.
    Una compra cuyo gasto no esté apuntado con su contacto **no entra** en ningún saldo, y eso hay que decirlo en
    vez de dejar creer que el saldo está completo.
    """
    facturas_de_compra_sin_contacto = db.scalar(
        select(models.Factura.id)
        .where(
            models.Factura.explotacion_id == explotacion_id,
            models.Factura.anulada.is_(False),
            ~models.Factura.id.in_(
                select(models.Gasto.factura_id).where(
                    models.Gasto.explotacion_id == explotacion_id,
                    models.Gasto.contacto_id == contacto_id,
                    models.Gasto.anulado.is_(False),
                )
            ),
        )
        .limit(1)
    )
    return {
        "se_adjudica_por": "contacto_id",
        "no_se_adjudica_por_nombre": True,
        # Se dice cuántos documentos quedan fuera, para poder revisarlos.
        "hay_facturas_de_compra_sin_contacto": facturas_de_compra_sin_contacto is not None,
        "nota": "las_facturas_de_compra_sin_gasto_con_contacto_no_entran_en_ningun_saldo",
    }
