"""¿Dónde se parte un importe en la pantalla de cuentas, a 712 px y con la explotación vacía?

Es el defecto 2 que encontró David mirando las capturas: a 712 px, «0,00 €» salía en varias líneas. Sus
capturas eran de una explotación **vacía**, y con datos el ancho de las tarjetas cambia, así que hay que
medirlo en los dos casos.

Uso:  python medir_importes.py http://127.0.0.1:8025
"""

from __future__ import annotations

import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8025"


def una_cuenta_vacia() -> str:
    with httpx.Client(base_url=DIRECCION, timeout=30.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Prueba de los importes",
                "correo": "importes@ejemplo.test",
                "clave": "una-clave-larga",
                "explotacion": {"nombre": "La finca vacía de los importes", "nif": "12345678Z"},
            },
        )
        if respuesta.status_code == 409:
            respuesta = cliente.post(
                "/api/cuenta/entrar", json={"correo": "importes@ejemplo.test", "clave": "una-clave-larga"}
            )
        respuesta.raise_for_status()
        return respuesta.json()["token"]


token = una_cuenta_vacia()
with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
    )
    for ancho in (390, 712, 1024, 1440):
        nav.medir(ancho, 900)
        nav.orden("Page.navigate", {"url": "about:blank"})
        nav.abrir(f"{DIRECCION}/#/cuentas", esperar=1.8)
        partidos = nav.evaluar(
            """(() => {
                const salida = [];
                for (const el of document.querySelectorAll('#pantalla *')) {
                    if (el.children.length) continue;
                    const texto = (el.innerText || '').trim();
                    // Solo lo que lleva una cifra con separador decimal y su símbolo: los importes.
                    if (!/\\d[.,]\\d{2}/.test(texto)) continue;
                    const rects = el.getClientRects();
                    salida.push({
                        clase: el.className || el.tagName,
                        texto,
                        lineas: rects.length,
                        ancho: Math.round(el.getBoundingClientRect().width),
                        anchoPadre: Math.round((el.parentElement || el).getBoundingClientRect().width),
                    });
                }
                return salida;
            })()"""
        )
        partidos_2 = [fila for fila in partidos if fila["lineas"] > 1]
        print(f"\n=== a {ancho} px: {len(partidos)} importes, {len(partidos_2)} partidos")
        for fila in partidos_2[:10]:
            print(
                f"  · PARTIDO {fila['clase']} — «{fila['texto']}» en {fila['lineas']} líneas"
                f" (ancho {fila['ancho']} de {fila['anchoPadre']})"
            )
        if not partidos_2:
            for fila in partidos[:4]:
                print(f"  · ok {fila['clase']} — «{fila['texto']}» (ancho {fila['ancho']})")

        # **Y todo lo que se parte, no solo los importes**: si el defecto está en la etiqueta de al lado o
        # en un aviso, mirar solo las cifras no lo vería.
        todos = nav.evaluar(
            """(() => {
                const salida = [];
                for (const el of document.querySelectorAll('#pantalla *')) {
                    if (el.children.length) continue;
                    const texto = (el.innerText || '').trim();
                    if (!texto) continue;
                    const rects = el.getClientRects();
                    if (rects.length <= 1) continue;
                    const caja = el.getBoundingClientRect();
                    salida.push({
                        clase: el.className || el.tagName,
                        texto: texto.slice(0, 60),
                        lineas: rects.length,
                        ancho: Math.round(caja.width),
                        alto: Math.round(caja.height),
                    });
                }
                return salida;
            })()"""
        )
        print(f"  (y en total hay {len(todos)} nodos con el texto partido:)")
        for fila in todos[:12]:
            print(f"     - {fila['clase']} «{fila['texto']}» {fila['lineas']} líneas ({fila['ancho']}x{fila['alto']})")
