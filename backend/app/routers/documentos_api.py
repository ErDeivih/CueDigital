"""La documentación anexa: los papeles que acompañan al cuaderno.

## Por qué existe esto

**Esta sección faltaba y se encontró leyendo las instrucciones oficiales.** La app de la Junta la
llama «Documentación», y las instrucciones dicen, con estas palabras:

> *«El apartado Documentación permite guardar la documentación complementaria al Cuaderno:
> contratos, facturas, albaranes de entrega de envases a Sigfito, etc. La documentación puede
> organizarse en distintas carpetas.»*

Y no es un adorno. El cuaderno dice lo que se hizo, pero **los papeles son los que lo
demuestran**: el contrato de arrendamiento de la tierra que se labra, la factura del producto que
se compró, el resguardo de Sigfito de los envases vacíos. Sin un sitio donde estén, acaban en una
caja de zapatos, en el móvil de quien los hizo o en el coche.

## Las decisiones

1. **El papel apuntado y el fichero son dos cosas distintas y las dos valen.** Se puede apuntar
   «el contrato está en el cajón de arriba» sin subir nada (`tiene_fichero: false`). Obligar a
   subir el fichero para poder apuntarlo dejaría fuera al que no sabe hacerle una foto, y ese es
   justo el agricultor que más necesita el programa.
2. **El fichero va a disco, no a la base ni al repositorio** (`app/adjuntos.py`). Mismo motivo que
   con los boletines de laboratorio.
3. **Un papel se anula con su motivo** —y desde la ronda 94 **también se puede corregir y borrar**,
   que es lo que pidió David: «recuerda también dejar borrar las cosas que introduzca porque puede
   que me equivoque, o modificar también». Lo que no cambia es lo de fondo: un papel que se borra de
   verdad **se lleva su fichero**, y lo que había queda escrito en la auditoría. Anular sigue siendo
   lo correcto cuando el papel existe y lo que está mal es el apunte: el fichero se queda.
4. **La carpeta la escribe el agricultor.** El documento oficial dice que «puede organizarse en
   distintas carpetas» y no impone ninguna; `catalogos.CARPETAS_SUGERIDAS` son sugerencias. Un
   catálogo cerrado de carpetas sería una obligación que la Junta no pide.
5. **El tipo sí sale del documento** (contrato, factura, albarán de Sigfito, otros), porque los
   nombra él y sigue con «etc.».
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import adjuntos, catalogos, correcciones, legal, models, servicios, textos
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual, obtener_de_la_explotacion
from ..schemas import DocumentoEntrada, DocumentoSalida

router = APIRouter(prefix="/api", tags=["documentación"])

CARPETA_POR_DEFECTO = "Otros"


def _con_etiqueta(documento: models.DocumentoAnexo) -> DocumentoSalida:
    """El documento con el nombre del tipo ya resuelto.

    Se resuelve aquí y no en la pantalla porque el catálogo vive en el servidor: si la interfaz
    pusiera los nombres, habría dos listas que mantener y acabarían diciendo cosas distintas.
    """
    return DocumentoSalida(
        id=documento.id,
        campana_id=documento.campana_id,
        carpeta=documento.carpeta or CARPETA_POR_DEFECTO,
        titulo=documento.titulo,
        tipo=documento.tipo if documento.tipo in catalogos.TIPOS_DOCUMENTO else "otros",
        etiqueta_tipo=catalogos.etiqueta_documento(documento.tipo),
        fecha=documento.fecha,
        quien=documento.quien,
        notas=documento.notas,
        nombre_del_fichero=documento.fichero_nombre,
        tipo_del_fichero=documento.fichero_tipo,
        bytes=documento.fichero_bytes,
        tiene_fichero=bool(documento.fichero_ruta),
        anulado=documento.anulado,
        motivo_anulacion=documento.motivo_anulacion,
        creado_en=documento.creado_en,
    )


def _campana_que_toca(db, explotacion, campana_id: int | None) -> int | None:
    """La campaña del papel. Si no se dice, la del año en curso, y si no hay ninguna, ninguna.

    Decisión: **aquí no se falla si no hay campaña**. Un documento anexo no es una actuación: el
    contrato de arrendamiento vale para diez años y una factura puede ser de una campaña que
    todavía no está creada. Obligar a tener creado el año para poder guardar un papel sería
    ponerle una puerta al agricultor delante de algo que no la necesita.
    """
    if campana_id is not None:
        return obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id).id
    campana = db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion.id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )
    return campana.id if campana else None


@router.get("/documentos")
def listar(
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    carpeta: str | None = None,
    tipo: str | None = None,
    incluir_anulados: bool = False,
) -> dict:
    """Los papeles de la finca, agrupados por carpeta.

    Se devuelven agrupados y no en una lista plana porque así es como se buscan: nadie piensa
    «quiero el documento 47», piensa «quiero la factura del abono». Y se devuelven **también las
    carpetas vacías**, para que se vea que existen y que se puede archivar ahí.

    Decisión: por defecto se devuelven TODOS los años, no solo la campaña en curso. Un contrato de
    arrendamiento no es de un año, y las facturas de la campaña pasada siguen haciendo falta
    cuando llega una inspección.
    """
    consulta = select(models.DocumentoAnexo).where(
        models.DocumentoAnexo.explotacion_id == explotacion.id
    )
    if not incluir_anulados:
        consulta = consulta.where(models.DocumentoAnexo.anulado.is_(False))
    if campana_id is not None:
        consulta = consulta.where(models.DocumentoAnexo.campana_id == campana_id)
    if tipo is not None:
        consulta = consulta.where(models.DocumentoAnexo.tipo == tipo)

    documentos = list(
        db.scalars(
            consulta.order_by(
                models.DocumentoAnexo.fecha.desc().nullslast(),
                models.DocumentoAnexo.id.desc(),
            )
        )
    )
    if carpeta is not None:
        documentos = [
            documento
            for documento in documentos
            if (documento.carpeta or CARPETA_POR_DEFECTO) == carpeta
        ]

    salida = [_con_etiqueta(documento) for documento in documentos]
    nombres: list[str] = []
    for documento in salida:
        if documento.carpeta not in nombres:
            nombres.append(documento.carpeta)
    # Las sugeridas que aún no se usan también aparecen: si no, no habría forma de archivar en
    # una carpeta nueva sin escribirla a mano, y el agricultor no sabe que puede.
    for sugerida in catalogos.CARPETAS_SUGERIDAS:
        if sugerida not in nombres:
            nombres.append(sugerida)

    return {
        "textos": textos.DOCUMENTOS,
        "documentos": [documento.model_dump() for documento in salida],
        "carpetas": [
            {
                "nombre": nombre,
                "cuantos": len([d for d in salida if d.carpeta == nombre]),
            }
            for nombre in nombres
        ],
        "sugeridas": list(catalogos.CARPETAS_SUGERIDAS),
        "tipos": [
            {"valor": tipo, "etiqueta": catalogos.etiqueta_documento(tipo)}
            for tipo in catalogos.TIPOS_DOCUMENTO
        ],
        "cuantos": len(salida),
        "sin_archivar": [d.model_dump() for d in salida if d.tipo == "otros"],
        "resumen": (
            textos.DOCUMENTOS["sin_papeles"]
            if not salida
            else textos.con_cuenta(textos.DOCUMENTOS, "cuantos", len(salida))
        ),
    }


def _preparar_documento_guardable(
    datos: DocumentoEntrada,
    explotacion,
    db: Db,
    *,
    actual: models.DocumentoAnexo | None = None,
) -> models.DocumentoAnexo:
    """Comprueba un papel y lo devuelve listo para guardar, **sin guardarlo**.

    Lo usan el alta y la corrección, y **es a propósito**: las dos tienen que exigir lo mismo (que
    el tipo sea uno de los que hay, que la carpeta vacía vaya a «Otros», que la campaña sea de esta
    finca). Si la corrección copiara lo que manda el navegador sin más, un papel corregido podría
    quedarse con un tipo que no existe y desaparecer de la lista sin que nadie lo entienda.

    `actual` es el papel que se está corrigiendo, y sirve para **dejar quieto lo que el formulario
    no puede mandar**: su fichero (ver `servicios.columnas_que_una_correccion_no_toca`). Cambiar el
    título de un contrato no puede dejarlo sin el contrato.
    """
    if datos.tipo not in catalogos.TIPOS_DOCUMENTO:
        raise HTTPException(
            status_code=422,
            detail=(
                f"«{datos.tipo}» no es un tipo de papel que se pueda apuntar. "
                f"Los que hay: {', '.join(catalogos.TIPOS_DOCUMENTO)}."
            ),
        )
    documento = models.DocumentoAnexo(
        explotacion_id=explotacion.id,
        campana_id=_campana_que_toca(db, explotacion, datos.campana_id),
        carpeta=(datos.carpeta or "").strip() or CARPETA_POR_DEFECTO,
        titulo=datos.titulo.strip(),
        tipo=datos.tipo,
        fecha=datos.fecha,
        quien=(datos.quien or "").strip() or None,
        notas=(datos.notas or "").strip() or None,
    )
    if actual is not None:
        for columna in servicios.columnas_que_una_correccion_no_toca(
            models.DocumentoAnexo, DocumentoEntrada, DocumentoSalida
        ):
            setattr(documento, columna, getattr(actual, columna))
    return documento


@router.post("/documentos", response_model=DocumentoSalida, status_code=status.HTTP_201_CREATED)
def crear(
    datos: DocumentoEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> DocumentoSalida:
    """Apunta un papel, con o sin fichero.

    Aquí se apunta y **el fichero se sube aparte** (`POST /api/documentos/{id}/fichero`). Es a
    propósito: así se puede apuntar el papel desde el móvil sin cobertura —«el contrato está en el
    cajón»— y subir la foto cuando se llegue a casa. Al revés no se podría.
    """
    documento = _preparar_documento_guardable(datos, explotacion, db)
    db.add(documento)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="documento",
            entidad_id=documento.id,
            accion="crear",
            datos={"titulo": documento.titulo, "tipo": documento.tipo, "carpeta": documento.carpeta},
        )
    )
    db.commit()
    db.refresh(documento)
    return _con_etiqueta(documento)


@router.put("/documentos/{documento_id}", response_model=DocumentoSalida)
def corregir(
    documento_id: int,
    datos: DocumentoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> DocumentoSalida:
    """Corrige un papel ya apuntado: su título, su carpeta, su tipo, su fecha y sus notas.

    POR QUÉ SE CORRIGE EN EL SITIO Y NO SE BORRA Y SE VUELVE A APUNTAR. Porque el fichero cuelga de
    esta fila: borrar y volver a apuntar dejaría el papel **sin su contrato**, y el agricultor
    tendría que volver a subirlo —y el que hizo la foto en el móvil, muchas veces, ya no la tiene—.
    Corrigiendo aquí, el papel sigue siendo el mismo —mismo `id`— con los datos buenos, y lo que
    había antes queda escrito en la auditoría (`correcciones`).

    Y pasa por **las mismas comprobaciones que el alta**, porque es la misma función
    (`_preparar_documento_guardable`): un tipo que no existe se rechaza igual en las dos puertas.

    El fichero **no se toca**: el formulario no lo manda, y para cambiarlo está su propia puerta
    (`POST /api/documentos/{id}/fichero`), que además borra el viejo al guardar el nuevo.
    """
    documento = obtener_de_la_explotacion(
        db, models.DocumentoAnexo, documento_id, explotacion.id
    )
    preparado = _preparar_documento_guardable(datos, explotacion, db, actual=documento)
    correcciones.corregir(
        db,
        guardado=documento,
        preparado=preparado,
        entidad="documento",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    db.refresh(documento)
    return _con_etiqueta(documento)


@router.delete("/documentos/{documento_id}")
def borrar(
    documento_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Borra un papel del cuaderno **y su fichero del disco**.

    POR QUÉ AQUÍ SÍ SE BORRA EL FICHERO, AL CONTRARIO QUE AL ANULAR. Son dos cosas distintas y hay
    que poder hacer las dos:

      · **Anular** es «este papel no era lo que yo pensaba»: el papel existe, y el fichero es la
        prueba, así que se queda (ver `anular`).
      · **Borrar** es «esto no debería estar aquí»: el agricultor se ha equivocado al subirlo —el
        papel de otro, la foto que no era, el contrato que ya no vale—. Dejar el fichero en el disco
        sería **basura que nadie va a limpiar nunca**: ocupa sitio, no lo enseña ninguna pantalla y
        no lo puede borrar él, que no tiene acceso a esa carpeta. Por eso se borra, y por eso la
        fila desaparece de verdad en vez de quedarse anulada.

    Lo que había queda escrito en la auditoría (`correcciones.borrar`), así que el programa **sí
    sabe** que existió: el cuaderno no lo enseña y el programa puede contestar «¿y aquel papel?».

    La ruta del fichero **nunca sale del nombre que manda el navegador** (ver `adjuntos`): la decide
    el programa cuando guarda, y lo que se borra es esa ruta, comprobada por la base de datos. Un
    nombre como `../../main.py` no puede decidir qué fichero se borra.

    Antes de borrar se cuentan las cosas del cuaderno que apunten al papel, como en todo lo que se
    puede borrar. **Y no es una lista escrita a mano**: `correcciones.tablas_que_apuntan_a` las
    descubre **por el nombre de la columna**, así que el día que una tabla nueva apunte a un papel
    queda contada sola. Hoy son dos: la **inspección** de una máquina y la **aplicabilidad** de una
    obligación, las dos con su `documento_id`. Por eso borrar un papel que alguna use contesta
    **409** en vez de dejarlas apuntando a algo que ya no está.
    """
    documento = obtener_de_la_explotacion(
        db, models.DocumentoAnexo, documento_id, explotacion.id
    )
    dependencias = correcciones.en_uso(
        db, explotacion_id=explotacion.id, columna="documento_id", valor=documento_id
    )
    if dependencias:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B5_en_uso", dependencias),
        )
    ruta_del_fichero = documento.fichero_ruta
    correcciones.borrar(
        db,
        registro=documento,
        entidad="documento",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    # El fichero se borra **después** de que la fila esté fuera, igual que al reemplazarlo
    # (`subir_fichero`): al revés, un fallo al guardar dejaría el papel apuntado sin su papel.
    adjuntos.borrar_del_disco(ruta_del_fichero)
    return {"borrado": True, "id": documento_id, "fichero_borrado": bool(ruta_del_fichero)}


@router.post("/documentos/{documento_id}/fichero", response_model=DocumentoSalida)
async def subir_fichero(
    documento_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
    fichero: UploadFile = File(...),
) -> DocumentoSalida:
    """Sube el papel: un PDF, una foto o el fichero de oficina que sea.

    Se admiten más formatos que en los boletines de laboratorio (ver `adjuntos.TIPOS_DOCUMENTO`),
    porque lo que pide una inspección no tiene un formato fijo: el contrato suele ser un PDF, la
    factura puede venir en una hoja de cálculo, y el resguardo de Sigfito puede ser una foto.
    """
    documento = obtener_de_la_explotacion(
        db, models.DocumentoAnexo, documento_id, explotacion.id
    )
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, adjuntos.TIPOS_DOCUMENTO)
    nombre, ruta, tipo, bytes_escritos = adjuntos.guardar_en_disco(
        explotacion_id=explotacion.id,
        prefijo="documento",
        fichero=fichero,
        contenido=contenido,
        permitidos=adjuntos.TIPOS_DOCUMENTO,
    )
    anterior = documento.fichero_ruta
    documento.fichero_nombre = nombre
    documento.fichero_ruta = ruta
    documento.fichero_tipo = tipo
    documento.fichero_bytes = bytes_escritos
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="documento",
            entidad_id=documento.id,
            accion="subir_fichero",
            datos={"nombre": nombre, "bytes": bytes_escritos},
        )
    )
    db.commit()
    # El fichero anterior se borra al final, cuando ya está guardado el nuevo: al revés, un fallo
    # al guardar dejaría el papel sin fichero y sin el viejo.
    if anterior and anterior != ruta:
        adjuntos.borrar_del_disco(anterior)
    db.refresh(documento)
    return _con_etiqueta(documento)


@router.get("/documentos/{documento_id}/fichero")
def descargar(
    documento_id: int, explotacion: ExplotacionActual, db: Db
) -> FileResponse:
    """El papel, tal y como se subió."""
    documento = obtener_de_la_explotacion(
        db, models.DocumentoAnexo, documento_id, explotacion.id
    )
    if not documento.fichero_ruta:
        raise HTTPException(status_code=404, detail=textos.DOCUMENTOS["sin_fichero"])
    ruta = adjuntos.ruta_segura(documento.fichero_ruta)
    return FileResponse(
        ruta,
        media_type=documento.fichero_tipo or "application/octet-stream",
        filename=documento.fichero_nombre or ruta.name,
    )


@router.post("/documentos/{documento_id}/anular", response_model=DocumentoSalida)
def anular(
    documento_id: int,
    datos: dict,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> DocumentoSalida:
    """Anula el apunte de un papel. El motivo es obligatorio y el fichero no se borra.

    Decisión: **el fichero se queda**. Lo que se anula es el apunte —«esto no era lo que yo
    pensaba»—, y el papel sigue siendo el papel: aquí el fichero **es** la prueba de lo que había, y
    borrarlo sería destruirla, que es justo lo contrario de lo que hace un cuaderno.

    Esa es la diferencia con `borrar` (ronda 94), y las dos hacen falta: **anular** es «este papel no
    era lo que yo pensaba» —el papel existe y se queda, con su motivo escrito— y **borrar** es «esto
    no debería estar aquí» —el agricultor se ha equivocado al subirlo, y entonces el fichero se va
    con la fila, porque dejarlo en el disco es basura que nadie va a limpiar—.
    """
    documento = obtener_de_la_explotacion(
        db, models.DocumentoAnexo, documento_id, explotacion.id
    )
    motivo = str((datos or {}).get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=422, detail=textos.DOCUMENTOS["falta_el_motivo"])
    documento.anulado = True
    documento.motivo_anulacion = motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="documento",
            entidad_id=documento.id,
            accion="anular",
            datos={"motivo": motivo},
        )
    )
    db.commit()
    db.refresh(documento)
    return _con_etiqueta(documento)


@router.get("/documentos/listado")
def listado(explotacion: ExplotacionActual, db: Db) -> dict:
    """El índice de los papeles, en texto plano, para pegarlo en un correo o imprimirlo.

    Mismo motivo que el listado de números de un análisis: el uso real es mandarle al técnico o al
    gestor «esto es lo que tengo». Un texto se pega en cualquier sitio; una pantalla, no.
    """
    documentos = list(
        db.scalars(
            select(models.DocumentoAnexo)
            .where(
                models.DocumentoAnexo.explotacion_id == explotacion.id,
                models.DocumentoAnexo.anulado.is_(False),
            )
            .order_by(models.DocumentoAnexo.carpeta, models.DocumentoAnexo.fecha)
        )
    )
    lineas = [textos.DOCUMENTOS["titulo"].upper()]
    carpeta_actual = None
    for documento in documentos:
        carpeta = documento.carpeta or CARPETA_POR_DEFECTO
        if carpeta != carpeta_actual:
            lineas.append("")
            lineas.append(f"--- {carpeta} ---")
            carpeta_actual = carpeta
        partes = [documento.titulo]
        if documento.fecha:
            partes.append(legal.formatea_fecha(documento.fecha))
        partes.append(catalogos.etiqueta_documento(documento.tipo))
        if documento.quien:
            partes.append(documento.quien)
        partes.append("con fichero" if documento.fichero_ruta else "sin fichero")
        lineas.append(" · ".join(partes))
    if not documentos:
        lineas.append(textos.DOCUMENTOS["sin_papeles"])
    return {
        "titulo": textos.DOCUMENTOS["titulo"],
        "lineas": lineas,
        "texto": "\n".join(lineas),
        "cuantos": len(documentos),
    }
