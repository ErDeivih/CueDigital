"""El script que llama al interfaz de la Junta con el certificado del almacén de Windows.

Existe por un motivo que ya está medido: la clave privada del certificado de David **no es
exportable**, así que no se puede usar desde Python (que va con OpenSSL), pero **sí desde Windows**,
que firma el saludo TLS por dentro. Ese script es la única forma de comprobar qué contesta el
interfaz sin pedirle a nadie que exporte su clave.

Lo que se comprueba aquí **no es que funcione** (eso se hizo a mano, contra el interfaz de verdad, y
toca la red: los tests no tocan la red): se comprueba que **el script no puede hacer daño**. Es
decir:

  · que no lleve ningún secreto dentro (ni claves, ni certificados, ni contraseñas);
  · que **no exporte** el certificado ni la clave a ningún sitio;
  · que el certificado se identifique por parámetro o por variable de entorno, nunca escrito aquí;
  · que **solo haga llamadas de lectura** (nada de `crear` ni de `exportar`, que son los métodos que
    escriben en la Junta);
  · y que la documentación lo cuente, para que el siguiente sepa que existe.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "backend" / "scripts" / "probar_iuws_con_certificado.ps1"
GUIA = RAIZ / "docs" / "INTEGRACION_IUWS.md"


def _codigo() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _sin_comentarios() -> str:
    """El script sin sus comentarios: para buscarse cosas que **hacen**, no que se cuentan.

    Hace falta de verdad: el bloque de comentarios del script **dice** que no exporta la clave ni
    llama a `crear`, y si se buscara sobre el texto entero, el propio aviso haría fallar la
    comprobación. (Pasó al escribir estas pruebas: salían tres fallos que eran del texto, no del
    código.)
    """
    texto = re.sub(r"<#.*?#>", "", _codigo(), flags=re.S)
    lineas = [linea for linea in texto.splitlines() if not linea.lstrip().startswith("#")]
    return "\n".join(lineas)


class TestElScriptExisteYSeCuenta:
    def test_el_script_esta_y_se_puede_leer(self):
        assert SCRIPT.exists(), "falta el script que llama al interfaz con el certificado de Windows"
        codigo = _codigo()
        assert "POR QUÉ EXISTE" in codigo, "el script no explica por qué existe"
        assert "no exportable" in codigo, (
            "el script no dice que la clave no es exportable, que es la razón de que él exista"
        )

    def test_la_documentacion_lo_nombra(self):
        guia = GUIA.read_text(encoding="utf-8")
        assert "probar_iuws_con_certificado.ps1" in guia, (
            "la guía del IUWS no cuenta que existe este script"
        )
        # Y cuenta lo que contestó de verdad, que es la razón de haberlo escrito.
        assert "Dominio del certificado no registrado en el sistema" in guia, (
            "la guía no recoge lo que contestó el interfaz con el certificado puesto"
        )


class TestElScriptNoPuedeHacerDano:
    def test_no_lleva_ningun_secreto_dentro(self):
        codigo = _codigo()
        for prohibido in (
            "BEGIN PRIVATE KEY",
            "BEGIN RSA PRIVATE KEY",
            "BEGIN CERTIFICATE",
            "MII",
            "password",
            "contraseña",
            "PfxPassword",
        ):
            assert prohibido not in codigo, f"el script lleva algo que parece un secreto: {prohibido}"

    def test_no_exporta_el_certificado_ni_la_clave(self):
        """Lo que no se debe hacer nunca: sacar la clave del almacén a un fichero."""
        codigo = _sin_comentarios()
        for prohibido in (
            "Export-PfxCertificate",
            "Export-Certificate",
            "Export-Clixml",
            "Set-Content",
            "Out-File",
            "pfx",
        ):
            assert prohibido not in codigo, f"el script podría estar escribiendo el certificado: {prohibido}"

    def test_el_certificado_se_identifica_desde_fuera(self):
        """Ni el NIF ni la huella de nadie se escriben en el repositorio."""
        codigo = _sin_comentarios()
        assert "$env:CUEDIGITAL_CERTIFICADO" in codigo, (
            "el script no lee el certificado de una variable de entorno"
        )
        # El NIF de David no puede estar escrito en el código (sí en la documentación, que cuenta lo
        # que se comprobó: eso es la memoria del proyecto, no un dato que el script necesite).
        assert "70922320A" not in codigo, "el script lleva el NIF escrito dentro"

    def test_solo_hace_llamadas_de_lectura(self):
        """`crear` y `exportar` son los métodos que escriben en la Junta: aquí, ni de broma."""
        codigo = _sin_comentarios()
        assert '"GET"' in codigo, "el script no dice que va con GET"
        for metodo in ("POST", "PUT", "DELETE"):
            assert f'"{metodo}"' not in codigo, f"el script hace una llamada de escritura: {metodo}"
        for ruta in ("crear", "exportar"):
            assert ruta not in codigo, f"el script llama a un método que escribe en la Junta: {ruta}"

    def test_no_manda_datos_del_agricultor(self):
        codigo = _sin_comentarios()
        # Nada de cuerpo en las peticiones: solo se pide, no se cuenta nada.
        assert "GetRequestStream" not in codigo, "el script manda un cuerpo en la petición"
        assert re.search(r"\.Method\s*=\s*\"GET\"", codigo), "el método de la petición no es GET"
