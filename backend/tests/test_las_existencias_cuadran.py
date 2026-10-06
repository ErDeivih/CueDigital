"""Que las existencias cuadren y que todas las vistas físicas digan lo mismo (T21).

## Por qué existe este fichero

En este programa hay **dos libros** que hasta hoy no se hablaban: la cesta de productos (lo comprado en
las facturas menos los tratamientos: `servicios.situacion_de_la_cesta`) y el almacén (existencias
físicas por envases y lotes: `servicios.existencias_del_almacen`). Un trabajo que gasta de un envase
mueve el segundo y el primero no se entera, así que dos pantallas del mismo programa pueden decir dos
cosas distintas del mismo artículo.

Lo que se comprueba aquí, en el orden en que se lee:

  1. **La aritmética y la relación por identificador** (`TestElSaldoFisico…`, primeros bloques): contra
     `app/existencias.py`, que es lógica pura. Estas pruebas **pasan ya**.
  2. **El caso de aceptación del encargo, contra la API de verdad** (`TestElCasoDelEncargo…`):
     recepción de 40 L → trabajo que consume 6 L → **todas las vistas físicas dicen 34 L**; el reenvío
     no duplica; la corrección y la anulación actualizan todas las vistas; y la factura posterior al
     albarán no añade otra entrada.
  3. **El mismo consumo por dos puertas** (`TestElMismoConsumoPorDosPuertas`): un tratamiento apuntado a
     mano y la salida que ese mismo tratamiento provoca en el almacén **no se cuentan dos veces**.
  4. **Lo que el coordinador tiene que cablear** (`TestLoQueEsperaAlCableado`): las vistas que hoy no
     consultan el saldo físico. Estas pruebas **esperan** a que `existencias.py` esté enchufado, y lo
     dicen con un mensaje claro en vez de fallar por un `KeyError`.

## De dónde sale cada cosa

  · La **recepción** es un albarán: `POST /api/almacen/recepciones` (`Recepcion` + `LineaDeRecepcion` →
    `Lote` + `MovimientoDeExistencias` de entrada). Es lo único que mete mercancía.
  · El **consumo** es lo que sale con un apunte detrás: `POST /api/almacen/salidas`, o la puerta del
    trabajo (`POST /api/trabajos`, que la llama por dentro).
  · La **existencia física** es el saldo de los movimientos, y se lee en `GET /api/almacen/existencias`.

Las dos últimas clases son **la aceptación del encargo**: si el coordinador enchufa `existencias.py` y
alguna de ellas se queda en rojo, es que las vistas han dejado de decir lo mismo.
"""

from __future__ import annotations

import ast
import json
import pathlib
import textwrap

import pytest

from app import existencias, legal, servicios, textos

RAIZ = pathlib.Path(__file__).resolve().parents[2]
EL_INFORME = RAIZ / "docs" / "T21_EXISTENCIAS.md"

NIF_DEL_PROVEEDOR = "B34123456"


# --------------------------------------------------------------------------
# Ayudas: lo que hace la pantalla, hecho desde el test
# --------------------------------------------------------------------------


def _producto(cliente, cabeceras, **cambios) -> dict:
    """Un producto de la cesta con su unidad de compra, que es lo que enlaza con el almacén."""
    cuerpo = {
        "nombre_comercial": "Glifosato 36 SL",
        "numero_registro": "24.123",
        "dosis_maxima": 2.0,
        "unidad_dosis": "L/ha",
        "plazo_seguridad_dias": 21,
        "unidad_compra": "L",
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/productos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _pedir_recepcion(cliente, cabeceras, **cambios):
    """Manda un albarán y devuelve la respuesta entera, para poder mirar el código de estado."""
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
                "cantidad": 40.0,
                "unidad_de_la_cantidad": "L",
                "numero_lote": "4471-A",
                "fecha_caducidad": "2028-06-30",
                "presentacion": "garrafa de 20 L",
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


def _un_tratamiento(cliente, cabeceras, campana, parcela, producto_id, dosis, superficie, **cambios):
    """Un tratamiento con su total calculado por el programa (dosis × hectáreas)."""
    cuerpo = {
        "campana_id": campana["id"],
        "fecha": "2026-05-05",
        "parcela_id": parcela["id"],
        "superficie_tratada_ha": superficie,
        "justificacion": "Vi la plaga o la hierba en el campo",
        "producto_id": producto_id,
        "dosis": dosis,
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/tratamientos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _una_salida(cliente, cabeceras, **cambios):
    """Gastar de un lote por la puerta de las salidas. Devuelve la respuesta entera: el código importa."""
    cuerpo = {"apunte_tipo": "tratamiento", "apunte_id": 0, "lote_id": 0}
    cuerpo.update(cambios)
    return cliente.post("/api/almacen/salidas", headers=cabeceras, json=cuerpo)


def _pedir_trabajo(cliente, cabeceras, campana, parcela, **cambios):
    """Manda un trabajo hecho y devuelve la respuesta entera: el código importa (201 o 200)."""
    cuerpo = {
        "campana_id": campana["id"],
        "tipo": "tratamiento",
        "fecha": "2026-05-20",
        "parcela_id": parcela["id"],
        "superficie_ha": 2.0,
        "observaciones": "Se echó con el pulverizador grande",
    }
    cuerpo.update(cambios)
    return cliente.post("/api/trabajos", headers=cabeceras, json=cuerpo)


def _un_trabajo(cliente, cabeceras, campana, parcela, **cambios):
    """Un trabajo hecho que gasta de un envase. La puerta es `POST /api/trabajos`."""
    respuesta = _pedir_trabajo(cliente, cabeceras, campana, parcela, **cambios)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _corregir_trabajo(cliente, cabeceras, campana, parcela, labor_id, **cambios):
    """Corregir un trabajo hecho: la puerta pide el cuerpo entero (`TrabajoEntrada`)."""
    cuerpo = {
        "campana_id": campana["id"],
        "tipo": "tratamiento",
        "fecha": "2026-05-20",
        "parcela_id": parcela["id"],
        "superficie_ha": 2.0,
    }
    cuerpo.update(cambios)
    return cliente.put(f"/api/trabajos/{labor_id}", headers=cabeceras, json=cuerpo)


def _una_factura(cliente, cuenta, **cambios) -> dict:
    """Una factura de compra sin fichero, como cuando se teclea a mano."""
    cuerpo = {
        "fecha": "2026-03-20",
        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "proveedor_nif": NIF_DEL_PROVEEDOR,
        "numero_factura": "2026/00123",
        "total": 100.0,
        "leida_por": "a mano",
        "lineas": [{"descripcion": "GLIFOSATO 36% SL 40 L", "cantidad": 40.0, "unidad": "L"}],
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
    for fila in datos["productos"]:
        if fila["producto_id"] == producto_id:
            return fila
    raise AssertionError(f"el producto {producto_id} no está en la cesta: {datos['productos']}")


def _el_libro(cliente, cabeceras, **params) -> list[dict]:
    respuesta = cliente.get("/api/almacen/movimientos", headers=cabeceras, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _el_libro_que_cuenta(cliente, cabeceras, **params) -> list[dict]:
    """El libro **solo con lo que cuenta hoy**.

    Es lo que hay que pasarle al saldo: un movimiento anulado, o cuyo apunte está anulado, sigue en el
    libro —nada se borra— pero no ha movido nada. Contarlo daría un saldo que no es el de verdad.
    """
    return _el_libro(cliente, cabeceras, solo_los_que_cuentan=True, **params)


def _los_articulos_crudos(cliente, cabeceras) -> list[dict]:
    """Los artículos tal y como los devuelve su puerta, con **su `id`**, que es lo que enlaza.

    Se piden a `GET /api/almacen/articulos` y no a `existencias` porque la vista de existencias sirve
    para pintar y no promete traer el identificador. El enlace producto ↔ artículo va por
    `producto_id`, y ese campo está en el artículo.
    """
    respuesta = cliente.get("/api/almacen/articulos", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _la_vista_fisica(cliente, cabeceras) -> dict:
    """**Lo que la pantalla tiene que pintar**, montado con lo que devuelven las puertas de verdad.

    Esto es lo que el coordinador tiene que cablear en el endpoint: las filas de la cesta, los artículos
    y los movimientos del almacén, y `existencias.el_saldo_fisico_de_una_cesta` para que cada artículo
    salga **una vez con un solo saldo**. Mientras el cableado no esté, esta prueba demuestra dos cosas a
    la vez: que la lógica pura acierta con los datos reales, y que los datos que hacen falta **ya se
    sirven** por las puertas que existen.
    """
    cesta = _la_cesta(cliente, cabeceras)
    movimientos = _el_libro_que_cuenta(cliente, cabeceras)
    return existencias.el_saldo_fisico_de_una_cesta(
        cesta["productos"],
        _los_articulos_crudos(cliente, cabeceras),
        movimientos,
        # **Sin pasarle `apuntes` a propósito**, que es como lo va a llamar el coordinador: la lista de
        # consumos se saca de los propios movimientos del almacén, y con eso ya se reconoce el mismo
        # consumo apuntado por las dos puertas (`labor 3` en el libro es `labor 3` en el apunte).
        compra_sin_entrar=_existencias(cliente, cabeceras)["comprado_sin_entrar"],
    )


def _el_renglon(vista: dict, producto_id: int) -> existencias.ElCuadreDeUnArticulo:
    for fila in vista["articulos"]:
        if fila.de_la_cesta and fila.de_la_cesta["ficha_id"] == producto_id:
            return fila
    raise AssertionError(
        f"el producto {producto_id} no tiene ningún artículo del almacén en la vista: "
        f"{[(f.articulo_id, f.nombre, f.de_la_cesta) for f in vista['articulos']]}"
    )


@pytest.fixture
def parcela_grande(crear_parcela):
    """10 ha, para que las cuentas del test salgan redondas."""
    return crear_parcela(alias="La Grande", superficie_ha=10.0)


# ==========================================================================
# 1. La aritmética del saldo físico y la relación por identificador
#
# Lógica pura: no hace falta ni servidor ni base. Estas pruebas **pasan ya** (son las que protegen
# `app/existencias.py` mientras el coordinador cablea lo demás).
# ==========================================================================


class TestQueEsCadaCosa:
    """Comprar, recibir, consumir y tener son **cuatro hechos distintos**, y aquí no se mezclan."""

    def test_la_compra_no_es_una_recepcion(self):
        """La factura no mete mercancía: lo que entra es el albarán. Es el fallo que más se repite."""
        una_compra = {
            "articulo_id": 1,
            "lote_id": None,
            "tipo": "entrada",
            "origen_tipo": "factura",
            "cantidad": 40.0,
            "unidad": "L",
            "cuenta": True,
            # Una línea de factura **no** es un movimiento: no tiene lote ni tipo.
        }
        assert existencias.es_entrada(una_compra) is True  # si se apuntó la entrada, entró
        # Y una compra sin movimiento no es una entrada: no hay nada que contar.
        assert not hasattr(existencias, "es_entrada_de_factura")

    def test_las_cuatro_clases_de_hecho_tienen_su_nombre(self):
        assert existencias.ClaseDeHecho.COMPRA == "compra"
        assert existencias.ClaseDeHecho.RECEPCION == "recepcion"
        assert existencias.ClaseDeHecho.CONSUMO == "consumo"
        assert existencias.ClaseDeHecho.EXISTENCIA == "existencia"
        # Y son cuatro cosas distintas, no cuatro nombres de lo mismo.
        assert len({
            existencias.ClaseDeHecho.COMPRA,
            existencias.ClaseDeHecho.RECEPCION,
            existencias.ClaseDeHecho.CONSUMO,
            existencias.ClaseDeHecho.EXISTENCIA,
        }) == 4

    def test_una_entrada_es_lo_que_mete_mercancia_y_una_salida_lo_que_la_gasta(self):
        entrada = {"tipo": "entrada", "cantidad": 40.0, "unidad": "L", "cuenta": True}
        salida = {"tipo": "salida", "cantidad": 6.0, "unidad": "L", "cuenta": True}
        assert existencias.es_entrada(entrada) is True
        assert existencias.es_consumo(entrada) is False
        assert existencias.es_consumo(salida) is True
        assert existencias.es_entrada(salida) is False

    def test_una_merma_baja_el_saldo_pero_no_es_un_consumo(self):
        """Lo que se rompe o se derrama **no se ha echado en la tierra**: contarlo como gastado diría
        que el producto se aplicó, y eso es una afirmación distinta."""
        merma = {"tipo": "merma", "cantidad": 2.0, "unidad": "L", "cuenta": True}
        assert existencias.es_consumo(merma) is False
        assert existencias.SIGNO_DE_CADA_TIPO["merma"] == -1
        assert existencias.SIGNO_DE_CADA_TIPO["salida"] == -1

    def test_un_movimiento_anulado_no_cuenta(self):
        anulada = {"tipo": "salida", "cantidad": 6.0, "unidad": "L", "cuenta": False}
        assert existencias.es_consumo(anulada) is False
        assert existencias.es_entrada(anulada) is False

    def test_un_movimiento_del_que_no_se_sabe_si_cuenta_se_cuenta(self):
        """Si la fila no trae el `cuenta` —una API que no conoce anulaciones— se da por contada: **nunca
        se inventa un «no cuenta»**, que escondería mercancía que existe."""
        assert existencias.servicio_contado({"tipo": "entrada", "cantidad": 5.0}) is True


class TestLaRelacionVaPorIdentificador:
    """Producto ↔ artículo ↔ lote se relacionan **por identificador**, y por nada más."""

    def test_dos_fichas_con_el_mismo_nombre_no_se_unen(self):
        """Es la mitad del encargo. Si se unieran por el nombre, el envase de un producto acabaría
        contando en la cuenta de otro y eso no se puede deshacer."""
        articulos = [
            {"id": 1, "nombre": "Glifosato 36 SL", "producto_id": 7, "fertilizante_id": None},
            {"id": 2, "nombre": "GLIFOSATO 36 % SL", "producto_id": None, "fertilizante_id": None},
        ]
        relacion = existencias.la_relacion_por_identificador(articulos)
        assert relacion["producto"] == {7: 1}
        # El artículo 2 se llama **casi** igual y no se une a nada: se queda sin equivalencia.
        assert existencias.la_ficha_de_un_articulo(articulos[1]) is None

    def test_el_enganche_es_el_identificador_de_la_ficha(self):
        articulos = [
            {"id": 4, "nombre": "Nitrato amónico", "producto_id": None, "fertilizante_id": 2},
        ]
        relacion = existencias.la_relacion_por_identificador(articulos)
        assert existencias.el_articulo_de_una_ficha("fertilizante", 2, relacion) == 4
        assert existencias.el_articulo_de_una_ficha("fertilizante", 3, relacion) is None
        assert existencias.el_articulo_de_una_ficha("producto", 2, relacion) is None

    def test_una_ficha_sin_articulo_no_es_un_cero(self):
        """`None` es «no hay con qué relacionarlo», y eso se declara. Un cero diría que no queda nada."""
        relacion = existencias.la_relacion_por_identificador([])
        assert existencias.el_articulo_de_una_ficha("producto", 99, relacion) is None

    def test_si_dos_articulos_reclaman_la_misma_ficha_manda_el_de_identificador_mas_bajo(self):
        """Cuando pasa (el mismo producto dado de alta dos veces), se elige **por una regla escrita** y
        no por parecido: así el resultado es el mismo hoy y mañana."""
        articulos = [
            {"id": 9, "nombre": "Otro nombre", "producto_id": 7, "fertilizante_id": None},
            {"id": 3, "nombre": "Glifosato", "producto_id": 7, "fertilizante_id": None},
        ]
        relacion = existencias.la_relacion_por_identificador(articulos)
        assert relacion["producto"] == {7: 3}

    def test_los_lotes_de_un_articulo_van_por_su_articulo_id(self):
        lotes = [
            {"id": 2, "articulo_id": 1, "numero_lote": "B", "fecha_caducidad": None},
            {"id": 1, "articulo_id": 1, "numero_lote": "A", "fecha_caducidad": "2027-01-01"},
            {"id": 3, "articulo_id": 2, "numero_lote": "C", "fecha_caducidad": "2026-01-01"},
        ]
        suyos = existencias.los_lotes_de_un_articulo(lotes, articulo_id=1)
        assert [lote["numero_lote"] for lote in suyos] == ["A", "B"]
        # El que no tiene caducidad va **al final**, no el primero: no saber cuándo caduca no es
        # «el que más dura».
        assert suyos[-1]["fecha_caducidad"] is None

    def test_los_movimientos_de_un_articulo_y_de_un_lote(self):
        movimientos = [
            {"articulo_id": 1, "lote_id": 10, "tipo": "entrada"},
            {"articulo_id": 1, "lote_id": 11, "tipo": "salida"},
            {"articulo_id": 2, "lote_id": 12, "tipo": "entrada"},
        ]
        assert len(existencias.los_movimientos_de_un_articulo(movimientos, articulo_id=1)) == 2
        assert len(
            existencias.los_movimientos_de_un_articulo(
                movimientos, articulo_id=1, lote_id=11
            )
        ) == 1


class TestElSaldoFisicoDelArticulo:
    """El saldo físico sale **solo de los movimientos**, y cuando no se puede saber se dice por qué."""

    def test_cuarenta_menos_seis_son_treinta_y_cuatro(self):
        movimientos = [
            {
                "articulo_id": 1,
                "lote_id": 1,
                "tipo": "entrada",
                "cantidad": 40.0,
                "unidad": "L",
                "cuenta": True,
            },
            {
                "articulo_id": 1,
                "lote_id": 1,
                "tipo": "salida",
                "cantidad": 6.0,
                "unidad": "L",
                "cuenta": True,
            },
        ]
        saldo = existencias.el_saldo_fisico(
            movimientos, articulo={"id": 1, "nombre": "Glifosato 36 SL", "unidad": "L"}
        )
        assert saldo["saldo"] == 34.0
        assert saldo["se_puede_saber"] is True
        assert saldo["entradas"] == 40.0
        assert saldo["salidas"] == 6.0

    def test_una_factura_no_mete_mercancia_en_el_saldo(self):
        """El saldo se calcula con lo que **entró**, no con lo que se compró. Con la compra apuntada y
        ningún albarán, el saldo es cero y eso se sabe."""
        saldo = existencias.el_saldo_fisico([], articulo={"id": 1, "nombre": "X", "unidad": "L"})
        assert saldo["saldo"] == 0.0
        assert saldo["sin_movimientos"] is True

    def test_sin_la_cantidad_de_una_entrada_no_se_sabe_lo_que_queda_y_no_es_cero(self):
        """El caso del albarán con la casilla borrada. **Un cero diría que no queda nada** y el
        agricultor iría a comprar por nada."""
        movimientos = [
            {"articulo_id": 1, "lote_id": 1, "tipo": "entrada", "cantidad": None, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 1, "tipo": "salida", "cantidad": 6.0, "unidad": "L", "cuenta": True},
        ]
        saldo = existencias.el_saldo_fisico(movimientos, articulo={"id": 1, "nombre": "X", "unidad": "L"})
        assert saldo["saldo"] is None
        assert saldo["se_puede_saber"] is False
        assert saldo["motivo_codigo"] == "AL30_falta_la_cantidad"

    def test_los_litros_y_los_kilos_no_se_restan(self):
        movimientos = [
            {"articulo_id": 1, "lote_id": 1, "tipo": "entrada", "cantidad": 40.0, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 1, "tipo": "salida", "cantidad": 6.0, "unidad": "kg", "cuenta": True},
        ]
        saldo = existencias.el_saldo_fisico(movimientos, articulo={"id": 1, "nombre": "X", "unidad": "L"})
        assert saldo["saldo"] is None
        assert saldo["motivo_codigo"] == "AL31_unidades_que_no_cuadran"

    def test_el_saldo_negativo_se_devuelve_tal_cual(self):
        """Señala que falta una entrada o que hay una salida de más. Taparlo con un cero escondería el
        problema."""
        movimientos = [
            {"articulo_id": 1, "lote_id": 1, "tipo": "entrada", "cantidad": 3.0, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 1, "tipo": "salida", "cantidad": 5.0, "unidad": "L", "cuenta": True},
        ]
        saldo = existencias.el_saldo_fisico(movimientos, articulo={"id": 1, "nombre": "X", "unidad": "L"})
        assert saldo["saldo"] == -2.0
        assert saldo["motivo_codigo"] == "AL33_saldo_negativo"

    def test_el_saldo_no_se_calcula_dos_veces_distinto(self):
        """**La única resta es la del almacén.** Esta prueba ata las dos: si alguien reescribiera la
        aritmética aquí y un día se separaran, esto se pone rojo."""
        movimientos = [
            {"articulo_id": 1, "lote_id": 1, "tipo": "entrada", "cantidad": 40.0, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 1, "tipo": "salida", "cantidad": 6.0, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 1, "tipo": "merma", "cantidad": 1.0, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 1, "tipo": "ajuste", "cantidad": -0.5, "unidad": "L", "cuenta": True},
        ]
        mio = existencias.el_saldo_fisico(movimientos, articulo={"id": 1, "nombre": "X", "unidad": "L"})
        suyo = servicios.saldo_de_un_conjunto(movimientos, "L")
        assert mio["saldo"] == suyo["saldo"] == 32.5

    def test_los_numeros_de_cada_lote_salen_de_sus_propios_movimientos(self):
        movimientos = [
            {"articulo_id": 1, "lote_id": 10, "tipo": "entrada", "cantidad": 20.0, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 10, "tipo": "salida", "cantidad": 5.0, "unidad": "L", "cuenta": True},
            {"articulo_id": 1, "lote_id": 11, "tipo": "entrada", "cantidad": 20.0, "unidad": "L", "cuenta": True},
        ]
        saldo = existencias.el_saldo_fisico(movimientos, articulo={"id": 1, "nombre": "X", "unidad": "L"})
        assert saldo["saldo"] == 35.0
        por_lote = {fila["lote_id"]: fila["saldo"] for fila in saldo["lotes"]}
        assert por_lote == {10: 15.0, 11: 20.0}
        # Y las dos cuentas cuadran: los envases suman el total, que es lo que hace que un saldo por
        # lote sirva para algo.
        assert sum(por_lote.values()) == saldo["saldo"]


class TestElMismoConsumoNoSeCuentaDosVeces:
    """Un consumo apuntado en el cuaderno y su salida del almacén son **el mismo consumo por dos
    puertas**. Se cuenta una vez, y se dice."""

    def _un_apunte(self, **cambios) -> dict:
        apunte = {
            "origen_tipo": "tratamiento",
            "origen_id": 12,
            "producto_id": 7,
            "cantidad": 6.0,
            "unidad": "L",
        }
        apunte.update(cambios)
        return apunte

    def _una_salida(self, **cambios) -> dict:
        movimiento = {
            "articulo_id": 1,
            "lote_id": 1,
            "tipo": "salida",
            "origen_tipo": "tratamiento",
            "origen_id": 12,
            "cantidad": 6.0,
            "unidad": "L",
            "cuenta": True,
        }
        movimiento.update(cambios)
        return movimiento

    def test_el_apunte_con_su_salida_es_el_mismo_consumo(self):
        deduplicado = existencias.la_deduplicacion([self._un_apunte()], [self._una_salida()])
        assert len(deduplicado["del_almacen"]) == 1
        assert deduplicado["solo_en_la_cesta"] == []
        assert deduplicado["el_mismo_consumo"][0]["es_el_mismo_consumo"] is True
        assert deduplicado["el_mismo_consumo"][0]["salidas_del_almacen"] == 1

    def test_un_apunte_sin_salida_no_ha_movido_ningun_envase(self):
        """Se cuenta en la cesta y el almacén no lo conoce. **No se tira**: se declara, porque un
        apunte que desaparece es un litro que nadie cuenta."""
        deduplicado = existencias.la_deduplicacion([self._un_apunte()], [])
        assert deduplicado["del_almacen"] == []
        assert len(deduplicado["solo_en_la_cesta"]) == 1

    def test_dos_salidas_del_mismo_apunte_son_dos_consumos_y_ninguna_se_tira(self):
        """Dos garrafas gastadas en el mismo tratamiento: el apunte de la cesta es uno y las salidas
        del almacén son dos. Contar dos veces el mismo consumo es el fallo; tirar una salida, otro."""
        dos = [
            self._una_salida(lote_id=1, cantidad=3.0),
            self._una_salida(lote_id=2, cantidad=3.0),
        ]
        deduplicado = existencias.la_deduplicacion([self._un_apunte(cantidad=6.0)], dos)
        assert len(deduplicado["del_almacen"]) == 1
        assert deduplicado["el_mismo_consumo"][0]["salidas_del_almacen"] == 2
        assert deduplicado["el_mismo_consumo"][0]["cantidad_en_el_almacen"] == 6.0
        assert deduplicado["el_mismo_consumo"][0]["es_el_mismo_consumo"] is True

    def test_dos_consumos_distintos_no_se_unen(self):
        """Dos tratamientos distintos del mismo producto con la misma cantidad son **dos consumos de
        verdad**, y unirlos escondería producto echado."""
        otro_tratamiento = self._una_salida(origen_id=13)
        deduplicado = existencias.la_deduplicacion([self._un_apunte()], [otro_tratamiento])
        assert deduplicado["del_almacen"] == []
        assert len(deduplicado["solo_en_la_cesta"]) == 1

    def test_si_no_se_puede_comprobar_que_son_el_mismo_no_se_afirma(self):
        """Tres finales y no dos: sí, no, y **no lo he podido comprobar**. Con una salida de 1 L y un
        apunte de 2 L no se puede decir que sean el mismo consumo, así que no se dice."""
        deduplicado = existencias.la_deduplicacion(
            [self._un_apunte(cantidad=2.0)], [self._una_salida(cantidad=1.0)]
        )
        assert deduplicado["el_mismo_consumo"][0]["es_el_mismo_consumo"] is False
        deduplicado = existencias.la_deduplicacion(
            [self._un_apunte(cantidad=None)], [self._una_salida()]
        )
        assert deduplicado["el_mismo_consumo"][0]["es_el_mismo_consumo"] is None

    def test_un_apunte_anulado_no_hace_que_el_consumo_cuente(self):
        """La salida anulada no cuenta: su apunte queda «solo en la cesta» y se dice, que es lo que
        evita dar por gastado lo que no se gastó."""
        deduplicado = existencias.la_deduplicacion(
            [self._un_apunte()], [self._una_salida(cuenta=False)]
        )
        assert deduplicado["del_almacen"] == []
        assert len(deduplicado["solo_en_la_cesta"]) == 1


class TestLaVistaQueSeTieneQuePintar:
    """La vista que el coordinador tiene que servir: **un artículo, un saldo**, y lo demás al lado."""

    def _la_vista(self, **cambios) -> dict:
        articulos = [
            {
                "id": 1,
                "nombre": "Glifosato 36 SL",
                "categoria": "fitosanitario",
                "unidad": "L",
                "producto_id": 7,
                "fertilizante_id": None,
            }
        ]
        movimientos = [
            {
                "articulo_id": 1,
                "lote_id": 1,
                "tipo": "entrada",
                "cantidad": 40.0,
                "unidad": "L",
                "cuenta": True,
                "origen_tipo": "recepcion",
                "origen_id": 1,
            },
            {
                "articulo_id": 1,
                "lote_id": 1,
                "tipo": "salida",
                "cantidad": 6.0,
                "unidad": "L",
                "cuenta": True,
                "origen_tipo": "tratamiento",
                "origen_id": 12,
            },
        ]
        cesta = [
            {
                "producto_id": 7,
                "nombre_comercial": "Glifosato 36 SL",
                "numero_registro": "24.123",
                "unidad_compra": "L",
                "comprado": 40.0,
                "comprado_de_donde": "facturas",
                "gastado": 6.0,
                "apuntes": 1,
                "queda": 34.0,
                "se_puede_comparar": True,
                "motivo": "",
            }
        ]
        datos = {
            "cesta": cesta,
            "articulos": articulos,
            "movimientos": movimientos,
            "apuntes": [
                {
                    "origen_tipo": "tratamiento",
                    "origen_id": 12,
                    "producto_id": 7,
                    "cantidad": 6.0,
                    "unidad": "L",
                }
            ],
            "compra_sin_entrar": [],
        }
        datos.update(cambios)
        return existencias.el_saldo_fisico_de_una_cesta(
            datos["cesta"], datos["articulos"], datos["movimientos"],
            apuntes=datos["apuntes"], compra_sin_entrar=datos["compra_sin_entrar"],
        )

    def test_el_saldo_de_la_vista_es_el_fisico_y_la_cesta_va_al_lado(self):
        vista = self._la_vista()
        renglon = _el_renglon(vista, 7)
        assert renglon.saldo_fisico == 34.0
        assert renglon.se_puede_saber is True
        # Lo que dice el otro libro **no se suma** al saldo: se enseña aparte.
        assert renglon.compra_apuntada == 40.0
        assert renglon.consumo_apuntado == 6.0

    def test_el_mismo_consumo_por_dos_puertas_no_se_resta_dos_veces(self):
        vista = self._la_vista()
        renglon = _el_renglon(vista, 7)
        assert renglon.saldo_fisico == 34.0, "el consumo se ha contado dos veces"
        assert renglon.consumos_que_no_se_cuentan_dos_veces == 1
        assert renglon.el_mismo_consumo[0]["origen_id"] == 12

    def test_un_producto_sin_articulo_queda_pendiente_y_no_en_cero(self):
        """El dato antiguo sin correspondencia: **pendiente, no cero**."""
        vista = self._la_vista(
            articulos=[],
            movimientos=[],
            apuntes=[],
            cesta=[
                {
                    "producto_id": 99,
                    "nombre_comercial": "Producto viejo sin almacén",
                    "unidad_compra": "L",
                    "comprado": 20.0,
                    "gastado": 0.0,
                    "apuntes": 0,
                }
            ],
        )
        assert vista["articulos"] == []
        assert vista["cuantos_pendientes"] == 1
        pendiente = vista["pendientes"][0]
        assert pendiente["saldo_fisico"] is None
        assert pendiente["motivo_codigo"] == "A24_el_producto_no_tiene_articulo"
        assert pendiente["compra_apuntada"] == 20.0

    def test_un_producto_comprado_sin_albaran_no_se_convierte_en_existencias(self):
        """Hay artículo, hay compra apuntada y **no ha entrado nada**. El saldo es cero y lo que se dice
        es que la mercancía no ha llegado: no es un descuadre ni unas existencias perdidas."""
        vista = self._la_vista(
            movimientos=[],
            apuntes=[],
            cesta=[
                {
                    "producto_id": 7,
                    "nombre_comercial": "Glifosato 36 SL",
                    "unidad_compra": "L",
                    "comprado": 40.0,
                    "gastado": 0.0,
                    "apuntes": 0,
                }
            ],
        )
        renglon = _el_renglon(vista, 7)
        assert renglon.saldo_fisico == 0.0
        assert renglon.situacion == "pendiente"
        assert "el albarán" in renglon.que_pasa
        assert vista["cuantos_sin_entrar"] == 0  # no se ha declarado compra sin entrar aquí

    def test_un_articulo_del_almacen_sin_ficha_de_la_cesta_y_sin_entrar_queda_pendiente(self):
        """Un artículo que no sale de ninguna ficha de la cesta y del que **no ha entrado nada**: el
        cero es una entrada que falta, y se dice."""
        vista = self._la_vista(
            cesta=[],
            apuntes=[],
            movimientos=[],
            articulos=[
                {
                    "id": 5,
                    "nombre": "Cosa suelta",
                    "categoria": "otros",
                    "unidad": "kg",
                    "producto_id": None,
                    "fertilizante_id": None,
                }
            ],
        )
        renglon = vista["articulos"][0]
        assert renglon.saldo_fisico == 0.0
        assert renglon.situacion == "pendiente"
        assert "el albarán" in renglon.que_pasa

    def test_la_compra_sin_entrar_va_aparte_y_no_se_suma(self):
        vista = self._la_vista(compra_sin_entrar=[{"nombre": "Otra cosa", "lineas": 2}])
        assert vista["compra_sin_entrar"] == [{"nombre": "Otra cosa", "lineas": 2}]
        # Y el saldo del artículo no ha cambiado por tener una compra pendiente de recibir.
        assert _el_renglon(vista, 7).saldo_fisico == 34.0

    def test_un_articulo_que_no_es_de_la_cesta_sale_igual(self):
        """Una semilla o el aceite del taller no son fichas de la cesta y **no son un error**: salen con
        su saldo, que es lo que hay en el almacén."""
        vista = self._la_vista(
            cesta=[],
            apuntes=[],
            articulos=[
                {
                    "id": 5,
                    "nombre": "Semilla de trigo",
                    "categoria": "semilla",
                    "unidad": "kg",
                    "producto_id": None,
                    "fertilizante_id": None,
                }
            ],
            movimientos=[
                {
                    "articulo_id": 5,
                    "lote_id": 3,
                    "tipo": "entrada",
                    "cantidad": 500.0,
                    "unidad": "kg",
                    "cuenta": True,
                }
            ],
        )
        assert vista["cuantos"] == 1
        assert vista["articulos"][0].saldo_fisico == 500.0

    def test_cada_articulo_sale_una_vez(self):
        """Aunque haya dos artículos que reclamen la misma ficha, el saldo de cada uno es el suyo y
        ninguno se pierde por el camino."""
        vista = self._la_vista(
            articulos=[
                {
                    "id": 1,
                    "nombre": "Glifosato 36 SL",
                    "categoria": "fitosanitario",
                    "unidad": "L",
                    "producto_id": 7,
                    "fertilizante_id": None,
                },
                {
                    "id": 2,
                    "nombre": "Glifosato (el otro envase)",
                    "categoria": "fitosanitario",
                    "unidad": "L",
                    "producto_id": 7,
                    "fertilizante_id": None,
                },
            ]
        )
        assert vista["cuantos"] == 2
        assert {fila.articulo_id for fila in vista["articulos"]} == {1, 2}

    def test_sin_unidad_no_se_hace_la_cuenta_y_se_dice_que_falta_la_unidad(self):
        """Sin saber **en qué se mide** una entrada no se puede restar nada: no es un cero, es un «no
        se puede saber», y el texto que se enseña lo dice en lugar de dejar un número suelto."""
        vista = self._la_vista(
            cesta=[
                {
                    "producto_id": 7,
                    "nombre_comercial": "Cosa sin unidad",
                    "unidad_compra": "",
                    "comprado": 40.0,
                    "gastado": 6.0,
                    "apuntes": 1,
                }
            ],
            articulos=[
                {
                    "id": 1,
                    "nombre": "Cosa sin unidad",
                    "categoria": "otros",
                    "unidad": None,
                    "producto_id": 7,
                    "fertilizante_id": None,
                }
            ],
            movimientos=[
                {
                    "articulo_id": 1,
                    "lote_id": 1,
                    "tipo": "entrada",
                    "cantidad": 40.0,
                    "unidad": None,
                    "cuenta": True,
                },
                {
                    "articulo_id": 1,
                    "lote_id": 1,
                    "tipo": "salida",
                    "cantidad": 6.0,
                    "unidad": None,
                    "cuenta": True,
                },
            ],
            apuntes=[],
        )
        renglon = _el_renglon(vista, 7)
        assert renglon.saldo_fisico is None
        assert renglon.se_puede_saber is False
        assert renglon.motivo_codigo == "AL32_falta_la_unidad"
        texto = existencias.el_texto_de_un_saldo(renglon)
        assert "en qué se miden" in texto
        assert not texto.startswith("0")

    def test_cuando_no_se_puede_saber_el_texto_es_el_motivo(self):
        vista = self._la_vista(
            movimientos=[
                {
                    "articulo_id": 1,
                    "lote_id": 1,
                    "tipo": "entrada",
                    "cantidad": None,
                    "unidad": "L",
                    "cuenta": True,
                }
            ]
        )
        texto = existencias.el_texto_de_un_saldo(_el_renglon(vista, 7))
        assert "no se puede saber" in texto or "no puede" in texto
        assert not texto.startswith("0")


class TestLoQueSeProponeParaElArticuloQueFalta:
    """Dar de alta el artículo que falta **es una propuesta**, y con el enlace por identificador."""

    def test_la_propuesta_lleva_el_identificador_y_la_categoria(self):
        propuesta = existencias.el_articulo_que_falta_de_una_ficha(
            {
                "producto_id": 7,
                "nombre_comercial": "Glifosato 36 SL",
                "unidad_compra": "L",
                "numero_registro": "24.123",
            },
            explotacion_id=3,
        )
        assert propuesta["producto_id"] == 7
        assert propuesta["fertilizante_id"] is None
        assert propuesta["categoria"] == "fitosanitario"
        assert propuesta["unidad"] == "L"
        assert propuesta["numero_registro"] == "24.123"

    def test_sin_unidad_apuntada_el_articulo_se_queda_sin_unidad(self):
        """Un producto sin unidad de compra **no pasa a ser litros por conveniencia**."""
        propuesta = existencias.el_articulo_que_falta_de_una_ficha(
            {"producto_id": 7, "nombre_comercial": "X", "unidad_compra": ""},
            explotacion_id=3,
        )
        assert propuesta["unidad"] is None

    def test_sin_identificador_no_hay_propuesta(self):
        """No se enlaza por el nombre: si no hay identificador, no hay nada que proponer."""
        assert (
            existencias.el_articulo_que_falta_de_una_ficha(
                {"nombre_comercial": "X"}, explotacion_id=3
            )
            is None
        )


# ==========================================================================
# 2. Los textos: existen, no llevan jerga y cada hueco se rellena
# ==========================================================================


class TestLosTextosDeEsteTicket:
    def test_todos_los_codigos_tienen_su_frase(self):
        for codigo in existencias.CODIGOS_DE_TEXTO:
            assert codigo in existencias.MENSAJES
            assert existencias.MENSAJES[codigo].strip()

    def test_las_frases_estan_en_el_sitio_donde_vive_todo_el_texto(self):
        """**Las frases que ve el agricultor viven en `app/textos.py`** y no en el módulo.

        Mientras el coordinador no integre el bloque, esto se queda en rojo: es el recordatorio de que
        un texto escrito en un módulo de lógica deja de estar cubierto por la revisión de jerga y por el
        guardián que exige que toda clave que pide la pantalla exista.
        """
        faltan = [codigo for codigo in existencias.CODIGOS_DE_TEXTO if codigo not in textos.MENSAJES]
        assert not faltan, (
            "faltan en app/textos.py las frases de este ticket: "
            f"{faltan}. El bloque literal está en docs/T21_EXISTENCIAS.md"
        )
        for codigo in existencias.CODIGOS_DE_TEXTO:
            assert textos.MENSAJES[codigo] == existencias.MENSAJES[codigo]

    def test_cada_hueco_se_puede_rellenar(self):
        """Un mensaje que se pide y sale en blanco es lo primero que hace desconfiar de un programa."""
        huecos = {
            "A24_el_producto_no_tiene_articulo": {},
            "A25_los_dos_libros_dicen_lo_mismo": {},
            "A26_el_libro_viejo_no_tiene_saldo_fisico": {},
            "A27_unidades_que_no_se_pueden_restar": {"unidad": "L", "otra": "kg"},
            "A28_no_hay_articulo_del_que_sacar_el_saldo": {},
        }
        assert set(huecos) == set(existencias.CODIGOS_DE_TEXTO)
        for codigo, valores in huecos.items():
            relleno = existencias.mensaje(codigo, **valores)
            assert "{" not in relleno and "}" not in relleno

    def test_ninguna_frase_lleva_jerga(self):
        """La lista viva está en `textos.PALABRAS_PROHIBIDAS` y la comprueban tres pruebas del
        proyecto. Estas frases son nuevas, así que se revisan aquí también."""
        for codigo, frase in existencias.MENSAJES.items():
            encontradas = textos.palabras_prohibidas_encontradas(frase)
            assert not encontradas, f"«{codigo}» lleva jerga: {encontradas}"

    def test_lo_que_no_se_puede_hacer_se_dice_con_sus_palabras(self):
        """Los dos motivos que ya existían en el programa se usan tal cual, sin escribir una segunda
        versión de la misma frase."""
        assert textos.MENSAJES["A21_unidades_distintas"] in textos.MENSAJES.values()
        assert textos.MENSAJES["A22_gastado_mas_que_comprado"] in textos.MENSAJES.values()


# ==========================================================================
# 3. El caso del encargo, contra la API de verdad
# ==========================================================================


class TestElCasoDelEncargo:
    """**Recepción de 40 L → trabajo que consume 6 L → todas las vistas físicas muestran 34 L.**

    Se hace de punta a punta y por las puertas de verdad: el albarán por la suya, el trabajo por
    `POST /api/trabajos` (que descuenta por la puerta de las salidas) y la lectura por
    `/api/almacen/existencias` y por la vista del saldo físico.
    """

    @pytest.fixture
    def el_escenario(self, cliente, cuenta, campana, parcela_grande):
        producto = _producto(cliente, cuenta["cabeceras"])
        recibido = _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 40.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                    "fecha_caducidad": "2028-06-30",
                }
            ],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        lote = _el_lote(articulo, "4471-A")
        return {
            "producto": producto,
            "recepcion": recibido,
            "articulo": articulo,
            "lote": lote,
            "parcela": parcela_grande,
            "campana": campana,
            "cabeceras": cuenta["cabeceras"],
        }

    def _un_trabajo_que_gasta(self, cliente, el_escenario, **cambios):
        cambios.setdefault(
            "insumos",
            [
                {
                    "articulo_id": el_escenario["articulo"]["articulo_id"],
                    "lote_id": el_escenario["lote"]["lote_id"],
                    "cantidad": 6.0,
                    "unidad": "L",
                }
            ],
        )
        return _un_trabajo(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            **cambios,
        )

    def test_la_recepcion_mete_cuarenta_litros(self, cliente, el_escenario):
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 40.0
        assert articulo["entradas"] == 40.0
        assert el_escenario["lote"]["saldo"] == 40.0

    def test_el_trabajo_consume_seis_y_todas_las_vistas_fisicas_dicen_34(
        self, cliente, el_escenario
    ):
        hecho = self._un_trabajo_que_gasta(cliente, el_escenario)
        assert hecho["ya_estaba"] is False

        # (a) La vista del almacén, por su puerta.
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 34.0
        assert articulo["salidas"] == 6.0
        # (b) El lote, que es lo que mira una inspección cuando hay un aviso de partida.
        assert _el_lote(articulo, "4471-A")["saldo"] == 34.0
        # (c) La vista del saldo físico, que es la que tienen que consultar **todas** las pantallas.
        renglon = _el_renglon(_la_vista_fisica(cliente, el_escenario["cabeceras"]), el_escenario["producto"]["id"])
        assert renglon.saldo_fisico == 34.0
        assert renglon.situacion == "cuadra", renglon.que_pasa
        # (d) Y el libro dice de dónde salió: un solo consumo, con su apunte detrás.
        salidas = [
            fila
            for fila in _el_libro(cliente, el_escenario["cabeceras"])
            if fila["tipo"] == "salida"
        ]
        assert len(salidas) == 1
        assert salidas[0]["origen_tipo"] == "labor"
        assert salidas[0]["origen_id"] == hecho["hecho"]["id"]
        assert salidas[0]["cantidad"] == 6.0

    def test_reenviar_el_trabajo_no_duplica_el_consumo(self, cliente, el_escenario):
        """La cola del móvil reintenta sin preguntar. El trabajo se reconoce por su clave de reenvío y
        el consumo **no se descuenta dos veces**."""
        insumos = [
            {
                "articulo_id": el_escenario["articulo"]["articulo_id"],
                "lote_id": el_escenario["lote"]["lote_id"],
                "cantidad": 6.0,
                "unidad": "L",
            }
        ]
        primera = _un_trabajo(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            insumos=insumos,
            clave_de_reenvio="movil-1",
            id_local="movil-1",
        )
        segunda = _pedir_trabajo(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            insumos=insumos,
            clave_de_reenvio="movil-1",
            id_local="movil-1",
        )
        assert segunda.status_code == 200, segunda.text
        assert segunda.json()["ya_estaba"] is True
        assert segunda.json()["hecho"]["id"] == primera["hecho"]["id"]
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 34.0, "el reenvío ha descontado el consumo dos veces"
        assert len(
            [f for f in _el_libro(cliente, el_escenario["cabeceras"]) if f["tipo"] == "salida"]
        ) == 1

    def test_reenviar_el_albaran_no_duplica_la_entrada(self, cliente, el_escenario):
        repetido = _pedir_recepcion(
            cliente,
            el_escenario["cabeceras"],
            lineas=[
                {
                    "producto_id": el_escenario["producto"]["id"],
                    "cantidad": 40.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        assert repetido.status_code == 200, repetido.text
        assert repetido.json()["ya_estaba"] is True
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 40.0
        assert articulo["entradas"] == 40.0

    def test_anular_el_trabajo_devuelve_los_seis_litros_a_todas_las_vistas(
        self, cliente, el_escenario
    ):
        """**Anular actualiza todas las vistas**, y sin tocar el libro: el movimiento sigue ahí con su
        fecha y su autor, y lo que cambia es que deja de contar."""
        hecho = self._un_trabajo_que_gasta(cliente, el_escenario)
        assert _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")["saldo"] == 34.0

        anulado = cliente.post(
            f"/api/trabajos/{hecho['hecho']['id']}/anular",
            headers=el_escenario["cabeceras"],
            json={"motivo": "no se llegó a tratar esa tierra"},
        )
        assert anulado.status_code == 200, anulado.text

        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 40.0
        assert _el_lote(articulo, "4471-A")["saldo"] == 40.0
        renglon = _el_renglon(
            _la_vista_fisica(cliente, el_escenario["cabeceras"]), el_escenario["producto"]["id"]
        )
        assert renglon.saldo_fisico == 40.0
        # El movimiento sigue en el libro y dice por qué no cuenta.
        salidas = [
            fila
            for fila in _el_libro(cliente, el_escenario["cabeceras"])
            if fila["tipo"] == "salida"
        ]
        assert len(salidas) == 1
        assert salidas[0]["cuenta"] is False
        assert "anulado" in salidas[0]["no_cuenta_porque"]

    def test_corregir_el_trabajo_actualiza_todas_las_vistas(self, cliente, el_escenario):
        """Lo que sale del envase se corrige anulando la salida vieja y apuntando la nueva: **nunca
        quedan dos vivas**, así que el saldo es el de la corrección y no la suma de las dos."""
        hecho = self._un_trabajo_que_gasta(cliente, el_escenario)
        assert _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")["saldo"] == 34.0

        correccion = _corregir_trabajo(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            hecho["hecho"]["id"],
            insumos=[
                {
                    "articulo_id": el_escenario["articulo"]["articulo_id"],
                    "lote_id": el_escenario["lote"]["lote_id"],
                    "cantidad": 10.0,
                    "unidad": "L",
                }
            ],
        )
        assert correccion.status_code == 200, correccion.text

        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 30.0, "la corrección no ha actualizado el saldo (¿dos salidas vivas?)"
        assert articulo["salidas"] == 10.0
        vivas = [
            fila
            for fila in _el_libro(cliente, el_escenario["cabeceras"])
            if fila["tipo"] == "salida" and fila["cuenta"]
        ]
        assert len(vivas) == 1
        renglon = _el_renglon(
            _la_vista_fisica(cliente, el_escenario["cabeceras"]), el_escenario["producto"]["id"]
        )
        assert renglon.saldo_fisico == 30.0

    def test_corregir_a_la_baja_actualiza_todas_las_vistas(self, cliente, el_escenario):
        """Y corregir a menos (de 6 a 2) sube el saldo: la vista no se queda con el número viejo."""
        hecho = self._un_trabajo_que_gasta(cliente, el_escenario)
        correccion = _corregir_trabajo(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            hecho["hecho"]["id"],
            insumos=[
                {
                    "articulo_id": el_escenario["articulo"]["articulo_id"],
                    "lote_id": el_escenario["lote"]["lote_id"],
                    "cantidad": 2.0,
                    "unidad": "L",
                }
            ],
        )
        assert correccion.status_code == 200, correccion.text
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 38.0
        renglon = _el_renglon(
            _la_vista_fisica(cliente, el_escenario["cabeceras"]), el_escenario["producto"]["id"]
        )
        assert renglon.saldo_fisico == 38.0

    def test_la_factura_posterior_al_albaran_no_anade_otra_entrada(self, cliente, cuenta, el_escenario):
        """**A15.** La factura llega después: se engancha al albarán y el almacén sigue con 40 litros,
        no con 80. Las facturas no meten mercancía."""
        factura = _una_factura(
            cliente,
            cuenta,
            numero_factura="2026/00123",
            lineas=[
                {
                    "descripcion": "GLIFOSATO 36% SL 40 L",
                    "cantidad": 40.0,
                    "unidad": "L",
                    "producto_id": el_escenario["producto"]["id"],
                }
            ],
        )
        antes = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        enganchada = cliente.post(
            f"/api/almacen/recepciones/{el_escenario['recepcion']['recepcion']['id']}/factura",
            headers=el_escenario["cabeceras"],
            json={"factura_id": factura["id"]},
        )
        assert enganchada.status_code == 200, enganchada.text

        despues = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert despues["saldo"] == 40.0
        assert despues["entradas"] == antes["entradas"] == 40.0
        entradas = [
            fila
            for fila in _el_libro(cliente, el_escenario["cabeceras"])
            if fila["tipo"] == "entrada"
        ]
        assert len(entradas) == 1
        # Y la cesta, que sí cuenta la compra, cuenta **la compra una vez**: 40, no 80.
        fila = _fila_de_la_cesta(_la_cesta(cliente, el_escenario["cabeceras"]), el_escenario["producto"]["id"])
        assert fila["comprado"] == 40.0

    def test_el_consumo_del_trabajo_se_cruza_con_el_apunte_y_no_se_cuenta_dos_veces(
        self, cliente, el_escenario
    ):
        """El trabajo apunta la labor **y** la salida. La vista física las reconoce como **el mismo
        consumo** y no lo resta dos veces."""
        hecho = self._un_trabajo_que_gasta(cliente, el_escenario)
        vista = _la_vista_fisica(cliente, el_escenario["cabeceras"])
        renglon = _el_renglon(vista, el_escenario["producto"]["id"])
        assert renglon.saldo_fisico == 34.0
        assert renglon.consumos_que_no_se_cuentan_dos_veces == 1
        assert renglon.el_mismo_consumo[0]["origen_tipo"] == "labor"
        assert renglon.el_mismo_consumo[0]["origen_id"] == hecho["hecho"]["id"]
        assert renglon.el_mismo_consumo[0]["es_el_mismo_consumo"] is True


# ==========================================================================
# 4. El mismo consumo por dos puertas
# ==========================================================================


class TestElMismoConsumoPorDosPuertas:
    """Un tratamiento apuntado por su puerta (`POST /api/tratamientos`) y el consumo de ese mismo
    tratamiento sacado del envase (`POST /api/almacen/salidas`).

    **Son el mismo hecho visto por dos puertas**, así que el almacén baja una vez y la vista lo dice.
    """

    @pytest.fixture
    def el_escenario(self, cliente, cuenta, campana, parcela_grande):
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 40.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        return {
            "producto": producto,
            "articulo": articulo,
            "lote": _el_lote(articulo, "4471-A"),
            "parcela": parcela_grande,
            "campana": campana,
            "cabeceras": cuenta["cabeceras"],
        }

    def test_el_tratamiento_y_su_salida_bajan_el_almacen_una_sola_vez(self, cliente, el_escenario):
        apunte = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            el_escenario["producto"]["id"],
            1.0,
            6.0,
        )
        assert apunte["cantidad_total"] == 6.0
        salida = _una_salida(
            cliente,
            el_escenario["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte["id"],
            lote_id=el_escenario["lote"]["lote_id"],
        )
        assert salida.status_code == 201, salida.text
        # La cantidad sale del apunte: no hay que teclearla y no puede decir otra cosa.
        assert salida.json()["movimiento"]["cantidad"] == 6.0

        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 34.0
        assert len(
            [f for f in _el_libro(cliente, el_escenario["cabeceras"]) if f["tipo"] == "salida"]
        ) == 1

        vista = _la_vista_fisica(cliente, el_escenario["cabeceras"])
        renglon = _el_renglon(vista, el_escenario["producto"]["id"])
        assert renglon.saldo_fisico == 34.0
        assert renglon.consumos_que_no_se_cuentan_dos_veces == 1
        assert renglon.el_mismo_consumo[0]["origen_tipo"] == "tratamiento"
        assert renglon.el_mismo_consumo[0]["origen_id"] == apunte["id"]
        # Y la cesta sigue sabiendo lo suyo: lo echado son 6 litros, no 12.
        fila = _fila_de_la_cesta(_la_cesta(cliente, el_escenario["cabeceras"]), el_escenario["producto"]["id"])
        assert fila["gastado"] == 6.0

    def test_reenviar_la_salida_del_tratamiento_no_descuenta_dos_veces(self, cliente, el_escenario):
        apunte = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            el_escenario["producto"]["id"],
            1.0,
            6.0,
        )
        primera = _una_salida(
            cliente,
            el_escenario["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte["id"],
            lote_id=el_escenario["lote"]["lote_id"],
        )
        segunda = _una_salida(
            cliente,
            el_escenario["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte["id"],
            lote_id=el_escenario["lote"]["lote_id"],
        )
        assert primera.status_code == 201
        assert segunda.status_code == 200
        assert segunda.json()["ya_estaba"] is True
        assert segunda.json()["movimiento"]["id"] == primera.json()["movimiento"]["id"]
        assert _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")["saldo"] == 34.0

    def test_anular_el_tratamiento_devuelve_el_consumo_al_almacen(self, cliente, el_escenario):
        """Una anulación revierte el efecto **sin borrar la historia**: la salida sigue en el libro y
        deja de contar."""
        apunte = _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            el_escenario["producto"]["id"],
            1.0,
            6.0,
        )
        _una_salida(
            cliente,
            el_escenario["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte["id"],
            lote_id=el_escenario["lote"]["lote_id"],
        )
        anulado = cliente.post(
            f"/api/tratamientos/{apunte['id']}/anular",
            headers=el_escenario["cabeceras"],
            json={"motivo": "me equivoqué de producto"},
        )
        assert anulado.status_code == 200, anulado.text
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 40.0
        renglon = _el_renglon(
            _la_vista_fisica(cliente, el_escenario["cabeceras"]), el_escenario["producto"]["id"]
        )
        assert renglon.saldo_fisico == 40.0
        # Y el mismo consumo ya no se cruza: la salida no cuenta, así que no hay nada que descontar.
        assert renglon.consumos_que_no_se_cuentan_dos_veces == 0

    def test_un_tratamiento_sin_salida_no_ha_movido_ningun_envase(self, cliente, el_escenario):
        """Se apunta el tratamiento y **no se saca del envase**: el almacén no lo sabe, y eso se dice
        en vez de dar por hecho que el producto salió."""
        _un_tratamiento(
            cliente,
            el_escenario["cabeceras"],
            el_escenario["campana"],
            el_escenario["parcela"],
            el_escenario["producto"]["id"],
            1.0,
            6.0,
        )
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 40.0
        vista = _la_vista_fisica(cliente, el_escenario["cabeceras"])
        renglon = _el_renglon(vista, el_escenario["producto"]["id"])
        assert renglon.saldo_fisico == 40.0
        assert renglon.consumos_que_no_se_cuentan_dos_veces == 0


# ==========================================================================
# 5. Lo que espera al cableado del coordinador
#
# Estas pruebas son la **aceptación del encargo**: exigen que las pantallas que enseñan «te queda»
# consulten el saldo físico. Hoy no lo hacen —el endpoint de la cesta sirve la cuenta de facturas
# menos tratamientos—, así que se declaran aquí y se ponen en verde en cuanto `existencias.py` esté
# enchufado. **No se borran**: son el contrato.
# ==========================================================================


def _el_cableado_esta_hecho(cliente, cabeceras) -> bool:
    """Si la cesta ya sirve el saldo físico de cada producto, que es lo que pide el encargo."""
    respuesta = cliente.get("/api/productos/cesta/situacion", headers=cabeceras)
    if respuesta.status_code != 200:
        return False
    filas = respuesta.json().get("productos", [])
    # Sin productos no se puede saber; la prueba que lo usa siempre tiene al menos uno.
    return bool(filas) and all("saldo_fisico" in fila for fila in filas)


class TestLoQueEsperaAlCableado:
    """**Estas pruebas no pasan todavía**, y es lo esperado: el coordinador tiene que cablear
    `existencias.py` en las puertas que enseñan «te queda». Están escritas enteras porque son la
    aceptación del encargo, y llevan un mensaje que dice exactamente qué falta."""

    @pytest.fixture
    def el_escenario(self, cliente, cuenta, campana, parcela_grande):
        producto = _producto(cliente, cuenta["cabeceras"])
        _recepcion(
            cliente,
            cuenta["cabeceras"],
            lineas=[
                {
                    "producto_id": producto["id"],
                    "cantidad": 40.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                }
            ],
        )
        articulo = _el_articulo(_existencias(cliente, cuenta["cabeceras"]), "Glifosato 36 SL")
        apunte = _un_tratamiento(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela_grande,
            producto["id"],
            1.0,
            6.0,
        )
        salida = _una_salida(
            cliente,
            cuenta["cabeceras"],
            apunte_tipo="tratamiento",
            apunte_id=apunte["id"],
            lote_id=_el_lote(articulo, "4471-A")["lote_id"],
        )
        assert salida.status_code == 201, salida.text
        return {
            "producto": producto,
            "apunte": apunte,
            "cabeceras": cuenta["cabeceras"],
        }

    def test_la_cesta_sirve_el_saldo_fisico_de_cada_producto(self, cliente, el_escenario):
        """La cesta es **una de las pantallas que enseñan «te queda»**: tiene que traer el saldo físico
        del artículo, no solo su cuenta de facturas menos tratamientos."""
        cesta = _la_cesta(cliente, el_escenario["cabeceras"])
        fila = _fila_de_la_cesta(cesta, el_escenario["producto"]["id"])
        assert _el_cableado_esta_hecho(cliente, el_escenario["cabeceras"]), (
            "falta el cableado: `GET /api/productos/cesta/situacion` tiene que devolver, en cada "
            "producto, `saldo_fisico` (el del artículo enlazado por `ProductoFitosanitario.id` → "
            "`Articulo.producto_id`), `saldo_fisico_conocido`, `situacion` y `motivo_fisico`. "
            "El bloque literal está en docs/T21_EXISTENCIAS.md"
        )
        assert fila["saldo_fisico"] == 34.0
        assert fila["situacion"] == "cuadra"

    def test_la_vista_de_las_existencias_dice_el_mismo_saldo(self, cliente, el_escenario):
        """Las dos pantallas que enseñan «te queda» dicen **el mismo número** para el mismo artículo."""
        cesta = _la_cesta(cliente, el_escenario["cabeceras"])
        fila = _fila_de_la_cesta(cesta, el_escenario["producto"]["id"])
        articulo = _el_articulo(_existencias(cliente, el_escenario["cabeceras"]), "Glifosato 36 SL")
        assert articulo["saldo"] == 34.0
        assert fila.get("saldo_fisico") == articulo["saldo"], (
            "la cesta y el almacén enseñan números distintos del mismo artículo: falta cablear "
            "`existencias.el_saldo_fisico_de_una_cesta` en la puerta de la cesta. Ver "
            "docs/T21_EXISTENCIAS.md"
        )

    def test_la_vista_fisica_trae_lo_que_no_se_puede_relacionar(self, cliente, el_escenario):
        """Y declara lo que queda pendiente: un producto sin artículo **no se convierte en cero**."""
        vista = _la_vista_fisica(cliente, el_escenario["cabeceras"])
        assert "pendientes" in vista
        assert "compra_sin_entrar" in vista


# ==========================================================================
# 6. El informe y el código dicen lo mismo
# ==========================================================================


def _bloque_literal(marca: str, cierre: str) -> dict:
    """Un diccionario escrito en el informe, leído como lo leería Python.

    Si el bloque del informe tiene una errata, revienta **aquí** y no en el ordenador del coordinador.
    """
    texto = EL_INFORME.read_text(encoding="utf-8")
    trozo = texto.split(marca, 1)
    assert len(trozo) == 2, f"el informe no lleva el bloque «{marca}»"
    corte = trozo[1].index(cierre)
    return ast.literal_eval("{" + textwrap.dedent(trozo[1][:corte]) + "}")


class TestElInformeDiceLoMismoQueElCodigo:
    def test_el_informe_lleva_las_frases_de_este_ticket(self):
        """Las cinco frases son **exactamente** las que usa el módulo: si se separan, la pantalla
        enseñaría una frase que nadie ha probado."""
        del_informe = _bloque_literal("MENSAJES.update({", "\n})")
        assert del_informe == existencias.MENSAJES, (
            "el informe y el módulo no dicen las mismas frases: en el informe sobran "
            f"{sorted(set(del_informe) - set(existencias.MENSAJES))} y faltan "
            f"{sorted(set(existencias.MENSAJES) - set(del_informe))}"
        )

    def test_el_informe_lleva_los_bloques_que_el_coordinador_necesita(self):
        """Los cambios compartidos, cada uno con su ancla y su fichero: si falta uno, el que integra se
        queda a medias y las pantallas seguirían sin decir lo mismo.

        No se busca una lista de deseos: se busca **lo que de verdad hay que pegar** en los ficheros que
        no son de este ticket, que es el único motivo por el que este informe existe.
        """
        texto = EL_INFORME.read_text(encoding="utf-8")
        for pieza in (
            # El bloque 3.1: las cinco frases, tal y como se leen con ast.literal_eval.
            "MENSAJES.update({",
            # El bloque 3.2: la función de servicios y su import.
            "def el_saldo_fisico_de_una_cesta(",
            "from . import borradores, catalogos, correcciones, existencias, geo, legal, models, textos",
            # El bloque 3.2, segunda mitad: la puerta de la cesta.
            "saldo_fisico",
            "situacion",
            # El bloque 3.3: la vista física en la puerta del almacén.
            "el_saldo_fisico",
            # Y el enganche por identificador, que es la decisión del ticket.
            "articulo_id",
        ):
            assert pieza in texto, f"al informe le falta el bloque o la línea «{pieza}»"
