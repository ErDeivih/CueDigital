"""Lo que queda en la auditoría cuando alguien toca una ficha (14/10/2026).

POR QUÉ ESTA PRUEBA. El inventario que se hizo para la fusión midió que **tres** caminos de escritura no dejaban
rastro: `enlazar`, `quitar_el_enlace` y `marcar_un_papel` ponían `editado_a_mano = True` y **no** llamaban a
`correcciones.apuntar`. Lo peor no es el hueco en sí: es que `papeles_de_un_contacto` y `enlaces_de_contacto` **no
tienen columna de anulación**, así que una fila borrada **no se puede reconstruir salvo por la auditoría** — y en
esos caminos la auditoría no existía.

Esta prueba mira **la tabla de auditoría**, no la respuesta de la puerta: una puerta que contesta 200 y no deja
rastro es exactamente el defecto que se está arreglando.
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def _lo_apuntado(db_sesion, contacto_id: int, accion: str) -> list[models.Auditoria]:
    """Las filas de auditoría de esa ficha y esa acción, de la más nueva a la más vieja."""
    return list(
        db_sesion.scalars(
            select(models.Auditoria)
            .where(
                models.Auditoria.entidad == "contacto",
                models.Auditoria.entidad_id == contacto_id,
                models.Auditoria.accion == accion,
            )
            .order_by(models.Auditoria.id.desc())
        )
    )


def _una_ficha(cliente, cuenta) -> dict:
    creada = cliente.post(
        "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Cooperativa de la Auditoría"}
    )
    assert creada.status_code == 201, creada.text
    return creada.json()


def test_marcar_un_papel_queda_en_la_auditoria(cliente, cuenta, db_sesion):
    """**Marcar y desmarcar un papel deja su fila.** Antes no dejaba ninguna: el papel se ponía y no quedaba quién."""
    ficha = _una_ficha(cliente, cuenta)
    assert _lo_apuntado(db_sesion, ficha["id"], "papeles") == [], "de partida no hay nada apuntado"

    marcado = cliente.post(
        f"/api/contactos/{ficha['id']}/papeles",
        headers=cuenta["cabeceras"],
        json={"papel": "proveedor", "puesto": True},
    )
    assert marcado.status_code == 200, marcado.text

    db_sesion.expire_all()
    apuntado = _lo_apuntado(db_sesion, ficha["id"], "papeles")
    assert len(apuntado) == 1, f"tiene que quedar una fila: {len(apuntado)}"
    # **Y dice QUÉ se marcó y quién**, que es para lo que sirve.
    assert "proveedor" in str(apuntado[0].datos), f"y con el papel dentro: {apuntado[0].datos}"
    assert apuntado[0].usuario_id is not None, "y con quién lo hizo"

    # Y desmarcarlo deja **otra** fila: el rastro no se pisa, se añade.
    desmarcado = cliente.post(
        f"/api/contactos/{ficha['id']}/papeles",
        headers=cuenta["cabeceras"],
        json={"papel": "proveedor", "puesto": False},
    )
    assert desmarcado.status_code == 200, desmarcado.text
    db_sesion.expire_all()
    quedan = _lo_apuntado(db_sesion, ficha["id"], "papeles")
    assert len(quedan) == 2, f"desmarcarlo tiene que dejar su propia fila: {len(quedan)}"
    assert "proveedor" not in str(quedan[0].datos) or quedan[0].datos != apuntado[0].datos, (
        "y la última tiene que decir el estado de AHORA, no repetir la de antes"
    )
