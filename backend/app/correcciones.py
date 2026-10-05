"""Corregir y borrar lo que el agricultor ha introducido.

**POR QUÉ EXISTE ESTE FICHERO, Y QUÉ PASA CON LA REGLA DE SIEMPRE**

La regla de la casa era «nada se borra»: los registros se anulaban (`anulado` +
`motivo_anulacion`) y se conservaba el rastro. Está escrita en `models.py` y tiene su razón:
un cuaderno que se puede cambiar sin dejar huella no vale en una inspección.

David pidió lo contrario, con estas palabras: «recuerda también dejar borrar las cosas que
introduzca porque puede que me equivoque, o modificar también». Y tiene razón: hasta ahora,
si tecleaba una tierra con la referencia mal copiada, o un apunte de algo que no llegó a
hacer, lo único que podía hacer era **anularlo**, y el error se quedaba dentro del cuaderno
para siempre. Un cuaderno que no se puede corregir es un cuaderno que acaba con datos falsos.

Lo de aquí **no deroga la regla: la cumple por otra vía**. Las dos operaciones dejan rastro en
la tabla de auditoría (`models.Auditoria`), que es lo que la regla protegía:

  - **Corregir** (`corregir`): la fila sigue siendo la misma —mismo `id`— con los valores
    nuevos, y en la auditoría queda **qué decía antes y qué dice ahora**, campo por campo. Es
    exactamente lo que se hacía desde siempre con el plan de abono y con las medidas
    preventivas, que se pueden cambiar. Y hay una razón de peso para corregir **en el sitio** y
    no crear otro apunte: el identificador que viaja a la Junta (`IdAjena`) es el `id` de la
    fila (ver `iuws_mapeo`), así que corregir aquí es lo que hace que la Junta entienda que es
    **la misma** actividad y la sustituya, en vez de apuntarla dos veces.
  - **Borrar** (`borrar`): la fila desaparece del cuaderno —que es lo que el agricultor quiere
    cuando se ha equivocado, porque un apunte anulado sigue saliendo en la lista y sigue
    habiendo que explicarlo— y en la auditoría queda **el registro entero que había**, con la
    fecha, la finca y quién lo borró. O sea: en el cuaderno no está, y el programa **sí sabe
    que existió**. Lo que no se puede hacer, ni antes ni ahora, es que un dato desaparezca sin
    que quede constancia de que estuvo.

**Lo que NO se puede borrar, y por qué**: un apunte **firmado**. La firma es la prueba de lo
que había en un momento dado, y `models.Firma` dice, con razón, que una firma no se borra
nunca. Si el agricultor firma el cuaderno (o un apunte suelto) y después lo borra, la firma
se quedaría apuntando a algo que ya no existe y parecería que el cuaderno está respaldado
cuando no lo está. En ese caso se dice y se ofrece lo que sí vale: **anularlo**, que lo deja
tachado, con su motivo y con la firma cuadrando.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import inspect as inspeccionar
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
# Lo que no se copia nunca de un registro preparado a uno guardado. El identificador y la finca
# no se tocan (una corrección no puede cambiar de finca ni de fila), y el estado de anulación
# tampoco: corregir un apunte anulado no lo resucita, y para eso está volver a apuntarlo.
CAMPO_QUE_NO_SE_TOCA = frozenset(
    {"id", "explotacion_id", "anulado", "motivo_anulacion", "creado_en", "actualizado_en"}
)


def campos_corregibles(modelo: type) -> list[str]:
    """Las columnas de esa tabla que se pueden corregir, en el orden en que están declaradas."""
    return [
        atributo.key
        for atributo in inspeccionar(modelo).mapper.column_attrs
        if atributo.key not in CAMPO_QUE_NO_SE_TOCA
    ]


def _como_se_guarda(valor):
    """Deja el valor en algo que se pueda escribir en la auditoría (que es una columna JSON).

    Una fecha no se puede meter en un JSON tal cual: reventaría al guardar el rastro, y el
    agricultor vería un fallo al corregir algo que sí se puede corregir.
    """
    if isinstance(valor, (dt.date, dt.datetime)):
        return valor.isoformat()
    if isinstance(valor, (str, int, float, bool)) or valor is None:
        return valor
    if isinstance(valor, (list, tuple)):
        return [_como_se_guarda(elemento) for elemento in valor]
    if isinstance(valor, dict):
        return {str(clave): _como_se_guarda(dato) for clave, dato in valor.items()}
    return str(valor)


def _apuntar_en_la_auditoria(
    db: Session, explotacion_id: int, usuario_id: int | None, entidad: str, entidad_id: int | None,
    accion: str, datos: dict,
) -> None:
    db.add(
        models.Auditoria(
            explotacion_id=explotacion_id,
            usuario_id=usuario_id,
            entidad=entidad,
            entidad_id=entidad_id,
            accion=accion,
            datos=datos,
        )
    )


def corregir(
    db: Session,
    *,
    guardado,
    preparado,
    entidad: str,
    explotacion_id: int,
    usuario_id: int | None = None,
) -> dict:
    """Pasa al registro guardado los valores del registro recién preparado.

    `preparado` es lo que devuelven las funciones de `servicios.preparar_*`, así que la
    corrección pasa por **las mismas cuentas y las mismas comprobaciones** que el alta: el
    plazo de seguridad, el abono puro, el cultivo declarado. Si se corrigiera copiando lo que
    manda el navegador, un apunte corregido podría quedar con números que el alta no habría
    aceptado nunca.

    Devuelve los cambios, que es lo que se guarda en la auditoría: `{campo: [antes, ahora]}`.
    Si no hay ningún cambio, no se apunta nada (corregir sin cambiar nada no es un cambio).
    """
    cambios: dict[str, list] = {}
    for nombre in campos_corregibles(type(guardado)):
        nuevo = getattr(preparado, nombre, None)
        viejo = getattr(guardado, nombre, None)
        if viejo != nuevo:
            cambios[nombre] = [_como_se_guarda(viejo), _como_se_guarda(nuevo)]
            setattr(guardado, nombre, nuevo)
    if cambios:
        _apuntar_en_la_auditoria(
            db, explotacion_id, usuario_id, entidad, guardado.id, "corregir", cambios
        )
    db.commit()
    return cambios


def borrar(
    db: Session,
    *,
    registro,
    entidad: str,
    explotacion_id: int,
    usuario_id: int | None = None,
) -> dict:
    """Quita el registro del cuaderno, dejando escrito lo que había.

    Lo que se guarda en la auditoría es el registro entero (menos el identificador y la finca,
    que van en sus propias columnas de la auditoría). Es lo que permite contestar «¿y esto que
    yo tenía apuntado?» sin que el cuaderno siga enseñando un apunte que no existió.
    """
    rastro = {
        nombre: _como_se_guarda(getattr(registro, nombre, None))
        for nombre in campos_corregibles(type(registro))
    }
    entidad_id = registro.id
    _apuntar_en_la_auditoria(
        db, explotacion_id, usuario_id, entidad, entidad_id, "borrar", rastro
    )
    db.delete(registro)
    db.commit()
    return rastro


def firmas_de_un_apunte(db: Session, *, explotacion_id: int, entidad: str, entidad_id: int):
    """Las firmas que apuntan a ese apunte suelto, si tiene alguna."""
    return list(
        db.scalars(
            select(models.Firma).where(
                models.Firma.explotacion_id == explotacion_id,
                models.Firma.entidad == entidad,
                models.Firma.entidad_id == entidad_id,
            )
        )
    )


# --------------------------------------------------------------------------
# Qué se cuenta antes de borrar algo (rondas 92 y 93)
# --------------------------------------------------------------------------
#
# Estas dos se escribieron para las tierras (`parcelas.py`, ronda 92) y se han mudado aquí en la 93,
# cuando resultó que **todo lo que se puede borrar tiene el mismo problema**: un producto que está
# dentro de un tratamiento, una máquina que se usó en una labor, una campaña con apuntes, un plan que
# sostiene unos abonos. La cuenta se hace igual en todos los casos, y tenerla una sola vez evita que
# cada router se acuerde de contarla a su manera (o se olvide de una tabla).
#
# Y el motivo de fondo es el mismo que el de las tierras: **borrar algo que está en uso deja el
# cuaderno diciendo cosas que no son**. Si se borrara el producto de un tratamiento, ese tratamiento
# seguiría contando que se echó algo que ya no se sabe qué era.


def tablas_que_apuntan_a(columna: str) -> list:
    """Las tablas del cuaderno que tienen una columna que apunta a ese registro.

    **Se sacan de las tablas de verdad, y no de una lista escrita a mano**, y eso es lo que importa:
    cuando se añadieron las ventas y los análisis —los dos apuntan a una tierra—, una lista hecha a
    mano se habría quedado corta sin que nadie se enterase, y borrar una tierra habría reventado al
    guardar (la base de datos no deja un apunte apuntando a una tierra que ya no existe) o, peor,
    habría dejado el apunte sin decir dónde se hizo. Hay una prueba que exige que esta cuenta
    encuentre **las siete tablas que hay hoy**: el día que se añada la octava, esa prueba avisa y
    obliga a decidir qué se hace con ella.

    La tabla `grupo_parcela` (qué tierras lleva dentro cada grupo) no tiene modelo, así que no sale
    aquí, y es lo correcto: no es un apunte, es la lista de tierras con las que se apunta de una
    vez, y su fila desaparece sola cuando se borra la tierra (`ondelete="CASCADE"`). Un grupo no es
    el cuaderno.
    """
    return sorted(
        (mapper.class_ for mapper in models.Base.registry.mappers if columna in mapper.columns),
        key=lambda modelo: modelo.__tablename__,
    )


def cuantas_filas_apuntan_a(
    db: Session, modelo, columna: str, valor: int, explotacion_id: int
) -> int:
    """Cuántas filas de esa tabla apuntan a ese registro, en esta finca."""
    from sqlalchemy import func

    return int(
        db.scalar(
            select(func.count())
            .select_from(modelo)
            .where(
                getattr(modelo, columna) == valor,
                modelo.explotacion_id == explotacion_id,
            )
        )
        or 0
    )


def cuantas_cosas_apuntan_a(
    db: Session, *, explotacion_id: int, columna: str, valor: int
) -> int:
    """Cuántas cosas del cuaderno apuntan a ese registro, contando **todas** las tablas que lo usan.

    Se cuentan también las anuladas: siguen apuntando a él, y si desapareciera se quedarían sin decir
    lo que dicen.
    """
    return sum(
        cuantas_filas_apuntan_a(db, modelo, columna, valor, explotacion_id)
        for modelo in tablas_que_apuntan_a(columna)
    )


def en_uso(db: Session, *, explotacion_id: int, columna: str, valor: int) -> int:
    """Cuántas cosas del cuaderno usan ese registro. Cero quiere decir «se puede borrar»."""
    return cuantas_cosas_apuntan_a(db, explotacion_id=explotacion_id, columna=columna, valor=valor)
