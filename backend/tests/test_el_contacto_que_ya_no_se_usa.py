"""CRM-03, criterio (e): **un contacto inactivo conserva sus relaciones**.

POR QUÉ EXISTE. El inventario de CRM-03 lo midió: hasta hoy **no existía el estado inactivo**, así que el
agricultor que deja de tratar con un proveedor tenía que elegir entre dejarle la ficha como si siguiera
trabajando con él o **borrarla** —y borrarla se lleva por delante el pasado: sus facturas, sus ventas y sus
papeles seguirían apuntándole—. Eso es lo que el criterio (e) prohíbe.

**Sin datos inventados y por las puertas de verdad**: las fichas se crean como las crea el agricultor
(`POST /api/contactos`) y se dan de baja y se vuelven a usar por **la suya** (`/baja` y `/alta`). La primera
versión de esta prueba **daba de baja a mano en la base** porque la puerta no existía; ya existe, así que la
prueba la usa.
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def _una_ficha(cliente, cuenta, nombre: str, papeles: list[str]) -> dict:
    respuesta = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={"nombre": nombre, "telefono": "923 000 000", "papeles": papeles},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _los_papeles(db_sesion, contacto_id: int) -> list[str]:
    return sorted(
        papel.papel
        for papel in db_sesion.scalars(
            select(models.PapelDeUnContacto).where(models.PapelDeUnContacto.contacto_id == contacto_id)
        )
    )


def _la_traza(db_sesion, contacto_id: int, accion: str):
    return list(
        db_sesion.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == "contacto",
                models.Auditoria.entidad_id == contacto_id,
                models.Auditoria.accion == accion,
            )
        )
    )


def test_un_contacto_recien_apuntado_esta_activo(cliente, cuenta):
    """Lo primero: `True` por defecto. Dar de baja es una decisión que se toma, no el estado de partida."""
    ficha = _una_ficha(cliente, cuenta, "Suministros del Páramo, S.L.", ["proveedor"])
    assert ficha.get("activo") is True, f"una ficha recién apuntada tiene que estar activa: {ficha}"


def test_la_baja_conserva_sus_papeles_y_su_ficha_se_sigue_leyendo(cliente, cuenta, db_sesion):
    """Lo que pide el criterio (e), por la puerta de verdad."""
    ficha = _una_ficha(cliente, cuenta, "Taller Agrícola Sanz", ["taller", "proveedor"])
    papeles_de_antes = _los_papeles(db_sesion, ficha["id"])
    assert papeles_de_antes == ["proveedor", "taller"], f"la prueba necesita dos papeles: {ficha}"

    baja = cliente.post(
        f"/api/contactos/{ficha['id']}/baja",
        headers=cuenta["cabeceras"],
        json={"motivo": "Se jubiló y cerró el taller"},
    )
    assert baja.status_code == 200, baja.text
    assert baja.json()["activo"] is False, f"la baja tiene que decirlo: {baja.json().get('activo')}"

    # 1. La ficha sigue leyéndose: un contacto de baja NO se borra.
    suya = cliente.get(f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"])
    assert suya.status_code == 200, (
        f"un contacto de baja no se borra: su ficha tiene que seguir leyéndose ({suya.status_code})"
    )
    assert suya.json()["activo"] is False
    assert suya.json()["nombre"] == "Taller Agrícola Sanz"

    # 2. Y conserva sus papeles: eso es la relación que el criterio manda conservar.
    assert _los_papeles(db_sesion, ficha["id"]) == papeles_de_antes, (
        "dar de baja no puede llevarse los papeles"
    )

    # 3. La vuelta existe y funciona: dar de baja no puede ser de un solo sentido (un proveedor vuelve, y
    #    volver a apuntarlo duplicaría su ficha, con las facturas viejas apuntando a la de antes).
    alta = cliente.post(
        f"/api/contactos/{ficha['id']}/alta",
        headers=cuenta["cabeceras"],
        json={"motivo": "Ha vuelto a abrir"},
    )
    assert alta.status_code == 200, alta.text
    assert alta.json()["activo"] is True, f"y volver a usarlo tiene que decirlo: {alta.json().get('activo')}"
    assert _los_papeles(db_sesion, ficha["id"]) == papeles_de_antes


def test_la_baja_y_la_vuelta_dejan_traza_con_su_motivo(cliente, cuenta, db_sesion):
    """**Y queda quién lo hizo y por qué** (11/10/2026).

    Es lo que hace que esta decisión se pueda revisar dentro de un año: «¿por qué dejamos de trabajar con
    este?». Dar de baja **no** es una corrección de los datos, así que va con **su propia acción** en la
    auditoría, no con la de corregir.
    """
    ficha = _una_ficha(cliente, cuenta, "Cooperativa de Peñaranda", ["comprador"])
    baja = cliente.post(
        f"/api/contactos/{ficha['id']}/baja",
        headers=cuenta["cabeceras"],
        json={"motivo": "Cambió de comprador y ya no nos compra"},
    )
    assert baja.status_code == 200, baja.text

    rastro = _la_traza(db_sesion, ficha["id"], "baja")
    assert len(rastro) == 1, f"la baja tiene que dejar una fila de auditoría, y ha dejado {len(rastro)}"
    assert rastro[0].usuario_id is not None, "y decir quién la hizo"
    assert rastro[0].datos["activo"] == [True, False], f"con el cambio, para poder leerlo: {rastro[0].datos}"
    assert rastro[0].datos["motivo"] == [None, "Cambió de comprador y ya no nos compra"], (
        f"y con el motivo, que es para lo que se guarda: {rastro[0].datos}"
    )

    # Y la vuelta, con su propia acción: las dos mitades se distinguen en la auditoría.
    cliente.post(f"/api/contactos/{ficha['id']}/alta", headers=cuenta["cabeceras"], json={"motivo": "Vuelve"})
    rastro_alta = _la_traza(db_sesion, ficha["id"], "alta")
    assert len(rastro_alta) == 1, "volver a usarlo también tiene que dejar su traza"
    assert rastro_alta[0].datos["activo"] == [False, True]


def test_dar_de_baja_dos_veces_no_apunta_dos_veces(cliente, cuenta, db_sesion):
    """Reenviar la baja no puede dejar dos filas ni cambiar la fecha de la primera.

    Es la misma regla que en el resto del programa: **una acción que ya está hecha no se vuelve a apuntar**
    —el agricultor con guantes toca dos veces, y el programa no puede contar dos bajas donde hubo una—.
    """
    ficha = _una_ficha(cliente, cuenta, "Recambios del Páramo", ["proveedor"])
    primera = cliente.post(f"/api/contactos/{ficha['id']}/baja", headers=cuenta["cabeceras"], json={})
    segunda = cliente.post(f"/api/contactos/{ficha['id']}/baja", headers=cuenta["cabeceras"], json={})
    assert primera.status_code == 200 and segunda.status_code == 200
    assert segunda.json()["activo"] is False
    assert len(_la_traza(db_sesion, ficha["id"], "baja")) == 1, (
        "dos bajas seguidas tienen que dejar **una** traza: la segunda no cambia nada"
    )


def test_un_contacto_de_baja_se_sigue_ofreciendo_para_lo_de_antes(cliente, cuenta, db_sesion):
    """**Y sigue ofreciéndose, a propósito** (CRM-03, criterio (e), 11/10/2026).

    La decisión, y su motivo, que conviene no deshacer: en este programa los sitios donde se ofrece un contacto
    son sitios de **historia** —enlazar el nombre escrito en una factura vieja, elegir el comprador de una venta
    pasada—, y **el proveedor con el que ya no trabajas es justamente el que necesita que sus papeles viejos
    sigan teniendo ficha**. Filtrarlo sería quitar la ficha que hace falta para ese trabajo. Lo que hace un
    contacto de baja es **decirlo** —su rótulo lleva «DE BAJA»—, no esconderse.

    Esta prueba existe para que nadie lo «arregle» filtrando sin leer esto.
    """
    ficha = _una_ficha(cliente, cuenta, "Proveedor de toda la vida", ["proveedor"])
    cliente.post(f"/api/contactos/{ficha['id']}/baja", headers=cuenta["cabeceras"], json={"motivo": "Se jubiló"})

    suyos = cliente.get("/api/contactos", headers=cuenta["cabeceras"])
    assert suyos.status_code == 200, suyos.text
    el_suyo = [uno for uno in suyos.json() if uno["id"] == ficha["id"]]
    assert el_suyo, (
        "un contacto de baja tiene que seguir en la lista: sus facturas y sus ventas viejas lo necesitan"
    )
    assert el_suyo[0]["activo"] is False, "y tiene que venir con su estado, para poder marcarlo"
    assert el_suyo[0]["papeles"] == ["proveedor"], "y con sus papeles"