"""**Los permisos por ROL, andados en un navegador de verdad** (18/10/2026, segunda version).

### ***Lo que estaba mal en la primera***

*La primera version abria **solo el Inicio** y comprobaba que alli no estuvieran siete botones -fusion,
borrados, notas, bajas, banco y bandeja-. **Esos botones tampoco estan en el Inicio del titular**: viven en
la ficha del contacto, en la pantalla de fusion, en el movimiento del banco y en el papel de la bandeja. Asi
que las siete comprobaciones **pasaban sin demostrar nada**.*

***Un control que pasa igual con el defecto y sin el no es un control.*** *Lo que hace falta es un **control
positivo**: que al titular **si** se le ofrezcan, **en las pantallas donde existen**. Si no aparece ni cuando
deberia, la prueba no ha mirado donde toca.*

### ***Y tres cosas mas que la primera version no distinguia***

  1. **Ayudante** -puede modificar, no ve el dinero- y **consulta** -ni una cosa ni la otra- **no son lo
     mismo**, y cada uno tiene su prueba.
  2. ***La consulta no se puede conceder por la pantalla*** -`POST /quien-entra` da siempre ayudante-, **pero
     eso no impide probarla**: se prepara el acceso **solo en la base temporal del escenario aislado** y se
     entra con el navegador de verdad.
  3. ***Un boton con `hidden` sigue en el HTML.*** *Mirar si una cadena aparece en el volcado no dice si el
     agricultor lo ve. Se mira **si es visible y si se puede enfocar**: un `hidden` no se enfoca.*

### Lo que se comprueba, en este orden

    0 · las capacidades de cada rol, por `/api/cuenta/yo`   -la fuente de la verdad-
    1 · TITULAR: las siete se ofrecen en sus pantallas     -***control positivo***- y el dinero se ve
    2 · AYUDANTE: apunta un trabajo agronomico, y no le llega el dinero
    3 · CONSULTA: no se le ofrecen las escrituras, y la API no las admite (403)
    4 · y el cambio de cuenta y de explotacion **en el mismo navegador**

Uso:
    python scripts/verificar_los_permisos_por_rol.py [direccion]

*Sin direccion **se levanta su propio servidor** -base temporal, puerto libre-, que es el unico sitio donde
se puede sembrar el acceso de consulta sin tocar la base del agricultor.*
"""

from __future__ import annotations

import json
import os
import pathlib
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

BACKEND = pathlib.Path(__file__).resolve().parents[1]
PYTHON = BACKEND.parent / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = pathlib.Path(sys.executable)

COMPROBACIONES = 0
FALLOS: list[str] = []

# ***Las siete que la revision reprodujo***, por el nombre que llevan en el HTML.
LAS_SIETE = {
    "fusion-hacer": "fusionar dos fichas",
    "fusion-deshacer": "deshacer una fusion",
    "contacto-borrar-si": "borrar un contacto (confirmado)",
    "contacto-nota": "apuntar una nota",
    "contacto-baja": "dar de baja un contacto",
    "banco-deshacer": "deshacer una conciliacion",
    "bandeja-confirmar": "confirmar un papel de la bandeja",
}


def comprobar(bien: bool, que: str, esperaba: str = "", encontre: str = "") -> bool:
    global COMPROBACIONES
    COMPROBACIONES += 1
    if bien:
        print(f"  [OK   ] {que}")
    else:
        print(f"  [FALLO] {que}")
        if esperaba or encontre:
            print(f"          esperaba : {esperaba}")
            print(f"          encontre : {str(encontre)[:400]}")
        FALLOS.append(que)
    return bien


# -----------------------------------------------------------------------------------------------------------
# Hablar con la puerta, y quedarse con el codigo
# -----------------------------------------------------------------------------------------------------------


def _llamar(
    direccion: str, camino: str, *, token: str | None = None, cuerpo: dict | None = None, metodo: str = "GET"
) -> tuple[int, object]:
    """***Devuelve el codigo y lo que contesta***: *hace falta el codigo, porque un 403 es un resultado y no
    una excepcion.*"""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    cabeceras = {"Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    peticion = urllib.request.Request(f"{direccion}{camino}", data=datos, method=metodo, headers=cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            texto = respuesta.read().decode("utf-8")
            return respuesta.status, (json.loads(texto) if texto.strip() else None)
    except urllib.error.HTTPError as fallo:
        texto = fallo.read().decode("utf-8", errors="replace")
        try:
            return fallo.code, json.loads(texto)
        except json.JSONDecodeError:
            return fallo.code, texto


def _una_cuenta_nueva(direccion: str, correo: str, clave: str, nombre: str) -> dict:
    codigo, lo_que_sea = _llamar(
        direccion,
        "/api/cuenta/registro",
        cuerpo={
            "nombre": nombre,
            "correo": correo,
            "clave": clave,
            "explotacion": {"nombre": f"La finca de {nombre}", "nif": "12345678Z"},
        },
        metodo="POST",
    )
    if codigo not in (200, 201) or not isinstance(lo_que_sea, dict):
        raise SystemExit(f"no se pudo dar de alta «{correo}»: {codigo} {lo_que_sea!r}")
    return lo_que_sea


def _las_capacidades(direccion: str, token: str) -> dict:
    codigo, datos = _llamar(direccion, "/api/cuenta/yo", token=token)
    if codigo != 200 or not isinstance(datos, dict):
        raise SystemExit(f"`/api/cuenta/yo` contesto {codigo}: {datos!r}")
    return datos


# -----------------------------------------------------------------------------------------------------------
# El estado de las acciones en la pantalla: visible Y enfocable
# -----------------------------------------------------------------------------------------------------------

# ***Una sola llamada devuelve el estado de TODAS las acciones de la pantalla.***
#
# *Y no mira el texto del volcado: mira **el elemento**. Un boton con `hidden` **sigue en el HTML** -mi version
# anterior lo daba por escondido con una busqueda de cadena, y eso no dice si el agricultor lo ve-. Aqui se
# pregunta si tiene caja, si es visible para el navegador y **si se puede enfocar**: lo que no se enfoca no se
# puede pulsar con el tabulador, que es como se usa esto sin raton.*
EL_ESTADO_DE_LAS_ACCIONES = """
(() => {
  const salida = {};
  for (const el of document.querySelectorAll('[data-accion]')) {
    const accion = el.getAttribute('data-accion');
    const caja = el.getBoundingClientRect();
    let estado = 'enfocable';
    if (el.hidden || el.disabled) estado = 'oculto';
    else if (!(el.checkVisibility
               ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})
               : (caja.width > 0 && caja.height > 0))) estado = 'no-visible';
    else {
      el.focus();
      if (document.activeElement !== el) estado = 'no-enfocable';
      if (document.activeElement === el) el.blur();
    }
    if (salida[accion] !== 'enfocable') salida[accion] = estado;
  }
  return salida;
})()
"""


def _el_estado(nav) -> dict:
    return nav.evaluar(EL_ESTADO_DE_LAS_ACCIONES) or {}


def _esperar_quieta(nav, segundos: float = 25.0, quieta: float = 1.5) -> None:
    """***Espera a que la pantalla deje de cambiar.***

    *Se anota el numero de acciones cada cuarto de segundo, y se sigue cuando lleva **un segundo y medio igual**.
    **Hace falta**: la ficha del contacto se pinta **por partes** -la ficha, luego las notas, luego los canales-,
    y preguntar antes de tiempo devuelve una pantalla a medias.*

    ***Sin esto la prueba era una carrera***, y se noto asi: *la misma pantalla daba **30** acciones al titular,
    **23** al ayudante y **22** a la consulta, y la diferencia entre 22 y 23 no es un patron de permisos -es
    tiempo-. **Llegue a creer que mi cambio habia quitado botones al ayudante; era esto.***
    """
    limite = time.time() + segundos
    anterior, desde = -1, time.time()
    while time.time() < limite:
        ahora = nav.evaluar("document.querySelectorAll('[data-accion]').length") or 0
        if ahora != anterior:
            anterior, desde = ahora, time.time()
        elif time.time() - desde >= quieta:
            return
        time.sleep(0.25)


# -----------------------------------------------------------------------------------------------------------
# Sembrar la consulta, SOLO en la base temporal
# -----------------------------------------------------------------------------------------------------------


def sembrar_la_consulta(base: pathlib.Path, usuario_id: int, explotacion_id: int) -> None:
    """***El acceso de consulta, escrito a mano en la base del escenario aislado.***

    *No se toca la base del agricultor, y no se anade ninguna puerta al programa: **la consulta no se puede
    conceder por la pantalla**, y eso no es un defecto que se arregle aqui -es una decision de producto-. Lo que
    si se puede es **comprobar como se comporta** un acceso asi, y para eso se escribe la fila donde vive: en
    `accesos_a_fincas`, con las dos capacidades en falso y su papel.*
    """
    conexion = sqlite3.connect(str(base), timeout=20)
    try:
        conexion.execute(
            "INSERT INTO accesos_a_fincas "
            "(usuario_id, explotacion_id, puede_modificar, puede_ver_lo_economico, papel, creado_en) "
            "VALUES (?, ?, 0, 0, 'consulta', datetime('now'))",
            (usuario_id, explotacion_id),
        )
        conexion.commit()
    finally:
        conexion.close()


# -----------------------------------------------------------------------------------------------------------
# Andar las pantallas
# -----------------------------------------------------------------------------------------------------------

# ***Cada pantalla, y el boton que hay que pulsar para llegar a su estado.***
#
# *`contacto-borrar-si` **no existe** en la ficha: es el boton del **dialogo de confirmacion**, y aparece cuando se
# pulsa `contacto-borrar`. **Pulsarlo solo abre el dialogo** -confirmar es el otro-, asi que es seguro.*
# ***La fusion necesita estado***: *`fusion-hacer` no esta en el reposo de la pantalla -solo `fusion-ver`-,
# porque aparece **cuando ya hay origen, destino y vista previa**. Asi que se eligen los dos en sus `<select>` y se
# pulsa «ver lo que pasa», que es **lo que hace un agricultor**.*
#
# ***Y sirve para los tres roles a la vez***: *el ayudante, que puede escribir, vera `fusion-hacer`; la consulta,
# que no, no lo vera **pero si la vista previa**. Eso es exactamente lo que hay que distinguir.*
PREPARAR_LA_FUSION = """
(() => {
  const origen = document.querySelector('#fusion-origen');
  const destino = document.querySelector('#fusion-destino');
  if (!origen || !destino) return 'sin-selects';
  const los = Array.from(origen.options).map((o) => o.value).filter((v) => v);
  if (los.length < 2) return 'hacen-falta-dos';
  origen.value = los[0];
  origen.dispatchEvent(new Event('change', { bubbles: true }));
  destino.value = los[1];
  destino.dispatchEvent(new Event('change', { bubbles: true }));
  const ver = document.querySelector('[data-accion="fusion-ver"]');
  if (!ver) return 'sin-ver';
  ver.click();
  return 'puesto';
})()
"""

PANTALLAS = [
    ("inicio", "/", None, None),
    ("contactos", "#/contactos", None, None),
    ("la ficha del contacto", "#/contactos/{contacto}", "contacto-borrar", None),
    ("fusion", "#/fusion", None, PREPARAR_LA_FUSION),
    ("bancos", "#/cuentas/bancos", None, None),
    ("el movimiento del banco", "#/cuentas/bancos/{movimiento}", None, None),
    ("la bandeja", "#/papeles/bandeja", None, None),
    ("el papel de la bandeja", "#/papeles/bandeja/{papel}", "bandeja-revisar", None),
]


def _poner_la_sesion(
    nav,
    direccion: str,
    token: str,
    *,
    esperar: str = "document.querySelector('#pantalla') !== null",
    segundos: float = 25.0,
) -> None:
    """*El vale de la cuenta, en el sitio donde la aplicacion lo lee: **es su propio mecanismo de sesion**.*

    ***Y hay que estar dentro de la aplicacion para ponerlo*** (18/10/2026): *en `about:blank` -la pagina en
    blanco del principio- el navegador contesta `SecurityError: Access is denied for this document` al tocar
    `localStorage`. Asi que primero se abre el origen de la aplicacion, despues se pone el vale y despues se
    **recarga de verdad**, que es lo que hace que la aplicacion lo lea.*
    """
    nav.abrir(f"{direccion}/", esperar=1.5)
    nav.evaluar("window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ")")
    nav.orden("Page.reload", {})
    nav.esperar(esperar, segundos=segundos)


def _recorrer(nav, direccion: str, las_que_hay: dict) -> dict:
    """***Anda las pantallas y devuelve, por accion, donde se ofrecio.***

    *`las_que_hay` lleva los ids del escenario para armar las direcciones.*
    """
    ofrecidas: dict[str, list[str]] = {}
    for nombre, patron, abre, prepara in PANTALLAS:
        camino = patron.format(**las_que_hay)
        nav.abrir(f"{direccion}/{camino}", esperar=2.0)
        nav.esperar("document.querySelector('#pantalla') && document.querySelector('#pantalla').innerText.length > 0", segundos=25)
        _esperar_quieta(nav)
        if prepara:
            como_fue = nav.evaluar(prepara)
            if como_fue != "puesto":
                print(f"        (no se pudo preparar «{nombre}»: {como_fue})")
            else:
                _esperar_quieta(nav)
        estado = _el_estado(nav)
        # *Y si esa pantalla tiene un estado al que se llega pulsando -el dialogo, la revision del papel-, se
        # pulsa **solo si esta**: al que no puede escribir no se le ofrece, y entonces no hay nada que pulsar.*
        if abre and estado.get(abre) == "enfocable":
            nav.pulsar(f'[data-accion="{abre}"]')
            _esperar_quieta(nav, segundos=10.0, quieta=0.8)
            for accion, suyo in _el_estado(nav).items():
                if suyo == "enfocable":
                    estado[accion] = "enfocable"
        for accion, suyo in estado.items():
            if suyo == "enfocable":
                ofrecidas.setdefault(accion, []).append(nombre)
        print(f"      {nombre:26} {len(estado):3} acciones · {sum(1 for v in estado.values() if v == 'enfocable'):3} enfocables")
    return ofrecidas


def _el_dinero_en_la_pantalla(nav) -> str:
    return nav.evaluar("document.querySelector('#pantalla').innerText") or ""


def andar(direccion: str, base_de_datos: pathlib.Path | None) -> int:
    print(f"== Los permisos por rol, andados en un navegador  ({direccion}) ==")
    escenario = preparar(direccion)
    el_titular = escenario.volumen
    marca = f"{int(time.time())}-{os.getpid()}"
    clave = "una-clave-larga"
    print(f"  la finca del titular: {el_titular.explotacion_id}, con {len(escenario.gastos)} gastos")

    # *Un movimiento del banco, para abrir su pantalla.*
    codigo, los_movimientos = _llamar(direccion, "/api/bancos/movimientos", token=el_titular.token)
    el_movimiento = None
    if codigo == 200 and isinstance(los_movimientos, list) and los_movimientos:
        el_movimiento = los_movimientos[0].get("id")
    elif codigo == 200 and isinstance(los_movimientos, dict):
        suyos = los_movimientos.get("movimientos") or los_movimientos.get("items") or []
        el_movimiento = suyos[0].get("id") if suyos else None
    comprobar(el_movimiento is not None, "se encuentra un movimiento del banco para su pantalla", encontre=codigo)

    las_que_hay = {
        "contacto": escenario.contactos[0] if escenario.contactos else 1,
        "movimiento": el_movimiento or 1,
        "papel": escenario.papeles[0] if escenario.papeles else 1,
    }

    # -------------------------------------------------------------------------------------------------------
    print("\n0. LAS CAPACIDADES, POR `/api/cuenta/yo`  -la fuente de la verdad-")
    el_ayudante = _una_cuenta_nueva(direccion, f"ayudante-{marca}@ejemplo.test", clave, "El ayudante")
    la_consulta = _una_cuenta_nueva(direccion, f"consulta-{marca}@ejemplo.test", clave, "La consulta")

    # *El ayudante, por la puerta que existe -la que concede AYUDANTE-.*
    codigo, _ = _llamar(
        direccion, "/api/fincas/quien-entra", token=el_titular.token,
        cuerpo={"correo": f"ayudante-{marca}@ejemplo.test"}, metodo="POST",
    )
    comprobar(codigo == 201, "el ayudante entra en la finca por la puerta que existe", encontre=codigo)

    # *La consulta, **solo en la base temporal**: no hay puerta que la conceda.*
    if base_de_datos is not None and base_de_datos.exists():
        sus_capacidades = _las_capacidades(direccion, la_consulta["token"])
        sembrar_la_consulta(
            base_de_datos, sus_capacidades["usuario_id"], el_titular.explotacion_id
        )
        comprobar(
            True,
            "***la consulta se siembra en la base TEMPORAL*** -no hay puerta que la conceda, y no se anade-",
        )
    else:
        comprobar(
            False,
            "***la consulta necesita el escenario aislado*** y no se ha podido sembrar: "
            "arranca el guion sin direccion para que levante su propia base",
        )

    # *Los tres, a trabajar en la finca del titular: el vale dice en que finca se esta.*
    los_vales = {}
    for nombre, cuenta in (("titular", {"token": el_titular.token}), ("ayudante", el_ayudante), ("consulta", la_consulta)):
        if nombre == "titular":
            los_vales[nombre] = el_titular.token
            continue
        codigo, cambio = _llamar(
            direccion, "/api/fincas/cambiar", token=cuenta["token"],
            cuerpo={"explotacion_id": el_titular.explotacion_id}, metodo="POST",
        )
        comprobar(codigo == 200, f"«{nombre}» se pone a trabajar en la finca del titular", encontre=codigo)
        los_vales[nombre] = (cambio or {}).get("token") or cuenta["token"]

    las_suyas = {nombre: _las_capacidades(direccion, vale) for nombre, vale in los_vales.items()}
    for nombre, capacidades in las_suyas.items():
        print(
            f"      {nombre:9} modificar={capacidades['puede_modificar']!s:5} "
            f"economico={capacidades['puede_ver_lo_economico']!s:5} "
            f"titular={capacidades['es_titular']!s:5} finca={capacidades['explotacion']['id']}"
        )
    comprobar(
        las_suyas["titular"]["puede_modificar"] and las_suyas["titular"]["puede_ver_lo_economico"],
        "***el titular puede modificar y ver el dinero***",
    )
    comprobar(
        las_suyas["ayudante"]["puede_modificar"] and not las_suyas["ayudante"]["puede_ver_lo_economico"],
        "***el ayudante puede modificar y NO ve el dinero***",
    )
    comprobar(
        not las_suyas["consulta"]["puede_modificar"] and not las_suyas["consulta"]["puede_ver_lo_economico"],
        "***la consulta no puede ni una cosa ni la otra***",
    )

    # -------------------------------------------------------------------------------------------------------
    print("\n1. EL TITULAR  -el CONTROL POSITIVO: donde deberian estar, estan-")
    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            _poner_la_sesion(nav, direccion, los_vales["titular"])
            print("    las pantallas del titular:")
            las_del_titular = _recorrer(nav, direccion, las_que_hay)

            # ***Y aqui esta la clave de todo: el control positivo se hace SOLO sobre lo que el titular
            # alcanza.*** *Si una accion no se le ofrece ni a el, **no se ha llegado a su estado** -la fusion
            # necesita origen y destino, el deshacer del banco necesita un movimiento conciliado, y confirmar de
            # la bandeja necesita un papel revisado-. **Declararla «no verificada» es la verdad**; contarla como
            # buena seria el error que traia la primera version, y contarla como fallo seria culpar al codigo de
            # no haber sabido llegar.*
            las_de_verdad = {a for a in LAS_SIETE if las_del_titular.get(a)}
            for accion, que_es in LAS_SIETE.items():
                donde = las_del_titular.get(accion) or []
                if donde:
                    comprobar(
                        True,
                        f"***el titular SI ve «{accion}»*** -{que_es}- en {', '.join(donde)}",
                    )
                else:
                    print(
                        f"  [SIN VERIFICAR] «{accion}» -{que_es}-: **no se ha llegado a su estado** como titular, "
                        "asi que no se puede decir nada de sus permisos"
                    )
            comprobar(
                len(las_de_verdad) >= 3,
                f"***y el control positivo alcanza {len(las_de_verdad)} de las siete***",
                esperaba="al menos tres",
                encontre=f"{sorted(las_de_verdad)}",
            )
            # ***Y la fusion se hace de verdad***, para llegar a `fusion-deshacer`: *en esta base de usar y tirar
            # se puede, y es la unica forma de que el boton de deshacer exista. Despues se deshace, que es lo que
            # hace el agricultor cuando se equivoca.*
            nav.abrir(f"{direccion}/#/fusion", esperar=2.0)
            _esperar_quieta(nav)
            nav.evaluar(preparar_la_fusion_de_nuevo := PREPARAR_LA_FUSION)
            _esperar_quieta(nav)
            if _el_estado(nav).get("fusion-hacer") == "enfocable":
                nav.pulsar('[data-accion="fusion-hacer"]')
                _esperar_quieta(nav, segundos=20.0)
                el_estado_tras_fusionar = _el_estado(nav)
                comprobar(
                    el_estado_tras_fusionar.get("fusion-deshacer") == "enfocable",
                    "***y despues de fusionar, el titular SI ve «fusion-deshacer»***",
                    encontre=str(sorted(k for k, v in el_estado_tras_fusionar.items() if v == "enfocable")),
                )
                # *Y se deshace: no se deja la finca de la prueba con una fusion hecha.*
                if el_estado_tras_fusionar.get("fusion-deshacer") == "enfocable":
                    nav.pulsar('[data-accion="fusion-deshacer"]')
                    _esperar_quieta(nav, segundos=20.0)

            # *Y el dinero.*
            nav.abrir(f"{direccion}/", esperar=2.5)
            nav.esperar("document.querySelector('#pantalla').innerText.length > 200", segundos=25)
            el_texto_del_titular = _el_dinero_en_la_pantalla(nav)
            comprobar("EUR" in el_texto_del_titular, "***y el titular SI ve el dinero en su panel***", encontre=el_texto_del_titular[:400])

            # ---------------------------------------------------------------------------------------------------
            print("\n2. EL AYUDANTE  -puede apuntar, y el dinero no le llega-")
            codigo, hecho = _llamar(
                direccion, "/api/trabajos", token=los_vales["ayudante"],
                cuerpo={
                    "campana_id": escenario.volumen.campanas[0].id,
                    "tipo": "laboreo",
                    "fecha": "2026-10-19",
                    "parcela_id": escenario.tierras[0].id,
                },
                metodo="POST",
            )
            comprobar(codigo == 201, "***el ayudante SI puede apuntar un trabajo agronomico***", encontre=f"{codigo} {str(hecho)[:200]}")

            codigo, su_panel = _llamar(direccion, "/api/panel", token=los_vales["ayudante"])
            el_crudo = json.dumps(su_panel, ensure_ascii=False)
            comprobar(
                codigo == 200 and not any(m["clave"] == "gastos" for m in (su_panel or {}).get("las_metricas", [])),
                "***y NO recibe la metrica del dinero***", encontre=el_crudo[:300],
            )
            comprobar("EUR" not in el_crudo, "***ni la unidad del dinero en la respuesta***", encontre=el_crudo[:300])

            _poner_la_sesion(nav, direccion, los_vales["ayudante"])
            print("    las pantallas del ayudante:")
            las_del_ayudante = _recorrer(nav, direccion, las_que_hay)
            # ***El ayudante PUEDE MODIFICAR***: *lo que ve el titular de las siete, **lo tiene que ver el
            # tambien**. Lo que no puede es ver el dinero -y eso se comprueba aparte-. *Mi primera version pedia
            # lo contrario y estaba mal: el ayudante escribe, y apuntar una nota o dar de baja un contacto es
            # escribir.*
            for accion in sorted(las_de_verdad):
                comprobar(
                    accion in las_del_ayudante,
                    f"***el ayudante SI ve «{accion}», porque puede escribir***",
                    esperaba=f"ofrecida (el titular la ve en {', '.join(las_del_titular.get(accion, []))})",
                    encontre=f"ofrecidas: {sorted(las_del_ayudante)}",
                )
            nav.abrir(f"{direccion}/", esperar=2.5)
            nav.esperar("document.querySelector('#pantalla').innerText.length > 200", segundos=25)
            comprobar("EUR" not in _el_dinero_en_la_pantalla(nav), "***ni lo ve en la pantalla***")

            # ---------------------------------------------------------------------------------------------------
            print("\n3. LA CONSULTA  -ni escribe ni ve el dinero-")
            if las_suyas["consulta"]["puede_modificar"] is False:
                for camino, cuerpo, que in (
                    ("/api/trabajos", {"campana_id": escenario.volumen.campanas[0].id, "tipo": "laboreo",
                                       "fecha": "2026-10-19", "parcela_id": escenario.tierras[0].id}, "apuntar un trabajo"),
                    (f"/api/contactos/{las_que_hay['contacto']}/notas", {"texto": "no deberia entrar"}, "apuntar una nota"),
                ):
                    codigo, contestado = _llamar(direccion, camino, token=los_vales["consulta"], cuerpo=cuerpo, metodo="POST")
                    comprobar(codigo == 403, f"***la consulta NO puede {que} (403)***", encontre=f"{codigo} {str(contestado)[:200]}")
                codigo, contestado = _llamar(
                    direccion, f"/api/contactos/{las_que_hay['contacto']}", token=los_vales["consulta"], metodo="DELETE"
                )
                comprobar(codigo == 403, "***ni borrar un contacto (403)***", encontre=f"{codigo} {str(contestado)[:200]}")

                _poner_la_sesion(nav, direccion, los_vales["consulta"])
                print("    las pantallas de la consulta:")
                las_de_la_consulta = _recorrer(nav, direccion, las_que_hay)
                for accion in sorted(las_de_verdad):
                    comprobar(
                        accion not in las_de_la_consulta,
                        f"***a la consulta NO se le ofrece «{accion}»***",
                        esperaba="no ofrecida",
                        encontre=f"ofrecidas: {sorted(las_de_la_consulta)}",
                    )
                # *Y ninguna escritura de las gordas, no solo las siete.*
                for accion in ("gastos-guardar", "contacto-guardar", "trabajos-guardar", "papel-nuevo"):
                    comprobar(
                        accion not in las_de_la_consulta,
                        f"***ni «{accion}», que es otra escritura***",
                        encontre=f"ofrecidas: {sorted(las_de_la_consulta)}",
                    )
                nav.abrir(f"{direccion}/", esperar=2.5)
                nav.esperar("document.querySelector('#pantalla').innerText.length > 200", segundos=25)
                comprobar("EUR" not in _el_dinero_en_la_pantalla(nav), "***y no ve el dinero en la pantalla***")

                # -----------------------------------------------------------------------------------------------
                print("\n3b. Y LAS QUE NO SE ALCANZAN EN LA PANTALLA, POR LA PUERTA")
                # *A `fusion-deshacer`, `banco-deshacer` y `bandeja-confirmar` **no se llega** sin un estado que
                # hay que construir -una fusion hecha, un movimiento conciliado, un papel revisado-. **La pantalla
                # no se ha podido probar con ellas**, y se dice. Lo que **si** queda acreditado es que **la puerta
                # las deniega**, que es donde esta la autorizacion de verdad.*
                una, otra = (escenario.contactos + [0, 0])[:2]
                LAS_QUE_SE_CIERRAN_POR_LA_PUERTA = [
                    ("POST", f"/api/contactos/{una}/fusion/{otra}", {}, "fusionar dos fichas"),
                    ("POST", f"/api/contactos/{otra}/deshacer-la-fusion", {}, "deshacer una fusion"),
                    ("POST", f"/api/bancos/movimientos/{las_que_hay['movimiento']}/desconciliar",
                     {"imputaciones": []}, "deshacer una conciliacion"),
                    ("POST", f"/api/bandeja/{las_que_hay['papel']}/confirmar", {}, "confirmar un papel"),
                ]
                for metodo, camino, cuerpo, que in LAS_QUE_SE_CIERRAN_POR_LA_PUERTA:
                    codigo, contestado = _llamar(direccion, camino, token=los_vales["consulta"], cuerpo=cuerpo, metodo=metodo)
                    comprobar(
                        codigo == 403,
                        f"***la puerta deniega «{que}» a la consulta (403)***",
                        encontre=f"{codigo} {str(contestado)[:200]}",
                    )
            else:
                comprobar(False, "***la consulta no tiene las capacidades que se esperaban***", encontre=str(las_suyas["consulta"]))

            # ---------------------------------------------------------------------------------------------------
            print("\n4. EL CAMBIO DE CUENTA Y DE EXPLOTACION, EN EL MISMO NAVEGADOR")
            # *Se vuelve al titular **en el mismo navegador**, sin cerrarlo: es el cambio de cuenta.*
            _poner_la_sesion(nav, direccion, los_vales["titular"])
            nav.abrir(f"{direccion}/", esperar=2.5)
            nav.esperar("document.querySelector('#pantalla').innerText.length > 200", segundos=25)
            comprobar("EUR" in _el_dinero_en_la_pantalla(nav), "***vuelto al titular, el dinero reaparece***", encontre=_el_dinero_en_la_pantalla(nav)[:300])

            # *Y el cambio de EXPLOTACION: el ayudante tiene dos -la suya y la del titular-.*
            codigo, suya = _llamar(direccion, "/api/cuenta/yo", token=los_vales["ayudante"])
            la_suya = (suya or {}).get("explotacion", {}).get("id") if isinstance(suya, dict) else None
            codigo, cambio = _llamar(
                direccion, "/api/fincas/cambiar", token=los_vales["ayudante"],
                cuerpo={"explotacion_id": la_suya}, metodo="POST",
            )
            comprobar(codigo == 200, "el ayudante cambia a su propia explotacion", encontre=codigo)
            vale_en_la_suya = (cambio or {}).get("token") or los_vales["ayudante"]
            codigo, yo_alli = _llamar(direccion, "/api/cuenta/yo", token=vale_en_la_suya)
            comprobar(
                isinstance(yo_alli, dict) and yo_alli.get("explotacion", {}).get("id") == la_suya,
                "***y `/api/cuenta/yo` dice que esta en la otra***",
                esperaba=str(la_suya),
                encontre=str(yo_alli)[:300],
            )
            # *En la pantalla, la finca distinta: los contactos del titular no son los suyos.*
            _poner_la_sesion(nav, direccion, vale_en_la_suya)
            nav.abrir(f"{direccion}/#/contactos", esperar=2.5)
            nav.esperar("document.querySelector('#pantalla').innerText.length > 0", segundos=20)
            nav.esperar("true", segundos=0.5)
            comprobar(
                "El que no se borra" not in _el_dinero_en_la_pantalla(nav),
                "***y en su finca no salen los contactos de la otra***",
                encontre=_el_dinero_en_la_pantalla(nav)[:300],
            )
    except RuntimeError as fallo:
        print(f"  >> el navegador no ha podido: {fallo}")
        FALLOS.append(f"el navegador no ha podido ({fallo})")

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  - {fallo}")
    return 1 if FALLOS else 0


def un_puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def con_su_propio_servidor() -> int:
    """*La base del agricultor no se toca: servidor con base temporal, que ademas es donde se siembra la consulta.*"""
    puerto = un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    temporal = tempfile.mkdtemp(prefix="cuedigital-permisos-")
    try:
        base = pathlib.Path(temporal) / "prueba.db"
        entorno = dict(os.environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        servidor = subprocess.Popen(  # noqa: S603
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
            cwd=str(BACKEND), env=entorno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            listo = False
            for _ in range(120):
                try:
                    with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                        listo = True
                        break
                except (urllib.error.URLError, OSError):
                    if servidor.poll() is not None:
                        raise SystemExit("el servidor no ha arrancado")
                    time.sleep(0.5)
            if not listo:
                raise SystemExit("el servidor no ha contestado a /api/interfaz")
            return andar(direccion, base)
        finally:
            if servidor.poll() is None:
                servidor.terminate()
                try:
                    servidor.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    servidor.kill()
                    servidor.wait(timeout=10)
    finally:
        import shutil

        time.sleep(1.0)
        shutil.rmtree(temporal, ignore_errors=True)


def main() -> int:
    if len(sys.argv) > 1:
        return andar(sys.argv[1], None)
    return con_su_propio_servidor()


if __name__ == "__main__":
    raise SystemExit(main())
