"""La prueba del pago, vista en ROJO sin el arreglo y en verde con él (08/10/2026).

**Por qué un guion y no una orden en línea.** Lo intenté en línea y me rompí dos veces con el escapado de
comillas; el fichero se quedó intacto por suerte, pero la demostración **no se hizo**. Aquí se hace con cuidado y
se **restaura byte a byte** desde el texto original, que es como se hizo con el albarán.

Uso:  python scripts/demostrar_que_la_prueba_del_pago_falla_antes.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
APP = RAIZ / "web" / "app.js"
LA_PRUEBA = RAIZ / "tests" / "test_el_pago_se_guarda_por_su_puerta.py"
LA_LINEA = '    ruta = "/api/gastos/pagos";\n'


def correr_la_prueba() -> int:
    suyo = subprocess.run(  # noqa: S603 — es el propio proyecto
        [sys.executable, "-m", "pytest", str(LA_PRUEBA), "-q"],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return suyo.returncode


def main() -> int:
    original = APP.read_text(encoding="utf-8")
    if LA_LINEA not in original:
        print("=> no encuentro la linea del arreglo en app.js: mira antes de seguir")
        return 1

    print("1) con el arreglo puesto:")
    con_arreglo = correr_la_prueba()
    print(f"   codigo {con_arreglo} ({'verde' if con_arreglo == 0 else 'ROJO'})")

    try:
        APP.write_text(original.replace(LA_LINEA, "", 1), encoding="utf-8")
        print("2) con el arreglo QUITADO a proposito:")
        sin_arreglo = correr_la_prueba()
        print(f"   codigo {sin_arreglo} ({'verde' if sin_arreglo == 0 else 'ROJO, que es lo que se le pide'})")
    finally:
        # **Byte a byte**: se repone el texto original entero, no una reconstruccion.
        APP.write_text(original, encoding="utf-8")
        repuesto = APP.read_text(encoding="utf-8") == original
        print(f"3) restaurado byte a byte: {'si' if repuesto else 'NO'}")

    print("4) y otra vez con el arreglo:")
    otra_vez = correr_la_prueba()
    print(f"   codigo {otra_vez} ({'verde' if otra_vez == 0 else 'ROJO'})")

    if con_arreglo == 0 and sin_arreglo != 0 and repuesto and otra_vez == 0:
        print("\n=> DEMOSTRADO: la prueba falla sin el arreglo y pasa con el")
        return 0
    print("\n=> NO queda demostrado: mira los codigos de arriba")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
