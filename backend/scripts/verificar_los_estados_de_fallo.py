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


def el_texto_quieto(nav, segundos: float = 25.0) -> str:
    """***El texto de la pantalla, cuando ya no cambia*** (21/10/2026).

    *Antes se esperaba un tiempo fijo -`_ = el_texto_quieto(nav)`-, y eso hace **pruebas intermitentes**: la primera pasada
    de este mismo guion fallo una vez y a la siguiente paso, sin tocar nada. **Una prueba que a veces pasa no prueba
    nada.***

    *Aqui se espera a que el texto sea el mismo dos veces seguidas: la pantalla ha terminado de pintarse de
    verdad.*
    """
    anterior = ""
    for _ in range(int(segundos / 0.4)):
        actual = el_texto(nav)
        if actual and actual == anterior:
            return actual
        anterior = actual
        time.sleep(0.4)
    return el_texto(nav)


def esperar_a_que_aparezca(nav, lo_que_busca: str, segundos: float = 15.0) -> str:
    """***Espera a que ese texto este en la pantalla, y devuelve lo ultimo que se leyo*** (21/10/2026).

    *La lectura de un instante no vale: la pantalla **se pinta mas de una vez** -primero sin datos, despues con lo
    que ha contestado el servidor- y a veces redirige. **Medido**: la comprobacion de las campañas fallaba una vez de
    cada dos, sin tocar nada.*

    *Una prueba que a veces pasa no prueba nada, asi que se espera **a que aparezca**, que es lo que se quiere saber,
    y se falla con el ultimo texto leido si no llega.*
    """
    el_ultimo = ""
    for _ in range(int(segundos / 0.4)):
        el_ultimo = el_texto(nav)
        if lo_que_busca in el_ultimo:
            return el_ultimo
        time.sleep(0.4)
    return el_ultimo


def abrir_y_esperar(nav, el_proxy: str, camino: str, lo_que_busca: str, intentos: int = 3) -> str:
    """***Abre la pantalla y espera a que diga lo que se busca, reintentando*** (21/10/2026).

    *Todo pasa por el proxy, y a veces una carga de pagina se queda a medias: la pantalla se queda en la de entrar o
    a medio pintar. Se vio porque **cada pasada fallaba una pantalla distinta** -analisis, campañas, emitidas- sin
    tocar nada: **el fallo era del instrumento, no de la aplicacion**.*

    *Se reintenta la navegacion, no la comprobacion: si el texto aparece, aparece; lo que puede fallar es que la
    pagina llegue a pintarse.*
    """
    el_ultimo = ""
    for _ in range(intentos):
        nav.abrir(f"{el_proxy}/{camino}", esperar=3.0)
        for _ in range(30):
            if el_texto(nav):
                break
            time.sleep(0.5)
        el_ultimo = esperar_a_que_aparezca(nav, lo_que_busca, segundos=12.0)
        if lo_que_busca in el_ultimo:
            return el_ultimo
    return el_ultimo


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
                _ = el_texto_quieto(nav)
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
                _ = el_texto_quieto(nav)
                el_suyo = esperar_a_que_aparezca(nav, "no es que no tengas")
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

    # ---------------------------------------------------------------- 3 · el cuaderno
            print("\n3. EL CUADERNO, CON UNA DE SUS TRES CARGAS FALLANDO")
            with el_proxy_que_falla(direccion, "/api/labores") as el_proxy:
                _poner_la_sesion(nav, el_proxy, cuenta["token"])
                nav.abrir(f"{el_proxy}/#/cuaderno", esperar=3.0)
                for _ in range(30):
                    if el_texto(nav):
                        break
                    time.sleep(0.5)
                _ = el_texto_quieto(nav)
                el_cuaderno = esperar_a_que_aparezca(nav, "no está completo")
                fallos += not comprobar(
                    # ***El cuaderno tiene su frase propia***, y es mejor que la generica: no dice «no es que no
                    # tengas» -que ahi no encaja- sino **«lo que ves no esta completo»**, que es lo que pasa.
                    "no está completo" in el_cuaderno,
                    "***el cuaderno dice que lo que se ve NO ESTA COMPLETO***",
                    el_cuaderno,
                )
                fallos += not comprobar(
                    "labores y cosechas" in el_cuaderno,
                    "***y dice CUAL falta: las labores***",
                    el_cuaderno,
                )

            # ---------------------------------------------------------------- 4 · facturas emitidas
            print("\n4. LAS FACTURAS EMITIDAS, CON SU CARGA FALLANDO")
            with el_proxy_que_falla(direccion, "/api/facturas-emitidas") as el_proxy:
                _poner_la_sesion(nav, el_proxy, cuenta["token"])
                # ***Se llega desde ventas***: *la lista de facturas emitidas **no tiene direccion propia** -ni
                # `#/facturas_emitidas` ni `#/facturas-emitidas` abren nada-, se abre con su boton. **Y asi es como
                # llega el agricultor**, que es lo que hay que comprobar.*
                nav.abrir(f"{el_proxy}/#/ventas", esperar=3.0)
                time.sleep(1.5)
                nav.evaluar(
                    "(() => { const b = document.querySelector('[data-accion=\"facturas-emitidas-ver\"]');"
                    " if (b) b.click(); return Boolean(b); })()"
                )
                for _ in range(20):
                    time.sleep(0.5)
                    if "factura" in el_texto(nav).lower():
                        break
                time.sleep(1.5)
                el_emitidas = esperar_a_que_aparezca(nav, "no es que no tengas ninguna")
                fallos += not comprobar(
                    "no es que no tengas ninguna" in el_emitidas,
                    "***las facturas emitidas dicen que no se pudieron cargar***",
                    el_emitidas,
                )

            # ---------------------------------------------------------------- 5 y 6 · analisis y grupos
            for numero, nombre, clave_api, camino in (
                (5, "LOS ANALISIS", "/api/analiticas", "#/analisis"),
                (6, "LOS GRUPOS", "/api/grupos", "#/grupos"),
            ):
                print(f"\n{numero}. {nombre}, CON SU CARGA FALLANDO")
                with el_proxy_que_falla(direccion, clave_api) as el_proxy:
                    _poner_la_sesion(nav, el_proxy, cuenta["token"])
                    el_suyo = abrir_y_esperar(nav, el_proxy, camino, "no es que no tengas")
                    fallos += not comprobar(
                        "no es que no tengas" in el_suyo,
                        f"***{nombre.lower()} dicen que no se pudieron cargar***",
                        el_suyo,
                    )

            # ---------------------------------------------------------------- 7 a 9 · cultivos, cesta, anos
            for numero, nombre, clave_api, camino in (
                (7, "LOS CULTIVOS", "/api/cultivos", "#/cultivos"),
                (8, "LA CESTA DE PRODUCTOS", "/api/productos/cesta/situacion", "#/almacen"),
                (9, "LAS CAMPANAS", "/api/campanas", "#/anos"),
            ):
                print(f"\n{numero}. {nombre}, CON SU CARGA FALLANDO")
                with el_proxy_que_falla(direccion, clave_api) as el_proxy:
                    _poner_la_sesion(nav, el_proxy, cuenta["token"])
                    el_suyo = abrir_y_esperar(nav, el_proxy, camino, "no es que no tengas")
                    fallos += not comprobar(
                        "no es que no tengas" in el_suyo,
                        f"***{nombre.lower()} dicen que no se pudieron cargar***",
                        el_suyo,
                    )

    print(f"\nComprobaciones: {13}   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
