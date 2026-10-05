"""Las parcelas que se llevan igual: apuntar una vez lo que se hace en seis.

**Por qué existe este fichero.** Es la tercera vez que aparece el mismo fallo, y por eso está
escrito aquí con nombre y apellidos: **el apartado existía en el programa y no tenía puerta**.

- `GrupoParcelas` (la «unidad homogénea de cultivo» de la app oficial) estaba en la base de datos
  con tres endpoints: listar, crear a mano y `calcular` automático.
- **Ninguna pantalla los llamaba.** `grupo_id` no aparecía ni una vez en todo el JavaScript.
- Y mientras tanto la lista de comprobación decía «`GrupoParcelas`, a mano y automático».

Y había un agujero de verdad, no solo una pantalla que faltaba: **la comprobación de que no se
trata más superficie de la que hay solo se hacía cuando el apunte era de una parcela.** En un
grupo no se comprobaba nada: se podía apuntar un tratamiento de 100 hectáreas sobre un grupo de
5 y el programa no decía ni una palabra.

Lo que se comprueba aquí:

1. Que se pueden juntar parcelas: a mano y con el botón que las junta solo.
2. Que apuntar en un grupo guarda **el grupo y no una parcela suelta**, y que la superficie que
   se pone es la de todas juntas.
3. Que **la superficie del grupo sí se comprueba** (el agujero).
4. Que un apunte no puede ser a la vez de una parcela y de un grupo.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tres_parcelas(cliente, cuenta, crear_parcela):
    """Tres parcelas de cebada, del mismo sistema y **cerca**, para poder juntarlas.

    La geometría hace falta de verdad: el cálculo automático solo junta parcelas que estén a
    menos de 8 km, que es lo que dice el documento oficial. Tres puntos a un kilómetro escaso
    unos de otros, en la misma zona.
    """
    return [
        crear_parcela(
            alias="El Prado",
            superficie_ha=2.0,
            geometria="POINT(-5.0000 40.9000)",
        ),
        crear_parcela(
            alias="La Vega",
            superficie_ha=3.0,
            geometria="POINT(-5.0050 40.9050)",
        ),
        crear_parcela(
            alias="El Alto",
            superficie_ha=5.0,
            geometria="POINT(-5.0100 40.9100)",
        ),
    ]


def _juntar(cliente, cabeceras, parcelas, nombre="La cebada", campana_id=None) -> dict:
    respuesta = cliente.post(
        "/api/grupos",
        headers=cabeceras,
        json={
            "nombre": nombre,
            "parcela_ids": [p["id"] for p in parcelas],
            "campana_id": campana_id,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _grupos(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/grupos", headers=cabeceras).json()


def _declarar(cliente, cabeceras, campana, parcela, especie):
    cliente.post(
        f"/api/parcelas/{parcela['id']}/cultivos",
        headers=cabeceras,
        json={"campana_id": campana["id"], "especie": especie, "sistema": "secano"},
    )


class TestJuntarParcelas:
    def test_una_sola_parcela_no_hace_grupo(self, cliente, cuenta, parcela):
        """Juntar una parcela consigo misma no ahorra nada y confunde la lista."""
        respuesta = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Yo conmigo", "parcela_ids": [parcela["id"]]},
        )
        assert respuesta.status_code == 422
        assert "dos parcelas" in respuesta.json()["detail"]

    def test_se_juntan_a_mano(self, cliente, cuenta, tres_parcelas):
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas[:2])
        assert grupo["nombre"] == "La cebada"
        assert len(grupo["parcela_ids"]) == 2
        assert grupo["creado_automaticamente"] is False

    def test_el_grupo_suma_las_superficies(self, cliente, cuenta, tres_parcelas):
        """Es lo que hace falta para comprobar que no se trata más tierra de la que hay."""
        _juntar(cliente, cuenta["cabeceras"], tres_parcelas)  # 2 + 3 + 5
        grupo = _grupos(cliente, cuenta["cabeceras"])[0]
        assert grupo["superficie_total_ha"] == 10.0

    def test_el_boton_de_juntarlas_solo_las_junta(self, cliente, cuenta, campana, tres_parcelas):
        """Mismo cultivo y mismo sistema, y cerca: eso es lo que mira el cálculo automático."""
        for parcela in tres_parcelas:
            _declarar(cliente, cuenta["cabeceras"], campana, parcela, "Cebada")
        respuesta = cliente.post("/api/grupos/calcular", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["grupos_creados"] >= 1
        assert _grupos(cliente, cuenta["cabeceras"])

    def test_sin_cultivo_declarado_no_junta_nada(self, cliente, cuenta, tres_parcelas):
        """Agrupar a ciegas juntaría parcelas que no se llevan igual."""
        respuesta = cliente.post("/api/grupos/calcular", headers=cuenta["cabeceras"]).json()
        assert respuesta["grupos_creados"] == 0

    def test_no_junta_cultivos_distintos(self, cliente, cuenta, campana, tres_parcelas):
        _declarar(cliente, cuenta["cabeceras"], campana, tres_parcelas[0], "Cebada")
        _declarar(cliente, cuenta["cabeceras"], campana, tres_parcelas[1], "Girasol")
        _declarar(cliente, cuenta["cabeceras"], campana, tres_parcelas[2], "Cebada")
        cliente.post("/api/grupos/calcular", headers=cuenta["cabeceras"])
        grupos = _grupos(cliente, cuenta["cabeceras"])
        for grupo in grupos:
            cultivos = {
                c
                for c in ("cebada", "girasol")
                if c in (grupo["cultivo"] or "").lower()
            }
            # El grupo que exista tiene que ser de un solo cultivo, nunca mezclados.
            assert len(cultivos) <= 1, grupo

    def test_hace_falta_entrar(self, cliente):
        assert cliente.get("/api/grupos").status_code == 401

    def test_una_finca_no_ve_los_grupos_de_otra(self, cliente, cuenta, crear_cuenta, tres_parcelas):
        _juntar(cliente, cuenta["cabeceras"], tres_parcelas[:2])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        assert _grupos(cliente, otra["cabeceras"]) == []


class TestApuntarEnUnGrupo:
    def test_el_tratamiento_guarda_el_grupo_y_no_una_parcela(
        self, cliente, cuenta, campana, tres_parcelas, producto
    ):
        """Un apunte es de una parcela o de un grupo, nunca de las dos cosas."""
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas)
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "grupo_id": grupo["id"],
                "superficie_tratada_ha": 10.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["grupo_id"] == grupo["id"]
        assert datos["parcela_id"] is None

    def test_la_labor_tambien(self, cliente, cuenta, campana, tres_parcelas):
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas)
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "laboreo",
                "fecha": "2026-04-10",
                "grupo_id": grupo["id"],
                "superficie_ha": 10.0,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["grupo_id"] == grupo["id"]

    def test_el_abono_tambien(self, cliente, cuenta, campana, tres_parcelas, fertilizante):
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas)
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "grupo_id": grupo["id"],
                "superficie_ha": 10.0,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 300.0,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["grupo_id"] == grupo["id"]

    def test_sin_parcela_y_sin_grupo_no_se_puede(
        self, cliente, cuenta, campana, producto
    ):
        """Un apunte tiene que decir dónde, aunque sea en un grupo."""
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 422


class TestElAgujeroDeLaSuperficie:
    """Lo que no se comprobaba: tratar más hectáreas de las que tiene el grupo.

    Sin esto, un grupo era un agujero por el que se colaba cualquier superficie. Y no es un
    detalle de contabilidad: la superficie tratada es lo que se declara a la Junta.
    """

    def test_pasarse_de_la_superficie_del_grupo_bloquea(
        self, cliente, cuenta, campana, tres_parcelas, producto
    ):
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas)  # 2 + 3 + 5 = 10 ha
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "grupo_id": grupo["id"],
                "superficie_tratada_ha": 40.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 422, "40 ha en un grupo de 10 no puede pasar"
        avisos = respuesta.json()["detail"]["avisos"]
        assert any(aviso["codigo"] == "V4_superficie_excedida_grupo" for aviso in avisos)

    def test_y_se_dice_la_superficie_del_grupo_no_la_de_una_parcela(
        self, cliente, cuenta, campana, tres_parcelas, producto
    ):
        """Decir «la parcela tiene 2,43 ha» cuando son cinco parcelas sería confundir."""
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas)
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "grupo_id": grupo["id"],
                "superficie_tratada_ha": 40.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        aviso = [
            a
            for a in respuesta.json()["avisos"]
            if a["codigo"] == "V4_superficie_excedida_grupo"
        ][0]
        assert "10,00" in aviso["mensaje"], f"tiene que decir 10 ha: {aviso['mensaje']}"

    def test_lo_que_cabe_en_el_grupo_pasa(self, cliente, cuenta, campana, tres_parcelas, producto):
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas)
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "grupo_id": grupo["id"],
                "superficie_tratada_ha": 10.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 201, respuesta.text

    def test_el_abono_tambien_se_comprueba(self, cliente, cuenta, campana, tres_parcelas, fertilizante):
        grupo = _juntar(cliente, cuenta["cabeceras"], tres_parcelas)
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "grupo_id": grupo["id"],
                "superficie_ha": 30.0,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 300.0,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert respuesta.status_code == 422
        avisos = respuesta.json()["detail"]["avisos"]
        assert any(aviso["codigo"] == "F2_superficie_excedida_grupo" for aviso in avisos)

    def test_una_parcela_suelta_sigue_comprobando_lo_suyo(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """El aviso de siempre no se ha roto al añadir el de los grupos."""
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 10.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        codigos = {aviso["codigo"] for aviso in respuesta.json()["avisos"]}
        assert "V4_superficie_excedida" in codigos
        assert "V4_superficie_excedida_grupo" not in codigos


class TestLaAyudaDelGrupo:
    def test_sin_grupo_la_superficie_no_se_inventa(self):
        """`None` es «no lo sé», y aquí significa que no hay grupo del que hablar."""
        from app import validaciones

        assert validaciones._superficie_del_grupo(None) is None

    def test_un_grupo_sin_parcelas_no_da_cero(self):
        """Cero diría que el grupo no tiene tierra, y eso impediría apuntar cualquier cosa."""
        from app import validaciones

        class Vacio:
            parcelas: list = []

        assert validaciones._superficie_del_grupo(Vacio()) is None


class TestLosTextosDeLaPantalla:
    def test_entran_en_la_revision_de_jerga(self):
        from app import textos

        assert textos.GRUPOS["titulo"] in textos.textos_visibles()

    def test_ninguno_lleva_jerga(self):
        from app import textos

        assert not [
            valor
            for valor in textos.GRUPOS.values()
            if textos.palabras_prohibidas_encontradas(valor)
        ]

    def test_se_dice_para_que_sirve(self):
        from app import textos

        assert "un tratamiento para las seis" in textos.GRUPOS["explica"]
        assert "cada parcela" in textos.GRUPOS["para_que"]

    def test_no_se_llama_uhc(self):
        """El nombre oficial es «unidad homogénea de cultivo», y eso no lo dice nadie en el campo."""
        from app import textos

        assert "homogénea" not in " ".join(textos.GRUPOS.values()).lower()
        assert "UHC" not in " ".join(textos.GRUPOS.values())
