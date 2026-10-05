"""El cliente del IUWS: hablar de verdad con el interfaz de la Junta.

`iuws.py` sabe **qué** hay que mandar y con qué formato. Esto sabe **cómo** mandarlo: las
llamadas HTTP, las cabeceras del certificado y la comprobación de que al otro lado hay alguien.

## Lo que se ha comprobado contra el interfaz de verdad

El 22/09/2026, `GET /IUWS/api/version` contestó 200 con la versión 3.11.4 tanto en
Castilla y León como en el entorno de integración del FEGA. Los métodos autenticados de
esta versión siguen pendientes de probar con el certificado y el alta reales.

## Cómo se prueba esto sin el certificado

Con un **transporte de mentira**: `httpx` deja inyectar uno, así que los tests prueban el flujo
entero —cabeceras, cuerpo, lectura de la respuesta— sin salir a internet. Y la llamada de
`version`, que no necesita certificado, se prueba **contra el interfaz de verdad** en la prueba
de humo.
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache

from jsonschema import Draft7Validator

import httpx

from . import iuws, textos

# El script que firma con el certificado del almacén de Windows. Está en `scripts/` y **fuera de la
# aplicación** a propósito: no es parte del programa, es la herramienta que usa cuando necesita
# firmar con una clave que no se puede sacar de donde vive.
FIRMADOR_DE_WINDOWS = (
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "firmar_con_el_certificado.ps1"
)

# --------------------------------------------------------------------------
# El certificado
# --------------------------------------------------------------------------


def cabecera_certificado(pem: str) -> str:
    """Prepara el certificado para la cabecera `certificate-sscc`.

    El Anexo VI lo dice con pelos y señales, y son tres cosas que hay que quitar:
    la línea `-----BEGIN CERTIFICATE-----`, la línea `-----END CERTIFICATE-----`, y **todos los
    saltos de línea**. Si se manda tal cual, el interfaz no lo reconoce.

    Se acepta tanto un PEM en texto como un DER ya en base64.
    """
    if not pem or not pem.strip():
        return ""
    texto = pem.strip()
    if "-----BEGIN" in texto:
        texto = "\n".join(
            linea
            for linea in texto.splitlines()
            if not linea.strip().startswith("-----")
        )
    return "".join(texto.split())


def certificado_configurado() -> tuple[str | None, str | None]:
    """El certificado y su clave, si están configurados. `(cert, clave)` o `(None, None)`.

    Decisión sobre el formato: se piden **dos ficheros PEM** (certificado y clave) y no un
    PKCS#12, porque para leer un `.p12` hace falta una librería de criptografía y **todavía no
    se ha añadido a propósito**: hasta que no exista el certificado de verdad no se puede probar
    con una clave real, y meter una dependencia grande que nadie ha ejercitado es peor que no
    tenerla. El día que llegue el certificado se decide: o se convierte a PEM con OpenSSL, que
    es una línea de comandos, o se añade la librería con sus tests.
    """
    certificado = (os.environ.get("CUEDIGITAL_IUWS_CERTIFICADO") or "").strip()
    clave = (os.environ.get("CUEDIGITAL_IUWS_CLAVE") or "").strip()
    if not certificado or not clave:
        return (None, None)
    try:
        return (
            open(certificado, encoding="utf-8").read(),
            open(clave, encoding="utf-8").read(),
        )
    except OSError:
        return (None, None)


def firmador_con_el_certificado_de_windows():
    """La función que firma **de verdad**, con el certificado del almacén de Windows.

    POR QUÉ ASÍ. Para presentar hay que mandar `data-signed`: el NIF firmado con la clave privada del
    certificado de dominio. Esa clave **no es exportable** —y no se debe exportar: una clave
    exportada es una clave que se puede copiar—, así que no se puede leer desde Python ni pasar a
    OpenSSL. Lo que sí se puede es **firmar donde vive**: Windows firma por dentro y aquí solo llega
    la firma. Lo hace `scripts/firmar_con_el_certificado.ps1`, que se comprobó con el certificado de
    David el 27/09/2026: firma y la firma **se verifica** con la clave pública del certificado.

    Devuelve `None` cuando no se puede firmar así (no es Windows, no está el script o no hay
    certificado configurado). **Nunca devuelve una firma inventada**: quien llama dice que no se pudo.
    """
    if os.name != "nt" or not FIRMADOR_DE_WINDOWS.exists():
        return None
    if not (os.environ.get("CUEDIGITAL_CERTIFICADO") or "").strip():
        return None

    def firmar(datos: bytes) -> bytes:
        orden = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(FIRMADOR_DE_WINDOWS),
            "-Texto",
            datos.decode("utf-8"),
        ]
        salida = subprocess.run(orden, capture_output=True, text=True, timeout=60)
        if salida.returncode != 0:
            raise OSError(
                "no se ha podido firmar con el certificado del almacén de Windows: "
                + (salida.stderr or "").strip()
            )
        return base64.b64decode(salida.stdout.strip())

    return firmar


def datos_firmados(valor: str, firmador=None) -> str | None:
    """El parámetro `data-signed`: el NIF o CIF firmado con la clave privada del certificado.

    El Anexo VI dice que el interfaz comprueba que ese dato corresponda con lo que tiene
    guardado, usando la clave pública del certificado que va en `certificate-sscc`.

    Se firma por este orden, y el primero que funcione manda:

    1. El `firmador` que se pase a mano (es lo que permite probar el flujo entero sin certificado).
    2. La librería `cryptography`, **si está instalada y hay un `.pem` configurado**. No está añadida
       a propósito: sin el certificado de verdad no se puede probar con una clave real.
    3. **El certificado del almacén de Windows**, por `firmar_con_el_certificado.ps1`. Es el camino
       que funciona con el certificado de David, porque su clave no es exportable y solo se puede
       usar donde vive.

    Si no funciona ninguno, se devuelve `None` y quien llama **dice que falta**. Nunca se devuelve
    una firma inventada: el interfaz la rechazaría o, peor, aceptaría algo mal firmado.
    """
    if not valor:
        return None

    if firmador is not None:
        firma = firmador(valor.encode("utf-8"))
        return base64.b64encode(firma).decode("ascii")

    firma = _firmar_con_cryptography(valor)
    if firma is not None:
        return firma

    firmar_en_windows = firmador_con_el_certificado_de_windows()
    if firmar_en_windows is not None:
        try:
            return base64.b64encode(firmar_en_windows(valor.encode("utf-8"))).decode("ascii")
        except (OSError, ValueError):
            return None

    return None


def _firmar_con_cryptography(valor: str) -> str | None:
    """Firmar con la librería `cryptography`, si está y si hay un `.pem` configurado."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        return None

    _certificado, clave_pem = certificado_configurado()
    if not clave_pem:
        return None
    try:
        clave = serialization.load_pem_private_key(clave_pem.encode("utf-8"), password=None)
        firma = clave.sign(valor.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    except Exception:  # noqa: BLE001 — una clave que no se puede leer es «no se pudo firmar»
        return None
    return base64.b64encode(firma).decode("ascii")


def falta_para_firmar() -> str:
    """Qué hace falta para poder firmar. Se dice tal cual, sin rodeos.

    Y lo que dice ha cambiado el 27/09/2026: **ya no hace falta exportar la clave**. Antes se pedía
    un `.pem` de la clave privada, que es justo lo que no se debe hacer con la de un certificado de
    verdad. Ahora se firma donde la clave vive.
    """
    return (
        "Para firmar el parámetro data-signed hace falta la clave privada del certificado de "
        "dominio. En este ordenador se firma con el certificado del almacén de Windows, que se "
        "busca por la variable CUEDIGITAL_CERTIFICADO (el NIF o la huella), y la clave no sale de "
        "ahí. En otro ordenador, o se pone el certificado en su almacén, o se configura "
        "CUEDIGITAL_IUWS_CERTIFICADO (el .pem del certificado) y CUEDIGITAL_IUWS_CLAVE (el .pem de "
        "la clave) y se instala `cryptography`."
    )


# --------------------------------------------------------------------------
# Las llamadas
# --------------------------------------------------------------------------


@dataclass
class Resultado:
    """Lo que ha pasado con una llamada: lo que contestó y si se pudo hacer."""

    hecha: bool
    codigo: int | None = None
    texto: str = ""
    respuesta: iuws.Respuesta | None = None
    mensaje: str = ""
    url: str = ""
    # Lo que se ha mandado, para poder enseñarlo cuando el interfaz dice que está mal.
    enviado: dict | None = None
    cabeceras: dict = field(default_factory=dict)


def _cabeceras(token: str | None, cabecera_cert: str | None) -> dict:
    """Las cabeceras de una llamada al IUWS, tal y como las documenta el Anexo VI."""
    cabeceras = {"Accept": "application/json"}
    if token:
        # El token va en Authorization, sin la palabra «Bearer»: el anexo dice «adjuntar el
        # jwt en la cabecera Authorization» y los ejemplos del anexo lo mandan pelado.
        cabeceras["Authorization"] = token
    if cabecera_cert:
        cabeceras["certificate-sscc"] = cabecera_cert
    return cabeceras


# Qué se considera «no se ha podido llegar». Decisión: **solo los fallos de red** (`httpx` los
# agrupa en `HTTPError`), no cualquier excepción. Un `except Exception` aquí taparía los fallos
# del propio programa y los disfrazaría de «no hay conexión», que es justo el error que hace
# perder una tarde entera buscando el problema en el cortafuegos. Esto se descubrió con un test
# que pasaba por el camino equivocado y salía diciendo que no había red.
FALLOS_DE_RED = (httpx.HTTPError,)


def _mensaje_de_la_respuesta(leida: iuws.Respuesta, codigo_http: int, si_va_bien: str) -> str:
    """Qué decir según lo que ha contestado el interfaz.

    Decisión importante, y esto es un fallo que se encontró con un test: **el interfaz contesta
    `200` aunque el resultado sea un error.** El código de verdad va en el cuerpo
    (`codigoResultado`), no en el estado HTTP. Mirar solo el `200` haría decir «comunicación
    establecida» cuando en realidad ha contestado `ERROR_VALIDAR_CREDENCIALES`, que es
    exactamente el error que uno tarda una tarde en encontrar.

    Así que manda el cuerpo: si el cuerpo dice OK, va bien; si dice un error, se cuenta el error
    con su nombre.
    """
    if leida.esta_ok:
        return si_va_bien
    if leida.codigo:
        # Se pone el nombre del código entre paréntesis a propósito: «La llamada no está
        # autorizada» es la explicación, pero el nombre (ERROR_VALIDAR_CREDENCIALES) es lo que
        # se busca en el manual y lo que hay que pegar en un correo a soporte.
        return f"{leida.mensaje or 'El interfaz ha contestado un error.'} ({leida.codigo})"
    return leida.mensaje or f"El interfaz ha contestado {codigo_http}."


def comprobar_version(base: str | None = None, transporte=None) -> Resultado:
    """Pregunta al interfaz con qué versión trabaja.

    **Es la única llamada que se puede hacer sin certificado y sin estar dado de alta**, así que
    es la que sirve para saber si hay camino hasta la Junta. Se puede usar hoy mismo.

    Comprobado contra el interfaz de Castilla y León: contesta `200 {"version": "3.11.4"}`.
    """
    base = base or iuws.configuracion()["base"]
    url = iuws.url_version(base)
    cliente = httpx.Client(timeout=iuws.ESPERA_SEGUNDOS, transport=transporte)
    try:
        respuesta = cliente.get(url)
    except FALLOS_DE_RED as error:
        return Resultado(
            hecha=True,
            codigo=None,
            url=url,
            mensaje=f"No se ha podido llegar al interfaz ({type(error).__name__}).",
        )

    version = ""
    try:
        version = str(respuesta.json().get("version") or "")
    except Exception:  # noqa: BLE001 — aquí sí: puede contestar texto y no JSON, y eso no es un
        # fallo, es una respuesta que hay que poder enseñar. Lo de arriba es distinto: allí un
        # error del programa no puede pasar por «no hay red».
        texto = respuesta.text.strip()[:80]
        coincidencia = re.search(r"\b\d+\.\d+\.\d+\b", texto)
        version = coincidencia.group() if coincidencia else texto

    return Resultado(
        hecha=True,
        codigo=respuesta.status_code,
        texto=respuesta.text[:500],
        url=url,
        mensaje=(
            f"El interfaz de la Junta contesta y trabaja con la versión {version}."
            if respuesta.status_code == 200
            else f"El interfaz ha contestado {respuesta.status_code}."
        ),
        cabeceras={"version": version},
    )


def comprobar_donde_contesta(base_configurada: str | None = None, transporte=None) -> dict:
    """Prueba a ver **a qué dirección** contesta la Junta, y no solo si contesta.

    Por qué existe: permite probar la dirección configurada y, si no responde, la del
    organismo pagador. En la versión 3.11.4 el entorno de integración sí responde en
    `/IUWS/api/version`; la ruta anterior sin `/api/` devuelve 404.

    Así que si la dirección configurada no contesta en el método de versión, se prueban las de
    las comunidades (Anexo X). Como mucho son dos llamadas, y las dos son al método abierto.

    Decisión: se para en cuanto una contesta 200. Seguir preguntando a servidores que ya se sabe
    que no van a contestar es darle trabajo a la Junta sin motivo.
    """
    primera = base_configurada or iuws.configuracion()["base"]
    candidatas: list[str] = [primera]
    for base in iuws.BASES_CONOCIDAS:
        if base not in candidatas:
            candidatas.append(base)

    probadas: list[dict] = []
    buena: dict | None = None
    for base in candidatas:
        resultado = comprobar_version(base, transporte=transporte)
        fila = {
            "base": base,
            "url": resultado.url,
            "codigo": resultado.codigo,
            "version": resultado.cabeceras.get("version", ""),
            "mensaje": resultado.mensaje,
        }
        probadas.append(fila)
        if resultado.codigo == 200:
            buena = fila
            break

    if buena is None:
        mensaje = textos.IUWS["conexion_sin_respuesta"]
        if any(fila["codigo"] is not None for fila in probadas):
            mensaje = textos.IUWS["conexion_404"]
    elif probadas[0] is buena:
        mensaje = textos.IUWS["conexion_en_la_configurada"].format(version=buena["version"])
    else:
        mensaje = textos.IUWS["conexion_en_otra_direccion"].format(
            base=buena["base"], version=buena["version"]
        )

    return {"probadas": probadas, "buena": buena, "mensaje": mensaje}


def pedir_token(
    base: str | None = None, nombre_app: str | None = None, transporte=None
) -> Resultado:
    """Pide el token de sesión: es la puerta de todo lo demás.

    Necesita el certificado **de cliente**: lo exige el propio servidor al negociar TLS, así que
    si no está configurado no se llama. Y el nombre comercial tiene que estar dado de alta en el
    interfaz, o contesta `ERROR_VALIDAR_CREDENCIALES`.
    """
    config = iuws.configuracion()
    base = base or config["base"]
    nombre_app = nombre_app or config["nombre_comercial"]
    if not nombre_app:
        return Resultado(hecha=False, mensaje=iuws.por_que_falta("nombre_comercial"))

    certificado, clave = certificado_configurado()
    if not certificado:
        return Resultado(hecha=False, mensaje=iuws.por_que_falta("certificado"))

    url = iuws.url_comunicacion(base, nombre_app)
    cliente = httpx.Client(
        timeout=iuws.ESPERA_SEGUNDOS,
        transport=transporte,
        # httpx espera rutas de fichero; `certificado_configurado()` devuelve el contenido
        # PEM para la firma. En las pruebas con MockTransport no se negocia TLS.
        cert=(os.environ["CUEDIGITAL_IUWS_CERTIFICADO"], os.environ["CUEDIGITAL_IUWS_CLAVE"])
        if transporte is None else None,
    )
    try:
        respuesta = cliente.get(url)
    except FALLOS_DE_RED as error:
        return Resultado(
            hecha=True,
            url=url,
            mensaje=f"No se ha podido establecer la comunicación ({type(error).__name__}).",
        )

    leida = iuws.leer_respuesta(respuesta.text)
    return Resultado(
        hecha=True,
        codigo=respuesta.status_code,
        texto=respuesta.text[:500],
        respuesta=leida,
        url=url,
        mensaje=_mensaje_de_la_respuesta(
            leida,
            respuesta.status_code,
            "Comunicación establecida: ya se puede llamar al resto de métodos.",
        ),
    )


def comprobar_estado(id_peticion: int | str, token: str, base: str | None = None, transporte=None) -> Resultado:
    """Pregunta cómo va una carga que ya se ha mandado.

    Decisión: **no hace falta el certificado para esta llamada** si ya se tiene el token. Lo que
    hace falta es el token, y el anexo dice que el token se obtiene con el certificado. Así que
    en la práctica sí, pero el cliente no lo exige: si alguien tiene un token, puede preguntar.
    """
    base = base or iuws.configuracion()["base"]
    url = iuws.url_comprobar_estado(base, id_peticion)
    if not token:
        return Resultado(hecha=False, url=url, mensaje="Hace falta el token de sesión.")

    cliente = httpx.Client(timeout=iuws.ESPERA_SEGUNDOS, transport=transporte)
    try:
        respuesta = cliente.get(url, headers=_cabeceras(token, None))
    except FALLOS_DE_RED as error:
        return Resultado(hecha=True, url=url, mensaje=f"No se ha podido preguntar ({type(error).__name__}).")

    leida = iuws.leer_respuesta(respuesta.text)
    return Resultado(
        hecha=True,
        codigo=respuesta.status_code,
        texto=respuesta.text[:2000],
        respuesta=leida,
        url=url,
        mensaje=leida.mensaje or f"El interfaz ha contestado {respuesta.status_code}.",
    )


@lru_cache(maxsize=1)
def _validador_oficial() -> Draft7Validator:
    esquema = json.loads(iuws.RUTA_ESQUEMA_OFICIAL.read_text(encoding="utf-8"))
    Draft7Validator.check_schema(esquema)
    return Draft7Validator(esquema)


def errores_del_esquema(cuerpo: dict) -> list[str]:
    """Qué incumple un cuerpo del esquema oficial, como lista de rutas de campo.

    Se expone aparte de `enviar_cuaderno` porque hace falta en dos momentos distintos: **antes
    de mandar** (para no mandar algo que se sabe que va a fallar) y **al revisar el cuaderno**
    (para poder decir qué campo falta, en vez de un error técnico que no dice nada). Estando en
    un solo sitio, no pueden decir cosas distintas.

    Cuando **falta un campo obligatorio**, el esquema no apunta al campo: apunta al objeto que
    lo contiene y el nombre solo sale en el mensaje. Por eso se añade entre paréntesis:
    `CUADERNO.0` no le dice a nadie qué falta, y `CUADERNO.0 (CodigoRea)` sí.
    """
    salida = []
    for error in _validador_oficial().iter_errors(cuerpo):
        ruta = ".".join(str(parte) for parte in error.absolute_path) or "CUADERNO"
        if error.validator == "required" and error.message:
            trozos = error.message.split("'")
            if len(trozos) > 1:
                ruta = f"{ruta} ({trozos[1]})"
        salida.append(ruta)
    return salida


def enviar_cuaderno(paquete: dict, token: str, base: str | None = None, transporte=None) -> Resultado:
    """Manda el JSON del cuaderno. Devuelve el id de la petición para poder seguirla.

    **Esto no se puede usar todavía**, y se dice antes de intentarlo: el cuerpo tiene que ir en
    el formato del descriptor v3.11.4. Se comprueba contra el esquema JSON oficial antes de
    llamar al servidor. La marca local `formato` nunca viaja en el cuerpo IUWS.
    """
    if paquete.get("formato") != iuws.FORMATO_DESCRIPTOR:
        return Resultado(
            hecha=False,
            mensaje=(
                "Ese paquete no está en el formato del descriptor v3.11.4, así que no se manda. "
                "El interfaz lo rechazaría, y mandar algo que se sabe que va a fallar no ayuda "
                "a nadie. Ver docs/INTEGRACION_IUWS.md."
            ),
        )

    if set(paquete) != {"formato", "CUADERNO"} or not paquete["CUADERNO"]:
        return Resultado(hecha=False, mensaje="El paquete no contiene un cuaderno oficial completo.")
    cuerpo_oficial = {"CUADERNO": paquete["CUADERNO"]}
    fallos = errores_del_esquema(cuerpo_oficial)
    if fallos:
        return Resultado(
            hecha=False,
            mensaje=f"El paquete no cumple el esquema oficial v3.11.4 en {fallos[0]}.",
        )

    base = base or iuws.configuracion()["base"]
    url = iuws.url_crear(base)
    if not token:
        return Resultado(hecha=False, url=url, mensaje="Hace falta el token de sesión.")

    cuerpo = json.dumps(cuerpo_oficial, ensure_ascii=False).encode("utf-8")
    cabeceras = _cabeceras(token, None)
    cabeceras["Content-Type"] = "application/json; charset=utf-8"

    cliente = httpx.Client(timeout=iuws.ESPERA_SEGUNDOS, transport=transporte)
    try:
        respuesta = cliente.post(url, content=cuerpo, headers=cabeceras)
    except FALLOS_DE_RED as error:
        return Resultado(hecha=True, url=url, mensaje=f"No se ha podido mandar ({type(error).__name__}).")

    leida = iuws.leer_respuesta(respuesta.text)
    return Resultado(
        hecha=True,
        codigo=respuesta.status_code,
        texto=respuesta.text[:2000],
        respuesta=leida,
        url=url,
        enviado=cuerpo_oficial,
        mensaje=(
            f"Carga recibida. Número de petición: {leida.id_peticion}. Con ese número se puede "
            "preguntar cómo va con comprobarEstado."
            if leida.id_peticion
            else _mensaje_de_la_respuesta(
                leida,
                respuesta.status_code,
                "El interfaz ha recibido la carga, pero no ha dado número de petición.",
            )
        ),
    )
