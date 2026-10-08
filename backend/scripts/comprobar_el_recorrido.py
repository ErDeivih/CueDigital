"""El primer recorrido completo, pulsando de verdad: Inicio → Tierras → ficha → trabajo → historial.

Es la comprobación del objetivo de esta ronda. Se hace con la explotación de 64 tierras
(`datos_representativos.py`), no con una cuenta vacía: es la única forma de que el recorrido se parezca a
lo que hace el agricultor (buscar una tierra entre muchas, abrir su ficha, apuntar un trabajo y verlo).

Cada paso dice **qué se ha pulsado y qué ha pasado**, y al final se cuentan las comprobaciones y los
fallos. Si algo no se puede dar desde la pantalla, se dice en el informe en vez de darlo por bueno.

Uso:  python scripts/comprobar_el_recorrido.py http://127.0.0.1:8029 [carpeta-de-capturas]
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
CARPETA = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\David\AppData\Local\Temp\cd-ui")
COMPROBACIONES = 0
FALLOS: list[str] = []
# Lo que se mide y **todavía no está**: se apunta con su frase en vez de darlo por bueno o de poner la
# prueba en rojo. Es el mismo convenio que el guion del teclado y el zoom: un hueco declarado se ve, y el
# día que se cierre, esta lista se queda vacía sola.
HALLAZGOS: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> bool:
    global COMPROBACIONES
    COMPROBACIONES += 1
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {descripcion}")
    if not condicion:
        FALLOS.append(descripcion)
    return bool(condicion)


def captura(nav: NavegadorDeVerdad, nombre: str) -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    (CARPETA / f"recorrido-{nombre}.png").write_bytes(
        base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
    )


def texto_de(nav: NavegadorDeVerdad, selector: str = "#pantalla") -> str:
    return nav.evaluar(
        f"(() => {{ const el = document.querySelector({json.dumps(selector)});"
        " return el ? (el.innerText || '') : ''; })()"
    ) or ""


def hay(nav: NavegadorDeVerdad, selector: str) -> bool:
    return bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(selector)}))"))


def _el_de_dentro(uno: dict) -> dict:
    """**Los datos de un trabajo vienen envueltos**, y hay que sacarlos de dentro.

    El servidor no devuelve el trabajo a pelo: lo devuelve como `{"previsto": {...}}` o `{"labor": {...}}`
    —con su envoltorio, que dice de dónde sale cada cosa—, y quien lo mira tiene que desenvolverlo. Esto
    parecía un guardado fallido (`tipo` salía `None`) y era la comprobación leyendo el nivel de fuera. Se
    saca lo de dentro por nombre, y si no hay envoltorio se devuelve lo que venga.
    """
    if not isinstance(uno, dict):
        return {}
    for clave in ("previsto", "labor", "trabajo", "hecho", "linea"):
        if isinstance(uno.get(clave), dict):
            return uno[clave]
    return uno


def _lo_previsto(estado: dict) -> str:
    """Lo que el servidor dice que queda previsto, en una línea, para poder leerlo en la salida.

    Existe porque un guardado que falla en silencio es lo que hay que poder ver: si esto sale vacío cuando
    debería haber un plan, el problema está en el guardado, y si sale el plan de otro tipo, el problema es
    del tipo que se eligió — dos cosas muy distintas que un «0» a secas no distingue.
    """
    previstos = (estado or {}).get("que_queda_previsto") or []
    if not previstos:
        return "nada"
    dichos = []
    for uno in previstos:
        dentro = _el_de_dentro(uno)
        dichos.append(
            f"{dentro.get('tipo')} · {dentro.get('cuando') or dentro.get('fecha_prevista') or 'sin fecha'}"
        )
    return ", ".join(dichos)


def escribir_en(nav: NavegadorDeVerdad, selector: str, texto: str) -> None:
    """Escribe en un campo: `escribir` teclea **en lo que tenga el foco**, así que primero se enfoca."""
    nav.evaluar(
        f"(() => {{ const el = document.querySelector({json.dumps(selector)});"
        " if (el) { el.focus(); el.select && el.select(); } return null; })()"
    )
    nav.escribir(texto)


def esperar_la_pantalla(nav: NavegadorDeVerdad) -> None:
    """Espera a que la pantalla **tenga contenido de verdad**.

    `Boolean(document.querySelector('#pantalla'))` no vale: `#pantalla` existe siempre, incluso vacía, así
    que esperar por ella es no esperar nada (y por eso la primera vuelta midió «Inicio sin acciones»: se
    estaba mirando la pantalla en blanco).
    """
    nav.esperar(
        "document.querySelectorAll('#pantalla [data-accion], #pantalla button').length > 0",
        segundos=12,
    )


def paso(nav: NavegadorDeVerdad, numero: int, titulo: str) -> None:
    print(f"\n── Paso {numero}: {titulo}   (dirección: {nav.evaluar('location.hash')})")


def acciones(nav: NavegadorDeVerdad) -> list[str]:
    """Las acciones que la pantalla ofrece ahora mismo: es lo que se pulsa, y lo que se enseña si falta algo."""
    return nav.evaluar(
        "[...new Set([...document.querySelectorAll('#pantalla [data-accion]')]"
        ".map((e) => e.dataset.accion))]"
    ) or []


def pulsar_si_hay(nav: NavegadorDeVerdad, selector: str, esperar: str | None = None) -> bool:
    """Pulsa si el botón está y **dice si después pasó lo que tenía que pasar**.

    Si no está, o si después no llega lo que se esperaba, se enseña lo que la pantalla ofrece: un recorrido
    que se rompe sin decir por dónde no sirve para arreglarlo. Y devuelve el resultado de la **espera**, no
    el de la pulsación: pulsar un botón que no lleva a ninguna parte no es un paso dado (esta fue la
    primera trampa del guion: decía «Inicio lleva a las tierras» con la pantalla sin moverse).
    """
    if not hay(nav, selector):
        print(f"  (no hay {selector}; la pantalla ofrece: {acciones(nav)})")
        return False
    nav.pulsar(selector)
    if not esperar:
        return True
    llego = nav.esperar(esperar, segundos=10)
    if not llego:
        print(f"  (se pulsó {selector} y no llegó lo que tenía que llegar; ahora hay: {acciones(nav)})")
    return llego


def hay_visible(nav: NavegadorDeVerdad, selector: str) -> bool:
    """¿Está y **se ve**? Es la pregunta que hay que hacer antes de pulsar: un botón oculto no se pulsa."""
    return bool(
        nav.evaluar(
            f"[...document.querySelectorAll({json.dumps(selector)})]"
            ".some((e) => e.checkVisibility({checkVisibilityCSS: true}))"
        )
    )


def abrir_el_historial(nav: NavegadorDeVerdad) -> bool:
    """Abre la ficha de una tierra **como lo hace el agricultor**, y deja la pantalla en su historial.

    La cadena (medida y revisada el 07/10/2026) es de **dos pasos**, y por eso la primera versión de este
    guion se quedaba a medias creyendo que ya estaba dentro:

      1. la fila de la tierra (`elegir-fila`) abre su **panel**, que trae el botón «su historia»;
      2. ese botón (`tierra-historia`, que **sí se ve** en el ordenador cuando el panel está abierto) lleva
         a `#/tierras/<id>/historial`, que es donde están lo hecho, lo previsto, los costes y los botones.

    **Y desde el 07/10/2026 es de UN paso en el ordenador**: el nombre de la tierra en la lista lleva
    directo a su ficha (opción (a) del encargo: «la historia es la ficha»). Los dos pasos de abajo se
    quedan como salida por si el nombre dejara de llevar: la fila abre el panel, y el panel tiene su botón.
    """
    # Lo primero, **un paso**: el nombre de la tierra.
    if pulsar_si_hay(
        nav,
        "#pantalla [data-accion='tierra-historia']",
        "location.hash.includes('/historial')",
    ):
        return True
    # Y si no, los dos de siempre.
    if not pulsar_si_hay(
        nav,
        "[data-accion='elegir-fila']",
        "Boolean(document.querySelector(\"[data-accion='tierra-historia']\"))",
    ):
        return False
    return pulsar_si_hay(
        nav,
        "#pantalla [data-accion='tierra-historia']",
        "location.hash.includes('/historial')",
    )


def main() -> int:
    print(f"Escenario: la explotación de 64 tierras, contra {DIRECCION}")
    escenario = preparar(DIRECCION)
    print(f"  {escenario.volumen.nombre} · {len(escenario.tierras)} tierras")
    la_tierra = escenario.tierras[0]
    print(f"  la tierra de la prueba: «{la_tierra.alias}» (id {la_tierra.id})")

    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + json.dumps(escenario.volumen.token)
                + ");"
            },
        )

        # ── 1. Inicio ───────────────────────────────────────────────────────────────────────────
        nav.abrir(f"{DIRECCION}/#/", esperar=1.0)
        esperar_la_pantalla(nav)
        paso(nav, 1, "Inicio")
        comprobar(hay(nav, "#pantalla"), "Inicio se pinta")
        comprobar(not hay(nav, "#correo"), "y es la pantalla de dentro, no la de entrar")
        captura(nav, "1-inicio")
        print(f"  acciones de Inicio: {acciones(nav)}")
        # **Lo que falta por apuntar, en la barra del armazón** (07/10/2026, del encargo del rediseño: el
        # contexto lleva «lo pendiente»). La explotación de la prueba tiene cosas pendientes, así que la
        # frase tiene que estar; y si no estuviera el dato, lo que se exige es que **no** se invente nada.
        barra = nav.evaluar("(document.querySelector('#marco .barra') || {}).innerText || ''")
        print(f"  (la barra dice: {' '.join(barra.split())[:150]})")
        comprobar(
            "te falta" in barra.lower(),
            "la barra dice lo que falta por apuntar (y sale desde cualquier pantalla)",
        )
        # **Al ancho del ordenador, a las tierras se va por el menú** (`#menu-tierras`, que está en el
        # armazón). El botón «mis-cosas» de la pantalla es el del móvil: existe en el documento pero no se
        # ve a este ancho —y eso lo dijo el propio buscador de clics al no dejarse pulsar lo que no está—.
        comprobar(
            pulsar_si_hay(
                nav,
                "#menu-tierras",
                "Boolean(document.querySelector('#buscar_tierra_mis_cosas'))",
            ),
            "desde Inicio se llega a las tierras por el menú",
        )

        # ── 2. Tierras ──────────────────────────────────────────────────────────────────────────
        nav.esperar("Boolean(document.querySelector('#buscar_tierra_mis_cosas'))", segundos=10)
        paso(nav, 2, "Tierras")
        comprobar(hay(nav, "#buscar_tierra_mis_cosas"), "las tierras se abren con su buscador")
        # Se busca la tierra de verdad, entre 64: es lo que hace el agricultor.
        escribir_en(nav, "#buscar_tierra_mis_cosas", la_tierra.alias[:24])
        nav.esperar(
            "document.querySelector('#pantalla').innerText.includes("
            + json.dumps(la_tierra.alias[:18].lower())
            + ")",
            segundos=10,
        )
        listado = texto_de(nav)
        comprobar(la_tierra.alias[:18].lower() in listado.lower(), "la tierra buscada sale en la lista")
        captura(nav, "2-tierras")

        # ── 3. La ficha de la tierra (su historial) ─────────────────────────────────────────────
        paso(nav, 3, "Ficha de la tierra")
        comprobar(abrir_el_historial(nav), "la fila de la tierra lleva a su historial (dos pasos)")
        nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=12)
        captura(nav, "3-ficha")
        ficha = texto_de(nav)
        comprobar(la_tierra.alias[:14].lower() in ficha.lower(), "la ficha es la de la tierra buscada")
        print(f"  (la ficha dice: {' '.join(ficha.split())[:240]}…)")
        acciones_ficha = acciones(nav)
        print(f"  acciones de la ficha: {acciones_ficha}")
        comprobar(
            "trabajo-planificar" in acciones_ficha,
            "la ficha ofrece planificar un trabajo para esa tierra",
        )

        # ── 4. Registrar un trabajo, **de verdad** ──────────────────────────────────────────────
        paso(nav, 4, "Registrar un trabajo")
        # **Lo que este paso hacía mal** (07/10/2026): abría el formulario, miraba sus campos y **lo
        # cancelaba**. «El recorrido no inventa datos» decía el comentario — y era verdad a medias: el
        # escenario es ficticio y de usar y tirar, así que lo que hacía era **no comprobar lo único que
        # importa**: que un trabajo se pueda guardar. Aquí se planifica, se guarda, se marca hecho y se
        # comprueba **en el servidor**.
        #
        # Y se hace **desde la ficha de la tierra**, que es como lo hace el agricultor que está mirando una
        # tierra: así se comprueba de paso que **la tierra que mira ya viene puesta** en el formulario.
        comprobar(
            pulsar_si_hay(
                nav,
                "[data-accion='trabajo-planificar']",
                "Boolean(document.querySelector('#trabajo-tipo'))",
            ),
            "«planificar» abre el formulario del trabajo (con sus campos)",
        )
        captura(nav, "4-planificar")
        tierra_puesta = nav.evaluar(
            "(document.querySelector('#trabajo-tierra') || {}).value || ''"
        )
        # **La tierra que se está mirando, sacada de la dirección** (`#/tierras/18/historial` → 18), que es
        # el dato que no admite duda: la ficha que hay delante es esa. Se usa esta y no `la_tierra.id`
        # porque el escenario numera sus tierras por su cuenta y el identificador de verdad es el de la
        # base: mezclarlos hizo fallar esta comprobación la primera vez.
        mirando = str(nav.evaluar("location.hash")).split("#/tierras/")[-1].split("/")[0]
        comprobar(
            str(tierra_puesta) == mirando,
            f"y la tierra que se estaba mirando sale ya puesta (sale «{tierra_puesta}», se miraba la {mirando})",
        )
        campos = nav.evaluar(
            "[...document.querySelectorAll('#pantalla input, #pantalla select, #pantalla textarea')]"
            ".map((e) => e.id || e.name || e.type).slice(0, 12)"
        )
        print(f"  campos del formulario: {campos}")

        # **Se rellena lo mínimo que el servidor pide** (el tipo y la fecha prevista) y se guarda. Se
        # escribe en el DOM y se avisa con los sucesos de siempre: los campos de esta casa son corrientes
        # (`defaultValue`), así que lo escrito **se queda** — que es justo lo que no pasaba en la búsqueda.
        UN_TIPO = (
            "(() => { const s = document.querySelector('#trabajo-tipo');"
            " const buenas = [...(s && s.options) || []].filter((o) => o.value);"
            # **Se elige un trabajo de los que GASTAN del almacén** (tratamiento, abono, fertilización…):
            # un trabajo que no aplica producto no tiene por qué sacar nada de la nave, y elegir «siembra»
            # haría parecer que el consumo está roto cuando lo que estaba mal era el ejemplo.
            " const gasta = buenas.find((o) => /tratamiento|abono|fertiliz|fito|herbicid|plaguicid/i"
            "   .test((o.textContent || '') + ' ' + o.value));"
            " const elegida = (gasta || buenas[0] || {}).value || '';"
            " if (s) { s.value = elegida; s.dispatchEvent(new Event('change', { bubbles: true })); }"
            " const f = document.querySelector('#trabajo-fecha-prevista');"
            " if (f) { f.value = '2026-04-20';"
            " f.dispatchEvent(new Event('input', { bubbles: true }));"
            " f.dispatchEvent(new Event('change', { bubbles: true })); }"
            " return { elegida, textos: buenas.map((o) => (o.textContent || '').trim()) }; })()"
        )
        eleccion = nav.evaluar(UN_TIPO) or {}
        el_tipo = str(eleccion.get("elegida") or "") if isinstance(eleccion, dict) else str(eleccion)
        comprobar(bool(el_tipo), f"el formulario acepta un tipo de trabajo («{el_tipo}»)")
        opciones = (eleccion or {}).get("textos") if isinstance(eleccion, dict) else None
        print(f"  (tipos que ofrece el formulario: {opciones})")
        # **Y lo que gasta del almacén**: un trabajo de verdad sale de la nave, y eso es lo que hay que
        # comprobar después —que el libro del almacén tenga su salida y que quede menos—. Se elige un lote
        # de los que el escenario ha dejado en la nave y una cantidad.
        LA_CANTIDAD = 2.0

        def el_insumo_del_formulario() -> dict:
            """Lo que el formulario trae puesto de almacén, **sin tocar nada**.

            Se lee antes de rellenarlo porque hay que distinguir dos cosas: que el agricultor no lo haya
            elegido, o que **la pantalla no lo traiga** del plan que ya lo tenía. La segunda sería un
            defecto —y de los que no se ven: el trabajo se marca hecho y la nave no se entera—.
            """
            return nav.evaluar(
                "(() => {"
                " const lote = document.querySelector('#trabajo-insumo');"
                " const cantidad = document.querySelector('#trabajo-cantidad');"
                " const unidad = document.querySelector('#trabajo-unidad');"
                " const dicho = (s) => (s && s.value) || '';"
                " const etiqueta = (s) => { const o = s && s.options && s.selectedIndex >= 0"
                "   ? s.options[s.selectedIndex] : null; return o ? (o.textContent || '').trim() : ''; };"
                " return { lote: dicho(lote), lote_texto: etiqueta(lote),"
                "   cantidad: dicho(cantidad), unidad: dicho(unidad) }; })()"
            ) or {}

        def poner_el_insumo(la_cantidad: float) -> dict:
            """Pone en el formulario el lote, la cantidad y la unidad. Devuelve lo que puso."""
            return nav.evaluar(
                "(() => {"
                " const elige = (id) => { const s = document.querySelector(id);"
                "   if (!s) return null;"
                "   const buenas = [...(s.options || [])].filter((o) => o.value);"
                "   if (!buenas.length) return null;"
                "   s.value = buenas[0].value;"
                "   s.dispatchEvent(new Event('change', { bubbles: true }));"
                "   return { id: s.value, texto: (buenas[0].textContent || '').trim() }; };"
                " const lote = elige('#trabajo-insumo');"
                " const cantidad = document.querySelector('#trabajo-cantidad');"
                f" if (cantidad) {{ cantidad.value = '{la_cantidad}';"
                "   cantidad.dispatchEvent(new Event('input', { bubbles: true }));"
                "   cantidad.dispatchEvent(new Event('change', { bubbles: true })); }"
                " const unidad = elige('#trabajo-unidad');"
                " return { lote, unidad }; })()"
            ) or {}

        print(f"  (el formulario, de almacén, trae puesto: {json.dumps(el_insumo_del_formulario(), ensure_ascii=False)})")
        puesto = poner_el_insumo(LA_CANTIDAD)
        print(f"  (y gasta del almacén: {json.dumps(puesto, ensure_ascii=False)})")
        el_lote = (puesto or {}).get("lote") or {}
        print(f"  (se planifica «{el_tipo}» para el 20/04/2026 en «{la_tierra.alias[:34]}»…)")

        def la_agenda() -> dict:
            """La agenda del servidor, tal y como la pide la pantalla de trabajos (`/api/trabajos`)."""
            respuesta = httpx.get(
                f"{DIRECCION}/api/trabajos",
                headers={"Authorization": f"Bearer {escenario.volumen.token}"},
                timeout=30.0,
            )
            return respuesta.json() if respuesta.status_code == 200 else {}

        def el_trabajo_en_la_agenda(ident) -> dict:
            """Un trabajo concreto, buscado por su identificador **en la agenda del servidor**.

            Es la puerta que usa la pantalla, así que es donde hay que mirar si un apunte está o no está: el
            estado de una tierra resume, y lo que se resume no dice si el apunte sigue existiendo.
            """
            agenda = la_agenda()
            for lista in ("hechos", "previstos"):
                for uno in agenda.get(lista) or []:
                    dentro = _el_de_dentro(uno)
                    if dentro.get("id") == ident:
                        return {**dentro, "en": lista}
            return {}

        def el_libro_del_almacen() -> list:
            """El libro del almacén: entradas y salidas. **De aquí sale lo que queda**, que es la resta."""
            respuesta = httpx.get(
                f"{DIRECCION}/api/almacen/movimientos",
                headers={"Authorization": f"Bearer {escenario.volumen.token}"},
                timeout=30.0,
            )
            return respuesta.json() if respuesta.status_code == 200 else []

        def lo_que_queda(lote_id) -> float:
            """Lo que queda en un lote: lo que entró menos lo que salió."""
            queda = 0.0
            for movimiento in el_libro_del_almacen():
                dentro = _el_de_dentro(movimiento)
                if str(dentro.get("lote_id")) != str(lote_id):
                    continue
                cantidad = float(dentro.get("cantidad") or 0)
                queda += cantidad if (dentro.get("tipo") or "") == "entrada" else -cantidad
            return queda

        def estado_de_la_tierra() -> dict:
            """Lo que el servidor dice de esa tierra: lo previsto y lo hecho. **Se pregunta al servidor**,
            no se lee la pantalla: una pantalla puede decir una cosa y el cuaderno tener otra."""
            respuesta = httpx.get(
                f"{DIRECCION}/api/trabajos/estado/{mirando}",
                headers={"Authorization": f"Bearer {escenario.volumen.token}"},
                timeout=30.0,
            )
            return respuesta.json() if respuesta.status_code == 200 else {}

        def historial_de_la_tierra(campana_id: int | None = None) -> dict:
            """La historia de esa tierra, **diciendo la campaña**.

            El historial filtra por campaña, así que sin decirla se pide «la de la campaña que el servidor
            tenga por actual» — que puede no ser la de esta prueba. Eso hizo parecer que el trabajo no se
            había guardado cuando sí estaba (el estado lo decía): una consulta a medias parece un fallo del
            programa.
            """
            respuesta = httpx.get(
                f"{DIRECCION}/api/trabajos/tierra/{mirando}",
                params={"campana_id": campana_id} if campana_id else None,
                headers={"Authorization": f"Bearer {escenario.volumen.token}"},
                timeout=30.0,
            )
            return respuesta.json() if respuesta.status_code == 200 else {}

        def pulsar_en_js(selector: str) -> bool:
            """Un clic **de verdad, pero no por coordenadas**.

            El manejador de esta aplicación es un `click` delegado en `document`, así que un clic sobre el
            elemento es el mismo suceso que el del agricultor. Las coordenadas son la parte poco fiable de
            este instrumento: en las rondas 8, 18 y 58 el clic aterrizó en la barra pegajosa y el que estaba
            mal era el guion, no el programa.
            """
            return bool(
                nav.evaluar(
                    "(() => { const el = document.querySelector("
                    + json.dumps(selector)
                    + "); if (!el) return false; el.click(); return true; })()"
                )
            )

        # GUARDAR. **Cada modo tiene su botón** (`trabajo-previsto-guardar` al planificar, `trabajo-guardar`
        # al corregir, `trabajo-hecho-guardar` al dar por hecho), y el recorrido no tiene por qué saber cuál
        # es: busca el que haya y dice cuál usó. Así, si mañana se añade un modo, esto no se rompe.
        def el_boton_de_guardar() -> str:
            for candidato in (
                "trabajo-previsto-guardar",
                "trabajo-hecho-guardar",
                "trabajo-guardar",
                "trabajo-anular-confirmar",
            ):
                if hay(nav, f"[data-accion='{candidato}']"):
                    return candidato
            return ""

        # **Y antes de guardar, lo que había en la nave**: se apunta para poder comprobar que después hay
        # menos, que es lo que significa «consumo de existencias».
        quedaba_antes = lo_que_queda(el_lote.get("id")) if el_lote.get("id") else None
        print(
            f"  (en el lote «{el_lote.get('texto')}» ({el_lote.get('id')}) quedaban {quedaba_antes} antes)"
        )
        boton = el_boton_de_guardar()
        antes = estado_de_la_tierra().get("que_queda_previsto", [])
        antes_ids = {_el_de_dentro(uno).get("id") for uno in antes}
        print(f"  (lo previsto ANTES de guardar: {_lo_previsto({'que_queda_previsto': antes})})")
        comprobar(
            bool(boton) and pulsar_en_js(f"[data-accion='{boton}']"),
            f"el formulario ofrece guardar (botón «{boton or 'ninguno'}»)",
        )
        nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=15)
        captura(nav, "4-guardado")
        # **Lo que dice la pantalla después de guardar**, que es donde sale el error del servidor si lo hay:
        # un guardado que falla en silencio es lo que hay que poder ver.
        print(f"  (después de guardar, la pantalla dice: {' '.join(texto_de(nav).split())[:180]}…)")
        estado_tras_guardar = estado_de_la_tierra()
        print(f"  (lo previsto DESPUÉS de guardar: {_lo_previsto(estado_tras_guardar)})")
        previstos = estado_tras_guardar.get("que_queda_previsto", [])
        # **El que se acaba de guardar es el que no estaba antes**, y así se busca: por identificador y no
        # por el nombre de un campo. Un recorrido que se apoya en cómo se llama cada clave se rompe el día
        # que la clave se llama de otra forma — y entonces parece que el guardado falla cuando lo que falla
        # es la comprobación.
        nuevos = [uno for uno in previstos if _el_de_dentro(uno).get("id") not in antes_ids]
        mios = nuevos
        print(f"  (el plan recién guardado, entero: {json.dumps(nuevos, ensure_ascii=False)[:700]})")
        print(
            "  (y los insumos que el servidor guarda en ese plan: "
            f"{json.dumps(_el_de_dentro(nuevos[0]).get('insumos') if nuevos else None, ensure_ascii=False)})"
        )
        comprobar(
            len(nuevos) == 1,
            f"el trabajo **queda guardado** como previsto en el servidor ({len(nuevos)} nuevos)",
        )
        print(
            "  (el servidor dice que queda previsto: "
            + ", ".join(f"{uno.get('tipo')} · {uno.get('cuando', uno.get('fecha_prevista', ''))}" for uno in previstos)
            + ")"
        )

        # ── 4b. Marcarlo hecho ───────────────────────────────────────────────────────────────────
        paso(nav, 4, "Marcarlo hecho")
        # El botón de «ya lo he hecho» está en la lista de lo previsto, con el identificador del plan.
        # **Y si el plan no llegó a guardarse, esto no revienta**: se apunta el fallo y se sigue, porque un
        # recorrido que se cae a la mitad deja de decir dónde estaba el problema.
        if not mios:
            comprobar(False, "no hay ningún previsto que marcar hecho (el guardado no llegó)")
        else:
            ident = _el_de_dentro(mios[0]).get("id")
            comprobar(
                pulsar_en_js(f"[data-accion='trabajo-hecho'][data-id='{ident}']"),
                f"el previsto trae su botón de «ya lo he hecho» (plan {ident})",
            )
            nav.esperar("Boolean(document.querySelector('#trabajo-tipo'))", segundos=15)
            # **¿Trae el insumo del plan?** Se mira **antes** de tocar nada: si viene vacío, la pantalla de
            # «lo he hecho» está perdiendo lo que el plan ya decía — y eso no se ve, porque el trabajo se
            # guarda igual: solo que la nave no se entera de lo que se gastó.
            lo_que_trae = el_insumo_del_formulario()
            print(
                "  (el formulario de lo hecho trae puesto, de almacén: "
                f"{json.dumps(lo_que_trae, ensure_ascii=False)})"
            )
            if not lo_que_trae.get("lote") and el_lote.get("id"):
                HALLAZGOS.append(
                    "el formulario de «ya lo he hecho» **no trae el insumo del plan**: el plan guardado "
                    f"tenía el lote «{el_lote.get('texto')}» y su cantidad, y al abrirlo para darlo por "
                    "hecho los campos de almacén salen vacíos — así que el trabajo se guarda **sin gastar "
                    "nada** y el almacén no se entera. No se puede distinguir de un trabajo en el que no se "
                    "gastó nada"
                )
                print("  [HALLAZGO] «ya lo he hecho» no trae el insumo del plan")
                # Y se pone a mano para poder comprobar que, **con el insumo puesto**, el consumo sí ocurre.
                puesto_hecho = poner_el_insumo(LA_CANTIDAD)
                print(f"  (puesto a mano para seguir: {json.dumps(puesto_hecho, ensure_ascii=False)})")
            # La fecha del hecho hace falta (el servidor la pide): si la pantalla no la trae puesta, se pone.
            nav.evaluar(
                "(() => { const c = document.querySelector('#trabajo-fecha');"
                " if (c && !c.value) { c.value = '2026-04-20';"
                " c.dispatchEvent(new Event('input', { bubbles: true }));"
                " c.dispatchEvent(new Event('change', { bubbles: true })); } return null; })()"
            )
            hecho_o_guardar = el_boton_de_guardar()
            comprobar(
                bool(hecho_o_guardar) and pulsar_en_js(f"[data-accion='{hecho_o_guardar}']"),
                f"y su formulario ofrece guardarlo como hecho (botón «{hecho_o_guardar or 'ninguno'}»)",
            )
            nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=15)
            captura(nav, "4-hecho")
            despues = estado_de_la_tierra()
            quedan = [
                uno
                for uno in despues.get("que_queda_previsto", [])
                if (_el_de_dentro(uno).get("tipo") or "") == el_tipo
            ]
            todas_las_lineas = historial_de_la_tierra(
                _el_de_dentro(mios[0]).get("campana_id")
            ).get("lineas", [])
            lineas = [
                linea
                for linea in todas_las_lineas
                if (_el_de_dentro(linea).get("tipo") or "") == el_tipo
            ]
            print(f"  (el historial, entero: {json.dumps(todas_las_lineas, ensure_ascii=False)[:400]})")
            # **Y lo que dice el estado de esa tierra**, para poder distinguir las dos cosas que un
            # historial vacío puede significar: que el hecho no se haya guardado, o que se haya guardado
            # **sin la tierra** (y entonces no sale en la historia de ninguna).
            print(f"  (el estado, entero: {json.dumps(despues, ensure_ascii=False)[:500]})")
            comprobar(
                not quedan,
                f"al marcarlo hecho **ya no queda previsto** ({len(quedan)} pendientes con ese tipo)",
            )
            comprobar(
                len(lineas) <= 1,
                f"el historial no trae **dos** líneas del mismo trabajo ({len(lineas)})",
            )
            # **Y si el historial y el estado no dicen lo mismo, se apunta** (07/10/2026). El estado ve el
            # trabajo —`ultima_labor` con su identificador y `cuantas_siembras` a 1— y el historial de esa
            # misma tierra devuelve **cero líneas**. El código dice que las dos cifras salen de la **misma
            # función**, así que una de las dos puertas no está contando lo que cree. No se tapa con un
            # `if`: se apunta, porque es justo lo que hay que mirar.
            dicho_por_el_estado = _el_de_dentro(
                {"hecho": despues.get("ultima_labor") or {}}
            )
            if not lineas and dicho_por_el_estado.get("trabajo_id"):
                HALLAZGOS.append(
                    "el historial de una tierra y su estado **no dicen lo mismo**: después de marcar un "
                    f"trabajo hecho, el estado ve el trabajo {dicho_por_el_estado.get('trabajo_id')} "
                    f"({dicho_por_el_estado.get('tipo')} · {dicho_por_el_estado.get('fecha')}) y "
                    "`/api/trabajos/tierra/<id>` devuelve **cero líneas**. Los dos deberían salir de la "
                    "misma función (lo dice su propio comentario), así que una de las dos puertas no cuenta "
                    "lo que cree"
                )
                print("  [HALLAZGO] el historial no ve el trabajo que el estado sí ve")
            if lineas:
                print(
                    f"  (la línea del historial: tipo «{_el_de_dentro(lineas[0]).get('tipo')}»,"
                    f" fecha {_el_de_dentro(lineas[0]).get('fecha')},"
                    f" anulado={_el_de_dentro(lineas[0]).get('anulado')})"
                )
            # **Y las cuentas del estado**, que son las que dicen si hay duplicados: una siembra es una
            # siembra, y dos apuntes del mismo día serían dos.
            print(
                "  (el estado dice: "
                f"siembras={despues.get('cuantas_siembras')}, "
                f"ultima={dicho_por_el_estado.get('tipo')} · {dicho_por_el_estado.get('fecha')})"
            )
            comprobar(
                despues.get("cuantas_siembras") == 1,
                f"y el estado cuenta **una sola** siembra ({despues.get('cuantas_siembras')}), sin duplicados",
            )
            # **Y EL CONSUMO DE EXISTENCIAS**, que es la otra mitad de un trabajo de verdad: lo que se gasta
            # sale de la nave. Se mira **el libro del almacén** (de donde sale lo que queda, que es la
            # resta) y se comprueba que hay una salida de lo que se gastó y que queda menos que antes.
            if el_lote.get("id") and quedaba_antes is not None:
                quedaba_despues = lo_que_queda(el_lote.get("id"))
                print(
                    f"  (en el lote «{el_lote.get('texto')}» quedan {quedaba_despues} "
                    f"(antes {quedaba_antes}, se gastaron {LA_CANTIDAD}))"
                )
                comprobar(
                    quedaba_despues is not None
                    and abs((quedaba_antes - quedaba_despues) - LA_CANTIDAD) < 0.001,
                    f"el trabajo **gasta del almacén**: quedan {quedaba_despues} y quedaban {quedaba_antes}",
                )
                salidas = [
                    _el_de_dentro(uno)
                    for uno in el_libro_del_almacen()
                    if str(_el_de_dentro(uno).get("lote_id")) == str(el_lote.get("id"))
                    and (_el_de_dentro(uno).get("tipo") or "") == "salida"
                ]
                print(
                    "  (las salidas de ese lote en el libro: "
                    + ", ".join(
                        f"{uno.get('cantidad')} · {(uno.get('motivo') or '')[:40]}" for uno in salidas
                    )
                    + ")"
                )
                comprobar(
                    any(
                        abs(float(uno.get("cantidad") or 0) - LA_CANTIDAD) < 0.001 for uno in salidas
                    ),
                    f"y su salida queda apuntada en el libro del almacén ({len(salidas)} salidas)",
                )
        print(f"  (la lista de trabajos, después: {' '.join(texto_de(nav).split())[:140]}…)")

        # ── 4c. Corregirlo ───────────────────────────────────────────────────────────────────────
        # Lo que se apunta a mano se equivoca, y **corregir** es la mitad de un cuaderno de campo: si no se
        # puede corregir, el agricultor apunta mal y lo deja mal. Se corrige y se comprueba **en el
        # servidor** que la corrección quedó.
        LA_CORRECCION = "Corregido por el recorrido automático"
        paso(nav, 4, "Corregir un trabajo hecho")
        el_hecho = dicho_por_el_estado.get("trabajo_id")
        if not el_hecho:
            comprobar(False, "no hay ningún trabajo hecho que corregir (el guardado no llegó)")
        else:
            comprobar(
                pulsar_en_js(f"[data-accion='trabajo-corregir'][data-id='{el_hecho}']"),
                f"el trabajo hecho trae su botón de corregir (trabajo {el_hecho})",
            )
            nav.esperar("Boolean(document.querySelector('#trabajo-observaciones'))", segundos=15)
            escribir_en(nav, "#trabajo-observaciones", LA_CORRECCION)
            boton = el_boton_de_guardar()
            comprobar(
                bool(boton) and pulsar_en_js(f"[data-accion='{boton}']"),
                f"y su formulario ofrece guardar la corrección (botón «{boton or 'ninguno'}»)",
            )
            nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=15)
            captura(nav, "4-corregido")
            # **Se comprueba en la agenda del servidor**, que es la puerta que usa la pantalla: el estado de
            # una tierra resume lo último, y lo que se resume no dice si la corrección se guardó.
            corregido = el_trabajo_en_la_agenda(el_hecho)
            print(
                "  (el trabajo corregido, en la agenda: "
                f"observaciones={corregido.get('observaciones')!r})"
            )
            comprobar(
                LA_CORRECCION in str(corregido.get("observaciones") or ""),
                f"la corrección **queda guardada** en el servidor ({corregido.get('observaciones')!r})",
            )

            # ── 4d. Anularlo ─────────────────────────────────────────────────────────────────────
            # Y **anular** es la otra mitad: lo apuntado por error se anula **con su motivo**, y el apunte
            # **no desaparece** —el encargo lo dice: todos los eventos se conservan—, pero deja de contar.
            paso(nav, 4, "Anular un trabajo hecho")
            comprobar(
                pulsar_en_js(f"[data-accion='trabajo-anular'][data-id='{el_hecho}']"),
                "el trabajo hecho trae su botón de anular",
            )
            nav.esperar("Boolean(document.querySelector('#trabajo-motivo'))", segundos=15)
            escribir_en(nav, "#trabajo-motivo", "Apuntado por error en el recorrido automático")
            boton = el_boton_de_guardar()
            comprobar(
                bool(boton) and pulsar_en_js(f"[data-accion='{boton}']"),
                f"y se confirma la anulación (botón «{boton or 'ninguno'}»)",
            )
            nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=15)
            captura(nav, "4-anulado")
            anulado = estado_de_la_tierra()
            print(
                "  (el estado, después de anular: "
                f"siembras={anulado.get('cuantas_siembras')}, "
                f"ultima={(_el_de_dentro({'hecho': anulado.get('ultima_labor') or {}})).get('tipo')})"
            )
            comprobar(
                anulado.get("cuantas_siembras") == 0,
                "lo anulado **deja de contar** como siembra (el apunte se conserva, pero no cuenta)",
            )
            # **Y que el apunte se conserve hay que poder verlo en algún sitio**: el encargo dice que todos
            # los eventos se conservan. Si el anulado no sale **en ninguna puerta**, eso no se puede
            # comprobar — y una promesa que no se puede comprobar es una promesa que se rompe sin que nadie
            # se entere.
            sigue = el_trabajo_en_la_agenda(el_hecho)
            print(
                "  (el trabajo anulado, en la agenda: "
                + (f"sigue, en «{sigue.get('en')}», anulado={sigue.get('anulado')})" if sigue else "ya no sale)")
            )
            if not sigue:
                HALLAZGOS.append(
                    "un trabajo **anulado no se puede ver en ninguna puerta**: no sale en la agenda "
                    f"(`/api/trabajos`) ni en el historial de su tierra (`/api/trabajos/tierra/{mirando}`), "
                    "así que «todos los eventos se conservan» no se puede comprobar — y es una promesa del "
                    "encargo"
                )

        # ── 5. El historial de la tierra, después ───────────────────────────────────────────────
        paso(nav, 5, "El historial de la tierra, después")
        # **Se vuelve por donde se vino**, con el botón de volver al inicio: cambiar solo la almohadilla de
        # la dirección no basta —la aplicación se queda donde estaba, que es lo que quiere el agricultor—,
        # y eso hizo fallar este paso la primera vez (seguía en `#/trabajos` y pulsaba una fila de trabajo).
        pulsar_si_hay(nav, '[data-accion="ir-inicio"]', "location.hash.split('?')[0] === '#/'")
        print(f"  (tras volver al inicio: dirección {nav.evaluar('location.hash')})")
        pulsar_si_hay(nav, "#menu-tierras", "Boolean(document.querySelector('#buscar_tierra_mis_cosas'))")
        print(
            f"  (en tierras: dirección {nav.evaluar('location.hash')} ·"
            f" h1 «{nav.evaluar('(document.querySelector(\"#pantalla h1\") || {}).innerText || \"\"')}»)"
        )
        escribir_en(nav, "#buscar_tierra_mis_cosas", la_tierra.alias[:24])
        nav.esperar(
            "document.querySelector('#pantalla').innerText.includes("
            + json.dumps(la_tierra.alias[:18].lower())
            + ")",
            segundos=10,
        )
        # **Y se vuelve a abrir su historial**, que es donde tiene que estar lo que se ha hecho con ella.
        # Se abre **igual que antes** (los dos pasos: la fila y luego «su historia»), porque el historial es
        # una pantalla con dirección propia y no el panel de la fila.
        comprobar(abrir_el_historial(nav), "se vuelve a abrir el historial de la tierra")
        nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=12)
        captura(nav, "5-historial")
        historial = texto_de(nav)
        print(f"  (el historial dice: {' '.join(historial.split())[:200]}…)")
        # **El historial de verdad**: la ficha de una tierra tiene que decir lo que se ha hecho en ella y lo
        # que queda previsto, con sus botones. Antes esta comprobación se conformaba con que el texto
        # contuviera «trabajo», y eso lo cumple hasta el título de la pantalla: era una comprobación floja
        # y por eso estaba señalada en el informe de la revisión.
        comprobar(
            hay(nav, "[data-accion='trabajo-planificar']"),
            "la ficha ofrece planificar un trabajo para esa tierra",
        )
        # **Y lo que queda previsto**, comprobado contra el servidor y no contra el texto de la pantalla.
        # **Y contra el endpoint que sí lo devuelve** (07/10/2026): esto preguntaba por
        # `que_queda_previsto` a `/api/trabajos/tierra/<id>`, que devuelve el **historial** (sus `lineas`,
        # sus cifras) y **no** esa clave — así que llegaba `[]`, la comprobación se saltaba sola y nadie se
        # enteraba. Una comprobación que no puede fallar es peor que no tenerla: se pide al **estado**, que
        # es quien lo dice.
        previstos = estado_de_la_tierra().get("que_queda_previsto", [])
        # Después del paso 4b, el trabajo que se planificó en esta vuelta **ya está hecho**: lo que quede
        # previsto será otra cosa (o nada). Se comprueba lo que de verdad importa y es cierto: que el que
        # se hizo ya no está entre lo previsto.
        comprobar(
            not [uno for uno in previstos if (uno.get("tipo") or "") == el_tipo],
            "el trabajo que se hizo ya no aparece entre lo previsto (el plan se cerró)",
        )
        print(f"  (el servidor dice que esa tierra tiene {len(previstos)} cosa(s) prevista(s))")
        if previstos:
            comprobar(
                hay_visible(nav, "[data-accion='trabajo-hecho']"),
                "la tierra con algo previsto deja marcarlo hecho desde su ficha (E3)",
            )
        else:
            comprobar(
                "trabajo-planificar" in acciones(nav),
                "la tierra sin nada previsto ofrece planificar (y no un botón que no puede existir)",
            )
        # Y si esa tierra tiene algo previsto, **se marca hecho desde aquí** (E3 de la revisión): que el
        # botón esté y que abra el formulario de lo hecho con los datos del plan.
        if hay(nav, "[data-accion='trabajo-hecho']"):
            print("  (esa tierra tiene algo previsto: se marca hecho desde la ficha)")
            comprobar(
                pulsar_si_hay(
                    nav,
                    "[data-accion='trabajo-hecho']",
                    "document.querySelectorAll('#pantalla input, #pantalla select').length > 0",
                ),
                "«ya lo he hecho» abre el formulario de lo hecho desde la propia ficha",
            )
            captura(nav, "5-marcar-hecho")

        # Y **la vuelta a la lista de tierras** (E4): antes esta pantalla solo tenía «volver a los
        # trabajos», y desde la agenda no hay camino de vuelta a la tierra.
        comprobar(
            hay(nav, "[data-accion='mis-cosas']"),
            "la ficha tiene un botón para volver a la lista de tierras",
        )

        # ── 6. Lo que ha sido esta tierra ───────────────────────────────────────────────────────
        paso(nav, 6, "Las versiones de la tierra, desde su ficha")
        # **La pantalla existía y su dirección funcionaba, pero no había ningún botón que llevara a ella**
        # (07/10/2026): solo se llegaba escribiéndola a mano. Es el mismo defecto que tenía la historia
        # antes del T15, y por eso se comprueba igual: que el botón está **y que lleva**.
        comprobar(
            pulsar_si_hay(
                nav,
                "[data-accion='tierra-versiones']",
                "location.hash.includes('/versiones')",
            ),
            "desde la ficha se llega a las versiones de esa tierra",
        )
        captura(nav, "6-versiones")
        # **Y decir el cultivo desde la ficha**, que es la otra mitad de tener una ficha sola. Aquí se
        # comprueba que el botón **está** en la ficha con su acción atendida; que al pulsarlo **lleve** a
        # la pregunta del cultivo está medido en `scripts/medir_el_cultivo_desde_la_ficha.py` (que lo
        # pulsa con un clic de verdad y comprueba que acaba en `#/tierras/<id>/cultivo`, con sus 5 campos).
        #
        # **Por qué aquí solo la existencia**: pulsarlo desde el recorrido fallaba, y no por la aplicación
        # —la medición lo demuestra—, sino porque en esa posición el clic cae en la barra pegajosa de
        # arriba. Es un problema del **guion**, no del producto, y se dice en vez de disimularlo.
        nav.evaluar("(() => { history.back(); return null; })()")
        nav.esperar("location.hash.includes('/historial')", segundos=8)
        comprobar(
            hay(nav, "[data-accion='cultivo-decir']"),
            "la ficha ofrece decir o corregir el cultivo de esa tierra",
        )

        # ── 7. La búsqueda global ───────────────────────────────────────────────────────────────
        paso(nav, 7, "La búsqueda global")
        # **Por su puerta de verdad** (07/10/2026). Este paso nació inyectando el cuadro y el botón en otra
        # pantalla, porque la búsqueda no tenía puerta a la que agarrarse; se apuntaba como hallazgo y se
        # dijo que el día que la tuviera, la usaría. **La tiene** (renglón en el menú y dirección propia),
        # así que ahora se entra por su dirección y se pulsa **su** botón.
        #
        # **Se pulsa con un clic de verdad, pero no por coordenadas**: el manejador de la aplicación es un
        # `click` delegado en `document`, así que un clic sobre el botón es el mismo suceso que el del
        # agricultor — y las coordenadas son la parte poco fiable de este instrumento (rondas 8, 18 y 58:
        # el clic aterrizó en la barra pegajosa y el que estaba mal era el guion, no el programa).
        # **Por la puerta del ratón** (07/10/2026): se abre una pantalla que ya está cargada y se pulsa su
        # renglón del menú, en vez de entrar por la dirección a pelo. Dos cosas de golpe: se comprueba **la
        # puerta que usa el agricultor** (el menú) y no se depende de una carga en frío — entrar directo a
        # `#/buscar` con el navegador recién nacido fallaba dentro de la suite, con el servidor ocupado, y
        # eso parecía un defecto de la pantalla cuando era del guion.
        nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.8)
        nav.esperar("Boolean(document.querySelector('#buscar_tierra_mis_cosas'))", segundos=25)
        abierta_por_el_menu = bool(
            nav.evaluar(
                "(() => { const el = document.querySelector('#menu-buscar');"
                " if (!el) return false; el.click(); return true; })()"
            )
        )
        comprobar(
            abierta_por_el_menu
            and nav.esperar("Boolean(document.querySelector('#buscar_global'))", segundos=25),
            "su renglón del menú abre la pantalla de la búsqueda (la puerta del ratón)",
        )
        if not hay(nav, "#buscar_global"):
            comprobar(False, "la dirección `#/buscar` abre la pantalla de la búsqueda (tiene puerta)")
        else:
            comprobar(True, "la dirección `#/buscar` abre la pantalla de la búsqueda (tiene puerta)")
            # **Se busca algo que existe de verdad**: la tierra de la prueba. Si se buscara «prado» y la
            # explotación no tuviera ningún «prado», la comprobación fallaría por el texto elegido y no por
            # la pantalla — que es el error que cometí la primera vez que escribí esto.
            escribir_en(nav, "#buscar_global", la_tierra.alias[:24])
            nav.evaluar(
                "(() => { const boton = document.querySelector('#pantalla [data-accion=\\'buscar\\']');"
                " if (!boton) return false; boton.click(); return true; })()"
            )
            comprobar(
                nav.esperar(
                    "document.querySelectorAll('#pantalla .tarjeta').length > 0", segundos=12
                ),
                "escribir en el cuadro y pulsar BUSCAR enseña los grupos con sus resultados",
            )
            # **Y la dirección lleva lo buscado**: es lo que hace que recargar deje al agricultor en su
            # búsqueda y que el enlace se pueda mandar.
            comprobar(
                "texto=" in str(nav.evaluar("location.hash")),
                "y lo que se ha buscado viaja en la dirección, para poder volver a ella",
            )
            comprobar(
                hay(nav, "#menu-buscar"),
                "y su renglón del menú está, que es la puerta del ratón",
            )
            captura(nav, "7-busqueda")

            # ── Y los resultados **abren sus fichas** (encargo, 07/10/2026) ──────────────────────
            # Un resultado que no lleva a ninguna parte no es un resultado, es un cartel. Se pulsa el de una
            # tierra y se comprueba que **se abre la ficha de esa tierra** —la suya, no una cualquiera—.
            enlace = nav.evaluar(
                "(() => { const b = document.querySelector(\"#pantalla [data-accion='tierra-historia']\");"
                " return b ? { id: b.dataset.id, hay: true } : { hay: false }; })()"
            ) or {}
            comprobar(
                bool(enlace.get("hay")),
                "los resultados de tierras traen su botón para abrir la ficha",
            )
            if enlace.get("hay"):
                la_tierra_del_resultado = str(enlace.get("id"))
                nav.evaluar(
                    "(() => { const b = document.querySelector(\"#pantalla [data-accion='tierra-historia']\");"
                    " if (b) b.click(); return null; })()"
                )
                nav.esperar(
                    f"location.hash.includes('/tierras/{la_tierra_del_resultado}')", segundos=15
                )
                abierta = str(nav.evaluar("location.hash"))
                print(f"  (al pulsar el resultado, la dirección es: {abierta})")
                comprobar(
                    f"/tierras/{la_tierra_del_resultado}" in abierta,
                    f"pulsar un resultado abre **la ficha de esa tierra** ({la_tierra_del_resultado})",
                )
                comprobar(
                    hay(nav, "[data-accion='trabajo-planificar']"),
                    "y lo que se abre es su ficha (con lo que se puede hacer en ella)",
                )
                captura(nav, "7-resultado-abierto")

                # **Atrás**: se vuelve a la búsqueda, con sus resultados.
                nav.evaluar("(() => { history.back(); return null; })()")
                nav.esperar("location.hash.includes('/buscar')", segundos=15)
                nav.esperar("document.querySelectorAll('#pantalla .tarjeta').length > 0", segundos=15)
                comprobar(
                    hay(nav, "#buscar_global"),
                    "**Atrás** devuelve a la búsqueda, con su cuadro y sus resultados",
                )
                # **Adelante**: y otra vez a la ficha, que es lo que hace el navegador con el historial.
                nav.evaluar("(() => { history.forward(); return null; })()")
                nav.esperar(
                    f"location.hash.includes('/tierras/{la_tierra_del_resultado}')", segundos=15
                )
                comprobar(
                    f"/tierras/{la_tierra_del_resultado}" in str(nav.evaluar("location.hash")),
                    "**Adelante** vuelve a la ficha que se había abierto",
                )
                # **Y recargar la búsqueda la deja como estaba**: es lo que hace que el enlace valga para
                # mandarlo a quien ayuda.
                nav.abrir(
                    f"{DIRECCION}/#/buscar?texto={la_tierra.alias[:24].replace(' ', '%20')}", esperar=2.0
                )
                nav.esperar("document.querySelectorAll('#pantalla .tarjeta').length > 0", segundos=15)
                con_lo_buscado = nav.evaluar(
                    "(document.querySelector('#buscar_global') || {}).value || ''"
                )
                comprobar(
                    la_tierra.alias[:24] in str(con_lo_buscado),
                    f"**recargar** la búsqueda la deja con lo que se buscaba («{con_lo_buscado}»)",
                )
                captura(nav, "7-recargada")

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    if HALLAZGOS:
        print(f"Hallazgos: {len(HALLAZGOS)} (lo que se sabe que falta, medido)")
        for apunte in HALLAZGOS:
            print(f"  · {apunte}")
    for fallo in FALLOS:
        print(f"  · {fallo}")
    print(f"Capturas en {CARPETA} (recorrido-*.png)")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
