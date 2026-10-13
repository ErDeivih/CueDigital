"""Dependencias compartidas de la API.

La pieza clave es `explotacion_actual`: TODO lo que se consulte o se escriba pasa
por ella. Es lo que impide que un agricultor vea los datos de otro. Si un router
nuevo no la usa, hay un fallo de seguridad, no un detalle de estilo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from . import accesos, models, security
from .database import get_db

Db = Annotated[Session, Depends(get_db)]


def usuario_actual(
    db: Db,
    authorization: Annotated[str | None, Header()] = None,
) -> models.Usuario:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Entra con tu cuenta para poder ver tu cuaderno.",
        )
    token = authorization.split(" ", 1)[1].strip()
    datos = security.leer_token(token)
    if not datos:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Te hemos desconectado por seguridad. Vuelve a entrar.",
        )
    usuario = db.get(models.Usuario, int(datos["uid"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Esa cuenta no está activa. Vuelve a entrar.",
        )
    # El token dice a qué finca pertenece: si no coincide con la del usuario, el
    # token es viejo o está manipulado.
    if usuario.explotacion_id != int(datos["eid"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Te hemos desconectado por seguridad. Vuelve a entrar.",
        )
    # **Y tiene que poder entrar en esa finca** (ronda 89): una finca puede tener varias cuentas y a una
    # cuenta se le puede quitar el acceso. Sin esta comprobación, un vale de una finca de la que ya no se
    # tiene acceso seguiría valiendo, que es justo lo que no puede pasar con datos de otro.
    if not accesos.puede_entrar(db, usuario.id, usuario.explotacion_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ya no tienes acceso a esa finca. Vuelve a entrar.",
        )
    return usuario


UsuarioActual = Annotated[models.Usuario, Depends(usuario_actual)]


def explotacion_actual(usuario: UsuarioActual, db: Db) -> models.Explotacion:
    explotacion = db.get(models.Explotacion, usuario.explotacion_id)
    if explotacion is None:
        raise HTTPException(status_code=404, detail="No encontramos tu finca.")
    return explotacion


ExplotacionActual = Annotated[models.Explotacion, Depends(explotacion_actual)]


def exigir_poder_modificar(usuario: UsuarioActual, db: Db) -> None:
    """**403 si esta cuenta no puede modificar** lo de esta finca (Entrega 4, 13/10/2026).

    POR QUÉ ESTO NO ES UN BOTÓN ESCONDIDO. El encargo lo dice con estas palabras: *«ocultar un botón no constituye
    autorización»*. Esconder el botón está bien para no ofrecer lo que no se puede hacer, pero **la puerta es la que
    autoriza**: se comprueba aquí, en el servidor, y da igual que se llegue por la pantalla, por la URL o por un
    identificador a mano.

    Y **sin fila de acceso no hay capacidad**: una cuenta de la que no se sabe nada **no puede** modificar. Es la
    regla de la casa —lo que no se sabe no se convierte en un «sí»—.
    """
    if not accesos.puede_modificar(db, usuario.id, usuario.explotacion_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta puede mirar esta finca, pero no cambiarla.",
        )


PuedeModificar = Annotated[None, Depends(exigir_poder_modificar)]


def exigir_ver_lo_economico(usuario: UsuarioActual, db: Db) -> None:
    """**403 si esta cuenta no puede ver el dinero** (Entrega 4, 13/10/2026).

    Y no es «esconder los importes»: la puerta **no los manda**. El contrato: *«sin permiso económico: no aparecen
    importes ni documentos restringidos»*.
    """
    if not accesos.puede_ver_lo_economico(db, usuario.id, usuario.explotacion_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no puede ver las cuentas de esta finca.",
        )


PuedeVerLoEconomico = Annotated[None, Depends(exigir_ver_lo_economico)]


def obtener_de_la_explotacion(db: Session, modelo, objeto_id: int, explotacion_id: int):
    """Coge un objeto comprobando que es de esta finca.

    Se usa en todos los routers. Devolver 404 y no 403 es intencionado: así no se
    filtra si un identificador existe o no en otra finca.
    """
    objeto = db.get(modelo, objeto_id)
    if objeto is None or getattr(objeto, "explotacion_id", None) != explotacion_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    return objeto
