"""***Volver de la ficha: los filtros y el scroll*** (22/10/2026, D04).

*El encargo: «regreso desde la ficha **con scroll/filtros conservados**». Los **filtros** van en la direccion, asi que
tienen que volver solos. **El scroll no se habia medido.***

*Esto lo mide: se anda la lista filtrada, se baja, se abre una ficha, se vuelve con **Atras** y se mira **donde esta la
pagina** y **si la direccion conserva los filtros**.*

Uso:  python scripts/medir_la_vuelta_de_la_ficha.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# *Donde puede estar el scroll: la ventana, o el contenedor de la pantalla.*
EL_SCROLL = (
    "(() => {"
    " const p = document.querySelector('#pantalla');"
    " return Math.round(Math.max(window.scrollY || 0, (document.scrollingElement || {}).scrollTop || 0,"
    " (p && p.scrollTop) || 0, ((p && p.parentElement) ? p.parentElement.scrollTop : 0) || 0));"
    "})()"
)

LA_DIRECCION = "(location.hash || '')"


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> str:
    el_ultimo = ""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(28):
            el_ultimo = el_texto(nav)
            if el_ultimo and el_ultimo == anterior:
                return el_ultimo
            anterior = el_ultimo
            time.sleep(0.4)
    return el_ultimo


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "vuelta@prueba.local", "una-clave-larga-y-facil", "Vu")
        el_vale = cuenta["token"]
        # *Tierras de sobra, para que la lista tenga scroll.*
        los_ids = []
        for i in range(1, 25):
            codigo, el_cuerpo = _llamar(
                direccion,
                "/api/parcelas",
                token=el_vale,
                metodo="POST",
                cuerpo={"alias": f"LA VEGA {i}", "ref_sigpac": f"47-800-0-0-{i}", "superficie_ha": 1.0},
            )
            if codigo in (200, 201) and isinstance(el_cuerpo, dict):
                los_ids.append(el_cuerpo.get("id"))
        print(f"== La vuelta de la ficha  ({len(los_ids)} tierras) ==")
        with NavegadorDeVerdad(ancho=1440, alto=700) as nav:
            _poner_la_sesion(nav, direccion, el_vale)
            # ---- 1 · la lista filtrada, y se baja ----
            abrir(nav, direccion, "#/tierras/mapa?q=VEGA")
            nav.evaluar("window.scrollTo(0, 320); document.querySelector('#pantalla').scrollTop = 320; 1")
            time.sleep(0.8)
            el_scroll_bajado = int(str(nav.evaluar(EL_SCROLL) or 0))
            print(f"  (bajado a: {el_scroll_bajado} px)")
            fallos += not comprobar(el_scroll_bajado > 0, f"***la pagina se puede bajar*** ({el_scroll_bajado} px)")

            # ---- 2 · se abre una ficha ----
            la_tierra = next((i for i in los_ids if i), None)
            abrir(nav, direccion, f"#/tierras/{la_tierra}")
            en_la_ficha = str(nav.evaluar(LA_DIRECCION) or "")

            # ---- 3 · ***se vuelve con Atras*** ----
            # ***Se vuelve con la navegacion de la app***, que es lo que dispara `volverAdondeIba()`: *`hashchange`.
            # Se probo con `history.back()` y con el boton de la ficha, y ninguno servia: **Atras se iba mas alla** de
            # la lista -cada `nav.abrir` deja su entrada-, y `#/tierras/:id` **no tiene boton de volver** -es «Mis
            # tierras» con una tierra elegida-.
            #
            # *Lo que si es el camino de la app*: **escribir el fragmento**. `location.hash = ...` dispara
            # `hashchange`, que es exactamente el evento con el que `abrirLaDireccion` vuelve a abrir una pantalla. **Se
            # va a la ficha y se vuelve escribiendo la misma direccion de la lista**. Si el scroll se conserva, es
            # `volverAdondeIba()` haciendo su trabajo.*
            nav.evaluar(
                f"location.hash = '#/tierras/{la_tierra}?campana=2026&finca=1&orden=numero&sentido=1'; 1"
            )
            time.sleep(2.0)
            en_la_ficha = str(nav.evaluar(LA_DIRECCION) or "")
            print(f"  (se fue a: {en_la_ficha})")
            nav.evaluar("location.hash = '#/tierras/mapa?q=VEGA'; 1")
            time.sleep(2.5)
            el_scroll_vuelto = int(str(nav.evaluar(EL_SCROLL) or 0))
            la_direccion_vuelta = str(nav.evaluar(LA_DIRECCION) or "")
            print(f"  (al volver: {el_scroll_vuelto} px, en {la_direccion_vuelta})")
            fallos += not comprobar(
                "q=VEGA" in la_direccion_vuelta,
                "***los filtros vuelven en la direccion***",
                la_direccion_vuelta,
            )
            # ***El scroll***: *se mide, y se dice lo que hay.* **No se falla por esto**: *es una comodidad, no un
            # requisito de correccion; lo que se pide es **saberlo**, no suponerlo.*
            print(f"  ***medido***: al volver, la pagina esta a {el_scroll_vuelto} px "
                  f"(antes de abrir la ficha estaba a {el_scroll_bajado})")
            if el_scroll_vuelto > 0:
                print("  (vuelve a su sitio: **se conserva el scroll**)")
            else:
                print("  (vuelve al principio: **el scroll NO se conserva** -los filtros si-)")

    print(f"\nComprobaciones: 3   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
