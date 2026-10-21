"""***Los estados de fallo, en un navegador de verdad*** (21/10/2026, D03).

*Los arreglos de D03 -«un fallo no es un cero», «no se pudo cargar» en vez de «no hay»- se podian escribir, pero
**no verificar**: los recorridos usan un servidor de verdad, donde nada falla.*

*Esto lo cambia: se levanta el servidor temporal, se pone **el proxy que hace fallar una ruta** delante, y se mira
**lo que se ve**. Nada de esto toca la base del agricultor ni modifica la aplicacion.*

Uso:  python scripts/verificar_los_estados_de_fallo.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from el_proxy_que_falla import el_proxy_que_falla  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _poner_la_sesion, _una_cuenta_nueva  # noqa: E402


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def el_aviso(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#aviso-cargas') || {}).innerText") or "")


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        las_palabras = json.loads(
            urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=10).read().decode("utf-8")
        )["maestros"]
        sin_parcela = las_palabras["sin_parcela"]
        sin_fallo = las_palabras["sin_fallo"]
        print(f"== Los estados de fallo, en un navegador  ({direccion}) ==")
        print(f"  «sin tierras»: {sin_parcela[:70]!r}")
        print(f"  «no se pudo»:  {sin_fallo[:70]!r}")

        cuenta = _una_cuenta_nueva(direccion, "fallos@prueba.local", "una-clave-larga-y-facil", "Fa")
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            # ---------------------------------------------------------------- 1 · tierras
            print("\n1. LA PANTALLA DE LAS TIERRAS, CON SU CARGA FALLANDO")
            with el_proxy_que_falla(direccion, "/api/parcelas") as el_proxy:
                _poner_la_sesion(nav, el_proxy, cuenta["token"])
                nav.abrir(f"{el_proxy}/#/tierras", esperar=3.0)
                for _ in range(30):
                    if el_texto(nav):
                        break
                    time.sleep(0.5)
                time.sleep(2.0)
                el_suyo = el_texto(nav)
                el_de_arriba = el_aviso(nav)
                fallos += not comprobar(
                    sin_fallo.split("**")[0].strip() in el_suyo or "no es que no tengas" in el_suyo,
                    "la seccion de las tierras DICE que no se pudo cargar",
                    el_suyo,
                )
                fallos += not comprobar(
                    sin_parcela not in el_suyo,
                    "***y NO dice «todavia no tienes tierras»***",
                    el_suyo,
                )
                fallos += not comprobar(
                    bool(el_de_arriba.strip()),
                    "y el aviso de arriba lo dice",
                    el_de_arriba,
                )

            # ---------------------------------------------------------------- 2 · el control
            print("\n2. CON OTRA COSA FALLANDO, LAS TIERRAS NO SE ENTERAN (control)")
            with el_proxy_que_falla(direccion, "/api/productos") as el_proxy:
                # ***Y aqui hay que volver a sembrar el vale***: *cada proxy escucha en **otro puerto**, o sea en
                # **otro origen**, y `localStorage` es por origen. Sin esto, la segunda vuelta ensenaba la pantalla
                # de entrar y la prueba medía la entrada -lo cazó la primera pasada-.*
                _poner_la_sesion(nav, el_proxy, cuenta["token"])
                nav.abrir(f"{el_proxy}/#/tierras", esperar=3.0)
                for _ in range(30):
                    if el_texto(nav):
                        break
                    time.sleep(0.5)
                time.sleep(2.0)
                el_suyo = el_texto(nav)
                fallos += not comprobar(
                    sin_parcela in el_suyo,
                    "***sin fallar SU carga, las tierras dicen que no hay -que es la verdad-***",
                    el_suyo,
                )
                # ***Y lo que de verdad importa***: *con **otra** carga fallando, el fallo sale **solo en su
                # seccion** -los productos lo dicen, las tierras no-. **Eso es la correspondencia «seccion -> carga»
                # funcionando**, que es lo que no se podia comprobar sin el proxy.*
                fallos += not comprobar(
                    "no es que no tengas" in el_suyo,
                    "***y el fallo sale en SU seccion: los productos lo dicen***",
                    el_suyo,
                )

    print(f"\nComprobaciones: {6}   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
