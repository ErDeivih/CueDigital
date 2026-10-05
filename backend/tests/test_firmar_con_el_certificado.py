"""Firmar `data-signed` con el certificado del almacén de Windows.

Para presentar el cuaderno hay que mandar el NIF **firmado con la clave privada** del certificado de
dominio. La de David está en el almacén de Windows y **no es exportable**, así que no se puede leer
desde Python: se firma **donde vive**, con `scripts/firmar_con_el_certificado.ps1`, y aquí solo llega
la firma.

Lo que se comprueba aquí:

  · que el script **no pueda hacer daño**: no exporta la clave ni el certificado, no escribe
    ficheros, no toca la red y no lleva ningún secreto dentro;
  · que firme como hay que firmar (RSA, PKCS#1 v1.5, SHA-256) y que traiga su modo de comprobación;
  · que el programa lo use bien desde Python (los argumentos, el base64 y los casos en los que
    **no** se puede firmar).

**Y lo que no se hace en ningún caso:** llamar al script de verdad. Eso firmaría con la clave privada
de David, y una prueba no toca el certificado de nadie. Se comprobó a mano el 27/09/2026: la firma
salió y **se verificó** con la clave pública del certificado.
"""

from __future__ import annotations

import base64
import pathlib
import re

import pytest

from app import iuws_cliente

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "backend" / "scripts" / "firmar_con_el_certificado.ps1"
GUIA = RAIZ / "docs" / "INTEGRACION_IUWS.md"


def _codigo() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _sin_comentarios() -> str:
    """El script sin el bloque de comentarios: para mirar lo que **hace**, no lo que cuenta.

    Hace falta de verdad: el aviso del principio **dice** que no exporta la clave, y buscando sobre
    el texto entero el propio aviso haría fallar la comprobación.
    """
    texto = re.sub(r"<#.*?#>", "", _codigo(), flags=re.S)
    return "\n".join(
        linea for linea in texto.splitlines() if not linea.lstrip().startswith("#")
    )


class TestElScriptNoPuedeHacerDano:
    def test_el_script_esta_y_explica_por_que_existe(self):
        assert SCRIPT.exists(), "falta el script que firma con el certificado de Windows"
        codigo = _codigo()
        assert "POR QUÉ EXISTE" in codigo
        assert "no es exportable" in codigo, (
            "el script no dice que la clave no es exportable, que es la razón de que exista"
        )

    def test_no_exporta_la_clave_ni_el_certificado(self):
        codigo = _sin_comentarios()
        for prohibido in (
            "Export-PfxCertificate",
            "Export-Certificate",
            "Export-Clixml",
            "Set-Content",
            "Out-File",
            "pfx",
        ):
            assert prohibido not in codigo, f"el script podría estar escribiendo la clave: {prohibido}"

    def test_no_toca_la_red(self):
        """Firmar es local: el script no llama a la Junta ni a ningún sitio."""
        codigo = _sin_comentarios()
        for prohibido in ("HttpWebRequest", "WebClient", "Invoke-WebRequest", "Invoke-RestMethod", "http"):
            assert prohibido not in codigo, f"el script sale a la red: {prohibido}"

    def test_no_lleva_ningun_secreto_dentro(self):
        codigo = _codigo()
        for prohibido in ("BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY", "BEGIN CERTIFICATE", "MII"):
            assert prohibido not in codigo, f"el script lleva algo que parece un secreto: {prohibido}"
        # Y ningún dato personal escrito: el certificado se busca por variable de entorno.
        assert "$env:CUEDIGITAL_CERTIFICADO" in codigo
        assert "70922320A" not in codigo, "el script lleva el NIF escrito dentro"

    def test_firma_como_hay_que_firmar(self):
        """RSA con PKCS#1 v1.5 y SHA-256: lo mismo que haría cualquier cliente del interfaz."""
        codigo = _sin_comentarios()
        assert "SHA256" in codigo, "no dice con qué resumen firma"
        assert "Pkcs1" in codigo, "no dice con qué relleno firma"
        assert "SignData" in codigo, "no firma: hace otra cosa"

    def test_trae_su_modo_de_comprobacion(self):
        """`-Comprobar` firma y comprueba la firma con la clave pública. Es la prueba de que va."""
        codigo = _sin_comentarios()
        assert "-Comprobar" in codigo or "[switch]$Comprobar" in codigo
        assert "VerifyData" in codigo, "no comprueba la firma que acaba de hacer"

    def test_la_documentacion_lo_cuenta(self):
        guia = GUIA.read_text(encoding="utf-8")
        assert "firmar_con_el_certificado.ps1" in guia, (
            "la guía del IUWS no cuenta que existe el firmador de Windows"
        )


class TestElProgramaUsaEseFirmador:
    def test_sin_windows_no_se_puede_firmar_asi(self, monkeypatch):
        monkeypatch.setattr(iuws_cliente.os, "name", "posix")
        assert iuws_cliente.firmador_con_el_certificado_de_windows() is None

    def test_sin_el_script_no_se_puede_firmar_asi(self, monkeypatch):
        monkeypatch.setattr(iuws_cliente.os, "name", "nt")
        monkeypatch.setattr(iuws_cliente, "FIRMADOR_DE_WINDOWS", pathlib.Path("no-existe.ps1"))
        assert iuws_cliente.firmador_con_el_certificado_de_windows() is None

    def test_sin_certificado_configurado_no_se_puede_firmar_asi(self, monkeypatch):
        monkeypatch.setattr(iuws_cliente.os, "name", "nt")
        monkeypatch.delenv("CUEDIGITAL_CERTIFICADO", raising=False)
        assert iuws_cliente.firmador_con_el_certificado_de_windows() is None

    def test_llama_al_script_con_el_texto_y_devuelve_la_firma(self, monkeypatch):
        """Los argumentos importan: el texto va tal cual y la firma vuelve en base64."""
        monkeypatch.setattr(iuws_cliente.os, "name", "nt")
        monkeypatch.setenv("CUEDIGITAL_CERTIFICADO", "12345678Z")
        visto = {}

        def falso_run(orden, **resto):
            visto["orden"] = orden
            visto["resto"] = resto

            class Salida:
                returncode = 0
                stdout = base64.b64encode(b"firma-de-verdad").decode("ascii") + "\n"
                stderr = ""

            return Salida()

        monkeypatch.setattr(iuws_cliente.subprocess, "run", falso_run)

        firmar = iuws_cliente.firmador_con_el_certificado_de_windows()
        assert firmar is not None, "con Windows, el script y el certificado, tiene que poder firmar"
        firma = firmar(b"12345678Z")
        assert firma == b"firma-de-verdad"
        assert str(SCRIPT) in visto["orden"], "no llama al script del proyecto"
        assert "12345678Z" in visto["orden"], "no le pasa el texto que hay que firmar"
        assert visto["resto"].get("capture_output") is True, "no recoge lo que contesta el script"

    def test_si_el_script_falla_se_dice_que_no_se_pudo(self, monkeypatch):
        monkeypatch.setattr(iuws_cliente.os, "name", "nt")
        monkeypatch.setenv("CUEDIGITAL_CERTIFICADO", "12345678Z")

        class Salida:
            returncode = 2
            stdout = ""
            stderr = "No hay ningún certificado con «12345678Z»"

        monkeypatch.setattr(iuws_cliente.subprocess, "run", lambda *a, **k: Salida())

        firmar = iuws_cliente.firmador_con_el_certificado_de_windows()
        with pytest.raises(OSError) as fallo:
            firmar(b"12345678Z")
        assert "certificado" in str(fallo.value)

    def test_datos_firmados_usa_el_firmador_de_windows(self, monkeypatch):
        """El camino completo: el programa pide firmar y sale la firma en base64."""
        monkeypatch.setattr(
            iuws_cliente,
            "firmador_con_el_certificado_de_windows",
            lambda: (lambda datos: b"firma-de-windows"),
        )
        datos = iuws_cliente.datos_firmados("12345678Z")
        assert datos == base64.b64encode(b"firma-de-windows").decode("ascii")

    def test_si_el_firmador_de_windows_falla_no_devuelve_una_firma_inventada(self, monkeypatch):
        def revienta(datos):
            raise OSError("no se pudo firmar")

        monkeypatch.setattr(iuws_cliente, "firmador_con_el_certificado_de_windows", lambda: revienta)
        assert iuws_cliente.datos_firmados("12345678Z") is None

    def test_ya_no_se_pide_exportar_la_clave(self):
        """Lo que decía antes era pedir justo lo que no se debe hacer con una clave de verdad."""
        texto = iuws_cliente.falta_para_firmar()
        assert "almacén de Windows" in texto
        assert "no sale de ahí" in texto
        # Sigue diciendo las dos variables, porque en otro ordenador hacen falta.
        assert "CUEDIGITAL_CERTIFICADO" in texto
        assert "CUEDIGITAL_IUWS_CLAVE" in texto
