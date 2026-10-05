"""Las reglas de abono de las zonas de nitratos (Orden MAV/398/2022).

Hasta la ronda 11 la aplicación decía «en tu zona hay reglas más estrictas» y **no decía
cuáles**. El motivo era bueno —no inventarse una norma— pero el resultado no servía: un aviso
que no dice qué hay que hacer no ayuda a nadie.

Los números de esta ronda **no están inventados**: salen de la presentación «Zonas Vulnerables a
la contaminación por nitratos en Castilla y León» de la Consejería de Medio Ambiente, Vivienda y
Ordenación del Territorio (abril de 2026), que es la que recoge el contenido del programa de
actuación. Cada regla lleva escrita su fuente en `catalogos.REGLAS_NITRATOS`.

Los anexos III y V se extraen del PDF oficial y quedan disponibles para consulta. El cuaderno
todavía no comprueba automáticamente todos los casos: faltan la delimitación municipal y los
datos de siembra, cosecha o parada vegetativa necesarios para periodos relativos.
"""

from __future__ import annotations

import pytest

from app import catalogos, textos


class TestLasReglasCargadas:
    def test_estan_las_que_el_documento_de_la_junta_dice(self):
        claves = {regla.clave for regla in catalogos.REGLAS_NITRATOS}
        assert "estiercol_170" in claves
        assert "pendiente_15" in claves
        assert "orilla_5_m" in claves
        assert "sin_cultivo" in claves
        assert "riesgo_escorrentia" in claves
        assert "forestal" in claves

    def test_el_tope_de_estiercol_es_170_kg_de_nitrogeno_por_hectarea(self):
        """Es el número de la Directiva de nitratos, y lo dice la propia Junta."""
        assert catalogos.limite_de_estiercol_kg_n_ha() == 170.0
        regla = catalogos.regla_de_nitratos("estiercol_170")
        assert regla.valor == 170.0
        assert "kg N/ha" in regla.unidad

    def test_la_pendiente_maxima_para_liquidos_es_15_por_ciento(self):
        assert catalogos.pendiente_maxima_para_organico_liquido() == 15.0

    def test_cada_regla_dice_de_donde_sale(self):
        """Para que nadie tenga que preguntarse de dónde ha salido un número."""
        for regla in catalogos.REGLAS_NITRATOS:
            assert regla.fuente.strip(), regla.clave
            assert "MAV/398/2022" in regla.fuente, regla.clave

    def test_cada_regla_dice_que_hace_la_aplicacion(self):
        for regla in catalogos.REGLAS_NITRATOS:
            assert regla.que_hace_la_app in ("avisa", "consulta", "sin_datos"), regla.clave

    def test_lo_que_no_se_puede_comprobar_esta_marcado_como_tal(self):
        """Las dos tablas ya están; todavía no se presentan como comprobación automática."""
        consulta = {r.clave for r in catalogos.reglas_nitratos() if r.que_hace_la_app == "consulta"}
        assert consulta == {"aportes_por_cultivo", "periodos_prohibidos"}

    def test_y_se_dice_que_falta_en_cristiano(self):
        assert catalogos.LIMITES_QUE_FALTAN == ()
        assert catalogos.limites_que_faltan() == ()

    def test_lo_que_falta_dice_por_que_no_se_puede_comprobar(self):
        assert all(r.que_hace_la_app != "sin_datos" for r in catalogos.reglas_nitratos())

    def test_el_abono_organico_se_distingue_del_de_fabrica(self):
        """La regla de los 170 kg va sobre los estiércoles, no sobre los minerales."""
        assert catalogos.es_abono_organico("organico") is True
        assert catalogos.es_abono_organico("organo-mineral") is True
        assert catalogos.es_abono_organico("mineral") is False
        assert catalogos.es_abono_organico(None) is False
        assert catalogos.es_abono_organico("") is False


class TestElAvisoDeLaZona:
    def _avisar(self, cliente, cuenta, parcela, **cambios):
        from tests.conftest import DATOS_CUENTA  # noqa: F401

        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        cuerpo = {
            "campana_id": campana["id"],
            "fecha": "2026-02-20",
            "parcela_id": parcela["id"],
            "superficie_ha": parcela["superficie_ha"],
            "kg_ha_producto": 300.0,
        }
        cuerpo.update(cambios)
        respuesta = cliente.post(
            "/api/fertilizaciones/validar", headers=cuenta["cabeceras"], json=cuerpo
        )
        assert respuesta.status_code == 200, respuesta.text
        return {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}

    def test_en_zona_de_nitratos_el_aviso_trae_el_numero(self, cliente, cuenta, crear_parcela):
        """Ya no dice «hay reglas más estrictas»: dice cuáles y con qué número."""
        en_zona = crear_parcela(zona_vulnerable_nitratos=True)
        avisos = self._avisar(cliente, cuenta, en_zona)
        assert "F3_zona_nitratos" in avisos
        mensaje = avisos["F3_zona_nitratos"]["mensaje"]
        assert "170" in mensaje, "no dice el tope"
        assert "nitrógeno" in mensaje.lower()

    def test_fuera_de_la_zona_no_se_avisa_de_nada(self, cliente, cuenta, crear_parcela):
        """Fuera de zona vulnerable el Código de Buenas Prácticas es voluntario."""
        fuera = crear_parcela(zona_vulnerable_nitratos=False)
        avisos = self._avisar(cliente, cuenta, fuera)
        assert "F3_zona_nitratos" not in avisos
        assert not [c for c in avisos if c.startswith("N")]

    def test_si_no_se_sabe_si_esta_en_zona_no_se_avisa_de_lo_que_no_se_sabe(
        self, cliente, cuenta, crear_parcela
    ):
        """«No lo sé» no es «no». Pero tampoco se puede avisar de una regla que quizá no aplica."""
        no_se = crear_parcela(zona_vulnerable_nitratos=None)
        avisos = self._avisar(cliente, cuenta, no_se)
        assert "F3_zona_nitratos" not in avisos


class TestElTopeDeLosEstiercoles:
    """170 kg de nitrógeno por hectárea al año, en forma de estiércol o purín."""

    def _abonar(self, cliente, cuenta, parcela, fertilizante, **cambios):
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        cuerpo = {
            "campana_id": campana["id"],
            "fecha": "2026-02-20",
            "parcela_id": parcela["id"],
            "superficie_ha": parcela["superficie_ha"],
            "fertilizante_id": fertilizante["id"],
            "kg_ha_producto": 1000.0,
        }
        cuerpo.update(cambios)
        return cliente.post("/api/fertilizaciones", headers=cuenta["cabeceras"], json=cuerpo)

    def _validar(self, cliente, cuenta, parcela, fertilizante, **cambios):
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        cuerpo = {
            "campana_id": campana["id"],
            "fecha": "2026-02-20",
            "parcela_id": parcela["id"],
            "superficie_ha": parcela["superficie_ha"],
            "fertilizante_id": fertilizante["id"],
            "kg_ha_producto": 100.0,
        }
        cuerpo.update(cambios)
        respuesta = cliente.post(
            "/api/fertilizaciones/validar", headers=cuenta["cabeceras"], json=cuerpo
        )
        return {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}

    @pytest.fixture
    def purin(self, cliente, cuenta):
        """Un purín con un 4 % de nitrógeno: 1.000 kg/ha son 40 kg N/ha."""
        respuesta = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Purín de cerdo", "tipo": "organico", "riqueza_n": 4.0},
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    @pytest.fixture
    def urea(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Urea 46%", "tipo": "mineral", "riqueza_n": 46.0},
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def test_pasarse_del_tope_avisa_con_los_numeros(
        self, cliente, cuenta, crear_parcela, purin
    ):
        """5.000 kg/ha de purín al 4 % son 200 kg N/ha: pasa de 170."""
        en_zona = crear_parcela(zona_vulnerable_nitratos=True)
        avisos = self._validar(cliente, cuenta, en_zona, purin, kg_ha_producto=5000.0)
        assert "N1_estiercol_pasa_tope" in avisos
        mensaje = avisos["N1_estiercol_pasa_tope"]["mensaje"]
        assert "170" in mensaje, "no dice el tope"
        assert "200" in mensaje, "no dice cuánto llevaría"

    def test_el_aviso_no_bloquea(self, cliente, cuenta, crear_parcela, purin):
        """El cuaderno tiene que recoger lo que ha pasado, aunque se haya pasado.

        Si el programa impidiera apuntarlo, el cuaderno acabaría diciendo que ese abono no se
        echó, que es peor que el error que se quiere evitar.
        """
        en_zona = crear_parcela(zona_vulnerable_nitratos=True)
        avisos = self._validar(cliente, cuenta, en_zona, purin, kg_ha_producto=5000.0)
        assert avisos["N1_estiercol_pasa_tope"]["bloquea"] is False

    def test_por_debajo_del_tope_no_avisa(self, cliente, cuenta, crear_parcela, purin):
        en_zona = crear_parcela(zona_vulnerable_nitratos=True)
        avisos = self._validar(cliente, cuenta, en_zona, purin, kg_ha_producto=1000.0)
        assert "N1_estiercol_pasa_tope" not in avisos

    def test_lo_que_ya_se_echa_ese_ano_cuenta(self, cliente, cuenta, crear_parcela, purin):
        """El tope es **al año**, así que dos aportes que por separado caben, juntos no."""
        en_zona = crear_parcela(zona_vulnerable_nitratos=True)
        # 4.000 kg/ha al 4 % = 160 kg N/ha. Cabe.
        primera = self._abonar(cliente, cuenta, en_zona, purin, kg_ha_producto=4000.0)
        assert primera.status_code == 201, primera.text

        # Y ahora 1.000 kg/ha más: 40 más, total 200. No cabe.
        avisos = self._validar(cliente, cuenta, en_zona, purin, kg_ha_producto=1000.0)
        assert "N1_estiercol_pasa_tope" in avisos
        assert "160" in avisos["N1_estiercol_pasa_tope"]["mensaje"], "no cuenta lo de antes"

    def test_un_abono_de_fabrica_no_cuenta_para_el_tope(self, cliente, cuenta, crear_parcela, urea):
        """La regla de los 170 kg es sobre los estiércoles, no sobre el nitrógeno mineral."""
        en_zona = crear_parcela(zona_vulnerable_nitratos=True)
        avisos = self._validar(cliente, cuenta, en_zona, urea, kg_ha_producto=500.0)
        assert "N1_estiercol_pasa_tope" not in avisos

    def test_fuera_de_la_zona_el_tope_no_se_aplica(self, cliente, cuenta, crear_parcela, purin):
        fuera = crear_parcela(zona_vulnerable_nitratos=False)
        avisos = self._validar(cliente, cuenta, fuera, purin, kg_ha_producto=5000.0)
        assert "N1_estiercol_pasa_tope" not in avisos

    def test_lo_anulado_no_cuenta_para_el_tope(self, cliente, cuenta, crear_parcela, purin):
        en_zona = crear_parcela(zona_vulnerable_nitratos=True)
        creada = self._abonar(cliente, cuenta, en_zona, purin, kg_ha_producto=4000.0).json()
        cliente.post(
            f"/api/fertilizaciones/{creada['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de parcela"},
        )
        avisos = self._validar(cliente, cuenta, en_zona, purin, kg_ha_producto=1000.0)
        assert "N1_estiercol_pasa_tope" not in avisos, "lo anulado no se echó"


class TestElTopeCuandoSeAbonaPorGrupo:
    """El tope de los 170 kg en un apunte que va sobre **varias tierras a la vez** (A4 de T02).

    **Por qué estas pruebas existen.** El tope es **por tierra y por año**, y un apunte de grupo no
    lleva `parcela_id`: es lo que manda la pantalla al elegir el grupo. Antes, eso hacía que ese
    nitrógeno **no contara para ninguna tierra**, así que la regla no saltaba nunca. Ahora cuenta en
    cada tierra del grupo a su dosis **por hectárea** (nunca repartiendo los kilos totales del
    grupo, que sería inventarse un reparto: un grupo es una unidad homogénea de cultivo,
    `models.GrupoParcelas`), y al apuntar sobre el grupo se comprueba **tierra por tierra**, con la
    historia de cada una, para que quien abona siempre por grupo también vea el aviso.
    """

    @pytest.fixture
    def purin(self, cliente, cuenta):
        """Un purín con un 4 % de nitrógeno: 1.000 kg/ha son 40 kg N/ha."""
        respuesta = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Purín de cerdo", "tipo": "organico", "riqueza_n": 4.0},
        )
        return respuesta.json()

    def _grupo(self, cliente, cuenta, parcelas, nombre="Los trigos"):
        creado = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={"nombre": nombre, "parcela_ids": [p["id"] for p in parcelas]},
        )
        assert creado.status_code == 201, creado.text
        return next(
            g
            for g in cliente.get("/api/grupos", headers=cuenta["cabeceras"]).json()
            if g["id"] == creado.json()["id"]
        )

    def _abonar_en_la_tierra(self, cliente, cuenta, campana, parcela, purin, kg_ha):
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-10",
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": purin["id"],
                "kg_ha_producto": kg_ha,
            },
        )
        assert respuesta.status_code == 201, respuesta.text

    def _validar_en_el_grupo(self, cliente, cuenta, campana, grupo, purin, kg_ha=2500.0):
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-03-01",
                "grupo_id": grupo["id"],
                "superficie_ha": grupo["superficie_total_ha"],
                "fertilizante_id": purin["id"],
                "kg_ha_producto": kg_ha,
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        return {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}

    def test_se_comprueba_tierra_por_tierra_y_nombra_la_que_mas_llevaba(
        self, cliente, cuenta, campana, crear_parcela, purin
    ):
        """Una tierra del grupo ya lleva 80 kg N/ha: con los 100 del apunte serían 180 y pasa de 170."""
        primera = crear_parcela(alias="El Prado", zona_vulnerable_nitratos=True)
        segunda = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        # 2.000 kg/ha de purín al 4 % son 80 kg N/ha **en El Prado**.
        self._abonar_en_la_tierra(cliente, cuenta, campana, primera, purin, 2000.0)
        grupo = self._grupo(cliente, cuenta, [primera, segunda])

        avisos = self._validar_en_el_grupo(cliente, cuenta, campana, grupo, purin, kg_ha=2500.0)

        assert "F11_tope_estiercol_en_una_tierra_del_grupo" in avisos, (
            "la tierra del grupo que ya llevaba 80 kg N/ha llega a 180 con este abono, y el tope "
            "de la Orden MAV/398/2022 es de 170: antes el apunte de grupo no se comparaba con nada"
        )
        mensaje = avisos["F11_tope_estiercol_en_una_tierra_del_grupo"]["mensaje"]
        assert "El Prado" in mensaje, "el aviso tiene que decir de qué tierra del grupo habla"
        assert "170" in mensaje and "180,0" in mensaje
        assert avisos["F11_tope_estiercol_en_una_tierra_del_grupo"]["bloquea"] is False, (
            "avisa y no bloquea: el cuaderno tiene que recoger lo que de verdad se echó"
        )

    def test_con_las_tierras_por_debajo_del_tope_no_avisa(
        self, cliente, cuenta, campana, crear_parcela, purin
    ):
        """El control: sin pasarse, no hay aviso. Si no, el aviso no significaría nada."""
        primera = crear_parcela(alias="El Prado", zona_vulnerable_nitratos=True)
        segunda = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        grupo = self._grupo(cliente, cuenta, [primera, segunda])

        avisos = self._validar_en_el_grupo(cliente, cuenta, campana, grupo, purin, kg_ha=1000.0)
        assert "F11_tope_estiercol_en_una_tierra_del_grupo" not in avisos, "40 kg N/ha no es pasarse"

    def test_fuera_de_la_zona_el_tope_no_se_aplica_al_grupo(
        self, cliente, cuenta, campana, crear_parcela, purin
    ):
        """Si todas las tierras del grupo están fuera de la zona, no hay tope que comprobar."""
        primera = crear_parcela(alias="El Prado", zona_vulnerable_nitratos=False)
        segunda = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=False)
        grupo = self._grupo(cliente, cuenta, [primera, segunda])

        avisos = self._validar_en_el_grupo(cliente, cuenta, campana, grupo, purin, kg_ha=5000.0)
        assert not [codigo for codigo in avisos if codigo.startswith("N")]
        assert "F11_tope_estiercol_en_una_tierra_del_grupo" not in avisos

    def test_si_alguna_tierra_del_grupo_no_tiene_zona_comprobada_se_dice(
        self, cliente, cuenta, campana, crear_parcela, purin
    ):
        """Un grupo con una tierra de zona desconocida: no se puede dar por comprobado entero."""
        en_zona = crear_parcela(alias="El Prado", zona_vulnerable_nitratos=True)
        sin_zona = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=None)
        grupo = self._grupo(cliente, cuenta, [en_zona, sin_zona])

        avisos = self._validar_en_el_grupo(cliente, cuenta, campana, grupo, purin, kg_ha=1000.0)
        assert "N4_no_se_si_es_zona_de_nitratos" in avisos, (
            "esa tierra puede estar en zona y no se ha mirado: callarlo sería decir que está bien"
        )
        assert avisos["N4_no_se_si_es_zona_de_nitratos"]["bloquea"] is False

    def test_un_abono_de_grupo_sin_composicion_no_se_compara_contra_cero(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Sin composición no se puede calcular el aporte, así que no se compara con el tope."""
        primera = crear_parcela(alias="El Prado", zona_vulnerable_nitratos=True)
        segunda = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        grupo = self._grupo(cliente, cuenta, [primera, segunda])
        sin_composicion = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Purín del montón", "tipo": "organico"},
        ).json()

        avisos = self._validar_en_el_grupo(
            cliente, cuenta, campana, grupo, sin_composicion, kg_ha=5000.0
        )
        assert "F9_composicion_sin_comprobar" in avisos
        assert "F11_tope_estiercol_en_una_tierra_del_grupo" not in avisos, (
            "no se puede decir que se pasa ni que no: el aporte no se sabe calcular"
        )


class TestLaPendiente:
    @pytest.fixture
    def estiercol(self, cliente, cuenta):
        """Un estiércol orgánico: la regla de la pendiente es solo para los orgánicos."""
        respuesta = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Estiércol de vacuno", "tipo": "organico", "riqueza_n": 2.0},
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _validar(self, cliente, cuenta, parcela, abono, kg_ha=300.0):
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": abono["id"],
                "kg_ha_producto": kg_ha,
            },
        )
        return {a["codigo"]: a for a in respuesta.json()["avisos"]}

    def test_en_pendiente_avisa_de_que_solo_valen_los_solidos(
        self, cliente, cuenta, crear_parcela, estiercol
    ):
        inclinada = crear_parcela(zona_vulnerable_nitratos=True, pendiente_pct=22.0)
        avisos = self._validar(cliente, cuenta, inclinada, estiercol)
        assert "N2_pendiente_organico" in avisos
        mensaje = avisos["N2_pendiente_organico"]["mensaje"]
        assert "15" in mensaje, "no dice la pendiente máxima"
        assert "22" in mensaje, "no dice la pendiente de la parcela"
        assert "SÓLIDOS" in mensaje
        assert avisos["N2_pendiente_organico"]["bloquea"] is False

    def test_en_pendiente_pero_con_abono_de_fabrica_no_avisa(
        self, cliente, cuenta, crear_parcela, fertilizante
    ):
        """La regla es para los abonos orgánicos: el mineral no entra."""
        inclinada = crear_parcela(zona_vulnerable_nitratos=True, pendiente_pct=22.0)
        avisos = self._validar(cliente, cuenta, inclinada, fertilizante)
        assert "N2_pendiente_organico" not in avisos

    def test_en_llano_no_avisa(self, cliente, cuenta, crear_parcela, estiercol):
        llana = crear_parcela(zona_vulnerable_nitratos=True, pendiente_pct=3.0)
        avisos = self._validar(cliente, cuenta, llana, estiercol)
        assert "N2_pendiente_organico" not in avisos

    def test_sin_saber_la_pendiente_no_se_avisa_de_lo_que_no_se_sabe(
        self, cliente, cuenta, crear_parcela, estiercol
    ):
        """La pendiente la trae el SIGPAC; si no está, no se supone que sea llana."""
        sin_dato = crear_parcela(zona_vulnerable_nitratos=True, pendiente_pct=None)
        avisos = self._validar(cliente, cuenta, sin_dato, estiercol)
        assert "N2_pendiente_organico" not in avisos


class TestLosTextos:
    def test_los_mensajes_nuevos_existen_y_se_pueden_rellenar(self):
        for clave in ("N1_estiercol_pasa_tope", "N2_pendiente_organico"):
            assert clave in textos.MENSAJES

    def test_el_mensaje_del_tope_se_rellena_con_sus_cuatro_numeros(self):
        mensaje = textos.mensaje(
            "N1_estiercol_pasa_tope", tope="170", total="200,0", ya="160,0", nuevo="40,0"
        )
        assert "170" in mensaje and "200,0" in mensaje and "160,0" in mensaje and "40,0" in mensaje

    def test_el_mensaje_del_tope_dice_que_se_puede_apuntar(self):
        """Un aviso que no dice qué pasa si sigues no sirve de nada."""
        assert "Se puede apuntar" in textos.MENSAJES["N1_estiercol_pasa_tope"]

    def test_el_mensaje_de_la_pendiente_dice_qué_comprobar(self):
        """El programa no sabe si el abono es sólido o líquido, así que dice qué mirar."""
        mensaje = textos.MENSAJES["N2_pendiente_organico"]
        assert "purín" in mensaje.lower()

    def test_la_ayuda_tiene_su_apartado_de_reglas(self):
        pantalla = textos.PANTALLA_AYUDA
        assert pantalla["reglas_titulo"]
        assert pantalla["lo_que_falta_titulo"]
        assert pantalla["lo_que_falta_intro"]

    def test_la_ayuda_dice_que_lo_que_falta_no_es_un_olvido(self):
        assert "no es un olvido" in textos.PANTALLA_AYUDA["lo_que_falta_intro"].lower()

    def test_todo_el_texto_nuevo_esta_en_el_fichero_de_textos(self):
        visibles = textos.textos_visibles()
        assert textos.MENSAJES["N1_estiercol_pasa_tope"] in visibles
        assert textos.MENSAJES["N2_pendiente_organico"] in visibles
        assert textos.PANTALLA_AYUDA["reglas_titulo"] in visibles
        assert textos.PANTALLA_AYUDA["la_app_no_puede"] in visibles


class TestLoQueLlegaALaPantalla:
    def test_la_interfaz_trae_las_reglas_con_su_numero(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        reglas = {r["clave"]: r for r in datos["reglas_nitratos"]}
        assert reglas["estiercol_170"]["texto_valor"] == "170 kg N/ha al año"
        assert reglas["pendiente_15"]["texto_valor"] == "15 % de pendiente"

    def test_la_interfaz_dice_cuales_se_pueden_comprobar_y_cuales_no(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        reglas = {r["clave"]: r for r in datos["reglas_nitratos"]}
        assert reglas["estiercol_170"]["que_hace_la_app"] == "avisa"
        assert reglas["aportes_por_cultivo"]["que_hace_la_app"] == "consulta"

    def test_la_interfaz_trae_lo_que_falta(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert datos["limites_que_faltan"] == []
        assert len(datos["aportes_maximos_n"]) == 22
        assert len(datos["periodos_prohibidos_n"]) == 6

    def test_la_ayuda_completa_tambien(self, cliente):
        ayuda = cliente.get("/api/ayuda").json()
        assert len(ayuda["reglas_nitratos"]) == len(catalogos.REGLAS_NITRATOS)
        assert ayuda["limites_que_faltan"] == []
        assert len(ayuda["aportes_maximos_n"]) == 22


class TestElServicio:
    """El nitrógeno que ya se ha echado en una tierra, contado por el servicio.

    **Estas dos pruebas devolvían un número y ahora devuelven un `servicios.Nitrogeno`**, y el
    cambio es el arreglo de A4 y A6 de `docs/T02_VALORES_POR_DEFECTO.md`: un solo número no puede
    contar la verdad de este cálculo, porque hay aportes que **no se pueden atribuir** a la tierra
    (los que se apuntaron en varias tierras a la vez y no dicen cuál) y aportes de los que **no se
    conoce la composición**. Los dos se contaban como cero, que es exactamente el defecto. Ahora el
    número sigue estando en `.kg_n_ha` y los huecos se declaran aparte, para que quien avisa pueda
    decirlo.
    """

    def test_el_nitrogeno_organico_se_suma_solo_el_organico(
        self, cliente, cuenta, crear_parcela, campana, db_sesion
    ):
        from app import models, servicios

        parcela = crear_parcela(zona_vulnerable_nitratos=True)
        explotacion_id = cuenta["explotacion_id"]
        import datetime as dt

        db_sesion.add_all(
            [
                models.RegistroFertilizacion(
                    explotacion_id=explotacion_id,
                    campana_id=campana["id"],
                    fecha=dt.date(2026, 2, 1),
                    parcela_id=parcela["id"],
                    superficie_ha=1.0,
                    tipo="organico",
                    kg_ha_producto=1000.0,
                    cantidad_total_kg=1000.0,
                    uf_n_ha=40.0,
                ),
                models.RegistroFertilizacion(
                    explotacion_id=explotacion_id,
                    campana_id=campana["id"],
                    fecha=dt.date(2026, 2, 2),
                    parcela_id=parcela["id"],
                    superficie_ha=1.0,
                    tipo="mineral",
                    kg_ha_producto=100.0,
                    cantidad_total_kg=100.0,
                    uf_n_ha=46.0,
                ),
            ]
        )
        db_sesion.commit()
        organico = servicios.nitrogeno_organico_en_la_parcela(
            db_sesion,
            explotacion_id=explotacion_id,
            parcela_id=parcela["id"],
            campana_id=campana["id"],
        )
        todo = servicios.nitrogeno_aplicado_en_la_parcela(
            db_sesion,
            explotacion_id=explotacion_id,
            parcela_id=parcela["id"],
            campana_id=campana["id"],
        )
        assert organico.kg_n_ha == 40.0, "solo el orgánico"
        assert todo.kg_n_ha == 86.0, "y el total con el mineral"
        # Los dos apuntes se pudieron contar enteros: no hay nada que declarar como pendiente.
        assert organico.sin_composicion == 0 and organico.sin_atribuir == 0
        assert todo.sin_composicion == 0 and todo.sin_atribuir == 0
        assert todo.esta_completo is True

    def test_un_apunte_sin_composicion_no_suma_cero_sino_que_se_declara(
        self, cliente, cuenta, crear_parcela, campana, db_sesion
    ):
        """El caso de A6, en el servicio: sin composición no hay aporte que sumar, y se cuenta aparte.

        Antes, `uf_n_ha = 0.0` entraba en la suma como un cero, así que el programa comparaba el
        tope de 170 kg contra una cifra que decía que ese estiércol no había aportado nada.
        """
        from app import models, servicios

        parcela = crear_parcela(zona_vulnerable_nitratos=True)
        import datetime as dt

        db_sesion.add(
            models.RegistroFertilizacion(
                explotacion_id=cuenta["explotacion_id"],
                campana_id=campana["id"],
                fecha=dt.date(2026, 2, 1),
                parcela_id=parcela["id"],
                superficie_ha=1.0,
                tipo="organico",
                kg_ha_producto=5000.0,
                cantidad_total_kg=5000.0,
                # No consta la composición: es el `None` que ahora puede guardarse.
                riqueza_n=None,
                uf_n_ha=None,
            )
        )
        db_sesion.commit()

        organico = servicios.nitrogeno_organico_en_la_parcela(
            db_sesion,
            explotacion_id=cuenta["explotacion_id"],
            parcela_id=parcela["id"],
            campana_id=campana["id"],
        )
        assert organico.kg_n_ha == 0.0, "no hay nada que sumar: no se sabe lo que aportó"
        assert organico.sin_composicion == 1, (
            "pero el hueco se declara, que es lo que impide que parezca un cero"
        )
        assert organico.esta_completo is False
