"""***El arranque y la navegacion prolongada*** (22/10/2026, D07).

*El encargo pide «medir navegacion prolongada, peticiones de arranque y memoria». Esto mide las tres cosas, y lo hace
**con el navegador de verdad**:*

  · **las peticiones de arranque**: *cuantas llamadas a `/api/` hace la aplicacion al abrirse, contadas por el propio
    navegador (`performance.getEntriesByType("resource")`), no por una lista que uno recuerde;*
  · **la memoria**: *la del monton de JavaScript (`performance.memory`), antes y despues de andar quince pantallas;*
  · **los nodos del documento**: *cuantos elementos hay, que es lo que delata una pantalla que no se desmonta.*

***Un aviso sobre lo que esto mide***: *un numero mas alto no es un defecto por si solo. **Lo que importa es que al
volver al principio la aplicacion quede como estaba**: si despues de andar quince pantallas y volver al inicio hay
el doble de nodos, algo se esta quedando.*

Uso:  python scripts/medir_el_arranque_y_la_navegacion.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# *Las pantallas por las que se anda. Se repiten tres veces cada una.*
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


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> None:
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=2.5)
        anterior = ""
        for _ in range(25):
            el_actual = el_texto(nav)
            if el_actual and el_actual == anterior:
                return
            anterior = el_actual
            time.sleep(0.35)


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "arranque@prueba.local", "una-clave-larga-y-facil", "Ar")
        el_vale = cuenta["token"]
        # *Unos datos, para que las pantallas no salgan vacias.*
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
            print(f"== El arranque  ({direccion}) ==")
            abrir(nav, direccion, "#/")

            # ---- 1 · las peticiones de arranque ----
            las_llamadas = nav.evaluar(LAS_LLAMADAS) or []
            las_unicas = sorted(set(str(l) for l in las_llamadas))
            print(f"  (peticiones al abrir: {len(las_llamadas)}, {len(las_unicas)} distintas)")
            print(f"  ({', '.join(las_unicas[:14])})")
            fallos += not comprobar(
                len(las_unicas) > 0,
                f"***el navegador cuenta las peticiones de arranque*** ({len(las_unicas)} distintas)",
            )
            # *Y se dice cuantas, sin inventar un limite: es una medida, no un veredicto.*
            print(f"  ***medido***: {len(las_unicas)} peticiones distintas al abrir")

            # ---- 2 · la memoria y los nodos, al principio ----
            los_nodos_al_principio = int(str(nav.evaluar(LOS_NODOS) or 0))
            la_memoria_al_principio = int(str(nav.evaluar(LA_MEMORIA) or -1))
            print(f"  (al principio: {los_nodos_al_principio} nodos, memoria {la_memoria_al_principio} MB)")

            # ---- 3 · andar quince pantallas ----
            for _ in range(3):
                for camino in LAS_PANTALLAS:
                    abrir(nav, direccion, camino)
            los_nodos_despues = int(str(nav.evaluar(LOS_NODOS) or 0))
            la_memoria_despues = int(str(nav.evaluar(LA_MEMORIA) or -1))
            print(f"  (tras andar 18 pantallas: {los_nodos_despues} nodos, memoria {la_memoria_despues} MB)")

            # ---- 4 · volver al principio: ***aqui se ve si algo se queda*** ----
            abrir(nav, direccion, "#/")
            time.sleep(1.0)
            los_nodos_al_volver = int(str(nav.evaluar(LOS_NODOS) or 0))
            la_memoria_al_volver = int(str(nav.evaluar(LA_MEMORIA) or -1))
            print(f"  (al volver: {los_nodos_al_volver} nodos, memoria {la_memoria_al_volver} MB)")
            fallos += not comprobar(
                los_nodos_al_volver <= los_nodos_al_principio * 1.5 + 50,
                f"***al volver al principio no quedan nodos de mas*** "
                f"({los_nodos_al_principio} -> {los_nodos_al_volver})",
            )
            # *La memoria: se avisa de lo que crece, sin fallar por un numero -el recolector de basura decide cuando
            # limpia, y eso no lo controla la aplicacion-.*
            if la_memoria_al_principio > 0 and la_memoria_al_volver > 0:
                el_crecimiento = la_memoria_al_volver - la_memoria_al_principio
                print(f"  ***medido***: la memoria paso de {la_memoria_al_principio} a {la_memoria_al_volver} MB "
                      f"({el_crecimiento:+d})")
                fallos += not comprobar(
                    el_crecimiento <= 60,
                    f"***y la memoria no se dispara*** ({el_crecimiento:+d} MB tras 18 pantallas)",
                )
            else:
                print("  (este navegador no da `performance.memory`: la memoria no se mide)")

    print(f"\nComprobaciones: 4   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
