"""Comprueba la app publicada y saca las capturas de 360 y 1024 (09/11/2026).

QUÉ COMPRUEBA, Y POR QUÉ ASÍ
============================

1. Entra en la cuenta de ejemplo **por la API pública** (dirección del servidor de casa).
2. Abre `/nuevo/` en Chrome de verdad, mete el vale en el almacén del navegador y recarga: así
   se ve la pantalla como la vería el agricultor, sin tocar el servidor.
3. Va a «Tierras» y comprueba que **aparecen las cinco parcelas del cliente** con su nombre.
4. Comprueba que **se ha pintado al menos un mapa** (la imagen del contorno cargada de verdad,
   `naturalWidth > 0`), que es la prueba de que el backend del servidor está contestando.
5. Guarda capturas a **360 y 1024 px** en `docs/capturas-despliegue/`.

Uso:

    python deploy/comprobar_publica.py https://<url-publica>
"""

from __future__ import annotations

import base64
import pathlib
import sys
import time

import httpx

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
from scripts.navegador_cdp import NavegadorDeVerdad  # noqa: E402

URL = (sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")
if not URL:
    raise SystemExit("Falta la URL pública: python deploy/comprobar_publica.py https://…")

CORREO = "demo@cuedigital.local"
CLAVE = "cuaderno-demo-2026"
SALIDA = RAIZ / "docs" / "capturas-despliegue"
SALIDA.mkdir(parents=True, exist_ok=True)

fallos: list[str] = []


def comprobar(condicion: bool, que: str, detalle: str = "") -> None:
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {que}" + (f" — {detalle}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(que)


def captura(navegador, nombre: str) -> pathlib.Path:
    datos = navegador.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = SALIDA / nombre
    destino.write_bytes(base64.b64decode(datos))
    print(f"  captura: {destino.relative_to(RAIZ)}  ({destino.stat().st_size // 1024} KB)")
    return destino


def main() -> int:
    print(f"Comprobación de la app publicada en {URL}")
    cliente = httpx.Client(base_url=URL, timeout=60.0)
    salud = cliente.get("/health")
    comprobar(salud.status_code == 200, "el servidor del túnel contesta /health", str(salud.status_code))
    entrada = cliente.post("/api/cuenta/entrar", json={"correo": CORREO, "clave": CLAVE})
    comprobar(entrada.status_code == 200, "la cuenta de ejemplo entra por la API pública",
              f"{entrada.status_code} {entrada.text[:120]}")
    if entrada.status_code != 200:
        return 1
    vale = entrada.json()["token"]

    # La finca que se ve en la pantalla, por la API (es la misma que pinta).
    tierras = cliente.get("/api/nuevo/tierras", headers={"Authorization": f"Bearer {vale}"}).json()
    lista = tierras.get("tierras") or []
    comprobar(len(lista) == 5, "la finca de ejemplo tiene sus cinco parcelas", f"{len(lista)}")

    with NavegadorDeVerdad() as navegador:
        navegador.abrir(f"{URL}/nuevo/")
        # El vale vive en el almacén del navegador de ESTE origen; sin él la pantalla pediría permiso.
        navegador.evaluar(
            "localStorage.setItem('cuedigital.token', %r); location.reload();" % vale
        )
        time.sleep(3.0)
        # Ir a «Tierras» (la pestaña de abajo en el móvil y de la barra en el ordenador).
        navegador.evaluar(
            "(() => { const b = [...document.querySelectorAll('[data-vista], a, button')]"
            ".find(e => (e.textContent || '').trim() === 'Tierras'); if (b) b.click(); return !!b; })()"
        )
        time.sleep(2.5)
        texto = navegador.evaluar("document.body.innerText")
        comprobar("Tierras" in texto or "tierras" in texto, "la pantalla de tierras carga")
        for alias in ("El Prado", "El Alto", "La Vega", "Las Eras", "El Visor"):
            comprobar(alias in texto, f"la parcela «{alias}» se ve en la lista",
                      texto[:200] if alias not in texto else "")

        # Un mapa pintado de verdad: la imagen del contorno cargada.
        cargados = navegador.evaluar(
            "(() => [...document.images].filter(i => i.src.includes('/api/mapa/') && i.naturalWidth > 0).length)()"
        )
        comprobar(int(cargados or 0) >= 1, "hay al menos un mapa con su contorno cargado",
                  f"cargados={cargados}")

        navegador.medir(360, 844, movil=True)
        time.sleep(1.2)
        captura(navegador, "tierras-360.png")
        navegador.medir(1024, 768)
        time.sleep(1.2)
        captura(navegador, "tierras-1024.png")

        # Y la ficha de una tierra, con su mapa, en los dos anchos.
        navegador.medir(360, 844, movil=True)
        time.sleep(0.8)
        navegador.evaluar(
            "(() => { const c = [...document.querySelectorAll('[data-tierra], li, button, a')]"
            ".find(e => (e.textContent || '').includes('El Prado')); if (c) c.click(); return !!c; })()"
        )
        time.sleep(2.5)
        texto_ficha = navegador.evaluar("document.body.innerText")
        comprobar("El Prado" in texto_ficha, "se abre la ficha de una tierra")
        cargados_ficha = navegador.evaluar(
            "(() => [...document.images].filter(i => i.src.includes('/api/mapa/') && i.naturalWidth > 0).length)()"
        )
        comprobar(int(cargados_ficha or 0) >= 1, "la ficha enseña el mapa con el contorno",
                  f"cargados={cargados_ficha}")
        captura(navegador, "ficha-360.png")
        navegador.medir(1024, 768)
        time.sleep(1.2)
        captura(navegador, "ficha-1024.png")

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
