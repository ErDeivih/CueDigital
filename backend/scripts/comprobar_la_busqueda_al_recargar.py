"""¿Quién pierde el texto de la búsqueda al recargar: la pantalla o mi espera? (07/10/2026).

**Por qué existe.** En una pasada del recorrido, la comprobación *«recargar la búsqueda la deja con lo que se
buscaba»* falló **una vez**: el cuadro salió vacío. No se ha vuelto a repetir, y eso no es una explicación.
David pidió investigarlo -no descartarlo porque no se repita- y determinar **si falla la aplicación o la espera
del instrumento**.

**Cómo lo decide.** En vez de mirar una sola vez al final, se **sondea** cada 50 ms y se guarda **la secuencia
de estados** `(dirección, cuadro, tarjetas)`. Si el cuadro se rellena **después** de aparecer los resultados
-secuencia `tarjetas>0` con `cuadro=null`, y luego `cuadro` con el texto- entonces la espera del recorrido
-que espera a las tarjetas y **luego** lee el cuadro- se está cumpliendo **antes de tiempo**, y el fallo es del
instrumento. Si el cuadro **no llega a rellenarse nunca**, el fallo es de la pantalla.

**Con latencia** (`Network.emulateNetworkConditions` por CDP, sin tocar la aplicación) para provocar la carrera:
es cuando el servidor tarda cuando se ve quién llega antes.

Uso:  python scripts/comprobar_la_busqueda_al_recargar.py http://127.0.0.1:8129 [segundos-por-paso]
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8129"
SEGUNDOS = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
CADA = 0.05


def la_traza(nav: NavegadorDeVerdad, etiqueta: str, segundos: float = SEGUNDOS) -> list[dict]:
    """Sondea y devuelve **la secuencia de estados distintos**: dirección, cuadro y tarjetas."""
    visto: list[dict] = []
    final = time.time() + segundos
    while time.time() < final:
        try:
            estado = nav.evaluar(
                "(() => ({"
                " direccion: String(location.hash).slice(0, 60),"
                " cuadro: ('#buscar_global' && document.querySelector('#buscar_global'))"
                " ? document.querySelector('#buscar_global').value : null,"
                " tarjetas: document.querySelectorAll('#pantalla .tarjeta').length"
                "}))()"
            )
        except Exception as exc:  # la pestaña puede estar navegando: se anota y se sigue
            estado = {"error": str(exc)[:40]}
        if not visto or visto[-1] != estado:
            visto.append(estado)
            print(f"    +{time.time() - (final - segundos):5.2f}s  {estado}")
        time.sleep(CADA)
    print(f"  [{etiqueta}] {len(visto)} estados distintos en {segundos:.0f}s")
    return visto


def main() -> int:
    # **Con sesión, como el recorrido** (07/10/2026): la primera versión de esta sonda **no iniciaba sesión** y
    # medía una pantalla que no se pinta -el cuadro salía `None`-, que no es el fallo que se investiga. Se
    # prepara el mismo escenario que usa el recorrido y se mete su token en el navegador, que es como entra él:
    # el recorrido lo hace con `localStorage['cuedigital.token']`, comprobado en su código.
    import datos_representativos as datos

    carpeta = pathlib.Path(tempfile.mkdtemp(prefix="cuedigital-busqueda-"))
    volumen, escenario = datos._la_del_volumen(  # noqa: SLF001 — es el mismo preparador que usa el recorrido
        DIRECCION, f"busqueda{int(time.time())}", carpeta, False
    )
    print(f"  la sesión: {volumen.nombre}, con {len(escenario.tierras)} tierras")

    with NavegadorDeVerdad(ancho=1280, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(volumen.token) + ");"},
        )
        nav.abrir(f"{DIRECCION}/#/tierras", esperar=2.0)
        nav.esperar("Boolean(document.querySelector('#buscar_tierra_mis_cosas'))", segundos=25)
        # **Consultas que existen de verdad** (07/10/2026): la primera versión intentaba leer el alias de una
        # tierra de la lista y **no acerté con el selector**, así que la traza no llegó a correr —y la sonda lo
        # dijo, en vez de sacar conclusiones de la nada—. Con una letra suelta se busca algo que sale seguro
        # —«a» está en casi cualquier alias— y el cuadro se comporta igual que con un alias entero, que es lo
        # que se está investigando.
        consultas = [
            ("una letra que sale seguro", "a"),
            ("una palabra corriente", "de"),
            ("algo sin resultados", "zzzz-no-existe-zzzz"),
        ]
        for etiqueta, consulta in consultas:
            la_direccion = f"{DIRECCION}/#/buscar?texto={urllib.parse.quote(consulta)}"
            print(f"\n=== {etiqueta}: {consulta!r}")
            # **Sin pausa arbitraria**: se abre y se sondea desde el primer instante.
            nav.abrir(la_direccion, esperar=0.0)
            la_traza(nav, "abrir la dirección")
            # Y recargando la misma página.
            nav.evaluar("(() => { location.reload(); return null; })()")
            la_traza(nav, "recargar")
            # Y con el servidor lento: latencia de 900 ms por CDP.
            nav.orden("Network.enable")
            nav.orden(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": 900,
                    "downloadThroughput": -1,
                    "uploadThroughput": -1,
                },
            )
            nav.abrir(la_direccion, esperar=0.0)
            la_traza(nav, "abrir con latencia de 900 ms", segundos=SEGUNDOS + 6.0)
            nav.orden("Network.emulateNetworkConditions", {"offline": False, "latency": 0,
                                                           "downloadThroughput": -1,
                                                           "uploadThroughput": -1})

        # Atrás y adelante, que es lo que hace el navegador con el historial.
        print("\n=== Atrás / Adelante")
        nav.abrir(f"{DIRECCION}/#/tierras", esperar=1.5)
        nav.abrir(f"{DIRECCION}/#/buscar?texto={urllib.parse.quote(consultas[0][1])}", esperar=0.0)
        la_traza(nav, "la búsqueda, recién abierta")
        nav.evaluar("(() => { history.back(); return null; })()")
        la_traza(nav, "Atrás")
        nav.evaluar("(() => { history.forward(); return null; })()")
        la_traza(nav, "Adelante")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
