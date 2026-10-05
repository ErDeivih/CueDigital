"""La versión de la aplicación se ve en pantalla, y es la de verdad.

**Por qué existe esta prueba (30/09/2026, la pidió David).** Con la aplicación abierta en el móvil y en el
ordenador, y con la caché del navegador por medio, se quedó sin respuesta la pregunta que más importa
cuando algo se ve raro: **«¿estoy viendo lo nuevo o lo viejo?»**. No había forma de saberlo sin abrir las
herramientas del navegador, y así es imposible que un agricultor (o yo mismo) distinga «esto no funciona»
de «esto es la versión de antes».

La decisión: el pie de todas las pantallas dice la versión (`app.js`, `pintarPie`), y esa versión es **la
misma cadena que el nombre de la caché** del `service-worker.js`. Si las dos se separan pasan dos cosas
malas, y las dos son silenciosas:

  · si la caché **no** sube, el navegador sigue sirviendo los ficheros viejos y la pantalla no cambia
    aunque la versión que se enseña sea nueva (mentira en pantalla);
  · si el número **no** se enseña, no hay forma de comprobar cuál de las dos cosas está pasando.

Por eso lo que se comprueba aquí no es el número (que cambia cada vez que se despliega algo) sino que
**los dos números sean el mismo** y que el pie lo pinte de verdad.
"""

from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"


def _version_de_la_aplicacion() -> str:
    codigo = (WEB / "app.js").read_text(encoding="utf-8")
    encontrado = re.search(r'const VERSION_DE_LA_APLICACION = "([^"]+)"', codigo)
    assert encontrado, "app.js no dice la versión de la aplicación"
    return encontrado.group(1)


def _version_de_la_cache() -> str:
    codigo = (WEB / "service-worker.js").read_text(encoding="utf-8")
    encontrado = re.search(r'const CACHE = "cuedigital-([^"]+)"', codigo)
    assert encontrado, "el service-worker no dice el nombre de su caché"
    return encontrado.group(1)


class TestLaVersionSeVe:
    def test_la_version_del_pie_y_la_de_la_cache_son_la_misma(self):
        """Si se separan, o el navegador sirve lo viejo, o el número que se enseña es mentira."""
        del_pie = _version_de_la_aplicacion()
        de_la_cache = _version_de_la_cache()
        assert del_pie == de_la_cache, (
            f"la versión que se enseña ({del_pie}) y la caché ({de_la_cache}) no son la misma: "
            "el pie diría una versión que no es la que hay en el navegador"
        )

    def test_la_version_tiene_la_forma_de_una_fecha(self):
        """Con fecha se sabe de un vistazo si lo que se ve es de esta ronda o de la de hace un mes."""
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d+", _version_de_la_aplicacion()), (
            "la versión no lleva la fecha y un número (AAAA-MM-DD-N)"
        )

    def test_el_pie_la_ensena(self):
        """Y se enseña en el pie, que es lo único que está en todas las pantallas sin ocupar sitio."""
        codigo = (WEB / "app.js").read_text(encoding="utf-8")
        assert "VERSION_DE_LA_APLICACION" in codigo.split("function pintarPie()", 1)[1][:900], (
            "el pie no enseña la versión"
        )
