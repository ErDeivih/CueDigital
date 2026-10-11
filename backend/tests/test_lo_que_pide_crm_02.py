"""Las tres cifras del encargo de CRM-02 que faltaban por probar en el módulo del banco.

`docs/CONTRATO_IMPLEMENTACION_CRM.md`, en el apartado «El banco por fichero y la conciliación
reversible (CRM-02)», dice que el módulo del banco —el ticket T20, con sus 91 pruebas— cumple siete de
los once criterios de CRM-02 y que **tres están a medias, los tres por falta de prueba con las cifras
del encargo**:

  · un movimiento de **1210** repartido en **400 + 810**;
  · un papel pagado con **dos movimientos distintos**;
  · deshacer **y volver a conciliar**, comparando saldos.

Este fichero escribe esas tres, y solo esas tres. El arnés no se inventa: se importa el del recorrido
por la API de T20 (`tests/test_extractos.py`), que ya sabe dar de alta la cuenta, subir el extracto de
ejemplo y crear un papel nuestro, y se usan los mismos fixtures de `conftest.py`.

Lo que cada una cubre, y lo que se rompería sin ella:

  · **Las cifras.** La prueba que hay hoy reparte un movimiento entre dos papeles con **300,00 y
    405,40** (`TestElRecorridoPorLaApi.test_un_movimiento_puede_saldar_dos_papeles_a_la_vez`), y con
    esas cifras no se distingue un reparto de una casualidad: lo que la cifra del encargo mide es que
    salgan **dos vínculos** —uno por papel y con su importe— y que el movimiento quede **sin resto**.
    Y las cifras 1210/400/810 que sí están escritas en el programa son de **cobros**
    (`tests/test_las_aplicaciones_de_un_cobro.py`), no del banco.
  · **Dos movimientos, no dos veces el mismo.** Lo probado es el **mismo** movimiento conciliado dos
    veces, que ejercita la rama de «sumar a la fila existente» del router (`conciliar_un_movimiento`).
    Un papel pagado con dos movimientos **distintos** tiene que dejar **dos filas**, y el índice único
    es parcial (`anulada = 0`), que es lo que las admite.
  · **La vuelta.** «Deshacer deja todo como estaba» está probado; **volver a conciliar después de
    deshacer, no**. Sin esa vuelta no se comprueba que la pareja (movimiento, papel) quede libre otra
    vez, que la fila deshecha conserve su importe y su rastro, ni que los dos saldos vuelvan
    **exactamente** al mismo número.
"""

from __future__ import annotations

from decimal import Decimal

import test_extractos

from app import extractos, models

# El arnés de T20, tal cual: cuenta, importación, papel nuestro y movimiento.
#
# Se instancia en vez de copiar sus ayudantes a este fichero por el motivo de siempre: dos copias del
# mismo arnés se separan a la primera corrección, y aquí lo que se mide son las cifras del encargo, no
# cómo se monta el escenario. Se importa el **módulo** (y no la clase) para que pytest no recoja otra
# vez, dentro de este fichero, las pruebas del recorrido que ya viven en `test_extractos.py`.
ARNES = test_extractos.TestElRecorridoPorLaApi()


class TestLasCifrasDelEncargoEnElBanco:
    """Las tres cifras del encargo, contra la API del banco y contra lo que queda en la base."""

    # --- ayudantes ---

    def _un_papel_de(self, cliente, cuenta, importe: str) -> dict:
        """Un papel nuestro (entrega y factura emitida) por el importe que se pida."""
        return ARNES._una_factura_nuestra(cliente, cuenta, importe)

    def _el_movimiento_sin_importe_con_cifra(
        self, cliente, cuenta, *, importe: str, signo: str
    ) -> dict:
        """La línea del fichero de ejemplo que **no trae importe**, con la cifra que pide el encargo.

        **Por qué se escribe a mano y no se busca en el fichero.** Los extractos de `tests/datos/` no
        traen ningún movimiento de 1210 € ni de 500 € —el único cobro del extracto principal son
        1.205,40 €—, y no se inventa un fichero de extracto para la ocasión: se usa la puerta que el
        producto tiene para un importe que el banco no dijo (`PUT /api/bancos/movimientos/{id}`), que
        deja el motivo apuntado y marca el movimiento como corregido. Lo que estas pruebas miden es la
        **conciliación**; la lectura del fichero tiene sus propias pruebas con los ficheros de ejemplo.
        """
        movimiento = ARNES._el_movimiento(cliente, cuenta, "SIN IMPORTE")
        assert movimiento["importe"] is None, "esa línea del fichero de ejemplo sí trae importe"
        corregido = cliente.put(
            f"/api/bancos/movimientos/{movimiento['id']}",
            headers=cuenta["cabeceras"],
            json={
                "importe": importe,
                "signo": signo,
                "motivo": "La cifra está en el extracto de papel de la oficina",
            },
        )
        assert corregido.status_code == 200, corregido.text
        assert corregido.json()["corregido"] is True
        return corregido.json()

    def _el_estado_del_movimiento(self, cliente, cuenta, movimiento: dict) -> dict:
        """El movimiento **leído de la base** (por la lista), no lo que contestó la última operación."""
        listado = cliente.get(
            f"/api/bancos/movimientos?cuenta_id={movimiento['cuenta_id']}",
            headers=cuenta["cabeceras"],
        ).json()["items"]
        return next(item for item in listado if item["id"] == movimiento["id"])

    def _el_pendiente_de(self, cliente, cuenta, papel: dict) -> dict | None:
        """Lo que le falta a un papel, por la puerta del banco. `None` si ya no debe nada."""
        pendientes = cliente.get("/api/bancos/pendientes", headers=cuenta["cabeceras"]).json()
        return next(
            (
                pendiente
                for pendiente in pendientes
                if pendiente["clase"] == extractos.FACTURA_EMITIDA
                and pendiente["documento_id"] == papel["id"]
            ),
            None,
        )

    def _las_filas_de(
        self, db_sesion, movimiento: dict, papel: dict
    ) -> list[models.ConciliacionDeMovimiento]:
        """Los vínculos guardados de una pareja (movimiento, papel), deshechos incluidos.

        `expire_all` **no es un adorno**: la sesión de la prueba guarda en memoria lo que ya ha leído, y
        el que escribe de verdad es el de la API (otra sesión). Sin tirar esa copia, la segunda lectura
        devuelve la fila con los valores de antes y una fila deshecha se leería como viva —que es lo que
        pasó al escribir esta prueba, y es justo el dato que hay que comprobar aquí—.
        """
        db_sesion.expire_all()
        return (
            db_sesion.query(models.ConciliacionDeMovimiento)
            .filter_by(
                movimiento_id=movimiento["id"],
                clase=extractos.FACTURA_EMITIDA,
                documento_id=papel["id"],
            )
            .all()
        )

    def _apuntar(self, cliente, cuenta, movimiento: dict, imputaciones: list[dict]) -> dict:
        respuesta = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/conciliar",
            headers=cuenta["cabeceras"],
            json={"imputaciones": imputaciones},
        )
        assert respuesta.status_code == 200, respuesta.text
        return respuesta.json()

    def _una_imputacion(self, papel: dict, importe: str) -> dict:
        return {
            "clase": extractos.FACTURA_EMITIDA,
            "documento_id": papel["id"],
            "importe": importe,
        }

    # --- las tres cifras ---

    def test_un_movimiento_de_1210_se_reparte_entre_dos_papeles_de_400_y_810(
        self, cliente, cuenta, db_sesion
    ):
        """Un ingreso de 1210,00 contra dos papeles nuestros: 400,00 a uno y 810,00 al otro.

        **Por qué existe.** Es la primera cifra del encargo, y la que separa un **reparto** de una
        **suma**: dos vínculos, cada uno con su papel y su importe, y el movimiento **sin resto**
        (1210,00 apuntados de 1210,00 que entraron). Sin esta prueba, un reparto que se quedara en los
        400 del primer papel —o que apuntara los 1210 enteros al primero y dejara al segundo
        esperando— pasaría desapercibido: nada de lo que hay hoy comprueba que el movimiento quede a
        cero con estas cifras.
        """
        cuenta_bancaria = ARNES._crear_cuenta(cliente, cuenta)
        ARNES._importar(cliente, cuenta, cuenta_bancaria["id"])
        de_400 = self._un_papel_de(cliente, cuenta, "400.00")
        de_810 = self._un_papel_de(cliente, cuenta, "810.00")
        movimiento = self._el_movimiento_sin_importe_con_cifra(
            cliente, cuenta, importe="1210.00", signo=extractos.ENTRA
        )

        # Los dos papeles esperan lo suyo, y enteros.
        assert self._el_pendiente_de(cliente, cuenta, de_400)["pendiente"] == "400.00"
        assert self._el_pendiente_de(cliente, cuenta, de_810)["pendiente"] == "810.00"

        hecha = self._apuntar(
            cliente,
            cuenta,
            movimiento,
            [self._una_imputacion(de_400, "400.00"), self._una_imputacion(de_810, "810.00")],
        )

        # Un vínculo por papel, con su importe, y la suma es el movimiento entero.
        assert {(h["documento_id"], Decimal(h["importe"])) for h in hecha["conciliaciones"]} == {
            (de_400["id"], Decimal("400.00")),
            (de_810["id"], Decimal("810.00")),
        }
        assert sum(
            (Decimal(h["importe"]) for h in hecha["conciliaciones"]), Decimal("0")
        ) == Decimal("1210.00")
        assert Decimal(hecha["movimiento"]["imputado"]) == Decimal("1210.00")
        assert hecha["movimiento"]["estado"] == extractos.CONCILIADO
        assert hecha["movimiento"]["por_conciliar"] == "0.00", (
            "el movimiento no puede quedarse con resto: 400 + 810 son los 1210 que entraron"
        )

        # **En la base de datos**, no solo en la respuesta: dos filas, una por papel y con su importe.
        filas = (
            db_sesion.query(models.ConciliacionDeMovimiento)
            .filter_by(movimiento_id=movimiento["id"])
            .all()
        )
        assert len(filas) == 2, f"el reparto tiene que dejar dos filas, y ha dejado {len(filas)}"
        assert sorted(fila.importe for fila in filas) == [Decimal("400.00"), Decimal("810.00")]
        assert {fila.documento_id for fila in filas} == {de_400["id"], de_810["id"]}
        assert all(fila.anulada is False for fila in filas)
        assert Decimal(hecha["movimiento"]["importe"]) == sum(
            (fila.importe for fila in filas), Decimal("0")
        ), "lo apuntado y lo que dice el banco tienen que ser el mismo número"

        # Y los dos papeles quedan saldados: un papel que ya no debe nada no es un pendiente.
        assert self._el_pendiente_de(cliente, cuenta, de_400) is None
        assert self._el_pendiente_de(cliente, cuenta, de_810) is None

    def test_un_papel_pagado_con_dos_movimientos_distintos_del_extracto(
        self, cliente, cuenta, db_sesion
    ):
        """Una factura de 1205,40 cobrada con dos movimientos del banco: 500,00 y 705,40.

        **Por qué existe.** Es la segunda cifra del encargo. Lo que hay probado hoy es el **mismo**
        movimiento conciliado dos veces —500 y luego 705,40—, que ejercita otra rama del router: la de
        **sumar a la fila que ya estaba**. Con dos movimientos distintos lo que tiene que haber son
        **dos filas**, cada una con su movimiento y su importe, y el papel bajando con las dos. Sin
        esta prueba, un programa que solo supiera apuntar el mismo movimiento dos veces —y que
        perdiera el segundo pago, o lo sumara en la fila del primero— daría el papel por cobrado sin
        haberlo estado.
        """
        cuenta_bancaria = ARNES._crear_cuenta(cliente, cuenta)
        ARNES._importar(cliente, cuenta, cuenta_bancaria["id"])
        papel = self._un_papel_de(cliente, cuenta, "1205.40")
        primero = self._el_movimiento_sin_importe_con_cifra(
            cliente, cuenta, importe="500.00", signo=extractos.ENTRA
        )
        segundo = ARNES._el_movimiento(cliente, cuenta, "COOPERATIVA")
        assert Decimal(segundo["importe"]) == Decimal("1205.40")
        assert primero["id"] != segundo["id"]

        assert self._el_pendiente_de(cliente, cuenta, papel)["pendiente"] == "1205.40"

        # Primer movimiento: los 500,00 enteros, y con eso el movimiento queda apuntado del todo.
        una = self._apuntar(cliente, cuenta, primero, [self._una_imputacion(papel, "500.00")])
        assert Decimal(una["movimiento"]["imputado"]) == Decimal("500.00")
        assert una["movimiento"]["por_conciliar"] == "0.00"
        assert una["movimiento"]["estado"] == extractos.CONCILIADO
        # El papel **baja con el primero**: le faltan los 705,40 que quedan por cobrar.
        assert self._el_pendiente_de(cliente, cuenta, papel)["pendiente"] == "705.40"

        # Segundo movimiento, **distinto del primero**: los 705,40 que faltaban.
        otra = self._apuntar(cliente, cuenta, segundo, [self._una_imputacion(papel, "705.40")])
        assert Decimal(otra["movimiento"]["imputado"]) == Decimal("705.40")
        # Del segundo movimiento queda la otra mitad sin apuntar, y se dice: no se cuela como cobrado.
        assert otra["movimiento"]["por_conciliar"] == "500.00"
        assert otra["movimiento"]["estado"] == extractos.CONCILIADO_EN_PARTE
        # Y el papel **baja con el segundo** hasta no deber nada.
        assert self._el_pendiente_de(cliente, cuenta, papel) is None

        # **Dos filas, y de dos movimientos distintos.** Es lo que distingue esto de «el mismo
        # movimiento dos veces», donde la fila sería una sola con su importe sumado.
        filas = (
            db_sesion.query(models.ConciliacionDeMovimiento)
            .filter_by(clase=extractos.FACTURA_EMITIDA, documento_id=papel["id"])
            .all()
        )
        assert len(filas) == 2, f"dos pagos distintos son dos filas, y hay {len(filas)}"
        assert {fila.movimiento_id for fila in filas} == {primero["id"], segundo["id"]}
        assert sorted(fila.importe for fila in filas) == [Decimal("500.00"), Decimal("705.40")]
        assert sum((fila.importe for fila in filas), Decimal("0")) == Decimal("1205.40")
        assert all(fila.anulada is False for fila in filas)

    def test_desconciliar_y_volver_a_conciliar_deja_los_mismos_saldos(
        self, cliente, cuenta, db_sesion
    ):
        """Se concilia, se deshace y **se vuelve a conciliar**: los dos saldos, al mismo número.

        **Por qué existe.** Es la tercera cifra del encargo, y la que faltaba de verdad: «deshacer
        deja todo como estaba» está probado, pero **la vuelta no**. Sin ella no se comprueba que la
        pareja (movimiento, papel) quede libre otra vez, que la fila deshecha conserve su importe y su
        rastro —el índice único es parcial (`anulada = 0`) y eso es lo que lo permite—, ni que el
        segundo apunte deje **exactamente** los mismos números que el primero. Si al deshacer se
        perdiera el importe del vínculo, o si la vuelta dejara el papel a medias, aquí se vería.

        Los dos números se leen **de la base**, por las dos puertas del banco (lo que le falta al papel
        y lo que le queda al movimiento), no de la respuesta de la operación: es el estado que verá el
        agricultor la próxima vez que abra la pantalla.
        """
        cuenta_bancaria = ARNES._crear_cuenta(cliente, cuenta)
        ARNES._importar(cliente, cuenta, cuenta_bancaria["id"])
        papel = self._un_papel_de(cliente, cuenta, "1205.40")
        movimiento = ARNES._el_movimiento(cliente, cuenta, "COOPERATIVA")

        def los_dos_saldos() -> tuple[str, str | None]:
            """El pendiente del papel y lo que le queda al movimiento, tal y como están guardados."""
            return (
                self._el_pendiente_de(cliente, cuenta, papel)["pendiente"],
                self._el_estado_del_movimiento(cliente, cuenta, movimiento)["por_conciliar"],
            )

        # Antes de tocar nada: el papel entero y el movimiento entero.
        assert los_dos_saldos() == ("1205.40", "1205.40")

        # Se concilia medio pago.
        self._apuntar(cliente, cuenta, movimiento, [self._una_imputacion(papel, "500.00")])
        al_conciliar = los_dos_saldos()
        assert al_conciliar == ("705.40", "705.40")
        vivas = [fila for fila in self._las_filas_de(db_sesion, movimiento, papel) if not fila.anulada]
        assert len(vivas) == 1
        assert vivas[0].importe == Decimal("500.00")

        # Se deshace: el pendiente **vuelve** al valor de antes, y el movimiento también.
        deshecho = cliente.post(
            f"/api/bancos/movimientos/{movimiento['id']}/desconciliar",
            headers=cuenta["cabeceras"],
            json={},
        )
        assert deshecho.status_code == 200, deshecho.text
        assert str(deshecho.json()["movimiento"]["imputado"]) == "0.00"
        assert los_dos_saldos() == ("1205.40", "1205.40")
        # Y el vínculo deshecho no se borra: se queda con su importe y su rastro.
        deshechas = [fila for fila in self._las_filas_de(db_sesion, movimiento, papel) if fila.anulada]
        assert len(deshechas) == 1
        assert deshechas[0].importe == Decimal("500.00")
        assert deshechas[0].deshecha_en is not None
        assert deshechas[0].deshecha_por_usuario_id is not None

        # Y se vuelve a conciliar, con el mismo importe.
        self._apuntar(cliente, cuenta, movimiento, [self._una_imputacion(papel, "500.00")])
        assert los_dos_saldos() == al_conciliar, (
            "la vuelta tiene que dejar los dos saldos exactamente como la primera vez: "
            f"{al_conciliar} y no {los_dos_saldos()}"
        )

        # La pareja tiene otra vez **una** fila viva con su importe. La deshecha se conserva —y por eso
        # aquí hay dos filas y no una reutilizada—: el índice único es parcial (`anulada = 0`), así que
        # deshacer deja la pareja libre y la vuelta escribe un vínculo nuevo, sin tocar el rastro.
        todas = self._las_filas_de(db_sesion, movimiento, papel)
        assert len(todas) == 2, f"la deshecha se conserva y la vuelta escribe otra: hay {len(todas)}"
        vivas_otra_vez = [fila for fila in todas if not fila.anulada]
        assert len(vivas_otra_vez) == 1
        assert vivas_otra_vez[0].importe == Decimal("500.00"), (
            "la fila viva de la pareja tiene que recuperar el importe que se apuntó"
        )
