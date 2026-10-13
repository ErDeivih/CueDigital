"""Los servicios a terceros (CRM-04, 14/10/2026).

EL RECORRIDO, CON LAS PALABRAS DEL CONTRATO (`COLA.md:110`): *cliente → propuesta de trabajo → aceptación → parte
realizado → venta/documento → cobro*.

Y LAS CUATRO COSAS QUE ESTE CONTRATO PROTEGE, que son las que deciden cómo está escrito esto:

1. **Trabajo externo, con ubicación y superficie separadas de las tierras propias.** *10 ha de un tercero **no suman**
   superficie propia.* Por eso la ubicación y la hectárea viven en el trabajo y **nunca** se escriben en `parcelas`:
   si se escribieran, cualquier suma del agricultor —y el volcado de la PAC— contaría tierras que no son suyas.
2. **El insumo del cliente no descuenta almacén propio; el propio sí.** *2 L propios consumen; 2 L del cliente no.*
   Aquí se guarda **de quién es**, y quien descuente el almacén tiene que mirar esto antes de tocar nada.
3. **Cambiar la tarifa no reescribe partes aceptados anteriores.** Por eso **aceptar copia la tarifa** dentro del
   trabajo: el precio de un trabajo aceptado es el que se aceptó, no el que la casa tenga hoy en la lista.
4. **El plan no consume, y la ejecución repetida no duplica.** Lo primero es que **proponer y aceptar no tocan el
   almacén** (no se ha hecho nada todavía); lo segundo es la `clave_de_reenvio`, con su índice único.

Y EL COBRO **no se inventa aquí**: vive en el saldo del contacto, que es donde está el dinero de todos los documentos
de esta casa (ventas, facturas, cobros). *Cobro parcial exacto* sale de ahí, no de una cuenta paralela.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from .. import models, textos
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual
from app.deps import PuedeVerLoEconomico

router = APIRouter(prefix="/api/trabajos-a-terceros", tags=["trabajos a terceros"])


# ---------------------------------------------------------------------------
# Lo que se puede mandar
# ---------------------------------------------------------------------------


class LoQueSePropone(BaseModel):
    """Una propuesta de trabajo para un tercero. **Todavía no se ha hecho nada**: es una oferta."""

    contacto_id: int
    titulo: str = Field(min_length=1, max_length=200)
    ubicacion: str | None = None
    superficie_ha: Decimal | None = None
    de_quien_es_el_insumo: str = "propio"
    tarifa_por_hora: Decimal | None = None
    horas_previstas: Decimal | None = None
    notas: str | None = None
    # **La clave de reenvío**: apuntar dos veces lo mismo (un doble clic, la cola del móvil) no puede duplicarlo.
    clave_de_reenvio: str | None = None


class LoQueSeAcepta(BaseModel):
    """La aceptación. **Y aquí se copia la tarifa**, que es lo que el contrato protege."""

    tarifa_aceptada: Decimal | None = None


class ElParteDeLoHecho(BaseModel):
    """El parte: lo que de verdad se hizo. Se copian las horas, la máquina, el operario y el desplazamiento."""

    horas_hechas: Decimal | None = None
    maquina: str | None = None
    operario: str | None = None
    desplazamiento_km: Decimal | None = None
    hecho_en: dt.date | None = None
    # **El coste puede no saberse**, y entonces se queda vacío: el contrato pide que el margen **marque** los costes
    # desconocidos, así que un cero aquí sería mentir.
    coste_conocido: Decimal | None = None
    clave_de_reenvio: str | None = None


# ---------------------------------------------------------------------------
# Los ayudantes
# ---------------------------------------------------------------------------


def _suyo(db: Db, explotacion_id: int, trabajo_id: int) -> models.TrabajoParaUnTercero:
    """El trabajo, **comprobando que es de esta finca**. 404 y no 403, como en el resto: así no se puede ni saber
    que existe el de otro."""
    trabajo = db.scalar(
        select(models.TrabajoParaUnTercero).where(
            models.TrabajoParaUnTercero.id == trabajo_id,
            models.TrabajoParaUnTercero.explotacion_id == explotacion_id,
        )
    )
    if trabajo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=textos.mensaje("C7_no_existe"))
    return trabajo


def _el_cliente(db: Db, explotacion_id: int, contacto_id: int) -> models.Contacto:
    cliente = db.scalar(
        select(models.Contacto).where(
            models.Contacto.id == contacto_id,
            models.Contacto.explotacion_id == explotacion_id,
        )
    )
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ese cliente no está en tu cuaderno.",
        )
    return cliente


def _lo_que_se_ve(trabajo: models.TrabajoParaUnTercero, cliente: models.Contacto) -> dict:
    return {
        "id": trabajo.id,
        "estado": trabajo.estado,
        "titulo": trabajo.titulo,
        "cliente": {"id": cliente.id, "nombre": cliente.nombre},
        "ubicacion": trabajo.ubicacion,
        "superficie_ha": trabajo.superficie_ha,
        "de_quien_es_el_insumo": trabajo.de_quien_es_el_insumo,
        "tarifa_por_hora": trabajo.tarifa_por_hora,
        "horas_previstas": trabajo.horas_previstas,
        "aceptado_en": trabajo.aceptado_en,
        # **La tarifa ACEPTADA es la que vale**, y se enseña aparte de la de la lista para que se vea la diferencia
        # cuando la casa sube precios: lo aceptado no se reescribe.
        "tarifa_aceptada": trabajo.tarifa_aceptada,
        "horas_hechas": trabajo.horas_hechas,
        "maquina": trabajo.maquina,
        "operario": trabajo.operario,
        "desplazamiento_km": trabajo.desplazamiento_km,
        "coste_conocido": trabajo.coste_conocido,
        # **Y si no consta, se dice.** El contrato: el margen tiene que **marcar** los costes desconocidos.
        "coste_conocido_o_no": trabajo.coste_conocido is not None,
        "hecho_en": trabajo.hecho_en,
        "notas": trabajo.notas,
    }


# ---------------------------------------------------------------------------
# Las puertas
# ---------------------------------------------------------------------------


@router.get("")
def la_lista(db: Db, explotacion: ExplotacionActual) -> dict:
    """Los trabajos para terceros de esta finca, con su cliente y su estado."""
    trabajos = list(
        db.scalars(
            select(models.TrabajoParaUnTercero)
            .where(models.TrabajoParaUnTercero.explotacion_id == explotacion.id)
            .order_by(models.TrabajoParaUnTercero.id.desc())
        )
    )
    clientes = {
        contacto.id: contacto
        for contacto in db.scalars(
            select(models.Contacto).where(models.Contacto.explotacion_id == explotacion.id)
        )
    }
    return {"trabajos": [_lo_que_se_ve(t, clientes[t.contacto_id]) for t in trabajos if t.contacto_id in clientes]}


@router.post("", status_code=status.HTTP_201_CREATED)
def proponer(
    datos: LoQueSePropone,
    db: Db,
    explotacion: ExplotacionActual,
    poder: PuedeModificar,
) -> dict:
    """**Propone** un trabajo. No se ha hecho nada, así que no toca el almacén ni la superficie propia.

    Y si viene con `clave_de_reenvio` y esa clave ya está, **devuelve la que había** en vez de apuntar otra: lo mismo
    que hace el resto de la casa (`uq_trabajo_a_tercero_reenvio`).
    """
    if datos.de_quien_es_el_insumo not in ("propio", "cliente"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El insumo es tuyo o del cliente: no hay otra posibilidad.",
        )
    cliente = _el_cliente(db, explotacion.id, datos.contacto_id)

    if datos.clave_de_reenvio:
        ya = db.scalar(
            select(models.TrabajoParaUnTercero).where(
                models.TrabajoParaUnTercero.explotacion_id == explotacion.id,
                models.TrabajoParaUnTercero.clave_de_reenvio == datos.clave_de_reenvio,
            )
        )
        if ya is not None:
            return _lo_que_se_ve(ya, cliente)

    trabajo = models.TrabajoParaUnTercero(
        explotacion_id=explotacion.id,
        contacto_id=cliente.id,
        estado=models.TrabajoParaUnTercero.PROPUESTO,
        titulo=datos.titulo,
        ubicacion=datos.ubicacion,
        superficie_ha=datos.superficie_ha,
        de_quien_es_el_insumo=datos.de_quien_es_el_insumo,
        tarifa_por_hora=datos.tarifa_por_hora,
        horas_previstas=datos.horas_previstas,
        notas=datos.notas,
        clave_de_reenvio=datos.clave_de_reenvio,
    )
    db.add(trabajo)
    db.commit()
    db.refresh(trabajo)
    return _lo_que_se_ve(trabajo, cliente)


@router.post("/{trabajo_id}/aceptar")
def aceptar(
    trabajo_id: int,
    datos: LoQueSeAcepta,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    poder: PuedeModificar,
) -> dict:
    """**Acepta** el trabajo, y **copia la tarifa dentro**. A partir de aquí, subir la tarifa de la casa no cambia
    este trabajo: *el precio de lo aceptado es el que se aceptó*.

    Y **aceptar no consume almacén**: todavía no se ha hecho el trabajo. Lo pide el contrato: *«plan no consume»*.
    """
    trabajo = _suyo(db, explotacion.id, trabajo_id)
    if trabajo.estado != models.TrabajoParaUnTercero.PROPUESTO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ese trabajo ya está {trabajo.estado}: aceptarlo otra vez no cambia nada.",
        )
    # **La copia**: si no dicen tarifa, se copia la que se propuso; y si tampoco hay, se queda vacía y se dice.
    trabajo.tarifa_aceptada = datos.tarifa_aceptada if datos.tarifa_aceptada is not None else trabajo.tarifa_por_hora
    trabajo.estado = models.TrabajoParaUnTercero.ACEPTADO
    trabajo.aceptado_en = dt.datetime.now(dt.UTC)
    trabajo.aceptado_por = usuario.id
    db.commit()
    db.refresh(trabajo)
    return _lo_que_se_ve(trabajo, _el_cliente(db, explotacion.id, trabajo.contacto_id))


@router.post("/{trabajo_id}/parte")
def apuntar_el_parte(
    trabajo_id: int,
    datos: ElParteDeLoHecho,
    db: Db,
    explotacion: ExplotacionActual,
    poder: PuedeModificar,
) -> dict:
    """**El parte de lo hecho.** Y solo se apunta sobre lo aceptado: un parte de algo que nadie aceptó es un trabajo
    que no se ha pedido.

    **El almacén se descuenta aquí, y solo si el insumo es propio.** Lo del cliente no toca el almacén del
    agricultor: *2 L propios consumen; 2 L del cliente no*. (Lo que se descuenta de verdad lo hará el movimiento de
    almacén, que es de otro módulo; aquí se deja dicho **de quién era**, que es lo que hace falta para hacerlo bien.)
    """
    trabajo = _suyo(db, explotacion.id, trabajo_id)
    if trabajo.estado != models.TrabajoParaUnTercero.ACEPTADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Solo se le puede apuntar el parte a un trabajo aceptado, y este está {trabajo.estado}.",
        )
    trabajo.horas_hechas = datos.horas_hechas
    trabajo.maquina = datos.maquina
    trabajo.operario = datos.operario
    trabajo.desplazamiento_km = datos.desplazamiento_km
    trabajo.hecho_en = datos.hecho_en or dt.date.today()
    trabajo.coste_conocido = datos.coste_conocido
    if datos.clave_de_reenvio:
        trabajo.clave_de_reenvio = datos.clave_de_reenvio
    trabajo.estado = models.TrabajoParaUnTercero.HECHO
    db.commit()
    db.refresh(trabajo)
    respuesta = _lo_que_se_ve(trabajo, _el_cliente(db, explotacion.id, trabajo.contacto_id))
    # **Y se dice, con todas las letras, qué pasa con el almacén.** Que no se descuente lo del cliente no puede ser
    # algo que alguien tenga que deducir.
    respuesta["almacen"] = (
        "el insumo es TUYO: este trabajo sí descuenta de tu almacén"
        if trabajo.de_quien_es_el_insumo == "propio"
        else "el insumo es DEL CLIENTE: este trabajo NO toca tu almacén"
    )
    return respuesta


@router.post("/{trabajo_id}/cancelar")
def cancelar(
    trabajo_id: int,
    db: Db,
    explotacion: ExplotacionActual,
    poder: PuedeModificar,
) -> dict:
    """Se cancela lo que no se ha hecho. **Lo ya hecho no se cancela**: eso sería borrar un parte."""
    trabajo = _suyo(db, explotacion.id, trabajo_id)
    if trabajo.estado == models.TrabajoParaUnTercero.HECHO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese trabajo ya se hizo: un parte hecho no se cancela.",
        )
    trabajo.estado = models.TrabajoParaUnTercero.CANCELADO
    db.commit()
    db.refresh(trabajo)
    return _lo_que_se_ve(trabajo, _el_cliente(db, explotacion.id, trabajo.contacto_id))


# ---------------------------------------------------------------------------
# EL MARGEN DE UN TRABAJO A UN TERCERO
# ---------------------------------------------------------------------------

@router.get("/{trabajo_id}/margen")
def el_margen_del_trabajo(
    trabajo_id: int,
    db: Db,
    usuario: UsuarioActual,
    explotacion: ExplotacionActual,
    _: PuedeVerLoEconomico,
):
    """**Lo facturado, lo que costó y lo que queda** (CRM-04, 14/10/2026).

    POR QUÉ ESTA PUERTA. El contrato del ticket pide *«margen marca costes desconocidos»*. El parte ya apunta
    `coste_conocido` y ya avisa con `coste_conocido_o_no`, pero **no había margen**: el inventario del CRM-05
    lo encontró medido (`terceros_api.py:266` escribe el coste; no había nada que lo comparara con el ingreso).
    Y un margen que trata un coste que no consta como un cero **miente**: diría que un trabajo sin coste
    apuntado es todo beneficio.

    CÓMO SE ENLAZA EL INGRESO, SIN ADJUDICAR NADA A OJO. **Por la `clave_de_reenvio`**: es la llave que este
    proyecto usa para decir «esto y aquello son el mismo asunto», y el trabajo a un tercero **ya la lleva**
    (`uq_trabajo_a_tercero_reenvio`). Así **no** se adjudica un documento «por coincidencia de nombres», que es
    lo que el encargo prohíbe: se adjudica por la clave que el agricultor escribió.

    Y las dos banderas van separadas, porque son **dos** incógnitas distintas: `coste_conocido_o_no` y
    `facturado_o_no`. Si falta cualquiera de las dos, **el margen NO se calcula** — se dice que no consta.
    """
    trabajo = _suyo(db, explotacion.id, trabajo_id)

    # **Lo facturado**: las ventas y las facturas emitidas de ESTA finca con la misma clave. Se pide el importe
    # de cada una y se suman aparte, para poder decir **cuántos documentos** lo sostienen (la cobertura).
    facturado = Decimal("0")
    documentos = 0
    if trabajo.clave_de_reenvio:
        for modelo, columna in (
            (models.VentaDeCosecha, models.VentaDeCosecha.importe),
            (models.FacturaEmitida, models.FacturaEmitida.importe_total),
        ):
            filas = db.execute(
                select(columna).where(
                    modelo.explotacion_id == explotacion.id,
                    modelo.clave_de_reenvio == trabajo.clave_de_reenvio,
                )
            ).scalars().all()
            for importe in filas:
                if importe is not None:
                    facturado += Decimal(str(importe))
                    documentos += 1

    coste = trabajo.coste_conocido
    hay_facturado = bool(trabajo.clave_de_reenvio) and documentos > 0
    hay_coste = coste is not None
    return {
        "trabajo_id": trabajo.id,
        "clave_de_reenvio": trabajo.clave_de_reenvio,
        # **Lo que se sabe**, con sus dos banderas.
        "facturado": facturado if hay_facturado else None,
        "facturado_o_no": hay_facturado,
        "coste_conocido": coste,
        "coste_conocido_o_no": hay_coste,
        "documentos": documentos,
        # **Y el margen, solo si las dos están.** Si falta una, `None` y el porqué en la bandera: es la
        # diferencia entre «no lo sé» y «cero», que es lo que el contrato pide en todo el módulo.
        "margen": (facturado - Decimal(str(coste))) if (hay_facturado and hay_coste) else None,
        "sin_clave_de_reenvio": not bool(trabajo.clave_de_reenvio),
    }
