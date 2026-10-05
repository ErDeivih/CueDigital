"""Tests del cliente del IUWS: el que habla de verdad con la Junta.

Lo importante de estos tests es que **no salen a internet**. `httpx` deja inyectar un
transporte de mentira, así que se prueba el flujo entero —la dirección, las cabeceras, el
cuerpo y la lectura de la respuesta— sin red. La única prueba que sale de verdad es la de humo,
que es donde toca.

Y lo que no se puede probar, se declara: firmar el parámetro `data-signed` necesita la clave
privada del certificado, que no existe todavía. Aquí se prueba que **no se inventa una firma**
y que se dice qué falta.
"""

from __future__ import annotations

import base64
import json
import pathlib

import httpx
import pytest

from app import iuws, iuws_cliente

# Un certificado de mentira, con la forma de uno de verdad (lo que importa son las líneas de
# cabecera y los saltos de línea, no el contenido).
CERTIFICADO_DE_MENTIRA = """-----BEGIN CERTIFICATE-----
MIIB1TCCAXugAwIBAgIUJ
QvZ8pQ2mZ0kZ1Qw
-----END CERTIFICATE-----
"""


def transporte(manejador) -> httpx.MockTransport:
    return httpx.MockTransport(manejador)


# --------------------------------------------------------------------------
# La cabecera del certificado
# --------------------------------------------------------------------------


class TestLaCabeceraDelCertificado:
    def test_quita_las_lineas_de_begin_y_end(self):
        """El anexo lo dice: se manda el certificado sin las líneas de cabecera."""
        limpio = iuws_cliente.cabecera_certificado(CERTIFICADO_DE_MENTIRA)
        assert "BEGIN" not in limpio
        assert "END" not in limpio
        assert limpio.startswith("MIIB1TCC")

    def test_quita_todos_los_saltos_de_linea(self):
        """Y sin saltos: si se manda con ellos, el interfaz no lo reconoce."""
        limpio = iuws_cliente.cabecera_certificado(CERTIFICADO_DE_MENTIRA)
        assert "\n" not in limpio
        assert "\r" not in limpio
        assert limpio == "MIIB1TCCAXugAwIBAgIUJQvZ8pQ2mZ0kZ1Qw"

    def test_acepta_un_certificado_que_ya_viene_pelado(self):
        """Un DER pasado a base64 no trae líneas de cabecera: hay que aceptarlo igual."""
        assert iuws_cliente.cabecera_certificado("MIIB1TCC\nAXug") == "MIIB1TCCAXug"

    def test_sin_certificado_devuelve_vacio_y_no_falla(self):
        """Vacío es «no hay certificado», y eso se dice; no se manda una cabecera con basura."""
        assert iuws_cliente.cabecera_certificado("") == ""
        assert iuws_cliente.cabecera_certificado("   \n  ") == ""

    def test_no_se_pierde_ningun_caracter_del_contenido(self):
        """Quitar las líneas de cabecera no puede comerse ni un carácter del certificado."""
        original = "".join(
            linea for linea in CERTIFICADO_DE_MENTIRA.splitlines() if not linea.startswith("-----")
        )
        assert iuws_cliente.cabecera_certificado(CERTIFICADO_DE_MENTIRA) == original


class TestLeerElCertificadoDelDisco:
    def test_sin_configurar_devuelve_nada(self, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_IUWS_CERTIFICADO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CLAVE", raising=False)
        assert iuws_cliente.certificado_configurado() == (None, None)

    def test_con_solo_el_certificado_no_vale(self, monkeypatch, tmp_path):
        """Hacen falta los dos: con el certificado y sin la clave no se puede firmar nada."""
        certificado = tmp_path / "cert.pem"
        certificado.write_text(CERTIFICADO_DE_MENTIRA, encoding="utf-8")
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(certificado))
        monkeypatch.delenv("CUEDIGITAL_IUWS_CLAVE", raising=False)
        assert iuws_cliente.certificado_configurado() == (None, None)

    def test_lo_lee_cuando_estan_los_dos(self, monkeypatch, tmp_path):
        certificado = tmp_path / "cert.pem"
        clave = tmp_path / "clave.pem"
        certificado.write_text(CERTIFICADO_DE_MENTIRA, encoding="utf-8")
        clave.write_text("-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----\n", encoding="utf-8")
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(certificado))
        monkeypatch.setenv("CUEDIGITAL_IUWS_CLAVE", str(clave))
        leido, leida_clave = iuws_cliente.certificado_configurado()
        assert "BEGIN CERTIFICATE" in leido
        assert "PRIVATE KEY" in leida_clave

    def test_una_ruta_que_no_existe_no_revienta(self, monkeypatch, tmp_path):
        """Si el fichero no está donde dice, es «no hay certificado», no un error del programa."""
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(tmp_path / "no_esta.pem"))
        monkeypatch.setenv("CUEDIGITAL_IUWS_CLAVE", str(tmp_path / "tampoco.pem"))
        assert iuws_cliente.certificado_configurado() == (None, None)


class TestDondeContesta:
    """La dirección que trae el programa por defecto es una trampa, y hay que decirlo.

    El entorno de integración de FEGA contesta en `/IUWS/` pero **no publica ninguno de los
    siete métodos** (dan 404). Sin esto, la prueba de conexión diría «404» y quien la leyera
    pensaría que el problema es suyo.
    """

    def test_si_la_configurada_contesta_no_sigue_preguntando(self):
        """Preguntar a servidores que ya se sabe que no van a contestar es molestar."""
        llamadas = []

        def manejador(peticion):
            llamadas.append(str(peticion.url))
            return httpx.Response(200, json={"version": "3.11.4"})

        datos = iuws_cliente.comprobar_donde_contesta(
            "https://servicios.ayg.jcyl.es", transporte=transporte(manejador)
        )
        assert len(llamadas) == 1
        assert datos["buena"]["base"] == "https://servicios.ayg.jcyl.es"
        assert datos["buena"]["version"] == "3.11.4"
        assert "3.11.4" in datos["mensaje"]
        assert "tienes puesta" in datos["mensaje"]

    def test_si_la_configurada_da_404_prueba_la_de_la_comunidad(self):
        def manejador(peticion):
            if "entornointegracion" in str(peticion.url):
                return httpx.Response(404, text="")
            return httpx.Response(200, json={"version": "3.11.4"})

        datos = iuws_cliente.comprobar_donde_contesta(
            "https://sga.entornointegracion.es", transporte=transporte(manejador)
        )
        assert [f["codigo"] for f in datos["probadas"]] == [404, 200]
        assert datos["buena"]["base"] == "https://servicios.ayg.jcyl.es"
        # Y se dice que hay que cambiar la dirección, no solo que una contesta.
        assert "no por la dirección que tienes puesta" in datos["mensaje"]
        assert "servicios.ayg.jcyl.es" in datos["mensaje"]

    def test_si_nadie_contesta_se_dice_que_es_la_red(self):
        def manejador(peticion):
            raise httpx.ConnectError("sin salida")

        datos = iuws_cliente.comprobar_donde_contesta(
            "https://sga.entornointegracion.es", transporte=transporte(manejador)
        )
        assert datos["buena"] is None
        assert "red" in datos["mensaje"].lower() or "cortafuegos" in datos["mensaje"].lower()
        # Y no se culpa a las credenciales, que es lo que hay que evitar.
        assert "credenciales" in datos["mensaje"].lower()

    def test_un_404_se_explica_como_lo_que_es(self):
        datos = iuws_cliente.comprobar_donde_contesta(
            "https://sga.entornointegracion.es",
            transporte=transporte(lambda peticion: httpx.Response(404, text="")),
        )
        assert datos["buena"] is None
        assert "404" in datos["mensaje"]
        # Lo importante: que no se confunda con un problema de credenciales.
        assert "NO es un problema de credenciales" in datos["mensaje"]
        assert "Anexo VI" in datos["mensaje"]

    def test_prueba_la_configurada_primero(self):
        datos = iuws_cliente.comprobar_donde_contesta(
            "https://otra.direccion.es",
            transporte=transporte(lambda peticion: httpx.Response(404, text="")),
        )
        assert datos["probadas"][0]["base"] == "https://otra.direccion.es"

    def test_no_prueba_dos_veces_la_misma_direccion(self):
        """Si la configurada ya es la de la comunidad, no se llama dos veces al mismo sitio."""
        datos = iuws_cliente.comprobar_donde_contesta(
            "https://servicios.ayg.jcyl.es",
            transporte=transporte(lambda peticion: httpx.Response(404, text="")),
        )
        bases = [f["base"] for f in datos["probadas"]]
        assert len(bases) == len(set(bases))

    def test_las_bases_conocidas_son_las_del_anexo(self):
        assert iuws.BASES_CONOCIDAS == tuple(iuws.BASES_POR_CCAA.values())
        assert "https://servicios.ayg.jcyl.es" in iuws.BASES_CONOCIDAS


class TestLoQueSeComproboEnElEntornoDeIntegracion:
    def test_la_ruta_actual_de_version_si_contesta(self):
        assert iuws.COMPROBADO_ENTORNO_INTEGRACION
        assert "404" in iuws.COMPROBADO_ENTORNO_INTEGRACION["/IUWS/version"]
        assert "200" in iuws.COMPROBADO_ENTORNO_INTEGRACION["/IUWS/api/version"]

    def test_el_de_la_comunidad_si_los_tiene(self):
        assert "/IUWS/api/version" in iuws.COMPROBADO_CONTRA_EL_INTERFAZ
        assert "200" in iuws.COMPROBADO_CONTRA_EL_INTERFAZ["/IUWS/api/version"]

    def test_el_entorno_de_integracion_es_la_direccion_por_defecto(self):
        """Si algún día cambia la dirección por defecto, esto avisa de que hay que repensarlo."""
        assert iuws.ENTORNO_INTEGRACION == "https://sga.entornointegracion.es"


# --------------------------------------------------------------------------
# La firma: lo que NO se hace
# --------------------------------------------------------------------------


class TestLaFirmaDelDato:
    @pytest.fixture(autouse=True)
    def _sin_el_certificado_de_verdad(self, monkeypatch):
        """**Las pruebas no tocan el certificado de nadie.**

        Desde la ronda 31, `datos_firmados` sabe firmar con el certificado del almacén de Windows
        cuando está configurado. Si en el ordenador donde se corren las pruebas hay uno (y lo hay),
        una prueba que llegue hasta ahí **firmaría de verdad con la clave privada de David**. Eso no
        se hace nunca: aquí se apaga ese camino, y las pruebas que quieren probarlo lo encienden a
        mano con un script de mentira.
        """
        monkeypatch.delenv("CUEDIGITAL_CERTIFICADO", raising=False)
        monkeypatch.setattr(
            iuws_cliente, "FIRMADOR_DE_WINDOWS", pathlib.Path("no-existe-este-script.ps1")
        )

    def test_con_un_firmador_de_mentira_devuelve_la_firma_en_base64(self):
        """Así se puede probar el flujo entero sin tener la clave privada de verdad."""
        datos = iuws_cliente.datos_firmados("12345678Z", firmador=lambda texto: b"firma-de-mentira")
        assert datos == base64.b64encode(b"firma-de-mentira").decode("ascii")
        assert base64.b64decode(datos) == b"firma-de-mentira"

    def test_al_firmador_se_le_pasa_el_dato_en_utf8(self):
        """El interfaz firma el texto tal cual: si se cambiara la codificación, no cuadraría."""
        visto = {}

        def firmador(texto):
            visto["texto"] = texto
            return b"x"

        iuws_cliente.datos_firmados("B12345678", firmador=firmador)
        assert visto["texto"] == b"B12345678"

    def test_sin_firmador_y_sin_clave_devuelve_nada(self, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_IUWS_CERTIFICADO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CLAVE", raising=False)
        assert iuws_cliente.datos_firmados("12345678Z") is None

    def test_sin_dato_no_hay_nada_que_firmar(self):
        assert iuws_cliente.datos_firmados("") is None

    def test_nunca_devuelve_una_firma_inventada(self, monkeypatch):
        """Esto es lo importante: si no se puede firmar, se dice. Una firma falsa haría que el
        interfaz rechazara la carga o, peor, aceptara algo mal firmado."""
        monkeypatch.delenv("CUEDIGITAL_IUWS_CERTIFICADO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CLAVE", raising=False)
        for dato in ("12345678Z", "B12345678", "cualquier-cosa"):
            assert iuws_cliente.datos_firmados(dato) is None

    def test_se_dice_que_hace_falta_para_firmar(self):
        texto = iuws_cliente.falta_para_firmar()
        assert "CUEDIGITAL_IUWS_CLAVE" in texto
        assert "CUEDIGITAL_IUWS_CERTIFICADO" in texto
        # Y con las palabras de la lista de lo que falta, no con otras.
        assert iuws.por_que_falta("certificado")


# --------------------------------------------------------------------------
# Las cabeceras de la llamada
# --------------------------------------------------------------------------


class TestLasCabeceras:
    def test_el_token_va_en_authorization_sin_la_palabra_bearer(self):
        """El anexo lo manda pelado; los ejemplos no llevan «Bearer»."""
        cabeceras = iuws_cliente._cabeceras("eyJhbGciOi", None)
        assert cabeceras["Authorization"] == "eyJhbGciOi"
        assert "Bearer" not in cabeceras["Authorization"]

    def test_el_certificado_va_en_su_cabecera(self):
        cabeceras = iuws_cliente._cabeceras(None, "MIIB1TCC")
        assert cabeceras["certificate-sscc"] == "MIIB1TCC"

    def test_sin_token_ni_certificado_no_se_mandan_cabeceras_vacias(self):
        """Una cabecera vacía es peor que no mandarla: el interfaz la lee y no entiende nada."""
        cabeceras = iuws_cliente._cabeceras(None, None)
        assert "Authorization" not in cabeceras
        assert "certificate-sscc" not in cabeceras

    def test_siempre_se_pide_json(self):
        assert iuws_cliente._cabeceras(None, None)["Accept"] == "application/json"


# --------------------------------------------------------------------------
# La versión: la única llamada que se puede hacer hoy
# --------------------------------------------------------------------------


class TestComprobarLaVersion:
    def test_lee_la_version_que_contesta_el_interfaz(self):
        def manejador(peticion):
            assert peticion.method == "GET"
            assert str(peticion.url) == "https://ejemplo.es/IUWS/api/version"
            return httpx.Response(200, json={"version": "3.11.4"})

        resultado = iuws_cliente.comprobar_version("https://ejemplo.es", transporte=transporte(manejador))
        assert resultado.hecha is True
        assert resultado.codigo == 200
        assert resultado.cabeceras["version"] == "3.11.4"
        assert "3.11.4" in resultado.mensaje

    def test_la_version_observada_es_la_que_contestó_de_verdad(self):
        """Si alguien cambia la constante sin volver a llamar, este test lo para."""
        assert iuws.VERSION_OBSERVADA == "3.11.4"
        assert iuws.FECHA_DE_LA_COMPROBACION

    def test_acepta_una_version_en_texto_y_no_solo_json(self):
        resultado = iuws_cliente.comprobar_version(
            "https://ejemplo.es",
            transporte=transporte(lambda peticion: httpx.Response(200, text="Versión del descriptor : 3.11.4")),
        )
        assert resultado.codigo == 200
        assert resultado.cabeceras["version"] == "3.11.4"

    def test_si_no_contesta_lo_dice_sin_reventar(self):
        """Un fallo de red tiene que llegar como «no se pudo», no como una excepción."""

        def manejador(peticion):
            raise httpx.ConnectError("sin red")

        resultado = iuws_cliente.comprobar_version("https://ejemplo.es", transporte=transporte(manejador))
        assert resultado.hecha is True
        assert resultado.codigo is None
        assert "no se ha podido llegar" in resultado.mensaje.lower()

    def test_usa_la_base_configurada_si_no_se_le_dice_otra(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_IUWS_BASE", "https://otra.es")
        resultado = iuws_cliente.comprobar_version(
            transporte=transporte(lambda peticion: httpx.Response(200, json={"version": "1"}))
        )
        assert resultado.url == "https://otra.es/IUWS/api/version"

    def test_un_codigo_raro_no_se_confunde_con_un_ok(self):
        resultado = iuws_cliente.comprobar_version(
            "https://ejemplo.es",
            transporte=transporte(lambda peticion: httpx.Response(500, text="vaya")),
        )
        assert resultado.codigo == 500
        assert "500" in resultado.mensaje

    def test_un_fallo_del_programa_no_se_disfraza_de_fallo_de_red(self):
        """Esto se descubrió con un test que pasaba un manejador donde va un transporte.

        El cliente decía «no se ha podido llegar al interfaz», que habría mandado a buscar el
        problema en el cortafuegos. Un fallo del propio programa tiene que salir a la luz.
        """
        with pytest.raises(AttributeError):
            iuws_cliente.comprobar_version("https://ejemplo.es", transporte=lambda peticion: None)


# --------------------------------------------------------------------------
# El token
# --------------------------------------------------------------------------


class TestPedirElToken:
    def test_sin_nombre_comercial_no_llama_y_dice_que_falta(self, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_IUWS_APP", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CERTIFICADO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CLAVE", raising=False)
        resultado = iuws_cliente.pedir_token("https://ejemplo.es")
        assert resultado.hecha is False
        assert "nombre comercial" in resultado.mensaje.lower()

    def test_con_nombre_pero_sin_certificado_no_llama(self, monkeypatch):
        """El certificado lo exige el servidor: llamar sin él solo da un error sin arreglo."""
        monkeypatch.setenv("CUEDIGITAL_IUWS_APP", "CuadernoDePrueba")
        monkeypatch.delenv("CUEDIGITAL_IUWS_CERTIFICADO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CLAVE", raising=False)
        resultado = iuws_cliente.pedir_token("https://ejemplo.es")
        assert resultado.hecha is False
        assert "certificado" in resultado.mensaje.lower()

    def test_la_direccion_lleva_el_nombre_comercial(self, monkeypatch, tmp_path):
        """El nombre del cuaderno va en la dirección, no en el certificado."""
        certificado = tmp_path / "cert.pem"
        clave = tmp_path / "clave.pem"
        certificado.write_text(CERTIFICADO_DE_MENTIRA, encoding="utf-8")
        clave.write_text("clave", encoding="utf-8")
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(certificado))
        monkeypatch.setenv("CUEDIGITAL_IUWS_CLAVE", str(clave))

        def manejador(peticion):
            assert str(peticion.url) == "https://ejemplo.es/IUWS/api/comunicacion/CuadernoDePrueba"
            return httpx.Response(200, json={"resultado": {"codigoResultado": "OK"}})

        resultado = iuws_cliente.pedir_token(
            "https://ejemplo.es", nombre_app="CuadernoDePrueba", transporte=transporte(manejador)
        )
        assert resultado.codigo == 200
        assert resultado.respuesta.esta_ok is True

    def test_una_credencial_mala_se_explica_con_su_nombre(self, monkeypatch, tmp_path):
        certificado = tmp_path / "cert.pem"
        clave = tmp_path / "clave.pem"
        certificado.write_text(CERTIFICADO_DE_MENTIRA, encoding="utf-8")
        clave.write_text("clave", encoding="utf-8")
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(certificado))
        monkeypatch.setenv("CUEDIGITAL_IUWS_CLAVE", str(clave))

        resultado = iuws_cliente.pedir_token(
            "https://ejemplo.es",
            nombre_app="CuadernoDePrueba",
            transporte=transporte(
                lambda peticion: httpx.Response(
                    200,
                    json={"resultado": {"codigoResultado": "ERROR_VALIDAR_CREDENCIALES"}},
                )
            ),
        )
        assert resultado.respuesta.codigo == "ERROR_VALIDAR_CREDENCIALES"
        assert "credenciales" in resultado.mensaje.lower()
        # Y sale el nombre del código, que es lo que se busca en el manual y lo que se pega en
        # un correo a soporte. «La llamada no está autorizada» a secas no basta.
        assert "ERROR_VALIDAR_CREDENCIALES" in resultado.mensaje
        assert "autorizada" in resultado.mensaje.lower()

    def test_un_200_con_error_en_el_cuerpo_no_se_cuenta_como_que_va_bien(self, monkeypatch, tmp_path):
        """El interfaz contesta 200 aunque el resultado sea un error.

        Es la trampa que hace perder una tarde: mirar solo el estado HTTP y decir «comunicación
        establecida» cuando en realidad ha dicho ERROR_VALIDAR_CREDENCIALES.
        """
        certificado = tmp_path / "cert.pem"
        clave = tmp_path / "clave.pem"
        certificado.write_text(CERTIFICADO_DE_MENTIRA, encoding="utf-8")
        clave.write_text("clave", encoding="utf-8")
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(certificado))
        monkeypatch.setenv("CUEDIGITAL_IUWS_CLAVE", str(clave))

        resultado = iuws_cliente.pedir_token(
            "https://ejemplo.es",
            nombre_app="CuadernoDePrueba",
            transporte=transporte(
                lambda peticion: httpx.Response(
                    200, json={"resultado": {"codigoResultado": "ERROR_VALIDAR_CERTIFICADO"}}
                )
            ),
        )
        assert resultado.codigo == 200
        assert resultado.respuesta.esta_ok is False
        assert "establecida" not in resultado.mensaje.lower()
        assert "ERROR_VALIDAR_CERTIFICADO" in resultado.mensaje

    def test_cuando_de_verdad_va_bien_si_lo_dice(self, monkeypatch, tmp_path):
        certificado = tmp_path / "cert.pem"
        clave = tmp_path / "clave.pem"
        certificado.write_text(CERTIFICADO_DE_MENTIRA, encoding="utf-8")
        clave.write_text("clave", encoding="utf-8")
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(certificado))
        monkeypatch.setenv("CUEDIGITAL_IUWS_CLAVE", str(clave))

        resultado = iuws_cliente.pedir_token(
            "https://ejemplo.es",
            nombre_app="CuadernoDePrueba",
            transporte=transporte(
                lambda peticion: httpx.Response(
                    200, json={"resultado": {"codigoResultado": "OK"}}
                )
            ),
        )
        assert resultado.respuesta.esta_ok is True
        assert "establecida" in resultado.mensaje.lower()

    def test_si_se_cae_la_conexion_lo_dice_y_no_revienta(self, monkeypatch, tmp_path):
        certificado = tmp_path / "cert.pem"
        clave = tmp_path / "clave.pem"
        certificado.write_text(CERTIFICADO_DE_MENTIRA, encoding="utf-8")
        clave.write_text("clave", encoding="utf-8")
        monkeypatch.setenv("CUEDIGITAL_IUWS_CERTIFICADO", str(certificado))
        monkeypatch.setenv("CUEDIGITAL_IUWS_CLAVE", str(clave))

        def manejador(peticion):
            raise httpx.ConnectError("cortado")

        resultado = iuws_cliente.pedir_token(
            "https://ejemplo.es", nombre_app="CuadernoDePrueba", transporte=transporte(manejador)
        )
        assert resultado.hecha is True
        assert "comunicación" in resultado.mensaje.lower()


# --------------------------------------------------------------------------
# Seguir una carga
# --------------------------------------------------------------------------


class TestComprobarElEstado:
    def test_sin_token_no_llama(self):
        resultado = iuws_cliente.comprobar_estado(7, token="", base="https://ejemplo.es")
        assert resultado.hecha is False
        assert resultado.url == "https://ejemplo.es/IUWS/api/comprobarEstado/7"

    def test_pregunta_por_el_numero_de_peticion(self):
        def manejador(peticion):
            assert str(peticion.url) == "https://ejemplo.es/IUWS/api/comprobarEstado/7"
            assert peticion.headers["Authorization"] == "eyJhbGciOi"
            return httpx.Response(
                200,
                json={
                    "resultado": {
                        "codigoResultado": "OK",
                        "detalleOperacion": {"estado": "PROCESADO"},
                    }
                },
            )

        resultado = iuws_cliente.comprobar_estado(7, token="eyJhbGciOi", base="https://ejemplo.es", transporte=transporte(manejador))
        assert resultado.respuesta.operacion == {"estado": "PROCESADO"}

    def test_una_carga_a_medias_dice_que_actividades_han_fallado(self):
        resultado = iuws_cliente.comprobar_estado(
            7,
            token="t",
            base="https://ejemplo.es",
            transporte=transporte(
                lambda peticion: httpx.Response(
                    200,
                    json={
                        "resultado": {
                            "codigoResultado": "PARCIAL",
                            "detalleImportacion": [
                                {"codigo": 3, "descripcion": "ok"},
                                {"codigo": 6, "descripcion": "mal"},
                            ],
                        }
                    },
                )
            ),
        )
        fallidas = resultado.respuesta.actividades_fallidas()
        assert len(fallidas) == 1
        assert fallidas[0]["explicacion"]


# --------------------------------------------------------------------------
# Mandar el cuaderno: lo que todavía no se puede
# --------------------------------------------------------------------------


class TestEnviarElCuaderno:
    def test_un_paquete_que_no_es_el_del_descriptor_no_se_manda(self):
        """Mandar algo que se sabe que va a rebotar no ayuda a nadie, y encima molesta."""

        def manejador(peticion):  # pragma: no cover — no debería llamarse nunca
            raise AssertionError("no se debería haber llamado al interfaz")

        resultado = iuws_cliente.enviar_cuaderno(
            {"formato": "sobre-documentado-con-contenido-minimo-siex", "CUADERNO": []},
            token="t",
            base="https://ejemplo.es",
            transporte=transporte(manejador),
        )
        assert resultado.hecha is False
        assert "descriptor" in resultado.mensaje.lower()

    def test_el_paquete_que_hace_esta_aplicacion_dice_que_no_es_el_bueno(self):
        """El paquete real que arma la aplicación tiene que ser rechazado aquí, no en la Junta."""
        assert iuws.FORMATO_DESCRIPTOR == "descriptor-v3.11.4"
        assert "sobre-documentado" not in iuws.FORMATO_DESCRIPTOR

    def test_con_el_formato_bueno_se_manda_y_se_lee_el_numero_de_peticion(self):
        visto = {}

        def manejador(peticion):
            visto["cuerpo"] = json.loads(peticion.content.decode("utf-8"))
            visto["content_type"] = peticion.headers["Content-Type"]
            visto["authorization"] = peticion.headers["Authorization"]
            return httpx.Response(
                200,
                json={"resultado": {"codigoResultado": "OK", "detalleImportacion": [{"codigo": 42}]}},
            )

        paquete = {
            "formato": iuws.FORMATO_DESCRIPTOR,
            "CUADERNO": [{
                "CAExplotacion": "13",
                "IdTitular": "70922320A",
                "CodigoRea": "ES130000008847",
                "UnidadGestora": "B12345678",
            }],
        }
        resultado = iuws_cliente.enviar_cuaderno(
            paquete, token="eyJhbGciOi", base="https://ejemplo.es", transporte=transporte(manejador)
        )
        assert resultado.codigo == 200
        assert resultado.respuesta.id_peticion == 42
        assert visto["cuerpo"] == {"CUADERNO": paquete["CUADERNO"]}
        assert "charset=utf-8" in visto["content_type"]
        assert visto["authorization"] == "eyJhbGciOi"
        assert "42" in resultado.mensaje

    def test_sin_token_no_se_manda(self):
        resultado = iuws_cliente.enviar_cuaderno(
            {"formato": iuws.FORMATO_DESCRIPTOR, "CUADERNO": [{
                "CAExplotacion": "13", "IdTitular": "70922320A",
                "CodigoRea": "ES130000008847", "UnidadGestora": "B12345678",
            }]},
            token="",
            base="https://ejemplo.es",
        )
        assert resultado.hecha is False

    def test_lo_que_se_manda_no_pierde_los_acentos(self):
        """El cuaderno va en español: si se estropeara la codificación, la Junta leería basura."""
        visto = {}

        def manejador(peticion):
            visto["crudo"] = peticion.content
            return httpx.Response(200, json={"resultado": {"codigoResultado": "OK"}})

        iuws_cliente.enviar_cuaderno(
            {"formato": iuws.FORMATO_DESCRIPTOR, "CUADERNO": [{
                "CAExplotacion": "13", "IdTitular": "Peña",
                "CodigoRea": "ES130000008847", "UnidadGestora": "B12345678",
            }]},
            token="t",
            base="https://ejemplo.es",
            transporte=transporte(manejador),
        )
        assert "Peña".encode("utf-8") in visto["crudo"]

    def test_el_esquema_oficial_rechaza_un_campo_obligatorio_ausente(self):
        def manejador(_peticion):
            raise AssertionError("No se debe llamar al IUWS con un cuaderno incompleto")

        resultado = iuws_cliente.enviar_cuaderno(
            {"formato": iuws.FORMATO_DESCRIPTOR, "CUADERNO": [{"CAExplotacion": "13"}]},
            token="t", base="https://ejemplo.es", transporte=transporte(manejador),
        )
        assert resultado.hecha is False
        assert "esquema oficial" in resultado.mensaje

    def test_el_sobre_que_hace_la_aplicacion_cumple_el_esquema_oficial(self):
        """El sobre exterior ya valida contra el esquema oficial, y esto lo demuestra.

        Se cambió `IDTitular` por `IdTitular` justo por esto: el esquema declara `IdTitular`
        como obligatorio, así que con el nombre del ejemplo del anexo el sobre no validaba
        nunca y el fallo no se veía hasta el final del camino.

        Ojo con la longitud: el esquema exige **exactamente 14 caracteres** en `CodigoSIEX` y
        en `CodigoRea`, que es lo que mide un código de REA (`ES130000008847`). No es un
        capricho del test: es una restricción del descriptor oficial.
        """
        sobre = iuws.sobre_del_cuaderno(
            codigo_siex="ES130000008847",
            ca="13",
            nif_titular="70922320A",
            unidad_gestora="B12345678",
            codigo_rea="ES130000008847",
            id_cuaderno=2026,
        )
        assert iuws_cliente.errores_del_esquema({"CUADERNO": [sobre]}) == []

    def test_al_sobre_sin_codigo_rea_el_esquema_le_falta_justo_ese_campo(self):
        """Y cuando falta algo, se sabe **qué** falta: eso es lo que puede leer una persona."""
        sobre = iuws.sobre_del_cuaderno(codigo_siex=None, ca="13", nif_titular="70922320A")
        fallos = iuws_cliente.errores_del_esquema({"CUADERNO": [sobre]})
        assert fallos, "sin CodigoRea el esquema tiene que quejarse"
        assert any("CodigoRea" in fallo for fallo in fallos), fallos

    def test_un_codigo_de_rea_corto_se_ve_antes_de_mandarlo(self):
        """Un código que no mida 14 no vale, y se sabe aquí y no en la Junta."""
        sobre = iuws.sobre_del_cuaderno(
            codigo_siex="933", ca="13", nif_titular="70922320A",
            unidad_gestora="B12345678", codigo_rea="ES130000008847",
        )
        fallos = iuws_cliente.errores_del_esquema({"CUADERNO": [sobre]})
        assert any("CodigoSIEX" in fallo for fallo in fallos), fallos

    def test_el_identificador_de_cuaderno_tiene_que_ser_un_numero(self):
        """El esquema lo declara `integer`: mandarlo como texto no vale.

        Lo encontró el esquema, no una llamada: la aplicación lo pasaba como cadena porque en
        el ejemplo del anexo aparece entre comillas. Es el mismo tipo de fallo que
        `IDTitular`: el ejemplo del anexo no es el contrato.
        """
        base = dict(
            codigo_siex="ES130000008847", ca="13", nif_titular="70922320A",
            unidad_gestora="B12345678", codigo_rea="ES130000008847",
        )
        assert iuws_cliente.errores_del_esquema(
            {"CUADERNO": [iuws.sobre_del_cuaderno(id_cuaderno=2026, **base)]}
        ) == []
        fallos = iuws_cliente.errores_del_esquema(
            {"CUADERNO": [iuws.sobre_del_cuaderno(id_cuaderno="2026", **base)]}
        )
        assert any("IdCuaderno" in fallo for fallo in fallos), fallos


# --------------------------------------------------------------------------
# Que la lista de lo comprobado y las direcciones del programa digan lo mismo
# --------------------------------------------------------------------------


class TestLaListaDeLoComprobado:
    def test_solo_se_apunta_como_comprobado_lo_llamado_de_verdad(self):
        """La lista crece **solo** cuando hay una llamada de verdad detrás, y con su fecha.

        Se actualiza el 27/09/2026 con motivo: ese día se llamó al interfaz con
        `scripts/probar_iuws.py` y se apuntó lo que contestó la llamada del token sin certificado
        (el entorno de integración contesta «No Autorizado», y producción corta el saludo TLS). La
        lista deja de tener una sola entrada porque ahora hay **dos** llamadas comprobadas, no
        porque se hayan dado por buenas dos rutas de un documento.
        """
        assert set(iuws.COMPROBADO_CONTRA_EL_INTERFAZ) == {
            "/IUWS/api/version",
            "/IUWS/api/comunicacion/{app}",
        }
        assert iuws.COMPROBADO_EL, "lo comprobado se apunta con su fecha"
        assert iuws.RESPUESTAS_OBSERVADAS["produccion_castilla_y_leon"]["version"].startswith("200")

    def test_la_direccion_de_version_es_la_comprobada(self):
        base = "https://ejemplo.es"
        assert iuws.url_version(base).replace(base, "") in iuws.COMPROBADO_CONTRA_EL_INTERFAZ

    def test_el_de_la_version_dice_que_contesta_200(self):
        assert "200" in iuws.COMPROBADO_CONTRA_EL_INTERFAZ["/IUWS/api/version"]

    def test_ninguno_dice_404(self):
        """Un 404 habría significado que la dirección está mal. Ninguno lo dio."""
        for que in iuws.COMPROBADO_CONTRA_EL_INTERFAZ.values():
            assert "404" not in que

class TestElMotivoDeLoQueFalta:
    def test_devuelve_el_motivo_redactado(self):
        """El motivo del descriptor ya no dice «falta el fichero»: el fichero está.

        Se actualiza el test porque cambió el mundo, no porque estorbara: el descriptor CUE
        v3.11.4 se extrajo del Anexo VI oficial el 22/09/2026 y está en `data/iuws_fuentes/`.
        Lo que falta ahora es **mapearlo** y tener los **códigos** de los catálogos.
        """
        texto = iuws.por_que_falta("descriptor")
        assert "mapeo" in texto
        assert "iuws_fuentes" in texto

    def test_dice_a_quien_se_le_pide(self):
        for clave in ("nombre_comercial", "dominio", "certificado", "codigo_siex"):
            assert "pide" in iuws.por_que_falta(clave) or "pedir" in iuws.por_que_falta(clave)

    def test_una_clave_que_no_existe_devuelve_vacio(self):
        """Vacío y no una frase inventada: quien llame tiene que poder notar que no existe."""
        assert iuws.por_que_falta("inventada") == ""

    def test_todas_las_claves_de_la_lista_tienen_motivo(self):
        for falta in iuws.QUE_FALTA:
            assert iuws.por_que_falta(falta.clave)


# --------------------------------------------------------------------------
# Por la api: sin salir a internet
# --------------------------------------------------------------------------


class TestLaPruebaPorLaApi:
    def test_sin_pedirlo_no_llama_al_interfaz(self, cliente, cuenta, monkeypatch):
        """Pinchar al servidor de la Junta cada vez que se abre una pantalla es molestar."""
        monkeypatch.delenv("CUEDIGITAL_IUWS_APP", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CERTIFICADO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_IUWS_CLAVE", raising=False)

        def no_llamar(*args, **kwargs):  # pragma: no cover — no debería llamarse
            raise AssertionError("no se debería haber llamado al interfaz")

        monkeypatch.setattr(iuws_cliente, "comprobar_version", no_llamar)
        datos = cliente.get("/api/iuws/version", headers=cuenta["cabeceras"]).json()
        assert datos["probado"] is False
        assert datos["conectado"] is False
        # Pero se dice que ESTA prueba sí se puede hacer ya, y qué contestó cuando se comprobó.
        assert datos["se_puede_probar_ya"] is True
        assert datos["version_observada"] == iuws.VERSION_OBSERVADA
        assert datos["url"].endswith("/IUWS/api/version")
        assert datos["faltan"]

    def test_pidiendolo_llama_y_cuenta_lo_que_le_han_dicho(self, cliente, cuenta, monkeypatch):
        monkeypatch.setattr(
            iuws_cliente,
            "comprobar_donde_contesta",
            lambda base_configurada=None, transporte=None: {
                "probadas": [
                    {
                        "base": "https://sga.entornointegracion.es",
                        "url": "https://sga.entornointegracion.es/IUWS/api/version",
                        "codigo": 404,
                        "version": "",
                        "mensaje": "",
                    },
                    {
                        "base": "https://servicios.ayg.jcyl.es",
                        "url": "https://servicios.ayg.jcyl.es/IUWS/api/version",
                        "codigo": 200,
                        "version": "3.11.4",
                        "mensaje": "",
                    },
                ],
                "buena": {
                    "base": "https://servicios.ayg.jcyl.es",
                    "url": "https://servicios.ayg.jcyl.es/IUWS/api/version",
                    "codigo": 200,
                    "version": "3.11.4",
                    "mensaje": "",
                },
                "mensaje": "Hay camino hasta la Junta, pero no por la dirección que tienes puesta.",
            },
        )
        datos = cliente.get("/api/iuws/version?llamar=1", headers=cuenta["cabeceras"]).json()
        assert datos["probado"] is True
        assert datos["conectado"] is True
        assert datos["codigo"] == 200
        assert datos["donde_contesta"] == "https://servicios.ayg.jcyl.es"
        assert [p["codigo"] for p in datos["probadas"]] == [404, 200]
        assert datos["respuesta"] == '{"version": "3.11.4"}'
        assert "ojo_con_la_direccion_por_defecto" in datos

    def test_sin_pedirlo_dice_las_direcciones_que_se_pueden_probar(self, cliente, cuenta, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_IUWS_APP", raising=False)
        datos = cliente.get("/api/iuws/version", headers=cuenta["cabeceras"]).json()
        assert datos["direcciones_conocidas"]["por_comunidad"]["Castilla y León"] == (
            "https://servicios.ayg.jcyl.es"
        )

    def test_la_lista_de_lo_comprobado_se_sirve_entera(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/comprobar-de-verdad", headers=cuenta["cabeceras"]).json()
        # Dos métodos comprobados desde el 27/09/2026: la versión (que contesta 200) y la llamada
        # del token sin certificado (que es la que dice dónde se corta). Se sirven los dos.
        assert len(datos["metodos"]) == 2
        assert len(datos["en_el_entorno_de_integracion"]) == 2
        assert datos["version_observada"] == iuws.VERSION_OBSERVADA
        assert "401" in datos["que_significa_un_401"]
        assert datos["por_que_no_se_prueba_lo_demas"]
        assert "404" in datos["donde"]["ojo"]

    def test_el_estado_lleva_lo_que_se_comprobo(self, cliente, cuenta):
        datos = cliente.get("/api/iuws/estado", headers=cuenta["cabeceras"]).json()
        assert datos["version_observada"] == iuws.VERSION_OBSERVADA
        assert datos["fecha_de_la_comprobacion"]
        assert len(datos["comprobado_contra_el_interfaz"]) == 2


class TestElResultado:
    def test_un_resultado_sin_hacer_dice_que_no_se_hizo(self):
        resultado = iuws_cliente.Resultado(hecha=False, mensaje="falta algo")
        assert resultado.hecha is False
        assert resultado.codigo is None


@pytest.mark.parametrize(
    "linea",
    [
        "-----BEGIN CERTIFICATE-----",
        "-----END CERTIFICATE-----",
    ],
)
def test_las_lineas_de_cabecera_se_van(linea):
    assert linea.strip() not in iuws_cliente.cabecera_certificado(CERTIFICADO_DE_MENTIRA)
