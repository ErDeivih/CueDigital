"""Capturas y medidas para la revisión de interfaz (`task-7`).

## Para qué existe

El encargo pide un inventario de pantallas de la app nueva (`/nuevo/`) **con capturas
reales a 390 y 1024 px** y diez problemas de interfaz **con evidencia**. Una captura sin
medida acredita poco, así que este guion hace las dos cosas por pantalla:

  1. **Captura** la pantalla tal y como la ve el agricultor (desde arriba, con el ancho de
     un móvil y el de un ordenador).
  2. **Mide en el DOM** lo que se puede medir sin opinar: desbordes, controles por debajo
     del tamaño de dedo, textos por debajo del tamaño mínimo legible, textos recortados y
     el contraste WCAG de cada trozo de texto (el color del texto contra su fondo efectivo).

Y lo guarda todo en `docs/capturas-revision/`: las imágenes y un `mediciones.json` con lo
medido, para que el documento de la revisión pueda citar de dónde sale cada afirmación.

**No cambia nada de la aplicación**: solo abre un navegador, pulsa lo que pulsaría el
agricultor y guarda fotos y números.

## Cómo se lanza

Necesita un servidor de verdad con base y adjuntos temporales (en `8091`:

```powershell
cd backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\\cd-revision-8091\\datos.db"
$env:CUEDIGITAL_ADJUNTOS="$env:TEMP\\cd-revision-8091\\adjuntos"
$env:CUEDIGITAL_SECRETO="revision"
$env:CUEDIGITAL_ENTORNO="pruebas"
$env:CUEDIGITAL_ITERACIONES_PBKDF2="100000"
..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8091
```

Y después:

```powershell
..\\.venv\\Scripts\\python.exe scripts\\capturar_pantallas_para_la_revision.py http://127.0.0.1:8091
```

Si no hay navegador instalado, el guion lo dice y sale con código 1 sin inventar capturas.
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
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
ANCHOS = ((390, 844), (1024, 900))

# Lo que se mide en cada pantalla. Devuelve un objeto con lo que se puede medir en el DOM:
#   · desborde_horizontal: si la página se sale del ancho (scroll horizontal).
#   · controles: todos los botones y enlaces que se ven, con su alto y su ancho.
#   · pequenos: los que no llegan al tamaño de dedo (44 px) —el mínimo del proyecto—.
#   · textos_pequenos: cada trozo de texto con su tamaño en píxeles (la letra base del
#     contrato es 18 px; por debajo de eso, a partir de los 50 años no se lee).
#   · recortados: textos que se salen de su caja y se ven cortados con puntos suspensivos
#     o tapados (scrollWidth > clientWidth con el desborde oculto).
#   · contrastes: color del texto, fondo efectivo (subiendo por los padres), tamaño y texto,
#     para calcular el contraste WCAG en Python.
#   · bloques: los hijos visibles de la pantalla, con su posición, para saber qué queda por
#     debajo del primer pantallazo (información que exige scroll).
MEDIR_JS = r"""(() => {
  const seVe = (n) => { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const raiz = document.querySelector('.contenido') || document.body;
  const texto = (n) => (n.innerText || n.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 70);
  const elFondo = (n) => {
    let e = n;
    while (e && e !== document.documentElement) {
      const c = getComputedStyle(e).backgroundColor;
      if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c;
      e = e.parentElement;
    }
    return 'rgb(255, 255, 255)';
  };
  const controles = Array.from(document.querySelectorAll(
      'button, a, input, select, textarea, [role="button"]'
    )).filter(seVe);
  const losControles = controles.map((n) => {
    const r = n.getBoundingClientRect();
    const zona = n.closest('.contenido') ? 'contenido'
      : n.closest('.barra-lateral') ? 'lateral'
      : n.closest('[data-nav-inferior]') ? 'inferior' : 'cabecera';
    return {
      tipo: n.tagName.toLowerCase(),
      texto: (n.innerText || n.getAttribute('aria-label') || n.getAttribute('placeholder') || n.type || '').replace(/\s+/g, ' ').trim().slice(0, 55),
      alto: Math.round(r.height * 10) / 10,
      ancho: Math.round(r.width * 10) / 10,
      arriba: Math.round(r.top),
      zona,
      deshabilitado: Boolean(n.disabled) || n.getAttribute('aria-disabled') === 'true',
      href: n.getAttribute ? (n.getAttribute('href') || '') : '',
    };
  });
  const pequenos = losControles.filter((c) => c.alto > 0 && c.alto < 44);
  const enlaces = losControles.filter((c) => c.tipo === 'a' && c.href)
    .map((c) => ({ texto: c.texto, href: c.href, zona: c.zona }));
  const deshabilitados = losControles.filter((c) => c.deshabilitado)
    .map((c) => ({ texto: c.texto, zona: c.zona }));
  const estilosClave = (selector) => Array.from(document.querySelectorAll(selector)).filter(seVe).slice(0, 6)
    .map((n) => {
      const s = getComputedStyle(n);
      return { selector, texto: (n.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 45),
               color: s.color, fondo: elFondo(n), px: parseFloat(s.fontSize) || 0 };
    });
  const hojas = Array.from(raiz.querySelectorAll('*')).filter(
    (n) => n.children.length === 0 && (n.textContent || '').trim() && seVe(n)
  );
  const textosPequenos = [];
  const recortados = [];
  const contrastes = [];
  for (const n of hojas) {
    const s = getComputedStyle(n);
    const tam = parseFloat(s.fontSize) || 0;
    const t = (n.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 55);
    if (tam && tam < 16) textosPequenos.push({ px: tam, texto: t });
    const seCorta = n.scrollWidth > n.clientWidth + 2
      && (s.overflow === 'hidden' || s.overflowX === 'hidden' || s.textOverflow === 'ellipsis');
    if (seCorta) recortados.push({ texto: t, anchoCaja: n.clientWidth, anchoTexto: n.scrollWidth });
    if (t) contrastes.push([s.color, elFondo(n), tam, t].join('|'));
  }
  const bloques = Array.from(raiz.children).filter(seVe).map((n) => {
    const r = n.getBoundingClientRect();
    return {
      etiqueta: n.tagName.toLowerCase() + (n.className ? '.' + String(n.className).split(' ')[0] : ''),
      arriba: Math.round(r.top + raiz.scrollTop),
      alto: Math.round(r.height),
      texto: texto(n),
    };
  });
  const porDebajo = losControles.filter((c) => c.arriba > window.innerHeight).length;
  const cabecera = document.querySelector('.barra-superior');
  const h1 = document.querySelector('.contenido h1');
  return JSON.stringify({
    vista: (document.querySelector('[data-vista]') || {}).getAttribute
      ? document.querySelector('[data-vista]').getAttribute('data-vista') : null,
    estado: document.querySelector('[data-estado]')
      ? document.querySelector('[data-estado]').getAttribute('data-estado') : null,
    titulo: (h1 || {}).innerText || '',
    cabecera_alto: cabecera ? Math.round(cabecera.getBoundingClientRect().height) : 0,
    contenido_arriba: (() => { const c = document.querySelector('.contenido'); return c ? Math.round(c.getBoundingClientRect().top) : 0; })(),
    h1: h1 ? { alto: Math.round(h1.getBoundingClientRect().height), ancho: Math.round(h1.getBoundingClientRect().width) } : null,
    desborde_horizontal: document.documentElement.scrollWidth - window.innerWidth,
    alto_pagina: document.documentElement.scrollHeight,
    alto_ventana: window.innerHeight,
    controles: losControles,
    pequenos,
    enlaces,
    deshabilitados,
    estilos_clave: [
      ...estilosClave('.pestanas .pastilla'),
      ...estilosClave('.pastilla--activa'),
      ...estilosClave('.tarjeta-dato__cifra'),
      ...estilosClave('.tarjeta-dato__nota'),
      ...estilosClave('.grupo__cuenta'),
      ...estilosClave('.tierra__detalle'),
      ...estilosClave('.calendario__numero'),
      ...estilosClave('.calendario__hoy'),
      ...estilosClave('.nav__enlace, .nav__enlace--activo'),
    ],
    textos_pequenos: textosPequenos,
    recortados,
    contrastes: contrastes.slice(0, 400),
    bloques,
    controles_por_debajo: porDebajo,
    texto: (document.body ? document.body.innerText : '').replace(/\n{3,}/g, '\n\n').slice(0, 6000),
  });
})()"""


def la_luminancia(color: str) -> float:
    """La luminancia relativa de un color `rgb(...)`/`rgba(...)`, según la WCAG."""
    numeros = [float(n) for n in re.findall(r"[\d.]+", color)[:3]]
    if len(numeros) < 3:
        return 0.0
    canales = []
    for valor in numeros:
        c = valor / 255.0
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def el_contraste(un_color: str, un_fondo: str) -> float:
    a, b = la_luminancia(un_color), la_luminancia(un_fondo)
    claro, oscuro = max(a, b), min(a, b)
    return round((claro + 0.05) / (oscuro + 0.05), 2)


def captura(nav: NavegadorDeVerdad, nombre: str) -> pathlib.Path:
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    crudo = nav.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = CAPTURAS / f"{nombre}.png"
    destino.write_bytes(base64.b64decode(crudo))
    return destino


def arriba_del_todo(nav: NavegadorDeVerdad) -> None:
    """Coloca la pantalla arriba (la captura tiene que ser lo primero que ve el agricultor)."""
    nav.evaluar(
        "(() => {"
        " window.scrollTo(0, 0);"
        " const m = document.querySelector('.contenido');"
        " if (m) m.scrollTo(0, 0);"
        " return true; })()"
    )
    time.sleep(0.25)


def medir(nav: NavegadorDeVerdad) -> dict:
    crudo = nav.evaluar(MEDIR_JS)
    datos = json.loads(crudo) if crudo else {}
    contrastes = []
    for linea in datos.get("contrastes") or []:
        color, fondo, tamano, texto = (linea.split("|") + ["", "", "", ""])[:4]
        if not color or not texto:
            continue
        try:
            contrastes.append(
                {
                    "contraste": el_contraste(color, fondo),
                    "px": float(tamano or 0),
                    "texto": texto,
                }
            )
        except (ValueError, ZeroDivisionError):
            continue
    datos["contrastes"] = {
        "medidos": len(contrastes),
        "por_debajo_de_4_5": sorted(
            [c for c in contrastes if c["contraste"] < 4.5], key=lambda c: c["contraste"]
        )[:12],
        "por_debajo_de_3": sorted(
            [c for c in contrastes if c["contraste"] < 3.0], key=lambda c: c["contraste"]
        )[:12],
    }
    return datos


def la_sesion(nav: NavegadorDeVerdad, base: str, token: str) -> None:
    nav.abrir(base, esperar=0.8)
    nav.evaluar(f"localStorage.setItem('cuedigital.token', {json.dumps(token)})")
    nav.abrir(f"{base}/nuevo/", esperar=1.0)


# Las pantallas que se recorren, en orden. Cada una: clave (nombre del fichero), nombre para
# el documento, los pasos para llegar (destino de la barra o clic concreto) y, si es una
# ventana, el selector que la cierra.
PANTALLAS = [
    {"clave": "hoy", "nombre": "Hoy", "pasos": []},
    {"clave": "tierras", "nombre": "Mis tierras", "pasos": [("destino", "tierras")]},
    {
        "clave": "tierra",
        "nombre": "Ficha de una tierra",
        "pasos": [("destino", "tierras"), ("pulsar", "[data-tierra-id]")],
    },
    {"clave": "apuntar", "nombre": "Apuntar un trabajo (labor)", "pasos": [("destino", "apuntar")]},
    {
        "clave": "apuntar-tratamiento",
        "nombre": "Apuntar un tratamiento",
        "pasos": [("destino", "apuntar"), ("pulsar", "[data-apuntar-tab=\"tratamiento\"]")],
    },
    {
        "clave": "alta",
        "nombre": "Añadir tierras",
        "pasos": [("destino", "tierras"), ("pulsar", "[data-accion=anadir-tierras]")],
    },
    {
        "clave": "sigpac",
        "nombre": "Ventana del SIGPAC",
        "pasos": [
            ("destino", "tierras"),
            ("pulsar", "[data-accion=anadir-tierras]"),
            ("pulsar", "[data-abrir-ventana-sigpac]"),
        ],
        "cerrar": "[data-ventana-cerrar]",
        "vista": "ventana",
    },
    {"clave": "cuaderno", "nombre": "Cuaderno", "pasos": [("destino", "cuaderno")]},
    {"clave": "productos", "nombre": "Productos y abonos", "pasos": [("destino", "productos")]},
    {"clave": "calendario", "nombre": "Calendario", "pasos": [("destino", "calendario")]},
    {"clave": "trabajos", "nombre": "Trabajos", "pasos": [("destino", "trabajos")]},
    {"clave": "facturas", "nombre": "Facturas", "pasos": [("destino", "facturas")]},
    {"clave": "mas", "nombre": "Más", "pasos": [("destino", "mas")], "solo_movil": True},
]


def recorrer(nav: NavegadorDeVerdad, base: str, ancho: int, alto: int, token: str) -> dict:
    print(f"\n== {ancho}×{alto} px ==")
    nav.medir(ancho, alto, movil=ancho <= 712)
    la_sesion(nav, base, token)
    if not esperar_estado(nav, "listo"):
        print("  (la app no llega a «listo»)")

    medidas: dict[str, dict] = {}
    for pantalla in PANTALLAS:
        clave = pantalla["clave"]
        if pantalla.get("solo_movil") and ancho > 712:
            print(f"  -- {clave}: no se alcanza a {ancho} px (no hay destino «Más» en escritorio)")
            continue
        print(f"  -- {pantalla['nombre']} ({clave})")
        for tipo, valor in pantalla["pasos"]:
            if tipo == "destino":
                if not ir_a_una_vista(nav, valor):
                    print(f"     (no se llega a {valor})")
            else:
                clic_en_visible(nav, valor)
        if pantalla.get("vista") == "ventana":
            nav.esperar("!!document.querySelector('[data-ventana-sigpac]')", segundos=15)
        else:
            nav.esperar(
                f"!!document.querySelector('[data-vista=\"{clave if clave != 'apuntar-tratamiento' else 'apuntar'}\"]')",
                segundos=15,
            )
            esperar_lo_pintado(nav, clave if clave != "apuntar-tratamiento" else "apuntar")
            if clave == "apuntar-tratamiento":
                nav.esperar("document.querySelectorAll('[data-apuntar-producto]').length > 0"
                            " || document.body.innerText.toLowerCase().includes('no hay')", segundos=25)
        time.sleep(1.2)  # los mapas y las miniaturas llegan después del HTML
        arriba_del_todo(nav)
        datos = medir(nav)
        datos["pantalla"] = pantalla["nombre"]
        datos["ruta"] = " / ".join(f"{t}:{v}" for t, v in pantalla["pasos"]) or "arranque"
        medidas[clave] = datos

        fichero = captura(nav, f"{clave}-{ancho}")
        print(
            f"     captura {fichero.name} · desborde {datos.get('desborde_horizontal')} px ·"
            f" {len(datos.get('pequenos') or [])} controles <44 px ·"
            f" {len(datos.get('textos_pequenos') or [])} textos <16 px ·"
            f" {len(datos.get('recortados') or [])} recortados"
        )
        if pantalla.get("cerrar"):
            nav.evaluar(
                "(() => { const b = document.querySelector(" + json.dumps(pantalla["cerrar"]) + ");"
                " if (!b) return false; b.click(); return true; })()"
            )
            nav.esperar("!document.querySelector('[data-ventana-sigpac]')", segundos=10)
    return medidas


def el_modo(nav: NavegadorDeVerdad, modo: str) -> None:
    """Fija el modo claro u oscuro del sistema, para que la captura no dependa del Windows que la hace."""
    nav.orden(
        "Emulation.setEmulatedMedia",
        {"features": [{"name": "prefers-color-scheme", "value": modo}]},
    )
    time.sleep(0.3)


def el_mismo_recorrido_en_claro(nav: NavegadorDeVerdad, base: str, token: str) -> dict:
    """La app tiene además una paleta oscura. Se captura el mismo recorrido en claro (el del contrato).

    El modo oscuro es una decisión de la app nueva (su CSS tiene `prefers-color-scheme: dark`), no del
    contrato: `DESIGN.md` solo define la paleta clara. Para que la revisión no confunda «la app se ve
    así» con «el Windows que hizo la captura estaba en oscuro», se hacen las dos y se comparan.
    """
    print("\n== El mismo recorrido en modo claro (390 px) ==")
    el_modo(nav, "light")
    nav.medir(390, 844, movil=True)
    la_sesion(nav, base, token)
    esperar_estado(nav, "listo")
    medidas: dict[str, dict] = {}
    for clave, nombre, pasos in (
        ("hoy", "Hoy", []),
        ("tierras", "Mis tierras", [("destino", "tierras")]),
        ("apuntar", "Apuntar un trabajo", [("destino", "apuntar")]),
        ("cuaderno", "Cuaderno", [("destino", "cuaderno")]),
    ):
        for tipo, valor in pasos:
            if tipo == "destino":
                ir_a_una_vista(nav, valor)
        nav.esperar(f"!!document.querySelector('[data-vista=\"{clave}\"]')", segundos=15)
        esperar_lo_pintado(nav, clave)
        time.sleep(1.0)
        arriba_del_todo(nav)
        datos = medir(nav)
        datos["pantalla"] = nombre
        medidas[clave] = datos
        print(f"  -- {nombre} ({clave})")
        print(f"     captura {captura(nav, f'{clave}-claro-390').name}")
    el_modo(nav, "dark")
    return medidas


def el_estado_vacio(base: str, nav: NavegadorDeVerdad) -> dict | None:
    """La pantalla de tierras de una cuenta recién creada: el vacío de verdad, no simulado."""
    print("\n== estado vacío (cuenta sin tierras, 390 px) ==")
    token = cuenta_vacia(base)
    nav.medir(390, 844, movil=True)
    la_sesion(nav, base, token)
    esperar_estado(nav, "vacio", segundos=25)
    ir_a_una_vista(nav, "tierras")
    nav.esperar("document.querySelector('[data-vista=\"tierras\"]') !== null", segundos=15)
    time.sleep(0.8)
    arriba_del_todo(nav)
    datos = medir(nav)
    # El enlace del estado vacío: a dónde lleva de verdad.
    datos["enlace_vacio"] = nav.evaluar(
        "(() => { const a = document.querySelector('[data-traer-tierras]');"
        " return a ? a.getAttribute('href') : null; })()"
    )
    captura(nav, "vacio-tierras-390")
    print(f"  captura vacio-tierras-390.png · el botón del vacío lleva a {datos['enlace_vacio']!r}")
    return datos


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("base", nargs="?", default="http://127.0.0.1:8091")
    analizador.add_argument("--sin-vacio", action="store_true", help="no crear la cuenta vacía")
    argumentos = analizador.parse_args()
    base = argumentos.base.rstrip("/")

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    print(f"== Capturas de la revisión de interfaz ({base}) ==")
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
            el_modo(nav, "dark")
            for ancho, alto in ANCHOS:
                todo[str(ancho)] = recorrer(nav, base, ancho, alto, token)
            todo["claro"] = el_mismo_recorrido_en_claro(nav, base, token)
            if not argumentos.sin_vacio:
                vacio = el_estado_vacio(base, nav)
                if vacio:
                    todo["vacio-390"] = vacio
    except SinNavegador as fallo:
        print(f"\nNo se puede hacer la revisión: {fallo}")
        return 1

    destino = CAPTURAS / "mediciones.json"
    destino.write_text(json.dumps(todo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nCapturas y medidas en {CAPTURAS.relative_to(RAIZ)}")
    print(f"  {destino.name}: {sum(len(v) for v in todo.values())} pantallas medidas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
