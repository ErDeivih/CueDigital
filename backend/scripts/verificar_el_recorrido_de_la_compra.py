"""***El segundo recorrido: compra -> recepcion -> lote -> gasto -> pago*** (22/10/2026, D05).

*El mas largo de los cuatro. Se anda **por las puertas de verdad**, paso a paso, y **se dice el codigo de cada una**:
lo que se pueda andar, se anda; lo que no, se queda escrito con su codigo y su motivo.*

Uso:  python scripts/verificar_el_recorrido_de_la_compra.py
"""

from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

EL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def con_formulario(direccion: str, camino: str, el_vale: str, datos: dict) -> tuple[int, object]:
    """*Un multipart con `datos` y un fichero, como manda la pantalla.*"""
    el_limite = "----prueba"
    el_cuerpo = b"".join([
        f"--{el_limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="datos"\r\n\r\n',
        json.dumps(datos).encode("utf-8"),
        b"\r\n",
        f"--{el_limite}\r\n".encode(),
        b'Content-Disposition: form-data; name="fichero"; filename="factura.png"\r\n',
        b"Content-Type: image/png\r\n\r\n",
        EL_PNG,
        b"\r\n",
        f"--{el_limite}--\r\n".encode(),
    ])
    la_peticion = urllib.request.Request(
        f"{direccion}{camino}",
        data=el_cuerpo,
        method="POST",
        headers={
            "Authorization": f"Bearer {el_vale}",
            "Content-Type": f"multipart/form-data; boundary={el_limite}",
        },
    )
    try:
        with urllib.request.urlopen(la_peticion, timeout=30) as la_respuesta:
            return la_respuesta.status, json.loads(la_respuesta.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as el_error:
        return el_error.code, el_error.read().decode("utf-8", "replace")


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> str:
    el_ultimo = ""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(30):
            el_ultimo = el_texto(nav)
            if el_ultimo and el_ultimo == anterior:
                return el_ultimo
            anterior = el_ultimo
            time.sleep(0.4)
    return el_ultimo


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:300]!r}")
    return bien


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "compra@prueba.local", "una-clave-larga-y-facil", "Co")
        el_vale = cuenta["token"]
        print(f"== Compra -> recepcion -> lote -> gasto -> pago  ({direccion}) ==")
        _, la_campana = _llamar(direccion, "/api/campanas/actual", token=el_vale)
        la_campana_id = (la_campana or {}).get("id")

        # ---- 1 · la compra ----
        codigo, la_compra = con_formulario(
            direccion,
            "/api/facturas",
            el_vale,
            {
                "proveedor": "SUMAGRO",
                "numero_factura": "F-2026-001",
                "fecha": "2026-07-10",
                "base_imponible": "100.00",
                "cuota_iva": "21.00",
                "total": "121.00",
            },
        )
        print(f"  (la compra: {codigo} {str(la_compra)[:160]})")
        fallos += not comprobar(codigo in (200, 201), "***la compra se da de alta***", str(la_compra))
        la_compra_id = la_compra.get("id") if isinstance(la_compra, dict) else None

        # ---- 2 · el articulo y el lote ----
        codigo, el_articulo = _llamar(
            direccion,
            "/api/almacen/articulos",
            token=el_vale,
            metodo="POST",
            cuerpo={"nombre": "PRODUCTO DEL ALMACEN", "unidad": "L"},
        )
        print(f"  (el articulo: {codigo} {str(el_articulo)[:120]})")
        el_articulo_id = el_articulo.get("id") if isinstance(el_articulo, dict) else None

        codigo, el_lote = _llamar(
            direccion,
            "/api/almacen/lotes",
            token=el_vale,
            metodo="POST",
            cuerpo={"articulo_id": el_articulo_id, "numero_lote": "LOTE-2026-1", "cantidad": 100.0},
        )
        print(f"  (el lote: {codigo} {str(el_lote)[:120]})")
        fallos += not comprobar(codigo in (200, 201), "***el lote se da de alta en el almacen***", str(el_lote))
        el_lote_id = el_lote.get("id") if isinstance(el_lote, dict) else None

        # ---- 3 · la recepcion ----
        codigo, la_recepcion = _llamar(
            direccion,
            "/api/almacen/recepciones",
            token=el_vale,
            metodo="POST",
            # ***El albaran lleva LINEAS***: *lo dice `RecepcionEntrada` -`lineas: list[...]`-, y el error lo decia
            # con otras palabras: «escribe **que producto, cuanto y de que lote**». Se probo a ponerlo suelto en la
            # raiz y no cuela: **cada cosa que llega es una linea**.*
            cuerpo={
                "fecha": "2026-07-10",
                "proveedor": "SUMAGRO",
                "numero_albaran": "ALB-2026-1",
                "factura_id": la_compra_id,
                "lineas": [
                    {
                        "articulo_id": el_articulo_id,
                        "cantidad": 100.0,
                        "lote": "LOTE-2026-1",
                    }
                ],
            },
        )
        print(f"  (la recepcion: {codigo} {str(la_recepcion)[:160]})")
        fallos += not comprobar(
            codigo in (200, 201), "***lo comprado se recibe en el almacen***", str(la_recepcion)
        )

        # ---- 4 · el gasto ----
        codigo, el_gasto = _llamar(
            direccion,
            "/api/gastos",
            token=el_vale,
            metodo="POST",
            cuerpo={
                "campana_id": la_campana_id,
                "fecha": "2026-07-10",
                "concepto": "PRODUCTO DEL ALMACEN",
                "categoria": "fitosanitario",
                "proveedor": "SUMAGRO",
                "importe": "121.00",
                "clave_de_reenvio": "gasto-compra-1",
            },
        )
        print(f"  (el gasto: {codigo} {str(el_gasto)[:160]})")
        fallos += not comprobar(codigo in (200, 201), "***el gasto se apunta***", str(el_gasto))
        el_gasto_id = el_gasto.get("id") if isinstance(el_gasto, dict) else None

        # ---- 5 · el pago ----
        if el_gasto_id:
            codigo, el_pago = _llamar(
                direccion,
                "/api/gastos/pagos",
                token=el_vale,
                metodo="POST",
                cuerpo={
                    "fecha": "2026-07-20",
                    "importe": "60.00",
                    "gasto_id": el_gasto_id,
                    "clave_de_reenvio": "pago-compra-1",
                },
            )
            print(f"  (el pago: {codigo} {str(el_pago)[:160]})")
            fallos += not comprobar(codigo in (200, 201), "***y se paga, en parte***", str(el_pago))

        # ---- 6 · y lo que se ve: la compra, por su ID ----
        # *`#/compras/:id` esta en la tabla de patrones, y se miro antes de escribir la direccion.*
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)
            la_compra_abierta = abrir(nav, direccion, f"#/compras/{la_compra_id}")
            fallos += not comprobar(
                "no lleva a ninguna parte" not in la_compra_abierta and "SUMAGRO" in la_compra_abierta,
                f"***`#/compras/{la_compra_id}` abre la compra, con su proveedor***",
                la_compra_abierta,
            )
            la_otra = abrir(nav, direccion, f"#/compras/{la_compra_id}")
            fallos += not comprobar(
                la_otra == la_compra_abierta,
                "***y aguanta la recarga***",
                la_otra,
            )


    print(f"\nComprobaciones: 7   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
