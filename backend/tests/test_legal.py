"""Cálculos legales, probados uno a uno.

Si uno de estos falla, el cuaderno no vale: son las cuentas que el agricultor no
puede hacer de cabeza y de las que depende que pueda vender su cosecha.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import legal


class TestPlazoDeSeguridad:
    def test_suma_los_dias_de_espera(self):
        # 1 de mayo + 21 días = 22 de mayo. Es el ejemplo que se le da al agricultor.
        assert legal.fecha_fin_plazo_seguridad(dt.date(2026, 5, 1), 21) == dt.date(2026, 5, 22)

    def test_plazo_cero_permite_cosechar_el_mismo_dia(self):
        assert legal.fecha_fin_plazo_seguridad(dt.date(2026, 5, 1), 0) == dt.date(2026, 5, 1)

    def test_cruza_el_cambio_de_mes_y_de_ano(self):
        assert legal.fecha_fin_plazo_seguridad(dt.date(2026, 12, 25), 10) == dt.date(2027, 1, 4)

    def test_no_permite_cosechar_antes(self):
        assert not legal.se_puede_cosechar(dt.date(2026, 5, 1), 21, dt.date(2026, 5, 21))

    def test_permite_cosechar_el_dia_exacto(self):
        assert legal.se_puede_cosechar(dt.date(2026, 5, 1), 21, dt.date(2026, 5, 22))

    def test_cuenta_los_dias_que_faltan(self):
        assert legal.dias_para_poder_cosechar(
            dt.date(2026, 5, 1), 21, referencia=dt.date(2026, 5, 13)
        ) == 9

    def test_un_plazo_negativo_es_un_error_de_programa(self):
        with pytest.raises(ValueError):
            legal.fecha_fin_plazo_seguridad(dt.date(2026, 5, 1), -1)


class TestUnidadesFertilizantes:
    def test_el_ejemplo_de_la_etiqueta(self):
        # 300 kg de un abono al 33,5 % aportan 100,5 kg de nitrógeno puro.
        assert legal.unidades_fertilizantes(300, 33.5) == pytest.approx(100.5)

    def test_riqueza_cero_no_aporta_nada(self):
        assert legal.unidades_fertilizantes(300, 0) == 0.0

    def test_uf_por_hectarea(self):
        assert legal.uf_por_hectarea(300, 33.5) == pytest.approx(100.5)

    def test_abono_compuesto_reparte_los_tres_nutrientes(self):
        # Un 15-15-15 a 400 kg/ha aporta 60 kg de cada nutriente.
        assert legal.uf_por_hectarea(400, 15) == pytest.approx(60.0)


class TestDosisYSuperficie:
    def test_dosis_igual_a_la_de_etiqueta_esta_bien(self):
        assert not legal.supera_dosis_etiqueta(0.8, 0.8)

    def test_pasarse_de_dosis_se_detecta(self):
        assert legal.supera_dosis_etiqueta(1.5, 0.8)

    def test_los_redondeos_de_la_etiqueta_no_bloquean(self):
        # 0,8 escrito como 0,8000001 no puede impedir guardar: sería un bloqueo absurdo.
        assert not legal.supera_dosis_etiqueta(0.8000001, 0.8)

    def test_cantidad_total_es_dosis_por_hectareas(self):
        assert legal.cantidad_total(0.8, 2.43) == pytest.approx(1.944)

    def test_tratar_mas_hectareas_que_la_parcela_se_detecta(self):
        assert legal.supera_superficie(5.0, 2.43)

    def test_un_metro_cuadrado_de_mas_no_bloquea(self):
        # 0,0001 ha es 1 m²: el SIGPAC da cuatro decimales y redondear a mano no
        # puede impedir guardar un apunte correcto.
        assert not legal.supera_superficie(2.4301, 2.43)


class TestVigencias:
    def test_sin_fecha_no_esta_vigente(self):
        assert not legal.esta_vigente(None)

    def test_carne_en_plazo(self):
        assert legal.esta_vigente(dt.date(2026, 12, 31), referencia=dt.date(2026, 9, 21))

    def test_carne_caducado(self):
        assert not legal.esta_vigente(dt.date(2026, 3, 3), referencia=dt.date(2026, 9, 21))

    def test_caduca_pronto_avisa_antes(self):
        assert legal.caduca_pronto(dt.date(2026, 10, 10), 30, dt.date(2026, 9, 21))

    def test_caduca_pronto_no_avisa_si_falta_mucho(self):
        assert not legal.caduca_pronto(dt.date(2027, 6, 1), 30, dt.date(2026, 9, 21))

    def test_caduca_pronto_no_avisa_si_ya_caduco(self):
        # Ya caducado es otro aviso, más grave. No se cuenta dos veces.
        assert not legal.caduca_pronto(dt.date(2026, 1, 1), 30, dt.date(2026, 9, 21))


class TestFormatoEnCastellano:
    def test_los_decimales_van_con_coma(self):
        assert legal.formatea_numero(0.8) == "0,80"

    def test_los_miles_van_con_punto(self):
        assert legal.formatea_numero(1234.5, 1) == "1.234,5"

    def test_la_fecha_se_lee_en_castellano(self):
        assert legal.formatea_fecha(dt.date(2026, 5, 22)) == "22/05/2026"

    def test_una_fecha_que_no_existe_se_dice_con_palabras(self):
        assert legal.formatea_fecha(None) == "sin fecha"
