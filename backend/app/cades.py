"""Comprobar la firma del cuaderno de verdad: leer el fichero de firma y verificar que vale.

## Para qué sirve esto, dicho sin tecnicismos

Cuando el agricultor firma el cuaderno, el programa guarda un fichero de firma. Hasta ahora se
guardaba **sin mirarlo**: se comprobaba que la huella que decía el agricultor fuera la del
cuaderno de ahora, pero nadie miraba dentro del fichero de firma. Eso deja un hueco, y es el
hueco que importa:

- Se podía subir **cualquier cosa** como fichero de firma (un fichero de texto, la firma de otro
  documento) y el programa lo guardaba igual.
- Una firma de **otro cuaderno** se aceptaba mientras la huella que acompañaba coincidiera.

Lo que hace esto es **mirar dentro**: sacar el certificado que firmó, comprobar la aritmética de
la firma, y comprobar que el contenido firmado es exactamente el cuaderno que tenemos.

## Cómo se comprueba una firma, en tres pasos

Un CAdES es un fichero binario con una estructura anidada (ASN.1 DER). Dentro está el
certificado, el algoritmo, el resumen que se firmó y un número que es la firma. Se comprueba así:

1. **¿El resumen coincide?** El fichero de firma lleva dentro el resumen del cuaderno que se
   firmó. Se recalcula el del cuaderno que tenemos y se comparan. Si no coinciden, esa firma es
   de otro documento. **Este paso es el que de verdad protege el cuaderno.**
2. **¿La aritmética cuadra?** La firma es un número elevado a una potencia con la clave pública
   del certificado. Se hace la cuenta y se mira si sale el resumen. Si sale, solo pudo firmarlo
   quien tiene la clave privada de ese certificado.
3. **¿Es el certificado que dice?** Que la cuenta se pueda hacer con ese certificado quiere decir
   que es suyo; no hay que fiarse de lo que ponga el fichero.

## Lo que esto NO comprueba, y se dice en voz alta

**No comprueba la cadena de confianza.** O sea: comprueba que *esta firma corresponde a este
cuaderno y a este certificado*, pero **no** comprueba que el certificado lo haya emitido una
autoridad de certificación de fiar. Eso necesita la lista de autoridades raíz en las que
confiar, y esa lista hay que instalarla y mantenerla: no se puede deducir del fichero. Poner un
«sí» ahí sin tenerla sería el peor sitio para mentir, porque es justo el dato que se mira
(`cadena_de_confianza_comprobada` está en falso y se queda en falso).

En la práctica esto importa menos de lo que parece: en esta aplicación **el agricultor entra con
su certificado**, y lo valida el servidor web con la lista de autoridades del sistema. La firma
tiene que ser del mismo NIF que entró. Lo que faltaba por comprobar es lo de arriba: que el
fichero de firma sea de verdad de este cuaderno.

## Sin librerías de criptografía, a propósito

Esto está escrito a mano, sin añadir ninguna dependencia. Se puede porque la cuenta de una firma
RSA no necesita una librería: es una potencia modular, y `pow(base, exponente, modulo)` la hace
Python nativamente. Lo único que hace falta es saber leer la estructura binaria, y eso son unas
decenas de líneas.

Las consecuencias hay que decirlas, y están en el resultado:

- **RSA: sí.** Es lo que usan los certificados de la FNMT, el DNI electrónico y la mayoría de los
  que se usan en el campo. Se comprueba de verdad.
- **Curva elíptica: no.** Comprobarla exige aritmética de curvas, que no es una potencia modular
  y sería mucho más código del que se puede escribir sin poder probarlo a fondo. Si llega una
  firma de curva elíptica, esto dice **«no se ha podido comprobar»**, que no es lo mismo que «no
  vale». Confundir las dos cosas sería llamar mentiroso a un agricultor por no saber leer su
  certificado.
- **SHA-1: no se admite.** Se sabe leer, pero está roto desde hace años: una firma con SHA-1 no
  se puede dar por buena.
- **Cadena de confianza: no** (por lo dicho arriba, y se declara en el resultado).
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Lo que se puede comprobar y lo que no
# --------------------------------------------------------------------------

# Los algoritmos de resumen que se saben leer, por su identificador oficial (OID).
RESUMENES = {
    "2.16.840.1.101.3.4.2.1": "sha256",
    "2.16.840.1.101.3.4.2.2": "sha384",
    "2.16.840.1.101.3.4.2.3": "sha512",
    "2.16.840.1.101.3.4.2.4": "sha224",
    "1.3.14.3.2.26": "sha1",
}

# La cabecera que lleva el resumen dentro de la firma, según el algoritmo. Es lo que se espera
# encontrar al final de la cuenta: viene de la norma PKCS#1 (DigestInfo).
CABECERAS_DIGESTINFO = {
    "sha256": bytes.fromhex("3031300d060960864801650304020105000420"),
    "sha384": bytes.fromhex("3041300d060960864801650304020205000430"),
    "sha512": bytes.fromhex("3051300d060960864801650304020305000440"),
    "sha224": bytes.fromhex("302d300d06096086480165030402040500041c"),
    "sha1": bytes.fromhex("3021300906052b0e03021a05000414"),
}

# Los que ya no se admiten aunque se sepan leer. SHA-1 está roto desde hace años: una firma con
# SHA-1 no se puede dar por buena, y hay que decirlo en vez de comprobarla y callarse.
RESUMENES_NO_ADMITIDOS = {"sha1": "la firma usa SHA-1, que está roto desde hace años y ya no se admite"}

# Los identificadores de firma RSA, que son los que se comprueban.
FIRMAS_RSA = {
    "1.2.840.113549.1.1.1",  # rsaEncryption
    "1.2.840.113549.1.1.5",  # sha1WithRSA
    "1.2.840.113549.1.1.11",  # sha256WithRSA
    "1.2.840.113549.1.1.12",  # sha384WithRSA
    "1.2.840.113549.1.1.13",  # sha512WithRSA
    "1.2.840.113549.1.1.14",  # sha224WithRSA
}

# Los que NO se saben comprobar, con su nombre para poder explicarlo. Aquí está la diferencia
# entre «no vale» y «no lo he podido comprobar»: esto es lo segundo.
FIRMAS_QUE_NO_SE_COMPRUEBAN = {
    "1.2.840.10045.4.3.2": "curva elíptica con SHA-256",
    "1.2.840.10045.4.3.3": "curva elíptica con SHA-384",
    "1.2.840.10045.4.3.4": "curva elíptica con SHA-512",
    "1.2.840.10045.4.1": "curva elíptica con SHA-1",
    "1.3.101.112": "Ed25519",
}

# Los nombres de los campos del titular de un certificado, por su identificador oficial. Son los
# que hacen falta para poder decir **de quién es** el certificado que firmó, que es lo que
# permite comprobar que es el mismo agricultor que ha entrado.
NOMBRES_DEL_SUJETO = {
    "2.5.4.3": "CN",
    "2.5.4.4": "SN",
    "2.5.4.5": "serialNumber",
    "2.5.4.6": "C",
    "2.5.4.7": "L",
    "2.5.4.8": "ST",
    "2.5.4.9": "street",
    "2.5.4.10": "O",
    "2.5.4.11": "OU",
    "2.5.4.12": "title",
    "2.5.4.42": "G",
    "1.2.840.113549.1.9.1": "emailAddress",
}

# Los OID que hacen falta para orientarse dentro del fichero.
OID_SIGNED_DATA = "1.2.840.113549.1.7.2"
OID_ATRIBUTO_MENSAJE = "1.2.840.113549.1.9.4"
OID_ATRIBUTO_FECHA = "1.2.840.113549.1.9.5"
OID_RSA = "1.2.840.113549.1.1.1"

# Los estados posibles del resultado. Tres, y la diferencia entre los dos últimos es la que
# importa: «no vale» y «no lo he podido comprobar» no son lo mismo.
ESTADO_BIEN = "bien"
ESTADO_MAL = "mal"
ESTADO_NO_COMPROBADA = "no_comprobada"

# Las explicaciones **para el agricultor**, en sus palabras. Van aparte de `motivo` a propósito:
# el motivo dice qué ha pasado de verdad («la firma es de curva elíptica con SHA-256») y eso hay
# que guardarlo para poder averiguar algo meses después, pero **no se le puede enseñar a un
# agricultor**: no puede hacer nada con un «SHA-256», y la regla del proyecto es que ningún
# mensaje que él lea lleve jerga. Dos textos para dos lectores distintos.
EXPLICACION_BIEN = "es de este cuaderno y tuya"
EXPLICACION_MAL = "el fichero no es de este cuaderno, o no lo has firmado tú"
EXPLICACION_NO_ES_UNA_FIRMA = "el fichero que has subido no es un fichero de firma"
EXPLICACION_CURVA = "tu certificado es de los que este programa todavía no sabe leer"
EXPLICACION_FALTA_EL_CUADERNO = "hace falta el cuaderno para poder compararlo"
EXPLICACION_SIN_CERTIFICADO = "el fichero de firma no dice con qué certificado se firmó"
EXPLICACION_SIN_FIRMA = "el fichero de firma no trae la firma dentro"
EXPLICACION_ALGORITMO_VIEJO = "la firma está hecha con un sistema viejo que ya no se admite"
EXPLICACION_TIPO_DESCONOCIDO = "este tipo de firma todavía no se sabe comprobar aquí"
EXPLICACION_RESUMEN_DESCONOCIDO = "la firma está hecha de una forma que no se sabe leer"


@dataclass
class Resultado:
    """Qué se ha podido comprobar de una firma, y qué no.

    `estado` es lo que hay que mirar:

    - **`bien`**: la firma corresponde al contenido y al certificado. Comprobado.
    - **`mal`**: la firma NO corresponde. Alguien ha tocado algo. Esto no se puede aceptar.
    - **`no_comprobada`**: no se ha podido comprobar, y se dice por qué. **No** es lo mismo que
      «mal»: una firma de curva elíptica cae aquí, y tratarla como mala sería acusar a un
      agricultor de algo que no ha hecho.
    """

    estado: str = ESTADO_NO_COMPROBADA
    # `motivo` es para quien mantiene esto: dice qué ha pasado, con los nombres de las cosas.
    # `explicacion` es para el agricultor: dice lo mismo sin una sola palabra que no entienda.
    motivo: str = ""
    explicacion: str = EXPLICACION_NO_ES_UNA_FIRMA
    firmante: str = ""
    # De quién es el certificado que firmó. Es lo que permite comprobar que es el mismo
    # agricultor que ha entrado: una firma buena de otro certificado no es una firma suya.
    firmante_nif: str = ""
    firmante_nombre: str = ""
    numero_de_serie: str = ""
    algoritmo_de_firma: str = ""
    algoritmo_de_resumen: str = ""
    # Los pasos, cada uno con su respuesta.
    resumen_coincide: bool | None = None
    aritmetica_correcta: bool | None = None
    firmado_en: str | None = None
    # Si el certificado estaba en vigor cuando se firmó. Se informa, pero **no se rechaza por
    # esto**: si el reloj del ordenador del agricultor va mal, rechazar la firma le echaría la
    # culpa a él de algo que no ha hecho.
    vigente_al_firmar: bool | None = None
    # El contenido firmado: si el fichero de firma lo lleva dentro (adjunta) o no (destacada).
    lleva_el_contenido_dentro: bool = False
    el_contenido_adjunto_es_el_nuestro: bool | None = None
    certificados_dentro: int = 0
    # Y lo que no se comprueba, declarado en el propio resultado para que nadie lo suponga.
    cadena_de_confianza_comprobada: bool = False
    no_comprobado: list[str] = field(default_factory=list)

    @property
    def vale(self) -> bool:
        """Solo cuando se ha comprobado y ha salido bien. Es lo que se guarda en la base."""
        return self.estado == ESTADO_BIEN

    @property
    def esta_tocado(self) -> bool:
        """Comprobado y NO vale. Es lo único que se puede rechazar sin dudar."""
        return self.estado == ESTADO_MAL

    def como_dict(self) -> dict:
        return {
            "estado": self.estado,
            "vale": self.vale,
            "motivo": self.motivo,
            "explicacion": self.explicacion,
            "firmante": self.firmante,
            "firmante_nif": self.firmante_nif,
            "firmante_nombre": self.firmante_nombre,
            "numero_de_serie": self.numero_de_serie,
            "algoritmo_de_firma": self.algoritmo_de_firma,
            "algoritmo_de_resumen": self.algoritmo_de_resumen,
            "resumen_coincide": self.resumen_coincide,
            "aritmetica_correcta": self.aritmetica_correcta,
            "firmado_en": self.firmado_en,
            "vigente_al_firmar": self.vigente_al_firmar,
            "lleva_el_contenido_dentro": self.lleva_el_contenido_dentro,
            "el_contenido_adjunto_es_el_nuestro": self.el_contenido_adjunto_es_el_nuestro,
            "certificados_dentro": self.certificados_dentro,
            "cadena_de_confianza_comprobada": self.cadena_de_confianza_comprobada,
            "no_comprobado": list(self.no_comprobado),
        }


# --------------------------------------------------------------------------
# Leer la estructura binaria (ASN.1 DER)
#
# Estructura mínima: cada cosa empieza por una etiqueta, sigue el tamaño y luego el contenido.
# Con eso se puede recorrer el fichero entero. No se implementa nada más de ASN.1 porque no hace
# falta: lo que hay dentro son secuencias, conjuntos y cadenas.
#
# CONVENIO que hay que tener claro al leer el resto: las funciones de certificado reciben el
# **contenido** de la SEQUENCE del certificado, sin la etiqueta de fuera. Es lo que devuelve
# `hijos`, y por eso todas usan el mismo: `hijos(certificado)[0][1]` es el `tbsCertificate`.
# --------------------------------------------------------------------------

ETIQUETA_SECUENCIA = 0x30
ETIQUETA_CONJUNTO = 0x31
ETIQUETA_OCTETOS = 0x04
ETIQUETA_BITS = 0x03
ETIQUETA_OID = 0x06
ETIQUETA_ENTERO = 0x02
# Las etiquetas «de contexto»: son las que usa el CMS para marcar sus partes ([0], [1]…).
ETIQUETA_CONTEXTO_0 = 0xA0


class NoSeEntiende(ValueError):
    """El fichero de firma no tiene la forma que debería.

    Se trata aparte de «la firma no vale» porque un fichero ilegible no es una firma que no
    vale: es que no es una firma. Y eso hay que decirlo distinto: una es «vuelve a subirlo», la
    otra es «alguien ha tocado esto».
    """


def leer_tlv(datos: bytes, posicion: int) -> tuple[int, bytes, int]:
    """Lee una cosa de la estructura: devuelve (etiqueta, contenido, dónde sigue).

    Solo se admiten tamaños «normales» (hasta 4 bytes de longitud), que es todo lo que cabe en un
    fichero de firma. Un tamaño imposible se trata como fichero ilegible, no como un caso raro
    que haya que soportar.
    """
    if posicion + 2 > len(datos):
        raise NoSeEntiende("el fichero se acaba antes de tiempo")
    etiqueta = datos[posicion]
    posicion += 1
    primera = datos[posicion]
    posicion += 1
    if primera < 0x80:
        largo = primera
    else:
        cuantos = primera & 0x7F
        if cuantos == 0 or cuantos > 4:
            raise NoSeEntiende("tamaño de campo imposible")
        if posicion + cuantos > len(datos):
            raise NoSeEntiende("el fichero se acaba antes de decir cuánto mide")
        largo = int.from_bytes(datos[posicion : posicion + cuantos], "big")
        posicion += cuantos
    if posicion + largo > len(datos):
        raise NoSeEntiende("el contenido dice medir más de lo que hay")
    return etiqueta, datos[posicion : posicion + largo], posicion + largo


def hijos(contenido: bytes) -> list[tuple[int, bytes]]:
    """Parte el contenido de una secuencia o un conjunto en sus trozos, en orden."""
    trozos: list[tuple[int, bytes]] = []
    posicion = 0
    while posicion < len(contenido):
        etiqueta, valor, posicion = leer_tlv(contenido, posicion)
        trozos.append((etiqueta, valor))
    return trozos


def leer_entero(datos: bytes) -> int:
    return int.from_bytes(datos, "big", signed=False)


def leer_oid(datos: bytes) -> str:
    """Convierte un identificador oficial a texto (`1.2.840.113549...`).

    Se hace a mano porque estos identificadores son los que hay que poder enseñar en un motivo:
    «2.16.840.1.101.3.4.2.1» se puede buscar, un número suelto no.
    """
    if not datos:
        return ""
    primera = datos[0]
    partes = [str(primera // 40), str(primera % 40)]
    valor = 0
    for byte in datos[1:]:
        valor = (valor << 7) | (byte & 0x7F)
        if not byte & 0x80:
            partes.append(str(valor))
            valor = 0
    return ".".join(partes)


def _envolver(etiqueta: int, contenido: bytes) -> bytes:
    """Vuelve a montar un trozo con su etiqueta y su tamaño."""
    return bytes([etiqueta]) + _largo(len(contenido)) + contenido


def _largo(cuantos: int) -> bytes:
    if cuantos < 0x80:
        return bytes([cuantos])
    if cuantos < 0x100:
        return bytes([0x81, cuantos])
    return bytes([0x82]) + cuantos.to_bytes(2, "big")


def reconstruir_conjunto(contenido: bytes) -> bytes:
    """Vuelve a envolver unos atributos firmados con la etiqueta de conjunto.

    **Este detalle es el que hace que la comprobación funcione o no.** Dentro del fichero, los
    atributos firmados van marcados como «[0]» (una etiqueta de contexto), pero lo que se firmó
    fue lo mismo con la etiqueta de conjunto (0x31). Si se verifica tal cual está en el fichero,
    la cuenta no sale nunca. Es un error clásico y silencioso: diría «firma manipulada» de
    firmas perfectamente buenas.
    """
    return _envolver(ETIQUETA_CONJUNTO, contenido)


# --------------------------------------------------------------------------
# Sacar las piezas del fichero
# --------------------------------------------------------------------------


@dataclass
class Firmante:
    """Lo que hace falta para comprobar una firma, ya sacado del fichero."""

    contenido_dentro: bytes | None = None
    certificado: bytes | None = None
    certificados: int = 0
    algoritmo_de_resumen: str = ""
    oid_de_resumen: str = ""
    oid_de_firma: str = ""
    firma: bytes = b""
    atributos_firmados: bytes | None = None
    resumen_declarado: bytes | None = None
    firmado_en: str | None = None
    numero_de_serie: str = ""


def _certificados_de(datos: bytes) -> list[bytes]:
    """Los certificados que van dentro de la firma, en orden."""
    try:
        return [valor for _etiqueta, valor in hijos(datos)]
    except NoSeEntiende:
        return []


def _contenido_del_certificado(datos: bytes) -> bytes:
    """Acepta un certificado entero o su contenido, y devuelve siempre el contenido.

    Por qué existe esto: dentro del fichero de firma los certificados vienen **sin** la etiqueta
    de fuera (es lo que devuelve `hijos`), pero quien llama desde fuera tiene el certificado
    entero, tal cual está en un `.cer`. Que las funciones de aquí abajo tuvieran que saber cuál
    de las dos formas les están dando sería una trampa para el siguiente que las use: le
    funcionaría con una y le daría un resultado vacío con la otra, **sin dar ningún error**.

    La diferencia es clara y no hay ambigüedad:

    * un certificado **entero** es `30 <tamaño> <contenido>`, así que al partirlo sale **un**
      trozo;
    * el **contenido** son los tres campos de dentro (los datos, el algoritmo y la firma), así
      que al partirlo salen **tres**.

    Y como un certificado siempre tiene sus tres campos, «sale un trozo» solo puede querer decir
    que falta desenvolverlo.
    """
    try:
        trozos = hijos(datos)
    except NoSeEntiende:
        return datos
    if len(trozos) == 1 and trozos[0][0] == ETIQUETA_SECUENCIA:
        return trozos[0][1]
    return datos


def _campos_del_certificado(datos: bytes) -> list[tuple[int, bytes]]:
    """Los campos del `tbsCertificate`, ya sea el certificado entero o su contenido."""
    trozos = hijos(_contenido_del_certificado(datos))
    return hijos(trozos[0][1])


def numero_de_serie_del_certificado(certificado: bytes) -> str:
    """El número de serie de un certificado: lo que lo identifica sin ambigüedad."""
    try:
        tbs = _campos_del_certificado(certificado)
    except (NoSeEntiende, IndexError):
        return ""
    if not tbs:
        return ""
    # El primero puede ser la versión ([0]); el número de serie va justo después.
    indice = 1 if tbs[0][0] == ETIQUETA_CONTEXTO_0 else 0
    if indice >= len(tbs) or tbs[indice][0] != ETIQUETA_ENTERO:
        return ""
    return format(leer_entero(tbs[indice][1]), "X")


def _atributos_firmados(contenido: bytes) -> tuple[bytes | None, str | None]:
    """El resumen que se firmó y la fecha de firma, de entre los atributos.

    SignedAttributes es una lista de `SEQUENCE { OID, SET OF valor }`. Solo interesan dos:
    `messageDigest` (el resumen del cuaderno) y `signingTime` (cuándo se firmó).
    """
    resumen: bytes | None = None
    fecha: str | None = None
    for _etiqueta, atributo in hijos(contenido):
        campos = hijos(atributo)
        if len(campos) < 2 or campos[0][0] != ETIQUETA_OID:
            continue
        oid = leer_oid(campos[0][1])
        valores = hijos(campos[1][1]) if campos[1][0] == ETIQUETA_CONJUNTO else []
        if not valores:
            continue
        if oid == OID_ATRIBUTO_MENSAJE and valores[0][0] == ETIQUETA_OCTETOS:
            resumen = valores[0][1]
        elif oid == OID_ATRIBUTO_FECHA:
            # La fecha se deja en el formato de siempre (2026-09-22T17:15:45) y no en el de
            # ASN.1 (260922171545Z), porque luego hay que compararla con las fechas del
            # certificado, y comparar dos formatos distintos da un «no» silencioso.
            cruda = valores[0][1].decode("ascii", errors="replace")
            fecha = _leer_fecha_asn1(valores[0][1]) or cruda
    return resumen, fecha


def leer_firmante(datos: bytes) -> Firmante:
    """Recorre el fichero de firma y saca las piezas. Lanza `NoSeEntiende` si no lo es."""
    etiqueta, cuerpo, _ = leer_tlv(datos, 0)
    if etiqueta != ETIQUETA_SECUENCIA:
        raise NoSeEntiende("el fichero no empieza como una firma")

    trozos = hijos(cuerpo)
    if len(trozos) < 2:
        raise NoSeEntiende("el fichero no tiene contenido")

    tipo = leer_oid(trozos[0][1])
    if tipo != OID_SIGNED_DATA:
        raise NoSeEntiende(f"no es una firma de datos (tipo {tipo})")

    # El contenido del ContentInfo va marcado como [0] y dentro está el SignedData.
    etiqueta_interior, interior, _ = leer_tlv(trozos[1][1], 0)
    if etiqueta_interior != ETIQUETA_SECUENCIA:
        raise NoSeEntiende("la firma no tiene la estructura esperada")

    # SignedData: version, digestAlgorithms, encapContentInfo, [certificados], [crls],
    # signerInfos. Los corchetes son opcionales, así que se busca por etiqueta y no por orden.
    partes = hijos(interior)
    contenido_dentro: bytes | None = None
    certificados: list[bytes] = []
    firmantes: list[tuple[int, bytes]] = []

    for indice, (etiqueta_parte, valor_parte) in enumerate(partes):
        if indice == 2 and etiqueta_parte == ETIQUETA_SECUENCIA:
            # encapContentInfo: puede llevar el contenido (adjunta) o no (destacada).
            for etiqueta_hijo, valor_hijo in hijos(valor_parte):
                if etiqueta_hijo == ETIQUETA_CONTEXTO_0:
                    _e, octetos, _ = leer_tlv(valor_hijo, 0)
                    contenido_dentro = octetos
        elif etiqueta_parte == ETIQUETA_CONTEXTO_0:
            certificados = _certificados_de(valor_parte)
        elif etiqueta_parte == ETIQUETA_CONJUNTO:
            firmantes = hijos(valor_parte)

    if not firmantes:
        raise NoSeEntiende("la firma no dice quién ha firmado")

    resultado = Firmante(contenido_dentro=contenido_dentro, certificados=len(certificados))

    _etiqueta_firmante, cuerpo_firmante = firmantes[0]
    campos = hijos(cuerpo_firmante)
    # SignerInfo: version, sid, digestAlgorithm, [signedAttrs], signatureAlgorithm, signature.
    # Como los atributos firmados son opcionales, se busca por etiqueta.
    for etiqueta_campo, valor_campo in campos:
        # El «sid» es lo primero que es una secuencia: el emisor y el número de serie.
        if etiqueta_campo == ETIQUETA_SECUENCIA:
            dentro = hijos(valor_campo)
            if len(dentro) == 2 and dentro[1][0] == ETIQUETA_ENTERO:
                resultado.numero_de_serie = format(leer_entero(dentro[1][1]), "X")
            break

    for etiqueta_campo, valor_campo in campos:
        if etiqueta_campo == ETIQUETA_SECUENCIA:
            if resultado.oid_de_resumen:
                continue
            dentro = hijos(valor_campo)
            if dentro and dentro[0][0] == ETIQUETA_OID:
                resultado.oid_de_resumen = leer_oid(dentro[0][1])
                resultado.algoritmo_de_resumen = RESUMENES.get(resultado.oid_de_resumen, "")
        elif etiqueta_campo == ETIQUETA_CONTEXTO_0:
            resultado.atributos_firmados = valor_campo
            resultado.resumen_declarado, resultado.firmado_en = _atributos_firmados(valor_campo)

    # La última secuencia de algoritmos es la de la firma, y después viene la firma.
    secuencias = [valor for etiqueta, valor in campos if etiqueta == ETIQUETA_SECUENCIA]
    if len(secuencias) >= 2:
        dentro = hijos(secuencias[-1])
        if dentro and dentro[0][0] == ETIQUETA_OID:
            resultado.oid_de_firma = leer_oid(dentro[0][1])
    octetos = [valor for etiqueta, valor in campos if etiqueta == ETIQUETA_OCTETOS]
    if octetos:
        resultado.firma = octetos[-1]

    # El certificado: se busca el que corresponde al número de serie del firmante, y si no
    # aparece, el primero. Pero no se da por bueno por decirlo el fichero: la cuenta de la firma
    # es la que decide si ese certificado es el que firmó.
    for candidato in certificados:
        if numero_de_serie_del_certificado(candidato) == resultado.numero_de_serie:
            resultado.certificado = candidato
            break
    if resultado.certificado is None and certificados:
        resultado.certificado = certificados[0]
    return resultado


def numero_de_serie_del_firmante(datos: bytes) -> str:
    """El número de serie del certificado que firmó, sin comprobar nada más.

    Está para poder mirar un fichero de firma sin verificar la firma: sirve para saber de quién
    es sin fiarse de nada de lo que diga.
    """
    try:
        return leer_firmante(datos).numero_de_serie
    except NoSeEntiende:
        return ""


def sujeto_del_certificado(certificado: bytes) -> dict[str, str]:
    """De quién es el certificado: los campos de su titular, por nombre corto.

    Un certificado guarda el titular como una lista de parejas «campo = valor». Se devuelven con
    los nombres de siempre (`CN`, `O`, `serialNumber`), que son los que se ven en el certificado
    cuando se abre, no los números de la norma.

    Decisión: si un campo se repite, se queda el primero. No se concatenan, porque el valor se
    usa para comparar con el NIF que dice el certificado de entrada, y una lista de dos valores
    no coincidiría con nada.
    """
    sujeto: dict[str, str] = {}
    try:
        tbs = _campos_del_certificado(certificado)
    except (NoSeEntiende, IndexError):
        return sujeto
    # El titular es la secuencia que va detrás de la validez. Se busca por estructura: la validez
    # es la secuencia de dos fechas, y justo después viene el titular.
    secuencias = [valor for etiqueta, valor in tbs if etiqueta == ETIQUETA_SECUENCIA]
    titular = None
    for secuencia in secuencias:
        dentro = hijos(secuencia)
        es_validez = (
            len(dentro) == 2
            and all(etiqueta in (0x17, 0x18) for etiqueta, _ in dentro)
        )
        if es_validez:
            continue
        if dentro and all(etiqueta == ETIQUETA_CONJUNTO for etiqueta, _ in dentro):
            titular = secuencia
            break
    if titular is None:
        return sujeto

    # El titular es una lista de conjuntos, y dentro de cada conjunto va una SECUENCIA con la
    # pareja «campo = valor». Ese nivel de en medio es fácil de saltarse: si se busca el OID
    # directamente dentro del conjunto, no se encuentra nada y el titular sale vacío **sin dar
    # ningún error**. Pasó al escribir esto, y por eso se deja dicho.
    for _etiqueta, conjunto in hijos(titular):
        for etiqueta_pareja, pareja in hijos(conjunto):
            if etiqueta_pareja != ETIQUETA_SECUENCIA:
                continue
            partes = hijos(pareja)
            if len(partes) < 2 or partes[0][0] != ETIQUETA_OID:
                continue
            oid = leer_oid(partes[0][1])
            nombre = NOMBRES_DEL_SUJETO.get(oid, oid)
            if nombre in sujeto:
                continue
            sujeto[nombre] = partes[1][1].decode("utf-8", errors="replace").strip()
    return sujeto


def nif_del_sujeto(sujeto: dict[str, str]) -> str:
    """El NIF del titular, sacado de su certificado.

    El sitio oficial donde va es el campo `serialNumber`, y es lo que exige la norma para los
    certificados de persona física y jurídica españoles. Si ahí no hay nada con pinta de NIF, se
    busca en el nombre, porque hay certificados antiguos que lo ponen ahí.

    Devolver `""` es una respuesta legítima: significa «este certificado no dice su NIF de una
    forma que yo sepa leer», y entonces **no se puede comprobar** que sea el mismo agricultor.
    Eso es distinto de «es otro».
    """
    candidatos = [sujeto.get("serialNumber", ""), sujeto.get("CN", "")]
    for candidato in candidatos:
        for trozo in candidato.replace("-", " ").replace("/", " ").split():
            limpio = trozo.strip().upper()
            if len(limpio) in (9, 10) and limpio[:1].isalpha() and limpio[1:8].isdigit():
                return limpio
            if len(limpio) == 9 and limpio[:8].isdigit() and limpio[8:].isalpha():
                return limpio
    return ""


def _leer_fecha_asn1(datos: bytes) -> str | None:
    """Convierte una fecha de ASN.1 a texto. `YYMMDDHHMMSSZ` o `YYYYMMDDHHMMSSZ`."""
    try:
        texto = datos.decode("ascii").strip()
    except Exception:  # noqa: BLE001 — una fecha ilegible es una fecha que no se sabe leer
        return None
    limpio = texto.rstrip("Z")
    if not limpio.isdigit():
        return None
    if len(limpio) == 12:  # UTCTime: dos dígitos de año
        anio = int(limpio[:2])
        anio += 2000 if anio < 50 else 1900
        resto = limpio[2:]
    elif len(limpio) >= 14:  # GeneralizedTime: cuatro dígitos de año
        anio = int(limpio[:4])
        resto = limpio[4:]
    else:
        return None
    return f"{anio:04d}-{resto[0:2]}-{resto[2:4]}T{resto[4:6]}:{resto[6:8]}:{resto[8:10]}"


def validez_del_certificado(certificado: bytes) -> tuple[str, str] | None:
    """Desde cuándo y hasta cuándo vale el certificado, en texto. `None` si no se puede leer."""
    try:
        tbs = _campos_del_certificado(certificado)
    except (NoSeEntiende, IndexError):
        return None
    for etiqueta, valor in tbs:
        if etiqueta != ETIQUETA_SECUENCIA:
            continue
        dentro = hijos(valor)
        if len(dentro) == 2 and all(e in (0x17, 0x18) for e, _ in dentro):
            desde = _leer_fecha_asn1(dentro[0][1])
            hasta = _leer_fecha_asn1(dentro[1][1])
            if desde and hasta:
                return desde, hasta
    return None


def _estaba_vigente(certificado: bytes, firmado_en: str | None) -> bool | None:
    """Si el certificado estaba en vigor en el momento de firmar.

    Se informa y no se rechaza. Motivo: la fecha de firma la pone el reloj del ordenador del
    agricultor. Si ese reloj va un día adelantado y el certificado caducó ayer, rechazar la firma
    sería echarle la culpa de algo que no ha hecho. Lo que sí se hace es decirlo, para que quien
    mire la ficha lo vea.
    """
    if not firmado_en:
        return None
    validez = validez_del_certificado(certificado)
    if validez is None:
        return None
    desde, hasta = validez
    # Las dos fechas vienen en el mismo formato, así que se pueden comparar como texto.
    try:
        return desde <= firmado_en[:19] <= hasta
    except TypeError:  # pragma: no cover — no debería pasar con dos cadenas
        return None


# --------------------------------------------------------------------------
# La clave pública y la cuenta
# --------------------------------------------------------------------------


def clave_publica_rsa(certificado: bytes) -> tuple[int, int] | None:
    """Saca el módulo y el exponente de un certificado. `None` si no es RSA.

    Recorre el certificado hasta el `subjectPublicKeyInfo` y de ahí al `RSAPublicKey`, que son
    dos números: el módulo (enorme, 2048 bits lo normal) y el exponente (casi siempre 65537).
    """
    try:
        tbs = _campos_del_certificado(certificado)
    except (NoSeEntiende, IndexError):
        return None
    for etiqueta, valor in tbs:
        if etiqueta != ETIQUETA_SECUENCIA:
            continue
        dentro = hijos(valor)
        if not dentro or dentro[0][0] != ETIQUETA_SECUENCIA:
            continue
        algoritmo = hijos(dentro[0][1])
        if not algoritmo or algoritmo[0][0] != ETIQUETA_OID:
            continue
        if leer_oid(algoritmo[0][1]) != OID_RSA:
            continue
        for etiqueta_clave, valor_clave in dentro[1:]:
            if etiqueta_clave != ETIQUETA_BITS or not valor_clave:
                continue
            # El primer byte del BIT STRING dice cuántos bits de relleno hay (siempre 0).
            try:
                _e, numeros, _ = leer_tlv(valor_clave[1:], 0)
                partes = hijos(numeros)
            except NoSeEntiende:
                return None
            if len(partes) >= 2:
                return leer_entero(partes[0][1]), leer_entero(partes[1][1])
    return None


def _comprobar_aritmetica(firma: bytes, certificado: bytes, esperado: bytes) -> bool:
    """La cuenta de la firma RSA.

    Una firma RSA es el resumen elevado a la clave privada (módulo el módulo del certificado).
    Para comprobarla se hace lo contrario con la clave pública: `firma ^ exponente`. Si el
    resultado es el resumen esperado, es que solo pudo firmarlo quien tiene la privada.

    Se usa `pow(base, exponente, modulo)`, que es una potencia modular y la hace Python de serie:
    por eso esto no necesita ninguna librería de criptografía.
    """
    clave = clave_publica_rsa(certificado)
    if clave is None or not firma:
        return False
    modulo, exponente = clave
    try:
        resultado = pow(int.from_bytes(firma, "big"), exponente, modulo)
    except (ValueError, OverflowError):
        return False
    cuantos = (modulo.bit_length() + 7) // 8
    obtenido = resultado.to_bytes(cuantos, "big")
    # El relleno de delante (0x00 0x01 0xFF…) se ignora: lo que se busca es el final.
    return obtenido.endswith(esperado)


def _digestinfo(algoritmo: str, resumen: bytes) -> bytes | None:
    cabecera = CABECERAS_DIGESTINFO.get(algoritmo)
    return cabecera + resumen if cabecera else None


# --------------------------------------------------------------------------
# Lo que se llama desde fuera
# --------------------------------------------------------------------------


def verificar(fichero: bytes, contenido: bytes | None = None) -> Resultado:
    """Comprueba una firma CAdES contra el contenido que se le dé.

    `fichero` es el fichero de firma tal cual lo devolvió AutoFirma (los bytes, no el base64).
    `contenido` es el cuaderno firmado: el texto canónico, byte a byte. Si la firma lleva el
    contenido dentro, no hace falta, pero **si se pasa se comprueba que sea el mismo**: una firma
    adjunta de otro cuaderno no vale.

    Nunca lanza una excepción por un fichero raro: devuelve un resultado que dice qué pasó, para
    poder enseñárselo al agricultor en sus palabras.
    """
    resultado = Resultado()
    resultado.no_comprobado.append(
        "la cadena de confianza: no se comprueba que el certificado lo haya emitido una "
        "autoridad de fiar, porque eso necesita la lista de autoridades raíz"
    )

    if not fichero:
        resultado.motivo = "no hay fichero de firma"
        return resultado

    try:
        firmante = leer_firmante(fichero)
    except NoSeEntiende as error:
        resultado.motivo = f"eso no parece un fichero de firma ({error})"
        return resultado

    resultado.numero_de_serie = firmante.numero_de_serie
    resultado.algoritmo_de_resumen = firmante.algoritmo_de_resumen
    resultado.algoritmo_de_firma = firmante.oid_de_firma
    resultado.firmado_en = firmante.firmado_en
    resultado.lleva_el_contenido_dentro = firmante.contenido_dentro is not None
    resultado.certificados_dentro = firmante.certificados

    if firmante.certificado is None:
        resultado.motivo = "la firma no lleva dentro el certificado con el que se firmó"
        resultado.explicacion = EXPLICACION_SIN_CERTIFICADO
        return resultado
    if not firmante.firma:
        resultado.motivo = "la firma no lleva la firma"
        resultado.explicacion = EXPLICACION_SIN_FIRMA
        return resultado

    # De quién es el certificado que firmó. Esto no decide si la firma vale —eso lo decide la
    # cuenta de más abajo—, pero es lo que permite comprobar que es **el mismo agricultor** que
    # ha entrado: una firma perfectamente buena de otro certificado no es una firma suya.
    sujeto = sujeto_del_certificado(firmante.certificado)
    resultado.firmante_nif = nif_del_sujeto(sujeto)
    resultado.firmante_nombre = sujeto.get("CN", "")
    resultado.firmante = ", ".join(
        f"{clave}={valor}" for clave, valor in sujeto.items() if clave in ("CN", "serialNumber")
    )
    resultado.vigente_al_firmar = _estaba_vigente(firmante.certificado, firmante.firmado_en)

    # ¿Se sabe comprobar este tipo de firma? Si no, se dice, y NO se dice que esté mal.
    if firmante.oid_de_firma in FIRMAS_QUE_NO_SE_COMPRUEBAN:
        resultado.motivo = (
            f"la firma es de {FIRMAS_QUE_NO_SE_COMPRUEBAN[firmante.oid_de_firma]} y eso todavía "
            "no se sabe comprobar aquí. No quiere decir que no valga"
        )
        resultado.explicacion = EXPLICACION_CURVA
        return resultado
    if firmante.oid_de_firma not in FIRMAS_RSA:
        resultado.motivo = (
            f"no se sabe comprobar este tipo de firma ({firmante.oid_de_firma or 'sin decir'})"
        )
        resultado.explicacion = EXPLICACION_TIPO_DESCONOCIDO
        return resultado
    if not firmante.algoritmo_de_resumen:
        resultado.motivo = (
            "el resumen está hecho con un algoritmo que no se sabe leer "
            f"({firmante.oid_de_resumen or 'sin decir'})"
        )
        resultado.explicacion = EXPLICACION_RESUMEN_DESCONOCIDO
        return resultado
    if firmante.algoritmo_de_resumen in RESUMENES_NO_ADMITIDOS:
        resultado.estado = ESTADO_MAL
        resultado.motivo = RESUMENES_NO_ADMITIDOS[firmante.algoritmo_de_resumen]
        resultado.explicacion = EXPLICACION_ALGORITMO_VIEJO
        resultado.resumen_coincide = False
        resultado.aritmetica_correcta = False
        return resultado

    # El contenido contra el que se comprueba: el de dentro si lo lleva, el que nos den si no.
    if firmante.contenido_dentro is not None:
        if contenido is not None:
            resultado.el_contenido_adjunto_es_el_nuestro = (
                firmante.contenido_dentro == contenido
            )
            if not resultado.el_contenido_adjunto_es_el_nuestro:
                resultado.estado = ESTADO_MAL
                resultado.motivo = (
                    "el cuaderno que va dentro de la firma no es el cuaderno que hay ahora"
                )
                resultado.explicacion = EXPLICACION_MAL
                return resultado
        contenido = firmante.contenido_dentro

    if contenido is None:
        resultado.motivo = (
            "la firma no lleva el cuaderno dentro, así que hace falta darle el cuaderno para "
            "poder comprobarla"
        )
        resultado.explicacion = EXPLICACION_FALTA_EL_CUADERNO
        return resultado

    resumen_del_contenido = hashlib.new(firmante.algoritmo_de_resumen, contenido).digest()

    if firmante.atributos_firmados is None:
        # Sin atributos firmados se firma el contenido directamente. AutoFirma siempre los pone,
        # pero hay generadores que no, y comprobarlo es lo mismo.
        esperado = _digestinfo(firmante.algoritmo_de_resumen, resumen_del_contenido)
        if esperado is None:
            resultado.motivo = "no se sabe preparar el resumen de ese algoritmo"
            resultado.explicacion = EXPLICACION_RESUMEN_DESCONOCIDO
            return resultado
        resultado.aritmetica_correcta = _comprobar_aritmetica(
            firmante.firma, firmante.certificado, esperado
        )
    else:
        # Paso 1: el resumen que la firma dice que había tiene que ser el del cuaderno.
        if firmante.resumen_declarado is None:
            resultado.motivo = "la firma no dice qué resumen firmó"
            resultado.explicacion = EXPLICACION_SIN_FIRMA
            return resultado
        resultado.resumen_coincide = firmante.resumen_declarado == resumen_del_contenido
        if not resultado.resumen_coincide:
            resultado.estado = ESTADO_MAL
            resultado.motivo = (
                "la firma es de otro cuaderno: el resumen que lleva dentro no es el de este"
            )
            resultado.explicacion = EXPLICACION_MAL
            resultado.aritmetica_correcta = False
            return resultado
        # Paso 2: la aritmética, sobre los atributos firmados tal y como se firmaron.
        firmado = reconstruir_conjunto(firmante.atributos_firmados)
        esperado = _digestinfo(
            firmante.algoritmo_de_resumen,
            hashlib.new(firmante.algoritmo_de_resumen, firmado).digest(),
        )
        if esperado is None:
            resultado.motivo = "no se sabe preparar el resumen de ese algoritmo"
            resultado.explicacion = EXPLICACION_RESUMEN_DESCONOCIDO
            return resultado
        resultado.aritmetica_correcta = _comprobar_aritmetica(
            firmante.firma, firmante.certificado, esperado
        )

    if not resultado.aritmetica_correcta:
        resultado.estado = ESTADO_MAL
        resultado.motivo = (
            "la firma no cuadra con el certificado: el fichero de firma está tocado o no es de "
            "quien dice"
        )
        resultado.explicacion = EXPLICACION_MAL
        return resultado

    resultado.estado = ESTADO_BIEN
    resultado.motivo = "la firma corresponde a este cuaderno y a este certificado"
    resultado.explicacion = EXPLICACION_BIEN
    return resultado


def verificar_base64(texto: str, contenido: bytes | None = None) -> Resultado:
    """Lo mismo, pero con el fichero tal y como lo manda el navegador (en base64)."""
    try:
        fichero = base64.b64decode(texto or "", validate=True)
    except Exception:  # noqa: BLE001 — un base64 mal formado es simplemente «no hay firma»
        return Resultado(
            motivo="eso no parece un fichero de firma (no se puede leer)",
            explicacion=EXPLICACION_NO_ES_UNA_FIRMA,
        )
    return verificar(fichero, contenido)


# --------------------------------------------------------------------------
# Lo que se le cuenta al agricultor
# --------------------------------------------------------------------------


def resumen_para_el_agricultor(resultado: Resultado) -> str:
    """Una frase para la pantalla, sin tecnicismos.

    El agricultor tiene que poder hacer algo con lo que lea. «Error de validación CMS» no le
    sirve de nada; «el fichero de firma no es de este cuaderno, vuelve a firmarlo» sí.

    Decisión, y esto se aprendió escribiendo el test de la jerga: **aquí NO se usa `motivo`.**
    El motivo dice qué ha pasado de verdad y lleva los nombres de las cosas («curva elíptica con
    SHA-256»), que es justo lo que hay que guardar para poder investigar después y justo lo que
    no se le puede enseñar a un agricultor. Para eso está `explicacion`.
    """
    if resultado.estado == ESTADO_BIEN:
        return "La firma está comprobada: es de este cuaderno y tuya."
    if resultado.estado == ESTADO_MAL:
        return (
            "El fichero de firma no es de este cuaderno. Puede que hayas firmado otro, o que el "
            "fichero se haya estropeado al mandarlo. Vuelve a firmarlo."
        )
    return (
        "No se ha podido comprobar la firma, pero se ha guardado igual. No es culpa tuya: "
        f"{resultado.explicacion}."
    )
