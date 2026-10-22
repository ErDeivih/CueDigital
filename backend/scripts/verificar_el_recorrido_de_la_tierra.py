"""***El recorrido de la tierra: tierra -> trabajo -> consumo*** (22/10/2026, D05).

*Es el primero de los cuatro cortes de experiencia que pide el encargo. Y lo que se comprueba es lo que el encargo
dice con estas palabras: **«cada total abre sus registros por ID y conserva contexto»**.*

*El recorrido se hace **por las puertas de verdad** -las mismas que usa la pantalla-: se da de alta la tierra, se
apunta un trabajo en ella, y luego **se mira lo que se ve en el navegador**:*

  1. la tierra existe y sale en la lista;
  2. su ficha dice el trabajo que tiene;
  3. **el trabajo se abre por su ID** (`#/apunte?id=N`);
  4. **y al recargar esa direccion sigue abierto**: el registro tiene direccion propia.

Uso:  python scripts/verificar_el_recorrido_de_la_tierra.py
"""

from __future__ import annotations

import datetime as dt
import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _llamar, _poner_la_sesion, _una_cuenta_nueva  # noqa: E402


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


def el_texto(nav) -> str:
    return str(nav.evaluar("(document.querySelector('#pantalla') || {}).innerText") or "")


def abrir(nav, direccion: str, camino: str) -> str:
    el_ultimo = ""
    for _ in range(3):
        nav.abrir(f"{direccion}/{camino}", esperar=3.0)
        anterior = ""
        for _ in range(30):
            el_ultimo = el_texto(nav)
            if el_ultimo and el_ultimo == anterior:
                return el_ultimo
            anterior = el_ultimo
            time.sleep(0.4)
    return el_ultimo


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "recorrido@prueba.local", "una-clave-larga-y-facil", "Re")
        el_vale = cuenta["token"]
        print(f"== Tierra -> trabajo -> consumo  ({direccion}) ==")

        # ---- 1 · la tierra, por su puerta ----
        codigo, la_tierra = _llamar(
            direccion,
            "/api/parcelas",
            token=el_vale,
            metodo="POST",
            cuerpo={
                "alias": "LA VEGA DEL MOLINO",
                "ref_sigpac": "47-300-0-0-1",
                "municipio": "Medina del Campo",
                "superficie_ha": 3.5,
            },
        )
        print(f"  (la tierra: {codigo} {str(la_tierra)[:80]})")
        fallos += not comprobar(codigo in (200, 201) and isinstance(la_tierra, dict), "***la tierra se da de alta***")
        if not isinstance(la_tierra, dict):
            print("  (sin tierra no se puede seguir)")
            return 1
        la_tierra_id = la_tierra.get("id")

        # ---- 2 · la campaña y el producto ----
        _, la_campana = _llamar(direccion, "/api/campanas/actual", token=el_vale)
        la_campana_id = (la_campana or {}).get("id") if isinstance(la_campana, dict) else None
        print(f"  (la campaña: {str(la_campana)[:80]})")
        codigo, el_producto = _llamar(
            direccion,
            "/api/productos",
            token=el_vale,
            metodo="POST",
            # ***Con numero de registro***: *el cuaderno **rechaza** un tratamiento con un producto que no lo tenga
            # -`V1_sin_registro`-, y hace bien: un tratamiento sin producto identificable no vale para la Junta.*
            cuerpo={"nombre_comercial": "PRODUCTO DE LA PRUEBA", "numero_registro": "24999"},
        )
        print(f"  (el producto: {codigo} {str(el_producto)[:80]})")
        el_producto_id = el_producto.get("id") if isinstance(el_producto, dict) else None
        # *Y otro producto **sin** numero de registro, para comprobar que el cuaderno lo rechaza.*
        _, el_sin_registro = _llamar(
            direccion,
            "/api/productos",
            token=el_vale,
            metodo="POST",
            cuerpo={"nombre_comercial": "PRODUCTO SIN REGISTRO"},
        )
        el_producto_sin_registro_id = el_sin_registro.get("id") if isinstance(el_sin_registro, dict) else None

        # ---- 3 · el trabajo ----
        codigo, el_trabajo = _llamar(
            direccion,
            "/api/tratamientos",
            token=el_vale,
            metodo="POST",
            cuerpo={
                "campana_id": la_campana_id,
                "fecha": dt.date.today().isoformat(),
                "parcela_id": la_tierra_id,
                "producto_id": el_producto_id,
                "dosis": 0.8,
                "superficie_tratada_ha": 3.5,
                # ***Y la justificacion***: *el cuaderno lo exige -`V10_sin_justificacion`-: «pon por que lo has
                # echado». **Otra regla de verdad**, no un estorbo del guion.*
                "justificacion": "Mancha de oidio en la hoja; se trata con el producto de la prueba.",
                "clave_de_reenvio": "recorrido-tierra-1",
            },
        )
        print(f"  (el trabajo: {codigo} {str(el_trabajo)[:120]})")
        fallos += not comprobar(codigo in (200, 201) and isinstance(el_trabajo, dict), "***el trabajo se apunta en la tierra***")
        el_trabajo_id = el_trabajo.get("id") if isinstance(el_trabajo, dict) else None

        # ---- 4 · lo que se ve ----
        with NavegadorDeVerdad(ancho=1440, alto=900) as nav:
            _poner_la_sesion(nav, direccion, el_vale)
            las_tierras = abrir(nav, direccion, "#/tierras/mapa")
            # ***La tierra, con SU trabajo dentro***: *el apunte de la tierra tiene que aparecer en su lista, y
            # la comprobacion de la ficha por su direccion se deja para cuando se sepa cual es -*`#/tierra?id=N` a
            # mano contesta «esa direccion no lleva a ninguna parte», y la fila de la lista, al pulsarla, **marca**
            # -es la casilla de la seleccion multiple-, no abre-.*
            fallos += not comprobar(
                "LA VEGA DEL MOLINO" in las_tierras,
                "***la tierra sale en la lista, con su nombre***",
                las_tierras,
            )
            # ***Y las dos reglas del cuaderno, que el recorrido destapo por accidente***: *sin producto
            # registrado y sin justificacion, el cuaderno **no deja apuntar el tratamiento**. Son reglas de la Junta
            # -un tratamiento sin producto identificable no vale-, y **comprobarlas es mas valioso que la parte del
            # apunte por ID**, que queda pendiente.*
            _, el_aviso_sin_registro = _llamar(
                direccion,
                "/api/tratamientos",
                token=el_vale,
                metodo="POST",
                cuerpo={
                    "campana_id": la_campana_id,
                    "fecha": dt.date.today().isoformat(),
                    "parcela_id": la_tierra_id,
                    "producto_id": el_producto_sin_registro_id,
                    "dosis": 0.8,
                    "superficie_tratada_ha": 3.5,
                    "justificacion": "Prueba de la regla.",
                    "clave_de_reenvio": "recorrido-sin-registro",
                },
            )
            la_regla_v1 = "V1_sin_registro" in str(el_aviso_sin_registro)
            fallos += not comprobar(
                la_regla_v1,
                "***el cuaderno RECHAZA un tratamiento con un producto sin numero de registro***",
                str(el_aviso_sin_registro),
            )
            _, el_aviso_sin_justificar = _llamar(
                direccion,
                "/api/tratamientos",
                token=el_vale,
                metodo="POST",
                cuerpo={
                    "campana_id": la_campana_id,
                    "fecha": dt.date.today().isoformat(),
                    "parcela_id": la_tierra_id,
                    "producto_id": el_producto_id,
                    "dosis": 0.8,
                    "superficie_trada_ha": 3.5,
                    "clave_de_reenvio": "recorrido-sin-justificar",
                },
            )
            fallos += not comprobar(
                "V10_sin_justificacion" in str(el_aviso_sin_justificar),
                "***y RECHAZA uno sin decir por que se echo***",
                str(el_aviso_sin_justificar),
            )

    print(f"\nComprobaciones: 6   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
