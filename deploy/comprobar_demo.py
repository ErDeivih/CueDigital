"""Comprueba la demo estática y saca capturas (10/11/2026).

Sirve igual para el paquete local (`servir_demo.py`) y para la URL de GitHub Pages. Comprueba lo
que pide el encargo:

1. La página responde y la aplicación pinta.
2. **El aviso de DEMO está** (no se puede confundir con la aplicación de verdad).
3. Se ven **las cinco parcelas del cliente**.
4. **El alta por referencia de seis números funciona**: se busca una referencia conocida, se
   marca el recinto y la tierra nueva aparece en la lista (guardada en el navegador).
5. Capturas a **360 y 1024 px**.

Uso:

    python deploy/comprobar_demo.py http://127.0.0.1:8100/
"""

from __future__ import annotations

import base64
import pathlib
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
from scripts.navegador_cdp import NavegadorDeVerdad  # noqa: E402

URL = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
if not URL:
    raise SystemExit("Falta la URL: python deploy/comprobar_demo.py http://127.0.0.1:8100/")

SALIDA = RAIZ / "docs" / "capturas-despliegue"
SALIDA.mkdir(parents=True, exist_ok=True)
fallos: list[str] = []


def comprobar(condicion: bool, que: str, detalle: str = "") -> None:
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {que}" + (f" — {detalle}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(que)


def captura(navegador, nombre: str) -> None:
    datos = navegador.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = SALIDA / nombre
    destino.write_bytes(base64.b64decode(datos))
    print(f"  captura: {destino.relative_to(RAIZ)}  ({destino.stat().st_size // 1024} KB)")


def texto(navegador) -> str:
    return navegador.evaluar("document.body.innerText") or ""


def pulsar(navegador, etiqueta: str, exacto: bool = False) -> bool:
    """Pulsa el primer botón/enlace visible que diga eso. Devuelve si lo encontró."""
    comparacion = (
        "(e.textContent||'').trim().toLowerCase() === %r" % etiqueta.lower()
        if exacto
        else "(e.textContent||'').trim().toLowerCase().includes(%r)" % etiqueta.lower()
    )
    return bool(
        navegador.evaluar(
            "(() => { const b = [...document.querySelectorAll('button, a, [role=button]')]"
            ".filter(e => e.offsetParent !== null).find(e => " + comparacion + ");"
            "if (b) { b.click(); return true; } return false; })()"
        )
    )


def vista(navegador) -> str:
    return navegador.evaluar(
        "(document.querySelector('.app') ? document.querySelector('.app').dataset.vista : '')"
    ) or ""


def esperar_vista(navegador, cual: str, segundos: float = 12.0) -> bool:
    return navegador.esperar(
        "(document.querySelector('.app') && document.querySelector('.app').dataset.vista === %r)"
        % cual,
        segundos=segundos,
    )


def main() -> int:
    print(f"Comprobación de la demo en {URL}")
    with NavegadorDeVerdad() as navegador:
        # Se limpia la caché del navegador: si no, una versión anterior de la demo se queda
        # pegada y la comprobación mira lo que ya no está publicado.
        navegador.abrir("about:blank", esperar=0.3)
        try:
            navegador.orden("Network.enable")
            navegador.orden("Network.clearBrowserCache")
        except Exception:
            pass
        navegador.abrir(URL, esperar=1.5)
        comprobar(
            bool(navegador.esperar("document.querySelector('.app') !== null", segundos=25)),
            "la aplicación pinta",
        )
        comprobar(
            "DEMO" in texto(navegador) and bool(navegador.evaluar("!!document.getElementById('demo-aviso')")),
            "el aviso de DEMO está en la pantalla",
        )

        navegador.medir(360, 844, movil=True)
        time.sleep(0.8)
        captura(navegador, "demo-hoy-360.png")

        comprobar(pulsar(navegador, "tierras", exacto=True), "se puede ir a Tierras")
        comprobar(esperar_vista(navegador, "tierras"), "la pantalla de tierras carga")
        time.sleep(1.0)
        cuerpo = texto(navegador)
        for alias in ("El Llano", "La Fuente", "Los Olmos", "La Dehesa", "El Barbecho"):
            comprobar(alias in cuerpo, f"se ve la parcela «{alias}»")
        captura(navegador, "demo-tierras-360.png")

        navegador.medir(1024, 768)
        time.sleep(1.0)
        captura(navegador, "demo-tierras-1024.png")

        # ── El alta por referencia de seis números ────────────────────────────────────────
        navegador.medir(390, 844, movil=True)
        time.sleep(0.6)
        comprobar(pulsar(navegador, "añadir tierras"), "se abre «Añadir tierras»")
        comprobar(esperar_vista(navegador, "alta"), "la pantalla de alta carga")
        time.sleep(1.0)
        # El camino de la referencia: la caja «O pega las referencias» y su botón.
        puesto = navegador.evaluar(
            "(() => { const c = [...document.querySelectorAll('textarea, input[type=text]')]"
            ".filter(e => e.offsetParent !== null).pop();"
            "if (!c) return false; c.focus();"
            "const proto = c.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype"
            ": window.HTMLInputElement.prototype;"
            "const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
            "setter.call(c, '47-99-0-0-903-1');"
            "c.dispatchEvent(new Event('input', {bubbles: true}));"
            "c.dispatchEvent(new Event('change', {bubbles: true})); return true; })()"
        )
        comprobar(bool(puesto), "hay una caja para pegar la referencia y se rellena")
        time.sleep(0.6)
        captura(navegador, "demo-alta-referencia-390.png")
        comprobar(pulsar(navegador, "traer las pegadas"), "se pulsa «Traer las pegadas»")
        time.sleep(3.0)
        captura(navegador, "demo-alta-hecha-390.png")
        print("  texto tras traer:", texto(navegador)[:220].replace("\n", " | "))

        # De vuelta a la lista: la tierra nueva está.
        pulsar(navegador, "tierras", exacto=True)
        comprobar(esperar_vista(navegador, "tierras"), "se vuelve a Tierras")
        time.sleep(1.5)
        lista = texto(navegador)
        guardadas = navegador.evaluar(
            "(() => { try { return JSON.parse(localStorage.getItem('cuedigital.demo.tierras') || '[]').length; }"
            "catch (e) { return -1; } })()"
        )
        comprobar(int(guardadas or 0) >= 1, "la tierra nueva queda guardada en el navegador", f"guardadas={guardadas}")
        comprobar("6 tierras" in lista.lower() or "6 tierras" in lista, "la lista pasa a seis tierras", lista[:200])
        captura(navegador, "demo-tierras-con-alta-390.png")

        # **Y su contorno**: se abre la ficha de la tierra nueva y el dibujo tiene que estar.
        # Se busca por su nombre exacto (el que quedó guardado), no por un texto supuesto.
        alias = navegador.evaluar(
            "(() => { try { const l = JSON.parse(localStorage.getItem('cuedigital.demo.tierras') || '[]');"
            "return l.length ? l[l.length - 1].alias : ''; } catch (e) { return ''; } })()"
        ) or ""
        abierta = navegador.evaluar(
            "(() => { const fila = [...document.querySelectorAll('button.tierra')]"
            ".filter(e => e.offsetParent !== null)"
            ".find(e => (e.textContent || '').includes(%r));"
            "if (!fila) { const ultima = [...document.querySelectorAll('button.tierra')].pop();"
            "if (!ultima) return false; ultima.click(); return true; }"
            "fila.click(); return true; })()" % alias
        )
        comprobar(bool(abierta), "se abre la ficha de la tierra nueva", f"alias={alias}")
        time.sleep(2.5)
        dibujo = navegador.evaluar(
            "(() => { const s = document.querySelector('svg.mapa__dibujo');"
            "if (!s) return 0; return s.querySelectorAll('path, polygon, polyline, line').length; })()"
        )
        comprobar(int(dibujo or 0) > 0, "la ficha dibuja el contorno de la parcela", f"trazos={dibujo}")
        captura(navegador, "demo-alta-contorno-390.png")
        navegador.medir(1024, 768)
        time.sleep(1.0)
        captura(navegador, "demo-alta-contorno-1024.png")

    print()
    if fallos:
        print("RESULTADO: fallan " + str(len(fallos)) + " comprobaciones:")
        for fallo in fallos:
            print("  ·", fallo)
        return 1
    print("RESULTADO: todo lo comprobado ha ido bien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
