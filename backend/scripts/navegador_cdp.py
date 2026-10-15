"""Un navegador de verdad, manejado de verdad.

## Por qué existe este fichero

`comprobar_en_un_navegador.py` abre Chrome con **`--dump-dom`**: carga la página, deja que corra el
JavaScript y vuelca el HTML. Eso sirve para lo que ese guion comprueba (que las pantallas se dibujan, que
los datos llegan y que no saltan errores), pero **no puede hacer dos cosas que el encargo pide**:

  · **Pulsar el teclado**. Un `KeyboardEvent` inventado con `dispatchEvent` no mueve el foco: quien mueve
    el foco es el navegador, y solo obedece a una tecla **de verdad**.
  · **Ver una descarga**. Cuando el agricultor pulsa «EXPORTAR», el navegador guarda un fichero en su
    carpeta de descargas. Eso no aparece en el DOM, así que un volcado de HTML no puede distinguir
    «descargó» de «no hizo nada».

Las dos cosas las sabe hacer el **protocolo de depuración de Chrome (CDP)**, que es lo que hay aquí: se
abre Chrome con `--remote-debugging-port`, se habla con él por un websocket y se le mandan órdenes
(`Input.dispatchKeyEvent` para las teclas, `Browser.setDownloadBehavior` para las descargas,
`Emulation.setDeviceMetricsOverride` para medir con un tamaño y una escala concretos).

## Lo que NO es

No sustituye a `comprobar_en_un_navegador.py` (que sigue siendo el que recorre las 16 pantallas largas y
mira el HTML). Esto es **la pieza de abajo**, para las comprobaciones que necesitan un navegador que
obedezca al teclado y a las descargas.

## Cómo se usa

```python
from navegador_cdp import NavegadorDeVerdad

with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
    nav.abrir("http://127.0.0.1:8011/#/tierras")
    nav.esperar("document.querySelector('[data-accion=\"mis-cosas\"]') !== null")
    nav.tecla("Tab")                                   # una tecla de verdad
    print(nav.evaluar("document.activeElement.outerHTML"))
    nav.escribir("El Prado")                           # texto, como si se tecleara
    nav.descargas_en(r"C:\\temp\\descargas")            # a partir de aquí, lo que se descargue va ahí
    nav.pulsar('[data-accion="cuaderno-exportar"]')     # un clic de verdad (no un dispatchEvent)
```

Si no hay navegador instalado, `NavegadorDeVerdad` **lo dice y no revienta**: quien lo use decide si eso
es un fallo de la comprobación o una comprobación que no se puede hacer en esa máquina.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

NAVEGADORES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


class SinNavegador(RuntimeError):
    """No hay ningún navegador instalado en esta máquina."""


def el_navegador() -> str | None:
    for ruta in NAVEGADORES:
        if pathlib.Path(ruta).exists():
            return ruta
    return None


def _un_puerto_libre() -> int:
    with socket.socket() as hueco:
        hueco.bind(("127.0.0.1", 0))
        return int(hueco.getsockname()[1])


class NavegadorDeVerdad:
    """Chrome sin ventana, manejado por CDP.

    Se entra y se sale con `with`: al salir se cierra el navegador y se borra el perfil de usar y tirar.
    """

    def __init__(
        self,
        *,
        ancho: int = 1440,
        alto: int = 900,
        escala: float = 1.0,
        ruta: str | None = None,
    ) -> None:
        """`escala` es la **escala del dispositivo**: 2.0 es la pantalla de Windows al 200 %. No es lo
        mismo que el zoom del navegador, y por eso las comprobaciones dicen cuál de las dos usan."""
        self.ruta = ruta or el_navegador()
        if self.ruta is None:
            raise SinNavegador(
                "No hay Chrome ni Edge instalado en esta máquina, así que no se puede comprobar "
                "en un navegador de verdad."
            )
        self.ancho = ancho
        self.alto = alto
        self.escala = escala
        self.puerto = _un_puerto_libre()
        self.perfil = tempfile.mkdtemp(prefix="cuedigital-cdp-")
        self.proceso: subprocess.Popen | None = None
        self._websocket = None
        self._bucle: asyncio.AbstractEventLoop | None = None
        self._secuencia = 0
        self._siguiente_id = 1
        self.sesion: str | None = None
        self._descargas: str | None = None

    # ---------------------------------------------------------------- abrir y cerrar

    def __enter__(self) -> "NavegadorDeVerdad":
        orden = [
            self.ruta,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            f"--user-data-dir={self.perfil}",
            f"--remote-debugging-port={self.puerto}",
            f"--window-size={self.ancho},{self.alto}",
        ]
        if self.escala != 1.0:
            # **La escala del dispositivo, que es lo que hace Windows** al poner la pantalla al 200 %:
            # cada píxel lógico pasa a ocupar dos físicos. No es el zoom del navegador (ver `zoom`).
            orden.append(f"--force-device-scale-factor={self.escala}")
        orden.append("about:blank")
        self.proceso = subprocess.Popen(orden, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._esperar_al_puerto()
        # **Un solo bucle de sucesos para toda la vida del objeto, y el websocket vive dentro de él.** Con
        # un `asyncio.run` por orden, la conexión se queda atada al bucle que la abrió: al cerrarse ese
        # bucle, la siguiente orden falla con «Event loop is closed» (costó una vuelta verlo).
        self._bucle = asyncio.new_event_loop()
        self._bucle.run_until_complete(self._conectar())
        return self

    def _matar_los_suyos(self) -> None:
        """Mata los procesos del navegador **de esta instancia**, y solo esos.

        **Por que hace falta, si `__exit__` ya termina el proceso** (14/10/2026): `subprocess.Popen`
        lanza el **lanzador** de Chrome, y **Chrome se re-ejecuta a si mismo**: el lanzador muere solo y
        `terminate()` se lleva al mensajero, mientras **el navegador sigue vivo**. Se acumularon **diez**
        en una sesion, y eso hace fallar `tests/test_el_recorrido_se_anda.py`, que **lo dice en su propio
        docstring**: «con otra sesion de navegador en marcha… dos navegadores a la vez se estorban».

        **Se mata por el PERFIL** (`--user-data-dir`), que es unico de cada instancia: asi no se toca
        ningun otro navegador de la maquina -y en particular **ninguno del dueno**-. Se eligio esto y no
        matar por nombre de proceso justo por eso.
        """
        if not self.perfil:
            return
        try:
            if sys.platform.startswith("win"):
                guion = (
                    "Get-CimInstance Win32_Process | "
                    "Where-Object { $_.CommandLine -like '*" + str(self.perfil) + "*' } | "
                    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", guion],
                    capture_output=True,
                    check=False,
                    timeout=30,
                )
            else:
                subprocess.run(["pkill", "-f", str(self.perfil)], capture_output=True, check=False, timeout=30)
        except (OSError, subprocess.SubprocessError):
            # Que no se pueda limpiar **no puede tumbar un recorrido que ya termino bien**: se deja
            # dicho y se sigue. Antes esto no existia y el resultado era peor: los navegadores vivos.
            print("  (no se han podido cerrar los navegadores de esta instancia: se dejan)")

    def __exit__(self, *_excepcion) -> None:
        self.cerrar()

    def cerrar(self) -> None:
        if self._websocket is not None and self._bucle is not None:
            try:
                self._bucle.run_until_complete(self._websocket.close())
            except Exception:
                pass
            self._websocket = None
        if self._bucle is not None:
            try:
                self._bucle.close()
            except Exception:
                pass
            self._bucle = None
        if self.proceso is not None:
            self.proceso.terminate()
            try:
                self.proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proceso.kill()
            self.proceso = None
        self._matar_los_suyos()
        shutil.rmtree(self.perfil, ignore_errors=True)

    def _esperar_al_puerto(self, segundos: float = 20.0) -> None:
        limite = time.time() + segundos
        while time.time() < limite:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.puerto}/json/version", timeout=1):
                    return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("el navegador no ha abierto su puerto de depuración")

    # ---------------------------------------------------------------- hablar con él

    def _destino(self) -> str:
        """El websocket de la pestaña que hay abierta (no el del navegador entero)."""
        with urllib.request.urlopen(f"http://127.0.0.1:{self.puerto}/json/list", timeout=5) as respuesta:
            destinos = json.loads(respuesta.read().decode("utf-8"))
        for destino in destinos:
            if destino.get("type") == "page" and destino.get("webSocketDebuggerUrl"):
                return destino["webSocketDebuggerUrl"]
        raise RuntimeError("el navegador no tiene ninguna pestaña abierta")

    async def _conectar(self):
        if self._websocket is None:
            import websockets

            self._websocket = await websockets.connect(self._destino(), max_size=64 * 1024 * 1024)
        return self._websocket

    async def _orden(self, metodo: str, parametros: dict | None = None) -> dict:
        websocket = await self._conectar()
        self._siguiente_id += 1
        mio = self._siguiente_id
        await websocket.send(json.dumps({"id": mio, "method": metodo, "params": parametros or {}}))
        while True:
            crudo = await asyncio.wait_for(websocket.recv(), timeout=60)
            mensaje = json.loads(crudo)
            if mensaje.get("id") == mio:
                if "error" in mensaje:
                    raise RuntimeError(f"{metodo}: {mensaje['error']}")
                return mensaje.get("result", {})

    def orden(self, metodo: str, parametros: dict | None = None) -> dict:
        """Una orden suelta al navegador (para lo que no tenga ayudante aquí)."""
        if self._bucle is None:
            raise RuntimeError("el navegador no está abierto: se usa dentro de un `with`")
        return self._bucle.run_until_complete(self._orden(metodo, parametros))

    # ---------------------------------------------------------------- lo de todos los días

    def abrir(self, url: str, *, esperar: float = 0.8) -> None:
        self.orden("Page.enable")
        self.orden("Page.navigate", {"url": url})
        time.sleep(esperar)

    def evaluar(self, expresion: str):
        """Ejecuta JavaScript en la página y devuelve el valor (ya convertido a algo de Python)."""
        resultado = self.orden(
            "Runtime.evaluate",
            {
                "expression": expresion,
                "returnByValue": True,
                "awaitPromise": True,
                "userGesture": True,
            },
        )
        if resultado.get("exceptionDetails"):
            raise RuntimeError(f"el JavaScript ha fallado: {resultado['exceptionDetails']}")
        return resultado.get("result", {}).get("value")

    def esperar(self, condicion: str, *, segundos: float = 10.0, cada: float = 0.1) -> bool:
        """Espera a que se cumpla una condición en la página. Devuelve si se cumplió."""
        limite = time.time() + segundos
        while time.time() < limite:
            try:
                if self.evaluar(f"Boolean({condicion})"):
                    return True
            except Exception:
                pass
            time.sleep(cada)
        return False

    def tecla(self, nombre: str, *, mayusculas: bool = False) -> None:
        """Una tecla **de verdad**, de las que mueven el foco y activan un botón.

        Sirve `Tab`, `Enter`, `Escape`, `ArrowDown`, `ArrowUp`, `Backspace`, `Space` o una letra suelta
        (`"a"`). Las teclas con modificador (Shift+Tab) se piden con `mayusculas=True`.
        """
        codigos = {
            "Tab": (9, "Tab"),
            "Enter": (13, "Enter"),
            "Escape": (27, "Escape"),
            "Space": (32, "Space"),
            "Backspace": (8, "Backspace"),
            "ArrowDown": (40, "ArrowDown"),
            "ArrowUp": (38, "ArrowUp"),
            "ArrowLeft": (37, "ArrowLeft"),
            "ArrowRight": (39, "ArrowRight"),
            "Home": (36, "Home"),
            "End": (35, "End"),
        }
        if nombre in codigos:
            codigo, texto = codigos[nombre]
            comun = {
                "windowsVirtualKeyCode": codigo,
                "nativeVirtualKeyCode": codigo,
                "code": texto,
                "key": texto,
                "modifiers": 8 if mayusculas else 0,
            }
            # `rawKeyDown` y no `keyDown` para las teclas que no escriben nada: con `keyDown` el navegador
            # espera un carácter que no va a llegar.
            self.orden("Input.dispatchKeyEvent", {"type": "rawKeyDown", **comun})
            self.orden("Input.dispatchKeyEvent", {"type": "keyUp", **comun})
        else:
            # Una letra: se manda como texto, que es lo que hace el navegador al teclearla.
            self.orden("Input.insertText", {"text": nombre})
        time.sleep(0.05)

    def escribir(self, texto: str) -> None:
        """Escribe en lo que tenga el foco, como si se tecleara."""
        self.orden("Input.insertText", {"text": texto})
        time.sleep(0.05)

    def pulsar(self, selector: str) -> None:
        """Un clic **de verdad** en el centro de un elemento (no un `dispatchEvent` inventado).

        Se busca el elemento, se mira dónde está en pantalla y se manda el clic ahí: eso dispara lo mismo
        que el dedo del agricultor, incluido el `click` que el navegador genera solo.

        **Se elige el primer elemento que se VE, y si ninguno se ve, se falla** (07/10/2026). Antes se
        cogía el primero que casara con el selector, y eso hizo perder dos vueltas: hay acciones que se
        pintan en sitios que no se ven (el botón de una confirmación anterior, por ejemplo), y pulsar uno
        de esos es mandar el clic a la esquina (0,0) —donde no hay nada— **sin que el guion se enterara**.
        Un clic que no llega a ninguna parte tiene que doler, no pasar en silencio.
        """
        centro = self.evaluar(
            f"""(() => {{
                const todos = [...document.querySelectorAll({json.dumps(selector)})];
                if (!todos.length) return null;
                const el = todos.find((uno) => uno.checkVisibility({{checkVisibilityCSS: true}}));
                if (!el) return {{oculto: true, cuantos: todos.length}};
                el.scrollIntoView({{block: "center"}});
                const caja = el.getBoundingClientRect();
                return {{x: caja.left + caja.width / 2, y: caja.top + caja.height / 2}};
            }})()"""
        )
        if not centro:
            raise RuntimeError(f"no hay ningún elemento que case con {selector!r}")
        if centro.get("oculto"):
            raise RuntimeError(
                f"{selector!r} casa con {centro['cuantos']} elemento(s) y ninguno se ve: "
                "no se puede pulsar lo que no está"
            )
        for tipo in ("mousePressed", "mouseReleased"):
            self.orden(
                "Input.dispatchMouseEvent",
                {
                    "type": tipo,
                    "x": centro["x"],
                    "y": centro["y"],
                    "button": "left",
                    "clickCount": 1,
                },
            )
        time.sleep(0.15)

    # ---------------------------------------------------------------- descargas

    def descargas_en(self, carpeta: str) -> None:
        """A partir de aquí, lo que se descargue se guarda en esa carpeta (y se puede mirar).

        Se pide por el dominio del **navegador** (`Browser.setDownloadBehavior`), que es el que manda sobre
        todas las pestañas; si esta versión de Chrome no lo acepta por esta conexión, se cae al de la
        página (`Page.setDownloadBehavior`), que hace lo mismo para la pestaña abierta. Costó una vuelta:
        pidiéndolo solo por la página, la orden no daba error y **no se descargaba nada**.
        """
        pathlib.Path(carpeta).mkdir(parents=True, exist_ok=True)
        self._descargas = carpeta
        try:
            self.orden(
                "Browser.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": carpeta, "eventsEnabled": True},
            )
        except RuntimeError:
            self.orden(
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": carpeta},
            )

    def lo_descargado(self, *, segundos: float = 15.0, nombre: str | None = None) -> pathlib.Path | None:
        """Espera a que aparezca el fichero descargado y lo devuelve.

        Se espera a que **deje de crecer** (un `.crdownload` a medias no es una descarga hecha) y, si se
        dice un `nombre`, a que sea ese. Devuelve `None` si no llegó nada: quien comprueba decide si eso
        es un fallo (casi siempre lo es).
        """
        if self._descargas is None:
            raise RuntimeError("antes de descargar hay que decir dónde: `descargas_en(carpeta)`")
        limite = time.time() + segundos
        anterior = -1
        while time.time() < limite:
            ficheros = [
                f
                for f in pathlib.Path(self._descargas).iterdir()
                if f.is_file() and not f.name.endswith(".crdownload")
            ]
            if nombre is not None:
                ficheros = [f for f in ficheros if f.name == nombre]
            if ficheros:
                tamano = max(f.stat().st_size for f in ficheros)
                if tamano > 0 and tamano == anterior:
                    return max(ficheros, key=lambda f: f.stat().st_mtime)
                anterior = tamano
            time.sleep(0.2)
        return None

    # ---------------------------------------------------------------- medir

    def medir(self, ancho: int, alto: int, *, escala: float = 1.0, movil: bool = False) -> None:
        """Pone la página en un tamaño y una escala concretos (para medir anchos sin abrir otra ventana)."""
        # **Y se apaga la cache del navegador, que es la mitad que no se ve** (14/10/2026). El servidor
        # sirve los ficheros de `web/` tal cual -`main.py` monta `StaticFiles`-, y el navegador se los
        # guarda: cuando un fichero de JavaScript cambia **entre dos vueltas** -y en esta casa los cambian
        # hasta tres agentes a la vez-, `abrir` puede estar sirviendo **el de antes**.
        #
        # **Se descubrio midiendo, no suponiendo**: el recorrido de la aplicabilidad fallo en un campo que
        # no encontraba, y al preguntarle **al servidor** por el fichero result que lo servia **nuevo**
        # mientras el navegador tenia el **viejo**. Lo peor de esto no es que un recorrido falle: es que
        # **puede pasar midiendo codigo viejo** y dar por bueno algo que ya no esta, que es la peor clase
        # de verde.
        #
        # Va aqui, en `medir`, porque es **lo primero que hace todo recorrido** y siempre antes de abrir
        # nada: asi lo arreglan todos, y no solo el que se dio cuenta.
        self.orden("Network.enable")
        self.orden("Network.setCacheDisabled", {"cacheDisabled": True})
        self.orden(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": ancho,
                "height": alto,
                "deviceScaleFactor": escala,
                "mobile": movil,
            },
        )
        time.sleep(0.3)

    def zoom(self, factor: float) -> None:
        """El **zoom del navegador** (el de Ctrl+«+»), que no es la escala del dispositivo.

        El zoom cambia los píxeles lógicos que caben en la ventana: al 200 %, una ventana de 1440 px ve la
        página como si midiera 720. Chrome lo expone por `Emulation.setPageScaleFactor` en su forma de
        pellizco; para el zoom de verdad lo que se puede hacer por protocolo es fijar la escala de la
        página, y **eso es lo que se documenta como tal** en la comprobación que lo use.
        """
        self.orden("Emulation.setPageScaleFactor", {"pageScaleFactor": factor})
        time.sleep(0.3)
