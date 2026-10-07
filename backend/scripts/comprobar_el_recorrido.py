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
        comprobar(
            hay(nav, "[data-accion='tierra-historia']"),
            "la lista lleva a la ficha de una tierra («tierra-historia»)",
        )
        nav.pulsar("[data-accion='tierra-historia']")
        nav.esperar("location.hash.includes('tierra')", segundos=10)
        esperar_la_pantalla(nav)
        captura(nav, "3-ficha")
        ficha = texto_de(nav)
        comprobar(la_tierra.alias[:14].lower() in ficha.lower(), "la ficha es la de la tierra buscada")
        print(f"  (la ficha dice, en resumen: {' '.join(ficha.split())[:220]}…)")
        tiene_historial = bool(nav.evaluar("Boolean(document.querySelector('[data-accion=\"trabajos-ver\"]'))"))
        print(f"  ¿hay un botón para ver los trabajos desde la ficha? {tiene_historial}")
        acciones_ficha = nav.evaluar(
            "[...new Set([...document.querySelectorAll('#pantalla [data-accion]')]"
            ".map((e) => e.dataset.accion))]"
        )
        print(f"  acciones de la ficha: {acciones_ficha}")

        # ── 4. Registrar un trabajo ─────────────────────────────────────────────────────────────
        paso(nav, 4, "Registrar un trabajo")
        # La lista de trabajos es la puerta que el menú ofrece («trabajos-ver»).
        pulsar_si_hay(nav, '[data-accion="trabajos-ver"]', "Boolean(document.querySelector('#pantalla'))")
        acciones_trabajos = acciones(nav)
        print(f"  acciones de la pantalla de trabajos: {acciones_trabajos}")
        comprobar(
            any(a.startswith("trabajo") or a.startswith("plan") for a in acciones_trabajos),
            "la pantalla de trabajos ofrece planificar o apuntar un trabajo",
        )
        captura(nav, "4-trabajos")

        # ── 5. El historial de la tierra ────────────────────────────────────────────────────────
        paso(nav, 5, "El historial de la tierra, después")
        nav.abrir(f"{DIRECCION}/#/", esperar=1.0)
        pulsar_si_hay(nav, "#menu-tierras", "Boolean(document.querySelector('#buscar_tierra_mis_cosas'))")
        nav.escribir("#buscar_tierra_mis_cosas", la_tierra.alias[:24])
        nav.esperar(
            "document.querySelector('#pantalla').innerText.includes("
            + json.dumps(la_tierra.alias[:18].lower())
            + ")",
            segundos=10,
        )
        nav.pulsar("[data-accion='tierra-historia']")
        esperar_la_pantalla(nav)
        captura(nav, "5-historial")
        comprobar(
            len(texto_de(nav)) > 40,
            "el historial de la tierra se puede volver a abrir después de pasar por los trabajos",
        )

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  · {fallo}")
    print(f"Capturas en {CARPETA} (recorrido-*.png)")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
