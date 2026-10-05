"""Las medidas preventivas de la explotación (gestión integrada de plagas).

Esta sección existe porque la app oficial tiene «Explotación: Medidas Preventivas» y el
contenido mínimo del CUE la sitúa **a nivel de Explotación** («GIP a nivel de explotación»,
apartado 1.1). Se declaran una vez y valen para todo el año.

Y hay algo que este test deja escrito porque era un agujero de verdad: el campo `medidas`
del tratamiento **existía en la base de datos desde el principio y la pantalla no lo
preguntaba nunca**, así que siempre estaba vacío. La gestión integrada de plagas exige
demostrar que se priorizó lo no químico antes de tratar, y eso no se podía cumplir de
ninguna manera. Ahora el registro de la finca alimenta el apunte del tratamiento.
"""

from __future__ import annotations

import pytest

from app import catalogos, textos


class TestLoQuePideLaNorma:
    def test_las_diez_medidas_estan_en_el_catalogo(self):
        assert len(catalogos.MEDIDAS_PREVENTIVAS) == 10

    def test_cada_medida_se_pregunta_como_una_pregunta(self):
        """En pantalla se lee una pregunta; lo que se guarda es el nombre oficial."""
        for medida in catalogos.MEDIDAS_PREVENTIVAS:
            assert medida.pregunta.startswith("¿"), medida.codigo
            assert medida.pregunta.endswith("?"), medida.codigo
            assert medida.etiqueta and not medida.etiqueta.startswith("¿"), medida.codigo

    def test_los_codigos_no_se_repiten(self):
        codigos = [m.codigo for m in catalogos.MEDIDAS_PREVENTIVAS]
        assert len(codigos) == len(set(codigos))

    def test_se_pueden_marcar_varias_medidas(self, declarar_medidas):
        """La app oficial dice literalmente: «Es posible marcar varias medidas»."""
        declaracion = declarar_medidas(["rotacion", "muestreo", "higiene"])
        assert declaracion["cuantas"] == 3
        assert set(declaracion["aplicadas"]) == {"rotacion", "muestreo", "higiene"}

    def test_la_pantalla_trae_siempre_las_diez_preguntas(self, cliente, cuenta):
        """Aunque no haya declarado nada: si no, no habría forma de marcar la primera."""
        datos = cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()
        assert len(datos["medidas"]) == 10
        assert datos["declarada"] is False
        assert datos["cuantas"] == 0
        assert all(medida["aplicada"] is False for medida in datos["medidas"])

    def test_las_diez_preguntas_salen_siempre_en_el_mismo_orden(self, cliente, cuenta, declarar_medidas):
        """Si cambiara el orden, el agricultor creería que le preguntan cosas distintas."""
        antes = [m["codigo"] for m in cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()["medidas"]]
        declarar_medidas(["trampeo", "linderos"])
        despues = [m["codigo"] for m in cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()["medidas"]]
        assert antes == despues == [m.codigo for m in catalogos.MEDIDAS_PREVENTIVAS]

    def test_se_guarda_el_nombre_oficial_de_cada_medida(self, cliente, cuenta, declarar_medidas):
        """Lo que se entrega a la administración lleva el nombre, no el código."""
        declarar_medidas(["rotacion", "muestreo"])
        informe = cliente.get("/api/medidas/informe", headers=cuenta["cabeceras"]).json()
        nombres = [fila["medida"] for fila in informe["filas"]]
        assert "Rotación de cultivos" in nombres
        assert "Muestreo y respeto de los umbrales de tratamiento" in nombres


class TestNadaSeInventa:
    def test_una_medida_que_no_existe_no_se_guarda(self, cliente, cuenta):
        respuesta = cliente.put(
            "/api/medidas",
            headers=cuenta["cabeceras"],
            json={"aplicadas": ["rotacion", "poner_musica_al_ganado"]},
        )
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["aplicadas"] == ["rotacion"]
        assert datos["descartadas"] == ["poner_musica_al_ganado"]

    def test_un_codigo_raro_no_hace_perder_las_demas(self, cliente, cuenta):
        """Lo que no puede pasar es que un código raro tumbe las siete que sí valen."""
        respuesta = cliente.put(
            "/api/medidas",
            headers=cuenta["cabeceras"],
            json={"aplicadas": ["rotacion", "variedades", "trampeo", "de_la_nada"]},
        )
        assert respuesta.json()["cuantas"] == 3

    def test_el_catalogo_dice_que_sus_codigos_son_internos(self):
        """El catálogo oficial se publica «según catálogo» y no trae los códigos.

        Queda escrito para que nadie presente los códigos de aquí como si fueran los de la
        Junta: lo que se imprime y se exporta es el nombre de cada medida.
        """
        aviso = textos.MEDIDAS["catalogo_aviso"].lower()
        assert "no trae los códigos" in aviso
        assert "internos" in aviso


class TestNadaSeBorra:
    def test_desmarcar_una_medida_no_la_borra(self, cliente, cuenta, declarar_medidas):
        """Se queda con `aplicada=False`: así se puede responder «¿esto lo hacías antes?»."""
        declarar_medidas(["rotacion", "muestreo"])
        declarar_medidas(["rotacion"])
        datos = cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()
        por_codigo = {m["codigo"]: m for m in datos["medidas"]}
        assert por_codigo["muestreo"]["aplicada"] is False
        assert len(datos["medidas"]) == 10, "desmarcar no puede quitar la pregunta"

    def test_lo_que_se_deja_de_hacer_no_sale_en_el_informe(self, cliente, cuenta, declarar_medidas):
        declarar_medidas(["rotacion", "muestreo"])
        declarar_medidas(["rotacion"])
        informe = cliente.get("/api/medidas/informe", headers=cuenta["cabeceras"]).json()
        nombres = [fila["medida"] for fila in informe["filas"]]
        assert nombres == ["Rotación de cultivos"]

    def test_la_declaracion_se_puede_cambiar_todas_las_veces_que_haga_falta(
        self, cliente, cuenta, declarar_medidas
    ):
        """Es una declaración, no un apunte: se corrige y ya está."""
        for marcar in (["rotacion"], ["rotacion", "higiene"], ["trampeo"]):
            declarar_medidas(marcar)
        datos = cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()
        assert datos["aplicadas"] == ["trampeo"]

    def test_queda_rastro_de_la_declaracion(self, cliente, cuenta, declarar_medidas):
        """La auditoría se comprueba por sus propios tests; aquí basta con que no reviente."""
        declarar_medidas(["rotacion"])
        declarar_medidas([])
        assert cliente.get("/api/medidas", headers=cuenta["cabeceras"]).status_code == 200


class TestLasTusPalabras:
    def test_lo_que_haces_y_no_esta_en_las_diez_se_puede_escribir(
        self, cliente, cuenta, declarar_medidas
    ):
        """Las diez preguntas no cubren todo lo que se hace en el campo."""
        declarar_medidas(
            ["trampeo"],
            observaciones={"trampeo": "Pongo trampas para la procesionaria en los pinos"},
        )
        datos = cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()
        por_codigo = {m["codigo"]: m for m in datos["medidas"]}
        assert "procesionaria" in por_codigo["trampeo"]["observaciones"]

    def test_las_tus_palabras_salen_en_el_informe(self, cliente, cuenta, declarar_medidas):
        declarar_medidas(["trampeo"], observaciones={"trampeo": "Con trampas de feromona"})
        informe = cliente.get("/api/medidas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["filas"][0]["observaciones"] == "Con trampas de feromona"

    def test_una_nota_vacia_se_guarda_como_nada(self, cliente, cuenta, declarar_medidas):
        """Un hueco en blanco no es una nota: es que no hay nota."""
        declarar_medidas(["rotacion"], observaciones={"rotacion": "   "})
        datos = cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()
        assert datos["medidas"][0]["observaciones"] is None

    def test_la_nota_de_una_medida_no_se_cuela_en_otra(self, cliente, cuenta, declarar_medidas):
        declarar_medidas(["rotacion", "trampeo"], observaciones={"rotacion": "Trigo-cebada"})
        datos = cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()
        por_codigo = {m["codigo"]: m for m in datos["medidas"]}
        assert por_codigo["rotacion"]["observaciones"] == "Trigo-cebada"
        assert por_codigo["trampeo"]["observaciones"] is None


class TestLosMensajes:
    def test_sin_declarar_nada_se_dice_que_falta(self, cliente, cuenta):
        datos = cliente.get("/api/medidas", headers=cuenta["cabeceras"]).json()
        assert datos["mensaje"] == textos.MEDIDAS["sin_declarar"]

    def test_con_una_medida_el_mensaje_va_en_singular(self, cliente, cuenta, declarar_medidas):
        """«Tienes marcadas 1 medidas» es lo primero que hace desconfiar de un programa."""
        declaracion = declarar_medidas(["rotacion"])
        assert "1 medida." in declaracion["mensaje"]
        assert "medidas" not in declaracion["mensaje"]

    def test_con_varias_el_mensaje_va_en_plural(self, cliente, cuenta, declarar_medidas):
        declaracion = declarar_medidas(["rotacion", "higiene"])
        assert "2 medidas" in declaracion["mensaje"]

    def test_no_marcar_ninguna_se_puede_pero_se_avisa(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/medidas/validar", headers=cuenta["cabeceras"], json={"aplicadas": []}
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "P1_sin_ninguna" in avisos
        # Avisa, no bloquea: hay fincas que de verdad no hacen ninguna de las diez.
        assert avisos["P1_sin_ninguna"]["bloquea"] is False
        assert respuesta.json()["puede_guardarse"] is True

    def test_marcar_alguna_no_da_ningun_aviso(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/medidas/validar",
            headers=cuenta["cabeceras"],
            json={"aplicadas": ["rotacion"]},
        )
        assert respuesta.json()["avisos"] == []

    def test_el_aviso_de_no_marcar_ninguna_dice_que_hacer(self):
        mensaje = textos.MENSAJES["P1_sin_ninguna"]
        assert "márcala" in mensaje


class TestElAvisoEnElTratamiento:
    """La gestión integrada de plagas une las dos secciones: finca y apunte."""

    def test_sin_medidas_declaradas_el_tratamiento_avisa(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(),
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "P2_tratamiento_sin_medidas" in avisos
        assert avisos["P2_tratamiento_sin_medidas"]["bloquea"] is False
        # Y no impide guardar: el agricultor puede apuntar hoy y declarar mañana.
        assert respuesta.json()["puede_guardarse"] is True

    def test_con_una_medida_declarada_ya_no_avisa(
        self, cliente, cuenta, nuevo_tratamiento, declarar_medidas
    ):
        declarar_medidas(["rotacion"])
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(),
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "P2_tratamiento_sin_medidas" not in codigos

    def test_haber_declarado_que_no_haces_ninguna_cuenta_como_declarado(
        self, cliente, cuenta, nuevo_tratamiento, declarar_medidas
    ):
        """Si el agricultor ya dijo «no hago ninguna», ya está contestado.

        Volver a pedírselo en cada apunte sería no escucharle, y el aviso perdería valor
        por repetido.
        """
        declarar_medidas([])
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(),
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "P2_tratamiento_sin_medidas" not in codigos

    def test_en_una_nave_no_se_pregunta_por_las_medidas_del_cultivo(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion, declarar_medidas
    ):
        """Tratar una nave no tiene nada que ver con la gestión integrada del cultivo."""
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(),
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "P2_tratamiento_sin_medidas" not in codigos

    def test_el_aviso_dice_donde_se_arregla(self):
        mensaje = textos.MENSAJES["P2_tratamiento_sin_medidas"]
        assert "Lo que hago sin echar producto" in mensaje

    def test_el_tratamiento_sigue_guardando_sus_propias_medidas(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        """Y son OTRAS: lo que hiciste esa vez, no lo que haces siempre."""
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(medidas=["muestreo", "higiene"]),
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["medidas"] == ["muestreo", "higiene"]

    def test_solo_se_guardan_medidas_del_catalogo_en_el_tratamiento(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(medidas=["muestreo", "inventada"]),
        )
        assert respuesta.json()["medidas"] == ["muestreo"]

    def test_son_dos_cosas_distintas_y_no_se_pisan(
        self, cliente, cuenta, nuevo_tratamiento, declarar_medidas
    ):
        """Declarar en la finca NO mete medidas en los apuntes ya hechos.

        Es importante que sea así: un apunte dice lo que se hizo ese día. Rellenarlo
        después con lo que el agricultor declara hoy sería escribir en el cuaderno algo
        que no pasó.
        """
        primero = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(medidas=[]),
        ).json()
        declarar_medidas(["rotacion", "muestreo"])
        visto = cliente.get(
            f"/api/tratamientos/{primero['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert visto["medidas"] == []


class TestElInforme:
    def test_el_informe_dice_que_no_hay_nada_cuando_no_hay_nada(self, cliente, cuenta):
        informe = cliente.get("/api/medidas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantas"] == 0
        assert informe["sin_nada"] == textos.MEDIDAS["informe_sin_nada"]
        assert informe["declarada"] is False

    def test_el_informe_no_se_confunde_con_un_identificador(self, cliente, cuenta):
        respuesta = cliente.get("/api/medidas/informe", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200

    def test_el_informe_dice_que_es_de_toda_la_finca(self, cliente, cuenta, declarar_medidas):
        """Es un bloque a nivel de Explotación del contenido mínimo del CUE."""
        declarar_medidas(["rotacion"])
        informe = cliente.get("/api/medidas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["de_la_finca"] == textos.MEDIDAS["de_la_finca"]
        assert informe["cuantas"] == 1


class TestAislamiento:
    def test_cada_finca_declara_lo_suyo(self, cliente, cuenta, declarar_medidas, crear_cuenta):
        declarar_medidas(["rotacion", "muestreo"])
        otro = crear_cuenta("otro@ejemplo.test")
        datos = cliente.get("/api/medidas", headers=otro["cabeceras"]).json()
        assert datos["declarada"] is False
        assert datos["cuantas"] == 0

    def test_lo_que_declara_uno_no_avisa_en_los_apuntes_del_otro(
        self, cliente, cuenta, declarar_medidas, crear_cuenta, nuevo_tratamiento
    ):
        declarar_medidas(["rotacion"])
        otro = crear_cuenta("otro@ejemplo.test")
        # El otro agricultor tiene su propia parcela y su propio producto.
        parcela = cliente.post(
            "/api/parcelas",
            headers=otro["cabeceras"],
            json={"alias": "La Vega", "superficie_ha": 1.0, "sistema": "secano"},
        ).json()
        producto = cliente.post(
            "/api/productos",
            headers=otro["cabeceras"],
            json={"nombre_comercial": "Otro 25 EC", "numero_registro": "24.999", "dosis_maxima": 1.0},
        ).json()
        campana = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=otro["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-01",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "P2_tratamiento_sin_medidas" in codigos


class TestElCuadernoLoLleva:
    def test_el_csv_lleva_las_medidas_preventivas(self, cliente, cuenta, declarar_medidas):
        declarar_medidas(["rotacion", "muestreo"], observaciones={"muestreo": "Antes de decidir"})
        texto = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"]).content.decode(
            "utf-8-sig"
        )
        assert textos.MEDIDAS["informe_titulo"].upper() in texto
        assert "Rotación de cultivos" in texto
        assert "Antes de decidir" in texto

    def test_el_csv_dice_que_no_hay_ninguna_si_no_la_hay(self, cliente, cuenta):
        texto = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"]).content.decode(
            "utf-8-sig"
        )
        assert textos.MEDIDAS["informe_sin_nada"] in texto

    def test_el_pdf_lleva_las_medidas_preventivas(self, cliente, cuenta, declarar_medidas):
        declarar_medidas(["rotacion"])
        respuesta = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        assert respuesta.content.startswith(b"%PDF")
        assert len(respuesta.content) > 1500

    def test_las_medidas_no_se_filtran_por_campana(self, cliente, cuenta, declarar_medidas):
        """Son un bloque a nivel de Explotación: no dependen del año."""
        declarar_medidas(["rotacion"])
        del_ano_que_viene = cliente.get(
            "/api/cuaderno/export.csv?campana_id=999", headers=cuenta["cabeceras"]
        )
        # Un año que no existe da 404, así que se comprueba con el año de verdad.
        assert del_ano_que_viene.status_code == 404
        texto = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"]).content.decode(
            "utf-8-sig"
        )
        assert "Rotación de cultivos" in texto


class TestElVocabulario:
    def test_la_interfaz_trae_las_medidas_para_la_pantalla(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert len(datos["medidas_preventivas"]) == 10
        for medida in datos["medidas_preventivas"]:
            assert medida["pregunta"].startswith("¿")
            assert medida["etiqueta"]

    def test_la_interfaz_trae_los_textos_de_la_pantalla(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert datos["medidas"]["titulo"] == "Lo que hago sin echar producto"
        assert datos["medidas"]["hacer"] == "MARCAR LO QUE HAGO"

    def test_lo_que_se_pregunta_en_el_tratamiento_esta_en_los_textos(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert datos["medidas"]["pregunta_en_el_tratamiento"].endswith("?")
        assert datos["medidas"]["pista_en_el_tratamiento"]

    def test_todo_el_texto_nuevo_esta_en_el_fichero_de_textos(self):
        """Si un texto nuevo no entra en `textos_visibles`, el test de jerga deja de verlo."""
        visibles = textos.textos_visibles()
        assert textos.MEDIDAS["titulo"] in visibles
        assert textos.MEDIDAS["catalogo_aviso"] in visibles
        assert textos.MENSAJES["P1_sin_ninguna"] in visibles
        assert textos.MENSAJES["P2_tratamiento_sin_medidas"] in visibles
        assert textos.PORQUE["por_que_medidas"] in visibles


class TestLaAyuda:
    def test_la_ayuda_trae_el_porque_de_las_medidas(self, cliente):
        ayuda = cliente.get("/api/ayuda").json()
        assert "por_que_medidas" in ayuda["porques"]
        assert "medidas" in ayuda

    def test_el_porque_explica_para_que_sirve_y_no_solo_que_hay_que_hacerlo(self):
        texto = textos.PORQUE["por_que_medidas"]
        assert "inspección" in texto
        assert "ahorras" in texto


@pytest.mark.parametrize("codigo", [m.codigo for m in catalogos.MEDIDAS_PREVENTIVAS])
def test_cada_medida_se_puede_declarar(codigo, cliente, cuenta):
    """Las diez, una por una: ninguna puede quedarse sin poder marcarse."""
    respuesta = cliente.put(
        "/api/medidas", headers=cuenta["cabeceras"], json={"aplicadas": [codigo]}
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["aplicadas"] == [codigo]
