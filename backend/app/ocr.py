"""Leer el texto que hay dentro de una foto o de un papel escaneado.

## Para qué

Una factura llega de tres maneras: en **PDF de verdad** (con su texto dentro, que se lee sin más),
en **papel** (una foto con el móvil) o **escaneada** (un PDF que por dentro es una imagen). Las dos
últimas no tienen texto: hay que **mirar la imagen y reconocer las letras**, que es lo que hace
Tesseract.

Tesseract es un programa aparte, no una librería de Python. Se usa así a propósito:

1. **No engorda las dependencias del proyecto.** `requirements.txt` se lee entero en dos minutos y
   eso es una decisión del proyecto: meter aquí un OCR de Python de verdad (EasyOCR, PaddleOCR)
   son cientos de megas y modelos que hay que descargar.
2. **Si no está, se dice y se sigue.** Sin el programa, la aplicación funciona igual: el agricultor
   sube la foto, se guarda como justificante y teclea los datos. Lo que **no** se hace nunca es
   inventarse lo que pone el papel.

## Y por eso el idioma importa, y se dice cuál se ha usado

Tesseract lee con un idioma que hay que tener instalado. Si solo está el inglés, los números
—cantidades, precios, NIF, fechas— se leen bien (los dígitos no son de ningún idioma), pero las
palabras con tilde y la eñe salen mal: «PEÑARANDA» se lee «Pefiaranda». La aplicación **lo dice en
la pantalla** en vez de disimularlo, porque el agricultor tiene que saber que lo que ve puede
llevar erratas y que es él quien confirma el dato.
"""

from __future__ import annotations

import functools
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Dónde suele estar el programa cuando no está en el PATH. En Windows el instalador no lo añade al
# PATH, así que buscarlo solo con `shutil.which` no basta: en el ordenador donde se probó esto
# estaba en `C:\Program Files\Tesseract-OCR` y `shutil.which` no lo encontraba.
RUTAS_CONOCIDAS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    "/opt/homebrew/bin/tesseract",
)

# El idioma que se le pide, por orden de preferencia: español e inglés juntos si están los dos (las
# facturas traen palabras en los dos idiomas), y si no, el que haya.
IDIOMAS_PREFERIDOS = ("spa+eng", "spa", "eng")

# Cuánto se espera como mucho a que el programa conteste. Una factura ocupa una página y tarda
# segundos; si tarda más, algo va mal y es mejor decirlo que dejar al agricultor esperando.
ESPERA_SEGUNDOS = 60.0

# Cómo se le pide que mire la imagen. `6` es «un bloque de texto uniforme», que es lo que es una
# factura, y se comprobó contra un ejemplo de verdad: con el modo por defecto (`3`) la tabla se
# partía en trozos y los números salían separados de sus descripciones.
MODO_DE_PAGINA = 6

# Cuántas páginas de un PDF escaneado se miran. Una factura es de una página o dos; un documento
# de cincuenta páginas no se lee entero para no tener al agricultor esperando.
MAXIMO_PAGINAS = 3

# A partir de aquí (píxeles de ancho) la imagen ya se lee bien y no hace falta hacerla más grande.
ANCHO_SUFICIENTE = 1600


class SinLector(RuntimeError):
    """No hay ningún programa de reconocimiento de letras instalado."""


@functools.lru_cache(maxsize=1)
def carpeta_de_idiomas() -> str:
    """Dónde están los idiomas del lector.

    Si el proyecto tiene sus propios idiomas en `data/ocr/tessdata` (ver
    `scripts/bajar_idioma_ocr.py`), se usan esos y **no se toca la instalación del sistema**: así el
    español se puede instalar sin permisos de administrador y sin cambiar nada del ordenador de
    nadie. Si no están ahí, se devuelve cadena vacía y el programa usa los del sistema.
    """
    propia = Path(__file__).resolve().parents[2] / "data" / "ocr" / "tessdata"
    return str(propia) if propia.is_dir() and any(propia.glob("*.traineddata")) else ""


def _entorno() -> dict:
    """El entorno con el que se llama al lector, con los idiomas del proyecto si los hay."""
    entorno = dict(os.environ)
    propia = carpeta_de_idiomas()
    if propia:
        entorno["TESSDATA_PREFIX"] = propia
    return entorno


@functools.lru_cache(maxsize=1)
def programa() -> str | None:
    """El programa de reconocimiento de letras, o `None` si no está.

    Se mira una vez y se recuerda. Primero la variable de entorno (para quien lo tenga en un sitio
    raro), después el PATH y por último los sitios donde lo deja el instalador.
    """
    configurado = (os.environ.get("CUEDIGITAL_OCR") or "").strip()
    if configurado and Path(configurado).exists():
        return configurado
    en_el_path = shutil.which("tesseract")
    if en_el_path:
        return en_el_path
    for ruta in RUTAS_CONOCIDAS:
        if Path(ruta).exists():
            return ruta
    return None


def hay_lector() -> bool:
    return programa() is not None


@functools.lru_cache(maxsize=1)
def idiomas_disponibles() -> tuple[str, ...]:
    """Los idiomas que tiene instalados el programa de reconocimiento.

    Se miran los del proyecto (`data/ocr/tessdata`) **y** los del sistema, porque el lector puede
    tener el español en cualquiera de los dos sitios. Si el programa no está, esto devuelve una
    lista vacía y no revienta: quien pregunte tiene que poder decir «no se puede leer la foto» sin
    que salte un error por detrás.
    """
    ruta = programa()
    if ruta is None:
        return ()
    try:
        salida = subprocess.run(
            [ruta, "--list-langs"],
            capture_output=True,
            text=True,
            timeout=ESPERA_SEGUNDOS,
            check=False,
            env=_entorno(),
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    idiomas = []
    for linea in (salida.stdout or "").splitlines():
        limpio = linea.strip()
        # La primera línea es «List of available languages in "…" (2):» y no es un idioma.
        if not limpio or limpio.lower().startswith("list of available"):
            continue
        idiomas.append(limpio)
    # Y los del proyecto, por si el programa no los ve (según cómo esté instalado, `--list-langs`
    # mira en la carpeta del sistema y no en la que se le pasa por entorno).
    propia = carpeta_de_idiomas()
    if propia:
        for fichero in Path(propia).glob("*.traineddata"):
            nombre = fichero.name.replace(".traineddata", "")
            if nombre not in idiomas:
                idiomas.append(nombre)
    return tuple(sorted(set(idiomas)))


def idioma_a_usar() -> str:
    """El mejor idioma de los que hay instalados, o cadena vacía si no hay ninguno."""
    disponibles = idiomas_disponibles()
    if not disponibles:
        return ""
    for preferido in IDIOMAS_PREFERIDOS:
        partes = preferido.split("+")
        if all(parte in disponibles for parte in partes):
            return preferido
    # Un idioma que no sea el de las orientaciones de la página vale más que nada.
    for idioma in disponibles:
        if idioma != "osd":
            return idioma
    return ""


def estado() -> dict:
    """Lo que la pantalla necesita para explicarse. Se puede preguntar siempre."""
    ruta = programa()
    idioma = idioma_a_usar() if ruta else ""
    return {
        "hay_lector": ruta is not None,
        "programa": ruta or "",
        "idiomas": list(idiomas_disponibles()),
        "idioma": idioma,
        # Se dice en castellano y sin tecnicismos: es lo que se enseña si falta el programa.
        "lee_el_espanol": "spa" in idiomas_disponibles(),
        "nota": _nota(idioma),
    }


def _nota(idioma: str) -> str:
    if not hay_lector():
        return (
            "En este ordenador no está instalado el programa que lee las fotos. Puedes subir la "
            "factura igual: se guardará como justificante y los datos los escribes tú."
        )
    if "spa" not in idioma:
        return (
            "El lector de fotos está funcionando, pero solo con el idioma inglés: los números "
            "(cantidades, precios, NIF y fechas) los lee bien, y las palabras con tilde o con eñe "
            "pueden salir cambiadas. Por eso te enseño lo que he leído para que lo corrijas."
        )
    return (
        "El lector de fotos está funcionando con el idioma español: todo lo que lea te lo enseño "
        "para que lo confirmes."
    )


def leer_texto(imagen: bytes, *, modo: int | None = None) -> str:
    """Las letras que hay dentro de una imagen.

    Falla con `SinLector` si no hay programa instalado: quien lo llame tiene que poder decir «no se
    puede leer la foto» y ofrecer teclearlo a mano, que es la salida honesta.
    """
    ruta = programa()
    if ruta is None:
        raise SinLector("no hay ningún programa de reconocimiento de letras instalado")
    idioma = idioma_a_usar()
    if not idioma:
        raise SinLector("el programa de reconocimiento no tiene ningún idioma instalado")

    preparada = _prepara_la_imagen(imagen)
    with tempfile.TemporaryDirectory(prefix="cuedigital_ocr_") as carpeta:
        entrada = Path(carpeta) / "factura.png"
        entrada.write_bytes(preparada)
        try:
            salida = subprocess.run(
                [
                    ruta,
                    str(entrada),
                    "stdout",
                    "-l",
                    idioma,
                    "--psm",
                    str(modo or MODO_DE_PAGINA),
                ],
                capture_output=True,
                timeout=ESPERA_SEGUNDOS,
                check=False,
                env=_entorno(),
            )
        except (OSError, subprocess.SubprocessError) as fallo:
            raise SinLector(f"el programa de reconocimiento no ha podido leer la imagen: {fallo}")
    # Tesseract avisa por la salida de error y escribe el texto por la salida normal. Se devuelven
    # las dos cosas pegadas: si algo sale mal, lo que haya escrito ayuda a entenderlo y no molesta.
    devuelto = salida.stdout.decode("utf-8", "replace")
    return devuelto.replace("\r\n", "\n").strip()


def _prepara_la_imagen(imagen: bytes) -> bytes:
    """Deja la imagen en el tamaño y el formato que el lector entiende mejor.

    Hace falta de verdad, y se vio probando: una foto de móvil es enorme (cuatro mil píxeles de
    ancho) y ahí el lector tarda muchísimo; y una imagen muy pequeña (una captura, un recorte) se
    lee mal. Se deja un ancho razonable y se convierte a escala de grises, que es lo que necesita
    para reconocer letras.
    """
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow viene con pdfplumber
        return imagen
    try:
        with Image.open(io.BytesIO(imagen)) as original:
            # Los formatos con transparencia (PNG con fondo vacío) se leen mal: se pasan a fondo
            # blanco. Y los que tienen varias páginas (un TIFF) se quedan con la primera.
            if original.mode in ("RGBA", "LA", "P"):
                fondo = Image.new("RGB", original.size, "white")
                convertida = original.convert("RGBA")
                fondo.paste(convertida, mask=convertida.split()[-1])
                imagen_pillow = fondo
            else:
                imagen_pillow = original.convert("RGB")
            if imagen_pillow.width > ANCHO_SUFICIENTE * 3:
                factor = (ANCHO_SUFICIENTE * 3) / imagen_pillow.width
                imagen_pillow = imagen_pillow.resize(
                    (int(imagen_pillow.width * factor), int(imagen_pillow.height * factor))
                )
            salida = io.BytesIO()
            imagen_pillow.convert("L").save(salida, format="PNG")
            return salida.getvalue()
    except Exception:
        # Si la imagen no se puede abrir (un formato raro), se manda tal cual y que lo intente el
        # lector: es mejor intentarlo que rendirse antes de probar.
        return imagen


def leer_texto_de_un_pdf(pdf: bytes, *, paginas: int = MAXIMO_PAGINAS) -> str:
    """El texto de un PDF **escaneado** (el que por dentro es una imagen y no tiene letras).

    Se dibuja cada página como una imagen y se le pasa al lector. Es lo que hace falta cuando el
    proveedor manda la factura escaneada, que es muy común.
    """
    if not hay_lector():
        raise SinLector("no hay ningún programa de reconocimiento de letras instalado")
    try:
        import pypdfium2 as pdfium
    except ImportError as fallo:  # pragma: no cover - viene con pdfplumber
        raise SinLector("no se puede dibujar el PDF para leerlo") from fallo

    documento = pdfium.PdfDocument(pdf)
    trozos: list[str] = []
    try:
        for numero in range(min(paginas, len(documento))):
            imagen = documento[numero].render(scale=3).to_pil()
            salida = io.BytesIO()
            imagen.save(salida, format="PNG")
            trozos.append(leer_texto(salida.getvalue()))
    finally:
        documento.close()
    return "\n".join(trozo for trozo in trozos if trozo).strip()


def huella(contenido: bytes) -> str:
    """Una huella del fichero, para saber si ya se subió el mismo documento.

    Se guarda con la factura: si el agricultor sube dos veces la misma foto (le pasa a todo el
    mundo), la aplicación puede avisarle en vez de apuntarla dos veces.
    """
    return hashlib.sha256(contenido).hexdigest()
