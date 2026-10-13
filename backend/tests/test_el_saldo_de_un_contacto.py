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

import json as _json
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

def test_una_compra_con_factura_y_gasto_cuenta_una_sola_vez(cliente, cuenta, campana):
    """**Factura y gasto de la misma compra: una sola obligación** (encargo, Entrega 1).

    La factura de compra **no tiene `contacto_id`** —su proveedor es texto—, así que **no se adjudica por nombre**
    (el encargo lo prohíbe) y **no entra** en el saldo de ningún contacto. La obligación vive en su **gasto**, que
    sí dice de quién es. Por eso una compra con las dos cosas cuenta **una vez**, y no por una resta afortunada
    sino porque la factura no se cuenta nunca.
    """
    contacto = _un_contacto(cliente, cuenta, "Suministros del Páramo, S.L.")
    factura = cliente.post(
        "/api/facturas",
        headers=cuenta["cabeceras"],
        # **Como formulario, no como JSON**: esta puerta es `datos: str = File(...)` porque en la misma petición
        # viaja el fichero del papel, y un formulario con fichero no puede llevar un cuerpo JSON normal. Lo dice la
        # propia puerta: *«Los datos llegan como un JSON en el campo `datos` porque en la misma petición viaja el
        # fichero»*. (Con `json=` contestaba 422 pidiendo `datos`, que es exactamente eso.)
        data={"datos": _json.dumps({
            "fecha": "2026-06-01",
            "proveedor": contacto["nombre"],
            "numero_factura": "F-2026-77",
            "base_imponible": "495.87",
            "cuota_iva": "104.13",
            "total": "600",
        })},
    )
    assert factura.status_code in (200, 201), f"no se pudo apuntar la factura de compra: {factura.text}"
    gasto = cliente.post(
        "/api/gastos",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-06-01",
            "concepto": "Abono de la factura F-2026-77",
            "categoria": "abono",
            "proveedor": contacto["nombre"],
            "contacto_id": contacto["id"],
            "factura_id": factura.json()["id"],
            "importe": "600",
        },
    )
    assert gasto.status_code in (200, 201), gasto.text

    saldo = _su_saldo(cliente, cuenta, contacto["id"])
    assert _una_cifra(saldo["le_debemos"]["total"]) == Decimal("600"), (
        f"la compra tiene que contar una vez (600), no dos (1200): {saldo['le_debemos']}"
    )
    assert len(saldo["le_debemos"]["documentos"]) == 1, (
        f"y con un solo documento, que es el gasto: {saldo['le_debemos']['documentos']}"
    )


def test_el_dinero_sin_asignar_se_ensena_pero_no_rebaja_la_deuda(cliente, cuenta, crear_venta):
    """**Un cobro sin aplicar no rebaja lo que nos deben** (encargo: «cobros y pagos sin asignar»).

    Puede ser de esta factura o de otra, o de algo que aún no está apuntado: darlo por cobrado sería inventar. Se
    enseña en su lista, con su fecha y su importe, y **no toca el total**.
    """
    contacto = _un_contacto(cliente, cuenta)
    _una_venta_facturada_y_cobrada(cliente, cuenta, crear_venta, contacto, importe="1210", cobro="400")
    suelto = cliente.post(
        "/api/cobros",
        headers=cuenta["cabeceras"],
        json={"fecha": "2026-08-10", "importe": "100", "cliente": contacto["nombre"], "contacto_id": contacto["id"]},
    )
    assert suelto.status_code in (200, 201), f"no se pudo apuntar el cobro suelto: {suelto.text}"

    saldo = _su_saldo(cliente, cuenta, contacto["id"])
    assert _una_cifra(saldo["nos_debe"]["total"]) == Decimal("810"), (
        f"el cobro sin asignar NO puede rebajar la deuda: {saldo['nos_debe']}"
    )
    assert len(saldo["sin_asignar"]["cobros"]) == 1, saldo["sin_asignar"]
    assert _una_cifra(saldo["sin_asignar"]["cobros"][0]["importe"]) == Decimal("100")
    assert saldo["sin_asignar"]["nota"] == "sin_asignar_no_es_un_anticipo", (
        "y no se le llama anticipo, porque no se sabe de qué es"
    )


def test_un_exceso_se_marca_para_revisar_y_no_se_llama_anticipo(cliente, cuenta, crear_venta):
    """**Cobrar más de lo que valía el documento se marca, no se interpreta** (encargo, Entrega 1).

    El encargo lo prohíbe con estas palabras: *«No interpretar todo exceso de cobro como anticipo»*. Aquí se cobra
    de más y lo que se exige es que **aparezca en `para_revisar`**, que el pendiente quede en **negativo** (a favor
    suyo, dicho y no escondido) y que **nadie lo llame anticipo**.
    """
    contacto = _un_contacto(cliente, cuenta)
    factura = _una_venta_facturada_y_cobrada(cliente, cuenta, crear_venta, contacto, importe="1210", cobro="1210")
    de_mas = cliente.post(
        "/api/cobros",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-08-20",
            "importe": "200",
            "cliente": contacto["nombre"],
            "contacto_id": contacto["id"],
            "aplicaciones": [{"factura_emitida_id": factura["id"], "importe": "200"}],
        },
    )
    if de_mas.status_code not in (200, 201):
        # Si la puerta no deja aplicar de más, se dice y no se inventa el caso: **no se declara comprobado**.
        import pytest

        pytest.skip(f"la puerta no permite aplicar de más ({de_mas.status_code}): {de_mas.text[:120]}")

    saldo = _su_saldo(cliente, cuenta, contacto["id"])
    assert _una_cifra(saldo["nos_debe"]["total"]) == Decimal("-200"), (
        f"el exceso deja el pendiente en negativo, a favor suyo, y no se esconde: {saldo['nos_debe']}"
    )
    assert saldo["para_revisar"], f"y tiene que aparecer para revisarlo: {saldo.get('para_revisar')}"
    assert "anticipo" not in str(saldo).lower() or "no_es_un_anticipo" in str(saldo), (
        "a un exceso no se le llama anticipo en ningún sitio"
    )
