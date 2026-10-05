"""Certificado digital: quien entra, y cómo se sabe.

Esto es la puerta. IUWS (la Interfaz Único de Web Services de FEGA, por donde se entrega
el cuaderno a la Junta) exige **certificado de persona jurídica y JWT**, con ENS nivel
medio. Y para que el agricultor pueda entrar sin teclear nada, el certificado es también
la mejor forma de identificarse: él ya lo tiene, se lo dio la FNMT, y es lo que usa para
hablar con la administración.

**Cómo llega el certificado al programa.** El programa NO valida el certificado: eso lo
hace el servidor web que tiene delante (nginx, con `ssl_verify_client on`), que además
le pasa el resultado. Lo que se hace aquí es leer lo que el servidor web ya ha validado.

Decisión de seguridad que no se puede tocar: **las cabeceras no se creen por defecto.**
Si el programa estuviera expuesto directamente, cualquiera podría mandar
`X-SSL-Client-Subject: CN=...` y entrar como otro. Por eso hay que encender
`CUEDIGITAL_CONFIAR_EN_CABECERAS=1` a mano, y solo cuando haya un servidor web delante
que las ponga. Hay un test que comprueba que con esto apagado **no se entra**.

Lo que NO se hace aquí, y conviene tenerlo escrito: no se valida la cadena de confianza
ni se comprueba que el certificado no esté revocado. Eso es del servidor web. Aquí solo
se lee el nombre, se saca el NIF y se comprueba que sea un NIF con sentido.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from fastapi import Request

# --------------------------------------------------------------------------
# NIF: DNI, NIE y CIF
# --------------------------------------------------------------------------

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
LETRAS_CIF = "JABCDEFGHI"

# Qué tipo de organización es cada letra inicial de un CIF. Se usa solo para saber cómo
# se calcula el dígito de control, que cambia según el tipo.
TIPOS_CIF = {
    "A": "sociedad anónima",
    "B": "sociedad limitada",
    "C": "sociedad colectiva",
    "D": "sociedad comanditaria",
    "E": "comunidad de bienes",
    "F": "sociedad cooperativa",
    "G": "asociación",
    "H": "comunidad de propietarios",
    "J": "sociedad civil",
    "K": "formato antiguo",
    "L": "formato antiguo",
    "M": "formato antiguo",
    "N": "entidad extranjera",
    "P": "corporación local",
    "Q": "organismo público",
    "R": "congregación religiosa",
    "S": "órgano de la administración",
    "U": "unión temporal de empresas",
    "V": "sociedad agraria de transformación",
    "W": "establecimiento permanente",
}

# El tipo de organización decide si el dígito de control va en cifra o en letra. No es
# lo mismo en todas: las sociedades anónimas y limitadas lo llevan en cifra obliga-
# toriamente, y los organismos públicos en letra. Aceptar las dos formas en todos los
# casos dejaría pasar NIF mal escritos.
CIF_DIGITO_OBLIGATORIO = set("ABEH")
CIF_LETRA_OBLIGATORIA = set("KLMNPQSW")


def normaliza_nif(nif: str | None) -> str:
    """Deja el NIF en su forma canónica: sin espacios, sin guiones y en mayúsculas."""
    if not nif:
        return ""
    limpio = re.sub(r"[\s\-.]", "", str(nif)).upper()
    # Algunos certificados llevan el NIF con prefijo de país: "ES70922320A".
    if limpio.startswith("ES") and len(limpio) > 2:
        limpio = limpio[2:]
    # Y las empresas llevan a veces "VATES-" delante.
    limpio = re.sub(r"^(VATES|VAT|IDCES)[-:]?", "", limpio)
    return limpio


def tipo_de_nif(nif: str) -> str | None:
    """Devuelve 'dni', 'nie', 'cif' o None si no tiene forma de NIF español."""
    limpio = normaliza_nif(nif)
    if re.fullmatch(r"\d{8}[A-Z]", limpio):
        return "dni"
    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", limpio):
        return "nie"
    if re.fullmatch(r"[A-Z]\d{7}[0-9A-Z]", limpio):
        return "cif"
    return None


def nif_valido(nif: str | None) -> bool:
    """¿Tiene este NIF la letra o el dígito de control correctos?

    Sirve para dos cosas. La primera, avisar de una errata al teclear el NIF de la
    finca, que es un dato que luego va en todos los papeles. La segunda, no fiarse de un
    certificado que traiga un NIF sin sentido.

    Estos algoritmos son públicos y están fijados por el Ministerio. Están aquí escritos
    a mano, y con tests con NIF reales inventados, para no depender de ninguna librería
    para una cuenta de diez líneas.
    """
    limpio = normaliza_nif(nif)
    tipo = tipo_de_nif(limpio)
    if tipo is None:
        return False

    if tipo == "dni":
        return limpio[8] == LETRAS_DNI[int(limpio[:8]) % 23]

    if tipo == "nie":
        equivalencias = {"X": "0", "Y": "1", "Z": "2"}
        numero = int(equivalencias[limpio[0]] + limpio[1:8])
        return limpio[8] == LETRAS_DNI[numero % 23]

    # CIF: se suman las cifras de las posiciones pares y los dígitos de las impares
    # multiplicadas por dos (si sale de una cifra, se suman sus dígitos).
    letra, digitos, control = limpio[0], limpio[1:8], limpio[8]
    suma = 0
    for posicion, caracter in enumerate(digitos):
        cifra = int(caracter)
        # Las posiciones impares (1ª, 3ª, 5ª y 7ª) se doblan; si el doble pasa de
        # nueve, se le restan nueve (que es lo mismo que sumar sus dos cifras).
        if posicion % 2 == 0:
            doble = cifra * 2
            suma += doble if doble < 10 else doble - 9
        else:
            suma += cifra
    resultado = (10 - (suma % 10)) % 10

    if letra in CIF_DIGITO_OBLIGATORIO:
        return control == str(resultado)
    if letra in CIF_LETRA_OBLIGATORIA:
        return control == LETRAS_CIF[resultado]
    # Los demás tipos admiten las dos formas.
    return control == str(resultado) or control == LETRAS_CIF[resultado]


# --------------------------------------------------------------------------
# El nombre distinguido (DN) del certificado
# --------------------------------------------------------------------------

# Los OID que pueden venir en vez del nombre corto, según cómo lo escriba el servidor
# web. nginx manda "SERIALNUMBER=..." pero otros mandan "OID.2.5.4.5=...".
EQUIVALENCIAS_DE_CLAVE = {
    "OID.2.5.4.3": "CN",
    "OID.2.5.4.4": "SN",
    "OID.2.5.4.5": "SERIALNUMBER",
    "OID.2.5.4.10": "O",
    "OID.2.5.4.11": "OU",
    "OID.2.5.4.42": "G",
    "OID.2.5.4.97": "ORGANIZATIONIDENTIFIER",
    "2.5.4.3": "CN",
    "2.5.4.4": "SN",
    "2.5.4.5": "SERIALNUMBER",
    "2.5.4.10": "O",
    "2.5.4.11": "OU",
    "2.5.4.42": "G",
    "2.5.4.97": "ORGANIZATIONIDENTIFIER",
}


def _separa_campos(dn: str) -> list[str]:
    """Parte un DN por las comas QUE NO ESTÁN ESCAPADAS.

    Hace falta de verdad: hay apellidos y razones sociales con coma dentro
    ("PEREZ VELASCO, DAVID" va escapado como "PEREZ VELASCO\\, DAVID"). Partir por todas
    las comas destrozaría el nombre y el NIF.
    """
    campos: list[str] = []
    actual: list[str] = []
    escapado = False
    entrecomillado = False
    for caracter in dn:
        if escapado:
            actual.append(caracter)
            escapado = False
            continue
        if caracter == "\\":
            actual.append(caracter)
            escapado = True
            continue
        if caracter == '"':
            entrecomillado = not entrecomillado
        if caracter == "," and not entrecomillado:
            campos.append("".join(actual))
            actual = []
            continue
        actual.append(caracter)
    campos.append("".join(actual))
    return [campo.strip() for campo in campos if campo.strip()]


def parsea_dn(dn: str | None) -> dict[str, str]:
    """Convierte un nombre distinguido en un diccionario.

    Entiende las tres formas en que llega en la práctica: claves cortas (CN, SN),
    claves con OID (`OID.2.5.4.5`) y valores entrecomillados o con comas escapadas.
    """
    if not dn:
        return {}
    campos: dict[str, str] = {}
    for trozo in _separa_campos(dn):
        if "=" not in trozo:
            continue
        clave, valor = trozo.split("=", 1)
        clave = clave.strip().upper()
        clave = EQUIVALENCIAS_DE_CLAVE.get(clave, clave)
        valor = valor.strip()
        if valor.startswith('"') and valor.endswith('"') and len(valor) >= 2:
            valor = valor[1:-1]
        # Se quitan los escapes que quedan dentro del valor.
        valor = valor.replace("\\,", ",").replace("\\=", "=").replace("\\\\", "\\")
        campos[clave] = valor
    return campos


@dataclass(frozen=True)
class Certificado:
    """Lo que se saca de un certificado, una vez leído su nombre."""

    dn: str
    campos: dict[str, str]
    nif: str
    nombre: str
    organizacion: str

    @property
    def es_empresa(self) -> bool:
        return tipo_de_nif(self.nif) == "cif" if self.nif else False

    @property
    def nif_valido(self) -> bool:
        return nif_valido(self.nif)

    def como_dict(self) -> dict:
        return {
            "nif": self.nif,
            "nombre": self.nombre,
            "organizacion": self.organizacion,
            "es_empresa": self.es_empresa,
            "nif_valido": self.nif_valido,
        }


def certificado_de_dn(dn: str | None) -> Certificado | None:
    """Saca el NIF, el nombre y la organización de un nombre distinguido.

    De dónde sale el NIF, por orden:

    1. **`serialNumber`**: es donde lo pone la FNMT en los certificados españoles, tanto
       de persona física como de persona jurídica. Es el sitio bueno.
    2. **`organizationIdentifier`**: algunos certificados de empresa lo llevan ahí, con
       un prefijo ("VATES-A12345678") que se quita.
    3. Si no hay NIF por ningún lado, se deja vacío. **No se adivina.**

    El nombre se compone con `CN`, y si no hay, con `G` (nombre) + `SN` (apellidos).
    """
    campos = parsea_dn(dn)
    if not campos:
        return None

    candidatos = [
        campos.get("SERIALNUMBER", ""),
        campos.get("ORGANIZATIONIDENTIFIER", ""),
    ]
    nif = ""
    for candidato in candidatos:
        limpio = normaliza_nif(candidato)
        if tipo_de_nif(limpio):
            nif = limpio
            break

    nombre = campos.get("CN", "").strip()
    if not nombre:
        partes = [campos.get("G", "").strip(), campos.get("SN", "").strip()]
        nombre = " ".join(parte for parte in partes if parte)

    return Certificado(
        dn=dn or "",
        campos=campos,
        nif=nif,
        nombre=nombre,
        organizacion=campos.get("O", "").strip(),
    )


# --------------------------------------------------------------------------
# Leer el certificado de la petición
# --------------------------------------------------------------------------

CABECERA_SUJETO = "X-SSL-Client-Subject"
CABECERA_VERIFICACION = "X-SSL-Client-Verify"


def confiar_en_cabeceras() -> bool:
    """¿Está el programa detrás de un servidor web que pone estas cabeceras?

    Por defecto NO. Si se creyera las cabeceras sin más, cualquiera que llegara al
    programa directamente podría mandar `X-SSL-Client-Subject: CN=lo que sea,
    SERIALNUMBER=70922320A` y entrar como otro agricultor. Es el fallo clásico de
    confiar en una cabecera que pone el cliente.
    """
    return os.environ.get("CUEDIGITAL_CONFIAR_EN_CABECERAS", "").strip() in ("1", "true", "si", "sí")


def nombre_cabecera_sujeto() -> str:
    return os.environ.get("CUEDIGITAL_CABECERA_CERTIFICADO", CABECERA_SUJETO)


def nombre_cabecera_verificacion() -> str:
    return os.environ.get("CUEDIGITAL_CABECERA_VERIFICACION", CABECERA_VERIFICACION)


def certificado_de_peticion(request: Request) -> Certificado | None:
    """El certificado del cliente, tal y como lo ha validado el servidor web.

    Devuelve None si no hay certificado, si el programa no está configurado para
    creerse las cabeceras, o si el servidor web dice que la validación NO ha ido bien.
    """
    if not confiar_en_cabeceras():
        return None

    verificacion = request.headers.get(nombre_cabecera_verificacion())
    if verificacion is not None and verificacion.strip().upper() != "SUCCESS":
        # El servidor web ha mirado el certificado y no le ha gustado. No se entra,
        # aunque venga el nombre.
        return None

    return certificado_de_dn(request.headers.get(nombre_cabecera_sujeto()))


def esta_configurado() -> bool:
    """¿Se puede entrar con certificado en esta instalación?"""
    return confiar_en_cabeceras()
