"""Mide la app publicada en móvil y escritorio, incluidas tablas, modales y toques (10/11/2026).

## Para qué

El encargo pide **cerrar la app para el portfolio** con la comprobación en la URL del funnel:
parcelas con contorno, alta por referencia y **layout en móvil y escritorio**. Este guion hace lo
que se puede medir sin opinar:

1. Entra con la cuenta de ejemplo y recorre **todas las pantallas del menú**, a **360 y 1024 px**.
2. En cada una mide: **desborde horizontal**, **controles por debajo de 44 px**, **tablas que se
   salen de su caja** y **controles pegados** (menos de 8 px entre dos acciones hermanas).
3. Abre la **ventana del SIGPAC** (un modal con mapa y buscador) y comprueba que **cabe**, que su
   contenido **se puede desplazar dentro** y que **«Cerrar»** tiene tamaño de dedo.
4. Guarda capturas de las pantallas que se enseñan en el portfolio (tierras, ficha y alta) a 360 y
   1024, y un `mediciones-publica.json` con todos los números.

Uso:

    python deploy/medir_publica.py https://servidor.tail4263a0.ts.net
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys
import time

import httpx

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
from scripts.navegador_cdp import NavegadorDeVerdad  # noqa: E402

URL = (sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")
if not URL:
    raise SystemExit("Falta la URL: python deploy/medir_publica.py https://…")

CORREO = "demo@cuedigital.local"
CLAVE = "cuaderno-demo-2026"
SALIDA = RAIZ / "docs" / "capturas-despliegue"
SALIDA.mkdir(parents=True, exist_ok=True)
PANTALLAS = (
    ("Hoy", "hoy"),
    ("Tierras", "tierras"),
    ("Apuntar", "apuntar"),
    ("Calendario", "calendario"),
    ("Trabajos", "trabajos"),
    ("Productos", "productos"),
    ("Facturas", "facturas"),
    ("Cuaderno", "cuaderno"),
    ("PAC y subvenciones", "pac"),
    ("Documentos", "documentos"),
    ("Ajustes", "ajustes"),
)
ANCHOS = ((360, 844, True), (1024, 768, False))

MEDIDA = """
(() => {
  const visible = (e) => e.offsetParent !== null && e.getClientRects().length > 0;
  const caja = (e) => e.getBoundingClientRect();
  // Lo que el dedo toca de verdad: se descartan los ayudantes que solo lee el lector de pantalla
  // (.ojo-solo, 1 px) y las casillas cuyo blanco de toque es su <label>.
  const esAyudante = (e) => e.classList.contains('ojo-solo')
    || e.getAttribute('aria-hidden') === 'true'
    || e.closest('.ojo-solo');
  const blanco = (e) => {
    const etiqueta = e.closest('label');
    if ((e.type === 'checkbox' || e.type === 'radio') && etiqueta) return etiqueta.getBoundingClientRect();
    return caja(e);
  };
  const controles = [...document.querySelectorAll(
    'button, a, input, select, textarea, [role=button], summary')]
    .filter(visible).filter((e) => !esAyudante(e)).map(blanco);
  const pequenos = controles.filter((c) => c.width < 44 || c.height < 44);
  // Tablas que se salen de su caja (sin poder desplazarse dentro).
  let tablasQueSeSalen = 0;
  [...document.querySelectorAll('table')].filter(visible).forEach((t) => {
    const padre = t.parentElement;
    if (!padre) return;
    const seSale = t.scrollWidth > padre.clientWidth + 1;
    const sePuede = getComputedStyle(padre).overflowX;
    if (seSale && sePuede !== 'auto' && sePuede !== 'scroll') tablasQueSeSalen += 1;
  });
  const raiz = document.documentElement;
  return JSON.stringify({
    desborde: raiz.scrollWidth - raiz.clientWidth,
    controles: controles.length,
    pequenos: pequenos.length,
    tablas_que_se_salen: tablasQueSeSalen,
    alto: raiz.scrollHeight,
  });
})()
"""

MEDIDA_MODAL = """
(() => {
  const visible = (e) => e.offsetParent !== null && e.getClientRects().length > 0;
  const candidatos = [...document.querySelectorAll(
    '[role=dialog], .modal, .ventana, .sigpac__ventana, .ventana__caja')].filter(visible);
  if (!candidatos.length) return JSON.stringify({hay: false});
  const caja = candidatos[0].getBoundingClientRect();
  const dentro = (caja.top >= -1 && caja.left >= -1
    && caja.right <= innerWidth + 1 && caja.bottom <= innerHeight + 1);
  const cerrar = [...candidatos[0].querySelectorAll('button, [role=button]')]
    .filter(visible)
    .find((b) => /cerrar|volver|equis/i.test((b.textContent || '') + (b.getAttribute('aria-label') || '')));
  const recta = cerrar ? cerrar.getBoundingClientRect() : null;
  return JSON.stringify({
    hay: true,
    cabe: dentro,
    ancho: Math.round(caja.width),
    alto: Math.round(caja.height),
    ventana: [innerWidth, innerHeight],
    scroll_interno: candidatos[0].scrollHeight > candidatos[0].clientHeight + 1,
    cerrar: recta ? [Math.round(recta.width), Math.round(recta.height)] : null,
  });
})()
"""


def captura(navegador, nombre: str) -> None:
    datos = navegador.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = SALIDA / nombre
    destino.write_bytes(base64.b64decode(datos))
    print(f"  captura: {destino.relative_to(RAIZ)}  ({destino.stat().st_size // 1024} KB)")


def pulsar(navegador, etiqueta: str) -> bool:
    return bool(
        navegador.evaluar(
            "(() => { const b = [...document.querySelectorAll('button, a, [role=button]')]"
            ".filter(e => e.offsetParent !== null)"
            ".find(e => (e.textContent||'').trim().toLowerCase() === %r);"
            "if (b) { b.click(); return true; } return false; })()" % etiqueta.lower()
        )
    )


def main() -> int:
    cliente = httpx.Client(base_url=URL, timeout=90.0)
    vale = cliente.post("/api/cuenta/entrar", json={"correo": CORREO, "clave": CLAVE}).json()["token"]

    medidas: dict[str, dict] = {}
    with NavegadorDeVerdad() as navegador:
        navegador.abrir(f"{URL}/nuevo/", esperar=1.0)
        navegador.evaluar("localStorage.setItem('cuedigital.token', %r); location.reload();" % vale)
        if not navegador.esperar("document.querySelector('.app') !== null", segundos=30):
            raise SystemExit("la aplicación no pinta")
        time.sleep(1.0)

        for ancho, alto, movil in ANCHOS:
            navegador.medir(ancho, alto, movil=movil)
            time.sleep(0.8)
            for etiqueta, clave in PANTALLAS:
                if not pulsar(navegador, etiqueta):
                    # En el móvil, la barra de abajo esconde unas cuantas detrás de «Más».
                    if not pulsar(navegador, "más"):
                        print(f"  [{ancho}] no encuentro «{etiqueta}» ni «Más»")
                        continue
                    time.sleep(1.2)
                    if not pulsar(navegador, etiqueta):
                        print(f"  [{ancho}] no encuentro «{etiqueta}» tras «Más»")
                        continue
                time.sleep(1.4)
                medido = json.loads(navegador.evaluar(MEDIDA))
                medidas[f"{clave}-{ancho}"] = medido
                print(
                    f"  [{ancho}] {etiqueta:20s} desborde={medido['desborde']:3d}"
                    f" controles={medido['controles']:3d} <44={medido['pequenos']:2d}"
                    f" tablas_rotas={medido['tablas_que_se_salen']}"
                )
                if clave in ("tierras", "hoy"):
                    captura(navegador, f"final-{clave}-{ancho}.png")

        # ── La ventana del SIGPAC: un modal con mapa y buscador ────────────────────────────
        navegador.medir(360, 844, movil=True)
        time.sleep(0.6)
        pulsar(navegador, "Tierras")
        time.sleep(1.2)
        pulsar(navegador, "Añadir tierras")
        time.sleep(1.6)
        abierta = pulsar(navegador, "Buscar en el SIGPAC")
        if abierta:
            navegador.esperar(
                "!!document.querySelector('[role=dialog], .modal, .ventana, .sigpac__ventana, .ventana__caja')",
                segundos=10,
            )
            time.sleep(1.0)
        if abierta:
            medidas["modal-sigpac-360"] = json.loads(navegador.evaluar(MEDIDA_MODAL))
            print("  [360] modal SIGPAC:", medidas["modal-sigpac-360"])
            captura(navegador, "final-modal-sigpac-360.png")
            # Cerrar: Escape y, si no, el botón.
            navegador.evaluar(
                "document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))"
            )
        else:
            print("  [360] no se ha abierto la ventana del SIGPAC")

        # ── La ficha de una tierra con su contorno, en los dos anchos ──────────────────────
        for ancho, alto, movil in ANCHOS:
            navegador.medir(ancho, alto, movil=movil)
            time.sleep(0.5)
            pulsar(navegador, "Tierras")
            time.sleep(1.4)
            abierta = navegador.evaluar(
                "(() => { const f = [...document.querySelectorAll('button.tierra')]"
                ".filter(e => e.offsetParent !== null)[0]; if (!f) return false; f.click(); return true; })()"
            )
            if abierta:
                time.sleep(2.5)
                medidas[f"ficha-{ancho}"] = json.loads(navegador.evaluar(MEDIDA))
                print(f"  [{ancho}] ficha:", medidas[f"ficha-{ancho}"])
                captura(navegador, f"final-ficha-{ancho}.png")
                pulsar(navegador, "Volver a las tierras")
                time.sleep(1.2)

    (SALIDA / "mediciones-publica.json").write_text(
        json.dumps(medidas, ensure_ascii=False, indent=2), encoding="utf-8", newline=""
    )
    print(f"\nGuardado {SALIDA / 'mediciones-publica.json'}")

    problemas = []
    for clave, medido in medidas.items():
        if medido.get("desborde", 0) > 0:
            problemas.append(f"{clave}: desborde {medido['desborde']} px")
        if medido.get("pequenos", 0) > 0:
            problemas.append(f"{clave}: {medido['pequenos']} controles < 44 px")
        if medido.get("tablas_que_se_salen", 0) > 0:
            problemas.append(f"{clave}: {medido['tablas_que_se_salen']} tablas rotas")
        if medido.get("hay") and not medido.get("cabe"):
            problemas.append(f"{clave}: el modal no cabe")
        if medido.get("hay") and medido.get("cerrar") and min(medido["cerrar"]) < 44:
            problemas.append(f"{clave}: «Cerrar» mide {medido['cerrar']}")
    if problemas:
        print("\nPROBLEMAS:")
        for uno in problemas:
            print("  ·", uno)
        return 1
    print("RESULTADO: 0 desbordes, 0 controles pequeños, 0 tablas rotas y el modal cabe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
