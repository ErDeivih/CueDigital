"""**El panel de la finca, andado desde la PANTALLA** (CRM-11, 17/10/2026).

La cola lo pide con estas palabras: *«***valor nullable, unidad, periodo, finca/campana, filtros, cobertura,
fuente y enlace***. ***Hectareas de trabajo acumulado distintas de superficie unica; kilos distintos de
EUR***»*, y el contrato del panel, escrito en `app/paneles.py`: *«un panel no es una pantalla con numeros, es
**un numero que se puede defender**»*.

***Y esto se anda por la pantalla, no por la puerta***: *una metrica que solo existe en el servidor **no es una
funcion para el agricultor**.*

***Y el panel vive en el INICIO*** -su modulo del menu se llama `panel`-, asi que su direccion es `#/panel` y
es la primera pantalla que se abre.

Lo que se comprueba, **contrastando la pantalla con lo que dice su puerta**:

  1. ***Las metricas salen en el inicio***, con su titulo.
  2. ***Cada una dice en que se mide*** -su unidad- ***y de donde sale*** -su fuente-.
  3. ***Y cuanto ha mirado***: la cobertura, `contadas` de `de`.
  4. ***Lo que no se sabe se dice con su palabra*** -«No se sabe»-, y **nunca con un cero**.
  5. ***Y se avisa de que las cifras no se suman***: *«contestan a preguntas distintas».*

Uso:  python scripts/verificar_el_recorrido_del_panel.py <direccion>
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
    print(f"== El panel de la finca, por la pantalla  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token

    # ***Lo que dice la puerta***, para contrastar la pantalla contra ello: *asi la prueba no depende de los
    # datos de la finca de pruebas.*
    el_panel = _api("/api/panel", token, metodo="GET")
    if not isinstance(el_panel, dict):
        raise SystemExit(f"la puerta no ha devuelto el panel: {el_panel!r}")
    las_suyas = el_panel.get("las_metricas") or []
    if not las_suyas:
        raise SystemExit("la puerta no ha devuelto ninguna metrica")

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            # ***La sesion, antes de la primera pagina***: *sin ella se abre la pantalla de ENTRAR y todas las
            # comprobaciones fallan contra el formulario -que es lo que paso con el recorrido de la PAC-.*
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )
            # ***El inicio NO vive en `#/panel`***: *`pantallaDeLaDireccion` mapea el **modulo** `panel` a la
            # pantalla `inicio`, y eso es para marcar el renglon del menu -no para leer la direccion-. En la
            # tabla del enrutador, `inicio` tiene **el camino vacio** (`patron: []`), asi que el inicio es la
            # raiz. Con `#/panel` la aplicacion contestaba «esa direccion no lleva a ninguna parte», y las
            # catorce comprobaciones de este guion fallaban contra esa pantalla -no contra el panel-.*
            nav.abrir(f"{DIRECCION}/", esperar=3.0)
            # *Las metricas se piden **aparte** al abrir el inicio, asi que hay que esperar a que lleguen.*
            nav.esperar(
                "document.querySelector('#pantalla').innerText.includes("
                + json.dumps(el_panel["textos"]["titulo"])
                + ")",
                segundos=30,
            )
            texto = elTexto(nav)

            print("\n1. LAS METRICAS SALEN EN EL INICIO")
            comprobar(
                el_panel["textos"]["titulo"] in texto,
                "***el panel esta donde el agricultor entra***",
                esperaba=f"«{el_panel['textos']['titulo']}»",
                encontre=texto[:300],
            )
            comprobar(
                el_panel["textos"]["explica"] in texto,
                "y dice lo que esta mirando",
                encontre=texto[:400],
            )

            print("\n2. CADA UNA DICE EN QUE SE MIDE Y DE DONDE SALE")
            for una in las_suyas[:3]:
                comprobar(
                    una["titulo"] in texto,
                    f"***«{una['titulo']}» sale***",
                    encontre=texto[:600],
                )
                comprobar(
                    una["unidad"] in texto,
                    f"***y en que se mide ({una['unidad']})***",
                    esperaba=una["unidad"],
                    encontre=texto[:800],
                )
                comprobar(
                    una["fuente"] in texto,
                    f"***y de donde sale ({una['fuente']})***",
                    esperaba=una["fuente"],
                    encontre=texto[:800],
                )

            print("\n3. Y CUANTO HA MIRADO")
            la_primera = las_suyas[0]
            if la_primera["cobertura"]["de"]:
                comprobar(
                    f"{la_primera['cobertura']['contadas']} de {la_primera['cobertura']['de']}" in texto,
                    "***la cobertura: cuantas se han mirado***",
                    esperaba=f"«{la_primera['cobertura']['contadas']} de {la_primera['cobertura']['de']}»",
                    encontre=texto[:800],
                )

            print("\n4. LO QUE NO SE SABE SE DICE, Y NUNCA UN CERO")
            if any(una.get("valor") is None for una in las_suyas):
                comprobar(
                    el_panel["textos"]["no_se_sabe"] in texto,
                    "***«No se sabe», con su palabra***",
                    esperaba=f"«{el_panel['textos']['no_se_sabe']}»",
                    encontre=texto[:900],
                )
            # *Y en ningun caso un cero disfrazado de dato: la pantalla no pinta `0 <unidad>` de una metrica
            # que no se sabe.*
            comprobar(
                all(
                    f"0 {una['unidad']}" not in texto
                    for una in las_suyas
                    if una.get("valor") is None
                ),
                "***y NUNCA un cero donde no se sabe***",
            )

            print("\n5. Y SE AVISA DE QUE LAS CIFRAS NO SE SUMAN")
            comprobar(
                el_panel["textos"]["no_se_suman"] in texto,
                "***«contestan a preguntas distintas»***",
                esperaba=f"«{el_panel['textos']['no_se_suman']}»",
                encontre=texto[-400:],
            )
            # ***Y las parejas que se confunden viajan en la respuesta***, para que la pantalla no las sepa de
            # memoria.
            comprobar(
                len(el_panel.get("lo_que_no_se_suma") or []) >= 2,
                "***y la puerta dice que parejas se confunden***",
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
