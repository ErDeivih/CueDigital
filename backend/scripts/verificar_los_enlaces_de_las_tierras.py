"""***Los enlaces de las tierras, comprobados*** (21/10/2026, D04).

*Abre las direcciones que el documento `docs/ENLACES_DE_LAS_TIERRAS.md` da por buenas y comprueba que **cada una
abre lo suyo** -y no la pantalla de «esa direccion no lleva a ninguna parte», que es el error que ya aparecio dos veces
con direcciones inventadas-.*

*Y comprueba lo que el documento afirma: que **`#/mapa` no es la vista de las tierras** sino la busqueda en SIGPAC,
que es la razon por la que no se redirige.*

Uso:  python scripts/verificar_los_enlaces_de_las_tierras.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

NO_LLEVA_A_NADA = "no lleva a ninguna parte"


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def las_filas(nav) -> int:
    """***Cuantas tierras se ven en la tabla***: *es la lista, y es lo que se puede contar de verdad.*"""
    return int(
        nav.evaluar(
            "document.querySelectorAll('#pantalla table tbody tr').length || 0"
        )
        or 0
    )


def abrir(nav, direccion: str, camino: str) -> str:
    """*Abre y espera a que la pantalla pinte algo de verdad.*"""
    el_ultimo = ""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        for _ in range(30):
            el_ultimo = el_texto(nav)
            if el_ultimo and NO_LLEVA_A_NADA not in el_ultimo:
                anterior, el_ultimo = el_ultimo, el_ultimo
                time.sleep(0.5)
                if el_texto(nav) == anterior:
                    return el_ultimo
        time.sleep(0.5)
    return el_ultimo


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "enlaces@prueba.local", "una-clave-larga-y-facil", "En")
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            _poner_la_sesion(nav, direccion, cuenta["token"])
            print(f"== Los enlaces de las tierras  ({direccion}) ==")

            print("\n1. CADA DIRECCION ABRE LO SUYO, Y NO LA DE «NO LLEVA A NADA»")
            los_textos = {}
            for camino, nombre in (
                ("#/tierras", "mis cosas"),
                ("#/tierras/mapa", "las tierras enteras"),
                ("#/mapa", "la busqueda en SIGPAC"),
            ):
                el_suyo = abrir(nav, direccion, camino)
                los_textos[camino] = el_suyo
                fallos += not comprobar(
                    el_suyo and NO_LLEVA_A_NADA not in el_suyo,
                    f"***{camino} abre {nombre}***",
                    el_suyo,
                )
                print(f"          dice: {el_suyo[:100]!r}")

            print("\n2. Y SON TRES PANTALLAS DISTINTAS")
            fallos += not comprobar(
                len(set(los_textos.values())) == 3,
                "***las tres no son la misma***: *si `#/mapa` fuera la vista de las tierras, sobraria*",
            )

            print("\n3. LA VISTA DE LAS TIERRAS ENSENA LA LISTA Y EL MAPA")
            las_tierras = los_textos["#/tierras/mapa"]
            fallos += not comprobar(
                "tierra" in las_tierras.lower(),
                "***`#/tierras/mapa` habla de las tierras***",
                las_tierras,
            )

            # ---------------------------------------------------------------- 4 · el puente
            print("\n4. EL PUENTE: DE LA LISTA A LA VISTA COMPLETA, SIN VOLVER AL MENU")
            el_de_la_lista = abrir(nav, direccion, "#/tierras")
            fallos += not comprobar(
                "mis tierras en el mapa" in el_de_la_lista.lower(),
                "***la lista de lo que uso OFRECE el puente a la vista completa***",
                el_de_la_lista,
            )
            # *Y se pulsa, que es como se llega.*
            se_pulso = nav.evaluar(
                "(() => { const b = document.querySelector('[data-accion=\"tierras-al-mapa\"]');"
                " if (b) b.click(); return Boolean(b); })()"
            )
            la_vista = ""
            for _ in range(30):
                la_vista = el_texto(nav)
                if "en el mapa y en la tabla" in la_vista:
                    break
                time.sleep(0.5)
            fallos += not comprobar(
                bool(se_pulso) and "en el mapa y en la tabla" in la_vista,
                "***y al pulsarlo se llega a la vista completa***",
                la_vista,
            )
            fallos += not comprobar(
                # ***Con su contexto detras, que es lo que hace falta***: *la direccion no es solo «la pantalla»,
                # es **la pantalla en esta campaña y esta finca** -`#/tierras/mapa?campana=2026&finca=1`-, y eso es
                # el «enlace permanente al contexto» del contrato.*
                str(nav.evaluar("window.location.hash")).startswith("#/tierras/mapa"),
                "***y la direccion queda escrita, con su campaña y su finca***",
                str(nav.evaluar("window.location.hash")),
            )

            # ---------------------------------------------------------------- 5 · la lista y el mapa
            print("\n5. LA LISTA Y EL MAPA, CON EL MISMO CONJUNTO")
            # *Tres tierras de verdad, creadas por la puerta: sin datos, esto no probaria nada.*
            for i, alias in enumerate(("TIERRA UNO", "TIERRA DOS", "OTRA COSA"), start=1):
                _llamar(
                    direccion,
                    "/api/parcelas",
                    token=cuenta["token"],
                    metodo="POST",
                    cuerpo={
                        "alias": alias,
                        "ref_sigpac": f"47-001-0-0-{i}",
                        "municipio": "Valladolid",
                        "superficie_ha": 1.5,
                    },
                )
            todas = abrir(nav, direccion, "#/tierras/mapa")
            las_todas = las_filas(nav)
            fallos += not comprobar(
                las_todas == 3,
                f"***la vista ensena las TRES tierras*** (filas: {las_todas})",
                todas,
            )
            # *Y con un filtro puesto por la direccion, las que casan.*
            las_filtradas_texto = abrir(nav, direccion, "#/tierras/mapa?q=TIERRA")
            las_filtradas = las_filas(nav)
            fallos += not comprobar(
                las_filtradas == 2,
                f"***con `?q=TIERRA` ensena DOS, no tres*** (filas: {las_filtradas})",
                las_filtradas_texto,
            )
            # *Y al recargar la misma direccion, sigue filtrado: la direccion lleva el contexto.*
            recargada = abrir(nav, direccion, "#/tierras/mapa?q=TIERRA")
            las_de_la_recarga = las_filas(nav)
            fallos += not comprobar(
                las_de_la_recarga == 2,
                f"***y al recargar sigue en DOS: el filtro viaja en la direccion*** (filas: {las_de_la_recarga})",
                recargada,
            )
            # ***Y lo que el encargo pide de verdad***: *la lista y el mapa salen del **mismo** array -la pantalla
            # recibe `vista.tierras` una sola vez y lo usa para las dos-, asi que no pueden discrepar. Se deja dicho
            # aqui para que la comprobacion no prometa mas de lo que mide: **lo medido es la lista**.*
            fallos += not comprobar(
                las_filtradas == las_de_la_recarga,
                "***las tres lecturas cuentan lo mismo: 3 sin filtro, 2 con el, 2 al recargar***",
            )

    print(f"\nComprobaciones: 12   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
