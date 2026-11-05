"""Utilidades geográficas.

Decisión: se calculan aquí, con la biblioteca estándar, sin shapely ni geopandas.
Motivo: la única cuenta que hace falta hoy es "¿están estas dos parcelas a menos de
8 km?", que es lo que pide la unidad homogénea de cultivo, y el centro de un
polígono para ponerlo en el mapa. Traer shapely para eso sería desproporcionado.

Cuando entren las consultas espaciales de verdad (intersección con zonas
vulnerables o con cauces), eso se resuelve en PostGIS y no aquí.
"""

from __future__ import annotations

import math
import re

RADIO_TIERRA_KM = 6371.0088
# El mismo radio en metros: es la unidad en la que se mide el área de un trozo (T05). Se deriva del
# de arriba para que no haya dos números que puedan separarse.
RADIO_TIERRA_M = RADIO_TIERRA_KM * 1000.0
# Radio que fija la aplicación oficial para agrupar parcelas en una unidad homogénea.
RADIO_UHC_KM = 8.0

_NUMERO = re.compile(r"(-?\d+(?:\.\d+)?)")


def centroide_wkt(wkt: str | None) -> tuple[float, float] | None:
    """Centro aproximado de una geometría en texto WKT.

    Se usa la media de los vértices. Para parcelas agrícolas, que son polígonos
    convexos y pequeños, el error frente al centroide real es de metros y no afecta
    a ninguna decisión. Devuelve (longitud, latitud) o None si no se puede leer.

    Acepta también **un solo punto**, y eso se arregló en la ronda 17: antes hacían falta tres
    vértices, así que una parcela con solo un punto en el mapa se quedaba fuera de la agrupación
    automática **sin decir nada**. Un punto es su propio centro, así que no hay nada que
    aproximar. Lo que sigue devolviendo `None` es una parcela sin geometría ninguna: ahí no hay
    forma de saber si está cerca de otra, y quien llama tiene que decirlo en vez de suponer.
    """
    if not wkt:
        return None
    numeros = [float(n) for n in _NUMERO.findall(wkt)]
    if len(numeros) < 2:
        return None
    if len(numeros) % 2 != 0:
        numeros = numeros[:-1]

    puntos = list(zip(numeros[0::2], numeros[1::2]))

    # Un anillo cerrado repite el primer vértice al final. Si no se quita, ese
    # vértice pesa doble y el centro se va unos metros hacia él. Con un cuadrado de
    # 100 m eso son 11 m de error, que no rompen nada, pero es gratis hacerlo bien.
    if len(puntos) > 2 and puntos[0] == puntos[-1]:
        puntos = puntos[:-1]
    if not puntos:
        return None

    longitud = sum(punto[0] for punto in puntos) / len(puntos)
    latitud = sum(punto[1] for punto in puntos) / len(puntos)
    return (longitud, latitud)


def distancia_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia entre dos puntos (longitud, latitud) por la fórmula del haversine."""
    lon1, lat1 = a
    lon2, lat2 = b
    rad = math.radians
    dlat = rad(lat2 - lat1)
    dlon = rad(lon2 - lon1)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * math.asin(min(1.0, math.sqrt(h)))


def estan_cerca(
    a: tuple[float, float] | None,
    b: tuple[float, float] | None,
    radio_km: float = RADIO_UHC_KM,
) -> bool:
    """¿Se pueden agrupar estas dos parcelas?

    Si alguna no tiene coordenadas, se devuelve True: es preferible ofrecer un
    grupo que el agricultor puede revisar a negarle la función porque no dibujó la
    parcela. El agricultor siempre confirma el grupo antes de guardarlo.
    """
    if a is None or b is None:
        return True
    return distancia_km(a, b) <= radio_km


# --------------------------------------------------------------------------
# El dibujo del trozo
#
# El SIGPAC devuelve la forma de cada recinto desde la ronda 10, y hasta la 20 **no se veía en
# ninguna parte**: se guardaba en la base de datos y ahí se quedaba. Lo que hace esto es
# convertirla en un dibujo que el navegador pueda pintar sin ninguna librería de mapas.
#
# Decisión: se dibuja **directamente en SVG**, sin mapas de por medio. Un mapa de verdad (con sus
# teselas, sus calles y sus servidores) pesa megas y necesita cobertura, y aquí lo único que hace
# falta es que el agricultor reconozca su tierra de un vistazo: la forma del trozo.
#
# Y una cosa que hay que hacer bien o el dibujo miente: **un grado de longitud no mide lo mismo
# que uno de latitud**. En Salamanca, un grado de longitud son unos 84 km y uno de latitud unos
# 111. Si se dibuja tal cual, la parcela sale estirada como si fuera más ancha de lo que es. Por
# eso se corrige por el coseno de la latitud.
# --------------------------------------------------------------------------

# El lado del cuadro donde se dibuja. El navegador lo escala a lo que necesite.
LADO_DEL_DIBUJO = 100.0
# Un margen para que el borde del trozo no quede pegado al canto.
MARGEN_DEL_DIBUJO = 4.0


def dibujo_svg(wkt: str | None, lado: float = LADO_DEL_DIBUJO) -> str | None:
    """La forma de un trozo, lista para pintar en un `viewBox` de `lado` por `lado`.

    Devuelve el atributo `d` de un `<path>` de SVG (`M x y L x y … Z`) o `None` si no hay
    geometría que dibujar. `None` no es un error: una parcela apuntada a mano no tiene forma, y
    eso hay que decirlo en pantalla en vez de dibujar un cuadro inventado.
    """
    centro = centroide_wkt(wkt)
    if centro is None:
        return None

    puntos = _puntos_de_un_wkt(wkt)
    if len(puntos) < 3:
        return None

    # Se corrige la anchura por la latitud: a 41 grados, un grado de longitud son unos 84 km.
    factor = math.cos(math.radians(centro[1]))
    plano = [(lon * factor, lat) for lon, lat in puntos]

    ancho = max(x for x, _ in plano) - min(x for x, _ in plano)
    alto = max(y for _, y in plano) - min(y for _, y in plano)
    if ancho <= 0 and alto <= 0:
        return None

    util = lado - 2 * MARGEN_DEL_DIBUJO
    # Se mantiene la proporción: el lado que más mide ocupa todo el hueco y el otro se centra.
    escala = util / max(ancho, alto) if max(ancho, alto) > 0 else 1.0
    sobra_x = (util - ancho * escala) / 2
    sobra_y = (util - alto * escala) / 2
    x0, y0 = min(x for x, _ in plano), min(y for _, y in plano)

    def a_pantalla(punto: tuple[float, float]) -> tuple[float, float]:
        x = (punto[0] - x0) * escala + MARGEN_DEL_DIBUJO + sobra_x
        # La Y se da la vuelta: en el mapa el norte va arriba, y en la pantalla la Y crece hacia
        # abajo. Sin esto el dibujo sale del revés, y eso se nota en cuanto el trozo no es simétrico.
        y = lado - ((punto[1] - y0) * escala + MARGEN_DEL_DIBUJO + sobra_y)
        return round(x, 3), round(y, 3)

    primeros = a_pantalla(plano[0])
    partes = [f"M {primeros[0]} {primeros[1]}"]
    for punto in plano[1:]:
        x, y = a_pantalla(punto)
        partes.append(f"L {x} {y}")
    partes.append("Z")
    return " ".join(partes)


def puntos_de_un_wkt(wkt: str | None) -> list[tuple[float, float]]:
    """Los vértices de una geometría, en el orden en que vienen: `[(longitud, latitud), …]`.

    Es lo que necesita el mapa: para pintar la parcela encima de la foto hay que saber por dónde
    pasa, en coordenadas de verdad, y la pantalla las coloca ella. Devolver el WKT y que el
    JavaScript lo interprete sería escribir otra vez, y peor, algo que aquí ya está hecho.
    """
    return _puntos_de_un_wkt(wkt or "")


def puntos_del_wkt(wkt: str | None) -> list[tuple[float, float]]:
    """Los puntos de una geometría en `[(longitud, latitud), …]`, para pintarla donde sea.

    Es el nombre que pide la interfaz nueva (`/api/nuevo/tierras`, el `anillo` de cada tierra) y hace
    lo mismo que `puntos_de_un_wkt`, que ya estaba: los dos se apoyan en el mismo `_puntos_de_un_wkt`
    para que no haya dos maneras de leer un WKT que un día discrepen. El nombre nuevo está pedido por
    el contrato del armazón (`IMP-1`, 05/11/2026); el Lead decidirá si se queda uno solo.

    Devuelve la lista vacía si no hay geometría: **una tierra apuntada a mano no tiene forma**, y
    quien llama tiene que decirlo en vez de dibujar un cuadro inventado.
    """
    return _puntos_de_un_wkt(wkt or "")


def _puntos_de_un_wkt(wkt: str) -> list[tuple[float, float]]:
    """Los vértices de una geometría, en orden. Se quita el que cierra el anillo si lo repite."""
    numeros = [float(n) for n in _NUMERO.findall(wkt or "")]
    if len(numeros) % 2 != 0:
        numeros = numeros[:-1]
    puntos = list(zip(numeros[0::2], numeros[1::2]))
    if len(puntos) > 2 and puntos[0] == puntos[-1]:
        puntos = puntos[:-1]
    return puntos


# --------------------------------------------------------------------------
# Medir una forma: cuánto mide, por dónde pasa y si dos trozos se pisan (T05, 02/10/2026)
# --------------------------------------------------------------------------
#
# **Por qué esto vive aquí y no en el servicio de las versiones.** Medir una forma es una cuenta
# sobre un texto WKT, igual que sacar su centro o dibujarla, y aquí están las demás. Hace falta de
# verdad: el contrato (§2.1) pide guardar **el área de la geometría** aparte del área del SIGPAC y
# de la declarada, y avisar de los **solapes** entre recintos sin corregirlos por su cuenta.
#
# **Lo que NO es esta área.** No es la superficie oficial del recinto: esa la publica el SIGPAC y se
# guarda tal cual (`superficie_sigpac_ha`, y en la versión `area_sigpac_ha`). Las tres magnitudes
# —la de la forma, la del SIGPAC y la declarada— se guardan por separado y **ninguna se deduce de
# otra**; esto solo mide la primera.
#
# La medida está comprobada contra un recinto **oficial**: `data/sigpac/recinto_de_ejemplo.json`
# (una respuesta de verdad del SIGPAC) trae su WKT y su superficie oficial, 2,7923 ha. El área de
# ese WKT sale **2,788534 ha**, un 0,13 % menos. Es el orden de error que se espera de medir sobre
# un plano local en vez de sobre el elipsoide, y no cambia ninguna decisión: la superficie que se
# declara sigue siendo la del SIGPAC o la del agricultor, nunca esta.
#
# Las coordenadas del WKT son longitud y latitud (EPSG:4326 / 4258), que es como las publica el
# SIGPAC: `POLYGON((-5.238 40.923, …))`.


def anillos_de_un_wkt(wkt: str | None) -> list[list[tuple[float, float]]]:
    """Los anillos de una geometría, uno por cada grupo de coordenadas entre paréntesis.

    Un `POLYGON` trae el anillo de fuera y, si los tiene, los agujeros; un `MULTIPOLYGON` trae
    varios trozos, cada uno con los suyos. Se separan **por los paréntesis**, que es lo que de
    verdad separa un anillo de otro: contar comas juntaría en uno solo los anillos de un trozo
    multiparte, y el área saldría mal sin que nadie se enterase.

    Un punto o una línea no tienen anillos, y por eso devuelve una lista vacía: no hay forma que
    medir, y quien llame tiene que decir «no se sabe» en vez de un cero.
    """
    texto = wkt or ""
    anillos: list[list[tuple[float, float]]] = []
    profundidad = 0
    inicio: int | None = None
    for posicion, caracter in enumerate(texto):
        if caracter == "(":
            profundidad += 1
            if profundidad >= 2 and inicio is None:
                inicio = posicion + 1
        elif caracter == ")":
            if profundidad >= 2 and inicio is not None:
                puntos = _puntos_de_una_lista(texto[inicio:posicion])
                if len(puntos) >= 3:
                    anillos.append(puntos)
                inicio = None
            profundidad = max(0, profundidad - 1)
    return anillos


def _puntos_de_una_lista(trozo: str) -> list[tuple[float, float]]:
    """Los pares de números de un trozo de WKT, en orden. El impar que sobra se descarta."""
    numeros = [float(n) for n in _NUMERO.findall(trozo or "")]
    if len(numeros) % 2 != 0:
        numeros = numeros[:-1]
    puntos = list(zip(numeros[0::2], numeros[1::2]))
    if len(puntos) > 2 and puntos[0] == puntos[-1]:
        puntos = puntos[:-1]
    return puntos


def _area_de_un_anillo_en_metros(anillo: list[tuple[float, float]]) -> float:
    """El área que encierra un anillo, en metros cuadrados, sobre un plano local.

    Se corrige la longitud por el coseno de la latitud media del anillo (a 41 grados, un grado de
    longitud son unos 84 km y uno de latitud, 111): sin eso, un cuadrado de 100 m saldría un 25 %
    más ancho de lo que es.
    """
    latitud_media = sum(punto[1] for punto in anillo) / len(anillo)
    factor = math.cos(math.radians(latitud_media))
    plano = [
        (RADIO_TIERRA_M * math.radians(lon) * factor, RADIO_TIERRA_M * math.radians(lat))
        for lon, lat in anillo
    ]
    doble = 0.0
    for indice, (x1, y1) in enumerate(plano):
        x2, y2 = plano[(indice + 1) % len(plano)]
        doble += x1 * y2 - x2 * y1
    return abs(doble) / 2.0


def _dentro_de_un_anillo(anillo: list[tuple[float, float]], punto: tuple[float, float]) -> bool:
    """¿Ese punto cae dentro de ese anillo? Regla par-impar, que es la que entiende los agujeros."""
    dentro = False
    for indice, (x1, y1) in enumerate(anillo):
        x2, y2 = anillo[(indice + 1) % len(anillo)]
        if (y1 > punto[1]) != (y2 > punto[1]):
            corte = x1 + (punto[1] - y1) * (x2 - x1) / (y2 - y1)
            if punto[0] < corte:
                dentro = not dentro
    return dentro


def _profundidad_de_un_anillo(
    anillo: list[tuple[float, float]], anillos: list[list[tuple[float, float]]]
) -> int:
    """Cuántos anillos lo envuelven: 0 el de fuera, 1 un agujero, 2 una isla dentro de un agujero.

    Se mira **un vértice del anillo**, que es lo que hace falta para saber de qué anillo se trata:
    los anillos de una misma geometría no se cruzan entre sí.
    """
    vertice = anillo[0]
    return sum(
        1
        for otro in anillos
        if otro is not anillo and _dentro_de_un_anillo(otro, vertice)
    )


def area_ha(wkt: str | None) -> float | None:
    """El área que encierra una geometría, en hectáreas, o `None` si no se puede medir.

    Los anillos se suman **por profundidad** —el de fuera suma, un agujero resta, una isla dentro
    de un agujero vuelve a sumar—, así que el resultado no depende de hacia dónde estén dibujados
    los anillos, que es algo que cambia de una fuente a otra.

    `None` cuando no hay nada que medir (un punto, una línea, un texto vacío, algo que no se
    entiende) o cuando lo que sale no puede ser un área (cero o negativa, que es lo que da una
    geometría mal formada). **Nunca un cero**: un cero ahí sería decir que la tierra no tiene
    superficie, y eso es justo lo que `docs/T02_VALORES_POR_DEFECTO.md` prohíbe (A7).
    """
    anillos = anillos_de_un_wkt(wkt)
    if not anillos:
        return None
    total = 0.0
    for anillo in anillos:
        area = _area_de_un_anillo_en_metros(anillo)
        total += area if _profundidad_de_un_anillo(anillo, anillos) % 2 == 0 else -area
    if total <= 0:
        return None
    return total / 10_000.0


def rectangulo_de_un_wkt(
    wkt: str | None,
) -> tuple[float, float, float, float] | None:
    """El rectángulo que envuelve una forma: `(longitud mínima, latitud mínima, máximas)`.

    Es la comprobación barata que se hace **antes** de mirar si dos trozos se pisan: si sus
    rectángulos no se tocan, las formas tampoco. `None` si no hay forma.
    """
    puntos = [punto for anillo in anillos_de_un_wkt(wkt) for punto in anillo]
    if not puntos:
        return None
    longitudes = [punto[0] for punto in puntos]
    latitudes = [punto[1] for punto in puntos]
    return (min(longitudes), min(latitudes), max(longitudes), max(latitudes))


def punto_dentro_del_wkt(wkt: str | None, longitud: float, latitud: float) -> bool | None:
    """¿Ese punto cae dentro de esa forma? `None` si no hay forma con la que contestar.

    Los tres finales importan (`AGENTS.md`, «Comprobar algo que viene de fuera»): sí, no, y **no
    lo he podido comprobar**. Una parcela apuntada a mano no tiene forma, así que de ella no se
    puede decir ni que sí ni que no.
    """
    anillos = anillos_de_un_wkt(wkt)
    if not anillos:
        return None
    dentro = False
    for anillo in anillos:
        if _dentro_de_un_anillo(anillo, (longitud, latitud)):
            dentro = not dentro
    return dentro


# Los tres nombres que puede devolver `se_solapan`. El cuarto, `no_se`, es el que se dice cuando
# falta la forma: no saberlo **no es** lo mismo que saber que no se pisan.
SOLAPE_SEGURO = "si"
SOLAPE_POSIBLE = "puede"
SOLAPE_NO = "no"
SOLAPE_NO_SE = "no_se"


def se_solapan(a: str | None, b: str | None) -> str:
    """¿Se pisan estas dos formas? `si`, `puede`, `no` o `no_se`.

    **Por qué hay un «puede» y no un sí o un no a secas.** Decir si dos polígonos se pisan, con
    exactitud, es calcular su intersección, y eso aquí no se hace (ni hace falta: no se va a
    recortar ninguna parcela sola). Lo que sí se puede decir sin inventar nada es esto:

      · **`si`** — un vértice de una forma cae dentro de la otra: hay solape, seguro.
      · **`puede`** — los rectángulos que las envuelven se tocan, pero ningún vértice cae dentro
        del otro. Es el caso de dos trozos que se cruzan como una cruz, y también el de dos que
        solo se rozan. Se avisa para que se mire, y **no se corrige nada**.
      · **`no`** — los rectángulos no se tocan, así que las formas tampoco.
      · **`no_se`** — a alguna de las dos le falta la forma.

    El aviso que sale de aquí es informativo: el contrato (§2.1, E2) pide **detectar** solapes y
    decirlo, no arreglarlos por su cuenta.
    """
    rectangulo_a = rectangulo_de_un_wkt(a)
    rectangulo_b = rectangulo_de_un_wkt(b)
    if rectangulo_a is None or rectangulo_b is None:
        return SOLAPE_NO_SE
    if not _se_tocan(rectangulo_a, rectangulo_b):
        return SOLAPE_NO
    vertices_a = [punto for anillo in anillos_de_un_wkt(a) for punto in anillo]
    vertices_b = [punto for anillo in anillos_de_un_wkt(b) for punto in anillo]
    for longitud, latitud in vertices_a:
        if _dentro_de_algun_anillo(b, longitud, latitud):
            return SOLAPE_SEGURO
    for longitud, latitud in vertices_b:
        if _dentro_de_algun_anillo(a, longitud, latitud):
            return SOLAPE_SEGURO
    return SOLAPE_POSIBLE


def _se_tocan(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    """¿Se tocan estos dos rectángulos (aunque sea solo en el borde)?"""
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _dentro_de_algun_anillo(wkt: str | None, longitud: float, latitud: float) -> bool:
    """Si el punto cae dentro de la forma, contando los agujeros con la regla par-impar."""
    return punto_dentro_del_wkt(wkt, longitud, latitud) is True
