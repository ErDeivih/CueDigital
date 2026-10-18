"""**La preparacion de la PAC, andada desde la PANTALLA** (CRM-09, 17/10/2026).

La cola lo pide con estas palabras: *«paquete preparatorio por recinto: referencias, superficie, cultivos,
practica, documentos y cuestiones pendientes. ***No envio directo ni garantia de elegibilidad***»*, y
*«falta area/cultivo/evidencia -> ***incompleto***»*.

***Y esto se anda por la pantalla, no por la puerta***: *un paquete que solo existe en el servidor **no es una
funcion para el agricultor**.*

Lo que se comprueba, en orden, **contrastando la pantalla con lo que dice su puerta** -que es lo que hace que
esta prueba no dependa de los datos de la finca de pruebas-:

  1. ***Lo primero que se lee es lo que NO se puede afirmar***: sin fuente legal cargada, «no se puede decir si
     algo es elegible» -y se lee **antes** del resumen-.
  2. ***El porcentaje lleva su numerador y su denominador***, o dice que no se sabe: *nunca un cero*.
  3. ***Las hectareas que se quedan fuera se dicen***.
  4. ***Cada tierra sale, con lo que le falta***: *las incompletas no se esconden*.
  5. ***Y la advertencia va al pie, siempre***: «no es la declaracion ni una garantia de elegibilidad».

Uso:  python scripts/verificar_el_recorrido_de_la_pac.py <direccion>
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


def elTexto(nav) -> str:
    return nav.evaluar("document.querySelector('#pantalla').innerText") or ""


def main() -> int:
    print(f"== La preparacion de la PAC, por la pantalla  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token

    # ***Lo que dice la puerta***, para contrastar la pantalla contra ello: *asi la prueba no depende de que la
    # finca de pruebas tenga unas hectareas concretas.*
    el_paquete = _api("/api/pac/paquete", token, metodo="GET")
    if not isinstance(el_paquete, dict):
        raise SystemExit(f"la puerta no ha devuelto el paquete: {el_paquete!r}")

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            # ***La sesion del navegador, puesta ANTES de la primera pagina***: *`preparar` da el token para la
            # API, pero el navegador tiene el suyo en su `localStorage` -y sin el se abre la pantalla de
            # ENTRAR, que es lo que paso la primera vez que se anduvo este guion: **ocho comprobaciones y
            # cinco fallos, todos contra la pantalla de entrar**-.*
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )
            nav.abrir(f"{DIRECCION}/#/pac", esperar=3.0)
            nav.esperar(
                "document.querySelector('#pantalla').innerText.length > 60", segundos=30
            )
            texto = elTexto(nav)

            print("\n1. LO PRIMERO ES LO QUE NO SE PUEDE AFIRMAR")
            comprobar(
                "no se puede decir si algo es elegible" in texto.lower(),
                "***y se dice: sin fuente legal no hay elegibilidad***",
                esperaba="«no se puede decir si algo es elegible»",
                encontre=texto[:320],
            )
            # ***Y antes del resumen***: *decirlo despues de la tabla es decirlo tarde.*
            el_aviso = texto.lower().find("elegible")
            el_resumen = texto.find(el_paquete["textos"]["resumen"])
            comprobar(
                el_resumen < 0 or (el_aviso >= 0 and el_aviso < el_resumen),
                "***y se lee ANTES del resumen***",
                esperaba="el aviso primero",
                encontre=f"aviso en {el_aviso}, resumen en {el_resumen}",
            )

            print("\n2. EL PORCENTAJE, CON SU NUMERADOR Y SU DENOMINADOR")
            suyo = el_paquete["el_resumen"]
            if suyo.get("porcentaje") is None:
                comprobar(
                    el_paquete["textos"]["falta_superficie"] in texto,
                    "***y si no se sabe, se dice***",
                    esperaba=f"«{el_paquete['textos']['falta_superficie']}»",
                    encontre=texto[:400],
                )
                comprobar(
                    "0 %" not in texto,
                    "***y NUNCA un cero por ciento***",
                )
            else:
                comprobar(
                    f"{suyo['numerador']} de {suyo['denominador']}" in texto,
                    "***con el numerador y el denominador a la vista***",
                    esperaba=f"«{suyo['numerador']} de {suyo['denominador']}»",
                    encontre=texto[:400],
                )
                comprobar(
                    f"{suyo['porcentaje']} %" in texto,
                    "***y su porcentaje***",
                    esperaba=f"«{suyo['porcentaje']} %»",
                    encontre=texto[:400],
                )

            print("\n3. LAS HECTAREAS QUE SE QUEDAN FUERA SE DICEN")
            if suyo.get("se_queda_fuera"):
                comprobar(
                    f"{suyo['se_queda_fuera']} ha" in texto,
                    "***«tierra sin cultivo no desaparece para pintar verde»***",
                    esperaba=f"«{suyo['se_queda_fuera']} ha»",
                    encontre=texto[:500],
                )

            print("\n4. CADA TIERRA SALE, CON LO QUE LE FALTA")
            la_primera = (el_paquete["las_tierras"] or [{}])[0].get("alias")
            comprobar(
                bool(la_primera) and la_primera in texto,
                "***y las tierras salen, por su nombre***",
                esperaba=f"«{la_primera}»",
                encontre=texto[:400],
            )
            if el_paquete.get("las_incompletas"):
                comprobar(
                    el_paquete["textos"]["incompleto"] in texto,
                    "***y las incompletas lo dicen: no se esconden***",
                    esperaba=f"«{el_paquete['textos']['incompleto']}»",
                    encontre=texto[:600],
                )

            print("\n5. Y LA ADVERTENCIA VA AL PIE, SIEMPRE")
            comprobar(
                "garantia de elegibilidad" in texto.lower().replace("í", "i"),
                "***«no es la declaracion ni una garantia de elegibilidad»***",
                esperaba="la advertencia del pie",
                encontre=texto[-320:],
            )
            # ***Y viaja en la respuesta***, no solo en la pantalla: *el paquete se puede guardar y reenviar.*
            comprobar(
                bool(el_paquete.get("no_es_garantia")),
                "***y viaja con el paquete, no solo en la pantalla***",
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
