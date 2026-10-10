"""Las tres guardas del repintado: que **respeten lo que esté abierto** (08/10/2026).

**Por qué existe.** El recorrido económico encontró andando el primero de esta clase -el formulario del albarán se
abría y se cerraba solo-, y el **revisor independiente** encontró **dos más**, exactamente el mismo fallo en otros
dos sitios:

1. `abrirElLibroDelAlmacen` repintaba la lista al terminar la carga y **descartaba** el formulario del albarán;
2. el repintado de la ficha de una recepción **se comía el enganche de la factura**, que se abre desde esa misma
   ficha sin tocar `suyo.recepcion`;
3. y el repintado del libro **se comía el movimiento a mano** (`movimiento-nuevo`), que vive en las fichas del
   propio libro.

Las tres se arreglan igual: la guarda de la clase es **una**, «si hay algo abierto, se pinta eso» -el albarán ya
tenía la suya y su prueba-, y aquí se sujetan las **dos que faltaban**.

**Y este fichero se demuestra solo**: corriéndolo directo, quita cada guarda, comprueba que la prueba se pone
**roja** y la repone **byte a byte**. Es la forma que se usó con el albarán y con el pago.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "web" / "app.js"

# Las dos guardas que se sujetan aquí, y el sitio donde tienen que estar.
LAS_GUARDAS = (
    ("el enganche de la recepción", 'if (sigue && estado.pantalla === "recepcion" && !suyo.enganche)'),
    ("el movimiento a mano", "if (suyo.movimiento) return pantallaMovimientoDeAlmacen();"),
)


def test_los_repintados_respetan_lo_que_este_abierto():
    """El enganche de la recepción y el movimiento a mano no pueden perderse al repintar."""
    fuente = APP.read_text(encoding="utf-8")
    faltan = [nombre for nombre, guarda in LAS_GUARDAS if guarda not in fuente]
    assert not faltan, (
        "el repintado **no respeta** lo que esté abierto en: "
        + ", ".join(faltan)
        + ". Sin esa guarda, se pinta encima y el agricultor pierde lo que acaba de abrir"
    )


if __name__ == "__main__":
    # **La demostración**: sin cada guarda, esta prueba tiene que ponerse ROJA.
    original = APP.read_text(encoding="utf-8")
    pruebas = pathlib.Path(__file__).resolve()
    codigos = {}
    try:
        for nombre, guarda in LAS_GUARDAS:
            if guarda not in original:
                print(f"=> no encuentro la guarda de {nombre}: mira antes de seguir")
                raise SystemExit(1)
            APP.write_text(original.replace(guarda, "// guarda quitada a proposito", 1), encoding="utf-8")
            suyo = subprocess.run(  # noqa: S603 — es el propio proyecto
                [sys.executable, "-m", "pytest", str(pruebas), "-q"],
                cwd=str(RAIZ / "backend"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            codigos[nombre] = suyo.returncode
            print(f"  sin la guarda de {nombre}: codigo {suyo.returncode} "
                  f"({'ROJA, que es lo que se le pide' if suyo.returncode != 0 else 'VERDE: no sujeta nada'})")
            APP.write_text(original, encoding="utf-8")
    finally:
        APP.write_text(original, encoding="utf-8")
    repuesto = APP.read_text(encoding="utf-8") == original
    print(f"  restaurado byte a byte: {'si' if repuesto else 'NO'}")
    if repuesto and all(codigo != 0 for codigo in codigos.values()):
        print("=> DEMOSTRADO: sin cada guarda, la prueba se pone roja; con ellas, verde")
        raise SystemExit(0)
    raise SystemExit(1)
