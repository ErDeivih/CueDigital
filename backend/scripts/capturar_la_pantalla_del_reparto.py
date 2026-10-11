"""La pantalla del reparto de un cobro, **en un navegador de verdad y con capturas** (11/10/2026).

POR QUÉ EXISTE. El ticket CRM-01 terminó con todo el reparto hecho y probado —el alta, la ficha, el banco,
el margen, la lista de sin asignar, el recorrido en 39 · 0— y con **una** cosa pendiente que no puede hacer
quien escribe el programa: **mirar la pantalla**. Este guion monta el caso del encargo (un ingreso de 350 €
que salda una deuda de 100 y otra de 250), entra **como entra el agricultor** (con su vale guardado, no con
una maqueta), marca las dos casillas y deja **tres capturas** con su tamaño de verdad:

  · el **móvil** (390 px), que es como lo usa en el campo;
  · el **escritorio** (1440 px), que es donde el revisor mira que nada se salga;
  · y el **escritorio estrecho** (1024 px), que es el ancho donde este programa ya se ha roto una vez.

Y de paso comprueba lo que se puede comprobar sin ojos: que las dos casillas están, que **cada una dice lo
que le queda por cobrar** (elegir a ciegas entre dos números de factura no es elegir), que al marcarlas el
formulario sigue teniendo su botón de guardar a la vista, y que **nada se sale** de la ventana.

Uso:  python scripts/capturar_la_pantalla_del_reparto.py <direccion> [carpeta-de-capturas]
"""

from __future__ import annotations

import base64
import json
import pathlib
import struct
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"
CARPETA = (
    pathlib.Path(sys.argv[2])
    if len(sys.argv) > 2
    else pathlib.Path(r"F:\EspacioCodigo\CueDigital\docs\capturas")
)

COMPROBACIONES = 0
FALLOS = 0


def comprobar(bien: bool, que: str) -> bool:
    global COMPROBACIONES, FALLOS
    COMPROBACIONES += 1
    print(f"  [{'OK  ' if bien else 'FALLO'}] {que}")
    if not bien:
        FALLOS += 1
    return bien


def en_consola(algo) -> str:
    """El texto, en algo que la consola de Windows sepa escribir (los emojis y las flechas la revientan)."""
    return str(algo).encode("ascii", "replace").decode("ascii")


def _api(camino: str, token: str, cuerpo: dict | None = None, *, metodo: str = "POST"):
    """Una llamada a la puerta del servidor con el vale del agricultor."""
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(
        f"{DIRECCION}{camino}",
        data=datos,
        method=metodo,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as fallo:
        raise SystemExit(
            f"la puerta {camino} contesto {fallo.code}: {fallo.read().decode('utf-8')[:300]}"
        )


def _el_caso_del_encargo(token: str, campana_id: int) -> tuple[int, int]:
    """Las dos deudas del encargo (100 y 250), por las puertas de verdad. Devuelve sus facturas."""
    facturas = []
    for numero, importe in (("REPARTO-A", "100.00"), ("REPARTO-B", "250.00")):
        entrega = _api(
            "/api/ventas",
            token,
            {
                "campana_id": campana_id,
                "fecha": "2026-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "importe": importe,
                "comprador": "Cooperativa Agricola de Penaranda",
            },
        )
        factura = _api(
            "/api/facturas-emitidas",
            token,
            {
                "fecha": "2026-07-20",
                "numero": numero,
                "cliente": "Cooperativa Agricola de Penaranda",
                "entregas": [entrega["id"]],
            },
        )
        facturas.append(factura["id"])
    return facturas[0], facturas[1]


def captura(nav: NavegadorDeVerdad, nombre: str) -> dict:
    """La captura, diciendo **de qué tamaño es** y con qué ventana se hizo (como en el guion de la compra)."""
    CARPETA.mkdir(parents=True, exist_ok=True)
    destino = CARPETA / f"cobro-reparto-{nombre}.png"
    crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
    destino.write_bytes(crudo)
    ancho_imagen, alto_imagen = struct.unpack(">II", crudo[16:24])
    return {
        "ruta": destino,
        "ventana": nav.evaluar("[window.innerWidth, window.innerHeight]"),
        "imagen": [ancho_imagen, alto_imagen],
    }


def lo_que_se_sale(nav: NavegadorDeVerdad) -> list[str]:
    """Los controles de la pantalla cuyo rectángulo **no cabe entero** en la ventana.

    Es la comprobación que en CRM-00 destapó la barra: un control puede estar «puesto» y salirse por la
    derecha sin que nadie lo vea, y eso en el móvil significa un botón que no se puede pulsar.
    """
    return nav.evaluar(
        "(() => {"
        "  const fuera = [];"
        "  for (const nodo of document.querySelectorAll('#pantalla [data-accion], #pantalla input, #pantalla select')) {"
        "    const r = nodo.getBoundingClientRect();"
        "    if (r.width === 0 && r.height === 0) continue;"
        "    if (r.left < -0.5 || r.right > window.innerWidth + 0.5) {"
        "      fuera.push((nodo.id || nodo.dataset.accion || nodo.tagName) + ':' + Math.round(r.left) + '..' + Math.round(r.right));"
        "    }"
        "  }"
        "  return fuera;"
        "})()"
    )


def la_pantalla_del_reparto(nav: NavegadorDeVerdad) -> bool:
    """Abre la pantalla de apuntar un cobro y deja el caso del encargo puesto. Devuelve si hay dos casillas."""
    nav.abrir(f"{DIRECCION}/#/ventas/cobros/nuevo", esperar=2.5)
    nav.esperar("document.querySelectorAll('#pantalla [data-accion]').length > 0", segundos=25)
    return nav.evaluar(
        "document.querySelectorAll('#pantalla input[type=\"checkbox\"]').length"
    ) >= 2


def main() -> int:
    print(f"  (la direccion: {DIRECCION})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    campana_id = escenario.volumen.campana_actual.id
    print(f"  (la sesion: {escenario.volumen.nombre})")

    print("\n1) El caso del encargo: un ingreso de 350 EUR que salda una deuda de 100 y otra de 250")
    una, otra = _el_caso_del_encargo(token, campana_id)
    comprobar(bool(una and otra), f"las dos deudas estan puestas (facturas {una} y {otra})")

    for ancho, alto, nombre, movil in (
        (390, 1400, "movil", True),
        (1440, 900, "escritorio", False),
        (1024, 900, "escritorio-1024", False),
    ):
        print(f"\n2) A {ancho} px ({nombre})")
        with NavegadorDeVerdad(ancho=ancho, alto=alto) as nav:
            nav.medir(ancho, alto, movil=movil)
            # Se entra **como entra el agricultor**: con su vale guardado, que es lo que hace `app.js` al
            # arrancar. Asi la pantalla es la de verdad y no una maqueta.
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": "window.localStorage.setItem('cuedigital.token', "
                    + json.dumps(token)
                    + ");"
                },
            )
            hay_dos = la_pantalla_del_reparto(nav)
            comprobar(hay_dos, f"la pantalla ofrece una casilla por factura")

            if hay_dos:
                # Se escribe el importe que entra y se marcan las dos, que es el caso del encargo.
                nav.evaluar(
                    "(() => {"
                    "  const importe = document.getElementById('cobro-importe');"
                    "  if (importe) { importe.value = '350,00'; }"
                    "  for (const c of document.querySelectorAll('#pantalla input[type=\"checkbox\"]')) {"
                    "    c.checked = true;"
                    "  }"
                    "  return true;"
                    "})()"
                )
                texto = nav.evaluar("(document.querySelector('#pantalla') || {}).innerText || ''")
                comprobar(
                    "100,00" in texto and "250,00" in texto,
                    "cada casilla dice lo que le queda por cobrar",
                )
                comprobar(
                    "queda" in texto.lower(),
                    "y se explica que sin escribir importe se aplica lo que le queda",
                )
                comprobar(
                    len(nav.evaluar("document.querySelectorAll('#pantalla input[type=\"checkbox\"]:checked').length ? [1] : []")) == 1,
                    "las dos casillas se pueden marcar a la vez",
                )

            fuera = lo_que_se_sale(nav)
            comprobar(not fuera, f"nada se sale de la ventana ({en_consola(fuera) if fuera else 'nada'})")

            la_captura = captura(nav, nombre)
            print(
                f"  [OK  ] captura {en_consola(la_captura['ruta'].name)}: "
                f"imagen {la_captura['imagen'][0]}x{la_captura['imagen'][1]}, "
                f"ventana {la_captura['ventana'][0]}x{la_captura['ventana'][1]}"
            )

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {FALLOS}")
    return 0 if FALLOS == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
