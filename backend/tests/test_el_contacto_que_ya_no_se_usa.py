"""CRM-03, criterio (e): **un contacto inactivo conserva sus relaciones**.

POR QUÉ EXISTE. El inventario de CRM-03 lo midió: hasta hoy **no existía el estado inactivo**, así que el
agricultor que deja de tratar con un proveedor tenía que elegir entre dejarle la ficha como si siguiera
trabajando con él o **borrarla** —y borrarla se lleva por delante el pasado: sus facturas, sus ventas y sus
papeles seguirían apuntándole. Eso es lo que el criterio (e) prohíbe.

**Sin datos inventados**: las fichas y los papeles se crean por las puertas de verdad, como los crea el
agricultor. Lo único que se hace aquí a mano es **la baja**, porque **todavía no tiene puerta propia** (es la
pieza siguiente: su botón, su motivo y su prueba). Queda dicho para que no parezca que ya está.
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def test_un_contacto_recien_apuntado_esta_activo(cliente, cuenta):
    """Lo primero: `True` por defecto. Dar de baja es una decisión que se toma, no el estado de partida."""
    respuesta = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={"nombre": "Suministros del Páramo, S.L.", "papeles": ["proveedor"]},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json().get("activo") is True, (
        f"una ficha recién apuntada tiene que estar activa: {respuesta.json()}"
    )


def test_el_contacto_de_baja_conserva_sus_papeles_y_su_ficha_se_lee(cliente, cuenta, db_sesion):
    """Y lo que pide el criterio (e), que es lo que importa.

    Se da de baja **en la base** (no hay puerta todavía), y se exige que:
    1. la ficha **siga estando** y se pueda leer por su puerta, con su estado nuevo;
    2. **conserve sus papeles** —que es la «relación» que declara el criterio—;
    3. y deje de contar como activa, que es lo que servirá para no ofrecerla donde ya no toca.
    """
    respuesta = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={
            "nombre": "Taller Agrícola Sanz",
            "telefono": "923 000 000",
            "papeles": ["taller", "proveedor"],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    ficha = respuesta.json()
    papeles_de_antes = sorted(ficha.get("papeles") or [])
    assert papeles_de_antes == ["proveedor", "taller"], f"la prueba necesita dos papeles: {ficha}"

    # La baja, a mano y a la vista: es lo que todavía no tiene puerta.
    contacto = db_sesion.get(models.Contacto, ficha["id"])
    contacto.activo = False
    db_sesion.commit()

    # 1. La ficha sigue leyéndose, y dice que está de baja.
    suya = cliente.get(f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"])
    assert suya.status_code == 200, (
        f"un contacto de baja NO se borra: su ficha tiene que seguir leyéndose ({suya.status_code})"
    )
    assert suya.json()["activo"] is False, f"y tiene que decirlo: {suya.json().get('activo')}"
    assert suya.json()["nombre"] == "Taller Agrícola Sanz"

    # 2. Y conserva sus papeles: eso es la relación que el criterio manda conservar.
    los_papeles = list(
        db_sesion.scalars(
            select(models.PapelDeUnContacto).where(models.PapelDeUnContacto.contacto_id == ficha["id"])
        )
    )
    assert sorted(papel.papel for papel in los_papeles) == papeles_de_antes, (
        f"dar de baja no puede llevarse los papeles: {[papel.papel for papel in los_papeles]}"
    )
