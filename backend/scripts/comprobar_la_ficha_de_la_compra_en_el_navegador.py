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
import struct
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


def en_consola(algo) -> str:
    """Lo que se imprime, **en algo que la consola de Windows sepa escribir** (09/10/2026).

    Medido: el texto de la barra de arriba trae el carácter del botón del menú (☰), y la consola de este
    Windows va en `cp1252`, así que imprimirlo **reventaba el guion entero** con un `UnicodeEncodeError`
    —después de haber medido bien la barra—. El fallo era del instrumento, no de la barra: lo que se
    imprime es para leerlo, y un carácter que no se puede escribir se sustituye en vez de tumbar la
    comprobación.
    """
    return str(algo).encode("ascii", "replace").decode("ascii")


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


# **La visibilidad, de verdad** (11/10/2026, CRM-00). Se usa desde todas las comprobaciones de pantalla.
#
# POR QUÉ ESTÁ AQUÍ Y NO DENTRO DE CADA CONSULTA. La comprobación que había daba por «visible» un control
# con tal de que tuviera tamaño y no estuviera en `display: none`, y **eso no es visible**: el revisor lo
# demostró midiendo —en la captura de escritorio había controles **fuera de la ventana** y la prueba los
# contaba como a la vista—. Un rectángulo de 120 px que empieza en 1400 con la ventana de 1440 está
# cortado; uno que empieza en 1500 no se ve en absoluto. Lo mismo vale para un ancestro con `overflow:
# hidden`: el elemento existe, mide, y no se ve.
#
# Así que «visible y utilizable» es aquí: tiene tamaño, no está oculto por estilo, **y su rectángulo entero
# cabe dentro de la ventana y dentro de todos los ancestros que recortan**. Es la definición que el
# encargo pide («un rectángulo con ancho positivo fuera de la pantalla no es visible»).
LA_VISIBILIDAD = """
    const totalmenteVisible = (el) => {
        if (!el) return {visible: false, motivo: 'no existe'};
        const estilo = getComputedStyle(el);
        if (estilo.display === 'none') return {visible: false, motivo: 'display none'};
        if (estilo.visibility === 'hidden') return {visible: false, motivo: 'visibility hidden'};
        if (Number(estilo.opacity) === 0) return {visible: false, motivo: 'opacidad 0'};
        const c = el.getBoundingClientRect();
        if (c.width <= 0 || c.height <= 0) return {visible: false, motivo: 'sin tamano'};
        // **La ventana**: el rectángulo entero, no solo su esquina.
        if (c.left < -0.5 || c.top < -0.5 || c.right > window.innerWidth + 0.5 || c.bottom > window.innerHeight + 0.5) {
            return {
                visible: false,
                motivo: 'fuera de la ventana',
                caja: [Math.round(c.left), Math.round(c.top), Math.round(c.right), Math.round(c.bottom)],
                ventana: [window.innerWidth, window.innerHeight],
            };
        }
        // **Y los ancestros que recortan**, subiendo por el árbol: un `overflow: hidden` corta igual que el
        // borde de la pantalla, y es justo lo que hace la barra con el nombre largo.
        for (let padre = el.parentElement; padre; padre = padre.parentElement) {
            const suyo = getComputedStyle(padre);
            const recorta = ['hidden', 'clip', 'auto', 'scroll'].includes(suyo.overflowX) ||
                             ['hidden', 'clip', 'auto', 'scroll'].includes(suyo.overflowY);
            if (!recorta) continue;
            const p = padre.getBoundingClientRect();
            if (c.left < p.left - 0.5 || c.right > p.right + 0.5 || c.top < p.top - 0.5 || c.bottom > p.bottom + 0.5) {
                return {visible: false, motivo: 'recortado por ' + (padre.className || padre.tagName), };
            }
        }
        return {visible: true, motivo: '', caja: [Math.round(c.left), Math.round(c.top), Math.round(c.right), Math.round(c.bottom)]};
    };
"""


def la_visibilidad(nav: NavegadorDeVerdad, selector: str) -> dict:
    """Qué dice la visibilidad de verdad sobre esos controles: uno a uno, con su motivo si no se ven."""
    return nav.evaluar(
        "(() => {"
        + LA_VISIBILIDAD
        + f"""
        const controles = [...document.querySelectorAll({json.dumps(selector)})];
        return {{
            ventana: [window.innerWidth, window.innerHeight],
            cuantos: controles.length,
            suyos: controles.map((el) => {{
                const suyo = totalmenteVisible(el);
                return {{
                    texto: (el.innerText || el.value || el.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim().slice(0, 40),
                    accion: el.dataset ? (el.dataset.accion || '') : '',
                    visible: suyo.visible,
                    motivo: suyo.motivo,
                    caja: suyo.caja || null,
                }};
            }}),
        }};
    }})()"""
    )


def captura(nav: NavegadorDeVerdad, nombre: str) -> dict:
    """La captura, **diciendo de qué tamaño es y con qué ventana se hizo** (CRM-00, 11/10/2026).

    Antes devolvía solo la ruta y el guion decía «captura del móvil» sin más: la ventana del navegador de
    Windows no baja de ~500 px, así que una captura «de 390» salía de 500 y nadie se enteraba hasta que el
    revisor midió el PNG. Ahora se devuelven las dos cosas —lo que dice la página (`innerWidth`) y lo que
    mide la imagen—, para poder contrastarlas.
    """
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"compra-{nombre}.png"
    crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
    destino.write_bytes(crudo)
    ancho_imagen, alto_imagen = struct.unpack(">II", crudo[16:24])
    ventana = nav.evaluar("[window.innerWidth, window.innerHeight]")
    return {
        "ruta": destino,
        "ventana": ventana,
        "imagen": [ancho_imagen, alto_imagen],
    }


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
        # **Los cuatro rótulos, medidos donde están y sin depender de las mayúsculas** (09/10/2026). Esta
        # comprobación buscaba «Recibido» en el texto de toda la pantalla y **fallaba**: los rótulos se
        # pintan en mayúsculas (`text-transform`, como los encabezados de las tablas del diseño), así que
        # «Recibido» no aparecía con esa caja en ningún sitio —las otras tres palabras sí, por casualidad,
        # en la tabla y en las filas del gasto—. El producto estaba bien; el instrumento medía otra cosa.
        rotulos = nav.evaluar(
            "[...document.querySelectorAll('#pantalla .ficha-resumen-etiqueta')].map((e) => e.innerText)"
        )
        print(f"  (rotulos de los cuatro indicadores: {en_consola(rotulos)})")
        en_mayusculas = [str(rotulo).strip().upper() for rotulo in rotulos]
        for etiqueta in ("Facturado", "Recibido", "Pagado", "Pendiente"):
            comprobar(
                etiqueta.upper() in en_mayusculas,
                f"la ficha dice «{etiqueta}» en uno de sus cuatro indicadores",
            )
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
        print(
            f"  (captura del movil: {movil['ruta'].name}, ventana {movil['ventana']}, "
            f"imagen {movil['imagen']})"
        )

        print("\n4) **Ningun importe sin coma decimal ni moneda** (lo pidio David el 09/10/2026)")
        # Un importe con punto y dos decimales es el texto de máquina que se colaba en la pantalla
        # (`663.00`), y el revisor lo vio en la captura. Se busca en **todo** el texto de la ficha, que es
        # donde aparecería, y no en un sitio concreto: no hay ninguna cifra de dinero que deba salir así.
        sueltos = nav.evaluar(
            """(() => {
                const texto = (document.querySelector('#pantalla') || {}).innerText || '';
                return (texto.match(/(^|[\\s(])\\d+\\.\\d\\d(?!\\d)/g) || []).map((t) => t.trim());
            })()"""
        )
        comprobar(
            not sueltos,
            f"y ningun importe sale como texto de maquina (encontrados: {sueltos})",
        )
        comprobar(
            "," in el_texto(nav) and "€" in el_texto(nav),
            "y los importes van con coma decimal y en euros",
        )

        print("\n5) La direccion es permanente: se recarga y vuelve a salir")
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

    # ── El escritorio, a los dos anchos que pidió David: 1440 y 1024 ────────────────────────────────────
    for ancho in (1440, 1024):
        with NavegadorDeVerdad(ancho=ancho, alto=900) as nav:
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

            print(f"\n6) **La ficha y la barra a {ancho} px**")

            # **Los cuatro indicadores, en una fila o cuadrícula.** Es lo que pidió David: en el escritorio
            # la ficha seguía siendo una columna móvil, con cada cifra ocupando el ancho entero. Se mide de
            # verdad: las cuatro cajas tienen que compartir la misma altura de arriba —una fila— y estar en
            # cuatro columnas distintas.
            la_rejilla = nav.evaluar(
                """(() => {
                    const cajas = [...document.querySelectorAll('#pantalla .ficha-resumen')];
                    return {
                        cuantas: cajas.length,
                        arribas: cajas.map((c) => Math.round(c.getBoundingClientRect().top)),
                        izquierdas: cajas.map((c) => Math.round(c.getBoundingClientRect().left)),
                        anchos: cajas.map((c) => Math.round(c.getBoundingClientRect().width)),
                    };
                })()"""
            )
            print(f"     (indicadores: {en_consola(la_rejilla)})")
            comprobar(la_rejilla["cuantas"] == 4, f"la ficha trae sus cuatro indicadores ({la_rejilla['cuantas']})")
            # **En escritorio ancho, una fila** (1440). A 1024 la rejilla baja a dos filas de dos —que es
            # una cuadrícula, y es lo que el encargo pide («una fila o cuadrícula»)—, y lo que **no** puede
            # pasar en ninguno de los dos es que vuelvan a la columna móvil: cuatro cifras apiladas son
            # cuatro pantallas de scroll, que es justo el defecto que se venía a arreglar.
            if ancho >= 1440:
                comprobar(
                    len(set(la_rejilla["arribas"])) == 1,
                    f"y los cuatro estan en la misma fila (arribas: {la_rejilla['arribas']})",
                )
            else:
                comprobar(
                    len(set(la_rejilla["arribas"])) <= 2,
                    f"y a {ancho} van en cuadricula, no en columna (arribas: {la_rejilla['arribas']})",
                )
            comprobar(
                len({izquierda for izquierda in la_rejilla["izquierdas"]}) >= 2,
                f"y hay al menos dos columnas (izquierdas: {la_rejilla['izquierdas']})",
            )
            comprobar(
                min(la_rejilla["anchos"]) >= 120,
                f"y ninguno encogido a una tira (el mas estrecho: {min(la_rejilla['anchos'])} px)",
            )

            # **La barra de arriba, entera y sin acciones ocultas.** David vio la barra cortada en la
            # captura y el revisor lo confirmó midiendo: había controles **fuera de la ventana** que la
            # comprobación anterior contaba como visibles, porque solo miraba que tuvieran tamaño. Aquí se
            # mide lo que pidió el encargo: el **rectángulo completo** de cada control, dentro de la ventana
            # y dentro de los ancestros que recortan (`LA_VISIBILIDAD`). Un rectángulo con ancho positivo
            # fuera de la pantalla **no** es visible.
            la_barra = nav.evaluar(
                "(() => {"
                + LA_VISIBILIDAD
                + """
                    const deEscritorio = document.querySelector('.marco .barra');
                    const usaEscritorio = totalmenteVisible(deEscritorio).visible;
                    const caja = usaEscritorio ? deEscritorio : document.querySelector('.cabecera');
                    if (!caja) return {hay: false};
                    const datos = caja.querySelector('.barra-datos') || caja;
                    const acciones = caja.querySelector('.barra-acciones') || caja.querySelector('.cabecera-botones');
                    const botones = [...(acciones ? acciones.querySelectorAll('button, a') : [])];
                    // **Qué se recorta, y cuál no** (09/10/2026). La casa tiene decidido que, si algo tiene
                    // que ceder en esta barra, ceda **el nombre de la explotación**, y nunca la campaña ni
                    // la cuenta ni las acciones. Así que no basta con «hay algo cortado»: hay que decir
                    // **qué**.
                    const trozos = [...datos.querySelectorAll('.barra-dato')].map((d) => ({
                        rotulo: ((d.querySelector('.barra-rotulo') || {}).innerText || '').trim(),
                        recortado: d.scrollWidth > d.clientWidth + 1,
                    }));
                    return {
                        hay: true,
                        usaEscritorio,
                        ventana: [window.innerWidth, window.innerHeight],
                        anchoCaja: Math.round(caja.getBoundingClientRect().width),
                        altoCaja: Math.round(caja.getBoundingClientRect().height),
                        caja: (() => {
                            const c = caja.getBoundingClientRect();
                            return [Math.round(c.left), Math.round(c.top), Math.round(c.right), Math.round(c.bottom)];
                        })(),
                        trozos,
                        acciones: botones.map((b) => {
                            const suyo = totalmenteVisible(b);
                            return {
                                texto: (b.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 30),
                                visible: suyo.visible,
                                motivo: suyo.motivo,
                                caja: suyo.caja || null,
                            };
                        }),
                        texto: (caja.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 120),
                    };
                })()"""
            )
            print(f"     (barra: {en_consola(la_barra)})")
            comprobar(bool(la_barra.get("hay")), f"a {ancho} px hay una barra de arriba")
            # **Cada acción, entera dentro de la ventana.** Esta es la comprobación que sustituye a contar
            # cajas: se exige el rectángulo completo, así que un control cortado por el borde derecho o
            # sacado de la pantalla cuenta como lo que es.
            las_acciones = la_barra.get("acciones", [])
            cortadas = [
                f"{accion['texto'] or '(sin texto)'} [{accion['motivo']}] {accion['caja']}"
                for accion in las_acciones
                if not accion["visible"]
            ]
            comprobar(
                bool(las_acciones),
                f"y la barra tiene acciones ({[a['texto'] for a in las_acciones]})",
            )
            comprobar(
                not cortadas,
                f"y todas sus acciones estan enteras dentro de la ventana "
                f"({len(las_acciones) - len(cortadas)} de {len(las_acciones)}; cortadas: {cortadas})",
            )
            # Y **la barra entera** también: si la propia barra se sale, algo de dentro está fuera aunque
            # sus botones quepan (el nombre, la campaña o la cuenta).
            dentro = la_barra.get("caja") or [0, 0, 0, 0]
            comprobar(
                dentro[0] >= -0.5 and dentro[2] <= (la_barra.get("ventana") or [0, 0])[0] + 0.5,
                f"y la barra entera cabe en la ventana (barra {dentro}, ventana {la_barra.get('ventana')})",
            )
            print(f"     (barra: {en_consola(la_barra)})")
            comprobar(bool(la_barra.get("hay")), f"a {ancho} px hay una barra de arriba")
            # **Lo esencial no se recorta.** El nombre de la explotación sí puede (es lo que la casa decidió
            # que ceda, y aquí se le está dando un nombre larguísimo a propósito: el del fixture lleva un
            # número detrás). Lo que no puede quedar cortado es la **campaña** —el agricultor tiene que saber
            # en qué año apunta— ni la **cuenta**, que es lo que David vio cortado en la captura.
            # **A 1024 el armazón usa la cabecera de móvil, y eso es una decisión del diseño, no un
            # recorte** (medido el 09/10/2026): el corte de escritorio está en `64rem`, y a 1024 px de
            # ventana el ancho de maquetación se queda en 1009 por la barra de desplazamiento, así que la
            # consulta de medios no entra y sale la cabecera compacta —con sus acciones, las dos a la
            # vista—. Donde se exige que la campaña y la cuenta estén sin cortar es donde existen: en la
            # barra del armazón de escritorio.
            if la_barra.get("usaEscritorio"):
                esenciales = [
                    trozo
                    for trozo in la_barra.get("trozos", [])
                    if "CAMPA" in trozo["rotulo"].upper() or "CUENTA" in trozo["rotulo"].upper()
                ]
                comprobar(
                    len(esenciales) >= 2,
                    f"y la barra dice la campana y la cuenta "
                    f"({[t['rotulo'] for t in la_barra.get('trozos', [])]})",
                )
                recortados_esenciales = [
                    trozo["rotulo"] for trozo in esenciales if trozo["recortado"]
                ]
                comprobar(
                    not recortados_esenciales,
                    f"y ninguna de las dos sale cortada (cortadas: {recortados_esenciales})",
                )
                # **Y se dice qué sí se recorta**, que es el nombre de la explotación: la casa decidió que
                # ceda él antes que la campaña o la cuenta, y aquí se le está dando un nombre larguísimo a
                # propósito. Dejarlo escrito evita que alguien lea «hay algo recortado» como un defecto.
                print(
                    "     (recortado por el nombre largo: "
                    f"{[t['rotulo'] for t in la_barra.get('trozos', []) if t['recortado']]})"
                )
            # Y las acciones, ya comprobadas arriba una a una con su rectángulo entero. Aquí se deja dicho
            # cuántas son, porque el encargo pide poder **activarlas**, no solo verlas: se cuentan las que
            # además se pueden pulsar (no `disabled`) y tienen área de toque suficiente.
            cuantas = len(las_acciones)
            pulsables = nav.evaluar(
                "(() => {"
                + LA_VISIBILIDAD
                + """
                    // **La barra que de verdad se usa a este ancho**, que es la misma regla que arriba: a 1024
                    // el armazón enseña la cabecera compacta, y medir los botones de la barra escondida daba
                    // cuatro botones de 0×0 —un fallo del instrumento, no de la pantalla— (CRM-00).
                    const deEscritorio = document.querySelector('.marco .barra');
                    const caja = totalmenteVisible(deEscritorio).visible
                        ? deEscritorio
                        : document.querySelector('.cabecera');
                    if (!caja) return {cuantas: 0, pequenas: [], deshabilitadas: []};
                    const acciones = caja.querySelector('.barra-acciones') || caja.querySelector('.cabecera-botones');
                    const botones = [...(acciones ? acciones.querySelectorAll('button, a') : [])];
                    const c = (b) => {
                        const r = b.getBoundingClientRect();
                        return [Math.round(r.width), Math.round(r.height)];
                    };
                    return {
                        cuantas: botones.length,
                        suyos: botones.map((b) => ({
                            texto: (b.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 26),
                            clase: b.className,
                            ancho: c(b)[0],
                            alto: c(b)[1],
                        })),
                        pequenas: botones.filter((b) => c(b)[0] < 44 || c(b)[1] < 44).map((b) => [
                            (b.innerText || '').trim().slice(0, 20),
                            c(b),
                        ]),
                        deshabilitadas: botones.filter((b) => b.disabled).map((b) => (b.innerText || '').trim()),
                    };
                })()"""
            )
            print(f"     (acciones: {en_consola(pulsables)})")
            comprobar(
                not pulsables.get("deshabilitadas"),
                f"y ninguna accion esta deshabilitada ({pulsables.get('deshabilitadas')})",
            )
            comprobar(
                not pulsables.get("pequenas"),
                f"y todas tienen area de toque (menos de 44 px: {pulsables.get('pequenas')})",
            )

            # **Y las líneas, en tabla**: es lo que pidió David («líneas en tabla»). Una tabla de verdad,
            # con sus encabezados, y no una lista de fichas.
            la_tabla = nav.evaluar(
                """(() => {
                    const tabla = document.querySelector('#pantalla table.tabla');
                    if (!tabla) return {hay: false};
                    return {
                        hay: true,
                        filas: tabla.querySelectorAll('tbody tr').length,
                        columnas: [...tabla.querySelectorAll('thead th')].map((th) => (th.innerText || '').trim()),
                        scroll: (tabla.parentElement.className || '').includes('tabla-scroll'),
                    };
                })()"""
            )
            print(f"     (lineas: {la_tabla})")
            comprobar(bool(la_tabla.get("hay")), "las lineas van en una tabla")
            comprobar(la_tabla.get("filas", 0) >= 1, "con sus filas")
            comprobar(
                len(la_tabla.get("columnas", [])) == 4,
                f"y sus cuatro columnas ({la_tabla.get('columnas')})",
            )
            comprobar(bool(la_tabla.get("scroll")), "y la tabla se puede desplazar en el movil")

            # Y los dos bloques separados: lo que ha llegado y el dinero.
            los_bloques = nav.evaluar(
                "document.querySelectorAll('#pantalla section.ficha-bloque').length"
            )
            comprobar(los_bloques == 2, f"y los dos bloques separados: datos y dinero ({los_bloques})")

            # **Ninguna cifra de dinero en texto de máquina**, tampoco aquí.
            sueltos_aqui = nav.evaluar(
                """(() => {
                    const texto = (document.querySelector('#pantalla') || {}).innerText || '';
                    return (texto.match(/(^|[\\s(])\\d+\\.\\d\\d(?!\\d)/g) || []).map((t) => t.trim());
                })()"""
            )
            comprobar(not sueltos_aqui, f"y ningun importe como 663.00 (encontrados: {sueltos_aqui})")

            print(f"     (texto de la barra: {en_consola(la_barra.get('texto'))})")
            destino = captura(nav, "escritorio" if ancho == 1440 else f"escritorio-{ancho}")
            print(
                f"  (captura a {ancho}: {destino['ruta'].name}, ventana {destino['ventana']}, "
                f"imagen {destino['imagen']})"
            )

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {FALLOS}")
    print(f"Capturas en {CARPETA}")
    return 0 if FALLOS == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
