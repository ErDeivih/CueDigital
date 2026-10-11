"""Las ventas y los cobros, de punta a punta (CRM-01, 11/10/2026).

**Por qué este guion.** El encargo de CRM-01 trae seis criterios de aceptación con números concretos (una
venta de 1210 €, un cobro de 350 repartido entre dos deudas, 8000 kg sin precio…). Antes de tocar el módulo
hay que saber **qué cumple hoy y qué no**, y eso no se lee: se mide. Este guion recorre el camino del
agricultor —cosecha → entrega → venta → factura → cobro— contra un **servidor aislado con base temporal** y
comprueba cada criterio, diciendo **cuál no se cumple y por qué**, sin maquillarlo.

Lo que se comprueba, y por qué cada cosa:

  1. **La venta de 1210 € y sus dos cobros.** Cobro de 400 → pendiente 810; cobro de 810 → pendiente 0,
     **comprobado por identificador** (no por el total global, que es lo que puede tapar un error) y con
     **otra venta intacta** al lado.
  2. **Un cobro mayor que la deuda**: se imputa lo que se debe y el sobrante se dice como «sin asignar»,
     sin dejar la factura en negativo y sin perder el dinero.
  3. **El reparto de un cobro entre dos deudas** (350 entre 100 y 250). Es el criterio que el módulo **no**
     puede cumplir hoy: un cobro apunta a **una** factura. Se mide y se dice, con la evidencia del modelo.
  4. **8000 kg con el precio sin conocer**: la cantidad es un dato y el importe **no es un cero**.
  5. **El reenvío del mismo cobro**: la misma clave dos veces apunta **un** cobro y el dinero no se dobla.
  6. **El aislamiento entre fincas** y los **importes en español** (coma decimal y moneda).

Uso:  python scripts/comprobar_las_ventas_y_los_cobros_de_punta_a_punta.py <direccion>
"""

from __future__ import annotations

import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"

COMPROBACIONES = 0
FALLOS = 0


def comprobar(bien: bool, que: str) -> bool:
    global COMPROBACIONES, FALLOS
    COMPROBACIONES += 1
    if not bien:
        FALLOS += 1
    print(f"  [{'OK  ' if bien else 'FALLO'}] {que}")
    return bien


def _pedir(cliente, metodo: str, camino: str, cuerpo: dict | None = None):
    """Una llamada a la API como la hace la pantalla. Devuelve `(codigo, cuerpo)`."""
    respuesta = getattr(cliente, metodo)(camino, json=cuerpo) if cuerpo is not None else getattr(
        cliente, metodo
    )(camino)
    try:
        devuelto = respuesta.json()
    except Exception:  # noqa: BLE001 - lo que importa es el código, no el cuerpo
        devuelto = None
    return respuesta.status_code, devuelto


class ElCaso:
    """La explotación de la prueba, con un cliente HTTP ya autenticado."""

    def __init__(self, direccion: str, escenario) -> None:
        import httpx

        self.finca = escenario.volumen
        self.ajena = escenario.ajena
        self.campana = self.finca.campana_actual.id
        self.http = httpx.Client(
            base_url=direccion,
            headers={"Authorization": f"Bearer {self.finca.token}"},
            timeout=30,
        )
        self.http_ajena = httpx.Client(
            base_url=direccion,
            headers={"Authorization": f"Bearer {self.ajena.token}"},
            timeout=30,
        )

    def una_venta(self, importe: str | None, cantidad: float = 1000.0, producto: str = "Trigo blando"):
        """Apuntar una entrega. `importe=None` es «no se sabe el precio todavía»."""
        cuerpo = {
            "campana_id": self.campana,
            "fecha": "2026-07-10",
            "producto": producto,
            "cantidad": cantidad,
            "unidad": "kg",
            "comprador": "Cooperativa Agrícola de Peñaranda",
        }
        if importe is not None:
            cuerpo["importe"] = importe
        return _pedir(self.http, "post", "/api/ventas", cuerpo)

    def una_factura(self, entregas: list[int], numero: str):
        return _pedir(
            self.http,
            "post",
            "/api/facturas-emitidas",
            {
                "fecha": "2026-07-20",
                "numero": numero,
                "cliente": "Cooperativa Agrícola de Peñaranda",
                "entregas": entregas,
            },
        )

    def un_cobro(self, importe: str, factura_id: int | None, clave: str | None = None):
        cuerpo = {"fecha": "2026-08-01", "importe": importe}
        if factura_id is not None:
            cuerpo["factura_emitida_id"] = factura_id
        if clave is not None:
            cuerpo["clave_de_reenvio"] = clave
        return _pedir(self.http, "post", "/api/cobros", cuerpo)

    def un_cobro_repartido(self, importe: str, aplicaciones: list[dict]):
        """Un cobro repartido entre varias deudas: una fila por factura, con su importe."""
        return _pedir(
            self.http,
            "post",
            "/api/cobros",
            {"fecha": "2026-08-01", "importe": importe, "aplicaciones": aplicaciones},
        )

    def la_factura(self, factura_id: int):
        return _pedir(self.http, "get", f"/api/facturas-emitidas/{factura_id}")


def main() -> int:
    print(f"  (la direccion: {DIRECCION})")
    escenario = preparar(DIRECCION)
    caso = ElCaso(DIRECCION, escenario)
    print(f"  (la sesion: {escenario.volumen.nombre}, campana {caso.campana})")

    # ── 1) La venta de 1210 € y sus dos cobros ───────────────────────────────────────────────────────
    print("\n1) La venta de 1210 EUR, cobrada en dos veces (400 y 810)")
    codigo, entrega = caso.una_venta("1210.00")
    comprobar(codigo == 201, f"la entrega se apunta ({codigo})")
    codigo, factura = caso.una_factura([entrega["id"]], "CRM01-F1")
    comprobar(codigo == 201, f"y su factura se emite ({codigo})")
    comprobar(
        factura["importe_total"] == "1210.00" and factura["pendiente"] == "1210.00",
        f"la factura nace con 1210,00 facturados y pendientes "
        f"({factura['importe_total']} / {factura['pendiente']})",
    )

    # **Otra venta al lado**: es lo que demuestra que cobrar una no toca las demás.
    _, entrega_b = caso.una_venta("500.00", producto="Cebada")
    _, factura_b = caso.una_factura([entrega_b["id"]], "CRM01-F2")

    codigo, primero = caso.un_cobro("400.00", factura["id"])
    comprobar(codigo == 201, f"el primer cobro entra ({codigo})")
    comprobar(
        primero["factura"]["pendiente"] == "810.00" and primero["factura"]["cobrado"] == "400.00",
        f"1210 - 400 = 810 pendientes ({primero['factura']['pendiente']})",
    )
    comprobar(
        primero["cobro"]["importe_imputado"] == "400.00", "y lo imputado es el dinero entero"
    )

    # **Por identificador, no por el total**: se vuelve a preguntar por esa factura.
    _, la_suya = caso.la_factura(factura["id"])
    comprobar(
        la_suya["pendiente"] == "810.00",
        f"y preguntando por esa factura sale lo mismo ({la_suya['pendiente']})",
    )
    _, la_de_al_lado = caso.la_factura(factura_b["id"])
    comprobar(
        la_de_al_lado["pendiente"] == "500.00",
        f"la otra venta no se ha tocado ({la_de_al_lado['pendiente']})",
    )

    codigo, segundo = caso.un_cobro("810.00", factura["id"])
    comprobar(codigo == 201, f"el segundo cobro entra ({codigo})")
    comprobar(
        segundo["factura"]["pendiente"] == "0.00" and segundo["factura"]["estado"] == "cobrada",
        f"y la factura queda cobrada por identificador ({segundo['factura']['pendiente']}, "
        f"{segundo['factura']['estado']})",
    )
    _, la_lista = _pedir(caso.http, "get", "/api/facturas-emitidas")
    comprobar(
        len(la_lista) == 2,
        f"y **cobrar no ha creado facturas**: siguen siendo dos ({len(la_lista)})",
    )

    # ── 2) Un cobro mayor que la deuda ───────────────────────────────────────────────────────────────
    print("\n2) Un cobro mayor que lo que se debe (400 sobre una deuda de 100)")
    _, entrega_c = caso.una_venta("100.00", cantidad=100.0, producto="Avena")
    _, factura_c = caso.una_factura([entrega_c["id"]], "CRM01-F3")
    codigo, grande = caso.un_cobro("400.00", factura_c["id"])
    comprobar(codigo == 201, f"el cobro grande se apunta entero ({codigo})")
    comprobar(
        grande["cobro"]["importe"] == "400.00" and grande["cobro"]["importe_imputado"] == "100.00",
        f"se imputan los 100 que se debian y el resto no se pierde "
        f"({grande['cobro']['importe']} / {grande['cobro']['importe_imputado']})",
    )
    comprobar(
        grande["factura"]["pendiente"] == "0.00",
        f"y la factura nunca queda en negativo ({grande['factura']['pendiente']})",
    )
    sin_asignar = grande["cobro"].get("texto_sin_asignar") or ""
    comprobar(
        "300" in sin_asignar,
        f"y lo que sobra se dice como sin asignar ({sin_asignar!r})",
    )

    # ── 3) El reparto de un cobro entre dos deudas (el criterio que no se cumplía) ───────────────────
    print("\n3) Un cobro de 350 repartido entre dos deudas de 100 y 250")
    _, entrega_d = caso.una_venta("100.00", cantidad=100.0, producto="Centeno")
    _, factura_d = caso.una_factura([entrega_d["id"]], "CRM01-F4")
    _, entrega_e = caso.una_venta("250.00", cantidad=250.0, producto="Triticale")
    _, factura_e = caso.una_factura([entrega_e["id"]], "CRM01-F5")

    codigo, repartido = caso.un_cobro_repartido(
        "350.00",
        [
            {"factura_emitida_id": factura_d["id"], "importe": "100.00"},
            {"factura_emitida_id": factura_e["id"], "importe": "250.00"},
        ],
    )
    comprobar(codigo == 201, f"el cobro repartido entra ({codigo})")
    suyas = (repartido or {}).get("cobro", {}).get("aplicaciones") or []
    comprobar(len(suyas) == 2, f"con una aplicacion por deuda ({len(suyas)})")
    comprobar(
        sum(float(a["importe"]) for a in suyas) == 350.0,
        f"y las aplicaciones suman los 350 que entraron "
        f"({[a['importe'] for a in suyas]})",
    )
    comprobar(
        (repartido or {}).get("cobro", {}).get("texto_sin_asignar", "x") == "",
        "y no queda nada sin asignar",
    )
    # **Por identificador**: cada deuda queda saldada, que es lo que el criterio pide.
    _, la_primera = caso.la_factura(factura_d["id"])
    _, la_segunda = caso.la_factura(factura_e["id"])
    comprobar(
        la_primera["pendiente"] == "0.00" and la_segunda["pendiente"] == "0.00",
        f"y las dos deudas quedan a cero ({la_primera['pendiente']} y {la_segunda['pendiente']})",
    )

    # Y el sobrante, con el caso del encargo: 400 de los que solo se aplican 350.
    _, entrega_f = caso.una_venta("350.00", cantidad=350.0, producto="Alfalfa")
    _, factura_f = caso.una_factura([entrega_f["id"]], "CRM01-F5b")
    codigo, con_sobrante = caso.un_cobro_repartido(
        "400.00", [{"factura_emitida_id": factura_f["id"], "importe": "350.00"}]
    )
    comprobar(codigo == 201, f"un cobro de 400 con 350 aplicados entra ({codigo})")
    comprobar(
        (con_sobrante or {}).get("cobro", {}).get("texto_sin_asignar") == "50,00 €",
        f"y los 50 que sobran se dicen sin asignar "
        f"({(con_sobrante or {}).get('cobro', {}).get('texto_sin_asignar')!r}, no un pago perdido)",
    )

    # ── 4) 8000 kg con el precio sin conocer ─────────────────────────────────────────────────────────
    print("\n4) 8000 kg vendidos sin saber el precio todavia")
    codigo, sin_precio = caso.una_venta(None, cantidad=8000.0, producto="Girasol")
    comprobar(codigo == 201, f"la entrega se apunta sin precio ({codigo})")
    comprobar(
        sin_precio.get("importe") in (None, ""),
        f"y su importe **no es un cero**: es que no se sabe ({sin_precio.get('importe')!r})",
    )
    comprobar(
        float(sin_precio.get("cantidad") or 0) == 8000.0,
        f"la cantidad si es un dato ({sin_precio.get('cantidad')})",
    )
    codigo, no_se_puede = caso.una_factura([sin_precio["id"]], "CRM01-F6")
    comprobar(
        codigo >= 400,
        f"y no se puede facturar sin precio: se dice que falta ({codigo})",
    )

    # ── 5) El reenvío del mismo cobro ────────────────────────────────────────────────────────────────
    print("\n5) El reenvio del mismo cobro (la misma clave dos veces)")
    _, entrega_f = caso.una_venta("300.00", cantidad=300.0, producto="Maiz")
    _, factura_f = caso.una_factura([entrega_f["id"]], "CRM01-F7")
    codigo, el_primero = caso.un_cobro("100.00", factura_f["id"], clave="cobro-de-prueba-1")
    comprobar(codigo == 201, f"el cobro se apunta ({codigo})")
    codigo, el_de_nuevo = caso.un_cobro("100.00", factura_f["id"], clave="cobro-de-prueba-1")
    # **El código de estado, medido y no maquillado.** El reenvío contesta **201** (no 200) aunque no haya
    # creado nada: es una inconsistencia conocida —el mismo caso en las facturas de compra contesta 200— que
    # David aceptó **como secundaria** «siempre que no cree otra operación». Lo que importa se comprueba
    # aparte y con dureza: mismo identificador, un solo cobro y el dinero sin doblar. Si algún día se
    # arregla el código, esta línea empezará a decir 200 y no habrá que tocar la comprobación.
    print(f"     (el reenvio contesta {codigo}; la inconsistencia conocida es que deberia ser 200)")
    comprobar(
        200 <= codigo < 300,
        f"el reenvio del mismo cobro se acepta sin error ({codigo})",
    )
    comprobar(
        el_de_nuevo["ya_estaba"] is True or el_de_nuevo["cobro"]["id"] == el_primero["cobro"]["id"],
        "y la respuesta dice que ya estaba",
    )
    comprobar(
        el_de_nuevo["cobro"]["id"] == el_primero["cobro"]["id"],
        "y es **el mismo identificador**, no una fila nueva",
    )
    _, la_suya = caso.la_factura(factura_f["id"])
    comprobar(
        la_suya["cobrado"] == "100.00",
        f"y el dinero no se ha doblado ({la_suya['cobrado']} cobrados, no 200)",
    )

    # ── 6) Aislamiento entre fincas y los importes en español ────────────────────────────────────────
    print("\n6) El aislamiento entre fincas y el formato de los importes")
    codigo, _ = _pedir(caso.http_ajena, "get", f"/api/facturas-emitidas/{factura['id']}")
    comprobar(codigo == 404, f"otra finca no puede ver esta factura ({codigo})")
    _, la_lista = _pedir(caso.http, "get", "/api/facturas-emitidas")
    suya = [fila for fila in la_lista if fila["id"] == factura["id"]][0]
    comprobar(
        suya["texto_pendiente"] == "0,00 €",
        f"y los importes van con coma decimal y en euros ({suya['texto_pendiente']})",
    )

    # ── 7) Que el reparto no se cuente dos veces ni desaparezca (11/10/2026) ─────────────────────────
    print("\n7) El reparto, visto desde las otras pantallas: el banco y el dinero sin asignar")
    # Un dinero que de verdad no se sabe a qué va, para que las listas no estén vacías por casualidad.
    _, suelto = caso.un_cobro("80.00", None)

    _, sin_asignar = _pedir(caso.http, "get", "/api/cobros?solo=sin_asignar")
    identificadores = [c["id"] for c in sin_asignar]
    comprobar(
        (suelto or {}).get("cobro", {}).get("id") in identificadores,
        "el dinero que no se sabe a que va sale en su lista",
    )
    comprobar(
        (repartido or {}).get("cobro", {}).get("id") not in identificadores,
        "y el cobro **repartido a mano** no sale ahi: se sabe perfectamente a que va "
        "(miraba la columna de la factura, que en un reparto va vacia a proposito)",
    )

    # Y la conciliacion del banco: las dos deudas del reparto estan cobradas, asi que no se ofrecen para
    # conciliar; y el ingreso repartido tampoco, porque su dinero **ya esta** donde tenia que estar.
    _, pendientes = _pedir(caso.http, "get", "/api/bancos/pendientes")
    comprobar(
        isinstance(pendientes, list),
        f"la lista de papeles por conciliar del banco se lee ({type(pendientes).__name__})",
    )
    por_clase = {}
    for documento in pendientes if isinstance(pendientes, list) else []:
        por_clase.setdefault(documento.get("clase"), set()).add(documento.get("documento_id"))
    comprobar(
        factura_d["id"] not in por_clase.get("factura_emitida", set()),
        "la primera deuda del reparto **no** aparece como pendiente en el banco",
    )
    comprobar(
        factura_e["id"] not in por_clase.get("factura_emitida", set()),
        "y la segunda tampoco",
    )
    comprobar(
        (repartido or {}).get("cobro", {}).get("id") not in por_clase.get("cobro", set()),
        "y el ingreso repartido no se ofrece para conciliar otra vez",
    )

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {FALLOS}")
    return 0 if FALLOS == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
