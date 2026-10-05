"""Geografía: centros de parcela y distancia entre parcelas.

Lo que se comprueba aquí es lo que decide si dos parcelas se pueden agrupar para
ahorrarle apuntes al agricultor.

Y desde T05 (02/10/2026), también **medir una forma**: su área, por dónde pasa y si dos trozos se
pisan. Eso es lo que alimenta el área de la geometría de cada versión del recinto y el aviso de
solapes, así que la comprobación que más importa de todo el fichero es la primera: el área de un
recinto **de verdad**, el que publica el SIGPAC con su superficie oficial al lado.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import geo

RAIZ = Path(__file__).resolve().parents[2]

CUADRADO_PEQUENO = (
    "POLYGON((-5.0000 40.0000, -5.0010 40.0000, -5.0010 40.0010, -5.0000 40.0010, "
    "-5.0000 40.0000))"
)


class TestCentroide:
    def test_lee_el_centro_de_un_poligono(self):
        centro = geo.centroide_wkt(CUADRADO_PEQUENO)
        assert centro is not None
        assert centro[0] == pytest.approx(-5.0005, abs=1e-4)
        assert centro[1] == pytest.approx(40.0005, abs=1e-4)

    def test_sin_geometria_no_hay_centro(self):
        assert geo.centroide_wkt(None) is None
        assert geo.centroide_wkt("") is None

    def test_texto_que_no_es_una_geometria_no_revienta(self):
        assert geo.centroide_wkt("esto no es una parcela") is None


class TestDistancias:
    def test_un_grado_de_latitud_son_unos_111_km(self):
        distancia = geo.distancia_km((0.0, 0.0), (0.0, 1.0))
        assert distancia == pytest.approx(111.19, abs=0.5)

    def test_la_distancia_es_simetrica(self):
        a, b = (-5.0, 40.0), (-6.0, 41.0)
        assert geo.distancia_km(a, b) == pytest.approx(geo.distancia_km(b, a))

    def test_el_mismo_punto_esta_a_cero(self):
        assert geo.distancia_km((-5.0, 40.0), (-5.0, 40.0)) == pytest.approx(0.0, abs=1e-9)


class TestCercania:
    def test_dos_parcelas_juntas_se_pueden_agrupar(self):
        assert geo.estan_cerca((-5.0005, 40.0005), (-5.002, 40.002))

    def test_dos_parcelas_lejos_no_se_agrupan(self):
        # Un grado de longitud a esta latitud son unos 85 km: pasa del radio de 8 km.
        assert not geo.estan_cerca((-5.0, 40.0), (-6.0, 40.0))

    def test_sin_coordenadas_se_prefiere_ofrecer_el_grupo(self):
        # Es preferible proponer un grupo que el agricultor puede revisar a negarle
        # la función porque no dibujó la parcela.
        assert geo.estan_cerca(None, (-5.0, 40.0))
        assert geo.estan_cerca(None, None)

    def test_el_radio_que_fija_la_aplicacion_oficial(self):
        assert geo.RADIO_UHC_KM == 8.0


# --------------------------------------------------------------------------
# Medir una forma (T05, 02/10/2026)
# --------------------------------------------------------------------------


def _el_recinto_de_ejemplo_del_sigpac() -> dict:
    """El recinto que el SIGPAC publica como ejemplo, con su WKT y su superficie oficial.

    Es la respuesta de verdad que se guardó el día que se escribió el conector
    (`data/sigpac/recinto_de_ejemplo.json`, ver `data/sigpac/LEEME.md`) y trae las dos cosas que
    hacen falta para comprobar una medida: **la forma** y **la superficie que dice el SIGPAC**
    (2,7923 ha). Probar el área contra un polígono inventado por nosotros solo demostraría que
    somos coherentes con nosotros mismos.
    """
    return json.loads(
        (RAIZ / "data" / "sigpac" / "recinto_de_ejemplo.json").read_text(encoding="utf-8")
    )[0]


CUADRADO_DE_UNOS_100_M = (
    "POLYGON((-5.0 41.0, -4.999 41.0, -4.999 41.001, -5.0 41.001, -5.0 41.0))"
)
CUADRADO_QUE_PISA_AL_ANTERIOR = (
    "POLYGON((-4.9995 41.0005, -4.9985 41.0005, -4.9985 41.0015, -4.9995 41.0015, "
    "-4.9995 41.0005))"
)
CUADRADO_LEJOS = "POLYGON((-4.99 41.0, -4.989 41.0, -4.989 41.001, -4.99 41.001, -4.99 41.0))"


class TestElAreaDeUnaForma:
    def test_el_area_del_recinto_de_ejemplo_cuadra_con_la_que_dice_el_sigpac(self):
        """**La comprobación que da valor a todas las demás.**

        El SIGPAC publica de ese recinto su forma y su superficie: 2,7923 ha. El área de su WKT sale
        2,788534 ha, un **0,13 % menos**. Es el error que se espera de medir sobre un plano local en
        vez de sobre el elipsoide, y el margen que se exige aquí es ese mismo (medio punto
        porcentual), no uno puesto a ojo: si algún día se cambia la forma de medir, esta prueba es la
        que avisa de que el número ha dejado de cuadrar con el oficial.
        """
        recinto = _el_recinto_de_ejemplo_del_sigpac()
        area = geo.area_ha(recinto["wkt"])
        assert area is not None
        oficial = recinto["superficie"]
        assert area == pytest.approx(oficial, rel=0.005), (
            f"el área medida ({area} ha) se separa más de medio punto de la oficial ({oficial} ha)"
        )
        # Y se dice el número medido, que es el que está escrito en la documentación de T05.
        assert area == pytest.approx(2.788534, abs=1e-5)

    def test_un_cuadrado_de_unos_cien_metros_mide_lo_que_tiene_que_medir(self):
        # 0,001° de latitud son 111,3 m y de longitud, 111,3 × cos(41°) = 84,0 m: 0,935 ha.
        area = geo.area_ha(CUADRADO_DE_UNOS_100_M)
        assert area == pytest.approx(0.9331, abs=0.002)

    def test_los_trozos_de_un_multiparte_se_suman(self):
        uno = geo.area_ha(CUADRADO_DE_UNOS_100_M)
        dos = geo.area_ha(
            "MULTIPOLYGON(((-5.0 41.0,-4.999 41.0,-4.999 41.001,-5.0 41.001,-5.0 41.0)),"
            "((-4.99 41.0,-4.989 41.0,-4.989 41.001,-4.99 41.001,-4.99 41.0)))"
        )
        assert dos == pytest.approx(uno * 2, rel=1e-6)

    def test_un_agujero_resta_y_no_depende_de_como_esten_dibujados_los_anillos(self):
        """Los anillos se suman **por profundidad**, no por hacia dónde apunten.

        Es lo que hace que el área salga bien venga la geometría de donde venga: el SIGPAC, el
        Catastro y el cuaderno de la Junta no tienen por qué dibujar los anillos en el mismo sentido,
        y un agujero tiene que restar siempre.
        """
        con_hueco = (
            "POLYGON((-5.0 41.0,-4.99 41.0,-4.99 41.01,-5.0 41.01,-5.0 41.0),"
            "(-4.996 41.004,-4.994 41.004,-4.994 41.006,-4.996 41.006,-4.996 41.004))"
        )
        al_reves = (
            "POLYGON((-5.0 41.0,-5.0 41.01,-4.99 41.01,-4.99 41.0,-5.0 41.0),"
            "(-4.996 41.004,-4.996 41.006,-4.994 41.006,-4.994 41.004,-4.996 41.004))"
        )
        entero = geo.area_ha("POLYGON((-5.0 41.0,-4.99 41.0,-4.99 41.01,-5.0 41.01,-5.0 41.0))")
        assert geo.area_ha(con_hueco) == pytest.approx(geo.area_ha(al_reves))
        assert geo.area_ha(con_hueco) < entero

    def test_sin_forma_no_hay_area_y_nunca_es_cero(self):
        """Lo que no se puede medir se queda en blanco: **un cero sería decir que no tiene tierra**.

        Es el hallazgo A7 de `docs/T02_VALORES_POR_DEFECTO.md`, aplicado a la medida de una forma:
        un punto, una línea, un texto vacío o algo que no se entiende no miden cero hectáreas.
        """
        for nada in (None, "", "POINT(-5.0 41.0)", "LINESTRING(-5.0 41.0, -4.9 41.1)", "vaya"):
            assert geo.area_ha(nada) is None, f"«{nada}» no puede medir cero hectáreas"


class TestPorDondePasaUnaForma:
    def test_un_punto_dentro_y_un_punto_fuera(self):
        assert geo.punto_dentro_del_wkt(CUADRADO_DE_UNOS_100_M, -4.9995, 41.0005) is True
        assert geo.punto_dentro_del_wkt(CUADRADO_DE_UNOS_100_M, -4.9, 41.0) is False

    def test_sin_forma_no_se_puede_decir_ni_si_ni_no(self):
        """Los tres finales: sí, no y **no lo he podido comprobar**, que no es «no»."""
        assert geo.punto_dentro_del_wkt(None, -5.0, 41.0) is None
        assert geo.punto_dentro_del_wkt("POINT(-5.0 41.0)", -5.0, 41.0) is None

    def test_el_rectangulo_que_envuelve_una_forma(self):
        rectangulo = geo.rectangulo_de_un_wkt(CUADRADO_DE_UNOS_100_M)
        assert rectangulo == pytest.approx((-5.0, 41.0, -4.999, 41.001))
        assert geo.rectangulo_de_un_wkt(None) is None


class TestSiDosTrozosSePisan:
    def test_dos_formas_que_se_pisan_se_dicen_que_si(self):
        assert geo.se_solapan(CUADRADO_DE_UNOS_100_M, CUADRADO_QUE_PISA_AL_ANTERIOR) == (
            geo.SOLAPE_SEGURO
        )

    def test_dos_formas_lejos_se_dicen_que_no(self):
        assert geo.se_solapan(CUADRADO_DE_UNOS_100_M, CUADRADO_LEJOS) == geo.SOLAPE_NO

    def test_sin_forma_no_se_puede_saber(self):
        assert geo.se_solapan(None, CUADRADO_DE_UNOS_100_M) == geo.SOLAPE_NO_SE

    def test_dos_formas_que_se_cruzan_como_una_cruz_dicen_que_puede(self):
        """El tercer final, y por qué existe.

        Dos rectángulos cruzados no tienen ningún vértice dentro del otro, así que no se puede
        decir «se pisan» mirando vértices, y tampoco se puede decir «no se pisan», porque sí se
        pisan. La respuesta honesta es **«puede»**, y el contrato pide exactamente eso: avisar para
        que se mire, sin corregirlo por su cuenta.
        """
        ancho = "POLYGON((-5.0 41.0,-4.9 41.0,-4.9 41.01,-5.0 41.01,-5.0 41.0))"
        alto = "POLYGON((-4.96 40.99,-4.95 40.99,-4.95 41.02,-4.96 41.02,-4.96 40.99))"
        assert geo.se_solapan(ancho, alto) == geo.SOLAPE_POSIBLE
