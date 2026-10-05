"""Las claves de los agricultores, y el atajo que NO se puede colar en producción.

Este fichero existe por una decisión de la ronda 9: la suite tardaba seis minutos porque
registrar una cuenta deriva la clave 240.000 veces, y eso se paga en casi todos los tests.
Se bajó el número **solo para los tests**, y bajar eso es exactamente la clase de atajo que
un día se cuela en el servidor de verdad y deja las claves de todo el mundo fáciles de
adivinar.

Así que el atajo tiene dos cerraduras, y las dos se prueban aquí:

1. Hacen falta **dos** variables de entorno para bajarlo: el número y `CUEDIGITAL_ENTORNO=pruebas`.
2. Si alguien baja el número sin decir que es un entorno de pruebas, el programa **falla
   fuerte** en vez de arrancar con las claves débiles.
"""

from __future__ import annotations

import pytest

from app import security

# El valor que usa la suite.
ITERACIONES_DE_PRUEBAS = "1000"


class TestElMinimoDeIteraciones:
    def test_por_defecto_se_usa_el_numero_de_verdad(self, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_ITERACIONES_PBKDF2", raising=False)
        assert security.iteraciones_pbkdf2() == security.ITERACIONES_PBKDF2

    def test_el_numero_de_verdad_es_alto(self):
        """Si alguien lo baja a mano en el código, que se vea aquí."""
        assert security.ITERACIONES_PBKDF2 >= 200_000

    def test_bajarlo_sin_decir_que_es_un_entorno_de_pruebas_falla(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_ITERACIONES_PBKDF2", ITERACIONES_DE_PRUEBAS)
        monkeypatch.delenv("CUEDIGITAL_ENTORNO", raising=False)
        with pytest.raises(RuntimeError) as error:
            security.iteraciones_pbkdf2()
        assert "fáciles de adivinar" in str(error.value)

    def test_bajarlo_en_el_entorno_de_pruebas_se_permite(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_ITERACIONES_PBKDF2", ITERACIONES_DE_PRUEBAS)
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "pruebas")
        assert security.iteraciones_pbkdf2() == 1000

    def test_un_valor_que_no_es_un_numero_se_dice(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_ITERACIONES_PBKDF2", "muchas")
        with pytest.raises(RuntimeError):
            security.iteraciones_pbkdf2()

    def test_un_numero_por_encima_del_minimo_se_acepta_siempre(self, monkeypatch):
        """Subirlo no es un riesgo: se puede subir en cualquier sitio."""
        monkeypatch.setenv("CUEDIGITAL_ITERACIONES_PBKDF2", "500000")
        monkeypatch.delenv("CUEDIGITAL_ENTORNO", raising=False)
        assert security.iteraciones_pbkdf2() == 500_000


class TestLasClavesGuardadas:
    def test_el_numero_de_iteraciones_va_dentro_del_hash(self):
        """Por eso se puede cambiarlo sin romper las claves que ya están guardadas."""
        guardada = security.hash_clave("una-clave-larga")
        algoritmo, iteraciones, sal, derivada = guardada.split("$")
        assert algoritmo == "pbkdf2_sha256"
        assert int(iteraciones) == security.iteraciones_pbkdf2()
        assert sal and derivada

    def test_una_clave_se_verifica_aunque_cambie_el_numero_de_iteraciones(self, monkeypatch):
        """Cada clave se comprueba con el número con el que se creó, no con el de ahora.

        Es lo que permite bajar el número en los tests sin invalidar nada, y lo que hará que
        subirlo en producción tampoco deje fuera a nadie.
        """
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "pruebas")
        monkeypatch.setenv("CUEDIGITAL_ITERACIONES_PBKDF2", "1000")
        guardada = security.hash_clave("una-clave-larga-de-verdad")

        monkeypatch.setenv("CUEDIGITAL_ITERACIONES_PBKDF2", "5000")
        assert security.verificar_clave("una-clave-larga-de-verdad", guardada) is True
        assert security.verificar_clave("otra-clave-distinta", guardada) is False

    def test_una_clave_corta_no_se_acepta(self):
        with pytest.raises(ValueError):
            security.hash_clave("corta")

    def test_una_clave_guardada_rota_no_revienta(self):
        assert security.verificar_clave("lo-que-sea", "esto-no-es-un-hash") is False
        assert security.verificar_clave("lo-que-sea", "md5$1$a$b") is False

    def test_dos_claves_iguales_no_dan_el_mismo_hash(self):
        """La sal es distinta en cada una: dos agricultores con la misma clave no se ven."""
        una = security.hash_clave("la-misma-clave")
        otra = security.hash_clave("la-misma-clave")
        assert una != otra


class TestElEntornoDePruebas:
    def test_la_suite_se_marca_como_entorno_de_pruebas(self):
        """Es lo que permite que la suite vaya rápido sin debilitar nada de verdad."""
        assert security.entorno_de_pruebas() is True
        assert security.iteraciones_pbkdf2() < security.ITERACIONES_MINIMAS_DE_VERDAD

    def test_solo_cuenta_la_palabra_exacta(self, monkeypatch):
        for valor in ("produccion", "prod", "PRUEBA", "pruebas de carga", ""):
            monkeypatch.setenv("CUEDIGITAL_ENTORNO", valor)
            assert security.entorno_de_pruebas() is False, valor

    def test_acepta_la_palabra_en_cualquier_forma(self, monkeypatch):
        for valor in ("pruebas", "PRUEBAS", " Pruebas "):
            monkeypatch.setenv("CUEDIGITAL_ENTORNO", valor)
            assert security.entorno_de_pruebas() is True, valor
