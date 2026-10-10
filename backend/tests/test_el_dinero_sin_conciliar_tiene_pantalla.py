"""El dinero sin conciliar tiene pantalla, y su botón (08/10/2026).

**Por qué existe.** El recorrido económico demostró, **por dos caminos independientes**, que el CRM sabía
apuntar un pago, anularlo, conciliarlo **automáticamente por antigüedad** y quitarle aplicaciones… y que **no
tenía ninguna pantalla que lo hiciera**:

* el cliente **no leía nunca** `GET /api/gastos/pagos` -sólo escribía en esa puerta-;
* y **`sin_conciliar` aparecía 0 veces** en `app.js`.

Consecuencia medida: el `pendiente` de un gasto se quedaba en **663,00** para siempre, porque **no había forma
de decir a qué gasto va un pago**. Los textos ya estaban escritos en `textos.py` (`pagos_titulo`,
`sin_conciliar_titulo`, `pago_conciliar` «DECIR A QUÉ VA»), así que la pantalla estaba **prevista y no se hizo**.

**Y este fichero se demuestra solo**: corriéndolo directo quita cada pieza, comprueba que la prueba se pone
**roja** y la repone **byte a byte**.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "web" / "app.js"
CUENTAS = RAIZ / "backend" / "web" / "react" / "pantallas" / "gastos.js"

LAS_PIEZAS = (
    (APP, "el cliente **pide** los pagos", 'apiJson("/api/gastos/pagos")'),
    (APP, "los pagos entran en el estado de las cuentas", "suyo.pagos = await apiJson"),
    (APP, "y llegan a `cuentas`, que es lo que la pantalla lee", "...(suyo.pagos || {})"),
    (CUENTAS, "y la pantalla los pinta con su botón", "sinConciliar=${cuentas.sin_conciliar || []}"),
)


def test_el_dinero_sin_conciliar_tiene_pantalla():
    """Lo que el servidor ofrece tiene que poder hacerse desde la pantalla, no sólo por la API."""
    fuente_app = APP.read_text(encoding="utf-8")
    fuente_cuentas = CUENTAS.read_text(encoding="utf-8")
    faltan = [
        nombre
        for (fichero, nombre, pieza) in LAS_PIEZAS
        if pieza not in (fuente_app if fichero == APP else fuente_cuentas)
    ]
    assert not faltan, (
        "el dinero sin conciliar **no se puede aplicar** desde la pantalla; falta: " + ", ".join(faltan)
    )


if __name__ == "__main__":
    originales = {fichero: fichero.read_text(encoding="utf-8") for fichero, _, _ in LAS_PIEZAS}
    pruebas = pathlib.Path(__file__).resolve()
    codigos = {}
    try:
        for fichero, nombre, pieza in LAS_PIEZAS:
            original = originales[fichero]
            if pieza not in original:
                print(f"=> no encuentro la pieza de {nombre}: mira antes de seguir")
                raise SystemExit(1)
            # Se quita **entre marcas de comentario y código**: sustituir por una línea inocua de JS.
            fichero.write_text(original.replace(pieza, "// pieza quitada a proposito", 1), encoding="utf-8")
            suyo = subprocess.run(  # noqa: S603 — es el propio proyecto
                [sys.executable, "-m", "pytest", str(pruebas), "-q"],
                cwd=str(RAIZ / "backend"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            codigos[nombre] = suyo.returncode
            print(f"  sin {nombre}: codigo {suyo.returncode} "
                  f"({'ROJA, que es lo que se le pide' if suyo.returncode != 0 else 'VERDE: no sujeta nada'})")
            fichero.write_text(original, encoding="utf-8")
    finally:
        for fichero, original in originales.items():
            fichero.write_text(original, encoding="utf-8")
    repuestos = all(fichero.read_text(encoding="utf-8") == original for fichero, original in originales.items())
    print(f"  restaurados byte a byte: {'si' if repuestos else 'NO'}")
    if repuestos and all(codigo != 0 for codigo in codigos.values()):
        print("=> DEMOSTRADO: sin cada pieza, la prueba se pone roja; con ellas, verde")
        raise SystemExit(0)
    raise SystemExit(1)
