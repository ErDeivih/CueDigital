"""La comprobación en un navegador de verdad: que el guion esté y que no deje basura.

`scripts/comprobar_en_un_navegador.py` abre Chrome (o Edge) sin ventana, entra con una cuenta de
prueba y comprueba que la pantalla de inicio **la dibuja React de verdad** en un navegador. Es lo
único que no se puede probar de ninguna otra forma: los tests dibujan los componentes con
`renderToStaticMarkup` (sin navegador) o con un DOM de mentira, y ahí `ReactDOM.createRoot` no existe.

Estos tests **no abren ningún navegador**: eso es una comprobación a mano, como `humo.py`. Lo que
comprueban es lo que sí se puede comprobar sin navegador:

1. Que el guion está y se puede leer (que no se ha quedado a medias).
2. Que dice que hace falta un servidor y que sin navegador **no falla** (es una comprobación de más,
   no un requisito).
3. **Que no deja ficheros dentro de la aplicación.** La página que usa para entrar con sesión se
   escribe dentro de `backend/web/` (tiene que servirse desde el propio programa: un módulo de otro
   origen no carga) y se borra al terminar. Si un día se quedara ahí, sería un fichero de más en la
   aplicación, y esto lo avisa.
"""

from __future__ import annotations

import pathlib

from scripts import comprobar_en_un_navegador as comprobar

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"


class TestElGuion:
    def test_el_guion_esta_y_se_lee(self):
        assert comprobar.__doc__, "el guion no explica para qué sirve"
        assert comprobar.NAVEGADORES, "no sabe qué navegadores buscar"
        # Por defecto apunta al servidor de pruebas (8010) y se le puede pasar otra dirección.
        assert comprobar.DIRECCION_POR_DEFECTO.startswith("http"), "no dice dónde está el servidor"
        fuente = pathlib.Path(comprobar.__file__).read_text(encoding="utf-8")
        assert "add_argument(\"direccion\"" in fuente, "no deja pasarle la dirección del servidor"
        # **La dirección se lee dentro de `main()`, no al importar el módulo.** Se hacía al importar y
        # el test lo cazó: al importarlo desde pytest, `sys.argv` es el de pytest, y el guion creía
        # que el servidor estaba en la ruta de un fichero de tests y fallaba sin motivo.
        assert "sys.argv[1]" not in fuente, "la dirección se sigue leyendo al importar el módulo"

    def test_busca_navegadores_instalados(self):
        """Sin navegador no se puede comprobar, y el guion tiene que decirlo, no reventar."""
        assert any("chrome.exe" in ruta or "msedge.exe" in ruta for ruta in comprobar.NAVEGADORES)
        # `navegador()` devuelve la ruta o `None`: las dos cosas valen (en este PC, una ruta).
        encontrado = comprobar.navegador()
        assert encontrado is None or pathlib.Path(encontrado).exists()

    def test_la_pagina_de_la_comprobacion_lleva_el_viewport(self):
        """Sin `viewport`, el navegador dibuja la página como si fuera ancha y la captura sale
        recortada. Pasó, y me hizo buscar un fallo de anchura que no existía."""
        guion = pathlib.Path(comprobar.__file__).read_text(encoding="utf-8")
        assert 'name="viewport"' in guion, "la página de la comprobación no lleva el viewport"
        assert "width=device-width" in guion

    def test_un_paso_de_la_ruta_que_no_encuentra_su_boton_lo_dice(self):
        """**Esto faltaba, y hacía que la comprobación diera por buena otra pantalla.**

        Cada pantalla se comprueba recorriendo una ruta de botones. Si un selector no existe, el
        navegador no pulsa nada y la comprobación se queda en la pantalla de antes; si los textos que
        busca también están ahí, **pasa sin haber visto la pantalla que decía comprobar**. Pasó el
        27/09/2026 con «el plan de abono», que se quedó en «mi cuaderno» y aun así «pasó».

        Ahora la página apunta en su título lo que no encontró y el guion lo lee y falla. Aquí se
        comprueba que las dos mitades están: la que lo apunta y la que lo lee.
        """
        guion = pathlib.Path(comprobar.__file__).read_text(encoding="utf-8")
        assert "window.pasosSinEncontrar" in guion, "la página ya no apunta los pasos que no encuentra"
        assert "SIN-ENCONTRAR" in guion, "la página ya no deja la señal donde el guion la lee"
        assert "_pasos_sin_encontrar" in guion, "el guion ya no lee los pasos que no se encontraron"

    def test_el_lector_de_los_pasos_perdidos_lee_lo_que_escribe_la_pagina(self):
        """La señal se lee de verdad: se prueba el lector con un HTML como el que vuelca el navegador."""
        html = "<html><head><title>SIN-ENCONTRAR: [data-accion=\"plan-ver\"] | escribir:#papel-titulo</title></head></html>"
        perdidos = comprobar._pasos_sin_encontrar(html)
        assert perdidos == ['[data-accion="plan-ver"]', "escribir:#papel-titulo"]
        # Y si no hay nada perdido, no se inventa nada.
        assert comprobar._pasos_sin_encontrar("<html><title>Comprobación en navegador</title></html>") == []


class TestElHuecoDelAsistente:
    """El asistente monta sus pasos en un **hueco** (`#formulario`), no en la pantalla entera.

    La interfaz vieja pinta la pregunta y deja ese hueco vacío; después React lo llena con la pieza del
    paso (la lista de tierras, el resumen…). Si React no llega a montar —un fichero de `web/react/` que
    no ha llegado, la caché de un móvil a medias tras un despliegue— el agricultor ve la pregunta y
    **nada que contestar**. Eso **solo** se ve en un navegador de verdad: en los tests no hay ReactDOM.
    """

    def test_se_comprueba_que_el_hueco_no_se_queda_vacio(self):
        fuente = pathlib.Path(comprobar.__file__).read_text(encoding="utf-8")
        assert comprobar.FORMULARIO_CON_PIEZA, (
            "ningún paso del asistente se comprueba en un navegador: es lo que más se usa del programa "
            "y su hueco es lo único que no se puede probar de otra forma"
        )
        assert "FORMULARIO_CON_PIEZA" in fuente and "_formulario_vacio" in fuente, (
            "el guion ya no comprueba que el hueco del asistente se llene"
        )

    def test_el_lector_del_hueco_ve_lo_que_dibuja_react(self):
        """El lector se prueba con los dos HTML que de verdad salen de un navegador."""
        vacio = (
            '<div class="pasos"></div><p class="pregunta">¿Dónde?</p>'
            '<div id="formulario"></div><div class="barra-acciones"></div>'
        )
        assert comprobar._formulario_vacio(vacio) is True, "no ve el hueco vacío"

        # El caso que de verdad importa: React ha montado dentro (el resumen, que lleva `<div>` dentro:
        # por eso se mira el hueco **vacío** y no el contenido hasta el primer `</div>`).
        lleno = (
            '<p class="pregunta">Mira si está bien</p><div id="formulario">'
            '<dl><div class="resumen-dato"><dt>¿Dónde?</dt><dd>El Prado</dd></div></dl>'
            "</div>"
        )
        assert comprobar._formulario_vacio(lleno) is False, "dice que está vacío y tiene el resumen"
        # Y una pantalla sin asistente (sin ese hueco) no cuenta como vacía: no hay nada que llenar.
        assert comprobar._formulario_vacio('<div id="pantalla"></div>') is False

    def test_las_rutas_del_asistente_llegan_hasta_el_resumen(self):
        """Y la ruta tiene que estar de verdad en la lista: si no, esto no comprueba nada."""
        nombres = [nombre for nombre, _ruta, _esperadas in comprobar.PANTALLAS]
        for nombre in comprobar.FORMULARIO_CON_PIEZA:
            assert nombre in nombres, f"«{nombre}» no está en las pantallas que se recorren"


class TestNoDejaNadaDentro:
    def test_la_pagina_de_la_comprobacion_no_se_queda_en_la_aplicacion(self):
        """El fichero que se escribe dentro de `web/` se borra al terminar: aquí se comprueba que no
        se ha quedado ninguno de una ejecución anterior o interrumpida."""
        assert not (WEB / "_comprobacion_navegador.html").exists(), (
            "ha quedado la página de la comprobación dentro de la aplicación: bórrala "
            "(el guion la borra al terminar, así que esto quiere decir que se interrumpió)"
        )

    def test_la_pagina_se_escribe_dentro_de_la_aplicacion(self):
        """Y se escribe ahí **a propósito**: un módulo de otro origen no carga (hace falta CORS, que
        el programa no pone porque no lo necesita), así que la comprobación tiene que servirse desde
        el propio programa."""
        fuente = pathlib.Path(comprobar.__file__).read_text(encoding="utf-8")
        assert '"web" / "_comprobacion_navegador.html"' in fuente
        assert "unlink(missing_ok=True)" in fuente, "no borra la página al terminar"
