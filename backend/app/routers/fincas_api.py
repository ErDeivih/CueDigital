"""Las fincas de una cuenta: cuáles puede usar, cambiar de una a otra y quién más entra.

POR QUÉ EXISTE

Hasta la ronda 89 una cuenta estaba atada a una sola finca. David lo pidió al revés —«quiero que una
explotación puedan acceder varias cuentas, no solo 1»— y esto es lo que hace falta para eso, sin tocar el
aislamiento: cada consulta sigue pasando por `explotacion_actual`, que sigue saliendo de la finca en la que
la cuenta está trabajando.

Los cuatro caminos:

  · `GET /api/fincas` — las fincas de esta cuenta, con la suya marcada como la que está usando.
  · `GET /api/fincas/quien-entra` — quién puede entrar en la finca en la que se está trabajando.
  · `POST /api/fincas/cambiar` — ponerse a trabajar en otra finca de las que puede usar (devuelve un vale
    nuevo, porque el vale dice la finca).
  · `POST /api/fincas/quien-entra` y `DELETE /api/fincas/quien-entra/{usuario_id}` — añadir y quitar
    cuentas: **solo el titular** de la finca, salvo que uno se quite a sí mismo.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, func, select

from .. import accesos, models, security, textos
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual
from ..schemas import (
    CambiarDeFincaEntrada,
    FincaSalida,
    NuevaCuentaEnLaFincaEntrada,
    QuienEntraSalida,
    TokenSalida,
)

router = APIRouter(prefix="/api/fincas", tags=["fincas"])

F = textos.FINCAS


def _la_finca(db: Db, explotacion_id: int) -> models.Explotacion:
    finca = db.get(models.Explotacion, explotacion_id)
    if finca is None:
        raise HTTPException(status_code=404, detail=F["no_existe"])
    return finca


def _las_hectareas(db: Db, explotacion_id: int) -> tuple[float, int]:
    """Las hectáreas apuntadas de una finca, y **cuántas tierras no tienen ese dato** (A7, 03/10/2026).

    Se cuenta aquí y no en la pantalla porque el dato es del servidor. Sirve para lo que pidió el diseño de
    Stitch de esta pantalla (ronda 90): al elegir en qué finca trabajas, el tamaño es lo que distingue una
    finca de otra cuando se llaman parecido.

    **Y devuelve también las tierras sin superficie, que es lo que faltaba.** La suma se hacía con
    `coalesce(sum(...), 0.0)`, y SQL **ignora los `NULL`** al sumar: una finca con diez tierras, tres de
    ellas sin superficie apuntada, enseñaba un total más pequeño que parecía completo. Es la misma trampa de
    siempre (un dato que no se sabe convertido en un cero que parece un dato), así que ahora se devuelven las
    dos cosas y quien lo enseñe puede decir «y falta la superficie de 3 tierras».
    """
    total, sin_superficie = db.execute(
        select(
            func.sum(models.Parcela.superficie_ha),
            func.sum(case((models.Parcela.superficie_ha.is_(None), 1), else_=0)),
        ).where(models.Parcela.explotacion_id == explotacion_id)
    ).one()
    return round(float(total or 0.0), 4), int(sin_superficie or 0)


def _como_salida(
    db: Db, uno: models.AccesoAFinca, activa: int
) -> FincaSalida:
    finca = _la_finca(db, uno.explotacion_id)
    hectareas, tierras_sin_superficie = _las_hectareas(db, finca.id)
    return FincaSalida(
        id=finca.id,
        nombre=finca.nombre,
        municipio=finca.municipio or "",
        papel=uno.papel,
        activa=uno.explotacion_id == activa,
        hectareas=hectareas,
        tierras_sin_superficie=tierras_sin_superficie,
    )


@router.get("", response_model=list[FincaSalida])
def mis_fincas(usuario: UsuarioActual, db: Db) -> list[FincaSalida]:
    """Las fincas en las que puede entrar esta cuenta, con la que está usando marcada."""
    return [
        _como_salida(db, uno, usuario.explotacion_id)
        for uno in accesos.fincas_de(db, usuario.id)
    ]


@router.post("/cambiar", response_model=TokenSalida)
def cambiar_de_finca(
    datos: CambiarDeFincaEntrada, usuario: UsuarioActual, db: Db
) -> TokenSalida:
    """Ponerse a trabajar en otra finca de las que puede usar.

    Devuelve un **vale nuevo**, y no es un capricho: el vale dice en qué finca se está trabajando, y es lo
    que impide que un vale viejo siga viendo datos de una finca que ya no se está mirando.
    """
    if not accesos.puede_entrar(db, usuario.id, datos.explotacion_id):
        raise HTTPException(status_code=404, detail=F["no_es_tuya"])
    finca = _la_finca(db, datos.explotacion_id)
    usuario.explotacion_id = finca.id
    db.add(
        models.Auditoria(
            explotacion_id=finca.id,
            usuario_id=usuario.id,
            entidad="explotacion",
            entidad_id=finca.id,
            accion="entrar",
            datos={"correo": usuario.correo},
        )
    )
    db.commit()
    return TokenSalida(
        token=security.crear_token(
            usuario.id, finca.id, version=usuario.token_version or 0
        ),
        usuario_id=usuario.id,
        explotacion_id=finca.id,
        nombre=usuario.nombre,
    )


@router.get("/quien-entra", response_model=QuienEntraSalida)
def quien_entra(
    usuario: UsuarioActual, explotacion: ExplotacionActual, db: Db
) -> QuienEntraSalida:
    """Quién puede entrar en la finca en la que se está trabajando.

    Lo puede ver cualquiera que entre en la finca: saber quién más la usa no es un secreto, y es lo que
    hace falta para pedirle al titular que añada o quite a alguien.
    """
    suyos = accesos.quien_entra(db, explotacion.id)
    personas = []
    for uno in suyos:
        cuenta = db.get(models.Usuario, uno.usuario_id)
        if cuenta is None:
            continue
        personas.append(
            {
                "usuario_id": cuenta.id,
                "nombre": cuenta.nombre,
                "correo": cuenta.correo,
                "papel": uno.papel,
                "eres_tu": cuenta.id == usuario.id,
                # El titular puede quitar a los demás, y cualquiera puede quitarse a sí mismo (menos de su
                # propia finca, que es la suya y no se deja).
                "se_puede_quitar": (
                    cuenta.id != usuario.id or uno.papel != accesos.TITULAR
                )
                and (
                    accesos.es_titular(db, usuario.id, explotacion.id)
                    or cuenta.id == usuario.id
                ),
            }
        )
    return QuienEntraSalida(
        explotacion_id=explotacion.id,
        nombre=explotacion.nombre,
        soy_titular=accesos.es_titular(db, usuario.id, explotacion.id),
        personas=personas,
    )


@router.post("/quien-entra", response_model=QuienEntraSalida, status_code=status.HTTP_201_CREATED)
def anadir_a_la_finca(
    datos: NuevaCuentaEnLaFincaEntrada,
    usuario: UsuarioActual,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> QuienEntraSalida:
    """Le da acceso a otra cuenta que ya está dada de alta en el programa.

    Se pide el correo y no el nombre: el correo es lo que identifica una cuenta y no se repite. Si esa
    cuenta no existe, se dice que se dé de alta primero, que es lo que hay que hacer y no se puede hacer
    por ella (la clave la elige cada uno).
    """
    if not accesos.es_titular(db, usuario.id, explotacion.id):
        raise HTTPException(status_code=403, detail=F["solo_el_titular"])
    correo = datos.correo.strip().lower()
    otra = db.scalar(select(models.Usuario).where(models.Usuario.correo == correo))
    if otra is None:
        raise HTTPException(status_code=404, detail=F["cuenta_que_no_existe"])
    if not otra.activo:
        raise HTTPException(status_code=409, detail=F["cuenta_no_activa"])
    if otra.id == usuario.id:
        raise HTTPException(status_code=409, detail=F["ya_eres_tu"])
    if accesos.puede_entrar(db, otra.id, explotacion.id):
        raise HTTPException(status_code=409, detail=F["ya_estaba"])
    accesos.anadir_acceso(db, otra, explotacion.id, papel=accesos.AYUDANTE)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="acceso",
            entidad_id=otra.id,
            accion="anadir",
            datos={"correo": otra.correo},
        )
    )
    db.commit()
    return quien_entra(usuario, explotacion, db)


@router.delete("/quien-entra/{usuario_id}", response_model=QuienEntraSalida)
def quitar_de_la_finca(
    usuario_id: int,
    usuario: UsuarioActual,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> QuienEntraSalida:
    """Quita el acceso a una cuenta. El titular puede quitar a los demás; uno puede quitarse a sí mismo.

    Y hay uno que no se puede quitar: **el titular de la finca**. Una finca sin titular sería una finca que
    nadie puede gestionar.
    """
    otra = db.get(models.Usuario, usuario_id)
    if otra is None or not accesos.puede_entrar(db, otra.id, explotacion.id):
        raise HTTPException(status_code=404, detail=F["no_entra"])
    es_uno_mismo = otra.id == usuario.id
    if not es_uno_mismo and not accesos.es_titular(db, usuario.id, explotacion.id):
        raise HTTPException(status_code=403, detail=F["solo_el_titular"])
    if accesos.es_titular(db, otra.id, explotacion.id):
        raise HTTPException(status_code=409, detail=F["el_titular_no_se_quita"])
    if not accesos.quitar_acceso(db, otra, explotacion.id):
        raise HTTPException(status_code=409, detail=F["no_se_pudo_quitar"])
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="acceso",
            entidad_id=otra.id,
            accion="quitar",
            datos={"correo": otra.correo, "cuando": dt.datetime.now().isoformat(timespec="seconds")},
        )
    )
    db.commit()
    return quien_entra(usuario, explotacion, db)
