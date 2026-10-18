"""**El abono, andado por la PANTALLA** (CRM-07, 17/10/2026).

El criterio dice *«aplicar los criterios de arriba a sus contratos, entrada, calculos, historial **y
pantallas**»*, y la parte de servidor ya esta. Esto es la pantalla.

***Por donde se llega, medido y no supuesto***: `montarAbonos` **no es un catalogo** -es el paso «¿que
abono?» del asistente de **«HE ABONADO»**-, y ahi es donde salen la **base de la riqueza** y la **densidad**.
El camino es: *HE ABONADO -> ¿Donde? (la parcela) -> ... -> ¿que abono?*.

Uso:  python scripts/verificar_el_abono_por_la_pantalla.py <direccion>
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "scripts")

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8030"

COMPROBACIONES = 0
FALLOS: list[str] = []


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    global COMPROBACIONES
    COMPROBACIONES += 1
    print(f"  [{'OK   ' if bien else 'FALLO'}] {que}")
    if not bien and encontre:
        print(f"          encontre : {encontre}")
    if not bien:
        FALLOS.append(que)
    return bien


def lasAcciones(nav) -> list:
    """Las acciones que hay en pantalla, con su campo y su valor. ***Se listan, no se suponen.***"""
    return nav.evaluar(
        "Array.from(document.querySelectorAll('#pantalla [data-accion]'))"
        ".map((b) => [b.dataset.accion, b.dataset.campo || '', b.dataset.valor || '']"
        ".join('|') + ':' + (b.textContent || '').trim().slice(0, 20))"
    )


def elTexto(nav) -> str:
    return nav.evaluar("document.querySelector('#pantalla').innerText") or ""


def pulsa(nav, selector: str) -> bool:
    return bool(
        nav.evaluar(
            "(() => { const b = document.querySelector(%s);"
            " if (b) { b.click(); return true; } return false; })()" % json.dumps(selector)
        )
    )


def pulsaPorTexto(nav, texto: str) -> bool:
    return bool(
        nav.evaluar(
            "(() => { const b = Array.from(document.querySelectorAll('#pantalla [data-accion], #marco [data-accion]'))"
            ".find((x) => (x.textContent || '').trim().toUpperCase().startsWith(%s.toUpperCase()));"
            " if (b) { b.click(); return true; } return false; })()" % json.dumps(texto)
        )
    )


def main() -> int:
    print(f"== El abono, por la pantalla  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )

            print("\n1. EL ASISTENTE DE ABONAR, PASO A PASO")
            nav.abrir(f"{DIRECCION}/", esperar=3.0)
            comprobar(pulsaPorTexto(nav, "HE ABONADO"), "se abre el asistente de abonar")
            nav.esperar("true", segundos=2.5)

            print("\n2. LA PARCELA (paso 1 de 7)")
            # ***Selector sin comillas en el valor***: `[data-campo=parcela_id]` es CSS valido tal cual, y
            # asi no hay ni una comilla que escapar. La version con comillas daba
            # `SyntaxError: missing ) after argument list`.
            comprobar(
                pulsa(nav, "[data-campo=parcela_id]"),
                "se puede elegir la parcela",
                encontre=str(lasAcciones(nav)[:4]),
            )
            nav.esperar("true", segundos=2.0)
            print(f"   tras elegir: {elTexto(nav)[:130]!r}")

            print("\n3. Y HASTA EL PASO DEL ABONO")
            for paso in range(1, 12):
                texto = elTexto(nav)
                print(f"   paso {paso}: {texto[:110]!r}")
                if "abono" in texto.lower() and "\u00bf" in texto:
                    print("      ***ESTE ES EL PASO DEL ABONO***")
                    print(f"      acciones: {lasAcciones(nav)[:10]}")
                    break
                if not any(pulsaPorTexto(nav, palabra) for palabra in ("SEGUIR", "SIGUIENTE", "APUNTAR", "\u2192")):
                    print(f"      (no encuentro como avanzar) acciones: {lasAcciones(nav)[:6]}")
                    break
                nav.esperar("true", segundos=1.8)

            print("\n4. ANADIR UN ABONO, DESDE EL PROPIO ASISTENTE")
            comprobar(
                pulsa(nav, "[data-accion=anadir-maestro]"),
                "***el asistente ofrece anadir un abono***",
                encontre=str(lasAcciones(nav)[:6]),
            )
            nav.esperar("true", segundos=3.0)
            texto = elTexto(nav)
            print(f"   el formulario: {texto[:260]!r}")
            print(f"   acciones: {lasAcciones(nav)[:14]}")

            print("\n5. EL FORMULARIO DEL ABONO, QUE ES SU PROPIO ASISTENTE")
            # ***El alta de un abono no es un formulario de una hoja***: es un asistente de varios pasos
            # -medido: «Paso 1 de 4, ¿Como se llama el abono?»-, asi que la base y la densidad **no estan
            # en el primer paso**. Hay que rellenar lo que pide cada uno para poder avanzar.
            vista_la_base = False
            vista_la_densidad = False
            for paso in range(1, 7):
                texto = elTexto(nav)
                print(f"   paso {paso}: {texto[:150]!r}")
                print(f"      acciones: {lasAcciones(nav)[:8]}")
                bajo = texto.lower()
                if "gramos por litro" in bajo or "riqueza" in bajo:
                    vista_la_base = vista_la_base or ("litro" in bajo or "riqueza" in bajo)
                    vista_la_densidad = vista_la_densidad or ("litro" in bajo)
                if "gramos por litro" in bajo:
                    print("      ***AQUI ESTAN LA BASE Y SUS TRES OPCIONES***")
                    # ***Se elige la de los liquidos***, que es el caso que el criterio pone de ejemplo.
                    comprobar(
                        pulsa(
                            nav,
                            "[data-accion=elegir][data-campo=base_de_la_riqueza]"
                            "[data-valor=gramos_por_litro]",
                        ),
                        "***se puede elegir «gramos por litro»***",
                        encontre=str(lasAcciones(nav)[:6]),
                    )
                    nav.esperar("true", segundos=1.6)
                    break
                # Rellenar lo que pida el paso (el nombre, y luego la composicion).
                nav.evaluar(
                    '(() => { const c = document.querySelector("#pantalla input[data-campo=nombre]")'
                    ' || document.querySelector("#pantalla input[type=text]");'
                    " if (!c) return false; c.value = 'Liquido 100 g/L';"
                    " c.dispatchEvent(new Event('input', { bubbles: true })); return true; })()"
                )
                if not any(
                    pulsaPorTexto(nav, palabra)
                    for palabra in ("SEGUIR", "SIGUIENTE", "GUARDAR", "\u2192")
                ):
                    print("      (no hay como avanzar; acciones arriba)")
                    break
                nav.esperar("true", segundos=1.6)

            print("\n6. LO QUE SE APORTO AYER, COMPROBADO EN LA PANTALLA")
            comprobar(
                vista_la_base,
                "***la pantalla ensena la base de la riqueza***",
                encontre=str(lasAcciones(nav)[:8]),
            )
            comprobar(
                vista_la_densidad,
                "***y la riqueza por litro, que es la base de los liquidos***",
                encontre=str(lasAcciones(nav)[:8]),
            )

            print("\n7. GUARDAR, Y VOLVER AL PASO DEL ABONO")
            # Se sigue hasta el final del formulario. La composicion se ve **en el paso del asistente**,
            # que es de donde se vino: ahi esta `composicionDelAbono`.
            for vuelta in range(1, 9):
                # ***`APUNTARLO` es el boton que cierra*** (medido: el ultimo paso es «¿Es mineral o
                # ecologico?» y ahi no hay «SEGUIR» sino «APUNTARLO»). Va el primero: en un paso que
                # ofrezca los dos, el que **cierra** es el que interesa.
                # ***LOS `data-accion` UNICOS, sin recortar.*** Adivinar el nombre del boton que cierra
                # costo tres vueltas: `asistente-apuntar` **no existe**, y por eso se pulsaba
                # `asistente-seguir` una y otra vez en el mismo paso. Se listan y se lee.
                print(
                    f"   vuelta {vuelta}: los data-accion = "
                    + str(
                        nav.evaluar(
                            'Array.from(new Set(Array.from(document.querySelectorAll("#pantalla [data-accion]"))'
                            '.map((x) => x.dataset.accion))).join(" ");'
                        )
                    )
                )
                # ***Por `data-accion`, que es lo que NO depende del idioma ni del texto del boton.***
                # ***HAY QUE ELEGIR LA OPCION DEL PASO, IGUAL QUE EN EL PASO 3.*** Aqui estuvo el atasco:
                # `APUNTARLO` **no es otro boton** -es el **texto** de `asistente-seguir` en el ultimo paso-,
                # asi que el guion pulsaba lo correcto y **no pasaba nada**: el paso 4 («¿Es mineral o
                # ecologico?») pide **elegir**, y en el paso 3 funciono justo porque se eligio «gramos por
                # litro» antes de avanzar. Los `data-accion` del paso 4, medidos:
                #     elegir  asistente-atras  asistente-saltar  asistente-seguir
                for campo, valor in (("tipo", "mineral"),):
                    nav.evaluar(
                        '(() => { const b = document.querySelector("#pantalla [data-accion=elegir]'
                        "[data-campo=" + campo + "][data-valor=" + valor + ']");'
                        " if (b) { b.click(); return true; } return false; })()"
                    )
                    nav.esperar("true", segundos=1.0)

                # ***POR ORDEN DE PRIORIDAD, y el que CIERRA primero.*** La version anterior cogia el
                # ULTIMO de una lista con `.pop()`, y en el paso 4 («¿Es mineral o ecologico?») hay
                # **tambien** un `asistente-seguir`: asi que pulsaba «avanzar» en vez de «APUNTARLO», ocho
                # vueltas seguidas en el mismo sitio. Medido en la salida: `pulsado: 'asistente-seguir'`
                # una y otra vez, con el paso 4 delante.
                pulso = nav.evaluar(
                    '(() => { const busca = (a) => document.querySelector("#pantalla [data-accion=" + a + "]");'
                    " for (const a of ['asistente-apuntar', 'asistente-guardar', 'asistente-terminar',"
                    " 'abono-guardar', 'asistente-seguir']) {"
                    " const b = busca(a); if (b) { b.click(); return a; } } return ''; })()"
                )
                print(f"              pulsado: {pulso!r}")
                if not pulso:
                    if not any(
                        pulsaPorTexto(nav, palabra)
                        for palabra in ("APUNTARLO", "GUARDAR", "TERMINAR", "SEGUIR", "\u2192")
                    ):
                        print("              (no hay como seguir)")
                        break
                nav.esperar("true", segundos=2.0)
                texto = elTexto(nav)
                if "\u00bfQu\u00e9 abono has echado" in texto or "A\u00d1ADIR UN ABONO" in texto:
                    break

            print("\n8. ***Y LA COMPOSICION, CON SU BASE***, que es el fallo que se arreglo")
            print(f"   {elTexto(nav)[:300]!r}")
            comprobar(
                "g/L" in elTexto(nav) or "g/l" in elTexto(nav),
                "***la composicion dice «g/L», no un «100-0-0» a secas***",
                encontre=elTexto(nav)[:300],
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
