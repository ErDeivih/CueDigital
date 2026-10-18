"""**El SERVIDOR deniega las siete operaciones sin capacidad, y no cambia nada** (18/10/2026).

### ***Por que existe esta prueba***

*La revision independiente demostro que **la interfaz ofrecia** siete operaciones que escriben -fusion, borrado
confirmado, notas, bajas, deshacer- a un usuario de consulta. **Y dejo abierto, con razon, si el servidor tambien
las permitia**:*

    «Esto acredita un defecto de interfaz, no prueba por si solo que el servidor permita fusionar o borrar sin
     capacidad.»

***Un fallo de interfaz se arregla escondiendo un boton. Un fallo de servidor es una puerta abierta.*** *Asi que
esto se comprueba **por comportamiento**, no por lo que diga el codigo.*

### ***Y por que se puede probar con identificadores que no existen***

*La dependencia `PuedeModificar` corre **antes** del cuerpo de la puerta: **sin capacidad, la respuesta es 403
antes de mirar si el objeto existe**. Eso hace la prueba corta y, sobre todo, **dice cual es el orden**: el
permiso no se comprueba despues de haber tocado nada.*

*Y en las tres de contactos, ademas, **se mira que el dato siga igual**: un 403 que hubiera dejado el borrado a
medias no seria un 403.*
"""

from __future__ import annotations

import pytest

from test_los_permisos_por_materia import _sin_capacidad  # noqa: E402  — el andamiaje, prestado


# ***Las siete operaciones que la revision reprodujo en la interfaz***, cada una con **su puerta**.
LAS_SIETE = [
    ("POST", "/api/contactos/{a}/fusion/{b}", None, "fusion-hacer"),
    ("POST", "/api/contactos/{a}/deshacer-la-fusion", None, "fusion-deshacer"),
    ("POST", "/api/contactos/{a}/notas", {"texto": "una nota"}, "contacto-nota"),
    ("POST", "/api/contactos/{a}/baja", {}, "contacto-baja"),
    ("DELETE", "/api/contactos/{a}", None, "contacto-borrar-si"),
    ("POST", "/api/bandeja/{a}/confirmar", {}, "bandeja-confirmar"),
    ("POST", "/api/bancos/movimientos/{a}/desconciliar", {"imputaciones": []}, "banco-deshacer"),
]


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo", "accion"), LAS_SIETE)
def test_sin_capacidad_el_servidor_contesta_403(cliente, cuenta, db_sesion, metodo, ruta, cuerpo, accion):
    """***403 en las siete***, y **antes de mirar el objeto** -por eso vale un identificador que no existe-."""
    _sin_capacidad(db_sesion, cuenta, "puede_modificar")

    la_ruta = ruta.format(a=999_001, b=999_002)
    respuesta = cliente.request(metodo, la_ruta, headers=cuenta["cabeceras"], json=cuerpo)

    assert respuesta.status_code == 403, (
        f"***«{accion}» ({metodo} {la_ruta}) tiene que dar 403 sin capacidad***, y da "
        f"{respuesta.status_code}: {respuesta.text[:300]}"
    )


def test_y_con_capacidad_no_da_403(cliente, cuenta):
    """***El control***: *sin quitar la capacidad, esas puertas **no** contestan 403* -contestaran 404, porque el
    objeto no existe, pero **no es un problema de permiso**-.

    *Sin esto, la prueba de arriba podria pasar porque la ruta no existiera.*
    """
    for metodo, ruta, cuerpo, accion in LAS_SIETE:
        la_ruta = ruta.format(a=999_001, b=999_002)
        respuesta = cliente.request(metodo, la_ruta, headers=cuenta["cabeceras"], json=cuerpo)
        assert respuesta.status_code != 403, (
            f"***«{accion}» no puede dar 403 con capacidad***: {respuesta.status_code} {respuesta.text[:200]}"
        )


def test_un_borrado_que_se_deniega_NO_borra(cliente, cuenta, db_sesion):
    """***Y el dato sigue igual***: *un 403 que hubiera borrado a medias no seria un 403.*

    *Se mira la ficha entera despues, que es lo que ve el agricultor.*
    """
    creado = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={"nombre": "El que no se borra", "tipo": "proveedor"},
    )
    assert creado.status_code in (200, 201), creado.text
    el_id = creado.json()["id"]

    _sin_capacidad(db_sesion, cuenta, "puede_modificar")
    assert cliente.delete(f"/api/contactos/{el_id}", headers=cuenta["cabeceras"]).status_code == 403

    # *Y sigue estando, con su nombre.*
    despues = cliente.get(f"/api/contactos/{el_id}", headers=cuenta["cabeceras"])
    assert despues.status_code == 200, f"***el contacto no puede desaparecer***: {despues.status_code}"
    assert despues.json()["nombre"] == "El que no se borra", despues.json()


def test_y_una_nota_que_se_deniega_NO_se_apunta(cliente, cuenta, db_sesion):
    """*Lo mismo con la nota: sin capacidad no se apunta, y la ficha no la trae.*"""
    creado = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={"nombre": "El de la nota", "tipo": "proveedor"},
    )
    el_id = creado.json()["id"]
    antes = cliente.get(f"/api/contactos/{el_id}", headers=cuenta["cabeceras"]).json()

    _sin_capacidad(db_sesion, cuenta, "puede_modificar")
    assert (
        cliente.post(
            f"/api/contactos/{el_id}/notas",
            headers=cuenta["cabeceras"],
            json={"texto": "esta nota no puede entrar"},
        ).status_code
        == 403
    )

    despues = cliente.get(f"/api/contactos/{el_id}", headers=cuenta["cabeceras"]).json()
    assert despues.get("notas", []) == antes.get("notas", []), (
        f"***la nota no puede haberse apuntado***: {despues.get('notas')}"
    )
    assert "esta nota no puede entrar" not in str(despues), despues
