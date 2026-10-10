"""El pago se guarda **por su puerta** (`/api/gastos/pagos`), no por la de los gastos (08/10/2026).

**Por qué existe.** Lo encontró el recorrido económico desde las pantallas y lo confirmó un revisor
independiente: la rama del pago de `guardarLasCuentas` construía el cuerpo correcto —importe, fecha, proveedor,
forma, clave de reenvío y aplicaciones, **sin `concepto`**— pero **no reasignaba la ruta**, que nace arriba en
`/api/gastos`. Esa puerta **exige `concepto`**, así que el servidor devolvía **HTTP 422** y el agricultor **no
podía apuntar un pago**, que es justo el tramo que este encargo venía a comprobar.

Medido contra el servidor antes del arreglo:

    /api/gastos:       RECHAZA el cuerpo del pago (HTTP 422 Unprocessable Entity)
    /api/gastos/pagos: ACEPTA el cuerpo del pago

**Esta prueba sujeta el arreglo**: que la rama del pago apunte a su puerta. Sin esa línea se pone roja, que es
lo que se le pide a la prueba de un defecto: **fallar antes del arreglo**.
"""

from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "web" / "app.js"

LA_RAMA = '} else if (clase === "pago") {'
SU_PUERTA = 'ruta = "/api/gastos/pagos";'


def test_la_rama_del_pago_apunta_a_la_puerta_del_pago():
    """El cuerpo del pago no lleva `concepto`: tiene que ir a la puerta que lo acepta."""
    fuente = APP.read_text(encoding="utf-8")
    assert LA_RAMA in fuente, "no encuentro la rama del pago en `guardarLasCuentas`"
    desde = fuente.index(LA_RAMA)
    suyo = fuente[desde : desde + 700]
    assert SU_PUERTA in suyo, (
        "la rama del pago **no reasigna la ruta**: el cuerpo va sin `concepto` y la puerta de los gastos lo "
        "rechaza con HTTP 422 -medido contra el servidor-, así que el agricultor no puede apuntar un pago"
    )
