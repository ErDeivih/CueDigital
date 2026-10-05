"""Los datos que faltaban al agricultor se preguntan, guardan y devuelven."""

from app import iuws_mapeo


def test_cosecha_con_cuatro_respuestas_distintas(cliente, cuenta, campana, parcela):
    respuesta = cliente.post("/api/cosecha", headers=cuenta["cabeceras"], json={
        "campana_id": campana["id"], "fecha": "2026-05-12", "parcela_id": parcela["id"],
        "semillas_siembra": True, "plantas_cosechadas": False,
        "sin_cosechar_ambiental": True, "restos_cosecha_depositados": False,
    })
    assert respuesta.status_code == 201, respuesta.text
    labor = cliente.get("/api/labores", headers=cuenta["cabeceras"]).json()[0]
    assert [labor[c] for c in (
        "semillas_siembra", "plantas_cosechadas", "sin_cosechar_ambiental",
        "restos_cosecha_depositados",
    )] == [True, False, True, False]


def test_cubierta_separa_establecimiento_de_mantenimiento(cliente, cuenta, campana, parcela):
    respuesta = cliente.post("/api/labores", headers=cuenta["cabeceras"], json={
        "campana_id": campana["id"], "tipo": "cubierta", "fecha": "2026-05-12",
        "parcela_id": parcela["id"], "fecha_establecimiento_cubierta": "2025-10-03",
        "tipo_cobertura": "Vegetal espontánea", "anchura_cubierta_m": 1.6,
        "anchura_libre_proyeccion_m": 0.4,
    })
    assert respuesta.status_code == 201, respuesta.text
    labor = respuesta.json()
    assert labor["fecha"] == "2026-05-12"
    assert labor["fecha_establecimiento_cubierta"] == "2025-10-03"
    assert labor["tipo_cobertura"] == "Vegetal espontánea"
    assert labor["anchura_cubierta_m"] == 1.6
    assert labor["anchura_libre_proyeccion_m"] == 0.4


def test_restos_sin_respuesta_no_se_convierten_en_no(cliente, cuenta, campana, parcela):
    respuesta = cliente.post("/api/labores", headers=cuenta["cabeceras"], json={
        "campana_id": campana["id"], "tipo": "desbroce", "fecha": "2026-05-12",
        "parcela_id": parcela["id"], "restos_desbroce_depositados": False,
    })
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["restos_desbroce_depositados"] is False
    assert respuesta.json()["restos_poda_depositados"] is None


def test_tipo_y_unidad_del_producto_siguen_pendientes_de_codigo(
    cliente, cuenta, campana, parcela, crear_producto,
):
    producto = crear_producto(tipo_producto="Herbicida")
    assert producto["tipo_producto"] == "Herbicida"
    respuesta = cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json={
        "campana_id": campana["id"], "fecha": "2026-05-12", "parcela_id": parcela["id"],
        "superficie_tratada_ha": 1.0, "producto_id": producto["id"],
        "dosis": 0.5, "unidad_cantidad_aplicada": "L",
        "justificacion": "Vi pulgón en la parcela",
    })
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["unidad_cantidad_aplicada"] == "L"
    correspondencia = {c.oficial: c for c in iuws_mapeo.correspondencia_de_un_bloque("DatosCubierta")}
    assert correspondencia["FecEstablecimientoCub"].de == "fecha_establecimiento_cubierta"
    assert correspondencia["TipoCobertura"].estado == iuws_mapeo.HACE_FALTA_CATALOGO
