"""La seguridad de lo que se sirve por web: cabeceras y alta de cuentas (10/11/2026).

Lo que se ata aquí es lo que el aviso de los coordinadores puso encima de la mesa: que la app había
estado en un túnel abierto, sin cabeceras y con el registro libre. Estas pruebas cubren **lo que se
puede comprobar sin red**:

- las **cabeceras de seguridad** van en todas las respuestas (también en la pantalla y en las
  imágenes), y HSTS **solo** cuando la petición vino por HTTPS;
- el **alta de cuentas** está abierta en pruebas y local, y **cerrada en producción** salvo que se
  encienda a propósito con `CUEDIGITAL_REGISTRO=abierto`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main, seguridad


@pytest.fixture()
def cliente_http():
    with TestClient(main.app) as cliente:
        yield cliente


class TestLasCabecerasDeSeguridad:
    def test_la_salud_lleva_las_cabeceras(self, cliente_http):
        respuesta = cliente_http.get("/health")
        assert respuesta.status_code == 200
        assert respuesta.headers["x-content-type-options"] == "nosniff"
        assert respuesta.headers["x-frame-options"] == "DENY"
        assert respuesta.headers["referrer-policy"] == "no-referrer"
        assert "camera=()" in respuesta.headers["permissions-policy"]
        assert "default-src 'self'" in respuesta.headers["content-security-policy"]
        assert respuesta.headers["cross-origin-opener-policy"] == "same-origin"

    def test_la_pantalla_tambien_las_lleva(self, cliente_http):
        respuesta = cliente_http.get("/nuevo/")
        assert respuesta.status_code == 200
        assert respuesta.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in respuesta.headers["content-security-policy"]

    def test_la_api_tambien(self, cliente_http):
        respuesta = cliente_http.get("/api/interfaz")
        assert respuesta.status_code == 200
        assert respuesta.headers["x-frame-options"] == "DENY"

    def test_por_http_no_se_manda_hsts(self, cliente_http):
        # En local se trabaja por http: mandar HSTS ahí no hace nada y deja el navegador con una
        # idea equivocada del sitio.
        respuesta = cliente_http.get("/health")
        assert "strict-transport-security" not in respuesta.headers

    def test_por_https_si_se_manda_hsts(self):
        with TestClient(main.app, base_url="https://testserver") as cliente:
            respuesta = cliente.get("/health")
        assert respuesta.headers["strict-transport-security"].startswith("max-age=")

    def test_la_politica_no_deja_meter_la_app_en_otra_pagina(self):
        politica = seguridad.CABECERAS["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in politica
        assert "object-src 'none'" in politica


class TestElAltaDeCuentas:
    def test_en_pruebas_esta_abierta(self, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_REGISTRO", raising=False)
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "pruebas")
        assert seguridad.registro_abierto() is True

    def test_en_produccion_esta_cerrada(self, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_REGISTRO", raising=False)
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "")
        assert seguridad.registro_abierto() is False

    def test_se_puede_encender_a_proposito(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_REGISTRO", "abierto")
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "")
        assert seguridad.registro_abierto() is True

    def test_cualquier_otra_cosa_la_cierra(self, monkeypatch):
        for valor in ("cerrado", "no", "0", "ABIERTO?"):
            monkeypatch.setenv("CUEDIGITAL_REGISTRO", valor)
            assert seguridad.registro_abierto() is False, valor

    def test_con_el_registro_cerrado_el_alta_contesta_403(self, cliente_http, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_REGISTRO", "cerrado")
        respuesta = cliente_http.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba",
                "correo": "cerrado@ejemplo.test",
                "clave": "clave-larga-para-probar",
                "explotacion": {"nombre": "Finca de prueba", "nif": "00000000T"},
            },
        )
        assert respuesta.status_code == 403
        # Y el mensaje dice qué hacer, que es la regla de la casa.
        assert "Entra con la cuenta" in respuesta.json()["detail"]

    def test_con_el_registro_abierto_el_alta_no_contesta_403(self, cliente_http, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_REGISTRO", "abierto")
        respuesta = cliente_http.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba",
                "correo": "abierto@ejemplo.test",
                "clave": "clave-larga-para-probar",
                "explotacion": {"nombre": "Finca de prueba", "nif": "00000000T"},
            },
        )
        assert respuesta.status_code == 201
