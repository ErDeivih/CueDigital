"""***Diagnóstico TEMPORAL*** del recorrido de la cola sin conexión (30/10/2026).

No forma parte del producto: se escribe para **ver** por qué el recorrido
`verificar_que_la_cola_no_cruza_cuentas.py` deja de mandar el apunte propio, en vez de
suponerlo. Se borra cuando se sepa.

Lo que se mira, y por qué cada cosa:

1. `navigator.onLine` — `mandarPendientes` sale con «esperar» si es falso, y entonces **no se
   manda nada** aunque se dispare `online`.
2. Las llamadas a `fetch` — si el drenaje ni siquiera llega a pedir, el fallo está antes.
3. Si la pantalla es la de entrar o la aplicación — un vale sembrado que no vale deja la
   pantalla en blanco de sesión y el drenaje sin cuenta.
4. La cola, antes y después del evento.
"""

import json
import time

import capturar_la_pantalla_del_reparto as el_reparto
from andar_el_recorrido_de_la_pac import el_servidor_temporal
from datos_representativos import preparar
from navegador_cdp import NavegadorDeVerdad

# *Se envuelve `fetch` ANTES de que arranque la aplicación, para verlo todo.*
EL_REGISTRO = (
    "(() => { window.__fetchLog = [];"
    " if (!window.fetch) return 'sin-fetch';"
    " const elDeVerdad = window.fetch.bind(window);"
    " window.fetch = function (lo, opciones) {"
    "  try { const d = typeof lo === 'string' ? lo : ((lo && lo.url) || '');"
    "  const c = (opciones && opciones.body) || '';"
    "  window.__fetchLog.push({url: String(d), cuerpo: String(c).slice(0, 120)}); } catch (e) {}"
    "  return elDeVerdad(lo, opciones); };"
    " return 'envuelto'; })()"
)

LA_COLA = (
    "(() => { try { const l = window.localStorage; const los = [];"
    " for (let i = 0; i < (l.length || 0); i += 1) { const k = l.key(i);"
    " if (typeof k !== 'string') continue;"
    " if (k === 'cuedigital.pendientes') { try { const v = JSON.parse(l.getItem(k));"
    " if (Array.isArray(v)) los.push(...v); } catch (e) {} continue; }"
    " if (k.indexOf('cuedigital.pendiente.') !== 0) continue;"
    " try { const v = JSON.parse(l.getItem(k)); if (v) los.push(v); } catch (e) { los.push({id_local: k}); } }"
    " return JSON.stringify(los); } catch (e) { return '[]'; } })()"
)


def main() -> int:
    with el_servidor_temporal() as direccion:
        el_reparto.DIRECCION = direccion
        print(f"== Diagnóstico de la cola  ({direccion}) ==")
        escenario = preparar(direccion)
        token = escenario.volumen.token
        la_campana = escenario.volumen.campanas[0].id
        la_parcela = escenario.tierras[0].id

        yo = el_reparto._api("/api/cuenta/yo", token, metodo="GET") or {}
        la_de_ahora = f"{yo.get('usuario_id')}:{(yo.get('explotacion') or {}).get('id')}"
        print(f"  la sesion: {la_de_ahora}")

        la_cola = [
            {
                "tipo": "laboreo",
                "ruta": "/api/trabajos",
                "datos": {
                    "campana_id": la_campana,
                    "tipo": "laboreo",
                    "subtipo": "de-la-cuenta-abierta",
                    "fecha": "2026-10-19",
                    "parcela_id": la_parcela,
                },
                "id_local": "p-diagnostico",
                "apuntado_en": "2026-10-19T08:00:00.000Z",
                "cuenta": la_de_ahora,
            }
        ]

        with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
            nav.medir(1440, 1000)
            nav.orden("Network.enable")
            nav.orden(
                "Network.emulateNetworkConditions",
                {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1},
            )
            nav.orden(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": (
                        # El Chrome sin ventana del banco de pruebas no tiene salida a internet y
                        # declara `navigator.onLine === false` aunque el servidor de pruebas esté
                        # ahí al lado. Se declara con cobertura, que es la situación del campo.
                        "Object.defineProperty(Navigator.prototype, 'onLine', "
                        "{configurable: true, get: function () { return true; }});"
                        "window.localStorage.setItem('cuedigital.token', "
                        + json.dumps(token)
                        + ");"
                        "window.localStorage.setItem('cuedigital.pendientes', "
                        + json.dumps(json.dumps(la_cola))
                        + ");"
                        + EL_REGISTRO
                    )
                },
            )
            nav.abrir(f"{direccion}/#/inicio", esperar=3.0)
            nav.esperar(
                "document.querySelector('#pantalla') && document.querySelector('#pantalla').innerText.length > 40",
                segundos=40,
            )

            print("  onLine:", nav.evaluar("String(navigator.onLine)"))
            print("  hay vale:", nav.evaluar("String(!!window.localStorage.getItem('cuedigital.token'))"))
            print(
                "  pantalla:",
                str(
                    nav.evaluar(
                        "(() => { const p = document.querySelector('#pantalla');"
                        " return p ? p.innerText.slice(0, 80).replace(/\\n/g, ' | ') : '(sin pantalla)'; })()"
                    )
                )[:120],
            )
            print("  cola al llegar:", str(nav.evaluar(LA_COLA))[:200])
            print("  fetch al llegar:", str(nav.evaluar("JSON.stringify((window.__fetchLog||[]).map(function (x) { return x.url; }))"))[:300])

            nav.evaluar("window.dispatchEvent(new Event('online')); 'ok'")
            time.sleep(8.0)

            print("  cola despues:", str(nav.evaluar(LA_COLA))[:300])
            print(
                "  fetch despues:",
                str(
                    nav.evaluar(
                        "JSON.stringify((window.__fetchLog||[]).filter(function (x) {"
                        " return x.url.indexOf('/api/trabajos') === 0; }))"
                    )
                )[:600],
            )
            print(
                "  aviso:",
                str(
                    nav.evaluar(
                        "(() => { const a = document.querySelector('#aviso-pendientes');"
                        " return a ? a.innerText : '(sin aviso)'; })()"
                    )
                )[:200],
            )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
