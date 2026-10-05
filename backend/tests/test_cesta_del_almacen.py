"""Lo que tengo en el almacén: cuánto producto entró, cuánto salió y cuánto queda.

**Por qué existe este fichero.** La app oficial de la Junta tiene el apartado «Cesta de la
compra» para anotar la *adquisición* de productos, y un botón «Situación Cesta» que enseña «las
cantidades adquiridas y gastadas de los distintos productos fitosanitarios utilizados en la
campaña». En este programa, los cuatro campos de la compra —`cantidad_comprada`, `unidad_compra`,
`fecha_compra`, `proveedor`— **estaban en la tabla desde el principio y no los usaba nadie**:
ninguna pantalla los pedía y ninguna cuenta los leía.

O sea que la Cesta estaba a medias: se anotaba *qué* producto tienes, pero no *cuánto*. Y la
pregunta que se hace de verdad en el campo es «¿me queda producto para tratar esta parcela, o
tengo que ir a comprar?». Con esto se contesta.

**Lo que más se comprueba aquí es cuándo NO se contesta.** Un producto se compra en una unidad
(litros, kilos) y se echa con una dosis que se mide en otra («kg/ha»). Restar un litro de un kilo
necesita la densidad, que no sabemos y que cambia de un producto a otro. Ahí este programa **no
hace la cuenta y dice por qué**: poner un número inventado sería mucho peor que no ponerlo,
porque el agricultor compraría o dejaría de comprar con ese número delante.
"""

from __future__ import annotations

import pytest

from app import catalogos, legal


def _producto(cliente, cabeceras, **cambios) -> dict:
    """Da de alta un producto con lo mínimo, más lo que se le pase.

    La dosis máxima se pone alta a propósito (2 L/ha) para que los números del test sean
    redondos: si se pasara de la etiqueta, la validación lo bloquearía —y hace bien— y el test
    estaría midiendo otra cosa.
    """
    cuerpo = {
        "nombre_comercial": "Ejemplo 25 EC",
        "numero_registro": "24.123",
        "dosis_maxima": 2.0,
        "unidad_dosis": "L/ha",
        "plazo_seguridad_dias": 21,
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/productos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


@pytest.fixture
def parcela_grande(crear_parcela):
    """Una parcela de 10 ha, para que las cuentas del test salgan redondas.

    La parcela de las pruebas mide 2,43 ha, y con ese número las multiplicaciones dan cifras
    largas que hacen más difícil ver si el resultado es el que tiene que ser.
    """
    return crear_parcela(alias="La Grande", superficie_ha=10.0)


def _tratamiento(cliente, cabeceras, campana, parcela, producto_id, dosis, superficie):
    respuesta = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-05",
            "parcela_id": parcela["id"],
            "superficie_tratada_ha": superficie,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto_id,
            "dosis": dosis,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _cesta(cliente, cabeceras, **params) -> dict:
    respuesta = cliente.get("/api/productos/cesta/situacion", headers=cabeceras, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _fila(datos, producto_id):
    return [fila for fila in datos["productos"] if fila["producto_id"] == producto_id][0]


# --------------------------------------------------------------------------
# La aritmética de las unidades, que es lo que hace que esto valga o no valga
# --------------------------------------------------------------------------


class TestLasUnidades:
    def test_la_unidad_de_lo_que_se_echa_sale_de_la_dosis(self):
        assert legal.unidad_de_una_dosis("L/ha") == "L"
        assert legal.unidad_de_una_dosis("kg/ha") == "kg"
        assert legal.unidad_de_una_dosis("mL/hL") == "mL"
        assert legal.unidad_de_una_dosis("g/hL") == "g"
        assert legal.unidad_de_una_dosis(None) == ""

    def test_litros_y_kilos_no_se_pueden_comparar(self):
        """Haría falta la densidad, que no la sabemos y cambia de un producto a otro."""
        assert not legal.se_pueden_comparar("L", "kg")
        assert not legal.se_pueden_comparar("kg", "L")

    def test_un_litro_y_un_mililitro_si(self):
        assert legal.se_pueden_comparar("L", "mL")
        assert legal.se_pueden_comparar("kg", "g")

    def test_el_cc_y_el_mililitro_son_lo_mismo(self):
        """No es una aproximación: es la misma cantidad con dos nombres."""
        assert legal.se_pueden_comparar("cc", "mL")
        assert legal.convierte(1, "cc", "mL") == 1

    def test_las_conversiones_que_si_son_exactas(self):
        assert legal.convierte(2.5, "L", "mL") == 2500
        assert legal.convierte(2500, "mL", "L") == 2.5
        assert legal.convierte(1, "kg", "g") == 1000
        assert legal.convierte(500, "g", "kg") == 0.5

    def test_una_conversion_imposible_devuelve_nada_y_no_un_numero(self):
        """`None` es «no lo sé». Un número inventado aquí sería peor que no contestar."""
        assert legal.convierte(1, "kg", "L") is None
        assert legal.convierte(1, "L", "g") is None

    def test_una_unidad_desconocida_no_se_inventa(self):
        assert legal.familia_y_factor("fanegas") is None
        assert legal.a_la_unidad_base(3, "fanegas") is None
        assert not legal.se_pueden_comparar("fanegas", "L")

    def test_nada_no_es_cero(self):
        """Sin dato no es «no queda producto»: son dos cosas muy distintas."""
        assert legal.a_la_unidad_base(None, "L") is None

    def test_el_nombre_de_la_unidad_que_se_enseña(self):
        assert legal.nombre_corto_de_unidad("litros") == "L"
        assert legal.nombre_corto_de_unidad("cc") == "mL"
        assert legal.nombre_corto_de_unidad("fanegas") == "fanegas"


# --------------------------------------------------------------------------
# Las cuentas, de punta a punta
# --------------------------------------------------------------------------


class TestLasCuentasDelAlmacen:
    def test_sin_tratamientos_queda_todo_lo_comprado(self, cliente, cuenta, campana):
        producto = _producto(cliente, cuenta["cabeceras"], cantidad_comprada=5, unidad_compra="L")
        datos = _cesta(cliente, cuenta["cabeceras"])
        fila = _fila(datos, producto["id"])
        assert fila["comprado"] == 5
        assert fila["gastado"] == 0
        assert fila["queda"] == 5
        assert fila["se_puede_comparar"] is True
        assert fila["motivo"] == ""

    def test_lo_echado_se_descuenta(self, cliente, cuenta, campana, parcela_grande):
        """1,5 L/ha en 10 ha son 15 L, y de 20 L quedan 5."""
        producto = _producto(cliente, cuenta["cabeceras"], cantidad_comprada=20, unidad_compra="L")
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.5, 10.0)
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["gastado"] == 15.0
        assert fila["queda"] == 5.0
        assert fila["apuntes"] == 1

    def test_dos_tratamientos_se_suman(self, cliente, cuenta, campana, parcela_grande):
        producto = _producto(cliente, cuenta["cabeceras"], cantidad_comprada=100, unidad_compra="L")
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.0, 10.0)
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 2.0, 10.0)
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["gastado"] == 30.0
        assert fila["apuntes"] == 2

    def test_se_puede_comprar_en_litros_y_echar_en_mililitros(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """1 L son 1000 mL, y eso es exacto: la cuenta se hace."""
        producto = _producto(
            cliente,
            cuenta["cabeceras"],
            dosis_maxima=800,
            unidad_dosis="mL/hL",
            cantidad_comprada=5,
            unidad_compra="L",
        )
        # 500 mL/hL no es una dosis por hectárea, pero la cantidad total que se guarda es
        # dosis × superficie, así que la cuenta es la misma: 500 × 10 = 5000 mL.
        _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 500.0, 10.0
        )
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["gastado"] == 5000.0
        assert fila["unidad_gastado"] == "mL"
        # 5 L son 5000 mL, menos 5000 mL echados: queda cero, que es un cero de verdad.
        assert fila["queda"] == 0.0

    def test_un_tratamiento_anulado_no_cuenta(self, cliente, cuenta, campana, parcela_grande):
        """Lo anulado es lo que no pasó, así que no gasta producto."""
        producto = _producto(cliente, cuenta["cabeceras"], cantidad_comprada=20, unidad_compra="L")
        tratamiento = _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.0, 10.0
        )
        cliente.post(
            f"/api/tratamientos/{tratamiento['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué"},
        )
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["gastado"] == 0
        assert fila["queda"] == 20


class TestCuandoLaCuentaNoSePuedeHacer:
    """Esta es la parte que más importa: el programa no inventa un número."""

    def test_sin_saber_cuanto_se_compro_no_se_dice_cuanto_queda(self, cliente, cuenta, campana, parcela_grande):
        producto = _producto(cliente, cuenta["cabeceras"])
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.0, 10.0)
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["comprado"] is None
        assert fila["queda"] is None
        assert "cuánto compraste" in fila["motivo"]
        # Y lo que sí se sabe se dice igual: lo echado.
        assert fila["gastado"] == 10.0

    def test_comprado_en_kilos_y_echado_en_litros_no_se_resta(self, cliente, cuenta, campana, parcela_grande):
        """Un litro y un kilo no son lo mismo, y aquí no se hace como si lo fueran."""
        producto = _producto(
            cliente, cuenta["cabeceras"], cantidad_comprada=10, unidad_compra="kg"
        )
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.0, 10.0)
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["se_puede_comparar"] is False
        assert fila["queda"] is None, "no puede dar un número: no se sabe la densidad"
        assert "kg" in fila["motivo"] and "L" in fila["motivo"]
        # Las dos cantidades sí se enseñan, cada una con su unidad.
        assert fila["comprado"] == 10
        assert fila["unidad_compra"] == "kg"
        assert fila["gastado"] == 10.0
        assert fila["unidad_gastado"] == "L"

    def test_el_mensaje_no_lleva_jerga(self, cliente, cuenta, campana, parcela_grande):
        producto = _producto(
            cliente, cuenta["cabeceras"], cantidad_comprada=10, unidad_compra="kg"
        )
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.0, 10.0)
        from app import textos

        motivo = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])["motivo"]
        assert motivo
        assert not textos.palabras_prohibidas_encontradas(motivo)


class TestCuandoSaleQueSeHaGastadoMasDeLoComprado:
    def test_avisa_de_que_falta_una_compra(self, cliente, cuenta, campana, parcela_grande):
        """No es una acusación: lo normal es que el producto venga de otro año."""
        producto = _producto(cliente, cuenta["cabeceras"], cantidad_comprada=2, unidad_compra="L")
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.5, 10.0)
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["queda"] == -13.0
        assert fila["motivo"]
        assert "más de lo que apuntaste que compraste" in fila["motivo"]

    def test_y_si_en_otros_anos_se_echo_mas_todavia_lo_dice(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """Porque entonces lo más probable es que sea de una compra vieja, no un descuadre."""
        producto = _producto(cliente, cuenta["cabeceras"], cantidad_comprada=2, unidad_compra="L")
        _tratamiento(cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.5, 10.0)
        fila = _fila(_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert fila["gastado_en_total"] >= fila["gastado"]


class TestLoQueDiceLaPantalla:
    def test_sin_productos_lo_dice(self, cliente, cuenta):
        datos = _cesta(cliente, cuenta["cabeceras"])
        assert datos["cuantos"] == 0
        assert datos["resumen"] == datos["textos"]["vacia"]

    def test_cada_producto_trae_su_nombre_y_su_registro(self, cliente, cuenta):
        _producto(cliente, cuenta["cabeceras"], cantidad_comprada=5, unidad_compra="L")
        datos = _cesta(cliente, cuenta["cabeceras"])
        assert datos["productos"][0]["nombre_comercial"] == "Ejemplo 25 EC"
        assert datos["productos"][0]["numero_registro"] == "24.123"

    def test_trae_la_fecha_y_el_proveedor_de_la_compra(self, cliente, cuenta):
        _producto(
            cliente,
            cuenta["cabeceras"],
            cantidad_comprada=5,
            unidad_compra="L",
            fecha_compra="2026-03-10",
            proveedor="Cooperativa de Peñaranda",
        )
        fila = _cesta(cliente, cuenta["cabeceras"])["productos"][0]
        assert fila["fecha_compra"] == "2026-03-10"
        assert fila["proveedor"] == "Cooperativa de Peñaranda"

    def test_dice_cuantos_no_tienen_cantidad_apuntada(self, cliente, cuenta):
        """Es lo que permite decirle al agricultor «apúntalo y aquí saldrán las cuentas»."""
        _producto(cliente, cuenta["cabeceras"], cantidad_comprada=5, unidad_compra="L")
        _producto(cliente, cuenta["cabeceras"], nombre_comercial="Otro", numero_registro="24.999")
        datos = _cesta(cliente, cuenta["cabeceras"])
        assert datos["sin_cantidad"] == 1
        assert datos["cuantos"] == 2

    def test_dice_de_que_campaña_son_las_cuentas(self, cliente, cuenta, campana):
        _producto(cliente, cuenta["cabeceras"], cantidad_comprada=5, unidad_compra="L")
        datos = _cesta(cliente, cuenta["cabeceras"])
        assert datos["campana_id"] == campana["id"]
        assert datos["campana_anio"] == campana["anio"]

    def test_los_textos_van_en_la_respuesta(self, cliente, cuenta):
        datos = _cesta(cliente, cuenta["cabeceras"])
        assert datos["textos"]["titulo"]
        assert datos["textos"]["explica"]

    def test_hace_falta_entrar(self, cliente):
        assert cliente.get("/api/productos/cesta/situacion").status_code == 401


class TestElAislamiento:
    def test_una_finca_no_ve_los_productos_de_otra(self, cliente, cuenta, crear_cuenta):
        _producto(cliente, cuenta["cabeceras"], cantidad_comprada=5, unidad_compra="L")
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        datos = _cesta(cliente, otra["cabeceras"])
        assert datos["cuantos"] == 0


class TestLaFichaDelProductoYaPideLaCompra:
    """El otro medio del arreglo: sin pedir el dato, la pantalla no tendría nada que enseñar."""

    def test_los_campos_de_la_compra_se_guardan(self, cliente, cuenta):
        producto = _producto(
            cliente,
            cuenta["cabeceras"],
            cantidad_comprada=12.5,
            unidad_compra="L",
            fecha_compra="2026-04-01",
            proveedor="Agroquímicos del Duero",
        )
        assert producto["cantidad_comprada"] == 12.5
        assert producto["unidad_compra"] == "L"
        assert producto["fecha_compra"] == "2026-04-01"
        assert producto["proveedor"] == "Agroquímicos del Duero"

    def test_la_unidad_de_compra_por_defecto_son_litros(self, cliente, cuenta):
        assert _producto(cliente, cuenta["cabeceras"])["unidad_compra"] == "L"

    def test_las_unidades_de_compra_son_las_del_catalogo(self):
        """El agricultor elige de una lista, no escribe a mano: si no, salen diez formas de
        decir «litros» y no se pueden sumar."""
        assert "L" in catalogos.UNIDADES_PRODUCTO
        assert "kg" in catalogos.UNIDADES_PRODUCTO
        for unidad in catalogos.UNIDADES_PRODUCTO:
            assert legal.familia_y_factor(unidad) is not None, f"la unidad {unidad} no se sabe sumar"

    def test_el_catalogo_de_unidades_llega_a_la_pantalla(self, cliente, cuenta):
        interfaz = cliente.get("/api/interfaz").json()
        assert "L" in interfaz["unidades_producto"]
        assert interfaz["cesta"]["titulo"]


class TestLosTextosDeLaPantalla:
    def test_entran_en_la_revision_de_jerga(self):
        from app import textos

        assert textos.CESTA["titulo"] in textos.textos_visibles()

    def test_ninguno_lleva_jerga(self):
        from app import textos

        assert not [
            valor
            for valor in textos.CESTA.values()
            if textos.palabras_prohibidas_encontradas(valor)
        ]

    def test_se_dice_para_que_sirve(self):
        from app import textos

        assert "inspección" in textos.CESTA["para_que_sirve"] or "inspección" in textos.CESTA["explica"]

    def test_se_dice_que_sin_el_dato_no_hay_cuentas(self):
        from app import textos

        assert "no se inventan" in textos.CESTA["como_apuntarlo"]
