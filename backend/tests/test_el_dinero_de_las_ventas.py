import re
"""El dinero de lo que se vende (T12, E6, 03/10/2026).

Lo que este fichero comprueba, y por qué es lo más importante de la entrega:

  · **Los dos casos de aceptación del contrato** (§6): **A06** (factura de 121 €, pago de 40 € → pendiente
    81 €, y un segundo importe conciliado **no crea una segunda factura**) y **A08** (venta de 8.000 kg
    **sin precio** → cantidad conocida, importe pendiente, **no ingreso cero**).
  · **Que el dinero no pierda céntimos**, con números que **fallarían** si se usara coma flotante
    (`0,10 + 0,20`; un 21 % sobre 121,00; un 80,999 que tiene que redondearse a 81,00; un precio de
    0,2350 €/kg por 42.000 kg). No es una precaución teórica: `0,1 + 0,2` en coma flotante da
    `0,30000000000000004`, y un total que no cuadra con la suma de sus filas es lo primero que hace
    desconfiar de un programa de cuentas.
  · **Que el dinero se cuenta una sola vez**, por las tres puertas por las que se duplica: agrupar
    entregas en una factura, reenviar la misma petición (el móvil sin cobertura) y cobrar.
  · **Que el resumen cuadra con el detalle**: lo que dice el pie de la tabla es exactamente la suma de las
    filas que se enseñan, con datos representativos (varias campañas, importes incompletos, un pago
    parcial, entregas agrupadas y una devolución).
  · **Que nada de otra finca se ve ni se enlaza** (el caso A13 del contrato).
  · Y **que lo que se emite aquí no se presenta como un documento fiscal**: el contrato dice que la emisión
    fiscal completa «requiere especificación normativa propia antes de activarse como tal», así que lo que
    hay es una factura **nuestra**, de gestión, y hay pruebas que impiden que alguien la disfrace de otra
    cosa.

Las cuentas puras (sin base de datos) están en `app/dinero.py` y `app/ventas.py`, y se prueban aquí
también: son las que hacen que el resto sea verdad.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select

from app import dinero, models, textos, ventas
from app.database import engine


# --------------------------------------------------------------------------
# El dinero, sin base de datos: los números que fallarían con coma flotante
# --------------------------------------------------------------------------


class TestElDineroNoPierdeCentimos:
    """Las cuentas puras, con los números que distinguen un cálculo exacto de uno de coma flotante.

    Es la primera clase del fichero a propósito: si esto estuviera mal, todo lo demás daría igual.
    """

    def test_diez_mas_veinte_centimos_son_treinta(self):
        """`0,1 + 0,2` es **el** número que distingue `Decimal` de `float`, y en un programa de cuentas
        aparece todos los días (dos apuntes de diez y veinte céntimos).

        En coma flotante da `0,30000000000000004`: si esto fallara, el total de una pantalla y la suma de
        sus filas empezarían a separarse por unos céntimos y nadie sabría por qué.
        """
        assert dinero.suma(Decimal("0.10"), Decimal("0.20")) == Decimal("0.30")
        assert dinero.a_texto(dinero.suma(Decimal("0.10"), Decimal("0.20"))) == "0.30"
        # Y el mismo caso sumando muchas veces, que es como se acumula el error de verdad.
        muchos = dinero.suma(*[Decimal("0.10")] * 10)
        assert muchos == Decimal("1.00"), muchos

    def test_el_veintiuno_por_cien_de_ciento_veintiuno(self):
        """El 21 % sobre 121,00 son 25,41 exactos: un impuesto calculado al céntimo.

        Se calcula aquí aunque el programa no emita impuestos (esto es la cuenta de gestión del
        agricultor): es el número de referencia de la aritmética decimal del A06, que es un 121.
        """
        assert dinero.producto(Decimal("121.00"), Decimal("0.21")) == Decimal("25.41")
        assert dinero.a_texto(dinero.producto(Decimal("121.00"), Decimal("0.21"))) == "25.41"

    def test_un_pendiente_de_ochenta_con_novecientos_noventa_y_nueve_milesimas(self):
        """`80,999` no es 80,99 ni 81 a ojo: se redondea **al céntimo y hacia arriba**.

        Es el caso que el ticket pide probar con un número que falle si está mal, y falla por dos caminos:
        si no se redondeara, el pendiente saldría con tres decimales (una cifra que no es dinero); y si se
        redondeara con la regla por defecto de Python (al par), `0,125` daría `0,12`, que no es lo que
        espera quien echa la cuenta a mano.
        """
        assert dinero.redondea(Decimal("80.999")) == Decimal("81.00")
        assert dinero.a_texto(Decimal("80.999")) == "81.00"
        # La regla, con el número que distingue «al alza» de «al par».
        assert dinero.redondea(Decimal("0.125")) == Decimal("0.13"), "ha redondeado al par"
        assert dinero.redondea(Decimal("0.135")) == Decimal("0.14")
        assert dinero.redondea(Decimal("0.145")) == Decimal("0.15")

    def test_un_precio_pactado_con_cuatro_cifras_no_se_redondea_antes_de_multiplicar(self):
        """`0,2350 €/kg × 42.000 kg` son 9.870,00 €, y redondear el precio antes daría 10.080,00 €.

        Doscientos diez euros de diferencia, y en el sentido que perjudica al agricultor. Por eso el
        precio se guarda con las cifras que se pactaron y **lo único que se redondea es el importe**, una
        sola vez, al final.
        """
        assert dinero.producto(Decimal("42000"), Decimal("0.2350")) == Decimal("9870.00")
        mal_hecho = dinero.producto(Decimal("42000"), dinero.redondea(Decimal("0.2350")))
        assert mal_hecho == Decimal("10080.00"), "el redondeo pronto no da lo que se esperaba"
        assert dinero.producto(Decimal("42000"), Decimal("0.2350")) != mal_hecho

    def test_un_importe_no_se_acepta_como_numero_de_coma_flotante(self):
        """Y no es una precaución de adorno: es la puerta que impide que el `float` entre por atrás.

        Un `2.35` escrito en el código (o un número de JSON en vez de una cadena) ya perdió la cuenta:
        `Decimal(2.35)` es `2,350000000000000088817841970012523…`. Aquí se rechaza con un mensaje que dice
        qué mandar.
        """
        with pytest.raises(dinero.ErrorDeDinero):
            dinero.a_decimal(2.35)
        with pytest.raises(dinero.ErrorDeDinero):
            dinero.suma(Decimal("1.00"), 0.1)
        with pytest.raises(dinero.ErrorDeDinero):
            dinero.resta(Decimal("1.00"), 0.1)
        # Y los tres que sí valen: el texto (lo que viaja), el entero y el propio `Decimal`.
        assert dinero.a_decimal("2.35") == Decimal("2.35")
        assert dinero.a_decimal(2) == Decimal("2")
        assert dinero.a_decimal(Decimal("2.35")) == Decimal("2.35")

    def test_un_importe_escrito_a_mano_se_lee_como_se_escribe_en_espana(self):
        """«1.234,56» y «0,235» —y el cero delante no es un separador de miles—."""
        assert dinero.de_texto("1.234,56") == Decimal("1234.56")
        assert dinero.de_texto("121,50") == Decimal("121.50")
        # **La excepción que hace falta para un precio**: «0.235» son veintitrés céntimos y medio el kilo,
        # no doscientos treinta y cinco euros. Sin esto, un precio pactado con tres cifras se guardaría
        # multiplicado por mil.
        assert dinero.de_texto("0.235") == Decimal("0.235")
        # Y la regla del lector de facturas del programa para el resto: «1.234» son mil doscientos treinta y
        # cuatro (que es como se escribe un importe en un papel español).
        assert dinero.de_texto("1.234") == Decimal("1234")
        # Lo que no es un número no se convierte en cero: se dice.
        with pytest.raises(dinero.ErrorDeDinero):
            dinero.de_texto("mil euros")
        # Y el hueco es «no se sabe», no cero.
        assert dinero.de_texto("") is None
        assert dinero.de_texto(None) is None

    def test_lo_que_no_se_sabe_no_es_cero_al_restar(self):
        """Restar no se puede inventar: sin importe conocido, el pendiente **no se sabe**."""
        assert dinero.resta(None, Decimal("40.00")) is None
        assert dinero.resta(Decimal("121.00"), None) is None
        assert ventas.pendiente_de(None, Decimal("40.00")) is None
        # Y con importe, el pendiente nunca es negativo: si se cobró de más, sobra dinero, no falta.
        assert ventas.pendiente_de(Decimal("121.00"), Decimal("200.00")) == Decimal("0.00")

    def test_el_importe_se_enseña_como_se_escribe_un_importe_aqui(self):
        assert dinero.formatea(Decimal("1234.5")) == "1.234,50 €"
        assert dinero.formatea(Decimal("9870.00")) == "9.870,00 €"
        # **Lo que no se sabe se enseña vacío, no como 0,00 €**: son cosas distintas y confundirlas es
        # decirle al agricultor que no le deben nada cuando lo que pasa es que no se sabe.
        assert dinero.formatea(None) == ""

    def test_el_importe_va_y_vuelve_de_la_base_sin_perder_ni_un_centimo(self, cliente, cuenta, campana, parcela):
        """La prueba que cierra el círculo: **lo guardado en la base es exacto**.

        El importe se guarda como **texto decimal canónico** precisamente porque SQLite no tiene un tipo
        decimal y un `Numeric` de SQLAlchemy allí acabaría pasando por `float` (el dialecto lo dice:
        `supports_native_decimal = False`). Aquí se comprueba de verdad: se guardan importes con los
        céntimos más incómodos, se vuelven a leer y se comparan.

        **Y se comprueba en los dos motores** (revisión del T12): esta prueba empezaba comprobando que el
        motor fuera SQLite —una línea con `engine.dialect.name`—, así que en PostgreSQL, que es el motor
        de producción, se ponía en rojo por construcción y el viaje de ida y vuelta del importe **no se
        comprobaba allí**. Lo único que era sintaxis de SQLite era el `typeof`; el tipo guardado se
        pregunta a cada motor con lo suyo, y lo que importa —que la columna guarde texto y que el valor
        vuelva exacto— se mide igual en los dos.
        """
        creadas = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "0.10",
            },
        ).json()
        for importe in ("0.20", "9870.00", "1234.56", "0.01"):
            respuesta = cliente.post(
                "/api/ventas",
                headers=cuenta["cabeceras"],
                json={
                    "campana_id": campana["id"],
                    "fecha": "2026-07-11",
                    "producto": "Trigo blando",
                    "cantidad": 1000.0,
                    "unidad": "kg",
                    "importe": importe,
                },
            )
            assert respuesta.status_code == 201, respuesta.text
            assert respuesta.json()["importe"] == importe, (
                f"el importe {importe} ha vuelto como {respuesta.json()['importe']}"
            )
        # Y en la base está como **texto**, no como número de coma flotante: se mira con una consulta en
        # crudo, sin pasar por el tipo de SQLAlchemy, porque es el dato guardado lo que se está comprobando.
        from sqlalchemy import text as sql

        # El tipo guardado, **preguntado a cada motor con su sintaxis** (revisión del T12): `typeof` es de
        # SQLite y en PostgreSQL el mismo dato se pregunta con `pg_typeof`. Lo que se exige es lo mismo en
        # los dos: que la columna guarde **texto** y no un número de coma flotante.
        if engine.dialect.name == "postgresql":
            la_del_tipo = "SELECT pg_typeof(importe)::text FROM ventas_de_cosecha WHERE id = :id"
            el_tipo_de_texto = "character varying"
        else:
            la_del_tipo = "SELECT typeof(importe) FROM ventas_de_cosecha WHERE id = :id"
            el_tipo_de_texto = "text"

        with _sesion() as sesion:
            guardado = sesion.execute(
                sql("SELECT importe FROM ventas_de_cosecha WHERE id = :id"), {"id": creadas["id"]}
            ).scalar()
            tipo = sesion.execute(sql(la_del_tipo), {"id": creadas["id"]}).scalar()
        assert guardado == "0.10", f"el importe se ha guardado como {guardado!r}"
        assert tipo == el_tipo_de_texto, f"la columna del importe es de tipo {tipo} en la base"

    def test_la_suma_de_dos_entregas_de_diez_y_veinte_centimos_da_treinta(self, cliente, cuenta, campana):
        """El mismo `0,10 + 0,20` pero pasando por la base y por la tabla: es donde se vería el error."""
        for importe in ("0.10", "0.20"):
            cliente.post(
                "/api/ventas",
                headers=cuenta["cabeceras"],
                json={
                    "campana_id": campana["id"],
                    "fecha": "2026-07-10",
                    "producto": "Trigo blando",
                    "cantidad": 1000.0,
                    "unidad": "kg",
                    "importe": importe,
                },
            )
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        assert tabla["totales"]["importe"] == "0.30", tabla["totales"]


def _sesion():
    """Una sesión del motor de la suite, para mirar lo que hay guardado **tal y como se guardó**."""
    from sqlalchemy.orm import Session

    return Session(engine)


# --------------------------------------------------------------------------
# A08 — la venta sin precio: cantidad conocida, importe pendiente, no ingreso cero
# --------------------------------------------------------------------------


class TestA08LaVentaSinPrecio:
    """El caso A08 del contrato, palabra por palabra: «Venta con 8.000 kg y sin precio → Cantidad conocida,
    importe pendiente; **no ingreso cero**».

    Es el caso que separa un programa de cuentas de una hoja de cálculo: la tentación es poner un `0` en el
    importe «para que sume», y con eso el año acaba con un ingreso de cero euros por una partida que vale
    dinero.
    """

    def _venta_sin_precio(self, cliente, cuenta, campana):
        respuesta = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 8000.0,
                "unidad": "kg",
                "comprador": "Cooperativa Agrícola de Peñaranda",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def test_la_cantidad_se_sabe_y_el_importe_no(self, cliente, cuenta, campana):
        venta = self._venta_sin_precio(cliente, cuenta, campana)
        # La cantidad, sí.
        assert venta["cantidad"] == 8000.0
        assert venta["texto_cantidad"] == "8.000,00 kg"
        # Y el importe, **no**: `None` no es `0`.
        assert venta["importe"] is None
        assert venta["importe_total"] is None
        assert venta["texto_importe"] == ""
        # El estado lo dice con palabras, y no hay nada que cobrar porque no está facturada.
        assert venta["estado"] == "sin_importe"
        assert venta["etiqueta_estado"] == textos.VENTA["estado_sin_importe"]
        assert venta["facturada"] is False
        assert venta["pendiente"] is None

    def test_no_aparece_como_ingreso_de_cero_euros(self, cliente, cuenta, campana):
        """Ni en el resumen del año, ni en el pie de la tabla, ni en el total de nada."""
        self._venta_sin_precio(cliente, cuenta, campana)
        resumen = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        # El importe conocido sigue siendo cero **porque no hay ninguno conocido**, y el resumen dice que a
        # una entrega le falta: es la diferencia entre «no hay importes» y «hay un importe de cero».
        assert resumen["dinero"]["importe"] == "0.00"
        assert resumen["dinero"]["sin_importe"] == 1
        assert resumen["dinero"]["entregas"] == 1
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        assert tabla["totales"]["sin_importe"] == 1
        # Y el pie lo dice con palabras, sin que nadie tenga que adivinarlo.
        assert tabla["avisos"] == [textos.VENTA["faltan_importes_una"]]
        # La fila enseña la cantidad y deja el importe **vacío** (no «0,00 €»).
        fila = tabla["filas"][0]
        assert fila["cantidad"] == "8.000,00 kg"
        assert fila["importe"] == ""
        assert fila["importe_conocido"] is False

    def test_una_entrega_sin_importe_no_se_puede_facturar_y_se_dice_que_hacer(
        self, cliente, cuenta, campana
    ):
        """Y no se deja al agricultor sin salida: el aviso dice que hay que poner el importe."""
        venta = self._venta_sin_precio(cliente, cuenta, campana)
        respuesta = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [venta["id"]]},
        )
        assert respuesta.status_code == 422
        assert "importe" in respuesta.json()["detail"].lower()

    def test_cuando_se_sabe_el_precio_la_cuenta_se_hace_sola(self, cliente, cuenta, campana):
        """Y el importe calculado es exacto: 8.000 kg × 0,2350 €/kg = 1.880,00 €."""
        venta = self._venta_sin_precio(cliente, cuenta, campana)
        respuesta = cliente.put(
            f"/api/ventas/{venta['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 8000.0,
                "unidad": "kg",
                "comprador": "Cooperativa Agrícola de Peñaranda",
                "precio_unitario": "0.2350",
                "vencimiento": "2026-09-10",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert cuerpo["importe_total"] == "1880.00"
        assert cuerpo["texto_importe_total"] == "1.880,00 €"
        assert cuerpo["precio_unitario"] == "0.2350"
        assert cuerpo["vencimiento"] == "2026-09-10"
        # Y ya no está en el grupo de «sin importe»: el hueco se ha cerrado.
        assert cuerpo["estado"] == "sin_facturar"
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        assert tabla["totales"]["sin_importe"] == 0
        assert tabla["avisos"] == []


# --------------------------------------------------------------------------
# A06 — la factura de 121 y el pago de 40
# --------------------------------------------------------------------------


class TestA06ElPagoParcial:
    """El caso A06 del contrato: «Factura 121 EUR, pago 40 EUR → Pendiente 81; **segundo importe conciliado
    no crea segunda factura**».

    Las dos mitades, una por una: el pendiente exacto y que cobrar **no crea documentos**.
    """

    def _una_factura_de_121(self, cliente, cuenta, campana):
        """Una entrega de 121,00 € y su factura nuestra. Devuelve `(entrega, factura)`."""
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
                "comprador": "Cooperativa Agrícola de Peñaranda",
            },
        ).json()
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-07-20",
                "numero": "F-2026-1",
                "cliente": "Cooperativa Agrícola de Peñaranda",
                "entregas": [entrega["id"]],
            },
        ).json()
        assert factura["importe_total"] == "121.00"
        return entrega, factura

    def test_con_la_factura_hecha_el_pendiente_es_lo_facturado(self, cliente, cuenta, campana):
        _entrega, factura = self._una_factura_de_121(cliente, cuenta, campana)
        assert factura["pendiente"] == "121.00"
        assert factura["cobrado"] == "0.00"
        assert factura["texto_pendiente"] == "121,00 €"

    def test_un_pago_de_40_deja_81_pendientes(self, cliente, cuenta, campana):
        """El número del contrato, calculado con `Decimal` y dicho con palabras al agricultor."""
        _entrega, factura = self._una_factura_de_121(cliente, cuenta, campana)
        respuesta = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "40.00", "factura_emitida_id": factura["id"]},
        )
        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        # 121 − 40 = 81, y el pendiente se calcula, no se guarda.
        assert cuerpo["factura"]["pendiente"] == "81.00"
        assert cuerpo["factura"]["cobrado"] == "40.00"
        # Y el aviso lo dice con el número exacto y con las dos cifras de la factura.
        assert "40,00 €" in cuerpo["avisos"][0] and "81,00 €" in cuerpo["avisos"][0], cuerpo["avisos"]
        # Lo imputado de este cobro es lo que se debía: ni un céntimo más.
        assert cuerpo["cobro"]["importe_imputado"] == "40.00"
        assert cuerpo["cobro"]["texto_sin_asignar"] == ""

    def test_un_segundo_importe_conciliado_no_crea_una_segunda_factura(self, cliente, cuenta, campana):
        """**La segunda mitad del A06, y la que más fácil se rompe.**

        Se cuentan las facturas **antes y después** de cobrar los 81 que faltaban: tiene que haber una sola.
        Un programa que «emitiera» una factura al registrar un pago duplicaría los ingresos sin que nadie lo
        notara hasta cuadrar el año.
        """
        _entrega, factura = self._una_factura_de_121(cliente, cuenta, campana)
        cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "40.00", "factura_emitida_id": factura["id"]},
        )
        antes = len(cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json())
        assert antes == 1

        # El segundo importe, conciliado por el mismo camino que usaría la pantalla.
        segundo = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-20", "importe": "81.00", "factura_emitida_id": factura["id"]},
        )
        assert segundo.status_code == 201, segundo.text
        despues = cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json()
        assert len(despues) == antes == 1, "cobrar ha creado una factura nueva"
        assert despues[0]["id"] == factura["id"], "la factura que hay no es la de antes"
        assert despues[0]["pendiente"] == "0.00"
        assert despues[0]["estado"] == "cobrada"
        assert despues[0]["texto_pendiente"] == "0,00 €"
        # Y sus dos cobros están los dos, cada uno con lo suyo.
        assert [c["importe"] for c in despues[0]["cobros"]] == ["40.00", "81.00"]
        # El resumen del año cuadra: 121 facturados, 121 cobrados, nada pendiente.
        resumen = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        assert resumen["dinero"]["facturado"] == "121.00"
        assert resumen["dinero"]["cobrado"] == "121.00"
        assert resumen["dinero"]["pendiente"] == "0.00"

    def test_un_cobro_mas_grande_que_lo_que_se_debe_no_deja_el_pendiente_en_negativo(
        self, cliente, cuenta, campana
    ):
        """Si entra más dinero del que se debe, la factura queda a cero y **el sobrante se dice aparte**.

        Lo que no se hace es dejar la factura en `-19,00 €`: un pendiente negativo no se puede sumar con los
        demás y no significa nada para quien lo lee.
        """
        _entrega, factura = self._una_factura_de_121(cliente, cuenta, campana)
        respuesta = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "140.00", "factura_emitida_id": factura["id"]},
        ).json()
        assert respuesta["factura"]["pendiente"] == "0.00"
        assert respuesta["factura"]["cobrado"] == "121.00"
        assert respuesta["cobro"]["importe_imputado"] == "121.00"
        assert respuesta["cobro"]["sin_asignar"] == "19.00"
        # Y se dice: un sobrante callado sería dinero que aparece de la nada al cuadrar el año.
        assert "19,00 €" in respuesta["avisos"][0], respuesta["avisos"]

    def test_conciliar_y_deshacer_no_borra_el_movimiento(self, cliente, cuenta, campana):
        """«Deshacer la conciliación no borra el movimiento original» (contrato §4, S14).

        El cobro sigue apuntado con su importe y su fecha; lo único que cambia es contra qué factura va. Y
        la factura vuelve a deber lo que debía, que es la verdad.
        """
        _entrega, factura = self._una_factura_de_121(cliente, cuenta, campana)
        cobro = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "40.00", "factura_emitida_id": factura["id"]},
        ).json()["cobro"]
        # Se le quita la asignación.
        respuesta = cliente.post(
            f"/api/cobros/{cobro['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={"factura_emitida_id": None},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["cobro"]["id"] == cobro["id"], "el cobro se ha ido"
        assert respuesta.json()["cobro"]["importe"] == "40.00", "el importe del cobro ha cambiado"
        assert respuesta.json()["cobro"]["factura_emitida_id"] is None
        # Y la factura vuelve a los 121 pendientes.
        factura_otra_vez = cliente.get(
            f"/api/facturas-emitidas/{factura['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert factura_otra_vez["pendiente"] == "121.00"
        # Y se puede volver a conciliar con la misma factura, que es lo que hace falta cuando uno se
        # equivoca al quitarla.
        otra_vez = cliente.post(
            f"/api/cobros/{cobro['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={"factura_emitida_id": factura["id"]},
        ).json()
        assert otra_vez["factura"]["pendiente"] == "81.00"

    def test_un_cobro_sin_factura_queda_sin_asignar_y_no_se_pierde(self, cliente, cuenta, campana):
        """«Pagos sin factura quedan por conciliar» (contrato §4): el dinero entra y espera."""
        self._una_factura_de_121(cliente, cuenta, campana)
        cobro = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "50.00", "cliente": "Un cliente", "referencia": "TRANSF 1"},
        ).json()["cobro"]
        assert cobro["factura_emitida_id"] is None
        assert cobro["importe"] == "50.00"
        assert cobro["sin_asignar"] == "50.00"
        sin_asignar = cliente.get("/api/cobros?solo=sin_asignar", headers=cuenta["cabeceras"]).json()
        assert [c["id"] for c in sin_asignar] == [cobro["id"]]

    def test_el_rastro_del_cobro_dice_lo_que_paso_y_con_que_etiqueta(self, cliente, cuenta, campana):
        """Conciliar y deshacer dejan su fila en el rastro, **cada uno con su etiqueta**.

        El rastro es lo que se mira en una inspección —o dentro de dos años, cuando nadie se acuerda de por
        qué esa factura dejó de deber—, así que lo que se comprueba es que la etiqueta dice **qué pasó** y no
        una cualquiera: apuntar un cobro, decirlo de qué factura es y quitársela son tres cosas distintas y
        las tres tienen que poder leerse.

        Esta prueba existe además porque esas etiquetas se escriben **en su sitio y enteras** (y no dentro de
        una expresión que elija entre dos): el guardián que vigila que quepan en su columna
        (`tests/test_las_etiquetas_del_rastro_caben.py`) las lee así, y una etiqueta que el guardián no ve es
        una etiqueta que nadie vigila. La encontró este ticket midiendo las suyas.
        """
        _entrega, factura = self._una_factura_de_121(cliente, cuenta, campana)
        cobro = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "40.00", "factura_emitida_id": factura["id"]},
        ).json()["cobro"]
        cliente.post(
            f"/api/cobros/{cobro['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={"factura_emitida_id": None},
        )
        cliente.post(
            f"/api/cobros/{cobro['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={"factura_emitida_id": factura["id"]},
        )
        with _sesion() as sesion:
            filas = list(
                sesion.scalars(
                    select(models.Auditoria)
                    .where(
                        models.Auditoria.entidad == "cobro",
                        models.Auditoria.entidad_id == cobro["id"],
                    )
                    .order_by(models.Auditoria.id)
                )
            )
        acciones = [fila.accion for fila in filas]
        # Los cuatro momentos, en orden: se apunta, se le quita la factura, se le vuelve a poner.
        assert acciones == ["crear", "desconciliar", "conciliar"], acciones
        # Y cada uno con su cuenta dentro, que es para lo que sirve el rastro.
        assert filas[0].datos["importe"] == "40.00"
        assert filas[-1].datos["factura"] == factura["id"]
        assert filas[1].datos["factura"] is None

    def test_un_cobro_de_cero_no_es_un_cobro(self, cliente, cuenta, campana):
        respuesta = cliente.post(
            "/api/cobros", headers=cuenta["cabeceras"], json={"fecha": "2026-08-01", "importe": "0.00"}
        )
        assert respuesta.status_code == 422
        assert "cero" in respuesta.json()["detail"].lower()

    def test_anular_un_cobro_devuelve_la_deuda_y_no_lo_cuenta_dos_veces(self, cliente, cuenta, campana):
        """Anular es la salida de «me he equivocado», y no puede dejar la factura debiendo de más.

        El cobro **no se borra**: queda anulado con su motivo y deja de contar. Y la factura vuelve a deber
        los 121, que es la verdad: ese dinero ya no está apuntado. Lo que no puede pasar es que anular y
        volver a apuntar el mismo pago acabe contándolo dos veces (81 pendientes en vez de 0), que es el
        fallo que se cuela cuando la suma se hace «por lo que hay en la lista» sin mirar el estado.
        """
        _entrega, factura = self._una_factura_de_121(cliente, cuenta, campana)
        cobro = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "40.00", "factura_emitida_id": factura["id"]},
        ).json()["cobro"]
        anulado = cliente.post(
            f"/api/cobros/{cobro['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me he equivocado al apuntarlo"},
        )
        assert anulado.status_code == 200, anulado.text
        assert anulado.json()["anulado"] is True
        vista = cliente.get(f"/api/facturas-emitidas/{factura['id']}", headers=cuenta["cabeceras"]).json()
        assert vista["pendiente"] == "121.00", "la factura sigue dando por cobrado lo anulado"
        assert vista["cobrado"] == "0.00"
        assert vista["cobros"] == [], "el cobro anulado sigue contando"
        # Y no está en la lista de cobros vivos, pero **sigue en la base** con su motivo.
        assert cliente.get("/api/cobros", headers=cuenta["cabeceras"]).json() == []
        with _sesion() as sesion:
            guardado = sesion.get(models.Cobro, cobro["id"])
            assert guardado is not None and guardado.anulado is True
            assert guardado.motivo_anulacion
        # Y volver a apuntarlo (el agricultor se equivocó **al anular**, que también pasa) cuadra: cero
        # pendientes, y no 81 como saldría si el dinero se contara dos veces.
        otra_vez = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-02", "importe": "121.00", "factura_emitida_id": factura["id"]},
        ).json()
        assert otra_vez["factura"]["pendiente"] == "0.00", otra_vez["factura"]


# --------------------------------------------------------------------------
# Agrupar entregas: no duplicar los ingresos
# --------------------------------------------------------------------------


class TestAgruparEntregas:
    """«Una entrega puede facturarse después o agruparse; **no duplicar ingresos al agrupar**» (contrato §4).

    La regla se sostiene en dos sitios y se prueban los dos: el importe de la factura **es la suma de sus
    líneas** (no un número aparte que se pueda solapar), y una entrega viva **no puede estar en dos facturas
    vivas** (lo impide un índice único en la base, no una comprobación amable).
    """

    def _dos_entregas(self, cliente, cuenta, campana):
        entregas = []
        for fecha, importe in (("2026-07-10", "121.00"), ("2026-07-12", "79.00")):
            entregas.append(
                cliente.post(
                    "/api/ventas",
                    headers=cuenta["cabeceras"],
                    json={
                        "campana_id": campana["id"],
                        "fecha": fecha,
                        "producto": "Trigo blando",
                        "cantidad": 1000.0,
                        "unidad": "kg",
                        "importe": importe,
                    },
                ).json()
            )
        return entregas

    def test_el_importe_de_la_factura_es_la_suma_de_sus_lineas(self, cliente, cuenta, campana):
        """121 + 79 = 200, y no 200 más lo que ya contaban las entregas por su cuenta."""
        entregas = self._dos_entregas(cliente, cuenta, campana)
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [e["id"] for e in entregas]},
        ).json()
        assert factura["importe_total"] == "200.00"
        assert factura["entregas"] == 2
        assert [linea["importe"] for linea in factura["lineas"]] == ["121.00", "79.00"]
        # Y la factura no tiene ningún importe propio que se pueda solapar con las entregas: su total es la
        # suma, y el resumen del año lo cuenta **una vez** (200 facturados, no 400).
        resumen = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        assert resumen["dinero"]["facturado"] == "200.00"
        assert resumen["dinero"]["importe"] == "200.00", "las entregas se han contado dos veces"

    def test_una_entrega_viva_no_puede_estar_en_dos_facturas(self, cliente, cuenta, campana):
        """Se dice en qué factura está ya, para que el agricultor no tenga que buscarla."""
        entregas = self._dos_entregas(cliente, cuenta, campana)
        primera = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "numero": "F-1", "entregas": [entregas[0]["id"]]},
        ).json()
        segunda = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-21", "entregas": [entregas[0]["id"], entregas[1]["id"]]},
        )
        assert segunda.status_code == 422
        aviso = segunda.json()["detail"]
        assert "F-1" in aviso, f"el aviso no dice en qué factura está: {aviso}"
        # Y sigue habiendo una sola factura.
        assert len(cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json()) == 1
        assert primera["id"] == cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json()[0]["id"]

    def test_la_misma_entrega_reenviada_no_se_factura_dos_veces(self, cliente, cuenta, campana):
        """Dentro de la **misma** petición tampoco: dos veces el mismo identificador son dos líneas... no.

        Lo que no puede pasar de ninguna manera es que la misma entrega acabe contada dos veces en la misma
        factura, así que la segunda línea tropieza con el índice único y la petición entera se rechaza.
        """
        entregas = self._dos_entregas(cliente, cuenta, campana)
        respuesta = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [entregas[0]["id"], entregas[0]["id"]]},
        )
        assert respuesta.status_code == 422, respuesta.text
        assert cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json() == []

    def test_quitar_la_factura_deja_las_entregas_libres_otra_vez(self, cliente, cuenta, campana):
        """«Me he equivocado al agrupar» tiene salida: se quita la factura y se rehace con las que sean."""
        entregas = self._dos_entregas(cliente, cuenta, campana)
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "numero": "F-1", "entregas": [e["id"] for e in entregas]},
        ).json()
        quitada = cliente.post(
            f"/api/facturas-emitidas/{factura['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me he equivocado al agrupar"},
        )
        assert quitada.status_code == 200, quitada.text
        assert quitada.json()["anulada"] is True
        assert cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json() == []
        # Y ahora las dos se pueden facturar por separado: cada entrega vuelve a estar libre.
        nueva = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-22", "numero": "F-2", "entregas": [entregas[0]["id"]]},
        )
        assert nueva.status_code == 201, nueva.text
        assert nueva.json()["importe_total"] == "121.00"

    def test_una_factura_con_cobros_no_se_quita_sin_quitar_antes_los_cobros(self, cliente, cuenta, campana):
        """Si se quitara, el dinero que ha entrado se quedaría sin saber de dónde viene."""
        entregas = self._dos_entregas(cliente, cuenta, campana)
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [entregas[0]["id"]]},
        ).json()
        cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "40.00", "factura_emitida_id": factura["id"]},
        )
        respuesta = cliente.post(
            f"/api/facturas-emitidas/{factura['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me he equivocado"},
        )
        assert respuesta.status_code == 409
        assert "cobros" in respuesta.json()["detail"].lower()

    def test_la_diferencia_observada_se_dice_y_no_se_reescribe_el_documento(self, cliente, cuenta, campana):
        """«Registrar diferencias observadas sin forzar a que una factura original cuadre» (contrato §2).

        Si se corrige el importe de una entrega después de facturarla, la factura **conserva lo que se
        emitió** y la pantalla dice que hay una diferencia con las dos cifras. Lo que no se hace es
        reescribir el documento ni esconder el cambio.
        """
        entregas = self._dos_entregas(cliente, cuenta, campana)
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [entregas[0]["id"]]},
        ).json()
        # Ahora se corrige el importe de la entrega: vale 130,00 en vez de 121,00.
        cliente.put(
            f"/api/ventas/{entregas[0]['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": entregas[0]["fecha"],
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "130.00",
            },
        )
        vista = cliente.get(f"/api/facturas-emitidas/{factura['id']}", headers=cuenta["cabeceras"]).json()
        # La factura sigue diciendo 121: lo que se emitió, emitido está.
        assert vista["importe_total"] == "121.00"
        linea = vista["lineas"][0]
        assert linea["importe"] == "121.00"
        assert linea["importe_ahora"] == "130.00"
        assert linea["diferencia"] is True
        assert linea["texto_importe"] == "121,00 €" and linea["texto_importe_ahora"] == "130,00 €"


# --------------------------------------------------------------------------
# Los ajustes: devolución y peso, humedad o calidad, con origen y evidencia
# --------------------------------------------------------------------------


class TestLasDevolucionesYLosAjustes:
    """«Registrar devoluciones y ajustes de peso/humedad/calidad **con evidencia y origen**» (contrato §4).

    La prueba que importa es la de los tres datos obligatorios: un ajuste sin origen es **un número suelto
    que cambia el importe sin decir de dónde sale**, y es exactamente lo que el ticket quiere impedir.
    """

    def _una_entrega(self, cliente, cuenta, campana, **cambios):
        datos = {
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 8000.0,
            "unidad": "kg",
            "precio_unitario": "0.2350",
            "comprador": "Cooperativa Agrícola de Peñaranda",
        }
        datos.update(cambios)
        return cliente.post("/api/ventas", headers=cuenta["cabeceras"], json=datos).json()

    def test_una_devolucion_resta_kilos_y_euros(self, cliente, cuenta, campana):
        """8.000 kg a 0,2350 €/kg son 1.880,00 €; devolver 3.000 kg y 40,50 € deja 5.000 kg y 1.839,50 €."""
        entrega = self._una_entrega(cliente, cuenta, campana)
        assert entrega["importe_total"] == "1880.00"
        ajuste = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "devolucion",
                "origen": "cliente",
                "motivo": "el trigo venía con mucha humedad y me lo han devuelto",
                "cantidad": "-3000",
                "importe": "-40.50",
                "evidencia_descripcion": "albarán de devolución 2026/77",
            },
        )
        assert ajuste.status_code == 201, ajuste.text
        vista = cliente.get(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"]).json()
        assert vista["importe_total"] == "1839.50"
        assert vista["kilos_netos"] == 5000.0
        # La cantidad apuntada sigue ahí: es la entrega la que dice los kilos netos, calculados.
        assert vista["cantidad"] == 8000.0
        # Y el ajuste se enseña con sus palabras, no con su código.
        assert vista["ajustes"][0]["etiqueta_tipo"] == textos.VENTA["tipos_de_ajuste"]["devolucion"]
        assert vista["ajustes"][0]["etiqueta_origen"] == textos.VENTA["origenes_de_un_ajuste"]["cliente"]

    def test_un_ajuste_sin_origen_no_se_apunta(self, cliente, cuenta, campana):
        """**La prueba del ticket**: un número que cambia el importe sin decir de dónde sale, no."""
        entrega = self._una_entrega(cliente, cuenta, campana)
        for datos in (
            # Sin origen.
            {"tipo": "peso", "motivo": "pesaba menos de lo apuntado", "cantidad": "-500"},
            # Con un origen que no está en la lista cerrada.
            {
                "tipo": "peso",
                "origen": "un_amigo",
                "motivo": "pesaba menos",
                "cantidad": "-500",
            },
            # Sin motivo.
            {"tipo": "peso", "origen": "bascula", "motivo": "", "cantidad": "-500"},
            # Y con un tipo que no es ninguno de los cuatro.
            {
                "tipo": "lo_que_sea",
                "origen": "bascula",
                "motivo": "algo pasó",
                "cantidad": "-500",
            },
        ):
            respuesta = cliente.post(
                f"/api/ventas/{entrega['id']}/ajustes", headers=cuenta["cabeceras"], json=datos
            )
            assert respuesta.status_code == 422, f"se ha aceptado {datos}"
        # Y la entrega sigue valiendo lo que valía: no ha entrado ningún número sin explicación.
        vista = cliente.get(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"]).json()
        assert vista["importe_total"] == "1880.00"
        assert vista["ajustes"] == []

    def test_un_ajuste_que_no_cambia_nada_no_se_apunta(self, cliente, cuenta, campana):
        """Un apunte que no mueve ni los kilos ni los euros no es un ajuste: se dice por qué."""
        entrega = self._una_entrega(cliente, cuenta, campana)
        respuesta = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes",
            headers=cuenta["cabeceras"],
            json={"tipo": "calidad", "origen": "acuerdo", "motivo": "lo hemos hablado"},
        )
        assert respuesta.status_code == 422
        assert "no cambia" in respuesta.json()["detail"].lower()

    def test_un_ajuste_sin_papel_se_apunta_y_se_dice_que_no_lo_trae(self, cliente, cuenta, campana):
        """El papel puede llegar después: bloquear el apunte por eso sería impedir apuntar lo que pasó."""
        entrega = self._una_entrega(cliente, cuenta, campana)
        ajuste = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "humedad",
                "origen": "laboratorio",
                "motivo": "el boletín dice que venía con un 14 % de humedad",
                "importe": "-25.00",
            },
        ).json()
        assert ajuste["tiene_papel"] is False
        # Y la pantalla tiene con qué decirlo: el texto está en el servidor, no escrito a mano.
        assert textos.VENTA["ajuste_sin_papel"]

    def test_el_papel_del_ajuste_se_sube_y_no_se_puede_escribir_fuera_de_su_carpeta(
        self, cliente, cuenta, campana, tmp_path
    ):
        """El fichero va a disco con la ruta que pone el programa, **nunca con el nombre que manda el
        navegador**: un nombre como `../../app/main.py` escribiría fuera de su carpeta.

        Es la misma regla que los boletines y las facturas (`app/adjuntos.py`), y se comprueba
        **mirando el disco**, no confiando en el código.
        """
        entrega = self._una_entrega(cliente, cuenta, campana)
        ajuste = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "peso",
                "origen": "bascula",
                "motivo": "la báscula dio menos kilos",
                "cantidad": "-300",
            },
        ).json()
        assert ajuste["tiene_papel"] is False
        subido = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes/{ajuste['id']}/papel",
            headers=cuenta["cabeceras"],
            files={"fichero": ("../../app/main.py.png", b"\x89PNG\r\n\x1a\n datos", "image/png")},
        )
        assert subido.status_code == 200, subido.text
        cuerpo = subido.json()
        assert cuerpo["tiene_papel"] is True
        # El nombre que se enseña es el que mandó el navegador (recortado), pero la ruta es la que puso el
        # programa: dentro de la carpeta de la finca y con un nombre al azar.
        from app import adjuntos

        carpeta = adjuntos.carpeta_de_adjuntos()
        with _sesion() as sesion:
            ruta = sesion.scalar(
                select(models.AjusteDeEntrega.fichero_ruta).where(
                    models.AjusteDeEntrega.id == ajuste["id"]
                )
            )
        assert ruta and ".." not in ruta and ruta.startswith(f"{cuenta['explotacion_id']}/")
        assert (carpeta / ruta).is_file(), "el papel no está donde dice que está"

    def test_quitar_un_ajuste_devuelve_el_importe_y_no_borra_el_papel(self, cliente, cuenta, campana):
        """El papel sigue siendo el justificante de lo que se apuntó, aunque el ajuste ya no cuente."""
        entrega = self._una_entrega(cliente, cuenta, campana)
        ajuste = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "calidad",
                "origen": "acuerdo",
                "motivo": "acordamos descontar por la calidad",
                "importe": "-80.00",
            },
        ).json()
        assert cliente.get(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"]).json()[
            "importe_total"
        ] == "1800.00"
        quitado = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes/{ajuste['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me he equivocado al apuntarlo"},
        )
        assert quitado.status_code == 200, quitado.text
        assert quitado.json()["anulado"] is True
        vista = cliente.get(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"]).json()
        assert vista["importe_total"] == "1880.00", "el importe no ha vuelto al de antes"
        assert vista["ajustes"] == [], "el ajuste quitado sigue contando"

    def test_un_ajuste_no_puede_ser_de_una_entrega_de_otra_finca(self, cliente, cuenta, campana, crear_cuenta):
        """El caso A13 del contrato: sin datos ni filtración de existencia (404, no 403)."""
        entrega = self._una_entrega(cliente, cuenta, campana)
        otra = crear_cuenta("otra-finca-t12@ejemplo.test", nombre="Otro", nif="87654321X")
        respuesta = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes",
            headers=otra["cabeceras"],
            json={
                "tipo": "peso",
                "origen": "bascula",
                "motivo": "desde otra finca",
                "cantidad": "-100",
            },
        )
        assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# El reenvío: el móvil sin cobertura no apunta dos veces
# --------------------------------------------------------------------------


class TestElReenvioNoDuplica:
    """El caso A12 del contrato: «Móvil repite envío al reconectar → un trabajo, sus consumos una vez,
    respuesta recuperable».

    Aquí vale para las cuatro cosas del dinero: la entrega, el ajuste, la factura y el cobro. Y no es una
    precaución teórica: el agricultor apunta de pie en una parcela sin cobertura todos los días.
    """

    def test_la_misma_entrega_dos_veces_es_una_entrega(self, cliente, cuenta, campana):
        carga = {
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 8000.0,
            "unidad": "kg",
            "importe": "1880.00",
            "clave_de_reenvio": "el-movil-1",
        }
        primera = cliente.post("/api/ventas", headers=cuenta["cabeceras"], json=carga)
        segunda = cliente.post("/api/ventas", headers=cuenta["cabeceras"], json=carga)
        assert primera.status_code == 201, primera.text
        # **La segunda devuelve la misma entrega**, y con 201 igual que la primera: reenviar devuelve su
        # resultado (contrato §2), no un error.
        assert segunda.status_code == 201, segunda.text
        assert segunda.json()["id"] == primera.json()["id"]
        assert len(cliente.get("/api/ventas", headers=cuenta["cabeceras"]).json()) == 1

    def test_el_mismo_cobro_dos_veces_es_un_cobro(self, cliente, cuenta, campana):
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
            },
        ).json()
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [entrega["id"]]},
        ).json()
        carga = {
            "fecha": "2026-08-01",
            "importe": "40.00",
            "factura_emitida_id": factura["id"],
            "clave_de_reenvio": "cobro-repetido",
        }
        primera = cliente.post("/api/cobros", headers=cuenta["cabeceras"], json=carga).json()
        segunda = cliente.post("/api/cobros", headers=cuenta["cabeceras"], json=carga).json()
        assert segunda["ya_estaba"] is True, "el reenvío no dice que ya estaba apuntado"
        assert segunda["cobro"]["id"] == primera["cobro"]["id"]
        # Y lo importante: **el pendiente no se ha movido**. Con el mismo cobro contado dos veces saldría
        # 41 pendientes en vez de 81, que es un error de 40 euros.
        assert segunda["factura"]["pendiente"] == "81.00"
        assert len(cliente.get("/api/cobros", headers=cuenta["cabeceras"]).json()) == 1

    def test_la_misma_factura_dos_veces_es_una_factura(self, cliente, cuenta, campana):
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
            },
        ).json()
        carga = {
            "fecha": "2026-07-20",
            "numero": "F-1",
            "entregas": [entrega["id"]],
            "clave_de_reenvio": "factura-repetida",
        }
        primera = cliente.post("/api/facturas-emitidas", headers=cuenta["cabeceras"], json=carga)
        segunda = cliente.post("/api/facturas-emitidas", headers=cuenta["cabeceras"], json=carga)
        assert primera.status_code == 201 and segunda.status_code == 201, segunda.text
        assert segunda.json()["id"] == primera.json()["id"]
        assert len(cliente.get("/api/facturas-emitidas", headers=cuenta["cabeceras"]).json()) == 1
        # Y el resumen del año cuenta 121 una vez, no 242.
        resumen = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        assert resumen["dinero"]["facturado"] == "121.00"

    def test_el_mismo_ajuste_dos_veces_es_un_ajuste(self, cliente, cuenta, campana):
        """Dos devoluciones iguales apuntadas por el móvil no pueden restar dos veces."""
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 8000.0,
                "unidad": "kg",
                "precio_unitario": "0.2350",
            },
        ).json()
        carga = {
            "tipo": "devolucion",
            "origen": "cliente",
            "motivo": "me han devuelto mil kilos",
            "cantidad": "-1000",
            "importe": "-235.00",
            "clave_de_reenvio": "ajuste-repetido",
        }
        primera = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes", headers=cuenta["cabeceras"], json=carga
        )
        segunda = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes", headers=cuenta["cabeceras"], json=carga
        )
        assert primera.status_code == 201 and segunda.status_code == 201, segunda.text
        assert primera.json()["id"] == segunda.json()["id"]
        vista = cliente.get(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"]).json()
        assert vista["importe_total"] == "1645.00", "la devolución se ha restado dos veces"
        assert len(vista["ajustes"]) == 1


# --------------------------------------------------------------------------
# El resumen cuadra con el detalle, y la tabla es la del contrato
# --------------------------------------------------------------------------


class TestLaTablaYElResumenCuadran:
    """«Si el resumen dice que hay 3.000 € pendientes, la suma de las filas tiene que dar 3.000 €».

    Con datos representativos de verdad: varias campañas, importes incompletos, un pago parcial, entregas
    agrupadas en una factura y una devolución. Es la prueba que caza el fallo más caro de una pantalla de
    cuentas: un total que no cuadra con lo que se ve.
    """

    def _la_finca_del_ticket(self, cliente, cuenta, campana):
        """Las entregas del encargo de pruebas, con sus formas raras: una sin importe (A08), una con ajuste,
        dos agrupadas en una factura con un pago parcial, y una de una campaña anterior."""
        entregas = {}
        # 1) Sin importe: 8.000 kg y no se sabe por cuánto (A08).
        entregas["sin_importe"] = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Cebada",
                "cantidad": 8000.0,
                "unidad": "kg",
                "comprador": "Cooperativa Agrícola de Peñaranda",
            },
        ).json()
        # 2) Con importe y sin facturar.
        entregas["suelta"] = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-11",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "300.00",
                "comprador": "Un vecino",
            },
        ).json()
        # 3) y 4) Dos entregas que se agrupan en una factura, con un pago parcial y devolución.
        entregas["a"] = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-12",
                "producto": "Trigo blando",
                "cantidad": 42000.0,
                "unidad": "kg",
                "precio_unitario": "0.2350",
                "comprador": "Cooperativa Agrícola de Peñaranda",
            },
        ).json()
        entregas["b"] = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-13",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "200.00",
                "comprador": "Cooperativa Agrícola de Peñaranda",
            },
        ).json()
        # Una devolución sobre la entrega grande: 2.000 kg y 100,00 €.
        cliente.post(
            f"/api/ventas/{entregas['a']['id']}/ajustes",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "humedad",
                "origen": "bascula",
                "motivo": "la báscula dio menos kilos de los apuntados",
                "cantidad": "-2000",
                "importe": "-100.00",
            },
        )
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-07-20",
                "numero": "F-2026-1",
                "cliente": "Cooperativa Agrícola de Peñaranda",
                "entregas": [entregas["a"]["id"], entregas["b"]["id"]],
            },
        ).json()
        # Un pago parcial de 5.000,00 €.
        cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "5000.00", "factura_emitida_id": factura["id"]},
        )
        return entregas, factura

    def test_el_pie_es_la_suma_de_las_filas(self, cliente, cuenta, campana):
        """El número del contrato, con los datos del encargo: el pie y la suma de las filas son el mismo."""
        self._la_finca_del_ticket(cliente, cuenta, campana)
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        totales = tabla["totales"]
        # Lo que dicen las filas, sumado **con Decimal** (que es lo que hace el servidor).
        importe = dinero.suma(*[f["importe_valor"] or None for f in tabla["filas"]])
        cobrado = dinero.suma(*[f["cobrado_valor"] or None for f in tabla["filas"]])
        pendiente = dinero.suma(*[f["pendiente_valor"] or None for f in tabla["filas"]])
        assert importe == Decimal(totales["importe"]), (importe, totales["importe"])
        assert cobrado == Decimal(totales["cobrado"]), (cobrado, totales["cobrado"])
        assert pendiente == Decimal(totales["pendiente"]), (pendiente, totales["pendiente"])
        # Y los números del encargo, uno por uno:
        #  Cebada (sin importe) + 300,00 + (42.000 kg × 0,2350 = 9.870,00 − 100,00 de la devolución) + 200,00
        assert totales["importe"] == "10270.00", totales
        assert totales["facturado"] == "9970.00", totales
        assert totales["cobrado"] == "5000.00", totales
        assert totales["pendiente"] == "4970.00", totales
        assert totales["sin_importe"] == 1
        assert totales["entregas"] == 4
        # Y el pie lo dice con las palabras del servidor.
        assert tabla["pie"] == textos.VENTA["pie_varias"].format(
            entregas=4, importe="10.270,00 €", pendiente="4.970,00 €"
        )
        # El aviso de lo que no entra en la cuenta, con su número.
        assert tabla["avisos"] == [textos.VENTA["faltan_importes_una"]]

    def test_el_reparto_del_cobro_entre_las_entregas_de_una_factura_cuadra(self, cliente, cuenta, campana):
        """La factura agrupa dos entregas y el pago es **de la factura**: se reparte por orden y sin repetir.

        Es lo que hace que la suma de la columna «cobrado» sea exactamente lo cobrado: con el importe
        repetido en cada fila (lo fácil), la suma daría el doble en una factura de dos entregas.
        """
        self._la_finca_del_ticket(cliente, cuenta, campana)
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        con_cobro = [f for f in tabla["filas"] if Decimal(f["cobrado_valor"] or "0") > 0]
        # El pago (5.000,00) va primero a la entrega más antigua de la factura (la del 12/07, que vale
        # 9.770,00) y **no** se repite en la otra.
        assert len(con_cobro) == 1, f"el cobro está en más de una fila: {con_cobro}"
        assert con_cobro[0]["cobrado_valor"] == "5000.00"
        assert con_cobro[0]["pendiente_valor"] == "4770.00"
        # Y la otra entrega de la misma factura sale con lo suyo: nada cobrado y 200,00 pendientes.
        otra = [
            f
            for f in tabla["filas"]
            if f["factura_numero"] == "F-2026-1" and Decimal(f["cobrado_valor"] or "0") == 0
        ]
        assert len(otra) == 1
        assert otra[0]["pendiente_valor"] == "200.00"
        # La suma de los dos pendientes es el de la factura, exacto.
        assert dinero.suma(Decimal("4770.00"), Decimal("200.00")) == Decimal("4970.00")

    def test_el_resumen_del_ano_dice_lo_mismo_que_la_tabla(self, cliente, cuenta, campana):
        """Dos pantallas que enseñan el mismo dinero no pueden decir cosas distintas."""
        self._la_finca_del_ticket(cliente, cuenta, campana)
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        resumen = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        for clave in ("importe", "facturado", "cobrado", "pendiente", "entregas", "sin_importe"):
            assert resumen["dinero"][clave] == tabla["totales"][clave], clave

    def test_cada_campana_lleva_sus_entregas_y_su_dinero(self, cliente, cuenta, campana):
        """**Varias campañas**, que es como son los datos de verdad: la tabla es de una y el dinero también.

        La campaña es una dimensión y no se deduce del año natural (contrato §2): una entrega de la campaña
        pasada no puede aparecer en el total de la de ahora, ni su pendiente engordar lo que te deben este
        año. Se comprueba con dos campañas y una entrega en cada una.
        """
        anterior = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={"anio": campana["anio"] - 1, "fecha_inicio": "2024-09-01", "fecha_fin": "2025-08-31"},
        )
        assert anterior.status_code == 201, anterior.text
        # Una entrega cobrada en la campaña anterior y otra pendiente en la de ahora.
        vieja = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": anterior.json()["id"],
                "fecha": "2025-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "100.00",
            },
        ).json()
        nueva = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Cebada",
                "cantidad": 2000.0,
                "unidad": "kg",
                "importe": "300.00",
            },
        ).json()
        # La tabla, sin decir campaña, es la de la campaña que se está llevando: solo la de ahora.
        actual = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        assert [f["id"] for f in actual["filas"]] == [nueva["id"]]
        assert actual["totales"]["importe"] == "300.00"
        # Y pidiendo la anterior, solo la suya (y con su dinero, no con el de la otra).
        pasada = cliente.get(
            f"/api/ventas/tabla?campana_id={anterior.json()['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert [f["id"] for f in pasada["filas"]] == [vieja["id"]]
        assert pasada["totales"]["importe"] == "100.00"
        # Y los dos resúmenes tampoco se mezclan.
        suyo = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        assert suyo["campana"] == campana["anio"]
        assert suyo["dinero"]["importe"] == "300.00"
        el_de_antes = cliente.get(
            f"/api/ventas/resumen?campana_id={anterior.json()['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert el_de_antes["campana"] == campana["anio"] - 1
        assert el_de_antes["dinero"]["importe"] == "100.00"

    def test_las_columnas_son_las_ocho_del_contrato(self, cliente, cuenta, campana):
        """«Cliente, producto, fecha, cantidad, importe conocido, vencimiento, cobrado y pendiente»."""
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        claves = [columna["clave"] for columna in tabla["columnas"]]
        for esperada in (
            "cliente",
            "producto",
            "fecha",
            "cantidad",
            "importe",
            "vencimiento",
            "cobrado",
            "pendiente",
        ):
            assert esperada in claves, f"falta la columna {esperada}: {claves}"
        # Y cada columna viene con su rótulo del servidor (la pantalla no escribe ni una palabra).
        assert {columna["texto"] for columna in tabla["columnas"]} >= {
            textos.VENTA["tabla_cliente"],
            textos.VENTA["tabla_producto"],
            textos.VENTA["tabla_pendiente"],
        }

    def test_una_columna_obligatoria_no_se_puede_quitar_de_la_tabla(self, cliente, cuenta, campana):
        """Las columnas configurables (contrato §3) no pueden dejar la tabla sin lo que se viene a mirar.

        `acciones` es obligatoria **desde la revisión del T12**: la pieza `Tabla` pinta la celda de los
        botones como última columna de cada fila, así que la columna que la titula tiene que estar. Sin
        ella, el rótulo de una columna de datos caía encima de los botones y esa columna no se pintaba
        nunca (defecto 5 de `docs/REVISION_T12.md`).
        """
        tabla = cliente.get(
            "/api/ventas/tabla?columnas=cliente,producto", headers=cuenta["cabeceras"]
        ).json()
        claves = [columna["clave"] for columna in tabla["columnas"]]
        assert claves == ["cliente", "producto", "fecha", "cantidad", "importe", "pendiente", "acciones"], claves
        # Y sin pedir nada salen todas.
        todas = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        assert len(todas["columnas"]) > len(claves)

    def test_los_filtros_cuentan_lo_que_dejan_dentro(self, cliente, cuenta, campana):
        """Un pie que suma lo que hay pero no dice qué se ha filtrado es un pie que engaña."""
        self._la_finca_del_ticket(cliente, cuenta, campana)
        solo_pendientes = cliente.get(
            "/api/ventas/tabla?solo=pendientes", headers=cuenta["cabeceras"]
        ).json()
        assert solo_pendientes["totales"]["pendiente"] == solo_pendientes["totales"]["pendiente"]
        assert Decimal(solo_pendientes["totales"]["pendiente"]) > 0
        # Y todas las que quedan tienen algo pendiente: ni una de más.
        assert all(f["pendiente_valor"] for f in solo_pendientes["filas"])
        solo_sin_importe = cliente.get(
            "/api/ventas/tabla?solo=sin_importe", headers=cuenta["cabeceras"]
        ).json()
        assert [f["producto"] for f in solo_sin_importe["filas"]] == ["Cebada"]
        assert solo_sin_importe["filtradas"] == 1
        assert solo_sin_importe["total"] == 4
        # Y buscar por el albarán encuentra la entrega, que es lo que se hace con el papel en la mano.
        buscado = cliente.get(
            "/api/ventas/tabla?q=cebada", headers=cuenta["cabeceras"]
        ).json()
        assert [f["producto"] for f in buscado["filas"]] == ["Cebada"]

    def test_la_tabla_se_ordena_por_valor_y_no_por_el_texto(self, cliente, cuenta, campana):
        """El importe se guarda como texto decimal: ordenar por el texto pondría 9,00 € detrás de 121,00 €."""
        for importe, producto in (("900.00", "Nueve"), ("121.00", "Ciento"), ("9.00", "Nueve euros")):
            cliente.post(
                "/api/ventas",
                headers=cuenta["cabeceras"],
                json={
                    "campana_id": campana["id"],
                    "fecha": "2026-07-10",
                    "producto": producto,
                    "cantidad": 1.0,
                    "unidad": "kg",
                    "importe": importe,
                },
            )
        ascendente = cliente.get(
            "/api/ventas/tabla?orden=importe&sentido=1", headers=cuenta["cabeceras"]
        ).json()
        assert [f["importe_valor"] for f in ascendente["filas"]] == ["9.00", "121.00", "900.00"]
        descendente = cliente.get(
            "/api/ventas/tabla?orden=importe&sentido=-1", headers=cuenta["cabeceras"]
        ).json()
        assert [f["importe_valor"] for f in descendente["filas"]] == ["900.00", "121.00", "9.00"]

    def test_una_entrega_sin_importe_se_va_al_final_al_ordenar_por_dinero(self, cliente, cuenta, campana):
        """«No se sabe» no es un número: no se coloca entre los de cero como si valiera cero."""
        cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Sin precio",
                "cantidad": 1000.0,
                "unidad": "kg",
            },
        )
        cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-11",
                "producto": "Con precio",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "10.00",
            },
        )
        tabla = cliente.get("/api/ventas/tabla?orden=importe&sentido=1", headers=cuenta["cabeceras"]).json()
        assert [f["producto"] for f in tabla["filas"]] == ["Con precio", "Sin precio"]

    def test_el_vencimiento_marca_lo_que_esta_vencido(self, cliente, cuenta, campana):
        """«Cobros y pagos vencidos» es la tarjeta del panel de Economía, y sale de aquí."""
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
                "vencimiento": "2026-07-15",
            },
        ).json()
        cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [entrega["id"]]},
        )
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        fila = tabla["filas"][0]
        # La fecha de hoy de la suite es posterior al vencimiento (2026-07-15), así que sale vencida y la
        # pantalla tiene con qué explicarlo.
        assert dt.date.today() > dt.date(2026, 7, 15), "esta prueba necesita una fecha posterior"
        assert fila["clave_estado"] == "vencida", fila
        assert fila["estado"] == textos.VENTA["estado_vencida"]
        assert textos.VENTA["estado_vencida_pista"]


# --------------------------------------------------------------------------
# Aislamiento entre fincas (el caso A13 del contrato)
# --------------------------------------------------------------------------


class TestNadaDeOtraFinca:
    """«Tierra ajena o enlace a adjunto de otra finca → sin datos ni filtración de existencia».

    Se comprueba en las cuatro puertas del dinero, y en las tres que llevan un identificador de otra finca:
    leerla, cobrar contra ella y anular un cobro suyo. Todas contestan **404** y no 403, para no contar si
    ese identificador existe en otra finca.
    """

    def _lo_de_una_finca(self, cliente, cuenta, campana):
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
            },
        ).json()
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "entregas": [entrega["id"]]},
        ).json()
        cobro = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-08-01", "importe": "40.00", "factura_emitida_id": factura["id"]},
        ).json()["cobro"]
        return entrega, factura, cobro

    def test_otra_finca_no_ve_ni_toca_nada(self, cliente, cuenta, campana, crear_cuenta):
        entrega, factura, cobro = self._lo_de_una_finca(cliente, cuenta, campana)
        otra = crear_cuenta("la-otra-finca@ejemplo.test", nombre="Otro", nif="87654321X")
        cabeceras = otra["cabeceras"]
        assert cliente.get(f"/api/ventas/{entrega['id']}", headers=cabeceras).status_code == 404
        assert cliente.get(f"/api/facturas-emitidas/{factura['id']}", headers=cabeceras).status_code == 404
        assert (
            cliente.post(
                "/api/cobros",
                headers=cabeceras,
                json={"fecha": "2026-08-02", "importe": "10.00", "factura_emitida_id": factura["id"]},
            ).status_code
            == 404
        )
        # Y tampoco puede enlazar un ajuste a una entrega que no es suya, ni quitarle un cobro.
        assert (
            cliente.post(
                f"/api/ventas/{entrega['id']}/ajustes",
                headers=cabeceras,
                json={"tipo": "peso", "origen": "bascula", "motivo": "desde fuera", "cantidad": "-1"},
            ).status_code
            == 404
        )
        assert (
            cliente.post(
                f"/api/cobros/{cobro['id']}/anular", headers=cabeceras, json={"motivo": "porque sí"}
            ).status_code
            == 404
        )
        # Y sus listas están vacías: no es que no pueda tocar, es que no ve nada.
        assert cliente.get("/api/ventas", headers=cabeceras).json() == []
        assert cliente.get("/api/facturas-emitidas", headers=cabeceras).json() == []
        assert cliente.get("/api/cobros", headers=cabeceras).json() == []
        # Y la factura de la finca de verdad sigue intacta (nadie le ha tocado el pendiente).
        vista = cliente.get(f"/api/facturas-emitidas/{factura['id']}", headers=cuenta["cabeceras"]).json()
        assert vista["pendiente"] == "81.00"


# --------------------------------------------------------------------------
# Lo que este ticket NO hace, y se dice
# --------------------------------------------------------------------------


class TestLaEmisionFiscalNoSeActiva:
    """El contrato lo dice con estas palabras (§4, S12): «La emisión fiscal completa requiere especificación
    normativa propia antes de activarse como tal».

    Aquí se comprueba que **no se ha activado por la puerta de atrás**: ni un impuesto en los datos, ni una
    palabra de ley en las pantallas del dinero, y ninguna ruta que prometa un documento con validez.

    Es la prueba que impide que alguien, dentro de un mes, le ponga «IVA» a un campo o llame «factura
    oficial» a esto porque «queda mejor».
    """

    def test_lo_que_se_emite_es_una_factura_nuestra_de_gestion(self, cliente, cuenta, campana):
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
            },
        ).json()
        factura = cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "numero": "F-2026-1", "entregas": [entrega["id"]]},
        ).json()
        # Ni base imponible, ni cuota, ni tipo: lo que se guarda es lo que se ha entregado y por cuánto.
        for prohibido in ("base_imponible", "cuota_iva", "tipo_iva", "iva", "verifactu", "impuesto"):
            assert prohibido not in factura, f"la factura lleva «{prohibido}»"
        # Y su total es **la suma de lo entregado**, sin nada más.
        assert factura["importe_total"] == "121.00"

    def test_ninguna_pantalla_del_dinero_habla_de_impuestos_ni_de_ley(self):
        """Las palabras que no pueden salir en pantalla, comprobadas sobre los textos del servidor.

        Es la mitad «y no se disfraza» de la decisión: si alguien añadiera un texto con «IVA» o «factura
        legal», esto saltaría antes de que llegara al agricultor.
        """
        dichos = []
        for clave, valor in {**textos.VENTA, **textos.FACTURA_EMITIDA, **textos.COBRO}.items():
            if isinstance(valor, str):
                dichos.append((clave, valor))
            elif isinstance(valor, dict):
                dichos.extend((f"{clave}.{dentro}", texto) for dentro, texto in valor.items())
        for clave, frase in dichos:
            bajo = frase.lower()
            for palabra in ("iva", "verifactu", "impuesto", "hacienda", "ticketbai", "ley "):
                assert palabra not in bajo, f"«{clave}» habla de {palabra}: {frase}"

    def test_las_pantallas_dicen_que_no_es_un_documento_con_validez_oficial(self):
        """Y decirlo es obligatorio, no un detalle: es lo que impide que alguien lo presente donde no vale."""
        for clave in ("aviso_no_oficial", "explica"):
            assert "no es un documento con validez oficial" in textos.FACTURA_EMITIDA[clave] or (
                "no es una factura con validez oficial" in textos.FACTURA_EMITIDA[clave]
            ), textos.FACTURA_EMITIDA[clave]

    def test_no_hay_ninguna_ruta_que_emita_un_documento_fiscal(self):
        """Se mira lo que la aplicación **publica**, no una respuesta: así caza una ruta aunque su pantalla
        no se use en ninguna otra prueba de este fichero."""
        from app.main import app

        publicadas = {
            (metodo.upper(), ruta)
            for ruta, metodos in app.openapi()["paths"].items()
            for metodo in metodos
        }
        for metodo, ruta in publicadas:
            bajo = ruta.lower()
            # **Se mira el segmento entero, no una subcadena** (07/10/2026): buscando `iva` a secas,
            # «normat**iva**» daba un falso positivo -y una ruta que no emite nada no puede fallar por como
            # se llama-. Aqui se parte la ruta en trozos y se busca un trozo que **sea** eso.
            trozos = set(re.split(r"[/_-]+", bajo))
            for prohibido in ("iva", "verifactu", "fiscal", "hacienda", "impuesto"):
                assert prohibido not in trozos, f"hay una ruta de emisión fiscal: {metodo} {ruta}"
        # Y las cuatro rutas del dinero de este ticket sí están, que es lo que sí se entrega.
        for esperada in (
            ("GET", "/api/ventas/tabla"),
            ("POST", "/api/facturas-emitidas"),
            ("GET", "/api/cobros"),
            ("POST", "/api/cobros"),
        ):
            assert esperada in publicadas, f"falta {esperada}"


# --------------------------------------------------------------------------
# El esquema: lo que cambia al añadir estas tablas
# --------------------------------------------------------------------------


class TestElEsquemaDelDinero:
    """Tres decisiones de esquema que conviene dejar fijadas, porque deshacerlas rompe cosas en silencio."""

    def test_las_cuatro_cosas_estan_separadas(self):
        """«Separar lote cosechado, entrega/albarán, factura emitida y cobro» (contrato §4, S12).

        Las cuatro existen y son cuatro sitios distintos. Y el «lote cosechado» **no es una tabla nueva**:
        es la labor de tipo cosecha que ya existía, y la entrega la referencia. Duplicarla habría sido
        tener dos listas de lo mismo.
        """
        tablas = models.Base.metadata.tables
        assert "ventas_de_cosecha" in tablas, "falta la entrega"
        assert "facturas_emitidas" in tablas, "falta la factura nuestra"
        assert "lineas_de_factura_emitida" in tablas, "falta la línea que ata entrega y factura"
        assert "cobros" in tablas, "falta el cobro"
        assert "ajustes_de_entrega" in tablas, "faltan las devoluciones y los ajustes"
        # Y el lote cosechado es la labor de tipo cosecha: la entrega la apunta con `cosecha_id`.
        assert "cosecha_id" in tablas["ventas_de_cosecha"].columns
        assert tablas["ventas_de_cosecha"].columns["cosecha_id"].foreign_keys
        assert next(iter(tablas["ventas_de_cosecha"].columns["cosecha_id"].foreign_keys)).target_fullname == "labores.id"

    def test_todas_las_tablas_del_dinero_separan_las_fincas(self):
        """`explotacion_id` en todas: es lo que impide que un agricultor vea lo de otro (contrato §2)."""
        for tabla in (
            "ventas_de_cosecha",
            "facturas_emitidas",
            "lineas_de_factura_emitida",
            "cobros",
            "ajustes_de_entrega",
        ):
            assert "explotacion_id" in models.Base.metadata.tables[tabla].columns, (
                f"«{tabla}» no dice de qué finca es"
            )

    def test_el_importe_no_se_guarda_como_numero_de_coma_flotante(self):
        """El tipo de las columnas de dinero, comprobado: **texto decimal, no `Float`**.

        Es la decisión que hace que el dinero no pierda céntimos en la base, y es fácil de deshacer sin
        querer: `Float` es lo que pone todo el mundo y lo que ya tienen las columnas de las facturas de
        compra (que son de antes de este ticket y no se tocan aquí).
        """
        for tabla, columnas in {
            "ventas_de_cosecha": ("importe", "precio_unitario"),
            "facturas_emitidas": ("importe_total",),
            "lineas_de_factura_emitida": ("importe",),
            "cobros": ("importe", "importe_imputado"),
            "ajustes_de_entrega": ("importe",),
        }.items():
            for columna in columnas:
                tipo = str(models.Base.metadata.tables[tabla].columns[columna].type)
                assert tipo.startswith("VARCHAR"), f"{tabla}.{columna} es {tipo} y debería ser texto decimal"

    def test_la_factura_cuelga_del_ano_y_el_cobro_no(self):
        """Es una decisión con motivo, y hay pruebas de la casa que la vigilan por los dos lados.

        La factura sí: se emite **para una campaña** y así la pantalla de los años la cuenta y no borra un
        año que tiene facturas sin decirlo (está en `OTRAS_COSAS`). El cobro no: es dinero que entra un día
        y salda una factura, y colgarlo del año obligaría a decidir de qué año es un pago de enero que salda
        una factura de diciembre.
        """
        tablas = models.Base.metadata.tables
        assert "campana_id" in tablas["facturas_emitidas"].columns
        assert "campana_id" not in tablas["cobros"].columns
        assert "campana_id" not in tablas["ajustes_de_entrega"].columns
        # Y la factura está clasificada en la pantalla de los años, que es lo que exige el guardián de
        # `explotacion.OTRAS_COSAS`.
        from app.routers import explotacion

        assert "FacturaEmitida" in explotacion.OTRAS_COSAS

    def test_una_entrega_de_una_factura_con_cobros_no_se_borra(self, cliente, cuenta, campana, usuario=None):
        """Si se borrara, la factura seguiría contando un dinero cuya entrega ya no existe."""
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
            },
        ).json()
        cliente.post(
            "/api/facturas-emitidas",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-07-20", "numero": "F-1", "entregas": [entrega["id"]]},
        )
        # Borrarla no se puede: hay una factura viva detrás.
        respuesta = cliente.delete(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 409
        assert "F-1" in respuesta.json()["detail"]
        # Y anularla tampoco, por el mismo motivo: la factura quedaría contando algo que ya no vale.
        assert (
            cliente.post(
                f"/api/ventas/{entrega['id']}/anular",
                headers=cuenta["cabeceras"],
                json={"motivo": "me he equivocado"},
            ).status_code
            == 409
        )

    def test_borrar_una_entrega_se_lleva_sus_ajustes_su_papel_y_deja_el_rastro(
        self, cliente, cuenta, campana
    ):
        """Sus ajustes son parte de ella: se van con ella, **cada uno con su rastro en la auditoría**.

        Borrarlos de uno en uno sería pedirle al agricultor que deshaga su error en tres pasos, y dejarlos
        colgando reventaría al guardar (la base no deja un ajuste apuntando a una entrega que no existe).

        **Y su papel se va del disco**, que es lo que no se puede olvidar: un ajuste puede llevar la foto del
        básculero o el boletín del laboratorio, y si se borrara la entrega y el papel se quedara, habría
        papeles del agricultor —con su nombre y su NIF— en la carpeta de adjuntos sin que nada los nombre. Se
        comprueba **mirando el disco**, no confiando en el código.
        """
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": "121.00",
            },
        ).json()
        ajuste = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "peso",
                "origen": "bascula",
                "motivo": "la báscula dio menos kilos",
                "cantidad": "-100",
            },
        ).json()
        subido = cliente.post(
            f"/api/ventas/{entrega['id']}/ajustes/{ajuste['id']}/papel",
            headers=cuenta["cabeceras"],
            files={"fichero": ("bascula.png", b"\x89PNG\r\n\x1a\n datos", "image/png")},
        )
        assert subido.status_code == 200, subido.text
        from app import adjuntos

        with _sesion() as sesion:
            ruta = sesion.scalar(
                select(models.AjusteDeEntrega.fichero_ruta).where(
                    models.AjusteDeEntrega.id == ajuste["id"]
                )
            )
        assert ruta and (adjuntos.carpeta_de_adjuntos() / ruta).is_file()

        borrado = cliente.delete(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"])
        assert borrado.status_code == 200, borrado.text
        assert not (adjuntos.carpeta_de_adjuntos() / ruta).exists(), (
            "el papel del ajuste se ha quedado en el disco sin que nada lo nombre"
        )
        with _sesion() as sesion:
            assert sesion.scalar(
                select(models.AjusteDeEntrega).where(models.AjusteDeEntrega.id == ajuste["id"])
            ) is None, "el ajuste se ha quedado colgando"
            # Y el rastro está: el programa sabe que existió.
            acciones = [
                fila.accion
                for fila in sesion.scalars(
                    select(models.Auditoria).where(
                        models.Auditoria.entidad.in_(("ajuste_de_entrega", "venta_cosecha"))
                    )
                )
            ]
        assert "borrar" in acciones

    def test_una_cosecha_de_la_que_sale_una_entrega_no_se_borra(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """El «lote cosechado» del contrato, con su consecuencia: **la cosecha no se puede tirar**.

        Es el fallo que este proyecto más veces ha pagado: un dato que se puede borrar por un sitio mientras
        otro lo está usando deja el cuaderno diciendo cosas que no son. Aquí, sin la comprobación, el
        borrado reventaría con un fallo de la base en la cara (la clave ajena lo impide, pero nadie traduce
        el error); con ella, se dice **cuántas entregas la usan** y qué hacer.
        """
        cosecha = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-01",
                "parcela_id": crear_parcela()["id"],
                "producto": "Trigo blando",
                "cantidad_kg": 42000.0,
            },
        )
        assert cosecha.status_code == 201, cosecha.text
        cosecha_id = cosecha.json()["id"]
        entrega = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 42000.0,
                "unidad": "kg",
                "importe": "9870.00",
                "cosecha_id": cosecha_id,
            },
        )
        assert entrega.status_code == 201, entrega.text
        # Y la entrega dice de dónde salió, que es lo único que contesta «¿de dónde salió esta partida?».
        assert entrega.json()["de_que_cosecha"].startswith("Trigo blando")
        vista = cliente.get(f"/api/ventas/{entrega.json()['id']}", headers=cuenta["cabeceras"]).json()
        assert "01/07/2026" in vista["de_que_cosecha"]
        # Borrarla, no: se dice cuántas entregas la usan y qué hacer.
        borrado = cliente.delete(f"/api/cosecha/{cosecha_id}", headers=cuenta["cabeceras"])
        assert borrado.status_code == 409, borrado.text
        assert "1 entrega" in borrado.json()["detail"]
        # Y una labor que no es una cosecha no puede ser el lote del que salió una entrega.
        labor = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "fecha": "2026-07-02", "tipo": "labrar"},
        )
        if labor.status_code == 201:
            mal = cliente.post(
                "/api/ventas",
                headers=cuenta["cabeceras"],
                json={
                    "campana_id": campana["id"],
                    "fecha": "2026-07-11",
                    "producto": "Trigo blando",
                    "cantidad": 1000.0,
                    "unidad": "kg",
                    "importe": "100.00",
                    "cosecha_id": labor.json()["id"],
                },
            )
            assert mal.status_code == 422, mal.text
            assert "cosecha" in mal.json()["detail"].lower()

    def test_la_cosecha_de_otra_finca_no_se_puede_enlazar(
        self, cliente, cuenta, campana, crear_cuenta, crear_parcela
    ):
        """El aislamiento también en el enlace nuevo: 404 y no 403 (contrato A13)."""
        cosecha = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-01",
                "parcela_id": crear_parcela()["id"],
                "producto": "Trigo blando",
                "cantidad_kg": 42000.0,
            },
        ).json()
        otra = crear_cuenta("otra-cosecha-t12@ejemplo.test", nombre="Otro", nif="87654321X")
        su_campana = cliente.get("/api/campanas/actual", headers=otra["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/ventas",
            headers=otra["cabeceras"],
            json={
                "campana_id": su_campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "cosecha_id": cosecha["id"],
            },
        )
        assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# El guardián: lo que se acepta tiene que caber donde se guarda
# --------------------------------------------------------------------------


class TestLoQueSeAceptaCabeDondeSeGuarda:
    """Ningún texto del dinero se acepta con más letras de las que caben en su columna.

    **Por qué existe esta prueba** (revisión del T12). El defecto más caro que ha pagado este proyecto en
    producción fue `auditoria.accion`: una etiqueta de más de 30 caracteres que en el ordenador del
    agricultor (SQLite) se guardaba sin decir nada y **en PostgreSQL tumbaba la operación entera**. El T12
    volvió a abrir la misma puerta en nueve campos del dinero (el nombre del comprador, la referencia del
    banco, la evidencia de un ajuste, el número de una factura…).

    Lo que se comprueba aquí es **la declaración, no el caso concreto**: para cada campo de texto de los
    cuatro esquemas del dinero que va a una columna con tope, el esquema tiene que declarar **el mismo
    ancho que la columna**, leído de la columna. Así, el día que alguien ensanche una columna, el tope se
    ensancha con ella, y el día que añada un campo de texto al dinero y se olvide del tope, esta prueba lo
    dice. Los casos concretos (los nueve campos, por la API) los mide la prueba de la revisión.
    """

    # Los cuatro esquemas de entrada del dinero, cada uno con la tabla donde acaba lo que acepta.
    CASOS = [
        ("VentaEntrada", "VentaDeCosecha"),
        ("AjusteEntrada", "AjusteDeEntrega"),
        ("CobroEntrada", "Cobro"),
        ("FacturaEmitidaEntrada", "FacturaEmitida"),
    ]

    def test_cada_campo_de_texto_del_dinero_declara_el_ancho_de_su_columna(self):
        from typing import get_args

        from app import schemas

        sin_tope = []
        for nombre_del_esquema, nombre_de_la_tabla in self.CASOS:
            esquema = getattr(schemas, nombre_del_esquema, None)
            assert esquema is not None, f"no existe el esquema {nombre_del_esquema}"
            modelo = getattr(models, nombre_de_la_tabla)
            for nombre, columna in modelo.__table__.columns.items():
                ancho = getattr(columna.type, "length", None)
                if not ancho or nombre not in esquema.model_fields:
                    continue
                campo = esquema.model_fields[nombre]
                anotacion = campo.annotation
                es_de_texto = anotacion is str or str in get_args(anotacion)
                if not es_de_texto:
                    continue
                topes = [
                    getattr(meta, "max_length", None)
                    for meta in getattr(campo, "metadata", [])
                    if getattr(meta, "max_length", None)
                ]
                if not topes:
                    sin_tope.append(
                        f"{nombre_del_esquema}.{nombre}: se acepta texto de cualquier largo y su columna "
                        f"({modelo.__tablename__}.{nombre}) admite {ancho}. En SQLite se guardaría; en "
                        "PostgreSQL falla la operación entera."
                    )
                elif topes[0] != ancho:
                    sin_tope.append(
                        f"{nombre_del_esquema}.{nombre}: el esquema admite {topes[0]} caracteres y la "
                        f"columna admite {ancho}."
                    )
        assert not sin_tope, "\n  ".join(["hay campos del dinero sin tope o con el tope mal:"] + sin_tope)

    def test_el_importe_mas_grande_que_se_acepta_cabe_en_su_columna(self):
        """Y el tope del importe, por arriba, tiene que caber: si no, vuelve el `DataError` de PostgreSQL.

        `dinero.a_texto` ya se niega a devolver un texto que no quepa (`MAXIMO_DE_CIFRAS`), pero eso sería
        un 500 con una frase de programador: lo que se comprueba aquí es que **lo que el esquema acepta**
        quepa, que es lo que hace que el rechazo sea un 422 con la frase del agricultor.
        """
        for tope, es_precio in ((dinero.MAXIMO_DE_UN_IMPORTE, False), (dinero.MAXIMO_DE_UN_PRECIO, True)):
            assert dinero.cabe_en_el_dinero(tope, es_precio=es_precio)
            decimales = 6 if es_precio else 2
            texto = dinero.a_texto(dinero.redondea(tope, decimales), decimales)
            assert len(texto) < dinero.MAXIMO_DE_CIFRAS, (
                f"el importe máximo que se acepta se guarda como «{texto}», que mide {len(texto)} y la "
                f"columna {dinero.MAXIMO_DE_CIFRAS}"
            )
            # Y por encima del tope no cabe: es lo que contesta 422 en vez de romper.
            assert not dinero.cabe_en_el_dinero(tope + Decimal("0.01"), es_precio=es_precio)
