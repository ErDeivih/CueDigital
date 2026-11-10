"""**La seguridad de lo que se sirve por web** (10/11/2026).

## Por qué existe este módulo

Los dos coordinadores avisaron de que la app había estado publicada en un túnel abierto a internet
con **las parcelas reales de un cliente**. Eso ya está cerrado (el acceso va solo por la red de
Tailscale), y además de cerrar hay que **endurecer**: cabeceras que el navegador respeta y el alta
de cuentas cerrada salvo que se pida lo contrario.

## Las dos piezas

1. **Cabeceras de seguridad** (`CABECERAS`) para todas las respuestas. Se ponen aquí, en un solo
   sitio, y no en cada router: una cabecera que se olvida en una puerta es una cabecera que no
   existe.
2. **El alta de cuentas** (`registro_abierto`): cerrada por defecto en producción y abierta en
   desarrollo y en las pruebas, que es donde hace falta crear cuentas. Se enciende con
   `CUEDIGITAL_REGISTRO=abierto`.
"""

from __future__ import annotations

import os

# Cabeceras que se ponen en **todas** las respuestas. Lo que hace cada una:
#
#  · `X-Content-Type-Options: nosniff` — el navegador no adivina el tipo de un fichero: un `.txt`
#    que lleve dentro un script no se ejecuta como script.
#  · `X-Frame-Options: DENY` y `frame-ancestors 'none'` — la app no se puede meter dentro de otra
#    página (nada de clickjacking).
#  · `Referrer-Policy: no-referrer` — la dirección de la app no se va en el `Referer` a otros sitios.
#  · `Permissions-Policy` — se apagan cámara, micrófono y ubicación del navegador: la app no los usa.
#  · `Content-Security-Policy` — la pantalla solo carga de su propio servidor; las imágenes, además,
#    de `data:` y `blob:` (el mapa y las descargas las sirve el propio programa); nada de otras
#    fuentes, ni `frame-ancestors`.
#  · `Cross-Origin-Opener-Policy: same-origin` — otra página no puede quedarse con la ventana.
CABECERAS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "Cross-Origin-Opener-Policy": "same-origin",
}

# HSTS solo tiene sentido cuando la petición llega por HTTPS: mandarlo por HTTP no hace nada y en
# desarrollo molesta (el navegador se queda con «este sitio es https» para el localhost).
HSTS = "max-age=31536000; includeSubDomains"


def cabeceras_para(*, https: bool) -> dict[str, str]:
    """Las cabeceras de una respuesta, con HSTS solo si la petición vino por HTTPS."""
    cabeceras = dict(CABECERAS)
    if https:
        cabeceras["Strict-Transport-Security"] = HSTS
    return cabeceras


# --------------------------------------------------------------------------- el alta de cuentas
#
# **Cerrada por defecto en producción** (10/11/2026). Durante el desarrollo hace falta crear
# cuentas a todas horas, así que en pruebas y en local está abierta. Lo que no puede es quedarse
# abierta por descuido en el servidor de verdad: cualquiera que sepa la dirección podría darse de
# alta y ver sus propias tierras (no las de otro, pero sí usar el servicio).
def registro_abierto(*, entorno: str | None = None, valor: str | None = None) -> bool:
    """¿Se puede dar de alta una cuenta nueva?

    1. Si `CUEDIGITAL_REGISTRO` está puesto, manda: `abierto` la abre y cualquier otra cosa la cierra.
    2. Si no está puesto, se abre **solo** fuera de producción (pruebas, local).
    """
    entorno = entorno if entorno is not None else os.environ.get("CUEDIGITAL_ENTORNO", "")
    valor = valor if valor is not None else os.environ.get("CUEDIGITAL_REGISTRO", "")
    if valor:
        return valor.strip().lower() == "abierto"
    es_produccion = entorno.strip().lower() in ("", "produccion", "producción", "production")
    return not es_produccion
