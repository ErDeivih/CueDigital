"""La ficha de una compra: **facturado, recibido, pagado y pendiente**, y lo que no se puede saber.

**Por qué existe.** El encargo lo pide con estas palabras: *que la ficha de la compra enseñe lo
facturado, lo recibido, lo pagado y lo pendiente, con sus enlaces y conservando filtros y contexto*.
Hasta el 09/10/2026 esas cuatro cifras vivían en tres pantallas distintas y **nadie las juntaba**, así que
la pregunta «¿cuánto falta por llegar de esta compra?» había que contestarla recorriéndolas a mano.

Lo que se exige aquí, y por qué cada cosa:

  · **Las cuatro cifras juntas y cuadradas** con lo que dicen las otras puertas: lo facturado es el total
    de la factura, lo pagado sale de `servicios.lo_pagado_de_un_gasto` (la regla única del dinero) y el
    pendiente es lo que falta. Si la ficha dijera otra cosa que la pantalla de gastos, serían **dos
    cifras del mismo dinero**.
  · **Lo recibido se cuenta por albaranes y, cuando se puede, línea a línea** por el enganche
    `linea_factura_id`, y **solo cuenta lo que no está anulado**: un albarán anulado no metió nada.
  · **Lo que no se sabe se declara**: una línea sin enganche sale como `recibido: None` y con su aviso, en
    vez de salir como un cero que parecería una cifra. Es la regla del «no lo sé» de todo el programa.
  · **Los enlaces**: la ficha devuelve los **identificadores** de los albaranes, los gastos y los pagos,
    que es lo que la pantalla necesita para llevar a cada registro.
"""

from __future__ import annotations

import json

from app import textos


def _una_factura(cliente, cabeceras, **cambios) -> dict:
    """Una factura de compra con su línea, como la manda la pantalla."""
    cuerpo = {
        "fecha": "2026-03-15",
        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "proveedor_nif": "F37012345",
        "numero_factura": "2026/00123",
        "base_imponible": 663.0,
        "cuota_iva": 0.0,
        "tipo_iva_pct": 0.0,
        "total": 663.0,
        "leida_por": "a mano",
        "lineas": [
            {
                "descripcion": "Abono compuesto 15-15-15",
                "cantidad": 500.0,
                "unidad": "kg",
                "precio_unitario": 1.326,
                "importe": 663.0,
            }
        ],
    }
    cuerpo.update(cambios)
    respuesta = cliente.post(
        "/api/facturas", headers=cabeceras, data={"datos": json.dumps(cuerpo)}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _un_articulo(cliente, cabeceras, **cambios) -> dict:
    cuerpo = {"nombre": "Abono compuesto 15-15-15", "categoria": "abono", "unidad": "kg"}
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/almacen/articulos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _un_albaran(cliente, cabeceras, factura: dict, articulo: dict, *, cantidad: float, **cambios):
    """Un albarán enganchado **a la factura y a su línea**, que es el enganche línea a línea."""
    cuerpo = {
        "fecha": "2026-03-16",
        "proveedor": factura["proveedor"],
        "proveedor_nif": factura["proveedor_nif"],
        "numero_albaran": "A-2026-0001",
        "factura_id": factura["id"],
        "lineas": [
            {
                "articulo_id": articulo["id"],
                "nombre": articulo["nombre"],
                "unidad": "kg",
                "cantidad": cantidad,
                "linea_factura_id": factura["lineas"][0]["id"],
            }
        ],
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/almacen/recepciones", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code in (200, 201), respuesta.text
    # **La respuesta viene envuelta** (`{"recepcion": {...}, "avisos": [...]}`), medido: devolverla tal
    # cual y pedirle `["id"]` da un `KeyError` que parece un fallo del servidor y es del instrumento.
    devuelto = respuesta.json()
    return devuelto.get("recepcion") or devuelto


def _un_gasto(cliente, cabeceras, factura: dict, *, importe="663.00") -> dict:
    """La puerta de gastos es **cuerpo JSON** (`datos: GastoEntrada`), no un formulario.

    Se comprobó midiendo (09/10/2026): mandándolo como formulario contesta
    `{"loc": ["body"], "msg": "Input should be a valid dictionary or object"}`. Y los importes van como
    **texto** (`"663.00"`), que es la regla del dinero del proyecto.
    """
    respuesta = cliente.post(
        "/api/gastos",
        headers=cabeceras,
        json={
            "concepto": f"Compra de abono, factura {factura['numero_factura']}",
            "importe": importe,
            "fecha": "2026-03-15",
            "categoria": "abono",
            "factura_id": factura["id"],
        },
    )
    assert respuesta.status_code in (200, 201), respuesta.text
    devuelto = respuesta.json()
    return devuelto.get("gasto") or devuelto


def _la_ficha(cliente, cabeceras, factura_id: int) -> dict:
    respuesta = cliente.get(f"/api/compras/{factura_id}", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_la_ficha_dice_lo_facturado_lo_recibido_lo_pagado_y_lo_que_queda(cliente, cuenta):
    """Las cuatro cifras, juntas y cuadradas, y sus enlaces."""
    factura = _una_factura(cliente, cuenta["cabeceras"])
    articulo = _un_articulo(cliente, cuenta["cabeceras"])
    albaran = _un_albaran(cliente, cuenta["cabeceras"], factura, articulo, cantidad=300.0)
    gasto = _un_gasto(cliente, cuenta["cabeceras"], factura)

    # Un pago de 200 aplicado **a esa deuda**, con la puerta de pagos.
    pago = cliente.post(
        "/api/gastos/pagos",
        headers=cuenta["cabeceras"],
        json={
            "importe": "200.00",
            "fecha": "2026-03-20",
            "proveedor": factura["proveedor"],
            "forma": "transferencia",
        },
    )
    assert pago.status_code in (200, 201), pago.text
    pago_id = (pago.json().get("pago") or pago.json()).get("id")
    conciliado = cliente.post(
        f"/api/gastos/pagos/{pago_id}/conciliar",
        headers=cuenta["cabeceras"],
        json={"automatico": True, "gastos": [gasto["id"]], "aplicaciones": []},
    )
    assert conciliado.status_code == 200, conciliado.text

    ficha = _la_ficha(cliente, cuenta["cabeceras"], factura["id"])
    compra = ficha["compra"]

    # ── Lo facturado
    assert compra["facturado"] == "663.00", compra["facturado"]
    assert compra["numero_factura"] == "2026/00123"

    # ── Lo recibido: el albarán cuenta, y de la línea han entrado 300 de 500
    assert compra["recibido"]["cuantas_recepciones"] == 1
    assert [una["id"] for una in compra["recibido"]["recepciones"]] == [albaran["id"]]
    assert compra["recibido"]["recepciones"][0]["cantidad_por_unidad"] == {"kg": 300.0}
    la_linea = compra["recibido"]["por_linea"][0]
    assert la_linea["facturado"] == 500.0
    assert la_linea["recibido"] == 300.0
    assert la_linea["falta"] == 200.0
    assert compra["recibido"]["todo_recibido"] is False, "faltan 200 kg y la ficha tiene que decirlo"

    # ── Lo pagado y lo que queda
    assert compra["pagado"] == "200.00", compra["pagado"]
    assert compra["pendiente"] == "463.00", compra["pendiente"]

    # ── Y los enlaces: los identificadores de lo que cuelga de esta compra
    assert compra["gasto_ids"] == [gasto["id"]]
    assert compra["pago_ids"] == [pago_id]
    assert compra["recepcion_ids"] == [albaran["id"]]


def test_lo_que_no_se_puede_saber_se_dice_y_no_se_pinta_como_un_cero(cliente, cuenta):
    """Una línea sin enganche con el albarán: **no se puede saber**, y eso es lo que sale.

    Es la mitad del encargo que se olvida: un `recibido: 0` sería una afirmación falsa («no ha entrado
    nada») cuando lo que pasa es que no hay con qué compararlo. Y si no hay ningún albarán, tampoco se
    puede decir que no haya entrado: se dice que **no ha entrado nada todavía** y por qué.
    """
    factura = _una_factura(cliente, cuenta["cabeceras"])

    # Sin ningún albarán: la ficha lo dice con sus palabras.
    ficha = _la_ficha(cliente, cuenta["cabeceras"], factura["id"])
    assert ficha["compra"]["recibido"]["cuantas_recepciones"] == 0
    assert textos.mensaje("AL40_esta_factura_no_ha_metido_nada_en_el_almacen") in ficha["avisos"]

    # Y con un albarán que **no** dice a qué línea de la factura corresponde, no se puede saber cuánto ha
    # entrado de cada línea.
    articulo = _un_articulo(cliente, cuenta["cabeceras"])
    _un_albaran(
        cliente,
        cuenta["cabeceras"],
        factura,
        articulo,
        cantidad=300.0,
        lineas=[
            {
                "articulo_id": articulo["id"],
                "nombre": articulo["nombre"],
                "unidad": "kg",
                "cantidad": 300.0,
            }
        ],
    )

    ficha = _la_ficha(cliente, cuenta["cabeceras"], factura["id"])
    la_linea = ficha["compra"]["recibido"]["por_linea"][0]
    assert la_linea["recibido"] is None, "sin enganche no se puede saber, y no es un cero"
    assert la_linea["falta"] is None
    assert ficha["compra"]["recibido"]["todo_recibido"] is None
    assert ficha["compra"]["recibido"]["lineas_sin_enganche"] == 1
    assert any("no se puede saber" in aviso for aviso in ficha["avisos"]), ficha["avisos"]


def test_un_albaran_anulado_no_cuenta_como_recibido(cliente, cuenta):
    """Lo que se anuló **no entró**: sigue viéndose en la ficha, pero no cuenta.

    Sin esto, anular un albarán mal apuntado dejaría la compra diciendo que la mercancía entró, que es
    justo lo contrario de lo que el agricultor acaba de decir.
    """
    factura = _una_factura(cliente, cuenta["cabeceras"])
    articulo = _un_articulo(cliente, cuenta["cabeceras"])
    albaran = _un_albaran(cliente, cuenta["cabeceras"], factura, articulo, cantidad=300.0)

    anulado = cliente.post(
        f"/api/almacen/recepciones/{albaran['id']}/anular",
        headers=cuenta["cabeceras"],
        json={"motivo": "venía de menos"},
    )
    assert anulado.status_code == 200, anulado.text

    ficha = _la_ficha(cliente, cuenta["cabeceras"], factura["id"])
    recibido = ficha["compra"]["recibido"]
    assert recibido["cuantas_recepciones"] == 0, "un albarán anulado no cuenta"
    assert recibido["cuantas_anuladas"] == 1, "pero se sigue viendo que existió"
    assert recibido["recepciones"][0]["anulada"] is True
    assert recibido["por_linea"][0]["recibido"] is None, "lo anulado no entró"
    assert textos.mensaje("AL40_esta_factura_no_ha_metido_nada_en_el_almacen") in ficha["avisos"]


def test_la_ficha_no_enseña_el_dinero_de_otra_compra(cliente, cuenta):
    """Un pago de 350 que reparte 100 aquí y 250 allá: **aquí se ven 100**, no 350.

    Es la forma fácil de contar el mismo dinero dos veces, y por eso lo que se enseña es **lo aplicado a
    esta compra**, que es la misma regla con la que la pantalla de gastos cuenta lo pagado.
    """
    mia = _una_factura(cliente, cuenta["cabeceras"])
    ajena = _una_factura(
        cliente, cuenta["cabeceras"], numero_factura="2026/00124", total=250.0, base_imponible=250.0
    )
    mi_gasto = _un_gasto(cliente, cuenta["cabeceras"], mia, importe="100.00")
    su_gasto = _un_gasto(cliente, cuenta["cabeceras"], ajena, importe="250.00")

    pago = cliente.post(
        "/api/gastos/pagos",
        headers=cuenta["cabeceras"],
        json={"importe": "350.00", "fecha": "2026-03-20", "forma": "transferencia"},
    )
    assert pago.status_code in (200, 201), pago.text
    pago_id = (pago.json().get("pago") or pago.json()).get("id")
    conciliado = cliente.post(
        f"/api/gastos/pagos/{pago_id}/conciliar",
        headers=cuenta["cabeceras"],
        json={"automatico": True, "gastos": [mi_gasto["id"], su_gasto["id"]], "aplicaciones": []},
    )
    assert conciliado.status_code == 200, conciliado.text

    ficha = _la_ficha(cliente, cuenta["cabeceras"], mia["id"])
    assert ficha["compra"]["pagado"] == "100.00", ficha["compra"]["pagado"]
    assert ficha["compra"]["pendiente"] == "0.00"
    assert ficha["compra"]["pagos"][0]["importe"] == "350.00", "el pago entero se ve"
    assert ficha["compra"]["pagos"][0]["aplicado_a_esta_compra"] == "100.00", (
        "pero lo que va a esta compra son 100"
    )


def test_la_ficha_de_otra_finca_no_se_abre(cliente, cuenta, crear_cuenta):
    """El aislamiento: la compra de otra finca **no es tuya**, y la puerta lo dice."""
    factura = _una_factura(cliente, cuenta["cabeceras"])
    la_otra = crear_cuenta("otro@ejemplo.test", nombre="Otro agricultor", nif="12345678Z")

    respuesta = cliente.get(f"/api/compras/{factura['id']}", headers=la_otra["cabeceras"])

    assert respuesta.status_code == 404, respuesta.text
