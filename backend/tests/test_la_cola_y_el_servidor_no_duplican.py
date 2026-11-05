"""**La cola y el servidor no apuntan dos veces lo mismo** (19/10/2026, D02).

### ***Lo que el encargo pide con estas palabras***

*«…**idempotencia tras respuesta perdida**»*, y *«concurrencia entre pestañas»*.

### ***Por que esta prueba, habiendo ya una suite de reenvios***

*`test_lo_que_no_se_apunta_dos_veces.py` cubre **la puerta del plan** -`/api/trabajos/previstos/{id}/hecho`- y las
demas. **Pero la cola sin cobertura no manda por ahi**: manda por **`POST /api/trabajos`**, que es el alta directa
de un trabajo hecho. **Esa puerta es la que el movil llama al volver la red**, y es la que hay que probar con la
misma clave dos veces.*

*Es el camino real: el agricultor apunta sin cobertura, la cola guarda el apunte **con su `clave_de_reenvio`**
-que es su `id_local`-, vuelve la red, y si **la respuesta se pierde** el movil reintenta. **El servidor tiene que
reconocerlo, no apuntar el trabajo dos veces.***

*Y el control positivo: **otra clave si es un trabajo nuevo**. Sin el, la prueba pasaria tambien si la puerta
estuviera tirando todos los envios.*
"""

from __future__ import annotations


def _una_labor(cliente, cuenta, campana, parcela, clave: str, **cambios):
    el_cuerpo = {
        "campana_id": campana["id"],
        "tipo": "laboreo",
        # **«grada», que es un apero del catálogo** (`trabajos.SUBTIPOS_DE_LABOREO`). Aquí ponía
        # «gradeo», que no está en el vocabulario del programa: desde el IMP-9 (05/11/2026) la puerta
        # valida el apero y contestaría 422 —que es justo lo que se quiere—, así que la prueba, que mide
        # el reenvío y no el apero, usa uno que existe. Lo que se comprueba aquí sigue siendo lo mismo.
        "subtipo": "grada",
        "fecha": "2026-10-19",
        "parcela_id": parcela["id"],
        "clave_de_reenvio": clave,
    }
    el_cuerpo.update(cambios)
    return cliente.post("/api/trabajos", headers=cuenta["cabeceras"], json=el_cuerpo)


def _los_trabajos(cliente, cuenta) -> list[dict]:
    los = cliente.get("/api/trabajos", headers=cuenta["cabeceras"]).json()
    if isinstance(los, list):
        return los
    return los.get("hechos") or los.get("trabajos") or []


def test_el_mismo_apunte_dos_veces_apunta_UNO(cliente, cuenta, campana, crear_parcela):
    """***La respuesta perdida no duplica el trabajo.***

    *Es la mitad del contrato que le toca al servidor: la cola ya sella la clave, y aqui se comprueba que **la
    puerta la reconoce**.*
    """
    parcela = crear_parcela(alias="La de la respuesta perdida")

    la_primera = _una_labor(cliente, cuenta, campana, parcela, "la-misma-siempre")
    assert la_primera.status_code == 201, la_primera.text
    el_trabajo = la_primera.json().get("hecho") or la_primera.json()

    # *El movil no recibio la respuesta y reintenta: **mismo cuerpo, misma clave**.*
    la_repetida = _una_labor(cliente, cuenta, campana, parcela, "la-misma-siempre")
    assert la_repetida.status_code in (200, 201), (
        f"***un reintento legitimo no puede fallar***: {la_repetida.status_code} {la_repetida.text[:300]}"
    )
    el_repetido = la_repetida.json().get("hecho") or la_repetida.json()
    assert el_repetido.get("id") == el_trabajo.get("id"), (
        f"***tiene que contestar el que ya estaba***: {el_trabajo.get('id')} frente a {el_repetido.get('id')}"
    )

    # ***Y en la finca hay UNO, no dos.***
    los_mios = [uno for uno in _los_trabajos(cliente, cuenta) if uno.get("id") == el_trabajo.get("id")]
    assert len(los_mios) == 1, f"***el mismo apunte tiene que estar una vez***: {len(los_mios)}"


def test_y_otra_clave_SI_es_otro_trabajo(cliente, cuenta, campana, crear_parcela):
    """***El control positivo***: *sin esto, la prueba anterior pasaria tambien si no se apuntara nada.*"""
    parcela = crear_parcela(alias="La de las dos claves")

    la_primera = _una_labor(cliente, cuenta, campana, parcela, "una-clave")
    la_segunda = _una_labor(cliente, cuenta, campana, parcela, "otra-clave")
    assert la_primera.status_code == 201 and la_segunda.status_code == 201

    los_dos = {
        (la_primera.json().get("hecho") or la_primera.json()).get("id"),
        (la_segunda.json().get("hecho") or la_segunda.json()).get("id"),
    }
    assert len(los_dos) == 2, f"***dos claves son dos trabajos***: {los_dos}"


def test_la_misma_clave_con_OTROS_DATOS_es_un_conflicto(cliente, cuenta, campana, crear_parcela):
    """***Y la otra mitad***: *si lo que cambia es el apunte y no el reintento, **se dice**, no se devuelve el que
    estaba **sin mirar** — que era la mitad silenciosa del defecto y la peor, porque no se ve.*
    """
    parcela = crear_parcela(alias="La de la clave repetida con otros datos")

    la_primera = _una_labor(cliente, cuenta, campana, parcela, "la-de-los-dos-datos")
    assert la_primera.status_code == 201, la_primera.text

    la_cambiada = _una_labor(
        cliente, cuenta, campana, parcela, "la-de-los-dos-datos", subtipo="otro-trabajo"
    )
    assert la_cambiada.status_code == 409, (
        f"***la misma clave con otros datos tiene que ser 409***: "
        f"{la_cambiada.status_code} {la_cambiada.text[:300]}"
    )
