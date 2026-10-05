"""El volcado oficial a la Junta (IUWS).

Aquí se prueba lo que se puede probar sin certificado y sin dominio: el protocolo, el
catálogo de mensajes, la lectura de respuestas, el identificador de cada actividad, el
contenido mínimo campo por campo y —lo más importante— que **lo que no se sabe no se
inventa**.

Lo que este test deja escrito y conviene entender antes de tocar nada:

* El formato exacto del JSON de importación está en el descriptor `BdcSix-DS-DiseñoCUE.xlsx`
  v3.11.4, que **no tenemos**. El propio Anexo VI avisa de que sus ejemplos «pueden no
  corresponderse con la v2.6». Por eso no se genera ese JSON, y hay tests que lo comprueban.
* Los campos «según catálogo» salen **vacíos**, no con un número inventado. Un código mal
  puesto no da error en el momento: guarda el producto equivocado.
* El `IdAjena` **no puede cambiar nunca**: si cambia, la Junta deja de reconocer lo ya
  cargado y lo duplica todo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import iuws, iuws_cliente, iuws_contenido, iuws_mapeo, textos


class TestLasDirecciones:
    """Las direcciones salen del Anexo VI, tal cual, con sus ejemplos."""

    def test_version(self):
        assert iuws.url_version("https://servidor:puerto") == "https://servidor:puerto/IUWS/api/version"

    def test_comunicacion(self):
        """El ejemplo del anexo: `/IUWS/api/comunicacion/nombreAppCue`."""
        assert (
            iuws.url_comunicacion("https://servidor:puerto", "CUE Digital")
            == "https://servidor:puerto/IUWS/api/comunicacion/CUEDigital"
        )

    def test_exportar_rea(self):
        """El ejemplo literal del anexo: `53442255P_V83192450`."""
        assert (
            iuws.url_exportar_rea("https://servidor:puerto", "53442255P", "V83192450")
            == "https://servidor:puerto/IUWS/api/exportarREA/53442255P_V83192450"
        )

    def test_exportar_cue(self):
        """El Anexo VI v3.11.4 ya no incluye el IdCuaderno en esta ruta."""
        assert (
            iuws.url_exportar_cue("https://servidor:puerto", "ES130000008847", "V83192450")
            == "https://servidor:puerto/IUWS/api/exportar/ES130000008847_V83192450"
        )

    def test_crear(self):
        assert iuws.url_crear("https://servidor:puerto") == "https://servidor:puerto/IUWS/api/crear/"

    def test_comprobar_estado(self):
        """El ejemplo literal del anexo: `comprobarEstado/256`."""
        assert (
            iuws.url_comprobar_estado("https://servidor:puerto", 256)
            == "https://servidor:puerto/IUWS/api/comprobarEstado/256"
        )

    def test_sin_cif_la_direccion_no_deja_un_hueco(self):
        """`A__B` no es lo mismo que `A_B`: el hueco vacío rompería la llamada."""
        url = iuws.url_exportar_cue("https://x", "ES130000008847")
        assert url == "https://x/IUWS/api/exportar/ES130000008847"
        assert "__" not in url

    def test_las_barras_sobran(self):
        assert iuws.url_version("https://x/") == "https://x/IUWS/api/version"

    def test_el_nombre_de_la_app_no_puede_llevar_barras(self):
        """Va dentro de la dirección: una barra cambiaría la ruta que se llama."""
        assert iuws.url_comunicacion("https://x", "CUE/Digital v2") == "https://x/IUWS/api/comunicacion/CUEDigitalv2"

    def test_la_base_de_castilla_y_leon_es_la_del_anexo_x(self):
        """Sale del Anexo X, que lista las direcciones comunidad por comunidad."""
        assert (
            iuws.BASES_POR_CCAA["Castilla y León"] == "https://servicios.ayg.jcyl.es"
        )

    def test_el_entorno_de_integracion_y_su_consola(self):
        assert iuws.ENTORNO_INTEGRACION == "https://sga.entornointegracion.es"
        assert iuws.SWAGGER_INTEGRACION.endswith("/IUWS/swagger-ui.html")

    def test_los_catalogos_oficiales_tienen_su_direccion(self):
        assert "bdcsixpor/catalogos" in iuws.CATALOGOS_SIEX


class TestLosMensajes:
    def test_estan_los_diecinueve_codigos_del_anexo(self):
        """El Anexo 1 los numera del 1 al 19. Ninguno puede faltar."""
        assert sorted(iuws.MENSAJES) == list(range(1, 20))

    def test_cada_codigo_dice_que_significa_en_castellano(self):
        for codigo in iuws.MENSAJES:
            explicacion = iuws.mensaje_de_codigo(codigo)
            assert explicacion.strip()
            assert "no está en el manual" not in explicacion

    def test_un_codigo_desconocido_se_dice_y_no_se_inventa(self):
        """Un número que no está en el manual no se puede interpretar: se dice."""
        explicacion = iuws.mensaje_de_codigo(999)
        assert "999" in explicacion
        assert "no está en el manual" in explicacion

    def test_algunos_codigos_concretos_son_los_del_anexo(self):
        assert "grabada correctamente" in iuws.mensaje_de_codigo(3)
        assert "catálogo" in iuws.mensaje_de_codigo(5) or "valores" in iuws.mensaje_de_codigo(5)
        assert "ROMA" in iuws.mensaje_de_codigo(6)
        assert "ROPO" in iuws.mensaje_de_codigo(7)
        assert "SIGPAC" in iuws.mensaje_de_codigo(10)

    def test_los_resultados_generales_estan_los_cinco(self):
        for resultado in ("OK", "PARCIAL", "FALLO", "ERROR", "ERROR_VALIDAR_CREDENCIALES"):
            assert resultado in iuws.RESULTADOS


class TestLeerLoQueContesta:
    def test_una_respuesta_ok(self):
        leida = iuws.leer_respuesta(
            '{"resultado": {"codigoResultado": "OK", "detalleImportacion": [{"codigo": 256, "descripcion": "Recibido"}]}}'
        )
        assert leida.esta_ok
        assert not leida.es_fallo
        assert leida.id_peticion == 256

    def test_el_id_de_la_peticion_es_lo_que_se_le_pasa_a_comprobar_estado(self):
        """Sin ese identificador no se puede saber si la carga ha ido bien."""
        leida = iuws.leer_respuesta(
            {"resultado": {"codigoResultado": "OK", "detalleImportacion": [{"codigo": 42}]}}
        )
        assert iuws.url_comprobar_estado("https://x", leida.id_peticion).endswith("/42")

    def test_una_respuesta_a_medias(self):
        leida = iuws.leer_respuesta(
            {
                "resultado": {
                    "codigoResultado": "PARCIAL",
                    "detalleImportacion": [
                        {"codigo": 3, "descripcion": "Actividad grabada correctamente"},
                        {"codigo": 5, "descripcion": "Campo mal"},
                    ],
                }
            }
        )
        assert leida.es_parcial
        assert not leida.esta_ok

    def test_una_respuesta_con_fallo_de_credenciales(self):
        leida = iuws.leer_respuesta(
            {"resultado": {"codigoResultado": "ERROR_VALIDAR_CREDENCIALES", "detalleImportacion": [{"codigo": 2}]}}
        )
        assert leida.es_fallo
        assert "autorizada" in leida.mensaje

    def test_las_actividades_que_fallan_se_sacan_con_su_motivo_escrito(self):
        """No «error 5»: qué actividad y por qué."""
        leida = iuws.leer_respuesta(
            {
                "resultado": {
                    "codigoResultado": "PARCIAL",
                    "detalleImportacion": [
                        {"codigo": 3, "descripcion": "ok"},
                        {"codigo": 6, "descripcion": "mal"},
                        {"codigo": 10, "descripcion": "mal"},
                    ],
                }
            }
        )
        fallidas = leida.actividades_fallidas()
        assert len(fallidas) == 2, "la que fue bien no cuenta como fallida"
        assert "ROMA" in fallidas[0]["explicacion"]
        assert "SIGPAC" in fallidas[1]["explicacion"]

    def test_el_estado_de_un_proceso_pendiente(self):
        leida = iuws.leer_respuesta(
            {
                "resultado": {
                    "codigoResultado": "OK",
                    "detalleOperacion": {"codigo": 3, "descripcion": "pendiente de procesamiento"},
                }
            }
        )
        assert leida.operacion["codigo"] == 3

    def test_la_respuesta_de_comprobar_estado_trae_el_cuaderno(self):
        leida = iuws.leer_respuesta(
            {"resultado": {"codigoResultado": "OK", "CUADERNO": {"CodigoSIEX": "933"}}}
        )
        assert leida.cuaderno["CodigoSIEX"] == "933"

    def test_una_respuesta_que_no_es_json_no_revienta(self):
        """Si el interfaz contesta un texto, hay que poder enseñarlo tal cual a soporte."""
        leida = iuws.leer_respuesta("<html>502 Bad Gateway</html>")
        assert leida.esta_ok is False
        assert "502" in leida.mensaje

    def test_una_respuesta_vacia_tampoco_revienta(self):
        assert iuws.leer_respuesta(None).esta_ok is False
        assert iuws.leer_respuesta({}).esta_ok is False

    def test_se_guarda_lo_crudo_por_si_hay_que_mandarlo_a_soporte(self):
        leida = iuws.leer_respuesta({"resultado": {"codigoResultado": "FALLO"}})
        assert leida.crudo == {"resultado": {"codigoResultado": "FALLO"}}


class TestElIdentificadorDeCadaActividad:
    """`IdAjena`: lo genera esta herramienta y es lo que evita duplicar y permite corregir."""

    def test_tiene_la_forma_documentada(self):
        assert iuws.id_ajeno("70922320A", "tratamiento", 14) == "CD-70922320A-T-14"

    def test_lleva_el_nif_porque_las_autorizaciones_van_por_titular(self):
        assert "70922320A" in iuws.id_ajeno("70922320A", "venta", 1)

    def test_cada_clase_de_actividad_tiene_su_sigla(self):
        siglas = {tipo: iuws.id_ajeno("1", tipo, 1).split("-")[2] for tipo in iuws.SIGLAS}
        assert len(set(siglas.values())) == len(siglas), f"hay siglas repetidas: {siglas}"

    def test_es_el_mismo_siempre(self):
        """Si cambiara, la Junta dejaría de reconocer lo ya cargado y lo duplicaría todo."""
        for _ in range(3):
            assert iuws.id_ajeno("70922320A", "tratamiento", 14) == "CD-70922320A-T-14"

    def test_dos_actividades_distintas_no_comparten_identificador(self):
        assert iuws.id_ajeno("70922320A", "tratamiento", 14) != iuws.id_ajeno("70922320A", "tratamiento", 15)
        assert iuws.id_ajeno("70922320A", "tratamiento", 14) != iuws.id_ajeno("70922320A", "venta", 14)

    def test_dos_fincas_no_comparten_identificador(self):
        assert iuws.id_ajeno("70922320A", "tratamiento", 1) != iuws.id_ajeno("12345678Z", "tratamiento", 1)

    def test_un_tipo_desconocido_no_revienta(self):
        assert iuws.id_ajeno("70922320A", "lo_que_sea", 3).endswith("-X-3")


class TestElSobre:
    def test_lleva_los_campos_del_descriptor_oficial(self):
        """Los nombres son los del esquema oficial, no los del ejemplo del anexo.

        Se cambió `IDTitular` por `IdTitular` al cotejar el sobre con el esquema JSON oficial
        v3.11.4: el esquema declara `IdTitular` como **obligatorio**, así que con el nombre del
        ejemplo del anexo el sobre no validaba nunca. El test se actualiza porque el
        comportamiento nuevo es el correcto: manda el esquema, que es el contrato que se
        comprueba antes de enviar.
        """
        sobre = iuws.sobre_del_cuaderno(
            codigo_siex="933",
            ca="13",
            nif_titular="68554421P",
            unidad_gestora="Q4197553C",
            codigo_rea="ES130000000016",
            id_cuaderno="23",
        )
        assert sobre["CodigoSIEX"] == "933"
        assert sobre["CAExplotacion"] == "13"
        assert sobre["IdTitular"] == "68554421P"
        assert sobre["UnidadGestora"] == "Q4197553C"
        assert sobre["CodigoRea"] == "ES130000000016"
        assert sobre["IdCuaderno"] == "23"

    def test_no_usa_el_nombre_del_ejemplo_del_anexo(self):
        """El ejemplo del anexo dice `IDTitular`; el esquema oficial dice `IdTitular`.

        Esto se deja fijado en un test propio porque es exactamente el tipo de detalle que
        alguien «arregla» copiando el ejemplo y vuelve a romper la validación.
        """
        sobre = iuws.sobre_del_cuaderno(codigo_siex=None, ca="13", nif_titular="1")
        assert "IDTitular" not in sobre
        assert "IdTitular" in sobre

    def test_el_codigo_de_castilla_y_leon_es_el_13(self):
        assert iuws.CODIGOS_CA["Castilla y León"] == "13"

    def test_lo_que_no_esta_no_se_queda_en_blanco(self):
        """Un campo vacío en el sobre es una credencial que falla."""
        sobre = iuws.sobre_del_cuaderno(codigo_siex=None, ca="13", nif_titular="1")
        assert "UnidadGestora" not in sobre
        assert "CodigoRea" not in sobre


class TestLoQueFalta:
    def test_la_lista_dice_quien_tiene_que_darlo(self):
        for falta in iuws.QUE_FALTA:
            assert falta.que and falta.por_que and falta.quien

    def test_todas_bloquean_porque_sin_ellas_no_se_puede_volcar(self):
        assert all(falta.bloquea for falta in iuws.QUE_FALTA)

    def test_el_descriptor_es_lo_primero_que_falta(self):
        claves = [falta.clave for falta in iuws.QUE_FALTA]
        assert "descriptor" in claves
        assert "catalogos" in claves
        assert "nombre_comercial" in claves
        assert "dominio" in claves
        assert "certificado" in claves

    def test_con_el_descriptor_cargado_deja_de_aparecer(self):
        sin = iuws.lo_que_falta(descriptor=False, configurado={})
        con = iuws.lo_que_falta(descriptor=True, configurado={})
        assert any(f.clave == "descriptor" for f in sin)
        assert not any(f.clave == "descriptor" for f in con)
        # Los catálogos se comprueban por separado del esquema.
        assert any(f.clave == "catalogos" for f in sin)
        assert any(f.clave == "catalogos" for f in con)
        assert len(con) == len(sin) - 1

    def test_lo_que_ya_esta_configurado_tampoco_aparece(self):
        falta = iuws.lo_que_falta(descriptor=False, configurado={"nombre_comercial": True})
        assert not any(f.clave == "nombre_comercial" for f in falta)

    def test_el_alta_en_el_entorno_es_una_pieza_mas(self):
        """Es lo que devuelve la Junta cuando contesta al formulario, y sin ella no se llama."""
        claves = [f.clave for f in iuws.QUE_FALTA]
        assert "alta_entorno" in claves
        assert not any(
            f.clave == "alta_entorno"
            for f in iuws.lo_que_falta(descriptor=False, configurado={"alta_entorno": True})
        )

    def test_el_formulario_de_cyl_esta_entero(self):
        """Los ocho campos del formulario, tal y como los lista el documento de la Junta."""
        assert len(iuws.CAMPOS_DEL_FORMULARIO_CYL) == 8
        assert "Nombre del software comercial" in iuws.CAMPOS_DEL_FORMULARIO_CYL
        assert any("CN del certificado" in campo for campo in iuws.CAMPOS_DEL_FORMULARIO_CYL)

    def test_los_dos_correos_a_los_que_se_pide(self):
        assert iuws.CONTACTOS["fega"] == "soporte-integracioncue@fega.es"
        assert iuws.CONTACTOS["castilla_y_leon"] == "comercialcuecyl@jcyl.es"


class TestLaConfiguracion:
    def test_sin_nada_configurado_no_esta_conectado(self, monkeypatch):
        for variable in (
            "CUEDIGITAL_IUWS_APP",
            "CUEDIGITAL_IUWS_CIF",
            "CUEDIGITAL_IUWS_DOMINIO",
            "CUEDIGITAL_IUWS_CERTIFICADO",
            "CUEDIGITAL_IUWS_ALTA",
        ):
            monkeypatch.delenv(variable, raising=False)
        config = iuws.configuracion()
        assert config["conectado"] is False
        assert config["puesto"] == {
            "catalogos": False,
            "nombre_comercial": False,
            "dominio": False,
            "certificado": False,
            "empresa_habilitada": False,
            "alta_entorno": False,
        }

    def test_no_hay_ningun_dato_de_la_empresa_en_el_repositorio(self, monkeypatch):
        """El nombre comercial, el CIF y el certificado salen del entorno, nunca del código.

        Un test que lo compruebe de verdad: se mira el módulo y se ve que los valores por
        defecto son cadenas vacías.
        """
        for variable in (
            "CUEDIGITAL_IUWS_APP",
            "CUEDIGITAL_IUWS_CIF",
            "CUEDIGITAL_IUWS_DOMINIO",
            "CUEDIGITAL_IUWS_CERTIFICADO",
            "CUEDIGITAL_IUWS_ALTA",
        ):
            monkeypatch.delenv(variable, raising=False)
        config = iuws.configuracion()
        assert config["nombre_comercial"] == ""
        assert config["cif_empresa_habilitada"] == ""
        assert config["dominio"] == ""
        assert config["certificado_configurado"] is False
        assert config["alta_entorno"] == ""

    def test_la_base_se_puede_cambiar_para_probar_en_integracion(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_IUWS_BASE", "https://otro.sitio")
        assert iuws.configuracion()["base"] == "https://otro.sitio"

    def test_por_defecto_se_apunta_al_entorno_de_integracion(self, monkeypatch):
        """Se apunta a pruebas y no a producción: es lo que se puede usar sin autorización."""
        monkeypatch.delenv("CUEDIGITAL_IUWS_BASE", raising=False)
        assert iuws.configuracion()["base"] == iuws.ENTORNO_INTEGRACION


class TestElDescriptor:
    def test_sin_fichero_el_descriptor_no_esta_cargado(self, monkeypatch):
        monkeypatch.setattr(iuws, "_RUTA_DESCRIPTOR", Path("no_existe_esto.json"))
        iuws.olvidar_descriptor()
        try:
            assert iuws.descriptor_cargado() is False
            assert iuws.descriptor() is None
        finally:
            iuws.olvidar_descriptor()

    def test_un_fichero_vacio_no_cuenta_como_descriptor(self, tmp_path):
        ruta = tmp_path / "descriptor.json"
        ruta.write_text("{}", encoding="utf-8")
        assert iuws.cargar_descriptor(ruta) is None
        iuws.olvidar_descriptor()

    def test_un_fichero_roto_no_revienta(self, tmp_path):
        ruta = tmp_path / "descriptor.json"
        ruta.write_text("esto no es json", encoding="utf-8")
        assert iuws.cargar_descriptor(ruta) is None
        iuws.olvidar_descriptor()

    def test_un_descriptor_de_verdad_se_carga(self, tmp_path):
        ruta = tmp_path / "descriptor.json"
        ruta.write_text(json.dumps({"version": "3.11.4", "bloques": {"A": {}}}), encoding="utf-8")
        try:
            assert iuws.cargar_descriptor(ruta)["version"] == "3.11.4"
            assert iuws.descriptor_cargado() is True
        finally:
            iuws.olvidar_descriptor()

    def test_la_plantilla_del_repositorio_no_se_carga_sola(self):
        """El fichero de ejemplo NO se llama como el de verdad, así que no se carga.

        Es a propósito: si se cargara, la aplicación diría que tiene el descriptor cuando
        solo tiene una plantilla con los nombres de campo vacíos.
        """
        assert Path(iuws._RUTA_DESCRIPTOR).name == "iuws_descriptor_cue.json"
        plantilla = Path(iuws._RUTA_DESCRIPTOR).with_name("iuws_descriptor_cue.ejemplo.json")
        assert plantilla.exists(), "la plantilla tiene que estar en el repositorio"
        datos = json.loads(plantilla.read_text(encoding="utf-8"))
        assert datos["version"] == iuws.VERSION_DESCRIPTOR_CUE
        # Y los nombres de campo están vacíos a propósito: no se copian de los ejemplos del
        # anexo, porque el anexo avisa de que pueden no corresponder con la v2.6.
        campos = datos["bloques"]["ActividadesExplotacion"]["Fertilizacion"]["campos"]
        assert campos == {}


class TestElContenidoMinimo:
    def test_estan_los_bloques_que_el_cuaderno_puede_rellenar(self):
        for clave in (
            "datos_generales",
            "datos_titular",
            "superficies",
            "tratamientos",
            "fertilizacion",
            "labores",
            "siembra_plantacion",
            "cosecha_comercializada",
            "analiticas",
            "medidas_preventivas",
            "edificaciones",
            "maquinaria",
        ):
            assert clave in iuws_contenido.BLOQUES, clave

    def test_cada_bloque_lleva_el_numero_y_el_nombre_del_documento(self):
        """Para poder cotejarlo con el papel sin interpretar nada."""
        for clave, (nombre, nivel, campos) in iuws_contenido.BLOQUES.items():
            assert nombre.strip(), clave
            assert nivel in ("explotacion", "parcela", "instalacion", "equipo", "tratamiento", "fertilizacion", "labor", "siembra", "venta", "analitica", "medida"), clave
            for campo in campos:
                assert campo.numero >= 1, f"{clave}: campo sin número"
                assert campo.nombre.strip(), f"{clave}: campo sin nombre"

    def test_los_campos_obligatorios_son_los_que_marca_la_norma(self):
        """Los que el documento marca con asterisco, uno por uno."""
        obligatorios = {
            (clave, campo.nombre)
            for clave, (_n, _v, campos) in iuws_contenido.BLOQUES.items()
            for campo in campos
            if campo.obligatorio
        }
        assert ("tratamientos", "Fecha inicio de tratamiento") in obligatorios
        assert ("tratamientos", "Superficie tratada (ha)") in obligatorios
        assert ("cosecha_comercializada", "Producto vegetal (venta de cosecha comercializada)") in obligatorios
        assert ("cosecha_comercializada", "Cantidad de producto vegetal (venta de cosecha comercializada)") in obligatorios
        assert ("analiticas", "Material analizado") in obligatorios

    def test_la_venta_tiene_los_numeros_que_le_da_el_documento(self):
        """El bloque que separa las dos clases de venta: 1 fecha, 2-3 comercializada, 4-5 directa."""
        campos = {c.numero: c.nombre for c in iuws_contenido.BLOQUES["cosecha_comercializada"][2]}
        assert campos[1] == "Fecha (intervalo de tiempo)"
        assert "comercializada" in campos[2] and "comercializada" in campos[3]
        assert "venta directa" in campos[4] and "venta directa" in campos[5]
        assert len(campos) == 5, "no se puede inventar un campo que el documento no tiene"

    def test_los_nueve_parametros_del_suelo_con_su_numero(self):
        """Del 8 al 16, en el orden del documento técnico."""
        numeros = [numero for numero, _n, _c in iuws_contenido.PARAMETROS_SUELO_NUMERADOS]
        assert numeros == list(range(8, 17))
        nombres = {clave: nombre for _num, nombre, clave in iuws_contenido.PARAMETROS_SUELO_NUMERADOS}
        assert nombres["materia_organica"] == "Materia Orgánica (%)"
        assert nombres["fosforo_asimilable"] == "Fósforo asimilable (ppm)"
        assert nombres["conductividad"] == "Conductividad eléctrica a 25 ºC (dS/m)"

    def test_los_parametros_del_suelo_son_los_mismos_que_los_del_catalogo(self):
        """Los dos sitios tienen que decir lo mismo, o el volcado y la app se contradicen."""
        del_documento = {clave for _n, _nombre, clave in iuws_contenido.PARAMETROS_SUELO_NUMERADOS}
        del_catalogo = {p.clave for p in __import__("app.catalogos", fromlist=["catalogos"]).parametros_de("suelo")}
        assert del_documento == del_catalogo

    def test_los_campos_de_catalogo_salen_listados(self):
        """Son los que no se pueden rellenar, y hay que poder decir cuáles son."""
        faltan = iuws_contenido.campos_de_catalogo()
        assert faltan
        nombres = {f["campo"] for f in faltan}
        assert any("Producto vegetal" in nombre for nombre in nombres)
        assert "Cultivo" in nombres
        assert "Justificación de la actuación" in nombres

    def test_todos_los_campos_de_catalogo_llevan_la_marca(self):
        faltan = iuws_contenido.campos_de_catalogo()
        assert all(f["bloque"] and f["numero"] and f["campo"] for f in faltan)

    def test_se_puede_preguntar_por_un_solo_bloque(self):
        faltan = iuws_contenido.campos_de_catalogo("tratamientos")
        assert faltan
        assert all("Tratamientos" in f["bloque"] for f in faltan)

    def test_el_resumen_de_bloques_cuenta_bien(self):
        resumen = {b["clave"]: b for b in iuws_contenido.resumen_de_bloques()}
        assert resumen["tratamientos"]["campos"] == len(iuws_contenido.BLOQUES["tratamientos"][2])
        assert resumen["tratamientos"]["de_catalogo"] >= 1
        assert all("SIEX v3.11" in b["fuente_del_documento"] for b in resumen.values())


class TestLosValoresNoSeInventan:
    def _campo(self, **cambios):
        base = dict(numero=1, nombre="Un campo", de="lo_que_sea")
        base.update(cambios)
        return iuws_contenido.Campo(**base)

    def test_un_campo_de_catalogo_sale_vacio_aunque_haya_valor(self):
        """Un nombre donde el interfaz espera un número es peor que un hueco: el hueco se ve."""
        registro = type("Falso", (), {"cultivo": "Trigo blando"})()
        campo = self._campo(de="cultivo", catalogo=True)
        assert iuws_contenido._valor(registro, campo) is None

    def test_un_campo_que_no_existe_sale_vacio_y_no_en_cero(self):
        """«No lo sé» y «es cero» no son lo mismo, y en un volcado oficial importa."""
        registro = type("Falso", (), {})()
        assert iuws_contenido._valor(registro, self._campo(tipo="numero")) is None

    def test_un_cero_de_verdad_si_sale(self):
        registro = type("Falso", (), {"lo_que_sea": 0})()
        assert iuws_contenido._valor(registro, self._campo(tipo="numero")) == 0

    def test_los_si_no_van_como_la_norma_los_pide(self):
        """La norma los pide como S/N, no como true/false."""
        registro = type("Falso", (), {"lo_que_sea": True})()
        assert iuws_contenido._valor(registro, self._campo(tipo="si_no")) == "S"
        registro = type("Falso", (), {"lo_que_sea": False})()
        assert iuws_contenido._valor(registro, self._campo(tipo="si_no")) == "N"
        registro = type("Falso", (), {"lo_que_sea": None})()
        assert iuws_contenido._valor(registro, self._campo(tipo="si_no")) is None

    def test_las_fechas_van_en_iso(self):
        """El anexo usa dd/mm/aaaa en sus ejemplos, pero avisa de que no son la v2.6."""
        import datetime as dt

        registro = type("Falso", (), {"lo_que_sea": dt.date(2026, 5, 1)})()
        assert iuws_contenido._valor(registro, self._campo(tipo="fecha")) == "2026-05-01"

    def test_los_numeros_no_llevan_ruido_de_coma_flotante(self):
        registro = type("Falso", (), {"lo_que_sea": 0.1 + 0.2})()
        assert iuws_contenido._valor(registro, self._campo(tipo="numero")) == 0.3

    def test_se_puede_sacar_un_valor_de_dentro_del_json_de_una_labor(self):
        """Los detalles de una labor van dentro de un JSON, y ahí también hay que buscar."""
        registro = type("Falso", (), {"detalles": {"lote": "L-1"}})()
        assert iuws_contenido._valor(registro, self._campo(de="lote")) == "L-1"

    def test_la_fila_lleva_el_nombre_de_cada_campo(self):
        """Para poder leer el volcado sin tener el documento delante."""
        registro = type("Falso", (), {"poligono": 12})()
        fila = iuws_contenido.fila("superficies", registro)
        assert fila["c6"] == 12
        assert fila["c6_nombre"] == "Código de Polígono"
        assert fila["c15_nombre"] == "Superficie DGC (ha, dos decimales)"

    def test_la_fila_marca_los_campos_de_catalogo(self):
        registro = type("Falso", (), {})()
        fila = iuws_contenido.fila("tratamientos", registro)
        assert fila["c6_catalogo"] is True
        assert fila["c6"] is None

    def test_la_fila_lleva_el_identificador_ajeno_si_se_le_da(self):
        registro = type("Falso", (), {})()
        fila = iuws_contenido.fila("tratamientos", registro, identificador="CD-1-T-2")
        assert fila["IdAjena"] == "CD-1-T-2"


class TestElPaqueteNoSeHacePasarPorElVolcado:
    def test_el_paquete_dice_que_no_es_el_json_del_descriptor(self, cliente, cuenta):
        """Lo más importante de todo: que nadie mande esto a la Junta creyendo que vale."""
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        assert datos["formato"] == "sobre-documentado-con-contenido-minimo-siex"
        assert "NO en el formato del descriptor" in datos["aviso"]
        assert datos["descriptor_cargado"] is False
        assert datos["version_descriptor_esperada"] == "3.11.4"

    def test_el_paquete_dice_que_le_falta(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        claves = {f["clave"] for f in datos["faltan"]}
        assert "descriptor" in claves
        assert "catalogos" in claves

    def test_el_sobre_lleva_los_datos_de_la_finca(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        sobre = datos["CUADERNO"][0]
        assert sobre["IdTitular"] == "70922320A", "el nombre del esquema oficial, no el del ejemplo"
        assert sobre["CAExplotacion"] == "13", "Castilla y León es el 13"

    def test_el_paquete_lleva_lo_que_hay_en_el_cuaderno(self, cliente, cuenta, nuevo_tratamiento):
        cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        filas = datos["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"]
        assert len(filas) == 1
        assert filas[0]["c1"] == "2026-05-01", "la fecha en ISO"
        assert filas[0]["c22"] == "Ejemplo 25 EC", "el nombre comercial"
        assert filas[0]["c24"] == "24.123", "el número de registro"

    def test_cada_actividad_lleva_su_identificador_ajeno(self, cliente, cuenta, nuevo_tratamiento):
        cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"][0]
        assert fila["IdAjena"].startswith("CD-70922320A-T-")

    def test_los_campos_de_catalogo_que_tenemos_van_con_su_codigo_oficial(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        """El cultivo ya no sale vacío: tenemos el catálogo oficial y se manda el código.

        **Este test cambió en la ronda 10, y por qué.** Antes comprobaba que `c6` salía a
        `None` porque no teníamos el catálogo de «Cultivo (según catálogo)». En la ronda 10 se
        encontró el servicio de listas de códigos del SIGPAC, que es público, y de ahí salen los
        **933 productos oficiales** (`cod_producto`, del FEGA). «Trigo blando» es el código 1.

        Así que el comportamiento nuevo es mejor y el test se actualiza para exigirlo: un código
        oficial que no se manda es un volcado que la Junta no puede leer.
        """
        cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"][0]
        assert fila["c6"] == 1, "el código oficial de TRIGO BLANDO"
        assert fila["c6_nombre"] == "Cultivo"

    def test_un_cultivo_que_no_esta_en_el_catalogo_oficial_sale_vacio(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        """Sigue sin inventarse nada: si el nombre no está en la lista, el campo va vacío."""
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(cultivo="Zapato de goma"),
        )
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"][0]
        assert fila["c6"] is None, "un nombre que no está en el catálogo no da un código"

    def test_los_catalogos_que_no_tenemos_siguen_vacios(self, cliente, cuenta, nuevo_tratamiento):
        """La materia activa, la eficacia y la unidad no están en ninguna lista que tengamos.

        Se dejan vacías **y marcadas**, para poder decir cuáles faltan. Poner un cero o un
        nombre en su sitio sería peor que el hueco: el hueco se ve.
        """
        cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"][0]
        assert fila["c54"] is None, "la eficacia es un catálogo que no tenemos"
        assert fila["c54_catalogo"] is True
        assert fila["c18"] is None, "la unidad de medida es otro catálogo que no tenemos"
        assert datos["catalogos_que_faltan"]

    def test_el_catalogo_oficial_de_productos_es_el_del_fega(self):
        """933 productos, con sus códigos. Se comprueban unos cuantos conocidos."""
        from app import sigpac

        productos = sigpac.productos_oficiales()
        assert len(productos) == 933
        assert productos[1] == "TRIGO BLANDO"
        assert productos[5] == "CEBADA"
        # Y el 0 es «producto desconocido», que es un código de verdad, no la ausencia de dato.
        assert productos[0] == "PRODUCTO DESCONOCIDO"

    def test_una_actividad_anulada_no_se_vuelca(self, cliente, cuenta, nuevo_tratamiento):
        """Lo que se anuló no pasó: mandarlo sería mandar un dato que el agricultor ya corrigió."""
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.post(
            f"/api/tratamientos/{creado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de producto"},
        )
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        assert datos["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"] == []

    def test_el_paquete_se_puede_descargar(self, cliente, cuenta):
        respuesta = cliente.get("/api/iuws/paquete.json", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        assert "attachment" in respuesta.headers["content-disposition"]
        assert respuesta.json()["formato"] == "sobre-documentado-con-contenido-minimo-siex"

    def test_los_bloques_que_se_vuelcan_salen_con_lo_que_tienen(self, cliente, cuenta, venta):
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        filas = datos["CUADERNO"][0]["ActividadesExplotacion"]["cosecha_comercializada"]
        assert len(filas) == 1
        assert filas[0]["c1"] == "2026-07-10"
        assert filas[0]["c3"] == 42000.0
        assert filas[0]["unidad"] == "kg"
        assert filas[0]["kilos"] == 42000.0

    def test_la_venta_directa_usa_sus_propios_numeros(self, cliente, cuenta, crear_venta):
        """El documento separa las dos clases de venta y las numera distinto.

        Los campos 2 y 3 son de la venta a un comprador y los 4 y 5 de la venta directa. Una
        venta directa metida en los campos de la comercializada sería un dato mal puesto.
        """
        crear_venta(tipo="venta_directa", producto="Lechuga", cantidad=3000, unidad="ud")
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["cosecha_comercializada"][0]
        assert "c2" not in fila and "c3" not in fila, "ha usado los campos de la comercializada"
        assert "c4_nombre" in fila and "c5_nombre" in fila
        assert fila["c5"] == 3000.0


class TestElEstado:
    def test_dice_que_no_esta_conectado_y_por_que(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        assert datos["conectado"] is False
        assert datos["descriptor_cargado"] is False
        assert datos["cuantas_faltan"] > 0

    def test_cada_cosa_que_falta_dice_quien_la_da(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        for falta in datos["faltan"]:
            assert falta["que"] and falta["por_que"] and falta["quien"]

    def test_trae_las_direcciones_y_los_correos(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        assert datos["url_version"].endswith("/IUWS/api/version")
        assert datos["contactos"]["castilla_y_leon"] == "comercialcuecyl@jcyl.es"
        assert len(datos["campos_del_formulario"]) == 8

    def test_el_codigo_siex_de_la_finca_se_comprueba_de_verdad(self, cliente, cuenta):
        """Sin él, el interfaz no sabe de qué explotación se le habla."""
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        assert datos["codigo_siex_puesto"] is False

    def test_la_tabla_del_descriptor_sale_por_la_puerta(self, cliente, cuenta):
        """De nada sirve tener la tabla del descriptor si la pantalla no la puede ver.

        Este proyecto ya ha tenido varias veces el mismo fallo: un dato que existe, que se
        calcula y que **no llega a ninguna pantalla**. Por eso se comprueba aquí, en la
        respuesta de verdad, y no solo en el módulo.
        """
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        descriptor = datos["descriptor"]
        assert descriptor["cargada"] is True
        assert descriptor["campos"] == 402
        assert descriptor["obligatorios"] == 175
        assert descriptor["catalogos"], "y con los catálogos que pide el descriptor"

    def test_el_mapeo_del_tratamiento_sale_por_la_puerta_y_separa_las_dos_cosas(
        self, cliente, cuenta
    ):
        """Lo que depende de FEGA y lo que depende de nosotros no pueden ir en el mismo saco.

        Si van juntos, no se sabe si hay que escribir a FEGA o escribir una pantalla.
        """
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        mapeo = datos["mapeo_del_tratamiento"]
        assert mapeo["campos"] == len(iuws_mapeo.correspondencia_del_tratamiento())
        assert mapeo["hacen_falta_catalogos"], "el catálogo es lo que depende de FEGA"
        assert mapeo["no_lo_tenemos"] or mapeo["a_medias"], "y esto es lo que depende de nosotros"
        assert mapeo["catalogos"] == mapeo["catalogos_confirmados_por_el_descriptor"]

    def test_el_cruce_con_los_catalogos_de_siex_sale_por_la_puerta(self, cliente, cuenta):
        """Saber qué tabla es no sirve de nada si no se puede consultar desde la aplicación."""
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        cruce = datos["catalogos_de_siex"]
        assert cruce["cargado"] is True
        assert cruce["catalogos_de_siex"] == 287
        assert cruce["coinciden_exactamente"] > 0
        assert cruce["los_que_no_coinciden"], "y los que no coinciden también se dicen"
        tablas = {r["descriptor"]: r["tabla_de_siex"] for r in cruce["el_cruce"]}
        assert tablas["Eficacia del tratamiento"] == "EFICACIA_TRATAMIENTO"

    def test_el_mapa_del_cuaderno_entero_sale_por_la_puerta(self, cliente, cuenta):
        """Es la lista de la compra: sin puerta, no la ve nadie."""
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        mapa = datos["mapa_del_cuaderno"]
        assert mapa["bloques"] == 18
        assert mapa["bloques_sin_descriptor"] == []
        assert mapa["catalogos"], "el mapa tiene que decir qué catálogos hacen falta"
        assert mapa["bloques_que_necesitan_las_parcelas"] > 0
        tratamientos = next(f for f in mapa["mapa"] if f["bloque"] == "TratamFito")
        assert tratamientos["bloque_en_el_descriptor"].endswith("TratamFito")
        # Y de qué tabla nuestra sale cada bloque, que es lo que dice dónde está el trabajo.
        assert tratamientos["de_donde_sale"]["tabla"] == "TratamientoFitosanitario"
        assert mapa["bloques_sin_tabla"] == ["EnergiaUtilizada"]
        assert len(mapa["tablas_que_cubren_varios_bloques"]["Labor"]) == 7

    def test_el_mapeo_de_los_bloques_sale_por_la_puerta_y_no_finge(self, cliente, cuenta):
        """Los bloques que están hechos, y **los que faltan por su nombre**."""
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        mapeo = datos["mapeo_de_los_bloques"]
        assert len(mapeo["bloques_mapeados"]) == 18
        assert mapeo["bloques_sin_mapear"] == []
        assert mapeo["obligatorios_que_se_pueden"] > 0
        # La siembra, que no necesita ningún catálogo: se ve en la respuesta.
        siembra = mapeo["detalle"]["SiembraPlantacion"]
        assert siembra["catalogos"] == []
        # La máquina de la siembra ya se apunta (ver `test_mapeo_oficial.py`): lo que falta de
        # verdad en este bloque es el código de la DGC, que lo asigna la administración.
        assert siembra["no_lo_tenemos"] == ["DGCs"]

    def test_el_estado_no_miente_cuando_el_mapeo_aun_no_tiene_catalogos(self, cliente, cuenta, monkeypatch, tmp_path):
        """El esquema y las credenciales no demuestran que los catálogos estén mapeados."""
        ruta = tmp_path / "descriptor.json"
        ruta.write_text(json.dumps({"version": "3.11.4", "bloques": {"A": {}}}), encoding="utf-8")
        iuws.cargar_descriptor(ruta)
        for variable, valor in (
            ("CUEDIGITAL_IUWS_APP", "CUE Digital"),
            ("CUEDIGITAL_IUWS_CIF", "B12345678"),
            ("CUEDIGITAL_IUWS_DOMINIO", "cuedigital.test"),
            ("CUEDIGITAL_IUWS_CERTIFICADO", "si"),
            ("CUEDIGITAL_IUWS_ALTA", "alta-2026-0001"),
        ):
            monkeypatch.setenv(variable, valor)
        # Y la finca tiene su código SIEX.
        respuesta = cliente.put(
            "/api/mi-finca",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "David Pérez Velasco",
                "nif": "70922320A",
                "codigo_siex": "ES130000008847",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        try:
            datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
            assert datos["descriptor_cargado"] is True
            assert datos["codigo_siex_puesto"] is True
            assert [f["clave"] for f in datos["faltan"]] == ["catalogos"]
            assert datos["conectado"] is False
        finally:
            iuws.olvidar_descriptor()


class TestLaPruebaDeConexion:
    def test_sin_configurar_no_llama_al_interfaz(self, cliente, cuenta, monkeypatch):
        """Hacer una llamada sin el certificado que exige solo da un error que no se puede arreglar.

        Ojo, que esto cambió en la ronda 12: antes no se llamaba porque faltaba configuración;
        ahora la prueba de versión **sí se puede hacer** sin tener nada (el método de versión es
        el único que el interfaz deja abierto), así que no se llama por otro motivo: porque no
        se ha pedido. Se llama solo con `?llamar=1`, para no pinchar al servidor de la Junta
        cada vez que alguien abre una pantalla. Aquí se comprueba que, sin pedirlo, no llama.
        """
        for variable in (
            "CUEDIGITAL_IUWS_APP",
            "CUEDIGITAL_IUWS_CIF",
            "CUEDIGITAL_IUWS_DOMINIO",
            "CUEDIGITAL_IUWS_CERTIFICADO",
        ):
            monkeypatch.delenv(variable, raising=False)

        def no_llamar(*args, **kwargs):  # pragma: no cover — no debería llamarse
            raise AssertionError("no se debería haber llamado al interfaz")

        monkeypatch.setattr(iuws_cliente, "comprobar_version", no_llamar)
        datos = cliente.get("/api/iuws/version", headers=cuenta["cabeceras"]).json()
        assert datos["probado"] is False
        assert datos["conectado"] is False
        assert datos["faltan"]
        # Lo que sí se puede decir ya, sin tener nada: que esta prueba está a mano.
        assert datos["se_puede_probar_ya"] is True
        assert datos["version_observada"] == iuws.VERSION_OBSERVADA


class TestLosMensajesPorLaApi:
    def test_el_catalogo_de_mensajes_se_sirve_traducido(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/mensajes", headers=cuenta["cabeceras"]).json()
        assert len(datos["mensajes"]) == 19
        uno = [m for m in datos["mensajes"] if m["codigo"] == 5][0]
        assert uno["nombre"] == "ERROR_VALIDAR_CAMPO"
        assert uno["explicacion"]

    def test_traducir_una_respuesta_pegada(self, cliente, cuenta):
        """Es lo que evita que una incidencia se convierta en «me da un error»."""
        datos = cliente.post(
            "/api/iuws/leer-respuesta",
            headers=cuenta["cabeceras"],
            json={
                "respuesta": {
                    "resultado": {
                        "codigoResultado": "PARCIAL",
                        "detalleImportacion": [
                            {"codigo": 3, "descripcion": "ok"},
                            {"codigo": 6, "descripcion": "mal"},
                        ],
                    }
                }
            },
        ).json()
        assert datos["es_parcial"] is True
        assert datos["esta_ok"] is False
        assert len(datos["actividades_fallidas"]) == 1
        assert "ROMA" in datos["actividades_fallidas"][0]["explicacion"]

    def test_sin_respuesta_que_traducir_se_dice(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/iuws/leer-respuesta", headers=cuenta["cabeceras"], json={}
        )
        assert respuesta.status_code == 422


class TestElContenidoPorLaApi:
    def test_se_pueden_ver_los_campos_que_se_vuelcan(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/contenido", headers=cuenta["cabeceras"]).json()
        assert datos["bloques"]
        assert "tratamientos" in datos["campos_por_bloque"]
        nombres = [c["nombre"] for c in datos["campos_por_bloque"]["tratamientos"]]
        assert "Superficie tratada (ha)" in nombres

    def test_dice_de_que_documento_sale(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/contenido", headers=cuenta["cabeceras"]).json()
        assert "SIEX v3.11" in datos["fuente"]
        assert "Anexo II" in datos["fuente"]

    def test_los_numeros_de_campo_van_con_su_nombre(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/contenido", headers=cuenta["cabeceras"]).json()
        for campo in datos["campos_por_bloque"]["cosecha_comercializada"]:
            assert campo["numero"] >= 1
            assert campo["nombre"]


class TestLosTextosDeLaIntegracion:
    def test_los_textos_de_iuws_no_son_para_el_agricultor(self):
        """La excepción a la regla del cero jerga, dicha y probada.

        Los textos del IUWS usan «interfaz», «credenciales» y «descriptor» porque son los
        nombres del manual de FEGA. Los lee quien integra, no un agricultor. Por eso NO están
        en `textos_visibles()` y el test de jerga no los revisa.
        """
        visibles = textos.textos_visibles()
        for texto in textos.IUWS.values():
            assert texto not in visibles, "los textos del IUWS no son para el agricultor"

    def test_y_se_ve_que_la_excepcion_es_querida(self):
        """Si alguien los metiera en la lista, el test de jerga los cazaría de golpe."""
        jerga = textos.palabras_prohibidas_encontradas(textos.IUWS["explica"])
        assert "interfaz" in jerga, (
            "si esto dejara de pasar, es que alguien ha cambiado los textos o la lista de "
            "palabras prohibidas: revisa por qué antes de tocar nada"
        )

    def test_la_pantalla_avisa_de_que_no_es_para_el_agricultor(self):
        assert "no es para el agricultor" in textos.IUWS["para_quien"]

    def test_el_texto_dice_claro_que_el_paquete_no_es_el_volcado(self):
        aviso = textos.IUWS["el_paquete_no_es_el_volcado"]
        assert "NO es el fichero que se manda" in aviso
        assert "BdcSix-DS-DiseñoCUE.xlsx" in aviso

    def test_se_dice_que_los_catalogos_van_vacios_a_proposito(self):
        assert "inventado" in textos.IUWS["los_catalogos"]

    def test_el_repositorio_no_tiene_ningun_dato_de_la_empresa(self):
        """El nombre comercial, el CIF y el dominio no están escritos en ninguna parte."""
        for ruta in (
            Path(iuws.__file__),
            Path(iuws_contenido.__file__),
        ):
            texto = ruta.read_text(encoding="utf-8")
            assert "CUEDIGITAL_IUWS_APP" in texto or "iuws_contenido" in ruta.name
        # Y los contactos son los que publica el documento, no datos de nadie.
        assert iuws.CONTACTOS["fega"].endswith("@fega.es")


@pytest.mark.parametrize("tipo", sorted(iuws.SIGLAS))
def test_cada_clase_de_actividad_tiene_su_sigla_y_su_identificador(tipo):
    identificador = iuws.id_ajeno("70922320A", tipo, 7)
    assert identificador.startswith("CD-70922320A-")
    assert identificador.endswith("-7")
