"""***El OCR, medido por campo*** (22/10/2026, D08).

*El encargo pide «OCR con **corpus autorizado** y **resultados por campo**». El corpus autorizado **no lo tengo** -no
se puede inventar: hay que usar facturas de verdad, con permiso de quien las emite-.*

***Lo que SI se puede hacer, y se hace aqui***: *comprobar **que el lector lee**, y **campo por campo**, con una factura
**sintetica** -fabricada por el guion, sin datos de nadie-. **No es el corpus**: es el minimo que dice si el camino
funciona o si esta roto.*

*Y se dice lo que el propio modulo advierte: **sin el programa, la aplicacion sigue** y el agricultor teclea los
datos; **nunca se inventa lo que pone el papel**.*

Uso:  python scripts/medir_el_ocr_por_campo.py
"""

from __future__ import annotations

import base64
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, "scripts")
sys.path.insert(0, ".")

from app import ocr  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

# ***La factura sintetica.*** *Los campos que el encargo quiere comprobar, con datos que se ven a la primera.*
LA_FACTURA = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<style>
 body { font-family: Arial, sans-serif; background: white; color: #111; margin: 40px; }
 h1 { font-size: 34px; margin: 0 0 20px; }
 p { font-size: 26px; margin: 8px 0; }
 table { font-size: 26px; border-collapse: collapse; margin-top: 18px; }
 th, td { border: 1px solid #333; padding: 8px 14px; }
</style></head><body>
 <h1>FACTURA</h1>
 <p><strong>Proveedor:</strong> SUMINISTROS AGRICOLAS PENARANDA SL</p>
 <p><strong>NIF:</strong> B12345678</p>
 <p><strong>Numero de factura:</strong> F-2026-0042</p>
 <p><strong>Fecha:</strong> 15/07/2026</p>
 <table>
  <tr><th>Concepto</th><th>Cantidad</th><th>Importe</th></tr>
  <tr><td>Abono NPK</td><td>500 kg</td><td>100,00 EUR</td></tr>
  <tr><td>Transporte</td><td>1</td><td>21,00 EUR</td></tr>
 </table>
 <p><strong>Base imponible:</strong> 100,00 EUR</p>
 <p><strong>IVA 21%:</strong> 21,00 EUR</p>
 <p><strong>Total:</strong> 121,00 EUR</p>
</body></html>"""

# *Lo que hay que encontrar en el texto, campo por campo.*
LOS_CAMPOS = {
    "el proveedor": "PENARANDA",
    "el NIF": "B12345678",
    "el numero de factura": "F-2026-0042",
    "la fecha": "15/07/2026",
    "la base imponible": "100",
    "el IVA": "21",
    "el total": "121",
}


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def main() -> int:
    if not ocr.hay_lector():
        print("  ***no hay lector instalado***: el camino del OCR no se puede medir aqui.")
        print("  (la aplicacion, sin lector, sigue funcionando y el agricultor teclea los datos: no se inventa nada)")
        return 1
    print(f"== El OCR por campo  (lector: {ocr.programa()}, idioma: {ocr.idioma_a_usar()}) ==")
    fallos = 0
    with tempfile.TemporaryDirectory(prefix="cuedigital-ocr-") as la_carpeta:
        la_pagina = pathlib.Path(la_carpeta) / "factura.html"
        la_pagina.write_text(LA_FACTURA, encoding="utf-8")
        la_imagen = pathlib.Path(la_carpeta) / "factura.png"
        with NavegadorDeVerdad(ancho=1200, alto=900) as nav:
            nav.abrir(la_pagina.as_uri(), esperar=1.5)
            time.sleep(0.5)
            el_crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
            la_imagen.write_bytes(el_crudo)
        print(f"  (la factura sintetica: {la_imagen.stat().st_size // 1024} KB)")
        # ***Y se le da al lector del programa***, no a otro: *lo que se mide es lo que el agricultor se encontraria.*
        el_texto = ocr.leer_texto(la_imagen.read_bytes())
        print(f"  (lo que ha leido, {len(el_texto)} caracteres)")
        print(f"  ({' '.join(el_texto.split())[:220]})")
        for el_campo, lo_que_busca in LOS_CAMPOS.items():
            fallos += not comprobar(
                lo_que_buscar(lo_que_busca) in el_texto.replace(" ", ""),
                f"***el OCR encuentra {el_campo}*** ({lo_que_busca})",
                el_texto,
            )
    print(f"\nComprobaciones: {len(LOS_CAMPOS)}   Fallos: {fallos}")
    print(
        "\n***Aviso***: *esto es una factura **sintetica**, no el corpus autorizado. "
        "Dice que el lector lee; NO dice que lea las facturas de verdad. "
        "Eso necesita un corpus con permiso.*"
    )
    return 1 if fallos else 0


def lo_que_buscar(lo_que: str) -> str:
    """*Se compara sin espacios: el OCR parte las lineas donde le parece.*"""
    return lo_que.replace(" ", "")


if __name__ == "__main__":
    raise SystemExit(main())
