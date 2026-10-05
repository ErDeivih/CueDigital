"""El cruce entre los catálogos que pide el descriptor y los que publica SIEX.

Lo que se prueba aquí es una sola idea, y es la que evita el error caro: **una correspondencia
solo vale si los dos nombres son exactamente iguales**. Parecerse no es ser. Un catálogo
equivocado no da error al mandarlo: guarda el producto equivocado.

Por eso hay un test que recorre todas las correspondencias y comprueba, una por una, que el
nombre del descriptor y el de la tabla de SIEX coinciden de verdad. Si alguien mete un emparejado
«a ojo», ese test se pone en rojo.
"""

from __future__ import annotations

import json
from pathlib import Path

from app import catalogos_siex, iuws_descriptor

RAIZ = Path(__file__).resolve().parents[2]


class TestElInventario:
    def test_se_carga_el_inventario_del_proyecto(self):
        assert catalogos_siex.cargada() is True
        assert len(catalogos_siex.inventario()["catalogos"]) == 287

    def test_el_fichero_dice_de_donde_sale_y_que_no_son_los_valores(self):
        """Nadie puede confundir esto con los códigos: son los nombres de las tablas."""
        datos = json.loads(catalogos_siex.RUTA.read_text(encoding="utf-8"))
        assert "DERIVADO" in datos["_leeme"]
        assert "captcha" in datos["_leeme"]
        assert datos["direccion"].startswith("https://www3.sede.fega.gob.es")

    def test_sin_inventario_se_dice_que_no_esta_y_no_se_inventa_nada(self, tmp_path):
        catalogos_siex.olvidar()
        try:
            assert catalogos_siex.cargar(tmp_path / "no-existe.json") is None
            assert catalogos_siex.cargada() is False
            assert catalogos_siex.catalogo_de_siex("Plagas") is None
            assert catalogos_siex.catalogos_publicos() == ()
            resumen = catalogos_siex.resumen()
            assert resumen["cargado"] is False
            assert "bajar_catalogos_siex" in resumen["por_que_no"]
        finally:
            catalogos_siex.olvidar()
            catalogos_siex.cargar()

    def test_un_fichero_ilegible_no_revienta(self, tmp_path):
        roto = tmp_path / "roto.json"
        roto.write_text("{ esto no es json", encoding="utf-8")
        catalogos_siex.olvidar()
        try:
            assert catalogos_siex.cargar(roto) is None
        finally:
            catalogos_siex.olvidar()
            catalogos_siex.cargar()


class TestLasCorrespondenciasSonExactas:
    def test_todas_las_correspondencias_lo_son_de_verdad(self):
        """El test que impide el emparejado por parecido, que es lo que no se puede hacer.

        Se recorre el cruce entero y se comprueba que, en cada renglón emparejado, el nombre que
        usa el descriptor y el de la tabla de SIEX son iguales (sin mayúsculas ni acentos).
        """
        emparejados = [r for r in catalogos_siex.el_cruce() if r["tabla_de_siex"]]
        assert emparejados, "sin correspondencias, este módulo no sirve para nada"
        for renglon in emparejados:
            tabla = catalogos_siex.catalogo_de_siex(renglon["descriptor"])
            assert tabla is not None
            assert catalogos_siex.normaliza(tabla["nombre"]) == catalogos_siex.normaliza(
                renglon["descriptor"]
            ), f"{renglon['descriptor']!r} no coincide exactamente"

    def test_los_parecidos_no_se_emparejan(self):
        """El caso que da sentido a todo esto: `tipos de producto` **no** es `TIPO_PRODFITO`.

        Se parecen, y no se puede afirmar que sean lo mismo. El día que FEGA lo diga, se apunta;
        hoy no se apunta, y el programa lo dice en vez de suponerlo.
        """
        assert catalogos_siex.catalogo_de_siex("tipos de producto") is None
        assert catalogos_siex.catalogo_de_siex("Plagas") is None
        # Y para que se vea que el parecido existe de verdad, se comprueba que la tabla
        # parecida está en el inventario: el que no se empareje no es por no tenerla.
        assert catalogos_siex.catalogo_de_siex("tipo de producto fitosanitario") is not None

    def test_la_eficacia_del_tratamiento_si_tiene_tabla(self):
        """Era la laguna apuntada como «ese catálogo no existe»: existe, con ese nombre."""
        tabla = catalogos_siex.catalogo_de_siex("Eficacia del tratamiento")
        assert tabla is not None
        assert tabla["id"] == "EFICACIA_TRATAMIENTO"
        assert tabla["publico"] is True

    def test_las_que_coinciden_son_publicas(self):
        """Si alguna no fuera pública, no se podría ni pedir: se dice en el renglón."""
        for renglon in catalogos_siex.el_cruce():
            if renglon["tabla_de_siex"]:
                assert renglon["publica"] is True, renglon

    def test_un_nombre_vacio_o_inexistente_no_devuelve_nada(self):
        for nombre in ("", "   ", "Catálogo que no existe"):
            assert catalogos_siex.catalogo_de_siex(nombre) is None


class TestElResumen:
    def test_cuadra_y_dice_los_dos_grupos(self):
        resumen = catalogos_siex.resumen()
        assert resumen["cargado"] is True
        assert resumen["catalogos_de_siex"] == 287
        assert len(resumen["el_cruce"]) == resumen["coinciden_exactamente"]
        assert len(resumen["los_que_no_coinciden"]) == resumen["sin_coincidencia"]
        assert (
            resumen["coinciden_exactamente"] + resumen["sin_coincidencia"]
            == len(iuws_descriptor.catalogos_que_pide())
        )

    def test_los_que_no_coinciden_son_los_que_hay_que_preguntar(self):
        resumen = catalogos_siex.resumen()
        assert "tipos de producto" in resumen["los_que_no_coinciden"]
        assert "Plagas" in resumen["los_que_no_coinciden"]
        # Y estos ya no hay que preguntarlos: se sabe a qué tabla van.
        assert "Eficacia del tratamiento" not in resumen["los_que_no_coinciden"]
        assert "Unidades de Medida" not in resumen["los_que_no_coinciden"]
