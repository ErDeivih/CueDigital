"""Prepara el front estático para publicarlo en GitHub Pages (09/11/2026).

QUÉ HACE Y POR QUÉ ASÍ
=====================

La pantalla nueva no se compila: son cuatro ficheros (`app.js`, `modelo.js`, `estilos.css` e
`index.html`) más React y `htm` en `web/vendor/`. Para publicarla en GitHub Pages hay que:

1. **Copiar** esos ficheros a una carpeta plana, con `vendor/` dentro.
2. **Poner las rutas relativas**: `index.html` los pide con `/nuevo/...` y `/vendor/...` cuando
   los sirve el propio programa; en Pages viven en la raíz del proyecto (`/CueDigital/`), así
   que una barra delante apuntaría al dominio y no al proyecto.
3. **Decir dónde está la API**: `config.js` pone `window.CUEDIGITAL_API` con la dirección del
   servidor. Sin él, la pantalla pediría `/api/...` a Pages (404) y saldría vacía.
4. Añadir un `.nojekyll`, o GitHub Pages se come los ficheros que empiezan por `_`.

Uso:

    python deploy/paginas_github/preparar.py --servidor https://<servidor> --salida build/pages

El `--servidor` es la dirección pública del backend (la del túnel o la del dominio). Si no se
pasa, se lee de la variable `CUEDIGITAL_API` del entorno.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"
NUEVO = WEB / "nuevo"
VENDOR = WEB / "vendor"
VENDOR_NECESARIO = (
    "react.production.min.js",
    "react-dom.production.min.js",
    "htm.umd.js",
)
# Las cuatro cosas que la pantalla necesita, y nada más (ni LEEMEs ni licencias: van al repo).
FICHEROS_DEL_MODELO = ("app.js", "modelo.js", "estilos.css")


def _index_para_pages(servidor: str) -> str:
    """El `index.html` de la app, con rutas relativas y `config.js` delante del módulo."""
    html = (NUEVO / "index.html").read_text(encoding="utf-8")
    # Las rutas absolutas de la app (`/nuevo/x`, `/vendor/x`) pasan a relativas.
    for viejo, nuevo in (
        ('href="/nuevo/estilos.css"', 'href="estilos.css"'),
        ('href="/marca.svg"', 'href="marca.svg"'),
        ('src="/vendor/', 'src="vendor/'),
        ('src="/nuevo/app.js"', 'src="app.js"'),
    ):
        if viejo not in html:
            raise SystemExit(f"el index.html de la app ya no tiene esto: {viejo}")
        html = html.replace(viejo, nuevo)

    config = (
        "  <!-- Dónde está la API. La escribe deploy/paginas_github/preparar.py al publicar.\n"
        "       Vacía = la API está en el mismo sitio que la pantalla (lo normal). -->\n"
        f'  <script src="config.js" data-servidor="{servidor}"></script>\n'
    )
    if "</head>" not in html:
        raise SystemExit("el index.html no tiene </head>")
    return html.replace("</head>", config + "</head>", 1)


def _config_js(servidor: str, demo_correo: str = "", demo_clave: str = "") -> str:
    partes = [
        "// La dirección del servidor de CueDigital, para la pantalla publicada aparte.\n",
        "// Vacía = el mismo sitio (cuando la sirve el propio programa).\n",
        'window.CUEDIGITAL_API = "%s";\n' % servidor,
    ]
    if demo_correo and demo_clave:
        # **Entrada automática en la cuenta de ejemplo** (solo para la demo publicada). La
        # pantalla nueva no tiene formulario de entrar: en el servidor de verdad el vale lo
        # pone la aplicación de siempre, en el mismo origen. Publicada aparte, el vale tiene
        # que vivir en ESTE origen, así que al abrir se entra en la cuenta de ejemplo y se
        # guarda. Sin esto, la demo enseñaría «sin permiso» en todas las pantallas.
        partes.append(
            """
// Entrada automática en la cuenta de ejemplo (demo publicada, sin formulario de entrar).
// Las credenciales son de una finca de ejemplo: no hay datos de ningún agricultor real.
(function () {
  var CLAVE = "cuedigital.token";
  try {
    if (localStorage.getItem(CLAVE) || !window.CUEDIGITAL_API) return;
    fetch(window.CUEDIGITAL_API + "/api/cuenta/entrar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correo: %s, clave: %s }),
    })
      .then(function (respuesta) { return respuesta.ok ? respuesta.json() : null; })
      .then(function (datos) {
        if (datos && datos.token) {
          localStorage.setItem(CLAVE, datos.token);
          location.reload();
        }
      })
      .catch(function () {});
  } catch (error) {}
})();
"""
            % (
                repr(demo_correo).replace("'", '"'),
                repr(demo_clave).replace("'", '"'),
            )
        )
    return "".join(partes)


def preparar(
    servidor: str,
    salida: pathlib.Path,
    demo_correo: str = "",
    demo_clave: str = "",
) -> pathlib.Path:
    servidor = (servidor or "").strip().rstrip("/")
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir(parents=True)

    for nombre in FICHEROS_DEL_MODELO:
        shutil.copy2(NUEVO / nombre, salida / nombre)
    for nombre in VENDOR_NECESARIO:
        destino = salida / "vendor"
        destino.mkdir(exist_ok=True)
        shutil.copy2(VENDOR / nombre, destino / nombre)
    shutil.copy2(WEB / "marca.svg", salida / "marca.svg")

    (salida / "index.html").write_text(_index_para_pages(servidor), encoding="utf-8", newline="")
    (salida / "config.js").write_text(_config_js(servidor, demo_correo, demo_clave), encoding="utf-8", newline="")
    # Sin esto, GitHub Pages (Jekyll) ignora lo que empieza por `_` y puede reescribir cosas.
    (salida / ".nojekyll").write_text("", encoding="utf-8", newline="")

    # Comprobación del propio guion: que no quede ninguna ruta absoluta a la app.
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
        "--salida",
        default=str(RAIZ / "build" / "pages"),
        help="Carpeta donde se deja el front listo para publicar.",
    )
    parser.add_argument("--demo-correo", default="", help="Cuenta de ejemplo de la demo.")
    parser.add_argument("--demo-clave", default="", help="Clave de esa cuenta de ejemplo.")
    args = parser.parse_args()
    destino = preparar(
        args.servidor, pathlib.Path(args.salida), args.demo_correo, args.demo_clave
    )
    ficheros = sorted(p.name for p in destino.rglob("*") if p.is_file())
    print(f"Front preparado en {destino}")
    print(f"Servidor de la API: {args.servidor or '(el mismo sitio)'}")
    print("Ficheros:", ", ".join(ficheros))
    return 0


if __name__ == "__main__":
    sys.exit(main())
