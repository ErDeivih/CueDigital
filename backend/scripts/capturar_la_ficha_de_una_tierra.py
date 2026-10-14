"""Capturar la FICHA DE UNA TIERRA **con sus papeles dentro** (14/10/2026).

POR QUE EXISTE. La ficha de una tierra tiene desde hoy (CRM-06) una seccion con **sus** papeles: un contrato de
arrendamiento, la factura de esa parcela, una inspeccion. Y **una pantalla vacia no se puede juzgar** — es la
trampa que ya costo una ronda en esta sesion, y la dice el guion de al lado—, asi que hay que montar el caso
antes de capturar: una tierra, **un papel subido por su puerta de verdad** (`POST /api/bandeja/subir`) y
**enlazado por la clase `tierra`** (`POST /api/bandeja/{id}/vincular`), como lo haria el agricultor.

El escenario **no se inventa aqui**: se piden prestados los constructores de `datos_representativos`, y la
llamada al servidor es la misma `_api` que usan los otros dos guiones de captura. Lo unico propio es el caso.

Y **ademas de la foto se comprueba**: la seccion tiene que estar y traer el titulo del papel. Una captura sin
comprobacion es una foto, no una prueba.

Uso:  python scripts/capturar_la_ficha_de_una_tierra.py <direccion> [nombre] [ancho]
"""

from __future__ import annotations

import base64
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from capturar_la_pantalla_del_reparto import _api  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
NOMBRE = sys.argv[2] if len(sys.argv) > 2 else "ficha-de-una-tierra-con-papeles"
ANCHO = int(sys.argv[3]) if len(sys.argv) > 3 else 1440
CARPETA = pathlib.Path(r"F:\EspacioCodigo\CueDigital\docs\capturas")

# Un PDF minimo **de verdad** (empieza por %PDF y acaba en %%EOF): el guardin del fichero mira la cabecera.
UN_PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
EL_PAPEL = "Contrato de arrendamiento de El Prado"


def _subir_el_papel(token: str) -> int:
    """Sube un papel por su puerta de verdad. Devuelve su id.

    Se hace con `httpx` y no con `_api` porque esta puerta pide **multipart**, y `_api` manda JSON.
    """
    import httpx

    respuesta = httpx.post(
        f"{DIRECCION}/api/bandeja/subir",
        headers={"Authorization": f"Bearer {token}"},
        files={"fichero": ("contrato-de-arrendamiento.pdf", UN_PDF, "application/pdf")},
        data={"tipo": "contrato"},
        timeout=60.0,
    )
    respuesta.raise_for_status()
    return int(respuesta.json()["papel"]["id"])


def main() -> int:
    print(f"  (direccion: {DIRECCION}   ancho: {ANCHO})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token

    # **Una tierra del escenario, por su puerta.**
    tierras = _api("/api/parcelas", token, metodo="GET")
    lista = tierras if isinstance(tierras, list) else (tierras or {}).get("parcelas") or []
    if not lista:
        print("  (el escenario no ha traido tierras: no hay ficha que capturar)")
        return 1
    tierra = lista[0]
    tierra_id = int(tierra["id"])
    print(f"  (la tierra: {tierra_id} {tierra.get('alias') or tierra.get('nombre') or ''})")

    papel_id = _subir_el_papel(token)
    enlace = _api(
        f"/api/bandeja/{papel_id}/vincular", token, {"clase": "tierra", "entidad_id": tierra_id}
    )
    print(f"  (el papel {papel_id}, enlazado: {str(enlace)[:80]})")

    # **Lo que contesta la puerta, preguntado desde aqui** (el guion tiene el vale): asi se sabe si el
    # problema esta en el servidor o en la pantalla, sin adivinar.
    puerta = _api(
        f"/api/bandeja?estado=todos&clase=tierra&entidad_id={tierra_id}", token, metodo="GET"
    )
    suyos = (puerta or {}).get("papeles") if isinstance(puerta, dict) else None
    print(f"  (lo que contesta la puerta: {len(suyos) if suyos is not None else 'sin papeles'} papeles)")

    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"{NOMBRE}.png"
    with NavegadorDeVerdad(ancho=ANCHO, alto=1000) as nav:
        nav.medir(ANCHO, 1000, movil=ANCHO < 700)
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
        )
        nav.abrir(f"{DIRECCION}/#/tierras/{tierra_id}/historial", esperar=3.0)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
        destino.write_bytes(crudo)
        # **Y ademas de la foto, la comprobacion**: la seccion y su papel tienen que estar en el texto.
        # **Por ESTRUCTURA, no por una cadena que yo suponga**: se busca el `h2` de la seccion y se
        # mira la lista que lleva debajo. El titulo del papel lo pone el servidor (sale del nombre del
        # fichero), asi que aqui se comprueba que **hay una fila** y se devuelve su texto tal cual, sin
        # inventarse como se llama.
        tierraIdDeLaPagina = tierra_id
        suyo = nav.evaluar(
            "(() => { const pantalla = document.querySelector('#pantalla');"
            " const textos = Array.from(pantalla ? pantalla.querySelectorAll('h2') : [])"
            "   .map(h => h.innerText.trim());"
            " const h2 = Array.from(pantalla ? pantalla.querySelectorAll('h2') : [])"
            "   .find(h => h.innerText.includes('Los papeles de esta tierra'));"
            " const lista = h2 && h2.nextElementSibling && h2.nextElementSibling.tagName === 'UL'"
            "   ? h2.nextElementSibling : null;"
            " const filas = lista ? Array.from(lista.querySelectorAll('li')).map(li => li.innerText.trim()) : [];"
            " const peticiones = performance.getEntriesByType('resource')"
            "   .map(e => e.name).filter(n => n.indexOf('bandeja') >= 0);"
            " const xhr = new XMLHttpRequest();"
            " xhr.open('GET', '/api/bandeja?estado=todos&clase=tierra&entidad_id=" + str(tierraIdDeLaPagina) + "&sonda=1', false);"
            " xhr.setRequestHeader('Authorization', 'Bearer ' + (localStorage.getItem('cuedigital.token') || ''));"
            " xhr.send();"
            " const estadoXhr = xhr.status;"
            " let cuantosPapeles = null; let cuantosDice = null;"
            " try { const cuerpo = JSON.parse(xhr.responseText || '{}');"
            "   cuantosPapeles = Array.isArray(cuerpo.papeles) ? cuerpo.papeles.length : 'no es lista';"
            "   cuantosDice = cuerpo.cuantos; } catch (e) { cuantosPapeles = 'no es JSON'; }"

            " const textoPantalla = pantalla ? pantalla.innerText : '';"
            " const cabecera = textoPantalla.slice(0, 220);"
            " const avisos = Array.from(pantalla ? pantalla.querySelectorAll('.aviso') : [])"
            "   .map(a => a.innerText.trim());"
            " const sonda = window.__sondaPapeles;"
            " return { cabecera: cabecera, avisos: avisos, sonda: sonda, seccion: Boolean(h2), filas: filas, peticiones: peticiones, estadoXhr: estadoXhr, cuantosPapeles: cuantosPapeles, cuantosDice: cuantosDice,"
            "          vacio: Boolean(pantalla && pantalla.innerText.includes('No tiene ningun papel enlazado')),"
            "          secciones: textos }; })()"
        )
        # **Segunda vuelta a la misma ficha** (14/10/2026): es el experimento que distingue las dos
        # causas que quedan. Si los papeles salen AHORA y no la primera vez, el fallo es de TIEMPO (el
        # repintado llega antes que la lista); si siguen sin salir, es de DATOS.
        nav.abrir(f"{DIRECCION}/#/tierras/{tierra_id}/historial", esperar=3.0)
        nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
        segunda = nav.evaluar(
            "(() => { const p = document.querySelector('#pantalla'); const t = p ? p.innerText : '';"
            " const h2 = Array.from(p ? p.querySelectorAll('h2') : [])"
            "   .find(x => x.innerText.includes('Los papeles de esta tierra'));"
            " const ul = h2 && h2.nextElementSibling && h2.nextElementSibling.tagName === 'UL'"
            "   ? h2.nextElementSibling : null;"
            " return { filas: ul ? ul.querySelectorAll('li').length : 0,"
            "          diceVacio: t.includes('No tiene ningun papel enlazado') }; })()"
        )
        print(f"  (segunda vuelta a la misma ficha: {json.dumps(segunda, ensure_ascii=False)})")

    ancho_imagen, alto_imagen = struct.unpack(">II", crudo[16:24])
    print(f"  captura: {destino}")
    print(f"  imagen: {ancho_imagen}x{alto_imagen}")
    print(f"  la pantalla: {json.dumps(suyo, ensure_ascii=False)}")
    if not (suyo or {}).get("seccion"):
        print("  >> LA SECCION NO ESTA: la captura no vale como prueba")
        return 2
    if not (suyo or {}).get("filas"):
        print("  >> LA SECCION ESTA VACIA: el papel enlazado no sale en su ficha")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
