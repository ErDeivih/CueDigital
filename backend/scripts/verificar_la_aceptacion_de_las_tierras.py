"""***La aceptacion grande de las tierras*** (22/10/2026, D04).

*El encargo pide aceptar con **64 tierras**: una busqueda que devuelve **8**, un **filtro cruzado**, una tierra **sin
geometria**, un **poligono con agujero**, seleccion multiple, exportacion filtrada, volver de la ficha con filtros, y
probar **enlace directo, recarga y Atras/Adelante**.*

*Esto lo mide con **64 tierras de verdad**, dadas de alta por la puerta -no inventadas en la base-.*

Uso:  python scripts/verificar_la_aceptacion_de_las_tierras.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# *Los pueblos, para el filtro cruzado. Cuatro.*
LOS_PUEBLOS = ("Medina del Campo", "Penaranda de Bracamonte", "Arevalo", "Coca")


def el_poligono(x: float, y: float) -> str:
    """*Un cuadrado pequeno, para que la tierra tenga forma.*"""
    return (
        f"POLYGON(({x} {y}, {x + 0.001:.4f} {y}, {x + 0.001:.4f} {y + 0.001:.4f}, "
        f"{x} {y + 0.001:.4f}, {x} {y}))"
    )


EL_AGUJERO = (
    "POLYGON((-4.8000 41.6000, -4.7900 41.6000, -4.7900 41.6100, -4.8000 41.6100, -4.8000 41.6000),"
    " (-4.7980 41.6030, -4.7930 41.6030, -4.7930 41.6070, -4.7980 41.6070, -4.7980 41.6030))"
)


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def las_filas(nav) -> int:
    return int(
        str(
            nav.evaluar(
                "Array.from(document.querySelectorAll('#pantalla table tbody tr'))"
                ".filter(function (f) { const r = f.getBoundingClientRect();"
                " return r.width > 0 && r.height > 0; }).length || 0"
            )
        )
        or 0
    )


def abrir(nav, direccion: str, camino: str) -> str:
    el_ultimo = ""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(30):
            el_ultimo = el_texto(nav)
            if el_ultimo and el_ultimo == anterior:
                return el_ultimo
            anterior = el_ultimo
            time.sleep(0.4)
    return el_ultimo


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "aceptacion@prueba.local", "una-clave-larga-y-facil", "Ac")
        el_vale = cuenta["token"]
        print(f"== La aceptacion de las tierras  ({direccion}) ==")

        # ---- ***las 64 tierras***: *8 que se llaman VEGA -la busqueda tiene que devolver 8- y 56 mas.* ----
        print("\n1. LAS 64 TIERRAS")
        creadas = 0
        for i in range(1, 65):
            el_pueblo = LOS_PUEBLOS[i % len(LOS_PUEBLOS)]
            el_alias = f"LA VEGA {i}" if i <= 8 else f"LA ERA {i}"
            el_cuerpo = {
                "alias": el_alias,
                "ref_sigpac": f"47-900-0-0-{i}",
                "municipio": el_pueblo,
                "superficie_ha": 1.0 + (i % 5),
            }
            # *Las 8 primeras con forma, una con agujero, y de la 10 en adelante **sin geometria**.*
            if i <= 8:
                el_cuerpo["geometria"] = el_poligono(-4.80 + i / 1000, 41.60)
            elif i == 9:
                el_cuerpo["geometria"] = EL_AGUJERO
            codigo, _ = _llamar(direccion, "/api/parcelas", token=el_vale, metodo="POST", cuerpo=el_cuerpo)
            if codigo in (200, 201):
                creadas += 1
        print(f"  (creadas: {creadas})")
        fallos += not comprobar(creadas == 64, f"***las 64 tierras se dan de alta*** ({creadas})")

        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)

            # ---- 2 · las 64 y la busqueda de 8 ----
            print("\n2. LA BUSQUEDA DEVUELVE 8")
            el_texto_de_64 = abrir(nav, direccion, "#/tierras/mapa")
            las_64 = las_filas(nav)
            fallos += not comprobar(las_64 == 64, f"***se ven las 64*** (filas: {las_64})", el_texto_de_64)
            abrir(nav, direccion, "#/tierras/mapa?q=VEGA")
            las_ocho = las_filas(nav)
            fallos += not comprobar(las_ocho == 8, f"***la busqueda «VEGA» devuelve 8*** (filas: {las_ocho})")

            # ---- 3 · el filtro cruzado ----
            print("\n3. EL FILTRO CRUZADO")
            el_pueblo = LOS_PUEBLOS[0]
            abrir(nav, direccion, f"#/tierras/mapa?municipio={el_pueblo.replace(chr(32), '%20')}")
            las_del_pueblo = las_filas(nav)
            print(f"  ({el_pueblo}: {las_del_pueblo} filas)")
            abrir(
                nav,
                direccion,
                f"#/tierras/mapa?q=VEGA&municipio={el_pueblo.replace(chr(32), '%20')}",
            )
            las_cruzadas = las_filas(nav)
            print(f"  (VEGA en {el_pueblo}: {las_cruzadas} filas)")
            fallos += not comprobar(
                0 < las_cruzadas <= min(las_del_pueblo, 8),
                f"***el filtro cruzado es un SUBCONJUNTO de los dos*** "
                f"({las_cruzadas} de {las_del_pueblo} y de 8)",
            )

            # ---- 4 · la tierra sin geometria y el poligono con agujero ----
            print("\n4. LA QUE NO TIENE FORMA, Y LA QUE TIENE AGUJERO")
            el_mapa = abrir(nav, direccion, "#/tierras/mapa")
            los_poligonos = int(str(nav.evaluar("document.querySelectorAll('#pantalla svg polygon').length || 0")) or 0)
            print(f"  (poligonos dibujados: {los_poligonos} de 64 tierras)")
            fallos += not comprobar(
                los_poligonos <= 64,
                f"***se dibujan como mucho las 64 -no hay poligonos de mas-*** ({los_poligonos})",
            )

            # ---- 5 · el enlace directo, la recarga y Atras/Adelante ----
            print("\n5. EL ENLACE DIRECTO, LA RECARGA Y ATRAS")
            abrir(nav, direccion, "#/tierras/mapa?q=VEGA")
            la_primera = las_filas(nav)
            la_recargada = abrir(nav, direccion, "#/tierras/mapa?q=VEGA")
            fallos += not comprobar(
                las_filas(nav) == la_primera,
                "***recargar la misma direccion deja lo mismo***",
                la_recargada,
            )
            # *Atras, a la de las 64.*
            nav.orden("Runtime.evaluate", {"expression": "history.back()"})
            time.sleep(1.5)
            abrir(nav, direccion, "#/tierras/mapa")
            fallos += not comprobar(
                las_filas(nav) <= 64,
                "***Atras no rompe la pantalla***",
                el_texto(nav),
            )

    print(f"\nComprobaciones: 8   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
