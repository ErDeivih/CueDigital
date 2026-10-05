"""Elegir la parcela desde el mapa, y lo que el SIGPAC sabe de esa tierra.

**Por qué existe este fichero.** El agricultor no se sabe sus códigos. Lo que sabe es dónde está
su tierra: la reconoce en una foto aérea y la señala con el dedo. Para eso hacen falta las
consultas del SIGPAC que trabajan **por coordenadas** y las que **cruzan un recinto con las capas
oficiales**, y este fichero comprueba las dos cosas contra respuestas de verdad del servicio,
guardadas en `data/sigpac/` (los tests no salen a internet).

Las direcciones y el significado de cada campo salen de la documentación del propio FEGA, el
catálogo de servicios del SIGPAC (`https://sigpac-hubcloud.es/`), que tiene una página de ejemplo
por consulta. Lo que se comprueba aquí, y de dónde sale:

* `query/recinfobypoint/[srid]/[x]/[y]` — las propiedades del recinto que **contiene** un punto.
  Es «tocar el mapa».
* `query/refrecinbycoord/[srid]/[x]/[y]` — solo su referencia.
* `query/refcatparcela/[pr]/[mu]/[ag]/[zo]/[po]/[pa]` — la **referencia catastral** de la
  parcela, que el contenido mínimo del CUE pide por su nombre y que hasta ahora solo se guardaba
  si el agricultor la pegaba a mano.
* `query/recinfoparc/[pr]/[mu]/[ag]/[zo]/[po]/[pa]` — todos los recintos de una parcela.
* `intersection/nitratos/[...]` — si el recinto está en zona vulnerable a nitratos **de verdad**,
  por cruce con la capa oficial, y no deducido del municipio. Lo mismo con Red Natura, montanera,
  fitosanitarios y pastos permanentes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import sigpac

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data" / "sigpac"

# El punto que se comprobó contra el servicio: cae dentro de la parcela 503/53, que es la vecina
# de la del agricultor (la 51). Se guarda así, tal y como salió, porque enseña una cosa que hay
# que tener presente al hacer el mapa: **un punto justo en una linde es de la parcela de al lado**,
# y por eso la pantalla tiene que enseñar qué trozo ha encontrado y su superficie antes de darlo
# de alta.
PUNTO_COMPROBADO = (-5.55470, 40.90730)
RECINTO_DEL_PUNTO = "37:70:0:0:503:53:1"
RECINTO_DEL_AGRICULTOR = "37-70-0-0-503-51-1"
SU_REFERENCIA_CATASTRAL = "37070A503000510000AQ"


def _respuesta(nombre: str):
    return json.loads((DATOS / nombre).read_text(encoding="utf-8"))


class TestLasDireccionesDeLasConsultas:
    """Las direcciones tienen que ser las de la documentación, no unas que «funcionen».

    Si alguien las cambia por parecidas y el servicio contesta otra cosa, los datos que se
    guardarían serían de otra parcela, y eso no se nota hasta que el agricultor lo mira.
    """

    def test_las_propiedades_del_recinto_de_un_punto(self):
        url = sigpac.url_recinto_por_punto(*PUNTO_COMPROBADO)
        assert url == (
            "https://sigpac-hubcloud.es/servicioconsultassigpac/query/"
            "recinfobypoint/4326/-5.5547/40.9073.json"
        )

    def test_la_referencia_del_recinto_de_un_punto(self):
        url = sigpac.url_referencia_por_punto(*PUNTO_COMPROBADO)
        assert url.endswith("/query/refrecinbycoord/4326/-5.5547/40.9073.json")

    def test_se_puede_pedir_en_otro_sistema_de_referencia(self):
        """El navegador da grados (4326), pero el servicio admite el oficial (4258)."""
        assert "/refrecinbycoord/4258/" in sigpac.url_referencia_por_punto(-5.5, 40.9, srid=4258)

    def test_la_referencia_catastral_de_una_parcela(self):
        busqueda = sigpac.Busqueda(provincia=37, municipio=70, poligono=503, parcela=51)
        assert sigpac.url_referencia_catastral(busqueda).endswith(
            "/query/refcatparcela/37/70/0/0/503/51.json"
        )

    def test_todos_los_recintos_de_una_parcela(self):
        busqueda = sigpac.Busqueda(provincia=37, municipio=70, poligono=503, parcela=51)
        assert sigpac.url_recintos_de_la_parcela(busqueda).endswith(
            "/query/recinfoparc/37/70/0/0/503/51.json"
        )

    def test_la_interseccion_con_una_capa(self):
        referencia = sigpac.lee_referencia(RECINTO_DEL_AGRICULTOR)
        assert sigpac.url_interseccion("nitratos", referencia).endswith(
            "/intersection/nitratos/37/70/0/0/503/51/1.json"
        )
        assert sigpac.url_interseccion("red_natura", referencia).endswith(
            "/intersection/red_natura/37/70/0/0/503/51/1.json"
        )
        assert sigpac.url_interseccion("pastos", referencia).endswith(
            "/intersection/pastos/37/70/0/0/503/51/1.json"
        )

    def test_una_capa_que_no_existe_se_dice_en_vez_de_inventarse_la_direccion(self):
        referencia = sigpac.lee_referencia(RECINTO_DEL_AGRICULTOR)
        with pytest.raises(ValueError):
            sigpac.url_interseccion("inventada", referencia)

    def test_las_cinco_capas_son_las_que_publica_el_sigpac(self):
        assert sigpac.CAPAS_DE_INTERSECCION == (
            "nitratos",
            "red_natura",
            "montanera",
            "fitosanitarios",
            "pastos",
        )


class TestTocarElMapa:
    """El punto que toca el agricultor tiene que dar con su tierra."""

    def test_se_leen_las_propiedades_del_recinto_que_contiene_el_punto(self):
        recinto = sigpac.lee_recinto(_respuesta("recinto_de_un_punto.json"))
        assert recinto is not None
        assert recinto.ref_sigpac == "37-70-0-0-503-53-1"
        assert recinto.superficie == 9.055
        assert recinto.uso_sigpac == "TA"
        assert recinto.pendiente_media == 1.2
        assert recinto.wkt, "con el dibujo, para poder pintarlo en el mapa"

    def test_y_su_referencia_a_secas(self):
        referencias = sigpac.lee_referencias(_respuesta("referencia_de_un_punto.json"))
        assert [r.como_texto() for r in referencias] == ["37-70-0-0-503-53-1"]

    def test_el_recinto_que_devuelve_es_el_que_contiene_el_punto_no_el_de_al_lado(self):
        """Comprobado contra el servicio: ese punto cae en la 53 y **no** en la 51 del agricultor.

        Es la razón de que la pantalla del mapa tenga que enseñar **qué trozo ha encontrado y su
        superficie** antes de darlo de alta: en una linde, un dedo al lado equivocado es otra
        parcela, y quien lo sabe es el agricultor.
        """
        recinto = sigpac.lee_recinto(_respuesta("recinto_de_un_punto.json"))
        assert recinto.parcela == 53
        suya = sigpac.lee_recinto(_respuesta("recinto_de_ejemplo_503_51.json"))
        assert suya.parcela == 51
        assert suya.superficie == 4.9016

    def test_una_respuesta_que_no_se_entiende_no_revienta(self):
        assert sigpac.lee_referencias("no es json") == []
        assert sigpac.lee_referencias([{"sin_referencia": 1}]) == []
        assert sigpac.lee_referencias([{"refrecinto": "37:70"}]) == []
        # Un diccionario sin datos no da un error: da un recinto sin referencia, y quien llama
        # mira eso mismo para saber que ahí no hay nada.
        assert sigpac.lee_recinto({"nada": 1}).ref_sigpac == ""

    def test_si_no_hay_recinto_en_ese_punto_se_dice_que_no_hay_nada(self):
        """Un camino, un pueblo o el monte: ahí no hay recinto, y eso no es un fallo."""
        assert sigpac.lee_recinto("[]") is None


class TestLaReferenciaCatastralLaPoneElSigpac:
    """El dato que el contenido mínimo pide y que el agricultor casi nunca tiene a mano."""

    def test_se_lee_la_referencia_de_la_parcela_del_agricultor(self):
        referencia = sigpac.lee_referencia_catastral_de_una_parcela(
            _respuesta("referencia_catastral_de_la_parcela.json")
        )
        assert referencia == SU_REFERENCIA_CATASTRAL
        assert len(referencia) == 20, "la referencia catastral de rústica tiene 20 caracteres"

    def test_su_reparto_de_cifras_cuadra_con_la_parcela(self):
        """Y cuadra con lo que ya sabíamos: la provincia, el municipio, el polígono y la parcela.

        Es la comprobación que une las tres fuentes: el visor del SIGPAC (`37:70:0:0:503:51`), la
        Sede del Catastro y esta consulta. Si algún día dejaran de cuadrar, esto salta.
        """
        crudo = sigpac.lee_referencia_catastral_de_una_parcela(
            _respuesta("referencia_catastral_de_la_parcela.json")
        )
        catastral = sigpac.lee_referencia_catastral(crudo)
        assert catastral is not None
        assert (catastral.provincia, catastral.municipio) == (37, 70)
        assert (catastral.poligono, catastral.parcela) == (503, 51)

    def test_sin_referencia_se_devuelve_nada(self):
        assert sigpac.lee_referencia_catastral_de_una_parcela("[]") is None
        assert sigpac.lee_referencia_catastral_de_una_parcela([{"provincia": 37}]) is None
        assert sigpac.lee_referencia_catastral_de_una_parcela("no es json") is None


class TestLaZonaDeNitratosDeVerdad:
    """Por cruce con la capa oficial, que es distinto de mirarlo por el municipio.

    La lista de municipios dice que el **pueblo** está en una zona declarada. Esto dice si
    **este trozo de tierra** cae dentro, y cuánto de él: hay recintos que solo están dentro a
    medias, y eso se le tiene que poder decir al agricultor.
    """

    def test_un_recinto_que_no_esta_en_zona(self):
        """La parcela del agricultor: la consulta devuelve una lista vacía, y eso es un dato."""
        intersecciones = sigpac.lee_interseccion(_respuesta("interseccion_nitratos_no.json"))
        assert intersecciones == []

    def test_un_recinto_que_si_esta(self):
        intersecciones = sigpac.lee_interseccion(_respuesta("interseccion_nitratos_si.json"))
        assert len(intersecciones) == 1
        una = intersecciones[0]
        assert una.referencia.como_texto() == "5-36-0-0-6-5015-3"
        assert una.superficie_m2 == pytest.approx(555.5924290957715)
        assert una.porcentaje == 100.0

    def test_la_decision_con_la_capa_oficial(self, monkeypatch):
        """`zona_de_nitratos` devuelve las dos cosas: si está y cuánto de él está."""
        import httpx

        class Respuesta:
            status_code = 200

            def __init__(self, cuerpo):
                self.text = json.dumps(cuerpo)

        def con_nitratos(url, **kwargs):
            return Respuesta(_respuesta("interseccion_nitratos_si.json"))

        def sin_nitratos(url, **kwargs):
            return Respuesta(_respuesta("interseccion_nitratos_no.json"))

        referencia = sigpac.lee_referencia(RECINTO_DEL_AGRICULTOR)
        monkeypatch.setattr(httpx, "get", sin_nitratos)
        assert sigpac.zona_de_nitratos(referencia) == (False, 0.0)

        monkeypatch.setattr(httpx, "get", con_nitratos)
        en_zona, porcentaje = sigpac.zona_de_nitratos(referencia)
        assert en_zona is True
        assert porcentaje == 100.0

    def test_una_interseccion_a_medias_se_lee_con_su_porcentaje(self):
        """El caso que hay que saber contar: solo una parte del trozo está dentro de la zona.

        Este ejemplo es el de la **documentación oficial** (su página de la consulta de nitratos),
        puesto aquí a propósito para dejar escrito que `surface_tpc` es un porcentaje y puede no
        ser 100, y que entonces no se puede decir un «sí» redondo sin más.
        """
        cuerpo = [
            {
                "provincia": 45,
                "municipio": 115,
                "agregado": 0,
                "zona": 0,
                "poligono": 18,
                "parcela": 10,
                "recinto": 2,
                "surface_intersection": 9155.648977209576,
                "surface_tpc": 1.8097449219724349,
            }
        ]
        una = sigpac.lee_interseccion(cuerpo)[0]
        assert una.porcentaje == pytest.approx(1.8097, abs=1e-3)
        assert 0 < una.porcentaje < 100

    def test_una_respuesta_rara_no_revienta(self):
        """Y lo más importante: una respuesta que no se entiende **no** es un «no está».

        Si el servicio contestara otra cosa (o contestara la respuesta de otra consulta), tomar
        eso por una lista vacía haría que el programa dijera «tu parcela no está en zona de
        nitratos» sin saberlo. Por eso se devuelve `None`, que es «no lo sé».
        """
        assert sigpac.lee_interseccion("no es json") is None
        assert sigpac.lee_interseccion([{"sin_provincia": 1}]) is None
        assert sigpac.lee_interseccion({"provincia": "no es un número"}) is None
        # Y con la respuesta de OTRA consulta (la de un recinto) tampoco se inventa nada.
        assert sigpac.lee_interseccion(_respuesta("recinto_de_ejemplo_503_51.json")) is None

    def test_si_la_respuesta_no_se_entiende_no_se_dice_que_no_esta(self, monkeypatch):
        import httpx

        class Respuesta:
            status_code = 200
            text = "esto no es lo que esperaba"

        monkeypatch.setattr(httpx, "get", lambda url, **k: Respuesta())
        referencia = sigpac.lee_referencia(RECINTO_DEL_AGRICULTOR)
        assert sigpac.zona_de_nitratos(referencia) is None, "no se sabe, y eso hay que decirlo"


class TestLasImagenesDelMapa:
    """La foto del campo y los linderos, que son lo que el agricultor reconoce.

    Los dos servicios son WMS 1.3.0, y con `EPSG:4326` la caja va **latitud primero**. Equivocar
    ese orden no da un error: da otra zona del país, y el agricultor vería una foto que no es la
    suya. Por eso se comprueba con números.
    """

    def test_la_caja_va_con_la_latitud_primero(self):
        url = sigpac.url_imagen_del_mapa("foto", oeste=-5.56, sur=40.90, este=-5.55, norte=40.91,
                                        ancho=800, alto=600)
        assert "bbox=40.9,-5.56,40.91,-5.55" in url, url
        assert "crs=EPSG:4326" in url
        assert "version=1.3.0" in url

    def test_la_foto_es_del_ign_y_va_en_jpeg(self):
        url = sigpac.url_imagen_del_mapa("foto", -5.56, 40.90, -5.55, 40.91, 800, 600)
        assert url.startswith("https://www.ign.es/wms-inspire/pnoa-ma?")
        assert "layers=OI.OrthoimageCoverage" in url
        assert "format=image/jpeg" in url
        assert "transparent" not in url, "la foto es el fondo: no se pide transparente"

    def test_los_linderos_son_del_sigpac_y_van_transparentes(self):
        url = sigpac.url_imagen_del_mapa("linderos", -5.56, 40.90, -5.55, 40.91, 800, 600)
        assert url.startswith("https://sigpac-hubcloud.es/wms?")
        assert "layers=recinto" in url
        assert "transparent=true" in url, "los linderos van encima de la foto"

    def test_el_tamano_tiene_tope(self):
        """Una imagen enorme tarda y gasta datos del agricultor sin darle nada mejor."""
        url = sigpac.url_imagen_del_mapa("foto", -5.56, 40.90, -5.55, 40.91, 99999, 99999)
        assert "width=1600" in url and "height=1600" in url

    def test_una_capa_de_mapa_que_no_existe_se_dice(self):
        with pytest.raises(ValueError):
            sigpac.url_imagen_del_mapa("inventada", -5.56, 40.90, -5.55, 40.91, 800, 600)


class TestLaPantallaDelMapa:
    """Los tres endpoints que usa la pantalla del mapa.

    **Cambio de contrato del 03/10/2026: `POST /api/mapa/punto` ahora pide sesión**, y por eso las
    pruebas del toque llevan `cuenta` y mandan su vale. Antes se servía sin sesión, y era la ruta
    que hacía **hasta tres llamadas de salida** (SIGPAC y Catastro, 10 s cada una) por cada toque,
    sin límite ni caché: cualquiera con la dirección podía usar esta instalación de repetidor
    contra dos servicios públicos (ver `docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.16 y §5.1).
    Cerrada no cambia nada para el agricultor: la pantalla ya mandaba su vale (`app.js:6771`, por
    `apiJson`, que siempre lo pone). El contrato nuevo —sin vale no se pregunta— tiene su prueba
    en `tests/test_lo_que_no_pide_sesion.py`.

    Las pruebas de `/api/mapa/imagen` **siguen sin sesión a propósito**: la pantalla la pide con
    un `<img src>` y un `<img>` no puede mandar cabeceras. Está declarado en esa misma prueba.
    """

    @pytest.fixture
    def sigpac_de_verdad(self, monkeypatch):
        """El SIGPAC de verdad sin salir a internet: responde lo que respondió, por consulta."""
        import httpx

        respuestas = {
            "recinfobypoint": "recinto_de_un_punto.json",
            "refrecinbycoord": "referencia_de_un_punto.json",
            "refcatparcela": "referencia_catastral_de_la_parcela.json",
            "recinfoparc": "recintos_de_la_parcela.json",
            "intersection/nitratos/37/70": "interseccion_nitratos_no.json",
            "intersection/nitratos/5/36": "interseccion_nitratos_si.json",
        }
        llamadas: list[str] = []

        class Respuesta:
            status_code = 200

            def __init__(self, cuerpo, tipo="application/json"):
                self.text = json.dumps(cuerpo) if not isinstance(cuerpo, str) else cuerpo
                self.content = self.text.encode()
                self.headers = {"content-type": tipo}

        def get_falso(url, **kwargs):
            llamadas.append(url)
            for trozo, fichero in respuestas.items():
                if trozo in url:
                    return Respuesta(_respuesta(fichero))
            if "/query/recinfo/" in url:
                return Respuesta(_respuesta("recinto_de_ejemplo_503_51.json"))
            return Respuesta([])

        monkeypatch.setattr(httpx, "get", get_falso)
        return llamadas

    def test_los_textos_del_mapa_llegan_a_la_pantalla(self, cliente):
        """Los textos del mapa tienen que servirse, y con las claves que usa la pantalla.

        Esto faltaba: los textos estaban escritos y **no se servían**, así que la pantalla habría
        salido con los botones en blanco. Los tests de JavaScript no lo cazaban porque usan sus
        propios textos de mentira; se caza aquí, preguntando a la interfaz de verdad.
        """
        interfaz = cliente.get("/api/interfaz").json()
        assert "mapa" in interfaz, "la interfaz no sirve los textos del mapa"
        mapa = interfaz["mapa"]
        for clave in (
            "titulo",
            "pista_mover",
            "necesita_conexion",
            "sin_conexion",
            "sin_centro",
            "sin_ubicacion",
            "acercar",
            "alejar",
            "estoy_aqui",
            "elegir_en_el_mapa",
            "poner_en_el_centro",
            "cargando",
            "encontrado_titulo",
            "pregunta",
            "no_hay_nada",
            "apuntarla",
            "no_es_mia",
            "superficie",
            "pueblo",
            "referencia_catastral",
            "zona_nitratos",
            "zona_nitratos_si",
            "zona_nitratos_parte",
            "zona_nitratos_no",
            "zona_nitratos_no_se",
            "la_foto",
            "los_linderos",
            "el_cultivo",
            "no_se_pudo_apuntar",
        ):
            assert mapa.get(clave), f"falta el texto del mapa «{clave}»"
        # Y las que la pantalla toma del SIGPAC (la referencia, el uso, el sistema y el nombre).
        for clave in ("referencia_como_sea", "uso", "sistema", "alias"):
            assert interfaz["sigpac"].get(clave), f"falta el texto del SIGPAC «{clave}»"

    def test_el_estado_dice_que_hay_detras_del_mapa(self, cliente):
        datos = cliente.get("/api/mapa/estado").json()
        assert set(datos["capas"]) == {"foto", "linderos", "cultivo"}
        assert datos["necesita_conexion"] is True
        assert "conexión" in datos["mensaje_sin_conexion"]
        assert "Creative Commons" in datos["licencia"]
        assert "IGN" in datos["licencia"] and "SIGPAC" in datos["licencia"]

    def test_la_imagen_se_sirve_desde_el_programa(self, cliente, monkeypatch):
        """El navegador no habla con el IGN: le pide la imagen a su propio programa."""
        import httpx

        png = b"\x89PNG\r\n\x1a\n" + b"datos de mentira"

        class Respuesta:
            status_code = 200
            content = png
            headers = {"content-type": "image/png"}

        llamadas: list[str] = []

        def get_falso(url, **kwargs):
            llamadas.append(url)
            return Respuesta()

        monkeypatch.setattr(httpx, "get", get_falso)
        sigpac.olvidar_las_imagenes()
        respuesta = cliente.get(
            "/api/mapa/imagen",
            params={"capa": "linderos", "oeste": -5.56, "sur": 40.90, "este": -5.55, "norte": 40.91},
        )
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"].startswith("image/png")
        assert respuesta.content == png
        assert "max-age" in respuesta.headers.get("cache-control", "")
        assert sigpac.url_imagen_del_mapa("linderos", -5.56, 40.90, -5.55, 40.91, 900, 600) == llamadas[0]

    def test_la_misma_imagen_no_se_pide_dos_veces(self, cliente, monkeypatch):
        """Mover el mapa y volver pide lo mismo: el programa se lo queda un rato."""
        import httpx

        class Respuesta:
            status_code = 200
            content = b"\x89PNG\r\n\x1a\n" + b"x"
            headers = {"content-type": "image/png"}

        llamadas: list[str] = []
        monkeypatch.setattr(httpx, "get", lambda url, **k: (llamadas.append(url), Respuesta())[1])
        sigpac.olvidar_las_imagenes()
        parametros = {"capa": "foto", "oeste": -5.56, "sur": 40.90, "este": -5.55, "norte": 40.91}
        cliente.get("/api/mapa/imagen", params=parametros)
        cliente.get("/api/mapa/imagen", params=parametros)
        assert len(llamadas) == 1, f"se ha pedido dos veces: {llamadas}"

    def test_una_caja_al_reves_se_dice_en_vez_de_ensenar_otro_sitio(self, cliente):
        respuesta = cliente.get(
            "/api/mapa/imagen",
            params={"capa": "foto", "oeste": -5.55, "sur": 40.91, "este": -5.56, "norte": 40.90},
        )
        assert respuesta.status_code == 422
        assert "al revés" in respuesta.json()["detail"]

    def test_una_caja_demasiado_grande_se_rechaza(self, cliente):
        """Pedir media España en una imagen no da una imagen buena: se dice y que se aleje menos."""
        respuesta = cliente.get(
            "/api/mapa/imagen",
            params={"capa": "foto", "oeste": -8.0, "sur": 36.0, "este": 3.0, "norte": 44.0},
        )
        assert respuesta.status_code == 422
        assert "tamaño" in respuesta.json()["detail"]

    def test_si_el_servicio_de_mapas_no_contesta_se_dice(self, cliente, monkeypatch):
        import httpx

        def falla(url, **kwargs):
            raise httpx.ConnectError("sin red")

        monkeypatch.setattr(httpx, "get", falla)
        sigpac.olvidar_las_imagenes()
        respuesta = cliente.get(
            "/api/mapa/imagen",
            params={"capa": "foto", "oeste": -5.56, "sur": 40.90, "este": -5.55, "norte": 40.91},
        )
        assert respuesta.status_code == 503
        assert "conexión" in respuesta.json()["detail"]

    def test_si_el_servicio_contesta_algo_que_no_es_una_imagen_no_se_sirve(self, cliente, monkeypatch):
        """Un error del servicio en formato JSON no puede acabar dentro de un `<img>`."""
        import httpx

        class Respuesta:
            status_code = 200
            content = b'{"error": "vaya"}'
            headers = {"content-type": "application/json"}

        monkeypatch.setattr(httpx, "get", lambda url, **k: Respuesta())
        sigpac.olvidar_las_imagenes()
        respuesta = cliente.get(
            "/api/mapa/imagen",
            params={"capa": "foto", "oeste": -5.56, "sur": 40.90, "este": -5.55, "norte": 40.91},
        )
        assert respuesta.status_code == 503

    def test_tocar_el_mapa_devuelve_la_parcela_con_todo_lo_que_se_sabe(
        self, cliente, cuenta, sigpac_de_verdad
    ):
        respuesta = cliente.post(
            "/api/mapa/punto",
            headers=cuenta["cabeceras"],
            json={"x": -5.55470, "y": 40.90730},
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["encontrado"] is True
        assert datos["referencia"] == "37-70-0-0-503-53-1"
        assert datos["superficie_ha"] == 9.055
        assert datos["uso_sigpac"] == "TA"
        assert datos["uso"] == "TIERRAS ARABLES"
        assert datos["pendiente_pct"] == 1.2
        assert len(datos["puntos"]) > 3, "los vértices, para pintar la parcela encima del mapa"
        assert datos["municipio"]["nombre"] == "Calvarrasa de Arriba"
        assert datos["municipio"]["codigo_ine"] == "37070"
        assert datos["referencia_catastral"] == SU_REFERENCIA_CATASTRAL
        assert datos["en_zona_de_nitratos"] is False
        assert datos["zona_de_nitratos_porcentaje"] == 0.0

    def test_tocar_donde_no_hay_parcela_se_dice_con_palabras(self, cliente, cuenta, monkeypatch):
        import httpx

        class Vacia:
            status_code = 200
            text = "[]"
            content = b"[]"
            headers = {"content-type": "application/json"}

        monkeypatch.setattr(httpx, "get", lambda url, **k: Vacia())
        datos = cliente.post(
            "/api/mapa/punto",
            headers=cuenta["cabeceras"],
            json={"x": -5.5, "y": 40.9},
        ).json()
        assert datos["encontrado"] is False
        assert "no hay ninguna parcela" in datos["mensaje"]

    def test_un_toque_que_no_es_un_sitio_se_dice(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/mapa/punto",
            headers=cuenta["cabeceras"],
            json={"x": "por ahí", "y": 40.9},
        )
        assert respuesta.status_code == 422
        assert "dónde has tocado" in respuesta.json()["detail"]

        fuera = cliente.post(
            "/api/mapa/punto",
            headers=cuenta["cabeceras"],
            json={"x": 500.0, "y": 900.0},
        )
        assert fuera.status_code == 422
        assert "no son de ningún sitio" in fuera.json()["detail"]

    def test_si_el_sigpac_no_contesta_no_se_inventa_donde_esta(self, cliente, cuenta, monkeypatch):
        import httpx

        def falla(url, **kwargs):
            raise httpx.ConnectError("sin red")

        monkeypatch.setattr(httpx, "get", falla)
        respuesta = cliente.post(
            "/api/mapa/punto",
            headers=cuenta["cabeceras"],
            json={"x": -5.5547, "y": 40.9073},
        )
        assert respuesta.status_code == 503
        assert "conexión" in respuesta.json()["detail"]

    def test_si_la_zona_de_nitratos_no_se_entiende_no_se_dice_que_no_esta(
        self, cliente, cuenta, monkeypatch
    ):
        """El caso que importa: de la zona de nitratos dependen las reglas de abono.

        Si el cruce con la capa oficial contesta algo que no se entiende, la respuesta es «no se
        sabe» (nulo), y la pantalla lo dice. Poner un «no» sin comprobarlo sería afirmar algo
        sobre el abono de esa tierra que nadie ha mirado.
        """
        import httpx

        class Respuesta:
            def __init__(self, cuerpo):
                self.status_code = 200
                self.text = json.dumps(cuerpo) if not isinstance(cuerpo, str) else cuerpo
                self.content = self.text.encode()
                self.headers = {"content-type": "application/json"}

        def get_falso(url, **kwargs):
            if "intersection/nitratos" in url:
                return Respuesta("esto no es lo que esperaba")
            if "recinfobypoint" in url:
                return Respuesta(_respuesta("recinto_de_un_punto.json"))
            if "refcatparcela" in url:
                return Respuesta(_respuesta("referencia_catastral_de_la_parcela.json"))
            return Respuesta([])

        monkeypatch.setattr(httpx, "get", get_falso)
        datos = cliente.post(
            "/api/mapa/punto",
            headers=cuenta["cabeceras"],
            json={"x": -5.55470, "y": 40.90730},
        ).json()
        assert datos["encontrado"] is True
        assert datos["en_zona_de_nitratos"] is None, (
            "no se sabe, y eso es distinto de decir que no está"
        )


class TestLaParcelaSeRellenaConLoQueSabeElSigpac:
    """El alta de una parcela rellena lo que antes había que teclear, o no se rellenaba.

    Antes, una parcela traída del SIGPAC salía **sin pueblo y sin referencia catastral**, y la
    zona de nitratos se deducía del municipio o se quedaba en «no lo sé». Ahora el SIGPAC dice su
    pueblo (sus códigos son los del INE), su referencia catastral y si la tierra está en una zona
    vulnerable, por cruce con la capa oficial. Lo que no cambia es la regla de siempre: **si un
    dato no se sabe, no se afirma**.
    """

    @pytest.fixture
    def sigpac_de_verdad(self, monkeypatch):
        import httpx

        def get_falso(url, **kwargs):
            class Respuesta:
                status_code = 200

                def __init__(self, nombre):
                    self.text = (DATOS / nombre).read_text(encoding="utf-8")
                    self.content = self.text.encode()
                    self.headers = {"content-type": "application/json"}

            if "refcatparcela" in url:
                return Respuesta("referencia_catastral_de_la_parcela.json")
            if "intersection/nitratos" in url:
                return Respuesta("interseccion_nitratos_no.json")
            if "/query/recinfo/" in url:
                return Respuesta("recinto_de_ejemplo_503_51.json")
            return Respuesta("interseccion_nitratos_no.json")

        monkeypatch.setattr(httpx, "get", get_falso)

    def test_la_parcela_sale_con_su_pueblo_su_referencia_catastral_y_su_zona(
        self, cliente, cuenta, sigpac_de_verdad
    ):
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-70-0-0-503-51-1", "alias": "El llano"},
        )
        assert respuesta.status_code == 201, respuesta.text
        parcela = respuesta.json()
        assert parcela["ref_sigpac"] == "37-70-0-0-503-51-1"
        assert parcela["superficie_ha"] == 4.9016
        assert parcela["municipio"] == "Calvarrasa de Arriba", "de los códigos del recinto"
        assert parcela["provincia"] == "Salamanca"
        assert parcela["codigo_ine"] == "37070"
        assert parcela["referencia_catastral"] == SU_REFERENCIA_CATASTRAL, "la pone el SIGPAC"
        assert parcela["zona_vulnerable_nitratos"] is False, "la capa oficial dice que no está"
        assert parcela["agregado"] == 0 and parcela["zona"] == 0

    def test_la_referencia_catastral_que_pega_el_agricultor_manda(
        self, cliente, cuenta, sigpac_de_verdad
    ):
        """Si él la tiene en el papel, se guarda la suya: él es quien firma el cuaderno."""
        suya = "37070A50300051000AQ"
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={
                "ref_sigpac": "37-70-0-0-503-51-1",
                "referencia_catastral": suya,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["referencia_catastral"] == suya

    def test_si_la_capa_de_nitratos_no_se_entiende_se_cae_a_la_lista_del_pueblo(
        self, cliente, cuenta, monkeypatch
    ):
        """Sin poder cruzar con la capa oficial, se usa el listado de municipios, como antes.

        Y queda dicho de dónde sale: la lista dice si el **pueblo** está en zona declarada, así
        que la parcela se marca igual que se marcaba. Lo que nunca se hace es poner un «no» sin
        haberlo mirado.

        Ojo con la preparación: la suite de pruebas arranca **sin** el catálogo de zonas cargado
        (el `conftest` apunta su ruta a un fichero que no existe, para que las pruebas que
        comprueban la fuente oficial lo carguen ellas). Aquí se carga a mano, que es lo que hace
        el servidor de verdad al arrancar.
        """
        import httpx

        from app import catalogos
        from scripts import bajar_zonas_vulnerables_cyl as fuente

        def get_falso(url, **kwargs):
            class Respuesta:
                status_code = 200

                def __init__(self, nombre):
                    self.text = (DATOS / nombre).read_text(encoding="utf-8")
                    self.content = self.text.encode()
                    self.headers = {"content-type": "application/json"}

            if "intersection/nitratos" in url:
                return Respuesta("recinto_de_ejemplo_503_51.json")  # no es una intersección
            if "refcatparcela" in url:
                return Respuesta("referencia_catastral_de_la_parcela.json")
            return Respuesta("recinto_de_ejemplo_503_51.json")

        monkeypatch.setattr(httpx, "get", get_falso)
        monkeypatch.setattr(catalogos, "_RUTA_ZV_POR_DEFECTO", fuente.CSV)
        try:
            catalogos.cargar_zonas_vulnerables()
            # Un pueblo que SÍ está en el listado oficial de zonas vulnerables.
            respuesta = cliente.post(
                "/api/parcelas/desde-sigpac",
                headers=cuenta["cabeceras"],
                json={
                    "ref_sigpac": "37-70-0-0-503-51-1",
                    "municipio": "Peñaranda de Bracamonte",
                    "provincia": "Salamanca",
                },
            )
            assert respuesta.status_code == 201, respuesta.text
            assert respuesta.json()["zona_vulnerable_nitratos"] is True
        finally:
            catalogos.olvidar_zonas_vulnerables()

    def test_y_sin_listado_ni_capa_la_zona_queda_en_no_lo_se(
        self, cliente, cuenta, monkeypatch, tmp_path
    ):
        """El caso honesto: no se sabe, y se dice que no se sabe.

        Sin la capa oficial (el SIGPAC no contesta a esa consulta) y sin listado municipal
        cargado, el programa **no puede** decir que la parcela no está en zona: se queda en «no
        lo sé» y preguntará. Es la regla que ya tenía el programa para el listado.
        """
        import httpx

        from app import catalogos

        def get_falso(url, **kwargs):
            class Respuesta:
                status_code = 200

                def __init__(self, nombre):
                    self.text = (DATOS / nombre).read_text(encoding="utf-8")
                    self.content = self.text.encode()
                    self.headers = {"content-type": "application/json"}

            if "intersection/nitratos" in url:
                raise httpx.ConnectError("sin red")
            if "refcatparcela" in url:
                return Respuesta("referencia_catastral_de_la_parcela.json")
            return Respuesta("recinto_de_ejemplo_503_51.json")

        monkeypatch.setattr(httpx, "get", get_falso)
        monkeypatch.setattr(catalogos, "_RUTA_ZV_POR_DEFECTO", tmp_path / "no-existe.csv")
        try:
            catalogos.olvidar_zonas_vulnerables()
            respuesta = cliente.post(
                "/api/parcelas/desde-sigpac",
                headers=cuenta["cabeceras"],
                json={"ref_sigpac": "37-70-0-0-503-51-1"},
            )
            assert respuesta.status_code == 201, respuesta.text
            assert respuesta.json()["zona_vulnerable_nitratos"] is None
        finally:
            catalogos.olvidar_zonas_vulnerables()


class TestSiElSigpacNoContesta:
    """Lo que no se puede hacer es inventarse el dato: se dice que no se sabe."""

    def test_las_tres_consultas_nuevas_avisan_cuando_no_hay_red(self, monkeypatch):
        import httpx

        def falla(url, **kwargs):
            raise httpx.ConnectError("sin red")

        monkeypatch.setattr(httpx, "get", falla)
        referencia = sigpac.lee_referencia(RECINTO_DEL_AGRICULTOR)
        busqueda = sigpac.Busqueda(provincia=37, municipio=70, poligono=503, parcela=51)

        with pytest.raises(sigpac.SigpacNoContesta):
            sigpac.pedir_recinto_por_punto(*PUNTO_COMPROBADO)
        with pytest.raises(sigpac.SigpacNoContesta):
            sigpac.pedir_referencia_catastral(busqueda)
        with pytest.raises(sigpac.SigpacNoContesta):
            sigpac.pedir_interseccion("nitratos", referencia)

    def test_un_error_del_servicio_tambien_se_avisa(self, monkeypatch):
        import httpx

        class Error:
            status_code = 500
            text = "vaya"

        monkeypatch.setattr(httpx, "get", lambda url, **k: Error())
        with pytest.raises(sigpac.SigpacNoContesta):
            sigpac.pedir_interseccion(
                "nitratos", sigpac.lee_referencia(RECINTO_DEL_AGRICULTOR)
            )

    def test_todos_los_recintos_de_la_parcela_se_leen(self):
        """La consulta oficial `recinfoparc` devuelve los recintos con TODAS sus propiedades."""
        recintos = sigpac.lee_recintos(_respuesta("recintos_de_la_parcela.json"))
        # Ojo: `recinfoparc` devuelve una lista de propiedades, no una colección de la OGC API,
        # así que se lee con `lee_recinto` sobre cada elemento.
        assert recintos == [], "no es una respuesta de la API de descarga"
        uno = sigpac.lee_recinto(_respuesta("recintos_de_la_parcela.json"))
        assert uno is not None
        assert uno.ref_sigpac == RECINTO_DEL_AGRICULTOR
        assert uno.superficie == 4.9016
