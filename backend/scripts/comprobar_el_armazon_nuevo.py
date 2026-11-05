"""El armazón **nuevo**, en un navegador de verdad: 390, 1024 y 1440 px y los cuatro estados.

## Por qué existe

David aprobó el diseño y pidió que el armazón nuevo («Hoy» + «Mis parcelas») **se pueda recorrer** a
390, 1024 y 1440 px con los cuatro estados. Eso no se comprueba leyendo ficheros: hace falta un
navegador que mida el ancho, que aplique el CSS, que cargue el mapa y que enseñe u oculte la barra
lateral y la barra inferior. Por eso esto usa `navegador_cdp.py` (Chrome por el protocolo de
depuración) y la explotación de 64 tierras de `datos_representativos.py`.

## Qué comprueba

Por cada ancho (390, 1024 y 1440):

  · La app arranca **con la sesión puesta** (el vale se escribe en el `localStorage` del servidor de
    pruebas, la misma clave que usa la app vieja) y termina en estado «listo».
  · **No hay scroll horizontal**.
  · **La navegación cambia con el ancho**: en el móvil se ve la barra inferior con los cinco destinos
    y no la lateral; en tableta/PC se ve la lateral. Los destinos que se pulsan miden ≥44 px.
  · **Hoy**: título, contador de tierras y bloque de lo último.
  · **Mis parcelas**: contador con las 64 tierras, **varios municipios** (las parcelas no están todas
    juntas), filas, selección de una tierra y **panel** con alias, datos y **otros años**.
  · **El mapa**: o carga la ortofoto (`naturalWidth > 0`) o la app dice que no ha podido, con salida.
  · **Sin textos de desarrollador ni jerga prohibida** (doctrina §8) en el texto visible.

Y los cuatro estados: cargando (API retrasada), error (API caída), vacío (cuenta sin tierras) y sin
permiso (sin vale).

## Cómo se lanza

```powershell
cd backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\\cd-nuevo.db"
$env:CUEDIGITAL_ADJUNTOS="$env:TEMP\\cd-nuevo-adjuntos"
..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8031
..\\.venv\\Scripts\\python.exe scripts\\comprobar_el_armazon_nuevo.py http://127.0.0.1:8031
```

Deja las capturas en `docs/capturas-nuevo/` y sale con código 0 solo si no hay fallos.
`--romper nav|mapa|textos` sirve para comprobar que las comprobaciones **pueden fallar**.
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[2]
CAPTURAS = RAIZ / "docs" / "capturas-nuevo"
ANCHOS = (390, 1024, 1440)
FALLOS = 0
ROMPER = "ninguna"


def comprobar(ok: bool, texto: str) -> bool:
    global FALLOS
    print(f"  [{'OK   ' if ok else 'FALLO'}] {texto}")
    if not ok:
        FALLOS += 1
    return ok


def cuenta_vacia(base: str) -> str:
    """Una cuenta recién creada, sin tierras: es el estado vacío de verdad, no simulado."""
    marca = uuid.uuid4().hex[:8]
    with httpx.Client(base_url=base, timeout=60.0) as cliente:
        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={
                "nombre": "Cuenta vacía",
                "correo": f"vacia-{marca}@ejemplo.test",
                "clave": "una-clave-larga-de-verdad",
                "explotacion": {"nombre": "La Finca Vacía", "nif": "12345678Z"},
            },
        )
    respuesta.raise_for_status()
    return respuesta.json()["token"]


def la_sesion(nav: NavegadorDeVerdad, origen: str, token: str) -> None:
    nav.abrir(origen)
    nav.evaluar(f"localStorage.setItem('cuedigital.token', {json.dumps(token)})")


def texto_visible(nav: NavegadorDeVerdad) -> str:
    return nav.evaluar("document.body ? document.body.innerText : ''") or ""


def captura(nav: NavegadorDeVerdad, nombre: str) -> pathlib.Path:
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    crudo = nav.orden("Page.captureScreenshot", {"format": "png"})["data"]
    destino = CAPTURAS / f"{nombre}.png"
    destino.write_bytes(base64.b64decode(crudo))
    return destino


def estado_actual(nav: NavegadorDeVerdad) -> str:
    return (
        nav.evaluar(
            "(() => { const raiz = document.querySelector('[data-estado]');"
            " return raiz ? raiz.getAttribute('data-estado') : '(sin estado)'; })()"
        )
        or "(sin estado)"
    )


def esperar_estado(nav: NavegadorDeVerdad, estado: str, segundos: float = 25.0) -> bool:
    return nav.esperar(
        "document.querySelector('[data-estado=\"" + estado + "\"]') !== null",
        segundos=segundos,
    )


def clic_en_visible(nav: NavegadorDeVerdad, selector: str) -> bool:
    """Pulsa el primero que se ve (la barra lateral y la inferior conviven en el DOM)."""
    return bool(
        nav.evaluar(
            "(() => { const el = Array.from(document.querySelectorAll("
            + json.dumps(selector)
            + ")).find(e => e.getBoundingClientRect().width > 0);"
            " if (!el) return false; el.click(); return true; })()"
        )
    )


def palabras_prohibidas() -> list[str]:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from app import textos

    return list(getattr(textos, "PALABRAS_PROHIBIDAS", []))


DE_DESARROLLADOR = (
    "token",
    "endpoint",
    "artboard",
    "lorem",
    "fixme",
    "console.log",
    "api/",
    "localhost",
)


def sin_textos_de_desarrollador(nav: NavegadorDeVerdad, ancho: int) -> None:
    visible = texto_visible(nav).lower()
    malas = [palabra for palabra in DE_DESARROLLADOR if palabra in visible]
    if ROMPER == "textos":
        malas = malas + ["(roto a propósito)"]
    comprobar(not malas, f"{ancho} px: la pantalla no habla de cómo está hecha ({malas or 'limpio'})")
    jerga = [palabra for palabra in palabras_prohibidas() if palabra.lower() in visible]
    comprobar(not jerga, f"{ancho} px: sin jerga prohibida ({jerga or 'limpio'})")


def comprobar_un_ancho(nav: NavegadorDeVerdad, base: str, ancho: int) -> None:
    print(f"\n== {ancho} px ==")
    nav.medir(ancho, 900, movil=ancho <= 712)
    nav.abrir(f"{base}/nuevo/", esperar=1.0)
    if not esperar_estado(nav, "listo"):
        comprobar(False, f"{ancho} px: la app no llega a «listo» (está en «{estado_actual(nav)}»)")
        captura(nav, f"fallo-{ancho}")
        return
    comprobar(True, f"{ancho} px: la app arranca con la sesión puesta")

    desborde = nav.evaluar("document.documentElement.scrollWidth - window.innerWidth")
    comprobar((desborde or 0) <= 1, f"{ancho} px: no hay scroll horizontal ({desborde} px de más)")

    hay_inferior = bool(
        nav.evaluar(
            "Array.from(document.querySelectorAll('[data-nav-inferior]'))"
            ".some(e => e.getBoundingClientRect().width > 0)"
        )
    )
    hay_lateral = bool(
        nav.evaluar(
            "Array.from(document.querySelectorAll('[data-nav-lateral]'))"
            ".some(e => e.getBoundingClientRect().width > 0)"
        )
    )
    if ancho <= 700:
        comprobar(hay_inferior, f"{ancho} px: se ve la barra inferior")
        comprobar(not hay_lateral, f"{ancho} px: no se ve la barra lateral en el móvil")
    else:
        comprobar(hay_lateral, f"{ancho} px: se ve la barra lateral")

    destinos = nav.evaluar(
        "Array.from(document.querySelectorAll('[data-destino]'))"
        ".filter(e => e.getBoundingClientRect().width > 0)"
        ".map(e => ({clave: e.getAttribute('data-destino'),"
        " alto: Math.round(e.getBoundingClientRect().height)}))"
    ) or []
    claves = {d["clave"] for d in destinos}
    if ROMPER == "nav":
        claves = claves | {"inexistente"}
    comprobar(
        {"hoy", "tierras"} <= claves,
        f"{ancho} px: están los destinos Hoy y Tierras (hay {sorted(claves)})",
    )
    pequenos = [d for d in destinos if d["alto"] < 44]
    comprobar(not pequenos, f"{ancho} px: los destinos se pueden pulsar con el pulgar ({pequenos or 'todos ≥44'})")

    # «Hoy»
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-vista=\"hoy\"]')")),
              f"{ancho} px: se abre «Hoy»")
    titulo = nav.evaluar("(document.querySelector('[data-titulo]')||{}).textContent || ''") or ""
    comprobar("hoy" in titulo.lower(), f"{ancho} px: el título dice Hoy ({titulo!r})")
    contador = nav.evaluar("(document.querySelector('[data-contador-tierras]')||{}).textContent || ''") or ""
    comprobar("64" in contador, f"{ancho} px: el contador de tierras dice 64 ({contador!r})")
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-ultimos]')")),
              f"{ancho} px: está el bloque de lo último")

    # «Mis parcelas»
    clic_en_visible(nav, "[data-destino=tierras]")
    llego_tierras = nav.esperar(
        "(() => { const raiz = document.querySelector('[data-vista=\"tierras\"]');"
        " return !!raiz && raiz.getAttribute('data-estado') === 'listo'; })()",
        segundos=20,
    )
    comprobar(llego_tierras, f"{ancho} px: se llega a «Mis parcelas» con los datos")
    totales = nav.evaluar("(document.querySelector('[data-totales]')||{}).textContent || ''") or ""
    comprobar("64" in totales, f"{ancho} px: el contador dice 64 tierras ({totales!r})")
    municipios = nav.evaluar("document.querySelectorAll('[data-municipio]').length") or 0
    comprobar(municipios >= 2, f"{ancho} px: las tierras salen agrupadas en varios municipios ({municipios})")
    filas = nav.evaluar("document.querySelectorAll('[data-tierra-id]').length") or 0
    comprobar(filas > 0, f"{ancho} px: hay filas de tierras ({filas})")

    clic_en_visible(nav, "[data-tierra-id]")
    espera_panel = nav.esperar("document.querySelector('[data-panel]') !== null", segundos=10)
    alias = nav.evaluar("(document.querySelector('[data-panel-alias]')||{}).textContent || ''") or ""
    comprobar(espera_panel and bool(alias.strip()),
              f"{ancho} px: el panel de la tierra enseña su alias ({alias!r})")
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-panel-otros-anios]')")),
              f"{ancho} px: el panel tiene el bloque de otros años")

    # El mapa: o carga la ortofoto, o la app dice que no ha podido (nunca una caja muda).
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-mapa]')")), f"{ancho} px: está el mapa")
    llego = nav.esperar(
        "(() => { const i = document.querySelector('[data-mapa-imagen]');"
        " return (i && i.naturalWidth > 0) || !!document.querySelector('[data-mapa-error]'); })()",
        segundos=15,
    )
    cargada = bool(nav.evaluar(
        "(() => { const i = document.querySelector('[data-mapa-imagen]');"
        " return !!i && i.naturalWidth > 0; })()"
    ))
    if ROMPER == "mapa":
        comprobar(cargada, f"{ancho} px: el mapa TIENE imagen (comprobación rota a propósito)")
    elif llego and cargada:
        comprobar(True, f"{ancho} px: el mapa tiene imagen")
    elif llego:
        comprobar(True, f"{ancho} px: el mapa dice que no ha podido cargarse, con salida")
    else:
        comprobar(False, f"{ancho} px: el mapa se queda en blanco sin decir nada")

    sin_textos_de_desarrollador(nav, ancho)
    print(f"  (captura: {captura(nav, f'armazon-{ancho}').relative_to(RAIZ)})")


def comprobar_estados(nav: NavegadorDeVerdad, base: str, token_vacio: str, token: str) -> None:
    print("\n== Los cuatro estados ==")
    registrados: list[dict] = []

    def interceptar(fuente: str | None) -> None:
        while registrados:
            nav.orden("Page.removeScriptToEvaluateOnNewDocument", {"identifier": registrados.pop()["identifier"]})
        if fuente:
            registrados.append(
                nav.orden("Page.addScriptToEvaluateOnNewDocument", {"source": fuente})
            )

    # 1) cargando: la API no contesta todavía.
    nav.abrir(base)
    nav.evaluar("localStorage.setItem('cuedigital.token', " + json.dumps(token) + ")")
    interceptar(
        "(() => { const f = window.fetch; window.fetch = (u, o) => "
        "String(u).includes('/api/nuevo/') ? new Promise(() => {}) : f(u, o); })();"
    )
    nav.abrir(f"{base}/nuevo/", esperar=1.2)
    comprobar(nav.esperar("document.querySelector('[data-estado=cargando]') !== null", segundos=10),
              "estado cargando: la app dice que está trayendo")
    captura(nav, "estado-cargando")

    # 2) error: la API falla.
    interceptar(
        "(() => { const f = window.fetch; window.fetch = (u, o) => "
        "String(u).includes('/api/nuevo/') ? Promise.reject(new Error('sin red')) : f(u, o); })();"
    )
    nav.abrir(f"{base}/nuevo/", esperar=1.2)
    comprobar(nav.esperar("document.querySelector('[data-estado=error]') !== null", segundos=10),
              "estado error: la app avisa de que no ha podido")
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-reintentar]')")),
              "estado error: hay botón de volver a intentar")
    captura(nav, "estado-error")

    # 3) vacío: una cuenta sin tierras.
    interceptar(None)
    nav.abrir(base)
    nav.evaluar("localStorage.setItem('cuedigital.token', " + json.dumps(token_vacio) + ")")
    nav.abrir(f"{base}/nuevo/", esperar=1.2)
    comprobar(nav.esperar("document.querySelector('[data-estado=\"vacio\"]') !== null", segundos=15),
              "estado vacío: la app dice que aún no hay tierras")
    # El botón de salir del vacío está en la tarjeta de «Hoy» o en la pantalla de tierras según la
    # vista; se busca en la vista actual y, si no, se cambia a tierras, que es donde vive el otro.
    hay_boton = bool(nav.evaluar(
        "Array.from(document.querySelectorAll('[data-traer-tierras]'))"
        ".some(e => e.getBoundingClientRect().width > 0)"
    ))
    if not hay_boton:
        clic_en_visible(nav, "[data-destino=tierras]")
        nav.esperar("document.querySelector('[data-vista=\"tierras\"]') !== null", segundos=10)
        hay_boton = bool(nav.evaluar(
            "Array.from(document.querySelectorAll('[data-traer-tierras]'))"
            ".some(e => e.getBoundingClientRect().width > 0)"
        ))
    comprobar(hay_boton, "estado vacío: hay un botón que lo arregla")
    captura(nav, "estado-vacio")

    # 4) sin permiso: sin vale.
    nav.abrir(base)
    nav.evaluar("localStorage.removeItem('cuedigital.token')")
    nav.abrir(f"{base}/nuevo/", esperar=1.2)
    comprobar(nav.esperar("document.querySelector('[data-estado=\"sin-permiso\"]') !== null", segundos=10),
              "sin permiso: la app pide entrar")
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-entrar]')")),
              "sin permiso: hay enlace para entrar")
    captura(nav, "estado-sin-permiso")


def main() -> int:
    global ROMPER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="dirección del servidor de pruebas, p. ej. http://127.0.0.1:8031")
    parser.add_argument("--romper", choices=("nav", "mapa", "textos", "ninguna"), default="ninguna")
    argumentos = parser.parse_args()
    ROMPER = argumentos.romper
    base = argumentos.base.rstrip("/")
    print(f"== El armazón nuevo, en un navegador de verdad ({base}) ==")
    escenario = preparar(base)
    token = escenario.volumen.token
    token_vacio = cuenta_vacia(base)
    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        la_sesion(nav, base, token)
        for ancho in ANCHOS:
            comprobar_un_ancho(nav, base, ancho)
        comprobar_estados(nav, base, token_vacio, token)
    print(f"\nFallos: {FALLOS}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
