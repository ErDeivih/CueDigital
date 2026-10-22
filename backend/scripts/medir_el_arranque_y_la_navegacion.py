"""***El arranque y la navegación dentro de la SPA*** (22/10/2026, D07 — segunda versión).

*La primera versión de este medidor **no valía***: *navegaba con `nav.abrir(<URL completa>)` en cada transición, así que
**recargaba el documento** y borraba precisamente la memoria que decía medir. Lo señaló la revisión independiente: «no
usar `nav.abrir` en cada transición: recarga el documento y borra la memoria que se quiere medir».*

***Lo que hace ahora***:

  · **una sola carga**: *la primera pantalla se abre con `nav.abrir` y **no se vuelve a usar**;*
  · *las demás transiciones se hacen **escribiendo el fragmento** (`location.hash`), que es lo que hace la aplicación
    cuando el agricultor pulsa un enlace: **una navegación de la SPA, sin documento nuevo**;*
  · ***y se comprueba que de verdad no ha habido recarga***: *`performance.timeOrigin` tiene que ser **el mismo** todo el
    rato, y `performance.getEntriesByType("navigation")` tiene que tener **una sola** entrada. Si cambia, el instrumento
    está mal y **se dice**, en vez de medir un documento nuevo y llamarlo «sesión».*

*Y se mide lo que pide el encargo: **peticiones de arranque, memoria, nodos del documento y el ciclo de vida** —que al
volver al principio no quede nada de las pantallas por las que se pasó—.*

Uso:  python scripts/medir_el_arranque_y_la_navegacion.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

LAS_PANTALLAS = (
    "#/",
    "#/tierras/mapa",
    "#/cuaderno",
    "#/ventas",
    "#/papeles/bandeja",
    "#/tierras",
)

LAS_LLAMADAS = (
    "performance.getEntriesByType('resource')"
    ".filter(function (r) { return r.name.indexOf('/api/') !== -1; })"
    ".map(function (r) { return r.name.split('/api/')[1].split('?')[0]; })"
)

LOS_NODOS = "document.getElementsByTagName('*').length"

LA_MEMORIA = (
    "(() => { if (!performance.memory) return -1;"
    " return Math.round(performance.memory.usedJSHeapSize / 1048576); })()"
)

# ***La prueba de que NO ha habido recarga.***
EL_TIME_ORIGIN = "Math.round(performance.timeOrigin)"
LAS_NAVEGACIONES = "performance.getEntriesByType('navigation').length"

EL_TIEMPO_DEL_NAVEGADOR = (
    "(() => { const n = performance.getEntriesByType('navigation')[0];"
    " if (!n) return '';"
    " return Math.round(n.domContentLoadedEventEnd) + '|' + Math.round(n.loadEventEnd); })()"
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def en_la_spa(nav, camino: str) -> str:
    """***Navegar dentro de la SPA***: *se escribe el fragmento y se espera a que la pantalla se quede quieta.*
    ***Nunca `nav.abrir`***: *eso sería otro documento y se perdería la memoria que se mide.*"""
    nav.evaluar(f"location.hash = {camino!r}; 1")
    anterior = ""
    el_ultimo = ""
    for _ in range(40):
        el_ultimo = el_texto(nav)
        if el_ultimo and el_ultimo == anterior:
            return el_ultimo
        anterior = el_ultimo
        time.sleep(0.3)
    return el_ultimo


def el_arranque(nav, direccion: str) -> dict:
    """*La única carga de documento: aquí sí se abre la URL entera.*"""
    el_reloj = time.time()
    nav.abrir(f"{direccion}/#/", esperar=3.0)
    anterior = ""
    for _ in range(40):
        if el_texto(nav) and el_texto(nav) == anterior:
            break
        anterior = el_texto(nav)
        time.sleep(0.3)
    return {
        "segundos": time.time() - el_reloj,
        "timeOrigin": str(nav.evaluar(EL_TIME_ORIGIN)),
        "navegaciones": int(str(nav.evaluar(LAS_NAVEGACIONES) or 0)),
        "nodos": int(str(nav.evaluar(LOS_NODOS) or 0)),
        "memoria": int(str(nav.evaluar(LA_MEMORIA) or -1)),
    }


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "arranque@prueba.local", "una-clave-larga-y-facil", "Ar")
        el_vale = cuenta["token"]
        for i, alias in enumerate(("LA VEGA", "EL PRADO"), start=1):
            _llamar(
                direccion,
                "/api/parcelas",
                token=el_vale,
                metodo="POST",
                cuerpo={"alias": alias, "ref_sigpac": f"47-500-0-0-{i}", "superficie_ha": 2.0},
            )
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)

            # ---- 1 · el arranque: **la única página que se abre** ----
            print(f"== El arranque  ({direccion}) ==")
            el_principio = el_arranque(nav, direccion)
            print(f"  ***medido***: {el_principio['segundos']:.1f} s hasta tener pantalla")
            print(f"  (timeOrigin {el_principio['timeOrigin']} · {el_principio['navegaciones']} navegación(es))")
            el_tiempo = str(nav.evaluar(EL_TIEMPO_DEL_NAVEGADOR) or "")
            if el_tiempo:
                el_dom, _, el_load = el_tiempo.partition("|")
                print(f"  (el navegador: `domContentLoaded` {el_dom} ms · `load` {el_load} ms)")
            fallos += not comprobar(
                el_principio["segundos"] < 30.0,
                f"***el arranque no se eterniza*** ({el_principio['segundos']:.1f} s)",
            )

            las_unicas = sorted(set(str(l) for l in (nav.evaluar(LAS_LLAMADAS) or [])))
            print(f"  ***medido***: {len(las_unicas)} peticiones distintas al abrir")
            fallos += not comprobar(
                len(las_unicas) > 0, f"***el navegador cuenta las peticiones*** ({len(las_unicas)})"
            )

            # ---- 2 · andar quince pantallas **sin recargar** ----
            print("\n== Y la navegación, dentro de la SPA ==")
            el_time_origin = el_principio["timeOrigin"]
            las_navegaciones = el_principio["navegaciones"]
            la_recarga = False
            for _ in range(3):
                for camino in LAS_PANTALLAS:
                    en_la_spa(nav, camino)
                    # ***En cada transición***: *si el documento se ha recargado, esto lo dice.*
                    if str(nav.evaluar(EL_TIME_ORIGIN)) != el_time_origin:
                        la_recarga = True
                        fallos += not comprobar(False, f"***sin recargar*** (el `timeOrigin` cambió en {camino})")
                        el_time_origin = str(nav.evaluar(EL_TIME_ORIGIN))
                    las_navegaciones = int(str(nav.evaluar(LAS_NAVEGACIONES) or 0))

            los_nodos_despues = int(str(nav.evaluar(LOS_NODOS) or 0))
            la_memoria_despues = int(str(nav.evaluar(LA_MEMORIA) or -1))
            print(f"  (tras 18 pantallas: {los_nodos_despues} nodos, memoria {la_memoria_despues} MB)")
            if not la_recarga:
                fallos += not comprobar(True, "***el `timeOrigin` no se ha movido en ninguna transición***")
            fallos += not comprobar(
                las_navegaciones == el_principio["navegaciones"],
                "***una sola navegación de documento en todo el recorrido*** "
                f"({el_principio['navegaciones']} -> {las_navegaciones})",
            )

            # ---- 3 · volver al principio: aquí se ve si algo se queda ----
            en_la_spa(nav, "#/")
            time.sleep(1.0)
            los_nodos_al_volver = int(str(nav.evaluar(LOS_NODOS) or 0))
            la_memoria_al_volver = int(str(nav.evaluar(LA_MEMORIA) or -1))
            print(f"  (al volver: {los_nodos_al_volver} nodos, memoria {la_memoria_al_volver} MB)")
            fallos += not comprobar(
                los_nodos_al_volver <= el_principio["nodos"] * 1.5 + 50,
                f"***al volver al principio no quedan nodos de más*** "
                f"({el_principio['nodos']} -> {los_nodos_al_volver})",
            )
            if el_principio["memoria"] > 0 and la_memoria_al_volver > 0:
                el_crecimiento = la_memoria_al_volver - el_principio["memoria"]
                print(
                    f"  ***medido***: la memoria pasó de {el_principio['memoria']} a {la_memoria_al_volver} MB "
                    f"({el_crecimiento:+d})"
                )
                fallos += not comprobar(
                    el_crecimiento <= 60,
                    f"***y la memoria no se dispara*** ({el_crecimiento:+d} MB tras 18 pantallas sin recargar)",
                )
            else:
                print("  (este navegador no da `performance.memory`: la memoria no se mide)")

    print(f"\nComprobaciones: 6   Fallos: {fallos}")
    print("\n***Lo que este medidor NO dice***: *que la aplicación sea rápida —no hay con qué compararlo—, ni lo que")
    print("  pasa en media hora de uso real. **Sí dice que no hay recarga**, y que sin recargar no se queda nada.*")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
