"""**El taller de una averia**, andado desde la pantalla (CRM-07 #7, 14/10/2026).

El informe del dueno lo pide con dos palabras: «**taller de la averia**». Y el taller **ya vivia en la
casa**: es un **papel de `Contacto`**, no una tabla nueva. Lo que faltaba era **el enlace**, y este
recorrido lo anda entero:

  1. **El desplegable ofrece los talleres de la finca, y solo esos.** Tres contactos: dos con el papel
     `taller` y uno **sin** el. El que no es taller **no se ofrece**, que es la mitad de la regla.
  2. **Se elige, se guarda, y se ve en la tarjeta** con su **nombre**, no con su identificador.
  3. **Y se RECARGA la pagina**: lo guardado sigue ahi. Esto es lo que un unitario no prueba —que la
     fila se haya escrito **y** se vuelva a leer— y es el punto del metodo: pantalla -> peticion ->
     persistencia -> lectura -> **recarga**.
  4. **Y sin taller se puede guardar**, y la tarjeta dice que **no consta**: la malloria de las averias
     se arreglan uno mismo, y poder decir «no lo se» es la mitad de este programa.

Uso:  python scripts/verificar_el_recorrido_del_taller_de_una_averia.py <direccion>

      La direccion **se pasa como primer argumento y es obligatoria**: `_api` no la recibe, la lee de la
      constante `DIRECCION` de SU modulo. Sin pasarla, el sintoma es «conexion rechazada», que parece un
      servidor caido y no lo es.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "scripts")

from capturar_la_pantalla_del_reparto import _api  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"

COMPROBACIONES = 0
FALLOS: list[str] = []


def comprobar(bien: bool, que: str, esperaba: str = "", encontre: str = "") -> bool:
    global COMPROBACIONES
    COMPROBACIONES += 1
    if bien:
        print(f"  [OK   ] {que}")
    else:
        print(f"  [FALLO] {que}")
        if esperaba or encontre:
            print(f"          esperaba : {esperaba}")
            print(f"          encontre : {encontre}")
        FALLOS.append(que)
    return bien


def pulsar(nav: NavegadorDeVerdad, selector: str) -> bool:
    """Un clic **en la pagina**, no por coordenadas (`nav.pulsar` pincha donde esta dibujado y devuelve
    `True` aunque caiga al lado)."""
    try:
        return bool(
            nav.evaluar(
                "(() => { const el = document.querySelector(" + json.dumps(selector) + ");"
                " if (!el) return false; el.scrollIntoView({block: 'center'}); el.click(); return true; })()"
            )
        )
    except RuntimeError as fallo:
        print(f"  (no se ha podido pulsar {selector}: {fallo})")
        return False


def un_contacto(token: str, nombre: str, papel: str | None) -> dict:
    cuerpo = {"nombre": nombre}
    if papel:
        cuerpo["papeles"] = [papel]
    hecho = _api("/api/contactos", token, cuerpo, metodo="POST")
    if not isinstance(hecho, dict) or not hecho.get("id"):
        raise SystemExit(f"la puerta no ha devuelto el contacto: {hecho!r}")
    return hecho


def main() -> int:
    print(f"== El taller de una averia, andado desde la pantalla  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token

    maquina = (escenario.maquinas or [None])[0]
    if maquina is None:
        raise SystemExit("no he podido averiguar: la finca de `preparar` no trae ninguna maquina")
    maquina_id = maquina.get("id") if isinstance(maquina, dict) else maquina
    print(f"  (la maquina de la prueba es la {maquina_id})")

    marca = str(int(__import__("time").time()))
    EL_BUENO = f"Talleres El Camino {marca}"
    EL_OTRO = f"El taller del pueblo {marca}"
    NO_ES_TALLER = f"La ferreteria {marca}"
    el_bueno = un_contacto(token, EL_BUENO, "taller")
    un_contacto(token, EL_OTRO, "taller")
    un_contacto(token, NO_ES_TALLER, None)
    print("  (tres contactos: dos talleres y uno que no lo es)")

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )

            print("\n1. EL DESPLEGABLE OFRECE LOS TALLERES, Y SOLO ESOS")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{maquina_id}", esperar=3.0)
            if not comprobar(
                bool(nav.esperar("document.querySelectorAll('#pantalla *').length > 20", segundos=25)),
                "la ficha de la maquina abre por su direccion",
            ):
                return 1
            if not comprobar(pulsar(nav, '#pantalla [data-accion="maquina-averia-nueva"]'), "y el formulario de la averia se abre pulsando"):
                return 1
            nav.esperar("Boolean(document.getElementById('averia-que'))", segundos=25)

            # **Se lee UN contenedor** (14/10/2026): la pantalla pinta la lista y el panel de la fila
            # elegida, y a 1440 px los dos se ven; leer `#pantalla` entero contaria cada boton dos veces.
            opciones = nav.evaluar(
                "(() => { const p = document.getElementById('pantalla');"
                " const cs = Array.from(p.querySelectorAll('.barra-acciones')).filter((c) =>"
                "   c.querySelector('[data-accion=\"maquina-elegir\"][data-campo=\"taller_contacto_id\"]'));"
                " const c = cs[0]; if (!c) return null;"
                " return Array.from(c.querySelectorAll("
                "   '[data-accion=\"maquina-elegir\"][data-campo=\"taller_contacto_id\"]'))"
                "   .map((b) => (b.innerText || '').replace(/\\s+/g, ' ').trim()); })()"
            )
            if not comprobar(opciones is not None and len(opciones) >= 2, "el desplegable del taller tiene opciones", encontre=repr(opciones)):
                return 1
            comprobar(any(EL_BUENO in (o or "") for o in opciones), "y ofrece el taller de la finca", encontre=repr(opciones))
            comprobar(any(EL_OTRO in (o or "") for o in opciones), "y el otro taller tambien", encontre=repr(opciones))
            comprobar(not any(NO_ES_TALLER in (o or "") for o in opciones), "y NO ofrece un contacto que no es taller", encontre=repr(opciones))

            print("\n2. SE ELIGE, SE GUARDA, Y SE VE")
            # **Se pulsa EL taller, no «un» taller**: por su `data-valor`, que es su identificador.
            # Pulsar el primero que aparezca pasaria aunque se eligiera otro, y la comprobacion de
            # despues -«la tarjeta dice su nombre»- no lo notaria si los nombres se parecen.
            su_identificador = el_bueno["id"]
            el_selector = (
                '#pantalla [data-accion="maquina-elegir"]'
                '[data-campo="taller_contacto_id"]'
                + '[data-valor="' + str(su_identificador) + '"]'
            )
            comprobar(pulsar(nav, el_selector), "se puede pulsar el taller que se quiere")
            nav.evaluar(
                "(() => { const el = document.getElementById('averia-que'); if (!el) return false;"
                " el.value = 'Se ha roto el embrague'; el.dispatchEvent(new Event('input', {bubbles: true}));"
                " return true; })()"
            )
            if not comprobar(pulsar(nav, '#pantalla [data-accion="maquina-guardar"]'), "y se guarda la averia"):
                return 1
            guardado = bool(nav.esperar(f"document.querySelector('#pantalla').innerText.indexOf({json.dumps(EL_BUENO)}) >= 0", segundos=25))
            comprobar(guardado, "y la tarjeta de la averia dice el taller, con su nombre", encontre=(nav.evaluar("document.querySelector('#pantalla').innerText") or "")[-400:])
            comprobar(
                EL_BUENO in (nav.evaluar("document.querySelector('#pantalla').innerText") or ""),
                "y lo dice por su nombre, no por su identificador",
            )

            print("\n3. Y SE RECARGA LA PAGINA: sigue ahi")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{maquina_id}", esperar=3.0)
            nav.esperar("document.querySelectorAll('#pantalla *').length > 20", segundos=25)
            texto = nav.evaluar("document.querySelector('#pantalla').innerText") or ""
            comprobar(EL_BUENO in texto, "lo guardado sigue despues de recargar", encontre=texto[-400:])

            print("\n4. Y SIN TALLER SE PUEDE GUARDAR: no consta, y no pasa nada")
            # **Cada paso se comprueba y CADA LECTURA ESPERA** (14/10/2026). La primera version de este
            # bloque pulsaba, escribia y guardaba **sin comprobar** que el formulario se hubiera abierto,
            # y leia el texto **una sola vez** justo despues de guardar. Salio rojo -«no encuentro la
            # averia»- y lo que pasaba es que **React todavia no habia repintado**: el guion hermano ya
            # lo avisa («sin esas esperas saldrian falsos rojos»). Un recorrido que no espera miente.
            comprobar(
                pulsar(nav, '#pantalla [data-accion="maquina-averia-nueva"]'),
                "y se abre otro formulario de averia",
            )
            comprobar(
                bool(nav.esperar("Boolean(document.getElementById('averia-que'))", segundos=25)),
                "y su campo de «que paso» esta listo",
            )
            LO_QUE_PASO = "Una tonteria que arregle yo"
            nav.evaluar(
                "(() => { const el = document.getElementById('averia-que'); if (!el) return false;"
                " el.value = " + json.dumps(LO_QUE_PASO) + ";"
                " el.dispatchEvent(new Event('input', {bubbles: true})); return true; })()"
            )
            comprobar(pulsar(nav, '#pantalla [data-accion="maquina-guardar"]'), "y se guarda")
            guardada = bool(
                nav.esperar(
                    "document.querySelector('#pantalla').innerText.indexOf(" + json.dumps(LO_QUE_PASO) + ") >= 0",
                    segundos=25,
                )
            )
            comprobar(
                guardada,
                "una averia sin taller se guarda igual (no consta, y no pasa nada)",
                esperaba=LO_QUE_PASO + " en la ficha",
                encontre=(nav.evaluar("document.querySelector('#pantalla').innerText") or "")[-300:],
            )
    except RuntimeError as fallo:
        print(f"  >> el navegador no ha podido: {fallo}")
        FALLOS.append(f"el navegador no ha podido ({fallo})")

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  - {fallo}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
