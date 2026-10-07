"""La búsqueda global: lo que encuentra, lo que no, y lo que **no puede** encontrar.

Es la puerta que pidió el encargo del rediseño («búsqueda global» en la cabecera). Lo que se comprueba
aquí, por orden de importancia:

1. **Que no enseñe lo de otra explotación.** Es lo primero que hay que probar de un buscador en un
   programa que guarda datos de varios agricultores: buscar no puede ser una forma de enterarse de lo que
   hay en la finca del vecino.
2. Que encuentre **por el nombre y por la referencia oficial**, que son las dos formas en las que el
   agricultor nombra una tierra.
3. Que **no invente**: con una letra suelta no busca y lo dice; si no hay nada, devuelve cero.

Las cuentas y las tierras se crean **por la API**, como lo haría el agricultor: así la prueba no depende
de cómo estén hechas las tablas por dentro.
"""

from __future__ import annotations


def _una_tierra(cliente, cuenta, alias: str, ref: str = "") -> int:
    respuesta = cliente.post(
        "/api/parcelas",
        json={"alias": alias, "ref_sigpac": ref or None},
        headers=cuenta["cabeceras"],
    )
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()["id"]


def _buscar(cliente, cuenta, texto: str) -> dict:
    respuesta = cliente.get("/api/buscar", params={"texto": texto}, headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _etiquetas(salida: dict) -> list[str]:
    return [r["etiqueta"] for grupo in salida["grupos"] for r in grupo["resultados"]]


class TestLaBusqueda:
    def test_encuentra_por_el_nombre_y_por_la_referencia(self, cliente, cuenta):
        _una_tierra(cliente, cuenta, "El Prado de arriba", "ES-P-00001-0001")
        _una_tierra(cliente, cuenta, "La Vega del río", "ES-P-00002-0002")

        por_nombre = _buscar(cliente, cuenta, "prado")
        assert por_nombre["buscado"] is True
        assert _etiquetas(por_nombre) == ["El Prado de arriba"]

        por_referencia = _buscar(cliente, cuenta, "00002")
        assert _etiquetas(por_referencia) == ["La Vega del río"]

    def test_el_texto_se_coteja_sin_tildes(self, cliente, cuenta):
        """«Machacón» tiene que salir buscando «MACHACON»: es el caso que está documentado en el buscador
        de tierras, y esta puerta coteja igual **a propósito** (el mismo `_como_se_busca`)."""
        _una_tierra(cliente, cuenta, "Machacón")
        assert _etiquetas(_buscar(cliente, cuenta, "MACHACON")) == ["Machacón"]

    def test_no_ensena_lo_de_otra_explotacion(self, cliente, cuenta, crear_cuenta):
        """**Lo más importante de un buscador aquí.** La tierra de la otra explotación no sale, y tampoco
        se dice que exista: no sale, y ya está."""
        _una_tierra(cliente, cuenta, "El Prado de arriba")
        la_ajena = crear_cuenta("ajena-buscar@ejemplo.test", nombre="El vecino")
        _una_tierra(cliente, la_ajena, "El Prado de la ajena", "ES-P-99999-9999")

        assert _etiquetas(_buscar(cliente, cuenta, "prado")) == ["El Prado de arriba"]
        assert _etiquetas(_buscar(cliente, la_ajena, "prado")) == ["El Prado de la ajena"]

    def test_con_una_letra_no_busca_y_lo_dice(self, cliente, cuenta):
        """Una letra sacaría casi todo, y una lista con casi todo no ayuda a encontrar nada. Se dice con su
        motivo, en vez de devolver una lista larga o un vacío sin explicación."""
        _una_tierra(cliente, cuenta, "El Prado")
        salida = _buscar(cliente, cuenta, "p")
        assert salida["buscado"] is False
        assert salida["motivo"] == "muy_corto"
        assert salida["grupos"] == []

    def test_si_no_hay_nada_devuelve_cero_y_no_inventa(self, cliente, cuenta):
        _una_tierra(cliente, cuenta, "El Prado")
        salida = _buscar(cliente, cuenta, "helicoptero")
        assert salida["buscado"] is True
        assert salida["grupos"] == []

    def test_encuentra_un_gasto_por_su_concepto_y_dice_lo_que_costo(self, cliente, cuenta):
        """Y lo que se busca con un nombre en la cabeza («el gasóleo») sale con **su importe**, que es lo
        que se quiere saber al encontrarlo. Los dos grupos conviven: una búsqueda puede encontrar una
        tierra y un gasto a la vez."""
        respuesta = cliente.post(
            "/api/gastos",
            json={"concepto": "Gasóleo de la siega", "importe": "300.50", "fecha": "2026-06-15"},
            headers=cuenta["cabeceras"],
        )
        assert respuesta.status_code in (200, 201), respuesta.text
        _una_tierra(cliente, cuenta, "El Prado del gasóleo")

        salida = _buscar(cliente, cuenta, "gasoleo")
        por_clave = {grupo["clave"]: grupo for grupo in salida["grupos"]}
        assert set(por_clave) == {"tierras", "gastos"}
        assert [r["etiqueta"] for r in por_clave["gastos"]["resultados"]] == ["Gasóleo de la siega"]
        assert "300,50" in por_clave["gastos"]["resultados"][0]["detalle"]

    def test_un_gasto_sin_importe_sale_sin_cifra_ni_cero(self, cliente, cuenta):
        """Un gasto del que no se sabe lo que costó **existe** y hay que poder encontrarlo; lo que no se
        hace es enseñar un cero, que diría que costó cero."""
        respuesta = cliente.post(
            "/api/gastos",
            json={"concepto": "Reparación del tractor", "fecha": "2026-06-16"},
            headers=cuenta["cabeceras"],
        )
        assert respuesta.status_code in (200, 201), respuesta.text

        salida = _buscar(cliente, cuenta, "reparacion")
        gastos = [g for g in salida["grupos"] if g["clave"] == "gastos"][0]
        assert [r["etiqueta"] for r in gastos["resultados"]] == ["Reparación del tractor"]
        assert "0" not in gastos["resultados"][0]["detalle"], (
            f"un gasto sin importe no puede enseñar un cero: {gastos['resultados'][0]['detalle']!r}"
        )

    def test_tampoco_ensena_los_gastos_de_otra_explotacion(self, cliente, cuenta, crear_cuenta):
        la_ajena = crear_cuenta("ajena-gastos@ejemplo.test", nombre="El vecino")
        respuesta = cliente.post(
            "/api/gastos",
            json={"concepto": "Gasóleo del vecino", "importe": "10.00", "fecha": "2026-06-15"},
            headers=la_ajena["cabeceras"],
        )
        assert respuesta.status_code in (200, 201), respuesta.text

        salida = _buscar(cliente, cuenta, "gasoleo")
        assert salida["grupos"] == [], "sale un gasto que no es de esta explotación"

    def test_encuentra_a_una_persona_y_dice_lo_que_la_distingue(self, cliente, cuenta):
        """Las personas se buscan por su nombre, y lo que se enseña al lado es **lo que distingue a dos
        que se llaman igual**: su teléfono o su NIF. Si no consta ninguno, no se enseña un hueco."""
        respuesta = cliente.post(
            "/api/contactos",
            json={"nombre": "Talleres Mariano", "telefono": "600 111 222", "es_empresa": True},
            headers=cuenta["cabeceras"],
        )
        assert respuesta.status_code in (200, 201), respuesta.text

        salida = _buscar(cliente, cuenta, "mariano")
        personas = [g for g in salida["grupos"] if g["clave"] == "personas"][0]
        assert [r["etiqueta"] for r in personas["resultados"]] == ["Talleres Mariano"]
        assert personas["resultados"][0]["detalle"] == "600 111 222"

    def test_tampoco_ensena_las_personas_de_otra_explotacion(self, cliente, cuenta, crear_cuenta):
        la_ajena = crear_cuenta("ajena-personas@ejemplo.test", nombre="El vecino")
        respuesta = cliente.post(
            "/api/contactos",
            json={"nombre": "Talleres del vecino"},
            headers=la_ajena["cabeceras"],
        )
        assert respuesta.status_code in (200, 201), respuesta.text

        assert _buscar(cliente, cuenta, "talleres")["grupos"] == [], (
            "sale una persona que no es de esta explotación"
        )

    def _una_maquina(self, cliente, cuenta, nombre: str, matricula: str = "") -> None:
        """Dar de alta una máquina por la API.

        **`clase`, `propiedad` y `disponibilidad` son obligatorias y no tienen valor de partida** (a
        propósito: un valor por defecto sería afirmar «es tuya» o «está disponible» sin que nadie lo haya
        dicho). Los valores que admite cada una están en `app/maquinaria.py`.
        """
        respuesta = cliente.post(
            "/api/maquinaria",
            json={
                "nombre": nombre,
                "matricula": matricula or None,
                "clase": "tractor",
                "propiedad": "no_se",
                "disponibilidad": "no_se",
            },
            headers=cuenta["cabeceras"],
        )
        assert respuesta.status_code in (200, 201), respuesta.text

    def test_encuentra_una_maquina_por_su_nombre_y_por_su_matricula(self, cliente, cuenta):
        """Las máquinas se buscan por su nombre y **por su matrícula**, que es como se las nombra cuando se
        habla de ellas en el taller. Al lado se enseña la matrícula, que es lo que distingue dos tractores."""
        self._una_maquina(cliente, cuenta, "Tractor de la casa", "1234 ABC")

        por_nombre = _buscar(cliente, cuenta, "tractor")
        maquinas = [g for g in por_nombre["grupos"] if g["clave"] == "maquinas"][0]
        assert [r["etiqueta"] for r in maquinas["resultados"]] == ["Tractor de la casa"]
        assert maquinas["resultados"][0]["detalle"] == "1234 ABC"

        por_matricula = _buscar(cliente, cuenta, "1234")
        assert [g["clave"] for g in por_matricula["grupos"]] == ["maquinas"]

    def test_tampoco_ensena_las_maquinas_de_otra_explotacion(self, cliente, cuenta, crear_cuenta):
        la_ajena = crear_cuenta("ajena-maquinas@ejemplo.test", nombre="El vecino")
        self._una_maquina(cliente, la_ajena, "Tractor del vecino", "9999 ZZZ")

        assert _buscar(cliente, cuenta, "tractor")["grupos"] == [], (
            "sale una máquina que no es de esta explotación"
        )
