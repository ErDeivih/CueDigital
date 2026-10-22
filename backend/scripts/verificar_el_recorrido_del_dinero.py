"""***El recorrido del dinero: venta -> factura -> cobro parcial -> pendiente*** (22/10/2026, D05).

*El tercero de los cuatro cortes de experiencia. Se anda **por las puertas de verdad** y se comprueba lo que el
contrato pide con nombre y apellidos: **A06** -una factura de 121 con un pago de 40 deja 81 pendientes- y que los
totales que se ven **cuadren con lo que hay**.*

Uso:  python scripts/verificar_el_recorrido_del_dinero.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


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


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "dinero@prueba.local", "una-clave-larga-y-facil", "Di")
        el_vale = cuenta["token"]
        print(f"== Venta -> factura -> cobro parcial -> pendiente  ({direccion}) ==")
        _, la_campana = _llamar(direccion, "/api/campanas/actual", token=el_vale)
        la_campana_id = (la_campana or {}).get("id")

        # ---- 1 · la venta, con su importe ----
        codigo, la_venta = _llamar(
            direccion,
            "/api/ventas",
            token=el_vale,
            metodo="POST",
            cuerpo={
                "campana_id": la_campana_id,
                "tipo": "comercializada",
                "fecha": "2026-07-15",
                "producto": "Cebada",
                "cantidad": 8.0,
                "unidad": "t",
                "comprador": "Cooperativa de la Prueba",
                "importe": "121.00",
            },
        )
        print(f"  (la venta: {codigo} {str(la_venta)[:100]})")
        fallos += not comprobar(codigo in (200, 201), "***la venta se apunta, con su importe***", str(la_venta))
        la_venta_id = la_venta.get("id") if isinstance(la_venta, dict) else None

        # ---- 2 · la factura ----
        codigo, la_factura = _llamar(
            direccion,
            "/api/facturas-emitidas",
            token=el_vale,
            metodo="POST",
            cuerpo={"fecha": "2026-07-16", "entregas": [la_venta_id]},
        )
        print(f"  (la factura: {codigo} {str(la_factura)[:100]})")
        fallos += not comprobar(codigo in (200, 201), "***la entrega se factura***", str(la_factura))
        la_factura_id = la_factura.get("id") if isinstance(la_factura, dict) else None

        # ---- 3 · el cobro parcial ----
        el_cobro = None
        if la_factura_id:
            codigo, el_cobro = _llamar(
                direccion,
                "/api/cobros",
                token=el_vale,
                metodo="POST",
                cuerpo={
                    "fecha": "2026-07-20",
                    "importe": "40.00",
                    "factura_emitida_id": la_factura_id,
                    "clave_de_reenvio": "cobro-parcial-40",
                },
            )
            print(f"  (el cobro: {codigo} {str(el_cobro)[:100]})")
            fallos += not comprobar(codigo in (200, 201), "***se apunta un cobro PARCIAL de 40***", str(el_cobro))

        # ---- 4 · el pendiente, que es lo que importa ----
        if la_factura_id:
            _, la_leida = _llamar(direccion, f"/api/facturas-emitidas/{la_factura_id}", token=el_vale)
            el_pendiente = str((la_leida or {}).get("pendiente") or "")
            print(f"  (la factura dice: pendiente {el_pendiente!r})")
            # ***A06.*** *De 121 pagados 40 quedan 81 -y **el pendiente no es cero**, que es el defecto que tendria
            # un programa que diera la factura por cobrada al primer pago-.*
            fallos += not comprobar(
                el_pendiente.startswith("81"),
                f"***de 121 pagados 40 quedan 81*** (dice {el_pendiente!r})",
            )

        # ---- 5 · y lo que se ve ----
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)
            las_ventas = abrir(nav, direccion, "#/ventas")
            fallos += not comprobar(
                "121" in las_ventas,
                "***la venta sale en la tabla, con su importe***",
                las_ventas,
            )
            # ***Y el registro de verdad: la FACTURA, por su ID.*** *`react/rutas.js` da los patrones, y una
            # venta **no tiene ficha** -es una fila de la tabla-, pero la factura si: `#/ventas/facturas/:id`.*
            la_factura_abierta = abrir(nav, direccion, f"#/ventas/facturas/{la_factura_id}")
            fallos += not comprobar(
                "no lleva a ninguna parte" not in la_factura_abierta and "81" in la_factura_abierta,
                f"***`#/ventas/facturas/{la_factura_id}` abre la factura, con su pendiente***",
                la_factura_abierta,
            )
            # *Y aguanta la recarga.*
            la_factura_otra_vez = abrir(nav, direccion, f"#/ventas/facturas/{la_factura_id}")
            fallos += not comprobar(
                la_factura_otra_vez == la_factura_abierta,
                "***y al recargarla, lo mismo: el enlace es permanente***",
                la_factura_otra_vez,
            )

    print(f"\nComprobaciones: 7   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
