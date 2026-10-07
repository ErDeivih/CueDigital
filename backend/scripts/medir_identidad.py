"""Mide la identidad de cada pantalla y dónde se parte un importe (07/10/2026).

Sirve para dos cosas del encargo de esta ronda:

  · **Defecto 4**: qué elemento es propio de cada pantalla (para identificarla sin ambigüedad) y qué
    acciones/ids aparecen en una y no en las otras.
  · **Defecto 2**: qué elementos parten su texto en varias líneas a 712 px (el «0,00 €» cortado).

Uso:  python medir_identidad.py http://127.0.0.1:8025
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8025"
RUTAS = [
    ("inicio", "/#/"),
    ("cuaderno", "/#/cuaderno"),
    ("tierras", "/#/tierras"),
    ("cuentas", "/#/cuentas"),
]

escenario = preparar(DIRECCION)
print("escenario:", escenario.resumen()[:200].replace("\n", " | "))
with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.orden(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(escenario.volumen.token) + ");"},
    )
    for nombre, ruta in RUTAS:
        nav.medir(1440, 900)
        nav.orden("Page.navigate", {"url": "about:blank"})
        nav.abrir(f"{DIRECCION}{ruta}", esperar=1.6)
        identidad = nav.evaluar(
            """(() => {
                const pantalla = document.querySelector('#pantalla');
                const acciones = [...document.querySelectorAll('#pantalla [data-accion]')]
                    .map((el) => el.dataset.accion);
                const ids = [...document.querySelectorAll('#pantalla [id]')].map((el) => el.id);
                return {
                    hayEntrada: Boolean(document.querySelector('#correo')),
                    titulo: (pantalla.querySelector('h1') || {}).innerText || '',
                    accionesUnicas: [...new Set(acciones)].slice(0, 14),
                    ids: [...new Set(ids)].slice(0, 14),
                    texto: (pantalla.innerText || '').slice(0, 160).replace(/\\n/g, ' | '),
                };
            })()"""
        )
        print(f"\n=== {nombre} ({ruta})")
        print("  h1:", identidad["titulo"])
        print("  hay formulario de entrar:", identidad["hayEntrada"])
        print("  acciones:", identidad["accionesUnicas"])
        print("  ids:", identidad["ids"])
        print("  texto:", identidad["texto"])

    # --- Defecto 2: qué se parte en varias líneas a 712 px ---------------------
    print("\n=== elementos con el texto partido en varias líneas (712 px, cuentas)")
    nav.medir(712, 900)
    nav.orden("Page.navigate", {"url": "about:blank"})
    nav.abrir(f"{DIRECCION}/#/cuentas", esperar=1.8)
    partidos = nav.evaluar(
        """(() => {
            const salida = [];
            for (const el of document.querySelectorAll('#pantalla *')) {
                if (el.children.length) continue;                 // solo el nodo que lleva el texto
                const texto = (el.innerText || '').trim();
                if (!texto || !/\\d/.test(texto)) continue;        // solo lo que lleva cifras
                if (el.getClientRects().length <= 1) continue;     // una sola línea: no se parte
                salida.push({
                    clase: el.className || el.tagName,
                    texto,
                    lineas: el.getClientRects().length,
                    ancho: Math.round(el.getBoundingClientRect().width),
                });
            }
            return salida.slice(0, 20);
        })()"""
    )
    for fila in partidos:
        print(f"  · {fila['clase']} — «{fila['texto']}» en {fila['lineas']} líneas (ancho {fila['ancho']})")
