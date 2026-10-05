"""Facturas de compra: subirlas, que el programa las lea y que el agricultor las confirme.

## El recorrido, tal y como lo vive el agricultor

1. **Hace una foto** (o sube el PDF que le ha mandado el proveedor) desde el móvil.
2. **El programa la lee** y le enseña **lo que ha entendido**: el proveedor, el NIF, la fecha, el
   número de factura, los totales y cada línea con su producto, su cantidad y su precio.
3. **Él dice si está bien o lo corrige.** Lo que se guarda es lo que él ha dado por bueno. Esto no
   es un detalle: es lo que hace que se pueda leer una foto hecha con el móvil sin jugarse un dato.
4. **Queda en la base** y sirve para tres cosas: saber **cuánto producto se ha comprado** (y
   compararlo con lo que se ha echado), rellenar la **«empresa suministradora» y el «nº de factura»**
   que pide la hoja 9.1 del cuaderno de la Junta, y tener **el justificante** a mano si alguien lo
   pide (el cuaderno dice que hay que conservarlo tres años).

## Las decisiones

1. **Leer y guardar son dos puertas distintas** (`/leer` no escribe nada). Igual que con el cuaderno
   de la Junta: primero se enseña lo que se ha entendido, y solo después se guarda.
2. **Nada se inventa.** Si no hay lector de fotos instalado, si el PDF es un escaneo sin letras o si
   una línea no cuadra, se dice — y la factura se puede guardar igual con los datos que escriba el
   agricultor. Una factura con datos inventados es peor que una factura a medias.
3. **El fichero va a disco, no a la base** (`app/adjuntos.py`), igual que los boletines y los
   papeles.
4. **La cantidad comprada se saca de las facturas**, y cuando las unidades no se pueden comparar
   —comprado en «botes», echado en litros— **no se resta**: se dice por qué. Es la misma regla que
   ya seguía la cesta del almacén.
5. **Y desde la ronda 94 una factura se puede corregir y borrar**, que es lo que pidió David:
   «recuerda también dejar borrar las cosas que introduzca porque puede que me equivoque, o
   modificar también». Con una condición, y está razonada en `borrar_factura`: **el borrado no puede
   dejar la cesta del almacén diciendo una cosa y el cuaderno otra**. Corregir, en cambio, no se
   niega nunca: corregir es decir la verdad, y si la verdad deja el cuadre en rojo, el programa ya lo
   cuenta con sus palabras (`textos.MENSAJES["A22_gastado_mas_que_comprado"]`).
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import adjuntos, correcciones, facturas as lectura, legal, models, ocr, servicios, textos
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    FacturaEntrada,
    FacturaLeidaSalida,
    FacturaSalida,
    LineaDeFacturaLeidaSalida,
    LineaDeFacturaSalida,
)

router = APIRouter(prefix="/api/facturas", tags=["facturas"])

# Lo que se admite: la factura del proveedor en PDF, o una foto del papel. Se reutiliza la lista de
# los papeles anexos, que ya está probada, para no tener dos listas de tipos de fichero.
TIPOS = adjuntos.TIPOS_DOCUMENTO


def _productos_conocidos(db, explotacion) -> list[dict]:
    """La cesta del agricultor, para poder decir «esta línea es el Glifosato que ya tienes»."""
    return [
        {
            "id": producto.id,
            "nombre_comercial": producto.nombre_comercial,
            "numero_registro": producto.numero_registro,
            "materia_activa": producto.materia_activa,
        }
        for producto in db.scalars(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == explotacion.id
            )
        )
    ]


def _abonos_conocidos(db, explotacion) -> list[dict]:
    """Los abonos de la finca, con su composición **o diciendo que no consta** (A6, 03/10/2026).

    La composición de un abono puede ser «no lo sé» desde que las riquezas tienen tres estados, y aquí se
    formateaban con `:g`: con un `None` eso revienta. Hoy esta función no la llama nadie, pero el día que se
    use reventaría por un dato que el programa ya admite a propósito.
    """

    def composicion(abono) -> str:
        if abono.riqueza_n is None or abono.riqueza_p is None or abono.riqueza_k is None:
            return ""
        return f"{abono.riqueza_n:g}-{abono.riqueza_p:g}-{abono.riqueza_k:g}"

    return [
        {"id": abono.id, "nombre": abono.nombre, "riqueza": composicion(abono)}
        for abono in db.scalars(
            select(models.Fertilizante).where(models.Fertilizante.explotacion_id == explotacion.id)
        )
    ]


def _ya_estaba(db, explotacion, huella: str) -> models.Factura | None:
    """¿Esta misma factura ya se subió? Se mira por la huella del fichero.

    Subir dos veces la misma foto es lo que hace todo el mundo, y apuntar dos veces la misma compra
    descuadraría el almacén y las cuentas. Se avisa, y el agricultor decide.
    """
    if not huella:
        return None
    return db.scalar(
        select(models.Factura).where(
            models.Factura.explotacion_id == explotacion.id,
            models.Factura.huella == huella,
            models.Factura.anulada.is_(False),
        )
    )


@router.post("/leer", response_model=FacturaLeidaSalida)
async def leer_una_factura(
    explotacion: ExplotacionActual, db: Db, fichero: UploadFile = File(...)
) -> FacturaLeidaSalida:
    """Mira el documento y cuenta lo que ha entendido. **No guarda nada.**"""
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS)
    leida = lectura.leer_factura(
        contenido,
        nif_del_agricultor=explotacion.nif,
        productos=_productos_conocidos(db, explotacion),
    )
    ya_estaba = _ya_estaba(db, explotacion, ocr.huella(contenido))
    return FacturaLeidaSalida(
        proveedor=leida.proveedor,
        proveedor_nif=leida.proveedor_nif,
        numero_factura=leida.numero_factura,
        fecha=leida.fecha,
        base_imponible=leida.base_imponible,
        cuota_iva=leida.cuota_iva,
        tipo_iva_pct=leida.tipo_iva_pct,
        total=leida.total,
        lineas=[
            LineaDeFacturaLeidaSalida(
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                unidad=linea.unidad,
                precio_unitario=linea.precio_unitario,
                importe=linea.importe,
                numero_registro=linea.numero_registro,
                cuadra=linea.cuadra,
                confianza=linea.confianza,
                producto_sugerido_id=linea.producto_sugerido_id,
                producto_sugerido=linea.producto_sugerido,
                como_se_sugiere=linea.como_se_sugiere,
            )
            for linea in leida.lineas
        ],
        como_se_leyo=leida.como_se_leyo,
        idioma_del_lector=leida.idioma_del_lector,
        texto_crudo=leida.texto_crudo,
        avisos=leida.avisos,
        resumen=leida.resumen(),
        ya_estaba=ya_estaba.id if ya_estaba else None,
    )


def _con_nombres(db, factura: models.Factura) -> FacturaSalida:
    """La factura con los nombres de sus productos y abonos ya resueltos."""
    productos = {
        producto.id: producto.nombre_comercial
        for producto in db.scalars(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == factura.explotacion_id
            )
        )
    }
    abonos = {
        abono.id: abono.nombre
        for abono in db.scalars(
            select(models.Fertilizante).where(
                models.Fertilizante.explotacion_id == factura.explotacion_id
            )
        )
    }
    lineas = [
        LineaDeFacturaSalida(
            id=linea.id,
            descripcion=linea.descripcion,
            cantidad=linea.cantidad,
            unidad=linea.unidad,
            precio_unitario=linea.precio_unitario,
            importe=linea.importe,
            numero_registro=linea.numero_registro,
            lote=linea.lote,
            producto_id=linea.producto_id,
            fertilizante_id=linea.fertilizante_id,
            producto=productos.get(linea.producto_id),
            fertilizante=abonos.get(linea.fertilizante_id),
            cuadra=_cuadra(linea),
        )
        for linea in factura.lineas
    ]
    return FacturaSalida(
        id=factura.id,
        campana_id=factura.campana_id,
        fecha=factura.fecha,
        proveedor=factura.proveedor,
        proveedor_nif=factura.proveedor_nif,
        numero_factura=factura.numero_factura,
        base_imponible=factura.base_imponible,
        cuota_iva=factura.cuota_iva,
        tipo_iva_pct=factura.tipo_iva_pct,
        total=factura.total,
        notas=factura.notas,
        leida_por=factura.leida_por,
        tiene_fichero=bool(factura.fichero_ruta),
        nombre_del_fichero=factura.fichero_nombre,
        anulada=factura.anulada,
        motivo_anulacion=factura.motivo_anulacion,
        creada_en=factura.creada_en,
        lineas=lineas,
    )


def _cuadra(linea: models.LineaDeFactura) -> bool | None:
    """cantidad × precio = importe. Se calcula al leer y no se guarda: así sigue siendo verdad
    después de que el agricultor corrija un número."""
    if linea.cantidad is None or linea.precio_unitario is None or linea.importe is None:
        return None
    if linea.cantidad <= 0 or linea.precio_unitario <= 0:
        return None
    return abs(linea.cantidad * linea.precio_unitario - linea.importe) <= max(
        0.03, abs(linea.importe) * 0.02
    )


def _la_campana(db, explotacion, fecha: dt.date | None) -> models.Campana | None:
    """La campaña del año de la factura, o la del año en curso.

    Una factura es de un año, y el almacén y el cuadre se miran por campaña: si la factura es de
    diciembre y se sube en enero, lo que manda es el año del papel, no el del día en que se sube.
    """
    anio = (fecha or dt.date.today()).year
    campana = db.scalar(
        select(models.Campana).where(
            models.Campana.explotacion_id == explotacion.id,
            models.Campana.anio == anio,
        )
    )
    if campana is None:
        campana = db.scalar(
            select(models.Campana)
            .where(models.Campana.explotacion_id == explotacion.id)
            .order_by(models.Campana.anio.desc())
            .limit(1)
        )
    return campana


@router.post("", response_model=FacturaSalida, status_code=status.HTTP_201_CREATED)
async def guardar_una_factura(
    explotacion: ExplotacionActual,
    db: Db,
    datos: str = File(...),
    fichero: UploadFile | None = File(default=None),
) -> FacturaSalida:
    """Guarda la factura que el agricultor ha confirmado, con su fichero si lo hay.

    Los datos llegan como un JSON en el campo `datos` porque en la misma petición viaja el fichero:
    un formulario con fichero no puede llevar un cuerpo JSON normal.
    """
    import json

    try:
        entrada = FacturaEntrada.model_validate(json.loads(datos))
    except (ValueError, TypeError) as fallo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No se han podido leer los datos de la factura.",
        ) from fallo

    factura = _preparar_factura_guardable(entrada, explotacion, db)
    db.add(factura)
    # Se guarda antes de las líneas porque cada línea necesita **el identificador de su factura**
    # (`lineas_de_factura.factura_id`), y ese identificador lo pone la base de datos al insertarla.
    db.flush()
    for linea in _preparar_lineas_de_la_factura(
        db,
        explotacion,
        entrada.lineas,
        factura_id=factura.id,
        fecha=factura.fecha,
        proveedor=factura.proveedor,
    ):
        db.add(linea)

    if fichero is not None and (fichero.filename or ""):
        contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS)
        nombre, ruta, tipo, bytes_escritos = adjuntos.guardar_en_disco(
            explotacion_id=explotacion.id,
            prefijo="factura",
            fichero=fichero,
            contenido=contenido,
            permitidos=TIPOS,
        )
        factura.fichero_nombre = nombre
        factura.fichero_ruta = ruta
        factura.fichero_tipo = tipo
        factura.fichero_bytes = bytes_escritos
        factura.huella = ocr.huella(contenido)

    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="factura",
            entidad_id=factura.id,
            accion="guardar_factura",
            datos={
                "proveedor": factura.proveedor,
                "numero_factura": factura.numero_factura,
                "total": factura.total,
                "lineas": len(entrada.lineas),
                "leida_por": factura.leida_por,
            },
        )
    )
    db.commit()
    db.refresh(factura)
    return _con_nombres(db, factura)


def _preparar_factura_guardable(
    entrada: FacturaEntrada, explotacion, db, *, actual: models.Factura | None = None
) -> models.Factura:
    """Comprueba una factura y la devuelve lista para guardar, **sin guardarla**.

    Lo usan el alta y la corrección, y **es a propósito**: las dos tienen que hacer lo mismo con lo
    que manda el formulario (recortar los textos, dejar los vacíos en «no lo sé», sacar la campaña
    del año del papel). Si la corrección copiara lo que llega sin más, una factura corregida podría
    quedarse en la campaña que no es.

    **La campaña se vuelve a calcular**, y esto es una decisión: el alta la saca del **año de la
    fecha del papel** (`_la_campana`), no del formulario —`FacturaEntrada` no la acepta—, así que
    corregir la fecha de una factura de diciembre que se apuntó en enero tiene que cambiarle la
    campaña. Es el mismo caso que la zona de nitratos de una tierra: **lo que el alta calcula sola
    se vuelve a calcular al corregir**, y por eso se pone después de copiar lo que el formulario no
    puede mandar de vuelta.

    `actual` es la factura que se está corrigiendo. Sirve para **dejar quieto lo que el formulario no
    puede mandar ni debe**: su fichero (nombre de disco, ruta, tipo y bytes), su huella y la fecha en
    que se apuntó (ver `servicios.columnas_que_una_correccion_no_toca`). Corregir un número no puede
    dejar la factura sin su justificante, y menos aún resucitar una anulada o dejar la fecha de alta
    en blanco.
    """
    # La campaña se saca del **año del papel**, no del día en que se sube: una factura de diciembre
    # subida en enero es de la campaña que acaba.
    campana = _la_campana(db, explotacion, entrada.fecha)
    factura = models.Factura(
        explotacion_id=explotacion.id,
        campana_id=campana.id if campana else None,
        fecha=entrada.fecha,
        proveedor=(entrada.proveedor or "").strip() or None,
        proveedor_nif=(entrada.proveedor_nif or "").strip() or None,
        numero_factura=(entrada.numero_factura or "").strip() or None,
        base_imponible=entrada.base_imponible,
        cuota_iva=entrada.cuota_iva,
        tipo_iva_pct=entrada.tipo_iva_pct,
        total=entrada.total,
        notas=entrada.notas,
        leida_por=(entrada.leida_por or "a mano").strip()[:20],
    )
    if actual is not None:
        for columna in servicios.columnas_que_una_correccion_no_toca(
            models.Factura, FacturaEntrada, FacturaSalida
        ):
            setattr(factura, columna, getattr(actual, columna))
        # Y la campaña se pone **después**, porque la de arriba es la del año del papel y es la que
        # manda: ver la decisión del principio.
        factura.campana_id = campana.id if campana else None
    return factura


def _preparar_lineas_de_la_factura(
    db,
    explotacion,
    lineas_de_la_entrada,
    *,
    factura_id: int,
    fecha: dt.date | None,
    proveedor: str | None,
) -> list[models.LineaDeFactura]:
    """Las líneas de una factura, comprobadas y listas para guardar, **sin guardarlas**.

    Lo usan el alta y la corrección, para que las dos pasen por lo mismo: que el producto y el abono
    a los que se engancha una línea sean **de esta finca** (lo de otra contesta 404, como todo en
    esta API) y que lo que se da de alta con lo que dice la factura se dé de alta igual
    (`_producto_de_la_factura`). Si la corrección se hiciera por su cuenta, una factura corregida
    podría acabar enganchada a un producto de otro agricultor.

    `fecha` y `proveedor` se pasan aparte del identificador a propósito: cuando se está corrigiendo,
    el identificador es el de la factura guardada pero la fecha y el proveedor que hay que escribir
    en un producto nuevo son **los corregidos**, no los viejos.

    Las líneas se devuelven sin guardar y **se rehacen enteras** al corregir (ver `corregir_factura`):
    nada del programa apunta a una línea, así que no hay nada que se quede colgando de una línea que
    ya no está.
    """
    lineas: list[models.LineaDeFactura] = []
    for linea in lineas_de_la_entrada:
        _comprobar_que_es_suya(db, explotacion, linea.producto_id, models.ProductoFitosanitario)
        _comprobar_que_es_suya(db, explotacion, linea.fertilizante_id, models.Fertilizante)
        producto_id = linea.producto_id or _producto_de_la_factura(
            db,
            explotacion,
            linea,
            factura_id=factura_id,
            fecha=fecha,
            proveedor=proveedor,
        )
        lineas.append(
            models.LineaDeFactura(
                explotacion_id=explotacion.id,
                factura_id=factura_id,
                descripcion=linea.descripcion.strip()[:200],
                cantidad=linea.cantidad,
                unidad=(linea.unidad or "").strip()[:20] or None,
                precio_unitario=linea.precio_unitario,
                importe=linea.importe,
                numero_registro=(linea.numero_registro or "").strip()[:40] or None,
                lote=(linea.lote or "").strip()[:60] or None,
                producto_id=producto_id,
                fertilizante_id=linea.fertilizante_id,
            )
        )
    return lineas


def _comprobar_que_es_suya(db, explotacion, identificador: int | None, tabla) -> None:
    """Un producto o un abono de otra explotación no se puede enganchar a esta factura.

    Es la misma regla que en el resto del programa: los datos de una finca no se pueden mezclar con
    los de otra, ni por error ni a propósito.
    """
    if identificador is None:
        return
    obtener_de_la_explotacion(db, tabla, identificador, explotacion.id)


def _producto_de_la_factura(
    db,
    explotacion,
    linea,
    *,
    factura_id: int,
    fecha: dt.date | None,
    proveedor: str | None,
) -> int | None:
    """Da de alta el producto de una línea, si el agricultor ha dicho que no lo tiene apuntado.

    Se crea con **lo que dice la factura**, que es de donde salen los datos de verdad:

    * el nombre comercial, de la descripción de la línea;
    * el número de registro, si la factura lo trae impreso (es el dato que identifica al producto
      sin lugar a dudas, y el que después hace que se pueda mandar al cuaderno);
    * la cantidad comprada y su unidad, la fecha de la factura y el proveedor.

    La fecha, el proveedor y el identificador se pasan aparte —y no la factura entera— porque al
    **corregir** una factura valen cosas distintas de sitios distintos: el identificador es el de la
    factura guardada, y la fecha y el proveedor tienen que ser **los corregidos**, que son con los
    que se está guardando.

    **Lo que no se inventa**: la dosis máxima, el plazo de seguridad y la materia activa. Eso está en
    la etiqueta del bote y no en la factura, así que se quedan vacíos hasta que el agricultor los
    apunte (el programa ya le avisa cuando un producto no tiene dosis).

    Y si ya hay un producto con el mismo nombre o el mismo número de registro, **se engancha a ese**
    en vez de crear otro: dos fichas del mismo producto descuadrarían el almacén.
    """
    if not linea.crear_producto or not linea.descripcion.strip():
        return None

    existente = _producto_que_ya_esta(db, explotacion, linea)
    if existente is not None:
        return existente.id

    producto = models.ProductoFitosanitario(
        explotacion_id=explotacion.id,
        nombre_comercial=linea.descripcion.strip()[:200],
        numero_registro=(linea.numero_registro or "").strip()[:40] or None,
        cantidad_comprada=linea.cantidad,
        unidad_compra=(linea.unidad or "").strip()[:10] or "L",
        fecha_compra=fecha,
        proveedor=(proveedor or "").strip()[:200] or None,
    )
    db.add(producto)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="producto",
            entidad_id=producto.id,
            accion="crear_desde_una_factura",
            datos={
                "nombre_comercial": producto.nombre_comercial,
                "numero_registro": producto.numero_registro,
                "factura_id": factura_id,
            },
        )
    )
    return producto.id


def _producto_que_ya_esta(db, explotacion, linea) -> models.ProductoFitosanitario | None:
    """¿Ese producto ya está en la cesta? Se mira por el número de registro y por el nombre."""
    registro = (linea.numero_registro or "").strip()
    if registro:
        encontrado = db.scalar(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == explotacion.id,
                models.ProductoFitosanitario.numero_registro == registro,
            )
        )
        if encontrado is not None:
            return encontrado
    clave = servicios.clave_de_producto(linea.descripcion)
    for producto in db.scalars(
        select(models.ProductoFitosanitario).where(
            models.ProductoFitosanitario.explotacion_id == explotacion.id
        )
    ):
        if servicios.clave_de_producto(producto.nombre_comercial) == clave:
            return producto
    return None


@router.get("", response_model=list[FacturaSalida])
def listar_facturas(
    explotacion: ExplotacionActual, db: Db, incluir_anuladas: bool = False
) -> list[FacturaSalida]:
    consulta = select(models.Factura).where(models.Factura.explotacion_id == explotacion.id)
    if not incluir_anuladas:
        consulta = consulta.where(models.Factura.anulada.is_(False))
    facturas = list(
        db.scalars(consulta.order_by(models.Factura.fecha.desc().nullslast(), models.Factura.id.desc()))
    )
    return [_con_nombres(db, factura) for factura in facturas]


@router.get("/estado")
def estado_del_lector(explotacion: ExplotacionActual, db: Db) -> dict:
    """Lo que la pantalla necesita: si se pueden leer las fotos y con qué idioma."""
    return {
        "textos": textos.FACTURAS,
        "lector": ocr.estado(),
        "tipos_de_fichero": [extension.lstrip(".") for extension in sorted(set(TIPOS.values()))],
        "unidades": sorted(lectura.UNIDADES.values()),
    }


@router.get("/resumen")
def lo_comprado_por_producto(explotacion: ExplotacionActual, db: Db) -> list[dict]:
    """Lo comprado de cada producto, con las facturas de donde sale.

    Es la mitad del cuadre que pidió David: **lo comprado contra lo echado**. La otra mitad la da
    `GET /api/cesta`, que ya sabía cuánto se ha echado. Aquí se dice, además, **de qué factura**
    sale cada compra, que es lo que hay que poder enseñar.
    """
    from .. import servicios

    return servicios.comprado_por_producto(db, explotacion_id=explotacion.id)


@router.get("/{factura_id}", response_model=FacturaSalida)
def ver_factura(factura_id: int, explotacion: ExplotacionActual, db: Db) -> FacturaSalida:
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    return _con_nombres(db, factura)


@router.post("/{factura_id}/fichero", response_model=FacturaSalida)
async def subir_el_fichero(
    factura_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    fichero: UploadFile = File(...),
) -> FacturaSalida:
    """Sube (o cambia) la foto o el PDF de una factura ya guardada."""
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS)
    nombre, ruta, tipo, bytes_escritos = adjuntos.guardar_en_disco(
        explotacion_id=explotacion.id,
        prefijo="factura",
        fichero=fichero,
        contenido=contenido,
        permitidos=TIPOS,
    )
    anterior = factura.fichero_ruta
    factura.fichero_nombre = nombre
    factura.fichero_ruta = ruta
    factura.fichero_tipo = tipo
    factura.fichero_bytes = bytes_escritos
    factura.huella = ocr.huella(contenido)
    db.commit()
    # El fichero anterior se borra **después** de guardar el nuevo: si fallara el guardado, no se
    # puede quedar la factura sin justificante.
    if anterior:
        adjuntos.borrar_del_disco(anterior)
    db.refresh(factura)
    return _con_nombres(db, factura)


@router.get("/{factura_id}/fichero")
def ver_el_fichero(factura_id: int, explotacion: ExplotacionActual, db: Db) -> FileResponse:
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    if not factura.fichero_ruta:
        raise HTTPException(
            status_code=404, detail=textos.FACTURAS["sin_fichero"]
        )
    ruta = adjuntos.ruta_segura(factura.fichero_ruta)
    return FileResponse(
        ruta,
        media_type=factura.fichero_tipo or "application/octet-stream",
        filename=factura.fichero_nombre or "factura",
    )


@router.post("/{factura_id}/anular", response_model=FacturaSalida)
def anular_factura(
    factura_id: int, datos: dict, explotacion: ExplotacionActual, db: Db
) -> FacturaSalida:
    """Anula la factura con su motivo. **No se borra nada**: el fichero y el apunte se quedan."""
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    motivo = (datos.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.FACTURAS["falta_motivo"],
        )
    factura.anulada = True
    factura.motivo_anulacion = motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="factura",
            entidad_id=factura.id,
            accion="anular_factura",
            datos={"motivo": motivo},
        )
    )
    db.commit()
    db.refresh(factura)
    return _con_nombres(db, factura)


# --------------------------------------------------------------------------
# Corregir y borrar una factura (ronda 94)
# --------------------------------------------------------------------------


def _linea_como_rastro(linea: models.LineaDeFactura) -> dict:
    """Una línea reducida a lo que hay que poder volver a leer después en la auditoría.

    **Lo que se compró es la factura**: borrarla sin dejar escrito qué llevaba dentro sería perder
    justo el dato que engancha con la cesta (el producto y su número de registro). Y las líneas no
    son columnas de la factura, así que la cuenta que hace `correcciones.borrar` —que recorre las
    columnas de la fila— no las coge: por eso se apuntan aparte, al corregir y al borrar.
    """
    return {
        "descripcion": linea.descripcion,
        "cantidad": linea.cantidad,
        "unidad": linea.unidad,
        "precio_unitario": linea.precio_unitario,
        "importe": linea.importe,
        "numero_registro": linea.numero_registro,
        "lote": linea.lote,
        "producto_id": linea.producto_id,
        "fertilizante_id": linea.fertilizante_id,
    }


def _lineas_como_rastro(lineas) -> list[dict]:
    return [_linea_como_rastro(linea) for linea in lineas]


def _apuntes_que_se_quedarian_sin_compra(db, explotacion, factura: models.Factura) -> int:
    """Cuántos apuntes se quedarían diciendo que se echó producto que la cesta ya no da por comprado.

    **Es la cuenta que decide si una factura se puede borrar** (ver `borrar_factura`), y se le
    pregunta a la propia cesta: se mira qué diría **con** la factura y qué diría **sin ella**
    (`servicios.comprado_de_un_producto(..., excluyendo_factura_id=...)`, que recorre el mismo camino
    que cuando no existe de verdad, incluida la vuelta a la cifra de la ficha del producto).

    **Solo se cuentan las que el borrado convertiría en un descuadre.** O sea: si con la factura la
    cuenta cuadraba (o no se sabía cuánto se compró) y sin ella sale que se ha echado más de lo
    comprado, esos apuntes se quedan sin compra que los explique y el borrado se niega. Y al revés:

      · Si la cuenta **ya venía descuadrada**, borrar la factura no le añade ninguna mentira nueva
        —el programa ya lo está diciendo con sus palabras y el agricultor sabe por qué (el producto
        puede venir de la campaña anterior)—, así que no se niega.
      · **Una factura anulada cae siempre en ese caso**, y sale sola: el «comprado» deja fuera las
        anuladas, así que la cuenta es exactamente la misma con ella y sin ella. Por eso hay un camino
        para deshacerse de una factura sin dejar el cuadre mintiendo: **anularla con su motivo y
        después borrarla**.
      · **Cuando la cuenta no se puede hacer, no se niega nada**: si las unidades no se pueden
        comparar, no se afirma un descuadre y el borrado pasa. La cesta dirá «no lo sé», que es lo
        que dice cuando no lo sabe.

    Se cuentan **los apuntes de todas las campañas** (`campana_id=None`), no solo los de la factura:
    el «comprado» de la cesta se suma **sin mirar la campaña** (ver `comprado_de_un_producto`), así
    que la compra que se va la echan de menos todas.
    """
    productos = {
        linea.producto_id for linea in factura.lineas if linea.producto_id is not None
    }
    se_quedarian_sin_compra = 0
    for producto_id in sorted(productos):
        producto = db.get(models.ProductoFitosanitario, producto_id)
        if producto is None:
            # Una línea enganchada a un producto que ya no está no puede descuadrar nada: lo que se
            # ha echado de ese producto ya no se puede comparar con nada.
            continue
        gastado, apuntes = servicios.lo_gastado_de_un_producto(
            db, explotacion_id=explotacion.id, producto_id=producto_id, campana_id=None
        )
        if not apuntes:
            continue
        unidad_compra = (producto.unidad_compra or "").strip()
        # La unidad de lo que se echa se saca de la dosis del producto, igual que en la cesta.
        unidad_gastado = legal.unidad_de_una_dosis(producto.unidad_dosis)
        queda_con = servicios.lo_que_queda_de_un_producto(
            servicios.comprado_de_un_producto(
                db, explotacion_id=explotacion.id, producto=producto
            )[0],
            gastado,
            unidad_compra,
            unidad_gastado,
        )[1]
        queda_sin = servicios.lo_que_queda_de_un_producto(
            servicios.comprado_de_un_producto(
                db,
                explotacion_id=explotacion.id,
                producto=producto,
                excluyendo_factura_id=factura.id,
            )[0],
            gastado,
            unidad_compra,
            unidad_gastado,
        )[1]
        if queda_sin is None or queda_sin >= 0:
            continue
        if queda_con is not None and queda_con < 0:
            continue
        se_quedarian_sin_compra += apuntes
    return se_quedarian_sin_compra


def _tablas_que_apuntan_a_una_factura() -> list:
    """Las tablas del cuaderno que apuntan a una factura, **quitando sus propias líneas**.

    Se saca de las tablas de verdad y no de una lista escrita a mano (`correcciones.tablas_que_apuntan_a`),
    por el mismo motivo que la cuenta de las tierras: el día que se añada otra tabla que apunte a una
    factura, sale aquí sola y el borrado la cuenta en vez de reventar al guardar.

    Hoy son dos, y la diferencia entre las dos es la decisión:

      · **`lineas_de_factura`**: las líneas **son parte de la factura** y se van con ella en cascada
        (`Factura.lineas`, `cascade="all, delete-orphan"`). Contarlas como dependencia bloquearía
        todos los borrados, así que se quedan fuera, y lo que se cuenta en su lugar es la cesta
        (`_apuntes_que_se_quedarian_sin_compra`).
      · **`fertilizaciones`**: un abono puede decir **de qué factura salió** (`Fertilizacion.factura_id`,
        lo que permite contestar «¿de qué compra es este abono?» en una inspección). Eso sí es una
        dependencia de verdad: sin la factura, ese abono se queda sin decir de dónde salió —y la base
        de datos no admitiría la fila—, así que se cuenta y contesta 409, como todo lo que está en uso.
    """
    return [
        modelo
        for modelo in correcciones.tablas_que_apuntan_a("factura_id")
        if modelo is not models.LineaDeFactura
    ]


def _cuantos_apuntes_usan_la_factura(db, explotacion_id: int, factura_id: int) -> int:
    """Cuántas cosas del cuaderno apuntan a esa factura (los abonos que salieron de ella)."""
    return sum(
        correcciones.cuantas_filas_apuntan_a(
            db, modelo, "factura_id", factura_id, explotacion_id
        )
        for modelo in _tablas_que_apuntan_a_una_factura()
    )


@router.put("/{factura_id}", response_model=FacturaSalida)
def corregir_factura(
    factura_id: int,
    datos: FacturaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> FacturaSalida:
    """Corrige una factura ya guardada: el proveedor, el NIF, el número, la fecha, los totales **y
    sus líneas** (lo que se compró).

    POR QUÉ SE CORRIGE EN EL SITIO, Y QUÉ PASA CON EL ALMACÉN. La factura se corrige en su misma fila
    —mismo `id`— y lo que había queda escrito en la auditoría (`correcciones`), igual que en los
    apuntes del cuaderno. Y corrigiendo en el sitio es donde hace falta: el agricultor confirma en la
    pantalla lo que el lector **ha entendido** de una foto, y ahí se equivoca uno; hasta ahora la
    única salida era anular la factura y volver a subirla.

    **Y el almacén no hay que arreglarlo: se arregla solo, porque el almacén es una cuenta y no un
    depósito.** Lo que la cesta dice de un producto se calcula cada vez que se mira
    (`servicios.situacion_de_la_cesta`): lo comprado son las líneas de las facturas no anuladas, y lo
    echado son los tratamientos. O sea que cambiar una línea de 20 L a 5 L hace que la cesta diga 5 L
    **la próxima vez que se mire**, sin tocar nada más: no hay un número guardado que se quede
    diciendo lo de antes. Es la misma razón por la que borrar una factura quita del almacén lo que
    metió.

    Las líneas **se rehacen enteras**, no se corrigen una a una. Nada del programa apunta a una línea
    —la única tabla que apunta a `factura_id` es `lineas_de_factura`, que es parte de la propia
    factura—, su identificador no viaja a la Junta, y rehacerlas es lo que garantiza que no quede
    ninguna línea vieja colgando de una factura corregida. Lo que había antes y lo que hay ahora
    queda apuntado en la auditoría (`corregir_lineas`), que es lo que permite contestar «¿y esto qué
    decía?».

    Las comprobaciones son **las mismas que al guardar** (es la misma función,
    `_preparar_factura_guardable` y `_preparar_lineas_de_la_factura`): un producto de otra finca
    contesta 404 con el mismo mensaje que en el alta, y la campaña se vuelve a sacar del año del
    papel. Y las líneas nuevas se preparan **antes** de tocar nada, así que una corrección rechazada
    deja la factura como estaba, con sus números y sus líneas.

    Lo que no se toca es el fichero del justificante (ni su huella): el formulario no lo manda, y
    para cambiarlo está su propia puerta (`POST /api/facturas/{id}/fichero`), que además borra el
    viejo. Y corregir una factura anulada **no la resucita**: el estado de anulación no es un dato
    que el formulario pueda mandar.
    """
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    preparado = _preparar_factura_guardable(datos, explotacion, db, actual=factura)
    lineas_de_antes = _lineas_como_rastro(factura.lineas)
    # Las líneas nuevas se preparan ANTES de tocar la factura: si una trae un producto de otra finca,
    # la corrección se rechaza y aquí no ha cambiado nada.
    lineas_de_ahora = _preparar_lineas_de_la_factura(
        db,
        explotacion,
        datos.lineas,
        factura_id=factura.id,
        fecha=preparado.fecha,
        proveedor=preparado.proveedor,
    )
    correcciones.corregir(
        db,
        guardado=factura,
        preparado=preparado,
        entidad="factura",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    for vieja in list(factura.lineas):
        db.delete(vieja)
    for nueva in lineas_de_ahora:
        db.add(nueva)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="factura",
            entidad_id=factura.id,
            accion="corregir_lineas",
            datos={"antes": lineas_de_antes, "ahora": _lineas_como_rastro(lineas_de_ahora)},
        )
    )
    db.commit()
    db.refresh(factura)
    return _con_nombres(db, factura)


@router.delete("/{factura_id}")
def borrar_factura(
    factura_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Borra una factura, **si con eso la cesta del almacén no empieza a decir cosas que no son**.

    LA DECISIÓN, Y POR QUÉ ES ESA. Lo primero que hay que entender es que **el almacén de este
    programa no es un depósito: es una cuenta**. `servicios.situacion_de_la_cesta` dice lo que queda
    restando lo comprado (que sale de las líneas de las facturas **no anuladas**) menos lo echado (que
    sale de los tratamientos). No hay ninguna fila que diga «tengo 20 litros»: se calcula. De ahí
    salen dos consecuencias, y las dos son buenas:

      1. **Borrar la factura ya quita del almacén lo que metió**, sola: sus líneas se van con ella y
         el «comprado» de ese producto se vuelve a sumar sin ellas. O sea que la opción «borrarla y
         quitar también lo que metió en el almacén» **no hay que programarla**: es lo que pasa. Y es
         lo que hace que la cesta diga la verdad cuando el borrado es correcto (la factura repetida,
         la que no era suya, la que se subió por error).

      2. **Pero si esa compra ya se ha echado, el borrado puede dejar la cuenta coja**: la cesta
         sumaría el gasto de un producto del que ya no queda compra ninguna y diría «has gastado más
         de lo que has comprado» de algo que **sí** se compró —o se quedaría sin saber cuánto se
         compró, que es lo que dice cuando no lo sabe—. Lo primero es lo que no puede pasar: el
         cuaderno diría que se echó y el almacén que no se compró, y en una inspección eso es un
         descuadre que el agricultor no puede explicar. El cuaderno es lo único que este programa no
         puede estropear. (Lo segundo —«no lo sé»— no es una mentira, y por eso no bloquea nada.)

    De las salidas que había sobre la mesa, entonces:

      · **«No dejarla borrar cuando su producto ya se ha usado»**, a secas, se descarta: niega
        borrados que son correctos. El caso que lo rompe es el de siempre —subir dos veces la misma
        factura—: el producto sí se ha echado, pero **la otra factura sigue ahí** y la cuenta cuadra.
        Negarse dejaría al agricultor con una factura falsa dentro, que es justo lo que pidió
        arreglar. Lo que se niega no es «que se haya usado», es **«que el borrado convierta la cuenta
        en un descuadre»**, y eso se pregunta de verdad (`_apuntes_que_se_quedarian_sin_compra`).
      · **«Borrarla y quitar lo que metió en el almacén»** es lo que ya pasa (punto 1): la decisión no
        es esa, es **cuándo se puede**.
      · Y la que se ha tomado es la tercera: **se borra cuando el borrado no convierte el cuadre en un
        descuadre; y cuando sí, no se borra**. En ese caso se contesta 409 con **cuántos apuntes** se
        quedarían sin compra que los explique
        (`textos.mensaje_con_cuenta("B5_en_uso", ...)`, el mensaje de siempre para esto), y las dos
        salidas que se le dan son las de verdad: **corregir la factura** —que es lo que se quiere casi
        siempre, porque el error suele ser un número o una línea— o corregir/borrar los apuntes que la
        usaron. Y si lo que pasa es que la factura sobra porque está **repetida**, lo que corresponde
        no es borrarla: es **anularla** con su motivo —una factura anulada ya no cuenta en la cesta,
        así que borrarla después no cambia ninguna cuenta— y entonces sí se puede borrar sin que el
        cuadre se quede mintiendo.

    Hay otra cosa que tampoco se lleva por delante: **un abono que diga que salió de esta compra**
    (`Fertilizacion.factura_id`). Eso se cuenta primero y contesta 409 igual, porque sin la factura
    ese abono se queda sin decir de dónde salió (y la base de datos no admitiría la fila).

    El fichero del justificante **sí se borra** del disco, y aquí no hay la duda que hay con los
    papeles anulados: si la factura desaparece del cuaderno, dejar su foto o su PDF en el disco es
    basura que nadie va a limpiar —el agricultor no tiene acceso a esa carpeta y ninguna pantalla la
    vuelve a enseñar—. Su ruta la decide el programa al guardar (`adjuntos`), **nunca** el nombre que
    manda el navegador, así que un nombre como `../../main.py` no puede decidir qué fichero se borra.

    Se borra con `correcciones.borrar`, así que queda en la auditoría la fila entera; y además se
    apunta **qué líneas llevaba** (`borrar_lineas`), porque lo que se compró es la factura. Las
    líneas se van con ella: la base de datos las borra en cascada (`Factura.lineas`,
    `cascade="all, delete-orphan"`). Una factura no se firma (ver `firmas_api.ENTIDADES`), así que no
    hay firma que proteger.
    """
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    # Primero, lo que no se puede llevar por delante de ninguna manera: un abono que diga que salió
    # de esta compra. Es la misma cuenta que en todo lo que se puede borrar (`correcciones.en_uso`),
    # quitando las líneas, que son parte de la factura (ver `_tablas_que_apuntan_a_una_factura`).
    usos = _cuantos_apuntes_usan_la_factura(db, explotacion.id, factura_id)
    if usos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B5_en_uso", usos),
        )
    # Y después, la cesta: borrar no puede dejar la cuenta diciendo que se echó producto que ya no
    # se da por comprado (ver `_apuntes_que_se_quedarian_sin_compra`).
    sin_compra = _apuntes_que_se_quedarian_sin_compra(db, explotacion, factura)
    if sin_compra:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B5_en_uso", sin_compra),
        )
    lineas = _lineas_como_rastro(factura.lineas)
    ruta_del_fichero = factura.fichero_ruta
    # El rastro de las líneas se apunta antes de borrar: así entra en el mismo guardado que la
    # factura y no puede quedarse a medias.
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="factura",
            entidad_id=factura.id,
            accion="borrar_lineas",
            datos={"lineas": lineas},
        )
    )
    correcciones.borrar(
        db,
        registro=factura,
        entidad="factura",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    # El fichero se borra **después** de que la fila esté fuera, igual que al reemplazarlo: al revés,
    # un fallo al guardar dejaría la factura apuntada sin su justificante.
    adjuntos.borrar_del_disco(ruta_del_fichero)
    return {
        "borrado": True,
        "id": factura_id,
        "lineas_borradas": len(lineas),
        "fichero_borrado": bool(ruta_del_fichero),
    }
