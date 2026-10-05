"""Los ficheros que sube el agricultor: dónde van, cuáles se admiten y cómo se guardan.

Esto lo usaban solo los boletines de laboratorio. Al añadir la **documentación anexa** (los
contratos, las facturas, los albaranes de entrega de envases a Sigfito) hizo falta lo mismo otra
vez, y copiar esta lógica habría sido la peor opción posible: es código de seguridad —de dónde
sale la ruta, qué tipos se admiten, cuánto se deja subir— y tener dos copias significa que un día
se arregla una y la otra se queda como estaba. Así que está en un solo sitio.

## Las tres decisiones que hay aquí, y por qué

1. **Los ficheros van a disco, no a la base de datos y no al repositorio.** Un contrato de un
   agricultor no puede acabar dentro de un fichero que se sube a git, y meter PDFs en la base de
   datos hace que cada copia de seguridad pese cientos de megas. La carpeta está en el
   `.gitignore` y se puede cambiar con `CUEDIGITAL_ADJUNTOS`, que es lo que hace falta en el
   servidor de verdad (los datos van en un volumen aparte del código).
2. **El nombre del fichero lo decide el programa, no el navegador.** El nombre que manda el
   navegador se guarda solo para enseñarlo. Si se usara para la ruta, un nombre como
   `../../app/main.py` escribiría donde no debe, y adivinar la ruta de otro agricultor sería
   cuestión de probar números.
3. **Al descargar se comprueba que la ruta sigue dentro de su carpeta.** La ruta viene de la base
   de datos: si alguien la cambiara a mano, esto impide que se pueda leer un fichero de fuera.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

# Un fichero se guarda como mucho así. Sin este tope, un fichero enorme se leería entero en
# memoria antes de poder rechazarlo, que es justo lo que se quiere evitar.
MAXIMO_BYTES = 12 * 1024 * 1024

# Lo que se lee por trozos, para poder cortar en cuanto pasa del tope.
TROZO_BYTES = 1024 * 1024

# Los boletines de laboratorio: un PDF o una foto que hace el móvil.
TIPOS_BOLETIN = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}

# La documentación anexa es más variada, porque lo que pide una inspección no tiene un formato
# fijo: el contrato de arrendamiento suele ser un PDF, la factura del proveedor puede venir en
# PDF o en una hoja de cálculo, y el albarán de Sigfito puede ser una foto del resguardo.
TIPOS_DOCUMENTO = {
    **TIPOS_BOLETIN,
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.oasis.opendocument.text": ".odt",
    "application/vnd.oasis.opendocument.spreadsheet": ".ods",
    "application/vnd.oasis.opendocument.presentation": ".odp",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/zip": ".zip",
}


def carpeta_de_adjuntos() -> Path:
    """Dónde se guardan los ficheros que sube el agricultor."""
    configurada = os.environ.get("CUEDIGITAL_ADJUNTOS")
    if configurada:
        return Path(configurada)
    return Path(__file__).resolve().parents[2] / "datos" / "adjuntos"


def nombre_humano(tipo: str, permitidos: dict[str, str]) -> str:
    """Cómo se le dice al agricultor qué ficheros valen, en sus palabras.

    Se escribe a partir de la lista de tipos admitidos, no a mano: así, si mañana se admite un
    formato más, el mensaje no se queda diciendo lo de antes.
    """
    extensiones = sorted({extension.lstrip(".").upper() for extension in permitidos.values()})
    return " o ".join([", ".join(extensiones[:-1]), extensiones[-1]]) if len(extensiones) > 1 else extensiones[0]


def _revisar(fichero: UploadFile, contenido: bytes, permitidos: dict[str, str]) -> str:
    """Comprueba el tipo y el tamaño. Devuelve la extensión con la que se guardará."""
    tipo = (fichero.content_type or "").split(";")[0].strip().lower()
    if tipo not in permitidos:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ese tipo de fichero no vale ({tipo or 'sin decir'}). "
                f"Puedes subir: {nombre_humano(tipo, permitidos)}."
            ),
        )
    if not contenido:
        raise HTTPException(status_code=422, detail="El fichero está vacío.")
    if len(contenido) > MAXIMO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Ese fichero es demasiado grande ({len(contenido) // (1024 * 1024)} MB). "
                f"El máximo son {MAXIMO_BYTES // (1024 * 1024)} MB."
            ),
        )
    return permitidos[tipo]


async def leer_el_fichero(
    fichero: UploadFile, permitidos: dict[str, str], maximo: int | None = None
) -> tuple[bytes, str]:
    """Lee lo que ha subido el navegador, por trozos, y devuelve `(contenido, tipo)`.

    Se lee a trozos y se corta en cuanto pasa del tope: así un fichero de dos gigas no se llega a
    cargar entero en memoria. El tipo se mira **antes** de leer nada, para no gastar trabajo
    leyendo un fichero que se va a rechazar.
    """
    tope = maximo or MAXIMO_BYTES
    tipo = (fichero.content_type or "").split(";")[0].strip().lower()
    if tipo not in permitidos:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ese tipo de fichero no vale ({tipo or 'sin decir'}). "
                f"Puedes subir: {nombre_humano(tipo, permitidos)}."
            ),
        )

    trozos: list[bytes] = []
    leidos = 0
    while True:
        trozo = await fichero.read(TROZO_BYTES)
        if not trozo:
            break
        leidos += len(trozo)
        if leidos > tope:
            raise HTTPException(
                status_code=413,
                detail=f"Ese fichero pasa de {tope // (1024 * 1024)} MB. Sube otro.",
            )
        trozos.append(trozo)
    return b"".join(trozos), tipo


def guardar_en_disco(
    *,
    explotacion_id: int,
    prefijo: str,
    fichero: UploadFile,
    contenido: bytes,
    permitidos: dict[str, str],
) -> tuple[str, str, str, int]:
    """Escribe el fichero en disco. Devuelve `(nombre, ruta_relativa, tipo, bytes)`.

    `nombre` es el que manda el navegador, recortado, y **solo sirve para enseñarlo**.
    `ruta_relativa` es la que se guarda en la base de datos, relativa a la carpeta de adjuntos:
    guardar la ruta completa ataría los datos a la máquina donde se instaló el programa, y el
    día que se mueva el volumen las referencias dejarían de valer.
    """
    extension = _revisar(fichero, contenido, permitidos)
    raiz = carpeta_de_adjuntos()
    carpeta = raiz / str(explotacion_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    # El identificador aleatorio evita que subir dos veces el mismo papel se pise el uno al otro,
    # y que se pueda adivinar la ruta de otro agricultor probando números.
    destino = carpeta / f"{prefijo}-{uuid.uuid4().hex[:10]}{extension}"
    destino.write_bytes(contenido)
    tipo = (fichero.content_type or "").split(";")[0].strip().lower()
    return (
        (fichero.filename or prefijo)[:200],
        destino.relative_to(raiz).as_posix(),
        tipo,
        len(contenido),
    )


def ruta_segura(ruta_relativa: str) -> Path:
    """La ruta de un fichero, comprobando que sigue dentro de la carpeta de adjuntos.

    Es una comprobación de seguridad, no un adorno: la ruta viene de la base de datos, y este
    programa guarda ahí lo que le llega. Si alguien la cambiara a mano, esto impide que se pueda
    leer un fichero del sistema desde la web.
    """
    raiz = carpeta_de_adjuntos().resolve()
    destino = (raiz / ruta_relativa).resolve()
    if not str(destino).startswith(str(raiz)) or not destino.is_file():
        raise HTTPException(status_code=404, detail="Ese fichero ya no está.")
    return destino


def borrar_del_disco(ruta_relativa: str | None) -> None:
    """Borra un fichero, y si no puede, no pasa nada.

    Que no se pueda borrar un fichero viejo **no puede impedir** guardar el nuevo: el agricultor
    ya ha hecho la foto y ha pulsado el botón. Un fichero huérfano ocupa sitio; un agricultor que
    no puede guardar su papel, no.
    """
    if not ruta_relativa:
        return
    try:
        (carpeta_de_adjuntos() / ruta_relativa).unlink(missing_ok=True)
    except OSError:
        pass
