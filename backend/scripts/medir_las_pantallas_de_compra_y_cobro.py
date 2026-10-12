"""Medir las pantallas de COMPRA y de COBRO **con datos dentro** (11/10/2026).

POR QUÉ EXISTE. Medí el CRM entero y `#/facturas` y `#/ventas/cobros` salieron **vacías**: el escenario de
`datos_representativos` trae ventas y banco, pero **no facturas de compra ni cobros**. Y **una pantalla vacía
no tiene forma que juzgar** — es una de las trampas que ya me ha costado una ronda esta sesión, junto con la de
medir pantallas de error.

Estas son justo **las dos pantallas cuyas capturas miró el dueño del producto** para decir que la aplicación
«parece una UI para niños pequeños», así que son las que hay que medir **con su escenario bueno**.

Y el escenario **no se inventa aquí**: se piden prestados los constructores que ya usan los dos guiones de
captura (`_la_compra_de_la_prueba` y `_el_caso_del_encargo`), que son los que hicieron esas capturas. Si un
día cambia el escenario, cambia en un sitio.

Uso:  python scripts/medir_las_pantallas_de_compra_y_cobro.py <direccion>
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from comprobar_la_ficha_de_la_compra_en_el_navegador import _la_compra_de_la_prueba  # noqa: E402
from capturar_la_pantalla_del_reparto import _el_caso_del_encargo  # noqa: E402
from datos_representativos import preparar  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8029"

LO_QUE_SE_MIDE = """(() => {
  const p = document.querySelector('.pantalla');
  const tabla = document.querySelector('#pantalla table.tabla');
  const filas = tabla ? tabla.querySelectorAll('tbody tr').length : 0;
  const primera = tabla ? tabla.querySelector('tbody tr') : null;
  const h = document.querySelector('#pantalla h1, #pantalla h2');
  const lista = document.querySelectorAll('#pantalla .lista li, #pantalla .tarjeta').length;
  const celdas = primera ? [...primera.querySelectorAll('td')].map(
    (c) => Math.round(c.getBoundingClientRect().width)) : [];
  const botones = [...document.querySelectorAll('#pantalla .boton')];
  return {
    titulo: h ? (h.textContent || '').trim().slice(0, 42) : null,
    ancho: p ? Math.round(p.getBoundingClientRect().width) : null,
    tabla: Boolean(tabla),
    filas,
    alto_fila: primera ? Math.round(primera.getBoundingClientRect().height) : null,
    columnas: tabla ? tabla.querySelectorAll('thead th').length : 0,
    ancho_de_las_celdas: celdas,
    lista_o_tarjetas: lista,
    botones: botones.length,
    alto_boton: botones.length ? Math.round(botones[0].getBoundingClientRect().height) : null,
  };
})()"""


def main() -> int:
    print(f"  (direccion: {DIRECCION})")
    escenario = preparar(DIRECCION)
    token = escenario.volumen.token
    # **`campana_actual()` es un método y `campanas` una lista** (11/10/2026). La primera versión pedía
    # `volumen.campana`, que no existe, así que se quedaba en `None` y **el escenario del cobro nunca se
    # montó**: el medidor dijo «no hay datos» sin decir que el que no había montado nada era él. Es la misma
    # familia de fallo que el resto de la sesión: el instrumento, antes que el producto.
    campana = escenario.volumen.campana_actual.id
    print(f"  (campaña para el cobro: {campana})")
    if campana is None:
        print("  (sin campaña: no se puede montar el cobro)")

    # **Los escenarios, prestados de los guiones que ya los montan.**
    try:
        compra_id = _la_compra_de_la_prueba(token)
        print(f"  (compra de la prueba: {compra_id})")
    except Exception as error:  # noqa: BLE001 - se dice y se sigue, que esto es un medidor
        compra_id = None
        print(f"  (no he podido montar la compra: {type(error).__name__}: {str(error)[:70]})")
    cobro_ok = False
    if campana is not None:
        try:
            _el_caso_del_encargo(token, campana)
            cobro_ok = True
        except Exception as error:  # noqa: BLE001
            print(f"  (no he podido montar el cobro: {type(error).__name__}: {str(error)[:70]})")

    rutas = ["#/facturas"]
    if compra_id:
        rutas.append(f"#/compras/{compra_id}")
    if cobro_ok:
        rutas.append("#/ventas/cobros")

    with NavegadorDeVerdad(ancho=1440, alto=1000) as nav:
        nav.medir(1440, 1000, movil=False)
        nav.orden(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "window.localStorage.setItem('cuedigital.token', " + json.dumps(token) + ");"},
        )
        for ruta in rutas:
            nav.abrir(f"{DIRECCION}/{ruta}", esperar=2.2)
            nav.esperar("document.querySelectorAll('#pantalla *').length > 0", segundos=25)
            print(f"  {ruta:24} {json.dumps(nav.evaluar(LO_QUE_SE_MIDE), ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
