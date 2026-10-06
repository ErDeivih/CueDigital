"""El teclado y el zoom, **de verdad**.

## Por qué existe este fichero

`comprobar_en_un_navegador.py` abre Chrome con `--dump-dom` y comprueba, entre otras cosas, **el ancho de
720 px**: el ancho al que equivale una ventana de 1440 px con el zoom al 200 %. Su propio comentario lo dice
con honestidad: *«No es el zoom de verdad —eso solo lo prueba un navegador con la ampliación puesta—»*. Eso
es una comprobación de **adaptación de pantalla** y sigue valiendo; lo que no es es una prueba de zoom, y
**este fichero es el que hace la de zoom**.

Tampoco se puede pulsar el teclado con un `--dump-dom`: un `KeyboardEvent` inventado con `dispatchEvent` no
mueve el foco (quien lo mueve es el navegador, y solo obedece a una tecla de verdad). Aquí se usa
`navegador_cdp.py`, que habla con Chrome por el **protocolo de depuración (CDP)** y manda teclas de verdad.

## Qué comprueba, y con qué

1. **El recorrido, entero y con el teclado**: entrar escribiendo, abrir una ficha, corregirla tecleando,
   guardar, abrir y cerrar la pregunta de anular (el «diálogo» de esta aplicación) y volver. En **cada
   paso** se mira **quién tiene el foco**, y lo que se guarda se comprueba además **en el servidor**.
2. **El foco visible**: se mide con `getComputedStyle` en el elemento que tiene el foco (contorno, sombra o
   borde). No vale «el navegador ya lo hace»: se mide.
3. **El orden de navegación**: se tabula desde el principio, se apunta la secuencia entera y se comprueba
   que va del armazón a la pantalla y de ahí al contenido, que **no hay ningún sitio del que no se pueda
   salir** (la secuencia se cierra en anillo) y que con Mayús+Tab se recorre al revés.
4. **Los controles accesibles**: se cuentan los `button`, `a`, `input`, `select` y `textarea` de cada
   pantalla y se comprueba que **todos** tienen nombre accesible (texto, `aria-label`, `title` o su
   etiqueta) y que **ninguno** lleva `tabindex="-1"`.
5. **El zoom, en sus dos formas, que NO son la misma cosa**:
   · la **escala del dispositivo** al 200 % (`--force-device-scale-factor=2`, que es lo que hace Windows al
     poner la pantalla al 200 %): `window.devicePixelRatio === 2` y el ancho lógico **no** cambia;
   · el **zoom de página** (el de Ctrl+«+», con la tecla de verdad): reduce los píxeles lógicos que caben
     en la ventana, y además se comprueba que la pantalla **no se sale** de lo que cabe
     (`scrollWidth <= clientWidth`).
   Y se separa de las dos el **pellizco** (`Emulation.setPageScaleFactor`), que tampoco es el zoom de
   página: acerca la imagen sin recomponer la pantalla.

## Cómo se lanza

```powershell
cd backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\\cd-teclado.db"
..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8022     # en otra terminal
..\\.venv\\Scripts\\python.exe scripts\\comprobar_teclado_y_zoom.py http://127.0.0.1:8022
```

Necesita un servidor de verdad con una base que se pueda ensuciar (crea una cuenta y le mete datos). **No
es un test**: los tests no levantan navegadores.

## Las comprobaciones tienen que poder fallar

`--romper outline` quita el contorno del foco en la página y `--romper nombre` deja un botón sin nombre
accesible (las dos cosas **solo en el navegador**: no se toca ningún fichero). Sirve para ver el fallo y
para saber que la comprobación no está pasando por casualidad.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

from navegador_cdp import NavegadorDeVerdad, SinNavegador  # noqa: E402

# ---------------------------------------------------------------------------
# La cuenta, el contador y lo que se va apuntando
# ---------------------------------------------------------------------------

COMPROBACIONES = 0
FALLOS: list[str] = []
HALLAZGOS: list[str] = []
RECORRIDOS: list[tuple[str, str, str]] = []  # (etiqueta, dónde acabó, por dónde pasó)


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


def titulo(texto: str) -> None:
    print(f"\n{texto}")


# ---------------------------------------------------------------------------
# El JavaScript que se le pregunta al navegador
# ---------------------------------------------------------------------------
#
# Va en constantes y no en una cadena suelta porque cada uno se usa desde varios sitios, y porque lo que
# mide cada uno está escrito aquí al lado (que es la mitad de que la medida valga algo).

FOCO = r"""
(() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) {
    return {cuerpo: true, clave: "BODY", quien: "BODY", etiqueta: "", region: "fuera", caja: "", visible: true};
  }
  const c = el.getBoundingClientRect();
  const texto = (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40);
  const visible = el.checkVisibility ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) : true;
  const accion = (el.dataset && el.dataset.accion) || "";
  return {
    cuerpo: false,
    clave: el.tagName + "|" + (el.id || "") + "|" + accion + "|" + texto,
    quien: el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (accion ? "[" + accion + "]" : ""),
    etiqueta: texto,
    region: el.closest("#pantalla") ? "pantalla" : (el.closest("#marco, .marco, header.cabecera") ? "armazon" : "fuera"),
    caja: Math.round(c.left) + "," + Math.round(c.top) + " " + Math.round(c.width) + "x" + Math.round(c.height),
    visible: visible,
  };
})()
"""

# El estilo del foco, medido **en el elemento que tiene el foco**. `outline-style: auto` es el contorno que
# pinta el navegador por su cuenta, y se dice: de ese no se puede saber de qué color se ve de verdad.
# El estilo del foco, medido **en el elemento que tiene el foco** y comparado con **el mismo elemento sin
# el foco** (un clon fuera de la pantalla). Sin esa comparación, un borde de siempre —que está con foco y
# sin él— pasaría por señal de foco, y la comprobación diría que se ve algo que no cambia. Se dice **qué**
# cambia (contorno, sombra, borde, fondo o letra), porque «hay algo» no es una medida.
#
# `outline-style: auto` es el contorno que pinta el navegador por su cuenta, y se dice: de ese no se puede
# saber de qué color se ve de verdad (por eso su contraste no se calcula).
ESTILO_DEL_FOCO = r"""
(() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  const e = getComputedStyle(el);
  const clon = el.cloneNode(false);
  clon.removeAttribute("id");
  clon.style.position = "fixed";
  clon.style.left = "-10000px";
  clon.style.top = "0";
  clon.style.pointerEvents = "none";
  document.body.appendChild(clon);
  const sinFoco = getComputedStyle(clon);
  const cambia = [];
  if (e.outlineStyle !== sinFoco.outlineStyle || e.outlineWidth !== sinFoco.outlineWidth ||
      e.outlineColor !== sinFoco.outlineColor) cambia.push("contorno");
  if (e.boxShadow !== sinFoco.boxShadow) cambia.push("sombra");
  if (e.borderTopColor !== sinFoco.borderTopColor || e.borderTopWidth !== sinFoco.borderTopWidth ||
      e.borderTopStyle !== sinFoco.borderTopStyle) cambia.push("borde");
  if (e.backgroundColor !== sinFoco.backgroundColor) cambia.push("fondo");
  if (e.color !== sinFoco.color) cambia.push("letra");
  clon.remove();
  const accion = (el.dataset && el.dataset.accion) || "";
  // El color del contorno contra lo que hay detrás (el primer fondo que no sea transparente subiendo por el
  // árbol), con la razón de contraste de la WCAG, que es un número que se puede comparar.
  const luminancia = (color) => {
    const numeros = String(color).match(/\d+(\.\d+)?/g);
    if (!numeros || numeros.length < 3) return null;
    const partes = numeros.slice(0, 3).map((v) => Number(v) / 255).map((c) =>
      c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    return 0.2126 * partes[0] + 0.7152 * partes[1] + 0.0722 * partes[2];
  };
  let fondo = null;
  for (let nodo = el; nodo; nodo = nodo.parentElement) {
    const color = getComputedStyle(nodo).backgroundColor;
    if (color && color !== "transparent" && color !== "rgba(0, 0, 0, 0)") { fondo = color; break; }
  }
  const uno = luminancia(e.outlineColor);
  const otro = fondo ? luminancia(fondo) : null;
  const contraste = uno !== null && otro !== null
    ? Math.round(((Math.max(uno, otro) + 0.05) / (Math.min(uno, otro) + 0.05)) * 100) / 100
    : null;
  return {
    quien: el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (accion ? "[" + accion + "]" : ""),
    etiqueta: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 30),
    contorno: e.outlineStyle + " " + e.outlineWidth + " " + e.outlineColor,
    contornoAncho: e.outlineWidth,
    sombra: e.boxShadow,
    borde: e.borderTopWidth + " " + e.borderTopStyle + " " + e.borderTopColor,
    fondoDetras: fondo,
    contraste: contraste,
    cambia: cambia,
    seVe: cambia.length > 0,
    loPintaElNavegador: e.outlineStyle === "auto",
  };
})()
"""

# Los controles de la pantalla: cuántos hay, y cuáles no tienen nombre accesible.
#
# **La regla del nombre, dicha aquí**: `aria-label`, lo que apunte `aria-labelledby`, `title`, su
# `<label for>`, la etiqueta que lo envuelve, su propio texto, el `value` si es un botón de formulario y
# —lo último, y se apunta aparte porque es lo más flojo— el marcador (`placeholder`). Lo que no tenga nada
# de eso sale en la lista. Los que no se ven no se cuentan: un control escondido no es un control.
CONTROLES = r"""
(() => {
  const visible = (el) => (el.checkVisibility ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) : true);
  const nombreDe = (el) => {
    const aria = el.getAttribute("aria-label");
    if (aria && aria.trim()) return {por: "aria-label"};
    const porLabelledby = el.getAttribute("aria-labelledby");
    if (porLabelledby) {
      const texto = porLabelledby.split(/\s+/).map((id) => {
        const otro = document.getElementById(id);
        return otro ? otro.textContent : "";
      }).join(" ").trim();
      if (texto) return {por: "aria-labelledby"};
    }
    const title = el.getAttribute("title");
    if (title && title.trim()) return {por: "title"};
    if (el.id) {
      const suyo = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (suyo && suyo.textContent.trim()) return {por: "label[for]"};
    }
    const envuelto = el.closest("label");
    if (envuelto && envuelto.textContent.trim()) return {por: "label que lo envuelve"};
    if ((el.textContent || "").trim()) return {por: "texto"};
    if (el.tagName === "INPUT" && ["submit", "button", "reset"].includes(el.type) && el.value && el.value.trim()) {
      return {por: "value"};
    }
    const marcador = el.getAttribute("placeholder");
    if (marcador && marcador.trim()) return {por: "placeholder", flojo: true};
    return null;
  };
  const quien = (el) => el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") +
    ((el.dataset && el.dataset.accion) ? "[" + el.dataset.accion + "]" : "") + " «" +
    (el.textContent || el.value || "").replace(/\s+/g, " ").trim().slice(0, 24) + "»";
  const todos = [...document.querySelectorAll("button, a, input, select, textarea")];
  const visibles = todos.filter(visible);
  const sinNombre = [];
  const flojos = [];
  const conTabindexMenosUno = [];
  for (const el of visibles) {
    const suyo = nombreDe(el);
    if (!suyo) sinNombre.push(quien(el));
    else if (suyo.flojo) flojos.push(quien(el));
    if (el.getAttribute("tabindex") === "-1") conTabindexMenosUno.push(quien(el));
  }
  return {
    hay: todos.length,
    visibles: visibles.length,
    ocultos: todos.length - visibles.length,
    sinNombre: sinNombre,
    soloMarcador: flojos,
    conTabindexMenosUno: conTabindexMenosUno,
    deCadaClase: {
      button: visibles.filter((el) => el.tagName === "BUTTON").length,
      a: visibles.filter((el) => el.tagName === "A").length,
      input: visibles.filter((el) => el.tagName === "INPUT").length,
      select: visibles.filter((el) => el.tagName === "SELECT").length,
      textarea: visibles.filter((el) => el.tagName === "TEXTAREA").length,
    },
  };
})()
"""

# Lo que ocupa la pantalla, lo que cabe y con qué escala. Es la medida del zoom, la haga el que la haga.
ANCHO = r"""
(() => ({
  ocupa: document.documentElement.scrollWidth,
  cabe: document.documentElement.clientWidth,
  dpr: window.devicePixelRatio,
  innerWidth: window.innerWidth,
  escalaVisual: window.visualViewport ? window.visualViewport.scale : null,
}))()
"""

# La firma de una pantalla quieta: cuántos controles tiene (y cuántos se ven), cuánto texto y cuántos hijos
# el armazón. Se pide dos veces seguidas y, cuando coincide **y hay algo que tabular**, la pantalla ha dejado
# de pintarse. Lo de «y hay algo que tabular» es lo que evita dar por buena una pantalla a medio cargar: en
# el inicio de ordenador, mientras llega el panel de mando, el contenido no tiene ni un botón a la vista.
FIRMA = r"""
(() => {
  const p = document.querySelector("#pantalla");
  const m = document.querySelector("#marco");
  const visibles = (el) => (el.checkVisibility ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) : true);
  const dentro = p ? [...p.querySelectorAll("button, a, input, select, textarea")] : [];
  return {
    controles: p ? dentro.length : -1,
    visibles: dentro.filter(visibles).length,
    texto: p ? p.textContent.replace(/\s+/g, " ").trim().length : -1,
    marco: m ? m.children.length : -1,
    h1: p && p.querySelector("h1") ? p.querySelector("h1").textContent.slice(0, 40) : "",
  };
})()
"""


# ---------------------------------------------------------------------------
# Las teclas, de verdad
# ---------------------------------------------------------------------------


def pulsar_enter(nav: NavegadorDeVerdad) -> None:
    """Enter **de verdad**, el que activa el botón que tiene el foco.

    `navegador_cdp.tecla("Enter")` manda `rawKeyDown`, y con eso el navegador **no** activa el botón: se
    midió (el botón de entrar no hacía nada y no se entraba, con el token sin aparecer). Con `keyDown` y su
    texto (`\\r`) sí lo activa. La herramienta no se toca —no es de este guion—: la tecla que falta se manda
    desde aquí, que para eso `NavegadorDeVerdad` deja pedir órdenes sueltas.
    """
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


def abrir_de_verdad(nav: NavegadorDeVerdad, url: str) -> None:
    """Abre una dirección con una **carga de verdad**.

    Hace falta, y costó una vuelta verlo: `Page.navigate` a la misma ruta cambiando solo lo de después de la
    almohadilla (`#/`) es una navegación **dentro del mismo documento**. La página no se recarga,
    `estado.token` sigue vivo en memoria y la comprobación se cree que ha vuelto a empezar cuando no. Se
    pasa por `about:blank`, que obliga a cargar de nuevo (y de paso deja el foco donde lo deja el navegador
    al cargar, que es lo que se quiere medir).
    """
    nav.orden("Page.navigate", {"url": "about:blank"})
    time.sleep(0.15)
    nav.abrir(url)


def aplicar_zoom_de_pagina(nav: NavegadorDeVerdad, factor: float = 2.0, *, maximo: int = 8) -> int:
    """Amplía con **Ctrl+«=»**, que es el atajo de Chrome (el mismo que Ctrl+«+»).

    El zoom va por pasos (100 → 110 → 125 → 150 → 175 → 200), así que al 200 % hacen falta cinco
    pulsaciones. Devuelve cuántas se han necesitado.
    """
    comun = {
        "windowsVirtualKeyCode": 187,
        "nativeVirtualKeyCode": 187,
        "code": "Equal",
        "key": "=",
        "modifiers": 2,
        "text": "",
    }
    pulsaciones = 0
    while nav.evaluar("window.devicePixelRatio") < factor and pulsaciones < maximo:
        nav.orden("Input.dispatchKeyEvent", {"type": "rawKeyDown", **comun})
        nav.orden("Input.dispatchKeyEvent", {"type": "keyUp", **comun})
        pulsaciones += 1
        time.sleep(0.35)
    return pulsaciones


def poner_el_foco_al_principio(nav: NavegadorDeVerdad) -> bool:
    """Deja el foco en el cuerpo del documento, quitándolo de donde esté.

    `document.body.focus()` a secas no vale: el cuerpo no es enfocable, así que el navegador no mueve el
    foco. Con `tabindex="-1"` puesto un momento —y quitado en la misma línea, para no dejar rastro— el foco
    sí queda en el cuerpo. **Ojo: esto no basta para tabular «desde el principio»**, porque Chrome guarda
    cuál fue el último elemento con el foco y sigue desde ahí (medido: la secuencia empezaba por el
    contenido de la pantalla en vez de por el menú, que es el orden del HTML). Para eso hace falta cargar la
    pantalla de nuevo, y es lo que hace `el_orden_de_navegacion`.
    """
    return bool(
        nav.evaluar(
            """(() => {
              if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
              document.body.setAttribute('tabindex', '-1');
              document.body.focus();
              document.body.removeAttribute('tabindex');
              return document.activeElement === document.body;
            })()"""
        )
    )


def foco(nav: NavegadorDeVerdad) -> dict:
    return nav.evaluar(FOCO)


def esperar_la_pantalla(nav: NavegadorDeVerdad, *, segundos: float = 12.0) -> dict:
    """Espera a que la pantalla esté pintada **y quieta**, y devuelve su firma.

    Hace falta de verdad: React monta en dos tiempos, así que al cambiar de pantalla el contenedor se vacía
    y se vuelve a llenar. Tabulando justo en ese hueco, el orden que se mide es el de una pantalla a medias
    (costó una vuelta: el primer paseo empezó en la pantalla del error —un solo botón— y siguió por el menú
    recién montado, así que parecía que el orden era «pantalla y luego menú»).
    """
    firma_anterior = None
    iguales = 0
    firma: dict = {}
    limite = time.time() + segundos
    while time.time() < limite:
        firma = nav.evaluar(FIRMA) or {}
        if firma == firma_anterior and int(firma.get("visibles", 0)) >= 1:
            iguales += 1
            if iguales >= 2:
                return firma
        else:
            iguales = 0
        firma_anterior = firma
        time.sleep(0.25)
    return firma


def tabular_hasta(nav: NavegadorDeVerdad, condicion: str, *, maximo: int = 200, pasos: list | None = None) -> int | None:
    """Tabulación de verdad hasta que el foco esté donde se busca. Devuelve cuántas pulsaciones costó.

    `None` es «no se ha llegado», y eso es un fallo de la comprobación que lo pida: un paso que no encuentra
    su botón dejaría la comprobación en la pantalla anterior y la daría por buena.
    """
    for cuantas in range(maximo):
        if nav.evaluar(f"Boolean({condicion})"):
            return cuantas
        nav.tecla("Tab")
        if pasos is not None:
            pasos.append(foco(nav))
    return None


def condicion_de_accion(accion: str, *, en_la_pantalla: bool = True) -> str:
    dentro = " && document.activeElement.closest('#pantalla') !== null" if en_la_pantalla else ""
    return (
        "document.activeElement && document.activeElement.dataset && "
        f"document.activeElement.dataset.accion === {json.dumps(accion)}{dentro}"
    )


def condicion_de_id(identificador: str) -> str:
    return f"document.activeElement && document.activeElement.id === {json.dumps(identificador)}"


def hasta_accion(nav, accion, *, en_la_pantalla=True, maximo=200, pasos=None):
    return tabular_hasta(nav, condicion_de_accion(accion, en_la_pantalla=en_la_pantalla), maximo=maximo, pasos=pasos)


def hasta_id(nav, identificador, *, maximo=200, pasos=None):
    return tabular_hasta(nav, condicion_de_id(identificador), maximo=maximo, pasos=pasos)


def valor_de(nav: NavegadorDeVerdad, identificador: str) -> str | None:
    """Lo que hay escrito en un campo, o `None` si ese campo no está (que es un fallo de otro, no una caída)."""
    return nav.evaluar(
        f"""(() => {{
          const el = document.getElementById({json.dumps(identificador)});
          return el ? el.value : null;
        }})()"""
    )


def reemplazar_lo_escrito(nav: NavegadorDeVerdad, texto: str) -> None:
    """Borra lo que hubiera (con la tecla de borrar, una pulsación por letra) y escribe lo nuevo."""
    cuantas = len(nav.evaluar("(document.activeElement && document.activeElement.value) || ''"))
    for _ in range(cuantas):
        nav.tecla("Backspace")
    nav.escribir(texto)


# ---------------------------------------------------------------------------
# Las comprobaciones de una pantalla: foco visible, controles y orden
# ---------------------------------------------------------------------------


def romper_si_toca(nav: NavegadorDeVerdad, romper: str | None) -> None:
    """La rotura a propósito del contorno del foco, **solo dentro del navegador**.

    No se toca ningún fichero: se mete una hoja de estilos en la página. Sirve para ver el fallo de verdad y
    para saber que la comprobación no está pasando por casualidad (si con esto sigue en verde, no mide el
    contorno). Al repintar una pantalla, la hoja del `<head>` sigue puesta.
    """
    if romper != "outline":
        return
    nav.evaluar(
        """(() => {
          if (document.getElementById('rotura-del-foco')) return null;
          document.head.insertAdjacentHTML('beforeend',
            '<style id="rotura-del-foco">button, a, input, select, textarea {' +
            ' outline: none !important; box-shadow: none !important; }</style>');
          return null;
        })()"""
    )


def el_foco_se_ve(nav: NavegadorDeVerdad, donde: str, *, romper: str | None = None) -> dict | None:
    """Mide el estilo del foco **en el elemento que lo tiene** y comprueba que se ve."""
    romper_si_toca(nav, romper)
    estilo = nav.evaluar(ESTILO_DEL_FOCO)
    if not estilo:
        comprobar(False, f"{donde}: hay algo con el foco que medir (ahora mismo no hay nada)")
        return None
    comprobar(
        estilo["seVe"],
        f"{donde}: el foco se ve en {estilo['quien']} — cambia {estilo['cambia'] or 'nada'} "
        f"(contorno «{estilo['contorno']}», sombra «{estilo['sombra']}», borde «{estilo['borde']}»)",
    )
    if "contorno" in estilo["cambia"] and not estilo["loPintaElNavegador"] and estilo["contraste"] is not None:
        print(
            f"           (el contorno «{estilo['contorno']}» contra el fondo «{estilo['fondoDetras']}»: "
            f"razón de contraste {estilo['contraste']}:1)"
        )
    if estilo["loPintaElNavegador"] and estilo["cambia"] == ["contorno"]:
        hallazgo(
            f"{donde}: el único cambio del foco en {estilo['quien']} es el contorno que pinta el navegador "
            f"(`outline-style: auto`, {estilo['contornoAncho']}): la hoja de estilos de la aplicación no "
            f"declara nada para él (sí lo declara para los campos: `input:focus{{outline:4px solid "
            f"var(--foco)}}`). De un contorno `auto` no se puede saber de qué color se ve de verdad, así que "
            f"su contraste no se mide"
        )
    return estilo


def los_controles_de_la_pantalla(nav: NavegadorDeVerdad, donde: str, *, romper: str | None = None) -> dict:
    """Cuenta los controles de la pantalla y comprueba que todos tienen nombre y ninguno está vetado."""
    if romper == "nombre":
        # Rotura a propósito: se deja un botón sin ningún nombre accesible (solo en el navegador).
        nav.evaluar(
            """(() => {
              const el = document.querySelector('#pantalla button');
              if (el) { el.textContent = ''; el.removeAttribute('aria-label'); el.removeAttribute('title'); }
              return null;
            })()"""
        )
    datos = nav.evaluar(CONTROLES)
    de_cada = datos["deCadaClase"]
    comprobar(
        datos["sinNombre"] == [],
        f"{donde}: los {datos['visibles']} controles que se ven tienen nombre accesible "
        f"(botones {de_cada['button']}, enlaces {de_cada['a']}, campos {de_cada['input']}, "
        f"listas {de_cada['select']}, textos {de_cada['textarea']}) — sin nombre: "
        f"{datos['sinNombre'] or 'ninguno'}",
    )
    comprobar(
        datos["conTabindexMenosUno"] == [],
        f'{donde}: ningún control lleva tabindex="-1" — {datos["conTabindexMenosUno"] or "ninguno"}',
    )
    if datos["soloMarcador"]:
        hallazgo(
            f"{donde}: {len(datos['soloMarcador'])} control(es) solo tienen nombre por el marcador "
            f"(`placeholder`), que desaparece al escribir: {datos['soloMarcador']}"
        )
    return datos


def el_orden_de_navegacion(
    nav: NavegadorDeVerdad, donde: str, *, direccion_del_paseo: str, maximo: int = 90
) -> list[dict]:
    """Tabulando **desde el principio**: apunta la secuencia y comprueba el orden y que no haya trampas.

    «Desde el principio» quiere decir con la pantalla **recién cargada**, que es la única forma de que el
    navegador no siga desde el último elemento que tuvo el foco (ver `poner_el_foco_al_principio`). Por eso
    el paseo carga su dirección: si la secuencia empezara a media pantalla, el orden que se midiera no
    sería el de la pantalla, y la comprobación diría que el menú va después del contenido.
    """
    print(f"    (tabulando {donde}, desde el principio)")
    secuencia: list[dict] = []
    # **El paseo se repite si la pantalla se pinta a mitad.** Pasó de verdad: al recargar el inicio, la
    # primera lectura decía «quieta» cuando todavía no había llegado el panel de mando, y las tres primeras
    # pulsaciones de Tab se quedaban en el cuerpo (el foco no tenía a dónde ir). Un paseo así mide el orden
    # de una pantalla a medias, así que se detecta y se vuelve a empezar.
    for intento in (1, 2):
        abrir_de_verdad(nav, direccion_del_paseo)
        nav.esperar("document.querySelector('#pantalla') !== null", segundos=10)
        esperar_la_pantalla(nav)
        if intento == 1:
            comprobar(
                foco(nav)["cuerpo"],
                f"{donde}: el paseo empieza con el foco en el cuerpo, con la pantalla recién cargada",
            )
        secuencia = []
        for _ in range(maximo):
            nav.tecla("Tab")
            quien = foco(nav)
            if secuencia and quien["clave"] == secuencia[0]["clave"] and len(secuencia) > 3:
                secuencia.append(quien)
                break
            secuencia.append(quien)
        if sum(1 for uno in secuencia[:3] if uno["cuerpo"]) < 2:
            break
        print("    (la pantalla se ha pintado a mitad del paseo: se repite)")
    for numero, quien in enumerate(secuencia, start=1):
        print(f"      {numero:2d}. {quien['quien']:<34} «{quien['etiqueta'][:30]}»")

    claves = [uno["clave"] for uno in secuencia]
    # **Sin trampas**: si la secuencia vuelve al primero, se puede salir de todos y cada uno de los sitios
    # por los que pasa (el último lleva otra vez al primero). Si se agota el máximo sin cerrar el anillo,
    # hay un sitio del que no se sale.
    comprobar(
        len(secuencia) > 3 and claves[-1] == claves[0],
        f"{donde}: el tabulador recorre {len(claves) - 1} paradas y vuelve a la primera "
        f"(no hay ningún sitio del que no se pueda salir)",
    )
    repetidos = [i for i in range(1, len(claves)) if claves[i] == claves[i - 1]]
    comprobar(repetidos == [], f"{donde}: ninguna pulsación se queda en el mismo sitio — {repetidos or 'ninguna'}")
    # Las regiones: el armazón (el menú y la barra) primero, la pantalla después y el contenido dentro de
    # ella. Se cuentan los cambios de región y no puede haber más de dos, ni vueltas atrás.
    regiones = [uno["region"] for uno in secuencia if uno["region"] != "fuera"]
    cambios = [i for i in range(1, len(regiones)) if regiones[i] != regiones[i - 1]]
    comprobar(
        len(cambios) <= 2,
        f"{donde}: las regiones van seguidas, sin saltos ({' → '.join(dict.fromkeys(regiones))}; "
        f"{len(cambios)} cambios)",
    )
    # Y hacia atrás: Mayús+Tab recorre la misma lista al revés.
    delante = claves[:-1]
    poner_el_foco_al_principio(nav)
    detras: list[str] = []
    for _ in range(len(delante)):
        nav.tecla("Tab", mayusculas=True)
        detras.append(foco(nav)["clave"])
    comprobar(
        detras == list(reversed(delante)),
        f"{donde}: con Mayús+Tab se recorre la misma lista al revés",
    )
    return secuencia


def el_ancho_cabe(nav: NavegadorDeVerdad, donde: str) -> dict:
    """La pantalla no se sale de lo que cabe (la regla de `comprobar_en_un_navegador.py`, con +1 de redondeo)."""
    datos = nav.evaluar(ANCHO)
    comprobar(
        datos["ocupa"] <= datos["cabe"] + 1,
        f"{donde}: la pantalla no se sale de lo que cabe (ocupa {datos['ocupa']} de {datos['cabe']} px)",
    )
    return datos


# ---------------------------------------------------------------------------
# La cuenta y los datos de la prueba
# ---------------------------------------------------------------------------


def sembrar_la_prueba(direccion: str) -> dict:
    """Una cuenta con una tierra y un gasto, por la API (que es como se dan de alta de verdad).

    **Hace falta tener datos**: una lista vacía se ve bien aunque esté rota, y lo que hay que recorrer es una
    ficha con contenido dentro.
    """
    correo = f"teclado-{os.getpid()}@ejemplo.test"
    clave = "una-clave-larga"
    with httpx.Client(base_url=direccion, timeout=30.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba del teclado",
                "correo": correo,
                "clave": clave,
                "explotacion": {"nombre": "La finca de la prueba del teclado", "nif": "12345678Z"},
            },
        )
        respuesta.raise_for_status()
        token = respuesta.json()["token"]
        cabeceras = {"Authorization": f"Bearer {token}"}
        campana = cliente.get("/api/campanas/actual", headers=cabeceras).json()
        tierra = cliente.post(
            "/api/parcelas",
            headers=cabeceras,
            json={
                "alias": "El Prado",
                "ref_sigpac": "37-70-0-0-503-51",
                "municipio": "Calvarrasa de Arriba",
                "provincia": "Salamanca",
                "codigo_ine": "37070",
                "poligono": 503,
                "numero_parcela": 51,
                "numero_recinto": 1,
                "superficie_ha": 4.9,
                "uso_sigpac": "TA",
                "sistema": "secano",
            },
        )
        gasto = cliente.post(
            "/api/gastos",
            headers=cabeceras,
            json={
                "campana_id": campana["id"],
                "fecha": "2026-04-12",
                "concepto": "Gasóleo para el tractor",
                "categoria": "gasoleo",
                "proveedor": "Cooperativa Agrícola de Peñaranda",
                "importe": "254.10",
            },
        )
        if gasto.status_code != 201:
            raise RuntimeError(f"no se ha podido apuntar el gasto de la prueba: {gasto.status_code} {gasto.text}")
        return {
            "correo": correo,
            "clave": clave,
            "token": token,
            "campana_id": campana["id"],
            "tierra_id": tierra.json()["id"] if tierra.status_code == 201 else None,
            "gasto_id": gasto.json()["gasto"]["id"],
        }


def el_gasto_en_el_servidor(direccion: str, token: str, gasto_id: int) -> dict | None:
    """Lo que el servidor dice de ese gasto: es la prueba de que **se guardó de verdad**."""
    with httpx.Client(base_url=direccion, timeout=30.0, headers={"Authorization": f"Bearer {token}"}) as cliente:
        respuesta = cliente.get("/api/gastos")
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
        lista = cuerpo.get("gastos") if isinstance(cuerpo, dict) else cuerpo
        for uno in lista or []:
            if int(uno.get("id", 0)) == int(gasto_id):
                return uno
    return None


# ---------------------------------------------------------------------------
# El recorrido del encargo, tecla a tecla
# ---------------------------------------------------------------------------


def entrar_escribiendo(nav: NavegadorDeVerdad, datos: dict, etiqueta: str, *, romper: str | None = None) -> None:
    """Entrar en la aplicación **con el teclado**: se escribe el correo y la clave y se pulsa con Enter.

    Se entra por la dirección de verdad (`#/`, que es la que abre el agricultor). **No** se entra por
    `#/entrar`: se midió que esa dirección no está en la tabla de rutas y, después de entrar bien, deja al
    agricultor en la pantalla de «Esa dirección no lleva a ninguna parte» (ver `la_direccion_de_entrar`).
    """
    direccion = datos["direccion"]
    print("  · Entrar (se escribe el correo y la clave, y se pulsa con Enter)")
    abrir_de_verdad(nav, f"{direccion}/#/")
    comprobar(
        nav.esperar("document.querySelector('#correo') !== null && document.querySelector('#pantalla') !== null"),
        "la pantalla de entrar se abre (sin cuenta abierta)",
    )
    empezando = foco(nav)
    comprobar(empezando["cuerpo"], "al cargar, el foco está en el cuerpo del documento (donde lo deja el navegador)")
    nav.tecla("Tab")
    comprobar(not foco(nav)["cuerpo"], f"la primera tabulación mueve el foco ({foco(nav)['quien']})")

    cuantas = hasta_id(nav, "correo")
    comprobar(cuantas is not None, f"se llega al campo «Tu correo» tabulando ({cuantas} pulsaciones)")
    if cuantas is not None and cuantas > 15:
        hallazgo(
            f"en la pantalla de entrar hay que pulsar Tab {cuantas} veces para llegar al primer campo: el "
            f"armazón de escritorio (el menú de módulos, que el agricultor todavía no puede usar porque no ha "
            f"entrado) se tabula entero antes que el formulario"
        )
    el_foco_se_ve(nav, "el campo «Tu correo»", romper=romper)
    nav.escribir(datos["correo"])
    comprobar(
        valor_de(nav, "correo") == datos["correo"],
        "el correo se ha escrito en su campo (tecleado, no puesto por JavaScript)",
    )
    nav.tecla("Tab")
    comprobar(foco(nav)["quien"] == "input#clave", f"la siguiente tabulación lleva al campo de la clave ({foco(nav)['quien']})")
    nav.escribir(datos["clave"])
    cuantas = hasta_accion(nav, "entrar")
    comprobar(cuantas is not None, f"se llega al botón de entrar tabulando ({cuantas} pulsaciones más)")
    el_foco_se_ve(nav, "el botón de entrar", romper=romper)
    pulsar_enter(nav)
    esperar_la_pantalla(nav)
    comprobar(
        nav.esperar(
            "document.querySelector('#pantalla h1') && "
            "document.querySelector('#pantalla h1').textContent.indexOf('Hola') === 0",
            segundos=10,
        ),
        "Enter en el botón de entrar entra de verdad (y aparece la pantalla de inicio)",
    )
    comprobar(
        bool(nav.evaluar("localStorage.getItem('cuedigital.token')")),
        "la cuenta ha quedado abierta (hay token en el navegador)",
    )


def la_direccion_de_entrar(nav: NavegadorDeVerdad, datos: dict) -> None:
    """Dos cosas que se miden aquí y que no se ven en ningún otro sitio.

    1. **`#/entrar`**, que es la dirección que abren `comprobar_en_un_navegador.py` y `humo_cdp.py`: no está
       en la tabla de rutas de `rutas.js`. Se entra bien desde ella y se mira **qué ve el agricultor**.
    2. **Sin sesión**, ¿se pinta la pantalla? Se quita el token, se recarga (que sí vuelve a la pantalla de
       entrar) y después se navega a una dirección de dentro como lo haría la barra del navegador.
    """
    direccion = datos["direccion"]
    print("  · La dirección `#/entrar` (la que usan las comprobaciones del proyecto) y lo que se ve después")
    abrir_de_verdad(nav, f"{direccion}/#/entrar")
    nav.esperar("document.querySelector('#correo') !== null")
    hasta_id(nav, "correo")
    nav.escribir(datos["correo"])
    nav.tecla("Tab")
    nav.escribir(datos["clave"])
    hasta_accion(nav, "entrar")
    pulsar_enter(nav)
    time.sleep(2.0)
    texto = str(
        nav.evaluar(
            "document.querySelector('#pantalla') ? "
            "document.querySelector('#pantalla').textContent.replace(/\\s+/g, ' ').trim() : ''"
        )
    )
    comprobar(
        bool(nav.evaluar("localStorage.getItem('cuedigital.token')")),
        "entrando desde `#/entrar`, la cuenta se abre igual (el token queda guardado)",
    )
    if "no lleva a ninguna parte" in texto:
        hallazgo(
            "entrar desde la dirección `#/entrar` (la que abre `humo_cdp.py`, el humo de esta herramienta) "
            f"deja al agricultor en «{texto[:60]}…» aunque la cuenta se haya abierto: `entrar` no está en la "
            "tabla de rutas de `web/react/rutas.js`, así que la dirección no lleva a ninguna pantalla y la "
            "única salida es su botón de volver al principio. `comprobar_en_un_navegador.py` abre la "
            f"dirección pelada ({direccion}/) y por eso no le pasa"
        )
    else:
        print(f"  [OK   ] desde `#/entrar` se llega a una pantalla con contenido («{texto[:60]}»)")

    print("  · Y sin sesión: ¿vuelve la pantalla de entrar, o se pinta la pantalla igual?")
    nav.evaluar("localStorage.removeItem('cuedigital.token')")
    abrir_de_verdad(nav, f"{direccion}/#/")
    comprobar(
        nav.esperar("document.querySelector('#correo') !== null", segundos=10),
        "quitando la sesión y recargando de verdad, vuelve la pantalla de entrar",
    )
    # Y ahora una dirección de dentro, que es lo que pasa al escribirla en la barra del navegador (o al
    # recargar un enlace guardado): cambia solo lo de después de la almohadilla.
    nav.abrir(f"{direccion}/#/cuentas")
    time.sleep(1.5)
    sin_sesion = nav.evaluar(
        """(() => ({
          hayEntrada: Boolean(document.querySelector('#correo')),
          h1: document.querySelector('#pantalla h1') ? document.querySelector('#pantalla h1').textContent.slice(0, 50) : '',
          controles: document.querySelectorAll('#pantalla button, #pantalla input').length,
          menu: document.querySelectorAll('#marco .menu-lista > li').length,
          token: localStorage.getItem('cuedigital.token') ? 'SI' : 'NO',
        }))()"""
    )
    comprobar(
        sin_sesion["token"] == "NO",
        "y la sesión sigue sin abrirse (no hay token)",
    )
    if not sin_sesion["hayEntrada"] and sin_sesion["controles"] > 0:
        hallazgo(
            f"escribir una dirección de dentro (`#/cuentas`) con la sesión cerrada **pinta la pantalla igual** "
            f"(«{sin_sesion['h1']}», {sin_sesion['controles']} controles y {sin_sesion['menu']} renglones de "
            f"menú) en vez de mandar a la pantalla de entrar: el armazón y la pantalla se dibujan sin cuenta "
            f"abierta y los datos llegan vacíos (el servidor contesta que no)"
        )
    else:
        print("  [OK   ] con la sesión cerrada, una dirección de dentro no pinta la pantalla")
    # Se deja el navegador como estaba (sin cuenta abierta) para que el recorrido empiece de cero.
    nav.evaluar("localStorage.removeItem('cuedigital.token')")



def el_recorrido(
    nav: NavegadorDeVerdad,
    datos: dict,
    etiqueta: str,
    *,
    romper: str | None = None,
    ancho: bool = False,
    con_menu: bool = False,
    orden_del_inicio: bool = False,
    la_direccion_entrar: bool = False,
    zoom_de_pagina: bool = False,
) -> None:
    """Abrir ficha → completar formulario → guardar → cerrar el diálogo → volver. Todo con el teclado.

    Se ejecuta **entero en cada forma de zoom**: es lo que demuestra que el recorrido sigue funcionando al
    200 %, que es lo que pide el encargo.
    """
    direccion = datos["direccion"]
    concepto_nuevo = f"Gasóleo de la siega ({etiqueta})"
    importe_nuevo = "300,50"
    # **Cómo se llama hoy la ficha**, leído del servidor: el recorrido se repite tres veces (una por cada
    # forma de zoom) y cada pasada guarda su concepto, así que dar por hecho el del principio haría fallar
    # la segunda vuelta por un motivo que no es de la pantalla.
    anteriores = el_gasto_en_el_servidor(direccion, datos["token"], datos["gasto_id"]) or {}
    titulo_de_la_ficha = str(anteriores.get("concepto") or "Gasóleo para el tractor")

    titulo(f"== El recorrido con teclado · {etiqueta} ==")
    medidas = nav.evaluar(ANCHO)
    print(f"  (la ventana: {medidas.get('innerWidth')} px lógicos, devicePixelRatio {medidas.get('dpr')})")

    if la_direccion_entrar:
        la_direccion_de_entrar(nav, datos)

    if zoom_de_pagina:
        # Si la recarga se ha llevado el zoom por delante, se vuelve a poner: lo que se comprueba es el
        # recorrido **con el zoom puesto**, no que Chrome se acuerde de él.
        if nav.evaluar("window.devicePixelRatio") < 2:
            aplicar_zoom_de_pagina(nav)

    entrar_escribiendo(nav, datos, etiqueta, romper=romper)

    if orden_del_inicio:
        el_orden_de_navegacion(nav, "la pantalla de inicio", direccion_del_paseo=f"{direccion}/#/")
        los_controles_de_la_pantalla(nav, "la pantalla de inicio", romper=romper)

    # --- a la lista de cuentas ------------------------------------------------
    #
    # **En el ordenador se llega por el menú, tabulando** (que es lo que hace un agricultor con teclado).
    # A 712 px (el zoom del 200 %) el menú de módulos del armazón no se dibuja, así que se llega **por la
    # dirección de la pantalla**, que es la única puerta que queda a ese ancho; se mide y se dice.
    if con_menu:
        abrir_de_verdad(nav, f"{direccion}/#/")
        nav.esperar("document.querySelector('#pantalla h1') !== null")
        esperar_la_pantalla(nav)
        cuantas = hasta_accion(nav, "gastos-ver", en_la_pantalla=False)
        comprobar(
            cuantas is not None,
            f"«Mis cuentas» se alcanza con el teclado desde el inicio, por el renglón del menú "
            f"({cuantas} pulsaciones de Tab)",
        )
        if cuantas is not None:
            el_foco_se_ve(nav, "el renglón «Mis cuentas» del menú", romper=romper)
            pulsar_enter(nav)
            esperar_la_pantalla(nav)
    else:
        abrir_de_verdad(nav, f"{direccion}/#/cuentas")

    comprobar(
        nav.esperar("document.querySelector('[data-accion=\"gasto-abrir\"]') !== null", segundos=10),
        "la lista de cuentas se dibuja con la ficha del gasto dentro",
    )
    esperar_la_pantalla(nav)
    if ancho:
        el_ancho_cabe(nav, f"la lista de cuentas · {etiqueta}")
    los_controles_de_la_pantalla(nav, f"la lista de cuentas · {etiqueta}", romper=romper)
    el_orden_de_navegacion(nav, f"la lista de cuentas · {etiqueta}", direccion_del_paseo=f"{direccion}/#/cuentas")

    # --- abrir la ficha, con el teclado --------------------------------------
    print("  · Abrir la ficha (tabulando hasta su botón y pulsando Enter)")
    cuantas = hasta_accion(nav, "gasto-abrir")
    comprobar(cuantas is not None, f"se llega al botón de abrir la ficha tabulando ({cuantas} pulsaciones)")
    el_foco_se_ve(nav, "el botón de abrir la ficha", romper=romper)
    pulsar_enter(nav)
    esperar_la_pantalla(nav)
    comprobar(
        nav.esperar(
            "document.querySelector('#pantalla h1') && document.querySelector('#pantalla h1').textContent.indexOf("
            + json.dumps(titulo_de_la_ficha) + ") === 0",
            segundos=10,
        ),
        f"la ficha se abre, y es la del gasto que se ha sembrado («{titulo_de_la_ficha}»)",
    )
    if ancho:
        el_ancho_cabe(nav, f"la ficha del gasto · {etiqueta}")
    los_controles_de_la_pantalla(nav, f"la ficha del gasto · {etiqueta}", romper=romper)

    # --- completar el formulario, tecleando ----------------------------------
    print("  · Completar el formulario (CORREGIR y se escribe dentro de los campos)")
    cuantas = hasta_accion(nav, "gasto-nuevo")
    comprobar(cuantas is not None, f"se llega a CORREGIR tabulando ({cuantas} pulsaciones)")
    pulsar_enter(nav)
    comprobar(
        nav.esperar("document.querySelector('#gasto-concepto') !== null", segundos=10),
        "el formulario se abre con lo que ya estaba puesto",
    )
    cuantas = hasta_id(nav, "gasto-concepto")
    comprobar(cuantas is not None, f"se llega al campo del concepto tabulando ({cuantas} pulsaciones)")
    el_foco_se_ve(nav, "el campo del concepto", romper=romper)
    reemplazar_lo_escrito(nav, concepto_nuevo)
    comprobar(
        valor_de(nav, "gasto-concepto") == concepto_nuevo,
        f"el concepto se ha escrito tecleando («{concepto_nuevo}»)",
    )
    # **El orden del formulario, medido**: después del concepto viene la categoría (que son botones, no un
    # campo) y después el importe. Suponer que el siguiente Tab es el importe fue un fallo de esta
    # comprobación —el importe se escribía en el aire y acababa pegado al concepto—, así que aquí se tabula
    # **hasta el importe** y se apunta por dónde se pasa.
    paradas: list[dict] = []
    cuantas = hasta_id(nav, "gasto-importe", pasos=paradas)
    comprobar(
        cuantas is not None,
        f"se llega al campo del importe tabulando ({cuantas} pulsaciones, pasando por "
        f"{[uno['quien'] for uno in paradas] or 'nada'})",
    )
    if cuantas is not None:
        for numero, quien in enumerate(paradas, start=1):
            print(f"        Tab {numero}: {quien['quien']} «{quien['etiqueta'][:30]}»")
        el_foco_se_ve(nav, "el campo del importe", romper=romper)
        reemplazar_lo_escrito(nav, importe_nuevo)
        comprobar(
            valor_de(nav, "gasto-importe") == importe_nuevo,
            f"el importe se ha escrito tecleando («{importe_nuevo}»)",
        )
    los_controles_de_la_pantalla(nav, f"el formulario del gasto · {etiqueta}", romper=romper)

    # --- guardar --------------------------------------------------------------
    print("  · Guardar (Enter en su botón)")
    cuantas = hasta_accion(nav, "gasto-guardar")
    comprobar(cuantas is not None, f"se llega a GUARDAR tabulando ({cuantas} pulsaciones)")
    el_foco_se_ve(nav, "el botón de guardar", romper=romper)
    pulsar_enter(nav)
    comprobar(
        nav.esperar("document.querySelector('#gasto-concepto') === null", segundos=15),
        "al guardar, el formulario se cierra solo",
    )
    comprobar(
        nav.esperar(
            "document.querySelector('#pantalla h1') && document.querySelector('#pantalla h1').textContent.indexOf("
            + json.dumps(concepto_nuevo) + ") === 0",
            segundos=15,
        ),
        "la ficha vuelve con el concepto nuevo: el guardado llegó a la pantalla",
    )
    guardado = el_gasto_en_el_servidor(direccion, datos["token"], datos["gasto_id"])
    comprobar(guardado is not None, "el gasto sigue en el servidor")
    comprobar(
        bool(guardado) and str(guardado.get("concepto")) == concepto_nuevo,
        f"el servidor tiene el concepto nuevo ({guardado.get('concepto') if guardado else 'no se ha leído'})",
    )
    try:
        importe_leido = float(str((guardado or {}).get("importe", "0")).replace(",", "."))
    except ValueError:
        importe_leido = 0.0
    comprobar(
        abs(importe_leido - 300.50) < 0.01,
        f"el servidor tiene el importe nuevo ({importe_leido} €)",
    )

    # --- el diálogo: la pregunta de anular -----------------------------------
    print("  · El diálogo (la pregunta de anular): Escape y su propio botón")
    cuantas = hasta_accion(nav, "gasto-anular")
    comprobar(cuantas is not None, f"se llega a ANULAR tabulando ({cuantas} pulsaciones)")
    pulsar_enter(nav)
    comprobar(
        nav.esperar("document.querySelector('[data-accion=\"gasto-cancelar\"]') !== null", segundos=10),
        "la pregunta se abre (con su motivo, su botón de confirmar y su cancelar)",
    )
    nav.tecla("Escape")
    sigue_abierta = bool(nav.evaluar("Boolean(document.querySelector('[data-accion=\"gasto-cancelar\"]'))"))
    comprobar(
        sigue_abierta,
        "Escape **no** cierra la pregunta: la aplicación no escucha el teclado (no hay ni un `keydown` en "
        "`web/`), así que la única salida es su botón",
    )
    if sigue_abierta:
        hallazgo(
            "cerrar la pregunta de anular con Escape no funciona: la aplicación no tiene ningún manejador de "
            "teclado, así que quien va con el teclado tiene que tabular hasta CANCELAR"
        )
    cuantas = hasta_accion(nav, "gasto-cancelar")
    comprobar(cuantas is not None, f"se llega a CANCELAR tabulando ({cuantas} pulsaciones)")
    pulsar_enter(nav)
    comprobar(
        nav.esperar("document.querySelector('[data-accion=\"gasto-cancelar\"]') === null", segundos=10),
        "su botón sí cierra la pregunta",
    )
    sin_anular = el_gasto_en_el_servidor(direccion, datos["token"], datos["gasto_id"])
    comprobar(
        bool(sin_anular) and not sin_anular.get("anulado"),
        "y no se ha anulado nada: el gasto sigue vivo en el cuaderno",
    )

    # --- volver ---------------------------------------------------------------
    print("  · Volver (con el teclado)")
    cuantas = hasta_accion(nav, "gastos-ver")
    comprobar(cuantas is not None, f"se llega a VOLVER tabulando ({cuantas} pulsaciones)")
    pulsar_enter(nav)
    comprobar(
        nav.esperar("document.querySelector('[data-accion=\"gasto-abrir\"]') !== null", segundos=10),
        "se vuelve a la lista de cuentas",
    )
    donde_acabo_la_lista = str(nav.evaluar("location.hash"))
    cuantas = hasta_accion(nav, "ir-inicio")
    comprobar(cuantas is not None, f"y de la lista se vuelve al inicio tabulando ({cuantas} pulsaciones)")
    pulsar_enter(nav)
    comprobar(
        nav.esperar("document.querySelector('#pantalla h1') && document.querySelector('#pantalla h1').textContent.indexOf('Hola') === 0", segundos=10),
        "el recorrido acaba en el inicio, que es donde empieza",
    )
    donde_acabo = str(nav.evaluar("location.hash"))
    RECORRIDOS.append((etiqueta, donde_acabo, f"entrar → {'menú → ' if con_menu else 'dirección → '}lista ({donde_acabo_la_lista}) → ficha → formulario → guardado → pregunta de anular → lista → inicio"))
    print(f"    dirección en la que acabó el recorrido: {donde_acabo or '(sin hash)'}")


# ---------------------------------------------------------------------------
# El zoom, en sus dos formas (que no son la misma)
# ---------------------------------------------------------------------------


def la_escala_del_dispositivo_al_200(direccion: str, datos: dict, romper: str | None) -> None:
    """La pantalla de Windows al 200 %: **desde el arranque del navegador**, que es como pasa de verdad."""
    titulo("== La escala del dispositivo al 200 % (`--force-device-scale-factor=2`) ==")
    print("  (el navegador se abre ya con la escala puesta, como la pantalla de Windows al 200 %)")
    with NavegadorDeVerdad(ancho=1440, alto=900, escala=2.0) as nav:
        abrir_de_verdad(nav, f"{direccion}/#/")
        nav.esperar("document.querySelector('#pantalla') !== null")
        medidas = nav.evaluar(ANCHO)
        comprobar(
            abs(medidas["dpr"] - 2.0) < 0.01,
            f"`window.devicePixelRatio` es 2 (medido: {medidas['dpr']})",
        )
        comprobar(
            medidas["innerWidth"] > 1024,
            f"y el ancho lógico **no** cambia: la ventana sigue viendo {medidas['innerWidth']} px de CSS "
            f"(el armazón de ordenador sigue saliendo)",
        )
        comprobar(
            bool(
                nav.evaluar(
                    "Boolean(document.getElementById('menu-cuentas')) && "
                    "document.getElementById('menu-cuentas').checkVisibility({checkVisibilityCSS: true})"
                )
            ),
            "el menú de módulos del ordenador sigue dibujado (y por tanto tabulable) a esta escala",
        )
        el_recorrido(nav, {**datos, "direccion": direccion}, "escala del dispositivo 2 (1440 px lógicos)", romper=romper, ancho=True, con_menu=True)


def el_zoom_de_pagina_al_200(direccion: str, datos: dict, romper: str | None) -> None:
    """El zoom de Ctrl+«+», con la tecla de verdad: reduce los píxeles lógicos que caben en la ventana."""
    titulo("== El zoom de página al 200 % (Ctrl+«+», tecla de verdad) ==")
    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        abrir_de_verdad(nav, f"{direccion}/#/")
        nav.esperar("document.querySelector('#correo') !== null || document.querySelector('#pantalla') !== null")
        antes = nav.evaluar(ANCHO)
        print(f"  antes del zoom: devicePixelRatio {antes['dpr']}, ventana {antes['innerWidth']} px lógicos")
        # Ctrl+«=» es el atajo de ampliar de Chrome (el mismo que Ctrl+«+»). El zoom va por pasos:
        # 100 → 110 → 125 → 150 → 175 → 200, así que hacen falta cinco pulsaciones.
        pulsaciones = aplicar_zoom_de_pagina(nav)
        despues = nav.evaluar(ANCHO)
        print(
            f"  tras {pulsaciones} pulsaciones de Ctrl+«=»: devicePixelRatio {despues['dpr']}, ventana "
            f"{despues['innerWidth']} px lógicos, escala visual {despues['escalaVisual']}"
        )
        comprobar(
            abs(despues["dpr"] - 2.0) < 0.01 and pulsaciones > 0,
            f"el zoom de página llega al 200 % con la tecla de verdad ({pulsaciones} pulsaciones; "
            f"devicePixelRatio {despues['dpr']})",
        )
        comprobar(
            despues["innerWidth"] < antes["innerWidth"] / 1.9,
            f"y **reduce los píxeles lógicos que caben**: de {antes['innerWidth']} a {despues['innerWidth']} px",
        )
        comprobar(
            despues["ocupa"] <= despues["cabe"] + 1,
            f"y la pantalla no se sale de lo que cabe (ocupa {despues['ocupa']} de {despues['cabe']} px)",
        )
        # Esto es lo que **no** es el zoom de página: el pellizco.
        nav.zoom(2.0)
        pellizco = nav.evaluar(ANCHO)
        print(
            f"  y el pellizco (`Emulation.setPageScaleFactor`, que es lo que usa `navegador_cdp.zoom`) deja: "
            f"devicePixelRatio {pellizco['dpr']}, ventana {pellizco['innerWidth']} px lógicos, escala visual "
            f"{pellizco['escalaVisual']}"
        )
        comprobar(
            pellizco["innerWidth"] == despues["innerWidth"],
            "el pellizco **no** cambia los píxeles lógicos que caben (por eso no es el zoom de página: acerca "
            "la imagen, no recompone la pantalla)",
        )
        nav.zoom(1.0)
        # Y ahora el recorrido, con el zoom de página puesto (al recargar, Chrome lo mantiene).
        el_recorrido(
            nav,
            {**datos, "direccion": direccion},
            "zoom de página 2 (712 px lógicos)",
            romper=romper,
            ancho=True,
            con_menu=False,
            orden_del_inicio=True,
            zoom_de_pagina=True,
        )
        # Y lo que se mide aquí y no en la escala del dispositivo: el menú de módulos.
        abrir_de_verdad(nav, f"{direccion}/#/")
        nav.esperar("document.querySelector('#pantalla h1') !== null")
        esperar_la_pantalla(nav)
        visible_el_menu = bool(
            nav.evaluar(
                "Boolean(document.getElementById('menu-cuentas')) && "
                "document.getElementById('menu-cuentas').checkVisibility({checkVisibilityCSS: true})"
            )
        )
        comprobar(
            not visible_el_menu,
            "a 712 px el menú de módulos del ordenador **no** se dibuja (ni se tabula): `#menu-cuentas` está "
            "en el documento pero no se ve",
        )
        if not visible_el_menu:
            hallazgo(
                "con el zoom de página al 200 % (712 px) el menú de módulos no está: `#menu-cuentas` existe en "
                "el documento pero `checkVisibility()` es falso, así que con el teclado no se llega a «Mis "
                "cuentas» desde el inicio (la pantalla de inicio de ese ancho no lleva a las cuentas). En esta "
                "comprobación se llega por la dirección de la pantalla (`#/cuentas`), que es la única puerta "
                "que queda a ese ancho"
            )


# ---------------------------------------------------------------------------
# Lo que se hace al ejecutarlo
# ---------------------------------------------------------------------------


def main() -> int:
    analizador = argparse.ArgumentParser(description="El teclado y el zoom, de verdad.")
    analizador.add_argument("direccion", nargs="?", default="http://127.0.0.1:8022", help="dónde está el servidor de pruebas")
    analizador.add_argument(
        "--romper",
        choices=["outline", "nombre"],
        default=None,
        help="rompe a propósito una comprobación (solo en el navegador, no toca ningún fichero)",
    )
    analizador.add_argument("--solo-zoom", action="store_true", help="se salta el recorrido de la escala 1")
    analizador.add_argument(
        "--solo-escala-1",
        action="store_true",
        help="solo el recorrido de la escala 1 (el de 1440 px): para mirar un fallo sin esperar a los otros dos",
    )
    argumentos = analizador.parse_args()

    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("El teclado y el zoom, de verdad. Servidor:", argumentos.direccion)
    print(f"(romper a propósito: {argumentos.romper or 'no'})")
    try:
        datos = sembrar_la_prueba(argumentos.direccion)
    except Exception as fallo:
        print(f"No se ha podido preparar la prueba en {argumentos.direccion}: {fallo}")
        print("¿Está el servidor de pruebas levantado con una base que se pueda ensuciar?")
        return 2
    datos["direccion"] = argumentos.direccion
    print(f"Cuenta de la prueba: {datos['correo']} · gasto n.º {datos['gasto_id']}")

    try:
        if not argumentos.solo_zoom:
            with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
                el_recorrido(
                    nav,
                    datos,
                    "escala 1 (1440 px)",
                    romper=argumentos.romper,
                    orden_del_inicio=True,
                    la_direccion_entrar=True,
                    con_menu=True,
                )
                # La pantalla de entrar, con su orden de navegación completo (es la primera que se ve).
                nav.evaluar("localStorage.removeItem('cuedigital.token')")
                abrir_de_verdad(nav, f"{argumentos.direccion}/#/")
                nav.esperar("document.querySelector('#correo') !== null")
                esperar_la_pantalla(nav)
                los_controles_de_la_pantalla(nav, "la pantalla de entrar", romper=argumentos.romper)
                el_orden_de_navegacion(
                    nav, "la pantalla de entrar", direccion_del_paseo=f"{argumentos.direccion}/#/"
                )
        if not argumentos.solo_escala_1:
            la_escala_del_dispositivo_al_200(argumentos.direccion, datos, argumentos.romper)
            el_zoom_de_pagina_al_200(argumentos.direccion, datos, argumentos.romper)
    except SinNavegador as fallo:
        print(f"\n{fallo}")
        print("Sin navegador no se puede comprobar ni el teclado ni el zoom: la comprobación queda SIN HACER.")
        return 2

    titulo("== Resumen ==")
    print("Dónde acabó cada recorrido:")
    for etiqueta, donde, como in RECORRIDOS:
        print(f"  · {etiqueta}: {donde or '(sin hash)'} — {como}")
    if HALLAZGOS:
        distintos = list(dict.fromkeys(HALLAZGOS))
        print(f"\nHallazgos: {len(HALLAZGOS)} medidas, {len(distintos)} distintos (los mismos salen en cada pasada de zoom)")
        for uno in distintos:
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
