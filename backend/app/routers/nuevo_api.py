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
