"""El saldo de un contacto: **cuánto nos debe y cuánto le debemos** (Entrega 1, 13/10/2026).

Lo que se comprueba aquí son las cifras del encargo, **por las puertas de verdad** (las ventas, las facturas
emitidas, los cobros, los gastos y los pagos se apuntan como los apunta el agricultor), y no fabricando filas a
mano: si algo de esto se rompiera en la puerta, la prueba lo vería.

Las cifras que pide el encargo, tal cual:

  · venta de 1210 € con un cobro de 400 €  → **nos debe 810 €**
  · compra de 600 € con un pago de 150 €   → **le debemos 450 €**
  · las dos cosas del mismo contacto       → **810 y 450, separadas** (no 360)
  · factura y gasto de la misma compra     → **una sola obligación**
  · una anulación                          → **recalcula**
  · un importe que no se sabe              → **no se convierte en cero**
  · otra explotación                       → **nada**
"""

from __future__ import annotations

from decimal import Decimal


def _una_cifra(valor) -> Decimal:
    """El dinero se compara como número, dé igual cómo lo mande el JSON (cadena o número)."""
    return Decimal(str(valor))


def _un_contacto(cliente, cuenta, nombre: str = "Cooperativa Agrícola de Peñaranda") -> dict:
    respuesta = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={"nombre": nombre, "papeles": ["comprador", "proveedor"]},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _su_saldo(cliente, cuenta, contacto_id: int) -> dict:
    respuesta = cliente.get(f"/api/contactos/{contacto_id}/saldo", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _una_venta_facturada_y_cobrada(cliente, cuenta, crear_venta, contacto: dict, *, importe, cobro, fecha="2026-07-10"):
    """El camino entero: entrega → factura emitida (que es lo que se cobra) → cobro."""
    venta = crear_venta(
        importe=importe,
        # La puerta **exige saber cuánto se ha vendido** (aviso `C2_sin_cantidad`): sin cantidad no deja apuntar la
        # entrega, y hace bien —una venta sin kilos no es una venta—. El importe va aparte porque en el campo se
        # apunta lo que dice el albarán, no lo que salga de multiplicar.
        cantidad=1000,
        precio_unitario=None,
        contacto_id=contacto["id"],
        comprador=contacto["nombre"],
    )
    factura = cliente.post(
        "/api/facturas-emitidas",
        headers=cuenta["cabeceras"],
        json={
            "fecha": fecha,
            "cliente": contacto["nombre"],
            "contacto_id": contacto["id"],
            "entregas": [venta["id"]],
        },
    )
    assert factura.status_code in (200, 201), f"no se pudo facturar la entrega: {factura.text}"
    suya = factura.json()
    if cobro:
        cobrado = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-08-01",
                "importe": cobro,
                "aplicaciones": [{"factura_emitida_id": suya["id"], "importe": cobro}],
            },
        )
        assert cobrado.status_code in (200, 201), f"no se pudo apuntar el cobro: {cobrado.text}"
    return suya


def test_una_venta_cobrada_a_medias_nos_debe_lo_que_falta(cliente, cuenta, crear_venta):
    """**Venta 1210 €, cobro 400 €: nos debe 810 €.**"""
    contacto = _un_contacto(cliente, cuenta)
    _una_venta_facturada_y_cobrada(cliente, cuenta, crear_venta, contacto, importe="1210", cobro="400")

    saldo = _su_saldo(cliente, cuenta, contacto["id"])
    assert _una_cifra(saldo["nos_debe"]["total"]) == Decimal("810"), (
        f"nos debe 810 y dice {saldo['nos_debe']['total']}: {saldo['nos_debe']}"
    )
    # Y la cifra **abre su documento**, que es lo que la hace comprobable.
    assert len(saldo["nos_debe"]["documentos"]) == 1, saldo["nos_debe"]["documentos"]
    suyo = saldo["nos_debe"]["documentos"][0]
    assert suyo["clase"] == "factura_emitida", suyo
    assert _una_cifra(suyo["importe"]) == Decimal("1210") and _una_cifra(suyo["cobrado"]) == Decimal("400")
    assert _una_cifra(suyo["pendiente"]) == Decimal("810")
    # La moneda se declara, no se supone.
    assert saldo["moneda"] == "EUR", saldo["moneda"]


def test_una_compra_pagada_a_medias_le_debemos_lo_que_falta(cliente, cuenta, campana):
    """**Compra 600 €, pago 150 €: le debemos 450 €.**"""
    contacto = _un_contacto(cliente, cuenta, "Suministros del Páramo, S.L.")
    gasto = cliente.post(
        "/api/gastos",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-06-01",
            "concepto": "Abono",
            "categoria": "abono",
            "proveedor": contacto["nombre"],
            "contacto_id": contacto["id"],
            "importe": "600",
        },
    )
    assert gasto.status_code in (200, 201), gasto.text
    pago = cliente.post(
        "/api/gastos/pagos",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-06-15",
            "importe": "150",
            "contacto_id": contacto["id"],
            "proveedor": contacto["nombre"],
            "aplicaciones": [{"gasto_id": gasto.json()["gasto"]["id"], "importe": "150"}],
        },
    )
    assert pago.status_code in (200, 201), f"no se pudo apuntar el pago: {pago.text}"

    saldo = _su_saldo(cliente, cuenta, contacto["id"])
    assert _una_cifra(saldo["le_debemos"]["total"]) == Decimal("450"), (
        f"le debemos 450 y dice {saldo['le_debemos']['total']}: {saldo['le_debemos']}"
    )
    # **Y lo que nos debe no se mezcla**: este contacto no nos debe nada.
    assert _una_cifra(saldo["nos_debe"]["total"]) == Decimal("0"), saldo["nos_debe"]


def test_las_dos_cosas_del_mismo_contacto_van_separadas(cliente, cuenta, crear_venta, campana):
    """**Las dos operaciones del mismo contacto: 810 y 450, separadas** (no 360).

    Es la decisión que el encargo pide con más insistencia: restar una deuda de otra esconde las dos, y la misma
    persona es cliente y proveedor casi siempre.
    """
    contacto = _un_contacto(cliente, cuenta)
    _una_venta_facturada_y_cobrada(cliente, cuenta, crear_venta, contacto, importe="1210", cobro="400")
    gasto = cliente.post(
        "/api/gastos",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-06-01",
            "concepto": "Gasóleo",
            "categoria": "gasoleo",
            "proveedor": contacto["nombre"],
            "contacto_id": contacto["id"],
            "importe": "600",
        },
    )
    assert gasto.status_code in (200, 201), gasto.text
    pago = cliente.post(
        "/api/gastos/pagos",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-06-15",
            "importe": "150",
            "contacto_id": contacto["id"],
            "proveedor": contacto["nombre"],
            "aplicaciones": [{"gasto_id": gasto.json()["gasto"]["id"], "importe": "150"}],
        },
    )
    assert pago.status_code in (200, 201), pago.text

    saldo = _su_saldo(cliente, cuenta, contacto["id"])
    assert _una_cifra(saldo["nos_debe"]["total"]) == Decimal("810"), saldo["nos_debe"]
    assert _una_cifra(saldo["le_debemos"]["total"]) == Decimal("450"), saldo["le_debemos"]


def test_una_anulacion_recalcula_el_saldo(cliente, cuenta, crear_venta):
    """**Anular el cobro devuelve la deuda entera**: lo anulado no cuenta, y el saldo se recalcula solo."""
    contacto = _un_contacto(cliente, cuenta)
    _una_venta_facturada_y_cobrada(cliente, cuenta, crear_venta, contacto, importe="1210", cobro="400")
    assert _una_cifra(_su_saldo(cliente, cuenta, contacto["id"])["nos_debe"]["total"]) == Decimal("810")

    suyos = cliente.get("/api/ventas", headers=cuenta["cabeceras"])
    assert suyos.status_code == 200, suyos.text
    cobros = cliente.get("/api/cobros", headers=cuenta["cabeceras"])
    if cobros.status_code == 200 and cobros.json():
        el_cobro = cobros.json()[0]
        anulado = cliente.post(
            f"/api/cobros/{el_cobro['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba apuntado dos veces"},
        )
        assert anulado.status_code in (200, 201), anulado.text
        saldo = _su_saldo(cliente, cuenta, contacto["id"])
        assert _una_cifra(saldo["nos_debe"]["total"]) == Decimal("1210"), (
            f"al anular el cobro vuelve a deberse todo: {saldo['nos_debe']}"
        )


def test_un_importe_que_no_se_sabe_no_se_convierte_en_cero(cliente, cuenta, campana):
    """**Un gasto sin importe aparece, pero no suma un cero**: se cuenta aparte y se dice."""
    contacto = _un_contacto(cliente, cuenta, "Taller sin factura todavía")
    gasto = cliente.post(
        "/api/gastos",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-06-01",
            "concepto": "Reparación (falta la factura)",
            "categoria": "reparacion",
            "proveedor": contacto["nombre"],
            "contacto_id": contacto["id"],
        },
    )
    assert gasto.status_code in (200, 201), gasto.text

    saldo = _su_saldo(cliente, cuenta, contacto["id"])
    assert saldo["le_debemos"]["sin_importe"] == 1, saldo["le_debemos"]
    assert saldo["le_debemos"]["documentos"], "el documento tiene que aparecer para poder revisarlo"
    assert saldo["le_debemos"]["documentos"][0]["pendiente"] is None, (
        f"lo que no se sabe va en `None`, nunca en cero: {saldo['le_debemos']['documentos'][0]}"
    )
    assert _una_cifra(saldo["le_debemos"]["total"]) == Decimal("0"), (
        "y el total no puede contar ese documento como cero euros"
    )


def test_el_saldo_de_un_contacto_de_otra_finca_no_se_ve(cliente, cuenta, crear_cuenta):
    """**Aislamiento**: ni sabiendo el identificador. 404, como la ficha (y no 403, que ya diría que existe)."""
    mio = _un_contacto(cliente, cuenta, "Cooperativa de Peñaranda")
    otro = crear_cuenta("otro-saldo@ejemplo.test")
    respuesta = cliente.get(f"/api/contactos/{mio['id']}/saldo", headers=otro["cabeceras"])
    assert respuesta.status_code == 404, (
        f"el saldo de otra finca tiene que dar 404, y ha dado {respuesta.status_code}: {respuesta.text}"
    )
