"""Las puertas de los trabajos por tierra (T15, 05/10/2026).

## Qué añade esto a lo que ya había

El programa ya sabe apuntar labores (`POST /api/registros/labores`): lo que se hizo, dónde, con qué
máquina y de qué cultivo. Lo que no tenía es **lo que se piensa hacer**: no existía el trabajo previsto,
así que la agenda del contrato (§4, S04) y el «próximo trabajo» de la ficha de una tierra (§4, S03) no
se podían ni pintar —está escrito en el seguimiento, en los dos sitios donde dice «no se inventa»—.

Este router añade tres cosas:

  1. **Lo previsto** (`/api/trabajos/previstos`): lo que se piensa hacer, con su día, su tierra, su
     máquina y lo que hará falta. Vive en **su propia tabla**, y ahí está la decisión del ticket: una
     columna `estado` en la tabla de labores con el valor por defecto «previsto» convertiría en
     planificado todo el cuaderno que el agricultor ya tiene apuntado. Ver `app/trabajos.py`.
  2. **Marcar lo que de verdad se hizo** (`/api/trabajos/previstos/{id}/hecho`): el plan se cumple
     apuntando el hecho, con su día real, sus hectáreas reales, sus horas y lo que se gastó de verdad.
     **Un plan no se convierte en un hecho por parecerse a él**: el vínculo lo dice el agricultor.
  3. **La agenda y la historia** (`/api/trabajos`, `/api/trabajos/tierra/{parcela_id}`): lo previsto, lo
     hecho, el historial de una tierra con **todos** sus eventos y el estado derivado —qué tiene
     sembrado, qué se ha hecho, qué queda—. Todo ello lo calcula `app/trabajos.py`, que es lógica pura:
     aquí solo se leen las filas, se llaman esas funciones y se devuelve lo que dicen.

## Las tres reglas que este fichero cumple, y cómo

  · **Lo previsto no consume existencias.** Lo único que descuenta del almacén es un hecho, y pasa por
    la puerta que ya existe (`almacen_api.sacar_de_un_lote`, con `apunte_tipo="labor"`): **no hay una
    segunda forma de restar**. Lo que gastaría un plan se enseña como estimación, con su dosis y sus
    hectáreas, y no toca nada.
  · **Nada se borra.** Corregir escribe la fila que ya estaba y deja `[antes, ahora]` en la auditoría;
    anular pone `anulado` y el motivo; nada se tira. Y **lo firmado no se borra**: se anula, y el
    router lo dice antes de intentarlo (`correcciones.firmas_de_un_apunte`).
  · **Corregir y anular no duplican consumos.** Si lo que cambia es lo que salió del envase, la salida
    vieja se **anula** y se apunta una nueva por la puerta de las salidas: nunca quedan dos vivas, y
    nunca se reescribe por detrás la cantidad de un movimiento que alguien apuntó. Lo mismo con lo que
    se anula: el movimiento se queda en el libro y deja de contar, porque `models.Labor` está en
    `servicios.estado_de_los_origenes`.

## LO QUE FALTABA, Y YA ESTÁ (07/10/2026)

**Este fichero decía que estaba escrito entero y que no se podía importar**, esperando seis piezas de
ficheros del coordinador (las tablas de lo previsto, las columnas nuevas de `models.Labor`, los esquemas,
las frases `TJ1`–`TJ28` y el bloque `AGENDA`, tres líneas de `servicios` y el `include_router` de
`main.py`). **Todo eso está puesto y el router está integrado**: la revisión del recorrido lo comprobó
ejecutando `pytest tests/test_trabajos.py -q -rs` → **77 pruebas pasan y 0 saltan**, así que ya no hay
ninguna prueba esperando. El texto de arriba se queda escrito, con su fecha, porque explica por qué este
fichero se escribió antes que sus piezas y en qué orden se integró; lo que **no** se puede dejar es la
frase «no se puede importar», que era verdad el 05/10 y dejó de serlo.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .. import correcciones, models, reenvios, servicios, textos, trabajos as logica
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AnulacionEntrada,
    MarcarHechoEntrada,
    ReprogramarEntrada,
    SalidaDeAlmacenEntrada,
    TrabajoEntrada,
    TrabajoPrevistoEntrada,
)
# **La puerta de las salidas, importada tal cual.** Es la mitad de este ticket: lo que gasta un trabajo
# sale del almacén por donde sale todo lo demás, no por un camino nuevo. Llamarla aquí, en vez de copiar
# su lógica, es lo que garantiza que no haya dos formas de descontar (las comprobaciones de reenvío, el
# aviso de que el envase se queda en negativo y la auditoría son las mismas).
from .almacen_api import sacar_de_un_lote

router = APIRouter(prefix="/api/trabajos", tags=["trabajos"])

# Lo que este router necesita de los ficheros compartidos, con nombre y apellidos. Se sirve en
# `/api/trabajos/que-falta` para que la pantalla pueda decirlo: un hueco que no se dice se convierte en
# un hueco que alguien rellena con lo que le parece.
LO_QUE_FALTA: tuple[str, ...] = (
    "models.TrabajoPrevisto y models.LineaDeTrabajoPrevisto: las dos tablas de lo previsto",
    "las columnas nuevas de models.Labor: clave_de_reenvio, horas y previsto_id",
    "los esquemas de schemas.py: TrabajoEntrada, TrabajoPrevistoEntrada y sus salidas",
    "las frases de textos.py: los códigos TJ1–TJ28 y el bloque AGENDA",
    "servicios.APUNTES_QUE_GASTAN con «labor», y sus dos listas de origen y de gasto",
    "el include_router de main.py",
)

# Los estados con los que se puede pedir la agenda. `anulado` no está entre ellos: **anulado no es un
# estado de un trabajo, es lo que le pasa a un hecho registrado**, y se pide con `incluir_anulados`.
ESTADOS_QUE_SE_PUEDEN_PEDIR = ("previsto", "en_curso", "realizado", "cancelado")


# --------------------------------------------------------------------------
# Leer las filas y contarlas con la lógica pura
# --------------------------------------------------------------------------


# -----------------------------------------------------------------------------------------------------------
# ***Lo que no es una columna***: las filas hijas (18/10/2026, revision independiente)
# -----------------------------------------------------------------------------------------------------------
#
# Un plan guarda sus **lineas** en otra tabla, y una labor guarda sus **insumos** como **salidas de almacen**.
# Eso no esta en la fila, asi que `reenvios` no lo puede comparar solo: **la puerta lo acredita aqui**.
#
# ***Y hacia falta***: *antes, `reenvios` **saltaba** esos campos, asi que un reintento con **otras** lineas u
# **otros** insumos devolvia el plan o la labor que ya habia **como si fuera lo que se acaba de mandar** -con las
# filas hijas de la **primera** vez-. La revision lo pide con esas palabras: «cada puerta debe acreditar los
# datos compuestos que el ayudante no compara».*


def _un_numero(valor):
    """**Un numero en la forma en que se compara**: *sin colas de redondeo; `None` sigue siendo `None`.*"""
    return None if valor is None else round(float(valor), 4)


def _la_linea_como_tupla(linea) -> tuple:
    """***Los nueve campos de una linea***, *los mismos en la peticion y en la fila guardada.*"""
    return (
        linea.parcela_id,
        _un_numero(linea.superficie_ha),
        _un_numero(linea.cantidad),
        (linea.unidad or "").strip(),
        _un_numero(linea.dosis_por_ha),
        linea.articulo_id,
        linea.lote_id,
        _un_numero(linea.horas),
        (linea.observaciones or "").strip(),
    )


def _las_lineas_son_las_del_plan(db, previsto_id: int, datos) -> bool:
    """***Si las lineas que se mandan son las que el plan ya tiene.*** *Se comparan como **conjunto ordenado**:
    el orden en que se escribieron no es parte de la accion.*"""
    las_de_antes = list(
        db.scalars(
            select(models.LineaDeTrabajoPrevisto).where(
                models.LineaDeTrabajoPrevisto.trabajo_previsto_id == previsto_id
            )
        )
    )
    return sorted(_la_linea_como_tupla(una) for una in las_de_antes) == sorted(
        _la_linea_como_tupla(una) for una in (datos.lineas or [])
    )


def _el_insumo_como_tupla(insumo) -> tuple:
    """***Lo que de verdad se guarda de un insumo***: *el envase, la cantidad y la unidad.*

    *`articulo_id` no se compara porque **no viaja**: el envase ya dice de que es. Y `dosis_por_ha` y
    `aceptar_descuadre` tampoco se guardan en la salida, asi que **no se pueden comparar** -se dice aqui en vez
    de fingir que se miran-.*
    """
    return (insumo.lote_id, _un_numero(insumo.cantidad), (insumo.unidad or "").strip())


def _los_insumos_son_los_de_la_labor(db, labor_id: int, datos) -> bool:
    """***Si los insumos que se mandan son los que la labor ya gasto.***

    ***Solo se miran los que la puerta habria escrito***: *la funcion que saca del almacen **se salta** los
    insumos sin cantidad, sin unidad o sin envase -y lo dice en un aviso-, asi que compararlos seria pedirle a la
    base algo que nunca se le mando.*
    """
    las_salidas = list(
        db.scalars(
            select(models.MovimientoDeExistencias).where(
                models.MovimientoDeExistencias.origen_tipo == "labor",
                models.MovimientoDeExistencias.origen_id == labor_id,
                models.MovimientoDeExistencias.anulado.is_(False),
            )
        )
    )
    los_que_se_escribieron = [
        insumo
        for insumo in (datos.insumos or [])
        if insumo.cantidad is not None
        and (insumo.unidad or "").strip()
        and insumo.lote_id is not None
    ]
    return sorted(_el_insumo_como_tupla(una) for una in las_salidas) == sorted(
        _el_insumo_como_tupla(uno) for uno in los_que_se_escribieron
    )


def _lo_compuesto(db):
    """***El `tambien` que se le pasa a `reenvios`***: *contesta por las filas hijas y **cierra en falso** con lo
    que no sepa.*

    *Un campo que no sea columna ni este aqui **no se da por la misma accion**: un 409 que se puede explicar es
    mejor que una fila hija que no se apunto.*
    """

    def el_que_mira(campo: str, ya, datos) -> bool:
        if campo == "lineas":
            return _las_lineas_son_las_del_plan(db, ya.id, datos)
        if campo == "insumos":
            return _los_insumos_son_los_de_la_labor(db, ya.id, datos)
        return False

    return el_que_mira


# ***Y las horas, que se guardan con otro nombre***: *`horas` en la peticion, `horas_previstas` en la fila.*
LAS_HORAS_DEL_PLAN = {"horas": "horas_previstas"}


def _la_clave(datos) -> str | None:
    """La clave de reenvío del móvil, del sitio donde venga."""
    return ((getattr(datos, "clave_de_reenvio", None) or getattr(datos, "id_local", None) or "") or "").strip()[:120] or None


def _el_subtipo(labor: models.Labor) -> str | None:
    """El subtipo de una labor de suelo (rodillo, cultivador, arado…).

    **Se lee de la columna si existe y, mientras no exista, de `detalles`.** El contrato (§4, S05) pide
    el subtipo con nombre y número, y la regla de la casa es que un dato así vive en su columna y no en
    un JSON de texto libre —`Labor.detalles` es un cajón que no se puede consultar ni sumar—. La columna
    está propuesta en `docs/T15_TRABAJOS.md`; hasta que llegue, el asistente lo guarda en `detalles` y
    aquí se lee de ahí para no perderlo.
    """
    de_la_columna = getattr(labor, "subtipo", None)
    if de_la_columna:
        return de_la_columna
    detalles = labor.detalles or {}
    return (detalles.get("subtipo") or "").strip() or None


def _los_consumos_de_una_labor(db, labor: models.Labor) -> list[dict]:
    """Las salidas del almacén que sostienen esta labor: **las vivas y las anuladas**.

    Las anuladas se devuelven también, y con ellas se puede explicar lo que de verdad pasó: una salida
    que se anuló al corregir el trabajo sigue en el libro, tachada, y no cuenta. Si aquí se
    devolvieran solo las vivas, la pantalla no podría decir por qué hay dos movimientos de lo mismo.

    ## El nombre del producto y el del envase van aquí, y no los pone la pantalla

    Se descubrió recorriendo el recorrido 4 en un navegador: la historia de una tierra decía
    **«Qué gastaste del almacén: 6 L»**, sin decir de qué. Un número sin su producto no contesta la
    pregunta que se hace el día de una inspección —y menos con un fitosanitario, que es justo lo que hay
    que poder decir de qué lote salió—. El nombre del artículo y el número del envase **ya estaban en la
    base** (los lee el libro del almacén por la misma razón), así que se resuelven aquí, que es donde se
    sabe de qué movimiento se habla: la pantalla no tiene que cruzar listas ni puede enseñar el nombre de
    un artículo que ya no es.
    """
    movimientos = list(
        db.scalars(
            select(models.MovimientoDeExistencias).where(
                models.MovimientoDeExistencias.explotacion_id == labor.explotacion_id,
                models.MovimientoDeExistencias.origen_tipo == "labor",
                models.MovimientoDeExistencias.origen_id == labor.id,
            )
        )
    )
    # Una consulta por cada identificador distinto, y no una por movimiento: un trabajo que gasta de tres
    # envases del mismo artículo no pregunta tres veces por el mismo nombre.
    nombres_de_articulo: dict[int, str] = {}
    numeros_de_lote: dict[int, str] = {}
    for movimiento in movimientos:
        if movimiento.articulo_id and movimiento.articulo_id not in nombres_de_articulo:
            articulo = db.get(models.Articulo, movimiento.articulo_id)
            nombres_de_articulo[movimiento.articulo_id] = articulo.nombre if articulo else ""
        if movimiento.lote_id and movimiento.lote_id not in numeros_de_lote:
            lote = db.get(models.Lote, movimiento.lote_id)
            numeros_de_lote[movimiento.lote_id] = lote.numero_lote if lote else ""
    return [
        logica.un_insumo(
            articulo_id=movimiento.articulo_id,
            # El nombre y el envase, para que lo que gastó un trabajo se pueda leer entero. Si el
            # artículo ya no está, se queda vacío: la pantalla enseña la cantidad y no un número de la
            # base, que es la regla de siempre.
            articulo=nombres_de_articulo.get(movimiento.articulo_id) or None,
            lote_id=movimiento.lote_id,
            numero_lote=numeros_de_lote.get(movimiento.lote_id) or None,
            cantidad=movimiento.cantidad,
            unidad=movimiento.unidad,
            anulado=movimiento.anulado,
            movimiento_id=movimiento.id,
            fecha=movimiento.fecha,
            origen_tipo="labor",
            origen_id=labor.id,
        )
        for movimiento in movimientos
    ]


def _una_labor_como_trabajo(db, labor: models.Labor) -> dict:
    """Una fila de labores contada como lo que es: **un hecho**.

    Aquí está el único sitio donde «realizado» se pone sin que nadie lo haya escrito, y es correcto: la
    tabla de labores no tiene ninguna forma de guardar algo que no ha pasado —el agricultor apunta ahí
    pulsando «HE SEMBRADO»—. Si algún día esa tabla tuviera estados, esta línea es la que hay que
    cambiar, y `trabajos.un_hecho` lo dice en su comentario.
    """
    return logica.un_hecho(
        id=labor.id,
        campana_id=labor.campana_id,
        tipo=labor.tipo,
        subtipo=_el_subtipo(labor),
        fecha=labor.fecha,
        parcela_id=labor.parcela_id,
        grupo_id=labor.grupo_id,
        superficie_ha=labor.superficie_ha,
        cultivo=labor.cultivo,
        variedad=labor.variedad,
        equipo_id=labor.equipo_id,
        horas=getattr(labor, "horas", None),
        anulado=labor.anulado,
        motivo_anulacion=labor.motivo_anulacion,
        clave_de_reenvio=getattr(labor, "clave_de_reenvio", None),
        previsto_id=getattr(labor, "previsto_id", None),
        observaciones=labor.observaciones,
        insumos=_los_consumos_de_una_labor(db, labor),
    )


def _la_campana_de_la_peticion(db, explotacion, campana_id):
    """La campaña en la que se está mirando: la que pide quien llama, o **la que se está llevando**.

    Hace falta para leer el cultivo declarado, que es **de una campaña** (una tierra tiene un cultivo por
    año). Se resuelve igual que `/api/campanas/actual` —la más nueva de la explotación—, que es la misma
    regla que usa el programa entero, y no una segunda forma de decidir cuál es el año de hoy.
    """
    if campana_id is not None:
        return campana_id
    return db.scalar(
        select(models.Campana.id)
        .where(models.Campana.explotacion_id == explotacion.id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )


def _el_cultivo_del_cuaderno(db, explotacion, parcela_id: int, campana_id) -> dict | None:
    """Lo que el agricultor **declaró** que hay en esa tierra ese año, con la forma que espera la pantalla.

    **Por qué esto es un defecto arreglado y no un adorno.** «Qué hay hoy» se calculaba solo con las
    labores de siembra y plantación. Pero el agricultor apunta lo que tiene sembrado en «qué hay
    sembrado» (la tabla `parcelas_cultivos`, la que va al cuaderno de la Junta), y **no tiene por qué
    llevar además una labor de siembra**: abrir entonces una tierra con TRIGO BLANDO declarado decía «de
    esta tierra no consta que haya nada sembrado» —una contradicción con la pantalla de al lado, con las
    dos mirando los mismos datos—. Se encontró abriendo la historia de una tierra en un navegador de
    verdad, con el guion de `scripts/comprobar_en_un_navegador.py`.

    **Solo se rellena cuando no hay nada que deducir de las labores**: lo que dice una labor de siembra
    apuntada es un hecho del cuaderno y manda; esto es el respaldo para las tierras que solo tienen la
    declaración. Y **no se inventa nada**: sin declaración devuelve `None`, y el estado sigue diciendo
    que no consta, que es la verdad.
    """
    declarado = servicios.cultivo_declarado(
        db,
        explotacion_id=explotacion.id,
        parcela_id=parcela_id,
        campana_id=_la_campana_de_la_peticion(db, explotacion, campana_id),
    )
    if declarado is None:
        return None
    return {
        # `tipo` y `trabajo_id` van en `None` **a propósito**: esto no sale de ninguna labor, y poner aquí
        # el tipo de la última que hubiera sería decir que la siembra la apuntó alguien cuando no es así.
        "tipo": None,
        "cultivo": declarado.especie,
        "variedad": declarado.variedad,
        "fecha": declarado.fecha_inicio,
        "trabajo_id": None,
        "superficie_ha": declarado.superficie_cultivada_ha,
        # De dónde sale, dicho: no es lo mismo deducirlo de una labor que leerlo de lo que él declaró.
        "de_donde": "lo_dijo_el_agricultor",
    }


def _las_labores(db, explotacion, *, parcela_id=None, campana_id=None, desde=None, hasta=None):
    consulta = select(models.Labor).where(models.Labor.explotacion_id == explotacion.id)
    if parcela_id is not None:
        consulta = consulta.where(models.Labor.parcela_id == parcela_id)
    if campana_id is not None:
        consulta = consulta.where(models.Labor.campana_id == campana_id)
    if desde is not None:
        consulta = consulta.where(models.Labor.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(models.Labor.fecha <= hasta)
    return list(db.scalars(consulta.order_by(models.Labor.fecha, models.Labor.id)))


def _los_previstos(db, explotacion, *, parcela_id=None, campana_id=None, estado=None):
    """Los trabajos planificados, tal y como están en su tabla.

    **El estado se copia tal cual, incluido el vacío.** Si un plan no dice en qué punto está, se queda
    sin decir —`None`, «no consta»— y la lógica pura no lo toma ni por previsto ni por hecho. Es la
    misma regla que la del resto del programa con los datos que no se saben.
    """
    consulta = select(models.TrabajoPrevisto).where(
        models.TrabajoPrevisto.explotacion_id == explotacion.id
    )
    if parcela_id is not None:
        consulta = consulta.where(models.TrabajoPrevisto.parcela_id == parcela_id)
    if campana_id is not None:
        consulta = consulta.where(models.TrabajoPrevisto.campana_id == campana_id)
    if estado is not None:
        consulta = consulta.where(models.TrabajoPrevisto.estado == estado)
    return [
        logica.un_trabajo(
            id=plan.id,
            de_donde="previsto",
            campana_id=plan.campana_id,
            tipo=plan.tipo,
            subtipo=plan.subtipo,
            estado=plan.estado,
            fecha_prevista=plan.fecha_prevista,
            fecha_fin_prevista=plan.fecha_fin_prevista,
            fecha_prevista_antes=plan.fecha_prevista_antes,
            parcela_id=plan.parcela_id,
            grupo_id=plan.grupo_id,
            superficie_ha=plan.superficie_ha,
            cultivo=plan.cultivo,
            variedad=plan.variedad,
            equipo_id=plan.equipo_id,
            persona=plan.persona,
            horas_previstas=getattr(plan, "horas_previstas", None),
            clave_de_reenvio=plan.clave_de_reenvio,
            observaciones=plan.observaciones,
            insumos=[
                logica.un_insumo(
                    articulo_id=linea.articulo_id,
                    articulo=None,
                    lote_id=linea.lote_id,
                    cantidad=linea.cantidad,
                    unidad=linea.unidad,
                    dosis_por_ha=linea.dosis_por_ha,
                )
                for linea in (plan.lineas or [])
            ],
        )
        for plan in db.scalars(consulta.order_by(models.TrabajoPrevisto.fecha_prevista))
    ]


def _el_bloque_de_lo_que_falta() -> list[dict]:
    """Lo que el programa no sabe, para decirlo en la pantalla y no en un comentario del código."""
    return [dict(falta) for falta in logica.QUE_FALTA]


# --------------------------------------------------------------------------
# La agenda y el historial
# --------------------------------------------------------------------------


@router.get("/que-falta")
def lo_que_falta_de_los_trabajos() -> dict:
    """Lo que este ticket todavía no sabe, y lo que le falta para funcionar entero.

    Es la misma puerta que ya tienen la maquinaria y el volcado oficial: lo que no se puede hacer se
    **declara** con lo que es, para qué hace falta y de quién depende. Aquí hay dos listas y las dos
    importan: `falta` es lo que el programa no sabe hacer (la lluvia, la nascencia medida) y
    `falta_para_integrar` es lo que le falta a este módulo para poder ejecutarse.
    """
    return {
        "falta": _el_bloque_de_lo_que_falta(),
        "falta_para_integrar": list(LO_QUE_FALTA),
        "estados": list(logica.ESTADOS_DE_UN_TRABAJO),
        "tipos": list(logica.TIPOS_DE_TRABAJO),
        "subtipos_de_laboreo": list(logica.SUBTIPOS_DE_LABOREO),
        "textos": textos.ACCIONES,
    }


@router.get("")
def la_agenda(
    explotacion: ExplotacionActual,
    db: Db,
    parcela_id: int | None = None,
    campana_id: int | None = None,
    estado: str | None = None,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
    incluir_anulados: bool = True,
) -> dict:
    """La agenda: **lo previsto y lo hecho, en el mismo sitio y sin mezclarse** (S04).

    Es la pantalla que faltaba: la lista de trabajos con su fecha prevista o real, su tierra, su tipo,
    su máquina, su duración, su superficie y su estado. Y lo anulado sale —tachado, con su motivo—,
    porque esconderlo haría que el agricultor no pudiera explicar su propio cuaderno.

    Lo que devuelve es lo que dicen las funciones puras, y **nada se cuenta aquí**: ni las hectáreas, ni
    las horas, ni los días que faltan. Es la forma de que la agenda, la ficha de la tierra y el cuaderno
    no puedan decir cifras distintas.
    """
    if estado is not None and estado not in ESTADOS_QUE_SE_PUEDEN_PEDIR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("TJ17_un_plan_no_es_un_trabajo"),
        )
    if parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)

    hoy = dt.date.today()
    labores = _las_labores(
        db, explotacion, parcela_id=parcela_id, campana_id=campana_id, desde=desde, hasta=hasta
    )
    hechos = [_una_labor_como_trabajo(db, labor) for labor in labores]
    if not incluir_anulados:
        hechos = [hecho for hecho in hechos if not hecho["anulado"]]

    planes = _los_previstos(db, explotacion, parcela_id=parcela_id, campana_id=campana_id, estado=estado)
    # **El reenvío del móvil se quita aquí y se dice**: la misma petición dos veces es un trabajo, no
    # dos, y lo que se ha quitado se cuenta con su código para que nadie crea que se ha perdido.
    unicos = logica.quita_los_reenvios(hechos)

    return {
        "hechos": unicos["trabajos"],
        "previstos": planes,
        "reenviados": unicos["cuantos_reenviados"],
        "no_se_pudo_comprobar_si_ya_estaba": unicos["sin_clave"],
        "aviso_codigo": unicos["sin_clave_porque_codigo"],
        "lo_previsto_y_lo_hecho": logica.lo_previsto_y_lo_hecho(planes, unicos["trabajos"])["sin_cumplir"],
        "hoy": hoy,
        "textos": textos.ACCIONES,
    }


@router.get("/tierra/{parcela_id}")
def la_historia_de_una_tierra(
    parcela_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    incluir_anulados: bool = True,
) -> dict:
    """**El historial y el estado de una tierra** (S03): todo lo que ha pasado, y qué hay hoy.

    Es la mitad del ticket que más se va a mirar: la ficha de una tierra enseña sus labores por orden,
    con su superficie, su máquina, sus insumos y si están corregidas o anuladas, y debajo el estado
    derivado —qué tiene sembrado, qué se ha hecho y qué queda previsto—.

    Las dos cosas salen de las mismas cifras (`trabajos.cifras_de_una_tierra`), y hay una prueba que lo
    exige: **una cifra que sale en dos pantallas tiene que salir del mismo sitio**.

    Y lo que **no** dice, porque no se puede saber: si ha nacido la planta (de una lluvia no se deduce)
    y si la tierra quedó vacía después de la cosecha. Va en la respuesta, con su código, para que la
    pantalla lo enseñe en vez de callarse.
    """
    tierra = obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    hoy = dt.date.today()
    hechos = [
        _una_labor_como_trabajo(db, labor)
        for labor in _las_labores(db, explotacion, parcela_id=parcela_id, campana_id=campana_id)
    ]
    planes = _los_previstos(db, explotacion, parcela_id=parcela_id, campana_id=campana_id)

    historial = logica.historial_de_una_tierra(
        hechos,
        parcela_id=parcela_id,
        campana_id=campana_id,
        incluir_anulados=incluir_anulados,
        hoy=hoy,
    )
    estado = logica.estado_de_una_tierra(
        hechos, planes, parcela_id=parcela_id, campana_id=campana_id, hoy=hoy
    )
    # Y si de las labores no sale ningún cultivo, se mira lo que el agricultor **declaró** para ese año:
    # una tierra con el cultivo puesto en «qué hay sembrado» y sin ninguna labor de siembra no puede
    # salir aquí diciendo que no consta que haya nada sembrado.
    if estado.get("cultivo_declarado") is None:
        estado["cultivo_declarado"] = _el_cultivo_del_cuaderno(db, explotacion, parcela_id, campana_id)
    return {
        "tierra": {"id": tierra.id, "alias": tierra.alias, "superficie_ha": tierra.superficie_ha},
        "historial": historial,
        "estado": estado,
        "trabajos_sin_hectareas": historial["cifras"]["superficie_sin_decir"],
        "lo_que_no_se_sabe": {
            "nascencia": estado["no_se_puede_deducir_la_nascencia_porque_codigo"],
            "en_el_suelo": estado["no_se_puede_deducir_el_suelo_porque_codigo"],
            "de_la_tierra": _el_porque_de_la_tierra(tierra),
            "hectareas": historial["cifras"]["lo_que_no_se_sabe"],
        },
        "falta": _el_bloque_de_lo_que_falta(),
        "textos": textos.ACCIONES,
    }


def _el_porque_de_la_tierra(tierra: models.Parcela) -> str:
    """Por qué no se puede comparar lo trabajado con la tierra: si no consta su superficie, se dice."""
    return "" if tierra.superficie_ha is not None else "TJ23_faltan_las_hectareas_de_la_tierra"


@router.get("/historial/{parcela_id}")
def el_historial_de_una_tierra(
    parcela_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    incluir_anulados: bool = True,
) -> dict:
    """Solo el historial: lo que ha pasado en esa tierra, en orden y **sin tirar nada**.

    Está separado del estado porque son dos cosas distintas y se miran por separado —la historia se lee
    de arriba abajo y el estado se lee de un vistazo—, y porque un dato que se pide aparte se puede
    probar aparte. Las cifras que lleva dentro son **las mismas** que las del estado: salen de la misma
    función, y hay una prueba que lo exige.
    """
    obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    hechos = [
        _una_labor_como_trabajo(db, labor)
        for labor in _las_labores(db, explotacion, parcela_id=parcela_id, campana_id=campana_id)
    ]
    return logica.historial_de_una_tierra(
        hechos,
        parcela_id=parcela_id,
        campana_id=campana_id,
        incluir_anulados=incluir_anulados,
        hoy=dt.date.today(),
    )


@router.get("/estado/{parcela_id}")
def el_estado_de_una_tierra(
    parcela_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
) -> dict:
    """Solo el estado derivado: qué tiene sembrado, qué se ha hecho y qué queda previsto.

    Está separado de la historia porque hay pantallas —la lista de tierras, el panel— que solo
    necesitan esto, y porque un dato que se pide aparte se puede probar aparte. **Es la misma función**
    que usa la historia: no hay dos estados que puedan discrepar.
    """
    obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    hechos = [
        _una_labor_como_trabajo(db, labor)
        for labor in _las_labores(db, explotacion, parcela_id=parcela_id, campana_id=campana_id)
    ]
    planes = _los_previstos(db, explotacion, parcela_id=parcela_id, campana_id=campana_id)
    estado = logica.estado_de_una_tierra(
        hechos, planes, parcela_id=parcela_id, campana_id=campana_id, hoy=dt.date.today()
    )
    # Lo mismo que en la historia: sin cultivo deducido de las labores, se dice lo que él declaró.
    if estado.get("cultivo_declarado") is None:
        estado["cultivo_declarado"] = _el_cultivo_del_cuaderno(db, explotacion, parcela_id, campana_id)
    return estado


# --------------------------------------------------------------------------
# Planificar: lo previsto
# --------------------------------------------------------------------------


@router.get("/previstos")
def los_trabajos_previstos(
    explotacion: ExplotacionActual,
    db: Db,
    parcela_id: int | None = None,
    campana_id: int | None = None,
    estado: str | None = None,
) -> list[dict]:
    """Lo que está planificado, con lo que gastaría cada cosa **dicho como estimación**."""
    planes = _los_previstos(db, explotacion, parcela_id=parcela_id, campana_id=campana_id, estado=estado)
    return [
        {
            "previsto": plan,
            "gastaria": logica.estimacion_de_lo_previsto(plan),
            "dias_que_faltan": logica.dias_que_faltan(plan["fecha_prevista"], dt.date.today()),
        }
        for plan in planes
    ]


@router.post("/previstos", status_code=status.HTTP_201_CREATED)
def planificar_un_trabajo(
    datos: TrabajoPrevistoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    respuesta: Response,
    puede_modificar: PuedeModificar,
) -> dict:
    """Planificar un trabajo: **lo que se piensa hacer, que no ha pasado y no gasta nada**.

    Tres cuidados que están aquí porque son los que impiden los dos defectos clásicos de una agenda:

      1. **El reenvío no duplica el plan.** El móvil reintenta al volver la cobertura, así que la misma
         petición (la misma clave) devuelve el plan que ya había.
      2. **Lo que no se sabe se queda en blanco.** El día, la superficie y las horas son opcionales: un
         plan sin día se apunta igual y la pantalla dice que no se sabe cuándo toca. Poner hoy por
         defecto sería afirmar un día que nadie ha dicho.
      3. **El estado nace en `previsto`**, que aquí sí es un valor por defecto correcto: una fila de
         esta tabla es un plan porque esta tabla es donde se apuntan los planes (en la tabla de hechos
         el mismo valor por defecto sería un defecto; ver `app/trabajos.py`).
    """
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is None and datos.grupo_id is None:
        raise HTTPException(status_code=422, detail=textos.mensaje("V18_sin_parcela"))
    if datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    if datos.equipo_id is not None:
        # La máquina tiene que ser suya, y **no se comprueba aquí la ITEAF**: un plan se puede apuntar
        # meses antes y la inspección se mira el día que se hace (es lo que hace la maquinaria).
        obtener_de_la_explotacion(db, models.EquipoAplicacion, datos.equipo_id, explotacion.id)

    clave = _la_clave(datos)
    if clave:
        ya = db.scalar(
            select(models.TrabajoPrevisto).where(
                models.TrabajoPrevisto.explotacion_id == explotacion.id,
                models.TrabajoPrevisto.clave_de_reenvio == clave,
            )
        )
        if ya is not None:
            # ***Y si la misma clave trae OTROS datos, 409*** (CRM-05, 17/10/2026): *devolver el plan que
            # habia sin mirar seria dar por guardado algo que **no se guardo**.*
            ya = reenvios.lo_que_contesta(
                ya, datos, traducir=LAS_HORAS_DEL_PLAN, tambien=_lo_compuesto(db)
            )
            respuesta.status_code = status.HTTP_200_OK
            return {
                "previsto": _los_previstos(db, explotacion, parcela_id=ya.parcela_id)[0],
                "ya_estaba": True,
            }

    plan = models.TrabajoPrevisto(
        explotacion_id=explotacion.id,
        campana_id=datos.campana_id,
        tipo=datos.tipo,
        subtipo=(datos.subtipo or "").strip()[:30] or None,
        # Nace previsto, y consta por escrito por qué aquí sí (ver el docstring).
        estado="previsto",
        fecha_prevista=datos.fecha_prevista,
        fecha_fin_prevista=datos.fecha_fin_prevista,
        parcela_id=datos.parcela_id,
        grupo_id=datos.grupo_id,
        superficie_ha=datos.superficie_ha,
        cultivo=(datos.cultivo or "").strip()[:120] or None,
        variedad=(datos.variedad or "").strip()[:120] or None,
        equipo_id=datos.equipo_id,
        persona=(datos.persona or "").strip()[:120] or None,
        # Las horas que se piensa estar, que no son las que se estuvo: hasta que no se haga, esto es
        # una previsión y se enseña como tal.
        horas_previstas=datos.horas,
        observaciones=(datos.observaciones or "").strip()[:500] or None,
        clave_de_reenvio=clave,
    )
    db.add(plan)
    try:
        # ***El `flush` es donde se ESCRIBE la fila*** (CRM-05, 17/10/2026): *el choque del indice salta
        # aqui, no al confirmar al final. Sin este `try`, dos peticiones simultaneas que pasen las dos la
        # consulta de «¿ya esta?» dejan a una con un **500** en vez del plan que ya estaba.*
        #
        # *Y aqui el `flush` **no se puede mover** al final: las lineas del plan necesitan `plan.id`, que
        # no existe hasta que la fila va a la base.*
        db.flush()
    except IntegrityError:
        db.rollback()
        ya = db.scalar(
            select(models.TrabajoPrevisto).where(
                models.TrabajoPrevisto.explotacion_id == explotacion.id,
                models.TrabajoPrevisto.clave_de_reenvio == clave,
            )
        )
        if ya is None:
            raise
        # **El mismo 409, por el mismo camino.**
        ya = reenvios.lo_que_contesta(
            ya, datos, traducir=LAS_HORAS_DEL_PLAN, tambien=_lo_compuesto(db)
        )
        respuesta.status_code = status.HTTP_200_OK
        return {
            "previsto": _los_previstos(db, explotacion, parcela_id=ya.parcela_id)[0],
            "ya_estaba": True,
        }

    for linea in datos.lineas or []:
        obtener_de_la_explotacion(db, models.Parcela, linea.parcela_id, explotacion.id)
        db.add(
            models.LineaDeTrabajoPrevisto(
                explotacion_id=explotacion.id,
                trabajo_previsto_id=plan.id,
                parcela_id=linea.parcela_id,
                superficie_ha=linea.superficie_ha,
                cantidad=linea.cantidad,
                unidad=(linea.unidad or "").strip()[:10] or None,
                dosis_por_ha=linea.dosis_por_ha,
                articulo_id=linea.articulo_id,
                lote_id=linea.lote_id,
                horas=linea.horas,
                observaciones=(linea.observaciones or "").strip()[:500] or None,
            )
        )

    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="trabajo_previsto",
            entidad_id=plan.id,
            accion="planificar",
            datos={
                "tipo": plan.tipo,
                "subtipo": plan.subtipo,
                "tierra": plan.parcela_id,
                "fecha_prevista": logica.como_json(plan.fecha_prevista),
                "superficie_ha": plan.superficie_ha,
                # **Escrito en el rastro**: esto no ha gastado nada, y dentro de un año hay que poder
                # verlo sin saber de memoria cómo funcionaba el programa.
                "consume_existencias": False,
            },
        )
    )
    if clave is None:
        # Sin clave no se puede comprobar un reenvío, y eso se dice en vez de dar por bueno que no lo hay.
        aviso = textos.mensaje("TJ12_no_se_pudo_comprobar_si_ya_estaba")
    else:
        aviso = ""
    db.commit()
    db.refresh(plan)
    return {"previsto": _los_previstos(db, explotacion, parcela_id=plan.parcela_id)[0], "aviso": aviso}


@router.put("/previstos/{previsto_id}")
def corregir_un_trabajo_previsto(
    previsto_id: int,
    datos: TrabajoPrevistoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Corregir un plan. Se cambia la fila que ya estaba y queda el rastro de qué decía antes.

    **Corregir un plan no es reprogramarlo**: si lo que cambia es el día, el cambio pasa por
    `logica.reprogramar`, que deja escrito el día que tenía antes. Aquí se corrigen los demás datos
    —la tierra, la máquina, lo que se piensa gastar—, y todo con las mismas comprobaciones que al
    planificar: que la tierra y la máquina sean de esta finca.
    """
    plan = obtener_de_la_explotacion(db, models.TrabajoPrevisto, previsto_id, explotacion.id)
    enviados = datos.model_fields_set
    if "parcela_id" in enviados and datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    if "equipo_id" in enviados and datos.equipo_id is not None:
        obtener_de_la_explotacion(db, models.EquipoAplicacion, datos.equipo_id, explotacion.id)

    def suyo(campo, lo_que_habia):
        """Lo que la petición no manda **se queda como estaba**: no es «bórralo», es «de eso no hablo»."""
        return getattr(datos, campo) if campo in enviados else lo_que_habia

    preparado = models.TrabajoPrevisto(
        explotacion_id=explotacion.id,
        campana_id=suyo("campana_id", plan.campana_id),
        tipo=suyo("tipo", plan.tipo),
        subtipo=suyo("subtipo", plan.subtipo),
        estado=plan.estado,
        fecha_prevista=suyo("fecha_prevista", plan.fecha_prevista),
        fecha_prevista_antes=plan.fecha_prevista_antes,
        fecha_fin_prevista=suyo("fecha_fin_prevista", plan.fecha_fin_prevista),
        parcela_id=suyo("parcela_id", plan.parcela_id),
        grupo_id=suyo("grupo_id", plan.grupo_id),
        superficie_ha=suyo("superficie_ha", plan.superficie_ha),
        cultivo=suyo("cultivo", plan.cultivo),
        variedad=suyo("variedad", plan.variedad),
        equipo_id=suyo("equipo_id", plan.equipo_id),
        persona=suyo("persona", plan.persona),
        horas_previstas=suyo("horas", plan.horas_previstas),
        observaciones=suyo("observaciones", plan.observaciones),
        # La clave de reenvío **no se toca**: si se perdiera, un reenvío de la petición original ya no
        # reconocería este plan y apuntaría otro.
        clave_de_reenvio=plan.clave_de_reenvio,
        # Y lo que el bucle de `correcciones` copiaría a nulo si no se copiara aquí, porque esa lista
        # está escrita para otras tablas.
        creado_en=plan.creado_en,
    )
    correcciones.corregir(
        db,
        guardado=plan,
        preparado=preparado,
        entidad="trabajo_previsto",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"previsto": _los_previstos(db, explotacion, parcela_id=plan.parcela_id)[0]}


@router.post("/previstos/{previsto_id}/reprogramar")
def reprogramar_un_trabajo_previsto(
    previsto_id: int,
    datos: ReprogramarEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Mover un plan a otro día. **Lo que ya se hizo no se mueve**, y se dice por qué.

    El contrato lo pide con esas palabras: «reprogramar no cambia fecha de un trabajo ya realizado». Un
    trabajo hecho tiene la fecha del día en que se hizo, y esa fecha es la que va al cuaderno.
    """
    plan = obtener_de_la_explotacion(db, models.TrabajoPrevisto, previsto_id, explotacion.id)
    antes = plan.fecha_prevista
    cambio = logica.reprogramar(
        logica.un_trabajo(
            id=plan.id, de_donde="previsto", estado=plan.estado, fecha_prevista=plan.fecha_prevista
        ),
        datos.fecha_prevista,
        motivo=datos.motivo,
    )
    if not cambio["cambiado"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=textos.mensaje(cambio["motivo_codigo"])
        )
    plan.fecha_prevista_antes = antes
    plan.fecha_prevista = cambio["trabajo"]["fecha_prevista"]
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="trabajo_previsto",
            entidad_id=plan.id,
            accion="reprogramar",
            datos={
                "cambios": logica.como_json(cambio["cambios"]),
                "motivo": (datos.motivo or "").strip()[:500] or None,
            },
        )
    )
    db.commit()
    db.refresh(plan)
    return {"previsto": _los_previstos(db, explotacion, parcela_id=plan.parcela_id)[0]}


@router.post("/previstos/{previsto_id}/cancelar")
def cancelar_un_trabajo_previsto(
    previsto_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Cancelar un plan, con su motivo. **El plan no se borra**: queda cancelado y se puede leer.

    Un plan cancelado no se convierte en un hecho nunca (lo que hubo fue otra cosa) y no cuenta como
    pendiente. Y no es lo mismo que anular un hecho: **anular pertenece a lo que ya pasó** (lo dice el
    contrato con esas palabras), así que un plan se cancela.
    """
    plan = obtener_de_la_explotacion(db, models.TrabajoPrevisto, previsto_id, explotacion.id)
    motivo = (datos.motivo or "").strip()
    if len(motivo) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("TJ5_falta_el_motivo_para_anular"),
        )
    if plan.estado == "realizado":
        # **Un plan ya cumplido no se cancela**: el hecho está apuntado y la tierra ya se trabajó.
        # Cancelarlo dejaría el hecho apuntando a un plan que dice que no se hizo.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("TJ17_un_plan_no_es_un_trabajo"),
        )
    plan.estado = "cancelado"
    plan.motivo_cancelacion = motivo[:500]
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="trabajo_previsto",
            entidad_id=plan.id,
            accion="cancelar",
            datos={"motivo": plan.motivo_cancelacion},
        )
    )
    db.commit()
    return {"previsto": _los_previstos(db, explotacion, parcela_id=plan.parcela_id)[0]}


# --------------------------------------------------------------------------
# Marcar lo que de verdad se hizo
# --------------------------------------------------------------------------


def _la_labor_del_trabajo(datos: TrabajoEntrada, explotacion, db) -> models.Labor:
    """Comprueba un trabajo y devuelve la labor lista para guardar, **sin guardarla**.

    Son las mismas tres comprobaciones que hace el alta de labores del cuaderno
    (`registros._preparar_labor_guardable`): la campaña es de esta finca, la labor es de una tierra o de
    un grupo (nunca de nada), y la máquina es suya. Están escritas otra vez aquí en vez de llamar a
    aquella porque aquella recibe un `LaborEntrada` y esta puerta recibe un `TrabajoEntrada` con el
    subtipo y las horas; si el coordinador prefiere una sola, esta es la que se puede borrar.

    Y una cosa que **no** se comprueba aquí a propósito: la ITEAF de la máquina. Una labor se puede
    hacer con un tractor que no la necesita, y eso ya lo dice la maquinaria en su pantalla.
    """
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is None and datos.grupo_id is None:
        raise HTTPException(status_code=422, detail=textos.mensaje("V18_sin_parcela"))
    if datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    if datos.equipo_id is not None:
        obtener_de_la_explotacion(db, models.EquipoAplicacion, datos.equipo_id, explotacion.id)

    labor = models.Labor(
        explotacion_id=explotacion.id,
        campana_id=datos.campana_id,
        tipo=datos.tipo,
        fecha=datos.fecha,
        parcela_id=datos.parcela_id,
        grupo_id=datos.grupo_id,
        superficie_ha=datos.superficie_ha,
        cultivo=(datos.cultivo or "").strip()[:120] or None,
        variedad=(datos.variedad or "").strip()[:120] or None,
        equipo_id=datos.equipo_id,
        horas=datos.horas,
        observaciones=(datos.observaciones or "").strip()[:500] or None,
        clave_de_reenvio=_la_clave(datos),
        previsto_id=datos.previsto_id,
        # **El subtipo va en su columna** (06/10/2026). Aquí ponía `detalles={"subtipo": …}` con el
        # comentario «va en su columna cuando exista, y mientras no exista en `detalles`»: la columna
        # **existe desde que se integró el T15**, y la regla de la casa es que un dato del contrato
        # —y el subtipo lo es (§4, S05): «con nombre y número»— viva en su columna y no en un JSON de
        # texto libre, que no se puede consultar ni sumar. `_el_subtipo` lee la columna primero y
        # `detalles` después, así que los apuntes escritos antes de esto se siguen leyendo igual.
        subtipo=(datos.subtipo or "").strip()[:30] or None,
    )
    if not labor.cultivo:
        # El cultivo, igual que en el resto del programa: si el apunte no lo trae, se pone el que el
        # agricultor ya dijo que hay en esa parcela este año.
        declarado = servicios.cultivo_declarado(
            db,
            explotacion_id=explotacion.id,
            parcela_id=datos.parcela_id,
            campana_id=datos.campana_id,
        )
        if declarado is not None:
            labor.cultivo = declarado.especie
    return labor


def _sacar_lo_que_gasto_el_trabajo(
    *,
    db,
    explotacion,
    usuario,
    labor: models.Labor,
    datos: TrabajoEntrada,
    avisos: list[str],
) -> None:
    """Saca del almacén lo que gastó el trabajo, **por la puerta de las salidas que ya existe**.

    Esta función no resta nada por su cuenta: llama a `almacen_api.sacar_de_un_lote`, que es el único
    sitio del programa que saca producto de un envase dejando un apunte detrás. Así el trabajo hereda
    todo lo que esa puerta ya hace bien (el reenvío, el aviso de que el envase se queda en negativo, la
    unidad del lote y la auditoría) y no hay dos formas de descontar que un día digan cosas distintas.

    Y lo que no se sabe **no se resta**: sin cantidad, sin unidad o sin envase se dice por qué y no se
    toca el almacén. Restar «lo que sea» sería peor que no restar.
    """
    for insumo in datos.insumos or []:
        if insumo.cantidad is None:
            avisos.append(textos.mensaje("TJ21_falta_la_cantidad"))
            continue
        if not (insumo.unidad or "").strip():
            avisos.append(textos.mensaje("TJ22_falta_la_unidad"))
            continue
        if insumo.lote_id is None:
            # Se sabe cuánto, pero no de dónde sale. Aquí está lo que evita restar de un envase que no es.
            avisos.append(textos.mensaje("TJ26_el_apunte_del_consumo_no_esta"))
            continue
        sacar_de_un_lote(
            datos=SalidaDeAlmacenEntrada(
                apunte_tipo="labor",
                apunte_id=labor.id,
                lote_id=insumo.lote_id,
                cantidad=insumo.cantidad,
                unidad=insumo.unidad,
                fecha=labor.fecha,
                motivo=None,
                aceptar_descuadre=insumo.aceptar_descuadre,
                # **Sin clave de reenvío propia, y esto es a propósito.** Aquí se puso en el T10
                # `«{clave}:salida»` y hacía daño: si el agricultor anulaba el apunte y la cola del móvil
                # reenviaba la misma petición, la salida nueva no se apuntaba porque la puerta encontraba
                # por esa clave la salida VIEJA —que sigue viva: solo su apunte está anulado—. La
                # protección de verdad es la comprobación por apunte y envase, y el reenvío de la misma
                # petición lo corta antes el alta del trabajo, que lo reconoce por su clave.
                clave_de_reenvio=None,
            ),
            explotacion=explotacion,
            usuario=usuario,
            db=db,
            respuesta=Response(),
                    # ***Llamada INTERNA, no una peticion de la pantalla*** (17/10/2026): *esta funcion
            # **usa la misma puerta a proposito** -para que la regla viva en un solo sitio-, y quien
            # llama es el propio programa, no una cuenta. Pasarle `None` es decir la verdad: **no hay
            # una cuenta detras a la que preguntarle**.*
            puede_modificar=None,
)


@router.post("/previstos/{previsto_id}/hecho", status_code=status.HTTP_201_CREATED)
def marcar_lo_que_de_verdad_se_hizo(
    previsto_id: int,
    datos: MarcarHechoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """**Lo planificado se cumple apuntando lo que pasó**, con su día y lo que se gastó de verdad.

    Aquí está el caso A05 al derecho: un plan **no** se convierte en un trabajo hecho por parecerse a
    él, ni por su fecha, ni por su tipo. El agricultor dice lo que de verdad hizo —que casi nunca es
    exactamente lo que había planeado— y eso es lo que se apunta: su día real, sus hectáreas reales,
    sus horas reales y el producto que de verdad salió del almacén.

    El plan queda `realizado` y apunta al hecho. **Y si el plan ya estaba cumplido, esto contesta 409**:
    si se hizo otra vez, es otro trabajo.

    Lo que se hace, en orden:

      1. Se comprueba que el plan es de esta finca y que no está ya cumplido ni cancelado.
      2. Se prepara y se guarda el hecho (la labor), con el vínculo al plan.
      3. **Se descuenta del almacén lo que dice el hecho**, por la puerta de las salidas.
      4. Se apunta en el rastro. Y el hecho, si se corrige o se anula después, arrastra su salida sin
         que haga falta deshacer ninguna resta.
    """
    plan = obtener_de_la_explotacion(db, models.TrabajoPrevisto, previsto_id, explotacion.id)
    hecho_previsto = logica.un_trabajo(
        id=plan.id,
        de_donde="previsto",
        estado=plan.estado,
        tipo=plan.tipo,
        subtipo=plan.subtipo,
        fecha_prevista=plan.fecha_prevista,
        parcela_id=plan.parcela_id,
    )

    clave = _la_clave(datos)
    if clave:
        ya = db.scalar(
            select(models.Labor).where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.clave_de_reenvio == clave,
                models.Labor.anulado.is_(False),
            )
        )
        if ya is not None:
            # ***Y si la misma clave trae OTROS datos, 409*** (CRM-05, 17/10/2026).
            reenvios.lo_que_contesta(ya, datos, tambien=_lo_compuesto(db))
            # La cola del móvil reintenta: se devuelve el trabajo que ya había **sin volver a descontar**.
            return {
                "hecho": _una_labor_como_trabajo(db, ya),
                "ya_estaba": True,
                "aviso": textos.mensaje("TJ11_el_trabajo_ya_estaba"),
            }

    labor = _la_labor_del_trabajo(
        TrabajoEntrada(
            campana_id=plan.campana_id,
            tipo=plan.tipo,
            subtipo=plan.subtipo,
            fecha=datos.fecha,
            parcela_id=plan.parcela_id,
            grupo_id=plan.grupo_id,
            superficie_ha=datos.superficie_ha if datos.superficie_ha is not None else plan.superficie_ha,
            cultivo=datos.cultivo if datos.cultivo is not None else plan.cultivo,
            variedad=datos.variedad if datos.variedad is not None else plan.variedad,
            equipo_id=datos.equipo_id if datos.equipo_id is not None else plan.equipo_id,
            horas=datos.horas,
            observaciones=datos.observaciones,
            insumos=datos.insumos,
            previsto_id=plan.id,
            clave_de_reenvio=clave,
            id_local=datos.id_local,
        ),
        explotacion,
        db,
    )
    comprobado = logica.marcar_como_hecho(
        hecho_previsto, logica.un_hecho(id=labor.id, tipo=labor.tipo, fecha=labor.fecha)
    )
    if not comprobado["se_puede"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=textos.mensaje(comprobado["motivo_codigo"])
        )

    db.add(labor)
    db.flush()
    avisos: list[str] = []
    _sacar_lo_que_gasto_el_trabajo(
        db=db, explotacion=explotacion, usuario=usuario, labor=labor, datos=datos, avisos=avisos
    )

    plan.estado = "realizado"
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="trabajo_previsto",
            entidad_id=plan.id,
            accion="marcar_hecho",
            datos={
                "hecho_id": labor.id,
                "cambios": logica.como_json(comprobado["lo_que_cambia"]),
                # Lo que se apuntó de verdad, que casi nunca es exactamente lo planificado: es lo que
                # permite ver dentro de un año qué se hizo y qué se había pensado.
                "fecha_prevista": logica.como_json(plan.fecha_prevista),
                "fecha_hecha": logica.como_json(labor.fecha),
                "superficie_prevista_ha": plan.superficie_ha,
                "superficie_hecha_ha": labor.superficie_ha,
            },
        )
    )
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="labor",
            entidad_id=labor.id,
            accion="crear",
            datos={
                "tipo": labor.tipo,
                # **El subtipo es el de la labor, no `datos.subtipo`** (06/10/2026). Aquí ponía
                # `datos.subtipo`, y `MarcarHechoEntrada` **no tiene ese campo**: marcar un plan como
                # hecho contestaba **500** siempre, con un `AttributeError`, así que la segunda mitad del
                # recorrido 4 —«planificar un trabajo → marcar lo que de verdad se hizo»— **no se podía
                # hacer desde la aplicación**. Se encontró recorriendo ese recorrido en un navegador de
                # verdad: la pantalla decía «No se ha podido» y el registro del servidor tenía la traza.
                # El dato bueno es el de la labor que se acaba de crear, que es la que guarda el apero
                # (y viene del plan, que es de donde sale el trabajo).
                "subtipo": labor.subtipo,
                "tierra": labor.parcela_id,
                "fecha": logica.como_json(labor.fecha),
                "superficie_ha": labor.superficie_ha,
                "horas": labor.horas,
                "de_que_plan": plan.id,
            },
        )
    )
    try:
        # ***Y aqui el `commit` es el que escribe*** (CRM-05, 17/10/2026): *esta puerta **no hace `flush`**,
        # asi que la fila de la labor va a la base al confirmar. Es el mismo caso que la averia de la
        # maquina, y el `try` va aqui por el mismo motivo: **sin el, la que pierde la carrera ve un 500
        # en vez del trabajo que ya estaba apuntado**.*
        db.commit()
    except IntegrityError:
        db.rollback()
        # **La misma busqueda que la de arriba**, con el mismo filtro: *una labor **anulada** no cuenta, y
        # anular existe justo para poder volver a apuntar el trabajo.*
        ya = db.scalar(
            select(models.Labor).where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.clave_de_reenvio == clave,
                models.Labor.anulado.is_(False),
            )
        )
        if ya is None:
            raise
        # **El mismo 409, por el mismo camino**, antes de montar la respuesta.
        reenvios.lo_que_contesta(ya, datos, tambien=_lo_compuesto(db))
        return {
            "hecho": _una_labor_como_trabajo(db, ya),
            "ya_estaba": True,
            "aviso": textos.mensaje("TJ11_el_trabajo_ya_estaba"),
        }
    db.refresh(labor)
    return {
        "hecho": _una_labor_como_trabajo(db, labor),
        "previsto": _los_previstos(db, explotacion, parcela_id=plan.parcela_id)[0],
        "ya_estaba": False,
        "avisos": avisos,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def apuntar_un_trabajo_hecho(
    datos: TrabajoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    respuesta: Response,
    puede_modificar: PuedeModificar,
) -> dict:
    """Apuntar un trabajo que **ya se ha hecho** (sin plan detrás): rodillo, cultivador, escarda…

    Es la puerta que el agricultor usará desde el campo la mayoría de las veces: «he pasado el rodillo en
    El Prado». Lo que se apunta es un hecho; lo que se gasta sale del almacén por la puerta de las
    salidas; y **reenviar desde el móvil no duplica nada**, porque la clave de reenvío lo reconoce y
    devuelve el trabajo que ya había.
    """
    clave = _la_clave(datos)
    if clave:
        ya = db.scalar(
            select(models.Labor).where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.clave_de_reenvio == clave,
                models.Labor.anulado.is_(False),
            )
        )
        if ya is not None:
            # ***Y si la misma clave trae OTROS datos, 409*** (18/10/2026, y esto faltaba): *el 409 estaba **solo
            # en el camino del `except IntegrityError`**, asi que en el caso **normal** -un reintento, que es el
            # que pasa siempre- la puerta salia por aqui **sin mirar nada**. Un reintento con **otros kilos**
            # devolvia la labor vieja con «ya estaba» **y el almacen se quedaba con el descuento de la primera
            # vez**. Lo encontro la prueba de los insumos con envase.*
            reenvios.lo_que_contesta(ya, datos, tambien=_lo_compuesto(db))
            respuesta.status_code = status.HTTP_200_OK
            return {
                "hecho": _una_labor_como_trabajo(db, ya),
                "ya_estaba": True,
                "aviso": textos.mensaje("TJ11_el_trabajo_ya_estaba"),
            }

    labor = _la_labor_del_trabajo(datos, explotacion, db)
    db.add(labor)
    db.flush()
    avisos: list[str] = []
    _sacar_lo_que_gasto_el_trabajo(
        db=db, explotacion=explotacion, usuario=usuario, labor=labor, datos=datos, avisos=avisos
    )
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="labor",
            entidad_id=labor.id,
            accion="crear",
            datos={
                "tipo": labor.tipo,
                "subtipo": datos.subtipo,
                "tierra": labor.parcela_id,
                "fecha": logica.como_json(labor.fecha),
                "superficie_ha": labor.superficie_ha,
                "horas": labor.horas,
                "clave_de_reenvio": clave,
            },
        )
    )
    if clave is None:
        avisos.append(textos.mensaje("TJ12_no_se_pudo_comprobar_si_ya_estaba"))
    try:
        # ***Y aqui el `commit` es el que escribe*** (CRM-05, 17/10/2026): *esta puerta tampoco hace
        # `flush`, asi que la labor va a la base al confirmar. **Sin el `try`, la que pierde la carrera ve
        # un 500** en vez del trabajo que ya estaba apuntado -y es la puerta que el agricultor usa desde el
        # campo la mayoria de las veces-.*
        db.commit()
    except IntegrityError:
        db.rollback()
        ya = db.scalar(
            select(models.Labor).where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.clave_de_reenvio == clave,
                models.Labor.anulado.is_(False),
            )
        )
        if ya is None:
            raise
        # **El mismo 409, por el mismo camino**, antes de montar la respuesta.
        reenvios.lo_que_contesta(ya, datos, tambien=_lo_compuesto(db))
        return {
            "hecho": _una_labor_como_trabajo(db, ya),
            "ya_estaba": True,
            "aviso": textos.mensaje("TJ11_el_trabajo_ya_estaba"),
        }
    db.refresh(labor)
    return {"hecho": _una_labor_como_trabajo(db, labor), "ya_estaba": False, "avisos": avisos}


# --------------------------------------------------------------------------
# Corregir y anular un trabajo hecho
# --------------------------------------------------------------------------


@router.put("/{labor_id}")
def corregir_un_trabajo_hecho(
    labor_id: int,
    datos: TrabajoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Corregir un trabajo **sin que queden dos descuentos ni se toque lo firmado**.

    Es la parte del ticket que más cuidado tiene, y se resuelve así:

      · Lo que cambia del trabajo se corrige **en la misma fila** y en el rastro queda qué decía antes,
        campo por campo (`correcciones.corregir`). El identificador es el que viaja a la Junta, así que
        corregir aquí es lo que hace que una actividad corregida sea **la misma** y no dos.
      · Si lo que cambia es **lo que salió del almacén**, la salida vieja se anula (con su motivo: se
        corrigió el trabajo) y se apunta una nueva por la puerta de las salidas. Nunca quedan dos vivas,
        y nunca se reescribe la cantidad de un movimiento por detrás.
      · **Un apunte firmado no se cambia por detrás**: lo que se firmó sigue siendo lo que se firmó, y
        la corrección queda como revisión nueva (A14). Se dice antes de tocar nada.
    """
    labor = obtener_de_la_explotacion(db, models.Labor, labor_id, explotacion.id)
    if labor.anulado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=textos.mensaje("TJ3_el_apunte_esta_anulado")
        )
    firmas = correcciones.firmas_de_un_apunte(
        db, explotacion_id=explotacion.id, entidad="labor", entidad_id=labor.id
    )
    # **Lo que la petición no manda se queda como estaba.** Es la regla de siempre en este programa: una
    # petición que no manda la fecha no está diciendo que no había fecha, está diciendo que de eso no
    # habla. Sin esta mezcla, corregir las horas desde fuera de la pantalla dejaría el trabajo sin día,
    # que es el día que se enseña en una inspección.
    enviados = datos.model_fields_set

    def suyo(campo, lo_que_habia):
        return getattr(datos, campo) if campo in enviados else lo_que_habia

    lo_que_hay = {
        "campana_id": suyo("campana_id", labor.campana_id),
        "tipo": suyo("tipo", labor.tipo),
        "subtipo": suyo("subtipo", _el_subtipo(labor)),
        "fecha": suyo("fecha", labor.fecha),
        "parcela_id": suyo("parcela_id", labor.parcela_id),
        "grupo_id": suyo("grupo_id", labor.grupo_id),
        "superficie_ha": suyo("superficie_ha", labor.superficie_ha),
        "cultivo": suyo("cultivo", labor.cultivo),
        "variedad": suyo("variedad", labor.variedad),
        "equipo_id": suyo("equipo_id", labor.equipo_id),
        "horas": suyo("horas", getattr(labor, "horas", None)),
        "observaciones": suyo("observaciones", labor.observaciones),
    }
    preparada = _la_labor_del_trabajo(
        # `insumos` no va aquí a propósito: lo que salió del almacén se mira después, y solo si la
        # petición habla de ello. Un formulario que no pregunta los insumos no puede vaciarlos.
        TrabajoEntrada(**lo_que_hay, insumos=None, previsto_id=labor.previsto_id),
        explotacion,
        db,
    )
    preparada.clave_de_reenvio = labor.clave_de_reenvio
    preparada.anulado = labor.anulado
    preparada.motivo_anulacion = labor.motivo_anulacion
    preparada.creado_en = labor.creado_en

    correcciones.corregir(
        db,
        guardado=labor,
        preparado=preparada,
        entidad="labor",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )

    # Lo que salió del almacén se mira **después** de corregir, y con la lógica pura: se comparan las
    # salidas vivas con lo que el trabajo dice ahora. Si nada de eso cambió, el almacén no se toca.
    antes = _una_labor_como_trabajo(db, labor)
    avisos: list[str] = []
    if datos.insumos is not None:
        vivas = [insumo for insumo in antes["insumos"] if not insumo["anulado"]]
        cambios = logica.corregir(
            logica.un_hecho(id=labor.id, insumos=vivas),
            {"insumos": [logica.un_insumo(**insumo.model_dump()) for insumo in datos.insumos]},
        )
        if cambios["hay_que_tocar_el_almacen"]:
            for vieja in vivas:
                movimiento = db.get(models.MovimientoDeExistencias, vieja["movimiento_id"])
                if movimiento is None or movimiento.anulado:
                    continue
                movimiento.anulado = True
                movimiento.motivo_anulacion = textos.mensaje("TJ4_lo_que_salio_cambio")
                db.add(
                    models.Auditoria(
                        explotacion_id=explotacion.id,
                        usuario_id=usuario.id,
                        entidad="movimiento_de_existencias",
                        entidad_id=movimiento.id,
                        accion="anular",
                        datos={"motivo": movimiento.motivo_anulacion, "por": f"trabajo {labor.id}"},
                    )
                )
            db.flush()
            _sacar_lo_que_gasto_el_trabajo(
                db=db,
                explotacion=explotacion,
                usuario=usuario,
                labor=labor,
                datos=TrabajoEntrada(
                    campana_id=labor.campana_id,
                    tipo=labor.tipo,
                    fecha=labor.fecha,
                    parcela_id=labor.parcela_id,
                    insumos=datos.insumos,
                ),
                avisos=avisos,
            )
            avisos.append(textos.mensaje("TJ4_lo_que_salio_cambio"))
            db.commit()
    if firmas:
        # **Y se dice**: el apunte estaba firmado, así que esta corrección es una revisión nueva y la
        # firma antigua sigue valiendo para lo que se firmó.
        avisos.append(textos.mensaje("TJ19_la_revision_de_lo_firmado"))
    db.refresh(labor)
    return {
        "hecho": _una_labor_como_trabajo(db, labor),
        "corregido": True,
        "revision_nueva": bool(firmas),
        "avisos": avisos,
    }


@router.post("/{labor_id}/anular")
def anular_un_trabajo_hecho(
    labor_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Anular un trabajo, con su motivo. **Y lo que gastó vuelve a contar, sin tocar el libro.**

    Esto es lo mejor de haber hecho que el producto salga por la puerta de las salidas: anular el
    trabajo devuelve al almacén lo que salió **sin borrar ningún movimiento**. La salida se queda donde
    está, con su fecha, su cantidad y quién la apuntó, y deja de contar porque
    `servicios.estado_de_los_origenes` mira si la labor está anulada —igual que un tratamiento anulado:
    «anular 2 L devuelve 2»—. Nada se borra, y no hay dos descuentos que deshacer.

    Y **un apunte firmado también se puede anular**: lo que no se puede es borrarlo. Es la salida que
    tiene el agricultor cuando el programa le dice que un apunte firmado no se borra.
    """
    labor = obtener_de_la_explotacion(db, models.Labor, labor_id, explotacion.id)
    antes = _una_labor_como_trabajo(db, labor)
    cambio = logica.anular(antes, datos.motivo)
    if not cambio["anulado"]:
        codigo = status.HTTP_409_CONFLICT if cambio["ya_estaba"] else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=codigo, detail=textos.mensaje(cambio["motivo_codigo"]))

    vivas = [insumo for insumo in antes["insumos"] if not insumo["anulado"]]
    labor.anulado = True
    labor.motivo_anulacion = cambio["trabajo"]["motivo_anulacion"]
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="labor",
            entidad_id=labor.id,
            accion="anular",
            datos={
                "motivo": labor.motivo_anulacion,
                # Lo que vuelve a contar, apuntado: es lo que permite explicar por qué la existencia
                # subió sin que nadie tocara el libro.
                "salidas_que_dejan_de_contar": [insumo["movimiento_id"] for insumo in vivas],
            },
        )
    )
    db.commit()
    db.refresh(labor)
    return {
        "hecho": _una_labor_como_trabajo(db, labor),
        "anulado": True,
        "lo_que_vuelve_a_contar": [insumo["movimiento_id"] for insumo in vivas],
        "aviso": textos.mensaje("TJ3_el_apunte_esta_anulado") if vivas else "",
    }
