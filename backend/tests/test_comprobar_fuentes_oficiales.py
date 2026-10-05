"""Comprobar que los datos oficiales siguen igual: que la comprobación no engañe.

Este guion existe para contestar a una pregunta que nadie se hace hasta que es tarde: «¿la lista
oficial que tengo bajada sigue siendo la oficial?». Lo peligroso no es que no funcione, es que diga
**«ha cambiado»** todos los días (y entonces nadie lo mire) o que diga **«sigue igual»** cuando no
lo sabe.

Por eso lo que más se prueba aquí es la diferencia entre dos clases de fuente:

- **Un fichero publicado y quieto** (una norma, un Excel colgado en una web): si cambia un byte, ha
  cambiado el dato. Se compara la huella.
- **Un listado que el servidor genera cada vez que se le pide** (las exportaciones del registro de
  fitosanitarios del MAPA): lleva dentro la hora en que se generó, así que **su huella cambia aunque
  los datos sean los mismos**. Ahí la huella no dice nada y lo que se compara es **cuántas filas
  trae**.

Ninguno de estos tests sale a internet.
"""

from __future__ import annotations

import io
import json
import pathlib
import zipfile

import httpx
from openpyxl import Workbook

from scripts import comprobar_fuentes_oficiales as comprobar

RAIZ = pathlib.Path(__file__).resolve().parents[2]


def _un_xlsx(cuantas_filas: int) -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Datos"
    hoja.append(["codigo", "descripcion"])
    for numero in range(cuantas_filas):
        hoja.append([numero + 1, f"fila {numero + 1}"])
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def _otros_bytes_mismas_filas(contenido: bytes) -> bytes:
    """El mismo Excel con otro contenido byte a byte (como el que genera el servidor cada vez).

    Se le añade un fichero suelto al ZIP, que es lo que hace de verdad una exportación con su fecha
    de generación: las hojas y sus filas son idénticas, los bytes no.
    """
    original = zipfile.ZipFile(io.BytesIO(contenido))
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as nuevo:
        for elemento in original.infolist():
            nuevo.writestr(elemento, original.read(elemento.filename))
        nuevo.writestr("docProps/generado.txt", "generado a las 12:34:56")
    return salida.getvalue()


class TestLoQueSeCompara:
    def test_un_fichero_publicado_se_compara_por_su_huella(self):
        contenido = b"una norma publicada"
        fuente = {
            "nombre": "una norma",
            "url": "https://ejemplo.test/norma.pdf",
            "sha256": __import__("hashlib").sha256(contenido).hexdigest(),
        }
        with httpx.Client(transport=httpx.MockTransport(lambda _p: httpx.Response(200, content=contenido))) as cliente:
            resultado = comprobar.comprueba(cliente, fuente)
        assert resultado["resultado"] == "igual"

    def test_un_fichero_publicado_que_cambia_se_detecta(self):
        fuente = {
            "nombre": "una norma",
            "url": "https://ejemplo.test/norma.pdf",
            "sha256": "0" * 64,
        }
        with httpx.Client(transport=httpx.MockTransport(lambda _p: httpx.Response(200, content=b"otra cosa"))) as cliente:
            resultado = comprobar.comprueba(cliente, fuente)
        assert resultado["resultado"] == "ha_cambiado"
        assert resultado["sha256"] == "0" * 64, "no dice cuál se guardó"
        assert len(resultado["huella_ahora"]) == 64, "no dice cuál hay ahora"

    def test_un_listado_generado_no_se_compara_por_su_huella(self):
        """**Esta es la comprobación que más importa.**

        El mismo listado del MAPA, con las mismas filas, sale con otra huella porque el servidor le
        mete la fecha de generación. Comparando la huella diría «ha cambiado» cada día, y un aviso
        que salta siempre es un aviso que se deja de mirar.
        """
        primero = _un_xlsx(5)
        otro = _otros_bytes_mismas_filas(primero)
        assert otro != primero, "las dos versiones tienen que ser distintas byte a byte"

        fuente = {
            "nombre": "una tabla del MAPA",
            "url": "https://ejemplo.test/ExportExcel",
            "sha256": __import__("hashlib").sha256(primero).hexdigest(),
            "peticion": {"metodo": "POST", "datos": {"tipoExportacion": "Unidades"}},
            "comprobado": "6 filas en «Datos» (1 hoja: Datos: 6)",
        }
        with httpx.Client(transport=httpx.MockTransport(lambda _p: httpx.Response(200, content=otro))) as cliente:
            resultado = comprobar.comprueba(cliente, fuente)

        assert resultado["resultado"] == "igual", "ha dado por cambiado un listado idéntico"
        assert resultado["filas_ahora"] == resultado["filas_antes"] == 6
        assert resultado["huella_ahora"] != fuente["sha256"], "la prueba no está probando lo que cree"

    def test_un_listado_generado_con_otras_filas_se_detecta(self):
        fuente = {
            "nombre": "una tabla del MAPA",
            "url": "https://ejemplo.test/ExportExcel",
            "sha256": "0" * 64,
            "peticion": {"metodo": "POST", "datos": {"tipoExportacion": "Unidades"}},
            "comprobado": "6 filas en «Datos» (1 hoja: Datos: 6)",
        }
        otras = _un_xlsx(9)
        with httpx.Client(transport=httpx.MockTransport(lambda _p: httpx.Response(200, content=otras))) as cliente:
            resultado = comprobar.comprueba(cliente, fuente)
        assert resultado["resultado"] == "ha_cambiado"
        assert resultado["filas_antes"] == 6
        assert resultado["filas_ahora"] == 10  # la cabecera más nueve filas

    def test_la_peticion_se_repite_igual(self):
        """Las tablas del MAPA no se piden con un GET: hay que repetir el POST con su formulario."""
        visto: list[httpx.Request] = []

        def handler(peticion: httpx.Request) -> httpx.Response:
            visto.append(peticion)
            return httpx.Response(200, content=_un_xlsx(1))

        fuente = {
            "nombre": "una tabla del MAPA",
            "url": "https://ejemplo.test/ExportExcel",
            "sha256": "0" * 64,
            "peticion": {"metodo": "POST", "datos": {"tipoExportacion": "Unidades"}},
            "comprobado": "2 filas",
        }
        with httpx.Client(transport=httpx.MockTransport(handler)) as cliente:
            comprobar.comprueba(cliente, fuente)

        assert visto[0].method == "POST"
        assert b"tipoExportacion=Unidades" in visto[0].content


class TestCuandoNoSeSabe:
    def test_si_no_se_puede_llegar_no_se_dice_que_ha_cambiado(self):
        """«No lo sé» no es «ha cambiado»: son dos cosas distintas y se dicen distinto."""
        def handler(_peticion: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("sin red")

        fuente = {"nombre": "una norma", "url": "https://ejemplo.test/x.pdf", "sha256": "0" * 64}
        with httpx.Client(transport=httpx.MockTransport(handler)) as cliente:
            resultado = comprobar.comprueba(cliente, fuente)
        assert resultado["resultado"] == "no_se_pudo"
        assert "ConnectError" in resultado["detalle"]

    def test_un_error_del_servidor_tampoco_es_un_cambio(self):
        fuente = {"nombre": "una norma", "url": "https://ejemplo.test/x.pdf", "sha256": "0" * 64}
        with httpx.Client(transport=httpx.MockTransport(lambda _p: httpx.Response(503))) as cliente:
            resultado = comprobar.comprueba(cliente, fuente)
        assert resultado["resultado"] == "no_se_pudo"
        assert "503" in resultado["detalle"]

    def test_una_fuente_sin_datos_se_dice(self):
        resultado = comprobar.comprueba(httpx.Client(transport=httpx.MockTransport(lambda _p: httpx.Response(200))), {"nombre": "x", "aviso": "no está el fichero"})
        assert resultado["resultado"] == "sin_datos"


class TestLaListaDeFuentes:
    def test_las_fuentes_salen_de_los_ficheros_de_procedencia(self):
        fuentes = comprobar._fuentes()
        assert fuentes, "no se ha leído ninguna fuente: ¿falta algún procedencia.json?"
        urls = [fuente["url"] for fuente in fuentes if fuente.get("url")]
        assert any("fega.gob.es" in url for url in urls), "no están las fuentes del FEGA"
        assert any("mapa.gob.es" in url for url in urls), "no están las del MAPA"
        assert any("opendata.jcyl.es" in url for url in urls), "no está el listado de zonas vulnerables"

    def test_lo_que_se_baja_con_post_lleva_apuntado_como_se_pide(self):
        """Sin esto, la procedencia no sirve para volver a comprobar nada."""
        fuentes = comprobar._fuentes()
        del_mapa = [
            fuente
            for fuente in fuentes
            if "servicio.mapa.gob.es" in (fuente.get("url") or "")
        ]
        assert del_mapa, "no hay ninguna fuente del MAPA"
        for fuente in del_mapa:
            assert fuente.get("peticion"), f"{fuente['nombre']} no dice cómo se pidió"
            assert fuente["peticion"]["metodo"] == "POST"

    def test_la_procedencia_apunta_las_filas_de_lo_que_se_genera(self):
        """Para poder comparar dentro de un mes hace falta saber con cuántas filas se bajó."""
        fuentes = comprobar._fuentes()
        for fuente in fuentes:
            if fuente.get("peticion"):
                assert comprobar._filas_apuntadas(fuente), (
                    f"{fuente['nombre']} no lleva apuntado con cuántas filas se bajó"
                )

    def test_la_huella_del_listado_de_zonas_vulnerables_esta_apuntada(self):
        datos = json.loads((RAIZ / "data" / "zv_cyl_fuentes" / "procedencia.json").read_text(encoding="utf-8"))
        assert len(datos["fuente_excel_sha256"]) == 64
        assert datos["municipios"] == 387
        assert datos["zonas"] == 24
