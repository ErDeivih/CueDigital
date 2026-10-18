"""**Las reservas, andadas desde la PANTALLA** (CRM-07 #9, 17/10/2026).

La cola lo pide con estas palabras: «***Reserva para planificar no es consumo***», y el encargo del modulo
pide *«reservas con maquina, intervalo, responsable, trabajo y estado; ***conflictos de solape en servidor***,
anulaciones e indisponibilidad por averia»*.

Y esto se anda **por los formularios**, no por la puerta: el revisor lo dejo dicho -«no sustituir los
formularios por altas mediante API»-, porque un apunte que solo existe en el servidor **no es una funcion
para el agricultor**.

Lo que se comprueba, en orden:

  1. Una maquina **sin reservas** lo dice, **y ofrece reservarla**.
  2. El boton **abre el formulario**, y trae sus campos: desde, hasta, como va y notas.
  3. Se reserva un tramo y la ficha la ensena, con su estado.
  4. ***Otra reserva que se pisa la para EL SERVIDOR***, y **lo dice** con su motivo.
  5. La misma hora en **otra maquina** si se puede.
  6. **Corregir** sale relleno con lo que habia.
  7. **Anular** pide el motivo, y la maquina **vuelve a estar libre**: *el mismo tramo se puede reservar
     otra vez*, que es la prueba de que anular de verdad la libera.
  8. **Se recarga** la pagina y todo sigue.

Uso:  python scripts/verificar_el_recorrido_de_las_reservas.py <direccion>
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


def pulsar(nav, selector: str) -> None:
    """Pulsa algo. **No devuelve nada**: un boton que existe no es un boton que ha hecho su trabajo."""
    nav.evaluar(
        "(() => { const b = document.querySelector(%s); if (b) b.click(); return true; })()"
        % json.dumps(selector)
    )


def escribe(nav, casilla: str, texto: str) -> bool:
    return bool(
        nav.evaluar(
            "(() => { const c = document.getElementById(%s); if (!c) return false;"
            " c.value = %s;"
            " c.dispatchEvent(new Event('input', { bubbles: true }));"
            " c.dispatchEvent(new Event('change', { bubbles: true })); return true; })()"
            % (json.dumps(casilla), json.dumps(texto))
        )
    )


def elTexto(nav) -> str:
    return nav.evaluar("document.querySelector('#pantalla').innerText") or ""


def esperarQueDiga(nav, texto: str, segundos: int = 25):
    """Espera a que **la pantalla diga algo**.

    ***El texto va por `json.dumps` y no cosido a mano*** (17/10/2026): *un selector o una frase con
    comillas dentro, metidos a mano en una cadena de JavaScript, **rompen el fichero entero** -y el
    fallo sale como un `SyntaxError` en una linea que parece correcta-. Con `json.dumps` se escapa solo.*
    """
    return nav.esperar(
        "document.querySelector('#pantalla').innerText.includes(%s)" % json.dumps(texto), segundos=segundos
    )


def esperarQueHaya(nav, selector: str, segundos: int = 20):
    """Espera a que **exista algo en la pantalla**. *Mismo motivo que arriba: `json.dumps`.*"""
    return nav.esperar("Boolean(document.querySelector(%s))" % json.dumps(selector), segundos=segundos)


def laFicha(nav, direccion: str, maquina_id: int, *, espera: str = "Reservas") -> str:
    nav.abrir(f"{direccion}/#/maquinaria/{maquina_id}", esperar=3.0)
    nav.esperar(
        f"document.querySelector('#pantalla').innerText.indexOf({json.dumps(espera)}) >= 0", segundos=25
    )
    return elTexto(nav)


def unaMaquina(token: str, nombre: str) -> int:
    creada = _api(
        "/api/maquinaria",
        token,
        {"nombre": nombre, "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
        metodo="POST",
    )
    if not isinstance(creada, dict) or not creada.get("id"):
        raise SystemExit(f"la puerta no ha devuelto la maquina: {creada!r}")
    return creada["id"]


def lasReservas(token: str, maquina_id: int) -> list:
    suyas = _api(f"/api/maquinaria/{maquina_id}/reservas", token, metodo="GET")
    return suyas if isinstance(suyas, list) else []


def main() -> int:
    print(f"== Las reservas, por la pantalla  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    marca = str(int(time.time()))
    suya = unaMaquina(token, f"El reservado {marca}")
    laOtra = unaMaquina(token, f"El otro {marca}")

    # ***Un tramo con hora, que es lo que decide el solape***. *Se usa una fecha lejana para no chocar con
    # nada de la finca de pruebas.*
    desde = "2027-05-20T08:00"
    hasta = "2027-05-20T14:00"

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )

            print("\n1. UNA MAQUINA SIN RESERVAS LO DICE, Y OFRECE RESERVARLA")
            texto = laFicha(nav, DIRECCION, suya)
            comprobar("No has reservado esta" in texto, "dice que no ha reservado nada", encontre=texto[-300:])
            comprobar(
                "Reservar no gasta nada" in texto,
                "***y dice que reservar NO es consumo***, que es la frase de la cola",
            )

            print("\n2. EL BOTON ABRE EL FORMULARIO, CON SUS CAMPOS")
            pulsar(nav, '#pantalla [data-accion="maquina-reserva-nueva"]')
            for casilla, que in (
                ("reserva-desde", "el desde"),
                ("reserva-hasta", "el hasta"),
                ("reserva-notas", "las notas"),
            ):
                comprobar(
                    bool(esperarQueHaya(nav, f"#{casilla}")),
                    f"el formulario trae {que}",
                )
            # ***Y los dos extremos son de FECHA Y HORA***: *una reserva es «el martes de 9 a 11», y con un
            # campo de solo fecha la hora se perderia al guardar, y en silencio.*
            comprobar(
                nav.evaluar("document.getElementById('reserva-desde').type") == "datetime-local",
                "***y son de fecha Y HORA, no de solo fecha***",
                encontre=str(nav.evaluar("document.getElementById('reserva-desde').type")),
            )
            comprobar(
                "Pedida" in elTexto(nav) and "En curso" in elTexto(nav) and "Hecha" in elTexto(nav),
                "***y el estado se ELIGE entre los tres que hay***",
            )

            print("\n3. SE RESERVA UN TRAMO, Y LA FICHA LA ENSENA")
            escribe(nav, "reserva-desde", desde)
            escribe(nav, "reserva-hasta", hasta)
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            comprobar(
                bool(esperarQueDiga(nav, 'Ya está reservada')),
                "el aviso dice que se ha reservado",
                encontre=elTexto(nav)[-300:],
            )
            texto = elTexto(nav)
            comprobar("Pedida" in texto, "***y la reserva sale en la ficha, con su estado***", encontre=texto[-400:])

            suyas = lasReservas(token, suya)
            comprobar(len(suyas) == 1, "y hay UNA reserva en el servidor", encontre=str(len(suyas)))
            la_primera = suyas[0]["id"] if suyas else 0

            print("\n4. OTRA QUE SE PISA LA PARA EL SERVIDOR, Y LO DICE")
            pulsar(nav, '#pantalla [data-accion="maquina-reserva-nueva"]')
            esperarQueHaya(nav, "#reserva-desde")
            # *Un tramo que se pisa por la mitad: de 12:00 a 18:00 choca con 08:00-14:00.*
            escribe(nav, "reserva-desde", "2027-05-20T12:00")
            escribe(nav, "reserva-hasta", "2027-05-20T18:00")
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            comprobar(
                bool(esperarQueDiga(nav, 'ya está reservada')),
                "***el solape lo para el servidor, y lo dice***",
                encontre=elTexto(nav)[-400:],
            )
            comprobar(
                len(lasReservas(token, suya)) == 1,
                "***y NO se ha apuntado la segunda***",
                encontre=str(len(lasReservas(token, suya))),
            )

            print("\n5. LA MISMA HORA EN OTRA MAQUINA SI SE PUEDE")
            laOtraTexto = laFicha(nav, DIRECCION, laOtra)
            pulsar(nav, '#pantalla [data-accion="maquina-reserva-nueva"]')
            esperarQueHaya(nav, "#reserva-desde")
            escribe(nav, "reserva-desde", desde)
            escribe(nav, "reserva-hasta", hasta)
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            comprobar(
                bool(esperarQueDiga(nav, 'Ya está reservada')),
                "otra maquina, a la misma hora, si se puede",
                encontre=elTexto(nav)[-300:],
            )
            comprobar(len(lasReservas(token, laOtra)) == 1, "y queda apuntada en la suya")

            print("\n6. CORREGIR SALE RELLENO CON LO QUE HABIA")
            texto = laFicha(nav, DIRECCION, suya)
            pulsar(nav, f'#pantalla [data-accion="maquina-reserva-corregir"][data-id="{la_primera}"]')
            comprobar(
                bool(esperarQueHaya(nav, "#reserva-desde")),
                "el formulario de corregir sale",
            )
            comprobar(
                (nav.evaluar("document.getElementById('reserva-desde').value") or "").startswith("2027-05-20"),
                "***y viene relleno con lo que habia***",
                encontre=str(nav.evaluar("document.getElementById('reserva-desde').value")),
            )

            print("\n7. ANULAR PIDE EL MOTIVO, Y LA MAQUINA VUELVE A ESTAR LIBRE")
            pulsar(nav, '#pantalla [data-accion="maquina-cancelar"]')
            esperarQueHaya(nav, '#pantalla [data-accion="maquina-reserva-corregir"]')
            pulsar(nav, f'#pantalla [data-accion="maquina-anular"][data-que="reserva"][data-id="{la_primera}"]')
            comprobar(
                bool(esperarQueHaya(nav, "#anular-motivo")),
                "***anular pide su motivo, como una averia***",
            )
            escribe(nav, "anular-motivo", "Se cayo el trabajo")
            pulsar(nav, '#pantalla [data-accion="maquina-anular-confirmar"]')
            comprobar(
                bool(esperarQueDiga(nav, 'vuelve a estar libre')),
                "***y el aviso dice que la maquina vuelve a estar libre***",
                encontre=elTexto(nav)[-300:],
            )
            comprobar("Se cayo el trabajo" in elTexto(nav), "la reserva queda tachada con su motivo")

            # ***Y ESTA ES LA PRUEBA DE QUE ANULAR DE VERDAD LA LIBERA***: *el mismo tramo, otra vez.*
            pulsar(nav, '#pantalla [data-accion="maquina-reserva-nueva"]')
            esperarQueHaya(nav, "#reserva-desde")
            escribe(nav, "reserva-desde", desde)
            escribe(nav, "reserva-hasta", hasta)
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            comprobar(
                bool(esperarQueDiga(nav, 'Ya está reservada')),
                "***y el MISMO tramo se puede reservar otra vez: anular de verdad la libera***",
                encontre=elTexto(nav)[-400:],
            )

            print("\n8. SE RECARGA LA PAGINA, Y TODO SIGUE")
            texto = laFicha(nav, DIRECCION, suya)
            comprobar(texto.count("Pedida") >= 1 or "Pedida" in texto, "las reservas siguen tras recargar")
            comprobar("Se cayo el trabajo" in texto, "***y la anulada sigue con su motivo***", encontre=texto[-400:])

    except Exception as fallo:  # noqa: BLE001
        comprobar(False, f"el recorrido se rompio: {fallo}")

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    if FALLOS:
        for uno in FALLOS:
            print(f"  - {uno}")
        return 1
    print("***Las reservas se andan enteras por la pantalla.***")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
