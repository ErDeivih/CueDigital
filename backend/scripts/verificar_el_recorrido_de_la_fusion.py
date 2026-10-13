"""El recorrido de la fusión de fichas (Entrega 5), **andado en el navegador** (14/10/2026).

POR QUÉ HACE FALTA. La pantalla está enrutada y las puertas del servidor están probadas, pero **nada de eso prueba
que se vea**: lo prueba leer **el DOM**. Es la lección que esta casa ha pagado ya tres veces (la pantalla muda, el
`list()` que devuelve claves, el filtro que se caía de la dirección).

Y LO QUE MÁS IMPORTA AQUÍ, que es lo que este contrato tiene de especial: **la pantalla tiene que PARAR** cuando las
dos fichas tienen notas escritas. La nota es un **campo único**, así que juntarlas perdería una de las dos — y eso no
lo puede decidir una pantalla. Se mide: que **no** haya botón de juntar y que lo diga con palabras.

Se apoya en lo que ya hay: el servidor y su limpieza se **importan** del guion de las tareas, el navegador es el
`NavegadorDeVerdad` de la casa, y la forma es la de los otros dos recorridos.

    uso:  .venv\\Scripts\\python.exe backend\\scripts\\verificar_el_recorrido_de_la_fusion.py [PUERTO] [CAPTURAS]
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

os.environ["CUEDIGITAL_ENTORNO"] = "pruebas"
os.environ["CUEDIGITAL_ITERACIONES_PBKDF2"] = "1000"
os.environ["PYTHONIOENCODING"] = "utf-8"

from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_el_recorrido_de_las_tareas import (  # noqa: E402
    apagar_el_servidor,
    levantar_el_servidor,
    lo_que_ha_quedado_vivo,
)

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8363
CAPTURAS = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ.parent / "docs" / "capturas"
LA_DIRECCION = "#/fusion"

comprobaciones = 0
fallos: list[str] = []


def comprobar(que: str, bien: bool, detalle: str = "") -> None:
    global comprobaciones
    comprobaciones += 1
    if bien:
        print(f"  [OK   ] {que}")
    else:
        print(f"  [FALLO] {que}   {detalle}")
        fallos.append(que)


def puerta(token: str, metodo: str, camino: str, cuerpo: dict | None = None):
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    peticion = urllib.request.Request(
        f"http://127.0.0.1:{PUERTO}{camino}",
        data=datos,
        method=metodo,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            crudo, codigo = respuesta.read().decode("utf-8") or "null", respuesta.status
    except urllib.error.HTTPError as error:
        crudo, codigo = error.read().decode("utf-8", "replace"), error.code
    except Exception as error:  # noqa: BLE001
        return 0, f"no ha llegado: {error}"
    try:
        return codigo, json.loads(crudo)
    except Exception:  # noqa: BLE001
        return codigo, crudo


def entrar(navegador: NavegadorDeVerdad, token: str) -> None:
    """Se entra y **se recarga**: meter el vale no basta, porque cambiar el `#` no vuelve a arrancar la aplicación."""
    navegador.abrir(f"http://127.0.0.1:{PUERTO}/", esperar=1.5)
    navegador.evaluar(f'localStorage.setItem("cuedigital.token", {json.dumps(token)})')
    navegador.evaluar("location.hash = ''; location.reload()")
    navegador.esperar("!!document.querySelector('h1')", segundos=20)


def lo_que_se_ve(navegador: NavegadorDeVerdad) -> dict:
    crudo = navegador.evaluar(
        "JSON.stringify({"
        "  h1: (document.querySelector('h1')||{}).textContent || '',"
        # **La dirección y el titular, que es lo que dice QUÉ pantalla se ha pintado**: el armazón tiene su propio
        # `h1`, así que sin esto un «hay título» puede estar pasando por el título de otra pantalla.
        "  hash: location.hash,"
        "  principales: Array.from(document.querySelectorAll('h1, h2')).map((e)=>(e.textContent||'').trim()),"
        "  botones: Array.from(document.querySelectorAll('button')).map((b)=>(b.textContent||'').trim()),"
        "  filas: document.querySelectorAll('table tbody tr').length,"
        "  texto: document.body.textContent || ''"
        "})"
    )
    return json.loads(crudo) if isinstance(crudo, str) else (crudo or {})


def elegir(navegador: NavegadorDeVerdad, campo: str, valor) -> None:
    """Elige en un desplegable y **dispara el cambio**, que es como se entera la pantalla."""
    navegador.evaluar(
        f"(() => {{ const c = document.getElementById({json.dumps(campo)});"
        f" c.value = {json.dumps(str(valor))};"
        " c.dispatchEvent(new Event('change', { bubbles: true })); return c.value; })()"
    )


def main() -> int:
    import tempfile

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    temporal = pathlib.Path(tempfile.mkdtemp(prefix="cd-fusion-"))
    proceso = None
    try:
        print("== el servidor, contra una base TEMPORAL (nunca la del agricultor) ==")
        proceso, base, _ = levantar_el_servidor(temporal)
        os.environ["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"
        import time

        for _ in range(60):
            if puerta("", "GET", "/api/interfaz")[0]:
                break
            time.sleep(0.5)

        codigo, alta = puerta(
            "",
            "POST",
            "/api/cuenta/registro",
            {
                "explotacion": {"nombre": "Finca de la fusión", "nif": "70922320A", "provincia": "Salamanca", "municipio": "Peñaranda"},
                "nombre": "El de la fusión",
                "correo": "fusion-recorrido@ejemplo.test",
                "clave": "una-clave-larga-de-prueba",
            },
        )
        if codigo != 201:
            print(f"  [FALLO] no se ha podido dar de alta la cuenta: {codigo} {str(alta)[:200]}")
            return 1
        token = alta["token"]

        # **Dos fichas que son la misma**, y **una tercera sin notas** para poder fusionar de verdad.
        con_notas_una = puerta(token, "POST", "/api/contactos", {"nombre": "Hermanos Pérez (el viejo)"})
        con_notas_otra = puerta(token, "POST", "/api/contactos", {"nombre": "Hermanos Pérez (el nuevo)"})
        sin_notas_una = puerta(token, "POST", "/api/contactos", {"nombre": "El del prado (repetido)"})
        sin_notas_otra = puerta(token, "POST", "/api/contactos", {"nombre": "El del prado"})
        for ficha in (con_notas_una, con_notas_otra, sin_notas_una, sin_notas_otra):
            assert ficha[0] == 201, ficha
        # Las notas se apuntan por su puerta, que es la que las guarda.
        for ficha, nota in ((con_notas_una, "Le gusta que le llamen por la mañana."), (con_notas_otra, "Tiene dos naves.")):
            puesto = puerta(token, "POST", f"/api/contactos/{ficha[1]['id']}/notas", {"texto": nota})
            assert puesto[0] in (200, 201), puesto

        with NavegadorDeVerdad() as navegador:
            entrar(navegador, token)
            # **EL VIGILANTE DE ERRORES, DELANTE DE TODO** (14/10/2026). Y esto es lo que me faltó durante cuatro
            # rondas: el cargador de esta pantalla es `async`, así que **una excepción suya no la recoge nadie** —la
            # promesa se rechaza, la aplicación se queda donde estaba y el recorrido ve **el armazón**. Una pantalla
            # que revienta al abrirse **se ve igual que una que no existe**, y por eso estuve arreglando el enrutado
            # (la llave, el ancla, el envoltorio, los nombres) sin que ninguno fuera el problema.
            #
            # La forma es **la de la casa** (`verificar_el_recorrido_de_las_tareas.py:543`): se apuntan los `error` y
            # también las **promesas rechazadas** (`unhandledrejection`), que es justo el caso de un `async`.
            # Va **después de entrar** (que recarga el documento, y al recargar se pierden los oyentes) y **antes de
            # navegar** a la dirección de esta pantalla.
            navegador.evaluar(
                "window.__los_errores = [];"
                "window.addEventListener('error', (e) => window.__los_errores.push('error: ' + String(e.message || e)));"
                "window.addEventListener('unhandledrejection', (r) => window.__los_errores.push("
                "'promesa rechazada: ' + String((r && r.reason && r.reason.message) || (r && r.reason) || r)));"
            )
            navegador.abrir(f"http://127.0.0.1:{PUERTO}/{LA_DIRECCION}", esperar=2.0)
            # **Y se dice lo que ha saltado, en la primera línea**: sin esto, un fallo de JavaScript deja la pantalla a
            # medias y el recorrido entero habla de otra cosa.
            print(f"  errores de la página al abrir la pantalla: {navegador.evaluar('JSON.stringify(window.__los_errores || [])')}")

            # --- 1 · Que la pantalla NO salga muda ---
            visto = lo_que_se_ve(navegador)
            comprobar("la pantalla tiene su título (no sale muda)", bool((visto.get("h1") or "").strip()), f"h1={visto.get('h1')!r}")
            comprobar(
                "y los botones llevan su texto",
                bool(visto.get("botones")) and all((b or "").strip() for b in visto["botones"]),
                f"botones={visto.get('botones')!r}",
            )

            # --- 2 · La vista previa, con dos que SÍ se pueden juntar ---
            elegir(navegador, "fusion-origen", sin_notas_una[1]["id"])
            elegir(navegador, "fusion-destino", sin_notas_otra[1]["id"])
            navegador.evaluar("document.querySelector('[data-accion=fusion-ver]').click()")
            navegador.esperar("document.body.textContent.includes('Esto es lo que va a pasar')", segundos=15)
            visto = lo_que_se_ve(navegador)
            comprobar("la vista previa se enseña", "Esto es lo que va a pasar" in (visto.get("texto") or ""), "")
            comprobar("y cuenta las tablas", visto.get("filas", 0) >= 5, f"filas={visto.get('filas')}")
            comprobar(
                "y dice que no choca nada",
                "No choca nada" in (visto.get("texto") or ""),
                [l for l in (visto.get("texto") or "").split("\n") if "choca" in l][:2],
            )
            comprobar(
                "y ofrece juntarlas",
                any("Juntarlas" in b for b in visto.get("botones") or []),
                f"botones={visto.get('botones')!r}",
            )
            comprobar(
                "y avisa de que la que desaparece NO se borra",
                "NO se borra" in (visto.get("texto") or ""),
                "",
            )

            # --- 3 · **LO QUE MÁS IMPORTA**: dos con notas escritas → la pantalla PARA ---
            elegir(navegador, "fusion-origen", con_notas_una[1]["id"])
            elegir(navegador, "fusion-destino", con_notas_otra[1]["id"])
            navegador.evaluar("document.querySelector('[data-accion=fusion-ver]').click()")
            navegador.esperar("document.body.textContent.includes('Esto es lo que va a pasar')", segundos=15)
            visto = lo_que_se_ve(navegador)
            comprobar(
                "con las dos fichas con notas, la pantalla NO ofrece juntarlas",
                not any("Juntarlas" in b for b in visto.get("botones") or []),
                f"botones={visto.get('botones')!r}",
            )
            comprobar(
                "y lo dice con palabras",
                "NO lo puede decidir" in (visto.get("texto") or ""),
                [l for l in (visto.get("texto") or "").split("\n") if "decidir" in l][:2],
            )
            # **Y el servidor tampoco las junta**: se comprueba que la puerta lo impide, no solo la pantalla.
            intento = puerta(token, "POST", f"/api/contactos/{con_notas_una[1]['id']}/fusion/{con_notas_otra[1]['id']}")
            comprobar(
                "y el servidor tampoco las junta (no es solo que la pantalla no enseñe el botón)",
                intento[0] != 200,
                f"contestó {intento[0]}: {str(intento[1])[:120]}",
            )

            # --- 4 · Juntar de verdad, y deshacer ---
            elegir(navegador, "fusion-origen", sin_notas_una[1]["id"])
            elegir(navegador, "fusion-destino", sin_notas_otra[1]["id"])
            navegador.evaluar("document.querySelector('[data-accion=fusion-ver]').click()")
            navegador.esperar("document.body.textContent.includes('Esto es lo que va a pasar')", segundos=15)
            juntadas = puerta(token, "POST", f"/api/contactos/{sin_notas_una[1]['id']}/fusion/{sin_notas_otra[1]['id']}")
            comprobar("la fusión se hace", juntadas[0] == 200, f"{juntadas[0]}: {str(juntadas[1])[:120]}")
            la_que_desaparece = puerta(token, "GET", f"/api/contactos/{sin_notas_una[1]['id']}")
            comprobar(
                "y la que desaparece remite a la que se queda",
                la_que_desaparece[0] == 200 and la_que_desaparece[1].get("fusionado_con_id") == sin_notas_otra[1]["id"],
                str(la_que_desaparece[1])[:140],
            )
            deshecho = puerta(token, "POST", f"/api/contactos/{sin_notas_otra[1]['id']}/deshacer-la-fusion")
            comprobar("y se puede deshacer", deshecho[0] == 200, f"{deshecho[0]}: {str(deshecho[1])[:120]}")
            vuelta = puerta(token, "GET", f"/api/contactos/{sin_notas_una[1]['id']}")
            comprobar(
                "y al deshacer, la que desaparecía deja de remitir",
                vuelta[0] == 200 and not vuelta[1].get("fusionado_con_id"),
                str(vuelta[1])[:140],
            )

            # --- 5 · La dirección y la ventana ---
            comprobar(
                "la dirección sigue siendo la de esta pantalla",
                LA_DIRECCION in (navegador.evaluar("location.hash") or ""),
                f"hash={navegador.evaluar('location.hash')!r}",
            )
            navegador.medir(1440, 1000)
            fuera = navegador.evaluar(
                "JSON.stringify(Array.from(document.querySelectorAll('button, a, input, select, th')).filter("
                "  (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > window.innerWidth + 2 || r.left < -2); }"
                ").length)"
            )
            comprobar("ningún control se sale de la ventana", str(fuera) == "0", f"fuera: {fuera}")
            print(f"  capturas: {len(list(CAPTURAS.glob('fusion-*.png')))}")

        print()
        print(f"Comprobaciones: {comprobaciones}   Fallos: {len(fallos)}")
        return 1 if fallos else 0
    finally:
        print()
        print(apagar_el_servidor(proceso))
        import hashlib
        import shutil

        shutil.rmtree(temporal, ignore_errors=True)
        print(f"  la carpeta temporal se ha borrado: {temporal}")
        print(f"  procesos que han quedado vivos: {lo_que_ha_quedado_vivo() or 'ninguno'}")
        real = RAIZ / "cuedigital.db"
        if real.exists():
            huella = hashlib.sha256(real.read_bytes()).hexdigest().upper()
            esperada = "CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12"
            print(f"  la base del agricultor, después: {huella}")
            print(f"  [{'OK   ' if huella == esperada else 'FALLO'}] y su huella {'NO ' if huella == esperada else 'SÍ '}ha cambiado")


if __name__ == "__main__":
    raise SystemExit(main())
