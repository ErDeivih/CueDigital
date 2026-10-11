"""El cuaderno: resumen, lo que falta, exportación y PDF.

Dos decisiones de usabilidad que están implementadas aquí:

1. **El PDF sale aunque falten datos.** Si el agricultor necesita el papel hoy y le
   falta un dato, se le da el papel y una hoja al final diciendo qué falta. Negarle
   el documento hasta que esté perfecto es la forma más rápida de que abandone.

2. **Se dice qué falta, en castellano y con nombres.** No un contador rojo de
   "3 pendientes", sino "a El Prado le falta decir qué cultivo tiene este año".
"""

from __future__ import annotations

import csv
import datetime as dt
import io

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select

from .. import catalogos, dinero, legal, models, servicios, sigpac, textos
from ..deps import Db, ExplotacionActual

router = APIRouter(prefix="/api", tags=["cuaderno"])

CABECERAS_TRATAMIENTO = [
    "Fecha",
    "Parcela",
    "Cultivo",
    "Superficie (ha)",
    "Producto",
    "Nº etiqueta",
    "Dosis",
    "Cantidad",
    "Días espera",
    "Se puede coger desde",
    "Aplicador",
    "Máquina",
]

CABECERAS_ABONO = [
    "Fecha",
    "Parcela",
    "Superficie (ha)",
    "Abono",
    "kg/ha",
    "Total (kg)",
    "N (kg/ha)",
    "P (kg/ha)",
    "K (kg/ha)",
]

# El «Informe Analíticas» de la app oficial (Utilidades > Ver listados). Una fila por
# análisis, con sus números pegados en una sola casilla: un boletín de tierra trae nueve
# y uno de agua trae tres, así que una columna por parámetro daría una tabla con casi
# todo vacío y con un ancho imposible de imprimir.
CABECERAS_VENTA = [
    "Día",
    "Cómo se vendió",
    "Qué",
    "Variedad",
    "Cuánto",
    # **El dinero de la venta** (CRM-01, 11/10/2026): el cuaderno decía qué se vendió y a quién, pero **no
    # por cuánto**, que es la mitad de lo que se mira en una inspección y en una cuenta. Se añade el importe
    # y el precio, con la misma regla que en las pantallas: los dos son **opcionales** —una entrega puede
    # apuntarse antes de saber el precio (el A08)—, así que cuando no consta se escribe lo que dice el
    # programa en todas partes: «Falta el importe», nunca un cero que parecería una venta de cero euros.
    "Importe",
    "Precio",
    "Partida",
    "A quién",
    "Nº albarán",
    "De dónde",
]

CABECERAS_VENTA_PDF = [
    "Día",
    "Qué",
    "Cuánto",
    "Importe",
    "Precio",
    "A quién",
    "Partida",
    "De dónde",
]

ANCHOS_VENTA_CM = (1.7, 2.6, 2.0, 2.1, 1.9, 4.3, 3.0, 4.0)


def _el_dinero_de_una_venta(valor) -> str:
    """Un importe de una venta para el papel: en euros y con coma, o **dicho con palabras** si no consta.

    Es la regla del «no lo sé» del programa entero, aplicada al cuaderno: un importe que no se apuntó **no es
    cero**, y escribirlo como `0,00 €` en un documento que va a una inspección sería decir algo que no es
    verdad. La frase es la misma que usa la pantalla de lo que se vende (`textos.VENTA`), para que el papel y
    la pantalla digan lo mismo.
    """
    suyo = dinero.a_decimal(valor)
    if suyo is None:
        return textos.VENTA["estado_sin_importe"]
    return dinero.formatea(suyo)

CABECERAS_ANALISIS = [
    "Muestra",
    "Resultado",
    "Qué se analizó",
    "De dónde",
    "Laboratorio",
    "Nº boletín",
    "Números del boletín",
]

CABECERAS_ANALISIS_PDF = [
    "Muestra",
    "Qué",
    "De dónde",
    "Laboratorio",
    "Números del boletín",
]

ANCHOS_ANALISIS_CM = (1.7, 2.2, 2.3, 2.6, 9.8)

# En el PDF los títulos van cortos y las columnas justas: con títulos largos, reportlab
# parte las palabras ("SuperficieProducto") y el cuaderno impreso parece hecho con prisa.
# En el CSV, en cambio, interesa el título largo y descriptivo, porque ahí el ancho de
# columna no es un problema y quien lo abre quiere saber qué es cada número.
CABECERAS_TRATAMIENTO_PDF = [
    "Fecha",
    "Parcela",
    "Cultivo",
    "Sup. (ha)",
    "Producto",
    "Nº etiq.",
    "Dosis",
    "Cantidad",
    "Espera",
    "Coger desde",
    "Quién aplica",
    "Máquina",
]

CABECERAS_ABONO_PDF = [
    "Fecha",
    "Parcela",
    "Sup. (ha)",
    "Abono",
    "kg/ha",
    "Total (kg)",
    "N (kg/ha)",
    "P (kg/ha)",
    "K (kg/ha)",
]

# Anchos en centímetros. El ancho útil de A4 con estos márgenes son 18,6 cm, y las
# tablas van justas a propósito: si se dejan sin anchos, reportlab las desborda y el
# PDF sale con columnas cortadas.
ANCHOS_TRATAMIENTO_CM = (1.45, 1.7, 1.5, 1.15, 2.3, 1.15, 1.2, 1.15, 0.95, 1.45, 1.5, 1.4)
ANCHOS_ABONO_CM = (1.6, 2.1, 1.3, 2.9, 1.15, 1.5, 1.35, 1.35, 1.35)

# Las labores: lo que se hizo en el campo (sembrar, regar, podar, pastorear, coger la cosecha…).
#
# Esta sección **faltaba**, y es de las que más pesa: el contenido mínimo del cuaderno pide las
# labores culturales (bloque 5), el riego (bloque 9) y la siembra y plantación (bloque 6), y en
# este programa los tres son labores de distinto tipo. Se apuntaban y no salían ni en el papel ni
# en el fichero de datos: la peor clase de fallo, porque el agricultor tenía el dato y el
# documento que entrega no lo enseñaba.
CABECERAS_LABOR = ["Fecha", "Labor", "Parcela", "Sup. (ha)", "Cultivo"]

# Lo propio de cada tipo de labor, aparte y en su orden, porque en el papel estas etiquetas se
# juntan con sus valores en una línea: así no hay dos nombres para lo mismo.
CABECERAS_LABOR_DETALLE = [
    "Agua",
    "Unidad del agua",
    "De dónde salió el agua",
    "Sistema de riego",
    "Nº de contador",
    "Semilla (kg)",
    "Dosis (kg/ha)",
    "Lote de la semilla",
    "Semilla tratada",
    "Qué le echaron a la semilla",
    "Cuándo se trató la semilla",
    "Cómo funcionó el tratamiento de la semilla",
    "Semilla comprada",
    "Fecha de la compra",
    "Siembra directa",
    "Marco",
    "Plantas por hectárea",
    "Ganado de otros",
    "Ganado propio",
    # Con qué máquina se hizo la labor. El contenido mínimo del CUE lo pide (bloques de labores y
    # de siembra), y hasta la ronda 4 no se podía ni apuntar.
    "Máquina",
]

CABECERAS_LABOR_PDF = [
    "Fecha",
    "Labor",
    "Parcela",
    "Sup. (ha)",
    "Cultivo",
    "Lo que se apuntó",
    "Observaciones",
]
ANCHOS_LABOR_CM = (1.5, 2.1, 2.3, 1.2, 1.9, 6.0, 3.6)

# Las parcelas: las tierras del agricultor. Es el bloque 12 del contenido mínimo («Datos de
# superficies») y en el papel es lo primero que mira quien revisa un cuaderno: qué tierras son y
# dónde están.
CABECERAS_PARCELA = [
    "Parcela",
    "Referencia SIGPAC",
    "Municipio",
    "Provincia",
    "Superficie (ha)",
    "Uso",
    "Secano o regadío",
]
ANCHOS_PARCELA_CM = (2.6, 3.4, 3.4, 2.6, 2.0, 2.6, 2.0)

# En el fichero de datos, además, la pendiente y si la parcela está en zona de nitratos: las dos
# importan para cumplir, y en el papel estorban.
CABECERAS_PARCELA_DETALLE = ["Pendiente (%)", "Zona de nitratos"]

# El plan de abono del año: lo que se pensaba echar, para poder compararlo después con lo que de
# verdad se echó.
CABECERAS_PLAN = [
    "Parcela",
    "Cultivo",
    "Sup. (ha)",
    "Producción esperada (kg/ha)",
    "N (kg/ha)",
    "P (kg/ha)",
    "K (kg/ha)",
    "Del suelo y del agua",
    "Notas",
]
ANCHOS_PLAN_CM = (2.3, 2.4, 1.3, 2.1, 1.3, 1.3, 1.3, 2.1, 4.5)

# En el fichero de datos, además, el reparto previsto: qué abono, cuánto y en qué momento. En el
# papel va debajo de la tabla, en renglones, porque no cabe en una columna.
CABECERAS_PLAN_DETALLE = ["Reparto previsto"]

# Las naves y los almacenes (bloque de «edificaciones» del contenido mínimo) y las máquinas de echar
# producto (bloque de «maquinaria»). Con estos dos, el cuaderno impreso lleva los trece bloques: sin
# ellos el papel no decía en qué local se había tratado ni con qué máquina se había echado.
CABECERAS_INSTALACION = [
    "Qué es",
    "Tipo",
    "Referencia catastral",
    "Municipio",
    "Para qué se usa",
    "Superficie (m²)",
]
ANCHOS_INSTALACION_CM = (3.2, 2.2, 3.0, 3.0, 4.6, 2.6)

CABECERAS_MAQUINA = ["Máquina", "Tipo", "Nº ROMA", "Nº de serie", "ITEAf", "Próxima ITEAf"]
ANCHOS_MAQUINA_CM = (3.6, 3.0, 3.0, 3.0, 3.0, 3.0)


# --------------------------------------------------------------------------
# Consultas base
# --------------------------------------------------------------------------


def _campana(db, explotacion, campana_id: int | None) -> models.Campana:
    if campana_id is not None:
        campana = db.get(models.Campana, campana_id)
        if campana is None or campana.explotacion_id != explotacion.id:
            raise HTTPException(status_code=404, detail="Ese año no está en tu cuaderno.")
        return campana
    campana = db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion.id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )
    if campana is None:
        raise HTTPException(status_code=404, detail="Todavía no hay ningún año creado.")
    return campana


def _tratamientos(db, explotacion, campana_id: int) -> list[models.TratamientoFitosanitario]:
    return list(
        db.scalars(
            select(models.TratamientoFitosanitario)
            .where(
                models.TratamientoFitosanitario.explotacion_id == explotacion.id,
                models.TratamientoFitosanitario.campana_id == campana_id,
                models.TratamientoFitosanitario.anulado.is_(False),
            )
            .order_by(models.TratamientoFitosanitario.fecha)
        )
    )


def _fertilizaciones(db, explotacion, campana_id: int) -> list[models.RegistroFertilizacion]:
    return list(
        db.scalars(
            select(models.RegistroFertilizacion)
            .where(
                models.RegistroFertilizacion.explotacion_id == explotacion.id,
                models.RegistroFertilizacion.campana_id == campana_id,
                models.RegistroFertilizacion.anulado.is_(False),
            )
            .order_by(models.RegistroFertilizacion.fecha)
        )
    )


def _labores(db, explotacion, campana_id: int) -> list[models.Labor]:
    return list(
        db.scalars(
            select(models.Labor)
            .where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.campana_id == campana_id,
                models.Labor.anulado.is_(False),
            )
            .order_by(models.Labor.fecha)
        )
    )


def _parcelas(db, explotacion) -> list[models.Parcela]:
    return list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.alias)
        )
    )


def _planes(db, explotacion, campana_id: int) -> list[models.PlanAbonado]:
    return list(
        db.scalars(
            select(models.PlanAbonado)
            .where(
                models.PlanAbonado.explotacion_id == explotacion.id,
                models.PlanAbonado.campana_id == campana_id,
            )
            .order_by(models.PlanAbonado.id)
        )
    )


def _instalaciones(db, explotacion) -> list[models.Instalacion]:
    return list(
        db.scalars(
            select(models.Instalacion)
            .where(models.Instalacion.explotacion_id == explotacion.id)
            .order_by(models.Instalacion.alias)
        )
    )


def _maquinas(db, explotacion) -> list[models.EquipoAplicacion]:
    return list(
        db.scalars(
            select(models.EquipoAplicacion)
            .where(models.EquipoAplicacion.explotacion_id == explotacion.id)
            .order_by(models.EquipoAplicacion.nombre)
        )
    )


def _si_no(valor: bool | None) -> str:
    """Sí, no, o vacío. Vacío es «no lo sé», y **no** se escribe «no»: son cosas distintas."""
    if valor is None:
        return ""
    return textos.ACCIONES["si"] if valor else textos.ACCIONES["no"]


def _numero_o_vacio(valor: float | None, decimales: int = 2) -> str:
    """Un número, o vacío si no se apuntó. **Nunca un cero de relleno**: el cero es un dato."""
    if valor is None:
        return ""
    return legal.formatea_numero(valor, decimales)


def _texto_del_reparto_previsto(db, explotacion, plan) -> str:
    """El reparto previsto del plan en una línea: «qué abono, cuánto y en qué momento».

    Un abono del plan puede venir con su nombre escrito o solo con su ficha; si solo hay ficha
    se busca el nombre, pero **únicamente entre los abonos de esta explotación**: el papel de
    una finca no puede sacar el nombre de un abono de otra.
    """
    trozos: list[str] = []
    for abono in plan.detalle or []:
        if not isinstance(abono, dict):
            continue
        nombre = (abono.get("nombre") or "").strip()
        if not nombre and abono.get("fertilizante_id"):
            ficha = db.get(models.Fertilizante, abono["fertilizante_id"])
            if ficha is not None and ficha.explotacion_id == explotacion.id:
                nombre = (ficha.nombre or "").strip()
        kilos = _numero_o_vacio(abono.get("kg_ha"), 2)
        momento = (abono.get("momento") or "").strip()
        if not (nombre or kilos or momento):
            continue
        trozo = nombre
        if kilos:
            trozo = (f"{trozo} {kilos} kg/ha").strip()
        if momento:
            trozo = f"{trozo} ({momento})".strip()
        trozos.append(trozo)
    return " · ".join(trozos)


def _fila_de_la_instalacion(instalacion) -> list[str]:
    """Una nave o un almacén, con las columnas de `CABECERAS_INSTALACION`."""
    return [
        instalacion.alias or "",
        catalogos.ETIQUETA_INSTALACION.get(instalacion.tipo or "", instalacion.tipo or ""),
        instalacion.referencia_catastral or "",
        instalacion.municipio or "",
        instalacion.uso or "",
        _numero_o_vacio(instalacion.superficie_m2, 2),
    ]


def _fila_de_la_maquina(maquina) -> list[str]:
    """Una máquina de echar producto, con las columnas de `CABECERAS_MAQUINA`.

    Las dos fechas ITEAf van las dos: la de la última inspección y la de la siguiente. Un equipo
    con la ITEAf caducada no puede aplicarse, y en el papel eso se ve de un vistazo.
    """
    return [
        maquina.nombre or "",
        maquina.tipo or "",
        maquina.numero_roma or "",
        maquina.numero_serie or "",
        legal.formatea_fecha(maquina.fecha_iteaf) if maquina.fecha_iteaf else "",
        legal.formatea_fecha(maquina.fecha_proxima_iteaf) if maquina.fecha_proxima_iteaf else "",
    ]


def _fila_de_la_parcela(parcela) -> list[str]:
    """Una parcela, con las columnas de `CABECERAS_PARCELA`. El papel y el fichero usan esto.

    El uso va traducido por el catálogo oficial del SIGPAC; si el código no está en el
    fichero se escribe el código tal cual, y nunca una traducción nuestra.
    """
    return [
        parcela.alias or "",
        parcela.ref_sigpac or "",
        parcela.municipio or "",
        parcela.provincia or "",
        _numero_o_vacio(parcela.superficie_ha, 4),
        sigpac.etiqueta_uso(parcela.uso_sigpac),
        catalogos.ETIQUETA_SISTEMA.get(parcela.sistema or "", ""),
    ]


def _fila_del_plan(db, plan) -> list[str]:
    """Una línea del plan de abono, con las columnas de `CABECERAS_PLAN`."""
    return [
        _nombre_parcela(db, plan.parcela_id),
        plan.cultivo or "",
        _numero_o_vacio(plan.superficie_ha, 4),
        _numero_o_vacio(plan.produccion_esperada_kg_ha, 2),
        _numero_o_vacio(plan.necesidad_n, 2),
        _numero_o_vacio(plan.necesidad_p, 2),
        _numero_o_vacio(plan.necesidad_k, 2),
        _numero_o_vacio(plan.aportes_suelo_agua, 2),
        plan.notas or "",
    ]


def _valores_del_detalle_de_la_labor(db, labor) -> list[str]:
    """Lo propio de esa labor, en el mismo orden que `CABECERAS_LABOR_DETALLE`.

    Lleva la base de datos porque la máquina se guarda por su identificador y en el papel tiene que
    salir su nombre: un número no le dice nada a quien revisa el cuaderno.
    """
    return [
        _numero_o_vacio(labor.volumen_agua),
        labor.unidad_agua or "",
        catalogos.ETIQUETA_ORIGEN_AGUA.get(labor.origen_agua or "", ""),
        catalogos.ETIQUETA_SISTEMA_RIEGO.get(labor.sistema_riego or "", ""),
        labor.numero_contador or "",
        _numero_o_vacio(labor.cantidad_semilla_kg),
        _numero_o_vacio(labor.dosis_siembra_kg_ha),
        labor.lote_semilla or "",
        _si_no(labor.material_tratado),
        labor.tratamiento_semilla or "",
        legal.formatea_fecha(labor.fecha_tratamiento_semilla)
        if labor.fecha_tratamiento_semilla
        else "",
        catalogos.ETIQUETA_EFICACIA.get(labor.eficacia_tratamiento_semilla or "", ""),
        _si_no(labor.material_adquirido),
        legal.formatea_fecha(labor.fecha_adquisicion) if labor.fecha_adquisicion else "",
        _si_no(labor.siembra_directa),
        labor.marco_plantacion or "",
        _numero_o_vacio(labor.densidad_plantacion),
        _si_no(labor.animales_terceros),
        _si_no(labor.animales_propios),
        _nombre_equipo(db, labor.equipo_id),
    ]


def _lo_que_se_apunto(db, labor) -> str:
    """Lo propio de esa labor, en una línea, para el papel.

    En el fichero de datos cada cosa va en su columna; en el papel hay que poder leerlo de un
    vistazo, así que se juntan las etiquetas con sus valores y **solo se nombra lo que se apuntó**:
    lo que está vacío no se enseña, porque un hueco no es un dato. Se usan las mismas etiquetas que
    las columnas del fichero, para que no haya dos nombres para lo mismo.
    """
    partes = [
        f"{etiqueta}: {valor}"
        for etiqueta, valor in zip(
            CABECERAS_LABOR_DETALLE, _valores_del_detalle_de_la_labor(db, labor)
        )
        if valor
    ]
    return " · ".join(partes)


def _nota_de_la_labor(labor) -> str:
    """La nota suelta de la labor, si la tiene. Se guarda como `{"nota": "..."}`."""
    detalles = labor.detalles
    if isinstance(detalles, dict):
        return str(detalles.get("nota") or "")
    return ""


def _ventas(db, explotacion, campana_id: int) -> list[models.VentaDeCosecha]:
    return list(
        db.scalars(
            select(models.VentaDeCosecha)
            .where(
                models.VentaDeCosecha.explotacion_id == explotacion.id,
                models.VentaDeCosecha.campana_id == campana_id,
                models.VentaDeCosecha.anulado.is_(False),
            )
            .order_by(models.VentaDeCosecha.fecha)
        )
    )


def _donde_salio(db, venta: models.VentaDeCosecha) -> str:
    """De dónde salió lo que se vendió, para el informe."""
    if venta.parcela_id is not None:
        return _nombre_parcela(db, venta.parcela_id)
    if venta.grupo_id is not None:
        grupo = db.get(models.GrupoParcelas, venta.grupo_id)
        return grupo.nombre if grupo else textos.VENTA["varias_parcelas"]
    return textos.VENTA["sin_donde"]


def _texto_cantidad(venta: models.VentaDeCosecha) -> str:
    corto = (catalogos.unidad_de_venta(venta.unidad) or {}).get("corto", venta.unidad)
    return f"{legal.formatea_numero(venta.cantidad, 2)} {corto}".strip()


def _medidas_aplicadas(db, explotacion) -> list[models.MedidaPreventivaDeclarada]:
    """Las medidas preventivas que la finca dice aplicar.

    Van en el cuaderno porque es un bloque «a nivel de Explotación» del contenido mínimo
    del CUE: no dependen de la campaña, así que no se filtran por año.
    """
    return [
        fila
        for fila in servicios.medidas_declaradas(db, explotacion_id=explotacion.id)
        if fila.aplicada
    ]


def _analiticas(db, explotacion, campana_id: int) -> list[models.Analitica]:
    return list(
        db.scalars(
            select(models.Analitica)
            .where(
                models.Analitica.explotacion_id == explotacion.id,
                models.Analitica.campana_id == campana_id,
                models.Analitica.anulado.is_(False),
            )
            .order_by(models.Analitica.fecha_toma_muestra)
        )
    )


def _sitio_de_la_muestra(db, analitica: models.Analitica) -> str:
    """De dónde salió la muestra, para el informe."""
    if analitica.parcela_id is not None:
        return _nombre_parcela(db, analitica.parcela_id)
    if analitica.instalacion_id is not None:
        instalacion = db.get(models.Instalacion, analitica.instalacion_id)
        return instalacion.alias if instalacion else textos.ANALITICA["parcela_vacia"]
    return analitica.lote or textos.ANALITICA["parcela_vacia"]


def _numeros_del_boletin(db, analitica: models.Analitica) -> str:
    """Los números de un análisis en una sola línea: «Fósforo: 18 ppm · pH: 7,4».

    El separador es un punto medio y no una coma porque los números llevan coma decimal:
    con comas, «Fósforo: 18, pH: 7,4» se lee como si el pH fuera parte del fósforo.
    """
    partes = []
    for parametro in analitica.parametros or []:
        if not isinstance(parametro, dict):
            continue
        conocido = catalogos.parametro_de(analitica.tipo, parametro.get("clave"))
        nombre = conocido.etiqueta if conocido else str(parametro.get("clave"))
        valor = legal.formatea_medida(parametro.get("valor"), parametro.get("unidad") or "")
        partes.append(f"{nombre}: {valor}")
    if analitica.sustancia_detectada:
        partes.append(f"{textos.ROTULOS['analisis']}: {analitica.sustancia_detectada}")
    return " · ".join(partes)


def _nombre_parcela(db, parcela_id: int | None) -> str:
    if parcela_id is None:
        return "varias parcelas"
    parcela = db.get(models.Parcela, parcela_id)
    return parcela.alias if parcela else "parcela borrada"


def _nombre_aplicador(db, aplicador_id: int | None) -> str:
    if aplicador_id is None:
        return ""
    aplicador = db.get(models.Aplicador, aplicador_id)
    return aplicador.nombre if aplicador else ""


def _la_dosis_con_su_unidad(tratamiento, decimales: int) -> str:
    """La dosis con su unidad, o **vacío si no se sabe**.

    **Un cero aquí no es un hueco: es una afirmación** (02/10/2026, defecto A9 de la auditoría de valores
    por defecto, `docs/T02_VALORES_POR_DEFECTO.md`). `tratamientos.dosis` admite «no se sabe» desde que se
    arreglaron los valores por defecto, pero estas dos salidas —**el CSV y el PDF, que es el documento que
    el agricultor firma**— seguían escribiendo `0`, así que un tratamiento del que no se apuntó la dosis
    salía como si se hubiera echado cero producto.

    Y con la unidad pegada habría sido peor: un hueco se leería «` kg/ha`», que parece una unidad sin
    número. Por eso, cuando no se sabe, **se deja en blanco**, que es como esta misma fila escribe ya el
    plazo de seguridad.
    """
    if tratamiento.dosis is None:
        return ""
    return f"{legal.formatea_numero(tratamiento.dosis, decimales)} {tratamiento.unidad_dosis or ''}".strip()


def _la_cantidad_o_vacio(valor, decimales: int) -> str:
    """La cantidad con sus decimales, o **vacío si no se sabe**. Mismo motivo que la dosis.

    Se usa para la cantidad total aplicada, que también admite «no se sabe» y que en el CSV y en el PDF
    salía como un cero.
    """
    if valor is None:
        return ""
    return legal.formatea_numero(valor, decimales)


def _nombre_equipo(db, equipo_id: int | None) -> str:
    if equipo_id is None:
        return ""
    equipo = db.get(models.EquipoAplicacion, equipo_id)
    return equipo.nombre if equipo else ""


# --------------------------------------------------------------------------
# Resumen y "lo que falta"
# --------------------------------------------------------------------------


@router.get("/cuaderno/resumen")
def resumen(explotacion: ExplotacionActual, db: Db, campana_id: int | None = None) -> dict:
    campana = _campana(db, explotacion, campana_id)
    tratamientos = _tratamientos(db, explotacion, campana.id)
    abonos = _fertilizaciones(db, explotacion, campana.id)
    labores = _labores(db, explotacion, campana.id)

    superficie_parcelas = sum(
        p.superficie_ha
        for p in db.scalars(
            select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
        )
        if p.superficie_ha is not None
    )
    hectareas_tratadas = sum(t.superficie_tratada_ha for t in tratamientos)
    hectareas_abonadas = sum(a.superficie_ha for a in abonos)
    # Un apunte del que no consta la composición **no suma cero**: se queda fuera y se dice cuántos
    # son, porque un total que parece completo y no lo es acaba en una decisión (A6 de
    # `docs/T02_VALORES_POR_DEFECTO.md`).
    con_composicion = [a for a in abonos if a.uf_n_total is not None]
    nitrogeno_total = sum(a.uf_n_total for a in con_composicion)
    sin_composicion = len(abonos) - len(con_composicion)

    return {
        "campana": {"id": campana.id, "anio": campana.anio, "cerrada": campana.cerrada},
        "parcelas": len(
            list(
                db.scalars(
                    select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
                )
            )
        ),
        # Las hectáreas de las tierras que sí las tienen, y cuántas no las traen. **Antes las que
        # faltaban sumaban cero en silencio** (A7): una finca con una tierra sin superficie enseñaba
        # un total que parecía completo. Aquí se cuenta el hueco para que la pantalla pueda decirlo.
        "superficie_total_ha": round(superficie_parcelas, 2),
        "tierras_sin_superficie": sum(
            1
            for p in db.scalars(
                select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
            )
            if p.superficie_ha is None
        ),
        "apuntes_de_producto": len(tratamientos),
        "hectareas_con_producto": round(hectareas_tratadas, 2),
        "apuntes_de_abono": len(abonos),
        # Cuántos trabajos se han apuntado (sembrar, regar, coger…). Se cuenta aquí para que la
        # pantalla de inicio pueda decir la verdad: decía «todavía no has apuntado nada» mirando
        # solo lo que recordaba el móvil, y quien había apuntado un abono en el ordenador de casa
        # leía que su cuaderno estaba vacío. Con los tres números, «no has apuntado nada» es un
        # hecho comprobado y no una suposición.
        "apuntes_de_trabajo": len(labores),
        "hectareas_abonadas": round(hectareas_abonadas, 2),
        "nitrogeno_total_kg": round(nitrogeno_total, 2),
        # Cuántos abonos del año se han quedado fuera de ese total por no constar su composición.
        "abonos_sin_composicion": sin_composicion,
    }


@router.get("/cuaderno/falta")
def lo_que_falta(explotacion: ExplotacionActual, db: Db, campana_id: int | None = None) -> dict:
    """Qué está a medias, dicho con nombre y apellido.

    Es la respuesta a "¿tengo el cuaderno en condiciones?". Sin esto, el agricultor
    no sabe si le falta algo hasta que llega una inspección.
    """
    campana = _campana(db, explotacion, campana_id)
    pendientes: list[dict] = []

    # Parcelas sin cultivo declarado este año.
    con_cultivo = {
        c.parcela_id
        for c in db.scalars(
            select(models.ParcelaCultivo).where(
                models.ParcelaCultivo.explotacion_id == explotacion.id,
                models.ParcelaCultivo.campana_id == campana.id,
            )
        )
    }
    tierras = list(
        db.scalars(select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id))
    )
    for parcela in tierras:
        if parcela.id not in con_cultivo:
            pendientes.append(
                {
                    "tipo": "parcela_sin_cultivo",
                    "parcela_id": parcela.id,
                    "mensaje": textos.mensaje("A3_parcela_sin_cultivo", parcela=parcela.alias),
                }
            )

    tratamientos = _tratamientos(db, explotacion, campana.id)
    sin_justificar = [t for t in tratamientos if not (t.justificacion or "").strip()]
    if sin_justificar:
        pendientes.append(
            {
                "tipo": "tratamiento_sin_justificacion",
                "cuantos": len(sin_justificar),
                "mensaje": textos.mensaje_con_cuenta("A6", len(sin_justificar)),
            }
        )
    sin_dosis = [t for t in tratamientos if t.dosis is None]
    if sin_dosis:
        pendientes.append(
            {
                "tipo": "tratamiento_sin_dosis",
                "cuantos": len(sin_dosis),
                "mensaje": textos.mensaje_con_cuenta("A7", len(sin_dosis)),
            }
        )

    # Quién aplicó y con qué máquina son dos datos obligatorios del cuaderno. No se
    # bloquea el apunte por no tenerlos (el agricultor puede no acordarse en el
    # momento), pero tienen que salir aquí: si no, se llega a la inspección con el
    # cuaderno a medias y sin saberlo.
    sin_quien = [t for t in tratamientos if t.aplicador_id is None or t.equipo_id is None]
    if sin_quien:
        pendientes.append(
            {
                "tipo": "tratamiento_sin_aplicador_o_equipo",
                "cuantos": len(sin_quien),
                "mensaje": textos.mensaje_con_cuenta("A9", len(sin_quien)),
            }
        )

    # **«No te falta nada» exige haber mirado algo** (01/10/2026, T02). Con el año sin empezar —ninguna
    # tierra dada de alta o ninguna con datos— las comprobaciones de arriba **no tienen nada que mirar**, así
    # que `pendientes` sale vacío y la respuesta decía «esta_completo: true» con el mensaje «No te falta nada
    # por apuntar». El silencio se leía como un visto bueno: un cuaderno vacío no está al día, está **sin
    # empezar**, y esa es una diferencia que importa delante de una inspección. Se dice con su propio texto.
    hay_algo_que_mirar = bool(tierras) or bool(tratamientos)
    if not hay_algo_que_mirar:
        return {
            "campana": campana.anio,
            # `None` y no `False`: no es que falte algo, es que **no se sabe** si falta (no hay nada todavía).
            "esta_completo": None,
            "pendientes": [],
            "mensaje": textos.mensaje("A8_sin_nada_que_revisar"),
        }

    return {
        "campana": campana.anio,
        "esta_completo": not pendientes,
        "pendientes": pendientes,
        "mensaje": textos.mensaje("A8_todo_en_orden") if not pendientes else None,
    }


# --------------------------------------------------------------------------
# Exportación
# --------------------------------------------------------------------------


@router.get("/cuaderno/export.csv")
def exportar_csv(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> Response:
    campana = _campana(db, explotacion, campana_id)
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\n")

    escritor.writerow([f"Cuaderno de campo - {explotacion.nombre} - {campana.anio}"])
    escritor.writerow([])

    # Las tierras y el plan van antes que lo que se hizo: un cuaderno empieza por decir de qué
    # parcelas habla y qué se pensaba hacer. Es el bloque 12 del contenido mínimo («Datos de
    # superficies») y el plan de abono del año.
    escritor.writerow([textos.PARCELAS["informe_titulo"].upper()])
    escritor.writerow(CABECERAS_PARCELA + CABECERAS_PARCELA_DETALLE)
    parcelas = _parcelas(db, explotacion)
    if not parcelas:
        escritor.writerow([textos.PARCELAS["informe_sin_nada"]])
    for parcela in parcelas:
        escritor.writerow(
            _fila_de_la_parcela(parcela)
            + [
                _numero_o_vacio(parcela.pendiente_pct, 2),
                _si_no(parcela.zona_vulnerable_nitratos),
            ]
        )

    escritor.writerow([])
    escritor.writerow([textos.INSTALACIONES["informe_titulo"].upper()])
    escritor.writerow(CABECERAS_INSTALACION)
    instalaciones = _instalaciones(db, explotacion)
    if not instalaciones:
        escritor.writerow([textos.INSTALACIONES["informe_sin_nada"]])
    for instalacion in instalaciones:
        escritor.writerow(_fila_de_la_instalacion(instalacion))

    escritor.writerow([])
    escritor.writerow([textos.MAQUINARIA["informe_titulo"].upper()])
    escritor.writerow(CABECERAS_MAQUINA)
    maquinas = _maquinas(db, explotacion)
    if not maquinas:
        escritor.writerow([textos.MAQUINARIA["informe_sin_nada"]])
    for maquina in maquinas:
        escritor.writerow(_fila_de_la_maquina(maquina))

    escritor.writerow([])
    escritor.writerow([textos.PLAN["titulo"].upper()])
    escritor.writerow(CABECERAS_PLAN + CABECERAS_PLAN_DETALLE)
    planes = _planes(db, explotacion, campana.id)
    if not planes:
        # El plan es una previsión, así que no tenerlo no es un error: se dice y ya está.
        escritor.writerow([textos.PLAN["sin_planes"]])
    for plan in planes:
        escritor.writerow(
            _fila_del_plan(db, plan) + [_texto_del_reparto_previsto(db, explotacion, plan)]
        )

    escritor.writerow([])
    escritor.writerow(["PRODUCTOS APLICADOS"])
    escritor.writerow(CABECERAS_TRATAMIENTO)
    for t in _tratamientos(db, explotacion, campana.id):
        escritor.writerow(
            [
                legal.formatea_fecha(t.fecha),
                _nombre_parcela(db, t.parcela_id),
                t.cultivo or "",
                legal.formatea_numero(t.superficie_tratada_ha, 4),
                t.producto_nombre or "",
                t.numero_registro or "",
                _la_dosis_con_su_unidad(t, 4),
                _la_cantidad_o_vacio(t.cantidad_total, 4),
                t.plazo_seguridad_dias if t.plazo_seguridad_dias is not None else "",
                legal.formatea_fecha(t.fecha_fin_plazo_seguridad),
                _nombre_aplicador(db, t.aplicador_id),
                _nombre_equipo(db, t.equipo_id),
            ]
        )

    escritor.writerow([])
    escritor.writerow(["ABONOS"])
    escritor.writerow(CABECERAS_ABONO)
    for a in _fertilizaciones(db, explotacion, campana.id):
        escritor.writerow(
            [
                legal.formatea_fecha(a.fecha),
                _nombre_parcela(db, a.parcela_id),
                legal.formatea_numero(a.superficie_ha, 4),
                a.fertilizante_nombre or "",
                legal.formatea_numero(a.kg_ha_producto, 2),
                legal.formatea_numero(a.cantidad_total_kg, 2),
                # Lo que aporta: en blanco cuando no consta la composición, **nunca un cero**. Un
                # cero aquí se lee como «este abono no aportó nada», y lo que pasa es que nadie ha
                # declarado lo que lleva (A6 de `docs/T02_VALORES_POR_DEFECTO.md`).
                _numero_o_vacio(a.uf_n_ha, 2),
                _numero_o_vacio(a.uf_p_ha, 2),
                _numero_o_vacio(a.uf_k_ha, 2),
            ]
        )

    escritor.writerow([])
    escritor.writerow([textos.LABORES["informe_titulo"].upper()])
    escritor.writerow(CABECERAS_LABOR + CABECERAS_LABOR_DETALLE + ["Nota", "Observaciones"])
    labores = _labores(db, explotacion, campana.id)
    if not labores:
        escritor.writerow([textos.LABORES["informe_sin_nada"]])
    for labor in labores:
        escritor.writerow(
            [
                legal.formatea_fecha(labor.fecha),
                catalogos.ETIQUETA_LABOR.get(labor.tipo, labor.tipo),
                _nombre_parcela(db, labor.parcela_id),
                _numero_o_vacio(labor.superficie_ha, 4),
                labor.cultivo or "",
            ]
            + _valores_del_detalle_de_la_labor(db, labor)
            + [_nota_de_la_labor(labor), labor.observaciones or ""]
        )

    escritor.writerow([])
    escritor.writerow([textos.VENTA["informe_titulo"].upper()])
    escritor.writerow(CABECERAS_VENTA)
    ventas = _ventas(db, explotacion, campana.id)
    if not ventas:
        # Una sección vacía se dice, en vez de dejar solo la cabecera: quien abre el CSV
        # tiene que poder distinguir «no hay nada» de «la exportación se ha roto».
        escritor.writerow([textos.VENTA["informe_sin_nada"]])
    for venta in ventas:
        escritor.writerow(
            [
                legal.formatea_fecha(venta.fecha),
                catalogos.ETIQUETA_VENTA_CORTA.get(venta.tipo, venta.tipo),
                venta.producto,
                venta.variedad or "",
                _texto_cantidad(venta),
                _el_dinero_de_una_venta(venta.importe),
                _el_dinero_de_una_venta(venta.precio_unitario),
                venta.lote or "",
                venta.comprador or "",
                venta.numero_albaran or "",
                _donde_salio(db, venta),
            ]
        )

    escritor.writerow([])
    escritor.writerow([textos.MEDIDAS["informe_titulo"].upper()])
    escritor.writerow([textos.MEDIDAS["de_la_finca"]])
    medidas = _medidas_aplicadas(db, explotacion)
    if medidas:
        for fila in medidas:
            escritor.writerow(
                [catalogos.etiqueta_medida(fila.medida), fila.observaciones or ""]
            )
    else:
        escritor.writerow([textos.MEDIDAS["informe_sin_nada"]])

    escritor.writerow([])
    escritor.writerow([textos.ANALITICA["informe_titulo"].upper()])
    escritor.writerow(CABECERAS_ANALISIS)
    analiticas = _analiticas(db, explotacion, campana.id)
    if not analiticas:
        escritor.writerow([textos.ANALITICA["informe_sin_nada"]])
    for analitica in analiticas:
        escritor.writerow(
            [
                legal.formatea_fecha(analitica.fecha_toma_muestra),
                legal.formatea_fecha(analitica.fecha_resultado),
                catalogos.etiqueta_analitica(analitica.tipo),
                _sitio_de_la_muestra(db, analitica),
                analitica.laboratorio or "",
                analitica.numero_informe or "",
                _numeros_del_boletin(db, analitica),
            ]
        )

    # El BOM es deliberado: sin él, Excel abre el fichero y destroza las tildes, y
    # el agricultor cree que el programa está mal.
    contenido = "\ufeff" + salida.getvalue()
    nombre = f"cuaderno_{campana.anio}.csv"
    return Response(
        content=contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )

# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------


def _tabla(datos: list[list[str]], anchos_cm: tuple[float, ...] | None = None) -> Table:
    tabla = Table(datos, colWidths=[a * cm for a in anchos_cm] if anchos_cm else None, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f5d3a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ]
        )
    )
    return tabla


@router.get("/cuaderno/pdf")
def exportar_pdf(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> StreamingResponse:
    campana = _campana(db, explotacion, campana_id)
    tratamientos = _tratamientos(db, explotacion, campana.id)
    abonos = _fertilizaciones(db, explotacion, campana.id)
    pendientes = lo_que_falta(explotacion, db, campana.id)["pendientes"]

    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Cuaderno de campo {campana.anio}",
        author=explotacion.nombre,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    estilos = getSampleStyleSheet()
    piezas: list = [
        Paragraph(f"Cuaderno de campo · {explotacion.nombre}", estilos["Title"]),
        Paragraph(f"Año {campana.anio}", estilos["Heading2"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f"Titular: {explotacion.nombre}<br/>"
            f"NIF: {explotacion.nif}<br/>"
            f"Finca en: {explotacion.municipio or '—'} ({explotacion.provincia or '—'})",
            estilos["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    # Las tierras van justo debajo de quién es el titular: un cuaderno empieza por decir de qué
    # parcelas habla. Es el bloque 12 del contenido mínimo («Datos de superficies»).
    parcelas = _parcelas(db, explotacion)
    piezas.extend(
        [
            Paragraph(f"{textos.PARCELAS['informe_titulo']} ({len(parcelas)})", estilos["Heading2"]),
        ]
    )
    if parcelas:
        filas = [CABECERAS_PARCELA]
        for parcela in parcelas:
            filas.append(_fila_de_la_parcela(parcela))
        piezas.append(_tabla(filas, ANCHOS_PARCELA_CM))
    else:
        piezas.append(Paragraph(textos.PARCELAS["informe_sin_nada"], estilos["Normal"]))

    # Las naves y los almacenes, y las máquinas de echar producto: los dos bloques del contenido
    # mínimo que faltaban para que el papel lleve los trece. Van con las tierras porque son la
    # misma cosa: lo que el agricultor tiene.
    instalaciones = _instalaciones(db, explotacion)
    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(
                f"{textos.INSTALACIONES['informe_titulo']} ({len(instalaciones)})",
                estilos["Heading2"],
            ),
        ]
    )
    if instalaciones:
        filas = [CABECERAS_INSTALACION]
        for instalacion in instalaciones:
            filas.append(_fila_de_la_instalacion(instalacion))
        piezas.append(_tabla(filas, ANCHOS_INSTALACION_CM))
    else:
        piezas.append(Paragraph(textos.INSTALACIONES["informe_sin_nada"], estilos["Normal"]))

    maquinas = _maquinas(db, explotacion)
    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(
                f"{textos.MAQUINARIA['informe_titulo']} ({len(maquinas)})", estilos["Heading2"]
            ),
        ]
    )
    if maquinas:
        filas = [CABECERAS_MAQUINA]
        for maquina in maquinas:
            filas.append(_fila_de_la_maquina(maquina))
        piezas.append(_tabla(filas, ANCHOS_MAQUINA_CM))
    else:
        piezas.append(Paragraph(textos.MAQUINARIA["informe_sin_nada"], estilos["Normal"]))

    # El plan de abono del año: lo previsto, para poder compararlo con lo que de verdad se echó.
    # Es una previsión, así que no tenerlo no es un error y se dice sin más.
    planes = _planes(db, explotacion, campana.id)
    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(f"{textos.PLAN['titulo']} ({len(planes)})", estilos["Heading2"]),
        ]
    )
    if planes:
        filas = [CABECERAS_PLAN]
        for plan in planes:
            filas.append(_fila_del_plan(db, plan))
        piezas.append(_tabla(filas, ANCHOS_PLAN_CM))
        # El reparto previsto no cabe en una columna, así que va debajo en renglones. Solo sale
        # el de los planes que lo tengan: no se rellena con nada.
        for plan in planes:
            reparto = _texto_del_reparto_previsto(db, explotacion, plan)
            if reparto:
                piezas.append(
                    Paragraph(f"{_nombre_parcela(db, plan.parcela_id)}: {reparto}", estilos["Normal"])
                )
    else:
        piezas.append(Paragraph(textos.PLAN["sin_planes"], estilos["Normal"]))

    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(f"Productos aplicados ({len(tratamientos)})", estilos["Heading2"]),
        ]
    )

    if tratamientos:
        filas = [CABECERAS_TRATAMIENTO_PDF]
        for t in tratamientos:
            filas.append(
                [
                    legal.formatea_fecha(t.fecha),
                    _nombre_parcela(db, t.parcela_id),
                    t.cultivo or "",
                    legal.formatea_numero(t.superficie_tratada_ha, 2),
                    t.producto_nombre or "",
                    t.numero_registro or "",
                    _la_dosis_con_su_unidad(t, 2),
                    _la_cantidad_o_vacio(t.cantidad_total, 2),
                    str(t.plazo_seguridad_dias if t.plazo_seguridad_dias is not None else ""),
                    legal.formatea_fecha(t.fecha_fin_plazo_seguridad),
                    _nombre_aplicador(db, t.aplicador_id),
                    _nombre_equipo(db, t.equipo_id),
                ]
            )
        piezas.append(_tabla(filas, ANCHOS_TRATAMIENTO_CM))
    else:
        piezas.append(Paragraph("Todavía no hay ningún producto apuntado este año.", estilos["Normal"]))

    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(f"Abonos ({len(abonos)})", estilos["Heading2"]),
        ]
    )
    if abonos:
        filas = [CABECERAS_ABONO_PDF]
        for a in abonos:
            filas.append(
                [
                    legal.formatea_fecha(a.fecha),
                    _nombre_parcela(db, a.parcela_id),
                    legal.formatea_numero(a.superficie_ha, 2),
                    a.fertilizante_nombre or "",
                    legal.formatea_numero(a.kg_ha_producto, 1),
                    legal.formatea_numero(a.cantidad_total_kg, 1),
                    # En blanco cuando no consta la composición, nunca un cero (A6).
                    _numero_o_vacio(a.uf_n_ha, 1),
                    _numero_o_vacio(a.uf_p_ha, 1),
                    _numero_o_vacio(a.uf_k_ha, 1),
                ]
            )
        piezas.append(_tabla(filas, ANCHOS_ABONO_CM))
    else:
        piezas.append(Paragraph("Todavía no hay ningún abono apuntado este año.", estilos["Normal"]))

    # Las labores: lo que se hizo en el campo. Es la sección que faltaba, y una de las que el
    # contenido mínimo del cuaderno pide.
    labores = _labores(db, explotacion, campana.id)
    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(f"{textos.LABORES['informe_titulo']} ({len(labores)})", estilos["Heading2"]),
        ]
    )
    if labores:
        filas = [CABECERAS_LABOR_PDF]
        for labor in labores:
            filas.append(
                [
                    legal.formatea_fecha(labor.fecha),
                    catalogos.ETIQUETA_LABOR.get(labor.tipo, labor.tipo),
                    _nombre_parcela(db, labor.parcela_id),
                    _numero_o_vacio(labor.superficie_ha, 2),
                    labor.cultivo or "",
                    _lo_que_se_apunto(db, labor),
                    labor.observaciones or "",
                ]
            )
        piezas.append(_tabla(filas, ANCHOS_LABOR_CM))
    else:
        piezas.append(Paragraph(textos.LABORES["informe_sin_nada"], estilos["Normal"]))

    # Lo que se ha vendido: es el «Informe Cosechas Comercializadas» de la app oficial, que
    # allí sale por Utilidades > Ver listados.
    ventas = _ventas(db, explotacion, campana.id)
    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(f"{textos.VENTA['informe_titulo']} ({len(ventas)})", estilos["Heading2"]),
        ]
    )
    if ventas:
        filas = [CABECERAS_VENTA_PDF]
        for venta in ventas:
            filas.append(
                [
                    legal.formatea_fecha(venta.fecha),
                    f"{venta.producto}" + (f" ({venta.variedad})" if venta.variedad else ""),
                    _texto_cantidad(venta),
                    _el_dinero_de_una_venta(venta.importe),
                    _el_dinero_de_una_venta(venta.precio_unitario),
                    venta.comprador or "",
                    venta.lote or "",
                    _donde_salio(db, venta),
                ]
            )
        piezas.append(_tabla(filas, ANCHOS_VENTA_CM))
    else:
        piezas.append(Paragraph(textos.VENTA["informe_sin_nada"], estilos["Normal"]))

    # Las medidas preventivas: bloque a nivel de Explotación del contenido mínimo del CUE.
    # No dependen de la campaña, así que van antes de las secciones del año.
    medidas = _medidas_aplicadas(db, explotacion)
    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(textos.MEDIDAS["informe_titulo"], estilos["Heading2"]),
            Paragraph(textos.MEDIDAS["de_la_finca"], estilos["Italic"]),
            Spacer(1, 0.2 * cm),
        ]
    )
    if medidas:
        for fila in medidas:
            etiqueta = catalogos.etiqueta_medida(fila.medida)
            texto_fila = f"• {etiqueta}"
            if fila.observaciones:
                texto_fila += f" — {fila.observaciones}"
            piezas.append(Paragraph(texto_fila, estilos["Normal"]))
    else:
        piezas.append(Paragraph(textos.MEDIDAS["informe_sin_nada"], estilos["Normal"]))

    # El informe de análisis. Es el «Informe Analíticas» de la app oficial, que allí sale
    # por Utilidades > Ver listados.
    analiticas = _analiticas(db, explotacion, campana.id)
    piezas.extend(
        [
            Spacer(1, 0.6 * cm),
            Paragraph(f"{textos.ANALITICA['informe_titulo']} ({len(analiticas)})", estilos["Heading2"]),
        ]
    )
    if analiticas:
        filas = [CABECERAS_ANALISIS_PDF]
        for analitica in analiticas:
            filas.append(
                [
                    legal.formatea_fecha(analitica.fecha_toma_muestra),
                    catalogos.etiqueta_analitica(analitica.tipo),
                    _sitio_de_la_muestra(db, analitica),
                    analitica.laboratorio or "",
                    _numeros_del_boletin(db, analitica),
                ]
            )
        piezas.append(_tabla(filas, ANCHOS_ANALISIS_CM))
    else:
        piezas.append(Paragraph(textos.ANALITICA["informe_sin_nada"], estilos["Normal"]))

    # La hoja de "lo que falta" es lo que permite dar el PDF aunque esté a medias.
    piezas.extend([Spacer(1, 0.8 * cm), Paragraph("Lo que falta por completar", estilos["Heading2"])])
    if pendientes:
        piezas.append(
            Paragraph(
                "Este cuaderno se puede usar, pero conviene terminar estas cosas:",
                estilos["Normal"],
            )
        )
        piezas.append(Spacer(1, 0.2 * cm))
        for pendiente in pendientes:
            piezas.append(Paragraph(f"• {pendiente['mensaje']}", estilos["Normal"]))
    else:
        piezas.append(Paragraph(textos.mensaje("A8_todo_en_orden"), estilos["Normal"]))

    piezas.extend(
        [
            Spacer(1, 0.8 * cm),
            Paragraph(
                f"Documento generado el {legal.formatea_fecha(dt.date.today())}. "
                "Este cuaderno recoge los apuntes hechos por el titular de la finca.",
                estilos["Italic"],
            ),
        ]
    )

    documento.build(piezas)
    buffer.seek(0)
    nombre = f"cuaderno_{campana.anio}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


# --------------------------------------------------------------------------
# Ayuda: los textos, servidos desde el mismo sitio que usa el programa
# --------------------------------------------------------------------------


@router.get("/ayuda")
def ayuda_completa() -> dict:
    return {
        "porques": textos.PORQUE,
        "campos": [
            {"campo": campo, **datos} for campo, datos in sorted(textos.AYUDA.items())
        ],
        "plazos_legales": {
            "cuaderno_en_papel_hasta": legal.formatea_fecha(catalogos.FECHA_FIN_CUADERNO_PAPEL),
            "productos_electronico_desde": legal.formatea_fecha(
                catalogos.FECHA_REGISTRO_ELECTRONICO_FITOSANITARIOS
            ),
            "abonos_obligatorio_desde": legal.formatea_fecha(
                catalogos.FECHA_REGISTRO_OBLIGATORIO_FERTILIZACION
            ),
        },
        "medidas_preventivas": [
            {"codigo": m.codigo, "pregunta": m.pregunta, "etiqueta": m.etiqueta}
            for m in catalogos.MEDIDAS_PREVENTIVAS
        ],
        "medidas": textos.MEDIDAS,
        "justificaciones": list(catalogos.JUSTIFICACIONES),
        # Las reglas del programa de actuación de las zonas de nitratos, con su número y su
        # fuente. Y lo que ese programa pide y no tenemos cargado, dicho en vez de callado.
        "reglas_nitratos": [
            {
                "clave": regla.clave,
                "que": regla.que,
                "valor": regla.valor,
                "unidad": regla.unidad,
                "fuente": regla.fuente,
                "texto_valor": (
                    f"{legal.formatea_numero(regla.valor, 0)} {regla.unidad}".strip()
                    if regla.valor is not None
                    else ""
                ),
                "que_hace_la_app": regla.que_hace_la_app,
            }
            for regla in catalogos.reglas_nitratos()
        ],
        "limites_que_faltan": list(catalogos.limites_que_faltan()),
        "aportes_maximos_n": list(catalogos.nitratos_cyl.aportes_maximos()),
        "periodos_prohibidos_n": list(catalogos.nitratos_cyl.periodos_prohibidos()),
    }


@router.get("/ayuda/{campo}")
def ayuda_de_un_campo(campo: str) -> dict:
    datos = textos.ayuda(campo)
    if datos is None:
        raise HTTPException(status_code=404, detail="De eso no tengo explicación todavía.")
    return {"campo": campo, **datos}
