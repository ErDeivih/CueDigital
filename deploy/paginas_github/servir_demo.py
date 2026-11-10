"""Sirve el paquete de la demo en local, con los tipos de fichero bien puestos (10/11/2026).

POR QUÉ NO VALE `python -m http.server`
=======================================

En Windows, el `http.server` de la biblioteca estándar saca el tipo de los ficheros del registro
del sistema, y allí un `.js` puede ser `text/plain`. Un navegador que recibe un módulo JavaScript
con `text/plain` **lo rechaza**: la pantalla se queda en blanco y no dice por qué. Es la misma
trampa que está documentada en `AGENTS.md` para la aplicación, así que aquí se declaran los tipos
a mano igual que en `app/main.py`.

Uso:

    python deploy/paginas_github/servir_demo.py build/pages-demo 8100
"""

from __future__ import annotations

import functools
import http.server
import pathlib
import sys

TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webmanifest": "application/manifest+json",
}


class ConLosTiposDeLaCasa(http.server.SimpleHTTPRequestHandler):
    """El servidor de siempre, pero con los tipos declarados a mano."""

    def guess_type(self, path):  # noqa: D102 — es la firma de la biblioteca estándar
        sufijo = pathlib.Path(str(path)).suffix.lower()
        return TIPOS.get(sufijo) or "application/octet-stream"

    def end_headers(self):  # noqa: D102
        # Para que al repetir pruebas no se quede una versión vieja en la caché del navegador.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> int:
    carpeta = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "build/pages-demo")
    puerto = int(sys.argv[2] if len(sys.argv) > 2 else 8100)
    if not carpeta.is_dir():
        raise SystemExit(f"No existe la carpeta {carpeta}. Prepara el paquete primero.")
    manejador = functools.partial(ConLosTiposDeLaCasa, directory=str(carpeta))
    with http.server.ThreadingHTTPServer(("127.0.0.1", puerto), manejador) as servidor:
        print(f"Demo en http://127.0.0.1:{puerto}/  (carpeta {carpeta})")
        servidor.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
