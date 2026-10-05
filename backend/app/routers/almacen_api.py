"""El almacén: el albarán que llega, los lotes y el libro de movimientos (T09, 03/10/2026).

## Qué había antes de esto y por qué hacía falta

«Lo que tengo en el almacén» **se calculaba**: lo comprado salía de las líneas de las facturas, lo
gastado de los tratamientos, y la resta se hacía cada vez que se miraba la pantalla
(`GET /api/productos/cesta/situacion`, `servicios.situacion_de_la_cesta`). Eso contesta a «¿me queda
producto?», que es la pregunta de todos los días, y **no se ha tocado**: la pantalla del almacén
sigue enseñando exactamente los mismos números que antes.

Lo que no se podía contestar era lo que pide una inspección y lo que pide el contrato del CRM:

  · **de qué lote salió** lo que se echó (si el fabricante avisa de una partida, ¿dónde se fue?);
  · **qué entró de verdad**, que no es lo mismo que lo que se compró: la mercancía entra el día que
    llega el camión, y eso lo dice el albarán, no la factura;
  · **qué se perdió o se contó distinto**, que no es ni un gasto ni una compra.

Este router añade eso: `Articulo`, `Lote`, `Recepcion`, `LineaDeRecepcion` y
`MovimientoDeExistencias`, con sus puertas.

## Las tres protecciones que no se pueden romper, y cómo se cumplen aquí

1. **La misma mercancía no entra dos veces.** Las entradas del libro las crea **solo** la recepción
   del albarán. La factura no mete ni un litro: cuando llega después, se engancha al albarán
   (`POST /api/almacen/recepciones/{id}/factura`) y ahí se acaba (caso A15 del contrato).

2. **Recibir dos veces el mismo albarán no duplica nada.** Se reconoce por la clave de reenvío de la
   petición —lo que manda la cola del móvil cuando apunta sin cobertura (`web/nucleo.js`: `id_local`,
   y `mandarPendientes` en `web/app.js` reenvía exactamente el mismo cuerpo)— y, sobre todo, por el
   número del albarán con su proveedor y su año. Las dos comprobaciones están en
   `_recepcion_que_ya_estaba`, y la de la clave está además forzada por un índice único en la base.

3. **El libro no se suma a la cesta.** Son dos vistas distintas de lo mismo y se contestan por
   separado (ver la cabecera del bloque del almacén en `servicios.py`). Sumarlas contaría cada litro
   dos veces: una por la factura y otra por la entrada.

Y una cuarta, que es la que hace que esto sirva en una inspección: **nada se borra**. Un movimiento
o un albarán se anulan con su motivo, y si lo que se anula es el tratamiento del que salía una
salida, esa salida deja de contar sin tocar el libro (`servicios.estado_de_los_origenes`).
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from .. import models, servicios, textos
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AnulacionEntrada,
    ArticuloEntrada,
    ArticuloSalida,
    EnlazarLaFacturaEntrada,
    LineaDeRecepcionSalida,
    LoteEntrada,
    LoteSalida,
    MovimientoEntrada,
    MovimientoSalida,
    RecepcionEntrada,
    RecepcionSalida,
    SalidaDeAlmacenEntrada,
)

router = APIRouter(prefix="/api/almacen", tags=["almacen"])


# --------------------------------------------------------------------------
# Cosas pequeñas que se repiten
# --------------------------------------------------------------------------


def _texto(valor: str | None, largo: int) -> str | None:
    """Un texto recortado, y vacío se queda en `None` («no lo sé»), nunca en «»."""
    return (valor or "").strip()[:largo] or None


def _la_clave(datos) -> str | None:
    """La clave de reenvío de la petición, con el nombre que la mande.

    Es el «identificador único de petición» del contrato (§2) y, en el campo, la única defensa que
    hay contra un envío repetido: la cola del móvil reintenta el mismo cuerpo sin preguntar. Se
    acepta con los dos nombres —`clave_de_reenvio` y `id_local` (el del móvil)— porque son la misma
    cosa, y perder la protección por un nombre distinto sería el peor motivo para perderla.
    """
    clave = (datos.clave_de_reenvio or datos.id_local or "").strip()
    return clave[:120] or None


def _con_nombres(db, recepcion: models.Recepcion) -> RecepcionSalida:
    """La recepción con los nombres de sus artículos y de sus lotes ya resueltos.

    Como en las facturas: la pantalla no tiene que cruzar listas ni puede enseñar el nombre de un
    artículo que ya no es.
    """
    lineas: list[LineaDeRecepcionSalida] = []
    for linea in sorted(recepcion.lineas, key=lambda fila: fila.id):
        articulo = db.get(models.Articulo, linea.articulo_id)
        lote = db.get(models.Lote, linea.lote_id)
        lineas.append(
            LineaDeRecepcionSalida(
                id=linea.id,
                articulo_id=linea.articulo_id,
                lote_id=linea.lote_id,
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                unidad=linea.unidad,
                linea_factura_id=linea.linea_factura_id,
                articulo=articulo.nombre if articulo else None,
                numero_lote=lote.numero_lote if lote else None,
                fecha_caducidad=lote.fecha_caducidad if lote else None,
            )
        )
    return RecepcionSalida(
        id=recepcion.id,
        fecha=recepcion.fecha,
        proveedor=recepcion.proveedor,
        proveedor_nif=recepcion.proveedor_nif,
        numero_albaran=recepcion.numero_albaran,
        factura_id=recepcion.factura_id,
        notas=recepcion.notas,
        anulada=recepcion.anulada,
        motivo_anulacion=recepcion.motivo_anulacion,
        creada_en=recepcion.creada_en,
        lineas=lineas,
        entradas=_cuantas_entradas(db, recepcion),
    )


def _cuantas_entradas(db, recepcion: models.Recepcion) -> int:
    """Cuántas entradas del libro ha metido este albarán. Cero cuando está anulado.

    Es el número que hay que enseñar para contestar la pregunta de verdad: «¿esto ha entrado en el
    almacén o solo está apuntado?». Una recepción anulada tiene cero, y así se ve.
    """
    if recepcion.anulada:
        return 0
    return len(
        list(
            db.scalars(
                select(models.MovimientoDeExistencias).where(
                    models.MovimientoDeExistencias.explotacion_id == recepcion.explotacion_id,
                    models.MovimientoDeExistencias.origen_tipo == "recepcion",
                    models.MovimientoDeExistencias.origen_id == recepcion.id,
                    models.MovimientoDeExistencias.anulado.is_(False),
                )
            )
        )
    )


def _la_respuesta_de_una_que_ya_estaba(
    db, recepcion: models.Recepcion, *, como_se_reconocio: str
) -> dict:
    """Lo que se contesta cuando el albarán ya estaba apuntado: **el mismo, y sin tocar nada**.

    Devuelve el que había (con sus líneas y sus entradas) para que quien lo mandó tenga el mismo
    resultado que la primera vez, y lo dice en palabras: «ya estaba, no se ha contado dos veces». La
    fecha de antes va dentro del aviso, porque si la que llega ahora es otra, uno de los dos apuntes
    tiene la fecha mal y hay que mirarlo.

    El que se devuelve **nunca está anulado**: los dos caminos de `_recepcion_que_ya_estaba` buscan
    solo entre los que no lo están, y eso es lo que permite volver a apuntar un albarán que se anuló
    por estar mal.
    """
    avisos = []
    de_antes = recepcion.fecha.strftime("%d/%m/%Y") if recepcion.fecha else None
    avisos.append(
        textos.MENSAJES["AL6_ese_albaran_ya_estaba"].format(
            fecha=f" (el {de_antes})" if de_antes else ""
        )
    )
    return {
        "recepcion": _con_nombres(db, recepcion),
        "ya_estaba": True,
        "como_se_reconocio": como_se_reconocio,
        "avisos": avisos,
        "textos": textos.ALMACEN,
    }


def _recepcion_que_ya_estaba(
    db, explotacion, *, clave: str | None, datos: RecepcionEntrada
) -> tuple[models.Recepcion | None, str]:
    """El albarán que ya está apuntado, si lo está, y cómo se ha reconocido.

    Las dos formas, por este orden, y **las dos solo miran albaranes que no estén anulados**: un
    albarán anulado es lo que el agricultor ha dicho que estaba mal, así que volver a apuntarlo tiene
    que ser posible —si no, no habría forma de arreglarlo—.

      1. **La clave de reenvío.** Si esta misma petición ya se atendió, se devuelve la misma
         recepción. Es lo que protege del reenvío del móvil cuando el agricultor apunta sin cobertura.
      2. **El número del albarán con su proveedor.** Y el año, cuando los dos papeles lo dicen: dos
         albaranes con el mismo número pero de años distintos son dos papeles distintos, porque las
         numeraciones se reinician. Si a alguno le falta la fecha, se dan por el mismo: en la duda,
         **no duplicar** es lo que protege el almacén, y deshacerlo es tan fácil como anular.
    """
    if clave:
        ya = db.scalar(
            select(models.Recepcion).where(
                models.Recepcion.explotacion_id == explotacion.id,
                models.Recepcion.clave_de_reenvio == clave,
                models.Recepcion.anulada.is_(False),
            )
        )
        if ya is not None:
            return ya, "clave_de_reenvio"

    identidad = servicios.clave_de_un_albaran(
        datos.proveedor, datos.proveedor_nif, datos.numero_albaran
    )
    if identidad is None:
        # Sin número o sin proveedor no se puede reconocer nada, y eso **no** es «no estaba»: quien
        # llama tiene que decirlo en la pantalla (ver `AL5_no_se_pudo_comprobar_si_ya_estaba`).
        return None, ""

    candidatas = db.scalars(
        select(models.Recepcion).where(
            models.Recepcion.explotacion_id == explotacion.id,
            models.Recepcion.anulada.is_(False),
        )
    )
    for candidata in candidatas:
        if not servicios.el_mismo_albaran(
            proveedor=candidata.proveedor,
            proveedor_nif=candidata.proveedor_nif,
            numero_albaran=candidata.numero_albaran,
            otro_proveedor=datos.proveedor,
            otro_proveedor_nif=datos.proveedor_nif,
            otro_numero_albaran=datos.numero_albaran,
        ):
            continue
        if (
            candidata.fecha is not None
            and datos.fecha is not None
            and candidata.fecha.year != datos.fecha.year
        ):
            continue
        return candidata, "numero_de_albaran"
    return None, ""


def _completar_la_unidad(articulo: models.Articulo, del_papel: str | None, avisos: list[str]) -> None:
    """La unidad del artículo: se aprende del papel si no se sabía, y **no se pisa** si ya estaba.

    Y si lo que dice el papel es de otra familia —el artículo se cuenta en litros y esta línea viene
    en kilos—, no se cambia nada y se avisa: un litro y un kilo no son lo mismo, y elegir uno de los
    dos por nuestra cuenta estropearía la cuenta del almacén para siempre.
    """
    nueva = (del_papel or "").strip()
    if not nueva:
        return
    if not (articulo.unidad or "").strip():
        articulo.unidad = nueva[:10]
        return
    if not servicios.se_pueden_sumar(articulo.unidad, nueva):
        avisos.append(
            textos.MENSAJES["AL3_la_unidad_no_cuadra"].format(
                unidad=articulo.unidad, otra=nueva
            )
        )


def _el_articulo_de_la_linea(
    db, explotacion, linea, avisos: list[str]
) -> models.Articulo:
    """El artículo de una línea del albarán: el que ya hay o uno nuevo, sin inventarse nada.

    El orden importa y es el de la certeza: lo que el agricultor ha elegido a mano manda; después,
    la ficha del producto o del abono del programa —que es lo que hace que el almacén hable de lo
    mismo que el resto del cuaderno—; y si no hay nada de eso, el nombre que pone el papel.

    Cuando el artículo sale de una ficha, **la categoría y la unidad salen de la ficha**: un producto
    de la cesta tiene su unidad de compra (litros, kilos…) y un abono no dice su unidad en ninguna
    parte, así que el abono se queda sin unidad hasta que un papel lo diga. Inventarse «kg» para un
    abono líquido sería un error que después no se puede deshacer.
    """
    if linea.articulo_id is not None:
        articulo = obtener_de_la_explotacion(
            db, models.Articulo, linea.articulo_id, explotacion.id
        )
        _completar_la_unidad(articulo, linea.unidad or linea.unidad_de_la_cantidad, avisos)
        return articulo

    if linea.producto_id is not None:
        producto = obtener_de_la_explotacion(
            db, models.ProductoFitosanitario, linea.producto_id, explotacion.id
        )
        articulo = db.scalar(
            select(models.Articulo).where(
                models.Articulo.explotacion_id == explotacion.id,
                models.Articulo.producto_id == producto.id,
            )
        )
        if articulo is None:
            articulo = models.Articulo(
                explotacion_id=explotacion.id,
                nombre=producto.nombre_comercial,
                categoria="fitosanitario",
                unidad=(producto.unidad_compra or "").strip()[:10] or None,
                producto_id=producto.id,
            )
            db.add(articulo)
            db.flush()
        _completar_la_unidad(articulo, linea.unidad or linea.unidad_de_la_cantidad, avisos)
        return articulo

    if linea.fertilizante_id is not None:
        abono = obtener_de_la_explotacion(
            db, models.Fertilizante, linea.fertilizante_id, explotacion.id
        )
        articulo = db.scalar(
            select(models.Articulo).where(
                models.Articulo.explotacion_id == explotacion.id,
                models.Articulo.fertilizante_id == abono.id,
            )
        )
        if articulo is None:
            articulo = models.Articulo(
                explotacion_id=explotacion.id,
                nombre=abono.nombre,
                categoria="abono",
                # Un abono no tiene unidad en su ficha: no se pone ninguna.
                unidad=None,
                fertilizante_id=abono.id,
            )
            db.add(articulo)
            db.flush()
        _completar_la_unidad(articulo, linea.unidad or linea.unidad_de_la_cantidad, avisos)
        return articulo

    nombre = (linea.nombre or "").strip()
    if nombre:
        for candidato in db.scalars(
            select(models.Articulo).where(models.Articulo.explotacion_id == explotacion.id)
        ):
            if servicios.normaliza_para_comparar(candidato.nombre) == servicios.normaliza_para_comparar(
                nombre
            ):
                _completar_la_unidad(
                    candidato, linea.unidad or linea.unidad_de_la_cantidad, avisos
                )
                return candidato
        articulo = models.Articulo(
            explotacion_id=explotacion.id,
            nombre=nombre[:200],
            categoria=servicios.categoria_valida(linea.categoria),
            unidad=(linea.unidad or linea.unidad_de_la_cantidad or "").strip()[:10] or None,
        )
        db.add(articulo)
        db.flush()
        return articulo

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=textos.mensaje("AL2_la_linea_no_dice_que_es"),
    )


def _la_factura_comprobada(db, explotacion, factura_id: int | None):
    """La factura, si es de esta finca y no está ya enganchada a otro albarán **vivo**."""
    if factura_id is None:
        return None
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    # **Solo cuentan los albaranes vivos** (03/10/2026). Sin este filtro, un albarán anulado seguía
    # «teniendo» la factura, y el agricultor que anulaba un albarán por haberse equivocado se
    # encontraba con que ya no podía enganchar esa factura a ninguno: el programa le decía «esa
    # factura ya está enganchada a otro albarán» señalando a uno anulado, que es un albarán que ya no
    # dice nada. Un documento anulado no puede seguir reteniendo papeles.
    otra = db.scalar(
        select(models.Recepcion).where(
            models.Recepcion.explotacion_id == explotacion.id,
            models.Recepcion.factura_id == factura.id,
            models.Recepcion.anulada.is_(False),
        )
    )
    if otra is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("AL7_esa_factura_ya_esta_en_otro_albaran"),
        )
    return factura


# --------------------------------------------------------------------------
# El artículo y el lote
# --------------------------------------------------------------------------


@router.post("/articulos", response_model=ArticuloSalida, status_code=status.HTTP_201_CREATED)
def crear_articulo(
    datos: ArticuloEntrada, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> models.Articulo:
    """Dar de alta lo que se guarda en el almacén.

    No es obligatorio pasar por aquí: una línea de albarán da de alta el artículo que no exista (ver
    `_el_articulo_de_la_linea`). Esta puerta existe para lo que no viene en ningún albarán: la
    semilla que se guarda de un año para otro, un producto que ya estaba en la nave.
    """
    producto = None
    if datos.producto_id is not None:
        producto = obtener_de_la_explotacion(
            db, models.ProductoFitosanitario, datos.producto_id, explotacion.id
        )
    abono = None
    if datos.fertilizante_id is not None:
        abono = obtener_de_la_explotacion(
            db, models.Fertilizante, datos.fertilizante_id, explotacion.id
        )
    articulo = models.Articulo(
        explotacion_id=explotacion.id,
        nombre=datos.nombre.strip()[:200],
        categoria=servicios.categoria_valida(datos.categoria),
        unidad=(datos.unidad or "").strip()[:10] or None,
        producto_id=producto.id if producto else None,
        fertilizante_id=abono.id if abono else None,
    )
    db.add(articulo)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="articulo",
            entidad_id=articulo.id,
            accion="crear",
            datos={"nombre": articulo.nombre, "categoria": articulo.categoria},
        )
    )
    db.commit()
    return articulo


@router.get("/articulos", response_model=list[ArticuloSalida])
def listar_articulos(explotacion: ExplotacionActual, db: Db) -> list[models.Articulo]:
    return list(
        db.scalars(
            select(models.Articulo)
            .where(models.Articulo.explotacion_id == explotacion.id)
            .order_by(models.Articulo.nombre)
        )
    )


@router.get("/lotes", response_model=list[LoteSalida])
def listar_lotes(
    explotacion: ExplotacionActual, db: Db, articulo_id: int | None = None
) -> list[models.Lote]:
    """Los lotes de un artículo, con su número y su caducidad. Vacío es «no consta», no «no caduca»."""
    consulta = select(models.Lote).where(models.Lote.explotacion_id == explotacion.id)
    if articulo_id is not None:
        obtener_de_la_explotacion(db, models.Articulo, articulo_id, explotacion.id)
        consulta = consulta.where(models.Lote.articulo_id == articulo_id)
    return list(
        db.scalars(
            consulta.order_by(models.Lote.fecha_caducidad.is_(None), models.Lote.fecha_caducidad)
        )
    )


@router.post("/lotes", response_model=LoteSalida, status_code=status.HTTP_201_CREATED)
def crear_lote(
    datos: LoteEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    respuesta: Response,
) -> models.Lote:
    """Abrir un lote sin pasar por un albarán.

    Hace falta de verdad: hay producto que ya estaba en la nave cuando se empezó a usar el programa, y
    una entrada sin compra detrás necesita su lote para poder apuntarse.

    Si ese número ya existe para ese artículo, **se devuelve el que hay** (con código 200, que es la
    verdad: no se ha creado nada): el mismo envase no se duplica porque se apunte dos veces, y su
    caducidad no se cambia por lo que diga el segundo papel.
    """
    articulo = obtener_de_la_explotacion(db, models.Articulo, datos.articulo_id, explotacion.id)
    ya = servicios.el_lote_de_un_numero(
        db,
        explotacion_id=explotacion.id,
        articulo_id=articulo.id,
        numero_lote=datos.numero_lote,
    )
    if ya is not None:
        respuesta.status_code = status.HTTP_200_OK
        return ya
    lote = servicios.lote_para_apuntar(
        db,
        explotacion_id=explotacion.id,
        articulo=articulo,
        numero_lote=datos.numero_lote,
        fecha_caducidad=datos.fecha_caducidad,
        presentacion=datos.presentacion,
        contenido_por_envase=datos.contenido_por_envase,
        ubicacion=datos.ubicacion,
    )
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="lote",
            entidad_id=lote.id,
            accion="crear",
            datos={
                "articulo": articulo.nombre,
                "numero_lote": lote.numero_lote,
                "fecha_caducidad": (
                    lote.fecha_caducidad.isoformat() if lote.fecha_caducidad else None
                ),
            },
        )
    )
    db.commit()
    return lote


# --------------------------------------------------------------------------
# La recepción del albarán: lo que mete mercancía en el almacén
# --------------------------------------------------------------------------


@router.post("/recepciones", status_code=status.HTTP_201_CREATED)
def crear_recepcion(
    datos: RecepcionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    respuesta: Response,
) -> dict:
    """Apuntar un albarán: sus líneas, sus lotes y las entradas del libro. **Una sola vez.**

    Es el único sitio del programa que mete mercancía en el almacén, y por eso es donde están las
    tres protecciones del encargo:

      · **Reenviar la petición no crea otro albarán.** Si la clave de reenvío ya se atendió, o si ya
        hay un albarán con ese número de ese proveedor, se devuelve **el que había**, con código 200
        en vez de 201, y sin tocar ni una línea ni un litro.
      · **Un albarán sin número no se puede reconocer**, así que se apunta igual —lo que llegó, llegó—
        y la respuesta lo dice (`AL5_no_se_pudo_comprobar_si_ya_estaba`). No saber no es un «sí» ni un
        «no», y se declara.
      · **Todo va en una sola transacción.** Si una línea falla, no queda medio albarán apuntado con
        medio almacén metido (contrato §2: «un fallo revierte todo»).

    Lo que **no** hace: no apunta precios ni da nada por pagado. Eso es la factura, que es otro
    documento y otro día, y que no vuelve a meter la mercancía cuando llega (A15).
    """
    if not datos.lineas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL1_una_recepcion_sin_lineas"),
        )

    clave = _la_clave(datos)
    ya, como = _recepcion_que_ya_estaba(db, explotacion, clave=clave, datos=datos)
    if ya is not None:
        respuesta.status_code = status.HTTP_200_OK
        return _la_respuesta_de_una_que_ya_estaba(db, ya, como_se_reconocio=como)

    factura = _la_factura_comprobada(db, explotacion, datos.factura_id)
    avisos: list[str] = []
    if servicios.clave_de_un_albaran(
        datos.proveedor, datos.proveedor_nif, datos.numero_albaran
    ) is None:
        avisos.append(textos.MENSAJES["AL5_no_se_pudo_comprobar_si_ya_estaba"])

    recepcion = models.Recepcion(
        explotacion_id=explotacion.id,
        fecha=datos.fecha,
        proveedor=_texto(datos.proveedor, 200),
        proveedor_nif=_texto(datos.proveedor_nif, 20),
        numero_albaran=_texto(datos.numero_albaran, 80),
        factura_id=factura.id if factura else None,
        clave_de_reenvio=clave,
        notas=_texto(datos.notas, 2000),
    )
    db.add(recepcion)
    db.flush()

    for linea in datos.lineas:
        if linea.linea_factura_id is not None:
            linea_de_la_factura = obtener_de_la_explotacion(
                db, models.LineaDeFactura, linea.linea_factura_id, explotacion.id
            )
            if factura is not None and linea_de_la_factura.factura_id != factura.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=textos.mensaje("AL23_esa_linea_no_es_de_esa_factura"),
                )
        articulo = _el_articulo_de_la_linea(db, explotacion, linea, avisos)
        lote = servicios.lote_para_apuntar(
            db,
            explotacion_id=explotacion.id,
            articulo=articulo,
            numero_lote=linea.numero_lote,
            fecha_caducidad=linea.fecha_caducidad,
            presentacion=linea.presentacion,
            contenido_por_envase=linea.contenido_por_envase,
            ubicacion=linea.ubicacion,
        )
        if (
            lote.fecha_caducidad is not None
            and linea.fecha_caducidad is not None
            and lote.fecha_caducidad != linea.fecha_caducidad
        ):
            avisos.append(
                textos.MENSAJES["AL4_la_caducidad_no_cuadra"].format(
                    antes=lote.fecha_caducidad.strftime("%d/%m/%Y"),
                    ahora=linea.fecha_caducidad.strftime("%d/%m/%Y"),
                )
            )
        # La unidad del movimiento: **la que dice el albarán** (en cualquiera de los dos nombres con
        # los que la puede mandar la pantalla) y, si el albarán no la dice, la del artículo, que es la
        # que el agricultor ya había dicho. Si tampoco la hay, el movimiento se queda sin unidad y el
        # almacén dirá que no puede hacer la cuenta en vez de suponer litros: lo que dice el papel
        # manda sobre la ficha, porque la ficha es lo que sabíamos antes de ver el envase.
        unidad = (
            (linea.unidad_de_la_cantidad or linea.unidad or "").strip()[:10] or articulo.unidad
        )
        db.add(
            models.LineaDeRecepcion(
                explotacion_id=explotacion.id,
                recepcion_id=recepcion.id,
                articulo_id=articulo.id,
                lote_id=lote.id,
                descripcion=_texto(linea.descripcion, 200),
                cantidad=linea.cantidad,
                unidad=unidad,
                linea_factura_id=linea.linea_factura_id,
            )
        )
        db.add(
            models.MovimientoDeExistencias(
                explotacion_id=explotacion.id,
                articulo_id=articulo.id,
                lote_id=lote.id,
                tipo="entrada",
                fecha=recepcion.fecha,
                cantidad=linea.cantidad,
                unidad=unidad,
                origen_tipo="recepcion",
                origen_id=recepcion.id,
                motivo=None,
                usuario_id=usuario.id,
            )
        )

    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="recepcion",
            entidad_id=recepcion.id,
            accion="crear",
            datos={
                "proveedor": recepcion.proveedor,
                "numero_albaran": recepcion.numero_albaran,
                "fecha": recepcion.fecha.isoformat() if recepcion.fecha else None,
                "lineas": len(datos.lineas),
                "clave_de_reenvio": clave,
            },
        )
    )
    db.commit()
    db.refresh(recepcion)

    return {
        "recepcion": _con_nombres(db, recepcion),
        "ya_estaba": False,
        "como_se_reconocio": "",
        "avisos": avisos,
        "textos": textos.ALMACEN,
    }


@router.get("/recepciones", response_model=list[RecepcionSalida])
def listar_recepciones(
    explotacion: ExplotacionActual, db: Db, desde: dt.date | None = None, hasta: dt.date | None = None
) -> list[RecepcionSalida]:
    """Lo que ha llegado, lo último primero, y **siempre lo de esta finca y de nadie más**.

    Se busca por fechas y no por campaña: el almacén no cuelga del año (el porqué, en
    `models.Recepcion`). Un albarán **sin fecha** no entra en un rango: no se sabe si estaba dentro.
    """
    consulta = select(models.Recepcion).where(
        models.Recepcion.explotacion_id == explotacion.id
    )
    if desde is not None or hasta is not None:
        consulta = consulta.where(models.Recepcion.fecha.is_not(None))
    if desde is not None:
        consulta = consulta.where(models.Recepcion.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(models.Recepcion.fecha <= hasta)
    recepciones = db.scalars(
        consulta.order_by(
            models.Recepcion.fecha.is_(None),
            models.Recepcion.fecha.desc(),
            models.Recepcion.id.desc(),
        )
    )
    return [_con_nombres(db, recepcion) for recepcion in recepciones]


@router.get("/recepciones/{recepcion_id}", response_model=RecepcionSalida)
def ver_recepcion(
    recepcion_id: int, explotacion: ExplotacionActual, db: Db
) -> RecepcionSalida:
    recepcion = obtener_de_la_explotacion(
        db, models.Recepcion, recepcion_id, explotacion.id
    )
    return _con_nombres(db, recepcion)


@router.post("/recepciones/{recepcion_id}/anular", response_model=RecepcionSalida)
def anular_recepcion(
    recepcion_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> RecepcionSalida:
    """Anular un albarán que estaba mal.

    **No se borra y no se le quitan las líneas.** Queda con su motivo escrito, y sus entradas dejan de
    contar en el almacén (`servicios.estado_de_los_origenes`), así que el libro sigue diciendo lo que
    se apuntó aquel día y a la vez la cuenta es la de verdad.

    Para eso sirve: es el camino para arreglar un albarán mal apuntado —se anula y se apunta el bueno—
    sin que las dos versiones cuenten a la vez. Y por eso mismo **no se puede anular dos veces**: el
    primer motivo es el que vale, y pisarlo sería perder lo que dijo quien lo anuló.
    """
    recepcion = obtener_de_la_explotacion(
        db, models.Recepcion, recepcion_id, explotacion.id
    )
    if recepcion.anulada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("AL20_ya_estaba_anulado"),
        )
    recepcion.anulada = True
    recepcion.motivo_anulacion = datos.motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="recepcion",
            entidad_id=recepcion.id,
            accion="anular",
            datos={"motivo": datos.motivo, "num_albaran": recepcion.numero_albaran},
        )
    )
    db.commit()
    return _con_nombres(db, recepcion)


@router.post("/recepciones/{recepcion_id}/factura", response_model=RecepcionSalida)
def enganchar_la_factura(
    recepcion_id: int,
    datos: EnlazarLaFacturaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> RecepcionSalida:
    """Decir de qué factura es un albarán que ya está apuntado (caso A15).

    **Esto no mete nada en el almacén.** La mercancía entró una vez, el día que llegó el albarán; la
    factura solo dice de dónde salió y cuánto costó. Es justo el caso que el contrato pone como
    prueba: «factura llega después de albarán recibido → una entrada de almacén y vínculo entre ambos
    documentos». Después de engancharla, el lote sigue teniendo exactamente los mismos litros.

    Y se puede afinar línea a línea (`lineas`), para el caso en que los dos papeles no cuadren del
    todo. Eso tampoco mueve cantidades: solo dice qué línea del albarán es qué línea de la factura.
    """
    recepcion = obtener_de_la_explotacion(
        db, models.Recepcion, recepcion_id, explotacion.id
    )
    factura = _la_factura_comprobada(db, explotacion, datos.factura_id)
    lineas_de_la_factura = {linea.id: linea for linea in factura.lineas}
    antes = recepcion.factura_id

    for enlace in datos.lineas:
        linea = obtener_de_la_explotacion(
            db, models.LineaDeRecepcion, enlace.linea_de_recepcion_id, explotacion.id
        )
        if linea.recepcion_id != recepcion.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
            )
        if enlace.linea_de_factura_id not in lineas_de_la_factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
            )
        linea.linea_factura_id = enlace.linea_de_factura_id

    recepcion.factura_id = factura.id
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="recepcion",
            entidad_id=recepcion.id,
            accion="enlazar_la_factura",
            datos={
                "num_albaran": recepcion.numero_albaran,
                "factura_id": factura.id,
                "numero_factura": factura.numero_factura,
                "factura_de_antes": antes,
                "lineas_enlazadas": len(datos.lineas),
            },
        )
    )
    db.commit()
    return _con_nombres(db, recepcion)


@router.get("/facturas/{factura_id}/posibles-recepciones")
def posibles_recepciones_de_una_factura(
    factura_id: int, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Qué albaranes podrían ser los de esta factura. **Es una propuesta, no un hecho.**

    Se propone por proveedor y por fechas cercanas, y con las líneas casadas por producto o abono: es
    lo que hace falta para no tener que buscar el albarán a mano entre todos. Enseñar la propuesta
    **no engancha nada**: el agricultor dice cuál es y se engancha por su puerta. Es la misma regla
    que en el dictado y en la lectura de facturas: una máquina propone, una persona confirma.
    """
    factura = obtener_de_la_explotacion(db, models.Factura, factura_id, explotacion.id)
    # Los albaranes vivos que ya tienen esta factura. Los anulados no cuentan: un albarán anulado no
    # «tiene» nada (ver `_la_factura_comprobada`).
    enganchadas = list(
        db.scalars(
            select(models.Recepcion).where(
                models.Recepcion.explotacion_id == explotacion.id,
                models.Recepcion.factura_id == factura.id,
                models.Recepcion.anulada.is_(False),
            )
        )
    )
    sin_factura = list(
        db.scalars(
            select(models.Recepcion).where(
                models.Recepcion.explotacion_id == explotacion.id,
                models.Recepcion.factura_id.is_(None),
                models.Recepcion.anulada.is_(False),
            )
        )
    )
    proveedor = servicios.normaliza_para_comparar(factura.proveedor_nif or factura.proveedor)
    propuestas = []
    for recepcion in sin_factura:
        suyo = servicios.normaliza_para_comparar(
            recepcion.proveedor_nif or recepcion.proveedor
        )
        if proveedor and suyo and proveedor != suyo:
            continue
        propuestas.append(
            {
                "recepcion_id": recepcion.id,
                "numero_albaran": recepcion.numero_albaran,
                "fecha": recepcion.fecha.isoformat() if recepcion.fecha else None,
                "proveedor": recepcion.proveedor,
                "lineas_casadas": _lineas_casadas(db, recepcion, factura),
                "como_se_propone": (
                    "por el proveedor" if proveedor and suyo else "no consta el proveedor en alguno"
                ),
            }
        )
    return {
        "factura_id": factura.id,
        "ya_enganchadas": [
            {"recepcion_id": recepcion.id, "numero_albaran": recepcion.numero_albaran}
            for recepcion in enganchadas
        ],
        "propuestas": propuestas,
        "textos": textos.ALMACEN,
    }


def _lineas_casadas(db, recepcion: models.Recepcion, factura: models.Factura) -> list[dict]:
    """Qué línea del albarán parece la misma que qué línea de la factura, y por qué.

    Se casa por el **producto o el abono**, que es lo que no admite duda: si la línea del albarán es
    el Glifosato y hay una línea de la factura del mismo producto, son la misma cosa. Las que no
    casan se quedan fuera, y se dice por qué, en vez de proponer la «más parecida» por el nombre, que
    es como se cuela un dato de otro producto.
    """
    articulos = {
        articulo.id: articulo
        for articulo in db.scalars(
            select(models.Articulo).where(
                models.Articulo.explotacion_id == recepcion.explotacion_id
            )
        )
    }
    casadas: list[dict] = []
    for linea in sorted(recepcion.lineas, key=lambda fila: fila.id):
        articulo = articulos.get(linea.articulo_id)
        if articulo is None:
            continue
        for de_la_factura in factura.lineas:
            if articulo.producto_id is not None and de_la_factura.producto_id == articulo.producto_id:
                casadas.append(
                    {
                        "linea_de_recepcion_id": linea.id,
                        "linea_de_factura_id": de_la_factura.id,
                        "como": "es el mismo producto",
                    }
                )
                break
            if (
                articulo.fertilizante_id is not None
                and de_la_factura.fertilizante_id == articulo.fertilizante_id
            ):
                casadas.append(
                    {
                        "linea_de_recepcion_id": linea.id,
                        "linea_de_factura_id": de_la_factura.id,
                        "como": "es el mismo abono",
                    }
                )
                break
    return casadas


# --------------------------------------------------------------------------
# El libro: lo que entra, lo que sale, lo que se pierde y lo que se cuenta distinto
# --------------------------------------------------------------------------


@router.post("/movimientos", status_code=status.HTTP_201_CREATED)
def apuntar_un_movimiento(
    datos: MovimientoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    respuesta: Response,
) -> dict:
    """Apuntar a mano lo que pasó: una entrada sin papel, una merma o un ajuste.

    **Por qué una salida no se apunta por aquí.** Porque una salida de verdad sale de un trabajo: si
    se pudiera restar producto sin decir de dónde, el almacén dejaría de poder contestar la única
    pregunta que importa cuando hay un problema con un lote —«¿esto dónde se fue?»—. Las salidas
    tienen su puerta (`POST /api/almacen/salidas`) y exigen el apunte del que salen.

    **El motivo no es un adorno.** En una merma, en un ajuste y en una entrada que no viene de ningún
    papel, no hay ningún documento que explique el movimiento: lo único que lo explica es lo que
    escriba el agricultor. Sin eso, dentro de dos años nadie sabe por qué faltan diez litros, y un
    cuaderno que no se puede explicar no sirve en una inspección.

    Y cuando el movimiento viene de una factura (una compra sin albarán en la mano), se dice
    (`origen_tipo="factura"`): así se sabe de dónde salió y queda el vínculo con el papel.
    """
    tipo = (datos.tipo or "").strip().lower()
    if tipo not in servicios.TIPOS_DE_MOVIMIENTO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL8_tipo_de_movimiento_desconocido"),
        )
    if tipo == "salida":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL9_una_salida_necesita_su_apunte"),
        )
    if tipo == "ajuste" and (datos.cantidad is None or datos.cantidad == 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL11_un_ajuste_necesita_la_diferencia"),
        )
    if tipo == "merma" and (datos.cantidad is None or datos.cantidad <= 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL12_una_merma_necesita_la_cantidad"),
        )
    if datos.cantidad is not None and not (datos.unidad or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL13_falta_la_unidad"),
        )

    origen_tipo = (datos.origen_tipo or "manual").strip().lower()
    if origen_tipo not in servicios.ORIGENES_DE_UN_MOVIMIENTO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL8_tipo_de_movimiento_desconocido"),
        )
    if origen_tipo in ("recepcion", "tratamiento", "fertilizacion"):
        # Un movimiento que sale de un albarán o de un apunte tiene su puerta, y ahí es donde el
        # programa pone la referencia. Apuntarlo a mano sería perder de dónde viene.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL22_eso_tiene_su_puerta"),
        )

    factura = None
    if origen_tipo == "factura":
        if datos.origen_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=textos.mensaje("AL21_la_factura_no_esta_dicha"),
            )
        factura = obtener_de_la_explotacion(
            db, models.Factura, datos.origen_id, explotacion.id
        )
    else:
        origen_tipo = "manual"

    # Sin un papel detrás, el motivo es obligatorio: ver la decisión de arriba. Con una factura
    # delante, el papel ya lo explica, así que se puede dejar en blanco.
    motivo = (datos.motivo or "").strip()[:500]
    if tipo in ("merma", "ajuste") and not motivo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL10_falta_el_motivo"),
        )
    if tipo == "entrada" and factura is None and not motivo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL10_falta_el_motivo"),
        )

    if datos.linea_factura_id is not None:
        linea_de_la_factura = obtener_de_la_explotacion(
            db, models.LineaDeFactura, datos.linea_factura_id, explotacion.id
        )
        if factura is not None and linea_de_la_factura.factura_id != factura.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=textos.mensaje("AL23_esa_linea_no_es_de_esa_factura"),
            )

    lote, articulo = _el_lote_del_movimiento(db, explotacion, datos)

    # El reenvío: si esta misma petición ya se atendió, se devuelve el mismo movimiento. Se comprueba
    # aquí, y además la base tiene un índice único por clave y finca: dos peticiones a la vez tampoco
    # pueden crear dos, porque la segunda choca con la primera al guardar.
    clave = _la_clave(datos)
    if clave:
        repetido = db.scalar(
            select(models.MovimientoDeExistencias).where(
                models.MovimientoDeExistencias.explotacion_id == explotacion.id,
                models.MovimientoDeExistencias.clave_de_reenvio == clave,
            )
        )
        if repetido is not None:
            respuesta.status_code = status.HTTP_200_OK
            return {
                "movimiento": _un_movimiento(db, repetido),
                "ya_estaba": True,
                "avisos": [],
                "textos": textos.ALMACEN,
            }

    movimiento = models.MovimientoDeExistencias(
        explotacion_id=explotacion.id,
        articulo_id=articulo.id,
        lote_id=lote.id,
        tipo=tipo,
        fecha=datos.fecha,
        cantidad=datos.cantidad,
        unidad=(datos.unidad or "").strip()[:10] or None,
        origen_tipo=origen_tipo,
        origen_id=factura.id if factura else None,
        motivo=motivo or None,
        usuario_id=usuario.id,
        clave_de_reenvio=clave,
    )
    db.add(movimiento)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="movimiento_de_existencias",
            entidad_id=movimiento.id,
            accion="crear",
            datos={
                "tipo": tipo,
                "articulo": articulo.nombre,
                "numero_lote": lote.numero_lote,
                "cantidad": datos.cantidad,
                "unidad": movimiento.unidad,
                "motivo": motivo or None,
                "origen_tipo": origen_tipo,
            },
        )
    )
    db.commit()
    db.refresh(movimiento)
    return {
        "movimiento": _un_movimiento(db, movimiento),
        "ya_estaba": False,
        "avisos": [],
        "textos": textos.ALMACEN,
    }


def _el_lote_del_movimiento(
    db, explotacion, datos: MovimientoEntrada
) -> tuple[models.Lote, models.Articulo]:
    """El lote y el artículo de un movimiento a mano, comprobando que son de esta finca.

    El lote se puede decir de dos formas —por su identificador, o por el artículo y su número—, y la
    segunda hace falta de verdad: un lote que aparece por primera vez en una merma no tiene
    identificador todavía. Si se dice el identificador, se comprueba además que sea del artículo: un
    movimiento de un artículo en el lote de otro dejaría las dos cuentas mal.
    """
    if datos.lote_id is not None:
        lote = obtener_de_la_explotacion(db, models.Lote, datos.lote_id, explotacion.id)
        articulo = db.get(models.Articulo, lote.articulo_id)
        if datos.articulo_id is not None and datos.articulo_id != lote.articulo_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=textos.mensaje("AL14_ese_lote_no_es_de_ese_articulo"),
            )
        return lote, articulo

    if datos.articulo_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL2_la_linea_no_dice_que_es"),
        )
    articulo = obtener_de_la_explotacion(
        db, models.Articulo, datos.articulo_id, explotacion.id
    )
    lote = servicios.lote_para_apuntar(
        db,
        explotacion_id=explotacion.id,
        articulo=articulo,
        numero_lote=datos.numero_lote,
        fecha_caducidad=datos.fecha_caducidad,
        presentacion=datos.presentacion,
        contenido_por_envase=datos.contenido_por_envase,
        ubicacion=datos.ubicacion,
    )
    if not (articulo.unidad or "").strip() and (datos.unidad or "").strip():
        articulo.unidad = datos.unidad.strip()[:10]
    return lote, articulo


def _un_movimiento(db, movimiento: models.MovimientoDeExistencias) -> MovimientoSalida:
    """Un movimiento suelto, tal y como se devuelve al apuntarlo o al anularlo.

    Se lee por el mismo camino que el listado (`servicios.un_movimiento_del_almacen`): lo que se
    contesta al apuntar algo tiene que ser lo mismo que saldrá después al consultarlo, «cuenta o no
    cuenta» incluido.
    """
    fila = servicios.un_movimiento_del_almacen(
        db, explotacion_id=movimiento.explotacion_id, movimiento_id=movimiento.id
    )
    if fila is not None:
        return MovimientoSalida(**fila)
    # Si no apareciera (no puede pasar: se acaba de escribir), se devuelve lo que se sabe del objeto,
    # sin inventarse el nombre del artículo ni el número del lote.
    return MovimientoSalida(
        id=movimiento.id,
        articulo_id=movimiento.articulo_id,
        lote_id=movimiento.lote_id,
        tipo=movimiento.tipo,
        fecha=movimiento.fecha,
        cantidad=movimiento.cantidad,
        unidad=movimiento.unidad,
        origen_tipo=movimiento.origen_tipo,
        origen_id=movimiento.origen_id,
        motivo=movimiento.motivo,
        usuario_id=movimiento.usuario_id,
        anulado=movimiento.anulado,
        motivo_anulacion=movimiento.motivo_anulacion,
        creado_en=movimiento.creado_en,
        cuenta=not movimiento.anulado,
        no_cuenta_porque=None,
    )


@router.get("/movimientos", response_model=list[MovimientoSalida])
def listar_movimientos(
    explotacion: ExplotacionActual,
    db: Db,
    articulo_id: int | None = None,
    lote_id: int | None = None,
    tipo: str | None = None,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
    solo_los_que_cuentan: bool = False,
) -> list[MovimientoSalida]:
    """El libro de movimientos: entradas, salidas, mermas y ajustes, lo último primero.

    Va **siempre filtrado por la finca** (`ExplotacionActual`), como todo en esta API. Cada fila dice
    si cuenta o no y por qué, porque un movimiento anulado, o cuyo apunte está anulado, sigue estando
    en el libro —nada se borra— pero no entra en la cuenta, y eso hay que poder verlo.

    Se busca por fechas: el libro no cuelga del año (ver `models.MovimientoDeExistencias`).
    """
    if articulo_id is not None:
        obtener_de_la_explotacion(db, models.Articulo, articulo_id, explotacion.id)
    if lote_id is not None:
        obtener_de_la_explotacion(db, models.Lote, lote_id, explotacion.id)
    filas = servicios.movimientos_del_almacen(
        db,
        explotacion_id=explotacion.id,
        articulo_id=articulo_id,
        lote_id=lote_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
        solo_los_que_cuentan=solo_los_que_cuentan,
    )
    return [MovimientoSalida(**fila) for fila in filas]


@router.post("/movimientos/{movimiento_id}/anular", response_model=MovimientoSalida)
def anular_movimiento(
    movimiento_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> MovimientoSalida:
    """Anular un movimiento del libro, con su motivo. Nada se borra.

    Es lo que se hace cuando el papel estaba mal: el movimiento se queda tachado, con lo que dijo
    quien lo anuló, y deja de contar. Y no se puede anular dos veces, para que el primer motivo —el
    que escribió quien se dio cuenta— no se pierda.

    **Lo que salió de un albarán no se anula aquí**: se anula el albarán, que es lo que de verdad
    pasó, y con él dejan de contar todas sus entradas de una vez. Anular una sola línea dejaría el
    albarán diciendo que metió mercancía que el almacén ya no cuenta.
    """
    movimiento = obtener_de_la_explotacion(
        db, models.MovimientoDeExistencias, movimiento_id, explotacion.id
    )
    if movimiento.origen_tipo == "recepcion" and not movimiento.anulado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("AL24_eso_se_anula_en_su_albaran"),
        )
    if movimiento.anulado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("AL20_ya_estaba_anulado"),
        )
    movimiento.anulado = True
    movimiento.motivo_anulacion = datos.motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="movimiento_de_existencias",
            entidad_id=movimiento.id,
            accion="anular",
            datos={"motivo": datos.motivo, "tipo": movimiento.tipo},
        )
    )
    db.commit()
    return _un_movimiento(db, movimiento)


@router.post("/salidas", status_code=status.HTTP_201_CREATED)
def sacar_de_un_lote(
    datos: SalidaDeAlmacenEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    respuesta: Response,
) -> dict:
    """Sacar producto de un lote, **diciendo de qué trabajo sale**.

    Es la forma de que un tratamiento o un abono descuente del almacén, y la única que hay: el apunte
    es obligatorio porque es lo que permite comprobar el consumo y, sobre todo, **revertirlo**. Si se
    anula el tratamiento, su salida deja de contar sola, sin tocar el libro
    (`servicios.estado_de_los_origenes`): así «anular 2 L devuelve 2» sin borrar nada.

    **Dos veces lo mismo no descuenta dos veces.** Un apunte y un lote solo pueden tener una salida
    viva, así que reenviar la petición —el móvil sin cobertura, un botón pulsado dos veces— devuelve
    la que había en vez de apuntar otra. Y si ahora dice otra cantidad, se devuelve la de antes **con
    un aviso**: cambiarla por detrás dejaría el libro diciendo algo que nadie apuntó. (Si la que había
    está anulada, sí se puede apuntar otra: anular existe justo para eso.)

    **La cantidad sale del apunte, no de la dosis.** Si el apunte tiene la cantidad total, se copia
    (con su unidad) y no hay que teclearla otra vez. Si solo tiene la dosis por hectárea, se pide la
    cantidad: multiplicarla por la superficie por nuestra cuenta es exactamente la confusión de diez
    veces que hay que evitar (A02).

    Y si lo que sale deja el lote en negativo, se avisa antes de apuntarlo (`AL18`). Con
    `aceptar_descuadre` se apunta igual y queda marcado en el libro: lo que de verdad pasó se puede
    registrar siempre, lo que no se hace es apuntarlo a escondidas.
    """
    if datos.apunte_tipo not in servicios.APUNTES_QUE_GASTAN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL15_eso_no_gasta_del_almacen"),
        )
    lote = obtener_de_la_explotacion(db, models.Lote, datos.lote_id, explotacion.id)
    articulo = db.get(models.Articulo, lote.articulo_id)

    gasto = servicios.lo_que_gasta_un_apunte(
        db,
        explotacion_id=explotacion.id,
        apunte_tipo=datos.apunte_tipo,
        apunte_id=datos.apunte_id,
    )
    if not gasto.get("existe"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    if gasto.get("anulado"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("AL16_el_apunte_esta_anulado"),
        )

    clave = _la_clave(datos)
    # **Solo se busca entre las salidas que cuentan.** Si la que había está anulada, el agricultor
    # tiene que poder apuntar la buena: una salida anulada sigue en el libro —nada se borra— pero ya
    # no dice nada de este apunte.
    #
    # **Y una siembra saca la semilla de UN envase, no de varios** (03/10/2026, lo cazó la revisión del
    # T10). La comprobación de «ya estaba» es por apunte **y envase**, que es lo correcto para un
    # tratamiento o un abono —se pueden gastar dos garrafas en el mismo trabajo— pero no para una
    # siembra: la siembra guarda **un** lote, así que una segunda salida por otro envase del mismo
    # artículo descontaba dos veces y dejaba el libro con dos salidas vivas que no cuadran con lo que
    # dice el apunte. Con la siembra se busca por apunte, sin mirar el envase.
    condiciones = [
        models.MovimientoDeExistencias.explotacion_id == explotacion.id,
        models.MovimientoDeExistencias.origen_tipo == datos.apunte_tipo,
        models.MovimientoDeExistencias.origen_id == datos.apunte_id,
        models.MovimientoDeExistencias.anulado.is_(False),
    ]
    if datos.apunte_tipo != "siembra":
        condiciones.append(models.MovimientoDeExistencias.lote_id == lote.id)
    ya = db.scalar(select(models.MovimientoDeExistencias).where(*condiciones))
    if ya is None and clave:
        # Y la clave de reenvío: si esta misma petición ya se atendió —aunque el apunte o el lote
        # vinieran mal en el reintento—, se devuelve el mismo movimiento.
        #
        # **Solo entre las salidas vivas**, igual que la búsqueda de arriba (03/10/2026). Faltaba ese
        # filtro, y el resultado era una pérdida silenciosa: el agricultor anulaba una salida, volvía
        # a mandarla desde el móvil con la misma clave y el programa le contestaba «ya estaba» con la
        # salida **anulada**, así que él veía el apunte hecho y en el almacén no había pasado nada.
        # Lo que se reenvía desde la cola es una petición que hay que atender, no una que ya está.
        ya = db.scalar(
            select(models.MovimientoDeExistencias).where(
                models.MovimientoDeExistencias.explotacion_id == explotacion.id,
                models.MovimientoDeExistencias.clave_de_reenvio == clave,
                models.MovimientoDeExistencias.anulado.is_(False),
            )
        )
    if ya is not None:
        avisos = []
        if (
            datos.cantidad is not None
            and ya.cantidad is not None
            and abs(ya.cantidad - datos.cantidad) > 1e-9
        ):
            avisos.append(
                textos.MENSAJES["AL19_la_salida_ya_estaba_con_otra_cantidad"].format(
                    antes=ya.cantidad, ahora=datos.cantidad, unidad=ya.unidad or ""
                )
            )
        respuesta.status_code = status.HTTP_200_OK
        return {
            "movimiento": _un_movimiento(db, ya),
            "ya_estaba": True,
            "avisos": avisos,
            "textos": textos.ALMACEN,
        }

    cantidad = datos.cantidad if datos.cantidad is not None else gasto.get("cantidad")
    if cantidad is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("AL17_el_apunte_no_dice_el_total"),
        )
    unidad = (datos.unidad or "").strip()[:10] or (gasto.get("unidad") or "").strip()[:10] or None
    if unidad is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("AL13_falta_la_unidad"),
        )

    if not datos.aceptar_descuadre:
        _no_dejar_el_lote_en_negativo(
            db, explotacion_id=explotacion.id, lote=lote, cantidad=cantidad, unidad=unidad
        )

    movimiento = models.MovimientoDeExistencias(
        explotacion_id=explotacion.id,
        articulo_id=articulo.id,
        lote_id=lote.id,
        tipo="salida",
        # La fecha del trabajo, que es el día en que se gastó el producto, no la del día en que se
        # teclea: apuntar un tratamiento de la semana pasada no lo convierte en cosa de hoy.
        fecha=datos.fecha or gasto.get("fecha"),
        cantidad=cantidad,
        unidad=unidad,
        origen_tipo=datos.apunte_tipo,
        origen_id=datos.apunte_id,
        motivo=(datos.motivo or "").strip()[:500] or None,
        usuario_id=usuario.id,
        clave_de_reenvio=clave,
    )
    db.add(movimiento)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="movimiento_de_existencias",
            entidad_id=movimiento.id,
            accion="crear",
            datos={
                "tipo": "salida",
                "articulo": articulo.nombre if articulo else None,
                "numero_lote": lote.numero_lote,
                "cantidad": cantidad,
                "unidad": unidad,
                "apunte": f"{datos.apunte_tipo} {datos.apunte_id}",
                "dosis_por_ha_del_apunte": gasto.get("dosis_por_ha"),
                "aceptar_descuadre": datos.aceptar_descuadre,
            },
        )
    )
    db.commit()
    db.refresh(movimiento)

    avisos: list[str] = []
    unidad_del_lote = _unidad_del_lote(db, explotacion.id, lote)
    if unidad_del_lote and not servicios.se_pueden_sumar(unidad, unidad_del_lote):
        avisos.append(
            textos.MENSAJES["AL3_la_unidad_no_cuadra"].format(
                unidad=unidad_del_lote, otra=unidad
            )
        )

    return {
        "movimiento": _un_movimiento(db, movimiento),
        "ya_estaba": False,
        "avisos": avisos,
        # **Las dos cuentas, dichas por separado**: la cantidad total que se gastó y la dosis por
        # hectárea. Enseñarlas juntas y con su nombre es lo que evita que se confundan, que es un
        # fallo de diez veces (A02).
        "cantidad_total_gastada": cantidad,
        "unidad_de_la_cantidad": unidad,
        "dosis_por_hectarea": gasto.get("dosis_por_ha"),
        "superficie_ha": gasto.get("superficie_ha"),
        "textos": textos.ALMACEN,
    }


def _unidad_del_lote(db, explotacion_id: int, lote: models.Lote) -> str | None:
    """En qué unidad se lleva la cuenta de ese lote (la de lo que entró). `None` si no se sabe."""
    movimientos = servicios.movimientos_del_almacen(
        db, explotacion_id=explotacion_id, lote_id=lote.id, solo_los_que_cuentan=True
    )
    for movimiento in movimientos:
        if movimiento["tipo"] == "entrada" and (movimiento["unidad"] or "").strip():
            return movimiento["unidad"].strip()
    articulo = db.get(models.Articulo, lote.articulo_id)
    return (articulo.unidad or "").strip() or None if articulo else None


def _no_dejar_el_lote_en_negativo(
    db, *, explotacion_id: int, lote: models.Lote, cantidad: float, unidad: str
) -> None:
    """Avisa —y espera confirmación— cuando lo que sale es más de lo que el libro dice que hay.

    **No impide registrar lo que de verdad pasó**, y eso es una decisión del contrato: «nunca altera
    a escondidas una compra ni impide registrar lo que de verdad ocurrió». Lo que hace es parar una
    vez y dar las tres salidas que hay: corregir la cantidad, apuntar la entrada que falta, o decir
    que la diferencia es de verdad (y entonces se apunta, y el lote queda marcado en negativo).

    Y cuando no se puede saber lo que queda —falta la cantidad de una entrada, o hay unidades que no
    se pueden comparar— **no se bloquea nada**: no se puede afirmar que se pase, así que no se dice.
    """
    filas = servicios.existencias_del_almacen(
        db, explotacion_id=explotacion_id, articulo_id=lote.articulo_id
    )
    for fila in filas:
        for de_lote in fila["lotes"]:
            if de_lote["lote_id"] != lote.id:
                continue
            queda = de_lote["saldo"]
            su_unidad = de_lote["unidad"]
            if queda is None or not su_unidad:
                return
            if not servicios.se_pueden_sumar(unidad, su_unidad):
                return
            en_su_unidad = servicios.pasa_a_la_unidad(cantidad, unidad, su_unidad)
            if en_su_unidad is None or en_su_unidad <= queda:
                return
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=textos.MENSAJES["AL18_el_lote_se_queda_en_negativo"].format(
                    queda=queda, unidad=su_unidad, sacas=en_su_unidad
                ),
            )


# --------------------------------------------------------------------------
# Las existencias: por artículo y por lote
# --------------------------------------------------------------------------


@router.get("/existencias")
def ver_las_existencias(
    explotacion: ExplotacionActual,
    db: Db,
    articulo_id: int | None = None,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
) -> dict:
    """Lo que queda, **artículo por artículo y lote por lote**.

    Es la vista que contesta a las dos preguntas de un almacén: «¿me queda producto?» (por artículo) y
    «¿de qué lote era?» (por lote, con su caducidad). Cada lote lleva su cuenta por separado, porque
    un envase con un número distinto es otro envase: si el fabricante avisa de un lote, hay que poder
    saber qué quedaba **de ese**, no del total.

    `desde` y `hasta` **no cambian el saldo** (el saldo no es de un periodo: es lo que hay hoy): lo que
    hacen es añadir, artículo por artículo, lo que se movió en esas fechas. Son dos preguntas distintas
    y mezclarlas daría un número que no significa nada.

    Las tres cosas que se dicen en vez de esconderse están explicadas en
    `servicios.existencias_del_almacen`: un lote del que no se sabe la cantidad sale con `null` y su
    motivo, un saldo negativo se devuelve tal cual y marcado, y la caducidad tiene tres estados
    (caducado, en fecha y «no se sabe cuándo caduca»).

    **Y lo que no se mezcla:** esto no es la cesta. Aquí sale solo lo que dicen los movimientos; lo
    comprado por factura sin albarán se declara aparte (`comprado_sin_entrar`) para que nadie crea que
    sus existencias se han perdido.
    """
    if articulo_id is not None:
        obtener_de_la_explotacion(db, models.Articulo, articulo_id, explotacion.id)

    filas = servicios.existencias_del_almacen(
        db, explotacion_id=explotacion.id, articulo_id=articulo_id
    )
    if desde is not None or hasta is not None:
        for fila in filas:
            fila["movimientos_del_periodo"] = servicios.movimientos_del_almacen(
                db,
                explotacion_id=explotacion.id,
                articulo_id=fila["articulo_id"],
                desde=desde,
                hasta=hasta,
            )

    con_existencias = [
        fila for fila in filas if fila["movimientos"] > 0 or fila["lotes"]
    ]
    return {
        "textos": textos.ALMACEN,
        "articulos": filas,
        "cuantos": len(filas),
        "cuantos_con_existencias": len(con_existencias),
        "sin_poder_saber": sum(1 for fila in filas if fila["saldo"] is None),
        "en_negativo": sum(1 for fila in filas if (fila["saldo"] or 0) < 0),
        "caducados": sum(fila["caducados"] for fila in filas),
        "sin_caducidad_apuntada": sum(fila["sin_caducidad_apuntada"] for fila in filas),
        # **Lo comprado que todavía no ha entrado.** Va aparte de las existencias y no se le suma
        # nunca: es la respuesta a «por qué mi almacén sale vacío si yo he comprado», y sin ella el
        # silencio parecería que el programa ha perdido el producto.
        "comprado_sin_entrar": servicios.lo_comprado_que_no_ha_entrado(
            db, explotacion_id=explotacion.id
        ),
        "resumen": (
            textos.ALMACEN["sin_articulos"]
            if not filas
            else textos.con_cuenta(textos.ALMACEN, "cuantos_articulos", len(filas))
        ),
    }
