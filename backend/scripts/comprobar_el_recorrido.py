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

        # ── 4. Registrar un trabajo ─────────────────────────────────────────────────────────────
        paso(nav, 4, "Registrar un trabajo")
        # La lista de trabajos es la puerta que el menú ofrece («trabajos-ver»).
        pulsar_si_hay(nav, '[data-accion="trabajos-ver"]', "location.hash.includes('trabajos')")
        acciones_trabajos = acciones(nav)
        print(f"  acciones de la pantalla de trabajos: {acciones_trabajos}")
        comprobar(
            "trabajo-planificar" in acciones_trabajos,
            "la pantalla de trabajos ofrece planificar un trabajo",
        )
        captura(nav, "4-trabajos")
        # **Y se abre el formulario de verdad**, que es lo que hace el agricultor para apuntar el trabajo:
        # si el botón estuviera muerto, esto no abriría nada.
        comprobar(
            pulsar_si_hay(
                nav,
                "[data-accion='trabajo-planificar']",
                "document.querySelectorAll('#pantalla input, #pantalla select, #pantalla textarea').length > 0",
            ),
            "«planificar» abre el formulario del trabajo (con sus campos)",
        )
        captura(nav, "4-planificar")
        campos = nav.evaluar(
            "[...document.querySelectorAll('#pantalla input, #pantalla select, #pantalla textarea')]"
            ".map((e) => e.id || e.name || e.type).slice(0, 12)"
        )
        print(f"  campos del formulario: {campos}")
        # Se vuelve a la lista de trabajos sin guardar nada: el recorrido no inventa datos.
        nav.pulsar("[data-accion='trabajo-cancelar']") if hay(
            nav, "[data-accion='trabajo-cancelar']"
        ) else nav.abrir(f"{DIRECCION}/#/trabajos", esperar=1.2)

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
        # **Y lo que queda previsto**, comprobado contra el servidor y no contra el texto de la pantalla:
        # esta tierra puede no tener nada planificado (la primera del escenario no tiene), y entonces lo
        # honesto no es exigir un botón que no puede estar, sino exigirlo **solo si el servidor dice que
        # hay algo previsto**. Así la comprobación dice la verdad en los dos casos.
        previstos = httpx.get(
            f"{DIRECCION}/api/trabajos/tierra/{la_tierra.id}",
            headers={"Authorization": f"Bearer {escenario.volumen.token}"},
            timeout=30.0,
        ).json().get("que_queda_previsto", [])
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

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  · {fallo}")
    print(f"Capturas en {CARPETA} (recorrido-*.png)")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
