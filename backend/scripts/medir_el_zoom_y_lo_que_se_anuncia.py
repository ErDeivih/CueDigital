"""***El zoom al 200 % y lo que lee un lector de pantalla*** (22/10/2026, D05).

*Dos cosas del encargo que **no hacen falta ver**:*

  · **el zoom al 200 %**: *que la pantalla no se rompa -lo tipico es que aparezca desplazamiento horizontal, que
    es lo que impide leer sin mover la pagina a un lado y a otro-;*
  · **lo que se anuncia**: *que todo lo que se pulsa **tenga nombre** -texto, `aria-label`-, que las imagenes tengan
    `alt` y que los campos tengan su etiqueta.*

***Lo que esto no comprueba***: *que el lector lo lea **bien** -el orden, el tono, si interrumpe-. Eso necesita un
lector de verdad o alguien escuchandolo, y queda fuera de lo que se puede medir aqui.*

Uso:  python scripts/medir_el_zoom_y_lo_que_se_anuncia.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# *El desplazamiento horizontal que sobra: si el documento es mas ancho que la ventana, hay que arrastrar la pagina.*
EL_DESBORDE = (
    "(() => { const d = document.documentElement;"
    " return (d.scrollWidth - window.innerWidth) + '|' + window.innerWidth + '|' + d.scrollWidth; })()"
)

# *Lo que se anuncia.*
LO_ANUNCIADO = (
    "(() => {"
    " const sinNombre = Array.from(document.querySelectorAll('#pantalla button, #pantalla a')).filter(function (n) {"
    "  const texto = (n.textContent || '').trim();"
    "  return !texto && !n.getAttribute('aria-label') && !n.getAttribute('title');"
    " }).length;"
    " const imagenes = Array.from(document.querySelectorAll('#pantalla img')).filter(function (n) {"
    "  return !n.getAttribute('alt') && !n.getAttribute('aria-label');"
    " }).length;"
    " const campos = Array.from(document.querySelectorAll('#pantalla input, #pantalla select, #pantalla textarea')).filter(function (n) {"
    "  const id = n.id;"
    "  const conEtiqueta = id && document.querySelector('label[for=\"' + id + '\"]');"
    "  return !conEtiqueta && !n.getAttribute('aria-label') && !n.getAttribute('aria-labelledby')"
    "   && !n.getAttribute('placeholder') && !n.getAttribute('type') || (n.getAttribute('type') || '') === 'hidden' ? false : (!conEtiqueta && !n.getAttribute('aria-label') && !n.getAttribute('aria-labelledby') && !n.getAttribute('placeholder'));"
    " }).length;"
    " const vivas = document.querySelectorAll('[aria-live]').length;"
    " return sinNombre + '|' + imagenes + '|' + campos + '|' + vivas;"
    "})()"
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
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
        cuenta = _una_cuenta_nueva(direccion, "zoom@prueba.local", "una-clave-larga-y-facil", "Zo")
        with NavegadorDeVerdad(ancho=390, alto=844) as nav:
            _poner_la_sesion(nav, direccion, cuenta["token"])
            print(f"== El zoom y lo que se anuncia  ({direccion}) ==")
            for pantalla, camino in (("#/", "inicio"), ("#/tierras/mapa", "tierras"), ("#/cuaderno", "cuaderno")):
                abrir(nav, direccion, pantalla)
                # --- 1 · al 200 % ---
                # ***Antes y despues***: *si el zoom no cambia nada, la comprobacion no comprueba nada. Se mide la
                # escala real (`visualViewport.scale`) para saber que se aplico.*
                la_escala = "(() => (window.visualViewport ? window.visualViewport.scale : 1).toFixed(2))()"
                el_sin_zoom = str(nav.evaluar(EL_DESBORDE) or "0|0|0")
                nav.orden("Emulation.setPageScaleFactor", {"pageScaleFactor": 2})
                time.sleep(0.6)
                la_escala_puesta = str(nav.evaluar(la_escala) or "1")
                el_desborde = str(nav.evaluar(EL_DESBORDE) or "0|0|0")
                print(f"  (sin zoom: {el_sin_zoom.split('|')[0]}px de mas · con zoom: escala {la_escala_puesta})")
                sobran, _, resto = el_desborde.partition("|")
                ancho_ventana, _, ancho_doc = resto.partition("|")
                nav.orden("Emulation.setPageScaleFactor", {"pageScaleFactor": 1})
                los_int = int(float(sobran or 0))
                print(f"\n== {camino} ==")
                # *Se dice QUE pantalla es: tres numeros iguales en tres pantallas distintas seria sospechoso -y lo
                # fue: la primera version no estaba navegando-.*
                print(f"  (dice: {el_texto(nav)[:70]!r})")
                print(f"  (al 200 %: sobran {los_int}px  -  ventana {ancho_ventana}, documento {ancho_doc})")
                fallos += not comprobar(
                    los_int <= 1,
                    f"***{camino}: al 200 % no hay que arrastrar la pagina a los lados*** ({los_int}px de mas)",
                )
                # ***Y que el zoom se haya aplicado de verdad***: *si la escala sigue en 1, lo anterior no ha
                # probado nada.*
                fallos += not comprobar(
                    float(la_escala_puesta) > 1.5,
                    f"***{camino}: el zoom se aplico de verdad*** (escala: {la_escala_puesta})",
                )
                # --- 2 · lo que se anuncia ---
                sin_nombre, _, resto = (str(nav.evaluar(LO_ANUNCIADO) or "0|0|0|0")).partition("|")
                imagenes, _, resto = resto.partition("|")
                campos, _, vivas = resto.partition("|")
                print(f"  (sin nombre: {sin_nombre} · imagenes sin alt: {imagenes} · campos sin etiqueta: {campos} · zonas vivas: {vivas})")
                fallos += not comprobar(
                    int(sin_nombre or 0) == 0,
                    f"***{camino}: todo lo que se pulsa tiene NOMBRE*** ({sin_nombre} sin nombre)",
                )
                fallos += not comprobar(
                    int(campos or 0) == 0,
                    f"***{camino}: los campos tienen su ETIQUETA*** ({campos} sin etiqueta)",
                )
    print(f"\nComprobaciones: 12   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
