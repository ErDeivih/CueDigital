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
import pathlib
import sys
import time

sys.path.insert(0, "scripts")

from capturar_la_pantalla_del_reparto import _api  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
# ***`_llamar` y no `_api` para lo que puede contestar 4xx***: *`_api` **lanza**, y hay comprobaciones -el 409 del
# conflicto- en las que **el 4xx es el resultado que se busca**.*
from verificar_los_permisos_por_rol import _llamar  # noqa: E402

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


def esperar_de_verdad(nav, condicion: str, que: str, segundos: float = 40.0) -> None:
    """***Una espera que, si no llega, REVIENTA*** (19/10/2026).

    *`navegador_cdp.esperar` **devuelve `False` al agotarse; no lanza**. Asi que `nav.esperar(...)` a secas era
    **decoracion**: el guion seguia, las comprobaciones de despues median lo que hubiera -a menudo nada- y salian
    «OK» por no haber mirado.*

    ***Es el mismo vicio que un control que pasa con y sin el defecto***, y en un recorrido de navegador es el mas
    caro: **el guion decia «y sale en el historial» con el historial vacio.***

    *Aqui se comprueba el resultado y se para diciendo **que** no llego.*
    """
    if not nav.esperar(condicion, segundos=segundos):
        raise RuntimeError(f"***no se cumplio***: {que}")


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
            # ***El ancla es «Lo que consta»*** (18/10/2026): *la pantalla se rehizo con el recorrido completo, y
            # el resumen del paquete vive ahora en la capa de lo que consta. **La propiedad es la misma**: el aviso,
            # antes que las cifras.*
            el_resumen = texto.find("Lo que consta")
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

            # ============================================================================ la campaña y la hipótesis
            print("\n3. LA CAMPANA OBJETIVO Y LA HIPOTESIS  -el recorrido del agricultor-")
            nav.abrir(f"{DIRECCION}/#/pac", esperar=2.0)
            nav.esperar("document.querySelector('#pac-anio') !== null", segundos=30)
            el_anio = (el_paquete.get("campana_anio") or 2026) + 1
            nav.evaluar(
                "(() => { const c = document.querySelector('#pac-anio');"
                f" c.value = '{el_anio}';"
                " c.dispatchEvent(new Event('input', {bubbles: true})); return 'puesto'; })()"
            )
            nav.pulsar('[data-accion="pac-evaluar"]')
            nav.esperar(
                "document.querySelector('[data-capa=\"escenario\"]') !== null", segundos=40
            )
            comprobar(
                "hipótesis" in elTexto(nav).lower() or "hipotesis" in elTexto(nav).lower(),
                "***el escenario se pinta y dice que es una hipotesis***",
                encontre=elTexto(nav)[:400],
            )

            # *Una hipotesis de verdad: se propone un cultivo en una tierra y se compara.*
            el_primero = (el_paquete.get("las_tierras") or [{}])[0].get("parcela_id")
            if el_primero:
                nav.evaluar(
                    "(() => { const s = document.getElementById('pac-cultivo-" + str(el_primero) + "');"
                    " if (!s) return 'sin-select'; s.value = 'cebada';"
                    " s.dispatchEvent(new Event('change', {bubbles: true})); return 'puesto'; })()"
                )
                nav.pulsar(f'[data-accion="pac-proponer"][data-parcela="{el_primero}"]')
                # *Proponer **calcula** (19/10/2026), asi que se espera al escenario de la propuesta: **no a un
                # `true`**, que pasaba siempre y dejaba al guion midiendo lo de antes.*
                esperar_de_verdad(
                    nav,
                    "document.querySelector('[data-capa=\"escenario\"]') !== null",
                    "el escenario con la propuesta",
                )
                nav.pulsar('[data-accion="pac-comparar"]')
                esperar_de_verdad(
                    nav,
                    "document.querySelector('[data-paso=\"diferencias\"]') !== null",
                    "la comparacion de las dos alternativas",
                )
                comprobar(
                    "cebada" in elTexto(nav).lower(),
                    "***y la comparacion ensena lo propuesto***",
                    encontre=elTexto(nav)[:500],
                )

            # ============================================================================ guardar y el historial
            print("\n4. GUARDAR LA VERSION Y VER EL HISTORIAL")
            # ***El boton tiene que estar VIVO***: *si esta `disabled`, el clic no hace nada y el guion lo tapaba
            # dando por bueno el historial vacio. Se mira antes de pulsar.*
            comprobar(
                nav.evaluar(
                    "(() => { const b = document.querySelector('[data-accion=\"pac-guardar\"]');"
                    " return !!b && !b.disabled; })()"
                )
                is True,
                "***el boton de guardar esta vivo (hay escenario que guardar)***",
            )
            nav.pulsar('[data-accion="pac-guardar"]')
            esperar_de_verdad(
                nav,
                "(() => { const a = document.querySelector('[data-aviso=\"aviso\"]');"
                " return !!a && a.innerText.toLowerCase().includes('guardada'); })()",
                "el aviso de la version guardada",
            )
            comprobar(
                "version 1" in elTexto(nav).lower() or "versión 1" in elTexto(nav).lower(),
                "***la version 1 queda guardada y se dice***",
                encontre=elTexto(nav)[:500],
            )

            nav.pulsar('[data-accion="pac-historial"]')
            esperar_de_verdad(
                nav, "document.querySelector('[data-foto]') !== null", "la foto en el historial"
            )
            comprobar(
                (nav.evaluar("document.querySelectorAll('[data-foto]').length") or 0) >= 1,
                "***y sale en el historial, contada***",
            )

            # ============================================================================ la exportacion, de verdad
            print("\n5. LA EXPORTACION: el fichero de ESA version")
            import tempfile as _tempfile

            with _tempfile.TemporaryDirectory(prefix="cd-pac-csv-") as la_carpeta:
                nav.descargas_en(la_carpeta)
                esperar_de_verdad(
                    nav,
                    "document.querySelector('[data-accion=\"pac-exportar\"]') !== null",
                    "el boton de exportar la version guardada",
                    segundos=30,
                )
                nav.esperar(
                    "document.querySelector('[data-accion=\"pac-exportar\"]') !== null", segundos=30
                )
                nav.pulsar('[data-accion="pac-exportar"]')
                # ***`nombre` es el nombre EXACTO del fichero, no una extension***: *pasarle `.csv` no casaba con
                # `pac-2027-v1.csv` y devolvia `None` -que el guion leia como «no se descargo nada» cuando lo que
                # no casaba era el filtro-. Se espera a lo que llegue y se mira la extension aqui.*
                el_fichero = nav.lo_descargado(segundos=25)
                if el_fichero is not None and el_fichero.suffix.lower() != ".csv":
                    el_fichero = None
                print(
                    "    el historial en el DOM: "
                    + str(
                        nav.evaluar(
                            "(() => { const h = document.querySelector('[data-capa=\"historial\"]');"
                            " return h ? h.outerHTML.slice(0, 700) : '(sin historial)'; })()"
                        )
                    )[:700]
                )
                if el_fichero is None:
                    comprobar(False, "***la exportacion tiene que descargar un fichero***")
                else:
                    el_contenido = pathlib.Path(el_fichero).read_text(encoding="utf-8-sig", errors="replace")
                    comprobar(
                        f"version 1" in el_contenido and str(el_anio) in el_contenido,
                        "***y el fichero dice SU version y SU año***",
                        esperaba=f"version 1 · {el_anio}",
                        encontre=el_contenido[:260],
                    )

            # ============================================================================ el conflicto
            print("\n6. LO QUE CAMBIA ENTRE EVALUAR Y GUARDAR: el conflicto")
            # *Se evalua, se cambia la finca por la puerta y se guarda con la huella de lo evaluado: **el servidor
            # tiene que decir que cambio, no sustituirlo**.*
            el_estado, el_de_antes = _llamar(
                DIRECCION, "/api/pac/escenario", token=token, cuerpo={"anio": el_anio}, metodo="POST"
            )
            la_huella = ((el_de_antes or {}).get("escenario") or {}).get("huella_de_la_fuente")
            if la_huella and el_primero:
                _llamar(
                    DIRECCION,
                    f"/api/parcelas/{el_primero}",
                    token=token,
                    cuerpo={"alias": f"Cambiado {int(time.time())}"},
                    metodo="PUT",
                )
                # ***`_llamar` y no `_api`***: *`_api` **lanza** cuando la puerta contesta 409 -y el 409 es
                # **exactamente lo que se viene a comprobar**-. Con `_api`, el guion se moria en el caso que existia
                # para comprobar.*
                el_guardado, el_cuerpo = _llamar(
                    DIRECCION,
                    "/api/pac/foto",
                    token=token,
                    cuerpo={"anio": el_anio, "huella_de_la_fuente": la_huella},
                    metodo="POST",
                )
                comprobar(
                    el_guardado == 409,
                    "***guardar lo evaluado con la finca cambiada tiene que dar 409***",
                    encontre=str(el_cuerpo)[:300],
                )
                comprobar(
                    isinstance(el_cuerpo, dict)
                    and (el_cuerpo.get("detail") or {}).get("se_puede_recalcular") is True,
                    "***y decir que se puede recalcular***",
                    encontre=str(el_cuerpo)[:300],
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
