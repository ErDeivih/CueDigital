"""Dar de alta una parcela sin saberse ningún código.

**El problema que resuelve este fichero.** Para traer una parcela del SIGPAC había que
escribir **siete números** de memoria. El agricultor no los tiene así en ninguna parte: en el
visor del SIGPAC su parcela se lee `37:70:0:0:503:51` (seis números, y el recinto en otra
columna) y en la Sede del Catastro lo que hay es la referencia catastral de 20 caracteres. Lo
que él ve en su pantalla tiene que valer, y el programa tiene que sacar de ahí el polígono y la
parcela.

**Y los municipios.** El municipio y la provincia se escribían a mano, y si no coincidían al
carácter con el nombre oficial, la comprobación de zona vulnerable no encontraba el pueblo y
el agricultor se quedaba sin saber si su parcela tiene límites de abono. Ahora se eligen de la
lista oficial del INE, que es la misma numeración que usan el visor del SIGPAC y la referencia
catastral.

**De dónde salen los datos de este test, y por qué se pueden comprobar.** Las referencias son
las que el agricultor tiene en su papel (dos capturas de sus pantallas, del visor del SIGPAC y
de la Sede del Catastro), y todo lo demás se coteja contra las fuentes oficiales que están en
el repositorio: el diccionario de municipios del INE y la respuesta de verdad del SIGPAC de esa
misma parcela. Nada de lo que se afirma aquí está puesto a mano.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from app import catalogos, sigpac

RAIZ = Path(__file__).resolve().parents[2]
MUNICIPIOS = RAIZ / "data" / "municipios_cyl.csv"
FUENTES_MUNICIPIOS = RAIZ / "data" / "municipios_ine_fuentes"
RECINTOS_DE_EJEMPLO = RAIZ / "data" / "sigpac" / "recintos_de_ejemplo.json"
ZV_CYL = RAIZ / "data" / "zv_cyl.csv"

# La parcela del agricultor, tal y como se lee en el visor del SIGPAC: provincia 37, municipio
# 70, sin agregado ni zona, polígono 503, parcela 51, un solo recinto (el 1).
SU_PARCELA_EN_EL_VISOR = "37:70:0:0:503:51"
SU_PARCELA_CON_RECINTO = "37-70-0-0-503-51-1"

# Su referencia catastral, la que da la Sede del Catastro (captura del 24/09/2026). Los cuatro
# datos que se usan para buscar el recinto son las 14 primeras cifras; lo que va detrás son las
# de control, que no se usan.
SU_REFERENCIA_CATASTRAL = "37070A503000230000AF"

# Y la de la parcela que sale en el visor del SIGPAC, con el recinto 1 que verificamos contra el
# servicio. Se admite con la cola de control más corta porque esas cifras no se usan para buscar.
SU_REFERENCIA_CATASTRAL_DEL_VISOR = "37070A50300051000AQ"


class TestLaReferenciaSeEntiendeComoLaEscribeElAgricultor:
    """Las tres formas que el agricultor tiene delante tienen que valer."""

    def test_la_del_visor_del_sigpac(self):
        """`37:70:0:0:503:51`: seis números, sin recinto, que es lo que enseña el visor."""
        busqueda = sigpac.lee_busqueda(SU_PARCELA_EN_EL_VISOR)
        assert busqueda.provincia == 37
        assert busqueda.municipio == 70
        assert busqueda.agregado == 0
        assert busqueda.zona == 0
        assert busqueda.poligono == 503
        assert busqueda.parcela == 51
        assert busqueda.recinto is None, "el recinto no viene en el visor: se elige de la lista"
        assert busqueda.es_completa is False

    def test_los_siete_numeros_de_siempre(self):
        busqueda = sigpac.lee_busqueda(SU_PARCELA_CON_RECINTO)
        assert (busqueda.poligono, busqueda.parcela, busqueda.recinto) == (503, 51, 1)
        assert busqueda.es_completa is True

    def test_la_referencia_catastral_lleva_dentro_el_poligono_y_la_parcela(self):
        """Lo que hace falta para buscar el recinto sale de las 14 primeras cifras.

        Y se coteja con lo que dice el propio Catastro en su pantalla: esa referencia es de
        «Polígono 503 Parcela 23, CAMINO DE CALVARRASA, CALVARRASA DE ARRIBA (SALAMANCA)».
        """
        busqueda = sigpac.lee_busqueda(SU_REFERENCIA_CATASTRAL)
        assert busqueda.provincia == 37
        assert busqueda.municipio == 70
        assert busqueda.poligono == 503
        assert busqueda.parcela == 23
        assert busqueda.referencia_catastral == SU_REFERENCIA_CATASTRAL

    def test_la_referencia_catastral_del_visor_da_la_misma_parcela_que_el_visor(self):
        """La otra: la de la parcela 51, que es la que verificamos contra el SIGPAC.

        Se coteja con la respuesta de verdad del servicio (guardada en `data/sigpac/`): el
        polígono y la parcela que salen de la referencia catastral son los mismos que los del
        recinto que devuelve el SIGPAC para `37/70/0/0/503/51/1`.
        """
        busqueda = sigpac.lee_busqueda(SU_REFERENCIA_CATASTRAL_DEL_VISOR)
        assert (busqueda.poligono, busqueda.parcela) == (503, 51)

        cuerpo = json.loads(RECINTOS_DE_EJEMPLO.read_text(encoding="utf-8"))
        recintos = sigpac.lee_recintos(cuerpo)
        assert recintos, "la respuesta de ejemplo tiene que traer el recinto de esta parcela"
        primero = recintos[0]
        assert (primero.poligono, primero.parcela) == (busqueda.poligono, busqueda.parcela)

    def test_el_municipio_de_la_referencia_catastral_es_el_del_listado_del_ine(self):
        """`37070` tiene que ser Calvarrasa de Arriba en la lista oficial, no en la nuestra.

        Esto es lo que une las dos fuentes: el municipio de la referencia catastral y el del
        visor del SIGPAC («70 - CALVARRASA DE ARRIBA») son el mismo código del INE.
        """
        busqueda = sigpac.lee_busqueda(SU_REFERENCIA_CATASTRAL)
        municipio = catalogos.municipio_por_codigo_ine(f"{busqueda.provincia:02d}{busqueda.municipio:03d}")
        assert municipio is not None, "ese código municipal tiene que estar en la lista del INE"
        assert municipio.nombre == "Calvarrasa de Arriba"
        assert municipio.provincia == "Salamanca"
        assert municipio.codigo_municipio == "070", "el del visor del SIGPAC"

    def test_una_cosa_que_no_es_ninguna_de_las_tres_se_dice_claro(self):
        """El mensaje tiene que decir las tres formas: quien lo lee no sabe qué escribir."""
        with pytest.raises(sigpac.ReferenciaInvalida) as fallo:
            sigpac.lee_busqueda("123")
        mensaje = str(fallo.value)
        assert "37:70:0:0:503:51" in mensaje
        assert "37070A50300051000AQ" in mensaje
        assert "3" in mensaje, "y cuántos números ha escrito, para que pueda contarlos"

    def test_sin_escribir_nada_tambien_se_dice(self):
        with pytest.raises(sigpac.ReferenciaInvalida):
            sigpac.lee_busqueda("   ")

    def test_una_referencia_sin_recinto_se_completa_con_el_recinto_que_se_le_diga(self):
        """El recinto se elige de la lista del SIGPAC, y con él ya se puede pedir el trozo."""
        busqueda = sigpac.lee_busqueda(SU_PARCELA_EN_EL_VISOR)
        referencia = busqueda.con_recinto(2)
        assert referencia.como_texto() == "37-70-0-0-503-51-2"
        assert sigpac.url_recinto(referencia).endswith("/query/recinfo/37/70/0/0/503/51/2.json")


class TestLaBusquedaDeLosTrozos:
    """La consulta que devuelve **todos los recintos** de una parcela.

    Es lo que hace falta para no tener que saberse el recinto: se le enseña la lista al
    agricultor y él marca los suyos, igual que en las aplicaciones oficiales del FEGA.
    """

    def test_lee_la_respuesta_de_verdad_del_sigpac(self):
        """Se prueba contra la respuesta que devolvió el servicio, no contra una inventada."""
        cuerpo = json.loads(RECINTOS_DE_EJEMPLO.read_text(encoding="utf-8"))
        recintos = sigpac.lee_recintos(cuerpo)
        assert len(recintos) == 1
        recinto = recintos[0]
        assert recinto.recinto == 1
        assert recinto.ref_sigpac == SU_PARCELA_CON_RECINTO
        assert recinto.pendiente_media == 1.0
        assert recinto.altitud == 837

    def test_la_direccion_lleva_los_datos_que_piden_las_aplicaciones_oficiales(self):
        """Provincia, municipio, polígono y parcela son los obligatorios; agregado y zona no.

        Las aplicaciones oficiales del FEGA lo dicen así: «son obligatorios para definir la
        búsqueda Cód. Provincia, Cód. Municipio, Cód. Polígono y Cód. Parcela». El agregado y la
        zona se filtran **solo si el agricultor los ha dicho**: con la referencia del visor los
        ha dicho (van en la propia referencia), y con la catastral no, porque esa no los trae.
        """
        busqueda = sigpac.lee_busqueda(SU_PARCELA_EN_EL_VISOR)
        url = sigpac.url_recintos(busqueda)
        assert "collections/recintos/items" in url
        assert "provincia=37" in url
        assert "municipio=70" in url
        assert "poligono=503" in url
        assert "parcela=51" in url
        assert "agregado=0" in url, "el visor sí dice el agregado: va en su referencia"

        del_catastro = sigpac.url_recintos(sigpac.lee_busqueda(SU_REFERENCIA_CATASTRAL))
        assert "poligono=503" in del_catastro and "parcela=23" in del_catastro
        assert "agregado=" not in del_catastro, "el Catastro no dice el agregado: no se supone"
        assert "zona=" not in del_catastro

    def test_si_el_agricultor_dice_la_zona_se_filtra(self):
        busqueda = sigpac.Busqueda(provincia=37, municipio=70, poligono=503, parcela=51, zona=1)
        assert "zona=1" in sigpac.url_recintos(busqueda)

    def test_una_respuesta_que_no_se_entiende_no_revienta(self):
        """Si el servicio contesta algo raro, la aplicación dice que no hay nada: no revienta."""
        assert sigpac.lee_recintos("esto no es json") == []
        assert sigpac.lee_recintos({"features": "tampoco"}) == []
        assert sigpac.lee_recintos({"features": [{"properties": {"sin_recinto": 1}}]}) == []


class TestLaListaOficialDeMunicipios:
    """La lista con la que el agricultor elige su pueblo en vez de escribirlo."""

    def test_estan_los_2248_municipios_de_la_comunidad(self):
        with MUNICIPIOS.open(encoding="utf-8", newline="") as fichero:
            filas = list(csv.DictReader(fichero))
        assert len(filas) == 2248, "los municipios de Castilla y León"

    def test_cada_provincia_tiene_los_suyos(self):
        """Si el INE cambia el fichero, estos números dejan de salir y hay que enterarse."""
        esperados = {
            "Ávila": 248,
            "Burgos": 371,
            "León": 211,
            "Palencia": 191,
            "Salamanca": 362,
            "Segovia": 209,
            "Soria": 183,
            "Valladolid": 225,
            "Zamora": 248,
        }
        with MUNICIPIOS.open(encoding="utf-8", newline="") as fichero:
            cuenta: dict[str, int] = {}
            for fila in csv.DictReader(fichero):
                cuenta[fila["provincia"]] = cuenta.get(fila["provincia"], 0) + 1
        assert cuenta == esperados

    def test_el_codigo_de_cinco_cifras_es_provincia_mas_municipio(self):
        with MUNICIPIOS.open(encoding="utf-8", newline="") as fichero:
            for fila in csv.DictReader(fichero):
                assert fila["codigo_ine"] == fila["codigo_provincia"] + fila["codigo_municipio"]
                assert len(fila["codigo_ine"]) == 5
                assert len(fila["codigo_municipio"]) == 3

    def test_la_copia_oficial_esta_y_coincide_con_su_huella(self):
        """El fichero que se guarda es la copia literal del INE, y su huella está declarada.

        Sin esto, el CSV podría haberlo escrito alguien a mano y nadie lo sabría.
        """
        procedencia = json.loads((FUENTES_MUNICIPIOS / "procedencia.json").read_text("utf-8"))
        xlsx = FUENTES_MUNICIPIOS / f"diccionario{procedencia['anio_del_diccionario']}.xlsx"
        assert xlsx.exists(), "tiene que estar la copia del diccionario oficial"
        assert hashlib.sha256(xlsx.read_bytes()).hexdigest() == procedencia["sha256"]
        assert procedencia["municipios"] == 2248
        assert "ine.es" in procedencia["url"]

    def test_los_municipios_del_listado_de_zonas_estan_todos(self):
        """Cotejo de dos fuentes oficiales distintas: el INE y la Junta.

        Si no coincidieran, elegir el municipio de una lista daría un código que no vale para
        la otra, y la zona de nitratos se calcularía con la numeración equivocada.
        """
        conocidos = {municipio.codigo_ine for municipio in catalogos.municipios_de_cyl()}
        with ZV_CYL.open(encoding="utf-8", newline="") as fichero:
            del_listado = {fila["codigo_ine"].strip() for fila in csv.DictReader(fichero)}
        assert len(del_listado) == 387
        assert del_listado <= conocidos, f"faltan {sorted(del_listado - conocidos)}"

    def test_se_busca_como_se_busca_en_el_movil(self):
        """Sin tildes y con lo que empieza por lo escrito delante."""
        nombres = [m.nombre for m in catalogos.busca_municipios("penaranda")]
        assert "Peñaranda de Bracamonte" in nombres, "sin tilde también tiene que encontrarlo"

        primeros = [m.nombre for m in catalogos.busca_municipios("calv")][:2]
        assert primeros == ["Calvarrasa de Abajo", "Calvarrasa de Arriba"]

    def test_se_puede_acotar_a_una_provincia(self):
        de_salamanca = catalogos.busca_municipios("santa", provincia="Salamanca")
        assert de_salamanca, "tiene que encontrar pueblos"
        assert {m.provincia for m in de_salamanca} == {"Salamanca"}


class TestElProgramaLeAyudaABuscarLosTrozos:
    """Los tres endpoints que quitan el trabajo de saberse códigos.

    Se prueban sustituyendo `httpx.get` por las **dos respuestas de verdad** de la parcela del
    agricultor (la lista de trozos y el trozo concreto), así que el camino que se prueba es el
    mismo que va a usar él: HTTP, parser, zona de nitratos y alta de la parcela.

    **Cambio de contrato del 03/10/2026, y por eso estas pruebas llevan ahora `cuenta`.**
    `POST /api/sigpac/buscar` **pedía sesión desde el primer día y dejó de pedirla**: era una de
    las rutas sin sesión que hacían llamadas de salida (hasta **26** al SIGPAC por petición, sin
    límite ni caché), y la revisión de rutas sin sesión lo dejó apuntado
    (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.12 y §5.1). Cerrarla no rompe nada para el
    agricultor —`app.js:6999` ya mandaba su vale, porque todo pasa por `apiJson`, que siempre lo
    pone— pero **sí cambia lo que hay que hacer para preguntar**: ahora hay que entrar. Estas
    pruebas preguntan como pregunta la pantalla, con su vale, que es lo que hay que comprobar; y
    el contrato nuevo (sin vale no se pregunta) tiene su prueba propia en
    `tests/test_lo_que_no_pide_sesion.py`.
    """

    @pytest.fixture
    def sigpac_de_verdad(self, monkeypatch):
        """El SIGPAC de verdad, pero sin salir a internet: responde lo que respondió."""
        import httpx

        trozos = json.loads(RECINTOS_DE_EJEMPLO.read_text(encoding="utf-8"))
        el_suyo = json.loads(
            (RAIZ / "data" / "sigpac" / "recinto_de_ejemplo_503_51.json").read_text("utf-8")
        )

        class Respuesta:
            status_code = 200

            def __init__(self, cuerpo):
                self.text = json.dumps(cuerpo)

        llamadas: list[str] = []

        def get_falso(url, **kwargs):
            llamadas.append(url)
            if "collections/recintos" in url:
                return Respuesta(trozos)
            if "recinfo/37/70/0/0/503/51/1" in url:
                return Respuesta(el_suyo)
            return Respuesta([])

        monkeypatch.setattr(httpx, "get", get_falso)
        return llamadas

    def test_la_lista_de_pueblos_se_sirve_para_elegir(self, cliente):
        """Sin escribir ningún código: se busca por el nombre y viene el código con él."""
        datos = cliente.get("/api/municipios?buscar=calvarrasa").json()
        assert datos["total"] == 2248
        assert len(datos["provincias"]) == 9
        nombres = [m["nombre"] for m in datos["municipios"]]
        assert "Calvarrasa de Arriba" in nombres
        el_suyo = next(m for m in datos["municipios"] if m["nombre"] == "Calvarrasa de Arriba")
        assert el_suyo["codigo_ine"] == "37070"
        assert el_suyo["codigo_municipio"] == "070"
        assert el_suyo["provincia"] == "Salamanca"

    def test_se_buscan_los_trozos_con_el_pueblo_elegido(self, cliente, cuenta, sigpac_de_verdad):
        """Lo que hacen las aplicaciones oficiales: municipio de la lista, polígono y parcela."""
        respuesta = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={
                "provincia": "Salamanca",
                "municipio": "Calvarrasa de Arriba",
                "poligono": 503,
                "parcela": 51,
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["encontrados"] == 1
        trozo = datos["recintos"][0]
        assert trozo["recinto"] == 1
        assert trozo["referencia"] == SU_PARCELA_CON_RECINTO
        assert trozo["superficie_ha"] == 4.9016
        assert trozo["uso_sigpac"] == "TA"
        assert trozo["uso"] == "TIERRAS ARABLES"
        assert trozo["tiene_dibujo"] is True
        assert datos["municipio"]["codigo_ine"] == "37070"

    def test_se_buscan_los_trozos_pegando_la_referencia_del_visor(
        self, cliente, cuenta, sigpac_de_verdad
    ):
        """Y sin elegir nada: `37:70:0:0:503:51` es lo que se lee en el visor y tiene que valer."""
        respuesta = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={"referencia": SU_PARCELA_EN_EL_VISOR},
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["encontrados"] == 1
        assert datos["busqueda"] == "37:70:0:0:503:51"

    def test_se_buscan_los_trozos_pegando_la_referencia_catastral(
        self, cliente, cuenta, sigpac_de_verdad
    ):
        """La del Catastro trae dentro el polígono y la parcela, y se guarda con la parcela."""
        respuesta = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={"referencia": SU_REFERENCIA_CATASTRAL_DEL_VISOR},
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["encontrados"] == 1, "se busca por el polígono y la parcela que lleva dentro"
        assert datos["referencia_catastral"] == SU_REFERENCIA_CATASTRAL_DEL_VISOR

    def test_sin_recintos_se_dice_que_no_hay_ninguno(self, cliente, cuenta, monkeypatch):
        """Cuarenta trozos en una parcela que no existe: se dice, no se deja la pantalla vacía."""
        import httpx

        class Vacia:
            status_code = 200
            text = '{"type": "FeatureCollection", "features": []}'

        monkeypatch.setattr(httpx, "get", lambda url, **k: Vacia())
        datos = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={"referencia": SU_PARCELA_EN_EL_VISOR},
        ).json()
        assert datos["encontrados"] == 0
        assert datos["mensaje"] == sigpac_textos()["sin_recintos"]
        assert "polígono y la parcela" in datos["mensaje"]

    def test_si_el_sigpac_no_contesta_no_se_inventa_nada(self, cliente, cuenta, monkeypatch):
        import httpx

        def falla(url, **kwargs):
            raise httpx.ConnectError("sin red")

        monkeypatch.setattr(httpx, "get", falla)
        respuesta = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={"referencia": SU_PARCELA_EN_EL_VISOR},
        )
        assert respuesta.status_code == 503
        assert "no se ha podido preguntar" in respuesta.json()["detail"].lower()

    def test_con_el_pueblo_a_mano_pero_sin_poligono_se_dice_que_falta(self, cliente, cuenta):
        """Sin polígono ni parcela no se puede buscar, y se dice qué falta en vez de fallar."""
        respuesta = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={"municipio": "Calvarrasa de Arriba"},
        )
        assert respuesta.status_code == 422
        assert "polígono" in respuesta.json()["detail"]

    def test_un_pueblo_que_no_esta_en_la_lista_se_dice(self, cliente, cuenta):
        """Sin el código del municipio no se puede preguntar: adivinarlo sería inventarse dónde está."""
        respuesta = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={"municipio": "Pueblo Inventado", "poligono": 1, "parcela": 1},
        )
        assert respuesta.status_code == 422
        assert "no está en la lista" in respuesta.json()["detail"]

    def test_se_traen_varios_trozos_de_una_vez(
        self, cliente, cuenta, sigpac_de_verdad, db_sesion
    ):
        """Pegar una lista de referencias y traerlas todas: cuarenta parcelas de una sentada."""
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac/varias",
            headers=cuenta["cabeceras"],
            json={
                "referencias": [SU_PARCELA_CON_RECINTO, SU_PARCELA_CON_RECINTO],
                "sistema": "secano",
                "municipio": "Calvarrasa de Arriba",
                "provincia": "Salamanca",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["cuantas"] == 2
        assert not datos["fallos"]
        assert datos["mensaje"], "y se dice cuántas han entrado"

        parcelas = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()
        assert len(parcelas) == 2
        una = parcelas[0]
        assert una["superficie_ha"] == 4.9016
        assert una["superficie_oficial"] is True
        assert una["municipio"] == "Calvarrasa de Arriba"
        assert una["agregado"] == 0 and una["zona"] == 0
        assert una["poligono"] == 503 and una["numero_parcela"] == 51

    def test_las_que_van_mal_no_tiran_las_demas(self, cliente, cuenta, sigpac_de_verdad):
        """Si tres de cuarenta están mal copiadas, tener las otras treinta y siete es lo que importa."""
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac/varias",
            headers=cuenta["cabeceras"],
            json={"referencias": ["no es una referencia", SU_PARCELA_CON_RECINTO, SU_PARCELA_EN_EL_VISOR]},
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["cuantas"] == 1, "la buena entra"
        assert len(datos["fallos"]) == 2
        motivos = " ".join(fallo["motivo"] for fallo in datos["fallos"])
        assert "no lo entiendo" in motivos.lower()
        assert "falta el número del trozo" in motivos.lower()

    def test_la_parcela_guardada_se_lleva_la_referencia_catastral(
        self, cliente, cuenta, sigpac_de_verdad
    ):
        """Si el agricultor la ha pegado, se guarda: el contenido mínimo del CUE la pide.

        Y el camino es el suyo: la referencia del Catastro sirve para **buscar** los trozos (que
        es lo que hace el Catastro: da la parcela, no el recinto), y al traer el trozo se guarda
        la referencia catastral con él. Cuando solo se pega la referencia catastral en el alta
        directa, se dice que falta el número del trozo y se le manda a la búsqueda: es lo que
        quiere hacer de todas formas.
        """
        # 1. Solo con la referencia catastral no se puede traer: falta el trozo, y se dice.
        sin_recinto = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": SU_REFERENCIA_CATASTRAL_DEL_VISOR},
        )
        assert sin_recinto.status_code == 422
        assert "falta el número del trozo" in sin_recinto.json()["detail"]

        # 2. El camino bueno: buscar los trozos y traer el marcado, con su referencia catastral.
        cliente.post(
            "/api/parcelas/desde-sigpac/varias",
            headers=cuenta["cabeceras"],
            json={
                "referencias": [SU_PARCELA_CON_RECINTO],
                "alias": "El llano",
                "municipio": "Calvarrasa de Arriba",
                "provincia": "Salamanca",
                "referencia_catastral": SU_REFERENCIA_CATASTRAL_DEL_VISOR,
            },
        )
        parcelas = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()
        assert len(parcelas) == 1
        assert parcelas[0]["referencia_catastral"] == SU_REFERENCIA_CATASTRAL_DEL_VISOR
        assert parcelas[0]["codigo_ine"] == "37070", "el código INE del pueblo elegido"


def sigpac_textos() -> dict:
    """Los textos del SIGPAC, para comparar los mensajes sin escribirlos otra vez a mano."""
    from app import textos

    return textos.SIGPAC
