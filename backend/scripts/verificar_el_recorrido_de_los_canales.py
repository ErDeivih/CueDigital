"""El recorrido de los canales de un contacto (Entrega 2), **andado de verdad**: servidor aislado, navegador y captura.

POR QUÉ EXISTE (13/10/2026). La Entrega 2 dice que un contacto tiene **varios** teléfonos, correos y
direcciones, cada uno con su etiqueta y **uno principal por clase**. Las pruebas de servidor comprueban las
puertas (`POST /api/contactos/<id>/canales`, `.../principal`, `DELETE ...`) y las de JavaScript comprueban
que el componente pinta lo que le llega. **Ninguna de las dos anda el camino**, y el camino tiene tres
tramos que solo se ven andando:

  · **La migración**: lo que ya estaba apuntado en las cuatro columnas de la ficha tiene que aparecer como
    el canal **principal** de su clase en el bloque «Sus teléfonos, correos y direcciones». Si eso no
    pasa, el agricultor cree que ha perdido lo que tenía.
  · **El alta rápida en la ficha** (`#canal-clase`, `#canal-valor`, `#canal-etiqueta` y el botón
    `canal-nuevo`), que es como se apunta el segundo teléfono.
  · **Que se quede**: cambiar el principal, recargar la página entera y que siga el mismo; quitar el
    principal y que otro de su clase pase a serlo.

Este guion lo anda entero y **lo cuenta paso a paso**: qué se pidió, qué contestó el servidor (código y
texto) y qué se vio en pantalla. Cuando un paso no se puede dar, **se dice con el detalle exacto y no se
simula**: un recorrido que se salta el paso que falla es un recorrido que miente.

## Lo que monta, y por qué así

  · **Su propio servidor**, en un puerto que no es de nadie (8362 por defecto, nunca 8000 ni 8029) y con
    una **base temporal** (`CUEDIGITAL_DATABASE_URL`). Nunca la base del agricultor, y se comprueba su
    huella **antes y después**.
  · **El escenario prestado**: `datos_representativos.preparar()`, el mismo que usan los demás guiones.
    De ahí salen la explotación del volumen **y la ajena**, que es la que hace falta para la comprobación
    de aislamiento: el 404 se demuestra con dos explotaciones de verdad en la misma base.
  · **Un contacto creado por la puerta de verdad** (`POST /api/contactos`) con teléfono, correo, dirección
    y localidad, que son los cuatro datos del encargo.
  · **Un navegador de verdad** (`NavegadorDeVerdad`, CDP): abre `#/contactos`, pulsa el botón de abrir la
    ficha y **lee el DOM** —no una captura de la API— para comprobar el bloque de los canales, el alta
    rápida, el principal, la recarga y el quitar.

## El paso que se hace a mano, y por qué se dice

Si el bloque de los canales **no se pinta** para un contacto recién creado, el alta rápida **no existe** y
el recorrido no se puede ni empezar. En ese caso este guion **no se inventa el clic**: apunta el canal por
**la puerta de la API** (`POST /api/contactos/<id>/canales`), que es la puerta de la aplicación, deja la
ficha en el estado que la migración tendría que haber dejado, y **lo dice en voz alta** antes de seguir.
Así el informe separa dos averías que se arreglan en sitios distintos: «el dato no llegó al canal» y «los
controles del canal no funcionan».

Uso:  python scripts/verificar_el_recorrido_de_los_canales.py [puerto] [carpeta-de-capturas]
"""

from __future__ import annotations

import base64
import hashlib
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

# **La base del agricultor no se toca, y se demuestra.** Su huella tiene que ser la misma antes y después.
LA_BASE_DEL_AGRICULTOR = BACKEND / "cuedigital.db"
SU_HUELLA_ESPERADA = "CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12"

# **Los puertos de David no se tocan** (8000 y 8029). El de por defecto es uno libre elegido a mano.
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8362
CARPETA = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "docs" / "capturas"

# El contacto de esta prueba. El nombre **no puede casar con los veinte que crea `datos_representativos`**
# («Proveedor de la prueba NN S.L.»): si casara, el guion podría estar abriendo la ficha de otro.
NOMBRE = "Cooperativa de los Canales de la Prueba"

# Los cuatro datos del encargo, escritos una sola vez.
TELEFONO = "947 123 456"
CORREO = "admin@coop.test"
DIRECCION = "Calle Mayor 3"
LOCALIDAD = "Peñaranda"

# El canal que se apunta desde la pantalla, con el alta rápida.
SEGUNDO_TELEFONO = "947 999 111"
ETIQUETA = "almacén"

# Lo que se lee de la pantalla, con las palabras exactas del servidor (`app/textos.py`).
TITULO_CANALES = "Sus teléfonos, correos y direcciones"
EL_PRINCIPAL = "El principal"

# Los dos mensajes posibles de un 422 en esta puerta, **palabra por palabra** (`app/textos.py`).
CLASE_QUE_NO_EXISTE = "Eso no es un teléfono, un correo ni una dirección."
NADA_ESCRITO = "Escribe el teléfono, el correo o la dirección."

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


def la_huella_de_un_fichero(ruta: pathlib.Path) -> str:
    """La huella del fichero, leído a trozos: la base del agricultor puede ser grande."""
    if not ruta.exists():
        return "(no existe)"
    resumen = hashlib.sha256()
    with open(ruta, "rb") as suyo:
        for trozo in iter(lambda: suyo.read(1024 * 1024), b""):
            resumen.update(trozo)
    return resumen.hexdigest().upper()


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


def _el_detalle(devuelto) -> str:
    """El texto del error, que es lo que hay que citar **palabra por palabra**."""
    if isinstance(devuelto, dict):
        return str(devuelto.get("detail") or devuelto.get("mensaje") or devuelto)
    return str(devuelto)


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


def levantar_el_servidor(
    temporal: pathlib.Path, *, sufijo: str = ""
) -> tuple[subprocess.Popen, str, pathlib.Path, str]:
    """Arranca uvicorn contra una base temporal y devuelve el proceso, su dirección y su bitácora.

    `sufijo` distingue la bitácora de un arranque del de otro: este guion **reinicia** el servidor contra la
    misma base para medir la migración de arranque, y las dos bitácoras tienen que poder leerse.
    """
    base = temporal / f"cd-canales-{os.getpid()}.db"
    bitacora = temporal / f"servidor{sufijo}.log"
    entorno = dict(os.environ)
    # **La base es la de la prueba**, nunca la del agricultor. Y en UTF-8, que si no la consola de
    # Windows se atraganta con las tildes de los textos.
    entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
    entorno["PYTHONIOENCODING"] = "utf-8"
    # **El secreto, fijo y de la prueba.** Sin esto cada arranque se inventa uno (`security.py`) y el vale
    # de la primera vuelta dejaría de valer en la segunda, que es justo lo que hace falta para medir la
    # migración: apagar, volver a arrancar contra la misma base y preguntar con el mismo vale.
    entorno["CUEDIGITAL_SECRETO"] = "el-secreto-de-la-prueba-de-los-canales"
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

# **Se lee el DOM, no una captura.** El bloque de los canales es un `h2` con su título y, debajo, la lista
# `ul.lista-de-canales`, con un `li` por canal: el `<strong>` de delante es su clase («Teléfono») y lleva la
# marca «El principal` el que lo es. El alta rápida son tres controles por `id` y un botón por `data-accion`.
# El error, si lo hay, va en `.aviso-error` (que es `AvisoDeError` en `react/componentes.js`).
LEER_LA_FICHA = """
(() => {
  const p = document.querySelector('#pantalla');
  if (!p) return { hay_pantalla: false };
  const texto = (n) => (n ? n.textContent.replace(/\\s+/g, ' ').trim() : '');
  const TITULO = @TITULO@, PRINCIPAL = @PRINCIPAL@;
  const secciones = [...p.querySelectorAll('h2')].map(texto);
  const lista = p.querySelector('ul.lista-de-canales');
  const canales = lista
    ? [...lista.querySelectorAll('li')].map((li) => {
        const fuertes = [...li.querySelectorAll('strong')].map(texto);
        const botones = [...li.querySelectorAll('[data-accion]')];
        return {
          texto: texto(li),
          clase: fuertes.length ? fuertes[0] : '',
          principal: fuertes.indexOf(PRINCIPAL) >= 0,
          acciones: botones.map((b) => b.dataset.accion),
          canal: botones.length && botones[0].dataset.canal ? botones[0].dataset.canal : null,
        };
      })
    : [];
  const elige = document.getElementById('canal-clase');
  return {
    hay_pantalla: true,
    direccion: window.location.hash,
    titulo: texto(p.querySelector('h1')),
    secciones: secciones,
    hay_bloque: secciones.indexOf(TITULO) >= 0,
    hay_lista: Boolean(lista),
    canales: canales,
    cuantos_canales: canales.length,
    principales: canales.filter((c) => c.principal).map((c) => c.clase),
    alta: {
      hay_clase: Boolean(elige),
      hay_valor: Boolean(document.getElementById('canal-valor')),
      hay_etiqueta: Boolean(document.getElementById('canal-etiqueta')),
      hay_boton: Boolean(p.querySelector('[data-accion="canal-nuevo"]')),
      opciones: elige ? [...elige.options].map((o) => o.value) : [],
      elegida: elige ? elige.value : null,
    },
    error: texto(p.querySelector('.aviso-error')),
    nodos: p.querySelectorAll('*').length,
    texto: p.innerText.replace(/\\s+/g, ' ').trim(),
  };
})()
""".replace("@TITULO@", json.dumps(TITULO_CANALES)).replace("@PRINCIPAL@", json.dumps(EL_PRINCIPAL))

# **Los errores de la página, apuntados desde el primer momento.** Sin esto, un fallo de JavaScript dentro
# de la ficha se lee como «no hay canales» y se confunde con que el bloque no esté pintado.
VIGILAR_LOS_ERRORES = """
window.__los_errores = [];
window.addEventListener('error', (e) => window.__los_errores.push('error: ' + String(e.message)));
window.addEventListener('unhandledrejection', (e) => {
  const r = e.reason;
  window.__los_errores.push('promesa rechazada: ' + String((r && r.message) || r));
});
"""


def leer_la_ficha(nav) -> dict:
    global PANTALLA
    PANTALLA = nav.evaluar(LEER_LA_FICHA) or {"hay_pantalla": False}
    return PANTALLA


def decir_la_ficha(lo_que_hay: dict) -> None:
    decir(f"en pantalla: {lo_que_hay.get('direccion')!r}  título {lo_que_hay.get('titulo')!r}")
    decir(
        f"secciones: {lo_que_hay.get('secciones')}   nodos: {lo_que_hay.get('nodos')}   "
        f"error en pantalla: {lo_que_hay.get('error')!r}"
    )
    decir(
        f"bloque de los canales: {lo_que_hay.get('hay_bloque')}   "
        f"lista: {lo_que_hay.get('hay_lista')}   canales: {lo_que_hay.get('cuantos_canales')}"
    )
    for canal in lo_que_hay.get("canales") or []:
        decir(
            f"             {canal['clase']!r} principal={canal['principal']} "
            f"acciones={canal['acciones']} canal={canal['canal']}  {canal['texto']!r}"
        )
    alta = lo_que_hay.get("alta") or {}
    decir(
        f"alta rápida: clase={alta.get('hay_clase')} valor={alta.get('hay_valor')} "
        f"etiqueta={alta.get('hay_etiqueta')} botón={alta.get('hay_boton')} "
        f"opciones={alta.get('opciones')} elegida={alta.get('elegida')!r}"
    )


def decir_lo_que_se_ve(lo_que_hay: dict, cuanto: int = 1100) -> None:
    """El texto de la pantalla, tal cual: es «lo que se vio», y sin él no se puede juzgar un fallo."""
    texto = (lo_que_hay.get("texto") or "").strip()
    decir(f"lo que se ve: {texto[:cuanto]!r}")


def guardar_captura(nav, destino: pathlib.Path) -> str:
    """Una captura de verdad, con su tamaño medido del propio PNG."""
    crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
    destino.write_bytes(crudo)
    ancho, alto = struct.unpack(">II", crudo[16:24])
    decir(f"captura: {destino}  ({ancho}x{alto}, {len(crudo)} bytes)")
    return str(destino)


# **Las filas se reconocen por su valor, no por la palabra de la clase.** La pantalla dice «Su teléfono»
# porque ese texto vive en `textos.py` y puede cambiar; el número, no. Se comprueba el dato, no el rótulo.
def los_del_telefono(suyos: list[dict]) -> list[dict]:
    return [
        canal
        for canal in suyos
        if TELEFONO in (canal.get("texto") or "") or SEGUNDO_TELEFONO in (canal.get("texto") or "")
    ]


def los_principales_por_clase(suyos: list[dict]) -> dict[str, int]:
    """Cuántas marcas «El principal» hay en cada clase, contando por la palabra que usa la pantalla."""
    cuenta: dict[str, int] = {}
    for canal in suyos:
        if canal.get("principal"):
            clase = canal.get("clase") or "(sin clase)"
            cuenta[clase] = cuenta.get(clase, 0) + 1
    return cuenta


def la_regla_del_principal(suyos: list[dict]) -> bool:
    """La regla entera de un vistazo: **ni dos marcas en una clase ni una clase con valores sin marca**."""
    por_clase = los_principales_por_clase(suyos)
    clases = {canal.get("clase") or "(sin clase)" for canal in suyos}
    return bool(suyos) and all(cuenta == 1 for cuenta in por_clase.values()) and clases == set(por_clase)


def escribir_en_un_campo(nav, campo: str, valor: str) -> str:
    """Escribe en un campo **con el teclado del navegador**, y dice **cómo lo ha conseguido**.

    Devuelve `"teclado"` si el texto ha llegado tecleándolo, y `"javascript"` si ha habido que ponerlo por
    JavaScript. **Se dice y no se disimula**: un tecleo que no llega es un paso que no se ha dado, y quien
    lea el informe tiene que poder distinguir «lo escribí» de «se lo puse».
    """
    nav.evaluar(f"document.getElementById({json.dumps(campo)}).focus()")
    nav.escribir(valor)
    if nav.evaluar(f"document.getElementById({json.dumps(campo)}).value") == valor:
        return "teclado"
    # **El navegador sin ventana a veces no tiene el foco de la página**, y entonces `Input.insertText` no
    # llega a ningún sitio (no da error: simplemente no escribe). Se prueban las teclas de verdad, una a una.
    nav.evaluar(f"document.getElementById({json.dumps(campo)}).focus()")
    for letra in valor:
        nav.orden("Input.dispatchKeyEvent", {"type": "keyDown", "text": letra, "unmodifiedText": letra})
        nav.orden("Input.dispatchKeyEvent", {"type": "keyUp"})
    if nav.evaluar(f"document.getElementById({json.dumps(campo)}).value") == valor:
        return "teclado"
    nav.evaluar(f"document.getElementById({json.dumps(campo)}).value = {json.dumps(valor)}")
    return "javascript"


# **Los repintados de la ficha, contados.** Si el texto tecleado desaparece de un campo, hay que saber si es
# porque la pantalla se ha vuelto a pintar encima: contarlo es lo que convierte «no se queda» en un dato.
VIGILAR_LOS_REPINTADOS = """
(() => {
  window.__repintados = 0;
  const p = document.getElementById('pantalla');
  if (!p) return 'no hay pantalla que vigilar';
  const vigia = new MutationObserver((cambios) => { window.__repintados += cambios.length; });
  vigia.observe(p, { childList: true, subtree: true, characterData: true });
  window.__el_vigia = vigia;
  return 'vigilando';
})()
"""

# **La sonda del campo**, que es lo que hace falta para saber por qué no se queda lo tecleado: cuántos
# elementos con ese `id` hay (un `id` repetido es un defecto en sí), cuál tiene el foco y qué dice el DOM.
LA_SONDA_DEL_CAMPO = """
(() => {
  const todos = [...document.querySelectorAll('#canal-valor')];
  const el = document.getElementById('canal-valor');
  return {
    cuantos_con_ese_id: todos.length,
    cuantas_pantallas: document.querySelectorAll('#pantalla').length,
    tiene_el_foco: Boolean(el) && document.activeElement === el,
    quien_tiene_el_foco: document.activeElement
      ? (document.activeElement.id || document.activeElement.tagName)
      : null,
    valor: el ? el.value : null,
    valor_atributo: el ? el.getAttribute('value') : null,
    se_ve: el ? el.checkVisibility({ checkVisibilityCSS: true }) : null,
    la_pagina_tiene_el_foco: document.hasFocus(),
    es_solo_lectura: el ? el.readOnly : null,
    esta_deshabilitado: el ? el.disabled : null,
    tipo: el ? el.type : null,
    atributos: el ? el.getAttributeNames() : null,
    repintados: window.__repintados,
  };
})()
"""


# **¿Es el mismo elemento el que se enfoca y el que se lee?** Si la pantalla sustituye el campo por otro entre
# el foco y la lectura, el texto entra en un elemento que ya no está y se lee otro vacío. Se apunta el
# elemento en una variable global y se compara después, y se vigila **el cuerpo entero** (no `#pantalla`,
# que también puede ser sustituido) para ver si la pantalla se repinta por debajo.
LA_PRUEBA_DEL_MISMO_CAMPO = """
(() => {
  window.__el_campo = document.getElementById('canal-valor');
  window.__repintados_del_cuerpo = 0;
  window.__vigia_del_cuerpo = new MutationObserver((cambios) => {
    window.__repintados_del_cuerpo += cambios.length;
  });
  window.__vigia_del_cuerpo.observe(document.body, {
    childList: true, subtree: true, characterData: true, attributes: true,
  });
  return window.__el_campo ? 'apuntado' : 'no hay campo';
})()
"""

LA_COMPARACION_DEL_CAMPO = """
(() => {
  const ahora = document.getElementById('canal-valor');
  const antes = window.__el_campo;
  return {
    el_de_antes_sigue_conectado: antes ? antes.isConnected : null,
    el_de_antes_es_el_de_ahora: antes ? (antes === ahora) : null,
    valor_del_de_antes: antes ? antes.value : null,
    valor_del_de_ahora: ahora ? ahora.value : null,
    repintados_del_cuerpo: window.__repintados_del_cuerpo,
  };
})()
"""


def pulsar_sin_reventar(nav, selector: str) -> str | None:
    """Pulsa, y **si no se puede, lo dice**: un paso que no se puede dar no puede tumbar el recorrido."""
    try:
        nav.pulsar(selector)
        return None
    except RuntimeError as fallo:
        decir(f"NO SE HA PODIDO PULSAR {selector!r}: {fallo}")
        return str(fallo)


# ---------------------------------------------------------------------------
# El recorrido
# ---------------------------------------------------------------------------


def el_contacto_por_su_puerta(token: str) -> int:
    """El contacto del encargo, con sus cuatro datos, por `POST /api/contactos`."""
    paso("2", "El contacto, por la puerta de verdad, con teléfono, correo, dirección y localidad")
    codigo, ficha = la_puerta(
        token,
        "POST",
        "/api/contactos",
        {
            "nombre": NOMBRE,
            "es_empresa": True,
            "telefono": TELEFONO,
            "correo": CORREO,
            "direccion": DIRECCION,
            "localidad": LOCALIDAD,
        },
        que="sí",
    )
    comprobar(codigo == 201, f"el contacto se da de alta ({codigo})")
    if codigo != 201:
        raise SystemExit("sin contacto no hay recorrido que andar")
    identificador = int(ficha["id"])
    decir(f"el contacto es el {identificador}")
    decir(
        "los cuatro datos, en las columnas de siempre: "
        f"teléfono {ficha.get('telefono')!r} correo {ficha.get('correo')!r} "
        f"dirección {ficha.get('direccion')!r} localidad {ficha.get('localidad')!r}"
    )
    # **Lo que la puerta devuelve ya dice si la migración ha corrido**: `canales` viene en la respuesta y,
    # si el alta no crea canales, viene vacío. Se dice tal cual, que es el dato del que sale todo lo demás.
    decir(f"y al darla de alta, la ficha trae {len(ficha.get('canales') or [])} canal(es): "
          f"{como_texto(ficha.get('canales'))}")
    return identificador


def la_migracion_por_la_puerta(token: str, contacto_id: int) -> dict:
    """`GET /api/contactos/<id>`: lo que dice el servidor de los canales, sin pasar por la pantalla."""
    paso("3", "La migración, por la puerta de datos: ¿están los cuatro datos como canales principales?")
    codigo, ficha = la_puerta(token, "GET", f"/api/contactos/{contacto_id}", que="sí")
    comprobar(codigo == 200, f"la ficha se lee ({codigo})")
    canales = (ficha or {}).get("canales") or []
    decir(f"canales que devuelve la ficha: {len(canales)}")
    for canal in canales:
        decir(
            f"             {canal.get('clase')} etiqueta={canal.get('etiqueta')!r} "
            f"teléfono={canal.get('telefono')!r} correo={canal.get('correo')!r} "
            f"dirección={canal.get('direccion')!r} localidad={canal.get('localidad')!r} "
            f"principal={canal.get('principal')}"
        )
    comprobar(
        len(canales) >= 3,
        f"los cuatro datos han pasado a ser canales (se esperaban 3: teléfono, correo y dirección; hay {len(canales)})",
    )
    for clase, campo, valor in (
        ("telefono", "telefono", TELEFONO),
        ("correo", "correo", CORREO),
        ("direccion", "direccion", DIRECCION),
    ):
        suyo = next((canal for canal in canales if canal.get("clase") == clase), None)
        comprobar(
            suyo is not None and suyo.get(campo) == valor and suyo.get("principal") is True,
            f"el {clase} {valor!r} es el canal principal de su clase "
            f"({como_texto(suyo) if suyo else 'no hay ningún canal de esa clase'})",
        )
    la_direccion = next((canal for canal in canales if canal.get("clase") == "direccion"), None)
    comprobar(
        la_direccion is not None and la_direccion.get("localidad") == LOCALIDAD,
        f"y la dirección se lleva su localidad ({LOCALIDAD!r}): "
        f"{la_direccion.get('localidad') if la_direccion else '—'!r}",
    )
    return ficha or {}


def el_recorrido_en_el_navegador(token: str, contacto_id: int, ficha_de_la_puerta: dict, ajena: str) -> dict:
    """La mitad que no se puede comprobar sin ojos: la pantalla, el alta, el principal, la recarga y el quitar."""
    resultado: dict = {"capturas": [], "a_mano": False}
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

        # **El foco de la página, pedido a propósito.** Un navegador sin ventana arranca **sin el foco** y
        # entonces `Input.insertText` no llega a ningún campo: no falla, simplemente no escribe. Se pide el
        # foco antes de teclear nada, y si este navegador no sabe darlo, se dice.
        nav.orden("Page.enable")
        nav.orden("Page.bringToFront")
        try:
            nav.orden("Emulation.setFocusEmulationEnabled", {"enabled": True})
            decir("se le pide el foco a la página (`Emulation.setFocusEmulationEnabled`), para poder teclear")
        except RuntimeError as fallo:
            decir(f"(este navegador no sabe dar el foco a la página: {fallo})")

        paso("4", "Abrir la lista de contactos en un navegador de verdad y abrir ESA ficha")
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos", esperar=3.0)
        comprobar(
            nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30),
            "la pantalla de contactos se dibuja",
        )
        suyo = nav.evaluar(
            "Boolean(document.querySelector('"
            f'[data-accion="contacto-abrir"][data-id="{contacto_id}"]'
            "'))"
        )
        comprobar(bool(suyo), f"la fila del contacto {contacto_id} está en la lista")
        if suyo:
            nav.pulsar(f'[data-accion="contacto-abrir"][data-id="{contacto_id}"]')
            nav.esperar(f"document.querySelector('#pantalla h1') !== null", segundos=25)
        else:
            decir("no hay fila que pulsar: se va a la dirección de la ficha, y se dice")
            nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos/{contacto_id}", esperar=3.0)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        time.sleep(1.0)
        ficha = leer_la_ficha(nav)
        decir_la_ficha(ficha)
        decir_lo_que_se_ve(ficha)
        resultado["ficha_recien_creada"] = ficha
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "canales-ficha-sin-bloque.png")
        )
        comprobar(
            bool(ficha.get("titulo")),
            f"la ficha se abre y trae su título ({ficha.get('titulo')!r})",
        )
        comprobar(
            ficha.get("hay_bloque") is True,
            f"en la ficha sale el bloque «{TITULO_CANALES}»",
        )
        comprobar(
            ficha.get("cuantos_canales", 0) >= 3,
            f"y dentro están los canales de los cuatro datos ({ficha.get('cuantos_canales')})",
        )
        if not ficha.get("hay_bloque"):
            decir(
                "el bloque no está: el componente solo lo pinta si la ficha trae algún canal "
                "(`corrigiendo && (borrador.canales || []).length`, en react/pantallas/contactos.js:571), "
                f"y la puerta ha devuelto {len(ficha_de_la_puerta.get('canales') or [])} canal(es)"
            )
        comprobar(
            bool((ficha.get("alta") or {}).get("hay_valor")),
            "y está el alta rápida (#canal-valor) para apuntar otro",
        )

        # **Si el alta rápida no existe, el recorrido no se puede ni empezar.** Se apunta el canal por la
        # puerta de la API —la de la aplicación—, se dice en voz alta, y se sigue: así el informe separa
        # «el dato no llegó al canal» de «los controles del canal no funcionan».
        if not (ficha.get("alta") or {}).get("hay_boton"):
            paso("4b", "EL PASO QUE FALTA, HECHO A MANO Y DICHO: se apunta el teléfono por la puerta de la API")
            decir(
                "el alta rápida no existe porque el bloque no se pinta, y el bloque no se pinta porque la "
                "ficha no trae ningún canal. Se apunta el teléfono de siempre a mano, con la misma puerta "
                "que usa la pantalla, para dejar la ficha como la migración tendría que haberla dejado:"
            )
            codigo, con_canal = la_puerta(
                token,
                "POST",
                f"/api/contactos/{contacto_id}/canales",
                {"clase": "telefono", "telefono": TELEFONO, "principal": True},
                que="sí",
            )
            comprobar(codigo == 200, f"el teléfono de siempre se apunta a mano ({codigo})")
            for clase, cuerpo in (
                ("correo", {"clase": "correo", "correo": CORREO, "principal": True}),
                ("direccion", {"clase": "direccion", "direccion": DIRECCION,
                               "localidad": LOCALIDAD, "principal": True}),
            ):
                codigo, con_canal = la_puerta(
                    token, "POST", f"/api/contactos/{contacto_id}/canales", cuerpo, que="sí"
                )
                comprobar(codigo == 200, f"y el {clase} ({codigo})")
            resultado["a_mano"] = True
            nav.orden("Page.reload", {"ignoreCache": True})
            time.sleep(3.0)
            nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
            time.sleep(1.0)
            ficha = leer_la_ficha(nav)
            decir_la_ficha(ficha)
            decir_lo_que_se_ve(ficha)
            resultado["ficha_con_el_paso_a_mano"] = ficha
            resultado["capturas"].append(
                guardar_captura(nav, CARPETA / "canales-ficha-con-bloque.png")
            )
            comprobar(
                ficha.get("hay_bloque") is True and ficha.get("cuantos_canales") == 3,
                f"con los canales apuntados a mano, el bloque sale con sus 3 canales "
                f"({ficha.get('cuantos_canales')})",
            )
            comprobar(
                la_regla_del_principal(ficha.get("canales") or []),
                "y cada clase con valores tiene UNA sola marca «El principal» "
                f"({los_principales_por_clase(ficha.get('canales') or [])})",
            )
            comprobar(
                (ficha.get("alta") or {}).get("hay_boton") is True,
                "y ahora sí está el alta rápida (el botón `canal-nuevo`)",
            )

        if not (ficha.get("alta") or {}).get("hay_boton"):
            decir("sin alta rápida no se puede apuntar el segundo teléfono: el recorrido se para aquí, y se dice")
            resultado["sin_alta_rapida"] = True
            return resultado

        paso("5", f"Apuntar OTRO teléfono por el alta rápida ({SEGUNDO_TELEFONO}, «{ETIQUETA}»)")
        decir(
            "los tres controles del encargo: "
            f"#canal-clase={json.dumps((ficha['alta'] or {}).get('elegida'))} "
            f"#canal-valor={json.dumps((ficha['alta'] or {}).get('hay_valor'))} "
            f"#canal-etiqueta={json.dumps((ficha['alta'] or {}).get('hay_etiqueta'))}"
        )
        # **Por qué no se queda lo tecleado, medido y no supuesto.** El teclado del protocolo **sí llega** a
        # un `input` de una página en blanco (comprobado aparte, con `Input.insertText` y con teclas una a
        # una), así que si aquí no llega es por algo de esta pantalla. Se mira: dónde está el foco, cuántos
        # elementos hay con ese `id`, si el texto entra y desaparece, y cuántas veces se repinta la ficha.
        decir(f"se enciende el vigía de repintados: {nav.evaluar(VIGILAR_LOS_REPINTADOS)}")
        # **Y se le vuelve a pedir el foco a la página justo antes de teclear.** En un navegador sin ventana
        # el foco de la página se pierde con las navegaciones, y `Input.insertText` **no da error**: simple-
        # mente no escribe en ningún sitio. Como eso se leería como «el campo está roto», se pide el foco
        # aquí, se mide si la página lo tiene, y todo queda dicho.
        nav.orden("Page.bringToFront")
        try:
            nav.orden("Emulation.setFocusEmulationEnabled", {"enabled": True})
        except RuntimeError as fallo:
            decir(f"(no se ha podido pedir el foco de la página: {fallo})")
        time.sleep(0.3)
        antes = nav.evaluar(LA_SONDA_DEL_CAMPO)
        decir(f"el campo, antes de teclear: {como_texto(antes)}")
        nav.evaluar("document.getElementById('canal-valor').focus()")
        con_foco = nav.evaluar(LA_SONDA_DEL_CAMPO)
        decir(f"y con el foco pedido:        {como_texto(con_foco)}")
        comprobar(
            bool((con_foco or {}).get("tiene_el_foco")),
            "el campo #canal-valor coge el foco cuando se le pide",
        )
        comprobar(
            (con_foco or {}).get("cuantos_con_ese_id") == 1,
            f"y hay UN solo campo con ese id ({(con_foco or {}).get('cuantos_con_ese_id')})",
        )
        # **¿Es el mismo elemento el que se enfoca y el que se lee?** Si la pantalla sustituye el campo por
        # otro entre el foco y la lectura, el texto entra en un elemento que ya no está y se lee otro vacío.
        decir(f"se apunta el elemento del campo: {nav.evaluar(LA_PRUEBA_DEL_MISMO_CAMPO)}")
        nav.evaluar("document.getElementById('canal-valor').focus()")
        nav.escribir(SEGUNDO_TELEFONO)
        la_comparacion = nav.evaluar(LA_COMPARACION_DEL_CAMPO)
        decir(f"¿es el mismo elemento el que se enfoca y el que se lee?: {como_texto(la_comparacion)}")
        comprobar(
            bool((la_comparacion or {}).get("el_de_antes_es_el_de_ahora")),
            "el campo no se sustituye entre enfocarlo y leerlo (es el mismo elemento)",
        )
        nav.escribir(SEGUNDO_TELEFONO)
        justo_despues = nav.evaluar(LA_SONDA_DEL_CAMPO)
        time.sleep(0.8)
        un_poco_despues = nav.evaluar(LA_SONDA_DEL_CAMPO)
        decir(f"justo después de teclear:    {como_texto(justo_despues)}")
        decir(f"y 0,8 segundos después:      {como_texto(un_poco_despues)}")
        decir(
            "el teclado del protocolo llega al campo y lo que pasa después: "
            f"entra={bool((justo_despues or {}).get('valor'))} "
            f"se_queda={bool((un_poco_despues or {}).get('valor'))} "
            f"repintados_durante_el_tecleo={(un_poco_despues or {}).get('repintados')}"
        )
        comprobar(
            bool((un_poco_despues or {}).get("valor")),
            "lo tecleado en #canal-valor SE QUEDA en el campo (no lo borra un repintado)",
        )
        # **Y si el campo acepta texto por la vía del propio navegador.** `document.execCommand('insertText')`
        # es la maquinaria de edición del navegador sobre el elemento que tiene el foco. Si esto tampoco
        # escribe, el que no acepta texto es **el campo** (un `readonly`, por ejemplo) y eso no es cosa del
        # teclado del protocolo: es la pantalla.
        lo_que_dice_el_navegador = nav.evaluar(
            "(() => { const el = document.getElementById('canal-valor');"
            " if (!el) return 'no hay campo';"
            " el.focus();"
            " let vale = null;"
            " try { vale = document.execCommand('insertText', false, 'PRUEBA'); }"
            " catch (fallo) { vale = 'reventó: ' + fallo.message; }"
            " return {lo_ha_aceptado: vale, valor: el.value,"
            " es_solo_lectura: el.readOnly, esta_deshabilitado: el.disabled}; })()"
        )
        decir(f"y el campo, con la maquinaria de edición del navegador: {como_texto(lo_que_dice_el_navegador)}")
        comprobar(
            bool((lo_que_dice_el_navegador or {}).get("valor")),
            "el campo ACEPTA texto escrito (no es de solo lectura ni está deshabilitado)",
        )
        nav.evaluar("document.getElementById('canal-valor').value = ''")

        # Se teclea **en el campo**, no se pone el valor por JavaScript: `Input.insertText` es lo que hace
        # el navegador cuando el agricultor escribe. Y **se lee lo que ha quedado en el campo**, porque un
        # tecleo que no llega es un paso que no se ha dado.
        for campo, valor in (("canal-valor", SEGUNDO_TELEFONO), ("canal-etiqueta", ETIQUETA)):
            como = escribir_en_un_campo(nav, campo, valor)
            resultado[f"como_se_escribio_{campo}"] = como
            decir(f"en #{campo} el texto ha llegado por: {como}")
        tecleado = nav.evaluar(
            "({valor: document.getElementById('canal-valor').value,"
            " etiqueta: document.getElementById('canal-etiqueta').value,"
            " clase: document.getElementById('canal-clase').value})"
        )
        decir(f"lo que ha quedado en los campos, leído del DOM: {como_texto(tecleado)}")
        comprobar(
            (tecleado or {}).get("valor") == SEGUNDO_TELEFONO
            and (tecleado or {}).get("etiqueta") == ETIQUETA,
            "los campos llevan lo que se ha escrito, leído del DOM",
        )
        comprobar(
            resultado.get("como_se_escribio_canal-valor") == "teclado"
            and resultado.get("como_se_escribio_canal-etiqueta") == "teclado",
            "y ha llegado escribiéndolo con el teclado, no poniéndolo por JavaScript "
            f"({resultado.get('como_se_escribio_canal-valor')!r}, "
            f"{resultado.get('como_se_escribio_canal-etiqueta')!r})",
        )
        comprobar(
            (tecleado or {}).get("clase") == "telefono",
            f"la clase elegida es «teléfono» ({(tecleado or {}).get('clase')!r})",
        )
        aviso = pulsar_sin_reventar(nav, '[data-accion="canal-nuevo"]')
        comprobar(aviso is None, "el botón «Apuntar otro» se ha podido pulsar")
        if aviso is None:
            nav.esperar(
                "document.querySelectorAll('ul.lista-de-canales li').length >= 4", segundos=30
            )
            time.sleep(1.0)
        anadido = leer_la_ficha(nav)
        decir_la_ficha(anadido)
        decir_lo_que_se_ve(anadido)
        resultado["tras_apuntar"] = anadido
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "canales-dos-telefonos.png")
        )
        _, ficha_ahora = la_puerta(token, "GET", f"/api/contactos/{contacto_id}")
        los_telefonos = [
            canal for canal in (ficha_ahora.get("canales") or []) if canal.get("clase") == "telefono"
        ]
        decir(f"la puerta de datos dice que hay {len(los_telefonos)} teléfonos: {como_texto(los_telefonos)}")
        comprobar(
            len(los_telefonos) == 2
            and any(canal.get("telefono") == SEGUNDO_TELEFONO for canal in los_telefonos),
            f"el segundo teléfono ({SEGUNDO_TELEFONO}) queda apuntado",
        )
        comprobar(
            any(
                canal.get("telefono") == SEGUNDO_TELEFONO and canal.get("etiqueta") == ETIQUETA
                for canal in los_telefonos
            ),
            f"y con su etiqueta «{ETIQUETA}»",
        )
        comprobar(
            anadido.get("cuantos_canales", 0) == 4,
            f"y la pantalla enseña los cuatro canales ({anadido.get('cuantos_canales')})",
        )
        el_nuevo = next(
            (canal for canal in los_telefonos if canal.get("telefono") == SEGUNDO_TELEFONO), None
        )
        el_de_siempre = next(
            (canal for canal in los_telefonos if canal.get("telefono") == TELEFONO), None
        )
        if el_nuevo is None or el_de_siempre is None:
            decir("no están los dos teléfonos: sin ellos no se puede seguir con el principal")
            resultado["sin_los_dos_telefonos"] = True
            return resultado
        resultado["canal_nuevo"] = int(el_nuevo["id"])
        resultado["canal_de_siempre"] = int(el_de_siempre["id"])

        paso("6", "Elegir el nuevo como principal, y que el de siempre DEJE de serlo")
        comprobar(
            el_de_siempre.get("principal") is True,
            "de partida el principal del teléfono es el de siempre",
        )
        el_nuevo_id = int(el_nuevo["id"])
        el_de_siempre_id = int(el_de_siempre["id"])
        el_boton = f'[data-accion="canal-principal"][data-canal="{el_nuevo_id}"]'
        hay_boton = nav.evaluar(f"Boolean(document.querySelector({json.dumps(el_boton)}))")
        decir(
            f"el botón de usar como principal en el canal {el_nuevo_id}: {hay_boton}  "
            "(el que ya es principal no lo lleva, y eso es lo que se comprueba)"
        )
        comprobar(
            bool(hay_boton),
            f"el canal nuevo ({SEGUNDO_TELEFONO}) trae el botón de «usar este»",
        )
        el_del_viejo = f'[data-accion="canal-principal"][data-canal="{el_de_siempre_id}"]'
        comprobar(
            nav.evaluar(f"Boolean(document.querySelector({json.dumps(el_del_viejo)}))") is False,
            "y el que ya es principal NO trae ese botón (un botón que no hace nada sería un botón de más)",
        )
        if hay_boton:
            aviso = pulsar_sin_reventar(nav, el_boton)
            if aviso is None:
                time.sleep(2.0)
                nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        principal = leer_la_ficha(nav)
        decir_la_ficha(principal)
        decir_lo_que_se_ve(principal)
        resultado["tras_el_principal"] = principal
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "canales-nuevo-principal.png")
        )
        _, ficha_ahora = la_puerta(token, "GET", f"/api/contactos/{contacto_id}")
        los_telefonos = [
            canal for canal in (ficha_ahora.get("canales") or []) if canal.get("clase") == "telefono"
        ]
        decir(f"la puerta de datos dice: {como_texto(los_telefonos)}")
        principales = [canal for canal in los_telefonos if canal.get("principal")]
        comprobar(
            len(principales) == 1 and principales[0].get("telefono") == SEGUNDO_TELEFONO,
            f"el principal del teléfono pasa a ser el nuevo y solo hay uno ({como_texto(principales)})",
        )
        comprobar(
            all(not canal.get("principal") for canal in los_telefonos if canal.get("telefono") == TELEFONO),
            f"y el de siempre ({TELEFONO}) ha dejado de llevarlo",
        )
        # Y en la pantalla, que es lo que se mira: la marca «El principal» tiene que estar **una sola vez**
        # por clase, y en el `li` del nuevo. Se mira clase por clase, que es como lo pide el encargo.
        suyos = principal.get("canales") or []
        de_telefono = los_del_telefono(suyos)
        con_marca = [canal for canal in de_telefono if canal.get("principal")]
        comprobar(
            len(con_marca) == 1 and SEGUNDO_TELEFONO in (con_marca[0]["texto"] if con_marca else ""),
            f"en la pantalla hay UNA sola marca «{EL_PRINCIPAL}» de teléfono, y está en el nuevo "
            f"({[canal['texto'] for canal in con_marca]})",
        )
        comprobar(
            la_regla_del_principal(suyos),
            "y no hay dos marcados: cada clase con valores tiene una sola marca "
            f"({los_principales_por_clase(suyos)})",
        )

        paso("7", "RECARGAR la página entera y ver si se queda")
        # **Primero, lo que pasa al recargar donde deja el botón de abrir.** Se dice, porque es lo que haría
        # el agricultor, y de aquí sale si la ficha tiene dirección propia.
        antes_de_recargar = leer_la_ficha(nav)
        decir(
            f"tras pulsar el botón de abrir, la dirección es {antes_de_recargar.get('direccion')!r} "
            "(se dice: la ficha abierta desde la lista puede no escribir su propia dirección)"
        )
        resultado["direccion_tras_el_boton"] = antes_de_recargar.get("direccion")
        nav.orden("Page.reload", {"ignoreCache": True})
        time.sleep(3.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
        time.sleep(1.0)
        recargada = leer_la_ficha(nav)
        decir_la_ficha(recargada)
        resultado["tras_recargar_donde_deja_el_boton"] = recargada
        comprobar(
            recargada.get("cuantos_canales") == 4
            and any(SEGUNDO_TELEFONO in (canal.get("texto") or "") for canal in recargada.get("canales") or []),
            "al recargar donde deja el botón de abrir, la ficha sigue con sus dos teléfonos",
        )
        # **Y ahora, en la dirección propia de la ficha**, que es la que la aplicación dice que se puede
        # recargar (`app.js`: «se abre por su puerta… recargar tiene que dejar la ficha entera»).
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos/{contacto_id}", esperar=3.0)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        time.sleep(1.0)
        en_su_direccion = leer_la_ficha(nav)
        decir_la_ficha(en_su_direccion)
        comprobar(
            en_su_direccion.get("cuantos_canales") == 4,
            f"la ficha en su propia dirección trae los cuatro canales "
            f"({en_su_direccion.get('cuantos_canales')})",
        )
        nav.orden("Page.reload", {"ignoreCache": True})
        time.sleep(3.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
        time.sleep(1.0)
        recargada = leer_la_ficha(nav)
        decir_la_ficha(recargada)
        decir_lo_que_se_ve(recargada)
        resultado["tras_recargar"] = recargada
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "canales-tras-recargar.png")
        )
        suyos = recargada.get("canales") or []
        los_dos = los_del_telefono(suyos)
        comprobar(
            len(los_dos) == 2,
            f"tras recargar la página entera siguen los DOS teléfonos ({len(los_dos)})",
        )
        comprobar(
            len([canal for canal in los_dos if canal.get("principal")]) == 1
            and SEGUNDO_TELEFONO
            in ([canal["texto"] for canal in los_dos if canal.get("principal")] or [""])[0],
            "y el principal sigue siendo el mismo "
            f"({[canal['texto'] for canal in los_dos if canal.get('principal')]})",
        )
        comprobar(
            any(ETIQUETA in (canal.get("texto") or "") for canal in los_dos),
            f"y el nuevo conserva su etiqueta «{ETIQUETA}»",
        )
        comprobar(
            la_regla_del_principal(suyos),
            "y sigue habiendo una sola marca por clase "
            f"({los_principales_por_clase(suyos)})",
        )

        paso("8", f"QUITAR el principal ({SEGUNDO_TELEFONO}) y ver quién pasa a serlo")
        el_boton = f'[data-accion="canal-quitar"][data-canal="{el_nuevo_id}"]'
        comprobar(
            bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(el_boton)}))")),
            f"el canal {el_nuevo_id} trae su botón de quitar",
        )
        aviso = pulsar_sin_reventar(nav, el_boton)
        if aviso is None:
            nav.esperar(
                "document.querySelectorAll('ul.lista-de-canales li').length <= 3", segundos=30
            )
            time.sleep(1.0)
        quitado = leer_la_ficha(nav)
        decir_la_ficha(quitado)
        decir_lo_que_se_ve(quitado)
        resultado["tras_quitar"] = quitado
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "canales-tras-quitar.png")
        )
        suyos = quitado.get("canales") or []
        comprobar(
            not any(SEGUNDO_TELEFONO in (canal.get("texto") or "") for canal in suyos),
            f"el canal quitado ({SEGUNDO_TELEFONO}) desaparece de la pantalla",
        )
        de_telefono = los_del_telefono(suyos)
        comprobar(
            len(de_telefono) == 1 and TELEFONO in de_telefono[0]["texto"],
            f"y queda el otro de su clase ({[canal['texto'] for canal in de_telefono]})",
        )
        comprobar(
            len(de_telefono) == 1 and de_telefono[0].get("principal") is True,
            f"y ese otro ha pasado a ser el principal ({EL_PRINCIPAL}): "
            f"{[canal['texto'] for canal in de_telefono]}",
        )
        comprobar(
            la_regla_del_principal(suyos),
            "y la clase no se ha quedado sin ninguno ni con dos marcas "
            f"({los_principales_por_clase(suyos)})",
        )
        _, ficha_ahora = la_puerta(token, "GET", f"/api/contactos/{contacto_id}")
        los_telefonos = [
            canal for canal in (ficha_ahora.get("canales") or []) if canal.get("clase") == "telefono"
        ]
        decir(f"la puerta de datos dice: {como_texto(los_telefonos)}")
        comprobar(
            len(los_telefonos) == 1
            and los_telefonos[0].get("telefono") == TELEFONO
            and los_telefonos[0].get("principal") is True,
            "y por la puerta de datos queda ese mismo, como principal",
        )

        paso("9", "Y otra vez la página entera, para ver que también se queda")
        nav.orden("Page.reload", {"ignoreCache": True})
        time.sleep(3.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
        time.sleep(1.0)
        recargada = leer_la_ficha(nav)
        decir_la_ficha(recargada)
        decir_lo_que_se_ve(recargada)
        resultado["tras_recargar_2"] = recargada
        resultado["capturas"].append(
            guardar_captura(nav, CARPETA / "canales-tras-recargar-2.png")
        )
        suyos = recargada.get("canales") or []
        de_telefono = los_del_telefono(suyos)
        comprobar(
            len(de_telefono) == 1
            and TELEFONO in de_telefono[0]["texto"]
            and de_telefono[0].get("principal") is True,
            f"tras recargar sigue habiendo un solo teléfono y es el principal "
            f"({[canal['texto'] for canal in de_telefono]})",
        )
        comprobar(
            recargada.get("cuantos_canales") == 3,
            f"y siguen los tres canales del principio ({recargada.get('cuantos_canales')})",
        )
        comprobar(
            la_regla_del_principal(suyos),
            "y la regla del principal sigue en pie "
            f"({los_principales_por_clase(suyos)})",
        )
        resultado["errores_de_la_pagina"] = nav.evaluar("window.__los_errores || []")
        decir(f"errores de la página en todo el recorrido: {como_texto(resultado['errores_de_la_pagina'])}")

        paso("10", "AISLAMIENTO: la segunda explotación no puede tocar los canales de la primera")
        el_mio = resultado.get("canal_nuevo")
        codigo, cruzado = la_puerta(
            ajena,
            "POST",
            f"/api/contactos/{contacto_id}/canales",
            {"clase": "telefono", "telefono": "666 000 000", "principal": True},
            que="sí",
        )
        comprobar(codigo == 404, f"apuntar un canal en la ficha de otro da 404 ({codigo})")
        resultado["aislamiento"] = codigo == 404
        decir(f"y lo que contesta: {como_texto(cruzado)}")
        if el_mio:
            codigo, cruzado = la_puerta(
                ajena,
                "DELETE",
                f"/api/contactos/{contacto_id}/canales/{el_mio}",
                que="sí",
            )
            comprobar(codigo == 404, f"y quitárselo también da 404 ({codigo})")

    return resultado


def las_puertas_y_sus_422(token: str, contacto_id: int) -> dict:
    """Las dos negativas de la puerta, **con su texto exacto**, que es lo que el encargo pide citar."""
    paso("11", "Las dos negativas de la puerta, con su texto exacto (422)")
    salida: dict = {}
    codigo, devuelto = la_puerta(
        token,
        "POST",
        f"/api/contactos/{contacto_id}/canales",
        {"clase": "whatsapp", "telefono": "947 000 000"},
        que="sí",
    )
    salida["clase_rara"] = (codigo, _el_detalle(devuelto))
    comprobar(codigo == 422, f"una clase que no existe da 422 ({codigo})")
    comprobar(
        _el_detalle(devuelto) == CLASE_QUE_NO_EXISTE,
        f"y su texto es, palabra por palabra: «{_el_detalle(devuelto)}»",
    )
    decir(f"se esperaba:   «{CLASE_QUE_NO_EXISTE}»")
    codigo, devuelto = la_puerta(
        token,
        "POST",
        f"/api/contactos/{contacto_id}/canales",
        {"clase": "telefono"},
        que="sí",
    )
    salida["sin_nada"] = (codigo, _el_detalle(devuelto))
    comprobar(codigo == 422, f"un canal sin nada escrito da 422 ({codigo})")
    comprobar(
        _el_detalle(devuelto) == NADA_ESCRITO,
        f"y su texto es, palabra por palabra: «{_el_detalle(devuelto)}»",
    )
    decir(f"se esperaba:   «{NADA_ESCRITO}»")
    return salida


# ---------------------------------------------------------------------------
# Todo junto
# ---------------------------------------------------------------------------


def main() -> int:
    global PUERTO
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    print("=" * 78)
    print("  EL RECORRIDO DE LOS CANALES DE UN CONTACTO — migración, alta, principal, quitar y recarga")
    print("=" * 78)
    print(f"  puerto: {PUERTO}   (nunca 8000 ni 8029)")
    print(f"  intérprete: {PYTHON}")

    paso("0", "La base del agricultor, que NO se toca")
    huella_antes = la_huella_de_un_fichero(LA_BASE_DEL_AGRICULTOR)
    decir(f"sha256 antes: {huella_antes}")
    decir(f"se esperaba:  {SU_HUELLA_ESPERADA}")
    comprobar(
        huella_antes == SU_HUELLA_ESPERADA,
        "la huella de la base del agricultor es la que tiene que ser, antes de empezar",
    )

    if not _el_puerto_esta_libre(PUERTO):
        elegido = _un_puerto_libre()
        print(f"  (el puerto {PUERTO} está ocupado; se usa el {elegido}, que está libre)")
        PUERTO = elegido
    if PUERTO in (8000, 8029):
        print("  (el puerto pedido es de David: no se toca)")
        return 2

    temporal = pathlib.Path(tempfile.mkdtemp(prefix="cd-canales-"))
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
        ajena = escenario.ajena.token
        for renglon in escenario.resumen().splitlines():
            decir(renglon)
        comprobar(bool(token), "hay vale y explotación de verdad")
        comprobar(bool(ajena), "y hay una SEGUNDA explotación, para el aislamiento")
        decir(
            f"la explotación del volumen es la {escenario.volumen.explotacion_id} y la ajena la "
            f"{escenario.ajena.explotacion_id}"
        )

        contacto_id = el_contacto_por_su_puerta(token)
        ficha = la_migracion_por_la_puerta(token, contacto_id)
        recorrido = el_recorrido_en_el_navegador(token, contacto_id, ficha, ajena)
        las_puertas = las_puertas_y_sus_422(token, contacto_id)

        paso("12", "La migración DE ARRANQUE, medida reiniciando el servidor contra la MISMA base")
        # **Esto es lo que convierte «lo he leído en el código» en «lo he medido».** La migración de los
        # canales es de arranque: solo puede tocar las fichas que ya existen cuando el servidor se levanta.
        # Con el servidor ya en marcha, una ficha creada después **nunca pasa por ella**, así que la única
        # forma de comprobarla es apagar, volver a arrancar contra la misma base y preguntar por esa ficha.
        decir(
            "se crea una ficha con los cuatro datos y se reinicia el servidor contra la misma base temporal: "
            "ese es el momento en el que sus cuatro datos tendrían que pasar a ser canales principales."
        )
        codigo, otra_ficha = la_puerta(
            token,
            "POST",
            "/api/contactos",
            {
                "nombre": NOMBRE + " (para el reinicio)",
                "es_empresa": True,
                "telefono": TELEFONO,
                "correo": CORREO,
                "direccion": DIRECCION,
                "localidad": LOCALIDAD,
            },
            que="sí",
        )
        comprobar(codigo == 201, f"la ficha del reinicio se crea ({codigo})")
        otro_id = int(otra_ficha["id"])
        decir(
            f"la ficha del reinicio es la {otro_id} y nace con "
            f"{len(otra_ficha.get('canales') or [])} canal(es)"
        )
        decir(f"se apaga el servidor: {apagar_el_servidor(servidor)}")
        servidor = None
        servidor, direccion, base, bitacora_del_reinicio = levantar_el_servidor(temporal, sufijo="-reinicio")
        comprobar(_esperar_al_servidor(), "el servidor vuelve a contestar tras el reinicio")
        codigo, despues_del_reinicio = la_puerta(token, "GET", f"/api/contactos/{otro_id}", que="sí")
        comprobar(codigo == 200, f"la ficha del reinicio se vuelve a leer ({codigo})")
        canales_tras_arrancar = (despues_del_reinicio or {}).get("canales") or []
        comprobar(
            len(canales_tras_arrancar) >= 3,
            "tras arrancar, los cuatro datos de esa ficha son canales principales "
            f"({len(canales_tras_arrancar)} canal/es)",
        )
        lo_que_dice_el_arranque = [
            renglon.strip()
            for renglon in pathlib.Path(bitacora_del_reinicio)
            .read_text(encoding="utf-8", errors="replace")
            .splitlines()
            if "canal" in renglon.lower()
        ]
        decir(
            "y lo que el arranque dice de los canales, en su bitácora: "
            f"{lo_que_dice_el_arranque or '(no dice nada de canales)'}"
        )
        comprobar(
            bool(lo_que_dice_el_arranque),
            "el arranque deja dicho en su bitácora lo que ha llevado a la tabla de canales",
        )

        paso("13", "El resumen")
        ficha_en_pantalla = recorrido.get("ficha_recien_creada") or {}
        despues_de_recargar = recorrido.get("tras_recargar") or {}
        despues_de_quitar = recorrido.get("tras_quitar") or {}
        despues_de_recargar_2 = recorrido.get("tras_recargar_2") or {}
        decir(f"canales que traía la ficha recién creada, por la puerta:  {len(ficha.get('canales') or [])}")
        decir(f"el bloque de los canales, sin ayuda, en la pantalla:        {ficha_en_pantalla.get('hay_bloque')}")
        decir(f"el alta rápida, sin ayuda, en la pantalla:                  {(ficha_en_pantalla.get('alta') or {}).get('hay_boton')}")
        decir(f"hubo que apuntar los canales a mano por la API:             {recorrido.get('a_mano')}")
        decir(f"canales en pantalla tras apuntar el segundo teléfono:       {(recorrido.get('tras_apuntar') or {}).get('cuantos_canales')}")
        decir(f"tras recargar la página entera:                             {despues_de_recargar.get('cuantos_canales')} canales")
        decir(f"tras quitar el principal:                                   {despues_de_quitar.get('cuantos_canales')} canales")
        decir(f"tras la segunda recarga:                                    {despues_de_recargar_2.get('cuantos_canales')} canales")
        decir(f"el aislamiento (404 al tocar la ficha de otro):             {recorrido.get('aislamiento')}")
        decir(f"las dos negativas, con su texto:                            {como_texto(las_puertas)}")
        decir(f"errores de la página:                                       {como_texto(recorrido.get('errores_de_la_pagina'))}")
        decir(
            "canales de la ficha del reinicio, tras arrancar el servidor: "
            f"{len(canales_tras_arrancar)}"
        )

        los_dos = los_del_telefono((recorrido.get("tras_apuntar") or {}).get("canales") or [])
        de_telefono_tras_quitar = los_del_telefono(despues_de_quitar.get("canales") or [])
        print(
            "\nHUELLA"
            f" canales={(recorrido.get('tras_apuntar') or {}).get('cuantos_canales')}"
            f" migracion_arranque={len(canales_tras_arrancar) >= 3}"
            f" en_el_alta={len(ficha.get('canales') or []) >= 3}"
            f" bloque={ficha_en_pantalla.get('hay_bloque')}"
            f" alta={bool((ficha_en_pantalla.get('alta') or {}).get('hay_boton'))}"
            f" dos_telefonos={len(los_dos) == 2}"
            f" principal={bool(despues_de_recargar.get('cuantos_canales') == 4)}"
            f" recarga={len(los_del_telefono(despues_de_recargar.get('canales') or [])) == 2}"
            f" quitar={len(de_telefono_tras_quitar) == 1}"
            f" promueve={bool(de_telefono_tras_quitar and de_telefono_tras_quitar[0].get('principal') is True)}"
            f" recarga2={despues_de_recargar_2.get('cuantos_canales') == 3}"
            f" aislamiento404={recorrido.get('aislamiento')}"
        )
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
        huella_despues = la_huella_de_un_fichero(LA_BASE_DEL_AGRICULTOR)
        print(f"\n  la base del agricultor, después: {huella_despues}")
        print(
            "  [{}] y su huella NO ha cambiado".format(
                "OK   " if huella_despues == huella_antes else "FALLO"
            )
        )


if __name__ == "__main__":
    raise SystemExit(main())
