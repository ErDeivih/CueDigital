"""La foto de una tierra: la ortofoto con su contorno dibujado, para la ficha y la trazabilidad.

**Por qué existe este fichero.** David pidió la integración con el SIGPAC con los datos de las
tierras **y el contorno en el mapa de cada parcela para tener la imagen**. La puerta es
`GET /api/mapa/tierra/{parcela_id}.png`; lo que se comprueba aquí, por orden de importancia:

1. **Que salga un PNG del tamaño pedido**, con la ortofoto de fondo y el contorno encima.
2. **Que el contorno se vea de verdad**: la línea blanca sobre la foto y el relleno dentro del
   trozo. Se prueba con una foto sintética inyectada, así que **ninguna prueba sale a internet**.
3. **Que no se invente nada**: una tierra sin forma no devuelve un cuadro (409), y si el servicio
   de la ortofoto no contesta, se dice (503) en vez de servir una imagen que no es la suya.
4. **Que sea dato del agricultor**: sin sesión, 401; la tierra de otra finca, 404.
5. **Que el `fetch` se pueda sustituir**: es lo que permite cumplir el punto 2 sin red.
"""

from __future__ import annotations

import io
import json
import pathlib

import pytest
from PIL import Image

from app import geo, mapa_de_una_tierra as mapa, sigpac

RAIZ = pathlib.Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data" / "sigpac"

# El color de la foto sintética: plano y distinto del relleno y de la línea, para poder contar
# píxeles sin dudas. Si se usara una foto de verdad, no se podría afirmar que un píxel es fondo.
FONDO = (40, 90, 140)
BLANCO = mapa.COLOR_LINEA[:3]


def _la_forma_de_una_tierra_de_verdad() -> str:
    """El WKT de un recinto real del SIGPAC, el mismo que usan las demás pruebas del mapa."""
    datos = json.loads((DATOS / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))
    return datos[0]["wkt"]


WKT = _la_forma_de_una_tierra_de_verdad()


def _una_foto(ancho: int, alto: int) -> bytes:
    """Una foto sintética del tamaño pedido: un color plano, sin salir a internet."""
    salida = io.BytesIO()
    Image.new("RGB", (ancho, alto), FONDO).save(salida, format="PNG")
    return salida.getvalue()


@pytest.fixture
def ortofoto_falsa(monkeypatch):
    """Sustituye el servicio de la ortofoto por una foto plana y apunta lo que se le pide."""
    llamadas: list[dict] = []

    def falsa(capa, oeste, sur, este, norte, ancho, alto):
        llamadas.append(
            {
                "capa": capa,
                "oeste": oeste,
                "sur": sur,
                "este": este,
                "norte": norte,
                "ancho": ancho,
                "alto": alto,
            }
        )
        return _una_foto(ancho, alto), "image/png"

    monkeypatch.setattr(sigpac, "pedir_imagen_del_mapa", falsa)
    return llamadas


def _la_imagen(cliente, cuenta, parcela, **parametros):
    return cliente.get(
        f"/api/mapa/tierra/{parcela['id']}.png",
        headers=cuenta["cabeceras"],
        params=parametros,
    )


class TestLaImagenDeLaTierra:
    def test_es_un_png_del_tamano_pedido(self, cliente, cuenta, crear_parcela, ortofoto_falsa):
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        respuesta = _la_imagen(cliente, cuenta, parcela, ancho=640, alto=480)

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.headers["content-type"].startswith("image/png")
        assert respuesta.content[:8] == b"\x89PNG\r\n\x1a\n", "no es un PNG de verdad"
        assert Image.open(io.BytesIO(respuesta.content)).size == (640, 480)

    def test_sin_decir_tamano_sale_el_de_por_defecto(
        self, cliente, cuenta, crear_parcela, ortofoto_falsa
    ):
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        respuesta = _la_imagen(cliente, cuenta, parcela)

        assert respuesta.status_code == 200, respuesta.text
        assert Image.open(io.BytesIO(respuesta.content)).size == (
            mapa.ANCHO_POR_DEFECTO,
            mapa.ALTO_POR_DEFECTO,
        )

    def test_se_pide_la_foto_del_terreno_de_la_tierra(
        self, cliente, cuenta, crear_parcela, ortofoto_falsa
    ):
        """La caja que se pide al mapa tiene que ser la de la tierra, no otra provincia."""
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        _la_imagen(cliente, cuenta, parcela, ancho=640, alto=480)

        assert len(ortofoto_falsa) == 1, "se le ha pedido la foto al servicio más de una vez"
        pedida = ortofoto_falsa[0]
        assert pedida["capa"] == "foto", "la ortofoto es la capa «foto» del servicio"
        assert (pedida["ancho"], pedida["alto"]) == (640, 480)

        puntos = geo.puntos_del_wkt(WKT)
        longitudes = [punto[0] for punto in puntos]
        latitudes = [punto[1] for punto in puntos]
        assert pedida["oeste"] < min(longitudes) < max(longitudes) < pedida["este"]
        assert pedida["sur"] < min(latitudes) < max(latitudes) < pedida["norte"]


class TestElContornoSeVe:
    """La prueba que importa: que la imagen no sea solo la foto, sino la foto con su contorno."""

    def test_hay_linea_blanca_del_contorno(
        self, cliente, cuenta, crear_parcela, ortofoto_falsa
    ):
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        respuesta = _la_imagen(cliente, cuenta, parcela, ancho=640, alto=480)

        imagen = Image.open(io.BytesIO(respuesta.content)).convert("RGB")
        cuantos_colores = imagen.size[0] * imagen.size[1]
        colores = {
            color: cuantos
            for cuantos, color in (imagen.getcolors(maxcolors=cuantos_colores) or [])
        }
        blancos = colores.get(BLANCO, 0)
        assert blancos > 100, f"el contorno no se ve: solo {blancos} píxeles de la línea"

    def test_el_interior_cambia_y_lo_de_fuera_no(
        self, cliente, cuenta, crear_parcela, ortofoto_falsa
    ):
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        respuesta = _la_imagen(cliente, cuenta, parcela, ancho=640, alto=480)
        imagen = Image.open(io.BytesIO(respuesta.content)).convert("RGB")

        # Fuera de la tierra (la esquina, dentro del margen) se ve la foto tal cual.
        assert imagen.getpixel((3, 3)) == FONDO, "se ha pintado fuera de la tierra"

        # Dentro de la tierra, el relleno translúcido cambia el color de la foto.
        caja = mapa.caja_de_la_tierra(WKT, 640, 480)
        centro = geo.centroide_wkt(WKT)
        assert centro is not None
        x = round((centro[0] - caja[0]) / (caja[2] - caja[0]) * 640)
        y = round((caja[3] - centro[1]) / (caja[3] - caja[1]) * 480)
        assert imagen.getpixel((x, y)) != FONDO, "el relleno del trozo no se ha dibujado"


class TestLaCaja:
    """La caja se calcula una vez y se usa para pedir la foto y para dibujar: tiene que cuadrar."""

    def test_lleva_margen_alrededor_de_la_tierra(self):
        caja = mapa.caja_de_la_tierra(WKT, 800, 600)
        puntos = geo.puntos_del_wkt(WKT)
        longitudes = [punto[0] for punto in puntos]
        latitudes = [punto[1] for punto in puntos]

        ocupa_x = (max(longitudes) - min(longitudes)) / (caja[2] - caja[0])
        ocupa_y = (max(latitudes) - min(latitudes)) / (caja[3] - caja[1])

        # El lado que limita ocupa 1/1,15 de la caja: el 15 % de margen se reparte a los dos lados.
        assert max(ocupa_x, ocupa_y) == pytest.approx(1 / 1.15, abs=0.01)
        # Y nunca ocupa más que eso: la tierra no puede quedar cortada por el borde.
        assert ocupa_x <= 1 / 1.15 + 0.01
        assert ocupa_y <= 1 / 1.15 + 0.01

    @pytest.mark.parametrize("ancho,alto", [(800, 600), (400, 800), (1200, 300)])
    def test_respeta_el_aspecto_de_la_imagen(self, ancho, alto):
        caja = mapa.caja_de_la_tierra(WKT, ancho, alto)
        assert (caja[2] - caja[0]) / (caja[3] - caja[1]) == pytest.approx(
            ancho / alto, rel=1e-6
        ), "la foto saldría deformada"

    def test_una_tierra_sin_forma_no_tiene_caja(self):
        with pytest.raises(mapa.SinForma):
            mapa.caja_de_la_tierra(None, 800, 600)
        with pytest.raises(mapa.SinForma):
            mapa.caja_de_la_tierra("POINT(-5.5 40.9)", 800, 600)


class TestNoSeInventaNada:
    def test_una_tierra_sin_forma_contesta_409_y_no_pide_foto(
        self, cliente, cuenta, crear_parcela, ortofoto_falsa
    ):
        parcela = crear_parcela(alias="Apuntada a mano", geometria=None)

        respuesta = _la_imagen(cliente, cuenta, parcela)

        assert respuesta.status_code == 409, respuesta.text
        assert "forma" in respuesta.json()["detail"].lower()
        assert ortofoto_falsa == [], "no se pide una foto para una tierra que no tiene contorno"

    def test_si_la_ortofoto_no_contesta_se_dice(
        self, cliente, cuenta, crear_parcela, monkeypatch
    ):
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        def sin_red(*argumentos, **opciones):
            raise sigpac.SigpacNoContesta("sin red")

        monkeypatch.setattr(sigpac, "pedir_imagen_del_mapa", sin_red)
        respuesta = _la_imagen(cliente, cuenta, parcela)

        assert respuesta.status_code == 503, respuesta.text
        assert "conexión" in respuesta.json()["detail"].lower()

    def test_si_el_servicio_contesta_algo_que_no_es_una_foto_no_se_sirve(
        self, cliente, cuenta, crear_parcela, monkeypatch
    ):
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        monkeypatch.setattr(
            sigpac, "pedir_imagen_del_mapa", lambda *a, **k: (b'{"vaya": 1}', "application/json")
        )
        respuesta = _la_imagen(cliente, cuenta, parcela)

        assert respuesta.status_code == 503, respuesta.text

    def test_una_tierra_que_no_es_de_esta_finca_contesta_404(
        self, cliente, crear_parcela, crear_cuenta
    ):
        """Ni se dice si existe: `deps.obtener_de_la_explotacion` devuelve 404, no 403."""
        suya = crear_parcela(alias="La mía", geometria=WKT)
        otro = crear_cuenta(correo="otro@ejemplo.test", nombre="Otro", nif="12345678Z")

        respuesta = cliente.get(
            f"/api/mapa/tierra/{suya['id']}.png", headers=otro["cabeceras"]
        )

        assert respuesta.status_code == 404, respuesta.text

    def test_una_tierra_que_no_existe_contesta_404(self, cliente, cuenta):
        respuesta = cliente.get("/api/mapa/tierra/99999.png", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 404, respuesta.text


class TestLaPuertaEsDelAgricultor:
    def test_sin_sesion_contesta_401(self, cliente, crear_parcela, cuenta):
        """La imagen lleva los datos de su tierra: no es pública, aunque la ortofoto sí lo sea."""
        parcela = crear_parcela(alias="El prado", geometria=WKT, **{"superficie_ha": 2.4})
        _ = cuenta  # la finca tiene que existir antes de pedir la imagen sin vale

        respuesta = cliente.get(f"/api/mapa/tierra/{parcela['id']}.png")

        assert respuesta.status_code == 401, respuesta.text


class TestLosTopesDeTamano:
    @pytest.mark.parametrize(
        "ancho,alto",
        [
            (mapa.ANCHO_MINIMO - 1, 480),
            (mapa.ANCHO_MAXIMO + 1, 480),
            (640, mapa.ALTO_MINIMO - 1),
            (640, mapa.ALTO_MAXIMO + 1),
        ],
    )
    def test_un_tamano_fuera_de_los_topes_contesta_422(
        self, cliente, cuenta, crear_parcela, ortofoto_falsa, ancho, alto
    ):
        parcela = crear_parcela(alias="El prado", geometria=WKT)

        respuesta = _la_imagen(cliente, cuenta, parcela, ancho=ancho, alto=alto)

        assert respuesta.status_code == 422, respuesta.text
        assert "píxeles" in respuesta.json()["detail"]
        assert ortofoto_falsa == [], "no se pide la foto si el tamaño no vale"


class TestElFetchSePuedeSustituir:
    """Lo que permite probarlo todo sin red: el servicio de la ortofoto es una función."""

    def test_el_fetch_inyectado_evita_internet(self):
        llamadas: list[tuple] = []

        def fetch(capa, oeste, sur, este, norte, ancho, alto):
            llamadas.append((capa, oeste, sur, este, norte, ancho, alto))
            return _una_foto(ancho, alto), "image/png"

        png = mapa.imagen_de_la_tierra(WKT, 320, 240, fetch=fetch)

        assert len(llamadas) == 1, "el fetch se tiene que llamar una vez"
        assert llamadas[0][0] == "foto"
        assert Image.open(io.BytesIO(png)).size == (320, 240)

    def test_un_fetch_que_falla_se_convierte_en_sin_ortofoto(self):
        def fetch(*argumentos, **opciones):
            raise RuntimeError("se ha caído")

        with pytest.raises(mapa.SinOrtofoto):
            mapa.imagen_de_la_tierra(WKT, 320, 240, fetch=fetch)

    def test_un_fetch_sin_forma_no_llega_a_pedir_foto(self):
        llamadas: list[tuple] = []

        def fetch(*argumentos, **opciones):
            llamadas.append(argumentos)
            return _una_foto(320, 240), "image/png"

        with pytest.raises(mapa.SinForma):
            mapa.imagen_de_la_tierra(None, 320, 240, fetch=fetch)
        assert llamadas == []
