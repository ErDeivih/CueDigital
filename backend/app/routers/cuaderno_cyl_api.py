"""Traer las tierras del cuaderno de la Junta (el Cuecyl) al cuaderno del agricultor.

## Por qué existe esto

El agricultor de Castilla y León que lleva su cuaderno en la aplicación de la Junta tiene ahí,
ya escritas, todas sus parcelas: las que declaró en la Solicitud Única, con su polígono, su
parcela, su recinto, su uso, su cultivo, su ecorregimen y sus hectáreas. En el cuaderno real de
David (campaña 2026) son **54 líneas y 51 tierras distintas**.

Pedirle que las teclee otra vez sería una tontería y, peor, una fuente de errores: un número
cambiado y la tierra del cuaderno deja de ser la suya. Así que este apartado lee el fichero que
descarga de la Junta y da de alta sus tierras aquí.

## Las decisiones (y por qué)

1. **Primero se lee y se enseña, y solo después se apunta.** Son dos puertas: `/leer` no escribe
   nada y `/importar` escribe. Así el agricultor ve «esto es lo que trae tu cuaderno» —cuántas
   tierras, cuántas hectáreas, qué pueblos, qué cultivos— **antes** de que le aparezcan 51
   parcelas en la lista. Dar de alta 51 parcelas sin avisar no es una función, es una sorpresa.
2. **Se puede subir las veces que haga falta y no se duplica nada.** Es la prueba de verdad de
   que el emparejamiento está bien hecho: si el agricultor sube el cuaderno de 2026 dos veces
   (o el de 2025 y luego el de 2026), la segunda vez no le salen tierras repetidas.
3. **Una tierra que ya estaba y no tenía cultivo, se queda con el cultivo del cuaderno.** Es el
   caso del que apuntó sus parcelas por su referencia o tocando el mapa y todavía no ha dicho qué
   siembra: el cuaderno lo dice, así que se aprovecha en vez de crear una parcela nueva al lado.
4. **Una tierra que el papel parte en trozos se apunta en trozos.** El cuaderno oficial escribe
   una línea por cultivo y superficie declarada: en el de 2026, el recinto 1 de la parcela 24 del
   polígono 507 sale tres veces (barbecho 4,44 ha, avena 0,46 ha y avena 0,13 ha). Aquí se apunta
   igual, porque es lo que de verdad hay: si se juntara todo en una parcela de 5,07 ha, el
   programa dejaría echar producto para 5 hectáreas de avena cuando solo hay 0,13.
5. **La superficie de la tierra es la que se cultiva; la del recinto se guarda aparte.** La hoja
   2.1 del cuaderno pide las dos («Superficie SIGPAC» y «Superficie Cultivada») y no son lo
   mismo. Para las dosis manda la cultivada; la del recinto se queda en
   `Parcela.superficie_sigpac_ha` para poder rellenar el cuaderno.
6. **Lo que ya está escrito no se pisa.** De los datos del titular solo se rellenan los huecos:
   si el agricultor escribió su nombre de una manera, se queda como él lo escribió. Y una tierra
   que ya tiene cultivo declarado en esa campaña **no** se cambia por lo que diga el papel.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select

from .. import catalogos, cuaderno_cyl, cuaderno_cyl_exportar as exportar, models, textos
from ..deps import Db, ExplotacionActual
from ..schemas import (
    CuadernoLeidoSalida,
    ImportacionDelCuadernoSalida,
    LineaDeCuadernoSalida,
)

router = APIRouter(prefix="/api/cuaderno-cyl", tags=["cuaderno de la Junta"])

# El cuaderno de la Junta es un libro de cálculo (xlsx). Los tipos que se aceptan son los mismos
# que deja subir el navegador al elegir un fichero de Excel, y se comprueban por la extensión y
# por el contenido, no por lo que diga el navegador.
TIPOS = (".xlsx", ".xlsm")

# Cuántas líneas se devuelven en la vista previa. El cuaderno de una explotación grande puede
# traer cientos de líneas, y al móvil no le hace falta el listado entero para enseñar el resumen:
# lo que importa son los números de arriba y los avisos.
MAXIMO_DE_LINEAS_EN_LA_VISTA = 400


def _linea_como_salida(linea: cuaderno_cyl.LineaDeParcela) -> LineaDeCuadernoSalida:
    return LineaDeCuadernoSalida(
        orden=linea.orden,
        ref_sigpac=linea.ref_sigpac,
        municipio=linea.municipio_nombre,
        uso_sigpac=linea.uso_sigpac,
        superficie_sigpac_ha=linea.superficie_sigpac_ha,
        superficie_cultivada_ha=linea.superficie_cultivada_ha,
        especie=linea.especie,
        variedad=linea.variedad or None,
        ecorregimen=linea.ecorregimen or None,
        sistema=linea.sistema,
        zona_nitratos=linea.zona_nitratos,
    )


async def _leer_lo_que_han_subido(fichero: UploadFile) -> cuaderno_cyl.CuadernoLeido:
    """Lee el fichero subido y devuelve el cuaderno, o un 422 que se entiende.

    El mensaje de error se enseña tal cual en la pantalla, así que se cuenta en castellano y sin
    palabras raras: lo que ha pasado es que ese fichero no es el cuaderno de la Junta.
    """
    nombre = (fichero.filename or "").lower()
    if not nombre.endswith(TIPOS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.CUADERNO_CYL["no_se_pudo"],
        )
    contenido = await fichero.read()
    try:
        return cuaderno_cyl.leer_cuaderno(contenido)
    except cuaderno_cyl.CuadernoIlegible as problema:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(problema)
        ) from problema


def _respuesta_de_la_lectura(leido: cuaderno_cyl.CuadernoLeido) -> CuadernoLeidoSalida:
    generales = leido.generales
    return CuadernoLeidoSalida(
        anio=leido.anio,
        titular=generales.nombre,
        nif=generales.nif,
        registro_autonomico=generales.registro_autonomico or None,
        localidad=generales.localidad or None,
        resumen=leido.resumen(),
        lineas=[
            _linea_como_salida(linea)
            for linea in leido.parcelas[:MAXIMO_DE_LINEAS_EN_LA_VISTA]
        ],
    )


@router.post("/leer", response_model=CuadernoLeidoSalida)
async def leer_el_cuaderno(
    explotacion: ExplotacionActual, fichero: UploadFile = File(...)
) -> CuadernoLeidoSalida:
    """Mira el cuaderno y cuenta lo que trae. **No apunta nada.**

    Va en dos pasos a propósito (leer y luego importar): el agricultor tiene que poder ver qué
    va a pasar antes de que pase.
    """
    leido = await _leer_lo_que_han_subido(fichero)
    return _respuesta_de_la_lectura(leido)


def _la_campana(db, explotacion, anio: int | None) -> models.Campana:
    """La campaña del cuaderno, o la del año en curso si el cuaderno no dice de qué año es.

    Si no existe se crea, con el mismo criterio que la campaña que se crea sola al darse de alta
    (del 1 de enero al 31 de diciembre). Un cuaderno de otra campaña no se puede apuntar sin su
    año: el cultivo de una tierra es por campaña, y sin campaña no se sabe de qué año es.
    """
    anio = anio or dt.date.today().year
    campana = db.scalar(
        select(models.Campana).where(
            models.Campana.explotacion_id == explotacion.id,
            models.Campana.anio == anio,
        )
    )
    if campana is not None:
        return campana
    campana = models.Campana(
        explotacion_id=explotacion.id,
        anio=anio,
        fecha_inicio=dt.date(anio, 1, 1),
        fecha_fin=dt.date(anio, 12, 31),
    )
    db.add(campana)
    db.flush()
    return campana


# Los datos del titular que se rellenan desde la hoja 1.1, con el nombre que se enseña en el
# resumen. Se rellenan **solo si están vacíos**: lo que el agricultor ya había escrito no se toca.
CAMPOS_DEL_TITULAR = {
    "registro_autonomico": "nº de registro de la explotación",
    "registro_nacional": "nº de registro nacional",
    "direccion": "dirección",
    "localidad": "localidad",
    "codigo_postal": "código postal",
    "provincia": "provincia",
    "telefono": "teléfono",
    "correo": "correo",
}


def _rellenar_los_huecos_del_titular(db, explotacion, generales) -> list[str]:
    """Copia los datos del titular del cuaderno **solo donde no había nada**.

    Se devuelven los nombres de los campos que se han rellenado, para poder decirlo en pantalla.
    Un dato que el agricultor ya había escrito no se pisa nunca: si él puso su nombre de una
    manera y el cuaderno lo pone de otra, manda la suya.

    **El nombre y el NIF no se copian ni aunque estén vacíos**, y eso es a propósito: el NIF es lo
    que identifica al titular delante de la administración y lo que se compara con el certificado
    digital al entrar. Además, el cuaderno de la Junta lo escribe **con el formato de su registro**
    («0-70922320-A», con un cero delante que un DNI no lleva), así que copiarlo tal cual dejaría un
    NIF que no coincidiría con el del certificado. Si falta, se pide en la pantalla de la finca.
    """
    del_cuaderno = {
        "registro_autonomico": generales.registro_autonomico,
        "registro_nacional": generales.registro_nacional,
        "direccion": generales.direccion,
        "localidad": generales.localidad,
        "codigo_postal": generales.codigo_postal,
        "provincia": generales.provincia,
        # El cuaderno trae el móvil (y a veces un fijo): si tiene los dos, se guardan juntos,
        # porque la finca tiene un solo teléfono de contacto y separarlos sería una columna más
        # para nada.
        "telefono": " / ".join(
            numero for numero in (generales.telefono_movil, generales.telefono_fijo) if numero
        ),
        "correo": generales.correo,
    }
    rellenados: list[str] = []
    for campo, valor in del_cuaderno.items():
        if not valor:
            continue
        if getattr(explotacion, campo, None):
            continue
        setattr(explotacion, campo, valor)
        rellenados.append(CAMPOS_DEL_TITULAR[campo])
    if rellenados:
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                entidad="explotacion",
                entidad_id=explotacion.id,
                accion="rellenar_desde_el_cuaderno_de_la_junta",
                datos={campo: getattr(explotacion, campo) for campo in del_cuaderno},
            )
        )
    return rellenados


def _clave_de_una_linea(linea: cuaderno_cyl.LineaDeParcela) -> tuple:
    """Con qué se reconoce que una línea del cuaderno ya está apuntada.

    Son tres cosas juntas, y las tres hacen falta: **la tierra** (su referencia del SIGPAC), **lo
    que se siembra** y **cuántas hectáreas**. Con la referencia sola, las tres líneas del recinto
    partido (barbecho y dos trozos de avena) se confundirían con una sola; con la referencia y el
    cultivo, los dos trozos de avena del mismo recinto se confundirían entre ellos.
    """
    superficie = linea.superficie_cultivada_ha
    return (
        linea.ref_sigpac,
        linea.especie.strip().lower(),
        (linea.variedad or "").strip().lower(),
        round(superficie, 4) if superficie is not None else None,
    )


def _nombre_para_la_tierra(linea: cuaderno_cyl.LineaDeParcela) -> str:
    """Cómo se llama la tierra recién traída, sin inventarse ningún nombre.

    Se usa lo que el agricultor ya tiene delante en el papel del SIGPAC y en el cuaderno: el
    polígono, la parcela, el recinto y lo que hay sembrado. Un nombre inventado («El Prado») sería
    peor: no lo reconocería, y él puede cambiarlo después por el que use en casa.

    Cuando la misma tierra aparece en varias líneas (trozos), se añaden las hectáreas: es lo
    único que distingue un trozo de otro, y es un dato del cuaderno, no una invención.
    """
    nombre = f"{linea.referencia.poligono}/{linea.referencia.parcela}-{linea.referencia.recinto}"
    cultivo = linea.especie.strip()
    if cultivo:
        nombre = f"{nombre} {cultivo}"
    if linea.superficie_cultivada_ha is not None:
        nombre = f"{nombre} ({linea.superficie_cultivada_ha:g} ha)"
    return nombre[:120]


def _apuntar_la_linea(db, explotacion, campana, linea, parcela: models.Parcela | None) -> str:
    """Da de alta una línea del cuaderno, o le pone el cultivo a una tierra que ya estaba.

    Devuelve qué ha pasado: `"creada"` o `"con_cultivo"`.
    """
    if parcela is None:
        # El **código del INE** del pueblo sale del propio cuaderno: su columna del término
        # municipal trae el código de 3 cifras, y el de la provincia, 2. Juntos son los 5 del INE
        # (el código de municipio del SIGPAC es el mismo del INE: eso ya se comprobó con el listado
        # oficial en `tests/test_parcelas_por_codigos.py`). Sin este código, el cuaderno que se saca
        # después saldría sin el término municipal, que es lo primero que se mira.
        codigo_ine = None
        if linea.referencia.provincia and linea.municipio_codigo:
            codigo_ine = f"{linea.referencia.provincia:02d}{linea.municipio_codigo:03d}"
        del_ine = catalogos.municipio_por_codigo_ine(codigo_ine) if codigo_ine else None
        parcela = models.Parcela(
            explotacion_id=explotacion.id,
            alias=_nombre_para_la_tierra(linea),
            ref_sigpac=linea.ref_sigpac,
            provincia=(del_ine.provincia if del_ine else explotacion.provincia) or "",
            municipio=linea.municipio_nombre or (del_ine.nombre if del_ine else explotacion.municipio) or "",
            codigo_ine=codigo_ine,
            agregado=linea.referencia.agregado,
            zona=linea.referencia.zona,
            poligono=linea.referencia.poligono,
            numero_parcela=linea.referencia.parcela,
            numero_recinto=linea.referencia.recinto,
            # La superficie que se cultiva y se trata. La del recinto entero va aparte.
            #
            # **Y si el papel no la trae, se queda en blanco: no se pone un cero.** Antes esta línea
            # era `linea.superficie_cultivada_ha or 0.0`, y un cero ahí no era un número feo en una
            # lista: la tierra quedaba dada de alta con «0,00 ha» y, como todas las comprobaciones de
            # superficie comparan contra ella, **dejaba de poder tratarse ni abonarse** —cualquier
            # superficie la superaba—. Y no era un caso raro: la plantilla de la Junta deja esa
            # casilla vacía en varias tierras (A7 de `docs/T02_VALORES_POR_DEFECTO.md`). En blanco
            # es «no lo sé», que es lo mismo que ya se hace con la superficie del recinto, aquí
            # debajo: dos criterios distintos para el mismo objeto era justo el defecto.
            superficie_ha=linea.superficie_cultivada_ha,
            superficie_oficial=False,
            superficie_sigpac_ha=linea.superficie_sigpac_ha,
            uso_sigpac=linea.uso_sigpac or None,
            # El cuaderno de la Junta no dice si el agua de riego es de pozo, pero sí dice si la
            # tierra es de secano o de regadío («S» o «R» en su casilla), así que de ahí sí se
            # rellena. **Y cuando el papel no lo dice, se queda en «no lo sé»** (A10 de
            # `docs/T02_VALORES_POR_DEFECTO.md`): antes esta línea era `linea.sistema or "secano"`, y
            # eso **declaraba de secano** una tierra de regadío cuyo renglón venía en blanco —el
            # agricultor la veía de secano y el abonado se comparaba contra el límite que no es—.
            # En blanco es «no lo sé», igual que la superficie de aquí arriba.
            sistema=linea.sistema or None,
            # La casilla «parcela ubicada en zona nitratos» del cuaderno: puesta está en zona,
            # en blanco no se sabe (nunca «no está», que sería inventarse una comprobación).
            zona_vulnerable_nitratos=linea.zona_nitratos,
        )
        db.add(parcela)
        db.flush()
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                entidad="parcela",
                accion="crear_desde_el_cuaderno_de_la_junta",
                datos={
                    "ref_sigpac": parcela.ref_sigpac,
                    "superficie_ha": parcela.superficie_ha,
                    "superficie_sigpac_ha": parcela.superficie_sigpac_ha,
                    "orden_en_el_cuaderno": linea.orden,
                },
            )
        )
        hecho = "creada"
    else:
        hecho = "con_cultivo"

    db.add(
        models.ParcelaCultivo(
            explotacion_id=explotacion.id,
            parcela_id=parcela.id,
            campana_id=campana.id,
            especie=linea.especie.strip(),
            variedad=linea.variedad or None,
            # El sistema del renglón del papel manda; si el papel no lo dice, se copia el de la tierra
            # cuando se conoce (es el mismo dato, mirado desde la tierra) y si tampoco se conoce se
            # queda en «no lo sé». Las dos cosas pueden ser `None` desde A10.
            sistema=linea.sistema or parcela.sistema,
            fecha_inicio=linea.fecha_inicio,
            fecha_fin=linea.fecha_fin,
            ecorregimen=linea.ecorregimen or None,
            superficie_cultivada_ha=linea.superficie_cultivada_ha,
        )
    )
    return hecho


@router.post("/importar", response_model=ImportacionDelCuadernoSalida)
async def importar_el_cuaderno(
    explotacion: ExplotacionActual, db: Db, fichero: UploadFile = File(...)
) -> ImportacionDelCuadernoSalida:
    """Apunta las tierras del cuaderno. Se puede repetir: no duplica nada."""
    leido = await _leer_lo_que_han_subido(fichero)
    campana = _la_campana(db, explotacion, leido.anio)
    rellenados = _rellenar_los_huecos_del_titular(db, explotacion, leido.generales)

    # Lo que ya está apuntado, en el idioma de las líneas del cuaderno: (referencia, cultivo,
    # hectáreas). Se mira de una vez en lugar de preguntar por cada línea, que con 54 líneas son
    # 54 consultas y no hace falta ninguna.
    existentes = list(
        db.scalars(
            select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
        )
    )
    cultivos_de_la_campana = {
        cultivo.parcela_id: cultivo
        for cultivo in db.scalars(
            select(models.ParcelaCultivo).where(
                models.ParcelaCultivo.explotacion_id == explotacion.id,
                models.ParcelaCultivo.campana_id == campana.id,
            )
        )
    }
    # De cada tierra se saca su «clave»: por la superficie cultivada si el cultivo la tiene
    # apuntada (una línea del cuaderno) y, si no, por la superficie de la tierra.
    claves_apuntadas: set[tuple] = set()
    for parcela in existentes:
        cultivo = cultivos_de_la_campana.get(parcela.id)
        if cultivo is None:
            continue
        superficie = (
            cultivo.superficie_cultivada_ha
            if cultivo.superficie_cultivada_ha is not None
            else parcela.superficie_ha
        )
        claves_apuntadas.add(
            (
                parcela.ref_sigpac or "",
                (cultivo.especie or "").strip().lower(),
                (cultivo.variedad or "").strip().lower(),
                round(superficie, 4) if superficie is not None else None,
            )
        )

    # Y las tierras que ya están apuntadas **sin cultivo** en esta campaña: son las que pueden
    # recibir el cultivo del cuaderno en vez de crear una parcela nueva al lado. Solo se ofrecen
    # si esa referencia aparece **una sola vez** en el cuaderno: si el papel la parte en trozos,
    # la tierra que ya había es el recinto entero y no uno de los trozos.
    cuantas_veces_esa_tierra = {}
    for linea in leido.parcelas:
        cuantas_veces_esa_tierra[linea.ref_sigpac] = (
            cuantas_veces_esa_tierra.get(linea.ref_sigpac, 0) + 1
        )
    libre_por_referencia: dict[str, models.Parcela] = {}
    for parcela in existentes:
        if parcela.id in cultivos_de_la_campana:
            continue
        referencia = parcela.ref_sigpac or ""
        if cuantas_veces_esa_tierra.get(referencia, 0) == 1:
            libre_por_referencia.setdefault(referencia, parcela)

    creadas = 0
    con_cultivo = 0
    ya_estaban = 0

    for linea in leido.parcelas:
        if _clave_de_una_linea(linea) in claves_apuntadas:
            ya_estaban += 1
            continue
        libre = libre_por_referencia.pop(linea.ref_sigpac, None)
        hecho = _apuntar_la_linea(db, explotacion, campana, linea, libre)
        if hecho == "creada":
            creadas += 1
        else:
            con_cultivo += 1
        claves_apuntadas.add(_clave_de_una_linea(linea))

    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="explotacion",
            entidad_id=explotacion.id,
            accion="traer_tierras_del_cuaderno_de_la_junta",
            datos={
                "campana": campana.anio,
                "lineas_leidas": leido.lineas_en_el_papel,
                "creadas": creadas,
                "con_cultivo_puesto": con_cultivo,
                "ya_estaban": ya_estaban,
                "datos_del_titular_rellenados": rellenados,
            },
        )
    )
    db.commit()

    avisos = list(leido.avisos)
    # Las líneas que se leyeron pero no se han apuntado son las que no se pudieron identificar
    # (sin polígono, sin parcela o sin recinto): la lectura ya ha dicho cuáles son, y aquí se
    # cuenta para que los números del resumen cuadren.
    sin_apuntar = len(leido.lineas_ilegibles)

    return ImportacionDelCuadernoSalida(
        anio=campana.anio,
        campana_id=campana.id,
        creadas=creadas,
        con_cultivo=con_cultivo,
        ya_estaban=ya_estaban,
        sin_apuntar=sin_apuntar,
        lineas_leidas=leido.lineas_en_el_papel,
        tierras_en_el_cuaderno=leido.tierras,
        hectareas_declaradas=leido.hectareas_declaradas,
        titular_rellenado=rellenados,
        avisos=avisos,
    )


@router.get("/estado")
def estado_del_cuaderno_de_la_junta() -> dict:
    """Lo que la pantalla necesita para explicarse: los textos y de dónde se descarga."""
    return {
        "textos": textos.CUADERNO_CYL,
        "se_puede": True,
        "de_donde": (
            "El cuaderno se descarga de la aplicación de la Junta (Cuecyl), en "
            "https://particulares.ayg.jcyl.es, entrando con el certificado digital del titular."
        ),
        "tipos_de_fichero": list(TIPOS),
    }


@router.get("/hojas")
def las_hojas_del_cuaderno() -> dict:
    """Las 25 hojas del cuaderno oficial, con su nombre y qué son.

    Se sirve para que la pantalla pueda contar qué trae el cuaderno sin llevar la lista escrita en el
    JavaScript: si la Junta añade una hoja, se añade aquí y ya está.
    """
    return {
        "hojas": [
            {"nombre": nombre, "titulo": exportar.TITULOS.get(nombre, nombre)}
            for nombre in exportar.HOJAS
        ]
    }


@router.get("/que-falta")
def lo_que_le_falta_al_cuaderno(explotacion: ExplotacionActual, db: Db) -> dict:
    """Qué datos pide el cuaderno y no están puestos, con dónde se ponen.

    **Esto es lo que contesta a «¿qué me falta para tener el cuaderno entero?»**, y sale de comparar
    el cuaderno oficial con lo que el agricultor tiene apuntado: no es una lista escrita a mano, es
    lo que de verdad falta. Se puede mirar sin sacar el fichero.
    """
    campana = _la_campana(db, explotacion, None)
    escrito = exportar.escribe_el_cuaderno(db, explotacion, campana)
    return escrito.resumen()


@router.get("/exportar")
def sacar_el_cuaderno(explotacion: ExplotacionActual, db: Db) -> Response:
    """Saca el cuaderno de la Junta relleno con los datos del agricultor, para descargarlo.

    El fichero se escribe con las 25 hojas del cuaderno oficial, sus cabeceras y sus columnas, y con
    lo que el agricultor tiene apuntado. Lo que no esté puesto sale **en blanco** (no con un cero ni
    con un dato inventado), y la pantalla dice qué falta antes de descargarlo.
    """
    campana = _la_campana(db, explotacion, None)
    escrito = exportar.escribe_el_cuaderno(db, explotacion, campana)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="explotacion",
            entidad_id=explotacion.id,
            accion="sacar_el_cuaderno_de_la_junta",
            datos={"anio": escrito.anio, "hojas_con_datos": escrito.hojas_con_datos},
        )
    )
    db.commit()
    return Response(
        content=escrito.contenido,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{exportar.nombre_del_fichero(explotacion, campana)}"'
            )
        },
    )
