"""**El piloto de la edicion concurrente: el tratamiento** (CRM-08, 17/10/2026).

El ticket lo pide asi: *«Piloto en formulario de **trabajo** y **factura**»*, y esto es el trabajo:
`PUT /api/tratamientos/{id}`, que es la puerta que corrige un tratamiento ya apuntado.

***Lo que hay que poder decir***: si el formulario manda **la version que tenia** y el apunte ha cambiado
desde entonces, **no se escribe nada** y se contesta **409** diciendo quien lo cambio. *«No ultimo escritor
silencioso.»*
"""

from __future__ import annotations


def _un_tratamiento(cliente, cuenta, campana, crear_parcela, producto, **cambios):
    parcela = crear_parcela(superficie_ha=3.0)
    cuerpo = {
        "campana_id": campana["id"],
        "fecha": "2026-05-05",
        "parcela_id": parcela["id"],
        "producto_id": producto["id"],
        "dosis": 0.5,
        "superficie_tratada_ha": 3.0,
        "justificacion": "Vi la plaga o la hierba en el campo",
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---------------------------------------------------------------------------
# 1 · Sin version esperada: como siempre
# ---------------------------------------------------------------------------


def test_sin_version_esperada_se_corrige_como_siempre(
    cliente, cuenta, campana, crear_parcela, producto
):
    """***La compatibilidad.*** Un formulario que no manda version sigue funcionando igual.

    *Es lo que deja encender esto puerta a puerta: las dieciseis que ya corregian no se enteran.*
    """
    suyo = _un_tratamiento(cliente, cuenta, campana, crear_parcela, producto)

    respuesta = cliente.put(
        f"/api/tratamientos/{suyo['id']}",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-05",
            "parcela_id": suyo["parcela_id"],
            "producto_id": suyo["producto_id"],
            "dosis": 0.6,
            "superficie_tratada_ha": 3.0,
        "justificacion": "Vi la plaga o la hierba en el campo",
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["dosis"] == 0.6


# ---------------------------------------------------------------------------
# 2 · Con la version buena
# ---------------------------------------------------------------------------


def test_con_la_version_BUENA_se_corrige(cliente, cuenta, campana, crear_parcela, producto):
    """***El camino bueno***: se manda **la version que tiene**, y cuadra.

    ***Y no es cero***: *un apunte recien creado ya tiene historia* -su alta dejo una fila en la auditoria-,
    asi que su version es **la de su alta**. Se coge de la respuesta, que es de donde la coge el formulario.
    """
    suyo = _un_tratamiento(cliente, cuenta, campana, crear_parcela, producto)
    assert suyo["version"] is not None, "***la respuesta tiene que traer la version***"
    assert suyo["version"] > 0, "***y la de un apunte dado de alta no es cero***"

    respuesta = cliente.put(
        f"/api/tratamientos/{suyo['id']}",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-05",
            "parcela_id": suyo["parcela_id"],
            "producto_id": suyo["producto_id"],
            "dosis": 0.65,
            "superficie_tratada_ha": 3.0,
        "justificacion": "Vi la plaga o la hierba en el campo",
            "version_esperada": suyo["version"],
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["dosis"] == 0.65


# ---------------------------------------------------------------------------
# 3 · Y con la mala: 409, y NO se escribe nada
# ---------------------------------------------------------------------------


def test_con_la_version_MALA_contesta_409_Y_NO_se_escribe_nada(
    cliente, cuenta, campana, crear_parcela, producto
):
    """***«No ultimo escritor silencioso.»***

    Se corrige una vez -para que el apunte tenga historia-, y luego se intenta corregir **diciendo la
    version vieja**, que es lo que le pasaria a quien tuviera el formulario abierto de antes.
    """
    suyo = _un_tratamiento(cliente, cuenta, campana, crear_parcela, producto)
    la_url = f"/api/tratamientos/{suyo['id']}"
    base = {
        "campana_id": campana["id"],
        "fecha": "2026-05-05",
        "parcela_id": suyo["parcela_id"],
        "producto_id": suyo["producto_id"],
        "superficie_tratada_ha": 3.0,
        "justificacion": "Vi la plaga o la hierba en el campo",
    }

    # La primera correccion: aqui el apunte pasa a tener historia.
    primera = cliente.put(
        la_url, headers=cuenta["cabeceras"], json={**base, "dosis": 0.6}
    )
    assert primera.status_code == 200, primera.text
    assert primera.json()["dosis"] == 0.6

    # Y ahora, alguien que tenia el formulario abierto **de antes** manda la version 0.
    choque = cliente.put(
        la_url,
        headers=cuenta["cabeceras"],
        json={**base, "dosis": 0.7, "version_esperada": suyo["version"]},
    )

    assert choque.status_code == 409, choque.text
    assert "ha cambiado" in choque.json()["detail"], choque.json()["detail"]

    # ***Y LO QUE IMPORTA: no se ha escrito nada.***
    despues = cliente.get(la_url, headers=cuenta["cabeceras"])
    assert despues.status_code == 200, despues.text
    assert despues.json()["dosis"] == 0.6, (
        f"***la dosis del que llego tarde NO se ha escrito***: {despues.json()['dosis']}"
    )
