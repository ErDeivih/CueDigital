"""***Escape, y el foco de regreso*** (22/10/2026, D05).

*El encargo pide «tabulador/Escape, foco de regreso». La aplicacion tiene el manejador -«Escape cierra lo que este
abierto»- y esto comprueba **lo que casi nadie comprueba**: que al cerrar, **el foco vuelve a donde estaba**, no al
principio de la pagina.*

Uso:  python scripts/verificar_el_escape_y_el_foco.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

EL_FOCO = (
    "(() => { const n = document.activeElement;"
    " if (!n || n === document.body) return 'el cuerpo de la pagina';"
    " return (n.getAttribute('data-accion') || '') + '|' + (n.textContent || n.tagName || '').trim().slice(0, 40); })()"
)
# ***Y se buscan en TODA la pagina***, no solo en `#pantalla`: *el boton de apuntar vive en la barra de arriba
# -`#marco`-, y buscandolo solo en la pantalla no se encontraba.*
LAS_ACCIONES = "Array.from(document.querySelectorAll('[data-accion]')).map(function (n) { return n.getAttribute('data-accion'); })"


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


# ***Se mira el MENU, no `#pantalla`*** (22/10/2026): *el menu vive fuera de la pantalla -es el armazon-, asi que
# el texto de `#pantalla` **no cambia** al abrirlo ni al cerrarlo, y la comprobacion miraba donde no pasaba nada. Se
# cuenta **si su boton de cerrar se ve**: abierto, si; cerrado, no.*
EL_MENU = (
    "Array.from(document.querySelectorAll('[data-accion=\"menu-cerrar\"]'))"
    ".filter(function (n) { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).length"
)


def el_menu_abierto(nav) -> int:
    return int(str(nav.evaluar(EL_MENU) or "0"))


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


def la_tecla(nav, tecla: str, codigo: int) -> None:
    for tipo in ("keyDown", "keyUp"):
        nav.orden(
            "Input.dispatchKeyEvent",
            {"type": tipo, "key": tecla, "code": tecla, "windowsVirtualKeyCode": codigo},
        )


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "escape@prueba.local", "una-clave-larga-y-facil", "Es")
        # ***A anchura de movil***: *el menu que tapa la pantalla es el del movil -en el ordenador esta en una
        # columna y no se abre-. Y es el caso que el codigo documenta: «cerrarlo con Escape es lo que espera
        # cualquiera».*
        with NavegadorDeVerdad(ancho=390, alto=844) as nav:
            _poner_la_sesion(nav, direccion, cuenta["token"])
            print(f"== Escape y foco de regreso  ({direccion}) ==")
            # ***El inicio es la RAIZ***, no `#/inicio`: *`#/inicio` contesta «esa direccion no lleva a ninguna
            # parte» -lo dijo la comprobacion, leyendo el texto de la pantalla-.*
            abrir(nav, direccion, "#/")
            las = nav.evaluar(LAS_ACCIONES) or []
            print(f"  (acciones en el inicio: {las})")
            # ***Se abre el menu***, que es lo que tapa la pantalla en el movil y lo que Escape tiene que cerrar.
            la_de_apuntar = next((a for a in las if str(a) == "menu-abrir"), None)
            if la_de_apuntar is None:
                fallos += not comprobar(False, "***no encuentro con que abrir el menu***", str(las))
            else:
                # *Se enfoca y se pulsa, como haria el teclado.*
                nav.evaluar(
                    "(() => { const b = document.querySelector('[data-accion=\""
                    + str(la_de_apuntar)
                    + "\"]'); if (b) b.focus(); if (b) b.click(); return Boolean(b); })()"
                )
                time.sleep(1.2)
                print(f"  (tras abrir, el foco esta en: {nav.evaluar(EL_FOCO)!r})")
                el_abierto = el_menu_abierto(nav)
                print(f"  (menu abierto: {el_abierto})")
                # *Y Escape.*
                la_tecla(nav, "Escape", 27)
                time.sleep(1.0)
                el_despues = el_menu_abierto(nav)
                el_foco = str(nav.evaluar(EL_FOCO) or "")
                print(f"  (tras Escape, el foco esta en: {el_foco!r}; menu: {el_despues})")
                fallos += not comprobar(
                    el_abierto == 1 and el_despues == 0,
                    "***Escape CIERRA el menu que estaba abierto***",
                    f"abierto: {el_abierto} -> despues: {el_despues}",
                )
                fallos += not comprobar(
                    str(la_de_apuntar) in el_foco,
                    f"***y el foco VUELVE al boton que lo abrio*** (foco: {el_foco!r})",
                )
    print(f"\nComprobaciones: 2   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
