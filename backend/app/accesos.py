"""Quién puede entrar en cada finca (varias cuentas en la misma explotación).

POR QUÉ ESTE FICHERO

Hasta la ronda 89, `usuarios.explotacion_id` era el único sitio donde se decía de quién era una finca: una
cuenta, una finca. David pidió lo contrario —«quiero que una explotación puedan acceder varias cuentas, no
solo 1»—, y eso es lo que se resuelve aquí, **sin tocar el aislamiento**: cada tabla de negocio sigue
llevando su `explotacion_id` y lo de otra finca sigue contestando 404.

Las tres reglas, que es lo que hay que poder leer de un vistazo:

  1. **Una cuenta siempre tiene su finca** (la que creó al darse de alta) y no se puede quedar sin ella.
  2. **El titular puede añadir y quitar cuentas** de su finca; un ayudante usa la finca entera pero no
     decide quién más entra.
  3. **Cambiar de finca es cambiar `usuarios.explotacion_id`** y volver a entrar (el vale nuevo dice la
     finca en la que se trabaja). Así todo lo que ya había sigue funcionando igual.

`asegurar_accesos` es la puesta al día: rellena el acceso de las cuentas que ya existían antes de que esta
tabla existiera (la de David, por ejemplo). Sin eso, al actualizar el programa **nadie podría entrar**.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models

TITULAR = "titular"
AYUDANTE = "ayudante"


def asegurar_accesos(db: Session) -> int:
    """Le pone a cada cuenta el acceso a su propia finca si le falta. Devuelve cuántos ha puesto.

    Se llama al arrancar el programa. Es idempotente: si ya están, no hace nada.
    """
    usuarios = list(db.scalars(select(models.Usuario)))
    puestos = 0
    for usuario in usuarios:
        if usuario.explotacion_id is None:
            continue
        ya = db.scalar(
            select(models.AccesoAFinca).where(
                models.AccesoAFinca.usuario_id == usuario.id,
                models.AccesoAFinca.explotacion_id == usuario.explotacion_id,
            )
        )
        if ya is not None:
            continue
        db.add(
            models.AccesoAFinca(
                usuario_id=usuario.id,
                explotacion_id=usuario.explotacion_id,
                papel=TITULAR if usuario.es_titular else AYUDANTE,
            )
        )
        puestos += 1
    if puestos:
        db.commit()
    return puestos


def acceso(db: Session, usuario_id: int, explotacion_id: int) -> models.AccesoAFinca | None:
    """El acceso de una cuenta a una finca, o nada si no lo tiene."""
    return db.scalar(
        select(models.AccesoAFinca).where(
            models.AccesoAFinca.usuario_id == usuario_id,
            models.AccesoAFinca.explotacion_id == explotacion_id,
        )
    )


def puede_entrar(db: Session, usuario_id: int, explotacion_id: int) -> bool:
    return acceso(db, usuario_id, explotacion_id) is not None



def _la_capacidad(db, usuario_id: int, explotacion_id: int, cual: str) -> bool:
    """El valor de una capacidad, mirando el acceso. **Sin fila de acceso, no hay capacidad.**"""
    acceso = db.scalar(
        select(models.AccesoAFinca).where(
            models.AccesoAFinca.usuario_id == usuario_id,
            models.AccesoAFinca.explotacion_id == explotacion_id,
        )
    )
    if acceso is None:
        return False
    return bool(getattr(acceso, cual))


def puede_modificar(db, usuario_id: int, explotacion_id: int) -> bool:
    """**Modificar** lo de esa finca (Entrega 4, 13/10/2026): apuntar, corregir y quitar.

    Consultar ya lo da el propio acceso a la finca: esto es lo que se puede **cambiar**.
    """
    return _la_capacidad(db, usuario_id, explotacion_id, "puede_modificar")


def puede_ver_lo_economico(db, usuario_id: int, explotacion_id: int) -> bool:
    """**Consultar lo económico**: los saldos, los importes y los documentos con dinero.

    El contrato lo dice con estas palabras: *«ocultar dinero también lo elimina de la respuesta»*. Por eso esto
    no se comprueba en la pantalla, sino **en la puerta**: si no hay capacidad, la respuesta no lleva el dinero
    —ni la pantalla puede enseñarlo aunque quiera—.
    """
    return _la_capacidad(db, usuario_id, explotacion_id, "puede_ver_lo_economico")

def es_titular(db: Session, usuario_id: int, explotacion_id: int) -> bool:
    suyo = acceso(db, usuario_id, explotacion_id)
    return suyo is not None and suyo.papel == TITULAR


def fincas_de(db: Session, usuario_id: int) -> list[models.AccesoAFinca]:
    """Las fincas en las que puede entrar esta cuenta, **la suya primero** y luego por nombre.

    El orden importa poco en pantalla, pero que la suya salga primera sí: es en la que trabaja casi
    siempre.
    """
    accesos = list(
        db.scalars(
            select(models.AccesoAFinca)
            .where(models.AccesoAFinca.usuario_id == usuario_id)
            .order_by(models.AccesoAFinca.explotacion_id)
        )
    )
    usuario = db.get(models.Usuario, usuario_id)
    accesos.sort(key=lambda uno: (0 if uno.explotacion_id == usuario.explotacion_id else 1, uno.id))
    return accesos


def quien_entra(db: Session, explotacion_id: int) -> list[models.AccesoAFinca]:
    """Las cuentas que pueden entrar en una finca, el titular primero."""
    accesos = list(
        db.scalars(
            select(models.AccesoAFinca)
            .where(models.AccesoAFinca.explotacion_id == explotacion_id)
            .order_by(models.AccesoAFinca.id)
        )
    )
    accesos.sort(key=lambda uno: (0 if uno.papel == TITULAR else 1, uno.id))
    return accesos


def anadir_acceso(
    db: Session, usuario: models.Usuario, explotacion_id: int, papel: str = AYUDANTE
) -> models.AccesoAFinca:
    """Le da a una cuenta acceso a una finca. Si ya lo tenía, devuelve el que había."""
    ya = acceso(db, usuario.id, explotacion_id)
    if ya is not None:
        return ya
    nuevo = models.AccesoAFinca(
        usuario_id=usuario.id, explotacion_id=explotacion_id, papel=papel
    )
    db.add(nuevo)
    db.flush()
    return nuevo


def quitar_acceso(db: Session, usuario: models.Usuario, explotacion_id: int) -> bool:
    """Le quita a una cuenta el acceso a una finca. Devuelve si se ha quitado.

    **La finca propia no se quita**, y no es un capricho: es lo que garantiza que ninguna cuenta se quede
    sin finca en la que trabajar (todas las consultas pasan por `usuarios.explotacion_id`). Si la cuenta
    estaba trabajando en esa finca se la devuelve a la suya, y el vale viejo deja de valer: al entrar otra
    vez se le da uno de su finca.
    """
    suyo = acceso(db, usuario.id, explotacion_id)
    if suyo is None:
        return False
    if suyo.explotacion_id == usuario.explotacion_id and suyo.papel == TITULAR:
        return False
    db.delete(suyo)
    # Y se le devuelve a su finca si estaba trabajando en la que acaba de dejar.
    propia = db.scalar(
        select(models.AccesoAFinca).where(
            models.AccesoAFinca.usuario_id == usuario.id,
            models.AccesoAFinca.papel == TITULAR,
        )
    )
    if propia is not None and usuario.explotacion_id == explotacion_id:
        usuario.explotacion_id = propia.explotacion_id
    db.flush()
    return True
