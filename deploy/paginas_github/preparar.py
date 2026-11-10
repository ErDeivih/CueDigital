"""Prepara el front estático para publicarlo en GitHub Pages (10/11/2026).

DOS MODOS
=========

1. **Contra un servidor** (`--servidor https://…`): la pantalla llama al backend de verdad. El
   paquete lleva un `config.js` con `window.CUEDIGITAL_API` y el `index.html` normal.
2. **Demo sin servidor** (`--demo`): la pantalla **no llama a nadie**. Se copian dentro
   `demo-datos.js` (copia literal de lo que contestó el servidor para la finca de ejemplo) y
   `demo.js`, que intercepta `fetch` y contesta con esos datos, guarda en el navegador lo que se
   dé de alta y pone el aviso de que es una demo. Sirve aunque el servidor de casa esté apagado.

Lo que hace siempre: rutas relativas en el `index.html` (Pages sirve el proyecto en
`/<repositorio>/`), `.nojekyll` y comprobar que no queda ninguna ruta absoluta de la app.

Uso:

    python deploy/paginas_github/preparar.py --servidor https://… --salida build/pages
    python deploy/paginas_github/preparar.py --demo --salida build/pages-demo
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"
NUEVO = WEB / "nuevo"
VENDOR = WEB / "vendor"
AQUI = pathlib.Path(__file__).resolve().parent
VENDOR_NECESARIO = (
    "react.production.min.js",
    "react-dom.production.min.js",
    "htm.umd.js",
)
FICHEROS_DEL_MODELO = ("app.js", "modelo.js", "estilos.css")


def _index_para_pages(servidor: str, demo: bool) -> str:
    """El `index.html` de la app, con rutas relativas y lo que haga falta delante del módulo."""
    html = (NUEVO / "index.html").read_text(encoding="utf-8")
    for viejo, nuevo in (
        ('href="/nuevo/estilos.css"', 'href="estilos.css"'),
        ('href="/marca.svg"', 'href="marca.svg"'),
        ('src="/vendor/', 'src="vendor/'),
        ('src="/nuevo/app.js"', 'src="app.js"'),
    ):
        if viejo not in html:
            raise SystemExit(f"el index.html de la app ya no tiene esto: {viejo}")
        html = html.replace(viejo, nuevo)

    guiones = ['  <script src="config.js"></script>\n']
    if demo:
        # `demo-datos.js` primero (los datos) y `demo.js` después (el parche de fetch). Los dos
        # son guiones clásicos: se ejecutan antes que el módulo de la aplicación.
        guiones = [
            "  <!-- Demo sin servidor: los datos van dentro y la pantalla no pide nada a nadie. -->\n",
            '  <script src="demo-datos.js"></script>\n',
            '  <script src="demo.js"></script>\n',
        ]
    if "</head>" not in html:
        raise SystemExit("el index.html no tiene </head>")
    # **Cabeceras de seguridad en la demo estática** (10/11/2026). GitHub Pages no deja poner
    # cabeceras HTTP de verdad, así que se pone lo que el navegador sí obedece en el propio HTML:
    # la política de contenido (por `meta`) y que no se mande la dirección de procedencia. Lo que
    # no se puede desde aquí (`X-Frame-Options`, `frame-ancestors`, HSTS) queda escrito en
    # `docs/SEGURIDAD.md` para cuando se mude a un alojamiento que sí deje cabeceras.
    politica = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'" + ("" if demo else f" {servidor}") + "; "
        "font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"
    )
    seguridad = (
        f'  <meta http-equiv="Content-Security-Policy" content="{politica}">\n'
        '  <meta name="referrer" content="no-referrer">\n'
    )
    return html.replace("</head>", seguridad + "".join(guiones) + "</head>", 1)


def _config_js(servidor: str) -> str:
    return (
        "// La dirección del servidor de CueDigital. Vacía = el mismo sitio de la pantalla.\n"
        'window.CUEDIGITAL_API = "%s";\n' % servidor
    )


def _datos_de_la_demo() -> str:
    fichero = AQUI / "demo" / "datos.json"
    if not fichero.is_file():
        raise SystemExit(
            "No está deploy/paginas_github/demo/datos.json. Se saca del servidor de ejemplo con:\n"
            "  python deploy/paginas_github/sacar_datos_demo.py https://<url>"
        )
    datos = json.loads(fichero.read_text(encoding="utf-8"))
    return "window.CUEDIGITAL_DEMO_DATOS = " + json.dumps(
        datos, ensure_ascii=False, separators=(",", ":")
    ) + ";\n"


def preparar(servidor: str, salida: pathlib.Path, demo: bool = False) -> pathlib.Path:
    servidor = (servidor or "").strip().rstrip("/")
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)

    for nombre in FICHEROS_DEL_MODELO:
        shutil.copy2(NUEVO / nombre, salida / nombre)
    for nombre in VENDOR_NECESARIO:
        (salida / "vendor").mkdir(exist_ok=True)
        shutil.copy2(VENDOR / nombre, salida / "vendor" / nombre)
    shutil.copy2(WEB / "marca.svg", salida / "marca.svg")

    (salida / "index.html").write_text(
        _index_para_pages(servidor, demo), encoding="utf-8", newline=""
    )
    if demo:
        (salida / "demo-datos.js").write_text(_datos_de_la_demo(), encoding="utf-8", newline="")
        shutil.copy2(AQUI / "demo.js", salida / "demo.js")

        # **`_headers`**: GitHub Pages lo ignora, pero Netlify y Cloudflare Pages lo leen. Se deja
        # escrito para que, si la demo se muda a un alojamiento que sí pone cabeceras, no haya que
        # inventarlo: solo hay que copiar el fichero.
        (salida / "_headers").write_text(
            "/*\n"
            "  X-Content-Type-Options: nosniff\n"
            "  X-Frame-Options: DENY\n"
            "  Referrer-Policy: no-referrer\n"
            "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
            "  Cross-Origin-Opener-Policy: same-origin\n"
            "  Content-Security-Policy: default-src 'self'; script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'\n",
            encoding="utf-8",
            newline="",
        )
    else:
        (salida / "config.js").write_text(_config_js(servidor), encoding="utf-8", newline="")
    # Sin esto, GitHub Pages (Jekyll) ignora lo que empieza por `_` y puede reescribir cosas.
    (salida / ".nojekyll").write_text("", encoding="utf-8", newline="")

    index = (salida / "index.html").read_text(encoding="utf-8")
    for prohibido in ('href="/nuevo/', 'src="/nuevo/', 'src="/vendor/', 'href="/vendor/'):
        if prohibido in index:
            raise SystemExit(f"se ha quedado una ruta absoluta: {prohibido}")
    return salida


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara el front para GitHub Pages.")
    parser.add_argument(
        "--servidor",
        default=os.environ.get("CUEDIGITAL_API", ""),
        help="Dirección pública del backend (por ejemplo https://abc.trycloudflare.com).",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo sin servidor: los datos van dentro y la pantalla no llama a nadie.",
    )
    parser.add_argument(
        "--salida",
        default=str(RAIZ / "build" / "pages"),
        help="Carpeta donde se deja el front listo para publicar.",
    )
    args = parser.parse_args()
    destino = preparar(args.servidor, pathlib.Path(args.salida), args.demo)
    ficheros = sorted(p.name for p in destino.rglob("*") if p.is_file())
    modo = "DEMO (sin servidor)" if args.demo else f"contra {args.servidor or '(el mismo sitio)'}"
    print(f"Front preparado en {destino} · {modo}")
    print("Ficheros:", ", ".join(ficheros))
    return 0


if __name__ == "__main__":
    sys.exit(main())
