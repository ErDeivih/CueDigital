"""Lo que se vende: la cosecha comercializada y la venta directa.

La app oficial lo tiene en «Otras Actividades: Cosecha Comercializada», y el contenido
mínimo del CUE la llama «Cosecha comercializada y/o venta directa». Es el bloque que cierra
el cuaderno por arriba: **no es lo que recoges, es lo que sale de la finca**.

Tres decisiones que conviene no deshacer:

1. **La ruta y el modelo se llaman «venta», aunque la sección oficial se llame «cosecha
   comercializada».** El motivo es que ya existe un `/api/cosecha` para «he cogido la
   cosecha», y dos cosas distintas llamadas «cosecha» en el mismo programa es una trampa
   para quien lo lea dentro de un año. Además, «lo que he vendido» es como lo dice el
   agricultor.

2. **No hay precio ni importe, y no es un olvido.** Lo que la norma pide de esta sección es
   producto, cantidad y fecha; la facturación está en otra parte (Verifactu, factura
   electrónica) que todavía no toca. Empezar por el dinero sería empezar por el final.

3. **Se avisa de si lo vendido cuadra con lo cosechado, y no se bloquea.** Lo normal cuando
   alguien vende más de lo que ha apuntado es que se haya olvidado de apuntar la cosecha,
   no que venda lo que no tiene. Y puede tener razón: puede estar vendiendo de la cosecha
   del año pasado.

## Y el T12 (E6, 03/10/2026), que es lo que cambia el punto 2

Ese punto 2 decía la verdad mientras esta sección no llevaba cuentas. Desde el T12 **sí las
lleva**, y el contrato lo pide con estas palabras (§4, S12): «Separar lote cosechado,
entrega/albarán, factura emitida y cobro». Lo que hay aquí, y dónde está cada cosa:

  · **La entrega** es esta tabla (`ventas_de_cosecha`), que ya existía y **no se ha
    duplicado**: el albarán, el comprador, los kilos y el día. Lo que se le ha añadido es el
    importe (que puede no saberse: es el caso A08), el precio pactado, el vencimiento, el
    enlace con la ficha del cliente y el enlace con la **cosecha** de la que salió (el «lote
    cosechado», que ya existía como la labor de tipo cosecha y por eso no tiene tabla nueva).
  · **La factura emitida** (`/api/facturas-emitidas`) es un documento **nuestro**, de gestión,
    que agrupa una o varias entregas. No es una factura con validez ante nadie: el contrato
    dice que eso «requiere especificación normativa propia antes de activarse como tal», y
    aquí no se emite.
  · **El cobro** (`/api/cobros`) es el dinero que entra, y puede ser parcial: es el caso A06
    del contrato (factura de 121 € y un pago de 40 € → pendiente 81 €).

## La protección que manda sobre todas las demás: **el dinero se cuenta una vez**

Las tres formas de duplicar ingresos, cerradas y probadas:

  1. **Al agrupar entregas en una factura**: el importe de la factura es la suma de sus líneas y
     una entrega viva solo puede estar en una factura viva (índice único en la base).
  2. **Al reenviar la misma petición** (el móvil sin cobertura): la clave de reenvío devuelve lo
     que ya había en vez de apuntar otra vez.
  3. **Al cobrar**: un cobro se imputa a una factura con una cantidad, y el reparto entre las
     entregas que la componen se hace por orden (ver `ventas.reparto_de_lo_cobrado`), así que la
     suma de las filas es exactamente lo cobrado y nada se cuenta dos veces.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .. import adjuntos, catalogos, correcciones, dinero, legal, models, servicios, textos, validaciones, ventas
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AjusteDeUnaEntrega,
    AjusteEntrada,
    AplicacionDeUnCobroSalida,
    CobroDeUnaFactura,
    CobroEntrada,
    ColumnaDeUnaTabla,
    ConciliacionEntrada,
    FacturaEmitidaEntrada,
    FacturaEmitidaSalida,
    InformeDeVentas,
    LineaDeUnaFacturaEmitida,
    RespuestaDeUnCobro,
    TablaDeVentas,
    VentaConNombres,
    VentaEntrada,
    VentaSalida,
)

router = APIRouter(prefix="/api", tags=["lo que se vende"])

# El papel que demuestra una devolución o un ajuste: una foto del básculero, el boletín del
# laboratorio, el resguardo. Se admiten los mismos formatos que un boletín de análisis, porque es lo
# mismo: un papel que hace una foto. La lista está en `adjuntos.py` y no se copia aquí para que un
# formato nuevo no haya que apuntarlo en dos sitios.
TIPOS_DE_PAPEL_DE_UN_AJUSTE = adjuntos.TIPOS_BOLETIN


def _campana(db, explotacion, campana_id: int | None) -> models.Campana:
    if campana_id is not None:
        return obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    campana = db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion.id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )
    if campana is None:
        raise HTTPException(status_code=404, detail="Todavía no hay ningún año creado.")
    return campana


def _donde(db, venta: models.VentaDeCosecha) -> str:
    """De dónde salió lo que se vendió, dicho como lo diría el agricultor."""
    if venta.parcela_id is not None:
        parcela = db.get(models.Parcela, venta.parcela_id)
        return parcela.alias if parcela else textos.VENTA["sin_donde"]
    if venta.grupo_id is not None:
        grupo = db.get(models.GrupoParcelas, venta.grupo_id)
        return grupo.nombre if grupo else textos.VENTA["varias_parcelas"]
    return textos.VENTA["sin_donde"]


def _la_cosecha_de_la_que_sale(db, venta: models.VentaDeCosecha) -> str:
    """De qué cosecha salió, con el nombre y el día, para que el agricultor la reconozca.

    Vacío cuando no se ha dicho: **no se rellena con la cosecha más parecida**, que sería afirmar de
    dónde salió una partida sin saberlo. Es la regla de todo el programa, y aquí tiene un motivo
    extra: de esto depende poder responder «¿de dónde salió este trigo?» cuando pregunta un cliente.
    """
    if venta.cosecha_id is None:
        return ""
    labor = db.get(models.Labor, venta.cosecha_id)
    if labor is None or labor.explotacion_id != venta.explotacion_id:
        return ""
    producto = (labor.detalles or {}).get("producto") or ""
    return f"{producto} · {legal.formatea_fecha(labor.fecha)}".strip(" ·")


# --------------------------------------------------------------------------
# Las cuentas de una entrega: sus ajustes, su factura y lo que le han pagado
# --------------------------------------------------------------------------
#
# Todo esto se **calcula** y no se guarda, por el mismo motivo por el que los kilos de una venta se
# calculan al vuelo: si un día cambia la regla de conversión o de reparto, el apunte histórico no se
# queda mintiendo. Y lo que no se sabe se queda en «no se sabe», que es la mitad del ticket (A08).


def los_ajustes_de_una_entrega(
    db, *, explotacion_id: int, venta_id: int, solo_vivos: bool = True
) -> list[models.AjusteDeEntrega]:
    consulta = select(models.AjusteDeEntrega).where(
        models.AjusteDeEntrega.explotacion_id == explotacion_id,
        models.AjusteDeEntrega.venta_id == venta_id,
    )
    if solo_vivos:
        consulta = consulta.where(models.AjusteDeEntrega.anulado.is_(False))
    orden = (
        models.AjusteDeEntrega.fecha.asc(),
        models.AjusteDeEntrega.id.asc(),
    )
    return list(db.scalars(consulta.order_by(*orden)))


def como_se_ve_un_ajuste(ajuste: models.AjusteDeEntrega) -> AjusteDeUnaEntrega:
    return AjusteDeUnaEntrega(
        id=ajuste.id,
        tipo=ajuste.tipo,
        etiqueta_tipo=textos.VENTA["tipos_de_ajuste"].get(ajuste.tipo, ajuste.tipo),
        fecha=ajuste.fecha,
        cantidad=ajuste.cantidad,
        unidad=ajuste.unidad,
        importe=dinero.a_decimal(ajuste.importe),
        texto_importe=dinero.formatea(dinero.a_decimal(ajuste.importe)),
        origen=ajuste.origen,
        etiqueta_origen=textos.VENTA["origenes_de_un_ajuste"].get(ajuste.origen, ajuste.origen),
        motivo=ajuste.motivo,
        evidencia_descripcion=ajuste.evidencia_descripcion,
        tiene_papel=bool(ajuste.fichero_ruta),
        nombre_del_papel=ajuste.fichero_nombre,
        anulado=ajuste.anulado,
        motivo_anulacion=ajuste.motivo_anulacion,
    )


def _la_linea_de_factura_de_una_entrega(
    db, *, explotacion_id: int, venta_id: int
) -> models.LineaDeFacturaEmitida | None:
    return db.scalar(
        select(models.LineaDeFacturaEmitida).where(
            models.LineaDeFacturaEmitida.explotacion_id == explotacion_id,
            models.LineaDeFacturaEmitida.venta_id == venta_id,
            models.LineaDeFacturaEmitida.anulada.is_(False),
        )
    )


def lo_cobrado_de_una_factura(
    db, *, explotacion_id: int, factura_id: int, sin_este_cobro: int | None = None
) -> Decimal:
    """Lo que se ha cobrado de esa factura. **La regla vive en `servicios`** (11/10/2026).

    Aquí queda solo el nombre que usaba este fichero, delegando: la regla la comparten la ficha de la
    factura, el margen de lo que se vende y la conciliación del banco, y tenerla en tres copias fue
    exactamente cómo el reparto de un cobro se quedó sin contar en cinco sitios distintos.
    """
    return servicios.lo_cobrado_de_una_factura(
        db,
        explotacion_id=explotacion_id,
        factura_id=factura_id,
        sin_este_cobro=sin_este_cobro,
    )


def las_entregas_de_una_factura(
    db, *, explotacion_id: int, factura_id: int, con_anuladas: bool = False
) -> list[models.LineaDeFacturaEmitida]:
    """Las líneas vivas de una factura, **en el orden en que se reparte el dinero**: la más antigua
    primero.

    Ese orden no es cosmético: es el que usa `ventas.reparto_de_lo_cobrado` para decidir a qué
    entrega va cada euro, y por eso se fija aquí una sola vez. Se ordena por la fecha de la entrega y,
    si dos son del mismo día, por su número, para que el reparto sea el mismo siempre (si cambiara,
    el pendiente de una fila cambiaría sin que nadie hubiera cobrado nada).

    `con_anuladas` es para **una factura quitada** (revisión del T12): sus líneas siguen en la base con
    su `anulada` y su motivo, y lo que hay que poder ver de un documento que se emitió es lo que decía.
    Las cuentas de una factura viva **no** las miran: ahí una línea anulada no cuenta.
    """
    consulta = select(models.LineaDeFacturaEmitida).where(
        models.LineaDeFacturaEmitida.explotacion_id == explotacion_id,
        models.LineaDeFacturaEmitida.factura_emitida_id == factura_id,
    )
    if not con_anuladas:
        consulta = consulta.where(models.LineaDeFacturaEmitida.anulada.is_(False))
    lineas = list(db.scalars(consulta))
    orden: list[tuple[dt.date, int, models.LineaDeFacturaEmitida]] = []
    for linea in lineas:
        entrega = db.get(models.VentaDeCosecha, linea.venta_id)
        fecha = (entrega.fecha if entrega else None) or dt.date.min
        orden.append((fecha, linea.venta_id, linea))
    return [linea for _, _, linea in sorted(orden, key=lambda uno: (uno[0], uno[1]))]


@dataclass
class LoQueSeSabeDeUnaEntrega:
    """Todo lo que hay que saber de una entrega para contarla, sin volver a preguntar nada.

    Existe para que la misma cuenta la usen la lista, la tabla, el informe y la ficha: si cada uno la
    hiciera por su cuenta, un día dirían cosas distintas y el agricultor tendría que decidir a cuál
    creer. Lo que no se sabe va en `None`, nunca en cero.
    """

    importe: Decimal | None = None
    importe_total: Decimal | None = None
    cantidad_neta: float | None = None
    cobrado: Decimal | None = None
    pendiente: Decimal | None = None
    estado: str = ventas.SIN_IMPORTE
    facturada: bool = False
    factura_id: int | None = None
    factura_numero: str | None = None
    vencimiento: dt.date | None = None
    ajustes: list[models.AjusteDeEntrega] = field(default_factory=list)


def lo_que_se_sabe_de_una_entrega(
    db, explotacion, venta: models.VentaDeCosecha, *, reparto: dict[int, Decimal] | None = None
) -> LoQueSeSabeDeUnaEntrega:
    """La cuenta entera de una entrega: sus ajustes, su importe, su factura y lo que le han pagado.

    `reparto` es **lo cobrado que le toca a esta entrega** dentro de su factura (la cifra ya
    repartida, `Decimal`). Lo calcula quien tiene la factura entera a la vista, porque el reparto es
    de la factura y no de la entrega (ver `ventas.reparto_de_lo_cobrado`). Cuando se mira una entrega
    sola, no se pasa nada y se calcula aquí pidiendo su factura: así el número es el mismo se mire
    por donde se mire, y no hay dos formas de contar lo cobrado.
    """
    ajustes = los_ajustes_de_una_entrega(db, explotacion_id=explotacion.id, venta_id=venta.id)
    deltas = [dinero.a_decimal(a.importe) for a in ajustes if a.importe is not None]
    importe = dinero.a_decimal(venta.importe)
    importe_total = ventas.importe_de_una_entrega(
        importe=importe,
        # La cantidad va con `cantidad_a_decimal` y no con `a_decimal`: una cantidad no es dinero y
        # el programa la guarda como número decimal desde siempre (el porqué, entero, en `dinero.py`).
        cantidad=dinero.cantidad_a_decimal(venta.cantidad),
        precio_unitario=dinero.a_decimal(venta.precio_unitario),
        ajustes=deltas,
    )
    cantidad_neta = ventas.cantidad_neta(
        dinero.cantidad_a_decimal(venta.cantidad),
        [dinero.cantidad_a_decimal(a.cantidad) for a in ajustes if a.cantidad is not None],
    )

    linea = _la_linea_de_factura_de_una_entrega(
        db, explotacion_id=explotacion.id, venta_id=venta.id
    )
    factura = db.get(models.FacturaEmitida, linea.factura_emitida_id) if linea else None
    if factura is not None and factura.anulada:
        factura = None
    if factura is not None and reparto is None:
        reparto = _el_reparto_de_una_factura(
            db, explotacion=explotacion, factura=factura
        ).get(venta.id, dinero.CERO)
    cobrado = None
    pendiente = None
    if factura is not None:
        cobrado = reparto
        pendiente = ventas.pendiente_de(importe_total, cobrado)
    vencimiento = venta.vencimiento or (factura.vencimiento if factura else None)
    estado = ventas.estado_de_una_entrega(
        importe=importe_total,
        cobrado=cobrado,
        facturada=factura is not None,
        vencimiento=vencimiento,
        hoy=dt.date.today(),
    )
    return LoQueSeSabeDeUnaEntrega(
        importe=importe,
        importe_total=importe_total,
        cantidad_neta=float(cantidad_neta) if cantidad_neta is not None else None,
        cobrado=cobrado,
        pendiente=pendiente,
        estado=estado,
        facturada=factura is not None,
        factura_id=factura.id if factura else None,
        factura_numero=factura.numero if factura else None,
        vencimiento=vencimiento,
        ajustes=ajustes,
    )


def _el_reparto_de_una_factura(
    db, *, explotacion, factura: models.FacturaEmitida
) -> dict[int, Decimal]:
    """A qué entrega va cada euro cobrado de esa factura: `{venta_id: lo que le toca}`.

    Las entregas se toman **en el orden en que se facturaron** (la más antigua primero) y se les
    aplica lo cobrado hasta completarlas. Con eso, la suma de lo que enseña cada fila es exactamente
    lo que se ha cobrado de la factura, que es lo que hace que el pie de la tabla y el detalle no
    puedan contradecirse.
    """
    lineas = las_entregas_de_una_factura(
        db, explotacion_id=explotacion.id, factura_id=factura.id
    )
    importes = [dinero.a_decimal(linea.importe) for linea in lineas]
    cobrado = lo_cobrado_de_una_factura(
        db, explotacion_id=explotacion.id, factura_id=factura.id
    )
    reparto = ventas.reparto_de_lo_cobrado(importes, cobrado)
    return {linea.venta_id: cuanto for linea, cuanto in zip(lineas, reparto, strict=True)}



def con_nombres(
    db,
    venta: models.VentaDeCosecha,
    *,
    explotacion=None,
    reparto: dict[int, Decimal] | None = None,
) -> VentaConNombres:
    """La venta con los nombres ya resueltos y sus cuentas hechas, para enseñarla sin más llamadas.

    **Las cuentas se hacen aquí y no en el navegador**, y no es por comodidad: es porque el dinero se
    calcula con `Decimal` y en el JavaScript todo número es de coma flotante. Si la pantalla sumara
    los importes, `0,10 + 0,20` daría `0,30000000000000004` y el agricultor vería una cifra que no
    es. La pantalla **enseña lo que el servidor ya calculó**, que es la regla de este ticket.
    """
    base = VentaSalida.model_validate(venta).model_dump()
    base["kilos"] = catalogos.kilos_de_una_venta(venta.cantidad, venta.unidad)
    base["etiqueta_tipo"] = catalogos.ETIQUETA_VENTA_CORTA.get(venta.tipo, venta.tipo)
    base["donde"] = _donde(db, venta)
    base["etiqueta_unidad"] = (catalogos.unidad_de_venta(venta.unidad) or {}).get(
        "etiqueta", venta.unidad
    )
    base["texto_cantidad"] = (
        f"{legal.formatea_numero(venta.cantidad, 2)} "
        f"{(catalogos.unidad_de_venta(venta.unidad) or {}).get('corto', venta.unidad)}"
    ).strip()
    if explotacion is not None:
        _las_cuentas_en_la_salida(db, explotacion, venta, base, reparto=reparto)
    return VentaConNombres(**base)


def _las_cuentas_en_la_salida(db, explotacion, venta, base: dict, *, reparto=None) -> None:
    """Mete en la respuesta lo que se sabe del dinero y con qué palabras se enseña."""
    suyo = lo_que_se_sabe_de_una_entrega(db, explotacion, venta, reparto=reparto)
    base["importe"] = suyo.importe
    base["importe_total"] = suyo.importe_total
    base["cobrado"] = suyo.cobrado
    base["pendiente"] = suyo.pendiente
    base["estado"] = suyo.estado
    base["facturada"] = suyo.facturada
    base["factura_emitida_id"] = suyo.factura_id
    base["factura_numero"] = suyo.factura_numero
    base["vencimiento"] = suyo.vencimiento
    base["ajustes"] = [como_se_ve_un_ajuste(a) for a in suyo.ajustes]
    base["texto_importe"] = dinero.formatea(suyo.importe)
    base["texto_importe_total"] = dinero.formatea(suyo.importe_total)
    base["texto_cobrado"] = dinero.formatea(suyo.cobrado) if suyo.facturada else ""
    base["texto_pendiente"] = dinero.formatea(suyo.pendiente) if suyo.facturada else ""
    base["etiqueta_estado"] = textos.VENTA.get(f"estado_{suyo.estado}", suyo.estado)
    base["de_que_cosecha"] = _la_cosecha_de_la_que_sale(db, venta)
    if suyo.cantidad_neta is not None:
        base["kilos_netos"] = suyo.cantidad_neta


def _rechazar_si_bloquea(avisos: list[validaciones.Aviso]) -> None:
    bloqueantes = [aviso for aviso in avisos if aviso.bloquea]
    if bloqueantes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "puede_guardarse": False,
                "avisos": [aviso.como_dict() for aviso in bloqueantes],
            },
        )


def _avisos(db, explotacion, datos, sin_esta: int | None = None) -> list[validaciones.Aviso]:
    """Los avisos de una venta, con los totales de la campaña ya calculados.

    Los totales se pasan SIN contar esta venta: si se contara, al corregir una venta ya
    guardada se compararía consigo misma y el aviso de «vendes más de lo que cogiste»
    saltaría siempre.
    """
    campana = obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    vendido, _cuantas = servicios.lo_vendido_en_la_campana(
        db, explotacion_id=explotacion.id, campana_id=campana.id, sin_esta=sin_esta
    )
    cosechado = servicios.lo_cosechado_en_la_campana(
        db, explotacion_id=explotacion.id, campana_id=campana.id
    )
    return validaciones.validar_venta(
        datos=datos, cosechado_kg=cosechado, vendido_kg=vendido
    )


def _comprobar_sitio(db, explotacion, datos) -> None:
    """Que la campaña, la tierra, el grupo, el cliente y la cosecha son **de esta finca**.

    El cliente y la cosecha se comprueban aquí y no se dejaron fuera a propósito: son los dos
    enlaces que añade el T12, y un enlace a un identificador de otra finca es exactamente la fuga
    que el contrato prohíbe (A13). `obtener_de_la_explotacion` contesta **404 y no 403**, para no
    contar si ese identificador existe en otra finca.
    """
    obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    if datos.parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    if datos.grupo_id is not None:
        obtener_de_la_explotacion(db, models.GrupoParcelas, datos.grupo_id, explotacion.id)
    if getattr(datos, "contacto_id", None) is not None:
        obtener_de_la_explotacion(db, models.Contacto, datos.contacto_id, explotacion.id)
    if getattr(datos, "cosecha_id", None) is not None:
        labor = obtener_de_la_explotacion(db, models.Labor, datos.cosecha_id, explotacion.id)
        if labor.tipo != "cosecha":
            # Decir que una labor cualquiera es «la cosecha de la que salió» sería apuntar de dónde
            # salió una partida con un dato que no lo dice. Se contesta con palabras.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ese apunte no es una cosecha, así que no puede ser el lote del que salió.",
            )


def _el_importe_negativo(datos) -> None:
    """Un importe de una entrega no puede ser negativo.

    Lo que resta (una devolución, un descuento) se apunta como ajuste de la entrega, con su origen y
    su motivo, no como un importe en negativo: si no, dentro de un año ese `-40,50` no dice de dónde
    sale, que es justo lo que el contrato quiere impedir.
    """
    for campo in ("importe", "precio_unitario"):
        valor = dinero.a_decimal(getattr(datos, campo, None))
        if valor is not None and valor < 0:
            _rechazar_si_bloquea(
                [
                    validaciones.Aviso(
                        codigo="D2_importe_negativo",
                        mensaje=textos.mensaje("D2_importe_negativo"),
                        bloquea=True,
                        campo=campo,
                    )
                ]
            )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.get("/ventas", response_model=list[VentaConNombres])
def listar_ventas(
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    tipo: str | None = None,
) -> list[VentaConNombres]:
    consulta = select(models.VentaDeCosecha).where(
        models.VentaDeCosecha.explotacion_id == explotacion.id,
        models.VentaDeCosecha.anulado.is_(False),
    )
    if campana_id is not None:
        consulta = consulta.where(models.VentaDeCosecha.campana_id == campana_id)
    if tipo is not None:
        consulta = consulta.where(models.VentaDeCosecha.tipo == tipo)
    ventas = list(db.scalars(consulta.order_by(models.VentaDeCosecha.fecha.desc())))
    # **Las cuentas del dinero, también aquí** (revisión del T12). Esta lista se llamaba a
    # `con_nombres(db, venta)` **sin la explotación**, así que `_las_cuentas_en_la_salida` no se ejecutaba y
    # devolvía los campos del dinero en su valor por defecto: `importe_total: None`, `estado: ""` y, sobre
    # todo, **`facturada: false`** de una entrega que está dentro de una factura cobrada a medias.
    #
    # Y eso no es un hueco: **es una afirmación falsa**, que es la peor forma de un dato que no se sabe —el
    # programa no dice «no lo he mirado», dice «no está facturada»—. La ficha y la tabla ya lo decían bien:
    # eran **tres puertas del mismo dato y dos contestaban distinto**.
    #
    # El reparto de lo cobrado se calcula **una vez por factura** y se reutiliza en todas sus entregas: es
    # una cuenta de la factura entera (ver `ventas.reparto_de_lo_cobrado`), y hacerla por entrega daría a
    # cada una lo cobrado de todas.
    repartos: dict[int, Decimal] = {}
    for factura in db.scalars(
        select(models.FacturaEmitida).where(
            models.FacturaEmitida.explotacion_id == explotacion.id,
            models.FacturaEmitida.anulada.is_(False),
        )
    ):
        repartos.update(_el_reparto_de_una_factura(db, explotacion=explotacion, factura=factura))
    return [
        con_nombres(db, venta, explotacion=explotacion, reparto=repartos.get(venta.id))
        for venta in ventas
    ]


@router.get("/ventas/informe", response_model=InformeDeVentas)
def informe_de_ventas(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> InformeDeVentas:
    """El «Informe Cosechas Comercializadas» de la app oficial.

    Va declarado ANTES de `/ventas/{venta_id}` a propósito: FastAPI resuelve las rutas por
    orden de declaración, así que si estuviera después, «informe» se leería como un
    identificador y esta llamada devolvería un 422 sin explicar por qué.
    """
    campana = _campana(db, explotacion, campana_id)
    ventas = list(
        db.scalars(
            select(models.VentaDeCosecha)
            .where(
                models.VentaDeCosecha.explotacion_id == explotacion.id,
                models.VentaDeCosecha.campana_id == campana.id,
                models.VentaDeCosecha.anulado.is_(False),
            )
            .order_by(models.VentaDeCosecha.fecha)
        )
    )
    resumen = servicios.resumen_de_ventas(
        db, explotacion_id=explotacion.id, campana_id=campana.id
    )
    hay_unidades = any(
        catalogos.kilos_de_una_venta(venta.cantidad, venta.unidad) is None for venta in ventas
    )

    filas = [
        {
            "fecha": legal.formatea_fecha(venta.fecha),
            "fecha_fin": legal.formatea_fecha(venta.fecha_fin) if venta.fecha_fin else "",
            "tipo": catalogos.ETIQUETA_VENTA_CORTA.get(venta.tipo, venta.tipo),
            "producto": venta.producto,
            "variedad": venta.variedad or "",
            "cantidad": f"{legal.formatea_numero(venta.cantidad, 2)} "
            f"{(catalogos.unidad_de_venta(venta.unidad) or {}).get('corto', venta.unidad)}",
            "lote": venta.lote or "",
            "comprador": venta.comprador or "",
            "numero_albaran": venta.numero_albaran or "",
            "donde": _donde(db, venta),
        }
        for venta in ventas
    ]

    vendido = resumen["vendido_kg"]
    cosechado = resumen["cosechado_kg"]
    if not ventas:
        mensaje = textos.VENTA["informe_sin_nada"]
    elif cosechado <= 0:
        mensaje = textos.VENTA["sin_cosecha"].format(
            vendido=legal.formatea_numero(vendido, 0)
        )
    elif vendido > cosechado * 1.001:
        mensaje = textos.VENTA["no_cuadra"].format(
            vendido=legal.formatea_numero(vendido, 0),
            cosechado=legal.formatea_numero(cosechado, 0),
        )
    else:
        mensaje = textos.VENTA["cuadra"].format(
            vendido=legal.formatea_numero(vendido, 0),
            cosechado=legal.formatea_numero(cosechado, 0),
        )

    return InformeDeVentas(
        campana=campana.anio,
        cuantas=len(filas),
        vendido_kg=vendido,
        cosechado_kg=cosechado,
        queda_kg=resumen["queda_kg"],
        hay_unidades=hay_unidades,
        titulos=[
            textos.VENTA["tabla_dia"],
            textos.VENTA["tabla_que"],
            textos.VENTA["tabla_cuanto"],
            textos.VENTA["tabla_quien"],
            textos.VENTA["tabla_lote"],
            textos.VENTA["tabla_donde"],
            textos.VENTA["tabla_albaran"],
        ],
        filas=filas,
        vacio=textos.VENTA["informe_sin_nada"],
        mensaje=mensaje,
    )


@router.get("/ventas/resumen")
def resumen_de_ventas_endpoint(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> dict:
    """Lo vendido y lo cosechado, para poder mirarlo de un vistazo.

    Va antes de `/ventas/{venta_id}` por el mismo motivo que el informe: si no, «resumen» se
    leería como un identificador.
    """
    campana = _campana(db, explotacion, campana_id)
    resumen = servicios.resumen_de_ventas(
        db, explotacion_id=explotacion.id, campana_id=campana.id
    )
    return {
        "campana": campana.anio,
        "filas": [
            {"que": textos.VENTA["vendido"], "kilos": resumen["vendido_kg"]},
            {"que": textos.VENTA["cosecha_apuntada"], "kilos": resumen["cosechado_kg"]},
            {"que": textos.VENTA["queda_por_vender"], "kilos": resumen["queda_kg"]},
        ],
        "ventas": resumen["ventas"],
        "cuadra": resumen["vendido_kg"] <= resumen["cosechado_kg"] * 1.001,
        # ── Y el dinero (T12) ────────────────────────────────────────────────────────────────
        #
        # Los cuatro números de las cuentas, calculados **con las mismas funciones que la tabla y
        # las fichas**, así que el resumen y el detalle no pueden decir cosas distintas. Van en texto
        # decimal (contrato §2) y `sin_importe` cuenta las entregas que **no entran** en la suma por
        # no saberse su importe: sin ese número, el total parecería completo (A08).
        "dinero": _el_dinero_de_la_campana(db, explotacion, campana),
    }


def _el_dinero_de_la_campana(db, explotacion, campana) -> dict:
    """Lo que suman las entregas del año: importe conocido, facturado, cobrado y pendiente.

    Es una cuenta de **cobro**, no de devengo: `facturado` solo cuenta lo que está en una factura
    nuestra y `pendiente` lo que de esa factura falta por cobrar. Una entrega con importe pero sin
    facturar suma en `importe` y no en `pendiente`, y eso es la verdad: no es que no se lo deban, es
    que todavía no se le ha pedido a nadie.
    """
    repartos: dict[int, Decimal] = {}
    for factura in db.scalars(
        select(models.FacturaEmitida).where(
            models.FacturaEmitida.explotacion_id == explotacion.id,
            models.FacturaEmitida.anulada.is_(False),
        )
    ):
        repartos.update(
            _el_reparto_de_una_factura(db, explotacion=explotacion, factura=factura)
        )
    filas = []
    for venta in db.scalars(
        select(models.VentaDeCosecha).where(
            models.VentaDeCosecha.explotacion_id == explotacion.id,
            models.VentaDeCosecha.campana_id == campana.id,
            models.VentaDeCosecha.anulado.is_(False),
        )
    ):
        suyo = lo_que_se_sabe_de_una_entrega(
            db, explotacion, venta, reparto=repartos.get(venta.id)
        )
        filas.append(
            {
                "importe": dinero.a_texto(suyo.importe_total),
                "cobrado": dinero.a_texto(suyo.cobrado),
                "facturada": suyo.facturada,
            }
        )
    return ventas.cuenta_de_dinero(filas).como_dict()


@router.post("/ventas/validar")
def validar_venta_endpoint(datos: VentaEntrada, explotacion: ExplotacionActual, db: Db) -> dict:
    avisos = _avisos(db, explotacion, datos)
    return {
        "puede_guardarse": not validaciones.hay_bloqueo(avisos),
        "avisos": [aviso.como_dict() for aviso in avisos],
    }


@router.post("/ventas", response_model=VentaConNombres, status_code=status.HTTP_201_CREATED)
def crear_venta(
    datos: VentaEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> VentaConNombres:
    """Apunta una entrega. **Reenviar la misma petición no la apunta dos veces.**

    El reenvío es el caso A12 del contrato y pasa todos los días: el agricultor apunta en el campo
    sin cobertura, el móvil guarda la petición con su clave y la repite al volver a haber red. Si no
    se reconociera, la misma partida saldría dos veces en el cuaderno y en las cuentas.

    Se reconoce por **la clave de reenvío**, que es lo que manda la cola del móvil
    (`nucleo.claveDeReenvio`), y la protección es doble: la comprobación de aquí y un índice único
    parcial en la base, que es la mitad que una comprobación en Python no cubre (dos peticiones a la
    vez). Cuando ya estaba, se devuelve **la entrega que había**, con las cuentas que tenga ahora:
    reenviar devuelve su resultado, no un error (contrato §2).
    """
    if datos.clave_de_reenvio:
        ya = db.scalar(
            select(models.VentaDeCosecha).where(
                models.VentaDeCosecha.explotacion_id == explotacion.id,
                models.VentaDeCosecha.clave_de_reenvio == datos.clave_de_reenvio,
                models.VentaDeCosecha.anulado.is_(False),
            )
        )
        if ya is not None:
            return con_nombres(db, ya, explotacion=explotacion)

    _rechazar_si_bloquea(_avisos(db, explotacion, datos))
    _el_importe_negativo(datos)
    _comprobar_sitio(db, explotacion, datos)

    venta = models.VentaDeCosecha(explotacion_id=explotacion.id, **datos.model_dump())
    db.add(venta)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="venta_cosecha",
            accion="crear",
            datos={
                "producto": venta.producto,
                "cantidad": venta.cantidad,
                "unidad": venta.unidad,
                # El importe también va al rastro: es el dato que antes no existía y el que más se
                # va a mirar dentro de un año.
                "importe": dinero.a_texto(dinero.a_decimal(venta.importe)),
            },
        )
    )
    db.commit()
    return con_nombres(db, venta, explotacion=explotacion)


@router.put("/ventas/{venta_id}", response_model=VentaConNombres)
def corregir_venta(
    venta_id: int,
    datos: VentaEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> VentaConNombres:
    """Corrige una venta. Los avisos se calculan sin contar la venta que se está corrigiendo.

    **Y corregir el importe de una entrega no reescribe la factura que ya se hizo.** La línea de la
    factura guarda la fotografía del día en que se emitió, así que lo que se hizo, hecho se queda; lo
    que cambia es que la pantalla de la factura dice que hay una diferencia (el contrato lo pide:
    «registrar diferencias observadas sin forzar a que una factura original cuadre con un redondeo
    distinto»). Callarlo o reescribir el documento serían las dos formas de mentir.
    """
    _rechazar_si_bloquea(_avisos(db, explotacion, datos, sin_esta=venta_id))
    _el_importe_negativo(datos)
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    _comprobar_sitio(db, explotacion, datos)

    # La clave de reenvío del alta no se toca al corregir: es la del envío que creó la fila, y
    # cambiarla por la de la corrección dejaría al móvil sin poder reconocer la petición original.
    if datos.clave_de_reenvio is None:
        datos.clave_de_reenvio = venta.clave_de_reenvio

    antes = {
        "producto": venta.producto,
        "cantidad": venta.cantidad,
        "importe": dinero.a_texto(dinero.a_decimal(venta.importe)),
    }
    for clave, valor in datos.model_dump().items():
        setattr(venta, clave, valor)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="venta_cosecha",
            entidad_id=venta.id,
            accion="corregir",
            datos={
                "antes": antes,
                "ahora": {
                    "producto": venta.producto,
                    "cantidad": venta.cantidad,
                    "importe": dinero.a_texto(dinero.a_decimal(venta.importe)),
                },
            },
        )
    )
    db.commit()
    return con_nombres(db, venta, explotacion=explotacion)


@router.post("/ventas/{venta_id}/anular", response_model=VentaSalida)
def anular_venta(
    venta_id: int,
    datos: dict,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> models.VentaDeCosecha:
    """Anula la venta. No se borra: queda con el motivo, como todo en el cuaderno.

    Una venta **facturada no se anula por aquí**: primero hay que quitar la factura, porque si no la
    factura se quedaría contando un dinero que ya no tiene entrega detrás. Se dice con palabras y con
    el botón que lo arregla (la factura, que está en su pantalla).
    """
    motivo = (datos or {}).get("motivo", "").strip()
    if len(motivo) < 3:
        raise HTTPException(
            status_code=422, detail="Dinos por qué lo anulas, para que quede apuntado."
        )
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    linea = _la_linea_de_factura_de_una_entrega(
        db, explotacion_id=explotacion.id, venta_id=venta.id
    )
    if linea is not None:
        factura = db.get(models.FacturaEmitida, linea.factura_emitida_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje(
                "D6_esa_entrega_ya_esta_facturada",
                numero=_como_se_llama_una_factura(factura),
            ),
        )
    venta.anulado = True
    venta.motivo_anulacion = motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="venta_cosecha",
            entidad_id=venta.id,
            accion="anular",
            datos={"motivo": motivo},
        )
    )
    db.commit()
    return venta


def _como_se_llama_una_factura(factura: models.FacturaEmitida | None) -> str:
    """El nombre de una factura nuestra: su número y, si no lo tiene, su fecha.

    Un número que no está **no se inventa**: un número inventado acabaría en un papel que va a manos de
    un cliente. Es la misma regla de siempre, aplicada a un documento que se enseña.
    """
    if factura is None:
        return ""
    if factura.numero:
        return factura.numero
    return legal.formatea_fecha(factura.fecha) if factura.fecha else ""


def _el_titulo_de_una_factura(factura: models.FacturaEmitida | None) -> str:
    """Cómo se llama esa factura en una lista, ya compuesto: «Factura F-2026-1 · Cooperativa».

    Se compone aquí y no en la pantalla por la regla de siempre: en un componente, una frase compuesta
    es una frase escrita a mano, y el día que cambie el nombre de las cosas habría que cambiarlo en dos
    sitios. Si la factura no tiene número, se llama por su fecha y **no se le inventa uno**.
    """
    if factura is None:
        return ""
    plantilla = (
        textos.FACTURA_EMITIDA["nombre_con_cliente"]
        if factura.cliente
        else textos.FACTURA_EMITIDA["nombre"]
    )
    if not factura.numero:
        plantilla = textos.FACTURA_EMITIDA["nombre_sin_numero"]
    return (
        plantilla.replace("{numero}", factura.numero or "")
        .replace("{fecha}", legal.formatea_fecha(factura.fecha) if factura.fecha else "")
        .replace("{cliente}", factura.cliente or "")
        .strip()
    )


@router.delete("/ventas/{venta_id}")
def borrar_venta(
    venta_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """Quita una venta del cuaderno.

    QUÉ CAMBIA CON EL T12, Y POR QUÉ. Aquí decía —con razón— que **nada del cuaderno apuntaba a una
    venta, así que no había nada que comprobar antes de borrarla**. Desde el T12 eso ya no es
    verdad, y lo avisó el propio guardián que estaba puesto para eso
    (`test_nada_apunta_a_una_venta_y_no_tiene_fichero`, que exigía que la lista de tablas que apuntan
    a `venta_id` estuviera vacía): ahora apuntan `lineas_de_factura_emitida` y `ajustes_de_entrega`.
    O sea que la comprobación que faltaba **la pidió el test**, que es exactamente para lo que
    estaba. Las dos cosas que se hacen ahora:

      · **Si la entrega está dentro de una factura viva, no se borra**: contesta 409 y dice en qué
        factura está. Si se borrara, la factura seguiría contando un dinero cuya entrega ya no
        existe, y el agricultor no tendría forma de saber de dónde salía ese importe.
      · **Sus ajustes se van con ella**, y cada uno deja su propio rastro en la auditoría. Son parte
        de la entrega (una devolución de esta entrega, sin la entrega, no significa nada) y borrarlos
        uno a uno sería pedirle al agricultor que deshaga el error en tres pasos. Lo que **no** se
        pierde es el rastro: `correcciones.borrar` escribe el registro entero de cada ajuste.

    SOBRE EL PAPEL DE LA VENTA: la entrega sigue sin tener fichero propio en su tabla, pero **sus
    ajustes sí pueden tenerlo** (la foto del básculero, el boletín del laboratorio). Por eso ahora
    sí se borra del disco lo que haya: si no, quedarían papeles del agricultor —con su nombre y su
    NIF— en la carpeta de adjuntos sin que nada los nombre. Hay una prueba que lo comprueba mirando
    el disco, no confiando en el código.
    """
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    linea = _la_linea_de_factura_de_una_entrega(
        db, explotacion_id=explotacion.id, venta_id=venta.id
    )
    if linea is not None:
        factura = db.get(models.FacturaEmitida, linea.factura_emitida_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje(
                "D6_esa_entrega_ya_esta_facturada",
                numero=_como_se_llama_una_factura(factura),
            ),
        )

    for ajuste in los_ajustes_de_una_entrega(
        db, explotacion_id=explotacion.id, venta_id=venta.id, solo_vivos=False
    ):
        adjuntos.borrar_del_disco(ajuste.fichero_ruta)
        correcciones.borrar(
            db,
            registro=ajuste,
            entidad="ajuste_de_entrega",
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
        )

    correcciones.borrar(
        db,
        registro=venta,
        entidad="venta_cosecha",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": venta_id}


# --------------------------------------------------------------------------
# La tabla de S12: lo que se ha vendido, filtrado, con su pie
# --------------------------------------------------------------------------


# Las ocho columnas del contrato (§4, S12), en su orden: «cliente, producto, fecha, cantidad,
# importe conocido, vencimiento, cobrado y pendiente». Las tres últimas claves del diccionario son
# las que se pueden quitar desde la pantalla (columnas configurables, contrato §3), y por eso se
# declaran aparte: una tabla a la que se le puede quitar la fecha deja de servir.
COLUMNAS_DE_LA_TABLA = (
    ("cliente", "tabla_cliente", True),
    ("producto", "tabla_producto", True),
    ("fecha", "tabla_fecha", True),
    ("cantidad", "tabla_cantidad", True),
    ("importe", "tabla_importe", True),
    ("vencimiento", "tabla_vencimiento", True),
    ("cobrado", "tabla_cobrado", True),
    ("pendiente", "tabla_pendiente", True),
    ("estado", "tabla_estado", False),
    ("partida", "tabla_lote", False),
    ("albaran", "tabla_albaran", False),
    ("donde", "tabla_donde", False),
    # **Y la última es la de las acciones** (revisión del T12). La pieza `Tabla`
    # (`web/react/piezas/tabla.js`) pinta una cabecera por columna y, al final de cada fila, la celda de los
    # botones: por eso **quien prepara una tabla escribe una celda menos que columnas tiene**. Aquí no se
    # cumplía —el servidor mandaba doce columnas de datos y la pantalla escribía once celdas más la de los
    # botones— y el resultado era que **el rótulo «De dónde» caía encima de los botones** y el valor de esa
    # columna no se pintaba nunca en el ordenador. Con esta columna, las doce de datos tienen su celda y la
    # decimotercera —la de los botones— lleva el rótulo que ya estaba escrito en los textos.
    #
    # No tiene clave de dato (su valor lo pinta la pieza) y no se puede ordenar: un botón no ordena nada.
    ("acciones", "tabla_acciones", False),
)

# Las que no se pueden ordenar: ordenar por «de dónde» o por la partida no dice nada (y por la columna de
# las acciones, que son botones, menos todavía). El resto se ordena de verdad, en la consulta.
COLUMNAS_SIN_ORDEN = ("donde", "partida", "albaran", "estado", "acciones")

# Las que no se pueden quitar: sin ellas la tabla no contesta a la pregunta que se viene a hacer
# («¿quién me debe y cuánto?»). La de las acciones tampoco se puede quitar: es la que lleva los botones.
COLUMNAS_OBLIGATORIAS = ("cliente", "producto", "fecha", "cantidad", "importe", "pendiente", "acciones")


def _las_filas_de_la_tabla(db, explotacion, lista, *, repartos: dict[int, dict]) -> list[dict]:
    """Una fila por entrega, con las columnas del contrato ya escritas.

    El orden de la lista lo fija quien llama (`ordenar_ventas`), y **las cuentas salen de
    `lo_que_se_sabe_de_una_entrega`**, la misma función que usa la ficha: así la tabla, la ficha y el
    pie no pueden decir cosas distintas del mismo dinero.
    """
    filas = []
    for venta in lista:
        suyo = lo_que_se_sabe_de_una_entrega(
            db, explotacion, venta, reparto=repartos.get(venta.id)
        )
        unidad = (catalogos.unidad_de_venta(venta.unidad) or {}).get("corto", venta.unidad)
        cantidad = (
            f"{legal.formatea_numero(suyo.cantidad_neta, 2)} {unidad}".strip()
            if suyo.cantidad_neta is not None
            else ""
        )
        if suyo.cantidad_neta is not None and suyo.cantidad_neta != venta.cantidad:
            # Si los kilos han cambiado con un ajuste, se dice en su propia columna con la palabra,
            # no con un color: «39.000,00 kg (de 42.000,00)».
            cantidad = (
                f"{cantidad} (de {legal.formatea_numero(venta.cantidad, 2)} {unidad})".strip()
            )
        filas.append(
            {
                "id": venta.id,
                "cliente": venta.comprador or "",
                "contacto_id": venta.contacto_id,
                "producto": venta.producto,
                "variedad": venta.variedad or "",
                "fecha": legal.formatea_fecha(venta.fecha),
                # **Y la fecha con su rótulo delante, compuesta aquí** («Fecha: 10/07/2026»): la tarjeta
                # del móvil la enseña tal cual, y una frase compuesta dentro de un componente es una
                # frase escrita a mano (`AGENTS.md` §3.1).
                "fecha_linea": f"{textos.VENTA['tabla_fecha']}: {legal.formatea_fecha(venta.fecha)}",
                # La fecha **en su forma ordenable** viaja aparte, para que ordenar por fecha ordene
                # por el valor y no por el texto ya formateado (contrato §3). El 15/03/2026 y el
                # 01/02/2027 se ordenan al revés si se comparan como texto.
                "fecha_valor": venta.fecha.isoformat(),
                "cantidad": cantidad,
                "cantidad_valor": suyo.cantidad_neta,
                "unidad": unidad,
                "importe": dinero.formatea(suyo.importe_total),
                "importe_valor": dinero.a_texto(suyo.importe_total),
                "importe_conocido": suyo.importe_total is not None,
                "vencimiento": (
                    legal.formatea_fecha(suyo.vencimiento) if suyo.vencimiento else ""
                ),
                "vencimiento_valor": (
                    suyo.vencimiento.isoformat() if suyo.vencimiento else ""
                ),
                "cobrado": dinero.formatea(suyo.cobrado) if suyo.facturada else "",
                "cobrado_valor": dinero.a_texto(suyo.cobrado) if suyo.facturada else "",
                "pendiente": dinero.formatea(suyo.pendiente) if suyo.facturada else "",
                "pendiente_valor": dinero.a_texto(suyo.pendiente) if suyo.facturada else "",
                "estado": textos.VENTA.get(f"estado_{suyo.estado}", suyo.estado),
                "clave_estado": suyo.estado,
                "estado_vencida": suyo.estado == ventas.VENCIDA,
                "partida": venta.lote or "",
                "albaran": venta.numero_albaran or "",
                "donde": _donde(db, venta),
                "factura_emitida_id": suyo.factura_id,
                "factura_numero": suyo.factura_numero or "",
                "facturada": suyo.facturada,
                # El aviso de «esa entrega ya está en la factura X», **compuesto aquí**: en la pantalla
                # de facturar se enseña al lado de cada entrega que no se puede marcar, y una frase
                # compuesta dentro de un componente sería una frase escrita a mano.
                "aviso_facturada": (
                    textos.mensaje(
                        "D6_esa_entrega_ya_esta_facturada", numero=suyo.factura_numero or ""
                    )
                    if suyo.facturada
                    else ""
                ),
                "ajustes": len(suyo.ajustes),
                "de_que_cosecha": _la_cosecha_de_la_que_sale(db, venta),
                # Y la misma frase con su rótulo, compuesta aquí por el mismo motivo que `fecha_linea`.
                "cosecha_linea": (
                    f"{textos.VENTA['de_que_cosecha']}: {_la_cosecha_de_la_que_sale(db, venta)}"
                    if _la_cosecha_de_la_que_sale(db, venta)
                    else ""
                ),
            }
        )
    return filas


def _ordenar_ventas(lista: list[models.VentaDeCosecha], orden: str | None, sentido: int, db, explotacion):
    """Ordena las entregas **por el valor** de la columna, no por el texto.

    El contrato lo pide con estas palabras (§3): «Fechas y cantidades se ordenan por valor, no por
    texto formateado». Y en este ticket hay una tercera que se ordena por valor de verdad: **el
    importe**, que en la base está guardado como texto decimal (`"9.00"` es mayor que `"121.00"` si
    se compara como texto, y menor si se compara como número). Por eso el importe se ordena aquí, en
    memoria y con `Decimal`: en SQL no se puede, y está dicho en `app/dinero.py`.

    Una entrega **sin importe no se coloca como si valiera cero**: se va al final, se ordene como se
    ordene, porque «no lo sé» no es un número y ponerlo entre los de cero sería mentir sobre dónde
    está. Los empates se rompen por la fecha y el identificador, para que el orden sea **estable**
    (contrato §3) y dos consultas iguales devuelvan lo mismo.
    """
    cuentas = {
        venta.id: lo_que_se_sabe_de_una_entrega(db, explotacion, venta) for venta in lista
    }

    def clave(venta: models.VentaDeCosecha):
        suyo = cuentas[venta.id]
        if orden == "importe":
            valor = suyo.importe_total
            return (valor is None, valor or dinero.CERO, venta.fecha, venta.id)
        if orden == "cantidad":
            valor = suyo.cantidad_neta
            return (valor is None, valor or 0.0, venta.fecha, venta.id)
        if orden == "cliente":
            return ((venta.comprador or "").lower(), venta.fecha, venta.id)
        if orden == "producto":
            return ((venta.producto or "").lower(), venta.fecha, venta.id)
        if orden == "vencimiento":
            return (
                suyo.vencimiento is None,
                suyo.vencimiento or dt.date.min,
                venta.fecha,
                venta.id,
            )
        if orden == "pendiente":
            valor = suyo.pendiente if suyo.facturada else None
            return (valor is None, valor or dinero.CERO, venta.fecha, venta.id)
        if orden == "cobrado":
            valor = suyo.cobrado if suyo.facturada else None
            return (valor is None, valor or dinero.CERO, venta.fecha, venta.id)
        return (venta.fecha, venta.id)

    return sorted(lista, key=clave, reverse=sentido < 0)


@router.get("/ventas/tabla", response_model=TablaDeVentas)
def tabla_de_ventas(
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    q: str | None = None,
    solo: str | None = None,
    orden: str | None = None,
    sentido: int = -1,
    columnas: str | None = None,
) -> TablaDeVentas:
    """La tabla de S12: las entregas del año, filtradas, con el pie y los totales del dinero.

    **El pie lo calcula el servidor sobre el conjunto filtrado** (contrato §3: «las sumas no se
    calculan sobre la página visible: el servidor devuelve el agregado del conjunto filtrado»), y
    sale de las **mismas filas** que se enseñan, así que el pie y el detalle no pueden contradecirse.
    Eso se prueba con números: tres entregas con 1.000 € pendientes dan 1.000 € en el pie y 1.000 €
    al sumar las filas.

    Los filtros son los tres que el ticket necesita de verdad:
      · `q` busca por cliente, producto y número de albarán.
      · `solo=pendientes` deja lo que falta por cobrar, que es la pregunta del día.
      · `solo=sin_importe` deja lo que no tiene precio, que es el A08 y lo que hay que completar.
    """
    campana = _campana(db, explotacion, campana_id)
    consulta = select(models.VentaDeCosecha).where(
        models.VentaDeCosecha.explotacion_id == explotacion.id,
        models.VentaDeCosecha.campana_id == campana.id,
        models.VentaDeCosecha.anulado.is_(False),
    )
    lista = list(db.scalars(consulta))
    total_sin_filtrar = len(lista)

    if q:
        buscado = servicios.clave_de_producto(q)
        lista = [
            venta
            for venta in lista
            if buscado
            and (
                buscado in servicios.clave_de_producto(venta.comprador)
                or buscado in servicios.clave_de_producto(venta.producto)
                or buscado in servicios.clave_de_producto(venta.numero_albaran)
                or buscado in servicios.clave_de_producto(venta.variedad)
            )
        ]

    # El reparto de lo cobrado se calcula **una vez por factura** y no una vez por entrega: es una
    # cuenta de la factura entera (ver `ventas.reparto_de_lo_cobrado`), y hacerla por entrega daría
    # a cada una lo cobrado de todas.
    repartos: dict[int, dict] = {}
    for factura in db.scalars(
        select(models.FacturaEmitida).where(
            models.FacturaEmitida.explotacion_id == explotacion.id,
            models.FacturaEmitida.anulada.is_(False),
        )
    ):
        repartos.update(
            {
                venta_id: valor
                for venta_id, valor in _el_reparto_de_una_factura(
                    db, explotacion=explotacion, factura=factura
                ).items()
            }
        )

    if solo == "pendientes":
        lista = [
            venta
            for venta in lista
            if lo_que_se_sabe_de_una_entrega(
                db, explotacion, venta, reparto=repartos.get(venta.id)
            ).estado
            in ventas.ESTADOS_CON_PENDIENTE
        ]
    elif solo == "sin_importe":
        lista = [
            venta
            for venta in lista
            if lo_que_se_sabe_de_una_entrega(db, explotacion, venta).importe_total is None
        ]

    lista = _ordenar_ventas(lista, orden, sentido, db, explotacion)
    filas = _las_filas_de_la_tabla(db, explotacion, lista, repartos=repartos)

    # Los totales, de las mismas filas que se enseñan.
    cuenta = ventas.cuenta_de_dinero(
        [
            {
                "importe": fila["importe_valor"],
                "cobrado": fila["cobrado_valor"] or None,
                "facturada": fila["facturada"],
            }
            for fila in filas
        ]
    )
    pedidas = [clave.strip() for clave in (columnas or "").split(",") if clave.strip()]
    conocidas = {clave for clave, _, _ in COLUMNAS_DE_LA_TABLA}
    if not pedidas:
        # Sin pedir nada se devuelven **todas**, y no solo las obligatorias: quien no dice qué
        # columnas quiere no está pidiendo una tabla recortada.
        elegidas = [clave for clave, _, _ in COLUMNAS_DE_LA_TABLA]
    else:
        elegidas = [clave for clave in pedidas if clave in conocidas]
        # Una columna obligatoria que se quiera quitar **se queda**: sin ella la tabla no contesta a
        # la pregunta que se viene a hacer, y quitar la fecha dejaría una lista que no se puede leer.
        for obligatoria in COLUMNAS_OBLIGATORIAS:
            if obligatoria not in elegidas:
                elegidas.append(obligatoria)
        # Y el orden es siempre el de la tabla, no el que haya mandado el navegador: dos peticiones
    # con las mismas columnas tienen que devolver la tabla igual.
    orden_de_columnas = [clave for clave, _, _ in COLUMNAS_DE_LA_TABLA]
    elegidas = [clave for clave in orden_de_columnas if clave in set(elegidas)]
    etiquetas = {clave: textos.VENTA[texto] for clave, texto, _ in COLUMNAS_DE_LA_TABLA}
    avisos = []
    if cuenta.sin_importe == 1:
        avisos.append(textos.VENTA["faltan_importes_una"])
    elif cuenta.sin_importe > 1:
        avisos.append(
            textos.VENTA["faltan_importes"].format(cuantas=cuenta.sin_importe)
        )
    return TablaDeVentas(
        columnas=[
            ColumnaDeUnaTabla(
                clave=clave,
                texto=etiquetas[clave],
                ordenable=clave not in COLUMNAS_SIN_ORDEN,
            )
            for clave in elegidas
        ],
        filas=filas,
        pie=_el_pie_de_la_tabla(cuenta),
        avisos=avisos,
        totales=cuenta.como_dict(),
        filtradas=len(filas),
        total=total_sin_filtrar,
    )


def _el_pie_de_la_tabla(cuenta: ventas.CuentaDeDinero) -> str:
    """El pie de la tabla: cuántas entregas, cuánto valen y cuánto falta por cobrar.

    Con las dos formas, singular y plural. «1 entregas» es lo primero que hace desconfiar de un
    programa (`AGENTS.md` §4), y aquí además el pie es una cuenta: si está mal escrito, se duda del
    número que lleva al lado.

    **Y con una tercera forma para cuando no se sabe ningún importe** (revisión del T12). El pie de
    siempre pone `dinero.formatea(None)`, que es «0,00 €»: con las entregas del año sin precio —que es el
    caso A08 del contrato, «cantidad conocida, importe pendiente; **no ingreso cero**»— el número más
    grande de la pantalla decía que se había vendido por cero euros. Un año entero así daría «0,00 €» en
    el pie. Cuando **ninguna** entrega de las que se están contando tiene importe, aquí no se da ningún
    número: se dice que no se sabe, que es la verdad.
    """
    if cuenta.entregas and cuenta.sin_importe == cuenta.entregas:
        plantilla = (
            textos.VENTA["pie_una_sin_importe"]
            if cuenta.entregas == 1
            else textos.VENTA["pie_varias_sin_importe"]
        )
        return plantilla.format(entregas=cuenta.entregas)
    plantilla = textos.VENTA["pie_una"] if cuenta.entregas == 1 else textos.VENTA["pie_varias"]
    return plantilla.format(
        entregas=cuenta.entregas,
        importe=dinero.formatea(cuenta.importe),
        pendiente=dinero.formatea(cuenta.pendiente),
    )


@router.get("/ventas/{venta_id}", response_model=VentaConNombres)
def ver_venta(venta_id: int, explotacion: ExplotacionActual, db: Db) -> VentaConNombres:
    """Una entrega, con sus cuentas.

    Va declarada **después** de `/ventas/tabla` a propósito, y es la misma trampa que ya está
    documentada en `/ventas/informe`: FastAPI resuelve las rutas por orden de declaración, así que si
    esta estuviera antes, `/api/ventas/tabla` se leería como el identificador de una entrega y la
    tabla del contrato devolvería un 422 sin explicar por qué.
    """
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    return con_nombres(db, venta, explotacion=explotacion)


# --------------------------------------------------------------------------
# Los ajustes de una entrega: devoluciones, peso, humedad y calidad
# --------------------------------------------------------------------------


@router.get("/ventas/{venta_id}/ajustes", response_model=list[AjusteDeUnaEntrega])
def listar_los_ajustes(
    venta_id: int, explotacion: ExplotacionActual, db: Db
) -> list[AjusteDeUnaEntrega]:
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    return [
        como_se_ve_un_ajuste(ajuste)
        for ajuste in los_ajustes_de_una_entrega(
            db, explotacion_id=explotacion.id, venta_id=venta.id
        )
    ]


@router.post(
    "/ventas/{venta_id}/ajustes",
    response_model=AjusteDeUnaEntrega,
    status_code=status.HTTP_201_CREATED,
)
def apuntar_un_ajuste(
    venta_id: int,
    datos: AjusteEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> AjusteDeUnaEntrega:
    """Apunta una devolución o un ajuste de peso, humedad o calidad sobre una entrega.

    **Las tres cosas que se exigen, y por qué**, porque son la mitad del ticket («con evidencia y
    origen», dice el contrato): el **tipo** (qué pasó), el **origen** (de dónde sale el número) y el
    **motivo** (la frase del agricultor). Un ajuste sin origen es un número suelto que cambia el
    importe sin decir de dónde sale, y eso es exactamente lo que el contrato prohíbe. Los tres se
    comprueban con palabras, no con un error técnico.

    El papel es **opcional** y se dice cuando no lo hay: en el campo hay veces que el boletín llega
    después, y bloquear el apunte por eso sería impedir apuntar lo que de verdad pasó. Se sube
    después, con `POST /api/ventas/{id}/ajustes/{ajuste_id}/papel`.

    Y tiene que **cambiar algo**: un ajuste que no mueve ni los kilos ni los euros no se apunta, y se
    dice por qué (eso se cuenta en las observaciones de la entrega, que es donde cabe).
    """
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    tipo = datos.tipo.strip()
    if tipo not in ventas.TIPOS_DE_AJUSTE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Ese tipo de apunte no es ninguno de los que se pueden hacer "
                f"({', '.join(ventas.TIPOS_DE_AJUSTE)}). Elige uno de la lista."
            ),
        )
    origen = datos.origen.strip()
    motivo = datos.motivo.strip()
    if origen not in ventas.ORIGENES_DE_UN_AJUSTE or len(motivo) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("D7_el_ajuste_necesita_origen"),
        )
    # La cantidad y el importe ya vienen convertidos **por el esquema** (revisión del T12): antes se
    # convertían aquí y una entrada mal escrita tumbaba el endpoint con un 500 que el móvil reintentaba
    # para siempre. Ahora lo que no vale contesta 422 en la puerta, como en el cobro.
    cantidad = datos.cantidad
    importe = datos.importe
    if cantidad is None and importe is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.VENTA["ajuste_sin_nada"],
        )

    clave = datos.clave_de_reenvio
    if clave:
        ya = db.scalar(
            select(models.AjusteDeEntrega).where(
                models.AjusteDeEntrega.explotacion_id == explotacion.id,
                models.AjusteDeEntrega.clave_de_reenvio == clave,
                models.AjusteDeEntrega.anulado.is_(False),
            )
        )
        if ya is not None:
            # El móvil que reintenta: se devuelve el ajuste que ya estaba, no se apunta otra vez.
            return como_se_ve_un_ajuste(ya)

    # La fecha ya es un `date` (la validó el esquema). Si no viene, **se apunta la de hoy**, que es cuando
    # se está apuntando el ajuste: es lo que hacía antes y sigue siendo lo correcto (el agricultor está
    # contando lo que le han dicho hoy).
    ajuste = models.AjusteDeEntrega(
        explotacion_id=explotacion.id,
        venta_id=venta.id,
        tipo=tipo,
        fecha=datos.fecha or dt.date.today(),
        cantidad=cantidad,
        unidad=(datos.unidad or "").strip() or venta.unidad,
        importe=importe,
        origen=origen,
        motivo=motivo,
        evidencia_descripcion=(datos.evidencia_descripcion or "").strip() or None,
        clave_de_reenvio=clave,
    )
    db.add(ajuste)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="ajuste_de_entrega",
            entidad_id=ajuste.id,
            accion="crear",
            datos={
                "entrega": venta.id,
                "tipo": tipo,
                "origen": origen,
                "cantidad": cantidad,
                "importe": dinero.a_texto(importe),
            },
        )
    )
    db.commit()
    return como_se_ve_un_ajuste(ajuste)


@router.post("/ventas/{venta_id}/ajustes/{ajuste_id}/anular", response_model=AjusteDeUnaEntrega)
def anular_un_ajuste(
    venta_id: int,
    ajuste_id: int,
    datos: dict,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> AjusteDeUnaEntrega:
    """Quita un ajuste del importe, con su motivo y sin borrarlo.

    El papel que traía **no se borra del disco**: sigue siendo el justificante de lo que se apuntó, y
    el programa tiene que poder enseñarlo aunque el ajuste ya no cuente. Es la misma regla del
    cuaderno (nada se borra) aplicada al dinero.
    """
    motivo = str((datos or {}).get("motivo") or "").strip()
    if len(motivo) < 3:
        raise HTTPException(
            status_code=422, detail="Dinos por qué lo quitas, para que quede apuntado."
        )
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    ajuste = obtener_de_la_explotacion(
        db, models.AjusteDeEntrega, ajuste_id, explotacion.id
    )
    if ajuste.venta_id != venta.id:
        # El ajuste no es de esta entrega: se contesta como si no existiera, para no contar de qué
        # entrega es un ajuste de otra.
        raise HTTPException(status_code=404, detail="Ese apunte no está en esta entrega.")
    ajuste.anulado = True
    ajuste.motivo_anulacion = motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="ajuste_de_entrega",
            entidad_id=ajuste.id,
            accion="anular",
            datos={"motivo": motivo},
        )
    )
    db.commit()
    return como_se_ve_un_ajuste(ajuste)


@router.post(
    "/ventas/{venta_id}/ajustes/{ajuste_id}/papel",
    response_model=AjusteDeUnaEntrega,
)
async def subir_el_papel_de_un_ajuste(
    venta_id: int,
    ajuste_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
    fichero: UploadFile = File(...),
) -> AjusteDeUnaEntrega:
    """Sube el papel que demuestra el ajuste: la foto del básculero, el boletín del laboratorio.

    Se guarda igual que los boletines y las facturas (`app/adjuntos.py`): **el fichero va a disco y
    en la base queda la referencia**, y el nombre que manda el navegador **no se usa como ruta** —
    la pone el programa, con el identificador de la finca de carpeta y un nombre al azar. Un nombre
    como `../../app/main.py` escribiría fuera de su carpeta, y hay una prueba que lo comprueba
    mirando el disco.
    """
    venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
    ajuste = obtener_de_la_explotacion(db, models.AjusteDeEntrega, ajuste_id, explotacion.id)
    if ajuste.venta_id != venta.id:
        raise HTTPException(status_code=404, detail="Ese apunte no está en esta entrega.")
    contenido, _ = await adjuntos.leer_el_fichero(fichero, TIPOS_DE_PAPEL_DE_UN_AJUSTE)
    nombre, ruta, tipo, bytes_escritos = adjuntos.guardar_en_disco(
        explotacion_id=explotacion.id,
        prefijo=f"ajuste-{ajuste.id}",
        fichero=fichero,
        contenido=contenido,
        permitidos=TIPOS_DE_PAPEL_DE_UN_AJUSTE,
    )
    anterior = ajuste.fichero_ruta
    ajuste.fichero_nombre = nombre
    ajuste.fichero_ruta = ruta
    ajuste.fichero_tipo = tipo
    ajuste.fichero_bytes = bytes_escritos
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="ajuste_de_entrega",
            entidad_id=ajuste.id,
            accion="subir_papel",
            datos={"fichero": nombre, "bytes": bytes_escritos},
        )
    )
    db.commit()
    if anterior and anterior != ruta:
        # El papel viejo se va del disco **después** de guardar el nuevo: si se borrara antes y el
        # guardado fallara, el agricultor se quedaría sin ninguno de los dos.
        adjuntos.borrar_del_disco(anterior)
    return como_se_ve_un_ajuste(ajuste)


# --------------------------------------------------------------------------
# La factura emitida: nuestra cuenta, que agrupa entregas
# --------------------------------------------------------------------------
#
# **Nada de lo que hay aquí emite un documento con validez ante nadie.** El contrato (§4, S12) lo
# dice con estas palabras: «La emisión fiscal completa requiere especificación normativa propia
# antes de activarse como tal». Esta factura es la cuenta del agricultor —qué entregó, por cuánto y
# qué le deben— y sirve para dos cosas muy concretas: saber a quién reclamar y poder apuntar los
# cobros contra algo. Ni un impuesto, ni un número de serie oficial, ni una palabra de ley.


def como_se_ve_una_factura(db, explotacion, factura: models.FacturaEmitida) -> FacturaEmitidaSalida:
    """La factura con sus líneas, sus cobros y sus cuentas hechas.

    **El total y el cobrado se calculan aquí**, no se leen de una columna escrita a mano: el total es
    la suma de las líneas vivas y el cobrado la suma de lo imputado de los cobros vivos. Es lo que
    hace imposible que la factura y sus entregas cuenten el dinero dos veces.

    **Y una factura quitada sigue diciendo lo que decía** (revisión del T12): se miraban solo sus líneas
    vivas, así que una factura anulada de 121,00 € con una entrega dentro contestaba «0,00 €» y «0
    entregas» aunque sus líneas siguieran en la base con su motivo. Eso es la trampa del A08 —«no lo sé»
    convertido en cero— aplicada a un documento: para mirar dentro de un año qué se emitió y por qué se
    quitó, lo que hay que ver es lo que ponía, con su estado dicho y sin contar en lo que te deben.
    """
    anulada = bool(factura.anulada)
    lineas = las_entregas_de_una_factura(
        db, explotacion_id=explotacion.id, factura_id=factura.id, con_anuladas=anulada
    )
    lineas_vistas: list[LineaDeUnaFacturaEmitida] = []
    total = dinero.CERO
    for linea in lineas:
        entrega = db.get(models.VentaDeCosecha, linea.venta_id)
        # El importe **de ahora** de la entrega, para poder decir la diferencia si la hay. Se calcula
        # con la misma función que todo lo demás; si la entrega ya no está, no hay diferencia que
        # contar y la línea se queda como se emitió.
        ahora = None
        if entrega is not None and entrega.explotacion_id == explotacion.id:
            ahora = lo_que_se_sabe_de_una_entrega(db, explotacion, entrega).importe_total
        suyo = dinero.a_decimal(linea.importe)
        total = dinero.suma(total, suyo)
        lineas_vistas.append(
            LineaDeUnaFacturaEmitida(
                id=linea.id,
                venta_id=linea.venta_id,
                fecha=entrega.fecha if entrega else None,
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                unidad=linea.unidad,
                importe=suyo,
                texto_importe=dinero.formatea(suyo),
                # La línea de una factura quitada se enseña diciendo que está anulada: así no se confunde
                # con una línea viva de una factura viva.
                anulada=bool(linea.anulada),
                entrega_existe=entrega is not None,
                importe_ahora=ahora,
                texto_importe_ahora=dinero.formatea(ahora),
                diferencia=(
                    ahora is not None and suyo is not None and dinero.redondea(ahora) != dinero.redondea(suyo)
                ),
            )
        )

    # **Los cobros que van contra esta factura se buscan por sus aplicaciones** (CRM-01, 11/10/2026), no por
    # la columna del cobro: un ingreso repartido entre varias deudas tiene esa columna **vacía** a propósito
    # —el dinero vive en las aplicaciones—, así que mirando la columna esta factura no vería su parte y
    # volvería a estar pendiente sin que nadie hubiera dejado de cobrar.
    cobros = db.scalars(
        select(models.Cobro)
        .join(models.AplicacionDeUnCobro, models.AplicacionDeUnCobro.cobro_id == models.Cobro.id)
        .where(
            models.Cobro.explotacion_id == explotacion.id,
            models.AplicacionDeUnCobro.factura_emitida_id == factura.id,
            models.AplicacionDeUnCobro.anulado.is_(False),
            models.Cobro.anulado.is_(False),
        )
        .order_by(models.Cobro.fecha.asc(), models.Cobro.id.asc())
    )
    cobros_vistos = [como_se_ve_un_cobro(db, explotacion, cobro) for cobro in cobros]
    # Y el cobrado, de la regla única: la suma de las aplicaciones vivas contra esta factura.
    cobrado = lo_cobrado_de_una_factura(db, explotacion_id=explotacion.id, factura_id=factura.id)
    # Una factura quitada **no se debe**: se enseña lo que decía (su total y sus líneas) y su estado, pero
    # el pendiente es cero de verdad, no un cero por no mirarlo.
    pendiente = dinero.CERO if anulada else ventas.pendiente_de(total, cobrado)
    estado = (
        "anulada"
        if anulada
        else ventas.estado_de_una_entrega(
            importe=total,
            cobrado=cobrado,
            facturada=True,
            vencimiento=factura.vencimiento,
            hoy=dt.date.today(),
        )
    )
    return FacturaEmitidaSalida(
        id=factura.id,
        campana_id=factura.campana_id,
        numero=factura.numero,
        fecha=factura.fecha,
        vencimiento=factura.vencimiento,
        cliente=factura.cliente,
        cliente_nif=factura.cliente_nif,
        contacto_id=factura.contacto_id,
        importe_total=dinero.redondea(total),
        texto_total=dinero.formatea(total),
        cobrado=dinero.redondea(cobrado),
        texto_cobrado=dinero.formatea(cobrado),
        pendiente=pendiente,
        texto_pendiente=dinero.formatea(pendiente),
        estado=estado,
        etiqueta_estado=textos.VENTA.get(f"estado_{estado}", estado),
        titulo=_el_titulo_de_una_factura(factura),
        # La fecha con su rótulo («Fecha: 20/07/2026»), compuesta aquí y no en la pantalla.
        fecha_linea=(
            f"{textos.VENTA['tabla_fecha']}: {legal.formatea_fecha(factura.fecha)}"
            if factura.fecha
            else ""
        ),
        # Y el nombre con lo que queda por cobrar, que es lo que hace falta para **elegir** una factura en
        # la lista de un cobro: elegir a ciegas entre cuatro números de factura no es elegir.
        titulo_con_pendiente=f"{_el_titulo_de_una_factura(factura)} · "
        f"{textos.FACTURA_EMITIDA['pendiente']}: {dinero.formatea(pendiente)}",
        anulada=factura.anulada,
        motivo_anulacion=factura.motivo_anulacion,
        notas=factura.notas,
        lineas=lineas_vistas,
        cobros=cobros_vistos,
        entregas=len(lineas_vistas),
    )


def como_se_ve_un_cobro(db, explotacion, cobro: models.Cobro) -> CobroDeUnaFactura:
    """Un cobro, con **a qué facturas va** y lo que sobra dicho por separado (CRM-01, 11/10/2026).

    Las cifras salen de **las aplicaciones**, que es donde vive el reparto: `imputado` es lo que suman y
    `sin asignar` lo que falta hasta el importe del cobro. Un cobro sin ninguna aplicación es dinero que
    todavía no se sabe a qué va, y se dice así —«sin asignar», no «sobra»—.
    """
    importe = dinero.a_decimal(cobro.importe)
    suyas = list(
        db.scalars(
            select(models.AplicacionDeUnCobro)
            .where(
                models.AplicacionDeUnCobro.cobro_id == cobro.id,
                models.AplicacionDeUnCobro.anulado.is_(False),
            )
            .order_by(models.AplicacionDeUnCobro.id)
        )
    )
    aplicaciones_vistas: list[AplicacionDeUnCobroSalida] = []
    for aplicacion in suyas:
        su_factura = db.get(models.FacturaEmitida, aplicacion.factura_emitida_id)
        # El aislamiento no se supone: si la base se editara a mano, una aplicación de otra finca no se
        # enseña (es la misma comprobación que hace este mismo sitio con la factura del cobro).
        if su_factura is not None and su_factura.explotacion_id != explotacion.id:
            continue
        aplicaciones_vistas.append(
            AplicacionDeUnCobroSalida(
                factura_emitida_id=aplicacion.factura_emitida_id,
                factura_numero=su_factura.numero if su_factura else None,
                importe=dinero.a_decimal(aplicacion.importe),
                texto_importe=dinero.formatea(aplicacion.importe),
            )
        )
    imputado = dinero.suma(*[v.importe for v in aplicaciones_vistas]) if aplicaciones_vistas else None
    sobrante = None
    if not aplicaciones_vistas:
        # Sin ninguna aplicación, todo el dinero está sin asignar: no es que sobre, es que no se sabe a
        # qué va.
        sobrante = importe
    elif importe is not None and imputado is not None:
        sobrante = dinero.resta(importe, imputado)
    factura = (
        db.get(models.FacturaEmitida, cobro.factura_emitida_id)
        if cobro.factura_emitida_id is not None
        else None
    )
    if factura is not None and factura.explotacion_id != explotacion.id:
        # Un cobro nunca puede apuntar a una factura de otra finca, pero si la base se editara a
        # mano, esto impide que se enseñe: el aislamiento no se supone, se comprueba.
        factura = None
    return CobroDeUnaFactura(
        id=cobro.id,
        fecha=cobro.fecha,
        # La fecha con su rótulo del servidor, compuesta aquí: la ficha la enseña tal cual.
        fecha_linea=(
            f"{textos.COBRO['fecha']}: {legal.formatea_fecha(cobro.fecha)}" if cobro.fecha else ""
        ),
        importe=importe,
        texto_importe=dinero.formatea(importe),
        importe_imputado=imputado,
        aplicaciones=aplicaciones_vistas,
        texto_imputado=dinero.formatea(imputado) if imputado is not None else "",
        sin_asignar=sobrante,
        texto_sin_asignar=dinero.formatea(sobrante) if sobrante else "",
        factura_emitida_id=factura.id if factura else None,
        factura_numero=_como_se_llama_una_factura(factura) if factura else None,
        cliente=cobro.cliente,
        contacto_id=cobro.contacto_id,
        forma=cobro.forma,
        etiqueta_forma=textos.COBRO["formas"].get(cobro.forma, cobro.forma),
        referencia=cobro.referencia,
        notas=cobro.notas,
        anulado=cobro.anulado,
        motivo_anulacion=cobro.motivo_anulacion,
    )


@router.get("/facturas-emitidas", response_model=list[FacturaEmitidaSalida])
def listar_facturas_emitidas(
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
    solo: str | None = None,
) -> list[FacturaEmitidaSalida]:
    """Las facturas nuestras del año, de la más nueva a la más vieja.

    `solo=pendientes` deja las que todavía tienen algo por cobrar, que es la lista que se mira para
    saber a quién hay que llamar.
    """
    consulta = select(models.FacturaEmitida).where(
        models.FacturaEmitida.explotacion_id == explotacion.id,
        models.FacturaEmitida.anulada.is_(False),
    )
    if campana_id is not None:
        consulta = consulta.where(models.FacturaEmitida.campana_id == campana_id)
    facturas = [
        como_se_ve_una_factura(db, explotacion, factura)
        for factura in db.scalars(consulta)
    ]
    facturas.sort(key=lambda f: (f.fecha or dt.date.min, f.id), reverse=True)
    if solo == "pendientes":
        facturas = [f for f in facturas if f.pendiente and f.pendiente > 0]
    return facturas


@router.post(
    "/facturas-emitidas",
    response_model=FacturaEmitidaSalida,
    status_code=status.HTTP_201_CREATED,
)
def crear_factura_emitida(
    datos: FacturaEmitidaEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> FacturaEmitidaSalida:
    """Junta una o varias entregas en una factura nuestra. **Y no cuenta el dinero dos veces.**

    Las tres guardas, y cada una dice lo que pasa con palabras:

      1. **Al menos una entrega.** Una factura sin nada dentro no es una factura: no dice qué se
         vendió ni a quién cobrarle.
      2. **Ninguna entrega puede estar ya en otra factura viva.** Si lo está, se contesta 422 y se
         dice **en qué factura está**, para que el agricultor no tenga que buscarla. Además, la base
         tiene un índice único que lo impide aunque esta comprobación se olvidara: la misma entrega
         viva no puede estar en dos facturas vivas, y por eso agrupar no duplica ingresos.
      3. **Todas tienen que tener importe.** Una entrega sin precio no se puede facturar (es el A08:
         los kilos se saben y el importe está pendiente), y se dice por qué y qué hacer: ponerle el
         importe.

    El importe de la factura **es la suma de sus líneas**, calculada aquí: no se recibe de fuera, así
    que no puede solaparse con las entregas que la componen.
    """
    if datos.clave_de_reenvio:
        ya = db.scalar(
            select(models.FacturaEmitida).where(
                models.FacturaEmitida.explotacion_id == explotacion.id,
                models.FacturaEmitida.clave_de_reenvio == datos.clave_de_reenvio,
                models.FacturaEmitida.anulada.is_(False),
            )
        )
        if ya is not None:
            return como_se_ve_una_factura(db, explotacion, ya)

    if not datos.entregas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("D10_no_hay_nada_que_facturar"),
        )
    campana = _campana(db, explotacion, datos.campana_id)
    if datos.contacto_id is not None:
        obtener_de_la_explotacion(db, models.Contacto, datos.contacto_id, explotacion.id)

    entregas: list[models.VentaDeCosecha] = []
    vistas: set[int] = set()
    for venta_id in datos.entregas:
        venta = obtener_de_la_explotacion(db, models.VentaDeCosecha, venta_id, explotacion.id)
        # **La misma entrega dos veces en la misma petición tampoco.** Sin esta comprobación, la segunda
        # línea tropezaría con el índice único de la base y el agricultor vería un fallo del programa en vez
        # de que se lo digan con palabras (y la primera línea se quedaría a medias). Lo encontró una prueba
        # de este mismo ticket, que es exactamente para lo que está.
        if venta.id in vistas:
            # **Un mensaje propio, y no el de «ya está facturada»** (revisión del T12): antes salía
            # «Esa entrega ya está dentro de la factura .» —con el hueco en blanco donde iba el número— y
            # además decía algo que no era: esa entrega no está en ninguna factura, lo que pasa es que viene
            # dos veces en la misma petición. Se dice eso.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje("D14_esa_entrega_viene_repetida"),
            )
        vistas.add(venta.id)
        if venta.anulado:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Una de esas entregas está anulada, así que no se puede facturar.",
            )
        linea = _la_linea_de_factura_de_una_entrega(
            db, explotacion_id=explotacion.id, venta_id=venta.id
        )
        if linea is not None:
            otra = db.get(models.FacturaEmitida, linea.factura_emitida_id)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje(
                    "D6_esa_entrega_ya_esta_facturada",
                    numero=_como_se_llama_una_factura(otra),
                ),
            )
        suyo = lo_que_se_sabe_de_una_entrega(db, explotacion, venta)
        if suyo.importe_total is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje("D5_sin_importe_no_se_puede_facturar"),
            )
        entregas.append(venta)

    factura = models.FacturaEmitida(
        explotacion_id=explotacion.id,
        campana_id=campana.id,
        numero=(datos.numero or "").strip() or None,
        fecha=datos.fecha,
        vencimiento=datos.vencimiento,
        cliente=(datos.cliente or "").strip() or None,
        cliente_nif=(datos.cliente_nif or "").strip() or None,
        contacto_id=datos.contacto_id,
        notas=datos.notas,
        clave_de_reenvio=datos.clave_de_reenvio,
        importe_total=dinero.CERO,
    )
    db.add(factura)
    db.flush()

    total = dinero.CERO
    for venta in entregas:
        suyo = lo_que_se_sabe_de_una_entrega(db, explotacion, venta)
        db.add(
            models.LineaDeFacturaEmitida(
                explotacion_id=explotacion.id,
                factura_emitida_id=factura.id,
                venta_id=venta.id,
                # La fotografía del día que se factura: si mañana se corrige la entrega, la factura
                # no cambia sola (y la pantalla dirá que hay una diferencia).
                descripcion=venta.producto,
                cantidad=suyo.cantidad_neta,
                unidad=venta.unidad,
                importe=suyo.importe_total,
            )
        )
        total = dinero.suma(total, suyo.importe_total)
    factura.importe_total = dinero.redondea(total)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="factura_emitida",
            entidad_id=factura.id,
            accion="crear",
            datos={
                "entregas": [venta.id for venta in entregas],
                "importe_total": dinero.a_texto(factura.importe_total),
            },
        )
    )
    db.commit()
    return como_se_ve_una_factura(db, explotacion, factura)


@router.get("/facturas-emitidas/{factura_id}", response_model=FacturaEmitidaSalida)
def ver_factura_emitida(
    factura_id: int, explotacion: ExplotacionActual, db: Db
) -> FacturaEmitidaSalida:
    factura = obtener_de_la_explotacion(
        db, models.FacturaEmitida, factura_id, explotacion.id
    )
    return como_se_ve_una_factura(db, explotacion, factura)


@router.post("/facturas-emitidas/{factura_id}/anular", response_model=FacturaEmitidaSalida)
def anular_factura_emitida(
    factura_id: int,
    datos: dict,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> FacturaEmitidaSalida:
    """Quita la factura y **deja sus entregas libres** para volver a facturarlas.

    Con dos condiciones, y las dos son para que no desaparezca dinero de las cuentas:

      · **Si tiene cobros apuntados, no se quita** (409). Los cobros apuntan a la factura; si la
        factura desapareciera, ese dinero se quedaría sin saber de dónde viene. Se dice qué hacer:
        quitar primero los cobros (que también dejan su motivo apuntado) y después la factura.
      · **Las líneas se anulan, no se borran** (con su motivo), y al anularse la entrega queda otra
        vez libre: es lo que permite rehacer la factura con las entregas que sean, que es el caso de
        «me equivoqué al agrupar».
    """
    motivo = str((datos or {}).get("motivo") or "").strip()
    if len(motivo) < 3:
        raise HTTPException(
            status_code=422, detail="Dinos por qué la quitas, para que quede apuntado."
        )
    factura = obtener_de_la_explotacion(
        db, models.FacturaEmitida, factura_id, explotacion.id
    )
    cobrado = lo_cobrado_de_una_factura(
        db, explotacion_id=explotacion.id, factura_id=factura.id
    )
    tiene_cobros = db.scalar(
        select(models.Cobro.id).where(
            models.Cobro.explotacion_id == explotacion.id,
            models.Cobro.factura_emitida_id == factura.id,
            models.Cobro.anulado.is_(False),
        )
    )
    if tiene_cobros is not None or cobrado > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("D9_esa_factura_no_se_puede_quitar"),
        )
    factura.anulada = True
    factura.motivo_anulacion = motivo
    for linea in las_entregas_de_una_factura(
        db, explotacion_id=explotacion.id, factura_id=factura.id
    ):
        linea.anulada = True
        linea.motivo_anulacion = motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="factura_emitida",
            entidad_id=factura.id,
            accion="anular",
            datos={"motivo": motivo},
        )
    )
    db.commit()
    return como_se_ve_una_factura(db, explotacion, factura)


# --------------------------------------------------------------------------
# Los cobros: el dinero que entra, aunque sea una parte
# --------------------------------------------------------------------------


@router.get("/cobros", response_model=list[CobroDeUnaFactura])
def listar_cobros(
    explotacion: ExplotacionActual,
    db: Db,
    solo: str | None = None,
) -> list[CobroDeUnaFactura]:
    """El dinero que ha entrado, del más nuevo al más viejo.

    `solo=sin_asignar` deja los que todavía no se sabe qué factura saldan: es la lista que el
    contrato pide en su panel de Economía («pagos sin factura quedan por conciliar»).
    """
    cobros = list(
        db.scalars(
            select(models.Cobro)
            .where(
                models.Cobro.explotacion_id == explotacion.id,
                models.Cobro.anulado.is_(False),
            )
            .order_by(models.Cobro.fecha.desc(), models.Cobro.id.desc())
        )
    )
    vistos = [como_se_ve_un_cobro(db, explotacion, cobro) for cobro in cobros]
    if solo == "sin_asignar":
        # **«Sin asignar» es «sin ninguna aplicación», no «sin la columna de la factura»** (CRM-01, 11/10/2026).
        # Un cobro repartido entre varias deudas tiene `factura_emitida_id` vacío **a propósito** —el dinero
        # vive en las aplicaciones—, así que mirando esa columna el agricultor veía su ingreso recién
        # repartido en la lista del dinero que «todavía no se sabe de qué factura es», justo debajo de la
        # frase que dice que está esperando a que se le diga. Es la misma trampa que la ficha del cobro y el
        # `cobrado` de la factura: la mitad que lee el dato viejo no se entera del nuevo.
        vistos = [cobro for cobro in vistos if not cobro.aplicaciones]
    return vistos


def _la_factura_a_la_que_se_imputa(db, explotacion, factura_id: int | None):
    """La factura que salda un cobro, comprobando que es de esta finca y que sigue viva."""
    if factura_id is None:
        return None
    factura = obtener_de_la_explotacion(db, models.FacturaEmitida, factura_id, explotacion.id)
    if factura.anulada:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Esa factura está quitada, así que este cobro no puede ir contra ella.",
        )
    return factura


def _imputar(db, explotacion, cobro: models.Cobro, factura) -> tuple[Decimal, Decimal]:
    """Pone lo que de este cobro va a esa factura. Devuelve `(imputado, sobrante)`.

    **Se llama siempre que cambia el cobro o su factura**, y el número que deja guardado se calcula
    con lo que se debe **en ese momento**: con 121 facturados y 40 ya cobrados, un cobro de 100 se
    imputa por 81 y deja 19 sin asignar. Guardarlo y no recalcularlo cada vez es a propósito: si
    mañana se corrige la factura, el reparto que se hizo ese día no puede cambiar solo.
    """
    if factura is None:
        cobro.factura_emitida_id = None
        cobro.importe_imputado = None
        # **Y su aplicación se retira**, que es lo que devuelve la deuda a estar pendiente. No se borra: se
        # marca anulada con su motivo, como manda el patrón que documentan las referencias (deshacer
        # conciliación desvincula y no destruye el documento).
        _retirar_la_aplicacion(db, cobro, motivo="este cobro ya no va contra ninguna factura")
        return (dinero.CERO, dinero.a_decimal(cobro.importe) or dinero.CERO)
    cobro.factura_emitida_id = factura.id
    ya_cobrado = lo_cobrado_de_una_factura(
        db,
        explotacion_id=explotacion.id,
        factura_id=factura.id,
        # Lo cobrado por **otros** cobros: ver el porqué en `lo_cobrado_de_una_factura`.
        sin_este_cobro=cobro.id,
    )
    pendiente = ventas.pendiente_de(factura.importe_total, ya_cobrado)
    imputado, sobrante = ventas.reparto_de_un_cobro(cobro.importe, pendiente)
    cobro.importe_imputado = imputado
    _dejar_la_aplicacion(db, explotacion, cobro, factura, imputado)
    return (imputado, sobrante)


def _dejar_la_aplicacion(db, explotacion, cobro: models.Cobro, factura, imputado: Decimal) -> None:
    """Deja **una** aplicación viva de este cobro contra esa factura, por ese importe.

    Es el camino de siempre (un cobro que salda **una** factura) el que pasa por aquí. El reparto entre
    varias deudas se apunta con `aplicaciones` en el alta y deja **una fila por factura**.

    Si el importe imputado es cero —el caso de un cobro que llega cuando ya no se debe nada— **no se deja
    aplicación**: el dinero está sin asignar y una fila de cero euros no diría nada.
    """
    ya = db.scalar(
        select(models.AplicacionDeUnCobro).where(
            models.AplicacionDeUnCobro.cobro_id == cobro.id,
            models.AplicacionDeUnCobro.factura_emitida_id == factura.id,
            models.AplicacionDeUnCobro.anulado.is_(False),
        )
    )
    if imputado is None or imputado <= 0:
        if ya is not None:
            db.delete(ya)
        return
    if ya is None:
        db.add(
            models.AplicacionDeUnCobro(
                explotacion_id=explotacion.id,
                cobro_id=cobro.id,
                factura_emitida_id=factura.id,
                importe=imputado,
            )
        )
    else:
        ya.importe = imputado


def _repartir_el_cobro(db, explotacion, cobro: models.Cobro, aplicaciones) -> tuple[Decimal, Decimal]:
    """Reparte un cobro entre **varias** facturas. Devuelve `(lo imputado, lo que queda sin asignar)`.

    Es lo que el encargo de CRM-01 pide con números: *«un cobro de 350 aplicado a dos deudas 100/250, las
    aplicaciones suman 350 y el saldo sin aplicar queda en 0»*. Las dos invariantes que documentan las
    referencias que estudió el ticket (ERPNext: *«the total allocated amount can be less than or equal to
    the payment, but it cannot exceed the available amount»*) se comprueban aquí, y con palabras:

      · **Entre todas no se reparte más de lo que entró.** Si suman más que el importe del cobro, no se
        apunta nada y se dice cuánto es lo que sobra de la suma.
      · **A una factura no se le aplica más de lo que debe.** Lo que se debe se calcula **en este momento**
        y contando lo que ya se ha aplicado en esta misma petición, así que dos filas para la misma factura
        no pueden pasar de su pendiente entre las dos.
      · Y lo que **no** se reparte queda sin asignar, que es un dato: no se pierde ni se mete en ninguna
        factura a la fuerza.
    """
    importe_del_cobro = dinero.a_decimal(cobro.importe) or dinero.CERO
    ya_repartido: dict[int, Decimal] = {}
    for aplicacion in aplicaciones:
        su_importe = dinero.redondea(dinero.a_decimal(aplicacion.importe) or dinero.CERO)
        if su_importe <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Una parte del cobro no puede ser de cero euros ni negativa.",
            )
        la_factura = _la_factura_a_la_que_se_imputa(db, explotacion, aplicacion.factura_emitida_id)
        pendiente = ventas.pendiente_de(
            la_factura.importe_total,
            dinero.suma(
                lo_cobrado_de_una_factura(
                    db, explotacion_id=explotacion.id, factura_id=la_factura.id
                ),
                ya_repartido.get(la_factura.id, dinero.CERO),
            ),
        )
        if pendiente is None or su_importe > pendiente:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"A la factura {la_factura.numero or la_factura.id} no se le pueden aplicar "
                    f"{dinero.formatea(su_importe)}: solo le quedan "
                    f"{dinero.formatea(pendiente or dinero.CERO)} por cobrar."
                ),
            )
        ya_repartido[la_factura.id] = dinero.suma(
            ya_repartido.get(la_factura.id, dinero.CERO), su_importe
        )
        db.add(
            models.AplicacionDeUnCobro(
                explotacion_id=explotacion.id,
                cobro_id=cobro.id,
                factura_emitida_id=la_factura.id,
                importe=su_importe,
            )
        )
    total = dinero.suma(*ya_repartido.values()) if ya_repartido else dinero.CERO
    if total > importe_del_cobro:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"El reparto suma {dinero.formatea(total)} y el cobro es de "
                f"{dinero.formatea(importe_del_cobro)}: no se puede repartir más de lo que entró."
            ),
        )
    # Una sola factura: se deja también en las columnas de siempre para que las pantallas que las leen no se
    # queden sin el dato. Con varias, esas columnas van vacías a propósito: el dinero vive en las
    # aplicaciones, y poner una de las facturas ahí haría creer que el cobro es entero suyo.
    if len(ya_repartido) == 1:
        cobro.factura_emitida_id = next(iter(ya_repartido))
        cobro.importe_imputado = total
    return (total, dinero.redondea(importe_del_cobro - total))


def _retirar_la_aplicacion(db, cobro: models.Cobro, *, motivo: str) -> None:
    """Marca anuladas las aplicaciones vivas de ese cobro, con su motivo, en vez de borrarlas."""
    suyas = db.scalars(
        select(models.AplicacionDeUnCobro).where(
            models.AplicacionDeUnCobro.cobro_id == cobro.id,
            models.AplicacionDeUnCobro.anulado.is_(False),
        )
    )
    for aplicacion in suyas:
        aplicacion.anulado = True
        aplicacion.motivo_anulacion = motivo


@router.post("/cobros", response_model=RespuestaDeUnCobro, status_code=status.HTTP_201_CREATED)
def apuntar_un_cobro(
    datos: CobroEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> RespuestaDeUnCobro:
    """Apunta un cobro. **Puede ser una parte, y no crea ninguna factura** (caso A06).

    Las dos mitades del A06 se ven aquí:

      · Con una factura de 121 € facturados y un primer cobro de 40 €, el pendiente queda en 81 €
        exactos, y se contesta esa cifra para que la pantalla no tenga que hacer la cuenta (en el
        navegador el dinero perdería céntimos: todo número de JavaScript es de coma flotante).
      · **Conciliar un segundo importe no crea una segunda factura.** No hay ninguna línea de código
        en este router que cree una `FacturaEmitida` a partir de un cobro, y hay una prueba que
        cuenta las facturas antes y después para que siga siendo verdad.

    Un cobro mayor que lo que se debe **no se bloquea** (el agricultor puede haber cobrado intereses o
    haberse equivocado al teclear el total): se apunta entero, se imputa lo que se debe y lo que
    sobra queda dicho como «sin conciliar», con su cifra. Lo que no se hace nunca es dejar la factura
    con pendiente negativo.
    """
    # **Lo que se comprueba es lo que se va a guardar, no lo que llega** (revisión del T12). Antes se miraba
    # el importe tal cual venía, así que un cobro de `0.004` pasaba el filtro (es mayor que cero) y luego se
    # guardaba redondeado al céntimo: `"0.00"`. Un renglón de cero euros en la lista de lo que ha entrado es
    # justo lo que el aviso de abajo dice que no se admite.
    importe = dinero.redondea(dinero.a_decimal(datos.importe))
    if importe is None or importe <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("D8_el_cobro_tiene_que_ser_mayor_que_cero"),
        )
    if datos.clave_de_reenvio:
        ya = db.scalar(
            select(models.Cobro).where(
                models.Cobro.explotacion_id == explotacion.id,
                models.Cobro.clave_de_reenvio == datos.clave_de_reenvio,
                models.Cobro.anulado.is_(False),
            )
        )
        if ya is not None:
            # El móvil que reintenta: se devuelve el cobro que ya estaba. Es la respuesta estable
            # que pide el contrato («reenviar el mismo comando devuelve su resultado»).
            return RespuestaDeUnCobro(
                cobro=como_se_ve_un_cobro(db, explotacion, ya),
                ya_estaba=True,
                factura=(
                    como_se_ve_una_factura(
                        db, explotacion, db.get(models.FacturaEmitida, ya.factura_emitida_id)
                    )
                    if ya.factura_emitida_id
                    else None
                ),
            )
    if datos.contacto_id is not None:
        obtener_de_la_explotacion(db, models.Contacto, datos.contacto_id, explotacion.id)
    if datos.forma not in ventas.FORMAS_DE_COBRO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Esa forma de cobro no es ninguna de las que hay "
                f"({', '.join(ventas.FORMAS_DE_COBRO)}). Elige una de la lista."
            ),
        )

    factura = _la_factura_a_la_que_se_imputa(db, explotacion, datos.factura_emitida_id)
    # **El reparto entre varias deudas** (CRM-01, 11/10/2026): o viene una factura suelta —el camino de
    # siempre— o viene la lista de a qué va cada parte. Las dos cosas a la vez no: se contesta 422 en vez de
    # elegir por el agricultor cuál de las dos manda.
    if datos.aplicaciones and datos.factura_emitida_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "O me dices a qué factura va el cobro, o me dices cómo se reparte entre varias; "
                "las dos cosas a la vez no, porque no sé cuál manda."
            ),
        )
    cobro = models.Cobro(
        explotacion_id=explotacion.id,
        fecha=datos.fecha,
        importe=importe,
        cliente=(datos.cliente or "").strip() or None,
        contacto_id=datos.contacto_id,
        forma=datos.forma,
        referencia=(datos.referencia or "").strip() or None,
        notas=datos.notas,
        clave_de_reenvio=datos.clave_de_reenvio,
    )
    db.add(cobro)
    # **El `try` envuelve también el `flush`** (CRM-01, 11/10/2026), y esto se aprendió midiendo: el choque
    # con el índice de la clave salta **al insertar** —que es lo que hace `flush`—, no al confirmar, así que
    # un `try` alrededor del `commit` no recogía nada y el `IntegrityError` seguía saliendo sin manejar. Se
    # envolvió primero solo el `commit`, y la prueba de concurrencia siguió fallando **2 de cada 6 vueltas**
    # hasta que se envolvió lo que de verdad falla.
    try:
        db.flush()
        if datos.aplicaciones:
            imputado, sobrante = _repartir_el_cobro(db, explotacion, cobro, datos.aplicaciones)
        else:
            imputado, sobrante = _imputar(db, explotacion, cobro, factura)
        _el_rastro_de_un_cobro(
            db,
            explotacion.id,
            cobro,
            accion="crear",
            datos={
                "importe": dinero.a_texto(importe),
                "factura": factura.id if factura else None,
                "imputado": dinero.a_texto(imputado),
            },
        )
        db.commit()
    except IntegrityError:
        # **La carrera, resuelta como si la hubiera encontrado la búsqueda**: dos envíos a la vez con la misma
        # clave pueden pasar los dos por la comprobación de arriba antes de que ninguno haya escrito, y lo que
        # los separa es el índice único de la base. El móvil que reintenta recibe **su cobro**, no un 500.
        db.rollback()
        ya = db.scalar(
            select(models.Cobro).where(
                models.Cobro.explotacion_id == explotacion.id,
                models.Cobro.clave_de_reenvio == datos.clave_de_reenvio,
            )
        )
        if ya is None:
            raise
        return RespuestaDeUnCobro(
            cobro=como_se_ve_un_cobro(db, explotacion, ya),
            ya_estaba=True,
            factura=(
                como_se_ve_una_factura(
                    db, explotacion, db.get(models.FacturaEmitida, ya.factura_emitida_id)
                )
                if ya.factura_emitida_id
                else None
            ),
        )

    avisos: list[str] = []
    if factura is not None and sobrante > 0:
        avisos.append(
            textos.mensaje(
                "D4_cobro_mas_que_lo_que_se_debe",
                importe=dinero.formatea(importe),
                pendiente=dinero.formatea(
                    dinero.suma(dinero.a_decimal(factura.importe_total), -(imputado or dinero.CERO))
                ),
                imputado=dinero.formatea(imputado),
                sobrante=dinero.formatea(sobrante),
            )
        )
    vista = como_se_ve_una_factura(db, explotacion, factura) if factura else None
    if vista is not None:
        # Y la cuenta de cómo queda la factura, dicha con palabras y con el número exacto. Es lo
        # único que el agricultor necesita leer después de apuntar un pago parcial.
        if vista.pendiente and vista.pendiente > 0:
            avisos.append(
                textos.mensaje(
                    "D3_falta_por_cobrar",
                    cobrado=vista.texto_cobrado,
                    total=vista.texto_total,
                    pendiente=vista.texto_pendiente,
                )
            )
        else:
            avisos.append(textos.COBRO["queda_cobrada"].format(numero=vista.numero or ""))
    return RespuestaDeUnCobro(
        cobro=como_se_ve_un_cobro(db, explotacion, cobro),
        ya_estaba=False,
        avisos=[aviso for aviso in avisos if aviso],
        factura=vista,
    )


def _el_rastro_de_un_cobro(
    db, explotacion_id: int, cobro: models.Cobro, *, accion: str, datos: dict
) -> None:
    """Apunta en el rastro lo que ha pasado con un cobro.

    Existe por dos motivos que se juntan. El primero es de siempre en este proyecto: **una sola forma de
    escribir el rastro de un cobro**, para que sus tres momentos (apuntarlo, conciliarlo y anularlo) dejen
    la misma clase de fila y no se separen con el tiempo.

    El segundo se descubrió midiendo: la etiqueta de la acción es un texto que tiene que **caber** en su
    columna, y el guardián que lo vigila la lee escrita **entera y pegada a su campo**. Con el ternario que
    había antes —una etiqueta u otra según haya factura— ese guardián veía la primera y la segunda se
    quedaba sin vigilar. Al pasar la etiqueta por aquí, cada llamada lleva su literal entero y las dos
    quedan a la vista de quien las vigila.
    """
    db.add(
        models.Auditoria(
            explotacion_id=explotacion_id,
            entidad="cobro",
            entidad_id=cobro.id,
            accion=accion,
            datos=datos,
        )
    )


@router.post("/cobros/{cobro_id}/conciliar", response_model=RespuestaDeUnCobro)
def conciliar_un_cobro(
    cobro_id: int,
    datos: ConciliacionEntrada,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> RespuestaDeUnCobro:
    """Dice a qué factura salda un cobro, o le quita la asignación.

    **Deshacer la conciliación no borra el movimiento.** El cobro sigue apuntado con su importe y su
    fecha, solo deja de apuntar a una factura: es la regla que el contrato pide para la conciliación
    («Deshacer conciliación no borra el movimiento original») y aquí vale igual, aunque la
    conciliación muchos a muchos sea del ticket T20.

    Y **no crea ninguna factura**: si no hay ninguna contra la que imputar, el dinero se queda sin
    asignar y se dice. Es la otra mitad del A06.
    """
    cobro = obtener_de_la_explotacion(db, models.Cobro, cobro_id, explotacion.id)
    if cobro.anulado:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ese cobro está quitado, así que no se puede asignar a ninguna factura.",
        )
    factura = _la_factura_a_la_que_se_imputa(db, explotacion, datos.factura_emitida_id)
    imputado, sobrante = _imputar(db, explotacion, cobro, factura)
    # **La etiqueta del rastro, en dos literales enteros y no dentro de una expresión**, y esto no es
    # estética: el guardián que vigila que las etiquetas quepan en su columna
    # (`tests/test_las_etiquetas_del_rastro_caben.py`) las lee buscando la etiqueta pegada a su nombre de
    # campo, así que un ternario —una etiqueta sí, y si no otra— le dejaba ver la primera y **la segunda se
    # quedaba sin vigilar**. Lo encontró el propio ticket al medir sus etiquetas: una etiqueta que el
    # guardián no ve es una etiqueta que nadie vigila, y ese guardián existe justo porque una etiqueta de
    # más de 30 caracteres rompía la operación entera en PostgreSQL.
    #
    # (Las comillas de este comentario son simples a propósito: con comillas dobles, la etiqueta de ejemplo
    # de aquí dentro se contaría como una etiqueta más del programa, y ensuciaría la cuenta de quien
    # vigila. Se probó y se vio: tres ejemplos escritos con comillas dobles subían la cuenta de 67 a 71.)
    los_datos_del_rastro = {
        "factura": factura.id if factura else None,
        "imputado": dinero.a_texto(imputado),
    }
    if factura:
        _el_rastro_de_un_cobro(db, explotacion.id, cobro, accion="conciliar", datos=los_datos_del_rastro)
    else:
        _el_rastro_de_un_cobro(
            db, explotacion.id, cobro, accion="desconciliar", datos=los_datos_del_rastro
        )
    db.commit()
    vista = como_se_ve_una_factura(db, explotacion, factura) if factura else None
    avisos = []
    if factura is None:
        avisos.append(textos.COBRO["deshecho"])
    elif sobrante > 0:
        avisos.append(
            textos.mensaje(
                "D4_cobro_mas_que_lo_que_se_debe",
                importe=dinero.formatea(dinero.a_decimal(cobro.importe)),
                pendiente=dinero.formatea(
                    dinero.suma(dinero.a_decimal(factura.importe_total), -(imputado or dinero.CERO))
                ),
                imputado=dinero.formatea(imputado),
                sobrante=dinero.formatea(sobrante),
            )
        )
    if vista is not None:
        avisos.append(
            textos.mensaje(
                "D3_falta_por_cobrar",
                cobrado=vista.texto_cobrado,
                total=vista.texto_total,
                pendiente=vista.texto_pendiente,
            )
            if vista.pendiente and vista.pendiente > 0
            else textos.COBRO["queda_cobrada"].format(numero=vista.numero or "")
        )
    return RespuestaDeUnCobro(
        cobro=como_se_ve_un_cobro(db, explotacion, cobro),
        ya_estaba=False,
        avisos=[aviso for aviso in avisos if aviso],
        factura=vista,
    )


@router.post("/cobros/{cobro_id}/anular", response_model=CobroDeUnaFactura)
def anular_un_cobro(
    cobro_id: int,
    datos: dict,
    explotacion: ExplotacionActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> CobroDeUnaFactura:
    """Quita un cobro, con su motivo. La factura **vuelve a deber lo que debía**.

    No se borra la fila: queda anulada con su motivo y deja de contar en las sumas. Es la misma regla
    del cuaderno, y aquí tiene una consecuencia visible: el pendiente de la factura sube otra vez, lo
    cual es la verdad (ese dinero ya no está apuntado).
    """
    motivo = str((datos or {}).get("motivo") or "").strip()
    if len(motivo) < 3:
        raise HTTPException(
            status_code=422, detail="Dinos por qué lo quitas, para que quede apuntado."
        )
    cobro = obtener_de_la_explotacion(db, models.Cobro, cobro_id, explotacion.id)
    cobro.anulado = True
    cobro.motivo_anulacion = motivo
    # **Y sus aplicaciones se retiran con él** (CRM-01, 11/10/2026), conservando su importe y con el motivo
    # de la anulación: es lo que hace que la deuda vuelva a estar pendiente sin destruir el rastro de lo que
    # se había conciliado. La lectura ya no las cuenta por el cobro anulado, pero dejarlas vivas sería
    # engañoso para quien mire la tabla.
    _retirar_la_aplicacion(db, cobro, motivo=f"se anuló el cobro: {motivo}")
    _el_rastro_de_un_cobro(db, explotacion.id, cobro, accion="anular", datos={"motivo": motivo})
    db.commit()
    return como_se_ve_un_cobro(db, explotacion, cobro)

