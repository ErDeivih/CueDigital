"""El cultivo de cada parcela: qué hay sembrado este año y qué hubo los años anteriores.

**Por qué existe este fichero.** Es el fallo más raro de los que han salido en estas rondas,
porque no era un dato que faltara: **estaba todo y no se podía usar**.

- La tabla `ParcelaCultivo` existía desde las primeras rondas, con su endpoint de alta.
- **Ninguna pantalla la usaba.**
- Y el cuaderno **ya le decía al agricultor** «a El Prado le falta decir qué cultivo tiene este
  año. Sin eso el cuaderno queda a medias»… y no había ninguna forma de contestarle. Eso es
  justo lo que prohíbe la regla del proyecto: *si le dices al agricultor que le falta algo, le
  das el botón que lo arregla*.

Las tres consecuencias, y las tres se comprueban aquí:

1. El agricultor no podía declarar el cultivo (y la app oficial lo tiene como la pestaña
   «Características DGC» y la de «Historial Cultivos»).
2. El campo «Cultivo» de **todos** los tratamientos y labores salía vacío: el asistente no lo
   preguntaba y nadie lo rellenaba. El volcado oficial lo mandaba en blanco.
3. El aviso **V5** («en esa fecha no había cultivo en esta parcela») **no podía saltar nunca**,
   porque dependía de un dato que no había manera de meter. Un aviso que no puede saltar es un
   aviso que no existe.
"""

from __future__ import annotations

import pytest

from app import servicios


def _declarar(cliente, cabeceras, parcela_id, **cambios) -> dict:
    campana = cliente.get("/api/campanas/actual", headers=cabeceras).json()
    cuerpo = {"campana_id": campana["id"], "especie": "Trigo blando", "sistema": "secano"}
    cuerpo.update(cambios)
    respuesta = cliente.post(
        f"/api/parcelas/{parcela_id}/cultivos", headers=cabeceras, json=cuerpo
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _finca(cliente, cabeceras, **params) -> dict:
    respuesta = cliente.get("/api/cultivos", headers=cabeceras, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _de_la_parcela(datos, parcela_id):
    return [parcela for parcela in datos["parcelas"] if parcela["parcela_id"] == parcela_id][0]


class TestLoQueFaltabaEsPoderDecirlo:
    def test_la_pantalla_tiene_lo_que_necesita(self, cliente, cuenta, parcela):
        """Todas las parcelas salen, con su nombre y su superficie."""
        datos = _finca(cliente, cuenta["cabeceras"])
        fila = _de_la_parcela(datos, parcela["id"])
        assert fila["alias"] == "El Prado"
        assert fila["superficie_ha"] == 2.43

    def test_una_parcela_sin_cultivo_dice_que_le_falta(self, cliente, cuenta, parcela):
        """Y sale en la lista, en vez de esconderse: es la que hay que arreglar."""
        datos = _finca(cliente, cuenta["cabeceras"])
        fila = _de_la_parcela(datos, parcela["id"])
        assert fila["actual"] is None
        assert fila["falta_decirlo"] is True
        assert datos["faltan"] == 1

    def test_se_declara_el_cultivo(self, cliente, cuenta, parcela):
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Cebada", variedad="Meseta")
        fila = _de_la_parcela(_finca(cliente, cuenta["cabeceras"]), parcela["id"])
        assert fila["actual"]["especie"] == "Cebada"
        assert fila["actual"]["variedad"] == "Meseta"
        assert fila["falta_decirlo"] is False

    def test_y_el_aviso_del_cuaderno_desaparece(self, cliente, cuenta, parcela):
        """De nada sirve decir «falta esto» si sigue diciéndolo después de hacerlo."""
        antes = cliente.get("/api/cuaderno/falta", headers=cuenta["cabeceras"]).json()
        assert any(p["tipo"] == "parcela_sin_cultivo" for p in antes["pendientes"])

        _declarar(cliente, cuenta["cabeceras"], parcela["id"])

        despues = cliente.get("/api/cuaderno/falta", headers=cuenta["cabeceras"]).json()
        assert not any(p["tipo"] == "parcela_sin_cultivo" for p in despues["pendientes"])

    def test_corregirlo_no_deja_dos_cultivos(self, cliente, cuenta, parcela):
        """Si se equivoca al escribirlo, tiene que poder arreglarlo sin que le queden dos."""
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Cebada")
        segunda = _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Trigo")
        assert segunda["corregido"] is True

        cultivos = cliente.get(
            f"/api/parcelas/{parcela['id']}/cultivos", headers=cuenta["cabeceras"]
        ).json()
        assert len(cultivos) == 1
        assert cultivos[0]["especie"] == "Trigo"

    def test_las_fechas_del_cultivo_se_guardan(self, cliente, cuenta, parcela):
        _declarar(
            cliente,
            cuenta["cabeceras"],
            parcela["id"],
            fecha_inicio="2025-11-01",
            fecha_fin="2026-07-15",
        )
        fila = _de_la_parcela(_finca(cliente, cuenta["cabeceras"]), parcela["id"])
        assert fila["actual"]["fecha_inicio"] == "2025-11-01"
        assert fila["actual"]["fecha_fin"] == "2026-07-15"

    def test_hace_falta_entrar(self, cliente):
        assert cliente.get("/api/cultivos").status_code == 401

    def test_una_finca_no_ve_los_cultivos_de_otra(self, cliente, cuenta, crear_cuenta, parcela):
        _declarar(cliente, cuenta["cabeceras"], parcela["id"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        assert _finca(cliente, otra["cabeceras"])["cuantos"] == 0

    def test_no_se_puede_declarar_en_una_parcela_de_otra_finca(
        self, cliente, cuenta, crear_cuenta, parcela
    ):
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        campana = cliente.get("/api/campanas/actual", headers=otra["cabeceras"]).json()
        respuesta = cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=otra["cabeceras"],
            json={"campana_id": campana["id"], "especie": "Trigo"},
        )
        assert respuesta.status_code == 404


class TestElHistorialDeCultivos:
    """«Historial Cultivos» de la app oficial: qué se sembró los años anteriores."""

    def test_el_de_la_campana_anterior_sigue_ahi(self, cliente, cuenta, parcela):
        anterior = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={"anio": 2025, "fecha_inicio": "2025-01-01", "fecha_fin": "2025-12-31"},
        ).json()
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": anterior["id"], "especie": "Girasol"},
        )
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Cebada")

        fila = _de_la_parcela(_finca(cliente, cuenta["cabeceras"]), parcela["id"])
        assert fila["actual"]["especie"] == "Cebada"
        assert [c["especie"] for c in fila["anteriores"]] == ["Girasol"]
        assert fila["anteriores"][0]["anio"] == 2025

    def test_dice_si_repite_el_mismo_cultivo_que_el_ano_pasado(self, cliente, cuenta, parcela):
        """La rotación es una de las medidas preventivas del cuaderno: verlo ayuda a decidir."""
        anterior = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={"anio": 2025, "fecha_inicio": "2025-01-01", "fecha_fin": "2025-12-31"},
        ).json()
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": anterior["id"], "especie": "Trigo blando"},
        )
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Trigo blando")
        fila = _de_la_parcela(_finca(cliente, cuenta["cabeceras"]), parcela["id"])
        assert fila["repite_el_del_ano_pasado"] is True

    def test_no_lo_dice_si_cambia_de_cultivo(self, cliente, cuenta, parcela):
        anterior = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={"anio": 2025, "fecha_inicio": "2025-01-01", "fecha_fin": "2025-12-31"},
        ).json()
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": anterior["id"], "especie": "Girasol"},
        )
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Cebada")
        fila = _de_la_parcela(_finca(cliente, cuenta["cabeceras"]), parcela["id"])
        assert fila["repite_el_del_ano_pasado"] is False


class TestElCultivoSeRellenaSoloEnLosApuntes:
    """Lo que la app oficial llama un «campo calculado»: no se pregunta en cada apunte."""

    def test_el_tratamiento_coge_el_cultivo_de_la_parcela(self, cliente, cuenta, campana, parcela, producto):
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Cebada de dos carreras")
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 2.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["cultivo"] == "Cebada de dos carreras"

    def test_la_labor_tambien(self, cliente, cuenta, campana, parcela):
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Alfalfa")
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "poda",
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 1.0,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["cultivo"] == "Alfalfa"

    def test_si_el_apunte_trae_su_propio_cultivo_manda_el_suyo(self, cliente, cuenta, campana, parcela, producto):
        """El de la parcela es el valor por defecto, no una imposición.

        Un agricultor puede tratar una parcela cuyo cultivo declarado es uno y sin embargo estar
        tratando otra cosa (una cubierta, un lindero). Lo que él diga va por delante.
        """
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Cebada")
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
                "cultivo": "La cubierta del lindero",
            },
        )
        assert respuesta.json()["cultivo"] == "La cubierta del lindero"

    def test_sin_cultivo_declarado_se_queda_vacio_y_no_se_inventa(self, cliente, cuenta, campana, parcela, producto):
        """Vacío es «no lo sé», y es mejor que poner el cultivo de otra parcela."""
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.json()["cultivo"] is None

    def test_el_cultivo_llega_al_volcado_oficial(self, cliente, cuenta, campana, parcela, producto):
        """El bloque de tratamientos del contenido mínimo tiene un campo «Cultivo».

        Sin esto iba en blanco: el asistente no lo preguntaba y nadie lo rellenaba.

        Y ojo con lo que sale: **no sale el texto «Cebada», sale su código oficial del catálogo
        de productos del FEGA** (5). Eso lo hace el volcado desde la ronda 10, y está bien: el
        contenido mínimo pide el cultivo «según catálogo». Lo que faltaba era el dato de partida.
        """
        _declarar(cliente, cuenta["cabeceras"], parcela["id"], especie="Cebada")
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        paquete = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        tratamientos = paquete["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"]
        assert tratamientos[0]["c6"] == 5, "tiene que ir el código oficial de la cebada"
        assert tratamientos[0]["c6_catalogo"] is True, "y marcado como que viene de catálogo"

    def test_sin_cultivo_declarado_el_volcado_va_vacio_y_marcado(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """Y lo que no se sabe se deja vacío, nunca con el código de otro cultivo."""
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        paquete = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        tratamientos = paquete["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"]
        assert tratamientos[0]["c6"] is None
        assert tratamientos[0]["c6_catalogo"] is True


class TestElAvisoQueNoPodiaSaltar:
    """El aviso V5 existía, estaba probado, y **no podía saltar nunca**.

    Depende de saber el periodo del cultivo de esa parcela esa campaña, y ese dato no había
    manera de meterlo desde el programa. Un aviso que no puede saltar es un aviso que no existe:
    daba la sensación de estar vigilado sin vigilar nada.
    """

    def test_el_aviso_salta_cuando_la_fecha_esta_fuera_del_cultivo(
        self, cliente, cuenta, campana, parcela, producto
    ):
        _declarar(
            cliente,
            cuenta["cabeceras"],
            parcela["id"],
            especie="Trigo blando",
            fecha_inicio="2026-03-01",
            fecha_fin="2026-06-30",
        )
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-01-15",  # antes de que hubiera cultivo
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        codigos = {aviso["codigo"] for aviso in respuesta.json()["avisos"]}
        assert "V5_fecha_fuera_de_cultivo" in codigos

    def test_y_no_salta_si_la_fecha_esta_dentro(self, cliente, cuenta, campana, parcela, producto):
        _declarar(
            cliente,
            cuenta["cabeceras"],
            parcela["id"],
            especie="Trigo blando",
            fecha_inicio="2026-03-01",
            fecha_fin="2026-06-30",
        )
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        codigos = {aviso["codigo"] for aviso in respuesta.json()["avisos"]}
        assert "V5_fecha_fuera_de_cultivo" not in codigos

    def test_el_aviso_no_bloquea(self, cliente, cuenta, campana, parcela, producto):
        """Avisa y no bloquea: el agricultor sabe mejor que el programa qué había en su tierra."""
        _declarar(
            cliente,
            cuenta["cabeceras"],
            parcela["id"],
            fecha_inicio="2026-06-01",
            fecha_fin="2026-06-30",
        )
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-01-15",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 201, respuesta.text


class TestLaAyudaDeLaFuncion:
    def test_sin_parcelas_declaradas_la_funcion_no_revienta(self, db_sesion):
        assert servicios.cultivo_declarado(
            db_sesion, explotacion_id=99, parcela_id=None, campana_id=None
        ) is None


class TestLosTextosDeLaPantalla:
    def test_entran_en_la_revision_de_jerga(self):
        from app import textos

        assert textos.CULTIVOS["titulo"] in textos.textos_visibles()

    def test_ninguno_lleva_jerga(self):
        from app import textos

        assert not [
            valor
            for valor in textos.CULTIVOS.values()
            if textos.palabras_prohibidas_encontradas(valor)
        ]

    def test_se_dice_para_que_sirve(self):
        from app import textos

        assert "rotación" in textos.CULTIVOS["para_que"]
        assert "ya no tienes que escribir el cultivo" in textos.CULTIVOS["explica"]

    def test_el_aviso_de_repetir_manda_a_las_medidas_preventivas(self):
        """Porque repetir cultivo no está prohibido: lo que se pide es apuntar lo que haces."""
        from app import textos

        assert "medidas preventivas" in textos.CULTIVOS["repite"]
