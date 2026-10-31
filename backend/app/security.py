"""Autenticación y aislamiento entre explotaciones.

Decisión: se resuelve con la biblioteca estándar (hashlib + hmac) en vez de añadir
passlib, bcrypt y python-jose. Para un MVP de un solo agricultor por cuenta, tres
dependencias más solo añaden superficie de fallo. El hash es PBKDF2-SHA256 con sal
por usuario, que es sólido, y el token va firmado con HMAC-SHA256.

Lo que SÍ se hace aquí desde D06 (19/10/2026):

- **Rotación del secreto de firma**: `CUEDIGITAL_SECRETO` es el actual y
  `CUEDIGITAL_SECRETO_ANTERIOR` permite seguir aceptando los vale firmados antes de
  cambiarlo, el tiempo justo para que la gente vuelva a entrar. En producción, sin
  secreto (o con menos de 32 caracteres) el programa **no arranca**.
- **Revocación de los vales**: cada vale lleva la versión de sesión de su cuenta
  (`tv`, 0 si es de antes de D06). Subirla invalida todos los vales de esa cuenta.

Lo que NO se hace aquí todavía: doble factor. El límite de intentos vive en
`app/limites.py` porque necesita saber la dirección de quien llama.
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


LONGITUD_MINIMA_DEL_SECRETO = 32


def entorno_de_produccion() -> bool:
    """Si esto es una instalación de verdad y no la suite ni un banco de pruebas.

    Solo se aceptan nombres explícitos: dejar la variable vacía en un servidor no
    puede parecer «modo pruebas» por accidente.
    """
    return (os.environ.get("CUEDIGITAL_ENTORNO") or "").strip().lower() in {
        "produccion",
        "producción",
        "prod",
        "production",
    }


def secretos_de_firma() -> tuple[str, ...]:
    """Los secretos con los que se firma y se comprueba un vale, de nuevo a viejo.

    El primero firma; todos comprueban. Así se puede poner el secreto nuevo en
    `CUEDIGITAL_SECRETO`, dejar el viejo en `CUEDIGITAL_SECRETO_ANTERIOR`, reiniciar
    y que nadie se quede fuera; después se quita el anterior.
    """
    actual = (os.environ.get("CUEDIGITAL_SECRETO") or "").strip()
    anterior = (os.environ.get("CUEDIGITAL_SECRETO_ANTERIOR") or "").strip()
    if entorno_de_produccion():
        if not actual:
            raise RuntimeError(
                "Falta CUEDIGITAL_SECRETO. En producción no se genera uno al azar: eso "
                "cerraría todas las sesiones al reiniciar. Pon un secreto de al menos "
                f"{LONGITUD_MINIMA_DEL_SECRETO} caracteres."
            )
        if len(actual) < LONGITUD_MINIMA_DEL_SECRETO:
            raise RuntimeError(
                f"CUEDIGITAL_SECRETO tiene {len(actual)} caracteres; en producción hacen "
                f"falta al menos {LONGITUD_MINIMA_DEL_SECRETO}."
            )
        if anterior and len(anterior) < LONGITUD_MINIMA_DEL_SECRETO:
            raise RuntimeError(
                "CUEDIGITAL_SECRETO_ANTERIOR es demasiado corto: tiene que tener al menos "
                f"{LONGITUD_MINIMA_DEL_SECRETO} caracteres, igual que el actual."
            )
    else:
        # En local y en la suite se puede funcionar sin secreto: se genera uno por
        # proceso. Las sesiones se caen al reiniciar, y eso es visible y no peligroso.
        actual = actual or secrets.token_urlsafe(48)
    if anterior and anterior != actual:
        return (actual, anterior)
    return (actual,)


def clave_secreta() -> str:
    """El secreto que firma ahora. Se conserva por compatibilidad con quien lo llame."""
    return _SECRETOS_EN_MEMORIA[0]


_SECRETOS_EN_MEMORIA = secretos_de_firma()


def _recargar_secretos_para_pruebas() -> None:
    """Vuelve a leer el entorno. Solo lo usan los tests de rotación y el arranque."""
    global _SECRETOS_EN_MEMORIA
    _SECRETOS_EN_MEMORIA = secretos_de_firma()


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


def _firmar(carga: str, secreto: str) -> str:
    return _b64(
        hmac.new(secreto.encode("utf-8"), carga.encode("ascii"), hashlib.sha256).digest()
    )


def crear_token(
    usuario_id: int,
    explotacion_id: int,
    segundos: int = DURACION_TOKEN_SEGUNDOS,
    version: int = 0,
) -> str:
    """Un vale para entrar. `version` es la versión de sesión de la cuenta.

    Los vales de antes de D06 no llevan `tv` y se tratan como versión 0; por eso el
    valor por defecto es 0 y una cuenta existente sigue entrando sin tocar nada.
    """
    cuerpo = {
        "uid": usuario_id,
        "eid": explotacion_id,
        "tv": int(version or 0),
        "exp": int(time.time()) + segundos,
    }
    carga = _b64(json.dumps(cuerpo, separators=(",", ":")).encode("utf-8"))
    return f"{carga}.{_firmar(carga, _SECRETOS_EN_MEMORIA[0])}"


def leer_token(token: str) -> dict | None:
    """Devuelve el contenido del token, o None si no vale.

    Se comprueba la firma ANTES de mirar la fecha: así un token manipulado no
    puede provocar trabajo extra ni filtrar información. Se aceptan los secretos
    actual y anterior para que rotar el secreto no eche a nadie de su cuaderno.
    """
    if not token or "." not in token:
        return None
    carga, firma_texto = token.rsplit(".", 1)
    try:
        recibida = _de_b64(firma_texto)
    except Exception:
        return None
    firma_buena = any(
        hmac.compare_digest(_firmar(carga, secreto), firma_texto)
        for secreto in _SECRETOS_EN_MEMORIA
    )
    if not firma_buena:
        return None
    try:
        cuerpo = json.loads(_de_b64(carga))
    except Exception:
        return None
    if int(cuerpo.get("exp", 0)) < int(time.time()):
        return None
    return cuerpo
