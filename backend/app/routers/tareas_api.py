"""Las próximas acciones, fuera de la ficha de un contacto (Entrega 3, 13/10/2026).

POR QUÉ ESTE FICHERO APARTE. En `contactos_api.py` vive lo que es de **una** ficha: apuntarle una tarea. Pero la
pregunta del agricultor casi nunca es «¿qué tengo con este contacto?», sino **«¿qué tengo que hacer hoy?»** — y eso
cruza contactos, hay que poder filtrarlo por responsable y por vencimiento, y hay que poder cerrar una tarea sin
entrar en la ficha de nadie.

LO QUE NO SE HACE AQUÍ, y es a propósito:

  · **No se manda ningún aviso ni se crea ningún mensaje.** Cerrar el programa no puede depender de que salga un
    correo: lo que hay es una lista que se mira, y eso es lo que se ha pedido. Un aviso automático que falle es peor
    que no tenerlo, porque el agricultor se fía.
  · **Vencida no se guarda**: se calcula al leer (`_una_tarea`), así que una tarea no cambia de estado porque pase
    la noche. Lo pide el encargo con estas palabras: *«la fecha vencida no transforma automáticamente una tarea en
    cancelada»*.
  · **Cerrar una tarea ya cerrada no hace nada**: ni cambia la fecha, ni deja otra traza. El agricultor toca dos
    veces con los guantes, y dos toques no pueden ser dos cierres.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from .. import correcciones, models, textos
from ..deps import Db, ExplotacionActual, UsuarioActual
from ..schemas import EntradaDeUnaTarea, ListaDeTareas
# El ayudante que cuenta una tarea (con lo que **se calcula**: `vencida` y la fecha dicha con palabras). Vive hoy en
# el router de contactos porque el primer sitio donde hizo falta fue la ficha; **cuando haya un tercer sitio que lo
# use, se mueve a un módulo suyo** —duplicarlo sería tener dos verdades sobre lo mismo, que es lo que no se hace—.
from .contactos_api import _una_tarea

router = APIRouter(prefix="/api/tareas", tags=["tareas"])


def _la_tarea_de_la_finca(db, explotacion_id: int, tarea_id: int) -> models.Tarea:
    """La tarea **de esa finca**, o 404. No se contesta «no es tuya»: eso ya diría que existe."""
    tarea = db.scalar(
        select(models.Tarea).where(
            models.Tarea.explotacion_id == explotacion_id,
            models.Tarea.id == tarea_id,
        )
    )
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=textos.mensaje("C7_no_existe"))
    return tarea


def _el_vencimiento_que_se_pide(vencimiento: str | None, hoy: dt.date):
    """Lo que significa cada vencimiento, **dicho en el servidor** y no en la pantalla.

    Se hace aquí por un motivo: la pantalla no tiene que saber qué es «vencida» —eso son cuentas y comparaciones de
    fechas, y de ahí salen las diferencias entre lo que dice un sitio y lo que dice otro—. El servidor decide, y la
    pantalla solo pinta.
    """
    if vencimiento == "vencidas":
        return models.Tarea.fecha_prevista.is_not(None), models.Tarea.fecha_prevista < hoy
    if vencimiento == "hoy":
        return models.Tarea.fecha_prevista.is_not(None), models.Tarea.fecha_prevista == hoy
    if vencimiento == "sin_fecha":
        return models.Tarea.fecha_prevista.is_(None), None
    # «todas» (o nada): sin filtro de fecha. Es lo que se enseña por defecto: esconder lo que no tiene fecha haría
    # que una tarea sin día **desapareciera** de la lista, que es como se pierden las cosas.
    return None, None


@router.get("", response_model=ListaDeTareas)
def las_tareas(
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    responsable: str | None = Query(default=None),
    estado: str | None = Query(default=None),
    vencimiento: str | None = Query(default=None),
    contacto_id: int | None = Query(default=None),
) -> dict:
    """**Lo que hay que hacer**, con los filtros del encargo: responsable, estado y vencimiento.

    El orden es el del trabajo: **lo pendiente antes que lo cerrado**, y dentro de lo pendiente **lo vencido arriba**
    (que es lo que se ha pasado de fecha), luego lo de hoy, luego lo que tiene día y por último **lo que no tiene
    fecha** — porque una tarea sin día no está «para ya», y ponerla arriba sería mentir con el orden.
    """
    hoy = dt.date.today()
    consulta = select(models.Tarea).where(models.Tarea.explotacion_id == explotacion.id)
    if responsable:
        consulta = consulta.where(models.Tarea.responsable == responsable)
    if estado:
        consulta = consulta.where(models.Tarea.estado == estado)
    if contacto_id:
        consulta = consulta.where(models.Tarea.contacto_id == contacto_id)
    tiene_fecha, condicion = _el_vencimiento_que_se_pide(vencimiento, hoy)
    if tiene_fecha is not None:
        consulta = consulta.where(tiene_fecha)
    if condicion is not None:
        consulta = consulta.where(condicion)

    suyas = list(db.scalars(consulta))
    suyas.sort(
        key=lambda t: (
            t.estado != models.Tarea.PENDIENTE,
            t.fecha_prevista is None,
            t.fecha_prevista or dt.date.max,
            t.id,
        )
    )
    return {"tareas": [_una_tarea(t, hoy) for t in suyas]}


@router.put("/{tarea_id}", response_model=ListaDeTareas)
def reprogramar_una_tarea(
    tarea_id: int,
    datos: EntradaDeUnaTarea,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Reprogramar**: cambiarle el día, el responsable o lo que hay que hacer.

    La corrección es **parcial**, como la de los canales: lo que no viene **no se toca**. Y si viene `fecha_prevista`
    vacía, la tarea se queda **sin fecha** —que es una decisión del agricultor, no un descuido—: por eso hay que
    mirar si el campo **viene** en la petición, y no si es nulo.
    """
    tarea = _la_tarea_de_la_finca(db, explotacion.id, tarea_id)
    antes = {"titulo": tarea.titulo, "responsable": tarea.responsable, "fecha": str(tarea.fecha_prevista or "")}
    enviados = datos.model_fields_set
    if "titulo" in enviados and datos.titulo.strip():
        tarea.titulo = datos.titulo.strip()
    if "descripcion" in enviados:
        tarea.descripcion = (datos.descripcion or "").strip() or None
    if "responsable" in enviados:
        tarea.responsable = (datos.responsable or "").strip() or None
    if "fecha_prevista" in enviados:
        tarea.fecha_prevista = datos.fecha_prevista
    tarea.clave_de_reenvio = None
    db.flush()
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="tarea",
        entidad_id=tarea.id,
        accion="tarea_reprogramar",
        datos={
            "titulo": [antes["titulo"], tarea.titulo],
            "responsable": [antes["responsable"], tarea.responsable],
            "fecha_prevista": [antes["fecha"], str(tarea.fecha_prevista or "")],
        },
    )
    db.commit()
    return {"tareas": [_una_tarea(tarea)]}


@router.post("/{tarea_id}/completar", response_model=ListaDeTareas)
def completar_una_tarea(
    tarea_id: int, db: Db, explotacion: ExplotacionActual, usuario: UsuarioActual
) -> dict:
    """**Completarla**, apuntando **quién y cuándo** (lo pide el encargo).

    Y **cerrar una que ya está cerrada no hace nada**: ni cambia la fecha, ni deja otra traza. Si ya estaba hecha, se
    devuelve como está —el agricultor toca dos veces con los guantes, y dos toques no pueden ser dos cierres—.
    """
    tarea = _la_tarea_de_la_finca(db, explotacion.id, tarea_id)
    if tarea.estado == models.Tarea.PENDIENTE:
        tarea.estado = models.Tarea.HECHA
        # La hora **local** del reloj, que es lo que pasó: aquí sí es un instante, y no se inventa.
        tarea.completada_en = dt.datetime.now()
        tarea.completada_por = usuario.nombre
        correcciones.apuntar(
            db,
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="tarea",
            entidad_id=tarea.id,
            accion="tarea_completar",
            datos={"estado": [models.Tarea.PENDIENTE, models.Tarea.HECHA], "por": [None, usuario.nombre]},
        )
        db.commit()
    return {"tareas": [_una_tarea(tarea)]}


@router.post("/{tarea_id}/cancelar", response_model=ListaDeTareas)
def cancelar_una_tarea(
    tarea_id: int, db: Db, explotacion: ExplotacionActual, usuario: UsuarioActual
) -> dict:
    """**Cancelarla**, que es distinto de hacerla: se apunta **quién y cuándo** y **no se borra**.

    Una tarea cancelada sigue ahí. Borrarla sería perder que existió y que alguien decidió que ya no hacía falta —
    que es exactamente lo que hay que poder mirar después—.
    """
    tarea = _la_tarea_de_la_finca(db, explotacion.id, tarea_id)
    if tarea.estado == models.Tarea.PENDIENTE:
        tarea.estado = models.Tarea.CANCELADA
        tarea.cancelada_en = dt.datetime.now()
        tarea.cancelada_por = usuario.nombre
        correcciones.apuntar(
            db,
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="tarea",
            entidad_id=tarea.id,
            accion="tarea_cancelar",
            datos={"estado": [models.Tarea.PENDIENTE, models.Tarea.CANCELADA], "por": [None, usuario.nombre]},
        )
        db.commit()
    return {"tareas": [_una_tarea(tarea)]}
