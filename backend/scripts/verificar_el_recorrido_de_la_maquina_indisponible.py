"""La maquina indisponible **no se ofrece como disponible**, andado desde la pantalla (CRM-07 #7, 14/10/2026).

POR QUE EXISTE. La revision del dueno del 14/10/2026 lo pide, en su linea 92 y dentro del punto 3 de la
cola («CRM-07 #7: averia, taller/contacto, presupuesto, gasto real y documento; ... **Maquina indisponible
no se ofrece como disponible**»). Hasta hoy, las listas donde se elige una maquina para trabajar traian
**todas** las de la finca, asi que el programa ofrecia para trabajar una maquina que el agricultor ya habia
dicho que no puede, y con ella se firmaba un trabajo diciendo que se hizo con una maquina parada.

Lo que se anadio es **una funcion**, `lasMaquinasParaElegir(tabla)` (`web/react/pantallas/maquinaria.js`),
que quita **solo** las de `no_disponible` y deja las de `no_se` —`app/maquinaria.py` lo tiene escrito:
«una maquina de la que nadie ha dicho nada **no esta "disponible", esta "sin decir"**»—, y que `web/app.js`
usa en las **dos** listas donde se elige una maquina para trabajar: el formulario de un trabajo
(`cargarElVocabularioDeLosTrabajos`) y el reparto de un gasto (`cargarLasMaquinasSiHacenFalta`).

**Y una funcion tiene su prueba unitaria; la pantalla, no.** Lo que se anda aqui es el camino del
agricultor: montar la finca, apuntar dos maquinas por la puerta —una `no_disponible` y otra `no_se`—,
abrir el formulario de un trabajo y **leer las opciones del desplegable**, que es lo que el agricultor tiene
delante. Llamar a la funcion y ver que devuelve nueve y no diez no probaria que el desplegable las pinta:
*mirar la puerta no acredita la pantalla*.

QUE COMPRUEBA, PASO A PASO
--------------------------
  0. **El caso, montado por las puertas de verdad**: dos maquinas de la finca que crea `preparar`, dadas de
     alta con `POST /api/maquinaria`, y la indisponible **estropeada despues con su `PUT`**
     (`PUT /api/maquinaria/<id>`), que es como se cambia la disponibilidad de una maquina que ya existe y
     como pasa de verdad. Antes de preguntarle a la pantalla se comprueba **contra la puerta** que las dos
     quedaron como se cree: sin eso, un verde podria estar midiendo un caso que no es.
  1. **El desplegable del formulario de un trabajo** (`#trabajo-maquina`): se abre la agenda (`#/trabajos`),
     se pulsa «planificar» —**con un clic en la pagina**, ver `pulsar`— y se leen **sus opciones**
     (`select.options`, que es como se lee un `<select>`), no el texto de la pantalla. Se exige:
       · la `no_disponible` **NO esta** ← esto es lo que pide el informe;
       · la `no_se` **SI esta** ← y es igual de importante: quitarla convertiria «sin decir» en «no»;
       · y el desplegable es **exactamente** las maquinas que la puerta dice que no estan indisponibles.
  2. **La pantalla de la maquinaria las sigue teniendo todas** (`#/maquinaria`): esa pantalla **no usa** la
     funcion y no filtra —es donde el agricultor la ve **y la arregla**—. Y ademas, la ficha de la maquina
     indisponible (`#/maquinaria/<id>`) se abre, dice su disponibilidad con la palabra del servidor y trae
     su boton de corregir: si desapareciera de aqui, el agricultor no podria arreglar lo que el programa le
     esta escondiendo en las otras dos listas.
  3. **La otra lista**: el reparto de un gasto (`#/cuentas/<id>` → «repartir» → destino «maquina»), con la
     misma exigencia. `app.js` usa la misma funcion en las dos, asi que las dos tienen que decir lo mismo;
     comprobar solo una dejaria la otra mitad sin andar.

LO QUE NO SE HACE AQUI
----------------------
No se levanta ningun servidor y no se toca el codigo de produccion: **se habla con el que ya este
levantado** en la direccion que se le pase. El escenario lo monta `datos_representativos.preparar`, que ya
sabe hacerlo y que **crea su propia finca en cada vuelta** (por eso no se puede mirar desde fuera lo que
dejo una vuelta anterior: cada corrida tiene la suya).

Uso:  python scripts/verificar_el_recorrido_de_la_maquina_indisponible.py <direccion>

      La direccion **se pasa como primer argumento y es obligatoria**: `_api` (el de
      `capturar_la_pantalla_del_reparto.py`) **no la recibe**, la lee de la constante `DIRECCION` de **su**
      modulo, que sale de `sys.argv[1]`. Sin pasarla, este guion hablaria con el puerto por defecto y el
      sintoma seria «conexion rechazada», que parece un servidor caido y no lo es.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from capturar_la_pantalla_del_reparto import _api  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad, SinNavegador  # noqa: E402

# La consola de Windows no sabe escribir todo lo que puede salir por aqui (tildes y comillas de la
# pantalla). Se pide UTF-8 y que no reviente por un caracter raro: un guion de verificacion que muere al
# imprimir lo que ha visto no verifica nada.
if getattr(sys, "stdout", None) is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"

# ---------------------------------------------------------------------------------------------
# LAS DIRECCIONES DE LAS PANTALLAS, averiguadas en el codigo (no supuestas)
# ---------------------------------------------------------------------------------------------
# * `backend/web/react/rutas.js:88` tiene `{ clave: "trabajos", patron: ["trabajos"] }`, y
#   `backend/web/app.js:1798` dice `PantallaDeLosTrabajos: "trabajos"` en `MODULO_DE_LA_PANTALLA`, asi que
#   `apuntarLaDireccion` escribe exactamente `#/trabajos` al montar la agenda. **El formulario de un
#   trabajo NO tiene direccion propia**: esta en `PANTALLAS_SIN_DIRECCION` (`app.js:969`) porque es un
#   formulario y al recargar saldria vacio, asi que se llega a el **pulsando** su boton.
# * `rutas.js:217` → `{ clave: "maquinaria", patron: ["maquinaria"] }` (`app.js:1786`), y `rutas.js:218` →
#   `{ clave: "maquina", patron: ["maquinaria", ":id"] }` con su direccion propia (`app.js:889`): la ficha
#   de una maquina se puede enlazar y recargar.
# * `rutas.js:210` → `{ clave: "gasto", patron: ["cuentas", ":id"] }` con direccion propia
#   (`app.js:893`, `PantallaDeUnGasto: "gasto"`), que es la ficha del gasto donde vive el boton de
#   repartir.
LA_AGENDA = "#/trabajos"
LA_MAQUINARIA = "#/maquinaria"
LA_FICHA_DE_UNA_MAQUINA = "#/maquinaria/{id}"
LA_FICHA_DE_UN_GASTO = "#/cuentas/{id}"

# ---------------------------------------------------------------------------------------------
# LOS `id` Y LOS `data-*` QUE HACEN FALTA, averiguados en el codigo (no inventados)
# ---------------------------------------------------------------------------------------------
# * **El boton de planificar** lo pinta `trabajos.js:244` con `accion="trabajo-planificar"`, y `app.js:23088`
#   lo atiende llevando al formulario en modo `planificar`. Va **acotado a `#pantalla`** porque el armazon
#   (`#marco`, el menu) tiene sus propios botones y un selector suelto podria coger el de otro sitio —es lo
#   que hace el guion hermano con todos los suyos—.
# * **El desplegable de la maquina** es un `id` y no un `data-*`: lo pinta el componente `Elegir`
#   (`trabajos.js:83-98`) como `<select id="trabajo-maquina">` (`trabajos.js:483`) con una `<option>` por
#   maquina (`valor` = el `id`, `texto` = el nombre) y, delante, la opcion vacia del «Sin maquina dicha».
#   **Ese `id` es lo unico que `app.js` tiene para leerlo**: su manejador lo busca asi, palabra por palabra
#   (`equipo_id: numero("trabajo-maquina")`, `app.js:22743`).
# * **El boton de repartir** (`gastos.js:782`, `accion="gasto-repartir"`) y **el destino «maquina»**
#   (`gastos.js:261-272`, `data-campo="destino_tipo"` con `data-valor="maquina"`, que es el que dispara
#   `cargarLasMaquinasSiHacenFalta`, `app.js:21467`). Las maquinas del reparto se pintan como botones de
#   marcar: `button[data-accion="gasto-marcar"]` con `data-clave` y, dentro, el nombre de la maquina
#   (`gastos.js:283-295`; es el bloque `marcas` de `app.js:21118-21134`).
EL_BOTON_DE_PLANIFICAR = '#pantalla button[data-accion="trabajo-planificar"]'
EL_DESPLEGABLE_DE_LA_MAQUINA = "trabajo-maquina"
EL_BOTON_DE_REPARTIR = '#pantalla button[data-accion="gasto-repartir"]'
EL_DESTINO_DE_LA_MAQUINA = (
    '#pantalla button[data-accion="gasto-elegir"][data-campo="destino_tipo"][data-valor="maquina"]'
)
LA_MARCA_DE_UNA_MAQUINA = '#pantalla button[data-accion="gasto-marcar"]'
# El boton de corregir de la ficha (`maquinaria.js:619`, `accion="maquina-corregir"`): es la mitad del
# «donde el agricultor la **arregla**» de esta comprobacion.
EL_BOTON_DE_CORREGIR_UNA_MAQUINA = "maquina-corregir"

# ---------------------------------------------------------------------------------------------
# LOS TRES ESTADOS DE LA DISPONIBILIDAD, leidos del servidor (no escritos de memoria)
# ---------------------------------------------------------------------------------------------
# `app/maquinaria.py:89-93`: `DISPONIBLE`, `NO_DISPONIBLE` y `NO_SE`, y `NO_SE` es el de partida porque
# «una maquina de la que nadie ha dicho nada no esta "disponible", esta "sin decir"».
DISPONIBLE = "disponible"
NO_DISPONIBLE = "no_disponible"
NO_SE = "no_se"

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


def pulsar(nav: NavegadorDeVerdad, selector: str) -> bool:
    """Un clic **en la pagina** (`el.click()`), no por coordenadas. **Y dice de verdad si pudo.**

    **Por que, que costo una ronda**: `nav.pulsar` usa `Input.dispatchMouseEvent`, que pincha **donde el
    elemento esta dibujado**. Si el boton queda **fuera de la vista** o tapado, el clic cae al lado —o en
    nada— y el guion creia haber pulsado: el paso decia «pulsado» y **no salia ninguna peticion**, y desde
    fuera parecia un fallo del producto. La casa ya lo tenia escrito en `comprobar_el_recorrido_economico.py`
    («el boton de este bloque queda debajo de la tabla, fuera de la vista; con `.click()` directo si»).

    Se hace `scrollIntoView` antes por si acaso, y luego `click()`, que dispara el manejador de React aunque
    el elemento no se vea. Y se devuelve **si el elemento existia**: un `true` de adorno es lo que hizo que
    aquel fallo pareciera otro.
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


def abrir_la_pantalla(nav: NavegadorDeVerdad, ruta: str, esperando: str, segundos: float = 25.0) -> bool:
    """Abre una pantalla de la aplicacion por su direccion y espera a que este montada.

    **`nav.abrir` (una navegacion del navegador) y no escribir el fragmento a mano.** `app.js:5377` escucha
    `popstate` y no `hashchange`, asi que lo que hay que provocar es una navegacion de verdad. **Medido, no
    supuesto** (sonda con CDP en Edge el 15/10/2026): una navegacion en la que **solo cambia el fragmento**
    dispara `popstate` **y** `hashchange` **sin recargar el documento**, asi que el enrutador la ve y no
    falta ningun `Page.reload`. Se usa para las tres pantallas de este guion y no se abre un navegador por
    pantalla: es el mismo documento, que es como se mueve el agricultor.

    Devuelve si la pantalla llego a estar montada: **no basta con haber pedido la direccion**, porque una
    pantalla que no se monta dejaria las comprobaciones siguientes midiendo el documento de antes.
    """
    nav.abrir(f"{DIRECCION}/{ruta}", esperar=1.0)
    return bool(nav.esperar(esperando, segundos=segundos))


def leer_el_desplegable(nav: NavegadorDeVerdad, campo: str) -> dict:
    """**Las opciones del `<select>`**, que es como se lee un desplegable: `select.options`.

    Se leen `valor` y `texto` de cada `<option>`: el `valor` es el identificador de la maquina —lo que
    viaja al servidor— y el `texto` es **el nombre, que es lo que el agricultor lee**. Se piden los dos
    porque la comprobacion tiene que valer por los dos caminos: que el nombre no salga es lo que pide el
    informe, y que el identificador no salga es lo que demuestra que no viaja escondido en una opcion.

    **No se lee el texto de la pantalla**: un `innerText` de `#pantalla` encontraria el nombre en cualquier
    rincon (un aviso, la lista de al lado) y daria por bueno que la opcion esta, que es justo lo que hay
    que medir. Aqui se mira **la lista de opciones del desplegable y nada mas**.
    """
    return nav.evaluar(
        "(() => { const s = document.getElementById(" + json.dumps(campo) + ");"
        " if (!s) return { hay: false };"
        " const opciones = Array.from(s.options).map((o) => ({"
        "   valor: String(o.value === undefined || o.value === null ? '' : o.value),"
        "   texto: String(o.text || '').trim() }));"
        " return { hay: true,"
        "          etiqueta: s.tagName || '',"
        "          opciones: opciones,"
        "          vacias: opciones.filter((o) => o.valor === '').length }; })()"
    ) or {}


def leer_la_lista_de_la_maquinaria(nav: NavegadorDeVerdad) -> dict:
    """Lo que la pantalla de la maquinaria **ensena**, renglon a renglon, y solo lo que se ve.

    La misma lista se pinta **dos veces** en el mismo HTML —la tabla del ordenador (`.solo-escritorio`) y
    las tarjetas del movil (`.solo-movil`)— y el CSS ensena una u otra segun el ancho
    (`estilos.css:1885-1900`). Se filtra con `checkVisibility`, que respeta el CSS: lo que se lee es **lo
    que el agricultor tiene delante** a este tamano, no el HTML entero.
    """
    return nav.evaluar(
        "(() => { const p = document.getElementById('pantalla');"
        " if (!p) return { hay: false };"
        " const seVe = (el) => Boolean(el) && el.checkVisibility({checkVisibilityCSS: true});"
        " const filas = Array.from(p.querySelectorAll('table.tabla tbody tr'))"
        "   .filter(seVe)"
        "   .map((tr) => { const celda = tr.querySelector('td');"
        "     return { nombre: ((celda && celda.innerText) || '').trim(),"
        "              texto: (tr.innerText || '').replace(/\\s+/g, ' ').trim() }; });"
        " return { hay: true, filas: filas, texto: p.innerText || '' }; })()"
    ) or {}


def leer_la_ficha_de_una_maquina(nav: NavegadorDeVerdad) -> dict:
    """Lo que la ficha de una maquina ensena: su titulo, los botones que trae y su texto."""
    return nav.evaluar(
        "(() => { const p = document.getElementById('pantalla');"
        " if (!p) return { hay: false };"
        " const h1 = p.querySelector('h1');"
        " const botones = Array.from(p.querySelectorAll('button[data-accion]'))"
        "   .map((b) => String(b.dataset.accion || ''));"
        " return { hay: true,"
        "          titulo: ((h1 && h1.innerText) || '').trim(),"
        "          botones: botones,"
        "          texto: p.innerText || '' }; })()"
    ) or {}


def leer_el_reparto_de_un_gasto(nav: NavegadorDeVerdad) -> dict:
    """Las maquinas que el reparto de un gasto deja marcar, y que destino esta elegido.

    El bloque `marcas` (`app.js:21117-21134`) pinta **un boton por cosa**: para las maquinas, su nombre en
    `data-clave` y como texto (`app.js:20976-20980` arma `clave` y `nombre` con `maquina.texto`). Se leen
    las dos cosas, como en el desplegable, y ademas **cual de los destinos esta marcado**: sin eso, un
    fallo del clic se leería como «el reparto no ofrece esas maquinas», que seria otra cosa.
    """
    return nav.evaluar(
        "(() => { const p = document.getElementById('pantalla');"
        " if (!p) return { hay: false };"
        # **Se mira SOLO lo que se ve** (14/10/2026): el mismo HTML trae la forma de movil y la de
        # escritorio y las separa el CSS (`.solo-escritorio` / `.solo-movil`), nunca JavaScript -lo dice
        # el contrato-. Sin filtrar, **cada maquina sale DOS VECES** y la lista parece el doble de larga.
        # Se copia el filtro que ya usa `leer_la_lista_de_la_maquinaria`, que es el mismo problema.
        " const seVe = (el) => Boolean(el) && el.checkVisibility({checkVisibilityCSS: true});"
        # **Se lee UN contenedor, no todos** (14/10/2026): la pantalla de una ficha pinta **la lista** y,
        # al lado, **el panel de la fila elegida**, y a 1440 px **los dos se ven**. El formulario del
        # reparto esta, por tanto, DOS VECES -9 botones en cada sitio, con las mismas claves-, y leer
        # `#pantalla` entero devuelve 18. **No es un defecto del producto: son los dos sitios donde el
        # agricultor lo ve.** Se coge el primero que tenga botones de marcar, que es el formulario.
        # (La vez anterior agrupe por `className` y los dos contenedores se llaman `barra-acciones`: se
        # fundieron en un cubo y la cuenta parecia «18 en un padre». El error estaba en la medicion.)
        " const contenedores = Array.from(p.querySelectorAll('.barra-acciones'))"
        "   .filter((c) => c.querySelector(" + json.dumps(LA_MARCA_DE_UNA_MAQUINA) + "));"
        " const contenedor = contenedores[0] || null;"
        " const botones = (contenedor ? Array.from(contenedor.querySelectorAll("
        + json.dumps(LA_MARCA_DE_UNA_MAQUINA)
        + ")) : []).filter(seVe).map((b) => ({ clave: String(b.dataset.clave || ''),"
        "                   texto: (b.innerText || '').replace(/\\s+/g, ' ').trim() }));"
        " const destinos = Array.from(p.querySelectorAll("
        + json.dumps('#pantalla button[data-accion="gasto-elegir"][data-campo="destino_tipo"]')
        + ")).filter(seVe).map((b) => ({ valor: String(b.dataset.valor || ''),"
        "                   elegido: String(b.dataset.elegido || '') }));"
        " return { hay: true, botones: botones, destinos: destinos }; })()"
    ) or {}


# ---------------------------------------------------------------------------------------------
# Hablar con la puerta
# ---------------------------------------------------------------------------------------------


def la_tabla_de_la_maquinaria(token: str) -> list[dict]:
    """Las maquinas de la finca **como las dice la puerta** (`GET /api/maquinaria`).

    Es la verdad contra la que se mide la pantalla: la puerta manda, por cada maquina, su `id`, su
    `nombre` y su `disponibilidad` en crudo (`MaquinaSalida`, `app/schemas.py:675`), que es exactamente lo
    que lee `lasMaquinasParaElegir`.
    """
    tabla = _api("/api/maquinaria", token, metodo="GET") or {}
    return [una for una in (tabla.get("maquinas") or []) if isinstance(una, dict)]


def la_maquina_de_la_puerta(token: str, maquina_id) -> dict:
    """Una maquina de la tabla de la puerta, o `{}` si no esta."""
    for una in la_tabla_de_la_maquinaria(token):
        if str(una.get("id")) == str(maquina_id):
            return una
    return {}


def apuntar_una_maquina(token: str, nombre: str, clase: str, disponibilidad: str) -> dict:
    """Da de alta una maquina **por su puerta**, con los cuatro campos que el esquema exige.

    Son los mismos que usa `tests/test_t14_maquinaria.py` en su ayuda `crear_maquina` (su linea 46): el
    nombre, la clase, la propiedad y la disponibilidad. Al dar de alta **las tres respuestas se exigen**
    (`app/routers/maquinaria_api.py:216-236`): no nacen contestadas a proposito, porque un valor de partida
    seria una afirmacion que nadie ha hecho.
    """
    maquina = _api(
        "/api/maquinaria",
        token,
        {"nombre": nombre, "clase": clase, "propiedad": "propia", "disponibilidad": disponibilidad},
    ) or {}
    if maquina.get("id") is None:
        raise SystemExit(
            f"no he podido averiguar la maquina que se acaba de dar de alta («{nombre}»): la puerta "
            f"`POST /api/maquinaria` ha contestado sin `id`: {str(maquina)[:200]}"
        )
    return maquina


def estropear_una_maquina(token: str, maquina: dict) -> dict:
    """Le cambia la disponibilidad a `no_disponible` **con su `PUT`**, que es como se corrige una maquina.

    **No se da de alta ya rota a proposito**: lo que el informe pide es que una maquina que **ya no se
    puede contar** no se ofrezca, y ese es el camino de verdad —la maquina estaba disponible, se averio, y
    el agricultor lo apunta—. Ademas es la unica forma de comprobar que la lista que se sirve **despues**
    del cambio ya no la ofrece.

    **El `nombre` viaja en el cuerpo aunque no cambie**: `_el_nombre_hace_falta`
    (`app/routers/maquinaria_api.py:195-203`) lo exige tambien al corregir, y sin el la puerta contesta
    **422** y no se cambiaria nada. Se mandan los cuatro campos, como hace
    `tests/test_t14_maquinaria.py:1089-1102`.
    """
    corregida = _api(
        f"/api/maquinaria/{maquina['id']}",
        token,
        {
            "nombre": maquina.get("nombre"),
            "clase": maquina.get("clase"),
            "propiedad": maquina.get("propiedad"),
            "disponibilidad": NO_DISPONIBLE,
        },
        metodo="PUT",
    ) or {}
    if str(corregida.get("disponibilidad")) != NO_DISPONIBLE:
        raise SystemExit(
            "no he podido averiguar si la maquina se ha quedado indisponible: la puerta "
            f"`PUT /api/maquinaria/{maquina['id']}` ha contestado con disponibilidad "
            f"{corregida.get('disponibilidad')!r}: {str(corregida)[:200]}"
        )
    return corregida


def las_palabras_de_la_disponibilidad(token: str) -> dict:
    """Las palabras del servidor para cada estado, **leidas de `/api/interfaz`** (no escritas aqui).

    Las sirve `routers/interfaz.py:212-215` desde `textos.MAQUINARIA_DE_LA_FINCA`, y son las que la
    pantalla ensena. Asi este guion no escribe ni una etiqueta de su cosecha: si manana cambia el texto,
    sigue comprobando lo correcto.
    """
    interfaz = _api("/api/interfaz", token, metodo="GET") or {}
    palabras = {
        str(una.get("valor")): una.get("texto")
        for una in (interfaz.get("disponibilidades_de_una_maquina") or [])
        if isinstance(una, dict)
    }
    for valor in (NO_DISPONIBLE, NO_SE):
        if not palabras.get(valor):
            raise SystemExit(
                f"no he podido averiguar la palabra `disponibilidad_{valor}`: `/api/interfaz` no la trae "
                "en `disponibilidades_de_una_maquina` (lo sirve `routers/interfaz.py` desde "
                "`textos.MAQUINARIA_DE_LA_FINCA`), y sin ella no se puede comprobar que la pantalla diga "
                "lo que se cree que dice"
            )
    return palabras


def en_linea(valores) -> str:
    """Una lista, en una linea y con sus tildes: para poder leerla en el informe."""
    return json.dumps(list(valores), ensure_ascii=False)


def main() -> int:
    print("== La maquina indisponible NO se ofrece como disponible, desde la pantalla ==")
    print(f"  (direccion: {DIRECCION})")

    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    print(f"  (la sesion: {escenario.volumen.nombre}; la finca ajena: {escenario.ajena.nombre})")

    palabras = las_palabras_de_la_disponibilidad(token)
    print(
        f"  (las palabras del servidor: {NO_DISPONIBLE!r} = {palabras[NO_DISPONIBLE]!r}, "
        f"{NO_SE!r} = {palabras[NO_SE]!r})"
    )

    # ---------------------------------------------------------------------------------------------
    # 0 · El caso, montado por las puertas de verdad
    # ---------------------------------------------------------------------------------------------
    print("\n0. EL CASO, MONTADO POR LAS PUERTAS DE VERDAD (una maquina no_disponible y otra no_se)")
    # **El nombre lleva la hora Y el proceso**, como en el guion hermano: esta finca es nueva en cada
    # vuelta, pero asi una vuelta se distingue de otra en cualquier captura o en cualquier base que se mire
    # despues.
    marca = f"{int(time.time())}-{os.getpid()}"
    nombre_sin_decir = f"El remolque SIN DECIR de la prueba {marca}"
    nombre_no_disponible = f"La cosechadora NO DISPONIBLE de la prueba {marca}"

    # La que **nadie ha mirado**: se da de alta ya en `no_se`, que es su estado natural (`NO_SE` es el de
    # partida en `app/maquinaria.py:89-93`) y ademas es lo que el agricultor contesta cuando no lo sabe.
    sin_decir = apuntar_una_maquina(token, nombre_sin_decir, "remolque", NO_SE)
    # Y la que **no se puede contar**: nace disponible y se estropea con su `PUT`, que es como pasa.
    se_estropeo = apuntar_una_maquina(token, nombre_no_disponible, "cosechadora", DISPONIBLE)
    estropear_una_maquina(token, se_estropeo)

    id_sin_decir = sin_decir.get("id")
    id_no_disponible = se_estropeo.get("id")
    print(
        f"  (las dos maquinas: {id_sin_decir} «{nombre_sin_decir}» y "
        f"{id_no_disponible} «{nombre_no_disponible}»)"
    )

    # **Se comprueba contra la puerta ANTES de preguntarle a la pantalla**: si la maquina no se hubiera
    # quedado como se cree, todo lo que viniera despues mediria un caso que no es —y podria salir en verde
    # por el motivo equivocado—.
    la_de_no_se = la_maquina_de_la_puerta(token, id_sin_decir)
    la_de_no_disponible = la_maquina_de_la_puerta(token, id_no_disponible)
    if not la_de_no_se or not la_de_no_disponible:
        raise SystemExit(
            "no he podido averiguar las dos maquinas en la tabla de la puerta (`GET /api/maquinaria`): "
            f"la de `no_se` da {str(la_de_no_se)[:120]} y la de `no_disponible` da "
            f"{str(la_de_no_disponible)[:120]}. Son el caso entero, y sin ellas no se puede andar"
        )
    comprobar(
        la_de_no_se.get("disponibilidad") == NO_SE,
        "la puerta dice que la maquina de la que nadie ha dicho nada esta en `no_se`",
        esperaba=NO_SE,
        encontre=repr(la_de_no_se.get("disponibilidad")),
    )
    comprobar(
        la_de_no_disponible.get("disponibilidad") == NO_DISPONIBLE,
        "y que la estropeada se ha quedado en `no_disponible` con su correccion",
        esperaba=NO_DISPONIBLE,
        encontre=repr(la_de_no_disponible.get("disponibilidad")),
    )

    # **La verdad contra la que se mide la pantalla**: las maquinas de la finca y, de ellas, las que la
    # puerta dice que **si** se pueden ofrecer para trabajar (todas menos las indisponibles).
    las_de_la_finca = la_tabla_de_la_maquinaria(token)
    las_que_se_ofrecen = [una for una in las_de_la_finca if una.get("disponibilidad") != NO_DISPONIBLE]
    ids_que_se_ofrecen = sorted(str(una.get("id")) for una in las_que_se_ofrecen)
    nombres_que_se_ofrecen = sorted(str(una.get("nombre")) for una in las_que_se_ofrecen)
    print(
        f"  (la finca tiene {len(las_de_la_finca)} maquinas; la puerta dice que se pueden ofrecer "
        f"{len(las_que_se_ofrecen)})"
    )
    # Si la maquina de `no_se` no estuviera entre las que se ofrecen, este guion no podria comprobar lo que
    # viene a comprobar: se dice y se para, en vez de seguir con un caso que no es el suyo.
    if str(id_sin_decir) not in ids_que_se_ofrecen:
        raise SystemExit(
            "no he podido averiguar por que la maquina de `no_se` no sale entre las que se pueden "
            "ofrecer: la puerta la da como "
            f"{la_de_no_se.get('disponibilidad')!r} y `lasMaquinasParaElegir` solo quita las de "
            f"`{NO_DISPONIBLE}` (`web/react/pantallas/maquinaria.js:766-770`)"
        )

    # ---------------------------------------------------------------------------------------------
    # Del 1 al 3: el recorrido, en el navegador
    # ---------------------------------------------------------------------------------------------
    try:
        # **El navegador se abre UNA vez y todo el recorrido vive dentro del `with`**: fuera de el, `nav`
        # esta cerrado y el error es `RuntimeError: el navegador no esta abierto`. Las tres pantallas se
        # abren en el mismo documento (ver `abrir_la_pantalla`), asi que no hace falta ni abrirlo tres veces
        # ni recargar.
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            # **`medir` y no solo el tamano**: ademas de fijar el ancho **apaga la cache** del navegador
            # (`navegador_cdp.py:425-451`). El servidor sirve los ficheros de `web/` tal cual, y con la
            # cache puesta `abrir` puede estar sirviendo **el JavaScript de antes**: un verde medido sobre
            # codigo viejo es la peor clase de verde. No se quita.
            nav.medir(1440, 1000)
            # El vale se mete **en cada documento nuevo**: asi una recarga sigue dentro de la sesion.
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )

            # ---------------------------------------------------------------------------------
            # 1 · El desplegable del formulario de un trabajo
            # ---------------------------------------------------------------------------------
            print(f"\n1. EL DESPLEGABLE DONDE SE ELIGE LA MAQUINA DE UN TRABAJO ({LA_AGENDA})")
            # Se espera **al boton de planificar**, y no a «algo pintado»: ese boton solo sale cuando la
            # agenda ha recibido sus datos (`GET /api/trabajos`), asi que verlo es saber que la pantalla
            # esta montada de verdad.
            montada = abrir_la_pantalla(
                nav,
                LA_AGENDA,
                "document.querySelector(" + json.dumps(EL_BOTON_DE_PLANIFICAR) + ") !== null",
            )
            if not comprobar(
                montada,
                "la agenda abre por su direccion y trae el boton de planificar un trabajo",
                esperaba=f"{LA_AGENDA} con {EL_BOTON_DE_PLANIFICAR}",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            ):
                print("  >> sin la agenda no se puede llegar al formulario de un trabajo")
                return 1
            comprobar(
                str(nav.evaluar("location.hash") or "").startswith(LA_AGENDA),
                "y la barra de direcciones esta EN la agenda, con sus parametros (campana y finca)",
                esperaba=LA_AGENDA,
                encontre=repr(nav.evaluar("location.hash")),
            )
            # **El formulario de un trabajo no tiene direccion** (`app.js:969`): se llega pulsando.
            if not comprobar(
                pulsar(nav, EL_BOTON_DE_PLANIFICAR),
                "y el formulario se abre pulsando «planificar» (un clic en la pagina)",
                esperaba=EL_BOTON_DE_PLANIFICAR,
                encontre="pulsado",
            ):
                print("  >> sin abrir el formulario no hay desplegable que leer")
                return 1
            # **Se espera al desplegable por su `id`**, que es lo unico que `app.js` tiene para leerlo: si
            # el campo cambiara de nombre, la prueba tiene que doler aqui y no medir un `<select>` de otro
            # campo del formulario.
            if not comprobar(
                bool(
                    nav.esperar(
                        "document.getElementById("
                        + json.dumps(EL_DESPLEGABLE_DE_LA_MAQUINA)
                        + ") !== null",
                        segundos=25,
                    )
                ),
                "y trae su desplegable de maquina",
                esperaba=f"#{EL_DESPLEGABLE_DE_LA_MAQUINA} en el formulario",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            ):
                print("  >> sin el desplegable no se puede leer lo que ofrece")
                return 1

            el_desplegable = leer_el_desplegable(nav, EL_DESPLEGABLE_DE_LA_MAQUINA)
            opciones = el_desplegable.get("opciones") or []
            con_maquina = [una for una in opciones if una.get("valor")]
            print(f"  (las opciones del desplegable: {en_linea([(o.get('valor'), o.get('texto')) for o in opciones])[:700]})")
            comprobar(
                el_desplegable.get("etiqueta") == "SELECT",
                "el campo de la maquina es un `<select>` (lo pinta `Elegir`, en `trabajos.js:83-98`)",
                esperaba="<select id=trabajo-maquina>",
                encontre=repr(el_desplegable.get("etiqueta")),
            )
            if not comprobar(
                bool(con_maquina),
                "y el desplegable trae maquinas que elegir (si no, no habria nada que medir)",
                esperaba=f"al menos una opcion con valor (la opcion vacia «sin maquina» no cuenta: {el_desplegable.get('vacias')})",
                encontre=en_linea([o.get("texto") for o in opciones])[:400],
            ):
                print("  >> el desplegable esta vacio: ni el informe ni su mitad se pueden comprobar asi")
                return 1

            # **Lo que pide el informe**: la que no se puede contar NO se ofrece.
            comprobar(
                str(id_no_disponible) not in [uno.get("valor") for uno in opciones],
                "la maquina `no_disponible` NO se ofrece para el trabajo (es lo que pide el informe)",
                esperaba=f"ninguna opcion con valor {str(id_no_disponible)!r}",
                encontre=en_linea([(o.get("valor"), o.get("texto")) for o in opciones])[:400],
            )
            comprobar(
                nombre_no_disponible not in [uno.get("texto") for uno in opciones],
                "y tampoco sale por su nombre, que es lo que el agricultor leeria",
                esperaba=f"ninguna opcion que diga «{nombre_no_disponible}»",
                encontre=en_linea([o.get("texto") for o in opciones])[:400],
            )

            # **Y la otra mitad, que es la que se rompe por hacer lo obvio**: la de `no_se` SI se ofrece.
            comprobar(
                str(id_sin_decir) in [uno.get("valor") for uno in opciones],
                "la maquina de la que NO SE SABE si se puede contar SI se ofrece",
                esperaba=f"una opcion con valor {str(id_sin_decir)!r}",
                encontre=en_linea([(o.get("valor"), o.get("texto")) for o in opciones])[:400],
            )
            comprobar(
                nombre_sin_decir in [uno.get("texto") for uno in opciones],
                "y con su nombre delante: quitarla seria convertir «sin decir» en «no»",
                esperaba=f"una opcion que diga «{nombre_sin_decir}»",
                encontre=en_linea([o.get("texto") for o in opciones])[:400],
            )

            # **Y la comprobacion que cierra las dos anteriores**: el desplegable tiene que ser
            # **exactamente** las maquinas que la puerta dice que no estan indisponibles. Asi no se cuela ni
            # una de mas (una indisponible ofrecida) ni una de menos (una `no_se` escondida), y no hace
            # falta escribir a mano cuantas son.
            comprobar(
                sorted(str(uno.get("valor")) for uno in con_maquina) == ids_que_se_ofrecen,
                "y el desplegable es exactamente las maquinas que la puerta dice que no estan indisponibles",
                esperaba=en_linea(ids_que_se_ofrecen),
                encontre=en_linea(sorted(str(uno.get("valor")) for uno in con_maquina)),
            )
            comprobar(
                sorted(str(uno.get("texto")) for uno in con_maquina) == nombres_que_se_ofrecen,
                "y sus nombres son los de esas mismas maquinas (los que la puerta manda)",
                esperaba=en_linea(nombres_que_se_ofrecen),
                encontre=en_linea(sorted(str(uno.get("texto")) for uno in con_maquina)),
            )

            # ---------------------------------------------------------------------------------
            # 2 · La pantalla de la maquinaria las sigue teniendo todas
            # ---------------------------------------------------------------------------------
            print(f"\n2. LA PANTALLA DE LA MAQUINARIA LAS SIGUE TENIENDO TODAS ({LA_MAQUINARIA})")
            # **Esta pantalla no usa la funcion y no filtra** (`maquinaria.js:757-760`): es donde el
            # agricultor la ve **y la arregla**. Si aqui desapareciera, el programa le estaria escondiendo
            # una maquina que no puede arreglar desde ningun sitio —y las otras dos listas no lo dirian—.
            montada = abrir_la_pantalla(
                nav,
                LA_MAQUINARIA,
                "document.querySelectorAll('#pantalla table.tabla tbody tr').length > 0",
            )
            if not comprobar(
                montada,
                "la pantalla de la maquinaria abre por su direccion y pinta su lista",
                esperaba=f"{LA_MAQUINARIA} con una tabla de maquinas",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            ):
                print("  >> sin la lista no se puede comprobar que no filtre")
                return 1
            la_lista = leer_la_lista_de_la_maquinaria(nav)
            filas = la_lista.get("filas") or []
            nombres_en_la_lista = [str(fila.get("nombre") or "") for fila in filas]
            print(f"  (la lista ensena {len(filas)} maquinas: {en_linea(nombres_en_la_lista)[:600]})")
            comprobar(
                nombre_no_disponible in nombres_en_la_lista,
                "la maquina `no_disponible` SIGUE en la lista (esa pantalla no filtra)",
                esperaba=f"una fila que diga «{nombre_no_disponible}»",
                encontre=en_linea(nombres_en_la_lista)[:400],
            )
            comprobar(
                nombre_sin_decir in nombres_en_la_lista,
                "y la de `no_se` tambien",
                esperaba=f"una fila que diga «{nombre_sin_decir}»",
                encontre=en_linea(nombres_en_la_lista)[:400],
            )
            comprobar(
                len(nombres_en_la_lista) == len(las_de_la_finca),
                "y estan TODAS las de la finca, no solo las que se pueden ofrecer",
                esperaba=f"{len(las_de_la_finca)} maquinas (las que dice la puerta)",
                encontre=f"{len(nombres_en_la_lista)} en la lista",
            )
            su_renglon = next(
                (fila for fila in filas if str(fila.get("nombre") or "") == nombre_no_disponible), {}
            )
            comprobar(
                palabras[NO_DISPONIBLE] in str(su_renglon.get("texto") or ""),
                "y su renglon dice su disponibilidad con la palabra del servidor, no con un color",
                esperaba=repr(palabras[NO_DISPONIBLE]),
                encontre=repr(str(su_renglon.get("texto") or "")[:200]),
            )

            # **Y su ficha, que es donde se arregla.** Se comprueba que se abre y que trae su boton de
            # corregir: una maquina que se pudiera ver pero no corregir dejaria al agricultor sin salida.
            la_ruta_de_la_ficha = LA_FICHA_DE_UNA_MAQUINA.format(id=id_no_disponible)
            print(f"\n2b. Y SU FICHA SE ABRE, LO DICE Y SE PUEDE ARREGLAR ({la_ruta_de_la_ficha})")
            # **Se espera a que el `h1` diga el nombre de ESA maquina, y no a que haya un `h1`**: la lista
            # de la que se viene **tambien tiene `h1`** (el titulo de la pantalla), asi que esperar «que
            # haya un `h1`» se cumpliria al instante y lo que se leería despues seria **la lista de antes**
            # creyendo que es la ficha. Es el fallo de dar por bueno lo ya pintado, y aqui se mide: si la
            # ficha no llega a abrirse, se espera y se dice lo que hay.
            montada = abrir_la_pantalla(
                nav,
                la_ruta_de_la_ficha,
                "(() => { const h1 = document.querySelector('#pantalla h1');"
                " return Boolean(h1) && (h1.innerText || '').trim() === "
                + json.dumps(nombre_no_disponible)
                + "; })()",
            )
            if not comprobar(
                montada,
                "la ficha de la maquina indisponible abre por su direccion",
                esperaba=f"{la_ruta_de_la_ficha} montada",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            ):
                print("  >> sin su ficha no se puede comprobar que el agricultor pueda arreglarla")
                return 1
            su_ficha = leer_la_ficha_de_una_maquina(nav)
            comprobar(
                su_ficha.get("titulo") == nombre_no_disponible,
                "y dice de que maquina es",
                esperaba=repr(nombre_no_disponible),
                encontre=repr(su_ficha.get("titulo")),
            )
            comprobar(
                palabras[NO_DISPONIBLE] in str(su_ficha.get("texto") or ""),
                "y ensena que no se puede contar con ella, con la palabra del servidor",
                esperaba=repr(palabras[NO_DISPONIBLE]),
                encontre=en_linea(
                    [linea for linea in str(su_ficha.get("texto") or "").splitlines() if linea.strip()][:6]
                )[:400],
            )
            comprobar(
                EL_BOTON_DE_CORREGIR_UNA_MAQUINA in (su_ficha.get("botones") or []),
                "y trae su boton de corregir, que es donde el agricultor la arregla",
                esperaba=f"un boton con data-accion={EL_BOTON_DE_CORREGIR_UNA_MAQUINA!r}",
                encontre=en_linea(su_ficha.get("botones"))[:400],
            )

            # ---------------------------------------------------------------------------------
            # 3 · La otra lista: el reparto de un gasto
            # ---------------------------------------------------------------------------------
            # **`app.js` usa la misma funcion en las dos listas donde se elige una maquina para trabajar**
            # (el formulario de un trabajo y el reparto de un gasto). Andar solo la primera dejaria la otra
            # mitad sin comprobar, y esa mitad es la que reparte un gasto entre maquinas: si la indisponible
            # se colara ahi, el agricultor repartiria el gasoleo de una maquina parada.
            gasto_id = (escenario.gastos or [None])[0]
            if gasto_id is None:
                raise SystemExit(
                    "no he podido averiguar un gasto del escenario: `preparar()` no ha dejado ninguno en "
                    "`escenario.gastos`, y sin un gasto no se puede abrir su reparto (que es la segunda "
                    "lista donde se elige una maquina para trabajar)"
                )
            la_ruta_del_gasto = LA_FICHA_DE_UN_GASTO.format(id=gasto_id)
            print(f"\n3. LA OTRA LISTA: EL REPARTO DE UN GASTO ({la_ruta_del_gasto})")
            montada = abrir_la_pantalla(
                nav,
                la_ruta_del_gasto,
                "document.querySelector(" + json.dumps(EL_BOTON_DE_REPARTIR) + ") !== null",
            )
            if not comprobar(
                montada,
                "la ficha de un gasto abre por su direccion y trae su boton de repartir",
                esperaba=f"{la_ruta_del_gasto} con {EL_BOTON_DE_REPARTIR}",
                encontre=f"hash={nav.evaluar('location.hash')!r}",
            ):
                print("  >> sin la ficha del gasto no se puede llegar a su reparto")
                return 1
            if not comprobar(
                pulsar(nav, EL_BOTON_DE_REPARTIR),
                "y se abre el formulario de repartir",
                esperaba=EL_BOTON_DE_REPARTIR,
                encontre="pulsado",
            ):
                return 1
            # **Se espera a que el formulario este pintado antes de pulsar dentro de el**: la pantalla se
            # monta en un `ReactDOM.createRoot(...).render(...)` (`react/montar.js:123`), que **no pinta de
            # forma sincrona**, asi que pulsar el destino justo despues del clic anterior puede caer en un
            # formulario que todavia no existe —y el fallo pareceria del producto—.
            los_destinos = nav.esperar(
                "document.querySelector(" + json.dumps(EL_DESTINO_DE_LA_MAQUINA) + ") !== null",
                segundos=25,
            ) and (
                nav.evaluar(
                    "Array.from(document.querySelectorAll("
                    + json.dumps(
                        '#pantalla button[data-accion="gasto-elegir"][data-campo="destino_tipo"]'
                    )
                    + ")).map((b) => String(b.dataset.valor || ''))"
                )
                or []
            )
            if not comprobar(
                bool(los_destinos),
                "y el formulario trae sus destinos (tierra, cultivo y maquina)",
                esperaba=EL_DESTINO_DE_LA_MAQUINA,
                encontre=en_linea(los_destinos or []),
            ):
                return 1
            # **Se elige el destino «maquina»**, que es lo que dispara `cargarLasMaquinasSiHacenFalta`
            # (`app.js:21467`) —las maquinas no se descargan al arrancar— y lo que cambia la lista que se
            # puede marcar.
            if not comprobar(
                pulsar(nav, EL_DESTINO_DE_LA_MAQUINA),
                "y se elige repartirlo entre las maquinas",
                esperaba=EL_DESTINO_DE_LA_MAQUINA,
                encontre="pulsado",
            ):
                print("  >> sin elegir «maquina» la lista que se mira seria la de tierras")
                return 1
            # **Y se espera a que la lista nueva este pintada** (`ReactDOM.createRoot`, otra vez asincrono)
            # antes de leerla: leerla antes daria «el reparto no ofrece las maquinas», que es el veredicto
            # contrario al que se viene a medir.
            las_marcas = nav.esperar(
                "document.querySelectorAll(" + json.dumps(LA_MARCA_DE_UNA_MAQUINA) + ").length > 0",
                segundos=25,
            ) and (
                nav.evaluar(
                    "Array.from(document.querySelectorAll("
                    + json.dumps(LA_MARCA_DE_UNA_MAQUINA)
                    + ")).map((b) => String(b.dataset.clave || ''))"
                )
                or []
            )
            if not comprobar(
                bool(las_marcas),
                "y aparece la lista de maquinas para marcar",
                esperaba=f"botones {LA_MARCA_DE_UNA_MAQUINA}",
                encontre=en_linea(las_marcas or []),
            ):
                print("  >> sin la lista de maquinas no se puede comprobar lo que ofrece el reparto")
                return 1
            el_reparto = leer_el_reparto_de_un_gasto(nav)
            botones = el_reparto.get("botones") or []
            claves = [str(uno.get("clave")) for uno in botones]
            textos = [str(uno.get("texto")) for uno in botones]
            print(f"  (las maquinas que el reparto deja marcar: {en_linea(textos)[:600]})")
            comprobar(
                any(
                    uno.get("valor") == "maquina" and uno.get("elegido") == "1"
                    for uno in el_reparto.get("destinos") or []
                ),
                "el reparto esta puesto en «maquina» (si no, la lista de arriba seria la de tierras)",
                esperaba="el destino «maquina» marcado (data-elegido=1)",
                encontre=en_linea(el_reparto.get("destinos")),
            )
            comprobar(
                nombre_no_disponible not in claves and nombre_no_disponible not in textos,
                "la maquina `no_disponible` NO se ofrece tampoco en el reparto de un gasto",
                esperaba=f"ninguna marca que diga «{nombre_no_disponible}»",
                encontre=en_linea(textos)[:400],
            )
            comprobar(
                nombre_sin_decir in claves and nombre_sin_decir in textos,
                "y la de `no_se` SI se ofrece, con su nombre",
                esperaba=f"una marca que diga «{nombre_sin_decir}»",
                encontre=en_linea(textos)[:400],
            )
            comprobar(
                sorted(claves) == nombres_que_se_ofrecen,
                "y el reparto ofrece exactamente las mismas maquinas que el formulario del trabajo",
                esperaba=en_linea(nombres_que_se_ofrecen),
                encontre=en_linea(sorted(claves)),
            )
    except SinNavegador as fallo:
        # **Sin navegador no se puede acreditar la pantalla**, y se dice: dar por bueno lo que no se ha
        # mirado seria justo el fallo que este guion persigue. Se apunta como un fallo mas (en vez de
        # morir) para que el resumen final salga igual y diga cuantas comprobaciones se quedaron sin hacer.
        print(f"\n>> no se puede comprobar la pantalla en esta maquina: {fallo}")
        FALLOS.append(f"no se puede comprobar la pantalla en esta maquina ({fallo})")
    except RuntimeError as fallo:
        # Un `RuntimeError` de aqui es del propio navegador (una orden que ha fallado, un JavaScript que
        # ha reventado): **tambien se apunta y se sigue**, porque un rastro de Python no dice lo que se
        # esperaba ni lo que se encontro, que es lo unico que permite arreglarlo en una consulta.
        print(f"\n>> el navegador no ha podido: {fallo}")
        FALLOS.append(f"el navegador no ha podido ({fallo})")

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  - {fallo}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
