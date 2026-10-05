"""Todo texto que la interfaz pide, existe.

**Por qué existe esta prueba, con el caso que la trajo.** En la ronda 32 se buscaron, uno por uno,
los textos que pide el JavaScript y salieron **dos fallos de verdad que nadie había visto**:

1. La ficha de la parcela traída del SIGPAC pedía `parcela.ref_sigpac`, que **no existe** en el
   vocabulario de la interfaz (las etiquetas de campo viven dentro de `etiquetas`, y además son
   preguntas). La etiqueta de la referencia salía **en blanco**: el agricultor veía el número del
   recinto sin saber qué número era.
2. Diez sitios pedían `mensajes.no_se_pudo`, que tampoco existía. Cuando fallaba una descarga (el
   cuaderno en papel, el fichero de datos) o una subida (el boletín, el papel firmado), el aviso
   salía **vacío**: el agricultor pulsaba, no pasaba nada y no había ni una palabra que le dijera
   por qué.

Los dos son el mismo fallo de fondo: un texto que falta **no revienta nada**, solo deja un hueco. Y
un hueco no lo caza ninguna prueba que mire si la aplicación «funciona». Se caza buscando.

Esta prueba hace la búsqueda **igual que la hace la aplicación** (`busca()` en `app.js` prueba las
claves más largas posibles antes de partir la ruta, porque hay etiquetas con puntos dentro del
nombre: `comun.fecha` es una sola clave). Y comprueba que el texto **existe**, no que no esté vacío:
hay textos que son listas y pueden estar legítimamente vacías (`limites_que_faltan` cuando no falta
ningún límite, por ejemplo).
"""

from __future__ import annotations

import pathlib
import re

from app.routers import interfaz as router_interfaz

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"

# Las claves que se piden con estas funciones y dónde viven en lo que sirve `/api/interfaz`.
# `mensaje("x")` busca `mensajes.x`, `aviso("x")` busca `aviso.x` y `accion("x")` busca `acciones.x`.
PATRONES = {
    "t": (re.compile(r"""\bt\(\s*["'`]([A-Za-z0-9_.]+)["'`]"""), ""),
    "mensaje": (re.compile(r"""\bmensaje\(\s*["'`]([A-Za-z0-9_.]+)["'`]"""), "mensajes."),
    "aviso": (re.compile(r"""\baviso\(\s*["'`]([A-Za-z0-9_.]+)["'`]"""), "aviso."),
    "accion": (re.compile(r"""\baccion\(\s*["'`]([A-Za-z0-9_.]+)["'`]"""), "acciones."),
}


def _buscador(objeto, claves):
    """La misma búsqueda que `busca()` en `app.js`, y por el mismo motivo.

    Se prueban primero las claves más largas: `etiquetas.comun.fecha.pregunta` tiene que encontrar la
    clave plana `"comun.fecha"` que hay dentro de `etiquetas`. Si aquí se partiera la ruta a lo bruto,
    media aplicación saldría como «texto que falta» y no faltaría ninguno.
    """
    if not claves:
        return objeto
    if not isinstance(objeto, dict):
        return None
    for largo in range(len(claves), 0, -1):
        clave = ".".join(claves[:largo])
        if clave in objeto:
            resto = _buscador(objeto[clave], claves[largo:])
            if resto is not None:
                return resto
    return None


def _claves_pedidas_por_el_javascript() -> dict[str, list[str]]:
    """Qué textos pide el JavaScript, con el sitio donde los pide (fichero y línea)."""
    pedidas: dict[str, list[str]] = {}
    for fichero in sorted(WEB.rglob("*.js")):
        # `vendor/` es React y `htm`, que no son nuestros.
        if "vendor" in fichero.parts:
            continue
        for numero, linea in enumerate(fichero.read_text(encoding="utf-8").splitlines(), 1):
            for patron, prefijo in PATRONES.values():
                for clave in patron.findall(linea):
                    pedidas.setdefault(prefijo + clave, []).append(f"{fichero.name}:{numero}")
    return pedidas


class TestTodosLosTextosExisten:
    def test_la_busqueda_encuentra_textos(self):
        """Si el extractor se rompiera, la prueba de abajo pasaría sin comprobar nada."""
        pedidas = _claves_pedidas_por_el_javascript()
        assert len(pedidas) > 200, (
            f"solo se han encontrado {len(pedidas)} textos pedidos por el JavaScript: "
            "el extractor se ha roto y esta prueba no está comprobando nada"
        )

    def test_no_falta_ningun_texto(self):
        """Y ninguna de las claves que se piden puede quedarse sin texto en el vocabulario."""
        vocabulario = router_interfaz.interfaz()
        pedidas = _claves_pedidas_por_el_javascript()

        faltan = {
            clave: sitios
            for clave, sitios in pedidas.items()
            if _buscador(vocabulario, clave.split(".")) is None
        }
        assert faltan == {}, (
            "la interfaz pide textos que no existen, y saldrían en blanco en la pantalla:\n"
            + "\n".join(
                f"  · {clave} (lo pide {', '.join(sitios[:4])})"
                for clave, sitios in sorted(faltan.items())
            )
        )

    def test_se_comprueba_que_existe_y_no_que_no_este_vacio(self):
        """Y esto se dice aquí porque es una decisión, no un descuido.

        Hay textos que son **listas** y pueden estar vacías sin que falte nada:
        `limites_que_faltan` está vacía cuando no falta ningún límite de nitrógeno, y eso es una
        buena noticia, no un texto que falte. Exigir que no estén vacíos obligaría a inventarse un
        texto para decir «no falta nada», que es justo lo contrario de lo que se quiere.
        """
        vocabulario = router_interfaz.interfaz()
        assert _buscador(vocabulario, ["limites_que_faltan"]) == [], (
            "`limites_que_faltan` ya no está vacía: revisa esta prueba, que habla de su caso"
        )
        assert _buscador(vocabulario, ["limites_que_faltan"]) is not None

    def test_los_dos_fallos_que_trajo_esta_prueba_no_vuelven(self):
        """Los dos casos concretos, con su nombre, para que no se arreglen «a medias» otra vez."""
        vocabulario = router_interfaz.interfaz()
        # 1. El rótulo de la referencia del SIGPAC: no puede pedirse `parcela.ref_sigpac`, que no
        #    existe. Se usa el del bloque del SIGPAC.
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert 't("parcela.ref_sigpac"' not in codigo, (
            "ha vuelto el rótulo que salía en blanco en la ficha de la parcela traída del SIGPAC"
        )
        assert 's("referencia")' in codigo
        # 2. El mensaje general de «no se ha podido»: tiene que existir donde se busca.
        assert "no_se_pudo" in vocabulario["mensajes"], (
            "falta el mensaje general de «no se ha podido» y los avisos volverían a salir en blanco"
        )
        assert vocabulario["mensajes"]["no_se_pudo"].strip()
