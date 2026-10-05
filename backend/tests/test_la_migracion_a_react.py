"""La migración a React: que el código, la documentación y la caché digan lo mismo.

Esto existe por un motivo concreto y ya conocido en este proyecto: **una lista escrita a mano se
queda vieja y nadie se entera**. Aquí hay tres sitios que hablan de lo mismo:

1. **El código** (`backend/web/app.js`): la lista `PANTALLAS_EN_REACT` dice qué pantallas se piden a
   React. Si una pantalla no está ahí y se monta con React igual, el siguiente que la mire no lo sabrá.
2. **La documentación** (`docs/REACT.md`): una tabla con las pantallas migradas y las que no. Si se
   queda atrás, alguien migra una pantalla que ya estaba migrada, o da por hecha una que no lo está.
3. **La caché del campo** (`backend/web/service-worker.js`): los ficheros de cada pantalla migrada
   tienen que estar en la lista de lo que se guarda para abrir la aplicación **sin cobertura**. Si
   falta uno, un agricultor que abra la aplicación en el campo se queda con la pantalla en blanco, y
   eso es lo peor que puede pasar aquí.

Además, cada pantalla de la lista tiene que tener su **fichero de verdad** en `backend/web/react/`.

Y esto no es una precaución teórica: la aplicación ya se quedó una vez con una pantalla que no
abría por un fichero que no estaba donde tenía que estar.
"""

from __future__ import annotations

import json
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "web" / "app.js"
REACT = RAIZ / "backend" / "web" / "react"
SERVICIO = RAIZ / "backend" / "web" / "service-worker.js"
GUIA = RAIZ / "docs" / "REACT.md"


def _migradas_en_el_codigo() -> set[str]:
    """Las pantallas que el código dice que están en React."""
    texto = APP.read_text(encoding="utf-8")
    encontrado = re.search(r"const PANTALLAS_EN_REACT = new Set\(\[(.*?)\]\)", texto, re.S)
    assert encontrado, "no encuentro `PANTALLAS_EN_REACT` en `app.js`"
    return set(re.findall(r'"([a-z_]+)"', encontrado.group(1)))


def _ficheros_de_react() -> set[str]:
    """Las pantallas que tienen su fichero dentro de `web/react/pantallas/`."""
    return {ruta.stem for ruta in (REACT / "pantallas").glob("*.js")}


def _en_la_guia() -> set[str]:
    """Las pantallas que `docs/REACT.md` marca como migradas, con el nombre de su fichero.

    Se leen de la tabla: cada fila que dice «✅ En React» y nombra un `pantallas/<nombre>.js`.
    """
    texto = GUIA.read_text(encoding="utf-8")
    return set(re.findall(r"pantallas/([a-z_]+)\.js`\) \| ✅ En React", texto))


def _en_la_cache() -> set[str]:
    """Las pantallas cuyos ficheros se guardan para abrir la aplicación sin cobertura."""
    texto = SERVICIO.read_text(encoding="utf-8")
    return set(re.findall(r'"/react/pantallas/([a-z_]+)\.js"', texto))


def quita_comentarios(codigo: str) -> str:
    """El código sin comentarios, para que una prueba no se crea lo que dice un comentario.

    Hace falta de verdad: en `app.js` hay comentarios que hablan de `pintar()` y de `innerHTML`
    explicando lo que se borró, y una prueba que buscara esas palabras en el texto entero se creería que
    siguen ahí.
    """
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return re.sub(r"(?m)//.*$", "", codigo)


class TestLasTresListasDicenLoMismo:
    def test_el_codigo_y_los_ficheros_cuadran(self):
        """Cada pantalla que el código dice que está en React tiene su fichero, y al revés."""
        en_el_codigo = _migradas_en_el_codigo()
        ficheros = _ficheros_de_react()

        sin_fichero = en_el_codigo - ficheros
        assert sin_fichero == set(), (
            f"el código dice que están en React y no tienen fichero: {sorted(sin_fichero)}"
        )
        sueltos = ficheros - en_el_codigo
        assert sueltos == set(), (
            f"hay ficheros de pantalla que no están en `PANTALLAS_EN_REACT`: {sorted(sueltos)}. "
            "Si una pantalla se migró, se apunta ahí; si no, sobra el fichero."
        )

    def test_la_documentacion_dice_lo_mismo_que_el_codigo(self):
        """La tabla de `docs/REACT.md` no puede quedarse atrás: es la guía del siguiente que llegue."""
        en_el_codigo = _migradas_en_el_codigo()
        en_la_guia = _en_la_guia()

        faltan_en_la_guia = en_el_codigo - en_la_guia
        assert faltan_en_la_guia == set(), (
            f"estas pantallas están en React y la guía no las marca como migradas: "
            f"{sorted(faltan_en_la_guia)}"
        )
        de_mas = en_la_guia - en_el_codigo
        assert de_mas == set(), (
            f"la guía dice que están migradas y el código no las tiene: {sorted(de_mas)}"
        )

    def test_lo_migrado_se_guarda_para_abrir_sin_cobertura(self):
        """**El fallo que esto evita es el peor de todos:** una pantalla que no abre en el campo."""
        en_el_codigo = _migradas_en_el_codigo()
        en_la_cache = _en_la_cache()
        faltan = en_el_codigo - en_la_cache
        assert faltan == set(), (
            f"estas pantallas están en React y NO se guardan para abrir sin cobertura: "
            f"{sorted(faltan)}. Añádelas a `FICHEROS` del service-worker (y sube el número de la "
            "caché en el mismo cambio)."
        )

    def test_la_guia_dice_en_que_punto_esta_la_migracion(self):
        """Y la guía tiene que decir **el estado**, no solo llevar la tabla.

        Hasta la ronda 72 esta prueba exigía que la guía llevara la cuenta de «van N y quedan M». Ahora
        quedan cero, así que lo que se comprueba es que lo diga: si alguien vuelve a dejar una pantalla sin
        migrar, la frase «la migración está terminada» se queda mintiendo y hay que releerla.
        """
        texto = GUIA.read_text(encoding="utf-8")
        assert "La migración está terminada" in texto, "la guía no dice en qué punto está la migración"
        assert _migradas_en_el_codigo(), "no hay ninguna pantalla migrada: algo se ha perdido"
        assert "✅ En React" in texto, "la guía no tiene la tabla de pantallas"
        # El número, escrito con letra, y **se mueve cada vez que se añade una pantalla**: era
        # «veintisiete» hasta la ronda 88 y es «veintiocho» desde que entró «quién entra en mi finca»
        # (ronda 89). Si un día esta prueba se pone roja por esto, lo que hay que hacer es contar las
        # pantallas de la tabla y poner el número nuevo **en la guía**, no quitar la comprobación: es la
        # que impide que la guía se quede mintiendo sobre cuánto queda migrado.
        assert "veintiocho" in texto, "la guía no dice cuántas pantallas están migradas"


class TestLoQueQuedaDeLaInterfazVieja:
    """**La migración está terminada, y esto es lo que lo mantiene terminado.**

    Hasta la ronda 72 quedaban dos cosas de la interfaz vieja: los pasos del asistente con `pintar` (que
    devolvían HTML) y la propia función `pintar()`, que era el único `innerHTML` de la aplicación. Las dos
    se borraron. Estas pruebas existen porque **volver atrás es muy fácil y no se nota**: alguien añade un
    paso con `pintar:` copiando un paso viejo de otro sitio, o alguien vuelve a pintar una pantalla con
    `innerHTML` «solo para esta vez», y la aplicación sigue funcionando… hasta que algo se cuela por el
    `innerHTML` y nadie lo ve.
    """

    def test_ningun_paso_del_asistente_pinta_html(self):
        """Los pasos se piden a React (`montar`): ni un `pintar:` en las definiciones de pasos.

        Un paso que traiga `pintar` en vez de `montar` **no pintaría nada**: el envoltorio del asistente
        solo sabe pintar el elemento que le da `montar`. El agricultor vería la pregunta y, debajo, nada.
        """
        lineas_pintar = [
            (numero, linea.strip())
            for numero, linea in enumerate(APP.read_text(encoding="utf-8").splitlines(), 1)
            if re.match(r"^\s+pintar:", linea)
        ]
        assert lineas_pintar == [], (
            "hay pasos del asistente que devuelven HTML (`pintar:`) en vez de un elemento de React "
            f"(`montar:`): {lineas_pintar}. Ese paso saldría en blanco."
        )

    def test_los_pasos_que_hay_son_todos_de_react(self):
        """Y que la cuenta no se quede a cero por el camino: los pasos siguen ahí, con `montar`."""
        texto = APP.read_text(encoding="utf-8")
        cuantos = len(re.findall(r"^\s+montar:", texto, re.M))
        assert cuantos >= 65, f"quedan {cuantos} pasos con `montar` y eran 65"

    def test_no_queda_ni_un_innerhtml_de_pantallas(self):
        """`pintar()` (que hacía `pantalla.innerHTML = …`) se borró: ya no hay dos interfaces.

        Se dejan fuera, con su motivo, los dos `innerHTML` que **no** son pantallas: el aviso de
        emergencia de `montar.js` (que se escribe a mano justo cuando React no ha cargado) y el aviso de
        apuntes pendientes de la cabecera (un trozo de la cabecera, no una pantalla).
        """
        codigo = quita_comentarios(APP.read_text(encoding="utf-8"))
        assert "function pintar(" not in codigo, "ha vuelto la función `pintar()`"
        usos = [
            linea.strip()
            for linea in codigo.splitlines()
            if "innerHTML" in linea and "avisoPendientes" not in linea
        ]
        assert usos == [], f"app.js vuelve a montar HTML a mano: {usos}"


class TestLoQueSeSirve:
    def test_todo_el_javascript_de_react_se_guarda_para_el_campo(self):
        """**Cada fichero de `web/react/` tiene que estar en la caché**, no solo las pantallas.

        Esto se añadió al meter la primera **pieza** (`react/piezas/resumen_del_apunte.js`, el resumen
        del asistente): un componente que no está en la caché es un hueco en el campo. El agricultor
        abre esa pantalla sin cobertura y se encuentra con que no se dibuja, y eso es lo peor que
        puede pasar aquí.
        """
        en_la_cache = {
            "/" + ruta.relative_to(RAIZ / "backend" / "web").as_posix()
            for ruta in (REACT).rglob("*.js")
        }
        guardados = set(re.findall(r'"([^"]+\.js)"', SERVICIO.read_text(encoding="utf-8")))
        faltan = sorted(en_la_cache - guardados)
        assert faltan == [], (
            f"estos ficheros de React NO se guardan para abrir sin cobertura: {faltan}. "
            "Añádelos a `FICHEROS` del service-worker (y sube el número de la caché)."
        )

    def test_cada_pantalla_migrada_se_sirve_como_javascript(self, cliente):
        """Servida por el programa y con el tipo correcto: si sale como texto, el navegador no la usa.

        El tipo importa de verdad: en Windows, Python saca el tipo de los ficheros del registro, y un
        `.js` servido como `text/plain` hace que el navegador rechace el módulo **sin decir por qué**.
        """
        for pantalla in sorted(_migradas_en_el_codigo()):
            respuesta = cliente.get(f"/react/pantallas/{pantalla}.js")
            assert respuesta.status_code == 200, f"no se sirve /react/pantallas/{pantalla}.js"
            assert "javascript" in respuesta.headers.get("content-type", ""), (
                f"/react/pantallas/{pantalla}.js no se sirve como JavaScript"
            )

    def test_los_componentes_compartidos_se_sirven(self, cliente):
        for fichero in ("componentes.js", "montar.js"):
            respuesta = cliente.get(f"/react/{fichero}")
            assert respuesta.status_code == 200, f"no se sirve /react/{fichero}"
            assert "javascript" in respuesta.headers.get("content-type", "")

    def test_la_pagina_carga_react_antes_que_la_aplicacion(self, cliente):
        """El orden importa: los ficheros de `vendor/` tienen que dejar `React` y `htm` puestos
        **antes** de que arranque `app.js`, o la primera pantalla no se puede dibujar."""
        html = cliente.get("/").text
        posicion_react = html.find("/vendor/react.production.min.js")
        posicion_app = html.find("/app.js")
        assert posicion_react > 0 and posicion_app > 0, "falta React o falta la aplicación"
        assert posicion_react < posicion_app, "la aplicación se carga antes que React"
        assert html.find("/vendor/htm.umd.js") < posicion_app, "falta `htm` o va después"


class TestElInventarioDeLoQueFalta:
    def test_la_guia_dice_como_se_añade_una_pantalla(self):
        """Lo que hace que esto se pueda seguir haciendo sin volver a pensarlo todo."""
        texto = GUIA.read_text(encoding="utf-8")
        for pieza in (
            "Cómo se añade una pantalla nueva",
            "PANTALLAS_EN_REACT",
            "renderToStaticMarkup",
            "comprobar_en_un_navegador",
        ):
            assert pieza in texto, f"a la guía le falta hablar de «{pieza}»"

    def test_la_guia_lleva_la_lista_de_lo_que_no_esta_resuelto(self):
        """Y lo que falta, dicho: si no, el siguiente cree que está todo hecho."""
        texto = GUIA.read_text(encoding="utf-8")
        assert "NO está resuelto" in texto
        # Las tres cosas que siguen pendientes y que no son «migrar más pantallas».
        for pendiente in ("jsdom", "React 18", "certificado"):
            assert pendiente.lower() in texto.lower(), f"la guía no habla de «{pendiente}»"

    def test_el_informe_de_la_migracion_se_puede_contar(self):
        """Un resumen en cifras, para poder decir «van N pantallas» sin contarlas a mano."""
        resumen = {
            "migradas": len(_migradas_en_el_codigo()),
            "con_fichero": len(_ficheros_de_react()),
            "en_la_guia": len(_en_la_guia()),
            "en_la_cache": len(_en_la_cache()),
        }
        assert len(set(resumen.values())) == 1, f"las cuentas no cuadran: {json.dumps(resumen)}"
        assert resumen["migradas"] >= 11, "se han perdido pantallas migradas por el camino"
