"""La puerta de la normativa: lo que sirve, y lo que **no** inventa (07/10/2026).

La pantalla de normativa no puede inventar nada -una obligacion y una recomendacion no se leen igual-, asi que
esta prueba sujeta **la puerta**: que sirva las diez reglas de la matriz, con sus direcciones oficiales, y que
**no rellene** lo que la matriz no dice.
"""

from __future__ import annotations


def _las_reglas(cliente, cuenta) -> list[dict]:
    respuesta = cliente.get("/api/normativa", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_sirve_las_diez_reglas_de_la_matriz(cliente, cuenta):
    """Ni nueve ni once, y en su orden: es lo que la matriz tiene."""
    reglas = _las_reglas(cliente, cuenta)
    assert [una["codigo"] for una in reglas] == [
        "N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08", "N09", "N10",
    ]


def test_cada_regla_trae_su_direccion_oficial(cliente, cuenta):
    """Sin direccion oficial, una regla no se puede comprobar -y lo que no se comprueba es una opinion."""
    for una in _las_reglas(cliente, cuenta):
        assert una["titulo"].strip(), una["codigo"]
        assert una["texto"].strip(), una["codigo"]
        assert una["fuentes"], una["codigo"]
        for fuente in una["fuentes"]:
            assert fuente["enlace"].startswith("https://"), (una["codigo"], fuente["enlace"])
            assert fuente["nombre"].strip(), (una["codigo"], fuente["enlace"])


def test_el_tipo_y_el_estado_salen_vacios_y_la_puerta_no_los_rellena(cliente, cuenta):
    """La decision de David, sujeta **en la puerta**: antes «sin clasificar» que rellenarlos a ojo.

    Si algun dia alguien rellena esto -en la matriz, que es donde tiene que ser-, este test falla y obliga a
    decirlo: presentar una recomendacion tecnica como una obligacion es lo que la matriz pide que no se haga.
    """
    for una in _las_reglas(cliente, cuenta):
        assert una["tipo"] == "", una["codigo"]
        assert una["estado"] == "", una["codigo"]


def test_los_avisos_de_la_matriz_llegan_enteros(cliente, cuenta):
    """Los dos avisos que mas duelen si se pierden por el camino."""
    por_codigo = {una["codigo"]: una for una in _las_reglas(cliente, cuenta)}
    assert "no copiar porcentajes" in por_codigo["N01"]["texto"].lower()
    assert "dos obligaciones diferentes" in por_codigo["N09"]["texto"].lower()


def test_una_regla_con_varias_normas_las_trae_todas(cliente, cuenta):
    """N07 se apoya en cuatro normas: si la puerta mandara solo la primera, la pantalla mentiria."""
    por_codigo = {una["codigo"]: una for una in _las_reglas(cliente, cuenta)}
    assert len(por_codigo["N07"]["fuentes"]) == 4

def test_la_ayuda_del_agricultor_es_la_que_se_sirve(cliente, cuenta):
    """La puerta manda **la ayuda**, no el texto de trabajo, y sin Markdown."""
    for una in _las_reglas(cliente, cuenta):
        assert una["ayuda"].strip(), una["codigo"]
        assert "**" not in una["ayuda"], una["codigo"]
        assert "](" not in una["ayuda"], una["codigo"]
