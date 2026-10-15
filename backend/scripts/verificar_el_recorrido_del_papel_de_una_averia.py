"""**El papel de una averia**, andado desde la pantalla (CRM-07 #7, 14/10/2026).

El informe del dueno pedia dos cosas: «**el documento de la averia**» y «**el presupuesto**». Y al
preguntarle por el presupuesto contesto: *«**un PAPEL que se engancha a la averia**»*. Asi que las dos
cosas del informe son **una**, y esto es lo que se anda:

  1. **Se ofrece el papel de la finca**, por su titulo.
  2. Se elige, se guarda, **y la ficha dice cual es**: el nombre, no el identificador.
  3. ***Y sigue diciendolo despues de RECARGAR***, que es lo que un unitario no prueba.
  4. Y una averia **sin papel** lo dice: «sin papel apuntado». Vacio es un caso normal -la mayoria se
     arreglan uno mismo-, y callarlo dejaria al agricultor sin saber si el programa no lo sabe.

***Y LOS DESPLEGABLES DE ESTA CASA SON BOTONES*** (14/10/2026). No son `<select>`: son botones con
`data-accion="maquina-elegir"` y `data-campo="<campo>"`, que es lo que pinta `OpcionesParaElegir`
(`componentes.js`). Este recorrido lo aprendio a la mala: buscaba un `<select>` y un `#averia-papel` que
**no existen**, y el recorrido hermano -el del taller- pasaba porque lee **por el texto**. ***El que
funciona busca como se puede, no como uno cree.***

Uso:  python scripts/verificar_el_recorrido_del_papel_de_una_averia.py <direccion>

      La direccion **se pasa como primer argumento y es obligatoria**: `_api` no la recibe, la lee de la
      constante `DIRECCION` de SU modulo. Sin pasarla, el sintoma es «conexion rechazada».
"""

from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "scripts")

from capturar_la_pantalla_del_reparto import _api  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"

# El boton de elegir el papel, por su `campo`. **No hay `id`**: el componente recibe `campo`, `rotulo`
# y `opciones`, pero no el `id` del bloque, asi que un `#averia-papel` no existe nunca.
EL_BOTON = '[data-accion="maquina-elegir"][data-campo="documento_id"]'

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


def pulsar(nav, selector: str) -> bool:
    """Pulsa **desde dentro de la pagina**. Devuelve si el elemento existe, que no es lo mismo que si el
    clic hizo algo: quien comprueba tiene que mirar el **estado**, no el valor de retorno."""
    return bool(
        nav.evaluar(
            "(() => { const el = document.querySelector(%s); if (!el) return false; el.click(); return true; })()"
            % json.dumps(selector)
        )
    )


def una_maquina(token: str, nombre: str) -> dict:
    hecho = _api("/api/maquinaria", token, {"nombre": nombre, "clase": "tractor",
                 "propiedad": "propia", "disponibilidad": "disponible"}, metodo="POST")
    if not isinstance(hecho, dict) or not hecho.get("id"):
        raise SystemExit(f"la puerta no ha devuelto la maquina: {hecho!r}")
    return hecho


def una_averia(token: str, maquina_id: int, que_paso: str, **campos) -> dict:
    cuerpo = {"fecha": "2026-04-01", "que_paso": que_paso, "resuelta": False}
    cuerpo.update(campos)
    hecho = _api(f"/api/maquinaria/{maquina_id}/averias", token, cuerpo, metodo="POST")
    if not isinstance(hecho, dict) or not hecho.get("id"):
        raise SystemExit(f"la puerta no ha devuelto la averia: {hecho!r}")
    return hecho


def un_papel(token: str, titulo: str) -> dict:
    hecho = _api("/api/documentos", token, {"titulo": titulo, "tipo": "factura",
                 "carpeta": "Reparaciones"}, metodo="POST")
    if not isinstance(hecho, dict) or not hecho.get("id"):
        raise SystemExit(f"la puerta no ha devuelto el papel: {hecho!r}")
    return hecho


def main() -> int:
    print(f"== El papel de una averia  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    marca = str(int(time.time()))
    con_papel = una_maquina(token, f"El Landini del papel {marca}")
    sin_papel = una_maquina(token, f"El Fendt sin papel {marca}")
    el_papel = un_papel(token, f"Factura del taller {marca}")
    # **A la maquina del papel NO se le deja una averia hecha**: la crea el formulario en el paso 2,
    # y es la unica que tendra. Dejandole una, la ficha ensena DOS -la de la puerta, sin papel, y la
    # del formulario, con papel- y leer `averias[0]` da la primera: un rojo que no es de nadie.
    una_averia(token, sin_papel["id"], "Se rompio el embrague")
    print(f"  (una maquina con su averia, un papel («{el_papel['titulo']}») y otra maquina sin papel)")

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden("Page.addScriptToEvaluateOnNewDocument",
                      {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"})

            print("\n1. SE OFRECE EL PAPEL DE LA FINCA")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{con_papel['id']}", esperar=3.0)
            if not comprobar(
                bool(nav.esperar("document.querySelectorAll('#pantalla *').length > 20", segundos=25)),
                "la ficha de la maquina abre por su direccion",
            ):
                return 1
            comprobar(
                pulsar(nav, '#pantalla [data-accion="maquina-averia-nueva"]'),
                "se abre el formulario de la averia",
            )
            # Se **espera al ESTADO**, no a que el boton exista: el formulario tarda en pintarse.
            if not comprobar(
                bool(nav.esperar("Boolean(document.getElementById('averia-que'))", segundos=25)),
                "y el formulario esta pintado (lo dice su campo «que paso»)",
            ):
                return 1
            if not comprobar(
                bool(nav.esperar(f"document.querySelectorAll({json.dumps(EL_BOTON)}).length > 0", segundos=25)),
                "y el papel se puede elegir",
            ):
                return 1
            opciones = nav.evaluar(
                f"Array.from(document.querySelectorAll({json.dumps(EL_BOTON)}))"
                "  .map((b) => (b.innerText || '').replace(/\\s+/g, ' ').trim())"
            ) or []
            comprobar(
                any("Factura del taller" in (texto or "") for texto in opciones),
                "y lo que se ofrece incluye el papel de la finca, con su titulo",
                esperaba="«Factura del taller…» entre las opciones",
                encontre=" · ".join(opciones)[:220],
            )

            print("\n2. SE ELIGE, SE GUARDA, Y LA FICHA DICE CUAL ES")
            elegido = nav.evaluar(
                f"(() => {{ const bs = Array.from(document.querySelectorAll({json.dumps(EL_BOTON)}));"
                " if (!bs.length) return 'sin opciones';"
                " const b = bs.find((x) => (x.innerText || '').indexOf('Factura del taller') >= 0);"
                " if (!b) return 'sin el papel';"
                " b.click();"
                " return (b.innerText || '').replace(/\\s+/g, ' ').trim(); })()"
            )
            comprobar(
                isinstance(elegido, str) and "Factura del taller" in elegido,
                "se elige el papel de la lista",
                encontre=str(elegido)[:140],
            )
            # ***HAY QUE DECIR QUE PASO***: `que_paso` es obligatorio en el esquema (`min_length=1`), y
            # sin rellenarlo el servidor contesta 422 y **no guarda nada** -mientras todas las
            # comprobaciones de alrededor pasan, porque `pulsar` solo mira que el boton exista-.
            nav.evaluar(
                "(() => { const c = document.getElementById('averia-que'); if (!c) return false;"
                " c.value = 'Se rompio el eje del ventilador';"
                " c.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"
            )
            comprobar(pulsar(nav, '#pantalla [data-accion="maquina-guardar"]'), "se pulsa guardar")
            # ***Y SE ESPERA A QUE EL FORMULARIO SE CIERRE***, que es la senal de que el guardado fue bueno
            # (`suyo.formulario = null` solo pasa despues de un guardado que el servidor acepto). Sin esta
            # espera, el `esperar` de abajo pasa **con el desplegable todavia abierto** -que ya ensena el
            # titulo- y la fila se lee antes de que la ficha se repinte: un falso positivo en toda regla.
            if not comprobar(
                bool(nav.esperar("!document.getElementById('averia-que')", segundos=25)),
                "***y el guardado entra***: el formulario se cierra solo cuando el servidor lo acepta",
                esperaba="el formulario cerrado",
                encontre="el formulario sigue abierto (el guardado no entro)",
            ):
                return 1
            texto = nav.evaluar("document.querySelector('#pantalla').innerText") or ""
            # **Se mira la FILA de la averia, no la ficha entera**: buscar en todo el documento encuentra
            # el boton de guardar («APUNTAR UNA AVERIA») y da un rojo que no es de nadie. Es la leccion de
            # «leer un solo contenedor», que ya costo un falso rojo con los botones del reparto.
            suyas = nav.evaluar(
                "Array.from(document.querySelectorAll('#pantalla .apunte-detalle'))"
                "  .map((e) => (e.innerText || '').replace(/\\s+/g, ' ').trim())"
                "  .filter((x) => x.indexOf('Papel') >= 0)"
            ) or []
            junto = " · ".join(suyas)
            comprobar(
                any(x.startswith("Papel:") for x in suyas),
                "la ficha dice CUAL es el papel, en la fila de la averia",
                esperaba="una linea «Papel: …»",
                encontre=junto or "(ninguna linea de papel)",
            )
            comprobar("Factura del taller" in junto, "y con su titulo, no con su identificador", encontre=junto)

            print("\n3. Y SE RECARGA LA PAGINA: sigue diciendolo")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{con_papel['id']}", esperar=3.0)
            nav.esperar("document.querySelector('#pantalla').innerText.indexOf('Factura del taller') >= 0",
                        segundos=25)
            texto2 = nav.evaluar("document.querySelector('#pantalla').innerText") or ""
            comprobar("Factura del taller" in texto2, "lo guardado sigue despues de recargar", encontre=texto2[-260:])

            print("\n4. Y UNA AVERIA SIN PAPEL LO DICE")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{sin_papel['id']}", esperar=3.0)
            nav.esperar("document.querySelector('#pantalla').innerText.indexOf('Papel:') >= 0", segundos=25)
            texto3 = nav.evaluar("document.querySelector('#pantalla').innerText") or ""
            comprobar(
                "Sin papel apuntado" in texto3,
                "sin papel dice que no hay ninguno, que es la verdad",
                esperaba="«Sin papel apuntado»",
                encontre=texto3[-260:],
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
