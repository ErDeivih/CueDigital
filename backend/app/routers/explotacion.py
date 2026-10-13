"""Mi finca y las campañas."""

from __future__ import annotations
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .. import certificados, correcciones, models, textos
from ..deps import PuedeVerLoEconomico, Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import CampanaCorreccion, CampanaEntrada, CampanaSalida, ExplotacionSalida

router = APIRouter(prefix="/api", tags=["finca"])


@router.get("/mi-finca", response_model=ExplotacionSalida)
def mi_finca(explotacion: ExplotacionActual) -> models.Explotacion:
    return explotacion


@router.put("/mi-finca", response_model=ExplotacionSalida)
def actualizar_mi_finca(
    datos: dict, explotacion: ExplotacionActual, db: Db
) -> models.Explotacion:
    permitidos = {
        "nombre",
        "nif",
        "codigo_siex",
        "ccaa",
        "provincia",
        "municipio",
        "produccion_ecologica",
        # Los datos de la portada del cuaderno de la Junta (hoja 1.1). **Faltaban aquí**, y era un
        # fallo de los de siempre: el modelo tenía las columnas, la pantalla las preguntaba… y este
        # endpoint las rechazaba con un «no se pueden cambiar estos datos». O sea que no había forma
        # de rellenar la portada del cuaderno desde el programa.
        "registro_nacional",
        "registro_autonomico",
        "direccion",
        "localidad",
        "codigo_postal",
        "telefono",
        "correo",
    }
    desconocidos = set(datos) - permitidos
    if desconocidos:
        raise HTTPException(
            status_code=422,
            detail=f"No se pueden cambiar estos datos: {', '.join(sorted(desconocidos))}",
        )
    for campo, valor in datos.items():
        # El NIF se guarda normalizado, igual que al darse de alta: es lo que después
        # se compara con el del certificado digital.
        setattr(explotacion, campo, certificados.normaliza_nif(valor) if campo == "nif" else valor)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="explotacion",
            entidad_id=explotacion.id,
            accion="actualizar",
            datos=datos,
        )
    )
    db.commit()
    return explotacion


@router.get("/campanas", response_model=list[CampanaSalida])
def listar_campanas(explotacion: ExplotacionActual, db: Db) -> list[CampanaSalida]:
    """Los años del cuaderno, del más nuevo al más viejo, **cada uno con lo que tiene dentro**.

    POR QUÉ SE CUENTA AQUÍ (ronda 93). El agricultor puede corregir y borrar un año, y **un año con cosas
    dentro no se borra** (contesta 409 con cuántas hay). Sin este número en la lista, la pantalla le
    ofrecería un botón de borrar que falla y no sabría por qué hasta pulsarlo; con él, se le dice antes
    («aquí dentro hay 42 cosas») y la pantalla decide no ofrecer lo que no se puede hacer. La cuenta es la
    misma función que usa el borrado (`_cuantas_cosas_hay_dentro`), así que **lo que dice la pantalla y lo
    que dice el servidor al negarse no pueden contradecirse**.

    **Y desde el 30/09/2026 se manda además el desglose** (`apuntes`, `tierras_con_cultivo`, `otras_cosas`):
    el total es lo que explica por qué no se puede borrar el año, pero **no es lo que el agricultor cuenta
    como apuntes**, y con el total solo la pantalla decía «54 cosas apuntadas dentro» mientras el cuaderno
    del mismo año decía «0 apuntes». Ver `_cuantas_cosas_hay_dentro_por_tipo`.
    """
    campanas = list(
        db.scalars(
            select(models.Campana)
            .where(models.Campana.explotacion_id == explotacion.id)
            .order_by(models.Campana.anio.desc())
        )
    )
    salidas: list[CampanaSalida] = []
    for campana in campanas:
        salida = CampanaSalida.model_validate(campana)
        cuantas = _cuantas_cosas_hay_dentro_por_tipo(db, explotacion.id, campana.id)
        salida.cuantas_cosas = cuantas["todos"]
        salida.apuntes = cuantas["apuntes"]
        salida.tierras_con_cultivo = cuantas["tierras_con_cultivo"]
        salida.otras_cosas = cuantas["otras"]
        salidas.append(salida)
    return salidas


def _comprobar_las_fechas(datos: CampanaEntrada) -> None:
    """El año no puede terminar antes de empezar.

    Vive aparte porque la comprobación es **la misma en el alta y en la corrección**, y tenía que
    seguir siéndolo: una campaña corregida con las fechas al revés pasaría por la puerta de atrás
    de lo que el alta no deja guardar.
    """
    if datos.fecha_fin < datos.fecha_inicio:
        raise HTTPException(status_code=422, detail="El año termina antes de empezar.")


def _ano_libre(db: Db, explotacion, anio: int, *, menos_esta: int | None = None) -> None:
    """Ese año no puede estar ya creado en esta finca.

    `menos_esta` es la campaña que se está corrigiendo: una campaña **es** su año, así que al
    guardarla sin cambiarlo se encontraría a sí misma y se rechazaría a sí misma.
    """
    consulta = select(models.Campana).where(
        models.Campana.explotacion_id == explotacion.id,
        models.Campana.anio == anio,
    )
    if menos_esta is not None:
        consulta = consulta.where(models.Campana.id != menos_esta)
    existente = db.scalar(consulta)
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El año {anio} ya está creado.",
        )


@router.post("/campanas", response_model=CampanaSalida, status_code=status.HTTP_201_CREATED)
def crear_campana(
    datos: CampanaEntrada, explotacion: ExplotacionActual, db: Db
) -> models.Campana:
    _comprobar_las_fechas(datos)
    _ano_libre(db, explotacion, datos.anio)
    campana = models.Campana(explotacion_id=explotacion.id, **datos.model_dump())
    db.add(campana)
    db.commit()
    return campana


@router.get("/campanas/comparar")
def comparar_dos_campanas(
    una_id: int,
    otra_id: int,
    db: Db,
    usuario: UsuarioActual,
    explotacion: ExplotacionActual,
    _: PuedeVerLoEconomico,
):
    """**Comparar dos campañas, y decir si NO se pueden comparar** (CRM-05, 14/10/2026).

    El contrato lo pide así: *«comparar campañas declara áreas y cobertura distintas»*. Y la tentación es
    poner dos márgenes uno al lado del otro y dejarlos restar — que es exactamente lo que **no** se puede
    hacer si una campaña se trabajó sobre 40 hectáreas y la otra sobre 12, o si de parte de las parcelas no
    consta la superficie.

    LAS ÁREAS DE UNA CAMPAÑA. `Parcela` **no** lleva `campana_id`: la tierra es la tierra y la campaña es el
    año. Así que lo que una campaña trabajó son **las parcelas que tocan sus apuntes**, y para eso se usan
    **las tres tablas que la casa ya usa en el cuaderno** (`cuaderno.py`: tratamientos, fertilizaciones y
    labores). La superficie es `Parcela.superficie_oficial`, la del SIGPAC: *«la oficial manda»*, dice su
    modelo.

    LA COBERTURA, COMO LA CASA LA DECLARA. Aquí se copia el patrón que ya está escrito en
    `cuaderno_cyl.py:372`: **una cifra parcial no se rellena con ceros, se declara parcial**. Se suman solo
    las parcelas que traen superficie y se dice **cuántas no la traen**, *«para que quien lea sepa que esa
    cifra es parcial»*. Y si alguna de las dos tiene parcelas sin superficie, **no son comparables**: la
    diferencia que se vería podría ser un agujero en los datos, no una diferencia de verdad.
    """
    def _la_mia(campana_id: int) -> models.Campana:
        # **De esta finca, o 404** — sin distinguir «no existe» de «no es tuya», como en el resto.
        campana = db.get(models.Campana, campana_id)
        if campana is None or campana.explotacion_id != explotacion.id:
            raise HTTPException(status_code=404, detail="Esa campaña no es de esta finca.")
        return campana

    def _lo_que_trabajo(campana: models.Campana) -> dict:
        tocadas: set[int] = set()
        apuntes = 0
        for modelo in (models.TratamientoFitosanitario, models.RegistroFertilizacion, models.Labor):
            filas = db.execute(
                select(modelo.parcela_id).where(
                    modelo.explotacion_id == explotacion.id,
                    modelo.campana_id == campana.id,
                )
            ).scalars().all()
            apuntes += len(filas)
            tocadas.update(pid for pid in filas if pid is not None)
        parcelas = (
            db.execute(
                select(models.Parcela).where(
                    models.Parcela.explotacion_id == explotacion.id,
                    models.Parcela.id.in_(tocadas),
                )
            ).scalars().all()
            if tocadas
            else []
        )
        hectareas = sum(
            (Decimal(str(p.superficie_oficial)) for p in parcelas if p.superficie_oficial is not None),
            Decimal("0"),
        )
        sin_superficie = sum(1 for p in parcelas if p.superficie_oficial is None)
        return {
            "campana_id": campana.id,
            "anio": campana.anio,
            "fecha_inicio": campana.fecha_inicio.isoformat() if campana.fecha_inicio else None,
            "fecha_fin": campana.fecha_fin.isoformat() if campana.fecha_fin else None,
            "cerrada": bool(campana.cerrada),
            "apuntes": apuntes,
            "parcelas": len(parcelas),
            # **La cifra con su cobertura al lado**: nunca se calla que es parcial.
            "hectareas": float(hectareas),
            "parcelas_sin_superficie": sin_superficie,
            "la_superficie_es_parcial": sin_superficie > 0,
        }

    una = _la_mia(una_id)
    otra = _la_mia(otra_id)
    suya = _lo_que_trabajo(una)
    ajena = _lo_que_trabajo(otra)

    # **Por qué no se pueden comparar, en palabras** — nunca un «no» seco, y cada motivo dicho como es:
    # no es lo mismo medir mal que no haber medido.
    motivos: list[str] = []
    if una.anio == otra.anio:
        motivos.append(f"las dos son del año {una.anio}: esto compara años distintos")
    if suya["la_superficie_es_parcial"] or ajena["la_superficie_es_parcial"]:
        motivos.append(
            "de algunas parcelas no consta la superficie oficial "
            f"({suya['parcelas_sin_superficie']} en {una.anio} y {ajena['parcelas_sin_superficie']} en {otra.anio}): "
            "la diferencia que se ve podría ser un hueco en los datos"
        )
    if suya["cerrada"] != ajena["cerrada"]:
        motivos.append("una está cerrada y la otra no: la que sigue abierta todavía va a recibir apuntes")
    if not suya["parcelas"] or not ajena["parcelas"]:
        motivos.append("alguna de las dos no tiene ni una parcela trabajada apuntada")

    return {
        "una": suya,
        "otra": ajena,
        "comparables": not motivos,
        "y_por_que_no": motivos,
        # Lo que sí se puede restar cuando se puede — y **nada** cuando no.
        "diferencia_de_hectareas": (round(suya["hectareas"] - ajena["hectareas"], 4) if not motivos else None),
    }


@router.get("/campanas/actual", response_model=CampanaSalida)
def campana_actual(explotacion: ExplotacionActual, db: Db) -> models.Campana:
    campana = db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion.id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )
    if campana is None:
        raise HTTPException(status_code=404, detail="Todavía no hay ningún año creado.")
    return campana


@router.put("/campanas/{campana_id}", response_model=CampanaSalida)
def corregir_campana(
    campana_id: int,
    datos: CampanaCorreccion,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.Campana:
    """Corrige una campaña: **su año, sus fechas y si está cerrada**.

    POR QUÉ HACÍA FALTA, Y POR QUÉ ES DE LAS COSAS QUE MÁS SE EQUIVOCAN. Hasta ahora una campaña se
    podía crear y no se podía tocar: si el año salía mal escrito —2027 donde iba 2026— o las fechas
    no eran las del ciclo del cultivo, no había ninguna forma de arreglarlo, y **todos los apuntes
    de ese año** (tratamientos, abonos, labores, análisis, ventas, planes) se quedaban colgando de
    un año que no es el suyo. David lo pidió con estas palabras: «recuerda también dejar borrar las
    cosas que introduzca porque puede que me equivoque, o modificar también».

    POR QUÉ SE CORRIGE EN EL SITIO Y NO SE BORRA Y SE VUELVE A CREAR. Porque de la campaña cuelga
    **el año entero**: cada apunte guarda su identificador (`campana_id`) y el identificador que
    viaja a la Junta (`IdAjena`) es el de la fila, así que crear otra campaña obligaría a volver a
    apuntar el año completo. Corrigiendo aquí, el año sigue siendo el mismo —mismo `id`— con los
    datos buenos, y **lo que había queda escrito en la auditoría, campo por campo**
    (`correcciones`).

    Pasa por **las mismas comprobaciones que el alta**, y a propósito: el año no puede terminar
    antes de empezar y no puede haber dos campañas con el mismo año en la misma finca (lo impide la
    base de datos, `uq_campana_anio`; sin comprobarlo antes, el agricultor vería un fallo del
    programa en vez de que se lo digan con palabras).
    """
    campana = obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    _comprobar_las_fechas(datos)
    _ano_libre(db, explotacion, datos.anio, menos_esta=campana.id)

    preparado = models.Campana(
        explotacion_id=explotacion.id,
        anio=datos.anio,
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
        cerrada=datos.cerrada,
    )
    # `creada_en` se queda como estaba, y hay que decirlo porque es una trampa conocida: se llama en
    # femenino, así que **se le escapa a la lista de `correcciones`** (que protege `creado_en`), y
    # una campaña sin fecha de alta no se puede guardar: la corrección fallaría con un fallo del
    # programa. Es la misma regla que en las tierras
    # (`parcelas._columnas_que_una_correccion_no_toca`):
    # lo que el formulario no puede mandar de vuelta **no se toca**, o se perdería.
    preparado.creada_en = campana.creada_en

    correcciones.corregir(
        db,
        guardado=campana,
        preparado=preparado,
        entidad="campana",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return campana


def _cuantas_cosas_hay_dentro(db: Db, explotacion_id: int, campana_id: int) -> int:
    """Cuántas cosas del cuaderno están apuntadas **dentro de esa campaña**.

    Las tablas se sacan de la base de datos y no de una lista escrita a mano
    (`correcciones.tablas_que_apuntan_a`): hoy son once —tratamientos, abonos, labores, el cultivo
    declarado de cada tierra, análisis, ventas, planes de abono, grupos, facturas, documentos anexos
    y firmas—, y el día que se añada la duodécima, esta cuenta la incluye sola. Se cuentan también
    las anuladas: siguen dentro del año y siguen diciendo lo que dicen.
    """
    return sum(
        correcciones.cuantas_filas_apuntan_a(db, modelo, "campana_id", campana_id, explotacion_id)
        for modelo in correcciones.tablas_que_apuntan_a("campana_id")
    )


# ── Qué es cada cosa que hay dentro de un año (30/09/2026) ────────────────────────────────────────────
#
# POR QUÉ ESTA CLASIFICACIÓN, CON EL FALLO QUE LA TRAJO. La pantalla de los años decía del 2026 «Tiene 54
# cosas apuntadas dentro» y «mi cuaderno» del mismo año decía «0 apuntes en el cuaderno». Las dos cosas eran
# verdad —las 54 eran las tierras con su cultivo dicho, que también cuelgan del año— y el agricultor no podía
# entenderlo: parece que una de las dos miente. Se vio en la revisión de la interfaz del 30/09/2026, mirando
# la aplicación con los datos de verdad.
#
# Así que el año cuenta **tres cosas distintas**, y cada una se llama por su nombre en la pantalla:
#
#   1. **Los apuntes del cuaderno**: tratamientos, abonos y labores (con las cosechas dentro: una cosecha es
#      una labor de ese tipo). Es **exactamente** lo que cuenta la pantalla de «mi cuaderno», y por eso los
#      dos números ya no se pueden contradecir.
#   2. **Las tierras con su cultivo dicho**: son datos del año, pero no son apuntes: es «qué hay sembrado».
#   3. **Las demás cosas**: análisis, ventas, planes de abono, grupos, facturas, papeles y la firma del año.
#
# Y el total sigue siendo el que impide borrar un año con cosas dentro (`_cuantas_cosas_hay_dentro`): el
# guardián tiene que contar **todo**, porque todo se lo llevaría por delante.
APUNTES_DEL_CUADERNO = ("TratamientoFitosanitario", "RegistroFertilizacion", "Labor")
TIERRAS_CON_CULTIVO = ("ParcelaCultivo",)
OTRAS_COSAS = (
    "Analitica",
    "VentaDeCosecha",
    "PlanAbonado",
    "GrupoParcelas",
    "Factura",
    "DocumentoAnexo",
    "Firma",
    # **La versión del recinto de cada tierra** (T05, 02/10/2026). Es la duodécima tabla que cuelga
    # del año, y la prueba `test_todas_las_tablas_del_ano_estan_clasificadas` avisó de que había que
    # decidir qué es. Decidido: **una de las demás cosas**. No es un apunte del cuaderno —no es un
    # trabajo ni un producto echado— ni una tierra con su cultivo dicho: es la ficha de qué era esa
    # tierra ese año y de dónde se supo. Y tiene que contar para el total, porque borrar el año se
    # llevaría por delante la historia de sus recintos.
    "VersionDeRecinto",
    # **La factura emitida** (T12, E6, 03/10/2026). Es la decimotercera tabla que cuelga del año, y la
    # prueba `test_todas_las_tablas_del_ano_estan_clasificadas` avisó de que había que decidir qué es
    # (que es exactamente para lo que está). Decidido: **una de las demás cosas**. No es un apunte del
    # cuaderno —no es un trabajo ni un producto echado— ni una tierra con su cultivo dicho: es la
    # cuenta de lo que se vendió ese año. Y **tiene que contar para el total**, porque borrar el año
    # se llevaría por delante las facturas y los cobros que las saldan quedarían apuntando al vacío.
    #
    # **El cobro NO está aquí, y es una decisión**: no cuelga del año (ver `models.Cobro`). El dinero
    # entra un día y salda una factura, que es quien tiene la campaña; colgarlo del año obligaría a
    # decidir de qué año es un pago de enero que salda una factura de diciembre, y esa decisión no la
    # tiene el programa.
    "FacturaEmitida",
    # **Las cuentas de la explotación (T13, E7, 05/10/2026).** Son la decimocuarta, la decimoquinta y
    # la decimosexta tabla que cuelgan del año, y la prueba `test_todas_las_tablas_del_ano_estan_clasificadas`
    # avisó de que había que decidir qué es (que es exactamente para lo que está). Decidido: **las
    # tres son «las demás cosas»**. No son apuntes del cuaderno —no son un trabajo ni un producto
    # echado— ni tierras con su cultivo dicho: son la cuenta de lo que costó el año.
    #
    #   · **`Gasto`**: lo que se consumió. Tiene que contar para el total, porque borrar el año se
    #     llevaría por delante sus cuentas y sus repartos quedarían apuntando al vacío.
    #   · **`InversionDeLaFinca`**: lo que se compró para durar. Cuenta también: aunque no entre
    #     entera en el margen del año, sí es una compra de ese año y su reparto a la campaña se
    #     perdería con él.
    #   · **`RepartoDeCoste`**: a dónde fue cada trozo. Cuenta por el mismo motivo que los dos de
    #     arriba.
    #   · **`Subvencion`**: una ayuda se pide y se cobra en un año. Cuenta también, y su razón es la
    #     misma que la de la inversión: es dinero de ese año y sus tres importes (el previsto, el
    #     concedido y el cobrado) se perderían con él.
    #
    # **El pago (`PagoDeGasto`) NO está aquí, y es la misma decisión que con el `Cobro`**: no cuelga
    # del año. El dinero sale un día y salda un gasto, y es el gasto quien tiene la campaña; colgarlo
    # del año obligaría a decidir de qué año es un pago de enero que salda la compra de diciembre, y
    # esa decisión no la tiene el programa.
    "Gasto",
    "InversionDeLaFinca",
    "RepartoDeCoste",
    "Subvencion",
    # **Y el trabajo planificado (T15, E9, 05/10/2026).** Es la decimonovena tabla que cuelga del año,
    # y la prueba `test_todas_las_tablas_del_ano_estan_clasificadas` avisó de que había que decidir qué
    # es. Decidido: **una de las demás cosas**. No es un apunte del cuaderno —un plan **no es un
    # trabajo hecho**, y por eso no puede contar como apunte, que es justo lo que el ticket persigue— ni
    # una tierra con su cultivo dicho: es lo que se piensa hacer ese año. Y cuenta para el total, porque
    # borrar el año se llevaría por delante lo que estaba pensado.
    #
    # **Sus líneas (`LineaDeTrabajoPrevisto`) no están aquí, y es correcto**: una línea dice qué insumo
    # lleva el plan y no tiene año propio; el año lo tiene el plan del que cuelga.
    "TrabajoPrevisto",
)


def _cuantas_cosas_hay_dentro_por_tipo(
    db: Db, explotacion_id: int, campana_id: int
) -> dict[str, int]:
    """Lo que hay dentro de un año, contado por lo que es.

    **Lo que no esté en las listas de arriba se cuenta como «otras cosas»**, y no se revienta la petición
    por eso: la aplicación sigue contestando (contando de más, que es lo honesto) y hay una prueba que exige
    que **todas** las tablas que apuntan a la campaña estén nombradas en una de las tres listas. Así, el día
    que se añada la duodécima tabla, avisa la prueba y no la pantalla.
    """
    cuantas = {"todos": 0, "apuntes": 0, "tierras_con_cultivo": 0, "otras": 0}
    for modelo in correcciones.tablas_que_apuntan_a("campana_id"):
        filas = correcciones.cuantas_filas_apuntan_a(
            db, modelo, "campana_id", campana_id, explotacion_id
        )
        cuantas["todos"] += filas
        if modelo.__name__ in APUNTES_DEL_CUADERNO:
            cuantas["apuntes"] += filas
        elif modelo.__name__ in TIERRAS_CON_CULTIVO:
            cuantas["tierras_con_cultivo"] += filas
        else:
            cuantas["otras"] += filas
    return cuantas


def _mensaje_de_lo_que_hay_dentro(cuantas: int) -> str:
    """El aviso de «aquí dentro hay N cosas», en singular o en plural.

    Se compone **con el ayudante de siempre** (`textos.mensaje_con_cuenta`), que es lo que hace el resto
    del programa. Durante la ronda 93 esto estuvo escrito a mano con un `try` de por medio, porque el
    texto del plural llevaba `{cuantas}` y el ayudante rellena `{cuantos}`: con dos o más cosas dentro
    reventaba con un 500 en vez de contestar el aviso. **El texto se corrigió** (`{cuantos}`), y con
    eso vuelve a haber un solo camino para contar cosas.
    """
    return textos.mensaje_con_cuenta("B6_tiene_dentro", cuantas)


@router.delete("/campanas/{campana_id}")
def borrar_campana(
    campana_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita una campaña del cuaderno, **si está vacía**.

    POR QUÉ NO SE BORRA UNA CAMPAÑA QUE TIENE COSAS DENTRO. Es el año entero del cuaderno: los
    tratamientos, los abonos, las labores, las cosechas, el cultivo declarado, los análisis, las
    ventas, los planes, las facturas, los documentos y hasta la firma del año apuntan a ella por su
    identificador. Borrarla sería tirar un año de cuaderno de una vez y en una inspección ese año no
    existiría. Por eso se contesta 409 diciendo **cuántas cosas hay dentro**
    (`textos.B6_tiene_dentro`), que es lo que hay que resolver antes.

    Y SOBRE **LA CAMPAÑA QUE SE ESTÁ LLEVANDO** (la que devuelve `/api/campanas/actual`, la del año
    más alto), que es la decisión que conviene leer entera:

      · **Con algo dentro no se borra**, como cualquier otra: es el año en el que la aplicación
        apunta todo lo que no dice el año, y el mensaje dice cuántas cosas se llevarían por delante.
      · **Vacía sí se puede borrar**, y es a propósito. Es la única forma que hay de deshacer un año
        creado por error o de más: `PUT` no puede fundir dos años en uno —no puede haber dos
        campañas con el mismo año—, así que si no se pudiera borrar, ese año de más se quedaría como
        «el año que estás llevando» para siempre, y en cuanto se apuntara algo dentro ya no habría
        forma de quitarlo. Bloquearlo sería cambiar un error corregible por un error para siempre.
      · **No se bloquea con un mensaje propio porque no existe**, y no se inventa: los dos que hay
        para esto —«esto lo usa N apuntes» y «aquí dentro hay N cosas»— contarían **cero** en ese
        caso, y decirle a un agricultor que algo lo usan cero apuntes es mentirle. Queda dicho en el
        informe de la ronda: si se quiere cerrar del todo, hace falta un texto nuevo en `textos.py`
        (o un botón en la web para volver a crear el año, que tampoco lo hay).

    Cuando se borra, se borra de verdad y con su rastro: `correcciones.borrar` deja en la auditoría
    la campaña entera que había, con qué día se quitó y quién lo quitó.
    """
    campana = obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    dentro = _cuantas_cosas_hay_dentro(db, explotacion.id, campana_id)
    if dentro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_mensaje_de_lo_que_hay_dentro(dentro),
        )
    correcciones.borrar(
        db,
        registro=campana,
        entidad="campana",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": campana_id}

