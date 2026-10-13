"""Cuenta: darse de alta y entrar.

Decisión de usabilidad: el alta pide lo mínimo. Nombre, correo, clave y los datos
de la finca. Todo lo demás (parcelas, productos, máquinas) se puede añadir después
o traer del SIGPAC. Si el alta pide cuarenta datos, el agricultor no llega al final.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import accesos, certificados, models, security, textos
from ..deps import Db, UsuarioActual
from ..schemas import EntrarEntrada, ExplotacionSalida, RegistroEntrada, TokenSalida

router = APIRouter(prefix="/api/cuenta", tags=["cuenta"])


def _con_nif_normalizado(valores: dict) -> dict:
    """Guarda el NIF siempre de la misma forma.

    Es lo que después se compara con el del certificado digital: "70922320a " y
    "70922320A" tienen que ser el mismo NIF, o el agricultor no podría entrar con su
    certificado por haber escrito el NIF con un espacio de más al darse de alta.
    """
    if valores.get("nif"):
        valores["nif"] = certificados.normaliza_nif(valores["nif"]) or valores["nif"]
    return valores


@router.post("/registro", response_model=TokenSalida, status_code=status.HTTP_201_CREATED)
def registrar(datos: RegistroEntrada, db: Db) -> TokenSalida:
    correo = datos.correo.strip().lower()
    if db.scalar(select(models.Usuario).where(models.Usuario.correo == correo)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese correo ya está usado. Prueba a entrar, o usa otro correo.",
        )
    try:
        clave_hash = security.hash_clave(datos.clave)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    explotacion = models.Explotacion(**_con_nif_normalizado(datos.explotacion.model_dump()))
    db.add(explotacion)
    db.flush()  # hace falta el id antes de crear el usuario

    usuario = models.Usuario(
        explotacion_id=explotacion.id,
        nombre=datos.nombre.strip(),
        correo=correo,
        clave_hash=clave_hash,
        es_titular=True,
    )
    db.add(usuario)
    db.flush()  # hace falta el id para el acceso de abajo

    # **Quien crea la finca es su titular** y queda apuntado como tal (ronda 89): es lo que después permite
    # añadir otras cuentas a la misma finca y decidir quién entra.
    db.add(
        models.AccesoAFinca(
            usuario_id=usuario.id,
            explotacion_id=explotacion.id,
            papel=accesos.TITULAR,
        )
    )

    # La campaña del año se crea sola: es un dato que el agricultor no tiene por qué
    # saber que existe, y sin ella no se puede apuntar nada.
    anio = dt.date.today().year
    db.add(
        models.Campana(
            explotacion_id=explotacion.id,
            anio=anio,
            fecha_inicio=dt.date(anio, 1, 1),
            fecha_fin=dt.date(anio, 12, 31),
        )
    )
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="explotacion",
            entidad_id=explotacion.id,
            accion="crear",
            datos={"nombre": explotacion.nombre, "nif": explotacion.nif},
        )
    )
    db.commit()

    return TokenSalida(
        token=security.crear_token(usuario.id, explotacion.id),
        usuario_id=usuario.id,
        explotacion_id=explotacion.id,
        nombre=usuario.nombre,
    )


@router.post("/entrar", response_model=TokenSalida)
def entrar(datos: EntrarEntrada, db: Db) -> TokenSalida:
    correo = datos.correo.strip().lower()
    usuario = db.scalar(select(models.Usuario).where(models.Usuario.correo == correo))
    # Se comprueba la clave aunque el usuario no exista, para no revelar qué correos
    # están dados de alta.
    if usuario is None or not security.verificar_clave(datos.clave, usuario.clave_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo o la clave no son correctos. Vuelve a probar.",
        )
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Esa cuenta no está activa.")

    return TokenSalida(
        token=security.crear_token(usuario.id, usuario.explotacion_id),
        usuario_id=usuario.id,
        explotacion_id=usuario.explotacion_id,
        nombre=usuario.nombre,
    )


@router.get("/yo")
def yo(usuario: UsuarioActual, db: Db) -> dict:
    explotacion = db.get(models.Explotacion, usuario.explotacion_id)
    return {
        "usuario_id": usuario.id,
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "es_titular": usuario.es_titular,
        # **Las capacidades por materia** (Entrega 4, 13/10/2026). Van aquí —y no en `/api/interfaz`, que es público
        # y va **antes de entrar**— porque son de **esta cuenta en esta finca**.
        #
        # **Para qué sirven en el front, y para qué NO**: para **no ofrecer** lo que no se puede hacer (esconder el
        # botón, el bloque del dinero y el alta) y para no pedir a una puerta que va a contestar 403. Lo que **no**
        # hacen es autorizar: el encargo lo dice con estas palabras, *«ocultar un botón no constituye autorización»*,
        # y la autorización está en la puerta, que la comprueba **en el servidor** por mucho que alguien llegue a
        # mano por la URL o por un identificador.
        "puede_modificar": accesos.puede_modificar(db, usuario.id, usuario.explotacion_id),
        # Y el dinero: si esto es `False`, el saldo **no viaja** —la puerta contesta 403— y la pantalla no tiene nada
        # que esconder porque no lo recibe.
        "puede_ver_lo_economico": accesos.puede_ver_lo_economico(db, usuario.id, usuario.explotacion_id),
        "explotacion": ExplotacionSalida.model_validate(explotacion).model_dump(),
    }


# --------------------------------------------------------------------------
# Entrar con el certificado digital
#
# El agricultor ya tiene el certificado: se lo dio la FNMT y es lo que usa para hablar
# con la administración. Poder entrar con él significa no teclear nada, y además es el
# requisito de IUWS, que exige certificado de persona jurídica.
# --------------------------------------------------------------------------


def _explotacion_por_nif(db: Session, nif: str) -> models.Explotacion | None:
    limpio = certificados.normaliza_nif(nif)
    if not limpio:
        return None
    return db.scalar(select(models.Explotacion).where(models.Explotacion.nif == limpio))


def _usuario_titular(db: Session, explotacion_id: int) -> models.Usuario | None:
    titular = db.scalar(
        select(models.Usuario).where(
            models.Usuario.explotacion_id == explotacion_id,
            models.Usuario.es_titular.is_(True),
        )
    )
    if titular is not None:
        return titular
    return db.scalar(
        select(models.Usuario).where(models.Usuario.explotacion_id == explotacion_id)
    )


@router.get("/certificado/estado")
def estado_del_certificado(request: Request) -> dict:
    """¿Se puede entrar con certificado aquí, y qué certificado se está viendo?

    Es lo que necesita la pantalla de entrada: si la instalación no está configurada, el
    botón no se enseña en vez de dar un error al pulsarlo.
    """
    certificado = certificados.certificado_de_peticion(request)
    return {
        "configurado": certificados.esta_configurado(),
        "hay_certificado": certificado is not None,
        "certificado": certificado.como_dict() if certificado else None,
        "si_no_se_puede": textos.CERTIFICADO["no_configurado"],
        "explicacion": textos.CERTIFICADO["vincular_explica"],
    }


@router.post("/entrar-con-certificado", response_model=TokenSalida)
def entrar_con_certificado(request: Request, db: Db) -> TokenSalida:
    """Entra sin teclear nada, usando el certificado de la conexión."""
    certificado = certificados.certificado_de_peticion(request)
    if certificado is None:
        # O no hay certificado, o la instalación no está configurada para creerse las
        # cabeceras. El mensaje es el mismo en los dos casos, y no revela nada.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=textos.CERTIFICADO["no_configurado"],
        )
    if not certificado.nif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=textos.CERTIFICADO["sin_nif"]
        )
    if not certificado.nif_valido:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=textos.CERTIFICADO["no_valido"].format(nif=certificado.nif),
        )

    explotacion = _explotacion_por_nif(db, certificado.nif)
    if explotacion is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=textos.CERTIFICADO["no_dado_de_alta"].format(nif=certificado.nif),
        )

    usuario = _usuario_titular(db, explotacion.id)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Esa cuenta no está activa."
        )

    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="sesion",
            entidad_id=usuario.id,
            accion="entrar_con_certificado",
            datos={"nif": certificado.nif, "nombre": certificado.nombre},
        )
    )
    db.commit()

    return TokenSalida(
        token=security.crear_token(usuario.id, explotacion.id),
        usuario_id=usuario.id,
        explotacion_id=explotacion.id,
        nombre=usuario.nombre,
    )


@router.post("/vincular-certificado")
def vincular_certificado(request: Request, usuario: UsuarioActual, db: Db) -> dict:
    """Ata el certificado a esta finca, para no volver a teclear nada.

    Se exige que el NIF coincida: vincular un certificado de otro NIF sería dejar que
    alguien entre en una finca que no es la suya.
    """
    certificado = certificados.certificado_de_peticion(request)
    if certificado is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=textos.CERTIFICADO["no_configurado"],
        )
    if not certificado.nif_valido:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.CERTIFICADO["no_valido"].format(nif=certificado.nif or "—"),
        )

    explotacion = db.get(models.Explotacion, usuario.explotacion_id)
    actual = certificados.normaliza_nif(explotacion.nif)
    if actual and actual != certificado.nif:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.CERTIFICADO["no_coincide"].format(
                nif=certificado.nif, de_la_finca=actual
            ),
        )

    explotacion.nif = certificado.nif
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="explotacion",
            entidad_id=explotacion.id,
            accion="vincular_certificado",
            datos={"nif": certificado.nif},
        )
    )
    db.commit()
    return {
        "vinculado": True,
        "nif": certificado.nif,
        "mensaje": textos.CERTIFICADO["vinculado"],
    }
