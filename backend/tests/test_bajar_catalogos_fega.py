"""Bajar los catálogos oficiales: que se baje lo que se puede y que **no** se toque el captcha.

Este test existe por un motivo muy concreto: la tentación. Cuando un catálogo oficial está detrás de un
captcha y hace falta, es facilísimo «arreglarlo» metiendo esa dirección en el guion de descarga y
buscándole la vuelta. Eso no se hace: saltarse un captcha es saltarse la norma de una web. Aquí hay
una prueba que **revienta si alguien lo intenta** (ver `TestNoSeTocaLoQueEstaProhibido`), y el LEEME
publica la lista de lo que falta con su dirección, para que se pueda pedir.

Lo que se comprueba:

1. Que la procedencia (dirección, fecha, huella) es la **de verdad**: la huella se recalcula del
   fichero que hay en el disco, no se copia de ningún sitio.
2. Que un fichero que no llega **no se guarda** y se dice con su dirección y su código HTTP.
3. Que una página web con un 200 donde se esperaba un Excel **no pasa por catálogo**.
4. Que el LEEME cuenta lo que hay, lo que **no** hay y por qué, y avisa de los dos catálogos que se
   llaman parecido.
5. Que la ruta `--sin-descarga` no toca la red.

**Ninguna prueba de este fichero sale a internet.**
"""

from __future__ import annotations

import hashlib
import io
import json
import pathlib

import httpx
import pytest
from openpyxl import Workbook

from scripts import bajar_catalogos_fega as bajar

RAIZ = pathlib.Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "data" / "fega"


# --------------------------------------------------------------------------
# Un servidor de mentira, para no salir a internet
# --------------------------------------------------------------------------


def _un_xlsx(filas: int = 3) -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Datos"
    hoja.append(["codigo", "descripcion"])
    for numero in range(filas):
        hoja.append([numero + 1, f"fila {numero + 1}"])
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


PAGINA_CON_ENLACE = (
    "<html><body><a href=\"/sites/default/files/files/document/2025.11.14-ANEXO.pdf\">Anexo</a>"
    "</body></html>"
)
PAGINA_DEL_MAPA = (
    "<html><body><a href=\"/dam/plagas.xlsx\">Plagas</a>"
    "<a href=\"/dam/jerarquia.xlsx\">Jerarquía</a></body></html>"
)


def _servidor(registro: list[str], *, xlsx: bytes | None = None, falla: set[str] | None = None):
    """Un `httpx.MockTransport` que contesta como el FEGA y el MAPA, y apunta lo que se le pide."""
    falla = falla or set()
    contenido_xlsx = xlsx or _un_xlsx()

    def handler(peticion: httpx.Request) -> httpx.Response:
        url = str(peticion.url)
        registro.append(f"{peticion.method} {url}")
        if any(prohibida in url for prohibida in ("bdcsixpor/catalogos", "login/portal", "/search/site")):
            raise AssertionError(f"se ha llamado a una dirección prohibida: {url}")
        if url in falla:
            return httpx.Response(404, text="no está")
        if url.endswith(".docx"):
            return httpx.Response(200, content=b"PK\x03\x04falso", headers={"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"})
        if url.endswith(".pdf"):
            return httpx.Response(200, content=b"%PDF-1.4 falso", headers={"content-type": "application/pdf"})
        if url.endswith(".xlsx"):
            return httpx.Response(
                200,
                content=contenido_xlsx,
                headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            )
        if "Exportaciones" in url:
            return httpx.Response(
                200,
                content=contenido_xlsx,
                headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            )
        # Las páginas oficiales, con su enlace dentro.
        if "mapa.gob.es" in url and not url.endswith((".xlsx", ".pdf", ".docx")):
            return httpx.Response(200, text=PAGINA_DEL_MAPA, headers={"content-type": "text/html"})
        return httpx.Response(200, text=PAGINA_CON_ENLACE, headers={"content-type": "text/html"})

    return httpx.MockTransport(handler)


@pytest.fixture
def sin_esperas(monkeypatch):
    """Sin las esperas de cortesía: en las pruebas no hay a quién molestar."""
    monkeypatch.setattr(bajar, "SEGUNDOS_ENTRE_PETICIONES", 0)


@pytest.fixture
def carpeta_temporal(monkeypatch, tmp_path):
    monkeypatch.setattr(bajar, "DESTINO", tmp_path)
    return tmp_path


@pytest.fixture
def fuentes_de_mentira(monkeypatch):
    """Un juego de fuentes pequeño, para no depender de los documentos oficiales de verdad."""
    monkeypatch.setattr(
        bajar,
        "FICHEROS_FEGA",
        {
            "anexo_viii_autorizacion_representacion.docx": {
                "url": "https://www.fega.gob.es/sites/default/files/files/document/anexo.docx",
                "que_es": "Un anexo de mentira, para la prueba",
                "comprobacion": "docx",
                "licencia": "FEGA: citando el origen",
            }
        },
    )
    monkeypatch.setattr(
        bajar,
        "EXPORTACIONES_MAPA",
        {"Unidades": {"fichero": "mapa_unidades.xlsx", "que_es": "Unidades", "filas_esperadas": 3}},
    )
    monkeypatch.setattr(
        bajar,
        "LISTADO_DE_PRODUCTOS",
        {"fichero": "mapa_productos.xlsx", "url": "https://servicio.mapa.gob.es/regfiweb/Exportaciones/Productos", "que_es": "Productos"},
    )


def _baja(registro: list[str], **kwargs):
    with httpx.Client(transport=_servidor(registro, **kwargs)) as cliente:
        return bajar.baja_todo(cliente)


# --------------------------------------------------------------------------
# Lo que hay en el disco
# --------------------------------------------------------------------------


class TestLoQueEstaBajado:
    def test_la_procedencia_dice_de_donde_sale_cada_fichero(self):
        """Cada fichero de `data/fega` tiene su dirección, su fecha y su huella."""
        procedencia = json.loads((CARPETA / "procedencia.json").read_text(encoding="utf-8"))
        ficheros = procedencia["ficheros"]
        assert ficheros, "no hay ningún fichero apuntado: lanza scripts/bajar_catalogos_fega.py"

        for nombre in ficheros:
            assert (CARPETA / nombre).exists(), f"{nombre} está apuntado y no está en el disco"

        for nombre, datos in ficheros.items():
            assert datos["url"].startswith("http")
            assert datos["descargado_el"]
            assert datos["que_es"]
            assert datos["licencia"]

    def test_las_huellas_son_las_de_los_ficheros_de_verdad(self):
        """La huella se recalcula del fichero: una procedencia copiada a mano no vale.

        Es el fallo que esto evita: apuntar que un fichero es el que se bajó aquel día cuando en
        realidad alguien lo ha cambiado después.
        """
        procedencia = json.loads((CARPETA / "procedencia.json").read_text(encoding="utf-8"))["ficheros"]
        for nombre, datos in procedencia.items():
            contenido = (CARPETA / nombre).read_bytes()
            assert hashlib.sha256(contenido).hexdigest() == datos["sha256"], (
                f"la huella de {nombre} no es la del fichero que hay"
            )
            assert len(contenido) == datos["bytes"]

    def test_el_leeme_cuenta_lo_mismo_que_la_procedencia(self):
        texto = (CARPETA / "LEEME.md").read_text(encoding="utf-8")
        procedencia = json.loads((CARPETA / "procedencia.json").read_text(encoding="utf-8"))["ficheros"]
        for nombre, datos in procedencia.items():
            assert nombre in texto, f"el LEEME no nombra {nombre}"
            assert datos["sha256"] in texto, f"el LEEME no lleva la huella de {nombre}"
            assert datos["url"] in texto, f"el LEEME no dice de dónde sale {nombre}"

    def test_el_leeme_dice_lo_que_no_se_ha_bajado_y_por_que(self):
        """Lo más importante del LEEME: lo que falta, con su dirección y su motivo."""
        texto = (CARPETA / "LEEME.md").read_text(encoding="utf-8")
        assert "captcha" in texto.lower(), "el LEEME no explica que hay valores detrás de un captcha"
        for bloqueado in bajar.NO_SE_DESCARGA:
            assert bloqueado["url"] in texto
            assert bloqueado["por_que_no"][:40] in texto

    def test_el_leeme_avisa_de_los_dos_catalogos_que_se_llaman_parecido(self):
        """`Unidades` (MAPA) no es `UNIDADES_MEDIDA` (SIEX). Es el error caro, y se avisa arriba."""
        texto = (CARPETA / "LEEME.md").read_text(encoding="utf-8")
        assert "UNIDADES_MEDIDA" in texto
        assert "no es" in texto.split("##")[0], "el aviso tiene que estar antes del primer apartado"

    def test_la_huella_del_anexo_vi_es_la_que_ya_estaba_apuntada(self):
        """El Anexo VI es la base del descriptor del cuaderno: su huella se comprueba con la que hay.

        Si el FEGA publica otra versión, esta prueba es la que avisa de que hay que mirarlo antes de
        dar por bueno el descriptor.
        """
        leeme = (RAIZ / "data" / "iuws_fuentes" / "LEEME.md").read_text(encoding="utf-8")
        assert bajar.HUELLA_ANEXO_VI in leeme
        assert bajar.FICHEROS_FEGA["anexo_vi_interfaz_unico_comun_3.11.4.docx"]["huella_conocida"] == (
            bajar.HUELLA_ANEXO_VI
        )


# --------------------------------------------------------------------------
# Lo que se puede bajar: el guion, con un servidor de mentira
# --------------------------------------------------------------------------


class TestElGuion:
    def test_baja_las_fuentes_y_apunta_su_procedencia(
        self, sin_esperas, carpeta_temporal, fuentes_de_mentira, monkeypatch
    ):
        monkeypatch.setattr(bajar, "DEL_DAM", {"plagas.xlsx": "Plagas"})
        registro: list[str] = []
        procedencia, fallos = _baja(registro)

        assert fallos == []
        assert set(procedencia) == {"anexo_viii_autorizacion_representacion.docx", "mapa_unidades.xlsx", "mapa_productos.xlsx", "mapa_plagas.xlsx"}
        for nombre, datos in procedencia.items():
            assert (carpeta_temporal / nombre).exists()
            assert datos["sha256"] == hashlib.sha256((carpeta_temporal / nombre).read_bytes()).hexdigest()

    def test_un_fichero_que_no_llega_no_se_guarda_y_se_dice_con_su_direccion(
        self, sin_esperas, carpeta_temporal, fuentes_de_mentira, monkeypatch
    ):
        """Un 404 no puede convertirse en un fichero vacío que luego parezca un catálogo."""
        monkeypatch.setattr(bajar, "DEL_DAM", {})
        monkeypatch.setattr(bajar, "LISTADO_DE_PRODUCTOS", {"fichero": "x.xlsx", "url": "https://servicio.mapa.gob.es/regfiweb/Exportaciones/Falla", "que_es": "x"})
        registro: list[str] = []
        procedencia, fallos = _baja(registro, falla={"https://servicio.mapa.gob.es/regfiweb/Exportaciones/Falla"})

        assert "mapa_productos" not in " ".join(procedencia)
        assert not (carpeta_temporal / "x.xlsx").exists()
        assert len(fallos) == 1
        assert "404" in fallos[0] and "Exportaciones/Falla" in fallos[0]

    def test_una_pagina_web_no_pasa_por_catalogo(
        self, sin_esperas, carpeta_temporal, fuentes_de_mentira, monkeypatch
    ):
        """Un HTML con un 200 donde se esperaba un Excel es un captcha o un error: se para."""
        monkeypatch.setattr(bajar, "DEL_DAM", {})
        monkeypatch.setattr(bajar, "LISTADO_DE_PRODUCTOS", {"fichero": "mapa_productos.xlsx", "url": "https://servicio.mapa.gob.es/regfiweb/Exportaciones/Productos", "que_es": "Productos"})

        def handler(peticion: httpx.Request) -> httpx.Response:
            if "Exportaciones" in str(peticion.url):
                return httpx.Response(200, text="<html>captcha</html>", headers={"content-type": "text/html"})
            return httpx.Response(200, content=b"PK\x03\x04", headers={"content-type": "application/octet-stream"})

        with httpx.Client(transport=httpx.MockTransport(handler)) as cliente:
            procedencia, fallos = bajar.baja_todo(cliente)

        assert "mapa_productos.xlsx" not in procedencia
        assert not (carpeta_temporal / "mapa_productos.xlsx").exists()
        assert any("no es un Excel" in fallo for fallo in fallos)

    def test_si_el_documento_oficial_cambia_se_para(
        self, sin_esperas, carpeta_temporal, monkeypatch
    ):
        """El Anexo VI no se sustituye en silencio: si cambia la huella, se para y se dice."""
        monkeypatch.setattr(
            bajar,
            "FICHEROS_FEGA",
            {
                "anexo.docx": {
                    "url": "https://www.fega.gob.es/sites/default/files/files/document/anexo.docx",
                    "que_es": "Un anexo",
                    "comprobacion": "docx",
                    "huella_conocida": "0" * 64,
                    "licencia": "FEGA",
                }
            },
        )
        monkeypatch.setattr(bajar, "EXPORTACIONES_MAPA", {})
        monkeypatch.setattr(bajar, "DEL_DAM", {})

        registro: list[str] = []
        procedencia, fallos = _baja(registro)

        assert "anexo.docx" not in procedencia
        assert not (carpeta_temporal / "anexo.docx").exists()
        assert any("ha cambiado el documento oficial" in fallo for fallo in fallos)

    def test_se_puede_rehacer_el_leeme_sin_tocar_la_red(
        self, sin_esperas, carpeta_temporal, monkeypatch
    ):
        """`--sin-descarga` rehace el LEEME con lo que ya está, y no llama a nadie."""
        (carpeta_temporal / "un_fichero.xlsx").write_bytes(_un_xlsx())
        (carpeta_temporal / "procedencia.json").write_text(
            json.dumps({"ficheros": {"un_fichero.xlsx": {"url": "https://ejemplo.test/un.xlsx", "que_es": "Un fichero", "descargado_el": "2026-09-27", "bytes": 1, "sha256": "a" * 64, "comprobado": "ok", "licencia": "FEGA"}}}),
            encoding="utf-8",
        )

        def no_llames_a_la_red(*_args, **_kwargs):
            raise AssertionError("--sin-descarga ha intentado salir a internet")

        monkeypatch.setattr(bajar.httpx, "Client", no_llames_a_la_red)
        monkeypatch.setattr("sys.argv", ["bajar_catalogos_fega.py", "--sin-descarga"])

        assert bajar.main() == 0
        assert "un_fichero.xlsx" in (carpeta_temporal / "LEEME.md").read_text(encoding="utf-8")


class TestNoSeTocaLoQueEstaProhibido:
    """La prueba más importante de este fichero.

    Las direcciones que están en `NO_SE_DESCARGA` (el captcha de SIEX, el portal con contraseña, el
    buscador que su `robots.txt` prohíbe) **no pueden aparecer en ninguna llamada del guion**. El
    servidor de mentira de estas pruebas revienta si alguien las pide, así que si un día alguien las
    mete «para que funcione», esto se pone en rojo.
    """

    def test_ninguna_direccion_prohibida_se_llama(self, sin_esperas, carpeta_temporal, fuentes_de_mentira, monkeypatch):
        monkeypatch.setattr(bajar, "DEL_DAM", {})
        registro: list[str] = []
        bajar.baja_todo(httpx.Client(transport=_servidor(registro)))
        for prohibida in ("bdcsixpor/catalogos", "login/portal", "/search/site"):
            assert not any(prohibida in llamada for llamada in registro)

    def test_la_lista_de_lo_prohibido_dice_por_que(self):
        """Cada dirección prohibida lleva su motivo escrito, y el del captcha lo dice con esas palabras."""
        motivos = {bloqueado["url"]: bloqueado["por_que_no"] for bloqueado in bajar.NO_SE_DESCARGA}
        assert any("bdcsixpor/catalogos" in url for url in motivos)
        assert any("captcha" in motivo.lower() for motivo in motivos.values())
        assert all(motivo.strip() for motivo in motivos.values())

    def test_ninguna_constante_de_descarga_apunta_a_lo_prohibido(self):
        """Las direcciones prohibidas pueden estar **contadas**, nunca en una constante de descarga.

        Se comprueban las constantes de verdad (las que se usan para pedir), no el texto del fichero:
        el docstring tiene que poder explicar por qué el captcha no se pasa, y ahí sí aparece esa
        dirección.
        """
        direcciones = [datos.get("url") or datos.get("pagina") or "" for datos in bajar.FICHEROS_FEGA.values()]
        direcciones += [
            bajar.EXPORTADOR_MAPA,
            bajar.PAGINA_DEL_REGISTRO,
            bajar.FEGA_DOCS,
            bajar.LISTADO_DE_PRODUCTOS["url"],
        ]
        direcciones += [datos.get("url", "") for datos in bajar.EXPORTACIONES_MAPA.values()]

        for prohibida in ("bdcsixpor/catalogos", "login/portal", "/search/site"):
            assert not any(prohibida in direccion for direccion in direcciones), (
                f"una constante de descarga apunta a {prohibida}"
            )
            assert any(prohibida in bloqueado["url"] for bloqueado in bajar.NO_SE_DESCARGA)
