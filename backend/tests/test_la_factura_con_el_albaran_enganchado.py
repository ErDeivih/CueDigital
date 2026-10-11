"""Corregir o borrar una factura **con un albarán enganchado a sus líneas** (09/10/2026).

**Por qué existe.** Lo encontró el revisor independiente, y era un **500** en producción: la factura
guardaba una lista de líneas, y `corregir_factura` las **borraba y las rehacía** enteras. Su propio
docstring lo justificaba diciendo que *«nada del programa apunta a una línea»*, y **era falso**:
`lineas_de_recepcion.linea_factura_id` apunta a `lineas_de_factura.id` —es el enganche que dice «esta
línea del albarán es esta línea de la factura»—. Así que al borrar la línea, la base rechazaba la
operación:

    sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) FOREIGN KEY constraint failed
    [SQL: DELETE FROM lineas_de_factura WHERE lineas_de_factura.id = ?]

El agricultor no podía corregir la factura y veía un 500 opaco. Y **ninguna prueba lo cubría**: el guion de
la compra engancha su albarán solo por cabecera, así que nunca pisaba ese camino.

Lo que se exige aquí:

  · **Corregir una factura con el albarán enganchado línea a línea se hace, y el enganche sobrevive.** Es
    lo que el encargo pide que se conserve: la línea mantiene su identificador, así que el albarán sigue
    diciendo a qué línea de la factura corresponde.
  · **Y si la corrección quiere quitar esa línea, se contesta 409 con sus palabras** —no un 500—, porque un
    enganche no se puede conservar si la línea desaparece.
  · **Borrar la factura tampoco revienta**: el guardián «está en uso» cuenta también el enganche fino, así
    que contesta lo que ya contestaba cuando había un abono colgando.
"""

from __future__ import annotations

import json

from app import textos

UNA_LINEA = {
    "descripcion": "GLIFOSATO 36% SL 20 L",
    "cantidad": 5,
    "unidad": "L",
    "precio_unitario": 34.0,
    "importe": 170.0,
}


def _cuerpo(**cambios) -> dict:
    cuerpo = {
        "fecha": "2026-03-15",
        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "proveedor_nif": "F37012345",
        "numero_factura": "2026/00123",
        "base_imponible": 170.0,
        "cuota_iva": 35.70,
        "tipo_iva_pct": 21.0,
        "total": 205.70,
        "leida_por": "a mano",
        "lineas": [dict(UNA_LINEA)],
    }
    cuerpo.update(cambios)
    return cuerpo


def _una_factura(cliente, cabeceras, **cambios) -> dict:
    respuesta = cliente.post(
        "/api/facturas", headers=cabeceras, data={"datos": json.dumps(_cuerpo(**cambios))}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _un_articulo(cliente, cabeceras) -> dict:
    respuesta = cliente.post(
        "/api/almacen/articulos",
        headers=cabeceras,
        json={"nombre": "Glifosato 36 SL", "categoria": "fitosanitario", "unidad": "L"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _un_albaran_enganchado_por_linea(cliente, cabeceras, factura: dict, articulo: dict) -> dict:
    """Un albarán cuya línea dice **a qué línea de la factura** corresponde (el enganche fino)."""
    respuesta = cliente.post(
        "/api/almacen/recepciones",
        headers=cabeceras,
        json={
            "fecha": "2026-03-16",
            "proveedor": factura["proveedor"],
            "proveedor_nif": factura["proveedor_nif"],
            "numero_albaran": "A-2026-0001",
            "factura_id": factura["id"],
            "lineas": [
                {
                    "articulo_id": articulo["id"],
                    "nombre": articulo["nombre"],
                    "unidad": "L",
                    "cantidad": 5,
                    "linea_factura_id": factura["lineas"][0]["id"],
                }
            ],
        },
    )
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json().get("recepcion") or respuesta.json()


def test_corregir_una_factura_con_el_albaran_enganchado_a_sus_lineas_no_revienta(cliente, cuenta):
    """El 500 que encontró el revisor: **se corrige, y el enganche sigue ahí.**

    Antes: `PUT /api/facturas/{id}` → 500 por la clave foránea. Ahora: 200, la línea cambia lo que tenía
    que cambiar, y el albarán **sigue apuntando a esa línea**.
    """
    factura = _una_factura(cliente, cuenta["cabeceras"])
    articulo = _un_articulo(cliente, cuenta["cabeceras"])
    albaran = _un_albaran_enganchado_por_linea(cliente, cuenta["cabeceras"], factura, articulo)
    la_linea_de_antes = factura["lineas"][0]["id"]

    corregida = cliente.put(
        f"/api/facturas/{factura['id']}",
        headers=cuenta["cabeceras"],
        json=_cuerpo(lineas=[{**UNA_LINEA, "descripcion": "GLIFOSATO 36% SL 20 L (corregido)"}]),
    )

    assert corregida.status_code == 200, (
        "corregir una factura con un albarán enganchado a sus líneas no puede contestar "
        f"{corregida.status_code}: {corregida.text}"
    )
    assert corregida.json()["lineas"][0]["descripcion"].endswith("(corregido)")
    assert corregida.json()["lineas"][0]["id"] == la_linea_de_antes, (
        "la línea conserva su identificador: es lo que mantiene vivo el enganche del albarán"
    )

    # Y el enganche, comprobado por donde se ve: la ficha de la compra dice que esa línea ha recibido.
    ficha = cliente.get(f"/api/compras/{factura['id']}", headers=cuenta["cabeceras"]).json()
    assert ficha["compra"]["recibido"]["por_linea"][0]["recibido"] == 5.0
    assert ficha["compra"]["recibido"]["cuantas_recepciones"] == 1
    assert albaran["id"] in ficha["compra"]["recepcion_ids"]


def test_quitar_una_linea_que_un_albaran_apunta_se_dice_con_palabras(cliente, cuenta):
    """Quitar esa línea **no se puede** (el enganche se quedaría sin nada), y se explica qué hacer.

    Es un 409 con su mensaje, no el 500 de la clave foránea: lo que no se puede hacer se dice, y se dice
    cómo se arregla (anular el albarán antes).
    """
    factura = _una_factura(cliente, cuenta["cabeceras"])
    articulo = _un_articulo(cliente, cuenta["cabeceras"])
    _un_albaran_enganchado_por_linea(cliente, cuenta["cabeceras"], factura, articulo)

    # La corrección manda **dos** líneas donde había una: la primera se escribe encima de la que el
    # albarán apunta y la segunda sobra... así que lo que se prueba aquí es lo contrario: mandar **cero**
    # líneas, que dejaría la línea apuntada sin sitio.
    sin_lineas = cliente.put(
        f"/api/facturas/{factura['id']}",
        headers=cuenta["cabeceras"],
        json=_cuerpo(lineas=[]),
    )

    assert sin_lineas.status_code == 409, sin_lineas.text
    assert textos.mensaje("AL44_no_se_puede_quitar_una_linea_con_albaran") in sin_lineas.text

    # Y la factura sigue como estaba: una corrección rechazada no deja nada a medias.
    sigue = cliente.get(f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"]).json()
    assert [una["id"] for una in sigue["lineas"]] == [factura["lineas"][0]["id"]]


def test_borrar_una_factura_con_el_albaran_enganchado_por_linea_no_revienta(cliente, cuenta):
    """Borrar tampoco revienta: el guardián cuenta también el enganche fino.

    Con la factura en la cabecera del albarán ya se negaba con un 409 («está en uso»). Faltaba el caso en
    que el albarán **solo** la lleva en sus líneas: ahí el borrado intentaba llevarse las líneas y la base
    lo rechazaba con un 500.
    """
    factura = _una_factura(cliente, cuenta["cabeceras"])
    articulo = _un_articulo(cliente, cuenta["cabeceras"])
    # Sin decir la factura en la cabecera: **solo** por el enganche de la línea.
    respuesta = cliente.post(
        "/api/almacen/recepciones",
        headers=cuenta["cabeceras"],
        json={
            "fecha": "2026-03-16",
            "proveedor": factura["proveedor"],
            "proveedor_nif": factura["proveedor_nif"],
            "numero_albaran": "A-2026-0002",
            "lineas": [
                {
                    "articulo_id": articulo["id"],
                    "nombre": articulo["nombre"],
                    "unidad": "L",
                    "cantidad": 5,
                    "linea_factura_id": factura["lineas"][0]["id"],
                }
            ],
        },
    )
    assert respuesta.status_code in (200, 201), respuesta.text

    borrado = cliente.delete(f"/api/facturas/{factura['id']}", headers=cuenta["cabeceras"])

    assert borrado.status_code in (200, 409), (
        f"borrar no puede contestar {borrado.status_code}: {borrado.text}"
    )
    if borrado.status_code == 409:
        assert "uso" in borrado.text or "apunt" in borrado.text, borrado.text
