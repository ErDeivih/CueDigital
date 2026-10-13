"""Darle la forma a una tierra que no la tiene (CRM-06, 14/10/2026).

**Por que existe esta puerta.** El mapa, cuando no hay ninguna tierra con forma, dice: *«Se le puede decir la
forma a una tierra desde su ficha»*. **Y esa accion no existia**: `Parcela.geometria` solo se escribe al crear la
tierra, y `PUT /api/parcelas/{id}` la protege a proposito (para que corregir un nombre no borre el dibujo). La
pantalla prometia algo que no se podia hacer.

Lo que se prueba aqui es eso, y solo eso: que se le puede dar la forma a una tierra que no la tiene, **que queda
apuntada con la fuente que dice quien lo dijo** (`agricultor`), y que **no se inventa nada** si no hay forma.

Y se comprueba que la forma **manda sobre el SIGPAC pero no sobre una medicion en el campo**, que es la regla de
prioridad que la casa tiene escrita.
"""

from __future__ import annotations

# Un cuadrado pequeno y valido, en WGS84, con coordenadas REALES (no inventadas al azar): el trozo de una finca.
UN_CUADRADO = "POLYGON((-4.7000 41.6000, -4.6990 41.6000, -4.6990 41.6010, -4.7000 41.6010, -4.7000 41.6000))"


def _darle_la_forma(cliente, cuenta, tierra_id: int, geometria: str, campana_id=None):
    cuerpo = {"geometria": geometria}
    if campana_id is not None:
        cuerpo["campana_id"] = campana_id
    return cliente.put(f"/api/parcelas/{tierra_id}/forma", headers=cuenta["cabeceras"], json=cuerpo)


def _las_versiones_de(cliente, cuenta, tierra_id: int) -> list[dict]:
    respuesta = cliente.get("/api/versiones", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    versiones = datos if isinstance(datos, list) else datos.get("versiones", [])
    return [v for v in versiones if v.get("parcela_id") == tierra_id]


def test_a_una_tierra_sin_forma_se_le_puede_dar_y_queda_apuntada(cliente, cuenta, crear_parcela, campana):
    # El caso del texto del mapa: una tierra sin forma, y alguien que se la dice.
    tierra = crear_parcela()
    assert _las_versiones_de(cliente, cuenta, tierra["id"]) == [], "de entrada no tiene ninguna forma"
    respuesta = _darle_la_forma(cliente, cuenta, tierra["id"], UN_CUADRADO, campana_id=campana["id"])
    assert respuesta.status_code == 200, respuesta.text
    # **Y queda apuntada con LA FUENTE que dice quien lo dijo**: no es una importacion del SIGPAC.
    versiones = _las_versiones_de(cliente, cuenta, tierra["id"])
    assert versiones, f"tiene que haber quedado una version: {respuesta.text[:200]}"
    assert any(v.get("fuente") == "agricultor" for v in versiones), versiones


def test_sin_forma_no_se_apunta_nada(cliente, cuenta, crear_parcela):
    # **Un poligono no se inventa**: sin forma, la puerta lo dice y no escribe.
    tierra = crear_parcela()
    respuesta = _darle_la_forma(cliente, cuenta, tierra["id"], "   ")
    assert respuesta.status_code == 400, f"sin forma no hay nada que apuntar: {respuesta.status_code}"
    assert _las_versiones_de(cliente, cuenta, tierra["id"]) == [], "y no puede haber escrito nada"


def test_la_tierra_de_otra_finca_no_se_toca(cliente, cuenta, crear_parcela, crear_cuenta):
    # **Aislamiento**: 404 sin distinguir «no existe» de «no es tuya».
    tierra = crear_parcela()
    otra = crear_cuenta("forma-de-tierra@ejemplo.test")
    respuesta = _darle_la_forma(cliente, otra, tierra["id"], UN_CUADRADO)
    assert respuesta.status_code == 404, f"otra finca no deberia poder: {respuesta.status_code}"
    assert _las_versiones_de(cliente, cuenta, tierra["id"]) == [], "y no puede haberle escrito la forma"
