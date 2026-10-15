"""Las cuentas de la explotación: gastos, inversiones, repartos, pagos y subvenciones (T13, E7).

QUÉ HAY AQUÍ, Y POR QUÉ ES UN ROUTER NUEVO

El contrato pide una pantalla de cuentas (`/cuentas`, S13) con cinco vistas (ingresos y gastos
registrados, vencimientos, tesorería, inversiones y margen por cultivo y por tierra) y una regla que
gobierna todas: «Compra de activo no equivale automáticamente a gasto completo del cultivo. Mostrar
costes directos, repartidos y sin asignar». Hasta este ticket el programa sabía lo que **entra**
(T12) y no sabía nada de lo que **sale**, así que este router es nuevo de punta a punta.

## Las cinco reglas del encargo, y dónde se cumplen en este fichero

  1. **Gasto, inversión, factura, pago y movimiento bancario son registros distintos.** Hay cinco
     tablas y cinco puertas, y **ninguna** de ellas escribe en otra: un pago no crea un gasto, una
     factura no es un gasto (`gasto.factura_id` apunta al justificante, no al revés) y el extracto del
     banco no se toca aquí (es T20).
  2. **Conciliar un pago no crea un segundo gasto.** La conciliación escribe en
     `aplicaciones_de_pago`, que es una tabla que **solo dice contra qué va el dinero**. No hay
     ninguna línea en este fichero que cree un `Gasto` a partir de un pago, y hay una prueba que
     cuenta los gastos antes y después.
  3. **Un traspaso entre cuentas propias no crea ingresos** (A07): la única puerta que lo hace
     (`gastos.traspaso_entre_cuentas_propias`) devuelve dos movimientos atados y **cero** ingreso y
     cero gasto operativo, y esta puerta de la API tampoco apunta nada en los gastos.
  4. **Pagos parciales y agrupados, y poder deshacerse.** Un pago puede repartirse entre varios
     gastos (`POST /pagos/{id}/conciliar`, y con `automatico` se reparte por orden de antigüedad) y
     varios pagos pueden ir contra un gasto. Deshacer **borra la aplicación y nada más**: el pago
     sigue apuntado con su importe entero y el gasto vuelve a estar pendiente, con su rastro en la
     auditoría (`correcciones.borrar`).
  5. **Costes repartidos + costes sin asignar = total conocido**, y un gasto que no se sabe repartir
     **no se reparte a medias**: se queda entero en «sin asignar» y se dice por qué.

## Y la regla que cruza todas: un importe que no consta NO es cero

Aquí se ve en tres sitios concretos, y los tres tienen prueba:

  · **El esquema acepta `importe` vacío** y lo guarda como `None`. Un gasto sin importe **existe**
    (el agricultor sabe que pagó algo y no sabe cuánto), y su estado es «sin importe», no «pagado».
  · **Ninguna cuenta suma un `None` como cero**: `gastos.py` lo deja fuera y cuenta cuántos faltan, y
    el pie de la pantalla dice «faltan N importes».
  · **El pendiente total es `None` en cuanto hay un gasto sin importe**: no se puede decir cuánto se
    debe de lo que no se sabe cuánto costó, y un `0,00 €` ahí diría que no se debe nada.

## Lo que este router NO hace

  · **No emite ningún documento fiscal** ni resume el IVA: eso necesita su propia especificación, como
    la factura emitida del T12.
  · **No amortiza nada.** No hay ninguna tabla de años de vida útil con fuente en el programa, así que
    la parte de una inversión que va a cada campaña **la dice el agricultor** con un reparto, y
    mientras no la diga se queda sin asignar. El porqué entero está en `gastos.QUE_FALTA`.
  · **No conecta con ningún banco** ni pide credenciales de ninguno.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .. import correcciones, dinero, gastos, models, servicios, textos, ventas
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AnulacionEntrada,
    ConciliacionDePagoEntrada,
    GastoEntrada,
    InversionEntrada,
    PagoEntrada,
    RepartoDeUnGastoEntrada,
    SubvencionEntrada,
)

router = APIRouter(prefix="/api", tags=["gastos"])


# --------------------------------------------------------------------------
# Ayudas: leer un importe de lo que llega, y dejar el rastro
# --------------------------------------------------------------------------


def _un_importe_que_se_puede_guardar(valor, *, codigo: str, **extra) -> Decimal | None:
    """Un importe de los que llegan, comprobado: vacío es «no lo sé» y lo que no cabe se dice.

    **Vacío sigue siendo `None`**, nunca cero: es la regla del encargo, y aquí es donde se decide,
    porque es la puerta de todo lo que entra. Y lo que no cabe en el sitio donde se guarda se rechaza
    con la frase del agricultor en vez de dejar que reviente el motor (en SQLite entra y en
    PostgreSQL tumba la operación entera: ese defecto ya llegó una vez con el dinero del T12).
    """
    if valor is None:
        return None
    try:
        numero = dinero.a_decimal(valor)
    except dinero.ErrorDeDinero as fallo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje(codigo, importe=str(valor), **extra),
        ) from fallo
    if numero is None:
        return None
    if not dinero.cabe_en_el_dinero(numero):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G11_ese_importe_no_cabe", importe=str(valor)),
        )
    return dinero.redondea(numero)


def _el_rastro(
    db: Db, explotacion_id: int, *, entidad: str, entidad_id: int | None, accion: str, datos: dict
) -> None:
    """Una fila del rastro de auditoría.

    Las etiquetas van **escritas enteras** en cada llamada y no por una variable: el guardián que
    comprueba que caben en su columna (`tests/test_las_etiquetas_del_rastro_caben.py`) lee el árbol
    del parser y una etiqueta escondida en una decisión se le quedaría sin vigilar.
    """
    db.add(
        models.Auditoria(
            explotacion_id=explotacion_id,
            entidad=entidad,
            entidad_id=entidad_id,
            accion=accion,
            datos=datos,
        )
    )


def _de_la_lista(valor: str | None, posibles: tuple[str, ...], *, codigo: str, **extra) -> str:
    """Comprueba que lo que llega es una de las respuestas posibles, y lo dice en cristiano.

    La lista cerrada del esquema daría un mensaje en inglés que habla de «input», y aquí el que lee
    es un agricultor. Y se comprueba **aquí y no en el formulario**: el formulario es una comodidad,
    no una puerta; la puerta es esta.

    **El segundo argumento se llama `posibles` y no `lista` a propósito, y esto es un defecto
    arreglado al integrar** (05/10/2026). Las llamadas le pasan la lista de valores posibles **de
    posición** y además le pasan `lista="…"` como palabra clave, que es el texto que sale en el
    aviso («las que hay son: mineral, organico…»). Con el parámetro llamado `lista`, esa palabra
    clave chocaba con él y **las trece pruebas del recorrido reventaban** con `TypeError: … got
    multiple values for argument 'lista'`. No se vio antes porque el router no se podía ni importar
    sin las tablas que integra el coordinador: es exactamente lo que pasa con el código que nadie ha
    ejecutado todavía.
    """
    limpio = (valor or "").strip().lower()
    if limpio not in posibles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje(codigo, valor=valor, **extra),
        )
    return limpio


# --------------------------------------------------------------------------
# Lo que se mira de un gasto: sus repartos, su cuadre, lo pagado y su estado
# --------------------------------------------------------------------------


def _sus_repartos(db: Db, explotacion_id: int, gasto_id: int) -> list[models.RepartoDeCoste]:
    """Los repartos vivos de un gasto, en un orden estable (el de la lista, que no cambia solo)."""
    return list(
        db.scalars(
            select(models.RepartoDeCoste)
            .where(
                models.RepartoDeCoste.explotacion_id == explotacion_id,
                models.RepartoDeCoste.gasto_id == gasto_id,
                models.RepartoDeCoste.anulado.is_(False),
            )
            .order_by(models.RepartoDeCoste.id)
        )
    )


def _lo_pagado(db: Db, explotacion_id: int, gasto_id: int) -> Decimal:
    """Cuánto dinero de los pagos vivos está aplicado a este gasto.

    **La regla se mudó a `servicios.lo_pagado_de_un_gasto`** (09/10/2026), cuando la ficha de la compra
    empezó a enseñar «pagado» y «pendiente» del mismo gasto: dos copias de esta cuenta podrían dar dos
    cifras distintas del mismo dinero en dos pantallas. Aquí se queda el nombre de siempre para no
    tocar los sitios que ya la llamaban.
    """
    return servicios.lo_pagado_de_un_gasto(db, explotacion_id=explotacion_id, gasto_id=gasto_id)


def _el_cuadre_del_reparto(
    gasto: models.Gasto, repartos, *, nombre_de_la_tierra: str | None = None
) -> gastos.CuadreDelReparto:
    """El cuadre que el contrato pide: los repartos que hay apuntados **y el coste directo**.

    **El gasto que ya dice de qué tierra o de qué cultivo es cuenta como asignado** (06/10/2026), y lo
    dice el ticket con estas palabras: «El coste directo: cuando el gasto ya dice de qué tierra o de qué
    cultivo es. Lo que no se sabe a qué va se apunta sin estos dos campos y se reparte después».
    Antes, un gasto apuntado **con su tierra** salía en la pantalla como «Sin asignar», con 0,00 € en
    «en tierras, cultivos o máquinas», y con el aviso de que **las cuentas no cierran** —«hay una parte
    del gasto que no está ni en un sitio ni en el otro»—, que es exactamente lo contrario de lo que el
    agricultor acababa de decir. Se encontró recorriendo el recorrido 2 en un navegador de verdad.
    """
    trozos = [
        {
            "destino_tipo": reparto.destino_tipo,
            "destino": reparto.destino,
            "importe": reparto.importe,
            "metodo": reparto.metodo,
        }
        for reparto in repartos
    ]
    # **El directo solo cuando no hay repartos**: si el gasto se repartió, el reparto es lo que dice a
    # dónde va cada trozo, y contar además el directo sumaría el mismo dinero dos veces.
    directo = _el_destino_directo(gasto, nombre_de_la_tierra) if not trozos else None
    if directo is not None:
        trozos.append(directo)
    cuadre = gastos.cuadre_del_reparto(gasto.importe, trozos)
    # **El motivo por el que no se pudo repartir se lee del trozo que lo guarda** (05/10/2026). El
    # cuadre se recalcula al abrir el gasto y el motivo no se puede deducir del importe: sin esto, la
    # pantalla enseñaría «sin asignar 663,00 €» sin decir qué falta para poder repartirlo, que es
    # justo lo que el ticket prohíbe. Ver `models.RepartoDeCoste.no_se_reparte`.
    if not cuadre.no_se_reparte:
        cuadre.no_se_reparte = next(
            (reparto.no_se_reparte for reparto in repartos if reparto.no_se_reparte), ""
        )
    return cuadre


def _el_destino_directo(gasto: models.Gasto, nombre_de_la_tierra: str | None) -> dict | None:
    """A dónde va un gasto **por decirlo él**: su tierra o su cultivo. Es el «coste directo» del ticket.

    Devuelve un trozo con la misma forma que un reparto —para que el cuadre lo cuente y la pantalla lo
    enseñe igual que los demás—, o `None` si el gasto no dice de dónde es o no dice lo que costó (sin
    importe no hay nada que asignar, y un cero sería mentira).
    """
    if gasto.importe is None:
        return None
    if gasto.parcela_id:
        return {
            "destino_tipo": gastos.TIERRA,
            "destino": nombre_de_la_tierra or str(gasto.parcela_id),
            "importe": gasto.importe,
            "metodo": gastos.DIRECTO,
        }
    if (gasto.cultivo or "").strip():
        return {
            "destino_tipo": gastos.CULTIVO,
            "destino": gasto.cultivo,
            "importe": gasto.importe,
            "metodo": gastos.DIRECTO,
        }
    return None


def _a_donde_va(gasto: models.Gasto, repartos, nombre_de_la_tierra: str | None) -> str:
    """A dónde va el gasto, **en palabras**, para que la pantalla no tenga que traducirlo.

    Lo que el gasto dice de sí mismo (su tierra o su cultivo) manda, porque es lo que el agricultor
    escribió al apuntarlo; si no dice nada, lo dice su primer reparto. Y si no hay nada de eso, vacío:
    la pantalla enseña entonces su «sin asignar», que es la verdad.
    """
    directo = _el_destino_directo(gasto, nombre_de_la_tierra)
    if directo is not None and not repartos:
        return directo["destino"]
    if repartos:
        return _la_etiqueta_del_destino(repartos[0], nombre_de_la_tierra)
    return ""


def _la_etiqueta_del_destino(reparto: models.RepartoDeCoste, nombre_de_la_tierra: str | None) -> str:
    """Cómo se llama el sitio al que va un trozo, para que la pantalla no tenga que traducirlo."""
    if reparto.destino_tipo == gastos.TIERRA and nombre_de_la_tierra:
        return nombre_de_la_tierra
    return reparto.destino or ""


def _como_se_ve_un_gasto(db: Db, explotacion, gasto: models.Gasto) -> dict:
    """Un gasto con todo lo que la pantalla necesita **ya calculado**: ni una cuenta en el navegador.

    En el navegador todo número es de coma flotante, así que las sumas de dinero se hacen aquí, con
    `Decimal`, y a la pantalla le llegan como texto (`"121.00"`). Es la misma decisión que tomó el
    T12 y por el mismo motivo.
    """
    repartos = _sus_repartos(db, explotacion.id, gasto.id)
    pagado = _lo_pagado(db, explotacion.id, gasto.id)
    pendiente = gastos.pendiente_de(gasto.importe, pagado)
    # **El nombre de la tierra del propio gasto** (06/10/2026): hace falta para el cuadre del coste
    # directo y para decir a dónde va sin que la pantalla traduzca un identificador.
    nombre_de_la_tierra = _el_nombre_de_una_tierra(db, explotacion.id, gasto.parcela_id)
    cuadre_del_reparto = _el_cuadre_del_reparto(
        gasto, repartos, nombre_de_la_tierra=nombre_de_la_tierra
    )
    nombres = _nombres_de_las_tierras(db, explotacion.id, repartos)
    return {
        "id": gasto.id,
        "campana_id": gasto.campana_id,
        "fecha": gasto.fecha.isoformat() if gasto.fecha else None,
        "vencimiento": gasto.vencimiento.isoformat() if gasto.vencimiento else None,
        "concepto": gasto.concepto,
        "categoria": gasto.categoria,
        "etiqueta_categoria": textos.GASTOS["categorias_de_gasto"].get(gasto.categoria, ""),
        "proveedor": gasto.proveedor,
        "proveedor_nif": gasto.proveedor_nif,
        "contacto_id": gasto.contacto_id,
        "factura_id": gasto.factura_id,
        "maquina_id": gasto.maquina_id,
        "averia_id": gasto.averia_id,
        "parcela_id": gasto.parcela_id,
        "cultivo": gasto.cultivo,
        "base_imponible": dinero.a_texto(gasto.base_imponible),
        "cuota_iva": dinero.a_texto(gasto.cuota_iva),
        "tipo_iva_pct": gasto.tipo_iva_pct,
        # **El importe viaja como texto, y cuando no consta viaja `None`**: no como «0.00».
        "importe": dinero.a_texto(gasto.importe),
        "texto_importe": dinero.formatea(gasto.importe),
        "pagado": dinero.a_texto(pagado),
        "texto_pagado": dinero.formatea(pagado),
        "pendiente": dinero.a_texto(pendiente),
        "texto_pendiente": dinero.formatea(pendiente),
        "estado": gastos.estado_de_un_gasto(
            importe=gasto.importe,
            pagado=pagado,
            vencimiento=gasto.vencimiento,
            hoy=dt.date.today(),
            anulado=gasto.anulado,
        ),
        "cuadre": gastos.cuadre_de_los_importes(
            base_imponible=gasto.base_imponible,
            cuota_iva=gasto.cuota_iva,
            total=gasto.importe,
            tipo_iva_pct=dinero.cantidad_a_decimal(gasto.tipo_iva_pct),
        ).como_dict(),
        # **A dónde va, en palabras** (06/10/2026): lo que el gasto dice de sí mismo —su tierra o su
        # cultivo, que es el «coste directo» del ticket— o, si no dice nada, su primer reparto. Vacío
        # cuando no hay nada: la pantalla enseña entonces su «sin asignar», que es la verdad.
        "va_a": _a_donde_va(gasto, repartos, nombre_de_la_tierra),
        "repartos": [
            {
                "id": reparto.id,
                "destino_tipo": reparto.destino_tipo,
                "destino": reparto.destino,
                "etiqueta_destino": _la_etiqueta_del_destino(
                    reparto, nombres.get(reparto.parcela_id)
                ),
                "parcela_id": reparto.parcela_id,
                "campana_id": reparto.campana_id,
                "maquina_id": reparto.maquina_id,
                "importe": dinero.a_texto(reparto.importe),
                "texto_importe": dinero.formatea(reparto.importe),
                "metodo": reparto.metodo,
                "confirmado_por_el_agricultor": reparto.confirmado_por_el_agricultor,
            }
            for reparto in repartos
        ],
        "cuadre_del_reparto": {
            **cuadre_del_reparto.como_dict(),
            "texto_repartido": dinero.formatea(cuadre_del_reparto.repartido),
            "texto_sin_asignar": dinero.formatea(cuadre_del_reparto.sin_asignar),
            "texto_entero": dinero.formatea(cuadre_del_reparto.entero),
            "texto_falta": dinero.formatea(cuadre_del_reparto.falta),
        },
        "anulado": gasto.anulado,
        "motivo_anulacion": gasto.motivo_anulacion,
        "notas": gasto.notas,
        # Las claves en las que se puede estar equivocado, para que la pantalla diga qué hacer.
        "le_falta_el_importe": gasto.importe is None,
        # **«Sin repartir» es que no está en ningún sitio de verdad** (05/10/2026): o no se ha
        # repartido todavía —nada apuntado, que es el caso de un gasto recién apuntado— o se ha dicho
        # «no sé a qué va» y el importe se ha quedado entero en «sin asignar». Se mira lo repartido y
        # no lo sin asignar: un gasto que acaba de apuntarse tiene `sin_asignar` a cero porque nadie ha
        # dicho nada todavía, y la pantalla tiene que poder avisar de eso mismo.
        "esta_sin_repartir": bool(cuadre_del_reparto.repartido == dinero.CERO),
        "no_cuadra": not cuadre_del_reparto.cuadra,
    }


def _el_nombre_de_una_tierra(db: Db, explotacion_id: int, parcela_id: int | None) -> str | None:
    """Cómo se llama esa tierra, si es de esta finca. `None` si no hay tierra o no es suya."""
    if not parcela_id:
        return None
    parcela = db.scalar(
        select(models.Parcela).where(
            models.Parcela.explotacion_id == explotacion_id, models.Parcela.id == parcela_id
        )
    )
    if parcela is None:
        return None
    return parcela.alias or parcela.ref_sigpac or f"#{parcela.id}"


def _nombres_de_las_tierras(db: Db, explotacion_id: int, repartos) -> dict[int, str]:
    """El nombre de cada tierra que aparece en esos repartos, para no enseñar un número."""
    ids = {reparto.parcela_id for reparto in repartos if reparto.parcela_id}
    if not ids:
        return {}
    parcelas = db.scalars(
        select(models.Parcela).where(
            models.Parcela.explotacion_id == explotacion_id, models.Parcela.id.in_(ids)
        )
    )
    return {parcela.id: (parcela.alias or parcela.ref_sigpac or f"#{parcela.id}") for parcela in parcelas}


def _como_se_ve_una_inversion(inversion: models.InversionDeLaFinca, *, repartido: Decimal) -> dict:
    """Una inversión: lo que costó y **cuánto de eso se ha llevado una campaña**, que es distinto."""
    sin_asignar = None
    if inversion.importe is not None:
        sin_asignar = dinero.redondea(inversion.importe - repartido)
        if sin_asignar < 0:
            sin_asignar = dinero.CERO
    return {
        "id": inversion.id,
        "campana_id": inversion.campana_id,
        "fecha": inversion.fecha.isoformat() if inversion.fecha else None,
        "concepto": inversion.concepto,
        "categoria": inversion.categoria,
        "etiqueta_categoria": textos.GASTOS["categorias_de_inversion"].get(inversion.categoria, ""),
        "proveedor": inversion.proveedor,
        "factura_id": inversion.factura_id,
        "maquina_id": inversion.maquina_id,
        "parcela_id": inversion.parcela_id,
        # **`None` cuando no consta**, y la pantalla lo enseña en blanco.
        "importe": dinero.a_texto(inversion.importe),
        "texto_importe": dinero.formatea(inversion.importe),
        "valor_residual": dinero.a_texto(inversion.valor_residual),
        "repartido_a_la_campana": dinero.a_texto(repartido),
        "texto_repartido": dinero.formatea(repartido),
        "sin_asignar": dinero.a_texto(sin_asignar),
        "texto_sin_asignar": dinero.formatea(sin_asignar),
        "es_un_gasto_completo_del_cultivo": gastos.es_un_gasto_completo_del_cultivo(
            gastos.INVERSION
        ),
        "anulada": inversion.anulada,
        "motivo_anulacion": inversion.motivo_anulacion,
        "notas": inversion.notas,
        "le_falta_el_importe": inversion.importe is None,
    }


def _repartido_de_una_inversion(db: Db, explotacion_id: int, inversion_id: int) -> Decimal:
    repartos = db.scalars(
        select(models.RepartoDeCoste).where(
            models.RepartoDeCoste.explotacion_id == explotacion_id,
            models.RepartoDeCoste.inversion_id == inversion_id,
            models.RepartoDeCoste.anulado.is_(False),
            models.RepartoDeCoste.destino_tipo != gastos.SIN_ASIGNAR,
        )
    )
    return dinero.suma(*[reparto.importe for reparto in repartos])


def _aplicaciones_vivas(db: Db, explotacion_id: int, pago_id: int) -> list[models.AplicacionDeUnPago]:
    return list(
        db.scalars(
            select(models.AplicacionDeUnPago)
            .where(
                models.AplicacionDeUnPago.explotacion_id == explotacion_id,
                models.AplicacionDeUnPago.pago_id == pago_id,
            )
            .order_by(models.AplicacionDeUnPago.id)
        )
    )


def _como_se_ve_un_pago(db: Db, explotacion, pago: models.PagoDeGasto) -> dict:
    """Un pago con lo que tiene aplicado, lo que le queda libre y a qué gastos va.

    **Lo que le queda libre** es el número que hace falta para no contar el mismo dinero dos veces:
    un pago de 500 € con 121 € aplicados tiene 379 € que todavía no se sabe a qué van, y eso se dice
    con esa palabra («sin conciliar»), no se esconde.
    """
    aplicaciones = _aplicaciones_vivas(db, explotacion.id, pago.id)
    aplicado = dinero.suma(*[aplicacion.importe for aplicacion in aplicaciones])
    libre = dinero.redondea((dinero.a_decimal(pago.importe) or dinero.CERO) - aplicado)
    if libre < 0:
        libre = dinero.CERO
    detalle = []
    for aplicacion in aplicaciones:
        suyo = db.get(models.Gasto, aplicacion.gasto_id)
        detalle.append(
            {
                "id": aplicacion.id,
                "gasto_id": aplicacion.gasto_id,
                "concepto": suyo.concepto if suyo else "",
                "importe": dinero.a_texto(aplicacion.importe),
                "texto_importe": dinero.formatea(aplicacion.importe),
                "el_gasto_sigue_existiendo": suyo is not None,
            }
        )
    return {
        "id": pago.id,
        "fecha": pago.fecha.isoformat() if pago.fecha else None,
        "importe": dinero.a_texto(pago.importe),
        "texto_importe": dinero.formatea(pago.importe),
        "proveedor": pago.proveedor,
        "contacto_id": pago.contacto_id,
        "forma": pago.forma,
        "etiqueta_forma": textos.GASTOS["formas_de_pago"].get(pago.forma, ""),
        "referencia": pago.referencia,
        "notas": pago.notas,
        "anulado": pago.anulado,
        "motivo_anulacion": pago.motivo_anulacion,
        "aplicado": dinero.a_texto(aplicado),
        "texto_aplicado": dinero.formatea(aplicado),
        "sin_conciliar": dinero.a_texto(libre),
        "texto_sin_conciliar": dinero.formatea(libre),
        "aplicaciones": detalle,
        "estan_sin_conciliar": len(detalle) == 0,
    }


def _como_se_ve_una_subvencion(subvencion: models.Subvencion) -> dict:
    """Una ayuda con **sus tres importes separados y su estado deducido**, no sumados."""
    estado = gastos.estado_de_una_subvencion(
        prevista=subvencion.importe_previsto is not None,
        concedida=subvencion.importe_concedido is not None,
        cobrada=subvencion.importe_cobrado is not None,
    )
    return {
        "id": subvencion.id,
        "campana_id": subvencion.campana_id,
        "concepto": subvencion.concepto,
        "organismo": subvencion.organismo,
        "fecha_solicitud": subvencion.fecha_solicitud.isoformat() if subvencion.fecha_solicitud else None,
        "fecha_concesion": subvencion.fecha_concesion.isoformat() if subvencion.fecha_concesion else None,
        "fecha_cobro": subvencion.fecha_cobro.isoformat() if subvencion.fecha_cobro else None,
        "importe_previsto": dinero.a_texto(subvencion.importe_previsto),
        "importe_concedido": dinero.a_texto(subvencion.importe_concedido),
        "importe_cobrado": dinero.a_texto(subvencion.importe_cobrado),
        "texto_previsto": dinero.formatea(subvencion.importe_previsto),
        "texto_concedido": dinero.formatea(subvencion.importe_concedido),
        "texto_cobrado": dinero.formatea(subvencion.importe_cobrado),
        "estado": estado,
        "etiqueta_estado": textos.GASTOS["estados_de_una_subvencion"].get(estado, ""),
        # **La previsión se dice aparte y no se suma al ingreso**: es la regla del contrato en S13.
        "cuenta_como_ingreso": estado == gastos.COBRADA,
        "anulada": subvencion.anulada,
        "motivo_anulacion": subvencion.motivo_anulacion,
        "notas": subvencion.notas,
    }


# --------------------------------------------------------------------------
# La pantalla de cuentas: todo lo que necesita, ya calculado
# --------------------------------------------------------------------------


@router.get("/gastos")
def las_cuentas(explotacion: ExplotacionActual, db: Db, campana_id: int | None = None) -> dict:
    """Las cuentas de la finca: los gastos, las inversiones, los pagos, las ayudas y el margen.

    Es la pantalla S13 entera, y devuelve **cinco listas separadas** —gastos, inversiones, pagos,
    ayudas y movimientos sin conciliar— porque el encargo exige que no se mezclen. Y devuelve tres
    cuentas distintas que tampoco se mezclan:

      · **el coste conocido**, con sus tres columnas (directos, repartidos y sin asignar);
      · **la caja**, que es el dinero que ha entrado y salido de verdad;
      · **el margen**, que sale **solo si no falta ningún importe** y que se dice incompleto cuando
        falta (con `margen` en `None`, nunca con un cero).
    """
    consulta = select(models.Gasto).where(models.Gasto.explotacion_id == explotacion.id)
    if campana_id is not None:
        consulta = consulta.where(models.Gasto.campana_id == campana_id)
    apuntados = list(db.scalars(consulta.order_by(models.Gasto.fecha.desc(), models.Gasto.id.desc())))

    inversiones = list(
        db.scalars(
            select(models.InversionDeLaFinca)
            .where(models.InversionDeLaFinca.explotacion_id == explotacion.id)
            .order_by(models.InversionDeLaFinca.id.desc())
        )
    )
    pagos = list(
        db.scalars(
            select(models.PagoDeGasto)
            .where(models.PagoDeGasto.explotacion_id == explotacion.id)
            .order_by(models.PagoDeGasto.fecha.desc(), models.PagoDeGasto.id.desc())
        )
    )
    subvenciones = list(
        db.scalars(
            select(models.Subvencion)
            .where(models.Subvencion.explotacion_id == explotacion.id)
            .order_by(models.Subvencion.id.desc())
        )
    )

    filas = [_como_se_ve_un_gasto(db, explotacion, gasto) for gasto in apuntados]

    # Las tres columnas del coste, calculadas con el módulo puro y **con cada gasto clasificado por
    # dónde va**: directo si tiene tierra o cultivo propio, repartido si viene de un reparto, y sin
    # asignar si no se sabe a qué va.
    costes_por_concepto: list[dict] = []
    for fila in filas:
        if fila["anulado"]:
            continue
        concepto = fila["cultivo"] or _etiqueta_de_la_tierra(fila)
        clase = gastos.SIN_ASIGNAR_CLASE
        if any(rep["destino_tipo"] != gastos.SIN_ASIGNAR for rep in fila["repartos"]):
            clase = gastos.REPARTIDO
        elif fila["parcela_id"] or fila["cultivo"]:
            clase = gastos.DIRECTO
        costes_por_concepto.append(
            {"concepto": concepto, "importe": fila["importe"], "clase": clase}
        )

    # Los ingresos de lo que se vende, para el margen, **solo si se ha pedido una campaña**: sin
    # campaña, mezclar las ventas de tres años con los gastos de uno daría un margen que no es de
    # nada. Y lo cobrado va aparte, que es lo que alimenta la caja.
    #
    # **De dónde sale lo cobrado de cada entrega, y por qué se hace así.** El dinero no se cobra
    # contra una entrega: se cobra contra **una factura**, que puede llevar dentro varias entregas.
    # Repartir el importe cobrado entero en cada entrega contaría el mismo dinero tres veces, y
    # repartirlo por porcentaje se inventaría céntimos. Lo que se hace es llamar a
    # `ventas.reparto_de_lo_cobrado`, que ya existe y tiene sus pruebas (T12): aplica lo cobrado a las
    # entregas **por orden, la más antigua primero**, y así la suma de las filas es exactamente lo
    # cobrado de la factura.
    cobrado_por_venta: dict[int, Decimal] = {}
    if campana_id is not None:
        # **El dinero cobrado de cada factura sale de la regla única** (`servicios.lo_cobrado_por_factura`,
        # CRM-01, 11/10/2026): antes se sumaba aquí `importe_imputado` agrupando por la columna del cobro, y
        # como un ingreso puede saldar **varias** deudas —con esa columna vacía a propósito—, el margen de
        # esa venta salía **sin cobrar**, que es un número equivocado en la pantalla donde el agricultor
        # decide qué sembrar. La regla es la misma que la del cobrado de una factura, y ahora es una sola.
        cobrado_por_factura = servicios.lo_cobrado_por_factura(db, explotacion_id=explotacion.id)
        for factura in db.scalars(
            select(models.FacturaEmitida).where(
                models.FacturaEmitida.explotacion_id == explotacion.id,
                models.FacturaEmitida.campana_id == campana_id,
                models.FacturaEmitida.anulada.is_(False),
            )
        ):
            lineas = [linea for linea in factura.lineas if not linea.anulada]
            if not lineas:
                continue
            repartido = ventas.reparto_de_lo_cobrado(
                [linea.importe for linea in lineas],
                cobrado_por_factura.get(factura.id, dinero.CERO),
            )
            for linea, cobrado in zip(lineas, repartido):
                cobrado_por_venta[linea.venta_id] = dinero.suma(
                    cobrado_por_venta.get(linea.venta_id, dinero.CERO), cobrado
                )

    ingresos_por_concepto: list[dict] = []
    if campana_id is not None:
        for venta in db.scalars(
            select(models.VentaDeCosecha).where(
                models.VentaDeCosecha.explotacion_id == explotacion.id,
                models.VentaDeCosecha.campana_id == campana_id,
                models.VentaDeCosecha.anulado.is_(False),
            )
        ):
            ingresos_por_concepto.append(
                {
                    "concepto": venta.producto or "",
                    # **Lo registrado**, que es con lo que se calcula el margen: una entrega sin
                    # importe suma como «no lo sé» (no como cero) y deja el margen incompleto.
                    "importe": venta.importe,
                    "cobrado": cobrado_por_venta.get(venta.id, dinero.CERO),
                }
            )

    pendientes_de_pago = [fila["pendiente"] for fila in filas if not fila["anulado"]]

    margenes = gastos.margen_por_concepto(costes_por_concepto, ingresos_por_concepto)
    caja = gastos.caja(
        cobros=[
            {"importe": cobro.importe, "anulado": cobro.anulado}
            for cobro in db.scalars(
                select(models.Cobro).where(models.Cobro.explotacion_id == explotacion.id)
            )
        ],
        pagos=[{"importe": pago.importe, "anulado": pago.anulado} for pago in pagos],
        por_pagar=[Decimal(fila) for fila in pendientes_de_pago if fila is not None],
        subvenciones=[
            {
                "estado": gastos.estado_de_una_subvencion(
                    prevista=subvencion.importe_previsto is not None,
                    concedida=subvencion.importe_concedido is not None,
                    cobrada=subvencion.importe_cobrado is not None,
                ),
                "importe": subvencion.importe_cobrado
                if subvencion.importe_cobrado is not None
                else subvencion.importe_concedido
                if subvencion.importe_concedido is not None
                else subvencion.importe_previsto,
            }
            for subvencion in subvenciones
            if not subvencion.anulada
        ],
    )

    trozos_de_reparto = [
        {**reparto, "anulado": False}
        for fila in filas
        for reparto in fila["repartos"]
    ]
    cuenta = gastos.cuenta_de_la_explotacion(
        gastos=[{"importe": fila["importe"], "pagado": fila["pagado"], "anulado": fila["anulado"]} for fila in filas],
        inversiones=[{"importe": inversion.importe, "anulado": inversion.anulada} for inversion in inversiones],
        facturas=[],
        pagos=[{"importe": pago.importe, "anulado": pago.anulado} for pago in pagos],
        movimientos=[],
        trozos_de_reparto=trozos_de_reparto,
    )

    return {
        "campana_id": campana_id,
        "cuantos": len(filas),
        "gastos": filas,
        "inversiones": [
            _como_se_ve_una_inversion(
                inversion, repartido=_repartido_de_una_inversion(db, explotacion.id, inversion.id)
            )
            for inversion in inversiones
        ],
        "pagos": [_como_se_ve_un_pago(db, explotacion, pago) for pago in pagos],
        "subvenciones": [_como_se_ve_una_subvencion(subvencion) for subvencion in subvenciones],
        "sin_conciliar": [
            _como_se_ve_un_pago(db, explotacion, pago)
            for pago in pagos
            if not pago.anulado and not _aplicaciones_vivas(db, explotacion.id, pago.id)
        ],
        "cuenta": cuenta.como_dict(),
        "caja": caja.como_dict(),
        "margenes": {concepto: suyo.como_dict() for concepto, suyo in margenes.items()},
        "coste_por_clase": _el_coste_por_clase(filas),
        "por_pagar": {
            "importe": dinero.a_texto(dinero.suma(*pendientes_de_pago)),
            "texto": dinero.formatea(dinero.suma(*pendientes_de_pago)),
            "cuantos": len(
                [uno for uno in pendientes_de_pago if uno is not None and Decimal(uno) > 0]
            ),
            "sin_importe": len([fila for fila in filas if not fila["anulado"] and fila["importe"] is None]),
        },
        # **Lo que este programa todavía no calcula**, para que una cifra que no aparece no parezca
        # un olvido: los años de vida útil, el extracto del banco y el resumen del IVA.
        "que_falta": [dict(uno) for uno in gastos.QUE_FALTA],
        "categorias_de_gasto": [
            {"valor": clave, "texto": textos.GASTOS["categorias_de_gasto"].get(clave, clave)}
            for clave in gastos.CATEGORIAS_DE_GASTO
        ],
        "categorias_de_inversion": [
            {"valor": clave, "texto": textos.GASTOS["categorias_de_inversion"].get(clave, clave)}
            for clave in gastos.CATEGORIAS_DE_INVERSION
        ],
        "metodos_de_reparto": [
            {"valor": clave, "texto": textos.GASTOS["metodos_de_reparto"].get(clave, clave)}
            for clave in gastos.METODOS_DE_REPARTO
        ],
        # Y las formas de pago: **la misma lista que la de cobro**, para no tener dos verdades sobre
        # cómo se mueve el dinero.
        "formas_de_pago": [
            {"valor": clave, "texto": textos.GASTOS["formas_de_pago"].get(clave, clave)}
            for clave in ventas.FORMAS_DE_COBRO
        ],
    }


def _etiqueta_de_la_tierra(fila: dict) -> str:
    """Cómo se llama el concepto de un gasto que no tiene cultivo: su tierra, o «sin asignar»."""
    for reparto in fila["repartos"]:
        if reparto["destino_tipo"] == gastos.TIERRA:
            return reparto["etiqueta_destino"] or reparto["destino"]
    return gastos.SIN_ASIGNAR


def _el_coste_por_clase(filas: list[dict]) -> dict:
    """Las tres columnas del contrato —directos, repartidos y sin asignar— ya sumadas.

    Se reparte **trozo a trozo**, y no «el gasto entero en una columna según lo que tenga»: un gasto
    de 100 € con 60 € repartidos a una tierra y 40 € sin asignar tiene que aparecer con 60 en una
    columna y 40 en la otra, o el total no cuadraría. Y la parte que no está en ningún reparto cuenta
    como sin asignar, que es la verdad: está apuntada y no se sabe a qué va.

    Las tres van separadas y no se suman en una cifra sola sin decirlo: un coste repartido es una
    estimación acordada con el agricultor y uno directo es lo que pone el papel, y son dos cosas de
    fiabilidad distinta.

    **La comprobación que esto sostiene**: `repartido + sin_asignar + directos = total conocido`. El
    total se devuelve calculado aparte, así que si un coste se perdiera entre dos pantallas, la
    prueba que compara los dos números se pondría roja.
    """
    directos = dinero.CERO
    repartidos = dinero.CERO
    sin_asignar = dinero.CERO
    sin_importe = 0
    sin_asignar_cuantos = 0
    for fila in filas:
        if fila["anulado"]:
            continue
        importe = dinero.a_decimal(fila["importe"])
        if importe is None:
            sin_importe += 1
            continue
        if fila["parcela_id"] or fila["cultivo"]:
            # Coste **directo**: el gasto ya dice de qué tierra o de qué cultivo es.
            directos = dinero.suma(directos, importe)
            continue
        repartido_aqui = dinero.CERO
        for trozo in fila["repartos"]:
            suyo = dinero.a_decimal(trozo["importe"]) or dinero.CERO
            if trozo["destino_tipo"] == gastos.SIN_ASIGNAR:
                sin_asignar = dinero.suma(sin_asignar, suyo)
            else:
                repartido_aqui = dinero.suma(repartido_aqui, suyo)
        repartidos = dinero.suma(repartidos, repartido_aqui)
        # Lo que no está en ningún trozo **no desaparece**: se queda sin asignar y cuenta.
        resto = dinero.redondea(importe - repartido_aqui)
        if resto > 0:
            sin_asignar = dinero.suma(sin_asignar, resto)
        if repartido_aqui <= 0 or resto > 0:
            sin_asignar_cuantos += 1
    total = dinero.suma(directos, repartidos, sin_asignar)
    return {
        "directos": dinero.a_texto(directos),
        "repartidos": dinero.a_texto(repartidos),
        "sin_asignar": dinero.a_texto(sin_asignar),
        "texto_directos": dinero.formatea(directos),
        "texto_repartidos": dinero.formatea(repartidos),
        "texto_sin_asignar": dinero.formatea(sin_asignar),
        # **Costes repartidos + costes sin asignar = total conocido**, y el total se dice.
        "total_conocido": dinero.a_texto(total),
        "texto_total_conocido": dinero.formatea(total),
        "sin_asignar_cuantos": sin_asignar_cuantos,
        "sin_importe": sin_importe,
        # **Y las dos frases que hacen que los números no parezcan completos.** Se componen aquí, con
        # singular y plural, y no en la pantalla: un «1 importes» es lo primero que hace desconfiar de
        # un programa, y una frase compuesta en el navegador es una frase escrita a mano (que la
        # prueba de las pantallas caza). Ver `textos.mensaje_con_cuenta`.
        "texto_sin_importe": (
            textos.mensaje_con_cuenta("G46_faltan_importes_por_saber", sin_importe)
            if sin_importe
            else ""
        ),
        "texto_sin_asignar_cuantos": (
            textos.mensaje_con_cuenta("G47_gastos_sin_saber_a_donde_van", sin_asignar_cuantos)
            if sin_asignar_cuantos
            else ""
        ),
    }


@router.get("/gastos/avisos")
def los_avisos(explotacion: ExplotacionActual, db: Db) -> list[dict]:
    """Lo que hay que mirar: gastos vencidos y gastos a los que les falta el importe.

    Es la misma idea que los avisos de la maquinaria (T14): el programa dice lo que **él** sabe y no
    lo que el agricultor debería mirar por su cuenta. Un gasto sin importe es un aviso de verdad:
    hasta que no se sepa, el margen no se puede calcular.
    """
    hoy = dt.date.today()
    avisos: list[dict] = []
    apuntados = db.scalars(
        select(models.Gasto).where(
            models.Gasto.explotacion_id == explotacion.id, models.Gasto.anulado.is_(False)
        )
    )
    for gasto in apuntados:
        pagado = _lo_pagado(db, explotacion.id, gasto.id)
        estado = gastos.estado_de_un_gasto(
            importe=gasto.importe, pagado=pagado, vencimiento=gasto.vencimiento, hoy=hoy
        )
        if estado == gastos.SIN_IMPORTE:
            avisos.append({"tipo": "sin_importe", "gasto_id": gasto.id, "concepto": gasto.concepto})
        elif estado == gastos.VENCIDO:
            avisos.append(
                {
                    "tipo": "vencido",
                    "gasto_id": gasto.id,
                    "concepto": gasto.concepto,
                    "vencimiento": gasto.vencimiento.isoformat() if gasto.vencimiento else None,
                    "texto_pendiente": dinero.formatea(gastos.pendiente_de(gasto.importe, pagado)),
                }
            )
    return avisos


@router.get("/gastos/averias")
def el_coste_de_las_averias(
    explotacion: ExplotacionActual, db: Db, maquina_id: int | None = None
) -> dict:
    """El coste de las averías de la finca, **avería por avería** (lo que el T14 dejó para el T13).

    Se calcula sumando los gastos que **dicen de qué avería salen** (`gastos.averia_id`), que es la
    única forma de que un importe no esté en dos sitios: la avería no guarda su coste, lo guarda el
    gasto. Y lo que no cuelga de ninguna avería se dice aparte, para que nadie crea que el coste de
    las averías es todo lo que se ha gastado en reparar.

    **Y con `?maquina_id=` se puede pedir SOLO las de una máquina** (CRM-07 #7, 14/10/2026), con su
    `total`: es lo que enseña la ficha de una máquina, que es donde el agricultor mira lo que le ha
    costado tenerla parada. Se filtra **aquí** y no en la pantalla porque las cifras las calcula el
    servidor, y porque sumar en la pantalla sería calcular lo mismo en dos sitios.
    """
    if maquina_id is not None:
        obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)
    apuntados = list(
        db.scalars(
            select(models.Gasto).where(
                models.Gasto.explotacion_id == explotacion.id, models.Gasto.anulado.is_(False)
            )
        )
    )
    filas = [
        {
            "averia_id": gasto.averia_id,
            # De qué máquina es el gasto: hace falta para contar bien las reparaciones que **no** cuelgan
            # de ninguna avería cuando se pide una máquina sola.
            "maquina_id": gasto.maquina_id,
            "importe": gasto.importe,
            "clase": gastos.SIN_ASIGNAR_CLASE
            if not _sus_repartos(db, explotacion.id, gasto.id)
            else gastos.REPARTIDO,
            "anulado": gasto.anulado,
        }
        for gasto in apuntados
    ]
    por_averia = gastos.coste_de_las_averias(filas)
    averias = {
        averia.id: averia
        for averia in db.scalars(
            select(models.AveriaDeMaquina).where(
                models.AveriaDeMaquina.explotacion_id == explotacion.id
            )
        )
    }
    salida = []
    for averia_id, coste in sorted(por_averia.items()):
        if averia_id == -1:
            continue
        averia = averias.get(averia_id)
        # **Si se pide una máquina, solo las suyas** (CRM-07 #7): la ficha de una máquina no tiene por
        # qué enseñar lo que se ha roto la del vecino.
        if maquina_id is not None and (averia is None or averia.maquina_id != maquina_id):
            continue
        suyo = coste.como_dict()
        suyo["que_paso"] = averia.que_paso if averia else ""
        suyo["fecha"] = averia.fecha.isoformat() if averia and averia.fecha else None
        suyo["maquina_id"] = averia.maquina_id if averia else None
        suyo["sigue_sin_arreglar"] = (averia.resuelta is False) if averia else None
        suyo["texto_coste"] = dinero.formatea(coste.coste)
        salida.append(suyo)
    # **El total de lo que se está enseñando**, y con dos avisos que no se pueden callar:
    #   · cuántos gastos lo forman, y
    #   · **cuántos de ellos NO tienen importe**. Un total que solo suma la mitad y no lo dice parece el
    #     total entero, y eso es lo que este módulo no hace en ningún sitio.
    total = gastos.CosteDeUnaAveria()
    for averia_id, coste in sorted(por_averia.items()):
        if averia_id == -1:
            continue
        averia = averias.get(averia_id)
        if maquina_id is not None and (averia is None or averia.maquina_id != maquina_id):
            continue
        total.gastos += coste.gastos
        total.sin_importe += coste.sin_importe
        total.coste = dinero.suma(total.coste, coste.coste)
    if maquina_id is not None:
        # Las reparaciones **de esa máquina** que no cuelgan de ninguna avería: también son suyas, y
        # también hay que contarlas y decirlo.
        suyas_sin_averia = [
            fila for fila in filas if fila["averia_id"] is None and fila["maquina_id"] == maquina_id
        ]
        sin_averia = gastos.coste_de_una_averia(suyas_sin_averia)
        total.gastos += sin_averia.gastos
        total.sin_importe += sin_averia.sin_importe
        total.coste = dinero.suma(total.coste, sin_averia.coste)
        reparaciones_sin_averia = {
            "cuantos": sin_averia.gastos,
            "importe": dinero.a_texto(sin_averia.coste),
        }
    else:
        reparaciones_sin_averia = {
            "cuantos": por_averia[-1].gastos if -1 in por_averia else 0,
            "importe": dinero.a_texto(por_averia[-1].coste) if -1 in por_averia else None,
        }
    return {
        "averias": salida,
        "total": {
            "coste": dinero.a_texto(total.coste),
            "texto_coste": dinero.formatea(total.coste),
            "gastos": total.gastos,
            "sin_importe": total.sin_importe,
            # `completo` es falso mientras haya algún gasto sin importe: la pantalla tiene que poder
            # decir «esto es lo que se sabe», no «esto es todo».
            "completo": total.sin_importe == 0,
        },
        # Los gastos de reparación que no dicen de qué avería salen: existen y no se esconden.
        "reparaciones_sin_averia": reparaciones_sin_averia,
    }


# --------------------------------------------------------------------------
# Apuntar, corregir y anular un gasto
# --------------------------------------------------------------------------


def _los_importes_del_gasto(datos) -> tuple[Decimal | None, gastos.CuadreDeImportes]:
    """El importe del gasto y el cuadre de sus cuentas, sin convertir nada ausente en cero."""
    base = _un_importe_que_se_puede_guardar(datos.base_imponible, codigo="G15_eso_no_es_un_importe")
    cuota = _un_importe_que_se_puede_guardar(datos.cuota_iva, codigo="G15_eso_no_es_un_importe")
    total = _un_importe_que_se_puede_guardar(datos.importe, codigo="G15_eso_no_es_un_importe")
    cuadre = gastos.cuadre_de_los_importes(
        base_imponible=base, cuota_iva=cuota, total=total, tipo_iva_pct=datos.tipo_iva_pct
    )
    importe = gastos.importe_de_un_gasto(
        base_imponible=base,
        cuota_iva=cuota,
        total=total,
        tipo_iva_pct=dinero.cantidad_a_decimal(datos.tipo_iva_pct),
    )
    return importe, cuadre


def _datos_comprobados_del_gasto(db: Db, explotacion, datos) -> dict:
    """Lo que se comprueba antes de guardar un gasto, y lo que se copia tal cual.

    Dos cosas se comprueban de verdad y no son trámites: **el concepto** (un gasto sin decir qué es
    no se puede revisar dentro de un año) y **que todo lo que se enlaza sea de esta finca** (una
    factura, una máquina o un papel de otra finca filtrarían datos de otro, y el contrato lo prohíbe).
    """
    concepto = (datos.concepto or "").strip()
    if not concepto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G16_el_gasto_necesita_saber_que_es"),
        )
    categoria = _de_la_lista(
        datos.categoria or "otro",
        gastos.CATEGORIAS_DE_GASTO,
        codigo="G2_esa_categoria_no_es_ninguna_de_las_que_hay",
        lista=", ".join(gastos.CATEGORIAS_DE_GASTO),
    )
    for modelo, identificador, nombre in (
        (models.Contacto, datos.contacto_id, "contacto"),
        (models.Factura, datos.factura_id, "factura"),
        (models.Maquina, datos.maquina_id, "maquina"),
        (models.AveriaDeMaquina, datos.averia_id, "averia"),
        (models.Parcela, datos.parcela_id, "parcela"),
        (models.Campana, datos.campana_id, "campana"),
    ):
        if identificador is not None:
            obtener_de_la_explotacion(db, modelo, identificador, explotacion.id)
        del nombre
    # **Y la avería tiene que ser de ESA máquina** (CRM-07 #7, 14/10/2026). El bucle de arriba comprueba
    # cada identificador **por separado** contra la finca, y eso deja pasar un gasto que dice «máquina A»
    # y cuelga de una avería de la **B**: el mismo coste saldria en **las dos fichas** —la de A por su
    # `maquina_id` y la de B porque la avería es suya— y en las cuentas como coste directo de una máquina
    # que no lo ha tenido. No se puede comprobar «por separado» algo que tiene que encajar **entre sí**.
    if datos.averia_id is not None and datos.maquina_id is not None:
        la_averia = obtener_de_la_explotacion(
            db, models.AveriaDeMaquina, datos.averia_id, explotacion.id
        )
        if la_averia.maquina_id != datos.maquina_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje("G53_la_averia_no_es_de_esa_maquina"),
            )
    importe, cuadre = _los_importes_del_gasto(datos)
    if importe is not None and importe == 0:
        # Un gasto de cero euros conocido no es un gasto: es un hueco con un número dentro. Y lo que
        # no se sabe **no se escribe como cero**: se deja en blanco, que es distinto.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G1_el_gasto_de_cero_euros_no_es_un_gasto"),
        )
    return {
        "concepto": concepto,
        "categoria": categoria,
        "campana_id": datos.campana_id,
        "fecha": datos.fecha,
        "vencimiento": datos.vencimiento,
        "proveedor": (datos.proveedor or "").strip() or None,
        "proveedor_nif": (datos.proveedor_nif or "").strip() or None,
        "contacto_id": datos.contacto_id,
        "factura_id": datos.factura_id,
        "maquina_id": datos.maquina_id,
        "averia_id": datos.averia_id,
        "parcela_id": datos.parcela_id,
        "cultivo": (datos.cultivo or "").strip() or None,
        "base_imponible": cuadre.base_imponible,
        "cuota_iva": cuadre.cuota_iva,
        "tipo_iva_pct": datos.tipo_iva_pct,
        "importe": importe,
        "notas": datos.notas,
    }


def _los_avisos_del_gasto(cuadre: gastos.CuadreDeImportes, importe: Decimal | None) -> list[str]:
    """Lo que hay que decirle al agricultor después de guardar, con el número exacto.

    Son tres cosas y las tres se dicen **sin bloquear**: el contrato prohíbe bloquear un apunte por un
    dato opcional. Se guarda y se avisa, y el aviso dice dónde se arregla.
    """
    avisos: list[str] = []
    if importe is None:
        avisos.append(textos.mensaje("G17_el_gasto_se_ha_guardado_sin_importe"))
    elif not cuadre.se_puede_comprobar:
        avisos.append(
            textos.mensaje(
                "G18_no_se_pueden_comprobar_las_cuentas",
                faltan=", ".join(cuadre.no_consta),
            )
        )
    elif not cuadre.cuadra:
        avisos.append(
            textos.mensaje(
                "G19_las_cuentas_del_gasto_no_cuadran",
                diferencia=dinero.formatea(cuadre.diferencia),
            )
        )
    return avisos


@router.post("/gastos", status_code=status.HTTP_201_CREATED)
def apuntar_un_gasto(datos: GastoEntrada, explotacion: ExplotacionActual, db: Db, usuario: UsuarioActual) -> dict:
    """Apunta un gasto: lo que se consumió, cuánto costó y de qué papel sale.

    **Reenviar no duplica** (el móvil sin cobertura, un botón pulsado dos veces): si llega la misma
    clave de reenvío, se devuelve el gasto que ya estaba, con `ya_estaba` en verdadero. Es la misma
    regla que en las entregas, los cobros y las máquinas.

    **Y un gasto sin importe se guarda igual.** El agricultor sabe que pagó la reparación y no se
    acuerda de cuánto: eso es un apunte de verdad con un dato pendiente, y el contrato dice que se
    guarda con pendientes («Un apunte real con datos incompletos se guarda con pendientes»). Lo que
    no se hace es escribir un cero, que en el margen del año se leería como «esta reparación salió
    gratis».
    """
    if datos.clave_de_reenvio:
        ya = db.scalar(
            select(models.Gasto).where(
                models.Gasto.explotacion_id == explotacion.id,
                models.Gasto.clave_de_reenvio == datos.clave_de_reenvio,
                models.Gasto.anulado.is_(False),
            )
        )
        if ya is not None:
            return {"gasto": _como_se_ve_un_gasto(db, explotacion, ya), "ya_estaba": True, "avisos": []}

    comprobado = _datos_comprobados_del_gasto(db, explotacion, datos)
    gasto = models.Gasto(explotacion_id=explotacion.id, clave_de_reenvio=datos.clave_de_reenvio, **comprobado)
    db.add(gasto)
    db.flush()
    _el_rastro(
        db,
        explotacion.id,
        entidad="gasto",
        entidad_id=gasto.id,
        accion="crear",
        datos={"concepto": gasto.concepto, "importe": dinero.a_texto(gasto.importe)},
    )
    del usuario  # la puerta lo exige (hay que estar dentro), y el rastro lo deja `_el_rastro`
    db.commit()
    avisos = _los_avisos_del_gasto(
        gastos.cuadre_de_los_importes(
            base_imponible=gasto.base_imponible,
            cuota_iva=gasto.cuota_iva,
            total=gasto.importe,
            tipo_iva_pct=dinero.cantidad_a_decimal(gasto.tipo_iva_pct),
        ),
        gasto.importe,
    )
    # **Y si no se sabe a qué va, se dice desde el primer momento**: un gasto sin repartir sigue
    # siendo un coste conocido, pero el agricultor tiene que saber que todavía no está en ninguna
    # tierra.
    avisos.append(textos.mensaje("G20_el_gasto_todavia_no_esta_en_ninguna_tierra"))
    return {
        "gasto": _como_se_ve_un_gasto(db, explotacion, gasto),
        "ya_estaba": False,
        "avisos": [aviso for aviso in avisos if aviso],
    }


@router.put("/gastos/{gasto_id}")
def corregir_un_gasto(
    gasto_id: int, datos: GastoEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Corrige un gasto **en su misma fila**, dejando en la auditoría lo que decía antes.

    Se corrige en el sitio y no se crea otro apunte por el mismo motivo que en el resto del cuaderno:
    la misma compra no puede aparecer dos veces, y el rastro de la corrección ya queda escrito campo
    por campo (`correcciones.corregir`).
    """
    gasto = obtener_de_la_explotacion(db, models.Gasto, gasto_id, explotacion.id)
    if gasto.anulado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("G21_eso_esta_anulado_y_no_se_corrige"),
        )
    comprobado = _datos_comprobados_del_gasto(db, explotacion, datos)
    # **La clave de reenvío no se pierde al corregir.** Si el esquema no la trae, se conserva la que
    # ya tenía: borrarla dejaría el gasto sin su marca de «esta petición ya se atendió», y el móvil
    # que reintentara volvería a apuntarlo (el caso A12).
    if datos.clave_de_reenvio is None:
        comprobado["clave_de_reenvio"] = gasto.clave_de_reenvio
    preparado = models.Gasto(**comprobado)
    correcciones.corregir(
        db,
        guardado=gasto,
        preparado=preparado,
        entidad="gasto",
        explotacion_id=explotacion.id,
    )
    return {"gasto": _como_se_ve_un_gasto(db, explotacion, gasto), "avisos": []}


@router.post("/gastos/{gasto_id}/anular")
def anular_un_gasto(
    gasto_id: int, datos: AnulacionEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Anula un gasto con su motivo y **revierte sus efectos**, sin borrar nada.

    Revertir los efectos son tres cosas, y las tres importan:

      1. El gasto deja de contar en las cuentas (sigue en el cuaderno, tachado y con el motivo).
      2. Sus repartos se anulan también: si siguieran vivos, el coste seguiría cargado a una tierra
         por un gasto que ya no vale.
      3. Las aplicaciones de pago que lo saldaban **se quitan**, y el dinero vuelve a estar sin
         conciliar: el pago sigue apuntado con su importe entero (deshacer una conciliación no borra
         el movimiento original) y el agricultor puede volver a decir contra qué iba.

    **Y nada de esto borra filas sin rastro**: cada paso deja su fila en la auditoría.
    """
    gasto = obtener_de_la_explotacion(db, models.Gasto, gasto_id, explotacion.id)
    motivo = (datos.motivo or "").strip()
    if not motivo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G22_para_anular_hace_falta_el_motivo"),
        )
    gasto.anulado = True
    gasto.motivo_anulacion = motivo
    _el_rastro(
        db,
        explotacion.id,
        entidad="gasto",
        entidad_id=gasto.id,
        accion="anular",
        datos={"motivo": motivo, "importe": dinero.a_texto(gasto.importe)},
    )
    for reparto in _sus_repartos(db, explotacion.id, gasto.id):
        reparto.anulado = True
        reparto.motivo_anulacion = textos.mensaje("G23_su_gasto_se_anulo")
        _el_rastro(
            db,
            explotacion.id,
            entidad="reparto_de_coste",
            entidad_id=reparto.id,
            accion="anular_con_el_gasto",
            datos={"gasto_id": gasto.id},
        )
    devueltos = 0
    for aplicacion in _aplicaciones_de_un_gasto(db, explotacion.id, gasto.id):
        db.delete(aplicacion)
        devueltos += 1
        _el_rastro(
            db,
            explotacion.id,
            entidad="aplicacion_de_pago",
            entidad_id=aplicacion.id,
            accion="quitar_al_anular_el_gasto",
            datos={"gasto_id": gasto.id, "importe": dinero.a_texto(aplicacion.importe)},
        )
    db.commit()
    avisos = [textos.mensaje("G24_gasto_anulado", motivo=motivo)]
    if devueltos:
        avisos.append(textos.mensaje("G25_el_dinero_ha_vuelto_a_estar_sin_conciliar", cuantos=devueltos))
    return {"gasto": _como_se_ve_un_gasto(db, explotacion, gasto), "avisos": avisos}


def _aplicaciones_de_un_gasto(db: Db, explotacion_id: int, gasto_id: int) -> list:
    """Las aplicaciones de pago que saldan ese gasto, de pagos vivos.

    Se saca de las aplicaciones y no de una lista escrita a mano: el día que un pago se aplique a un
    gasto por otra vía, esta cuenta lo encuentra sola.
    """
    return list(
        db.scalars(
            select(models.AplicacionDeUnPago)
            .join(models.PagoDeGasto, models.PagoDeGasto.id == models.AplicacionDeUnPago.pago_id)
            .where(
                models.AplicacionDeUnPago.explotacion_id == explotacion_id,
                models.AplicacionDeUnPago.gasto_id == gasto_id,
                models.PagoDeGasto.anulado.is_(False),
            )
        )
    )


# --------------------------------------------------------------------------
# Repartir un gasto: los cuatro métodos y el «sin asignar»
# --------------------------------------------------------------------------


@router.post("/gastos/{gasto_id}/repartos")
def repartir_un_gasto(
    gasto_id: int,
    datos: RepartoDeUnGastoEntrada,
    explotacion: ExplotacionActual,
    db: Db,
) -> dict:
    """Lleva un gasto a las tierras, los cultivos o las máquinas, con el método que diga el agricultor.

    ## El método lo confirma él, y aquí se ve por qué

      · **`area`** — se reparte por las hectáreas de las tierras que se digan, y **las hectáreas las
        lee el servidor** de cada tierra: el agricultor no las teclea (y así no hay dos verdades
        sobre cuánto mide su parcela).
      · **`horas`** y **`consumo`** — las horas o los litros de cada sitio los dice él: son datos que
        el programa no tiene.
      · **`manual`** — pone los importes uno a uno.

    ## Y lo que pasa cuando no se puede repartir

    Si falta la superficie de una de las tierras, **no se reparte entre las que sí se saben**: el
    gasto entero se queda **sin asignar** y se dice qué falta. Repartir solo entre las conocidas le
    cargaría a esas tierras la parte de la que falta, que es un coste por hectárea inventado —el
    fallo que el ticket prohíbe con estas palabras: «si un gasto no se sabe repartir, no se reparte a
    medias: se queda en “sin asignar” y se dice»—.
    """
    gasto = obtener_de_la_explotacion(db, models.Gasto, gasto_id, explotacion.id)
    if gasto.anulado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("G21_eso_esta_anulado_y_no_se_corrige"),
        )
    metodo = _de_la_lista(
        datos.metodo,
        gastos.METODOS_DE_REPARTO,
        codigo="G5_ese_metodo_de_reparto_no_es_ninguno_de_los_cuatro",
        lista=", ".join(gastos.METODOS_DE_REPARTO),
    )
    destino_tipo = _de_la_lista(
        datos.destino_tipo or gastos.TIERRA,
        gastos.DESTINOS_DE_UN_REPARTO,
        codigo="G26_eso_no_es_un_sitio_donde_repartir",
        lista=", ".join(gastos.DESTINOS_DE_UN_REPARTO),
    )
    # **Los destinos tienen que ser de la clase que se dice**, y se comprueba antes de escribir nada.
    # Ver `_comprueba_los_destinos`: sin esto, decir «cultivo» o «máquina» y mandar tierras guardaba un
    # reparto que **afirmaba una cosa falsa** en el libro de cuentas.
    _comprueba_los_destinos(db, explotacion, datos=datos, metodo=metodo, destino_tipo=destino_tipo)

    if metodo == gastos.MANUAL:
        hecho = gastos.reparto_a_mano(
            gasto.importe, [trozo.model_dump() for trozo in datos.trozos]
        )
    elif metodo == gastos.AREA:
        pesos = _las_hectareas_de_las_tierras(db, explotacion, datos.parcela_ids)
        hecho = gastos.reparto_por_area(gasto.importe, pesos, destino_tipo=destino_tipo)
    else:
        hecho = gastos.reparto_por_peso(
            gasto.importe, dict(datos.pesos), metodo=metodo, destino_tipo=destino_tipo
        )

    # Los repartos que hubiera **se quitan dejando el rastro entero en la auditoría**
    # (`correcciones.borrar`), porque el agricultor está diciendo otra vez a dónde va este gasto.
    for viejo in _sus_repartos(db, explotacion.id, gasto.id):
        correcciones.borrar(
            db, registro=viejo, entidad="reparto_de_coste", explotacion_id=explotacion.id
        )

    avisos: list[str] = []
    if hecho.no_se_puede:
        cuadre = gastos.el_gasto_queda_sin_asignar(gasto.importe, porque=hecho.no_se_puede)
        _guardar_los_repartos(db, explotacion, gasto, cuadre, confirmado=False)
        avisos.append(_el_aviso_de_un_reparto_que_no_se_puede(hecho.no_se_puede, gasto))
    else:
        cuadre = gastos.cuadre_del_reparto(
            gasto.importe,
            [
                {
                    "destino_tipo": trozo.destino_tipo,
                    "destino": trozo.destino,
                    "importe": trozo.importe,
                    "metodo": trozo.metodo,
                }
                for trozo in hecho.trozos
            ],
        )
        _guardar_los_repartos(db, explotacion, gasto, cuadre, confirmado=bool(datos.confirmado))
        if cuadre.sin_asignar > 0:
            avisos.append(
                textos.mensaje(
                    "G27_queda_parte_sin_asignar",
                    importe=dinero.formatea(cuadre.sin_asignar),
                )
            )
        if not cuadre.cuadra:
            avisos.append(
                textos.mensaje("G28_el_reparto_no_cuadra", falta=dinero.formatea(cuadre.falta))
            )
    db.commit()
    return {
        "gasto": _como_se_ve_un_gasto(db, explotacion, gasto),
        "residual_del_redondeo": dinero.a_texto(hecho.residual),
        "texto_residual": dinero.formatea(hecho.residual),
        "residual_en": hecho.residual_en,
        "avisos": avisos,
    }


def _comprueba_los_destinos(db: Db, explotacion, *, datos, metodo: str, destino_tipo: str) -> None:
    """Que cada destino sea **de la clase que se dice que es**, antes de escribir ni una fila.

    ## El defecto que esto arregla, y por qué es de los que no se pueden dejar pasar

    Se encontró recorriendo el recorrido 2 en un navegador: la pantalla ofrece repartir un gasto
    **entre tierras, entre cultivos o entre máquinas**, pero el nombre de cada cosa que se puede marcar
    lo ponía siempre la lista de tierras. Con `destino_tipo = "maquina"` y las tierras marcadas, el
    servidor **aceptaba** la petición y guardaba filas que decían `maquina` con el número de una tierra
    dentro: el libro de cuentas quedaba **afirmando algo falso** —«este dinero fue a la máquina 3»
    cuando el 3 es una parcela— sin un solo error y sin que nadie se enterara. Un dato inventado es lo
    que este proyecto no puede permitirse, así que lo que no se puede cumplir **se dice**:

      · **Por hectáreas solo se reparte entre tierras.** Las hectáreas son de una tierra: un cultivo o
        una máquina no tienen superficie propia, así que ahí no hay nada que pesar. Se dice **y se dice
        qué hacer** (elegir otro método), que es la regla de la casa para un «no se puede».
      · **Una tierra** se identifica por su número en el cuaderno (es lo que manda la pantalla) o por su
        nombre (que es como lo guarda el coste directo del gasto): el destino tiene que ser una de las
        dos cosas y existir en esta finca.
      · **Un cultivo** va con su nombre («TRIGO BLANDO»), no con un número: si lo que llega es un número,
        lo que se está repartiendo es una tierra con la etiqueta equivocada, y eso es exactamente el
        defecto de arriba.
      · **Una máquina** va con su nombre, y ese nombre tiene que ser el de una máquina de esta finca:
        una máquina que no existe es un destino inventado.
    """
    if metodo == gastos.AREA:
        if destino_tipo != gastos.TIERRA:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje("G48_las_hectareas_son_de_una_tierra"),
            )
        destinos = [str(uno) for uno in datos.parcela_ids]
    elif metodo == gastos.MANUAL:
        destinos = [str(trozo.destino) for trozo in datos.trozos]
    else:
        destinos = [str(clave) for clave in datos.pesos]

    for destino in destinos:
        limpio = destino.strip()
        if not limpio:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje("G49_un_destino_sin_nombre"),
            )
        if destino_tipo == gastos.TIERRA:
            if _la_tierra_del_destino(db, explotacion, limpio) is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=textos.mensaje("G50_esa_tierra_no_esta_en_tu_cuaderno"),
                )
        elif destino_tipo == gastos.CULTIVO:
            if limpio.isdigit():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=textos.mensaje("G51_eso_es_una_tierra_y_no_un_cultivo"),
                )
        elif destino_tipo == gastos.MAQUINA:
            if not _es_una_maquina_de_la_finca(db, explotacion, limpio):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=textos.mensaje("G52_esa_maquina_no_esta_en_tu_cuaderno"),
                )


def _la_tierra_del_destino(db: Db, explotacion, destino: str) -> models.Parcela | None:
    """La tierra de un destino de reparto: por su número (lo que manda la pantalla) o por su nombre."""
    if destino.isdigit():
        return db.scalar(
            select(models.Parcela).where(
                models.Parcela.explotacion_id == explotacion.id, models.Parcela.id == int(destino)
            )
        )
    return db.scalar(
        select(models.Parcela).where(
            models.Parcela.explotacion_id == explotacion.id, models.Parcela.alias == destino
        )
    )


def _es_una_maquina_de_la_finca(db: Db, explotacion, nombre: str) -> bool:
    """Si ese nombre es el de una máquina de esta finca. **Por el nombre, que es lo que se guarda.**"""
    return (
        db.scalar(
            select(models.Maquina).where(
                models.Maquina.explotacion_id == explotacion.id, models.Maquina.nombre == nombre
            )
        )
        is not None
    )


def _las_hectareas_de_las_tierras(db: Db, explotacion, parcela_ids) -> dict[str, Decimal | None]:
    """Las hectáreas de cada tierra pedida, **leídas de la tierra** y con `None` si no constan.

    `None` y no cero cuando la tierra no tiene superficie apuntada: un cero ahí sería «esta tierra
    mide cero hectáreas», y el reparto por área la dejaría sin coste como si no existiera. Con `None`
    el reparto no se hace y se dice, que es lo que el ticket pide.
    """
    pesos: dict[str, Decimal | None] = {}
    for parcela_id in parcela_ids:
        parcela = obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
        pesos[str(parcela_id)] = dinero.cantidad_a_decimal(parcela.superficie_ha)
    return pesos


def _guardar_los_repartos(db: Db, explotacion, gasto: models.Gasto, cuadre, *, confirmado: bool) -> None:
    """Guarda los trozos del cuadre como filas de reparto."""
    for trozo in cuadre.destinos:
        importe = dinero.a_decimal(trozo.get("importe"))
        destino = str(trozo.get("destino") or "")
        parcela_id = None
        if trozo["destino_tipo"] == gastos.TIERRA and destino.isdigit():
            parcela_id = int(destino)
        db.add(
            models.RepartoDeCoste(
                explotacion_id=explotacion.id,
                gasto_id=gasto.id,
                destino_tipo=trozo["destino_tipo"],
                destino=destino,
                parcela_id=parcela_id,
                campana_id=gasto.campana_id,
                importe=importe,
                metodo=trozo.get("metodo") or gastos.MANUAL,
                # **El motivo viaja con el trozo** (ver `models.RepartoDeCoste.no_se_reparte`): es lo
                # que permite decir «sin asignar, y es porque falta la superficie de una tierra» al
                # volver a abrir el gasto, y no solo en la respuesta del momento.
                no_se_reparte=cuadre.no_se_reparte or None,
                confirmado_por_el_agricultor=confirmado,
            )
        )
    _el_rastro(
        db,
        explotacion.id,
        entidad="gasto",
        entidad_id=gasto.id,
        accion="repartir",
        datos={
            "repartido": dinero.a_texto(cuadre.repartido),
            "sin_asignar": dinero.a_texto(cuadre.sin_asignar),
        },
    )


def _el_aviso_de_un_reparto_que_no_se_puede(porque: str, gasto: models.Gasto) -> str:
    """El aviso de un reparto que no se ha podido hacer, con el motivo exacto y qué hacer.

    Se dice cuál de los tres motivos es, porque se arreglan en sitios distintos: uno pide poner el
    importe del gasto, otro pide la superficie de la tierra y el otro pide decir el método. Un aviso
    genérico («no se ha podido repartir») dejaría al agricultor sin saber dónde ir.
    """
    if porque == gastos.NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE:
        return textos.mensaje("G9_el_gasto_no_tiene_importe_y_no_se_puede_repartir")
    if porque == gastos.NO_SE_REPARTE_PORQUE_FALTA_UN_PESO:
        return textos.mensaje("G6_no_se_puede_repartir_porque_falta_la_superficie")
    if porque == "se_ha_repartido_mas_que_el_gasto":
        return textos.mensaje("G7_el_reparto_a_mano_suma_mas_que_el_gasto")
    return textos.mensaje("G28_el_reparto_no_cuadra", falta=dinero.formatea(gasto.importe))


@router.post("/gastos/{gasto_id}/sin-asignar")
def dejarlo_sin_asignar(
    gasto_id: int, datos: RepartoDeUnGastoEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Deja el gasto entero en «sin asignar», **diciéndolo**: es una respuesta, no un hueco.

    Es lo que el agricultor elige cuando no sabe a qué va ese coste (la luz de la nave, el seguro que
    cubre toda la finca). El importe entero se queda sin asignar, el cuadre sigue cuadrando
    (repartido 0 + sin asignar el total = el total) y el coste **no desaparece de las cuentas**: lo
    que no está es atribuido a nadie.
    """
    gasto = obtener_de_la_explotacion(db, models.Gasto, gasto_id, explotacion.id)
    porque = datos.porque or gastos.NO_SE_REPARTE_PORQUE_NO_HA_DICHO_EL_METODO
    for viejo in _sus_repartos(db, explotacion.id, gasto.id):
        correcciones.borrar(
            db, registro=viejo, entidad="reparto_de_coste", explotacion_id=explotacion.id
        )
    cuadre = gastos.el_gasto_queda_sin_asignar(gasto.importe, porque=porque)
    _guardar_los_repartos(db, explotacion, gasto, cuadre, confirmado=False)
    db.commit()
    avisos = [textos.mensaje("G29_el_gasto_se_queda_sin_asignar_diciendolo")]
    if cuadre.entero is None:
        avisos.append(textos.mensaje("G9_el_gasto_no_tiene_importe_y_no_se_puede_repartir"))
    return {"gasto": _como_se_ve_un_gasto(db, explotacion, gasto), "avisos": avisos}


@router.delete("/gastos/{gasto_id}/repartos/{reparto_id}")
def quitar_un_reparto(
    gasto_id: int, reparto_id: int, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Quita un trozo del reparto, **dejando el rastro entero** de lo que había.

    Un reparto no se borra a secas: se borra con `correcciones.borrar`, que escribe en la auditoría lo
    que decía esa fila. El coste que llevaba ese trozo **vuelve a quedar sin asignar**, y eso se dice:
    es la regla del ticket, y el motivo de que quitar un trozo no pueda dejar el gasto «cuadrado» por
    arte del olvido.
    """
    gasto = obtener_de_la_explotacion(db, models.Gasto, gasto_id, explotacion.id)
    reparto = obtener_de_la_explotacion(db, models.RepartoDeCoste, reparto_id, explotacion.id)
    if reparto.gasto_id != gasto.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    correcciones.borrar(
        db, registro=reparto, entidad="reparto_de_coste", explotacion_id=explotacion.id
    )
    db.commit()
    return {"gasto": _como_se_ve_un_gasto(db, explotacion, gasto), "avisos": []}


# --------------------------------------------------------------------------
# Las inversiones: comprar un activo no es gastar en el cultivo
# --------------------------------------------------------------------------


@router.post("/gastos/inversiones", status_code=status.HTTP_201_CREATED)
def apuntar_una_inversion(
    datos: InversionEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Apunta un bien que se compra para durar: el tractor, la sembradora, la nave.

    **No se apunta como gasto, y ese es el motivo de que esta puerta exista.** Si el tractor de
    60.000 € entrara como gasto del año, el margen de esa campaña diría que se perdió dinero y los
    tres años siguientes que fue gratis. Lo que de la inversión va a cada campaña lo dice el
    agricultor con un reparto, y mientras no lo diga se queda **sin asignar y se ve**.
    """
    if datos.clave_de_reenvio:
        ya = db.scalar(
            select(models.InversionDeLaFinca).where(
                models.InversionDeLaFinca.explotacion_id == explotacion.id,
                models.InversionDeLaFinca.clave_de_reenvio == datos.clave_de_reenvio,
                models.InversionDeLaFinca.anulada.is_(False),
            )
        )
        if ya is not None:
            repartido = _repartido_de_una_inversion(db, explotacion.id, ya.id)
            return {"inversion": _como_se_ve_una_inversion(ya, repartido=repartido), "ya_estaba": True}
    concepto = (datos.concepto or "").strip()
    if not concepto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G30_la_inversion_necesita_saber_que_es"),
        )
    categoria = _de_la_lista(
        datos.categoria or "otro",
        gastos.CATEGORIAS_DE_INVERSION,
        codigo="G31_esa_categoria_de_inversion_no_existe",
        lista=", ".join(gastos.CATEGORIAS_DE_INVERSION),
    )
    for modelo, identificador in (
        (models.Contacto, datos.contacto_id),
        (models.Factura, datos.factura_id),
        (models.Maquina, datos.maquina_id),
        (models.Parcela, datos.parcela_id),
        (models.Campana, datos.campana_id),
    ):
        if identificador is not None:
            obtener_de_la_explotacion(db, modelo, identificador, explotacion.id)
    importe = _un_importe_que_se_puede_guardar(datos.importe, codigo="G15_eso_no_es_un_importe")
    if importe is not None and importe == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G12_la_inversion_de_cero_euros_no_es_una_inversion"),
        )
    inversion = models.InversionDeLaFinca(
        explotacion_id=explotacion.id,
        campana_id=datos.campana_id,
        fecha=datos.fecha,
        concepto=concepto,
        categoria=categoria,
        proveedor=(datos.proveedor or "").strip() or None,
        proveedor_nif=(datos.proveedor_nif or "").strip() or None,
        contacto_id=datos.contacto_id,
        factura_id=datos.factura_id,
        maquina_id=datos.maquina_id,
        parcela_id=datos.parcela_id,
        importe=importe,
        valor_residual=_un_importe_que_se_puede_guardar(
            datos.valor_residual, codigo="G15_eso_no_es_un_importe"
        ),
        notas=datos.notas,
        clave_de_reenvio=datos.clave_de_reenvio,
    )
    db.add(inversion)
    db.flush()
    _el_rastro(
        db,
        explotacion.id,
        entidad="inversion",
        entidad_id=inversion.id,
        accion="crear",
        datos={"concepto": concepto, "importe": dinero.a_texto(importe)},
    )
    db.commit()
    avisos = [textos.mensaje("G32_una_inversion_no_es_un_gasto_del_ano")]
    if importe is None:
        avisos.append(textos.mensaje("G33_la_inversion_se_ha_guardado_sin_importe"))
    return {
        "inversion": _como_se_ve_una_inversion(inversion, repartido=dinero.CERO),
        "ya_estaba": False,
        "avisos": avisos,
    }


@router.get("/gastos/inversiones")
def ver_las_inversiones(explotacion: ExplotacionActual, db: Db) -> dict:
    """Las inversiones de la finca, cada una con lo repartido y lo que sigue sin asignar."""
    inversiones = list(
        db.scalars(
            select(models.InversionDeLaFinca)
            .where(models.InversionDeLaFinca.explotacion_id == explotacion.id)
            .order_by(models.InversionDeLaFinca.id.desc())
        )
    )
    return {
        "inversiones": [
            _como_se_ve_una_inversion(
                inversion, repartido=_repartido_de_una_inversion(db, explotacion.id, inversion.id)
            )
            for inversion in inversiones
        ]
    }


@router.post("/gastos/inversiones/{inversion_id}/anular")
def anular_una_inversion(
    inversion_id: int, datos: AnulacionEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Anula una inversión con su motivo, y sus repartos dejan de contar."""
    inversion = obtener_de_la_explotacion(db, models.InversionDeLaFinca, inversion_id, explotacion.id)
    motivo = (datos.motivo or "").strip()
    if not motivo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G22_para_anular_hace_falta_el_motivo"),
        )
    inversion.anulada = True
    inversion.motivo_anulacion = motivo
    _el_rastro(
        db,
        explotacion.id,
        entidad="inversion",
        entidad_id=inversion.id,
        accion="anular",
        datos={"motivo": motivo},
    )
    for reparto in db.scalars(
        select(models.RepartoDeCoste).where(
            models.RepartoDeCoste.explotacion_id == explotacion.id,
            models.RepartoDeCoste.inversion_id == inversion.id,
            models.RepartoDeCoste.anulado.is_(False),
        )
    ):
        reparto.anulado = True
        reparto.motivo_anulacion = textos.mensaje("G23_su_gasto_se_anulo")
    db.commit()
    return {
        "inversion": _como_se_ve_una_inversion(inversion, repartido=dinero.CERO),
        "avisos": [textos.mensaje("G34_inversion_anulada", motivo=motivo)],
    }


# --------------------------------------------------------------------------
# Los pagos: parciales, agrupados y reversibles
# --------------------------------------------------------------------------


@router.post("/gastos/pagos", status_code=status.HTTP_201_CREATED)
def apuntar_un_pago(datos: PagoEntrada, explotacion: ExplotacionActual, db: Db) -> dict:
    """Apunta el dinero que sale, y opcionalmente contra qué gastos va.

    **Un pago no es un gasto.** Se puede apuntar el dinero que sale sin decir a qué va (lo normal
    cuando se mira el banco antes que los papeles): el pago queda **sin conciliar** y la pantalla lo
    enseña en su lista, esperando. Y conciliar después **no crea ningún gasto**: solo escribe contra
    qué iba ese dinero.

    Un importe **no puede ser cero ni negativo**: un pago de cero euros no es un pago, y admitirlo
    llenaría la lista de renglones que no dicen nada.
    """
    importe = _un_importe_que_se_puede_guardar(datos.importe, codigo="G15_eso_no_es_un_importe")
    if importe is None or importe <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G3_el_pago_tiene_que_ser_mayor_que_cero"),
        )
    if datos.clave_de_reenvio:
        ya = db.scalar(
            select(models.PagoDeGasto).where(
                models.PagoDeGasto.explotacion_id == explotacion.id,
                models.PagoDeGasto.clave_de_reenvio == datos.clave_de_reenvio,
                models.PagoDeGasto.anulado.is_(False),
            )
        )
        if ya is not None:
            # **La misma clave con otros datos es un conflicto, no un reenvío** (09/10/2026, lo cazó el
            # revisor): esta puerta devolvía el pago que ya estaba **y tiraba los datos nuevos en
            # silencio**, así que un dinero de 900 € apuntado con una clave ya usada por uno de 50 €
            # contestaba «ya estaba» y los 900 se perdían sin que nadie lo dijera. Es la misma regla que
            # la puerta de las facturas: una petición identifica **un** comando.
            if (
                dinero.a_texto(dinero.a_decimal(datos.importe)) != dinero.a_texto(ya.importe)
                or datos.fecha != ya.fecha
                or (datos.forma or "transferencia") != (ya.forma or "")
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=textos.mensaje("G41_la_misma_clave_con_otros_datos"),
                )
            return {
                "pago": _como_se_ve_un_pago(db, explotacion, ya),
                "ya_estaba": True,
                "avisos": [],
            }
    forma = _de_la_lista(
        datos.forma or "transferencia",
        ventas.FORMAS_DE_COBRO,
        codigo="G10_esa_forma_de_pago_no_es_ninguna_de_las_que_hay",
        lista=", ".join(ventas.FORMAS_DE_COBRO),
    )
    if datos.contacto_id is not None:
        obtener_de_la_explotacion(db, models.Contacto, datos.contacto_id, explotacion.id)
    pago = models.PagoDeGasto(
        explotacion_id=explotacion.id,
        fecha=datos.fecha,
        importe=importe,
        proveedor=(datos.proveedor or "").strip() or None,
        contacto_id=datos.contacto_id,
        forma=forma,
        referencia=(datos.referencia or "").strip() or None,
        notas=datos.notas,
        clave_de_reenvio=datos.clave_de_reenvio,
    )
    db.add(pago)
    db.flush()
    avisos = _aplicar_al_pago(db, explotacion, pago, datos.aplicaciones, automatico=False, gastos_marcados=[])
    _el_rastro(
        db,
        explotacion.id,
        entidad="pago",
        entidad_id=pago.id,
        accion="crear",
        datos={
            "importe": dinero.a_texto(importe),
            "aplicaciones": len(_aplicaciones_vivas(db, explotacion.id, pago.id)),
        },
    )
    db.commit()
    return {"pago": _como_se_ve_un_pago(db, explotacion, pago), "ya_estaba": False, "avisos": avisos}


def _aplicar_al_pago(
    db: Db,
    explotacion,
    pago: models.PagoDeGasto,
    aplicaciones,
    *,
    automatico: bool,
    gastos_marcados: list[int] | None = None,
) -> list[str]:
    """Escribe contra qué gastos va ese dinero. **Es lo único que hace la conciliación.**

    Dos reglas, y las dos con prueba:

      1. **No se puede aplicar más dinero del que tiene el pago.** Si el agricultor dice que 300 € de
         un pago de 200 € van a un gasto, eso es un error de tecleo y se dice con las dos cifras, en
         vez de dejar un pago que no cuadra por ningún lado.
      2. **No se puede aplicar a un gasto más de lo que debe.** Con 121 € de gasto y 40 € ya
         aplicados, lo que queda son 81 €: aplicar 100 dejaría el gasto con pendiente negativo, que es
         justo lo que no se puede sumar.
    """
    importe = dinero.a_decimal(pago.importe) or dinero.CERO
    ya_aplicado = dinero.suma(*[a.importe for a in _aplicaciones_vivas(db, explotacion.id, pago.id)])
    libre = dinero.redondea(importe - ya_aplicado)
    if libre <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("G8_ese_pago_ya_no_tiene_dinero_libre"),
        )
    avisos: list[str] = []
    if automatico:
        pendientes = []
        for gasto_id in gastos_marcados:
            gasto = obtener_de_la_explotacion(db, models.Gasto, int(gasto_id), explotacion.id)
            pagado = _lo_pagado(db, explotacion.id, gasto.id)
            pendientes.append((gasto.id, gastos.pendiente_de(gasto.importe, pagado)))
        reparto = gastos.reparto_de_un_pago(libre, pendientes)
        if reparto.sin_importe:
            avisos.append(
                textos.mensaje(
                    "G35_hay_gastos_sin_importe_y_no_se_les_aplica_el_dinero",
                    cuantos=len(reparto.sin_importe),
                )
            )
        for aplicacion in reparto.aplicaciones:
            db.add(
                models.AplicacionDeUnPago(
                    explotacion_id=explotacion.id,
                    pago_id=pago.id,
                    gasto_id=aplicacion.gasto_id,
                    importe=aplicacion.importe,
                )
            )
        if reparto.sin_conciliar > 0:
            avisos.append(
                textos.mensaje(
                    "G36_una_parte_del_pago_queda_sin_conciliar",
                    importe=dinero.formatea(reparto.sin_conciliar),
                )
            )
    for aplicacion in aplicaciones or []:
        gasto = obtener_de_la_explotacion(db, models.Gasto, aplicacion.gasto_id, explotacion.id)
        pagado = _lo_pagado(db, explotacion.id, gasto.id)
        pendiente = gastos.pendiente_de(gasto.importe, pagado)
        if pendiente is None:
            avisos.append(
                textos.mensaje(
                    "G37_a_este_gasto_no_se_le_puede_aplicar_dinero_sin_saber_lo_que_costo",
                    concepto=gasto.concepto,
                )
            )
            continue
        quiere = _un_importe_que_se_puede_guardar(
            aplicacion.importe, codigo="G15_eso_no_es_un_importe"
        )
        if quiere is None:
            quiere = pendiente if pendiente <= libre else libre
        if quiere > pendiente:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje(
                    "G4_un_pago_no_puede_aplicarse_mas_de_lo_que_se_debe",
                    quiere=dinero.formatea(quiere),
                    pendiente=dinero.formatea(pendiente),
                    concepto=gasto.concepto,
                ),
            )
        if quiere > libre:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=textos.mensaje(
                    "G38_ese_pago_no_tiene_tanto_dinero_libre",
                    quiere=dinero.formatea(quiere),
                    libre=dinero.formatea(libre),
                ),
            )
        if quiere <= 0:
            continue
        db.add(
            models.AplicacionDeUnPago(
                explotacion_id=explotacion.id,
                pago_id=pago.id,
                gasto_id=gasto.id,
                importe=dinero.redondea(quiere),
            )
        )
        libre = dinero.redondea(libre - quiere)
        _el_rastro(
            db,
            explotacion.id,
            entidad="pago",
            entidad_id=pago.id,
            accion="conciliar",
            datos={"gasto_id": gasto.id, "importe": dinero.a_texto(quiere)},
        )
    return avisos


@router.get("/gastos/pagos")
def ver_los_pagos(explotacion: ExplotacionActual, db: Db) -> dict:
    """Los pagos y **lo que no se sabe a qué va**, que es el dinero que está esperando."""
    pagos = list(
        db.scalars(
            select(models.PagoDeGasto)
            .where(models.PagoDeGasto.explotacion_id == explotacion.id)
            .order_by(models.PagoDeGasto.fecha.desc(), models.PagoDeGasto.id.desc())
        )
    )
    vistos = [_como_se_ve_un_pago(db, explotacion, pago) for pago in pagos]
    return {
        "pagos": vistos,
        "sin_conciliar": [
            pago for pago in vistos if not pago["anulado"] and not pago["aplicaciones"]
        ],
    }


@router.post("/gastos/pagos/{pago_id}/conciliar")
def conciliar_un_pago(
    pago_id: int, datos: ConciliacionDePagoEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Dice contra qué gastos va un dinero que ya estaba apuntado. **No crea ningún gasto.**

    Con `automatico` y una lista de gastos, el dinero se reparte **por orden, el más antiguo
    primero** (`gastos.reparto_de_un_pago`): es la regla de cualquier cuenta corriente y la que hace
    que la suma de lo aplicado sea exactamente el dinero disponible, sin un céntimo perdido y sin
    repartos por porcentaje.

    Y lo que sobra **no se reparte**: se queda dicho como «sin conciliar», esperando a saber a qué va
    o a devolverse. Dejarlo aplicado a un gasto lo pondría con pendiente negativo, que no se puede
    sumar con los demás.
    """
    pago = obtener_de_la_explotacion(db, models.PagoDeGasto, pago_id, explotacion.id)
    if pago.anulado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("G39_ese_pago_esta_anulado"),
        )
    avisos = _aplicar_al_pago(
        db,
        explotacion,
        pago,
        datos.aplicaciones,
        automatico=datos.automatico,
        gastos_marcados=list(datos.gastos),
    )
    db.commit()
    return {"pago": _como_se_ve_un_pago(db, explotacion, pago), "avisos": avisos}


@router.delete("/gastos/pagos/{pago_id}/aplicaciones/{aplicacion_id}")
def deshacer_una_conciliacion(
    pago_id: int, aplicacion_id: int, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Deshace una conciliación **sin borrar el movimiento original**.

    Lo que se borra es la fila que decía «este dinero va contra este gasto», y no a secas: con
    `correcciones.borrar`, que deja en la auditoría lo que decía. El pago **sigue apuntado con su
    importe entero** y vuelve a estar sin conciliar, y el gasto vuelve a estar pendiente. Es
    literalmente el contrato: «Deshacer conciliación no borra el movimiento original».
    """
    pago = obtener_de_la_explotacion(db, models.PagoDeGasto, pago_id, explotacion.id)
    aplicacion = obtener_de_la_explotacion(
        db, models.AplicacionDeUnPago, aplicacion_id, explotacion.id
    )
    if aplicacion.pago_id != pago.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    correcciones.borrar(
        db, registro=aplicacion, entidad="aplicacion_de_pago", explotacion_id=explotacion.id
    )
    db.commit()
    avisos = [textos.mensaje("G40_el_pago_sigue_apuntado_y_sin_conciliar")]
    vista = _como_se_ve_un_pago(db, explotacion, pago)
    return {"pago": vista, "avisos": avisos}


@router.post("/gastos/pagos/{pago_id}/anular")
def anular_un_pago(
    pago_id: int, datos: AnulacionEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Anula un pago con su motivo: el dinero no salió, y los gastos vuelven a estar pendientes.

    Los efectos se revierten quitando las aplicaciones (con su rastro), y **el pago sigue en el
    cuaderno**, tachado y con el motivo, porque un pago anulado sigue siendo un hecho que ocurrió:
    alguien lo apuntó y alguien lo deshizo.
    """
    pago = obtener_de_la_explotacion(db, models.PagoDeGasto, pago_id, explotacion.id)
    motivo = (datos.motivo or "").strip()
    if not motivo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G22_para_anular_hace_falta_el_motivo"),
        )
    pago.anulado = True
    pago.motivo_anulacion = motivo
    _el_rastro(
        db,
        explotacion.id,
        entidad="pago",
        entidad_id=pago.id,
        accion="anular",
        datos={"motivo": motivo, "importe": dinero.a_texto(pago.importe)},
    )
    for aplicacion in _aplicaciones_vivas(db, explotacion.id, pago.id):
        db.delete(aplicacion)
        _el_rastro(
            db,
            explotacion.id,
            entidad="aplicacion_de_pago",
            entidad_id=aplicacion.id,
            accion="quitar_al_anular_el_pago",
            datos={"gasto_id": aplicacion.gasto_id, "importe": dinero.a_texto(aplicacion.importe)},
        )
    db.commit()
    return {
        "pago": _como_se_ve_un_pago(db, explotacion, pago),
        "avisos": [textos.mensaje("G41_pago_anulado", motivo=motivo)],
    }


# --------------------------------------------------------------------------
# Las subvenciones: tres estados que no se suman entre sí
# --------------------------------------------------------------------------


@router.post("/gastos/subvenciones", status_code=status.HTTP_201_CREATED)
def apuntar_una_subvencion(
    datos: SubvencionEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Apunta una ayuda con **sus tres importes separados**: previsto, concedido y cobrado.

    Son tres columnas y no una con un estado, porque los tres pueden convivir: se pidió una ayuda
    esperando 12.000 €, le concedieron 9.000 y todavía no ha entrado nada. Con una sola columna,
    apuntar la concesión borraría la previsión, y el agricultor perdería la cuenta de lo que pidió.

    Y solo el importe cobrado cuenta como ingreso: **la previsión no se suma al ingreso cobrado**
    (regla del contrato en S13). La previsión se enseña, con su palabra, en su propia tarjeta.
    """
    concepto = (datos.concepto or "").strip()
    if not concepto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G42_la_ayuda_necesita_saber_de_que_es"),
        )
    if datos.campana_id is not None:
        obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)
    subvencion = models.Subvencion(
        explotacion_id=explotacion.id,
        campana_id=datos.campana_id,
        concepto=concepto,
        organismo=(datos.organismo or "").strip() or None,
        fecha_solicitud=datos.fecha_solicitud,
        fecha_concesion=datos.fecha_concesion,
        fecha_cobro=datos.fecha_cobro,
        importe_previsto=_un_importe_que_se_puede_guardar(
            datos.importe_previsto, codigo="G15_eso_no_es_un_importe"
        ),
        importe_concedido=_un_importe_que_se_puede_guardar(
            datos.importe_concedido, codigo="G15_eso_no_es_un_importe"
        ),
        importe_cobrado=_un_importe_que_se_puede_guardar(
            datos.importe_cobrado, codigo="G15_eso_no_es_un_importe"
        ),
        notas=datos.notas,
        clave_de_reenvio=datos.clave_de_reenvio,
    )
    db.add(subvencion)
    db.flush()
    _el_rastro(
        db,
        explotacion.id,
        entidad="subvencion",
        entidad_id=subvencion.id,
        accion="crear",
        datos={"concepto": concepto},
    )
    db.commit()
    vista = _como_se_ve_una_subvencion(subvencion)
    avisos = []
    if vista["estado"] == gastos.PREVISTA:
        avisos.append(textos.mensaje("G43_una_ayuda_prevista_no_es_un_ingreso"))
    return {"subvencion": vista, "avisos": avisos}


@router.get("/gastos/subvenciones")
def ver_las_subvenciones(explotacion: ExplotacionActual, db: Db) -> dict:
    """Las ayudas de la finca, **con lo previsto, lo concedido y lo cobrado por separado**."""
    subvenciones = list(
        db.scalars(
            select(models.Subvencion)
            .where(models.Subvencion.explotacion_id == explotacion.id)
            .order_by(models.Subvencion.id.desc())
        )
    )
    vistas = [_como_se_ve_una_subvencion(subvencion) for subvencion in subvenciones]
    vivas = [
        {
            "estado": vista["estado"],
            "importe": vista["importe_cobrado"]
            or vista["importe_concedido"]
            or vista["importe_previsto"],
        }
        for vista in vistas
        if not vista["anulada"]
    ]
    return {
        "subvenciones": vistas,
        "ingreso_cobrado": dinero.a_texto(gastos.ingreso_cobrado_de_subvenciones(vivas)),
        "importe_previsto": dinero.a_texto(gastos.importe_previsto_de_subvenciones(vivas)),
        "texto_ingreso_cobrado": dinero.formatea(gastos.ingreso_cobrado_de_subvenciones(vivas)),
        "texto_importe_previsto": dinero.formatea(gastos.importe_previsto_de_subvenciones(vivas)),
    }


@router.post("/gastos/subvenciones/{subvencion_id}/anular")
def anular_una_subvencion(
    subvencion_id: int, datos: AnulacionEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Anula una ayuda con su motivo: deja de contar como ingreso y se conserva el rastro."""
    subvencion = obtener_de_la_explotacion(db, models.Subvencion, subvencion_id, explotacion.id)
    motivo = (datos.motivo or "").strip()
    if not motivo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("G22_para_anular_hace_falta_el_motivo"),
        )
    subvencion.anulada = True
    subvencion.motivo_anulacion = motivo
    _el_rastro(
        db,
        explotacion.id,
        entidad="subvencion",
        entidad_id=subvencion.id,
        accion="anular",
        datos={"motivo": motivo},
    )
    db.commit()
    return {
        "subvencion": _como_se_ve_una_subvencion(subvencion),
        "avisos": [textos.mensaje("G44_ayuda_anulada", motivo=motivo)],
    }


# --------------------------------------------------------------------------
# Los traspasos entre cuentas propias: ni ingreso ni gasto (A07)
# --------------------------------------------------------------------------


@router.post("/gastos/traspaso")
def un_traspaso_entre_cuentas_propias(
    datos: dict, explotacion: ExplotacionActual, _usuario: UsuarioActual
) -> dict:
    """Dos movimientos atados y **cero ingreso y cero gasto operativo** (caso A07 del contrato).

    Esta puerta **no escribe nada**, y eso es lo importante: un traspaso de una cuenta propia a otra
    no es un ingreso ni un gasto, así que no puede acabar en la lista de gastos ni en la de ingresos.
    Lo que hace es decir cómo quedan los dos movimientos, para que los apunte quien corresponda (el
    extracto del banco es el ticket T20, y los movimientos no se guardan aquí todavía).

    Se dice así, y no se disimula: **hoy el traspaso no se guarda en ninguna tabla**, porque la tabla
    de movimientos bancarios es del ticket siguiente. Lo que sí se garantiza desde ya es que el
    programa **no lo va a contar como ingreso**, que es el fallo que el caso A07 existe para impedir.
    """
    traspaso = gastos.traspaso_entre_cuentas_propias(
        datos.get("importe"),
        cuenta_origen=str(datos.get("cuenta_origen") or ""),
        cuenta_destino=str(datos.get("cuenta_destino") or ""),
    )
    del explotacion
    avisos = []
    if not traspaso.vinculados:
        avisos.append(textos.mensaje("G45_un_traspaso_a_la_misma_cuenta_no_es_un_traspaso"))
    return {
        "traspaso": traspaso.como_dict(),
        "se_guarda": False,
        "por_que_no_se_guarda": textos.GASTOS["el_traspaso_no_se_guarda"],
        "avisos": avisos,
    }


# --------------------------------------------------------------------------
# Lo que se puede comprobar sin abrir la aplicación
# --------------------------------------------------------------------------


@router.get("/gastos/cuadre")
def el_cuadre_de_un_gasto(
    explotacion: ExplotacionActual,
    db: Db,
    importe: Decimal | None = None,
    repartido: Decimal | None = None,
    sin_asignar: Decimal | None = None,
) -> dict:
    """El cuadre de un reparto, para que la pantalla pueda enseñarlo **mientras se escribe**.

    Es la misma cuenta que se guarda, pedida a la misma función: así lo que se ve mientras se reparte
    y lo que queda apuntado no pueden decir cosas distintas. Sin esto, la pantalla tendría que sumar
    en el navegador, donde todo número es de coma flotante, y el céntimo del redondeo aparecería
    justo al guardar.
    """
    del explotacion, db
    cuadre = gastos.cuadre_del_reparto(
        importe,
        [] if sin_asignar is None and repartido is None else [
            {"destino_tipo": gastos.TIERRA, "destino": "repartido", "importe": repartido},
            {"destino_tipo": gastos.SIN_ASIGNAR, "destino": "", "importe": sin_asignar},
        ],
    )
    return {
        **cuadre.como_dict(),
        "texto_repartido": dinero.formatea(cuadre.repartido),
        "texto_sin_asignar": dinero.formatea(cuadre.sin_asignar),
        "texto_falta": dinero.formatea(cuadre.falta),
    }


@router.get("/gastos/que-falta")
def lo_que_falta_de_las_cuentas() -> list[dict]:
    """Lo que este programa **todavía no calcula** en las cuentas, con de quién depende.

    Se sirve aparte para que la pantalla pueda decirlo sin abrir ningún gasto: sin esto, el
    agricultor creería que una cifra que no aparece es un fallo del programa en vez de un dato que
    falta (la receta de `AGENTS.md`, aplicada igual que en la maquinaria del T14).
    """
    return [dict(uno) for uno in gastos.QUE_FALTA]


# --------------------------------------------------------------------------
# Referencias que usa la pantalla, para que no haya dos listas que se separen
# --------------------------------------------------------------------------


def las_categorias() -> dict:
    """Las dos listas de categorías, **nuestras** y dichas como nuestras.

    No hay ningún catálogo oficial de categorías cargado, así que estas son las que usa un agricultor
    cuando separa sus papeles. Se ofrecen para no teclear, no para obligar: lo que no encaje va a
    «otro» y su concepto dice lo que es.
    """
    return {
        "gasto": list(gastos.CATEGORIAS_DE_GASTO),
        "inversion": list(gastos.CATEGORIAS_DE_INVERSION),
    }


# --------------------------------------------------------------------------
# Lo que ha costado una tierra (T13 + T15, 05/10/2026)
# --------------------------------------------------------------------------
#
# **Va antes de la ficha de un gasto, y a propósito**: en este fichero las rutas de palabra fija van
# delante de las de identificador (ver el comentario del final), y «de-una-tierra» es una palabra fija.


@router.get("/gastos/de-una-tierra/{parcela_id}")
def lo_que_ha_costado_una_tierra(
    parcela_id: int,
    explotacion: ExplotacionActual,
    db: Db,
    campana_id: int | None = None,
) -> dict:
    """**Cuánto ha costado una tierra: lo que consta, y lo que no.**

    Es la mitad que le faltaba a la ficha de una tierra (el recorrido 5 del encargo: «qué cultivo tiene,
    qué trabajos se han hecho, qué queda previsto y **qué costes conocidos tiene**»): los trabajos ya
    salían en su historial (T15) y el dinero no.

    **Cómo se cuenta, y por qué así.** Son **dos cifras separadas** y no una sola suma, por el mismo
    motivo que en la pantalla de las cuentas: un coste **directo** es lo que pone el papel (un gasto que
    dice «esta tierra»), y uno **repartido** es una estimación que acordó el agricultor (un trozo de un
    gasto que se llevó a esta tierra desde la pantalla de las cuentas). Sumarlos en un número solo sería
    decir que son lo mismo.

      · **Directos**: los gastos no anulados que dicen esta tierra (`parcela_id`), con su importe.
      · **Repartidos**: los trozos de reparto no anulados que se llevaron a esta tierra, vengan de un
        gasto o de una inversión.
      · **Sin importe**: cuántos gastos de esta tierra **no dicen lo que costaron**. Se cuentan y se
        dicen: un total que calla que le faltan datos miente, y sumar un cero diría que salió gratis.

    **Y la regla que impide contarlo dos veces**, que es la misma de `_el_coste_por_clase`: un gasto que
    ya dice una tierra (o un cultivo) cuenta **por su importe entero** y **sus repartos no se miran**; si
    no, un gasto directo y repartido saldría por los dos lados. Por eso los repartos que se cuentan aquí
    son solo los de gastos que **no** dicen tierra ni cultivo.

    **Lo que NO hace, y se dice:** ni descuentos, ni margen, ni la parte que le toque de las inversiones.
    Un margen necesita los ingresos de esa tierra —que son de las ventas, y una entrega no dice de qué
    tierra salió— y el reparto de una inversión lo decide el agricultor. Ninguna de las dos cosas está
    resuelta en ningún ticket, así que aquí no se inventan.
    """
    tierra = obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)

    consulta = select(models.Gasto).where(
        models.Gasto.explotacion_id == explotacion.id,
        models.Gasto.parcela_id == parcela_id,
        models.Gasto.anulado.is_(False),
    )
    if campana_id is not None:
        consulta = consulta.where(models.Gasto.campana_id == campana_id)
    suyos = list(db.scalars(consulta.order_by(models.Gasto.fecha.desc(), models.Gasto.id.desc())))

    directos = dinero.CERO
    sin_importe = 0
    filas: list[dict] = []
    for gasto in suyos:
        importe = dinero.a_decimal(gasto.importe)
        if importe is None:
            # **No se suma un cero**: se cuenta aparte y se dice.
            sin_importe += 1
        else:
            directos = dinero.suma(directos, importe)
        filas.append(
            {
                "gasto_id": gasto.id,
                "que_es": gasto.concepto or "",
                "fecha": gasto.fecha,
                "importe": dinero.a_texto(importe),
                "texto_importe": dinero.formatea(importe),
                "de_donde": "directo",
            }
        )

    # Los repartos a esta tierra, de gastos que **no** dicen tierra ni cultivo (si no, se contarían dos
    # veces) y de inversiones (que no tienen esas columnas: una inversión se reparte o no se reparte).
    trozos = list(
        db.scalars(
            select(models.RepartoDeCoste).where(
                models.RepartoDeCoste.explotacion_id == explotacion.id,
                models.RepartoDeCoste.destino_tipo == gastos.TIERRA,
                models.RepartoDeCoste.parcela_id == parcela_id,
                models.RepartoDeCoste.anulado.is_(False),
            )
        )
    )
    repartidos = dinero.CERO
    for trozo in trozos:
        importe = dinero.a_decimal(trozo.importe)
        if trozo.gasto_id is not None:
            gasto = db.get(models.Gasto, trozo.gasto_id)
            if gasto is None or gasto.anulado or gasto.parcela_id or gasto.cultivo:
                continue
            que_es = gasto.concepto or ""
            fecha = gasto.fecha
        else:
            inversion = db.get(models.InversionDeLaFinca, trozo.inversion_id)
            if inversion is None or inversion.anulada:
                continue
            que_es = inversion.concepto or ""
            fecha = inversion.fecha
        if importe is not None:
            repartidos = dinero.suma(repartidos, importe)
        filas.append(
            {
                "gasto_id": trozo.gasto_id,
                "que_es": que_es,
                "fecha": fecha,
                "importe": dinero.a_texto(importe),
                "texto_importe": dinero.formatea(importe),
                "de_donde": "repartido",
                "porque": trozo.metodo or gastos.MANUAL,
            }
        )

    filas.sort(key=lambda fila: (fila["fecha"] is None, fila["fecha"] or "", -(fila["gasto_id"] or 0)))
    total = dinero.suma(directos, repartidos)
    return {
        "parcela_id": tierra.id,
        "tierra": tierra.alias,
        "campana_id": campana_id,
        "directos": dinero.a_texto(directos),
        "texto_directos": dinero.formatea(directos),
        "repartidos": dinero.a_texto(repartidos),
        "texto_repartidos": dinero.formatea(repartidos),
        "total_conocido": dinero.a_texto(total),
        "texto_total": dinero.formatea(total),
        # **Cuántos gastos no dicen lo que costaron**, y cuántas líneas tiene la cuenta. Un total sin
        # esto parece completo cuando no lo está.
        "sin_importe": sin_importe,
        "cuantos": len(filas),
        "filas": filas,
    }


# --------------------------------------------------------------------------
# La ficha de un gasto, **la última ruta del fichero y a propósito**
# --------------------------------------------------------------------------
#
# `GET /gastos/{gasto_id}` va la última porque FastAPI mira las rutas **en el orden en que están
# escritas**: si estuviera antes que `/gastos/pagos`, `/gastos/avisos` o `/gastos/cuadre`, la palabra
# «pagos» se leería como un identificador de gasto, no cuadraría con un número y el agricultor
# recibiría un «revisa lo que has escrito» al abrir una pantalla que existe. Es el mismo cuidado que
# tiene `rutas.js` con los tramos de texto fijo por delante de los identificadores, y hay una prueba
# que comprueba que las cinco rutas de palabra fija llegan de verdad a su función.


@router.get("/gastos/{gasto_id}")
def ver_un_gasto(gasto_id: int, explotacion: ExplotacionActual, db: Db) -> dict:
    """La ficha de un gasto: sus cuentas, sus repartos, lo pagado y lo que queda por pagar.

    Es **la misma vista** que la de la lista (`_como_se_ve_un_gasto`), y por eso no puede pasar que
    la fila de la tabla y la ficha digan cosas distintas: las dos salen de la misma función.
    """
    gasto = obtener_de_la_explotacion(db, models.Gasto, gasto_id, explotacion.id)
    return _como_se_ve_un_gasto(db, explotacion, gasto)
