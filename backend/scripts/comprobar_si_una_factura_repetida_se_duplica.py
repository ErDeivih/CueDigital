"""¿Protege el servidor contra apuntar **la misma factura** dos veces? (08/10/2026, corregido el 09/10/2026)

**Por qué.** El recorrido económico crea la factura **desde la pantalla** y, al pulsar guardar otra vez, el botón
está **deshabilitado** -medido-, así que no había segundo envío. Mi comprobación de «no duplica» era, por tanto,
**vacua**, como demostró el revisor independiente. Y el servidor no ayudaba: `models.Factura` **no tenía clave de
reenvío** y `POST /api/facturas` no comprobaba duplicados.

**Este guion tenía un defecto de instrumento, y se descubrió midiendo** (09/10/2026): `llamar` ya envuelve el
cuerpo en el campo `datos`, y los sitios donde se le llamaba le pasaban **otra vez** `{"datos": ...}`. El
servidor recibía `{"datos": {...}}`, `FacturaEntrada` lo aceptaba —todos sus campos son opcionales— y guardaba
**facturas vacías**: se comprobó en la base y las dos filas tenían `proveedor`, `total` y `numero_factura` a
`None` y **cero líneas**. O sea que la conclusión («dos envíos crean dos facturas») era cierta **por casualidad**,
pero no probaba lo que decía probar. Ahora se manda la factura entera y se **exige que haya llegado**: sin esa
comprobación, el mismo error volvería a pasar sin que nadie se entere.

Uso:  python scripts/comprobar_si_una_factura_repetida_se_duplica.py <direccion>
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8190"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datos_representativos as datos  # noqa: E402

# Una factura **entera**, como la manda la pantalla: con sus líneas, su proveedor y su total.
LA_FACTURA = {
    "fecha": "2026-10-05",
    "proveedor": "Suministros del Paramo, S.L.",
    "proveedor_nif": "B12345678",
    "numero_factura": "F-2026-0001",
    "base_imponible": 170.0,
    "cuota_iva": 35.70,
    "tipo_iva_pct": 21.0,
    "total": 205.70,
    "leida_por": "a mano",
    "lineas": [
        {
            "descripcion": "Abono compuesto 15-15-15",
            "cantidad": 500,
            "unidad": "kg",
            "precio_unitario": 0.34,
            "importe": 170.0,
        }
    ],
}


def llamar(camino: str, token: str, cuerpo: dict | None = None):
    """Llama a la API **como la llama la pantalla**, y devuelve (código, respuesta) sin lanzar.

    **Con `httpx` y en `multipart`** (08/10/2026): el servidor espera el cuerpo con el campo de formulario
    `datos` -medido dos veces: en JSON plano contesta `{'loc': ['body', 'datos'], 'msg': 'Field required'}`-, y la
    pantalla lo manda así. **El envoltorio lo pone aquí**, así que quien llame le pasa el cuerpo **pelado**.
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

    primera, respuesta_primera = llamar(
        "/api/facturas", volumen.token, {**LA_FACTURA, "clave_de_reenvio": "peticion-1"}
    )
    print(f"  la primera vez: HTTP {primera}")
    if primera >= 400:
        print(f"    (el servidor no acepta ni la primera: {str(respuesta_primera)[:200]})")
        print("=> sin una primera que entre, esto no se puede comprobar")
        return 1

    # **Que la factura ha llegado de verdad.** Es la comprobación que le faltaba a este guion: sin ella,
    # mandar un cuerpo vacío daba «201» y el guion se lo creía.
    print(f"  y ha llegado entera: total {respuesta_primera.get('total')!r}, "
          f"proveedor {respuesta_primera.get('proveedor')!r}, "
          f"{len(respuesta_primera.get('lineas') or [])} linea(s)")
    if respuesta_primera.get("total") is None or not respuesta_primera.get("lineas"):
        print("=> el instrumento esta roto: el servidor ha guardado una factura VACIA, "
              "asi que lo que se compruebe despues no vale")
        return 1

    # ── 1. El reenvío técnico: la misma petición, otra vez ────────────────────────────────────────────
    segunda, respuesta_segunda = llamar(
        "/api/facturas", volumen.token, {**LA_FACTURA, "clave_de_reenvio": "peticion-1"}
    )
    print(f"\n  la MISMA peticion otra vez: HTTP {segunda}  (id {respuesta_segunda.get('id')!r}, "
          f"ya_estaba {respuesta_segunda.get('ya_estaba')!r}, "
          f"como {respuesta_segunda.get('como_se_reconocio')!r})")
    _, las_guardadas = llamar("/api/facturas", volumen.token)
    cuantas = len(las_guardadas) if isinstance(las_guardadas, list) else len(
        (las_guardadas or {}).get("facturas") or []
    )
    print(f"  facturas que hay ahora en el servidor: {cuantas}")

    bien_el_reenvio = (
        segunda == 200
        and respuesta_segunda.get("id") == respuesta_primera.get("id")
        and respuesta_segunda.get("ya_estaba") is True
        and cuantas == 1
    )

    # ── 2. El posible duplicado comercial: otra petición, el mismo papel ──────────────────────────────
    tercera, respuesta_tercera = llamar(
        "/api/facturas", volumen.token, {**LA_FACTURA, "clave_de_reenvio": "peticion-2"}
    )
    print(f"\n  el mismo papel con OTRA peticion: HTTP {tercera}  "
          f"(id {respuesta_tercera.get('id')!r}, como {respuesta_tercera.get('como_se_reconocio')!r})")
    _, las_de_ahora = llamar("/api/facturas", volumen.token)
    cuantas_ahora = len(las_de_ahora) if isinstance(las_de_ahora, list) else len(
        (las_de_ahora or {}).get("facturas") or []
    )
    print(f"  facturas que hay ahora: {cuantas_ahora}")

    bien_el_papel = (
        tercera == 200
        and respuesta_tercera.get("como_se_reconocio") == "numero_de_factura"
        and cuantas_ahora == 1
    )

    # ── 3. El conflicto claro: la misma petición con otros datos ──────────────────────────────────────
    cuarta, respuesta_cuarta = llamar(
        "/api/facturas", volumen.token, {**LA_FACTURA, "total": 999.99, "clave_de_reenvio": "peticion-1"}
    )
    print(f"\n  la MISMA peticion con OTROS datos: HTTP {cuarta}")
    if cuarta >= 400:
        print(f"    (y dice: {str(respuesta_cuarta.get('detail'))[:120]})")
    bien_el_conflicto = cuarta == 409

    print()
    if bien_el_reenvio and bien_el_papel and bien_el_conflicto:
        print("=> PROTEGIDO: el reenvio devuelve la misma factura (200, una sola fila), el mismo papel se "
              "reconoce como posible duplicado, y la misma peticion con otros datos es un 409.")
        return 0
    print("=> NO PROTEGIDO: mira los tres resultados de arriba; el que falle dice por donde se cuela.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
