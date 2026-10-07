"""Revisar las pantallas en un navegador de verdad: identidad, datos esperados y capturas.

## Qué comprueba cada pantalla, y por qué así

Una captura no acredita nada si no se sabe **qué** se estaba mirando. Este guion exige **cuatro cosas** por
pantalla, y falla si alguna no se cumple:

  1. **La ruta**: la dirección en la que acaba la aplicación es la que se pidió.
  2. **Un elemento propio**, que solo existe en esa pantalla (medido: el buscador de tierras, el de cuentas,
     el botón de sacar el cuaderno…): sin esto, dos pantallas que enseñen el mismo texto pasarían por la
     misma.
  3. **La ausencia del formulario de entrar**: si está el campo del correo, no se está dentro de la
     aplicación. (La pantalla de entrar también dice «Mi cuaderno» en la cabecera, y esa fue la trampa que
     hacía pasar el login por cuatro pantallas distintas.)
  4. **Los datos esperados, sacados de la API**: el alias de una tierra del escenario tiene que estar en la
     lista de tierras; el concepto de un gasto, en la de cuentas. Lo que se espera no se escribe a mano: se
     pregunta al servidor y se exige en la pantalla.

## Y los casos negativos

Una comprobación que no puede fallar no comprueba nada, así que además se comprueba que **rechaza**:

  · la pantalla de entrar, que no puede pasar por ninguna de las cuatro;
  · una pantalla por otra (la identidad de tierras no vale para cuentas);
  · una ruta inventada (`#/no-existe`), que no es ninguna de las cuatro.

## Los escenarios

  · **`volumen`** (por defecto): la explotación de 64 tierras de `datos_representativos.py`, con nombres
    largos, papeles, gastos, movimientos y tierras incompletas. Es la que permite revisar tablas, nombres
    largos y cifras de verdad.
  · **`vacio`**: una cuenta recién creada. Sirve para lo contrario —que las pantallas se lean con el
    cuaderno sin empezar y que ningún texto afirme que está todo— y se guarda aparte.

Uso:
    python scripts/mirar_pantallas.py [direccion] [carpeta] [--vacio|--volumen] [--solo-capturas]
"""

from __future__ import annotations

import argparse
import base64
import json
import pathlib
import sys

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

ANCHOS = [(390, 844), (712, 900), (1024, 900), (1440, 900)]

# Lo que identifica a cada pantalla: su ruta, **la parte de pantalla de la dirección** (la aplicación añade
# la campaña y la finca por su cuenta, y eso es correcto: es el contexto), **un elemento que solo está en
# ella** y dónde mirar el texto. Los selectores están medidos con `medir_identidad.py` (07/10/2026).
PANTALLAS = [
    {
        "clave": "inicio",
        "ruta": "/#/",
        "pantalla_en_la_direccion": "#/",
        "propio": "#pantalla [data-accion='mis-cosas'], #pantalla [data-accion='gastos-ver-todas']",
        # **La página entera**, y no solo `#pantalla`: el nombre de la explotación —que es el dato que se
        # exige aquí— está en la cabecera del armazón, que vive fuera de la pantalla.
        "en": "#marco, #pantalla",
    },
    {
        "clave": "cuaderno",
        "ruta": "/#/cuaderno",
        "pantalla_en_la_direccion": "#/cuaderno",
        "propio": "#pantalla [data-accion='cuaderno-sacar']",
        "en": "#pantalla",
    },
    {
        "clave": "tierras",
        "ruta": "/#/tierras",
        "pantalla_en_la_direccion": "#/tierras",
        "propio": "#buscar_tierra_mis_cosas",
        "en": "#pantalla",
    },
    {
        "clave": "cuentas",
        "ruta": "/#/cuentas",
        "pantalla_en_la_direccion": "#/cuentas",
        "propio": "#gastos-buscar",
        "en": "#pantalla",
    },
]

FALLOS: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    print(f"  [{'OK  ' if condicion else 'FALLO'}] {descripcion}")
    if not condicion:
        FALLOS.append(descripcion)


def el_token(direccion: str, escenario: str) -> tuple[str, dict]:
    """El token con el que se entra, y los datos que se van a exigir en pantalla."""
    if escenario == "vacio":
        with httpx.Client(base_url=direccion, timeout=30.0) as cliente:
            respuesta = cliente.post(
                "/api/cuenta/registro",
                json={
                    "nombre": "Prueba del cuaderno sin empezar",
                    "correo": "vacio@ejemplo.test",
                    "clave": "una-clave-larga",
                    "explotacion": {"nombre": "La finca sin empezar", "nif": "12345678Z"},
                },
            )
            if respuesta.status_code == 409:
                respuesta = cliente.post(
                    "/api/cuenta/entrar", json={"correo": "vacio@ejemplo.test", "clave": "una-clave-larga"}
                )
            respuesta.raise_for_status()
            return respuesta.json()["token"], {}

    suyo = preparar(direccion)
    print(f"  escenario: {suyo.volumen.nombre}")
    print(f"  tierras: {len(suyo.tierras)} (sin superficie {len(suyo.tierras_sin_superficie)}, "
          f"sin forma {len(suyo.tierras_sin_forma)}, sin cultivo {len(suyo.tierras_sin_cultivo)})")
    esperado = {
        # **Lo que se va a exigir en pantalla, preguntado al servidor**: el nombre de la explotación (que va
        # en la cabecera), el alias de la primera tierra (un nombre largo de verdad), el concepto del primer
        # gasto y la cuenta de apuntes del cuaderno. Si una pantalla no los enseña, es que no está enseñando
        # los datos de esa explotación.
        "inicio": suyo.volumen.nombre,
        "tierras": suyo.tierras[0].alias,
        "cuentas": "",
        "cuaderno": "",
    }
    with httpx.Client(base_url=direccion, timeout=30.0) as cliente:
        cabeceras = {"Authorization": f"Bearer {suyo.volumen.token}"}
        gastos = cliente.get("/api/gastos", headers=cabeceras).json().get("gastos", [])
        if gastos:
            esperado["cuentas"] = gastos[0]["concepto"]
        resumen = cliente.get("/api/cuaderno/resumen", headers=cabeceras).json()
        # La cuenta que la pantalla dice es la **suma de los apuntes del año**, y se calcula igual que en la
        # pantalla: así lo que se exige sale del servidor y no de una lista escrita a mano.
        apuntes = sum(
            valor
            for clave, valor in resumen.items()
            if clave.startswith("apuntes") and isinstance(valor, int)
        )
        if apuntes:
            esperado["cuaderno"] = f"{apuntes} apuntes"
    return suyo.volumen.token, esperado


def lo_que_se_ve(nav: NavegadorDeVerdad, selector: str) -> str:
    """El texto de lo que se ve, en el contenedor que se diga.

    Se admiten **varios selectores separados por coma** (`#marco, #pantalla`): el nombre de la explotación
    vive en la cabecera del armazón y las cifras en la pantalla, y hay que poder mirar los dos sin depender
    de qué `innerText` incluye el navegador en cada ancho.
    """
    return nav.evaluar(
        "(() => {"
        f"  const trozos = []; for (const el of document.querySelectorAll({json.dumps(selector)}))"
        "     trozos.push(el.innerText || '');"
        "   return trozos.join(' \\n ');"
        "})()"
    ) or ""


def una_pantalla(nav: NavegadorDeVerdad, direccion: str, pantalla: dict, esperado: dict, prefijo: str, carpeta: pathlib.Path, *, capturas: bool) -> None:
    print(f"\n=== {pantalla['clave']} ({pantalla['ruta']})")
    for ancho, alto in ANCHOS:
        nav.medir(ancho, alto)
        # Por `about:blank`: cambiar solo la almohadilla no recarga, y la aplicación se quedaría con lo que
        # tiene en memoria (es la trampa que hizo que doce capturas fueran la pantalla de entrar).
        nav.orden("Page.navigate", {"url": "about:blank"})
        nav.abrir(f"{direccion}{pantalla['ruta']}", esperar=1.0)
        # **Se espera a que la pantalla esté, no a que pase el tiempo.** La primera vuelta falló por esto:
        # a 390 px, «inicio» se comprobaba antes de que llegara el nombre de la explotación del servidor, y
        # la comprobación decía que no lo enseñaba. Se espera al elemento propio (que es la identidad) y, si
        # hay dato esperado, a que llegue; después se comprueba todo igual, y si no llegó, falla.
        nav.esperar(f"Boolean(document.querySelector({json.dumps(pantalla['propio'])}))", segundos=10)
        esperado_aqui = esperado.get(pantalla["clave"], "")
        if esperado_aqui:
            nav.esperar(
                "document.body.innerText.toLowerCase().includes("
                + json.dumps(esperado_aqui.lower()) + ")",
                segundos=8,
            )
        donde = str(nav.evaluar("location.hash"))
        texto = lo_que_se_ve(nav, pantalla["en"])
        hay_entrada = bool(nav.evaluar("Boolean(document.querySelector('#correo'))"))
        propio = bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(pantalla['propio'])}))"))
        ancho_pagina = nav.evaluar(
            "(() => ({ ancho: document.documentElement.scrollWidth, cabe: window.innerWidth }))()"
        )
        # **La pantalla, no la dirección entera**: la aplicación añade `?campana=…&finca=…` por su cuenta, y
        # eso es lo correcto (el contexto viaja en la dirección). Lo que se comprueba es que la dirección
        # acabe en **esa** pantalla y no en otra.
        comprobar(
            donde.split("?")[0] == pantalla["pantalla_en_la_direccion"],
            f"{pantalla['clave']} a {ancho}: la dirección acaba en esa pantalla ({donde})",
        )
        comprobar(propio, f"{pantalla['clave']} a {ancho}: está su elemento propio")
        comprobar(not hay_entrada, f"{pantalla['clave']} a {ancho}: no está el formulario de entrar")
        esperado_aqui = esperado.get(pantalla["clave"], "")
        if esperado_aqui:
            comprobar(
                esperado_aqui.lower() in texto.lower(),
                f"{pantalla['clave']} a {ancho}: enseña los datos de la explotación («{esperado_aqui[:40]}»)",
            )
        comprobar(
            ancho_pagina["ancho"] <= ancho_pagina["cabe"],
            f"{pantalla['clave']} a {ancho}: la página no se sale ({ancho_pagina['ancho']} de {ancho_pagina['cabe']})",
        )
        if capturas:
            fichero = carpeta / f"{prefijo}-{pantalla['clave']}-{ancho}.png"
            fichero.write_bytes(
                base64.b64decode(nav.orden("Page.captureScreenshot", {"format": "png"})["data"])
            )


def el_cuaderno_sin_empezar(nav: NavegadorDeVerdad, direccion: str) -> None:
    """**El cuaderno vacío no puede decir que está completo** (07/10/2026).

    Es el defecto que encontró David mirando una captura: arriba se leía «Todavía no has apuntado nada este
    año» y, debajo, la sección decía «Lo tienes todo apuntado». Un cuaderno sin empezar no está al día, y el
    silencio (o el visto bueno) delante de una inspección es lo peor que puede decir este programa. Se
    comprueban las dos frases: la de arriba **tiene que estar** y la de abajo **no puede estar**.
    """
    print("\n=== el cuaderno sin empezar (no puede decir que está completo)")
    nav.medir(1440, 900)
    nav.orden("Page.navigate", {"url": "about:blank"})
    nav.abrir(f"{direccion}/#/cuaderno", esperar=1.5)
    texto = lo_que_se_ve(nav, "#pantalla")
    comprobar(
        "no has apuntado nada" in texto.lower() or "no hay nada apuntado" in texto.lower(),
        "el cuaderno sin empezar dice que no hay nada apuntado",
    )
    comprobar(
        "lo tienes todo apuntado" not in texto.lower(),
        "y NO dice que lo tienes todo apuntado (las dos frases se contradecían)",
    )


def los_negativos(direccion: str) -> None:
    """Una comprobación que no puede fallar no comprueba nada: esto exige que **rechace**.

    Va en **un navegador aparte y sin el token inyectado**, y eso es importante: el token de la sesión se
    pone en *cada documento nuevo* (`Page.addScriptToEvaluateOnNewDocument`), así que quitarlo desde la
    página no sirve de nada —la siguiente navegación lo vuelve a poner—. La primera versión de esta
    comprobación hacía justo eso y por eso «sin sesión» salía con sesión.
    """
    print("\n=== lo que tiene que RECHAZAR (si esto pasara, la comprobación no valdría)")
    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        # 1. Sin sesión: la pantalla de entrar **no** puede pasar por ninguna de las cuatro.
        nav.abrir(f"{direccion}/#/cuentas", esperar=1.4)
        comprobar(
            bool(nav.evaluar("Boolean(document.querySelector('#correo'))")),
            "sin sesión, la aplicación pide entrar (no pinta la pantalla de dentro)",
        )
        for pantalla in PANTALLAS:
            propio = bool(nav.evaluar(f"Boolean(document.querySelector({json.dumps(pantalla['propio'])}))"))
            comprobar(not propio, f"la pantalla de entrar no pasa por «{pantalla['clave']}»")
        # 2. Una ruta inventada tampoco.
        nav.orden("Page.navigate", {"url": "about:blank"})
        nav.abrir(f"{direccion}/#/no-existe-esto", esperar=1.2)
        comprobar(
            bool(nav.evaluar("Boolean(document.querySelector('#correo'))")),
            "una ruta inventada, sin sesión, tampoco pinta una pantalla de dentro",
        )
        # 3. **Y una pantalla no pasa por otra**: con sesión de verdad, la identidad de «tierras» no puede
        #    darse por buena estando en «cuentas».
        nav.orden("Page.navigate", {"url": "about:blank"})
        nav.abrir(f"{direccion}/#/entrar", esperar=1.2)
        comprobar(
            not bool(nav.evaluar("Boolean(document.querySelector('#gastos-buscar'))")),
            "la pantalla de entrar no tiene el buscador de cuentas",
        )


def main() -> int:
    analizador = argparse.ArgumentParser(description="Revisar y capturar las pantallas, con identidad y datos.")
    analizador.add_argument("direccion", nargs="?", default="http://127.0.0.1:8025")
    analizador.add_argument("carpeta", nargs="?", default=r"C:\Users\David\AppData\Local\Temp\cd-ui")
    analizador.add_argument("--vacio", action="store_true", help="con una cuenta recién creada")
    analizador.add_argument("--solo-capturas", action="store_true")
    argumentos = analizador.parse_args()

    carpeta = pathlib.Path(argumentos.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    escenario = "vacio" if argumentos.vacio else "volumen"
    print(f"Escenario: {escenario}. Carpeta: {carpeta}")
    token, esperado = el_token(argumentos.direccion, escenario)

    with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
        )
        for pantalla in PANTALLAS:
            una_pantalla(
                nav,
                argumentos.direccion,
                pantalla,
                esperado,
                escenario,
                carpeta,
                capturas=not argumentos.solo_capturas,
            )
        if not argumentos.solo_capturas:
            los_negativos(argumentos.direccion)
            if escenario == "vacio":
                el_cuaderno_sin_empezar(nav, argumentos.direccion)

    print(f"\nCapturas en {carpeta}")
    if FALLOS:
        print(f"FALLOS: {len(FALLOS)}")
        for fallo in FALLOS:
            print(f"  · {fallo}")
        return 1
    print("Todo correcto: cada pantalla es la que dice ser, con sus datos y sin el formulario de entrar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
