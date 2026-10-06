"""Cuánto ha costado una tierra: lo que consta, lo que no, y que nada se cuente dos veces.

**Por qué esta prueba vive en su propio fichero.** El recorrido que cierra —«abrir una tierra y entender
qué cultivo tiene, qué trabajos se han hecho, qué queda previsto y **qué costes conocidos tiene**»— es la
mitad que le faltaba a la ficha de una tierra: los trabajos los trae el T15 y el dinero lo trae el T13, y
esta es la costura entre los dos. Se prueba aparte para que las pruebas de cada ticket sigan siendo suyas.

**Lo que se comprueba, y por qué cada cosa importa:**

  1. Un gasto que **dice** la tierra es coste **directo**: lo que pone el papel.
  2. Un gasto que **no** dice tierra y se **repartió** a esa tierra es coste **repartido**: una estimación
     que acordó el agricultor. Van en columnas distintas porque son dos cosas de fiabilidad distinta.
  3. Un gasto de esa tierra que **no dice lo que costó** se **cuenta** (y se dice), y **no se suma un
     cero**: un total que calla que le faltan datos miente, y un cero diría que salió gratis.
  4. **Nada se cuenta dos veces**: un gasto que dice la tierra **y además** tiene un reparto a esa misma
     tierra cuenta una vez (por su importe, que es el criterio de la casa), y el reparto de un gasto que
     dice **otra** tierra no aparece aquí.
  5. Lo **anulado** no cuenta, ni el gasto ni el trozo.
  6. Una tierra de **otra finca** contesta **404** (y no 403: no se cuenta si existe en otra).

Y lo que esta prueba **no** puede comprobar, y se dice: que la pantalla lo enseñe. Eso es de la pantalla de
la historia de una tierra (`tests_js/interfaz.test.js`).
"""

from __future__ import annotations


def _un_gasto(cliente, cuenta, campana, **cambios) -> dict:
    """Un gasto apuntado como lo apunta la pantalla de las cuentas."""
    datos = {
        "campana_id": campana["id"],
        "fecha": "2026-03-04",
        "concepto": "Gasóleo",
        "categoria": "gasoleo",
        "importe": "100.00",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/gastos", headers=cuenta["cabeceras"], json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["gasto"]


def _reparte_a_mano(cliente, cuenta, gasto_id: int, trozos: list[dict]) -> dict:
    """Reparte un gasto con los trozos que se le digan (a una tierra, a un cultivo o sin asignar)."""
    respuesta = cliente.post(
        f"/api/gastos/{gasto_id}/repartos",
        headers=cuenta["cabeceras"],
        json={"metodo": "manual", "destino_tipo": "tierra", "trozos": trozos},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _lo_que_ha_costado(cliente, cuenta, parcela_id: int, campana=None) -> dict:
    consulta = f"?campana_id={campana['id']}" if campana else ""
    respuesta = cliente.get(
        f"/api/gastos/de-una-tierra/{parcela_id}{consulta}", headers=cuenta["cabeceras"]
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


class TestLoQueHaCostadoUnaTierra:
    def test_un_gasto_que_dice_la_tierra_es_coste_directo(self, cliente, cuenta, campana, crear_parcela):
        tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
        _un_gasto(cliente, cuenta, campana, parcela_id=tierra["id"], importe="250.00")

        cuenta_de_la_tierra = _lo_que_ha_costado(cliente, cuenta, tierra["id"])

        assert cuenta_de_la_tierra["directos"] == "250.00"
        assert cuenta_de_la_tierra["repartidos"] == "0.00"
        assert cuenta_de_la_tierra["total_conocido"] == "250.00"
        assert cuenta_de_la_tierra["sin_importe"] == 0
        assert cuenta_de_la_tierra["tierra"] == "El Prado"
        assert [fila["de_donde"] for fila in cuenta_de_la_tierra["filas"]] == ["directo"]

    def test_un_gasto_repartido_a_la_tierra_cuenta_como_repartido(self, cliente, cuenta, campana, crear_parcela):
        """Y **solo el trozo que se llevó a esa tierra**, no el gasto entero."""
        grande = crear_parcela(alias="El Prado", superficie_ha=4.0)
        otra = crear_parcela(alias="La Vega", superficie_ha=2.0, ref_sigpac="37-455-12-9")
        gasto = _un_gasto(cliente, cuenta, campana, concepto="Seguro de la finca", importe="100.00")
        _reparte_a_mano(
            cliente,
            cuenta,
            gasto["id"],
            [
                {"destino_tipo": "tierra", "destino": str(grande["id"]), "importe": "60.00", "metodo": "manual"},
                {"destino_tipo": "tierra", "destino": str(otra["id"]), "importe": "40.00", "metodo": "manual"},
            ],
        )

        suya = _lo_que_ha_costado(cliente, cuenta, grande["id"])

        assert suya["directos"] == "0.00", "un gasto sin tierra no es coste directo de ninguna"
        assert suya["repartidos"] == "60.00"
        assert suya["total_conocido"] == "60.00"
        assert suya["filas"][0]["que_es"] == "Seguro de la finca"
        assert suya["filas"][0]["de_donde"] == "repartido"

    def test_un_gasto_sin_importe_se_cuenta_y_no_se_suma_como_cero(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """**La regla de la casa**: un importe que no consta es «no lo sé», y un total que calla que le
        faltan datos miente."""
        tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
        _un_gasto(cliente, cuenta, campana, parcela_id=tierra["id"], importe="100.00")
        _un_gasto(
            cliente,
            cuenta,
            campana,
            parcela_id=tierra["id"],
            concepto="Reparación del remolque",
            importe=None,
            clave_de_reenvio="movil-sin-importe-1",
        )

        suya = _lo_que_ha_costado(cliente, cuenta, tierra["id"])

        assert suya["directos"] == "100.00", "el gasto sin importe no puede sumar cero"
        assert suya["sin_importe"] == 1, "no se dice que hay un gasto sin importe"
        assert suya["cuantos"] == 2, "las dos líneas están, aunque una no diga el importe"
        sin_importe = [fila for fila in suya["filas"] if fila["importe"] is None][0]
        assert sin_importe["texto_importe"] == "", "un importe que no consta se enseña en blanco"

    def test_un_gasto_que_dice_la_tierra_y_ademas_se_reparte_no_se_cuenta_dos_veces(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """**La trampa que esta prueba existe para cazar.**

        Un gasto que dice la tierra **es coste directo** (así lo cuenta la pantalla de las cuentas,
        `_el_coste_por_clase`), y si sus repartos se sumaran otra vez, ese coste saldría por los dos lados
        y el total de la tierra diría más de lo que costó. Se prueba con el caso exacto: el gasto dice la
        tierra **y** se reparte a ella.
        """
        tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
        gasto = _un_gasto(cliente, cuenta, campana, parcela_id=tierra["id"], importe="100.00")
        _reparte_a_mano(
            cliente,
            cuenta,
            gasto["id"],
            [{"destino_tipo": "tierra", "destino": str(tierra["id"]), "importe": "100.00", "metodo": "manual"}],
        )

        suya = _lo_que_ha_costado(cliente, cuenta, tierra["id"])

        assert suya["total_conocido"] == "100.00", (
            f"el gasto se ha contado dos veces: {suya['texto_total']} "
            f"(directos {suya['texto_directos']} + repartidos {suya['texto_repartidos']})"
        )
        assert suya["repartidos"] == "0.00"
        assert suya["cuantos"] == 1, "el mismo gasto sale dos veces en la lista"

    def test_el_reparto_de_un_gasto_de_otra_tierra_no_aparece_aqui(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Un gasto que dice otra tierra es coste **de esa otra**, y aquí no se cuenta."""
        suya = crear_parcela(alias="El Prado", superficie_ha=4.0)
        ajena = crear_parcela(alias="La Vega", superficie_ha=2.0, ref_sigpac="37-455-12-9")
        gasto = _un_gasto(cliente, cuenta, campana, parcela_id=ajena["id"], importe="100.00")
        _reparte_a_mano(
            cliente,
            cuenta,
            gasto["id"],
            [{"destino_tipo": "tierra", "destino": str(suya["id"]), "importe": "100.00", "metodo": "manual"}],
        )

        cuenta_de_suya = _lo_que_ha_costado(cliente, cuenta, suya["id"])

        assert cuenta_de_suya["total_conocido"] == "0.00", (
            "un gasto que dice otra tierra es coste de esa otra: aquí no puede aparecer por su reparto"
        )

    def test_lo_anulado_no_cuenta_ni_el_gasto_ni_el_trozo(self, cliente, cuenta, campana, crear_parcela):
        tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
        vivo = _un_gasto(cliente, cuenta, campana, parcela_id=tierra["id"], importe="100.00")
        anulado = _un_gasto(
            cliente,
            cuenta,
            campana,
            parcela_id=tierra["id"],
            concepto="Apuntado por error",
            importe="500.00",
            clave_de_reenvio="movil-anulado-1",
        )
        respuesta = cliente.post(
            f"/api/gastos/{anulado['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de tierra"},
        )
        assert respuesta.status_code == 200, respuesta.text

        suya = _lo_que_ha_costado(cliente, cuenta, tierra["id"])

        assert suya["directos"] == "100.00", f"lo anulado ha contado: {suya['texto_directos']}"
        assert suya["cuantos"] == 1
        assert suya["filas"][0]["gasto_id"] == vivo["id"]

    def test_una_tierra_de_otra_finca_contesta_404(self, cliente, cuenta, crear_cuenta, campana, crear_parcela):
        """**Aislamiento entre explotaciones**: 404 y no 403, para no contar si existe en otra finca."""
        tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
        otra = crear_cuenta(correo="otro@ejemplo.test")

        respuesta = cliente.get(
            f"/api/gastos/de-una-tierra/{tierra['id']}", headers=otra["cabeceras"]
        )

        assert respuesta.status_code == 404, respuesta.text

    def test_sin_entrar_no_se_ve_lo_que_ha_costado(self, cliente, crear_parcela, cuenta):
        tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
        assert cliente.get(f"/api/gastos/de-una-tierra/{tierra['id']}").status_code == 401

    def test_la_campana_filtra_lo_que_se_cuenta(self, cliente, cuenta, campana, crear_parcela):
        """El coste es **de un año**: un gasto de otra campaña no entra en la cuenta de esta."""
        tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
        _un_gasto(cliente, cuenta, campana, parcela_id=tierra["id"], importe="100.00")
        # Un gasto sin campaña: no es de este año, y por eso no entra cuando se pide el año.
        _un_gasto(
            cliente,
            cuenta,
            campana,
            parcela_id=tierra["id"],
            campana_id=None,
            concepto="Gasóleo de otro año",
            importe="70.00",
            clave_de_reenvio="movil-sin-campana-1",
        )

        de_este_ano = _lo_que_ha_costado(cliente, cuenta, tierra["id"], campana=campana)
        todo = _lo_que_ha_costado(cliente, cuenta, tierra["id"])

        assert de_este_ano["directos"] == "100.00"
        assert todo["directos"] == "170.00", "sin pedir año, la cuenta es la de todos los apuntes"

# ==========================================================================
# El gasto que dice su tierra está asignado (06/10/2026)
# ==========================================================================
#
# **Estas pruebas se añadieron al recorrer el recorrido 2 en un navegador de verdad.** Un gasto apuntado
# **con su tierra** salía en la pantalla como «Su tierra: Sin asignar», con 0,00 € en «en tierras,
# cultivos o máquinas» y con el aviso «Estas cuentas no cierran: hay una parte del gasto que no está ni
# en un sitio ni en el otro» — cuando el agricultor acababa de decir de qué tierra era—. El ticket dice
# lo contrario: «**El coste directo**: cuando el gasto ya dice de qué tierra o de qué cultivo es. Lo que
# no se sabe a qué va se apunta sin estos dos campos y se reparte después». Y la propia respuesta del
# servidor ya clasificaba ese gasto como directo en su resumen de costes: las dos mitades de la misma
# respuesta decían cosas distintas.


class TestUnGastoQueDiceSuTierraEstaAsignado:
    def _un_gasto(self, cliente, cuenta, campana, parcela, **cambios):
        datos = {
            "campana_id": campana["id"],
            "fecha": "2026-04-12",
            "concepto": "El gasóleo de la siega",
            "categoria": "gasoleo",
            "importe": "254.10",
            "parcela_id": parcela["id"],
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/gastos", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()["gasto"]

    def test_su_tierra_es_la_que_dice_y_no_sin_asignar(self, cliente, cuenta, campana, crear_parcela):
        """El gasto dice a dónde va, y lo dice con el nombre de la tierra."""
        parcela = crear_parcela(alias="El Prado")
        gasto = self._un_gasto(cliente, cuenta, campana, parcela)
        assert gasto["va_a"] == "El Prado", (
            f"un gasto apuntado con su tierra dice que va a «{gasto['va_a']}»: es lo contrario de lo "
            "que escribió el agricultor"
        )
        # Y el cuadre lo cuenta como asignado, así que **no falta nada**.
        cuadre = gasto["cuadre_del_reparto"]
        assert cuadre["texto_repartido"] == "254,10 €", (
            "el coste directo no se cuenta como asignado: la pantalla dirá que las cuentas no cierran"
        )
        assert cuadre["cuadra"] is True
        assert cuadre["texto_sin_asignar"] == "0,00 €"
        assert gasto["no_cuadra"] is False

    def test_sin_decir_a_que_va_sigue_estando_sin_asignar(self, cliente, cuenta, campana):
        """El otro lado: un gasto que **no** dice de dónde es no está asignado, y eso se dice.

        Es la mitad que impide que el arreglo se pase de largo: si todo cuadrara siempre, el aviso del
        coste sin asignar no valdría para nada.
        """
        respuesta = cliente.post(
            "/api/gastos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "concepto": "La reparación del remolque",
                "categoria": "reparacion",
                "importe": "80.00",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        gasto = respuesta.json()["gasto"]
        assert gasto["va_a"] == "", "un gasto que no dice a dónde va dice que va a algún sitio"
        assert gasto["cuadre_del_reparto"]["texto_repartido"] == "0,00 €"
        assert gasto["no_cuadra"] is True, "sin decir a qué va, las cuentas tienen que avisar"
        # Y el resumen de la respuesta lo cuenta como sin asignar, que es su columna.
        assert gasto["esta_sin_repartir"] is True

    def test_con_repartos_manda_el_reparto_y_no_se_cuenta_dos_veces(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Un gasto repartido **no** suma además su coste directo: el mismo dinero no puede contarse dos
        veces. Es la trampa que este arreglo podía traer, así que se prueba."""
        parcela = crear_parcela(alias="El Prado")
        gasto = self._un_gasto(cliente, cuenta, campana, parcela, importe="300.00")
        repartido = cliente.post(
            f"/api/gastos/{gasto['id']}/repartos",
            headers=cuenta["cabeceras"],
            json={
                "metodo": "manual",
                "destino_tipo": "tierra",
                "trozos": [{"destino_tipo": "tierra", "destino": str(parcela["id"]), "importe": "300.00"}],
                "confirmado": True,
            },
        )
        assert repartido.status_code in (200, 201), repartido.text
        ficha = cliente.get(f"/api/gastos/{gasto['id']}", headers=cuenta["cabeceras"]).json()
        cuadre = ficha["cuadre_del_reparto"]
        assert cuadre["texto_repartido"] == "300,00 €", (
            "el gasto repartido cuenta el dinero dos veces: el reparto y su coste directo"
        )
        assert cuadre["texto_sin_asignar"] == "0,00 €"
        assert cuadre["cuadra"] is True
