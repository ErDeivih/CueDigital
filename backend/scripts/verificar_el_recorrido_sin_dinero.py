"""**El recorrido de quien trabaja SIN VER EL DINERO** — el ayudante (18/10/2026).

### Lo que la revision dejo dicho, y lo que faltaba comprobar

*La revision independiente demostro dos cosas de interfaz y una de servidor:*

  · ***el panel daba el dinero sin la capacidad economica*** -ya no lo da-;
  · ***la interfaz ofrecia siete acciones que escriben*** a quien no puede escribir -ya no-;
  · ***y el servidor si denegaba las siete*** -comprobado, con diez pruebas-.

*Las tres estan probadas por la suite, pero **en el servidor y en el componente**. **Lo que no estaba
probado es la pantalla de verdad, con una cuenta de verdad**: que el dinero no se vea y que los botones
no se pinten. Y eso no se puede probar con `renderToStaticMarkup`: `app.js` decide al montar, y la
pantalla de verdad es la unica que dice lo que el agricultor va a ver.*

### Que se anda, y por que asi

  1. Se crea la finca del titular **con datos dentro** -tierras, gastos, contactos, papeles-.
  2. Se da de alta **otra cuenta** y se la mete en la finca **por la puerta que existe**:
     `POST /api/fincas/quien-entra`. *Y esa puerta concede **AYUDANTE***, que es exactamente el papel
     del contrato: **puede escribir y no puede ver el dinero**.
  3. Se entra **con el vale del ayudante**, cambiado a la finca del titular
     (`POST /api/fincas/cambiar`, que devuelve un vale nuevo porque el vale dice en que finca se esta).
  4. Se contrasta **la puerta y la pantalla**: lo que dice `/api/panel` y lo que se ve en el inicio.

### ***Y por que NO se prueba «consulta»***

*Porque **no hay puerta que la conceda**: `POST /quien-entra` da siempre `AYUDANTE` -se supo leyendo la
puerta, no adivinando-. La consulta -`puede_modificar` **y** economico, los dos en falso- la cubre la
suite con `_sin_capacidad`, que es **mas estricta** que la consulta real. **Que no haya puerta para
concederla es una decision de producto, no un defecto de esta estabilizacion**, y queda dicha.*

Uso:
    python scripts/verificar_el_recorrido_sin_dinero.py [direccion]

*Sin direccion **se levanta su propio servidor** -base temporal, puerto libre-, para poder andarlo con
un comando y sin tocar la base del agricultor.*
"""

from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import capturar_la_pantalla_del_reparto as _el_de_la_captura  # noqa: E402

_api = _el_de_la_captura._api
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

BACKEND = pathlib.Path(__file__).resolve().parents[1]
PYTHON = BACKEND.parent / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = pathlib.Path(sys.executable)

COMPROBACIONES = 0
FALLOS: list[str] = []

# ***Las siete que la revision reprodujo***, por su accion -el nombre que llevan en el HTML-.
LAS_SIETE = [
    "fusion-hacer",
    "fusion-deshacer",
    "contacto-borrar-si",
    "contacto-nota",
    "contacto-baja",
    "banco-deshacer",
    "bandeja-confirmar",
]


def comprobar(bien: bool, que: str, esperaba: str = "", encontre: str = "") -> bool:
    global COMPROBACIONES
    COMPROBACIONES += 1
    if bien:
        print(f"  [OK   ] {que}")
    else:
        print(f"  [FALLO] {que}")
        if esperaba or encontre:
            print(f"          esperaba : {esperaba}")
            print(f"          encontre : {encontre[:400]}")
        FALLOS.append(que)
    return bien


def _sin_vale(direccion: str, camino: str, cuerpo: dict) -> dict:
    """**Una llamada que no lleva vale**: el alta de una cuenta, que es lo unico que va sin sesion."""
    peticion = urllib.request.Request(
        f"{direccion}{camino}",
        data=json.dumps(cuerpo).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(peticion, timeout=120) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def el_texto(nav) -> str:
    return nav.evaluar("document.querySelector(\'#pantalla\').innerText") or ""


def el_html(nav) -> str:
    return nav.evaluar("document.querySelector(\'#pantalla\').innerHTML") or ""


def andar(direccion: str) -> int:
    # ***La direccion, tambien para `_api`*** (18/10/2026): *ese ayudante usa **su** global, que sale de
    # `sys.argv`; sin esto, el guion levantaria su servidor en un puerto libre y hablaria al 8029 -el de otro
    # guion-. Se engancha aqui, que es donde se sabe la direccion de verdad.*
    _el_de_la_captura.DIRECCION = direccion

    print(f"== El recorrido de quien trabaja sin ver el dinero  ({direccion}) ==")
    escenario = preparar(direccion)
    el_titular = escenario.volumen
    print(f"  la finca del titular: {el_titular.explotacion_id}, con {len(escenario.gastos)} gastos")

    marca = f"{int(time.time())}-{os.getpid()}"
    correo = f"ayudante-{marca}@ejemplo.test"
    clave = "una-clave-larga"

    print("\n1. SE DA DE ALTA OTRA CUENTA Y SE LA METE EN LA FINCA")
    la_cuenta = _sin_vale(
        direccion,
        "/api/cuenta/registro",
        {
            "nombre": "El ayudante de la prueba",
            "correo": correo,
            "clave": clave,
            "explotacion": {"nombre": "La finca del ayudante", "nif": "12345678Z"},
        },
    )
    comprobar(bool(la_cuenta.get("token")), "la cuenta nueva tiene su vale")
    quien_entra = _api("/api/fincas/quien-entra", el_titular.token, {"correo": correo}, metodo="POST")
    los_de_la_finca = [str(x) for x in json.dumps(quien_entra, ensure_ascii=False).split('"')]
    comprobar(correo in los_de_la_finca, "***y entra en la finca del titular***", encontre=str(quien_entra)[:300])

    print("\n2. Y SE PONE A TRABAJAR EN LA FINCA DEL TITULAR")
    el_cambio = _api(
        "/api/fincas/cambiar",
        la_cuenta["token"],
        {"explotacion_id": el_titular.explotacion_id},
        metodo="POST",
    )
    su_vale = (el_cambio or {}).get("token") or ""
    comprobar(bool(su_vale), "***con un vale nuevo, que ya dice en que finca esta***", encontre=str(el_cambio)[:300])
    if not su_vale:
        raise SystemExit("sin vale no se puede seguir")

    print("\n3. LO QUE DICE LA PUERTA DEL PANEL")
    su_panel = _api("/api/panel", su_vale, metodo="GET")
    if not isinstance(su_panel, dict):
        raise SystemExit(f"la puerta no ha devuelto el panel: {su_panel!r}")
    las_metricas = su_panel.get("las_metricas") or []
    comprobar(
        not any(una["clave"] == "gastos" for una in las_metricas),
        "***la metrica de gastos NO viene***",
        encontre=str([una["clave"] for una in las_metricas]),
    )
    el_panel_crudo = json.dumps(su_panel, ensure_ascii=False)
    comprobar("EUR" not in el_panel_crudo, "***ni la unidad del dinero***", encontre=el_panel_crudo[:400])
    comprobar(
        any(una["clave"] == "superficie" for una in las_metricas),
        "***y el panel agronomico SI viene*** -no se queda sin panel-",
        encontre=str([una["clave"] for una in las_metricas]),
    )

    print("\n4. Y LO QUE SE VE EN LA PANTALLA")
    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem(\'cuedigital.token\', " + json.dumps(su_vale) + ");"},
            )
            nav.abrir(f"{direccion}/", esperar=3.0)
            nav.esperar(
                "document.querySelector(\'#pantalla\').innerText.includes("
                + json.dumps(su_panel["textos"]["titulo"])
                + ")",
                segundos=30,
            )
            texto = el_texto(nav)
            html = el_html(nav)
            comprobar(
                su_panel["textos"]["titulo"] in texto,
                "***el inicio abre con la cuenta del ayudante***",
                encontre=texto[:300],
            )
            comprobar("EUR" not in texto, "***y NO dice ni un EUR***", encontre=texto[:600])
            comprobar(
                "123,45" not in texto and "123.45" not in texto,
                "***ni el importe de ningun gasto***",
                encontre=texto[:600],
            )
            for accion in LAS_SIETE:
                comprobar(
                    f'data-accion="{accion}"' not in html,
                    f"***«{accion}» NO se pinta***",
                    encontre=html[:400],
                )
            # ***Y lo que no es dinero se sigue viendo***: *la pantalla no se queda vacia.*
            comprobar(
                any(una["titulo"] in texto for una in las_metricas if una["clave"] == "superficie"),
                "***y la superficie SI se ve***",
                encontre=texto[:600],
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
    """*La base del agricultor no se toca: se levanta un servidor con una base temporal.*"""
    puerto = un_puerto_libre()
    direccion = f"http://127.0.0.1:{puerto}"
    # ***`mkdtemp` y limpieza a mano*** (18/10/2026): *en Windows la base sigue abierta un instante despues de
    # matar el servidor, y `TemporaryDirectory` revienta al limpiar con un `PermissionError` que **tapa el
    # resultado de la prueba**. Lo que falle es la limpieza, no el recorrido.*
    temporal = tempfile.mkdtemp(prefix="cuedigital-sin-dinero-")
    try:
        base = pathlib.Path(temporal) / "prueba.db"
        entorno = dict(os.environ)
        entorno["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        servidor = subprocess.Popen(  # noqa: S603
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(puerto)],
            cwd=str(BACKEND),
            env=entorno,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(120):
                try:
                    with urllib.request.urlopen(f"{direccion}/api/interfaz", timeout=2):
                        break
                except (urllib.error.URLError, OSError):
                    if servidor.poll() is not None:
                        raise SystemExit("el servidor no ha arrancado")
                    time.sleep(0.5)
            return andar(direccion)
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
        return andar(sys.argv[1])
    return con_su_propio_servidor()


if __name__ == "__main__":
    raise SystemExit(main())
