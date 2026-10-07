"""El armazón nuevo, **en un navegador de verdad**: el menú agrupado y la navegación completa.

## Por qué existe este fichero

El encargo del rediseño (`docs/REDISENO_V0_STITCH_20261007.md`, apartado 3) pide tres cosas que **no se
pueden comprobar leyendo ficheros**:

  1. «**Menú**: Inicio; Campo (…); Gestión (…); Cuaderno; Normativa; Ajustes. La agrupación es visual, no
     introduce pantallas intermedias obligatorias.»
  2. «**A 712 px y en cualquier ancho intermedio, Menú siempre ofrece todas las secciones**, incluidas
     Cuentas y Normativa.» (Normativa no existe como pantalla: lo que se comprueba es que **no** se ha
     inventado un renglón para llenar ese hueco.)
  3. «Login carece de menú de negocio y no deja abrir fichas sin sesión.»

Lo que hace falta para comprobarlo de verdad es un navegador que mida el ancho, que enseñe u oculte con su
CSS y que **mueva el foco con teclas de verdad**: «se llega a Cuentas tabulando» no se puede comprobar con
un HTML volcado. Por eso esto usa `navegador_cdp.py` (Chrome por el protocolo de depuración), el mismo que
usa `comprobar_teclado_y_zoom.py`.

## Qué comprueba, y a qué ancho

En **390, 712, 1024 y 1440 px** (con la sesión abierta):

  · **Los 21 renglones están**, cada uno con su `id` (`menu-<clave>`), y **ninguno de más**: un renglón que
    no lleve a ninguna pantalla (el hueco de «Normativa») se cuenta como fallo.
  · **El estado inicial no está a medias**: o no se ve ningún renglón (el menú está cerrado, que es lo que
    pasa por debajo de 64 rem) o se ven los 21 (el menú lateral del ordenador, que sale solo, y entonces no
    hay nada que pulsar: se dice como hallazgo). En el primer caso se **abre pulsando el botón de verdad**
    (`data-accion="menu-abrir"`) y se comprueba que salen los 21; y que el botón de cerrar
    (`data-accion="menu-cerrar"`) los vuelve a esconder.
  · **Los cinco grupos salen con su nombre**, y los nombres son **los del servidor** (`/api/interfaz`,
    `menu.grupo_*`), no unos escritos en el componente. Y se ven, no solo están en el documento.
  · **Todos los renglones están dentro de un grupo** (ninguno suelto ni colgado del grupo que no es): el
    grupo que le toca a cada renglón sale de la tabla `MODULOS` de `app.js`, leída aquí aparte. Se mide de
    dos formas —**por anidamiento** y **por posición**— y se dice cuál es la que vale.
  · **Se tabula por los 21 renglones y se llega a Cuentas**, y al pulsar Enter se abre «Mis cuentas»: eso es
    lo que demuestra que la agrupación **no** ha metido una pantalla intermedia.
  · **Sin sesión no hay menú de negocio**: en la pantalla de entrar no se ve ni un renglón de módulo, y una
    dirección de dentro (`#/cuentas`) no abre una ficha.

## Los paseos con el teclado, y por qué van en dos direcciones

Tabulando **de verdad**, con `Input.dispatchKeyEvent`. El armazón (`#marco`) va **antes** que la cabecera en
el documento, así que de qué lado se empieza depende de dónde esté el foco:

  · **En el ordenador** (el menú sale solo al cargar) el paseo va **hacia adelante** desde el cuerpo: el
    menú es lo primero del documento y se recorre entero.
  · **En el móvil**, el menú se abre con un botón que está **después** del armazón: al pulsarlo el foco se
    queda en ese botón, así que el paseo va **hacia atrás** (`Mayús+Tab`), que es lo que entra en el menú
    sin dar la vuelta a toda la página.

Se dice en cada paseo en qué dirección va y por dónde empieza. Un paseo que no llegue a Cuentas es un fallo.

## Las comprobaciones tienen que poder fallar

`--romper selector` cambia el selector del botón de abrir el menú por uno que no existe, `--romper renglon`
pide un renglón que no está (el «Normativa» del encargo) y `--romper grupo` pide un nombre de grupo que no
existe. **No se toca ningún fichero del programa**: la rotura es de este guion. Sirve para ver los fallos y
para saber que estas comprobaciones no están pasando por casualidad.

## Cómo se lanza

```powershell
cd backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\\cd-armazon-sub.db"
..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8027   # en otra terminal
..\\.venv\\Scripts\\python.exe scripts\\comprobar_el_armazon.py http://127.0.0.1:8027
```

Necesita un servidor de verdad con una base que se pueda ensuciar: crea una cuenta para entrar. **No es un
test**: los tests no levantan navegadores.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

from navegador_cdp import NavegadorDeVerdad, SinNavegador  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "web" / "app.js"

# Los cuatro anchos del encargo. 1024 px son 64 rem: es la frontera del CSS, y por eso está en la lista.
ANCHOS = (390, 712, 1024, 1440)

# ---------------------------------------------------------------------------
# El contador y lo que se va apuntando
# ---------------------------------------------------------------------------

COMPROBACIONES = 0
FALLOS: list[str] = []
HALLAZGOS: list[str] = []
NO_COMPROBADO: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> bool:
    """Una comprobación, con su recuento. Se puede fallar: eso es lo que la hace valer."""
    global COMPROBACIONES
    COMPROBACIONES += 1
    if condicion:
        print(f"  [OK   ] {descripcion}")
    else:
        print(f"  [FALLO] {descripcion}")
        FALLOS.append(descripcion)
    return bool(condicion)


def hallazgo(texto: str) -> None:
    """Lo que se ha medido y **no es un fallo de la comprobación**, pero hay que decirlo."""
    print(f"  [HALLAZGO] {texto}")
    HALLAZGOS.append(texto)


def sin_poder_comprobar(texto: str) -> None:
    """Lo que esta comprobación **no ha podido** mirar. No es un fallo, pero no puede quedarse callado."""
    print(f"  [SIN COMPROBAR] {texto}")
    NO_COMPROBADO.append(texto)


def titulo(texto: str) -> None:
    print(f"\n{texto}")


# ---------------------------------------------------------------------------
# La tabla de `app.js`, leída aparte
#
# Se lee aquí y no se pregunta al navegador a propósito: **lo que dice el programa** (qué renglón va en qué
# grupo) y **lo que se ve en la pantalla** son dos cosas distintas, y comprobar una contra la otra es lo que
# convierte esta medida en una comprobación. El lector se salta los comentarios y las cadenas —una tabla de
# este proyecto lleva corchetes y comillas dentro de los comentarios— y si no encontrara lo que busca lo dice.
# ---------------------------------------------------------------------------


def _final_de_la_cadena(codigo: str, desde: int) -> int:
    cierre = codigo[desde]
    i = desde + 1
    while i < len(codigo):
        if codigo[i] == "\\":
            i += 2
            continue
        if codigo[i] == cierre:
            return i
        i += 1
    return len(codigo)


def _recorta_la_lista(codigo: str, nombre: str) -> str:
    marca = f"const {nombre} = ["
    inicio = codigo.find(marca)
    if inicio < 0:
        raise ValueError(f"no encuentro la tabla «{nombre}» en app.js")
    desde = inicio + len(marca) - 1
    profundidad = 0
    i = desde
    while i < len(codigo):
        caracter = codigo[i]
        siguiente = codigo[i + 1] if i + 1 < len(codigo) else ""
        if caracter in "\"'`":
            i = _final_de_la_cadena(codigo, i) + 1
            continue
        if caracter == "/" and siguiente == "/":
            while i < len(codigo) and codigo[i] != "\n":
                i += 1
            continue
        if caracter == "/" and siguiente == "*":
            i = codigo.find("*/", i) + 1
            continue
        if caracter == "[":
            profundidad += 1
        elif caracter == "]":
            profundidad -= 1
            if profundidad == 0:
                return codigo[desde : i + 1]
        i += 1
    raise ValueError(f"la tabla «{nombre}» de app.js no se cierra")


def _objetos(texto: str) -> list[str]:
    """Los objetos `{…}` de primer nivel que hay en una lista (los `datos: {…}` de dentro no cuentan)."""
    objetos: list[str] = []
    profundidad = 0
    inicio: int | None = None
    i = 0
    while i < len(texto):
        caracter = texto[i]
        siguiente = texto[i + 1] if i + 1 < len(texto) else ""
        if caracter in "\"'`":
            i = _final_de_la_cadena(texto, i) + 1
            continue
        if caracter == "/" and siguiente == "/":
            while i < len(texto) and texto[i] != "\n":
                i += 1
            continue
        if caracter == "{":
            if profundidad == 0:
                inicio = i
            profundidad += 1
        elif caracter == "}":
            profundidad -= 1
            if profundidad == 0 and inicio is not None:
                objetos.append(texto[inicio : i + 1])
                inicio = None
        i += 1
    return objetos


def _campo(objeto: str, nombre: str) -> str:
    encontrado = re.search(rf'\b{nombre}:\s*"([^"]*)"', objeto)
    return encontrado.group(1) if encontrado else ""


def los_renglones_del_menu(codigo: str) -> list[dict]:
    """Los renglones de `MODULOS`: su clave, su texto, su acción y **su grupo**."""
    return [
        {
            "clave": _campo(objeto, "clave"),
            "texto": _campo(objeto, "texto"),
            "accion": _campo(objeto, "accion"),
            "grupo": _campo(objeto, "grupo"),
        }
        for objeto in _objetos(_recorta_la_lista(codigo, "MODULOS"))
    ]


def los_grupos_del_menu(codigo: str) -> list[dict]:
    """Los grupos de `GRUPOS_DEL_MENU`: su clave y la clave de su texto en el servidor."""
    return [
        {"clave": _campo(objeto, "clave"), "texto": _campo(objeto, "texto")}
        for objeto in _objetos(_recorta_la_lista(codigo, "GRUPOS_DEL_MENU"))
    ]


# ---------------------------------------------------------------------------
# Lo que se le pregunta al navegador
# ---------------------------------------------------------------------------

# El foco, con lo justo para saber dónde está el paseo.
FOCO = r"""
(() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) {
    return {cuerpo: true, id: "", accion: "", texto: "BODY", visible: true};
  }
  return {
    cuerpo: false,
    id: el.id || "",
    accion: (el.dataset && el.dataset.accion) || "",
    texto: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 30),
    visible: el.checkVisibility ? el.checkVisibility({checkVisibilityCSS: true, checkOpacity: true}) : true,
  };
})()
"""

# **La medida del menú**, que es el corazón de esta comprobación. Se le pasan las etiquetas de los grupos (las
# del servidor) y los `id` de los renglones (los de `app.js`), y devuelve:
#
#   · si cada renglón está en el documento y si **se ve** (`checkVisibility`, que es lo que ve el agricultor y
#     lo que tabula el navegador: un renglón con `display:none` no lo alcanza el tabulador);
#   · los botones `id="menu-…"` que hay **de más** (un renglón que no existe en el programa);
#   · cada etiqueta de grupo: cuántos elementos llevan ese texto exacto y si se ven;
#   · a qué grupo pertenece cada renglón, de dos formas: **por anidamiento** (el primer antepasado que
#     contiene exactamente una cabecera de grupo) y **por posición** (la última cabecera que va antes). La
#     primera es la buena —el renglón está *dentro* del grupo—; la segunda se mide para poder decir si la
#     agrupación es solo visual (un rótulo suelto entre renglones) en vez de callarlo.
#   · el estado del armazón: si se ve, si el menú está abierto y si los dos botones están.
MEDIDA_DEL_MENU = r"""
(() => {
  const ETIQUETAS = __ETIQUETAS__;
  const IDS = __IDS__;
  const visible = (el) =>
    !!(el && (el.checkVisibility ? el.checkVisibility({checkVisibilityCSS: true, checkOpacity: true}) : true));
  const textoDe = (el) => (el.textContent || "").replace(/\s+/g, " ").trim();
  const marco = document.getElementById("marco");
  const filas = IDS.map((id) => {
    const el = document.getElementById(id);
    return {id: id, existe: !!el, visible: visible(el), texto: el ? textoDe(el).slice(0, 40) : ""};
  });
  const menues = [...document.querySelectorAll("button[id^='menu-']")].map((el) => el.id);
  const cuerpo = [...document.querySelectorAll("body *")];
  // La cabecera de un grupo es el elemento **más pequeño** que lleva ese texto exacto y que no tiene ningún
  // botón dentro (si lo tuviera, sería el contenedor de los renglones, no el nombre del grupo).
  const candidatosDe = (etiqueta) =>
    cuerpo.filter((el) => textoDe(el) === etiqueta && !el.querySelector("button"));
  const cabeceraDe = {};
  const cabeceras = {};
  for (const etiqueta of ETIQUETAS) {
    const candidatos = candidatosDe(etiqueta);
    cabeceraDe[etiqueta] = candidatos.length ? candidatos[candidatos.length - 1] : null;
    cabeceras[etiqueta] = {cuantas: candidatos.length, visible: candidatos.some(visible)};
  }
  const vaAntes = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
  const porAnidamiento = {};
  const porPosicion = {};
  for (const fila of filas) {
    const el = fila.existe ? document.getElementById(fila.id) : null;
    if (!el) { porAnidamiento[fila.id] = null; porPosicion[fila.id] = null; continue; }
    let nodo = el.parentElement;
    let encontrado = null;
    let ambiguo = false;
    while (nodo) {
      const dentro = ETIQUETAS.filter((etiqueta) => cabeceraDe[etiqueta] && nodo.contains(cabeceraDe[etiqueta]));
      if (dentro.length === 1) { encontrado = dentro[0]; break; }
      if (dentro.length > 1) { ambiguo = true; break; }
      nodo = nodo.parentElement;
    }
    porAnidamiento[fila.id] = ambiguo ? "ambiguo" : encontrado;
    let suyo = null;
    for (const etiqueta of ETIQUETAS) {
      const cabecera = cabeceraDe[etiqueta];
      if (!cabecera || !vaAntes(cabecera, el)) continue;
      if (suyo === null || vaAntes(cabeceraDe[suyo], cabecera)) suyo = etiqueta;
    }
    porPosicion[fila.id] = suyo;
  }
  const boton = (accion) => {
    const el = document.querySelector('[data-accion="' + accion + '"]');
    return {existe: !!el, visible: visible(el)};
  };
  const nav = document.getElementById("menu-de-la-aplicacion");
  return {
    filas: filas,
    de_mas: menues.filter((id) => IDS.indexOf(id) === -1),
    cabeceras: cabeceras,
    por_anidamiento: porAnidamiento,
    por_posicion: porPosicion,
    marco: {existe: !!marco, visible: visible(marco), clase: marco ? String(marco.className) : ""},
    nav: {existe: !!nav, visible: visible(nav)},
    abrir: boton("menu-abrir"),
    cerrar: boton("menu-cerrar"),
    texto_del_marco: marco ? textoDe(marco).slice(0, 300) : "",
    visibles: filas.filter((fila) => fila.visible).length,
    existen: filas.filter((fila) => fila.existe).length,
  };
})()
"""

# Lo que hay que saber de la pantalla de entrar: si está, y si hay algo de negocio pintado detrás.
LA_ENTRADA = r"""
(() => {
  const pantalla = document.getElementById("pantalla");
  const marco = document.getElementById("marco");
  const visible = (el) =>
    !!(el && (el.checkVisibility ? el.checkVisibility({checkVisibilityCSS: true, checkOpacity: true}) : true));
  const filas = [...document.querySelectorAll("button[id^='menu-']")].filter(visible);
  const abrir = document.querySelector('[data-accion="menu-abrir"]');
  return {
    hay_entrada: !!document.getElementById("correo"),
    filas_visibles: filas.length,
    filas_en_el_documento: document.querySelectorAll("button[id^='menu-']").length,
    abrir_visible: visible(abrir),
    marco_pintado: marco ? (marco.textContent || "").trim().length > 0 : false,
    h1: pantalla && pantalla.querySelector("h1") ? pantalla.querySelector("h1").textContent.slice(0, 60) : "",
    controles: pantalla ? pantalla.querySelectorAll("button, input, select, textarea").length : -1,
    token: localStorage.getItem("cuedigital.token") ? "SI" : "NO",
  };
})()
"""

# La condición de «el menú ya está a la vista»: el renglón de las cuentas, visible de verdad.
CUENTAS_A_LA_VISTA = r"""
(() => {
  const el = document.getElementById("menu-cuentas");
  if (!el || !el.checkVisibility) return false;
  return el.checkVisibility({checkVisibilityCSS: true, checkOpacity: true});
})()
"""


# ---------------------------------------------------------------------------
# La cuenta de la prueba y el navegador
# ---------------------------------------------------------------------------


def sembrar_la_cuenta(direccion: str) -> dict:
    """Una cuenta para entrar: el menú es de negocio, así que sin sesión no hay nada que mirar."""
    correo = f"armazon-{os.getpid()}@ejemplo.test"
    clave = "una-clave-larga"
    with httpx.Client(base_url=direccion, timeout=30.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba del armazón",
                "correo": correo,
                "clave": clave,
                "explotacion": {"nombre": "La finca de la prueba del armazón", "nif": "12345678Z"},
            },
        )
        respuesta.raise_for_status()
        token = respuesta.json()["token"]
        # Los textos del servidor, que son los que tienen que salir en el menú. `/api/interfaz` no pide
        # sesión: es el vocabulario que el móvil se guarda para cuando no hay cobertura.
        interfaz = cliente.get("/api/interfaz").json()
    return {"correo": correo, "clave": clave, "token": token, "interfaz": interfaz}


def abrir_de_verdad(nav: NavegadorDeVerdad, url: str) -> None:
    """Abre una dirección con una **carga de verdad**, pasando por `about:blank`.

    Hace falta por lo mismo que en `comprobar_teclado_y_zoom.py`: cambiar solo lo de después de la
    almohadilla es una navegación dentro del mismo documento, no se recarga nada y el estado del armazón
    (el menú abierto, por ejemplo) seguiría vivo.
    """
    nav.orden("Page.navigate", {"url": "about:blank"})
    time.sleep(0.15)
    nav.abrir(url)


def entrar_en_el_navegador(nav: NavegadorDeVerdad, direccion: str, datos: dict) -> bool:
    """Abre la sesión en el navegador y carga la aplicación, por la dirección de verdad (`#/`).

    El token se escribe en el `localStorage` **del servidor de pruebas**, así que antes hay que estar en una
    página suya: en `about:blank` (que es donde deja el navegador la primera vuelta) el navegador no deja
    tocar el almacén y el intento revienta con «Access is denied for this document».
    """
    origen = nav.evaluar("location.origin")
    if not origen or origen == "null":
        nav.abrir(f"{direccion}/#/")
        nav.esperar(
            "document.getElementById('pantalla') !== null || document.getElementById('correo') !== null",
            segundos=15,
        )
    nav.evaluar(f"localStorage.setItem('cuedigital.token', {json.dumps(datos['token'])})")
    nav.evaluar("localStorage.setItem('cuedigital.nombre', 'Prueba del armazon')")
    abrir_de_verdad(nav, f"{direccion}/#/")
    return bool(
        nav.esperar(
            "document.getElementById('marco') !== null && document.querySelector('#pantalla') !== null",
            segundos=20,
        )
    )


def pulsar_enter(nav: NavegadorDeVerdad) -> None:
    """Enter **de verdad**, el que activa el botón que tiene el foco (`rawKeyDown` no lo activa)."""
    comun = {
        "windowsVirtualKeyCode": 13,
        "nativeVirtualKeyCode": 13,
        "code": "Enter",
        "key": "Enter",
        "text": "\r",
        "unmodifiedText": "\r",
    }
    nav.orden("Input.dispatchKeyEvent", {"type": "keyDown", **comun})
    nav.orden("Input.dispatchKeyEvent", {"type": "keyUp", **comun})
    time.sleep(0.25)


def foco(nav: NavegadorDeVerdad) -> dict:
    return nav.evaluar(FOCO) or {}


def esperar_la_pantalla(nav: NavegadorDeVerdad, *, segundos: float = 12.0) -> None:
    """Espera a que la pantalla esté pintada **y quieta** (React monta en dos tiempos)."""
    anterior = None
    iguales = 0
    limite = time.time() + segundos
    while time.time() < limite:
        firma = nav.evaluar(
            """(() => {
              const p = document.querySelector("#pantalla");
              const m = document.querySelector("#marco");
              return {
                controles: p ? p.querySelectorAll("button, a, input, select, textarea").length : -1,
                texto: p ? p.textContent.replace(/\\s+/g, " ").trim().length : -1,
                marco: m ? m.children.length : -1,
              };
            })()"""
        )
        if firma == anterior and int((firma or {}).get("marco", -1)) >= 1:
            iguales += 1
            if iguales >= 2:
                return
        else:
            iguales = 0
        anterior = firma
        time.sleep(0.25)


def la_medida(nav: NavegadorDeVerdad, etiquetas: list[str], ids: list[str]) -> dict:
    codigo = MEDIDA_DEL_MENU.replace("__ETIQUETAS__", json.dumps(etiquetas)).replace(
        "__IDS__", json.dumps(ids)
    )
    return nav.evaluar(codigo) or {}


def pulsar(nav: NavegadorDeVerdad, selector: str) -> bool:
    """Pulsa **de verdad** (un clic del navegador, no un `dispatchEvent` inventado)."""
    try:
        nav.pulsar(selector)
    except Exception as fallo:  # noqa: BLE001 — cualquier fallo aquí es un fallo de la comprobación
        print(f"           (no se ha podido pulsar {selector!r}: {fallo})")
        return False
    time.sleep(0.3)
    return True


# ---------------------------------------------------------------------------
# Los paseos con el teclado
# ---------------------------------------------------------------------------


def pasear(
    nav: NavegadorDeVerdad,
    *,
    hacia_atras: bool,
    parar_en: str = "",
    maximo: int = 240,
    tope_fuera: int = 3,
) -> dict:
    """Tabulando de verdad: apunta lo que va teniendo el foco, y los renglones por los que pasa.

    `parar_en` es el `id` donde se quiere acabar (el renglón de las cuentas). Sin él, el paseo termina
    cuando ya se han visto renglones y **se llevan `tope_fuera` paradas seguidas fuera del menú**: eso dice
    que ya se ha salido del armazón y que no queda ningún renglón por ver. Las paradas de fuera anteriores
    al primer renglón no cuentan: al abrir el menú desde el botón del móvil, el foco empieza fuera.

    **El paseo da la vuelta a la página si hace falta**, y eso está medido: a 390 px, abriendo el menú desde
    su botón, el renglón de las cuentas se alcanza en 26 pulsaciones porque el tabulador recorre antes la
    cabecera y la pantalla y vuelve a empezar el documento por el armazón. Por eso hay margen de sobra en
    `maximo`, y por eso el resumen del paseo dice dónde empieza: «26 pulsaciones» sin decir desde dónde no
    diría nada.
    """
    secuencia: list[dict] = []
    vistos: list[str] = []
    fuera_seguidos = 0
    for _ in range(maximo):
        nav.tecla("Tab", mayusculas=hacia_atras)
        quien = foco(nav)
        secuencia.append(quien)
        identificador = str(quien.get("id") or "")
        if identificador.startswith("menu-"):
            fuera_seguidos = 0
            if identificador not in vistos:
                vistos.append(identificador)
        elif vistos:
            fuera_seguidos += 1
        if parar_en and identificador == parar_en:
            return {"secuencia": secuencia, "vistos": vistos, "salida": "encontrado"}
        if not parar_en and vistos and fuera_seguidos >= tope_fuera:
            return {"secuencia": secuencia, "vistos": vistos, "salida": "fin"}
    return {"secuencia": secuencia, "vistos": vistos, "salida": "agotado"}


def el_resumen_del_paseo(paseo: dict, hacia_atras: bool) -> str:
    arranque = " → ".join(
        (uno.get("id") or uno.get("accion") or uno.get("texto") or "?") for uno in paseo["secuencia"][:6]
    )
    sentido = "hacia atrás (Mayús+Tab)" if hacia_atras else "hacia adelante (Tab)"
    return f"{sentido}, empieza en {arranque} … ({len(paseo['secuencia'])} pulsaciones)"


def abrir_el_menu_con_el_teclado(nav: NavegadorDeVerdad, *, maximo: int = 15) -> dict:
    """Tabulando hasta el botón del menú y pulsando Enter: el camino de quien no usa el ratón.

    Es una comprobación en sí misma: un botón al que solo se llega con el dedo deja fuera a quien navega con
    el teclado, y este botón es la única puerta al menú por debajo de 64 rem.
    """
    pulsaciones = None
    for cuantas in range(maximo + 1):
        if nav.evaluar(
            "!!(document.activeElement && document.activeElement.dataset && "
            "document.activeElement.dataset.accion === 'menu-abrir')"
        ):
            pulsaciones = cuantas
            break
        nav.tecla("Tab")
    if pulsaciones is None:
        return {"llego": False, "pulsaciones": None}
    pulsar_enter(nav)
    time.sleep(0.3)
    return {"llego": True, "pulsaciones": pulsaciones, "foco": foco(nav)}


# ---------------------------------------------------------------------------
# Las comprobaciones de un ancho
# ---------------------------------------------------------------------------


def el_nombre_del_grupo(interfaz: dict, grupo: dict) -> str:
    """El nombre de un grupo tal y como lo manda el servidor (vacío si no lo manda)."""
    menu = (interfaz or {}).get("menu") or {}
    clave_de_texto = str(grupo.get("texto") or "").split(".")[-1]
    valor = menu.get(clave_de_texto)
    return valor if isinstance(valor, str) and valor.strip() else ""


def comprobar_un_ancho(
    nav: NavegadorDeVerdad,
    direccion: str,
    datos: dict,
    ancho: int,
    renglones: list[dict],
    grupos: list[dict],
    nombres: dict,
    *,
    romper: str | None,
) -> None:
    titulo(f"== {ancho} px ==")
    ids = [f"menu-{renglon['clave']}" for renglon in renglones]
    etiquetas = [nombre for nombre in nombres.values() if nombre]
    if romper == "renglon":
        # Rotura a propósito: se pide un renglón que no existe (el «Normativa» del encargo). La
        # comprobación de «están los 21» tiene que cazarlo.
        ids = [*ids, "menu-normativa"]
    if romper == "grupo":
        # Rotura a propósito: se pide un grupo que no existe.
        etiquetas = [*etiquetas, "Normativa"]

    nav.medir(ancho, 900, movil=ancho <= 712)
    if not entrar_en_el_navegador(nav, direccion, datos):
        comprobar(False, f"{ancho} px: la aplicación se abre con la sesión puesta")
        return
    esperar_la_pantalla(nav)
    medida = la_medida(nav, etiquetas, ids)

    # --- los renglones están, y no hay ninguno de más -------------------------
    faltan = [fila["id"] for fila in medida["filas"] if not fila["existe"]]
    comprobar(
        faltan == [],
        f"{ancho} px: los {len(ids)} renglones del menú están en el documento "
        f"(faltan: {faltan or 'ninguno'})",
    )
    comprobar(
        medida["de_mas"] == [],
        f"{ancho} px: no hay ningún renglón de más ni inventado — {medida['de_mas'] or 'ninguno'}",
    )
    # El renglón que el encargo pedía y no existe (no hay pantalla que sea eso): si apareciera, es un fallo.
    inventados = [identificador for identificador in medida["de_mas"] if "normativ" in identificador.lower()]
    comprobar(
        inventados == [] and "normativ" not in str(medida["texto_del_marco"]).lower(),
        f"{ancho} px: no hay ningún renglón de «Normativa» en el menú",
    )

    # --- el estado inicial: cerrado del todo, o abierto del todo --------------
    visibles = int(medida["visibles"])
    comprobar(
        visibles in (0, len(renglones)),
        f"{ancho} px: el menú no se queda a medias — se ven {visibles} de {len(renglones)} renglones",
    )
    hay_que_abrirlo = visibles == 0
    hacia_atras = False
    if hay_que_abrirlo:
        comprobar(
            medida["abrir"]["existe"] and medida["abrir"]["visible"],
            f"{ancho} px: con el menú cerrado, el botón de abrirlo está y se ve",
        )
        if not (medida["abrir"]["existe"] and medida["abrir"]["visible"]):
            sin_poder_comprobar(
                f"{ancho} px: sin botón de abrir el menú no se puede comprobar que los 21 renglones se "
                f"alcancen con el teclado a este ancho"
            )
            return
        # --- se abre y se cierra con el ratón ---------------------------------
        selector = '[data-accion="menu-abrir"]'
        if romper == "selector":
            selector = '[data-accion="menu-abrir-NO-EXISTE"]'
        pulsado = pulsar(nav, selector)
        comprobar(pulsado, f"{ancho} px: el botón de abrir el menú se puede pulsar ({selector})")
        if not pulsado:
            return
        nav.esperar(CUENTAS_A_LA_VISTA, segundos=5)
        medida = la_medida(nav, etiquetas, ids)
        comprobar(
            int(medida["visibles"]) == len(renglones),
            f"{ancho} px: con el menú abierto se ven los {len(renglones)} renglones "
            f"(se ven {medida['visibles']}; el contenedor mide "
            f"{'visible' if medida['marco']['visible'] else 'oculto'} y su clase es "
            f"«{medida['marco']['clase']}»)",
        )
        if int(medida["visibles"]) != len(renglones):
            hallazgo(
                f"{ancho} px: el armazón abierto no se ve. La clase del contenedor es "
                f"«{medida['marco']['clase']}» y `checkVisibility` del marco dice "
                f"{medida['marco']['visible']}. Si la clase del menú abierto está puesta y no se ve, quien "
                f"manda es el CSS (un `display: none` que gana a la regla del menú abierto)"
            )
        if medida["cerrar"]["existe"]:
            cerrado = pulsar(nav, '[data-accion="menu-cerrar"]')
            comprobar(cerrado, f"{ancho} px: el botón de cerrar el menú se puede pulsar")
            if cerrado:
                tras_cerrar = la_medida(nav, etiquetas, ids)
                comprobar(
                    int(tras_cerrar["visibles"]) == 0,
                    f"{ancho} px: al cerrar el menú no se ve ningún renglón "
                    f"(se ven {tras_cerrar['visibles']})",
                )
        else:
            comprobar(False, f"{ancho} px: existe el botón de cerrar el menú")
        # --- y se abre con el teclado (que es lo que hace quien no usa el ratón) ---
        teclado = abrir_el_menu_con_el_teclado(nav)
        comprobar(
            teclado["llego"],
            f"{ancho} px: se llega al botón del menú tabulando "
            f"({teclado['pulsaciones']} pulsaciones)",
        )
        if teclado["llego"]:
            nav.esperar(CUENTAS_A_LA_VISTA, segundos=5)
            con_teclado = la_medida(nav, etiquetas, ids)
            comprobar(
                int(con_teclado["visibles"]) == len(renglones),
                f"{ancho} px: Enter en el botón abre el menú con los {len(renglones)} renglones "
                f"(se ven {con_teclado['visibles']})",
            )
            if int(con_teclado["visibles"]) == len(renglones):
                medida = con_teclado
                # El foco se queda donde estaba (en el botón de la cabecera, que el panel tapa). Se apunta
                # porque es lo que decide hacia dónde tiene que ir el paseo, y porque es una molestia real
                # para quien navega con el teclado.
                hacia_atras = (teclado.get("foco") or {}).get("accion") == "menu-abrir"
                hallazgo(
                    f"{ancho} px: al abrir el menú con Enter, el foco se queda en "
                    f"«{(teclado.get('foco') or {}).get('accion') or (teclado.get('foco') or {}).get('texto')}», "
                    f"que está en la cabecera: el panel lo tapa, y para entrar en él hay que dar la vuelta a "
                    f"la página con el tabulador (se ha medido así y el paseo va hacia atrás para entrar "
                    f"por el final del armazón)"
                )
                # Y con Escape: el panel tapa la pantalla, así que tiene que poder cerrarse con la tecla
                # (el programa lo tiene en su lista de lo que cierra Escape).
                nav.tecla("Escape")
                time.sleep(0.35)
                tras_escape = la_medida(nav, etiquetas, ids)
                comprobar(
                    int(tras_escape["visibles"]) == 0,
                    f"{ancho} px: Escape cierra el menú (se ven {tras_escape['visibles']} renglones)",
                )
                # Se vuelve a abrir con el teclado (el foco sigue donde estaba): los grupos y los paseos se
                # miden con el menú a la vista.
                teclado = abrir_el_menu_con_el_teclado(nav)
                if not teclado["llego"]:
                    comprobar(False, f"{ancho} px: se vuelve a llegar al botón del menú tabulando")
                    return
                nav.esperar(CUENTAS_A_LA_VISTA, segundos=5)
    else:
        hallazgo(
            f"{ancho} px: a este ancho el menú sale solo, sin pulsar nada ({visibles} renglones): es el menú "
            f"lateral del ordenador, así que no hay estado «cerrado» que comprobar. La comprobación de «con "
            f"el menú cerrado no se ve ningún renglón» solo se puede hacer por debajo de 64 rem (1024 px)"
        )
        if medida["abrir"]["visible"]:
            hallazgo(f"{ancho} px: el botón de abrir el menú se ve en el ordenador, donde el menú ya está abierto")

    # --- los cinco grupos, con los nombres del servidor -----------------------
    faltan_nombres = [
        etiqueta for etiqueta in etiquetas if not medida["cabeceras"].get(etiqueta, {}).get("cuantas")
    ]
    comprobar(
        faltan_nombres == [],
        f"{ancho} px: los {len(etiquetas)} grupos salen con su nombre (los del servidor) — "
        f"sin nombre: {faltan_nombres or 'ninguno'}",
    )
    sin_ver = [
        etiqueta
        for etiqueta in etiquetas
        if medida["cabeceras"].get(etiqueta, {}).get("cuantas")
        and not medida["cabeceras"][etiqueta]["visible"]
    ]
    comprobar(
        sin_ver == [],
        f"{ancho} px: los nombres de los grupos se ven, no solo están en el documento — ocultos: "
        f"{sin_ver or 'ninguno'}",
    )

    # --- todos los renglones, dentro de su grupo ------------------------------
    esperado = {
        f"menu-{renglon['clave']}": nombres.get(renglon["grupo"], "") for renglon in renglones
    }
    sueltos = [identificador for identificador, suyo in esperado.items() if not suyo]
    if sueltos:
        sin_poder_comprobar(f"{ancho} px: estos renglones no dicen su grupo en `app.js`: {sueltos}")
    mal_colgados = [
        identificador
        for identificador, suyo in esperado.items()
        if suyo and medida["por_anidamiento"].get(identificador) != suyo
    ]
    comprobar(
        mal_colgados == [],
        f"{ancho} px: cada renglón está dentro de su grupo — mal colgados: "
        f"{[(uno, medida['por_anidamiento'].get(uno)) for uno in mal_colgados] or 'ninguno'}",
    )
    if mal_colgados:
        solo_por_posicion = [
            identificador
            for identificador in mal_colgados
            if medida["por_posicion"].get(identificador) == esperado[identificador]
        ]
        if solo_por_posicion:
            hallazgo(
                f"{ancho} px: {len(solo_por_posicion)} renglones están agrupados **solo por posición** (el "
                f"rótulo del grupo va antes que ellos, pero no los contiene): {solo_por_posicion}"
            )

    # --- los paseos con el teclado --------------------------------------------
    el_paseo_por_los_renglones(nav, ancho, hacia_atras)
    # El paseo hasta las cuentas se hace **desde cero** (recarga y se vuelve a abrir el menú) para que el
    # punto de partida sea el mismo y el número de pulsaciones signifique algo.
    if not entrar_en_el_navegador(nav, direccion, datos):
        return
    esperar_la_pantalla(nav)
    if hay_que_abrirlo:
        teclado = abrir_el_menu_con_el_teclado(nav)
        if not teclado["llego"]:
            comprobar(False, f"{ancho} px: se vuelve a llegar al botón del menú tabulando")
            return
        nav.esperar(CUENTAS_A_LA_VISTA, segundos=5)
    el_paseo_hasta_cuentas(nav, ancho, hacia_atras, en_el_movil=hay_que_abrirlo)


def el_paseo_por_los_renglones(nav: NavegadorDeVerdad, ancho: int, hacia_atras: bool) -> None:
    """Tabulando, se pasa por **los 21 renglones**: ningún renglón se queda sin poder alcanzar con el teclado."""
    paseo = pasear(nav, hacia_atras=hacia_atras)
    print(f"    (paseo por los renglones: {el_resumen_del_paseo(paseo, hacia_atras)})")
    comprobar(
        len(paseo["vistos"]) == 21,
        f"{ancho} px: tabulando se pasa por los 21 renglones del menú "
        f"(se ha pasado por {len(paseo['vistos'])}: {paseo['vistos']}), salida «{paseo['salida']}»",
    )


def el_paseo_hasta_cuentas(
    nav: NavegadorDeVerdad, ancho: int, hacia_atras: bool, *, en_el_movil: bool
) -> None:
    """Tabulando de verdad, hasta el renglón de las cuentas; y Enter abre «Mis cuentas».

    Es lo que demuestran las dos cosas del encargo a la vez: que **se puede navegar por el menú con el
    teclado** (no solo escribiendo la dirección) y que la agrupación **no ha metido una pantalla
    intermedia**: al pulsar Enter en el renglón se abre la pantalla de las cuentas, no un grupo.
    """
    paseo = pasear(nav, hacia_atras=hacia_atras, parar_en="menu-cuentas", maximo=200)
    print(f"    (paseo hasta las cuentas: {el_resumen_del_paseo(paseo, hacia_atras)})")
    llego = paseo["salida"] == "encontrado"
    comprobar(
        llego,
        f"{ancho} px: se llega al renglón de las cuentas tabulando "
        f"({len(paseo['secuencia'])} pulsaciones, salida «{paseo['salida']}»)",
    )
    if not llego:
        return
    print("  · Enter en el renglón de las cuentas")
    pulsar_enter(nav)
    esperar_la_pantalla(nav)
    comprobar(
        bool(
            nav.esperar(
                "document.querySelector('#pantalla h1') !== null && "
                "document.querySelector('#pantalla h1').textContent.indexOf('Mis cuentas') === 0",
                segundos=15,
            )
        ),
        f"{ancho} px: Enter en el renglón abre «Mis cuentas» (sin ninguna pantalla de grupo por medio)",
    )
    if en_el_movil:
        # Al abrir una pantalla desde el panel, el panel tiene que apartarse: si se quedara encima, el
        # agricultor no vería lo que acaba de abrir. No es un fallo del contrato (no lo pide), así que se
        # apunta como hallazgo.
        abierto = nav.evaluar(
            """(() => {
              const marco = document.getElementById("marco");
              if (!marco) return false;
              const visible = (el) => !!(el && el.checkVisibility &&
                el.checkVisibility({checkVisibilityCSS: true, checkOpacity: true}));
              return [...marco.querySelectorAll("button[id^='menu-']")].some(visible);
            })()"""
        )
        if abierto:
            hallazgo(
                f"{ancho} px: al abrir «Mis cuentas» desde el menú, el panel se queda abierto encima de la "
                f"pantalla: el agricultor no ve lo que acaba de abrir hasta que lo cierra"
            )


# ---------------------------------------------------------------------------
# Sin sesión: no hay menú de negocio
# ---------------------------------------------------------------------------


def sin_sesion(nav: NavegadorDeVerdad, direccion: str) -> None:
    """La pantalla de entrar: ni un renglón de negocio, y una dirección de dentro no abre una ficha."""
    titulo("== Sin sesión: la pantalla de entrar ==")
    nav.medir(1440, 900)
    nav.evaluar("localStorage.removeItem('cuedigital.token')")
    abrir_de_verdad(nav, f"{direccion}/#/")
    comprobar(
        bool(nav.esperar("document.getElementById('correo') !== null", segundos=15)),
        "sin sesión se abre la pantalla de entrar",
    )
    esperar_la_pantalla(nav)
    datos = nav.evaluar(LA_ENTRADA) or {}
    comprobar(
        int(datos.get("filas_visibles", -1)) == 0,
        f"en la pantalla de entrar no se ve ni un renglón de menú (se ven {datos.get('filas_visibles')})",
    )
    comprobar(
        int(datos.get("filas_en_el_documento", -1)) == 0,
        f"en la pantalla de entrar no hay ni un renglón de menú en el documento "
        f"(hay {datos.get('filas_en_el_documento')}): el armazón no se pinta sin sesión",
    )
    if datos.get("abrir_visible"):
        hallazgo(
            "en la pantalla de entrar se ve el botón de abrir el menú, y no hay ningún menú de negocio que "
            "abrir: el agricultor lo pulsa y no pasa nada (o se abre un panel vacío)"
        )
    # Y una dirección de dentro, escrita como la escribe la barra del navegador: no puede abrir una ficha.
    nav.abrir(f"{direccion}/#/cuentas")
    time.sleep(1.5)
    dentro = nav.evaluar(LA_ENTRADA) or {}
    abierto = not dentro.get("hay_entrada") and (
        bool(str(dentro.get("h1") or "").strip()) or int(dentro.get("controles", 0)) > 0
    )
    comprobar(
        not abierto,
        "una dirección de dentro con la sesión cerrada no abre una ficha "
        f"(se ve «{dentro.get('h1') or 'la pantalla de entrar'}», {dentro.get('controles')} controles)",
    )
    if abierto:
        hallazgo(
            f"escribir `#/cuentas` con la sesión cerrada pinta la pantalla («{dentro.get('h1')}», "
            f"{dentro.get('controles')} controles): es el mismo hallazgo que ya está apuntado en "
            f"`comprobar_teclado_y_zoom.py` («escribir una dirección de dentro con la sesión cerrada pinta la "
            f"pantalla igual»)"
        )


# ---------------------------------------------------------------------------
# Lo que se hace al ejecutarlo
# ---------------------------------------------------------------------------


def main() -> int:
    analizador = argparse.ArgumentParser(description="El armazón nuevo, en un navegador de verdad.")
    analizador.add_argument(
        "direccion", nargs="?", default="http://127.0.0.1:8027", help="dónde está el servidor de pruebas"
    )
    analizador.add_argument(
        "--romper",
        choices=["selector", "renglon", "grupo"],
        default=None,
        help="rompe a propósito una comprobación (solo en este guion, no toca ningún fichero)",
    )
    analizador.add_argument("--anchos", default="", help="solo estos anchos, separados por comas")
    argumentos = analizador.parse_args()

    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("El armazón nuevo (el menú agrupado), en un navegador de verdad. Servidor:", argumentos.direccion)
    print(f"(romper a propósito: {argumentos.romper or 'no'})")

    codigo = APP.read_text(encoding="utf-8")
    renglones = los_renglones_del_menu(codigo)
    grupos = los_grupos_del_menu(codigo)
    print(f"La tabla de `app.js`: {len(renglones)} renglones y {len(grupos)} grupos")

    try:
        datos = sembrar_la_cuenta(argumentos.direccion)
    except Exception as fallo:  # noqa: BLE001
        print(f"No se ha podido preparar la prueba en {argumentos.direccion}: {fallo}")
        print("¿Está el servidor de pruebas levantado con una base que se pueda ensuciar?")
        return 2
    print(f"Cuenta de la prueba: {datos['correo']}")

    nombres = {grupo["clave"]: el_nombre_del_grupo(datos["interfaz"], grupo) for grupo in grupos}
    sin_nombre = [clave for clave, nombre in nombres.items() if not nombre]
    titulo("== Los textos de los grupos, en el servidor ==")
    comprobar(
        sin_nombre == [],
        f"el servidor manda el nombre de los {len(grupos)} grupos (`textos.MENU`) — "
        f"sin nombre: {sin_nombre or 'ninguno'}",
    )
    if nombres:
        print(f"  (los nombres: {list(nombres.values())})")

    anchos = ANCHOS
    if argumentos.anchos:
        anchos = tuple(int(uno) for uno in argumentos.anchos.split(",") if uno.strip())

    try:
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            for ancho in anchos:
                comprobar_un_ancho(
                    nav,
                    argumentos.direccion,
                    datos,
                    ancho,
                    renglones,
                    grupos,
                    nombres,
                    romper=argumentos.romper,
                )
            sin_sesion(nav, argumentos.direccion)
    except SinNavegador as fallo:
        print(f"\n{fallo}")
        print("Sin navegador no se puede comprobar el menú de verdad: la comprobación queda SIN HACER.")
        return 2

    titulo("== Resumen ==")
    if HALLAZGOS:
        distintos = list(dict.fromkeys(HALLAZGOS))
        print(f"Hallazgos: {len(HALLAZGOS)} medidas, {len(distintos)} distintos")
        for uno in distintos:
            print(f"  · {uno}")
    if NO_COMPROBADO:
        print(f"\nSin poder comprobar ({len(NO_COMPROBADO)}):")
        for uno in dict.fromkeys(NO_COMPROBADO):
            print(f"  · {uno}")
    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for uno in FALLOS:
        print(f"  [FALLO] {uno}")
    if argumentos.romper:
        print(
            f"\n(Se ha roto «{argumentos.romper}» a propósito: si esa comprobación no aparece entre los "
            f"fallos, es que no está midiendo lo que dice medir.)"
        )
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
