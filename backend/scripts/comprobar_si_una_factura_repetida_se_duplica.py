"""¿Protege el servidor contra apuntar **la misma factura** dos veces? (08/10/2026).

**Por qué.** El recorrido económico crea la factura **desde la pantalla** y, al pulsar guardar otra vez, el botón
está **deshabilitado** -medido-, así que no hay segundo envío. Mi comprobación de «no duplica» era, por tanto,
**vacua**, como demostró el revisor independiente. Y el servidor: `models.Factura` **no tiene clave de reenvío** y
`POST /api/facturas` no comprueba duplicados.

Mi primer intento de comprobarlo mandó un cuerpo **sin líneas** y el servidor contestó **422** -que puede ser por
las líneas, no por el duplicado-, así que eso **no probaba nada**. Aquí se manda el cuerpo **con su línea**, como
lo manda la pantalla, y se repite: si el segundo envío **pasa**, queda **demostrado** que dos envíos crean dos
facturas; si **se rechaza**, está protegido.

Uso:  python scripts/comprobar_si_una_factura_repetida_se_duplica.py <direccion>
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time
import urllib.error
import urllib.request

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8190"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datos_representativos as datos  # noqa: E402


def llamar(camino: str, token: str, cuerpo: dict | None = None):
    """Llama a la API **como la llama la pantalla**, y devuelve (código, respuesta) sin lanzar.

    **Con `httpx` y en `multipart`** (08/10/2026): el servidor espera el cuerpo con el campo de formulario
    `datos` -medido dos veces: en JSON plano contesta `{'loc': ['body', 'datos'], 'msg': 'Field required'}`-, y la
    pantalla lo manda así. `httpx` ya es dependencia del proyecto: lo usa el propio recorrido.
    """
    import httpx

    if cuerpo is None:
        respuesta = httpx.get(
            f"{DIRECCION}{camino}", headers={"Authorization": f"Bearer {token}"}, timeout=30
        )
    else:
        respuesta = httpx.post(
            f"{DIRECCION}{camino}",
            data={"datos": json.dumps(cuerpo)},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
    try:
        return (respuesta.status_code, respuesta.json())
    except ValueError:
        return (respuesta.status_code, {"crudo": respuesta.text[:200]})


def main() -> int:
    volumen, _ = datos._la_del_volumen(  # noqa: SLF001
        DIRECCION, f"duplicado{int(time.time())}", pathlib.Path(tempfile.mkdtemp()), False
    )
    print(f"  la sesión: {volumen.nombre}")

    la_factura = {
        "fecha": "2026-10-05",
        "proveedor": "Suministros del Paramo, S.L.",
        "proveedor_nif": "B12345678",
        "numero_factura": "F-2026-0001",
        "base_imponible": 1000,
        "cuota_iva": 21,
        "total": 1210,
        # La línea, como la manda la pantalla: los mismos campos del formulario.
        "lineas": [
            {
                "descripcion": "Abono compuesto 15-15-15",
                "cantidad": 500,
                "unidad": "kg",
                "precio": 2,
                "importe": 1000,
            }
        ],
    }

    primera, respuesta_primera = llamar("/api/facturas", volumen.token, {"datos": la_factura})
    print(f"  la primera vez: HTTP {primera}")
    if primera >= 400:
        print(f"    (el servidor no acepta ni la primera: {str(respuesta_primera)[:160]})")
        print("=> sin una primera que entre, esto no se puede comprobar")
        return 1

    segunda, respuesta_segunda = llamar("/api/facturas", volumen.token, {"datos": la_factura})
    print(f"  la MISMA otra vez: HTTP {segunda}")
    if segunda >= 400:
        print(f"    (y dice por qué: {str(respuesta_segunda)[:160]})")

    _, las_guardadas = llamar("/api/facturas", volumen.token)
    cuantas = len(las_guardadas) if isinstance(las_guardadas, list) else len(
        (las_guardadas or {}).get("facturas") or []
    )
    print(f"  facturas que hay ahora en el servidor: {cuantas}")

    if segunda < 400 and cuantas >= 2:
        print("\n=> HALLAZGO: DOS ENVIOS CREAN DOS FACTURAS. No hay proteccion contra el duplicado.")
        return 0
    if segunda < 400:
        print(f"\n=> el segundo envio paso, pero hay {cuantas}: mira si comparte fila (huella?) antes de concluir")
        return 1
    print("\n=> PROTEGIDO: el servidor rechaza la repeticion (y dice por que)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
