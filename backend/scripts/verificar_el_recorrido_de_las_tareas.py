"""El recorrido de «Lo que hay que hacer» (Entrega 3), **andado de verdad**: servidor aislado, navegador y capturas.

POR QUÉ EXISTE. La Entrega 3 dice que un contacto tiene **próximas acciones** —lo que queda por hacer con él— y que
hay una lista que cruza fichas, con filtros por vencimiento, que se puede **enlazar y recargar**. Las pruebas de
servidor (`tests/test_las_tareas_de_un_contacto.py`) comprueban las puertas (`POST /api/contactos/<id>/tareas`,
`GET/PUT /api/tareas`, `.../completar`, `.../cancelar`) y las de JavaScript comprueban que el componente pinta lo que
le llega. **Ninguna de las dos anda el camino**, y el camino tiene tramos que solo se ven andando:

  · **El alta rápida en la ficha** (`#tarea-titulo`, `#tarea-fecha` —que es un `date` de verdad—,
    `#tarea-responsable` y el botón `tarea-nueva`), que es como se apunta lo que hay que hacer.
  · **Que lo tecleado entre y se quede.** En la pantalla de los canales (Entrega 2) unos campos **no aceptaban
    tecleo** y eso solo se descubrió midiendo. Aquí se mide campo por campo, con el teclado del navegador, y se
    dice **con qué manera** ha entrado el texto en cada uno: no vale «lo escribí» si en realidad se puso por
    JavaScript.
  · **Que una fecha vencida deje la tarea pendiente y marcada** —el encargo lo dice con estas palabras:
    *«la fecha vencida no transforma automáticamente una tarea en cancelada»*— y que **se pueda completar** igual.
  · **Que cancelar no borre**: la tarea cancelada sigue ahí, con quién la canceló.
  · **Los filtros de la lista** (`tareas-ver` con `data-vencimiento`), que tienen que estar **en la dirección**
    (`#/tareas?vencimiento=…`), marcados, y **seguir puestos después de recargar**.
  · **El aislamiento**: con una segunda explotación de verdad, ni se ven las tareas de la primera ni se pueden
    cerrar (404).

## Lo que monta, y por qué así

  · **Su propio servidor**, en el puerto 8363 (nunca 8000 ni 8029, que son los de David) y con una **base temporal**
    (`CUEDIGITAL_DATABASE_URL`). Nunca la base del agricultor, y se comprueba su huella **antes y después**.
  · **El escenario prestado**: `datos_representativos.preparar()`, el mismo que usan los demás guiones. De ahí salen
    la explotación del volumen **y la ajena**, que es la que hace falta para la comprobación de aislamiento.
  · **Un contacto creado por la puerta de verdad** (`POST /api/contactos`).
  · **Un navegador de verdad** (`NavegadorDeVerdad`, CDP): abre la ficha, **teclea**, pulsa y **lee el DOM** —no una
    captura de la API— para comprobar el bloque, el alta, el cierre, la cancelación, la lista, los filtros y la
    recarga.

## Las dos vueltas, y por qué

El recorrido se anda **dos veces**, cada una con **su propia explotación** (una cuenta nueva, en la misma base). Las
dos vueltas imprimen **la misma línea `HUELLA`** con las mismas comprobaciones en forma de `True`/`False`: eso es lo
que demuestra que lo medido **no es casualidad de una tirada**. Si una vuelta sale distinta, se dice: una
comprobación que unas veces pasa y otras no **no está comprobada**.

## Lo que NO hace

**No arregla nada.** Este guion solo mide y cuenta. Cuando un paso no se puede dar, **se dice con el detalle exacto y
no se simula**: un recorrido que se salta el paso que falla es un recorrido que miente.

Uso:  python scripts/verificar_el_recorrido_de_las_tareas.py [puerto] [carpeta-de-capturas]
"""

from __future__ import annotations

import base64
import datetime as dt
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
import urllib.parse
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

# **Los puertos de David no se tocan** (8000 y 8029). El de por defecto lo dijo el encargo: 8363.
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8363
CARPETA = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "docs" / "capturas"

# El contacto de esta prueba. El nombre **no puede casar con los veinte que crea `datos_representativos`**
# («Proveedor de la prueba NN S.L.»): si casara, el guion podría estar abriendo la ficha de otro.
NOMBRE = "Cooperativa de las Tareas de la Prueba"

# **Las seis tareas del recorrido, con su día y su final.** Están pensadas para que cada filtro de la lista tenga
# algo que enseñar y algo que dejar fuera: si todas cayeran en el mismo saco, un filtro roto no se notaría.
#
#   (título, días respecto a hoy —None es «sin fecha»—, responsable, qué se hace con ella)
LAS_TAREAS = (
    ("Llamar al del pienso", 0, "Ana Ruiz", "completar"),
    ("Pagar la factura del taller", -1, "Ana Ruiz", "vencida_y_completar"),
    ("Encargar las semillas", None, "Ana Ruiz", "cancelar"),
    ("Revisar el riego", 1, "Ana Ruiz", "dejar"),
    ("Preguntar por el abono", None, "Ana Ruiz", "dejar"),
    ("Llamar al veterinario", -1, "Ana Ruiz", "dejar"),
)

# Lo que se lee de la pantalla, con las palabras exactas del servidor (`app/textos.py`).
TITULO_DEL_BLOQUE = "Lo que hay que hacer"
TITULO_DE_LA_LISTA = "Lo que hay que hacer"
MARCA_VENCIDA = "Vencida"
HECHA_POR = "Hecha por"
CANCELADA_POR = "Cancelada por"
SIN_FECHA = "Sin fecha"
YA_HECHA = "Ya hecha"
YA_CANCELADA = "Cancelada"

# El nombre del usuario que hace el recorrido, tal y como lo pone `datos_representativos` al registrar la cuenta:
# es lo que tiene que salir en «Hecha por …» y en «Cancelada por …».
QUIEN = "Cuaderno de volumen"

COMPROBACIONES = 0
FALLOS = 0
PANTALLA: dict = {}
# Las capturas que se han guardado de verdad, para poder contarlas y enseñarlas en el resumen.
CAPTURAS: list[str] = []
# La vuelta que se está andando, para que los pasos se numeren dentro de su vuelta y no se confundan los de una
# con los de la otra: dos recorridos con los mismos números de paso no se pueden leer.
VUELTA_ACTUAL = 0


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
    delante = f"v{VUELTA_ACTUAL} " if VUELTA_ACTUAL else ""
    print(f"\n{delante}{numero}) {titulo}")


def decir(texto: str) -> None:
    print(f"       {texto}")


def como_texto(algo, cuanto: int = 900) -> str:
    """El JSON, en un renglón y sin pasarse: es lo que contesta el servidor y hay que verlo entero."""
    try:
        crudo = json.dumps(algo, ensure_ascii=False, default=str)
    except Exception:  # noqa: BLE001
        crudo = str(algo)
    return crudo if len(crudo) <= cuanto else crudo[:cuanto] + " …"


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
    except Exception as fallo:  # noqa: BLE001 - una puerta que no contesta también es un dato
        return 0, f"la petición no ha llegado: {fallo}"
    try:
        return codigo, json.loads(crudo)
    except Exception:  # noqa: BLE001 - lo que importa es el texto tal cual llegó
        return codigo, crudo


def la_puerta(token: str, metodo: str, camino: str, cuerpo: dict | None = None, *, que: str = ""):
    """Igual que `_puerta`, pero **lo cuenta**: qué se pidió y qué se contestó."""
    codigo, devuelto = _puerta(token, metodo, camino, cuerpo)
    if que:
        decir(f"se pide:   {metodo} {camino}")
        if cuerpo is not None:
            decir(f"se manda:  {como_texto(cuerpo)}")
        decir(f"contesta:  {codigo}  {como_texto(devuelto)}")
    return codigo, devuelto


# ---------------------------------------------------------------------------
# La dirección, leída como la lee el enrutador
# ---------------------------------------------------------------------------
#
# **Medido, y por eso no se escribe una dirección a mano**: la aplicación reescribe la dirección en cada pantalla
# que pinta (`apuntarLaDireccion`, en `app.js`) y le añade **el contexto** —la campaña y la finca
# (`elContextoDeLaDireccion`)—, así que la dirección de la lista de tareas no es `#/tareas?vencimiento=hoy` sino,
# medido, `#/tareas?campana=2026&finca=1&vencimiento=hoy`. Comprobar la cadena literal habría dado un fallo que no
# existe: lo que hay que comprobar es **el camino y el filtro**, y decir la dirección entera tal cual salió.


def el_camino_de_la_direccion(direccion: str) -> str:
    """El trozo de delante de la interrogación (`#/tareas`, `#/contactos/7`)."""
    return str(direccion or "").split("?", 1)[0]


def los_parametros_de_la_direccion(direccion: str) -> dict:
    """Los parámetros de la dirección, leídos como los lee el enrutador: **lo que no está, no está**."""
    texto = str(direccion or "")
    if "?" not in texto:
        return {}
    salida: dict[str, str] = {}
    for trozo in texto.split("?", 1)[1].split("&"):
        if not trozo:
            continue
        nombre, _, valor = trozo.partition("=")
        salida[urllib.parse.unquote_plus(nombre).strip().lower()] = urllib.parse.unquote_plus(valor)
    return salida


def lleva_el_filtro(direccion: str, vencimiento: str | None) -> bool:
    """¿La dirección lleva **ese** filtro de vencimiento? `None` es «sin filtro»."""
    return los_parametros_de_la_direccion(direccion).get("vencimiento", "") == (vencimiento or "")


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


def levantar_el_servidor(temporal: pathlib.Path) -> tuple[subprocess.Popen, pathlib.Path, str]:
    """Arranca uvicorn contra una base temporal y devuelve el proceso, la base y su bitácora."""
    base = temporal / f"cd-tareas-{os.getpid()}.db"
    bitacora = temporal / "servidor.log"
    entorno = dict(os.environ)
    # **La base es la de la prueba**, nunca la del agricultor. Y en UTF-8, que si no la consola de Windows se
    # atraganta con las tildes de los textos.
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
    return proceso, base, str(bitacora)


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


def lo_que_ha_quedado_vivo() -> list[str]:
    """**Lo que este guion ha dejado vivo, si ha dejado algo.** Se pregunta a Windows por la línea de órdenes de
    los procesos y se buscan las tres marcas de esta prueba: la carpeta temporal, el perfil del navegador y el
    uvicorn del puerto. Si no se puede preguntar, se dice: una limpieza que no se comprueba no está hecha.
    """
    consulta = (
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -ne $null -and "
        "( $_.CommandLine -like '*cd-tareas-*' -or $_.CommandLine -like '*cuedigital-cdp-*' -or "
        "( $_.CommandLine -like '*uvicorn*' -and $_.CommandLine -like '*--port %d*' ) ) } | "
        "Where-Object { @('python.exe','pythonw.exe','chrome.exe','msedge.exe','node.exe') -contains $_.Name } | "
        "ForEach-Object { \"$($_.ProcessId) $($_.Name) $($_.CommandLine.Substring(0, [Math]::Min(160, $_.CommandLine.Length)))\" }"
        % PUERTO
    )
    try:
        salida = subprocess.run(  # noqa: S603
            ["powershell", "-NoProfile", "-Command", consulta],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as fallo:  # noqa: BLE001
        return [f"(no se ha podido comprobar: {fallo})"]
    if salida.returncode != 0:
        return [f"(no se ha podido comprobar: {salida.stderr.strip()[:200]})"]
    return [renglon.strip() for renglon in salida.stdout.splitlines() if renglon.strip()]


# ---------------------------------------------------------------------------
# Lo que se lee de la pantalla
# ---------------------------------------------------------------------------

# **Se lee el DOM, no una captura.** El bloque de las tareas es un `h2` con su título y, debajo, la lista
# `ul.lista-de-tareas`, con un `li` por tarea: el primer `<strong>` es el título, y si hay un segundo `<strong>`
# con «Vencida», es que está vencida. El alta rápida son tres controles por `id` y un botón por `data-accion`.
LEER_LA_FICHA = (
    """
(() => {
  const p = document.querySelector('#pantalla');
  if (!p) return { hay_pantalla: false };
  const texto = (n) => (n ? n.textContent.replace(/\\s+/g, ' ').trim() : '');
  const TITULO = @TITULO@, VENCIDA = @VENCIDA@;
  const secciones = [...p.querySelectorAll('h2')].map(texto);
  const lista = p.querySelector('ul.lista-de-tareas');
  const tareas = lista
    ? [...lista.querySelectorAll('li')].map((li) => {
        const strongs = [...li.querySelectorAll('strong')].map(texto);
        const acciones = [...li.querySelectorAll('[data-accion]')].map((b) => ({
          accion: b.dataset.accion,
          tarea: b.dataset.tarea === undefined ? null : b.dataset.tarea,
          id: b.dataset.id === undefined ? null : b.dataset.id,
        }));
        const clon = li.cloneNode(true);
        [...clon.querySelectorAll('strong')].forEach((s) => s.remove());
        [...clon.querySelectorAll('button')].forEach((b) => b.remove());
        return {
          texto: texto(li),
          titulo: strongs.length ? strongs[0] : '',
          strongs: strongs,
          vencida_marcada: strongs.indexOf(VENCIDA) > 0,
          sin_botones: acciones.length === 0,
          acciones: acciones,
          resto: clon.textContent.replace(/\\s+/g, ' ').trim(),
        };
      })
    : [];
  const campo = (id) => {
    const el = document.getElementById(id);
    if (!el) return { hay: false };
    return {
      hay: true,
      tipo: el.type,
      valor: el.value,
      solo_lectura: el.readOnly,
      deshabilitado: el.disabled,
      visible: el.checkVisibility({ checkVisibilityCSS: true }),
      tiene_el_foco: document.activeElement === el,
    };
  };
  return {
    hay_pantalla: true,
    direccion: window.location.hash,
    titulo: texto(p.querySelector('h1')),
    secciones: secciones,
    hay_bloque: secciones.indexOf(TITULO) >= 0,
    hay_lista: Boolean(lista),
    tareas: tareas,
    cuantas: tareas.length,
    alta: {
      titulo: campo('tarea-titulo'),
      fecha: campo('tarea-fecha'),
      responsable: campo('tarea-responsable'),
      hay_boton: Boolean(p.querySelector('[data-accion="tarea-nueva"]')),
    },
    error: texto(p.querySelector('.aviso-error') || p.querySelector('.aviso')),
    nodos: p.querySelectorAll('*').length,
    texto: p.innerText.replace(/\\s+/g, ' ').trim(),
  };
})()
"""
    .replace("@TITULO@", json.dumps(TITULO_DEL_BLOQUE))
    .replace("@VENCIDA@", json.dumps(MARCA_VENCIDA))
)

# **La lista de `#/tareas`.** La tabla se marca con `data-tabla="tareas"`. La primera celda lleva el título y, si
# está vencida, un `<strong>Vencida</strong>` al lado: se separan los dos para poder comprobar la marca sin
# confundirla con el texto. Los filtros son botones `tareas-ver`; **el elegido es el que NO lleva `boton-claro`**
# (el componente pinta con la clase apagada los que no están puestos), y el de «todas» **no lleva el `data-`
# atributo**, porque un valor vacío no se escribe (`datosDelBoton`).
LEER_LA_LISTA = (
    """
(() => {
  const p = document.querySelector('#pantalla');
  if (!p) return { hay_pantalla: false };
  const texto = (n) => (n ? n.textContent.replace(/\\s+/g, ' ').trim() : '');
  const VENCIDA = @VENCIDA@;
  const tabla = p.querySelector('[data-tabla="tareas"]');
  const filas = tabla
    ? [...tabla.querySelectorAll('tbody tr')].map((tr) => {
        const celdas = [...tr.querySelectorAll('td')];
        let titulo = '', vencida = false;
        if (celdas[0]) {
          const clon = celdas[0].cloneNode(true);
          const strongs = [...clon.querySelectorAll('strong')];
          vencida = strongs.some((s) => s.textContent.trim() === VENCIDA);
          strongs.forEach((s) => s.remove());
          titulo = clon.textContent.replace(/\\s+/g, ' ').trim();
        }
        return {
          titulo: titulo,
          vencida_marcada: vencida,
          fecha: celdas[1] ? texto(celdas[1]) : '',
          responsable: celdas[2] ? texto(celdas[2]) : '',
          con_quien: celdas[3] ? texto(celdas[3]) : '',
          enlace_ficha: celdas[3] && celdas[3].querySelector('a')
            ? celdas[3].querySelector('a').getAttribute('href') : null,
          cierre: celdas[4] ? texto(celdas[4]) : '',
          acciones: [...tr.querySelectorAll('[data-accion]')].map((b) => ({
            accion: b.dataset.accion,
            tarea: b.dataset.tarea === undefined ? null : b.dataset.tarea,
            id: b.dataset.id === undefined ? null : b.dataset.id,
          })),
        };
      })
    : [];
  const filtros = [...p.querySelectorAll('[data-accion="tareas-ver"]')].map((b) => ({
    vencimiento: b.dataset.vencimiento === undefined ? null : b.dataset.vencimiento,
    texto: texto(b),
    clase: b.className,
    marcado: b.className.split(/\\s+/).indexOf('boton-claro') < 0,
  }));
  return {
    hay_pantalla: true,
    direccion: window.location.hash,
    titulo: texto(p.querySelector('h1')),
    hay_tabla: Boolean(tabla),
    filas: filas,
    cuantas: filas.length,
    filtros: filtros,
    vacio: texto(p.querySelector('p.pista')),
    error: texto(p.querySelector('.aviso-error') || p.querySelector('.aviso')),
    nodos: p.querySelectorAll('*').length,
    texto: p.innerText.replace(/\\s+/g, ' ').trim(),
  };
})()
"""
    .replace("@VENCIDA@", json.dumps(MARCA_VENCIDA))
)

# **Los errores de la página, apuntados desde el primer momento.** Sin esto, un fallo de JavaScript dentro de la
# ficha se lee como «no hay tareas» y se confunde con que el bloque no esté pintado.
VIGILAR_LOS_ERRORES = """
window.__los_errores = [];
window.addEventListener('error', (e) => window.__los_errores.push('error: ' + String(e.message)));
window.addEventListener('unhandledrejection', (e) => {
  const r = e.reason;
  window.__los_errores.push('promesa rechazada: ' + String((r && r.message) || r));
});
// **Y todas las direcciones por las que pasa la página** (medido, 14/10/2026): un filtro que se escribe en la
// dirección y se borra acto seguido no se puede ver leyendo la dirección al final; hay que apuntar la historia.
window.__las_direcciones = [window.location.hash];
window.addEventListener('hashchange', () => {
  const ultima = window.__las_direcciones[window.__las_direcciones.length - 1];
  if (ultima !== window.location.hash) window.__las_direcciones.push(window.location.hash);
});
"""

# **Los textos de la lista, vistos desde dentro.** Lo que llega a la pantalla es lo que hay guardado en el móvil
# (`cuedigital.interfaz`), así que se mira **eso** y no una idea de lo que debería ser. Y se mira también lo que
# contesta la puerta, para poder decir de dónde sale.
LA_SONDA_DE_LOS_TEXTOS = """
(async () => {
  const de = (interfaz) => {
    if (!interfaz) return { hay: false };
    const suyo = interfaz.tareas;
    if (suyo === undefined) return { hay: false };
    const esLista = Array.isArray(suyo);
    return {
      hay: true,
      es_lista: esLista,
      tipo: esLista ? 'array' : typeof suyo,
      claves_o_elementos: esLista
        ? suyo.slice(0, 8)
        : (suyo && typeof suyo === 'object' ? Object.keys(suyo).slice(0, 8) : null),
      sabe_decir_el_titulo: esLista ? suyo.indexOf('titulo') >= 0 : Boolean(suyo && suyo.titulo),
      contactos_es_objeto: Boolean(interfaz.contactos && typeof interfaz.contactos === 'object'
        && !Array.isArray(interfaz.contactos)),
      trabajos_es_lista: Array.isArray(interfaz.trabajos),
    };
  };
  let guardado = null;
  try { guardado = JSON.parse(window.localStorage.getItem('cuedigital.interfaz') || 'null'); } catch (e) { guardado = null; }
  let deLaPuerta = null;
  try { deLaPuerta = await (await fetch('/api/interfaz')).json(); } catch (e) { deLaPuerta = null; }
  return { en_el_movil: de(guardado), de_la_puerta: de(deLaPuerta) };
})()
"""


def leer_la_ficha(nav) -> dict:
    global PANTALLA
    PANTALLA = nav.evaluar(LEER_LA_FICHA) or {"hay_pantalla": False}
    return PANTALLA


def leer_la_lista(nav) -> dict:
    return nav.evaluar(LEER_LA_LISTA) or {"hay_pantalla": False}


def la_tarea_por_su_titulo(lo_que_hay: dict, titulo: str) -> dict | None:
    """**La tarea, buscada por su título y no por su posición.** Es la lección que dejó escrita la prueba de
    servidor: dar por hecho que la primera de la lista es la que uno acaba de apuntar llevó a cerrar la tarea
    equivocada y a echarle la culpa a un filtro que funcionaba."""
    for tarea in lo_que_hay.get("tareas") or []:
        if tarea.get("titulo") == titulo:
            return tarea
    return None


def decir_la_ficha(lo_que_hay: dict) -> None:
    decir(f"en pantalla: {lo_que_hay.get('direccion')!r}  título {lo_que_hay.get('titulo')!r}")
    decir(
        f"secciones: {lo_que_hay.get('secciones')}   nodos: {lo_que_hay.get('nodos')}   "
        f"error en pantalla: {lo_que_hay.get('error')!r}"
    )
    decir(
        f"bloque «{TITULO_DEL_BLOQUE}»: {lo_que_hay.get('hay_bloque')}   "
        f"lista: {lo_que_hay.get('hay_lista')}   tareas: {lo_que_hay.get('cuantas')}"
    )
    for tarea in lo_que_hay.get("tareas") or []:
        decir(
            f"             {tarea['titulo']!r} vencida={tarea['vencida_marcada']} "
            f"cerrada={tarea['sin_botones']} acciones={[a['accion'] for a in tarea['acciones']]}"
            f"  {tarea['resto']!r}"
        )
    alta = lo_que_hay.get("alta") or {}
    decir(
        "alta rápida: "
        f"título={como_texto(alta.get('titulo'))} fecha={como_texto(alta.get('fecha'))} "
        f"responsable={como_texto(alta.get('responsable'))} botón={alta.get('hay_boton')}"
    )


def decir_lo_que_se_ve(lo_que_hay: dict, cuanto: int = 1200) -> None:
    """El texto de la pantalla, tal cual: es «lo que se vio», y sin él no se puede juzgar un fallo."""
    texto = (lo_que_hay.get("texto") or "").strip()
    decir(f"lo que se ve: {texto[:cuanto]!r}")


def guardar_captura(nav, destino: pathlib.Path) -> str:
    """Una captura de verdad, con su tamaño medido del propio PNG.

    **Y se apunta en `CAPTURAS`**, porque una captura que se guarda y no se cuenta es una captura que el informe
    no puede enseñar: el resumen decía «capturas: 0» con seis ficheros en el disco.
    """
    crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
    destino.write_bytes(crudo)
    ancho, alto = struct.unpack(">II", crudo[16:24])
    decir(f"captura: {destino}  ({ancho}x{alto}, {len(crudo)} bytes)")
    CAPTURAS.append(str(destino))
    return str(destino)


# ---------------------------------------------------------------------------
# El tecleo, medido campo por campo
# ---------------------------------------------------------------------------
#
# **Esto es el corazón del guion.** En la pantalla de los canales unos campos no aceptaban tecleo y solo se
# descubrió midiendo, así que aquí no se da nada por hecho: se prueba **manera por manera** y se dice **con cuál ha
# entrado** el texto. Y la diferencia importa:
#
#   · `insertText` y las teclas son **el teclado del navegador**: es lo que hace el agricultor cuando escribe.
#   · `maquinaria_del_navegador` es `document.execCommand('insertText')`: lo hace el navegador, pero **no es el
#     teclado del protocolo**. Se cuenta aparte y **no se llama «tecleado»**.
#   · `javascript` es poner el valor a mano (`.value = …`). **No es escribir**: se usa solo para poder seguir el
#     recorrido cuando no ha entrado de ninguna otra forma, y se dice en voz alta.

LAS_MANERAS = ("insertText", "keyDown", "rawKeyDown")

# Cómo se llama cada manera en el informe, para no confundir «clic» con «foco»: el clic es un ratón de verdad en el
# centro del campo (lo que hace un dedo), y el foco es pedirlo por JavaScript (que no siempre basta).
NOMBRE_DE_LA_MANERA = {
    "insertText": "insertText",
    "keyDown": "keyDown con texto",
    "rawKeyDown": "rawKeyDown + char",
}

LAS_TECLAS_RARAS = {
    " ": (32, "Space"),
    "-": (189, "Minus"),
    ".": (190, "Period"),
    "/": (191, "Slash"),
    ",": (188, "Comma"),
}


def _la_tecla(caracter: str) -> tuple[int, str]:
    """El código de tecla y el `code` de un carácter, que es lo que hace que llegue como una tecla de verdad."""
    if caracter.isdigit():
        return 48 + int(caracter), f"Digit{caracter}"
    if caracter.isascii() and caracter.isalpha():
        return ord(caracter.upper()), f"Key{caracter.upper()}"
    return LAS_TECLAS_RARAS.get(caracter, (0, ""))


def _limpiar_el_campo(nav, campo: str) -> None:
    """Vaciar el campo **no es teclear**: es dejar la mesa limpia para poder medir la manera siguiente.

    **Y se le quita el foco (`blur`) además de vaciarlo, que es lo que costó una vuelta** (medido, 14/10/2026):
    en un campo `date`, vaciarlo y volver a enfocarlo **no reinicia el trozo que se está editando**, así que los
    dígitos del día siguiente entran en el año y el campo se queda vacío. La combinación que sí funciona es
    `value = ''` → `blur()` → `focus()`; con eso, teclear `13102026` deja `2026-10-13`, y sin el `blur` deja `''`.
    """
    nav.evaluar(
        "(() => { const el = document.getElementById(%s); if (el) { el.value = ''; el.blur(); }"
        " return true; })()" % json.dumps(campo)
    )


def _leer_el_campo(nav, campo: str):
    return nav.evaluar(
        "(() => { const el = document.getElementById(%s); return el ? el.value : null; })()"
        % json.dumps(campo)
    )


def _enfocar_el_campo(nav, campo: str, *, con_clic: bool):
    """Deja el campo listo para recibir teclas. Devuelve si el navegador dice que ese campo tiene el foco.

    **Se prueba primero el clic de verdad** (el ratón, en el centro del campo), que es lo que hace el agricultor, y
    si no se puede —porque el campo no se ve— se pide el foco por JavaScript. La diferencia se apunta, porque un
    campo que necesita el clic y otro que no son dos campos distintos.
    """
    if con_clic:
        try:
            nav.pulsar("#" + campo)
        except RuntimeError as fallo:
            decir(f"       (no se ha podido pulsar #{campo}: {fallo})")
    return nav.evaluar(
        "(() => { const el = document.getElementById(%s); if (!el) return null; el.focus();"
        " return document.activeElement === el; })()" % json.dumps(campo)
    )


def _teclear_con(nav, campo: str, texto: str, manera: str) -> None:
    """Manda el texto **como lo manda el teclado del navegador**, con la manera que se le pida."""
    if manera == "insertText":
        nav.orden("Input.insertText", {"text": texto})
        return
    for caracter in texto:
        codigo, code = _la_tecla(caracter)
        comun = {
            "key": caracter,
            "code": code,
            "windowsVirtualKeyCode": codigo,
            "nativeVirtualKeyCode": codigo,
        }
        if manera == "keyDown":
            nav.orden(
                "Input.dispatchKeyEvent",
                {"type": "keyDown", "text": caracter, "unmodifiedText": caracter, **comun},
            )
            nav.orden("Input.dispatchKeyEvent", {"type": "keyUp", **comun})
        else:
            # `rawKeyDown` + `char` + `keyUp`: es lo que hace un teclado de verdad, y es la única forma en la que
            # un campo que no es de texto (el `date`, que edita por trozos) ve las teclas.
            nav.orden("Input.dispatchKeyEvent", {"type": "rawKeyDown", **comun})
            nav.orden(
                "Input.dispatchKeyEvent",
                {"type": "char", "text": caracter, "unmodifiedText": caracter, **comun},
            )
            nav.orden("Input.dispatchKeyEvent", {"type": "keyUp", **comun})


def _la_maquinaria_del_navegador(nav, campo: str, texto: str) -> dict:
    """`document.execCommand('insertText')` sobre el campo que tiene el foco: la maquinaria de edición **del
    navegador**. Si esto tampoco escribe, el que no acepta texto es **el campo**, y eso no es cosa del teclado del
    protocolo: es la pantalla."""
    return nav.evaluar(
        "(() => { const el = document.getElementById(%s); if (!el) return { hay: false };"
        " el.focus(); let vale = null;"
        " try { vale = document.execCommand('insertText', false, %s); }"
        " catch (fallo) { vale = 'reventó: ' + fallo.message; }"
        " return { hay: true, lo_ha_aceptado: vale, valor: el.value,"
        " solo_lectura: el.readOnly, deshabilitado: el.disabled,"
        " tiene_el_foco: document.activeElement === el }; })()"
        % (json.dumps(campo), json.dumps(texto))
    )


def medir_el_tecleo(nav, campo: str, valor: str) -> tuple[str | None, list[dict]]:
    """**Teclea un texto y mide por dónde ha entrado.** Devuelve `(manera, intentos)`.

    `manera` es la que ha funcionado —`"clic+insertText"`, `"foco+rawKeyDown + char"`, …— o `None` si el texto no
    ha entrado de ninguna forma de teclado. Se prueban dos vías de foco (el clic de verdad y el foco pedido) por
    cada manera, porque en un navegador sin ventana el foco de la página se pierde con las navegaciones y
    `Input.insertText` **no da error: simplemente no escribe**.
    """
    intentos: list[dict] = []
    for con_clic in (True, False):
        for manera in LAS_MANERAS:
            _limpiar_el_campo(nav, campo)
            enfocado = _enfocar_el_campo(nav, campo, con_clic=con_clic)
            _teclear_con(nav, campo, valor, manera)
            leido = _leer_el_campo(nav, campo)
            etiqueta = f"{'clic+' if con_clic else 'foco+'}{NOMBRE_DE_LA_MANERA[manera]}"
            intentos.append(
                {"manera": etiqueta, "valor": leido, "llego": leido == valor, "con_foco": enfocado}
            )
            if leido == valor:
                return etiqueta, intentos
    return None, intentos


# Cómo se escriben los dígitos de un día en cada uno de los tres órdenes que puede pedir un campo `date`.
LOS_ORDENES_DE_LA_FECHA = {
    "día-mes-año": lambda fecha: f"{fecha.day:02d}{fecha.month:02d}{fecha.year:04d}",
    "mes-día-año": lambda fecha: f"{fecha.month:02d}{fecha.day:02d}{fecha.year:04d}",
    "año-mes-día": lambda fecha: f"{fecha.year:04d}{fecha.month:02d}{fecha.day:02d}",
}


def los_digitos_de_una_fecha(fecha: dt.date, orden: str) -> str:
    """Los dígitos que hay que teclear para un día, en el orden que pida el campo."""
    return LOS_ORDENES_DE_LA_FECHA[orden](fecha)


def medir_el_tecleo_de_una_fecha(nav, campo: str, fecha: dt.date) -> tuple[str | None, str | None, list[dict]]:
    """**¿Se puede teclear un día en el campo `date`, y en qué orden pide los dígitos?**

    El campo `date` no es un campo de texto: el navegador lo pinta por **trozos** (día, mes, año) y el orden en el
    que los pide depende del idioma del navegador. Así que no vale con suponerlo: se mide.

    **Y se mide con una fecha que no se puede confundir** (25/12/2026): el 25 no cabe en un mes, así que los dígitos
    `25122026` **solo** encajan en un campo que pida día-mes-año, `12252026` solo en uno que pida mes-día-año, y
    `20261225` solo en uno que pida año-mes-día. Con el día de verdad no se puede averiguar —el 10 y el 12 valen
    para las dos casillas, y entonces el orden que se apunte puede ser el equivocado—, y esa trampa ya se ha comido
    una vuelta en esta casa.

    Después **se confirma con el día de verdad**, y si la confirmación no sale se dice que no se puede teclear.

    **Lo que se ha medido y por qué el código es así** (sonda aparte, 14/10/2026):
      · en este navegador el campo pide los dígitos en orden **día-mes-año**;
      · `.focus()` **no basta**: el campo necesita un **clic de verdad** para entrar en modo edición (con el foco
        pedido por JavaScript, `Input.insertText` y las teclas no escriben nada, y no dan error);
      · `Input.insertText` **no escribe** en un `date` (no es un campo de texto para el navegador), y
        `rawKeyDown` + `char` tampoco: lo que funciona es `keyDown` **con el texto** y tras un clic;
      · pulsar el campo **abre el calendario del navegador**, y eso **no estorba** para nada de lo que viene
        después (medido: se apuntaron tres tareas con el calendario abierto).
      · **`Escape` NO se pulsa aquí**: en esta aplicación Escape es «cierra lo que esté abierto» y pulsa el primer
        botón de cierre que encuentre (`LO_QUE_CIERRA_ESCAPE`, en `app.js`), así que en la ficha **se sale de la
        pantalla** y los campos desaparecen. Costó una sonda verlo.

    Devuelve `(manera, orden, intentos)`; `manera` y `orden` son `None` si el campo no acepta tecleo.
    """
    intentos: list[dict] = []
    # La sonda: una fecha en la que el día no cabe en un mes, así que cada orden solo puede dar UN resultado.
    la_sonda = dt.date(2026, 12, 25)
    las_ordenes = (
        ("día-mes-año", "25122026"),
        ("mes-día-año", "12252026"),
        ("año-mes-día", "20261225"),
    )

    def un_intento(con_clic: bool, manera: str, nombre_orden: str, digitos: str) -> tuple[str, str | None, bool]:
        etiqueta = f"{'clic+' if con_clic else 'foco+'}{NOMBRE_DE_LA_MANERA[manera]}"
        _limpiar_el_campo(nav, campo)
        enfocado = _enfocar_el_campo(nav, campo, con_clic=con_clic)
        _teclear_con(nav, campo, digitos, manera)
        return etiqueta, _leer_el_campo(nav, campo), bool(enfocado)

    # **El foco primero** y el clic después: el clic abre el calendario, y aunque está medido que no estorba, no
    # hace falta abrirlo para averiguar el orden si el foco bastara.
    for con_clic in (False, True):
        for manera in LAS_MANERAS:
            for nombre_orden, digitos in las_ordenes:
                etiqueta, leido, enfocado = un_intento(con_clic, manera, nombre_orden, digitos)
                intentos.append(
                    {
                        "manera": etiqueta,
                        "orden": nombre_orden,
                        "digitos": digitos,
                        "valor": leido,
                        "llego": leido == la_sonda.isoformat(),
                        "con_foco": enfocado,
                        "sonda": True,
                    }
                )
                if leido == la_sonda.isoformat():
                    # El orden está averiguado. Ahora **se confirma con el día de verdad**, que es el que hace
                    # falta de verdad: si esto fallara, el orden apuntado no serviría para el recorrido.
                    los_digitos = los_digitos_de_una_fecha(fecha, nombre_orden)
                    etiqueta, leido, enfocado = un_intento(con_clic, manera, nombre_orden, los_digitos)
                    intentos.append(
                        {
                            "manera": etiqueta,
                            "orden": nombre_orden,
                            "digitos": los_digitos,
                            "valor": leido,
                            "llego": leido == fecha.isoformat(),
                            "con_foco": enfocado,
                            "confirmacion": True,
                        }
                    )
                    if leido == fecha.isoformat():
                        return etiqueta, nombre_orden, intentos
                    return None, None, intentos
    return None, None, intentos


def teclear_por_la_manera_que_ya_funciona(nav, campo: str, valor: str, manera: str, *, es_fecha: bool = False) -> str:
    """Vuelve a teclear con la manera que ya se midió, y devuelve lo que ha quedado en el campo.

    **No se vuelve a barrer** todas las maneras en cada tarea: la primera tarea es la que mide (y se cuenta), y las
    demás usan lo medido. Si aun así no entrara, se dice y se sigue —con el valor puesto por JavaScript— para que
    el resto del recorrido se pueda medir.
    """
    con_clic = manera.startswith("clic+")
    _limpiar_el_campo(nav, campo)
    _enfocar_el_campo(nav, campo, con_clic=con_clic)
    for nombre, clave in NOMBRE_DE_LA_MANERA.items():
        if manera.endswith(clave):
            _teclear_con(nav, campo, valor, nombre)
            break
    leido = _leer_el_campo(nav, campo)
    if leido == valor:
        return "teclado"
    # Último recurso, y **dicho**: se pone el valor por JavaScript para poder seguir midiendo lo demás.
    nav.evaluar(
        "(() => { const el = document.getElementById(%s); if (el) el.value = %s; return true; })()"
        % (json.dumps(campo), json.dumps(valor))
    )
    decir(
        f"       NO HA ENTRADO por la manera medida ({manera!r}) en #{campo}: "
        f"se esperaba {valor!r} y se ha leído {leido!r}. Se pone por JavaScript para poder seguir."
    )
    return "javascript"


# ---------------------------------------------------------------------------
# El recorrido de una vuelta
# ---------------------------------------------------------------------------


def el_contacto_por_su_puerta(token: str) -> int:
    """El contacto del encargo, por `POST /api/contactos` (basta el nombre, como dice el encargo)."""
    paso("2", "El contacto, por la puerta de verdad")
    codigo, ficha = la_puerta(token, "POST", "/api/contactos", {"nombre": NOMBRE}, que="sí")
    comprobar(codigo == 201, f"el contacto se da de alta ({codigo})")
    if codigo != 201:
        raise SystemExit("sin contacto no hay recorrido que andar")
    identificador = int(ficha["id"])
    decir(f"el contacto es el {identificador}")
    decir(
        f"y nace con {len(ficha.get('tareas') or [])} tarea(s) apuntada(s) "
        f"(tiene que ser 0: una ficha nueva no tiene nada pendiente)"
    )
    comprobar(
        len(ficha.get("tareas") or []) == 0,
        "la ficha recién creada no trae tareas (una lista vacía es «no hay nada», no «no me lo han mandado»)",
    )
    return identificador


def abrir_la_ficha(nav, contacto_id: int) -> dict:
    """Abre la ficha **por su dirección** (`#/contactos/<id>`), que es la que se puede recargar.

    Y antes, para contarlo, se pasa por la lista y se pulsa la fila —que es lo que hace el agricultor—: así se mide
    **qué dirección deja el botón**, que es un dato que importa para la recarga.
    """
    paso("3", "Abrir la ficha en un navegador de verdad")
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
        nav.esperar("document.querySelector('#pantalla h1') !== null", segundos=25)
        time.sleep(1.2)
        tras_el_boton = nav.evaluar("window.location.hash")
        decir(
            f"tras pulsar la fila de la lista, la dirección es {tras_el_boton!r} "
            "(y no `#/contactos`: el botón de abrir sí escribe la dirección de la ficha, con el contexto detrás)"
        )
        comprobar(
            el_camino_de_la_direccion(tras_el_boton) == f"#/contactos/{contacto_id}",
            f"el botón de abrir deja la ficha en su dirección ({tras_el_boton!r}; el camino es "
            f"{el_camino_de_la_direccion(tras_el_boton)!r} —la aplicación le añade la campaña y la finca, "
            f"medido: {como_texto(los_parametros_de_la_direccion(tras_el_boton))})",
        )
    else:
        decir("no hay fila que pulsar: se va a la dirección de la ficha, y se dice")
    # **Y ahora sí, en su dirección**, que es la que el encargo nombra y la que tiene que aguantar una recarga.
    nav.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos/{contacto_id}", esperar=3.0)
    nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
    time.sleep(1.0)
    return leer_la_ficha(nav)


def el_alta_de_una_tarea(
    nav, contacto_id: int, titulo: str, fecha: dt.date | None, responsable: str, medido: dict
) -> dict:
    """**Teclea de verdad los tres campos y apunta la tarea.** Devuelve lo medido, para el informe.

    La **primera** tarea de la vuelta es la que mide: se barren todas las maneras, campo por campo, y se cuenta con
    qué ha entrado cada uno. Las demás usan lo ya medido (que es lo que hace el recorrido rápido), y si aun así algo
    no entrara, **se dice** y se sigue con el valor puesto por JavaScript, para que lo demás se pueda medir igual.
    """
    dia = fecha.isoformat() if fecha is not None else ""
    decir(
        f"se teclea, campo por campo: #tarea-titulo={titulo!r} #tarea-fecha={dia!r} "
        f"#tarea-responsable={responsable!r}"
    )

    def un_campo_de_texto(cual: str, valor: str) -> None:
        """Un campo de texto: se mide la primera vez y después se usa lo medido."""
        if medido.get(cual) is None:
            manera, intentos = medir_el_tecleo(nav, cual, valor)
            medido[f"intentos_{cual}"] = intentos
            for intento in intentos:
                decir(
                    f"         probado {intento['manera']!r} en #{cual} → valor "
                    f"{intento['valor']!r} (el campo tenía el foco: {intento['con_foco']})"
                )
            if manera is None:
                decir(
                    f"       NO HA ENTRADO TECLEANDO en #{cual}: se han probado "
                    f"{[i['manera'] for i in intentos]} y ninguna ha escrito {valor!r}. "
                    "Se pone por JavaScript para poder seguir midiendo lo demás —y se dice."
                )
                manera = "javascript"
            else:
                decir(f"       #{cual}: ha entrado por {manera!r}")
            medido[cual] = manera
        if medido[cual] == "javascript":
            nav.evaluar(
                "(() => { const el = document.getElementById(%s); if (el) el.value = %s; return true; })()"
                % (json.dumps(cual), json.dumps(valor))
            )
            return
        como = teclear_por_la_manera_que_ya_funciona(nav, cual, valor, medido[cual])
        decir(f"       #{cual}: tecleado por {medido[cual]!r} → {como}")

    un_campo_de_texto("tarea-titulo", titulo)
    un_campo_de_texto("tarea-responsable", responsable)

    # --- el día (un campo `date`) ---
    if fecha is None:
        decir("       #tarea-fecha: se deja EN BLANCO a propósito (una tarea sin fecha es una tarea)")
        _limpiar_el_campo(nav, "tarea-fecha")
    else:
        if medido.get("fecha") is None:
            manera, orden, intentos = medir_el_tecleo_de_una_fecha(nav, "tarea-fecha", fecha)
            medido["intentos_fecha"] = intentos
            vistos: dict[str, dict] = {}
            for intento in intentos:
                vistos.setdefault(intento["manera"], intento)
            for clave, intento in vistos.items():
                decir(
                    f"         probado {clave!r} en #tarea-fecha, con la sonda 25/12/2026 y los dígitos en orden "
                    f"{intento['orden']!r} ({intento['digitos']}) → el campo quedó en {intento['valor']!r} "
                    f"(el campo tenía el foco: {intento['con_foco']})"
                )
            for intento in intentos:
                if intento.get("confirmacion"):
                    decir(
                        f"         y con el día de verdad, en orden {intento['orden']!r} "
                        f"({intento['digitos']}) → {intento['valor']!r} "
                        f"(se esperaba {fecha.isoformat()!r})"
                    )
            if manera is None:
                decir(
                    "       NO HA ENTRADO TECLEANDO en #tarea-fecha: se han probado "
                    f"{sorted({i['manera'] for i in intentos})} con los dígitos en las tres órdenes, y el campo "
                    f"no ha llegado a {fecha.isoformat()!r}. Se pone por JavaScript para poder seguir midiendo."
                )
                manera = "javascript"
                orden = None
            else:
                decir(f"       #tarea-fecha: ha entrado por {manera!r} con los dígitos en orden {orden!r}")
            medido["fecha"] = manera
            medido["orden_de_la_fecha"] = orden
        if medido["fecha"] == "javascript":
            nav.evaluar(
                "(() => { const el = document.getElementById('tarea-fecha');"
                " if (el) el.value = %s; return true; })()" % json.dumps(fecha.isoformat())
            )
        else:
            digitos = los_digitos_de_una_fecha(fecha, medido["orden_de_la_fecha"])
            como = teclear_por_la_manera_que_ya_funciona(nav, "tarea-fecha", digitos, medido["fecha"])
            decir(
                f"       #tarea-fecha: tecleado por {medido['fecha']!r} en orden "
                f"{medido['orden_de_la_fecha']!r} ({digitos}) → {como}"
            )
    time.sleep(0.3)
    # **Lo que ha quedado en los campos, leído del DOM.** Un tecleo que no llega es un paso que no se ha dado.
    puestos = nav.evaluar(
        "({ titulo: (document.getElementById('tarea-titulo') || {}).value,"
        " fecha: (document.getElementById('tarea-fecha') || {}).value,"
        " responsable: (document.getElementById('tarea-responsable') || {}).value,"
        " tipo_de_la_fecha: (document.getElementById('tarea-fecha') || {}).type })"
    )
    decir(f"lo que ha quedado en los campos, leído del DOM: {como_texto(puestos)}")
    return {"puestos": puestos, "dia": dia, "titulo": titulo, "responsable": responsable}


def el_recorrido_en_el_navegador(direccion: str, token: str, ajena: str, vuelta: int) -> dict:
    """La mitad que no se puede comprobar sin ojos: el alta, el cierre, la cancelación, la lista y los filtros."""
    resultado: dict = {"capturas": [], "vuelta": vuelta, "maneras": {}}
    CARPETA.mkdir(parents=True, exist_ok=True)
    hoy = dt.date.today()
    medido: dict = {}
    empezaron_las_capturas = len(CAPTURAS)

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
        # **El foco de la página, pedido a propósito.** Un navegador sin ventana arranca **sin foco** y entonces
        # `Input.insertText` no llega a ningún campo: no falla, simplemente no escribe. Se pide antes de teclear.
        nav.orden("Page.enable")
        nav.orden("Page.bringToFront")
        try:
            nav.orden("Emulation.setFocusEmulationEnabled", {"enabled": True})
            decir("se le pide el foco a la página (`Emulation.setFocusEmulationEnabled`), para poder teclear")
        except RuntimeError as fallo:
            decir(f"(este navegador no sabe dar el foco a la página: {fallo})")

        # ---- el contacto y la ficha -------------------------------------------------
        contacto_id = el_contacto_por_su_puerta(token)
        resultado["contacto_id"] = contacto_id
        ficha = abrir_la_ficha(nav, contacto_id)
        decir_la_ficha(ficha)
        guardar_captura(nav, CARPETA / f"tareas-v{vuelta}-ficha-recien-abierta.png")
        comprobar(bool(ficha.get("titulo")), f"la ficha se abre y trae su título ({ficha.get('titulo')!r})")
        comprobar(
            ficha.get("hay_bloque") is True,
            f"en la ficha sale el bloque «{TITULO_DEL_BLOQUE}»",
        )
        alta = ficha.get("alta") or {}
        comprobar(
            bool((alta.get("titulo") or {}).get("hay")),
            "y está el alta rápida (#tarea-titulo)",
        )
        comprobar(
            (alta.get("fecha") or {}).get("tipo") == "date",
            f"el campo del día es un `date` de verdad "
            f"(tipo {(alta.get('fecha') or {}).get('tipo')!r})",
        )
        comprobar(
            bool((alta.get("responsable") or {}).get("hay")),
            "y el del responsable (#tarea-responsable)",
        )
        comprobar(
            bool(alta.get("hay_boton")),
            "y el botón de apuntar (`tarea-nueva`)",
        )
        if not alta.get("hay_boton"):
            decir("sin alta rápida no hay recorrido: se para aquí, y se dice")
            resultado["sin_alta_rapida"] = True
            return resultado

        # ---- las seis tareas, tecleadas ---------------------------------------------
        paso("4", "Apuntar las tareas con el alta rápida, **tecleando de verdad** los tres campos")
        las_creadas: dict[str, int] = {}
        for numero, (titulo, dias, responsable, que_hacer) in enumerate(LAS_TAREAS, start=1):
            fecha = None if dias is None else hoy + dt.timedelta(days=dias)
            decir("")
            decir(
                f"  --- tarea {numero} de {len(LAS_TAREAS)}: {titulo!r} "
                f"({fecha.isoformat() if fecha else 'sin fecha'}, {que_hacer}) ---"
            )
            antes = len(leer_la_ficha(nav).get("tareas") or [])
            tecleado = el_alta_de_una_tarea(nav, contacto_id, titulo, fecha, responsable, medido)
            # **Y se comprueba que el texto ha ENTRADO en los tres campos**, que es lo que pide el encargo.
            puestos = tecleado.get("puestos") or {}
            comprobar(
                puestos.get("titulo") == titulo,
                f"el título ha entrado en #tarea-titulo ({puestos.get('titulo')!r} == {titulo!r})",
            )
            comprobar(
                puestos.get("fecha") == (fecha.isoformat() if fecha else ""),
                f"el día ha entrado en #tarea-fecha ({puestos.get('fecha')!r} == "
                f"{(fecha.isoformat() if fecha else '')!r})",
            )
            comprobar(
                puestos.get("responsable") == responsable,
                f"el responsable ha entrado en #tarea-responsable "
                f"({puestos.get('responsable')!r} == {responsable!r})",
            )
            nav.pulsar('[data-accion="tarea-nueva"]')
            nav.esperar(
                f"document.querySelectorAll('ul.lista-de-tareas li').length >= {antes + 1}",
                segundos=30,
            )
            time.sleep(0.8)
            despues = leer_la_ficha(nav)
            comprobar(
                len(despues.get("tareas") or []) == antes + 1,
                f"la tarea queda apuntada ({len(despues.get('tareas') or [])} en el bloque, "
                f"antes había {antes})",
            )
            _, ficha_ahora = _puerta(token, "GET", f"/api/contactos/{contacto_id}")
            suya = None
            for tarea in (ficha_ahora.get("tareas") or []):
                if tarea.get("titulo") == titulo:
                    suya = tarea
            comprobar(
                suya is not None,
                f"y la puerta de datos la cuenta ({como_texto(suya)})",
            )
            if suya is not None:
                las_creadas[titulo] = int(suya["id"])
                comprobar(
                    suya.get("fecha_prevista") == (fecha.isoformat() if fecha else None),
                    f"con el día que se tecleó ({suya.get('fecha_prevista')!r}, "
                    f"texto en pantalla {suya.get('fecha_texto')!r})",
                )
                comprobar(
                    suya.get("responsable") == responsable,
                    f"y el responsable que se tecleó ({suya.get('responsable')!r})",
                )
        resultado["tareas"] = las_creadas
        resultado["maneras"] = {
            "titulo": medido.get("titulo"),
            "fecha": medido.get("fecha"),
            "orden_de_la_fecha": medido.get("orden_de_la_fecha"),
            "responsable": medido.get("responsable"),
        }
        # **El veredicto del tecleo, junto y dicho.** Es la comprobación más importante del encargo.
        decir("")
        decir(
            "EL TECLEO, RESUMIDO: "
            f"#tarea-titulo → {medido.get('titulo')!r}; "
            f"#tarea-fecha → {medido.get('fecha')!r} (dígitos en orden {medido.get('orden_de_la_fecha')!r}); "
            f"#tarea-responsable → {medido.get('responsable')!r}"
        )
        resultado["tecleo"] = all(
            isinstance(medido.get(campo), str) and not str(medido.get(campo)).startswith("javascript")
            for campo in ("titulo", "fecha", "responsable")
        )
        comprobar(
            resultado["tecleo"],
            "los TRES campos aceptan tecleo de teclado (no se ha puesto ninguno por JavaScript): "
            f"título={medido.get('titulo')!r} fecha={medido.get('fecha')!r} "
            f"responsable={medido.get('responsable')!r}",
        )
        ficha = leer_la_ficha(nav)
        decir_la_ficha(ficha)
        decir_lo_que_se_ve(ficha)
        guardar_captura(nav, CARPETA / f"tareas-v{vuelta}-ficha-con-las-seis.png")

        # ---- lo de hoy, con su día y sin vencida -------------------------------------
        paso("5", "La tarea de hoy: en la lista, con su día, su responsable y SIN vencida")
        la_de_hoy = la_tarea_por_su_titulo(ficha, "Llamar al del pienso")
        comprobar(la_de_hoy is not None, "la tarea de hoy está en el bloque «Lo que hay que hacer»")
        if la_de_hoy is not None:
            decir(f"lo que se lee de esa fila: {como_texto(la_de_hoy)}")
            comprobar(
                hoy.strftime("%d/%m/%Y") in (la_de_hoy.get("resto") or ""),
                f"lleva su día dicho con palabras ({hoy.strftime('%d/%m/%Y')}): "
                f"{(la_de_hoy.get('resto') or '')!r}",
            )
            comprobar(
                "Ana Ruiz" in (la_de_hoy.get("resto") or ""),
                f"y su responsable: {(la_de_hoy.get('resto') or '')!r}",
            )
            comprobar(
                la_de_hoy.get("vencida_marcada") is False,
                "y NO está marcada como vencida (es de hoy)",
            )
        la_sin_fecha = la_tarea_por_su_titulo(ficha, "Preguntar por el abono")
        comprobar(la_sin_fecha is not None, "la tarea sin fecha también está en el bloque")
        if la_sin_fecha is not None:
            comprobar(
                SIN_FECHA in (la_sin_fecha.get("resto") or ""),
                f"y dice «{SIN_FECHA}» en vez de inventarse un día: {(la_sin_fecha.get('resto') or '')!r}",
            )
            comprobar(
                la_sin_fecha.get("vencida_marcada") is False,
                "y una tarea sin fecha no está vencida",
            )
        la_de_manana = la_tarea_por_su_titulo(ficha, "Revisar el riego")
        comprobar(
            la_de_manana is not None
            and (hoy + dt.timedelta(days=1)).strftime("%d/%m/%Y") in (la_de_manana.get("resto") or "")
            and la_de_manana.get("vencida_marcada") is False,
            "la de mañana lleva su día y tampoco está vencida "
            f"({(la_de_manana or {}).get('resto')!r})",
        )

        # ---- completarla, y que se quede hecha ---------------------------------------
        paso("6", "Completar la de hoy: tiene que quedar HECHA y decir QUIÉN la hizo, y seguir tras recargar")
        el_id = las_creadas.get("Llamar al del pienso")
        el_boton = f'[data-accion="tarea-completar"][data-tarea="{el_id}"]'
        comprobar(
            bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(el_boton)}))")),
            f"la tarea {el_id} trae su botón de completar en la ficha",
        )
        nav.pulsar(el_boton)
        nav.esperar(
            f"!document.querySelector('[data-accion=\"tarea-completar\"][data-tarea=\"{el_id}\"]')",
            segundos=25,
        )
        time.sleep(1.0)
        tras_completar = leer_la_ficha(nav)
        decir_la_ficha(tras_completar)
        resultado["tras_completar"] = tras_completar
        guardar_captura(nav, CARPETA / f"tareas-v{vuelta}-ficha-tras-completar.png")
        la_hecha = la_tarea_por_su_titulo(tras_completar, "Llamar al del pienso")
        comprobar(la_hecha is not None, "la tarea sigue en el bloque (hecha, no borrada)")
        if la_hecha is not None:
            comprobar(
                la_hecha.get("sin_botones") is True,
                f"y ya no lleva botones de cerrar (una tarea cerrada no se vuelve a cerrar): "
                f"{[a['accion'] for a in la_hecha['acciones']]}",
            )
            comprobar(
                HECHA_POR in (la_hecha.get("resto") or "") and QUIEN in (la_hecha.get("resto") or ""),
                f"y dice quién la hizo («{HECHA_POR} {QUIEN}»): {(la_hecha.get('resto') or '')!r}",
            )
            comprobar(
                la_hecha.get("vencida_marcada") is False,
                "y no está vencida (era de hoy)",
            )
        _, ficha_ahora = _puerta(token, "GET", f"/api/contactos/{contacto_id}")
        suya = next(
            (t for t in (ficha_ahora.get("tareas") or []) if t.get("id") == el_id), None
        )
        decir(f"la puerta de datos dice: {como_texto(suya)}")
        comprobar(
            (suya or {}).get("estado") == "hecha",
            f"el servidor la da por hecha ({(suya or {}).get('estado')!r})",
        )
        comprobar(
            (suya or {}).get("completada_por") == QUIEN and bool((suya or {}).get("completada_en")),
            f"y apunta quién y cuándo ({(suya or {}).get('completada_por')!r}, "
            f"{(suya or {}).get('completada_en')!r})",
        )
        # **La recarga entera**, que es lo que pide el encargo: el dato está guardado, no solo pintado.
        decir("se recarga la página entera (`Page.reload {ignoreCache: true}`)")
        nav.orden("Page.reload", {"ignoreCache": True})
        time.sleep(3.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
        time.sleep(1.0)
        recargada = leer_la_ficha(nav)
        decir_la_ficha(recargada)
        resultado["tras_recargar_la_hecha"] = recargada
        la_hecha_tras = la_tarea_por_su_titulo(recargada, "Llamar al del pienso")
        comprobar(
            la_hecha_tras is not None
            and la_hecha_tras.get("sin_botones") is True
            and HECHA_POR in (la_hecha_tras.get("resto") or "")
            and QUIEN in (la_hecha_tras.get("resto") or ""),
            "tras recargar sigue HECHA y sigue diciendo quién "
            f"({(la_hecha_tras or {}).get('resto')!r})",
        )

        # ---- la vencida -------------------------------------------------------------
        paso("7", "La vencida: una tarea de AYER tiene que salir marcada «Vencida» y SEGUIR PENDIENTE")
        la_vencida_id = las_creadas.get("Pagar la factura del taller")
        la_vencida = la_tarea_por_su_titulo(recargada, "Pagar la factura del taller")
        comprobar(la_vencida is not None, "la tarea de ayer está en el bloque")
        if la_vencida is not None:
            decir(f"lo que se lee de esa fila: {como_texto(la_vencida)}")
            comprobar(
                la_vencida.get("vencida_marcada") is True,
                f"está marcada «{MARCA_VENCIDA}» en la pantalla",
            )
            comprobar(
                la_vencida.get("sin_botones") is False
                and any(a["accion"] == "tarea-completar" for a in la_vencida["acciones"]),
                "y SIGUE PENDIENTE: trae su botón de completar "
                f"({[a['accion'] for a in la_vencida['acciones']]})",
            )
        _, ficha_ahora = _puerta(token, "GET", f"/api/contactos/{contacto_id}")
        suya = next((t for t in (ficha_ahora.get("tareas") or []) if t.get("id") == la_vencida_id), None)
        decir(f"la puerta de datos dice: {como_texto(suya)}")
        resultado["vencida_por_la_puerta"] = suya
        comprobar(
            (suya or {}).get("estado") == "pendiente" and (suya or {}).get("vencida") is True,
            "la fecha vencida NO la ha cancelado: sigue pendiente y vencida "
            f"(estado {(suya or {}).get('estado')!r}, vencida {(suya or {}).get('vencida')!r})",
        )
        # **Y se completa**, que es lo que pide el encargo: una vencida se puede hacer igual.
        el_boton = f'[data-accion="tarea-completar"][data-tarea="{la_vencida_id}"]'
        comprobar(
            bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(el_boton)}))")),
            "la vencida trae su botón de completar en la pantalla",
        )
        nav.pulsar(el_boton)
        nav.esperar(
            f"!document.querySelector('[data-accion=\"tarea-completar\"][data-tarea=\"{la_vencida_id}\"]')",
            segundos=25,
        )
        time.sleep(1.0)
        tras_completar_la_vencida = leer_la_ficha(nav)
        decir_la_ficha(tras_completar_la_vencida)
        resultado["tras_completar_la_vencida"] = tras_completar_la_vencida
        guardar_captura(nav, CARPETA / f"tareas-v{vuelta}-ficha-vencida-completada.png")
        _, ficha_ahora = _puerta(token, "GET", f"/api/contactos/{contacto_id}")
        suya = next((t for t in (ficha_ahora.get("tareas") or []) if t.get("id") == la_vencida_id), None)
        decir(f"y después de completarla: {como_texto(suya)}")
        resultado["vencida_completada_por_la_puerta"] = suya
        comprobar(
            (suya or {}).get("estado") == "hecha",
            f"una tarea vencida SE PUEDE completar ({(suya or {}).get('estado')!r})",
        )
        comprobar(
            la_tarea_por_su_titulo(tras_completar_la_vencida, "Pagar la factura del taller").get(
                "vencida_marcada"
            )
            is False,
            "y al quedar hecha deja de estar vencida (lo vencido es lo pendiente que se pasó, no lo hecho)",
        )

        # ---- la cancelada -----------------------------------------------------------
        paso("8", "Cancelar: tiene que quedar CANCELADA, decir QUIÉN la canceló y NO DESAPARECER")
        la_cancelada_id = las_creadas.get("Encargar las semillas")
        el_boton = f'[data-accion="tarea-cancelar"][data-tarea="{la_cancelada_id}"]'
        comprobar(
            bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(el_boton)}))")),
            f"la tarea {la_cancelada_id} trae su botón de cancelar en la ficha",
        )
        nav.pulsar(el_boton)
        nav.esperar(
            f"!document.querySelector('[data-accion=\"tarea-cancelar\"][data-tarea=\"{la_cancelada_id}\"]')",
            segundos=25,
        )
        time.sleep(1.0)
        tras_cancelar = leer_la_ficha(nav)
        decir_la_ficha(tras_cancelar)
        resultado["tras_cancelar"] = tras_cancelar
        guardar_captura(nav, CARPETA / f"tareas-v{vuelta}-ficha-tras-cancelar.png")
        la_cancelada = la_tarea_por_su_titulo(tras_cancelar, "Encargar las semillas")
        comprobar(
            la_cancelada is not None,
            "la tarea cancelada SIGUE en el bloque (cancelar no es borrar)",
        )
        if la_cancelada is not None:
            comprobar(
                CANCELADA_POR in (la_cancelada.get("resto") or "")
                and QUIEN in (la_cancelada.get("resto") or ""),
                f"y dice quién la canceló («{CANCELADA_POR} {QUIEN}»): "
                f"{(la_cancelada.get('resto') or '')!r}",
            )
            comprobar(
                la_cancelada.get("sin_botones") is True,
                "y no lleva botones de cerrar",
            )
        _, ficha_ahora = _puerta(token, "GET", f"/api/contactos/{contacto_id}")
        suya = next(
            (t for t in (ficha_ahora.get("tareas") or []) if t.get("id") == la_cancelada_id), None
        )
        decir(f"la puerta de datos dice: {como_texto(suya)}")
        comprobar(
            (suya or {}).get("estado") == "cancelada"
            and (suya or {}).get("cancelada_por") == QUIEN
            and bool((suya or {}).get("cancelada_en")),
            f"el servidor la da por cancelada, con quién y cuándo "
            f"({(suya or {}).get('estado')!r}, {(suya or {}).get('cancelada_por')!r})",
        )
        comprobar(
            bool((suya or {}).get("completada_en")) is False,
            "y no se ha marcado como hecha de paso",
        )

        # ---- la lista de #/tareas ---------------------------------------------------
        paso("9", "La lista de `#/tareas`: los cuatro filtros, la dirección y la recarga")
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/tareas", esperar=3.0)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
        time.sleep(1.0)
        lista = leer_la_lista(nav)
        decir(
            f"en pantalla: {lista.get('direccion')!r}  título {lista.get('titulo')!r}  "
            f"tabla: {lista.get('hay_tabla')}  filas: {lista.get('cuantas')}"
        )
        decir(f"filtros que hay: {como_texto(lista.get('filtros'))}")
        # **¿De dónde salen las palabras de esta pantalla?** Se mira lo que hay guardado en el móvil y lo que
        # contesta la puerta: si el rótulo de la pantalla sale vacío, hay que poder decir **por qué**, y eso no se
        # adivina — se mide.
        los_textos = nav.evaluar(LA_SONDA_DE_LOS_TEXTOS)
        decir(f"los textos de la lista, en el móvil: {como_texto((los_textos or {}).get('en_el_movil'))}")
        decir(f"y los que contesta /api/interfaz:  {como_texto((los_textos or {}).get('de_la_puerta'))}")
        resultado["los_textos_de_la_lista"] = los_textos
        en_el_movil = (los_textos or {}).get("en_el_movil") or {}
        comprobar(
            en_el_movil.get("es_lista") is False and en_el_movil.get("sabe_decir_el_titulo") is True,
            "lo que la puerta manda en `tareas` es un diccionario con sus rótulos, no una lista de nombres "
            f"(tipo {en_el_movil.get('tipo')!r}, es_lista={en_el_movil.get('es_lista')}, "
            f"sabe_decir_el_titulo={en_el_movil.get('sabe_decir_el_titulo')})",
        )
        comprobar(
            bool(lista.get("titulo")),
            f"la pantalla de la lista enseña su título ({lista.get('titulo')!r})",
        )
        comprobar(
            all((f.get("texto") or "").strip() for f in (lista.get("filtros") or [])),
            "y los cuatro botones de filtro llevan su rótulo "
            f"({[(f.get('vencimiento'), f.get('texto')) for f in (lista.get('filtros') or [])]})",
        )
        resultado["rotulos_de_la_lista"] = bool(lista.get("titulo")) and all(
            (f.get("texto") or "").strip() for f in (lista.get("filtros") or [])
        )
        comprobar(
            lista.get("hay_tabla") is True and lista.get("cuantas") == len(LAS_TAREAS),
            f"la lista enseña las {len(LAS_TAREAS)} tareas sin filtro ({lista.get('cuantas')})",
        )
        comprobar(
            el_camino_de_la_direccion(lista.get("direccion")) == "#/tareas"
            and lleva_el_filtro(lista.get("direccion"), None),
            f"y su dirección es la de la lista, sin filtro puesto ({lista.get('direccion')!r})",
        )
        comprobar(
            sorted((f.get("vencimiento") or "") for f in (lista.get("filtros") or []))
            == ["", "hoy", "sin_fecha", "vencidas"],
            "están los cuatro filtros del encargo "
            f"({[(f.get('texto'), f.get('vencimiento')) for f in (lista.get('filtros') or [])]})",
        )
        comprobar(
            sum(1 for f in (lista.get("filtros") or []) if f.get("marcado")) == 1
            and [f for f in (lista.get("filtros") or []) if f.get("marcado")][0].get("vencimiento") is None,
            "y sin filtro está marcado el de «Todas» (uno solo, y es ese) "
            f"({[f.get('texto') for f in (lista.get('filtros') or []) if f.get('marcado')]})",
        )
        # **El contraste que hace que esto sea una medida y no una impresión**: lo que se ve tiene que ser
        # **exactamente** lo que el servidor devuelve para ese mismo filtro. Si la pantalla y la puerta dicen cosas
        # distintas, el que se equivoca es uno de los dos y hay que saberlo.
        resultado["filtros_medidos"] = {}
        las_pruebas = (
            ("hoy", "hoy"),
            ("vencidas", "vencidas"),
            ("sin_fecha", "sin_fecha"),
            ("todas", None),
        )
        for nombre, valor in las_pruebas:
            selector = (
                '[data-accion="tareas-ver"]:not([data-vencimiento])'
                if valor is None
                else f'[data-accion="tareas-ver"][data-vencimiento="{valor}"]'
            )
            decir("")
            decir(f"  --- filtro «{nombre}» ---")
            comprobar(
                bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(selector)}))")),
                f"el botón del filtro «{nombre}» existe en la pantalla",
            )
            # **Primero lo que dice el servidor, y después se espera a que la pantalla diga lo mismo**: así no se
            # lee una pantalla a medio pintar y no se confunde «todavía cargando» con «el filtro no filtra».
            camino = "/api/tareas" + (f"?vencimiento={valor}" if valor else "")
            codigo, suyas = la_puerta(token, "GET", camino, que="sí")
            comprobar(codigo == 200, f"la puerta {camino} contesta ({codigo})")
            de_la_puerta = sorted(t.get("titulo") or "" for t in (suyas or {}).get("tareas", []))
            # **Se borra la historia de direcciones justo antes de pulsar**, para poder decir si la dirección del
            # filtro **llega a existir** y quién la quita después. Sin esto, una dirección que se escribe y se
            # borra en el mismo suspiro se lee como «nunca se escribió», que es otra cosa.
            nav.evaluar("(() => { window.__las_direcciones = [window.location.hash]; return 1; })()")
            nav.pulsar(selector)
            llego = nav.esperar(
                "document.querySelectorAll('[data-tabla=\"tareas\"] tbody tr').length === "
                f"{len(de_la_puerta)}",
                segundos=25,
            )
            time.sleep(0.6)
            la_historia = nav.evaluar("window.__las_direcciones || []")
            filtrada = leer_la_lista(nav)
            decir(
                f"la pantalla se ha puesto al día tras pulsar: {llego}   "
                f"dirección: {filtrada.get('direccion')!r}   filas: {filtrada.get('cuantas')}   "
                f"marcado: {[f.get('vencimiento') for f in (filtrada.get('filtros') or []) if f.get('marcado')]}"
            )
            decir(f"direcciones por las que ha pasado la página: {la_historia}")
            resultado.setdefault("historias_de_la_direccion", {})[nombre] = la_historia
            for fila in filtrada.get("filas") or []:
                decir(
                    f"             {fila['titulo']!r} vencida={fila['vencida_marcada']} "
                    f"fecha={fila['fecha']!r} responsable={fila['responsable']!r} "
                    f"con_quien={fila['con_quien']!r} cierre={fila['cierre']!r}"
                )
            comprobar(
                el_camino_de_la_direccion(filtrada.get("direccion")) == "#/tareas"
                and lleva_el_filtro(filtrada.get("direccion"), valor),
                f"la dirección cambia al filtro «{nombre}» ({filtrada.get('direccion')!r}; se esperaba el "
                f"camino #/tareas con vencimiento={valor!r}). Direcciones por las que ha pasado: {la_historia}",
            )
            los_marcados = [f for f in (filtrada.get("filtros") or []) if f.get("marcado")]
            comprobar(
                len(los_marcados) == 1 and los_marcados[0].get("vencimiento") == valor,
                f"y el filtro puesto queda marcado, y solo él "
                f"({[f.get('vencimiento') for f in los_marcados]})",
            )
            en_pantalla = sorted(f.get("titulo") or "" for f in (filtrada.get("filas") or []))
            decir(f"la puerta dice: {de_la_puerta}")
            decir(f"la pantalla dice: {en_pantalla}")
            comprobar(
                en_pantalla == de_la_puerta,
                f"lo que se ve con el filtro «{nombre}» es EXACTAMENTE lo que devuelve el servidor "
                f"({len(en_pantalla)} == {len(de_la_puerta)})",
            )
            resultado["filtros_medidos"][nombre] = {
                "direccion": filtrada.get("direccion"),
                "en_pantalla": en_pantalla,
                "de_la_puerta": de_la_puerta,
            }
        # **Lo que cada filtro tiene que dejar dentro y fuera**, dicho por su nombre.
        medidos = resultado["filtros_medidos"]
        comprobar(
            "Llamar al del pienso" in medidos["hoy"]["en_pantalla"]
            and "Revisar el riego" not in medidos["hoy"]["en_pantalla"]
            and "Preguntar por el abono" not in medidos["hoy"]["en_pantalla"],
            "«hoy» trae lo de hoy y deja fuera lo de mañana y lo que no tiene fecha "
            f"({medidos['hoy']['en_pantalla']})",
        )
        comprobar(
            "Llamar al veterinario" in medidos["vencidas"]["en_pantalla"]
            and "Llamar al del pienso" not in medidos["vencidas"]["en_pantalla"],
            "«vencidas» trae lo de ayer y deja fuera lo de hoy "
            f"({medidos['vencidas']['en_pantalla']})",
        )
        comprobar(
            sorted(medidos["sin_fecha"]["en_pantalla"])
            == ["Encargar las semillas", "Preguntar por el abono"],
            "«sin fecha» trae las dos que no tienen día —y trae también la cancelada, que no ha desaparecido— "
            f"({medidos['sin_fecha']['en_pantalla']})",
        )
        comprobar(
            len(medidos["todas"]["en_pantalla"]) == len(LAS_TAREAS),
            "sin filtro están las seis, las cerradas incluidas "
            f"({len(medidos['todas']['en_pantalla'])})",
        )
        # **La recarga con el filtro puesto**, que es lo que hace que la lista se pueda enlazar.
        decir("")
        decir("  --- y con el filtro «hoy» puesto, se recarga la página entera ---")
        nav.pulsar('[data-accion="tareas-ver"][data-vencimiento="hoy"]')
        nav.esperar(
            "document.querySelectorAll('[data-tabla=\"tareas\"] tbody tr').length === "
            f"{len(medidos['hoy']['de_la_puerta'])}",
            segundos=25,
        )
        time.sleep(0.6)
        antes_de_recargar = leer_la_lista(nav)
        decir(f"antes de recargar: {antes_de_recargar.get('direccion')!r}")
        nav.orden("Page.reload", {"ignoreCache": True})
        time.sleep(3.5)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=30)
        nav.esperar(
            "document.querySelectorAll('[data-tabla=\"tareas\"] tbody tr').length === "
            f"{len(medidos['hoy']['de_la_puerta'])}",
            segundos=30,
        )
        time.sleep(1.0)
        tras_recargar = leer_la_lista(nav)
        decir(
            f"después de recargar: {tras_recargar.get('direccion')!r}  filas: {tras_recargar.get('cuantas')}  "
            f"marcado: {[f.get('texto') for f in (tras_recargar.get('filtros') or []) if f.get('marcado')]}"
        )
        decir(f"lo que se ve: {(tras_recargar.get('texto') or '')[:600]!r}")
        resultado["lista_tras_recargar"] = tras_recargar
        guardar_captura(nav, CARPETA / f"tareas-v{vuelta}-lista-hoy-tras-recargar.png")
        comprobar(
            el_camino_de_la_direccion(tras_recargar.get("direccion")) == "#/tareas"
            and lleva_el_filtro(tras_recargar.get("direccion"), "hoy"),
            f"tras recargar sigue el mismo filtro en la dirección ({tras_recargar.get('direccion')!r})",
        )
        los_marcados = [f for f in (tras_recargar.get("filtros") or []) if f.get("marcado")]
        comprobar(
            len(los_marcados) == 1 and los_marcados[0].get("vencimiento") == "hoy",
            f"y sigue marcado el mismo botón ({[f.get('texto') for f in los_marcados]})",
        )
        comprobar(
            sorted(f.get("titulo") for f in (tras_recargar.get("filas") or []))
            == sorted(antes_de_recargar.get("filas") and [f.get("titulo") for f in antes_de_recargar["filas"]] or []),
            "y la misma lista que antes de recargar "
            f"({[f.get('titulo') for f in (tras_recargar.get('filas') or [])]})",
        )
        # **El cierre desde la propia lista**, que es otra puerta distinta de la de la ficha (`data-id` es el
        # contacto, `data-tarea` la tarea). Se anda porque un botón que no hace nada en una lista es de las cosas
        # que más caro salen.
        decir("")
        decir("  --- extra: completar una tarea DESDE LA LISTA (la puerta de la lista, no la de la ficha) ---")
        nav.abrir(f"http://127.0.0.1:{PUERTO}/#/tareas", esperar=3.0)
        nav.esperar(
            "document.querySelectorAll('[data-tabla=\"tareas\"] tbody tr').length === "
            f"{len(LAS_TAREAS)}",
            segundos=30,
        )
        time.sleep(0.8)
        la_de_manana_id = las_creadas.get("Revisar el riego")
        boton_de_la_lista = (
            f'[data-accion="tarea-completar"][data-tarea="{la_de_manana_id}"]'
        )
        comprobar(
            bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(boton_de_la_lista)}))")),
            "la tarea de mañana trae su botón de completar en la lista",
        )
        nav.pulsar(boton_de_la_lista)
        nav.esperar("document.querySelector('#pantalla h1') !== null", segundos=25)
        time.sleep(2.0)
        tras_cerrar_en_la_lista = leer_la_ficha(nav)
        decir(
            f"tras pulsarlo, la pantalla es {tras_cerrar_en_la_lista.get('direccion')!r} "
            f"(título {tras_cerrar_en_la_lista.get('titulo')!r})"
        )
        _, ficha_ahora = _puerta(token, "GET", f"/api/contactos/{contacto_id}")
        suya = next(
            (t for t in (ficha_ahora.get("tareas") or []) if t.get("id") == la_de_manana_id), None
        )
        decir(f"la puerta de datos dice: {como_texto(suya)}")
        resultado["cierra_desde_la_lista"] = (suya or {}).get("estado") == "hecha"
        comprobar(
            resultado["cierra_desde_la_lista"],
            f"completar desde la lista cierra de verdad la tarea ({(suya or {}).get('estado')!r})",
        )
        resultado["la_lista_lleva_a_la_ficha"] = tras_cerrar_en_la_lista.get("direccion")

        # ---- extra: y sin ratón, ¿se puede teclear el día? ---------------------------
        # **Esto se mide porque la primera medición decía que no** (sonda del 14/10/2026) y luego resultó estar
        # confundida: el fallo era del guion —vaciaba el campo sin quitarle el foco— y no del campo. Se comprueba
        # aquí, con un `Tab` de verdad, porque es la diferencia entre «hay que pulsar con el ratón» y «se puede
        # escribir con el teclado», y eso decide si esta pantalla la puede usar quien no usa ratón.
        decir("")
        decir("  --- extra: el día, tecleado SOLO con el teclado (Tab, sin tocar el ratón) ---")
        nav.evaluar("(() => { const e = document.getElementById('tarea-titulo'); if (e) e.focus(); return 1; })()")
        time.sleep(0.2)
        nav.tecla("Tab")
        time.sleep(0.3)
        en_el_foco = nav.evaluar(
            "document.activeElement ? (document.activeElement.id || document.activeElement.tagName) : null"
        )
        decir(f"después de un `Tab` desde #tarea-titulo, tiene el foco: {en_el_foco!r}")
        resultado["el_tab_llega_al_dia"] = en_el_foco == "tarea-fecha"
        comprobar(
            resultado["el_tab_llega_al_dia"],
            f"con `Tab` se llega al campo del día ({en_el_foco!r})",
        )
        digitos_del_dia = los_digitos_de_una_fecha(
            hoy + dt.timedelta(days=2), medido.get("orden_de_la_fecha") or "día-mes-año"
        )
        antes_del_tab = _leer_el_campo(nav, "tarea-fecha")
        _teclear_con(nav, "tarea-fecha", digitos_del_dia, "keyDown")
        despues_del_tab = _leer_el_campo(nav, "tarea-fecha")
        decir(
            f"se teclean {digitos_del_dia} con el teclado: antes {antes_del_tab!r} → después "
            f"{despues_del_tab!r} (se esperaba "
            f"{(hoy + dt.timedelta(days=2)).isoformat()!r})"
        )
        resultado["el_dia_se_teclea_sin_raton"] = despues_del_tab == (hoy + dt.timedelta(days=2)).isoformat()
        comprobar(
            resultado["el_dia_se_teclea_sin_raton"],
            "y el día SE TECLEA sin ratón, solo con el teclado "
            f"({despues_del_tab!r}); el campo no hay que pulsarlo con el ratón para poder escribirlo",
        )

        resultado["errores_de_la_pagina"] = nav.evaluar("window.__los_errores || []")
        decir(
            f"errores de la página en todo el recorrido: "
            f"{como_texto(resultado['errores_de_la_pagina'])}"
        )
    resultado["capturas"] = CAPTURAS[empezaron_las_capturas:]
    return resultado


def el_aislamiento(token: str, ajena: str, contacto_id: int, las_creadas: dict) -> dict:
    """**La segunda explotación no ve ni toca las tareas de la primera.**

    Y para que «no ve nada» sea un dato y no un hueco, la ajena **tiene su propia tarea**: así `GET /api/tareas`
    devuelve **exactamente una**, con una marca inconfundible, y se ve que la puerta funciona y que filtra.
    """
    paso("10", "AISLAMIENTO: la segunda explotación no ve ni cierra las tareas de la primera")
    salida: dict = {}
    # Una tarea de verdad en la finca ajena, con su contacto y todo.
    codigo, su_contacto = la_puerta(
        ajena, "POST", "/api/contactos", {"nombre": "Contacto de la finca ajena (tareas)"}, que="sí"
    )
    comprobar(codigo == 201, f"la finca ajena tiene su propio contacto ({codigo})")
    ajena_contacto = int((su_contacto or {}).get("id") or 0)
    codigo, _ = la_puerta(
        ajena,
        "POST",
        f"/api/contactos/{ajena_contacto}/tareas",
        {"titulo": "TAREA DE LA FINCA AJENA", "fecha_prevista": dt.date.today().isoformat()},
        que="sí",
    )
    comprobar(codigo == 200, f"y su propia tarea ({codigo})")
    codigo, suyas = la_puerta(ajena, "GET", "/api/tareas", que="sí")
    comprobar(codigo == 200, f"la lista de la finca ajena se lee ({codigo})")
    titulos_ajenos = [t.get("titulo") for t in (suyas or {}).get("tareas", [])]
    decir(f"la finca ajena ve: {titulos_ajenos}")
    comprobar(
        titulos_ajenos == ["TAREA DE LA FINCA AJENA"],
        f"la finca ajena ve SOLO la suya, y ninguna de la primera ({titulos_ajenos})",
    )
    mias = [t for t in las_creadas]
    comprobar(
        not any(titulo in titulos_ajenos for titulo in mias),
        f"y no se ha colado ninguna de las de la primera explotación "
        f"(las mías: {mias})",
    )
    # Y el cierre cruzado, que es lo que tiene que dar **404** (no «no es tuya», que ya diría que existe).
    la_mia = las_creadas.get("Llamar al veterinario") or next(iter(las_creadas.values()), None)
    codigo, cruzado = la_puerta(ajena, "POST", f"/api/tareas/{la_mia}/completar", {}, que="sí")
    salida["completar_ajena"] = codigo
    comprobar(codigo == 404, f"completar una tarea ajena da 404 ({codigo})")
    decir(f"y lo que contesta: {como_texto(cruzado)}")
    codigo, _ = la_puerta(ajena, "POST", f"/api/tareas/{la_mia}/cancelar", {}, que="sí")
    salida["cancelar_ajena"] = codigo
    comprobar(codigo == 404, f"y cancelarla también da 404 ({codigo})")
    # **Y la tarea tiene que seguir como estaba**: un 404 que además hubiera tocado algo sería peor que un 200.
    _, ficha_ahora = _puerta(token, "GET", f"/api/contactos/{contacto_id}")
    suya = next((t for t in (ficha_ahora.get("tareas") or []) if t.get("id") == la_mia), None)
    decir(f"y la tarea de la primera explotación, después del intento: {como_texto(suya)}")
    comprobar(
        (suya or {}).get("estado") == "pendiente",
        f"el intento de la ajena NO ha tocado la tarea ({suya and suya.get('estado')!r})",
    )
    return salida


# ---------------------------------------------------------------------------
# Todo junto
# ---------------------------------------------------------------------------


def una_vuelta(direccion: str, vuelta: int) -> dict:
    """El recorrido entero, con **su propia explotación** (una cuenta nueva en la misma base temporal)."""
    global VUELTA_ACTUAL
    VUELTA_ACTUAL = vuelta
    print("\n" + "=" * 78)
    print(f"  VUELTA {vuelta} — el recorrido de «Lo que hay que hacer»")
    print("=" * 78)
    decir("se prepara el escenario prestado: datos_representativos.preparar(...)")
    escenario = preparar(direccion, marca=f"v{vuelta}-{os.getpid()}-{int(time.time())}")
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
    paso("1", "La explotación de esta vuelta, recién creada: no tiene que traer ninguna tarea")
    codigo, suyas = la_puerta(token, "GET", "/api/tareas", que="sí")
    comprobar(codigo == 200, f"la lista de tareas se lee ({codigo})")
    comprobar(
        (suyas or {}).get("tareas") == [],
        f"la explotación nueva no tiene tareas apuntadas ({(suyas or {}).get('tareas')!r})",
    )

    recorrido = el_recorrido_en_el_navegador(direccion, token, ajena, vuelta)
    creadas = recorrido.get("tareas") or {}
    aislamiento = el_aislamiento(token, ajena, int(recorrido.get("contacto_id") or 0), creadas)

    filtros = recorrido.get("filtros_medidos") or {}
    recargada = recorrido.get("lista_tras_recargar") or {}
    los_marcados = [f for f in (recargada.get("filtros") or []) if f.get("marcado")]
    tras_completar = recorrido.get("tras_completar") or {}
    la_hecha = la_tarea_por_su_titulo(tras_completar, "Llamar al del pienso") or {}
    la_hecha_tras = la_tarea_por_su_titulo(
        recorrido.get("tras_recargar_la_hecha") or {}, "Llamar al del pienso"
    ) or {}
    la_otra_vencida = la_tarea_por_su_titulo(
        recorrido.get("tras_recargar_la_hecha") or {}, "Llamar al veterinario"
    ) or {}
    tras_cancelar = recorrido.get("tras_cancelar") or {}
    la_cancelada = la_tarea_por_su_titulo(tras_cancelar, "Encargar las semillas") or {}
    la_vencida_por_la_puerta = recorrido.get("vencida_por_la_puerta") or {}
    la_vencida_despues = recorrido.get("vencida_completada_por_la_puerta") or {}

    huella = {
        # **Lo que se apunta**: las seis tareas quedan en el bloque y en la puerta de datos.
        "apunta": len(creadas) == len(LAS_TAREAS),
        # **El tecleo**: los tres campos, de teclado y no por JavaScript.
        "tecleo": bool(recorrido.get("tecleo")),
        # **Hecha**, y sigue hecha tras recargar la página entera.
        "hecha": la_hecha.get("sin_botones") is True and la_hecha_tras.get("sin_botones") is True,
        # **Quién** la hizo, en pantalla y tras la recarga.
        "quien": HECHA_POR in (la_hecha.get("resto") or "")
        and QUIEN in (la_hecha.get("resto") or "")
        and QUIEN in (la_hecha_tras.get("resto") or ""),
        # **Vencida**: lo de ayer sale marcado.
        "vencida": la_vencida_por_la_puerta.get("vencida") is True
        and la_otra_vencida.get("vencida_marcada") is True,
        # **Pendiente**: sigue pendiente y de verdad se puede completar.
        "pendiente": la_vencida_por_la_puerta.get("estado") == "pendiente"
        and la_vencida_despues.get("estado") == "hecha",
        # **Cancela**: cancelada, con quién, y sin desaparecer.
        "cancela": la_cancelada.get("sin_botones") is True
        and CANCELADA_POR in (la_cancelada.get("resto") or "")
        and QUIEN in (la_cancelada.get("resto") or ""),
        "no_desaparece": bool(la_cancelada)
        and "Encargar las semillas" in (filtros.get("sin_fecha", {}).get("en_pantalla") or [])
        and "Encargar las semillas" in (filtros.get("todas", {}).get("en_pantalla") or []),
        # **La lista**: las seis, cerradas incluidas.
        "lista": bool(filtros.get("todas")) and len(filtros["todas"]["en_pantalla"]) == len(LAS_TAREAS),
        # **Los filtros**: cada uno deja ver lo que tiene que dejar ver, y lo que se ve es **exactamente** lo que
        # devuelve el servidor para ese mismo filtro. (Esto es aparte de si el filtro queda escrito en la
        # dirección, que es otra cosa y se mide con su propio nombre.)
        "filtros": all(
            filtros.get(nombre, {}).get("en_pantalla") == filtros.get(nombre, {}).get("de_la_puerta")
            for nombre in ("hoy", "vencidas", "sin_fecha", "todas")
        )
        and bool(filtros.get("todas")),
        # **El filtro, en la dirección**: es lo que hace que la lista se pueda enlazar.
        "filtro_en_la_direccion": all(
            el_camino_de_la_direccion(filtros.get(nombre, {}).get("direccion")) == "#/tareas"
            and lleva_el_filtro(filtros.get(nombre, {}).get("direccion"), valor)
            for nombre, valor in (
                ("hoy", "hoy"),
                ("vencidas", "vencidas"),
                ("sin_fecha", "sin_fecha"),
                ("todas", None),
            )
        ),
        # **La recarga** con el filtro puesto: misma dirección, mismo botón marcado, misma lista.
        "recarga": el_camino_de_la_direccion(recargada.get("direccion")) == "#/tareas"
        and lleva_el_filtro(recargada.get("direccion"), "hoy")
        and len(los_marcados) == 1
        and los_marcados[0].get("vencimiento") == "hoy",
        # **Los rótulos de la pantalla** (medido): la lista de `#/tareas` sale con su título y con los nombres de
        # sus cuatro botones. Sin esto, la pantalla se abre **muda**: se puede usar, pero no se sabe qué es nada.
        "rotulos": bool(recorrido.get("rotulos_de_la_lista")),
        # **El día, sin ratón**: se llega con `Tab` y se teclea.
        "dia_sin_raton": bool(recorrido.get("el_tab_llega_al_dia"))
        and bool(recorrido.get("el_dia_se_teclea_sin_raton")),
        # **El aislamiento**: la otra finca no ve las mías, y no puede cerrarlas.
        "aislamiento_lista": aislamiento.get("completar_ajena") == 404
        and aislamiento.get("cancelar_ajena") == 404,
        "404": aislamiento.get("completar_ajena") == 404,
    }
    recorrido["huella"] = huella
    return recorrido


def main() -> int:
    global PUERTO
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    print("=" * 78)
    print("  EL RECORRIDO DE «LO QUE HAY QUE HACER» — alta, tecleo, cierre, vencida, cancelar y filtros")
    print("=" * 78)
    print(f"  puerto: {PUERTO}   (nunca 8000 ni 8029)")
    print(f"  intérprete: {PYTHON}")
    print(f"  capturas: {CARPETA}")
    print("  DOS vueltas, cada una con su propia explotación: la huella tiene que salir idéntica")

    paso("0", "La base del agricultor, que NO se toca")
    huella_antes = la_huella_de_un_fichero(LA_BASE_DEL_AGRICULTOR)
    decir(f"sha256 antes: {huella_antes}")
    decir(f"se esperaba:  {SU_HUELLA_ESPERADA}")
    comprobar(
        huella_antes == SU_HUELLA_ESPERADA,
        "la huella de la base del agricultor es la que tiene que ser, antes de empezar",
    )

    if PUERTO in (8000, 8029):
        print("  (el puerto pedido es de David: no se toca)")
        return 2
    if not _el_puerto_esta_libre(PUERTO):
        print(f"  AVISO: el puerto {PUERTO} está ocupado. Se para aquí y no se toca nada ajeno.")
        return 2

    temporal = pathlib.Path(tempfile.mkdtemp(prefix="cd-tareas-"))
    servidor = None
    vueltas: dict[int, dict] = {}
    try:
        paso("1", "El servidor aislado, con base temporal")
        servidor, base, bitacora = levantar_el_servidor(temporal)
        decir(f"se levanta: {PYTHON} -m uvicorn app.main:app --port {PUERTO}")
        decir(f"con CUEDIGITAL_DATABASE_URL=sqlite:///{base}")
        decir(f"y PYTHONIOENCODING=utf-8   (bitácora: {bitacora})")
        comprobar(_esperar_al_servidor(), "el servidor contesta en /api/interfaz")

        for numero in (1, 2):
            vueltas[numero] = una_vuelta(f"http://127.0.0.1:{PUERTO}", numero)

        paso("11", "El resumen, y las dos huellas")
        for numero in (1, 2):
            huella = vueltas[numero]["huella"]
            recorrido = vueltas[numero]
            print(f"\n  --- vuelta {numero} ---")
            decir(f"contacto: {recorrido.get('contacto_id')}   tareas apuntadas: {len(recorrido.get('tareas') or {})}")
            decir(
                "el tecleo, campo por campo: "
                f"título={recorrido.get('maneras', {}).get('titulo')!r} "
                f"fecha={recorrido.get('maneras', {}).get('fecha')!r} "
                f"(dígitos en orden {recorrido.get('maneras', {}).get('orden_de_la_fecha')!r}) "
                f"responsable={recorrido.get('maneras', {}).get('responsable')!r}"
            )
            for nombre, medido in (recorrido.get("filtros_medidos") or {}).items():
                decir(
                    f"filtro «{nombre}»: dirección {medido.get('direccion')!r} · "
                    f"{len(medido.get('en_pantalla') or [])} en pantalla · "
                    f"{len(medido.get('de_la_puerta') or [])} en la puerta"
                )
            decir(
                "direcciones por las que pasa la página al pulsar cada filtro: "
                f"{como_texto(recorrido.get('historias_de_la_direccion'))}"
            )
            decir(
                "los rótulos de la lista de tareas: "
                f"{como_texto(recorrido.get('los_textos_de_la_lista'))}"
            )
            decir(
                f"la lista lleva a la ficha: {recorrido.get('la_lista_lleva_a_la_ficha')!r}   "
                f"completar desde la lista: {recorrido.get('cierra_desde_la_lista')}"
            )
            decir(f"errores de la página: {como_texto(recorrido.get('errores_de_la_pagina'))}")
            decir(f"capturas: {len(recorrido.get('capturas') or [])}")

        lineas = []
        for numero in (1, 2):
            huella = vueltas[numero]["huella"]
            lineas.append(
                "HUELLA"
                + "".join(f" {clave}={valor}" for clave, valor in huella.items())
            )
            print("\n" + lineas[-1])
        comprobar(
            lineas[0] == lineas[1],
            "las DOS vueltas dan la MISMA huella (el recorrido es determinista)",
        )
        if lineas[0] != lineas[1]:
            decir(f"vuelta 1: {lineas[0]}")
            decir(f"vuelta 2: {lineas[1]}")
        # **Y las capturas, dichas una a una**: si un paso no dejó imagen, se sabe.
        todas = [ruta for numero in (1, 2) for ruta in (vueltas[numero].get("capturas") or [])]
        decir(f"capturas guardadas: {len(todas)}")
        for ruta in todas:
            decir(f"  {ruta}")

        print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {FALLOS}")
        return 0 if FALLOS == 0 else 1
    finally:
        print("\n  (se apaga lo que se ha levantado)")
        print(f"  {apagar_el_servidor(servidor)}")
        # **Windows tarda en soltar la base**: el fichero de SQLite sigue abierto un instante después de que el
        # servidor se apague, y borrar la carpeta falla con `PermissionError: [WinError 32]`. Se reintenta unas
        # cuantas veces y, si aun así no se puede, **se dice**: una limpieza que falla en silencio deja basura.
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
        print(f"  el puerto {PUERTO} vuelve a estar libre: {_el_puerto_esta_libre(PUERTO)}")
        vivo = lo_que_ha_quedado_vivo()
        print(f"  procesos míos que han quedado vivos: {vivo if vivo else 'ninguno'}")


if __name__ == "__main__":
    raise SystemExit(main())
