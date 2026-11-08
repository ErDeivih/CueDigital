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
    "data-apuntar-tierra",
    "data-apuntar-tab",
    "data-apuntar-producto",
    "data-apuntar-fertilizante",
    "data-apuntar-semilla",
    "data-apuntar-dosis",
    "data-apuntar-justificacion",
    "data-apuntar-total",
    "data-apuntar-apero",
    "data-apuntar-fecha",
    "data-apuntar-hectareas",
    "data-apuntar-nota",
    "data-apuntar-guardar",
    "data-apuntar-resultado",
    "data-miniatura-tierra",
    "data-guardar-imagen-tierra",
    "data-que-falta-seccion",
    "data-que-falta-item",
    "data-que-falta-cuenta",
    "data-producto-tab",
    "data-producto-id",
    "data-fertilizante-id",
    "data-producto-buscar",
    "data-aplicar-producto",
    "data-aplicar-tierra",
    "data-aplicar-fecha",
    "data-aplicar-dosis",
    "data-aplicar-hectareas",
    "data-aplicar-total",
    "data-aplicar-guardar",
    "data-aplicar-resultado",
    "data-siguiente-paso",
    "data-historial-comparativa",
    "data-historial-fila-anio",
    "data-dia-total",
    "data-calendario-totales",
    "data-filtro-tierra",
    "data-filtro-desde",
    "data-filtro-hasta",
    "data-resumen-tipo",
    "data-descargar-trabajos",
    "data-sigpac-dibujo-recinto",
    "data-cuaderno-aviso",
    "data-cuaderno-primero",
    "data-cuaderno-primero-donde",
    "data-que-falta-seccion-bloquea",
    "data-sigpac-cache-actualizadas",
    "data-sigpac-cache-actualizada",
    "data-cuaderno-aviso-cuenta",
    "data-que-falta-item-bloquea",
    "data-cuaderno-rellenables",
    "data-cuaderno-resumen",
    "data-que-falta-seccion-cuenta",
    "data-cuaderno-empezar",
    "data-sigpac-autobusqueda",
    "data-sigpac-cache",
    "data-sigpac-cache-provincia",
    "data-sigpac-cache-aplicar",
    "data-sigpac-cache-resultado",
    "data-sigpac-cache-atribucion",
    "data-ventana-sigpac",
    "data-ventana-cerrar",
    "data-abrir-ventana-sigpac",
    "data-abrir-ventana-sigpac-tierra",
    "data-sigpac-buscar-referencia",
    "data-sigpac-buscar-municipio",
    "data-sigpac-municipio-opcion",
    "data-sigpac-poligono",
    "data-sigpac-parcela",
    "data-sigpac-buscar",
    "data-sigpac-recinto-id",
    "data-sigpac-usar",
    "data-sigpac-resultado",
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
    "/api/labores",
    "/api/trabajos/opciones",
    "/api/trabajos/que-falta",
    "/api/productos",
    "/api/fertilizantes",
    "/api/semillas",
    "/api/siembras",
    "/api/tratamientos",
    "/api/fertilizaciones",
    "/api/municipios",
    "/contorno",
    "/api/sigpac/buscar",
    "/api/sigpac/cache",
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

    def test_la_vista_de_apuntar_esta_y_tiene_sus_enganches(self):
        fuente = leer("app.js")
        assert "VistaApuntar" in fuente
        assert '"apuntar"' in fuente
        # El apero se manda por la puerta de siempre y, si esa no lo conoce, por la de trabajos:
        # mandarlo por una que lo ignora lo perdería sin decir nada.
        assert "cuerpoDelApunte" in fuente
        assert "elAperoSeGuardaEnLabores" in fuente
        assert "/api/labores" in fuente
        # La miniatura del contorno en las listas y el guardar la imagen en la ficha.
        assert "Miniatura" in fuente
        assert "urlDeMiniatura" in fuente

    def test_apuntar_tiene_las_cuatro_pestanas_del_dia_a_dia(self):
        fuente = leer("app.js")
        modelo = leer("modelo.js")
        for pestana in ("labor", "tratamiento", "abono", "siembra"):
            assert f'clave: "{pestana}"' in fuente, f"falta la pestaña «{pestana}» en la vista de apuntar"
            assert f'data-apuntar-tab=${{una.clave}}' in fuente
        # Los cuerpos de las puertas nuevas viven en el modelo, y el abono tiene sus dos modos.
        for funcion in ("cuerpoDeLaSiembra", "cuerpoDeLaSiembraDelCuaderno", "cuerpoDelAbono", "normalizaSemillas"):
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"
        assert "modo =" in modelo
        # El total se calcula con dosis × hectáreas y los avisos del servidor se enseñan tal cual.
        assert "totalDeLaAplicacion" in fuente
        assert "mensajesDeLaRespuesta" in fuente
        # Sin semillas dadas de alta se ofrece la siembra del cuaderno, sin inventar ninguna.
        assert "textos.apuntar.siembra.sinSemillas" in fuente
        assert "textos.apuntar.siembra.delCuaderno" in fuente
        assert "siembraDelCuaderno" in fuente
        # Las cuatro pestañas llevan su texto en el modelo.
        for clave in ("pestanas", "producto", "abono", "siembra"):
            assert clave in modelo

    def test_el_cuaderno_guiado_y_los_productos_estan(self):
        fuente = leer("app.js")
        assert "VistaCuaderno" in fuente
        assert "VistaProductos" in fuente
        assert '"cuaderno"' in fuente
        assert '"productos"' in fuente
        # Lo que falta se agrupa y se puede agrupar de verdad, y el total sale de dosis × hectáreas.
        assert "agruparLoQueFalta" in fuente
        assert "totalDeLaAplicacion" in fuente
        assert "cuerpoDelTratamiento" in fuente
        assert "cuerpoDeLaFertilizacion" in fuente
        assert "rutaDeLaAplicacion" in fuente
        # El flujo encadenado: siempre hay un siguiente paso a la vista.
        assert "BotonSiguiente" in fuente
        assert "data-siguiente-paso" in fuente

    def test_la_ventana_aprovecha_la_tierra_y_el_cuaderno_cuenta_las_rellenables(self):
        fuente = leer("app.js")
        modelo = leer("modelo.js")
        # Desde la ficha, la ventana pregunta por la parcela para tener sus códigos y busca sola una vez.
        assert "RUTA_PARCELA" in fuente
        assert "/api/parcelas/" in fuente
        assert "data-sigpac-autobusqueda" in fuente
        assert "claveBuscada" in fuente
        assert "claveDeApertura" in fuente
        for funcion in ("camposInicialesDelSigpac", "faltasRellenables", "textoDeLasRellenables"):
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"
        # La línea nueva del cuaderno usa la misma función de destinos.
        assert "data-cuaderno-rellenables" in fuente
        assert "faltasRellenables(items)" in fuente
        assert "textos.cuaderno.rellenablesVarias" in modelo
        # Los inputs de la ventana siguen.
        for enganche in ("data-sigpac-buscar-referencia", "data-sigpac-poligono", "data-sigpac-parcela"):
            assert enganche in fuente

    def test_el_cuaderno_dice_lo_primero_y_el_sigpac_lista_las_tierras(self):
        fuente = leer("app.js")
        modelo = leer("modelo.js")
        # El aviso dice lo primero que el agricultor PUEDE rellenar y dónde; lo que depende de
        # la aplicación o de la Junta se dice aparte, sin mandarlo a la app vieja a arreglarlo.
        assert "data-cuaderno-primero" in fuente
        assert "data-cuaderno-primero-donde" in fuente
        assert "data-cuaderno-bloqueo-tecnico" in fuente
        assert "data-que-falta-seccion-bloquea" in fuente
        assert "data-que-falta-seccion-destino" in fuente
        for funcion in ("primerBloqueoDeLoQueFalta", "actualizadasDeLosContornos"):
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"
        # Las secciones que se pueden rellenar van antes (orden estable) y dentro sigue lo bloqueante.
        assert "ordenaLoQueFalta" in modelo
        # La lista de tierras actualizadas solo se pinta si el servidor trae alguna.
        assert "data-sigpac-cache-actualizadas" in fuente
        assert "data-sigpac-cache-actualizada" in fuente
        assert "textos.ventana.cache.tierrasActualizadas" in fuente
        assert "textos.ventana.cache.tierraSinNombre" in modelo

    def test_el_cuaderno_avisa_de_lo_que_bloquea(self):
        fuente = leer("app.js")
        modelo = leer("modelo.js")
        # El aviso va arriba, cuenta los bloqueos y ofrece seguir con lo que el agricultor puede
        # rellenar; lo técnico se dice con su responsable, no con un botón que no arregla nada.
        assert "data-cuaderno-aviso" in fuente
        assert "data-cuaderno-aviso-cuenta" in fuente
        assert "data-cuaderno-empezar" in fuente
        assert "textos.cuaderno.empezarPorElCuaderno" in fuente
        assert "textos.cuaderno.loPrimeroRellenable" in fuente
        assert "textos.cuaderno.bloqueoTecnico" in fuente
        # Cada fila dice si bloquea, para que el arnés lo pueda mirar.
        assert "data-que-falta-item-bloquea" in fuente
        # Lo que bloquea va primero dentro de su sección y el aviso se cuenta en singular y plural.
        for funcion in (
            "ordenaLoQueFalta",
            "textoDelAvisoDeBloqueo",
            "textoDeFaltasSinListar",
            "primerBloqueoDeLoQueFalta",
            "empezarPorLoPrimero",
        ):
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"
        # Si el servidor cuenta más de las que se ven, se dice sin inventar.
        assert "textos.cuaderno.noSeVenTodas" in modelo
        # Y el CSS del aviso no usa colores sueltos ni transparencias.
        css = leer("estilos.css")
        assert ".cuaderno__aviso" in css
        assert "var(--warning-tint)" in css

    def test_el_mapa_del_sigpac_se_toca_y_el_cuaderno_guia(self):
        fuente = leer("app.js")
        modelo = leer("modelo.js")
        css = leer("estilos.css")
        # Cada recinto dibujado es un botón: se toca, se enfoca y se elige con Enter y Espacio.
        assert "data-sigpac-dibujo-recinto" in fuente
        assert 'role="button"' in fuente
        assert 'tabIndex="0"' in fuente
        assert "aria-pressed" in fuente
        assert "onKeyDown" in fuente
        assert "mapa__anillo--toque" in fuente
        assert ".mapa__anillo--toque" in css
        assert "stroke-width: 60" in css
        assert "pointer-events: stroke" in css
        # La zona de toque va detrás y el trazo visible no se come los toques de las etiquetas.
        assert "mapa__dibujo text" in css
        # El cuaderno dice cuánto falta, cuánto bloquea, la cuenta de cada sección y por dónde empezar.
        assert "data-cuaderno-resumen" in fuente
        assert "data-cuaderno-empezar" in fuente
        assert "data-que-falta-seccion-cuenta" in fuente
        for funcion in (
            "resumenDeLoQueFalta",
            "empezarPorLoPrimero",
            "cuentaDeUnaSeccion",
            "destinoDeLaSeccion",
            "etiquetaDelRecintoEnElMapa",
        ):
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"
        # Se mantienen los enganches de antes del cuaderno.
        assert "data-que-falta-item" in fuente
        assert "data-que-falta-seccion" in fuente

    def test_la_ventana_tiene_los_contornos_de_toda_la_finca(self):
        fuente = leer("app.js")
        modelo = leer("modelo.js")
        # El bloque y sus cinco enganches.
        for enganche in (
            "data-sigpac-cache",
            "data-sigpac-cache-provincia",
            "data-sigpac-cache-aplicar",
            "data-sigpac-cache-resultado",
            "data-sigpac-cache-atribucion",
        ):
            assert enganche in fuente, f"falta el enganche «{enganche}»"
        # Las dos puertas que ya tenía el servidor y que ahora tienen pantalla.
        assert "RUTA_CACHE_SIGPAC" in fuente
        assert "/api/sigpac/cache" in fuente
        assert "pedirConDetalle" in fuente
        # Los cálculos, en el modelo: la caché, la provincia con su validez, la dirección y el
        # resultado en palabras (singular y plural).
        for funcion in (
            "normalizaCacheSigpac",
            "rutaDeLosContornos",
            "lineasDeLosContornos",
            "etiquetaDeProvinciaCache",
            "fechaValidezEnTexto",
        ):
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"
        for clave in ("actualizadas", "no_encontradas", "sin_codigos", "sin_forma"):
            assert clave in modelo
        # Sin mapas guardados se dice, y no hay botón que dispare una descarga de golpe.
        assert "textos.ventana.cache.sinMapas" in fuente
        assert "textos.ventana.cache.sinMapasAyuda" in fuente
        # Los errores se cuentan en palabras de agricultor (404/409), sin el código.
        assert "textos.ventana.cache.noHayMapa" in fuente
        assert "textos.ventana.cache.faltaElFichero" in fuente

    def test_la_ventana_del_sigpac_se_abre_desde_el_alta_y_desde_la_tierra(self):
        fuente = leer("app.js")
        assert "VentanaDelSigpac" in fuente
        assert "data-ventana-sigpac" in fuente
        # Las dos formas de buscar y los dos sitios desde los que se abre.
        assert "cuerpoDeBusquedaPorReferencia" in fuente
        assert "cuerpoDeBusquedaPorMunicipio" in fuente
        assert "normalizaMunicipios" in fuente
        assert "data-abrir-ventana-sigpac" in fuente
        assert "data-abrir-ventana-sigpac-tierra" in fuente
        # «Usar esta parcela» en el alta y el contorno en una tierra que ya existe.
        assert "data-sigpac-usar" in fuente
        assert "cuerpoDelContorno" in fuente
        assert "/api/parcelas/desde-sigpac" in fuente
        # Sin forma no se aplica nada: se dice.
        assert "avisoSinForma" in fuente
        # Y se puede cerrar con Escape y con el botón.
        assert 'evento.key === "Escape"' in fuente
        assert "data-ventana-cerrar" in fuente

    def test_las_funciones_de_la_ventana_estan_en_el_modelo(self):
        modelo = leer("modelo.js")
        for funcion in [
            "normalizaMunicipios",
            "cuerpoDeBusquedaPorReferencia",
            "cuerpoDeBusquedaPorMunicipio",
            "recintoElegido",
            "puedeUsarseElRecinto",
            "avisoSinForma",
            "cuerpoDelContorno",
        ]:
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"

    def test_el_movil_tiene_sus_reglas_sin_desbordes_ni_solapes(self):
        css = leer("estilos.css")
        # Ventana del SIGPAC a pantalla completa, con scroll dentro.
        assert "@media (max-width: 700px)" in css
        assert "height: 100dvh" in css
        assert "position: sticky" in css
        assert ".sigpac__resultados .mapa__lienzo" in css
        assert "min-height: 160px" in css
        # La barra inferior fija no tapa el último botón, y cuenta con el área segura del móvil.
        assert "env(safe-area-inset-bottom, 0px)" in css
        assert "padding-bottom: calc(96px + env(safe-area-inset-bottom, 0px))" in css
        # Las tablas anchas se desplazan dentro de su caja, con la primera columna a la vista.
        assert "-webkit-overflow-scrolling: touch" in css
        assert "position: sticky" in css
        # Los filtros se reparten en una columna a 480 y el mapa no se sale por la derecha.
        assert "@media (max-width: 480px)" in css
        assert "grid-template-columns: minmax(0, 1fr)" in css
        assert "min-width: 0" in css

    def test_se_pueden_comparar_anios_y_bajar_lo_filtrado(self):
        fuente = leer("app.js")
        modelo = leer("modelo.js")
        assert "comparativaDeAnios" in fuente
        assert "data-historial-comparativa" in fuente
        assert "totalesDeTrabajos" in fuente
        assert "data-calendario-totales" in fuente
        assert "queryDeTrabajos" in fuente
        assert "csvDeTrabajos" in fuente
        assert "data-descargar-trabajos" in fuente
        # Y las cuentas viven en el modelo, no en la pantalla.
        for funcion in ["comparativaDeAnios", "mesesEnPalabras", "totalesDeTrabajos", "queryDeTrabajos", "csvDeTrabajos"]:
            assert f"export function {funcion}" in modelo, f"falta la función «{funcion}» en el modelo"

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
