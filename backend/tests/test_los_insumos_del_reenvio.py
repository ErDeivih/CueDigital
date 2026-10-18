"""**Los insumos CON envase tambien se comparan** (18/10/2026).

### ***Por que esta prueba, si ya habia cuatro***

*Las otras cuatro del reenvio compuesto prueban las **lineas** del plan y **el camino de los insumos que la puerta
se salta**. Pero la comparacion de los insumos **de verdad** -los que si se escriben, con su envase- **no la
ejercitaba ninguna**: un insumo sin `lote_id` no se saca del almacen, asi que no hay nada que comparar.*

***Y es el caso que mas duele si se pierde***: *el reintento de una labor con **otros** insumos devolveria la
labor vieja y **el almacen se quedaria con el descuento de la primera vez**.*

### ***Como se siembra sin pasar por un albaran***

*`POST /api/almacen/lotes` **abre un lote** sin compra detras -lo dice su propia puerta: «hay producto que ya
estaba en la nave cuando se empezo a usar el programa»-, y el insumo lleva **`aceptar_descuadre`**, que es la
puerta diciendo «se que el envase se queda en negativo, apuntalo igual». Asi no hay que montar una recepcion
entera para probar lo que se quiere probar.*
"""

from __future__ import annotations


def _un_articulo(cliente, cuenta, nombre: str = "El producto del reenvio") -> dict:
    creado = cliente.post(
        "/api/almacen/articulos",
        headers=cuenta["cabeceras"],
        json={"nombre": nombre, "unidad": "kg"},
    )
    assert creado.status_code in (200, 201), creado.text
    return creado.json()


def _un_lote(cliente, cuenta, articulo_id: int, numero: str = "L-1801") -> dict:
    creado = cliente.post(
        "/api/almacen/lotes",
        headers=cuenta["cabeceras"],
        json={"articulo_id": articulo_id, "numero_lote": numero},
    )
    assert creado.status_code in (200, 201), creado.text
    return creado.json()


def _una_labor_con(cliente, cuenta, campana, parcela, lote_id: int, cantidad: str, clave: str):
    return cliente.post(
        "/api/trabajos",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "tipo": "laboreo",
            "fecha": "2026-11-12",
            "parcela_id": parcela["id"],
            "insumos": [
                {"lote_id": lote_id, "cantidad": cantidad, "unidad": "kg", "aceptar_descuadre": True}
            ],
            "clave_de_reenvio": clave,
        },
    )


def test_una_labor_con_los_MISMOS_insumos_no_se_apunta_dos_veces(cliente, cuenta, campana, crear_parcela):
    """***El reintento legitimo***: *los mismos insumos, con su envase, devuelven la misma labor.*"""
    parcela = crear_parcela(alias="La de los insumos con envase")
    articulo = _un_articulo(cliente, cuenta)
    lote = _un_lote(cliente, cuenta, articulo["id"])

    primera = _una_labor_con(cliente, cuenta, campana, parcela, lote["id"], "5", "labor-con-envase")
    assert primera.status_code == 201, primera.text

    repetida = _una_labor_con(cliente, cuenta, campana, parcela, lote["id"], "5", "labor-con-envase")
    assert repetida.status_code in (200, 201), (
        f"***el mismo reenvio, con los mismos insumos, devuelve la misma labor***: {repetida.text}"
    )
    assert repetida.json()["hecho"]["id"] == primera.json()["hecho"]["id"], repetida.json()


def test_y_con_OTRA_cantidad_de_insumo_es_un_conflicto(cliente, cuenta, campana, crear_parcela):
    """***Y con otra cantidad, 409.***

    *Esto es lo que antes se perdia: *la puerta habia sacado **5 kg** del almacen, y el reintento con **9** se
    contestaba con la labor vieja **como si se hubieran sacado 9**.*
    """
    parcela = crear_parcela(alias="La de la otra cantidad")
    articulo = _un_articulo(cliente, cuenta, "El producto de la otra cantidad")
    lote = _un_lote(cliente, cuenta, articulo["id"], "L-1802")

    assert _una_labor_con(cliente, cuenta, campana, parcela, lote["id"], "5", "labor-otra-cantidad").status_code == 201

    otra = _una_labor_con(cliente, cuenta, campana, parcela, lote["id"], "9", "labor-otra-cantidad")

    assert otra.status_code == 409, (
        f"***los kilos que se sacan del almacen son parte de la accion***: {otra.text}"
    )
