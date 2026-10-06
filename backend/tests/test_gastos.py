"""Pruebas del T13 (E7): los gastos, las inversiones, los repartos y el coste de las averías.

QUÉ SE PRUEBA AQUÍ, Y POR QUÉ ESTAS COSAS

El ticket trae siete reglas que no se pueden saltar, y **cada una tiene aquí una prueba que falla si
la regla se rompe** (no una prueba de «no revienta»):

  1. **Gasto, inversión, factura, pago y movimiento bancario son registros distintos.**
  2. **Conciliar un pago no crea un segundo gasto.**
  3. **Un traspaso entre cuentas propias no crea ingresos** (caso A07 del contrato).
  4. **Pagos parciales y agrupados funcionan y se pueden deshacer** (A06 por el lado de las salidas).
  5. **Costes repartidos + costes sin asignar = total conocido**, y si un gasto no se sabe repartir
     **no se reparte a medias**: se queda sin asignar y se dice.
  6. **Un importe que no consta NO es cero**: es «no lo sé», y viaja así de punta a punta.
  7. **Corregir o anular conserva la auditoría y revierte los efectos.** En este fichero se comprueba
     la mitad que es lógica pura (los efectos que hay que revertir); la auditoría se prueba en
     `TestElRecorridoDeUnGastoDePuntaAPunta`, que necesita el servidor.

Y además, el caso de aceptación **A03** («Abono 600 kg en 3 ha, N 15 % acreditado → 200 kg/ha de
producto; 30 kg N/ha; P desconocido si falta»), que es de este ticket.

DOS PARTES, Y POR QUÉ

  · **La primera parte no necesita servidor ni base de datos**: `app/gastos.py` son cuentas puras,
    como `legal.py`. Se ejecuta hoy y siempre.
  · **La segunda parte sí necesita las tablas y los esquemas**, que los integra el coordinador
    (`models.py` y `schemas.py` son ficheros compartidos y este ticket no los toca). Mientras no
    estén, esas pruebas **se saltan diciendo exactamente qué falta** —no se disimula con un verde—,
    y el día que se integre, corren solas. Eso está contado en `docs/T13_GASTOS.md`.
"""

from __future__ import annotations

import datetime as dt
import importlib
import pathlib
from decimal import Decimal

import pytest

from app import dinero, gastos

# --------------------------------------------------------------------------
# ¿Está ya integrado lo que este ticket necesita para probar el servidor?
# --------------------------------------------------------------------------
#
# Las tablas y los esquemas van en ficheros compartidos (`app/models.py`, `app/schemas.py`) que
# **integra el coordinador**, así que puede ocurrir que este fichero de pruebas se ejecute antes de
# que estén. En ese caso las pruebas del recorrido **se saltan con el motivo escrito**, en vez de
# dar un rojo que no es de nadie o —peor— un verde que no comprueba nada.

def _lo_que_falta_para_probar_el_servidor() -> str:
    """Qué falta para poder ejecutar las pruebas del recorrido, en una frase. Vacío si no falta nada."""
    try:
        modelos = importlib.import_module("app.models")
    except Exception as fallo:  # noqa: BLE001 — cualquier fallo aquí es «no está integrado»
        return f"no se puede importar `app.models`: {fallo}"
    faltan = [
        nombre
        for nombre in (
            "Gasto",
            "InversionDeLaFinca",
            "RepartoDeCoste",
            "PagoDeGasto",
            "AplicacionDeUnPago",
            "Subvencion",
        )
        if not hasattr(modelos, nombre)
    ]
    if faltan:
        return f"faltan las tablas en `app/models.py`: {', '.join(faltan)}"
    try:
        importlib.import_module("app.routers.gastos_api")
    except Exception as fallo:  # noqa: BLE001
        return f"no se puede importar `app.routers.gastos_api`: {fallo}"
    return ""


FALTA_PARA_EL_SERVIDOR = _lo_que_falta_para_probar_el_servidor()

sin_servidor = pytest.mark.skipif(
    bool(FALTA_PARA_EL_SERVIDOR),
    reason=(
        "el recorrido del gasto necesita las tablas y los esquemas, que integra el coordinador: "
        + (FALTA_PARA_EL_SERVIDOR or "")
    ),
)


# --------------------------------------------------------------------------
# 1. Los cinco registros NO son lo mismo
# --------------------------------------------------------------------------


class TestLosCincoRegistrosNoSonLoMismo:
    """La primera regla del encargo: «no los mezcles en una tabla ni en un nombre»."""

    def test_los_cinco_registros_estan_los_cinco_y_sin_repetir(self):
        assert len(gastos.REGISTROS_DE_DINERO) == 5
        assert len(set(gastos.REGISTROS_DE_DINERO)) == 5
        assert set(gastos.REGISTROS_DE_DINERO) == {
            "gasto",
            "inversion",
            "factura",
            "pago",
            "movimiento_bancario",
        }

    def test_una_inversion_no_es_un_gasto_completo_del_cultivo(self):
        """S13, literal: «Compra de activo no equivale automáticamente a gasto completo del cultivo».

        **Esta prueba muerde**: si alguien «arregla» `es_un_gasto_completo_del_cultivo` devolviendo
        `True` para una inversión, el tractor de 60.000 € se mete entero en el margen del año en que
        se compró y la campaña sale con 60.000 € de pérdidas que no existieron.
        """
        assert gastos.es_un_gasto_completo_del_cultivo(gastos.GASTO) is True
        assert gastos.es_un_gasto_completo_del_cultivo(gastos.INVERSION) is False
        assert gastos.es_un_gasto_completo_del_cultivo(gastos.FACTURA) is False
        assert gastos.es_un_gasto_completo_del_cultivo(gastos.PAGO) is False
        assert gastos.es_un_gasto_completo_del_cultivo(gastos.MOVIMIENTO_BANCARIO) is False

    def test_la_factura_el_pago_y_el_extracto_no_aportan_coste_por_si_solos(self):
        """Un coste contado dos veces es peor que un coste que falta, porque no se nota.

        Si la factura aportara coste además del gasto, cada compra contaría dos veces; y si el pago
        aportara coste, una reparación pagada en dos plazos contaría dos veces su importe.
        """
        assert gastos.APORTA_AL_COSTE[gastos.GASTO] is True
        assert gastos.APORTA_AL_COSTE[gastos.FACTURA] is False
        assert gastos.APORTA_AL_COSTE[gastos.PAGO] is False
        assert gastos.APORTA_AL_COSTE[gastos.MOVIMIENTO_BANCARIO] is False
        # Y la inversión no aporta «entera»: aporta solo lo que se le reparta a la campaña, que se
        # suma por la vía de los repartos y no por esta tabla.
        assert gastos.APORTA_AL_COSTE[gastos.INVERSION] is False

    def test_la_cuenta_lleva_los_cinco_registros_contados_por_separado(self):
        """Si los cinco fueran una sola cuenta, el fallo de contarlos dos veces no se vería."""
        cuenta = gastos.cuenta_de_la_explotacion(
            gastos=[{"importe": Decimal("100.00")}],
            inversiones=[{"importe": Decimal("60000.00")}],
            facturas=[{"total": Decimal("100.00")}],
            pagos=[{"importe": Decimal("40.00")}],
            movimientos=[{"importe": Decimal("500.00")}],
        )
        assert (cuenta.gastos, cuenta.inversiones, cuenta.facturas) == (1, 1, 1)
        assert (cuenta.pagos, cuenta.movimientos) == (1, 1)
        # Y el coste conocido es el del gasto, no el de la inversión ni el de la factura.
        assert cuenta.coste_conocido == Decimal("100.00")


# --------------------------------------------------------------------------
# 2. Un importe que no consta NO es cero
# --------------------------------------------------------------------------


class TestUnImporteQueNoConstaNoEsCero:
    """La regla de la casa entera, con las cuatro formas en que se rompe."""

    def test_un_gasto_sin_importe_no_esta_pagado_ni_pendiente(self):
        assert (
            gastos.estado_de_un_gasto(importe=None, pagado=Decimal("0.00"))
            == gastos.SIN_IMPORTE
        )

    def test_un_gasto_de_cero_euros_conocido_no_es_lo_mismo_que_uno_que_no_se_sabe(self):
        """**Esta es la prueba que distingue «no lo sé» de «es cero», y muerde.**

        Un gasto de 0,00 € que consta está pagado (no hay nada que pagar). Uno cuyo importe no
        consta está en «sin importe». Si alguien unifica los dos en un cero, esta prueba se pone
        roja —y en el cuaderno del agricultor eso es un gasto que desaparece de las cuentas—.
        """
        assert (
            gastos.estado_de_un_gasto(importe=Decimal("0.00"), pagado=Decimal("0.00"))
            == gastos.PAGADO
        )
        assert gastos.estado_de_un_gasto(importe=None, pagado=Decimal("0.00")) == gastos.SIN_IMPORTE

    def test_el_pendiente_de_lo_que_no_se_sabe_es_no_se_sabe(self):
        assert gastos.pendiente_de(None, Decimal("10.00")) is None
        assert gastos.pendiente_de(Decimal("121.00"), None) == Decimal("121.00")

    def test_un_importe_que_no_se_sabe_se_enseña_en_blanco_y_no_como_cero(self):
        """De punta a punta: el formateo de la pantalla también tiene que respetarlo."""
        assert dinero.formatea(None) == ""
        assert dinero.formatea(Decimal("0.00")) == "0,00 €"

    def test_el_pie_de_la_cuenta_dice_que_falta_un_importe(self):
        """Un total que calla que le faltan datos miente, aunque sume bien lo que hay."""
        cuenta = gastos.cuenta_de_la_explotacion(
            gastos=[
                {"importe": Decimal("100.00"), "pagado": Decimal("100.00")},
                {"importe": None, "pagado": Decimal("0.00")},
            ]
        )
        assert cuenta.gastos_sin_importe == 1
        # El pendiente **no se puede decir**: no se sabe cuánto falta de lo que no se sabe cuánto
        # costó. Un `0.00 €` ahí diría que no se debe nada.
        assert cuenta.pendiente is None
        # Y el coste conocido sí suma lo que consta: no se pierde lo que sí se sabe.
        assert cuenta.coste_conocido == Decimal("100.00")

    def test_el_iva_que_no_consta_no_se_cuenta_como_cero(self):
        cuadre = gastos.cuadre_de_los_importes(
            base_imponible=Decimal("100.00"), cuota_iva=None, total=Decimal("121.00")
        )
        assert cuadre.no_consta == ["cuota_iva"]
        # No se puede comprobar, pero **no se dice que esté mal**: son dos finales distintos.
        assert cuadre.se_puede_comprobar is False
        assert cuadre.cuadra is True
        assert cuadre.sumado is None


# --------------------------------------------------------------------------
# 3. La aritmética es la prueba
# --------------------------------------------------------------------------


class TestLaAritmeticaEsLaPrueba:
    """base + IVA = total. Cuando no cuadra se dice, y no se reescribe el papel."""

    def test_una_factura_que_cuadra(self):
        cuadre = gastos.cuadre_de_los_importes(
            base_imponible=Decimal("100.00"),
            cuota_iva=Decimal("21.00"),
            total=Decimal("121.00"),
        )
        assert cuadre.cuadra is True
        assert cuadre.se_puede_comprobar is True
        assert cuadre.diferencia == Decimal("0.00")

    def test_una_factura_que_no_cuadra_lo_dice_con_la_diferencia(self):
        """**Muerde**: si alguien quita la comprobación, un número mal leído de la columna de al
        lado entra en las cuentas sin que nadie lo vea."""
        cuadre = gastos.cuadre_de_los_importes(
            base_imponible=Decimal("100.00"),
            cuota_iva=Decimal("21.00"),
            total=Decimal("120.00"),
        )
        assert cuadre.cuadra is False
        assert cuadre.diferencia == Decimal("-1.00")

    def test_el_total_escrito_manda_sobre_la_suma(self):
        """El contrato: «registrar diferencias observadas sin forzar a que una factura original
        cuadre con un redondeo distinto». El programa comprueba, no corrige."""
        assert (
            gastos.importe_de_un_gasto(
                base_imponible=Decimal("100.00"),
                cuota_iva=Decimal("21.00"),
                total=Decimal("120.99"),
            )
            == Decimal("120.99")
        )

    def test_sin_total_escrito_se_suma_y_sin_nada_no_se_sabe(self):
        assert gastos.importe_de_un_gasto(
            base_imponible=Decimal("100.00"), cuota_iva=Decimal("21.00")
        ) == Decimal("121.00")
        assert gastos.importe_de_un_gasto(
            base_imponible=Decimal("100.00"), tipo_iva_pct=Decimal("21")
        ) == Decimal("121.00")
        # **Y sin nada, «no lo sé».** Un cero aquí sería un gasto de cero euros en las cuentas.
        assert gastos.importe_de_un_gasto() is None

    def test_el_iva_calculado_se_enseña_para_poder_compararlo(self):
        cuadre = gastos.cuadre_de_los_importes(
            base_imponible=Decimal("100.00"),
            cuota_iva=Decimal("21.00"),
            total=Decimal("121.00"),
            tipo_iva_pct=Decimal("21"),
        )
        assert cuadre.iva_calculado == Decimal("21.00")


# --------------------------------------------------------------------------
# 4. El reparto: la suma exacta y el céntimo a la vista
# --------------------------------------------------------------------------


class TestElRepartoSumaExacto:
    """«Un reparto que suma 99,99 de 100 y no dice dónde está el céntimo es un defecto»."""

    def test_cien_euros_entre_tres_tierras_iguales_suman_cien(self):
        """**Muerde**: con un redondeo al céntimo trozo a trozo salen 99,99 y el agricultor que echa
        la cuenta con la libreta ve que falta un céntimo."""
        hecho = gastos.reparto_por_area(
            Decimal("100.00"),
            {"El Prado": Decimal("2"), "La Vega": Decimal("2"), "El Alto": Decimal("2")},
        )
        assert hecho.suma() == Decimal("100.00")
        assert hecho.cuadra() is True
        # Y el céntimo que se ha repartido «de más» se dice, con el trozo que lo lleva.
        assert hecho.residual == Decimal("0.01")
        assert hecho.residual_en == "El Prado"
        assert [trozo.importe for trozo in hecho.trozos] == [
            Decimal("33.34"),
            Decimal("33.33"),
            Decimal("33.33"),
        ]

    @pytest.mark.parametrize(
        "total,cuantos",
        [("0.03", 3), ("10.00", 7), ("1234.56", 11), ("1.00", 6), ("99999.99", 13)],
    )
    def test_la_suma_siempre_es_exacta(self, total, cuantos):
        """Con cualquier total y cualquier número de trozos, ni un céntimo de más ni de menos."""
        pesos = {f"tierra-{indice}": Decimal("1.5") for indice in range(cuantos)}
        hecho = gastos.reparto_por_area(Decimal(total), pesos)
        assert hecho.suma() == Decimal(total)

    def test_el_reparto_se_puede_repetir_y_da_lo_mismo(self):
        """El mismo gasto y las mismas hectáreas tienen que dar el mismo reparto hoy y en un año.

        Sin un orden fijo para romper el empate, el céntimo del redondeo se le daría a uno u otro
        según cómo viniera el diccionario, y el programa parecería que cambia las cuentas solo.
        """
        pesos = {"b": Decimal("2"), "a": Decimal("2"), "c": Decimal("2")}
        primero = gastos.reparto_por_area(Decimal("100.00"), pesos)
        segundo = gastos.reparto_por_area(Decimal("100.00"), pesos)
        assert [t.importe for t in primero.trozos] == [t.importe for t in segundo.trozos]
        assert [t.destino for t in primero.trozos] == [t.destino for t in segundo.trozos]

    def test_un_reparto_por_hectareas_no_es_un_reparto_igualitario(self):
        hecho = gastos.reparto_por_area(
            Decimal("300.00"), {"grande": Decimal("10"), "pequena": Decimal("5")}
        )
        assert [t.importe for t in hecho.trozos] == [Decimal("200.00"), Decimal("100.00")]

    def test_los_tres_metodos_de_calculo_llevan_su_nombre(self):
        """El método se guarda con cada trozo: es lo que permite revisar de dónde salió la cifra."""
        assert gastos.reparto_por_area(Decimal("10"), {"a": Decimal("1")}).metodo == gastos.AREA
        assert gastos.reparto_por_horas(Decimal("10"), {"a": Decimal("1")}).metodo == gastos.HORAS
        assert (
            gastos.reparto_por_consumo(Decimal("10"), {"a": Decimal("1")}).metodo == gastos.CONSUMO
        )

    def test_un_importe_negativo_se_reparte_igual_y_con_su_signo(self):
        """Una devolución del proveedor es un gasto negativo y se reparte como cualquier otro."""
        hecho = gastos.reparto_por_area(
            Decimal("-100.00"), {"a": Decimal("1"), "b": Decimal("1"), "c": Decimal("1")}
        )
        assert hecho.suma() == Decimal("-100.00")
        assert all(trozo.importe < 0 for trozo in hecho.trozos)


class TestUnPesoQueNoSeSabeNoSeReparteAMedias:
    """La trampa del ticket: «si un gasto no se sabe repartir, no se reparte a medias»."""

    def test_si_falta_la_superficie_de_una_tierra_no_se_reparte(self):
        """**Muerde, y es la prueba que más importa de este fichero.**

        Repartir 100 € entre las dos tierras que sí se saben les cargaría también la parte de la
        tercera, o sea un coste por hectárea inventado. Lo que se hace es no repartir y decirlo.
        """
        hecho = gastos.reparto_por_area(
            Decimal("100.00"), {"El Prado": Decimal("2"), "La Vega": None}
        )
        assert hecho.trozos == []
        assert hecho.no_se_puede == gastos.NO_SE_REPARTE_PORQUE_FALTA_UN_PESO
        assert hecho.sin_peso == ["La Vega"]
        assert hecho.suma() == Decimal("0.00")

    def test_el_gasto_entero_se_queda_sin_asignar_y_el_cuadre_sigue_cuadrando(self):
        """Lo que no se reparte **no desaparece**: sigue siendo un coste conocido, sin dueño."""
        cuadre = gastos.el_gasto_queda_sin_asignar(
            Decimal("100.00"), porque=gastos.NO_SE_REPARTE_PORQUE_FALTA_UN_PESO
        )
        assert cuadre.repartido == Decimal("0.00")
        assert cuadre.sin_asignar == Decimal("100.00")
        assert cuadre.falta == Decimal("0.00")
        assert cuadre.cuadra is True
        assert cuadre.no_se_reparte == gastos.NO_SE_REPARTE_PORQUE_FALTA_UN_PESO

    def test_sin_importe_tampoco_se_reparte_y_se_dice_por_que(self):
        hecho = gastos.reparto_por_area(None, {"El Prado": Decimal("2")})
        assert hecho.no_se_puede == gastos.NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE
        assert hecho.total is None
        # Y el cuadre de un gasto sin importe no se puede cerrar: no se dice que cuadre.
        cuadre = gastos.cuadre_del_reparto(None, [])
        assert cuadre.cuadra is False
        assert cuadre.falta is None
        assert cuadre.no_se_reparte == gastos.NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE

    def test_todos_los_pesos_a_cero_tampoco_es_un_reparto(self):
        hecho = gastos.reparto_por_horas(Decimal("50.00"), {"a": Decimal("0"), "b": Decimal("0")})
        assert hecho.no_se_puede == gastos.NO_SE_REPARTE_PORQUE_FALTA_UN_PESO


class TestElCuadreDelReparto:
    """«Costes repartidos + costes sin asignar = total conocido»."""

    def test_repartido_mas_sin_asignar_es_el_total_conocido(self):
        cuadre = gastos.cuadre_del_reparto(
            Decimal("100.00"),
            [
                {"destino_tipo": gastos.TIERRA, "destino": "El Prado", "importe": Decimal("60.00")},
                {"destino_tipo": gastos.SIN_ASIGNAR, "destino": "", "importe": Decimal("40.00")},
            ],
        )
        assert cuadre.repartido == Decimal("60.00")
        assert cuadre.sin_asignar == Decimal("40.00")
        assert cuadre.total_conocido() == Decimal("100.00")
        assert cuadre.falta == Decimal("0.00")
        assert cuadre.cuadra is True

    def test_lo_que_no_esta_en_ningun_sitio_se_dice_cuanto_es(self):
        """**Muerde**: un gasto de 100 € con 60 € repartidos y nada sin asignar tiene 40 € que se
        han perdido por el camino, y sin esta comprobación nadie se enteraría."""
        cuadre = gastos.cuadre_del_reparto(
            Decimal("100.00"),
            [{"destino_tipo": gastos.TIERRA, "destino": "El Prado", "importe": Decimal("60.00")}],
        )
        assert cuadre.falta == Decimal("40.00")
        assert cuadre.cuadra is False

    def test_repartir_mas_de_lo_que_costo_es_un_error_y_se_ve(self):
        cuadre = gastos.cuadre_del_reparto(
            Decimal("100.00"),
            [{"destino_tipo": gastos.TIERRA, "destino": "El Prado", "importe": Decimal("140.00")}],
        )
        assert cuadre.falta == Decimal("-40.00")
        assert cuadre.cuadra is False

    def test_un_trozo_sin_importe_no_se_cuenta_como_cero_y_se_dice_cuantos_son(self):
        cuadre = gastos.cuadre_del_reparto(
            Decimal("100.00"),
            [
                {"destino_tipo": gastos.TIERRA, "destino": "El Prado", "importe": Decimal("100.00")},
                {"destino_tipo": gastos.CULTIVO, "destino": "Trigo", "importe": None},
            ],
        )
        assert cuadre.trozos_sin_importe == 1
        assert cuadre.repartido == Decimal("100.00")

    def test_el_cuadre_del_reparto_se_puede_mandar_entero_a_la_pantalla(self):
        """Los números viajan como texto decimal (contrato §2), y un «no lo sé» viaja en blanco."""
        cuadre = gastos.cuadre_del_reparto(None, [])
        texto = cuadre.como_dict()
        assert texto["entero"] is None
        assert texto["repartido"] == "0.00"
        assert texto["cuadra"] is False


class TestElMetodoLoConfirmaElAgricultor:
    """El contrato: «método de reparto confirmado (área, horas, consumo o manual)»."""

    def test_los_cuatro_metodos_estan_y_son_los_cuatro(self):
        assert set(gastos.METODOS_DE_REPARTO) == {"area", "horas", "consumo", "manual"}

    def test_un_metodo_que_no_existe_se_rechaza_en_vez_de_inventarse_uno(self):
        with pytest.raises(ValueError):
            gastos.reparto_por_peso(
                Decimal("10"), {"a": Decimal("1")}, metodo="lo_que_sea", destino_tipo=gastos.TIERRA
            )

    def test_el_reparto_a_mano_lleva_su_metodo_y_no_calcula_nada(self):
        hecho = gastos.reparto_a_mano(
            Decimal("100.00"),
            [
                {"destino_tipo": gastos.TIERRA, "destino": "El Prado", "importe": Decimal("70.00")},
            ],
        )
        assert hecho.metodo == gastos.MANUAL
        assert hecho.trozos[0].metodo == gastos.MANUAL
        assert hecho.suma() == Decimal("70.00")

    def test_el_reparto_a_mano_que_suma_de_mas_lo_dice(self):
        hecho = gastos.reparto_a_mano(
            Decimal("100.00"),
            [
                {"destino_tipo": gastos.TIERRA, "destino": "El Prado", "importe": Decimal("60.00")},
                {"destino_tipo": gastos.TIERRA, "destino": "La Vega", "importe": Decimal("50.00")},
            ],
        )
        assert hecho.no_se_puede == "se_ha_repartido_mas_que_el_gasto"


# --------------------------------------------------------------------------
# 5. El abono: el caso de aceptación A03
# --------------------------------------------------------------------------


class TestElAbonoDelCasoA03:
    """«Abono 600 kg en 3 ha, N 15 % acreditado | 200 kg/ha de producto; 30 kg N/ha; P desconocido»."""

    def test_las_dos_cifras_del_a03(self):
        abono = gastos.abono_por_hectarea(
            kg_producto=Decimal("600"),
            superficie_ha=Decimal("3"),
            riquezas={"n": Decimal("15"), "p": None, "k": None},
        )
        assert abono.producto_ha == Decimal("200.00")
        assert abono.nutriente_ha["n"] == Decimal("30.00")

    def test_el_fosforo_que_no_consta_no_es_cero(self):
        """**Muerde, y es el caso A03 entero.**

        Si alguien convierte el fósforo que nadie ha declarado en `0`, el programa está afirmando
        que ese abono no aporta fósforo —una mentira sobre el abono— y el dato acaba en el documento
        que se firma. Lo que tiene que salir es «no lo sé».
        """
        abono = gastos.abono_por_hectarea(
            kg_producto=Decimal("600"),
            superficie_ha=Decimal("3"),
            riquezas={"n": Decimal("15"), "p": None, "k": None},
        )
        assert abono.nutriente_ha["p"] is None
        assert abono.nutriente_ha["k"] is None
        assert abono.no_consta == ["p", "k"]
        assert abono.sin_ninguna_riqueza is False

    def test_el_producto_por_hectarea_y_el_nutriente_por_hectarea_son_dos_cifras_distintas(self):
        """200 kg de producto y 30 kg de nitrógeno no son el mismo número, y confundirlos es un
        error de diez veces. Van en dos campos distintos para que no se puedan intercambiar."""
        abono = gastos.abono_por_hectarea(
            kg_producto=Decimal("600"),
            superficie_ha=Decimal("3"),
            riquezas={"n": Decimal("15")},
        )
        assert abono.producto_ha == Decimal("200.00")
        assert abono.nutriente_ha["n"] == Decimal("30.00")
        assert abono.producto_ha != abono.nutriente_ha["n"]

    def test_sin_superficie_las_dos_cifras_por_hectarea_no_se_saben(self):
        """A02 y A03 por el mismo camino: si falta el área, la dosis es **desconocida**, no el total."""
        abono = gastos.abono_por_hectarea(
            kg_producto=Decimal("600"), superficie_ha=None, riquezas={"n": Decimal("15")}
        )
        assert abono.producto_ha is None
        assert abono.nutriente_ha["n"] is None
        # Pero el total de nutriente sí se sabe: los kilos de producto constan.
        assert abono.nutriente_total["n"] == Decimal("90.00")

    def test_una_superficie_de_cero_no_da_una_dosis_infinita(self):
        abono = gastos.abono_por_hectarea(
            kg_producto=Decimal("600"), superficie_ha=Decimal("0"), riquezas={"n": Decimal("15")}
        )
        assert abono.producto_ha is None

    def test_un_abono_del_que_no_se_sabe_ninguna_riqueza_lo_dice(self):
        abono = gastos.abono_por_hectarea(
            kg_producto=Decimal("600"), superficie_ha=Decimal("3"), riquezas={}
        )
        assert abono.sin_ninguna_riqueza is True
        assert abono.no_consta == ["n", "p", "k"]


# --------------------------------------------------------------------------
# 6. Conciliar un pago no crea un segundo gasto
# --------------------------------------------------------------------------


class TestConciliarUnPagoNoCreaUnGasto:
    """La regla del encargo, y el caso A06 por el lado de las salidas."""

    def test_el_caso_a06_por_las_salidas(self):
        """«Factura 121 EUR, pago 40 EUR → pendiente 81»."""
        assert gastos.pendiente_de(Decimal("121.00"), Decimal("40.00")) == Decimal("81.00")
        assert (
            gastos.estado_de_un_gasto(importe=Decimal("121.00"), pagado=Decimal("40.00"))
            == gastos.PAGADO_EN_PARTE
        )

    def test_conciliar_no_cambia_el_numero_de_gastos(self):
        """**Muerde.** Es la prueba de la regla «conciliar un pago no crea un segundo gasto».

        La cuenta de la finca se cierra antes y después de conciliar, y el número de gastos tiene que
        ser el mismo. Si alguien hiciera que conciliar apuntara algo en la lista de gastos —que es la
        forma fácil y equivocada de guardar la deuda—, aquí saltaría.
        """
        gastos_apuntados = [
            {"id": 1, "importe": Decimal("121.00"), "pagado": Decimal("0.00")},
            {"id": 2, "importe": Decimal("60.00"), "pagado": Decimal("0.00")},
        ]
        antes = gastos.cuenta_de_la_explotacion(gastos=gastos_apuntados)
        assert antes.gastos == 2

        # Se concilia un pago de 40 € contra el primer gasto: lo único que sale son aplicaciones.
        reparto = gastos.reparto_de_un_pago(
            Decimal("40.00"), [(1, gastos.pendiente_de(Decimal("121.00"), None))]
        )
        assert [a.como_dict() for a in reparto.aplicaciones] == [
            {"gasto_id": 1, "importe": "40.00"}
        ]

        # Y ahora la cuenta, con el pago aplicado: los gastos siguen siendo dos.
        con_el_pago = [
            {"id": 1, "importe": Decimal("121.00"), "pagado": reparto.aplicaciones[0].importe},
            {"id": 2, "importe": Decimal("60.00"), "pagado": Decimal("0.00")},
        ]
        despues = gastos.cuenta_de_la_explotacion(gastos=con_el_pago, pagos=[{"importe": Decimal("40.00")}])
        assert despues.gastos == antes.gastos
        assert despues.gastos == 2
        # Lo que sí cambia es lo pagado y el pendiente.
        assert despues.pagado == Decimal("40.00")
        assert despues.pendiente == Decimal("141.00")

    def test_un_pago_agrupado_salda_varios_gastos_sin_perder_un_centimo(self):
        reparto = gastos.reparto_de_un_pago(
            Decimal("100.00"),
            [(1, Decimal("60.00")), (2, Decimal("60.00")), (3, Decimal("60.00"))],
        )
        assert [(a.gasto_id, a.importe) for a in reparto.aplicaciones] == [
            (1, Decimal("60.00")),
            (2, Decimal("40.00")),
        ]
        assert reparto.sin_conciliar == Decimal("0.00")
        assert dinero.suma(*[a.importe for a in reparto.aplicaciones]) == Decimal("100.00")

    def test_dos_pagos_parciales_saldan_la_deuda_entre_los_dos(self):
        primero = gastos.reparto_de_un_pago(Decimal("40.00"), [(1, Decimal("81.00"))])
        assert primero.aplicaciones[0].importe == Decimal("40.00")
        assert primero.sin_conciliar == Decimal("0.00")
        pendiente = gastos.pendiente_de(Decimal("121.00"), Decimal("40.00"))
        segundo = gastos.reparto_de_un_pago(Decimal("81.00"), [(1, pendiente)])
        assert segundo.aplicaciones[0].importe == Decimal("81.00")
        assert (
            gastos.estado_de_un_gasto(importe=Decimal("121.00"), pagado=Decimal("121.00"))
            == gastos.PAGADO
        )

    def test_un_pago_mayor_que_la_deuda_deja_lo_que_sobra_dicho_y_no_un_pendiente_negativo(self):
        reparto = gastos.reparto_de_un_pago(
            Decimal("500.00"), [(1, Decimal("121.00"))]
        )
        assert reparto.aplicaciones[0].importe == Decimal("121.00")
        assert reparto.sin_conciliar == Decimal("379.00")
        # Y el pendiente del gasto **nunca** es negativo: se queda en cero.
        assert gastos.pendiente_de(Decimal("121.00"), Decimal("500.00")) == Decimal("0.00")

    def test_a_un_gasto_cuyo_importe_no_consta_no_se_le_aplica_dinero(self):
        """No se le puede aplicar dinero contra una cantidad desconocida: sería inventarse la deuda."""
        reparto = gastos.reparto_de_un_pago(
            Decimal("100.00"), [(1, None), (2, Decimal("50.00"))]
        )
        assert reparto.sin_importe == [1]
        assert [(a.gasto_id, a.importe) for a in reparto.aplicaciones] == [
            (2, Decimal("50.00"))
        ]
        assert reparto.sin_conciliar == Decimal("50.00")

    def test_deshacer_una_conciliacion_devuelve_la_deuda_y_no_borra_el_pago(self):
        """**Muerde.** Lo que devuelve `deshacer_las_aplicaciones` es una lista de pendientes: no
        borra el pago, no borra el gasto y no puede borrarlos, porque no los tiene."""
        pendientes_antes = [(1, Decimal("81.00"))]
        despues = gastos.deshacer_las_aplicaciones(
            [{"gasto_id": 1, "importe": Decimal("40.00")}], pendientes_antes
        )
        assert despues == [(1, Decimal("121.00"))]
        # Y el pago sigue apuntado con su importe entero: la función no lo toca.
        assert isinstance(despues, list)

    def test_lo_que_no_se_sabe_tampoco_se_puede_deshacer(self):
        """Un gasto sin importe sigue sin saberse después de deshacer: `None` sigue siendo `None`."""
        despues = gastos.deshacer_las_aplicaciones(
            [{"gasto_id": 1, "importe": Decimal("40.00")}], [(1, None)]
        )
        assert despues == [(1, None)]


# --------------------------------------------------------------------------
# 7. El traspaso entre cuentas propias: el caso A07
# --------------------------------------------------------------------------


class TestElTraspasoPropioNoEsIngresoNiGasto:
    """«Traspaso propio 500 EUR | Dos movimientos vinculados, cero ingreso/gasto operativo»."""

    def test_el_caso_a07_los_dos_movimientos_estan_atados(self):
        traspaso = gastos.traspaso_entre_cuentas_propias(
            Decimal("500.00"), cuenta_origen="Cuenta del banco", cuenta_destino="Cuenta de la cooperativa"
        )
        assert len(traspaso.movimientos) == 2
        assert traspaso.vinculados is True
        assert [movimiento["signo"] for movimiento in traspaso.movimientos] == ["-", "+"]
        assert {movimiento["importe"] for movimiento in traspaso.movimientos} == {"500.00"}

    def test_el_traspaso_no_mueve_el_margen(self):
        """**Muerde, y es la trampa del A07.**

        La forma «natural» de tratarlo sería sumar la entrada como ingreso y la salida como gasto: el
        agricultor vería 500 € de ingreso y 500 € de gasto que no existieron, la caja cuadraría y el
        margen sería mentira. Aquí los dos ceros se comprueban uno a uno.
        """
        traspaso = gastos.traspaso_entre_cuentas_propias(
            Decimal("500.00"), cuenta_origen="A", cuenta_destino="B"
        )
        assert traspaso.ingreso_operativo == Decimal("0.00")
        assert traspaso.gasto_operativo == Decimal("0.00")
        # Y la caja sí los ve: el dinero sale de una cuenta y entra en otra.
        assert traspaso.salida == Decimal("500.00")
        assert traspaso.entrada == Decimal("500.00")

    def test_un_traspaso_a_la_misma_cuenta_no_esta_atado(self):
        traspaso = gastos.traspaso_entre_cuentas_propias(
            Decimal("500.00"), cuenta_origen="A", cuenta_destino="A"
        )
        assert traspaso.vinculados is False

    def test_un_traspaso_sin_importe_no_es_un_traspaso_de_cero(self):
        traspaso = gastos.traspaso_entre_cuentas_propias(
            None, cuenta_origen="A", cuenta_destino="B"
        )
        assert traspaso.importe is None
        assert traspaso.movimientos == []
        assert traspaso.vinculados is False


# --------------------------------------------------------------------------
# 8. Las subvenciones: prevista, concedida y cobrada
# --------------------------------------------------------------------------


class TestLasSubvencionesTienenTresEstados:
    """«No sumar previsión al ingreso cobrado» (contrato, S13)."""

    def test_el_estado_es_el_mas_avanzado_de_los_que_constan(self):
        assert gastos.estado_de_una_subvencion(prevista=True, concedida=False, cobrada=False) == "prevista"
        assert gastos.estado_de_una_subvencion(prevista=True, concedida=True, cobrada=False) == "concedida"
        assert gastos.estado_de_una_subvencion(prevista=True, concedida=True, cobrada=True) == "cobrada"
        # Y una ayuda de la que no consta nada no es «prevista»: es que no se sabe.
        assert gastos.estado_de_una_subvencion(prevista=False, concedida=False, cobrada=False) == ""

    def test_la_prevision_no_se_suma_al_ingreso_cobrado(self):
        """**Muerde.** Es la regla escrita del contrato, y con una previsión de 12.000 € el agricultor
        creería que tiene un dinero que todavía no ha entrado."""
        subvenciones = [
            {"estado": gastos.COBRADA, "importe": Decimal("3000.00")},
            {"estado": gastos.CONCEDIDA, "importe": Decimal("9000.00")},
            {"estado": gastos.PREVISTA, "importe": Decimal("12000.00")},
        ]
        assert gastos.ingreso_cobrado_de_subvenciones(subvenciones) == Decimal("3000.00")
        # Y lo que se espera se dice aparte, no se tira.
        assert gastos.importe_previsto_de_subvenciones(subvenciones) == Decimal("21000.00")

    def test_una_subvencion_sin_importe_no_suma_cero(self):
        assert gastos.ingreso_cobrado_de_subvenciones(
            [{"estado": gastos.COBRADA, "importe": None}]
        ) == Decimal("0.00")


# --------------------------------------------------------------------------
# 9. El coste de las averías
# --------------------------------------------------------------------------


class TestElCosteDeLasAverias:
    """Lo que el T14 dejó declarado como de este ticket."""

    def test_el_coste_es_la_suma_de_los_gastos_de_la_averia_con_sus_tres_columnas(self):
        coste = gastos.coste_de_una_averia(
            [
                {"importe": Decimal("900.00"), "clase": gastos.DIRECTO},
                {"importe": Decimal("100.00"), "clase": gastos.REPARTIDO},
                {"importe": Decimal("50.00"), "clase": gastos.SIN_ASIGNAR_CLASE},
            ],
            averia_id=7,
        )
        assert coste.coste == Decimal("1050.00")
        assert coste.directo == Decimal("900.00")
        assert coste.repartido == Decimal("100.00")
        assert coste.sin_asignar == Decimal("50.00")
        assert coste.completo() is True

    def test_un_gasto_de_la_averia_sin_importe_no_es_un_cero_y_se_cuenta(self):
        """**Muerde.** «Costó 900 €» y «de esta reparación constan 900 € y hay un gasto del que no se
        sabe el importe» son dos frases distintas, y la segunda es la verdad."""
        coste = gastos.coste_de_una_averia(
            [
                {"importe": Decimal("900.00"), "clase": gastos.DIRECTO},
                {"importe": None, "clase": gastos.DIRECTO},
            ],
            averia_id=7,
        )
        assert coste.coste == Decimal("900.00")
        assert coste.sin_importe == 1
        assert coste.gastos == 2
        assert coste.completo() is False

    def test_una_averia_sin_ningun_gasto_cuesta_no_lo_se(self):
        """Ni cero ni «no costó nada»: es que no hay ningún apunte de lo que costó."""
        coste = gastos.coste_de_una_averia([], averia_id=7)
        assert coste.coste is None
        assert coste.gastos == 0
        assert coste.completo() is False

    def test_un_gasto_anulado_no_cuenta_pero_sigue_en_el_cuaderno(self):
        coste = gastos.coste_de_una_averia(
            [
                {"importe": Decimal("900.00"), "clase": gastos.DIRECTO},
                {"importe": Decimal("900.00"), "clase": gastos.DIRECTO, "anulado": True},
            ],
            averia_id=7,
        )
        assert coste.coste == Decimal("900.00")
        assert coste.gastos == 1

    def test_estar_arreglada_y_tener_coste_son_dos_cosas_distintas(self):
        """Una reparación de 900 € pagada no quiere decir que la máquina esté para trabajar."""
        arreglada = gastos.coste_de_una_averia(
            [{"importe": Decimal("900.00"), "clase": gastos.DIRECTO}],
            averia_id=7,
            arreglada=True,
        )
        sin_arreglar = gastos.coste_de_una_averia(
            [{"importe": Decimal("900.00"), "clase": gastos.DIRECTO}],
            averia_id=7,
            arreglada=False,
        )
        assert arreglada.coste == sin_arreglar.coste
        assert arreglada.arreglada is True and sin_arreglar.arreglada is False

    def test_el_coste_se_agrupa_por_averia_y_lo_que_no_cuelga_de_ninguna_se_dice(self):
        por_averia = gastos.coste_de_las_averias(
            [
                {"averia_id": 7, "importe": Decimal("900.00")},
                {"averia_id": 7, "importe": Decimal("100.00")},
                {"averia_id": 9, "importe": Decimal("50.00")},
                {"averia_id": None, "importe": Decimal("300.00")},
            ]
        )
        assert por_averia[7].coste == Decimal("1000.00")
        assert por_averia[9].coste == Decimal("50.00")
        # Los gastos de reparación que no cuelgan de ninguna avería no se pierden: se cuentan aparte
        # para que nadie crea que el coste de las averías es todo lo que se ha gastado en reparar.
        assert por_averia[-1].gastos == 1
        assert por_averia[-1].coste is None


# --------------------------------------------------------------------------
# 10. El margen y la caja: dos tarjetas distintas, y una puede estar incompleta
# --------------------------------------------------------------------------


class TestElMargenNoSeConstruyeConDatosQueFaltan:
    """«No construir un margen con datos que faltan. Si no se sabe un coste, el margen se enseña
    incompleto y diciéndolo, no con un cero»."""

    def test_el_margen_de_un_concepto_completo_se_calcula(self):
        cuenta = gastos.margen_por_concepto(
            [
                {"concepto": "Trigo", "importe": Decimal("1000.00"), "clase": gastos.DIRECTO},
                {"concepto": "Trigo", "importe": Decimal("200.00"), "clase": gastos.REPARTIDO},
            ],
            [{"concepto": "Trigo", "importe": Decimal("2000.00"), "cobrado": Decimal("500.00")}],
        )["Trigo"]
        assert cuenta.coste_conocido() == Decimal("1200.00")
        assert cuenta.margen() == Decimal("800.00")
        assert cuenta.completo() is True

    def test_con_un_coste_que_no_se_sabe_no_hay_margen(self):
        """**Muerde, y es la regla que más importa de este ticket.**

        Si el margen se calculara ignorando el coste que falta, saldría un número **más alto** que el
        verdadero y el agricultor creería que ha ganado dinero que no ha ganado. Lo que tiene que
        pasar es que el margen **no se pueda calcular** y que se diga cuántos importes faltan.
        """
        cuenta = gastos.margen_por_concepto(
            [
                {"concepto": "Trigo", "importe": Decimal("1000.00"), "clase": gastos.DIRECTO},
                {"concepto": "Trigo", "importe": None, "clase": gastos.DIRECTO},
            ],
            [{"concepto": "Trigo", "importe": Decimal("2000.00"), "cobrado": Decimal("2000.00")}],
        )["Trigo"]
        assert cuenta.margen() is None
        assert cuenta.completo() is False
        assert cuenta.costes_que_no_se == 1
        # Y el coste que sí consta no se pierde: se enseña, para saber lo que se sabe.
        assert cuenta.coste_conocido() == Decimal("1000.00")
        # En el texto que va a la pantalla, «no lo sé» viaja en blanco, no como «0.00».
        assert cuenta.como_dict()["margen"] is None

    def test_un_ingreso_que_no_se_sabe_tambien_deja_el_margen_sin_calcular(self):
        cuenta = gastos.margen_por_concepto(
            [{"concepto": "Trigo", "importe": Decimal("1000.00"), "clase": gastos.DIRECTO}],
            [{"concepto": "Trigo", "importe": None}],
        )["Trigo"]
        assert cuenta.margen() is None
        assert cuenta.ingresos_que_no_se == 1

    def test_los_costes_sin_asignar_siguen_contando_en_el_coste_conocido(self):
        """Un coste sin dueño es un coste conocido: si no sumara, el margen saldría mejor de lo que es."""
        cuenta = gastos.margen_por_concepto(
            [
                {"concepto": "Trigo", "importe": Decimal("1000.00"), "clase": gastos.DIRECTO},
                {"concepto": "Trigo", "importe": Decimal("400.00"), "clase": gastos.SIN_ASIGNAR_CLASE},
            ],
            [{"concepto": "Trigo", "importe": Decimal("2000.00")}],
        )["Trigo"]
        assert cuenta.sin_asignar == Decimal("400.00")
        assert cuenta.coste_conocido() == Decimal("1400.00")
        assert cuenta.margen() == Decimal("600.00")

    def test_lo_cobrado_no_es_lo_ganado(self):
        """El margen va con lo registrado y la caja con lo cobrado: son dos columnas distintas."""
        cuenta = gastos.margen_por_concepto(
            [], [{"concepto": "Trigo", "importe": Decimal("2000.00"), "cobrado": Decimal("500.00")}]
        )["Trigo"]
        assert cuenta.ingresos == Decimal("2000.00")
        assert cuenta.cobrado == Decimal("500.00")
        assert cuenta.margen() == Decimal("2000.00")

    def test_el_margen_de_la_finca_no_sale_si_falta_un_importe(self):
        cuenta = gastos.cuenta_de_la_explotacion(
            gastos=[{"importe": None}], ingresos=Decimal("1000.00")
        )
        assert cuenta.margen is None
        assert cuenta.margen_completo is False


class TestLaCajaNoEsElMargen:
    """«Margen operativo y caja tienen tarjetas distintas» (contrato, S13)."""

    def test_la_caja_cuenta_dinero_que_se_ha_movido_y_el_margen_lo_registrado(self):
        """**Muerde.** Con los mismos datos, las dos cifras tienen que poder ser distintas: si
        alguien unificara las dos tarjetas, una de las dos preguntas se quedaría sin contestar."""
        caja = gastos.caja(
            cobros=[{"importe": Decimal("500.00")}],
            pagos=[{"importe": Decimal("1200.00")}],
            por_cobrar=[Decimal("1500.00")],
            por_pagar=[Decimal("300.00")],
        )
        assert caja.entrado == Decimal("500.00")
        assert caja.salido == Decimal("1200.00")
        assert caja.saldo() == Decimal("-700.00")
        assert caja.por_cobrar == Decimal("1500.00")
        assert caja.por_pagar == Decimal("300.00")

        cuenta = gastos.margen_por_concepto(
            [{"concepto": "Trigo", "importe": Decimal("1200.00"), "clase": gastos.DIRECTO}],
            [{"concepto": "Trigo", "importe": Decimal("2000.00"), "cobrado": Decimal("500.00")}],
        )["Trigo"]
        # El mismo año: margen positivo y caja en negativo. Las dos cosas son verdad a la vez.
        assert cuenta.margen() == Decimal("800.00")
        assert caja.saldo() == Decimal("-700.00")

    def test_un_movimiento_anulado_no_cuenta_en_la_caja(self):
        caja = gastos.caja(
            cobros=[{"importe": Decimal("500.00"), "anulado": True}],
            pagos=[{"importe": Decimal("1200.00"), "anulado": True}],
        )
        assert caja.entrado == Decimal("0.00")
        assert caja.salido == Decimal("0.00")

    def test_un_movimiento_sin_importe_no_suma_cero_y_se_dice_cuantos_son(self):
        caja = gastos.caja(cobros=[{"importe": None}, {"importe": Decimal("100.00")}])
        assert caja.entrado == Decimal("100.00")
        assert caja.importes_que_no_se == 1

    def test_las_ayudas_previstas_van_fuera_de_lo_entrado(self):
        caja = gastos.caja(
            subvenciones=[
                {"estado": gastos.PREVISTA, "importe": Decimal("12000.00")},
                {"estado": gastos.COBRADA, "importe": Decimal("3000.00")},
            ]
        )
        assert caja.entrado == Decimal("0.00")
        assert caja.ayudas_cobradas == Decimal("3000.00")
        assert caja.ayudas_previstas == Decimal("12000.00")
        # El saldo de la caja no lleva la previsión dentro: no es dinero que haya.
        assert caja.saldo() == Decimal("0.00")


# --------------------------------------------------------------------------
# 11. La lista de lo que este programa todavía no calcula
# --------------------------------------------------------------------------


class TestLoQueEsteModuloNoHace:
    """Se dice para que nadie lo confunda con un olvido, como en el T14."""

    def test_no_hay_ninguna_amortizacion_calculada(self):
        """No hay ninguna tabla oficial de años de vida útil cargada, así que no se amortiza solo.

        Esta prueba existe para que nadie «arregle» el módulo metiendo una amortización lineal con
        años inventados: el día que se haga, tendrá que ser con la fuente delante y con esta prueba
        cambiada a propósito.
        """
        fuente = pathlib.Path(gastos.__file__).read_text(encoding="utf-8")
        assert "amortiza" in fuente.lower(), "el módulo tiene que decir que NO amortiza"
        assert "vida_util" not in fuente, "no puede haber una vida útil sin fuente que la respalde"

    def test_los_estados_y_los_motivos_son_codigos_y_no_frases(self):
        """Las palabras las pone `textos.py`: aquí solo hay códigos que la pantalla traduce."""
        for codigo in gastos.ESTADOS_DE_UN_GASTO + gastos.METODOS_DE_REPARTO:
            assert codigo.islower()
            assert " " not in codigo
        for motivo in (
            gastos.NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE,
            gastos.NO_SE_REPARTE_PORQUE_FALTA_UN_PESO,
        ):
            assert motivo.islower() and " " not in motivo


# --------------------------------------------------------------------------
# 12. El recorrido de punta a punta: lo que necesita el servidor
# --------------------------------------------------------------------------
#
# Estas pruebas son **el recorrido** del ticket: apuntar un gasto → asignarlo a tierras, cultivos o
# máquinas → consultar el importe conocido, los repartos y lo pendiente de pagar. Necesitan las tablas
# (`models.py`) y los esquemas (`schemas.py`), que son ficheros compartidos y los integra el
# coordinador. Mientras no estén, **se saltan diciendo exactamente qué falta**; el día que se integren
# corren solas, sin tocar nada de este fichero.
#
# Y lo que comprueban no es «no revienta»: cada una es una de las siete reglas del encargo.


def _lo_que_contesta(respuesta, *esperados):
    """La respuesta, comprobando antes el código: un 500 con el cuerpo vacío no dice nada útil."""
    assert respuesta.status_code in esperados or respuesta.status_code == 200, respuesta.text
    return respuesta.json()


@sin_servidor
class TestElRecorridoDeUnGastoDePuntaAPunta:
    """De apuntar el gasto a saber cuánto se debe: el camino entero, por la API."""

    def _un_gasto(self, cliente, cuenta, **cambios):
        datos = {
            "fecha": "2026-03-04",
            "concepto": "Abono 15-15-15",
            "categoria": "abono",
            "proveedor": "Cooperativa Agrícola de Peñaranda",
            "base_imponible": "600.00",
            "cuota_iva": "63.00",
            "importe": "663.00",
            "clave_de_reenvio": "movil-2026-03-04-1",
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/gastos", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def test_se_apunta_se_reparte_y_se_consulta_lo_que_se_debe(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """El recorrido entero: **guardar → asignar a tierras → consultar importe, repartos y pendiente**."""
        grande = crear_parcela(alias="El Prado", superficie_ha=4.0)
        pequena = crear_parcela(alias="La Vega", superficie_ha=2.0)
        apuntado = self._un_gasto(cliente, cuenta, campana_id=campana["id"])
        gasto = apuntado["gasto"]
        assert gasto["importe"] == "663.00"
        assert gasto["estado"] == gastos.SIN_PAGAR
        assert gasto["pendiente"] == "663.00"
        assert gasto["cuadre"]["cuadra"] is True
        # Acaba de apuntarse: todavía no está en ninguna tierra, y se dice.
        assert gasto["esta_sin_repartir"] is True

        repartido = cliente.post(
            f"/api/gastos/{gasto['id']}/repartos",
            headers=cuenta["cabeceras"],
            json={"metodo": "area", "destino_tipo": "tierra", "parcela_ids": [grande["id"], pequena["id"]]},
        )
        assert repartido.status_code == 200, repartido.text
        suyo = repartido.json()["gasto"]
        assert suyo["cuadre_del_reparto"]["repartido"] == "663.00"
        assert suyo["cuadre_del_reparto"]["sin_asignar"] == "0.00"
        assert suyo["cuadre_del_reparto"]["cuadra"] is True
        # Y el reparto es proporcional a las hectáreas: 4 ha y 2 ha se llevan 442 y 221.
        assert sorted(uno["importe"] for uno in suyo["repartos"]) == ["221.00", "442.00"]

        ficha = cliente.get(f"/api/gastos/{gasto['id']}", headers=cuenta["cabeceras"])
        assert ficha.status_code == 200
        assert ficha.json()["cuadre_del_reparto"]["total_conocido"] == "663.00"

    def test_un_pago_parcial_deja_el_pendiente_exacto_y_no_crea_otro_gasto(
        self, cliente, cuenta, campana
    ):
        """A06 por el lado de las salidas: 663 € de gasto y 200 € pagados → faltan 463 €, y sigue
        habiendo **un** gasto."""
        gasto = self._un_gasto(cliente, cuenta, campana_id=campana["id"])["gasto"]
        antes = cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()["gastos"]
        pago = cliente.post(
            "/api/gastos/pagos",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-03-20",
                "importe": "200.00",
                "proveedor": "Cooperativa Agrícola de Peñaranda",
                "clave_de_reenvio": "movil-pago-1",
                "aplicaciones": [{"gasto_id": gasto["id"]}],
            },
        )
        assert pago.status_code == 201, pago.text
        despues = cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()["gastos"]
        assert len(despues) == len(antes), "conciliar un pago ha creado un gasto"
        suyo = [uno for uno in despues if uno["id"] == gasto["id"]][0]
        assert suyo["pagado"] == "200.00"
        assert suyo["pendiente"] == "463.00"
        assert suyo["estado"] == gastos.PAGADO_EN_PARTE

    def test_reenviar_el_mismo_gasto_no_lo_duplica(self, cliente, cuenta, campana):
        primero = self._un_gasto(cliente, cuenta, campana_id=campana["id"])
        segundo = self._un_gasto(cliente, cuenta, campana_id=campana["id"])
        assert segundo["ya_estaba"] is True
        assert segundo["gasto"]["id"] == primero["gasto"]["id"]
        todos = cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()["gastos"]
        assert len(todos) == 1

    def test_un_gasto_sin_importe_se_guarda_y_lo_dice_sin_convertirlo_en_cero(
        self, cliente, cuenta, campana
    ):
        apuntado = self._un_gasto(
            cliente,
            cuenta,
            campana_id=campana["id"],
            concepto="Reparación del remolque",
            base_imponible=None,
            cuota_iva=None,
            importe=None,
            clave_de_reenvio="movil-2026-03-05-1",
        )
        gasto = apuntado["gasto"]
        assert gasto["importe"] is None
        assert gasto["texto_importe"] == ""
        assert gasto["estado"] == gastos.SIN_IMPORTE
        assert gasto["pendiente"] is None
        assert apuntado["avisos"], "no se dice que se ha guardado sin importe"
        # Y el pie de la cuenta lo dice, en vez de dar un total que parece completo.
        cuentas = cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()
        assert cuentas["cuenta"]["gastos_sin_importe"] == 1
        assert cuentas["cuenta"]["pendiente"] is None
        assert cuentas["coste_por_clase"]["sin_importe"] == 1

    def test_un_gasto_que_no_se_puede_repartir_se_queda_sin_asignar_y_se_dice(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """La trampa del ticket: falta la superficie de una tierra, así que **no se reparte a medias**."""
        con_superficie = crear_parcela(alias="El Prado", superficie_ha=4.0)
        sin_superficie = crear_parcela(alias="La Vega", superficie_ha=None)
        gasto = self._un_gasto(cliente, cuenta, campana_id=campana["id"])["gasto"]
        respuesta = cliente.post(
            f"/api/gastos/{gasto['id']}/repartos",
            headers=cuenta["cabeceras"],
            json={
                "metodo": "area",
                "destino_tipo": "tierra",
                "parcela_ids": [con_superficie["id"], sin_superficie["id"]],
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        suyo = cuerpo["gasto"]
        assert suyo["cuadre_del_reparto"]["repartido"] == "0.00"
        assert suyo["cuadre_del_reparto"]["sin_asignar"] == "663.00"
        assert suyo["cuadre_del_reparto"]["cuadra"] is True
        assert suyo["cuadre_del_reparto"]["no_se_reparte"] == gastos.NO_SE_REPARTE_PORQUE_FALTA_UN_PESO
        assert cuerpo["avisos"], "no se dice por qué no se ha podido repartir"

    def test_el_reparto_dice_donde_esta_el_centimo_del_redondeo(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """100 € entre tres tierras iguales: la suma tiene que ser exacta y el céntimo, visible."""
        tierras = [crear_parcela(alias=f"Tierra {indice}") for indice in range(3)]
        gasto = self._un_gasto(
            cliente,
            cuenta,
            campana_id=campana["id"],
            concepto="Seguro de la finca",
            importe="100.00",
            base_imponible=None,
            cuota_iva=None,
            clave_de_reenvio="movil-seguro-1",
        )["gasto"]
        respuesta = cliente.post(
            f"/api/gastos/{gasto['id']}/repartos",
            headers=cuenta["cabeceras"],
            json={"metodo": "area", "destino_tipo": "tierra", "parcela_ids": [t["id"] for t in tierras]},
        )
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["texto_residual"] == "0,01 €"
        assert cuerpo["residual_en"], "no se dice a qué trozo se le ha puesto el céntimo"
        importes = sorted(uno["importe"] for uno in cuerpo["gasto"]["repartos"])
        assert importes == ["33.33", "33.33", "33.34"]

    def test_anular_un_gasto_revierte_sus_efectos_y_deja_el_rastro(
        self, cliente, cuenta, campana, crear_parcela, db_sesion
    ):
        """Anular no borra: el gasto queda tachado con su motivo, sus repartos dejan de contar y el
        dinero que lo saldaba vuelve a estar sin conciliar."""
        parcela = crear_parcela(alias="El Prado", superficie_ha=4.0)
        gasto = self._un_gasto(cliente, cuenta, campana_id=campana["id"])["gasto"]
        cliente.post(
            f"/api/gastos/{gasto['id']}/repartos",
            headers=cuenta["cabeceras"],
            json={"metodo": "area", "destino_tipo": "tierra", "parcela_ids": [parcela["id"]]},
        )
        cliente.post(
            "/api/gastos/pagos",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-03-20", "importe": "200.00", "aplicaciones": [{"gasto_id": gasto["id"]}]},
        )
        anulado = cliente.post(
            f"/api/gastos/{gasto['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué: era de otra finca"},
        )
        assert anulado.status_code == 200, anulado.text
        suyo = anulado.json()["gasto"]
        assert suyo["anulado"] is True
        assert suyo["motivo_anulacion"] == "Me equivoqué: era de otra finca"
        assert suyo["repartos"] == [], "los repartos siguen vivos después de anular el gasto"
        cuentas = cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()
        assert cuentas["cuenta"]["coste_conocido"] == "0.00"
        assert cuentas["sin_conciliar"], "el dinero no ha vuelto a estar sin conciliar"
        # Y el rastro: el motivo, la anulación y la vuelta del dinero.
        from app import models

        acciones = {
            fila.accion
            for fila in db_sesion.query(models.Auditoria)
            .filter(models.Auditoria.entidad == "gasto")
            .all()
        }
        assert "anular" in acciones

    def test_deshacer_una_conciliacion_no_borra_el_pago(self, cliente, cuenta, campana):
        gasto = self._un_gasto(cliente, cuenta, campana_id=campana["id"])["gasto"]
        pago = cliente.post(
            "/api/gastos/pagos",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-03-20", "importe": "200.00", "aplicaciones": [{"gasto_id": gasto["id"]}]},
        ).json()["pago"]
        aplicacion = pago["aplicaciones"][0]["id"]
        deshecho = cliente.delete(
            f"/api/gastos/pagos/{pago['id']}/aplicaciones/{aplicacion}",
            headers=cuenta["cabeceras"],
        )
        assert deshecho.status_code == 200, deshecho.text
        suyo = deshecho.json()["pago"]
        # El pago sigue apuntado con su importe entero y vuelve a estar sin conciliar.
        assert suyo["importe"] == "200.00"
        assert suyo["sin_conciliar"] == "200.00"
        assert suyo["aplicaciones"] == []
        # Y el gasto vuelve a estar pendiente entero.
        ficha = cliente.get(f"/api/gastos/{gasto['id']}", headers=cuenta["cabeceras"]).json()
        assert ficha["pagado"] == "0.00"
        assert ficha["pendiente"] == "663.00"

    def test_el_margen_no_se_calcula_si_falta_un_importe(self, cliente, cuenta, campana):
        """Regla del contrato: «no construir un margen con datos que faltan»."""
        self._un_gasto(cliente, cuenta, campana_id=campana["id"], cultivo="Trigo")
        self._un_gasto(
            cliente,
            cuenta,
            campana_id=campana["id"],
            concepto="Reparación del remolque",
            cultivo="Trigo",
            importe=None,
            base_imponible=None,
            cuota_iva=None,
            clave_de_reenvio="movil-2026-03-06-1",
        )
        cuentas = cliente.get(
            f"/api/gastos?campana_id={campana['id']}", headers=cuenta["cabeceras"]
        ).json()
        trigo = cuentas["margenes"]["Trigo"]
        assert trigo["completo"] is False
        assert trigo["margen"] is None
        assert trigo["costes_que_no_se"] == 1
        assert trigo["coste_conocido"] == "663.00"

    def test_las_ayudas_tienen_sus_tres_cifras_y_la_prevision_no_es_ingreso(self, cliente, cuenta, campana):
        ayuda = cliente.post(
            "/api/gastos/subvenciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "concepto": "Ayuda a la cosecha de cereal",
                "organismo": "Junta de Castilla y León",
                "importe_previsto": "3000.00",
            },
        )
        assert ayuda.status_code == 201, ayuda.text
        vista = ayuda.json()["subvencion"]
        assert vista["estado"] == gastos.PREVISTA
        assert vista["cuenta_como_ingreso"] is False
        assert ayuda.json()["avisos"], "no se dice que una ayuda prevista no es un ingreso"
        listado = cliente.get("/api/gastos/subvenciones", headers=cuenta["cabeceras"]).json()
        assert listado["ingreso_cobrado"] == "0.00"
        assert listado["importe_previsto"] == "3000.00"

    def test_una_inversion_no_entra_en_el_coste_de_la_campana(self, cliente, cuenta, campana):
        cliente.post(
            "/api/gastos/inversiones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-01",
                "concepto": "Tractor usado",
                "categoria": "maquinaria",
                "importe": "24000.00",
            },
        )
        cuentas = cliente.get("/api/gastos", headers=cuenta["cabeceras"]).json()
        assert cuentas["cuenta"]["coste_conocido"] == "0.00"
        assert len(cuentas["inversiones"]) == 1
        assert cuentas["inversiones"][0]["texto_sin_asignar"] == "24.000,00 €"

    def test_el_gasto_de_otra_finca_no_se_ve(self, cliente, cuenta, crear_cuenta):
        from tests.conftest import DATOS_CUENTA

        otro = crear_cuenta("otro@ejemplo.test", nombre="Otro", nif="12345678Z")
        gasto = cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={"concepto": "Gasóleo", "importe": "100.00", "clave_de_reenvio": "aislamiento-1"},
        ).json()["gasto"]
        respuesta = cliente.get(f"/api/gastos/{gasto['id']}", headers=otro["cabeceras"])
        # **404 y no 403**: así no se cuenta si el identificador existe en otra finca.
        assert respuesta.status_code == 404, respuesta.text
        del DATOS_CUENTA

    def test_las_cinco_rutas_de_palabra_fija_llegan_a_su_funcion(self, cliente, cuenta):
        """`/gastos/{id}` va la última a propósito: si fuera antes, «pagos» se leería como un id.

        Sin esta prueba, un cambio de orden en el fichero haría que `/api/gastos/pagos` contestara
        «revisa lo que has escrito» en vez de dar la lista, y nadie se enteraría hasta el día que
        alguien abriera esa pantalla.
        """
        for ruta in (
            "/api/gastos",
            "/api/gastos/avisos",
            "/api/gastos/inversiones",
            "/api/gastos/pagos",
            "/api/gastos/subvenciones",
            "/api/gastos/cuadre",
            "/api/gastos/que-falta",
        ):
            respuesta = cliente.get(ruta, headers=cuenta["cabeceras"])
            assert respuesta.status_code == 200, f"{ruta} contesta {respuesta.status_code}"

    def test_los_gastos_de_un_gasto_sin_importe_no_se_pueden_repartir(self, cliente, cuenta, campana, crear_parcela):
        parcela = crear_parcela(alias="El Prado", superficie_ha=4.0)
        gasto = self._un_gasto(
            cliente,
            cuenta,
            campana_id=campana["id"],
            importe=None,
            base_imponible=None,
            cuota_iva=None,
            clave_de_reenvio="movil-sin-importe-reparto",
        )["gasto"]
        respuesta = cliente.post(
            f"/api/gastos/{gasto['id']}/repartos",
            headers=cuenta["cabeceras"],
            json={"metodo": "area", "destino_tipo": "tierra", "parcela_ids": [parcela["id"]]},
        )
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["gasto"]["cuadre_del_reparto"]["no_se_reparte"] == (
            gastos.NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE
        )
        assert cuerpo["avisos"], "no se dice que sin importe no se puede repartir"


@sin_servidor
class TestElCosteDeLasAveriasPorLaApi:
    """El coste de las averías, que el T14 dejó declarado como de este ticket."""

    def test_la_reparacion_es_un_gasto_que_dice_de_que_averia_sale(
        self, cliente, cuenta, campana
    ):
        maquina = cliente.post(
            "/api/maquinaria",
            headers=cuenta["cabeceras"],
            json={"nombre": "El Landini", "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
        )
        assert maquina.status_code == 201, maquina.text
        averia = cliente.post(
            f"/api/maquinaria/{maquina.json()['id']}/averias",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-04-01", "que_paso": "Se rompió el eje del ventilador", "resuelta": False},
        )
        assert averia.status_code == 201, averia.text
        cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "concepto": "Reparación del eje del ventilador",
                "categoria": "reparacion",
                "averia_id": averia.json()["id"],
                "maquina_id": maquina.json()["id"],
                "importe": "900.00",
                "clave_de_reenvio": "reparacion-1",
            },
        )
        coste = cliente.get("/api/gastos/averias", headers=cuenta["cabeceras"]).json()
        assert len(coste["averias"]) == 1
        suya = coste["averias"][0]
        assert suya["coste"] == "900.00"
        assert suya["texto_coste"] == "900,00 €"
        # **Y estar arreglada es otra cosa**: la avería sigue sin arreglar aunque la reparación esté
        # apuntada y pagada. Son dos datos distintos y el programa no los mezcla.
        assert suya["sigue_sin_arreglar"] is True

    def test_una_averia_sin_ningun_gasto_no_cuesta_cero(self, cliente, cuenta):
        maquina = cliente.post(
            "/api/maquinaria",
            headers=cuenta["cabeceras"],
            json={"nombre": "El Landini", "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
        ).json()
        averia = cliente.post(
            f"/api/maquinaria/{maquina['id']}/averias",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-04-01", "que_paso": "Se rompió el eje", "resuelta": None},
        ).json()
        coste = cliente.get("/api/gastos/averias", headers=cuenta["cabeceras"]).json()
        # No hay ninguna fila porque no hay ningún gasto apuntado: **no se inventa un cero**.
        assert all(uno["averia_id"] != averia["id"] for uno in coste["averias"])
        assert coste["reparaciones_sin_averia"]["cuantos"] == 0

# ==========================================================================
# El importe, como lo escribe un agricultor (06/10/2026)
# ==========================================================================
#
# **Estas dos pruebas se añadieron al recorrer el recorrido 2 en un navegador de verdad**, y el defecto
# era de los que dejan al agricultor sin poder trabajar: la pantalla manda el importe **tal y como se
# teclea**, así que un «254,10» —que es como lo escribe cualquiera aquí, y lo que da el teclado decimal
# del móvil— llegaba al servidor y Pydantic lo rechazaba con un 422
# («Input should be a valid decimal»). El agricultor veía «No se ha podido» y **no podía apuntar el
# gasto**. El proyecto ya tenía la regla escrita (`dinero.de_texto`: «se acepta lo que escribe un
# agricultor»), pero los importes de este ticket se declararon como `Decimal` a secas, así que no
# pasaban por ella. Ahora todos los importes de entrada usan el mismo tipo (`schemas.ImporteDeEntrada`).


class TestElImporteComoLoEscribeUnAgricultor:
    def test_un_importe_con_coma_se_entiende_y_se_guarda_exacto(self, cliente, cuenta):
        """«254,10» son doscientos cincuenta y cuatro euros con diez céntimos, y se guarda así."""
        respuesta = cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={
                "concepto": "El gasóleo de la siega",
                "categoria": "gasoleo",
                "importe": "254,10",
                "base_imponible": "1.234,56",
            },
        )
        assert respuesta.status_code == 201, (
            f"un importe escrito con coma no se ha aceptado: {respuesta.text}"
        )
        suyo = respuesta.json()["gasto"]
        # **Exacto**: el texto decimal llega al `Decimal` sin pasar por coma flotante.
        assert suyo["importe"] == "254.10"
        assert suyo["texto_importe"] == "254,10 €"

        # Y queda guardado de verdad: se lee de vuelta con el mismo número. (`GET /api/gastos/<id>` sí
        # devuelve el gasto directo: el envoltorio de `gasto` es del alta y de la corrección.)
        leido = cliente.get(f"/api/gastos/{suyo['id']}", headers=cuenta["cabeceras"]).json()
        assert leido["importe"] == "254.10"

    def test_un_numero_de_coma_flotante_se_sigue_rechazando(self, cliente, cuenta):
        """Y la otra mitad, que es la que el proyecto no quiere perder: un `float` de JSON ya perdió
        céntimos antes de llegar, así que **no vale** — el dinero viaja como texto decimal."""
        respuesta = cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={"concepto": "El gasóleo", "categoria": "gasoleo", "importe": 254.10},
        )
        assert respuesta.status_code == 422, (
            "un importe de coma flotante se ha aceptado: `Decimal(254.10)` no es 254,10"
        )
        assert "coma flotante" in respuesta.text or "float" in respuesta.text.lower()

    def test_vacio_sigue_siendo_no_se_sabe(self, cliente, cuenta):
        """Un importe que no se sabe **no es un cero**: la regla del encargo, y la que más veces se
        rompe al tocar esto."""
        respuesta = cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={"concepto": "Sin saber cuánto", "categoria": "otro"},
        )
        assert respuesta.status_code == 201, respuesta.text
        suyo = respuesta.json()["gasto"]
        assert suyo["importe"] is None, "un gasto sin importe ha salido con un cero"
        assert suyo["texto_importe"] in (None, ""), "se ha escrito un importe que no consta"
        assert suyo["texto_pendiente"] in (None, ""), "lo que falta por pagar de un importe que no consta"
