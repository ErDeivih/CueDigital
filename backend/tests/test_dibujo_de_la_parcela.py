"""El dibujo del trozo: la forma de la parcela, que estaba en la base de datos y no se veía.

**Por qué existe este fichero.** El SIGPAC devuelve la forma de cada recinto desde la ronda 10
—está descargado en `data/sigpac/recinto_de_ejemplo.json`, con su polígono de verdad— y hasta la
ronda 20 **no se veía en ninguna parte**: se guardaba en la columna `geometria` y ahí se quedaba.
La auditoría de la ronda 18 lo puso en la lista: un dato que entra y no sale.

Lo que se comprueba aquí, por orden de importancia:

1. **Que se dibuje la forma de verdad**, con las coordenadas del polígono.
2. **Que no salga estirada.** Un grado de longitud no mide lo mismo que uno de latitud: en
   Salamanca, 1° de longitud son unos 84 km y 1° de latitud unos 111. Si se dibuja tal cual, la
   parcela sale más ancha de lo que es — y un dibujo que miente sobre la forma de la tierra es
   peor que no tener dibujo.
3. **Que no se invente nada cuando no hay forma.** Una parcela apuntada a mano no tiene
   geometría: ahí no se dibuja un cuadro, no se dibuja nada.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from app import geo

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "data" / "sigpac"


def _poligono_de_verdad() -> str:
    """El WKT de un recinto real del SIGPAC, el que está descargado con los catálogos."""
    datos = json.loads((FIXTURES / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))
    return datos[0]["wkt"]


def _caja(dibujo: str) -> tuple[float, float, float, float]:
    """El rectángulo que ocupa un dibujo, sacado de sus coordenadas."""
    numeros = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", dibujo)]
    xs = numeros[0::2]
    ys = numeros[1::2]
    return min(xs), min(ys), max(xs), max(ys)


class TestSeDibujaLaForma:
    def test_un_recinto_de_verdad_se_dibuja(self):
        dibujo = geo.dibujo_svg(_poligono_de_verdad())
        assert dibujo is not None
        assert dibujo.startswith("M ")
        assert dibujo.endswith("Z")
        assert dibujo.count("L ") >= 2

    def test_todos_los_puntos_caen_dentro_del_cuadro(self):
        """Un punto fuera del `viewBox` se recorta y el agricultor ve una parcela cortada."""
        dibujo = geo.dibujo_svg(_poligono_de_verdad())
        x0, y0, x1, y1 = _caja(dibujo)
        assert 0 <= x0 < x1 <= 100, (x0, x1)
        assert 0 <= y0 < y1 <= 100, (y0, y1)

    def test_el_dibujo_es_el_mismo_siempre(self):
        """Si cambiara entre dos cargas, parecería que la parcela se ha movido."""
        assert geo.dibujo_svg(_poligono_de_verdad()) == geo.dibujo_svg(_poligono_de_verdad())

    def test_se_aprovecha_el_cuadro(self):
        """El lado más largo ocupa el hueco: si no, la parcela sale diminuta en una esquina."""
        dibujo = geo.dibujo_svg(_poligono_de_verdad())
        x0, y0, x1, y1 = _caja(dibujo)
        assert max(x1 - x0, y1 - y0) == pytest.approx(100 - 2 * geo.MARGEN_DEL_DIBUJO, abs=0.01)

    def test_el_dibujo_queda_centrado(self):
        """Lo que sobra del lado corto se reparte a los dos lados, no todo a uno."""
        dibujo = geo.dibujo_svg(_poligono_de_verdad())
        x0, y0, x1, y1 = _caja(dibujo)
        izquierda, derecha = x0 - 0, 100 - x1
        arriba, abajo = y0 - 0, 100 - y1
        assert izquierda == pytest.approx(derecha, abs=0.05)
        assert arriba == pytest.approx(abajo, abs=0.05)


class TestElDibujoNoMienteSobreLaForma:
    """Lo que hace que el dibujo sirva: que no salga estirado."""

    def test_la_correccion_de_la_latitud_cambia_el_dibujo(self):
        """El polígono de verdad, en grados, es mucho más ancho que alto: 0,003026° de longitud
        por 0,002266° de latitud, o sea 1,34 veces más ancho. Pero a 41° de latitud un grado de
        longitud son unos 84 km y uno de latitud unos 111, así que **en el suelo es casi
        cuadrado**. Sin la corrección saldría un tercio más ancho de lo que es.

        Se comprueban las dos cosas: que el dibujo sale casi cuadrado, y que ese «casi cuadrado»
        no es lo que saldría dibujando los grados tal cual.
        """
        import math

        dibujo = geo.dibujo_svg(_poligono_de_verdad())
        x0, y0, x1, y1 = _caja(dibujo)
        dibujada = (x1 - x0) / (y1 - y0)

        numeros = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", _poligono_de_verdad())]
        lons = numeros[0::2]
        lats = numeros[1::2]
        sin_corregir = (max(lons) - min(lons)) / (max(lats) - min(lats))
        con_correccion = sin_corregir * math.cos(
            math.radians(sum(lats) / len(lats))
        )

        assert dibujada == pytest.approx(con_correccion, rel=0.02)
        assert abs(dibujada - sin_corregir) > 0.2, "el dibujo no se ha corregido nada"

    def test_la_proporcion_es_la_de_la_tierra(self):
        """La proporción del dibujo tiene que ser la real en el suelo, no la de los grados."""
        import math

        dibujo = geo.dibujo_svg(_poligono_de_verdad())
        x0, y0, x1, y1 = _caja(dibujo)
        dibujada = (y1 - y0) / (x1 - x0)

        numeros = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", _poligono_de_verdad())]
        lons = numeros[0::2]
        lats = numeros[1::2]
        latitud_media = sum(lats) / len(lats)
        real = (max(lats) - min(lats)) / (
            (max(lons) - min(lons)) * math.cos(math.radians(latitud_media))
        )
        assert dibujada == pytest.approx(real, rel=0.01)

    def test_el_norte_va_arriba(self):
        """En la pantalla la Y crece hacia abajo, así que hay que darle la vuelta.

        Se dibuja un cuadro con un vértice claramente al norte de los demás: ese vértice tiene que
        quedar el más arriba de todos en el dibujo.
        """
        wkt = "POLYGON((0 0, 0.001 0, 0.001 0.001, 0.0005 0.004, 0 0.001, 0 0))"
        dibujo = geo.dibujo_svg(wkt)
        puntos = [
            (float(x), float(y))
            for x, y in re.findall(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)", dibujo)
        ]
        # El cuarto punto del anillo (0.0005 0.004) es el más al norte, y tiene que ser el más
        # arriba en la pantalla (la Y más pequeña).
        assert puntos[3][1] == min(y for _, y in puntos)


class TestCuandoNoHayForma:
    def test_sin_geometria_no_se_dibuja_nada(self):
        """Una parcela apuntada a mano no tiene forma. Un cuadro inventado parecería su parcela."""
        assert geo.dibujo_svg(None) is None
        assert geo.dibujo_svg("") is None

    def test_un_punto_no_es_una_forma(self):
        """Un punto sirve para saber dónde está, pero no tiene forma que dibujar."""
        assert geo.dibujo_svg("POINT(-5.0 40.9)") is None

    def test_dos_puntos_tampoco(self):
        assert geo.dibujo_svg("LINESTRING(-5.0 40.9, -5.001 40.901)") is None

    def test_algo_que_no_es_una_geometria_no_revienta(self):
        """Lo que no se entiende devuelve nada, no una excepción que tumbe la pantalla."""
        assert geo.dibujo_svg("esto no es una geometría") is None
        assert geo.dibujo_svg("POLYGON()") is None

    def test_un_cuadro_de_un_solo_punto_repetido_no_se_dibuja(self):
        assert geo.dibujo_svg("POLYGON((0 0, 0 0, 0 0))") is None


class TestElDibujoLlegaALaPantalla:
    def test_la_parcela_lo_devuelve(self, cliente, cuenta, crear_parcela):
        crear_parcela(alias="Con forma", geometria=_poligono_de_verdad())
        parcelas = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()
        assert parcelas[0]["dibujo"]
        assert parcelas[0]["dibujo"].startswith("M ")

    def test_una_parcela_sin_forma_lo_devuelve_vacio(self, cliente, cuenta, crear_parcela):
        crear_parcela(alias="Sin forma")
        parcelas = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()
        assert parcelas[0]["dibujo"] is None

    def test_no_se_manda_el_wkt_entero(self, cliente, cuenta, crear_parcela):
        """Lo que viaja al móvil es la línea que se pinta, no el texto del polígono."""
        crear_parcela(alias="Con forma", geometria=_poligono_de_verdad())
        parcela = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()[0]
        assert "geometria" not in parcela
        assert len(parcela["dibujo"]) < len(_poligono_de_verdad())

    def test_las_tres_partes_de_la_referencia(self, cliente, cuenta, crear_parcela):
        """El agricultor las tiene en el papel de su parcela: verlas separadas es lo que le
        permite comprobar que la que ha traído el programa es la suya."""
        crear_parcela(
            alias="El Prado",
            ref_sigpac="37-22-0-0-501-427-1",
            poligono=501,
            numero_parcela=427,
            numero_recinto=1,
        )
        parcela = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()[0]
        assert parcela["poligono"] == 501
        assert parcela["numero_parcela"] == 427
        assert parcela["numero_recinto"] == 1


class TestElDibujoEsUnaPropiedadCalculada:
    def test_cambiar_la_forma_cambia_el_dibujo(self, cliente, cuenta, crear_parcela, db_sesion):
        """Si el dibujo se guardara, una corrección de la forma dejaría el viejo.

        Y un dibujo que no es el de la parcela es peor que no tener dibujo.
        """
        from app import models

        parcela = crear_parcela(alias="Con forma", geometria=_poligono_de_verdad())
        antes = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()[0]["dibujo"]

        fila = db_sesion.get(models.Parcela, parcela["id"])
        fila.geometria = "POLYGON((0 0, 0.002 0, 0.002 0.001, 0 0.001, 0 0))"
        db_sesion.commit()

        despues = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()[0]["dibujo"]
        assert despues != antes
