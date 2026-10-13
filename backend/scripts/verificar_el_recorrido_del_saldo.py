"""El recorrido del saldo de un contacto, **andado de verdad**: servidor aislado, navegador y captura.

POR QUÉ EXISTE (14/10/2026). La Entrega 1 del saldo de un contacto se cerró con todo probado menos **el
criterio que solo se puede comprobar andando**: *«Recorrido desde ficha → cifra → documento → vuelta, con
recarga»*. Las pruebas de servidor comprueban las cifras (`app/saldos.py`) y las de JavaScript comprueban
que el componente pinta lo que le llega, pero **ninguna de las dos anda el camino**: abrir la lista de
contactos, abrir la ficha de un contacto que sea cliente **y** proveedor, mirar las dos cifras por
separado, bajar a sus documentos, pulsar el enlace de un documento, volver, y recargar la página entera.

Este guion lo anda entero y **lo cuenta paso a paso**: qué se pidió, qué contestó el servidor (código y
texto) y qué se vio en pantalla. Cuando algo no se puede hacer, se dice con el detalle exacto y **no se
simula**: un recorrido que se salta el paso que falla es un recorrido que miente.

## Lo que monta, y por qué así

  · **Su propio servidor**, en un puerto que no es de nadie (8360 por defecto, nunca 8000 ni 8029) y con
    una **base temporal** (`CUEDIGITAL_DATABASE_URL`). Nunca la base del agricultor.
  · **El escenario prestado**: `datos_representativos.preparar()`, que es el que usan los demás guiones.
    Aquí no se inventan datos: la explotación, sus 64 tierras y su cuenta salen de ahí.
  · **Un contacto que es comprador y proveedor a la vez**, con las cifras del encargo, creado **por las
    puertas de verdad** (`POST /api/contactos`, `/api/ventas`, `/api/facturas-emitidas`, `/api/cobros`,
    `/api/gastos`, `/api/gastos/pagos`): una venta de 1210 facturada y cobrada 400 (quedan 810) y un
    gasto de 600 pagado 150 (quedan 450).
  · **Un navegador de verdad** (`NavegadorDeVerdad`, CDP): abre `#/contactos`, pulsa el botón de abrir la
    ficha de ese contacto y **lee el DOM** —no una captura de la API— para comprobar las dos cifras, sus
    documentos, el enlace de un documento, la vuelta y la recarga completa.
  · **La puerta de datos**, `GET /api/contactos/<id>/saldo`, para no fiarse solo de lo que pinta la
    pantalla, y se dice si las dos coinciden.

Uso:  python scripts/verificar_el_recorrido_del_saldo.py [puerto] [carpeta-de-capturas]
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
PYTHON = sys.executable

# **Los puertos de David no se tocan** (8000 y 8029). El de por defecto es uno libre elegido a mano.
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8360
CARPETA = (
    pathlib.Path(sys.argv[2])
    if len(sys.argv) > 2
    else RAIZ / "docs" / "capturas"
)

# El contacto de esta prueba. El nombre **no puede casar con los veinte que crea `datos_representativos`**
# («Proveedor de la prueba NN S.L.»): si casara, el guion podría estar abriendo la ficha de otro.
NOMBRE = "Cooperativa del Saldo de la Prueba"

# Las cifras del encargo, escritas una sola vez.
VENTA_IMPORTE = "1210"
COBRO = "400"
GASTO_IMPORTE = "600"
PAGO = "150"
NOS_DEBE = "810"
LE_DEBEMOS = "450"
LA_SUMA_QUE_NO_VALE = "360"  # 810 − 450: lo que saldría si alguien restara los dos lados

COMPROBACIONES = 0
FALLOS = 0
PANTALLA: dict = {}


# ---------------------------------------------------------------------------
# Contar y decir
# ---------------------------------------------------------------------------


def comprobar(bien: bool, que: str) -> bool:
    global COMPROBACIONES, FALLOS
    COMPROBACIONES += 1
    if not bien:
        FALLOS += 1
    print(f"  [{'OK   ' if bien else 'FALLO'}] {que}")
    return bien


def paso(numero: str, titulo: str) -> None:
    print(f"\n{numero}) {titulo}")


def decir(texto: str) -> None:
    print(f"       {texto}")


def como_texto(algo) -> str:
    """El JSON, en un renglón y sin pasarse: es lo que contesta el servidor y hay que verlo entero."""
    try:
        crudo = json.dumps(algo, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        crudo = str(algo)
    return crudo if len(crudo) <= 700 else crudo[:700] + " …"


def en_consola(algo) -> str:
    """Lo que la consola de Windows sabe escribir (los emojis y las flechas la revientan)."""
    return str(algo).encode("ascii", "replace").decode("ascii")


# ---------------------------------------------------------------------------
# La puerta de datos
# ---------------------------------------------------------------------------


def _puerta(token: str, metodo: str, camino: str, cuerpo: dict | None = None):
    """Una llamada a la API con el vale del agricultor. Devuelve `(codigo, cuerpo_o_texto)`."""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(
        f"http://127.0.0.1:{PUERTO}{camino}",
        data=datos,
        method=metodo,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            crudo = respuesta.read().decode("utf-8") or "null"
            codigo = respuesta.status
    except urllib.error.HTTPError as fallo:
        crudo = fallo.read().decode("utf-8", "replace") or ""
        codigo = fallo.code
    try:
        return codigo, json.loads(crudo)
    except Exception:  # noqa: BLE001 - lo que importa es el texto tal cual llegó
        return codigo, crudo


def la_puerta(token: str, metodo: str, camino: str, cuerpo: dict | None = None, *, que: str = ""):
    """Igual que `_puerta`, pero **lo cuenta**: qué se pidió y qué se contestó."""
    codigo, devuelto = _puerta(token, metodo, camino, cuerpo)
    if que:
        decir(f"se pide:   {metodo} {camino}")
        decir(f"se manda:  {como_texto(cuerpo)}")
        decir(f"contesta:  {codigo}  {como_texto(devuelto)}")
    return codigo, devuelto


def _numero(valor) -> float | None:
    """Un importe del saldo, venga como venga (texto, número o «No se sabe cuánto»)."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    limpio = str(valor).replace("€", "").replace(" ", "").strip()
    if "," in limpio and "." in limpio:
        limpio = limpio.replace(".", "").replace(",", ".")
    elif "," in limpio:
        limpio = limpio.replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# El servidor de pruebas
# ---------------------------------------------------------------------------


def _el_puerto_esta_libre(puerto: int) -> bool:
    with socket.socket() as hueco:
        try:
            hueco.bind(("127.0.0.1", puerto))
            return True
        except OSError:
            return False


def _un_puerto_libre() -> int:
    with socket.socket() as hueco:
        hueco.bind(("127.0.0.1", 0))
        return int(hueco.getsockname()[1])


def _esperar_al_servidor(segundos: float = 90.0) -> bool:
    final = time.time() + segundos
    while time.time() < final:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{PUERTO}/api/interfaz", timeout=3
            ) as respuesta:
                if respuesta.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.4)
    return False


def levantar_el_servidor(temporal: pathlib.Path) -> tuple[subprocess.Popen, str, pathlib.Path, str]:
    """Arranca uvicorn contra una base temporal y devuelve el proceso y su bitácora."""
    base = temporal / f"cd-saldo-{os.getpid()}.db"
    bitacora = temporal / "servidor.log"
    entorno = dict(os.environ)
    # **La base es la de la prueba**, nunca la del agricultor. Y en UTF-8, que si no la consola de
    # Windows se atraganta con las tildes de los textos.
    entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
    entorno["PYTHONIOENCODING"] = "utf-8"
    with open(bitacora, "wb") as suyo:
        proceso = subprocess.Popen(  # noqa: S603 - es el propio proyecto
            [PYTHON, "-m", "uvicorn", "app.main:app", "--port", str(PUERTO)],
            cwd=str(BACKEND),
            env=entorno,
            stdout=suyo,
            stderr=subprocess.STDOUT,
        )
    return proceso, f"http://127.0.0.1:{PUERTO}", base, str(bitacora)


def apagar_el_servidor(proceso: subprocess.Popen | None) -> str:
    """Apaga el servidor y **lo cuenta**, para que se pueda comprobar que no queda nada vivo."""
    if proceso is None:
        return "no había ningún servidor que apagar"
    if proceso.poll() is not None:
        return f"el servidor ya estaba parado (código {proceso.returncode})"
    proceso.terminate()
    try:
        proceso.wait(timeout=20)
        return f"el servidor se ha apagado (código {proceso.returncode})"
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=10)
        return "el servidor no se apagaba y se ha matado"


# ---------------------------------------------------------------------------
# Lo que se lee de la pantalla
# ---------------------------------------------------------------------------

# **Se lee el DOM, no una captura.** El saldo son dos encabezados (`h3`, uno por sentido) y, debajo de
# cada uno, su lista de documentos (`ul.lista-del-saldo`), que es lo que el componente pinta
# (`react/pantallas/contactos.js`, `unLadoDelSaldo`).
LEER_LA_PANTALLA = """
(() => {
  const p = document.querySelector('#pantalla');
  if (!p) return { hay_pantalla: false };
  const texto = (n) => (n ? n.textContent.replace(/\\s+/g, ' ').trim() : '');
  const listas = [...p.querySelectorAll('ul.lista-del-saldo')].map((ul) => ({
    elementos: [...ul.querySelectorAll('li')].map((li) => ({
      texto: texto(li),
      enlace: li.querySelector('a') ? li.querySelector('a').getAttribute('href') : null,
    })),
  }));
  const acciones = [...p.querySelectorAll('[data-accion]')].map((n) => n.dataset.accion);
  return {
    hay_pantalla: true,
    direccion: window.location.hash,
    titulo: texto(p.querySelector('h1')),
    subtitulo: texto(p.querySelector('h2')),
    encabezados: [...p.querySelectorAll('h3')].map(texto),
    secciones: [...p.querySelectorAll('h2')].map(texto),
    acciones: [...new Set(acciones)],
    listas_del_saldo: listas,
    hay_saldo: p.querySelector('ul.lista-del-saldo') !== null,
    nodos: p.querySelectorAll('*').length,
    texto: p.innerText.replace(/\\s+/g, ' ').trim(),
  };
})()
"""


def leer_la_pantalla(nav) -> dict:
    global PANTALLA
    PANTALLA = nav.evaluar(LEER_LA_PANTALLA) or {"hay_pantalla": False}
    return PANTALLA


def decir_la_pantalla(lo_que_hay: dict) -> None:
    decir(f"en pantalla: {lo_que_hay.get('direccion')!r}  título {lo_que_hay.get('titulo')!r}")
    decir(
        f"secciones: {lo_que_hay.get('secciones')}   "
        f"acciones: {lo_que_hay.get('acciones')}   nodos: {lo_que_hay.get('nodos')}"
    )
    for encabezado in lo_que_hay.get("encabezados") or []:
        decir(f"             {encabezado}")


def decir_lo_que_se_ve(lo_que_hay: dict, cuanto: int = 900) -> None:
    """El texto de la pantalla, tal cual: es «lo que se vio», y sin él no se puede juzgar un fallo."""
    texto = (lo_que_hay.get("texto") or "").strip()
    decir(f"lo que se ve: {texto[:cuanto]!r}")


# **Los errores de la página, apuntados desde el primer momento.** Sin esto, un fallo de JavaScript dentro
# de la ficha se lee como «no hay saldo» y se confunde con que el saldo no esté.
VIGILAR_LOS_ERRORES = """
window.__los_errores = [];
window.addEventListener('error', (e) => window.__los_errores.push('error: ' + String(e.message)));
window.addEventListener('unhandledrejection', (e) => {
  const r = e.reason;
  window.__los_errores.push('promesa rechazada: ' + String((r && r.message) || r));
});
"""

# **Qué le entrega el envoltorio al componente.** `app.js` llama a `pantallaDeUnContacto({... saldo ...})`,
# y esa función es la que monta el elemento de React. Aquí se llama con un saldo y se leen **las
# propiedades que llegan al componente**: si el saldo no está entre ellas, no lo ha perdido el componente
# ni el servidor, lo ha perdido el envoltorio. No se pinta nada y no se toca la aplicación.
LA_SONDA_DEL_ENVOLTORIO = """
(async () => {
  const modulo = await import('/react/pantallas/contactos.js');
  const elemento = modulo.pantallaDeUnContacto({
    textos: {}, borrador: {}, papeles: [], vivos: [],
    corrigiendo: true, borrando: false, guardando: false, error: "",
    saldo: {
      nos_debe: { documentos: [] }, le_debemos: { documentos: [] },
      sin_asignar: { cobros: [], pagos: [] }, para_revisar: [],
    },
  });
  const props = (elemento && elemento.props) || {};
  return {
    componente: (elemento && elemento.type && (elemento.type.name || elemento.type.displayName)) || '',
    propiedades_que_llegan: Object.keys(props).sort(),
    llega_el_saldo: Object.prototype.hasOwnProperty.call(props, 'saldo'),
  };
})()
"""


# ---------------------------------------------------------------------------
# El recorrido
# ---------------------------------------------------------------------------


def montar_el_caso(token: str, campana: int) -> dict:
    """Las cuatro cosas del encargo, por sus puertas de verdad. Devuelve sus identificadores."""
    piezas: dict[str, int | dict] = {}

    paso("2", "El contacto, que es cliente Y proveedor a la vez")
    codigo, contacto = la_puerta(
        token,
        "POST",
        "/api/contactos",
        {
            "nombre": NOMBRE,
            "es_empresa": True,
            "papeles": ["comprador", "proveedor"],
        },
        que="sí",
    )
    comprobar(codigo == 201, f"el contacto se da de alta ({codigo})")
    if codigo != 201:
        raise SystemExit("sin contacto no hay recorrido que andar")
    identificador = int(contacto["id"])
    piezas["contacto"] = identificador
    decir(f"el contacto es el {identificador}, con papeles {contacto.get('papeles')}")

    paso("3", f"La venta de {VENTA_IMPORTE} y su factura")
    cuerpo_de_la_venta = {
        "campana_id": campana,
        "fecha": "2026-07-10",
        "cantidad": 1000,
        "importe": VENTA_IMPORTE,
        "contacto_id": identificador,
        "comprador": NOMBRE,
    }
    codigo, venta = la_puerta(token, "POST", "/api/ventas", cuerpo_de_la_venta, que="sí")
    if codigo != 201:
        # **El cuerpo que pasó el encargo no lleva `producto`**, y el servidor lo rechaza con un aviso
        # bloqueante (`C1_sin_producto`, 422). Se dice tal cual y se repite **añadiendo lo único que el
        # servidor pide**, que es un dato de la venta y no un atajo: sin venta no hay factura, y sin
        # factura no hay saldo que recorrer.
        decir("(el servidor ha rechazado el cuerpo del encargo: se repite añadiendo `producto`, que es")
        decir(" lo único que pide, y se sigue. El rechazo queda escrito arriba.)")
        cuerpo_de_la_venta["producto"] = "Trigo blando"
        codigo, venta = la_puerta(token, "POST", "/api/ventas", cuerpo_de_la_venta, que="sí")
    comprobar(codigo == 201, f"la venta de {VENTA_IMPORTE} se apunta ({codigo})")
    if codigo != 201:
        raise SystemExit("sin venta no hay factura que emitir")
    venta_id = int(venta["id"])
    piezas["venta"] = venta_id

    codigo, factura = la_puerta(
        token,
        "POST",
        "/api/facturas-emitidas",
        {
            "fecha": "2026-07-10",
            "cliente": NOMBRE,
            "contacto_id": identificador,
            "entregas": [venta_id],
        },
        que="sí",
    )
    comprobar(codigo == 201, f"la factura se emite con la entrega dentro ({codigo})")
    if codigo != 201:
        raise SystemExit("sin factura no hay nada que cobrar")
    factura_id = int(factura["id"])
    piezas["factura"] = factura_id
    decir(
        f"la factura es la {factura_id}: importe {factura.get('importe_total')} "
        f"pendiente {factura.get('pendiente')}"
    )

    paso("4", f"El cobro de {COBRO} (quedan {NOS_DEBE})")
    codigo, cobro = la_puerta(
        token,
        "POST",
        "/api/cobros",
        {
            "fecha": "2026-08-01",
            "importe": COBRO,
            "aplicaciones": [{"factura_emitida_id": factura_id, "importe": COBRO}],
        },
        que="sí",
    )
    comprobar(codigo == 201, f"el cobro de {COBRO} se apunta ({codigo})")
    if codigo == 201:
        # **La factura, preguntada por su identificador.** El reparto de un cobro contesta con `factura:
        # null` (el campo es del camino de una factura suelta), así que darla por buena leyendo eso sería
        # dar por bueno un hueco: se vuelve a preguntar por ella.
        _, la_factura = la_puerta(token, "GET", f"/api/facturas-emitidas/{factura_id}", que="sí")
        comprobar(
            _numero(la_factura.get("pendiente")) == float(NOS_DEBE),
            f"y la factura queda pendiente de {NOS_DEBE} ({la_factura.get('texto_pendiente')})",
        )

    paso("5", f"El gasto de {GASTO_IMPORTE} y su pago de {PAGO} (quedan {LE_DEBEMOS})")
    codigo, gasto = la_puerta(
        token,
        "POST",
        "/api/gastos",
        {
            "fecha": "2026-06-01",
            "concepto": "Abono",
            "categoria": "abono",
            "proveedor": NOMBRE,
            "contacto_id": identificador,
            "importe": GASTO_IMPORTE,
        },
        que="sí",
    )
    comprobar(codigo == 201, f"el gasto de {GASTO_IMPORTE} se apunta ({codigo})")
    if codigo != 201:
        raise SystemExit("sin gasto no hay nada que pagar")
    gasto_id = int((gasto.get("gasto") or gasto)["id"])
    piezas["gasto"] = gasto_id

    codigo, pago = la_puerta(
        token,
        "POST",
        "/api/gastos/pagos",
        {
            "fecha": "2026-06-15",
            "importe": PAGO,
            "contacto_id": identificador,
            "proveedor": NOMBRE,
            "aplicaciones": [{"gasto_id": gasto_id, "importe": PAGO}],
        },
        que="sí",
    )
    comprobar(codigo == 201, f"el pago de {PAGO} se apunta ({codigo})")

    return piezas


def por_la_puerta_de_datos(token: str, contacto_id: int) -> dict:
    """`GET /api/contactos/<id>/saldo`, que es lo que dice el servidor sin pasar por la pantalla."""
    paso("6", "Las mismas cifras por la puerta de datos (sin pasar por la pantalla)")
    codigo, saldo = la_puerta(token, "GET", f"/api/contactos/{contacto_id}/saldo", que="sí")
    comprobar(codigo == 200, f"el saldo del contacto se lee ({codigo})")
    if codigo != 200:
        return {}
    nos_debe = saldo.get("nos_debe") or {}
    le_debemos = saldo.get("le_debemos") or {}
    decir(
        f"nos debe: {nos_debe.get('total_texto')!r} (total {nos_debe.get('total')!r})   "
        f"le debemos: {le_debemos.get('total_texto')!r} (total {le_debemos.get('total')!r})"
    )
    comprobar(
        _numero(nos_debe.get("total")) == float(NOS_DEBE),
        f"nos debe {NOS_DEBE} ({nos_debe.get('total_texto')})",
    )
    comprobar(
        _numero(le_debemos.get("total")) == float(LE_DEBEMOS),
        f"le debemos {LE_DEBEMOS} ({le_debemos.get('total_texto')})",
    )
    for lado, nombre in ((nos_debe, "nos debe"), (le_debemos, "le debemos")):
        for documento in lado.get("documentos") or []:
            decir(
                f"documento ({nombre}): clase {documento.get('clase')} "
                f"fecha {documento.get('fecha')} importe {documento.get('importe_texto')} "
                f"cobrado/pagado {documento.get('cobrado_texto') or documento.get('pagado_texto')} "
                f"queda {documento.get('pendiente_texto')}"
            )
    return saldo


def el_recorrido_en_el_navegador(token: str, contacto_id: int, gasto_id: int) -> dict:
    """La mitad que no se puede comprobar sin ojos: la pantalla, el enlace, la vuelta y la recarga."""
    resultado: dict = {"capturas": []}
    CARPETA.mkdir(parents=True, exist_ok=True)

    with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
        nav.medir(1440, 1000, movil=False)
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + json.dumps(token)
                + ");"
                + VIGILAR_LOS_ERRORES
            },
        )

        paso("7", "Abrir la lista de contactos en un navegador de verdad")
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos", esperar=3.0)
        listo = nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
        comprobar(listo, "la pantalla de contactos se dibuja")
        cuantos = nav.evaluar("document.querySelectorAll('#pantalla [data-accion=\"contacto-abrir\"]').length")
        decir(f"la lista trae {cuantos} botones de abrir una ficha")

        paso("8", "Abrir la ficha de ESE contacto (pulsando su botón, como el agricultor)")
        suyo = nav.evaluar(
            "(() => { const b = document.querySelector("
            f"'[data-accion=\"contacto-abrir\"][data-id=\"{contacto_id}\"]');"
            " return b ? true : false; })()"
        )
        comprobar(bool(suyo), f"la fila del contacto {contacto_id} está en la lista")
        if not suyo:
            resultado["sin_ficha"] = True
            return resultado
        nav.pulsar(f'[data-accion="contacto-abrir"][data-id="{contacto_id}"]')
        aparece = nav.esperar("document.querySelector('#pantalla h2') !== null", segundos=20)
        comprobar(aparece, "la ficha se abre")
        nav.esperar("document.querySelector('ul.lista-del-saldo') !== null", segundos=20)
        lo_que_hay = leer_la_pantalla(nav)
        decir_la_pantalla(lo_que_hay)
        decir_lo_que_se_ve(lo_que_hay)
        resultado["ficha"] = lo_que_hay
        # **La captura de la ficha, se vea el saldo o no**: es la pantalla de la que habla el criterio, y
        # una captura es lo único que deja ver de un vistazo si el bloque está o no está.
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "saldo-ficha-del-contacto.png")
        )

        # **Si el saldo no sale, hay que saber POR QUÉ.** Un «no hay saldo» puede ser que el servidor no
        # lo dé, que la llamada falle en el navegador o que el componente no lo pinte: son tres averías
        # distintas y se arreglan en tres sitios distintos, así que se distinguen aquí.
        if not lo_que_hay.get("hay_saldo"):
            pedido_en_el_navegador = nav.evaluar(
                "fetch('/api/contactos/%d/saldo', {headers: {Authorization: "
                "'Bearer ' + window.localStorage.getItem('cuedigital.token')}})"
                ".then((r) => r.text().then((t) => ({estado: r.status, bytes: t.length,"
                " empieza: t.slice(0, 160)})))" % contacto_id
            )
            decir(f"y la misma puerta, pedida DESDE la página: {como_texto(pedido_en_el_navegador)}")
            resultado["la_puerta_desde_la_pagina"] = pedido_en_el_navegador
            los_errores = nav.evaluar("window.__los_errores || []")
            resultado["errores_de_la_pagina"] = los_errores
            decir(f"errores de la página: {como_texto(los_errores)}")
            # **Y por qué no sale.** Se llama al envoltorio que usa la aplicación —el mismo módulo que
            # sirve el servidor— con un saldo y se miran **las propiedades que llegan de verdad** al
            # componente. No se pinta nada: se lee lo que el envoltorio entrega.
            try:
                sonda = nav.evaluar(LA_SONDA_DEL_ENVOLTORIO)
                resultado["sonda_del_envoltorio"] = sonda
                decir(
                    "el envoltorio pantallaDeUnContacto() entrega al componente: "
                    f"{como_texto(sonda)}"
                )
            except Exception as fallo:  # noqa: BLE001
                decir(f"la sonda del envoltorio no se ha podido hacer: {fallo}")

        paso("9", "Las DOS cifras, cada una por su lado, leídas del DOM")
        encabezados = lo_que_hay.get("encabezados") or []
        de_nos_debe = [e for e in encabezados if "Nos debe" in e]
        de_le_debemos = [e for e in encabezados if "Le debemos" in e]
        comprobar(len(de_nos_debe) == 1, f"hay un solo «Nos debe» ({de_nos_debe})")
        comprobar(len(de_le_debemos) == 1, f"hay un solo «Le debemos» ({de_le_debemos})")
        comprobar(
            bool(de_nos_debe) and NOS_DEBE in de_nos_debe[0],
            f"la cifra de lo que nos debe es {NOS_DEBE} ({de_nos_debe[0] if de_nos_debe else '—'})",
        )
        comprobar(
            bool(de_le_debemos) and LE_DEBEMOS in de_le_debemos[0],
            f"la cifra de lo que le debemos es {LE_DEBEMOS} "
            f"({de_le_debemos[0] if de_le_debemos else '—'})",
        )
        comprobar(
            not any(LA_SUMA_QUE_NO_VALE in e for e in encabezados),
            f"ninguna cifra dice {LA_SUMA_QUE_NO_VALE} (los dos lados NO se restan)",
        )
        # Y que no estén mezcladas en un solo número: se mira el saldo entero, no solo los encabezados.
        comprobar(
            not any(
                e.replace(".", "").replace(",", "").find(LA_SUMA_QUE_NO_VALE) >= 0
                for e in encabezados
            ),
            f"y {LA_SUMA_QUE_NO_VALE} no aparece en ningún encabezado del saldo",
        )

        paso("10", "Debajo de cada cifra, sus documentos (fecha, importe, cobrado/pagado y lo que queda)")
        listas = lo_que_hay.get("listas_del_saldo") or []
        comprobar(len(listas) == 2, f"hay dos listas de documentos, una por cifra ({len(listas)})")
        if len(listas) == 2:
            los_de_nos_debe = listas[0]["elementos"]
            los_de_le_debemos = listas[1]["elementos"]
            comprobar(len(los_de_nos_debe) == 1, f"la de «nos debe» trae su documento ({len(los_de_nos_debe)})")
            comprobar(
                len(los_de_le_debemos) == 1,
                f"la de «le debemos» trae su documento ({len(los_de_le_debemos)})",
            )
            for rotulo, elementos, cobrado, queda in (
                ("nos debe", los_de_nos_debe, COBRO, NOS_DEBE),
                ("le debemos", los_de_le_debemos, PAGO, LE_DEBEMOS),
            ):
                if not elementos:
                    continue
                suyo = elementos[0]
                decir(f"documento de «{rotulo}»: {suyo['texto']!r}  ->  {suyo['enlace']!r}")
                comprobar(
                    "2026-" in suyo["texto"] or "/2026" in suyo["texto"],
                    f"lleva su fecha ({rotulo})",
                )
                comprobar(
                    "1.210,00" in suyo["texto"] or "600,00" in suyo["texto"],
                    f"lleva su importe ({rotulo})",
                )
                comprobar(
                    "Cobrado" in suyo["texto"] or "Pagado" in suyo["texto"],
                    f"lleva lo cobrado o lo pagado ({rotulo})",
                )
                comprobar(
                    f"{cobrado},00" in suyo["texto"],
                    f"y lo cobrado/pagado es {cobrado},00 ({rotulo})",
                )
                comprobar(
                    f"{queda},00" in suyo["texto"],
                    f"y lo que queda es {queda},00 ({rotulo})",
                )

        paso("11", "El enlace de un documento lleva a SU pantalla")
        el_enlace = None
        if len(listas) == 2 and listas[1]["elementos"]:
            el_enlace = listas[1]["elementos"][0]["enlace"]
        decir(f"el enlace del gasto: {el_enlace!r}  (se esperaba '#/cuentas/{gasto_id}')")
        comprobar(
            el_enlace == f"#/cuentas/{gasto_id}",
            f"el enlace del gasto apunta a su ficha (#/cuentas/{gasto_id})",
        )
        if el_enlace:
            aviso = pulsar_sin_reventar(nav, f'ul.lista-del-saldo li a[href="{el_enlace}"]')
            if aviso is None:
                time.sleep(1.5)
        else:
            # **No hay enlace que pulsar**, porque el bloque del saldo no está pintado (pasos 9 a 10).
            # No se simula el clic: se va a la MISMA dirección que ese enlace habría usado, para poder
            # decir si el destino funciona o no. Queda dicho que esto no es el clic.
            decir(
                "no hay ningún enlace que pulsar (el bloque del saldo no se ha pintado). "
                f"Se visita a mano la dirección que ese enlace habría usado: #/cuentas/{gasto_id}"
            )
            nav.abrir(f"http://127.0.0.1:{PUERTO}/#/cuentas/{gasto_id}", esperar=2.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        despues = leer_la_pantalla(nav)
        decir_la_pantalla(despues)
        decir_lo_que_se_ve(despues)
        resultado["tras_el_enlace"] = despues
        resultado["el_clic_se_pudo_dar"] = bool(el_enlace)
        comprobar(
            despues.get("direccion") == f"#/cuentas/{gasto_id}",
            f"la pantalla del documento está en #/cuentas/{gasto_id} ({despues.get('direccion')!r})",
        )
        comprobar(
            "no lleva a ninguna parte" not in (despues.get("texto") or "").lower(),
            "y la pantalla NO dice que esa dirección no lleve a ninguna parte",
        )
        comprobar(
            bool(despues.get("titulo")),
            f"y la pantalla carga con su título ({despues.get('titulo')!r})",
        )
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "saldo-documento-del-gasto.png")
        )

        paso("12", "Y desde ahí se vuelve: con el botón de volver de la ficha del gasto")
        hay_volver = nav.evaluar(
            "Boolean(document.querySelector('#pantalla [data-accion=\"gastos-ver\"]'))"
        )
        comprobar(bool(hay_volver), "la ficha del gasto trae un botón de volver")
        if hay_volver:
            aviso = pulsar_sin_reventar(nav, '#pantalla [data-accion="gastos-ver"]')
            if aviso is None:
                time.sleep(1.5)
                nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=20)
                vuelta = leer_la_pantalla(nav)
                decir_la_pantalla(vuelta)
                resultado["tras_el_boton_volver"] = vuelta
                decir(
                    "el botón «volver» de la ficha del gasto es el de la familia de las cuentas: "
                    f"deja en {vuelta.get('direccion')!r} ({vuelta.get('titulo')!r})"
                )
                comprobar(
                    vuelta.get("hay_saldo") is True,
                    "al volver con el botón, el saldo del contacto SIGUE en pantalla",
                )

        paso("13", "Y con «atrás» del navegador, desde la ficha del gasto")
        # El camino del agricultor: la lista, la ficha del contacto, y de ahí al documento. Como el
        # enlace no existe (el saldo no se pinta), el último tramo se hace **por la dirección**, que es
        # a donde el enlace habría llevado; y se dice.
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos", esperar=2.5)
        nav.esperar("document.querySelector('[data-accion=\"contacto-abrir\"]') !== null", segundos=25)
        if abrir_la_ficha(nav, contacto_id):
            antes_de_ir = leer_la_pantalla(nav)
            decir(
                f"con la ficha abierta la dirección es {antes_de_ir.get('direccion')!r} "
                "(la ficha no escribe dirección propia)"
            )
            nav.abrir(f"http://127.0.0.1:{PUERTO}/#/cuentas/{gasto_id}", esperar=2.0)
            donde = leer_la_pantalla(nav)
            decir(f"y en el documento estamos en {donde.get('direccion')!r}")
            nav.evaluar("window.history.back()")
            time.sleep(2.5)
            nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=20)
            atras = leer_la_pantalla(nav)
            decir_la_pantalla(atras)
            resultado["tras_atras"] = atras
            comprobar(
                atras.get("hay_saldo") is True,
                "«atrás» deja el saldo del contacto otra vez en pantalla",
            )
            comprobar(
                NOS_DEBE in " ".join(atras.get("encabezados") or []),
                f"y con su cifra de {NOS_DEBE}",
            )
            if not atras.get("hay_saldo"):
                decir(
                    f"«atrás» deja en {atras.get('direccion')!r}, que es {atras.get('titulo')!r}"
                )

        paso("14", "El saldo, otra vez, tras RECARGAR la página entera")
        # Se vuelve a la lista y se abre la ficha otra vez, para que el estado de partida sea el del
        # agricultor que acaba de abrirla; y se recarga **de verdad** (`Page.reload` vuelve a pedir el
        # documento al servidor: no es un repintado).
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos", esperar=2.5)
        nav.esperar("document.querySelector('[data-accion=\"contacto-abrir\"]') !== null", segundos=25)
        if abrir_la_ficha(nav, contacto_id):
            antes = leer_la_pantalla(nav)
            decir(f"antes de recargar: {antes.get('direccion')!r} — con saldo: {antes.get('hay_saldo')}")
            resultado["antes_de_recargar"] = antes
            if antes.get("hay_saldo"):
                resultado["capturas"].append(
                    guardar_captura(nav, CARPETA / "saldo-del-contacto.png")
                )
            nav.orden("Page.reload", {"ignoreCache": True})
            time.sleep(3.5)
            nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
            recargada = leer_la_pantalla(nav)
            decir_la_pantalla(recargada)
            resultado["tras_recargar"] = recargada
            resultado["capturas"].append(
                guardar_captura(nav, CARPETA / "saldo-del-contacto-tras-recargar.png")
            )
            comprobar(
                recargada.get("hay_saldo") is True
                and NOS_DEBE in " ".join(recargada.get("encabezados") or []),
                f"tras recargar la página entera sigue viéndose el saldo con {NOS_DEBE}",
            )
            comprobar(
                recargada.get("hay_saldo") is True
                and LE_DEBEMOS in " ".join(recargada.get("encabezados") or []),
                f"y con {LE_DEBEMOS}",
            )
            if not recargada.get("hay_saldo"):
                decir(
                    "tras recargar, la dirección se ha quedado en "
                    f"{recargada.get('direccion')!r} y la pantalla es {recargada.get('titulo')!r}"
                )

        paso("15", "¿Tiene la ficha del contacto una dirección propia que se pueda recargar?")
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos/{contacto_id}", esperar=3.0)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        a_donde_va = leer_la_pantalla(nav)
        decir_la_pantalla(a_donde_va)
        decir_lo_que_se_ve(a_donde_va)
        resultado["direccion_de_la_ficha"] = a_donde_va
    return resultado


def abrir_la_ficha(nav, contacto_id: int) -> bool:
    """Pulsa el botón de abrir la ficha y espera. Devuelve si se ha podido."""
    boton = f'[data-accion="contacto-abrir"][data-id="{contacto_id}"]'
    if not nav.evaluar(f"Boolean(document.querySelector({json.dumps(boton)}))"):
        decir(f"no hay ningún botón de abrir la ficha ({boton}): no se puede seguir por aquí")
        return False
    if pulsar_sin_reventar(nav, boton) is not None:
        return False
    time.sleep(1.0)
    return bool(nav.esperar("document.querySelector('#pantalla h1') !== null", segundos=20))


def pulsar_sin_reventar(nav, selector: str) -> str | None:
    """Pulsa, y **si no se puede, lo dice**: un paso que no se puede dar no puede tumbar el recorrido.

    Lo que se rompe se cuenta con el selector exacto, que es lo que hace falta para reproducirlo.
    """
    try:
        nav.pulsar(selector)
        return None
    except RuntimeError as fallo:
        decir(f"NO SE HA PODIDO PULSAR {selector!r}: {fallo}")
        return str(fallo)


def guardar_captura(nav, destino: pathlib.Path) -> str:
    """Una captura de verdad, con su tamaño medido del propio PNG."""
    crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
    destino.write_bytes(crudo)
    ancho, alto = struct.unpack(">II", crudo[16:24])
    decir(f"captura: {destino}  ({ancho}x{alto}, {len(crudo)} bytes)")
    return str(destino)


# ---------------------------------------------------------------------------
# Todo junto
# ---------------------------------------------------------------------------


def main() -> int:
    global PUERTO
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    if not _el_puerto_esta_libre(PUERTO):
        elegido = _un_puerto_libre()
        print(f"  (el puerto {PUERTO} está ocupado; se usa el {elegido}, que está libre)")
        PUERTO = elegido
    if PUERTO in (8000, 8029):
        print("  (el puerto pedido es de David: no se toca)")
        return 2

    print("=" * 78)
    print("  EL RECORRIDO DEL SALDO DE UN CONTACTO — ficha, cifra, documento, vuelta y recarga")
    print("=" * 78)
    print(f"  puerto: {PUERTO}   (nunca 8000 ni 8029)")
    print(f"  intérprete: {PYTHON}")

    temporal = pathlib.Path(tempfile.mkdtemp(prefix="cd-saldo-"))
    servidor = None
    try:
        paso("1", "El servidor aislado, con base temporal")
        servidor, direccion, base, bitacora = levantar_el_servidor(temporal)
        decir(f"se levanta: {PYTHON} -m uvicorn app.main:app --port {PUERTO}")
        decir(f"con CUEDIGITAL_DATABASE_URL=sqlite:///{base}")
        decir(f"y PYTHONIOENCODING=utf-8   (bitácora: {bitacora})")
        comprobar(_esperar_al_servidor(), "el servidor contesta en /api/interfaz")

        decir("se prepara el escenario prestado: datos_representativos.preparar(DIRECCION)")
        escenario = preparar(direccion)
        token = escenario.volumen.token
        campana = escenario.volumen.campana_actual.id
        for renglon in escenario.resumen().splitlines():
            decir(renglon)
        comprobar(bool(token), "hay vale y explotación de verdad")

        piezas = montar_el_caso(token, campana)
        saldo = por_la_puerta_de_datos(token, int(piezas["contacto"]))
        recorrido = el_recorrido_en_el_navegador(
            token, int(piezas["contacto"]), int(piezas["gasto"])
        )

        paso("16", "¿Coincide lo que pinta la pantalla con lo que dice la puerta de datos?")
        ficha = recorrido.get("ficha") or {}
        encabezados = " ".join(ficha.get("encabezados") or [])
        nos_debe = (saldo.get("nos_debe") or {}).get("total_texto") or ""
        le_debemos = (saldo.get("le_debemos") or {}).get("total_texto") or ""
        decir(f"la puerta de datos dice: {nos_debe!r} y {le_debemos!r}")
        decir(f"la pantalla dice:       {encabezados!r}")
        comprobar(
            NOS_DEBE in encabezados and NOS_DEBE in nos_debe,
            f"las dos fuentes dicen {NOS_DEBE} en «nos debe»",
        )
        comprobar(
            LE_DEBEMOS in encabezados and LE_DEBEMOS in le_debemos,
            f"las dos fuentes dicen {LE_DEBEMOS} en «le debemos»",
        )

        paso("17", "El resumen")
        atras = recorrido.get("tras_atras") or {}
        recargada = recorrido.get("tras_recargar") or {}
        volver = recorrido.get("tras_el_boton_volver") or {}
        donde_va_la_ficha = recorrido.get("direccion_de_la_ficha") or {}
        decir(f"la ficha trae el saldo:                    {ficha.get('hay_saldo')}")
        decir(f"el enlace del gasto se ha podido pulsar:   {bool(recorrido.get('el_clic_se_pudo_dar'))}")
        decir(f"la pantalla del gasto carga:               {bool(recorrido.get('tras_el_enlace'))}")
        decir(f"el botón «volver» deja el saldo:           {volver.get('hay_saldo')}")
        decir(f"«atrás» deja el saldo en pantalla:         {atras.get('hay_saldo')}")
        decir(f"tras recargar entera, el saldo sigue:      {recargada.get('hay_saldo')}")
        decir(f"y la dirección tras recargar es:           {recargada.get('direccion')!r}")
        if not recargada.get("hay_saldo"):
            decir(f"tras recargar, el título en pantalla es:   {recargada.get('titulo')!r}")
        decir(
            f"#/contactos/<id> abre:                     "
            f"{donde_va_la_ficha.get('titulo')!r} en {donde_va_la_ficha.get('direccion')!r}"
        )
        if volver:
            decir(
                "el botón «volver» de la ficha del gasto lleva a: "
                f"{volver.get('direccion')!r} ({volver.get('titulo')!r})"
            )
        if recorrido.get("sonda_del_envoltorio"):
            decir(
                "y el envoltorio de la ficha entrega al componente: "
                f"{como_texto(recorrido['sonda_del_envoltorio'])}"
            )

        print(f"\nHUELLA  nos_debe={NOS_DEBE} le_debemos={LE_DEBEMOS} "
              f"ficha={bool(ficha.get('hay_saldo'))} "
              f"clic={bool(recorrido.get('el_clic_se_pudo_dar'))} "
              f"documento={bool(recorrido.get('tras_el_enlace'))} "
              f"volver={bool(volver.get('hay_saldo'))} "
              f"atras={bool(atras.get('hay_saldo'))} "
              f"recarga={bool(recargada.get('hay_saldo'))}")
        print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {FALLOS}")
        return 0 if FALLOS == 0 else 1
    finally:
        print("\n  (se apaga lo que se ha levantado)")
        print(f"  {apagar_el_servidor(servidor)}")
        # **Windows tarda en soltar la base**: el fichero de SQLite sigue abierto un instante después de
        # que el servidor se apague, y borrar la carpeta falla con `PermissionError: [WinError 32]`. Se
        # reintenta unas cuantas veces y, si aun así no se puede, **se dice**: una limpieza que falla en
        # silencio deja basura en el disco de quien ejecuta esto.
        for _intento in range(12):
            shutil.rmtree(temporal, ignore_errors=True)
            if not temporal.exists():
                print(f"  la carpeta temporal se ha borrado: {temporal}")
                break
            time.sleep(0.5)
        else:
            print(f"  AVISO: la carpeta temporal no se ha podido borrar: {temporal}")


if __name__ == "__main__":
    raise SystemExit(main())
