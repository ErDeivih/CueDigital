"""Autenticación y aislamiento entre explotaciones.

Decisión: se resuelve con la biblioteca estándar (hashlib + hmac) en vez de añadir
passlib, bcrypt y python-jose. Para un MVP de un solo agricultor por cuenta, tres
dependencias más solo añaden superficie de fallo. El hash es PBKDF2-SHA256 con sal
por usuario, que es sólido, y el token va firmado con HMAC-SHA256.

Lo que NO se hace aquí y habrá que hacer antes de abrirlo a clientes: rotación de
claves, revocación de tokens, límite de intentos y doble factor. Está anotado para
que no se olvide.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

ITERACIONES_PBKDF2 = 240_000

# Por debajo de esto no se acepta, y menos aún en producción. Existe la variable de entorno
# porque la suite de tests registra una cuenta en casi todos los tests, y 240.000 iteraciones
# por registro son casi seis minutos de suite. Se baja SOLO si además está puesto
# `CUEDIGITAL_ENTORNO=pruebas`: hacen falta dos condiciones a propósito, para que un descuido
# en el servidor de verdad no deje las claves protegidas con mil iteraciones.
ITERACIONES_MINIMAS_DE_VERDAD = 100_000

DURACION_TOKEN_SEGUNDOS = 60 * 60 * 24 * 30  # 30 días

LONGITUD_CLAVE_MINIMA = 8


def entorno_de_pruebas() -> bool:
    return (os.environ.get("CUEDIGITAL_ENTORNO") or "").strip().lower() == "pruebas"


def iteraciones_pbkdf2() -> int:
    """Cuántas veces se deriva la clave. Falla fuerte si alguien intenta bajarlo de verdad.

    El número de iteraciones se guarda **dentro** de cada hash, así que cambiarlo no rompe
    las claves que ya están guardadas: cada una se verifica con el número con el que se creó.
    """
    crudo = (os.environ.get("CUEDIGITAL_ITERACIONES_PBKDF2") or "").strip()
    if not crudo:
        return ITERACIONES_PBKDF2
    try:
        valor = int(crudo)
    except ValueError:
        raise RuntimeError(
            "CUEDIGITAL_ITERACIONES_PBKDF2 tiene que ser un número entero."
        ) from None
    if valor < ITERACIONES_MINIMAS_DE_VERDAD and not entorno_de_pruebas():
        raise RuntimeError(
            f"CUEDIGITAL_ITERACIONES_PBKDF2 está en {valor}, por debajo del mínimo de "
            f"{ITERACIONES_MINIMAS_DE_VERDAD}. Eso dejaría las claves de los agricultores "
            "fáciles de adivinar. Si de verdad es un entorno de pruebas, pon también "
            "CUEDIGITAL_ENTORNO=pruebas."
        )
    return valor


def clave_secreta() -> str:
    """Clave para firmar los tokens.

    En producción DEBE venir del entorno. Si no viene, se genera una aleatoria: es
    preferible que las sesiones se caigan al reiniciar a que el programa arranque
    con una clave conocida y cualquiera pueda firmar tokens.
    """
    return os.environ.get("CUEDIGITAL_SECRETO") or secrets.token_urlsafe(48)


_SECRETO_EN_MEMORIA = clave_secreta()


def hash_clave(clave: str) -> str:
    if len(clave) < LONGITUD_CLAVE_MINIMA:
        raise ValueError(f"La clave tiene que tener al menos {LONGITUD_CLAVE_MINIMA} caracteres")
    iteraciones = iteraciones_pbkdf2()
    sal = secrets.token_bytes(16)
    derivada = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${sal.hex()}${derivada.hex()}"


def verificar_clave(clave: str, almacenada: str) -> bool:
    try:
        algoritmo, iteraciones, sal_hex, esperado_hex = almacenada.split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    derivada = hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(sal_hex), int(iteraciones)
    )
    # compare_digest: comparación en tiempo constante, para no filtrar la clave.
    return hmac.compare_digest(derivada.hex(), esperado_hex)


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("ascii").rstrip("=")


def _de_b64(texto: str) -> bytes:
    relleno = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode(texto + relleno)


def crear_token(usuario_id: int, explotacion_id: int, segundos: int = DURACION_TOKEN_SEGUNDOS) -> str:
    cuerpo = {
        "uid": usuario_id,
        "eid": explotacion_id,
        "exp": int(time.time()) + segundos,
    }
    carga = _b64(json.dumps(cuerpo, separators=(",", ":")).encode("utf-8"))
    firma = hmac.new(_SECRETO_EN_MEMORIA.encode("utf-8"), carga.encode("ascii"), hashlib.sha256).digest()
    return f"{carga}.{_b64(firma)}"


def leer_token(token: str) -> dict | None:
    """Devuelve el contenido del token, o None si no vale.

    Se comprueba la firma ANTES de mirar la fecha: así un token manipulado no
    puede provocar trabajo extra ni filtrar información.
    """
    if not token or "." not in token:
        return None
    carga, firma_texto = token.rsplit(".", 1)
    esperada = hmac.new(
        _SECRETO_EN_MEMORIA.encode("utf-8"), carga.encode("ascii"), hashlib.sha256
    ).digest()
    try:
        recibida = _de_b64(firma_texto)
    except Exception:
        return None
    if not hmac.compare_digest(esperada, recibida):
        return None
    try:
        cuerpo = json.loads(_de_b64(carga))
    except Exception:
        return None
    if int(cuerpo.get("exp", 0)) < int(time.time()):
        return None
    return cuerpo
