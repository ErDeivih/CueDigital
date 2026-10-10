"""Las dos líneas que rompían el pago: que sigan arregladas (08/10/2026).

**Por qué existe.** Son los dos defectos reales del recorrido económico que se arreglaron **sin** prueba que
fallara antes, y el revisor lo señaló:

1. `elFormularioDeLasCuentas` llamaba a **`hoy()`** al construir la fecha del pago, y **esa función no existe**
   -medido: `hoy(` aparecía **una sola vez** en todo `app.js`-. El `ReferenceError` lo recogía el `try` de
   `montar`, que hacía `listo = null` **sin dejar rastro**, y el agricultor veía el aviso `sin_react` («falta un
   fichero del programa»), que despista: **no faltaba ningún fichero**, y el formulario del pago **nunca** se
   podía abrir.
2. `opcionesDe` leía `spec.tipo` **sin comprobar que `spec` exista**, y la rama del pago la llama con
   `estado.interfaz.formas_de_pago`: si no llega, `TypeError` y el mismo aviso.

**Y este fichero se demuestra solo**: corriéndolo directo, quita cada arreglo, comprueba que la prueba se pone
**roja** y lo repone **byte a byte**. Es la forma que se usó con el albarán, con el pago y con los repintados.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "web" / "app.js"

# Lo que se sujeta: el arreglo de `hoy()` y el de `opcionesDe`, con el sitio donde tienen que estar.
LOS_ARREGLOS = (
    ("la fecha del pago sale del estado, no de `hoy()`", 'loQueYaEstaba("pago-fecha", cual.fecha || "")'),
    ("`opcionesDe` no revienta sin especificación", "if (!spec || !spec.tipo) return [];"),
)


def test_el_pago_no_revienta_al_construirse():
    """Sin estas dos líneas, la pantalla del pago no se abre y el agricultor no puede apuntar un pago."""
    fuente = APP.read_text(encoding="utf-8")
    faltan = [nombre for nombre, arreglo in LOS_ARREGLOS if arreglo not in fuente]
    assert not faltan, "el formulario del pago vuelve a romperse por: " + ", ".join(faltan)
    # **Y que no vuelva la llamada**, comprobando sólo el código: buscar `hoy(` a secas se pone rojo por los
    # **comentarios** que explican este mismo defecto -el mismo error que hizo un barrido mío por todo el
    # repositorio, que destrozó una huella-. Se miran las líneas que **no** son comentario.
    del_codigo = "\n".join(
        linea for linea in fuente.splitlines() if not linea.lstrip().startswith(("//", "*", "/*"))
    )
    assert "hoy(" not in del_codigo, "vuelve a haber una llamada a `hoy()`, que no existe en este fichero"


if __name__ == "__main__":
    original = APP.read_text(encoding="utf-8")
    pruebas = pathlib.Path(__file__).resolve()
    codigos = {}
    try:
        for nombre, arreglo in LOS_ARREGLOS:
            if arreglo not in original:
                print(f"=> no encuentro el arreglo de {nombre}: mira antes de seguir")
                raise SystemExit(1)
            APP.write_text(original.replace(arreglo, "// arreglo quitado a proposito", 1), encoding="utf-8")
            suyo = subprocess.run(  # noqa: S603 — es el propio proyecto
                [sys.executable, "-m", "pytest", str(pruebas), "-q"],
                cwd=str(RAIZ / "backend"),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            codigos[nombre] = suyo.returncode
            print(f"  sin el arreglo de {nombre}: codigo {suyo.returncode} "
                  f"({'ROJA, que es lo que se le pide' if suyo.returncode != 0 else 'VERDE: no sujeta nada'})")
            APP.write_text(original, encoding="utf-8")
    finally:
        APP.write_text(original, encoding="utf-8")
    repuesto = APP.read_text(encoding="utf-8") == original
    print(f"  restaurado byte a byte: {'si' if repuesto else 'NO'}")
    if repuesto and all(codigo != 0 for codigo in codigos.values()):
        print("=> DEMOSTRADO: sin cada arreglo, la prueba se pone roja; con ellos, verde")
        raise SystemExit(0)
    raise SystemExit(1)
