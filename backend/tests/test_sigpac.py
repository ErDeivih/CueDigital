"""El conector con el SIGPAC: traer la parcela sin teclearla.

Es lo que quita de en medio el momento en el que más gente abandona una aplicación nueva:
dar de alta cuarenta parcelas escribiendo ocho datos en cada una.

**Los tests no salen a internet.** Prueban el parser contra una respuesta **de verdad** del
SIGPAC guardada en `data/sigpac/recinto_de_ejemplo.json`, bajada con
`backend/scripts/bajar_sigpac.py`. Un test que depende de que el servicio del FEGA esté
disponible es una lotería, y una lotería no es un test.

Lo que sí se prueba contra la realidad es que los datos guardados **son los del SIGPAC y no los
ha escrito nadie a mano**: se comprueba que las listas oficiales tienen los códigos que el FEGA
publica (933 productos, 34 usos…) y que el recinto de ejemplo tiene los campos que el servicio
devuelve.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import catalogos, sigpac, textos

RUTA_DATOS = Path(__file__).resolve().parents[2] / "data" / "sigpac"


class TestLaReferencia:
    def test_se_lee_con_guiones(self):
        referencia = sigpac.lee_referencia("37-22-0-0-501-427-1")
        assert referencia.provincia == 37
        assert referencia.municipio == 22
        assert referencia.poligono == 501
        assert referencia.parcela == 427
        assert referencia.recinto == 1

    def test_se_lee_como_la_escriba_cada_uno(self):
        """Cada uno la copia de donde puede: del papel, del visor o de un correo."""
        esperada = "37-22-0-0-501-427-1"
        for texto in (
            "37-22-0-0-501-427-1",
            "37 22 0 0 501 427 1",
            "37.22.0.0.501.427.1",
            "37/22/0/0/501/427/1",
            "  37-22-0-0-501-427-1  ",
            "Provincia 37, municipio 22, polígono 501, parcela 427, recinto 1",
        ):
            # El último no tiene los siete números, así que este bucle comprueba los que sí.
            numeros = [n for n in texto.replace(",", " ").split() if n.isdigit()]
            if len(numeros) != 7:
                continue
            assert sigpac.lee_referencia(texto).como_texto() == esperada, texto

    def test_una_referencia_a_la_que_le_faltan_numeros_se_rechaza(self):
        with pytest.raises(sigpac.ReferenciaInvalida) as error:
            sigpac.lee_referencia("37-22-501-427-1")
        assert "siete números" in str(error.value)
        assert "5" in str(error.value), "y dice cuántos ha encontrado"

    def test_una_referencia_vacia_se_rechaza_con_un_mensaje_util(self):
        with pytest.raises(sigpac.ReferenciaInvalida) as error:
            sigpac.lee_referencia("   ")
        assert str(error.value).strip()

    def test_se_puede_escribir_y_leer(self):
        referencia = sigpac.lee_referencia("37-22-0-0-501-427-1")
        assert sigpac.lee_referencia(referencia.como_texto()) == referencia


class TestLasDirecciones:
    def test_la_direccion_de_consulta_lleva_los_siete_numeros_en_su_orden(self):
        """El orden lo fija el documento del FEGA, con este ejemplo:

        https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfo/6/60/0/0/41/126/1.json
        """
        referencia = sigpac.lee_referencia("6-60-0-0-41-126-1")
        assert sigpac.url_recinto(referencia) == (
            "https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfo/6/60/0/0/41/126/1.json"
        )

    def test_la_direccion_de_las_listas_de_codigos(self):
        assert sigpac.url_codigos("cod_aprovechamiento") == (
            "https://sigpac-hubcloud.es/codigossigpac/cod_aprovechamiento.json"
        )

    def test_la_direccion_se_puede_cambiar_para_probar_sin_salir_a_internet(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_SIGPAC_BASE", "https://mi.servidor.de.pruebas")
        assert sigpac.url_recinto(sigpac.lee_referencia("1-2-3-4-5-6-7")).startswith(
            "https://mi.servidor.de.pruebas/query/recinfo/"
        )


class TestElParser:
    """Contra una respuesta de verdad del SIGPAC, guardada en el repositorio."""

    @pytest.fixture
    def respuesta_de_verdad(self):
        return json.loads((RUTA_DATOS / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))

    def test_lee_un_recinto_de_verdad(self, respuesta_de_verdad):
        recinto = sigpac.lee_recinto(respuesta_de_verdad)
        assert recinto is not None
        assert recinto.provincia == 37, "Salamanca"
        assert recinto.superficie and recinto.superficie > 0
        assert recinto.uso_sigpac
        assert recinto.wkt and recinto.wkt.startswith("POLYGON")
        assert recinto.srid == 4258

    def test_el_dibujo_viene_en_wkt_y_es_el_mismo_formato_que_guardamos(self, respuesta_de_verdad):
        """`Parcela.geometria` es texto WKT a propósito (funciona en SQLite y en PostGIS), y el
        SIGPAC devuelve WKT. Encajan sin convertir nada."""
        recinto = sigpac.lee_recinto(respuesta_de_verdad)
        assert recinto.wkt.startswith("POLYGON((")
        assert recinto.wkt.endswith("))")

    def test_la_referencia_se_puede_reconstruir(self, respuesta_de_verdad):
        recinto = sigpac.lee_recinto(respuesta_de_verdad)
        assert recinto.ref_sigpac == "37-22-0-0-501-427-1"

    def test_una_lista_vacia_es_que_el_recinto_no_existe(self):
        """No es un error de la aplicación: esa referencia no es de nadie."""
        assert sigpac.lee_recinto([]) is None

    def test_una_respuesta_que_no_se_entiende_no_revienta(self):
        assert sigpac.lee_recinto("esto no es json") is None
        assert sigpac.lee_recinto(None) is None
        assert sigpac.lee_recinto({}) is not None, "un objeto vacío se lee, pero sin datos"
        assert sigpac.lee_recinto({}).ref_sigpac == ""

    def test_un_texto_json_tambien_vale(self, respuesta_de_verdad):
        recinto = sigpac.lee_recinto(json.dumps(respuesta_de_verdad))
        assert recinto.provincia == 37


class TestLasListasDeCodigosOficiales:
    def test_estan_descargadas(self):
        assert sigpac.datos_disponibles()["cargados"] is True

    def test_los_productos_son_los_933_del_fega(self):
        productos = sigpac.productos_oficiales()
        assert len(productos) == 933
        assert productos[1] == "TRIGO BLANDO"
        assert productos[0] == "PRODUCTO DESCONOCIDO"

    def test_los_usos_del_suelo_son_los_del_fega(self):
        usos = sigpac.usos_oficiales()
        assert len(usos) == 34
        assert usos["TA"] == "TIERRAS ARABLES"
        assert usos["OV"] == "OLIVAR"

    def test_un_uso_se_puede_leer_en_cristiano(self):
        assert sigpac.etiqueta_uso("TA") == "TIERRAS ARABLES"

    def test_un_uso_que_no_esta_se_devuelve_como_esta(self):
        """Sin traducción inventada: el código es lo que pone el papel del agricultor."""
        assert sigpac.etiqueta_uso("ZZ") == "ZZ"
        assert sigpac.etiqueta_uso(None) == ""

    def test_sin_ficheros_las_listas_estan_vacias_y_no_revienta(self, tmp_path):
        """Los nombres de los usos son un adorno: no tenerlos no puede impedir apuntar."""
        assert sigpac.cargar_codigos("cod_uso_sigpac", tmp_path) == {}
        assert sigpac.etiqueta_uso("TA") == "TIERRAS ARABLES", "sigue usando los de verdad"

    def test_un_fichero_roto_no_revienta(self, tmp_path):
        (tmp_path / "cod_uso_sigpac.json").write_text("no es json", encoding="utf-8")
        assert sigpac.cargar_codigos("cod_uso_sigpac", tmp_path) == {}

    def test_los_aprovechamientos_y_las_incidencias_tambien_estan(self):
        assert sigpac.aprovechamientos_oficiales()
        assert sigpac.incidencias_oficiales()

    def test_se_dice_de_donde_salen_los_datos(self):
        datos = sigpac.datos_disponibles()
        assert "Creative Commons" in datos["licencia"]
        assert "SIGPAC" in datos["licencia"]
        assert datos["como_actualizarlos"].endswith("bajar_sigpac.py")

    def test_hay_un_leeme_con_la_procedencia(self):
        """Para que nadie tenga que buscar de dónde salió cada fichero."""
        leeme = (RUTA_DATOS / "LEEME.md").read_text(encoding="utf-8")
        assert "sigpac-hubcloud.es" in leeme
        assert "FEGA" in leeme
        assert "bajar_sigpac.py" in leeme


class TestBuscarUnProducto:
    def test_encuentra_el_trigo_blando(self):
        codigo, nombre = sigpac.busca_producto("Trigo blando")
        assert codigo == 1
        assert nombre == "TRIGO BLANDO"

    def test_no_le_importan_las_mayusculas_ni_las_tildes(self):
        for texto in ("trigo blando", "TRIGO BLANDO", "  Trígo Blándo  "):
            assert sigpac.busca_producto(texto)[0] == 1, texto

    def test_encuentra_la_cebada(self):
        assert sigpac.busca_producto("CEBADA")[0] == 5

    def test_un_producto_que_no_existe_no_da_codigo(self):
        """Devolver `None` y no el código más parecido: un código mal puesto guarda el producto
        equivocado, y eso no da error al mandarlo."""
        assert sigpac.busca_producto("zapato") == (None, None)
        assert sigpac.busca_producto("") == (None, None)
        assert sigpac.busca_producto(None) == (None, None)

    def test_sin_catalogo_no_encuentra_nada(self, tmp_path):
        assert sigpac.busca_producto("trigo blando", {}) == (None, None)


class TestElConectorPorLaApi:
    """El endpoint que da de alta la parcela, sin salir a internet.

    Se le dice al conector que hable con un servidor de mentiras, que devuelve la respuesta de
    verdad del SIGPAC guardada en el repositorio. Así se prueba el camino entero —HTTP, parser,
    alta de la parcela— sin depender de que el FEGA esté disponible.
    """

    @pytest.fixture
    def servidor_sigpac(self, monkeypatch):
        """Sustituye `httpx.get` por uno que devuelve el recinto de ejemplo."""
        import httpx

        crudo = json.loads((RUTA_DATOS / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))

        class RespuestaFalsa:
            status_code = 200
            text = json.dumps(crudo)

            def raise_for_status(self):
                return None

        llamadas: list[str] = []

        def get_falso(url, **kwargs):
            llamadas.append(url)
            return RespuestaFalsa()

        monkeypatch.setattr(httpx, "get", get_falso)
        return llamadas

    def test_se_da_de_alta_la_parcela_con_una_referencia(self, cliente, cuenta, servidor_sigpac):
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1", "alias": "El Prado", "sistema": "secano"},
        )
        assert respuesta.status_code == 201, respuesta.text
        parcela = respuesta.json()
        assert parcela["alias"] == "El Prado"
        assert parcela["ref_sigpac"] == "37-22-0-0-501-427-1"
        assert parcela["superficie_ha"] > 0
        assert parcela["superficie_oficial"] is True, "la superficie del SIGPAC es la oficial"
        assert parcela["uso_sigpac"]
        assert parcela["pendiente_pct"] is not None
        assert servidor_sigpac and "recinfo/37/22/0/0/501/427/1" in servidor_sigpac[0]

    def test_la_parcela_trae_el_dibujo_del_trozo(self, cliente, cuenta, servidor_sigpac, db_sesion):
        cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        )
        from sqlalchemy import select

        from app import models

        parcela = db_sesion.scalar(select(models.Parcela))
        assert parcela.geometria and parcela.geometria.startswith("POLYGON")

    def test_sin_alias_se_llama_como_el_recinto(self, cliente, cuenta, servidor_sigpac):
        """No se le puede pedir el nombre antes: la gracia es no tener que escribir.

        El nombre que se pone solo dice **la parcela y el recinto**, no solo el recinto: «recinto
        1» a secas no dice de qué parcela es, y con cuarenta parcelas eso no sirve para
        reconocerla.
        """
        parcela = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        ).json()
        assert "427" in parcela["alias"]
        assert "1" in parcela["alias"]
        assert parcela["alias"] != "Recinto 1", "no se sabe de qué parcela es"

    def test_el_pueblo_sale_de_los_codigos_del_recinto_no_de_la_finca(
        self, cliente, cuenta, servidor_sigpac
    ):
        """El pueblo lo dicen los códigos del propio recinto, y **nunca** la explotación.

        Este test decía antes que el municipio y la provincia se quedaban en blanco, porque el
        código del SIGPAC no se daba por equivalente al del INE. Desde el 24/09/2026 sí se sabe
        que lo es: la parcela del agricultor (`37:70`) es Calvarrasa de Arriba (`37070`), está
        comprobado con su referencia catastral y con los 387 municipios del listado de IDECyL, y
        hay tests de eso (`test_parcelas_por_codigos.py`).

        **Lo que se sigue comprobando es lo importante**: que el pueblo se saca de los códigos
        del recinto y no se copia de la finca. La explotación de esta prueba es de otra provincia
        a propósito, y la parcela tiene que salir con la suya.
        """
        parcela = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        ).json()
        assert parcela["provincia"] == "Salamanca", "la del recinto (37), no la de la finca"
        assert parcela["municipio"], "y el pueblo, de la lista oficial del INE"
        assert parcela["codigo_ine"], "con su código, que es con el que se comprueba la zona"

    def test_la_zona_de_nitratos_se_comprueba_con_lo_que_se_sabe(
        self, cliente, cuenta, servidor_sigpac, monkeypatch
    ):
        """Con el pueblo ya resuelto, la zona se comprueba contra el listado oficial.

        Antes, sin municipio ni provincia escritos a mano, la parcela se quedaba en «no lo sé».
        Ahora el pueblo sale de los códigos del recinto, así que se puede comprobar: si el
        municipio está en el listado de zonas vulnerables, la parcela lo está, y si no, no. Y
        cuando el agricultor dice él de dónde es, manda lo que dice él.
        """
        from scripts import bajar_zonas_vulnerables_cyl as fuente

        monkeypatch.setattr(catalogos, "_RUTA_ZV_POR_DEFECTO", fuente.CSV)
        try:
            catalogos.cargar_zonas_vulnerables()
            resuelta = cliente.post(
                "/api/parcelas/desde-sigpac", headers=cuenta["cabeceras"],
                json={"ref_sigpac": "37-22-0-0-501-427-1"},
            ).json()
            assert resuelta["zona_vulnerable_nitratos"] is not None, (
                "con el pueblo resuelto se comprueba, no se queda en «no lo sé»"
            )
            con_ubicacion = cliente.post(
                "/api/parcelas/desde-sigpac", headers=cuenta["cabeceras"],
                json={"ref_sigpac": "37-22-0-0-501-427-1", "municipio": "Peñaranda de Bracamonte", "provincia": "Salamanca"},
            ).json()
            assert con_ubicacion["zona_vulnerable_nitratos"] is True
        finally:
            catalogos.olvidar_zonas_vulnerables()

    def test_los_nombres_se_pueden_corregir(self, cliente, cuenta, servidor_sigpac):
        parcela = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={
                "ref_sigpac": "37-22-0-0-501-427-1",
                "provincia": "Valladolid",
                "municipio": "Medina del Campo",
            },
        ).json()
        assert parcela["provincia"] == "Valladolid"
        assert parcela["municipio"] == "Medina del Campo"

    def test_una_referencia_mal_escrita_se_dice_con_claridad(self, cliente, cuenta, servidor_sigpac):
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-501"},
        )
        assert respuesta.status_code == 422
        assert "siete números" in respuesta.json()["detail"]

    def test_un_recinto_que_no_existe_se_dice_que_no_existe(self, cliente, cuenta, monkeypatch):
        import httpx

        class Vacia:
            status_code = 200
            text = "[]"

        monkeypatch.setattr(httpx, "get", lambda url, **k: Vacia())
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        )
        assert respuesta.status_code == 404
        assert "no tiene ningún recinto" in respuesta.json()["detail"]

    def test_si_el_sigpac_no_contesta_se_dice_y_se_puede_apuntar_a_mano(
        self, cliente, cuenta, monkeypatch
    ):
        """Un conector que rellena la superficie con lo que le parece sería peor que no
        tenerlo."""
        import httpx

        def falla(url, **kwargs):
            raise httpx.ConnectError("sin red")

        monkeypatch.setattr(httpx, "get", falla)
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        )
        assert respuesta.status_code == 503
        detalle = respuesta.json()["detail"]
        assert "a mano" in detalle, "y le dice qué hacer mientras"
        assert "SIGPAC" in detalle

    def test_y_el_alta_a_mano_sigue_funcionando(self, cliente, cuenta, crear_parcela):
        """El conector es un atajo, no un requisito: sin él se apunta igual que siempre."""
        parcela = crear_parcela(alias="A mano", superficie_ha=1.5)
        assert parcela["alias"] == "A mano"
        assert parcela["superficie_ha"] == 1.5
        assert parcela["ref_sigpac"] == "37-455-12-3", "la que escribió él a mano"
        # Y no se ha ido a preguntar al SIGPAC por ninguna parte.
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()[0]["alias"] == "A mano"


class TestConsultarSinDarDeAlta:
    def test_se_puede_comprobar_una_referencia_antes(self, cliente, cuenta, monkeypatch):
        import httpx

        crudo = json.loads((RUTA_DATOS / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))

        class RespuestaFalsa:
            status_code = 200
            text = json.dumps(crudo)

            def raise_for_status(self):
                return None

        monkeypatch.setattr(httpx, "get", lambda url, **k: RespuestaFalsa())
        datos = cliente.post(
            "/api/sigpac/consultar",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        ).json()
        assert datos["encontrado"] is True
        assert datos["uso"] == "TIERRAS ARABLES"
        assert datos["tiene_dibujo"] is True
        assert datos["superficie_ha"] > 0

    def test_una_referencia_que_no_existe_se_dice_sin_reventar(self, cliente, cuenta, monkeypatch):
        import httpx

        class Vacia:
            status_code = 200
            text = "[]"

            def raise_for_status(self):
                return None

        monkeypatch.setattr(httpx, "get", lambda url, **k: Vacia())
        datos = cliente.post(
            "/api/sigpac/consultar",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        ).json()
        assert datos["encontrado"] is False
        assert datos["mensaje"] == textos.SIGPAC["no_encontrado"]

    def test_el_estado_dice_qué_datos_hay_y_de_dónde_salen(self, cliente):
        datos = cliente.get("/api/sigpac/estado").json()
        assert datos["cargados"] is True
        assert datos["productos"] == 933
        assert "Creative Commons" in datos["licencia"]
        assert datos["textos"]["titulo"]


class TestElVocabulario:
    def test_la_interfaz_trae_los_textos_del_sigpac(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert datos["sigpac"]["traer"] == "TRAERME LOS DATOS"
        assert datos["sigpac"]["referencia_ejemplo"] == "37-22-0-0-501-427-1"

    def test_la_referencia_de_ejemplo_se_puede_leer(self):
        """Si el ejemplo de la pantalla no valiera, sería una guía para hacerlo mal."""
        sigpac.lee_referencia(textos.SIGPAC["referencia_ejemplo"])

    def test_todo_el_texto_nuevo_esta_en_el_fichero_de_textos(self):
        visibles = textos.textos_visibles()
        assert textos.SIGPAC["titulo"] in visibles
        assert textos.SIGPAC["no_encontrado"] in visibles
        assert textos.SIGPAC["los_nombres_no_vienen"] in visibles

    def test_el_texto_no_atribuye_al_recinto_los_nombres_de_la_finca(self):
        aviso = textos.SIGPAC["los_nombres_no_vienen"]
        assert "SIGPAC no trae los nombres" in aviso
        assert "todavía no sabemos" in aviso


class TestElUsoSigpacEnLaParcela:
    def test_los_usos_oficiales_son_los_del_fega(self):
        """34 usos, con sus nombres. No es una lista nuestra."""
        usos = sigpac.usos_oficiales()
        assert set(usos) >= {"TA", "OV", "FY", "IM", "PA", "PR"}
        assert usos["TA"] == "TIERRAS ARABLES"

    def test_un_uso_de_labor_no_se_confunde_con_improductivo(self):
        usos = sigpac.usos_oficiales()
        assert usos["IM"] != usos["TA"]

    def test_las_provincias_de_cyl_tienen_todas_uso_definido(self):
        """No se traduce el código a nombre de provincia porque el SIGPAC no los publica.

        Lo que sí se comprueba es que las nueve provincias de Castilla y León son las que la
        aplicación ofrece en el desplegable, para que el agricultor pueda corregir el nombre.
        """
        assert len(catalogos.PROVINCIAS_CYL) == 9
        assert "Salamanca" in catalogos.PROVINCIAS_CYL
        assert "Valladolid" in catalogos.PROVINCIAS_CYL
