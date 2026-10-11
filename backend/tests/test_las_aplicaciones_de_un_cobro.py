"""Un cobro repartido entre varias deudas (CRM-01, 11/10/2026).

**Por qué este fichero.** El encargo de CRM-01 pide tres cifras concretas, y las tres se comprueban aquí
**sumando las aplicaciones** y no mirando un total global, que es lo que puede tapar un error:

  · un cobro de **350** aplicado a dos deudas de **100** y **250**: las aplicaciones suman **350** y el saldo
    sin aplicar queda en **0**;
  · un cobro de **400** del que solo se aplican **350**: quedan **50 sin asignar**, sin que se pierda el pago
    ni se cuente como un ingreso nuevo;
  · la venta de **1210** con **400** y luego **810**: pendiente **810 → 0**.

Y las dos invariantes que documentan las referencias que estudió el ticket (ERPNext *Payment Entry*: «the
total allocated amount can be less than or equal to the payment, but it cannot exceed the available
amount»): **no se reparte más de lo que entró** y **a una factura no se le aplica más de lo que debe**.
"""

from __future__ import annotations

from decimal import Decimal


def _una_entrega(cliente, cuenta, campana, importe: str, producto: str = "Trigo blando") -> dict:
    respuesta = cliente.post(
        "/api/ventas",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": producto,
            "cantidad": 1000.0,
            "unidad": "kg",
            "importe": importe,
            "comprador": "Cooperativa Agrícola de Peñaranda",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _una_factura(cliente, cuenta, entrega: dict, numero: str) -> dict:
    respuesta = cliente.post(
        "/api/facturas-emitidas",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-07-20",
            "numero": numero,
            "cliente": "Cooperativa Agrícola de Peñaranda",
            "entregas": [entrega["id"]],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _una_factura_de(cliente, cuenta, campana, importe: str, numero: str) -> dict:
    return _una_factura(cliente, cuenta, _una_entrega(cliente, cuenta, campana, importe), numero)


def _la_factura(cliente, cuenta, factura_id: int) -> dict:
    respuesta = cliente.get(f"/api/facturas-emitidas/{factura_id}", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _el_cobro(cliente, cuenta, cuerpo: dict):
    return cliente.post("/api/cobros", headers=cuenta["cabeceras"], json=cuerpo)


def _suma(aplicaciones: list[dict]) -> Decimal:
    return sum((Decimal(a["importe"]) for a in aplicaciones), Decimal("0"))


def test_un_cobro_de_350_repartido_entre_dos_deudas_de_100_y_250(cliente, cuenta, campana):
    """**La cifra del encargo**: dos deudas de 100 y 250 saldadas con un solo ingreso de 350.

    Es lo que no se podía hacer con una sola factura en el cobro, y por lo que existe la tabla de
    aplicaciones. Se comprueba **por identificador**, factura a factura, y sumando las filas.
    """
    la_de_100 = _una_factura_de(cliente, cuenta, campana, "100.00", "CRM01-APL-1")
    la_de_250 = _una_factura_de(cliente, cuenta, campana, "250.00", "CRM01-APL-2")

    respuesta = _el_cobro(
        cliente,
        cuenta,
        {
            "fecha": "2026-08-01",
            "importe": "350.00",
            "aplicaciones": [
                {"factura_emitida_id": la_de_100["id"], "importe": "100.00"},
                {"factura_emitida_id": la_de_250["id"], "importe": "250.00"},
            ],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    suyas = cuerpo["cobro"]["aplicaciones"]
    assert len(suyas) == 2, f"el reparto tiene que tener dos filas: {suyas}"
    assert _suma(suyas) == Decimal("350.00"), f"las aplicaciones suman 350: {suyas}"
    assert cuerpo["cobro"]["texto_sin_asignar"] == "", (
        f"y no queda nada sin asignar: {cuerpo['cobro']['texto_sin_asignar']!r}"
    )
    # Por identificador: las dos deudas quedan saldadas.
    assert _la_factura(cliente, cuenta, la_de_100["id"])["pendiente"] == "0.00"
    assert _la_factura(cliente, cuenta, la_de_250["id"])["pendiente"] == "0.00"


def test_un_cobro_de_400_con_350_aplicado_deja_50_sin_asignar(cliente, cuenta, campana):
    """El sobrante es un dato, no dinero perdido: 400 que entran, 350 aplicados, 50 sin asignar."""
    la_factura = _una_factura_de(cliente, cuenta, campana, "350.00", "CRM01-APL-3")

    respuesta = _el_cobro(
        cliente,
        cuenta,
        {
            "fecha": "2026-08-01",
            "importe": "400.00",
            "aplicaciones": [
                {"factura_emitida_id": la_factura["id"], "importe": "350.00"},
            ],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["cobro"]["importe"] == "400.00", "el cobro se apunta entero"
    assert cuerpo["cobro"]["texto_sin_asignar"] == "50,00 €", (
        f"y lo que no se aplica se dice: {cuerpo['cobro']['texto_sin_asignar']!r}"
    )
    assert _la_factura(cliente, cuenta, la_factura["id"])["pendiente"] == "0.00"
    # Y no ha aparecido ninguna factura nueva: cobrar no emite documentos.
    assert len(cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json()) == 1


def test_la_venta_de_1210_cobrada_en_dos_veces_queda_a_cero(cliente, cuenta, campana):
    """La primera cifra del encargo, por identificador: 1210 → cobro 400 → pendiente 810 → cobro 810 → 0."""
    la_factura = _una_factura_de(cliente, cuenta, campana, "1210.00", "CRM01-APL-4")

    primero = _el_cobro(
        cliente, cuenta, {"fecha": "2026-08-01", "importe": "400.00", "factura_emitida_id": la_factura["id"]}
    )
    assert primero.status_code == 201, primero.text
    assert primero.json()["factura"]["pendiente"] == "810.00"

    segundo = _el_cobro(
        cliente, cuenta, {"fecha": "2026-08-20", "importe": "810.00", "factura_emitida_id": la_factura["id"]}
    )
    assert segundo.status_code == 201, segundo.text
    assert segundo.json()["factura"]["pendiente"] == "0.00"
    assert _la_factura(cliente, cuenta, la_factura["id"])["estado"] == "cobrada"


def test_no_se_puede_repartir_mas_de_lo_que_entro(cliente, cuenta, campana):
    """La invariante de la referencia, con palabras: «no se puede repartir más de lo que entró»."""
    una = _una_factura_de(cliente, cuenta, campana, "200.00", "CRM01-APL-5")
    otra = _una_factura_de(cliente, cuenta, campana, "200.00", "CRM01-APL-6")

    respuesta = _el_cobro(
        cliente,
        cuenta,
        {
            "fecha": "2026-08-01",
            "importe": "350.00",
            "aplicaciones": [
                {"factura_emitida_id": una["id"], "importe": "200.00"},
                {"factura_emitida_id": otra["id"], "importe": "200.00"},
            ],
        },
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "no se puede repartir más de lo que entró" in respuesta.text
    # Y no se ha apuntado nada a medias: el cobro no existe.
    assert cliente.get("/api/cobros", headers=cuenta["cabeceras"]).json() == []


def test_a_una_factura_no_se_le_aplica_mas_de_lo_que_debe(cliente, cuenta, campana):
    """La otra invariante: a una deuda de 100 no se le pueden aplicar 150."""
    la_factura = _una_factura_de(cliente, cuenta, campana, "100.00", "CRM01-APL-7")

    respuesta = _el_cobro(
        cliente,
        cuenta,
        {
            "fecha": "2026-08-01",
            "importe": "150.00",
            "aplicaciones": [{"factura_emitida_id": la_factura["id"], "importe": "150.00"}],
        },
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "solo le quedan" in respuesta.text
    assert cliente.get("/api/cobros", headers=cuenta["cabeceras"]).json() == []


def test_una_factura_suelta_y_un_reparto_a_la_vez_no_se_admiten(cliente, cuenta, campana):
    """O una factura, o el reparto: las dos cosas a la vez no, y se dice por qué en vez de elegir solo."""
    la_factura = _una_factura_de(cliente, cuenta, campana, "100.00", "CRM01-APL-8")

    respuesta = _el_cobro(
        cliente,
        cuenta,
        {
            "fecha": "2026-08-01",
            "importe": "100.00",
            "factura_emitida_id": la_factura["id"],
            "aplicaciones": [{"factura_emitida_id": la_factura["id"], "importe": "100.00"}],
        },
    )
    assert respuesta.status_code == 422, respuesta.text


def test_anular_el_cobro_devuelve_las_dos_deudas(cliente, cuenta, campana):
    """Deshacer **desvincula y no borra**: las dos deudas vuelven a estar pendientes y el cobro sigue ahí.

    Es lo que las dos referencias documentan como *unreconcile* («it does not erase the original vouchers»),
    y aquí se exige con las dos facturas del reparto, no con una.
    """
    una = _una_factura_de(cliente, cuenta, campana, "100.00", "CRM01-APL-9")
    otra = _una_factura_de(cliente, cuenta, campana, "250.00", "CRM01-APL-10")
    creado = _el_cobro(
        cliente,
        cuenta,
        {
            "fecha": "2026-08-01",
            "importe": "350.00",
            "aplicaciones": [
                {"factura_emitida_id": una["id"], "importe": "100.00"},
                {"factura_emitida_id": otra["id"], "importe": "250.00"},
            ],
        },
    ).json()

    anulado = cliente.post(
        f"/api/cobros/{creado['cobro']['id']}/anular",
        headers=cuenta["cabeceras"],
        json={"motivo": "me equivoqué de cliente"},
    )
    assert anulado.status_code == 200, anulado.text
    assert _la_factura(cliente, cuenta, una["id"])["pendiente"] == "100.00"
    assert _la_factura(cliente, cuenta, otra["id"])["pendiente"] == "250.00"
    # Y el cobro **no se ha borrado**: deja de contar —la lista solo enseña los vivos— y su rastro queda en
    # la auditoría con el motivo. Lo que se exige aquí es lo de arriba: las dos deudas vuelven a estar
    # pendientes, que es lo que significa deshacer una conciliación.
    assert cliente.get("/api/cobros", headers=cuenta["cabeceras"]).json() == [], (
        "un cobro anulado no puede seguir contando en la lista de lo que ha entrado"
    )


def test_no_se_puede_aplicar_un_cobro_a_una_factura_de_otra_finca(cliente, cuenta, crear_cuenta, campana):
    """El aislamiento: la factura de otra explotación no existe para esta, y se contesta 404.

    Se prueba con la factura de **esta** finca y el cobro de **la otra**: es el caso que el aislamiento
    tiene que cortar (y 404, no 403: no se filtra ni que exista).
    """
    la_mia = _una_factura_de(cliente, cuenta, campana, "100.00", "CRM01-APL-11")
    la_ajena = crear_cuenta("otro@ejemplo.test", nombre="Otro agricultor", nif="12345678Z")

    respuesta = cliente.post(
        "/api/cobros",
        headers=la_ajena["cabeceras"],
        json={
            "fecha": "2026-08-01",
            "importe": "100.00",
            "aplicaciones": [{"factura_emitida_id": la_mia["id"], "importe": "100.00"}],
        },
    )
    assert respuesta.status_code == 404, respuesta.text
    # Y la factura de esta finca sigue pendiente: el intento no ha dejado rastro en el dinero.
    assert _la_factura(cliente, cuenta, la_mia["id"])["pendiente"] == "100.00"
