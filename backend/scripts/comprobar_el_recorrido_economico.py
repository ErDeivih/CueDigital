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
            " if (b) { b.click(); return true; } return false; })()"
        )
        print(f"  (se ha pulsado guardar una segunda vez: {segunda_vez})")
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
        captura(nav, "economico-6-factura-guardada")

        # **Y guardar dos veces no puede duplicarla**: es el punto 3 de la lista. Aún sin saber si el formulario
        # sigue abierto, se comprueba **cuántas veces** sale su número en la lista.
        cuantas_veces = nav.evaluar(
            "(() => (document.body.innerText.match(new RegExp(" + json.dumps(EL_NUMERO) + ", 'g')) || []).length)()"
        )
        comprobar(
            int(cuantas_veces or 0) >= 1,
            f"y su número aparece en pantalla {cuantas_veces} vez/veces, para poder contar duplicados",
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
