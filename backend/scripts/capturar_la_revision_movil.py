"""Capturas y medidas de la revisión móvil (`task-8`): antes y después.

## Para qué existe

El encargo pide revisar **todas** las pantallas de la app nueva (`/nuevo/`) a **360, 390,
768 y 1024 px**, arreglar de verdad lo que no se puede usar con el dedo y **demostrarlo**
con capturas y números antes y después. Una captura sin medida acredita poco, así que este
guion hace las dos cosas por pantalla y por ancho:

  1. **Captura** la pantalla tal y como la ve el agricultor, desde arriba.
  2. **Mide en el DOM** lo que decide si se puede usar de pie en una parcela:
     · **desborde horizontal** de la página (scroll lateral: lo peor en un móvil);
     · **tamaño de lo que se toca** (`getBoundingClientRect`: alto y ancho de cada
       `button`, `a`, `input`, `select`, `textarea`, `[role=button]` y `summary`);
     · **separación entre acciones** (dos controles hermanos que se tocan);
     · **modales que no caben** (la caja respecto de la ventana, su scroll interno y si
       «Cerrar» queda dentro y con tamaño de dedo);
     · **tablas que se rompen** (la tabla y su caja: cuánto se sale y si se puede desplazar
       dentro de su caja sin mover la página);
     · **mapas tapados** (`elementFromPoint` sobre el lienzo: quién recibe el toque);
     · **teclado numérico** (`type`, `inputmode` y `enterkeyhint` de cada campo, con su
       etiqueta) para hectáreas, dosis, cantidades, superficie y referencias.

Y lo guarda todo en `docs/capturas-revision/`: las imágenes `antes-<pantalla>-<ancho>.png`
(o `despues-...`) y un `mediciones-antes.json` / `mediciones-despues.json`.

**No cambia nada de la aplicación**: solo abre un navegador, pulsa lo que pulsaría el
agricultor y guarda fotos y números.

## Cómo se lanza

Necesita un servidor de verdad con base y adjuntos temporales. En `8094`:

```powershell
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\\cd-revision-8094\\datos.db"
$env:CUEDIGITAL_ADJUNTOS="$env:TEMP\\cd-revision-8094\\adjuntos"
$env:CUEDIGITAL_SECRETO="revision"
$env:CUEDIGITAL_ENTORNO="pruebas"
$env:CUEDIGITAL_ITERACIONES_PBKDF2="100000"
..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8094
```

Y después, una vez para el «antes» y otra para el «después» (con la base recién hecha):

```powershell
..\\.venv\\Scripts\\python.exe scripts\\capturar_la_revision_movil.py http://127.0.0.1:8094 --momento antes
..\\.venv\\Scripts\\python.exe scripts\\capturar_la_revision_movil.py http://127.0.0.1:8094 --momento despues
```

Si no hay navegador instalado, el guion lo dice y sale con código 1 sin inventar capturas.
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

from comprobar_el_armazon_nuevo import (  # noqa: E402
    clic_en_visible,
    cuenta_vacia,
    esperar_estado,
    esperar_lo_pintado,
    ir_a_una_vista,
)
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad, SinNavegador  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[2]
CAPTURAS = RAIZ / "docs" / "capturas-revision"

# Los cuatro anchos del encargo. La altura es la de un móvil y una tableta de verdad:
# 360×640 (móvil pequeño), 390×844 (móvil habitual), 768×1024 (tableta en vertical) y
# 1024×900 (la tableta en horizontal, que es el ancho del contrato de escritorio).
ANCHOS = ((360, 640), (390, 844), (768, 1024), (1024, 900))

# La pieza que mide. Todo se lee del DOM con `getBoundingClientRect` y `getComputedStyle`:
# nada se supone. Devuelve un JSON con lo que se puede contar y citar en el documento.
MEDIR_JS = r"""(() => {
  const seVe = (n) => {
    if (!n || !n.getBoundingClientRect) return false;
    const r = n.getBoundingClientRect();
    const s = getComputedStyle(n);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const limpiar = (t) => (t || '').replace(/\s+/g, ' ').trim();
  const texto = (n) => limpiar(n.innerText || n.textContent || n.getAttribute('aria-label') || n.getAttribute('placeholder') || '').slice(0, 70);
  const caja = (n) => {
    const r = n.getBoundingClientRect();
    return { arriba: Math.round(r.top), izquierda: Math.round(r.left), ancho: Math.round(r.width * 10) / 10, alto: Math.round(r.height * 10) / 10, abajo: Math.round(r.bottom), derecha: Math.round(r.right) };
  };
  const donde = (n) => {
    const zona = n.closest('[data-vista]');
    return zona ? zona.getAttribute('data-vista') : (n.closest('.barra-inferior') ? 'barra-inferior'
      : n.closest('.barra-lateral') ? 'barra-lateral'
      : n.closest('.barra-superior') ? 'barra-superior' : 'suelto');
  };
  const identificador = (n) => {
    const attrs = ['data-accion', 'data-destino', 'data-ventana-cerrar', 'data-apuntar-tab',
      'data-filtro-tipo', 'data-cuaderno-empezar', 'data-sigpac-buscar', 'data-sigpac-usar',
      'data-cuaderno-filtro', 'data-trabajo-fila', 'data-tierra-id', 'data-producto-tab'];
    const pistas = attrs.filter((a) => n.hasAttribute(a)).map((a) => a + '=' + n.getAttribute(a));
    return pistas.join(' ') || n.className || n.tagName.toLowerCase();
  };

  // ---- lo que se toca -------------------------------------------------------
  // Un `input` recortado con `.ojo-solo` no es lo que se toca: detrás hay una etiqueta que
  // hace de botón. Y una casilla pequeña se toca por su etiqueta entera. Se mide el objetivo
  // real del dedo, que es lo que dice la norma de 44 px.
  const escondido = (n) => n.classList.contains('ojo-solo');
  const cajaDelObjetivo = (n) => {
    if (escondido(n)) {
      const etiqueta = n.closest('label');
      return etiqueta ? etiqueta : n;
    }
    if (n.matches('input[type=checkbox], input[type=radio]')) {
      const etiqueta = n.closest('label');
      return etiqueta ? etiqueta : n;
    }
    return n;
  };
  const controles = Array.from(document.querySelectorAll(
    'button, a, input, select, textarea, summary, [role="button"]'
  )).filter(seVe).map((n) => {
    const objetivo = cajaDelObjetivo(n);
    const c = caja(objetivo);
    return {
      etiqueta: n.tagName.toLowerCase(),
      objetivo: objetivo.tagName.toLowerCase() + (objetivo.className ? '.' + String(objetivo.className).split(' ')[0] : ''),
      texto: texto(objetivo),
      donde: donde(n),
      identificador: identificador(objetivo),
      clase: String(objetivo.className || ''),
      alto: c.alto,
      ancho: c.ancho,
      arriba: c.arriba,
      izquierda: c.izquierda,
      deshabilitado: Boolean(n.disabled) || n.getAttribute('aria-disabled') === 'true',
      principal: objetivo.classList.contains('boton--principal') || objetivo.classList.contains('boton--grande'),
      href: n.getAttribute ? (n.getAttribute('href') || '') : '',
    };
  });
  // Un dedo con guante acierta 44 px; la acción principal, 48.
  const pequenos = controles.filter((c) => c.alto < 44 || c.ancho < 44);
  const principalesPequenos = controles.filter((c) => c.principal && (c.alto < 48 || c.ancho < 48));

  // ---- separación entre acciones -------------------------------------------
  // Solo se miran los grupos de acciones (los botones que se presentan juntos) y los que
  // están en la misma fila. Una lista de 64 tierras apiladas no es un grupo de acciones: sus
  // filas van seguidas a propósito y cada una ocupa todo el ancho.
  const GRUPOS = '.nav, .estado__acciones, .filtros, .pestanas, .barra-superior, '
    + '.barra-superior__derecha, .barra-inferior, .pagina__fila, .cuaderno__cabecera, '
    + '.calendario__barra, .mapa__barra, .mapa__zoom, .panel__cabecera, .rejilla-campos, '
    + '.tarjetas, .fotos, .leyenda, .sigpac__cache-forma, .cuaderno__filtro, .campo-de-color';
  const ES_DESTRUCTIVA = (n) => /peligro|borrar|anular|deshacer/i.test(String(n.className || '') + ' ' + (n.textContent || ''));
  const huecos = [];
  const vistos = new Set();
  const nodos = Array.from(document.querySelectorAll(
    'button, a, input, select, textarea, summary, [role="button"]'
  )).filter(seVe);
  for (const n of nodos) {
    const padre = n.parentElement;
    if (!padre) continue;
    const esGrupo = padre.matches(GRUPOS);
    const hermanos = Array.from(padre.children).filter((h) => seVe(h) && h.matches('button, a, input, select, textarea, summary, [role="button"]'));
    const i = hermanos.indexOf(n);
    if (i < 0 || i + 1 >= hermanos.length) continue;
    const otro = hermanos[i + 1];
    const a = n.getBoundingClientRect();
    const b = otro.getBoundingClientRect();
    const mismaFila = Math.abs(a.top - b.top) < 2;
    const mismaColumna = Math.abs(a.left - b.left) < 2;
    if (!mismaFila && !(esGrupo && mismaColumna)) continue;
    const hueco = mismaFila
      ? Math.round((b.left - a.right) * 10) / 10
      : Math.round((b.top - a.bottom) * 10) / 10;
    const clave = identificador(n) + '|' + identificador(otro) + '|' + Math.round(a.top) + '|' + Math.round(b.top);
    if (vistos.has(clave)) continue;
    vistos.add(clave);
    if (hueco !== null && hueco < 8) {
      const destructiva = ES_DESTRUCTIVA(n) || ES_DESTRUCTIVA(otro);
      if (hueco < (destructiva ? 12 : 8)) {
        huecos.push({
          uno: identificador(n) + ' «' + texto(n) + '»',
          otro: identificador(otro) + ' «' + texto(otro) + '»',
          hueco,
          destructiva,
        });
      }
    }
  }

  // ---- tablas ---------------------------------------------------------------
  // Una tabla puede ser más ancha que su caja a propósito: entonces **se desplaza dentro de
  // su caja** (`overflow-x`), y eso no es un desborde de la página. Lo que no vale es que la
  // tabla estire la página: por eso se distingue «no cabe en su caja» de «se sale de la
  // pantalla».
  const tablas = Array.from(document.querySelectorAll('.tabla, .panel__tabla'))
    .filter(seVe).map((t) => {
      const envoltura = t.closest('.tabla-envoltura');
      const r = t.getBoundingClientRect();
      let recortado = false;
      let p = t.parentElement;
      while (p && p !== document.documentElement) {
        const s = getComputedStyle(p);
        if ((s.overflowX === 'auto' || s.overflowX === 'scroll' || s.overflowX === 'hidden')
            && p.getBoundingClientRect().right <= window.innerWidth + 1) { recortado = true; break; }
        p = p.parentElement;
      }
      return {
        filas: t.querySelectorAll('tbody tr').length || t.querySelectorAll('tr').length,
        ancho_tabla: Math.round(t.scrollWidth),
        ancho_caja: Math.round(t.clientWidth),
        se_sale_px: Math.round(Math.max(0, t.scrollWidth - t.clientWidth)),
        en_envoltura: Boolean(envoltura),
        envoltura_desplaza: envoltura ? getComputedStyle(envoltura).overflowX !== 'visible' : false,
        estira_la_pagina: !recortado && r.right > window.innerWidth + 1,
        primera_columna_fija: (() => {
          const celda = t.querySelector('thead th, tbody th, tbody td');
          return celda ? getComputedStyle(celda).position === 'sticky' : false;
        })(),
      };
    });

  // ---- mapas ----------------------------------------------------------------
  // Un mapa sirve para tocar. Se mira (1) que haya zonas de toque de verdad y (2) quién
  // recibe el dedo en un punto del trazo. Si el mapa está por debajo del pliegue, el punto
  // cae sobre la ventana y no es que algo lo tape: se dice «fuera de la vista».
  const mapa = (() => {
    const el = Array.from(document.querySelectorAll('[data-mapa], .mapa, .mapa__lienzo')).filter(seVe)[0];
    if (!el) return null;
    const lienzo = el.closest('.mapa__lienzo') || el.querySelector('.mapa__lienzo') || el;
    const r = lienzo.getBoundingClientRect();
    const puntos = [
      [r.left + r.width * 0.25, r.top + r.height * 0.3],
      [r.left + r.width * 0.5, r.top + r.height * 0.5],
      [r.left + r.width * 0.7, r.top + r.height * 0.65],
    ];
    const quienRecibe = (x, y) => {
      if (x < 0 || y < 0 || x > window.innerWidth || y > window.innerHeight) return "fuera";
      const encima = document.elementFromPoint(x, y);
      if (!encima) return "nada";
      if (encima.closest('.mapa__lienzo')) return "mapa";
      if (encima.closest('.modal')) return "ventana";
      return "otra-cosa";
    };
    const recibe = puntos.map(([x, y]) => quienRecibe(x, y));
    const zona = Array.from(document.querySelectorAll('[data-mapa-toque]')).filter(seVe)[0] || null;
    let toque = null;
    if (zona) {
      const largo = typeof zona.getTotalLength === "function" ? zona.getTotalLength() : 0;
      if (largo) {
        zona.scrollIntoView({ block: "center", behavior: "instant" });
        const punto = zona.getPointAtLength(largo / 2);
        const matriz = zona.getScreenCTM();
        const x = matriz.a * punto.x + matriz.c * punto.y + matriz.e;
        const y = matriz.b * punto.x + matriz.d * punto.y + matriz.f;
        const dentro = x >= 0 && y >= 0 && x <= window.innerWidth && y <= window.innerHeight;
        const encima = dentro ? document.elementFromPoint(x, y) : null;
        toque = {
          punto_dentro: dentro,
          alcanzable: Boolean(encima && (encima.hasAttribute("data-mapa-toque") || encima.closest(".mapa__lienzo"))),
          es_la_zona: Boolean(encima && encima.hasAttribute("data-mapa-toque")),
          quien_recibe: encima ? encima.tagName.toLowerCase() : null,
        };
      }
    }
    return {
      ancho: Math.round(r.width),
      alto: Math.round(r.height),
      zonas_de_toque: document.querySelectorAll('.mapa__anillo--toque, .mapa__punto--toque').length,
      anillos_visibles: document.querySelectorAll('.mapa__anillo').length
        - document.querySelectorAll('.mapa__anillo--toque').length,
      recintos_en_el_mapa: document.querySelectorAll('[data-sigpac-dibujo-recinto]').length,
      recintos_elegidos: Array.from(document.querySelectorAll('[data-sigpac-dibujo-recinto]'))
        .filter((n) => n.getAttribute('aria-pressed') === 'true').length,
      recintos_enfocables: Array.from(document.querySelectorAll('[data-sigpac-dibujo-recinto]'))
        .filter((n) => n.getAttribute('tabindex') === '0').length,
      quien_recibe: recibe,
      tapados: recibe.filter((uno) => uno === "otra-cosa" || uno === "nada").length,
      fuera_de_la_vista: recibe.filter((uno) => uno === "fuera" || uno === "ventana").length,
      toque,
    };
  })();

  // ---- teclado de cada campo ------------------------------------------------
  const campos = Array.from(document.querySelectorAll('input, select, textarea')).filter(seVe).map((n) => {
    const etiqueta = n.closest('label');
    return {
      etiqueta: etiqueta ? limpiar(etiqueta.querySelector('span') ? etiqueta.querySelector('span').textContent : etiqueta.textContent).slice(0, 55) : '',
      tipo: n.getAttribute('type') || n.tagName.toLowerCase(),
      inputmode: n.getAttribute('inputmode') || '',
      enterkeyhint: n.getAttribute('enterkeyhint') || '',
      nombre: n.getAttribute('name') || '',
      datos: Array.from(n.attributes).filter((a) => a.name.startsWith('data-')).map((a) => a.name).join(' '),
      en_modal: Boolean(n.closest('.modal__caja')),
    };
  });

  // ---- desborde horizontal --------------------------------------------------
  const desborde = document.documentElement.scrollWidth - window.innerWidth;
  // Quién se sale. Se descartan los hijos de una caja que desplaza dentro (tablas), porque
  // esos desbordan su caja a propósito y la página no se mueve.
  const culpables = [];
  for (const n of Array.from(document.querySelectorAll('.contenido *, .modal__caja *')).filter(seVe)) {
    const r = n.getBoundingClientRect();
    if (r.right <= window.innerWidth + 1) continue;
    let recortado = false;
    let p = n.parentElement;
    while (p && p !== document.documentElement) {
      const s = getComputedStyle(p);
      if ((s.overflowX === 'auto' || s.overflowX === 'scroll' || s.overflowX === 'hidden')
          && p.getBoundingClientRect().right <= window.innerWidth + 1) { recortado = true; break; }
      p = p.parentElement;
    }
    if (recortado) continue;
    culpables.push({ etiqueta: n.tagName.toLowerCase(), clase: String(n.className || ''), derecha: Math.round(r.right), texto: texto(n).slice(0, 45) });
    if (culpables.length >= 8) break;
  }

  // ---- tamaño de letra ------------------------------------------------------
  const raiz = document.querySelector('.contenido') || document.body;
  const hojas = Array.from(raiz.querySelectorAll('*')).filter(
    (n) => n.children.length === 0 && limpiar(n.textContent) && seVe(n)
  );
  let minimoPx = 99;
  const pequenosTexto = [];
  for (const n of hojas) {
    const px = parseFloat(getComputedStyle(n).fontSize) || 0;
    if (!px) continue;
    if (px < minimoPx) minimoPx = px;
    if (px < 16) pequenosTexto.push({ px, texto: limpiar(n.textContent).slice(0, 45) });
  }

  const cabecera = document.querySelector('.barra-superior');
  const h1 = document.querySelector('.contenido h1');
  return JSON.stringify({
    vista: (document.querySelector('[data-vista]') || { getAttribute: () => null }).getAttribute('data-vista'),
    estado: (document.querySelector('[data-estado]') || { getAttribute: () => null }).getAttribute('data-estado'),
    titulo: h1 ? limpiar(h1.innerText) : '',
    ancho_ventana: window.innerWidth,
    alto_ventana: window.innerHeight,
    desborde_horizontal: desborde,
    culpables_del_desborde: culpables,
    alto_pagina: document.documentElement.scrollHeight,
    cabecera_alto: cabecera ? Math.round(cabecera.getBoundingClientRect().height) : 0,
    controles: controles.map((c) => ({ ...c, pequeno: c.alto < 44 || c.ancho < 44 })),
    pequenos,
    principales_pequenos: principalesPequenos,
    huecos_pequenos: huecos,
    tablas,
    mapa,
    campos,
    textos_pequenos: pequenosTexto.slice(0, 60),
    textos_pequenos_total: pequenosTexto.length,
    letra_minima_px: minimoPx === 99 ? null : minimoPx,
  });
})()"""


def la_caja_de_una_ventana(nav: NavegadorDeVerdad) -> dict | None:
    """La caja del modal que esté abierto, medida desde Python (más simple que dentro del JS)."""
    return nav.evaluar(
        "(() => {"
        " const c = Array.from(document.querySelectorAll('.modal__caja'))"
        "   .find((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });"
        " if (!c) return null;"
        " const r = c.getBoundingClientRect();"
        " const cerrar = c.querySelector('[data-ventana-cerrar]');"
        " const rc = cerrar ? cerrar.getBoundingClientRect() : null;"
        " const cabecera = c.querySelector('.modal__cabecera');"
        " const rca = cabecera ? cabecera.getBoundingClientRect() : null;"
        " return JSON.stringify({"
        "  caja: {arriba: Math.round(r.top), izquierda: Math.round(r.left),"
        "    ancho: Math.round(r.width * 10) / 10, alto: Math.round(r.height * 10) / 10,"
        "    abajo: Math.round(r.bottom), derecha: Math.round(r.right)},"
        "  ancho_ventana: window.innerWidth, alto_ventana: window.innerHeight,"
        "  cabe: r.left >= -1 && r.right <= window.innerWidth + 1 && r.top >= -1"
        "    && r.bottom <= window.innerHeight + 1,"
        "  scroll_interno: c.scrollHeight > c.clientHeight + 1,"
        "  desborde_dentro: Math.round((c.scrollWidth - c.clientWidth) * 10) / 10,"
        "  cerrar_dentro_de_la_caja: rc ? (rc.top >= r.top - 1 && rc.bottom <= r.bottom + 1) : false,"
        "  cerrar_alto: rc ? Math.round(rc.height) : 0,"
        "  cerrado_arriba: rca ? rca.bottom <= window.innerHeight : false,"
        "  cerrar_visible: cerrar ? Boolean(cerrar.checkVisibility({checkVisibilityCSS: true})) : false"
        " }); })()"
    )


def captura(nav: NavegadorDeVerdad, nombre: str) -> pathlib.Path:
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    crudo = nav.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = CAPTURAS / f"{nombre}.png"
    destino.write_bytes(base64.b64decode(crudo))
    return destino


def arriba_del_todo(nav: NavegadorDeVerdad) -> None:
    nav.evaluar(
        "(() => { window.scrollTo(0, 0);"
        " const m = document.querySelector('.contenido'); if (m) m.scrollTo(0, 0); return true; })()"
    )
    time.sleep(0.2)


def medir(nav: NavegadorDeVerdad) -> dict:
    crudo = nav.evaluar(MEDIR_JS)
    datos = json.loads(crudo) if crudo else {}
    # El modal se vuelve a medir por un camino que no depende del JS incrustado de arriba.
    modal = la_caja_de_una_ventana(nav)
    datos["modal"] = json.loads(modal) if modal else None
    return datos


def la_sesion(nav: NavegadorDeVerdad, base: str, token: str) -> None:
    nav.abrir(base, esperar=0.8)
    nav.evaluar(f"localStorage.setItem('cuedigital.token', {json.dumps(token)})")
    nav.abrir(f"{base}/nuevo/", esperar=1.0)


def escribir_en_la_pantalla(nav: NavegadorDeVerdad, selector: str, valor: str) -> bool:
    """Escribe en un campo como lo haría el agricultor (setter nativo + evento `input`)."""
    return bool(
        nav.evaluar(
            "(() => { const el = document.querySelector(" + json.dumps(selector) + ");"
            " if (!el) return false; const setter = Object.getOwnPropertyDescriptor("
            "window.HTMLInputElement.prototype, 'value').set;"
            " setter.call(el, " + json.dumps(valor) + ");"
            " el.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"
        )
    )


# Las pantallas del encargo, en orden. Cada una: clave (nombre del fichero), nombre para el
# documento, cómo se llega (destino de la barra o clic concreto) y qué se hace cuando la
# pantalla ya tiene sus datos (`tras_pintar`), que es donde se elige la pestaña, se filtra o
# se busca en el SIGPAC. Las cinco primeras son las que pide David antes: mapa/tierras, ficha,
# alta por referencia (con la ventana del SIGPAC), cuaderno y tratamientos.
PANTALLAS = [
    {"clave": "hoy", "nombre": "Hoy", "pasos": []},
    {"clave": "tierras", "nombre": "Mis tierras y el mapa", "pasos": [("destino", "tierras")]},
    {
        "clave": "tierra",
        "nombre": "Ficha de una tierra",
        "pasos": [("destino", "tierras"), ("pulsar", "[data-tierra-id]")],
    },
    {
        "clave": "apuntar",
        "nombre": "Apuntar un trabajo",
        "pasos": [("destino", "apuntar")],
    },
    {
        "clave": "apuntar-tratamiento",
        "nombre": "Apuntar un tratamiento",
        "pasos": [("destino", "apuntar"), ("pulsar", "[data-apuntar-tab=\"tratamiento\"]")],
        "tras_pintar": [
            ("esperar", "[data-apuntar-producto]", 20),
            ("pulsar", "[data-apuntar-producto]"),
            ("esperar", "[data-apuntar-dosis]", 15),
        ],
    },
    {
        "clave": "alta",
        "nombre": "Añadir tierras por referencia",
        "pasos": [("destino", "tierras"), ("pulsar", "[data-accion=anadir-tierras]")],
    },
    {
        "clave": "sigpac",
        "nombre": "Ventana del SIGPAC, con el recinto buscado",
        "pasos": [
            ("destino", "tierras"),
            ("pulsar", "[data-accion=anadir-tierras]"),
            ("pulsar", "[data-abrir-ventana-sigpac]"),
        ],
        "cerrar": "[data-ventana-cerrar]",
        "vista": "ventana",
        # La búsqueda de verdad: si no hay cobertura, la ventana se captura sin recintos y
        # el documento lo dice; no se inventa un dibujo.
        "tras_pintar": [
            ("escribir", "[data-sigpac-buscar-referencia]", "37:70:0:0:503:51"),
            ("pulsar", "[data-sigpac-buscar]"),
            ("esperar", "[data-sigpac-recinto-id]", 40),
        ],
    },
    {"clave": "cuaderno", "nombre": "Cuaderno guiado", "pasos": [("destino", "cuaderno")]},
    {"clave": "productos", "nombre": "Productos y abonos", "pasos": [("destino", "productos")]},
    {"clave": "calendario", "nombre": "Calendario", "pasos": [("destino", "calendario")]},
    {
        "clave": "trabajos",
        "nombre": "Trabajos",
        "pasos": [("destino", "trabajos")],
    },
    {
        "clave": "trabajos-tratamiento",
        "nombre": "Lista de tratamientos",
        "pasos": [("destino", "trabajos")],
        "tras_pintar": [
            ("esperar", "[data-filtro-tipo]", 20),
            ("pulsar", "[data-filtro-tipo=\"tratamiento\"]"),
        ],
    },
    {"clave": "facturas", "nombre": "Facturas", "pasos": [("destino", "facturas")]},
    {"clave": "mas", "nombre": "Más", "pasos": [("destino", "mas")], "solo_movil": True},
]

# El nombre de la vista nueva que corresponde a cada clave (para esperar a que pinte).
VISTA_DE_LA_PANTALLA = {
    "apuntar-tratamiento": "apuntar",
    "trabajos-tratamiento": "trabajos",
    "alta": "alta",
    "sigpac": "alta",
}


def ir_a_la_pantalla(nav: NavegadorDeVerdad, pantalla: dict, clave: str) -> bool:
    for tipo, valor in pantalla["pasos"]:
        if tipo == "destino":
            if not ir_a_una_vista(nav, valor):
                print(f"     (no se llega al destino {valor})")
                return False
            # Se espera a que la pantalla tenga sus datos ANTES de pulsar nada: pulsar
            # mientras React repinta pierde el clic (se perdía a 360 en «Apuntar»).
            vista = VISTA_DE_LA_PANTALLA.get(valor, valor)
            nav.esperar(f"!!document.querySelector('[data-vista=\"{vista}\"]')", segundos=20)
            esperar_lo_pintado(nav, valor)
        else:
            time.sleep(0.4)
            if not clic_en_visible(nav, valor):
                print(f"     (no se encuentra {valor})")
                return False
    if pantalla.get("vista") == "ventana":
        if not nav.esperar("!!document.querySelector('[data-ventana-sigpac]')", segundos=20):
            print("     (no se abre la ventana del SIGPAC)")
            return False
    else:
        vista = VISTA_DE_LA_PANTALLA.get(clave, clave)
        if not nav.esperar(f"!!document.querySelector('[data-vista=\"{vista}\"]')", segundos=20):
            print(f"     (no se llega a la vista {vista})")
            return False
        esperar_lo_pintado(nav, vista)

    for accion in pantalla.get("tras_pintar", []):
        time.sleep(0.3)
        if accion[0] == "esperar":
            if not nav.esperar(f"!!document.querySelector({json.dumps(accion[1])})", segundos=accion[2]):
                print(f"     (no aparece {accion[1]}; se sigue para capturar lo que hay)")
                return True
        elif accion[0] == "pulsar":
            if not clic_en_visible(nav, accion[1]):
                print(f"     (no se encuentra {accion[1]})")
                return True
        elif accion[0] == "escribir":
            escribir_en_la_pantalla(nav, accion[1], accion[2])
    return True


def recorrer(nav: NavegadorDeVerdad, base: str, ancho: int, alto: int, token: str, momento: str) -> dict:
    print(f"\n== {ancho}×{alto} px ==")
    nav.medir(ancho, alto, movil=ancho <= 767)
    la_sesion(nav, base, token)
    if not esperar_estado(nav, "listo"):
        print("  (la app no llega a «listo»)")
        return {}

    medidas: dict[str, dict] = {}
    for pantalla in PANTALLAS:
        clave = pantalla["clave"]
        if pantalla.get("solo_movil") and ancho > 700:
            print(f"  -- {clave}: no se alcanza a {ancho} px (no hay destino «Más» en tableta)")
            continue
        print(f"  -- {pantalla['nombre']} ({clave})")
        if not ir_a_la_pantalla(nav, pantalla, clave):
            continue
        time.sleep(1.2)  # los mapas y las miniaturas llegan después del HTML
        arriba_del_todo(nav)
        # La captura se hace **antes de medir**: la medida acerca el mapa para comprobar que
        # recibe el toque, y la foto tiene que ser la primera pantalla, desde arriba.
        fichero = captura(nav, f"{momento}-{clave}-{ancho}")
        datos = medir(nav)
        datos["pantalla"] = pantalla["nombre"]
        datos["clave"] = clave
        datos["ruta"] = " / ".join(f"{t}:{v}" for t, v in pantalla["pasos"]) or "arranque"
        medidas[clave] = datos

        # **El mapa se toca de verdad**: se busca un punto del trazo, se mira quién lo recibe y,
        # en «Mis tierras», se lanza el clic y se comprueba que abre la ficha de esa tierra.
        if datos.get("mapa") and (datos["mapa"].get("zonas_de_toque") or 0) > 0:
            if clave == "tierras":
                nav.evaluar(
                    "(() => { const z = document.querySelector('[data-mapa-toque]');"
                    " if (!z) return false;"
                    " z.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));"
                    " return true; })()"
                )
                abre = nav.esperar("!!document.querySelector('[data-vista=\"tierra\"]')", segundos=10)
                datos["mapa"]["toque_abre_la_ficha"] = abre
                if abre:
                    # Se vuelve a la lista para que la pantalla siguiente salga de su sitio.
                    ir_a_una_vista(nav, "tierras")
                    nav.esperar("document.querySelectorAll('[data-tierra-id]').length > 0", segundos=20)
            elif clave == "sigpac":
                datos["mapa"]["toque_elige_recinto"] = bool(
                    nav.evaluar(
                        "(() => { const z = document.querySelector('[data-mapa-toque]');"
                        " if (!z) return false;"
                        " z.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));"
                        " return Array.from(document.querySelectorAll('[data-sigpac-dibujo-recinto]'))"
                        "   .some((p) => p.getAttribute('aria-pressed') === 'true'); })()"
                    )
                )

        print(
            f"     {fichero.name} · desborde {datos.get('desborde_horizontal')} px ·"
            f" {len(datos.get('pequenos') or [])} controles <44 px ·"
            f" {len(datos.get('huecos_pequenos') or [])} huecos <8 px ·"
            f" modal {'sí' if datos.get('modal') else 'no'}"
            f"{' (NO cabe)' if datos.get('modal') and not datos['modal'].get('cabe') else ''} ·"
            f" {len(datos.get('tablas') or [])} tablas"
        )
        if pantalla.get("cerrar"):
            nav.evaluar(
                "(() => { const b = document.querySelector(" + json.dumps(pantalla["cerrar"]) + ");"
                " if (!b) return false; b.click(); return true; })()"
            )
            nav.esperar("!document.querySelector('[data-ventana-sigpac]')", segundos=10)
    return medidas


def el_estado_vacio(base: str, nav: NavegadorDeVerdad, ancho: int, alto: int, momento: str) -> dict | None:
    """La pantalla de tierras de una cuenta recién creada: el vacío de verdad, no simulado."""
    if ancho > 767:
        return None  # el vacío se mira en el móvil, que es donde se usa
    print(f"\n== estado vacío (cuenta sin tierras, {ancho} px) ==")
    token = cuenta_vacia(base)
    nav.medir(ancho, alto, movil=True)
    la_sesion(nav, base, token)
    esperar_estado(nav, "vacio", segundos=30)
    ir_a_una_vista(nav, "tierras")
    nav.esperar("!!document.querySelector('[data-vista=\"tierras\"]')", segundos=20)
    time.sleep(0.8)
    arriba_del_todo(nav)
    datos = medir(nav)
    datos["pantalla"] = "Mis tierras, sin tierras"
    datos["clave"] = "vacio-tierras"
    captura(nav, f"{momento}-vacio-tierras-{ancho}")
    print(f"  {momento}-vacio-tierras-{ancho}.png · desborde {datos.get('desborde_horizontal')} px")
    return datos


def resumen(todo: dict) -> dict:
    """Los números que van a la tabla del documento: por ancho, desbordes y controles pequeños."""
    salida: dict[str, dict] = {}
    por_ancho: dict[int, list[dict]] = {}
    for clave, pantallas in todo.items():
        if not clave.isdigit():
            continue
        por_ancho[int(clave)] = list(pantallas.values())
    for ancho, pantallas in sorted(por_ancho.items()):
        desbordes = [
            (p["clave"], p["desborde_horizontal"])
            for p in pantallas
            if isinstance(p.get("desborde_horizontal"), int) and p["desborde_horizontal"] > 1
        ]
        pequenos = [
            {"pantalla": p["clave"], "cuantos": len(p.get("pequenos") or []), "cuales": p.get("pequenos")}
            for p in pantallas
            if p.get("pequenos")
        ]
        huecos = [
            {"pantalla": p["clave"], "cuantos": len(p.get("huecos_pequenos") or []), "cuales": p.get("huecos_pequenos")}
            for p in pantallas
            if p.get("huecos_pequenos")
        ]
        modales = [
            {"pantalla": p["clave"], "cabe": (p.get("modal") or {}).get("cabe"), "medida": p.get("modal")}
            for p in pantallas
            if p.get("modal")
        ]
        tablas = [
            {"pantalla": p["clave"], "tablas": p.get("tablas")}
            for p in pantallas
            if p.get("tablas")
        ]
        mapas = [
            {"pantalla": p["clave"], "mapa": p.get("mapa")}
            for p in pantallas
            if p.get("mapa")
        ]
        salida[str(ancho)] = {
            "pantallas_medidas": len(pantallas),
            "desbordes": desbordes,
            "pantallas_con_desborde": len(desbordes),
            "controles_pequenos": sum(len(p.get("pequenos") or []) for p in pantallas),
            "principales_pequenos": sum(len(p.get("principales_pequenos") or []) for p in pantallas),
            "huecos_pequenos": sum(len(p.get("huecos_pequenos") or []) for p in pantallas),
            "detalle_pequenos": pequenos,
            "detalle_huecos": huecos,
            "modales": modales,
            "modales_que_no_caben": sum(1 for m in modales if m["cabe"] is False),
            "tablas": tablas,
            "tablas_que_estiran_la_pagina": sum(
                1 for t in tablas for una in t["tablas"] if una.get("estira_la_pagina")
            ),
            "tablas_sin_caja": sum(
                1 for t in tablas for una in t["tablas"] if not una.get("en_envoltura")
            ),
            "mapas": mapas,
            "mapas_que_no_se_tocan": [
                {"pantalla": m["pantalla"], "mapa": m["mapa"]}
                for m in mapas
                if m["mapa"] and m["mapa"].get("anillos_visibles") and not m["mapa"].get("zonas_de_toque")
            ],
            "campos_sin_teclado_numerico": [
                {"pantalla": p["clave"], "campos": [
                    c for c in (p.get("campos") or [])
                    if not c["inputmode"] and c["tipo"] not in ("number", "tel", "date", "search", "file", "checkbox")
                ]}
                for p in pantallas
            ],
            "letra_minima_por_pantalla": {
                p["clave"]: p.get("letra_minima_px") for p in pantallas if p.get("letra_minima_px")
            },
        }
    return salida


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("base", nargs="?", default="http://127.0.0.1:8094")
    analizador.add_argument(
        "--momento", choices=("antes", "despues"), default="antes",
        help="el nombre que llevan las capturas y el JSON (antes/despues)",
    )
    analizador.add_argument("--sin-vacio", action="store_true", help="no crear la cuenta vacía")
    argumentos = analizador.parse_args()
    base = argumentos.base.rstrip("/")
    momento = argumentos.momento

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    print(f"== Revisión móvil ({momento}) contra {base} ==")
    try:
        with httpx.Client(base_url=base, timeout=120.0) as cliente:
            cliente.get("/health").raise_for_status()
    except Exception as fallo:  # noqa: BLE001
        print(f"No hay servidor en {base}: {fallo}")
        return 1

    escenario = preparar(base)
    print(f"  {escenario.resumen()}")
    token = escenario.volumen.token

    todo: dict[str, dict] = {}
    try:
        with NavegadorDeVerdad(ancho=390, alto=844) as nav:
            # El contrato de diseño define una sola paleta (la clara); el modo oscuro es
            # decisión de la app nueva y su contraste lo mide otro frente. Aquí se fija el
            # claro para que todas las capturas y medidas sean comparables entre sí.
            nav.orden(
                "Emulation.setEmulatedMedia",
                {"features": [{"name": "prefers-color-scheme", "value": "light"}]},
            )
            for ancho, alto in ANCHOS:
                todo[str(ancho)] = recorrer(nav, base, ancho, alto, token, momento)
                if not argumentos.sin_vacio:
                    vacio = el_estado_vacio(base, nav, ancho, alto, momento)
                    if vacio:
                        todo[f"vacio-{ancho}"] = vacio
    except SinNavegador as fallo:
        print(f"\nNo se puede hacer la revisión: {fallo}")
        return 1

    todo["resumen"] = resumen(todo)
    destino = CAPTURAS / f"mediciones-{momento}.json"
    destino.write_text(json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nCapturas y medidas en {CAPTURAS.relative_to(RAIZ)}")
    print(f"  {destino.name}")
    for ancho, numeros in todo["resumen"].items():
        print(
            f"  {ancho} px: {numeros['pantallas_medidas']} pantallas ·"
            f" {numeros['pantallas_con_desborde']} con desborde ·"
            f" {numeros['controles_pequenos']} controles <44 px ·"
            f" {numeros['huecos_pequenos']} huecos <8 px ·"
            f" {numeros['modales_que_no_caben']} modales que no caben"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
