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
