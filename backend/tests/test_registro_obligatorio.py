"""Tests de aceptación del registro obligatorio.

Cubre los casos del documento `MVP_CUADERNO_DE_CAMPO_v2.md`. Los que bloquean son los
que más importan: son los que impiden que el agricultor apunte algo que la ley no
permite, y que en una inspección le costaría una sanción.
"""

from __future__ import annotations

import datetime as dt

import pytest

from tests.conftest import FECHA_FIN_ESPERA, FECHA_TRATAMIENTO

from app.legal import hoy


def codigos(respuesta) -> list[str]:
    """Los códigos de los avisos que han impedido guardar."""
    return [aviso["codigo"] for aviso in respuesta.json()["detail"]["avisos"]]


def url_tratamientos() -> str:
    return "/api/tratamientos"


# --------------------------------------------------------------------------
# Alta y acceso
# --------------------------------------------------------------------------


class TestAltaYAcceso:
    def test_el_alta_crea_la_cuenta_la_campana_y_el_token(self, cliente, cuenta, campana):
        assert cuenta["token"]
        assert campana["anio"] >= 2026

    def test_no_se_puede_repetir_el_correo(self, cliente, cuenta):
        from tests.conftest import DATOS_CUENTA

        repetido = cliente.post("/api/cuenta/registro", json=DATOS_CUENTA)
        assert repetido.status_code == 409

    def test_entrar_con_la_clave_buena(self, cliente, cuenta):
        from tests.conftest import DATOS_CUENTA

        respuesta = cliente.post(
            "/api/cuenta/entrar",
            json={"correo": DATOS_CUENTA["correo"], "clave": DATOS_CUENTA["clave"]},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["token"]

    def test_entrar_con_la_clave_mala_no_dice_si_el_correo_existe(self, cliente, cuenta):
        from tests.conftest import DATOS_CUENTA

        respuesta = cliente.post(
            "/api/cuenta/entrar",
            json={"correo": DATOS_CUENTA["correo"], "clave": "clave-equivocada"},
        )
        assert respuesta.status_code == 401
        assert "correo o la clave" in respuesta.json()["detail"]

    def test_sin_entrar_no_se_ve_el_cuaderno(self, cliente):
        assert cliente.get("/api/parcelas").status_code == 401

    def test_una_clave_corta_se_rechaza(self, cliente):
        from tests.conftest import DATOS_CUENTA

        respuesta = cliente.post(
            "/api/cuenta/registro", json={**DATOS_CUENTA, "correo": "corto@x.test", "clave": "123"}
        )
        assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# Tratamientos: el registro obligatorio desde 2027
# --------------------------------------------------------------------------


class TestTratamiento:
    def test_un_apunte_completo_se_guarda(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["producto_nombre"] == "Ejemplo 25 EC"
        assert datos["numero_registro"] == "24.123"
        assert datos["materia_activa"] == "Tebuconazol"
        assert not datos["anulado"]

    def test_el_apunte_devuelve_el_producto_la_persona_y_la_maquina(
        self, cliente, cuenta, nuevo_tratamiento, aplicador, equipo
    ):
        """Los identificadores del producto, del aplicador y de la máquina vuelven en la respuesta.

        **Faltaban, y hacía falta que estuvieran.** El atajo «lo mismo que la última vez» guardaba
        en el móvil lo que se había apuntado, así que en un aparato nuevo no se podía ofrecer: el
        asistente necesita esos tres identificadores para volver a rellenar el apunte. Sin ellos
        en la respuesta, el atún no se puede sacar del servidor (ver `ultimoDeLaFinca` en
        `web/nucleo.js`), y la pantalla de inicio acababa diciendo que no había nada apuntado.
        """
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(aplicador_id=aplicador["id"], equipo_id=equipo["id"]),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["producto_id"] is not None, "sin el producto no se puede repetir el apunte"
        assert datos["aplicador_id"] == aplicador["id"]
        assert datos["equipo_id"] == equipo["id"]

        # Y también en la lista, que es de donde los saca la aplicación al arrancar.
        de_la_lista = cliente.get(
            f"/api/tratamientos?campana_id={datos['campana_id']}", headers=cuenta["cabeceras"]
        ).json()[0]
        assert de_la_lista["producto_id"] == datos["producto_id"]
        assert de_la_lista["aplicador_id"] == aplicador["id"]
        assert de_la_lista["equipo_id"] == equipo["id"]

    def test_calcula_la_fecha_en_que_se_puede_cosechar(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        datos = respuesta.json()
        assert datos["plazo_seguridad_dias"] == 21
        assert datos["fecha_fin_plazo_seguridad"] == FECHA_FIN_ESPERA

    def test_calcula_la_cantidad_total_de_producto(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(dosis=0.8, superficie_tratada_ha=2.43),
        )
        assert respuesta.json()["cantidad_total"] == pytest.approx(1.944)

    def test_sin_decir_por_que_no_se_guarda(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(justificacion=None),
        )
        assert respuesta.status_code == 422
        assert "V10_sin_justificacion" in codigos(respuesta)

    def test_pasarse_de_la_dosis_de_la_etiqueta_no_se_guarda(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento(dosis=1.5)
        )
        assert respuesta.status_code == 422
        assert "V3_dosis_excedida" in codigos(respuesta)

    def test_el_aviso_de_la_dosis_dice_cual_es_el_maximo(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento(dosis=1.5)
        )
        mensaje = respuesta.json()["detail"]["avisos"][0]["mensaje"]
        assert "0,80" in mensaje
        assert "L/ha" in mensaje

    def test_tratar_mas_hectareas_que_la_parcela_no_se_guarda(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(superficie_tratada_ha=5.0),
        )
        assert respuesta.status_code == 422
        assert "V4_superficie_excedida" in codigos(respuesta)

    def test_un_producto_no_autorizado_no_se_guarda(self, cliente, cuenta, crear_producto, nuevo_tratamiento):
        retirado = crear_producto(nombre_comercial="Retirado 10", autorizado=False)
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(producto_id=retirado["id"]),
        )
        assert respuesta.status_code == 422
        assert "V1_no_autorizado" in codigos(respuesta)

    def test_un_producto_sin_numero_de_etiqueta_no_se_guarda(
        self, cliente, cuenta, crear_producto, nuevo_tratamiento
    ):
        sin_numero = crear_producto(numero_registro=None)
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(producto_id=sin_numero["id"]),
        )
        assert respuesta.status_code == 422
        assert "V1_sin_registro" in codigos(respuesta)

    def test_un_carne_caducado_no_se_guarda(self, cliente, cuenta, crear_aplicador, nuevo_tratamiento):
        caducado = crear_aplicador(nombre="Juan", fecha_caducidad_carne="2026-03-03")
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(aplicador_id=caducado["id"]),
        )
        assert respuesta.status_code == 422
        assert "V6_carne_caducado" in codigos(respuesta)
        assert "03/03/2026" in respuesta.json()["detail"]["avisos"][0]["mensaje"]

    def test_quien_aplica_sin_carne_apuntado_no_se_guarda(
        self, cliente, cuenta, crear_aplicador, nuevo_tratamiento
    ):
        sin_carne = crear_aplicador(nombre="Juan", numero_carne=None)
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(aplicador_id=sin_carne["id"]),
        )
        assert respuesta.status_code == 422
        assert "V6_sin_carne" in codigos(respuesta)

    def test_una_maquina_con_la_itu_caducada_no_se_guarda(
        self, cliente, cuenta, crear_equipo, nuevo_tratamiento
    ):
        equipo = crear_equipo(fecha_proxima_iteaf="2026-01-01")
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(equipo_id=equipo["id"]),
        )
        assert respuesta.status_code == 422
        assert "V7_iteaf_caducada" in codigos(respuesta)

    def test_una_maquina_sin_fecha_de_itu_no_se_guarda(
        self, cliente, cuenta, crear_equipo, nuevo_tratamiento
    ):
        equipo = crear_equipo(fecha_proxima_iteaf=None)
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(equipo_id=equipo["id"]),
        )
        assert respuesta.status_code == 422
        assert "V7_sin_iteaf" in codigos(respuesta)

    def test_avisa_de_en_que_dia_se_podra_cosechar(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            "/api/tratamientos/validar", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        assert respuesta.status_code == 200
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "V8_dias_de_espera" in avisos
        assert "22/05/2026" in avisos["V8_dias_de_espera"]["mensaje"]
        assert not avisos["V8_dias_de_espera"]["bloquea"]

    def test_validar_no_guarda_nada(self, cliente, cuenta, nuevo_tratamiento):
        cliente.post(
            "/api/tratamientos/validar", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        listado = cliente.get(url_tratamientos(), headers=cuenta["cabeceras"])
        assert listado.json() == []

    def test_solo_se_guardan_las_medidas_del_catalogo(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(medidas=["rotacion", "una_medida_inventada"]),
        )
        assert respuesta.json()["medidas"] == ["rotacion"]

    def test_sin_parcela_no_se_guarda(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(parcela_id=None),
        )
        assert respuesta.status_code == 422
        assert "V18_sin_parcela" in codigos(respuesta)

    def test_avisa_si_la_parcela_tiene_agua_al_lado(self, cliente, cuenta, crear_parcela, nuevo_tratamiento):
        con_rio = crear_parcela(alias="El Soto", masa_agua_cerca=True)
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(parcela_id=con_rio["id"], franja_seguridad_respetada=None),
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "V11_franja_seguridad" in avisos
        assert "río o un arroyo" in avisos["V11_franja_seguridad"]["mensaje"]
        assert not avisos["V11_franja_seguridad"]["bloquea"]

    def test_en_ecologico_un_producto_no_permitido_no_se_guarda(
        self, cliente, cuenta, crear_producto, nuevo_tratamiento
    ):
        cliente.put(
            "/api/mi-finca", headers=cuenta["cabeceras"], json={"produccion_ecologica": True}
        )
        quimico = crear_producto(nombre_comercial="Químico fuerte", permitido_ecologico=False)
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(producto_id=quimico["id"]),
        )
        assert respuesta.status_code == 422
        assert "V15_no_ecologico" in codigos(respuesta)

    def test_avisa_si_el_bote_esta_caducado(self, cliente, cuenta, crear_producto, nuevo_tratamiento):
        viejo = crear_producto(nombre_comercial="Viejo", fecha_caducidad="2026-01-15")
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(producto_id=viejo["id"]),
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "V16_producto_caducado" in avisos
        assert not avisos["V16_producto_caducado"]["bloquea"]

    def test_se_copia_la_zona_de_nitratos_de_la_parcela(
        self, cliente, cuenta, crear_parcela, nuevo_tratamiento
    ):
        en_zona = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(parcela_id=en_zona["id"]),
        )
        assert respuesta.json()["en_zona_vulnerable"] is True

    def test_un_producto_tiene_que_estar_comprado_antes(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        """El apunte no puede inventarse un producto que no está en la lista de compras."""
        respuesta = cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(producto_id=9999),
        )
        assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# Cosecha: los días de espera
# --------------------------------------------------------------------------


class TestCosecha:
    def _apuntar_tratamiento(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        assert respuesta.status_code == 201, respuesta.text

    def test_no_se_puede_cosechar_antes_de_que_pasen_los_dias(
        self, cliente, cuenta, campana, parcela, nuevo_tratamiento
    ):
        self._apuntar_tratamiento(cliente, cuenta, nuevo_tratamiento)
        respuesta = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-10",
                "parcela_id": parcela["id"],
            },
        )
        assert respuesta.status_code == 422
        assert "V9_no_puedes_cosechar" in codigos(respuesta)

    def test_el_aviso_dice_el_dia_exacto_y_cuantos_faltan(
        self, cliente, cuenta, campana, parcela, nuevo_tratamiento
    ):
        self._apuntar_tratamiento(cliente, cuenta, nuevo_tratamiento)
        respuesta = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-10",
                "parcela_id": parcela["id"],
            },
        )
        mensaje = respuesta.json()["detail"]["avisos"][0]["mensaje"]
        assert "22/05/2026" in mensaje
        assert "12 días" in mensaje

    def test_se_puede_cosechar_el_dia_que_termine_el_plazo(
        self, cliente, cuenta, campana, parcela, nuevo_tratamiento
    ):
        self._apuntar_tratamiento(cliente, cuenta, nuevo_tratamiento)
        respuesta = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": FECHA_FIN_ESPERA,
                "parcela_id": parcela["id"],
            },
        )
        assert respuesta.status_code == 201, respuesta.text

    def test_un_tratamiento_anulado_ya_no_bloquea_la_cosecha(
        self, cliente, cuenta, campana, parcela, nuevo_tratamiento
    ):
        creado = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.post(
            f"/api/tratamientos/{creado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de parcela"},
        )
        respuesta = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-10",
                "parcela_id": parcela["id"],
            },
        )
        assert respuesta.status_code == 201, respuesta.text


# --------------------------------------------------------------------------
# Fertilización: el registro obligatorio desde 2026
# --------------------------------------------------------------------------


class TestFertilizacion:
    def test_calcula_el_abono_puro(self, cliente, cuenta, nueva_fertilizacion):
        respuesta = cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        # 300 kg/ha al 33,5 % son 100,5 kg de nitrógeno por hectárea.
        assert datos["uf_n_ha"] == pytest.approx(100.5)
        assert datos["cantidad_total_kg"] == pytest.approx(729.0)
        assert datos["uf_n_total"] == pytest.approx(244.215, abs=0.001)

    def test_guarda_una_copia_de_la_riqueza(self, cliente, cuenta, nueva_fertilizacion):
        """El histórico no puede cambiar si alguien edita la ficha del abono."""
        datos = cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        ).json()
        assert datos["riqueza_n"] == 33.5

    def test_abonar_mas_hectareas_que_la_parcela_no_se_guarda(
        self, cliente, cuenta, nueva_fertilizacion
    ):
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(superficie_ha=9.0),
        )
        assert respuesta.status_code == 422
        assert "F2_superficie_excedida" in codigos(respuesta)

    def test_sin_kilos_por_hectarea_no_se_guarda(self, cliente, cuenta, nueva_fertilizacion):
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(kg_ha_producto=0),
        )
        assert respuesta.status_code == 422

    def test_en_zona_de_nitratos_avisa_de_las_reglas_mas_duras(
        self, cliente, cuenta, crear_parcela, nueva_fertilizacion
    ):
        en_zona = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(parcela_id=en_zona["id"]),
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "F3_zona_nitratos" in avisos
        assert not avisos["F3_zona_nitratos"]["bloquea"]

    def test_en_regadio_sin_plan_de_abono_avisa(self, cliente, cuenta, crear_parcela, nueva_fertilizacion):
        regadio = crear_parcela(alias="El Regadío", sistema="regadio")
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(parcela_id=regadio["id"]),
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "F4_sin_plan_regadio" in avisos

    def test_en_secano_no_se_pide_el_plan(self, cliente, cuenta, nueva_fertilizacion):
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(),
        )
        codigos_avisos = {a["codigo"] for a in respuesta.json()["avisos"]}
        assert "F4_sin_plan_regadio" not in codigos_avisos

    def test_se_marca_que_la_parcela_esta_en_zona_de_nitratos(
        self, cliente, cuenta, crear_parcela, nueva_fertilizacion
    ):
        en_zona = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        datos = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(parcela_id=en_zona["id"]),
        ).json()
        assert datos["en_zona_vulnerable"] is True


# --------------------------------------------------------------------------
# Nada se borra
# --------------------------------------------------------------------------


class TestAnulacion:
    def test_anular_no_borra_el_apunte(self, cliente, cuenta, nuevo_tratamiento):
        creado = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.post(
            f"/api/tratamientos/{creado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de fecha"},
        )
        con_anulados = cliente.get(
            f"{url_tratamientos()}?incluir_anulados=true", headers=cuenta["cabeceras"]
        ).json()
        assert len(con_anulados) == 1
        assert con_anulados[0]["anulado"] is True

    def test_un_apunte_anulado_no_sale_en_el_cuaderno(self, cliente, cuenta, nuevo_tratamiento):
        creado = cliente.post(
            url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        cliente.post(
            f"/api/tratamientos/{creado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de fecha"},
        )
        assert cliente.get(url_tratamientos(), headers=cuenta["cabeceras"]).json() == []


# --------------------------------------------------------------------------
# Aislamiento entre fincas
# --------------------------------------------------------------------------


class TestAislamiento:
    def test_no_se_ve_la_parcela_de_otra_finca(self, cliente, cuenta, parcela, crear_cuenta):
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.get(f"/api/parcelas/{parcela['id']}", headers=otro["cabeceras"])
        assert respuesta.status_code == 404

    def test_no_se_puede_apuntar_en_una_parcela_ajena(
        self, cliente, cuenta, parcela, crear_cuenta, campana, producto
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        campana_ajena = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()
        respuesta = cliente.post(
            url_tratamientos(),
            headers=otro["cabeceras"],
            json={
                "campana_id": campana_ajena["id"],
                "fecha": FECHA_TRATAMIENTO,
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Probando",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 404

    def test_cada_finca_ve_solo_sus_parcelas(self, cliente, cuenta, parcela, crear_cuenta):
        otro = crear_cuenta("otro@ejemplo.test")
        assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) == 1
        assert cliente.get("/api/parcelas", headers=otro["cabeceras"]).json() == []

    def test_un_token_manipulado_no_vale(self, cliente, cuenta):
        falso = cuenta["token"][:-6] + "AAAAAA"
        respuesta = cliente.get("/api/parcelas", headers={"Authorization": f"Bearer {falso}"})
        assert respuesta.status_code == 401


# --------------------------------------------------------------------------
# Grupos de parcelas (unidad homogénea de cultivo)
# --------------------------------------------------------------------------


CUADRADO_CERCA_1 = "POLYGON((-5.0000 40.0000, -5.0010 40.0000, -5.0010 40.0010, -5.0000 40.0010, -5.0000 40.0000))"
CUADRADO_CERCA_2 = "POLYGON((-5.0020 40.0000, -5.0030 40.0000, -5.0030 40.0010, -5.0020 40.0010, -5.0020 40.0000))"
CUADRADO_LEJOS = "POLYGON((-6.0000 40.0000, -6.0010 40.0000, -6.0010 40.0010, -6.0000 40.0010, -6.0000 40.0000))"


class TestGrupos:
    def _preparar(self, cliente, cuenta, crear_parcela, campana):
        parcelas = [
            crear_parcela(alias="Trigo 1", geometria=CUADRADO_CERCA_1),
            crear_parcela(alias="Trigo 2", geometria=CUADRADO_CERCA_2),
            crear_parcela(alias="Trigo 3", geometria=CUADRADO_LEJOS),
        ]
        for parcela in parcelas:
            respuesta = cliente.post(
                f"/api/parcelas/{parcela['id']}/cultivos",
                headers=cuenta["cabeceras"],
                json={
                    "campana_id": campana["id"],
                    "especie": "Trigo blando",
                    "sistema": "secano",
                    "fecha_inicio": "2025-10-15",
                    "fecha_fin": "2026-06-30",
                },
            )
            assert respuesta.status_code == 201, respuesta.text
        return parcelas

    def test_agrupa_las_parcelas_que_se_llevan_igual_y_estan_cerca(
        self, cliente, cuenta, crear_parcela, campana
    ):
        parcelas = self._preparar(cliente, cuenta, crear_parcela, campana)
        respuesta = cliente.post(
            f"/api/grupos/calcular?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["grupos_creados"] == 1

        grupos = cliente.get("/api/grupos", headers=cuenta["cabeceras"]).json()
        assert len(grupos) == 1
        # Las dos de al lado sí; la que está a 85 km, no.
        assert set(grupos[0]["parcela_ids"]) == {parcelas[0]["id"], parcelas[1]["id"]}

    def test_un_grupo_a_mano(self, cliente, cuenta, crear_parcela):
        primera = crear_parcela(alias="Uno")
        segunda = crear_parcela(alias="Dos")
        respuesta = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Los trigos del río",
                "cultivo": "Trigo blando",
                "parcela_ids": [primera["id"], segunda["id"]],
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert set(respuesta.json()["parcela_ids"]) == {primera["id"], segunda["id"]}

    def test_un_grupo_de_una_sola_parcela_no_tiene_sentido(self, cliente, cuenta, parcela):
        respuesta = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Solo una", "parcela_ids": [parcela["id"]]},
        )
        assert respuesta.status_code == 422
        assert "dos parcelas" in respuesta.json()["detail"]

    def test_no_se_agrupan_parcelas_sin_cultivo_declarado(self, cliente, cuenta, crear_parcela, campana):
        crear_parcela(alias="Sin cultivo 1")
        crear_parcela(alias="Sin cultivo 2")
        respuesta = cliente.post(
            f"/api/grupos/calcular?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.json()["grupos_creados"] == 0


# --------------------------------------------------------------------------
# El cuaderno: resumen, lo que falta, papel y exportación
# --------------------------------------------------------------------------


class TestCuaderno:
    def test_el_resumen_cuenta_lo_que_hay(self, cliente, cuenta, campana, parcela, nuevo_tratamiento, nueva_fertilizacion):
        cliente.post(url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        )
        resumen = cliente.get(
            f"/api/cuaderno/resumen?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert resumen["apuntes_de_producto"] == 1
        assert resumen["apuntes_de_abono"] == 1
        # Los trabajos también se cuentan. Se añadió porque la pantalla de inicio decidía si
        # decirle al agricultor «todavía no has apuntado nada» mirando solo lo que recordaba su
        # móvil: quien había apuntado un abono desde otro aparato leía que su cuaderno estaba
        # vacío. Con los tres números, esa frase es un dato comprobado.
        assert resumen["apuntes_de_trabajo"] == 0
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "laboreo",
                "fecha": "2026-03-05",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "cultivo": "Trigo blando",
            },
        )
        de_nuevo = cliente.get(
            f"/api/cuaderno/resumen?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert de_nuevo["apuntes_de_trabajo"] == 1
        # Y no se mezclan: un trabajo no es un apunte de producto ni de abono.
        assert de_nuevo["apuntes_de_producto"] == 1
        assert de_nuevo["apuntes_de_abono"] == 1
        # El resumen es para leerlo, así que va redondeado a dos decimales: 244,22 kg.
        # El dato exacto (244,215) está en cada apunte de abono, sin redondear.
        assert resumen["nitrogeno_total_kg"] == pytest.approx(244.22, abs=0.001)

    def test_lo_que_falta_dice_el_nombre_de_la_parcela(self, cliente, cuenta, campana, parcela):
        respuesta = cliente.get(
            f"/api/cuaderno/falta?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        pendientes = respuesta.json()["pendientes"]
        assert any(p["tipo"] == "parcela_sin_cultivo" for p in pendientes)
        assert any("El Prado" in p["mensaje"] for p in pendientes)

    def test_sin_nada_apuntado_no_se_dice_que_este_todo_bien(self, cliente, cuenta, campana):
        """**Un cuaderno sin empezar no está al día** (01/10/2026, T02).

        Con cero tierras y cero apuntes, las comprobaciones de `lo_que_falta` no tienen nada que mirar, así
        que la lista de pendientes salía vacía y la respuesta decía «esta_completo: true» con el mensaje «No
        te falta nada por apuntar». **El silencio se leía como un visto bueno**, y delante de una inspección
        eso es lo peor que puede decir este programa: un cuaderno vacío no está al día, está sin empezar.

        Ahora la respuesta lo dice con su propio texto y `esta_completo` es `None` (no es que falte algo: es
        que no hay nada que revisar todavía, que no es lo mismo ni se escribe igual).
        """
        datos = cliente.get(
            f"/api/cuaderno/falta?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert datos["esta_completo"] is None, "un cuaderno vacío no puede salir «completo»"
        assert datos["pendientes"] == []
        assert datos["mensaje"], "tiene que decir que no hay nada que revisar"
        assert "no hay nada que revisar" in datos["mensaje"]
        assert "no te falta nada" not in datos["mensaje"].lower()

    def test_con_una_tierra_sin_cultivo_ya_hay_algo_que_revisar(self, cliente, cuenta, campana, parcela):
        """El otro lado de lo mismo: en cuanto hay **una** tierra, sí se puede decir si falta algo."""
        datos = cliente.get(
            f"/api/cuaderno/falta?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert datos["esta_completo"] is False
        assert [p["tipo"] for p in datos["pendientes"]] == ["parcela_sin_cultivo"]

    def test_cuando_esta_todo_se_dice_que_esta_bien(
        self, cliente, cuenta, campana, parcela, aplicador, equipo, nuevo_tratamiento
    ):
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "Trigo blando"},
        )
        # Un apunte está completo cuando además dice quién aplicó y con qué máquina:
        # son dos datos obligatorios del cuaderno, no un extra.
        cliente.post(
            url_tratamientos(),
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(aplicador_id=aplicador["id"], equipo_id=equipo["id"]),
        )
        datos = cliente.get(
            f"/api/cuaderno/falta?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert datos["esta_completo"] is True
        assert datos["mensaje"]

    def test_si_falta_quien_aplico_se_dice(
        self, cliente, cuenta, campana, parcela, nuevo_tratamiento
    ):
        """El apunte se guarda igual, pero el cuaderno avisa de que está a medias."""
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "Trigo blando"},
        )
        cliente.post(url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        datos = cliente.get(
            f"/api/cuaderno/falta?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert datos["esta_completo"] is False
        tipos = [p["tipo"] for p in datos["pendientes"]]
        assert "tratamiento_sin_aplicador_o_equipo" in tipos
        mensaje = next(
            p["mensaje"] for p in datos["pendientes"] if p["tipo"] == "tratamiento_sin_aplicador_o_equipo"
        )
        assert "quién echó el producto" in mensaje

    def test_el_pdf_se_genera(self, cliente, cuenta, campana, nuevo_tratamiento, nueva_fertilizacion):
        cliente.post(url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
        )
        respuesta = cliente.get(
            f"/api/cuaderno/pdf?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"] == "application/pdf"
        assert respuesta.content.startswith(b"%PDF")
        assert len(respuesta.content) > 1500

    def test_el_pdf_sale_aunque_falten_datos(self, cliente, cuenta, campana, parcela):
        """Negar el papel hasta que esté perfecto es la forma más rápida de que abandone."""
        respuesta = cliente.get(
            f"/api/cuaderno/pdf?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        assert respuesta.content.startswith(b"%PDF")

    def test_el_pdf_de_una_campana_vacia_tambien_sale(self, cliente, cuenta, campana):
        respuesta = cliente.get(
            f"/api/cuaderno/pdf?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200

    def test_la_exportacion_lleva_los_datos_y_las_tildes(
        self, cliente, cuenta, campana, nuevo_tratamiento
    ):
        cliente.post(url_tratamientos(), headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        respuesta = cliente.get(
            f"/api/cuaderno/export.csv?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        texto = respuesta.content.decode("utf-8")
        assert "El Prado" in texto
        assert "Ejemplo 25 EC" in texto
        assert "1,9440" in texto
        # El BOM es lo que hace que Excel no destroce las tildes.
        assert texto.startswith("\ufeff")


# --------------------------------------------------------------------------
# Ayuda
# --------------------------------------------------------------------------


class TestAyuda:
    def test_la_ayuda_trae_los_textos_y_los_plazos_legales(self, cliente):
        datos = cliente.get("/api/ayuda").json()
        assert "para_que_sirve" in datos["porques"]
        assert datos["plazos_legales"]["cuaderno_en_papel_hasta"] == "31/12/2026"
        assert datos["plazos_legales"]["productos_electronico_desde"] == "01/01/2027"
        assert datos["plazos_legales"]["abonos_obligatorio_desde"] == "01/01/2026"

    def test_la_ayuda_de_un_campo(self, cliente):
        datos = cliente.get("/api/ayuda/producto.plazo_seguridad_dias").json()
        assert datos["titulo"] == "Días de espera"
        assert datos["que_es"]

    def test_pedir_ayuda_de_algo_que_no_existe(self, cliente):
        assert cliente.get("/api/ayuda/inventado").status_code == 404

    def test_la_ayuda_no_lleva_jerga_en_la_respuesta(self, cliente):
        """La ayuda sale de la API, así que se comprueba lo que de verdad se sirve."""
        from app import textos

        datos = cliente.get("/api/ayuda").json()
        for texto in list(datos["porques"].values()):
            assert textos.palabras_prohibidas_encontradas(texto) == []
        for campo in datos["campos"]:
            for valor in campo.values():
                assert textos.palabras_prohibidas_encontradas(str(valor)) == []


# --------------------------------------------------------------------------
# Avisos que caducan
# --------------------------------------------------------------------------


class TestAvisos:
    def test_sin_nada_que_avisar_se_dice_que_todo_esta_bien(self, cliente, cuenta):
        respuesta = cliente.get("/api/avisos", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        assert respuesta.json()["avisos"][0]["tipo"] == "todo_bien"

    def test_avisa_de_un_carne_que_caduca_pronto(self, cliente, cuenta, crear_aplicador):
        dentro_de_20_dias = (hoy() + dt.timedelta(days=20)).isoformat()
        crear_aplicador(nombre="Juan", fecha_caducidad_carne=dentro_de_20_dias)
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        assert any(a["tipo"] == "carne" for a in avisos)
        assert any("Juan" in a["mensaje"] for a in avisos)

    def test_avisa_de_una_itu_que_caduca_pronto(self, cliente, cuenta, crear_equipo):
        dentro_de_30_dias = (hoy() + dt.timedelta(days=30)).isoformat()
        crear_equipo(nombre="Atomizador", fecha_proxima_iteaf=dentro_de_30_dias)
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        assert any(a["tipo"] == "iteaf" for a in avisos)

    def test_una_itu_caducada_es_urgente(self, cliente, cuenta, crear_equipo):
        crear_equipo(nombre="Viejo", fecha_proxima_iteaf="2020-01-01")
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        urgentes = [a for a in avisos if a["tipo"] == "iteaf"]
        assert urgentes and urgentes[0]["urgente"] is True


class TestElNumeroDeRegistroContraElListadoOficial:
    """El nº de registro se comprueba contra el listado oficial de productos del MAPA.

    Es un aviso, **nunca un bloqueo**: el agricultor puede apuntar lo que quiera, pero en una
    inspección lo que se mira es ese número. Y cuando el listado oficial no está bajado, el programa
    **no dice nada** —«no lo sé» no es «no existe»—, que es lo que impide que este aviso se convierta
    en una mentira.
    """

    def _un_numero_que_esta(self) -> str:
        """Un número de registro sacado del propio listado oficial: no se inventa ninguno."""
        from openpyxl import load_workbook

        from app import registro_oficial_de_productos as registro

        libro = load_workbook(registro.RUTA, read_only=True, data_only=True)
        hoja = libro[libro.sheetnames[0]]
        filas = hoja.iter_rows(values_only=True)
        for _ in range(registro.FILA_DE_LA_CABECERA):
            next(filas)
        numero = str(next(filas)[0]).strip()
        libro.close()
        return numero

    def test_un_numero_inventado_sale_en_los_avisos(self, cliente, cuenta, crear_producto):
        crear_producto(nombre_comercial="Producto raro", numero_registro="ES-99999999")
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        del_producto_avisos = [a for a in avisos if a["tipo"] == "numero_de_registro"]
        assert del_producto_avisos, "no ha avisado de un nº de registro que no está en el listado"
        assert "ES-99999999" in del_producto_avisos[0]["mensaje"]
        assert "listado oficial" in del_producto_avisos[0]["mensaje"]
        # No es urgente: es un dato que conviene mirar, no una cosa que caduque mañana.
        assert del_producto_avisos[0]["urgente"] is False

    def test_un_numero_que_esta_en_el_listado_no_da_la_lata(self, cliente, cuenta, crear_producto):
        """Si el número está en el registro oficial, este aviso no sale."""
        crear_producto(nombre_comercial="Producto de verdad", numero_registro=self._un_numero_que_esta())
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        assert not [a for a in avisos if a["tipo"] == "numero_de_registro"]

    def test_sin_el_listado_oficial_no_se_avisa_de_nada(self, cliente, cuenta, crear_producto, monkeypatch, tmp_path):
        """**El aviso más importante**: sin la lista bajada, el programa se calla.

        Un programa que dice «ese producto no existe» cuando en realidad no tiene la lista es peor
        que uno que no dice nada.
        """
        from app import registro_oficial_de_productos as registro

        monkeypatch.setattr(registro, "RUTA", tmp_path / "no_existe.xlsx")
        registro.olvidar()
        crear_producto(nombre_comercial="Producto sin lista", numero_registro="ES-99999999")

        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        assert not [a for a in avisos if a["tipo"] == "numero_de_registro"]
        registro.olvidar()

    def test_un_producto_sin_numero_de_registro_no_da_aviso(self, cliente, cuenta, crear_producto):
        """El número es opcional: si no está, no hay nada que comprobar ni que decir.

        Se apunta a propósito `numero_registro=None`, porque el producto de ejemplo de las pruebas
        trae por defecto un número inventado («24.123») que **sí** da aviso —y hace bien en darlo:
        ese número no está en el registro oficial—.
        """
        crear_producto(nombre_comercial="Sin número", numero_registro=None)
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        assert not [a for a in avisos if a["tipo"] == "numero_de_registro"]


# --------------------------------------------------------------------------
# Zonas vulnerables: la honestidad del "no lo sé"
# --------------------------------------------------------------------------


class TestZonasVulnerables:
    def test_sin_el_listado_cargado_el_programa_no_afirma_nada(self, cliente):
        """Sin el listado oficial no se puede decir que una parcela NO está en zona.

        Se dice "no lo sé" (None) en vez de False, y la aplicación pregunta.
        """
        estado = cliente.get("/api/zonas-vulnerables/estado").json()
        assert estado["cargado"] is False
        assert estado["municipios"] == 0

    def test_sin_listado_la_parcela_se_queda_sin_dato(self, cliente, cuenta, crear_parcela):
        parcela = crear_parcela(alias="Sin dato")
        assert parcela["zona_vulnerable_nitratos"] is None

    def test_el_agricultor_puede_marcarlo_a_mano(self, cliente, cuenta, crear_parcela):
        parcela = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        assert parcela["zona_vulnerable_nitratos"] is True


class TestListaOficialDeNitratos:
    """Cuando el listado oficial dice que sí, es que sí.

    Preguntarle al agricultor está bien para cuando no sabemos nada, pero no para
    dejarle contradecir el listado: la zona vulnerable no es una opinión suya, es lo
    que dice la ley, y de ahí salen obligaciones de abonado.
    """

    @pytest.fixture
    def listado(self, tmp_path):
        from app import catalogos

        ruta = tmp_path / "zv.csv"
        ruta.write_text(
            "municipio,provincia,codigo_ine\n"
            "Peñaranda de Bracamonte,Salamanca,37250\n",
            encoding="utf-8",
        )
        catalogos.cargar_zonas_vulnerables(ruta)
        assert catalogos.hay_datos_zonas_vulnerables()
        yield
        # Se deja limpio: un test que depende del orden de ejecución no vale nada.
        catalogos.olvidar_zonas_vulnerables()

    def test_la_lista_manda_sobre_lo_que_diga_el_agricultor(
        self, cliente, cuenta, crear_parcela, listado
    ):
        parcela = crear_parcela(
            municipio="Peñaranda de Bracamonte",
            provincia="Salamanca",
            zona_vulnerable_nitratos=False,
        )
        assert parcela["zona_vulnerable_nitratos"] is True

    def test_si_no_lo_sabe_se_deduce_de_la_lista(
        self, cliente, cuenta, crear_parcela, listado
    ):
        parcela = crear_parcela(
            municipio="Peñaranda de Bracamonte",
            provincia="Salamanca",
            zona_vulnerable_nitratos=None,
        )
        assert parcela["zona_vulnerable_nitratos"] is True

    def test_un_pueblo_que_no_esta_en_la_lista_no_se_marca(
        self, cliente, cuenta, crear_parcela, listado
    ):
        parcela = crear_parcela(municipio="Otro Pueblo", provincia="Salamanca")
        assert parcela["zona_vulnerable_nitratos"] is False

    def test_sin_ubicacion_propia_no_se_copia_la_de_la_explotacion(
        self, cliente, cuenta, crear_parcela, listado
    ):
        # La explotación está en Peñaranda, incluida en el listado de esta prueba.
        parcela = crear_parcela(municipio="", provincia="", zona_vulnerable_nitratos=None)
        assert parcela["zona_vulnerable_nitratos"] is None
        assert parcela["municipio"] == ""
        assert parcela["provincia"] == ""

    def test_sin_listado_el_agricultor_sigue_decidiendo(self, cliente, cuenta, crear_parcela):
        parcela = crear_parcela(zona_vulnerable_nitratos=False)
        assert parcela["zona_vulnerable_nitratos"] is False
