"""El plan de abono del año.

La app oficial lo llama «recomendación de nutrientes». Aquí se llama plan de abono,
porque es como lo llama el agricultor, y hace dos cosas:

1. **Guardar qué se piensa echar** y cuánto, por cultivo y por parcela.
2. **Compararlo con lo que de verdad se ha echado.** Esto es lo que de verdad sirve: un
   plan sin saber si se está cumpliendo es un papel guardado en un cajón.

Decisión: **un plan se puede corregir.** No es un apunte, es una previsión: si a mitad
de campaña cambia el tiempo o el precio del abono, el plan se ajusta y ya está. Lo que
no se toca nunca son los apuntes de abono que ya se han hecho, que esos sí son registro
obligatorio.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .. import correcciones, legal, models, servicios, textos, validaciones
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual, obtener_de_la_explotacion
from ..routers import analiticas_api
from ..schemas import PlanAbonadoEntrada, PlanAbonadoSalida, PlanConLoAplicado

router = APIRouter(prefix="/api", tags=["plan de abono"])


def _campana(db, explotacion, campana_id: int | None) -> models.Campana:
    if campana_id is not None:
        return obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    campana = db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion.id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )
    if campana is None:
        raise HTTPException(status_code=404, detail="Todavía no hay ningún año creado.")
    return campana


def _comprobar_analisis(db, explotacion, analitica_id: int | None) -> None:
    """Si el plan dice apoyarse en un análisis, ese análisis tiene que ser de esta finca.

    Sin esta comprobación, un identificador de otra finca se guardaría tal cual y el plan
    acabaría enseñando el análisis de otro agricultor. Es el mismo aislamiento que
    protege todo lo demás, aplicado a un campo que no es una clave foránea.
    """
    if analitica_id is None:
        return
    obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)


def _lo_aplicado(db, explotacion, plan) -> tuple[float, float, float, int]:
    """Lo que se ha echado contra este plan.

    Se cuenta **todo lo que se ha echado en la parcela del plan**, esté enlazado a él o
    no: nadie va a acordarse de enlazar cada abono a mano, y si solo contaran los
    enlazados, el aviso de pasarse no saltaría casi nunca. Lo que sí importa es que un
    apunte anulado no cuenta: lo que se anuló no se echó.
    """
    return servicios.lo_aplicado_contra_el_plan(
        db, explotacion_id=explotacion.id, plan=plan
    )


def _se_ha_pasado(plan, n: float, p: float, k: float) -> bool:
    """¿Se ha echado más de lo previsto, en cualquiera de los tres?

    La tolerancia de una milésima es para no avisar por redondeos de la propia cuenta.
    """
    parejas = (
        (plan.necesidad_n, n),
        (plan.necesidad_p, p),
        (plan.necesidad_k, k),
    )
    return any(necesidad and aplicado > necesidad * 1.001 for necesidad, aplicado in parejas)


def _mensaje(plan, n: float, p: float, k: float, apuntes: int) -> str:
    if plan.necesidad_n is None and plan.necesidad_p is None and plan.necesidad_k is None:
        return textos.PLAN["sin_necesidades"]
    if _se_ha_pasado(plan, n, p, k):
        return textos.PLAN["pasado"]
    if apuntes == 0:
        return textos.PLAN["sin_apuntes"]
    if apuntes == 1:
        return textos.PLAN["apuntes_uno"]
    return textos.PLAN["apuntes_varios"].format(cuantos=apuntes)


def _cultivo_precedente(db, explotacion, plan) -> str | None:
    """El cultivo del año anterior, que lo calcula `servicios` (una sola cuenta, un solo sitio).

    Aquí queda solo el nombre corto que usa el resto de este fichero: el cuaderno de la Junta
    escribe ese mismo dato en su hoja 9.1.2, y si cada uno lo calculara a su manera un día dirían
    cosas distintas.
    """
    return servicios.cultivo_precedente(db, explotacion, plan)


def _con_lo_aplicado(db, explotacion, plan) -> PlanConLoAplicado:
    n, p, k, apuntes = _lo_aplicado(db, explotacion, plan)
    # El análisis en el que se apoya el plan, si lo hay. Se resuelve aquí para que la
    # pantalla pueda enseñarlo sin una segunda llamada: en el campo, con mala cobertura,
    # una llamada de más es una pantalla en blanco.
    analisis = None
    if plan.analitica_id is not None:
        analitica = db.get(models.Analitica, plan.analitica_id)
        if analitica is not None and analitica.explotacion_id == explotacion.id:
            analisis = analiticas_api.con_sitio(db, analitica)
    return PlanConLoAplicado(
        **PlanAbonadoSalida.model_validate(plan).model_dump(),
        cultivo_precedente=_cultivo_precedente(db, explotacion, plan),
        aplicado_n=n,
        aplicado_p=p,
        aplicado_k=k,
        queda_n=round(plan.necesidad_n - n, 4) if plan.necesidad_n is not None else None,
        queda_p=round(plan.necesidad_p - p, 4) if plan.necesidad_p is not None else None,
        queda_k=round(plan.necesidad_k - k, 4) if plan.necesidad_k is not None else None,
        se_ha_pasado=_se_ha_pasado(plan, n, p, k),
        apuntes=apuntes,
        mensaje=_mensaje(plan, n, p, k, apuntes),
        analisis=analisis,
    )


def _rechazar_si_bloquea(avisos: list[validaciones.Aviso]) -> None:
    bloqueantes = [aviso for aviso in avisos if aviso.bloquea]
    if bloqueantes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "puede_guardarse": False,
                "avisos": [aviso.como_dict() for aviso in bloqueantes],
            },
        )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get("/planes", response_model=list[PlanConLoAplicado])
def listar_planes(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> list[PlanConLoAplicado]:
    consulta = select(models.PlanAbonado).where(
        models.PlanAbonado.explotacion_id == explotacion.id
    )
    if campana_id is not None:
        consulta = consulta.where(models.PlanAbonado.campana_id == campana_id)
    planes = list(db.scalars(consulta.order_by(models.PlanAbonado.cultivo)))
    return [_con_lo_aplicado(db, explotacion, plan) for plan in planes]


@router.post("/planes/validar")
def validar_plan_endpoint(datos: PlanAbonadoEntrada, _: ExplotacionActual) -> dict:
    """Pregunta qué le falta a un plan de abonado **antes** de guardarlo.

    **Pide sesión desde el 03/10/2026, y antes no la pedía.** Lo encontró la revisión de rutas
    sin sesión (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.18) y era una de las cuatro que
    **deberían** pedirla: su cuerpo lleva `campana_id`, `parcela_id` y `analitica_id`, que hoy no
    se usan porque `validaciones.validar_plan` es una función pura, pero es exactamente la clase
    de ruta que se convierte en un agujero el día que alguien consulte con esos identificadores.
    No rompe nada: la pantalla y el recorrido ya mandan su vale.
    """
    avisos = validaciones.validar_plan(datos=datos)
    return {
        "puede_guardarse": not validaciones.hay_bloqueo(avisos),
        "avisos": [aviso.como_dict() for aviso in avisos],
    }


@router.post("/planes", response_model=PlanAbonadoSalida, status_code=status.HTTP_201_CREATED)
def crear_plan(
    datos: PlanAbonadoEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> models.PlanAbonado:
    _rechazar_si_bloquea(validaciones.validar_plan(datos=datos))
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    _comprobar_analisis(db, explotacion, datos.analitica_id)

    plan = models.PlanAbonado(
        explotacion_id=explotacion.id,
        **datos.model_dump(exclude={"detalle"}),
        detalle=[abono.model_dump() for abono in datos.detalle],
    )
    db.add(plan)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="plan_abonado",
            accion="crear",
            datos={"cultivo": plan.cultivo, "superficie_ha": plan.superficie_ha},
        )
    )
    db.commit()
    return plan


@router.get("/planes/{plan_id}", response_model=PlanConLoAplicado)
def ver_plan(plan_id: int, explotacion: ExplotacionActual, db: Db) -> PlanConLoAplicado:
    plan = obtener_de_la_explotacion(db, models.PlanAbonado, plan_id, explotacion.id)
    return _con_lo_aplicado(db, explotacion, plan)


@router.put("/planes/{plan_id}", response_model=PlanAbonadoSalida)
def corregir_plan(
    plan_id: int,
    datos: PlanAbonadoEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> models.PlanAbonado:
    """Corrige el plan. Los abonos ya apuntados NO se tocan."""
    _rechazar_si_bloquea(validaciones.validar_plan(datos=datos))
    plan = obtener_de_la_explotacion(db, models.PlanAbonado, plan_id, explotacion.id)
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    _comprobar_analisis(db, explotacion, datos.analitica_id)

    for clave, valor in datos.model_dump(exclude={"detalle"}).items():
        setattr(plan, clave, valor)
    plan.detalle = [abono.model_dump() for abono in datos.detalle]
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="plan_abonado",
            entidad_id=plan.id,
            accion="corregir",
            datos={"cultivo": plan.cultivo, "necesidad_n": plan.necesidad_n},
        )
    )
    db.commit()
    return plan


@router.get("/planes/{plan_id}/resumen")
def resumen_del_plan(plan_id: int, explotacion: ExplotacionActual, db: Db) -> dict:
    """El plan y lo que llevas, en una tabla para poder mirarlo de un vistazo."""
    plan = obtener_de_la_explotacion(db, models.PlanAbonado, plan_id, explotacion.id)
    n, p, k, apuntes = _lo_aplicado(db, explotacion, plan)

    def fila(nombre: str, previsto, aplicado: float) -> dict:
        queda = round(previsto - aplicado, 4) if previsto is not None else None
        return {
            "nutriente": nombre,
            "previsto": previsto,
            "aplicado": aplicado,
            "queda": queda,
            "pasado": bool(previsto and aplicado > previsto * 1.001),
        }

    return {
        "plan_id": plan.id,
        "cultivo": plan.cultivo,
        "unidad": textos.PLAN["kilos_por_hectarea"],
        "filas": [
            fila("N", plan.necesidad_n, n),
            fila("P", plan.necesidad_p, p),
            fila("K", plan.necesidad_k, k),
        ],
        "apuntes": apuntes,
        "se_ha_pasado": _se_ha_pasado(plan, n, p, k),
        "mensaje": _mensaje(plan, n, p, k, apuntes),
    }


@router.delete("/planes/{plan_id}")
def borrar_plan(
    plan_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Quita el plan de abono del año, **si no tiene abonos apuntados contra él**.

    DECISIÓN, Y CONVIENE QUE QUEDE ESCRITA. Un plan es una previsión, así que se puede corregir
    (`PUT`, que ya existe) y también borrar: si el agricultor se ha equivocado de cultivo, de
    hectáreas o de año, lo que quiere es quitarlo de en medio, no quedarse con una previsión que no
    es la suya. Pero hay una cosa que no puede pasar: que los apuntes de abono **se queden sin decir
    contra qué plan se echaron**.

    Los apuntes de abono pueden enlazarse al plan (`RegistroFertilizacion.plan_id`), y eso es lo que
    contesta la pregunta que más se hace en una inspección: si lo que echaste estaba previsto o no.
    Si el plan desapareciera, esos apuntes seguirían teniendo su abono, su parcela y su cantidad
    —que es lo obligatorio— pero perderían la referencia a la previsión. Por eso, cuando hay abonos
    enlazados, se contesta 409 con **cuántos son** (`textos.B5_en_uso`, el mensaje genérico de «esto
    está en uso») y las dos salidas que hay de verdad: cambiar el plan de esos abonos (o borrarlos)
    antes, o **corregir el plan en vez de borrarlo**, que es lo que quiere la mayoría de las veces
    que alguien se equivoca.

    **Lo que NO se cuenta**, y también es una decisión: los abonos que se echaron en la parcela del
    plan **sin enlazarlo**. `servicios.lo_aplicado_contra_el_plan` los cuenta igual para avisar de
    que te has pasado —nadie se acuerda de enlazar cada abono a mano—, pero esos apuntes no dicen
    «este plan», así que borrar la previsión no les quita nada: siguen diciendo lo que de verdad
    pasó, que es lo que el cuaderno tiene que guardar.

    Al borrarlo queda en la auditoría el plan entero que había (el cultivo, las hectáreas, las
    necesidades, el análisis en el que se apoyaba y su reparto), con qué día se quitó.
    """
    plan = obtener_de_la_explotacion(db, models.PlanAbonado, plan_id, explotacion.id)

    abonos = correcciones.en_uso(
        db, explotacion_id=explotacion.id, columna="plan_id", valor=plan_id
    )
    if abonos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B5_en_uso", abonos),
        )

    correcciones.borrar(
        db,
        registro=plan,
        entidad="plan_abonado",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": plan_id}

