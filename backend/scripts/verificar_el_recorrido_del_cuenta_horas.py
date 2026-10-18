"""**El cuenta-horas, andado desde la PANTALLA** (CRM-07 #8, 16/10/2026).

El encargo lo pide asi: *«lecturas de contador fechadas y unidad; correcciones auditadas, sustitucion del
contador, datos faltantes. ***No inventar horas ni reducir acumulados silenciosamente***»*.

Y esto se anda **por los formularios**, no por la puerta: el revisor lo dejo dicho —*«no sustituir los
formularios por altas mediante API»*—, porque un campo que solo existe en el servidor no es una funcion
para el agricultor.

Lo que se comprueba, en orden:

  1. Una maquina **sin lecturas** dice que no hay ninguna, y **no** un «0 h».
  2. El boton de apuntar **abre el formulario**, y el formulario trae sus campos.
  3. Se apunta una lectura y la ficha dice lo que **marca**.
  4. Una segunda lectura y la ficha dice lo que **ha subido**.
  5. **Corregir** sale relleno con lo que habia.
  6. **Anular** pide el motivo, y la lectura queda tachada y deja de contar.
  7. **Se recarga** la pagina y todo sigue.
  8. Y el ***retroceso intermedio*** (1.000 -> 1.200 -> 1.100 -> 1.300) no se presenta como un total.

Uso:  python scripts/verificar_el_recorrido_del_cuenta_horas.py <direccion>
"""

from __future__ import annotations

import json
import re
import sys
import time

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


def pulsar(nav, selector: str) -> None:
    """Pulsa algo. **No devuelve nada**: un boton que existe no es un boton que ha hecho su trabajo."""
    nav.evaluar(
        "(() => { const b = document.querySelector(%s); if (b) b.click(); return true; })()"
        % json.dumps(selector)
    )


def escribe(nav, casilla: str, texto: str) -> bool:
    return bool(
        nav.evaluar(
            "(() => { const c = document.getElementById(%s); if (!c) return false;"
            " c.value = %s;"
            " c.dispatchEvent(new Event('input', { bubbles: true }));"
            " c.dispatchEvent(new Event('change', { bubbles: true })); return true; })()"
            % (json.dumps(casilla), json.dumps(texto))
        )
    )


def elTexto(nav) -> str:
    """Lo que se lee en la pantalla, **con las cifras normalizadas**.

    ***El punto de millar no se puede dar por hecho*** (17/10/2026). `Number(1000).toLocaleString("es-ES")`
    escribe «1.000» con el ICU completo, pero el Chrome del arnes escribe **«1000»**: buscar «1.000 h» no
    encontraba nada **aunque la pantalla lo estaba ensenando**, y me paso una ronda entera persiguiendo un
    fantasma por eso. Aqui se quita el punto **solo entre digitos** -que en espanol es el de millar, porque
    los decimales van con coma-, y asi la comprobacion vale con los dos formatos.
    """
    texto = nav.evaluar("document.querySelector('#pantalla').innerText") or ""
    return re.sub(r"(?<=\d)\.(?=\d)", "", texto)


def laFicha(nav, direccion: str, maquina_id: int, *, espera: str) -> str:
    nav.abrir(f"{direccion}/#/maquinaria/{maquina_id}", esperar=3.0)
    nav.esperar(
        f"document.querySelector('#pantalla').innerText.indexOf({json.dumps(espera)}) >= 0", segundos=25
    )
    return elTexto(nav)


def main() -> int:
    print(f"== El cuenta-horas, por la pantalla  ({DIRECCION}) ==")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    marca = str(int(time.time()))
    maquina = _api(
        "/api/maquinaria",
        token,
        {
            "nombre": f"El del recorrido {marca}",
            "clase": "tractor",
            "propiedad": "propia",
            "disponibilidad": "disponible",
        },
        metodo="POST",
    )
    if not isinstance(maquina, dict) or not maquina.get("id"):
        raise SystemExit(f"la puerta no ha devuelto la maquina: {maquina!r}")
    suya = maquina["id"]

    try:
        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
            )

            print("\n1. UNA MAQUINA SIN LECTURAS LO DICE, Y NO ENSENA UN CERO")
            texto = laFicha(nav, DIRECCION, suya, espera="cuenta-horas")
            comprobar("no hay ninguna lectura apuntada" in texto, "dice que no hay ninguna lectura")
            comprobar(
                "Marca ahora" not in texto and "0 h" not in texto,
                "***y NO ensena un cero ni una marca inventada***",
                encontre=texto[-240:],
            )

            print("\n2. EL BOTON DE APUNTAR ABRE EL FORMULARIO")
            pulsar(nav, '#pantalla [data-accion="maquina-lectura-nueva"]')
            comprobar(
                bool(nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)),
                "el formulario sale, con su casilla del valor",
            )
            comprobar(
                bool(nav.esperar("Boolean(document.getElementById('lectura-fecha'))", segundos=10)),
                "y con la fecha",
            )
            comprobar(
                "Horas" in elTexto(nav) and "Kilómetros" in elTexto(nav),
                "***y la unidad se ELIGE: horas o kilometros***",
                esperaba="las dos opciones a la vista",
                encontre=elTexto(nav)[-200:],
            )

            print("\n3. SE APUNTA UNA LECTURA")
            escribe(nav, "lectura-fecha", "2026-01-01")
            escribe(nav, "lectura-valor", "1000")
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            comprobar(
                bool(nav.esperar("!document.getElementById('lectura-valor')", segundos=25)),
                "***el guardado entra***: el formulario se cierra cuando el servidor lo acepta",
            )
            # ***Se vuelve a abrir la ficha*** en vez de mirar la que hay: al guardar, el formulario se
            # cierra **antes** de que la ficha se pida otra vez y se repinte, asi que leer justo despues
            # lee la ficha vieja. Abrirla de nuevo la pide y espera a que este -y el `encontre` mira la
            # seccion del cuenta-horas, no el final de la pantalla, que era lo que me dejaba ciega.
            texto = laFicha(nav, DIRECCION, suya, espera="Marca ahora")
            comprobar(
                "Marca ahora: 1000 h" in texto,
                "y la ficha dice lo que marca",
                esperaba="«Marca ahora: 1000 h»",
                encontre=texto[texto.find("cuenta-horas") :][:260],
            )
            comprobar(
                "Ha subido" not in texto,
                "y NO dice cuanto ha subido: con una sola lectura no se sabe",
            )

            print("\n4. UNA SEGUNDA LECTURA Y YA SE SABE LO QUE HA SUBIDO")
            pulsar(nav, '#pantalla [data-accion="maquina-lectura-nueva"]')
            nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)
            escribe(nav, "lectura-fecha", "2026-02-01")
            escribe(nav, "lectura-valor", "1250")
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            comprobar(
                bool(nav.esperar("!document.getElementById('lectura-valor')", segundos=25)),
                "la segunda lectura entra",
            )
            comprobar(
                bool(nav.esperar("document.querySelector('#pantalla').innerText.indexOf('250 h') >= 0", segundos=15)),
                "y dice las 250 horas que ha subido",
                encontre=elTexto(nav)[-240:],
            )

            print("\n5. CORREGIR SALE RELLENO Y CONSERVA LO QUE NO SE TOCA")
            primera = _api(f"/api/maquinaria/{suya}", token, metodo="GET")
            la_primera = (primera.get("lecturas") or [])[0]
            pulsar(nav, f'#pantalla [data-accion="maquina-lectura-corregir"][data-id="{la_primera["id"]}"]')
            comprobar(
                bool(nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)),
                "el formulario de corregir se abre",
            )
            comprobar(
                nav.evaluar("(document.getElementById('lectura-valor') || {}).value === '1000'"),
                "***y sale RELLENO con lo que habia***",
                encontre=str(nav.evaluar("(document.getElementById('lectura-valor') || {}).value")),
            )
            escribe(nav, "lectura-valor", "1100")
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            nav.esperar("!document.getElementById('lectura-valor')", segundos=25)
            texto = laFicha(nav, DIRECCION, suya, espera="Marca ahora")
            comprobar(
                "Marca ahora: 1250 h" in texto,
                "la correccion entra, y la marca de la ultima lectura no cambia",
                esperaba="«Marca ahora: 1250 h»",
                encontre=texto[texto.find("cuenta-horas") :][:260],
            )

            print("\n6. ANULAR PIDE EL MOTIVO, Y LA LECTURA DEJA DE CONTAR")
            segunda = _api(f"/api/maquinaria/{suya}", token, metodo="GET")
            la_segunda = (segunda.get("lecturas") or [])[-1]
            pulsar(nav, f'#pantalla [data-accion="maquina-lectura-anular"][data-id="{la_segunda["id"]}"]')
            comprobar(
                bool(nav.esperar("Boolean(document.getElementById('lectura-motivo'))", segundos=20)),
                "el formulario de anular pide el motivo",
            )
            escribe(nav, "lectura-motivo", "Me equivoque de maquina")
            pulsar(nav, '#pantalla [data-accion="maquina-guardar"]')
            nav.esperar("!document.getElementById('lectura-motivo')", segundos=25)
            texto = elTexto(nav)
            comprobar("anulada" in texto, "***la lectura queda tachada***", encontre=texto[-240:])
            comprobar(
                "Ha subido" not in texto,
                "***y deja de contar: ya no se puede afirmar cuanto ha subido***",
                encontre=texto[-240:],
            )

            print("\n7. Y SE RECARGA LA PAGINA: SIGUE")
            texto = laFicha(nav, DIRECCION, suya, espera="cuenta-horas")
            # ***Ojo con lo que se espera***: se anulo la lectura de 1.250, asi que lo que **marca** el
            # contador es la ultima que vale, que es la corregida: 1.100. Si aqui saliera 1.250 seria que
            # la anulada sigue contando, que es justo lo que no puede pasar.
            comprobar(
                "Marca ahora: 1100 h" in texto,
                "lo apuntado sigue despues de recargar, y la anulada no es la que marca",
                esperaba="«Marca ahora: 1100 h»",
                encontre=texto[texto.find("cuenta-horas") :][:260],
            )
            comprobar("anulada" in texto, "y la anulada sigue tachada")

            print("\n8. UN RETROCESO EN MEDIO NO SE PRESENTA COMO TOTAL")
            otra = _api(
                "/api/maquinaria",
                token,
                {
                    "nombre": f"El del retroceso {marca}",
                    "clase": "tractor",
                    "propiedad": "propia",
                    "disponibilidad": "disponible",
                },
                metodo="POST",
            )
            for indice, (dia, valor) in enumerate(
                [("2026-01-01", 1000), ("2026-02-01", 1200), ("2026-03-01", 1100), ("2026-04-01", 1300)], 1
            ):
                _api(
                    f"/api/maquinaria/{otra['id']}/lecturas",
                    token,
                    {"fecha": dia, "valor": valor, "unidad": "horas"},
                    metodo="POST",
                )
            texto = laFicha(nav, DIRECCION, otra["id"], espera="cuenta-horas")
            comprobar(
                # ***No se busca «300 h» a secas***: esta dentro de «1.300 h», que es lo que marca el
                # contador, y la comprobacion pasaba por el sitio equivocado. Se busca la FRASE del total.
                "Ha subido desde la primera lectura: 300" not in texto,
                "***no presenta 300 como total afirmado: el tramo no cuadra***",
                encontre=texto[texto.find("cuenta-horas") :][:260],
            )
            comprobar(
                "marca menos que la anterior" in texto,
                "***y la bajada se ENSENA***",
                encontre=texto[texto.find("cuenta-horas") :][:260],
            )
            print("\n9. Y LA UNIDAD SE ELIGE DE VERDAD: SE APUNTA EN KILOMETROS")
            tercera = _api(
                "/api/maquinaria",
                token,
                {
                    "nombre": f"La furgoneta {marca}",
                    "clase": "tractor",
                    "propiedad": "propia",
                    "disponibilidad": "disponible",
                },
                metodo="POST",
            )
            laFicha(nav, DIRECCION, tercera["id"], espera="cuenta-horas")
            pulsar(nav, "#pantalla [data-accion=maquina-lectura-nueva]")
            nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)
            escribe(nav, "lectura-fecha", "2026-05-01")
            escribe(nav, "lectura-valor", "50000")
            # ***Se elige pulsando la opción, como lo haria el agricultor.*** Contar atributos no
            # demuestra que se pueda elegir; pulsarlo y ver **lo que se guarda**, si.
            comprobar(
                bool(
                    nav.evaluar(
                        "(() => { const bs = Array.from(document.querySelectorAll('#pantalla [data-accion]'));"
                        " const b = bs.find((x) => (x.textContent || '').trim() === 'Kilómetros');"
                        " if (b) b.click(); return Boolean(b); })()"
                    )
                ),
                "la opción de kilómetros se puede pulsar",
            )
            nav.esperar("true", segundos=0.6)
            pulsar(nav, "#pantalla [data-accion=maquina-guardar]")
            comprobar(
                bool(nav.esperar("!document.getElementById('lectura-valor')", segundos=25)),
                "y la lectura entra",
            )
            suya_tercera = _api(f"/api/maquinaria/{tercera['id']}", token, metodo="GET")
            la_suya = (suya_tercera.get("lecturas") or [{}])[0]
            comprobar(
                la_suya.get("unidad") == "kilometros",
                "***y se guarda en KILOMETROS, que es lo que se eligio***",
                esperaba="unidad == 'kilometros'",
                encontre=f"unidad == {la_suya.get('unidad')!r}",
            )
            texto = laFicha(nav, DIRECCION, tercera["id"], espera="cuenta-horas")
            comprobar("50000 km" in texto, "y la ficha lo ensena con su unidad", encontre=texto[-220:])

            print("\n10. SI EL ENVIO FALLA, NO SE PIERDE LO ESCRITO, Y SE PUEDE REINTENTAR")
            # ***Es lo que le pasa al agricultor en el campo***: se va la cobertura a mitad de guardar.
            # Lo que hay que poder decir es que **no se pierde lo escrito** y que **se puede reintentar**,
            # que es lo que pide el encargo («conservar el borrador si falla el envio»).
            cuarta = _api(
                "/api/maquinaria",
                token,
                {
                    "nombre": f"El del corte {marca}",
                    "clase": "tractor",
                    "propiedad": "propia",
                    "disponibilidad": "disponible",
                },
                metodo="POST",
            )
            laFicha(nav, DIRECCION, cuarta["id"], espera="cuenta-horas")
            pulsar(nav, "#pantalla [data-accion=maquina-lectura-nueva]")
            nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)
            escribe(nav, "lectura-fecha", "2026-06-01")
            escribe(nav, "lectura-valor", "777")
            nav.orden("Network.enable")
            nav.orden("Network.setBlockedURLs", {"urls": ["*/lecturas*"]})
            pulsar(nav, "#pantalla [data-accion=maquina-guardar]")
            nav.esperar("true", segundos=4.0)
            comprobar(
                bool(nav.evaluar("Boolean(document.getElementById('lectura-valor'))")),
                "***el formulario SIGUE ABIERTO: no se cierra y no se pierde lo escrito***",
            )
            comprobar(
                nav.evaluar("(document.getElementById('lectura-valor') || {}).value") == "777",
                "***y el valor sigue escrito***",
                esperaba="777",
                encontre=repr(nav.evaluar("(document.getElementById('lectura-valor') || {}).value")),
            )
            comprobar(
                nav.evaluar("(document.getElementById('lectura-fecha') || {}).value") == "2026-06-01",
                "y la fecha tambien",
                esperaba="2026-06-01",
                encontre=repr(nav.evaluar("(document.getElementById('lectura-fecha') || {}).value")),
            )
            # **Se devuelve la red y se reintenta con lo que ya estaba escrito.**
            nav.orden("Network.setBlockedURLs", {"urls": []})
            pulsar(nav, "#pantalla [data-accion=maquina-guardar]")
            comprobar(
                bool(nav.esperar("!document.getElementById('lectura-valor')", segundos=30)),
                "***y al reintentar, ENTRA***",
            )
            texto = laFicha(nav, DIRECCION, cuarta["id"], espera="Marca ahora")
            comprobar(
                "Marca ahora: 777 h" in texto,
                "con el valor que se habia escrito, sin volver a teclearlo",
                esperaba="«Marca ahora: 777 h»",
                encontre=texto[texto.find("El cuenta-horas") :][:220],
            )
            # ***Y EL DOBLE TOQUE, que es el otro caso de verdad.***
            #
            # *Ojo: el reintento de arriba **no** prueba que no se duplique, y hay que decirlo: con la red
            # bloqueada **la peticion no llega al servidor**, asi que despues hay una fila aunque la clave
            # se hubiera regenerado. **Lo que de verdad pone a prueba el reenvio es tocar dos veces** -el
            # agricultor con los guantes-, que son **dos peticiones de verdad** con la misma clave.*
            #
            # *Y se mira **en el servidor**, no en la pantalla: la ficha podria estar enseñando una sola
            # lectura y haber dos en la base.*
            pulsar(nav, "#pantalla [data-accion=maquina-lectura-nueva]")
            nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)
            escribe(nav, "lectura-fecha", "2026-07-01")
            escribe(nav, "lectura-valor", "888")
            # **Dos toques seguidos**, sin esperar a que conteste el primero: es lo que pasa de verdad.
            pulsar(nav, "#pantalla [data-accion=maquina-guardar]")
            pulsar(nav, "#pantalla [data-accion=maquina-guardar]")
            comprobar(
                bool(nav.esperar("!document.getElementById('lectura-valor')", segundos=30)),
                "***y el doble toque se guarda***",
            )
            suya = _api(f"/api/maquinaria/{cuarta['id']}", token, metodo="GET")
            las_del_888 = [una for una in suya.get("lecturas", []) if float(una["valor"]) == 888.0]
            comprobar(
                len(las_del_888) == 1,
                "***y DOS TOQUES apuntan UNA lectura: la clave de reenvio es la misma***",
                esperaba="1 lectura de 888 h en el servidor",
                encontre=f"{len(las_del_888)} lecturas de 888 h, de {len(suya.get('lecturas', []))}",
            )

            print("\n11. UNA SUSTITUCION DEL CONTADOR NO HACE QUE EL ACUMULADO BAJE")
            # ***Es el caso que el encargo prohibe que pase solo***: le ponen un contador nuevo y el
            # contador marca menos. Con la lectura marcada como sustitucion, lo de antes **se suma** en
            # vez de restarse, y la cifra tiene que salir **positiva**.
            quinta = _api(
                "/api/maquinaria",
                token,
                {
                    "nombre": f"El del contador nuevo {marca}",
                    "clase": "tractor",
                    "propiedad": "propia",
                    "disponibilidad": "disponible",
                },
                metodo="POST",
            )
            laFicha(nav, DIRECCION, quinta["id"], espera="cuenta-horas")
            for dia, valor, es_el_cambio in (
                ("2026-01-01", "1000", False),
                ("2026-02-01", "50", True),
                ("2026-03-01", "200", False),
            ):
                pulsar(nav, "#pantalla [data-accion=maquina-lectura-nueva]")
                nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)
                escribe(nav, "lectura-fecha", dia)
                escribe(nav, "lectura-valor", valor)
                if es_el_cambio:
                    # ***Se elige pulsando, como lo haria el agricultor.***
                    comprobar(
                        bool(
                            nav.evaluar(
                                "(() => { const bs = Array.from(document.querySelectorAll('#pantalla [data-accion]'));"
                                " const b = bs.find((x) => (x.textContent || '').indexOf('empieza el contador nuevo') >= 0);"
                                " if (b) b.click(); return Boolean(b); })()"
                            )
                        ),
                        "la opción de la sustitución se puede pulsar",
                    )
                pulsar(nav, "#pantalla [data-accion=maquina-guardar]")
                comprobar(
                    bool(nav.esperar("!document.getElementById('lectura-valor')", segundos=25)),
                    f"la lectura del {dia} entra",
                )
            # ***Se espera LA CIFRA QUE SE VA A COMPROBAR*** (17/10/2026). Antes esperaba
            # `"Ha subido desde la primera lectura"` -la frase del **total**- y aqui el producto dice, con
            # razon, la del **subtotal**: con la sustitucion, el tramo de las 1.000 se queda sin pareja,
            # asi que 150 es **lo que se puede afirmar**, no el total. La comprobacion esperaba una frase
            # que el programa **no debe** decir, agotaba los 25 segundos y leia una pantalla a medias.
            # ***Esto no es un fallo del producto: es el producto siendo mas honesto que la prueba.***
            texto = laFicha(nav, DIRECCION, quinta["id"], espera="150")
            comprobar(
                "150" in texto,
                "***y el acumulado es 150, POSITIVO: la sustitucion no lo ha bajado***",
                esperaba="«…: 150 h»",
                encontre=texto[texto.find("El cuenta-horas") :][:280],
            )
            comprobar(
                "de lo que se puede afirmar" in texto,
                "***y se dice que es un SUBTOTAL: el tramo de antes se quedo sin pareja***",
                esperaba="«Ha subido, de lo que se puede afirmar: 150 h»",
                encontre=texto[texto.find("El cuenta-horas") :][:280],
            )
            comprobar(
                "subida" not in texto,
                "(y la pantalla no se rompe)",
            )
            # ***Un guion suelto no vale como comprobacion***: sale en cualquier parte. Lo que no puede
            # aparecer es una **cifra negativa** en la frase del acumulado.
            comprobar(
                ": -" not in texto[texto.find("El cuenta-horas") :][:200],
                "***y no aparece ninguna cifra negativa***",
                encontre=texto[texto.find("El cuenta-horas") :][:200],
            )

            print("\n12. UNIDADES INCOMPATIBLES: SE DICE, NO SE SUMA")
            # Horas y kilometros no se suman. Lo que hay que poder afirmar es que el programa **no
            # inventa** una cifra: dice que no son la misma unidad y no ensena un cero.
            sexta = _api(
                "/api/maquinaria",
                token,
                {
                    "nombre": f"El de las unidades {marca}",
                    "clase": "tractor",
                    "propiedad": "propia",
                    "disponibilidad": "disponible",
                },
                metodo="POST",
            )
            laFicha(nav, DIRECCION, sexta["id"], espera="cuenta-horas")
            for dia, valor, unidad in (("2026-01-01", "1000", None), ("2026-02-01", "20000", "Kilómetros")):
                pulsar(nav, "#pantalla [data-accion=maquina-lectura-nueva]")
                nav.esperar("Boolean(document.getElementById('lectura-valor'))", segundos=20)
                escribe(nav, "lectura-fecha", dia)
                escribe(nav, "lectura-valor", valor)
                if unidad:
                    nav.evaluar(
                        "(() => { const bs = Array.from(document.querySelectorAll('#pantalla [data-accion]'));"
                        " const b = bs.find((x) => (x.textContent || '').trim() === '" + unidad + "');"
                        " if (b) b.click(); return Boolean(b); })()"
                    )
                pulsar(nav, "#pantalla [data-accion=maquina-guardar]")
                nav.esperar("!document.getElementById('lectura-valor')", segundos=25)
            texto = laFicha(nav, DIRECCION, sexta["id"], espera="misma unidad")
            comprobar(
                "no son todas de la misma unidad" in texto,
                "***y dice que las unidades no son las mismas***",
                esperaba="«Las lecturas no son todas de la misma unidad…»",
                encontre=texto[texto.find("El cuenta-horas") :][:280],
            )
            comprobar(
                "Ha subido" not in texto,
                "***y NO ensena ninguna cifra: no se suman horas con kilometros***",
                encontre=texto[texto.find("El cuenta-horas") :][:280],
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
