"""Los canales de un contacto: varios teléfonos, correos y direcciones (Entrega 2, 13/10/2026).

POR QUÉ. Hasta hoy la ficha tenía **un** teléfono, **un** correo y **una** dirección, y eso no es lo que pasa: una
cooperativa tiene el de administración y el del almacén, la persona de contacto tiene su móvil, y la dirección de
entrega no es la de la sede. Con un solo hueco, el agricultor apunta uno y **pierde los otros**.

Aquí se prueba **la migración**: lo que ya estaba apuntado en las cuatro columnas de siempre pasa a ser el canal
**principal** de su clase, **tal cual estaba** —sin arreglar el teléfono, sin inventar prefijos, sin tocar un
texto—, y **correrla dos veces no duplica nada**. Las puertas y la pantalla van en sus pruebas.
"""

from __future__ import annotations

from sqlalchemy import select

from app import database, models


def _un_contacto_con_todo(cliente, cuenta, **cambios) -> dict:
    datos = {
        "nombre": "Cooperativa Agrícola de Peñaranda",
        "telefono": "947 123 456",
        "correo": "administracion@cooperativa.test",
        "direccion": "Calle Mayor 3",
        "localidad": "Peñaranda de Bracamonte",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/contactos", headers=cuenta["cabeceras"], json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _los_canales_de(db_sesion, contacto_id: int) -> list[models.CanalDeUnContacto]:
    db_sesion.expire_all()
    return list(
        db_sesion.scalars(
            select(models.CanalDeUnContacto).where(models.CanalDeUnContacto.contacto_id == contacto_id)
        )
    )


def test_la_migracion_lleva_lo_que_ya_estaba_a_su_canal_principal(cliente, cuenta, db_sesion):
    """Lo que ya estaba apuntado **no se pierde**: pasa a ser el principal de su clase, tal cual."""
    ficha = _un_contacto_con_todo(cliente, cuenta)
    assert _los_canales_de(db_sesion, ficha["id"]) == [], "de partida no hay canales: son nuevos"

    llevados = database.llevar_los_canales_de_los_contactos_a_su_tabla()
    assert llevados >= 3, f"tenía que llevarse el teléfono, el correo y la dirección: {llevados}"

    suyos = _los_canales_de(db_sesion, ficha["id"])
    assert sorted(canal.clase for canal in suyos) == ["correo", "direccion", "telefono"], (
        f"una clase por cada cosa apuntada: {[(c.clase, c.telefono, c.correo, c.direccion) for c in suyos]}"
    )
    assert all(canal.principal for canal in suyos), "y lo que ya estaba es lo **principal** de su clase"

    # **Tal cual estaba apuntado.** Ni el teléfono se «arregla» ni la dirección se reescribe.
    el_telefono = next(canal for canal in suyos if canal.clase == "telefono")
    assert el_telefono.telefono == "947 123 456", f"el teléfono se ha tocado: {el_telefono.telefono}"
    assert el_telefono.etiqueta is None, "y no se le inventa una etiqueta que nadie ha escrito"

    la_direccion = next(canal for canal in suyos if canal.clase == "direccion")
    assert la_direccion.direccion == "Calle Mayor 3", la_direccion.direccion
    assert la_direccion.localidad == "Peñaranda de Bracamonte", (
        f"la dirección se lleva con su localidad, que es como se apunta: {la_direccion.localidad}"
    )


def test_la_migracion_se_puede_correr_dos_veces(cliente, cuenta, db_sesion):
    """**Idempotencia**: correrla otra vez no duplica ni un canal.

    Es lo que pide el encargo al cerrar una migración, y aquí importa de verdad: este paso se ejecuta **en cada
    arranque** del programa, así que una migración que se repitiera iría llenando la tabla de copias.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()
    cuantos = len(_los_canales_de(db_sesion, ficha["id"]))
    assert cuantos == 3, cuantos

    otra_vez = database.llevar_los_canales_de_los_contactos_a_su_tabla()
    assert otra_vez == 0, f"la segunda vuelta no puede llevar nada, y ha llevado {otra_vez}"
    assert len(_los_canales_de(db_sesion, ficha["id"])) == cuantos, "y no puede haber duplicados"


def test_una_ficha_sin_datos_no_crea_ningun_canal(cliente, cuenta, db_sesion):
    """Una ficha de la que no se sabe nada **no inventa canales vacíos**: no hay nada que llevar."""
    respuesta = cliente.post(
        "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Solo el nombre"}
    )
    assert respuesta.status_code == 201, respuesta.text
    suya = respuesta.json()

    database.llevar_los_canales_de_los_contactos_a_su_tabla()
    assert _los_canales_de(db_sesion, suya["id"]) == [], "sin teléfono, sin correo y sin dirección no hay canal"


def test_la_migracion_no_toca_los_campos_de_siempre(cliente, cuenta, db_sesion):
    """**Copia, no traslada**: los cuatro campos de la ficha se quedan como están.

    Los leen cinco sitios (la exportación, la búsqueda global, la ficha, la tabla y la corrección), así que moverlos
    sería romper cinco cosas para ganar ninguna. Y lo que un documento diga de un contacto **no se toca nunca**.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()

    db_sesion.expire_all()
    la_ficha = db_sesion.get(models.Contacto, ficha["id"])
    assert la_ficha.telefono == "947 123 456", la_ficha.telefono
    assert la_ficha.correo == "administracion@cooperativa.test", la_ficha.correo
    assert la_ficha.direccion == "Calle Mayor 3", la_ficha.direccion
    assert la_ficha.localidad == "Peñaranda de Bracamonte", la_ficha.localidad
