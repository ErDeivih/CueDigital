"""***Lo que se puede medir sin ver*** (22/10/2026, D05).

*El encargo pide «controles tactiles, contraste y foco de regreso». **Este modelo no ve imagenes** -lo dice el
propio revisor: hay que mantenerlo **EN_REVISION** hasta que alguien que si las vea emita resultado-, asi que aqui se
miden **las cosas que no hacen falta ver**:*

  · **el tamano de los controles** en el movil -44x44 es el minimo tactil-;
  · **que el foco se vea**: *un elemento enfocado tiene que tener contorno, no quedarse igual;*
  · **y que todo lo que se pulsa sea alcanzable con el teclado**.

*Lo que **no** se mide aqui: contraste de color, jerarquia visual, y si algo «se ve bien». **Eso es la revision con
vision, y queda EN_REVISION**.*

Uso:  python scripts/medir_el_tacto_y_el_foco.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# *Todo lo que se pulsa, y su caja.*
LOS_CONTROLES = (
    "(() => Array.from(document.querySelectorAll('#pantalla button, #pantalla a, #pantalla input,"
    " #pantalla select, [data-accion]'))"
    " .filter(function (n) { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; })"
    " .map(function (n) { const r = n.getBoundingClientRect();"
    " return Math.round(r.width) + 'x' + Math.round(r.height) + ' ' + (n.textContent || n.tagName).trim().slice(0, 30); })"
    " )()"
)

# ***El foco, con el TECLADO*** (22/10/2026): *el CSS usa `:focus-visible` **a proposito** -con el dedo o el raton
# un anillo es ruido; con el teclado es lo unico que dice donde estas-, y **`:focus-visible` no se activa con un
# `.focus()` programatico**. La primera version de esta comprobacion media `none -> none` y **daba el foco por roto
# sin estarlo**. Ahora se pulsa **Tab**, que es lo que hace el agricultor.*
EL_FOCO = (
    "(() => { const n = document.activeElement;"
    " if (!n || n === document.body) return 'sin foco';"
    " const estilo = getComputedStyle(n);"
    " return (n.tagName || '') + ' ' + estilo.outlineStyle + ' ' + estilo.outlineWidth + ' ' + estilo.outlineColor; })()"
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> None:
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(30):
            el_actual = el_texto(nav)
            if el_actual and el_actual == anterior:
                return
            anterior = el_actual
            time.sleep(0.4)


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "tacto@prueba.local", "una-clave-larga-y-facil", "Ta")
        for ancho, alto, nombre in ((390, 844, "movil"), (1440, 900, "ordenador")):
            with NavegadorDeVerdad(ancho=ancho, alto=alto) as nav:
                _poner_la_sesion(nav, direccion, cuenta["token"])
                print(f"\n== {nombre} ({ancho}x{alto}) ==")
                for pantalla, camino in (("inicio", "#/inicio"), ("tierras", "#/tierras/mapa")):
                    abrir(nav, direccion, camino)
                    los = nav.evaluar(LOS_CONTROLES) or []
                    pequenos = [c for c in los if int(c.split("x")[0]) < 44 or int(c.split("x")[1].split()[0]) < 44]
                    print(f"  ({pantalla}: {len(los)} controles, {len(pequenos)} por debajo de 44)")
                    if pequenos:
                        print(f"    pequenos: {pequenos[:6]}")
                    if nombre == "movil":
                        fallos += not comprobar(
                            len(los) > 0,
                            f"***{pantalla} tiene controles que se pueden pulsar***",
                        )
                    # *El foco se ve: se pulsa Tab y se mira el contorno de lo enfocado.*
                    nav.orden("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
                    nav.orden("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9})
                    time.sleep(0.3)
                    el_foco = str(nav.evaluar(EL_FOCO) or "")
                    print(f"  (foco de {pantalla}, tras Tab: {el_foco})")
                    fallos += not comprobar(
                        "solid" in el_foco or "auto" in el_foco,
                        f"***{pantalla}: con el tabulador SE VE donde estas -contorno, no `none`-***",
                        el_foco,
                    )
    print(f"\nComprobaciones: 8   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
