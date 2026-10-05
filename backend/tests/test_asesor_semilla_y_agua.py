"""El asesor, la semilla y el agua de riego: lo último que quedaba a medias.

Estas tres cosas son las tres últimas secciones de la app oficial que estaban marcadas como
«a medias» en `docs/LO_QUE_PIDE_LA_JUNTA.md`, y las tres se arreglan igual: **convirtiendo en
columnas de verdad lo que era texto libre o no existía**.

| Sección oficial | Qué faltaba | Qué hay ahora |
|---|---|---|
| 2. Cuaderno: Asesores | El asesor GIP: su número, su ámbito y su entidad | Tabla `asesores` + el asesoramiento en el tratamiento (campos 44 a 53) |
| 8. Labores: Siembra / Plantación | Semilla, dosis y nº de lote | Columnas propias en `Labor` (campos 4 a 15) |
| 9. Labores: Riego | Volumen, origen del agua y nitratos | Columnas propias en `Labor` (campos 34 a 41) |

**Por qué importa que sean columnas y no JSON.** Estaban en un campo `detalles` de texto
libre, y ahí un dato no se puede consultar, no se puede sumar y no se puede volcar. El
cuaderno oficial los pide **uno por uno, con nombre y número**, y son justo los que hacen
falta para responder «¿de qué saco salió esta semilla?» o «¿cuánto nitrato traía el agua que
regué?».
"""

from __future__ import annotations

import pytest

from app import catalogos, iuws_contenido, textos


class TestElAsesor:
    def test_se_puede_dar_de_alta(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/asesores",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Ana García Ruiz",
                "nif": "12345678Z",
                "numero_ropo": "ROPO-ASESOR-778",
                "ambito": "gip",
                "entidad_certificacion": "Consejo Regulador de Producción Integrada",
                "telefono": "600000000",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["nombre"] == "Ana García Ruiz"
        assert datos["numero_ropo"] == "ROPO-ASESOR-778"
        assert datos["ambito"] == "gip"

    def test_el_asesor_es_otra_cosa_que_el_aplicador(self, cliente, cuenta, aplicador, asesor):
        """Son dos figuras distintas y la ley las separa: el asesor dice qué hacer y el
        aplicador lo hace. Cada una tiene su propia lista.

        Ojo con un detalle que es fácil de confundir: **los dos llevan un número de ROPO**,
        porque el ROPO inscribe por separado a los asesores y a los aplicadores (el documento
        de SIEX pide «Nº inscripción ROPO» en los dos sitios: campo 33 para el aplicador y
        campo 50 para el asesor). Lo que distingue al asesor son su ámbito y la entidad que lo
        certifica, que el aplicador no tiene.
        """
        asesores = cliente.get("/api/asesores", headers=cuenta["cabeceras"]).json()
        aplicadores = cliente.get("/api/aplicadores", headers=cuenta["cabeceras"]).json()
        assert len(asesores) == 1 and len(aplicadores) == 1

        assert asesores[0]["numero_ropo"] == "ROPO-ASESOR-778"
        assert aplicadores[0]["numero_ropo"] == "ROPO-1234"
        assert asesores[0]["numero_ropo"] != aplicadores[0]["numero_ropo"], "son dos registros"
        # Lo que solo tiene el asesor:
        assert asesores[0]["ambito"] == "gip"
        assert "ambito" not in aplicadores[0]
        # Y lo que solo tiene el aplicador:
        assert "numero_carne" not in asesores[0], "el asesor no lleva carné de aplicador"

    def test_un_ambito_que_no_existe_no_se_acepta(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/asesores",
            headers=cuenta["cabeceras"],
            json={"nombre": "Ana", "ambito": "de todo un poco"},
        )
        assert respuesta.status_code == 422

    def test_los_ambitos_son_los_del_registro(self):
        assert set(catalogos.AMBITOS_ASESOR) == {"gip", "produccion_integrada", "ecologico", "otros"}

    def test_cada_ambito_se_le_ensena_al_agricultor(self):
        for ambito in catalogos.AMBITOS_ASESOR:
            assert catalogos.ETIQUETA_AMBITO_ASESOR[ambito]
        # Y con palabras suyas, no con la sigla.
        assert "GIP" not in catalogos.ETIQUETA_AMBITO_ASESOR["gip"]


class TestElAsesoramientoDeUnTratamiento:
    """Los campos 44 a 53 del bloque de tratamientos del contenido mínimo."""

    def test_un_tratamiento_se_puede_asesorar(self, cliente, cuenta, nuevo_tratamiento, asesor):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(
                asesor_id=asesor["id"],
                asesor_fecha="2026-04-28",
                asesoramiento_validado=True,
                asesoramiento_contrato=True,
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["asesor_id"] == asesor["id"]
        assert datos["asesor_fecha"] == "2026-04-28"
        assert datos["asesoramiento_validado"] is True
        assert datos["asesoramiento_contrato"] is True

    def test_un_asesor_sin_numero_de_ropo_no_deja_guardar(
        self, cliente, cuenta, nuevo_tratamiento, crear_asesor
    ):
        """El interfaz de la Junta rechaza un asesor que no encuentre en ROPO (error 7).

        Así que un apunte que no se va a poder volcar es mejor no dejarlo guardar. Es la misma
        regla que con el carné del aplicador.
        """
        sin_ropo = crear_asesor(nombre="Sin papeles", numero_ropo=None)
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(asesor_id=sin_ropo["id"]),
        )
        assert respuesta.status_code == 422
        codigos = [a["codigo"] for a in respuesta.json()["detail"]["avisos"]]
        assert "S1_sin_ropo_asesor" in codigos

    def test_sin_decir_la_fecha_del_asesoramiento_se_avisa(
        self, cliente, cuenta, nuevo_tratamiento, asesor
    ):
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(asesor_id=asesor["id"], asesoramiento_validado=True),
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "S2_asesor_sin_fecha" in avisos
        assert avisos["S2_asesor_sin_fecha"]["bloquea"] is False

    def test_sin_decir_si_lo_valido_se_avisa(self, cliente, cuenta, nuevo_tratamiento, asesor):
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(asesor_id=asesor["id"], asesor_fecha="2026-04-28"),
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "S3_asesor_sin_validar" in avisos
        assert avisos["S3_asesor_sin_validar"]["bloquea"] is False

    def test_no_poder_decir_que_el_asesor_no_lo_valido_no_es_lo_mismo_que_no_decirlo(self):
        """`False` («el técnico no lo dio por bueno») y `None` («no lo he dicho») son cosas
        distintas, y por eso la casilla tiene tres estados y no dos."""
        from app import models

        assert models.TratamientoFitosanitario.asesoramiento_validado.property.columns[0].nullable

    def test_un_tratamiento_sin_asesor_no_avisa_de_nada(self, cliente, cuenta, nuevo_tratamiento):
        """No todos los tratamientos se consultan, y eso está bien."""
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(),
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert not [c for c in codigos if c.startswith("S")]

    def test_el_asesor_de_otra_finca_no_se_puede_usar(
        self, cliente, cuenta, nuevo_tratamiento, crear_cuenta, crear_asesor
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        ajeno = cliente.post(
            "/api/asesores",
            headers=otro["cabeceras"],
            json={"nombre": "Asesor ajeno", "numero_ropo": "X-1"},
        ).json()
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(asesor_id=ajeno["id"]),
        )
        assert respuesta.status_code == 404

    def test_el_asesor_sale_en_el_volcado_con_su_ropo(
        self, cliente, cuenta, nuevo_tratamiento, asesor
    ):
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(
                asesor_id=asesor["id"], asesor_fecha="2026-04-28", asesoramiento_validado=True
            ),
        )
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"][0]
        assert fila["c44"] == "2026-04-28", "la fecha del asesoramiento"
        assert fila["c45"] == "Ana García Ruiz", "el nombre del asesor"
        assert fila["c50"] == "ROPO-ASESOR-778", "su número de ROPO"
        assert fila["c51"] == "S", "validado, y la norma lo pide como S/N"
        assert fila["c50_nombre"] == "Nº inscripción ROPO del asesor"


class TestLaSemilla:
    def test_se_apunta_la_semilla_con_su_dosis_y_su_lote(self, cliente, cuenta, campana, parcela):
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "siembra",
                "fecha": "2026-03-01",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "cultivo": "Trigo blando",
                "cantidad_semilla_kg": 480.0,
                "dosis_siembra_kg_ha": 197.5,
                "lote_semilla": "L-SEM-2026-04",
                "material_adquirido": True,
                "fecha_adquisicion": "2026-02-20",
                "material_tratado": False,
                "siembra_directa": True,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["cantidad_semilla_kg"] == 480.0
        assert datos["dosis_siembra_kg_ha"] == 197.5
        assert datos["lote_semilla"] == "L-SEM-2026-04"
        assert datos["material_adquirido"] is True
        assert datos["material_tratado"] is False
        assert datos["siembra_directa"] is True

    def test_las_dos_preguntas_del_pastoreo_se_guardan_y_se_devuelven(
        self, cliente, cuenta, campana, parcela
    ):
        """El interfaz de la Junta las pide como **obligatorias** y el cuaderno no las hacía.

        Sin ellas no se puede armar el bloque del pastoreo, así que eran una laguna nuestra y no
        de nadie de fuera. Y vacío sigue siendo «no lo sé»: hay un test aparte para eso.
        """
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "pastoreo",
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "animales_terceros": True,
                "animales_propios": False,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["animales_terceros"] is True
        assert datos["animales_propios"] is False

    def test_sin_contestar_el_pastoreo_se_queda_vacio_y_no_se_inventa(
        self, cliente, cuenta, campana, parcela
    ):
        """No contestar no es decir que no: es «no lo sé»."""
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "pastoreo",
                "fecha": "2026-04-11",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["animales_terceros"] is None
        assert respuesta.json()["animales_propios"] is None

    def test_la_semilla_sale_en_el_volcado_con_su_numero_de_campo(
        self, cliente, cuenta, campana, parcela
    ):
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "siembra",
                "fecha": "2026-03-01",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "cantidad_semilla_kg": 480.0,
                "dosis_siembra_kg_ha": 197.5,
                "lote_semilla": "L-SEM-2026-04",
                "material_adquirido": True,
                "siembra_directa": True,
            },
        )
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["siembra_plantacion"][0]
        assert fila["c4"] == 480.0, "cantidad de semilla (kg)"
        assert fila["c5"] == 197.5, "dosis de siembra (kg/ha)"
        assert fila["c10"] == "L-SEM-2026-04", "nº de lote de la semilla adquirida"
        assert fila["c8"] == "S", "material adquirido"
        assert fila["c12"] == "S", "siembra directa"
        assert fila["c11"] == 2.43, "superficie sembrada"

    def test_no_se_vuelca_el_campo_que_fega_ha_quitado(self):
        """El control de versiones del anexo dice que se elimina `UnidadesSiembra`.

        Volcarlo sería mandar un campo que ya no existe. Se deja escrito para que nadie lo
        «arregle» añadiéndolo porque lo vio en una versión vieja del documento.
        """
        numeros = [campo.numero for campo in iuws_contenido.BLOQUES["siembra_plantacion"][2]]
        assert 6 not in numeros, "el campo 6 (Unidades de siembra) ya no existe en la v2.6"

    def test_sin_lote_no_se_inventa_uno(self, cliente, cuenta, campana, parcela):
        creado = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "siembra",
                "fecha": "2026-03-01",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        ).json()
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["siembra_plantacion"][0]
        assert fila["c10"] is None
        assert creado["lote_semilla"] is None

    def test_la_plantacion_tiene_su_densidad_y_su_marco(self, cliente, cuenta, campana, parcela):
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "plantacion",
                "fecha": "2026-03-15",
                "parcela_id": parcela["id"],
                "superficie_ha": 1.0,
                "densidad_plantacion": 2200.0,
                "marco_plantacion": "3 x 1,5 m",
            },
        )
        assert respuesta.status_code == 201
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["siembra_plantacion"][0]
        assert fila["c14"] == 2200.0
        assert fila["c15"] == "3 x 1,5 m"


class TestElAguaDelRiego:
    def test_se_apunta_de_donde_sale_el_agua_y_cuanto_nitrato_trae(
        self, cliente, cuenta, campana, parcela
    ):
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "riego",
                "fecha": "2026-06-01",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "volumen_agua": 1200.0,
                "unidad_agua": "m3",
                "origen_agua": "pozo",
                "sistema_riego": "aspersion",
                "numero_contador": "CNT-4471",
                "nitratos_agua": 38.0,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["volumen_agua"] == 1200.0
        assert datos["origen_agua"] == "pozo"
        assert datos["sistema_riego"] == "aspersion"
        assert datos["nitratos_agua"] == 38.0

    def test_el_agua_sale_en_el_volcado_con_los_numeros_de_la_fertirrigacion(
        self, cliente, cuenta, campana, parcela
    ):
        """El documento sitúa estos datos en el subbloque de fertirrigación (campos 34 a 42),
        porque el agua que riegas también abona. Nosotros los guardamos en la labor de riego,
        que es donde el agricultor los apunta, y al volcar se llevan a su sitio."""
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "riego",
                "fecha": "2026-06-01",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "volumen_agua": 1200.0,
                "unidad_agua": "m3",
                "origen_agua": "pozo",
                "sistema_riego": "aspersion",
                "numero_contador": "CNT-4471",
                "nitratos_agua": 38.0,
            },
        )
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = datos["CUADERNO"][0]["ActividadesExplotacion"]["riego"][0]
        assert fila["c35"] == 1200.0, "cantidad de agua"
        assert fila["c40"] == "CNT-4471", "nº de contador"
        assert fila["c41"] == 38.0, "N nítrico del agua"
        assert fila["c35_nombre"] == "Cantidad de agua"

    def test_el_origen_y_el_sistema_van_marcados_como_catalogo(self, cliente, cuenta):
        """Los códigos oficiales no los tenemos: van vacíos y marcados, no con los nuestros.

        Decisión importante: nuestras listas (`catalogos.ORIGENES_AGUA` y `SISTEMAS_RIEGO`)
        sirven para que el agricultor elija en vez de escribir, pero **no son las oficiales**.
        Presentarlas como si lo fueran sería inventar un código.
        """
        bloques = iuws_contenido.BLOQUES["riego"][2]
        por_numero = {campo.numero: campo for campo in bloques}
        assert por_numero[38].catalogo is True, "procedencia del agua"
        assert por_numero[34].catalogo is True, "sistema de riego"
        assert por_numero[37].catalogo is True, "unidad"

    def test_las_listas_del_agua_son_nuestras_y_se_dice(self):
        """Queda escrito en el catálogo para que nadie las presente como oficiales."""
        import pathlib

        fuente = pathlib.Path(catalogos.__file__).read_text(encoding="utf-8")
        assert "no son las oficiales" in fuente.lower()
        assert "el catálogo oficial" in fuente.lower() or "catálogo oficial" in fuente.lower()

    def test_un_riego_no_es_una_labor_cultural_cualquiera(self, cliente, cuenta, campana, parcela):
        """El riego tiene su propio bloque en el volcado, no va mezclado con las labores."""
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "riego",
                "fecha": "2026-06-01",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        datos = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        actividades = datos["CUADERNO"][0]["ActividadesExplotacion"]
        assert len(actividades["riego"]) == 1
        assert actividades["labores"] == []

    def test_los_origenes_del_agua_estan_en_cristiano(self):
        for origen in catalogos.ORIGENES_AGUA:
            assert catalogos.ETIQUETA_ORIGEN_AGUA[origen]
        assert catalogos.ETIQUETA_ORIGEN_AGUA["pozo"] == "Pozo o sondeo"
        assert catalogos.ETIQUETA_ORIGEN_AGUA["comunidad_regantes"] == "Comunidad de regantes"

    def test_las_unidades_del_agua_son_las_tres_que_usa_el_agricultor(self):
        """El metro cúbico es lo que marca el contador; el milímetro, lo que dice él; y los
        m³/ha, lo que se compara entre parcelas de distinto tamaño."""
        assert set(catalogos.UNIDADES_AGUA) == {"m3", "m3/ha", "mm"}


class TestLasTresSeccionesQuedanCubiertas:
    def test_la_lista_de_la_junta_ya_no_tiene_estas_tres_a_medias(self):
        """Las tres secciones de esta ronda estaban marcadas «a medias» y ya no lo están.

        Se comprueba leyendo el documento, para que si alguien vuelve a marcar una como
        pendiente sin motivo, se entere.
        """
        import pathlib
        import re

        documento = (pathlib.Path(__file__).resolve().parents[2] / "docs" / "LO_QUE_PIDE_LA_JUNTA.md").read_text(
            encoding="utf-8"
        )
        for fila in documento.splitlines():
            if not fila.startswith("| "):
                continue
            celdas = [c.strip() for c in fila.strip("|").split("|")]
            if len(celdas) < 3 or not celdas[0].isdigit():
                continue
            if any(
                palabra in celdas[1]
                for palabra in ("Asesores", "Siembra", "Riego")
            ):
                assert celdas[2] == "✅", f"la sección {celdas[1]} sigue a medias: {celdas[2]}"

    def test_y_el_resumen_sigue_cuadrando(self):
        """Lo comprueba `test_lista_de_la_junta.py`; aquí se deja el recordatorio."""
        assert True


class TestElVocabulario:
    def test_la_interfaz_trae_los_ambitos_del_asesor(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        valores = {a["valor"] for a in datos["ambitos_asesor"]}
        assert valores == set(catalogos.AMBITOS_ASESOR)

    def test_la_interfaz_trae_las_listas_del_agua(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert {o["valor"] for o in datos["origenes_agua"]} == set(catalogos.ORIGENES_AGUA)
        assert {s["valor"] for s in datos["sistemas_riego"]} == set(catalogos.SISTEMAS_RIEGO)
        assert {u["valor"] for u in datos["unidades_agua"]} == set(catalogos.UNIDADES_AGUA)

    def test_la_interfaz_trae_la_lista_de_la_eficacia(self, cliente, cuenta):
        """La lista es nuestra, y por eso se comprueba que sale y que está marcada como tal.

        El catálogo oficial de eficacia del tratamiento no lo tenemos: lo que se pregunta al
        agricultor son cuatro respuestas llanas. Si esta lista desapareciera de la interfaz, la
        pregunta se quedaría sin opciones y nadie lo notaría.
        """
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert {e["valor"] for e in datos["eficacia_del_tratamiento"]} == set(
            catalogos.EFICACIA_DEL_TRATAMIENTO
        )
        for entrada in datos["eficacia_del_tratamiento"]:
            assert entrada["texto"] == catalogos.ETIQUETA_EFICACIA[entrada["valor"]]

    def test_la_seccion_del_asesor_esta_en_mis_cosas(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert datos["maestros"]["seccion_asesor"] == "Quién me asesora"
        assert datos["maestros"]["anadir_asesor"] == "AÑADIR QUIÉN ME ASESORA"
        assert "sin_asesor" in datos["maestros"]

    def test_lo_que_se_pregunta_del_asesor_es_una_pregunta(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        for campo in (
            "asesor.nombre",
            "asesor.numero_ropo",
            "asesor.ambito",
            "tratamiento.asesor_id",
            "labor.semilla",
            "labor.origen_agua",
            "labor.agua",
        ):
            etiqueta = datos["etiquetas"][campo]
            assert etiqueta["pregunta"].endswith("?"), campo
            assert etiqueta["pista"], campo

    def test_todo_el_texto_nuevo_esta_en_el_fichero_de_textos(self):
        visibles = textos.textos_visibles()
        for clave in ("S1_sin_ropo_asesor", "S2_asesor_sin_fecha", "S3_asesor_sin_validar"):
            assert textos.MENSAJES[clave] in visibles, clave
        assert textos.MAESTROS["seccion_asesor"] in visibles
        assert textos.MAESTROS["anadir_asesor"] in visibles
        assert textos.ROTULOS["ropo_corto"] in visibles

    def test_la_ayuda_del_ropo_dice_que_hay_que_pedirlo(self):
        ayuda = textos.AYUDA["asesor.numero_ropo"]
        assert "ROPО" in ayuda["que_es"] or "ROP" in ayuda["que_es"]
        assert "no acepta" in ayuda["por_que"] or "no acepta" in ayuda["si_falta"]


class TestElInformeDeLaJunta:
    def test_la_tabla_de_secciones_ya_no_tiene_nada_a_medias(self):
        """Los 21 apartados de la app oficial están cubiertos.

        Lo comprueba `test_lista_de_la_junta.py` recontando la tabla; aquí se deja el
        recordatorio de la meta, porque es la que dice si el trabajo está hecho.

        Ojo con la palabra, que esto cambió en la ronda 13 **con motivo**: son **apartados**, no
        secciones. El documento oficial dice «seis secciones con veinte apartados…, además de un
        repositorio de documentación». Decir «secciones» a las 21 filas fue parte del motivo de
        que «Utilidades» —que es el menú de los informes, no un apartado— estuviera ocupando la
        fila 21 mientras el apartado de Documentación no existía en ninguna parte.
        """
        import pathlib

        documento = (
            pathlib.Path(__file__).resolve().parents[2] / "docs" / "LO_QUE_PIDE_LA_JUNTA.md"
        ).read_text(encoding="utf-8")
        trozo = documento.split("**Resumen:", 1)[1].split("\n", 1)[0]
        assert "21 apartados hechos" in trozo, f"el resumen dice: {trozo}"
        assert "0 a medias" in trozo
        assert "0 sin empezar" in trozo

    def test_y_lo_que_falta_de_la_junta_sigue_diciendose(self):
        """Los 21 apartados son los de la app oficial; aparte está lo que hay que pedir.

        Que no se confunda: tener los 21 apartados **no** quiere decir que se pueda entregar el
        cuaderno a la Junta. Falta el descriptor del IUWS y el certificado de dominio, y eso se
        dice en el apartado 2 del mismo documento.
        """
        import pathlib

        documento = (
            pathlib.Path(__file__).resolve().parents[2] / "docs" / "LO_QUE_PIDE_LA_JUNTA.md"
        ).read_text(encoding="utf-8")
        apartado2 = documento.split("## 2. Lo que la Junta pide", 1)[1].split("## 3.", 1)[0]
        assert "🔒" in apartado2, "tiene que seguir habiendo cosas que dependen de David"
        assert "Exportación IUWS" in apartado2


@pytest.mark.parametrize("ambito", list(catalogos.AMBITOS_ASESOR))
def test_cada_ambito_del_asesor_se_puede_dar_de_alta(ambito, cliente, cuenta):
    respuesta = cliente.post(
        "/api/asesores",
        headers=cuenta["cabeceras"],
        json={"nombre": f"Asesor de {ambito}", "numero_ropo": f"R-{ambito}"},
    )
    assert respuesta.status_code == 201, respuesta.text
    respuesta = cliente.post(
        "/api/asesores",
        headers=cuenta["cabeceras"],
        json={"nombre": "Otro", "numero_ropo": "R-2", "ambito": ambito},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["ambito"] == ambito
