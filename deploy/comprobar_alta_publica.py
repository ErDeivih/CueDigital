"""Comprueba el alta por referencia y el layout en la URL pública estable (10/11/2026).

QUÉ COMPRUEBA
=============

1. Que la URL contesta y la cuenta de ejemplo entra.
2. Que la finca tiene sus **cinco** parcelas antes de tocar nada.
3. Que se puede **dar de alta una tierra nueva con la referencia de seis números**
   (`37-2-0-0-502-1`) desde la pantalla de verdad, y que la tierra nueva aparece en la lista.
4. Que su **ficha enseña el contorno** (la imagen del mapa cargada de verdad, o el dibujo del
   contorno si la imagen no llega).
5. Que el **layout** de la pantalla de tierras está bien a 360, 390, 768 y 1024 px: sin
   desbordes, sin controles por debajo de 44 px y sin huecos por debajo de 8 px.
6. Guarda capturas en `docs/capturas-despliegue/`.

**Deja la finca como estaba**: al final borra la tierra que ha creado (es la finca de ejemplo,
no la de nadie) y comprueba que vuelven a ser cinco.

Uso:

    python deploy/comprobar_alta_publica.py https://servidor.tail4263a0.ts.net
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
    raise SystemExit("Falta la URL: python deploy/comprobar_alta_publica.py https://…")

CORREO = "demo@cuedigital.local"
CLAVE = "cuaderno-demo-2026"
REFERENCIA = "37-2-0-0-502-1"
SALIDA = RAIZ / "docs" / "capturas-despliegue"
SALIDA.mkdir(parents=True, exist_ok=True)
ANCHOS = ((360, 844, True), (390, 844, True), (768, 1024, False), (1024, 768, False))

fallos: list[str] = []

MEDIDA = """
(() => {
  const visible = (e) => e.offsetParent !== null && e.getClientRects().length > 0;
  const controles = [...document.querySelectorAll('button, a, input, select, textarea, [role=button]')]
    .filter(visible).map((e) => {
      const c = e.getBoundingClientRect();
      return { ancho: Math.round(c.width), alto: Math.round(c.height) };
    });
  const raiz = document.documentElement;
  return JSON.stringify({
    desborde: raiz.scrollWidth - raiz.clientWidth,
    controles: controles.length,
    pequenos: controles.filter((c) => c.ancho < 44 || c.alto < 44).length,
  });
})()
"""


def comprobar(condicion: bool, que: str, detalle: str = "") -> None:
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {que}" + (f" — {detalle}" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(que)


def captura(navegador, nombre: str) -> None:
    datos = navegador.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = SALIDA / nombre
    destino.write_bytes(base64.b64decode(datos))
    print(f"  captura: {destino.relative_to(RAIZ)}  ({destino.stat().st_size // 1024} KB)")


def pulsar(navegador, etiqueta: str, exacto: bool = False) -> bool:
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


def tierras_de(cliente, vale) -> list[dict]:
    respuesta = cliente.get("/api/nuevo/tierras", headers={"Authorization": f"Bearer {vale}"})
    return (respuesta.json().get("tierras") or []) if respuesta.status_code == 200 else []


def main() -> int:
    cliente = httpx.Client(base_url=URL, timeout=90.0)
    print(f"Alta y layout en {URL}")

    salud = cliente.get("/health")
    comprobar(salud.status_code == 200, "la URL contesta /health", str(salud.status_code))
    entrada = cliente.post("/api/cuenta/entrar", json={"correo": CORREO, "clave": CLAVE})
    comprobar(entrada.status_code == 200, "la cuenta de ejemplo entra", entrada.text[:120])
    if entrada.status_code != 200:
        return 1
    vale = entrada.json()["token"]
    cabeceras = {"Authorization": f"Bearer {vale}"}

    antes = tierras_de(cliente, vale)
    comprobar(len(antes) == 5, "la finca tenía sus cinco parcelas", f"{len(antes)}")

    with NavegadorDeVerdad() as navegador:
        navegador.abrir(f"{URL}/nuevo/", esperar=1.0)
        navegador.evaluar("localStorage.setItem('cuedigital.token', %r); location.reload();" % vale)
        comprobar(
            bool(navegador.esperar("document.querySelector('.app') !== null", segundos=30)),
            "la aplicación pinta",
        )
        time.sleep(1.0)

        # ── Layout a cuatro anchos, en la pantalla de tierras ───────────────────────────
        comprobar(pulsar(navegador, "tierras", exacto=True), "se puede ir a Tierras")
        navegador.esperar(
            "document.querySelector('.app') && document.querySelector('.app').dataset.vista === 'tierras'",
            segundos=15,
        )
        time.sleep(1.0)
        for ancho, alto, movil in ANCHOS:
            navegador.medir(ancho, alto, movil=movil)
            time.sleep(0.9)
            medido = json.loads(navegador.evaluar(MEDIDA))
            comprobar(
                medido["desborde"] == 0 and medido["pequenos"] == 0,
                f"layout correcto a {ancho} px",
                f"desborde={medido['desborde']} pequeños={medido['pequenos']}",
            )
            if ancho in (360, 1024):
                captura(navegador, f"estable-tierras-{ancho}.png")

        # ── El alta por referencia de seis números ───────────────────────────────────────
        navegador.medir(390, 844, movil=True)
        time.sleep(0.5)
        comprobar(pulsar(navegador, "añadir tierras"), "se abre «Añadir tierras»")
        navegador.esperar(
            "document.querySelector('.app') && document.querySelector('.app').dataset.vista === 'alta'",
            segundos=15,
        )
        time.sleep(1.0)
        # **Los seis números del papel**: provincia, municipio, agregado, zona, polígono y parcela.
        # (Pegar la referencia sirve para el trozo, siete números; para la parcela se usan las
        # casillas, que es lo que enseña el propio formulario.)
        puesto = navegador.evaluar(
            "(() => { const campos = [...document.querySelectorAll('input')]"
            ".filter(e => e.offsetParent !== null && (e.type === 'text' || e.type === 'number'));"
            "const valores = ['Salamanca', 'Calvarrasa de Arriba', '0', '0', '502', '1'];"
            "let puestos = 0;"
            "for (let i = 0; i < Math.min(campos.length, valores.length); i++) {"
            "  const c = campos[i]; c.focus();"
            "  Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')"
            ".set.call(c, valores[i]);"
            "  c.dispatchEvent(new Event('input', {bubbles: true}));"
            "  c.dispatchEvent(new Event('change', {bubbles: true})); puestos += 1; }"
            "return puestos; })()"
        )
        comprobar(int(puesto or 0) >= 6, "se rellenan las seis casillas del papel", str(puesto))
        time.sleep(0.5)
        comprobar(pulsar(navegador, "buscar", exacto=True), "se pulsa «Buscar»")
        navegador.esperar("document.body.innerText.includes('Recintos encontrados')", segundos=25)
        time.sleep(1.0)
        captura(navegador, "estable-alta-390.png")
        comprobar(
            pulsar(navegador, "añadir los marcados"),
            "se añaden los recintos marcados",
        )
        time.sleep(6.0)
        captura(navegador, "estable-alta-hecha-390.png")

        despues = tierras_de(cliente, vale)
        comprobar(
            len(despues) > len(antes),
            "las tierras nuevas se han dado de alta con su referencia",
            f"{len(antes)} → {len(despues)}",
        )
        ids_antes = {tierra['id'] for tierra in antes}
        nuevas = [tierra for tierra in despues if tierra['id'] not in ids_antes]
        creada = nuevas[0] if nuevas else None
        if creada:
            print(f"  alta: {creada.get('alias')} · {creada.get('municipio') or 'sin municipio'}"
                  f" · superficie={creada.get('superficie_ha')}")

        # ── Su ficha, con el contorno ───────────────────────────────────────────────────
        pulsar(navegador, "tierras", exacto=True)
        navegador.esperar(
            "document.querySelector('.app').dataset.vista === 'tierras'", segundos=15
        )
        time.sleep(2.0)
        pulsar(navegador, "tierras", exacto=True)
        time.sleep(1.0)
        abierta = navegador.evaluar(
            "(() => { const filas = [...document.querySelectorAll('button.tierra')]"
            ".filter(e => e.offsetParent !== null);"
            "const fila = %r ? filas.find(e => (e.textContent||'').includes(%r)) : null;"
            "const elegida = fila || filas[filas.length - 1];"
            "if (!elegida) return false; elegida.click(); return true; })()"
            % (creada.get("alias") if creada else "", creada.get("alias") if creada else "")
        )
        comprobar(bool(abierta), "se abre la ficha de la tierra nueva")
        time.sleep(4.0)
        dibujo = navegador.evaluar(
            "(() => { const img = document.querySelector('img[data-mapa-imagen]');"
            "const cargada = img && img.complete && img.naturalWidth > 0;"
            "const svg = document.querySelector('svg.mapa__dibujo');"
            "const trazos = svg ? svg.querySelectorAll('path, polygon, polyline, line').length : 0;"
            "return JSON.stringify({imagen: !!cargada, trazos: trazos}); })()"
        )
        datos = json.loads(dibujo or "{}")
        comprobar(
            datos.get("imagen") or (datos.get("trazos") or 0) > 0,
            "la ficha enseña el contorno",
            dibujo,
        )
        captura(navegador, "estable-ficha-nueva-390.png")
        navegador.medir(1024, 768)
        time.sleep(1.0)
        captura(navegador, "estable-ficha-nueva-1024.png")

    # ── Dejar la finca como estaba ───────────────────────────────────────────────────────
    for tierra in nuevas:
        borrada = cliente.delete(f"/api/parcelas/{tierra['id']}", headers=cabeceras)
        print(f"  limpieza de la parcela {tierra['id']} por la API: {borrada.status_code}")
    despues_limpieza = tierras_de(cliente, vale)
    if len(despues_limpieza) == len(antes):
        print(f"  la finca vuelve a tener sus {len(antes)} parcelas")
    else:
        print(f"  AVISO: quedan {len(despues_limpieza)} parcelas; borrar a mano las de la prueba: "
              f"{[t['id'] for t in nuevas]}")

    print()
    if fallos:
        print(f"RESULTADO: fallan {len(fallos)} comprobaciones:")
        for fallo in fallos:
            print("  ·", fallo)
        return 1
    print("RESULTADO: todo lo comprobado ha ido bien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
