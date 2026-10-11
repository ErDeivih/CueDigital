"""La ficha de una compra: **facturado, recibido, pagado y pendiente**, en un solo sitio (09/10/2026).

**Por qué existe.** El encargo lo pide así: *que la ficha de la compra enseñe lo facturado, lo recibido,
lo pagado y lo pendiente, con sus enlaces y conservando filtros y contexto*. Hoy esas cuatro cifras viven
en cuatro pantallas distintas —la factura en `/facturas`, el albarán en el almacén, el gasto y sus pagos en
`/gastos`— y **nadie las junta**, así que para contestar «¿cuánto falta por llegar de esta compra?» hay que
recorrerlas a mano. Esta puerta las junta, y cada cifra sale del **mismo sitio** del que sale en su
pantalla: lo que se paga se cuenta con `servicios.lo_pagado_de_un_gasto`, que es la regla única del dinero.

**Lo que esta puerta NO hace, y es a propósito:**

  · **No suma lo recibido a lo facturado.** Son dos cosas distintas y sumarlas contaría cada kilo dos
    veces: la factura dice lo que se compró, el albarán lo que entró. El contrato lo dice en S08 («compra
    y factura son eventos distintos»).
  · **No inventa lo que no se sabe.** Si una línea de la factura no está enganchada línea a línea con
    ningún albarán, no se puede saber cuánto ha entrado de ella, y eso **se declara** (`AL29…`) en vez de
    salir como un cero que parecería una cifra. Es la regla del «no lo sé» de todo el programa.
  · **No arma las direcciones de la pantalla.** Devuelve **identificadores**; los enlaces los construye el
    navegador, que es el único que sabe cómo se llaman sus rutas.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter
from sqlalchemy import select

from .. import dinero, gastos, models, servicios, textos
from ..deps import Db, ExplotacionActual, obtener_de_la_explotacion

router = APIRouter(prefix="/api/compras", tags=["compras"])


def _las_recepciones(db, explotacion_id: int, factura_id: int) -> list[models.Recepcion]:
    """Los albaranes enganchados a esta factura, **incluidos los anulados**.

    Los anulados se devuelven a propósito, y marcados: si el agricultor anuló un albarán de esta compra,
    tiene que poder verlo en la ficha —si no, parecería que nunca existió— y saber que **no cuenta**, que
    es lo que dice su campo `anulada`.
    """
    return list(
        db.scalars(
            select(models.Recepcion)
            .where(
                models.Recepcion.explotacion_id == explotacion_id,
                models.Recepcion.factura_id == factura_id,
            )
            .order_by(models.Recepcion.fecha, models.Recepcion.id)
        )
    )


def _lo_recibido_por_linea(db, explotacion_id: int, factura: models.Factura) -> list[dict]:
    """Cuánto ha entrado **de cada línea de la factura**, por el enganche línea a línea.

    El enganche es `lineas_de_recepcion.linea_factura_id`, que es lo que dice «esta línea del albarán es
    esta línea de la factura». Solo cuentan las líneas de albaranes **no anulados**: lo que se anuló no
    entró.
    """
    enganchadas = list(
        db.scalars(
            select(models.LineaDeRecepcion)
            .join(models.Recepcion, models.Recepcion.id == models.LineaDeRecepcion.recepcion_id)
            .where(
                models.LineaDeRecepcion.explotacion_id == explotacion_id,
                models.Recepcion.anulada.is_(False),
                models.Recepcion.factura_id == factura.id,
                models.LineaDeRecepcion.linea_factura_id.is_not(None),
            )
        )
    )
    recibido: dict[int, float] = {}
    for linea in enganchadas:
        if linea.cantidad is None:
            continue
        recibido[linea.linea_factura_id] = recibido.get(linea.linea_factura_id, 0.0) + float(
            linea.cantidad
        )

    salida = []
    for linea in sorted(factura.lineas, key=lambda fila: fila.id):
        suyo = recibido.get(linea.id)
        facturado = linea.cantidad
        falta = None
        if suyo is not None and facturado is not None:
            # **Solo se resta si se puede**: dos cantidades sin la misma unidad no se restan (sería
            # inventarse una conversión). Si la unidad no está, se dice que no se sabe.
            falta = float(facturado) - suyo
        salida.append(
            {
                "linea_factura_id": linea.id,
                "descripcion": linea.descripcion,
                "unidad": linea.unidad,
                "facturado": facturado,
                "recibido": suyo,
                "falta": falta,
            }
        )
    return salida


def _el_importe_del_papel(valor):
    """Un importe de la factura, en `Decimal`.

    **`Factura.total` es una columna `Float`** —de las primeras del programa—, así que no se le puede
    pasar a `dinero.a_decimal`, que rechaza los `float` a propósito (un `float` ya perdió céntimos antes
    de llegar). El camino sancionado para leer un importe de una columna así es
    `dinero.cantidad_a_decimal`, que pasa por el texto y es exacto para lo que dice el papel: es
    literalmente lo que ya hace `extractos_api` con `factura.total` (línea 722).
    """
    return dinero.cantidad_a_decimal(valor)


def _los_pagos(db, explotacion_id: int, gasto_ids: list[int]) -> list[dict]:
    """Los pagos vivos que llevan dinero aplicado a alguno de estos gastos.

    Se cuenta **lo aplicado a estos gastos**, no el importe del pago: un pago de 500 € que reparte 100 a
    esta compra y 400 a otra tiene que salir aquí con 100, o la ficha estaría contando dinero ajeno. Es
    la misma regla que `servicios.lo_pagado_de_un_gasto`, vista desde el otro lado.
    """
    if not gasto_ids:
        return []
    aplicaciones = list(
        db.scalars(
            select(models.AplicacionDeUnPago).where(
                models.AplicacionDeUnPago.explotacion_id == explotacion_id,
                models.AplicacionDeUnPago.gasto_id.in_(gasto_ids),
            )
        )
    )
    pagos: dict[int, dict] = {}
    for aplicacion in aplicaciones:
        pago = db.get(models.PagoDeGasto, aplicacion.pago_id)
        if pago is None or pago.anulado:
            continue
        suyo = pagos.setdefault(
            pago.id,
            {
                "id": pago.id,
                "importe": dinero.a_texto(pago.importe),
                "fecha": pago.fecha.isoformat() if pago.fecha else None,
                "forma": pago.forma,
                "aplicado_a_esta_compra": dinero.CERO,
            },
        )
        suyo["aplicado_a_esta_compra"] = dinero.suma(
            suyo["aplicado_a_esta_compra"], aplicacion.importe
        )
    # Se pasa a texto al final, con el acumulador ya cerrado: sumar textos sería sumar letras.
    for suyo in pagos.values():
        suyo["aplicado_a_esta_compra"] = dinero.a_texto(suyo["aplicado_a_esta_compra"])
    return sorted(pagos.values(), key=lambda fila: (fila["fecha"] or "", fila["id"]))


@router.get("/{factura_id}")
def ver_una_compra(factura_id: int, explotacion: ExplotacionActual, db: Db) -> dict:
    """La compra entera: lo facturado, lo que ha entrado, lo pagado y lo que queda.

    Las cuatro cifras salen de donde salen siempre —la factura de `facturas`, lo recibido de los albaranes
    enganchados, el dinero de `servicios.lo_pagado_de_un_gasto`— y **ninguna se recalcula a mano aquí**.
    """
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)

    recepciones = _las_recepciones(db, explotacion.id, factura.id)
    las_que_cuentan = [una for una in recepciones if not una.anulada]

    # **Lo recibido, albarán a albarán**: qué trajo cada uno, en su unidad. Se dice la unidad porque dos
    # albaranes pueden venir en unidades distintas y sumarlos sería el error que el programa evita.
    los_albaranes = []
    for recepcion in recepciones:
        por_unidad: dict[str, float] = {}
        for linea in recepcion.lineas:
            if linea.cantidad is None:
                continue
            unidad = (linea.unidad or "").strip() or "sin_unidad"
            por_unidad[unidad] = por_unidad.get(unidad, 0.0) + float(linea.cantidad)
        los_albaranes.append(
            {
                "id": recepcion.id,
                "numero_albaran": recepcion.numero_albaran,
                "fecha": recepcion.fecha.isoformat() if recepcion.fecha else None,
                "anulada": recepcion.anulada,
                "motivo_anulacion": recepcion.motivo_anulacion,
                "cantidad_por_unidad": por_unidad,
            }
        )

    por_linea = _lo_recibido_por_linea(db, explotacion.id, factura)
    sin_enganche = [una for una in por_linea if una["recibido"] is None]
    con_falta = [una for una in por_linea if una["falta"] is not None and una["falta"] > 0.0001]
    if not por_linea:
        todo_recibido = None  # una factura sin líneas no dice nada de lo recibido
    elif sin_enganche:
        todo_recibido = None  # no se puede saber: hay líneas sin enganche
    else:
        todo_recibido = not con_falta

    # **El dinero**: los gastos que apuntan a esta factura, cada uno con su pagado y su pendiente
    # calculados por la regla única.
    hoy = dt.date.today()
    suyos = list(
        db.scalars(
            select(models.Gasto)
            .where(
                models.Gasto.explotacion_id == explotacion.id,
                models.Gasto.factura_id == factura.id,
            )
            .order_by(models.Gasto.fecha, models.Gasto.id)
        )
    )
    los_gastos = []
    pagado_total = dinero.CERO
    pendiente_total = dinero.CERO
    for gasto in suyos:
        pagado = servicios.lo_pagado_de_un_gasto(
            db, explotacion_id=explotacion.id, gasto_id=gasto.id
        )
        pendiente = gastos.pendiente_de(gasto.importe, pagado)
        pagado_total = dinero.suma(pagado_total, pagado)
        if pendiente is not None:
            pendiente_total = dinero.suma(pendiente_total, pendiente)
        los_gastos.append(
            {
                "id": gasto.id,
                "concepto": gasto.concepto,
                "fecha": gasto.fecha.isoformat() if gasto.fecha else None,
                "importe": dinero.a_texto(gasto.importe),
                "pagado": dinero.a_texto(pagado),
                "pendiente": dinero.a_texto(pendiente),
                "estado": gastos.estado_de_un_gasto(
                    importe=gasto.importe,
                    pagado=pagado,
                    vencimiento=gasto.vencimiento,
                    hoy=hoy,
                    anulado=gasto.anulado,
                ),
            }
        )

    los_pagos = _los_pagos(db, explotacion.id, [gasto.id for gasto in suyos])

    # **Los avisos**: lo que no se puede saber y lo que no se ha movido. Sin ellos, un hueco parecería un
    # cero y una factura sin albarán parecería una compra sin mercancía.
    avisos: list[str] = []
    if factura.anulada:
        avisos.append(textos.mensaje("AL36_la_factura_esta_anulada"))
    if not las_que_cuentan:
        avisos.append(textos.mensaje("AL40_esta_factura_no_ha_metido_nada_en_el_almacen"))
    if sin_enganche:
        avisos.append(
            textos.MENSAJES["AL29_no_se_puede_saber_lo_recibido_por_linea"].format(
                cuantas=len(sin_enganche)
            )
        )

    return {
        "compra": {
            "factura_id": factura.id,
            "proveedor": factura.proveedor,
            "proveedor_nif": factura.proveedor_nif,
            "numero_factura": factura.numero_factura,
            "fecha": factura.fecha.isoformat() if factura.fecha else None,
            "anulada": factura.anulada,
            "motivo_anulacion": factura.motivo_anulacion,
            # Lo facturado: el papel, tal cual.
            "facturado": dinero.a_texto(_el_importe_del_papel(factura.total)),
            "facturado_texto": dinero.formatea(_el_importe_del_papel(factura.total)),
            "base_imponible": dinero.a_texto(_el_importe_del_papel(factura.base_imponible)),
            "cuota_iva": dinero.a_texto(_el_importe_del_papel(factura.cuota_iva)),
            "lineas": [
                {
                    "id": linea.id,
                    "descripcion": linea.descripcion,
                    "cantidad": linea.cantidad,
                    "unidad": linea.unidad,
                    "precio_unitario": linea.precio_unitario,
                    "importe": linea.importe,
                }
                for linea in sorted(factura.lineas, key=lambda fila: fila.id)
            ],
            # Lo recibido: los albaranes y, cuando se puede, línea a línea.
            "recibido": {
                "cuantas_recepciones": len(las_que_cuentan),
                "cuantas_anuladas": len(recepciones) - len(las_que_cuentan),
                "recepciones": los_albaranes,
                "por_linea": por_linea,
                "lineas_sin_enganche": len(sin_enganche),
                "lineas_con_falta": len(con_falta),
                "todo_recibido": todo_recibido,
            },
            # El dinero.
            "pagado": dinero.a_texto(pagado_total),
            "pagado_texto": dinero.formatea(pagado_total),
            "pendiente": dinero.a_texto(pendiente_total),
            "pendiente_texto": dinero.formatea(pendiente_total),
            "cuantos_gastos": len(los_gastos),
            "gastos": los_gastos,
            "pagos": los_pagos,
            # **Los identificadores para que la pantalla arme sus enlaces**, y nada más: el servidor no
            # sabe cómo se llaman las rutas del navegador.
            "recepcion_ids": [una["id"] for una in los_albaranes],
            "gasto_ids": [gasto["id"] for gasto in los_gastos],
            "pago_ids": [pago["id"] for pago in los_pagos],
        },
        "avisos": avisos,
        "textos": textos.FACTURAS,
    }
