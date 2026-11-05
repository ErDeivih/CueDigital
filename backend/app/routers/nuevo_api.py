"""**Las puertas del armazón nuevo** (`IMP-1` e `IMP-4`, 05/11/2026).

La interfaz nueva se sirve aparte, en `/nuevo/`, y la vieja sigue viva en `/`. Estas son las puertas
que la app nueva necesita para abrir y para montar una finca sin teclear nada:

  · `IMP-1` — **qué hay hoy** (`/api/nuevo/hoy`) y **cuáles son mis tierras** (`/api/nuevo/tierras`).
  · `IMP-4` — **importar el cuaderno de la Junta con la finca** (`/api/nuevo/importar-cuaderno`),
    **el resumen** de gastos, ventas y lo que falta (`/api/nuevo/resumen`) y **qué falta**, con dónde
    se arregla (`/api/nuevo/que-falta`).

La cuenta de cada una está en `app/nuevo.py`; aquí solo se pone la puerta, con su autorización, que es
lo que no se puede dejar en la pantalla. **Todas piden sesión y finca**, con las dependencias de
`app/deps.py`: `UsuarioActual` valida el vale y comprueba que esa cuenta puede entrar en la finca, y
`ExplotacionActual` fija la finca en la que se está trabajando. Sin ellas, la dirección a mano
devolvería los datos de cualquiera. La de importar pide además `PuedeModificar`, y lo pide **antes**
de abrir el fichero.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, File, UploadFile

from .. import nuevo
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual

router = APIRouter(prefix="/api/nuevo", tags=["nuevo"])


@router.get("/hoy")
def lo_de_hoy(explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db) -> dict:
    """**La finca, la campaña, las tierras y los últimos apuntes, en una sola llamada.**

    Es lo que pinta la pantalla de inicio de la app nueva: el saludo con el nombre del agricultor, el
    año que está llevando, cuántas tierras tiene y qué es lo último que apuntó. **Nada de esto se
    inventa**: sin tierras son cero tierras y cero hectáreas de verdad, y sin apuntes la lista va
    vacía (el motivo está contado en `app/nuevo.py`).
    """
    return nuevo.hoy(db, explotacion=explotacion, usuario=usuario)


@router.get("/tierras")
def mis_tierras(explotacion: ExplotacionActual, db: Db, campana_id: int | None = None) -> dict:
    """**Las tierras de la finca, agrupadas por municipio, con su forma y lo que hay sembrado.**

    La campaña es la que se está llevando; se puede pedir otra con `?campana_id=`, y una campaña de
    otra finca contesta **404** (`nuevo.la_campana_activa`), como en el resto del programa.

    El `anillo` de cada tierra son los puntos de su forma en `[longitud, latitud]` y va en `None` si la
    tierra no tiene forma: una parcela apuntada a mano no se dibuja, y la pantalla lo dice en vez de
    pintar un cuadro que no existe. `coef_regadio`, `region` y `admisibilidad` son atributos del
    SIGPAC que están llegando en paralelo; mientras no estén, valen `None`.
    """
    return nuevo.tierras(db, explotacion=explotacion, campana_id=campana_id)


@router.post("/importar-cuaderno")
async def importar_el_cuaderno_del_cliente(
    explotacion: ExplotacionActual,
    db: Db,
    _: PuedeModificar,
    fichero: UploadFile = File(...),
) -> dict:
    """**Sube el cuaderno de la Junta y la finca queda montada sin teclear nada.**

    Hace las tres cosas de una vez y contesta con las tres: **lee** el fichero (con la misma función
    que `/api/cuaderno-cyl/leer`), **rellena** los huecos del titular de la finca (nombre y NIF, solo
    los que estaban vacíos) y **apunta** las tierras con la importación de siempre, que reconoce cada
    parcela por su referencia del SIGPAC. Subirlo dos veces no duplica ninguna tierra.

    El permiso de modificar (`PuedeModificar`) se comprueba **antes de abrir el fichero**: sin
    capacidad, la respuesta es `403` y no se ha leído el papel del agricultor. Un fichero que no es el
    cuaderno contesta `422` con el mensaje de la casa. La sesión la exige también `PuedeModificar`, que
    se apoya en `UsuarioActual`: no hace falta pedirla otra vez aquí.
    """
    return await nuevo.importar_cuaderno(db, explotacion=explotacion, fichero=fichero)


@router.get("/resumen")
def el_resumen_de_la_finca(explotacion: ExplotacionActual, db: Db) -> dict:
    """**El dinero de la campaña y lo que falta del cuaderno, cada cifra por su lado.**

    Lo gastado y lo vendido **no se suman entre sí** (son dinero de distinto sentido y de distinta
    naturaleza), y el cuaderno no es dinero: son cuatro bloques que se leen por separado. Donde no hay
    datos el total es `0` porque la suma de nada es cero; donde hay un dato que no consta, la cifra va
    como `None` — un total al que le falta un sumando no es un total, y en las cuentas de una
    explotación eso no es un redondeo.
    """
    return nuevo.resumen(db, explotacion=explotacion)


@router.get("/que-falta")
def lo_que_falta_del_cuaderno(explotacion: ExplotacionActual, db: Db) -> dict:
    """**Qué falta, dónde se arregla y si bloquea**, de la lista de verdad (no escrita a mano).

    Junta lo que le falta al cuaderno (el informe del escritor del Cuecyl: hoja, dato y pantalla donde
    se pone) con lo que falta para presentarlo en la Junta (`iuws.QUE_FALTA`: catálogos, certificado,
    alta del dominio y código SIEX). Lo primero **no bloquea**; lo segundo, sí.
    """
    return nuevo.que_falta(db, explotacion=explotacion)


# --------------------------------------------------------------------------- IMP-6 · la tierra


@router.get("/tierra/{parcela_id}")
def la_ficha_de_una_tierra(
    parcela_id: int, explotacion: ExplotacionActual, db: Db
) -> dict:
    """**La ficha de una tierra: qué se ha hecho hoy sobre ella, su historial y su resumen.**

    Es la primera pantalla que pidió David: **tierra primero**. Arriba, los apuntes de **hoy** en esa
    tierra (la labor, la siembra, el tratamiento, el abono o la cosecha); debajo, un elemento por año
    con datos —del más nuevo al más viejo, sin rellenar años vacíos— con las dosis por hectárea y los
    meses del abono.

    Una tierra de otra finca contesta **404** y no 403, como en todo el programa: no se dice si un
    identificador existe en otro cuaderno. Una tierra propia sin apuntes devuelve las listas vacías y
    el resumen a cero: no se rellena con nada.
    """
    return nuevo.la_ficha_de_la_tierra(db, explotacion=explotacion, parcela_id=parcela_id)


@router.get("/calendario")
def el_calendario_de_los_trabajos(
    explotacion: ExplotacionActual,
    db: Db,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
) -> dict:
    """**Qué se ha hecho cada día**, entre dos fechas (por defecto, el mes en curso).

    Solo vuelven los días con algo: el calendario ya sabe qué días están vacíos. Un rango al revés o de
    más de un año contesta **422** con su motivo, en vez de devolver miles de filas.
    """
    return nuevo.calendario(db, explotacion=explotacion, desde=desde, hasta=hasta)


@router.get("/trabajos")
def los_trabajos_de_la_campana(
    explotacion: ExplotacionActual,
    db: Db,
    tipo: str | None = None,
    campana_id: int | None = None,
) -> dict:
    """**Los trabajos de la campaña, con su tierra y su municipio**, y filtrables por tipo.

    Los tipos que se ofrecen salen de lo que hay apuntado (con su recuento), así que no se enseña un
    filtro que no lleva a nada. Un tipo que el programa conoce y este año no tiene datos devuelve la
    lista vacía; uno que no existe en el vocabulario contesta **422** con la lista de los que valen.
    """
    return nuevo.trabajos(db, explotacion=explotacion, tipo=tipo, campana_id=campana_id)
