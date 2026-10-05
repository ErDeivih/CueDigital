"""Los ficheros de texto del proyecto no llevan marca de orden de bytes (BOM).

**Esto existe por un fallo real, que ha pasado dos veces.** En Windows, `Set-Content -Encoding
utf8` y `Out-File -Encoding utf8` (PowerShell 5.1) escriben UTF-8 **con BOM**. Y el BOM no es
invisible:

* En un fichero de Python, un carácter raro al principio puede acabar en un error de sintaxis.
* En un `.js` servido por el programa, un BOM delante puede hacer que el navegador no lo lea.
* Y en cualquier caso ensucia los diffs: el primer carácter de cada línea del historial.

La primera vez se coció un fichero de tests con acentos (y hubo que arreglarlo a mano), y la
segunda un `README.md`. Las dos veces el programa funcionaba, así que ningún test lo notó. Este
es el test que lo nota.

Se comprueban los ficheros que **edita una persona**: el código, la pantalla, los tests y la
documentación. No se miran los datos descargados de organismos oficiales, porque esos se guardan
tal y como los sirve el organismo.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]

# Los ficheros de texto que se editan a mano, por carpeta.
CARPETAS = ("backend/app", "backend/tests", "backend/tests_js", "backend/scripts", "backend/web", "docs")
SUFIJOS = {".py", ".js", ".css", ".md", ".html", ".json", ".webmanifest", ".csv"}
SUELTOS = ("README.md", "AGENTS.md", "DESIGN.md")

BOM = b"\xef\xbb\xbf"

# **Los ficheros de trabajo que crea un guion mientras corre, y que no son del proyecto.**
#
# `scripts/comprobar_en_un_navegador.py` escribe una página dentro de `backend/web/` **mientras
# comprueba** (tiene que servirla el propio programa: un módulo desde otro origen está prohibido por el
# navegador) y la borra al terminar. Si mientras corre se lanza la suite, esa página **entra en esta
# lista**, suma casos y los falla — y el que lo lee se pasa un rato buscando un fichero roto que no
# existe. Le pasó al subagente de T06: midió **3538 pruebas con 2 fallos** en vez de 3536 con 0, y lo
# cazó él mismo. Esta comprobación mira **lo que se edita a mano**, y una página que existe veinte
# segundos no es eso.
#
# Se filtra **por el nombre**, que es lo único que se puede hacer: el fichero no está siempre.
FUERA_DE_LA_LISTA = {
    "_comprobacion_navegador.html",
    "_comprobacion_en_un_hueco.html",
    "_comprobacion_movil_390.html",
}


def _ficheros() -> list[Path]:
    encontrados: list[Path] = []
    for carpeta in CARPETAS:
        ruta = RAIZ / carpeta
        if not ruta.exists():
            continue
        for fichero in ruta.rglob("*"):
            if fichero.is_file() and fichero.suffix in SUFIJOS:
                if fichero.name in FUERA_DE_LA_LISTA:
                    continue
                encontrados.append(fichero)
    for nombre in SUELTOS:
        ruta = RAIZ / nombre
        if ruta.is_file():
            encontrados.append(ruta)
    return sorted(encontrados)


# El mismo `parametrize` en los dos tests que miran todos los ficheros, con nombre para que se
# vea en el informe cuál falla. Va aquí, después de `_ficheros()`, porque se construye con ella.
_pytest_parametrize_ficheros = pytest.mark.parametrize(
    "fichero", _ficheros(), ids=lambda f: f.name
)


def test_hay_ficheros_que_mirar():
    """Si la lista saliera vacía, el test pasaría sin comprobar nada.

    Un test que no comprueba nada es peor que no tenerlo: deja creer que algo está vigilado
    cuando no lo está.
    """
    assert len(_ficheros()) > 40


@pytest.mark.parametrize("fichero", _ficheros(), ids=lambda f: f.name)
def test_sin_marca_de_orden_de_bytes(fichero: Path):
    assert not fichero.read_bytes().startswith(BOM), (
        f"{fichero.relative_to(RAIZ)} empieza con marca de orden de bytes. "
        "Se escribe sin BOM: usa la herramienta de edición, o "
        "[System.IO.File]::WriteAllText(ruta, texto, New-Object System.Text.UTF8Encoding($false))."
    )


def test_los_ficheros_con_acentos_se_leen_como_utf8():
    """Y lo que es más importante que el BOM: que los acentos no estén estropeados.

    Un fichero pasado por `Get-Content | Set-Content` de PowerShell puede quedar con los acentos
    convertidos en dos caracteres («ó» -> «Ã³»). Eso sí rompe cosas: un `SyntaxError` en Python y
    un texto ilegible en pantalla.

    **Cómo se distingue un fichero estropeado de uno que habla del destrozo.** La primera versión
    de este test buscaba el texto «Ã³» y saltó con `AGENTS.md`, que lo pone **como ejemplo** al
    explicar la trampa. Un test que da falsos positivos acaba desactivándose, así que se busca
    otra señal, y hay una que no falla: **el destrozo se puede deshacer**.

    Un fichero con acentos de verdad, pasado por cp1252 y vuelto a leer como UTF-8, revienta (la
    «ó» de verdad es un solo byte 0xF3, que no es UTF-8 válido). Un fichero estropeado, en cambio,
    sobrevive al viaje entero: es exactamente la operación que lo estropeó, así que devuelve otra
    cosa sin protestar. Solo se mira en los ficheros que tienen algún carácter no ASCII: uno que
    sea todo ASCII sobrevive al viaje sin estar estropeado, y ese no es el caso que se busca.
    """
    for fichero in _ficheros():
        texto = fichero.read_text(encoding="utf-8")
        if texto.isascii():
            continue
        try:
            deshecho = texto.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            # No sobrevive al viaje: los acentos son de verdad.
            continue
        if deshecho == texto:  # pragma: no cover — un fichero de solo ASCII ya se ha saltado
            continue
        raise AssertionError(
            f"{fichero.relative_to(RAIZ)} tiene los acentos estropeados: se ha pasado por un "
            f"Get-Content/Set-Content de PowerShell. Se arregla con "
            f"`texto.encode(\"cp1252\").decode(\"utf-8\")`. Empieza así: {deshecho[:60]!r}"
        )


def test_la_comprobacion_detecta_un_fichero_estropeado_de_verdad():
    """Un test que no falla nunca no vale nada: hay que probar que este falla cuando debe.

    Se le da un texto estropeado de verdad —el que sale de un `Get-Content | Set-Content`— y se
    comprueba que el mismo criterio del test de arriba lo caza. Y se le da el texto bueno, y se
    comprueba que no lo caza.
    """
    bueno = "El cuaderno de la explotación tiene una sección de análisis."
    # Así queda de verdad después de pasar por PowerShell: cada acento, en dos caracteres.
    estropeado = bueno.encode("utf-8").decode("cp1252")

    def sobrevive(texto: str) -> bool:
        """El mismo criterio que usa el test de los ficheros."""
        if texto.isascii():
            return False
        try:
            return texto.encode("cp1252").decode("utf-8") != texto
        except (UnicodeEncodeError, UnicodeDecodeError):
            return False

    assert sobrevive(estropeado), "el criterio no caza un fichero estropeado de verdad"
    assert not sobrevive(bueno), "el criterio se queja de un fichero que está bien"


def test_un_fichero_que_habla_del_destrozo_no_salta():
    """`AGENTS.md` explica esta trampa y pone un ejemplo del destrozo.

    Ese ejemplo es texto legítimo, y la primera versión de este test se quejaba de él. Se deja
    escrito porque es el motivo de que la comprobación sea la que es y no una búsqueda de texto.
    """
    ejemplo = 'la «ó» queda como «Ã³» y el fichero deja de compilar'
    try:
        deshecho = ejemplo.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        deshecho = None
    # La frase, tal y como está escrita en AGENTS.md, lleva una «ó» de verdad al lado del
    # ejemplo, así que no sobrevive al viaje. Por eso no salta.
    assert deshecho is None or deshecho == ejemplo


def _bytes_del_destrozo(linea: str) -> bytes | None:
    """Los bytes que habría tenido la línea antes de estropearse. `None` si no pudo venir de ahí.

    Hace falta ir carácter a carácter porque hay bytes que **no existen en cp1252** (0x81, 0x8D,
    0x8F, 0x90 y 0x9D) y se quedaron como el carácter de control que les toca. Sin esto, una línea
    con un emoji estropeado (`âš\\xa0ï¸\\x8f` en vez de ⚠️) no se puede ni comprobar: el viaje
    redondo con cp1252 revienta con esos bytes y la línea se da por buena. Se encontró así.
    """
    salida = bytearray()
    for caracter in linea:
        codigo = ord(caracter)
        if codigo < 128:
            salida.append(codigo)
            continue
        try:
            salida += caracter.encode("cp1252")
            continue
        except UnicodeEncodeError:
            pass
        if 0x80 <= codigo <= 0x9F:
            salida.append(codigo)
            continue
        return None  # un carácter que no puede venir de un destrozo: la línea está bien
    return bytes(salida)


def _deshecha(linea: str) -> str | None:
    """La línea tal y como era antes del destrozo, o `None` si no estaba estropeada."""
    crudo = _bytes_del_destrozo(linea)
    if crudo is None:
        return None
    try:
        deshecha = crudo.decode("utf-8")
    except UnicodeDecodeError:
        return None  # no era un destrozo: son acentos de verdad
    return deshecha if deshecha != linea else None


@_pytest_parametrize_ficheros
def test_ninguna_linea_tiene_los_acentos_estropeados(fichero: Path):
    """**El test de arriba miraba el fichero entero, y por eso se le escapó un caso de verdad.**

    El 24/09/2026 se encontró que `README.md`, `AGENTS.md` y dos documentos de `docs/` tenían
    **cientos de líneas** con «ó» en vez de «ó», y el test de arriba no decía nada. El motivo:
    esos ficheros estaban **a medias**. En cuanto una línea tiene acentos de verdad, el viaje de
    ida y vuelta del fichero entero revienta por esa línea, y el test daba por bueno todo lo
    demás. Cientos de líneas ilegibles dentro de un fichero que el test aprobaba.

    Se comprueba **línea a línea**, que es donde está el destrozo. Lo bueno de mirarlo así es que
    no hace falta ninguna lista de excepciones: la línea de `AGENTS.md` que pone «Ã³» **como
    ejemplo** lleva también una «ó» de verdad, así que esa línea no sobrevive al viaje y no salta
    (como se comprueba en el test de arriba).
    """
    for numero, linea in enumerate(fichero.read_text(encoding="utf-8").split("\n"), start=1):
        deshecha = _deshecha(linea)
        if deshecha is None:
            continue
        raise AssertionError(
            f"{fichero.relative_to(RAIZ)} línea {numero} tiene los acentos estropeados: "
            f"{deshecha[:70]!r} en vez de {linea[:70]!r}. Se arregla deshaciendo el destrozo en esa "
            "línea (ver `_deshecha`), o mejor con la herramienta de edición y no con PowerShell."
        )


def test_la_comprobacion_caza_un_fichero_a_medias():
    """Y que caza justo el caso que se le escapó: un fichero con unas líneas bien y otras no.

    Es el caso de verdad: alguien arregla la mitad de un documento y deja la otra mitad. El
    criterio del fichero entero lo daba por bueno; el de línea a línea tiene que cazarlo.

    Y se comprueba también el caso de los emojis, que se le escapaba incluso al criterio de línea:
    el ⚠️ estropeado lleva un byte (0x8F) que **no existe en cp1252**, así que la comprobación tiene
    que ir byte a byte o se lo traga.
    """

    def el_fichero_entero_esta_bien(texto: str) -> bool:
        try:
            return texto.encode("cp1252").decode("utf-8") == texto
        except (UnicodeEncodeError, UnicodeDecodeError):
            return True  # «no sobrevive: los acentos son de verdad»

    buena = "El cuaderno de la explotación tiene una sección de análisis."
    estropeada = buena.encode("utf-8").decode("cp1252")
    a_medias = "\n".join([buena, estropeada, buena])

    assert el_fichero_entero_esta_bien(a_medias), "el criterio viejo daba por bueno el fichero"
    assert any(_deshecha(linea) for linea in a_medias.split("\n")), "el criterio nuevo lo caza"
    assert not any(_deshecha(linea) for linea in buena.split("\n")), "y no salta con lo que está bien"

    aviso_bueno = "⚠️ Cuidado con esto."
    aviso_estropeado = aviso_bueno.encode("utf-8").decode("latin-1")
    with pytest.raises(UnicodeEncodeError):
        aviso_estropeado.encode("cp1252")  # por esto el viaje redondo con cp1252 no lo ve
    assert _deshecha(aviso_estropeado) == aviso_bueno, "el emoji estropeado tiene que cazarse"
