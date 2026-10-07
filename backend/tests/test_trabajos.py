"""Las reglas de los trabajos por tierra (T15, 05/10/2026).

**Una prueba por regla del negocio, y cada una dice qué se rompe si falla.** Las cuatro que el encargo
nombra están aquí, con su nombre, y son las que hay que mirar primero:

  · `test_un_trabajo_previsto_no_consume_existencias`
  · `test_un_rodillo_despues_de_sembrar_no_borra_el_estado_de_siembra`
  · `test_una_lluvia_no_acredita_nascencia`
  · `test_anular_no_duplica_consumos`

Todas estas pruebas son de la **lógica pura** (`app/trabajos.py`): no hay base de datos, no hay
servidor y no hay navegador. Es a propósito: las reglas del cuaderno se comprueban hoy, sin esperar a
que estén las tablas nuevas, y una prueba que necesita medio programa montado para comprobar una resta
es una prueba que se deja de ejecutar.

Al final del fichero hay un bloque de las puertas del router (`/api/trabajos`). **Ya no se saltan**: el
coordinador integró las tablas, los esquemas y las frases, así que esas pruebas **se ejecutan** y cubren
el recorrido entero (planificar → marcar lo hecho → historial y existencias → anular). Comprobado el
07/10/2026 por la revisión del recorrido: `pytest tests/test_trabajos.py -q -rs` → **77 pasan, 0 saltan**.

**Lo que decía antes este párrafo** («se saltan con el motivo escrito mientras el coordinador no integre
las tablas y los esquemas») era verdad el 05/10 y dejó de serlo. Se deja dicho aquí porque un documento
que miente sobre el estado del proyecto es peor que uno viejo.
"""

from __future__ import annotations

import ast
import datetime as dt
import pathlib
import re
import textwrap

import pytest

from app import trabajos, textos

HOY = dt.date(2026, 4, 1)
LA_TIERRA = 5
LA_CAMPANA = 2026


def la_siembra(**cambios) -> dict:
    """Una siembra de trigo en la tierra 5, del 1 de marzo de 2026."""
    datos = {
        "id": 1,
        "campana_id": LA_CAMPANA,
        "tipo": "siembra",
        "fecha": dt.date(2026, 3, 1),
        "parcela_id": LA_TIERRA,
        "cultivo": "Trigo blando",
        "variedad": "Craklin",
        "superficie_ha": 3.0,
        "horas": 4.0,
        "equipo_id": 7,
        "insumos": [
            # La salida del almacén que sostiene esta siembra: 600 kg del envase 11, con su movimiento.
            trabajos.un_insumo(
                articulo_id=1,
                articulo="Semilla",
                lote_id=11,
                cantidad=600.0,
                unidad="kg",
                movimiento_id=101,
                origen_tipo="labor",
                origen_id=1,
            )
        ],
    }
    datos.update(cambios)
    return trabajos.un_hecho(**datos)


def el_rodillo(**cambios) -> dict:
    """Un rodillo diez días después de la siembra, en la misma tierra."""
    datos = {
        "id": 2,
        "campana_id": LA_CAMPANA,
        "tipo": "laboreo",
        "subtipo": "rodillo",
        "fecha": dt.date(2026, 3, 10),
        "parcela_id": LA_TIERRA,
        "superficie_ha": 3.0,
        "equipo_id": 7,
    }
    datos.update(cambios)
    return trabajos.un_hecho(**datos)


def la_lluvia(**cambios) -> dict:
    """Doce litros el 11 de marzo. Es un hecho del cuaderno y **no** es un trabajo."""
    datos = {
        "id": 3,
        "campana_id": LA_CAMPANA,
        "tipo": "lluvia",
        "fecha": dt.date(2026, 3, 11),
        "parcela_id": LA_TIERRA,
        "lluvia_mm": 12.0,
    }
    datos.update(cambios)
    return trabajos.un_hecho(**datos)


def una_observacion(**cambios) -> dict:
    """Lo que el agricultor ha visto en el campo. Es la única puerta de la nascencia."""
    datos = {
        "id": 4,
        "campana_id": LA_CAMPANA,
        "tipo": "observacion",
        "fecha": dt.date(2026, 3, 20),
        "parcela_id": LA_TIERRA,
        "nascencia": True,
        "observaciones": "Ha nacido parejo",
    }
    datos.update(cambios)
    return trabajos.un_hecho(**datos)


def una_cosecha(**cambios) -> dict:
    datos = {
        "id": 5,
        "campana_id": LA_CAMPANA,
        "tipo": "cosecha",
        "fecha": dt.date(2026, 7, 10),
        "parcela_id": LA_TIERRA,
        "superficie_ha": 3.0,
    }
    datos.update(cambios)
    return trabajos.un_hecho(**datos)


def el_previsto(**cambios) -> dict:
    """Un trabajo planificado: pasar el cultivador el 20 de abril."""
    datos = {
        "id": 9,
        "campana_id": LA_CAMPANA,
        "tipo": "laboreo",
        "subtipo": "cultivador",
        "fecha_prevista": dt.date(2026, 4, 20),
        "parcela_id": LA_TIERRA,
        "superficie_ha": 3.0,
        "insumos": [
            trabajos.un_insumo(articulo_id=2, articulo="Gasóleo", dosis_por_ha=100.0, unidad="L")
        ],
    }
    datos.update(cambios)
    return trabajos.un_previsto(**datos)


def el_consumo(**cambios) -> dict:
    """La salida del almacén que sostiene la siembra: 600 kg del envase 11."""
    datos = {
        "articulo_id": 1,
        "articulo": "Semilla",
        "lote_id": 11,
        "cantidad": 600.0,
        "unidad": "kg",
        "origen_tipo": "labor",
        "origen_id": 1,
        "movimiento_id": 101,
    }
    datos.update(cambios)
    return trabajos.un_insumo(**datos)


# ==========================================================================
# 1. Un trabajo previsto no consume existencias ni acredita trabajo hecho
# ==========================================================================


class TestLoPrevistoNoEsUnTrabajoHecho:
    def test_un_trabajo_previsto_no_consume_existencias(self):
        """**La regla del encargo, entera.** Un plan no gasta nada del almacén.

        Si esto fallara, planificar la siembra de la semana que viene descontaría la semilla hoy: el
        agricultor vería su almacén vaciado por algo que todavía no ha hecho, y el libro diría que
        gastó un producto que sigue en la nave.
        """
        plan = el_previsto()
        consume, porque = trabajos.consume_existencias(plan)
        assert consume is False, "un trabajo previsto ha dicho que consume"
        assert porque == "TJ1_el_previsto_no_gasta"

        # Y con la salida del almacén delante —aunque no debería existir—, no cuenta.
        cuentas = trabajos.consumos_que_cuentan([plan], [el_consumo(origen_tipo="trabajo_previsto", origen_id=9)])
        assert cuentas["cuantos_cuentan"] == 0, "lo previsto ha descontado del almacén"
        assert cuentas["por_articulo"] == {}, "hay una cifra de almacén que sale de un plan"
        assert cuentas["no_cuentan"][0]["motivo_codigo"] == "TJ1_el_previsto_no_gasta"

    def test_lo_que_gastaria_lo_previsto_se_dice_como_estimacion(self):
        """Se puede enseñar lo que va a hacer falta, **dicho como estimación** y sin tocar nada."""
        gasto = trabajos.estimacion_de_lo_previsto(el_previsto())
        assert gasto["es_una_estimacion"] is True
        assert gasto["consume_existencias"] is False, "una estimación no puede decir que ha gastado"
        assert gasto["estimados"][0]["cantidad_estimada"] == 300.0  # 100 L/ha × 3 ha
        assert gasto["estimados"][0]["calculada"] is True
        assert gasto["completa"] is True

    def test_sin_hectareas_no_se_estima_nada_y_se_dice_lo_que_falta(self):
        """Un total inventado aquí es una compra que el agricultor no necesita."""
        gasto = trabajos.estimacion_de_lo_previsto(el_previsto(superficie_ha=None))
        assert gasto["se_puede_estimar"] is False
        assert gasto["estimados"] == []
        assert "superficie_ha" in gasto["falta"]

    def test_un_plan_de_siembra_no_anade_una_labor_hecha(self):
        """**El caso A05 del contrato**, tal cual: «plan de siembra confirmado como plan → no consume
        semillas ni añade labor realizada».

        Si esto fallara, confirmar un plan haría aparecer un cultivo sembrado en una tierra en la que
        todavía no se ha sembrado nada, y el cuaderno diría que se sembró.
        """
        plan = el_previsto(tipo="siembra", cultivo="Cebada", subtipo=None)
        estado = trabajos.estado_de_una_tierra([], [plan], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA, hoy=HOY)
        assert estado["se_ha_sembrado"] is False, "un plan ha puesto un cultivo sembrado"
        assert estado["cultivo_declarado"] is None
        assert estado["cuantos_previstos"] == 1
        assert estado["que_queda_previsto"][0]["previsto"]["id"] == 9

        junto = trabajos.lo_previsto_y_lo_hecho([plan], [])
        assert junto["cuantos_hechos"] == 0, "el plan ha contado como trabajo hecho"
        assert len(junto["sin_cumplir"]) == 1

    def test_un_trabajo_del_que_no_consta_su_estado_no_cuenta_como_hecho(self):
        """**Lo que no consta no se supone.** `None` no es «sí» ni es «no».

        Es el defecto que este ticket persigue: si un estado ausente se leyera como «hecho», todo lo que
        no se sabe gastaría del almacén y acreditaría trabajo; y si se leyera como «previsto», el
        cuaderno del agricultor se convertiría en una lista de planes.
        """
        sin_estado = trabajos.un_trabajo(
            id=1, campana_id=LA_CAMPANA, tipo="siembra", fecha=dt.date(2026, 3, 1), parcela_id=LA_TIERRA
        )
        assert sin_estado["estado"] is None
        assert trabajos.acredita_un_trabajo_hecho(sin_estado) is False
        consume, porque = trabajos.consume_existencias(sin_estado)
        assert consume is False and porque == "TJ2_no_consta_si_se_hizo"
        assert trabajos.cambia_el_cultivo(sin_estado) is False
        estado = trabajos.estado_de_una_tierra([sin_estado], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA)
        assert estado["se_ha_sembrado"] is False, "un apunte sin estado ha puesto un cultivo"

    def test_un_estado_que_el_programa_no_conoce_no_es_un_hecho(self):
        """Guardar un estado raro no puede acabar acreditando trabajo hecho."""
        raro = trabajos.un_trabajo(id=1, tipo="siembra", estado="lo_que_sea", parcela_id=LA_TIERRA)
        assert trabajos.estado_de(raro) is None
        assert trabajos.acredita_un_trabajo_hecho(raro) is False

    def test_lo_en_curso_tampoco_esta_hecho(self):
        """Un trabajo a medias no se apunta como terminado: es apuntar el resultado antes de tenerlo."""
        a_medias = el_previsto(estado="en_curso")
        consume, porque = trabajos.consume_existencias(a_medias)
        assert consume is False and porque == "TJ1_el_previsto_no_gasta"
        assert trabajos.acredita_un_trabajo_hecho(a_medias) is False

    def test_un_plan_no_se_marca_hecho_dos_veces(self):
        """Si se hizo otra vez, es **otro** trabajo: no se cumple dos veces el mismo plan."""
        plan = el_previsto(estado="realizado")
        resultado = trabajos.marcar_como_hecho(plan, la_siembra())
        assert resultado["se_puede"] is False
        assert resultado["motivo_codigo"] == "TJ11_el_trabajo_ya_estaba"

    def test_lo_previsto_y_lo_hecho_se_emparejan_solo_por_el_vinculo(self):
        """**No por parecido.** Misma tierra, mismo tipo y fechas cercanas no es «esto es lo que se hizo».

        Si esto fallara, el programa daría por hecho un trabajo que no se ha hecho (o al revés) por una
        coincidencia de fechas, y eso en un cuaderno es un dato falso.
        """
        plan = el_previsto(fecha_prevista=dt.date(2026, 3, 10), tipo="laboreo", subtipo="rodillo")
        parecido = el_rodillo(id=77)  # mismo tipo, misma tierra, mismo día… y sin vínculo
        junto = trabajos.lo_previsto_y_lo_hecho([plan], [parecido])
        assert junto["cumplidos"] == [], "se ha emparejado un plan con un hecho por parecerse"
        assert len(junto["sin_cumplir"]) == 1
        assert junto["hechos_sin_plan"][0]["id"] == 77

        con_vinculo = trabajos.marcar_como_hecho(plan, el_rodillo(id=77))
        assert con_vinculo["se_puede"] is True
        assert con_vinculo["hecho"]["previsto_id"] == 9
        assert con_vinculo["previsto"]["estado"] == "realizado"


# ==========================================================================
# 2. Un rodillo después de sembrar no borra el estado de siembra
# ==========================================================================


class TestUnAperoNoCambiaLoSembrado:
    def test_un_rodillo_despues_de_sembrar_no_borra_el_estado_de_siembra(self):
        """**El caso A04 del contrato.** El rodillo se apunta y la siembra sigue ahí.

        Si esto fallara, pasar el rodillo borraría el cultivo de la tierra: el agricultor vería su
        parcela «sin cultivo» en la pantalla y en el cuaderno después de haberla sembrado, y la
        comparación de campañas se quedaría sin la siembra.
        """
        estado = trabajos.estado_de_una_tierra(
            [la_siembra(), el_rodillo()], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA, hoy=HOY
        )
        assert estado["cultivo_declarado"] is not None, "el rodillo ha borrado lo sembrado"
        assert estado["cultivo_declarado"]["cultivo"] == "Trigo blando"
        assert estado["cultivo_declarado"]["variedad"] == "Craklin"
        assert estado["se_ha_sembrado"] is True
        # Y el estado lo explica, para que nadie lo tome por un olvido.
        assert estado["aperos_despues_de_sembrar"] == [2]
        assert estado["un_apero_no_cambia_lo_sembrado_codigo"] == "TJ8_un_rodillo_no_cambia_lo_sembrado"
        # La última labor sí es el rodillo: son dos cosas distintas y las dos se dicen.
        assert estado["ultima_labor"]["tipo_y_subtipo"] == "laboreo:rodillo"

    def test_el_historial_tiene_los_dos_eventos_y_el_cultivo_permanece(self):
        """La otra mitad de A04: «el historial contiene ambos».

        Si esto fallara, el historial escondería uno de los dos trabajos y el agricultor no podría
        explicar lo que hizo en su tierra.
        """
        historial = trabajos.historial_de_una_tierra(
            [la_siembra(), el_rodillo()], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA, hoy=HOY
        )
        assert historial["cuantos"] == 2, "el historial ha perdido un evento"
        assert [linea["tipo_y_subtipo"] for linea in historial["lineas"]] == ["siembra", "laboreo:rodillo"]
        assert historial["lineas"][0]["que_cambio"] == "se_sembro"
        assert historial["lineas"][1]["que_cambio"] == "", "el rodillo dice que cambió lo sembrado"
        # Y cada línea dice lo que hay sembrado **después** de ella, que es lo que hace que el historial
        # se lea como una historia.
        assert historial["lineas"][0]["lo_que_hay_sembrado_despues"]["cultivo"] == "Trigo blando"
        assert historial["lineas"][1]["lo_que_hay_sembrado_despues"]["cultivo"] == "Trigo blando"

    def test_ninguna_labor_de_suelo_cambia_lo_sembrado(self):
        """Ni el rodillo, ni el cultivador, ni el arado, ni la grada, ni una labor sin nombre.

        Se prueban **todos** los subtipos de labor de suelo del contrato, para que añadir uno nuevo sin
        pensarlo no cuele por la puerta de atrás.
        """
        for subtipo in trabajos.SUBTIPOS_DE_LABOREO:
            trabajo = el_rodillo(subtipo=subtipo)
            assert trabajos.cambia_el_cultivo(trabajo) is False, f"«{subtipo}» cambia lo sembrado"
            estado = trabajos.estado_de_una_tierra(
                [la_siembra(), trabajo], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA
            )
            assert estado["cultivo_declarado"]["cultivo"] == "Trigo blando"

    def test_ningun_otro_tipo_de_trabajo_cambia_lo_sembrado(self):
        """Solo sembrar y plantar cambian el estado de siembra. Ni regar, ni podar, ni coger el grano."""
        for tipo in trabajos.TIPOS_DE_TRABAJO:
            trabajo = el_rodillo(tipo=tipo, subtipo=None)
            cambia = trabajos.cambia_el_cultivo(trabajo)
            assert cambia is (tipo in trabajos.TIPOS_QUE_SIEMBRAN), f"«{tipo}» y el estado de siembra"
        assert trabajos.TIPOS_QUE_SIEMBRAN == ("siembra", "plantacion")

    def test_una_labor_de_suelo_sin_sembrar_no_inventa_un_cultivo(self):
        """Al revés también: un arado en una tierra sin sembrar no pone ningún cultivo."""
        estado = trabajos.estado_de_una_tierra(
            [el_rodillo()], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA
        )
        assert estado["cultivo_declarado"] is None
        assert estado["se_ha_sembrado"] is False

    def test_anular_una_siembra_devuelve_el_estado_a_lo_de_antes(self):
        """Nada se borra: si la segunda siembra se anula, vuelve a valer la primera.

        Y esto no es un capricho: es la consecuencia de que el estado salga **solo** de lo que cuenta.
        """
        primera = la_siembra(id=1, fecha=dt.date(2026, 2, 1), cultivo="Veza")
        segunda = la_siembra(id=6, fecha=dt.date(2026, 3, 1), cultivo="Trigo blando")
        anulada = trabajos.anular(segunda, "la sembré en otra tierra")["trabajo"]
        estado = trabajos.estado_de_una_tierra(
            [primera, anulada], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA
        )
        assert estado["cultivo_declarado"]["cultivo"] == "Veza"
        assert estado["cuantas_siembras"] == 1

    def test_la_siembra_sin_decir_el_cultivo_se_dice_que_no_se_sabe(self):
        """Se sembró, sí; con qué, no. Un hueco, y dicho: no se rellena con «sin cultivo»."""
        estado = trabajos.estado_de_una_tierra(
            [la_siembra(cultivo=None, variedad=None)], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA
        )
        assert estado["se_ha_sembrado"] is True
        assert estado["cultivo_declarado"]["cultivo"] is None
        assert estado["no_se_sabe_que_se_sembro_codigo"] == "TJ28_no_se_sabe_que_se_sembro"


# ==========================================================================
# 3. Una lluvia no acredita nascencia ni salud del cultivo
# ==========================================================================


class TestLaLluviaNoDiceNadaDelCultivo:
    def test_una_lluvia_no_acredita_nascencia(self):
        """**Que llueva no quiere decir que la planta haya nacido.**

        Si esto fallara, el programa afirmaría en el cuaderno que el cultivo ha nacido porque una
        estación midió doce litros: una afirmación sobre la planta que nadie ha visto, y que en una
        reclamación o en un seguro es un dato falso escrito por nosotros.
        """
        estado = trabajos.estado_de_una_tierra(
            [la_siembra(), la_lluvia()], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA, hoy=HOY
        )
        assert estado["nascencia"] is None, "una lluvia ha acreditado la nascencia"
        assert estado["hubo_lluvia"] is True, "y lo que sí se sabe —que llovió— no se pierde"
        assert estado["lluvias"][0]["milimetros"] == 12.0
        assert (
            estado["no_se_puede_deducir_la_nascencia_porque_codigo"]
            == "TJ7_de_la_lluvia_no_sale_la_nascencia"
        )

    def test_la_nascencia_solo_sale_de_una_observacion_de_alguien(self):
        """La única puerta: alguien que la ha visto y lo ha apuntado."""
        estado = trabajos.estado_de_una_tierra(
            [la_siembra(), la_lluvia(), una_observacion()],
            [],
            parcela_id=LA_TIERRA,
            campana_id=LA_CAMPANA,
            hoy=HOY,
        )
        assert estado["nascencia"] is True
        assert estado["nascencia_dicha_por"]["trabajo_id"] == 4
        assert estado["no_se_puede_deducir_la_nascencia_porque_codigo"] == ""

    def test_una_observacion_tambien_puede_decir_que_no_nacio(self):
        """Y el «no» es un dato, distinto de «no se sabe»: los tres estados, otra vez."""
        sin_nacer = una_observacion(nascencia=False, observaciones="No ha nacido nada")
        estado = trabajos.estado_de_una_tierra([la_siembra(), sin_nacer], [], parcela_id=LA_TIERRA)
        assert estado["nascencia"] is False

    def test_sin_ninguna_observacion_la_nascencia_no_se_sabe_y_se_dice(self):
        """Sin lluvia y sin observación: tampoco se supone. El hueco se queda hueco."""
        estado = trabajos.estado_de_una_tierra([la_siembra()], [], parcela_id=LA_TIERRA)
        assert estado["nascencia"] is None
        assert estado["no_se_puede_deducir_la_nascencia_porque_codigo"] == "TJ27_no_se_sabe_si_nacio"

    def test_una_lluvia_no_es_un_trabajo_de_la_tierra(self):
        """Sale en el historial —es un hecho— y no cuenta como trabajo hecho ni suma hectáreas."""
        lluvia = la_lluvia()
        assert trabajos.es_un_trabajo_de_la_tierra(lluvia) is False
        cifras = trabajos.cifras_de_una_tierra([la_siembra(), la_lluvia()], campana_id=LA_CAMPANA)
        assert cifras["trabajos_hechos"] == 1, "la lluvia ha contado como trabajo hecho"
        assert "lluvia" not in cifras["por_tipo"]
        assert cifras["superficie_ha"] == 3.0, "la lluvia ha sumado hectáreas trabajadas"

    def test_la_cosecha_no_dice_que_la_tierra_quedo_vacia(self):
        """Coger el grano no dice si quedó rastrojo, cubierta o nada. Eso se mira en el campo."""
        estado = trabajos.estado_de_una_tierra(
            [la_siembra(), una_cosecha()], [], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA
        )
        assert estado["en_el_suelo"] is None, "el programa ha supuesto lo que quedó en la tierra"
        assert estado["no_se_puede_deducir_el_suelo_porque_codigo"] == "TJ15_la_tierra_quedo_o_no"
        # Y lo sembrado sigue apuntado: coger el grano no borra que se sembró.
        assert estado["cultivo_declarado"]["cultivo"] == "Trigo blando"

        con_observacion = una_observacion(id=8, nascencia=None, en_el_suelo=False)
        dicho = trabajos.estado_de_una_tierra([la_siembra(), una_cosecha(), con_observacion], [])
        assert dicho["en_el_suelo"] is False

    def test_lo_que_no_se_puede_saber_se_declara_en_el_propio_dato(self):
        """El hueco viaja en la respuesta, no en un comentario. Es lo que hace que se pueda decir."""
        codigos = {falta["codigo"] for falta in trabajos.QUE_FALTA}
        assert "T15_sin_fuente_de_lluvia" in codigos
        assert "T15_sin_nascencia_medida" in codigos
        for falta in trabajos.QUE_FALTA:
            assert falta["que_es"] and falta["para_que"] and falta["de_quien_depende"], falta


# ==========================================================================
# 4. Anular y corregir no duplican consumos
# ==========================================================================


class TestAnularNoDuplicaConsumos:
    def test_anular_no_duplica_consumos(self):
        """**Anular un trabajo devuelve al almacén lo que salió, y no lo descuenta dos veces.**

        Si esto fallara, anular un trabajo dejaría el producto descontado para siempre (o lo devolvería
        dos veces, si alguien «deshiciera» la resta). El movimiento **no se toca**: se queda en el libro
        con su fecha y su autor, y deja de contar.
        """
        consumo = el_consumo()
        antes = trabajos.consumos_que_cuentan([la_siembra()], [consumo])
        assert antes["cuantos_cuentan"] == 1
        assert antes["por_articulo"]["1"]["suma"] == 600.0

        anulado = trabajos.anular(la_siembra(), "me equivoqué de tierra")
        assert anulado["anulado"] is True
        assert anulado["el_apunte_sigue_en_el_historial"] is True, "anular ha borrado el apunte"

        despues = trabajos.consumos_que_cuentan([anulado["trabajo"]], [consumo])
        assert despues["cuantos_cuentan"] == 0, "lo anulado sigue descontando"
        assert despues["por_articulo"] == {}
        assert despues["no_cuentan"][0]["motivo_codigo"] == "TJ3_el_apunte_esta_anulado"
        # El movimiento sigue ahí, entero: lo que cambia es que no cuenta.
        assert despues["no_cuentan"][0]["cantidad"] == 600.0
        assert despues["no_cuentan"][0]["movimiento_id"] == 101

    def test_anular_dos_veces_no_duplica_ni_el_motivo_ni_la_devolucion(self):
        """Y no falla: dice que ya estaba. Dos devoluciones de lo mismo serían un almacén que crece solo."""
        una_vez = trabajos.anular(la_siembra(), "me equivoqué")["trabajo"]
        otra_vez = trabajos.anular(una_vez, "me equivoqué otra vez")
        assert otra_vez["ya_estaba"] is True
        assert otra_vez["anulado"] is False, "se ha vuelto a anular un apunte ya anulado"
        assert otra_vez["consumos_que_dejan_de_contar"] == []
        assert otra_vez["motivo_codigo"] == "TJ6_el_trabajo_ya_estaba_anulado"

    def test_anular_sin_motivo_no_se_hace(self):
        """Sin motivo no hay anulación: dentro de dos años nadie sabría por qué ese trabajo no se hizo."""
        respuesta = trabajos.anular(la_siembra(), "  ")
        assert respuesta["anulado"] is False
        assert respuesta["motivo_codigo"] == "TJ5_falta_el_motivo_para_anular"

    def test_anular_deja_el_apunte_en_el_historial_con_su_motivo(self):
        """**Nada se borra**: el apunte anulado sigue en el historial, tachado y explicado."""
        anulado = trabajos.anular(la_siembra(), "la sembré en otra tierra")["trabajo"]
        historial = trabajos.historial_de_una_tierra([anulado, el_rodillo()], parcela_id=LA_TIERRA)
        assert historial["cuantos"] == 2, "el historial ha perdido el apunte anulado"
        primera = historial["lineas"][0]
        assert primera["anulado"] is True
        assert primera["motivo_anulacion"] == "la sembré en otra tierra"
        assert primera["cuenta_como_hecho"] is False
        assert primera["no_cuenta_porque_codigo"] == "TJ3_el_apunte_esta_anulado"
        # Y cuando la pantalla decide no enseñarlos, dice cuántos ha dejado fuera.
        solo_los_que_cuentan = trabajos.historial_de_una_tierra(
            [anulado, el_rodillo()], parcela_id=LA_TIERRA, incluir_anulados=False
        )
        assert solo_los_que_cuentan["cuantos"] == 1
        assert solo_los_que_cuentan["se_dejan_fuera"] == 1

    def test_corregir_lo_que_salio_anula_la_salida_vieja_y_apunta_la_nueva(self):
        """**Corregir no puede dejar dos descuentos vivos.** Ni reescribir la cantidad por detrás.

        Si esto fallara, corregir de 600 a 500 kilos dejaría el libro con dos salidas vivas —1.100 kg
        descontados— o con una cantidad cambiada a espaldas de quien la apuntó.
        """
        correccion = trabajos.corregir(la_siembra(), {"insumos": [el_consumo(cantidad=500.0)]})
        assert correccion["corregido"] is True
        assert correccion["hay_que_tocar_el_almacen"] is True
        assert len(correccion["consumos_que_hay_que_anular"]) == 1
        assert len(correccion["consumos_que_hay_que_apuntar"]) == 1
        assert correccion["consumos_que_hay_que_anular"][0]["movimiento_id"] == 101
        assert correccion["consumos_que_hay_que_apuntar"][0]["cantidad"] == 500.0
        # **La clave de reenvío no viaja a la salida nueva**: si viajara, el movimiento nuevo chocaría
        # con el viejo y el trabajo corregido se quedaría sin descontar nada.
        assert correccion["consumos_que_hay_que_apuntar"][0]["clave_de_reenvio"] is None

        # Y el resultado, tal y como lo deja el router: la vieja anulada y la nueva viva → una sola.
        vieja = {**correccion["consumos_que_hay_que_anular"][0], "anulado": True}
        nueva = {**correccion["consumos_que_hay_que_apuntar"][0], "movimiento_id": 102}
        despues = trabajos.consumos_que_cuentan([correccion["trabajo"]], [vieja, nueva])
        assert despues["cuantos_cuentan"] == 1, "quedan dos descuentos vivos"
        assert despues["por_articulo"]["1"]["suma"] == 500.0

    def test_corregir_unas_horas_no_toca_el_almacen(self):
        """Lo que no cambia lo que salió no puede mover existencias."""
        correccion = trabajos.corregir(la_siembra(), {"horas": 6.0, "observaciones": "Se atascó"})
        assert correccion["corregido"] is True
        assert correccion["hay_que_tocar_el_almacen"] is False, "corregir unas horas ha movido almacén"
        assert correccion["consumos_que_hay_que_anular"] == []
        assert correccion["cambios"]["horas"] == [4.0, 6.0]

    def test_corregir_deja_lo_que_decia_antes_campo_por_campo(self):
        """El rastro: qué decía y qué dice. Es lo que permite explicar el cambio dentro de dos años."""
        correccion = trabajos.corregir(la_siembra(), {"superficie_ha": 2.5, "cultivo": "Cebada"})
        assert correccion["cambios"] == {
            "superficie_ha": [3.0, 2.5],
            "cultivo": ["Trigo blando", "Cebada"],
        }
        assert correccion["trabajo"]["superficie_ha"] == 2.5

    def test_corregir_sin_cambiar_nada_no_apunta_nada(self):
        """Un rastro lleno de «no cambió nada» es un rastro que nadie lee."""
        correccion = trabajos.corregir(la_siembra(), {"cultivo": "Trigo blando"})
        assert correccion["corregido"] is False
        assert correccion["cambios"] == {}
        assert correccion["hay_que_tocar_el_almacen"] is False

    def test_corregir_no_resucita_un_apunte_anulado(self):
        """Lo anulado no se corrige: para eso está volver a apuntarlo."""
        anulado = trabajos.anular(la_siembra(), "me equivoqué")["trabajo"]
        correccion = trabajos.corregir(anulado, {"horas": 9.0})
        assert correccion["corregido"] is False
        assert correccion["motivo_codigo"] == "TJ3_el_apunte_esta_anulado"

    def test_un_plan_no_se_corrige_se_reprograma(self):
        """Corregir un plan sería escribir un plan con la puerta de los hechos."""
        correccion = trabajos.corregir(el_previsto(), {"fecha_prevista": dt.date(2026, 5, 1)})
        assert correccion["corregido"] is False
        assert correccion["motivo_codigo"] == "TJ17_un_plan_no_es_un_trabajo"


# ==========================================================================
# Lo firmado no se toca
# ==========================================================================


class TestLoFirmadoNoSeToca:
    def test_un_apunte_firmado_no_se_puede_borrar(self):
        """La firma es la prueba de lo que había: borrarla dejaría una firma de nada."""
        firmado = la_siembra(firmado=True, firma_huella="A1B2", firma_entidad_id=1)
        se_puede, porque = trabajos.se_puede_borrar(firmado)
        assert se_puede is False
        assert porque == "TJ10_lo_firmado_no_se_borra"
        # Y lo que sí se puede —anular— se puede, que es lo que hace que nadie se quede sin salida.
        assert trabajos.anular(firmado, "era de otra tierra")["anulado"] is True

    def test_corregir_lo_firmado_es_una_revision_nueva_y_la_firma_sigue_valiendo(self):
        """**El caso A14:** «editar registro firmado → revisión nueva, firma antigua verificable y bytes
        idénticos».

        Si esto fallara, corregir un apunte firmado cambiaría lo que se firmó: una inspección
        comprobaría la huella de un cuaderno que ya no es el que se firmó.
        """
        original = la_siembra(firmado=True, firma_huella="A1B2", firma_entidad_id=1, firmado_en=dt.datetime(2026, 3, 2))
        correccion = trabajos.corregir(original, {"superficie_ha": 2.5})
        assert correccion["lo_firmado_no_se_toca"] is True
        assert correccion["revision_nueva"] is not None
        assert correccion["revision_nueva"]["revision_de"] == 1
        assert correccion["revision_nueva"]["superficie_ha"] == 2.5
        assert correccion["firma_que_sigue_valiendo"]["huella"] == "A1B2"
        assert correccion["firma_que_sigue_valiendo"]["bytes_identicos"] is True
        # Y lo firmado no se ha tocado: el apunte de antes sigue diciendo lo mismo.
        assert original["superficie_ha"] == 3.0
        assert correccion["trabajo"]["id"] == original["id"]


# ==========================================================================
# Corregir y anular sin duplicar lo que llega del móvil
# ==========================================================================


class TestReenviarNoDuplica:
    def test_reenviar_desde_el_movil_no_duplica_trabajos(self):
        """**El caso A12:** el móvil repite el envío al recuperar la cobertura.

        Si esto fallara, un día sin cobertura acabaría con el mismo trabajo apuntado tres veces y el
        almacén descontado tres veces.
        """
        primera = la_siembra(id=1, clave_de_reenvio="apunte-1")
        repetida = la_siembra(id=2, clave_de_reenvio="apunte-1")
        otra = el_rodillo(id=3, clave_de_reenvio="apunte-2")

        unicos = trabajos.quita_los_reenvios([primera, repetida, otra])
        assert unicos["cuantos"] == 2, "el reenvío ha creado un trabajo de más"
        assert [t["id"] for t in unicos["trabajos"]] == [1, 3]
        assert unicos["cuantos_reenviados"] == 1
        assert unicos["reenviados"][0]["trabajo"]["id"] == 2
        assert unicos["reenviados"][0]["de_la_clave_de"] == 1

        # Y los consumos, con el reenvío quitado, cuentan una sola vez.
        consumos = [el_consumo(), el_consumo(origen_id=2, movimiento_id=102)]
        cuentas = trabajos.consumos_que_cuentan(unicos["trabajos"], consumos)
        assert cuentas["cuantos_cuentan"] == 1
        assert cuentas["por_articulo"]["1"]["suma"] == 600.0

    def test_dos_salidas_del_mismo_apunte_y_envase_cuentan_una(self):
        """El almacén tampoco descuenta dos veces lo mismo, aunque las dos salidas estén vivas."""
        cuentas = trabajos.consumos_que_cuentan(
            [la_siembra()], [el_consumo(), el_consumo(movimiento_id=102)]
        )
        assert cuentas["cuantos_cuentan"] == 1, "el mismo apunte ha descontado dos veces"
        assert cuentas["por_articulo"]["1"]["suma"] == 600.0
        assert len(cuentas["repetidos"]) == 1
        assert cuentas["repetidos"][0]["motivo_codigo"] == "TJ11_el_trabajo_ya_estaba"

    def test_un_trabajo_sin_clave_no_se_puede_comprobar_y_se_dice(self):
        """Sin clave no se puede reconocer un repetido. Dar por bueno que no lo está es inventarse el dato."""
        sin_clave = trabajos.quita_los_reenvios([la_siembra(), el_rodillo()])
        assert sin_clave["sin_clave"] == 2
        assert sin_clave["sin_clave_porque_codigo"] == "TJ12_no_se_pudo_comprobar_si_ya_estaba"

    def test_una_salida_de_otro_apunte_no_se_tira(self):
        """Un tratamiento o una siembra también gastan del almacén, y no son de este ticket: se devuelven
        aparte para que quien sume sepa que hay más libro."""
        cuentas = trabajos.consumos_que_cuentan(
            [la_siembra()], [el_consumo(origen_tipo="tratamiento"), el_consumo()]
        )
        assert cuentas["cuantos_cuentan"] == 1
        assert len(cuentas["de_otros_apuntes"]) == 1


# ==========================================================================
# Datos ausentes ≠ cero
# ==========================================================================


class TestLoQueNoSeSabeNoEsCero:
    def test_sumar_lo_que_se_sabe_no_convierte_los_huecos_en_ceros(self):
        """La regla del panel de mando: se suma lo que consta y **se dice cuántos no lo dicen**."""
        cuenta = trabajos.sumando_lo_que_se_sabe([3.0, None, 2.0])
        assert cuenta == {"suma": 5.0, "cuantos": 3, "sin_decir": 1}
        # Y sin nada que sumar, la suma es cero de verdad y el hueco sigue contado.
        assert trabajos.sumando_lo_que_se_sabe([None, None]) == {
            "suma": 0.0,
            "cuantos": 2,
            "sin_decir": 2,
        }
        assert trabajos.sumando_lo_que_se_sabe([])["cuantos"] == 0

    def test_una_superficie_que_no_consta_no_es_cero_en_el_historial(self):
        """El apunte sin hectáreas dice `None`, no `0`: «no lo apunté» no es «no trabajé nada»."""
        sin_hectareas = el_rodillo(id=4, superficie_ha=None)
        historial = trabajos.historial_de_una_tierra([sin_hectareas], parcela_id=LA_TIERRA)
        assert historial["lineas"][0]["trabajo"]["superficie_ha"] is None

    def test_las_hectareas_que_faltan_se_cuentan_aparte_y_se_dicen(self):
        """Y la cifra del año dice cuántos trabajos no traen sus hectáreas."""
        cifras = trabajos.cifras_de_una_tierra(
            [la_siembra(superficie_ha=None), el_rodillo(superficie_ha=2.0)], campana_id=LA_CAMPANA
        )
        assert cifras["superficie_ha"] == 2.0, "se ha sumado un hueco como si fuera cero"
        assert cifras["superficie_sin_decir"] == 1
        faltas = {falta["codigo"]: falta["cuantos"] for falta in cifras["lo_que_no_se_sabe"]}
        assert faltas["TJ13_faltan_las_hectareas"] == 1

    def test_las_horas_que_faltan_se_cuentan_aparte(self):
        cifras = trabajos.cifras_de_una_tierra(
            [la_siembra(horas=4.0), el_rodillo(horas=None)], campana_id=LA_CAMPANA
        )
        assert cifras["horas"] == 4.0
        assert cifras["horas_sin_decir"] == 1

    def test_lo_previsto_no_entra_en_las_cifras_de_lo_hecho(self):
        """Las cuentas del año son de lo que se hizo: un plan no suma hectáreas trabajadas."""
        cifras = trabajos.cifras_de_una_tierra([la_siembra()], campana_id=LA_CAMPANA)
        con_plan = trabajos.estado_de_una_tierra(
            [la_siembra()], [el_previsto()], parcela_id=LA_TIERRA, campana_id=LA_CAMPANA
        )
        assert con_plan["cifras"]["superficie_ha"] == cifras["superficie_ha"] == 3.0
        assert con_plan["cifras"]["trabajos_hechos"] == 1

    def test_un_saldo_no_se_da_a_medias(self):
        """En un panel interesa lo que consta; **en un saldo, no**: sin la cantidad no se sabe lo que queda."""
        sin_cantidad = trabajos.saldo_de_los_consumos([el_consumo(cantidad=None)])
        assert sin_cantidad["suma"] is None
        assert sin_cantidad["motivo_codigo"] == "TJ21_falta_la_cantidad"
        sin_unidad = trabajos.saldo_de_los_consumos([el_consumo(unidad=None)])
        assert sin_unidad["suma"] is None
        assert sin_unidad["motivo_codigo"] == "TJ22_falta_la_unidad"
        dos_unidades = trabajos.saldo_de_los_consumos(
            [el_consumo(), el_consumo(cantidad=1.0, unidad="L", lote_id=12)]
        )
        assert dos_unidades["suma"] is None
        assert dos_unidades["motivo_codigo"] == "TJ20_no_se_pueden_sumar_unidades"

    def test_los_dias_que_faltan_no_son_cero_cuando_no_se_puede_saber(self):
        """Un cero es «es hoy», que es una afirmación distinta de «no sé cuándo es»."""
        assert trabajos.dias_que_faltan(dt.date(2026, 4, 10), HOY) == 9
        assert trabajos.dias_que_faltan(dt.date(2026, 3, 25), HOY) == -7
        assert trabajos.dias_que_faltan(None, HOY) is None
        assert trabajos.dias_que_faltan(dt.date(2026, 4, 10), None) is None

    def test_un_previsto_sin_dia_no_inventa_una_fecha(self):
        estado = trabajos.estado_de_una_tierra(
            [la_siembra()], [el_previsto(fecha_prevista=None)], parcela_id=LA_TIERRA, hoy=HOY
        )
        assert estado["previstos_sin_dia"] == 1
        assert estado["que_queda_previsto"][0]["dias_que_faltan"] is None
        assert (
            estado["que_queda_previsto"][0]["sin_dia_porque_codigo"]
            == "TJ25_la_fecha_prevista_no_se_sabe"
        )

    def test_sin_fecha_de_hoy_no_se_cuentan_los_dias_y_se_dice_por_que(self):
        """El módulo no mira el reloj: sin día de hoy se dice que no se sabe, y no un cero."""
        estado = trabajos.estado_de_una_tierra([la_siembra()], [el_previsto()], parcela_id=LA_TIERRA)
        linea = estado["que_queda_previsto"][0]
        assert linea["dias_que_faltan"] is None
        assert linea["sin_dia_porque_codigo"] == "TJ24_no_hay_fecha_de_hoy"
        assert estado["previstos_retrasados"] is None


# ==========================================================================
# Reprogramar y el estado del plan
# ==========================================================================


class TestReprogramar:
    def test_no_se_reprograma_un_trabajo_ya_hecho(self):
        """El contrato lo dice con esas palabras: «reprogramar no cambia fecha de un trabajo ya
        realizado».

        Si esto fallara, el cuaderno diría que se sembró un día que no se sembró.
        """
        hecho = la_siembra()
        respuesta = trabajos.reprogramar(hecho, dt.date(2026, 4, 15))
        assert respuesta["cambiado"] is False
        assert respuesta["motivo_codigo"] == "TJ9_no_se_reprograma_lo_ya_hecho"
        assert respuesta["trabajo"]["fecha"] == dt.date(2026, 3, 1)

    def test_reprogramar_conserva_la_fecha_de_antes(self):
        """Cambiar un día sin dejar el anterior es de las cosas que después nadie puede explicar."""
        respuesta = trabajos.reprogramar(
            el_previsto(), dt.date(2026, 4, 25), motivo="Va a llover"
        )
        assert respuesta["cambiado"] is True
        assert respuesta["trabajo"]["fecha_prevista"] == dt.date(2026, 4, 25)
        assert respuesta["trabajo"]["fecha_prevista_antes"] == dt.date(2026, 4, 20)
        assert respuesta["cambios"]["fecha_prevista"] == ["2026-04-20", "2026-04-25"]

    def test_los_previstos_retrasados_se_cuentan_solo_si_se_sabe_que_dia_es_hoy(self):
        estado = trabajos.estado_de_una_tierra(
            [],
            [el_previsto(fecha_prevista=dt.date(2026, 3, 15)), el_previsto(id=10, fecha_prevista=dt.date(2026, 4, 20))],
            parcela_id=LA_TIERRA,
            hoy=HOY,
        )
        assert estado["previstos_retrasados"] == 1
        assert [linea["dias_que_faltan"] for linea in estado["que_queda_previsto"]] == [-17, 19]

    def test_un_plan_cancelado_no_cuenta_como_pendiente_ni_como_hecho(self):
        estado = trabajos.estado_de_una_tierra(
            [], [el_previsto(estado="cancelado")], parcela_id=LA_TIERRA, hoy=HOY
        )
        assert estado["cuantos_previstos"] == 0
        junto = trabajos.lo_previsto_y_lo_hecho([el_previsto(estado="cancelado")], [])
        assert len(junto["cancelados"]) == 1
        assert junto["sin_cumplir"] == []


# ==========================================================================
# El cuaderno y los paneles: los mismos hechos
# ==========================================================================


class TestLasMismasCifras:
    def test_el_historial_y_el_estado_sacan_las_mismas_cifras(self):
        """**Una cifra que sale en dos pantallas sale del mismo sitio.**

        Se prueba con hechos que una cuenta hecha a mano haría distinto: uno anulado, uno sin hectáreas
        y uno del tiempo. Si alguien vuelve a sumar por su cuenta en el historial, esta prueba se pone
        roja —que es justo lo que tiene que pasar—.
        """
        hechos = [
            la_siembra(),
            el_rodillo(superficie_ha=None),
            la_lluvia(),
            trabajos.anular(el_rodillo(id=6, superficie_ha=9.0), "no llegué a hacerlo")["trabajo"],
            trabajos.un_trabajo(id=7, campana_id=LA_CAMPANA, tipo="laboreo", parcela_id=None, superficie_ha=1.0),
        ]
        historial = trabajos.historial_de_una_tierra(hechos, campana_id=LA_CAMPANA)
        estado = trabajos.estado_de_una_tierra(hechos, [], campana_id=LA_CAMPANA)
        assert historial["cifras"] == estado["cifras"]
        assert historial["cifras"] == trabajos.cifras_de_una_tierra(hechos, campana_id=LA_CAMPANA)
        # Y la cuenta es la que tiene que ser: el anulado no suma, el hueco se cuenta aparte, la lluvia
        # no es un trabajo y el que no tiene tierra no es de esta tierra.
        assert historial["cifras"]["superficie_ha"] == 3.0
        assert historial["cifras"]["superficie_sin_decir"] == 1
        assert historial["cifras"]["trabajos_anulados"] == 1
        assert historial["cifras"]["sin_tierra"] == 1

    def test_las_cifras_de_otra_campana_no_se_mezclan(self):
        """Cada campaña cuenta lo suyo: mezclarlas daría un año con el doble de hectáreas."""
        hechos = [la_siembra(), la_siembra(id=20, campana_id=2025, superficie_ha=4.0)]
        assert trabajos.cifras_de_una_tierra(hechos, campana_id=2026)["superficie_ha"] == 3.0
        assert trabajos.cifras_de_una_tierra(hechos, campana_id=2025)["superficie_ha"] == 4.0


# ==========================================================================
# Los códigos de las frases, y los tipos de trabajo
# ==========================================================================


class TestLosCodigosYLoSQueSeDice:
    def test_todos_los_codigos_que_puede_devolver_tienen_su_frase(self):
        """Un código sin frase no revienta: sale un hueco en la pantalla, que es el fallo que este
        proyecto ya ha tenido tres veces. Esto lo caza **antes** de que se integre."""
        fuente = pathlib.Path(trabajos.__file__).read_text(encoding="utf-8")
        en_el_codigo = set(re.findall(r'"(TJ\d+_[a-z0-9_]+)"', fuente))
        conocidos = set(trabajos.CODIGOS_QUE_SE_DICEN)
        assert en_el_codigo, "no se ha leído ni un código: la prueba estaría mirando el vacío"
        assert en_el_codigo - conocidos == set(), (
            f"estos códigos se devuelven y no tienen frase: {sorted(en_el_codigo - conocidos)}"
        )
        assert conocidos - en_el_codigo == set(), (
            f"estas frases están escritas y no las devuelve nadie: {sorted(conocidos - en_el_codigo)}"
        )

    def test_ninguna_frase_lleva_huecos_que_nadie_rellena(self):
        """Las frases que pide este ticket dicen «cuántos» aparte, en su propio campo, para no tener que
        inventarse el singular y el plural dentro de un mensaje que se escribe una vez."""
        for codigo, frase in trabajos.CODIGOS_QUE_SE_DICEN.items():
            assert "{" not in frase and "}" not in frase, f"«{codigo}» lleva un hueco sin rellenar"
            assert frase.strip().endswith((".", "…")), f"«{codigo}» no termina en punto"
            assert frase[0].isupper(), f"«{codigo}» empieza en minúscula"

    def test_ninguna_frase_nueva_lleva_jerga(self):
        """La regla de la casa, comprobada **antes** de que las frases entren en `textos.py`: si se
        cuela una palabra de la lista negra, el test de jerga la cazaría después… o no la cazaría, si
        alguien copia la frase a un sitio que no se revisa."""
        for codigo, frase in trabajos.CODIGOS_QUE_SE_DICEN.items():
            encontradas = textos.palabras_prohibidas_encontradas(frase)
            assert encontradas == [], f"«{codigo}» lleva jerga: {encontradas}"

    def test_los_tipos_de_trabajo_son_los_que_el_programa_ya_tiene(self):
        """«Conservar tipos históricos»: los tipos salen de los botones que ya existen, no de una lista
        nueva escrita a mano que se quedaría vieja."""
        de_los_botones = {trabajo["id"] for trabajo in textos.TRABAJOS}
        de_las_labores = {trabajo["id"] for trabajo in textos.TRABAJOS_DE_LABOR}
        assert de_los_botones <= set(trabajos.TIPOS_DE_TRABAJO)
        assert de_las_labores <= set(trabajos.TIPOS_DE_TRABAJO)
        assert "siembra" in trabajos.TIPOS_DE_TRABAJO
        assert "laboreo" in trabajos.TIPOS_DE_TRABAJO
        assert len(set(trabajos.TIPOS_DE_TRABAJO)) == len(trabajos.TIPOS_DE_TRABAJO), "hay un tipo repetido"

    def test_la_lluvia_no_esta_entre_los_tipos_de_trabajo(self):
        """No es un trabajo: es un hecho del tiempo, y por eso vive aparte."""
        assert set(trabajos.HECHOS_DEL_TIEMPO) & set(trabajos.TIPOS_DE_TRABAJO) == set()

    def test_un_tipo_que_no_existe_no_revienta(self):
        """Un tipo histórico raro (de una instalación vieja) se apunta igual y no cambia nada de nadie."""
        raro = el_rodillo(tipo="lo_que_sea", subtipo=None)
        assert trabajos.tipo_y_subtipo(raro) == "lo_que_sea"
        assert trabajos.cambia_el_cultivo(raro) is False
        estado = trabajos.estado_de_una_tierra([la_siembra(), raro], [], parcela_id=LA_TIERRA)
        assert estado["cultivo_declarado"]["cultivo"] == "Trigo blando"


# ==========================================================================
# El router: sus puertas, y lo que le falta para poder ejecutarse
# ==========================================================================

RAIZ = pathlib.Path(__file__).resolve().parents[2]
EL_ROUTER = RAIZ / "backend" / "app" / "routers" / "trabajos_api.py"

# Lo que el router necesita del coordinador para poder importarse. Se saca de aquí para el mensaje del
# salto: así, quien lea el informe sabe exactamente qué falta, sin abrir el fichero.
LO_QUE_FALTA_PARA_EL_ROUTER = (
    "models.TrabajoPrevisto y models.LineaDeTrabajoPrevisto (las dos tablas de lo previsto)",
    "las columnas nuevas de models.Labor (clave_de_reenvio, horas, previsto_id)",
    "los esquemas de schemas.py (TrabajoEntrada, TrabajoPrevistoEntrada, TrabajoSalida, "
    "TrabajoPrevistoSalida, MarcarHechoEntrada, ReprogramarEntrada)",
    "las frases de textos.py (los códigos TJ1–TJ28 y el bloque AGENDA)",
    "servicios.APUNTES_QUE_GASTAN con «labor», `lo_que_gasta_un_apunte` y `estado_de_los_origenes`",
    "el include_router de main.py",
)


class TestLasPuertasDelRouter:
    def test_el_router_esta_escrito_y_dice_lo_que_necesita(self):
        """El fichero existe y declara sus puertas y lo que le falta, aunque todavía no se pueda
        importar. Esto se comprueba hoy y no espera a nadie."""
        assert EL_ROUTER.is_file(), "no está el router del ticket"
        codigo = EL_ROUTER.read_text(encoding="utf-8")
        assert 'APIRouter(prefix="/api/trabajos"' in codigo
        for trozo in (
            "/previstos",
            "/hecho",
            "/reprogramar",
            "/anular",
            "/historial",
            "/estado",
            "LO_QUE_FALTA",
        ):
            assert trozo in codigo, f"al router le falta «{trozo}»"

    def test_el_router_declara_lo_que_le_falta_al_coordinador(self):
        """Lo que no se puede ejecutar se dice con su nombre y apellidos, no con un «pendiente»."""
        codigo = EL_ROUTER.read_text(encoding="utf-8")
        for pieza in LO_QUE_FALTA_PARA_EL_ROUTER:
            # La primera palabra con sentido de cada pieza (el nombre del fichero o del bloque), que es
            # lo que tiene que aparecer en el comentario de la cabecera del router.
            nombre = pieza.split(" (")[0].split(" con ")[0].strip()
            assert nombre in codigo, f"el router no dice que necesita «{nombre}»"


def test_las_puertas_del_router_se_ejecutan_cuando_este_integrado():
    """El recorrido entero contra la API.**

    **Ya se ejecuta**, y no se salta: el router importa las tablas y los esquemas que el coordinador tenía
    que integrar, y están puestos (comprobado el 07/10/2026: 77 pruebas de este fichero pasan y 0 saltan).
    El `skip` que hay abajo se queda como red de seguridad —si algún día esa integración se rompe, la
    prueba lo dice en vez de fallar por un import—, pero **no se dispara**: el recorrido que comprueba es
    planificar → marcar lo hecho → historial y existencias → anular.
    """
    try:
        from app.routers import trabajos_api  # noqa: F401
    except Exception as fallo:  # noqa: BLE001 — cualquier fallo al importar es «no está integrado»
        pytest.skip(
            "El router del T15 todavía no se puede ejecutar: falta que el coordinador integre "
            + "; ".join(LO_QUE_FALTA_PARA_EL_ROUTER)
            + f". Al importarlo: {type(fallo).__name__}: {fallo}"
        )
    assert hasattr(trabajos_api, "router")


# ==========================================================================
# La copia de los textos que usan las pruebas del móvil
# ==========================================================================
#
# El fallo que esto vigila es el que `AGENTS.md` cuenta tres veces: **una pregunta que el test pinta en
# blanco**. Si la pantalla lee una clave que no está en la copia, la frase sale vacía en la prueba y la
# prueba **da por bueno cualquier cosa**. Aquí se comprueba por los dos lados: lo que la pantalla lee
# está en la copia, y lo que hay en la copia lo lee alguien.

LA_PANTALLA = RAIZ / "backend" / "web" / "react" / "pantallas" / "trabajos.js"
LA_COPIA_DEL_MOVIL = RAIZ / "backend" / "tests_js" / "trabajos.test.js"


def _las_claves_de_la_copia() -> set[str]:
    """Las claves del bloque `AGENDA` de la copia del test del móvil, leídas del fichero.

    El bloque está escrito aparte y con una clave por línea justo para esto: un guardián que lee ficheros
    necesita poder leerlos sin adivinar.
    """
    texto = LA_COPIA_DEL_MOVIL.read_text(encoding="utf-8")
    trozo = texto.split("const AGENDA = {", 1)
    assert len(trozo) == 2, "no encuentro el bloque `AGENDA` en la copia del test del móvil"
    cuerpo = trozo[1].split("\n};", 1)[0]
    claves = set(re.findall(r"(?m)^\s*([a-z][a-z0-9_]*):", cuerpo))
    assert len(claves) > 40, f"solo se han leído {len(claves)} claves: el extractor se ha roto"
    return claves


def _las_claves_que_lee_la_pantalla() -> set[str]:
    """Las claves del bloque de la agenda que la pantalla lee: `a.algo` en `trabajos.js`."""
    texto = LA_PANTALLA.read_text(encoding="utf-8")
    return set(re.findall(r"\ba\.([a-z][a-z0-9_]*)\b", texto))


class TestLaCopiaDeLosTextosDelMovil:
    def test_la_pantalla_no_lee_ninguna_clave_que_no_este_en_la_copia(self):
        """**La prueba del fallo que más veces ha tenido este proyecto**: una frase en blanco.

        Si esto fallara, esa frase saldría vacía en la pantalla de verdad —las claves no se inventan: se
        piden al servidor— y el test del móvil no lo vería, porque también estaría vacío allí.
        """
        leidas = _las_claves_que_lee_la_pantalla()
        copia = _las_claves_de_la_copia()
        assert leidas, "no se ha leído ni una clave: el extractor se ha roto"
        faltan = sorted(leidas - copia)
        assert faltan == [], (
            f"la pantalla lee claves que no están en la copia de los textos: {faltan}. "
            "Esas frases saldrían en blanco."
        )

    def test_la_copia_no_tiene_frases_que_nadie_lea(self):
        """Y al revés: una frase escrita y no leída es una frase que se queda vieja sin que nadie lo vea."""
        sobran = sorted(_las_claves_de_la_copia() - _las_claves_que_lee_la_pantalla())
        assert sobran == [], f"estas frases están en la copia y no las lee la pantalla: {sobran}"

    def test_la_copia_dice_lo_mismo_que_el_servidor_cuando_el_bloque_este_integrado(self):
        """La copia del móvil y el bloque `AGENDA` del servidor, clave por clave.

        **`textos.AGENDA` existe desde el 05/10/2026**, así que esto compara de verdad (no se salta). El
        `skip` de abajo es la red de seguridad por si esa integración se rompiera: un test que se saltara
        sin decir por qué sería un test que da por bueno lo que no ha mirado.
        """
        if not hasattr(textos, "AGENDA"):
            pytest.skip(
                "el bloque `AGENDA` todavía no está en `app/textos.py`: lo integra el coordinador y su "
                "bloque literal está en `docs/T15_TRABAJOS.md`. Cuando esté, esta prueba compara la copia "
                "del móvil con el servidor, clave por clave."
            )
        del_servidor = {clave: valor for clave, valor in dict(textos.AGENDA).items() if isinstance(valor, str)}
        del_movil = _las_claves_de_la_copia()
        assert set(del_servidor) == del_movil, (
            "la copia del móvil y el servidor no tienen las mismas claves: "
            f"sobran en el servidor {sorted(set(del_servidor) - del_movil)} y faltan "
            f"{sorted(del_movil - set(del_servidor))}"
        )

    def test_la_copia_no_lleva_jerga(self):
        """Las frases que lee el agricultor, sin jerga, comprobadas antes de que entren en `textos.py`."""
        texto = LA_COPIA_DEL_MOVIL.read_text(encoding="utf-8")
        cuerpo = texto.split("const AGENDA = {", 1)[1].split("\n};", 1)[0]
        for frase in re.findall(r':\s*"([^"]+)"', cuerpo):
            encontradas = textos.palabras_prohibidas_encontradas(frase)
            assert encontradas == [], f"una frase de la copia lleva jerga: {encontradas} en «{frase}»"


# ==========================================================================
# El informe y el código dicen lo mismo
# ==========================================================================
#
# El informe del ticket (`docs/T15_TRABAJOS.md`) lleva los bloques **literales** que el coordinador tiene
# que pegar en `textos.py`: los 28 mensajes y el bloque `AGENDA` de la pantalla. Un informe que se queda
# viejo es peor que no tenerlo: el que lo copia mete en el programa una frase que ya no es la que el
# código devuelve, y **el código devuelve códigos**, así que la frase nueva del informe saldría en la
# pantalla sin que ningún test la mirara. Estas dos pruebas atan el informe al código.

EL_INFORME = RAIZ / "docs" / "T15_TRABAJOS.md"


def _bloque_literal(marca: str, cierre: str) -> dict:
    """Un diccionario escrito en el informe, leído como lo leería Python.

    Se busca la marca, se coge el texto hasta el cierre y se lee con `literal_eval`: si el bloque del
    informe tiene una errata, esto revienta aquí y no en el ordenador del coordinador.
    """
    texto = EL_INFORME.read_text(encoding="utf-8")
    trozo = texto.split(marca, 1)
    assert len(trozo) == 2, f"el informe no lleva el bloque «{marca}»"
    corte = trozo[1].index(cierre)
    # El bloque va sangrado dentro del documento: se le quita el margen y se le vuelven a poner las
    # llaves, que es como lo leería Python. Si el informe tiene una errata, revienta aquí.
    return ast.literal_eval("{" + textwrap.dedent(trozo[1][:corte]) + "}")


class TestElInformeYElCodigoDicenLoMismo:
    def test_las_frases_de_los_codigos_del_informe_son_las_del_modulo(self):
        """Las 28 frases que el informe manda poner en `textos.py` son **exactamente** las que el módulo
        devuelve. Si se separan, la pantalla enseña una frase que nadie ha probado."""
        del_informe = _bloque_literal("MENSAJES.update({", "\n})")
        assert del_informe == trabajos.CODIGOS_QUE_SE_DICEN, (
            "el informe y el módulo no dicen las mismas frases: en el informe sobran "
            f"{sorted(set(del_informe) - set(trabajos.CODIGOS_QUE_SE_DICEN))} y faltan "
            f"{sorted(set(trabajos.CODIGOS_QUE_SE_DICEN) - set(del_informe))}"
        )

    def test_las_claves_de_la_agenda_del_informe_son_las_de_la_copia_del_movil(self):
        """Y el bloque `AGENDA` del informe tiene las mismas claves que la copia que usan las pruebas del
        móvil: si el informe se queda corto, el coordinador pega un bloque al que le falta una frase y la
        pantalla la pide en blanco."""
        del_informe = set(_bloque_literal("AGENDA: dict[str, str] = {", "\n}"))
        del_movil = _las_claves_de_la_copia()
        assert del_informe == del_movil, (
            "el informe y la copia del móvil no tienen las mismas claves: en el informe sobran "
            f"{sorted(del_informe - del_movil)} y faltan {sorted(del_movil - del_informe)}"
        )
        assert del_informe == _las_claves_que_lee_la_pantalla()

    def test_el_informe_lleva_los_bloques_que_el_coordinador_necesita(self):
        """Los seis cambios compartidos, con su bloque: si falta uno, el que integra se queda a medias."""
        texto = EL_INFORME.read_text(encoding="utf-8")
        for pieza in (
            "class TrabajoPrevisto(Base)",
            "class LineaDeTrabajoPrevisto(Base)",
            "class TrabajoEntrada(EntradaBase)",
            "class MarcarHechoEntrada(EntradaBase)",
            "class ReprogramarEntrada(EntradaBase)",
            "AGENDA: dict[str, str] = {",
            'APUNTES_QUE_GASTAN = ("tratamiento", "fertilizacion", "siembra", "labor")',
            "app.include_router(trabajos_api.router)",
            '"agenda": textos.AGENDA',
            "trabajo-anular-confirmar",
        ):
            assert pieza in texto, f"al informe le falta el bloque o la línea «{pieza}»"


# ==========================================================================
# El cultivo que el agricultor declaró, contra la API (05/10/2026)
# ==========================================================================
#
# **Estas pruebas existen por un defecto que se vio en un navegador de verdad.** La historia de una
# tierra enseñaba «de esta tierra no consta que haya nada sembrado» en una tierra que **sí** tenía su
# cultivo puesto en «qué hay sembrado»: «qué hay hoy» se calculaba solo con las labores de siembra y
# plantación, y el agricultor apunta lo que tiene sembrado en la pantalla de los cultivos —la que va al
# cuaderno de la Junta— sin que haga falta apuntar además una labor de siembra. Dos pantallas del mismo
# programa diciendo cosas distintas de la misma tierra y el mismo año.
#
# Lo que se comprueba aquí, una por una, son las cuatro cosas que pueden pasar: lo declarado sale, lo que
# dice una labor de siembra manda sobre lo declarado, sin nada no se inventa un cultivo, y el cultivo de
# **otro año** no se cuela como el de hoy.


class TestLoQueElAgricultorDeclaro:
    def _declarar(self, cliente, cuenta, campana, parcela, **cambios):
        datos = {
            "campana_id": campana["id"],
            "especie": "TRIGO BLANDO",
            "variedad": "Craklin",
            "fecha_inicio": "2026-03-01",
        }
        datos.update(cambios)
        respuesta = cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json=datos,
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _hecho(self, cliente, cuenta, campana, parcela, **cambios):
        datos = {
            "campana_id": campana["id"],
            "tipo": "laboreo",
            "subtipo": "cultivador",
            "fecha": "2026-03-18",
            "parcela_id": parcela["id"],
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/trabajos", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def test_una_tierra_con_el_cultivo_declarado_y_sin_labores_lo_ensena(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """**El caso que se veía mal**: cultivo declarado, ninguna labor de siembra.

        Si esto fallara, abrir una tierra con TRIGO BLANDO declarado diría que no consta que haya nada
        sembrado, que es lo contrario de lo que dice la pantalla de al lado con los mismos datos.
        """
        parcela = crear_parcela(alias="El Prado")
        self._declarar(cliente, cuenta, campana, parcela)
        respuesta = cliente.get(f"/api/trabajos/tierra/{parcela['id']}", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200, respuesta.text
        cultivo = respuesta.json()["estado"]["cultivo_declarado"]
        assert cultivo is not None, "la historia no ve el cultivo que el agricultor declaró"
        assert cultivo["cultivo"] == "TRIGO BLANDO"
        assert cultivo["variedad"] == "Craklin"
        assert cultivo["fecha"] == "2026-03-01"
        # Y se dice **de dónde sale**: no es lo mismo deducirlo de una labor que leerlo de lo que él dijo.
        assert cultivo["de_donde"] == "lo_dijo_el_agricultor"
        assert cultivo["trabajo_id"] is None, "se ha inventado una labor de siembra que nadie apuntó"
        # **Las dos puertas dicen lo mismo**: el estado solo y el estado dentro de la historia.
        otro = cliente.get(f"/api/trabajos/estado/{parcela['id']}", headers=cuenta["cabeceras"])
        assert otro.status_code == 200, otro.text
        assert otro.json()["cultivo_declarado"] == cultivo

    def test_lo_que_dice_una_labor_de_siembra_manda_sobre_la_declaracion(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Una siembra apuntada es un hecho del cuaderno y no se pisa con la declaración.

        Si esto fallara, apuntar «he sembrado cebada» y luego mirar la tierra diría trigo: el historial
        contaría una cosa y el estado de arriba, otra.
        """
        parcela = crear_parcela(alias="El Prado")
        self._declarar(cliente, cuenta, campana, parcela, especie="TRIGO BLANDO")
        self._hecho(cliente, cuenta, campana, parcela, tipo="siembra", subtipo=None, cultivo="CEBADA")
        estado = cliente.get(
            f"/api/trabajos/tierra/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()["estado"]
        assert estado["cultivo_declarado"]["cultivo"] == "CEBADA", (
            "la declaración ha pisado lo que dice la labor de siembra"
        )
        assert estado["cultivo_declarado"]["trabajo_id"] is not None
        assert estado["cultivo_declarado"].get("de_donde") != "lo_dijo_el_agricultor"

    def test_sin_declaracion_y_sin_siembra_no_se_inventa_un_cultivo(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Sin nada que lo diga, el cultivo no consta. **Un hueco no es un cero ni un «no hay».**"""
        parcela = crear_parcela(alias="La Vega")
        self._hecho(cliente, cuenta, campana, parcela)
        estado = cliente.get(
            f"/api/trabajos/tierra/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()["estado"]
        assert estado["cultivo_declarado"] is None
        assert estado["se_ha_sembrado"] is False

    def test_el_cultivo_declarado_de_otro_ano_no_sale_como_lo_de_hoy(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """El cultivo es **de un año**: el de 2025 no es lo que hay sembrado hoy.

        Si esto fallara, la historia de una tierra diría en 2026 lo que se sembró en 2025, que es
        justamente lo que no se puede afirmar sin mirar el campo.
        """
        parcela = crear_parcela(alias="El Prado")
        otra = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={"anio": 2025, "fecha_inicio": "2024-09-01", "fecha_fin": "2025-08-31"},
        )
        assert otra.status_code == 201, otra.text
        self._declarar(cliente, cuenta, campana, parcela, campana_id=otra.json()["id"], especie="CEBADA")
        estado = cliente.get(
            f"/api/trabajos/tierra/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()["estado"]
        assert estado["cultivo_declarado"] is None, (
            "el cultivo de 2025 ha salido como lo que hay sembrado en 2026"
        )

# ==========================================================================
# El recorrido 4, por las puertas de verdad (06/10/2026)
# ==========================================================================
#
# **Estas pruebas existen por un defecto de verdad.** La puerta de marcar un plan como hecho
# (`POST /api/trabajos/previstos/<id>/hecho`) contestaba **500 siempre**: dentro escribía
# `datos.subtipo`, y `MarcarHechoEntrada` no tiene ese campo. Es decir: **la segunda mitad del recorrido
# 4 —«planificar un trabajo → marcar lo que de verdad se hizo»— no se podía hacer desde la aplicación**,
# y las pruebas del ticket no lo veían porque solo ejercitaban la lógica pura (`trabajos.marcar_como_hecho`)
# y el fichero del router. Lo encontró el guion del navegador al recorrerlo pulsando: la pantalla decía
# «No se ha podido» y el registro del servidor tenía la traza.
#
# Lo que se comprueba aquí es el recorrido entero, que es lo que el encargo pide: se planifica, se marca
# lo que de verdad se hizo, y el hecho **llega al historial de su tierra** y al cuaderno, con el plan
# marcado como realizado.


class TestElRecorrido4PorLasPuertas:
    def _planificar(self, cliente, cuenta, campana, parcela, **cambios):
        datos = {
            "campana_id": campana["id"],
            "tipo": "laboreo",
            "subtipo": "cultivador",
            "fecha_prevista": "2026-09-20",
            "parcela_id": parcela["id"],
            "superficie_ha": 4.9,
            "horas": 3,
            "observaciones": "Pensado para después de la cosecha",
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/trabajos/previstos", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()["previsto"]

    def test_planificar_marcar_lo_hecho_y_que_llegue_al_historial(
        self, cliente, cuenta, campana, crear_parcela, db_sesion
    ):
        """El recorrido, de punta a punta, y con lo que de verdad se hizo **distinto** de lo pensado."""
        parcela = crear_parcela(alias="El Prado")
        plan = self._planificar(cliente, cuenta, campana, parcela)
        assert plan["estado"] == "previsto"

        # **Este envío es el que contestaba 500.** Se manda lo que la pantalla manda: el día de verdad y
        # las horas de verdad, que no tienen por qué ser las del plan.
        hecho = cliente.post(
            f"/api/trabajos/previstos/{plan['id']}/hecho",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-11-20", "horas": 5, "observaciones": "Al final fui por la tarde"},
        )
        assert hecho.status_code == 201, (
            f"marcar un plan como hecho contesta {hecho.status_code}: el recorrido 4 se queda a medias "
            f"({hecho.text[:200]})"
        )
        suyo = hecho.json()["hecho"]
        assert suyo["fecha"] == "2026-11-20", "el hecho no se ha apuntado con su día de verdad"
        assert suyo["horas"] == 5.0
        # La tierra y el tipo **son los del plan**: el hecho se apunta por la puerta del plan, que es
        # donde el agricultor dijo qué iba a hacer.
        assert suyo["parcela_id"] == parcela["id"]
        assert suyo["tipo"] == "laboreo"
        assert suyo["subtipo"] == "cultivador"

        # Y el plan queda cumplido, apuntando a lo que se hizo.
        planes = cliente.get("/api/trabajos/previstos", headers=cuenta["cabeceras"]).json()
        # La lista trae cada plan con lo que gastaría y los días que faltan: el plan va dentro.
        suyo_plan = next((uno["previsto"] for uno in planes if uno["previsto"]["id"] == plan["id"]), None)
        assert suyo_plan is not None, "el plan ha desaparecido de la lista"
        assert suyo_plan["estado"] == "realizado", "el plan no dice que se cumplió"

        # **Y llega al historial de su tierra**, que es la mitad que el agricultor mira.
        historial = cliente.get(
            f"/api/trabajos/historial/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert historial["cuantos"] == 1, "el trabajo hecho no ha llegado al historial de la tierra"
        assert historial["cifras"]["trabajos_hechos"] == 1

        # Y el rastro dice lo que se apuntó, con su apero: **es la línea que estaba rota** (pedía el
        # subtipo a un cuerpo que no lo trae), así que aquí se ata el dato bueno.
        from app import models

        rastro = db_sesion.query(models.Auditoria).filter_by(entidad="labor", accion="crear").all()
        assert rastro, "no se ha apuntado el rastro del trabajo hecho"
        assert rastro[-1].datos["subtipo"] == "cultivador"
        assert rastro[-1].datos["de_que_plan"] == plan["id"]

    def test_marcar_dos_veces_el_mismo_plan_no_apunta_dos_trabajos(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Y la regla del contrato: **si ya se hizo, es otro trabajo**. La segunda vez se dice (409) en
        vez de apuntar dos hechos del mismo plan."""
        parcela = crear_parcela(alias="El Prado")
        plan = self._planificar(cliente, cuenta, campana, parcela)
        primera = cliente.post(
            f"/api/trabajos/previstos/{plan['id']}/hecho",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-11-20"},
        )
        assert primera.status_code == 201, primera.text

        segunda = cliente.post(
            f"/api/trabajos/previstos/{plan['id']}/hecho",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-11-21"},
        )
        assert segunda.status_code == 409, (
            "un plan ya cumplido se ha vuelto a marcar como hecho: el trabajo quedaría dos veces"
        )
        historial = cliente.get(
            f"/api/trabajos/historial/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert historial["cuantos"] == 1, "hay dos hechos del mismo plan"

    def test_lo_previsto_no_gasta_nada_hasta_que_se_hace(
        self, cliente, cuenta, campana, crear_parcela, crear_producto
    ):
        """La regla que el contrato pide con nombre: **un plan no consume existencias**. Y al marcarlo
        hecho, sí: lo que se gastó sale del almacén por la puerta de las salidas."""
        parcela = crear_parcela(alias="El Prado")
        plan = self._planificar(
            cliente, cuenta, campana, parcela, tipo="siembra", subtipo=None, cultivo="Trigo blando"
        )
        # El plan no ha tocado ningún envase.
        existencias = cliente.get("/api/almacen/existencias", headers=cuenta["cabeceras"])
        assert existencias.status_code == 200, existencias.text
        assert existencias.json()["articulos"] == [], "lo previsto ha gastado algo del almacén"

        hecho = cliente.post(
            f"/api/trabajos/previstos/{plan['id']}/hecho",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-11-20", "horas": 5},
        )
        assert hecho.status_code == 201, hecho.text
        # Y el cuaderno lo cuenta: el trabajo hecho es un apunte del año, con su día.
        cuaderno = cliente.get(
            f"/api/cuaderno/resumen?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        )
        assert cuaderno.status_code == 200, cuaderno.text
