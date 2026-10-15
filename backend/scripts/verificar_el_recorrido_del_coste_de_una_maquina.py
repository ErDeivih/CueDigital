"""**Lo que ha costado tener una maquina parada**, andado desde la pantalla (CRM-07 #7, 14/10/2026).

El informe del dueno lo pide con estas palabras: «**el coste en la ficha de la maquina**». Y el coste **no
se apunta en la averia**: lo guarda el gasto, que dice de que averia sale (`gastos.averia_id`). Eso ya
estaba calculado en la puerta del coste; lo que faltaba era **que la ficha lo ensenara**, y este recorrido
lo anda:

  1. **El total**, que lo calcula el servidor: una reparacion de 900,00 EUR.
  2. ***Y que diga que hay un gasto SIN IMPORTE.*** Es el caso que este modulo no perdona: un total que solo
     suma la mitad y **no lo dice** parece el total entero. Aqui hay dos gastos y uno no tiene importe, asi
     que la ficha tiene que decir las dos cosas: la cifra **y** el aviso.
  3. **Y cada averia, lo que costo la suya**, con su nombre.
  4. **Y que la ficha siga diciendolo despues de RECARGAR** — que es lo que un unitario no prueba.
  5. **Y una maquina sin ningun gasto apuntado NO dice «0,00 EUR»**: dice que no se sabe. *No saberlo y ser
     cero no son lo mismo*, y este programa no los confunde en ningun sitio.

Uso:  python scripts/verificar_el_recorrido_del_coste_de_una_maquina.py <direccion>

      La direccion **se pasa como primer argumento y es obligatoria**: `_api` no la recibe, la lee de la
      constante `DIRECCION` de SU modulo. Sin pasarla, el sintoma es «conexion rechazada».
"""

from __future__ import annotations

import json
import sys

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


def una_maquina(token: str, nombre: str) -> dict:
    hecho = _api(
        "/api/maquinaria",
        token,
        {"nombre": nombre, "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
        metodo="POST",
    )
    if not isinstance(hecho, dict) or not hecho.get("id"):
        raise SystemExit(f"la puerta no ha devuelto la maquina: {hecho!r}")
    return hecho


def una_averia(token: str, maquina_id: int, que_paso: str) -> dict:
    hecho = _api(
        f"/api/maquinaria/{maquina_id}/averias",
        token,
        {"fecha": "2026-04-01", "que_paso": que_paso, "resuelta": False},
        metodo="POST",
    )
    if not isinstance(hecho, dict) or not hecho.get("id"):
        raise SystemExit(f"la puerta no ha devuelto la averia: {hecho!r}")
    return hecho


def un_gasto(token: str, campana_id, clave: str, concepto: str, **campos) -> dict:
    cuerpo = {"campana_id": campana_id, "concepto": concepto, "categoria": "reparacion", "clave_de_reenvio": clave}
    cuerpo.update(campos)
    hecho = _api("/api/gastos", token, cuerpo, metodo="POST")
    # **La puerta del gasto devuelve un ENVOLTORIO** (`{gasto: {...}, ya_estaba, avisos}`), no el gasto:
    # lo dijo ella misma al fallar, con el objeto entero delante. Se aceptan las dos formas porque lo que
    # se quiere es el identificador, y una puerta que devuelva el gasto suelto tambien vale.
    el_gasto = hecho.get("gasto") if isinstance(hecho, dict) else None
    if not isinstance(el_gasto, dict):
        el_gasto = hecho if isinstance(hecho, dict) and hecho.get("id") else None
    if not isinstance(el_gasto, dict) or not el_gasto.get("id"):
        raise SystemExit(f"la puerta no ha devuelto el gasto: {hecho!r}")
    return el_gasto


def main() -> int:
    print(f"== Lo que ha costado tener una maquina parada  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    campana = _api("/api/campanas/actual", token, metodo="GET")
    if not isinstance(campana, dict) or not campana.get("id"):
        raise SystemExit(f"no he podido averiguar la campana de la finca: {campana!r}")

    marca = str(int(__import__("time").time()))
    con_gastos = una_maquina(token, f"El Landini de la prueba {marca}")
    sin_gastos = una_maquina(token, f"El Fendt de la prueba {marca}")
    la_suya = una_averia(token, con_gastos["id"], "Se rompio el eje del ventilador")
    una_averia(token, sin_gastos["id"], "Se rompio el embrague")
    # **Dos gastos y uno SIN IMPORTE**: es el caso que importa, porque el total tiene que salir **y** el
    # aviso tambien. Si solo se apuntara el de 900, la prueba no diria nada de la regla que mas importa.
    un_gasto(token, campana["id"], f"coste-1-{marca}", "El eje del ventilador",
             maquina_id=con_gastos["id"], averia_id=la_suya["id"], importe="900.00")
    un_gasto(token, campana["id"], f"coste-2-{marca}", "La mano de obra",
             maquina_id=con_gastos["id"], averia_id=la_suya["id"])
    print("  (una maquina con una reparacion de 900,00 EUR y otra sin importe, y otra maquina sin nada)")

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )

            print("\n1. LA FICHA DICE LO QUE HA COSTADO")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{con_gastos['id']}", esperar=3.0)
            if not comprobar(
                bool(nav.esperar("document.querySelectorAll('#pantalla *').length > 20", segundos=25)),
                "la ficha de la maquina abre por su direccion",
            ):
                return 1
            # Se **espera** a que el coste este pintado, en vez de leer el texto una sola vez: es la
            # leccion del recorrido hermano -«sin esas esperas saldrian falsos rojos»-.
            nav.esperar("document.querySelector('#pantalla').innerText.indexOf('900,00') >= 0", segundos=25)
            texto = nav.evaluar("document.querySelector('#pantalla').innerText") or ""

            comprobar("900,00" in texto, "la ficha dice lo que ha costado la reparacion", encontre=texto[-300:])
            comprobar("ha costado tenerla parada" in texto, "y lo dice con la frase de la casa", encontre=texto[-300:])
            comprobar(
                "no tiene importe" in texto,
                "***y dice que hay un gasto SIN IMPORTE***, en vez de dar el total por bueno",
                esperaba="el aviso de que un gasto no tiene importe",
                encontre=texto[-300:],
            )
            comprobar("Costó: 900,00" in texto, "y la averia dice lo que costo la suya", encontre=texto[-300:])

            print("\n2. Y SE RECARGA LA PAGINA: sigue diciendolo")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{con_gastos['id']}", esperar=3.0)
            nav.esperar("document.querySelector('#pantalla').innerText.indexOf('900,00') >= 0", segundos=25)
            texto2 = nav.evaluar("document.querySelector('#pantalla').innerText") or ""
            comprobar("900,00" in texto2 and "no tiene importe" in texto2, "lo guardado sigue despues de recargar", encontre=texto2[-300:])

            print("\n3. Y UNA MAQUINA SIN GASTOS NO DICE «0,00 EUR»")
            nav.abrir(f"{DIRECCION}/#/maquinaria/{sin_gastos['id']}", esperar=3.0)
            nav.esperar("document.querySelectorAll('#pantalla *').length > 20", segundos=25)
            # **Se miran SOLO las lineas del coste**, no la ficha entera (14/10/2026). Mirando toda la
            # ficha, el «no dice 0,00» fallaba por **otros** ceros que no son el coste (las horas, los
            # equipos del cuaderno), y el fallo apuntaba al sitio equivocado. Es la leccion de siempre:
            # **leer un solo contenedor**, y el que toca.
            suyas3 = nav.evaluar(
                "Array.from(document.querySelectorAll('#pantalla .pista-campo, #pantalla .apunte-detalle'))"
                ".map((el) => (el.innerText || '').replace(/\\s+/g, ' ').trim())"
                ".filter((t) => t && (t.indexOf('costado') >= 0 || t.indexOf('Cost') >= 0"
                " || t.indexOf('gasto') >= 0))"
            ) or []
            junto3 = " · ".join(suyas3)
            comprobar(
                any("no hay ningún gasto apuntado" in linea for linea in suyas3),
                "sin gastos dice que no se sabe, que es la verdad",
                esperaba="«no hay ningún gasto apuntado»",
                encontre=junto3 or "(ninguna linea del coste)",
            )
            comprobar(
                "0,00" not in junto3,
                "***y NO dice «0,00 EUR»***: no saberlo y ser cero no son lo mismo",
                esperaba="ningun 0,00 en la linea del coste",
                encontre=junto3 or "(ninguna linea del coste)",
            )
    except RuntimeError as fallo:
        print(f"  >> el navegador no ha podido: {fallo}")
        FALLOS.append(f"el navegador no ha podido ({fallo})")

    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
    for fallo in FALLOS:
        print(f"  - {fallo}")
    return 1 if FALLOS else 0


if __name__ == "__main__":
    raise SystemExit(main())
