"""Lo que se vende: la cosecha comercializada y la venta directa.

La app oficial lo tiene en «Otras Actividades: Cosecha Comercializada», y el contenido
mínimo del CUE la llama «Cosecha comercializada y/o venta directa» (bloque 3 de los que se
recopilan «a nivel de Explotación»). Es la sección que cierra el cuaderno por arriba:

    no es lo que recoges, es lo que sale de la finca.

Lo que la norma pide, y este test comprueba uno por uno:

| Campo del contenido mínimo | Aquí |
|---|---|
| 1. Fecha (intervalo de tiempo)* | `fecha` + `fecha_fin` |
| 2. Producto vegetal (según catálogo)* | `producto` |
| 3. Cantidad de producto vegetal (kg o ud)* | `cantidad` + `unidad` |

Y distingue **dos clases de venta**, que es lo que separa `tipo`: la venta de cosecha
comercializada y la venta directa.

Dos cosas que este test deja escritas porque son decisiones, no olvidos:

* **No hay precio ni importe.** Lo que la norma pide de esta sección es qué, cuánto y cuándo.
  La facturación está en otra parte (Verifactu, factura electrónica) y empezar por el dinero
  sería empezar por el final.
* **Comparar lo vendido con lo cosechado avisa, y no bloquea.** El agricultor puede estar
  vendiendo de la cosecha del año pasado, y negarle el apunte por eso sería peor que el
  error que se quiere evitar.
"""

from __future__ import annotations

import pytest

from app import catalogos, textos


class TestLoQuePideLaNorma:
    def test_las_dos_clases_de_venta_que_separan_la_norma(self):
        assert set(catalogos.TIPOS_VENTA) == {"comercializada", "venta_directa"}

    def test_cada_clase_tiene_su_nombre_para_el_agricultor(self):
        for tipo in catalogos.TIPOS_VENTA:
            assert catalogos.ETIQUETA_VENTA[tipo]
            assert catalogos.ETIQUETA_VENTA_CORTA[tipo]
            # Y se lee como se lo diría él, no como lo dice la norma.
            assert "cosecha comercializada" not in catalogos.ETIQUETA_VENTA[tipo].lower()

    def test_se_puede_apuntar_una_venta_completa(self, crear_venta):
        venta = crear_venta()
        assert venta["producto"] == "Trigo blando"
        assert venta["cantidad"] == 42000.0
        assert venta["unidad"] == "kg"
        assert venta["tipo"] == "comercializada"
        assert venta["fecha"] == "2026-07-10"

    def test_una_venta_directa_es_otra_clase_y_se_puede_listar_aparte(
        self, crear_venta, cliente, cuenta
    ):
        crear_venta(tipo="venta_directa", producto="Lechuga", cantidad=3000, unidad="ud")
        solo_directas = cliente.get(
            "/api/ventas?tipo=venta_directa", headers=cuenta["cabeceras"]
        ).json()
        assert len(solo_directas) == 1
        assert solo_directas[0]["producto"] == "Lechuga"
        comercializadas = cliente.get(
            "/api/ventas?tipo=comercializada", headers=cuenta["cabeceras"]
        ).json()
        assert comercializadas == []

    def test_la_fecha_puede_ser_un_intervalo(self, crear_venta):
        """La norma la llama «fecha (intervalo de tiempo)»: una partida sale en varios viajes."""
        venta = crear_venta(fecha="2026-07-10", fecha_fin="2026-07-14")
        assert venta["fecha"] == "2026-07-10"
        assert venta["fecha_fin"] == "2026-07-14"

    def test_la_venta_de_un_solo_dia_no_necesita_fecha_fin(self, crear_venta):
        venta = crear_venta(fecha="2026-07-10", fecha_fin=None)
        assert venta["fecha_fin"] is None

    def test_las_unidades_son_las_que_nombra_la_norma_mas_la_tonelada(self):
        assert set(catalogos.UNIDADES_VENTA) == {"kg", "t", "ud"}

    def test_la_norma_nombra_los_kilos_y_las_unidades(self):
        etiquetas = {datos["etiqueta"] for datos in catalogos.UNIDADES_VENTA.values()}
        assert "kilos" in etiquetas
        assert "unidades" in etiquetas

    def test_se_puede_apuntar_en_toneladas_porque_asi_se_vende_el_grano(self, crear_venta):
        venta = crear_venta(cantidad=42.0, unidad="t")
        assert venta["kilos"] == 42000.0
        assert venta["texto_cantidad"] == "42,00 t"

    def test_se_guarda_el_numero_tal_cual_y_los_kilos_se_calculan(self, crear_venta):
        """No se guardan dos veces: si un día cambia el factor, el apunte histórico no miente."""
        venta = crear_venta(cantidad=3.0, unidad="t")
        assert venta["cantidad"] == 3.0
        assert venta["unidad"] == "t"
        assert venta["kilos"] == 3000.0


class TestNadaSeInventa:
    def test_las_unidades_no_se_pueden_convertir_a_kilos_cuando_no_son_peso(self):
        """Una unidad de lechugas no pesa lo que dice el número."""
        assert catalogos.kilos_de_una_venta(3000, "ud") is None
        assert catalogos.kilos_de_una_venta(3, "t") == 3000.0
        assert catalogos.kilos_de_una_venta(500, "kg") == 500.0

    def test_una_venta_en_unidades_no_entra_en_el_total_de_kilos(
        self, cliente, cuenta, crear_venta, campana
    ):
        """Es mejor un total que significa algo que uno que mezcla peras con manzanas."""
        crear_venta(cantidad=1000, unidad="kg")
        crear_venta(cantidad=3000, unidad="ud", producto="Lechuga")
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["vendido_kg"] == 1000.0
        assert informe["cuantas"] == 2, "pero las dos ventas salen en el informe"
        assert informe["hay_unidades"] is True

    def test_el_informe_avisa_de_que_hay_ventas_en_unidades(
        self, cliente, cuenta, crear_venta
    ):
        crear_venta(cantidad=3000, unidad="ud", producto="Lechuga")
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["hay_unidades"] is True

    def test_el_importe_se_puede_no_saber_y_entonces_no_es_cero(self, cliente, cuenta, venta):
        """El dinero del T12: la entrega trae importe, y **sin precio el importe es «no se sabe»**.

        ESTA PRUEBA DECÍA «no hay precio ni importe», Y SE CAMBIA CON EL MOTIVO ESCRITO. Aquella
        afirmación era verdad y era una decisión: mientras el programa no llevaba cuentas, meter un
        precio a medias habría sido empezar por el final. **El T12 es exactamente el ticket que las
        trae** («Entregas/ventas, importes decimales, cobros parciales; A06/A08» del contrato), así
        que lo que había que cambiar no es el comportamiento sino lo que se comprueba. Y lo que se
        comprueba ahora es lo que de aquella decisión sigue siendo sagrado, que es el caso A08 del
        contrato: **una venta sin precio tiene el importe pendiente, no un ingreso de cero euros**.
        Las tres afirmaciones de abajo son esa regla, una por una.
        """
        assert "importe" in venta, "el T12 añade el importe a la entrega"
        # El A08: sin precio, el importe no se sabe. `None` y no `0.0`: un cero sería un ingreso de
        # cero euros en las cuentas del año, que es falso, y es lo que el contrato prohíbe.
        assert venta["importe"] is None
        assert venta["precio_unitario"] is None
        assert venta["importe_total"] is None
        # Y con el hueco dicho, no escondido: el estado lo dice y la cifra que se enseña está vacía.
        assert venta["estado"] == "sin_importe"
        assert venta["texto_importe"] == ""
        # Sin factura todavía, tampoco hay nada que cobrar: el pendiente no se inventa.
        assert venta["pendiente"] is None

    def test_la_pantalla_dice_donde_esta_el_dinero_y_que_la_factura_no_es_oficial(
        self, cliente, cuenta
    ):
        """El aviso de la pantalla cambia con el T12, y la segunda mitad no puede desaparecer nunca.

        El texto viejo decía «aquí no se apunta el precio ni lo que te han pagado», y desde el T12 es
        mentira: dejarlo sería decirle al agricultor que no puede hacer algo que sí puede. El nuevo
        dice dónde está el dinero **y** que la factura que se hace desde esta pantalla es su cuenta de
        gestión, no un documento con validez oficial. Esa segunda mitad es una obligación del
        contrato (§4, S12: la emisión fiscal completa «requiere especificación normativa propia antes
        de activarse como tal»), así que se comprueba que está.
        """
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        aviso = datos["venta"]["dinero_fuera"].lower()
        assert "no se apunta el precio" not in aviso, "el aviso viejo ya no es verdad"
        assert "lo que te han pagado" in aviso
        assert "no es un documento con validez oficial" in aviso

    def test_el_producto_no_se_elige_de_una_lista_inventada(self, cliente, cuenta):
        """El catálogo oficial dice «según catálogo» y no lo trae: no se inventa."""
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        # Lo que sí se sirve son las clases de venta y las unidades, que la norma sí nombra.
        assert {t["valor"] for t in datos["tipos_venta"]} == {"comercializada", "venta_directa"}
        assert {u["valor"] for u in datos["unidades_venta"]} == {"kg", "t", "ud"}
        assert "productos_vegetales" not in datos, "no hay catálogo de productos inventado"


class TestValidaciones:
    def _validar(self, cliente, cuenta, campana, **cambios):
        cuerpo = {
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 1000.0,
            "unidad": "kg",
            "comprador": "La cooperativa",
        }
        cuerpo.update(cambios)
        respuesta = cliente.post("/api/ventas/validar", headers=cuenta["cabeceras"], json=cuerpo)
        assert respuesta.status_code == 200, respuesta.text
        return {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}

    def test_sin_producto_no_se_puede_guardar(self, cliente, cuenta, campana):
        avisos = self._validar(cliente, cuenta, campana, producto="")
        assert avisos["C1_sin_producto"]["bloquea"]

    def test_sin_cantidad_no_se_puede_guardar(self, cliente, cuenta, campana):
        avisos = self._validar(cliente, cuenta, campana, cantidad=None)
        assert avisos["C2_sin_cantidad"]["bloquea"]

    def test_una_cantidad_de_cero_no_vale(self, cliente, cuenta, campana):
        avisos = self._validar(cliente, cuenta, campana, cantidad=0)
        assert avisos["C2_sin_cantidad"]["bloquea"]

    def test_las_dos_fechas_al_reves_no_se_pueden_guardar(self, cliente, cuenta, campana):
        avisos = self._validar(
            cliente, cuenta, campana, fecha="2026-07-14", fecha_fin="2026-07-10"
        )
        assert avisos["C4_fechas_cruzadas"]["bloquea"]

    def test_sin_comprador_se_puede_guardar_pero_se_avisa(self, cliente, cuenta, campana):
        """El agricultor vende muchas veces sin tener el papel delante."""
        avisos = self._validar(cliente, cuenta, campana, comprador="")
        assert "C5_sin_comprador" in avisos
        assert not avisos["C5_sin_comprador"]["bloquea"]

    def test_ninguna_validacion_deja_al_agricultor_sin_salida(self, cliente, cuenta, campana):
        avisos = self._validar(cliente, cuenta, campana, producto="", cantidad=None)
        for aviso in avisos.values():
            if aviso["bloquea"]:
                assert aviso["mensaje"].strip()

    def test_se_puede_apuntar_una_venta_sin_nada_mas_que_lo_obligatorio(self, cliente, cuenta, campana):
        """El mínimo de la norma: producto, cantidad y fecha. Lo demás es para la trazabilidad."""
        respuesta = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Cebada",
                "cantidad": 5000.0,
            },
        )
        assert respuesta.status_code == 201, respuesta.text


class TestCuadraConLaCosecha:
    """Lo que de verdad sirve de esta sección: que el cuaderno cuadre."""

    def _cosechar(self, cliente, cuenta, parcela, campana, cantidad):
        respuesta = cliente.post(
            "/api/cosecha",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-01",
                "parcela_id": parcela["id"],
                "cantidad_kg": cantidad,
            },
        )
        assert respuesta.status_code == 201, respuesta.text

    def test_vender_sin_haber_apuntado_la_cosecha_avisa(self, cliente, cuenta, campana, parcela):
        respuesta = cliente.post(
            "/api/ventas/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "comprador": "La cooperativa",
            },
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "C6_venta_sin_cosecha" in avisos
        assert not avisos["C6_venta_sin_cosecha"]["bloquea"], "avisar, no bloquear"

    def test_vender_mas_de_lo_cosechado_avisa_con_los_dos_numeros(
        self, cliente, cuenta, campana, parcela
    ):
        self._cosechar(cliente, cuenta, parcela, campana, 30000)
        respuesta = cliente.post(
            "/api/ventas/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 42000.0,
                "comprador": "La cooperativa",
            },
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "C7_mas_de_lo_cosechado" in avisos
        assert "42.000" in avisos["C7_mas_de_lo_cosechado"]["mensaje"]
        assert "30.000" in avisos["C7_mas_de_lo_cosechado"]["mensaje"]
        assert not avisos["C7_mas_de_lo_cosechado"]["bloquea"]

    def test_vender_menos_de_lo_cosechado_no_avisa(self, cliente, cuenta, campana, parcela):
        self._cosechar(cliente, cuenta, parcela, campana, 50000)
        respuesta = cliente.post(
            "/api/ventas/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 42000.0,
                "comprador": "La cooperativa",
            },
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "C7_mas_de_lo_cosechado" not in codigos
        assert "C6_venta_sin_cosecha" not in codigos

    def test_el_aviso_cuenta_las_ventas_que_ya_habia(self, cliente, cuenta, campana, parcela):
        """Con dos ventas que juntas pasan de la cosecha, el aviso sale en la segunda."""
        self._cosechar(cliente, cuenta, parcela, campana, 30000)
        cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-08",
                "producto": "Trigo blando",
                "cantidad": 20000.0,
                "comprador": "La cooperativa",
            },
        )
        respuesta = cliente.post(
            "/api/ventas/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 20000.0,
                "comprador": "La cooperativa",
            },
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "C7_mas_de_lo_cosechado" in codigos, "20.000 + 20.000 pasa de 30.000"

    def test_al_corregir_una_venta_no_se_cuenta_a_si_misma(self, cliente, cuenta, campana, parcela):
        """Sin esto, el aviso saltaría siempre al corregir: la venta se compararía consigo misma."""
        self._cosechar(cliente, cuenta, parcela, campana, 50000)
        creada = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-08",
                "producto": "Trigo blando",
                "cantidad": 42000.0,
                "comprador": "La cooperativa",
            },
        ).json()
        respuesta = cliente.put(
            f"/api/ventas/{creada['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-08",
                "producto": "Trigo blando",
                "cantidad": 42000.0,
                "comprador": "La cooperativa",
            },
        )
        assert respuesta.status_code == 200, respuesta.text

    def test_lo_que_se_anula_no_cuenta(self, cliente, cuenta, campana, parcela):
        """Ni la cosecha anulada ni la venta anulada: lo que se anuló no pasó."""
        self._cosechar(cliente, cuenta, parcela, campana, 30000)
        creada = cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-08",
                "producto": "Trigo blando",
                "cantidad": 25000.0,
                "comprador": "La cooperativa",
            },
        ).json()
        cliente.post(
            f"/api/ventas/{creada['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de albarán"},
        )
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantas"] == 0
        assert informe["vendido_kg"] == 0.0

    def test_el_resumen_dice_lo_que_queda_por_vender(self, cliente, cuenta, campana, parcela):
        self._cosechar(cliente, cuenta, parcela, campana, 50000)
        cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 20000.0,
                "comprador": "La cooperativa",
            },
        )
        resumen = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        assert resumen["cuadra"] is True
        quedan = [fila for fila in resumen["filas"] if "queda" in fila["que"].lower()]
        assert quedan[0]["kilos"] == 30000.0


class TestElInforme:
    def test_el_informe_lleva_las_ventas_del_ano(self, cliente, cuenta, venta):
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantas"] == 1
        fila = informe["filas"][0]
        assert fila["producto"] == "Trigo blando"
        assert fila["cantidad"] == "42.000,00 kg"
        assert fila["comprador"] == "Cooperativa Agrícola de Peñaranda"
        assert fila["donde"] == "El Prado"
        assert fila["tipo"] == "Venta a comprador"

    def test_el_informe_dice_que_no_hay_nada_cuando_no_hay_nada(self, cliente, cuenta):
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantas"] == 0
        assert informe["vacio"] == textos.VENTA["informe_sin_nada"]

    def test_el_informe_no_se_confunde_con_un_identificador(self, cliente, cuenta):
        assert cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).status_code == 200

    def test_el_resumen_tampoco_se_confunde_con_un_identificador(self, cliente, cuenta):
        """`/ventas/resumen` va antes que `/ventas/{id}`, igual que el informe."""
        assert cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).status_code == 200

    def test_una_venta_anulada_no_sale_en_el_informe(self, cliente, cuenta, venta):
        cliente.post(
            f"/api/ventas/{venta['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba mal apuntada"},
        )
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantas"] == 0

    def test_el_informe_va_ordenado_por_fecha(self, cliente, cuenta, crear_venta):
        crear_venta(fecha="2026-08-01", producto="Cebada")
        crear_venta(fecha="2026-06-01", producto="Trigo blando")
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert [fila["producto"] for fila in informe["filas"]] == ["Trigo blando", "Cebada"]


class TestAnularYCorregir:
    def test_anular_no_borra_y_guarda_el_motivo(self, cliente, cuenta, venta):
        respuesta = cliente.post(
            f"/api/ventas/{venta['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Era de otra campaña"},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["anulado"] is True
        assert cliente.get(
            f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"]
        ).status_code == 200

    def test_anular_sin_motivo_no_se_acepta(self, cliente, cuenta, venta):
        respuesta = cliente.post(
            f"/api/ventas/{venta['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": ""},
        )
        assert respuesta.status_code == 422

    def test_una_venta_anulada_no_sale_en_la_lista(self, cliente, cuenta, venta):
        cliente.post(
            f"/api/ventas/{venta['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba mal"},
        )
        assert cliente.get("/api/ventas", headers=cuenta["cabeceras"]).json() == []

    def test_se_puede_corregir_la_cantidad_mal_copiada(self, cliente, cuenta, venta):
        respuesta = cliente.put(
            f"/api/ventas/{venta['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": venta["campana_id"],
                "fecha": venta["fecha"],
                "producto": venta["producto"],
                "cantidad": 41000.0,
                "unidad": "kg",
                "comprador": venta["comprador"],
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["cantidad"] == 41000.0

    def test_corregir_deja_rastro(self, cliente, cuenta, venta):
        respuesta = cliente.put(
            f"/api/ventas/{venta['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": venta["campana_id"],
                "fecha": venta["fecha"],
                "producto": "Cebada",
                "cantidad": 1000.0,
                "unidad": "kg",
                "comprador": venta["comprador"],
            },
        )
        assert respuesta.json()["producto"] == "Cebada"
        visto = cliente.get(f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"]).json()
        assert visto["id"] == venta["id"]


class TestAislamiento:
    def test_cada_finca_ve_sus_ventas(self, cliente, cuenta, venta, crear_cuenta):
        otro = crear_cuenta("otro@ejemplo.test")
        assert cliente.get("/api/ventas", headers=otro["cabeceras"]).json() == []

    def test_una_venta_de_otra_finca_no_se_puede_leer(self, cliente, cuenta, venta, crear_cuenta):
        otro = crear_cuenta("otro@ejemplo.test")
        assert cliente.get(
            f"/api/ventas/{venta['id']}", headers=otro["cabeceras"]
        ).status_code == 404

    def test_no_se_puede_vender_con_la_parcela_de_otro(
        self, cliente, cuenta, parcela, crear_cuenta
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        campana_otro = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/ventas",
            headers=otro["cabeceras"],
            json={
                "campana_id": campana_otro["id"],
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "parcela_id": parcela["id"],
            },
        )
        assert respuesta.status_code == 404

    def test_la_cosecha_de_otra_finca_no_cuenta_en_mi_cuadre(
        self, cliente, cuenta, campana, parcela, crear_cuenta
    ):
        """El aislamiento también vale para los totales, no solo para los listados."""
        otro = crear_cuenta("otro@ejemplo.test")
        cliente.post(
            "/api/cosecha",
            headers=otro["cabeceras"],
            json={
                "campana_id": cliente.get(
                    "/api/campanas/actual", headers=otro["cabeceras"]
                ).json()["id"],
                "fecha": "2026-07-01",
                "parcela_id": cliente.post(
                    "/api/parcelas",
                    headers=otro["cabeceras"],
                    json={"alias": "La Vega", "superficie_ha": 1.0, "sistema": "secano"},
                ).json()["id"],
                "cantidad_kg": 90000,
            },
        )
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cosechado_kg"] == 0.0


class TestElCuadernoLoLleva:
    def test_el_csv_lleva_lo_que_se_ha_vendido(self, cliente, cuenta, venta):
        texto = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"]).content.decode(
            "utf-8-sig"
        )
        assert "COSECHA COMERCIALIZADA" in texto
        assert "Trigo blando" in texto
        assert "Cooperativa Agrícola de Peñaranda" in texto
        assert "ALB-2026-118" in texto

    def test_el_csv_dice_que_no_hay_ventas_si_no_las_hay(self, cliente, cuenta):
        texto = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"]).content.decode(
            "utf-8-sig"
        )
        assert "COSECHA COMERCIALIZADA" in texto
        assert textos.VENTA["informe_sin_nada"] in texto

    def test_el_pdf_lleva_lo_que_se_ha_vendido(self, cliente, cuenta, venta):
        respuesta = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        assert respuesta.content.startswith(b"%PDF")
        assert len(respuesta.content) > 1500


class TestElVocabulario:
    def test_la_interfaz_trae_las_clases_de_venta(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert len(datos["tipos_venta"]) == 2
        assert datos["tipos_venta"][0]["valor"] == "comercializada"

    def test_la_interfaz_trae_las_unidades_de_venta(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        unidades = {u["valor"]: u for u in datos["unidades_venta"]}
        assert unidades["kg"]["texto"] == "kilos"
        assert unidades["t"]["texto"] == "toneladas"
        assert unidades["ud"]["corto"] == "ud"

    def test_la_interfaz_trae_los_textos_de_la_pantalla(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        assert datos["venta"]["titulo"] == "Lo que he vendido"
        assert datos["venta"]["anadir"] == "APUNTAR UNA VENTA"

    def test_lo_que_se_pregunta_es_una_pregunta(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz", headers=cuenta["cabeceras"]).json()
        for campo in (
            "venta.tipo",
            "venta.producto",
            "venta.cantidad",
            "venta.unidad",
            "venta.fecha",
            "venta.comprador",
        ):
            etiqueta = datos["etiquetas"][campo]
            assert etiqueta["pregunta"].endswith("?"), campo
            assert etiqueta["pista"], campo

    def test_todo_el_texto_nuevo_esta_en_el_fichero_de_textos(self):
        visibles = textos.textos_visibles()
        assert textos.VENTA["titulo"] in visibles
        assert textos.VENTA["dinero_fuera"] in visibles
        assert textos.MENSAJES["C1_sin_producto"] in visibles
        assert textos.MENSAJES["C7_mas_de_lo_cosechado"] in visibles
        assert textos.PORQUE["por_que_vender"] in visibles

    def test_la_ayuda_trae_el_porque_de_vender(self, cliente):
        ayuda = cliente.get("/api/ayuda").json()
        assert "por_que_vender" in ayuda["porques"]


class TestLosCalculos:
    def test_la_clave_de_producto_junta_las_formas_de_escribirlo(self):
        """«Trigo blando», «TRIGO BLANDO» y «trigo  blando» son lo mismo."""
        from app import servicios

        assert servicios.clave_de_producto("Trigo blando") == servicios.clave_de_producto(
            "  TRIGO   BLANDO  "
        )
        assert servicios.clave_de_producto("Trígo blándo") == "trigo blando"

    def test_sin_nombre_no_hay_clave(self):
        from app import servicios

        assert servicios.clave_de_producto(None) == ""
        assert servicios.clave_de_producto("") == ""

    def test_un_saco_de_kilos_y_una_tonelada_suman_igual(self, cliente, cuenta, crear_venta):
        crear_venta(cantidad=1.0, unidad="t")
        crear_venta(cantidad=500.0, unidad="kg")
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["vendido_kg"] == 1500.0

    def test_el_texto_de_la_cantidad_usa_la_coma_espanola(self, crear_venta):
        venta = crear_venta(cantidad=1234.5, unidad="kg")
        assert venta["texto_cantidad"] == "1.234,50 kg"


@pytest.mark.parametrize("tipo", list(catalogos.TIPOS_VENTA))
def test_las_dos_clases_de_venta_se_pueden_apuntar(tipo, crear_venta):
    venta = crear_venta(tipo=tipo)
    assert venta["tipo"] == tipo
    assert venta["etiqueta_tipo"] == catalogos.ETIQUETA_VENTA_CORTA[tipo]
