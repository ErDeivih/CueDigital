"""***Las capturas de las cinco anchuras*** (22/10/2026, D05).

*El encargo pide capturas de **320, 390, 712, 1024 y 1440** para revisar con vision. Esto las saca de la aplicacion
de verdad, con **una cuenta y unos datos temporales**, y las deja en una carpeta para mirarlas.*

*No es una prueba automatica: **es el material para la revision**.*

Uso:  python scripts/capturar_las_anchuras.py [carpeta]
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

LAS_ANCHURAS = ((320, 700), (390, 844), (712, 900), (1024, 768), (1440, 900))
LAS_PANTALLAS = (("inicio", "#/"), ("tierras", "#/tierras/mapa"), ("cuaderno", "#/cuaderno"))
LAS_SENALES = {
    "inicio": '[data-accion="inicio"][data-ir="mi_cuaderno"]',
    "tierras": '#t06_buscar',
    "cuaderno": '[data-accion="inicio"][data-ir="echar_producto"]',
}


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> None:
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(40):
            el_actual = el_texto(nav)
            if el_actual and el_actual == anterior:
                return
            anterior = el_actual
            time.sleep(0.5)


def main() -> int:
    la_carpeta = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("capturas-de-anchuras")
    la_carpeta.mkdir(parents=True, exist_ok=True)
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "capturas@prueba.local", "una-clave-larga-y-facil", "Ca")
        # *Unos datos, para que las pantallas no salgan vacias.*
        for i, alias in enumerate(("LA VEGA", "EL PRADO", "LAS ERAS"), start=1):
            _llamar(
                direccion,
                "/api/parcelas",
                token=cuenta["token"],
                metodo="POST",
                cuerpo={
                    "alias": alias,
                    "ref_sigpac": f"47-100-0-0-{i}",
                    "municipio": "Medina del Campo",
                    "superficie_ha": 2.0 + i,
                    "geometria": (
                        f"POLYGON(({-4.72 - i / 100} 41.65, {-4.71 - i / 100} 41.65, "
                        f"{-4.71 - i / 100} 41.66, {-4.72 - i / 100} 41.66, {-4.72 - i / 100} 41.65))"
                    ),
                },
            )
        for ancho, alto in LAS_ANCHURAS:
            with NavegadorDeVerdad(ancho=ancho, alto=alto) as nav:
                nav.medir(ancho, alto)
                _poner_la_sesion(nav, direccion, cuenta["token"])
                for nombre, camino in LAS_PANTALLAS:
                    abrir(nav, direccion, camino)
                    if not nav.esperar(
                        "document.querySelector('#pantalla ' + "
                        + json.dumps(LAS_SENALES[nombre]) + ") !== null",
                        segundos=20,
                    ):
                        raise RuntimeError(f"No se ha abierto {nombre}: {el_texto(nav)[:200]}")
                    medida = nav.evaluar("({ancho: innerWidth, alto: innerHeight})")
                    if medida != {"ancho": ancho, "alto": alto}:
                        raise RuntimeError(f"Viewport distinto del solicitado: {medida}")
                    if nombre == "cuaderno" and not nav.evaluar(
                        "document.querySelector('#pantalla h1')?.textContent.trim() === 'Mi cuaderno'"
                    ):
                        raise RuntimeError("La captura de cuaderno no contiene su título")
                    crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
                    destino = la_carpeta / f"{nombre}-{ancho}x{alto}.png"
                    destino.write_bytes(crudo)
                    print(f"  {destino.name}  ({len(crudo) // 1024} KB)")
    print(f"\n  las capturas, en {la_carpeta.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
