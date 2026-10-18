"""Los análisis de laboratorio: suelo, agua de riego, planta, cosecha y residuos.

La app oficial de Castilla y León lo tiene en «Otras Actividades: Analíticas», y es el
bloque 13 del contenido mínimo del CUE (documento técnico SIEX v3.11).

**Por qué esta sección merece la pena de verdad.** Un análisis de suelo es el papel más
reutilizable que tiene un agricultor: los números que trae sirven para el plan de abono de
este año y de los tres siguientes. En un cajón no sirve para nada. Aquí se guardan **por
clave**, que es lo que permite que el plan de abono los lea y que dentro de dos años se
sepa de dónde salía cada cifra.

Tres decisiones que conviene no deshacer:

1. **El boletín del laboratorio se guarda como fichero, no dentro de la base de datos.**
   Un boletín con fotos son varios megas; meterlo en una columna hace que la copia de
   seguridad del agricultor deje de poderse manejar.

2. **El nombre del fichero que manda el navegador NUNCA se usa como ruta.** La ruta la
   pone el programa: carpeta por finca, nombre por identificador. Un nombre como
   `../../app/main.py` llegaría a escribir fuera de su carpeta, y eso no puede pasar ni
   por descuido.

3. **Un parámetro que no esté en el catálogo se descarta, no se guarda.** Ver
   `servicios.limpia_parametros`. Guardarlo daría un cuaderno con un número que después
   nadie sabe interpretar, y en una inspección eso es peor que no tenerlo.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import adjuntos, catalogos, correcciones, legal, models, servicios, textos, validaciones
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AnaliticaConSitio,
    AnaliticaEntrada,
    AnaliticaSalida,
    InformeDeAnalisis,
)

router = APIRouter(prefix="/api", tags=["análisis"])

# --------------------------------------------------------------------------
# El boletín del laboratorio
# --------------------------------------------------------------------------

# La carpeta de adjuntos, los tipos admitidos y el tope de tamaño viven ahora en
# `app/adjuntos.py`, porque la documentación anexa necesitaba exactamente lo mismo y tener dos
# copias de código de seguridad es la forma más rápida de que una se arregle y la otra no.
# Se dejan estos nombres aquí para no romper nada de lo que ya los usaba.
MAXIMO_BYTES = adjuntos.MAXIMO_BYTES

# Tipos de fichero admitidos para el boletín. La lista es CORTA a propósito: se admiten el PDF y
# los formatos de foto que hacen los móviles, y nada más. Aceptar cualquier cosa convertiría la
# carpeta de adjuntos en un vertedero y en un problema de seguridad.
TIPOS_ADMITIDOS = adjuntos.TIPOS_BOLETIN
carpeta_de_adjuntos = adjuntos.carpeta_de_adjuntos
TROZO_BYTES = adjuntos.TROZO_BYTES


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


def _donde(db, analitica: models.Analitica) -> str:
    """De dónde salió la muestra, dicho como lo diría el agricultor."""
    if analitica.parcela_id is not None:
        parcela = db.get(models.Parcela, analitica.parcela_id)
        return parcela.alias if parcela else textos.ANALITICA["parcela_vacia"]
    if analitica.instalacion_id is not None:
        instalacion = db.get(models.Instalacion, analitica.instalacion_id)
        return instalacion.alias if instalacion else textos.ANALITICA["parcela_vacia"]
    if analitica.lote:
        return analitica.lote
    return textos.ANALITICA["parcela_vacia"]


def con_sitio(db, analitica: models.Analitica) -> AnaliticaConSitio:
    """El análisis, con el nombre de dónde salió y el nombre de cada número.

    Los nombres se resuelven aquí y no en la interfaz porque el catálogo vive en el
    servidor: si la interfaz los pusiera, habría dos listas de parámetros que mantener y
    acabarían diciendo cosas distintas.

    Es pública a propósito: el plan de abono la usa para devolver el análisis en el que se
    apoya, y tener dos versiones de esto sería la forma más rápida de que se separaran.
    """
    con_nombre = []
    for parametro in analitica.parametros or []:
        if not isinstance(parametro, dict):
            continue
        conocido = catalogos.parametro_de(analitica.tipo, parametro.get("clave"))
        con_nombre.append(
            {
                "clave": parametro.get("clave"),
                "etiqueta": conocido.etiqueta if conocido else str(parametro.get("clave")),
                "valor": parametro.get("valor"),
                "unidad": parametro.get("unidad") or "",
                "texto": legal.formatea_medida(
                    parametro.get("valor"), parametro.get("unidad") or ""
                ),
            }
        )
    base = AnaliticaSalida.model_validate(analitica).model_dump()
    # Se sobrescriben claves del diccionario en vez de pasarlas como argumentos repetidos:
    # `etiqueta_tipo` y `anios` ya vienen en el volcado con su valor por defecto, y
    # pasarlas dos veces revienta con «got multiple values for keyword argument».
    base["etiqueta_tipo"] = catalogos.etiqueta_analitica(analitica.tipo)
    base["anios"] = legal.anios_transcurridos(analitica.fecha_toma_muestra)
    base["donde"] = _donde(db, analitica)
    base["parametros_con_nombre"] = con_nombre
    return AnaliticaConSitio(**base)


def _guardar_adjunto(analitica: models.Analitica, fichero: UploadFile, contenido: bytes) -> None:
    """Escribe el boletín en disco y deja la referencia en el análisis.

    El nombre que manda el navegador se usa SOLO para enseñarlo. La ruta la decide el programa,
    y de eso se encarga `app/adjuntos.py`, que es el mismo sitio por el que pasan los papeles de
    la documentación anexa.
    """
    nombre, ruta, tipo, bytes_escritos = adjuntos.guardar_en_disco(
        explotacion_id=analitica.explotacion_id,
        prefijo="analitica",
        fichero=fichero,
        contenido=contenido,
        permitidos=adjuntos.TIPOS_BOLETIN,
    )
    anterior = analitica.fichero_ruta
    analitica.fichero_nombre = nombre
    analitica.fichero_ruta = ruta
    analitica.fichero_tipo = tipo
    analitica.fichero_bytes = bytes_escritos
    # El boletín anterior se borra cuando se deja de apuntar a él: si no, cada corrección dejaría
    # el fichero viejo ocupando sitio para siempre, y nadie se acordaría de limpiarlo.
    if anterior and anterior != ruta:
        adjuntos.borrar_del_disco(anterior)


def _ruta_del_informe(analitica: models.Analitica) -> Path:
    """La ruta del boletín, comprobando que sigue estando dentro de su carpeta.

    La comprobación la hace `app/adjuntos.py`, que es el mismo sitio por el que pasan los papeles
    de la documentación anexa. Aquí solo se cambia el mensaje: «vuelve a subirlo» tiene sentido
    para un boletín, y quien lo lee es el agricultor.
    """
    try:
        return adjuntos.ruta_segura(analitica.fichero_ruta or "")
    except HTTPException as error:
        raise HTTPException(
            status_code=404,
            detail="No encontramos el boletín guardado. Vuelve a subirlo.",
        ) from error


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get("/analiticas", response_model=list[AnaliticaConSitio])
def listar_analiticas(
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    tipo: str | None = None,
    parcela_id: int | None = None,
) -> list[AnaliticaConSitio]:
    """Los análisis de la finca, del más nuevo al más viejo.

    Un año no cierra el análisis: el de la tierra de 2024 sigue valiendo en 2026, así que
    por defecto se devuelven TODOS los de la finca, no solo los de la campaña en curso.
    `campana_id` filtra cuando de verdad se quiere solo un año.
    """
    consulta = select(models.Analitica).where(
        models.Analitica.explotacion_id == explotacion.id,
        models.Analitica.anulado.is_(False),
    )
    if campana_id is not None:
        consulta = consulta.where(models.Analitica.campana_id == campana_id)
    if tipo is not None:
        consulta = consulta.where(models.Analitica.tipo == tipo)
    if parcela_id is not None:
        consulta = consulta.where(models.Analitica.parcela_id == parcela_id)
    analiticas = list(
        db.scalars(consulta.order_by(models.Analitica.fecha_toma_muestra.desc()))
    )
    return [con_sitio(db, analitica) for analitica in analiticas]


@router.get("/analiticas/informe", response_model=InformeDeAnalisis)
def informe_de_analisis(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> InformeDeAnalisis:
    """El «Informe Analíticas» de la app oficial: todos los análisis, en una tabla.

    Va declarado ANTES de `/analiticas/{analitica_id}` a propósito. FastAPI resuelve las
    rutas por orden de declaración, así que si estuviera después, «informe» se leería
    como un identificador y esta llamada devolvería un 422 sin explicar por qué.
    """
    campana = _campana(db, explotacion, campana_id)
    analiticas = list(
        db.scalars(
            select(models.Analitica)
            .where(
                models.Analitica.explotacion_id == explotacion.id,
                models.Analitica.campana_id == campana.id,
                models.Analitica.anulado.is_(False),
            )
            .order_by(models.Analitica.fecha_toma_muestra)
        )
    )
    filas = []
    for analitica in analiticas:
        filas.append(
            {
                "fecha_toma_muestra": legal.formatea_fecha(analitica.fecha_toma_muestra),
                # En blanco y no «sin fecha»: en una tabla, un hueco se entiende y una
                # frase repetida en cada fila ensucia el informe.
                "fecha_resultado": (
                    legal.formatea_fecha(analitica.fecha_resultado)
                    if analitica.fecha_resultado
                    else ""
                ),
                "material": catalogos.etiqueta_analitica(analitica.tipo),
                "donde": _donde(db, analitica),
                "laboratorio": analitica.laboratorio or "",
                "numero_informe": analitica.numero_informe or "",
                "sustancia": analitica.sustancia_detectada or "",
                "numeros": [
                    {
                        "etiqueta": catalogos.parametro_de(analitica.tipo, p.get("clave")).etiqueta
                        if catalogos.parametro_de(analitica.tipo, p.get("clave"))
                        else str(p.get("clave")),
                        "texto": legal.formatea_medida(p.get("valor"), p.get("unidad") or ""),
                    }
                    for p in (analitica.parametros or [])
                    if isinstance(p, dict)
                ],
                "tiene_boletin": bool(analitica.fichero_ruta),
            }
        )
    return InformeDeAnalisis(
        campana=campana.anio,
        cuantos=len(filas),
        filas=filas,
        titulos=[
            textos.ROTULOS["muestra"],
            textos.ROTULOS["resultado"],
            textos.ROTULOS["material"],
            textos.ANALITICA["sitio"],
            textos.ROTULOS["laboratorio"],
            textos.ROTULOS["informe"],
            textos.ROTULOS["numeros"],
        ],
        vacio=textos.ANALITICA["informe_sin_nada"],
    )


@router.post("/analiticas/validar")
def validar_analitica_endpoint(datos: AnaliticaEntrada, _: ExplotacionActual) -> dict:
    """Pregunta qué le falta a un análisis **antes** de guardarlo.

    **Pide sesión desde el 03/10/2026, y antes no la pedía.** Lo encontró la revisión de rutas
    sin sesión (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.19) y se quedó en el cajón: era una
    de las cuatro rutas que **deberían** pedirla. El motivo es que su cuerpo lleva
    identificadores de la finca (`campana_id`, `parcela_id`, `instalacion_id`): hoy no se usan
    —`validaciones.validar_analitica` no toca la base de datos, es una función pura— pero una
    ruta pública que acepta identificadores de una finca es una puerta que se abre sola el día
    que alguien consulte algo con ellos. Y no rompe nada: **todo el que la llama ya manda su
    vale** (la pantalla y el recorrido de humo).
    """
    limpios = servicios.limpia_parametros(datos.tipo, datos.parametros)
    avisos = validaciones.validar_analitica(datos=datos, parametros_limpios=limpios)
    return {
        "puede_guardarse": not validaciones.hay_bloqueo(avisos),
        "avisos": [aviso.como_dict() for aviso in avisos],
    }


@router.post("/analiticas", response_model=AnaliticaConSitio, status_code=status.HTTP_201_CREATED)
def crear_analitica(
    datos: AnaliticaEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> AnaliticaConSitio:
    limpios = servicios.limpia_parametros(datos.tipo, datos.parametros)
    _rechazar_si_bloquea(
        validaciones.validar_analitica(datos=datos, parametros_limpios=limpios)
    )
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    if datos.instalacion_id is not None:
        obtener_de_la_explotacion(db, models.Instalacion, datos.instalacion_id, explotacion.id)

    analitica = servicios.preparar_analitica(datos, explotacion_id=explotacion.id)
    db.add(analitica)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="analitica",
            accion="crear",
            datos={
                "tipo": analitica.tipo,
                "fecha_toma_muestra": str(analitica.fecha_toma_muestra),
                "parametros": len(analitica.parametros or []),
            },
        )
    )
    db.commit()
    return con_sitio(db, analitica)


@router.get("/analiticas/{analitica_id}", response_model=AnaliticaConSitio)
def ver_analitica(
    analitica_id: int, explotacion: ExplotacionActual, db: Db
) -> AnaliticaConSitio:
    analitica = obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)
    return con_sitio(db, analitica)


@router.put("/analiticas/{analitica_id}", response_model=AnaliticaConSitio)
def corregir_analitica(
    analitica_id: int,
    datos: AnaliticaEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> AnaliticaConSitio:
    """Corrige un análisis.

    Se puede corregir entero y sin dejar rastro porque **un análisis no es un apunte del
    agricultor**: es un dato que viene de fuera, y si al copiarlo se ha bailado un número,
    lo que hay que hacer es dejarlo bien. Lo que sí se anota es que se ha corregido.
    """
    limpios = servicios.limpia_parametros(datos.tipo, datos.parametros)
    _rechazar_si_bloquea(
        validaciones.validar_analitica(datos=datos, parametros_limpios=limpios)
    )
    analitica = obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    if datos.instalacion_id is not None:
        obtener_de_la_explotacion(db, models.Instalacion, datos.instalacion_id, explotacion.id)

    for clave, valor in datos.model_dump(exclude={"parametros"}).items():
        setattr(analitica, clave, valor)
    analitica.parametros = limpios
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="analitica",
            entidad_id=analitica.id,
            accion="corregir",
            datos={"tipo": analitica.tipo, "parametros": len(limpios)},
        )
    )
    db.commit()
    return con_sitio(db, analitica)


@router.post("/analiticas/{analitica_id}/anular", response_model=AnaliticaSalida)
def anular_analitica(
    analitica_id: int,
    datos: dict,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> models.Analitica:
    """Anula el análisis. No se borra: queda con el motivo, como todo en el cuaderno."""
    motivo = (datos or {}).get("motivo", "").strip()
    if len(motivo) < 3:
        raise HTTPException(
            status_code=422, detail="Dinos por qué lo anulas, para que quede apuntado."
        )
    analitica = obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)
    analitica.anulado = True
    analitica.motivo_anulacion = motivo
    # Un plan que se apoyaba en un análisis anulado se queda sin apoyo: si no se quitara,
    # el informe diría que el plan se basa en un análisis que ya no vale.
    for plan in db.scalars(
        select(models.PlanAbonado).where(
            models.PlanAbonado.explotacion_id == explotacion.id,
            models.PlanAbonado.analitica_id == analitica.id,
        )
    ):
        plan.analitica_id = None
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="analitica",
            entidad_id=analitica.id,
            accion="anular",
            datos={"motivo": motivo},
        )
    )
    db.commit()
    return analitica


@router.post("/analiticas/{analitica_id}/informe", response_model=AnaliticaConSitio)
async def subir_informe(
    analitica_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
    fichero: UploadFile = File(...),
) -> AnaliticaConSitio:
    """Sube el boletín del laboratorio: el PDF o la foto que hace el móvil."""
    analitica = obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)

    # Se lee por trozos y se corta en cuanto pasa del tope: así un fichero de dos gigas no se
    # llega a cargar entero en memoria. El tipo se mira antes de leer nada.
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, adjuntos.TIPOS_BOLETIN)

    _guardar_adjunto(analitica, fichero, contenido)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="analitica",
            entidad_id=analitica.id,
            accion="subir_informe",
            datos={"nombre": analitica.fichero_nombre},
        )
    )
    db.commit()
    return con_sitio(db, analitica)


@router.get("/analiticas/{analitica_id}/informe")
def descargar_informe(
    analitica_id: int, explotacion: ExplotacionActual, db: Db
) -> FileResponse:
    analitica = obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)
    if not analitica.fichero_ruta:
        raise HTTPException(status_code=404, detail=textos.ANALITICA["sin_informe"])
    ruta = _ruta_del_informe(analitica)
    return FileResponse(
        ruta,
        media_type=analitica.fichero_tipo or "application/octet-stream",
        filename=analitica.fichero_nombre or ruta.name,
    )


@router.get("/analiticas/{analitica_id}/parametros")
def parametros_del_analisis(
    analitica_id: int, explotacion: ExplotacionActual, db: Db
) -> Response:
    """Los números de un análisis en texto plano, para pegarlos donde haga falta.

    Existe porque el uso real es este: el agricultor quiere mandarle a su técnico lo que
    dice el boletín por WhatsApp. Un texto se pega en cualquier sitio; una tabla, no.
    """
    analitica = obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)
    lineas = [
        f"{textos.ROTULOS['analisis']}: {catalogos.etiqueta_analitica(analitica.tipo)}",
        f"{textos.ANALITICA['sitio']}: {_donde(db, analitica)}",
        f"{textos.ANALITICA['cogida'].format(fecha=legal.formatea_fecha(analitica.fecha_toma_muestra))}",
    ]
    if analitica.laboratorio:
        lineas.append(f"{textos.ANALITICA['quien']}: {analitica.laboratorio}")
    if analitica.numero_informe:
        lineas.append(f"{textos.ANALITICA['informe_numero']}: {analitica.numero_informe}")
    for parametro in analitica.parametros or []:
        conocido = catalogos.parametro_de(analitica.tipo, parametro.get("clave"))
        nombre = conocido.etiqueta if conocido else parametro.get("clave")
        lineas.append(
            f"{nombre}: {legal.formatea_medida(parametro.get('valor'), parametro.get('unidad') or '')}"
        )
    return Response(
        content="\n".join(lineas),
        media_type="text/plain; charset=utf-8",
    )


@router.delete("/analiticas/{analitica_id}")
def borrar_analitica(
    analitica_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Quita un análisis del cuaderno, **si no está sosteniendo un plan de abono**.

    POR QUÉ NO SE BORRA UN ANÁLISIS QUE SOSTIENE UN PLAN. El plan guarda de qué análisis salió
    (`PlanAbonado.analitica_id`): ese análisis es el papel que justifica los números que se van a
    echar. Si desapareciera, el plan seguiría diciendo que se apoya en él —el informe lo enseña
    junto al plan— y no habría nada que enseñar: el cuaderno estaría justificando el abono con algo
    que ya no está. Así que se contesta 409 con **cuántos planes lo usan**
    (`textos.B5_en_uso`, el mensaje genérico de «esto está en uso»), que es lo que hay que resolver
    antes: corregir esos planes para que apunten a otro análisis, borrarlos, o **corregir el
    análisis en vez de borrarlo** (`PUT /api/analiticas/{id}`), que es lo que quiere la mayoría de
    las veces que alguien se equivoca al copiar un boletín.

    Y CUANDO SÍ SE BORRA, SE BORRA DE VERDAD, CON TODO LO SUYO:

      · La fila se va del cuaderno con `correcciones.borrar`, que deja en la auditoría el registro
        entero que había (los números, el laboratorio, el número de informe y qué fichero era).
      · **El boletín se va también del disco.** Dejarlo ahí sería basura del agricultor ocupando
        sitio para siempre y sin nada que lo explique: es el mismo cuidado que ya tiene
        `_guardar_adjunto` cuando se sube un boletín nuevo encima del viejo. Si el fichero no se
        puede borrar, no se impide nada —el análisis ya está borrado y el rastro también—, porque
        un fichero huérfano ocupa sitio y un agricultor que no puede borrar su apunte, no.
    """
    analitica = obtener_de_la_explotacion(db, models.Analitica, analitica_id, explotacion.id)

    planes = correcciones.en_uso(
        db, explotacion_id=explotacion.id, columna="analitica_id", valor=analitica_id
    )
    if planes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B5_en_uso", planes),
        )

    ruta_del_boletin = analitica.fichero_ruta
    correcciones.borrar(
        db,
        registro=analitica,
        entidad="analitica",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    adjuntos.borrar_del_disco(ruta_del_boletin)
    return {"borrado": True, "id": analitica_id}

