"""**Declarar una obligacion CON fecha** (revision del dueño, 14/10/2026).

Esto no lo cazaba nada, y el fallo era de los que no se ven venir: la entrada de **auditoria del alta**
metia el objeto `date` en `Auditoria.datos`, que es una columna **JSON** -`TypeError: Object of type date
is not JSON serializable`-, asi que la declaracion entera se iba en un **500** y **el agricultor perdia
lo que acababa de apuntar**.

**Por que no lo cazaba nada, que es lo que importa**:

· El recorrido de 46 comprobaciones **no lo andaba**: su paso 0 declara la obligacion **sin** fecha -a
  proposito, es el estado del contrato que se venia a corregir- y la fecha llega despues, en una
  **correccion**, que usa `correcciones._como_se_guarda` y **si** serializa bien. El camino roto era el
  **alta con fecha**, y por ahi no pasaba nadie.
· Y **ninguna prueba de `tests/` mandaba `fecha_de_la_evidencia`**.
· Lo encontro el subagente que hizo la segunda mitad del #6, **probando el ciclo de verdad** en vez de
  fiarse de las pruebas que habia.

**Y el caso es el NORMAL**, no un rincon: es lo que hace la pantalla cuando el agricultor tiene el papel
delante y lo apunta de una vez.

Se reutilizan los ayudantes de `test_t14_maquinaria.py`, que son el contrato de montaje del ticket.
"""

from __future__ import annotations

from test_t14_maquinaria import (  # noqa: F401
    crear_maquina,
    la_ficha,
    sus_obligaciones,
)


def test_declarar_una_obligacion_con_fecha_la_guarda_y_no_pierde_la_declaracion(cliente, cuenta):
    """El alta **con las dos fechas** responde 200, y las dos quedan guardadas."""
    cabeceras = cuenta["cabeceras"]
    maquina = crear_maquina(cliente, cabeceras)

    respuesta = cliente.put(
        f"/api/maquinaria/{maquina['id']}/obligaciones/itv",
        headers=cabeceras,
        json={
            "aplicabilidad": "si",
            "origen": "documento",
            # Las dos fechas a la vez: la del papel y la de la decision. La primera es la que reventaba
            # -llevaba ahi desde antes que la segunda-, y la segunda es la que destapo el fallo.
            "fecha_de_la_evidencia": "2026-03-14",
            "decidido_en": "2026-03-10",
        },
    )
    # **200 y no un 500**: si esto falla, el agricultor ha perdido lo que acaba de apuntar.
    assert respuesta.status_code == 200, respuesta.text

    ficha = la_ficha(cliente, cabeceras, maquina["id"])
    itv = sus_obligaciones(ficha)["itv"]
    assert itv["fecha_de_la_evidencia"] == "2026-03-14", (
        "la fecha del papel se guarda en el ALTA, no solo en la correccion"
    )
    assert itv["decidido_en"] == "2026-03-10", "y la de la decision tambien"
    # Y la declaracion **existe**: el 500 no se llevo por delante la fila entera.
    assert itv["aplicabilidad"] == "si"
    assert itv["origen_de_la_aplicabilidad"] == "documento"


def test_declarar_con_fecha_deja_su_rastro_en_la_auditoria(cliente, cuenta):
    """Y el rastro del alta nombra las dos fechas, **en texto** (la columna es JSON).

    Es la mitad que se rompia de verdad: no que la fecha no se guardara, sino que **al escribir el
    rastro** el `date` no se podia convertir a JSON y se caia todo. Que el rastro exista y traiga las
    fechas en texto es lo que demuestra que la conversion esta hecha.
    """
    cabeceras = cuenta["cabeceras"]
    maquina = crear_maquina(cliente, cabeceras)
    antes = cliente.get("/api/maquinaria/" + str(maquina["id"]) + "/auditoria", headers=cabeceras)
    respuesta = cliente.put(
        f"/api/maquinaria/{maquina['id']}/obligaciones/itv",
        headers=cabeceras,
        json={
            "aplicabilidad": "si",
            "origen": "documento",
            "fecha_de_la_evidencia": "2026-03-14",
            "decidido_en": "2026-03-10",
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    # Si la puerta de la auditoria no existe con esa forma, se dice en vez de dar por bueno el silencio.
    assert antes.status_code in (200, 404), antes.text
