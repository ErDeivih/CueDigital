"""El guardian de las reglas de la normativa (07/10/2026).

La pantalla de normativa **no puede inventar nada**: lo que ensena sale de la matriz. Este guardian sujeta lo
que se decidio antes de escribirla, para que no se pierda por el camino.
"""

from __future__ import annotations

from app import normativa, textos


def test_las_ayudas_viven_en_los_textos_y_no_dentro_del_modulo_de_datos():
    """**Dónde viven los textos visibles** (07/10/2026).

    David lo señaló: estas ayudas **se leen en pantalla**, y en esta casa los textos visibles viven en
    `app/textos.py` —para poder revisarlos juntos y para que la prueba de la jerga los mire—. Yo las había
    puesto dentro del módulo de datos. Esta prueba sujeta que **se citan**: si alguien vuelve a escribirlas
    dentro, o cambia una y no la otra, aquí se ve.
    """
    del_modulo = {una.codigo: una.ayuda for una in normativa.LAS_REGLAS}
    del_servidor = textos.AYUDA_DE_LA_NORMATIVA
    assert set(del_modulo) == set(del_servidor), (
        f"en el módulo sobran {sorted(set(del_modulo) - set(del_servidor))} y faltan "
        f"{sorted(set(del_servidor) - set(del_modulo))}"
    )
    for codigo, ayuda in del_servidor.items():
        assert del_modulo[codigo] == ayuda, f"{codigo}: el módulo no cita lo que hay en los textos"


def test_estan_las_diez_reglas():
    """Ni nueve ni once: la matriz tiene diez, y si manana tiene once, esto lo dice."""
    assert [una.codigo for una in normativa.LAS_REGLAS] == [
        "N01", "N02", "N03", "N04", "N05", "N06", "N07", "N08", "N09", "N10",
    ]


def test_ninguna_regla_se_queda_sin_lo_que_hace_falta_para_comprobarla():
    """Sin direccion oficial no se puede comprobar nada, y lo que no se puede comprobar es una opinion."""
    for una in normativa.LAS_REGLAS:
        assert una.titulo.strip(), una.codigo
        assert una.texto.strip(), una.codigo
        assert una.fuentes, una.codigo
        for fuente in una.fuentes:
            assert fuente.enlace.startswith("https://"), (una.codigo, fuente.enlace)
            assert fuente.nombre.strip(), (una.codigo, fuente.enlace)


def test_el_tipo_y_el_estado_van_vacios_y_no_inventados():
    """La decision de David: antes «sin clasificar» que rellenarlos a ojo.

    La matriz define los cinco tipos y los cinco estados, pero **no dice cual es cada regla**. Rellenarlos
    seria inventar una clasificacion legal, y presentar una recomendacion tecnica como una obligacion es justo
    lo que la matriz pide que no se haga.
    """
    for una in normativa.LAS_REGLAS:
        assert una.tipo == "", una.codigo
        assert una.estado == "", una.codigo


def test_los_avisos_de_la_matriz_siguen_dentro_del_texto():
    """Los avisos van dentro del texto, y no se separan: son lo que mas duele si se pierde."""
    por_codigo = {una.codigo: una for una in normativa.LAS_REGLAS}
    assert "no copiar porcentajes" in por_codigo["N01"].texto.lower()
    # Y N09 avisa de que son **dos obligaciones diferentes**: eso no se puede perder.
    assert "dos obligaciones diferentes" in por_codigo["N09"].texto.lower()


def test_una_regla_con_varias_normas_las_trae_todas():
    """N03, N05, N06, N07, N09 y N10 citan varias: si solo se guardara la primera, la pantalla mentiria."""
    por_codigo = {una.codigo: una for una in normativa.LAS_REGLAS}
    for codigo in ("N03", "N05", "N06", "N07", "N09", "N10"):
        assert len(por_codigo[codigo].fuentes) >= 2, codigo

def test_cada_regla_tiene_su_ayuda_y_sin_markdown():
    """**Lo que se le enseña al agricultor** (07/10/2026): la matriz es documentacion de trabajo -«Implementar
    tres ejes independientes», «Prueba:», «IUWS no condiciona la navegacion del CRM»- y eso no se le puede
    poner delante. Cada regla lleva su ayuda, escrita para el, y **sin Markdown visible**: los enlaces viven en
    `fuentes`, que es donde la pantalla los pinta.
    """
    for una in normativa.LAS_REGLAS:
        assert una.ayuda.strip(), una.codigo
        assert "**" not in una.ayuda, una.codigo
        assert "](" not in una.ayuda, una.codigo
        assert "Prueba:" not in una.ayuda, una.codigo
        assert "Implementar" not in una.ayuda, una.codigo
        assert "CRM" not in una.ayuda, una.codigo
