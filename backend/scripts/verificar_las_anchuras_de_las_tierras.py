"""***Las tres anchuras de las tierras*** (22/10/2026, D04).

*El encargo pide que, **en 1440x900, 1024 y movil**, la lista y el mapa representen el mismo conjunto. La vista usa
**una sola lista** y el CSS decide la forma -tabla en el ordenador, otra cosa en el movil-, asi que lo que se mide es
**lo que se ve**: las filas de la tabla o los renglones de la lista, lo que este visible en cada anchura.*

Uso:  python scripts/verificar_las_anchuras_de_las_tierras.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# *Lo que se cuenta: lo que **se ve**. Un `tr` escondido por el CSS no cuenta, y un renglon de lista tampoco si no se
# ve.*
# ***Solo las filas de la tabla de las tierras.*** *Se probo a contar tambien los `ul > li` y salian **4 siempre**
# -listas que no son las tierras: leyenda, botones-, lo que metia ruido en la cuenta. **La vista usa una sola tabla en
# las tres anchuras** -medido: 3 filas a 1440, a 1024 y a 390-, asi que es lo que se cuenta.*
# ***Filas O tarjetas*** (22/10/2026): *la pantalla de las tierras **cambio**: en el ordenador sigue siendo una
# tabla, y **en el movil son tarjetas** -lo pide el encargo: «en movil: tarjetas utiles»-. Contar solo las filas decia
# **0** a 390 px y parecia que no habia tierras. Se cuenta **lo que se ve**, sea fila o tarjeta.*
LOS_VISIBLES = (
    "(() => {"
    " const seVe = (n) => { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; };"
    " const filas = Array.from(document.querySelectorAll('#pantalla table tbody tr')).filter(seVe).length;"
    " const tarjetas = Array.from(document.querySelectorAll('#pantalla .t06-tarjeta')).filter(seVe).length;"
    " return filas + '|' + tarjetas;"
    "})()"
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def los_visibles(nav) -> tuple[int, int, int]:
    """*Cuantas cosas se ven, y **de que forma**: filas, tarjetas, y el total.*"""
    el_crudo = str(nav.evaluar(LOS_VISIBLES) or "0|0")
    las_filas, _, las_tarjetas = el_crudo.partition("|")
    filas, tarjetas = int(las_filas or 0), int(las_tarjetas or 0)
    return filas, tarjetas, filas + tarjetas


def abrir(nav, direccion: str, camino: str) -> str:
    el_ultimo = ""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        for _ in range(30):
            el_ultimo = el_texto(nav)
            if el_ultimo and "no lleva a ninguna parte" not in el_ultimo:
                anterior = el_ultimo
                time.sleep(0.6)
                if el_texto(nav) == anterior:
                    return el_ultimo
        time.sleep(0.5)
    return el_ultimo


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "anchuras@prueba.local", "una-clave-larga-y-facil", "An")
        for i, alias in enumerate(("TIERRA UNO", "TIERRA DOS", "OTRA COSA"), start=1):
            _llamar(
                direccion,
                "/api/parcelas",
                token=cuenta["token"],
                metodo="POST",
                cuerpo={
                    "alias": alias,
                    "ref_sigpac": f"47-002-0-0-{i}",
                    "municipio": "Valladolid",
                    "superficie_ha": 1.5,
                },
            )
        print(f"== Las tres anchuras  ({direccion}) ==")
        for ancho, alto, nombre in ((1440, 900, "ordenador"), (1024, 768, "tableta"), (390, 844, "movil")):
            with NavegadorDeVerdad(ancho=ancho, alto=alto) as nav:
                _poner_la_sesion(nav, direccion, cuenta["token"])
                print(f"\n{nombre} ({ancho}x{alto})")
                todas = abrir(nav, direccion, "#/tierras/mapa")
                # ***Los nombres, distintos***: *antes se hacia `filas, tarjetas, filas = ...` y el **total** pisaba al
                # numero de filas; el aviso decia «3 filas» cuando eran **0 filas y 3 tarjetas**. La aplicacion estaba
                # bien: el contenedor de la tabla tiene `display: none` a esta anchura, y se comprobo.*
                filas, tarjetas, el_total = los_visibles(nav)
                print(f"          (visibles: {filas} filas y {tarjetas} tarjetas -> {el_total})")
                fallos += not comprobar(
                    el_total == 3,
                    f"***se ven las tres tierras*** ({el_total})",
                    todas,
                )
                # *Y con el filtro, dos -lo mismo que en el ordenador.*
                abrir(nav, direccion, "#/tierras/mapa?q=TIERRA")
                filas, tarjetas, el_total = los_visibles(nav)
                print(f"          (con filtro: {filas} filas y {tarjetas} tarjetas -> {el_total})")
                fallos += not comprobar(
                    el_total == 2,
                    f"***con el filtro se ven DOS, tambien aqui*** ({el_total})",
                )
    print(f"\nComprobaciones: 6   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
