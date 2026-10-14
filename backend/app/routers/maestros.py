"""Maestros: productos comprados, abonos, quién aplica y con qué máquina.

Los avisos de este router son la parte que más agradece el agricultor: la ITV de la
máquina y el carné de aplicador son dos cosas que caducan y de las que nadie se
acuerda hasta que es tarde.

Y desde la ronda 94, **las seis fichas de esta parte se pueden corregir y se pueden borrar**: el
producto de la cesta, el abono, quién aplica, quién asesora, la máquina y la nave. Con las mismas
reglas que los apuntes del cuaderno (ronda 91) y las tierras (ronda 92): se corrige en la misma fila
y queda el rastro, y no se borra una ficha que está dentro de un apunte. El porqué, abajo.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import (
    adjuntos,
    catalogos,
    correcciones,
    legal,
    models,
    registro_oficial_de_productos,
    servicios,
    textos,
)
from .semillas_api import TIPOS_DE_ETIQUETA
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AplicadorEntrada,
    AplicadorSalida,
    AsesorEntrada,
    AsesorSalida,
    EquipoEntrada,
    EquipoSalida,
    FertilizanteEntrada,
    FertilizanteSalida,
    InstalacionEntrada,
    InstalacionSalida,
    ProductoEntrada,
    ProductoSalida,
)
# La regla de qué se puede tocar al corregir una ficha vive en `parcelas.py` (ronda 92) y se
# **importa en vez de copiarla**: es la misma cuenta para las tierras, para los grupos y para estas
# seis fichas, y copiada serían dos sitios donde equivocarse (o donde arreglar lo mismo dos veces).
# El día que `correcciones.py` se pueda tocar, esto se muda allí, como se mudó en la ronda 93 la
# cuenta de lo que depende de un registro.
from .parcelas import _columnas_que_una_correccion_no_toca

router = APIRouter(prefix="/api", tags=["maestros"])


# --------------------------------------------------------------------------
# Corregir y borrar las fichas de lo que se usa (ronda 94)
# --------------------------------------------------------------------------
#
# David lo pidió con estas palabras: «recuerda también dejar borrar las cosas que introduzca porque
# puede que me equivoque, o modificar también». La ronda 91 lo hizo con los apuntes del cuaderno
# (tratamientos, abonos, labores y cosechas) y la 92 con las tierras y los grupos. Esto es lo mismo
# para **las fichas de lo que se usa**: el producto de la cesta, el abono, quién aplica, quién
# asesora, la máquina y la nave.
#
# **Por qué se corrige en la misma fila y no se borra y se vuelve a meter.** Porque de estas fichas
# cuelgan los apuntes: un tratamiento guarda el identificador del producto que se echó, del que lo
# echó, de la máquina con la que se echó y de la nave donde se echó. Cada apunte guarda también una
# copia de lo que decía la etiqueta aquel día (`models.TratamientoFitosanitario`), y esa copia es la
# que no puede cambiar sola. Corrigiendo en el sitio, la ficha sigue siendo la misma —mismo `id`—
# con los datos buenos, y lo que decía antes queda escrito en la auditoría (`correcciones`).
#
# **Y por qué una ficha que está dentro de un apunte NO se borra.** Por lo mismo, al revés: esos
# apuntes apuntan a la ficha por su identificador, así que borrarla los dejaría diciendo algo que ya
# no se sabe qué era (qué producto se echó, con qué máquina, en qué nave). Sería destruir el cuaderno
# en silencio, que es lo único que este programa no puede hacer. Cuando pasa se contesta 409 con
# **cuántas cosas** la usan y qué se puede hacer. Si no la usa nada —lo normal en una ficha que se
# apuntó mal y no se llegó a usar—, se borra sin más y queda el rastro.
#
# La cuenta se saca de **las tablas de verdad** (`correcciones.tablas_que_apuntan_a`), no de una
# lista escrita a mano: una lista se quedaría corta el día que se añada la tabla siguiente, y borrar
# reventaría al guardar (la base de datos no deja un apunte apuntando a una ficha que ya no existe)
# o, peor, se llevaría el apunte por delante.


def _lo_que_el_formulario_no_puede_devolver(
    preparado, actual, modelo, entrada, salida
):
    """Deja quieto, en la ficha recién preparada, lo que el formulario de corregir no puede mandar.

    La regla está en `_columnas_que_una_correccion_no_toca`, y aquí se aplica: una columna que la API
    no acepta al dar de alta o que no devuelve nunca es un dato que el agricultor no puede ni ver ni
    escribir, así que el formulario no la tiene. Si la corrección la copiara del registro preparado,
    **la borraría sin que nadie se entere** y sin que la auditoría lo dijera, porque estaría
    comparando el valor nuevo contra sí mismo.

    En estas seis fichas hay tres casos, y los tres importan:

      · **`nif`** del aplicador y del asesor: está en la tabla y se acepta al dar de alta, pero
        `AplicadorSalida` y `AsesorSalida` no lo devuelven, así que la pantalla no puede mandarlo de
        vuelta. Corregir el nombre de quien aplica le borraría el NIF, que es lo que identifica a esa
        persona delante de la administración.
      · **`numero_serie`** de la máquina: igual, y es el dato con el que se distingue un equipo de
        otro del mismo modelo.
      · **`observaciones`** de la nave y **`creada_en`** de la nave. La segunda se llama en femenino,
        así que se le escapa la lista de `correcciones` (que protege `creado_en`) y hay que cuidarla
        aquí: sin copiarla, corregir el alias de una nave le pondría la fecha de alta en blanco y la
        base de datos no lo admitiría.
    """
    if actual is None:
        return preparado
    for columna in _columnas_que_una_correccion_no_toca(modelo, entrada, salida):
        setattr(preparado, columna, getattr(actual, columna))
    return preparado


def _usos_de_la_ficha(db: Db, explotacion, *, columna: str, valor: int) -> int:
    """Cuántas cosas del cuaderno usan esa ficha. Cero quiere decir «se puede borrar».

    `columna` es la columna que apunta a la ficha (`producto_id`, `equipo_id`…) y la cuenta recorre
    **todas** las tablas que la tienen, también los apuntes anulados: siguen apuntando a la ficha, y
    si desapareciera se quedarían sin decir lo que dicen.
    """
    return correcciones.en_uso(
        db, explotacion_id=explotacion.id, columna=columna, valor=valor
    )


def _no_se_borra_una_ficha_en_uso(usos: int) -> None:
    """Si algo del cuaderno la usa, se contesta 409 y **no se borra nada**.

    El mensaje es el mismo para las seis fichas y ya está escrito (`textos.B5_en_uso_*`): dice
    cuántas cosas la usan y las dos salidas que hay de verdad —cambiar o borrar antes esos apuntes,
    o **corregir la ficha** en vez de borrarla—, que es lo que quiere la mayoría de las veces que
    alguien se equivoca al escribirla (el nombre, el número de registro, la fecha de la ITV).
    """
    if usos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B5_en_uso", usos),
        )


# --------------------------------------------------------------------------
# Productos comprados (la "cesta")
# --------------------------------------------------------------------------


@router.get("/productos", response_model=list[ProductoSalida])
def listar_productos(explotacion: ExplotacionActual, db: Db) -> list[models.ProductoFitosanitario]:
    return list(
        db.scalars(
            select(models.ProductoFitosanitario)
            .where(models.ProductoFitosanitario.explotacion_id == explotacion.id)
            .order_by(models.ProductoFitosanitario.nombre_comercial)
        )
    )


def _preparar_producto_guardable(
    datos: ProductoEntrada,
    explotacion,
    *,
    actual: models.ProductoFitosanitario | None = None,
) -> models.ProductoFitosanitario:
    """Comprueba un producto de la cesta y lo devuelve listo para guardar, **sin guardarlo**.

    Lo usan el alta y la corrección, y **es a propósito**: las dos tienen que pasar por las mismas
    comprobaciones y las mismas cuentas. Hoy el alta de un producto no comprueba nada más que lo que
    dice el esquema (el nombre tiene que venir, la dosis tiene que ser mayor que cero), pero eso
    también es una regla del alta, y una corrección no puede ser la puerta de atrás para saltársela.

    `actual` es la ficha que se está corrigiendo, y sirve para dejar quieto lo que la corrección no
    puede tocar (ver `_lo_que_el_formulario_no_puede_devolver`). En el producto no hay nada de eso
    hoy —todo lo que la tabla guarda se puede dar de alta, leer y por tanto corregir—, y por eso el
    cuidado se nota cuando se añada la primera columna que no salga en la respuesta.

    **Lo que la petición no manda, no se borra** (ronda de A1, 02/10/2026). Es el cuidado que hay que
    tener justo con las columnas de tres estados: si una corrección no manda `autorizado`, un
    `None` de más **borraría** lo que el agricultor ya había comprobado. Se mira
    `model_fields_set`, que es lo que distingue «me lo mandan vacío» de «no me lo mandan».
    """
    valores = datos.model_dump()
    if actual is not None:
        for campo in ("autorizado", "permitido_ecologico"):
            if campo not in datos.model_fields_set:
                valores[campo] = getattr(actual, campo)
    producto = models.ProductoFitosanitario(explotacion_id=explotacion.id, **valores)
    return _lo_que_el_formulario_no_puede_devolver(
        producto, actual, models.ProductoFitosanitario, ProductoEntrada, ProductoSalida
    )


@router.post("/productos", response_model=ProductoSalida, status_code=status.HTTP_201_CREATED)
def crear_producto(
    datos: ProductoEntrada, explotacion: ExplotacionActual, db: Db
) -> models.ProductoFitosanitario:
    producto = _preparar_producto_guardable(datos, explotacion)
    db.add(producto)
    db.commit()
    return producto


@router.put("/productos/{producto_id}", response_model=ProductoSalida)
def corregir_producto(
    producto_id: int,
    datos: ProductoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.ProductoFitosanitario:
    """Corrige un producto ya apuntado. **No da de alta otro: cambia esa ficha.**

    Es lo que hace falta cuando el número de registro se copió a medias, cuando la fecha de caducidad
    era la del bote de al lado o cuando el producto estaba en la cesta dos veces con nombres
    distintos: hasta ahora, la única salida era anular los tratamientos que lo usaban.

    POR QUÉ SE CORRIGE EN LA MISMA FILA Y NO SE BORRA Y SE VUELVE A METER. Porque los tratamientos y
    las líneas de factura guardan **el identificador** de esta ficha: si en vez de corregir se
    creara otra, el mismo producto tendría dos identificadores, los tratamientos seguirían apuntando
    al viejo y la cesta contaría lo comprado dos veces (una por cada ficha). Corrigiendo aquí, la
    ficha es la misma con los datos buenos, y lo que decía antes queda en la auditoría
    (`correcciones`), campo por campo.

    Y pasa por las mismas comprobaciones que el alta, porque es la misma función
    (`_preparar_producto_guardable`).
    """
    producto = obtener_de_la_explotacion(
        db, models.ProductoFitosanitario, producto_id, explotacion.id
    )
    preparado = _preparar_producto_guardable(datos, explotacion, actual=producto)
    correcciones.corregir(
        db,
        guardado=producto,
        preparado=preparado,
        entidad="producto",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return producto


@router.delete("/productos/{producto_id}")
def borrar_producto(
    producto_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita un producto de la cesta, **si no lo está usando ningún apunte**.

    QUÉ SE ROMPE SI SE BORRA UN PRODUCTO QUE YA SE HA USADO. Dos cosas, y las dos son el cuaderno:

      · **Los tratamientos** guardan `producto_id`, y de esa ficha sale lo que decía la etiqueta el
        día de la aplicación (materia activa, dosis máxima, plazo de seguridad). Sin ella, el
        apunte se queda sin poder decir **qué se echó**, que es la primera pregunta de una
        inspección.
      · **Las líneas de factura** se enganchan a la ficha para saber cuánto se ha comprado de ese
        producto. Y el almacén —«Situación Cesta»— se calcula justo con eso: lo comprado sale de las
        compras y lo gastado de los tratamientos (`servicios.situacion_de_la_cesta`). No hay una
        tabla de movimientos de almacén que borrar, así que **las dos tablas que hay que contar son
        esas dos**, y `correcciones.tablas_que_apuntan_a("producto_id")` las encuentra sola.

    Una ficha recién apuntada, con la que no se ha hecho nada, se borra sin más: es lo normal cuando
    uno se equivoca al darla de alta y se da cuenta enseguida.
    """
    producto = obtener_de_la_explotacion(
        db, models.ProductoFitosanitario, producto_id, explotacion.id
    )
    _no_se_borra_una_ficha_en_uso(
        _usos_de_la_ficha(db, explotacion, columna="producto_id", valor=producto_id)
    )
    correcciones.borrar(
        db,
        registro=producto,
        entidad="producto",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": producto_id}


@router.get("/productos/{producto_id}", response_model=ProductoSalida)
def ver_producto(
    producto_id: int, explotacion: ExplotacionActual, db: Db
) -> models.ProductoFitosanitario:
    return obtener_de_la_explotacion(
        db, models.ProductoFitosanitario, producto_id, explotacion.id
    )


@router.get("/productos/cesta/situacion")
def situacion_de_la_cesta(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> dict:
    """Cuánto producto has comprado, cuánto llevas echado y cuánto te queda.

    Es el botón «Situación Cesta» de la app de la Junta, que enseña «las cantidades adquiridas y
    gastadas de los distintos productos fitosanitarios utilizados en la campaña». Aquí faltaba:
    los campos de la compra estaban en la tabla y no los usaba nadie, así que no se podía
    contestar a «¿me queda producto para tratar esta parcela?».

    Decisión: **no se resta cuando no se puede**. Si compraste en kilos y echas dosis en litros,
    no hay cuenta posible sin la densidad del producto, y decir «te quedan -3 kg» sería
    inventarse un dato. Se devuelve el motivo, y cada producto trae el suyo.
    """
    campana = None
    if campana_id is not None:
        campana = obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    else:
        campana = db.scalar(
            select(models.Campana)
            .where(models.Campana.explotacion_id == explotacion.id)
            .order_by(models.Campana.anio.desc())
            .limit(1)
        )

    filas = servicios.situacion_de_la_cesta(
        db,
        explotacion_id=explotacion.id,
        campana_id=campana.id if campana else None,
    )
    # **El saldo físico, que es el número que hay que enseñar.** Lo comprado y lo echado siguen ahí
    # (`comprado`, `gastado`), pero como lo que son: lo que dicen los papeles. El «te queda» de verdad
    # sale del libro de movimientos, relacionado por identificador. Si un producto no tiene artículo, su
    # `saldo_fisico` es `null` con su motivo (`A24`) y **no un cero**.
    saldos = servicios.el_saldo_fisico_de_una_cesta(db, explotacion_id=explotacion.id)
    for fila in filas:
        # La relación **ya viene hecha** desde `servicios`, por el identificador del artículo
        # (`saldos["por_producto"][producto_id]["articulo_id"]`). Aquí no se relaciona otra vez: si se
        # hiciera por el nombre, la pantalla y el almacén podrían decir cosas distintas del mismo
        # producto.
        suyo = saldos["por_articulo"].get(
            saldos["por_producto"].get(fila["producto_id"], {}).get("articulo_id")
        )
        fila["saldo_fisico"] = suyo.saldo_fisico if suyo else None
        fila["saldo_fisico_conocido"] = bool(suyo and suyo.se_puede_saber)
        fila["situacion"] = suyo.situacion if suyo else "pendiente"
        fila["motivo_fisico"] = (suyo.que_pasa or suyo.motivo) if suyo else textos.MENSAJES["A24_el_producto_no_tiene_articulo"]
        fila["lotes_del_articulo"] = suyo.lotes if suyo else []
        fila["el_mismo_consumo"] = suyo.el_mismo_consumo if suyo else []
    # La ficha del producto no se manda entera: la cesta enseña cuentas, y el objeto de dentro
    # no es JSON. Se devuelve lo que se ve.
    for fila in filas:
        fila.pop("producto", None)
        if fila["fecha_compra"] is not None:
            fila["fecha_compra"] = fila["fecha_compra"].isoformat()

    return {
        "textos": textos.CESTA,
        "productos": filas,
        "campana_id": campana.id if campana else None,
        "campana_anio": campana.anio if campana else None,
        "cuantos": len(filas),
        "sin_cantidad": len([f for f in filas if f["comprado"] is None]),
        "sin_poder_comparar": len([f for f in filas if not f["se_puede_comparar"]]),
        "resumen": (
            textos.CESTA["vacia"]
            if not filas
            else textos.con_cuenta(textos.CESTA, "cuantos", len(filas))
        ),
    }


# --------------------------------------------------------------------------
# Abonos
# --------------------------------------------------------------------------


@router.get("/fertilizantes", response_model=list[FertilizanteSalida])
def listar_fertilizantes(explotacion: ExplotacionActual, db: Db) -> list[models.Fertilizante]:
    return list(
        db.scalars(
            select(models.Fertilizante)
            .where(models.Fertilizante.explotacion_id == explotacion.id)
            .order_by(models.Fertilizante.nombre)
        )
    )


def _preparar_fertilizante_guardable(
    datos: FertilizanteEntrada,
    explotacion,
    *,
    actual: models.Fertilizante | None = None,
) -> models.Fertilizante:
    """Comprueba un abono y lo devuelve listo para guardar, **sin guardarlo**.

    Lo usan el alta y la corrección, para que las dos exijan lo mismo: el esquema ya obliga a que el
    nombre venga y a que las tres riquezas estén entre 0 y 100, y corregir un abono no puede ser la
    forma de meter un 120 % de nitrógeno que el alta no habría aceptado.

    Ojo con un detalle que sí importa: un abono **se copia dentro de cada apunte de fertilización**
    (`fertilizaciones.fertilizante_nombre`, `riqueza_n/p/k`) para que el histórico no cambie si
    alguien edita la ficha (`models.RegistroFertilizacion`). Corregir aquí **no toca** los apuntes ya
    hechos, y es lo correcto: lo que se echó aquel día se echó con lo que decía la ficha entonces.

    **Y lo que la petición no manda, no se borra** (mismo cuidado que en el producto, ronda de A1).
    Aquí hace falta desde que la composición tiene tres estados: `riqueza_n/p/k` admiten «no lo sé»
    (`None`), así que una corrección que solo cambie el nombre **borraría la composición** que el
    agricultor había copiado del saco, y encima con un hueco en vez de con un cero. Se mira
    `model_fields_set`, que distingue «me lo mandan vacío» de «no me lo mandan».
    """
    valores = datos.model_dump()
    if actual is not None:
        for campo in ("riqueza_n", "riqueza_p", "riqueza_k"):
            if campo not in datos.model_fields_set:
                valores[campo] = getattr(actual, campo)
    fertilizante = models.Fertilizante(explotacion_id=explotacion.id, **valores)
    return _lo_que_el_formulario_no_puede_devolver(
        fertilizante, actual, models.Fertilizante, FertilizanteEntrada, FertilizanteSalida
    )


@router.post("/fertilizantes", response_model=FertilizanteSalida, status_code=status.HTTP_201_CREATED)
def crear_fertilizante(
    datos: FertilizanteEntrada, explotacion: ExplotacionActual, db: Db
) -> models.Fertilizante:
    fertilizante = _preparar_fertilizante_guardable(datos, explotacion)
    db.add(fertilizante)
    db.commit()
    return fertilizante


@router.put("/fertilizantes/{fertilizante_id}", response_model=FertilizanteSalida)
def corregir_fertilizante(
    fertilizante_id: int,
    datos: FertilizanteEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.Fertilizante:
    """Corrige un abono ya apuntado. **No da de alta otro: cambia esa ficha.**

    Es lo que hace falta cuando la riqueza se copió mal del saco (un 33,5 % escrito como 3,5) o
    cuando el abono estaba en la lista dos veces. Corregir en la misma fila es lo que hace que los
    apuntes que lo usaron sigan apuntando al mismo abono.

    Y lo que decía antes queda escrito en la auditoría (`correcciones`). Los apuntes de fertilización
    ya hechos **no se tocan**: cada uno guardó su copia de la riqueza del día en que se echó, y un
    histórico que cambia solo no vale para nada.
    """
    fertilizante = obtener_de_la_explotacion(
        db, models.Fertilizante, fertilizante_id, explotacion.id
    )
    preparado = _preparar_fertilizante_guardable(datos, explotacion, actual=fertilizante)
    correcciones.corregir(
        db,
        guardado=fertilizante,
        preparado=preparado,
        entidad="fertilizante",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return fertilizante


def _planes_que_prevén_ese_abono(db: Db, explotacion_id: int, fertilizante_id: int) -> int:
    """Cuántos planes de abono llevan esa ficha dentro del reparto previsto.

    **Esta cuenta no la ve `correcciones.tablas_que_apuntan_a` y hay que hacerla aparte**, porque el
    reparto del plan (`planes_abonado.detalle`) es una columna JSON: dentro guarda qué abono se
    piensa echar, con su `fertilizante_id` y su nombre (`schemas.AbonPrevisto`), pero no es una clave
    foránea. Sin clave foránea no hay columna que contar ni cascada que avise, así que se mira a
    mano.

    **Y se cuenta aunque el plan sea una previsión y no un apunte**, por un motivo concreto: el papel
    del cuaderno saca el nombre del abono de la ficha cuando el plan solo trae la ficha
    (`routers/cuaderno.py`, `_texto_del_reparto_previsto`). Si la ficha desapareciera, el plan se
    imprimiría sin decir qué abono pensaba echar. Y el agricultor que de verdad quiera borrar el
    abono tiene la salida de siempre: corregir el plan primero.
    """
    planes = db.scalars(
        select(models.PlanAbonado).where(models.PlanAbonado.explotacion_id == explotacion_id)
    )
    return sum(
        1
        for plan in planes
        if any(
            isinstance(abono, dict) and abono.get("fertilizante_id") == fertilizante_id
            for abono in (plan.detalle or [])
        )
    )


@router.delete("/fertilizantes/{fertilizante_id}")
def borrar_fertilizante(
    fertilizante_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita un abono de la lista, **si no lo está usando ningún apunte**.

    QUÉ SE ROMPE SI SE BORRA UN ABONO QUE YA SE HA USADO:

      · **Los registros de fertilización** guardan `fertilizante_id`. El abonado es obligatorio
        desde el 01/01/2026: borrar la ficha deja el apunte sin poder decir **con qué se abonó**,
        que es justo lo que se mira en una inspección.
      · **Las líneas de factura** se enganchan a ella para saber cuánto abono se ha comprado.
      · **Los planes de abono** que la traen en su reparto previsto, que es el único caso que no se
        ve en una columna y por eso se cuenta aparte (`_planes_que_prevén_ese_abono`).

    Un abono apuntado y no usado se borra sin más, con su rastro en la auditoría.
    """
    fertilizante = obtener_de_la_explotacion(
        db, models.Fertilizante, fertilizante_id, explotacion.id
    )
    usos = _usos_de_la_ficha(
        db, explotacion, columna="fertilizante_id", valor=fertilizante_id
    ) + _planes_que_prevén_ese_abono(db, explotacion.id, fertilizante_id)
    _no_se_borra_una_ficha_en_uso(usos)
    correcciones.borrar(
        db,
        registro=fertilizante,
        entidad="fertilizante",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": fertilizante_id}


# --------------------------------------------------------------------------
# Quién aplica
# --------------------------------------------------------------------------


@router.get("/aplicadores", response_model=list[AplicadorSalida])
def listar_aplicadores(explotacion: ExplotacionActual, db: Db) -> list[models.Aplicador]:
    return list(
        db.scalars(
            select(models.Aplicador)
            .where(models.Aplicador.explotacion_id == explotacion.id)
            .order_by(models.Aplicador.nombre)
        )
    )


def _preparar_aplicador_guardable(
    datos: AplicadorEntrada,
    explotacion,
    *,
    actual: models.Aplicador | None = None,
) -> models.Aplicador:
    """Comprueba quién aplica y lo devuelve listo para guardar, **sin guardarlo**.

    Lo usan el alta y la corrección, y **es a propósito**: aquí vive la comprobación del carné, y una
    corrección no puede ser la puerta de atrás para meter un tipo de carné que el alta no acepta (la
    hoja 1.2 del cuaderno de la Junta marca con una cruz la columna que toca, y con un texto libre la
    cruz no se puede poner).

    El nombre del carné se normaliza aquí también (sin espacios de más y en minúsculas) para que las
    dos vías guarden exactamente lo mismo. Hasta la ronda 94 esto se hacía en el endpoint del alta:
    si se hubiera quedado ahí, el mismo carné escrito como «Cualificado» se guardaría de una forma al
    darlo de alta y de otra al corregirlo, y las dos fichas se leerían distinto sin motivo.
    """
    # El tipo de carné tiene que ser uno de los cuatro que distingue el cuaderno: en su hoja 1.2 se
    # marca con una cruz en la columna que toca, y con un texto libre la cruz no se puede poner
    # (¿«cualificado», «Cualificado» o «nivel 2»?). Un valor que no esté se rechaza con la lista
    # delante, como se hace con los tipos de papel y con los de abonado.
    if datos.tipo_carne and datos.tipo_carne.strip().lower() not in catalogos.TIPOS_CARNE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"«{datos.tipo_carne}» no es un tipo de carné. "
                f"Los que hay: {', '.join(catalogos.ETIQUETA_CARNE[valor] for valor in catalogos.TIPOS_CARNE)}."
            ),
        )
    valores = datos.model_dump()
    if valores.get("tipo_carne"):
        valores["tipo_carne"] = valores["tipo_carne"].strip().lower()
    aplicador = models.Aplicador(explotacion_id=explotacion.id, **valores)
    return _lo_que_el_formulario_no_puede_devolver(
        aplicador, actual, models.Aplicador, AplicadorEntrada, AplicadorSalida
    )


@router.post("/aplicadores", response_model=AplicadorSalida, status_code=status.HTTP_201_CREATED)
def crear_aplicador(
    datos: AplicadorEntrada, explotacion: ExplotacionActual, db: Db
) -> models.Aplicador:
    aplicador = _preparar_aplicador_guardable(datos, explotacion)
    db.add(aplicador)
    db.commit()
    return aplicador


@router.put("/aplicadores/{aplicador_id}", response_model=AplicadorSalida)
def corregir_aplicador(
    aplicador_id: int,
    datos: AplicadorEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.Aplicador:
    """Corrige quién aplica. **No da de alta otra ficha: cambia esa.**

    Es lo que hace falta cuando el número de carné se copió mal, cuando la fecha de caducidad era
    otra o cuando el nombre venía con una errata. Y es el caso que más importa de los seis, porque de
    esta ficha salen los dos avisos que el agricultor más agradece: el carné que caduca y la ITV.

    POR QUÉ SE CORRIGE EN LA MISMA FILA. Los tratamientos guardan `aplicador_id`: quien aplicó aquel
    día. Si en vez de corregir se borrara y se volviera a meter, esos apuntes se quedarían sin poder
    decir quién echó el producto, que es un dato obligatorio del cuaderno.

    Y pasa por las mismas comprobaciones que el alta, porque es la misma función
    (`_preparar_aplicador_guardable`): el tipo de carné se vuelve a mirar contra la lista.
    """
    aplicador = obtener_de_la_explotacion(db, models.Aplicador, aplicador_id, explotacion.id)
    preparado = _preparar_aplicador_guardable(datos, explotacion, actual=aplicador)
    correcciones.corregir(
        db,
        guardado=aplicador,
        preparado=preparado,
        entidad="aplicador",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return aplicador


@router.delete("/aplicadores/{aplicador_id}")
def borrar_aplicador(
    aplicador_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita quién aplica de la lista, **si no lo está usando ningún apunte**.

    QUÉ SE ROMPE SI SE BORRA ALGUIEN QUE YA HA APLICADO. Los tratamientos guardan `aplicador_id`, y
    ese identificador es lo que permite contestar «¿quién echó esto?» —el aplicador es un dato
    obligatorio del registro fitosanitario, con su carné y su ROPO—. Sin la ficha, el apunte se
    queda sin poder decir quién lo hizo, y con él se va también el aviso de que su carné caduca.

    A quien se dio de alta por error, o al trabajador que ya no está y **no aplicó nada**, se le
    borra la ficha sin más: para eso está.
    """
    aplicador = obtener_de_la_explotacion(db, models.Aplicador, aplicador_id, explotacion.id)
    _no_se_borra_una_ficha_en_uso(
        _usos_de_la_ficha(db, explotacion, columna="aplicador_id", valor=aplicador_id)
    )
    correcciones.borrar(
        db,
        registro=aplicador,
        entidad="aplicador",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": aplicador_id}


# --------------------------------------------------------------------------
# El técnico que asesora
#
# La app oficial lo tiene en «Cuaderno: Asesores». Es una figura distinta del aplicador: el
# asesor dice qué hay que hacer y el aplicador lo hace. Muchas veces es la misma persona, pero
# el número de ROPO del asesor es otro registro, y sin él el interfaz de la Junta rechaza el
# tratamiento entero.
# --------------------------------------------------------------------------


@router.get("/asesores", response_model=list[AsesorSalida])
def listar_asesores(explotacion: ExplotacionActual, db: Db) -> list[models.Asesor]:
    return list(
        db.scalars(
            select(models.Asesor)
            .where(models.Asesor.explotacion_id == explotacion.id)
            .order_by(models.Asesor.nombre)
        )
    )


def _preparar_asesor_guardable(
    datos: AsesorEntrada,
    explotacion,
    *,
    actual: models.Asesor | None = None,
) -> models.Asesor:
    """Comprueba quién asesora y lo devuelve listo para guardar, **sin guardarlo**.

    Lo usan el alta y la corrección, para que las dos exijan lo mismo: el ámbito del asesoramiento
    tiene que ser uno de los que distingue el cuaderno (`catalogos.AMBITOS_ASESOR`), porque es un
    dato que después se manda a la Junta y un texto libre no se puede mapear.
    """
    if datos.ambito and datos.ambito not in catalogos.AMBITOS_ASESOR:
        raise HTTPException(
            status_code=422,
            detail=(
                "Ese tipo de asesoramiento no existe. Puede ser: "
                f"{', '.join(catalogos.AMBITOS_ASESOR)}."
            ),
        )
    asesor = models.Asesor(explotacion_id=explotacion.id, **datos.model_dump())
    return _lo_que_el_formulario_no_puede_devolver(
        asesor, actual, models.Asesor, AsesorEntrada, AsesorSalida
    )


@router.post("/asesores", response_model=AsesorSalida, status_code=status.HTTP_201_CREATED)
def crear_asesor(
    datos: AsesorEntrada, explotacion: ExplotacionActual, db: Db
) -> models.Asesor:
    asesor = _preparar_asesor_guardable(datos, explotacion)
    db.add(asesor)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="asesor",
            accion="crear",
            datos={"nombre": asesor.nombre, "ropo": asesor.numero_ropo},
        )
    )
    db.commit()
    return asesor


@router.put("/asesores/{asesor_id}", response_model=AsesorSalida)
def corregir_asesor(
    asesor_id: int,
    datos: AsesorEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.Asesor:
    """Corrige quién asesora. **No da de alta otra ficha: cambia esa.**

    Es lo que hace falta cuando el número de ROPO venía con una cifra cambiada, cuando el teléfono es
    otro o cuando el ámbito estaba mal elegido. Y no es un detalle: el interfaz de la Junta rechaza
    un asesor cuyo ROPO no encuentre, así que un ROPO mal copiado deja el tratamiento sin poder
    volcar.

    POR QUÉ SE CORRIGE EN LA MISMA FILA. Los tratamientos guardan `asesor_id` (campos 44 a 53 del
    contenido mínimo): si en vez de corregir se diera de alta otro, los apuntes ya hechos seguirían
    apuntando al asesor con el ROPO malo. Corrigiendo aquí, la ficha sigue siendo la misma y lo que
    decía antes queda en la auditoría (`correcciones`).

    Y pasa por las mismas comprobaciones que el alta, porque es la misma función
    (`_preparar_asesor_guardable`): el ámbito se vuelve a mirar contra la lista.
    """
    asesor = obtener_de_la_explotacion(db, models.Asesor, asesor_id, explotacion.id)
    preparado = _preparar_asesor_guardable(datos, explotacion, actual=asesor)
    correcciones.corregir(
        db,
        guardado=asesor,
        preparado=preparado,
        entidad="asesor",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return asesor


@router.delete("/asesores/{asesor_id}")
def borrar_asesor(
    asesor_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita quién asesora de la lista, **si no lo está usando ningún apunte**.

    QUÉ SE ROMPE SI SE BORRA UN ASESOR QUE YA HA ASESORADO. Los tratamientos guardan `asesor_id` y
    de esa ficha salen el nombre y el número de ROPO, que el contenido mínimo del CUE pide en el
    bloque de tratamientos fitosanitarios (campos 44 a 53). Sin la ficha, el apunte se queda sin
    poder decir quién validó el tratamiento —y sin ROPO el interfaz de la Junta rechaza el bloque
    entero—.

    A quien se apuntó por error y no asesoró nada se le borra la ficha sin más, y queda el rastro.
    """
    asesor = obtener_de_la_explotacion(db, models.Asesor, asesor_id, explotacion.id)
    _no_se_borra_una_ficha_en_uso(
        _usos_de_la_ficha(db, explotacion, columna="asesor_id", valor=asesor_id)
    )
    correcciones.borrar(
        db,
        registro=asesor,
        entidad="asesor",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": asesor_id}


# --------------------------------------------------------------------------
# Máquinas
# --------------------------------------------------------------------------


@router.get("/equipos", response_model=list[EquipoSalida])
def listar_equipos(explotacion: ExplotacionActual, db: Db) -> list[models.EquipoAplicacion]:
    return list(
        db.scalars(
            select(models.EquipoAplicacion)
            .where(models.EquipoAplicacion.explotacion_id == explotacion.id)
            .order_by(models.EquipoAplicacion.nombre)
        )
    )


def _preparar_equipo_guardable(
    datos: EquipoEntrada,
    explotacion,
    *,
    actual: models.EquipoAplicacion | None = None,
) -> models.EquipoAplicacion:
    """Comprueba una máquina y la devuelve lista para guardar, **sin guardarla**.

    Lo usan el alta y la corrección, y **es a propósito**: las dos tienen que pasar por las mismas
    comprobaciones y guardar lo mismo.

    `actual` es la máquina que se está corrigiendo, y aquí hace falta de verdad: el **número de
    serie** está en la tabla y se acepta al dar de alta, pero `EquipoSalida` **no lo devuelve**, así
    que el formulario de corregir no lo tiene y no puede mandarlo de vuelta. Sin este cuidado,
    corregir el nombre de una máquina le borraría el número de serie sin que nadie se entere y sin
    que la auditoría lo dijera.
    """
    equipo = models.EquipoAplicacion(explotacion_id=explotacion.id, **datos.model_dump())
    return _lo_que_el_formulario_no_puede_devolver(
        equipo, actual, models.EquipoAplicacion, EquipoEntrada, EquipoSalida
    )


@router.post("/equipos", response_model=EquipoSalida, status_code=status.HTTP_201_CREATED)
def crear_equipo(
    datos: EquipoEntrada, explotacion: ExplotacionActual, db: Db
) -> models.EquipoAplicacion:
    equipo = _preparar_equipo_guardable(datos, explotacion)
    db.add(equipo)
    db.commit()
    return equipo


@router.put("/equipos/{equipo_id}", response_model=EquipoSalida)
def corregir_equipo(
    equipo_id: int,
    datos: EquipoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.EquipoAplicacion:
    """Corrige una máquina. **No da de alta otra: cambia esa ficha.**

    Es lo que más se corrige de todo esto, porque las fechas de la ITEAF se copian del papel y del
    papel al programa se cambia un número: si la fecha de la próxima inspección está mal, el aviso
    salta el día que no es. Y también el número de ROMA, que es lo que identifica la máquina en la
    hoja 1.3 del cuaderno.

    POR QUÉ SE CORRIGE EN LA MISMA FILA. Las labores y los tratamientos guardan `equipo_id` (con qué
    máquina se hizo cada trabajo). Si en vez de corregir se borrara y se volviera a meter, esos
    apuntes se quedarían sin poder decir con qué máquina se trabajó, que es un dato que el contenido
    mínimo del CUE pide en los bloques de labores y de siembra.

    Y el **número de serie sobrevive**: no viaja en la respuesta, así que el formulario no lo tiene,
    y por eso lo protege `_lo_que_el_formulario_no_puede_devolver`.
    """
    equipo = obtener_de_la_explotacion(db, models.EquipoAplicacion, equipo_id, explotacion.id)
    preparado = _preparar_equipo_guardable(datos, explotacion, actual=equipo)
    correcciones.corregir(
        db,
        guardado=equipo,
        preparado=preparado,
        entidad="equipo",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return equipo


@router.delete("/equipos/{equipo_id}")
def borrar_equipo(
    equipo_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita una máquina de la lista, **si no la está usando ningún apunte**.

    QUÉ SE ROMPE SI SE BORRA UNA MÁQUINA QUE YA SE HA USADO. Los tratamientos guardan `equipo_id` y
    las labores también: esa columna dice **con qué se hizo** cada trabajo, y la hoja 1.3 del
    cuaderno y los bloques de labores y de siembra del contenido mínimo lo piden por su nombre. Sin
    la ficha, el apunte se queda sin poder decir con qué máquina se echó el producto o se labró, y
    con ella se van también el número de ROMA y el aviso de la ITEAF.

    Una máquina apuntada por error, o vendida antes de usarla en nada, se borra sin más.
    """
    equipo = obtener_de_la_explotacion(db, models.EquipoAplicacion, equipo_id, explotacion.id)
    # **Y también cuenta si la maquinaria la tiene enlazada** (T14, 03/10/2026). Desde que hay lista de
    # maquinaria, un equipo de echar producto puede ser **la misma máquina** que una ficha de
    # `maquinas` (`maquinas.equipo_aplicacion_id`). Si se borrara el equipo, esa ficha se quedaría
    # apuntando a algo que ya no está —la base de datos no lo admitiría— y, sobre todo, el número de
    # ROMA y la fecha de la inspección desaparecerían de la hoja 1.3 del cuaderno. Se cuenta como una
    # dependencia más, con el mismo mensaje y la misma salida (corregir el equipo en vez de borrarlo).
    usos = _usos_de_la_ficha(db, explotacion, columna="equipo_id", valor=equipo_id) + _usos_de_la_ficha(
        db, explotacion, columna="equipo_aplicacion_id", valor=equipo_id
    )
    _no_se_borra_una_ficha_en_uso(usos)
    correcciones.borrar(
        db,
        registro=equipo,
        entidad="equipo",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": equipo_id}


# --------------------------------------------------------------------------
# Naves, almacenes e invernaderos
#
# Sin esto, la sección de «tratamiento de instalaciones» del cuaderno oficial no se
# puede cumplimentar de ninguna manera: no hay dónde apuntar que se trató una nave.
# --------------------------------------------------------------------------


@router.get("/instalaciones", response_model=list[InstalacionSalida])
def listar_instalaciones(explotacion: ExplotacionActual, db: Db) -> list[models.Instalacion]:
    return list(
        db.scalars(
            select(models.Instalacion)
            .where(models.Instalacion.explotacion_id == explotacion.id)
            .order_by(models.Instalacion.alias)
        )
    )


def _preparar_instalacion_guardable(
    datos: InstalacionEntrada,
    explotacion,
    *,
    actual: models.Instalacion | None = None,
) -> models.Instalacion:
    """Comprueba una nave y la devuelve lista para guardar, **sin guardarla**.

    Lo usan el alta y la corrección, para que las dos exijan lo mismo: el tipo de instalación tiene
    que ser uno de los que distingue el cuaderno (`catalogos.TIPOS_INSTALACION`), porque la sección
    de «tratamiento de instalaciones» del cuaderno oficial se cumplimenta por ese tipo.

    `actual` es la nave que se está corrigiendo, y aquí hay que cuidar **dos** columnas que el
    formulario no puede mandar de vuelta (ver `_lo_que_el_formulario_no_puede_devolver`):

      · **`observaciones`**: se acepta al dar de alta pero no se devuelve nunca, así que la pantalla
        no la tiene.
      · **`creada_en`**: cuándo se apuntó la nave. Se llama en femenino, así que se le escapa la
        lista de `correcciones` (que protege `creado_en`), y sin copiarla la corrección intentaría
        dejarla en blanco y la base de datos no lo admitiría: corregir el alias de una nave fallaría
        con un fallo del programa en vez de hacer lo que el agricultor ha pedido.
    """
    if datos.tipo not in catalogos.TIPOS_INSTALACION:
        raise HTTPException(
            status_code=422,
            detail=(
                "Ese tipo de instalación no existe. Puede ser: "
                f"{', '.join(catalogos.TIPOS_INSTALACION)}."
            ),
        )
    instalacion = models.Instalacion(explotacion_id=explotacion.id, **datos.model_dump())
    return _lo_que_el_formulario_no_puede_devolver(
        instalacion, actual, models.Instalacion, InstalacionEntrada, InstalacionSalida
    )


@router.post(
    "/instalaciones", response_model=InstalacionSalida, status_code=status.HTTP_201_CREATED
)
def crear_instalacion(
    datos: InstalacionEntrada, explotacion: ExplotacionActual, db: Db
) -> models.Instalacion:
    instalacion = _preparar_instalacion_guardable(datos, explotacion)
    db.add(instalacion)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="instalacion",
            accion="crear",
            datos={"alias": instalacion.alias, "tipo": instalacion.tipo},
        )
    )
    db.commit()
    return instalacion


@router.get("/instalaciones/{instalacion_id}", response_model=InstalacionSalida)
def ver_instalacion(
    instalacion_id: int, explotacion: ExplotacionActual, db: Db
) -> models.Instalacion:
    return obtener_de_la_explotacion(db, models.Instalacion, instalacion_id, explotacion.id)


@router.put("/instalaciones/{instalacion_id}", response_model=InstalacionSalida)
def corregir_instalacion(
    instalacion_id: int,
    datos: InstalacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.Instalacion:
    """Corrige una nave o un almacén. **No da de alta otra: cambia esa ficha.**

    Es lo que hace falta cuando la referencia catastral se copió mal o cuando el alias dejó de
    describir lo que hay dentro («El almacén grande» cuando se quedó pequeño y ahora es el silo).

    POR QUÉ SE CORRIGE EN LA MISMA FILA. Los tratamientos de instalaciones guardan `instalacion_id`
    —cuando se trata un almacén, el producto no se echa en la parcela sino en un local, y el apunte
    tiene que decir en cuál—, y los análisis también. Si en vez de corregir se borrara y se volviera
    a meter, esos apuntes se quedarían sin poder decir dónde se hizo el trabajo.

    Y pasa por las mismas comprobaciones que el alta, porque es la misma función
    (`_preparar_instalacion_guardable`): el tipo se vuelve a mirar contra la lista. Lo que no se toca
    es lo que el formulario no puede mandar de vuelta: las observaciones y la fecha en que se apuntó.
    """
    instalacion = obtener_de_la_explotacion(
        db, models.Instalacion, instalacion_id, explotacion.id
    )
    preparado = _preparar_instalacion_guardable(datos, explotacion, actual=instalacion)
    correcciones.corregir(
        db,
        guardado=instalacion,
        preparado=preparado,
        entidad="instalacion",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return instalacion


@router.delete("/instalaciones/{instalacion_id}")
def borrar_instalacion(
    instalacion_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita una nave de la lista, **si no la está usando ningún apunte**.

    QUÉ SE ROMPE SI SE BORRA UNA NAVE DONDE YA SE HA TRABAJADO:

      · **Los tratamientos de instalaciones** guardan `instalacion_id`. Tratar un almacén contra
        insectos o roedores es una aplicación que el cuaderno tiene que registrar, y sin la ficha el
        apunte se queda sin decir **dónde** se trató (la nave no tiene recinto SIGPAC: lo que la
        identifica delante de la administración es su referencia catastral, que está en esta ficha).
      · **Los análisis** guardan `instalacion_id` cuando la muestra salió de una nave o de una balsa,
        no de una tierra. Sin la ficha, el boletín se queda sin decir de dónde salió la muestra.

    Una nave apuntada por error se borra sin más, con su rastro en la auditoría.
    """
    instalacion = obtener_de_la_explotacion(
        db, models.Instalacion, instalacion_id, explotacion.id
    )
    _no_se_borra_una_ficha_en_uso(
        _usos_de_la_ficha(db, explotacion, columna="instalacion_id", valor=instalacion_id)
    )
    correcciones.borrar(
        db,
        registro=instalacion,
        entidad="instalacion",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": instalacion_id}


# --------------------------------------------------------------------------
# Avisos: lo que caduca
# --------------------------------------------------------------------------


@router.get("/avisos")
def avisos(explotacion: ExplotacionActual, db: Db) -> dict:
    """Cosas que caducan o que faltan, dichas en castellano y con un toque para quitarlas.

    Decisión de usabilidad: se devuelve una lista corta y ordenada por urgencia, y
    siempre con el mensaje ya escrito. La interfaz no tiene que componer frases: eso
    es lo que hace que un aviso acabe diciendo "ITEAF caducada" en vez de explicarle
    al agricultor qué tiene que hacer.
    """
    salida: list[dict] = []
    referencia = legal.hoy()

    for aplicador in db.scalars(
        select(models.Aplicador).where(models.Aplicador.explotacion_id == explotacion.id)
    ):
        if aplicador.es_empresa:
            continue
        if legal.caduca_pronto(aplicador.fecha_caducidad_carne, legal.DIAS_AVISO_CARNE, referencia):
            salida.append(
                {
                    "tipo": "carne",
                    "urgente": (legal.dias_hasta(aplicador.fecha_caducidad_carne, referencia) or 0) <= 7,
                    "mensaje": textos.mensaje(
                        "A1_carne_caduca_pronto",
                        nombre=aplicador.nombre,
                        fecha=legal.formatea_fecha(aplicador.fecha_caducidad_carne),
                    ),
                }
            )
        elif aplicador.fecha_caducidad_carne and aplicador.fecha_caducidad_carne < referencia:
            salida.append(
                {
                    "tipo": "carne",
                    "urgente": True,
                    "mensaje": textos.mensaje(
                        "V6_carne_caducado",
                        nombre=aplicador.nombre,
                        fecha=legal.formatea_fecha(aplicador.fecha_caducidad_carne),
                    ),
                }
            )

    for equipo in db.scalars(
        select(models.EquipoAplicacion).where(
            models.EquipoAplicacion.explotacion_id == explotacion.id
        )
    ):
        if legal.caduca_pronto(equipo.fecha_proxima_iteaf, legal.DIAS_AVISO_ITEAF, referencia):
            salida.append(
                {
                    "tipo": "iteaf",
                    "urgente": (legal.dias_hasta(equipo.fecha_proxima_iteaf, referencia) or 0) <= 15,
                    "mensaje": textos.mensaje(
                        "A2_iteaf_caduca_pronto",
                        equipo=equipo.nombre,
                        fecha=legal.formatea_fecha(equipo.fecha_proxima_iteaf),
                    ),
                }
            )
        elif equipo.fecha_proxima_iteaf and equipo.fecha_proxima_iteaf < referencia:
            salida.append(
                {
                    "tipo": "iteaf",
                    "urgente": True,
                    "mensaje": textos.mensaje("V7_iteaf_caducada", equipo=equipo.nombre),
                }
            )

    for producto in db.scalars(
        select(models.ProductoFitosanitario).where(
            models.ProductoFitosanitario.explotacion_id == explotacion.id
        )
    ):
        if legal.caduca_pronto(producto.fecha_caducidad, 60, referencia):
            salida.append(
                {
                    "tipo": "producto",
                    "urgente": False,
                    "mensaje": textos.mensaje(
                        "A4_producto_caduca_pronto",
                        producto=producto.nombre_comercial,
                        fecha=legal.formatea_fecha(producto.fecha_caducidad),
                    ),
                }
            )
        # --- la autorización excepcional ---
        #
        # Es el permiso temporal para usar un producto que no está autorizado con carácter
        # general. Se avisa antes de que acabe y, si ya acabó, se dice: el programa **no dejará
        # apuntarlo** (lo comprueba `validaciones.V1_autorizacion_caducada`). Ese aviso y esa
        # comprobación existían desde el principio, pero la fecha no se podía meter desde ninguna
        # pantalla, así que no podían saltar nunca. Esto es lo que les da el dato que les faltaba.
        if legal.caduca_pronto(producto.autorizacion_hasta, legal.DIAS_AVISO_AUTORIZACION, referencia):
            salida.append(
                {
                    "tipo": "autorizacion",
                    "urgente": (legal.dias_hasta(producto.autorizacion_hasta, referencia) or 0) <= 15,
                    "mensaje": textos.mensaje(
                        "A24_autorizacion_caduca_pronto",
                        producto=producto.nombre_comercial,
                        fecha=legal.formatea_fecha(producto.autorizacion_hasta),
                    ),
                }
            )
        elif producto.autorizacion_hasta and producto.autorizacion_hasta < referencia:
            salida.append(
                {
                    "tipo": "autorizacion_caducada",
                    "urgente": True,
                    "mensaje": textos.mensaje(
                        "A25_autorizacion_caducada",
                        producto=producto.nombre_comercial,
                        fecha=legal.formatea_fecha(producto.autorizacion_hasta),
                    ),
                }
            )

        # --- el número de registro, contra el listado oficial de productos del MAPA ---
        #
        # Es un dato que se puede comprobar de verdad desde la ronda 30: el listado oficial está
        # bajado en `data/fega/` con su procedencia. Se avisa, **no se bloquea**: el agricultor puede
        # apuntar lo que quiera, pero en una inspección el número de registro es lo que se mira.
        #
        # Y si el listado no está bajado, `aviso_sobre_el_numero` devuelve `None` y **no se dice
        # nada**: un programa que asegura «ese producto no existe» cuando en realidad no tiene la
        # lista es peor que uno que se calla.
        aviso_del_registro = registro_oficial_de_productos.aviso_sobre_el_numero(
            producto.numero_registro
        )
        if aviso_del_registro is not None:
            ficha = aviso_del_registro.get("ficha") or {}
            if aviso_del_registro["codigo"] == "no_vigente":
                salida.append(
                    {
                        "tipo": "producto_no_vigente",
                        "urgente": True,
                        "mensaje": textos.mensaje(
                            "A27_producto_no_vigente",
                            producto=producto.nombre_comercial,
                            numero=aviso_del_registro["numero"],
                            estado=ficha.get("estado") or "",
                        ),
                    }
                )
            elif aviso_del_registro["codigo"] == "no_esta_en_el_registro":
                salida.append(
                    {
                        "tipo": "numero_de_registro",
                        "urgente": False,
                        "mensaje": textos.mensaje(
                            "A26_numero_de_registro_desconocido",
                            producto=producto.nombre_comercial,
                            numero=aviso_del_registro["numero"],
                        ),
                    }
                )
            elif aviso_del_registro["codigo"] == "escrito_de_otra_forma":
                salida.append(
                    {
                        "tipo": "numero_de_registro_de_otra_forma",
                        "urgente": False,
                        "mensaje": textos.mensaje(
                            "A28_numero_de_registro_de_otra_forma",
                            producto=producto.nombre_comercial,
                            numero=aviso_del_registro["numero"],
                            oficial=aviso_del_registro["oficial"],
                        ),
                    }
                )

    if not salida:
        salida.append(
            {"tipo": "todo_bien", "urgente": False, "mensaje": textos.mensaje("A8_todo_en_orden")}
        )

    salida.sort(key=lambda aviso: not aviso["urgente"])
    return {"avisos": salida}

# --------------------------------------------------------------------------
# La foto de la etiqueta del producto (CRM-07 #10, 14/10/2026)
# --------------------------------------------------------------------------
#
# **La columna existia desde el principio y no la usaba nadie** (`models.py:439`,
# `ProductoFitosanitario.foto_etiqueta`): se daba de alta, se leia y ningun router la escribia. El
# contrato pide «fotos de etiqueta/justificante **como evidencia**», asi que aqui estan las dos
# puertas, **copiando la forma de la de la semilla** (`semillas_api.py:533`), que ya esta probada:
#
#   * **el fichero va al disco y en la base queda solo la ruta** (`app/adjuntos.py`): una foto de un
#     movil son cuatro megas y meterla en una columna haria que la copia de seguridad del agricultor
#     dejase de poderse manejar.
#   * **el nombre que manda el navegador no se usa como ruta**: la pone el programa, con la carpeta
#     de la finca y un identificador aleatorio.
#   * **el fichero viejo se borra DESPUES de guardar el nuevo**: si se borrara antes y fallara el
#     guardado, el agricultor se quedaria sin el papel que acababa de subir.
#   * y se sirve **solo si es de esta finca**.


@router.post("/productos/{producto_id}/etiqueta", response_model=ProductoSalida)
async def subir_la_foto_de_la_etiqueta(
    producto_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    fichero: UploadFile = File(...),
) -> models.ProductoFitosanitario:
    """Guardar la foto de la etiqueta con el producto."""
    producto = obtener_de_la_explotacion(
        db, models.ProductoFitosanitario, producto_id, explotacion.id
    )
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS_DE_ETIQUETA)
    nombre, ruta, tipo, tamano = adjuntos.guardar_en_disco(
        explotacion_id=explotacion.id,
        prefijo="etiqueta-producto",
        fichero=fichero,
        contenido=contenido,
        permitidos=TIPOS_DE_ETIQUETA,
    )
    anterior = producto.foto_etiqueta
    producto.foto_etiqueta = ruta
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="producto",
            entidad_id=producto.id,
            accion="subir_etiqueta",
            datos={"fichero": nombre, "tipo": tipo, "bytes": tamano},
        )
    )
    db.commit()
    db.refresh(producto)
    # **El fichero viejo se borra despues**, no antes: ver la cabecera de esta seccion.
    if anterior and anterior != ruta:
        adjuntos.borrar_del_disco(anterior)
    return producto


@router.get("/productos/{producto_id}/etiqueta")
def ver_la_foto_de_la_etiqueta(
    producto_id: int, explotacion: ExplotacionActual, db: Db
) -> FileResponse:
    """La foto de la etiqueta. La sirve el programa, y **solo si es de esta finca**."""
    producto = obtener_de_la_explotacion(
        db, models.ProductoFitosanitario, producto_id, explotacion.id
    )
    if not producto.foto_etiqueta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este producto no tiene la foto de la etiqueta.",
        )
    return FileResponse(
        adjuntos.ruta_segura(producto.foto_etiqueta),
        media_type="application/octet-stream",
        filename="etiqueta",
    )
