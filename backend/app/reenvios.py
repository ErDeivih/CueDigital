"""**Lo que una puerta contesta cuando la accion ya se habia apuntado** (CRM-05, 17/10/2026).

El encargo lo pide asi: *«reenvio seguro: ... identidad de la peticion, unicidad en base, **conflicto ante
datos distintos** y recuperacion ante concurrencia»*. *El indice unico -en los 24 modelos que llevan clave
de reenvio- impide la **segunda fila**; esto es la otra mitad: **que se contesta**.*

***Y hay dos respuestas, y confundirlas es una perdida silenciosa***:

  · **La misma accion otra vez**: *el doble toque con los guantes, la respuesta que se perdio, el reintento
    cuando vuelve la cobertura.* **Se devuelve lo que ya estaba, y no se apunta nada.**
  · **La misma clave con OTROS datos**: *entonces **409** y no se toca nada.* ***Contestar «ya esta» aqui
    seria dar por guardado algo que NO se guardo*** *-el agricultor creyendo que su correccion entro, y su
    correccion perdida-.*

***Y solo se compara LO QUE LA PETICION MANDA*** (`model_fields_set`), que es la regla de la casa desde el
abono -«un campo que no viene **no es un campo vacio**, es un campo del que la peticion no dice nada»-. *En
estas puertas, ademas, muchas veces lo que no viene **se rellena con lo que ya tenia el plan o la tierra**
-el cultivo de la parcela, la superficie del plan-, asi que compararlo daria **409 en un reintento
legitimo**, que es justo lo que no puede pasar.*

*Es el mismo criterio que ya estaba escrito, cada uno en su fichero, para las lecturas del cuenta-horas, las
inspecciones y las averias de la maquina. **Aqui esta escrito una sola vez** para las cuatro puertas que
faltaban -y es donde deberian venir las tres de antes el dia que se toquen-.*
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status

from . import textos

# **Los campos que no se comparan nunca**, y por que:
#   · `clave_de_reenvio` es **la clave**, no un dato de la accion: si se comparara, siempre coincidiria.
#   · `id_local` es **el mismo identificador con el nombre del movil** (`_la_clave` acepta los dos).
LOS_QUE_NO_SE_COMPARAN = ("clave_de_reenvio", "id_local")


def como_se_compara(valor: Any) -> Any:
    """Un valor **en la forma en la que se coteja**, para que dos que dicen lo mismo coincidan.

    *`Decimal("9.00")` y `9.0` son el mismo dinero, y `" Trigo "` y `"Trigo"` el mismo cultivo: **compararlos
    tal cual** daria un 409 en un reintento legitimo, que es el defecto que este modulo existe para no
    cometer -al reves-.*
    """
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, float):
        # *Los trillonarios del redondeo no son un dato distinto: `Numeric(12, 4)` no guarda mas.*
        return round(valor, 4)
    if isinstance(valor, str):
        return valor.strip()
    return valor


def es_una_columna(ya, nombre: str) -> bool:
    """***Si eso es una COLUMNA de la fila, y no una relacion ni una propiedad.***

    *Se comparaba con `hasattr`, y **`hasattr` no vale*** (18/10/2026, y costo un 409 falso en la primera
    prueba): *`TrabajoPrevisto` tiene una **relacion** `lineas`, asi que `hasattr(ya, "lineas")` es `True` y se
    comparaban **objetos con objetos** -siempre distintos-, en vez de dejar que la puerta comparase las lineas de
    verdad. **Un nombre que existe no es un dato que se pueda cotejar.***

    *La tabla de la fila sí lo dice: `ya.__table__.columns`.*
    """
    try:
        return nombre in ya.__table__.columns
    except AttributeError:
        return False


def la_misma_accion(ya, datos, *, traducir: dict[str, str] | None = None, tambien=None) -> bool:
    """***Si lo que llego es la MISMA accion que la que ya estaba apuntada.***

    *Recorre los campos que la peticion **manda** -`model_fields_set`- y los coteja con los de la fila que ya
    hay.*

    ***1 · `traducir`, para cuando la peticion y el modelo no usan el mismo nombre***: *`horas` se guarda en
    `horas_previstas`. Sin esto, el campo no se encontraba y se **saltaba**.*

    ***2 · `tambien`, para lo que NO es una columna***: *la puerta puede crear **filas hijas** -las lineas de un
    plan, los movimientos de almacen de los insumos de una labor- y esas no estan en la fila. `tambien` recibe
    `(campo, ya, datos)` y contesta si el hijo coincide.*

    ***3 · y lo que no es columna y no tiene `tambien`, NO SE DA POR LA MISMA ACCION*** (18/10/2026, revision
    independiente). *Antes se **saltaba**, con un comentario que decia «de esas se ocupa la puerta» -y **la
    puerta no se ocupaba**: habia creado las filas hijas con los datos de la **primera** vez, y el reintento
    devolvia aquello **como si fuera lo que se acaba de mandar**. La revision lo dice con esas palabras: «cada
    puerta debe acreditar los datos compuestos que el ayudante no compara».**

    *Se cierra en falso: un 409 que se puede explicar es mejor que una fila hija que no se apunto.*
    """
    las_traducciones = traducir or {}
    for campo in datos.model_fields_set:
        if campo in LOS_QUE_NO_SE_COMPARAN:
            continue
        columna = las_traducciones.get(campo, campo)
        if es_una_columna(ya, columna):
            if como_se_compara(getattr(ya, columna, None)) != como_se_compara(getattr(datos, campo, None)):
                return False
            continue
        # ***Lo que no es columna*** -ni relacion, ni propiedad-: *o lo acredita la puerta, o no se puede dar por
        # igual.**
        if tambien is None or not tambien(campo, ya, datos):
            return False
    return True


def lo_que_contesta(ya, datos, *, traducir: dict[str, str] | None = None, tambien=None):
    """**La fila que ya estaba, o un 409 si la misma clave trae otros datos.**

    *Es el ayudante que usan las puertas en los **dos** caminos* -el de la consulta previa y el de la
    recuperacion del choque-, **para que los dos contesten lo mismo**: *si solo se llamara en uno, un
    reintento contestaria una cosa u otra segun quien llegara antes, y eso es peor que no comprobarlo.*
    """
    if la_misma_accion(ya, datos, traducir=traducir, tambien=tambien):
        return ya
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=textos.mensaje("C7_la_accion_ya_se_guardo_de_otra_manera"),
    )
