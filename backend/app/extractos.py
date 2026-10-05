"""Leer un extracto de banco y cuadrarlo con los papeles de la finca (T20, E11).

## Qué es esto, y qué no

**Se lee un fichero y nada más.** No hay ninguna conexión con ningún banco: ni de verdad ni de
mentira, ni claves, ni direcciones de internet, ni un cliente de prueba. Lo prohíbe el encargo con
estas palabras, y aquí se cumple al pie de la letra: lo único que entra por esta puerta es **un
fichero que el agricultor ha descargado de su banca y ha subido él**. Todo lo que hay en este
módulo se puede probar con un fichero inventado, sin tarjeta, sin contraseña y sin cobertura.

**Y no hay FastAPI aquí.** Esto son funciones puras —leer un texto, decidir qué fila no se entiende,
calcular qué documento salda un movimiento— para que se puedan probar hoy, sin base de datos y sin
servidor. El router (`app/routers/extractos_api.py`) es quien habla HTTP, quien guarda y quien
escribe el rastro.

## Las cuatro reglas del ticket, y dónde está cada una

1. **Importar dos veces el mismo extracto no duplica movimientos** — `clave_de_duplicado()` y
   `separa_lo_que_ya_estaba()`. La clave no se inventa: es lo que identifica una línea de un
   extracto de verdad (la referencia del banco si la trae; si no, su día, su importe, su signo, su
   concepto y su saldo), más **el número de veces que esa misma línea aparece dentro del fichero**,
   que es el detalle que hace que un extracto con dos compras idénticas del mismo día siga teniendo
   dos movimientos en vez de uno.
2. **Un traspaso entre cuentas propias no crea ingresos** — `detectar_traspasos()` y
   `resumen_de_lo_que_ha_entrado_y_salido()` (el caso **A07**: dos movimientos de 500 € atados, cero
   ingreso y cero gasto).
3. **Importar no crea ningún ingreso ni ningún gasto, y conciliar tampoco** — `propone_…`,
   `revisa_una_conciliacion()` y `deshace_una_conciliacion()`. Estas funciones **solo devuelven a qué
   documento apunta el dinero**: no hay ninguna que fabrique un documento, un pago ni un movimiento.
4. **Un importe que no consta NO es cero** — `FilaDeExtracto.importe` es `None`, y `None` viaja
   hasta el cálculo (no se suma), hasta la pantalla (vacío) y hasta el CSV que se exporta (casilla
   en blanco). Hay una prueba que falla si aparece un `0,00` donde no había importe.

## Lo que este módulo NO hace, y se dice para que nadie lo dé por hecho

- **No adivina.** Una fila que no se entiende se **rechaza con su motivo y su número de línea**, no
  se rellena con lo que parece. Los tres casos que importan están aquí dentro y cada uno tiene su
  prueba: la fecha que puede ser de dos maneras (`03/04/2026` sin haber dicho el formato), el
  importe sin forma de saber si el dinero entra o sale, y el fichero que trae a la vez debe y haber.
- **No lee el formato de un banco concreto** (OFX, QFX, CAMT.053, Norma 43). Hoy se lee **CSV con
  cabecera y perfiles de formato guardables**, que es lo que el contrato pide en S14 («perfiles de
  formato guardables y rechazo de filas ambiguas») y lo que exporta casi cualquier banca. Lo que
  falta está enumerado en `FORMATOS_QUE_FALTAN`, y no se simula: un lector de OFX escrito a ojo
  contra un fichero inventado sería un lector que no funciona con el de verdad.
- **No guarda el fichero del extracto.** Un extracto lleva el número de cuenta completo y los
  nombres de terceros; los movimientos que se guardan son ya todo lo que hace falta, y el fichero se
  queda donde estaba. Lo que sí se guarda es su huella, para poder decir «este mismo fichero ya lo
  importaste».
- **No decide si un movimiento es un ingreso.** Eso lo dice el signo de la línea del banco, y es un
  hecho del extracto, no una opinión del programa.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field, replace
from decimal import Decimal
from itertools import combinations
from typing import Collection, Iterable, Mapping, Sequence

from . import dinero

# --------------------------------------------------------------------------
# El signo: entra o sale
#
# **Y solo dos valores, a propósito.** Con un importe delante, un banco siempre dice si el dinero
# entra o sale; lo que puede pasar es que el fichero no lo diga de una forma que se entienda, y
# entonces la fila **se rechaza**. Admitir aquí un tercer valor («no sé») sería admitir un movimiento
# del que no se sabe si suma o resta, y ese movimiento no se puede sumar, ni conciliar, ni cuadrar.
# --------------------------------------------------------------------------

ENTRA = "entra"
SALE = "sale"
SIGNOS = (ENTRA, SALE)

# --------------------------------------------------------------------------
# Cómo dice el fichero si el dinero entra o sale (el «estilo del signo»)
# --------------------------------------------------------------------------

# El importe viene con su signo («-320,00» quiere decir que sale).
SIGNO_EN_EL_IMPORTE = "en_el_importe"
# Dos columnas: una de debe (sale) y otra de haber (entra).
SIGNO_DEBE_HABER = "debe_haber"
# Una columna con el importe en positivo y otra que dice «A»/«D», «ABONO»/«CARGO»…
SIGNO_EN_SU_COLUMNA = "en_su_columna"

ESTILOS_DE_SIGNO = (SIGNO_EN_EL_IMPORTE, SIGNO_DEBE_HABER, SIGNO_EN_SU_COLUMNA)

# Lo que se admite como «entra» y como «sale» cuando el signo viene en su propia columna.
#
# **Las letras sueltas «C» y «D» NO están en ninguna de las dos listas, y es una decisión.** En un
# banco «C» es crédito (entra) y «D» es débito (sale); en otro, «C» es cargo y «D» es… cualquier
# cosa. Una letra que significa dos cosas contrarias según quién la escriba no se puede leer: si
# aparece, la fila se rechaza diciendo qué pasa, y quien tenga ese fichero añade la letra a su
# perfil una vez y ya está. Adivinar aquí sería cambiar el signo de todo un extracto.
DICEN_QUE_ENTRA_POR_DEFECTO = (
    "A",
    "ABONO",
    "ABONOS",
    "H",
    "HABER",
    "CREDITO",
    "INGRESO",
    "ENTRADA",
    "ENTRADA",
    "+",
)
DICEN_QUE_SALE_POR_DEFECTO = (
    "D",
    "DEBE",
    "CARGO",
    "CARGOS",
    "ADEUDO",
    "DEBITO",
    "PAGO",
    "SALIDA",
    "-",
)

# --------------------------------------------------------------------------
# Las columnas: se buscan por su etiqueta, nunca por su letra
#
# La receta de este programa, que ya salvó la lectura del cuaderno de la Junta: **la plantilla de
# quien publica el fichero cambia**, y una lectura por posición («la columna L») se rompe en
# silencio y devuelve datos de otro sitio. Aquí se busca cada dato por el texto de su cabecera, y
# las columnas de un extracto se llaman de muchas maneras distintas según el banco.
# --------------------------------------------------------------------------

# Nombres nuestros para las columnas. Son la clave del diccionario `PerfilDeFormato.columnas`.
COLUMNAS_QUE_SE_BUSCAN = (
    "fecha",
    "fecha_valor",
    "concepto",
    "importe",
    "saldo",
    "referencia",
    "debe",
    "haber",
    "signo",
)

# Cómo se llama cada columna en el fichero, con las formas que se han visto en extractos de verdad.
# El orden importa: «fecha valor» se prueba antes que «fecha», porque si no, la etiqueta larga
# acabaría leída como la corta (es el mismo defecto que se encontró en el cuaderno de la Junta, con
# el número de registro nacional y el autonómico).
ETIQUETAS_DE_COLUMNA: dict[str, tuple[str, ...]] = {
    "fecha_valor": ("fecha valor", "f valor", "fecha de valor"),
    "fecha": ("fecha", "fecha operacion", "fecha de operacion", "fecha movimiento", "dia", "fecha contable"),
    "concepto": (
        "concepto",
        "concepto ampliado",
        "descripcion",
        "descripcion ampliada",
        "movimiento",
        "detalle",
        "operacion",
    ),
    "importe": ("importe", "importe eur", "importe euros", "cantidad", "euros", "importe operacion"),
    "saldo": ("saldo", "saldo disponible", "saldo contable", "saldo despues", "saldo resultante"),
    "referencia": (
        "referencia",
        "referencia ampliada",
        "referencia del movimiento",
        "documento",
        "num documento",
        "numero documento",
        "numero de documento",
        "ref",
    ),
    "debe": ("debe", "cargo", "cargos", "adeudo", "debito", "importe cargo", "salida"),
    "haber": ("haber", "abono", "abonos", "credito", "importe abono", "entrada"),
    "signo": ("signo", "tipo", "tipo de operacion", "clase", "d/h", "cargo abono"),
}

# Las que se trae un extracto de verdad, que es lo que se usa cuando el agricultor no ha guardado
# ningún perfil: los nombres tal y como los escribe una banca española corriente.
COLUMNAS_DE_UN_EXTRACTO: dict[str, str] = {
    "fecha": "Fecha",
    "fecha_valor": "Fecha valor",
    "concepto": "Concepto",
    "importe": "Importe",
    "saldo": "Saldo",
    "referencia": "Referencia",
    "debe": "Debe",
    "haber": "Haber",
    "signo": "Signo",
}

# --------------------------------------------------------------------------
# Los formatos que faltan, dichos y no simulados
# --------------------------------------------------------------------------

FORMATOS_QUE_FALTAN = {
    "ofx": (
        "El formato OFX/QFX (el que exportan muchas bancas de otros países y algunos programas de "
        "contabilidad). Se leería igual de bien que un CSV, pero **no se ha escrito a ciegas**: "
        "hace falta un fichero de ejemplo de verdad para probarlo, y no se copia el de ningún "
        "agricultor. Mientras no esté, ese fichero se sube tal cual y el programa dice que no lo "
        "entiende, en vez de leer la mitad."
    ),
    "camt053": (
        "El CAMT.053 (el extracto en XML de la norma ISO 20022, que es el que da la banca "
        "electrónica de empresas). Falta lo mismo que el OFX: un ejemplo real con el que "
        "escribirlo y probarlo."
    ),
    "norma43": (
        "La Norma 43 de la AEB (el fichero de 80 columnas de toda la vida, con cabecera de cuenta "
        "y totales). Es el formato más fiel que existe para una cuenta española y también el más "
        "delicado: lleva el IBAN completo y los totales de control. Se puede hacer, y se hará "
        "cuando haya un fichero de ejemplo autorizado."
    ),
}

# --------------------------------------------------------------------------
# Los motivos por los que una fila se rechaza
#
# Son **claves, no frases**: las frases las escribe `textos.py`, que es donde vive todo lo que lee
# el agricultor. Aquí se dice qué ha pasado, en un idioma que el programa entiende.
# --------------------------------------------------------------------------

SIN_FECHA = "sin_fecha"
FECHA_AMBIGUA = "fecha_ambigua"
FECHA_ILEGIBLE = "fecha_ilegible"
SIN_SIGNO = "sin_signo"
DEBE_Y_HABER = "debe_y_haber"
SIGNO_DESCONOCIDO = "signo_desconocido"
IMPORTE_CERO = "importe_cero"
IMPORTE_ILEGIBLE = "importe_ilegible"
COLUMNAS_DE_MAS = "columnas_de_mas"
SIN_CABECERAS = "sin_cabeceras"

MOTIVOS_DE_RECHAZO = (
    SIN_FECHA,
    FECHA_AMBIGUA,
    FECHA_ILEGIBLE,
    SIN_SIGNO,
    DEBE_Y_HABER,
    SIGNO_DESCONOCIDO,
    IMPORTE_CERO,
    IMPORTE_ILEGIBLE,
    COLUMNAS_DE_MAS,
    SIN_CABECERAS,
)

# Lo que puede faltar en un movimiento que **sí** se guarda. Un importe que no consta no impide
# guardar el movimiento: la línea del banco existe, y lo que no se sabe es cuánto.
IMPORTE_NO_CONSTA = "importe_no_consta"
IMPORTE_ILEGIBLE_EN_LA_FILA = "importe_ilegible_en_la_fila"
SALDO_NO_CONSTA = "saldo_no_consta"
SALDO_ILEGIBLE = "saldo_ilegible"
REFERENCIA_NO_CONSTA = "referencia_no_consta"
CONCEPTO_NO_CONSTA = "concepto_no_consta"

# --------------------------------------------------------------------------
# Los avisos que acompañan a una lectura (también claves)
# --------------------------------------------------------------------------

AVISO_SIN_CABECERAS = "no_se_encuentran_las_cabeceras"
AVISO_NO_SE_SABE_LA_CUENTA = "no_se_sabe_de_que_cuenta_es"
AVISO_IMPORTES_QUE_NO_CONSTAN = "hay_importes_que_no_constan"
AVISO_FILAS_RECHAZADAS = "hay_filas_que_no_se_entienden"
AVISO_SALDO_NO_CUADRA = "el_saldo_no_cuadra"
AVISO_ORDEN_DUDOSO = "el_orden_de_las_filas_es_dudoso"
AVISO_FORMATO_DE_FECHA_SIN_DECLARAR = "el_formato_de_la_fecha_no_esta_declarado"
AVISO_FILAS_SIN_SIGNO = "hay_filas_sin_decir_si_el_dinero_entra_o_sale"

# --------------------------------------------------------------------------
# Estados de la conciliación
# --------------------------------------------------------------------------

SIN_CONCILIAR = "sin_conciliar"
CONCILIADO_EN_PARTE = "conciliado_en_parte"
CONCILIADO = "conciliado"
NO_SE_PUEDE_CONCILIAR = "no_se_puede_conciliar"

ESTADOS_DE_CONCILIACION = (SIN_CONCILIAR, CONCILIADO_EN_PARTE, CONCILIADO, NO_SE_PUEDE_CONCILIAR)

# --------------------------------------------------------------------------
# A qué se puede apuntar un movimiento
#
# El contrato (§11) dibuja la cadena `Vencimiento → AplicacionPago → MovimientoCuenta`. En este
# programa, hoy, lo que se puede pagar o cobrar es esto: el **cobro** que ya apuntó el T12 (dinero
# que entra, con o sin factura), la **factura nuestra** (lo que nos deben) y la **factura de compra**
# (lo que debemos). Todo lo demás (un gasto, una inversión, una nómina) es del T13 y del T08, y está
# declarado abajo en vez de inventado a medias.
# --------------------------------------------------------------------------

COBRO = "cobro"
FACTURA_EMITIDA = "factura_emitida"
FACTURA_DE_COMPRA = "factura_de_compra"

CLASES_DE_DOCUMENTO = (COBRO, FACTURA_EMITIDA, FACTURA_DE_COMPRA)

# Y las que faltan, con quién tiene que traerlas.
CLASES_QUE_FALTAN = {
    "gasto": "T13 (gastos, activos y repartos): un gasto sin factura, con su reparto.",
    "inversion": "T13: una compra de activo, que no es un gasto entero del cultivo.",
    "nomina": "T13: el pago de un trabajador.",
    "cuota_de_prestamo": "T13: el recibo de un préstamo, que no es un gasto de la cosecha.",
}

# --------------------------------------------------------------------------
# Tipos de propuesta de conciliación
# --------------------------------------------------------------------------

PROPUESTA_EXACTA = "exacta"
PROPUESTA_AGRUPADA = "agrupada"
PROPUESTA_PARCIAL = "parcial"

TIPOS_DE_PROPUESTA = (PROPUESTA_EXACTA, PROPUESTA_AGRUPADA, PROPUESTA_PARCIAL)

# Por qué se propone lo que se propone. Son claves, y salen en la pantalla para que el agricultor
# pueda decir «sí» sabiendo por qué se lo proponen.
PORQUE_LA_REFERENCIA_ESTA_EN_EL_CONCEPTO = "la_referencia_esta_en_el_concepto"
PORQUE_EL_NOMBRE_ESTA_EN_EL_CONCEPTO = "el_nombre_esta_en_el_concepto"
PORQUE_EL_IMPORTE_CUADRA = "el_importe_cuadra"
PORQUE_LA_SUMA_CUADRA = "la_suma_cuadra"
PORQUE_LA_FECHA_ESTA_CERCA = "la_fecha_esta_cerca"
PORQUE_LA_FECHA_ESTA_LEJOS = "la_fecha_esta_lejos"

# Lo que impide conciliar, dicho con una clave (nunca con un cero).
NO_PORQUE_NO_CONSTA_EL_IMPORTE = "no_consta_el_importe"
NO_PORQUE_ES_UN_TRASPASO = "es_un_traspaso_entre_cuentas_tuyas"
NO_PORQUE_YA_ESTA_CONCILIADO = "ya_esta_conciliado"
NO_PORQUE_NO_HAY_NADA_PENDIENTE = "no_hay_nada_pendiente_de_esa_clase"

# Y los problemas que se pueden encontrar al revisar una conciliación que pide el agricultor.
PROBLEMA_NO_CONSTA_EL_IMPORTE = "no_consta_el_importe_del_movimiento"
PROBLEMA_IMPORTE_NO_VALE = "el_importe_no_vale"
PROBLEMA_DOCUMENTO_SIN_PENDIENTE = "no_se_sabe_cuanto_le_falta_al_documento"
PROBLEMA_MAS_QUE_EL_PENDIENTE = "se_imputa_mas_de_lo_que_le_falta"
PROBLEMA_MAS_QUE_EL_MOVIMIENTO = "se_imputa_mas_de_lo_que_dice_el_movimiento"
PROBLEMA_DOCUMENTO_REPETIDO = "el_mismo_documento_dos_veces"
PROBLEMA_CLASE_EQUIVOCADA = "ese_documento_no_es_de_este_lado"
PROBLEMA_DE_OTRA_FINCA = "ese_documento_es_de_otra_finca"

PROBLEMAS_DE_UNA_CONCILIACION = (
    PROBLEMA_NO_CONSTA_EL_IMPORTE,
    PROBLEMA_IMPORTE_NO_VALE,
    PROBLEMA_DOCUMENTO_SIN_PENDIENTE,
    PROBLEMA_MAS_QUE_EL_PENDIENTE,
    PROBLEMA_MAS_QUE_EL_MOVIMIENTO,
    PROBLEMA_DOCUMENTO_REPETIDO,
    PROBLEMA_CLASE_EQUIVOCADA,
    PROBLEMA_DE_OTRA_FINCA,
)

# Cuántos días se admite entre dos patas de un traspaso propio. Tres es lo que tarda una
# transferencia entre dos entidades españolas; más que eso ya no es «el mismo dinero pasando de una
# cuenta a otra» y preferimos no proponerlo y que lo diga el agricultor.
DIAS_DE_UN_TRASPASO = 3

# Cuántos documentos puede juntar una propuesta agrupada y cuántas propuestas se le enseñan al
# agricultor. Los dos topes existen por lo mismo: una lista de combinaciones posibles crece muy
# deprisa y termina siendo una pantalla que nadie lee.
MAXIMO_DOCUMENTOS_EN_UNA_AGRUPADA = 4
MAXIMO_DE_PROPUESTAS = 5

# Cuántos días de separación se admiten entre un movimiento y el documento que paga, para poder
# proponerlo sin la referencia. Dos meses es lo que se tarda en cobrar una entrega de cereal.
DIAS_ENTRE_EL_MOVIMIENTO_Y_EL_PAPEL = 60


class ErrorDeExtracto(ValueError):
    """Algo que no se puede aceptar y que ve quien escribe el programa, no el agricultor.

    Es la misma idea que `dinero.ErrorDeDinero`: lo que rompe el contrato de estas funciones se dice
    en alto (un estilo de signo que no existe, un perfil sin columnas), y lo que ve el agricultor es
    una frase de `textos.py`, con su aviso y su «qué hago ahora».
    """


# ==========================================================================
# 1. El perfil de formato: cómo está escrito el fichero
# ==========================================================================


@dataclass(frozen=True)
class PerfilDeFormato:
    """Cómo está escrito un extracto. Se puede guardar y volver a usar (S14).

    ## Por qué esto existe y no se adivina sin más

    No hay dos bancas que exporten igual: una separa con punto y coma, otra con comas, otra con
    tabuladores; una escribe la fecha como `01/06/2026` y otra como `2026-06-01`; una pone el signo
    en el importe y otra en una columna con una letra. Adivinar todo eso funciona **casi** siempre, y
    «casi» en un extracto de banco quiere decir que un día de marzo se convierte en el 3 de enero, o
    que una entrada se apunta como salida.

    Así que aquí está escrito **lo que se sabe y lo que no**: los tres campos que pueden cambiar el
    sentido de un número (`decimal`, `formato_de_fecha` y `sin_signo_quiere_decir`) empiezan en
    `None`, que quiere decir «no me lo has dicho», y con `None` el programa **rechaza la fila que no
    se puede leer sin adivinar** en vez de elegir por su cuenta. Quien manda es el agricultor: el día
    que dice «mi banco escribe la fecha así», se guarda en su perfil y ya no se le vuelve a
    preguntar.
    """

    nombre: str = "Un extracto en columnas"
    # El separador de campos del CSV: «;», «,», tabulador o «|».
    delimitador: str = ";"
    # El separador decimal: «,» o «.». `None` es «no me lo has dicho» y se usa la regla de siempre
    # del programa (`dinero.de_texto`), que es la misma que lee una factura.
    decimal: str | None = None
    # `d/m/Y`, `Y-m-d`, `m/d/Y`… `None` es «no me lo has dicho», y entonces una fecha que se pueda
    # leer de dos maneras **se rechaza** en vez de elegir.
    formato_de_fecha: str | None = None
    estilo_del_signo: str = SIGNO_EN_EL_IMPORTE
    # Solo para el estilo `en_el_importe`: qué quiere decir un número **sin** signo. `None` es «no me
    # lo has dicho» y la fila se rechaza, porque un 40,00 sin signo puede ser un cobro o un pago.
    sin_signo_quiere_decir: str | None = None
    # Solo para el estilo `en_su_columna`: qué dice el fichero cuando el dinero entra y cuando sale.
    dicen_que_entra: tuple[str, ...] = DICEN_QUE_ENTRA_POR_DEFECTO
    dicen_que_sale: tuple[str, ...] = DICEN_QUE_SALE_POR_DEFECTO
    # El nombre de cada dato **en este fichero** («Fecha», «F. Valor», «Concepto ampliado»…).
    columnas: Mapping[str, str] = field(default_factory=lambda: dict(COLUMNAS_DE_UN_EXTRACTO))

    def __post_init__(self) -> None:
        if self.delimitador not in (";", ",", "\t", "|"):
            raise ErrorDeExtracto(
                f"«{self.delimitador}» no es un separador de columnas que se pueda leer."
            )
        if self.decimal not in (None, ",", "."):
            raise ErrorDeExtracto(
                f"«{self.decimal}» no es un separador decimal: solo valen la coma y el punto."
            )
        if self.estilo_del_signo not in ESTILOS_DE_SIGNO:
            raise ErrorDeExtracto(f"«{self.estilo_del_signo}» no es una forma de decir el signo.")
        if self.sin_signo_quiere_decir not in (None, *SIGNOS):
            raise ErrorDeExtracto(
                f"«{self.sin_signo_quiere_decir}» no es un signo: solo valen «entra» y «sale»."
            )
        if self.formato_de_fecha not in (None, "d/m/Y", "Y-m-d", "d-m-Y", "d.m.Y", "m/d/Y", "Y/m/d"):
            raise ErrorDeExtracto(
                f"«{self.formato_de_fecha}» no es una forma de fecha que se pueda leer."
            )

    # El nombre de la columna en el fichero, o `None` si este perfil no la tiene.
    def etiqueta_de(self, columna: str) -> str | None:
        nombre = self.columnas.get(columna)
        return nombre if nombre else None


# ==========================================================================
# 2. Lo que sale de leer el fichero
# ==========================================================================


@dataclass(frozen=True)
class CuentaDelFichero:
    """De qué cuenta habla el extracto, **sin guardar el número de cuenta entero**.

    Un extracto lleva el IBAN completo, que es un dato de la casa que no hace falta para nada de lo
    que se hace aquí: ni para cuadrar los movimientos, ni para conciliarlos, ni para enseñarlos. Lo
    único que hace falta es poder decir «esta es la cuenta que acaba en 5555» y que el agricultor la
    reconozca. Por eso de aquí solo sale el banco (si lo dice el fichero) y **los cuatro últimos
    dígitos**: hay una prueba que comprueba que el número entero no aparece en ningún sitio de lo que
    devuelve este módulo.
    """

    banco: str | None = None
    ultimos_digitos: str | None = None

    @property
    def se_reconoce(self) -> bool:
        return bool(self.ultimos_digitos)

    @property
    def como_se_llama(self) -> str:
        if self.banco and self.ultimos_digitos:
            return f"{self.banco}, cuenta terminada en {self.ultimos_digitos}"
        if self.ultimos_digitos:
            return f"Cuenta terminada en {self.ultimos_digitos}"
        return self.banco or ""


@dataclass(frozen=True)
class FilaDeExtracto:
    """Una línea del extracto, ya leída y ya decidida.

    ## La invariante que hay detrás de los dos campos que van juntos

    `importe` y `signo` **están los dos o no está ninguno**. No es casualidad: si el importe no
    consta, no hay ninguna forma de saber si el dinero entra o sale (no hay ni dinero), y si el
    importe consta, el signo está decidido porque una fila sin signo se rechaza. Hay una prueba que
    recorre todas las filas de todas las pruebas y comprueba que esa pareja nunca se rompe.

    Y lo que no consta, **no se rellena**: `importe` se queda en `None` y `falta` dice por qué
    (`importe_no_consta` cuando la casilla está vacía, `importe_ilegible_en_la_fila` cuando trae algo
    que no es un número). La diferencia entre esos dos casos solo se ve en el motivo que se le da al
    agricultor: en los dos, el importe es «no lo sé», y en ninguno es cero.
    """

    numero_de_linea: int
    fecha: dt.date | None
    concepto: str | None
    importe: Decimal | None
    signo: str | None
    saldo: Decimal | None
    referencia: str | None
    cuenta: str | None
    clave_de_duplicado: str
    fecha_valor: dt.date | None = None
    falta: tuple[str, ...] = ()
    es_traspaso_propio: bool = False
    explotacion_id: int | None = None

    @property
    def se_puede_conciliar(self) -> bool:
        """Si con este movimiento se puede pagar o cobrar algo.

        Sin importe, no: no se sabe cuánto. Y sin signo no llegaría hasta aquí (se rechaza al leer).
        """
        return self.importe is not None and self.signo in SIGNOS and self.importe > 0

    @property
    def entra_el_dinero(self) -> bool:
        return self.signo == ENTRA

    @property
    def importe_con_signo(self) -> Decimal | None:
        """El importe tal y como afecta a la cuenta: negativo si el dinero sale."""
        if self.importe is None:
            return None
        return self.importe if self.signo == ENTRA else -self.importe


@dataclass(frozen=True)
class FilaRechazada:
    """Una fila que **no** se ha podido leer, con su motivo y su número.

    Se rechaza en vez de adivinar, y se guarda el texto de la fila tal cual: es lo único que le
    permite al agricultor reconocerla en su fichero y decir qué pasa («ah, pues esa línea es la del
    recibo del seguro, que viene sin signo»).
    """

    numero_de_linea: int
    motivo: str
    texto: str
    lo_que_dice: str | None = None


@dataclass(frozen=True)
class Aviso:
    """Un aviso de la lectura, con las líneas de las que habla.

    Va con clave y no con frase, por la regla de siempre: la frase la escribe `textos.py`. Y lleva
    los números de línea porque un aviso sin ellos obliga al agricultor a buscar a mano.
    """

    codigo: str
    lineas: tuple[int, ...] = ()
    datos: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LecturaDelExtracto:
    """Lo que ha salido de leer un fichero. **Todavía no se ha guardado nada.**"""

    movimientos: tuple[FilaDeExtracto, ...]
    rechazadas: tuple[FilaRechazada, ...]
    cuenta: CuentaDelFichero
    saldo_final: Decimal | None
    columnas: Mapping[str, str]
    perfil: PerfilDeFormato
    avisos: tuple[Aviso, ...] = ()
    huella: str = ""
    lineas_leidas: int = 0

    @property
    def cuantos_sin_importe(self) -> int:
        return sum(1 for fila in self.movimientos if fila.importe is None)

    @property
    def esta_vacio(self) -> bool:
        return not self.movimientos and not self.rechazadas

    def cuantas_lineas(self, motivo: str) -> tuple[int, ...]:
        return tuple(f.numero_de_linea for f in self.rechazadas if f.motivo == motivo)


# ==========================================================================
# 3. Leer el fichero
# ==========================================================================

VACIO = "vacio"
ILEGIBLE = "ilegible"
LEIDO = "leido"

LEIDA = "leida"
AMBIGUA = "ambigua"

# La pista de un IBAN en el texto del fichero. **Solo se usa para sacar los cuatro últimos dígitos**
# y para saber de qué cuenta habla el extracto: lo que se encuentra no se guarda.
_PISTA_DE_CUENTA = re.compile(r"\b[A-Z]{2}\s?\d{2}(?:[\s\-]?\d){10,26}\b")

# Una fecha de un extracto: 01/06/2026, 1-6-26, 2026.06.01…
_PISTA_DE_FECHA = re.compile(r"^(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})$")


def huella_del_fichero(datos: bytes) -> str:
    """La huella del fichero que se sube, para poder decir «este mismo ya lo importaste».

    Se calcula sobre los bytes que ha subido el navegador, tal cual: si el agricultor vuelve a
    descargar el extracto de su banca y lo sube otra vez, la huella es la misma. Y si el banco ha
    añadido movimientos nuevos, no lo es —que es justo lo que hay que distinguir, porque entonces lo
    que hay que hacer es importar **solo lo nuevo**—.
    """
    return hashlib.sha256(datos).hexdigest()


def lee_el_texto(datos: bytes) -> str:
    """Los bytes del fichero, en texto. **Y se dice cómo se ha leído.**

    Los extractos que exporta una banca española llegan de dos maneras: en UTF-8 (los programas
    nuevos) y en Windows-1252 (Excel y todo lo que pasó por Excel). Decodificar el segundo como si
    fuera el primero no da un error: deja los acentos convertidos en basura, y como el concepto de un
    movimiento se usa para buscar la referencia y el nombre de la otra parte, un concepto roto es una
    conciliación que no se propone. Por eso se prueba UTF-8 primero —que además quita la marca de
    orden de bytes si la trae— y solo si falla se pasa al de Windows.
    """
    for juego in ("utf-8-sig", "cp1252"):
        try:
            return datos.decode(juego)
        except UnicodeDecodeError:
            continue
    # `latin-1` no falla nunca (cualquier byte es un carácter), así que esto no revienta jamás.
    return datos.decode("latin-1")


def sin_tildes_y_en_minusculas(texto: str | None) -> str:
    """Un texto para comparar: sin tildes, en minúsculas y con los espacios de dentro juntos.

    Se usa para comparar (¿el concepto lleva el nombre del cliente?, ¿es la misma referencia?), nunca
    para guardar: lo que dice el banco se guarda tal cual. Es la misma idea que el `sin_tildes` de
    las pruebas de jerga, y aquí importa porque un concepto puede venir en mayúsculas con tildes
    («TRANSFERENCIA RECIBIDA COOPERATIVA EJEMPLO») y el nombre del cliente estar escrito de otra
    manera.
    """
    if not texto:
        return ""
    descompuesto = unicodedata.normalize("NFD", texto)
    plano = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", plano).strip().lower()


def _lee_un_numero(texto: str | None, *, decimal_declarado: str | None) -> tuple[Decimal | None, str]:
    """Un número de una casilla, con lo que se ha podido saber de él.

    Devuelve `(valor, estado)`, y el estado es la mitad del trabajo: `vacio` («esa casilla no trae
    nada»), `ilegible` («trae algo, y no es un número») y `leido`. La diferencia no es un detalle de
    estilo: es lo que permite decirle al agricultor «en la fila 7 no hay importe» o «en la fila 9 hay
    algo que no se ha podido leer», que son dos cosas distintas, en vez de las dos un cero.

    **El separador decimal declarado manda.** Si el perfil dice que el decimal es la coma, el punto
    se quita como separador de miles aunque eso convierta un `40.00` en cuatro mil: el agricultor ha
    dicho cómo escribe su banco, y quien mejor que él lo sabe. Si no lo ha dicho (`None`), se usa la
    regla de siempre del programa (`dinero.de_texto`), que es la misma con la que se lee la factura
    de un proveedor —tener dos reglas para «qué significa este número» sería tener dos verdades—.
    """
    limpio = (texto or "").strip().replace("\u00a0", "").replace(" ", "")
    if not limpio:
        return (None, VACIO)
    limpio = limpio.removesuffix("€").strip()
    # Algunos extractos escriben el signo detrás («40,00-»). Se pasa delante, que es donde se lee.
    if limpio.endswith("-") and not limpio.startswith("-"):
        limpio = "-" + limpio[:-1]
    if decimal_declarado:
        el_otro = "." if decimal_declarado == "," else ","
        limpio = limpio.replace(el_otro, "")
        if decimal_declarado == ",":
            limpio = limpio.replace(",", ".")
    try:
        valor = dinero.de_texto(limpio)
    except dinero.ErrorDeDinero:
        return (None, ILEGIBLE)
    if valor is None:
        return (None, VACIO)
    return (valor, LEIDO)


def _lee_una_fecha(
    texto: str | None, *, formato_declarado: str | None
) -> tuple[dt.date | None, str]:
    """Una fecha de una casilla, o el motivo por el que no se puede leer.

    ## La regla que hace falta aquí, y por qué no se adivina

    `03/04/2026` es el 3 de abril en España y el 4 de marzo en medio mundo. En un extracto de banco
    esa diferencia mueve un movimiento de trimestre, así que **no se elige**:

      · si el perfil dice el formato, se lee como dice el perfil, y punto;
      · si no lo dice, se lee sin adivinar cuando el texto no es ambiguo (el día 13 no puede ser un
        mes; un año de cuatro cifras delante se lee solo; y `03/03/2026` es el 3 de marzo de las dos
        maneras);
      · y cuando de verdad se puede leer de dos maneras distintas, **la fila se rechaza** con el
        motivo `fecha_ambigua`, y la pantalla pide el formato del fichero. Es un segundo de trabajo
        para el agricultor una vez, y a cambio no se le mueve un apunte de mes.
    """
    limpio = (texto or "").strip()
    if not limpio:
        return (None, VACIO)
    trozos = _PISTA_DE_FECHA.match(limpio)
    if not trozos:
        return (None, ILEGIBLE)
    primero, segundo, tercero = (int(g) for g in trozos.groups())

    if formato_declarado:
        orden = formato_declarado.replace(".", "/").replace("-", "/").split("/")
        valores = {"d": primero, "m": segundo, "Y": tercero, "y": tercero}
        if [p[0] for p in orden] == ["Y", "m", "d"]:
            valores = {"Y": primero, "m": segundo, "d": tercero}
        elif [p[0] for p in orden] == ["m", "d", "Y"]:
            valores = {"m": primero, "d": segundo, "Y": tercero}
        elif [p[0] for p in orden] == ["d", "m", "Y"]:
            valores = {"d": primero, "m": segundo, "Y": tercero}
        else:  # pragma: no cover - el perfil ya valida los formatos que admite
            return (None, ILEGIBLE)
        return _monta_la_fecha(valores["d"], valores["m"], valores["Y"])

    # Sin formato declarado: se lee solo lo que no se puede leer mal.
    if primero > 31:
        # Un año delante: 2026-06-01.
        return _monta_la_fecha(tercero, segundo, primero)
    if primero > 12:
        return _monta_la_fecha(primero, segundo, tercero)
    if segundo > 12:
        # El mes va delante: 06/25/2026.
        return _monta_la_fecha(tercero, primero, segundo)
    if primero == segundo:
        # Da igual cómo se lea: 03/03/2026 es el 3 de marzo.
        return _monta_la_fecha(primero, segundo, tercero)
    return (None, AMBIGUA)


def _monta_la_fecha(dia: int, mes: int, anio: int) -> tuple[dt.date | None, str]:
    """La fecha, si existe en el calendario. Un 31 de febrero no se arregla: se dice."""
    if anio < 100:
        # Un año de dos cifras es de este siglo: un extracto que se descarga hoy no es de 1926.
        anio += 2000
    try:
        return (dt.date(anio, mes, dia), LEIDA)
    except ValueError:
        return (None, ILEGIBLE)


def deduce_el_formato_de_la_fecha(
    celdas: Sequence[tuple[int, str]],
) -> tuple[str | None, tuple[int, ...]]:
    """El formato de la fecha, deducido **de la evidencia del propio fichero**.

    Devuelve `(formato, líneas que lo demuestran)`, y `None` cuando el fichero no lo dice.

    ## Por qué se mira el fichero entero y no cada línea por su cuenta

    `03/04/2026` no se puede leer si no se sabe el orden de los tres números. Pero un extracto no
    trae una sola fecha: trae un mes entero, y **en cuanto una sola línea tiene un día del 13 en
    adelante, el orden de todas queda claro** (el 13 no puede ser un mes). Eso no es adivinar: es
    leer la prueba que está en el fichero, y es la misma forma de trabajar que el saldo de cada
    línea, que también sirve para comprobar la lectura.

    Lo que **no** se hace es elegir cuando el fichero se contradice (unas fechas que solo pueden ser
    día/mes/año y otras que solo pueden ser mes/día/año, o con el año delante y detrás mezclados):
    ahí se devuelve `None` y las líneas dudosas se rechazan, que es lo que hay que hacer cuando dos
    datos del mismo fichero dicen cosas distintas.
    """
    anio_delante: list[int] = []
    dia_primero: list[int] = []
    mes_primero: list[int] = []
    for numero, texto in celdas:
        trozos = _PISTA_DE_FECHA.match((texto or "").strip())
        if not trozos:
            continue
        primero, segundo, _tercero = (int(g) for g in trozos.groups())
        if primero > 31:
            anio_delante.append(numero)
        elif primero > 12:
            dia_primero.append(numero)
        elif segundo > 12:
            mes_primero.append(numero)

    if mes_primero and (dia_primero or anio_delante):
        return (None, ())
    if mes_primero:
        return ("m/d/Y", tuple(mes_primero))
    if anio_delante and dia_primero:
        return (None, ())
    if anio_delante:
        return ("Y-m-d", tuple(anio_delante))
    if dia_primero:
        return ("d/m/Y", tuple(dia_primero))
    return (None, ())


def _lee_el_importe_y_el_signo(
    fila: Sequence[str],
    indices: Mapping[str, int],
    perfil: PerfilDeFormato,
) -> tuple[Decimal | None, str | None, str]:
    """El importe y si el dinero entra o sale, o el motivo por el que no se puede saber.

    Devuelve `(importe, signo, estado)`. Los estados que acaban en fila rechazada son los que
    impiden saber el **signo**: `sin_signo`, `debe_y_haber` y `signo_desconocido`. Los que dejan el
    importe en «no lo sé» (`sin_importe` e `ilegible`) **no rechazan la fila**: la línea del banco
    existe y se guarda con lo que se sabe, que es todo menos el número.
    """

    def celda(nombre: str) -> str:
        posicion = indices.get(nombre)
        if posicion is None or posicion >= len(fila):
            return ""
        return fila[posicion]

    if perfil.estilo_del_signo == SIGNO_DEBE_HABER:
        debe, estado_debe = _lee_un_numero(celda("debe"), decimal_declarado=perfil.decimal)
        haber, estado_haber = _lee_un_numero(celda("haber"), decimal_declarado=perfil.decimal)
        # Una casilla vacía es «ahí no hay nada»; una casilla con un cero **es un cero**, que es un
        # dato distinto. Por eso se miran los dos estados y no solo si el número vale cero.
        if estado_debe == estado_haber == VACIO:
            return (None, None, VACIO)
        if ILEGIBLE in (estado_debe, estado_haber) and LEIDO not in (estado_debe, estado_haber):
            return (None, None, IMPORTE_ILEGIBLE)
        hay_debe = debe is not None and debe != 0
        hay_haber = haber is not None and haber != 0
        if hay_debe and hay_haber:
            # Las dos columnas con número: el fichero no dice cuál manda, y elegir una sería
            # inventarse el signo de un movimiento.
            return (None, None, DEBE_Y_HABER)
        if not hay_debe and not hay_haber:
            # Hay número (un cero, al menos) pero no hay dinero que mover.
            return (None, None, IMPORTE_CERO)
        if hay_debe:
            return (abs(debe), SALE, LEIDO)
        return (abs(haber), ENTRA, LEIDO)

    valor, estado = _lee_un_numero(celda("importe"), decimal_declarado=perfil.decimal)
    if estado == VACIO:
        return (None, None, VACIO)
    if estado == ILEGIBLE:
        return (None, None, IMPORTE_ILEGIBLE)
    assert valor is not None  # el estado `leido` siempre trae número
    if valor == 0:
        # Un movimiento de cero euros no es un movimiento: no hay dinero que conciliar y solo llena
        # la lista de renglones que no dicen nada. Es la misma decisión que en un cobro (T12).
        return (None, None, IMPORTE_CERO)

    if perfil.estilo_del_signo == SIGNO_EN_EL_IMPORTE:
        if valor < 0:
            return (abs(valor), SALE, LEIDO)
        if perfil.sin_signo_quiere_decir is None:
            # Un 40,00 sin signo puede ser un cobro o un pago, y el fichero no lo dice.
            return (None, None, SIN_SIGNO)
        return (abs(valor), perfil.sin_signo_quiere_decir, LEIDO)

    # El signo en su propia columna.
    que_dice = sin_tildes_y_en_minusculas(celda("signo"))
    if not que_dice:
        return (None, None, SIN_SIGNO)
    if que_dice in {sin_tildes_y_en_minusculas(v) for v in perfil.dicen_que_entra}:
        return (abs(valor), ENTRA, LEIDO)
    if que_dice in {sin_tildes_y_en_minusculas(v) for v in perfil.dicen_que_sale}:
        return (abs(valor), SALE, LEIDO)
    return (None, None, SIGNO_DESCONOCIDO)


def detecta_las_columnas(cabeceras: Sequence[str]) -> dict[str, str]:
    """Qué columna es cada cosa, **por el texto de su cabecera**.

    Se prueba primero la etiqueta más larga que encaje, para que «Fecha valor» no acabe leída como
    «Fecha» —que es el defecto que se encontró leyendo el cuaderno de la Junta, donde el número de
    registro nacional salía del autonómico por leer «la celda de al lado»—. Y se admite una etiqueta
    que *contenga* al nombre conocido, porque los ficheros de verdad escriben «Importe (EUR)».
    """
    encontradas: dict[str, str] = {}
    candidatas: list[tuple[int, str, str]] = []
    for columna, etiquetas in ETIQUETAS_DE_COLUMNA.items():
        for etiqueta in etiquetas:
            candidatas.append((len(etiqueta), columna, etiqueta))
    candidatas.sort(key=lambda c: -c[0])

    for cabecera in cabeceras:
        limpia = sin_tildes_y_en_minusculas(cabecera)
        if not limpia:
            continue
        for _largo, columna, etiqueta in candidatas:
            if columna in encontradas:
                continue
            if limpia == etiqueta or limpia.startswith(etiqueta) or etiqueta in limpia:
                encontradas[columna] = cabecera.strip()
                break
    return encontradas


def adivina_el_delimitador(lineas: Sequence[str]) -> str:
    """El separador de campos, contando cuál aparece más en la cabecera del fichero.

    Se cuenta en las primeras líneas y no en todo el fichero a propósito: un concepto puede llevar
    comas dentro («PAGO SEGURO, RECIBO 4471») y con el fichero entero ganaría la coma, que no es el
    separador de nada.
    """
    cuenta = {";": 0, ",": 0, "\t": 0, "|": 0}
    for linea in lineas[:20]:
        for separador in cuenta:
            cuenta[separador] += linea.count(separador)
    mejor = max(cuenta, key=lambda s: cuenta[s])
    return mejor if cuenta[mejor] > 0 else ";"


def _parte_en_filas(texto: str) -> list[list[str]]:
    """El fichero en filas de celdas, con el separador que se haya adivinado."""
    delimitador = adivina_el_delimitador(texto.splitlines())
    lector = csv.reader(io.StringIO(texto), delimiter=delimitador)
    return [fila for fila in lector]


def _busca_la_cabecera(
    filas: Sequence[Sequence[str]], perfil: PerfilDeFormato | None
) -> tuple[int | None, list[str], dict[str, str], dict[str, int]]:
    """Dónde está la fila de las cabeceras, y qué columna es cada cosa.

    Un extracto de verdad **no empieza por la tabla**: empieza por el nombre del banco, el de la
    cuenta, el periodo y el saldo. Por eso la cabecera se busca por su contenido (la fila que
    reconoce más columnas) y no por «la fila 5», que es la otra mitad de la receta de este programa
    al leer un fichero que publica otro: lo que se busca por su etiqueta no se rompe cuando el
    fichero cambia.

    Devuelve `(fila de la cabecera, sus celdas, qué columna es cada cosa, y en qué casilla está)`.
    **La casilla se busca por la etiqueta, no por el orden**: si el banco cambia dos columnas de
    sitio, la lectura sigue siendo la misma, que es justo lo que no pasaría leyendo «la columna L».
    """
    mejor: tuple[int | None, list[str], dict[str, str], dict[str, int], int] = (None, [], {}, {}, 0)
    for numero, fila in enumerate(list(filas)[:40]):
        if perfil is not None:
            # Lo que el agricultor ha dicho que se llama cada columna en su fichero, comparado sin
            # tildes y sin mayúsculas.
            conocidas = {
                sin_tildes_y_en_minusculas(etiqueta): columna
                for columna, etiqueta in perfil.columnas.items()
                if etiqueta
            }
            encontradas: dict[str, str] = {}
            indices: dict[str, int] = {}
            for posicion, celda in enumerate(fila):
                columna = conocidas.get(sin_tildes_y_en_minusculas(celda))
                if columna and columna not in encontradas:
                    encontradas[columna] = (celda or "").strip()
                    indices[columna] = posicion
        else:
            encontradas = detecta_las_columnas(fila)
            indices = {
                columna: next(
                    i for i, celda in enumerate(fila) if (celda or "").strip() == etiqueta
                )
                for columna, etiqueta in encontradas.items()
            }
        if len(encontradas) > mejor[4]:
            mejor = (numero, [c.strip() for c in fila], encontradas, indices, len(encontradas))

    numero, cabeceras, columnas, indices, cuantas = mejor
    if numero is None or cuantas < 2:
        return (None, [], {}, {})
    # Y hace falta al menos una columna de fecha y una de dinero, o lo que hay no es un extracto.
    tiene_fecha = "fecha" in columnas or "fecha_valor" in columnas
    tiene_dinero = any(c in columnas for c in ("importe", "debe", "haber"))
    if not (tiene_fecha and tiene_dinero):
        return (None, [], {}, {})
    return (numero, cabeceras, columnas, indices)


def perfil_desde_las_cabeceras(
    cabeceras: Sequence[str],
    columnas: Mapping[str, str],
    *,
    delimitador: str,
    decimal: str | None = None,
    formato_de_fecha: str | None = None,
) -> PerfilDeFormato:
    """El perfil que se deduce de un fichero, para poder enseñárselo al agricultor.

    **Lo que se deduce no es lo que se decide.** De aquí sale el nombre de cada columna (eso sí se
    puede leer del fichero), y el estilo del signo (se ve si hay columna de debe o de signo). Lo que
    **no** sale de aquí es el formato de la fecha ni qué quiere decir un número sin signo: esos dos
    los dice el agricultor, y mientras no los diga valen `None` y las filas que dependan de ellos se
    rechazan.
    """
    estilo = SIGNO_EN_EL_IMPORTE
    if "debe" in columnas or "haber" in columnas:
        estilo = SIGNO_DEBE_HABER
    elif "signo" in columnas:
        estilo = SIGNO_EN_SU_COLUMNA
    return PerfilDeFormato(
        nombre="Lo que se ha leído del fichero",
        delimitador=delimitador,
        decimal=decimal,
        formato_de_fecha=formato_de_fecha,
        estilo_del_signo=estilo,
        columnas=dict(columnas),
    )


def _la_cuenta_del_fichero(filas_de_antes: Sequence[Sequence[str]]) -> CuentaDelFichero:
    """Qué cuenta dice el fichero que es, **quedándose solo con los cuatro últimos dígitos**.

    Se busca en las líneas de arriba (donde un extracto pone de qué cuenta habla) y, si no está ahí,
    en ninguna otra parte: un IBAN que aparezca dentro de un concepto es el de la otra parte, no el
    de la casa, y tomarlo por la cuenta del extracto sería apuntar los movimientos en la cuenta
    equivocada.
    """
    banco: str | None = None
    ultimos: str | None = None
    for fila in filas_de_antes:
        for celda in fila:
            texto = (celda or "").strip()
            if not texto:
                continue
            if banco is None:
                # El nombre del banco es lo primero que escribe un extracto, y va sin el número.
                candidato = texto.strip(";:, ")
                if candidato and not _PISTA_DE_CUENTA.search(candidato) and len(candidato) <= 80:
                    banco = candidato
            if ultimos is None:
                pista = _PISTA_DE_CUENTA.search(texto)
                if pista:
                    solo_letras_y_digitos = re.sub(r"[^0-9A-Za-z]", "", pista.group(0)).upper()
                    if len(solo_letras_y_digitos) >= 15:
                        ultimos = solo_letras_y_digitos[-4:]
    return CuentaDelFichero(banco=banco, ultimos_digitos=ultimos)


def lee_extracto(
    texto: str,
    perfil: PerfilDeFormato | None = None,
    *,
    cuenta: str | None = None,
    explotacion_id: int | None = None,
) -> LecturaDelExtracto:
    """Lee un extracto y devuelve **lo que se ha podido entender, y lo que no**.

    Es la lectura previa que pide el contrato antes de importar nada: no guarda, no escribe y no
    decide nada por el agricultor. Devuelve los movimientos, las filas que no se han entendido con su
    motivo y su número de línea, los avisos (el saldo que no cuadra, los importes que no constan) y
    las columnas que se han reconocido, para que la pantalla pueda enseñar todo eso antes de que se
    apriete el botón.

    `cuenta` es el nombre con el que se guardan los movimientos (la cuenta del agricultor), y
    `explotacion_id` viaja en cada fila para que la aísle después quien la guarde: **un movimiento de
    una finca no se puede ver desde otra**, y eso empieza aquí, en el dato.
    """
    filas_crudas = _parte_en_filas(texto)
    delimitador = adivina_el_delimitador(texto.splitlines())

    numero_de_cabecera, cabeceras, columnas, indices = _busca_la_cabecera(filas_crudas, perfil)
    if numero_de_cabecera is None:
        # Sin cabeceras no se sabe qué columna es cada cosa, y adivinarlo por la posición es
        # exactamente lo que no se hace en este programa.
        rechazadas = tuple(
            FilaRechazada(
                numero_de_linea=i + 1,
                motivo=SIN_CABECERAS,
                texto=";".join(c for c in fila),
            )
            for i, fila in enumerate(filas_crudas)
            if any((c or "").strip() for c in fila)
        )
        return LecturaDelExtracto(
            movimientos=(),
            rechazadas=rechazadas,
            cuenta=CuentaDelFichero(),
            saldo_final=None,
            columnas={},
            perfil=perfil or PerfilDeFormato(delimitador=delimitador),
            avisos=(Aviso(AVISO_SIN_CABECERAS),),
            huella="",
            lineas_leidas=len(filas_crudas),
        )

    if perfil is None:
        perfil = perfil_desde_las_cabeceras(cabeceras, columnas, delimitador=delimitador)
    cuenta_del_fichero = _la_cuenta_del_fichero(filas_crudas[:numero_de_cabecera])

    movimientos: list[FilaDeExtracto] = []
    rechazadas: list[FilaRechazada] = []

    for numero, fila in enumerate(filas_crudas[numero_de_cabecera + 1 :], start=numero_de_cabecera + 2):
        # Se quitan las casillas vacías del final: muchos extractos acaban la línea con «;;».
        while fila and not (fila[-1] or "").strip():
            fila = fila[:-1]
        if not fila or not any((c or "").strip() for c in fila):
            continue
        if len(fila) > len(cabeceras):
            # Más casillas que cabeceras: un concepto con un punto y coma suelto desplaza todo lo que
            # va detrás, y leerlo daría un importe que no es el de esa línea. Se rechaza.
            rechazadas.append(
                FilaRechazada(
                    numero_de_linea=numero,
                    motivo=COLUMNAS_DE_MAS,
                    texto=";".join(fila),
                    lo_que_dice=f"{len(fila)} casillas de {len(cabeceras)}",
                )
            )
            continue

        def celda(nombre: str) -> str:
            posicion = indices.get(nombre)
            if posicion is None or posicion >= len(fila):
                return ""
            return (fila[posicion] or "").strip()

        fecha, estado_de_la_fecha = _lee_una_fecha(
            celda("fecha") or celda("fecha_valor"), formato_declarado=perfil.formato_de_fecha
        )
        if fecha is None:
            motivo = {
                VACIO: SIN_FECHA,
                ILEGIBLE: FECHA_ILEGIBLE,
                AMBIGUA: FECHA_AMBIGUA,
            }[estado_de_la_fecha]
            rechazadas.append(
                FilaRechazada(
                    numero_de_linea=numero,
                    motivo=motivo,
                    texto=";".join(fila),
                    lo_que_dice=celda("fecha") or celda("fecha_valor") or None,
                )
            )
            continue

        fecha_valor, _ = _lee_una_fecha(
            celda("fecha_valor"), formato_declarado=perfil.formato_de_fecha
        )
        importe, signo, estado_del_dinero = _lee_el_importe_y_el_signo(fila, indices, perfil)
        if estado_del_dinero in (DEBE_Y_HABER, SIGNO_DESCONOCIDO, SIN_SIGNO, IMPORTE_CERO, IMPORTE_ILEGIBLE):
            # Las cinco formas de no poder leer el dinero de una fila, cada una con su motivo. Y son
            # cinco motivos distintos y no uno porque el agricultor tiene que poder arreglarlos, y
            # cada uno se arregla de una manera: «no sé si entra o sale» se arregla diciendo el
            # formato, «trae debe y haber» mirando la línea, y «es un cero» no se arregla: esa línea
            # no es un movimiento.
            # Lo que se enseña de esa fila: el número que no se ha podido leer, para que el
            # agricultor reconozca la línea en su fichero.
            lo_que_trae = celda("importe") or celda("signo") or celda("debe") or celda("haber") or None
            rechazadas.append(
                FilaRechazada(
                    numero_de_linea=numero,
                    motivo=estado_del_dinero,
                    texto=";".join(fila),
                    lo_que_dice=lo_que_trae,
                )
            )
            continue
        if estado_del_dinero == VACIO:
            # La casilla del importe está vacía. **El movimiento se guarda** con el importe en «no lo
            # sé»: la línea del banco existe, y lo que falta es el número. Poner un cero aquí sería
            # decir que ese movimiento fue de cero euros, que es lo contrario de la verdad.
            importe, signo = None, None

        saldo, estado_del_saldo = _lee_un_numero(celda("saldo"), decimal_declarado=perfil.decimal)
        concepto = celda("concepto") or None
        referencia = celda("referencia") or None

        falta: list[str] = []
        if importe is None:
            falta.append(IMPORTE_NO_CONSTA if estado_del_dinero == VACIO else IMPORTE_ILEGIBLE_EN_LA_FILA)
        if saldo is None:
            falta.append(SALDO_NO_CONSTA if estado_del_saldo == VACIO else SALDO_ILEGIBLE)
        if referencia is None:
            falta.append(REFERENCIA_NO_CONSTA)
        if concepto is None:
            falta.append(CONCEPTO_NO_CONSTA)

        movimientos.append(
            FilaDeExtracto(
                numero_de_linea=numero,
                fecha=fecha,
                fecha_valor=fecha_valor,
                concepto=concepto,
                importe=importe,
                signo=signo,
                saldo=saldo,
                referencia=referencia,
                cuenta=cuenta,
                # La clave se deja sin el número de aparición y se completa al final, cuando ya se
                # sabe cuántas veces sale esa misma línea en el fichero.
                clave_de_duplicado=_parte_de_la_clave(
                    cuenta=cuenta,
                    fecha=fecha,
                    importe=importe,
                    signo=signo,
                    concepto=concepto,
                    saldo=saldo,
                    referencia=referencia,
                ),
                falta=tuple(falta),
                es_traspaso_propio=False,
                explotacion_id=explotacion_id,
            )
        )

    # El número de aparición de cada clave: la primera vez que sale una línea se numera 1, la segunda
    # 2, y así. Es lo que hace que un extracto con dos compras idénticas del mismo día siga teniendo
    # dos movimientos, y que subir el mismo fichero otra vez no cuele ninguno de los dos.
    apariciones: Counter[str] = Counter()
    movimientos_leidos: list[FilaDeExtracto] = []
    for fila in movimientos:
        base = fila.clave_de_duplicado
        apariciones[base] += 1
        movimientos_leidos.append(replace(fila, clave_de_duplicado=f"{base}#{apariciones[base]}"))
    movimientos = movimientos_leidos

    saldo_final = next((f.saldo for f in reversed(movimientos) if f.saldo is not None), None)
    avisos = _los_avisos_de_la_lectura(movimientos, rechazadas, perfil, cuenta_del_fichero)
    return LecturaDelExtracto(
        movimientos=tuple(movimientos),
        rechazadas=tuple(rechazadas),
        cuenta=cuenta_del_fichero,
        saldo_final=saldo_final,
        columnas=dict(columnas),
        perfil=perfil,
        avisos=avisos,
        huella="",
        lineas_leidas=len(filas_crudas),
    )


def _los_avisos_de_la_lectura(
    movimientos: Sequence[FilaDeExtracto],
    rechazadas: Sequence[FilaRechazada],
    perfil: PerfilDeFormato,
    cuenta: CuentaDelFichero,
) -> tuple[Aviso, ...]:
    """Los avisos de una lectura: lo que el agricultor tiene que saber antes de importar."""
    avisos: list[Aviso] = []
    if not cuenta.se_reconoce:
        avisos.append(Aviso(AVISO_NO_SE_SABE_LA_CUENTA))
    sin_importe = tuple(f.numero_de_linea for f in movimientos if f.importe is None)
    if sin_importe:
        avisos.append(
            Aviso(AVISO_IMPORTES_QUE_NO_CONSTAN, lineas=sin_importe, datos={"cuantos": len(sin_importe)})
        )
    if rechazadas:
        avisos.append(
            Aviso(
                AVISO_FILAS_RECHAZADAS,
                lineas=tuple(f.numero_de_linea for f in rechazadas),
                datos={"cuantas": len(rechazadas)},
            )
        )
    if perfil.formato_de_fecha is None:
        dudosas = tuple(
            f.numero_de_linea
            for f in movimientos
            if f.fecha is not None and f.fecha.day <= 12 and f.fecha.month <= 12
        )
        if dudosas:
            avisos.append(Aviso(AVISO_FORMATO_DE_FECHA_SIN_DECLARAR, lineas=dudosas))
    if perfil.estilo_del_signo == SIGNO_EN_EL_IMPORTE and perfil.sin_signo_quiere_decir is None:
        sin_signo = [f for f in rechazadas if f.motivo == SIN_SIGNO]
        if len(sin_signo) >= 2:
            avisos.append(
                Aviso(
                    AVISO_FILAS_SIN_SIGNO,
                    lineas=tuple(f.numero_de_linea for f in sin_signo),
                    datos={"cuantas": len(sin_signo)},
                )
            )
    avisos.extend(_comprueba_los_saldos(movimientos))
    return tuple(avisos)


def _comprueba_los_saldos(movimientos: Sequence[FilaDeExtracto]) -> list[Aviso]:
    """El saldo de cada línea, que es la prueba aritmética de que se ha leído bien.

    La idea es la misma que la del lector de facturas de este programa («la aritmética es la
    prueba»): si el extracto trae el saldo después de cada movimiento, entonces
    `saldo de antes + importe = saldo de ahora`, y una fila que no cuadre es una fila mal leída —un
    concepto que se ha comido una casilla, un importe de la columna de al lado—. Es lo que convierte
    una lectura en algo que se puede revisar.

    **Y se prueban los dos órdenes**, porque hay bancas que exportan del más nuevo al más viejo. Se
    cuenta en cuál de los dos cuadra más, se usa ese, y si cuadra igual de mal en los dos se dice que
    el orden es dudoso en vez de acusar a una fila concreta.
    """
    con_saldo = [
        (f.numero_de_linea, f.importe_con_signo, f.saldo)
        for f in movimientos
        if f.importe is not None and f.saldo is not None
    ]
    if len(con_saldo) < 2:
        return []

    def malas(secuencia: Sequence[tuple[int, Decimal | None, Decimal | None]]) -> list[int]:
        fallos: list[int] = []
        anterior: Decimal | None = None
        for numero, importe, saldo in secuencia:
            if anterior is not None and importe is not None and saldo is not None:
                if dinero.redondea(anterior + importe) != dinero.redondea(saldo):
                    fallos.append(numero)
            anterior = saldo
        return fallos

    de_arriba_abajo = malas(con_saldo)
    de_abajo_arriba = malas(list(reversed(con_saldo)))
    if not de_arriba_abajo or not de_abajo_arriba:
        # Hay una forma de leer el fichero en la que el saldo cuadra entero: el extracto está bien y
        # la otra forma es la que estaba al revés. No hay nada que avisar.
        return []
    if len(de_arriba_abajo) == len(de_abajo_arriba):
        # Cuadra igual de mal en los dos sentidos: no se sabe ni en qué orden vienen las filas, así
        # que acusar a una línea concreta sería inventarse cuál está mal.
        return [
            Aviso(
                AVISO_ORDEN_DUDOSO,
                lineas=tuple(f[0] for f in con_saldo),
                datos={"cuantas": len(de_arriba_abajo)},
            )
        ]
    peores = de_arriba_abajo if len(de_arriba_abajo) < len(de_abajo_arriba) else de_abajo_arriba
    if len(peores) >= len(con_saldo) - 1:
        # No cuadra casi ninguna línea: este saldo no es el que sigue a cada movimiento (algunos
        # extractos traen el saldo del día). Señalar una línea sería una acusación falsa.
        return []
    return [Aviso(AVISO_SALDO_NO_CUADRA, lineas=tuple(peores), datos={"cuantas": len(peores)})]


# ==========================================================================
# 4. Que importar dos veces no duplique nada
# ==========================================================================


def _parte_de_la_clave(
    *,
    cuenta: str | None,
    fecha: dt.date | None,
    importe: Decimal | None,
    signo: str | None,
    concepto: str | None,
    saldo: Decimal | None,
    referencia: str | None,
) -> str:
    """Lo que identifica una línea de un extracto. **Sin el número de aparición.**

    ## De dónde sale esta clave, y por qué no es un identificador inventado

    Un fichero de extracto no trae un identificador único de cada línea (bueno, algunos sí: la
    referencia del banco). Así que la clave se compone de lo que **sí** identifica un movimiento de
    verdad:

      · si el fichero trae **referencia**, esa manda: es el número con el que el banco identifica la
        operación, y es lo que hace que el mismo movimiento se reconozca aunque el banco lo exporte
        otro día con otro formato;
      · si no la trae, se usa **el día, el importe, el signo, el concepto y el saldo que queda
        después**. El saldo es lo que distingue dos compras idénticas del mismo día: si son de
        verdad dos, el saldo después de cada una es distinto.

    Y la cuenta va dentro, porque el mismo movimiento no puede estar en dos cuentas.
    """
    la_cuenta = sin_tildes_y_en_minusculas(cuenta) or "-"
    if referencia and referencia.strip():
        return f"r|{la_cuenta}|{sin_tildes_y_en_minusculas(referencia)}|{fecha.isoformat() if fecha else '-'}"
    dinero_texto = dinero.a_texto(importe) if importe is not None else "-"
    saldo_texto = dinero.a_texto(saldo) if saldo is not None else "-"
    return "h|" + "|".join(
        [
            la_cuenta,
            fecha.isoformat() if fecha else "-",
            dinero_texto,
            signo or "-",
            sin_tildes_y_en_minusculas(concepto),
            saldo_texto,
        ]
    )


def clave_de_duplicado(fila: FilaDeExtracto, *, aparicion: int = 1) -> str:
    """La clave completa de una fila, con **cuántas veces aparece esa misma línea en el fichero**.

    El número de aparición es el detalle que hace que esto funcione en los dos sentidos, y es donde
    se rompen las soluciones fáciles:

      · Si un extracto tiene **dos compras idénticas del mismo día, del mismo importe y con el mismo
        concepto**, son dos movimientos de verdad y hay que guardar los dos. Sin el contador, el
        segundo se tomaría por repetido del primero y **desaparecería un movimiento del banco**.
      · Y si el agricultor sube **el mismo fichero otra vez**, la primera coincidencia con la
        primera y la segunda con la segunda: no se cuela ninguna.

    Es la misma forma de trabajar que el «reenvío» del resto del programa (la clave de reenvío del
    móvil sin cobertura), aplicada a lo que trae un fichero en vez de a lo que manda un botón.
    """
    if aparicion < 1:
        raise ErrorDeExtracto("El número de aparición de una línea empieza en 1.")
    return f"{_parte_de_la_clave(cuenta=fila.cuenta, fecha=fila.fecha, importe=fila.importe, signo=fila.signo, concepto=fila.concepto, saldo=fila.saldo, referencia=fila.referencia)}#{aparicion}"


def separa_lo_que_ya_estaba(
    movimientos: Sequence[FilaDeExtracto], claves_guardadas: Collection[str]
) -> tuple[tuple[FilaDeExtracto, ...], tuple[FilaDeExtracto, ...]]:
    """Parte lo leído en «lo nuevo» y «lo que ya estaba», por su clave.

    Devuelve las dos listas y no solo la primera a propósito: **lo repetido se dice**. Un agricultor
    que sube dos veces el mismo extracto tiene que leer «este fichero ya estaba importado, no se ha
    añadido nada» y no quedarse con la duda de si se ha importado o no.
    """
    nuevas: list[FilaDeExtracto] = []
    repetidas: list[FilaDeExtracto] = []
    for fila in movimientos:
        (repetidas if fila.clave_de_duplicado in claves_guardadas else nuevas).append(fila)
    return (tuple(nuevas), tuple(repetidas))


# ==========================================================================
# 5. Un traspaso entre cuentas propias no es un ingreso ni un gasto (A07)
# ==========================================================================


@dataclass(frozen=True)
class Traspaso:
    """Dos movimientos que son **el mismo dinero pasando de una cuenta tuya a otra**.

    El caso **A07** del contrato, literal: «Traspaso propio 500 EUR → dos movimientos vinculados,
    cero ingreso/gasto operativo». Lo que se guarda aquí es el vínculo: sin él, los dos lados del
    traspaso se sumarían como un ingreso y un gasto, y el margen de la explotación saldría con 500 €
    de más en cada lado por haber movido dinero de sitio.
    """

    sale_de: str
    entra_en: str
    importe: Decimal
    dias_de_diferencia: int
    cuentas: tuple[str, str]

    @property
    def claves(self) -> tuple[str, str]:
        return (self.sale_de, self.entra_en)


def detectar_traspasos(
    movimientos: Sequence[FilaDeExtracto],
    *,
    cuentas_propias: Mapping[str, bool],
    dias_de_margen: int = DIAS_DE_UN_TRASPASO,
) -> tuple[Traspaso, ...]:
    """Busca parejas de movimientos que son un traspaso entre dos cuentas **de la casa**.

    Las condiciones son cuatro, y ninguna es negociable porque cada una quita una forma de confundir
    un traspaso con otra cosa:

      1. **Las dos cuentas son propias.** Un pago de 500 € a un proveedor y un cobro de 500 € de un
         cliente el mismo día **no** son un traspaso: son dos hechos distintos que casualmente
         cuadran, y atarlos convertiría un ingreso de verdad en «dinero movido de sitio».
      2. **Las dos cuentas son distintas.** Un apunte y su contrario en la misma cuenta es una
         devolución, no un traspaso.
      3. **Un lado sale y el otro entra, por el mismo importe exacto.** No «parecido»: un traspaso es
         el mismo dinero, y si lleva comisión, la comisión es **otra línea del extracto** (el
         contrato lo pide así: «las comisiones como línea aparte»). Por eso un traspaso con comisión
         no se detecta solo: se detecta el traspaso y la comisión se queda como su propio movimiento,
         que es la verdad.
      4. **Con pocos días de diferencia.** Tres por defecto, que es lo que tarda una transferencia
         entre dos entidades españolas.

    Y es **una propuesta, no un hecho**: el contrato pide que «duplicados y traspasos propios» sean
    revisables por el agricultor. Aquí se proponen las parejas; quien las da por buenas es él, desde
    la pantalla, y hasta entonces no cambian ninguna cuenta.
    """
    candidatos = [f for f in movimientos if f.se_puede_conciliar and cuentas_propias.get(f.cuenta or "", False)]
    salidas = [f for f in candidatos if f.signo == SALE]
    entradas = [f for f in candidatos if f.signo == ENTRA]

    parejas: list[tuple[int, FilaDeExtracto, FilaDeExtracto]] = []
    for sale in salidas:
        for entra in entradas:
            if (sale.cuenta or "") == (entra.cuenta or ""):
                continue
            if sale.importe != entra.importe:
                continue
            if sale.fecha is None or entra.fecha is None:
                continue
            dias = abs((entra.fecha - sale.fecha).days)
            if dias > dias_de_margen:
                continue
            parejas.append((dias, sale, entra))

    # La pareja que menos días se lleva va primero, y a igualdad de días, la que se lee antes en el
    # fichero: así el resultado es siempre el mismo para el mismo fichero, y una prueba puede
    # fijarlo.
    parejas.sort(key=lambda p: (p[0], p[1].clave_de_duplicado, p[2].clave_de_duplicado))
    usados: set[str] = set()
    traspasos: list[Traspaso] = []
    for dias, sale, entra in parejas:
        if sale.clave_de_duplicado in usados or entra.clave_de_duplicado in usados:
            continue
        usados.update({sale.clave_de_duplicado, entra.clave_de_duplicado})
        traspasos.append(
            Traspaso(
                sale_de=sale.clave_de_duplicado,
                entra_en=entra.clave_de_duplicado,
                importe=sale.importe or dinero.CERO,
                dias_de_diferencia=dias,
                cuentas=(sale.cuenta or "", entra.cuenta or ""),
            )
        )
    return tuple(traspasos)


def marca_los_traspasos(
    movimientos: Sequence[FilaDeExtracto], traspasos: Sequence[Traspaso]
) -> tuple[FilaDeExtracto, ...]:
    """Devuelve los movimientos con las dos patas de cada traspaso ya marcadas.

    Es un paso aparte de `detectar_traspasos` porque detectar y decidir son dos cosas: lo detectado
    se enseña para que el agricultor lo revise, y lo marcado es lo que se guarda cuando él dice que
    sí.
    """
    marcadas = {clave for traspaso in traspasos for clave in traspaso.claves}
    return tuple(
        replace(fila, es_traspaso_propio=True)
        if fila.clave_de_duplicado in marcadas
        else fila
        for fila in movimientos
    )


@dataclass(frozen=True)
class ResumenDeLoQueHaEntradoYSalido:
    """Lo que de verdad ha entrado y salido, sin contar el dinero que solo ha cambiado de sitio.

    Los tres números que hacen falta para que un resumen no mienta:

      · `entradas` y `salidas` **excluyen las dos patas de un traspaso propio**: mover dinero de una
        cuenta a otra no es ni un ingreso ni un gasto (A07).
      · `traspasos` e `importe_de_traspasos` dicen cuánto dinero se ha movido de sitio, y se enseña
        aparte para que el agricultor vea que la cuenta cuadra.
      · `sin_importe` cuenta los movimientos cuyo importe **no consta**. No son cero y no se suman:
        se cuentan, que es la única forma de que un total no mienta. Un total que se calla que le
        faltan datos es un total que engaña.
    """

    entradas: Decimal
    salidas: Decimal
    traspasos: int
    importe_de_traspasos: Decimal
    sin_importe: int

    @property
    def movimiento_neto(self) -> Decimal:
        return dinero.redondea(self.entradas - self.salidas)


def resumen_de_lo_que_ha_entrado_y_salido(
    movimientos: Sequence[FilaDeExtracto], traspasos: Sequence[Traspaso] = ()
) -> ResumenDeLoQueHaEntradoYSalido:
    """Suma lo que entra y lo que sale, dejando fuera lo que no es ni una cosa ni la otra.

    Se excluyen las dos patas de un traspaso **por la marca de la fila y por la lista de traspasos**:
    la marca es lo que se guarda, y la lista es lo que se acaba de proponer. Aceptar las dos cosas es
    a propósito: quien llame con la lista y sin marcar tiene que obtener la misma cuenta, porque el
    fallo que esto evita (un traspaso contado como ingreso) es justo el que no se puede colar por un
    descuido de quien llama.
    """
    fuera = {clave for traspaso in traspasos for clave in traspaso.claves}
    fuera.update(f.clave_de_duplicado for f in movimientos if f.es_traspaso_propio)

    entradas = dinero.CERO
    salidas = dinero.CERO
    importe_de_traspasos = dinero.CERO
    cuantos_traspasos = 0
    sin_importe = 0
    for fila in movimientos:
        if fila.clave_de_duplicado in fuera:
            if fila.importe is not None:
                importe_de_traspasos = dinero.suma(importe_de_traspasos, fila.importe)
                # Se cuentan las patas de traspaso que entran (una por pareja), no las dos.
                if fila.signo == SALE:
                    cuantos_traspasos += 1
            continue
        if fila.importe is None:
            sin_importe += 1
            continue
        if fila.signo == ENTRA:
            entradas = dinero.suma(entradas, fila.importe)
        else:
            salidas = dinero.suma(salidas, fila.importe)
    return ResumenDeLoQueHaEntradoYSalido(
        entradas=dinero.redondea(entradas) or dinero.CERO,
        salidas=dinero.redondea(salidas) or dinero.CERO,
        traspasos=cuantos_traspasos,
        importe_de_traspasos=dinero.redondea(importe_de_traspasos) or dinero.CERO,
        sin_importe=sin_importe,
    )


# ==========================================================================
# 6. La conciliación: muchos a muchos, y reversible
# ==========================================================================


@dataclass(frozen=True)
class DocumentoPorConciliar:
    """Un papel al que se le puede aplicar dinero: una factura, un cobro.

    `pendiente` es **lo que le falta**, y puede ser `None` («no se sabe cuánto le falta»). Un
    documento cuyo pendiente no se sabe **no entra en ninguna propuesta**: proponerle un pago
    obligaría a suponer que le falta todo, y eso es exactamente lo que este programa no hace con el
    dinero.
    """

    clase: str
    documento_id: int
    contraparte: str | None = None
    concepto: str | None = None
    referencia: str | None = None
    fecha: dt.date | None = None
    vencimiento: dt.date | None = None
    importe: Decimal | None = None
    pendiente: Decimal | None = None
    explotacion_id: int | None = None

    def __post_init__(self) -> None:
        if self.clase not in (*CLASES_DE_DOCUMENTO, *CLASES_QUE_FALTAN):
            raise ErrorDeExtracto(f"«{self.clase}» no es una clase de documento que se conozca.")

    @property
    def etiqueta(self) -> str:
        """Cómo se identifica este documento en la pantalla y en el rastro."""
        return f"{self.clase}:{self.documento_id}"

    @property
    def se_puede_conciliar(self) -> bool:
        return self.pendiente is not None and self.pendiente > 0

    @property
    def es_de_dinero_que_entra(self) -> bool:
        """Si este documento se paga con dinero que **entra**: lo que nos deben.

        Un cobro y una factura nuestra son dinero que entra. Una factura de compra es dinero que sale.
        Tenerlo escrito aquí es lo que impide proponer que un pago de 300 € salde una factura que nos
        deben.
        """
        return self.clase in (COBRO, FACTURA_EMITIDA)


@dataclass(frozen=True)
class LineaDeImputacion:
    """Cuánto de un movimiento va contra un documento. **Es un vínculo, no un pago nuevo.**"""

    documento: DocumentoPorConciliar
    importe: Decimal


@dataclass(frozen=True)
class PropuestaDeConciliacion:
    """Una manera de cuadrar un movimiento con uno o varios papeles, con el porqué.

    `porque` es lo que hace que la propuesta se pueda revisar: el agricultor ve «te lo propongo
    porque el importe cuadra y la referencia está en el concepto», no un número que sale de ninguna
    parte. Y `sobrante` dice si con esto queda dinero sin colocar, que es lo que pasa cuando entra
    más de lo que se debía.
    """

    movimiento: str
    lineas: tuple[LineaDeImputacion, ...]
    tipo: str
    porque: tuple[str, ...]
    puntuacion: int
    sobrante: Decimal

    @property
    def total(self) -> Decimal:
        return dinero.suma(*(linea.importe for linea in self.lineas))

    @property
    def documentos(self) -> tuple[str, ...]:
        return tuple(linea.documento.etiqueta for linea in self.lineas)


def _centimos(valor: Decimal) -> int:
    """Un importe en céntimos enteros, para poder buscar combinaciones exactas sin céntimos sueltos."""
    redondeado = dinero.redondea(valor) or dinero.CERO
    return int(redondeado * 100)


def _fechas_cerca(una: dt.date | None, otra: dt.date | None) -> int | None:
    """Cuántos días hay entre dos fechas, o `None` si falta alguna."""
    if una is None or otra is None:
        return None
    return abs((una - otra).days)


def _el_nombre_esta_en_el_concepto(contraparte: str | None, concepto: str | None) -> bool:
    """Si el nombre de la otra parte aparece dentro del concepto del movimiento.

    Se buscan las palabras de más de tres letras, y no el nombre entero: en un extracto el concepto
    viene recortado («TRANSF. COOP. EJEMPLO») y exigir el nombre completo no encontraría nada. Tres
    letras como mínimo porque «de», «la» y «sur» están dentro de cualquier palabra y propondrían
    cualquier cosa.
    """
    plano = sin_tildes_y_en_minusculas(concepto)
    if not plano or not contraparte:
        return False
    for palabra in sin_tildes_y_en_minusculas(contraparte).split():
        if len(palabra) >= 4 and palabra in plano:
            return True
    return False


def por_que_no_se_puede_conciliar(movimiento: FilaDeExtracto) -> str | None:
    """Por qué este movimiento no se puede conciliar con nada, si es que no se puede.

    Existe para que la pantalla pueda decirlo en vez de enseñar una lista vacía: una lista vacía se
    lee como «no hay nada que cuadrar», y puede querer decir «este movimiento no tiene importe» o
    «esto es un traspaso tuyo».
    """
    if movimiento.es_traspaso_propio:
        return NO_PORQUE_ES_UN_TRASPASO
    if movimiento.importe is None or movimiento.signo not in SIGNOS:
        return NO_PORQUE_NO_CONSTA_EL_IMPORTE
    if movimiento.importe <= 0:
        return NO_PORQUE_NO_CONSTA_EL_IMPORTE
    return None


def proponer_conciliaciones(
    movimiento: FilaDeExtracto,
    pendientes: Sequence[DocumentoPorConciliar],
    *,
    dias_de_margen: int = DIAS_ENTRE_EL_MOVIMIENTO_Y_EL_PAPEL,
    maximo_documentos: int = MAXIMO_DOCUMENTOS_EN_UNA_AGRUPADA,
    maximo_propuestas: int = MAXIMO_DE_PROPUESTAS,
) -> tuple[PropuestaDeConciliacion, ...]:
    """Qué papeles podrían cuadrar con este movimiento. **Es una propuesta, no una decisión.**

    ## Los tres casos que el contrato pide, y cómo se distinguen

      · **Exacta**: un documento al que le falta exactamente lo que dice el movimiento.
      · **Agrupada**: un solo ingreso que salda varios papeles (el banco paga tres facturas de una
        vez), y la suma de lo que les falta cuadra **exacta** con el movimiento.
      · **Parcial**: el movimiento lleva menos que lo que le falta al papel, así que lo salda a
        medias. Es el pago parcial de siempre, y es la mitad del A06.

    ## Lo que NO se propone, y se dice

    - **Una suma que no cuadra.** Si tres papeles suman 480 € y el movimiento es de 500 €, no se
      propone: los 20 € que faltan serían un invento, y el contrato pide que una cuenta cuadre.
    - **Un papel cuyo pendiente no se sabe.** No se sabe cuánto le falta, así que no se puede decir
      qué parte del movimiento le toca.
    - **Un papel de la otra finca.** Se comprueba el `explotacion_id` aquí también, además de en la
      consulta: una propuesta que cruce dos fincas es una filtración de datos, y se comprueba en los
      dos sitios a propósito.
    - **Un movimiento que entra contra una factura que se debe pagar.** El lado del dinero tiene que
      ser el mismo: lo que entra salda lo que nos deben, y lo que sale paga lo que debemos.
    """
    if por_que_no_se_puede_conciliar(movimiento) is not None:
        return ()
    if movimiento.importe is None or movimiento.fecha is None:
        return ()

    importe = dinero.redondea(movimiento.importe) or dinero.CERO
    quiere_entrar = movimiento.signo == ENTRA

    candidatos = [
        documento
        for documento in pendientes
        if documento.se_puede_conciliar
        and documento.es_de_dinero_que_entra == quiere_entrar
        and (
            movimiento.explotacion_id is None
            or documento.explotacion_id is None
            or documento.explotacion_id == movimiento.explotacion_id
        )
    ]

    propuestas: list[PropuestaDeConciliacion] = []

    def porque_de(documentos: Sequence[DocumentoPorConciliar]) -> tuple[tuple[str, ...], int]:
        motivos: list[str] = []
        puntos = 0
        texto_del_movimiento = sin_tildes_y_en_minusculas(
            f"{movimiento.concepto or ''} {movimiento.referencia or ''}"
        )
        for documento in documentos:
            referencia = sin_tildes_y_en_minusculas(documento.referencia)
            if referencia and len(referencia) >= 3 and referencia in texto_del_movimiento:
                motivos.append(PORQUE_LA_REFERENCIA_ESTA_EN_EL_CONCEPTO)
                puntos += 50
            if _el_nombre_esta_en_el_concepto(documento.contraparte, movimiento.concepto):
                motivos.append(PORQUE_EL_NOMBRE_ESTA_EN_EL_CONCEPTO)
                puntos += 20
            dias = _fechas_cerca(documento.fecha or documento.vencimiento, movimiento.fecha)
            if dias is not None:
                if dias <= 15:
                    motivos.append(PORQUE_LA_FECHA_ESTA_CERCA)
                    puntos += 10
                elif dias <= dias_de_margen:
                    motivos.append(PORQUE_LA_FECHA_ESTA_LEJOS)
                    puntos += 3
        return (tuple(dict.fromkeys(motivos)), puntos)

    for documento in candidatos:
        pendiente = dinero.redondea(documento.pendiente) or dinero.CERO
        if pendiente > importe:
            motivos, puntos = porque_de([documento])
            propuestas.append(
                PropuestaDeConciliacion(
                    movimiento=movimiento.clave_de_duplicado,
                    lineas=(LineaDeImputacion(documento=documento, importe=importe),),
                    tipo=PROPUESTA_PARCIAL,
                    porque=motivos,
                    puntuacion=puntos + 10,
                    sobrante=dinero.CERO,
                )
            )
        elif pendiente == importe:
            motivos, puntos = porque_de([documento])
            propuestas.append(
                PropuestaDeConciliacion(
                    movimiento=movimiento.clave_de_duplicado,
                    lineas=(LineaDeImputacion(documento=documento, importe=importe),),
                    tipo=PROPUESTA_EXACTA,
                    porque=tuple(dict.fromkeys((*motivos, PORQUE_EL_IMPORTE_CUADRA))),
                    puntuacion=puntos + 30,
                    sobrante=dinero.CERO,
                )
            )

    # Las agrupadas: solo con los papeles que caben dentro del movimiento, y solo sumas exactas.
    menudos = [d for d in candidatos if (dinero.redondea(d.pendiente) or dinero.CERO) < importe]
    # Con más de doce candidatos, el número de combinaciones deja de ser algo que se pueda mirar.
    menudos = sorted(menudos, key=lambda d: (d.fecha or dt.date(1900, 1, 1), d.documento_id))[:12]
    buscado = _centimos(importe)
    for cuantos in range(2, maximo_documentos + 1):
        for grupo in combinations(menudos, cuantos):
            if sum(_centimos(d.pendiente) for d in grupo if d.pendiente is not None) != buscado:
                continue
            motivos, puntos = porque_de(grupo)
            propuestas.append(
                PropuestaDeConciliacion(
                    movimiento=movimiento.clave_de_duplicado,
                    lineas=tuple(
                        LineaDeImputacion(documento=d, importe=dinero.redondea(d.pendiente) or dinero.CERO)
                        for d in grupo
                    ),
                    tipo=PROPUESTA_AGRUPADA,
                    porque=tuple(dict.fromkeys((*motivos, PORQUE_LA_SUMA_CUADRA))),
                    puntuacion=puntos + 40 + cuantos,
                    sobrante=dinero.CERO,
                )
            )

    # Se ordena por lo que mejor cuadra, y a igualdad, la que menos papeles toca: entre dos
    # propuestas iguales de buenas, la más simple es la que el agricultor puede revisar de un vistazo.
    propuestas.sort(key=lambda p: (-p.puntuacion, len(p.lineas), p.documentos))
    return tuple(propuestas[:maximo_propuestas])


@dataclass(frozen=True)
class RevisionDeUnaConciliacion:
    """El resultado de revisar lo que el agricultor quiere imputar. Con sus problemas, si los hay."""

    lineas: tuple[LineaDeImputacion, ...]
    problemas: tuple[str, ...]
    total: Decimal
    sobrante: Decimal

    @property
    def se_puede_guardar(self) -> bool:
        return not self.problemas and bool(self.lineas)


def revisa_una_conciliacion(
    *,
    movimiento: FilaDeExtracto,
    imputaciones: Sequence[tuple[DocumentoPorConciliar, Decimal | None]],
) -> RevisionDeUnaConciliacion:
    """Comprueba que el reparto que se quiere guardar tiene sentido. **No guarda nada.**

    Las reglas, una por una, y cada una existe porque su contraria sería un dato falso:

      · **Un movimiento sin importe no puede conciliar nada.** No es que sea cero: es que no se sabe
        cuánto, así que no hay nada que repartir.
      · **No se imputa más de lo que le falta al papel.** Si a una factura le faltan 81 € y se le
        imputan 100, la factura quedaría con un saldo a favor de 19 € que nadie ha acordado.
      · **No se imputa más de lo que dice el movimiento.** Con 500 € de ingreso no se pueden saldar
        700 € de facturas: los 200 que faltan no han llegado.
      · **Un mismo papel, una vez.** El mismo documento dos veces en la misma conciliación sería
        contar el mismo dinero dos veces sobre el mismo papel.
      · **El lado del dinero.** Un ingreso salda lo que nos deben; un pago, lo que debemos.
      · **La finca.** Un movimiento de una finca no toca papeles de otra.
      · **El pendiente tiene que saberse.** Un papel cuyo pendiente no se sabe se queda fuera hasta
        que se sepa: suponer que le falta todo es inventarse un número.
    """
    problemas: list[str] = []
    lineas: list[LineaDeImputacion] = []

    if movimiento.importe is None or movimiento.signo not in SIGNOS:
        return RevisionDeUnaConciliacion(
            lineas=(),
            problemas=(PROBLEMA_NO_CONSTA_EL_IMPORTE,),
            total=dinero.CERO,
            sobrante=dinero.CERO,
        )

    disponible = dinero.redondea(movimiento.importe) or dinero.CERO
    vistos: set[str] = set()
    for documento, importe in imputaciones:
        cuanto = dinero.a_decimal(importe)
        if cuanto is None or cuanto <= 0:
            problemas.append(PROBLEMA_IMPORTE_NO_VALE)
            continue
        cuanto = dinero.redondea(cuanto) or dinero.CERO
        if documento.etiqueta in vistos:
            problemas.append(PROBLEMA_DOCUMENTO_REPETIDO)
            continue
        vistos.add(documento.etiqueta)
        if documento.pendiente is None:
            problemas.append(PROBLEMA_DOCUMENTO_SIN_PENDIENTE)
            continue
        if (
            movimiento.explotacion_id is not None
            and documento.explotacion_id is not None
            and documento.explotacion_id != movimiento.explotacion_id
        ):
            problemas.append(PROBLEMA_DE_OTRA_FINCA)
            continue
        if documento.es_de_dinero_que_entra != (movimiento.signo == ENTRA):
            problemas.append(PROBLEMA_CLASE_EQUIVOCADA)
            continue
        if cuanto > (dinero.redondea(documento.pendiente) or dinero.CERO):
            problemas.append(PROBLEMA_MAS_QUE_EL_PENDIENTE)
            continue
        if cuanto > disponible:
            problemas.append(PROBLEMA_MAS_QUE_EL_MOVIMIENTO)
            continue
        disponible = dinero.redondea(disponible - cuanto) or dinero.CERO
        lineas.append(LineaDeImputacion(documento=documento, importe=cuanto))

    total = dinero.suma(*(linea.importe for linea in lineas))
    return RevisionDeUnaConciliacion(
        lineas=tuple(lineas),
        # Los problemas se dicen una vez cada uno y en el orden en que se han encontrado: repetir
        # «se imputa más de lo que le falta» tres veces no añade nada a lo que hay que arreglar.
        problemas=tuple(dict.fromkeys(problemas)),
        total=dinero.redondea(total) or dinero.CERO,
        sobrante=dinero.redondea((movimiento.importe or dinero.CERO) - total) or dinero.CERO,
    )


def reparte_lo_que_queda(
    *,
    importe: Decimal | None,
    pendientes: Sequence[DocumentoPorConciliar],
) -> tuple[LineaDeImputacion, ...]:
    """Reparte un importe entre los papeles elegidos, **por orden y hasta agotarlo**.

    Es la cuenta de un pago parcial o agrupado hecha de una vez: se va llenando cada papel hasta
    completar lo que le falta y se sigue con el siguiente, y lo que sobra se queda sin colocar (no se
    reparte a ojo entre todos, que es donde aparecerían los céntimos perdidos). Se usa cuando el
    agricultor dice «este ingreso paga estos tres papeles» sin decir cuánto a cada uno.
    """
    cuanto_queda = dinero.a_decimal(importe)
    if cuanto_queda is None or cuanto_queda <= 0:
        return ()
    cuanto_queda = dinero.redondea(cuanto_queda) or dinero.CERO

    lineas: list[LineaDeImputacion] = []
    for documento in pendientes:
        if cuanto_queda <= 0:
            break
        if documento.pendiente is None:
            # Un papel cuyo pendiente no se sabe no se toca: no se puede decidir cuánto le toca.
            continue
        falta = dinero.redondea(documento.pendiente) or dinero.CERO
        if falta <= 0:
            continue
        puesto = falta if falta <= cuanto_queda else cuanto_queda
        lineas.append(LineaDeImputacion(documento=documento, importe=dinero.redondea(puesto) or dinero.CERO))
        cuanto_queda = dinero.redondea(cuanto_queda - puesto) or dinero.CERO
    return tuple(lineas)


@dataclass(frozen=True)
class Devolucion:
    """Lo que un documento recupera cuando se deshace la conciliación."""

    documento: DocumentoPorConciliar
    importe: Decimal


def deshace_una_conciliacion(
    imputaciones: Sequence[LineaDeImputacion],
) -> tuple[Devolucion, ...]:
    """Lo que hay que devolverle a cada papel al deshacer. **Y el movimiento no se toca.**

    Esta función existe para que la regla del contrato («Deshacer conciliación **no borra** el
    movimiento original») sea algo que se pueda probar sin base de datos: lo único que sale de aquí
    son los importes que vuelven a quedar pendientes en cada documento, y **no sale nada del
    movimiento** —ni un movimiento nuevo, ni una anulación—. Lo que hace el router al deshacer es
    marcar los vínculos como deshechos, con quién, cuándo y por qué, y el movimiento del banco se
    queda exactamente como estaba, porque el banco ya movió ese dinero y eso no se puede deshacer.

    El caso que hay que poder contar: se concilió un pago de 40 € contra una factura de 121 €, y al
    deshacer, la factura vuelve a deber **81 €** (que es lo que debía antes), no 121: el pago sigue
    existiendo.
    """
    devoluciones: list[Devolucion] = []
    for linea in imputaciones:
        if linea.importe <= 0:
            continue
        devoluciones.append(Devolucion(documento=linea.documento, importe=dinero.redondea(linea.importe) or dinero.CERO))
    return tuple(devoluciones)


def estado_de_conciliacion(importe: Decimal | None, imputado: Decimal | None) -> str:
    """Cómo está un movimiento: sin conciliar, a medias, conciliado… o no se puede conciliar.

    **Un importe que no consta no es «sin conciliar»**: es que con ese movimiento no se puede hacer
    nada hasta saber cuánto es. Y un movimiento conciliado **por más de lo que dice** (dos papeles que
    suman más que el movimiento) no puede pasar de aquí: lo impide `revisa_una_conciliacion`.
    """
    if importe is None:
        return NO_SE_PUEDE_CONCILIAR
    vivo = dinero.a_decimal(imputado) or dinero.CERO
    if vivo <= 0:
        return SIN_CONCILIAR
    if (dinero.redondea(vivo) or dinero.CERO) >= (dinero.redondea(importe) or dinero.CERO):
        return CONCILIADO
    return CONCILIADO_EN_PARTE


def lo_que_falta_por_conciliar(importe: Decimal | None, imputado: Decimal | None) -> Decimal | None:
    """Lo que del movimiento queda sin colocar. `None` si no consta el importe; **nunca negativo**."""
    if importe is None:
        return None
    resto = dinero.redondea((dinero.a_decimal(importe) or dinero.CERO) - (dinero.a_decimal(imputado) or dinero.CERO))
    if resto is None:
        return None
    return resto if resto > 0 else dinero.CERO


# ==========================================================================
# 7. La exportación: lo que no consta sale **en blanco**, nunca en cero
# ==========================================================================

# Los rótulos del CSV. Van aquí y no en `textos.py` porque son los nombres de las columnas de un
# fichero, y el programa ya tiene esta costumbre con la exportación del cuaderno
# (`routers/cuaderno.py`, `CABECERAS_*`): lo que se sirve en un CSV no es una frase de pantalla.
CABECERAS_DEL_EXTRACTO = (
    "Día",
    "Cuenta",
    "Concepto",
    "Entra o sale",
    "Importe",
    "Saldo",
    "Referencia",
    "Estado",
    "Lo que no consta",
)

QUE_NO_CONSTA = {
    IMPORTE_NO_CONSTA: "no consta el importe",
    IMPORTE_ILEGIBLE_EN_LA_FILA: "el importe no se ha podido leer",
    SALDO_NO_CONSTA: "no consta el saldo",
    SALDO_ILEGIBLE: "el saldo no se ha podido leer",
    REFERENCIA_NO_CONSTA: "no consta la referencia",
    CONCEPTO_NO_CONSTA: "no consta el concepto",
}

ESTADO_EN_PALABRAS = {
    SIN_CONCILIAR: "sin conciliar",
    CONCILIADO_EN_PARTE: "conciliado a medias",
    CONCILIADO: "conciliado",
    NO_SE_PUEDE_CONCILIAR: "sin importe: no se puede conciliar",
}


def _numero_para_un_fichero(valor: Decimal | None, *, decimal: str = ",") -> str:
    """Un número para un CSV: con su coma decimal y **vacío si no se sabe**.

    Copia la decisión del cuaderno exportado (`_numero_o_vacio`): un dato que no consta sale en
    blanco y nunca como un cero de relleno, porque el cero es un dato y significa otra cosa. La
    diferencia con el cuaderno es que aquí no se pone el separador de miles: un CSV que se abre en
    una hoja de cálculo tiene que poder sumar la columna, y `1.205,40` con el punto dentro deja de ser
    un número para cualquier programa que no sea español.
    """
    if valor is None:
        return ""
    texto = f"{dinero.redondea(valor):f}"
    return texto.replace(".", decimal) if decimal != "." else texto


def a_csv(
    movimientos: Iterable[FilaDeExtracto],
    *,
    conciliado: Mapping[str, Decimal] | None = None,
    delimitador: str = ";",
    decimal: str = ",",
) -> str:
    """El extracto en un CSV, con el estado de cada movimiento. **Sin ceros de relleno.**

    `conciliado` es lo que ya se ha imputado de cada movimiento, por su clave de duplicado. Un
    movimiento cuyo importe no consta sale con la casilla del importe **en blanco** y con la última
    columna diciendo qué es lo que falta: es la mitad de la regla del ticket («un importe que no
    consta NO es cero, de punta a punta») y la razón de que esta función esté en el módulo puro: se
    puede probar hoy, sin base de datos y sin servidor.
    """
    conciliado = conciliado or {}
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=delimitador, lineterminator="\n")
    escritor.writerow(CABECERAS_DEL_EXTRACTO)
    for fila in movimientos:
        estado = estado_de_conciliacion(fila.importe, conciliado.get(fila.clave_de_duplicado))
        escritor.writerow(
            [
                fila.fecha.strftime("%d/%m/%Y") if fila.fecha else "",
                fila.cuenta or "",
                fila.concepto or "",
                {"entra": "Entra", "sale": "Sale"}.get(fila.signo or "", ""),
                _numero_para_un_fichero(fila.importe, decimal=decimal),
                _numero_para_un_fichero(fila.saldo, decimal=decimal),
                fila.referencia or "",
                ESTADO_EN_PALABRAS[estado],
                ", ".join(QUE_NO_CONSTA[clave] for clave in fila.falta if clave in QUE_NO_CONSTA),
            ]
        )
    return salida.getvalue()
