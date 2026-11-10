"""Mide la demo a 360, 390, 768 y 1024 px y saca capturas (10/11/2026).

Es la misma medida que se hizo en `docs/revision-interfaz.md` para los arreglos de móvil y
tableta (desbordes, controles por debajo de 44 px y huecos por debajo de 8 px), pero hecha sobre la
**demo publicada**, que lleva el mismo CSS y el mismo JavaScript que la aplicación. Sirve para
enseñar el «después» con números, no con impresiones.

Uso:

    python deploy/medir_demo.py https://erdeivih.github.io/cuedigital-demo/
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
from scripts.navegador_cdp import NavegadorDeVerdad  # noqa: E402

URL = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
if not URL:
    raise SystemExit("Falta la URL: python deploy/medir_demo.py https://…")

SALIDA = RAIZ / "docs" / "capturas-despliegue"
SALIDA.mkdir(parents=True, exist_ok=True)
ANCHOS = ((360, 844, True), (390, 844, True), (768, 1024, False), (1024, 768, False))

# Se mide en la pantalla de tierras (la que más controles tiene) y en la de hoy.
MEDIDA = """
(() => {
  const visible = (e) => e.offsetParent !== null && e.getClientRects().length > 0;
  const controles = [...document.querySelectorAll('button, a, input, select, textarea, [role=button]')]
    .filter(visible)
    .map((e) => {
      const c = e.getBoundingClientRect();
      return { ancho: Math.round(c.width), alto: Math.round(c.height),
               etiqueta: (e.textContent || e.value || e.getAttribute('aria-label') || e.tagName).trim().slice(0, 30) };
    });
  const pequenos = controles.filter((c) => c.ancho < 44 || c.alto < 44);
  const raiz = document.documentElement;
  // Huecos por debajo de 8 px entre hermanos visibles del mismo contenedor.
  let huecosPequenos = 0;
  const contenedores = new Set([...document.querySelectorAll('div, ul, ol, nav, section')]);
  contenedores.forEach((padre) => {
    const hijos = [...padre.children].filter(visible);
    for (let i = 1; i < hijos.length; i++) {
      const a = hijos[i - 1].getBoundingClientRect();
      const b = hijos[i].getBoundingClientRect();
      const mismoRenglon = Math.abs(a.top - b.top) < 6;
      const solapanX = a.left < b.right && b.left < a.right;
      const hueco = mismoRenglon && solapanX ? Math.round(b.top - a.bottom) : null;
      if (hueco !== null && hueco > 0 && hueco < 8) huecosPequenos += 1;
    }
  });
  return JSON.stringify({
    desborde: raiz.scrollWidth - raiz.clientWidth,
    controles: controles.length,
    pequenos: pequenos.length,
    muestra: pequenos.slice(0, 5),
    huecos_pequenos: huecosPequenos,
  });
})()
"""


def captura(navegador, nombre: str) -> None:
    datos = navegador.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = SALIDA / nombre
    destino.write_bytes(base64.b64decode(datos))
    print(f"  captura: {destino.relative_to(RAIZ)}")


def ir_a(navegador, vista: str, etiqueta: str) -> None:
    navegador.evaluar(
        "(() => { const b = [...document.querySelectorAll('button, a, [role=button]')]"
        ".filter(e => e.offsetParent !== null)"
        ".find(e => (e.textContent || '').trim().toLowerCase() === %r); if (b) b.click(); })()"
        % etiqueta.lower()
    )
    navegador.esperar(
        "(document.querySelector('.app') && document.querySelector('.app').dataset.vista === %r)" % vista,
        segundos=12,
    )
    time.sleep(0.8)


def main() -> int:
    print(f"Midiendo la demo en {URL}")
    resultado = {}
    with NavegadorDeVerdad() as navegador:
        navegador.abrir(URL, esperar=1.5)
        if not navegador.esperar("document.querySelector('.app') !== null", segundos=25):
            raise SystemExit("la aplicación no ha pintado")
        ir_a(navegador, "tierras", "Tierras")
        for ancho, alto, movil in ANCHOS:
            navegador.medir(ancho, alto, movil=movil)
            time.sleep(1.0)
            medido = json.loads(navegador.evaluar(MEDIDA))
            resultado[str(ancho)] = medido
            print(
                f"  {ancho}px · desborde={medido['desborde']}px · controles={medido['controles']}"
                f" · <44px={medido['pequenos']} · huecos<8px={medido['huecos_pequenos']}"
            )
            if medido["muestra"]:
                for uno in medido["muestra"]:
                    print(f"      pequeño: {uno['etiqueta']!r} {uno['ancho']}×{uno['alto']}")
            captura(navegador, f"demo-medida-{ancho}.png")
        # La pantalla de hoy, que es la portada.
        ir_a(navegador, "hoy", "Hoy")
        navegador.medir(360, 844, movil=True)
        time.sleep(0.8)
        captura(navegador, "demo-medida-hoy-360.png")

    (SALIDA / "medidas-demo.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8", newline=""
    )
    print("\nGuardado docs/capturas-despliegue/medidas-demo.json")
    problemas = [a for a, m in resultado.items() if m["desborde"] > 0 or m["pequenos"] > 0]
    if problemas:
        print("ANCHOS CON PROBLEMA:", ", ".join(problemas))
        return 1
    print("RESULTADO: 0 desbordes y 0 controles por debajo de 44 px en los cuatro anchos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
