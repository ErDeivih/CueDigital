"""Cómo se echó el producto: la hora, cómo estaba la planta y cómo estaba el día.

**Por qué existe este fichero.** Se encontró mirando, en vez de a ojo, **qué campos de cada tabla
no llegaban a ninguna pantalla**: se comparó cada columna con los esquemas de salida y con el
JavaScript. Salieron once del registro de tratamientos, y todos con el mismo problema: se
guardaban y ahí se quedaban.

De esos once, dos los pide el contenido mínimo del CUE **por su número**:

* campo **3**, «Hora de tratamiento» — el volcado lo declaraba como campo suyo y no había forma
  de rellenarlo, así que iba siempre vacío;
* campo **8**, «Estado Fenológico (según catálogo)» — ni siquiera estaba declarado en el volcado.

Y uno más tenía un efecto que se veía en pantalla sin saber de dónde venía: el aviso **V11**
«¿has dejado la orilla sin tratar?» **saltaba siempre** en las parcelas con agua cerca, porque
la pregunta no existía en ninguna pantalla. Su etiqueta estaba escrita desde el principio y nunca
se había puesto en ningún sitio.
"""

from __future__ import annotations

import pytest


def _tratamiento(cliente, cabeceras, campana, parcela, producto, **cambios) -> dict:
    cuerpo = {
        "campana_id": campana["id"],
        "fecha": "2026-05-05",
        "parcela_id": parcela["id"],
        "superficie_tratada_ha": 1.0,
        "justificacion": "Vi la plaga o la hierba en el campo",
        "producto_id": producto["id"],
        "dosis": 0.5,
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/tratamientos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


class TestLosCamposQueNoLlegabanANingunaPantalla:
    """Los once campos salen ahora en la respuesta, y se pueden escribir."""

    @pytest.mark.parametrize(
        "campo, valor",
        [
            ("hora_inicio", "07:30"),
            ("hora_fin", "10:15"),
            ("estado_cultivo", "Espigando"),
            ("volumen_caldo_l_ha", 250.0),
            ("franja_seguridad_respetada", True),
            ("aplicado_a_mano", True),
            ("eficacia", "bien"),
            ("temperatura_c", 18.5),
            ("humedad_pct", 65.0),
            ("viento_kmh", 12.0),
            ("viento_direccion", "Norte"),
            ("operadores_expuestos", 2),
            ("incidencias", "Se atascó una boquilla y se paró a limpiarla"),
        ],
    )
    def test_el_campo_se_guarda_y_se_devuelve(
        self, cliente, cuenta, campana, parcela, producto, campo, valor
    ):
        """Guardar un dato y no devolverlo es como no tenerlo: no llega a ninguna pantalla."""
        datos = _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto, **{campo: valor}
        )
        assert datos[campo] == valor

    def test_lo_que_no_se_apunta_se_queda_vacio_y_no_se_inventa(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """No apuntar el viento no es decir que no hacía viento."""
        datos = _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto)
        assert datos["hora_inicio"] is None
        assert datos["viento_kmh"] is None
        assert datos["estado_cultivo"] is None
        assert datos["franja_seguridad_respetada"] is None
        # Y las dos que se añadieron por el mapeo oficial: vacío es «no lo sé», no «no».
        assert datos["aplicado_a_mano"] is None
        assert datos["eficacia"] is None


class TestElAvisoQueSaltabaSiempre:
    """El aviso de la orilla sin tratar no se podía quitar porque no se podía contestar."""

    def test_con_agua_al_lado_y_sin_contestar_avisa(
        self, cliente, cuenta, campana, crear_parcela, producto
    ):
        parcela = crear_parcela(alias="La del río", masa_agua_cerca=True)
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
        assert "V11_franja_seguridad" in codigos

    def test_al_contestar_que_si_el_aviso_desaparece(
        self, cliente, cuenta, campana, crear_parcela, producto
    ):
        """**Esto es lo que faltaba**: poder quitar el aviso contestando la pregunta."""
        parcela = crear_parcela(alias="La del río", masa_agua_cerca=True)
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
                "franja_seguridad_respetada": True,
            },
        )
        codigos = {aviso["codigo"] for aviso in respuesta.json()["avisos"]}
        assert "V11_franja_seguridad" not in codigos

    def test_y_si_dice_que_no_la_dejo_tambien_desaparece(
        self, cliente, cuenta, campana, crear_parcela, producto
    ):
        """El cuaderno recoge lo que pasó. Si no la dejó, queda escrito, pero ya no es un aviso
        de «no me has contestado»: es un dato."""
        parcela = crear_parcela(alias="La del río", masa_agua_cerca=True)
        datos = _tratamiento(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela,
            producto,
            franja_seguridad_respetada=False,
        )
        assert datos["franja_seguridad_respetada"] is False


class TestElVolcadoOficial:
    def test_la_hora_llega_al_volcado(self, cliente, cuenta, campana, parcela, producto):
        """El campo 3 del contenido mínimo, «Hora de tratamiento».

        Estaba declarado en el volcado desde el principio y **no había forma de rellenarlo**,
        así que iba siempre vacío. Un campo declarado que nunca se puede llenar es una promesa
        que no se cumple.
        """
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto, hora_inicio="07:30")
        paquete = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        filas = paquete["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"]
        assert filas[0]["c3"] == "07:30"

    def test_el_estado_de_la_planta_ahora_esta_declarado(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """El campo 8, «Estado Fenológico». **No estaba ni declarado en el volcado.**

        El dato existía en la tabla y el bloque de tratamientos no lo nombraba, así que quien
        leyera el paquete no podía saber que faltaba. Ahora se declara, y va como los demás
        campos de catálogo: vacío y marcado, porque el catálogo oficial de estados fenológicos
        no lo tenemos.
        """
        _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto, estado_cultivo="Espigando"
        )
        datos = cliente.get("/api/iuws/contenido", headers=cuenta["cabeceras"]).json()
        campos = {campo["numero"]: campo for campo in datos["campos_por_bloque"]["tratamientos"]}
        assert 8 in campos, "el campo 8 tiene que estar declarado"
        assert "fenológico" in campos[8]["nombre"].lower()
        assert campos[8]["de"] == "estado_cultivo"

    def test_y_va_vacio_y_marcado_porque_es_de_catalogo(
        self, cliente, cuenta, campana, parcela, producto
    ):
        _tratamiento(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela,
            producto,
            estado_cultivo="Espigando",
        )
        paquete = cliente.get("/api/iuws/paquete", headers=cuenta["cabeceras"]).json()
        fila = paquete["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"][0]
        # El nombre lo escribe el agricultor en su cuaderno, pero al volcado va el CÓDIGO del
        # catálogo oficial, que no tenemos: se deja vacío y marcado, nunca el texto.
        assert fila["c8"] is None
        assert fila["c8_catalogo"] is True


class TestLosTextosDeLaPantalla:
    def test_entran_en_la_revision_de_jerga(self):
        from app import textos

        for clave in ("como_fue", "hora_inicio", "estado_cultivo", "viento_kmh"):
            assert f"tratamiento.{clave}" in textos.ETIQUETAS
            assert textos.ETIQUETAS[f"tratamiento.{clave}"]["pregunta"]

    def test_no_llevan_jerga(self):
        from app import textos

        sospechosos = [
            "tratamiento.como_fue",
            "tratamiento.hora_inicio",
            "tratamiento.hora_fin",
            "tratamiento.estado_cultivo",
            "tratamiento.como_estaba_el_dia",
            "tratamiento.temperatura_c",
            "tratamiento.humedad_pct",
            "tratamiento.viento_kmh",
            "tratamiento.viento_direccion",
            "tratamiento.volumen_caldo_l_ha",
            "tratamiento.franja_seguridad_respetada",
            "tratamiento.operadores_expuestos",
            "tratamiento.incidencias",
        ]
        for clave in sospechosos:
            for valor in textos.ETIQUETAS[clave].values():
                assert not textos.palabras_prohibidas_encontradas(valor), (clave, valor)

    def test_no_se_dice_fenologico_ni_operadores(self):
        """«Estado fenológico» y «operadores expuestos» son las palabras del manual, no del campo."""
        from app import textos

        junto = " ".join(
            valor
            for clave in ("estado_cultivo", "operadores_expuestos", "como_fue", "como_estaba_el_dia")
            for valor in textos.ETIQUETAS[f"tratamiento.{clave}"].values()
        ).lower()
        assert "fenol" not in junto
        assert "operador" not in junto

    def test_la_pantalla_dice_que_es_opcional(self):
        """Un formulario largo que no se puede saltar es un formulario que se abandona."""
        from app import textos

        assert "opcional" in textos.ETIQUETAS["tratamiento.como_fue"]["pista"].lower()

    def test_el_viento_se_explica_por_que_se_pregunta(self):
        from app import textos

        pista = textos.ETIQUETAS["tratamiento.como_estaba_el_dia"]["pista"].lower()
        assert "viento" in pista
