"""**La cola sin conexion no cruza cuentas** (19/10/2026).

### ***El fallo, con las palabras del informe***

*«La cola sin conexión puede enviar operaciones de una cuenta desde otra».* *Y era verdad: `mandarPendientes`
recorria `cola.leer()` **entero** y mandaba cada apunte con `api(...)`, es decir **con el vale de la sesion que
estuviera abierta**. Un trabajo apuntado sin cobertura en una finca, mandado al reconectar con otra cuenta, **se
escribia en la finca equivocada**.*

### ***Como se comprueba aqui, y por que asi***

*Se siembra la cola **directamente en `localStorage`** -que es exactamente lo que deja una sesion sin cobertura- con
**dos apuntes que solo se diferencian en la cuenta**:

    · uno de **la cuenta abierta**  -> ***tiene que mandarse***      (control positivo)
    · uno de **otra cuenta**       -> ***NO tiene que mandarse***   (el fallo)

*Si los dos se mandaran, habria **dos** trabajos; si solo el suyo, **uno**. **No hay forma de que pase por
casualidad.***

*Y ademas: el ajeno **sigue en la cola** -no se pierde- y la pantalla **lo dice**.*

Uso:  python scripts/verificar_que_la_cola_no_cruza_cuentas.py
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
import capturar_la_pantalla_del_reparto as el_reparto  # noqa: E402
from capturar_la_pantalla_del_reparto import _api  # noqa: E402
from verificar_los_permisos_por_rol import _llamar  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

# ***La cola, sea cual sea su disposición*** (23/10/2026, D01): *ahora guarda **una clave por intención**, y leer la clave
# vieja (`cuedigital.pendientes`) decía siempre «vacía». **El fallo era del instrumento, no de la app** — el mismo
# acoplamiento que se corrigió en las pruebas de JS con el ayudante `losPendientes`.*
LA_COLA_ENTERA_JS = (
    "(() => { try { const l = window.localStorage; const los = [];"
    " for (let i = 0; i < (l.length || 0); i += 1) { const k = l.key(i);"
    " if (typeof k !== 'string') continue;"
    " if (k === 'cuedigital.pendientes') { try { const v = JSON.parse(l.getItem(k));"
    " if (Array.isArray(v)) los.push(...v); } catch (e) {} continue; }"
    " if (k.indexOf('cuedigital.pendiente.') !== 0) continue;"
    " try { const v = JSON.parse(l.getItem(k)); if (v) los.push(v); } catch (e) { los.push({ id_local: k }); } }"
    " return JSON.stringify(los); } catch (e) { return '[]'; } })()"
)

COMPROBACIONES = 0
FALLOS: list[str] = []


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    global COMPROBACIONES
    COMPROBACIONES += 1
    if bien:
        print(f"  [OK   ] {que}")
    else:
        print(f"  [FALLO] {que}")
        if encontre:
            print(f"          encontre : {encontre[:300]}")
        FALLOS.append(que)
    return bien


def los_trabajos(direccion, token: str) -> list[dict]:
    """*Los trabajos de la finca, **sin filtrar**.*

    ***Y sin filtrar porque el filtro no es lo que parecia*** (19/10/2026): *`GET /api/trabajos?campana_id=5`
    contestaba **`[]`** con el trabajo creado en la campaña 5 -lo dijo el `POST`, que devolvio 201 con
    `campana_id: 5`-. **El trabajo estaba; el filtro de la direccion no lo traia.** Se comprobo mandando el mismo
    cuerpo a mano: 201, y la lista filtrada vacia. **La prueba se hace sobre lo que la puerta devuelve de verdad,
    no sobre el filtro que uno supone.***
    """
    los = _api("/api/trabajos", token, metodo="GET")
    if isinstance(los, list):
        return los
    los = los or {}
    return los.get("hechos") or los.get("trabajos") or []


def main() -> int:
    with el_servidor_temporal() as direccion:
        print(f"== La cola no cruza cuentas  ({direccion}) ==")
        escenario = preparar(direccion)
        token = escenario.volumen.token
        # ***`_api` lee la direccion de SU modulo***: *si no se le dice, se va al 8029 de por defecto -que no esta
        # levantado- y el guion muere con «conexion rechazada» antes de empezar.*
        el_reparto.DIRECCION = direccion
        la_campana = escenario.volumen.campanas[0].id
        la_parcela = escenario.tierras[0].id

        yo = _api("/api/cuenta/yo", token, metodo="GET") or {}
        la_de_ahora = f"{yo.get('usuario_id')}:{(yo.get('explotacion') or {}).get('id')}"
        print(f"  la sesion: {la_de_ahora}")
        assert la_de_ahora != "None:None", f"no se pudo leer la cuenta: {yo}"

        la_de_otra = "999999:999999"
        los_antes = los_trabajos(direccion, token)

        # ***Dos apuntes, iguales menos en la cuenta.***
        def un_apunte(subtipo: str, cuenta: str | None) -> dict:
            apunte = {
                "tipo": "laboreo",
                "ruta": "/api/trabajos",
                "datos": {
                    "campana_id": la_campana,
                    "tipo": "laboreo",
                    "subtipo": subtipo,
                    "fecha": "2026-10-19",
                    "parcela_id": la_parcela,
                },
                "id_local": f"p-{subtipo}",
                "apuntado_en": "2026-10-19T08:00:00.000Z",
            }
            if cuenta is not None:
                apunte["cuenta"] = cuenta
            return apunte

        la_cola = [un_apunte("de-la-cuenta-abierta", la_de_ahora), un_apunte("de-otra-cuenta", la_de_otra)]

        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            # ***La sesion Y la cola, puestas ANTES de la primera pagina***: *es lo que deja una sesion sin
            # cobertura, y aqui se siembra a mano para que la prueba no dependa de apagar la red.*
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": (
                        "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"
                        "window.localStorage.setItem('cuedigital.pendientes', " + json.dumps(json.dumps(la_cola)) + ");"
                    )
                },
            )
            nav.abrir(f"{direccion}/#/inicio", esperar=3.0)
            nav.esperar("document.querySelector('#pantalla') && document.querySelector('#pantalla').innerText.length > 40", segundos=40)

            print("\n1. LA COLA SE VACIA CON LA SESION ABIERTA")
            nav.evaluar("window.dispatchEvent(new Event('online')); 'ok'")
            # *Se espera a que el suyo llegue: es el control positivo.*
            for _intento in range(60):
                los_de_ahora = los_trabajos(direccion, token)
                if len(los_de_ahora) > len(los_antes):
                    break
                import time as _time

                _time.sleep(1.0)
            los_de_ahora = los_trabajos(direccion, token)
            # ***Y los subtipos, para poder mirarlos***: *la limpieza de los diagnosticos se llevo esta linea y el
            # recorrido dejo de arrancar -`NameError` en la comprobacion-. Se vio al volver a ejecutarlo, que es
            # justo lo que hay que hacer despues de limpiar.*
            los_subtipos = [str(uno.get("subtipo") or "") for uno in los_de_ahora]
            comprobar(
                "de-la-cuenta-abierta" in los_subtipos,
                "***el apunte de la cuenta abierta SI se manda*** (control positivo)",
                encontre=str(los_subtipos[:6]),
            )
            comprobar(
                "de-otra-cuenta" not in los_subtipos,
                "***y el de OTRA cuenta NO se manda***",
                encontre=str(los_subtipos[:6]),
            )

            print("\n2. Y LO AJENO NO SE PIERDE, Y SE DICE")
            la_que_queda = nav.evaluar(
                LA_COLA_ENTERA_JS
            ) or "[]"
            comprobar(
                "de-otra-cuenta" in str(la_que_queda),
                "***el apunte ajeno SIGUE en la cola: no se ha perdido***",
                encontre=str(la_que_queda)[:300],
            )
            el_aviso = nav.evaluar(
                "(() => { const a = document.querySelector('#aviso-pendientes');"
                " return a ? a.innerText : '(sin aviso)'; })()"
            ) or ""
            comprobar(
                "otra cuenta" in str(el_aviso).lower(),
                "***y la pantalla lo dice, en vez de dejar un numero que no baja***",
                encontre=str(el_aviso)[:200],
            )

        # ==================================================================================== 3 · rechazados
        print("\n3. LO QUE EL SERVIDOR RECHAZA SE APARTA, NO SE PIERDE")
        # *Un apunte con una campaña que no existe: **el servidor contesta 4xx**, y la cola tiene que **apartarlo con
        # su motivo** en vez de reintentarlo para siempre o tirarlo en silencio.*
        la_cola_mala = [un_apunte("que-el-servidor-rechaza", la_de_ahora)]
        la_cola_mala[0]["datos"]["campana_id"] = 999999
        la_cola_mala[0]["id_local"] = "p-de-rechazo"

        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": (
                        "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"
                        "window.localStorage.setItem('cuedigital.pendientes', "
                        + json.dumps(json.dumps(la_cola_mala))
                        + ");"
                        # ***La clave lleva dueno desde el 21/10***: *`cuedigital.rechazados.2:2`. Se borran todos
                        # los cubos, para que el recorrido empiece limpio.*
                        "Object.keys(window.localStorage)"
                        ".filter(function (k) { return k.indexOf('cuedigital.rechazados') === 0; })"
                        ".forEach(function (k) { window.localStorage.removeItem(k); });"
                    )
                },
            )
            nav.abrir(f"{direccion}/#/inicio", esperar=3.0)
            nav.esperar(
                "document.querySelector('#pantalla') && document.querySelector('#pantalla').innerText.length > 40",
                segundos=40,
            )
            nav.evaluar("window.dispatchEvent(new Event('online')); 'ok'")

            los_rechazados = "(todavia nada)"
            for _intento in range(45):
                los_rechazados = (
                    nav.evaluar(
                        # ***Se leen TODOS los cubos de rechazados***: *la clave lleva dueno -`...rechazados.2:2`-,
                        # y buscar solo la global daba «no se aparto» cuando sí se habia apartado.*
                        "(() => { try { return Object.keys(window.localStorage)"
                        ".filter(function (k) { return k.indexOf('cuedigital.rechazados') === 0; })"
                        ".map(function (k) { return window.localStorage.getItem(k) || ''; }).join(''); }"
                        " catch (e) { return ''; } })()"
                    )
                    or ""
                )
                if "que-el-servidor-rechaza" in str(los_rechazados):
                    break
                import time as _time

                _time.sleep(1.0)

            comprobar(
                "que-el-servidor-rechaza" in str(los_rechazados),
                "***el apunte rechazado se APARTA, con lo que se mando***",
                encontre=str(los_rechazados)[:400],
            )
            la_que_queda = (
                nav.evaluar(
                    LA_COLA_ENTERA_JS
                )
                or "[]"
            )
            comprobar(
                "que-el-servidor-rechaza" not in str(la_que_queda),
                "***y sale de la cola: no se reintenta para siempre***",
                encontre=str(la_que_queda)[:300],
            )
            el_aviso_malo = (
                nav.evaluar(
                    "(() => { const a = document.querySelector('#aviso-pendientes');"
                    " return a ? a.innerText : '(sin aviso)'; })()"
                )
                or ""
            )
            comprobar(
                len(str(el_aviso_malo).strip()) > 0 and "sin aviso" not in str(el_aviso_malo),
                "***y se dice en la pantalla, con su motivo***",
                encontre=str(el_aviso_malo)[:250],
            )

        # ============================================================================ 4 · el aviso dice la verdad entera
        print("\n4. CON PROPIOS Y AJENOS A LA VEZ, EL AVISO DICE LAS DOS COSAS")
        # ***El caso que el aviso ocultaba***: *con dos apuntes del agricultor y uno de otra cuenta, decia «1 de
        # otra cuenta» y **se callaba los dos suyos** -contaba lo que no puede mandar y ocultaba lo que si-.*
        #
        # *Se fuerza **sin red** -el evento `offline`, que la aplicacion escucha y repinta- para que los propios no
        # se manden y se queden en la cola, que es cuando el aviso mixto aparece.*
        la_cola_mixta = [
            un_apunte("propio-uno", la_de_ahora),
            un_apunte("propio-dos", la_de_ahora),
            un_apunte("ajeno", la_de_otra),
        ]

        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": (
                        "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"
                        "window.localStorage.setItem('cuedigital.pendientes', "
                        + json.dumps(json.dumps(la_cola_mixta))
                        + ");"
                    )
                },
            )
            nav.abrir(f"{direccion}/#/inicio", esperar=3.0)
            nav.esperar(
                "document.querySelector('#pantalla') && document.querySelector('#pantalla').innerText.length > 40",
                segundos=40,
            )
            # *Y se vuelve a sembrar la cola **despues** de que el vaciado del arranque haya pasado, y se dispara
            # el evento: la pantalla repinta con los tres apuntes en la cola.*
            nav.evaluar(
                "(() => { window.localStorage.setItem('cuedigital.pendientes', "
                + json.dumps(json.dumps(la_cola_mixta))
                + "); window.dispatchEvent(new Event('offline')); return 'puesto'; })()"
            )
            el_aviso_mixto = ""
            for _intento in range(20):
                el_aviso_mixto = (
                    nav.evaluar(
                        "(() => { const a = document.querySelector('#aviso-pendientes');"
                        " return a ? a.innerText : ''; })()"
                    )
                    or ""
                )
                if "otra cuenta" in str(el_aviso_mixto).lower():
                    break
                import time as _time

                _time.sleep(0.5)

            comprobar(
                "otra cuenta" in str(el_aviso_mixto).lower(),
                "***dice que hay apuntes de otra cuenta***",
                encontre=str(el_aviso_mixto)[:250],
            )
            comprobar(
                "2" in str(el_aviso_mixto),
                "***y NO se calla los dos del agricultor***",
                encontre=str(el_aviso_mixto)[:250],
            )

        print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {len(FALLOS)}")
        for uno in FALLOS:
            print(f"  - {uno}")
        return 0 if not FALLOS else 1


if __name__ == "__main__":
    raise SystemExit(main())
