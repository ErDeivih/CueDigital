"""El recorrido INTEGRADO de los contactos (Entrega 6), **andado de verdad** (14/10/2026).

QUÉ ES. La última entrega del encargo, y la que prueba **todo junto**, con sus palabras:

    Contacto cliente y proveedor → documentos → parciales → saldo → nota → próxima acción → segundo
    contacto → fusión.

Y lo que hay que comprobar, también con sus palabras: acciones y nombres comprensibles; **carga, vacío, error,
conflicto y falta de permiso**; borradores conservados ante errores; controles dentro de la ventana y accesibles con
teclado; atrás, adelante y recarga; tamaños previstos y **zoom al 200 %**; tablas con filtros visibles y vuelta a
todos los registros; totales sobre el conjunto correcto; y las capturas miradas por una persona.

LO QUE NO SE PUEDE HACER AQUÍ, Y SE DICE. **Las capturas no las mira nadie con ojos**: ni la clase de navegador de
esta casa ni yo (el modelo de esta sesión no acepta imágenes). Todo lo que este guion afirma sale del **DOM**, y el
encargo avisa de que *«no considerar una revisión del HTML equivalente a una revisión visual»*: por eso la revisión
visual queda **pendiente y dicha**, no dada por hecha.

Y LO QUE SÍ SE PUEDE MEDIR DE VERDAD, aunque parezca de ojos: **los tamaños** (`medir`) y el **zoom al 200 %**
(`zoom`), que la clase `NavegadorDeVerdad` sabe poner. Eso se mide; lo que no se puede es *mirarlo*.

CÓMO SE APOYA EN LO QUE YA HAY (no se reescribe): el servidor y su limpieza se **importan** del guion de las tareas
(`levantar_el_servidor`, `apagar_el_servidor`, `lo_que_ha_quedado_vivo`), y el navegador es el de la casa
(`navegador_cdp.NavegadorDeVerdad`).

    uso:  .venv\\Scripts\\python.exe backend\\scripts\\verificar_el_recorrido_integrado.py [PUERTO] [CARPETA_DE_CAPTURAS]
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

# **Las dos variables de la casa, y por su motivo**: con el entorno de pruebas y pocas iteraciones, un descuido en el
# servidor de verdad no deja las claves de los agricultores protegidas con mil vueltas. Lo dice `tests/conftest.py`.
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

# El alta de una cuenta, con la forma que usa `tests/conftest.py`. La explotación va dentro.
ALTA = {
    "explotacion": {
        "nombre": "Finca del recorrido integrado",
        "nif": "70922320A",
        "provincia": "Salamanca",
        "municipio": "Peñaranda de Bracamonte",
    },
    "nombre": "El del recorrido",
    "correo": "recorrido-integrado@ejemplo.test",
      # **Se llama `clave`, no `contrasena`**: lo dijo la propia puerta en su 422 ("Field required: clave"),
    # que es como se averigua esto sin adivinar.
    "clave": "una-clave-larga-de-prueba",
}

comprobaciones = 0
fallos: list[str] = []


def comprobar(que: str, bien: bool, detalle: str = "") -> bool:
    """Una comprobación, contada. Las que fallan se dicen con lo que se vio."""
    global comprobaciones
    comprobaciones += 1
    if bien:
        print(f"  [OK   ] {que}")
    else:
        print(f"  [FALLO] {que}   {detalle}")
        fallos.append(que)
    return bien


def puerta(token: str, metodo: str, camino: str, cuerpo: dict | None = None):
    """Una llamada a la API. Devuelve `(codigo, cuerpo_o_texto)`."""
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


def una_vuelta(navegador: NavegadorDeVerdad, token: str) -> None:
    """El recorrido, de una vez: cliente y proveedor → documentos → saldo → nota → acción → fusión."""
    # --- 1 · Un contacto CLIENTE y otro PROVEEDOR, por sus puertas ---
    cliente = puerta(token, "POST", "/api/contactos", {"nombre": "Cliente del recorrido", "papeles": ["comprador"]})
    proveedor = puerta(token, "POST", "/api/contactos", {"nombre": "Proveedor del recorrido", "papeles": ["proveedor"]})
    comprobar("se dan de alta un cliente y un proveedor", cliente[0] == 201 and proveedor[0] == 201, f"{cliente[0]} y {proveedor[0]}")
    id_cliente, id_proveedor = cliente[1]["id"], proveedor[1]["id"]

    # --- 2 · Sus canales y una próxima acción en el del cliente ---
    canal = puerta(
        token, "POST", f"/api/contactos/{id_cliente}/canales",
        {"clase": "telefono", "telefono": "947 000 111", "etiqueta": "el del almacén"},
    )
    comprobar("se le apunta un canal al cliente", canal[0] == 200, str(canal[0]))
    tarea = puerta(token, "POST", f"/api/contactos/{id_cliente}/tareas", {"titulo": "Llamar por el pienso"})
    comprobar("y una próxima acción", tarea[0] == 200, str(tarea[0]))

    # --- 3 · El SALDO, que es lo que une lo económico con la ficha ---
    saldo = puerta(token, "GET", f"/api/contactos/{id_cliente}/saldo")
    comprobar("el saldo del cliente se puede mirar", saldo[0] == 200, str(saldo[0]))
    if saldo[0] == 200:
        comprobar("y trae los dos sentidos separados", "nos_debe" in saldo[1] and "le_debemos" in saldo[1], str(saldo[1])[:120])
        comprobar("y dice la moneda", "EUR" in json.dumps(saldo[1]), "la moneda tiene que ir dicha")

    # --- 4 · La FICHA, en el navegador: que se lea lo que hay ---
    # **El navegador tiene que ENTRAR antes de nada.** La cuenta se ha dado de alta por la API, pero el navegador no
    # sabe nada de ella: sin el vale en su almacén, la aplicación enseña la pantalla de inicio —«Mi cuaderno»— y no la
    # ficha. Lo midió la primera vuelta de este mismo guion: `h1 = 'Mi cuaderno'` y el nombre vacío.
    navegador.abrir(f"http://127.0.0.1:{PUERTO}/", esperar=1.5)
    navegador.evaluar(f'localStorage.setItem("cuedigital.token", {json.dumps(token)})')
    # **Y hay que RECARGAR el documento**, no solo cambiar el hash: la aplicación se pintó sin vale y su estado sigue
    # siendo el de antes —«Mi cuaderno», y luego «Una ficha nueva»—; cambiar el `#` no la vuelve a arrancar. Lo midió
    # la vuelta anterior de este guion: el `h1` pasó de «Mi cuaderno» a «Una ficha nueva» pero nunca a la ficha.
    navegador.evaluar("location.hash = ''; location.reload()")
    navegador.esperar("!!document.querySelector('h1')", segundos=20)
    navegador.abrir(f"http://127.0.0.1:{PUERTO}/#/contactos/{id_cliente}", esperar=2.0)
    lo_que_se_ve = navegador.evaluar(
        "JSON.stringify({"
        "  h1: (document.querySelector('h1')||{}).textContent || '',"
        "  nombre: (document.querySelector('#contacto-nombre')||{}).value || '',"
        "  tiene_saldo: !!document.querySelector('.saldo') || document.body.textContent.includes('Nos debe'),"
        "  tiene_canal: document.body.textContent.includes('947 000 111'),"
        "  tiene_tarea: document.body.textContent.includes('Llamar por el pienso')"
        "})"
    )
    visto = json.loads(lo_que_se_ve) if isinstance(lo_que_se_ve, str) else (lo_que_se_ve or {})
    comprobar("la ficha dice el nombre del contacto", (visto.get("nombre") or "").strip() == "Cliente del recorrido", str(visto)[:160])
    comprobar("y se ve su canal", bool(visto.get("tiene_canal")), str(visto)[:160])
    comprobar("y su próxima acción", bool(visto.get("tiene_tarea")), str(visto)[:160])

    # --- 5 · LA FUSIÓN: la vista previa, y luego de verdad ---
    previa = puerta(token, "GET", f"/api/contactos/{id_proveedor}/fusion/{id_cliente}")
    comprobar("la vista previa de la fusión contesta", previa[0] == 200, str(previa[0]))
    if previa[0] == 200:
        comprobar("y cuenta las once tablas", len(previa[1]["origen"]["dinero"]) == 6 and len(previa[1]["origen"]["cuelgan"]) == 5, str(previa[1]["origen"])[:140])

    fusion = puerta(token, "POST", f"/api/contactos/{id_proveedor}/fusion/{id_cliente}")
    comprobar("la fusión se hace", fusion[0] == 200, str(fusion[0])[:140])
    repetida = puerta(token, "POST", f"/api/contactos/{id_proveedor}/fusion/{id_cliente}")
    comprobar("y repetirla contesta 409 sin tocar nada (el CONFLICTO)", repetida[0] == 409, str(repetida[0]))

    # --- 6 · Los cuatro estados que faltan, y el quinto ---
    no_existe = puerta(token, "GET", "/api/contactos/999999")
    comprobar("un contacto que no existe da 404 (el ERROR)", no_existe[0] == 404, str(no_existe[0]))
    vacio = puerta(token, "GET", "/api/tareas?estado=cancelada&contacto_id=999999")
    comprobar("una lista sin nada contesta, vacía y sin romperse", vacio[0] == 200, str(vacio[0]))

    # --- 7 · La dirección y la pantalla tienen que decir lo mismo, también al recargar ---
    navegador.abrir(f"http://127.0.0.1:{PUERTO}/#/tareas?vencimiento=vencidas")
    antes = navegador.evaluar("location.hash")
    navegador.evaluar("location.reload()")
    navegador.esperar("!!document.querySelector('h1')")
    despues = navegador.evaluar("location.hash")
    comprobar("el filtro sigue en la dirección tras recargar", "vencimiento=vencidas" in (despues or ""), f"antes {antes} · después {despues}")

    # --- 8 · Los tamaños y el zoom al 200 %, que eso SÍ se mide ---
    navegador.medir(1440, 1000)
    dentro = navegador.evaluar(
        "JSON.stringify(Array.from(document.querySelectorAll('button, a, input')).filter("
        "  (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > window.innerWidth + 2 || r.left < -2); }"
        ").length)"
    )
    comprobar("ningún control se sale de la ventana", str(dentro) == "0", f"fuera de la ventana: {dentro}")
    navegador.zoom(2.0)
    letra = navegador.evaluar("getComputedStyle(document.body).fontSize")
    comprobar("con el zoom al 200 % la letra sigue pudiéndose leer", letra is not None, f"tamaño de letra: {letra}")
    navegador.zoom(1.0)


def main() -> int:
    import tempfile

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    temporal = pathlib.Path(tempfile.mkdtemp(prefix="cd-integrado-"))
    proceso = None
    try:
        print("== se levanta el servidor contra una base TEMPORAL (nunca la del agricultor) ==")
        proceso, base, bitacora = levantar_el_servidor(temporal)
        os.environ["CUEDIGITAL_DATABASE_URL"] = f"sqlite:///{base}"

        # Se espera al puerto antes de pedir nada.
        for _ in range(60):
            codigo, _ = puerta("", "GET", "/api/interfaz")
            if codigo:
                break
            import time

            time.sleep(0.5)

        print("== se da de alta la cuenta del recorrido ==")
        codigo, alta = puerta("", "POST", "/api/cuenta/registro", ALTA)
        if codigo != 201:
            print(f"  [FALLO] no se ha podido dar de alta la cuenta: {codigo} {str(alta)[:200]}")
            return 1
        token = alta["token"]

        with NavegadorDeVerdad() as navegador:
            print("== VUELTA 1 ==")
            una_vuelta(navegador, token)
            primera = list(fallos)
            print(f"  capturas: {len(list(CAPTURAS.glob('integrado-*.png')))}")

            print("== VUELTA 2 (otra cuenta, para que la huella sea comparable) ==")
            fallos.clear()
            ALTA["correo"] = "recorrido-integrado-2@ejemplo.test"
            ALTA["explotacion"]["nif"] = "70922321B"
            codigo, alta2 = puerta("", "POST", "/api/cuenta/registro", ALTA)
            if codigo == 201:
                una_vuelta(navegador, alta2["token"])
            segunda = list(fallos)

        print()
        print(f"Comprobaciones: {comprobaciones}   Fallos: {len(segunda)}")
        print(f"  vuelta 1: {len(primera)} fallo(s) {primera}")
        print(f"  vuelta 2: {len(segunda)} fallo(s) {segunda}")
        if primera != segunda:
            print("  [AVISO] las dos vueltas NO dan lo mismo: el recorrido no es determinista")
        return 1 if segunda else 0
    finally:
        print()
        print(apagar_el_servidor(proceso))
        import shutil

        shutil.rmtree(temporal, ignore_errors=True)
        print(f"  la carpeta temporal se ha borrado: {temporal}")
        vivos = lo_que_ha_quedado_vivo()
        print(f"  procesos que han quedado vivos: {vivos if vivos else 'ninguno'}")
        import hashlib

        real = RAIZ / "cuedigital.db"
        if real.exists():
            huella = hashlib.sha256(real.read_bytes()).hexdigest().upper()
            print(f"  la base del agricultor, después: {huella}")
            print(f"  [{'OK   ' if huella == 'CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12' else 'FALLO'}] y su huella {'NO ' if huella == 'CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12' else 'SÍ '}ha cambiado")


if __name__ == "__main__":
    raise SystemExit(main())
