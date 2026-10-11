"""La API de los extractos de banco y de la conciliación (T20, E11).

## Qué hace esta API, y qué no

Se **sube un fichero** de extracto, se lee, se enseña lo que se ha entendido (y lo que no), y cuando
el agricultor dice que sí se guardan los movimientos. Después, cada movimiento se puede **apuntar**
contra los papeles que tiene en el programa (una factura nuestra, un cobro, una factura de compra),
por partes o juntando varios, y **deshacer** ese apunte sin que el movimiento del banco desaparezca.
Eso es todo.

**No se conecta ningún banco.** No hay ni una llamada a internet en este fichero: lo único que entra
es el fichero que el agricultor ha descargado de su banca y ha subido él. Lo prohíbe el encargo con
esas palabras, y hay una prueba que lee este fichero y lo comprueba (`TestNoHayNingunaConexionBancaria`).
La conexión bancaria es el ticket T24, y no se empieza hasta que haya proveedor y consentimiento.

## Las tres cosas que este fichero NO puede hacer, y por qué

1. **No guarda el fichero del extracto.** Un extracto lleva el número de cuenta completo y los nombres
   de terceros; los movimientos guardados son ya todo lo que hace falta (fecha, concepto, importe,
   referencia y saldo), y el fichero se queda donde estaba. Lo que sí se guarda es **su huella**, para
   poder decir «este mismo fichero ya lo importaste el 3 de octubre». Se dice aquí porque el contrato
   (§2, «Propuestas y confirmación») pide conservar el original: en un extracto de banco el original lo
   tiene el banco, y copiarlo sería guardar un dato personal sin necesidad.
2. **No crea ningún hecho de negocio al conciliar.** Conciliar escribe **una fila de vínculo** y una
   fila de auditoría, y nada más: ni una factura, ni un gasto, ni un cobro, ni un movimiento nuevo. Es
   la regla del ticket («conciliar un pago no crea otro gasto») y hay dos pruebas: una pura y otra que
   **cuenta las filas de la base** antes y después.
3. **No adivina nada.** Lo que no se entiende se rechaza con su motivo y su número de línea, y lo que
   no consta se queda en «no lo sé». La vista previa existe para eso: para que el agricultor vea
   exactamente qué se va a guardar antes de guardarlo.

## Lo que este fichero necesita del coordinador (el reparto del apartado 47.5)

Las cinco tablas (`CuentaBancaria`, `PerfilDeExtracto`, `ImportacionDeExtracto`, `MovimientoDeExtracto`
y `ConciliacionDeMovimiento`), su `include_router` en `main.py` y los textos de `textos.py`. Todo está
escrito, con el bloque literal, en `docs/T20_EXTRACTOS.md`. **Los esquemas de entrada y salida de esta
API viven aquí dentro y no en `schemas.py`**, y es a propósito: `schemas.py` es un fichero compartido
que el ticket no puede tocar, y sin sus esquemas este router no se podría ni ejecutar. Están escritos
para moverse tal cual a `schemas.py` el día que se integren (el bloque está en el informe).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from decimal import Decimal

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select

from .. import adjuntos, dinero, extractos, models, servicios, textos, ventas
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import EntradaBase, SalidaBase, _un_importe_que_cabe

router = APIRouter(prefix="/api/bancos", tags=["los extractos del banco"])

# Lo que se admite como extracto. Un CSV se sirve con tres tipos distintos según quién lo exporte
# (el navegador manda `text/csv`, Excel `application/vnd.ms-excel` y algunos programas
# `application/octet-stream`), así que los tres valen: lo que decide si el fichero sirve no es su
# etiqueta, es lo que se lee dentro.
TIPOS_DE_EXTRACTO = {
    "text/csv": ".csv",
    "text/plain": ".csv",
    "application/csv": ".csv",
    "application/vnd.ms-excel": ".csv",
    "application/octet-stream": ".csv",
}

# El ancho de las columnas de las tablas que este ticket propone. Están aquí **una sola vez** para que
# los esquemas de entrada y el informe no puedan decir cosas distintas de la base.
ANCHO_NOMBRE = 80
ANCHO_REFERENCIA = 120
ANCHO_CLAVE_DE_DUPLICADO = 300
ANCHO_MOTIVO = 300

# Las clases de documento que se pueden pagar o cobrar hoy. Lo que falte (un gasto sin factura, una
# inversión, una nómina) es del T13 y está declarado en `extractos.CLASES_QUE_FALTAN`.
CLASES_DE_HOY = extractos.CLASES_DE_DOCUMENTO


# ==========================================================================
# Los esquemas de esta API
#
# **Propuesta para `schemas.py`**, y se quedan aquí mientras no se integren: sin ellos este router no
# se puede ni ejecutar, y `schemas.py` es un fichero compartido que este ticket no escribe.
# ==========================================================================


class CuentaBancariaEntrada(EntradaBase):
    nombre: str = Field(min_length=1, max_length=ANCHO_NOMBRE)
    banco: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    # Solo los cuatro últimos dígitos: el número de cuenta entero no hace falta para nada y es un dato
    # que no queremos tener guardado (ver `extractos.CuentaDelFichero`).
    ultimos_digitos: str | None = Field(default=None, max_length=4)
    propia: bool = True
    activa: bool = True
    notas: str | None = None
    clave_de_reenvio: str | None = Field(default=None, max_length=ANCHO_REFERENCIA)

    @field_validator("ultimos_digitos", mode="before")
    @classmethod
    def _solo_los_cuatro_ultimos(cls, valor):
        if valor is None:
            return None
        limpio = "".join(c for c in str(valor) if c.isdigit())
        return limpio[-4:] or None


class CuentaBancariaSalida(SalidaBase):
    id: int
    nombre: str
    banco: str | None
    ultimos_digitos: str | None
    propia: bool
    activa: bool
    notas: str | None
    movimientos: int = 0
    sin_conciliar: int = 0


class PerfilDeExtractoEntrada(EntradaBase):
    """Cómo está escrito el fichero de este banco. Los tres campos que pueden cambiarle el sentido a
    un número (`decimal`, `formato_de_fecha` y `sin_signo_quiere_decir`) admiten vacío, y vacío quiere
    decir «no me lo has dicho»: entonces el programa lee lo que puede demostrar el propio fichero y
    **rechaza** lo que no, en vez de elegir."""

    nombre: str = Field(min_length=1, max_length=ANCHO_NOMBRE)
    cuenta_id: int | None = None
    delimitador: str = Field(default=";", max_length=4)
    decimal: str | None = Field(default=None, max_length=1)
    formato_de_fecha: str | None = Field(default=None, max_length=20)
    estilo_del_signo: str = Field(default=extractos.SIGNO_EN_EL_IMPORTE, max_length=30)
    sin_signo_quiere_decir: str | None = Field(default=None, max_length=10)
    dicen_que_entra: str | None = Field(default=None, max_length=200)
    dicen_que_sale: str | None = Field(default=None, max_length=200)
    columna_fecha: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_fecha_valor: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_concepto: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_importe: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_saldo: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_referencia: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_debe: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_haber: str | None = Field(default=None, max_length=ANCHO_NOMBRE)
    columna_signo: str | None = Field(default=None, max_length=ANCHO_NOMBRE)


class PerfilDeExtractoSalida(SalidaBase):
    id: int
    nombre: str
    cuenta_id: int | None
    delimitador: str
    decimal: str | None
    formato_de_fecha: str | None
    estilo_del_signo: str
    sin_signo_quiere_decir: str | None
    columnas: dict[str, str] = Field(default_factory=dict)


class TextoDeUnaFila(BaseModel):
    """Una fila del fichero que se enseña tal cual, con su motivo ya escrito en palabras."""

    numero_de_linea: int
    motivo: str
    que_pasa: str
    texto: str
    lo_que_dice: str | None = None


class AvisoDeLaLectura(BaseModel):
    codigo: str
    que_pasa: str
    lineas: list[int] = Field(default_factory=list)


class MovimientoLeido(BaseModel):
    """Un movimiento antes de guardarlo: lo que se va a apuntar si el agricultor dice que sí."""

    numero_de_linea: int
    fecha: dt.date | None
    concepto: str | None
    # `None` es «no consta», y viaja así hasta la pantalla y hasta el CSV. **Nunca un cero.**
    importe: Decimal | None
    signo: str | None
    saldo: Decimal | None
    referencia: str | None
    clave_de_duplicado: str
    ya_estaba: bool = False
    lo_que_falta: list[str] = Field(default_factory=list)


class TraspasoPropuesto(BaseModel):
    sale_de: str
    entra_en: str
    importe: Decimal
    dias_de_diferencia: int
    cuentas: list[str] = Field(default_factory=list)
    que_pasa: str = ""


class VistaPreviaDelExtracto(BaseModel):
    """Lo que sale de leer el fichero **sin guardar nada**. Es la pantalla de S14: primero leer."""

    cuenta_detectada: str | None = None
    ultimos_digitos: str | None = None
    saldo_final: Decimal | None = None
    columnas: dict[str, str] = Field(default_factory=dict)
    formato_de_fecha: str | None = None
    sin_signo_quiere_decir: str | None = None
    movimientos: list[MovimientoLeido] = Field(default_factory=list)
    ya_estaban: int = 0
    nuevas: int = 0
    rechazadas: list[TextoDeUnaFila] = Field(default_factory=list)
    avisos: list[AvisoDeLaLectura] = Field(default_factory=list)
    traspasos: list[TraspasoPropuesto] = Field(default_factory=list)
    resumen: dict[str, str | int | None] = Field(default_factory=dict)
    el_fichero_ya_estaba: bool = False


class ResultadoDeLaImportacion(BaseModel):
    importacion_id: int
    cuenta_id: int
    creados: int
    repetidos: int
    filas_rechazadas: int
    sin_importe: int
    el_fichero_ya_estaba: bool
    ya_estaba: bool = False
    avisos: list[str] = Field(default_factory=list)
    traspasos: list[TraspasoPropuesto] = Field(default_factory=list)


class MovimientoSalida(SalidaBase):
    id: int
    cuenta_id: int
    cuenta: str | None = None
    fecha: dt.date | None
    concepto: str | None
    referencia: str | None
    importe: Decimal | None
    signo: str | None
    saldo: Decimal | None
    estado: str
    imputado: Decimal
    por_conciliar: Decimal | None
    es_traspaso_propio: bool
    pareja_de_traspaso_id: int | None
    lo_que_falta: list[str] = Field(default_factory=list)
    se_puede_conciliar: bool
    por_que_no: str | None = None
    corregido: bool = False


class ListaDeMovimientos(BaseModel):
    items: list[MovimientoSalida] = Field(default_factory=list)
    total: int = 0
    total_del_contexto: int = 0
    agregados: dict[str, str | int] = Field(default_factory=dict)


class DocumentoPendiente(BaseModel):
    clase: str
    documento_id: int
    etiqueta: str
    contraparte: str | None = None
    referencia: str | None = None
    fecha: dt.date | None = None
    vencimiento: dt.date | None = None
    importe: Decimal | None = None
    pendiente: Decimal | None = None
    que_es: str = ""


class ImputacionEntrada(EntradaBase):
    clase: str = Field(min_length=1, max_length=30)
    documento_id: int
    importe: Decimal | None = None

    @field_validator("importe", mode="before")
    @classmethod
    def _el_importe_es_exacto(cls, valor):
        return _un_importe_que_cabe(valor)


class ConciliacionEntrada(EntradaBase):
    """A qué papeles se apunta este movimiento. Vacío es «míralo tú y reparte lo que quepa»."""

    imputaciones: list[ImputacionEntrada] = Field(default_factory=list)


class ConciliacionHecha(BaseModel):
    documento: str
    clase: str
    documento_id: int
    importe: Decimal


class ResultadoDeLaConciliacion(BaseModel):
    movimiento: MovimientoSalida
    conciliaciones: list[ConciliacionHecha] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)


class CorreccionDeUnMovimiento(EntradaBase):
    """Corregir un movimiento a mano. Lo que no se manda no se toca, y mandar `null` es «déjalo en no
    lo sé»: son dos cosas distintas y por eso se usa `exclude_unset` al aplicarlo."""

    fecha: dt.date | None = None
    concepto: str | None = None
    referencia: str | None = Field(default=None, max_length=ANCHO_REFERENCIA)
    importe: Decimal | None = None
    signo: str | None = None
    motivo: str | None = Field(default=None, max_length=ANCHO_MOTIVO)

    @field_validator("importe", mode="before")
    @classmethod
    def _el_importe_es_exacto(cls, valor):
        return _un_importe_que_cabe(valor)


class TraspasoEntrada(EntradaBase):
    """La otra pata del traspaso. Vacío es «quitar el vínculo»."""

    otro_movimiento_id: int | None = None


# ==========================================================================
# Los textos que necesita esta API
#
# Se piden por clave (`textos.mensaje`) y **no se escriben aquí**: la frase que lee el agricultor vive
# en `textos.py`. Las claves y sus frases están en `docs/T20_EXTRACTOS.md`, y hay una prueba
# (`test_los_textos_que_pide_el_router_estan_en_textos_py`) que las lee de este fichero y avisa de las
# que falten.
# ==========================================================================

TEXTO_DE_CADA_MOTIVO_DE_RECHAZO = {
    extractos.SIN_FECHA: "T20_sin_fecha",
    extractos.FECHA_AMBIGUA: "T20_fecha_dudosa",
    extractos.FECHA_ILEGIBLE: "T20_fecha_ilegible",
    extractos.SIN_SIGNO: "T20_sin_signo",
    extractos.DEBE_Y_HABER: "T20_debe_y_haber",
    extractos.SIGNO_DESCONOCIDO: "T20_signo_desconocido",
    extractos.IMPORTE_CERO: "T20_importe_cero",
    extractos.IMPORTE_ILEGIBLE: "T20_importe_ilegible",
    extractos.COLUMNAS_DE_MAS: "T20_columnas_de_mas",
    extractos.SIN_CABECERAS: "T20_sin_cabeceras",
}

TEXTO_DE_CADA_AVISO = {
    extractos.AVISO_SIN_CABECERAS: "T20_sin_cabeceras",
    extractos.AVISO_NO_SE_SABE_LA_CUENTA: "T20_no_se_sabe_de_que_cuenta_es",
    extractos.AVISO_IMPORTES_QUE_NO_CONSTAN: "T20_hay_importes_que_no_constan",
    extractos.AVISO_FILAS_RECHAZADAS: "T20_hay_filas_que_no_se_entienden",
    extractos.AVISO_SALDO_NO_CUADRA: "T20_el_saldo_no_cuadra",
    extractos.AVISO_ORDEN_DUDOSO: "T20_el_orden_de_las_filas_es_dudoso",
    extractos.AVISO_FORMATO_DE_FECHA_SIN_DECLARAR: "T20_el_formato_de_la_fecha_no_esta_declarado",
    extractos.AVISO_FORMATO_DE_FECHA_DEDUCIDO: "T20_el_formato_de_la_fecha_se_ha_deducido",
    extractos.AVISO_SIGNO_DEDUCIDO: "T20_el_signo_se_ha_deducido_del_saldo",
    extractos.AVISO_FILAS_SIN_SIGNO: "T20_hay_filas_sin_signo",
}

TEXTO_DE_CADA_PROBLEMA = {
    extractos.PROBLEMA_NO_CONSTA_EL_IMPORTE: "T20_el_movimiento_no_dice_cuanto",
    extractos.PROBLEMA_IMPORTE_NO_VALE: "T20_esa_cantidad_no_vale",
    extractos.PROBLEMA_DOCUMENTO_SIN_PENDIENTE: "T20_no_se_sabe_cuanto_le_falta",
    extractos.PROBLEMA_MAS_QUE_EL_PENDIENTE: "T20_mas_de_lo_que_le_falta",
    extractos.PROBLEMA_MAS_QUE_EL_MOVIMIENTO: "T20_mas_de_lo_que_dice_el_movimiento",
    extractos.PROBLEMA_DOCUMENTO_REPETIDO: "T20_el_mismo_papel_dos_veces",
    extractos.PROBLEMA_CLASE_EQUIVOCADA: "T20_ese_papel_no_va_por_ese_lado",
    extractos.PROBLEMA_DE_OTRA_FINCA: "T20_eso_no_esta_en_tu_cuaderno",
}

NOMBRE_DE_CADA_COLUMNA = {
    "fecha": "columna_fecha",
    "fecha_valor": "columna_fecha_valor",
    "concepto": "columna_concepto",
    "importe": "columna_importe",
    "saldo": "columna_saldo",
    "referencia": "columna_referencia",
    "debe": "columna_debe",
    "haber": "columna_haber",
    "signo": "columna_signo",
}


def _el_texto_de_una_fila_rechazada(motivo: str) -> str:
    """La frase que lee el agricultor para una fila que no se ha entendido.

    Se escriben una por una y **no en un diccionario de frases** por una razón de este programa: las
    frases viven en `textos.py`, y un diccionario `{motivo: "frase"}` aquí dentro sería un texto del
    agricultor escondido en un router, que es justo lo que el test de la jerga no puede vigilar.
    """
    if motivo == extractos.SIN_FECHA:
        return textos.mensaje("T20_sin_fecha")
    if motivo == extractos.FECHA_AMBIGUA:
        return textos.mensaje("T20_fecha_dudosa")
    if motivo == extractos.FECHA_ILEGIBLE:
        return textos.mensaje("T20_fecha_ilegible")
    if motivo == extractos.SIN_SIGNO:
        return textos.mensaje("T20_sin_signo")
    if motivo == extractos.DEBE_Y_HABER:
        return textos.mensaje("T20_debe_y_haber")
    if motivo == extractos.SIGNO_DESCONOCIDO:
        return textos.mensaje("T20_signo_desconocido")
    if motivo == extractos.IMPORTE_CERO:
        return textos.mensaje("T20_importe_cero")
    if motivo == extractos.IMPORTE_ILEGIBLE:
        return textos.mensaje("T20_importe_ilegible")
    if motivo == extractos.COLUMNAS_DE_MAS:
        return textos.mensaje("T20_columnas_de_mas")
    if motivo == extractos.SIN_CABECERAS:
        return textos.mensaje("T20_sin_cabeceras")
    # Un motivo nuevo sin su frase no puede salir en blanco: se dice que no se sabe qué pasó, que es
    # la verdad y es mejor que un hueco.
    return textos.mensaje("T20_esa_linea_no_se_ha_entendido")


def _el_texto_de_un_aviso(aviso: extractos.Aviso) -> str:
    """La frase de un aviso de la lectura, con sus números dentro."""
    codigo = aviso.codigo
    lineas = ", ".join(str(n) for n in aviso.lineas[:8])
    if codigo == extractos.AVISO_SIN_CABECERAS:
        return textos.mensaje("T20_sin_cabeceras")
    if codigo == extractos.AVISO_NO_SE_SABE_LA_CUENTA:
        return textos.mensaje("T20_no_se_sabe_de_que_cuenta_es")
    if codigo == extractos.AVISO_IMPORTES_QUE_NO_CONSTAN:
        return textos.mensaje("T20_hay_importes_que_no_constan", lineas=lineas)
    if codigo == extractos.AVISO_FILAS_RECHAZADAS:
        return textos.mensaje("T20_hay_filas_que_no_se_entienden", lineas=lineas)
    if codigo == extractos.AVISO_SALDO_NO_CUADRA:
        return textos.mensaje("T20_el_saldo_no_cuadra", lineas=lineas)
    if codigo == extractos.AVISO_ORDEN_DUDOSO:
        return textos.mensaje("T20_el_orden_de_las_filas_es_dudoso")
    if codigo == extractos.AVISO_FORMATO_DE_FECHA_SIN_DECLARAR:
        return textos.mensaje("T20_el_formato_de_la_fecha_no_esta_declarado", lineas=lineas)
    if codigo == extractos.AVISO_FORMATO_DE_FECHA_DEDUCIDO:
        return textos.mensaje(
            "T20_el_formato_de_la_fecha_se_ha_deducido", formato=aviso.datos.get("formato", ""), lineas=lineas
        )
    if codigo == extractos.AVISO_SIGNO_DEDUCIDO:
        return textos.mensaje("T20_el_signo_se_ha_deducido_del_saldo", lineas=lineas)
    if codigo == extractos.AVISO_FILAS_SIN_SIGNO:
        return textos.mensaje("T20_hay_filas_sin_signo", lineas=lineas)
    return textos.mensaje("T20_esa_linea_no_se_ha_entendido")


def _que_pasa_con_este_problema(problema: str) -> str:
    """La frase de un problema al conciliar, para que la pantalla diga qué arreglar."""
    if problema == extractos.PROBLEMA_NO_CONSTA_EL_IMPORTE:
        return textos.mensaje("T20_el_movimiento_no_dice_cuanto")
    if problema == extractos.PROBLEMA_IMPORTE_NO_VALE:
        return textos.mensaje("T20_esa_cantidad_no_vale")
    if problema == extractos.PROBLEMA_DOCUMENTO_SIN_PENDIENTE:
        return textos.mensaje("T20_no_se_sabe_cuanto_le_falta")
    if problema == extractos.PROBLEMA_MAS_QUE_EL_PENDIENTE:
        return textos.mensaje("T20_mas_de_lo_que_le_falta")
    if problema == extractos.PROBLEMA_MAS_QUE_EL_MOVIMIENTO:
        return textos.mensaje("T20_mas_de_lo_que_dice_el_movimiento")
    if problema == extractos.PROBLEMA_DOCUMENTO_REPETIDO:
        return textos.mensaje("T20_el_mismo_papel_dos_veces")
    if problema == extractos.PROBLEMA_CLASE_EQUIVOCADA:
        return textos.mensaje("T20_ese_papel_no_va_por_ese_lado")
    return textos.mensaje("T20_no_se_ha_podido_apuntar_eso")


# ==========================================================================
# Traducir de la base de datos a la lógica pura, y al revés
# ==========================================================================


def _la_cuenta(db, explotacion, cuenta_id: int):
    return obtener_de_la_explotacion(db, models.CuentaBancaria, cuenta_id, explotacion.id)


def _el_perfil(db, explotacion, perfil_id: int):
    return obtener_de_la_explotacion(db, models.PerfilDeExtracto, perfil_id, explotacion.id)


def _como_perfil_de_formato(fila) -> extractos.PerfilDeFormato:
    """La fila guardada, como perfil que entiende la lógica pura."""
    columnas = {
        columna: getattr(fila, nombre_del_campo)
        for columna, nombre_del_campo in NOMBRE_DE_CADA_COLUMNA.items()
        if getattr(fila, nombre_del_campo, None)
    }
    return extractos.PerfilDeFormato(
        nombre=fila.nombre,
        delimitador=fila.delimitador or ";",
        decimal=fila.decimal,
        formato_de_fecha=fila.formato_de_fecha,
        estilo_del_signo=fila.estilo_del_signo or extractos.SIGNO_EN_EL_IMPORTE,
        sin_signo_quiere_decir=fila.sin_signo_quiere_decir,
        dicen_que_entra=tuple(p for p in (fila.dicen_que_entra or "").split("|") if p)
        or extractos.DICEN_QUE_ENTRA_POR_DEFECTO,
        dicen_que_sale=tuple(p for p in (fila.dicen_que_sale or "").split("|") if p)
        or extractos.DICEN_QUE_SALE_POR_DEFECTO,
        columnas=columnas or dict(extractos.COLUMNAS_DE_UN_EXTRACTO),
    )


def _como_perfil_guardado(datos: PerfilDeExtractoEntrada, explotacion_id: int):
    """Y al revés: los campos del esquema, en la fila que se guarda."""
    fila = models.PerfilDeExtracto(
        explotacion_id=explotacion_id,
        nombre=datos.nombre,
        cuenta_id=datos.cuenta_id,
        delimitador=datos.delimitador,
        decimal=datos.decimal,
        formato_de_fecha=datos.formato_de_fecha,
        estilo_del_signo=datos.estilo_del_signo,
        sin_signo_quiere_decir=datos.sin_signo_quiere_decir,
        dicen_que_entra=datos.dicen_que_entra,
        dicen_que_sale=datos.dicen_que_sale,
    )
    for columna, nombre_del_campo in NOMBRE_DE_CADA_COLUMNA.items():
        setattr(fila, nombre_del_campo, getattr(datos, nombre_del_campo, None))
    return fila


def _lo_que_le_falta_al_movimiento(fila) -> list[str]:
    """Qué no consta en un movimiento guardado. Se calcula, no se guarda: es lo mismo que se lee."""
    falta: list[str] = []
    if fila.importe is None:
        falta.append(extractos.IMPORTE_NO_CONSTA)
    if fila.saldo is None:
        falta.append(extractos.SALDO_NO_CONSTA)
    if not fila.referencia:
        falta.append(extractos.REFERENCIA_NO_CONSTA)
    if not fila.concepto:
        falta.append(extractos.CONCEPTO_NO_CONSTA)
    return falta


def _como_fila_de_extracto(fila, nombre_de_la_cuenta: str | None) -> extractos.FilaDeExtracto:
    """Un movimiento guardado, como el objeto puro: para poder proponer conciliaciones y traspasos."""
    signo = fila.signo or None
    importe = dinero.a_decimal(fila.importe) if fila.importe is not None else None
    return extractos.FilaDeExtracto(
        numero_de_linea=0,
        fecha=fila.fecha,
        fecha_valor=fila.fecha_valor,
        concepto=fila.concepto,
        importe=importe,
        signo=signo if signo in extractos.SIGNOS else None,
        saldo=dinero.a_decimal(fila.saldo) if fila.saldo is not None else None,
        referencia=fila.referencia,
        cuenta=nombre_de_la_cuenta,
        clave_de_duplicado=fila.clave_de_duplicado,
        es_traspaso_propio=fila.pareja_de_traspaso_id is not None,
        explotacion_id=fila.explotacion_id,
    )


def _lo_que_esta_imputado(db, explotacion, movimiento_id: int) -> tuple[dict[str, Decimal], Decimal]:
    """Lo que ya se ha apuntado de este movimiento contra cada papel, y el total.

    Se cuenta **solo lo vivo**: una conciliación deshecha sigue en la tabla (con su fecha, su autor y su
    motivo, que es el rastro que pide el ticket) pero no suma.
    """
    filas = db.scalars(
        select(models.ConciliacionDeMovimiento).where(
            models.ConciliacionDeMovimiento.explotacion_id == explotacion.id,
            models.ConciliacionDeMovimiento.movimiento_id == movimiento_id,
            models.ConciliacionDeMovimiento.anulada.is_(False),
        )
    ).all()
    por_documento: dict[str, Decimal] = {}
    total = dinero.CERO
    for fila in filas:
        importe = dinero.a_decimal(fila.importe) or dinero.CERO
        clave = f"{fila.clase}:{fila.documento_id}"
        por_documento[clave] = dinero.suma(por_documento.get(clave, dinero.CERO), importe)
        total = dinero.suma(total, importe)
    return (por_documento, dinero.redondea(total) or dinero.CERO)


def _el_nombre_de_la_cuenta(db, explotacion, cuenta_id: int | None) -> str | None:
    """Cómo se llama la cuenta, para poder decir en qué cuenta está el movimiento."""
    if cuenta_id is None:
        return None
    cuenta = db.scalar(
        select(models.CuentaBancaria).where(
            models.CuentaBancaria.explotacion_id == explotacion.id,
            models.CuentaBancaria.id == cuenta_id,
        )
    )
    return cuenta.nombre if cuenta is not None else None


def _como_se_ve_un_movimiento(db, explotacion, fila, nombre_de_la_cuenta: str | None = None) -> MovimientoSalida:
    """Un movimiento con lo que hace falta para poder decidir qué hacer con él."""
    importe = dinero.a_decimal(fila.importe) if fila.importe is not None else None
    _por_documento, imputado = _lo_que_esta_imputado(db, explotacion, fila.id)
    puro = _como_fila_de_extracto(fila, nombre_de_la_cuenta)
    return MovimientoSalida(
        id=fila.id,
        cuenta_id=fila.cuenta_id,
        cuenta=nombre_de_la_cuenta,
        fecha=fila.fecha,
        concepto=fila.concepto,
        referencia=fila.referencia,
        importe=importe,
        signo=puro.signo,
        saldo=dinero.a_decimal(fila.saldo) if fila.saldo is not None else None,
        estado=extractos.estado_de_conciliacion(importe, imputado),
        imputado=imputado,
        por_conciliar=extractos.lo_que_falta_por_conciliar(importe, imputado),
        es_traspaso_propio=fila.pareja_de_traspaso_id is not None,
        pareja_de_traspaso_id=fila.pareja_de_traspaso_id,
        lo_que_falta=_lo_que_le_falta_al_movimiento(fila),
        se_puede_conciliar=puro.se_puede_conciliar,
        por_que_no=extractos.por_que_no_se_puede_conciliar(puro),
        corregido=bool(fila.corregido),
    )


def _los_pendientes(db, explotacion) -> list[extractos.DocumentoPorConciliar]:
    """Los papeles a los que se les puede apuntar dinero hoy, con lo que les falta.

    ## De dónde sale «lo que le falta» a cada uno, y por qué no se cuenta dos veces

    · **Factura nuestra**: su importe menos **los cobros vivos que tiene imputados** y menos las
      conciliaciones vivas que apuntan directamente a ella. El cobro ya resta por su cuenta
      (`importe_imputado`), y el movimiento del banco que se apunta a un cobro **no** vuelve a restar:
      son dos vistas del mismo dinero, y restar las dos sería contar dos veces el mismo pago.
    · **Cobro sin factura**: es dinero que entró y todavía no se sabe de qué factura es (el contrato lo
      llama «pagos sin factura quedan por conciliar»). Su pendiente es su importe: lo que falta es
      decir a qué va.
    · **Factura de compra**: su total menos lo que tenga apuntado. **Hoy no hay ninguna tabla de pagos
      a proveedores** —es del T13—, así que lo apuntado sale solo de esta conciliación, y se dice.

    Y van **de la más antigua a la más nueva**, que es lo que hace que el reparto automático de un
    ingreso (`extractos.reparte_lo_que_queda`) pague primero lo que lleva más tiempo esperando. Es la
    misma regla que el reparto de un cobro entre las entregas de una factura
    (`ventas.reparto_de_lo_cobrado`): por orden y sin repartos a ojo.
    """
    pendientes: list[extractos.DocumentoPorConciliar] = []

    conciliado_por_documento: dict[str, Decimal] = {}
    for fila in db.scalars(
        select(models.ConciliacionDeMovimiento).where(
            models.ConciliacionDeMovimiento.explotacion_id == explotacion.id,
            models.ConciliacionDeMovimiento.anulada.is_(False),
        )
    ).all():
        clave = f"{fila.clase}:{fila.documento_id}"
        conciliado_por_documento[clave] = dinero.suma(
            conciliado_por_documento.get(clave, dinero.CERO), dinero.a_decimal(fila.importe)
        )

    for factura in db.scalars(
        select(models.FacturaEmitida).where(
            models.FacturaEmitida.explotacion_id == explotacion.id,
            models.FacturaEmitida.anulada.is_(False),
        )
    ).all():
        total = dinero.a_decimal(factura.importe_total) if factura.importe_total is not None else None
        if total is None:
            # Una factura sin importe no se puede cobrar a medias: no se sabe cuánto le falta.
            pendiente = None
        else:
            # **Lo cobrado sale de la regla única** (`servicios.lo_cobrado_de_una_factura`, 11/10/2026): antes
            # se sumaba aquí la columna del cobro, que va vacía cuando un ingreso salda varias deudas, así
            # que esta factura aparecía **pendiente** en la conciliación del banco aunque ya estuviera
            # cobrada, y el agricultor volvía a conciliar un dinero que ya estaba donde tenía que estar.
            cobrado = servicios.lo_cobrado_de_una_factura(
                db, explotacion_id=explotacion.id, factura_id=factura.id
            )
            pendiente = ventas.pendiente_de(
                total,
                dinero.suma(cobrado, conciliado_por_documento.get(f"{extractos.FACTURA_EMITIDA}:{factura.id}", dinero.CERO)),
            )
        pendientes.append(
            extractos.DocumentoPorConciliar(
                clase=extractos.FACTURA_EMITIDA,
                documento_id=factura.id,
                contraparte=factura.cliente,
                referencia=factura.numero,
                fecha=factura.fecha,
                vencimiento=factura.vencimiento,
                importe=total,
                pendiente=pendiente,
                explotacion_id=explotacion.id,
            )
        )

    # **Y el dinero que de verdad está sin asignar** (CRM-01, 11/10/2026): lo que separa los dos casos es
    # **tener o no tener aplicaciones**, no la columna de la factura —un cobro repartido entre varias deudas
    # la tiene vacía a propósito, así que con la columna este bucle ofrecía para conciliar un ingreso que ya
    # estaba conciliado a mano, y encima con su importe entero—.
    for cobro in db.scalars(
        select(models.Cobro)
        .where(
            models.Cobro.explotacion_id == explotacion.id,
            models.Cobro.anulado.is_(False),
            ~models.Cobro.id.in_(
                select(models.AplicacionDeUnCobro.cobro_id).where(
                    models.AplicacionDeUnCobro.anulado.is_(False)
                )
            ),
        )
    ).all():
        importe = dinero.a_decimal(cobro.importe)
        pendientes.append(
            extractos.DocumentoPorConciliar(
                clase=extractos.COBRO,
                documento_id=cobro.id,
                contraparte=cobro.cliente,
                referencia=cobro.referencia,
                fecha=cobro.fecha,
                importe=importe,
                pendiente=importe,
                explotacion_id=explotacion.id,
            )
        )

    for factura in db.scalars(
        select(models.Factura).where(
            models.Factura.explotacion_id == explotacion.id,
            models.Factura.anulada.is_(False),
        )
    ).all():
        # El total de una factura recibida está guardado como número decimal desde antes de que
        # existiera el módulo del dinero (`Float`), así que se lee con `cantidad_a_decimal`, que no
        # rechaza el número de coma flotante. El día que T13 lo pase a `Dinero`, esto sigue valiendo.
        total = dinero.redondea(dinero.cantidad_a_decimal(factura.total)) if factura.total is not None else None
        apuntado = conciliado_por_documento.get(f"{extractos.FACTURA_DE_COMPRA}:{factura.id}", dinero.CERO)
        pendiente = ventas.pendiente_de(total, apuntado) if total is not None else None
        pendientes.append(
            extractos.DocumentoPorConciliar(
                clase=extractos.FACTURA_DE_COMPRA,
                documento_id=factura.id,
                contraparte=factura.proveedor,
                referencia=factura.numero_factura,
                fecha=factura.fecha,
                importe=total,
                pendiente=pendiente,
                explotacion_id=explotacion.id,
            )
        )
    # Lo más antiguo primero: es lo que espera el agricultor cuando dice «paga lo que se deba», y así
    # el reparto automático no depende del orden en que se dieron de alta los papeles.
    pendientes.sort(key=lambda documento: (documento.fecha or dt.date(1900, 1, 1), documento.documento_id))
    return pendientes


def _traspasos_propuestos(db, explotacion, ademas=()) -> tuple[extractos.Traspaso, ...]:
    """Las parejas que parecen un traspaso entre dos cuentas de la casa, para que el agricultor diga.

    Se mira **lo que ya está guardado** más lo que se acaba de leer, porque las dos patas de un
    traspaso pueden venir en dos ficheros distintos (uno por cuenta): si solo se mirara el fichero que
    se acaba de subir, el lado que llegó ayer no se vería y el traspaso no se propondría nunca.
    """
    nombres = {
        cuenta.id: cuenta.nombre
        for cuenta in db.scalars(
            select(models.CuentaBancaria).where(models.CuentaBancaria.explotacion_id == explotacion.id)
        ).all()
    }
    propias = {
        cuenta.id: bool(cuenta.propia)
        for cuenta in db.scalars(
            select(models.CuentaBancaria).where(models.CuentaBancaria.explotacion_id == explotacion.id)
        ).all()
    }
    guardados = db.scalars(
        select(models.MovimientoDeExtracto).where(
            models.MovimientoDeExtracto.explotacion_id == explotacion.id,
            models.MovimientoDeExtracto.pareja_de_traspaso_id.is_(None),
        )
    ).all()

    filas = [_como_fila_de_extracto(fila, nombres.get(fila.cuenta_id)) for fila in guardados]
    filas.extend(ademas)
    cuentas_por_nombre = {
        nombres.get(cuenta_id): propias.get(cuenta_id, False) for cuenta_id in nombres
    }
    cuentas_por_nombre = {nombre: propia for nombre, propia in cuentas_por_nombre.items() if nombre}
    return extractos.detectar_traspasos(filas, cuentas_propias=cuentas_por_nombre)


def _el_rastro(db, explotacion_id: int, fila, *, accion: str, datos: dict, usuario_id: int | None) -> None:
    """La fila del rastro: quién, cuándo y qué. Una sola forma de escribirla, como en los cobros.

    `accion` tiene que ser un texto fijo y caber en `auditoria.accion` (mide 80). Hay otro guardián en
    el programa (`tests/test_las_etiquetas_del_rastro_caben.py`) que lee todas las etiquetas y avisa.
    """
    db.add(
        models.Auditoria(
            explotacion_id=explotacion_id,
            usuario_id=usuario_id,
            entidad="movimiento_de_extracto",
            entidad_id=fila.id,
            accion=accion,
            datos=datos,
        )
    )


def _los_traspasos_como_salen(traspasos) -> list[TraspasoPropuesto]:
    return [
        TraspasoPropuesto(
            sale_de=traspaso.sale_de,
            entra_en=traspaso.entra_en,
            importe=traspaso.importe,
            dias_de_diferencia=traspaso.dias_de_diferencia,
            cuentas=list(traspaso.cuentas),
            que_pasa=textos.mensaje("T20_parece_un_traspaso_tuyo"),
        )
        for traspaso in traspasos
    ]


# ==========================================================================
# Las cuentas de la casa
# ==========================================================================


@router.get("/cuentas", response_model=list[CuentaBancariaSalida])
def listar_cuentas(explotacion: ExplotacionActual, db: Db) -> list[CuentaBancariaSalida]:
    """Las cuentas que el agricultor ha dado de alta. **No se pide ningún dato de la banca.**"""
    cuentas = db.scalars(
        select(models.CuentaBancaria)
        .where(models.CuentaBancaria.explotacion_id == explotacion.id)
        .order_by(models.CuentaBancaria.nombre)
    ).all()
    salida: list[CuentaBancariaSalida] = []
    for cuenta in cuentas:
        movimientos = (
            db.scalar(
                select(func.count())
                .select_from(models.MovimientoDeExtracto)
                .where(
                    models.MovimientoDeExtracto.explotacion_id == explotacion.id,
                    models.MovimientoDeExtracto.cuenta_id == cuenta.id,
                )
            )
            or 0
        )
        sin_conciliar = 0
        for fila in db.scalars(
            select(models.MovimientoDeExtracto).where(
                models.MovimientoDeExtracto.explotacion_id == explotacion.id,
                models.MovimientoDeExtracto.cuenta_id == cuenta.id,
            )
        ).all():
            _por_documento, imputado = _lo_que_esta_imputado(db, explotacion, fila.id)
            if imputado <= 0:
                sin_conciliar += 1
        salida.append(
            CuentaBancariaSalida(
                id=cuenta.id,
                nombre=cuenta.nombre,
                banco=cuenta.banco,
                ultimos_digitos=cuenta.ultimos_digitos,
                propia=cuenta.propia,
                activa=cuenta.activa,
                notas=cuenta.notas,
                movimientos=movimientos,
                sin_conciliar=sin_conciliar,
            )
        )
    return salida


@router.post("/cuentas", response_model=CuentaBancariaSalida, status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    datos: CuentaBancariaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> CuentaBancariaSalida:
    """Da de alta una cuenta. **No se pide ninguna clave de banca, y no hay dónde ponerla.**"""
    if datos.clave_de_reenvio:
        ya_estaba = db.scalar(
            select(models.CuentaBancaria).where(
                models.CuentaBancaria.explotacion_id == explotacion.id,
                models.CuentaBancaria.clave_de_reenvio == datos.clave_de_reenvio,
            )
        )
        if ya_estaba is not None:
            # Reenviar la misma petición (el móvil sin cobertura) devuelve la cuenta que ya había, no
            # otra: es la misma regla del resto del programa.
            return CuentaBancariaSalida.model_validate(ya_estaba)
    cuenta = models.CuentaBancaria(
        explotacion_id=explotacion.id,
        nombre=datos.nombre,
        banco=datos.banco,
        ultimos_digitos=datos.ultimos_digitos,
        propia=datos.propia,
        activa=datos.activa,
        notas=datos.notas,
        clave_de_reenvio=datos.clave_de_reenvio,
    )
    db.add(cuenta)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="cuenta_bancaria",
            entidad_id=cuenta.id,
            accion="crear_cuenta_bancaria",
            datos={"nombre": cuenta.nombre, "ultimos_digitos": cuenta.ultimos_digitos},
        )
    )
    db.commit()
    db.refresh(cuenta)
    return CuentaBancariaSalida.model_validate(cuenta)


@router.put("/cuentas/{cuenta_id}", response_model=CuentaBancariaSalida)
def corregir_cuenta(
    cuenta_id: int,
    datos: CuentaBancariaEntrada,
    explotacion: ExplotacionActual,
    db: Db,
) -> CuentaBancariaSalida:
    cuenta = _la_cuenta(db, explotacion, cuenta_id)
    cuenta.nombre = datos.nombre
    cuenta.banco = datos.banco
    cuenta.ultimos_digitos = datos.ultimos_digitos
    cuenta.propia = datos.propia
    cuenta.activa = datos.activa
    cuenta.notas = datos.notas
    db.commit()
    db.refresh(cuenta)
    return CuentaBancariaSalida.model_validate(cuenta)


# ==========================================================================
# Los perfiles de formato: cómo escribe este banco
# ==========================================================================


@router.get("/perfiles", response_model=list[PerfilDeExtractoSalida])
def listar_perfiles(explotacion: ExplotacionActual, db: Db) -> list[PerfilDeExtractoSalida]:
    perfiles = db.scalars(
        select(models.PerfilDeExtracto)
        .where(models.PerfilDeExtracto.explotacion_id == explotacion.id)
        .order_by(models.PerfilDeExtracto.nombre)
    ).all()
    return [_como_perfil_como_sale(perfil) for perfil in perfiles]


def _como_perfil_como_sale(perfil) -> PerfilDeExtractoSalida:
    return PerfilDeExtractoSalida(
        id=perfil.id,
        nombre=perfil.nombre,
        cuenta_id=perfil.cuenta_id,
        delimitador=perfil.delimitador,
        decimal=perfil.decimal,
        formato_de_fecha=perfil.formato_de_fecha,
        estilo_del_signo=perfil.estilo_del_signo,
        sin_signo_quiere_decir=perfil.sin_signo_quiere_decir,
        columnas={
            columna: getattr(perfil, nombre_del_campo)
            for columna, nombre_del_campo in NOMBRE_DE_CADA_COLUMNA.items()
            if getattr(perfil, nombre_del_campo, None)
        },
    )


@router.post("/perfiles", response_model=PerfilDeExtractoSalida, status_code=status.HTTP_201_CREATED)
def guardar_perfil(
    datos: PerfilDeExtractoEntrada, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> PerfilDeExtractoSalida:
    """Guarda cómo escribe este banco, para no volver a preguntarlo (S14: «perfiles guardables»).

    Se valida aquí, con la misma puerta que usa el lector (`PerfilDeFormato`), para que un perfil
    guardado no pueda tener un estilo de signo o un formato de fecha que el lector no entienda: un
    perfil inválido guardado es un fallo que solo se vería al importar, delante del agricultor.
    """
    if datos.cuenta_id is not None:
        _la_cuenta(db, explotacion, datos.cuenta_id)
    fila = _como_perfil_guardado(datos, explotacion.id)
    extractos.PerfilDeFormato(
        nombre=fila.nombre,
        delimitador=fila.delimitador or ";",
        decimal=fila.decimal,
        formato_de_fecha=fila.formato_de_fecha,
        estilo_del_signo=fila.estilo_del_signo,
        sin_signo_quiere_decir=fila.sin_signo_quiere_decir,
    )
    db.add(fila)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="perfil_de_extracto",
            entidad_id=fila.id,
            accion="guardar_perfil_de_extracto",
            datos={"nombre": fila.nombre},
        )
    )
    db.commit()
    db.refresh(fila)
    return _como_perfil_como_sale(fila)


@router.put("/perfiles/{perfil_id}", response_model=PerfilDeExtractoSalida)
def corregir_perfil(
    perfil_id: int,
    datos: PerfilDeExtractoEntrada,
    explotacion: ExplotacionActual,
    db: Db,
) -> PerfilDeExtractoSalida:
    fila = _el_perfil(db, explotacion, perfil_id)
    fila.nombre = datos.nombre
    fila.cuenta_id = datos.cuenta_id
    fila.delimitador = datos.delimitador
    fila.decimal = datos.decimal
    fila.formato_de_fecha = datos.formato_de_fecha
    fila.estilo_del_signo = datos.estilo_del_signo
    fila.sin_signo_quiere_decir = datos.sin_signo_quiere_decir
    fila.dicen_que_entra = datos.dicen_que_entra
    fila.dicen_que_sale = datos.dicen_que_sale
    for columna, nombre_del_campo in NOMBRE_DE_CADA_COLUMNA.items():
        setattr(fila, nombre_del_campo, getattr(datos, nombre_del_campo, None))
    db.commit()
    db.refresh(fila)
    return _como_perfil_como_sale(fila)


# ==========================================================================
# Leer el extracto: la vista previa y la importación
# ==========================================================================


def _lee_lo_que_ha_subido(
    *,
    contenido: bytes,
    cuenta_id: int,
    perfil,
    explotacion,
    db,
) -> tuple[extractos.LecturaDelExtracto, str]:
    """Lee el fichero que ha subido el navegador. Devuelve la lectura y la huella."""
    cuenta = _la_cuenta(db, explotacion, cuenta_id)
    lectura = extractos.lee_extracto(
        extractos.lee_el_texto(contenido),
        _como_perfil_de_formato(perfil) if perfil is not None else None,
        cuenta=cuenta.nombre,
        explotacion_id=explotacion.id,
    )
    return (lectura, extractos.huella_del_fichero(contenido))


def _las_claves_guardadas(db, explotacion, cuenta_id: int) -> set[str]:
    """Las claves de duplicado que ya están guardadas en esa cuenta."""
    return {
        clave
        for (clave,) in db.execute(
            select(models.MovimientoDeExtracto.clave_de_duplicado).where(
                models.MovimientoDeExtracto.explotacion_id == explotacion.id,
                models.MovimientoDeExtracto.cuenta_id == cuenta_id,
            )
        ).all()
    }


def _los_avisos_como_salen(lectura: extractos.LecturaDelExtracto) -> list[AvisoDeLaLectura]:
    return [
        AvisoDeLaLectura(
            codigo=aviso.codigo, que_pasa=_el_texto_de_un_aviso(aviso), lineas=list(aviso.lineas)
        )
        for aviso in lectura.avisos
    ]


def _el_resumen_como_sale(lectura: extractos.LecturaDelExtracto) -> dict[str, str | int | None]:
    """Las cuentas de la lectura, con lo que no consta dicho aparte y nunca sumado como cero."""
    resumen = extractos.resumen_de_lo_que_ha_entrado_y_salido(lectura.movimientos)
    return {
        "entradas": dinero.a_texto(resumen.entradas),
        "salidas": dinero.a_texto(resumen.salidas),
        "sin_importe": resumen.sin_importe,
        "lineas_leidas": lectura.lineas_leidas,
        "movimientos": len(lectura.movimientos),
        "rechazadas": len(lectura.rechazadas),
    }


@router.post("/extractos/vista-previa", response_model=VistaPreviaDelExtracto)
async def leer_el_extracto_sin_guardarlo(
    explotacion: ExplotacionActual,
    db: Db,
    fichero: UploadFile = File(...),
    cuenta_id: int = Form(...),
    perfil_id: int | None = Form(default=None),
) -> VistaPreviaDelExtracto:
    """Lee el extracto y **enseña lo que se va a apuntar, sin apuntar nada** (S14: «lectura previa»).

    Es el paso que hace que un extracto se pueda revisar: aquí salen las líneas entendidas, las que no
    se han entendido **con su número y su motivo**, lo que ya estaba de antes, los traspasos propios
    que parecen, y las cuentas de lo que entra y sale. Nada de esto toca la base de datos.
    """
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS_DE_EXTRACTO)
    perfil = _el_perfil(db, explotacion, perfil_id) if perfil_id is not None else None
    lectura, huella = _lee_lo_que_ha_subido(
        contenido=contenido, cuenta_id=cuenta_id, perfil=perfil, explotacion=explotacion, db=db
    )
    guardadas = _las_claves_guardadas(db, explotacion, cuenta_id)
    nuevas, repetidas = extractos.separa_lo_que_ya_estaba(lectura.movimientos, guardadas)

    mismas_huellas = db.scalar(
        select(func.count())
        .select_from(models.ImportacionDeExtracto)
        .where(
            models.ImportacionDeExtracto.explotacion_id == explotacion.id,
            models.ImportacionDeExtracto.huella == huella,
        )
    )
    traspasos = _traspasos_propuestos(db, explotacion, ademas=list(nuevas))
    return VistaPreviaDelExtracto(
        cuenta_detectada=lectura.cuenta.como_se_llama or None,
        ultimos_digitos=lectura.cuenta.ultimos_digitos,
        saldo_final=lectura.saldo_final,
        columnas=dict(lectura.columnas),
        formato_de_fecha=lectura.perfil.formato_de_fecha,
        sin_signo_quiere_decir=lectura.perfil.sin_signo_quiere_decir,
        movimientos=[
            MovimientoLeido(
                numero_de_linea=fila.numero_de_linea,
                fecha=fila.fecha,
                concepto=fila.concepto,
                importe=fila.importe,
                signo=fila.signo,
                saldo=fila.saldo,
                referencia=fila.referencia,
                clave_de_duplicado=fila.clave_de_duplicado,
                ya_estaba=fila.clave_de_duplicado in guardadas,
                lo_que_falta=list(fila.falta),
            )
            for fila in lectura.movimientos
        ],
        ya_estaban=len(repetidas),
        nuevas=len(nuevas),
        rechazadas=[
            TextoDeUnaFila(
                numero_de_linea=rechazada.numero_de_linea,
                motivo=rechazada.motivo,
                que_pasa=_el_texto_de_una_fila_rechazada(rechazada.motivo),
                texto=rechazada.texto,
                lo_que_dice=rechazada.lo_que_dice,
            )
            for rechazada in lectura.rechazadas
        ],
        avisos=_los_avisos_como_salen(lectura),
        traspasos=_los_traspasos_como_salen(traspasos),
        resumen=_el_resumen_como_sale(lectura),
        el_fichero_ya_estaba=bool(mismas_huellas),
    )


@router.post("/extractos/importar", response_model=ResultadoDeLaImportacion)
async def importar_el_extracto(
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    fichero: UploadFile = File(...),
    cuenta_id: int = Form(...),
    perfil_id: int | None = Form(default=None),
    clave_de_reenvio: str | None = Form(default=None),
) -> ResultadoDeLaImportacion:
    """Apunta los movimientos del extracto. **Los que ya estaban no se apuntan otra vez.**"""
    importacion = None
    if clave_de_reenvio:
        importacion = db.scalar(
            select(models.ImportacionDeExtracto).where(
                models.ImportacionDeExtracto.explotacion_id == explotacion.id,
                models.ImportacionDeExtracto.clave_de_reenvio == clave_de_reenvio,
            )
        )
    if importacion is not None:
        # Reenviar la misma petición no vuelve a apuntar nada: devuelve lo que pasó la primera vez.
        return ResultadoDeLaImportacion(
            importacion_id=importacion.id,
            cuenta_id=importacion.cuenta_id,
            creados=importacion.movimientos_creados,
            repetidos=importacion.movimientos_repetidos,
            filas_rechazadas=importacion.filas_rechazadas,
            sin_importe=importacion.movimientos_sin_importe,
            el_fichero_ya_estaba=True,
            ya_estaba=True,
            avisos=[textos.mensaje("T20_esa_importacion_ya_estaba_hecha")],
        )

    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS_DE_EXTRACTO)
    perfil = _el_perfil(db, explotacion, perfil_id) if perfil_id is not None else None
    lectura, huella = _lee_lo_que_ha_subido(
        contenido=contenido, cuenta_id=cuenta_id, perfil=perfil, explotacion=explotacion, db=db
    )
    guardadas = _las_claves_guardadas(db, explotacion, cuenta_id)
    nuevas, repetidas = extractos.separa_lo_que_ya_estaba(lectura.movimientos, guardadas)

    ya_estaba_el_fichero = bool(
        db.scalar(
            select(func.count())
            .select_from(models.ImportacionDeExtracto)
            .where(
                models.ImportacionDeExtracto.explotacion_id == explotacion.id,
                models.ImportacionDeExtracto.huella == huella,
            )
        )
    )

    importacion = models.ImportacionDeExtracto(
        explotacion_id=explotacion.id,
        cuenta_id=cuenta_id,
        perfil_id=perfil.id if perfil is not None else None,
        usuario_id=usuario.id,
        fichero_nombre=(fichero.filename or "")[:200] or None,
        huella=huella,
        lineas_leidas=lectura.lineas_leidas,
        movimientos_creados=len(nuevas),
        movimientos_repetidos=len(repetidas),
        movimientos_sin_importe=sum(1 for fila in nuevas if fila.importe is None),
        filas_rechazadas=len(lectura.rechazadas),
        decimal=lectura.perfil.decimal,
        formato_de_fecha=lectura.perfil.formato_de_fecha,
        sin_signo_quiere_decir=lectura.perfil.sin_signo_quiere_decir,
        clave_de_reenvio=clave_de_reenvio,
    )
    db.add(importacion)
    db.flush()

    for fila in nuevas:
        db.add(
            models.MovimientoDeExtracto(
                explotacion_id=explotacion.id,
                cuenta_id=cuenta_id,
                importacion_id=importacion.id,
                fecha=fila.fecha,
                fecha_valor=fila.fecha_valor,
                concepto=fila.concepto,
                referencia=fila.referencia,
                importe=fila.importe,
                signo=fila.signo,
                saldo=fila.saldo,
                clave_de_duplicado=fila.clave_de_duplicado,
            )
        )
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="importacion_de_extracto",
            entidad_id=importacion.id,
            accion="importar_extracto",
            datos={
                "cuenta": cuenta_id,
                "leidas": lectura.lineas_leidas,
                "creados": len(nuevas),
                "repetidos": len(repetidas),
                "rechazadas": len(lectura.rechazadas),
                "huella": huella,
            },
        )
    )
    db.commit()

    avisos: list[str] = []
    if ya_estaba_el_fichero:
        avisos.append(textos.mensaje("T20_el_mismo_fichero_ya_estaba"))
    if len(repetidas):
        avisos.append(textos.mensaje("T20_los_movimientos_que_ya_estaban", cuantos=len(repetidas)))
    sin_importe = sum(1 for fila in nuevas if fila.importe is None)
    if sin_importe:
        avisos.append(
            textos.mensaje(
                "T20_hay_importes_que_no_constan",
                lineas=", ".join(str(fila.numero_de_linea) for fila in nuevas if fila.importe is None),
            )
        )
    if lectura.rechazadas:
        avisos.append(
            textos.mensaje(
                "T20_hay_filas_que_no_se_entienden",
                lineas=", ".join(str(r.numero_de_linea) for r in lectura.rechazadas[:8]),
            )
        )
    traspasos = _traspasos_propuestos(db, explotacion)
    if traspasos:
        avisos.append(textos.mensaje("T20_parece_un_traspaso_tuyo"))
    return ResultadoDeLaImportacion(
        importacion_id=importacion.id,
        cuenta_id=cuenta_id,
        creados=len(nuevas),
        repetidos=len(repetidas),
        filas_rechazadas=len(lectura.rechazadas),
        sin_importe=sin_importe,
        el_fichero_ya_estaba=ya_estaba_el_fichero,
        ya_estaba=False,
        avisos=avisos,
        traspasos=_los_traspasos_como_salen(traspasos),
    )


# ==========================================================================
# Los movimientos: verlos, corregirlos y sacarlos en un fichero
# ==========================================================================


def _los_movimientos_filtrados(db, explotacion, *, cuenta_id, desde, hasta, texto):
    """La consulta de los movimientos, con los filtros que se piden de verdad.

    **El filtro por estado no está aquí y es a propósito**: «lo que está sin conciliar» no es una
    columna, es la suma de los vínculos vivos, y el dinero está guardado como texto decimal para que
    no pierda céntimos (ver `dinero.ImporteExacto`). Sumarlo en SQL no se puede —ni se debe—, así que
    ese filtro se aplica en memoria, sobre lo que ya está filtrado por cuenta y por fecha.
    """
    consulta = select(models.MovimientoDeExtracto).where(
        models.MovimientoDeExtracto.explotacion_id == explotacion.id
    )
    if cuenta_id is not None:
        consulta = consulta.where(models.MovimientoDeExtracto.cuenta_id == cuenta_id)
    if desde is not None:
        consulta = consulta.where(models.MovimientoDeExtracto.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(models.MovimientoDeExtracto.fecha <= hasta)
    if texto:
        como = f"%{texto}%"
        consulta = consulta.where(
            or_(
                models.MovimientoDeExtracto.concepto.ilike(como),
                models.MovimientoDeExtracto.referencia.ilike(como),
            )
        )
    return consulta


@router.get("/movimientos", response_model=ListaDeMovimientos)
def listar_movimientos(
    explotacion: ExplotacionActual,
    db: Db,
    cuenta_id: int | None = None,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
    texto: str | None = None,
    estado: str | None = None,
    limite: int = 200,
    salto: int = 0,
) -> ListaDeMovimientos:
    """Los movimientos apuntados, con su estado y lo que les falta por cuadrar."""
    consulta = _los_movimientos_filtrados(
        db, explotacion, cuenta_id=cuenta_id, desde=desde, hasta=hasta, texto=texto
    )
    filas = list(
        db.scalars(
            consulta.order_by(
                models.MovimientoDeExtracto.fecha.desc(), models.MovimientoDeExtracto.id.desc()
            )
        ).all()
    )
    nombres = {
        cuenta.id: cuenta.nombre
        for cuenta in db.scalars(
            select(models.CuentaBancaria).where(models.CuentaBancaria.explotacion_id == explotacion.id)
        ).all()
    }
    vistas = [_como_se_ve_un_movimiento(db, explotacion, fila, nombres.get(fila.cuenta_id)) for fila in filas]
    total_del_contexto = len(vistas)
    if estado:
        vistas = [vista for vista in vistas if vista.estado == estado]
    total = len(vistas)
    recortadas = vistas[salto : salto + max(1, limite)]

    entradas = dinero.suma(*(v.importe for v in vistas if v.signo == extractos.ENTRA))
    salidas = dinero.suma(*(v.importe for v in vistas if v.signo == extractos.SALE))
    return ListaDeMovimientos(
        items=recortadas,
        total=total,
        total_del_contexto=total_del_contexto,
        agregados={
            "entradas": dinero.formatea(entradas),
            "salidas": dinero.formatea(salidas),
            "sin_importe": sum(1 for v in vistas if v.importe is None),
            "sin_conciliar": sum(1 for v in vistas if v.estado == extractos.SIN_CONCILIAR),
            "conciliados": sum(1 for v in vistas if v.estado == extractos.CONCILIADO),
            "a_medias": sum(1 for v in vistas if v.estado == extractos.CONCILIADO_EN_PARTE),
            # Lo que no consta se dice **aparte** y no se suma como cero: un total que calla que le
            # faltan datos es un total que miente.
            "importes_que_no_constan": sum(1 for v in vistas if v.importe is None),
        },
    )


@router.get("/movimientos.csv")
def exportar_los_movimientos(
    explotacion: ExplotacionActual,
    db: Db,
    cuenta_id: int | None = None,
    desde: dt.date | None = None,
    hasta: dt.date | None = None,
    texto: str | None = None,
    estado: str | None = None,
) -> Response:
    """El extracto en un fichero, con el estado de cada movimiento y **sin ceros de relleno**.

    Reutiliza la misma consulta y los mismos permisos que la lista (el contrato lo pide así: «la
    exportación reutiliza la misma consulta y permisos»), y lo escribe `extractos.a_csv`, que deja la
    casilla **en blanco** cuando el importe no consta. Un `0,00` ahí sería decir que ese movimiento fue
    de cero euros, que es lo contrario de lo que dice el banco.

    **Y desde el 06/10/2026 acepta los mismos filtros que la lista** (`texto` y `estado`, además de la
    cuenta y las fechas). Antes no los aceptaba, y eso era un problema de los que no hacen ruido: **el
    agricultor filtraba la pantalla, pulsaba «EXPORTAR» y el fichero se llevaba todo**, sin decir nada.
    Lo encontró la comprobación de descargas (aceptación 3 del encargo: «un filtro de 10 tierras entre 64
    no debe exportar silenciosamente las 64»). El estado se filtra **después** de calcular la vista, con
    el mismo camino que la lista, para que las dos digan lo mismo.
    """
    lista = listar_movimientos(
        explotacion=explotacion,
        db=db,
        cuenta_id=cuenta_id,
        desde=desde,
        hasta=hasta,
        texto=texto,
        estado=estado,
        limite=10_000,
    )
    filas = [
        _como_fila_de_extracto(
            db.get(models.MovimientoDeExtracto, vista.id),
            vista.cuenta,
        )
        for vista in lista.items
    ]
    contenido = extractos.a_csv(
        filas, conciliado={fila.clave_de_duplicado: vista.imputado for fila, vista in zip(filas, lista.items)}
    )
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="extracto.csv"'},
    )


@router.put("/movimientos/{movimiento_id}", response_model=MovimientoSalida)
def corregir_un_movimiento(
    movimiento_id: int,
    datos: CorreccionDeUnMovimiento,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> MovimientoSalida:
    """Corrige a mano un movimiento: el importe que no consta, el concepto, el día.

    ## Por qué existe, y por qué solo con la conciliación deshecha

    Existe porque el programa dice «en esta línea no consta el importe» y **tiene que haber un sitio
    donde escribirlo**: decirle a un agricultor que le falta un dato sin darle dónde ponerlo es el
    fallo que este proyecto ya ha cometido cuatro veces.

    Y solo se puede corregir **lo que no está atado**: si el movimiento tiene dinero ya apuntado a un
    papel, cambiarle el importe dejaría una conciliación que dice más de lo que el movimiento dice.
    Entonces se dice qué hay que hacer primero (deshacerla), que es una frase con instrucción y no un
    «no se puede».
    """
    movimiento = obtener_de_la_explotacion(
        db, models.MovimientoDeExtracto, movimiento_id, explotacion.id
    )
    cambios = datos.model_dump(exclude_unset=True)
    cambios.pop("motivo", None)
    if not cambios:
        return _como_se_ve_un_movimiento(db, explotacion, movimiento)

    _por_documento, imputado = _lo_que_esta_imputado(db, explotacion, movimiento.id)
    if imputado > 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_no_se_puede_corregir_conciliado"),
        )

    if "signo" in cambios and cambios["signo"] not in (None, *extractos.SIGNOS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_esa_cantidad_no_vale"),
        )

    importe_final = cambios.get("importe", movimiento.importe)
    signo_final = cambios.get("signo", movimiento.signo)
    if importe_final is not None and not signo_final:
        # Un importe sin decir si entra o sale es un movimiento que no se puede sumar ni cuadrar.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_dinos_si_entra_o_sale"),
        )

    antes = {
        "fecha": str(movimiento.fecha) if movimiento.fecha else None,
        "concepto": movimiento.concepto,
        "referencia": movimiento.referencia,
        "importe": dinero.a_texto(movimiento.importe) if movimiento.importe is not None else None,
        "signo": movimiento.signo,
    }
    for campo, valor in cambios.items():
        setattr(movimiento, campo, valor)
    if movimiento.importe is None:
        # Si se queda sin importe, se queda también sin signo: no hay dinero, no hay sentido.
        movimiento.signo = None
    movimiento.corregido = True
    movimiento.motivo_de_la_correccion = datos.motivo or textos.mensaje("T20_correccion_a_mano")
    _el_rastro(
        db,
        explotacion.id,
        movimiento,
        accion="corregir_movimiento",
        datos={"antes": antes, "motivo": movimiento.motivo_de_la_correccion},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(movimiento)
    return _como_se_ve_un_movimiento(db, explotacion, movimiento)


# ==========================================================================
# La conciliación: proponerla, hacerla y deshacerla
# ==========================================================================


@router.get("/movimientos/{movimiento_id}/propuestas")
def ver_las_propuestas(
    movimiento_id: int,
    explotacion: ExplotacionActual,
    db: Db,
) -> dict:
    """Con qué papeles podría cuadrar este movimiento, y por qué se propone cada uno.

    Es una **propuesta**: no apunta nada. El contrato lo pide así para los duplicados y los traspasos, y
    para una conciliación vale igual: quien decide es el agricultor.

    ## Se propone con **el dinero que le queda**, no con el importe entero

    Un movimiento puede estar apuntado a medias (media factura ahora y la otra mitad el mes que viene) o
    entero. Si a un movimiento de 210 € ya se le han apuntado 210 €, proponerle otra vez 210 € es ofrecer
    **apuntar dos veces el mismo dinero**: el servidor lo rechaza al guardarlo
    (`T20_mas_de_lo_que_dice_el_movimiento`), pero ofrecer un botón que no puede funcionar es engañar a
    quien lo pulsa, y es justo el fallo que se veía: la pantalla enseñaba la propuesta, se pulsaba y salía
    un error. Así que las propuestas se calculan con lo que falta por colocar, y cuando no queda nada se
    dice con su frase (`ya_apuntado`, `texto_ya_apuntado`) en vez de enseñar una lista vacía sin motivo.
    """
    movimiento = obtener_de_la_explotacion(
        db, models.MovimientoDeExtracto, movimiento_id, explotacion.id
    )
    nombres = {
        cuenta.id: cuenta.nombre
        for cuenta in db.scalars(
            select(models.CuentaBancaria).where(models.CuentaBancaria.explotacion_id == explotacion.id)
        ).all()
    }
    puro = _como_fila_de_extracto(movimiento, nombres.get(movimiento.cuenta_id))
    pendientes = _los_pendientes(db, explotacion)
    _por_documento, ya_imputado = _lo_que_esta_imputado(db, explotacion, movimiento.id)
    por_conciliar = extractos.lo_que_falta_por_conciliar(puro.importe, ya_imputado)
    # `replace` con `None` deja el movimiento como estaba, y con un importe que no consta no hay
    # propuestas posibles: `proponer_conciliaciones` devuelve la lista vacía por su cuenta.
    propuestas = extractos.proponer_conciliaciones(replace(puro, importe=por_conciliar), pendientes)
    por_que_no = extractos.por_que_no_se_puede_conciliar(puro)
    ya_apuntado = puro.importe is not None and (por_conciliar or dinero.CERO) <= 0
    return {
        "movimiento": _como_se_ve_un_movimiento(db, explotacion, movimiento, nombres.get(movimiento.cuenta_id)),
        "se_puede_conciliar": puro.se_puede_conciliar,
        "por_que_no": textos.mensaje("T20_el_movimiento_no_dice_cuanto") if por_que_no else None,
        "clave_de_por_que_no": por_que_no,
        "ya_apuntado": ya_apuntado,
        "texto_ya_apuntado": textos.mensaje("T20_este_movimiento_ya_esta_apuntado") if ya_apuntado else None,
        "por_conciliar": por_conciliar,
        "propuestas": [
            {
                "tipo": propuesta.tipo,
                "total": propuesta.total,
                "sobrante": propuesta.sobrante,
                "puntuacion": propuesta.puntuacion,
                "porque": [_por_que_se_propone(motivo) for motivo in propuesta.porque],
                "imputaciones": [
                    {
                        "clase": linea.documento.clase,
                        "documento_id": linea.documento.documento_id,
                        "importe": linea.importe,
                    }
                    for linea in propuesta.lineas
                ],
            }
            for propuesta in propuestas
        ],
        "pendientes": [_un_pendiente_como_sale(documento) for documento in pendientes if documento.se_puede_conciliar],
    }


def _por_que_se_propone(motivo: str) -> str:
    """El porqué de una propuesta, en palabras: sin esto, la pantalla enseña un número sin motivo."""
    if motivo == extractos.PORQUE_LA_REFERENCIA_ESTA_EN_EL_CONCEPTO:
        return textos.mensaje("T20_porque_la_referencia_esta_en_el_concepto")
    if motivo == extractos.PORQUE_EL_NOMBRE_ESTA_EN_EL_CONCEPTO:
        return textos.mensaje("T20_porque_el_nombre_esta_en_el_concepto")
    if motivo == extractos.PORQUE_EL_IMPORTE_CUADRA:
        return textos.mensaje("T20_porque_el_importe_cuadra")
    if motivo == extractos.PORQUE_LA_SUMA_CUADRA:
        return textos.mensaje("T20_porque_la_suma_cuadra")
    if motivo == extractos.PORQUE_LA_FECHA_ESTA_CERCA:
        return textos.mensaje("T20_porque_la_fecha_esta_cerca")
    if motivo == extractos.PORQUE_LA_FECHA_ESTA_LEJOS:
        return textos.mensaje("T20_porque_la_fecha_esta_lejos")
    return textos.mensaje("T20_porque_no_se_sabe")


def _un_pendiente_como_sale(documento: extractos.DocumentoPorConciliar) -> DocumentoPendiente:
    que_es = textos.mensaje("T20_que_es_una_factura_nuestra")
    if documento.clase == extractos.COBRO:
        que_es = textos.mensaje("T20_que_es_un_cobro_sin_factura")
    if documento.clase == extractos.FACTURA_DE_COMPRA:
        que_es = textos.mensaje("T20_que_es_una_factura_de_compra")
    return DocumentoPendiente(
        clase=documento.clase,
        documento_id=documento.documento_id,
        etiqueta=documento.etiqueta,
        contraparte=documento.contraparte,
        referencia=documento.referencia,
        fecha=documento.fecha,
        vencimiento=documento.vencimiento,
        importe=documento.importe,
        pendiente=documento.pendiente,
        que_es=que_es,
    )


@router.get("/pendientes", response_model=list[DocumentoPendiente])
def ver_lo_que_queda_por_cuadrar(explotacion: ExplotacionActual, db: Db) -> list[DocumentoPendiente]:
    """Los papeles a los que todavía se les puede apuntar dinero.

    Es la mitad de «consultar pendientes» del recorrido: lo que se debe, lo que nos deben y el dinero
    que entró sin saber de qué factura es. Un papel cuyo pendiente **no consta** no entra en la lista:
    no se sabe cuánto le falta, y ponerlo con cero sería decir que está pagado.
    """
    return [
        _un_pendiente_como_sale(documento)
        for documento in _los_pendientes(db, explotacion)
        if documento.se_puede_conciliar
    ]


@router.post("/movimientos/{movimiento_id}/conciliar", response_model=ResultadoDeLaConciliacion)
def conciliar_un_movimiento(
    movimiento_id: int,
    datos: ConciliacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> ResultadoDeLaConciliacion:
    """Apunta este movimiento contra uno o varios papeles, por partes o agrupado.

    ## Lo que hace y lo que no hace

    **Escribe vínculos, y nada más.** No crea una factura, ni un gasto, ni un cobro, ni un movimiento:
    las filas que se guardan apuntan a documentos que ya existían, y si no existieran no se podría
    apuntar a ellos. Y como el vínculo es una fila con su importe, se puede apuntar un movimiento a
    tres facturas (agrupado), o media factura a un movimiento (parcial), y deshacerlo después sin que
    el movimiento del banco se toque.

    Si no se dice cuánto va a cada papel, se reparte **por orden** hasta agotar el dinero
    (`extractos.reparte_lo_que_queda`), que es la cuenta de siempre y no un reparto a ojo.
    """
    movimiento = obtener_de_la_explotacion(
        db, models.MovimientoDeExtracto, movimiento_id, explotacion.id
    )
    nombres = {
        cuenta.id: cuenta.nombre
        for cuenta in db.scalars(
            select(models.CuentaBancaria).where(models.CuentaBancaria.explotacion_id == explotacion.id)
        ).all()
    }
    puro = _como_fila_de_extracto(movimiento, nombres.get(movimiento.cuenta_id))
    if not puro.se_puede_conciliar:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_el_movimiento_no_dice_cuanto"),
        )

    pendientes = {documento.etiqueta: documento for documento in _los_pendientes(db, explotacion)}
    _por_documento, ya_imputado = _lo_que_esta_imputado(db, explotacion, movimiento.id)
    por_conciliar = extractos.lo_que_falta_por_conciliar(puro.importe, ya_imputado) or dinero.CERO

    if datos.imputaciones:
        elegidas: list[tuple[extractos.DocumentoPorConciliar, Decimal | None]] = []
        for imputacion in datos.imputaciones:
            documento = pendientes.get(f"{imputacion.clase}:{imputacion.documento_id}")
            if documento is None:
                # No se dice si existe en otra finca: es la misma regla de siempre (404, no 403).
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=textos.mensaje("T20_eso_no_esta_en_tu_cuaderno"),
                )
            elegidas.append((documento, imputacion.importe))
        revision = extractos.revisa_una_conciliacion(
            movimiento=replace(puro, importe=por_conciliar), imputaciones=elegidas
        )
    else:
        # Reparto automático: se llena por orden lo que quepa, y el resto se queda sin apuntar.
        candidatos = [
            documento
            for documento in pendientes.values()
            if documento.se_puede_conciliar
            and documento.es_de_dinero_que_entra == (puro.signo == extractos.ENTRA)
        ]
        lineas = extractos.reparte_lo_que_queda(importe=por_conciliar, pendientes=candidatos)
        total = dinero.suma(*(linea.importe for linea in lineas))
        revision = extractos.RevisionDeUnaConciliacion(
            lineas=lineas,
            problemas=(),
            total=total,
            sobrante=dinero.resta(por_conciliar, total) or dinero.CERO,
        )

    if revision.problemas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                _que_pasa_con_este_problema(problema) for problema in revision.problemas
            ],
        )
    if not revision.lineas:
        # Nada que apuntar: se dice, en vez de dar por buena una conciliación que no ha hecho nada.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_no_hay_nada_que_apuntar"),
        )

    for linea in revision.lineas:
        # **Una fila por pareja (movimiento, papel)**, que es lo que dice el índice único. Si a este
        # papel ya se le había apuntado dinero **de este mismo movimiento** (los 500 € de una factura de
        # 1.205,40 apuntados primero y los 705,40 después), lo que se suma es **la misma fila con su
        # importe nuevo**. Insertar otra rompería el índice (500 del servidor, sin explicación) y sería
        # contar el mismo dinero dos veces sobre la misma pareja.
        ya_apuntado_aqui = db.scalar(
            select(models.ConciliacionDeMovimiento).where(
                models.ConciliacionDeMovimiento.explotacion_id == explotacion.id,
                models.ConciliacionDeMovimiento.movimiento_id == movimiento.id,
                models.ConciliacionDeMovimiento.clase == linea.documento.clase,
                models.ConciliacionDeMovimiento.documento_id == linea.documento.documento_id,
                models.ConciliacionDeMovimiento.anulada.is_(False),
            )
        )
        if ya_apuntado_aqui is not None:
            ya_apuntado_aqui.importe = dinero.redondea(
                (dinero.a_decimal(ya_apuntado_aqui.importe) or dinero.CERO) + linea.importe
            )
            continue
        db.add(
            models.ConciliacionDeMovimiento(
                explotacion_id=explotacion.id,
                movimiento_id=movimiento.id,
                clase=linea.documento.clase,
                documento_id=linea.documento.documento_id,
                importe=linea.importe,
                usuario_id=usuario.id,
            )
        )
    _el_rastro(
        db,
        explotacion.id,
        movimiento,
        accion="conciliar_movimiento",
        datos={
            "total": dinero.a_texto(revision.total),
            "documentos": [linea.documento.etiqueta for linea in revision.lineas],
            "sobrante": dinero.a_texto(revision.sobrante),
        },
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(movimiento)

    avisos = [
        textos.mensaje(
            "T20_apuntado_contra_un_papel",
            importe=dinero.formatea(revision.total),
            cuantos=len(revision.lineas),
        )
    ]
    if revision.sobrante > 0:
        avisos.append(
            textos.mensaje("T20_todavia_queda_dinero_sin_apuntar", sobrante=dinero.formatea(revision.sobrante))
        )
    return ResultadoDeLaConciliacion(
        movimiento=_como_se_ve_un_movimiento(db, explotacion, movimiento, nombres.get(movimiento.cuenta_id)),
        conciliaciones=[
            ConciliacionHecha(
                documento=linea.documento.etiqueta,
                clase=linea.documento.clase,
                documento_id=linea.documento.documento_id,
                importe=linea.importe,
            )
            for linea in revision.lineas
        ],
        avisos=avisos,
    )


@router.post("/movimientos/{movimiento_id}/desconciliar", response_model=ResultadoDeLaConciliacion)
def deshacer_la_conciliacion(
    movimiento_id: int,
    datos: ConciliacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> ResultadoDeLaConciliacion:
    """Deshace lo apuntado. **El movimiento del banco no se toca, y queda el rastro.**

    Es la regla del contrato, literal: «Deshacer conciliación no borra el movimiento original». El
    banco ya movió ese dinero y eso no se puede deshacer; lo que se deshace es **a qué papeles se había
    apuntado**. Por eso las conciliaciones no se borran: se marcan como deshechas, con la fecha, quién
    lo deshizo y el motivo, y el importe vuelve a quedar pendiente en cada papel.
    """
    movimiento = obtener_de_la_explotacion(
        db, models.MovimientoDeExtracto, movimiento_id, explotacion.id
    )
    consulta = select(models.ConciliacionDeMovimiento).where(
        models.ConciliacionDeMovimiento.explotacion_id == explotacion.id,
        models.ConciliacionDeMovimiento.movimiento_id == movimiento.id,
        models.ConciliacionDeMovimiento.anulada.is_(False),
    )
    if datos.imputaciones:
        claves = [(i.clase, i.documento_id) for i in datos.imputaciones]
        consulta = consulta.where(
            or_(
                *[
                    (
                        models.ConciliacionDeMovimiento.clase == clase
                    ) & (models.ConciliacionDeMovimiento.documento_id == documento_id)
                    for clase, documento_id in claves
                ]
            )
        )
    vivas = list(db.scalars(consulta).all())
    if not vivas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_no_hay_nada_que_deshacer"),
        )

    ahora = dt.datetime.now()
    devuelto = dinero.CERO
    devueltas: list[ConciliacionHecha] = []
    for fila in vivas:
        importe = dinero.a_decimal(fila.importe) or dinero.CERO
        devuelto = dinero.suma(devuelto, importe)
        fila.anulada = True
        fila.deshecha_en = ahora
        fila.deshecha_por_usuario_id = usuario.id
        fila.motivo_del_deshacer = textos.mensaje("T20_deshacer_a_mano")
        devueltas.append(
            ConciliacionHecha(
                documento=f"{fila.clase}:{fila.documento_id}",
                clase=fila.clase,
                documento_id=fila.documento_id,
                importe=importe,
            )
        )
    _el_rastro(
        db,
        explotacion.id,
        movimiento,
        accion="desconciliar_movimiento",
        datos={
            "devuelto": dinero.a_texto(devuelto),
            "documentos": [f"{fila.clase}:{fila.documento_id}" for fila in vivas],
        },
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(movimiento)
    return ResultadoDeLaConciliacion(
        movimiento=_como_se_ve_un_movimiento(
            db, explotacion, movimiento, _el_nombre_de_la_cuenta(db, explotacion, movimiento.cuenta_id)
        ),
        conciliaciones=devueltas,
        avisos=[
            textos.mensaje(
                "T20_deshecho_el_movimiento_sigue_apuntado", importe=dinero.formatea(devuelto)
            )
        ],
    )


@router.post("/movimientos/{movimiento_id}/traspaso", response_model=ResultadoDeLaConciliacion)
def marcar_o_quitar_un_traspaso(
    movimiento_id: int,
    datos: TraspasoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> ResultadoDeLaConciliacion:
    """Ata (o desata) dos movimientos que son **el mismo dinero cambiando de cuenta**.

    Es el caso A07: con las dos patas atadas, el dinero que solo ha cambiado de sitio **no cuenta como
    ingreso ni como gasto**. Y las condiciones para atarlas se comprueban aquí, una por una, porque
    atar dos cosas que no son el mismo dinero es peor que no atar nada: un cobro de verdad quedaría
    escondido como «dinero movido de sitio».
    """
    movimiento = obtener_de_la_explotacion(
        db, models.MovimientoDeExtracto, movimiento_id, explotacion.id
    )
    if datos.otro_movimiento_id is None:
        return _quitar_el_traspaso(db, explotacion, movimiento, usuario)

    otro = obtener_de_la_explotacion(
        db, models.MovimientoDeExtracto, datos.otro_movimiento_id, explotacion.id
    )
    if otro.id == movimiento.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_el_traspaso_necesita_dos_movimientos"),
        )
    if movimiento.cuenta_id == otro.cuenta_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_un_traspaso_va_entre_dos_cuentas"),
        )
    if (
        movimiento.importe is None
        or otro.importe is None
        or dinero.a_decimal(movimiento.importe) != dinero.a_decimal(otro.importe)
        or not movimiento.signo
        or not otro.signo
        or movimiento.signo == otro.signo
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_eso_no_parece_un_traspaso"),
        )
    if movimiento.pareja_de_traspaso_id not in (None, otro.id) and otro.pareja_de_traspaso_id not in (
        None,
        movimiento.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_esos_movimientos_ya_estan_atados"),
        )
    movimiento.pareja_de_traspaso_id = otro.id
    otro.pareja_de_traspaso_id = movimiento.id
    _el_rastro(
        db,
        explotacion.id,
        movimiento,
        accion="marcar_traspaso_propio",
        datos={"pareja": otro.id, "importe": dinero.a_texto(dinero.a_decimal(movimiento.importe))},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(movimiento)
    return ResultadoDeLaConciliacion(
        movimiento=_como_se_ve_un_movimiento(
            db, explotacion, movimiento, _el_nombre_de_la_cuenta(db, explotacion, movimiento.cuenta_id)
        ),
        avisos=[textos.mensaje("T20_traspaso_atado")],
    )


def _quitar_el_traspaso(db, explotacion, movimiento, usuario) -> ResultadoDeLaConciliacion:
    if movimiento.pareja_de_traspaso_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("T20_ese_movimiento_no_es_un_traspaso"),
        )
    pareja = db.get(models.MovimientoDeExtracto, movimiento.pareja_de_traspaso_id)
    movimiento.pareja_de_traspaso_id = None
    if pareja is not None and pareja.explotacion_id == explotacion.id:
        pareja.pareja_de_traspaso_id = None
    _el_rastro(
        db,
        explotacion.id,
        movimiento,
        accion="quitar_traspaso_propio",
        datos={"pareja": pareja.id if pareja is not None else None},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(movimiento)
    return ResultadoDeLaConciliacion(
        movimiento=_como_se_ve_un_movimiento(
            db, explotacion, movimiento, _el_nombre_de_la_cuenta(db, explotacion, movimiento.cuenta_id)
        ),
        avisos=[textos.mensaje("T20_traspaso_quitado")],
    )
