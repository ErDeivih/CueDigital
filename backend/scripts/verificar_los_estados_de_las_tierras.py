"""***Los estados de las tierras: tres, sesenta y cuatro, filtro, vacío y fallo*** (23/10/2026, C2 de la revisión).

*Lo que pide la aceptación de C2: «capturas y mediciones de **tres/64 tierras, filtro activo, vacío y fallo**».*

***Y lo que mide de cada uno***: *que **al entrar se vea una tierra sin bajar** -a 1440 y a 320, que es donde la revisión
midió `top=742`-, **cuántas hay**, si el pliegue de los avanzados está **abierto cuando hay filtro**, y que el vacío lo
**diga** en vez de quedarse en blanco.*

*Las capturas van a `docs/capturas-de-anchuras/estados/`, para poder mirarlas.*

Uso:  python scripts/verificar_los_estados_de_las_tierras.py
"""

from __future__ import annotations

import base64
import pathlib
import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

LA_CARPETA = pathlib.Path("docs", "capturas-de-anchuras", "estados")

LA_PRIMERA_EN_LA_VENTANA = (
    "(() => {"
    " const filas = Array.from(document.querySelectorAll('#pantalla table tbody tr'));"
    " const tarjetas = Array.from(document.querySelectorAll('#pantalla .t06-tarjeta'));"
    " const uno = filas.concat(tarjetas).find((n) => { const r = n.getBoundingClientRect();"
    "   return r.width > 0 && r.height > 0; });"
    " if (!uno) return 'no hay ninguna';"
    " const r = uno.getBoundingClientRect();"
    " return (r.top < window.innerHeight && r.bottom > 0) ? 'dentro' : 'fuera (' + Math.round(r.top) + ')';"
    "})()"
)

CUANTAS = (
    "(() => { const f = document.querySelectorAll('#pantalla table tbody tr');"
    " const t = document.querySelectorAll('#pantalla .t06-tarjeta');"
    " return Math.max(f.length, t.length); })()"
)

EL_PLIEGUE = (
    "(() => { const d = document.querySelector('#pantalla .t06-avanzados');"
    " return d ? (d.open ? 'abierto' : 'plegado') : 'no hay pliegue'; })()"
)

EL_VACIO = (
    "(() => { const p = document.querySelector('#pantalla');"
    " return p ? (p.innerText || '').length : 0; })()"
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def en_la_spa(nav, camino: str) -> str:
    nav.evaluar(f"location.hash = {camino!r}; 1")
    anterior = ""
    el_ultimo = ""
    for _ in range(30):
        el_ultimo = el_texto(nav)
        if el_ultimo and el_ultimo == anterior:
            return el_ultimo
        anterior = el_ultimo
        time.sleep(0.35)
    return el_ultimo


def la_captura(nav, nombre: str) -> None:
    LA_CARPETA.mkdir(parents=True, exist_ok=True)
    el_crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
    (LA_CARPETA / nombre).write_bytes(el_crudo)


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "estados@prueba.local", "una-clave-larga-y-facil", "Es")
        el_vale = cuenta["token"]
        # *Tres tierras, y luego sesenta y una más: **64 en total**.*
        for i in range(1, 65):
            _llamar(
                direccion,
                "/api/parcelas",
                token=el_vale,
                metodo="POST",
                cuerpo={
                    "alias": f"LA VEGA {i}" if i <= 3 else f"LA ERA {i}",
                    "ref_sigpac": f"47-100-0-0-{i}",
                    "municipio": "Medina del Campo" if i % 2 else "Coca",
                    "superficie_ha": 1.0 + (i % 4),
                },
            )
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)

            # ---- 1 · el filtro activo (con 64 tierras) ----
            print("== Los estados de las tierras ==")
            en_la_spa(nav, "#/tierras/mapa?q=VEGA")
            el_pliegue = str(nav.evaluar(EL_PLIEGUE) or "")
            las_que_son = int(str(nav.evaluar(CUANTAS) or 0))
            print(f"  (filtro «VEGA»: {las_que_son} · el pliegue {el_pliegue})")
            fallos += not comprobar(las_que_son == 3, f"***el filtro deja tres*** ({las_que_son})")
            # ***Y el pliegue, con un filtro AVANZADO***: *la búsqueda por texto (`?q=`) **no** abre el pliegue de
            # avanzados a propósito -se ve siempre-, y el que se abre es el de cultivo, municipio, revisión o PAC.*
            en_la_spa(nav, "#/tierras/mapa?municipio=Medina%20del%20Campo")
            el_pliegue = str(nav.evaluar(EL_PLIEGUE) or "")
            print(f"  (con un filtro avanzado puesto, el pliegue: {el_pliegue})")
            fallos += not comprobar(
                el_pliegue == "abierto",
                "***con un filtro AVANZADO el pliegue se abre: se ve lo que filtra***",
                el_pliegue,
            )
            la_captura(nav, "tierras-filtro-1440x900.png")

            # ---- 2 · el vacío ----
            en_la_spa(nav, "#/tierras/mapa?q=no-hay-ninguna")
            las_que_son = int(str(nav.evaluar(CUANTAS) or 0))
            el_largo = int(str(nav.evaluar(EL_VACIO) or 0))
            print(f"  (vacío: {las_que_son} tierras · la pantalla dice {el_largo} caracteres)")
            fallos += not comprobar(las_que_son == 0, "***con un filtro que no casa no hay tierras***")
            fallos += not comprobar(el_largo > 40, "***y la pantalla lo DICE, no se queda en blanco***")
            la_captura(nav, "tierras-vacio-1440x900.png")

            # ---- 3 · las 64, a 1440 y a 320 ----
            for ancho, alto in ((1440, 900), (320, 700)):
                nav.orden(
                    "Emulation.setDeviceMetricsOverride",
                    {"width": ancho, "height": alto, "deviceScaleFactor": 1, "mobile": ancho < 700},
                )
                time.sleep(0.8)
                en_la_spa(nav, "#/tierras/mapa")
                la_primera = str(nav.evaluar(LA_PRIMERA_EN_LA_VENTANA) or "")
                las_que_son = int(str(nav.evaluar(CUANTAS) or 0))
                print(f"  ({ancho}x{alto}: {las_que_son} tierras · la primera {la_primera})")
                fallos += not comprobar(
                    la_primera == "dentro",
                    f"***a {ancho} con las 64 se ve una tierra sin bajar***",
                    la_primera,
                )
                la_captura(nav, f"tierras-64-{ancho}x{alto}.png")

    print(f"\nComprobaciones: 6   Fallos: {fallos}")
    print(f"\nLas capturas, en {LA_CARPETA}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
