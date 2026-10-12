"""Capturar la LISTA DE COBROS con un cobro dentro (11/10/2026).

POR QUÉ EXISTE. Es una de las dos pantallas cuyas capturas miró el dueño del producto para decir que la
aplicación «parece una UI para niños pequeños», y la última que se ha pasado a tabla. Para juzgarla hay que
**tener un cobro dentro**: sin datos, esa pantalla enseña su estado vacío y **una pantalla vacía no se puede
juzgar** —es la trampa que ya ha costado una ronda en esta sesión—.

El escenario **no se inventa aquí**: se piden prestados los constructores de los guiones que ya lo montan (la
compra de la prueba y el caso del encargo del reparto), y el cobro se crea **por su puerta de verdad**
(`POST /api/cobros`), como lo crearía el agricultor.

Uso:  python scripts/capturar_la_lista_de_cobros.py <direccion> [nombre] [ancho]
"""

from __future__ import annotations

import base64
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from capturar_la_pantalla_del_reparto import _api, _el_caso_del_encargo  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
NOMBRE = sys.argv[2] if len(sys.argv) > 2 else "cobros-escritorio-tabla"
ANCHO = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
CARPETA = pathlib.Path(r"F:\EspacioCodigo\CueDigital\docs\capturas")


def main() -> int:
    print(f"  (direccion: {DIRECCION}   ancho: {ANCHO})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    campana = escenario.volumen.campana_actual.id
    devuelto = _el_caso_del_encargo(token, campana)
    partes = devuelto if isinstance(devuelto, (list, tuple)) else [devuelto]
    deudas = [parte for parte in partes if isinstance(parte, int)]
    if not deudas:
        print("  (el caso del encargo no ha devuelto facturas: no hay cobro que capturar)")
        return 1
    hecho = _api(
        "/api/cobros",
        token,
        {"fecha": "2026-07-20", "importe": "40.00", "factura_emitida_id": deudas[0]},
    )
    print(f"  (el cobro: {str(hecho)[:90]})")

    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"{NOMBRE}.png"
    with NavegadorDeVerdad(ancho=ANCHO, alto=1000) as nav:
        nav.medir(ANCHO, 1000, movil=ANCHO < 700)
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
        )
        nav.abrir(f"{DIRECCION}/#/ventas/cobros", esperar=3.0)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
        destino.write_bytes(crudo)
        suyo = nav.evaluar(
            "(() => { const t = document.querySelector('#pantalla table.tabla');"
            " const f = t ? t.querySelector('tbody tr') : null;"
            " return { tabla: Boolean(t), filas: t ? t.querySelectorAll('tbody tr').length : 0,"
            " alto_fila: f ? Math.round(f.getBoundingClientRect().height) : null,"
            " columnas: t ? t.querySelectorAll('thead th').length : 0 }; })()"
        )
    ancho_imagen, alto_imagen = struct.unpack(">II", crudo[16:24])
    print(f"  captura: {destino}")
    print(f"  imagen: {ancho_imagen}x{alto_imagen}")
    print(f"  la pantalla: {json.dumps(suyo, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
