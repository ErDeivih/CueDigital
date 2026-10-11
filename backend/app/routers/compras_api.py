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
from sqlalchemy import or_, select

from .. import dinero, gastos, models, servicios, textos
from ..deps import Db, ExplotacionActual, obtener_de_la_explotacion

router = APIRouter(prefix="/api/compras", tags=["compras"])


def _las_recepciones(db, explotacion_id: int, factura_id: int) -> list[models.Recepcion]:
    """Los albaranes de esta compra, **incluidos los anulados**.

    Los anulados se devuelven a propósito, y marcados: si el agricultor anuló un albarán de esta compra,
    tiene que poder verlo en la ficha —si no, parecería que nunca existió— y saber que **no cuenta**, que
    es lo que dice su campo `anulada`.

    **Y se reconocen por los dos caminos** (09/10/2026, lo cazó el revisor): por la cabecera
    (`Recepcion.factura_id`, que es como se engancha desde la ficha del albarán) y **por la línea**
    (`LineaDeRecepcion.linea_factura_id`, que es el enganche fino, el que dice qué línea del albarán es
    qué línea de la factura). Antes solo se miraba la cabecera, así que un albarán enganchado **solo**
    por línea no aparecía: la ficha decía «no ha entrado nada» y «no se puede saber» de algo que sí sabía.
    """
    por_linea = list(
        db.scalars(
            select(models.LineaDeRecepcion.recepcion_id)
            .join(models.LineaDeFactura, models.LineaDeFactura.id == models.LineaDeRecepcion.linea_factura_id)
            .where(
                models.LineaDeRecepcion.explotacion_id == explotacion_id,
                models.LineaDeFactura.factura_id == factura_id,
            )
        )
    )
    return list(
        db.scalars(
            select(models.Recepcion)
            .where(
                models.Recepcion.explotacion_id == explotacion_id,
                or_(
                    models.Recepcion.factura_id == factura_id,
                    models.Recepcion.id.in_(por_linea) if por_linea else False,
                ),
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
            # **La línea tiene que ser de ESTA factura**, y se sabe por su enganche fino, no por la
            # cabecera del albarán (09/10/2026): exigir `Recepcion.factura_id` dejaba fuera los albaranes
            # enganchados solo por línea, que son justo los que hacen que esta pantalla sepa más.
            .join(
                models.LineaDeFactura,
                models.LineaDeFactura.id == models.LineaDeRecepcion.linea_factura_id,
            )
            .where(
                models.LineaDeRecepcion.explotacion_id == explotacion_id,
                models.Recepcion.anulada.is_(False),
                models.LineaDeFactura.factura_id == factura.id,
                models.LineaDeRecepcion.linea_factura_id.is_not(None),
            )
        )
    )
    recibido: dict[int, list[tuple[float, str]]] = {}
    for linea in enganchadas:
        if linea.cantidad is None:
            continue
        # **Con su unidad**, porque para restar hay que saber si se puede: 500 kg menos 300 L no son 200
        # de nada (09/10/2026, lo cazó el revisor: esto restaba unidades distintas y decía «faltan 200 kg»
        # de una línea que venía en litros).
        recibido.setdefault(linea.linea_factura_id, []).append(
            (float(linea.cantidad), (linea.unidad or "").strip())
        )

    salida = []
    for linea in sorted(factura.lineas, key=lambda fila: fila.id):
        suyas = recibido.get(linea.id)
        facturado = linea.cantidad
        la_unidad = (linea.unidad or "").strip()
        if suyas is None:
            suyo = None
        elif any(not servicios.se_pueden_sumar(la_unidad, unidad) for _cantidad, unidad in suyas):
            # Llegó, pero en una unidad que **no se puede comparar** con la de la factura: entonces la
            # cantidad recibida **no se puede decir que sea** la de la factura. Se declara «no se sabe» en
            # vez de restar peras con manzanas; lo que sí llegó se ve en `por_unidad`, que no mezcla.
            suyo = None
        else:
            suyo = sum(cantidad for cantidad, _unidad in suyas)
        falta = None
        if suyo is not None and facturado is not None:
            falta = float(facturado) - suyo
        salida.append(
            {
                "linea_factura_id": linea.id,
                "descripcion": linea.descripcion,
                "unidad": linea.unidad,
                "facturado": facturado,
                "recibido": suyo,
                "falta": falta,
                # Y **lo que llegó de esta línea aunque no se pueda comparar**, para que el agricultor vea
                # que sí entró algo y en qué unidad: sin esto, «no se puede saber» parecería «no llegó».
                "recibido_de_otros_modos": [
                    {"cantidad": cantidad, "unidad": unidad} for cantidad, unidad in (suyas or [])
                ]
                if suyo is None
                else [],
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


def _lo_que_ha_entrado_por_unidad(los_albaranes: list[dict]) -> dict[str, float]:
    """Cuánto ha entrado de esta compra **por unidad**, contando solo los albaranes que cuentan.

    Se devuelve un diccionario `{unidad: cantidad}` y no un solo número porque **dos unidades no se
    suman**: 300 kg y 20 L no son 320 de nada. Es la misma regla que aplica el almacén al libro
    (`servicios.se_pueden_sumar`), vista desde la ficha.
    """
    por_unidad: dict[str, float] = {}
    for albaran in los_albaranes:
        if albaran.get("anulada"):
            continue
        for unidad, cantidad in (albaran.get("cantidad_por_unidad") or {}).items():
            por_unidad[unidad] = por_unidad.get(unidad, 0.0) + cantidad
    return por_unidad


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
    # **Lo que no se sabe, contado** (09/10/2026, lo cazó el revisor): un gasto sin importe —el modelo lo
    # permite y la API lo acepta— deja su pendiente en `None`, y sumar «nada» no es sumar cero. Antes esa
    # compra enseñaba **Pendiente 0,00 €** mientras su propia fila decía «Pendiente: —»: la pantalla
    # afirmaba un cero que no sabía. Ahora, si falta un dato, el total **no se sabe** y se dice.
    cuantos_sin_saber = 0
    anulados = 0
    for gasto in suyos:
        # **Un gasto anulado no es una deuda** (09/10/2026, lo cazó el revisor): la pantalla de gastos lo
        # deja fuera de «por pagar» y esta ficha lo estaba sumando, así que el mismo dinero salía con dos
        # cifras en dos pantallas. Se cuenta aparte y se dice, en vez de sumarlo o de esconderlo.
        if gasto.anulado:
            anulados += 1
            continue
        pagado = servicios.lo_pagado_de_un_gasto(
            db, explotacion_id=explotacion.id, gasto_id=gasto.id
        )
        pendiente = gastos.pendiente_de(gasto.importe, pagado)
        pagado_total = dinero.suma(pagado_total, pagado)
        if pendiente is None:
            cuantos_sin_saber += 1
        else:
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

    los_pagos = _los_pagos(db, explotacion.id, [gasto["id"] for gasto in los_gastos])

    # **Y si los gastos no cuadran con lo que dice la factura, se dice** (09/10/2026, lo cazó el revisor).
    # No es un error del programa: el agricultor apunta primero la factura y el gasto después, y a veces
    # con otro número. Pero si el papel dice 663 y los gastos suman 100, el «pendiente» de esta compra
    # (100) no es el de la factura, y callarlo deja al agricultor creyendo que le quedan 100 € por pagar
    # de una compra de 663. Es la mitad financiera de la regla del «no lo sé»: se dice lo que no cuadra.
    lo_facturado = _el_importe_del_papel(factura.total)
    lo_gastado = dinero.suma(
        *[_el_importe_del_papel(fila["importe"]) for fila in los_gastos]
    )
    if (
        lo_facturado is not None
        and los_gastos
        and not cuantos_sin_saber
        and abs(lo_gastado - lo_facturado) >= 0.005
    ):
        avisos_del_cuadre = textos.MENSAJES["AL41_los_gastos_no_cuadran_con_la_factura"].format(
            facturado=dinero.formatea(lo_facturado), gastado=dinero.formatea(lo_gastado)
        )
    else:
        avisos_del_cuadre = ""

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
    if cuantos_sin_saber:
        avisos.append(
            textos.MENSAJES["AL42_hay_gastos_sin_importe"].format(cuantos=cuantos_sin_saber)
        )
    if anulados:
        avisos.append(textos.MENSAJES["AL43_hay_gastos_anulados"].format(cuantos=anulados))
    if avisos_del_cuadre:
        avisos.append(avisos_del_cuadre)

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
                # **El total que ha entrado, por unidad**, y solo de los albaranes que cuentan. Se suma
                # aquí, con la unidad delante, a propósito: sumar dos unidades distintas no se puede, y
                # sumar en el navegador (donde todo número es de coma flotante) es justo lo que el
                # programa no hace.
                "por_unidad": _lo_que_ha_entrado_por_unidad(los_albaranes),
                "por_linea": por_linea,
                "lineas_sin_enganche": len(sin_enganche),
                "lineas_con_falta": len(con_falta),
                "todo_recibido": todo_recibido,
            },
            # El dinero. **`pendiente` sale `None` —«no se sabe»— si algún gasto no tiene importe**:
            # un total al que le faltan sumandos no es un total, y enseñarlo como 0,00 sería afirmar
            # que no queda nada por pagar.
            "pagado": dinero.a_texto(pagado_total),
            "pagado_texto": dinero.formatea(pagado_total),
            "pendiente": None if cuantos_sin_saber else dinero.a_texto(pendiente_total),
            "pendiente_texto": "" if cuantos_sin_saber else dinero.formatea(pendiente_total),
            "cuantos_gastos": len(los_gastos),
            "cuantos_gastos_sin_importe": cuantos_sin_saber,
            "cuantos_gastos_anulados": anulados,
            "gastos": los_gastos,
            "pagos": los_pagos,
            # **Los identificadores para que la pantalla arme sus enlaces**, y nada más: el servidor no
            # sabe cómo se llaman las rutas del navegador.
            "recepcion_ids": [una["id"] for una in los_albaranes],
            "gasto_ids": [gasto["id"] for gasto in los_gastos],
            "pago_ids": [pago["id"] for pago in los_pagos],
        },
        "avisos": avisos,
        # **`textos.COMPRA`, y no `textos.FACTURAS`** (09/10/2026). Aquí estaba el defecto más gordo que
        # encontró el revisor de pantallas: la ficha pedía de este bloque ocho frases —«Los albaranes de
        # esta compra», «El dinero de esta compra», los dos botones de enlace…— que **solo existen en
        # `COMPRA`**, así que llegaban vacías: **dos botones en blanco de 1059 px** y dos títulos sin
        # texto, medidos en Chrome. Y las pruebas no lo veían porque la de JavaScript usa un juego de
        # textos escrito a mano. Ahora hay una prueba que **cruza** lo que el componente pide con lo que
        # esta puerta sirve (ver `tests/test_la_ficha_de_la_compra.py`).
        "textos": textos.COMPRA,
    }
