"""***Lo que se ve al entrar*** (22/10/2026, C2 de la revisión con visión).

*Lo que decía la revisión: «**en las cinco primeras vistas se ven sobre todo explicación y filtros. Ni a 1440×900
aparece una tierra**: búsqueda, cuatro grupos de opciones y agrupación empujan tabla/tarjetas y mapa hacia abajo».*

*Y su aceptación: «búsqueda y contexto visibles; **filtros avanzados plegables**; filtros activos y acción de quitarlos
reconocibles; **primeras tierras visibles sin atravesar todas las opciones**».*

***Esto mide las tres cosas que se pueden medir sin ojos***: *que la primera tierra **está dentro de la ventana** al
entrar; que los cuatro grupos **no** están a la vista cuando no hay filtro; y que **se abren solos** cuando lo hay, para
que se vea lo que filtra.*

Uso:  python scripts/verificar_lo_que_se_ve_al_entrar.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# ***La primera tierra, dentro de la ventana***: *se mira su caja, no que exista en el documento.*
LA_PRIMERA_EN_LA_VENTANA = (
    "(() => {"
    " const filas = Array.from(document.querySelectorAll('#pantalla table tbody tr'));"
    " const tarjetas = Array.from(document.querySelectorAll('#pantalla .t06-tarjeta'));"
    " const uno = filas.concat(tarjetas).find((n) => { const r = n.getBoundingClientRect();"
    "   return r.width > 0 && r.height > 0; });"
    " if (!uno) return 'no hay ninguna';"
    " const r = uno.getBoundingClientRect();"
    " const alto = window.innerHeight;"
    " return (r.top < alto && r.bottom > 0) ? 'dentro' : 'fuera (' + Math.round(r.top) + ' de ' + alto + ')';"
    "})()"
)

# ***Los cuatro grupos, a la vista o plegados.***
LAS_OPCIONES_A_LA_VISTA = (
    "(() => {"
    " const d = document.querySelector('#pantalla .t06-avanzados');"
    " if (!d) return 'no hay pliegue';"
    " const cajas = Array.from(d.querySelectorAll('select, input')).filter((n) => {"
    "   const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; });"
    " return (d.open ? 'abierto:' : 'plegado:') + cajas.length;"
    "})()"
)

# ***El botón del nombre dentro de la tarjeta***: *área y letra, que es lo que la revisión vio diminuto.*
EL_BOTON_DEL_NOMBRE = (
    "(() => {"
    " const b = document.querySelector('#pantalla .t06-tarjeta .tabla-enlace');"
    " if (!b) return 'no hay';"
    " const r = b.getBoundingClientRect(); const cs = getComputedStyle(b);"
    " return Math.round(r.width) + 'x' + Math.round(r.height) + '|' + parseFloat(cs.fontSize).toFixed(0);"
    "})()"
)

EL_PLIEGUE = (
    "(() => { const d = document.querySelector('#pantalla .t06-avanzados');"
    " return d ? (d.open ? 'abierto' : 'plegado') : 'no hay pliegue'; })()"
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


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "ventana@prueba.local", "una-clave-larga-y-facil", "Ve")
        el_vale = cuenta["token"]
        for i, alias in enumerate(("LA VEGA", "EL PRADO", "LA ERETA"), start=1):
            _llamar(
                direccion,
                "/api/parcelas",
                token=el_vale,
                metodo="POST",
                cuerpo={
                    "alias": alias,
                    "ref_sigpac": f"47-500-0-0-{i}",
                    "municipio": "Medina del Campo" if i == 1 else "Coca",
                    "superficie_ha": 2.0,
                },
            )
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)
            print("== Lo que se ve al entrar  (1440x900) ==")
            en_la_spa(nav, "#/tierras/mapa")

            # ---- 1 · la primera tierra, dentro de la ventana ----
            la_primera = str(nav.evaluar(LA_PRIMERA_EN_LA_VENTANA) or "")
            print(f"  (la primera tierra: {la_primera})")
            fallos += not comprobar(
                la_primera == "dentro",
                "***al entrar se ve una tierra SIN bajar***",
                la_primera,
            )

            # ---- 2 · los grupos, plegados ----
            las_opciones = str(nav.evaluar(LAS_OPCIONES_A_LA_VISTA) or "")
            print(f"  (los grupos: {las_opciones})")
            fallos += not comprobar(
                las_opciones.startswith("plegado"),
                "***los cuatro grupos están plegados cuando no hay filtro***",
                las_opciones,
            )
            fallos += not comprobar(
                las_opciones.endswith(":0"),
                "***y no queda ninguna opción a la vista mientras está plegado***",
                las_opciones,
            )

            # ---- 3 · y se abren solos si hay filtro ----
            en_la_spa(nav, "#/tierras/mapa?cultivo=trigo")
            el_pliegue = str(nav.evaluar(EL_PLIEGUE) or "")
            print(f"  (con un filtro puesto: {el_pliegue})")
            fallos += not comprobar(
                el_pliegue == "abierto",
                "***con un filtro puesto el pliegue se abre solo: se ve lo que filtra***",
                el_pliegue,
            )

            # ---- 4 · y en los móviles, la primera tarjeta también se ve ----
            # *Los dos del diseño: **390×844 y 320×700**. La revisión midió a 320 **top=742 con scroll=0**: o sea, la
            # primera tierra **por debajo** de la ventana.*
            for ancho, alto in ((390, 844), (320, 700)):
                nav.orden(
                    "Emulation.setDeviceMetricsOverride",
                    {"width": ancho, "height": alto, "deviceScaleFactor": 1, "mobile": True},
                )
                time.sleep(1.0)
                en_la_spa(nav, "#/tierras/mapa")
                la_primera_movil = str(nav.evaluar(LA_PRIMERA_EN_LA_VENTANA) or "")
                print(f"  (a {ancho}x{alto}, la primera: {la_primera_movil})")
                fallos += not comprobar(
                    la_primera_movil == "dentro",
                    f"***a {ancho}x{alto} se ve una tarjeta al entrar***",
                    la_primera_movil,
                )
                # ***Y el botón del nombre, con el suelo del diseño.***
                el_boton = str(nav.evaluar(EL_BOTON_DEL_NOMBRE) or "")
                el_area, _, la_letra = el_boton.partition("|")
                el_ancho, _, el_alto = el_area.partition("x")
                try:
                    los_lados = (int(el_ancho), int(el_alto))
                    la_letra_num = float(la_letra)
                except ValueError:
                    los_lados = (0, 0)
                    la_letra_num = 0
                print(f"  (a {ancho}, el botón del nombre: {el_boton})")
                fallos += not comprobar(
                    min(los_lados) >= 44,
                    f"***a {ancho} el botón del nombre llega a 44 de área*** ({el_boton})",
                    el_boton,
                )
                fallos += not comprobar(
                    la_letra_num >= 15,
                    f"***y no se le baja la letra*** ({el_boton})",
                    el_boton,
                )

    print(f"\nComprobaciones: 10   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
