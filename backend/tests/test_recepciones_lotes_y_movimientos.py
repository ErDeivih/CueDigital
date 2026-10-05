"""El almacén: el albarán que llega, los lotes y el libro de movimientos (T09).

**Por qué existe este fichero, y qué protege.** Hasta aquí, «lo que tengo en el almacén» se
calculaba comparando lo comprado (las líneas de las facturas) con lo gastado (los tratamientos), y la
pantalla del almacén enseña esa cuenta. Lo que no existía era **el libro**: qué entró de verdad, en
qué lote, y de qué lote salió lo que se ha echado.

Al añadir ese libro aparece el riesgo que el encargo prohíbe de forma expresa: **que la misma
mercancía se cuente dos veces**, una por la factura y otra por el movimiento de entrada. Este fichero
es lo que impide que eso pase sin que nadie se entere, y por eso lo primero que se comprueba aquí no
es que las cuentas salgan, sino que **no se sumen las dos** (clase
`TestElLibroNoSeSumaALaCesta`).

Los tres casos de aceptación del contrato que caen en este ticket están aquí con su nombre:

  · **A01** — compra de 5 L, aplicación de 2 L y de 3 L: saldo 0; el reenvío no duplica; anular la
    de 2 L devuelve 2 L. Es `TestElCasoA01PorEntero`.
  · **A02** — 2 L en 4 ha son 0,5 L/ha, y si falta el área la dosis es **desconocida** (no 2). Es
    `TestA02LaDosisPorHectareaNoEsLaCantidadTotal`.
  · **A15** — la factura llega después del albarán recibido: **una sola entrada** de almacén y el
    vínculo entre los dos documentos. Es `TestA15LaFacturaLlegaDespues`.

Y los dos textos de la casa: **un dato que no se sabe no es un cero** (una cantidad de albarán
ilegible deja el lote en «no se puede saber lo que queda», nunca en 0) y **nada se borra** (se anula
con motivo y queda el rastro).
"""

from __future__ import annotations

import json

import pytest

from app import legal, servicios

NIF_DEL_PROVEEDOR = "B34123456"


# --------------------------------------------------------------------------
# Ayudas: lo que hace la pantalla, hecho desde el test
# --------------------------------------------------------------------------


def _producto(cliente, cabeceras, **cambios) -> dict:
    """Un producto de la cesta. La dosis máxima se pone alta para que los números sean redondos."""
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


def _pedir_recepcion(cliente, cabeceras, **cambios):
    """Manda un albarán y devuelve la respuesta entera, para poder mirar el código."""
    cuerpo = {
        "fecha": "2026-03-15",
        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "proveedor_nif": NIF_DEL_PROVEEDOR,
        "numero_albaran": "A-2026-118",
        "lineas": [
            {
                "nombre": "Glifosato 36 SL",
                "categoria": "fitosanitario",
                "unidad": "L",
                "cantidad": 5.0,
                "unidad_de_la_cantidad": "L",
                "numero_lote": "4471-A",
                "fecha_caducidad": "2028-06-30",
                "presentacion": "garrafa de 5 L",
            }
        ],
    }
    cuerpo.update(cambios)
    return cliente.post("/api/almacen/recepciones", headers=cabeceras, json=cuerpo)


def _recepcion(cliente, cabeceras, **cambios) -> dict:
    respuesta = _pedir_recepcion(cliente, cabeceras, **cambios)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _existencias(cliente, cabeceras, **params) -> dict:
    respuesta = cliente.get("/api/almacen/existencias", headers=cabeceras, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _el_articulo(datos: dict, nombre: str) -> dict:
    for fila in datos["articulos"]:
        if fila["nombre"] == nombre:
            return fila
    raise AssertionError(f"no hay ningún artículo «{nombre}» en el almacén: {datos['articulos']}")


def _el_lote(articulo: dict, numero: str | None) -> dict:
    for fila in articulo["lotes"]:
        if fila["numero_lote"] == numero:
            return fila
    raise AssertionError(f"no hay ningún lote «{numero}»: {articulo['lotes']}")


def _un_tratamiento(cliente, cabeceras, campana, parcela, producto_id, dosis, superficie):
    """Un tratamiento con su total ya calculado por el programa (dosis × hectáreas)."""
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


def _una_salida(cliente, cabeceras, **cambios):
    """Gastar de un lote. Devuelve la respuesta entera: el código importa (201 o 200)."""
    cuerpo = {"apunte_tipo": "tratamiento", "apunte_id": 0, "lote_id": 0}
    cuerpo.update(cambios)
    return cliente.post("/api/almacen/salidas", headers=cabeceras, json=cuerpo)


def _una_factura(cliente, cuenta, **cambios) -> dict:
    """Una factura de compra sin fichero, como cuando se teclea a mano."""
    cuerpo = {
        "fecha": "2026-03-20",
        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "proveedor_nif": NIF_DEL_PROVEEDOR,
        "numero_factura": "2026/00123",
        "total": 100.0,
        "leida_por": "a mano",
        "lineas": [{"descripcion": "GLIFOSATO 36% SL 5 L", "cantidad": 5.0, "unidad": "L"}],
    }
    cuerpo.update(cambios)
    respuesta = cliente.post(
        "/api/facturas",
        headers=cuenta["cabeceras"],
        data={"datos": json.dumps(cuerpo)},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _la_cesta(cliente, cabeceras, **params) -> dict:
    respuesta = cliente.get("/api/productos/cesta/situacion", headers=cabeceras, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _fila_de_la_cesta(datos: dict, producto_id: int) -> dict:
    return [fila for fila in datos["productos"] if fila["producto_id"] == producto_id][0]


@pytest.fixture
def parcela_grande(crear_parcela):
    """10 ha, para que las cuentas del test salgan redondas."""
    return crear_parcela(alias="La Grande", superficie_ha=10.0)


# --------------------------------------------------------------------------
# La aritmética del almacén, que es lo que hace que esto valga o no valga
# --------------------------------------------------------------------------


class TestLaAritmeticaDeLasExistencias:
    def test_la_misma_unidad_se_suma(self):
        assert servicios.se_pueden_sumar("L", "L") is True
        assert servicios.se_pueden_sumar("kg", "KG") is True

    def test_los_litros_y_los_kilos_no_se_suman(self):
        """Haría falta la densidad, que no sabemos y cambia de un producto a otro."""
        assert servicios.se_pueden_sumar("L", "kg") is False

    def test_dentro_de_una_familia_si_se_suma(self):
        """1 L = 1000 mL es exacto, no una aproximación."""
        assert servicios.se_pueden_sumar("L", "mL") is True
        assert servicios.pasa_a_la_unidad(2.5, "L", "mL") == 2500.0

    def test_una_cantidad_sin_unidad_no_se_suma_con_nada(self):
        assert servicios.se_pueden_sumar(None, "L") is False
        assert servicios.se_pueden_sumar("", "L") is False

    def test_una_unidad_que_no_conocemos_solo_se_suma_consigo_misma(self):
        """Las semillas se cuentan por unidades, y una unidad no se convierte a kilos nunca."""
        assert servicios.se_pueden_sumar("ud", "ud") is True
        assert servicios.se_pueden_sumar("ud", "kg") is False

    def test_el_saldo_se_calcula_con_los_cuatro_tipos(self):
        cuenta = servicios.saldo_de_un_conjunto(
            [
                {"tipo": "entrada", "cantidad": 5.0, "unidad": "L"},
                {"tipo": "salida", "cantidad": 2.0, "unidad": "L"},
                {"tipo": "merma", "cantidad": 0.5, "unidad": "L"},
                {"tipo": "ajuste", "cantidad": 0.5, "unidad": "L"},
            ]
        )
        assert cuenta["entradas"] == 5.0
        assert cuenta["salidas"] == 2.0
        assert cuenta["mermas"] == 0.5
        assert cuenta["ajustes"] == 0.5
        assert cuenta["saldo"] == 3.0

    def test_un_ajuste_negativo_quita(self):
        cuenta = servicios.saldo_de_un_conjunto(
            [
                {"tipo": "entrada", "cantidad": 5.0, "unidad": "L"},
                {"tipo": "ajuste", "cantidad": -1.5, "unidad": "L"},
            ]
        )
        assert cuenta["saldo"] == 3.5

    def test_sin_movimientos_el_lote_esta_a_cero_y_eso_se_sabe(self):
        cuenta = servicios.saldo_de_un_conjunto([], "L")
        assert cuenta["saldo"] == 0.0
        assert cuenta["sin_movimientos"] is True

    def test_falta_la_cantidad_no_es_cero(self):
        """El caso del encargo: un albarán sin la cantidad legible."""
        cuenta = servicios.saldo_de_un_conjunto(
            [
                {"tipo": "entrada", "cantidad": None, "unidad": "L"},
                {"tipo": "salida", "cantidad": 2.0, "unidad": "L"},
            ]
        )
        assert cuenta["saldo"] is None
        assert cuenta["motivo_codigo"] == "AL30_falta_la_cantidad"
        assert cuenta["movimientos_sin_cantidad"] == 1

    def test_falta_la_unidad_no_es_cero(self):
        """Y no es lo mismo que falte la cantidad: aquí se sabe **cuánto**, no **en qué se mide**."""
        cuenta = servicios.saldo_de_un_conjunto([{"tipo": "entrada", "cantidad": 5.0}])
        assert cuenta["saldo"] is None
        assert cuenta["motivo_codigo"] == "AL32_falta_la_unidad"
        assert "sin decir en qué se mide" in cuenta["motivo"]

    def test_unidades_que_no_se_pueden_comparar_no_dan_un_numero(self):
        cuenta = servicios.saldo_de_un_conjunto(
            [
                {"tipo": "entrada", "cantidad": 5.0, "unidad": "L"},
                {"tipo": "salida", "cantidad": 3.0, "unidad": "kg"},
            ]
        )
        assert cuenta["saldo"] is None
        assert cuenta["motivo_codigo"] == "AL31_unidades_que_no_cuadran"
        assert cuenta["unidades_que_no_cuadran"] == ["kg"]

    def test_el_saldo_negativo_se_devuelve_tal_cual_y_marcado(self):
        """El contrato lo prohíbe expresamente: «saldo negativo señala falta de entrada o revisión,
        no inventa una compra». Convertirlo en cero sería esconder el problema."""
        cuenta = servicios.saldo_de_un_conjunto(
            [
                {"tipo": "entrada", "cantidad": 3.0, "unidad": "L"},
                {"tipo": "salida", "cantidad": 5.0, "unidad": "L"},
            ]
        )
        assert cuenta["saldo"] == -2.0
        assert cuenta["motivo_codigo"] == "AL33_saldo_negativo"

    def test_el_ajuste_no_es_un_gasto(self):
        """Una merma y un ajuste no son consumo: no cuentan como producto echado en la tierra."""
        cuenta = servicios.saldo_de_un_conjunto(
            [
                {"tipo": "entrada", "cantidad": 5.0, "unidad": "L"},
                {"tipo": "merma", "cantidad": 2.0, "unidad": "L"},
            ]
        )
        assert cuenta["salidas"] == 0.0
        assert cuenta["saldo"] == 3.0


class TestA02LaDosisPorHectareaNoEsLaCantidadTotal:
    """**El fallo de diez veces.** 2 L en 4 ha son 0,5 L/ha, y el total son 2 L: el mismo número
    significa una cosa u otra según dónde esté. Y si falta el área, la dosis es **desconocida**."""

    def test_dos_litros_en_cuatro_hectareas_son_media_por_hectarea(self):
        assert legal.dosis_por_hectarea(2.0, 4.0) == 0.5

    def test_sin_saber_el_area_la_dosis_es_desconocida_no_dos(self):
        assert legal.dosis_por_hectarea(2.0, None) is None

    def test_un_area_de_cero_no_es_un_area_conocida(self):
        """En esta base, un tratamiento sin superficie apuntada se guarda con un 0 heredado: un cero
        **no** significa «se trató cero hectáreas», significa que no consta."""
        assert legal.dosis_por_hectarea(2.0, 0.0) is None

    def test_sin_saber_la_cantidad_tampoco_hay_dosis(self):
        assert legal.dosis_por_hectarea(None, 4.0) is None

    def test_la_salida_dice_las_dos_cifras_con_su_nombre(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """2 L en 4 ha: las dos cifras salen juntas y cada una con su nombre."""
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        datos = _existencias(cliente, cuenta["cabeceras"])
        lote = _el_lote(_el_articulo(datos, "Ejemplo 25 EC"), "4471-A")
        tratamiento = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 4.0
        )
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=tratamiento["id"],
            lote_id=lote["lote_id"],
        )
        assert respuesta.status_code == 201, respuesta.text
        cuerpo = respuesta.json()
        # El total (lo que se gastó) y la dosis (lo que se gasta por hectárea) son dos cosas.
        assert cuerpo["cantidad_total_gastada"] == 2.0
        assert cuerpo["unidad_de_la_cantidad"] == "L"
        assert cuerpo["dosis_por_hectarea"] == 0.5
        assert cuerpo["superficie_ha"] == 4.0

    def test_si_falta_el_area_la_dosis_es_desconocida_y_el_total_lo_pone_el_agricultor(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """Un tratamiento de una nave no tiene hectáreas, y eso está bien: lo que no se puede es
        decir que su dosis por hectárea es 0,5 (ni 2)."""
        producto = _producto(cliente, cuenta["cabeceras"])
        instalacion = cliente.post(
            "/api/instalaciones",
            headers=cuenta["cabeceras"],
            json={"alias": "El almacén grande", "tipo": "almacen"},
        ).json()
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A"
        )
        tratamiento = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-06-10",
                "tipo": "instalaciones",
                "instalacion_id": instalacion["id"],
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
                "plazo_reentrada_dias": 3,
            },
        ).json()
        # Sin cantidad en la petición: el apunte no dice el total, así que **no se multiplica la dosis
        # por nada**. Se pide el total, que es lo que evita la confusión de diez veces.
        sin_total = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=tratamiento["id"],
            lote_id=lote["lote_id"],
        )
        assert sin_total.status_code == 409, sin_total.text
        assert "dosis" in sin_total.json()["detail"]

        # Y con el total dicho por el agricultor, se apunta: lo que de verdad pasó se registra.
        con_total = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=tratamiento["id"],
            lote_id=lote["lote_id"],
            cantidad=2.0,
            unidad="L",
        )
        assert con_total.status_code == 201, con_total.text
        assert con_total.json()["cantidad_total_gastada"] == 2.0
        assert con_total.json()["dosis_por_hectarea"] is None


# --------------------------------------------------------------------------
# La recepción: el albarán que mete la mercancía
# --------------------------------------------------------------------------


class TestUnaRecepcionCompleta:
    def test_se_apunta_el_albaran_con_su_lote_y_su_entrada(self, cliente, cuenta):
        guardada = _recepcion(cliente, cuenta["cabeceras"])
        albaran = guardada["recepcion"]
        assert guardada["ya_estaba"] is False
        assert albaran["numero_albaran"] == "A-2026-118"
        assert albaran["proveedor"].startswith("COOPERATIVA")
        assert albaran["fecha"] == "2026-03-15"
        assert albaran["anulada"] is False
        assert len(albaran["lineas"]) == 1
        assert albaran["lineas"][0]["cantidad"] == 5.0
        assert albaran["lineas"][0]["numero_lote"] == "4471-A"
        assert albaran["lineas"][0]["articulo"] == "Glifosato 36 SL"
        # Y la entrada del libro, que es lo que de verdad mete existencias.
        assert albaran["entradas"] == 1

    def test_la_campana_de_la_compra_la_guarda_su_factura(self, cliente, cuenta):
        """El almacén no lleva campaña propia (ver `test_el_almacen_no_cuelga_del_ano`), y no se
        pierde: el papel que compra el producto es la factura, y la factura sí dice de qué año es."""
        producto = _producto(cliente, cuenta["cabeceras"], unidad_compra="L")
        factura = _una_factura(
            cliente,
            cuenta,
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 5 L",
                    "cantidad": 5.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        assert factura["campana_id"] is not None

    def test_un_albaran_sin_fecha_no_se_queda_con_la_de_hoy(self, cliente, cuenta):
        """Un papel sin fecha se apunta sin fecha: ponerle la de hoy sería inventarse un dato que
        después no se puede distinguir de uno de verdad."""
        guardada = _recepcion(cliente, cuenta["cabeceras"], fecha=None)
        assert guardada["recepcion"]["fecha"] is None
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        assert libro[0]["fecha"] is None

    def test_el_almacen_no_cuelga_del_ano_y_eso_es_una_decision(self):
        """**Sin `campana_id`, a propósito** (03/10/2026).

        El contrato pide conservar campaña, ejercicio y fecha como dimensiones distintas, y esto no lo
        contradice: la campaña de una compra la guarda su **factura**, y la de un consumo, el **apunte**
        del que sale la salida. Lo que no lleva el almacén es una campaña propia, y el motivo se puede
        comprobar: el año del cuaderno tiene tres listas escritas a mano en `explotacion.py` —los
        apuntes, las tierras con su cultivo y «las demás cosas»— y una prueba que exige que **toda**
        tabla que cuelga de la campaña esté nombrada en una de ellas; un movimiento de almacén no es un
        apunte del cuaderno, así que nombrarlo es una decisión de otro ticket.

        Esta prueba está para que nadie lo «arregle» sin leer el porqué (está entero en
        `models.MovimientoDeExistencias`) y sin tocar antes esas dos listas y sus guardianes. Lo que sí
        tiene el libro es **fecha**, que es lo que un movimiento tiene, y por ella se busca.
        """
        from app import models

        for tabla in ("recepciones", "movimientos_de_existencias"):
            columnas = models.Base.metadata.tables[tabla].columns
            assert "campana_id" not in columnas, (
                f"«{tabla}» ha vuelto a colgar del año: lee la decisión de `models.MovimientoDeExistencias` "
                "y las dos listas de `explotacion.py` antes de hacerlo"
            )

    def test_el_libro_se_busca_por_fechas(self, cliente, cuenta):
        """Porque es lo que un movimiento tiene: el día en que entró o salió."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-1",
            fecha="2026-03-01",
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "L-1"}],
        )
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-2",
            fecha="2026-09-01",
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 3.0, "numero_lote": "L-2"}],
        )
        de_marzo = cliente.get(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            params={"desde": "2026-03-01", "hasta": "2026-03-31"},
        ).json()
        assert [fila["fecha"] for fila in de_marzo] == ["2026-03-01"]
        los_albaranes = cliente.get(
            "/api/almacen/recepciones",
            headers=cuenta["cabeceras"],
            params={"desde": "2026-08-01"},
        ).json()
        assert [fila["numero_albaran"] for fila in los_albaranes] == ["A-2"]

    def test_un_movimiento_sin_fecha_no_entra_en_un_rango(self, cliente, cuenta):
        """No se sabe si estaba dentro del periodo, así que no se puede afirmar que estuviera."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            fecha=None,
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0}],
        )
        del_periodo = cliente.get(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            params={"desde": "2026-01-01", "hasta": "2026-12-31"},
        ).json()
        assert del_periodo == []
        # Y sigue estando en el libro cuando no se le pide un periodo.
        assert len(cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()) == 1

    def test_el_albaran_sale_en_la_lista(self, cliente, cuenta):
        guardada = _recepcion(cliente, cuenta["cabeceras"])
        listado = cliente.get("/api/almacen/recepciones", headers=cuenta["cabeceras"]).json()
        assert [fila["id"] for fila in listado] == [guardada["recepcion"]["id"]]

    def test_el_albaran_se_puede_ver_por_su_identificador(self, cliente, cuenta):
        guardada = _recepcion(cliente, cuenta["cabeceras"])
        ficha = cliente.get(
            f"/api/almacen/recepciones/{guardada['recepcion']['id']}",
            headers=cuenta["cabeceras"],
        )
        assert ficha.status_code == 200
        assert ficha.json()["numero_albaran"] == "A-2026-118"

    def test_queda_apuntado_en_la_auditoria(self, cliente, cuenta, db_sesion):
        from app import models

        guardada = _recepcion(cliente, cuenta["cabeceras"])
        rastro = [
            fila
            for fila in db_sesion.query(models.Auditoria).all()
            if fila.entidad == "recepcion"
        ]
        assert [fila.accion for fila in rastro] == ["crear"]
        assert rastro[0].entidad_id == guardada["recepcion"]["id"]
        assert rastro[0].datos["lineas"] == 1
        assert rastro[0].usuario_id is not None

    def test_varias_lineas_en_el_mismo_albaran(self, cliente, cuenta):
        """Un albarán trae lo que trae: un producto, un abono y una cosa más."""
        guardada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "A"},
                {
                    "nombre": "Nitrato amónico",
                    "categoria": "abono",
                    "unidad": "kg",
                    "cantidad": 500.0,
                    "numero_lote": "B",
                },
                {"nombre": "Semilla de veza", "categoria": "semilla", "unidad": "kg", "cantidad": 25.0},
            ],
        )
        assert len(guardada["recepcion"]["lineas"]) == 3
        assert guardada["recepcion"]["entradas"] == 3
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert _el_articulo(datos, "Nitrato amónico")["saldo"] == 500.0
        assert _el_articulo(datos, "Semilla de veza")["saldo"] == 25.0

    def test_un_albaran_sin_lineas_no_apunta_nada(self, cliente, cuenta):
        respuesta = _pedir_recepcion(cliente, cuenta["cabeceras"], lineas=[])
        assert respuesta.status_code == 400
        assert "albarán sin decir qué venía" in respuesta.json()["detail"]

    def test_una_linea_que_no_dice_que_ha_llegado_no_se_puede_apuntar(self, cliente, cuenta):
        respuesta = _pedir_recepcion(
            cliente, cuenta["cabeceras"], lineas=[{"cantidad": 5.0, "unidad": "L"}]
        )
        assert respuesta.status_code == 400
        assert "no dices qué ha llegado" in respuesta.json()["detail"]

    def test_el_articulo_se_engancha_al_producto_de_la_cesta(self, cliente, cuenta):
        """Es lo que hace que el almacén hable de lo mismo que el resto del cuaderno."""
        producto = _producto(cliente, cuenta["cabeceras"], cantidad_comprada=5.0, unidad_compra="L")
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {"producto_id": producto["id"], "cantidad": 5.0, "unidad_de_la_cantidad": "L"}
            ],
        )
        datos = _existencias(cliente, cuenta["cabeceras"])
        articulo = _el_articulo(datos, "Ejemplo 25 EC")
        assert articulo["producto_id"] == producto["id"]
        assert articulo["categoria"] == "fitosanitario"
        # La unidad sale de la ficha del producto (`unidad_compra`), que es un dato que ya estaba.
        assert articulo["unidad"] == "L"

    def test_el_articulo_de_un_abono_se_queda_sin_unidad_si_nadie_la_dice(self, cliente, cuenta):
        """Un abono no dice su unidad en ninguna parte: inventarse «kg» para uno líquido sería un
        error que después no se puede deshacer."""
        abono = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Nitrato amónico 33,5%", "tipo": "mineral", "riqueza_n": 33.5},
        ).json()
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[{"fertilizante_id": abono["id"], "cantidad": 500.0, "numero_lote": "B"}],
        )
        datos = _existencias(cliente, cuenta["cabeceras"])
        articulo = _el_articulo(datos, "Nitrato amónico 33,5%")
        assert articulo["fertilizante_id"] == abono["id"]
        assert articulo["unidad"] is None
        # Y sin unidad no se hace la cuenta: se dice que no se puede saber.
        assert articulo["saldo"] is None
        assert "sin decir en qué se mide" in articulo["motivo"]


class TestUnaRecepcionSinAlgunDato:
    """**Un dato que no se sabe no es un cero.** El caso que el encargo pide de forma expresa: un
    albarán que llega sin la cantidad o sin la unidad."""

    def test_sin_la_cantidad_se_apunta_igual_y_se_dice_que_no_se_sabe(self, cliente, cuenta):
        guardada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad": "L",
                    "numero_lote": "4471-A",
                    "descripcion": "la casilla de la cantidad estaba borrada",
                }
            ],
        )
        linea = guardada["recepcion"]["lineas"][0]
        assert linea["cantidad"] is None
        # La línea **existe** (la mercancía llegó), pero la cantidad no se sabe.
        assert linea["unidad"] == "L"
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        lote = _el_lote(articulo, "4471-A")
        assert lote["saldo"] is None
        assert "sin la cantidad apuntada" in lote["motivo"]
        # Y **no** es un cero, que es lo que diría que no queda producto.
        assert lote["saldo"] != 0

    def test_sin_la_unidad_se_apunta_igual_y_no_se_hace_la_cuenta(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[{"nombre": "Glifosato 36 SL", "cantidad": 5.0, "numero_lote": "4471-A"}],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        assert articulo["unidad"] is None
        assert articulo["saldo"] is None
        assert articulo["motivo_codigo"] == "AL32_falta_la_unidad"

    def test_sin_caducidad_apuntada_el_lote_dice_que_no_se_sabe(self, cliente, cuenta):
        """El contrato lo pide así: «vencimiento desconocido no es vigente», y desde luego no es
        «está bien»."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "A"}],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL"), "A")
        assert lote["fecha_caducidad"] is None
        assert lote["caducado"] is None  # ni sí ni no: no se sabe

    def test_un_lote_caducado_se_marca(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad": "L",
                    "cantidad": 5.0,
                    "numero_lote": "VIEJO",
                    "fecha_caducidad": "2020-01-01",
                }
            ],
        )
        datos = _existencias(cliente, cuenta["cabeceras"])
        lote = _el_lote(_el_articulo(datos, "Glifosato 36 SL"), "VIEJO")
        assert lote["caducado"] is True
        assert datos["caducados"] == 1

    def test_un_lote_en_fecha_no_se_marca_como_caducado(self, cliente, cuenta):
        _recepcion(cliente, cuenta["cabeceras"])
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert _el_lote(_el_articulo(datos, "Glifosato 36 SL"), "4471-A")["caducado"] is False

    def test_sin_numero_de_lote_es_un_lote_sin_numero_no_un_lote_cero(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0}],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        assert articulo["cuantos_lotes"] == 1
        assert articulo["lotes"][0]["numero_lote"] is None
        assert articulo["lotes"][0]["saldo"] == 5.0


class TestLosLotesDeUnMismoArticulo:
    def test_dos_albaranes_con_lotes_distintos_son_dos_cuentas(self, cliente, cuenta):
        """Las existencias son **por lote**: un envase con otro número es otro envase, y si el
        fabricante avisa de uno hay que saber qué quedaba de ese."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-1",
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "L-1"}],
        )
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-2",
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 3.0, "numero_lote": "L-2"}],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        assert articulo["cuantos_lotes"] == 2
        assert _el_lote(articulo, "L-1")["saldo"] == 5.0
        assert _el_lote(articulo, "L-2")["saldo"] == 3.0
        assert articulo["saldo"] == 8.0

    def test_el_mismo_numero_de_lote_no_se_duplica(self, cliente, cuenta):
        """El envase que ya estaba en el almacén no se abre otra vez porque llegue otro albarán con
        el mismo número."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-1",
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "L-1"}],
        )
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-2",
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 2.0, "numero_lote": "L-1"}],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        assert articulo["cuantos_lotes"] == 1
        assert _el_lote(articulo, "L-1")["saldo"] == 7.0

    def test_la_caducidad_de_un_lote_que_ya_existe_no_se_cambia_y_se_avisa(self, cliente, cuenta):
        """Dos papeles que dicen fechas distintas no se arreglan eligiendo una: manda el envase."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-1",
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad": "L",
                    "cantidad": 5.0,
                    "numero_lote": "L-1",
                    "fecha_caducidad": "2028-06-30",
                }
            ],
        )
        segunda = _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-2",
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad": "L",
                    "cantidad": 2.0,
                    "numero_lote": "L-1",
                    "fecha_caducidad": "2029-01-31",
                }
            ],
        )
        assert any("caduca" in aviso for aviso in segunda["avisos"])
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL"), "L-1"
        )
        assert lote["fecha_caducidad"] == "2028-06-30"

    def test_los_lotes_que_no_se_pueden_sumar_avisan(self, cliente, cuenta):
        """Un lote en litros y otro en kilos del mismo artículo: no se suman, y se dice."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-1",
            lineas=[{"nombre": "Producto raro", "unidad": "L", "cantidad": 5.0, "numero_lote": "L-1"}],
        )
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-2",
            lineas=[{"nombre": "Producto raro", "unidad": "kg", "cantidad": 3.0, "numero_lote": "L-2"}],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Producto raro")
        assert articulo["saldo"] is None
        assert articulo["motivo_codigo"] == "AL31_unidades_que_no_cuadran"
        # Cada lote, por separado, sí sabe lo que tiene.
        assert _el_lote(articulo, "L-1")["saldo"] == 5.0
        assert _el_lote(articulo, "L-2")["saldo"] == 3.0


# --------------------------------------------------------------------------
# Duplicados: el mismo albarán dos veces
# --------------------------------------------------------------------------


class TestElMismoAlbaranDosVeces:
    """La protección del encargo: «recibir dos veces el mismo albarán no puede duplicar existencias»."""

    def test_el_segundo_envio_devuelve_el_que_ya_habia_y_no_duplica(self, cliente, cuenta):
        primera = _pedir_recepcion(cliente, cuenta["cabeceras"])
        assert primera.status_code == 201
        segunda = _pedir_recepcion(cliente, cuenta["cabeceras"])
        # 200 y no 201: no se ha creado nada nuevo.
        assert segunda.status_code == 200, segunda.text
        cuerpo = segunda.json()
        assert cuerpo["ya_estaba"] is True
        assert cuerpo["como_se_reconocio"] == "numero_de_albaran"
        assert cuerpo["recepcion"]["id"] == primera.json()["recepcion"]["id"]
        assert any("ya lo tenías apuntado" in aviso for aviso in cuerpo["avisos"])
        # Y las existencias son las de una sola vez.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 5.0

    def test_solo_hay_una_entrada_en_el_libro(self, cliente, cuenta):
        _pedir_recepcion(cliente, cuenta["cabeceras"])
        _pedir_recepcion(cliente, cuenta["cabeceras"])
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        assert len(libro) == 1
        assert libro[0]["tipo"] == "entrada"
        assert libro[0]["cantidad"] == 5.0

    def test_solo_hay_un_albaran_en_la_lista(self, cliente, cuenta):
        _pedir_recepcion(cliente, cuenta["cabeceras"])
        _pedir_recepcion(cliente, cuenta["cabeceras"])
        listado = cliente.get("/api/almacen/recepciones", headers=cuenta["cabeceras"]).json()
        assert len(listado) == 1

    def test_el_proveedor_se_reconoce_aunque_se_escriba_distinto(self, cliente, cuenta):
        """«COOPERATIVA AGRICOLA» y «Cooperativa  Agrícola  » son el mismo proveedor: si se compararan
        tal cual, el mismo albarán entraría dos veces en el almacén."""
        _pedir_recepcion(cliente, cuenta["cabeceras"])
        segunda = _pedir_recepcion(
            cliente,
            cuenta["cabeceras"],
            proveedor="Cooperativa  Agrícola de Peñaranda s.c.l.",
            proveedor_nif=None,
        )
        assert segunda.status_code == 200
        assert segunda.json()["ya_estaba"] is True

    def test_el_mismo_numero_en_otro_ano_es_otro_albaran(self, cliente, cuenta):
        """Las numeraciones se reinician cada año: el «A-2026-118» de 2026 y el de 2027 son dos
        papeles distintos."""
        _pedir_recepcion(cliente, cuenta["cabeceras"], fecha="2026-03-15")
        segunda = _pedir_recepcion(cliente, cuenta["cabeceras"], fecha="2027-03-15")
        assert segunda.status_code == 201
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 10.0

    def test_otro_numero_de_albaran_es_otra_entrega(self, cliente, cuenta):
        _pedir_recepcion(cliente, cuenta["cabeceras"], numero_albaran="A-1")
        segunda = _pedir_recepcion(cliente, cuenta["cabeceras"], numero_albaran="A-2")
        assert segunda.status_code == 201
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 10.0

    def test_sin_numero_de_albaran_se_apunta_y_se_dice_que_no_se_pudo_comprobar(
        self, cliente, cuenta
    ):
        """No saber no es un «sí» ni un «no»: se apunta la mercancía —llegó— y se declara que la
        comprobación del duplicado no se ha podido hacer."""
        primera = _pedir_recepcion(cliente, cuenta["cabeceras"], numero_albaran=None)
        assert primera.status_code == 201
        assert any(
            "no se ha podido comprobar" in aviso for aviso in primera.json()["avisos"]
        )
        assert primera.json()["ya_estaba"] is False

    def test_un_albaran_anulado_no_impide_volver_a_apuntarlo_bien(self, cliente, cuenta):
        """Es la única forma de arreglar uno mal apuntado, así que tiene que funcionar."""
        primera = _recepcion(cliente, cuenta["cabeceras"], lineas=[{"nombre": "X", "unidad": "L", "cantidad": 1.0}])
        anulada = cliente.post(
            f"/api/almacen/recepciones/{primera['recepcion']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué de cantidad"},
        )
        assert anulada.status_code == 200
        assert anulada.json()["anulada"] is True
        # Y no cuenta: el almacén se queda vacío, que es lo que ha dicho el agricultor.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "X")["saldo"] == 0.0

        segunda = _pedir_recepcion(
            cliente, cuenta["cabeceras"], lineas=[{"nombre": "X", "unidad": "L", "cantidad": 5.0}]
        )
        assert segunda.status_code == 201
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "X")["saldo"] == 5.0

    def test_un_albaran_anulado_no_se_anula_dos_veces(self, cliente, cuenta):
        """El primer motivo es el que vale: pisarlo sería perder lo que dijo quien lo anuló."""
        primera = _recepcion(cliente, cuenta["cabeceras"])
        cliente.post(
            f"/api/almacen/recepciones/{primera['recepcion']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "el primero"},
        )
        segunda = cliente.post(
            f"/api/almacen/recepciones/{primera['recepcion']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "el segundo"},
        )
        assert segunda.status_code == 409
        assert "ya estaba anulado" in segunda.json()["detail"]

    def test_la_anulacion_queda_en_la_auditoria(self, cliente, cuenta, db_sesion):
        from app import models

        primera = _recepcion(cliente, cuenta["cabeceras"])
        cliente.post(
            f"/api/almacen/recepciones/{primera['recepcion']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "estaba repetido"},
        )
        acciones = [
            fila.accion
            for fila in db_sesion.query(models.Auditoria).all()
            if fila.entidad == "recepcion"
        ]
        assert acciones == ["crear", "anular"]


class TestElReenvioDesdeLaColaSinCobertura:
    """El móvil apunta en el campo sin cobertura y manda lo pendiente al volver la red.

    **Qué se prueba aquí exactamente.** `web/app.js` (`mandarPendientes`) reenvía `apunte.datos` una
    y otra vez, con la misma ruta y el mismo cuerpo, hasta que el servidor contesta bien; y
    `web/nucleo.js` guarda cada apunte con su `id_local`. Aquí se manda **dos veces el mismo cuerpo**,
    tal cual lo haría la cola, y se comprueba que la segunda no crea otro albarán ni otros litros. Las
    dos defensas se prueban por separado: la del número del albarán (que funciona sin que la pantalla
    mande nada más) y la de la clave de reenvío.
    """

    def test_el_mismo_cuerpo_dos_veces_no_crea_dos_albaranes(self, cliente, cuenta):
        cuerpo = {
            "fecha": "2026-03-15",
            "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
            "numero_albaran": "A-2026-118",
            "lineas": [{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0}],
        }
        primera = cliente.post("/api/almacen/recepciones", headers=cuenta["cabeceras"], json=cuerpo)
        segunda = cliente.post("/api/almacen/recepciones", headers=cuenta["cabeceras"], json=cuerpo)
        assert primera.status_code == 201
        assert segunda.status_code == 200
        assert segunda.json()["recepcion"]["id"] == primera.json()["recepcion"]["id"]
        assert len(cliente.get("/api/almacen/recepciones", headers=cuenta["cabeceras"]).json()) == 1

    def test_la_clave_de_reenvio_del_movil_tambien_protege(self, cliente, cuenta):
        """`id_local`: el nombre que le da la cola del móvil. Se acepta con los dos nombres."""
        cuerpo = {
            "fecha": "2026-03-15",
            "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
            "numero_albaran": "A-2026-118",
            "id_local": "p1-2026-03-15T09:00:00.000Z",
            "lineas": [{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0}],
        }
        primera = cliente.post("/api/almacen/recepciones", headers=cuenta["cabeceras"], json=cuerpo)
        # El segundo envío llega **sin número de albarán** y con la misma clave: si la clave no
        # protegiera, entrarían 5 litros más.
        segunda = cliente.post(
            "/api/almacen/recepciones",
            headers=cuenta["cabeceras"],
            json={**cuerpo, "numero_albaran": None},
        )
        assert primera.status_code == 201
        assert segunda.status_code == 200
        assert segunda.json()["como_se_reconocio"] == "clave_de_reenvio"
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 5.0

    def test_la_clave_de_reenvio_de_un_movimiento_a_mano(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "A"}],
        )
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL"), "A"
        )
        cuerpo = {
            "tipo": "merma",
            "lote_id": lote["lote_id"],
            "cantidad": 1.0,
            "unidad": "L",
            "motivo": "se rompió el envase",
            "clave_de_reenvio": "p7-2026-03-16T08:00:00.000Z",
        }
        primera = cliente.post("/api/almacen/movimientos", headers=cuenta["cabeceras"], json=cuerpo)
        segunda = cliente.post("/api/almacen/movimientos", headers=cuenta["cabeceras"], json=cuerpo)
        assert primera.status_code == 201
        assert segunda.status_code == 200
        assert segunda.json()["ya_estaba"] is True
        assert segunda.json()["movimiento"]["id"] == primera.json()["movimiento"]["id"]
        # Y la merma cuenta una sola vez.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 4.0


# --------------------------------------------------------------------------
# A01: el caso de aceptación completo
# --------------------------------------------------------------------------


class TestElCasoA01PorEntero:
    """**A01 del contrato**: compra de 5 L, aplicación de 2 L y de 3 L → saldo 0; el reenvío no
    duplica; anular los 2 L devuelve 2 L.

    Se hace de punta a punta y con las puertas de verdad: el albarán por la suya, los tratamientos
    por `POST /api/tratamientos` (que no se ha tocado) y el consumo por la puerta de las salidas.
    """

    @pytest.fixture
    def el_escenario(self, cliente, cuenta, campana, parcela_grande):
        """5 L en el almacén, en un lote, y dos tierras donde gastarlos."""
        producto = _producto(cliente, cuenta["cabeceras"])
        otra_tierra = crear_otra_parcela(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A"
        )
        return {
            "producto": producto,
            "lote": lote,
            "parcela": parcela_grande,
            "otra": otra_tierra,
            "campana": campana,
            "cabeceras": cuenta["cabeceras"],
        }

    def test_5_litros_en_el_almacen(self, cliente, el_escenario):
        datos = _existencias(cliente, el_escenario["cabeceras"])
        assert _el_articulo(datos, "Ejemplo 25 EC")["saldo"] == 5.0

    def test_2_litros_en_una_tierra_y_3_en_otra_dejan_el_saldo_a_cero(self, cliente, el_escenario):
        dos = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            el_escenario["producto"]["id"],
            1.0,
            2.0,
        )
        tres = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["otra"],
            el_escenario["producto"]["id"],
            1.0,
            3.0,
        )
        assert (dos["cantidad_total"], tres["cantidad_total"]) == (2.0, 3.0)
        for apunte in (dos, tres):
            respuesta = _una_salida(
                cliente,
                el_escenario["cabeceras"],
                apunte_id=apunte["id"],
                lote_id=el_escenario["lote"]["lote_id"],
            )
            assert respuesta.status_code == 201, respuesta.text
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Ejemplo 25 EC")
        assert articulo["entradas"] == 5.0
        assert articulo["salidas"] == 5.0
        assert articulo["saldo"] == 0.0

    def test_reenviar_la_salida_no_descuenta_dos_veces(self, cliente, el_escenario):
        apunte = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            el_escenario["producto"]["id"],
            1.0,
            2.0,
        )
        primera = _una_salida(
            cliente,
            el_escenario["cabeceras"],
            apunte_id=apunte["id"],
            lote_id=el_escenario["lote"]["lote_id"],
        )
        segunda = _una_salida(
            cliente,
            el_escenario["cabeceras"],
            apunte_id=apunte["id"],
            lote_id=el_escenario["lote"]["lote_id"],
        )
        assert primera.status_code == 201
        assert segunda.status_code == 200
        assert segunda.json()["ya_estaba"] is True
        assert segunda.json()["movimiento"]["id"] == primera.json()["movimiento"]["id"]
        assert _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 3.0

    def test_anular_los_2_litros_devuelve_los_2_litros(self, cliente, el_escenario):
        """Y **sin tocar el libro**: el movimiento sigue ahí, con su fecha y su autor, y lo que
        cambia es que deja de contar. Es la regla de que una anulación revierte el efecto sin
        borrar la historia."""
        dos = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            el_escenario["producto"]["id"],
            1.0,
            2.0,
        )
        tres = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["otra"],
            el_escenario["producto"]["id"],
            1.0,
            3.0,
        )
        for apunte in (dos, tres):
            _una_salida(
                cliente,
                el_escenario["cabeceras"],
                apunte_id=apunte["id"],
                lote_id=el_escenario["lote"]["lote_id"],
            )
        assert _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 0.0

        anulado = cliente.post(
            f"/api/tratamientos/{dos['id']}/anular",
            headers=el_escenario["cabeceras"],
            json={"motivo": "no se llegó a tratar esa tierra"},
        )
        assert anulado.status_code == 200, anulado.text

        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Ejemplo 25 EC")
        assert articulo["saldo"] == 2.0
        # El movimiento sigue en el libro, y dice por qué no cuenta.
        libro = cliente.get("/api/almacen/movimientos", headers=el_escenario["cabeceras"]).json()
        salidas = [fila for fila in libro if fila["tipo"] == "salida"]
        assert len(salidas) == 2
        la_anulada = [fila for fila in salidas if fila["origen_id"] == dos["id"]][0]
        assert la_anulada["anulado"] is False  # el movimiento no se ha tocado
        assert la_anulada["cuenta"] is False
        assert "anulado" in la_anulada["no_cuenta_porque"]

    def test_el_abono_tambien_gasta_de_su_lote(self, cliente, cuenta, campana, parcela_grande):
        """Un abono descuenta del lote que se indique, igual que un tratamiento."""
        abono = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Nitrato amónico", "tipo": "mineral", "riqueza_n": 33.5},
        ).json()
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "fertilizante_id": abono["id"],
                    "cantidad": 1000.0,
                    "unidad_de_la_cantidad": "kg",
                    "numero_lote": "SACO-1",
                }
            ],
        )
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Nitrato amónico"), "SACO-1"
        )
        registro = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": parcela_grande["id"],
                "superficie_ha": 10.0,
                "fertilizante_id": abono["id"],
                "kg_ha_producto": 50.0,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert registro.status_code == 201, registro.text
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="fertilizacion",
            apunte_id=registro.json()["id"],
            lote_id=lote["lote_id"],
        )
        assert respuesta.status_code == 201, respuesta.text
        # 50 kg/ha × 10 ha = 500 kg, y la unidad la dice el apunte.
        assert respuesta.json()["cantidad_total_gastada"] == 500.0
        assert respuesta.json()["unidad_de_la_cantidad"] == "kg"
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Nitrato amónico")
        assert articulo["saldo"] == 500.0


def crear_otra_parcela(cliente, cabeceras) -> dict:
    """Una segunda tierra, para el caso de A01 (2 L en una y 3 L en otra)."""
    respuesta = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={
            "alias": "El Alto",
            "ref_sigpac": "37-455-12-4",
            "superficie_ha": 3.0,
            "superficie_oficial": True,
            "sistema": "secano",
            "municipio": "Peñaranda de Bracamonte",
            "provincia": "Salamanca",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------
# A15: la factura llega después del albarán
# --------------------------------------------------------------------------


class TestA15LaFacturaLlegaDespues:
    """**A15 del contrato**: «factura llega después de albarán recibido → una entrada de almacén y
    vínculo entre ambos documentos».

    Es el sitio donde un programa de almacén se suele equivocar: contar la compra por la factura *y*
    por el albarán. Aquí la factura no mete ni un litro, y lo que se comprueba es exactamente eso.
    """

    def _con_albaran_recibido(self, cliente, cuenta):
        producto = _producto(cliente, cuenta["cabeceras"])
        recibido = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        return producto, recibido

    def test_la_factura_se_engancha_al_albaran_sin_meter_nada_mas(self, cliente, cuenta):
        producto, recibido = self._con_albaran_recibido(cliente, cuenta)
        factura = _una_factura(
            cliente,
            cuenta,
            numero_factura="2026/00123",
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 5 L",
                    "cantidad": 5.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        enganchada = cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        assert enganchada.status_code == 200, enganchada.text
        assert enganchada.json()["factura_id"] == factura["id"]
        # **Y el almacén sigue con 5 litros**, no con 10: la mercancía entró una vez.
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")
        assert articulo["saldo"] == 5.0
        assert articulo["entradas"] == 5.0
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        assert len([fila for fila in libro if fila["tipo"] == "entrada"]) == 1

    def test_la_misma_compra_no_se_cuenta_dos_veces_ni_en_la_cesta_ni_en_el_libro(
        self, cliente, cuenta
    ):
        """**La protección del encargo, medida en los dos sitios a la vez.** La cesta cuenta lo
        comprado por la factura; el libro, lo que entró por el albarán. Son dos vistas distintas y no
        se suman: si se sumaran, cada litro contaría dos veces."""
        producto, recibido = self._con_albaran_recibido(cliente, cuenta)
        factura = _una_factura(
            cliente,
            cuenta,
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 5 L",
                    "cantidad": 5.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        antes = _fila_de_la_cesta(_la_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        # La cesta dice 5 (de la factura) y el libro dice 5 (del albarán), no 10.
        assert antes["comprado"] == 5.0

        cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        despues = _fila_de_la_cesta(_la_cesta(cliente, cuenta["cabeceras"]), producto["id"])
        assert despues == antes
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 5.0

    def test_una_factura_no_puede_estar_en_dos_albaranes(self, cliente, cuenta):
        """Si lo estuviera, la compra estaría sosteniendo dos entradas y el cuadre no se podría
        explicar."""
        producto, primero = self._con_albaran_recibido(cliente, cuenta)
        segundo = _recepcion(
            cliente, cuenta["cabeceras"], numero_albaran="A-2", lineas=[{"nombre": "Otra cosa", "unidad": "L", "cantidad": 1.0}]
        )
        factura = _una_factura(cliente, cuenta)
        cliente.post(
            f"/api/almacen/recepciones/{primero['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        repetida = cliente.post(
            f"/api/almacen/recepciones/{segundo['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        assert repetida.status_code == 409
        assert "ya está enganchada a otro albarán" in repetida.json()["detail"]

    def test_se_pueden_casar_las_lineas_una_a_una(self, cliente, cuenta):
        """El contrato lo prevé: «factura y recepción pueden relacionarse parcialmente por líneas»."""
        producto, recibido = self._con_albaran_recibido(cliente, cuenta)
        factura = _una_factura(
            cliente,
            cuenta,
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 5 L",
                    "cantidad": 5.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        enganchada = cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={
                "factura_id": factura["id"],
                "lineas": [
                    {
                        "linea_de_recepcion_id": recibido["recepcion"]["lineas"][0]["id"],
                        "linea_de_factura_id": factura["lineas"][0]["id"],
                    }
                ],
            },
        )
        assert enganchada.status_code == 200, enganchada.text
        assert enganchada.json()["lineas"][0]["linea_factura_id"] == factura["lineas"][0]["id"]
        # Y sigue sin moverse ni un litro.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 5.0

    def test_una_linea_que_no_es_de_esa_factura_se_rechaza(self, cliente, cuenta):
        producto, recibido = self._con_albaran_recibido(cliente, cuenta)
        factura = _una_factura(cliente, cuenta)
        otra_factura = _una_factura(cliente, cuenta, numero_factura="2026/00124")
        respuesta = cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={
                "factura_id": factura["id"],
                "lineas": [
                    {
                        "linea_de_recepcion_id": recibido["recepcion"]["lineas"][0]["id"],
                        "linea_de_factura_id": otra_factura["lineas"][0]["id"],
                    }
                ],
            },
        )
        assert respuesta.status_code == 404

    def test_se_propone_que_albaran_es_de_esa_factura_sin_enganchar_nada(self, cliente, cuenta):
        """Una máquina propone, una persona confirma: es la misma regla que en el dictado y en la
        lectura de facturas."""
        producto, recibido = self._con_albaran_recibido(cliente, cuenta)
        factura = _una_factura(
            cliente,
            cuenta,
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 5 L",
                    "cantidad": 5.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        propuesta = cliente.get(
            f"/api/almacen/facturas/{factura['id']}/posibles-recepciones",
            headers=cuenta["cabeceras"],
        )
        assert propuesta.status_code == 200
        cuerpo = propuesta.json()
        assert [fila["recepcion_id"] for fila in cuerpo["propuestas"]] == [
            recibido["recepcion"]["id"]
        ]
        assert cuerpo["propuestas"][0]["lineas_casadas"][0]["como"] == "es el mismo producto"
        # Y no ha enganchado nada: la factura sigue suelta hasta que alguien lo diga.
        ficha = cliente.get(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}",
            headers=cuenta["cabeceras"],
        ).json()
        assert ficha["factura_id"] is None

    def test_el_enganche_queda_en_la_auditoria(self, cliente, cuenta, db_sesion):
        from app import models

        producto, recibido = self._con_albaran_recibido(cliente, cuenta)
        factura = _una_factura(cliente, cuenta)
        cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        acciones = [
            fila.accion
            for fila in db_sesion.query(models.Auditoria).all()
            if fila.entidad == "recepcion"
        ]
        assert acciones == ["crear", "enlazar_la_factura"]

    def test_una_factura_anulada_no_quita_la_mercancia_que_llego(self, cliente, cuenta):
        """La mercancía está en la nave. Anular la factura dice que ese papel no vale, no que el
        producto se haya ido: la factura no era lo que metía la mercancía."""
        producto, recibido = self._con_albaran_recibido(cliente, cuenta)
        factura = _una_factura(cliente, cuenta)
        cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/factura",
            headers=cuenta["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        anulada = cliente.post(
            f"/api/facturas/{factura['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "era de otro proveedor"},
        )
        assert anulada.status_code == 200, anulada.text
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 5.0


# --------------------------------------------------------------------------
# La protección del encargo, dicha en voz alta
# --------------------------------------------------------------------------


class TestElLibroNoSeSumaALaCesta:
    """**Lo que NO puede pasar**, medido: que las existencias se cuenten dos veces, una por lo
    comprado y otra por el movimiento de entrada.

    La decisión está escrita en `servicios.py`: la cesta (`/api/productos/cesta/situacion`) sigue
    calculando lo comprado con las facturas y lo gastado con los tratamientos, **sin haberla tocado**,
    y el libro cuenta solo sus movimientos. Son dos vistas distintas de lo mismo y **no se suman
    nunca**. Estas pruebas son las que impiden que alguien las sume un día «para que cuadre»."""

    def test_recibir_un_albaran_no_cambia_ni_un_numero_de_la_cesta(self, cliente, cuenta):
        """La cesta de la pantalla del almacén tiene que seguir diciendo lo mismo que decía antes de
        que existiera el libro. Es la promesa que el encargo pide por escrito."""
        producto = _producto(
            cliente, cuenta["cabeceras"], cantidad_comprada=20.0, unidad_compra="L"
        )
        antes = _la_cesta(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        despues = _la_cesta(cliente, cuenta["cabeceras"])
        assert despues == antes
        # Y el número de la ficha del producto sigue siendo 20, no 25.
        assert _fila_de_la_cesta(despues, producto["id"])["comprado"] == 20.0
        # Mientras el libro dice 5: lo que entró por el albarán, que es otra pregunta.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 5.0

    def test_el_saldo_del_libro_sale_solo_de_los_movimientos(self, cliente, cuenta):
        """Con una factura de 101 L y ningún albarán, el libro dice **cero**, no 101: las facturas no
        meten mercancía, la mete el albarán."""
        producto = _producto(cliente, cuenta["cabeceras"], unidad_compra="L")
        _una_factura(
            cliente,
            cuenta,
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 101 L",
                    "cantidad": 101.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        # La cesta sí lo cuenta (es lo comprado según el papel).
        assert _fila_de_la_cesta(_la_cesta(cliente, cuenta["cabeceras"]), producto["id"])["comprado"] == 101.0
        # Y en el almacén no hay nada, porque no ha llegado nada. Y se dice por qué, para que un
        # almacén vacío no parezca unas existencias perdidas.
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert datos["articulos"] == []
        assert [fila["nombre"] for fila in datos["comprado_sin_entrar"]] == ["Ejemplo 25 EC"]
        assert datos["comprado_sin_entrar"][0]["lineas"] == 1

    def test_lo_que_ya_ha_entrado_no_sale_en_la_lista_de_lo_que_falta_por_llegar(
        self, cliente, cuenta
    ):
        producto = _producto(cliente, cuenta["cabeceras"], unidad_compra="L")
        _una_factura(
            cliente,
            cuenta,
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 5 L",
                    "cantidad": 5.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert datos["comprado_sin_entrar"] == []
        assert _el_articulo(datos, "Ejemplo 25 EC")["saldo"] == 5.0

    def test_una_compra_sin_albaran_se_puede_apuntar_a_mano_diciendo_que_es_de_una_factura(
        self, cliente, cuenta
    ):
        """El camino para la compra que se pagó al contado y no trajo albarán: se apunta la entrada y
        se dice de qué factura viene."""
        producto = _producto(cliente, cuenta["cabeceras"], unidad_compra="L")
        factura = _una_factura(
            cliente,
            cuenta,
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 20 L",
                    "cantidad": 20.0,
                    "unidad": "L",
                    "producto_id": producto["id"],
                }
            ],
        )
        articulo = cliente.post(
            "/api/almacen/articulos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Glifosato 36 SL", "categoria": "fitosanitario", "unidad": "L", "producto_id": producto["id"]},
        )
        assert articulo.status_code == 201, articulo.text
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "entrada",
                "articulo_id": articulo.json()["id"],
                "numero_lote": "SIN-ALBARAN",
                "cantidad": 20.0,
                "unidad": "L",
                "origen_tipo": "factura",
                "origen_id": factura["id"],
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        movimiento = respuesta.json()["movimiento"]
        assert movimiento["origen_tipo"] == "factura"
        assert movimiento["origen_id"] == factura["id"]
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert _el_articulo(datos, "Glifosato 36 SL")["saldo"] == 20.0
        # Y ya no falta nada por entrar de esa compra.
        assert datos["comprado_sin_entrar"] == []

    def test_un_movimiento_que_sale_de_un_albaran_o_de_un_apunte_no_se_apunta_a_mano(
        self, cliente, cuenta
    ):
        """Tienen su puerta, y ahí es donde el programa pone la referencia: apuntarlo a mano sería
        perder de dónde viene."""
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "entrada",
                "articulo_id": 1,
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "x",
                "origen_tipo": "recepcion",
                "origen_id": 1,
            },
        )
        assert respuesta.status_code == 400
        assert "se apunta desde ahí, no a mano" in respuesta.json()["detail"]


# --------------------------------------------------------------------------
# Las salidas: gastar de un lote sin dejar la cuenta mintiendo
# --------------------------------------------------------------------------


class TestGastarDeUnLote:
    def _con_lote(self, cliente, cuenta, cantidad=5.0, **cambios):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "unidad": "L",
                    "cantidad": cantidad,
                    "numero_lote": cambios.pop("numero_lote", "4471-A"),
                }
            ],
            **cambios,
        )
        return _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL"), "4471-A"
        )

    def test_la_cantidad_sale_del_apunte_y_no_hay_que_teclearla(
        self, cliente, cuenta, campana, parcela_grande
    ):
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 2.0
        )
        respuesta = _una_salida(
            cliente, cuenta["cabeceras"], apunte_id=apunte["id"], lote_id=lote["lote_id"]
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["movimiento"]["cantidad"] == 1.0
        assert respuesta.json()["movimiento"]["unidad"] == "L"

    def test_la_salida_coge_la_fecha_del_trabajo(self, cliente, cuenta, campana, parcela_grande):
        """La del día en que se echó el producto, no la del día en que se teclea: apuntar un
        tratamiento de la semana pasada no lo convierte en cosa de hoy."""
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A"
        )
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 2.0
        )
        respuesta = _una_salida(
            cliente, cuenta["cabeceras"], apunte_id=apunte["id"], lote_id=lote["lote_id"]
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["movimiento"]["fecha"] == apunte["fecha"] == "2026-05-05"

    def test_no_se_puede_sacar_de_un_apunte_que_no_gasta(self, cliente, cuenta, campana, parcela_grande):
        """Una labor no gasta producto del almacén, así que no puede restar nada."""
        lote = self._con_lote(cliente, cuenta)
        labor = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "laboreo",
                "fecha": "2026-04-01",
                "parcela_id": parcela_grande["id"],
                "superficie_ha": 2.0,
            },
        )
        assert labor.status_code == 201, labor.text
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="labor",
            apunte_id=labor.json()["id"],
            lote_id=lote["lote_id"],
        )
        assert respuesta.status_code == 400
        assert "no saca producto" in respuesta.json()["detail"]

    def test_de_un_apunte_anulado_no_se_saca_nada(self, cliente, cuenta, campana, parcela_grande):
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 2.0
        )
        cliente.post(
            f"/api/tratamientos/{apunte['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no se llegó a hacer"},
        )
        respuesta = _una_salida(
            cliente, cuenta["cabeceras"], apunte_id=apunte["id"], lote_id=lote["lote_id"]
        )
        assert respuesta.status_code == 409
        assert "está anulado" in respuesta.json()["detail"]

    def test_sacar_mas_de_lo_que_hay_avisa_antes_de_apuntarlo(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """El contrato lo pide: «avisa y pide corregir, registrar entrada o aceptar una discrepancia
        justificada... nunca altera a escondidas una compra ni impide registrar lo que de verdad
        ocurrió»."""
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 3.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.0, 4.0
        )
        aviso = _una_salida(
            cliente, cuenta["cabeceras"], apunte_id=apunte["id"], lote_id=lote["lote_id"]
        )
        assert aviso.status_code == 409
        detalle = aviso.json()["detail"]
        assert "quedan 3" in detalle and "vas a sacar 4" in detalle
        # Y da las tres salidas: corregir, apuntar la entrada que falta o decir que es de verdad.
        assert "corregir la cantidad" in detalle
        assert "apuntar la entrada" in detalle
        # No se ha apuntado nada.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 3.0

    def test_con_aceptar_el_descuadre_se_apunta_y_queda_marcado(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """Lo que de verdad pasó se registra siempre. Lo que no se hace es apuntarlo a escondidas:
        el saldo queda en negativo y a la vista."""
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 3.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 1.0, 4.0
        )
        respuesta = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
            aceptar_descuadre=True,
        )
        assert respuesta.status_code == 201, respuesta.text
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")
        assert articulo["saldo"] == -1.0
        assert articulo["motivo_codigo"] == "AL33_saldo_negativo"
        assert "Sale más de lo que entró" in articulo["motivo"]

    def test_si_no_se_sabe_lo_que_queda_no_se_bloquea_nada(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """No se puede afirmar que se pase de lo que hay, así que no se dice. Lo que no se puede
        hacer es inventarse un saldo para decidir."""
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                    "descripcion": "sin la cantidad legible",
                }
            ],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 2.0
        )
        respuesta = _una_salida(
            cliente, cuenta["cabeceras"], apunte_id=apunte["id"], lote_id=lote["lote_id"]
        )
        assert respuesta.status_code == 201, respuesta.text

    def test_una_salida_por_apunte_y_lote_aunque_cambie_la_cantidad(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """No se cambia por detrás: se devuelve la que había con un aviso, y el agricultor decide."""
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 2.0
        )
        _una_salida(cliente, cuenta["cabeceras"], apunte_id=apunte["id"], lote_id=lote["lote_id"])
        otra = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
            cantidad=3.0,
            unidad="L",
        )
        assert otra.status_code == 200
        assert otra.json()["ya_estaba"] is True
        assert any("ya habías apuntado que se sacaron" in aviso for aviso in otra.json()["avisos"])
        # Y la cantidad del libro es la de antes: no se ha cambiado por detrás.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")[
            "salidas"
        ] == 1.0

    def test_la_salida_tambien_se_protege_por_su_clave_de_reenvio(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """La cola del móvil reintenta **el mismo cuerpo**, pero el agricultor pudo corregir la
        pantalla entre un intento y otro: con la misma clave de reenvío, la respuesta es el mismo
        movimiento y no dos consumos del mismo trabajo."""
        producto = _producto(cliente, cuenta["cabeceras"])
        for lote, cantidad in (("L-1", 5.0), ("L-2", 3.0)):
            _recepcion(
                cliente,
                cuenta["cabeceras"],
                numero_albaran=f"A-{lote}",
                lineas=[
                    {
                        "producto_id": producto["id"],
                        "cantidad": cantidad,
                        "unidad_de_la_cantidad": "L",
                        "numero_lote": lote,
                    }
                ],
            )
        datos = _existencias(cliente, cuenta["cabeceras"])
        articulo = _el_articulo(datos, "Ejemplo 25 EC")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 2.0
        )
        primera = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_id=apunte["id"],
            lote_id=_el_lote(articulo, "L-1")["lote_id"],
            clave_de_reenvio="p9-2026-05-05T07:00:00.000Z",
        )
        assert primera.status_code == 201, primera.text
        segunda = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_id=apunte["id"],
            lote_id=_el_lote(articulo, "L-2")["lote_id"],
            clave_de_reenvio="p9-2026-05-05T07:00:00.000Z",
        )
        assert segunda.status_code == 200, segunda.text
        assert segunda.json()["ya_estaba"] is True
        assert segunda.json()["movimiento"]["id"] == primera.json()["movimiento"]["id"]
        # Y del segundo lote no se ha sacado nada: el reenvío no ha gastado donde no era.
        assert _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "L-2"
        )["saldo"] == 3.0

    def test_el_lote_de_otra_finca_no_se_puede_usar(self, cliente, cuenta, crear_cuenta):
        cuenta_b = crear_cuenta("otro@ejemplo.test", "Otro", "12345678Z")
        lote = self._con_lote(cliente, cuenta)
        respuesta = cliente.post(
            "/api/almacen/salidas",
            headers=cuenta_b["cabeceras"],
            json={"apunte_tipo": "tratamiento", "apunte_id": 1, "lote_id": lote["lote_id"]},
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_una_salida_anulada_se_puede_volver_a_apuntar_bien(
        self, cliente, cuenta, campana, parcela_grande
    ):
        """**Anular y volver a apuntar tiene que funcionar**, que es para lo que sirve anular.

        La salida anulada sigue en el libro —nada se borra— pero ya no dice nada de este apunte, así
        que el consumo bueno se puede apuntar: el saldo vuelve a cuadrar y quedan los dos
        movimientos, el tachado y el bueno.
        """
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        lote = _el_lote(_el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC"), "4471-A")
        apunte = _un_tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela_grande, producto["id"], 0.5, 4.0
        )
        primera = _una_salida(
            cliente, cuenta["cabeceras"], apunte_id=apunte["id"], lote_id=lote["lote_id"]
        )
        assert primera.status_code == 201
        cliente.post(
            f"/api/almacen/movimientos/{primera.json()['movimiento']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "en realidad saqué dos litros, no dos"},
        )
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 5.0

        segunda = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_id=apunte["id"],
            lote_id=lote["lote_id"],
            cantidad=2.0,
            unidad="L",
        )
        assert segunda.status_code == 201, segunda.text
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Ejemplo 25 EC")["saldo"] == 3.0
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        assert len([fila for fila in libro if fila["tipo"] == "salida"]) == 2
        assert len([fila for fila in libro if fila["tipo"] == "salida" and fila["cuenta"]]) == 1

    def test_lo_que_entro_con_un_albaran_no_se_anula_linea_a_linea(
        self, cliente, cuenta
    ):
        """Se anula el albarán, que es el papel: anular una sola línea dejaría el albarán diciendo
        que metió mercancía que el almacén ya no cuenta."""
        recibido = _recepcion(cliente, cuenta["cabeceras"])
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        respuesta = cliente.post(
            f"/api/almacen/movimientos/{libro[0]['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no vino ese bote"},
        )
        assert respuesta.status_code == 409
        assert "se deshace anulando el albarán" in respuesta.json()["detail"]
        # Y por su puerta sí: el albarán se anula y el almacén se queda a cero.
        anulada = cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no vino ese bote"},
        )
        assert anulada.status_code == 200
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 0.0

    def test_abrir_un_lote_que_ya_existe_devuelve_el_que_hay(self, cliente, cuenta):
        """El envase que ya estaba no se abre otra vez, y la respuesta no dice que ha creado nada."""
        articulo = cliente.post(
            "/api/almacen/articulos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Glifosato 36 SL", "categoria": "fitosanitario", "unidad": "L"},
        ).json()
        primera = cliente.post(
            "/api/almacen/lotes",
            headers=cuenta["cabeceras"],
            json={"articulo_id": articulo["id"], "numero_lote": "4471-A"},
        )
        assert primera.status_code == 201, primera.text
        segunda = cliente.post(
            "/api/almacen/lotes",
            headers=cuenta["cabeceras"],
            json={"articulo_id": articulo["id"], "numero_lote": "4471-a"},
        )
        assert segunda.status_code == 200, segunda.text
        assert segunda.json()["id"] == primera.json()["id"]
        assert len(cliente.get(
            "/api/almacen/lotes", headers=cuenta["cabeceras"], params={"articulo_id": articulo["id"]}
        ).json()) == 1


# --------------------------------------------------------------------------
# La merma y el ajuste
# --------------------------------------------------------------------------


class TestLaMermaYElAjuste:
    @pytest.fixture
    def con_lote(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "4471-A"}
            ],
        )
        return _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL"), "4471-A"
        )

    def test_una_merma_baja_el_saldo_y_pide_motivo(self, cliente, cuenta, con_lote):
        sin_motivo = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "merma",
                "lote_id": con_lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
            },
        )
        assert sin_motivo.status_code == 400
        assert "lo tiene que explicar quien lo apunta" in sin_motivo.json()["detail"]

        con_motivo = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "merma",
                "lote_id": con_lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "se rompió el envase en el remolque",
            },
        )
        assert con_motivo.status_code == 201, con_motivo.text
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        assert articulo["mermas"] == 1.0
        # Una merma **no** es un gasto: no cuenta como producto echado en la tierra.
        assert articulo["salidas"] == 0.0
        assert articulo["saldo"] == 4.0

    def test_un_ajuste_positivo_sube_el_saldo(self, cliente, cuenta, con_lote):
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "ajuste",
                "lote_id": con_lote["lote_id"],
                "cantidad": 2.0,
                "unidad": "L",
                "motivo": "contando el almacén había dos litros más",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 7.0

    def test_un_ajuste_negativo_baja_el_saldo(self, cliente, cuenta, con_lote):
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "ajuste",
                "lote_id": con_lote["lote_id"],
                "cantidad": -1.5,
                "unidad": "L",
                "motivo": "contando el almacén faltaba litro y medio",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 3.5

    def test_un_ajuste_de_cero_no_apunta_nada(self, cliente, cuenta, con_lote):
        """Si sale cero, es que cuadra: no hay nada que apuntar, y apuntarlo llenaría el libro de
        líneas que no dicen nada."""
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "ajuste",
                "lote_id": con_lote["lote_id"],
                "cantidad": 0.0,
                "unidad": "L",
                "motivo": "cuadra",
            },
        )
        assert respuesta.status_code == 400
        assert "es que cuadra" in respuesta.json()["detail"]

    def test_una_merma_sin_cantidad_no_se_apunta(self, cliente, cuenta, con_lote):
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={"tipo": "merma", "lote_id": con_lote["lote_id"], "motivo": "se rompió"},
        )
        assert respuesta.status_code == 400
        assert "cuánto" in respuesta.json()["detail"]

    def test_una_salida_a_mano_no_se_puede_apuntar(self, cliente, cuenta, con_lote):
        """Si se pudiera restar sin decir de dónde, el almacén dejaría de poder contestar la única
        pregunta que importa cuando hay un problema con un lote."""
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "salida",
                "lote_id": con_lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "porque sí",
            },
        )
        assert respuesta.status_code == 400
        assert "hay que decir de qué trabajo sale" in respuesta.json()["detail"]

    def test_un_tipo_que_no_existe_se_dice(self, cliente, cuenta, con_lote):
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={"tipo": "desaparecer", "lote_id": con_lote["lote_id"], "cantidad": 1.0, "unidad": "L"},
        )
        assert respuesta.status_code == 400
        assert "no es una cosa que pase en el almacén" in respuesta.json()["detail"]

    def test_una_cantidad_sin_unidad_no_se_apunta(self, cliente, cuenta, con_lote):
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={"tipo": "ajuste", "lote_id": con_lote["lote_id"], "cantidad": 1.0, "motivo": "x"},
        )
        assert respuesta.status_code == 400
        assert "en qué se mide" in respuesta.json()["detail"]

    def test_una_entrada_a_mano_sin_factura_pide_motivo(self, cliente, cuenta, con_lote):
        """Un movimiento sin ningún papel detrás solo lo explica quien lo apunta."""
        sin_motivo = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "entrada",
                "lote_id": con_lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
            },
        )
        assert sin_motivo.status_code == 400
        assert "no hay ningún papel" in sin_motivo.json()["detail"]

    def test_un_movimiento_anulado_deja_de_contar_y_sigue_en_el_libro(self, cliente, cuenta, con_lote):
        apuntado = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "merma",
                "lote_id": con_lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "me equivoqué",
            },
        ).json()["movimiento"]
        anulado = cliente.post(
            f"/api/almacen/movimientos/{apuntado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no se había roto nada"},
        )
        assert anulado.status_code == 200, anulado.text
        assert anulado.json()["anulado"] is True
        assert anulado.json()["cuenta"] is False
        # El saldo vuelve a 5 y la fila sigue en el libro, con su motivo de anulación.
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")["saldo"] == 5.0
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        la_anulada = [fila for fila in libro if fila["id"] == apuntado["id"]][0]
        assert la_anulada["motivo_anulacion"] == "no se había roto nada"

    def test_un_movimiento_anulado_no_se_anula_dos_veces(self, cliente, cuenta, con_lote):
        apuntado = cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "merma",
                "lote_id": con_lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "x",
            },
        ).json()["movimiento"]
        cliente.post(
            f"/api/almacen/movimientos/{apuntado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "primero"},
        )
        segunda = cliente.post(
            f"/api/almacen/movimientos/{apuntado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "segundo"},
        )
        assert segunda.status_code == 409

    def test_el_ajuste_queda_apuntado_en_la_auditoria(self, cliente, cuenta, con_lote, db_sesion):
        """Un ajuste mueve existencias sin ningún documento detrás: es justo el cambio que hay que
        poder revisar después, con quién lo hizo y por qué."""
        from app import models

        cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "ajuste",
                "lote_id": con_lote["lote_id"],
                "cantidad": -0.5,
                "unidad": "L",
                "motivo": "contando el almacén faltaba medio litro",
            },
        )
        rastro = [
            fila
            for fila in db_sesion.query(models.Auditoria).all()
            if fila.entidad == "movimiento_de_existencias"
        ]
        assert [fila.accion for fila in rastro] == ["crear"]
        assert rastro[0].datos["tipo"] == "ajuste"
        assert rastro[0].datos["motivo"] == "contando el almacén faltaba medio litro"
        assert rastro[0].usuario_id is not None


# --------------------------------------------------------------------------
# Consultar las existencias: por artículo y por lote
# --------------------------------------------------------------------------


class TestConsultarLasExistencias:
    def test_por_articulo_y_por_lote(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            numero_albaran="A-1",
            lineas=[
                {
                    "nombre": "Glifosato 36 SL",
                    "categoria": "fitosanitario",
                    "unidad": "L",
                    "cantidad": 5.0,
                    "numero_lote": "L-1",
                },
                {
                    "nombre": "Nitrato amónico",
                    "categoria": "abono",
                    "unidad": "kg",
                    "cantidad": 500.0,
                    "numero_lote": "S-1",
                },
            ],
        )
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert datos["cuantos"] == 2
        glifosato = _el_articulo(datos, "Glifosato 36 SL")
        assert glifosato["categoria"] == "fitosanitario"
        assert glifosato["unidad"] == "L"
        assert glifosato["cuantos_lotes"] == 1
        assert glifosato["lotes"][0]["numero_lote"] == "L-1"
        assert glifosato["lotes"][0]["saldo"] == 5.0
        assert _el_articulo(datos, "Nitrato amónico")["saldo"] == 500.0

    def test_una_linea_de_albaran_sin_decir_de_que_es_es_otra_cosa(self, cliente, cuenta):
        """Si el albarán no dice la clase de cosa (producto, abono, semilla…), se guarda en «otras
        cosas» en vez de inventarse una categoría. El agricultor la encuentra igual."""
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[{"nombre": "Aceite hidráulico", "unidad": "L", "cantidad": 20.0}],
        )
        assert _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Aceite hidráulico")[
            "categoria"
        ] == "otros"

    def test_se_puede_preguntar_por_un_articulo(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0},
                {"nombre": "Nitrato amónico", "categoria": "abono", "unidad": "kg", "cantidad": 500.0},
            ],
        )
        todos = _existencias(cliente, cuenta["cabeceras"])
        uno = _el_articulo(todos, "Glifosato 36 SL")
        solo_ese = _existencias(cliente, cuenta["cabeceras"], articulo_id=uno["articulo_id"])
        assert [fila["nombre"] for fila in solo_ese["articulos"]] == ["Glifosato 36 SL"]

    def test_los_textos_van_en_la_respuesta(self, cliente, cuenta):
        """Para que la pantalla no escriba ni una frase: las palabras viven en `textos.py`."""
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert datos["textos"]["titulo"] == "El libro del almacén"
        assert datos["textos"]["saldo_negativo"]

    def test_sin_nada_apuntado_lo_dice_sin_mentir(self, cliente, cuenta):
        datos = _existencias(cliente, cuenta["cabeceras"])
        assert datos["articulos"] == []
        assert "Todavía no hay nada apuntado" in datos["resumen"]

    def test_el_libro_se_puede_filtrar_por_tipo_y_por_lote(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "L-1"}
            ],
        )
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL"), "L-1"
        )
        cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "merma",
                "lote_id": lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "se rompió",
            },
        )
        entradas = cliente.get(
            "/api/almacen/movimientos", headers=cuenta["cabeceras"], params={"tipo": "entrada"}
        ).json()
        assert [fila["tipo"] for fila in entradas] == ["entrada"]
        del_lote = cliente.get(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            params={"lote_id": lote["lote_id"]},
        ).json()
        assert len(del_lote) == 2
        # Y cada movimiento dice de qué artículo y de qué lote es, sin que la pantalla cruce listas.
        assert del_lote[0]["articulo"] == "Glifosato 36 SL"
        assert del_lote[0]["numero_lote"] == "L-1"

    def test_el_libro_dice_cuales_cuentan_y_cuales_no(self, cliente, cuenta):
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "L-1"}
            ],
        )
        lote = _el_lote(
            _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL"), "L-1"
        )
        cliente.post(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            json={
                "tipo": "merma",
                "lote_id": lote["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "se rompió",
            },
        )
        solo = cliente.get(
            "/api/almacen/movimientos",
            headers=cuenta["cabeceras"],
            params={"solo_los_que_cuentan": True},
        ).json()
        assert len(solo) == 2
        assert all(fila["cuenta"] for fila in solo)

    def test_un_albaran_anulado_deja_sus_movimientos_sin_contar(self, cliente, cuenta):
        recibido = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[{"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0}],
        )
        cliente.post(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "el albarán era de otro año"},
        )
        libro = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        assert len(libro) == 1
        assert libro[0]["cuenta"] is False
        assert "anulado" in libro[0]["no_cuenta_porque"]
        # Y la recepción anulada dice que no ha metido nada.
        ficha = cliente.get(
            f"/api/almacen/recepciones/{recibido['recepcion']['id']}",
            headers=cuenta["cabeceras"],
        ).json()
        assert ficha["anulada"] is True
        assert ficha["entradas"] == 0


# --------------------------------------------------------------------------
# Aislamiento: nada de una finca se ve desde otra
# --------------------------------------------------------------------------


class TestCadaFincaVeLoSuyo:
    @pytest.fixture
    def dos_fincas(self, cliente, cuenta, crear_cuenta):
        otra = crear_cuenta("otro@ejemplo.test", "Otro Agricultor", "12345678Z")
        guardada = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {"nombre": "Glifosato 36 SL", "unidad": "L", "cantidad": 5.0, "numero_lote": "L-1"}
            ],
        )
        datos_a = _existencias(cliente, cuenta["cabeceras"])
        return {
            "a": cuenta,
            "b": otra,
            "recepcion": guardada["recepcion"],
            "articulo": _el_articulo(datos_a, "Glifosato 36 SL"),
            "lote": _el_lote(_el_articulo(datos_a, "Glifosato 36 SL"), "L-1"),
        }

    def test_los_albaranes_de_otra_finca_no_se_ven(self, cliente, dos_fincas):
        listado = cliente.get("/api/almacen/recepciones", headers=dos_fincas["b"]["cabeceras"]).json()
        assert listado == []

    def test_el_albaran_de_otra_finca_no_se_puede_ver(self, cliente, dos_fincas):
        respuesta = cliente.get(
            f"/api/almacen/recepciones/{dos_fincas['recepcion']['id']}",
            headers=dos_fincas["b"]["cabeceras"],
        )
        assert respuesta.status_code == 404

    def test_el_almacen_de_otra_finca_esta_vacio(self, cliente, dos_fincas):
        datos = _existencias(cliente, dos_fincas["b"]["cabeceras"])
        assert datos["articulos"] == []

    def test_el_libro_de_otra_finca_esta_vacio(self, cliente, dos_fincas):
        libro = cliente.get("/api/almacen/movimientos", headers=dos_fincas["b"]["cabeceras"]).json()
        assert libro == []

    def test_no_se_puede_preguntar_por_un_articulo_de_otra_finca(self, cliente, dos_fincas):
        respuesta = cliente.get(
            "/api/almacen/existencias",
            headers=dos_fincas["b"]["cabeceras"],
            params={"articulo_id": dos_fincas["articulo"]["articulo_id"]},
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_apuntar_un_movimiento_en_el_lote_de_otra_finca(self, cliente, dos_fincas):
        respuesta = cliente.post(
            "/api/almacen/movimientos",
            headers=dos_fincas["b"]["cabeceras"],
            json={
                "tipo": "merma",
                "lote_id": dos_fincas["lote"]["lote_id"],
                "cantidad": 1.0,
                "unidad": "L",
                "motivo": "x",
            },
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_abrir_un_lote_en_el_articulo_de_otra_finca(self, cliente, dos_fincas):
        respuesta = cliente.post(
            "/api/almacen/lotes",
            headers=dos_fincas["b"]["cabeceras"],
            json={"articulo_id": dos_fincas["articulo"]["articulo_id"], "numero_lote": "X"},
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_anular_el_albaran_de_otra_finca(self, cliente, dos_fincas):
        respuesta = cliente.post(
            f"/api/almacen/recepciones/{dos_fincas['recepcion']['id']}/anular",
            headers=dos_fincas["b"]["cabeceras"],
            json={"motivo": "porque yo lo digo"},
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_enganchar_una_factura_de_otra_finca(self, cliente, dos_fincas):
        factura = _una_factura(cliente, dos_fincas["b"])
        respuesta = cliente.post(
            f"/api/almacen/recepciones/{dos_fincas['recepcion']['id']}/factura",
            headers=dos_fincas["a"]["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        assert respuesta.status_code == 404

    def test_el_mismo_albaran_en_dos_fincas_no_es_el_mismo(self, cliente, dos_fincas):
        """Dos agricultores pueden tener un albarán con el mismo número de la misma cooperativa: son
        dos papeles de dos fincas, y el de una no puede estorbar al de la otra."""
        segunda = _pedir_recepcion(cliente, dos_fincas["b"]["cabeceras"])
        assert segunda.status_code == 201, segunda.text
        assert segunda.json()["recepcion"]["id"] != dos_fincas["recepcion"]["id"]

    def test_hace_falta_entrar(self, cliente):
        for ruta in (
            "/api/almacen/existencias",
            "/api/almacen/movimientos",
            "/api/almacen/recepciones",
            "/api/almacen/articulos",
        ):
            assert cliente.get(ruta).status_code == 401


# --------------------------------------------------------------------------
# Los textos: los que lee el agricultor viven en `textos.py` y sin jerga
# --------------------------------------------------------------------------


class TestLosTextosDeLaPantalla:
    def test_entran_en_la_revision_de_jerga(self):
        assert textos_del_almacen()["titulo"] in _todos_los_textos_visibles()

    def test_ninguno_lleva_jerga(self):
        from app import textos

        malos = {
            clave: textos.palabras_prohibidas_encontradas(valor)
            for clave, valor in textos.ALMACEN.items()
            if textos.palabras_prohibidas_encontradas(valor)
        }
        assert malos == {}, f"el vocabulario del almacén lleva jerga: {malos}"

    def test_los_mensajes_nuevos_tampoco(self):
        from app import textos

        malos = {
            codigo: textos.palabras_prohibidas_encontradas(mensaje)
            for codigo, mensaje in textos.MENSAJES.items()
            if codigo.startswith("AL") and textos.palabras_prohibidas_encontradas(mensaje)
        }
        assert malos == {}, f"mensajes del almacén con jerga: {malos}"

    def test_cada_clase_de_cosa_tiene_su_nombre_para_la_pantalla(self):
        """Las cuatro pestañas del contrato (§4), cada una con su palabra de agricultor."""
        from app import textos

        for categoria in servicios.CATEGORIAS_DE_ARTICULO:
            clave = f"categoria_{categoria}"
            assert textos.ALMACEN.get(clave), f"falta el nombre de la categoría {categoria}"

    def test_la_palabra_de_mostrador_no_se_le_ensena_al_agricultor(self):
        """«Fitosanitario» es la primera palabra de la lista de las prohibidas: en pantalla se dice
        «productos de tratamiento», que es lo que dice el contrato."""
        from app import textos

        assert "fitosanitario" not in textos.ALMACEN["categoria_fitosanitario"].lower()
        assert textos.ALMACEN["categoria_fitosanitario"] == "Productos de tratamiento"

    def test_un_lote_sin_caducidad_no_se_presenta_como_que_no_caduca(self):
        from app import textos

        assert "No es que no caduque" in textos.ALMACEN["sin_caducidad_pista"]

    def test_los_textos_que_llevan_cuenta_tienen_singular_y_plural(self):
        """«1 albaranes» es lo primero que hace desconfiar de un programa."""
        from app import textos

        for base in ("cuantos_albaranes", "cuantos_articulos"):
            assert textos.ALMACEN.get(f"{base}_uno"), f"falta el singular de {base}"
            assert textos.ALMACEN.get(base), f"falta el plural de {base}"
            assert "{cuantos" not in textos.ALMACEN[f"{base}_uno"]
        assert textos.con_cuenta(textos.ALMACEN, "cuantos_albaranes", 1) == "Tienes 1 albarán apuntado."
        assert textos.con_cuenta(textos.ALMACEN, "cuantos_albaranes", 3) == "Tienes 3 albaranes apuntados."


def textos_del_almacen() -> dict:
    from app import textos

    return dict(textos.ALMACEN)


def _todos_los_textos_visibles() -> list[str]:
    from app import textos

    return textos.textos_visibles()


# --------------------------------------------------------------------------
# La puesta al día de una instalación que ya existe
# --------------------------------------------------------------------------


class TestLaBaseSePoneAlDiaSola:
    def test_las_tablas_nuevas_se_crean_solas(self, db_sesion):
        """Las tablas nuevas las crea el programa al arrancar (`create_all`): no hay que pedirle
        nada a nadie, y por eso este ticket no necesita ninguna columna nueva en una tabla vieja."""
        from sqlalchemy import inspect

        from app.database import engine

        tablas = set(inspect(engine).get_table_names())
        for tabla in (
            "articulos",
            "lotes",
            "movimientos_de_existencias",
            "recepciones",
            "lineas_de_recepcion",
        ):
            assert tabla in tablas

    def test_todas_las_tablas_del_almacen_son_de_una_finca(self):
        """`explotacion_id` en todas: es lo que garantiza que un agricultor no vea lo de otro."""
        from app import models

        for tabla in (
            "articulos",
            "lotes",
            "movimientos_de_existencias",
            "recepciones",
            "lineas_de_recepcion",
        ):
            columnas = models.Base.metadata.tables[tabla].columns
            assert "explotacion_id" in columnas, f"«{tabla}» no dice de qué finca es"

    def test_un_movimiento_siempre_esta_en_un_lote(self):
        """No hay mercancía suelta que no se pueda contar: todo lo que hay está en algún lote."""
        from app import models

        columna = models.Base.metadata.tables["movimientos_de_existencias"].columns["lote_id"]
        assert columna.nullable is False
