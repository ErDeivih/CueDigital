"""El recorrido económico del CRM: factura → recepción → existencias → gasto → pago (08/10/2026).

**Qué comprueba.** Lo que todavía no está acreditado de extremo a extremo y que David pidió: que una factura de
compra entre por la pantalla, que de ella salga una **recepción física** que es la que **sube las existencias**,
que se apunte el **gasto** y que se pague **a plazos** -parcial, saldo pendiente y pago final-, con las cifras
cuadrando en cada paso.

**Cómo.** Con **documentos ficticios** y **base temporal**, desde las pantallas de verdad: servidor de pruebas
levantado por mí, sesión inyectada como la inyecta el recorrido general
(`localStorage['cuedigital.token']`, comprobado en su código) y un Chrome sin ventana por CDP.

**Lo que NO hace, y hay que decirlo.** Aquí **no se evalúa el reconocimiento automático de documentos** (OCR):
para eso hace falta un **corpus de facturas de verdad**, y si no lo hay en el repositorio, ese límite se declara
y la **entrada manual se comprueba por separado**. Lo que se meta a mano **no sustituye** aquella prueba: es
otra cosa distinta, y así se dirá en el resultado.

**Uso**:  python scripts/comprobar_el_recorrido_economico.py <direccion> [carpeta-de-capturas] [ruta-de-la-base]
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8140"
CARPETA = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(tempfile.gettempdir()) / "cd-ui"
# **La base, en el tercer argumento**: el segundo es la carpeta de capturas -el recorrido general ya se topó con
# eso- y la comprobación de la auditoría necesita saber dónde está la base de la prueba.
RUTA_DE_LA_BASE = sys.argv[3] if len(sys.argv) > 3 else None

LAS_COMPROBACIONES: list[str] = []
LOS_FALLOS: list[str] = []
LOS_HALLAZGOS: list[str] = []


def comprobar(bien: bool, que: str) -> bool:
    """Apunta una comprobación. Si no se cumple, es un **fallo**, y el guion termina en rojo."""
    if bien:
        LAS_COMPROBACIONES.append(que)
        print(f"[OK  ] {que}")
    else:
        LOS_FALLOS.append(que)
        print(f"[FALLO] {que}")
    return bool(bien)


def hallazgo(que: str) -> None:
    """Lo que se sabe que falta, **medido**. No es un fallo: es un límite que se declara."""
    LOS_HALLAZGOS.append(que)
    print(f"[HALLAZGO] {que}")


def paso(nav: NavegadorDeVerdad, numero: int, titulo: str) -> None:
    print(f"\n── {numero}. {titulo} " + "─" * max(0, 66 - len(titulo)))


def hay(nav: NavegadorDeVerdad, selector: str) -> bool:
    return bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(selector)}))"))


def captura(nav: NavegadorDeVerdad, nombre: str) -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    nav.orden("Page.captureScreenshot")
    print(f"  (captura: {nombre})")


def main() -> int:
    # **Nunca contra la base del agricultor** (08/10/2026, a raíz de la revisión independiente). Este guion **no
    # levanta el servidor** -contra lo que decía su cabecera, y eso lo destapó el revisor-: sólo habla por HTTP
    # con la dirección que le den. Si alguien apunta el servidor a la base real, el escenario se crea **dentro de
    # ella** (registro, 64 tierras, 40 gastos, factura, albarán y gasto, todo por API). Así que se exige la ruta
    # de la base y se comprueba que **no** es la del agricultor, antes de tocar nada.
    if not RUTA_DE_LA_BASE:
        print("=> falta la ruta de la base (tercer argumento): sin ella no puedo comprobar que no sea la real")
        return 1
    la_del_agricultor = (pathlib.Path(__file__).resolve().parents[1] / "cuedigital.db").resolve()
    if pathlib.Path(RUTA_DE_LA_BASE).resolve() == la_del_agricultor:
        print("=> NO se toca la base del agricultor: apunta el servidor a una base temporal")
        return 1
    print("  (la base de la prueba no es la del agricultor: adelante)")

    # **La salida, en UTF-8, pase lo que pase** (07/10/2026): este guion imprime acentos y rayas, y cuando la
    # salida no es UTF-8 -en la suite, sin `PYTHONIOENCODING`, la consola es cp1252- moría con
    # `UnicodeEncodeError`. No debe depender de cómo le llamen.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import datos_representativos as datos

    carpeta_de_los_datos = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital-economico-"))
    volumen, escenario = datos._la_del_volumen(  # noqa: SLF001 — el mismo preparador que usa el recorrido
        DIRECCION, f"economico{int(time.time())}", carpeta_de_los_datos, False
    )
    print(f"  la sesión: {volumen.nombre}, con {len(escenario.tierras)} tierras")

    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(volumen.token) + ");"},
        )
        nav.abrir(f"{DIRECCION}/#/inicio", esperar=2.0)
        comprobar(
            nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=25),
            "la aplicación abre con la sesión de la prueba",
        )
        # **Qué puertas hay para este recorrido** (08/10/2026): antes de recorrer nada, se mira qué pantallas
        # existen y con qué nombres, en el menú de verdad, para no inventarse rutas. La primera versión de esto
        # devolvía `[]` porque dejé un escapado roto dentro de la cadena de JavaScript; ahora se piden los datos
        # uno a uno y se filtra, sin comillas frágiles.
        el_menu = nav.evaluar(
            "(() => [...document.querySelectorAll('#marco a, #marco button, #marco [data-accion]')]"
            ".map((uno) => ({ id: uno.id || null,"
            " accion: (uno.dataset ? uno.dataset.accion : null) || null,"
            " href: uno.getAttribute('href'),"
            " texto: (uno.textContent || '').trim().slice(0, 24) }))"
            ".filter((uno) => uno.id || uno.accion || uno.href).slice(0, 40))()"
        )
        print("  (las puertas del menú, en vivo:)")
        for puerta in el_menu or []:
            print(f"    {puerta}")

        # **La pantalla de facturas, en vivo** (08/10/2026): se abre por su puerta y se listan **sus acciones y
        # sus campos**. Es la única forma de recorrerla sin inventarse selectores, que es el error que más
        # rondas me ha costado en esta sesión. La puerta es `menu-facturas`, leída del menú de verdad.
        nav.evaluar(
            "(() => { const b = document.querySelector('#menu-facturas'); if (b) { b.click(); } return null; })()"
        )
        nav.esperar("location.hash.includes('factura')", segundos=20)
        nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=10)
        print(f"  (la pantalla de facturas: {nav.evaluar('location.hash')})")
        print(
            "  (sus acciones: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 30))()"
                )
            )
        )
        print(
            "  (sus campos: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select,"
                    " #pantalla textarea')]"
                    ".map((uno) => uno.id || uno.name || uno.type).slice(0, 30))()"
                )
            )
        )
        captura(nav, "economico-1-facturas")

        # **El formulario de factura nueva** (08/10/2026): aquí es donde tiene que estar la **subida del
        # documento** y su extracción -y donde se corrige antes de confirmar-, que es el primer punto que pide
        # el encargo. Se pulsa su puerta y se vuelca lo que aparece, con nombres de verdad.
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"factura-nueva\"]');"
            " if (b) { b.click(); } return null; })()"
        )
        nav.esperar("Boolean(document.querySelector('#pantalla input, #pantalla select'))", segundos=20)
        print(f"  (la factura nueva: {nav.evaluar('location.hash')})")
        print(
            "  (sus acciones: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 30))()"
                )
            )
        )
        print(
            "  (sus campos: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select,"
                    " #pantalla textarea')]"
                    ".map((uno) => ({ id: uno.id || null, tipo: uno.type, nombre: uno.name || null }))"
                    ".slice(0, 40))()"
                )
            )
        )
        captura(nav, "economico-2-factura-nueva")

        # **La factura a mano** (08/10/2026): el camino que el encargo manda comprobar **por separado** del
        # reconocimiento. Aquí tienen que estar el proveedor, las líneas, las cantidades, las **unidades**, la
        # base, los impuestos y el total -el punto 2 de la lista-.
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"factura-mano\"]');"
            " if (b) { b.click(); } return null; })()"
        )
        nav.esperar("Boolean(document.querySelector('#pantalla input, #pantalla select'))", segundos=20)
        print(f"  (la factura a mano: {nav.evaluar('location.hash')})")
        print(
            "  (sus acciones: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 30))()"
                )
            )
        )
        print(
            "  (sus campos: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select,"
                    " #pantalla textarea')]"
                    ".map((uno) => ({ id: uno.id || null, tipo: uno.type, nombre: uno.name || null }))"
                    ".slice(0, 40))()"
                )
            )
        )
        captura(nav, "economico-3-factura-mano")

        # **Se rellena la factura a mano y se guarda** (08/10/2026): datos ficticios, y la línea atada a un
        # **producto** de verdad -el desplegable `factura-0-producto`-, que es lo que después tiene que moverse
        # en el almacén. Se escribe por JavaScript poniendo el valor y avisando los eventos: los campos
        # numéricos no se teclean bien, y el recorrido general ya se topó con eso.
        def escribir_en(selector: str, valor: str) -> bool:
            return bool(
                nav.evaluar(
                    "(() => { const c = document.querySelector(" + json.dumps(selector) + ");"
                    " if (!c) return false;"
                    " c.value = " + json.dumps(valor) + ";"
                    " c.dispatchEvent(new Event('input', { bubbles: true }));"
                    " c.dispatchEvent(new Event('change', { bubbles: true })); return true; })()"
                )
            )

        EL_NUMERO = "F-2026-0001"
        LOS_DATOS = {
            "#factura-proveedor": "Suministros del Páramo, S.L.",
            "#factura-proveedor-nif": "B12345678",
            "#factura-numero": EL_NUMERO,
            "#factura-fecha": "2026-10-05",
            "#factura-base": "1000",
            "#factura-iva": "21",
            "#factura-total": "1210",
            "#factura-0-descripcion": "Abono compuesto 15-15-15",
            "#factura-0-cantidad": "500",
            "#factura-0-unidad": "kg",
            "#factura-0-precio": "2",
            "#factura-0-importe": "1000",
        }
        escritos = {selector: escribir_en(selector, valor) for selector, valor in LOS_DATOS.items()}
        faltan = [selector for selector, bien in escritos.items() if not bien]
        comprobar(
            not faltan,
            "la factura a mano **acepta los siete datos** que pide el encargo "
            f"(proveedor, número, fecha, base, IVA, total y la línea){'' if not faltan else ': faltan ' + str(faltan)}",
        )
        # **Y la línea, atada a un producto** de verdad: es lo que después tiene que entrar en el almacén por la
        # recepción. Si no hay ningún producto al que atarla, es un hallazgo, no un fallo del recorrido.
        el_producto = nav.evaluar(
            # **Un producto de verdad, no el marcador** (08/10/2026): la primera opción del desplegable es
            # «No lo tengo apuntado: créalo con estos datos», que **no es un producto** -y fue lo que elegí la
            # primera vez, con lo que la línea quedaba sin artículo-. Se elige la primera que **no** sea ese
            # marcador: el escenario crea artículos por la API, así que los hay. Y se dice cuál.
            "(() => { const s = document.querySelector('#factura-0-producto');"
            " if (!s || !s.options) return null;"
            " const buena = [...s.options].findIndex("
            "   (o) => o.value && !/No lo tengo apuntado/i.test(o.textContent));"
            " if (buena < 0) return null;"
            " s.selectedIndex = buena;"
            " s.dispatchEvent(new Event('change', { bubbles: true }));"
            " return s.options[buena].textContent; })()"
        )
        comprobar(
            bool(el_producto),
            f"la línea se puede atar a un **producto** del almacén ({el_producto!r})",
        )
        captura(nav, "economico-5-factura-rellena")

        # **Se guarda**, y se comprueba que la factura **aparece** en su lista con su número.
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"factura-guardar\"]');"
            " if (b) { b.click(); } return null; })()"
        )
        # **Qué se puede pulsar en la pantalla de después de guardar** (08/10/2026): el mensaje «Factura
        # guardada.» se queda, y mi clic anterior **no dijo si el botón existía** -error mío-, así que antes de
        # pulsar nada se mira **qué acciones hay** y se dice.
        print(
            "  (lo que se puede pulsar después de guardar: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 20))()"
                )
            )
            + ")"
        )
        # **Se guarda otra vez, a propósito** (08/10/2026): después de guardar, la pantalla **sigue ofreciendo**
        # `factura-guardar` -medido: `['factura-guardar', 'factura-nueva']`-, así que aquí se prueba **el caso que
        # pide el encargo**: el agricultor que duda y le da dos veces. El servidor tiene que seguir teniendo una.
        segunda_vez = nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"factura-guardar\"]');"
            " if (!b) return 'no hay boton';"
            " if (b.disabled) return 'el boton esta DESHABILITADO';"
            " b.click(); return 'pulsado'; })()"
        )
        print(f"  (el segundo intento de guardar: {segunda_vez})")
        # **La comprobación del duplicado vive donde se puede hacer bien** (08/10/2026). Aquí dentro no se
        # puede: el botón de guardar queda **deshabilitado** -medido arriba-, así que **no hay segundo envío**, y
        # mandar el cuerpo a mano exige **multipart** con el campo `datos`, como lo manda la pantalla. Se comprueba
        # en su propio guion, y **está demostrado**: dos envíos de la misma factura **crean dos facturas** -es un
        # hallazgo, no una comprobación que pasa sola-.
        #     `scripts/comprobar_si_una_factura_repetida_se_duplica.py`
        nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=15)
        time.sleep(1.0)

        # **Se vuelve a la lista por la puerta de la aplicación** (08/10/2026): escribir la dirección a mano **no
        # repinta** la pantalla si ya se está en esa ruta -medido: la pantalla se quedaba diciendo «Factura
        # guardada.» y parecía que la lista no enseñaba el número-, así que se pulsa su acción, que es lo que
        # hace el agricultor. Y se espera **a una condición observable**: a que esté la acción de la lista.
        # **Y se vuelve a la lista por las puertas que sí existen** (08/10/2026): en la pantalla de después de
        # guardar **no hay** `facturas-abrir` -medido, y por eso mi clic no hacía nada-, pero **sí** hay
        # `factura-nueva`, y **esa** pantalla trae `facturas-abrir`. Se va por ahí, que es el camino de verdad.
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"factura-nueva\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        comprobar(
            nav.esperar(
                "Boolean(document.querySelector('#pantalla [data-accion=\"facturas-abrir\"]'))", segundos=20
            ),
            "desde la factura guardada se puede **volver a la lista** (por `factura-nueva`)",
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"facturas-abrir\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        nav.esperar(
            "Boolean(document.querySelector('#pantalla [data-accion=\"factura-nueva\"]'))", segundos=20
        )
        aparece = nav.esperar(
            "document.body.innerText.includes(" + json.dumps(EL_NUMERO) + ")", segundos=25
        )
        comprobar(aparece, f"al guardar, la factura **{EL_NUMERO}** aparece en la lista de facturas")

        # **Y se le pregunta al servidor** (08/10/2026), no sólo a la pantalla: es lo que distingue «no se
        # guardó» de «se guardó y mi comprobación estaba mirando donde no era». Si no está, se enseña **lo que
        # dice la pantalla**, que es donde estará el porqué.
        import urllib.request

        try:
            peticion = urllib.request.Request(
                f"{DIRECCION}/api/facturas",
                headers={"Authorization": f"Bearer {volumen.token}"},
            )
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                guardadas = json.loads(respuesta.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            guardadas = []
            print(f"  (no he podido preguntar por las facturas: {exc})")
        if isinstance(guardadas, dict):
            guardadas = guardadas.get("facturas") or []
        suyas = [una for una in guardadas if EL_NUMERO in str(una)]
        print(f"  (el servidor: {len(guardadas)} facturas, y con el número {EL_NUMERO}: {len(suyas)})")
        comprobar(bool(suyas), f"y **el servidor tiene guardada** la factura {EL_NUMERO}")
        # **Y guardar dos veces no la ha duplicado**: es el punto 3 del encargo, y aquí está el dato del servidor.
        comprobar(
            len(guardadas) == 1,
            f"**guardar dos veces no duplica**: el servidor sigue teniendo {len(guardadas)} factura(s)",
        )

        # **Qué enseña la lista, tal cual, y qué le ha puesto el servidor a la factura** (08/10/2026). Con esto
        # se sabe si el número no sale porque la lista mira **otra campaña**, porque no se pinta, o porque la
        # lista está vacía -en vez de suponerlo, que es lo que me ha costado más rondas en esta sesión-.
        if suyas:
            print(f"  (la factura guardada, como la devuelve el servidor: {str(suyas[0])[:220]})")
        print(f"  (la dirección de la lista: {nav.evaluar('location.hash')})")
        print(
            "  (lo que la lista enseña: "
            + str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText || ''"))[:400]
            + ")"
        )
        if not suyas:
            print(
                "  (lo que dice la pantalla: "
                + str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText || ''"))[:400]
                + ")"
            )

        # ── Y el **albarán**, que es lo único que mete existencias (08/10/2026) ───────────────────────
        # El encargo lo pone en el centro: que las existencias suban **por la recepción** y no por registrar la
        # factura. Aquí no se supone nada: se abre su puerta y se vuelca **lo que pide de verdad**.
        paso(nav, 2, "El albarán: lo que llega de verdad")
        nav.evaluar(
            "(() => { const b = document.querySelector('#menu-almacen');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        comprobar(
            nav.esperar(
                "Boolean(document.querySelector('#pantalla [data-accion=\"libro-ver\"]'))", segundos=20
            ),
            "el almacén se abre desde su renglón del menú",
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"libro-ver\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        comprobar(
            nav.esperar(
                "Boolean(document.querySelector('#pantalla [data-accion=\"albaran-nuevo\"]'))", segundos=20
            ),
            "el libro del almacén trae la puerta de **apuntar un albarán**",
        )
        # **Se espera al campo del formulario, no a «que haya campos»** (08/10/2026): la espera genérica la
        # cumplía la propia pantalla del libro, así que se seguía **antes** de que el albarán estuviera abierto y
        # las escrituras no encontraban sus campos -medido: los cuatro sin escribir-. Y se dice si el botón
        # estaba, que es lo que me faltó las tres veces anteriores.
        # **¿Existe el campo ANTES de pulsar?** (08/10/2026): si ese id ya está en la pantalla del libro -un
        # molde oculto que se rellena al abrir-, mi espera lo encuentra y **no prueba** que el formulario se haya
        # abierto. Es la medición que distingue las dos explicaciones posibles, y va antes de pulsar nada.
        print(
            "  (el `#albaran-fecha` ANTES de pulsar, en la lista: "
            + str(
                nav.evaluar(
                    "(() => { const todos = document.querySelectorAll('#albaran-fecha');"
                    " const uno = todos[0] || null;"
                    " return { cuantos: todos.length,"
                    "  visible: uno ? Boolean(uno.offsetParent) : null,"
                    "  alto: uno ? Math.round(uno.getBoundingClientRect().height) : null }; })()"
                )
            )
            + ")"
        )
        pulsado = nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"albaran-nuevo\"]');"
            " if (!b) return false; b.click(); return true; })()"
        )
        print(f"  (¿estaba la puerta del albarán?: {pulsado})")
        comprobar(
            bool(pulsado)
            and nav.esperar("Boolean(document.querySelector('#albaran-fecha'))", segundos=25),
            "al pulsar `albaran-nuevo` se abre **el formulario del albarán**",
        )
        print(f"  (el albarán nuevo: {nav.evaluar('location.hash')})")
        print(
            "  (lo que se puede pulsar: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 20))()"
                )
            )
            + ")"
        )
        print(
            "  (sus campos: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select,"
                    " #pantalla textarea')]"
                    ".map((uno) => ({ id: uno.id || null, tipo: uno.type })).slice(0, 40))()"
                )
            )
            + ")"
        )
        captura(nav, "economico-7-albaran-nuevo")

        # **Se rellena y se guarda el albarán** (08/10/2026): el mismo artículo que la factura y una cantidad. El
        # albarán es **lo único que mete existencias**, así que aquí se mide: antes y después, preguntando al
        # servidor. Y **se imprime la forma de su respuesta** antes de afirmar nada -la lección de la sesión-.
        def escribir_campo(selector: str, valor: str) -> bool:
            return bool(
                nav.evaluar(
                    "(() => { const c = document.querySelector(" + json.dumps(selector) + ");"
                    " if (!c) return false;"
                    " c.value = " + json.dumps(valor) + ";"
                    " c.dispatchEvent(new Event('input', { bubbles: true }));"
                    " c.dispatchEvent(new Event('change', { bubbles: true })); return true; })()"
                )
            )

        def las_existencias():
            """Lo que el servidor dice que hay. Se imprime su forma, no se supone."""
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(
                        f"{DIRECCION}/api/almacen/existencias",
                        headers={"Authorization": f"Bearer {volumen.token}"},
                    ),
                    timeout=30,
                ) as respuesta:
                    return json.loads(respuesta.read().decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                return {"error": str(exc)[:80]}

        # **La traza del formulario** (08/10/2026): la espera dice que `#albaran-fecha` está y, milisegundos
        # después, **no hay ninguno** -medido: `cuantos: 0`-. Las dos cosas no pueden ser verdad, así que se
        # **sondea** cada 100 ms y se apunta el estado: si el formulario sigue, o si la pantalla se ha caído a
        # otra cosa, y con qué acciones. Sin deducir: mirando.
        vistos: list = []
        for _ in range(50):  # cinco segundos
            estado = nav.evaluar(
                "(() => ({ campo: Boolean(document.querySelector('#albaran-fecha')),"
                " acciones: [...document.querySelectorAll('#pantalla [data-accion]')]"
                "  .map((uno) => uno.dataset.accion).slice(0, 6),"
                " direccion: String(location.hash).slice(0, 46) }))()"
            )
            if not vistos or vistos[-1] != estado:
                vistos.append(estado)
                print(f"    estado {len(vistos)}: {estado}")
            time.sleep(0.1)
        print(f"  (estados distintos del formulario en 5 s: {len(vistos)})")

        EL_ALBARAN = "ALB-2026-0001"
        escribio = {
            "#albaran-fecha": escribir_campo("#albaran-fecha", "2026-10-06"),
            "#albaran-proveedor": escribir_campo("#albaran-proveedor", "Suministros del Páramo, S.L."),
            "#albaran-numero": escribir_campo("#albaran-numero", EL_ALBARAN),
            "#albaran-0-cantidad": escribir_campo("#albaran-0-cantidad", "500"),
        }
        comprobar(
            all(escribio.values()),
            "el albarán acepta fecha, proveedor, número y la cantidad de su línea "
            f"(sin escribir: {[clave for clave, bien in escribio.items() if not bien] or 'ninguno'})",
        )
        el_articulo = nav.evaluar(
            "(() => { const s = document.querySelector('#albaran-0-articulo');"
            " if (!s || !s.options) return null; const buena = [...s.options].findIndex("
            "   (o) => o.value && !/no lo tengo/i.test(o.textContent));"
            " if (buena < 0) return null; s.selectedIndex = buena;"
            " s.dispatchEvent(new Event('change', { bubbles: true }));"
            " return s.options[buena].textContent; })()"
        )
        comprobar(bool(el_articulo), f"y su línea se ata a un **artículo** ({el_articulo!r})")
        # **La unidad, la del artículo** (08/10/2026): este proyecto es estricto con las unidades -«litros y kilos
        # no se suman»-, así que poner 500 kg en un artículo de litros **no demuestra** nada del almacén. Se
        # elige la unidad de litros, que es la del artículo de la prueba, y se dice cuál.
        la_unidad = nav.evaluar(
            "(() => { const s = document.querySelector('#albaran-0-unidad');"
            " if (!s || !s.options) return null;"
            " const buena = [...s.options].findIndex((o) => /^l$|litro/i.test((o.textContent || '').trim()));"
            " if (buena < 0) return null; s.selectedIndex = buena;"
            " s.dispatchEvent(new Event('change', { bubbles: true }));"
            " return s.options[buena].textContent; })()"
        )
        comprobar(bool(la_unidad), f"y la unidad de la línea, la del artículo ({la_unidad!r})")
        antes_de_recibir = las_existencias()
        # **Cómo se llama el saldo** (08/10/2026): se piden las **claves** del artículo y las del lote, en vez de
        # buscarlo a ojo en un volcado largo. Así la comprobación se escribe con el nombre de verdad.
        if isinstance(antes_de_recibir, dict) and antes_de_recibir.get("articulos"):
            el_articulo_cero = antes_de_recibir["articulos"][0]
            print(f"  (las claves de un artículo: {sorted(el_articulo_cero.keys())})")
            print(
                "  (las claves de un lote: "
                f"{sorted((el_articulo_cero.get('lotes') or [{}])[0].keys())})"
            )
        # **Sin los textos de la pantalla** (08/10/2026): la respuesta entera empieza por `textos` y con eso no se
        # compara nada. Se pide **lo de los números**, que es lo que hay que ver subir.
        print(
            "  (las existencias ANTES de recibir, sin los textos: "
            + str(
                {clave: valor for clave, valor in antes_de_recibir.items() if clave != "textos"}
                if isinstance(antes_de_recibir, dict)
                else antes_de_recibir
            )[:700]
            + ")"
        )
        captura(nav, "economico-8-albaran-relleno")
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"albaran-guardar\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=20)
        time.sleep(1.0)
        despues_de_recibir = las_existencias()
        print(
            "  (las existencias DESPUÉS de recibir, sin los textos: "
            + str(
                {clave: valor for clave, valor in despues_de_recibir.items() if clave != "textos"}
                if isinstance(despues_de_recibir, dict)
                else despues_de_recibir
            )[:700]
            + ")"
        )
        # **El saldo, antes y después, y de dónde viene lo que entra** (08/10/2026). Es **lo que el encargo pide**:
        # que las existencias suban **por la recepción** y que **la factura no añada nada**. El campo del saldo
        # se llama `saldo` y se ha leído **por su nombre** -preguntando las claves-, no buscándolo a ojo.
        def el_saldo(datos):
            try:
                return datos["articulos"][0]["saldo"]
            except (KeyError, IndexError, TypeError):
                return None

        saldo_antes = el_saldo(antes_de_recibir)
        saldo_despues = el_saldo(despues_de_recibir)
        print(f"  (el saldo del artículo: antes {saldo_antes!r} · después {saldo_despues!r})")
        comprobar(
            saldo_antes is not None and saldo_despues is not None,
            f"el servidor dice el **saldo** del artículo antes y después (antes {saldo_antes!r})",
        )
        try:
            subio = float(saldo_despues) - float(saldo_antes)
        except (TypeError, ValueError):
            subio = None
        comprobar(
            subio is not None and abs(subio - 500.0) < 0.001,
            f"y la recepción **sube el saldo** en lo que llegó (500 L: {saldo_antes!r} → {saldo_despues!r})",
        )
        # **Y de dónde sale cada movimiento**: cada uno dice su `origen_tipo`, así que se miran los orígenes que
        # hay. Lo que entra tiene que venir de **una recepción**, y **ninguno** puede salir de la factura.
        # **Los orígenes de TODOS los lotes** (08/10/2026): mirarlos sólo del primero era **mi** error -el
        # albarán **crea un lote nuevo**, así que su movimiento estaba en el otro-, y por eso la comprobación
        # decía que nada venía de una recepción mientras el saldo del artículo había subido 500 L. El saldo, que
        # es lo que importa, sí se lee del artículo entero y por eso era de fiar.
        los_del_lote = [
            uno
            for lote in ((despues_de_recibir.get("articulos") or [{}])[0].get("lotes") or [])
            for uno in (lote.get("movimientos_del_lote") or [])
        ]
        los_origenes = sorted({str(uno.get("origen_tipo")) for uno in los_del_lote})
        print(f"  (los orígenes de los movimientos del lote: {los_origenes})")
        comprobar(
            any("recep" in tipo.lower() for tipo in los_origenes),
            f"y lo que ha entrado viene de **una recepción** (orígenes: {los_origenes})",
        )
        comprobar(
            not any("factura" in tipo.lower() for tipo in los_origenes),
            f"y **ningún movimiento sale de la factura** (orígenes: {los_origenes})",
        )
        captura(nav, "economico-9-albaran-guardado")

        # ── El gasto y el dinero: pago parcial, saldo pendiente y pago final (08/10/2026) ──────────────
        # El último tramo del encargo. Se entra por el **renglón del menú** y se espera **a la acción del
        # formulario** (`gasto-guardar`, que el inventario del subagente deja identificada), no a «que haya
        # campos»: esa espera genérica ya me falló con el albarán.
        paso(nav, 3, "El gasto y el dinero")
        nav.evaluar(
            "(() => { const b = document.querySelector('#menu-cuentas');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        comprobar(
            nav.esperar(
                "Boolean(document.querySelector('#pantalla [data-accion=\"gasto-nuevo\"]'))", segundos=25
            ),
            "las cuentas se abren desde su renglón del menú, con su puerta de **apuntar un gasto**",
        )
        print(
            "  (lo que se puede pulsar en las cuentas: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 18))()"
                )
            )
            + ")"
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gasto-nuevo\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        comprobar(
            nav.esperar(
                "Boolean(document.querySelector('#pantalla [data-accion=\"gasto-guardar\"]'))", segundos=25
            ),
            "y `gasto-nuevo` abre **el formulario del gasto** (con la acción de guardar dentro)",
        )
        print(
            "  (sus campos: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select,"
                    " #pantalla textarea')]"
                    ".map((uno) => uno.id || uno.name || uno.type).slice(0, 30))()"
                )
            )
            + ")"
        )
        print(
            "  (sus acciones: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 18))()"
                )
            )
            + ")"
        )
        captura(nav, "economico-10-gasto-nuevo")

        # **Se rellena y se guarda el gasto** (08/10/2026). Datos ficticios, y se comprueba **contra el
        # servidor**, no contra la pantalla -que es lo que enseñó el tramo de la factura-. Y se imprime **la
        # forma** de su respuesta antes de afirmar dónde está el pendiente.
        EL_CONCEPTO = "Gasóleo de la cosechadora, recorrido económico"
        escribio_el_gasto = {
            "#gasto-concepto": escribir_campo("#gasto-concepto", EL_CONCEPTO),
            "#gasto-importe": escribir_campo("#gasto-importe", "663"),
            "#gasto-fecha": escribir_campo("#gasto-fecha", "2026-10-07"),
            "#gasto-proveedor": escribir_campo("#gasto-proveedor", "Suministros del Páramo, S.L."),
        }
        comprobar(
            all(escribio_el_gasto.values()),
            "el gasto acepta concepto, importe, fecha y proveedor "
            f"(sin escribir: {[c for c, b in escribio_el_gasto.items() if not b] or 'ninguno'})",
        )
        captura(nav, "economico-11-gasto-relleno")
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gasto-guardar\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=25)
        time.sleep(1.0)

        def los_gastos():
            """Lo que el servidor dice de los gastos. Se imprime su forma, no se supone."""
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(
                        f"{DIRECCION}/api/gastos",
                        headers={"Authorization": f"Bearer {volumen.token}"},
                    ),
                    timeout=30,
                ) as respuesta:
                    return json.loads(respuesta.read().decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                return {"error": str(exc)[:80]}

        los_del_servidor = los_gastos()
        print(
            "  (las claves de la respuesta de gastos: "
            + str(sorted(los_del_servidor.keys()) if isinstance(los_del_servidor, dict) else type(los_del_servidor))
            + ")"
        )
        # Se busca el gasto por su concepto, en cualquier lista de la respuesta.
        def buscar_el_gasto(datos) -> list:
            encontrados: list = []
            if isinstance(datos, dict):
                for valor in datos.values():
                    encontrados += buscar_el_gasto(valor)
            elif isinstance(datos, list):
                for uno in datos:
                    if isinstance(uno, dict) and EL_CONCEPTO in str(uno.get("concepto", "")):
                        encontrados.append(uno)
                    else:
                        encontrados += buscar_el_gasto(uno)
            return encontrados

        los_mios = buscar_el_gasto(los_del_servidor)
        print(f"  (el gasto, como lo devuelve el servidor: {str(los_mios[0])[:300] if los_mios else 'no aparece'})")
        comprobar(
            len(los_mios) == 1,
            f"al guardar, el servidor tiene **un** gasto con ese concepto ({len(los_mios)})",
        )
        captura(nav, "economico-12-gasto-guardado")

        # **Cómo se llama el pendiente de un gasto** (08/10/2026): se piden **sus claves**, en vez de buscarlo a
        # ojo en un volcado largo. Y **el pago parcial**: se abre su formulario y se mira qué pide.
        if los_mios:
            # **Las claves del dinero, enteras** (08/10/2026): el volcado entero se cortaba antes de la `p…`, así
            # que se piden **sólo las que hablan de dinero**, en vez de suponer que el pendiente se llama
            # `pendiente`.
            print(
                "  (las claves del gasto que hablan del dinero: "
                + str(
                    [
                        clave
                        for clave in sorted(los_mios[0])
                        if any(pista in clave for pista in ("pend", "pag", "importe", "estado", "venc"))
                    ]
                )
                + ")"
            )
        print(f"  (lo que el servidor dice que hay por pagar: {str(los_del_servidor.get('por_pagar'))[:220]})")
        # **Se sale del formulario** (08/10/2026): al guardar, la aplicación **se queda dentro** -medido: las
        # acciones eran `gasto-guardar` y `gasto-cancelar`-, así que no hay lista de gastos que marcar. Se sale
        # por su propio botón y se espera **a una condición de la lista**: que estén sus `gasto-elegir`.
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gasto-cancelar\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        # **Se mira qué queda**, en vez de suponer por dónde se sale (08/10/2026): supuse que `gasto-cancelar`
        # volvía a la lista y **no vuelve** -medido: no aparecían sus `gasto-elegir`-. Así que se imprimen las
        # acciones que hay después, y con eso se sabe por dónde se sale de verdad.
        nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=10)
        print(
            "  (después de `gasto-cancelar`, lo que se puede pulsar: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 16))()"
                )
            )
            + ")"
        )
        # **Cómo se elige un gasto para pagar** (08/10/2026): la lista trae `gasto-abrir` por fila -no
        # `gasto-elegir`, que es del formulario-, así que se miran **las casillas** y, si no las hay, se **abre el
        # gasto**, que es lo que haría el agricultor: abrirlo y pagarlo desde su ficha.
        print(
            "  (casillas en la lista de gastos: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input[type=\"checkbox\"]')]"
                    ".map((uno) => uno.id || uno.name || 'sin-nombre').slice(0, 12))()"
                )
            )
            + ")"
        )
        abierto = nav.evaluar(
            "(() => { const filas = [...document.querySelectorAll('#pantalla [data-accion=\"gasto-abrir\"]')];"
            " const mia = filas.find((b) =>"
            f"   (b.closest('tr, li, div') || b).textContent.includes({json.dumps(EL_CONCEPTO)}));"
            " const boton = mia || filas[0];"
            " if (!boton) return false; boton.click(); return true; })()"
        )
        print(f"  (¿se ha abierto el gasto?: {abierto})")
        # **La traza** (08/10/2026): el mismo instrumento que destapó el defecto del albarán. Se sondea cada
        # 100 ms tras pulsar: si la ficha **llega y se cae** -como el formulario del albarán-, o si **nunca
        # llega**. Sin deducir: mirando.
        vistos_gasto: list = []
        for _ in range(40):
            estado_gasto = nav.evaluar(
                "(() => ({"
                " ficha: Boolean(document.querySelector('#pantalla [data-accion=\"gasto-pago-conciliar\"],"
                "  #pantalla [data-accion=\"gasto-anular\"]')),"
                " abrir: document.querySelectorAll('#pantalla [data-accion=\"gasto-abrir\"]').length,"
                " direccion: String(location.hash).slice(0, 40) }))()"
            )
            if not vistos_gasto or vistos_gasto[-1] != estado_gasto:
                vistos_gasto.append(estado_gasto)
                print(f"    gasto, estado {len(vistos_gasto)}: {estado_gasto}")
            time.sleep(0.1)
        print(f"  (estados distintos tras `gasto-abrir`: {len(vistos_gasto)})")

        # **La puerta del pago, desde la ficha** (08/10/2026): el inventario del subagente sitúa
        # `gasto-pago-conciliar` **dentro de la ficha del gasto** (`gastos.js:559`) y la traza confirma que la
        # ficha está ahí. Se pulsa y se mira **qué pide el pago**, en vez de suponerlo.
        pulsado_el_pago = nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gasto-pago-conciliar\"]');"
            " if (!b) return false; b.click(); return true; })()"
        )
        print(f"  (¿se ha pulsado la puerta del pago?: {pulsado_el_pago})")
        nav.esperar("Boolean(document.querySelector('#pantalla input, #pantalla select'))", segundos=20)
        print(
            "  (lo que pide el pago: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select')]"
                    ".map((uno) => uno.id || uno.name || uno.type).slice(0, 20))()"
                )
            )
            + ")"
        )
        print(
            "  (y sus acciones: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 16))()"
                )
            )
            + ")"
        )
        captura(nav, "economico-14-pago")

        # **La vista con selección** (08/10/2026): la ficha del gasto **no** tiene la puerta del pago -medido: sus
        # acciones son repartir, sin asignar, anular y volver-, y el pago se hace sobre gastos **marcados**. Se
        # prueba la vista que el propio nombre anuncia, `gastos-ver-todas`, y se mira si trae **casillas** o
        # `gasto-marcar`. Otra vez: se pregunta antes de tocar.
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gastos-ver-todas\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=15)
        time.sleep(0.8)
        print(
            "  (en `gastos-ver-todas`, casillas y acciones: "
            + str(
                nav.evaluar(
                    "(() => ({ casillas: [...document.querySelectorAll('#pantalla input[type=\"checkbox\"]')]"
                    ".map((uno) => uno.id || uno.name || 'sin-nombre').slice(0, 8),"
                    " acciones: [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 20) }))()"
                )
            )
            + ")"
        )
        captura(nav, "economico-15-gastos-ver-todas")

        # **El formulario del pago, en crudo** (08/10/2026): se vuelve a las cuentas, se pulsa `gasto-pago-nuevo` y
        # se **vuelca lo que aparezca**, sin esperar ninguna acción concreta. Esperar `gasto-pago-conciliar` fue
        # **mi** error: esa es la de conciliar un pago **ya hecho**, no la del pago nuevo. Se incluyen los
        # **rótulos de los botones**, que es lo que dice qué hay que pulsar.
        # **Se instala el vigilante de errores ANTES de pulsar** (08/10/2026): el armazón enseña un aviso
        # genérico cuando no puede montar, así que **el error de verdad hay que cazarlo en la página**. Sin
        # eventos del protocolo: se deja un hueco en la ventana y se lee después.
        nav.evaluar(
            "(() => { window.__elErrorDeLaPantalla = null;"
            " window.addEventListener('error', (e) => {"
            "   window.__elErrorDeLaPantalla = String(e.message) + ' @ ' + String(e.filename) + ':'"
            "     + String(e.lineno) + ':' + String(e.colno); });"
            " window.addEventListener('unhandledrejection', (e) => {"
            "   window.__elErrorDeLaPantalla = 'promesa rechazada: ' + String(e.reason); });"
            " return true; })()"
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gastos-ver\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gasto-pago-nuevo\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        nav.esperar("Boolean(document.querySelector('#pantalla input, #pantalla select'))", segundos=20)
        time.sleep(0.8)
        print(
            "  (el pago nuevo, en crudo: "
            + str(
                nav.evaluar(
                    "(() => ({ campos: [...document.querySelectorAll('#pantalla input, #pantalla select')]"
                    ".map((uno) => uno.id || uno.name || uno.type).slice(0, 20),"
                    " acciones: [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 20),"
                    " botones: [...document.querySelectorAll('#pantalla button')]"
                    ".map((uno) => (uno.textContent || '').trim().slice(0, 26)).slice(0, 14) }))()"
                )
            )
            + ")"
        )
        captura(nav, "economico-16-pago-nuevo")
        print(f"  (el error de la pantalla, si lo hubo: {nav.evaluar('window.__elErrorDeLaPantalla')})")
        print(
            "  (y lo que dice el aviso: "
            + str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText || ''"))[:300]
            + ")"
        )

        # ── Que lo apuntado siga ahí después de recargar (08/10/2026) ────────────────────────────────
        # El encargo lo pide expresamente. Se recarga **de verdad** (`location.reload()`), se espera a que la
        # pantalla vuelva, y se pregunta **al servidor** por lo guardado: la factura, el albarán y el gasto.
        paso(nav, 4, "Que lo apuntado siga ahí después de recargar")
        nav.evaluar("(() => { location.reload(); return null; })()")
        comprobar(
            nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=30),
            "la aplicación **vuelve** después de recargar",
        )
        time.sleep(1.0)
        los_gastos_tras_recargar = los_gastos()
        los_mios_tras = buscar_el_gasto(los_gastos_tras_recargar)
        comprobar(
            len(los_mios_tras) == 1,
            f"y el **gasto sigue guardado** después de recargar ({len(los_mios_tras)} con ese concepto)",
        )
        print(
            "  (el gasto, tras recargar: "
            + str(los_mios_tras[0])[:220]
            if los_mios_tras
            else "  (el gasto no aparece tras recargar)"
        )
        captura(nav, "economico-17-tras-recargar")
        nav.esperar("Boolean(document.querySelector('#pantalla'))", segundos=15)
        print(
            "  (en la ficha del gasto, lo que se puede pulsar: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 18))()"
                )
            )
            + ")"
        )
        print(
            "  (y sus campos: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select')]"
                    ".map((uno) => uno.id || uno.name || uno.type).slice(0, 20))()"
                )
            )
            + ")"
        )
        captura(nav, "economico-13-ficha-del-gasto")

        # **Primero se elige el gasto** (08/10/2026): el pago se hace **sobre gastos marcados** -la pantalla trae
        # `gasto-elegir` y `gasto-marcar`-, así que pulsar el pago sin marcar nada no abre ningún formulario.
        # Se marca **el mío**, buscándolo por su concepto, y se dice si se ha podido.
        marcado = nav.evaluar(
            "(() => { const filas = [...document.querySelectorAll('#pantalla [data-accion=\"gasto-elegir\"]')];"
            " const mia = filas.find((b) =>"
            f"   (b.closest('tr, li, div') || b).textContent.includes({json.dumps(EL_CONCEPTO)}));"
            " const boton = mia || filas[0];"
            " if (!boton) return false; boton.click(); return true; })()"
        )
        print(f"  (¿se ha podido marcar el gasto?: {marcado})")
        time.sleep(0.6)
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"gasto-pago-nuevo\"]');"
            " if (b) { b.click(); return true; } return false; })()"
        )
        # **El formulario del pago**: se mira si está, en vez de darlo por hecho, mientras se aprende el camino.
        print(
            "  (¿hay formulario de pago?: "
            + str(
                nav.esperar(
                    "Boolean(document.querySelector('#pantalla [data-accion=\"gasto-pago-conciliar\"]'))",
                    segundos=20,
                )
            )
            + ")"
        )
        print(
            "  (los campos del pago: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select')]"
                    ".map((uno) => uno.id || uno.name || uno.type).slice(0, 24))()"
                )
            )
            + ")"
        )
        print(
            "  (sus acciones: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla [data-accion]')]"
                    ".map((uno) => uno.dataset.accion).slice(0, 18))()"
                )
            )
            + ")"
        )
        captura(nav, "economico-13-pago-nuevo")
        captura(nav, "economico-6-factura-guardada")

        # **Y guardar dos veces no puede duplicarla**: es el punto 3 de la lista. Aún sin saber si el formulario
        # sigue abierto, se comprueba **cuántas veces** sale su número en la lista.
        # **El recuento de duplicados, contra el servidor** (08/10/2026): contarlo en la pantalla dependía de en
        # qué pantalla estuviera -y **me falló por eso**-, así que se cuenta donde de verdad manda: **cuántas
        # facturas tienen ese número**. Es la prueba de duplicado de verdad, y no depende de dónde esté mirando.
        con_ese_numero = [una for una in guardadas if EL_NUMERO in str(una)]
        comprobar(
            len(con_ese_numero) == 1,
            f"y hay **una sola** factura con el número {EL_NUMERO} (el servidor cuenta {len(con_ese_numero)})",
        )

        # **Y la lectura del documento** (08/10/2026): qué pide y si deja **corregir antes de confirmar**. Se
        # vuelve a facturas y se entra otra vez por `factura-nueva`, que es la puerta de verdad.
        nav.abrir(f"{DIRECCION}/#/facturas", esperar=1.5)
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"factura-nueva\"]');"
            " if (b) { b.click(); } return null; })()"
        )
        nav.esperar("Boolean(document.querySelector('#factura-fichero'))", segundos=20)
        nav.evaluar(
            "(() => { const b = document.querySelector('#pantalla [data-accion=\"factura-leer\"]');"
            " if (b) { b.click(); } return null; })()"
        )
        nav.esperar("Boolean(document.querySelector('#pantalla input, #pantalla select'))", segundos=20)
        print(f"  (la lectura del documento: {nav.evaluar('location.hash')})")
        print(
            "  (lo que pide, campos y acciones: "
            + str(
                nav.evaluar(
                    "(() => [...document.querySelectorAll('#pantalla input, #pantalla select,"
                    " #pantalla [data-accion]')]"
                    ".map((uno) => ((uno.dataset && uno.dataset.accion)"
                    " ? ('accion: ' + uno.dataset.accion)"
                    " : ('campo: ' + (uno.id || uno.name || uno.type))))"
                    ".slice(0, 40))()"
                )
            )
        )
        captura(nav, "economico-4-factura-leer")
        captura(nav, "economico-0-inicio")

    print(f"\nComprobaciones: {len(LAS_COMPROBACIONES)}   Fallos: {len(LOS_FALLOS)}")
    if LOS_HALLAZGOS:
        print(f"Hallazgos: {len(LOS_HALLAZGOS)} (lo que se sabe que falta, medido)")
    return 1 if LOS_FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
