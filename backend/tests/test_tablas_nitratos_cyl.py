"""El JSON deriva de las tablas del PDF oficial, incluidas sus casillas vacías."""

from __future__ import annotations

from app import catalogos, nitratos_cyl
from scripts.bajar_nitratos_cyl import FUENTE_PDF, extraer


def test_extraccion_se_reproduce_desde_el_pdf_oficial():
    guardado = nitratos_cyl.cargar()
    reproducido = extraer(FUENTE_PDF, descargado_el=guardado["descargado_el"])
    assert reproducido == guardado
    assert len(guardado["aportes_maximos"]) == 22
    assert len(guardado["periodos_prohibidos"]) == 6


def test_los_numeros_y_los_blancos_son_los_del_anexo_iii():
    assert nitratos_cyl.aporte_de("Trigo y Triticale", "secano")["maximo_kg_n_ha"] == 105
    assert nitratos_cyl.aporte_de("Trigo y Triticale", "regadio")["maximo_kg_n_ha"] == 150
    assert nitratos_cyl.aporte_de("Cebada", "regadio")["maximo_kg_n_ha"] == 135
    assert nitratos_cyl.aporte_de("Maíz", "regadio")["maximo_kg_n_ha"] == 324
    assert nitratos_cyl.aporte_de("Patata", "regadio")["maximo_kg_n_ha"] == 200
    assert nitratos_cyl.aporte_de("Maíz", "secano") is None
    assert nitratos_cyl.aporte_de("Patata", "secano") is None
    assert nitratos_cyl.aporte_de("cultivo no recogido", "regadio") is None
    assert nitratos_cyl.aporte_de("Cebada", "sistema inventado") is None


def test_los_periodos_conservan_tipos_excepciones_y_fechas_relativas():
    datos = nitratos_cyl.cargar()
    invierno = next(p for p in datos["periodos_prohibidos"] if p["grupo_cultivos"] == "Cereales de Invierno")
    assert "tipos A y B" in invierno["fertilizantes_organicos"]
    assert "1 de abril a 1 de septiembre" in invierno["fertilizantes_organicos"]
    horticolas = next(p for p in datos["periodos_prohibidos"] if p["grupo_cultivos"] == "Hortícolas")
    assert "lenta liberación" in horticolas["fertilizantes_inorganicos_o_minerales"]
    assert "fertiirrigación" in horticolas["fertilizantes_inorganicos_o_minerales"]
    assert set(datos["tipos_fertilizante_organico"]) == {"A", "B", "C"}


def test_sin_fichero_no_se_inventa_el_limite(tmp_path, monkeypatch):
    ausente = tmp_path / "no-existe.json"
    assert nitratos_cyl.cargar(ausente) == {}
    assert nitratos_cyl.aportes_maximos(ausente) == ()
    assert nitratos_cyl.periodos_prohibidos(ausente) == ()
    monkeypatch.setattr(nitratos_cyl, "RUTA_POR_DEFECTO", ausente)
    assert len(catalogos.limites_que_faltan()) == 2
    assert {r.clave for r in catalogos.reglas_nitratos() if r.que_hace_la_app == "sin_datos"} == {
        "aportes_por_cultivo", "periodos_prohibidos"
    }
