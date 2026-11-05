"""La foto de una tierra: la ortofoto de su zona con su contorno dibujado encima.

**Para qué existe.** David pidió, junto con los datos de las tierras, **el contorno en el mapa de
cada parcela para tener la imagen**: una imagen que se pueda enseñar en la ficha de la tierra y
guardar como prueba de qué trozo se estaba mirando. El servidor ya sabía traer la ortofoto del IGN
(`sigpac.pedir_imagen_del_mapa`) y ya sabía leer la forma de una tierra (`geo`), pero las dos cosas
no se juntaban en ningún sitio: esto es lo que las junta.

**Cómo se hace, y por qué así.**

1. **La caja sale de la forma de la tierra, no del centro.** Se coge el rectángulo que envuelve su
   geometría, se le da un **15 % más de terreno alrededor** (un 7,5 % por cada lado, para que el
   borde del trozo no quede pegado al canto de la imagen) y se **estira hasta el aspecto de la
   imagen pedida**. Si no se estirara, el WMS devolvería una foto deformada o con franjas, y el
   contorno dibujado no caería donde toca.
2. **El contorno se dibuja en píxeles, no se le pide al SIGPAC.** Se pinta el polígono con un
   relleno amarillo translúcido y una **línea blanca con un borde oscuro debajo**: la ortofoto
   puede ser un rastrojo claro o un pinar oscuro, y una línea de un solo color desaparece en uno
   de los dos. El borde oscuro es el que garantiza que la línea se vea siempre.
3. **Si no hay forma, no se inventa un cuadro.** Se levanta `SinForma` y la puerta contesta 409:
   una tierra apuntada a mano no tiene polígono, y dibujar un rectángulo sería mentir sobre dónde
   está su tierra. Si no se puede traer la ortofoto, `SinOrtofoto` y 503, con el mismo criterio.

**Lo que NO se hace: caché de la imagen compuesta.** La ortofoto ya se cachea en `sigpac` (las
últimas veinte), y el navegador puede guardar el PNG un rato (`Cache-Control`). Pero **no se
guarda en el servidor la imagen ya dibujada**, y es a propósito: la forma de una tierra se puede
corregir (`POST /api/parcelas/{id}/forma`), y `Parcela` no tiene una marca de cuándo cambió su
geometría; una caché por identificador y tamaño podría servir un contorno viejo sobre una tierra
ya corregida, que es peor que no tener imagen. El contorno es lo único que importa aquí, así que
se dibuja cada vez: son milisegundos.

**El tamaño tiene tope** (200–1600 de ancho y 150–1200 de alto): una imagen enorme tarda, gasta
datos del agricultor y no se ve mejor en la pantalla de un móvil.
"""

from __future__ import annotations

import io
from collections.abc import Callable

from PIL import Image, ImageDraw

from . import geo, sigpac

# El tamaño que se pide cuando no se dice otro. 800×600 se ve bien en la ficha de una tierra en un
# móvil y en un ordenador, y no gasta datos de más.
ANCHO_POR_DEFECTO = 800
ALTO_POR_DEFECTO = 600

# Los topes. Por debajo no se reconoce el trozo; por encima no cabe en una pantalla y el WMS tarda.
ANCHO_MINIMO = 200
ANCHO_MAXIMO = 1600
ALTO_MINIMO = 150
ALTO_MAXIMO = 1200

# Cuánto terreno de más alrededor de la tierra. 0,15 es un 15 % del tamaño de su caja, o sea un
# 7,5 % por cada lado.
MARGEN = 0.15

# Cuando una geometría es degenerada (todos sus puntos en la misma longitud o latitud) la caja
# tendría un lado de cero y el servicio de mapas no sabría qué devolver. Se abre ese lado hasta
# este mínimo, que son unos 50 metros: suficiente para que la imagen tenga sentido y para no
# alejarse de la tierra.
LADO_MINIMO_GRADOS = 0.0005

# El relleno: amarillo suave y translúcido (alfa 70 de 255). Y la línea en dos capas: primero el
# borde oscuro, más grueso, y encima la línea blanca. Así el contorno se ve sobre rastrojo y sobre
# monte, que es lo que hay debajo en una ortofoto.
COLOR_RELLENO = (255, 214, 0, 70)
COLOR_LINEA = (255, 255, 255, 255)
COLOR_BORDE = (0, 0, 0, 160)

# El grosor de la línea, en píxeles, según el tamaño de la imagen: 3 px en la imagen por defecto
# (600 de alto) y 5 px a partir de 1000. Se pensó para que se vea en la pantalla de un móvil de
# 5 pulgadas, que es donde se va a mirar esto de verdad, sin que se coma el trozo pequeño.
GROSOR_MINIMO = 2
GROSOR_MAXIMO = 5

# La firma que tiene que tener lo que devuelve el `fetch`: (capa, oeste, sur, este, norte, ancho,
# alto) y devuelve (bytes de la imagen, tipo). Es la misma forma que
# `sigpac.pedir_imagen_del_mapa`, y se puede sustituir en los tests para no salir a internet.
Fetch = Callable[[str, float, float, float, float, int, int], tuple[bytes, str]]


class SinForma(ValueError):
    """La tierra no tiene geometría: no hay contorno que dibujar (y no se inventa)."""


class SinOrtofoto(RuntimeError):
    """No se ha podido traer la ortofoto, o lo que ha llegado no es una imagen."""


class TamanoInvalido(ValueError):
    """El ancho o el alto pedidos están fuera de los topes."""


def comprobar_tamano(ancho: int, alto: int) -> None:
    """Los topes de tamaño, dichos con un error que la puerta pueda explicar."""
    if not ANCHO_MINIMO <= int(ancho) <= ANCHO_MAXIMO:
        raise TamanoInvalido(
            f"El ancho de la imagen tiene que estar entre {ANCHO_MINIMO} y {ANCHO_MAXIMO} píxeles."
        )
    if not ALTO_MINIMO <= int(alto) <= ALTO_MAXIMO:
        raise TamanoInvalido(
            f"El alto de la imagen tiene que estar entre {ALTO_MINIMO} y {ALTO_MAXIMO} píxeles."
        )


def _puntos_de_la_tierra(geometria: str | None) -> list[list[tuple[float, float]]]:
    """Los anillos de la forma, o `SinForma` si no hay con qué dibujar.

    Se apoya en `geo.anillos_de_un_wkt` (que a su vez usa el mismo lector que
    `geo.puntos_del_wkt`) para no tener dos maneras de entender un WKT. Para el caso normal —un
    `POLYGON` de un recinto del SIGPAC— hay un anillo; si la geometría es multiparte, se dibujan
    todos sus anillos. Un punto o una línea no tienen anillo y no se dibujan.
    """
    anillos = [anillo for anillo in geo.anillos_de_un_wkt(geometria) if len(anillo) >= 3]
    if anillos:
        return anillos
    # El mismo lector, por si la geometría es una forma que `anillos_de_un_wkt` no separa (por
    # ejemplo, un WKT sin los paréntesis que espera). Se usa solo como red de seguridad.
    puntos = geo.puntos_del_wkt(geometria)
    if len(puntos) < 3:
        raise SinForma("La tierra no tiene su forma guardada: no hay contorno que dibujar.")
    return [puntos]


def caja_de_la_tierra(
    geometria: str | None, ancho: int, alto: int
) -> tuple[float, float, float, float]:
    """El rectángulo que se le pide al mapa: la tierra, con margen y con el aspecto de la imagen.

    Devuelve `(oeste, sur, este, norte)` en grados. El margen es del 15 % del tamaño de la caja de
    la tierra (7,5 % por cada lado), y después se estira el lado que haga falta hasta que la caja
    tenga la misma proporción que la imagen pedida. Sin ese estirón, el WMS devuelve la foto
    deformada o con franjas y el contorno cae donde no toca.
    """
    puntos = [punto for anillo in _puntos_de_la_tierra(geometria) for punto in anillo]
    oeste = min(punto[0] for punto in puntos)
    este = max(punto[0] for punto in puntos)
    sur = min(punto[1] for punto in puntos)
    norte = max(punto[1] for punto in puntos)

    centro_lon = (oeste + este) / 2.0
    centro_lat = (sur + norte) / 2.0
    # Un 15 % más de terreno: el factor es 1 + margen, y se reparte a los dos lados.
    lado_lon = max((este - oeste) * (1.0 + MARGEN), LADO_MINIMO_GRADOS)
    lado_lat = max((norte - sur) * (1.0 + MARGEN), LADO_MINIMO_GRADOS)

    # El aspecto manda: la imagen no se puede deformar. Se agranda el lado que se queda corto.
    aspecto = max(int(ancho), 1) / max(int(alto), 1)
    if lado_lon / lado_lat < aspecto:
        lado_lon = lado_lat * aspecto
    else:
        lado_lat = lado_lon / aspecto

    return (
        centro_lon - lado_lon / 2.0,
        centro_lat - lado_lat / 2.0,
        centro_lon + lado_lon / 2.0,
        centro_lat + lado_lat / 2.0,
    )


def _puntos_en_la_imagen(
    anillos: list[list[tuple[float, float]]],
    caja: tuple[float, float, float, float],
    ancho: int,
    alto: int,
) -> list[list[tuple[int, int]]]:
    """Cada anillo, con sus coordenadas convertidas a píxeles de la imagen.

    La Y se da la vuelta: en el mapa el norte va arriba y en una imagen la Y crece hacia abajo.
    """
    oeste, sur, este, norte = caja
    ancho_grados = max(este - oeste, 1e-12)
    alto_grados = max(norte - sur, 1e-12)
    salida: list[list[tuple[int, int]]] = []
    for anillo in anillos:
        salida.append(
            [
                (
                    round((lon - oeste) / ancho_grados * ancho),
                    round((norte - lat) / alto_grados * alto),
                )
                for lon, lat in anillo
            ]
        )
    return salida


def _grosor(ancho: int, alto: int) -> int:
    """El grosor de la línea: crece con la imagen, entre 2 y 5 píxeles."""
    return max(GROSOR_MINIMO, min(GROSOR_MAXIMO, round(min(ancho, alto) / 200)))


def dibujar_el_contorno(
    ortofoto: bytes, anillos: list[list[tuple[float, float]]], caja, ancho: int, alto: int
) -> bytes:
    """La ortofoto con el contorno encima, en PNG.

    El relleno va primero, translúcido; después el borde oscuro y, encima, la línea blanca. Se
    dibuja sobre una capa transparente y se compone al final, para que el relleno no tape la foto
    y para que la línea quede nítida encima de todo.
    """
    try:
        fondo = Image.open(io.BytesIO(ortofoto)).convert("RGB")
    except (OSError, ValueError) as error:
        raise SinOrtofoto(f"Lo que ha llegado no es una imagen ({type(error).__name__}).") from None
    if fondo.size != (ancho, alto):
        fondo = fondo.resize((ancho, alto), Image.LANCZOS)

    capa = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(capa)
    en_pixeles = _puntos_en_la_imagen(anillos, caja, ancho, alto)

    # El relleno solo del anillo de fuera. Un agujero se queda sin rellenar (no se resta): las
    # tierras del SIGPAC son un solo polígono y no merece la pena complicar esto por un caso que
    # no se ha visto; el contorno de todos los anillos sí se dibuja.
    if en_pixeles and len(en_pixeles[0]) >= 3:
        dibujo.polygon(en_pixeles[0], fill=COLOR_RELLENO)

    grosor = _grosor(ancho, alto)
    for anillo in en_pixeles:
        if len(anillo) < 3:
            continue
        cerrado = [*anillo, anillo[0]]
        dibujo.line(cerrado, fill=COLOR_BORDE, width=grosor + 2, joint="curve")
        dibujo.line(cerrado, fill=COLOR_LINEA, width=grosor, joint="curve")

    compuesta = Image.alpha_composite(fondo.convert("RGBA"), capa).convert("RGB")
    salida = io.BytesIO()
    compuesta.save(salida, format="PNG", optimize=True)
    return salida.getvalue()


def _traer_del_sigpac(
    capa: str, oeste: float, sur: float, este: float, norte: float, ancho: int, alto: int
) -> tuple[bytes, str]:
    """La ortofoto, del servicio que ya usa el programa (el WMS del IGN, capa `foto`).

    Se llama aquí y no en el router para que la puerta no sepa de servicios de fuera y para que
    los tests puedan sustituir `sigpac.pedir_imagen_del_mapa` por una respuesta sin red.
    """
    return sigpac.pedir_imagen_del_mapa(capa, oeste, sur, este, norte, ancho, alto)


def imagen_de_la_tierra(
    geometria: str | None,
    ancho: int = ANCHO_POR_DEFECTO,
    alto: int = ALTO_POR_DEFECTO,
    fetch: Fetch | None = None,
) -> bytes:
    """El PNG de la tierra: su ortofoto con el contorno dibujado, o el motivo por el que no.

    Levanta `TamanoInvalido` si el tamaño no es razonable, `SinForma` si la tierra no tiene
    geometría y `SinOrtofoto` si el servicio no contesta o contesta algo que no es una imagen.
    Quien llama traduce cada uno a su respuesta: **no se devuelve un cuadro de relleno**.
    """
    comprobar_tamano(ancho, alto)
    ancho = int(ancho)
    alto = int(alto)
    anillos = _puntos_de_la_tierra(geometria)
    caja = caja_de_la_tierra(geometria, ancho, alto)

    traer = fetch or _traer_del_sigpac
    try:
        contenido, tipo = traer("foto", caja[0], caja[1], caja[2], caja[3], ancho, alto)
    except sigpac.SigpacNoContesta as error:
        raise SinOrtofoto(f"El mapa no ha contestado ({error}).") from None
    except Exception as error:  # noqa: BLE001 — cualquier fallo del `fetch` es el mismo caso
        raise SinOrtofoto(f"No se ha podido traer la ortofoto ({type(error).__name__}).") from None

    tipo_limpio = (tipo or "").split(";")[0].strip().lower()
    if tipo_limpio not in ("image/png", "image/jpeg", "image/jpg") or not contenido:
        raise SinOrtofoto(
            f"El servicio ha contestado {tipo_limpio or 'sin tipo'}, y eso no es una foto."
        )

    return dibujar_el_contorno(contenido, anillos, caja, ancho, alto)
