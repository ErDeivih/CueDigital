"""**El panel de la finca: las metricas que se pueden defender** (CRM-11, 17/10/2026).

El contrato de la cola lo pide con estas palabras:

    ***valor nullable, unidad, periodo, finca/campana, filtros, cobertura, fuente y enlace***.
    ***Hectareas de trabajo acumulado distintas de superficie unica; kg distintos de EUR.***

*Y la idea entera vive en `app/paneles.py`: **un numero que se puede defender**.* Esta puerta la saca de alli
y la pone donde el agricultor pueda verla, **cruzando los datos de verdad de su finca**.

***Tres cosas que hace, y ninguna es adorno***:

  1. **Cada metrica dice de donde sale** (`fuente`): `parcelas`, `labores`, `gastos`, `ventas`... *Un numero
     que no puede decir su fuente no se puede discutir, y lo que no se puede discutir no se puede corregir.*
  2. **Dice cuanto ha mirado** (`cobertura`): *`{"contadas": 8, "de": 12}`. Sin eso, un total parece completo
     aunque le falten cuatro.*
  3. **Lo que no se sabe va como `None`, nunca como cero**: *si a un gasto le falta el importe, **el total de
     gastos no se sabe** -un total al que le falta un sumando no es un total mas pequeño-.*

***Y las que contestan a preguntas distintas NO se suman***, aunque las dos se midan en hectareas: *este
programa ya sabe que «lo que hay plantado» y «lo que se trato» no son lo mismo, y el panel no lo deshace.*
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from .. import accesos, models, paneles, superficies, textos
from ..deps import Db, ExplotacionActual, UsuarioActual

router = APIRouter(prefix="/api/panel", tags=["panel"])


def _la_suma(valores: list) -> float | None:
    """**La suma, o `None` si algun sumando no consta.**

    *Un total al que le falta un sumando **no es un total mas pequeño**, es un total que no se sabe -*la regla
    de toda la casa, y en un panel es la que impide enseñar un numero que miente-.*
    """
    return None if any(uno is None for uno in valores) else round(sum(float(uno) for uno in valores), 4)


def _la_campana(db, explotacion_id: int, campana_id: int | None):
    """La campana pedida, o **la mas nueva** de la finca. *`None` es «esta finca no tiene ninguna»*."""
    consulta = select(models.Campana).where(models.Campana.explotacion_id == explotacion_id)
    if campana_id is not None:
        return db.scalar(consulta.where(models.Campana.id == campana_id))
    return db.scalar(consulta.order_by(models.Campana.anio.desc()))


def _de_la_campana(consulta, modelo, la_campana):
    """Acota a la campana **cuando el modelo cuelga del año**. *Los que no cuelgan -los trabajos de un
    tercero- no se acotan: se cuentan todos, y `periodo` lo dice.*"""
    if la_campana is not None and hasattr(modelo, "campana_id"):
        return consulta.where(modelo.campana_id == la_campana.id)
    return consulta


@router.get("")
def el_panel(
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    campana_id: int | None = None,
) -> dict:
    """**Las metricas de la finca, cada una con su unidad, su fuente y su cobertura.**

    ***Y el dinero, solo para quien puede verlo*** (18/10/2026, revision independiente): *sin la capacidad
    economica, **la metrica de gastos no se construye y no viaja** -ni el importe, ni el subtotal, ni la
    cobertura-. **Esconderla en la pantalla no sirve**: el dinero ya habria salido por la red -y la revision lo
    reproduce: `/api/contactos/{id}/saldo` daba **403** y `/api/panel` daba **200** con los 123,45 € dentro-.*

    *Se **quita la metrica entera**, no se pone a cero: un cero afirma «no se ha gastado nada», que es una cosa
    distinta de «a ti no te lo cuento».*
    """
    puede_ver_el_dinero = accesos.puede_ver_lo_economico(db, usuario.id, explotacion.id)
    la_campana = _la_campana(db, explotacion.id, campana_id)
    periodo = str(la_campana.anio) if la_campana is not None else ""
    comun = {
        "periodo": periodo,
        "finca_id": explotacion.id,
        "campana_id": la_campana.id if la_campana is not None else None,
    }

    # ── 1 · La tierra que hay ──
    parcelas = list(
        db.scalars(select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id))
    )
    la_superficie = superficies.la_superficie_de_la_finca(parcelas)
    metrica_superficie = paneles.la_metrica(
        clave="superficie",
        titulo=textos.LAS_METRICAS["superficie_titulo"],
        valor=la_superficie["total"],
        magnitud=paneles.HECTAREAS_DE_SUPERFICIE,
        pregunta=textos.LAS_METRICAS["superficie_pregunta"],
        cobertura={
            "contadas": sum(1 for una in parcelas if una.superficie_ha is not None),
            "de": len(parcelas),
        },
        fuente="parcelas",
        enlace="#/tierras",
        **comun,
    )

    # ── 2 · El trabajo acumulado: **cinco labores en la misma tierra son cinco veces** ──
    labores = list(
        db.scalars(
            _de_la_campana(
                select(models.Labor).where(
                    models.Labor.explotacion_id == explotacion.id,
                    models.Labor.anulado.is_(False),
                ),
                models.Labor,
                la_campana,
            )
        )
    )
    metrica_trabajo = paneles.la_metrica(
        clave="trabajo",
        titulo=textos.LAS_METRICAS["trabajo_titulo"],
        valor=_la_suma([una.superficie_ha for una in labores]),
        magnitud=paneles.HECTAREAS_DE_TRABAJO,
        pregunta=textos.LAS_METRICAS["trabajo_pregunta"],
        cobertura={
            "contadas": sum(1 for una in labores if una.superficie_ha is not None),
            "de": len(labores),
        },
        fuente="labores",
        **comun,
    )

    # ── 3 · Lo que se trato de verdad ──
    tratamientos = list(
        db.scalars(
            _de_la_campana(
                select(models.TratamientoFitosanitario).where(
                    models.TratamientoFitosanitario.explotacion_id == explotacion.id,
                    models.TratamientoFitosanitario.anulado.is_(False),
                ),
                models.TratamientoFitosanitario,
                la_campana,
            )
        )
    )
    el_tratado = superficies.lo_tratado(tratamientos)
    metrica_tratado = paneles.la_metrica(
        clave="tratado",
        titulo=textos.LAS_METRICAS["tratado_titulo"],
        valor=el_tratado["total"],
        magnitud=paneles.HECTAREAS_DE_TRABAJO,
        pregunta=textos.LAS_METRICAS["tratado_pregunta"],
        cobertura={
            "contadas": sum(
                1 for uno in tratamientos if uno.superficie_tratada_ha is not None
            ),
            "de": len(tratamientos),
        },
        fuente="tratamientos",
        **comun,
    )

    # ── 4 · Lo que se hizo en tierras de otro: **su propia magnitud** ──
    de_terceros = list(
        db.scalars(
            select(models.TrabajoParaUnTercero).where(
                models.TrabajoParaUnTercero.explotacion_id == explotacion.id
            )
        )
    )
    lo_ajeno = superficies.lo_de_un_tercero(de_terceros)
    metrica_tercero = paneles.la_metrica(
        clave="de_tercero",
        titulo=textos.LAS_METRICAS["tercero_titulo"],
        valor=lo_ajeno["total"],
        magnitud=paneles.HECTAREAS_DE_TERCERO,
        pregunta=textos.LAS_METRICAS["tercero_pregunta"],
        cobertura={
            "contadas": sum(1 for uno in de_terceros if uno.superficie_ha is not None),
            "de": len(de_terceros),
        },
        fuente="trabajos de terceros",
        **comun,
    )

    # ── 5 · Lo que se ha gastado (EUR, que no se suma con los kilos) ──
    gastos = list(
        db.scalars(
            _de_la_campana(
                select(models.Gasto).where(
                    models.Gasto.explotacion_id == explotacion.id,
                    models.Gasto.anulado.is_(False),
                ),
                models.Gasto,
                la_campana,
            )
        )
    )
    # ***Y el dinero, solo si se puede ver***: *ni la metrica, ni su valor, ni su cobertura. **No se construye
    # siquiera** -que es la unica forma de que no se cuele por un descuido en `las_metricas` o en las
    # respuestas alternativas-.*
    metrica_gastos = (
        paneles.la_metrica(
            clave="gastos",
            titulo=textos.LAS_METRICAS["gastos_titulo"],
            valor=_la_suma([uno.importe for uno in gastos]),
            magnitud=paneles.EUROS,
            pregunta=textos.LAS_METRICAS["gastos_pregunta"],
            cobertura={
                "contadas": sum(1 for uno in gastos if uno.importe is not None),
                "de": len(gastos),
            },
            fuente="gastos",
            **comun,
        )
        if puede_ver_el_dinero
        else None
    )

    # ── 6 · Lo que ha salido en kilos ──
    ventas = list(
        db.scalars(
            _de_la_campana(
                select(models.VentaDeCosecha).where(
                    models.VentaDeCosecha.explotacion_id == explotacion.id,
                    models.VentaDeCosecha.anulado.is_(False),
                ),
                models.VentaDeCosecha,
                la_campana,
            )
        )
    )
    en_kilos = [una for una in ventas if (una.unidad or "").lower() == paneles.KILOS]
    metrica_cosecha = paneles.la_metrica(
        clave="cosecha",
        titulo=textos.LAS_METRICAS["cosecha_titulo"],
        valor=_la_suma([una.cantidad for una in en_kilos]),
        magnitud=paneles.KILOS,
        pregunta=textos.LAS_METRICAS["cosecha_pregunta"],
        cobertura={"contadas": len(en_kilos), "de": len(ventas)},
        fuente="ventas",
        **comun,
    )

    las_metricas = [
        metrica_superficie,
        metrica_trabajo,
        metrica_tratado,
        metrica_tercero,
        metrica_cosecha,
    ]
    if metrica_gastos is not None:
        las_metricas.insert(4, metrica_gastos)
    return {
        # **Las palabras viajan con los datos**, como en `/api/parcelas/vista`: *este endpoint es el unico
        # que las usa, y asi no hay que tocar `/api/interfaz`.*
        "textos": {
            **textos.LAS_METRICAS,
            "unidades": {
                clave: etiqueta
                for clave, etiqueta in textos.LAS_METRICAS["unidades"].items()
                if puede_ver_el_dinero or clave != paneles.EUROS
            },
        },
        "campana_id": la_campana.id if la_campana is not None else None,
        "campana_anio": la_campana.anio if la_campana is not None else None,
        "las_metricas": las_metricas,
        # ***Y lo que no se puede dar por bueno***: *«sin cumplimiento global que tape una regla critica no
        # comprobada». Si hay algo que no se ha podido mirar, **se dice**, aunque el total salga bien.*
        "sin_comprobar": paneles.lo_que_no_se_ha_comprobado(las_metricas),
        # **Las parejas que se confunden**, para que la pantalla lo pueda avisar sin saberlo de memoria.
        #
        # ***Y las que nombran el dinero tampoco viajan sin la capacidad*** (18/10/2026): *no son un importe,
        # pero son una pista, y la revision pide no dejarlo «ni en subtotales, cobertura, enlaces **ni en
        # respuestas alternativas**».*
        "lo_que_no_se_suma": [
            {"una": una, "otra": otra}
            for una, otra in paneles.LAS_QUE_SE_CONFUNDEN.items()
            if puede_ver_el_dinero or paneles.EUROS not in (una, otra)
        ],
    }
