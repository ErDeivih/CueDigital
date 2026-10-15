"""El recorrido de la APLICABILIDAD CON EVIDENCIA Y FECHA, **andado desde la pantalla** (14/10/2026).

POR QUE EXISTE. El contrato del CRM-07 pide, para cada obligacion de una maquina, «aplicabilidad con
**evidencia y fecha**» (es su punto #6). Hasta hoy la obligacion tenia `aplicabilidad` («si le toca», «no
le toca», «no lo se») y `origen` («de donde sale eso»), y `origen = "documento"` decia que aquello salia
de **un documento** —**sin decir cual**—: la ficha afirmaba tener un papel y no habia forma de decir cual
era ni de cuando, asi que no se podia abrir y no se podia ensenar en una inspeccion. Lo cuenta, con esas
palabras, el comentario de `tests/test_los_papeles_y_las_facturas_se_pueden_corregir.py` (la cuarta
dependencia de un papel).

Lo que se anadio, y es lo que se anda aqui, son **dos campos** de `obligaciones_de_maquina`:
`documento_id` (el papel que demuestra **por que** le toca, elegido entre los papeles de la finca) y
`fecha_de_la_evidencia` (**de cuando es ese papel**, que no es cuando se apunto). La pantalla los ensena
pegados a la respuesta de «de donde sale», porque es eso lo que demuestran.

**Y una suite no lo ve entero.** Las pruebas del servidor mandan el `PUT` a mano y por eso pueden pasar
mientras la pantalla no manda el papel, o lo manda y el campo de la fecha se pierde al repintar. Lo que
se anda aqui es el camino del agricultor: abrir la ficha de la maquina, escribir de cuando es el papel,
**elegir el papel** —que es lo que guarda las dos cosas a la vez— y leer despues lo que la pantalla
ensena. *Mirar la puerta no acredita la pantalla*, que es la leccion que esta casa ya ha pagado.

El escenario y la forma no se inventan: se piden prestados a los guiones de la casa (`preparar`, `_api`,
`NavegadorDeVerdad`), y la estructura entera es la del guion hermano
`scripts/verificar_el_recorrido_de_una_semilla.py`. Lo unico propio es el caso.

QUE COMPRUEBA, PASO A PASO
--------------------------
  0. **El caso, montado por las puertas de verdad** (no por la base): una maquina, **un papel subido por
     su puerta** (`POST /api/bandeja/subir`, que es la puerta de la bandeja documental: el papel queda
     guardado en «los papeles» de la finca, que es la lista de la que la pantalla lo elige), y la
     obligacion **ya declarada «sale de un documento» sin decir cual** —que es exactamente el estado que
     el contrato venia a corregir, montado con el `PUT` de la puerta—. De esa declaracion se guarda el
     `id` de la fila, que es lo que despues se busca en la auditoria (la ficha no lo publica: ver la
     nota del paso 7).
  1. **La ficha se abre por su direccion**: `#/maquinaria/<id>`, averiguada en `rutas.js` (la clave
     `maquina`, patron `["maquinaria", ":id"]`), y con ella el bloque del papel de esa obligacion.
  2. **La fecha se escribe en su campo** (`#obligacion-fecha-<tipo>`, que lleva
     `data-campo="fecha_de_la_evidencia"`), **antes** de elegir el papel, porque **elegir el papel es lo
     que guarda las dos cosas**: la fecha no tiene boton propio, viaja con el papel.
  3. **El papel se elige en la pantalla**: se busca entre los botones del bloque el que lleva **el papel
     que se ha subido** (`data-campo="documento_id"`, `data-valor="<id del papel>"`) y se comprueba que
     su texto es el nombre del papel, que es lo que el agricultor lee antes de pulsarlo.
  4. **Se ha guardado**, y por **dos vias**: la puerta (`GET /api/maquinaria/<id>`) devuelve
     `documento_de_la_aplicabilidad_id`, `la_aplicabilidad_trae_papel` y `fecha_de_la_evidencia`; y la
     **pantalla, tras recargar de verdad** (`Page.reload`, no volver a pedir la misma direccion: esto es
     un enrutador de `#` y no crea documento nuevo), ensena el nombre del papel y la fecha en su campo.
  5. **LA REGLA A1, que es la trampa de esta entrega**: se declara la aplicabilidad **otra vez** sin tocar
     el campo de la fecha, y despues de recargar **la fecha sigue ahi y el papel sigue elegido**. *Un
     `null` explicito borraria; no mandarlo, no.* Se comprueba ademas la otra mitad de la regla —**lo que
     la peticion no manda, no se borra**—: se vacia el campo de la fecha, se declara otra vez y la fecha
     guardada sigue en su sitio.
  6. **El aislamiento**: el papel de **otra finca** no vale. Por la puerta, un `PUT` con ese
     `documento_id` contesta **404** y **no escribe nada** (ni en la puerta, ni en la pantalla, ni en el
     rastro: el paso 7 lo mira tambien en la auditoria).
  7. **La auditoria**: el cambio de esa obligacion tiene que dejar rastro. La auditoria **no tiene puerta
     de API** en este proyecto: se lee de la base, en solo lectura, como hacen
     `comprobar_la_auditoria_de_una_anulacion.py` y `comprobar_la_compra_de_punta_a_punta.py`. Se exige
     —con asercion, no imprimiendo— que la correccion de **esa** obligacion nombre `documento_id` con el
     valor que se puso y `fecha_de_la_evidencia` con su fecha.

LO QUE NO SE HACE AQUI
----------------------
No se levanta ningun servidor y no se toca el codigo de produccion: **se habla con el que ya este
levantado** en la direccion que se le pase, y la base se abre **en solo lectura** (`mode=ro`) para mirar
la auditoria. Este guion no modifica nada del codigo de produccion.

Uso:  python scripts/verificar_el_recorrido_de_la_aplicabilidad.py [direccion] [ruta-de-la-base]
      (la direccion, por defecto http://127.0.0.1:8029; la base, por defecto backend/cuedigital.db,
      que es donde la deja el servidor con `sqlite:///./cuedigital.db` y el directorio de trabajo en
      `backend/`; la auditoria se lee de ahi, en solo lectura)
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from capturar_la_pantalla_del_reparto import _api  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad, SinNavegador  # noqa: E402

# La consola de Windows no sabe escribir todo lo que puede salir por aqui (tildes y comillas de la
# pantalla). Se pide UTF-8 y que no reviente por un caracter raro: un guion de verificacion que muere
# al imprimir lo que ha visto no verifica nada.
if getattr(sys, "stdout", None) is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
RAIZ = pathlib.Path(__file__).resolve().parents[1]
LA_BASE = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "cuedigital.db"

# ---------------------------------------------------------------------------------------------
# LA DIRECCION DE LA PANTALLA, averiguada en el codigo (no supuesta)
# ---------------------------------------------------------------------------------------------
# * `backend/web/react/rutas.js` tiene la tabla `PANTALLAS`, y ahi esta, palabra por palabra,
#   `{ clave: "maquina", patron: ["maquinaria", ":id"] }`: **el identificador viaja en el camino**, asi
#   que recargar devuelve al agricultor a la ficha de esa maquina y no a la lista.
# * `backend/web/app.js` la abre desde `if (clave === "maquina") return abrirUnaMaquina(parametros.id)`
#   (`abrirLaPantalla`) y su renglon del menu es el modulo `maquinaria` (`MODULO_DE_LA_PANTALLA`), asi
#   que `apuntarLaDireccion` escribe exactamente esta direccion (`if (clave === "maquina") {
#   parametros.id = maquina.id }`).
#
# **El identificador no se supone**: lo devuelve el servidor al dar de alta la maquina (paso 0).
LA_PANTALLA_DE_UNA_MAQUINA = "#/maquinaria/{id}"

# ---------------------------------------------------------------------------------------------
# LOS `id` Y LOS `data-*` DEL BLOQUE DEL PAPEL, averiguados en el codigo (no inventados)
# ---------------------------------------------------------------------------------------------
# * El campo de la fecha: `backend/web/react/pantallas/maquinaria.js`, funcion `Obligacion`, lo pinta con
#   `id={`obligacion-fecha-${obligacion.tipo}`}`, `type="date"` y `data-campo="fecha_de_la_evidencia"`.
#   **Ese `id` es lo unico que `app.js` tiene para leerlo**, porque su manejador lo busca asi, palabra por
#   palabra (`document.getElementById(`obligacion-fecha-${tipo}`)` en `maquina-declarar`), y lo manda como
#   `fecha_de_la_evidencia`.
# * Los botones del papel: los pinta `OpcionesParaElegir` (`backend/web/react/componentes.js`) con
#   `data-accion` (la que le pasa la ficha: `"maquina-declarar"`), y con `data-<campo>="<valor>"` mas
#   `data-tipo` (los `datos` del bloque). El bloque del papel lo monta `app.js` (`unaMaquinaPreparada`)
#   con `campo: "documento_id"`, `datos: { tipo: obligacion.tipo }` y un valor por papel
#   (`papelesParaElegir`, que usa el `id` del papel). **Un `data-*` vacio no se escribe**
#   (`datosDelBoton`): la opcion «sin papel» no lleva `data-valor`, y por eso el manejador la lee como
#   «ninguno».
LA_OBLIGACION_DE_LA_FECHA = "obligacion-fecha-{tipo}"
EL_CAMPO_DEL_INPUT_DE_LA_FECHA = "fecha_de_la_evidencia"
LA_ACCION_DE_DECLARAR = "maquina-declarar"
EL_CAMPO_DEL_PAPEL = "documento_id"
EL_CAMPO_DE_LA_APLICABILIDAD = "aplicabilidad"

# La fecha conocida que se escribe en el campo. **Un dia cualquiera del pasado, y escrito entero**: la
# fecha del papel la sabe el agricultor, no el programa, y vacio es «no consta» (nunca «hoy»).
FECHA_DE_LA_EVIDENCIA = "2026-03-14"

# La respuesta que se da al re-declarar (paso 5), por su **valor** (el de `maquinaria.APLICABILIDADES`,
# que es el que viaja en el `data-valor`): `si` para la primera vuelta y `no` para la segunda, que es la
# que deja el campo de la fecha vacio para probar que lo que no se manda no se borra.
APLICABILIDAD_PRIMERA = "si"
APLICABILIDAD_OTRA = "no"

# Los rotulos que la pantalla tiene que ensenar, **leidos del servidor** (`/api/interfaz` trae el bloque
# `maquinaria` de `textos.MAQUINARIA_DE_LA_FINCA`): asi este guion no escribe ni una etiqueta de su
# cosecha y, si manana cambia el texto, sigue comprobando lo correcto.
ROTULOS_QUE_HACEN_FALTA = (
    "documento_de_la_aplicabilidad",
    "fecha_de_la_evidencia",
    "sin_papel",
)

# La marca que se deja en la pantalla antes de recargar. Sirve para **probar que se ha recargado**: si
# sigue ahi despues de navegar, lo que se esta leyendo es el documento de antes y la comprobacion no
# probaria nada (dar por bueno lo ya pintado es el fallo que este guion persigue).
MARCA_DE_RECARGA = "__marcaDeLaVisitaAnterior"

COMPROBACIONES = 0
FALLOS: list[str] = []


def comprobar(bien: bool, que: str, esperaba: str = "", encontre: str = "") -> bool:
    """Apunta una comprobacion y lo dice con sus palabras. Devuelve si salio bien.

    Se imprime **siempre lo que se esperaba y lo que se ha encontrado**, tambien cuando sale bien: un
    «OK» sin el dato delante no se puede revisar despues.
    """
    global COMPROBACIONES
    COMPROBACIONES += 1
    print(f"  [{'OK   ' if bien else 'FALLO'}] {que}")
    if esperaba or encontre:
        print(f"          esperaba : {esperaba}")
        print(f"          encontre : {encontre}")
    if not bien:
        FALLOS.append(que)
    return bien


# ---------------------------------------------------------------------------------------------
# Las piezas del bloque del papel, por sus nombres exactos
# ---------------------------------------------------------------------------------------------


def el_identificador_de_la_fecha(tipo: str) -> str:
    """El `id` del campo de la fecha de esa obligacion (`obligacion-fecha-<tipo>`).

    Se compone igual que en `maquinaria.js`, porque es lo unico que `app.js` tiene para leerlo.
    """
    return LA_OBLIGACION_DE_LA_FECHA.format(tipo=tipo)


def el_selector_de_una_opcion(campo: str, tipo: str, valor: str) -> str:
    """El selector de un boton de declarar, por sus `data-*` (los pone `OpcionesParaElegir`).

    `campo` es el campo que se declara (`aplicabilidad`, `origen` o `documento_id`), `tipo` la obligacion
    y `valor` lo que se manda. **Un valor vacio no lleva `data-valor`** (`datosDelBoton`), asi que la
    opcion «sin papel» no se puede pedir por aqui —y no hace falta—.
    """
    return (
        f'button[data-accion="{LA_ACCION_DE_DECLARAR}"]'
        f'[data-campo="{campo}"]'
        f'[data-tipo="{tipo}"]'
        f'[data-valor="{valor}"]'
    )


# ---------------------------------------------------------------------------------------------
# Hablar con la pantalla
# ---------------------------------------------------------------------------------------------


def leer_el_bloque(nav: NavegadorDeVerdad, tipo: str, rotulo_del_papel: str) -> dict:
    """Lo que **ensena** el bloque del papel de esa obligacion.

    Se llega a el **por el campo de la fecha** (`#obligacion-fecha-<tipo>`, que es un `id` unico) y se
    sube a su renglon (`li`): ahi dentro estan el rotulo del papel con lo que ensena —**el nombre del
    papel, que es texto, no un `value`**—, el campo de la fecha y sus botones con sus `data-*`. Se lee el
    texto y no solo el dato porque lo que hay que comprobar es lo que ve el agricultor.
    """
    return nav.evaluar(
        "(() => {"
        " const campo = document.getElementById(" + json.dumps(el_identificador_de_la_fecha(tipo)) + ");"
        " if (!campo) return { hay: false };"
        " const li = campo.closest('li');"
        " if (!li) return { hay: true, sin_renglon: true };"
        " const rotulo = " + json.dumps(rotulo_del_papel) + ";"
        " const detalles = Array.from(li.querySelectorAll('.apunte-detalle'));"
        " const suyo = detalles.find((d) => {"
        "   const s = d.querySelector('strong');"
        "   return Boolean(s) && (s.innerText || '').trim() === rotulo; });"
        " let papel = null;"
        " if (suyo) { const texto = (suyo.innerText || '').replace(/\\s+/g, ' ').trim();"
        "   papel = texto.indexOf(rotulo) === 0 ? texto.slice(rotulo.length).trim() : texto; }"
        " const botones = Array.from(li.querySelectorAll("
        + json.dumps('button[data-campo="' + EL_CAMPO_DEL_PAPEL + '"]') + "))"
        "   .map((b) => ({ valor: b.dataset.valor === undefined ? '' : b.dataset.valor,"
        "                  elegido: b.dataset.elegido || '',"
        "                  accion: b.dataset.accion || '',"
        "                  campo: b.dataset.campo || '',"
        "                  tipo: b.dataset.tipo || '',"
        "                  texto: (b.innerText || '').replace(/\\s+/g, ' ').trim() }));"
        " return { hay: true, papel: papel,"
        "          fecha: String(campo.value || ''),"
        "          campo_del_input: campo.dataset.campo || '',"
        "          tipo_del_input: campo.type || '',"
        "          nombre_de_la_obligacion: ((li.querySelector('h3') || {}).innerText || '').trim(),"
        "          botones: botones,"
        "          texto: (li.innerText || '').replace(/\\s+/g, ' ').slice(0, 400) }; })()"
    ) or {}


def escribir_en_la_fecha(nav: NavegadorDeVerdad, tipo: str, valor: str) -> dict:
    """Escribe en el campo de la fecha **por su `id`**, como lo lee `app.js` al declarar.

    `app.js` no lee un estado de React: mira `document.getElementById('obligacion-fecha-<tipo>').value`
    justo al pulsar. Por eso basta con dejar el valor puesto (y avisar del cambio, que es lo que hace el
    navegador cuando alguien teclea). **Un `<input type="date">` que no entiende el valor lo deja vacio
    sin decir nada**, asi que quien llama mira lo que se ha leido de vuelta.
    """
    return nav.evaluar(
        "(() => { const c = document.getElementById("
        + json.dumps(el_identificador_de_la_fecha(tipo)) + ");"
        " if (!c) return { hay: false };"
        " c.focus();"
        " c.value = " + json.dumps(valor) + ";"
        " c.dispatchEvent(new Event('input', { bubbles: true }));"
        " c.dispatchEvent(new Event('change', { bubbles: true }));"
        " return { hay: true, valor: String(c.value || ''),"
        "          campo: c.dataset.campo || '', tipo: c.type || '' }; })()"
    ) or {}


def pulsar(nav: NavegadorDeVerdad, selector: str) -> bool:
    """Un clic **en la pagina** (`el.click()`), no por coordenadas. **Y dice de verdad si pudo.**

    **Por que, que costo una ronda** (14/10/2026): `nav.pulsar` usa `Input.dispatchMouseEvent`, que
    pincha **donde el elemento esta dibujado**. Si el boton queda **fuera de la vista** o tapado, el
    clic cae al lado —o en nada— y **el guion creia haber pulsado**: el paso 5b decia «pulsado» y
    **no salia ninguna peticion**, y desde fuera parecia un fallo del producto. La casa ya lo tenia
    escrito en `comprobar_el_recorrido_economico.py`: «el boton de este bloque queda debajo de la
    tabla, fuera de la vista; con `.click()` directo si».

    Se hace `scrollIntoView` antes **por si acaso**, y luego `click()`, que dispara el manejador de
    React aunque el elemento no se vea. Y se devuelve **si el elemento existia**: un `true` de adorno
    es lo que hizo que este fallo pareciera otro.
    """
    try:
        pulsado = nav.evaluar(
            "(() => { const el = document.querySelector(" + json.dumps(selector) + ");"
            " if (!el) return false;"
            " el.scrollIntoView({block: 'center'});"
            " el.click();"
            " return true; })()"
        )
    except RuntimeError as fallo:
        print(f"  (no se ha podido pulsar {selector}: {fallo})")
        return False
    if not pulsado:
        print(f"  (no existe el boton {selector}: no se puede pulsar lo que no esta)")
    return bool(pulsado)


def recargar(nav: NavegadorDeVerdad, direccion: str, esperando: str, segundos: float = 25.0) -> bool:
    """Recarga y **comprueba que de verdad se ha recargado** (la marca de la visita anterior ya no esta).

    Se esperan las dos cosas: que el documento sea nuevo y que la pantalla que se espera este montada.

    **`Page.reload` y NO `abrir` a la misma direccion**: este programa es un enrutador de `#`, asi que
    volver a pedir **la misma** direccion **no crea un documento nuevo** y la marca de la visita anterior
    sobrevivia (es el fallo que corrigio el guion hermano, y el detector tenia razon al protestar).
    `Page.reload` es la recarga del navegador, que es lo que hace el agricultor con F5. El parametro
    `direccion` se conserva porque es el que usan las llamadas.
    """
    nav.evaluar(f"window.{MARCA_DE_RECARGA} = 'sigue-ahi'")
    nav.orden("Page.reload", {"ignoreCache": True})
    es_nueva = bool(nav.esperar(f"typeof window.{MARCA_DE_RECARGA} === 'undefined'", segundos=25))
    montada = bool(nav.esperar(esperando, segundos=segundos))
    return es_nueva and montada


def api_con_codigo(camino: str, token: str, cuerpo: dict | None = None, *, metodo: str = "POST"):
    """La misma llamada que `_api`, pero **devolviendo el codigo** en vez de morir con el.

    POR QUE HACE FALTA. `_api` (el de `capturar_la_pantalla_del_reparto.py`) levanta un `SystemExit` en
    cuanto la puerta contesta algo que no sea 2xx —que es lo correcto para los demas guiones—, y aqui el
    **404 es la respuesta que se espera**: si el guion muriera al recibirlo, no podria comprobar que el
    papel de otra finca no ha escrito nada, que es la mitad del caso. La peticion es la misma, con el
    mismo vale y las mismas cabeceras.
    """
    import urllib.error
    import urllib.request

    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(
        f"{DIRECCION}{camino}",
        data=datos,
        method=metodo,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return respuesta.status, json.loads(respuesta.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as fallo:
        return fallo.code, fallo.read().decode("utf-8", "replace")[:300]


def la_obligacion(de_la_puerta: dict, tipo: str) -> dict:
    """La obligacion de ese tipo, tal y como la devuelve la puerta de la ficha."""
    for una in (de_la_puerta or {}).get("obligaciones") or []:
        if str(una.get("tipo")) == str(tipo):
            return una
    return {}


def esperar_a_que_la_puerta_lo_diga(
    token: str, maquina_id, tipo: str, campo: str, valor: str, segundos: float = 25.0
) -> bool:
    """Espera a que **la puerta** confirme que la declaracion ha llegado. Devuelve si lo hizo.

    POR QUE HACE FALTA, Y POR QUE NO VALE MIRAR LA PANTALLA. Elegir una opcion **no tiene boton de
    guardar**: el manejador manda el `PUT` y repinta cuando el servidor contesta. Si el guion recargara
    antes de que la peticion haya llegado, estaria midiendo la regla A1 **sobre una declaracion que no se
    mando**, y la prueba quedaria vacia sin decir nada —que es la peor forma de dar algo por bueno—.

    Y la senal **no puede ser el repintado**: las opciones de la aplicabilidad **no llevan `data-elegido`**
    (el bloque de `app.js` no le pasa `elegido`, al contrario que el del papel), asi que esperar por ahi
    seria esperar 25 segundos a algo que no va a pasar y seguir adelante igual. La senal buena es la
    puerta: se le pregunta hasta que diga el valor que se acaba de pulsar.
    """
    limite = time.time() + segundos
    while time.time() < limite:
        la_suya = la_obligacion(_api(f"/api/maquinaria/{maquina_id}", token, metodo="GET") or {}, tipo)
        if str(la_suya.get(campo)) == str(valor):
            return True
        time.sleep(0.25)
    return False


def subir_el_papel(token: str, titulo: str) -> dict:
    """Sube un papel **por su puerta de verdad** y devuelve lo que el servidor guardo.

    Se usa `POST /api/bandeja/subir`, que es la puerta de la bandeja documental: guarda el fichero tal y
    como llega y **crea el papel en «los papeles» de la finca** (llama a `documentos_api.crear`), que es
    la lista de la que la pantalla lo elige (`GET /api/documentos` → `papelesParaElegir`).

    Se hace con `httpx` y no con `_api` porque esta puerta pide **multipart**, y `_api` manda JSON. El
    PDF lleva el titulo dentro para que **cada vuelta suba bytes distintos**: el mismo fichero dos veces
    contesta 409 («ya estaba») y no crea ninguna ficha, y entonces la prueba no tendria papel.
    """
    import httpx

    un_pdf = (
        b"%PDF-1.4\n% " + titulo.encode("utf-8") + b"\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )
    respuesta = httpx.post(
        f"{DIRECCION}/api/bandeja/subir",
        headers={"Authorization": f"Bearer {token}"},
        files={"fichero": ("el-papel-de-la-prueba.pdf", un_pdf, "application/pdf")},
        data={"tipo": "otros", "titulo": titulo},
        timeout=60.0,
    )
    respuesta.raise_for_status()
    papel = (respuesta.json() or {}).get("papel")
    if not isinstance(papel, dict) or papel.get("id") is None:
        raise SystemExit(
            "no he podido averiguar el papel que se acaba de subir: `POST /api/bandeja/subir` ha "
            f"contestado sin `papel.id`: {str(respuesta.text)[:200]}"
        )
    return papel


def el_papel_de_la_finca(token: str, papel_id: int) -> dict | None:
    """El papel, **buscado en «los papeles» de la finca** (`GET /api/documentos`), que es la lista de la
    que la pantalla lo elige. Devuelve `None` si no esta: eso seria un caso, no una suposicion."""
    papeles = _api("/api/documentos", token, metodo="GET") or {}
    for papel in (papeles or {}).get("documentos") or []:
        if str(papel.get("id")) == str(papel_id):
            return papel
    return None


def main() -> int:
    print("== El recorrido de la aplicabilidad con evidencia y fecha, desde la pantalla ==")
    print(f"  (direccion: {DIRECCION})")
    print(f"  (la base para la auditoria: {LA_BASE})")

    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    print(f"  (la sesion: {escenario.volumen.nombre}; la finca ajena: {escenario.ajena.nombre})")

    # ---------------------------------------------------------------------------------------------
    # 0 · El caso, montado por las puertas de verdad
    # ---------------------------------------------------------------------------------------------
    print("\n0. EL CASO, MONTADO POR LAS PUERTAS DE VERDAD (una maquina, un papel y la obligacion)")

    # **Las palabras que la pantalla tiene que ensenar se leen del servidor** (`/api/interfaz` trae el
    # bloque `maquinaria` de `textos.MAQUINARIA_DE_LA_FINCA`).
    interfaz = _api("/api/interfaz", token, metodo="GET")
    bloque = (interfaz or {}).get("maquinaria") if isinstance(interfaz, dict) else None
    if not isinstance(bloque, dict):
        raise SystemExit(
            "no he podido averiguar los textos de la maquinaria: `/api/interfaz` no trae el bloque "
            "«maquinaria» (lo sirve `routers/interfaz.py` desde `textos.MAQUINARIA_DE_LA_FINCA`)"
        )
    etiquetas = {}
    for clave in ROTULOS_QUE_HACEN_FALTA:
        etiquetas[clave] = bloque.get(clave)
        if not etiquetas[clave]:
            raise SystemExit(
                f"no he podido averiguar el texto `maquinaria.{clave}`: `/api/interfaz` no lo trae, y sin "
                "el no se puede comprobar lo que ensena el bloque del papel"
            )
    # Y las palabras de las respuestas de la aplicabilidad, que son las que llevan sus botones.
    las_aplicabilidades = {
        str(una.get("valor")): una.get("texto")
        for una in (interfaz.get("aplicabilidades_de_una_obligacion") or [])
    }
    for valor in (APLICABILIDAD_PRIMERA, APLICABILIDAD_OTRA):
        if not las_aplicabilidades.get(valor):
            raise SystemExit(
                f"no he podido averiguar el texto `maquinaria.aplicabilidad_{valor}`: `/api/interfaz` no lo "
                "trae en `aplicabilidades_de_una_obligacion`, y sin el no se puede comprobar que el boton "
                "que se pulsa es el que dice lo que se cree"
            )

    # **La maquina, por su puerta** (`POST /api/maquinaria`). Los cuatro campos son los que el esquema
    # exige (los mismos que usa `tests/test_t14_maquinaria.py` en su ayuda `crear_maquina`), y el nombre
    # lleva la hora **y el proceso** para que esta vuelta no se confunda con la anterior —que es el mismo
    # truco que usa `preparar()` para sus correos—.
    marca = f"{int(time.time())}-{os.getpid()}"
    nombre_de_la_maquina = f"El tractor de la aplicabilidad {marca}"
    creada = _api(
        "/api/maquinaria",
        token,
        {
            "nombre": nombre_de_la_maquina,
            "clase": "tractor",
            "propiedad": "propia",
            "disponibilidad": "disponible",
        },
    ) or {}
    maquina_id = creada.get("id")
    if maquina_id is None:
        raise SystemExit(f"no he podido averiguar la maquina que se acaba de crear: {str(creada)[:200]}")
    print(f"  (la maquina: {maquina_id} «{nombre_de_la_maquina}»)")

    # **Cual es la obligacion que se anda**: la primera de las cinco que la ficha ensena, en el orden del
    # servidor (`maquinaria.OBLIGACIONES`). **No se escribe a mano**: se lee de la puerta, y es de donde
    # salen tambien el `id` del campo de la fecha y el `data-tipo` de sus botones.
    ficha = _api(f"/api/maquinaria/{maquina_id}", token, metodo="GET") or {}
    obligaciones = ficha.get("obligaciones") or []
    if not obligaciones:
        raise SystemExit(
            "no he podido averiguar de que obligacion es el papel: la ficha de la maquina no trae "
            "ninguna obligacion (las cinco las sirve `app/maquinaria.py`, `estado_de_todas_las_obligaciones`)"
        )
    tipo = str(obligaciones[0].get("tipo"))
    print(f"  (la obligacion: {tipo}; las cinco de la ficha: {[una.get('tipo') for una in obligaciones]})")

    # **La obligacion, declarada por la puerta tal y como estaba el mundo antes del CRM-07 #6**: dice que
    # sale de un documento (`origen: "documento"`) **sin decir cual**. Es el estado que el contrato venia a
    # corregir, y montarlo asi es lo que hace que **elegir el papel en la pantalla sea una correccion** (y
    # por tanto deje rastro en la auditoria) y no un alta, que no lo deja.
    #
    # **Y de aqui se guarda el `id` de la fila.** La ficha **no lo publica** (`EstadoDeUnaObligacionSalida`
    # no tiene `id`), asi que la unica forma de saber de que fila se habla —que es lo que hay que buscar en
    # la auditoria— es la respuesta de la puerta que la crea (`ObligacionSalida` si lo trae).
    declarada = _api(
        f"/api/maquinaria/{maquina_id}/obligaciones/{tipo}",
        token,
        {"aplicabilidad": "no_se", "origen": "documento"},
        metodo="PUT",
    ) or {}
    obligacion_id = declarada.get("id")
    if obligacion_id is None:
        raise SystemExit(
            "no he podido averiguar de que obligacion hay que buscar el rastro: la respuesta de "
            f"`PUT /api/maquinaria/<id>/obligaciones/{tipo}` no trae el `id` de la fila. Sin el no se puede "
            "decir si la entrada de la auditoria es de ESTA obligacion o de otra "
            "(la ficha no lo publica: `EstadoDeUnaObligacionSalida` no tiene ese campo)"
        )
    print(f"  (la obligacion {tipo} de esa maquina: fila {obligacion_id}, declarada «sale de un documento»)")

    # **El papel, subido por su puerta.** El titulo lleva la hora para que cada vuelta suba bytes
    # distintos y el guardian de duplicados (409) no se cruce en medio.
    titulo_del_papel = f"El papel que demuestra la obligacion de la prueba {marca}"
    el_papel = subir_el_papel(token, titulo_del_papel)
    papel_id = int(el_papel["id"])
    print(f"  (el papel subido: {papel_id} «{el_papel.get('titulo')}»)")

    # **Y tiene que estar en «los papeles» de la finca**, que es la lista de la que la pantalla lo elige:
    # si no estuviera, el recorrido no podria elegirlo y daria un fallo en el paso 3 que no es de la
    # pantalla. Por eso se comprueba **aqui**, contra la puerta, y se usa **el titulo que dice el
    # servidor** (no el que se le mando) como lo que la pantalla tiene que ensenar.
    guardado = el_papel_de_la_finca(token, papel_id)
    if not comprobar(
        guardado is not None,
        "el papel subido esta en «los papeles» de la finca (que es de donde la pantalla lo elige)",
        esperaba=f"el papel {papel_id} en `GET /api/documentos`",
        encontre=(
            "no esta"
            if guardado is None
            else f"titulo={guardado.get('titulo')!r} tipo={guardado.get('tipo')!r}"
        ),
    ):
        print("  >> sin el papel en la lista no se puede andar el recorrido")
        return 1
    titulo_del_papel = str(guardado.get("titulo"))

    # **El papel de la otra finca** (el escenario prepara una finca ajena con marcas inconfundibles). Se
    # busca por su puerta, con **su** vale: es un papel de verdad, de otra explotacion, y es lo que hace
    # falta para el paso 6.
    la_marca_ajena = (escenario.marcas_ajenas or ("", ""))[0]
    papeles_ajenos = _api("/api/documentos", escenario.ajena.token, metodo="GET") or {}
    el_ajeno = next(
        (
            papel
            for papel in (papeles_ajenos or {}).get("documentos") or []
            if la_marca_ajena and la_marca_ajena in str(papel.get("titulo") or "")
        ),
        None,
    )
    if el_ajeno is None:
        raise SystemExit(
            "no he podido averiguar el papel de la otra finca: con el vale de la explotacion ajena, "
            "`GET /api/documentos` no trae ninguno con la marca de la finca ajena "
            f"({la_marca_ajena!r}). Es lo que hace falta para comprobar el aislamiento (paso 6), y sin "
            "datos no se puede inventar"
        )
    papel_ajeno_id = int(el_ajeno["id"])
    print(f"  (el papel de la otra finca: {papel_ajeno_id} «{el_ajeno.get('titulo')}»)")

    # ---------------------------------------------------------------------------------------------
    # Del 1 al 6: el recorrido, en el navegador
    # ---------------------------------------------------------------------------------------------
    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            # El vale se mete **en cada documento nuevo** (y no una vez): asi recargar sigue estando
            # dentro de la sesion, que es lo que hace falta para mirar la pantalla despues de guardar.
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )
            la_direccion = LA_PANTALLA_DE_UNA_MAQUINA.format(id=maquina_id)
            nav.abrir(f"{DIRECCION}/{la_direccion}", esperar=3.0)

            # ---------------------------------------------------------------------------------
            # 1 · La ficha se abre por su direccion
            # ---------------------------------------------------------------------------------
            print(f"\n1. LA FICHA SE ABRE POR SU DIRECCION ({la_direccion})")
            # Se espera a **el campo de la fecha de esa obligacion**, que es lo unico que demuestra que
            # la ficha esta montada y con sus obligaciones dentro (la lista se pinta antes de que llegue
            # la ficha: con el `h1` a la vista todavia no hay ninguna obligacion).
            la_ficha = bool(
                nav.esperar(
                    "document.getElementById("
                    + json.dumps(el_identificador_de_la_fecha(tipo)) + ") !== null",
                    segundos=25,
                )
            )
            el_hash = nav.evaluar("location.hash")
            if not comprobar(
                la_ficha,
                "la ficha de la maquina abre por su direccion y trae el bloque del papel de esa obligacion",
                esperaba=f"{la_direccion} con el campo #{el_identificador_de_la_fecha(tipo)}",
                encontre=f"hash={el_hash!r}",
            ):
                print("  >> sin la ficha no se puede andar el recorrido")
                return 1
            el_bloque = leer_el_bloque(nav, tipo, etiquetas["documento_de_la_aplicabilidad"])
            print(f"  (el bloque del papel: {json.dumps(el_bloque, ensure_ascii=False)[:700]})")
            comprobar(
                el_hash == la_direccion,
                "la barra de direcciones dice exactamente la direccion de esa ficha",
                esperaba=la_direccion,
                encontre=repr(el_hash),
            )
            comprobar(
                bool(el_bloque.get("hay")) and not el_bloque.get("sin_renglon"),
                "el campo de la fecha esta dentro del renglon de su obligacion (y se ve su nombre)",
                esperaba="un `li` con su h3",
                encontre=f"h3={el_bloque.get('nombre_de_la_obligacion')!r}",
            )
            # El campo de la fecha, con lo que `maquinaria.js` le pone: es un `input` de tipo `date` y
            # lleva su `data-campo`, que es el nombre con el que viaja al servidor.
            comprobar(
                el_bloque.get("tipo_del_input") == "date"
                and el_bloque.get("campo_del_input") == EL_CAMPO_DEL_INPUT_DE_LA_FECHA,
                "el campo de la fecha es un `input type=date` con su `data-campo`",
                esperaba=f"type=date y data-campo={EL_CAMPO_DEL_INPUT_DE_LA_FECHA!r}",
                encontre=(
                    f"type={el_bloque.get('tipo_del_input')!r} "
                    f"data-campo={el_bloque.get('campo_del_input')!r}"
                ),
            )
            comprobar(
                (el_bloque.get("papel") or "") == etiquetas["sin_papel"],
                "y de aplicabilidad no consta ningun papel: lo dice con la palabra del servidor",
                esperaba=repr(etiquetas["sin_papel"]),
                encontre=repr(el_bloque.get("papel")),
            )
            los_botones_del_papel = el_bloque.get("botones") or []
            if not comprobar(
                bool(los_botones_del_papel),
                "el bloque trae la lista de papeles para elegir (los de esta finca)",
                esperaba="al menos un boton con data-campo=documento_id",
                encontre=json.dumps(los_botones_del_papel, ensure_ascii=False)[:400],
            ):
                print("  >> sin la lista de papeles no se puede elegir ninguno")
                return 1

            # ---------------------------------------------------------------------------------
            # 2 · La fecha, escrita ANTES de elegir el papel
            # ---------------------------------------------------------------------------------
            print(f"\n2. LA FECHA SE ESCRIBE EN SU CAMPO ({FECHA_DE_LA_EVIDENCIA}), ANTES DE ELEGIR EL PAPEL")
            # **Primero la fecha y despues el papel, y ese orden es el de la pantalla de verdad**: la
            # fecha no tiene boton propio, asi que **elegir el papel es lo que guarda las dos cosas**
            # (`maquina-declarar` lee el campo al pulsar y manda los dos juntos).
            escrita = escribir_en_la_fecha(nav, tipo, FECHA_DE_LA_EVIDENCIA)
            comprobar(
                escrita.get("valor") == FECHA_DE_LA_EVIDENCIA,
                f"la fecha se escribe en #{el_identificador_de_la_fecha(tipo)}",
                esperaba=FECHA_DE_LA_EVIDENCIA,
                encontre=repr(escrita.get("valor")),
            )

            # ---------------------------------------------------------------------------------
            # 3 · El papel, elegido en la pantalla
            # ---------------------------------------------------------------------------------
            print(f"\n3. EL PAPEL SE ELIGE EN LA PANTALLA (el {papel_id}, el que se ha subido)")
            el_mio = next(
                (boton for boton in los_botones_del_papel if boton.get("valor") == str(papel_id)), None
            )
            if not comprobar(
                el_mio is not None,
                "el papel que se ha subido sale en la lista de papeles del bloque, con su identificador",
                esperaba=f"un boton con data-valor={str(papel_id)!r}",
                encontre=json.dumps(
                    [(boton.get("valor"), boton.get("texto")) for boton in los_botones_del_papel],
                    ensure_ascii=False,
                )[:400],
            ):
                print("  >> sin su boton no se puede elegir el papel que se ha subido")
                return 1
            # **El texto del boton es el nombre del papel**: es lo que el agricultor lee antes de
            # pulsarlo, y por eso se comprueba que es el suyo y no el de otro.
            comprobar(
                el_mio.get("texto") == titulo_del_papel,
                "y su boton lleva el nombre del papel, que es lo que se lee antes de pulsarlo",
                esperaba=repr(titulo_del_papel),
                encontre=repr(el_mio.get("texto")),
            )
            comprobar(
                el_mio.get("accion") == LA_ACCION_DE_DECLARAR
                and el_mio.get("campo") == EL_CAMPO_DEL_PAPEL
                and el_mio.get("tipo") == tipo,
                "sus `data-*` son los que lee `app.js`: la accion de declarar, el campo y la obligacion",
                esperaba=(
                    f"accion={LA_ACCION_DE_DECLARAR!r} campo={EL_CAMPO_DEL_PAPEL!r} tipo={tipo!r}"
                ),
                encontre=(
                    f"accion={el_mio.get('accion')!r} campo={el_mio.get('campo')!r} "
                    f"tipo={el_mio.get('tipo')!r}"
                ),
            )
            el_selector_del_mio = "#pantalla " + el_selector_de_una_opcion(
                EL_CAMPO_DEL_PAPEL, tipo, str(papel_id)
            )
            if not comprobar(
                pulsar(nav, el_selector_del_mio),
                "el papel se pulsa en la pantalla (un clic de verdad)",
                esperaba=el_selector_del_mio,
                encontre="pulsado",
            ):
                print("  >> sin pulsar el papel no se guarda nada")
                return 1
            # Elegir el papel guarda **al elegir** (no hay boton de guardar): lo que se espera es que el
            # bloque se repinte con el papel ya elegido, que es la senal de que la puerta ha contestado.
            elegido = bool(
                nav.esperar(
                    "(() => { const b = document.querySelector(" + json.dumps(el_selector_del_mio) + ");"
                    " return Boolean(b) && b.dataset.elegido === '1'; })()",
                    segundos=25,
                )
            )
            comprobar(
                elegido,
                "y el bloque se repinta con ese papel marcado como el elegido (`data-elegido`)",
                esperaba="data-elegido=1 en su boton",
                encontre=json.dumps(
                    leer_el_bloque(nav, tipo, etiquetas["documento_de_la_aplicabilidad"]).get("botones"),
                    ensure_ascii=False,
                )[:400],
            )

            # ---------------------------------------------------------------------------------
            # 4 · Se ha guardado: la puerta y la pantalla
            # ---------------------------------------------------------------------------------
            print("\n4. SE HA GUARDADO, Y LO DICE LA PUERTA **Y** LA PANTALLA (tras recargar de verdad)")
            de_la_puerta = la_obligacion(_api(f"/api/maquinaria/{maquina_id}", token, metodo="GET") or {}, tipo)
            comprobar(
                str(de_la_puerta.get("documento_de_la_aplicabilidad_id")) == str(papel_id)
                and de_la_puerta.get("la_aplicabilidad_trae_papel") is True
                and str(de_la_puerta.get("fecha_de_la_evidencia")) == FECHA_DE_LA_EVIDENCIA,
                "la puerta devuelve el papel y la fecha en esa obligacion",
                esperaba=(
                    f"documento_de_la_aplicabilidad_id={papel_id}, la_aplicabilidad_trae_papel=True, "
                    f"fecha_de_la_evidencia={FECHA_DE_LA_EVIDENCIA!r}"
                ),
                encontre=(
                    f"documento_de_la_aplicabilidad_id={de_la_puerta.get('documento_de_la_aplicabilidad_id')!r} "
                    f"la_aplicabilidad_trae_papel={de_la_puerta.get('la_aplicabilidad_trae_papel')!r} "
                    f"fecha_de_la_evidencia={de_la_puerta.get('fecha_de_la_evidencia')!r}"
                ),
            )
            recargada = recargar(
                nav,
                f"{DIRECCION}/{la_direccion}",
                "document.getElementById(" + json.dumps(el_identificador_de_la_fecha(tipo)) + ") !== null",
            )
            comprobar(
                recargada,
                "la pagina se recarga de verdad (la marca de la visita anterior ya no esta)",
                esperaba="documento nuevo y la ficha montada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            visto = leer_el_bloque(nav, tipo, etiquetas["documento_de_la_aplicabilidad"])
            print(f"  (la ficha ensena: {json.dumps(visto, ensure_ascii=False)[:700]})")
            comprobar(
                (visto.get("papel") or "") == titulo_del_papel,
                "la pantalla ensena el NOMBRE del papel que lo demuestra",
                esperaba=repr(titulo_del_papel),
                encontre=repr(visto.get("papel")),
            )
            comprobar(
                (visto.get("fecha") or "") == FECHA_DE_LA_EVIDENCIA,
                "y la fecha del papel, en su campo",
                esperaba=FECHA_DE_LA_EVIDENCIA,
                encontre=repr(visto.get("fecha")),
            )
            el_suyo_ahora = next(
                (boton for boton in visto.get("botones") or [] if boton.get("valor") == str(papel_id)), None
            )
            comprobar(
                bool(el_suyo_ahora) and el_suyo_ahora.get("elegido") == "1",
                "y su boton sigue marcado como el elegido despues de recargar",
                esperaba="data-elegido=1 en el boton de ese papel",
                encontre=json.dumps(el_suyo_ahora, ensure_ascii=False),
            )

            # ---------------------------------------------------------------------------------
            # 5 · LA REGLA A1 (la trampa de esta entrega)
            # ---------------------------------------------------------------------------------
            print("\n5. LA REGLA A1: se declara la aplicabilidad OTRA VEZ sin tocar el campo de la fecha")
            # **Esta es la comprobacion mas importante del guion.** Al pulsar cualquier opcion se manda el
            # `PUT` entero de la obligacion —con el papel y con la fecha que haya en el campo—, y el
            # fallo que costo la ronda del #2 de semillas fue justo el de al lado: **un `null` explicito
            # borra; no mandarlo, no**. Aqui se comprueba que despues de re-declarar siguen ahi **las dos
            # cosas**, y que la pantalla las sigue ensenando (que es de donde las volveria a leer la
            # siguiente pulsacion: si el campo se quedara vacio, la fecha dejaria de viajar).
            antes_de_redeclarar = leer_el_bloque(nav, tipo, etiquetas["documento_de_la_aplicabilidad"])
            if not comprobar(
                (antes_de_redeclarar.get("fecha") or "") == FECHA_DE_LA_EVIDENCIA
                and (antes_de_redeclarar.get("papel") or "") == titulo_del_papel,
                "antes de re-declarar, el campo trae la fecha y el bloque el papel (si no, esta prueba no probaria nada)",
                esperaba=f"fecha={FECHA_DE_LA_EVIDENCIA!r} y el papel {titulo_del_papel!r}",
                encontre=(
                    f"fecha={antes_de_redeclarar.get('fecha')!r} "
                    f"papel={antes_de_redeclarar.get('papel')!r}"
                ),
            ):
                print("  >> el paso 4 no ha dejado la pantalla como debia: la regla A1 no se puede medir asi")
                return 1
            el_selector_de_la_aplicabilidad = "#pantalla " + el_selector_de_una_opcion(
                EL_CAMPO_DE_LA_APLICABILIDAD, tipo, APLICABILIDAD_PRIMERA
            )
            # La palabra del boton, leida del servidor: asi no se pulsa «un boton cualquiera».
            print(
                f"  (la respuesta que se pulsa: {APLICABILIDAD_PRIMERA!r} = "
                f"{las_aplicabilidades.get(APLICABILIDAD_PRIMERA)!r})"
            )
            if not comprobar(
                pulsar(nav, el_selector_de_la_aplicabilidad),
                "se pulsa una de las opciones de la aplicabilidad (y NO se toca el campo de la fecha)",
                esperaba=el_selector_de_la_aplicabilidad,
                encontre="pulsado",
            ):
                print("  >> sin pulsar la aplicabilidad no hay re-declaracion que medir")
                return 1
            llego = esperar_a_que_la_puerta_lo_diga(
                token, maquina_id, tipo, EL_CAMPO_DE_LA_APLICABILIDAD, APLICABILIDAD_PRIMERA
            )
            comprobar(
                llego,
                "y la re-declaracion llega a la puerta (si no, la regla A1 se mediria sobre una peticion que no se mando)",
                esperaba=f"aplicabilidad={APLICABILIDAD_PRIMERA!r} en la puerta",
                encontre=(
                    f"aplicabilidad="
                    f"{la_obligacion(_api(f'/api/maquinaria/{maquina_id}', token, metodo='GET') or {}, tipo).get('aplicabilidad')!r}"
                ),
            )
            recargada = recargar(
                nav,
                f"{DIRECCION}/{la_direccion}",
                "document.getElementById(" + json.dumps(el_identificador_de_la_fecha(tipo)) + ") !== null",
            )
            comprobar(
                recargada,
                "se recarga antes de leer (documento nuevo)",
                esperaba="documento nuevo, con la marca de la visita anterior borrada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            tras_la_redeclaracion = leer_el_bloque(nav, tipo, etiquetas["documento_de_la_aplicabilidad"])
            print(f"  (tras re-declarar: {json.dumps(tras_la_redeclaracion, ensure_ascii=False)[:700]})")
            comprobar(
                (tras_la_redeclaracion.get("fecha") or "") == FECHA_DE_LA_EVIDENCIA,
                "re-declarar la aplicabilidad NO ha borrado la fecha: sigue en su campo",
                esperaba=FECHA_DE_LA_EVIDENCIA,
                encontre=repr(tras_la_redeclaracion.get("fecha")),
            )
            comprobar(
                (tras_la_redeclaracion.get("papel") or "") == titulo_del_papel,
                "ni el papel: sigue elegido y con su nombre delante",
                esperaba=repr(titulo_del_papel),
                encontre=repr(tras_la_redeclaracion.get("papel")),
            )
            de_la_puerta = la_obligacion(_api(f"/api/maquinaria/{maquina_id}", token, metodo="GET") or {}, tipo)
            comprobar(
                str(de_la_puerta.get("documento_de_la_aplicabilidad_id")) == str(papel_id)
                and str(de_la_puerta.get("fecha_de_la_evidencia")) == FECHA_DE_LA_EVIDENCIA,
                "y la puerta dice lo mismo (el dato sigue guardado, no solo pintado)",
                esperaba=f"papel={papel_id} y fecha={FECHA_DE_LA_EVIDENCIA!r}",
                encontre=(
                    f"documento_de_la_aplicabilidad_id={de_la_puerta.get('documento_de_la_aplicabilidad_id')!r} "
                    f"fecha_de_la_evidencia={de_la_puerta.get('fecha_de_la_evidencia')!r}"
                ),
            )

            # **Y la otra mitad de la misma regla**: «lo que la peticion no manda, no se borra». Cuando el
            # campo esta vacio, `app.js` **no manda la clave** (`...(fecha_escrita ? {...} : {})`), asi que
            # el servidor tiene que dejar la fecha guardada donde estaba. Sin esta vuelta, «no mandarlo,
            # no» quedaria dicho en un comentario y no medido.
            #
            # **Que la clave no viaja se sabe por construccion, y por eso se mira el campo justo antes de
            # pulsar**: el manejador lee `document.getElementById(...).value` **en el momento del clic** y
            # arma el cuerpo con eso (no hay ningun repintado entre las dos cosas: React no vuelve a tocar
            # un campo que no controla). Lo que se comprueba aqui, con la puerta, es la otra mitad: que el
            # dato guardado **sigue** donde estaba.
            print("\n5b. LA OTRA MITAD DE A1: con el campo VACIO, la peticion no manda la fecha y la guardada se queda")
            vaciada = escribir_en_la_fecha(nav, tipo, "")
            comprobar(
                vaciada.get("valor") == "",
                "se vacia el campo de la fecha (lo que el agricultor puede hacer sin querer)",
                esperaba="el campo vacio",
                encontre=repr(vaciada.get("valor")),
            )
            el_selector_de_la_otra = "#pantalla " + el_selector_de_una_opcion(
                EL_CAMPO_DE_LA_APLICABILIDAD, tipo, APLICABILIDAD_OTRA
            )
            if not comprobar(
                pulsar(nav, el_selector_de_la_otra),
                "y se declara otra vez la aplicabilidad, ahora sin la fecha delante",
                esperaba=el_selector_de_la_otra,
                encontre="pulsado",
            ):
                print("  >> sin esa pulsacion no se puede medir la otra mitad de la regla")
                return 1
            llego = esperar_a_que_la_puerta_lo_diga(
                token, maquina_id, tipo, EL_CAMPO_DE_LA_APLICABILIDAD, APLICABILIDAD_OTRA
            )
            comprobar(
                llego,
                "y esta segunda declaracion tambien llega a la puerta",
                esperaba=f"aplicabilidad={APLICABILIDAD_OTRA!r} en la puerta",
                encontre=(
                    f"aplicabilidad="
                    f"{la_obligacion(_api(f'/api/maquinaria/{maquina_id}', token, metodo='GET') or {}, tipo).get('aplicabilidad')!r}"
                ),
            )
            if not llego:
                # **Se lee DESPUES de esperar, y solo si fallo**: antes, la peticion no estaba
                # **Y si no llega, hay que poder decir POR QUE** (14/10/2026). Este paso fallaba y el guion
                # no podia distinguir **«el clic no mando nada»** de **«mando y el servidor no lo guardo»**
                # —que es la diferencia entre arreglar la pantalla y arreglar el servidor—. Aqui se lee lo
                # que la pantalla dice (su aviso de error, si lo hay) y **si salio alguna peticion**, que es
                # el dato que faltaba: sin esto, el unico arreglo posible era adivinar.
                el_porque = nav.evaluar(
                    "(() => { const p = document.querySelector('#pantalla');"
                    " const avisos = Array.from(p ? p.querySelectorAll('.error, .error-campo, .aviso-error') : [])"
                    "   .map(e => e.innerText.trim()).filter(Boolean);"
                    " const peticiones = performance.getEntriesByType('resource')"
                    "   .map(e => e.name).filter(n => n.indexOf('obligaciones') >= 0);"
                    " return { avisos: avisos, peticiones: peticiones.slice(-3) }; })()"
                )
                print(f"  (peticiones que han salido: {json.dumps(el_porque.get('peticiones'), ensure_ascii=False)}")
                print(f"  (y errores en pantalla: {json.dumps(el_porque.get('avisos'), ensure_ascii=False)[:300]})")
                if el_porque.get("avisos"):
                    print("   ^ **la pantalla dice un ERROR**: apunta al SERVIDOR, no al clic")
                elif not el_porque.get("peticiones"):
                    print("   ^ **no ha salido ninguna peticion**: el clic no ha llegado a mandar nada")
                else:
                    print("   ^ salio peticion y no hay aviso en pantalla: mira lo que contesto")
                # registrada todavia, y el diagnostico daba una **falsa alarma en verde**.
            recargada = recargar(
                nav,
                f"{DIRECCION}/{la_direccion}",
                "document.getElementById(" + json.dumps(el_identificador_de_la_fecha(tipo)) + ") !== null",
            )
            comprobar(
                recargada,
                "se recarga antes de leer (documento nuevo)",
                esperaba="documento nuevo, con la marca de la visita anterior borrada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            sin_mandarla = leer_el_bloque(nav, tipo, etiquetas["documento_de_la_aplicabilidad"])
            print(f"  (tras declarar con el campo vacio: {json.dumps(sin_mandarla, ensure_ascii=False)[:700]})")
            comprobar(
                (sin_mandarla.get("fecha") or "") == FECHA_DE_LA_EVIDENCIA,
                "lo que la peticion NO manda no se borra: la fecha guardada sigue ahi",
                esperaba=FECHA_DE_LA_EVIDENCIA,
                encontre=repr(sin_mandarla.get("fecha")),
            )
            comprobar(
                (sin_mandarla.get("papel") or "") == titulo_del_papel,
                "y el papel tampoco se ha ido",
                esperaba=repr(titulo_del_papel),
                encontre=repr(sin_mandarla.get("papel")),
            )

            # ---------------------------------------------------------------------------------
            # 6 · El aislamiento: el papel de otra finca no vale
            # ---------------------------------------------------------------------------------
            print(f"\n6. EL AISLAMIENTO: el papel {papel_ajeno_id}, que es de otra finca, no vale")
            # El `PUT` se manda **con valores validos** (la aplicabilidad que hay ahora, leida de la puerta
            # en este momento, y un origen que existe) para que el 404 venga de **la comprobacion del
            # papel** y no de una validacion: si no, el guion daria por bueno el aislamiento por un motivo
            # que no es el suyo.
            de_la_puerta = la_obligacion(_api(f"/api/maquinaria/{maquina_id}", token, metodo="GET") or {}, tipo)
            codigo, cuerpo = api_con_codigo(
                f"/api/maquinaria/{maquina_id}/obligaciones/{tipo}",
                token,
                {
                    "aplicabilidad": str(de_la_puerta.get("aplicabilidad") or "no_se"),
                    "origen": "documento",
                    "documento_id": papel_ajeno_id,
                },
                metodo="PUT",
            )
            comprobar(
                codigo == 404,
                "la puerta contesta 404 a un papel que no es de esta explotacion",
                esperaba="404",
                encontre=f"{codigo}: {str(cuerpo)[:200]}",
            )
            # **Y no ha escrito nada**: lo dice la puerta (el papel y la fecha siguen siendo los de esta
            # finca) y lo dira la auditoria en el paso 7 (el papel ajeno no puede aparecer en el rastro).
            de_la_puerta = la_obligacion(_api(f"/api/maquinaria/{maquina_id}", token, metodo="GET") or {}, tipo)
            comprobar(
                str(de_la_puerta.get("documento_de_la_aplicabilidad_id")) == str(papel_id)
                and str(de_la_puerta.get("fecha_de_la_evidencia")) == FECHA_DE_LA_EVIDENCIA,
                "el papel ajeno no ha tocado la obligacion (lo que dice la puerta)",
                esperaba=f"papel={papel_id} y fecha={FECHA_DE_LA_EVIDENCIA!r}",
                encontre=(
                    f"documento_de_la_aplicabilidad_id={de_la_puerta.get('documento_de_la_aplicabilidad_id')!r} "
                    f"fecha_de_la_evidencia={de_la_puerta.get('fecha_de_la_evidencia')!r}"
                ),
            )
            recargada = recargar(
                nav,
                f"{DIRECCION}/{la_direccion}",
                "document.getElementById(" + json.dumps(el_identificador_de_la_fecha(tipo)) + ") !== null",
            )
            comprobar(
                recargada,
                "se recarga antes de leer (documento nuevo)",
                esperaba="documento nuevo, con la marca de la visita anterior borrada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            tras_el_ajeno = leer_el_bloque(nav, tipo, etiquetas["documento_de_la_aplicabilidad"])
            print(f"  (tras el intento con el papel ajeno: {json.dumps(tras_el_ajeno, ensure_ascii=False)[:700]})")
            comprobar(
                (tras_el_ajeno.get("papel") or "") == titulo_del_papel
                and (tras_el_ajeno.get("fecha") or "") == FECHA_DE_LA_EVIDENCIA,
                "y la pantalla sigue ensenando el papel de esta finca con su fecha",
                esperaba=f"{titulo_del_papel!r} y {FECHA_DE_LA_EVIDENCIA!r}",
                encontre=f"papel={tras_el_ajeno.get('papel')!r} fecha={tras_el_ajeno.get('fecha')!r}",
            )
    except SinNavegador as fallo:
        print(f"\n>> no se puede comprobar la pantalla en esta maquina: {fallo}")
        return 1

    # ---------------------------------------------------------------------------------------------
    # 7 · La auditoria: la correccion de esa obligacion tiene que dejar rastro
    # ---------------------------------------------------------------------------------------------
    # **La auditoria no tiene puerta de API en este proyecto**: se lee de la base, en solo lectura, como
    # hacen `comprobar_la_auditoria_de_una_anulacion.py` y `comprobar_la_compra_de_punta_a_punta.py`
    # (`select ... from auditoria where entidad = ? and entidad_id = ?`). Aqui se buscan las entradas de
    # **esta** obligacion (`entidad = "obligacion_de_maquina"`, `entidad_id =` el `id` de su fila) y, entre
    # ellas, la correccion que nombra el papel y su fecha.
    print("\n7. LA AUDITORIA: la correccion de esa obligacion nombra el papel y su fecha")
    if not LA_BASE.exists():
        raise SystemExit(
            f"no he podido averiguar la base de la auditoria: `{LA_BASE}` no existe. Se le pasa como "
            "segundo argumento (`python scripts/verificar_el_recorrido_de_la_aplicabilidad.py <direccion> "
            "<ruta-de-la-base>`); el servidor la deja en `backend/cuedigital.db` cuando corre con "
            "`sqlite:///./cuedigital.db` desde `backend/` (mira `CUEDIGITAL_DATABASE_URL`)"
        )
    # **La ruta, en la forma del URI de SQLite** (`F:/...`, con barras normales): es la que SQLite
    # entiende en Windows, y ademas se pide `mode=ro` para no escribir ni por accidente en la base.
    uri = "file:" + LA_BASE.resolve().as_posix() + "?mode=ro"
    try:
        conexion = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as fallo:
        raise SystemExit(
            f"no he podido averiguar la auditoria: no se ha podido abrir `{LA_BASE}` en solo lectura "
            f"({fallo}). ¿Es la base con la que corre el servidor?"
        )
    try:
        columnas = [fila[1] for fila in conexion.execute('PRAGMA table_info("auditoria")')]
        if not columnas:
            raise SystemExit(
                f"no he podido averiguar la auditoria: la base `{LA_BASE}` no tiene tabla `auditoria` "
                "(¿es la base con la que corre el servidor?)"
            )
        suyas: list[dict] = []
        todas_las_de_obligaciones = 0
        con_el_papel_ajeno: list[dict] = []
        for fila in conexion.execute('SELECT * FROM "auditoria" ORDER BY id'):
            valores = {columna: fila[i] for i, columna in enumerate(columnas)}
            if str(valores.get("entidad")) != "obligacion_de_maquina":
                continue
            todas_las_de_obligaciones += 1
            # El rastro del intento con el papel de otra finca: **no puede existir ninguno**. Se mira en
            # todas las obligaciones de la base y no solo en esta, porque lo que se comprueba es que el 404
            # no escribio nada en ninguna parte.
            try:
                lo_escrito = json.loads(valores.get("datos") or "{}")
            except ValueError:
                lo_escrito = {}
            if isinstance(lo_escrito, dict):
                cambio = lo_escrito.get("documento_id")
                if isinstance(cambio, list) and any(str(uno) == str(papel_ajeno_id) for uno in cambio):
                    con_el_papel_ajeno.append(valores)
            if str(valores.get("entidad_id")) == str(obligacion_id):
                suyas.append(valores)
    except sqlite3.Error as fallo:
        raise SystemExit(f"no he podido averiguar la auditoria de `{LA_BASE}`: {fallo}")
    finally:
        conexion.close()

    print(
        f"  (entradas de auditoria de obligaciones de maquina en esa base: {todas_las_de_obligaciones}; "
        f"de ESTA obligacion (fila {obligacion_id}): {len(suyas)})"
    )
    con_el_papel: list[tuple[dict, dict]] = []
    for entrada in suyas:
        try:
            escrito = json.loads(entrada.get("datos") or "{}")
        except ValueError:
            escrito = {}
        if not isinstance(escrito, dict):
            continue
        print(
            f"    · accion={entrada.get('accion')!r} "
            f"documento_id={escrito.get('documento_id')!r} "
            f"fecha_de_la_evidencia={escrito.get('fecha_de_la_evidencia')!r}"
        )
        if str(entrada.get("accion")) == "corregir":
            con_el_papel.append((entrada, escrito))

    # **Se exige, no se imprime.** Imprimir la lista de arriba no es comprobar: si el papel dejara de
    # guardarse, el renglon ensenaria `None` y el guion seguiria saliendo en verde —que es justo el fallo
    # que costo una ronda en el guion hermano de la semilla—.
    la_del_papel = [
        (entrada, escrito)
        for entrada, escrito in con_el_papel
        if isinstance(escrito.get("documento_id"), list)
        and len(escrito["documento_id"]) == 2
        and str(escrito["documento_id"][1]) == str(papel_id)
    ]
    comprobar(
        bool(la_del_papel),
        "hay una entrada de auditoria (accion «corregir») de ESTA obligacion que nombra el papel",
        esperaba=f"una entrada con `documento_id` = [algo, {papel_id}]",
        encontre=(
            f"{len(suyas)} entradas de esa obligacion; "
            + ("ninguna nombra ese papel" if not suyas else "mira la lista de arriba")
        ),
    )
    if la_del_papel:
        _, escrito = la_del_papel[-1]
        el_cambio = escrito["documento_id"]
        comprobar(
            el_cambio[0] in (None, ""),
            "y dice que ANTES no habia ningun papel: es la mitad que le faltaba al contrato",
            esperaba="sin papel antes (`None`)",
            encontre=repr(el_cambio[0]),
        )
        comprobar(
            str(el_cambio[1]) == str(papel_id),
            "y el valor que quedo es el papel que se eligio en la pantalla",
            esperaba=str(papel_id),
            encontre=repr(el_cambio[1]),
        )
        # **Y la fecha, que cambio a la vez** (viaja con el papel): se exige que el mismo rastro la nombre,
        # con la fecha que se escribio en el campo.
        traia = escrito.get("fecha_de_la_evidencia")
        comprobar(
            isinstance(traia, list)
            and len(traia) == 2
            and traia[0] in (None, "")
            and traia[1] == FECHA_DE_LA_EVIDENCIA,
            "el mismo rastro nombra `fecha_de_la_evidencia` con la fecha que se escribio",
            esperaba=f"[sin fecha, {FECHA_DE_LA_EVIDENCIA!r}]",
            encontre=repr(traia),
        )
    # Y el rastro que **no** puede estar: el del intento con el papel de otra finca (paso 6).
    comprobar(
        not con_el_papel_ajeno,
        "el intento con el papel de otra finca no ha dejado ni una entrada en el rastro",
        esperaba="ninguna entrada que nombre el papel ajeno",
        encontre=(
            f"{len(con_el_papel_ajeno)} entrada(s): "
            + json.dumps(
                [{clave: entrada.get(clave) for clave in ("entidad", "entidad_id", "accion")}
                 for entrada in con_el_papel_ajeno],
                ensure_ascii=False,
            )[:300]
        ),
    )

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  - {fallo}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
