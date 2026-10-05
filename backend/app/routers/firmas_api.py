"""La firma del cuaderno, por la API.

El agricultor firma con AutoFirma, que es el programa que usa para todo lo demás de la
administración. Por eso el servidor no firma nada: **prepara el fichero, lo entrega,
recibe la firma, la comprueba y guarda de qué fichero era**.

Decisión de seguridad: **para firmar hace falta haber entrado con el certificado**. Es
la única forma honesta de saber quién firma. Si se pudiera firmar con correo y clave,
la firma no diría nada de nadie, que es justo lo contrario de para lo que sirve.

Y desde la ronda 12, cuando llega el fichero de firma **se mira dentro** (`app/cades.py`).
Antes se guardaba sin abrirlo, y eso dejaba pasar cualquier cosa. Ahora hay tres finales
posibles, y el del medio es el importante:

1. **La firma se comprueba y es de este cuaderno y de este agricultor** → se guarda y queda
   marcada como comprobada.
2. **No se ha podido comprobar** (una firma de curva elíptica, por ejemplo) → **se guarda
   igual**, marcada como no comprobada y diciendo por qué. No comprobar algo no es motivo para
   dejar a un agricultor sin firmar su cuaderno.
3. **Se comprueba y NO es de este cuaderno, o es de otro certificado** → **se rechaza**. Aquí no
   hay duda: guardar eso sería dejar creer que el cuaderno está respaldado cuando no lo está.
"""

from __future__ import annotations

import base64
import datetime as dt

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from .. import cades, catalogos, certificados, firma as firma_util, legal, models, textos
from ..deps import Db, ExplotacionActual, obtener_de_la_explotacion
from ..schemas import EstadoFirma, FirmaEntrada, FirmaSalida

router = APIRouter(prefix="/api", tags=["firmas"])

ENTIDADES = ("cuaderno", "tratamiento", "fertilizacion", "labor")


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------


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


def _parcela(db, parcela_id: int | None) -> str:
    if parcela_id is None:
        return "varias parcelas"
    parcela = db.get(models.Parcela, parcela_id)
    return parcela.alias if parcela else ""


def _nombre_de(db, modelo, objeto_id, campo: str) -> str:
    if objeto_id is None:
        return ""
    objeto = db.get(modelo, objeto_id)
    return getattr(objeto, campo, "") if objeto else ""


def _tratamientos(db, explotacion, campana_id):
    return list(
        db.scalars(
            select(models.TratamientoFitosanitario)
            .where(
                models.TratamientoFitosanitario.explotacion_id == explotacion.id,
                models.TratamientoFitosanitario.campana_id == campana_id,
            )
            # El orden importa: si cambia, el fichero cambia y la firma deja de cuadrar.
            .order_by(
                models.TratamientoFitosanitario.fecha, models.TratamientoFitosanitario.id
            )
        )
    )


def _fertilizaciones(db, explotacion, campana_id):
    return list(
        db.scalars(
            select(models.RegistroFertilizacion)
            .where(
                models.RegistroFertilizacion.explotacion_id == explotacion.id,
                models.RegistroFertilizacion.campana_id == campana_id,
            )
            .order_by(
                models.RegistroFertilizacion.fecha, models.RegistroFertilizacion.id
            )
        )
    )


def _labores(db, explotacion, campana_id):
    return list(
        db.scalars(
            select(models.Labor)
            .where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.campana_id == campana_id,
            )
            .order_by(models.Labor.fecha, models.Labor.id)
        )
    )


def _texto_del_cuaderno(db, explotacion, campana) -> str:
    tratamientos = [
        firma_util.campos_de_un_tratamiento(
            registro,
            _parcela(db, registro.parcela_id),
            _nombre_de(db, models.Aplicador, registro.aplicador_id, "nombre"),
            _nombre_de(db, models.EquipoAplicacion, registro.equipo_id, "nombre"),
            _nombre_de(db, models.Instalacion, registro.instalacion_id, "alias"),
        )
        for registro in _tratamientos(db, explotacion, campana.id)
    ]
    abonos = [
        firma_util.campos_de_un_abono(registro, _parcela(db, registro.parcela_id))
        for registro in _fertilizaciones(db, explotacion, campana.id)
    ]
    labores = [
        firma_util.campos_de_una_labor(
            registro,
            _parcela(db, registro.parcela_id),
            catalogos.ETIQUETA_LABOR.get(registro.tipo, registro.tipo),
        )
        for registro in _labores(db, explotacion, campana.id)
    ]

    return firma_util.texto_del_cuaderno(
        explotacion={
            "Nombre": explotacion.nombre,
            "NIF": explotacion.nif,
            "Número de la finca": explotacion.codigo_siex,
            "Provincia": explotacion.provincia,
            "Pueblo": explotacion.municipio,
            "En ecológico": explotacion.produccion_ecologica,
        },
        campana={"Año": campana.anio, "Empieza": campana.fecha_inicio, "Termina": campana.fecha_fin},
        tratamientos=tratamientos,
        fertilizaciones=abonos,
        labores=labores,
    )


def _texto_de_un_registro(db, explotacion, entidad: str, entidad_id: int) -> str:
    if entidad == "tratamiento":
        registro = obtener_de_la_explotacion(
            db, models.TratamientoFitosanitario, entidad_id, explotacion.id
        )
        campos = firma_util.campos_de_un_tratamiento(
            registro,
            _parcela(db, registro.parcela_id),
            _nombre_de(db, models.Aplicador, registro.aplicador_id, "nombre"),
            _nombre_de(db, models.EquipoAplicacion, registro.equipo_id, "nombre"),
            _nombre_de(db, models.Instalacion, registro.instalacion_id, "alias"),
        )
        return firma_util.texto_de_un_registro("PRODUCTO APLICADO", campos)

    if entidad == "fertilizacion":
        registro = obtener_de_la_explotacion(
            db, models.RegistroFertilizacion, entidad_id, explotacion.id
        )
        campos = firma_util.campos_de_un_abono(registro, _parcela(db, registro.parcela_id))
        return firma_util.texto_de_un_registro("ABONO", campos)

    registro = obtener_de_la_explotacion(db, models.Labor, entidad_id, explotacion.id)
    campos = firma_util.campos_de_una_labor(
        registro,
        _parcela(db, registro.parcela_id),
        catalogos.ETIQUETA_LABOR.get(registro.tipo, registro.tipo),
    )
    return firma_util.texto_de_un_registro("LABOR", campos)


def _comprueba_entidad(entidad: str) -> None:
    if entidad not in ENTIDADES:
        raise HTTPException(
            status_code=422,
            detail=f"Eso no se puede firmar. Se puede firmar: {', '.join(ENTIDADES)}.",
        )


def _texto_y_huella(db, explotacion, entidad: str, entidad_id, campana_id) -> tuple[str, str, str, int | None]:
    """Devuelve el texto a firmar, su huella, el nombre del fichero y la campaña."""
    _comprueba_entidad(entidad)
    campana = _campana(db, explotacion, campana_id)

    if entidad == "cuaderno":
        texto = _texto_del_cuaderno(db, explotacion, campana)
        nombre = f"cuaderno_{campana.anio}.txt"
        return texto, firma_util.huella(texto), nombre, campana.id

    if entidad_id is None:
        raise HTTPException(
            status_code=422, detail="Dime qué apunte quieres firmar."
        )
    texto = _texto_de_un_registro(db, explotacion, entidad, entidad_id)
    nombre = f"{entidad}_{entidad_id}.txt"
    return texto, firma_util.huella(texto), nombre, campana.id


def _firma_vigente(db, explotacion, entidad: str, entidad_id, campana_id):
    """La última firma de eso, que es la que cuenta."""
    consulta = select(models.Firma).where(
        models.Firma.explotacion_id == explotacion.id,
        models.Firma.entidad == entidad,
    )
    consulta = (
        consulta.where(models.Firma.campana_id == campana_id)
        if entidad == "cuaderno"
        else consulta.where(models.Firma.entidad_id == entidad_id)
    )
    return db.scalar(consulta.order_by(models.Firma.firmado_en.desc(), models.Firma.id.desc()))


def _puede_firmar(request: Request, explotacion: models.Explotacion) -> bool:
    """Solo puede firmar quien ha entrado con un certificado de esta finca."""
    certificado = certificados.certificado_de_peticion(request)
    if certificado is None or not certificado.nif:
        return False
    return certificados.normaliza_nif(explotacion.nif) == certificado.nif


def _exige_certificado(request: Request, explotacion: models.Explotacion):
    certificado = certificados.certificado_de_peticion(request)
    if certificado is None or not certificado.nif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=textos.FIRMA["no_puede_firmar"]
        )
    if certificados.normaliza_nif(explotacion.nif) != certificado.nif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=textos.FIRMA["no_puede_firmar"]
        )
    return certificado


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get("/firmas/estado", response_model=EstadoFirma)
def estado(
    request: Request,
    explotacion: ExplotacionActual,
    db: Db,
    entidad: str = "cuaderno",
    entidad_id: int | None = None,
    campana_id: int | None = None,
) -> EstadoFirma:
    """¿Está firmado, y sigue valiendo la firma?"""
    _texto, huella_actual, nombre, campana_de_la_firma = _texto_y_huella(
        db, explotacion, entidad, entidad_id, campana_id
    )
    firmas = _firma_vigente(db, explotacion, entidad, entidad_id, campana_de_la_firma)

    situacion = firma_util.estado_de_la_firma(firmas, huella_actual)
    if situacion == firma_util.ESTADO_SIN_FIRMAR:
        mensaje = textos.FIRMA["sin_firmar"]
    elif situacion == firma_util.ESTADO_FIRMADO:
        mensaje = textos.FIRMA["firmado"].format(
            fecha=legal.formatea_fecha(firmas.firmado_en.date()),
            nombre=firmas.firmante_nombre or firmas.firmante_nif,
        )
    else:
        mensaje = textos.FIRMA["cambiado"].format(
            fecha=legal.formatea_fecha(firmas.firmado_en.date())
        )

    return EstadoFirma(
        estado=situacion,
        huella=huella_actual,
        puede_firmar=_puede_firmar(request, explotacion),
        nombre_del_fichero=nombre,
        firma=FirmaSalida.model_validate(firmas) if firmas else None,
        mensaje=mensaje,
        explicacion=textos.FIRMA["explica"],
    )


@router.get("/firmas/fichero")
def fichero(
    explotacion: ExplotacionActual,
    db: Db,
    entidad: str = "cuaderno",
    entidad_id: int | None = None,
    campana_id: int | None = None,
) -> PlainTextResponse:
    """El fichero que hay que firmar con AutoFirma."""
    texto, _huella, nombre, _campana_id = _texto_y_huella(
        db, explotacion, entidad, entidad_id, campana_id
    )
    return PlainTextResponse(
        texto,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/firmas/preparar")
def preparar(
    request: Request,
    explotacion: ExplotacionActual,
    db: Db,
    entidad: str = "cuaderno",
    entidad_id: int | None = None,
    campana_id: int | None = None,
    sistema: str = "windows",
) -> dict:
    """Todo lo que hace falta para firmar: el fichero, su huella y la orden que hay que ejecutar."""
    texto, huella, nombre, campana_de_la_firma = _texto_y_huella(
        db, explotacion, entidad, entidad_id, campana_id
    )
    return {
        "entidad": entidad,
        "entidad_id": entidad_id,
        "campana_id": campana_de_la_firma,
        "huella": huella,
        "nombre_del_fichero": nombre,
        "comando": firma_util.comando_autofirma(nombre, sistema),
        "formato": firma_util.FORMATO,
        "algoritmo": firma_util.ALGORITMO,
        "contenido": texto,
        "explicacion": textos.FIRMA["explica"],
    }


@router.post("/firmas", response_model=FirmaSalida, status_code=status.HTTP_201_CREATED)
def registrar(
    datos: FirmaEntrada, request: Request, explotacion: ExplotacionActual, db: Db
) -> models.Firma:
    """Guarda la firma que ha devuelto AutoFirma, después de comprobarla.

    Se comprueban dos cosas, y las dos tienen que salir bien:

    1. **Que la huella que se firmó es la del cuaderno de AHORA.** Si no coincide, se rechaza:
       firmar una versión vieja y guardarla como si fuera la de ahora sería dejar creer que el
       cuaderno está respaldado cuando ya no lo está.
    2. **Que el fichero de firma sea de verdad de este cuaderno y de este agricultor.**

    La segunda es la que se añadió en la ronda 12. Antes el fichero se guardaba sin abrirlo, así
    que se podía subir cualquier cosa: un fichero de texto, la firma de otro documento o la firma
    de otro agricultor. Ver `app/cades.py`.
    """
    certificado = _exige_certificado(request, explotacion)

    _texto, huella_actual, _nombre, campana_de_la_firma = _texto_y_huella(
        db, explotacion, datos.entidad, datos.entidad_id, datos.campana_id
    )
    if datos.huella != huella_actual:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=textos.FIRMA["huella_no_cuadra"]
        )

    contenido = datos.contenido
    verificacion: cades.Resultado | None = None
    if contenido:
        try:
            base64.b64decode(contenido, validate=True)
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail="Eso no parece un fichero de firma."
            ) from exc

        # El contenido firmado es el cuaderno tal y como está ahora: es lo que se le entregó al
        # agricultor para que lo firmara, byte a byte. La huella de arriba ya ha dicho que es el
        # mismo, así que aquí se le pasa el texto para que lo compruebe por dentro.
        verificacion = cades.verificar_base64(contenido, _texto.encode("utf-8"))

        if verificacion.esta_tocado:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.FIRMA["firma_no_es_de_este_cuaderno"].format(
                    motivo=verificacion.explicacion
                ),
            )

        # El mismo agricultor: si la firma la hizo otro certificado, no vale. Solo se comprueba
        # cuando el certificado de la firma **dice** su NIF: si no lo dice, no se puede saber, y
        # entonces no se rechaza (no saber no es lo mismo que saber que está mal).
        if (
            verificacion.vale
            and verificacion.firmante_nif
            and certificado.nif
            and verificacion.firmante_nif != certificado.nif
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.FIRMA["firma_de_otro_agricultor"].format(
                    firmante=verificacion.firmante_nombre or verificacion.firmante_nif,
                    nif=certificado.nif,
                ),
            )

    firma = models.Firma(
        explotacion_id=explotacion.id,
        entidad=datos.entidad,
        entidad_id=datos.entidad_id,
        campana_id=campana_de_la_firma,
        huella=datos.huella,
        version_canonica=firma_util.VERSION_CANONICA,
        algoritmo=firma_util.ALGORITMO,
        formato=firma_util.FORMATO,
        firmante_nif=certificado.nif,
        firmante_nombre=certificado.nombre,
        contenido=contenido,
        nombre_del_fichero=datos.nombre_del_fichero,
        # Se pone en verdadero **solo** cuando se ha comprobado de verdad. Si no se ha podido
        # comprobar (o no había fichero que comprobar), se queda en falso y se apunta por qué.
        verificada_criptograficamente=bool(verificacion and verificacion.vale),
        # En esta columna va la explicación **en palabras de agricultor**, porque es la que
        # acaba en su pantalla. El detalle técnico completo va en la auditoría de abajo: cada
        # cosa a quien la puede entender.
        nota_verificacion=(
            verificacion.explicacion
            if verificacion
            else "no se ha mandado el fichero de firma, así que no había nada que comprobar"
        ),
    )
    db.add(firma)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            # **`entidad` es un texto fijo, y `de_que_es` dice de qué se firmó** (02/10/2026). Aquí
            # ponía `f"firma_{datos.entidad}"`, que era correcto —`entidad` del esquema está topada en 40
            # y la columna mide 60, o sea 46 como mucho— pero **no se podía comprobar**: una etiqueta
            # montada con un dato no se puede medir leyendo el código, y la prueba guardiana del rastro
            # (`tests/test_las_etiquetas_del_rastro_caben.py`) lo dice y para. Las otras 33 entidades del
            # rastro son textos fijos que nombran **la clase** de cosa (`factura`, `parcela`…); esto es lo
            # mismo, y lo que decía antes (si la firma era del cuaderno o de un apunte) no se pierde:
            # va en `de_que_es`, que además se lee mejor que un identificador pegado con un guion bajo.
            entidad="firma",
            entidad_id=datos.entidad_id,
            accion="firmar",
            datos={
                "de_que_es": datos.entidad,
                "huella": datos.huella,
                "firmante": certificado.nif,
                "campana_id": campana_de_la_firma,
                # La comprobación de la firma se guarda entera: es lo que permite reconstruir,
                # meses después, qué se miró y qué no cuando se aceptó esta firma.
                "verificacion": verificacion.como_dict() if verificacion else None,
            },
        )
    )
    db.commit()
    db.refresh(firma)
    return firma


@router.get("/firmas", response_model=list[FirmaSalida])
def listar(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> list[models.Firma]:
    """Todas las firmas, de la más nueva a la más vieja.

    Se devuelven todas, incluidas las que ya no cuadran: la historia de las firmas es
    parte de lo que hay que poder enseñar.
    """
    consulta = select(models.Firma).where(models.Firma.explotacion_id == explotacion.id)
    if campana_id is not None:
        consulta = consulta.where(models.Firma.campana_id == campana_id)
    return list(db.scalars(consulta.order_by(models.Firma.firmado_en.desc(), models.Firma.id.desc())))
