"""El recorrido de la CATEGORIA y la PROCEDENCIA de una semilla, **andado desde la pantalla** (14/10/2026).

POR QUE EXISTE. El 14/10/2026 el dueno encontro un fallo de **perdida de datos**: al corregir **solo la
variedad** de una semilla, sus dos campos nuevos (`categoria_semilla` y `procedencia`, CRM-07 #2) se
borraban. La causa estaba en dos sitios y los dos importan:

  · en el servidor, la correccion construia la fila con una lista blanca (`lo_que_hay`) en la que no
    estaban esos dos campos — ya esta arreglado: «lo que la peticion no manda, no se borra» (A1);
  · y en la pantalla, el borrador con el que se abre la ficha **para corregir** tiene que traerlos. Si no
    los trae, el desplegable ensena «No consta» aunque la fila los tenga, y como el formulario manda
    **siempre** las claves (`categoria_semilla: escrita.categoria_semilla || null`), el servidor lo lee
    como un **vacio explicito** y borra lo guardado.

**Y una suite no lo habria visto.** Las pruebas del servidor mandan el `PUT` a mano y por eso pasan; lo
que se rompia era el camino del agricultor: abrir la ficha, cambiar la variedad y pulsar GUARDAR. Eso es
lo que se anda aqui, **leyendo el texto que ensena el desplegable** y no solo el `value` ni la API:
*mirar la puerta no acredita la pantalla*, que es la leccion que esta casa ya ha pagado.

El escenario y la forma no se inventan: se piden prestados a los guiones de la casa (`preparar`, `_api`,
`NavegadorDeVerdad`), como en `capturar_la_ficha_de_una_tierra.py`. Lo unico propio es el caso.

QUE COMPRUEBA, PASO A PASO
--------------------------
  1. **El alta desde la pantalla**: la lista de semillas (`#/semillas`), su boton de anadir, el nombre, y
     **`certificada` + `comprada` elegidos en sus desplegables**, y GUARDAR LA SEMILLA.
  2. **La persistencia, recargando**: se recarga de verdad (`nav.abrir` otra vez, con una marca en
     `window` que demuestra que el documento es nuevo) y se lee **lo que ensena la ficha**: el texto
     visible de los dos desplegables tiene que ser el de `certificada` y el de `comprada`.
  3. **El fallo de la perdida de datos**: se abre la correccion, se cambia **solo** `#semilla-variedad`,
     se guarda, se recarga y se vuelve a leer la pantalla: los dos campos siguen ahi. Y se comprueba que
     la variedad **si** cambio, porque un guardado que no guarda nada dejaria esta prueba vacia.
  4. **El cambio explicito**: ahora se eligen `r2` y `propia` en los desplegables, se guarda, se recarga y
     se lee otra vez: cambiaron, con su palabra.
  5. **El valor invalido**: por la puerta, `PUT /api/semillas/<id>` con `{"categoria_semilla":
     "lo_que_sea"}` tiene que contestar **422** y **no escribir nada** (ni en la puerta ni en la
     pantalla).
  6. **La auditoria**: el cambio de esos dos campos tiene que dejar rastro. La auditoria **no tiene
     puerta de API** en este proyecto: se lee de la base, en solo lectura, como hacen
     `comprobar_la_auditoria_de_una_anulacion.py` y `comprobar_la_compra_de_punta_a_punta.py`.

LO QUE NO SE HACE AQUI
----------------------
No se levanta ningun servidor ni se toca la base del agricultor: **se habla con el que ya este
levantado** en la direccion que se le pase. Este guion no modifica nada del codigo de produccion.

Uso:  python scripts/verificar_el_recorrido_de_una_semilla.py [direccion] [ruta-de-la-base]
      (la direccion, por defecto http://127.0.0.1:8029; la base, por defecto backend/cuedigital.db,
      que es donde la deja el servidor con `sqlite:///./cuedigital.db` y el directorio de trabajo en
      `backend/`; la auditoria se lee de ahi, en solo lectura)
"""

from __future__ import annotations

import json
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
#   `{ clave: "semillas", patron: ["semillas"] }`: **dos tramos de texto fijo**, porque es una lista y
#   no una ficha (una lista no necesita identificador en la barra de direcciones).
# * `backend/web/app.js` la abre desde `ABRIR_LA_PANTALLA.semillas = () => abrirLasSemillas()`, y su
#   renglon del menu es el modulo `semillas` (`MODULO_DE_LA_PANTALLA`), asi que `apuntarLaDireccion`
#   escribe exactamente esta direccion.
#
# **LA FICHA DE UNA SEMILLA NO TIENE DIRECCION, y no es un olvido**: `PantallaDeUnaSemilla` esta en
# `PANTALLAS_SIN_DIRECCION` («un formulario que al recargar saldria vacio es peor que no tener
# direccion»). Por eso aqui se llega a ella **como llega el agricultor**: se recarga la lista y se
# pulsa la tarjeta de la semilla. Y por eso el paso 2 y el 3 recargan y vuelven a abrir la ficha: es la
# unica forma de leer lo que la pantalla ensena despues de guardar.
LA_PANTALLA_DE_LAS_SEMILLAS = "#/semillas"

# Los `id` del formulario, tal y como estan en `backend/web/react/pantallas/semillas.js`. Los lee
# `recogeLaSemilla()` en `app.js` y **no se pueden cambiar** (hay pruebas que miran la lista entera de
# `id`: si cambian, el formulario se guarda vacio sin que salte nada).
CAMPO_NOMBRE = "semilla-nombre"
CAMPO_VARIEDAD = "semilla-variedad"
CAMPO_CATEGORIA = "semilla-categoria"
CAMPO_PROCEDENCIA = "semilla-procedencia"

# Y los botones, por su `data-accion` (el manejador de clics de la aplicacion es uno solo y lee eso).
BOTON_ANADIR = '[data-accion="semilla-nueva"]'
BOTON_GUARDAR = '[data-accion="semilla-guardar"]'
BOTON_ABRIR = '[data-accion="semilla-abrir"]'

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
# Hablar con la pantalla
# ---------------------------------------------------------------------------------------------


def escribir_en_el_campo(nav: NavegadorDeVerdad, identificador: str, valor: str) -> dict:
    """Escribe en un campo de texto **por su `id`**, como lo lee `recogeLaSemilla()`."""
    return nav.evaluar(
        "(() => { const c = document.getElementById(" + json.dumps(identificador) + ");"
        " if (!c) return { hay: false };"
        " c.focus();"
        " c.value = " + json.dumps(valor) + ";"
        " c.dispatchEvent(new Event('input', { bubbles: true }));"
        " c.dispatchEvent(new Event('change', { bubbles: true }));"
        " return { hay: true, valor: c.value }; })()"
    ) or {}


def elegir_en_el_desplegable(nav: NavegadorDeVerdad, identificador: str, valor: str) -> dict:
    """Elige una opcion **por su valor** y comprueba que esa opcion existe.

    Si el valor no estuviera en el desplegable, el navegador lo dejaria en blanco **sin decir nada**, y
    el guion daria por hecho un cambio que no ha hecho. Por eso se devuelve `existe` y quien llama lo
    mira.
    """
    return nav.evaluar(
        "(() => { const c = document.getElementById(" + json.dumps(identificador) + ");"
        " if (!c) return { hay: false };"
        " const quiere = " + json.dumps(valor) + ";"
        " const existe = Array.from(c.options).some((o) => o.value === quiere);"
        " c.value = quiere;"
        " c.dispatchEvent(new Event('change', { bubbles: true }));"
        " const opcion = c.selectedIndex >= 0 && c.options ? c.options[c.selectedIndex] : null;"
        " return { hay: true, existe: existe, valor: c.value,"
        "          texto: opcion ? opcion.textContent.trim() : null }; })()"
    ) or {}


def leer_la_ficha(nav: NavegadorDeVerdad) -> dict:
    """Lo que **ensena** la ficha: el valor elegido y **el texto visible** de los dos desplegables.

    Se lee el texto y no solo el `value` porque lo que hay que comprobar es lo que ve el agricultor: un
    desplegable con `value="certificada"` y la palabra «No consta» delante estaria mintiendo, y leyendo
    solo el `value` no se veria.
    """
    return nav.evaluar(
        "(() => {"
        " const lee = (id) => { const c = document.getElementById(id);"
        "   if (!c) return { hay: false };"
        "   const opcion = c.selectedIndex >= 0 && c.options ? c.options[c.selectedIndex] : null;"
        "   return { hay: true, valor: c.value,"
        "            texto: opcion ? opcion.textContent.trim() : null,"
        "            opciones: Array.from(c.options).map((o) => o.value + ' = ' + o.textContent.trim()) }; };"
        " const valor = (id) => { const c = document.getElementById(id);"
        "   return c ? String(c.value || '') : null; };"
        " return { categoria: lee(" + json.dumps(CAMPO_CATEGORIA) + "),"
        "          procedencia: lee(" + json.dumps(CAMPO_PROCEDENCIA) + "),"
        "          variedad: valor(" + json.dumps(CAMPO_VARIEDAD) + "),"
        "          nombre: valor(" + json.dumps(CAMPO_NOMBRE) + "),"
        "          h1: ((document.querySelector('#pantalla h1') || {}).textContent || '').trim(),"
        "          texto: ((document.querySelector('#pantalla') || {}).innerText || '').slice(0, 300) };"
        "})()"
    ) or {}


def pulsar(nav: NavegadorDeVerdad, selector: str) -> bool:
    """Un clic de verdad, sin dejar que un selector que no existe tumbe el guion con una traza."""
    try:
        nav.pulsar(selector)
        return True
    except RuntimeError as fallo:
        print(f"  (no se ha podido pulsar {selector}: {fallo})")
        return False


def recargar(nav: NavegadorDeVerdad, direccion: str, esperando: str, segundos: float = 25.0) -> bool:
    """Recarga y **comprueba que de verdad se ha recargado** (la marca de la visita anterior ya no esta).

    Se esperan las dos cosas: que el documento sea nuevo y que la pantalla que se espera este montada.
    """
    nav.evaluar(f"window.{MARCA_DE_RECARGA} = 'sigue-ahi'")
    # **`Page.reload` y NO `abrir` a la misma direccion** (corregido el 14/10/2026, y el detector
    # tenia razon al protestar): este programa es un enrutador de `#`, asi que volver a pedir **la
    # misma** direccion **no crea un documento nuevo** y la marca de la visita anterior sobrevivia.
    # `Page.reload` es la recarga del navegador, que es lo que hace el agricultor con F5, y el
    # parametro `direccion` se conserva porque es el que usan las llamadas.
    nav.orden("Page.reload", {"ignoreCache": True})
    es_nueva = bool(nav.esperar(f"typeof window.{MARCA_DE_RECARGA} === 'undefined'", segundos=25))
    montada = bool(nav.esperar(esperando, segundos=segundos))
    return es_nueva and montada


def abrir_la_ficha(nav: NavegadorDeVerdad, semilla_id: int, nombre: str) -> bool:
    """Abre la correccion de esa semilla **desde la lista**, que es como se llega a ella.

    Se espera primero a que su tarjeta exista (la lista se pinta antes de que lleguen las semillas: con
    `semilla-nueva` a la vista todavia no hay ninguna tarjeta), se pulsa y se comprueba que la ficha que
    se ha abierto es la suya —el campo del nombre trae su nombre—, no la de otra.
    """
    selector = f'{BOTON_ABRIR}[data-id="{semilla_id}"]'
    if not nav.esperar(f"document.querySelector({json.dumps('#pantalla ' + selector)}) !== null", segundos=25):
        print(f"  (la tarjeta de la semilla {semilla_id} no ha llegado a la lista)")
        return False
    if not pulsar(nav, selector):
        return False
    if not nav.esperar(
        f"document.querySelector({json.dumps('#pantalla ' + BOTON_GUARDAR)}) !== null", segundos=25
    ):
        print("  (la ficha no se ha abierto: no esta su boton de guardar)")
        return False
    en_el_campo = nav.evaluar(
        "(document.getElementById(" + json.dumps(CAMPO_NOMBRE) + ") || {}).value || ''"
    )
    if str(en_el_campo or "") != nombre:
        print(f"  (la ficha que se ha abierto no es la de «{nombre}»: trae {en_el_campo!r})")
        return False
    return True


def guardar_y_esperar_la_lista(nav: NavegadorDeVerdad) -> bool:
    """Pulsa GUARDAR LA SEMILLA y espera a que la ficha se cierre (que es lo que hace al guardar bien).

    Si el servidor dice que no, `guardarLaSemilla()` **se queda en la ficha** con el aviso puesto: por eso
    lo que se espera es que el boton de guardar desaparezca, y si no desaparece se imprime lo que hay en
    pantalla para que se vea el motivo.
    """
    if not pulsar(nav, BOTON_GUARDAR):
        return False
    cerrada = bool(
        nav.esperar(f"document.querySelector({json.dumps('#pantalla ' + BOTON_GUARDAR)}) === null", segundos=25)
    )
    if not cerrada:
        print(f"  (la ficha sigue abierta; dice: {leer_la_ficha(nav).get('texto', '')!r})")
    return cerrada


def api_con_codigo(camino: str, token: str, cuerpo: dict | None = None, *, metodo: str = "POST"):
    """La misma llamada que `_api`, pero **devolviendo el codigo** en vez de morir con el.

    POR QUE HACE FALTA. `_api` (el de `capturar_la_pantalla_del_reparto.py`) levanta un `SystemExit` en
    cuanto la puerta contesta algo que no sea 2xx —que es lo correcto para los demas guiones—, y aqui el
    **422 es la respuesta que se espera**: si el guion muriera al recibirlo, no podria comprobar que la
    semilla se ha quedado como estaba, que es la mitad del caso. La peticion es la misma, con el mismo
    vale y las mismas cabeceras.
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


def main() -> int:
    print("== El recorrido de la categoria y la procedencia de una semilla, desde la pantalla ==")
    print(f"  (direccion: {DIRECCION})")
    print(f"  (la base para la auditoria: {LA_BASE})")

    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    print(f"  (la sesion: {escenario.volumen.nombre})")

    # **Las palabras que la pantalla tiene que ensenar se leen del servidor** (`/api/interfaz` trae el
    # bloque `semillas` de `textos.py`): asi este guion no escribe ni una etiqueta de su cosecha y, si
    # manana cambia el texto, sigue comprobando lo correcto.
    interfaz = _api("/api/interfaz", token, metodo="GET")
    bloque = (interfaz or {}).get("semillas") if isinstance(interfaz, dict) else None
    if not isinstance(bloque, dict):
        raise SystemExit(
            "no he podido averiguar los textos de las semillas: `/api/interfaz` no trae el bloque "
            "«semillas» (lo sirve `routers/interfaz.py` desde `textos.SEMILLAS`)"
        )
    etiquetas = {}
    for clave in (
        "categoria_semilla_certificada",
        "categoria_semilla_r2",
        "procedencia_comprada",
        "procedencia_propia",
        "guardada",
    ):
        etiquetas[clave] = bloque.get(clave)
        if not etiquetas[clave]:
            raise SystemExit(
                f"no he podido averiguar el texto `semillas.{clave}`: `/api/interfaz` no lo trae, y sin "
                "el no se puede comprobar lo que ensena el desplegable"
            )

    nombre = f"Veza de la prueba {int(time.time())}"
    nueva_variedad = "Villalobos corregida"
    semilla_id: int | None = None

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            # El vale se mete **en cada documento nuevo** (y no una vez): asi recargar sigue estando
            # dentro de la sesion, que es lo que hace falta para mirar la pantalla despues de guardar.
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )
            nav.abrir(f"{DIRECCION}/{LA_PANTALLA_DE_LAS_SEMILLAS}", esperar=3.0)
            nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)

            # ---------------------------------------------------------------------------------
            # 1 · El alta, desde la pantalla
            # ---------------------------------------------------------------------------------
            print("\n1. EL ALTA DESDE LA PANTALLA (nombre, y `certificada` + `comprada` en los desplegables)")
            la_lista = bool(
                nav.esperar(
                    f"document.querySelector({json.dumps('#pantalla ' + BOTON_ANADIR)}) !== null",
                    segundos=25,
                )
            )
            if not comprobar(
                la_lista,
                "la pantalla de las semillas abre por su direccion y tiene su boton de anadir",
                esperaba=f"{LA_PANTALLA_DE_LAS_SEMILLAS} con {BOTON_ANADIR}",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            ) or not pulsar(nav, BOTON_ANADIR):
                print("  >> sin la lista no se puede andar el recorrido")
                return 1
            la_ficha = bool(
                nav.esperar(
                    f"document.getElementById({json.dumps(CAMPO_NOMBRE)}) !== null", segundos=25
                )
            )
            su_titulo = nav.evaluar(
                "((document.querySelector('#pantalla h1') || {}).textContent || '').trim()"
            )
            if not comprobar(
                la_ficha,
                "se abre la ficha de una semilla nueva",
                esperaba=f"el campo #{CAMPO_NOMBRE}",
                encontre=f"h1={su_titulo!r}",
            ):
                print("  >> sin la ficha no se puede dar de alta nada desde la pantalla")
                return 1

            escrito = escribir_en_el_campo(nav, CAMPO_NOMBRE, nombre)
            comprobar(
                escrito.get("valor") == nombre,
                f"el nombre se escribe en #{CAMPO_NOMBRE}",
                esperaba=nombre,
                encontre=repr(escrito.get("valor")),
            )
            # **El articulo del almacen se deja como esta** (la opcion vacia, «articulo nuevo»): el
            # formulario no tiene campo de unidad, y la unidad la pone el articulo cuando se engancha a
            # uno que ya existe. Un alta a mano no necesita ni una cosa ni la otra.
            cat = elegir_en_el_desplegable(nav, CAMPO_CATEGORIA, "certificada")
            comprobar(
                bool(cat.get("existe")) and cat.get("valor") == "certificada",
                f"la categoria se elige en #{CAMPO_CATEGORIA} y el desplegable la acepta",
                esperaba="certificada (con su opcion en la lista)",
                encontre=f"existe={cat.get('existe')} valor={cat.get('valor')!r} texto={cat.get('texto')!r}",
            )
            pro = elegir_en_el_desplegable(nav, CAMPO_PROCEDENCIA, "comprada")
            comprobar(
                bool(pro.get("existe")) and pro.get("valor") == "comprada",
                f"la procedencia se elige en #{CAMPO_PROCEDENCIA} y el desplegable la acepta",
                esperaba="comprada (con su opcion en la lista)",
                encontre=f"existe={pro.get('existe')} valor={pro.get('valor')!r} texto={pro.get('texto')!r}",
            )
            guardado = guardar_y_esperar_la_lista(nav)
            comprobar(
                guardado,
                "GUARDAR LA SEMILLA cierra la ficha (el guardado ha ido bien)",
                esperaba="la ficha se cierra y vuelve la lista",
                encontre=str(leer_la_ficha(nav).get("texto", ""))[:200],
            )
            aviso = nav.evaluar("((document.querySelector('#pantalla .aviso') || {}).innerText || '')")
            comprobar(
                etiquetas["guardada"] in str(aviso or ""),
                "y la pantalla lo dice con la palabra del servidor",
                esperaba=repr(etiquetas["guardada"]),
                encontre=repr(str(aviso or "")[:120]),
            )

            # La semilla que se acaba de dar de alta, **buscada en la lista por su tarjeta**: su
            # identificador lo dice la pantalla (`data-id`), no lo supone este guion.
            en_la_lista = nav.evaluar(
                "(() => { const todas = Array.from(document.querySelectorAll("
                + json.dumps("#pantalla " + BOTON_ABRIR)
                + "));"
                " const mia = todas.find((b) => (b.innerText || '').includes(" + json.dumps(nombre) + "));"
                " return { cuantas: todas.length, encontrada: Boolean(mia),"
                "          id: mia ? mia.dataset.id : null,"
                "          nombres: todas.map((b) => (b.innerText || '').trim().slice(0, 50)) }; })()"
            ) or {}
            print(f"  (tarjetas en la lista: {en_la_lista.get('cuantas')}; la nuestra: {en_la_lista.get('id')})")
            if not comprobar(
                bool(en_la_lista.get("encontrada")) and en_la_lista.get("id") is not None,
                "la semilla recien guardada sale en la lista con su tarjeta",
                esperaba=f"una tarjeta con «{nombre}» y su data-id",
                encontre=json.dumps(en_la_lista.get("nombres"), ensure_ascii=False)[:300],
            ):
                print("  >> sin su tarjeta no se puede abrir la ficha para seguir")
                return 1
            semilla_id = int(en_la_lista["id"])

            # ---------------------------------------------------------------------------------
            # 2 · La persistencia, recargando y mirando EL DESPLEGABLE
            # ---------------------------------------------------------------------------------
            print("\n2. LA PERSISTENCIA: se recarga y se mira LO QUE ENSENA EL DESPLEGABLE")
            # Lo que dice la puerta se imprime **como informacion**, para saber de que lado esta el
            # fallo si lo hay: no es la comprobacion (la comprobacion es la pantalla).
            de_la_puerta = _api(f"/api/semillas/{semilla_id}", token, metodo="GET") or {}
            print(
                "  (la puerta dice: "
                f"categoria_semilla={de_la_puerta.get('categoria_semilla')!r} "
                f"procedencia={de_la_puerta.get('procedencia')!r})"
            )
            recargada = recargar(
                nav,
                f"{DIRECCION}/{LA_PANTALLA_DE_LAS_SEMILLAS}",
                f"document.querySelector({json.dumps('#pantalla ' + BOTON_ANADIR)}) !== null",
            )
            comprobar(
                recargada,
                "la pagina se recarga de verdad (la marca de la visita anterior ya no esta)",
                esperaba="documento nuevo y la lista montada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            if not comprobar(
                abrir_la_ficha(nav, semilla_id, nombre),
                "y la ficha de esa semilla se vuelve a abrir desde su tarjeta",
                esperaba=f"la ficha de «{nombre}»",
                encontre=str(leer_la_ficha(nav).get("texto", ""))[:200],
            ):
                print("  >> sin la ficha no se puede leer lo que ensena")
                return 1
            visto = leer_la_ficha(nav)
            print(f"  (la ficha ensena: {json.dumps(visto, ensure_ascii=False)})")
            comprobar(
                (visto.get("categoria") or {}).get("valor") == "certificada"
                and (visto.get("categoria") or {}).get("texto") == etiquetas["categoria_semilla_certificada"],
                "el desplegable de la categoria sigue en «certificada», y con su palabra delante",
                esperaba=f"valor=certificada y texto={etiquetas['categoria_semilla_certificada']!r}",
                encontre=json.dumps(visto.get("categoria"), ensure_ascii=False),
            )
            comprobar(
                (visto.get("procedencia") or {}).get("valor") == "comprada"
                and (visto.get("procedencia") or {}).get("texto") == etiquetas["procedencia_comprada"],
                "el desplegable de la procedencia sigue en «comprada», y con su palabra delante",
                esperaba=f"valor=comprada y texto={etiquetas['procedencia_comprada']!r}",
                encontre=json.dumps(visto.get("procedencia"), ensure_ascii=False),
            )

            # ---------------------------------------------------------------------------------
            # 3 · El fallo de la perdida de datos: SOLO la variedad
            # ---------------------------------------------------------------------------------
            print("\n3. EL FALLO DE LA PERDIDA DE DATOS: se corrige SOLO la variedad")
            antes = leer_la_ficha(nav)
            print(
                "  (antes de guardar, la ficha ensena: "
                f"categoria={json.dumps(antes.get('categoria'), ensure_ascii=False)} "
                f"procedencia={json.dumps(antes.get('procedencia'), ensure_ascii=False)})"
            )
            # Se toca **una sola cosa**: la variedad. Si aqui ya pone «No consta», el fallo es de la
            # ficha al abrirse (lo dice el paso 2) y este paso lo va a confirmar al guardar.
            variedad = escribir_en_el_campo(nav, CAMPO_VARIEDAD, nueva_variedad)
            comprobar(
                variedad.get("valor") == nueva_variedad,
                f"solo se cambia la variedad (#{CAMPO_VARIEDAD}); los desplegables no se tocan",
                esperaba=nueva_variedad,
                encontre=repr(variedad.get("valor")),
            )
            comprobar(
                guardar_y_esperar_la_lista(nav),
                "la correccion se guarda y la ficha se cierra",
                esperaba="la ficha se cierra y vuelve la lista",
                encontre=str(leer_la_ficha(nav).get("texto", ""))[:200],
            )
            recargada = recargar(
                nav,
                f"{DIRECCION}/{LA_PANTALLA_DE_LAS_SEMILLAS}",
                f"document.querySelector({json.dumps('#pantalla ' + BOTON_ANADIR)}) !== null",
            )
            comprobar(
                recargada,
                "se recarga antes de leer (documento nuevo)",
                esperaba="documento nuevo, con la marca de la visita anterior borrada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            if not comprobar(
                abrir_la_ficha(nav, semilla_id, nombre),
                "y se vuelve a abrir su ficha",
                esperaba=f"la ficha de «{nombre}»",
                encontre=str(leer_la_ficha(nav).get("texto", ""))[:200],
            ):
                print("  >> sin la ficha no se puede leer lo que ensena")
                return 1
            despues = leer_la_ficha(nav)
            print(f"  (despues de corregir la variedad: {json.dumps(despues, ensure_ascii=False)})")
            # **El control positivo**: la variedad SI tiene que haber cambiado. Sin esto, un guardado que
            # no guardara nada dejaria la comprobacion de abajo vacia (los dos campos «seguirian ahi»
            # porque no se habria tocado nada).
            comprobar(
                despues.get("variedad") == nueva_variedad,
                "la variedad si se ha guardado (si no, esta prueba no probaria nada)",
                esperaba=nueva_variedad,
                encontre=repr(despues.get("variedad")),
            )
            comprobar(
                (despues.get("categoria") or {}).get("valor") == "certificada"
                and (despues.get("categoria") or {}).get("texto") == etiquetas["categoria_semilla_certificada"],
                "corregir la variedad NO ha borrado la categoria: sigue en «certificada»",
                esperaba=f"valor=certificada y texto={etiquetas['categoria_semilla_certificada']!r}",
                encontre=json.dumps(despues.get("categoria"), ensure_ascii=False),
            )
            comprobar(
                (despues.get("procedencia") or {}).get("valor") == "comprada"
                and (despues.get("procedencia") or {}).get("texto") == etiquetas["procedencia_comprada"],
                "ni la procedencia: sigue en «comprada»",
                esperaba=f"valor=comprada y texto={etiquetas['procedencia_comprada']!r}",
                encontre=json.dumps(despues.get("procedencia"), ensure_ascii=False),
            )

            # ---------------------------------------------------------------------------------
            # 4 · El cambio explicito: r2 y propia
            # ---------------------------------------------------------------------------------
            print("\n4. EL CAMBIO EXPLICITO: la categoria a `r2` y la procedencia a `propia`")
            # La ficha ya esta abierta (es la que se acaba de leer en el paso 3).
            cat = elegir_en_el_desplegable(nav, CAMPO_CATEGORIA, "r2")
            comprobar(
                bool(cat.get("existe")) and cat.get("valor") == "r2"
                and cat.get("texto") == etiquetas["categoria_semilla_r2"],
                f"se elige `r2` en #{CAMPO_CATEGORIA} y el desplegable lo ensena",
                esperaba=f"valor=r2 y texto={etiquetas['categoria_semilla_r2']!r}",
                encontre=json.dumps(cat, ensure_ascii=False),
            )
            pro = elegir_en_el_desplegable(nav, CAMPO_PROCEDENCIA, "propia")
            comprobar(
                bool(pro.get("existe")) and pro.get("valor") == "propia"
                and pro.get("texto") == etiquetas["procedencia_propia"],
                f"se elige `propia` en #{CAMPO_PROCEDENCIA} y el desplegable lo ensena",
                esperaba=f"valor=propia y texto={etiquetas['procedencia_propia']!r}",
                encontre=json.dumps(pro, ensure_ascii=False),
            )
            comprobar(
                guardar_y_esperar_la_lista(nav),
                "el cambio se guarda y la ficha se cierra",
                esperaba="la ficha se cierra y vuelve la lista",
                encontre=str(leer_la_ficha(nav).get("texto", ""))[:200],
            )
            recargada = recargar(
                nav,
                f"{DIRECCION}/{LA_PANTALLA_DE_LAS_SEMILLAS}",
                f"document.querySelector({json.dumps('#pantalla ' + BOTON_ANADIR)}) !== null",
            )
            comprobar(
                recargada,
                "se recarga antes de leer (documento nuevo)",
                esperaba="documento nuevo, con la marca de la visita anterior borrada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            if not comprobar(
                abrir_la_ficha(nav, semilla_id, nombre),
                "y se vuelve a abrir su ficha",
                esperaba=f"la ficha de «{nombre}»",
                encontre=str(leer_la_ficha(nav).get("texto", ""))[:200],
            ):
                print("  >> sin la ficha no se puede leer lo que ensena")
                return 1
            cambiado = leer_la_ficha(nav)
            print(f"  (despues del cambio explicito: {json.dumps(cambiado, ensure_ascii=False)})")
            comprobar(
                (cambiado.get("categoria") or {}).get("valor") == "r2"
                and (cambiado.get("categoria") or {}).get("texto") == etiquetas["categoria_semilla_r2"],
                "la categoria ha cambiado a `r2` y la pantalla lo dice con su palabra",
                esperaba=f"valor=r2 y texto={etiquetas['categoria_semilla_r2']!r}",
                encontre=json.dumps(cambiado.get("categoria"), ensure_ascii=False),
            )
            comprobar(
                (cambiado.get("procedencia") or {}).get("valor") == "propia"
                and (cambiado.get("procedencia") or {}).get("texto") == etiquetas["procedencia_propia"],
                "y la procedencia a `propia`, tambien con su palabra",
                esperaba=f"valor=propia y texto={etiquetas['procedencia_propia']!r}",
                encontre=json.dumps(cambiado.get("procedencia"), ensure_ascii=False),
            )

            # ---------------------------------------------------------------------------------
            # 5 · El valor invalido: por la puerta, y sin escribir nada
            # ---------------------------------------------------------------------------------
            print("\n5. EL VALOR INVALIDO: `PUT /api/semillas/<id>` con una categoria que no existe")
            codigo, cuerpo = api_con_codigo(
                f"/api/semillas/{semilla_id}", token, {"categoria_semilla": "lo_que_sea"}, metodo="PUT"
            )
            comprobar(
                codigo == 422,
                "la puerta contesta 422 a una categoria que no esta en el catalogo",
                esperaba="422",
                encontre=f"{codigo}: {str(cuerpo)[:200]}",
            )
            # **Y no ha escrito nada**: lo dice la puerta y lo dice la pantalla (que es lo que ve el
            # agricultor). Las dos, porque una puerta que contesta 422 y escribe igual seria peor.
            de_la_puerta = _api(f"/api/semillas/{semilla_id}", token, metodo="GET") or {}
            comprobar(
                de_la_puerta.get("categoria_semilla") == "r2"
                and de_la_puerta.get("procedencia") == "propia",
                "el valor invalido no ha tocado la semilla (lo que dice la puerta)",
                esperaba="categoria_semilla=r2 y procedencia=propia",
                encontre=(
                    f"categoria_semilla={de_la_puerta.get('categoria_semilla')!r} "
                    f"procedencia={de_la_puerta.get('procedencia')!r}"
                ),
            )
            recargada = recargar(
                nav,
                f"{DIRECCION}/{LA_PANTALLA_DE_LAS_SEMILLAS}",
                f"document.querySelector({json.dumps('#pantalla ' + BOTON_ANADIR)}) !== null",
            )
            comprobar(
                recargada,
                "se recarga antes de leer (documento nuevo)",
                esperaba="documento nuevo, con la marca de la visita anterior borrada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            )
            if comprobar(
                abrir_la_ficha(nav, semilla_id, nombre),
                "y se vuelve a abrir su ficha",
                esperaba=f"la ficha de «{nombre}»",
                encontre=str(leer_la_ficha(nav).get("texto", ""))[:200],
            ):
                tras_el_error = leer_la_ficha(nav)
                print(f"  (tras el valor invalido: {json.dumps(tras_el_error, ensure_ascii=False)})")
                comprobar(
                    (tras_el_error.get("categoria") or {}).get("valor") == "r2"
                    and (tras_el_error.get("procedencia") or {}).get("valor") == "propia",
                    "y la pantalla sigue ensenando lo mismo (el error no ha escrito nada)",
                    esperaba="r2 y propia en los desplegables",
                    encontre=json.dumps(
                        {
                            "categoria": tras_el_error.get("categoria"),
                            "procedencia": tras_el_error.get("procedencia"),
                        },
                        ensure_ascii=False,
                    ),
                )
    except SinNavegador as fallo:
        print(f"\n>> no se puede comprobar la pantalla en esta maquina: {fallo}")
        return 1

    # ---------------------------------------------------------------------------------------------
    # 6 · La auditoria: el cambio de esos dos campos tiene que dejar rastro
    # ---------------------------------------------------------------------------------------------
    # **La auditoria no tiene puerta de API en este proyecto**: se lee de la base, en solo lectura, como
    # hacen `comprobar_la_auditoria_de_una_anulacion.py` y `comprobar_la_compra_de_punta_a_punta.py`
    # (`select ... from auditoria where entidad = ? and entidad_id = ?`). Aqui se buscan las entradas de
    # **esta** semilla y, entre ellas, la correccion que nombra los dos campos.
    print("\n6. LA AUDITORIA: el cambio de la categoria y la procedencia deja rastro")
    if semilla_id is None:
        print("  >> no hay ninguna semilla que buscar en la auditoria")
        return 1
    if not LA_BASE.exists():
        raise SystemExit(
            f"no he podido averiguar la base de la auditoria: `{LA_BASE}` no existe. Se le pasa como "
            "segundo argumento (`python scripts/verificar_el_recorrido_de_una_semilla.py <direccion> "
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
        todas_las_de_semilla = 0
        for fila in conexion.execute('SELECT * FROM "auditoria" ORDER BY id'):
            valores = {columna: fila[i] for i, columna in enumerate(columnas)}
            if str(valores.get("entidad")) != "semilla":
                continue
            todas_las_de_semilla += 1
            if str(valores.get("entidad_id")) == str(semilla_id):
                suyas.append(valores)
    except sqlite3.Error as fallo:
        raise SystemExit(f"no he podido averiguar la auditoria de `{LA_BASE}`: {fallo}")
    finally:
        conexion.close()

    print(
        f"  (entradas de auditoria de semillas en esa base: {todas_las_de_semilla}; "
        f"de ESTA semilla ({semilla_id}): {len(suyas)})"
    )
    con_los_dos: list[tuple[dict, dict]] = []
    for entrada in suyas:
        try:
            escrito = json.loads(entrada.get("datos") or "{}")
        except ValueError:
            escrito = {}
        if not isinstance(escrito, dict):
            continue
        print(
            f"    · accion={entrada.get('accion')!r} "
            f"categoria_semilla={escrito.get('categoria_semilla')!r} "
            f"procedencia={escrito.get('procedencia')!r}"
        )
        if str(entrada.get("accion")) == "corregir" and "categoria_semilla" in escrito and "procedencia" in escrito:
            con_los_dos.append((entrada, escrito))

    comprobar(
        bool(con_los_dos),
        "hay una entrada de auditoria de ESTA semilla (accion «corregir») que nombra los dos campos",
        esperaba="una entrada con `categoria_semilla` y `procedencia` en lo que cambio",
        encontre=(
            f"{len(suyas)} entradas de esa semilla; "
            + ("ninguna nombra los dos campos" if not suyas else "mira la lista de arriba")
        ),
    )
    if con_los_dos:
        entrada, escrito = con_los_dos[-1]
        # Lo que se exige es el rastro **de este cambio** (lo que quedo despues): lo que decia antes se
        # imprime tal cual, porque si el paso 3 hubiera borrado los valores, el «antes» lo diria —y eso
        # ya lo cuenta el paso 3, que es donde se mide—.
        comprobar(
            escrito.get("categoria_semilla") == ["certificada", "r2"],
            "el rastro dice que la categoria paso de `certificada` a `r2`",
            esperaba="['certificada', 'r2']",
            encontre=repr(escrito.get("categoria_semilla")),
        )
        comprobar(
            escrito.get("procedencia") == ["comprada", "propia"],
            "y que la procedencia paso de `comprada` a `propia`",
            esperaba="['comprada', 'propia']",
            encontre=repr(escrito.get("procedencia")),
        )

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  - {fallo}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
