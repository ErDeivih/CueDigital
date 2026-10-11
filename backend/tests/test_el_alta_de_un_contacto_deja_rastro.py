"""CRM-03: el alta de un contacto **deja quién lo apuntó**.

POR QUÉ EXISTE ESTE FICHERO. El contrato pide, para toda entidad de negocio, «autor, fecha de creación,
versión y estado de anulación», y la revisión del T11 lo tenía **fichado y sin arreglar**
(`docs/REVISION_T11.md:364-368`): «las tres tablas nuevas no guardan autor… no se puede saber quién apuntó
una ficha, y `aplicar_la_migracion` no deja rastro en `auditoria` (sí lo dejan corregir, borrar y deshacer)».
Era, de todo lo que le falta a este ticket, **lo más barato**: no hace falta tabla nueva —`correcciones.py`
ya sabe apuntar—, hacía falta que el alta y la migración pasaran por él.

Y la prueba mira **la fila de la auditoría**, no la respuesta: un rastro que solo se ve en la respuesta HTTP
no sirve para lo que sirve un rastro —saber quién hizo qué, cuando ya no está delante—. Se comprueba también
la **forma** del apunte (`{campo: [antes, ahora]}`, y en un alta el «antes» es nada) porque es la misma que
usa una corrección: si el alta guardara otra cosa, la auditoría habría que leerla de dos maneras.
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def _el_rastro(db_sesion, *, entidad: str, entidad_id: int | None, accion: str):
    return list(
        db_sesion.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == entidad,
                models.Auditoria.entidad_id == entidad_id,
                models.Auditoria.accion == accion,
            )
        )
    )


def test_el_alta_de_una_ficha_deja_quien_la_apunto(cliente, cuenta, db_sesion):
    respuesta = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={
            "nombre": "Cooperativa Agrícola de Peñaranda",
            "es_empresa": True,
            "nif": "B09123456",
            "telefono": "947 123 456",
            "papeles": ["proveedor", "comprador"],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    ficha = respuesta.json()

    rastro = _el_rastro(db_sesion, entidad="contacto", entidad_id=ficha["id"], accion="crear")
    assert len(rastro) == 1, (
        f"el alta de una ficha tiene que dejar **una** fila en la auditoría, y ha dejado {len(rastro)}: "
        "el contrato pide autor para toda entidad de negocio"
    )
    apunte = rastro[0]
    assert apunte.usuario_id is not None, (
        "el rastro del alta no dice **quién**: eso es lo que se venía a arreglar"
    )
    assert apunte.datos["nombre"] == [None, "Cooperativa Agrícola de Peñaranda"], (
        f"y guarda el nombre con la misma forma que una corrección (`[antes, ahora]`): {apunte.datos}"
    )
    assert apunte.datos["papeles"] == [None, ["proveedor", "comprador"]], (
        f"y los papeles que se le pusieron, que es de lo que más se corrige después: {apunte.datos}"
    )
    # Y lo que **no** se apuntó vacío: un rastro lleno de `null` no dice nada.
    assert "correo" not in apunte.datos, (
        f"un campo que no se escribió no debería dejar rastro: {apunte.datos}"
    )
