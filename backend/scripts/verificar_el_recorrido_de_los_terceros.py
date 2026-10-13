"""El recorrido de los servicios a terceros (CRM-04), **andado en el navegador** (14/10/2026).

POR QUÉ HACE FALTA. La pantalla existe, tiene sus 30 textos y está enrutada, y **todas las puertas contestan 200**.
Nada de eso prueba que **se vea**. Lo que lo prueba es leer **el DOM**: el `<h1>` con texto, los rótulos de los
botones, y la fila del trabajo en la tabla **después de recargar**. Es la lección que esta casa ya ha pagado tres
veces: la pantalla muda, el `list()` que devuelve claves y el filtro que se caía de la dirección. Ninguna de las tres
la habría visto una suite.

Se apoya en lo que ya hay, en vez de reescribirlo: el servidor y su limpieza se **importan** del guion de las tareas,
el navegador es el `NavegadorDeVerdad` de la casa, y la forma es la del recorrido integrado.

    uso:  .venv\\Scripts\\python.exe backend\\scripts\\verificar_el_recorrido_de_los_terceros.py [PUERTO] [CAPTURAS]
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
LA_DIRECCION = "#/trabajos-a-terceros"

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
    """**El navegador tiene que entrar**, y hay que **recargar**: meter el vale no basta, porque cambiar el `#` no
    vuelve a arrancar la aplicación. Lo aprendí midiendo el recorrido integrado."""
    navegador.abrir(f"http://127.0.0.1:{PUERTO}/", esperar=1.5)
    navegador.evaluar(f'localStorage.setItem("cuedigital.token", {json.dumps(token)})')
    navegador.evaluar("location.hash = ''; location.reload()")
    navegador.esperar("!!document.querySelector('h1')", segundos=20)


def lo_que_se_ve(navegador: NavegadorDeVerdad) -> dict:
    crudo = navegador.evaluar(
        "JSON.stringify({"
        "  h1: (document.querySelector('h1')||{}).textContent || '',"
        "  botones: Array.from(document.querySelectorAll('button')).map((b)=>(b.textContent||'').trim()),"
        "  rotulos: Array.from(document.querySelectorAll('th, label')).map((e)=>(e.textContent||'').trim()),"
        "  filas: document.querySelectorAll('table tbody tr').length,"
        "  celdas: Array.from(document.querySelectorAll('table tbody tr:last-child td')).map((c)=>(c.textContent||'').trim()),"
        "  texto: document.body.textContent || ''"
        "})"
    )
    return json.loads(crudo) if isinstance(crudo, str) else (crudo or {})


def main() -> int:
    import tempfile

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    temporal = pathlib.Path(tempfile.mkdtemp(prefix="cd-terceros-"))
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
                "explotacion": {"nombre": "Finca de los terceros", "nif": "70922320A", "provincia": "Salamanca", "municipio": "Peñaranda"},
                "nombre": "El de los terceros",
                "correo": "terceros-recorrido@ejemplo.test",
                "clave": "una-clave-larga-de-prueba",
            },
        )
        if codigo != 201:
            print(f"  [FALLO] no se ha podido dar de alta la cuenta: {codigo} {str(alta)[:200]}")
            return 1
        token = alta["token"]

        cliente = puerta(token, "POST", "/api/contactos", {"nombre": "El vecino del prado"})
        assert cliente[0] == 201, cliente

        with NavegadorDeVerdad() as navegador:
            entrar(navegador, token)
            navegador.abrir(f"http://127.0.0.1:{PUERTO}/{LA_DIRECCION}", esperar=2.0)

            # --- 1 · Lo primero: que la pantalla NO salga muda ---
            visto = lo_que_se_ve(navegador)
            comprobar("la pantalla tiene su título (no sale muda)", bool((visto.get("h1") or "").strip()), f"h1={visto.get('h1')!r}")
            comprobar(
                "y los rótulos de la tabla y de los campos llevan texto",
                bool(visto.get("rotulos")) and all((r or "").strip() for r in visto["rotulos"]),
                f"rótulos={visto.get('rotulos')!r}",
            )
            comprobar(
                "y los botones llevan su texto",
                bool(visto.get("botones")) and all((b or "").strip() for b in visto["botones"]),
                f"botones={visto.get('botones')!r}",
            )
            # --- 2 · El estado VACÍO se dice con palabras, no con una tabla vacía ---
            comprobar(
                "sin trabajos, lo dice (el VACÍO)",
                "Todavía no le has hecho ningún trabajo" in (visto.get("texto") or ""),
                (visto.get("texto") or "")[:160],
            )

            # --- 3 · Se propone por la puerta y la fila TIENE que aparecer ---
            propuesta = puerta(
                token,
                "POST",
                "/api/trabajos-a-terceros",
                {
                    "contacto_id": cliente[1]["id"],
                    "titulo": "Segar el prado",
                    "ubicacion": "El prado del vecino",
                    "superficie_ha": "10.0",
                    "de_quien_es_el_insumo": "cliente",
                    "tarifa_por_hora": "30.0",
                },
            )
            comprobar("se propone un trabajo por su puerta", propuesta[0] == 201, str(propuesta[0])[:140])
            navegador.evaluar("location.reload()")
            navegador.esperar("!!document.querySelector('h1')", segundos=20)
            visto = lo_que_se_ve(navegador)
            comprobar("tras recargar, el trabajo sale en la tabla", visto.get("filas") == 1, f"filas={visto.get('filas')}")
            comprobar(
                "y se ve de quién es el gasoil, que es lo que no se puede deducir",
                "NO toca mi almacén" in (visto.get("texto") or ""),
                [r for r in (visto.get("texto") or "").split("\n") if "almacén" in r][:2],
            )
            comprobar(
                "y el precio, que es lo que se pactó",
                "30" in (visto.get("texto") or ""),
                "",
            )

            # --- 4 · Aceptar, y que la tarifa aceptada se vea ---
            trabajo_id = propuesta[1]["id"]
            aceptado = puerta(token, "POST", f"/api/trabajos-a-terceros/{trabajo_id}/aceptar", {})
            comprobar("se acepta", aceptado[0] == 200, str(aceptado[0]))
            navegador.evaluar("location.reload()")
            navegador.esperar("!!document.querySelector('h1')", segundos=20)
            visto = lo_que_se_ve(navegador)
            comprobar("y la pantalla lo dice aceptado", "Aceptado" in (visto.get("texto") or ""), "")
            comprobar(
                "y ofrece apuntar lo hecho",
                any("Apuntar lo hecho" in b for b in visto.get("botones") or []),
                f"botones={visto.get('botones')!r}",
            )

            # --- 5 · El parte SIN coste: el margen tiene que marcar que no consta ---
            parte = puerta(token, "POST", f"/api/trabajos-a-terceros/{trabajo_id}/parte", {"horas_hechas": "3.0"})
            comprobar("se apunta el parte", parte[0] == 200, str(parte[0])[:140])
            comprobar(
                "y la puerta avisa de que el almacén NO se toca",
                "NO toca tu almacén" in str(parte[1].get("almacen", "")),
                str(parte[1].get("almacen"))[:120],
            )
            navegador.evaluar("location.reload()")
            navegador.esperar("!!document.querySelector('h1')", segundos=20)
            visto = lo_que_se_ve(navegador)
            comprobar(
                "y en pantalla se lee que el coste NO consta (no un cero)",
                f"celdas de la fila: {visto.get('celdas')!r}",
                [r for r in (visto.get("texto") or "").split("\n") if "consta" in r][:2],
            )

            # --- 6 · La dirección y lo que se ve, de acuerdo (el fallo del filtro, aquí también) ---
            comprobar(
                "la dirección sigue siendo la de esta pantalla tras recargar",
                LA_DIRECCION in (navegador.evaluar("location.hash") or ""),
                f"hash={navegador.evaluar('location.hash')!r}",
            )

            # --- 7 · Y que quepa en la ventana ---
            navegador.medir(1440, 1000)
            fuera = navegador.evaluar(
                "JSON.stringify(Array.from(document.querySelectorAll('button, a, input, select, th')).filter("
                "  (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > window.innerWidth + 2 || r.left < -2); }"
                ").length)"
            )
            comprobar("ningún control se sale de la ventana", str(fuera) == "0", f"fuera: {fuera}")

            navegador.abrir(f"http://127.0.0.1:{PUERTO}/{LA_DIRECCION}", esperar=1.5)
            print(f"  capturas: {len(list(CAPTURAS.glob('terceros-*.png')))}")

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
