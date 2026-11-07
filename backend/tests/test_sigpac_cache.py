"""La caché de la descarga oficial del SIGPAC por provincia (AGR-3).

### Qué es esto

El FEGA publica el SIGPAC entero **en GeoPackage, una provincia por fichero y campaña**
(`https://sigpac-hubcloud.es/geopackages/{campaña}/recintos/`). Descargar la provincia una vez y
guardarla evita pedir un recinto por cada punto: es lo que AGR-3 pide para traer las parcelas en
lote.

### De dónde sale el patrón, y por qué se lee el listado

El nombre real, comprobado en el listado del servidor el 04/11/2026, es
`37_SALAMANCA_rec_2026_20251215_gpkg.zip` (628 MB la de Salamanca): el patrón es
`{PROVINCIA}_{NOMBRE}_rec_{CAMPAÑA}_{AAAAMMDD}_gpkg.zip`, donde `AAAAMMDD` es **la fecha de
validez** de los datos y cambia con cada actualización. Por eso **no se adivina la fecha**: se
lee el listado de la campaña y se busca el enlace de esa provincia. Lo verificado, con fecha y
URL, está en `docs/INVESTIGACION-AGRICOLA.md` (apartados 1.2 y 1.5).

Licencia: **CC BY 4.0**, con cita al FEGA y —al distribuir recintos— a la Dirección General del
Catastro. Se guarda en la ficha de cada descarga para que no se pierda.

### Lo que estos tests NO hacen

**No salen a internet.** La descarga se prueba con un `fetch` falso que devuelve un listado HTML
y un ZIP mínimo con un `.gpkg` dentro. El fichero real de 628 MB no se baja en la suite.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile

import pytest

from app import sigpac_cache

NOMBRE_SALAMANCA = "37_SALAMANCA_rec_2026_20251215_gpkg.zip"

LISTADO_DE_VERDAD = f"""<html><body><pre>
<a href="../">../</a>
<a href="05_AVILA_rec_2026_20251215_gpkg.zip">05_AVILA_rec_2026_20251215_gpkg.zip</a>
<a href="09_BURGOS_rec_2026_20251215_gpkg.zip">09_BURGOS_rec_2026_20251215_gpkg.zip</a>
<a href="{NOMBRE_SALAMANCA}">{NOMBRE_SALAMANCA}</a>
</pre></body></html>"""


def un_zip_con_un_gpkg(nombre_del_gpkg: str = "37_SALAMANCA_rec_2026_20251215.gpkg") -> bytes:
    """Un ZIP mínimo, como el que publica el FEGA: un `.gpkg` dentro."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as paquete:
        paquete.writestr(nombre_del_gpkg, b"SQLite format 3\x00 datos del recinto")
    return memoria.getvalue()


class ServidorDeMentira:
    """El `fetch` inyectable: contesta el listado o el fichero, según la dirección.

    Es lo que permite probar la descarga entera (listado, enlace, ZIP, sha256, ficha) sin
    depender de que el FEGA esté disponible, que es la regla de la casa.
    """

    def __init__(self, listado: str = LISTADO_DE_VERDAD, fichero: bytes | None = None):
        self.listado = listado
        self.fichero = un_zip_con_un_gpkg() if fichero is None else fichero
        self.llamadas: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.llamadas.append(url)
        # El listado es la carpeta (termina en barra); el fichero es un `.zip`.
        if url.endswith("/"):
            return self.listado.encode("utf-8")
        return self.fichero


@pytest.fixture(autouse=True)
def cache_en_una_carpeta_temporal(monkeypatch, tmp_path):
    """**La caché nunca se escribe dentro del proyecto** en los tests.

    Igual que `CUEDIGITAL_ADJUNTOS` en `conftest.py`: sin esto, cada ejecución dejaría un
    GeoPackage de mentira en `datos/sigpac_cache` del repositorio y nadie se enteraría.
    """
    destino = tmp_path / "sigpac_cache"
    monkeypatch.setenv("CUEDIGITAL_SIGPAC_CACHE", str(destino))
    return destino


class TestLaDescarga:
    def test_descarga_el_mapa_de_la_provincia_y_guarda_su_ficha(
        self, cache_en_una_carpeta_temporal
    ):
        servidor = ServidorDeMentira()
        ficha = sigpac_cache.descargar_provincia(37, 2026, fetch=servidor)

        assert ficha["provincia"] == 37
        assert ficha["campana"] == 2026
        assert ficha["fichero"] == NOMBRE_SALAMANCA, "el nombre es el que publica el FEGA"
        assert ficha["bytes"] == len(servidor.fichero)
        assert ficha["sha256"] == hashlib.sha256(servidor.fichero).hexdigest()
        assert ficha["fecha_validez"] == "2025-12-15", "sale del nombre, no se adivina"
        assert ficha["descargado"] is True

        # El fichero está en la carpeta y la ficha también.
        assert (cache_en_una_carpeta_temporal / NOMBRE_SALAMANCA).read_bytes() == servidor.fichero
        fichas = list(cache_en_una_carpeta_temporal.glob("*.json"))
        assert len(fichas) == 1

    def test_la_ficha_dice_la_licencia_y_de_quien_es_el_dato(
        self, cache_en_una_carpeta_temporal
    ):
        """CC BY 4.0 obliga a citar: la cita viaja con la ficha, no en un comentario."""
        ficha = sigpac_cache.descargar_provincia(37, 2026, fetch=ServidorDeMentira())
        assert "CC BY 4.0" in ficha["licencia"]
        assert "FEGA" in ficha["licencia"]
        assert "FONDO ESPAÑOL DE GARANTÍA AGRARIA" in ficha["atribucion"]

    def test_la_segunda_vez_no_vuelve_a_bajar_nada(self, cache_en_una_carpeta_temporal):
        """Con el fichero ya en la caché no se pide otra vez: son 628 MB por provincia."""
        servidor = ServidorDeMentira()
        primera = sigpac_cache.descargar_provincia(37, 2026, fetch=servidor)
        llamadas_tras_la_primera = len(servidor.llamadas)
        assert llamadas_tras_la_primera == 2, "listado + fichero"

        segunda = sigpac_cache.descargar_provincia(37, 2026, fetch=servidor)
        assert len(servidor.llamadas) == llamadas_tras_la_primera, "no se ha vuelto a llamar"
        assert segunda["descargado"] is False
        assert segunda["sha256"] == primera["sha256"]

    def test_se_pide_el_listado_de_la_campana_que_se_dice(
        self, cache_en_una_carpeta_temporal
    ):
        servidor = ServidorDeMentira()
        sigpac_cache.descargar_provincia(37, 2026, fetch=servidor)
        assert servidor.llamadas[0].endswith("/geopackages/2026/recintos/"), servidor.llamadas[0]
        assert servidor.llamadas[1].endswith(NOMBRE_SALAMANCA)

    def test_la_direccion_base_se_puede_cambiar_para_probar(
        self, cache_en_una_carpeta_temporal
    ):
        servidor = ServidorDeMentira()
        sigpac_cache.descargar_provincia(
            37, 2026, fetch=servidor, url_base="https://mi.servidor.de.pruebas/geopackages"
        )
        assert servidor.llamadas[0].startswith("https://mi.servidor.de.pruebas/geopackages/")

    def test_si_la_provincia_no_esta_en_el_listado_se_dice_y_no_se_inventa(
        self, cache_en_una_carpeta_temporal
    ):
        servidor = ServidorDeMentira()
        with pytest.raises(sigpac_cache.SinFichero) as fallo:
            sigpac_cache.descargar_provincia(24, 2026, fetch=servidor)
        mensaje = str(fallo.value)
        assert "24" in mensaje, "dice de qué provincia"
        assert "2026" in mensaje, "y de qué campaña"
        assert list(cache_en_una_carpeta_temporal.glob("*")) == [], "no se ha guardado nada"

    def test_si_no_hay_red_se_dice_y_no_se_guarda_nada(self, cache_en_una_carpeta_temporal):
        def sin_red(url):
            raise ConnectionError("no hay red")

        with pytest.raises(sigpac_cache.SinRed):
            sigpac_cache.descargar_provincia(37, 2026, fetch=sin_red)
        assert list(cache_en_una_carpeta_temporal.glob("*")) == []

    def test_un_fichero_que_no_es_un_zip_no_se_guarda(self, cache_en_una_carpeta_temporal):
        """Si el servidor devuelve una página de mantenimiento, no se guarda como si fuera el mapa."""
        servidor = ServidorDeMentira(fichero=b"<html>Servicio en mantenimiento</html>")
        with pytest.raises(sigpac_cache.FicheroNoValido):
            sigpac_cache.descargar_provincia(37, 2026, fetch=servidor)
        assert list(cache_en_una_carpeta_temporal.glob("*")) == []

    def test_un_zip_que_no_lleva_ningun_gpkg_no_se_guarda(self, cache_en_una_carpeta_temporal):
        servidor = ServidorDeMentira(fichero=un_zip_con_un_gpkg("leeme.txt"))
        with pytest.raises(sigpac_cache.FicheroNoValido) as fallo:
            sigpac_cache.descargar_provincia(37, 2026, fetch=servidor)
        assert "gpkg" in str(fallo.value).lower()
        assert list(cache_en_una_carpeta_temporal.glob("*")) == []

    def test_una_provincia_que_no_existe_se_rechaza(self, cache_en_una_carpeta_temporal):
        with pytest.raises(ValueError):
            sigpac_cache.descargar_provincia(99, 2026, fetch=ServidorDeMentira())
        assert list(cache_en_una_carpeta_temporal.glob("*")) == []


class TestLaDescargaPorTrozos:
    """El camino de red de verdad escribe por trozos a un temporal (no carga 628 MB en RAM)."""

    def _stream_que_escribe(self, contenido: bytes, visto: list | None = None):
        def stream(url, destino):
            if visto is not None:
                visto.append((url, destino))
            destino.write_bytes(contenido)
            return len(contenido), hashlib.sha256(contenido).hexdigest()

        return stream

    def test_la_descarga_por_trozos_guarda_el_zip_y_su_ficha(
        self, cache_en_una_carpeta_temporal
    ):
        fichero = un_zip_con_un_gpkg()
        visto: list = []
        ficha = sigpac_cache.descargar_provincia(
            37,
            2026,
            fetch=ServidorDeMentira(),
            stream=self._stream_que_escribe(fichero, visto),
        )

        assert ficha["bytes"] == len(fichero)
        assert ficha["sha256"] == hashlib.sha256(fichero).hexdigest()
        assert (cache_en_una_carpeta_temporal / NOMBRE_SALAMANCA).read_bytes() == fichero
        # Al callback se le da un temporal, nunca el nombre final: si se corta, no parece bueno.
        _url, destino = visto[0]
        assert destino.name != NOMBRE_SALAMANCA
        assert destino.name.endswith(".descargando")
        assert list(cache_en_una_carpeta_temporal.glob("*.descargando")) == []

    def test_si_el_stream_falla_no_queda_nada(self, cache_en_una_carpeta_temporal):
        def sin_red(url, destino):
            raise ConnectionError("se ha cortado la conexión")

        with pytest.raises(sigpac_cache.SinRed):
            sigpac_cache.descargar_provincia(
                37, 2026, fetch=ServidorDeMentira(), stream=sin_red
            )
        assert list(cache_en_una_carpeta_temporal.glob("*")) == []

    def test_si_el_stream_no_trae_un_zip_no_se_guarda(
        self, cache_en_una_carpeta_temporal
    ):
        with pytest.raises(sigpac_cache.FicheroNoValido):
            sigpac_cache.descargar_provincia(
                37,
                2026,
                fetch=ServidorDeMentira(),
                stream=self._stream_que_escribe(b"<html>mantenimiento</html>"),
            )
        assert list(cache_en_una_carpeta_temporal.glob("*")) == []

    def test_si_el_stream_llega_vacio_no_se_guarda(self, cache_en_una_carpeta_temporal):
        with pytest.raises(sigpac_cache.SinRed):
            sigpac_cache.descargar_provincia(
                37, 2026, fetch=ServidorDeMentira(), stream=self._stream_que_escribe(b"")
            )
        assert list(cache_en_una_carpeta_temporal.glob("*")) == []


class TestElEstado:
    def test_el_estado_lista_lo_descargado(self, cache_en_una_carpeta_temporal):
        sigpac_cache.descargar_provincia(37, 2026, fetch=ServidorDeMentira())
        estado = sigpac_cache.estado_cache()
        assert estado["cuantas"] == 1
        ficha = estado["provincias"][0]
        assert ficha["provincia"] == 37
        assert ficha["campana"] == 2026
        assert ficha["fecha_validez"] == "2025-12-15"
        assert ficha["bytes"] > 0
        assert len(ficha["sha256"]) == 64
        assert "CC BY 4.0" in estado["licencia"]

    def test_el_estado_no_dice_donde_esta_la_carpeta_del_servidor(
        self, cache_en_una_carpeta_temporal
    ):
        """La ruta absoluta de la instalación no sale por la API.

        Es el mismo defecto que se quitó de `GET /api/sigpac/estado` el 03/10/2026
        (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.13): decir dónde tiene los datos el servidor
        y con qué usuario corre no le sirve al agricultor y sí a quien busque por dónde entrar.
        """
        sigpac_cache.descargar_provincia(37, 2026, fetch=ServidorDeMentira())
        estado = sigpac_cache.estado_cache()
        texto = json.dumps(estado, ensure_ascii=False)
        assert str(cache_en_una_carpeta_temporal) not in texto
        assert "carpeta" not in {clave.lower() for clave in estado}

    def test_sin_nada_descargado_el_estado_esta_vacio_y_no_revienta(self):
        estado = sigpac_cache.estado_cache()
        assert estado["cuantas"] == 0
        assert estado["provincias"] == []

    def test_un_fichero_borrado_no_se_cuenta_como_descargado(
        self, cache_en_una_carpeta_temporal
    ):
        """Decir «está descargada» cuando el fichero ya no está sería mentir en el estado.

        La ficha se queda (es el registro de que se bajó), pero si el ZIP no está, esa provincia
        no está disponible: se cuenta como que no y se puede volver a pedir.
        """
        sigpac_cache.descargar_provincia(37, 2026, fetch=ServidorDeMentira())
        (cache_en_una_carpeta_temporal / NOMBRE_SALAMANCA).unlink()

        estado = sigpac_cache.estado_cache()
        assert estado["cuantas"] == 0, "el fichero no está: no se puede decir que esté"
        assert estado["provincias"] == []


class TestLaApi:
    """Las dos puertas: `GET /api/sigpac/cache` y `POST /api/sigpac/cache/{provincia}`."""

    def test_el_estado_se_puede_mirar_con_sesion(self, cliente, cuenta):
        respuesta = cliente.get("/api/sigpac/cache", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["cuantas"] == 0
        assert "licencia" in datos
        assert "textos" in datos, "los textos salen del servidor, como en el resto"

    def test_sin_sesion_no_se_mira(self, cliente):
        assert cliente.get("/api/sigpac/cache").status_code == 401

    def test_sin_sesion_no_se_descarga(self, cliente):
        assert cliente.post("/api/sigpac/cache/37").status_code == 401

    def test_la_descarga_se_pide_con_sesion(self, cliente, cuenta, monkeypatch):
        """La puerta usa el camino real: listado por `fetch_http` y ZIP por `stream_http`.

        Se sustituyen las dos funciones de red (la suite no sale a internet): lo que se prueba es
        la puerta y que el ZIP llega a la caché por el camino de streaming.
        """
        servidor = ServidorDeMentira()
        monkeypatch.setattr(sigpac_cache, "fetch_http", servidor)

        def stream_local(url, destino):
            destino.write_bytes(servidor.fichero)
            return len(servidor.fichero), hashlib.sha256(servidor.fichero).hexdigest()

        monkeypatch.setattr(sigpac_cache, "stream_http", stream_local)
        respuesta = cliente.post(
            "/api/sigpac/cache/37?campana=2026", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["provincia"] == 37
        assert datos["fichero"] == NOMBRE_SALAMANCA
        assert datos["sha256"]
        # Y queda en la caché: el estado lo dice.
        estado = cliente.get("/api/sigpac/cache", headers=cuenta["cabeceras"]).json()
        assert estado["cuantas"] == 1

    def test_sin_poder_modificar_no_se_descarga(self, cliente, cuenta, db_sesion, monkeypatch):
        """Descargar 628 MB es escribir en el servidor: la puerta lo exige y **no llama al FEGA**."""
        from sqlalchemy import select

        from app import models

        servidor = ServidorDeMentira()
        monkeypatch.setattr(sigpac_cache, "fetch_http", servidor)

        db_sesion.expire_all()
        acceso = db_sesion.scalar(
            select(models.AccesoAFinca).where(
                models.AccesoAFinca.usuario_id == cuenta["usuario_id"],
                models.AccesoAFinca.explotacion_id == cuenta["explotacion_id"],
            )
        )
        assert acceso is not None
        acceso.puede_modificar = False
        db_sesion.commit()

        respuesta = cliente.post(
            "/api/sigpac/cache/37?campana=2026", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 403, respuesta.text
        assert servidor.llamadas == [], "sin permiso no se ha pedido nada al FEGA"

    def test_sin_red_contesta_503_y_lo_dice(self, cliente, cuenta, monkeypatch):
        def sin_red(url):
            raise ConnectionError("no hay red")

        monkeypatch.setattr(sigpac_cache, "fetch_http", sin_red)
        respuesta = cliente.post(
            "/api/sigpac/cache/37?campana=2026", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 503, respuesta.text
        assert "SIGPAC" in respuesta.json()["detail"]

    def test_una_provincia_que_no_existe_contesta_422(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/sigpac/cache/99?campana=2026", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 422, respuesta.text


class TestElNombreDelFichero:
    def test_la_fecha_de_validez_se_lee_del_nombre(self):
        assert sigpac_cache.fecha_de_validez(NOMBRE_SALAMANCA) == "2025-12-15"

    def test_un_nombre_que_no_es_del_sigpac_no_inventa_fecha(self):
        assert sigpac_cache.fecha_de_validez("leeme.txt") is None
