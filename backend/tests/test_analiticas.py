"""Los análisis de laboratorio.

Esta sección existe por dos motivos, y los dos se prueban aquí:

1. **Cumplir.** La app oficial de Castilla y León tiene «Otras Actividades: Analíticas», y
   el contenido mínimo del CUE (documento técnico SIEX v3.11, bloque 13) fija qué tiene que
   poder apuntarse: material analizado, fecha de toma de muestra, laboratorio con su razón
   social y su NIF, número de boletín, tipo de análisis, sustancia detectada y los nueve
   parámetros del suelo.

2. **Que sirva.** Un análisis que solo se puede mirar es un papel en una pantalla. Lo que
   se prueba de verdad es que el plan de abono pueda apoyarse en él, que los parámetros
   tengan claves y no texto libre, y que un número que no exista en el catálogo no se cuele.

Y una cosa que NO se prueba porque no se hace: comparar el nitrato del agua con un límite
legal. El programa de actuación de Castilla y León (Orden MAV/398/2022) no está cargado, y
el test `test_no_se_inventa_un_limite_de_nitratos` deja escrito que es a propósito.
"""

from __future__ import annotations

import io

from app import catalogos, textos


# --------------------------------------------------------------------------
# Lo que pide el contenido mínimo del CUE
# --------------------------------------------------------------------------


class TestLoQuePideLaNorma:
    def test_se_puede_apuntar_un_analisis_completo(self, cliente, cuenta, parcela):
        respuesta = cliente.post(
            "/api/analiticas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": cliente.get(
                    "/api/campanas/actual", headers=cuenta["cabeceras"]
                ).json()["id"],
                "tipo": "suelo",
                "fecha_toma_muestra": "2026-02-14",
                "fecha_resultado": "2026-02-28",
                "parcela_id": parcela["id"],
                "laboratorio": "Laboratorio Agrario de Villamoriel",
                "nif_laboratorio": "B34123456",
                "numero_informe": "2026/0417",
                "tipo_analisis": "Análisis completo de fertilidad",
                "parametros": [
                    {"clave": "materia_organica", "valor": 1.8},
                    {"clave": "ph", "valor": 7.4},
                    {"clave": "fosforo_asimilable", "valor": 18.0},
                ],
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["laboratorio"] == "Laboratorio Agrario de Villamoriel"
        assert datos["nif_laboratorio"] == "B34123456"
        assert datos["numero_informe"] == "2026/0417"
        assert datos["tipo_analisis"] == "Análisis completo de fertilidad"
        assert len(datos["parametros"]) == 3

    def test_los_nueve_parametros_del_suelo_estan_en_el_catalogo(self):
        """Los nueve del bloque 13 del contenido mínimo del CUE, ni uno menos."""
        claves = {p.clave for p in catalogos.parametros_de("suelo")}
        assert claves == {
            "materia_organica",
            "arena",
            "limo",
            "arcilla",
            "ph",
            "fosforo_asimilable",
            "potasio_asimilable",
            "nitrogeno_total",
            "conductividad",
        }

    def test_los_parametros_del_suelo_son_los_oficiales(self):
        """Y están marcados como oficiales: de dónde sale cada lista queda escrito."""
        assert all(p.oficial for p in catalogos.parametros_de("suelo"))

    def test_lo_que_no_fija_ninguna_norma_va_marcado_como_tal(self):
        """De agua, planta, cosecha y residuos no hay listado oficial: se dice."""
        for tipo in ("agua_riego", "cultivo", "producto_cosechado", "residuos"):
            parametros = catalogos.parametros_de(tipo)
            assert parametros, f"{tipo} no tiene ningún parámetro"
            assert not any(p.oficial for p in parametros), tipo

    def test_los_cinco_tipos_de_la_app_oficial(self):
        """Cultivos, productos cosechados, suelo y agua de riego, más los residuos."""
        assert set(catalogos.TIPOS_ANALITICA) == {
            "suelo",
            "agua_riego",
            "cultivo",
            "producto_cosechado",
            "residuos",
        }

    def test_cada_tipo_tiene_su_nombre_para_el_agricultor(self):
        for tipo in catalogos.TIPOS_ANALITICA:
            assert catalogos.ETIQUETA_ANALITICA[tipo]

    def test_se_guarda_la_unidad_con_cada_valor(self, crear_parcela, crear_analitica):
        parcela = crear_parcela()
        guardado = crear_analitica(parcela_id=parcela["id"])
        unidades = {p["clave"]: p["unidad"] for p in guardado["parametros"]}
        assert unidades["ph"] == ""
        assert unidades["fosforo_asimilable"] == "ppm"
        assert unidades["conductividad"] == "dS/m"

    def test_la_unidad_la_pone_el_catalogo_y_no_el_que_llama(
        self, crear_parcela, crear_analitica
    ):
        """Si un boletín viniera en otras unidades, no puede colarse tal cual.

        Comparar el fósforo de dos años distintos exige que los dos estén en ppm. Si se
        aceptara la unidad que manda el navegador, un año estaría en ppm y otro en mg/kg y
        la comparación sería falsa sin que nadie se diera cuenta.
        """
        parcela = crear_parcela()
        guardado = crear_analitica(
            parcela_id=parcela["id"],
            parametros=[{"clave": "fosforo_asimilable", "valor": 18.0, "unidad": "mg/kg"}],
        )
        assert guardado["parametros"][0]["unidad"] == "ppm"


# --------------------------------------------------------------------------
# Que no se cuele lo que no existe
# --------------------------------------------------------------------------


class TestElCatalogoEsLaPuerta:
    def test_un_parametro_inventado_no_se_guarda(self, crear_parcela, crear_analitica):
        parcela = crear_parcela()
        guardado = crear_analitica(
            parcela_id=parcela["id"],
            parametros=[
                {"clave": "ph", "valor": 7.4},
                {"clave": "color_de_la_tierra", "valor": 3},
            ],
        )
        claves = [p["clave"] for p in guardado["parametros"]]
        assert claves == ["ph"]

    def test_un_parametro_de_otra_clase_de_analisis_no_vale(
        self, crear_parcela, crear_analitica
    ):
        """El fósforo asimilable es de tierra; en un análisis de agua no significa nada."""
        parcela = crear_parcela()
        guardado = crear_analitica(
            tipo="agua_riego",
            parcela_id=parcela["id"],
            parametros=[
                {"clave": "fosforo_asimilable", "valor": 18.0},
                {"clave": "nitratos", "valor": 42.0},
            ],
        )
        assert [p["clave"] for p in guardado["parametros"]] == ["nitratos"]

    def test_un_valor_vacio_no_se_guarda_como_cero(self, crear_parcela, crear_analitica):
        """Un boletín que no trae el dato no trae un cero: trae nada.

        Apuntar un cero sería apuntar un dato falso, y encima el plan de abono lo leería.
        """
        parcela = crear_parcela()
        guardado = crear_analitica(
            parcela_id=parcela["id"],
            parametros=[
                {"clave": "ph", "valor": 7.4},
                {"clave": "arcilla", "valor": None},
                {"clave": "arena", "valor": ""},
            ],
        )
        assert [p["clave"] for p in guardado["parametros"]] == ["ph"]

    def test_un_valor_que_no_es_un_numero_no_revienta(self, crear_parcela, crear_analitica):
        parcela = crear_parcela()
        guardado = crear_analitica(
            parcela_id=parcela["id"],
            parametros=[
                {"clave": "ph", "valor": 7.4},
                {"clave": "limo", "valor": "no lo sé"},
            ],
        )
        assert [p["clave"] for p in guardado["parametros"]] == ["ph"]

    def test_un_valor_con_coma_se_entiende(self, crear_parcela, crear_analitica):
        """El agricultor escribe «7,4» en el móvil. Rechazarlo sería no entenderle."""
        parcela = crear_parcela()
        guardado = crear_analitica(
            parcela_id=parcela["id"],
            parametros=[{"clave": "ph", "valor": "7,4"}],
        )
        assert guardado["parametros"][0]["valor"] == 7.4

    def test_el_mismo_parametro_dos_veces_solo_cuenta_una(self, crear_parcela, crear_analitica):
        """Se queda el primero: el del boletín, no una repetición de la interfaz."""
        parcela = crear_parcela()
        guardado = crear_analitica(
            parcela_id=parcela["id"],
            parametros=[
                {"clave": "ph", "valor": 7.4},
                {"clave": "ph", "valor": 9.9},
            ],
        )
        assert len(guardado["parametros"]) == 1
        assert guardado["parametros"][0]["valor"] == 7.4


# --------------------------------------------------------------------------
# Las validaciones
# --------------------------------------------------------------------------


class TestValidaciones:
    def _validar(self, cliente, cuenta, **cambios):
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        cuerpo = {
            "campana_id": campana["id"],
            "tipo": "suelo",
            "fecha_toma_muestra": "2026-02-14",
            "laboratorio": "Un laboratorio",
            "parametros": [{"clave": "ph", "valor": 7.4}],
        }
        cuerpo.update(cambios)
        respuesta = cliente.post(
            "/api/analiticas/validar", headers=cuenta["cabeceras"], json=cuerpo
        )
        assert respuesta.status_code == 200, respuesta.text
        return {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}

    def test_sin_decir_que_se_analiza_no_se_puede_guardar(self, cliente, cuenta):
        avisos = self._validar(cliente, cuenta, tipo="")
        assert avisos["N1_sin_material"]["bloquea"]

    def test_un_tipo_que_no_existe_no_se_puede_guardar(self, cliente, cuenta):
        avisos = self._validar(cliente, cuenta, tipo="las piedras")
        assert avisos["N1_sin_material"]["bloquea"]

    def test_un_analisis_de_tierra_sin_parcela_no_se_puede_guardar(
        self, cliente, cuenta, crear_parcela
    ):
        """De la parcela depende que el análisis sirva para el plan de abono de alguien."""
        avisos = self._validar(cliente, cuenta, tipo="suelo")
        assert avisos["N3_sin_sitio"]["bloquea"]

    def test_el_agua_puede_ser_de_una_balsa_y_no_de_una_parcela(self, cliente, cuenta):
        """El agua de riego no siempre sale de una parcela: sale del canal o de la balsa."""
        avisos = self._validar(
            cliente, cuenta, tipo="agua_riego", parametros=[{"clave": "nitratos", "valor": 42.0}]
        )
        assert "N3_sin_sitio" not in avisos

    def test_el_resultado_no_puede_ser_de_antes_de_la_muestra(self, cliente, cuenta, parcela):
        avisos = self._validar(
            cliente,
            cuenta,
            parcela_id=parcela["id"],
            fecha_toma_muestra="2026-02-14",
            fecha_resultado="2026-02-01",
        )
        assert avisos["N4_fechas_cruzadas"]["bloquea"]

    def test_un_analisis_sin_numeros_se_puede_guardar_pero_se_avisa(
        self, cliente, cuenta, parcela
    ):
        """El agricultor puede tener el boletín en casa y querer apuntarlo ya."""
        avisos = self._validar(cliente, cuenta, parcela_id=parcela["id"], parametros=[])
        assert "N5_sin_numeros" in avisos
        assert not avisos["N5_sin_numeros"]["bloquea"]

    def test_un_analisis_de_restos_sin_decir_que_sustancia_avisa(self, cliente, cuenta, parcela):
        avisos = self._validar(
            cliente,
            cuenta,
            tipo="residuos",
            parcela_id=parcela["id"],
            parametros=[{"clave": "residuo", "valor": 0.02}],
        )
        assert "N6_residuos_sin_sustancia" in avisos
        assert not avisos["N6_residuos_sin_sustancia"]["bloquea"]

    def test_sin_laboratorio_se_avisa(self, cliente, cuenta, parcela):
        avisos = self._validar(cliente, cuenta, parcela_id=parcela["id"], laboratorio="")
        assert "N9_sin_laboratorio" in avisos
        assert not avisos["N9_sin_laboratorio"]["bloquea"]

    def test_un_analisis_de_hace_tres_anos_avisa(self, cliente, cuenta, parcela):
        avisos = self._validar(
            cliente, cuenta, parcela_id=parcela["id"], fecha_toma_muestra="2022-03-01"
        )
        assert "N8_analisis_viejo" in avisos
        assert not avisos["N8_analisis_viejo"]["bloquea"]

    def test_un_analisis_de_este_ano_no_avisa_por_viejo(self, cliente, cuenta, parcela):
        avisos = self._validar(
            cliente, cuenta, parcela_id=parcela["id"], fecha_toma_muestra="2026-02-14"
        )
        assert "N8_analisis_viejo" not in avisos

    def test_el_agua_con_nitrato_avisa_de_que_hay_que_contarlo(
        self, cliente, cuenta, parcela
    ):
        """El mensaje dice el número y qué hacer, y no una cifra que no está cargada."""
        avisos = self._validar(
            cliente,
            cuenta,
            tipo="agua_riego",
            parcela_id=parcela["id"],
            parametros=[{"clave": "nitratos", "valor": 42.0}],
        )
        assert "N7_agua_con_nitrato" in avisos
        assert "42" in avisos["N7_agua_con_nitrato"]["mensaje"]

    def test_no_se_inventa_un_limite_de_nitratos(self):
        """El programa de actuación de CyL (Orden MAV/398/2022) no está cargado.

        Se avisa del número para que el agricultor lo cuente en los aportes, y no se dice
        «te has pasado»: afirmar un límite que no está cargado sería inventarse una norma,
        que es lo que este proyecto no hace.
        """
        mensaje = textos.MENSAJES["N7_agua_con_nitrato"].lower()
        assert "50" not in mensaje
        assert "te has pasado" not in mensaje
        assert "no se puede" not in mensaje

    def test_ninguna_validacion_deja_al_agricultor_sin_salida(self, cliente, cuenta, parcela):
        """Todo lo que bloquea dice qué hacer ahora."""
        avisos = self._validar(cliente, cuenta, tipo="", parametros=[])
        assert avisos["N1_sin_material"]["mensaje"].strip()


# --------------------------------------------------------------------------
# El fichero del laboratorio
# --------------------------------------------------------------------------


class TestElBoletin:
    def test_se_sube_el_pdf_del_laboratorio(self, cliente, cuenta, analitica):
        respuesta = cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("boletin.pdf", io.BytesIO(b"%PDF-1.4 hola"), "application/pdf")},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["fichero_nombre"] == "boletin.pdf"
        assert respuesta.json()["fichero_bytes"] == 13

    def test_el_boletin_se_puede_descargar(self, cliente, cuenta, analitica):
        cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("boletin.pdf", io.BytesIO(b"%PDF-1.4 hola"), "application/pdf")},
        )
        respuesta = cliente.get(
            f"/api/analiticas/{analitica['id']}/informe", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        assert respuesta.content == b"%PDF-1.4 hola"

    def test_una_foto_del_movil_tambien_vale(self, cliente, cuenta, analitica):
        respuesta = cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("foto.jpg", io.BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")},
        )
        assert respuesta.status_code == 200, respuesta.text

    def test_un_tipo_de_fichero_que_no_vale_se_rechaza(self, cliente, cuenta, analitica):
        """La carpeta de adjuntos no puede ser un vertedero."""
        respuesta = cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("virus.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
        )
        assert respuesta.status_code == 422
        assert "PDF" in respuesta.json()["detail"]

    def test_un_fichero_vacio_se_rechaza(self, cliente, cuenta, analitica):
        respuesta = cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("boletin.pdf", io.BytesIO(b""), "application/pdf")},
        )
        assert respuesta.status_code == 422

    def test_el_nombre_del_fichero_no_decide_donde_se_guarda(
        self, cliente, cuenta, analitica, tmp_path, monkeypatch
    ):
        """Un nombre con `..` no puede escribir fuera de la carpeta de adjuntos.

        Se comprueba de verdad, mirando el disco: el nombre que manda el navegador se usa
        para enseñarlo, y la ruta la pone el programa.
        """
        monkeypatch.setenv("CUEDIGITAL_ADJUNTOS", str(tmp_path))
        respuesta = cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={
                "fichero": (
                    "../../../../escapado.pdf",
                    io.BytesIO(b"%PDF-1.4"),
                    "application/pdf",
                )
            },
        )
        assert respuesta.status_code == 200
        guardados = list(tmp_path.rglob("*.pdf"))
        assert len(guardados) == 1
        # Todo lo que se ha escrito está DENTRO de la carpeta de adjuntos.
        assert tmp_path.resolve() in guardados[0].resolve().parents
        assert not (tmp_path.parent.parent / "escapado.pdf").exists()

    def test_sin_boletin_descargar_da_un_mensaje_util(self, cliente, cuenta, analitica):
        respuesta = cliente.get(
            f"/api/analiticas/{analitica['id']}/informe", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 404
        assert respuesta.json()["detail"] == textos.ANALITICA["sin_informe"]

    def test_subir_otro_boletin_reemplaza_al_anterior(self, cliente, cuenta, analitica, tmp_path, monkeypatch):
        """Corregir no puede ir dejando ficheros viejos ocupando sitio para siempre."""
        monkeypatch.setenv("CUEDIGITAL_ADJUNTOS", str(tmp_path))
        for contenido in (b"%PDF-1.4 primero", b"%PDF-1.4 segundo"):
            cliente.post(
                f"/api/analiticas/{analitica['id']}/informe",
                headers=cuenta["cabeceras"],
                files={"fichero": ("boletin.pdf", io.BytesIO(contenido), "application/pdf")},
            )
        assert len(list(tmp_path.rglob("*.pdf"))) == 1

    def test_el_boletin_de_otra_finca_no_se_puede_nisiquiera_leer(
        self, cliente, cuenta, analitica, crear_cuenta
    ):
        cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("boletin.pdf", io.BytesIO(b"%PDF-1.4 secreto"), "application/pdf")},
        )
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.get(
            f"/api/analiticas/{analitica['id']}/informe", headers=otro["cabeceras"]
        )
        assert respuesta.status_code == 404
        assert b"secreto" not in respuesta.content

    def test_los_tests_no_escriben_boletines_dentro_del_proyecto(
        self, cliente, cuenta, analitica
    ):
        """El test que sube un boletín no puede dejar un fichero de verdad en el proyecto.

        Se descubrió limpiando: sin fijar `CUEDIGITAL_ADJUNTOS` en `conftest.py`, cada
        ejecución de la suite dejaba boletines en `backend/datos/adjuntos` para siempre. No
        daba ningún fallo; lo que hacía era ensuciar el disco de quien ejecuta los tests, y
        de paso poder falsear el test que cuenta cuántos boletines hay guardados.
        """
        from pathlib import Path

        from app.routers.analiticas_api import carpeta_de_adjuntos

        raiz_del_proyecto = Path(__file__).resolve().parents[2]
        carpeta = carpeta_de_adjuntos().resolve()
        assert raiz_del_proyecto not in carpeta.parents, (
            f"la carpeta de adjuntos de los tests está dentro del proyecto: {carpeta}"
        )

        cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("boletin.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        escritos = list(carpeta.rglob("*.pdf"))
        assert escritos, "el boletín no se ha guardado en la carpeta temporal"
        # Y ninguno ha acabado dentro del proyecto.
        assert not list((raiz_del_proyecto / "backend" / "datos").rglob("*.pdf"))


# --------------------------------------------------------------------------
# Aislamiento entre fincas
# --------------------------------------------------------------------------


class TestCadaFincaVeLoSuyo:
    def test_un_analisis_de_otra_finca_no_se_ve(self, cliente, cuenta, analitica, crear_cuenta):
        otro = crear_cuenta("otro@ejemplo.test")
        listado = cliente.get("/api/analiticas", headers=otro["cabeceras"]).json()
        assert listado == []

    def test_un_analisis_de_otra_finca_no_se_puede_leer(
        self, cliente, cuenta, analitica, crear_cuenta
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.get(f"/api/analiticas/{analitica['id']}", headers=otro["cabeceras"])
        assert respuesta.status_code == 404

    def test_no_se_puede_atar_un_analisis_a_la_parcela_de_otro(
        self, cliente, cuenta, crear_cuenta, crear_parcela, crear_analitica
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        # La parcela de la primera finca, intentando usarla desde la segunda.
        parcela_de_la_primera = crear_parcela()
        campana_otro = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/analiticas",
            headers=otro["cabeceras"],
            json={
                "campana_id": campana_otro["id"],
                "tipo": "suelo",
                "fecha_toma_muestra": "2026-02-14",
                "parcela_id": parcela_de_la_primera["id"],
            },
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_apoyar_un_plan_en_el_analisis_de_otro(
        self, cliente, cuenta, analitica, crear_cuenta, crear_parcela
    ):
        """El plan guarda el análisis como un número suelto, así que hay que comprobarlo.

        Como `analitica_id` no es una clave foránea, la base de datos no lo impide: lo
        impide el router, y por eso este test existe.
        """
        otro = crear_cuenta("otro@ejemplo.test")
        parcela_otro = crear_parcela()
        campana_otro = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/planes",
            headers=otro["cabeceras"],
            json={
                "campana_id": campana_otro["id"],
                "parcela_id": parcela_otro["id"],
                "cultivo": "Trigo blando",
                "superficie_ha": 2.43,
                "analitica_id": analitica["id"],
            },
        )
        assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# El análisis sirve para el plan de abono
# --------------------------------------------------------------------------


class TestElPlanSeApoyaEnElAnalisis:
    def _plan(self, cliente, cuenta, parcela, **cambios):
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        cuerpo = {
            "campana_id": campana["id"],
            "parcela_id": parcela["id"],
            "cultivo": "Trigo blando",
            "superficie_ha": 2.43,
            "necesidad_n": 120.0,
        }
        cuerpo.update(cambios)
        return cliente.post("/api/planes", headers=cuenta["cabeceras"], json=cuerpo)

    def test_el_plan_guarda_en_que_analisis_se_apoya(self, cliente, cuenta, analitica, parcela):
        respuesta = self._plan(
            cliente, cuenta, parcela, analitica_id=analitica["id"], parcela_id=analitica["parcela_id"]
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["analitica_id"] == analitica["id"]

    def test_el_plan_devuelve_el_analisis_entero(self, cliente, cuenta, analitica, parcela):
        """Para poder enseñarlo sin una segunda llamada: en el campo eso importa."""
        creado = self._plan(
            cliente, cuenta, parcela, analitica_id=analitica["id"], parcela_id=analitica["parcela_id"]
        ).json()
        visto = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert visto["analisis"]["id"] == analitica["id"]
        assert visto["analisis"]["donde"] == "El Prado"
        assert visto["analisis"]["parametros_con_nombre"]

    def test_los_numeros_del_analisis_vienen_con_su_nombre_y_su_unidad(
        self, cliente, cuenta, analitica
    ):
        visto = cliente.get(
            f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
        ).json()
        con_nombre = {p["clave"]: p for p in visto["parametros_con_nombre"]}
        assert con_nombre["ph"]["etiqueta"] == "pH"
        assert con_nombre["ph"]["texto"] == "7,40"
        assert con_nombre["fosforo_asimilable"]["texto"] == "18,00 ppm"

    def test_un_plan_sin_analisis_sigue_valiendo(self, cliente, cuenta, parcela):
        """Hay agricultores que no tienen análisis y hacen el plan igual."""
        respuesta = self._plan(cliente, cuenta, parcela)
        assert respuesta.status_code == 201
        assert respuesta.json()["analitica_id"] is None

    def test_el_analisis_se_puede_quitar_del_plan(self, cliente, cuenta, analitica, parcela):
        creado = self._plan(
            cliente, cuenta, parcela, analitica_id=analitica["id"], parcela_id=analitica["parcela_id"]
        ).json()
        respuesta = cliente.put(
            f"/api/planes/{creado['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": creado["campana_id"],
                "parcela_id": creado["parcela_id"],
                "cultivo": creado["cultivo"],
                "superficie_ha": creado["superficie_ha"],
                "analitica_id": None,
            },
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["analitica_id"] is None

    def test_si_se_anula_el_analisis_el_plan_se_queda_sin_apoyo(
        self, cliente, cuenta, analitica, parcela
    ):
        """Un plan no puede decir que se apoya en un análisis que ya no vale."""
        creado = self._plan(
            cliente, cuenta, parcela, analitica_id=analitica["id"], parcela_id=analitica["parcela_id"]
        ).json()
        cliente.post(
            f"/api/analiticas/{analitica['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de boletín"},
        )
        visto = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert visto["analitica_id"] is None
        assert visto["analisis"] is None


# --------------------------------------------------------------------------
# Anular, corregir y listar
# --------------------------------------------------------------------------


class TestAnularYCorregir:
    def test_anular_no_borra_y_guarda_el_motivo(self, cliente, cuenta, analitica):
        respuesta = cliente.post(
            f"/api/analiticas/{analitica['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Ese boletín era de otra parcela"},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["anulado"] is True
        assert "otra parcela" in respuesta.json()["motivo_anulacion"]
        # Y sigue estando ahí, no desaparece.
        assert cliente.get(
            f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
        ).status_code == 200

    def test_anular_sin_motivo_no_se_acepta(self, cliente, cuenta, analitica):
        respuesta = cliente.post(
            f"/api/analiticas/{analitica['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": ""},
        )
        assert respuesta.status_code == 422

    def test_un_analisis_anulado_no_sale_en_la_lista(self, cliente, cuenta, analitica):
        cliente.post(
            f"/api/analiticas/{analitica['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba mal"},
        )
        assert cliente.get("/api/analiticas", headers=cuenta["cabeceras"]).json() == []

    def test_se_puede_corregir_un_numero_mal_copiado(self, cliente, cuenta, analitica):
        """Un análisis es un dato de fuera: si se copia mal, se deja bien."""
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        respuesta = cliente.put(
            f"/api/analiticas/{analitica['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "suelo",
                "fecha_toma_muestra": "2026-02-14",
                "parcela_id": analitica["parcela_id"],
                "laboratorio": analitica["laboratorio"],
                "parametros": [{"clave": "ph", "valor": 6.9}],
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        assert [p["clave"] for p in respuesta.json()["parametros"]] == ["ph"]
        assert respuesta.json()["parametros"][0]["valor"] == 6.9

    def test_corregir_deja_rastro(self, cliente, cuenta, analitica):
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        respuesta = cliente.put(
            f"/api/analiticas/{analitica['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "suelo",
                "fecha_toma_muestra": "2026-02-14",
                "parcela_id": analitica["parcela_id"],
                "laboratorio": "Otro",
                "parametros": [{"clave": "ph", "valor": 6.9}],
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        visto = cliente.get(f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]).json()
        assert visto["laboratorio"] == "Otro"
        assert visto["id"] == analitica["id"]

    def test_el_listado_va_del_mas_nuevo_al_mas_viejo(self, cliente, cuenta, crear_parcela, crear_analitica):
        parcela = crear_parcela()
        crear_analitica(parcela_id=parcela["id"], fecha_toma_muestra="2024-03-01")
        crear_analitica(parcela_id=parcela["id"], fecha_toma_muestra="2026-02-14")
        crear_analitica(parcela_id=parcela["id"], fecha_toma_muestra="2025-01-20")
        listado = cliente.get("/api/analiticas", headers=cuenta["cabeceras"]).json()
        assert [a["fecha_toma_muestra"] for a in listado] == [
            "2026-02-14",
            "2025-01-20",
            "2024-03-01",
        ]

    def test_un_analisis_viejo_sigue_en_la_lista_del_ano_siguiente(
        self, cliente, cuenta, crear_parcela, crear_analitica
    ):
        """El análisis de tierra de 2024 sigue valiendo en 2026: no se esconde."""
        parcela = crear_parcela()
        crear_analitica(parcela_id=parcela["id"], fecha_toma_muestra="2024-03-01")
        listado = cliente.get("/api/analiticas", headers=cuenta["cabeceras"]).json()
        assert len(listado) == 1
        assert listado[0]["anios"] == 2

    def test_se_puede_filtrar_por_parcela(self, cliente, cuenta, crear_parcela, crear_analitica):
        una = crear_parcela(alias="El Prado")
        otra = crear_parcela(alias="La Vega")
        crear_analitica(parcela_id=una["id"])
        crear_analitica(parcela_id=otra["id"])
        listado = cliente.get(
            f"/api/analiticas?parcela_id={una['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert len(listado) == 1
        assert listado[0]["donde"] == "El Prado"

    def test_se_puede_filtrar_por_clase(self, cliente, cuenta, crear_parcela, crear_analitica):
        parcela = crear_parcela()
        crear_analitica(parcela_id=parcela["id"])
        crear_analitica(
            tipo="agua_riego",
            parcela_id=parcela["id"],
            parametros=[{"clave": "nitratos", "valor": 42.0}],
        )
        listado = cliente.get("/api/analiticas?tipo=agua_riego", headers=cuenta["cabeceras"]).json()
        assert len(listado) == 1
        assert listado[0]["tipo"] == "agua_riego"

    def test_el_de_la_balsa_dice_de_donde_es(self, cliente, cuenta, instalacion, crear_analitica):
        guardado = crear_analitica(
            tipo="agua_riego",
            instalacion_id=instalacion["id"],
            parametros=[{"clave": "nitratos", "valor": 42.0}],
        )
        assert guardado["donde"] == "El almacén grande"

    def test_sin_sitio_lo_dice_en_vez_de_dejar_el_hueco(self, cliente, cuenta, crear_analitica):
        guardado = crear_analitica(
            tipo="agua_riego", lote="Lote del silo", parametros=[]
        )
        assert guardado["donde"] == "Lote del silo"

    def test_los_parametros_tambien_salen_en_texto_plano(self, cliente, cuenta, analitica):
        """Para podérselos mandar al técnico por WhatsApp, que es lo que se hace de verdad."""
        respuesta = cliente.get(
            f"/api/analiticas/{analitica['id']}/parametros", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        assert "Fósforo asimilable: 18,00 ppm" in respuesta.text
        assert "pH: 7,40" in respuesta.text


# --------------------------------------------------------------------------
# El informe
# --------------------------------------------------------------------------


class TestElInformeDeAnalisis:
    def test_el_informe_lleva_los_analisis_del_ano(self, cliente, cuenta, crear_parcela, crear_analitica):
        parcela = crear_parcela()
        crear_analitica(parcela_id=parcela["id"])
        informe = cliente.get("/api/analiticas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantos"] == 1
        fila = informe["filas"][0]
        assert fila["material"] == "La tierra"
        assert fila["donde"] == "El Prado"
        assert fila["laboratorio"] == "Laboratorio Agrario de Villamuriel"
        numeros = {n["etiqueta"]: n["texto"] for n in fila["numeros"]}
        assert numeros["Materia orgánica"] == "1,80 %"
        assert numeros["pH"] == "7,40"

    def test_el_informe_dice_que_no_hay_nada_cuando_no_hay_nada(self, cliente, cuenta):
        informe = cliente.get("/api/analiticas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantos"] == 0
        assert informe["vacio"] == textos.ANALITICA["informe_sin_nada"]

    def test_el_informe_no_se_confunde_con_un_identificador(self, cliente, cuenta):
        """`/analiticas/informe` va antes que `/analiticas/{id}` a propósito.

        Si estuviera después, FastAPI intentaría leer «informe» como un número y esta
        llamada devolvería un 422 sin explicar nada.
        """
        respuesta = cliente.get("/api/analiticas/informe", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200

    def test_un_analisis_anulado_no_sale_en_el_informe(self, cliente, cuenta, analitica):
        cliente.post(
            f"/api/analiticas/{analitica['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba mal"},
        )
        informe = cliente.get("/api/analiticas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantos"] == 0


# --------------------------------------------------------------------------
# El cuaderno en papel y en CSV
# --------------------------------------------------------------------------


class TestElCuadernoLoLleva:
    def test_el_pdf_lleva_el_informe_de_analisis(self, cliente, cuenta, analitica):
        respuesta = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"] == "application/pdf"
        # Un PDF de verdad, no un texto al que le han puesto la cabecera.
        assert respuesta.content.startswith(b"%PDF")

    def test_el_csv_lleva_el_informe_de_analisis(self, cliente, cuenta, analitica):
        respuesta = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        texto = respuesta.content.decode("utf-8-sig")
        assert textos.ANALITICA["informe_titulo"].upper() in texto
        assert "Laboratorio Agrario de Villamuriel" in texto
        assert "Fósforo asimilable: 18,00 ppm" in texto

    def test_el_csv_lleva_bom_para_que_excel_no_destroce_las_tildes(self, cliente, cuenta, analitica):
        respuesta = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"])
        assert respuesta.content.startswith(b"\xef\xbb\xbf")

    def test_el_pdf_sale_aunque_no_haya_analisis(self, cliente, cuenta):
        respuesta = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200


# --------------------------------------------------------------------------
# El vocabulario
# --------------------------------------------------------------------------


class TestElVocabularioLlegaALaPantalla:
    def test_la_interfaz_trae_las_clases_de_analisis(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        valores = [t["valor"] for t in datos["tipos_analitica"]]
        assert valores == list(catalogos.TIPOS_ANALITICA)
        assert datos["tipos_analitica"][0]["texto"] == "La tierra"

    def test_la_interfaz_trae_los_numeros_de_cada_clase(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        suelo = datos["parametros_analitica"]["suelo"]
        assert len(suelo) == 9
        assert {p["clave"] for p in suelo} >= {"ph", "fosforo_asimilable", "potasio_asimilable"}
        assert suelo[0]["pregunta"] == "Materia orgánica"

    def test_la_interfaz_dice_de_cual_hay_que_decir_la_parcela(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert set(datos["analitica_de_parcela"]) == {"suelo", "cultivo"}

    def test_la_interfaz_trae_los_textos_de_los_analisis(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert datos["analitica"]["titulo"] == "Los análisis"
        assert datos["analitica"]["anadir"] == "APUNTAR UN ANÁLISIS"

    def test_lo_que_se_pregunta_es_una_pregunta_y_no_un_rotulo(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        for campo in ("analitica.tipo", "analitica.fecha_toma_muestra", "analitica.laboratorio"):
            etiqueta = datos["etiquetas"][campo]
            assert etiqueta["pregunta"].endswith("?"), campo
            assert etiqueta["pista"], campo

    def test_todo_el_texto_nuevo_esta_en_el_fichero_de_textos(self):
        """Si un texto nuevo no entra en `textos_visibles`, el test de jerga deja de verlo."""
        visibles = textos.textos_visibles()
        assert textos.ANALITICA["titulo"] in visibles
        assert textos.MENSAJES["N1_sin_material"] in visibles
        assert textos.MENSAJES["N9_sin_laboratorio"] in visibles
        assert textos.ROTULOS["analisis"] in visibles


# --------------------------------------------------------------------------
# Los cálculos puros
# --------------------------------------------------------------------------


class TestLosCalculos:
    def test_una_medida_se_escribe_como_se_lee_en_castellano(self):
        from app import legal

        assert legal.formatea_medida(7.4, "") == "7,40"
        assert legal.formatea_medida(18.0, "ppm") == "18,00 ppm"
        assert legal.formatea_medida(0.31, "dS/m", 2) == "0,31 dS/m"

    def test_sin_dato_se_dice_sin_dato_y_no_un_cero(self):
        from app import legal

        assert legal.formatea_medida(None, "ppm") == "sin dato"

    def test_los_anos_transcurridos_se_cuentan_bien(self):
        import datetime as dt

        from app import legal

        referencia = dt.date(2026, 6, 1)
        assert legal.anios_transcurridos(dt.date(2026, 2, 14), referencia) == 0
        assert legal.anios_transcurridos(dt.date(2025, 2, 14), referencia) == 1
        assert legal.anios_transcurridos(dt.date(2024, 3, 1), referencia) == 2
        # Un día antes de cumplir el año, todavía no ha pasado un año entero.
        assert legal.anios_transcurridos(dt.date(2025, 6, 2), referencia) == 0

    def test_sin_fecha_no_hay_anos(self):
        from app import legal

        assert legal.anios_transcurridos(None) is None

    def test_se_coge_el_analisis_mas_nuevo(self):
        import datetime as dt

        from app import legal

        class Falso:
            def __init__(self, fecha):
                self.fecha_toma_muestra = fecha

        viejo = Falso(dt.date(2024, 1, 1))
        nuevo = Falso(dt.date(2026, 2, 14))
        assert legal.mas_reciente([viejo, nuevo]) is nuevo
        assert legal.mas_reciente([]) is None
