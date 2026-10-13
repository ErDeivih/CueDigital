"""El recorrido del conflicto de una nota, en un navegador de verdad (13/10/2026).

## Por qué existe

La revisión del dueño pidió, palabra por palabra: «guardar perdiendo la respuesta, editar, reintentar,
recibir 409, conservar el texto y guardar voluntariamente con otra clave; al recargar deben aparecer las
dos notas correctas». Eso **no se puede comprobar leyendo el código ni con dos llamadas seguidas a
`fetch`**: hay que perder la respuesta **de verdad** (que el servidor guarde la nota y que el navegador
no reciba nada), editar el campo **con el teclado**, volver a pulsar y mirar qué contesta el servidor y
qué enseña la pantalla.

## Cómo se pierde la respuesta (y por qué así)

Con el protocolo de depuración de Chrome (`Fetch.enable`, con `requestStage: "Response"` y el patrón de
`/notas`). El servidor **ya ha contestado** cuando llega `Fetch.requestPaused` —la petición salió y se
guardó la nota—, y lo que se tira es la respuesta: `Fetch.failRequest` con `errorReason: "Failed"` le
dice al navegador que esa petición falló. **No es una simulación**: la nota está en la base de datos y el
navegador ve un fallo de red, que es exactamente el caso que la revisión pidió reproducir.

Si `Fetch.failRequest` no se admitiera en la fase de respuesta, el guion lo dice y cae a
`Fetch.fulfillRequest` contestando un error (y lo deja escrito en el informe): lo que **no** hace es
fingirlo con dos llamadas seguidas.

## Por qué la intercepción va por su propia conexión

`NavegadorDeVerdad` habla CDP por un websocket y **descarta los sucesos** (`_orden` solo mira el mensaje
con su `id`). Si se activara `Fetch` en esa conexión, el suceso `Fetch.requestPaused` se perdería y la
petición se quedaría colgada para siempre. Aquí se abre **una segunda sesión** al mismo destino, en su
propio hilo y con su propio bucle de sucesos, para no tocar la conexión del navegador ni el fichero
`navegador_cdp.py`.

Uso:  python scripts/verificar_el_conflicto_de_una_nota.py <direccion>
"""

from __future__ import annotations

import asyncio
import base64
import json
import pathlib
import sys
import threading
import time
import urllib.request

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8350"
CARPETA = pathlib.Path(__file__).resolve().parents[2] / "docs" / "capturas"

EL_CONTACTO = "La prueba del conflicto de una nota"
TEXTO_1 = "Preguntar por el abono"
# Lo que se teclea **de verdad** al editar: se añade al final, que es lo que hace un dedo. Así el texto
# final se compone con el teclado y no se escribe de golpe con un `value =`.
LO_QUE_SE_ANADE = " y por el gasóleo"
TEXTO_2 = TEXTO_1 + LO_QUE_SE_ANADE  # «Preguntar por el abono y por el gasóleo»
EL_MENSAJE_DEL_CONFLICTO = "Esta acción ya se había guardado, pero con otro texto"
EL_MENSAJE_SIN_RESPUESTA = "No se ha podido. Prueba otra vez"


# ---------------------------------------------------------------------------
# La intercepción, en su propia sesión de CDP
# ---------------------------------------------------------------------------


class InterceptadorDeLaRespuesta:
    """Tira **la respuesta** de la primera petición que case, sin tocar la petición.

    Se activa por CDP en la fase de respuesta: cuando llega el suceso, la petición ya salió y el servidor
    ya contestó. Lo que se hace entonces es decirle al navegador que esa petición falló
    (`Fetch.failRequest`), así que el `fetch` de la página se resuelve con un error de red —la respuesta
    perdida— mientras que en el servidor la nota **sí está guardada**.
    """

    def __init__(self, puerto: int, trozo: str = "/notas") -> None:
        self.puerto = puerto
        self.trozo = trozo
        self.interceptadas: list[dict] = []
        self.ordenes: list[dict] = []
        self.fallos: list[str] = []
        self._listo = threading.Event()
        self._parar = threading.Event()
        self._hilo = threading.Thread(target=self._correr, daemon=True)
        self._id = 0
        self._ws = None
        self._nombres: dict[int, str] = {}

    # ------------------------------------------------------------------ desde fuera

    def el_destino(self) -> str:
        """El websocket de la pestaña abierta, preguntándolo al propio navegador."""
        with urllib.request.urlopen(f"http://127.0.0.1:{self.puerto}/json/list", timeout=5) as respuesta:
            destinos = json.loads(respuesta.read().decode("utf-8"))
        for destino in destinos:
            if destino.get("type") == "page" and destino.get("webSocketDebuggerUrl"):
                return destino["webSocketDebuggerUrl"]
        raise RuntimeError("el navegador no tiene ninguna pestaña abierta")

    def empezar(self) -> None:
        self._hilo.start()
        if not self._listo.wait(20):
            raise RuntimeError("la intercepción no ha llegado a activarse en 20 s")
        if self.fallos:
            raise RuntimeError(f"no se ha podido activar la intercepción: {self.fallos}")

    def esperar_una_intercepcion(self, segundos: float = 10.0) -> bool:
        limite = time.time() + segundos
        while time.time() < limite:
            if self.interceptadas:
                return True
            if self.fallos:
                return False
            time.sleep(0.1)
        return False

    def parar(self) -> None:
        """Al cerrar la conexión, el navegador levanta la intercepción: las demás peticiones pasan solas."""
        self._parar.set()
        if self._hilo.is_alive():
            self._hilo.join(timeout=6)


    # ------------------------------------------------------------------ el hilo

    def _correr(self) -> None:
        try:
            asyncio.run(self._bucle())
        except Exception as fallo:  # noqa: BLE001 — se cuenta, no se traga
            self.fallos.append(f"{type(fallo).__name__}: {fallo}")
            self._listo.set()

    async def _bucle(self) -> None:
        import websockets

        async with websockets.connect(self.el_destino(), max_size=64 * 1024 * 1024) as ws:
            self._ws = ws
            activacion = await self._preguntar(
                "Fetch.enable",
                {"patterns": [{"urlPattern": f"*{self.trozo}", "requestStage": "Response"}]},
            )
            if activacion.get("error"):
                self.fallos.append(f"Fetch.enable: {activacion['error']}")
            self._listo.set()
            while not self._parar.is_set():
                try:
                    crudo = await asyncio.wait_for(ws.recv(), timeout=0.3)
                except asyncio.TimeoutError:
                    continue
                except Exception as fallo:  # noqa: BLE001
                    if not self._parar.is_set():
                        self.fallos.append(f"se ha cortado la conexión: {fallo}")
                    break
                mensaje = json.loads(crudo)
                if mensaje.get("id") is not None:
                    self.ordenes.append(
                        {"metodo": self._cual(mensaje["id"]), "error": mensaje.get("error")}
                    )
                    continue
                if mensaje.get("method") == "Fetch.requestPaused":
                    await self._decidir(mensaje["params"])

    def _cual(self, identificador: int) -> str:
        return self._nombres.get(identificador, f"#{identificador}")

    async def _preguntar(self, metodo: str, parametros: dict) -> dict:
        """Manda una orden y espera **su** respuesta, sin perder los sucesos que lleguen mientras."""
        self._id += 1
        mio = self._id
        self._nombres[mio] = metodo
        await self._ws.send(json.dumps({"id": mio, "method": metodo, "params": parametros}))
        while True:
            crudo = await asyncio.wait_for(self._ws.recv(), timeout=20)
            mensaje = json.loads(crudo)
            if mensaje.get("id") == mio:
                return mensaje
            if mensaje.get("method") == "Fetch.requestPaused":
                await self._decidir(mensaje["params"])

    async def _decidir(self, params: dict) -> None:
        peticion = params.get("request", {})
        url = peticion.get("url", "")
        identificador = params["requestId"]
        if self.trozo not in url:
            await self._preguntar("Fetch.continueResponse", {"requestId": identificador})
            return
        # **Aquí ya hay respuesta del servidor**: la petición salió y se guardó. Se apunta lo que se ve
        # antes de tirarla, que es la prueba de que el servidor sí contestó.
        self.interceptadas.append(
            {
                "url": url,
                "metodo": peticion.get("method"),
                "tiene_estado": "responseStatusCode" in params,
                "estado_de_la_respuesta": params.get("responseStatusCode"),
                "error_de_la_respuesta": params.get("responseErrorReason"),
                "claves_del_suceso": sorted(params.keys()),
            }
        )
        respuesta = await self._preguntar(
            "Fetch.failRequest", {"requestId": identificador, "errorReason": "Failed"}
        )
        self.ordenes.append(
            {"metodo": "Fetch.failRequest", "error": respuesta.get("error"), "camino": "failRequest"}
        )
        if respuesta.get("error"):
            # Plan B, y se dice: si esta versión de Chrome no admite tirar una respuesta en la fase de
            # respuesta, se le contesta un error para que el `fetch` de la página falle igual.
            plan_b = await self._preguntar(
                "Fetch.fulfillRequest",
                {
                    "requestId": identificador,
                    "responseCode": 599,
                    "responseHeaders": [
                        {"name": "content-type", "value": "application/json"}
                    ],
                    "body": base64.b64encode(b"{}").decode("ascii"),
                },
            )
            self.ordenes.append(
                {
                    "metodo": "Fetch.fulfillRequest",
                    "error": plan_b.get("error"),
                    "camino": "plan B (contestar un error en vez de tirar la respuesta)",
                }
            )


# ---------------------------------------------------------------------------
# Lo de la casa: hablar con el servidor y mirar la pantalla
# ---------------------------------------------------------------------------


def el_cliente(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=DIRECCION,
        timeout=30.0,
        headers={"Authorization": f"Bearer {token}"},
    )


def la_ficha_por_la_puerta(cliente: httpx.Client, contacto_id: int) -> dict:
    respuesta = cliente.get(f"/api/contactos/{contacto_id}")
    print(f"    GET /api/contactos/{contacto_id} -> {respuesta.status_code}")
    respuesta.raise_for_status()
    return respuesta.json()


def las_notas_por_la_puerta(ficha: dict) -> list[dict]:
    """Las notas tal y como las contesta el servidor.

    **`clave_de_reenvio` va incluida a propósito**: es la clave de la acción con la que se guardó cada nota,
    y es lo único que permite decir con datos —y no por deducción— que la segunda nota se apuntó **con otra
    clave** y no reenviando la primera.
    """
    return [
        {
            "id": nota.get("id"),
            "texto": nota.get("texto"),
            "autor": nota.get("autor"),
            "autor_estado": nota.get("autor_estado"),
            "creado_en": nota.get("creado_en"),
            "clave_de_reenvio": nota.get("clave_de_reenvio"),
        }
        for nota in (ficha.get("notas_con_autor") or [])
    ]


def las_notas_de_la_pantalla(nav: NavegadorDeVerdad) -> list[dict]:
    """Lo que se ve en la ficha: cada nota con su texto, su autor y su fecha."""
    return nav.evaluar(
        """(() => {
            const lista = document.querySelector('#pantalla .lista-de-notas');
            if (!lista) return null;
            return [...lista.querySelectorAll(':scope > li')].map((fila) => ({
                texto: (fila.querySelector('.nota-texto') || {}).innerText || '',
                pie: (fila.querySelector('.pista-campo') || {}).innerText || '',
            }));
        })()"""
    )


def el_texto_del_campo(nav: NavegadorDeVerdad) -> str | None:
    return nav.evaluar(
        "(() => { const c = document.getElementById('contacto-nota-texto');"
        " return c ? c.value : null; })()"
    )


def el_aviso(nav: NavegadorDeVerdad) -> str:
    return (
        nav.evaluar(
            "(() => { const a = document.querySelector('#pantalla .aviso-error');"
            " return a ? a.innerText : ''; })()"
        )
        or ""
    )


def pon_el_cursor_al_final(nav: NavegadorDeVerdad) -> None:
    """Enfoca el campo de la nota y deja el cursor **al final**, que es donde escribe un dedo.

    Se enfoca y se coloca el cursor con la API del navegador (`focus` + `setSelectionRange`) y después se
    teclea con `Input.insertText`, que es lo que hace el navegador al escribir: **el texto lo mete el
    navegador**, no lo pone el guion con un `value =`.
    """
    nav.evaluar(
        "(() => { const c = document.getElementById('contacto-nota-texto');"
        " c.focus(); c.setSelectionRange(c.value.length, c.value.length); return null; })()"
    )


def teclear_en_la_nota(nav: NavegadorDeVerdad, texto: str) -> None:
    pon_el_cursor_al_final(nav)
    nav.escribir(texto)


def main() -> int:
    print(f"  (direccion: {DIRECCION})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    print(f"  (escenario prestado: {escenario.volumen.nombre!r}, token de {len(token)} caracteres)")

    with el_cliente(token) as cliente:
        # --- El contacto, por su puerta de verdad ------------------------------------------------
        alta = cliente.post("/api/contactos", json={"nombre": EL_CONTACTO})
        print(f"\n1) POST /api/contactos -> {alta.status_code}")
        alta.raise_for_status()
        contacto = alta.json()
        contacto_id = contacto["id"]
        print(f"   la ficha creada: id {contacto_id}, nombre {contacto.get('nombre')!r}")

        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000, movil=False)
            # **Se salta el service worker** (lo que hace «Omitir para red» en las herramientas del
            # navegador). No cambia lo que se comprueba —el service worker no toca `/api/`, lo dice su
            # propio código— y quita de en medio una caché que no pinta nada en esta comprobación.
            nav.orden("Network.enable")
            nav.orden("Network.setBypassServiceWorker", {"bypass": True})
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": "window.localStorage.setItem('cuedigital.token', "
                    + json.dumps(token)
                    + ");\n"
                    # **Los errores de la página, apuntados durante todo el recorrido.** Van en
                    # `sessionStorage` para que sobrevivan a la recarga: si el recorrido entero cuadra pero
                    # la página ha soltado un error de JavaScript por el camino, eso también hay que decirlo.
                    "(() => {\n"
                    "  try { window.__erroresDeLaPrueba = JSON.parse("
                    "sessionStorage.getItem('__erroresDeLaPrueba') || '[]'); }"
                    " catch (e) { window.__erroresDeLaPrueba = []; }\n"
                    "  const apuntaElFallo = (t) => { window.__erroresDeLaPrueba.push(t);"
                    " try { sessionStorage.setItem('__erroresDeLaPrueba',"
                    " JSON.stringify(window.__erroresDeLaPrueba)); } catch (e) {} };\n"
                    "  window.addEventListener('error', (e) =>"
                    " apuntaElFallo('error: ' + String(e.message || e.error)));\n"
                    "  window.addEventListener('unhandledrejection', (e) =>"
                    " apuntaElFallo('promesa rechazada: '"
                    " + String((e.reason && e.reason.message) || e.reason)));\n"
                    "})();\n"
                },
            )
            nav.abrir(f"{DIRECCION}/#/contactos", esperar=3.0)
            nav.esperar(
                f'document.querySelector(\'[data-accion="contacto-abrir"][data-id="{contacto_id}"]\') !== null',
                segundos=30,
            )

            # --- 1) Abrir la ficha y escribir la nota --------------------------------------------
            nav.pulsar(f'[data-accion="contacto-abrir"][data-id="{contacto_id}"]')
            hay_campo = nav.esperar(
                "document.getElementById('contacto-nota-texto') !== null", segundos=20
            )
            print(f"\n2) la ficha abierta y su campo de nota: {hay_campo}")
            if not hay_campo:
                print("   FALLO: la ficha no ha abierto su campo de nota")
                return 1
            teclear_en_la_nota(nav, TEXTO_1)
            print(f"   lo que hay escrito antes de pulsar: {el_texto_del_campo(nav)!r}")

            # --- 2) Perder la respuesta ------------------------------------------------------------
            interceptador = InterceptadorDeLaRespuesta(nav.puerto, "/notas")
            interceptador.empezar()
            print(
                "\n3) intercepción puesta (Fetch.enable con requestStage=Response, patrón «*/notas»)"
            )
            nav.pulsar(f'[data-accion="contacto-nota"][data-id="{contacto_id}"]')
            hubo = interceptador.esperar_una_intercepcion(segundos=15)
            print(f"   ¿ha llegado la respuesta a la intercepción?: {hubo}")
            print(f"   lo interceptado: {json.dumps(interceptador.interceptadas, ensure_ascii=False)}")
            print(f"   lo que contestó CDP a las órdenes: {json.dumps(interceptador.ordenes, ensure_ascii=False)}")
            if interceptador.fallos:
                print(f"   fallos de la intercepción: {interceptador.fallos}")
            interceptador.parar()
            print("   (intercepción levantada: las demás peticiones pasan solas)")

            # --- 3) El texto se conserva y la pantalla no se calla ---------------------------------
            nav.esperar(
                "(() => { const c = document.getElementById('contacto-nota-texto');"
                f" return (c && c.value === {json.dumps(TEXTO_1)})"
                " || Boolean(document.querySelector('#pantalla .aviso-error')); })()",
                segundos=15,
            )
            conservado = el_texto_del_campo(nav)
            aviso_tras_perder = el_aviso(nav)
            print("\n4) después de perder la respuesta:")
            print(f"   el campo dice: {conservado!r}")
            print(f"   el aviso de la pantalla dice: {aviso_tras_perder!r}")
            print(f"   ¿el texto se ha conservado?: {conservado == TEXTO_1}")
            print(f"   ¿la pantalla no se ha quedado en silencio?: {bool(aviso_tras_perder)}")

            # La nota, por la puerta de datos: **lo que se perdió fue la respuesta, no la nota**.
            ficha_tras_perder = la_ficha_por_la_puerta(cliente, contacto_id)
            print(
                "   la nota SÍ está en el servidor: "
                + json.dumps(las_notas_por_la_puerta(ficha_tras_perder), ensure_ascii=False)
            )

            # --- 4) Editar el texto y reintentar ---------------------------------------------------
            teclear_en_la_nota(nav, LO_QUE_SE_ANADE)
            editado = el_texto_del_campo(nav)
            print("\n5) el texto editado en el campo:")
            print(f"   {editado!r}")
            print(f"   ¿coincide con lo que se quería?: {editado == TEXTO_2}")

            nav.pulsar(f'[data-accion="contacto-nota"][data-id="{contacto_id}"]')
            nav.esperar(
                "(() => { const a = document.querySelector('#pantalla .aviso-error');"
                " return Boolean(a && a.innerText.trim()); })()",
                segundos=20,
            )
            aviso_del_conflicto = el_aviso(nav)
            conservado_tras_409 = el_texto_del_campo(nav)
            print("\n6) al reintentar (debería ser 409):")
            print(f"   el aviso de la pantalla dice: {aviso_del_conflicto!r}")
            print(f"   el campo sigue diciendo: {conservado_tras_409!r}")
            print(
                f"   ¿lo que se ve es el conflicto del servidor?: "
                f"{EL_MENSAJE_DEL_CONFLICTO in aviso_del_conflicto}"
            )
            print(f"   ¿el texto editado se ha conservado?: {conservado_tras_409 == TEXTO_2}")
            ficha_tras_409 = la_ficha_por_la_puerta(cliente, contacto_id)
            print(
                "   las notas que hay en el servidor en este momento: "
                + json.dumps(las_notas_por_la_puerta(ficha_tras_409), ensure_ascii=False)
            )

            # --- 6) Guardar voluntariamente con otra clave (volver a pulsar) -----------------------
            nav.pulsar(f'[data-accion="contacto-nota"][data-id="{contacto_id}"]')
            nav.esperar(
                "(() => { const c = document.getElementById('contacto-nota-texto');"
                " return Boolean(c) && c.value.trim() === ''; })()",
                segundos=20,
            )
            print("\n7) al volver a pulsar (la clave se renueva y la nota se apunta):")
            print(f"   el campo se ha vaciado: {el_texto_del_campo(nav)!r}")
            print(f"   el aviso de la pantalla dice: {el_aviso(nav)!r}")
            ficha_guardada = la_ficha_por_la_puerta(cliente, contacto_id)
            las_del_servidor = las_notas_por_la_puerta(ficha_guardada)
            print(
                "   las notas que hay en el servidor: "
                + json.dumps(las_del_servidor, ensure_ascii=False)
            )

            # --- 7) Recargar la pantalla entera ----------------------------------------------------
            nav.orden("Page.reload", {"ignoreCache": True})
            time.sleep(3.0)
            nav.esperar(
                f'document.querySelector(\'[data-accion="contacto-abrir"][data-id="{contacto_id}"]\') !== null',
                segundos=30,
            )
            nav.pulsar(f'[data-accion="contacto-abrir"][data-id="{contacto_id}"]')
            nav.esperar(
                "document.querySelector('#pantalla .lista-de-notas, #pantalla .aviso') !== null",
                segundos=20,
            )
            # Si la ficha no tiene ninguna nota, la pantalla enseña «Todavía no hay ninguna nota» en vez
            # de la lista: se espera a que aparezca una cosa o la otra.
            nav.esperar(
                "document.querySelector('#pantalla .lista-de-notas') !== null", segundos=10
            )
            de_la_pantalla = las_notas_de_la_pantalla(nav)
            print("\n8) después de recargar la pantalla entera:")
            print(
                "   lo que pinta la pantalla: "
                + json.dumps(de_la_pantalla, ensure_ascii=False)
            )

            # --- La captura del estado final -----------------------------------------------------
            errores_de_la_pagina = nav.evaluar(
                "JSON.stringify(window.__erroresDeLaPrueba || [])"
            )
            CARPETA.mkdir(parents=True, exist_ok=True)
            destino = CARPETA / "contacto-nota-conflicto.png"
            crudo = base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
            destino.write_bytes(crudo)
            print(f"\n9) captura del estado final: {destino}")
            print(f"   errores de JavaScript en la página, en todo el recorrido: {errores_de_la_pagina}")

    # ------------------------------------------------------------------------------------------
    # Lo que se dice del recorrido
    # ------------------------------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("LO QUE HA SALIDO, PASO A PASO")
    print("=" * 78)
    los_textos_servidor = [nota["texto"] for nota in las_del_servidor]
    los_textos_pantalla = [nota["texto"] for nota in (de_la_pantalla or [])]
    las_claves = [nota["clave_de_reenvio"] for nota in las_del_servidor]
    comprobaciones = [
        ("la nota se guardó aunque se perdiera la respuesta", len(ficha_tras_perder.get("notas_con_autor") or []) == 1),
        ("el campo conservó el texto al perder la respuesta", conservado == TEXTO_1),
        ("la pantalla explicó lo que pasaba (no se calló)", bool(aviso_tras_perder)),
        (
            "y lo que explicó fue el fallo de red (no el conflicto del servidor)",
            EL_MENSAJE_SIN_RESPUESTA in aviso_tras_perder
            and EL_MENSAJE_DEL_CONFLICTO not in aviso_tras_perder,
        ),
        ("el texto editado quedó en el campo", editado == TEXTO_2),
        ("el reintento dio el conflicto del servidor (409)", EL_MENSAJE_DEL_CONFLICTO in aviso_del_conflicto),
        ("el texto editado se conservó tras el 409", conservado_tras_409 == TEXTO_2),
        ("al volver a pulsar se apuntó la segunda nota", len(las_del_servidor) == 2),
        (
            "la segunda nota se apuntó con OTRA clave (no es un reenvío de la primera)",
            len(las_claves) == 2 and las_claves[0] != las_claves[1],
        ),
        ("en el servidor están las dos notas correctas", sorted(los_textos_servidor) == sorted([TEXTO_1, TEXTO_2])),
        ("al recargar se ven las dos notas", sorted(los_textos_pantalla) == sorted([TEXTO_1, TEXTO_2])),
        (
            "cada nota trae su autor y su fecha",
            all(
                nota.get("autor") and nota.get("creado_en")
                for nota in las_del_servidor
            ),
        ),
    ]
    for titulo, bien in comprobaciones:
        print(f"  [{'sí' if bien else 'NO'}] {titulo}")

    # **La clave de la acción, que es lo que la revisión llamó «otra clave».** Se lee de la puerta de
    # datos, no se deduce: el servidor guarda con qué acción se apuntó cada nota.
    print("\nLA CLAVE DE CADA ACCIÓN, POR LA PUERTA DE DATOS")
    for nota in las_del_servidor:
        print(f"  id {nota['id']}: {nota['texto']!r} -> clave {nota['clave_de_reenvio']!r}")
    print(f"  ¿las dos claves son distintas?: {len(las_claves) == 2 and len(set(las_claves)) == 2}")
    print(
        "\n  las notas del servidor: "
        + json.dumps(las_del_servidor, ensure_ascii=False, indent=2)
    )
    print(
        "\n  las notas de la pantalla: "
        + json.dumps(de_la_pantalla, ensure_ascii=False, indent=2)
    )

    # --- La comprobación por la puerta de datos, con el detalle de autor y fecha ----------------
    print("\nLA MISMA PREGUNTA POR LA PUERTA DE DATOS (GET /api/contactos/{id})")
    for nota in las_del_servidor:
        print(
            f"  id {nota['id']}: {nota['texto']!r} · autor {nota['autor']!r} "
            f"({nota['autor_estado']}) · {nota['creado_en']} · clave {nota['clave_de_reenvio']!r}"
        )
    print("\nLA MISMA COSA POR LA PANTALLA (recargada)")
    for nota in de_la_pantalla or []:
        print(f"  {nota['texto']!r} · {nota['pie']!r}")

    return 0 if all(bien for _, bien in comprobaciones) else 1


if __name__ == "__main__":
    raise SystemExit(main())
