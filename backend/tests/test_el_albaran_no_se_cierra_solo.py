"""El repintado del libro del almacén **no puede cerrar** el formulario del albarán (08/10/2026).

**Por qué existe esta prueba.** El defecto se encontró **andando por las pantallas**, con el guion
`scripts/comprobar_el_recorrido_economico.py`: pulsar «apuntar un albarán» **abría** el formulario y, en
milisegundos, **ya no estaba**. La traza del guion lo deja escrito: un solo estado en cinco segundos, y era la
lista.

**La causa**, en `web/app.js` (`abrirElLibroDelAlmacen`): al terminar la carga de datos, esa función volvía a
pintar la lista y **descartaba** el formulario que el agricultor acababa de abrir. Con la cobertura mala del
campo —que es cuando la carga tarda— pasaba **siempre**, y el albarán es **lo único que mete existencias**, así
que el agricultor no podía hacer entrar mercancía.

**Esta prueba sujeta la guarda** que lo arregla: que el repintado de después de cargar **respete** lo que esté
abierto, y que la guarda esté **después** de la carga (que es donde tiene efecto). Si alguien la quita, se pone
en rojo — que es lo que se le pide a una prueba de un defecto: **fallar antes del arreglo**.
"""

from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP = RAIZ / "backend" / "web" / "app.js"

LA_FUNCION = "async function abrirElLibroDelAlmacen()"
LA_GUARDA = "if (suyo.albaran) return pantallaNuevoAlbaran();"
LA_CARGA = "await recargarElLibro();"


def test_el_repintado_de_despues_de_cargar_respeta_el_formulario_del_albaran():
    """El libro del almacén se pinta al cargar; si hay un albarán abierto, se pinta **el formulario**."""
    fuente = APP.read_text(encoding="utf-8")
    assert LA_FUNCION in fuente, "no encuentro `abrirElLibroDelAlmacen` en `web/app.js`"

    desde = fuente.index(LA_FUNCION)
    suyo = fuente[desde : desde + 1600]
    assert LA_GUARDA in suyo, (
        "el repintado de después de cargar el libro **no respeta** el formulario del albarán abierto: sin esa "
        "guarda, pulsar «apuntar un albarán» abre el formulario y lo cierra solo (medido en un navegador de "
        "verdad; el albarán es lo único que mete existencias)"
    )
    # Y tiene que estar **después** de la carga: antes no serviría de nada, porque el que pisa el formulario es
    # justo el repintado que viene al terminar.
    assert suyo.index(LA_CARGA) < suyo.index(LA_GUARDA), (
        "la guarda está antes de la carga: el repintado de después seguiría cerrando el formulario"
    )
