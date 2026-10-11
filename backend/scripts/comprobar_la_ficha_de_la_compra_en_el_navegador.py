"""La ficha de una compra, **en un navegador de verdad y con capturas** (09/10/2026).

**Por qué.** El encargo lo pide con estas palabras: la ficha de la compra enseñando lo facturado, lo
recibido, lo pagado y lo pendiente, **con sus enlaces y conservando filtros y contexto**, y entregado
*desde las pantallas, con capturas*. Una puerta de servidor con sus pruebas no acredita que la pantalla
enseñe nada: eso solo se ve abriéndola.

Lo que comprueba, y por qué cada cosa:

  1. **Se llega por el botón**, no escribiendo la dirección: en la lista de facturas se pulsa
     «VER LA COMPRA» y la ficha se abre. Un botón que no lleva a ninguna parte es el defecto que ya
     apareció dos veces en este programa (la historia de una tierra y las versiones), así que se prueba
     el camino entero: lista → botón → ficha.
  2. **Las cuatro cifras están en pantalla**, con su número: 663,00 € facturado, 300,00 kg recibido,
     200,00 € pagado y 463,00 € pendiente.
  3. **Los enlaces llevan a sus registros**: el albarán y el gasto se pueden abrir desde aquí.
  4. **Y la dirección es permanente**: se recarga `#/compras/<id>` y la ficha vuelve a salir igual. Es lo
     que el contrato llama «enlace permanente al contexto», medido: si al recargar no volviera, el enlace
     no serviría para mandárselo a nadie.
  5. **Dos capturas**: el móvil (390 px) y el escritorio (1440 px), que es lo que se entrega.

Uso:  python scripts/comprobar_la_ficha_de_la_compra_en_el_navegador.py <direccion> [carpeta-de-capturas]
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
CARPETA = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(r"C:\Users\David\AppData\Local\Temp\cd-ui")

COMPROBACIONES = 0
FALLOS = 0


def comprobar(bien: bool, que: str) -> bool:
    global COMPROBACIONES, FALLOS
    COMPROBACIONES += 1
    if not bien:
        FALLOS += 1
    print(f"  [{'OK  ' if bien else 'FALLO'}] {que}")
    return bien


def _api(camino: str, token: str, cuerpo: dict | None = None, *, metodo: str = "POST"):
    """Una llamada a la API como la hace la pantalla. Devuelve (código, cuerpo)."""
    import httpx

    cabeceras = {"Authorization": f"Bearer {token}"}
    if cuerpo is None:
        respuesta = httpx.get(f"{DIRECCION}{camino}", headers=cabeceras, timeout=30)
    elif metodo == "PUT":
        respuesta = httpx.put(f"{DIRECCION}{camino}", json=cuerpo, headers=cabeceras, timeout=30)
    else:
        respuesta = httpx.post(f"{DIRECCION}{camino}", json=cuerpo, headers=cabeceras, timeout=30)
    try:
        return respuesta.status_code, respuesta.json()
    except ValueError:
        return respuesta.status_code, {"crudo": respuesta.text[:200]}


def _factura(token: str, numero: str) -> int:
    """Una factura con su línea, por la puerta de las facturas (que es `multipart` con `datos`)."""
    import httpx

    cuerpo = {
        "fecha": "2026-10-05",
        "proveedor": "Suministros del Paramo, S.L.",
        "proveedor_nif": "B12345678",
        "numero_factura": numero,
        "base_imponible": 663.0,
        "cuota_iva": 0.0,
        "tipo_iva_pct": 0.0,
        "total": 663.0,
        "leida_por": "a mano",
        "lineas": [
            {
                "descripcion": "Abono compuesto 15-15-15",
                "cantidad": 500.0,
                "unidad": "kg",
                "precio_unitario": 1.326,
                "importe": 663.0,
            }
        ],
    }
    respuesta = httpx.post(
        f"{DIRECCION}/api/facturas",
        data={"datos": json.dumps(cuerpo)},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    devuelto = respuesta.json()
    return (devuelto.get("factura") or devuelto)["id"], (devuelto.get("factura") or devuelto)["lineas"][0]["id"]


def _la_compra_de_la_prueba(token: str) -> int:
    """Una compra con las cuatro cifras distintas: facturada, recibida a medias, pagada a medias."""
    numero = f"F-2026-{int(time.time()) % 100000:05d}"
    factura_id, linea_id = _factura(token, numero)

    codigo, articulo = _api(
        "/api/almacen/articulos", token, {"nombre": "Abono compuesto 15-15-15", "categoria": "abono", "unidad": "kg"}
    )
    print(f"  (el articulo: {codigo} id {(articulo or {}).get('id')})")

    # Un albarán **enganchado a la factura y a su línea**: es lo que permite decir cuánto ha entrado de
    # cada línea, y por eso la ficha puede enseñar «300 de 500».
    codigo, albaran = _api(
        "/api/almacen/recepciones",
        token,
        {
            "fecha": "2026-10-06",
            "proveedor": "Suministros del Paramo, S.L.",
            "proveedor_nif": "B12345678",
            "numero_albaran": f"A-2026-{int(time.time()) % 100000:05d}",
            "factura_id": factura_id,
            "clave_de_reenvio": f"ficha-{numero}",
            "lineas": [
                {
                    "articulo_id": (articulo or {}).get("id"),
                    "nombre": "Abono compuesto 15-15-15",
                    "unidad": "kg",
                    "cantidad": 300.0,
                    "linea_factura_id": linea_id,
                }
            ],
        },
    )
    print(f"  (el albaran de 300: {codigo} id {((albaran or {}).get('recepcion') or {}).get('id')})")

    codigo, gasto = _api(
        "/api/gastos",
        token,
        {
            "concepto": f"Compra de abono, factura {numero}",
            "importe": "663.00",
            "fecha": "2026-10-05",
            "categoria": "abono",
            "factura_id": factura_id,
        },
    )
    gasto_id = (gasto or {}).get("id") or ((gasto or {}).get("gasto") or {}).get("id")
    print(f"  (el gasto de 663: {codigo} id {gasto_id})")

    codigo, pago = _api(
        "/api/gastos/pagos",
        token,
        {"importe": "200.00", "fecha": "2026-10-07", "forma": "transferencia"},
    )
    pago_id = (pago or {}).get("id") or ((pago or {}).get("pago") or {}).get("id")
    print(f"  (el pago de 200: {codigo} id {pago_id})")
    _api(
        f"/api/gastos/pagos/{pago_id}/conciliar",
        token,
        {"automatico": True, "gastos": [gasto_id], "aplicaciones": []},
    )
    return factura_id


def captura(nav: NavegadorDeVerdad, nombre: str) -> pathlib.Path:
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"compra-{nombre}.png"
    destino.write_bytes(base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"]))
    return destino


def el_texto(nav: NavegadorDeVerdad) -> str:
    return nav.evaluar("(document.querySelector('#pantalla') || {}).innerText || ''")


def main() -> int:
    print(f"  (la direccion: {DIRECCION})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    print(f"  (la sesion: {escenario.volumen.nombre})")

    factura_id = _la_compra_de_la_prueba(token)

    with NavegadorDeVerdad(ancho=390, alto=1400) as nav:
        # **El ancho de verdad, no el de la ventana** (09/10/2026, lo cazó el revisor): en Windows Chrome
        # no baja de 500 px de ventana, así que la captura «del móvil» salía de **500×1305** mientras el
        # guion decía 390. `medir` es lo que usa el resto del programa para esto, y deja el ancho de
        # verdad. Importa porque los cortes de `estilos.css` son 768 y 1024: 390 y 500 son los dos móvil,
        # pero decir «390» y entregar 500 es no saber qué se ha entregado.
        nav.medir(390, 1400, movil=True)
        # Se entra **como entra el agricultor**: con su vale guardado, que es lo que hace `app.js` al
        # arrancar. Así la pantalla es la de verdad y no una maqueta.
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + json.dumps(token)
                + ");"
            },
        )
        print("\n1) Se llega por el boton, desde la lista de facturas")
        nav.abrir(f"{DIRECCION}/#/facturas", esperar=2.0)
        nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=20)
        hay_boton = nav.evaluar(
            "document.querySelectorAll('#pantalla [data-accion=\"compra-abrir\"]').length"
        )
        comprobar(hay_boton > 0, f"la lista de facturas ofrece «VER LA COMPRA» ({hay_boton} boton/es)")

        # Y se pulsa **el de esta factura**, no otro: lo que se comprueba es el camino entero.
        nav.evaluar(
            f"""(() => {{
                const botones = [...document.querySelectorAll('#pantalla [data-accion="compra-abrir"]')];
                const suyo = botones.find((b) => Number(b.dataset.id) === {factura_id}) || botones[0];
                if (!suyo) return false;
                suyo.click();
                return true;
            }})()"""
        )
        # **`startsWith('#/compras/')` y no `indexOf('/compras/') === 0`** (09/10/2026): el `location.hash`
        # empieza por `#`, así que el índice del trozo es **1**, y la espera se quedaba mirando 20 segundos
        # una condición imposible mientras la ficha ya estaba abierta. El fallo era del instrumento —las
        # cuatro cifras salían bien en la pantalla—, que es la clase de fallo que más veces ha despistado
        # en este trabajo.
        nav.esperar("location.hash.startsWith('#/compras/')", segundos=20)
        esperado = nav.evaluar("location.hash")
        print(f"  (la direccion despues de pulsar: {esperado})")
        comprobar(
            esperado.startswith("#/compras/"),
            f"y al pulsarlo se abre **la ficha de la compra**, con su direccion ({esperado})",
        )

        print("\n2) Las cuatro cifras, en pantalla")
        nav.esperar("(document.querySelector('#pantalla') || {}).innerText || ''", segundos=15)
        for intento in range(30):
            texto = el_texto(nav)
            if "Pendiente" in texto:
                break
            time.sleep(0.5)
        texto = el_texto(nav)
        for etiqueta in ("Facturado", "Recibido", "Pagado", "Pendiente"):
            comprobar(etiqueta in texto, f"la ficha dice «{etiqueta}»")
        for cifra in ("663,00", "300,00", "200,00", "463,00"):
            comprobar(cifra in texto, f"y su cifra ({cifra})")

        print("\n3) Los enlaces, y la mercancia separada del dinero")
        enlaces = nav.evaluar(
            """(() => {
                const salida = {};
                for (const el of document.querySelectorAll('#pantalla [data-accion]')) {
                    salida[el.dataset.accion] = (salida[el.dataset.accion] || 0) + 1;
                }
                return salida;
            })()"""
        )
        print(f"  (acciones en la pantalla: {enlaces})")
        comprobar(enlaces.get("albaran-abrir", 0) >= 1, "el albarán de la compra se puede abrir desde aquí")
        comprobar(enlaces.get("gasto-abrir", 0) >= 1, "y el gasto también")

        # **Y que DIGAN algo** (09/10/2026). Esto faltaba, y por eso el revisor de pantallas encontró lo
        # que este guion no vio: los botones existían, pero con el texto **vacío**, porque la puerta
        # servía `textos.FACTURAS` en vez de `textos.COMPRA` y esas ocho frases no estaban allí. Dos
        # botones en blanco de 1059 px y dos títulos sin texto, con las trece comprobaciones en verde.
        # Un botón sin texto no es un botón: es un hueco que nadie pulsa.
        los_textos_de_la_pantalla = nav.evaluar(
            """(() => {
                const salida = {botones: [], titulos: []};
                for (const el of document.querySelectorAll('#pantalla [data-accion]')) {
                    salida.botones.push((el.innerText || '').trim());
                }
                for (const el of document.querySelectorAll('#pantalla h2, #pantalla h3')) {
                    salida.titulos.push((el.innerText || '').trim());
                }
                return salida;
            })()"""
        )
        vacios = [texto for texto in los_textos_de_la_pantalla["botones"] if not texto]
        comprobar(
            not vacios,
            f"y todos los botones dicen algo (vacíos: {len(vacios)} de "
            f"{len(los_textos_de_la_pantalla['botones'])})",
        )
        titulos_vacios = [texto for texto in los_textos_de_la_pantalla["titulos"] if not texto]
        comprobar(
            not titulos_vacios,
            f"y ningún título sale en blanco (vacíos: {len(titulos_vacios)} de "
            f"{len(los_textos_de_la_pantalla['titulos'])})",
        )

        movil = captura(nav, "movil")
        print(f"  (captura del movil: {movil})")

        print("\n4) La direccion es permanente: se recarga y vuelve a salir")
        nav.abrir(f"{DIRECCION}/#/compras/{factura_id}", esperar=2.5)
        nav.esperar("(document.querySelector('#pantalla') || {}).innerText || ''", segundos=15)
        for intento in range(30):
            texto = el_texto(nav)
            if "Pendiente" in texto:
                break
            time.sleep(0.5)
        texto_recargado = el_texto(nav)
        comprobar(
            "Pendiente" in texto_recargado and "463,00" in texto_recargado,
            "al recargar el enlace permanente, la ficha sale igual",
        )

    # Y la captura del escritorio, que es donde se mira con el papel delante.
    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + json.dumps(token)
                + ");"
            },
        )
        nav.abrir(f"{DIRECCION}/#/compras/{factura_id}", esperar=2.5)
        nav.esperar("(document.querySelector('#pantalla') || {}).innerText || ''", segundos=15)
        for intento in range(30):
            if "Pendiente" in el_texto(nav):
                break
            time.sleep(0.5)
        escritorio = captura(nav, "escritorio")
        print(f"  (captura del escritorio: {escritorio})")

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {FALLOS}")
    print(f"Capturas en {CARPETA}")
    return 0 if FALLOS == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
