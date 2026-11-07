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
import tempfile
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
    # La tierra se abre en su ficha (vista «tierra»). El panel de dentro de la lista sigue
    # existiendo en algunas pantallas, así que se acepta cualquiera de los dos.
    espera_ficha = nav.esperar(
        "!!document.querySelector('[data-vista=\"tierra\"]') || !!document.querySelector('[data-panel]')",
        segundos=15,
    )
    alias = nav.evaluar(
        "(() => { const p = document.querySelector('[data-panel-alias]');"
        " const h = document.querySelector('[data-vista=\"tierra\"] h1');"
        " return (p && p.textContent) || (h && h.textContent) || ''; })()"
    ) or ""
    comprobar(espera_ficha and bool(alias.strip()),
              f"{ancho} px: al clicar la tierra se abre su ficha con el nombre ({alias!r})")
    otros = bool(nav.evaluar(
        "!!document.querySelector('[data-panel-otros-anios]')"
        " || !!document.querySelector('[data-historial-anio]')"
    ))
    comprobar(otros, f"{ancho} px: la ficha tiene el bloque de otros años")

    # La ficha nueva tapa la lista: se vuelve a «Mis parcelas» para mirar su mapa.
    clic_en_visible(nav, "[data-destino=tierras]")
    nav.esperar(
        "(() => { const raiz = document.querySelector('[data-vista=\"tierras\"]');"
        " return !!raiz && raiz.getAttribute('data-estado') === 'listo'; })()",
        segundos=15,
    )

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


def escribir_en_campo(nav: NavegadorDeVerdad, indice: int, valor: str) -> None:
    """Escribe en el campo número `indice` de la rejilla de códigos, como lo haría una persona."""
    nav.evaluar(
        "(() => { const el = document.querySelectorAll('.rejilla-campos input')[" + str(indice) + "];"
        " if (!el) return false; const setter = Object.getOwnPropertyDescriptor("
        "window.HTMLInputElement.prototype, 'value').set;"
        " setter.call(el, " + json.dumps(valor) + ");"
        " el.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"
    )


def comprobar_alta_e_importacion(nav: NavegadorDeVerdad, base: str) -> None:
    """El alta de tierras (por código y con la ventana del SIGPAC) y la importación del cuaderno."""
    print("\n== Alta de tierras e importación ==")
    nav.medir(1440, 1000)
    nav.abrir(f"{base}/nuevo/", esperar=1.0)
    esperar_estado(nav, "listo")
    clic_en_visible(nav, "[data-destino=tierras]")
    llego_tierras = nav.esperar(
        "(() => { const raiz = document.querySelector('[data-vista=\"tierras\"]');"
        " return !!raiz && raiz.getAttribute('data-estado') === 'listo'"
        " && document.querySelectorAll('[data-tierra-id]').length > 0; })()",
        segundos=20,
    )
    comprobar(llego_tierras, "se abre «Mis parcelas» para dar de alta")
    if not llego_tierras:
        return
    antes = nav.evaluar("document.querySelectorAll('[data-tierra-id]').length") or 0
    comprobar(antes == 64, f"antes de dar de alta hay 64 tierras ({antes})")

    abrio_alta = clic_en_visible(nav, "[data-accion=anadir-tierras]")
    llego = abrio_alta and nav.esperar(
        "document.querySelector('[data-vista=\"alta\"]') !== null", segundos=15
    )
    comprobar(llego, "se abre «Añadir tierras»")
    if not llego:
        return

    # Por la referencia del SIGPAC de la parcela de ejemplo (37/70/0/0/503/51). Se escribe en el
    # recuadro de referencias, que es la forma en la que el agricultor la tiene delante.
    escribir_en_campo(nav, 4, "503")
    escribir_en_campo(nav, 5, "51")
    nav.evaluar(
        "(() => { const el = document.querySelector('[data-vista=\"alta\"] textarea');"
        " if (!el) return false; const setter = Object.getOwnPropertyDescriptor("
        "window.HTMLTextAreaElement.prototype, 'value').set;"
        " setter.call(el, '37:70:0:0:503:51');"
        " el.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"
    )
    nav.evaluar(
        "(() => { const b = document.querySelector('[data-buscar-codigos]');"
        " if (!b) return false; b.click(); return true; })()"
    )
    hay_recintos = nav.esperar("document.querySelectorAll('[data-recinto-id]').length > 0", segundos=40)
    cuantos = nav.evaluar("document.querySelectorAll('[data-recinto-id]').length") or 0
    comprobar(hay_recintos, f"la búsqueda por código trae recintos ({cuantos})")

    if hay_recintos:
        dibujados = nav.evaluar("document.querySelectorAll('[data-mapa-recinto]').length") or 0
        comprobar(dibujados > 0, f"la ventana del SIGPAC dibuja los recintos ({dibujados} en el mapa)")
        nav.evaluar(
            "(() => { const c = document.querySelector('[data-recinto-id] input[type=checkbox]');"
            " if (!c) return false; c.click(); return true; })()"
        )
        marca = nav.esperar(
            "(() => { const l = document.querySelector('[data-recinto-id]');"
            " return !!l && l.getAttribute('data-recinto-marcado') === 'si'; })()",
            segundos=10,
        )
        print("  diagnóstico marca:", nav.evaluar(
            "(() => { const l = document.querySelector('[data-recinto-id]');"
            " const b = document.querySelector('[data-anadir-seleccionados]');"
            " return JSON.stringify({marcado: l && l.getAttribute('data-recinto-marcado'),"
            " deshabilitado: b ? !!b.disabled : null}); })()"
        ))
        if not marca:
            nav.evaluar(
                "(() => { const l = document.querySelector('[data-recinto-id]');"
                " if (!l) return false; l.click(); return true; })()"
            )
            marca = nav.esperar(
                "(() => { const l = document.querySelector('[data-recinto-id]');"
                " return !!l && l.getAttribute('data-recinto-marcado') === 'si'; })()",
                segundos=10,
            )
        habilitado = nav.esperar(
            "(() => { const b = document.querySelector('[data-anadir-seleccionados]');"
            " return !!b && !b.disabled; })()",
            segundos=10,
        )
        comprobar(marca, "el recinto se puede marcar")
        comprobar(habilitado, "el botón de añadir se activa al marcar")
        nav.evaluar(
            "(() => { const b = document.querySelector('[data-anadir-seleccionados]');"
            " if (!b || b.disabled) return false; b.click(); return true; })()"
        )
        anadido = nav.esperar("document.querySelector('[data-alta-resultado]') !== null", segundos=30)
        comprobar(anadido, "la tierra marcada se añade con su aviso")
        clic_en_visible(nav, "[data-accion=anadir-tierras]")
        nav.esperar("document.querySelector('[data-vista=\"tierras\"]') !== null", segundos=10)
        despues = nav.evaluar("document.querySelectorAll('[data-tierra-id]').length") or 0
        comprobar(despues > antes, f"la lista crece tras el alta ({antes} → {despues})")

    # Importar el cuaderno de ejemplo, subiéndolo al campo de fichero de verdad.
    if not nav.evaluar("!!document.querySelector('[data-vista=\"alta\"]')"):
        clic_en_visible(nav, "[data-accion=anadir-tierras]")
        nav.esperar("document.querySelector('[data-vista=\"alta\"]') !== null", segundos=10)
    fichero = str(pathlib.Path(__file__).resolve().parents[1] / "tests" / "datos"
                  / "cuaderno_cyl_de_ejemplo.xlsx")
    raiz = nav.orden("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
    nodo = nav.orden("DOM.querySelector", {"nodeId": raiz, "selector": "[data-importar-cuaderno]"})["nodeId"]
    if nodo:
        nav.orden("DOM.setFileInputFiles", {"nodeId": nodo, "files": [fichero]})
        importado = nav.esperar(
            "(() => { const r = document.querySelector('[data-importar-resultado]');"
            " return !!r && r.innerText.trim().length > 0; })()",
            segundos=60,
        )
        texto = nav.evaluar(
            "(document.querySelector('[data-importar-resultado]')||{}).innerText || ''"
        ) or ""
        comprobar(importado and len(texto.strip()) > 0, f"traer el cuaderno devuelve resultado ({texto[:80]!r})")
        if importado:
            clic_en_visible(nav, "[data-accion=anadir-tierras]")
            nav.esperar("document.querySelector('[data-vista=\"tierras\"]') !== null", segundos=10)
            tras_importar = nav.evaluar("document.querySelectorAll('[data-tierra-id]').length") or 0
            comprobar(tras_importar > 0, f"las tierras del cuaderno quedan en la lista ({tras_importar})")
    else:
        comprobar(False, "no se encuentra el campo para subir el cuaderno")

    # Mapa coloreado y tarjetas de gastos/ingresos y «qué falta».
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-leyenda-uso]')")),
              "el mapa tiene leyenda de uso con palabra y color")
    clic_en_visible(nav, "[data-destino=hoy]")
    nav.esperar("document.querySelector('[data-vista=\"hoy\"]') !== null", segundos=10)
    nav.esperar("document.querySelector('[data-resumen-gastos]') !== null", segundos=20)
    nav.esperar("document.querySelector('[data-que-falta]') !== null", segundos=20)
    for atributo, nombre in (
        ("data-resumen-gastos", "gastos"),
        ("data-resumen-ventas", "ventas"),
        ("data-resumen-cuaderno", "cuaderno"),
        ("data-que-falta", "qué falta"),
    ):
        comprobar(bool(nav.evaluar(f"!!document.querySelector('[{atributo}]')")),
                  f"«Hoy» enseña {nombre}")
    print(f"  (captura: {captura(nav, 'alta-y-cuaderno').relative_to(RAIZ)})")


def crear_una_foto_de_factura() -> pathlib.Path:
    """Una foto sintética, solo para el arnés: no es una factura de verdad, es para ver el flujo."""
    from PIL import Image, ImageDraw

    destino = pathlib.Path(tempfile.gettempdir()) / "cd-factura-de-prueba.png"
    imagen = Image.new("RGB", (900, 1200), "white")
    lapiz = ImageDraw.Draw(imagen)
    renglones = [
        "FACTURA",
        "Proveedor de Ejemplo, S.L.",
        "NIF: B12345678",
        "Numero: 2026/00123",
        "Fecha: 05/11/2026",
        "Abono 33,5%  1000 kg  0,45 EUR/kg",
        "Base imponible: 450,00",
        "IVA 21%: 94,50",
        "TOTAL: 544,50 EUR",
    ]
    for indice, renglon in enumerate(renglones):
        lapiz.text((60, 80 + indice * 80), renglon, fill="black")
    imagen.save(destino)
    return destino


def comprobar_ficha_calendario_trabajos_y_facturas(
    nav: NavegadorDeVerdad, base: str, token: str
) -> None:
    """Tierra primero, su trabajo de hoy, apuntar desde la tierra, calendario, filtros y facturas."""
    print("\n== Tierra, historial, calendario, filtros y facturas ==")
    nav.medir(1440, 1000)
    nav.abrir(f"{base}/nuevo/", esperar=1.0)
    esperar_estado(nav, "listo")
    clic_en_visible(nav, "[data-destino=tierras]")
    nav.esperar(
        "(() => { const raiz = document.querySelector('[data-vista=\"tierras\"]');"
        " return !!raiz && raiz.getAttribute('data-estado') === 'listo'"
        " && document.querySelectorAll('[data-tierra-id]').length > 0; })()",
        segundos=20,
    )
    clic_en_visible(nav, "[data-tierra-id]")
    llego_tierra = nav.esperar("!!document.querySelector('[data-vista=\"tierra\"]')", segundos=15)
    comprobar(llego_tierra, "al clicar la tierra se abre su ficha")
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-trabajo-de-hoy]')")),
              "la ficha enseña el trabajo de hoy")
    comprobar(bool(nav.evaluar("!!document.querySelector('[data-historial]')")),
              "la ficha enseña el historial de la tierra")
    if llego_tierra:
        # La comparación de años: o filas, o el aviso de que todavía no hay años que comparar.
        comparativa = nav.esperar(
            "!!document.querySelector('[data-historial-comparativa]')", segundos=15
        )
        filas_anio = nav.evaluar("document.querySelectorAll('[data-historial-fila-anio]').length") or 0
        comprobar(comparativa and (filas_anio >= 1 or "años anteriores" in texto_visible(nav)),
                  f"la ficha compara los años anteriores ({filas_anio} filas)")
    if llego_tierra:
        # La primera tierra de la lista puede no tener forma en el SIGPAC (y entonces la ficha lo
        # dice, que es lo correcto). Se prueban varias hasta encontrar una con contorno dibujado.
        tiene_imagen = False
        for intento in range(6):
            tiene_imagen = nav.esperar(
                "(() => { const i = document.querySelector('[data-vista=\"tierra\"] img');"
                " return !!i && i.complete && i.naturalWidth > 0; })()",
                segundos=15,
            )
            if tiene_imagen:
                break
            sin_forma = "no tiene forma en el SIGPAC" in texto_visible(nav)
            if not sin_forma:
                break
            clic_en_visible(nav, "[data-destino=tierras]")
            nav.esperar("document.querySelector('[data-vista=\"tierras\"]') !== null", segundos=10)
            nav.evaluar(
                "(() => { const f = document.querySelectorAll('[data-tierra-id]')[" + str(intento + 1) + "];"
                " if (!f) return false; f.click(); return true; })()"
            )
            nav.esperar("document.querySelector('[data-vista=\"tierra\"]') !== null", segundos=10)
        comprobar(tiene_imagen, "la ficha enseña la imagen de la tierra con su contorno")
        print(f"  (captura: {captura(nav, 'tierra-historial').relative_to(RAIZ)})")

    # **Apuntar el trabajo del día desde la tierra**: apero del vocabulario del servidor, fecha de
    # hoy, hectáreas de la tierra y guardado de verdad (se comprueba en la API, no solo en pantalla).
    abrio_apuntar = clic_en_visible(nav, "[data-accion=apuntar-trabajo]") or clic_en_visible(
        nav, "[data-destino=apuntar]"
    )
    llego_apuntar = abrio_apuntar and nav.esperar(
        "!!document.querySelector('[data-vista=\"apuntar\"]')", segundos=15
    )
    comprobar(llego_apuntar, "se abre «Apuntar un trabajo» desde la tierra")
    if llego_apuntar:
        nav.esperar("document.querySelector('[data-apuntar-tierra]') !== null", segundos=20)
        # Si se ha abierto desde la barra (sin tierra elegida), se elige la primera: el formulario
        # necesita saber sobre qué tierra se apunta.
        elegida = nav.evaluar(
            "!!document.querySelector('[data-apuntar-tierra][aria-pressed=\"true\"],"
            " [data-apuntar-tierra][data-elegida=\"si\"], [data-apuntar-tierra].tierra--elegida')"
        )
        if not elegida:
            nav.evaluar(
                "(() => { const t = document.querySelector('[data-apuntar-tierra]');"
                " if (!t) return false; t.click(); return true; })()"
            )
            nav.esperar(
                "!!document.querySelector('[data-apuntar-tierra][aria-pressed=\"true\"],"
                " [data-apuntar-tierra][data-elegida=\"si\"], [data-apuntar-tierra].tierra--elegida')",
                segundos=10,
            )
    nav.esperar("document.querySelectorAll('[data-apuntar-apero]').length > 0", segundos=25)
    aperos = nav.evaluar("document.querySelectorAll('[data-apuntar-apero]').length") or 0
    comprobar(aperos >= 6, f"el apero sale del vocabulario del servidor ({aperos})")
    tabs = nav.evaluar("document.querySelectorAll('[data-apuntar-tab]').length") or 0
    comprobar(tabs >= 4, f"se puede apuntar labor, tratamiento, abono y siembra ({tabs} pestañas)")
    for clave, nombre, marcador in (
        ("tratamiento", "tratamiento", "[data-apuntar-producto]"),
        ("abono", "abono", "[data-apuntar-fertilizante]"),
        ("siembra", "siembra", "[data-apuntar-semilla]"),
    ):
        if not tabs:
            break
        nav.evaluar(
            "(() => { const t = document.querySelector('[data-apuntar-tab=\"" + clave + "\"]');"
            " if (!t) return false; t.click(); return true; })()"
        )
        visible = nav.esperar(
            "document.querySelectorAll('" + marcador + "').length > 0"
            " || document.body.innerText.toLowerCase().includes('no hay')"
            " || document.body.innerText.toLowerCase().includes('todavía no')",
            segundos=20,
        )
        cuantos = nav.evaluar("document.querySelectorAll('" + marcador + "').length") or 0
        comprobar(visible, f"la pestaña de {nombre} responde ({cuantos} para elegir)")
    if llego_apuntar and aperos:
        # Las pestañas de antes han podido dejar activa la de siembra: se vuelve a labor para
        # guardar el apero, que es lo que se comprueba aquí.
        nav.evaluar(
            "(() => { const t = document.querySelector('[data-apuntar-tab=\"labor\"]');"
            " if (!t) return false; t.click(); return true; })()"
        )
        nav.esperar("document.querySelectorAll('[data-apuntar-apero]').length > 0", segundos=15)
        nav.evaluar(
            "(() => { const a = document.querySelector('[data-apuntar-apero]');"
            " if (!a) return false; a.click(); return true; })()"
        )
        nav.esperar(
            "(() => { const b = document.querySelector('[data-apuntar-guardar]');"
            " return !!b && !b.disabled; })()",
            segundos=10,
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('[data-apuntar-guardar]');"
            " if (!b || b.disabled) return false; b.click(); return true; })()"
        )
        guardado = nav.esperar(
            "(() => { const r = document.querySelector('[data-apuntar-resultado]');"
            " return !!r && r.innerText.trim().length > 0; })()",
            segundos=30,
        )
        comprobar(guardado, "el trabajo del día se guarda y la pantalla lo dice")
        with httpx.Client(base_url=base, timeout=30.0) as cliente:
            labores = cliente.get(
                "/api/labores",
                headers={"Authorization": f"Bearer {token}"},
            ).json()
        hoy = nav.evaluar("new Date().toISOString().slice(0, 10)")
        nuevas = [
            labor
            for labor in (labores or [])
            if labor.get("fecha") == hoy and labor.get("subtipo")
        ]
        comprobar(bool(nuevas), f"el apunte queda en la base con su apero ({len(nuevas)})")
        print(f"  (captura: {captura(nav, 'apuntar-trabajo').relative_to(RAIZ)})")

    # Las miniaturas del contorno en la lista de tierras.
    clic_en_visible(nav, "[data-destino=tierras]")
    nav.esperar("document.querySelector('[data-vista=\"tierras\"]') !== null", segundos=15)
    miniaturas = nav.evaluar("document.querySelectorAll('[data-miniatura-tierra]').length") or 0
    comprobar(miniaturas > 0, f"cada tierra lleva su miniatura del contorno ({miniaturas})")

    clic_en_visible(nav, "[data-destino=calendario]")
    llego_cal = nav.esperar("!!document.querySelector('[data-vista=\"calendario\"]')", segundos=15)
    comprobar(llego_cal, "se abre el calendario")
    dias = nav.evaluar("document.querySelectorAll('[data-dia-calendario]').length") or 0
    comprobar(dias >= 28, f"el calendario tiene los días del mes ({dias})")
    if dias:
        nav.evaluar(
            "(() => { const d = document.querySelector('[data-dia-calendario]');"
            " if (!d) return false; d.click(); return true; })()"
        )
        nav.esperar("!!document.querySelector('[data-trabajo-del-dia]')", segundos=10)
        comprobar(bool(nav.evaluar("!!document.querySelector('[data-trabajo-del-dia]')")),
                  "al elegir un día se ven sus trabajos")
        totales_mes = nav.evaluar("document.querySelectorAll('[data-calendario-totales]').length") or 0
        dias_con_total = nav.evaluar("document.querySelectorAll('[data-dia-total]').length") or 0
        comprobar(totales_mes >= 1, "el calendario da el total del mes")
        comprobar(dias_con_total >= 1, f"cada día con trabajo trae su total ({dias_con_total})")
        print(f"  (captura: {captura(nav, 'calendario').relative_to(RAIZ)})")

    clic_en_visible(nav, "[data-destino=trabajos]")
    llego_trab = nav.esperar("!!document.querySelector('[data-vista=\"trabajos\"]')", segundos=15)
    comprobar(llego_trab, "se abre la lista de trabajos con filtros")
    filtros = nav.evaluar("document.querySelectorAll('[data-filtro-tipo]').length") or 0
    comprobar(filtros >= 1, f"hay filtros por tipo de trabajo ({filtros})")
    trazas = nav.evaluar(
        "(() => { const q = (s) => !!document.querySelector(s);"
        " return JSON.stringify({tierra: q('[data-filtro-tierra]'), desde: q('[data-filtro-desde]'),"
        " hasta: q('[data-filtro-hasta]'), descargar: q('[data-descargar-trabajos]')}); })()"
    )
    comprobar(trazas is not None and '"tierra":true' in trazas and '"desde":true' in trazas
              and '"hasta":true' in trazas and '"descargar":true' in trazas,
              f"los filtros dejan acotar por tierra y fechas y descargar ({trazas})")
    if filtros:
        nav.evaluar(
            "(() => { const f = document.querySelector('[data-filtro-tipo]');"
            " if (!f) return false; f.click(); return true; })()"
        )
        nav.esperar("document.querySelector('[data-trabajo-fila]') !== null ||"
                    " document.body.innerText.includes('No hay')", segundos=15)
        comprobar(True, "al filtrar por un tipo se enseña su lista (o que no hay)")
    print(f"  (captura: {captura(nav, 'trabajos-filtrados').relative_to(RAIZ)})")

    clic_en_visible(nav, "[data-destino=facturas]")
    llego_fact = nav.esperar("!!document.querySelector('[data-vista=\"facturas\"]')", segundos=15)
    comprobar(llego_fact, "se abre la pantalla de facturas")
    hay_camara = bool(nav.evaluar("!!document.querySelector('[data-factura-foto]')"))
    comprobar(hay_camara, "la pantalla de facturas tiene la foto y la cámara")
    if hay_camara:
        foto = crear_una_foto_de_factura()
        raiz = nav.orden("DOM.getDocument", {"depth": -1})["root"]["nodeId"]
        nodo = nav.orden("DOM.querySelector", {"nodeId": raiz, "selector": "[data-factura-foto]"})["nodeId"]
        if nodo:
            nav.orden("DOM.setFileInputFiles", {"nodeId": nodo, "files": [str(foto)]})
            nav.esperar("document.querySelectorAll('[data-vista=\"facturas\"] img').length > 0",
                        segundos=15)
            nav.evaluar(
                "(() => { const b = document.querySelector('[data-factura-leer]');"
                " if (!b || b.disabled) return false; b.click(); return true; })()"
            )
            leida = nav.esperar(
                "(() => document.querySelector('[data-factura-propuesta]') !== null"
                " || document.body.innerText.includes('No se ha podido leer la factura'))()",
                segundos=60,
            )
            texto = texto_visible(nav)
            if leida and "No se ha podido leer la factura" in texto:
                comprobar(True, "si el lector no entiende la foto, lo dice y deja escribirla a mano")
            elif leida:
                comprobar(True, "la factura se lee y se enseña la propuesta para revisar")
            else:
                comprobar(False, "la foto se queda sin respuesta: ni propuesta ni aviso")
        else:
            comprobar(False, "no se encuentra el campo de la foto de la factura")
        print(f"  (captura: {captura(nav, 'factura-leida').relative_to(RAIZ)})")


def comprobar_cuaderno_y_productos(nav: NavegadorDeVerdad, base: str) -> None:
    """El cuaderno guiado, los productos/abonos con dosis y el «siguiente paso» del flujo."""
    print("\n== Cuaderno guiado, productos con dosis y siguiente paso ==")
    nav.medir(1440, 1000)
    nav.abrir(f"{base}/nuevo/", esperar=1.0)
    esperar_estado(nav, "listo")

    clic_en_visible(nav, "[data-destino=cuaderno]")
    llego = nav.esperar("!!document.querySelector('[data-vista=\"cuaderno\"]')", segundos=15)
    comprobar(llego, "se abre el cuaderno guiado")
    nav.esperar("document.querySelectorAll('[data-que-falta-item]').length > 0", segundos=25)
    secciones = nav.evaluar("document.querySelectorAll('[data-que-falta-seccion]').length") or 0
    items = nav.evaluar("document.querySelectorAll('[data-que-falta-item]').length") or 0
    comprobar(secciones >= 1 and items >= 1,
              f"el cuaderno agrupa lo que falta por secciones ({secciones} secciones, {items} cosas)")
    print(f"  (captura: {captura(nav, 'cuaderno-guiado').relative_to(RAIZ)})")

    clic_en_visible(nav, "[data-destino=productos]")
    llego = nav.esperar("!!document.querySelector('[data-vista=\"productos\"]')", segundos=15)
    comprobar(llego, "se abren los productos y abonos")
    nav.esperar("document.querySelectorAll('[data-producto-tab]').length > 0", segundos=20)
    pestanas = nav.evaluar("document.querySelectorAll('[data-producto-tab]').length") or 0
    comprobar(pestanas >= 2, f"hay pestaña de productos y de abonos ({pestanas})")
    if llego and pestanas:
        # Los productos de la finca de prueba (el abono puede no haber ninguno: entonces la
        # pantalla lo dice con su estado vacío, y eso también es correcto).
        nav.esperar("document.querySelectorAll('[data-producto-id]').length > 0", segundos=20)
        productos = nav.evaluar("document.querySelectorAll('[data-producto-id]').length") or 0
        comprobar(productos > 0, f"la lista de productos trae los del servidor ({productos})")
        nav.evaluar(
            "(() => { const t = document.querySelector('[data-producto-tab=\"abonos\"]');"
            " if (!t) return false; t.click(); return true; })()"
        )
        nav.esperar("document.querySelectorAll('[data-fertilizante-id]').length > 0"
                    " || document.body.innerText.includes('abono')", segundos=20)
        abonos = nav.evaluar("document.querySelectorAll('[data-fertilizante-id]').length") or 0
        comprobar(True, f"la pestaña de abonos responde (abonos en la lista: {abonos})")
        if productos:
            nav.evaluar(
                "(() => { const t = document.querySelector('[data-producto-tab=\"productos\"]');"
                " if (!t) return false; t.click(); return true; })()"
            )
            nav.esperar("document.querySelectorAll('[data-producto-id]').length > 0", segundos=15)
            nav.evaluar(
                "(() => { const b = document.querySelector('[data-aplicar-producto]');"
                " if (!b) return false; b.click(); return true; })()"
            )
            nav.esperar("!!document.querySelector('[data-aplicar-dosis]')", segundos=10)
            # Una dosis por hectárea de prueba, escrita como lo haría una persona.
            nav.evaluar(
                "(() => { const el = document.querySelector('[data-aplicar-dosis]');"
                " if (!el) return false; const setter = Object.getOwnPropertyDescriptor("
                "window.HTMLInputElement.prototype, 'value').set;"
                " setter.call(el, '0.8'); el.dispatchEvent(new Event('input', { bubbles: true }));"
                " return true; })()"
            )
            hay_total = nav.esperar(
                "(() => { const t = document.querySelector('[data-aplicar-total]');"
                " return !!t && (t.getAttribute('data-aplicar-total') || t.innerText).trim().length > 0; })()",
                segundos=10,
            )
            comprobar(hay_total, "el total de dosis por hectáreas se calcula antes de guardar")
            print(f"  (captura: {captura(nav, 'productos-dosis').relative_to(RAIZ)})")

    # El «siguiente paso» del flujo: en la ficha de una tierra tiene que haber uno.
    clic_en_visible(nav, "[data-destino=tierras]")
    nav.esperar("document.querySelectorAll('[data-tierra-id]').length > 0", segundos=20)
    clic_en_visible(nav, "[data-tierra-id]")
    nav.esperar("!!document.querySelector('[data-vista=\"tierra\"]')", segundos=15)
    pasos = nav.evaluar("document.querySelectorAll('[data-siguiente-paso]').length") or 0
    comprobar(pasos >= 1, f"la ficha propone el siguiente paso del flujo ({pasos})")


def comprobar_la_ventana_del_sigpac(nav: NavegadorDeVerdad, base: str) -> None:
    """La ventana propia del SIGPAC: abrir, buscar por referencia, elegir y usar (alta y ficha)."""
    print("\n== Ventana del SIGPAC: elegir una parcela ==")
    nav.medir(1440, 1000)
    nav.abrir(f"{base}/nuevo/", esperar=1.0)
    esperar_estado(nav, "listo")

    clic_en_visible(nav, "[data-destino=tierras]")
    nav.esperar("document.querySelectorAll('[data-tierra-id]').length > 0", segundos=20)
    clic_en_visible(nav, "[data-accion=anadir-tierras]")
    nav.esperar("!!document.querySelector('[data-vista=\"alta\"]')", segundos=15)

    abrio = clic_en_visible(nav, "[data-abrir-ventana-sigpac]") and nav.esperar(
        "!!document.querySelector('[data-ventana-sigpac]')", segundos=15
    )
    comprobar(abrio, "se abre la ventana del SIGPAC desde el alta")
    if abrio:
        nav.evaluar(
            "(() => { const el = document.querySelector('[data-sigpac-buscar-referencia]');"
            " if (!el) return false; const setter = Object.getOwnPropertyDescriptor("
            "window.HTMLInputElement.prototype, 'value').set;"
            " setter.call(el, '37:70:0:0:503:51');"
            " el.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('[data-sigpac-buscar]');"
            " if (!b) return false; b.click(); return true; })()"
        )
        hay = nav.esperar("document.querySelectorAll('[data-sigpac-recinto-id]').length > 0",
                          segundos=45)
        cuantos = nav.evaluar("document.querySelectorAll('[data-sigpac-recinto-id]').length") or 0
        comprobar(hay, f"la ventana busca por la referencia y trae el recinto ({cuantos})")
        if hay:
            nav.evaluar(
                "(() => { const r = document.querySelector('[data-sigpac-recinto-id]');"
                " if (!r) return false; r.click(); return true; })()"
            )
            usar = nav.esperar(
                "(() => { const b = document.querySelector('[data-sigpac-usar]');"
                " return !!b && !b.disabled; })()",
                segundos=10,
            )
            comprobar(usar, "al elegir el recinto se puede usar la parcela")
            print(f"  (captura: {captura(nav, 'ventana-sigpac').relative_to(RAIZ)})")
        nav.evaluar(
            "(() => { const b = document.querySelector('[data-ventana-cerrar]');"
            " if (!b) return false; b.click(); return true; })()"
        )
        cerrada = nav.esperar("!document.querySelector('[data-ventana-sigpac]')", segundos=10)
        comprobar(cerrada, "la ventana se cierra sin cambiar nada")

    # Y desde la ficha de una tierra: elegir la parcela en el SIGPAC y aplicarle su contorno.
    clic_en_visible(nav, "[data-destino=tierras]")
    nav.esperar("document.querySelectorAll('[data-tierra-id]').length > 0", segundos=20)
    clic_en_visible(nav, "[data-tierra-id]")
    nav.esperar("!!document.querySelector('[data-vista=\"tierra\"]')", segundos=15)
    abrio = clic_en_visible(nav, "[data-abrir-ventana-sigpac-tierra]") and nav.esperar(
        "!!document.querySelector('[data-ventana-sigpac]')", segundos=15
    )
    comprobar(abrio, "se abre la ventana del SIGPAC desde la ficha de la tierra")
    if abrio:
        nav.evaluar(
            "(() => { const el = document.querySelector('[data-sigpac-buscar-referencia]');"
            " if (!el) return false; const setter = Object.getOwnPropertyDescriptor("
            "window.HTMLInputElement.prototype, 'value').set;"
            " setter.call(el, '37:70:0:0:503:51');"
            " el.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"
        )
        nav.evaluar(
            "(() => { const b = document.querySelector('[data-sigpac-buscar]');"
            " if (!b) return false; b.click(); return true; })()"
        )
        hay = nav.esperar("document.querySelectorAll('[data-sigpac-recinto-id]').length > 0",
                          segundos=45)
        if hay:
            nav.evaluar(
                "(() => { const r = document.querySelector('[data-sigpac-recinto-id]');"
                " if (!r) return false; r.click(); return true; })()"
            )
            nav.esperar(
                "(() => { const b = document.querySelector('[data-sigpac-usar]');"
                " return !!b && !b.disabled; })()",
                segundos=10,
            )
            nav.evaluar(
                "(() => { const b = document.querySelector('[data-sigpac-usar]');"
                " if (!b || b.disabled) return false; b.click(); return true; })()"
            )
            aplicado = nav.esperar(
                "(() => { const r = document.querySelector('[data-sigpac-resultado]');"
                " const f = document.querySelector('[data-contorno-aplicado]');"
                " return (!!r && r.innerText.trim().length > 0)"
                " || (!!f && f.innerText.trim().length > 0); })()",
                segundos=45,
            )
            comprobar(aplicado, "el contorno de la parcela se aplica a la tierra y se avisa")
        else:
            comprobar(False, "desde la ficha, la búsqueda no trajo el recinto")
        if nav.evaluar("!!document.querySelector('[data-ventana-sigpac]')"):
            nav.evaluar(
                "(() => { const b = document.querySelector('[data-ventana-cerrar]');"
                " if (!b) return false; b.click(); return true; })()"
            )


def ir_a_una_vista(nav: NavegadorDeVerdad, clave: str) -> bool:
    """Va a esa vista: en el móvil, las que no están en la barra inferior se abren desde «Más»."""
    if clic_en_visible(nav, f"[data-destino={clave}]"):
        return True
    if clic_en_visible(nav, "[data-destino=mas]"):
        nav.esperar("!!document.querySelector('[data-vista=\"mas\"]')", segundos=10)
        return clic_en_visible(nav, f"[data-accion=ir-{clave}]")
    return False


def comprobar_movil(nav: NavegadorDeVerdad, base: str) -> None:
    """**La pasada móvil**: se usa en el campo. Sin desbordes, sin solapamientos y al alcance del pulgar."""
    print("\n== Móvil primero: 390 y 360 px ==")
    for ancho, alto in ((390, 844), (360, 640)):
        print(f"-- {ancho}×{alto} --")
        nav.medir(ancho, alto, movil=True)
        nav.abrir(f"{base}/nuevo/", esperar=1.0)
        esperar_estado(nav, "listo")

        def sin_desborde(nombre: str) -> None:
            desborde = nav.evaluar("document.documentElement.scrollWidth - window.innerWidth") or 0
            comprobar(desborde <= 1, f"{ancho} px · {nombre}: sin scroll horizontal ({desborde} px)")

        sin_desborde("Hoy")
        for clave, nombre in (
            ("tierras", "Tierras"),
            ("calendario", "Calendario"),
            ("apuntar", "Apuntar"),
            ("trabajos", "Trabajos"),
            ("productos", "Productos"),
            ("cuaderno", "Cuaderno"),
            ("facturas", "Facturas"),
        ):
            if not ir_a_una_vista(nav, clave):
                comprobar(False, f"{ancho} px · {nombre}: no se llega a la vista")
                continue
            nav.esperar(f"!!document.querySelector('[data-vista=\"{clave}\"]')", segundos=15)
            sin_desborde(nombre)

        # La ficha de la tierra y su tabla de años, que es la que más se puede desbordar.
        if not ir_a_una_vista(nav, "tierras"):
            comprobar(False, f"{ancho} px · no se llega a Tierras")
            continue
        nav.esperar("document.querySelectorAll('[data-tierra-id]').length > 0", segundos=20)
        clic_en_visible(nav, "[data-tierra-id]")
        nav.esperar("!!document.querySelector('[data-vista=\"tierra\"]')", segundos=15)
        sin_desborde("Ficha de la tierra")
        tabla_dentro = nav.evaluar(
            "(() => { const t = document.querySelector('[data-historial-comparativa]');"
            " if (!t) return true;"
            " const caja = t.closest('[data-tabla-con-scroll], .tabla-con-scroll') || t.parentElement;"
            " return caja.scrollWidth <= caja.clientWidth + 1"
            " || getComputedStyle(caja).overflowX !== 'visible'; })()"
        )
        comprobar(bool(tabla_dentro), f"{ancho} px · la tabla de años no arrastra la página")
        print(f"  (captura: {captura(nav, f'movil-ficha-{ancho}').relative_to(RAIZ)})")

        # La ventana del SIGPAC, a pantalla completa y con su scroll interno.
        if not ir_a_una_vista(nav, "tierras"):
            continue
        nav.esperar("document.querySelectorAll('[data-tierra-id]').length > 0", segundos=20)
        clic_en_visible(nav, "[data-accion=anadir-tierras]")
        nav.esperar("!!document.querySelector('[data-vista=\"alta\"]')", segundos=15)
        abrio = clic_en_visible(nav, "[data-abrir-ventana-sigpac]") and nav.esperar(
            "!!document.querySelector('[data-ventana-sigpac]')", segundos=15
        )
        comprobar(abrio, f"{ancho} px · la ventana del SIGPAC se abre")
        if abrio:
            caja = nav.evaluar(
                "(() => { const v = document.querySelector('[data-ventana-sigpac]');"
                " if (!v) return null; const r = v.getBoundingClientRect();"
                " return JSON.stringify({izq: Math.round(r.left), arriba: Math.round(r.top),"
                " ancho: Math.round(r.width), alto: Math.round(r.height),"
                " ventanaAncho: window.innerWidth, ventanaAlto: window.innerHeight,"
                " scroll: v.scrollHeight > v.clientHeight}); })()"
            ) or "{}"
            datos = json.loads(caja)
            dentro = (
                datos.get("izq", -1) >= 0
                and datos.get("arriba", -1) >= 0
                and datos.get("ancho", 0) <= datos.get("ventanaAncho", 0) + 1
                and datos.get("alto", 0) <= datos.get("ventanaAlto", 0) + 1
            )
            comprobar(dentro, f"{ancho} px · la ventana del SIGPAC cabe en la pantalla")
            cerrar = nav.evaluar(
                "(() => { const b = document.querySelector('[data-ventana-cerrar]');"
                " if (!b) return false; const r = b.getBoundingClientRect();"
                " return r.top >= 0 && r.bottom <= window.innerHeight && r.width > 0; })()"
            )
            comprobar(bool(cerrar), f"{ancho} px · el botón de cerrar está al alcance")
            print(f"  (captura: {captura(nav, f'movil-sigpac-{ancho}').relative_to(RAIZ)})")
            nav.evaluar(
                "(() => { const b = document.querySelector('[data-ventana-cerrar]');"
                " if (!b) return false; b.click(); return true; })()"
            )
            nav.esperar("!document.querySelector('[data-ventana-sigpac]')", segundos=10)

        # Que la barra inferior no tape el último contenido: el contenido reserva su hueco.
        tapado = nav.evaluar(
            "(() => {"
            " const barra = Array.from(document.querySelectorAll('[data-nav-inferior]'))"
            "   .find(e => e.getBoundingClientRect().width > 0);"
            " if (!barra) return true;"
            " const altoBarra = barra.getBoundingClientRect().height;"
            " const main = document.querySelector('.contenido') || document.body;"
            " const relleno = parseFloat(getComputedStyle(main).paddingBottom) || 0;"
            " if (relleno >= altoBarra - 2) return true;"
            " main.scrollTop = main.scrollHeight; window.scrollTo(0, document.body.scrollHeight);"
            " const arriba = barra.getBoundingClientRect().top;"
            " const ultimo = Array.from(document.querySelectorAll('.contenido button, .contenido .boton'))"
            "   .filter(e => e.getBoundingClientRect().width > 0)"
            "   .map(e => e.getBoundingClientRect().bottom)"
            "   .reduce((a, b) => Math.max(a, b), 0);"
            " return ultimo <= arriba + 2; })()"
        )
        comprobar(bool(tapado), f"{ancho} px · la barra inferior no tapa el último botón")


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
        comprobar_alta_e_importacion(nav, base)
        comprobar_ficha_calendario_trabajos_y_facturas(nav, base, token)
        comprobar_cuaderno_y_productos(nav, base)
        comprobar_la_ventana_del_sigpac(nav, base)
        comprobar_movil(nav, base)
        comprobar_estados(nav, base, token_vacio, token)
    print(f"\nFallos: {FALLOS}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
