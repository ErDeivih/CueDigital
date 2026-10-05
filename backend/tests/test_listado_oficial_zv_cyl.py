"""La fuente municipal oficial se reproduce y se aplica sin confundir nombres."""

import hashlib
import json

import pytest

from app import catalogos
from scripts import bajar_zonas_vulnerables_cyl as fuente


def test_el_csv_se_reproduce_del_excel_de_idecyl_y_el_ine():
    excel = fuente.EXCEL.read_bytes()
    ine = fuente.INE.read_bytes()
    reproducido, zonas = fuente.extraer(excel, ine)
    assert reproducido == fuente.CSV.read_text(encoding="utf-8")
    meta = json.loads(fuente.PROCEDENCIA.read_text(encoding="utf-8"))
    assert meta["fuente_excel_sha256"] == hashlib.sha256(excel).hexdigest()
    assert meta["fuente_ine_sha256"] == hashlib.sha256(ine).hexdigest()
    assert len(zonas) == 24
    assert len(reproducido.splitlines()) == 388
    assert "Peñaranda de Bracamonte,Salamanca,37246,Alba-Peñaranda" in reproducido


def test_codigo_o_municipio_y_provincia_sin_ambiguedad(monkeypatch):
    monkeypatch.setattr(catalogos, "_RUTA_ZV_POR_DEFECTO", fuente.CSV)
    try:
        assert catalogos.cargar_zonas_vulnerables() == 387
        assert next(r for r in catalogos.reglas_nitratos() if r.clave == "aportes_por_cultivo").que_hace_la_app == "avisa"
        assert catalogos.es_zona_vulnerable("Peñaranda de Bracamonte", "Salamanca") is True
        assert catalogos.es_zona_vulnerable(None, codigo_ine="37246") is True
        assert catalogos.es_zona_vulnerable("Peñaranda de Bracamonte", "Burgos") is False
        assert catalogos.es_zona_vulnerable(
            "Peñaranda de Bracamonte", "Salamanca", "37250"
        ) is True
        assert catalogos.es_zona_vulnerable("Peñaranda de Bracamonte") is None
        assert catalogos.es_zona_vulnerable(None, codigo_ine="37250") is False
    finally:
        catalogos.olvidar_zonas_vulnerables()


@pytest.mark.parametrize("especie", ["Maíz", "Trigo blando"])
def test_no_se_inventa_cifra_si_la_casilla_o_el_nombre_no_coinciden(
    cliente, cuenta, campana, crear_parcela, fertilizante, especie,
):
    parcela = crear_parcela(zona_vulnerable_nitratos=True, sistema="secano")
    respuesta = cliente.post(
        f"/api/parcelas/{parcela['id']}/cultivos", headers=cuenta["cabeceras"],
        json={"campana_id": campana["id"], "especie": especie, "sistema": "secano"},
    )
    assert respuesta.status_code == 201, respuesta.text
    validacion = cliente.post("/api/fertilizaciones/validar", headers=cuenta["cabeceras"], json={
        "campana_id": campana["id"], "fecha": "2026-05-12", "parcela_id": parcela["id"],
        "superficie_ha": parcela["superficie_ha"], "fertilizante_id": fertilizante["id"],
        "kg_ha_producto": 1000,
    })
    assert validacion.status_code == 200, validacion.text
    assert "N3_tabla_cultivo" not in {a["codigo"] for a in validacion.json()["avisos"]}


def test_aviso_del_anexo_iii_solo_para_cultivo_y_zona_exactos(
    cliente, cuenta, campana, crear_parcela, fertilizante, monkeypatch,
):
    monkeypatch.setattr(catalogos, "_RUTA_ZV_POR_DEFECTO", fuente.CSV)
    try:
        catalogos.cargar_zonas_vulnerables()
        parcela = crear_parcela(
            municipio="Peñaranda de Bracamonte", provincia="Salamanca",
            zona_vulnerable_nitratos=None,
        )
        assert parcela["zona_vulnerable_nitratos"] is True
        cultivo = cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos", headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "Cebada", "sistema": "secano"},
        )
        assert cultivo.status_code == 201, cultivo.text
        cuerpo = {
            "campana_id": campana["id"], "fecha": "2026-05-12", "parcela_id": parcela["id"],
            "superficie_ha": parcela["superficie_ha"], "fertilizante_id": fertilizante["id"],
            "kg_ha_producto": 300,
        }
        primero = cliente.post("/api/fertilizaciones", headers=cuenta["cabeceras"], json=cuerpo)
        assert primero.status_code == 201, primero.text
        segundo = cliente.post("/api/fertilizaciones/validar", headers=cuenta["cabeceras"], json=cuerpo)
        assert segundo.status_code == 200, segundo.text
        avisos = {a["codigo"]: a for a in segundo.json()["avisos"]}
        assert avisos["N3_tabla_cultivo"]["bloquea"] is False
        assert "105,0" in avisos["N3_tabla_cultivo"]["mensaje"]
        assert "201,0" in avisos["N3_tabla_cultivo"]["mensaje"]
        assert cliente.get("/api/zonas-vulnerables/estado").json()["municipios"] == 387
    finally:
        catalogos.olvidar_zonas_vulnerables()
