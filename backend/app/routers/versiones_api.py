"""Las versiones del recinto: mirarlas, compararlas e importarlas (T05, 02/10/2026).

## Qué puertas abre esto

Hasta ahora una tierra se podía mirar **como es hoy** (`/api/parcelas`) y no había ninguna forma de
preguntar **qué era en cada campaña ni quién lo dijo**. Estas cinco rutas son esa pregunta, y son
las que pide el contrato para T05 y para E2 («ensayar importación por lote, solapes y diferencias de
superficie»):

    POST /api/versiones/previsualizar         qué pasaría con un lote, sin tocar la base
    POST /api/versiones/aplicar               importar el lote (repetible: aplicarlo dos veces no
                                              duplica nada)
    GET  /api/versiones                       las versiones de una tierra, o de toda la finca
    GET  /api/versiones/comparar              igual/cambiado/desaparecido/nuevo de una tierra
    GET  /api/versiones/comparar-explotacion  lo mismo, de la finca entera

## El aislamiento entre fincas, que es lo que no se puede saltar

**Todo pasa por `explotacion`** (`deps.py`) y las tierras y los años se cogen con
`obtener_de_la_explotacion`, que devuelve **404 y no 403**: así no se filtra si un identificador
existe en el cuaderno de otro. Lo mismo dentro del servicio: una tierra del lote que no sea de esta
finca corta la importación entera con un 404, en vez de guardar el resto y callarse.

## Y lo que estas rutas no hacen

  · **La previsualización no escribe.** `POST /api/versiones/previsualizar` solo lee: se puede
    llamar cien veces antes de decidir, y el plan que devuelve es el mismo objeto que devuelve
    `aplicar` con `aplicada` en verdadero, así que lo que se enseña antes no puede diferir de lo que
    pasa después.
  · **No corrigen nada.** Los solapes y las diferencias de superficie se cuentan y se explican; el
    programa no toca una hectárea ni un vértice por su cuenta.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import models, schemas
from .. import versiones_de_recinto as versiones
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion

router = APIRouter(prefix="/api/versiones", tags=["versiones"])


def _campana_de_la_finca(db: Db, explotacion_id: int, campana_id: int) -> models.Campana:
    """Una campaña de esta finca, o 404. Nunca una de otra."""
    return obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion_id)


def _mirando_el_lote(funcion):
    """Ejecuta lo que toca con el lote, traduciendo su fallo a la respuesta que le corresponde.

    `LoteQueNoSePuedeAplicar` ya trae el mensaje escrito y el código (400 si falta un dato, 404 si
    algo es de otra finca). Se traduce aquí y no dentro del servicio porque el servicio no sabe nada
    de HTTP: es una capa de cuentas, no una capa de red.
    """
    try:
        return funcion()
    except versiones.LoteQueNoSePuedeAplicar as fallo:
        raise HTTPException(status_code=fallo.codigo_http, detail=fallo.mensaje) from fallo


@router.post("/previsualizar", response_model=schemas.PlanDeImportacion)
def previsualizar(
    datos: schemas.LoteDeRecintosEntrada,
    explotacion: ExplotacionActual,
    db: Db,
) -> schemas.PlanDeImportacion:
    """**Qué pasaría** si se importara este lote. No escribe nada.

    Devuelve los cuatro números que hay que mirar antes de decidir (nuevos, cambiados, iguales y sin
    forma), el detalle de cada recinto con el porqué de su estado, los solapes que se han visto
    entre recintos y las diferencias de superficie que no cuadran. Es la mitad de la importación
    repetible del contrato: primero se ensaya, y después se aplica.
    """
    return _mirando_el_lote(lambda: versiones.plan_de_importacion(db, explotacion.id, datos))


@router.post("/aplicar", response_model=schemas.PlanDeImportacion)
def aplicar(
    datos: schemas.LoteDeRecintosEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> schemas.PlanDeImportacion:
    """Importa el lote. Aplicarlo dos veces con los mismos datos **no escribe nada la segunda vez**.

    Devuelve el mismo plan que la previsualización, con `aplicada` en verdadero y con lo que de
    verdad se ha escrito (`versiones_creadas`, `versiones_actualizadas`, `tierras_creadas`), para
    que se pueda comprobar contra el plan en vez de creérselo.

    **No toca el alias, las notas ni el historial de ninguna tierra**: el nombre de una tierra es del
    agricultor y no viene de ninguna fuente. Lo único que crea es una tierra que no existía, y solo
    cuando el lote trae su referencia completa.
    """
    return _mirando_el_lote(
        lambda: versiones.aplicar_importacion(db, explotacion, datos, usuario.id)
    )


@router.get("", response_model=list[schemas.VersionDeRecintoSalida])
def listar(
    explotacion: ExplotacionActual,
    db: Db,
    parcela_id: int | None = None,
    campana_id: int | None = None,
    fuente: str | None = None,
) -> list[schemas.VersionDeRecintoSalida]:
    """Las versiones de una tierra, o de la finca entera, de la campaña más nueva a la más vieja.

    **Un recinto sin forma sale en esta lista**, con `tiene_forma` en falso y su frase («Sin forma:
    no ha venido el polígono»). Es lo que pide el contrato: una fila sin polígono sigue en la tabla y
    en el grupo «sin forma»; lo que no se hace es dibujarle una forma que nadie ha medido.
    """
    if parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    if campana_id is not None:
        _campana_de_la_finca(db, explotacion.id, campana_id)
    return versiones.listar(
        db,
        explotacion.id,
        parcela_id=parcela_id,
        campana_id=campana_id,
        fuente=fuente,
    )


@router.get("/comparar", response_model=schemas.ComparacionDeVersiones)
def comparar(
    explotacion: ExplotacionActual,
    db: Db,
    parcela_id: int,
    campana_antes: int,
    campana_despues: int,
    fuente: str | None = None,
) -> schemas.ComparacionDeVersiones:
    """`igual / cambiado / desaparecido / nuevo` de **una tierra**, con el porqué de cada uno.

    El porqué es la mitad del valor: no basta con saber que un recinto cambió, hay que saber **qué**
    cambió («la forma del trozo», «las hectáreas que declaras», «la superficie del SIGPAC»).

    **Comparar no escribe nada**, así que se puede pedir tantas veces como haga falta. Y una versión
    de la campaña vieja **sigue diciendo lo mismo** después de importar la nueva: cada campaña tiene
    su fila, y comparar solo las lee.
    """
    obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    return versiones.comparar_dos_campanas(
        db,
        explotacion.id,
        _campana_de_la_finca(db, explotacion.id, campana_antes),
        _campana_de_la_finca(db, explotacion.id, campana_despues),
        parcela_id=parcela_id,
        fuente=fuente,
    )


@router.get("/comparar-explotacion", response_model=schemas.ComparacionDeVersiones)
def comparar_explotacion(
    explotacion: ExplotacionActual,
    db: Db,
    campana_antes: int,
    campana_despues: int,
    fuente: str | None = None,
) -> schemas.ComparacionDeVersiones:
    """Lo mismo, pero de **toda la finca**: qué recintos aparecieron, cuáles cambiaron y cuáles ya no
    vienen.

    Cada cambio trae su tierra (`tierra`, `parcela_id`), porque en una finca entera «un recinto
    desaparecido» solo significa algo si se sabe **de qué tierra** era.
    """
    return versiones.comparar_dos_campanas(
        db,
        explotacion.id,
        _campana_de_la_finca(db, explotacion.id, campana_antes),
        _campana_de_la_finca(db, explotacion.id, campana_despues),
        fuente=fuente,
    )
