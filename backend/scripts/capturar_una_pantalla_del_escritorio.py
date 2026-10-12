"""Capturar una pantalla del escritorio, con su tamaño de verdad (11/10/2026).

POR QUÉ EXISTE. El dueño del producto juzga **mirando**, y con razón: «no se parece a un CRM normal» es un
juicio de ojos, no de CSS. Después de cuatro rondas bajando la densidad del escritorio (la fila de la tabla
de ventas pasó de **277,9 px a 54,2**), hace falta **la captura** para poder comparar con las de antes.

Entra **como entra el agricultor** (con su vale guardado en el navegador, no con una maqueta) y deja el PNG en
la carpeta que se le diga, diciendo **de qué tamaño es la imagen** y con qué ventana se hizo: una captura que
dice «1440» y mide otra cosa es una captura que miente.

Uso:  python scripts/capturar_una_pantalla_del_escritorio.py <direccion> <#/ruta> <nombre> [ancho] [carpeta]
"""

from __future__ import annotations

import base64
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
PANTALLA = sys.argv[2] if len(sys.argv) > 2 else "#/ventas"
NOMBRE = sys.argv[3] if len(sys.argv) > 3 else "pantalla"
ANCHO = int(sys.argv[4]) if len(sys.argv) > 4 else 1440
CARPETA = pathlib.Path(sys.argv[5]) if len(sys.argv) > 5 else pathlib.Path(
    r"F:\EspacioCodigo\CueDigital\docs\capturas"
)


def main() -> int:
    print(f"  (direccion: {DIRECCION}   pantalla: {PANTALLA}   ancho: {ANCHO})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"{NOMBRE}.png"
    with NavegadorDeVerdad(ancho=ANCHO, alto=1000) as nav:
        nav.medir(ANCHO, 1000, movil=ANCHO < 700)
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
        )
        nav.abrir(f"{DIRECCION}/{PANTALLA.lstrip('/')}", esperar=2.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
        destino.write_bytes(crudo)
        ventana = nav.evaluar("[window.innerWidth, window.innerHeight]")
        filas = nav.evaluar(
            "(() => { const f = document.querySelector('table tbody tr');"
            " return f ? Math.round(f.getBoundingClientRect().height) : null; })()"
        )
    ancho_imagen, alto_imagen = struct.unpack(">II", crudo[16:24])
    print(f"  captura: {destino}")
    print(f"  imagen: {ancho_imagen}x{alto_imagen}   ventana: {ventana[0]}x{ventana[1]}")
    print(f"  alto de la primera fila de la tabla: {filas} px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
