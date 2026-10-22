"""Regresión D04: Atrás/Adelante conserva posición y filtros sin recargar el módulo.

Usa servidor, base, adjuntos y perfiles temporales. Un scroll perdido falla la prueba.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402


def esperar(nav, condicion: str) -> None:
    if not nav.esperar(condicion, segundos=30):
        raise RuntimeError(f"No se cumplió: {condicion}")


def main() -> int:
    fallos = 0
    comprobaciones = 0

    def comprobar(bien, que):
        nonlocal fallos, comprobaciones
        comprobaciones += 1
        fallos += not bien
        print(f"  [{'OK   ' if bien else 'FALLO'}] {que}", flush=True)

    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "vuelta@prueba.local", "una-clave-larga-y-facil", "Vu")
        ids = []
        for i in range(24):
            codigo, cuerpo = _llamar(direccion, "/api/parcelas", token=cuenta["token"], metodo="POST",
                                     cuerpo={"alias": f"LA VEGA {i}", "superficie_ha": 1.0})
            if codigo != 201:
                raise RuntimeError(f"No se creó la tierra temporal: {codigo}")
            ids.append(cuerpo["id"])

        for ancho in (1440, 390):
            with NavegadorDeVerdad(ancho=ancho, alto=700) as nav:
                nav.medir(ancho, 700)
                _poner_la_sesion(nav, direccion, cuenta["token"])
                nav.evaluar("location.hash = '#/tierras/mapa?q=VEGA'")
                esperar(nav, "document.querySelectorAll('.t06-tarjeta').length === 24")
                lista = nav.evaluar("location.hash")
                ficha = f"#/tierras/{ids[0]}"
                for vuelta in range(2):
                    nav.evaluar("window.scrollTo(0, 320)")
                    esperar(nav, "window.scrollY === 320")
                    comprobar(True, f"{ancho}: control positivo, lista desplazada a 320 px")
                    # Navegación dentro del mismo documento: Page.navigate/abrir recarga
                    # el módulo y borra precisamente el estado que se quiere comprobar.
                    nav.evaluar("location.hash = " + json.dumps(ficha))
                    esperar(nav, "document.querySelector('[data-accion=\"tierras-al-mapa\"]') !== null")
                    nav.evaluar("history.back()")
                    esperar(nav, "location.hash === " + json.dumps(lista))
                    esperar(nav, "document.querySelectorAll('.t06-tarjeta').length === 24")
                    time.sleep(0.15)
                    y = nav.evaluar("window.scrollY")
                    comprobar(abs(y - 320) <= 2, f"{ancho}, vuelta {vuelta + 1}: scroll restaurado ({y})")
                    comprobar("q=VEGA" in nav.evaluar("location.hash"), f"{ancho}: filtro conservado")
                    if vuelta == 0:
                        nav.evaluar("history.forward()")
                        esperar(nav, "document.querySelector('[data-accion=\"tierras-al-mapa\"]') !== null")
                        nav.evaluar("history.back()")
                        esperar(nav, "location.hash === " + json.dumps(lista))
                        esperar(nav, "document.querySelectorAll('.t06-tarjeta').length === 24")
                        comprobar(abs(nav.evaluar("window.scrollY") - 320) <= 2,
                                  f"{ancho}: Adelante y Atrás conservan la posición")
                # Control negativo: otra búsqueda empieza arriba, no hereda la posición.
                nav.evaluar("location.hash = '#/tierras/mapa?q=NO_EXISTE'")
                esperar(nav, "document.querySelectorAll('.t06-tarjeta').length === 0")
                comprobar(nav.evaluar("window.scrollY") == 0, f"{ancho}: otro filtro empieza arriba")
    print(f"\nComprobaciones: {comprobaciones}   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
