"""El registro obligatorio: tratamientos, abonos, labores y cosecha.

Este es el corazón del programa. Las dos secciones que pasan a ser obligatorias son:
  - fitosanitarios -> registro electrónico obligatorio desde el 01/01/2027
  - fertilización  -> obligatorio desde el 01/01/2026

Decisión: hay un endpoint `/validar` que hace exactamente las mismas comprobaciones
que el de guardar, pero sin escribir nada. Es lo que permite que la interfaz avise
al agricultor ANTES de que pulse guardar, en vez de regañarle después. Un aviso que
llega antes se arregla; uno que llega después hace que se abandone.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .. import catalogos, correcciones, legal, models, servicios, textos, validaciones
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AnulacionEntrada,
    AvisoSalida,
    CosechaEntrada,
    FertilizacionEntrada,
    FertilizacionSalida,
    LaborEntrada,
    LaborSalida,
    ResultadoValidacion,
    TratamientoEntrada,
    TratamientoSalida,
)

router = APIRouter(prefix="/api", tags=["registro"])


# --------------------------------------------------------------------------
# Utilidades internas
# --------------------------------------------------------------------------


def _cargar(db, explotacion, modelo, objeto_id):
    if objeto_id is None:
        return None
    return obtener_de_la_explotacion(db, modelo, objeto_id, explotacion.id)


def _grupo(db, explotacion, grupo_id):
    """La unidad homogénea de cultivo, cuando el apunte es de varias parcelas a la vez.

    Hace falta traerla entera (con sus parcelas) porque la comprobación de la superficie se hace
    contra la suma de todas ellas. Ver `validaciones._superficie_del_grupo`.
    """
    return _cargar(db, explotacion, models.GrupoParcelas, grupo_id)


def _periodo_cultivo(db, explotacion, parcela_id, campana_id):
    if parcela_id is None:
        return None
    cultivo = db.scalar(
        select(models.ParcelaCultivo).where(
            models.ParcelaCultivo.explotacion_id == explotacion.id,
            models.ParcelaCultivo.parcela_id == parcela_id,
            models.ParcelaCultivo.campana_id == campana_id,
        )
    )
    if cultivo is None:
        return None
    return (cultivo.fecha_inicio, cultivo.fecha_fin)


def _rechazar_si_bloquea(avisos: list[validaciones.Aviso]) -> None:
    """Si algo bloquea, se devuelve 422 con TODOS los avisos, ya redactados."""
    bloqueantes = [aviso for aviso in avisos if aviso.bloquea]
    if bloqueantes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "puede_guardarse": False,
                "avisos": [aviso.como_dict() for aviso in bloqueantes],
            },
        )


def _resultado(avisos: list[validaciones.Aviso]) -> ResultadoValidacion:
    return ResultadoValidacion(
        puede_guardarse=not validaciones.hay_bloqueo(avisos),
        avisos=[AvisoSalida(**aviso.como_dict()) for aviso in avisos],
    )


def _anular(db, explotacion, registro, motivo: str, entidad: str) -> None:
    """Nada se borra: se anula con un motivo y queda el rastro."""
    registro.anulado = True
    registro.motivo_anulacion = motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad=entidad,
            entidad_id=registro.id,
            accion="anular",
            datos={"motivo": motivo},
        )
    )
    db.commit()


def _no_se_borra_si_esta_firmado(db, explotacion, entidad: str, entidad_id: int) -> None:
    """Un apunte firmado no se borra: se dice y se ofrece anularlo.

    La firma es la prueba de lo que había apuntado en un momento dado. Borrar el apunte dejaría la
    firma apuntando a algo que ya no existe, y eso es peor que no tener firma: parecería que el
    cuaderno está respaldado cuando no lo está. Ver `correcciones.py`.
    """
    if correcciones.firmas_de_un_apunte(
        db, explotacion_id=explotacion.id, entidad=entidad, entidad_id=entidad_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("B1_firmado_no_se_borra"),
        )


# --------------------------------------------------------------------------
# Tratamientos
# --------------------------------------------------------------------------


def _contexto_tratamiento(datos: TratamientoEntrada, explotacion, db):
    campana = obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    parcela = _cargar(db, explotacion, models.Parcela, datos.parcela_id)
    producto = _cargar(db, explotacion, models.ProductoFitosanitario, datos.producto_id)
    aplicador = _cargar(db, explotacion, models.Aplicador, datos.aplicador_id)
    equipo = _cargar(db, explotacion, models.EquipoAplicacion, datos.equipo_id)
    instalacion = _cargar(db, explotacion, models.Instalacion, datos.instalacion_id)
    asesor = _cargar(db, explotacion, models.Asesor, datos.asesor_id)
    periodo = _periodo_cultivo(db, explotacion, datos.parcela_id, campana.id)
    return campana, parcela, producto, aplicador, equipo, instalacion, periodo, asesor


def _avisos_tratamiento(datos: TratamientoEntrada, explotacion, db) -> list[validaciones.Aviso]:
    (
        _campana,
        parcela,
        producto,
        aplicador,
        equipo,
        instalacion,
        periodo,
        asesor,
    ) = _contexto_tratamiento(datos, explotacion, db)
    # Las medidas preventivas de la finca solo se miran cuando el producto va sobre la
    # tierra: un tratamiento de una nave o del grano ya recogido no tiene nada que ver con
    # la gestión integrada de plagas del cultivo.
    #
    # Se cuenta como «declarado» en cuanto hay filas, aunque el agricultor haya dicho que
    # no hace ninguna: lo que el aviso persigue es que la sección esté rellenada, no que
    # la respuesta sea «sí». Volver a pedírselo en cada apunte sería no escucharle.
    hay_medidas: bool | None = None
    if datos.tipo in catalogos.TRATAMIENTO_EN_PARCELA:
        hay_medidas = bool(
            servicios.medidas_declaradas(db, explotacion_id=explotacion.id)
        )
    return validaciones.validar_tratamiento(
        datos=datos,
        parcela=parcela,
        producto=producto,
        aplicador=aplicador,
        equipo=equipo,
        instalacion=instalacion,
        explotacion=explotacion,
        periodo_cultivo=periodo,
        hay_medidas_declaradas=hay_medidas,
        asesor=asesor,
        grupo=_grupo(db, explotacion, getattr(datos, "grupo_id", None)),
    )


@router.post("/tratamientos/validar", response_model=ResultadoValidacion)
def validar_tratamiento_endpoint(
    datos: TratamientoEntrada, explotacion: ExplotacionActual, db: Db
) -> ResultadoValidacion:
    """Comprueba un tratamiento sin guardarlo. La interfaz lo llama mientras se rellena."""
    return _resultado(_avisos_tratamiento(datos, explotacion, db))


def _preparar_tratamiento_guardable(datos: TratamientoEntrada, explotacion, db):
    """Comprueba un tratamiento y devuelve el registro listo para guardar, sin guardarlo.

    Lo usan el alta y la corrección, y **es a propósito**: las dos tienen que pasar por las mismas
    comprobaciones y las mismas cuentas (el plazo de seguridad, el cultivo que el agricultor ya
    declaró, la superficie). Si la corrección copiara lo que manda el navegador sin más, un apunte
    corregido podría quedar con números que el alta no habría aceptado nunca.
    """
    avisos = _avisos_tratamiento(datos, explotacion, db)
    _rechazar_si_bloquea(avisos)

    _campana, parcela, producto, _aplicador, _equipo, _instalacion, _periodo, _asesor = (
        _contexto_tratamiento(datos, explotacion, db)
    )
    # El cultivo que el agricultor ya dijo que hay en esa parcela este año. La app oficial lo
    # llama «campo calculado»: no se pregunta en cada apunte. Sin esto, el campo «Cultivo» de
    # todos los tratamientos se quedaba vacío y el volcado oficial lo mandaba en blanco.
    declarado = servicios.cultivo_declarado(
        db,
        explotacion_id=explotacion.id,
        parcela_id=datos.parcela_id,
        campana_id=datos.campana_id,
    )
    return servicios.preparar_tratamiento(
        datos,
        explotacion_id=explotacion.id,
        producto=producto,
        parcela=parcela,
        cultivo_declarado=declarado.especie if declarado else None,
    )


@router.post("/tratamientos", response_model=TratamientoSalida, status_code=status.HTTP_201_CREATED)
def crear_tratamiento(
    datos: TratamientoEntrada,
    explotacion: ExplotacionActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> models.TratamientoFitosanitario:
    tratamiento = _preparar_tratamiento_guardable(datos, explotacion, db)
    db.add(tratamiento)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="tratamiento",
            entidad_id=tratamiento.id,
            accion="crear",
            datos={"fecha": str(tratamiento.fecha), "producto": tratamiento.producto_nombre},
        )
    )
    db.commit()
    # ***Y con su version*** (CRM-08, 17/10/2026): el formulario la necesita para **mandarla de vuelta** al
    # corregir, y sin ella no hay edicion concurrente que valga.
    #
    # ***Un apunte recien creado YA tiene historia*** -el alta deja su fila de auditoria-, asi que su version
    # no es cero: es la de su alta. *Y por eso la prueba que suponia un cero estaba mal, no el codigo.*
    return TratamientoSalida.model_validate(tratamiento).model_copy(
        update={
            "version": correcciones.la_version_de(
                db, entidad="tratamiento", entidad_id=tratamiento.id
            )
        }
    )


@router.get("/tratamientos", response_model=list[TratamientoSalida])
def listar_tratamientos(
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    parcela_id: int | None = None,
    incluir_anulados: bool = False,
) -> list[models.TratamientoFitosanitario]:
    consulta = select(models.TratamientoFitosanitario).where(
        models.TratamientoFitosanitario.explotacion_id == explotacion.id
    )
    if campana_id is not None:
        consulta = consulta.where(models.TratamientoFitosanitario.campana_id == campana_id)
    if parcela_id is not None:
        consulta = consulta.where(models.TratamientoFitosanitario.parcela_id == parcela_id)
    if not incluir_anulados:
        consulta = consulta.where(models.TratamientoFitosanitario.anulado.is_(False))
    return list(db.scalars(consulta.order_by(models.TratamientoFitosanitario.fecha.desc())))


@router.get("/tratamientos/{tratamiento_id}", response_model=TratamientoSalida)
def ver_tratamiento(
    tratamiento_id: int, explotacion: ExplotacionActual, db: Db
) -> models.TratamientoFitosanitario:
    return obtener_de_la_explotacion(
        db, models.TratamientoFitosanitario, tratamiento_id, explotacion.id
    )


@router.post("/tratamientos/{tratamiento_id}/anular")
def anular_tratamiento(
    tratamiento_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    tratamiento = obtener_de_la_explotacion(
        db, models.TratamientoFitosanitario, tratamiento_id, explotacion.id
    )
    _anular(db, explotacion, tratamiento, datos.motivo, "tratamiento")
    return {"anulado": True, "motivo": datos.motivo}


@router.put("/tratamientos/{tratamiento_id}", response_model=TratamientoSalida)
def corregir_tratamiento(
    tratamiento_id: int,
    datos: TratamientoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> models.TratamientoFitosanitario:
    """Corrige un tratamiento ya apuntado. **No borra y no duplica: cambia ese apunte.**

    POR QUÉ SE CORRIGE EN EL SITIO Y NO CREANDO OTRO. Porque el identificador que viaja a la Junta
    de cada actividad (`IdAjena`) es el `id` de esta fila (ver `iuws_mapeo`): si en vez de corregir
    se creara otro apunte, la Junta tendría los dos —el malo y el bueno— y el cuaderno diría que se
    trató dos veces. Corrigiendo aquí, la actividad sigue siendo la misma y con los datos buenos.

    Y lo que había antes **no se pierde**: queda en la auditoría, campo por campo (`correcciones`).
    """
    tratamiento = obtener_de_la_explotacion(
        db, models.TratamientoFitosanitario, tratamiento_id, explotacion.id
    )
    preparado = _preparar_tratamiento_guardable(datos, explotacion, db)
    # ***El piloto de la edicion concurrente*** (CRM-08, 17/10/2026). Si el formulario dice **que version
    # tenia** y el apunte ha cambiado desde entonces, `corregir` levanta `VersionQueNoCuadra` **sin escribir
    # nada**, y aqui se contesta **409** diciendo quien lo cambio. *«No ultimo escritor silencioso»*.
    try:
        correcciones.corregir(
            db,
            guardado=tratamiento,
            preparado=preparado,
            entidad="tratamiento",
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            version_esperada=getattr(datos, "version_esperada", None),
        )
    except correcciones.VersionQueNoCuadra as choque:
        raise HTTPException(
            status_code=409, detail=correcciones.el_conflicto_del_apunte(choque)
        ) from choque
    # ***Y con su version*** (CRM-08, 17/10/2026): el formulario la necesita para **mandarla de vuelta** al
    # corregir, y sin ella no hay edicion concurrente que valga.
    #
    # ***Un apunte recien creado YA tiene historia*** -el alta deja su fila de auditoria-, asi que su version
    # no es cero: es la de su alta. *Y por eso la prueba que suponia un cero estaba mal, no el codigo.*
    return TratamientoSalida.model_validate(tratamiento).model_copy(
        update={
            "version": correcciones.la_version_de(
                db, entidad="tratamiento", entidad_id=tratamiento.id
            )
        }
    )


@router.delete("/tratamientos/{tratamiento_id}")
def borrar_tratamiento(
    tratamiento_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    """Quita un tratamiento del cuaderno. Se puede deshacer lo que uno se ha equivocado.

    Lo que había queda escrito en la auditoría, así que el programa **sabe** que existió y se
    borró, aunque el cuaderno ya no lo enseñe. Lo que no se puede borrar es un apunte firmado.
    """
    tratamiento = obtener_de_la_explotacion(
        db, models.TratamientoFitosanitario, tratamiento_id, explotacion.id
    )
    _no_se_borra_si_esta_firmado(db, explotacion, "tratamiento", tratamiento_id)
    correcciones.borrar(
        db,
        registro=tratamiento,
        entidad="tratamiento",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": tratamiento_id}


# --------------------------------------------------------------------------
# Fertilización
# --------------------------------------------------------------------------


def _contexto_fertilizacion(datos: FertilizacionEntrada, explotacion, db):
    campana = obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    parcela = _cargar(db, explotacion, models.Parcela, datos.parcela_id)
    fertilizante = _cargar(db, explotacion, models.Fertilizante, datos.fertilizante_id)
    # El plan con el que hay que comparar: el que diga el agricultor, o el de esa parcela
    # y esa campaña. Nadie se acuerda de enlazar cada abono a mano.
    plan = servicios.plan_que_le_toca(
        db,
        explotacion_id=explotacion.id,
        campana_id=datos.campana_id,
        parcela_id=datos.parcela_id,
        plan_id=datos.plan_id,
    )
    return campana, parcela, fertilizante, plan


def _avisos_fertilizacion(datos: FertilizacionEntrada, explotacion, db) -> list[validaciones.Aviso]:
    _campana, parcela, fertilizante, plan = _contexto_fertilizacion(datos, explotacion, db)
    grupo = _grupo(db, explotacion, getattr(datos, "grupo_id", None))
    aplicado_n_ha = servicios.lo_aplicado_contra_el_plan(
        db, explotacion_id=explotacion.id, plan=plan
    )[0]
    # El nitrógeno que ya se ha echado como estiércol o purín en esa parcela este año: es lo que
    # hace falta para comprobar la regla de los 170 kg de la Orden MAV/398/2022.
    #
    # Las dos llamadas devuelven algo más que un número, y es a propósito: lo que se apuntó en un
    # grupo del que no se puede saber qué tierra lo recibió y lo que se apuntó sin composición
    # **no son ceros**, son huecos, y hay que poder decírselo al agricultor (A4 y A6 de
    # `docs/T02_VALORES_POR_DEFECTO.md`).
    organico = servicios.nitrogeno_organico_en_la_parcela(
        db,
        explotacion_id=explotacion.id,
        parcela_id=datos.parcela_id,
        campana_id=datos.campana_id,
    )
    total = servicios.nitrogeno_aplicado_en_la_parcela(
        db,
        explotacion_id=explotacion.id,
        parcela_id=datos.parcela_id,
        campana_id=datos.campana_id,
    )
    cultivo = servicios.cultivo_declarado(
        db,
        explotacion_id=explotacion.id,
        parcela_id=datos.parcela_id,
        campana_id=datos.campana_id,
    )
    # **Un abono de un grupo se comprueba tierra por tierra** (A4): el tope de los 170 kg es por
    # tierra y por año, así que se cuenta lo que ya llevaba cada una y se mira si con esta dosis se
    # pasa. Sin esto, quien abona siempre por grupo no vería el aviso nunca, porque al no haber una
    # tierra concreta no había contra qué comparar.
    tierras_del_grupo = None
    if datos.parcela_id is None and grupo is not None:
        tierras_del_grupo = []
        for tierra in grupo.parcelas:
            suyo = servicios.nitrogeno_organico_en_la_parcela(
                db,
                explotacion_id=explotacion.id,
                parcela_id=tierra.id,
                campana_id=datos.campana_id,
            )
            tierras_del_grupo.append(
                {
                    "alias": tierra.alias,
                    "en_zona": tierra.zona_vulnerable_nitratos,
                    "kg_n_ha": suyo.kg_n_ha,
                    "sin_atribuir": suyo.sin_atribuir,
                    "sin_composicion": suyo.sin_composicion,
                }
            )
    return validaciones.validar_fertilizacion(
        datos=datos,
        parcela=parcela,
        fertilizante=fertilizante,
        plan=plan,
        aplicado_n_ha=aplicado_n_ha,
        organico_n_ha=organico.kg_n_ha,
        total_n_ha=total.kg_n_ha,
        cultivo=cultivo,
        grupo=grupo,
        aportes_por_grupo_sin_comprobar=(
            organico.sin_atribuir
            if tierras_del_grupo is None
            else max([tierra["sin_atribuir"] for tierra in tierras_del_grupo] or [0])
        ),
        apuntes_ya_sin_composicion=(
            total.sin_composicion
            if tierras_del_grupo is None
            else sum(tierra["sin_composicion"] for tierra in tierras_del_grupo)
        ),
        tierras_del_grupo=tierras_del_grupo,
    )


@router.post("/fertilizaciones/validar", response_model=ResultadoValidacion)
def validar_fertilizacion_endpoint(
    datos: FertilizacionEntrada, explotacion: ExplotacionActual, db: Db
) -> ResultadoValidacion:
    return _resultado(_avisos_fertilizacion(datos, explotacion, db))


def _preparar_fertilizacion_guardable(datos: FertilizacionEntrada, explotacion, db):
    """Comprueba un abono y devuelve el registro listo para guardar, sin guardarlo.

    Como en los tratamientos, lo usan el alta y la corrección: un abono corregido pasa por las
    mismas reglas que uno nuevo (la superficie de la parcela, el tope de nitrógeno de la zona, el
    plan de abonado).
    """
    # El tipo de abonado solo puede ser uno de los tres que distingue la hoja 6 del cuaderno de la
    # Junta. Un valor que no esté en esa lista se rechaza con la lista delante, como se hace con los
    # tipos de papel: guardarlo tal cual acabaría en el cuaderno como un dato que no existe.
    if datos.tipo_fertilizacion and servicios.tipo_de_fertilizacion(datos.tipo_fertilizacion) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"«{datos.tipo_fertilizacion}» no es un tipo de abonado. "
                f"Los que hay: {', '.join(sorted(set(servicios.TIPOS_DE_FERTILIZACION.values())))}."
            ),
        )

    avisos = _avisos_fertilizacion(datos, explotacion, db)
    _rechazar_si_bloquea(avisos)

    # **La factura de la que sale el abono tiene que ser suya** (ronda 93). Este campo se copiaba tal
    # cual, sin mirar de quién era: un abono podía quedar apuntando a la factura de **otra finca** y el
    # listado devolvía ese identificador. Es la regla de toda la API —«eso no está en tu cuaderno»— y
    # aquí faltaba. Lo encontró el trabajo de corregir y borrar facturas (ronda 93), que tuvo que contar
    # las que dependen de una factura y se topó con que cualquiera podía apuntarle una.
    _cargar(db, explotacion, models.Factura, datos.factura_id)

    _campana, parcela, fertilizante, _plan = _contexto_fertilizacion(datos, explotacion, db)
    return servicios.preparar_fertilizacion(
        datos, explotacion_id=explotacion.id, fertilizante=fertilizante, parcela=parcela
    )


@router.post("/fertilizaciones", response_model=FertilizacionSalida, status_code=status.HTTP_201_CREATED)
def crear_fertilizacion(
    datos: FertilizacionEntrada,
    explotacion: ExplotacionActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> models.RegistroFertilizacion:
    registro = _preparar_fertilizacion_guardable(datos, explotacion, db)
    db.add(registro)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="fertilizacion",
            entidad_id=registro.id,
            accion="crear",
            datos={"fecha": str(registro.fecha), "abono": registro.fertilizante_nombre},
        )
    )
    db.commit()
    return registro


@router.get("/fertilizaciones", response_model=list[FertilizacionSalida])
def listar_fertilizaciones(
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    parcela_id: int | None = None,
) -> list[models.RegistroFertilizacion]:
    consulta = select(models.RegistroFertilizacion).where(
        models.RegistroFertilizacion.explotacion_id == explotacion.id,
        models.RegistroFertilizacion.anulado.is_(False),
    )
    if campana_id is not None:
        consulta = consulta.where(models.RegistroFertilizacion.campana_id == campana_id)
    if parcela_id is not None:
        consulta = consulta.where(models.RegistroFertilizacion.parcela_id == parcela_id)
    return list(db.scalars(consulta.order_by(models.RegistroFertilizacion.fecha.desc())))


@router.post("/fertilizaciones/{registro_id}/anular")
def anular_fertilizacion(
    registro_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    # ***Anular tambien es escribir***: *deja el apunte tachado, y eso cambia el cuaderno.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    registro = obtener_de_la_explotacion(
        db, models.RegistroFertilizacion, registro_id, explotacion.id
    )
    _anular(db, explotacion, registro, datos.motivo, "fertilizacion")
    return {"anulado": True, "motivo": datos.motivo}


@router.put("/fertilizaciones/{registro_id}", response_model=FertilizacionSalida)
def corregir_fertilizacion(
    registro_id: int,
    datos: FertilizacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> models.RegistroFertilizacion:
    """Corrige un abono ya apuntado: se cambia ese apunte, no se apunta otro.

    Los números que el agricultor no calcula (el abono puro, los kilos totales) se **vuelven a
    calcular**, no se copian: si se corrige la cantidad y el abono puro se quedara con el valor
    viejo, el cuaderno diría una cosa en los kilos y otra en las unidades fertilizantes, y la que
    mira la administración es la segunda.
    """
    registro = obtener_de_la_explotacion(
        db, models.RegistroFertilizacion, registro_id, explotacion.id
    )
    preparado = _preparar_fertilizacion_guardable(datos, explotacion, db)
    correcciones.corregir(
        db,
        guardado=registro,
        preparado=preparado,
        entidad="fertilizacion",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return registro


@router.delete("/fertilizaciones/{registro_id}")
def borrar_fertilizacion(
    registro_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    """Quita un abono del cuaderno, dejando en la auditoría lo que había."""
    registro = obtener_de_la_explotacion(
        db, models.RegistroFertilizacion, registro_id, explotacion.id
    )
    _no_se_borra_si_esta_firmado(db, explotacion, "fertilizacion", registro_id)
    correcciones.borrar(
        db,
        registro=registro,
        entidad="fertilizacion",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": registro_id}


# --------------------------------------------------------------------------
# Labores
# --------------------------------------------------------------------------


def _preparar_labor_guardable(datos: LaborEntrada, explotacion, db) -> models.Labor:
    """Comprueba una labor y devuelve el registro listo para guardar, sin guardarlo.

    Lo usan el alta y la corrección: lo de aquí es lo que hace que una labor corregida no pueda
    quedarse sin parcela, ni con una máquina de otra finca, ni con el cultivo en blanco cuando el
    agricultor ya dijo qué tiene sembrado en esa tierra.
    """
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is None and datos.grupo_id is None:
        raise HTTPException(status_code=422, detail=textos.mensaje("V18_sin_parcela"))
    _cargar(db, explotacion, models.Parcela, datos.parcela_id)
    # La máquina, si se ha dicho, tiene que ser suya: `_cargar` contesta «Eso no está en tu
    # cuaderno» (404) y no confirma si ese identificador existe en otra finca, que es la regla de
    # toda la API. No se comprueba la ITEAf aquí a propósito: la ITEAf es de los equipos de
    # aplicación de producto, y una labor se puede hacer con un tractor que no la necesita.
    _cargar(db, explotacion, models.EquipoAplicacion, datos.equipo_id)
    labor = models.Labor(explotacion_id=explotacion.id, **datos.model_dump())
    # El cultivo, igual que en los tratamientos: si el apunte no lo trae, se pone el que el
    # agricultor ya dijo que hay en esa parcela este año. Así el listado de labores y el volcado
    # oficial dicen de qué cultivo era la labor en vez de ir en blanco.
    if not labor.cultivo:
        declarado = servicios.cultivo_declarado(
            db,
            explotacion_id=explotacion.id,
            parcela_id=datos.parcela_id,
            campana_id=datos.campana_id,
        )
        if declarado is not None:
            labor.cultivo = declarado.especie
    return labor


@router.post("/labores", response_model=LaborSalida, status_code=status.HTTP_201_CREATED)
def crear_labor(
    datos: LaborEntrada,
    explotacion: ExplotacionActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> models.Labor:
    labor = _preparar_labor_guardable(datos, explotacion, db)
    db.add(labor)
    db.commit()
    return labor


@router.put("/labores/{labor_id}", response_model=LaborSalida)
def corregir_labor(
    labor_id: int,
    datos: LaborEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> models.Labor:
    """Corrige un trabajo ya apuntado, en la misma fila y con las mismas comprobaciones."""
    labor = obtener_de_la_explotacion(db, models.Labor, labor_id, explotacion.id)
    preparado = _preparar_labor_guardable(datos, explotacion, db)
    correcciones.corregir(
        db,
        guardado=labor,
        preparado=preparado,
        entidad="labor",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return labor


@router.delete("/labores/{labor_id}")
def borrar_labor(
    labor_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    """Quita un trabajo del cuaderno, dejando en la auditoría lo que había."""
    labor = obtener_de_la_explotacion(db, models.Labor, labor_id, explotacion.id)
    _no_se_borra_si_esta_firmado(db, explotacion, "labor", labor_id)
    correcciones.borrar(
        db,
        registro=labor,
        entidad="labor",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": labor_id}


@router.post("/labores/{labor_id}/anular")
def anular_labor(
    labor_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    # ***Anular tambien es escribir***: *deja el apunte tachado, y eso cambia el cuaderno.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    """Anula un trabajo: se queda tachado, con su motivo (lo mismo que un tratamiento).

    Existe desde la ronda 91 por un motivo concreto: cuando un apunte **firmado** no se puede
    borrar, el mensaje que lo dice manda al agricultor a anularlo. Sin esta ruta, el único camino
    que le quedaba era irse con el aviso y sin salida, que es justo lo que este programa no hace.
    """
    labor = obtener_de_la_explotacion(db, models.Labor, labor_id, explotacion.id)
    _anular(db, explotacion, labor, datos.motivo, "labor")
    return {"anulado": True, "motivo": datos.motivo}


@router.get("/labores", response_model=list[LaborSalida])
def listar_labores(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> list[models.Labor]:
    consulta = select(models.Labor).where(
        models.Labor.explotacion_id == explotacion.id, models.Labor.anulado.is_(False)
    )
    if campana_id is not None:
        consulta = consulta.where(models.Labor.campana_id == campana_id)
    return list(db.scalars(consulta.order_by(models.Labor.fecha.desc())))


# --------------------------------------------------------------------------
# Cosecha: aquí se comprueba lo de los días de espera
# --------------------------------------------------------------------------


@router.post("/cosecha/validar", response_model=ResultadoValidacion)
def validar_cosecha_endpoint(
    datos: CosechaEntrada, explotacion: ExplotacionActual, db: Db
) -> ResultadoValidacion:
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    tratamientos = list(
        db.scalars(
            select(models.TratamientoFitosanitario).where(
                models.TratamientoFitosanitario.explotacion_id == explotacion.id,
                models.TratamientoFitosanitario.parcela_id == datos.parcela_id,
                models.TratamientoFitosanitario.anulado.is_(False),
                models.TratamientoFitosanitario.fecha <= datos.fecha,
            )
        )
    )
    # El respaldo por catálogo: si a un apunte le falta el plazo pero su producto lo tiene (por
    # ejemplo, porque alguien rellenó la ficha del producto **después** de tratarlo), hay que usar
    # el del producto. **Esto no funcionaba**: el diccionario no se pasaba, así que iba vacío y el
    # respaldo no encontraba nunca nada (A5 de `docs/T02_VALORES_POR_DEFECTO.md`). Se piden todos
    # de una vez, no uno por tratamiento.
    productos_por_id = {
        producto.id: producto
        for producto in db.scalars(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == explotacion.id,
                models.ProductoFitosanitario.id.in_(
                    {t.producto_id for t in tratamientos if t.producto_id is not None}
                ),
            )
        )
    }
    avisos = validaciones.validar_cosecha(
        fecha_cosecha=datos.fecha,
        tratamientos=tratamientos,
        producto_por_id=productos_por_id,
    )
    return _resultado(avisos)


def _preparar_cosecha_guardable(datos: CosechaEntrada, explotacion, db):
    """Comprueba una cosecha (los días de espera) y la deja lista para guardar.

    Devuelve la labor y el resultado de la comprobación, que es lo que la pantalla enseña después
    («te quedan 12 días de espera»): así la comprobación se hace una vez y no dos.

    Una cosecha **es una labor** con `tipo="cosecha"`: se guarda en la misma tabla porque el
    cuaderno de la Junta las pide juntas en su hoja de labores, y lo que cambia es lo que se
    pregunta. Se separa aquí para que el alta y la corrección no puedan comprobar cosas distintas.
    """
    resultado = validar_cosecha_endpoint(datos, explotacion, db)
    if not resultado.puede_guardarse:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "puede_guardarse": False,
                "avisos": [aviso.model_dump() for aviso in resultado.avisos if aviso.bloquea],
            },
        )
    # La máquina, si se ha dicho, tiene que ser suya (404 si no). **Y hasta la ronda 91 esto se
    # perdía**: el asistente preguntaba con qué máquina se había cosechado, el navegador lo mandaba
    # y este esquema no tenía el campo, así que Pydantic lo tiraba sin decir nada. El contenido
    # mínimo del CUE pide la maquinaria en la hoja de labores, así que era un dato del cuaderno que
    # se quedaba vacío y nadie se enteraba.
    _cargar(db, explotacion, models.EquipoAplicacion, datos.equipo_id)
    labor = models.Labor(
        explotacion_id=explotacion.id,
        campana_id=datos.campana_id,
        tipo="cosecha",
        fecha=datos.fecha,
        parcela_id=datos.parcela_id,
        equipo_id=datos.equipo_id,
        detalles={"producto": datos.producto, "cantidad_kg": datos.cantidad_kg},
        semillas_siembra=datos.semillas_siembra,
        plantas_cosechadas=datos.plantas_cosechadas,
        sin_cosechar_ambiental=datos.sin_cosechar_ambiental,
        restos_cosecha_depositados=datos.restos_cosecha_depositados,
    )
    return labor, resultado


@router.post("/cosecha", status_code=status.HTTP_201_CREATED)
def registrar_cosecha(
    datos: CosechaEntrada,
    explotacion: ExplotacionActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    labor, resultado = _preparar_cosecha_guardable(datos, explotacion, db)
    db.add(labor)
    db.commit()
    return {"id": labor.id, "guardado": True, "avisos": [a.model_dump() for a in resultado.avisos]}


@router.put("/cosecha/{labor_id}")
def corregir_cosecha(
    labor_id: int,
    datos: CosechaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    """Corrige una cosecha ya apuntada: se cambia ese apunte, no se apunta otra."""
    labor = obtener_de_la_explotacion(db, models.Labor, labor_id, explotacion.id)
    preparado, resultado = _preparar_cosecha_guardable(datos, explotacion, db)
    correcciones.corregir(
        db,
        guardado=labor,
        preparado=preparado,
        entidad="labor",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"id": labor.id, "guardado": True, "avisos": [a.model_dump() for a in resultado.avisos]}


@router.delete("/cosecha/{labor_id}")
def borrar_cosecha(
    labor_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    # ***Escribir el cuaderno es escribir***: *quien solo mira, no apunta.*
    puede_modificar: PuedeModificar,
    db: Db,
) -> dict:
    """Quita una cosecha del cuaderno. Es la misma fila que la de las labores.

    **Desde el T12 (03/10/2026) una cosecha puede estar referenciada por entregas**, y eso cambia lo que se
    puede hacer aquí. La entrega apunta a la cosecha de la que salió (`VentaDeCosecha.cosecha_id`, el «lote
    cosechado» que el contrato manda separar), así que borrar la cosecha dejaría la entrega diciendo que
    salió de algo que ya no existe —y, sin esta comprobación, con un fallo de la base en la cara, porque la
    clave ajena lo impide pero nadie traduce el error—.

    El camino es el de siempre en este programa: **se dice cuántas entregas la usan y se ofrece lo que sí
    vale** (corregirla, o cambiar de qué cosecha sale la entrega). La cuenta se saca de las tablas de verdad
    (`correcciones.en_uso`), no de una lista escrita a mano: si mañana otra cosa apunta a una cosecha, esta
    cuenta la incluye sola.
    """
    labor = obtener_de_la_explotacion(db, models.Labor, labor_id, explotacion.id)
    _no_se_borra_si_esta_firmado(db, explotacion, "labor", labor_id)
    entregas = correcciones.en_uso(
        db, explotacion_id=explotacion.id, columna="cosecha_id", valor=labor_id
    )
    if entregas:
        # El mensaje va en singular o plural con el ayudante de siempre: «Esa cosecha la usa 1 entrega» y
        # «...la usan 3 entregas» son la misma cosa dicha como se dice (`textos.mensaje_con_cuenta`).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("D11_esa_cosecha_la_usa_una_entrega", entregas),
        )
    correcciones.borrar(
        db,
        registro=labor,
        entidad="labor",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": labor_id}
