"""Qué acciones ofrece cada pantalla, y cómo se llaman (encargo: «acciones claras», 07/10/2026).

«Las acciones no están claras» no es una medida. Lo que se puede medir es: **cuántas acciones** ofrece cada
pantalla, **cómo se llaman** (su texto) y **cuántas se ven** sin desplazarse — porque una acción que hay que
buscar no está clara, está escondida.

Se recorre el menú del armazón (una pantalla por renglón) y se apunta lo que ofrece cada una.

Uso:  python medir_las_acciones.py http://127.0.0.1:8074
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8074"

# Los renglones del menú que se recorren: los módulos del armazón, uno por uno.
MODULOS = (
    "inicio",
    "buscar",
    "tierras",
    "trabajos",
    "cuentas",
    "maquinaria",
    "papeles",
    "contactos",
    "almacen",
    "facturas",
    "cuaderno",
    "ayuda",
)

MEDIDA = (
    "(() => {"
    " const acciones = [...document.querySelectorAll('#pantalla [data-accion]')];"
    " const alto = window.innerHeight;"
    " const con_texto = acciones.map((e) => ({"
    "   accion: e.dataset.accion,"
    "   texto: (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 34),"
    "   visible: e.getBoundingClientRect().top < alto && e.getBoundingClientRect().bottom > 0,"
    "   en_barra: Boolean(e.closest('.barra-acciones'))"
    " }));"
    " return {"
    "  cuantas: con_texto.length,"
    "  visibles: con_texto.filter((a) => a.visible).length,"
    "  en_barra: con_texto.filter((a) => a.en_barra).length,"
    "  sin_texto: con_texto.filter((a) => !a.texto).length,"
    "  acciones: con_texto"
    " }; })()"
)


def main() -> int:
    escenario = preparar(DIRECCION)
    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "window.localStorage.setItem('cuedigital.token', "
                + repr(escenario.volumen.token).replace("'", '"')
                + ");"
            },
        )
        nav.abrir(f"{DIRECCION}/#/", esperar=2.0)
        nav.esperar("Boolean(document.querySelector('.cabecera'))", segundos=25)
        for modulo in MODULOS:
            if modulo != "inicio":
                if not nav.evaluar(
                    "(() => { const el = document.querySelector('#menu-" + modulo + "');"
                    " if (!el) return false; el.click(); return true; })()"
                ):
                    print(f"{modulo:>10}  —  (no hay renglón en el menú)")
                    continue
            nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=25)
            m = nav.evaluar(MEDIDA) or {}
            print(
                f"{modulo:>10}  acciones={m.get('cuantas'):>2}  visibles={m.get('visibles'):>2}"
                f"  en_barra={m.get('en_barra'):>2}  sin_texto={m.get('sin_texto'):>2}"
            )
            for una in (m.get("acciones") or [])[:12]:
                print(f"              · {una.get('accion'):<28} «{una.get('texto')}»")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
