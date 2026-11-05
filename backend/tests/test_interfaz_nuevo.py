"""Tests de la interfaz nueva, servida aparte en `/nuevo/`.

QUÉ SE COMPRUEBA AQUÍ, Y QUÉ NO

Se comprueba lo que se puede comprobar sin navegador: que los ficheros se sirven, con su
tipo, que la aplicación de siempre sigue viva en `/` (la nueva no la puede romper), que no
hay textos técnicos ni jerga en lo que lee el agricultor y que están los enganches
estables que necesita el arnés de navegador para poder mirar la pantalla sin leer el código.

No se comprueba cómo se ve. Eso exige abrir un navegador de verdad a 390, 1024 y 1440 px,
y lo hace quien revisa el diseño; un test que dijera «la pantalla se ve bien» estaría
mintiendo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import textos

WEB = Path(__file__).resolve().parents[1] / "web"
NUEVO = WEB / "nuevo"

FICHEROS_DE_LA_PANTALLA = ["index.html", "app.js", "estilos.css", "modelo.js"]

# Lo que el arnés de navegador busca en el HTML. Es un contrato cerrado: si alguien lo
# cambia, la verificación del diseño deja de poder hacerse sin leer el código.
ENGANCHES = [
    "data-vista",
    "data-estado",
    "data-nav-lateral",
    "data-nav-inferior",
    "data-destino",
    "data-accion",
    "data-volver",
    "data-tierra-id",
    "data-trabajo-de-hoy",
    "data-historial",
    "data-historial-anio",
    "data-dia-calendario",
    "data-trabajo-del-dia",
    "data-filtro-tipo",
    "data-trabajo-fila",
    "data-mes-anterior",
    "data-mes-siguiente",
    "data-factura-foto",
    "data-factura-leer",
    "data-factura-propuesta",
    "data-factura-guardar",
    "data-factura-resultado",
    "data-buscar-codigos",
    "data-recinto-id",
    "data-recinto-marcado",
    "data-anadir-seleccionados",
    "data-mapa-recinto",
    "data-mapa-ventana",
    "data-importar-cuaderno",
    "data-importar-resultado",
    "data-leyenda-uso",
    "data-resumen-gastos",
    "data-resumen-ventas",
    "data-resumen-cuaderno",
    "data-que-falta",
    "data-editar-alias",
    "data-editar-superficie",
    "data-guardar-alias",
    "data-titulo",
    "data-ultimos",
    "data-contador-tierras",
    "data-totales",
    "data-buscador",
    "data-municipio",
    "data-seleccionada",
    "data-mapa",
    "data-mapa-imagen",
    "data-mapa-error",
    "data-municipio-opcion",
    "data-zoom",
    "data-panel",
    "data-panel-alias",
    "data-panel-datos",
    "data-panel-otros-anios",
    "data-anio",
    "data-entrar",
    "data-reintentar",
    "data-traer-tierras",
]

# Las puertas del servidor que usa la pantalla. Si alguna cambia de dirección, esto salta
# antes de que el agricultor vea una pantalla que no carga nada.
PUERTAS = [
    "/api/nuevo/hoy",
    "/api/nuevo/tierras",
    "/api/nuevo/resumen",
    "/api/nuevo/que-falta",
    "/api/nuevo/importar-cuaderno",
    "/api/nuevo/tierra/",
    "/api/nuevo/calendario",
    "/api/nuevo/trabajos",
    "/api/sigpac/buscar",
    "/api/parcelas/desde-sigpac",
    "/api/parcelas/desde-sigpac/varias",
    "/api/mapa/punto",
    "/api/mapa/tierra/",
    "/api/facturas",
    "/api/facturas/leer",
    "/api/documentos",
    "/api/cuaderno-cyl/leer",
    "/api/cuaderno-cyl/importar",
]

PALABRAS_DE_PROGRAMADOR = [
    "token",
    "endpoint",
    "json",
    "fetch",
    "undefined",
    "api/",
]


def leer(nombre: str) -> str:
    return (NUEVO / nombre).read_text(encoding="utf-8")


def bloque_de_textos() -> str:
    """El trozo de `modelo.js` donde viven los textos que lee el agricultor."""
    fuente = leer("modelo.js")
    encontrado = re.search(r"export const textos = \{([\s\S]*?)\n\};", fuente)
    assert encontrado, "no se encuentra el bloque `textos` en modelo.js"
    return encontrado.group(1)


def sin_tildes(texto: str) -> str:
    import unicodedata

    return "".join(
        letra
        for letra in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(letra) != "Mn"
    )


class TestLosFicherosDeLaInterfazNuevaSeSirven:
    @pytest.mark.parametrize("nombre", FICHEROS_DE_LA_PANTALLA)
    def test_cada_fichero_se_sirve(self, cliente, nombre):
        respuesta = cliente.get(f"/nuevo/{nombre}")
        assert respuesta.status_code == 200, f"/nuevo/{nombre} no se sirve"
        assert len(respuesta.content) > 0

    def test_la_carpeta_sirve_su_portada(self, cliente):
        respuesta = cliente.get("/nuevo/")
        assert respuesta.status_code == 200
        assert "text/html" in respuesta.headers["content-type"]

    def test_el_javascript_se_sirve_como_javascript(self, cliente):
        # En Windows, Python saca el tipo de los `.js` del registro y puede devolver
        # `text/plain`: el navegador entonces no carga el módulo y la pantalla se queda
        # en blanco sin decir por qué.
        for nombre in ["app.js", "modelo.js"]:
            respuesta = cliente.get(f"/nuevo/{nombre}")
            assert "javascript" in respuesta.headers["content-type"], nombre

    def test_la_hoja_de_estilos_se_sirve_como_css(self, cliente):
        respuesta = cliente.get("/nuevo/estilos.css")
        assert respuesta.status_code == 200
        assert "text/css" in respuesta.headers["content-type"]

    def test_la_portada_carga_los_vendor_y_su_modulo(self, cliente):
        html = cliente.get("/nuevo/").text
        for ruta in [
            "/vendor/react.production.min.js",
            "/vendor/react-dom.production.min.js",
            "/vendor/htm.umd.js",
        ]:
            assert ruta in html, f"la portada no carga {ruta}"
        assert re.search(r'<script[^>]+type="module"[^>]+src="/nuevo/app\.js"', html)
        assert "/nuevo/estilos.css" in html


class TestLaAplicacionDeSiempreSigueViva:
    """La nueva se sirve aparte: si esto se rompe, el agricultor se queda sin nada."""

    def test_la_portada_de_siempre_sigue_en_la_raiz(self, cliente):
        respuesta = cliente.get("/")
        assert respuesta.status_code == 200
        assert "text/html" in respuesta.headers["content-type"]
        assert "CUE Digital" in respuesta.text

    def test_los_ficheros_de_siempre_siguen_sirviendose(self, cliente):
        for nombre in ["app.js", "estilos.css", "nucleo.js"]:
            respuesta = cliente.get(f"/{nombre}")
            assert respuesta.status_code == 200, nombre


class TestLoQueLeeElAgricultor:
    def test_los_textos_no_llevan_jerga(self):
        visible = sin_tildes(bloque_de_textos())
        for palabra in textos.PALABRAS_PROHIBIDAS:
            assert sin_tildes(palabra) not in visible, f"texto con jerga: «{palabra}»"

    def test_los_textos_no_hablan_de_como_esta_hecho(self):
        visible = sin_tildes(bloque_de_textos())
        for palabra in PALABRAS_DE_PROGRAMADOR:
            assert sin_tildes(palabra) not in visible, f"texto técnico: «{palabra}»"

    def test_no_se_escribe_nada_por_la_consola(self):
        for nombre in ["app.js", "modelo.js"]:
            fuente = leer(nombre)
            assert "console." not in fuente, f"{nombre} escribe en la consola"


class TestElContratoConElArnesDeNavegador:
    def test_estan_todos_los_enganches(self):
        fuente = leer("app.js")
        faltan = [enganche for enganche in ENGANCHES if enganche not in fuente]
        assert not faltan, f"faltan enganches en app.js: {faltan}"

    def test_el_estado_se_pinta_en_la_raiz_con_sus_cinco_valores(self):
        # Los nombres de los estados viven en el modelo y los pinta la aplicación.
        fuente = leer("app.js") + leer("modelo.js")
        for valor in ["cargando", "error", "vacio", "sin-permiso", "listo"]:
            assert f'"{valor}"' in fuente, f"falta el estado «{valor}»"

    def test_los_cinco_destinos_del_movil_estan(self):
        fuente = leer("app.js")
        for destino in ["hoy", "tierras", "apuntar", "calendario", "mas"]:
            assert f'"{destino}"' in fuente, f"falta el destino «{destino}»"
        # El cuaderno sigue teniendo su sitio en el lateral de la tableta y del ordenador.
        assert 'data-destino="cuaderno"' in fuente

    def test_la_vista_de_anadir_tierras_esta(self):
        fuente = leer("app.js")
        assert '"alta"' in fuente, "falta la vista de añadir tierras"
        assert 'data-vista=${vista}' in fuente

    def test_las_vistas_de_la_tierra_el_calendario_los_trabajos_y_las_facturas_estan(self):
        fuente = leer("app.js")
        for vista in ["tierra", "calendario", "trabajos", "facturas", "mas"]:
            assert f'"{vista}"' in fuente, f"falta la vista «{vista}»"
        assert "VistaTierra" in fuente
        assert "VistaCalendario" in fuente
        assert "VistaTrabajos" in fuente
        assert "VistaFacturas" in fuente

    def test_las_puertas_que_usa_la_pantalla_son_las_del_servidor(self):
        fuente = leer("app.js")
        faltan = [puerta for puerta in PUERTAS if puerta not in fuente]
        assert not faltan, f"la pantalla llama a puertas que no son las del contrato: {faltan}"


class TestLaPantallaNoSeCompila:
    def test_no_hay_paso_de_compilacion(self):
        # La interfaz son ficheros servidos tal cual: sin JSX, sin importar nada de npm y
        # sin transpilar. En el servidor donde se instala no hay Node.
        fuente = leer("app.js")
        assert "require(" not in fuente.split("\n")[0]
        assert "import React" not in fuente
        html = leer("index.html")
        assert "babel" not in html.lower()
        assert "JSX" not in html
