"""Las cuentas de la explotación: el gasto, la inversión, el reparto y el coste de las averías.

## Por qué existe este fichero (T13, E7)

Hasta este ticket el programa sabía lo que **entra** (T12: la entrega, la factura nuestra y el
cobro) y no sabía nada de lo que **sale**. Un cuaderno de campo que solo cuenta los ingresos no
sirve para decidir nada: la pregunta del agricultor es «¿me ha costado más de lo que he sacado?», y
esa cuenta no existía.

## Lo primero que hay que entender: cinco registros que NO son lo mismo

El encargo lo exige con estas palabras: «**Gasto, inversión, factura, pago y movimiento bancario son
registros distintos.** No los mezcles en una tabla ni en un nombre». Aquí eso no es un comentario: es
la estructura del módulo y tiene sus pruebas.

  · **El gasto** es lo que se ha consumido: el gasóleo, el abono, la reparación. Es un coste de la
    campaña y **es lo único que entra en el margen**.
  · **La inversión** (el activo) es lo que se compra para durar: el tractor, la sembradora, la nave.
    Una inversión **no es un gasto completo del cultivo** —lo dice el contrato en S13—: el tractor
    trabaja tres campañas, y meterlo entero en el margen del año en que se compró diría que ese año
    se perdió dinero y que los siguientes fueron gratis. Lo que de una inversión se lleva a cada
    campaña **lo decide el agricultor** con un reparto (y si no lo decide, esa parte se queda
    **sin asignar** y se dice, que es la regla del ticket).
  · **La factura** es el papel: lo que dice el proveedor. Una factura puede traer tres cosas
    distintas (un gasto, una inversión y una fianza) y una compra puede no tener factura (un ticket
    de gasóleo, una reparación pagada en efectivo). Por eso el gasto apunta a la factura y **no al
    revés**: la factura es el justificante, no el coste.
  · **El pago** es el dinero que sale, y puede ser parcial (121 facturados, 40 pagados) y agrupado
    (un pago que salda tres facturas). **Conciliar un pago con un gasto no crea un gasto**: solo dice
    contra qué iba ese dinero, que es exactamente la mitad del caso A06 aplicada a las salidas.
  · **El movimiento bancario** es lo que pone el extracto del banco, y **no se construye aquí**: es
    el ticket T20. Lo único que este módulo hace con él es **saber que es otra cosa** y no confundir
    un apunte del agricultor con una línea del extracto.

## Y lo segundo: un importe que no consta NO es cero

Es la regla de la casa entera y aquí tiene cuatro consecuencias que se ven en el código y en las
pruebas:

  1. **`None` viaja de punta a punta** (formulario → API → modelo → cálculo → pantalla → exportación).
     El total de un gasto que no se sabe es `None`, no `0.00`, y `dinero.formatea` lo enseña en
     blanco.
  2. **Un total que calla que le faltan datos miente**, así que todas las cuentas de este módulo
     dicen **cuántos importes no se saben** (`CosteDeUnConcepto.costes_que_no_se`).
  3. **Un margen con un coste que no se sabe se enseña incompleto y diciéndolo** (`margen` es `None`),
     nunca con un cero que parezca que el año salió bien.
  4. **Un reparto que no se puede hacer bien no se hace a medias**: si falta el peso de una de las
     tierras, **no se reparte por lo que sí se sabe** —eso sería inventarle a una tierra un coste que
     no le toca— y el gasto entero se queda **sin asignar**, diciéndolo.

## Lo que este módulo NO hace

  · **No toca la base de datos ni el servidor.** Son cuentas puras con pruebas propias, como
    `legal.py` y `ventas.py`, para poder comprobarlas con números que fallarían si el dinero fuera
    de coma flotante.
  · **No inventa ninguna amortización.** No hay en el programa ninguna tabla oficial de años de vida
    útil por tipo de bien, y el proyecto tiene escrito lo que se hace cuando falta una fuente: se
    declara. Por eso la parte de una inversión que va a cada campaña **la dice el agricultor**, y
    mientras no la diga se queda sin asignar.
  · **No calcula ningún plazo de pago.** Una fecha de vencimiento es la que trae el papel; el módulo
    solo compara con hoy para decir «vencido».
  · **No escribe ni una frase para el agricultor.** Los estados y los motivos se devuelven como
    códigos y las palabras las pone `textos.py`, como todo lo que lee el agricultor.
"""

from __future__ import annotations

import datetime as dt
import decimal
from dataclasses import dataclass, field
from decimal import Decimal

from . import dinero

# --------------------------------------------------------------------------
# 1. Los cinco registros, y lo que aporta cada uno al margen
# --------------------------------------------------------------------------

# **Las cinco palabras, escritas una vez y no sacadas de las claves de un diccionario.** Un botón
# que cambia de sitio se pulsa mal, y estas cinco se parecen lo suficiente como para confundirlas:
# el ticket existe justo porque mezclarlas es el fallo que hay que impedir.
GASTO = "gasto"
INVERSION = "inversion"
FACTURA = "factura"
PAGO = "pago"
MOVIMIENTO_BANCARIO = "movimiento_bancario"

REGISTROS_DE_DINERO: tuple[str, ...] = (GASTO, INVERSION, FACTURA, PAGO, MOVIMIENTO_BANCARIO)

# Qué aporta cada uno **al coste de la campaña**. Es la tabla que gobierna la mitad de este módulo y
# por eso se escribe, en vez de dejar que cada consulta decida lo suyo:
#
#   · el **gasto** aporta lo que costó, entero;
#   · la **inversión** aporta **solo la parte que el agricultor le haya repartido a la campaña** (y
#     mientras no la reparta, nada: se queda sin asignar y se dice);
#   · la **factura** no aporta nada por sí sola: es el papel. Si aportara, cada compra contaría dos
#     veces (una por la factura y otra por el gasto);
#   · el **pago** no aporta nada al coste: el coste existe desde que se consume, se haya pagado o no.
#     Lo que hace el pago es cambiar el pendiente, que es otra cuenta;
#   · el **movimiento bancario** no aporta nada: es el extracto, y un traspaso entre cuentas propias
#     no es ni ingreso ni gasto (caso A07).
APORTA_AL_COSTE: dict[str, bool] = {
    GASTO: True,
    INVERSION: False,  # solo lo repartido, que se suma aparte
    FACTURA: False,
    PAGO: False,
    MOVIMIENTO_BANCARIO: False,
}


def es_un_gasto_completo_del_cultivo(clase: str) -> bool:
    """¿Lo que se ha comprado entra entero en el coste de esta campaña?

    Es la regla del contrato en S13, en una línea: «Compra de activo no equivale automáticamente a
    gasto completo del cultivo». El tractor, la sembradora y la nave son **inversiones**, y de una
    inversión solo entra en la campaña la parte que el agricultor le asigne.
    """
    return clase == GASTO


# --------------------------------------------------------------------------
# 1-bis. Las categorías: **son nuestras, y se dice**
# --------------------------------------------------------------------------
#
# No hay ningún catálogo oficial de categorías de gasto agrario cargado en el programa, así que esta
# lista es la que usa un agricultor cuando separa sus papeles en montones. Se ofrece **para no
# teclear y para poder agrupar**, no para obligar: lo que no encaje se apunta en «otro» y su concepto
# dice lo que es. Y el día que haya un catálogo oficial (o el plan contable que use su asesor), se
# cambia aquí y no en la pantalla.
#
# **Lo que no se hace con esta lista: deducir nada.** Que un gasto sea de «reparacion» no dice de qué
# máquina es, ni a qué tierra va, ni si es una inversión. Eso se pregunta, uno por uno.
CATEGORIAS_DE_GASTO: tuple[str, ...] = (
    "abono",
    "fitosanitario",
    "semilla",
    "gasoleo",
    "reparacion",
    "servicio",
    "alquiler",
    "seguro",
    "impuesto",
    "cuota",
    "otro",
)

CATEGORIAS_DE_INVERSION: tuple[str, ...] = (
    "maquinaria",
    "apero",
    "instalacion",
    "vehiculo",
    "terreno",
    "otro",
)


# --------------------------------------------------------------------------
# 1-ter. Lo que este módulo NO calcula, y de quién depende
# --------------------------------------------------------------------------
#
# Es la receta de `AGENTS.md`: cuando algo no se puede hacer entero, se dice **qué es, para qué haría
# falta y de quién depende**, y se dice en la pantalla y no solo en un comentario. Sin esto, el
# agricultor cree que una cifra que no aparece es un fallo del programa.
QUE_FALTA: tuple[dict[str, str], ...] = (
    {
        "que": "Los años de vida útil de un bien y su cuota de amortización.",
        "para_que": "Poder llevar a cada campaña la parte del tractor que le toca sin preguntártelo.",
        "de_quien_depende": (
            "De que este programa tenga una tabla de amortización con su fuente. Hoy no la tiene, así "
            "que **la parte que va a cada campaña la dices tú**, con un reparto, y lo que no digas se "
            "queda sin asignar."
        ),
    },
    {
        "que": "El extracto del banco y la conciliación de un movimiento con un pago.",
        "para_que": "Poder cuadrar lo que dice el banco con lo que tienes apuntado, y deshacerlo.",
        "de_quien_depende": (
            "Es el ticket siguiente (los extractos). Aquí el pago se apunta a mano, con su fecha y su "
            "importe, y nunca se pide la contraseña de ningún banco."
        ),
    },
    {
        "que": "El IVA soportado y deducible, y el resumen trimestral.",
        "para_que": "Poder presentar los impuestos desde aquí.",
        "de_quien_depende": (
            "De una especificación fiscal propia, igual que la factura emitida: este programa guarda "
            "lo que dice el papel y no emite ningún documento con validez fiscal."
        ),
    },
)


# --------------------------------------------------------------------------
# 2. Los estados de un gasto: seis, y cada uno dice qué hacer
# --------------------------------------------------------------------------
#
# Seis y no tres, por el mismo motivo que en las ventas: cada uno se arregla de una manera distinta.
#
#   · `sin_importe`     — se apuntó el gasto y no se sabe cuánto costó. Hay que buscar el papel.
#   · `sin_pagar`       — hay importe y no ha salido dinero.
#   · `pagado_en_parte` — salió algo y falta algo. Es A06 por el lado de las salidas.
#   · `pagado`          — no falta nada.
#   · `vencido`         — falta algo y ya pasó el día acordado. Es lo único de esta pantalla que
#                         exige una llamada de teléfono.
#   · `anulado`         — no cuenta, y se conserva con su motivo.
SIN_IMPORTE = "sin_importe"
SIN_PAGAR = "sin_pagar"
PAGADO_EN_PARTE = "pagado_en_parte"
PAGADO = "pagado"
VENCIDO = "vencido"
ANULADO = "anulado"

ESTADOS_DE_UN_GASTO: tuple[str, ...] = (
    SIN_IMPORTE,
    SIN_PAGAR,
    PAGADO_EN_PARTE,
    PAGADO,
    VENCIDO,
    ANULADO,
)

# Los estados en los que todavía falta dinero **por pagar**, que es lo que suma el pie de la tabla de
# pendientes. `sin_importe` no entra: no se sabe si falta algo, y meterlo como cero sería inventarse
# una cifra (la mitad financiera de la regla del «no lo sé»).
ESTADOS_CON_PENDIENTE: tuple[str, ...] = (SIN_PAGAR, PAGADO_EN_PARTE, VENCIDO)


def pendiente_de(importe: Decimal | None, pagado: Decimal | None) -> Decimal | None:
    """Lo que falta por pagar. `None` si no se sabe el importe; **nunca negativo**.

    Nunca negativo es una decisión y no un descuido, y es la misma que ya tomó el lado del cobro: si
    alguien pagó de más (un redondeo del proveedor, una devolución), el pendiente es `0,00 €` y lo
    que sobra se dice aparte como dinero sin conciliar. Un pendiente de `-5,00 €` en una pantalla de
    cuentas no significa nada para quien la lee y hace imposible sumar la columna.
    """
    if importe is None:
        return None
    resto = dinero.resta(dinero.a_decimal(importe), dinero.a_decimal(pagado) or dinero.CERO)
    if resto is None:
        return None
    return resto if resto > 0 else dinero.CERO


def estado_de_un_gasto(
    *,
    importe: Decimal | None,
    pagado: Decimal | None,
    vencimiento: dt.date | None = None,
    hoy: dt.date | None = None,
    anulado: bool = False,
) -> str:
    """En qué estado está un gasto. Es una función pura y su primera prueba es el A06 por las salidas.

    El orden de las preguntas es el del agricultor: primero «¿esto cuenta?» (un gasto anulado no
    cuenta), después «¿sé cuánto costó?» (si no, no hay nada que pagar) y solo entonces «¿lo he
    pagado?».

    **Y una cosa que no se hace aquí**: no se convierte un pago que no consta en cero euros de
    gasto. Lo que no consta es el **importe**, y eso se mira tres líneas más arriba; que no haya
    ningún apunte de dinero a su favor sí es un cero de verdad, porque no hay nada apuntado.
    """
    if anulado:
        return ANULADO
    conocido = dinero.a_decimal(importe)
    if conocido is None:
        return SIN_IMPORTE
    salido = dinero.a_decimal(pagado) or dinero.CERO
    falta = pendiente_de(conocido, salido)
    if falta is not None and falta <= 0:
        return PAGADO
    if salido > 0:
        # Se pagó algo y sigue faltando algo: es A06 (121 € de factura, 40 € pagados → faltan 81).
        # Que además esté vencida no cambia lo que hay que hacer —pagar el resto—, así que el estado
        # se queda en «a medias» y la fecha se mira aparte, como dato de la fila.
        return PAGADO_EN_PARTE
    if vencimiento is not None and hoy is not None and vencimiento < hoy:
        return VENCIDO
    return SIN_PAGAR


# --------------------------------------------------------------------------
# 3. El importe del documento: la aritmética es la prueba
# --------------------------------------------------------------------------
#
# Esto es la regla del lector de facturas aplicada a las cuentas: base + IVA = total. Cuando no
# cuadra **se dice en la pantalla**, y es lo que convierte una lectura (o un tecleo) en algo que se
# puede revisar. Aquí no se corrige nada: el programa dice la diferencia, no reescribe el papel.
#
# Y el orden de las fuentes dice cuál manda: **el total que consta manda sobre todo lo demás**. Si el
# agricultor leyó «121,00 €» en el papel, ese es el total aunque base + cuota dé 120,99 por un
# redondeo del proveedor; el contrato lo pide así («registrar diferencias observadas sin forzar a que
# una factura original cuadre con un redondeo distinto»).

TOLERANCIA_DE_CENTIMOS = Decimal("0.01")


@dataclass
class CuadreDeImportes:
    """Las cuentas de un documento de gasto, con lo que no se sabe dicho aparte."""

    base_imponible: Decimal | None = None
    cuota_iva: Decimal | None = None
    total: Decimal | None = None
    # Lo que sale de sumar lo que sí consta, para poder comparar.
    sumado: Decimal | None = None
    diferencia: Decimal | None = None
    # Tres finales, no dos (la regla de la casa): cuadra, no cuadra, y no lo he podido comprobar.
    cuadra: bool = True
    se_puede_comprobar: bool = True
    # Los nombres de los importes que no constan, para que la pantalla pueda decir cuáles faltan.
    no_consta: list[str] = field(default_factory=list)
    # El IVA que sale de aplicar el tipo a la base, cuando el tipo consta. Es una comprobación más,
    # no un dato: no se guarda en ningún sitio.
    iva_calculado: Decimal | None = None

    def como_dict(self) -> dict:
        """Los números ya en su forma de texto, que es como viajan (contrato §2)."""
        return {
            "base_imponible": dinero.a_texto(self.base_imponible),
            "cuota_iva": dinero.a_texto(self.cuota_iva),
            "total": dinero.a_texto(self.total),
            "sumado": dinero.a_texto(self.sumado),
            "diferencia": dinero.a_texto(self.diferencia),
            "cuadra": self.cuadra,
            "se_puede_comprobar": self.se_puede_comprobar,
            "no_consta": list(self.no_consta),
            "iva_calculado": dinero.a_texto(self.iva_calculado),
            "faltan": dinero.cuantos_sin_saber(self.base_imponible, self.cuota_iva, self.total),
        }


def cuadre_de_los_importes(
    *,
    base_imponible: Decimal | None,
    cuota_iva: Decimal | None,
    total: Decimal | None,
    tipo_iva_pct: Decimal | None = None,
) -> CuadreDeImportes:
    """Comprueba las cuentas de un gasto: base + IVA = total. Dice lo que falta, nunca lo supone.

    Tres finales y no dos, que es la regla que este proyecto aprendió comprobando firmas:

      · **cuadra** — constan la base, la cuota y el total, y base + cuota es el total (con un céntimo
        de tolerancia, que es lo que se redondea en una factura de verdad);
      · **no cuadra** — constan los tres y no suman: la pantalla lo enseña para que se revise;
      · **no lo he podido comprobar** — falta alguno de los tres. Ahí **no se dice que esté mal**: se
        dice qué falta. Rechazar un gasto porque no se ha leído bien su IVA sería acusar al
        agricultor de algo que no ha hecho.

    El importe que de verdad se usa para el gasto lo decide el agricultor: si escribió el total, ese
    es el total; si no, se suma base + cuota; si tampoco, base × (1 + tipo); y si no hay nada, el
    gasto **no tiene importe**, que no es lo mismo que costar cero.
    """
    base = dinero.a_decimal(base_imponible)
    cuota = dinero.a_decimal(cuota_iva)
    escrito = dinero.a_decimal(total)
    tipo = dinero.a_decimal(tipo_iva_pct)

    no_consta: list[str] = []
    if base is None:
        no_consta.append("base_imponible")
    if cuota is None:
        no_consta.append("cuota_iva")
    if escrito is None:
        no_consta.append("total")

    iva_calculado = None
    if base is not None and tipo is not None:
        iva_calculado = dinero.redondea(base * tipo / Decimal(100))

    # Lo que se puede sumar. Un sumando que no consta **no se cuenta como cero**: se deja fuera y se
    # dice, que es lo que distingue «no lo sé» de «es cero».
    sumandos = [valor for valor in (base, cuota) if valor is not None]
    sumado = dinero.suma(*sumandos) if len(sumandos) == 2 else None

    se_puede_comprobar = base is not None and cuota is not None and escrito is not None
    diferencia = None
    cuadra = True
    if sumado is not None and escrito is not None:
        diferencia = dinero.resta(escrito, sumado)
        cuadra = abs(diferencia) <= TOLERANCIA_DE_CENTIMOS

    return CuadreDeImportes(
        base_imponible=base,
        cuota_iva=cuota,
        total=escrito,
        sumado=sumado,
        diferencia=diferencia,
        cuadra=cuadra if se_puede_comprobar else True,
        se_puede_comprobar=se_puede_comprobar,
        no_consta=no_consta,
        iva_calculado=iva_calculado,
    )


def importe_de_un_gasto(
    *,
    base_imponible: Decimal | None = None,
    cuota_iva: Decimal | None = None,
    total: Decimal | None = None,
    tipo_iva_pct: Decimal | None = None,
) -> Decimal | None:
    """Cuánto costó el gasto: **el total escrito manda**, y si no consta se calcula, o es «no lo sé».

    Las cuatro reglas, y por qué en ese orden:

      1. **Lo que el agricultor escribió manda.** Si él vio el papel del proveedor y pone 121,00 €,
         ese es el importe aunque la suma dé otra cosa por medio céntimo: el programa comprueba la
         aritmética, no corrige el papel de enfrente.
      2. Si no lo escribió pero constan la base y la cuota, se suman.
      3. Si no hay cuota pero sí base y tipo de IVA, se aplica el tipo a la base y se suma.
      4. Si no hay nada de eso, **no se sabe**: `None`, nunca `0.00`. Un cero sería un gasto de cero
         euros en las cuentas del año, que es falso.
    """
    escrito = dinero.a_decimal(total)
    if escrito is not None:
        return dinero.redondea(escrito)
    base = dinero.a_decimal(base_imponible)
    cuota = dinero.a_decimal(cuota_iva)
    if base is not None and cuota is not None:
        return dinero.redondea(dinero.suma(base, cuota))
    if base is not None:
        tipo = dinero.a_decimal(tipo_iva_pct)
        if tipo is not None:
            return dinero.redondea(base * (Decimal(100) + tipo) / Decimal(100))
    return None


# --------------------------------------------------------------------------
# 4. Los repartos: cómo se lleva un coste a las tierras, los cultivos y las máquinas
# --------------------------------------------------------------------------
#
# **El método de reparto lo confirma el agricultor** (contrato S13): por área, por horas, por consumo
# o a mano. Son cuatro y cada uno es una cosa distinta:
#
#   · **área**    — el alquiler de la nave, el seguro, la luz: se reparte por hectáreas.
#   · **horas**   — la mano de obra, el tractor: se reparte por las horas que trabajó en cada sitio.
#   · **consumo** — el gasóleo, el abono: se reparte por lo que se gastó en cada sitio.
#   · **manual**  — el agricultor pone los importes él mismo, uno por uno.
#
# Los tres primeros son una cuenta; el cuarto no. Y **ninguno de los cuatro se elige solo**: la
# pantalla pregunta cuál y el agricultor lo contesta, porque el mismo gasto se reparte de una manera
# u otra según el caso y el programa no lo puede adivinar.
AREA = "area"
HORAS = "horas"
CONSUMO = "consumo"
MANUAL = "manual"

METODOS_DE_REPARTO: tuple[str, ...] = (AREA, HORAS, CONSUMO, MANUAL)

# A qué se puede repartir un coste. `SIN_ASIGNAR` es una respuesta de verdad y no un hueco: es lo
# que se elige cuando el agricultor **no sabe** a qué va ese coste, y es lo que impide que el
# programa lo reparta «a medias entre todos», que es inventarse un coste por tierra.
TIERRA = "tierra"
CULTIVO = "cultivo"
MAQUINA = "maquina"
CAMPANA = "campana"
SIN_ASIGNAR = "sin_asignar"

DESTINOS_DE_UN_REPARTO: tuple[str, ...] = (TIERRA, CULTIVO, MAQUINA, CAMPANA, SIN_ASIGNAR)

# Las tres clases de coste que el contrato pide enseñar **por separado** en S13: directos, repartidos
# y sin asignar. Que vayan separados no es cosmética: un coste repartido es una estimación acordada
# y uno directo es lo que pone el papel, y sumarlos en una sola cifra sin decirlo mezcla dos cosas de
# fiabilidad distinta.
DIRECTO = "directo"
REPARTIDO = "repartido"
SIN_ASIGNAR_CLASE = "sin_asignar"

CLASES_DE_COSTE: tuple[str, ...] = (DIRECTO, REPARTIDO, SIN_ASIGNAR_CLASE)

# Por qué un gasto se ha quedado sin repartir. Se devuelve como código y la frase la pone
# `textos.py`: un gasto sin repartir **no es un error del programa**, es una decisión del
# agricultor o un dato que falta, y se dice cuál de las dos cosas es.
NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE = "no_se_el_importe"
NO_SE_REPARTE_PORQUE_FALTA_UN_PESO = "falta_un_peso"
NO_SE_REPARTE_PORQUE_NO_HA_DICHO_EL_METODO = "no_ha_dicho_el_metodo"


@dataclass
class TrozoDeReparto:
    """Un trozo de un gasto, con a quién va y por qué método."""

    destino_tipo: str
    destino: str
    importe: Decimal
    metodo: str

    def como_dict(self) -> dict:
        return {
            "destino_tipo": self.destino_tipo,
            "destino": self.destino,
            "importe": dinero.a_texto(self.importe),
            "metodo": self.metodo,
        }


@dataclass
class RepartoHecho:
    """Lo que sale de repartir un gasto entre varios sitios: los trozos **y el redondeo, a la vista**.

    `residual` es lo que se ha repartido «de más» al cuadrar los céntimos, y existe porque el
    contrato lo exige con estas palabras: «la suma tiene que ser exacta, con el redondeo residual a
    la vista. Un reparto que suma 99,99 de 100 y no dice dónde está el céntimo es un defecto».

    Sin este campo, el céntimo que falta es invisible: la pantalla enseña tres trozos que parecen
    bien y no suman el total, y nadie sabe por qué.
    """

    trozos: list[TrozoDeReparto] = field(default_factory=list)
    total: Decimal | None = None
    residual: Decimal = dinero.CERO
    # A qué trozo se le ha puesto el céntimo del redondeo. Se dice por nombre para que la pantalla
    # pueda enseñarlo, y porque «el primero» en una lista que se ordena por otro sitio es una
    # explicación que se pierde.
    residual_en: str | None = None
    metodo: str = ""
    # Si el reparto no se ha podido hacer, por qué. Vacío quiere decir que sí se ha hecho.
    no_se_puede: str = ""
    # Los destinos que no entraron en la cuenta por faltar su peso. Se dicen para que el agricultor
    # sepa qué dato falta, en vez de ver un reparto que no incluye su tierra y no saber por qué.
    sin_peso: list[str] = field(default_factory=list)

    def suma(self) -> Decimal:
        return dinero.suma(*[trozo.importe for trozo in self.trozos])

    def cuadra(self) -> bool:
        """¿Los trozos suman exactamente el total? Es la comprobación que el ticket exige."""
        if self.total is None:
            return False
        return self.suma() == dinero.redondea(self.total)


def reparto_por_peso(
    importe: Decimal | None,
    pesos: dict[str, Decimal | None],
    *,
    metodo: str,
    destino_tipo: str,
) -> RepartoHecho:
    """Reparte un importe entre varios destinos **en proporción a su peso**, sin perder un céntimo.

    ## Por qué el céntimo que sobra no se tira

    Dividir 100,00 € entre tres tierras iguales da 33,3333… € cada una. Redondeando cada trozo al
    céntimo salen 33,33 + 33,33 + 33,33 = **99,99**: falta un céntimo, y el agricultor que echa la
    cuenta con la libreta lo ve. Repartir «un poco más» a cada una es imposible (no hay medios
    céntimos), así que lo que se hace es lo que hace cualquier reparto de una cuenta:

      1. se calcula el trozo exacto de cada uno, sin redondear;
      2. se le da a cada uno **su parte entera en céntimos** (hacia abajo);
      3. los céntimos que sobran se dan **de uno en uno a quien más fracción tenía**, y el empate se
         rompe por el orden de la lista para que la cuenta salga **siempre igual**.

    El paso 3 es el que hace que la suma sea exacta y que el reparto se pueda repetir: con el mismo
    gasto y las mismas hectáreas, el mismo agricultor obtiene el mismo reparto hoy y dentro de un año.

    ## Y lo que NO hace: repartir cuando falta un peso

    Si de una de las tierras no se sabe su superficie, **el reparto no se hace**. Repartir entre las
    que sí se saben sería peor que no repartir: a las que entran les cargaría también la parte de la
    que falta, y el programa estaría inventándose un coste por hectárea. En ese caso se devuelve
    `no_se_puede = NO_SE_REPARTE_PORQUE_FALTA_UN_PESO` y la lista de destinos sin peso, y el gasto se
    queda **sin asignar**, que es lo que el ticket pide.

    Un peso de cero tampoco vale, y por el mismo motivo que un peso que no se sabe: significa
    «aquí no se gastó nada», y un destino con peso cero no recibe nada —pero si **todos** son cero
    no hay reparto que hacer—.
    """
    total = dinero.a_decimal(importe)
    if total is None:
        return RepartoHecho(total=None, metodo=metodo, no_se_puede=NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE)
    if metodo not in METODOS_DE_REPARTO:
        raise ValueError(f"«{metodo}» no es un método de reparto de los cuatro que hay.")
    if not pesos:
        return RepartoHecho(total=total, metodo=metodo, no_se_puede=NO_SE_REPARTE_PORQUE_FALTA_UN_PESO)

    conocidos: dict[str, Decimal] = {}
    sin_peso: list[str] = []
    for destino, valor in pesos.items():
        peso = dinero.cantidad_a_decimal(valor)
        if peso is None or peso < 0:
            sin_peso.append(str(destino))
            continue
        conocidos[str(destino)] = peso

    if sin_peso:
        return RepartoHecho(
            total=total,
            metodo=metodo,
            no_se_puede=NO_SE_REPARTE_PORQUE_FALTA_UN_PESO,
            sin_peso=sin_peso,
        )

    suma_de_pesos = sum(conocidos.values(), Decimal(0))
    if suma_de_pesos <= 0:
        return RepartoHecho(total=total, metodo=metodo, no_se_puede=NO_SE_REPARTE_PORQUE_FALTA_UN_PESO)

    # El reparto se hace **en céntimos enteros** y con el valor absoluto: un importe negativo (una
    # devolución del proveedor) se reparte igual y se le devuelve el signo al final. Repartir con el
    # signo dentro obligaría a ordenar las fracciones al revés y es donde se cuelan los errores.
    centimo = Decimal("0.01")
    signo = Decimal(-1) if total < 0 else Decimal(1)
    en_centimos = (abs(total) * 100).to_integral_value(rounding=decimal.ROUND_HALF_UP)
    total_de_centimos = int(en_centimos)

    exactos: dict[str, Decimal] = {}
    for destino, peso in conocidos.items():
        exactos[destino] = Decimal(total_de_centimos) * peso / suma_de_pesos

    enteros: dict[str, int] = {}
    fracciones: dict[str, Decimal] = {}
    for destino, exacto in exactos.items():
        abajo = int(exacto.to_integral_value(rounding=decimal.ROUND_FLOOR))
        enteros[destino] = abajo
        fracciones[destino] = exacto - abajo

    sobran = total_de_centimos - sum(enteros.values())
    # El empate se rompe por el orden de la lista, que es el que le ha pasado quien llama (las
    # tierras por su nombre, los meses por su número): así el mismo reparto sale siempre igual.
    orden = sorted(conocidos.keys(), key=lambda destino: (-fracciones[destino], list(conocidos).index(destino)))
    con_el_centimo: str | None = None
    for destino in orden[: max(sobran, 0)]:
        enteros[destino] += 1
        con_el_centimo = destino

    trozos = [
        TrozoDeReparto(
            destino_tipo=destino_tipo,
            destino=destino,
            importe=dinero.redondea(Decimal(enteros[destino]) * centimo * signo),
            metodo=metodo,
        )
        for destino in conocidos
    ]
    return RepartoHecho(
        trozos=trozos,
        total=dinero.redondea(total),
        residual=dinero.redondea(Decimal(max(sobran, 0)) * centimo * signo),
        residual_en=con_el_centimo,
        metodo=metodo,
    )


def reparto_por_area(
    importe: Decimal | None, areas: dict[str, Decimal | None], *, destino_tipo: str = TIERRA
) -> RepartoHecho:
    """Reparte por hectáreas. Es el método de lo que no se gasta en un sitio concreto."""
    return reparto_por_peso(importe, areas, metodo=AREA, destino_tipo=destino_tipo)


def reparto_por_horas(
    importe: Decimal | None, horas: dict[str, Decimal | None], *, destino_tipo: str = TIERRA
) -> RepartoHecho:
    """Reparte por las horas que se trabajó en cada sitio (la mano de obra, el tractor)."""
    return reparto_por_peso(importe, horas, metodo=HORAS, destino_tipo=destino_tipo)


def reparto_por_consumo(
    importe: Decimal | None, consumos: dict[str, Decimal | None], *, destino_tipo: str = TIERRA
) -> RepartoHecho:
    """Reparte por lo que se gastó en cada sitio (el gasóleo, el abono, el producto)."""
    return reparto_por_peso(importe, consumos, metodo=CONSUMO, destino_tipo=destino_tipo)


def reparto_a_mano(importe: Decimal | None, trozos: list[dict]) -> RepartoHecho:
    """El reparto que pone el agricultor, importe a importe. Aquí no hay proporción que calcular.

    **Lo que sí hace, y es lo único que puede estar mal en un reparto a mano: comprobar que los
    trozos no sumen más que el gasto.** Repartir 100 € en trozos de 60 y 50 no es un reparto, es un
    error de tecleo, y decirlo aquí evita que aparezca como un margen raro tres pantallas más
    adelante. Lo que falte por repartir **no es un error**: es un gasto del que todavía no se sabe a
    qué va, y se queda sin asignar (y `cuadre_del_reparto` lo dirá).
    """
    total = dinero.a_decimal(importe)
    trozos_hechos: list[TrozoDeReparto] = []
    for trozo in trozos or []:
        suyo = dinero.a_decimal(trozo.get("importe"))
        if suyo is None:
            # Un trozo sin importe no se cuenta como cero: se deja fuera y quien llama verá que el
            # reparto no cuadra, que es la verdad.
            continue
        trozos_hechos.append(
            TrozoDeReparto(
                destino_tipo=trozo.get("destino_tipo") or SIN_ASIGNAR,
                destino=str(trozo.get("destino") or ""),
                importe=dinero.redondea(suyo),
                metodo=MANUAL,
            )
        )
    hecho = RepartoHecho(trozos=trozos_hechos, total=total, metodo=MANUAL)
    if total is not None and hecho.suma() > dinero.redondea(total):
        # Se ha repartido más de lo que costó: eso no es un reparto incompleto, es un error de
        # tecleo, y el motivo se dice para que la pantalla no lo confunda con «falta por repartir».
        hecho.no_se_puede = "se_ha_repartido_mas_que_el_gasto"
    return hecho


@dataclass
class CuadreDelReparto:
    """El cuadre que el contrato pide: **costes repartidos + costes sin asignar = total conocido**.

    Es la comprobación central del ticket, y por eso está en un tipo propio con sus cuatro números a
    la vista en vez de escondida en una resta:

      · `entero` — lo que costó el gasto, si consta. Si no consta, **no hay cuadre que hacer** y se
        dice: no se puede repartir lo que no se sabe cuánto costó.
      · `repartido` — lo que se ha llevado a tierras, cultivos o máquinas.
      · `sin_asignar` — lo que sigue sin saberse a qué va. **No es un cero**: es una respuesta.
      · `falta` — lo que no está ni en un sitio ni en el otro. Si esto no es cero, el cuadre falla y
        se dice cuánto falta, que es lo que impide que un coste desaparezca por el camino.

    `cuadra` es falso también cuando se ha repartido **más** de lo que costó, que es un error de
    tecleo y no un reparto: `falta` sale negativo y la pantalla lo dice.
    """

    entero: Decimal | None = None
    repartido: Decimal = dinero.CERO
    sin_asignar: Decimal = dinero.CERO
    falta: Decimal | None = None
    cuadra: bool = True
    # Cuántos trozos traían un importe que no se sabe. No entran en la suma (no se cuentan como
    # cero) y por eso se dicen: sin este número, un reparto al que le falta un trozo parecería corto
    # por otro motivo.
    trozos_sin_importe: int = 0
    # Por qué el gasto se ha quedado sin asignar, cuando se ha quedado.
    no_se_reparte: str = ""
    destinos: list[dict] = field(default_factory=list)

    def total_conocido(self) -> Decimal:
        """Todo lo que consta que costó y está en uno de los dos sitios."""
        return dinero.suma(self.repartido, self.sin_asignar)

    def como_dict(self) -> dict:
        return {
            "entero": dinero.a_texto(self.entero),
            "repartido": dinero.a_texto(self.repartido),
            "sin_asignar": dinero.a_texto(self.sin_asignar),
            "total_conocido": dinero.a_texto(self.total_conocido()),
            "falta": dinero.a_texto(self.falta),
            "cuadra": self.cuadra,
            "trozos_sin_importe": self.trozos_sin_importe,
            "no_se_reparte": self.no_se_reparte,
            "destinos": list(self.destinos),
        }


def cuadre_del_reparto(entero: Decimal | None, trozos: list[dict] | None) -> CuadreDelReparto:
    """Cierra la cuenta de un gasto: lo repartido más lo sin asignar tiene que dar el total.

    `trozos` es lo que hay apuntado: cada uno con su `importe`, su `destino_tipo` y su `destino`. Un
    trozo con `destino_tipo = SIN_ASIGNAR` es una respuesta de verdad («no sé a qué va esto») y va a
    la columna de sin asignar, no a la de repartido.

    **La comprobación no es una tautología.** `falta` se calcula restando de verdad, así que si a un
    gasto de 100 € se le han apuntado 60 € a una tierra y nada sin asignar, el cuadre sale con 40 €
    que faltan y `cuadra` es falso. Eso es lo que impide que un coste se pierda entre dos pantallas.
    """
    cuadre = CuadreDelReparto(entero=dinero.a_decimal(entero))
    for trozo in trozos or []:
        importe = dinero.a_decimal(trozo.get("importe"))
        if importe is None:
            cuadre.trozos_sin_importe += 1
            continue
        redondeado = dinero.redondea(importe)
        if (trozo.get("destino_tipo") or "") == SIN_ASIGNAR:
            cuadre.sin_asignar = dinero.suma(cuadre.sin_asignar, redondeado)
        else:
            cuadre.repartido = dinero.suma(cuadre.repartido, redondeado)
        cuadre.destinos.append(
            {
                "destino_tipo": trozo.get("destino_tipo") or SIN_ASIGNAR,
                "destino": str(trozo.get("destino") or ""),
                "importe": dinero.a_texto(redondeado),
                "metodo": trozo.get("metodo") or MANUAL,
            }
        )
    if cuadre.entero is None:
        # Sin saber cuánto costó no hay cuadre: no se puede decir si lo repartido es todo o una
        # parte. Lo que sí se sabe se enseña, y se dice que falta el importe.
        cuadre.falta = None
        cuadre.cuadra = False
        cuadre.no_se_reparte = NO_SE_REPARTE_PORQUE_NO_SE_EL_IMPORTE
        return cuadre
    cuadre.falta = dinero.resta(cuadre.entero, cuadre.total_conocido())
    cuadre.cuadra = cuadre.falta == dinero.CERO
    return cuadre


def el_gasto_queda_sin_asignar(entero: Decimal | None, *, porque: str) -> CuadreDelReparto:
    """Un gasto que **no se reparte**: se queda entero en «sin asignar» y se dice por qué.

    Es la respuesta del ticket a «si un gasto no se sabe repartir, no se reparte a medias». Y fíjate
    en lo que **sí** hace: el importe entero va a `sin_asignar`, así que el cuadre sigue cuadrando
    (repartido 0 + sin asignar 100 = 100) y el coste **no desaparece de la vista**. Un gasto sin
    repartir sigue siendo un coste conocido; lo que no está es atribuido a nadie, y eso se dice.
    """
    cuadre = CuadreDelReparto(entero=dinero.a_decimal(entero), no_se_reparte=porque)
    if cuadre.entero is None:
        cuadre.cuadra = False
        cuadre.falta = None
        return cuadre
    cuadre.sin_asignar = cuadre.entero
    cuadre.falta = dinero.CERO
    cuadre.cuadra = True
    cuadre.destinos = [
        {
            "destino_tipo": SIN_ASIGNAR,
            "destino": "",
            "importe": dinero.a_texto(cuadre.entero),
            "metodo": MANUAL,
        }
    ]
    return cuadre


# --------------------------------------------------------------------------
# 5. El abono: dos cifras distintas dichas como distintas (caso de aceptación A03)
# --------------------------------------------------------------------------
#
# El caso A03 del contrato, literal: «Abono 600 kg en 3 ha, N 15 % acreditado | 200 kg/ha de
# producto; 30 kg N/ha; **P desconocido si falta**».
#
# Y lo que demuestra no es una multiplicación: son **dos cosas dichas como dos cosas distintas**. Los
# kilos de producto por hectárea y los kilos de nutriente por hectárea **no son el mismo número** y
# confundirlos es un error de diez veces en el abono. Y el fósforo, si nadie ha declarado la riqueza
# del abono en fósforo, **no es cero**: es que no se sabe, y en el documento que se firma se lee como
# «este abono no aporta fósforo», que es mentira.
#
# Es el mismo error que este proyecto ya ha perseguido en los casos A6, A7 y A9 (convertir lo ausente
# en cero), ahora con nutrientes. La cuenta de los nutrientes **no se escribe aquí de nuevo**:
# `legal.unidades_fertilizantes` ya existe y es la que usa el cuaderno, así que se reutiliza y no hay
# dos verdades sobre qué es una unidad fertilizante.

NUTRIENTES: tuple[str, ...] = ("n", "p", "k")


@dataclass
class AbonoPorHectarea:
    """Las cifras de un abono, cada una en su sitio y con lo que no se sabe dicho aparte."""

    kg_producto: Decimal | None = None
    superficie_ha: Decimal | None = None
    # **La cifra del producto**: kilos de abono por hectárea (200 en el A03).
    producto_ha: Decimal | None = None
    # **La cifra del nutriente**: kilos de nutriente por hectárea (30 de N en el A03). Una entrada
    # por nutriente, y `None` en la que no se sepa. Nunca un cero por no saberlo.
    nutriente_ha: dict[str, Decimal | None] = field(default_factory=dict)
    nutriente_total: dict[str, Decimal | None] = field(default_factory=dict)
    # Los nutrientes cuya riqueza **no consta**. Es lo que hace que la pantalla pueda decir «el
    # fósforo no lo sé» en vez de enseñar un cero, y es la mitad del A03.
    no_consta: list[str] = field(default_factory=list)
    # Si el abono no dice ni la riqueza de ningún nutriente, la pantalla lo dice con una frase: es un
    # caso muy distinto de «le falta el fósforo».
    sin_ninguna_riqueza: bool = False

    def como_dict(self) -> dict:
        return {
            "kg_producto": dinero.a_texto(self.kg_producto),
            "superficie_ha": dinero.a_texto(self.superficie_ha),
            "producto_ha": dinero.a_texto(self.producto_ha),
            "nutriente_ha": {clave: dinero.a_texto(valor) for clave, valor in self.nutriente_ha.items()},
            "nutriente_total": {
                clave: dinero.a_texto(valor) for clave, valor in self.nutriente_total.items()
            },
            "no_consta": list(self.no_consta),
            "sin_ninguna_riqueza": self.sin_ninguna_riqueza,
        }


def abono_por_hectarea(
    *,
    kg_producto: Decimal | None,
    superficie_ha: Decimal | None,
    riquezas: dict[str, Decimal | None] | None = None,
) -> AbonoPorHectarea:
    """El caso A03: cuánto producto y cuánto nutriente por hectárea, sin inventar el que no consta.

    `riquezas` es el porcentaje de cada nutriente **tal y como lo dice la etiqueta o el albarán**
    (`{"n": 15, "p": None, "k": None}`). Un nutriente que no venga, o que venga vacío, es «no
    consta» y sale en `no_consta`: **no se rellena con cero**.

    Y la superficie que no consta o que vale cero no convierte la cuenta en cero: deja las dos
    cifras por hectárea en «no se sabe» (`None`). Dividir por cero daría un número infinito, que en
    una pantalla de abono es peor que un hueco.
    """
    kilos = dinero.cantidad_a_decimal(kg_producto)
    superficie = dinero.cantidad_a_decimal(superficie_ha)

    producto_ha = None
    if kilos is not None and superficie is not None and superficie > 0:
        producto_ha = dinero.redondea(kilos / superficie, 4)

    dicho = riquezas or {}
    nutriente_ha: dict[str, Decimal | None] = {}
    nutriente_total: dict[str, Decimal | None] = {}
    no_consta: list[str] = []
    for nutriente in NUTRIENTES:
        riqueza = dinero.cantidad_a_decimal(dicho.get(nutriente))
        if riqueza is None:
            # **Aquí está el A03 entero**: el fósforo que nadie ha declarado se queda en «no lo sé».
            # Un `CERO` en esta línea convertiría el abono en «no aporta fósforo», que es una
            # afirmación sobre el abono que el programa no puede hacer.
            nutriente_ha[nutriente] = None
            nutriente_total[nutriente] = None
            no_consta.append(nutriente)
            continue
        if producto_ha is not None:
            nutriente_ha[nutriente] = dinero.redondea(producto_ha * riqueza / Decimal(100), 4)
        else:
            nutriente_ha[nutriente] = None
        if kilos is not None:
            nutriente_total[nutriente] = dinero.redondea(kilos * riqueza / Decimal(100), 4)
        else:
            nutriente_total[nutriente] = None

    return AbonoPorHectarea(
        kg_producto=kilos,
        superficie_ha=superficie,
        producto_ha=producto_ha,
        nutriente_ha=nutriente_ha,
        nutriente_total=nutriente_total,
        no_consta=no_consta,
        sin_ninguna_riqueza=len(no_consta) == len(NUTRIENTES),
    )


# --------------------------------------------------------------------------
# 6. Los pagos: parciales, agrupados, y que se puedan deshacer
# --------------------------------------------------------------------------
#
# **Conciliar un pago con un gasto no crea un gasto.** Es la regla del encargo escrita tal cual, y la
# forma de cumplirla es que la función de aquí **no devuelva gastos**: devuelve **aplicaciones**, que
# son pares «este dinero va contra este gasto». Con eso:
#
#   · el número de gastos no puede cambiar al conciliar, porque conciliar no tiene por dónde crearlos;
#   · un pago puede repartirse entre varios gastos (agrupado);
#   · varios pagos pueden ir contra un gasto (parcial);
#   · y deshacer es **quitar las aplicaciones**, no tocar ni el pago ni el gasto. El dinero sigue
#     apuntado y el gasto vuelve a estar pendiente, que es exactamente lo que pide el contrato para
#     deshacer una conciliación.


@dataclass
class AplicacionDeUnPago:
    """Un trozo de un pago, aplicado a un gasto. Es lo único que crea la conciliación."""

    gasto_id: int
    importe: Decimal

    def como_dict(self) -> dict:
        return {"gasto_id": self.gasto_id, "importe": dinero.a_texto(self.importe)}


@dataclass
class RepartoDeUnPago:
    """Cómo se reparte un pago entre los gastos que salda, y qué sobra."""

    aplicaciones: list[AplicacionDeUnPago] = field(default_factory=list)
    sin_conciliar: Decimal = dinero.CERO
    # Los gastos que se han quedado fuera por no saberse su importe. El dinero no se les aplica: no
    # se sabe contra qué cantidad iría, y aplicarlo contra un cero sería inventarse la deuda.
    sin_importe: list[int] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "aplicaciones": [aplicacion.como_dict() for aplicacion in self.aplicaciones],
            "sin_conciliar": dinero.a_texto(self.sin_conciliar),
            "sin_importe": list(self.sin_importe),
        }


def reparto_de_un_pago(
    importe: Decimal | None, pendientes: list[tuple[int, Decimal | None]]
) -> RepartoDeUnPago:
    """Reparte el dinero que sale entre los gastos que tiene delante: `[(gasto_id, pendiente)]`.

    ## La regla, que es la de cualquier cuenta corriente

    **El dinero se aplica por orden, el más antiguo primero** (el orden de la lista es el que le pasa
    quien llama, que ordena por fecha de vencimiento), y a cada gasto se le pone lo que le falta
    hasta completarlo. Así:

      · un pago de 100 € contra pendientes de 60, 60 y 60 deja 60, 40 y 0, y **ni un céntimo se
        pierde ni se cuenta dos veces**;
      · un pago de 500 € contra un pendiente de 121 deja 121 aplicados y **379 sin conciliar**: ese
        dinero no es de nadie todavía y se queda dicho, esperando a saber a qué va (o a devolverse).
        Lo que **no** se hace es dejar el gasto en `-379`: un pendiente negativo no se puede sumar
        con los demás y no significa nada para quien lee la pantalla.

    ## Y lo que no se puede hacer, dicho en vez de supuesto

    Un gasto cuyo importe no consta **no recibe nada** (`sin_importe`). No es que no deba nada: es
    que no se sabe cuánto debe, y aplicarle dinero contra una cantidad desconocida sería inventarse
    la deuda en el sitio donde más caro sale —el día que se reclame—.
    """
    salido = dinero.a_decimal(importe) or dinero.CERO
    reparto = RepartoDeUnPago()
    queda = dinero.redondea(salido)
    for gasto_id, pendiente in pendientes:
        conocido = dinero.a_decimal(pendiente)
        if conocido is None:
            reparto.sin_importe.append(gasto_id)
            continue
        if conocido <= 0 or queda <= 0:
            continue
        puesto = conocido if conocido <= queda else queda
        reparto.aplicaciones.append(
            AplicacionDeUnPago(gasto_id=gasto_id, importe=dinero.redondea(puesto))
        )
        queda = dinero.redondea(queda - puesto)
    reparto.sin_conciliar = queda if queda > 0 else dinero.CERO
    return reparto


def deshacer_las_aplicaciones(
    aplicaciones: list[dict], pendientes: list[tuple[int, Decimal | None]]
) -> list[tuple[int, Decimal | None]]:
    """Lo que queda pendiente **después de deshacer** una conciliación: se devuelve la deuda.

    Es la mitad del contrato que dice «deshacer una conciliación no borra el movimiento original», y
    aquí se ve por qué está escrita así: esta función **solo devuelve una lista de pendientes**. No
    borra nada, no toca el pago y no toca el gasto: quita lo que se había aplicado y la deuda vuelve.
    Quien llama se encarga de borrar las filas de aplicación (dejando el rastro en la auditoría), y el
    pago sigue apuntado con su importe entero, que es lo que hace que el dinero no desaparezca.
    """
    quitado: dict[int, Decimal] = {}
    for aplicacion in aplicaciones:
        gasto_id = int(aplicacion.get("gasto_id"))
        importe = dinero.a_decimal(aplicacion.get("importe")) or dinero.CERO
        quitado[gasto_id] = dinero.suma(quitado.get(gasto_id, dinero.CERO), importe)
    salida: list[tuple[int, Decimal | None]] = []
    for gasto_id, pendiente in pendientes:
        conocido = dinero.a_decimal(pendiente)
        if conocido is None:
            salida.append((gasto_id, None))
            continue
        salida.append((gasto_id, dinero.redondea(dinero.suma(conocido, quitado.get(gasto_id, dinero.CERO)))))
    return salida


# --------------------------------------------------------------------------
# 7. El traspaso entre cuentas propias (caso de aceptación A07)
# --------------------------------------------------------------------------
#
# El caso A07 del contrato, literal: «Traspaso propio 500 EUR | **Dos movimientos vinculados, cero
# ingreso/gasto operativo**».
#
# Lo que demuestra es que mover dinero de una cuenta propia a otra **no es ingreso ni gasto**, y que
# tienen que quedar **dos movimientos atados**, no uno suelto. Un extracto bancario trae las dos
# líneas (una salida de 500 en una cuenta y una entrada de 500 en la otra) y, si el programa las
# tratara como un gasto y un ingreso, el agricultor vería en su cuenta anual 500 € de gasto y 500 €
# de ingreso que no existieron: **la caja cuadraría y el margen sería mentira**.
#
# Y es una decisión del agricultor, no del programa: hay movimientos que se parecen (una
# transferencia a un proveedor y su devolución) y solo él sabe si es un traspaso propio. Por eso se
# marca a mano y el programa no lo adivina.

INGRESO = "ingreso"
GASTO_OPERATIVO = "gasto_operativo"
TRASPASO = "traspaso"

CLASES_DE_MOVIMIENTO: tuple[str, ...] = (INGRESO, GASTO_OPERATIVO, TRASPASO)


@dataclass
class TraspasoPropio:
    """Los dos movimientos de un traspaso, atados, y el efecto que tienen en las cuentas."""

    importe: Decimal | None = None
    cuenta_origen: str = ""
    cuenta_destino: str = ""
    salida: Decimal = dinero.CERO
    entrada: Decimal = dinero.CERO
    # **Lo que de verdad importa, y se dice con un cero explícito**: un traspaso no mueve el margen.
    ingreso_operativo: Decimal = dinero.CERO
    gasto_operativo: Decimal = dinero.CERO
    vinculados: bool = False
    # Los dos apuntes que hay que guardar. Van aquí y no en el router para que la prueba pueda
    # comprobar que **son dos** y que están atados, que es literalmente lo que pide el caso A07.
    movimientos: list[dict] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "importe": dinero.a_texto(self.importe),
            "cuenta_origen": self.cuenta_origen,
            "cuenta_destino": self.cuenta_destino,
            "salida": dinero.a_texto(self.salida),
            "entrada": dinero.a_texto(self.entrada),
            "ingreso_operativo": dinero.a_texto(self.ingreso_operativo),
            "gasto_operativo": dinero.a_texto(self.gasto_operativo),
            "vinculados": self.vinculados,
            "movimientos": list(self.movimientos),
        }


def traspaso_entre_cuentas_propias(
    importe: Decimal | None, *, cuenta_origen: str, cuenta_destino: str
) -> TraspasoPropio:
    """El caso A07: dos movimientos atados y **cero ingreso/gasto operativo**.

    Un traspaso de la misma cuenta a la misma cuenta no es un traspaso: es un apunte mal hecho, y se
    contesta con los dos movimientos sin atar (`vinculados = False`) para que quien llama pueda
    decirlo. Un importe que no consta tampoco se convierte en cero: los dos movimientos salen con su
    importe en blanco.
    """
    conocido = dinero.a_decimal(importe)
    if conocido is not None:
        conocido = dinero.redondea(abs(conocido))
    distinta = bool(cuenta_origen) and bool(cuenta_destino) and cuenta_origen != cuenta_destino
    traspaso = TraspasoPropio(
        importe=conocido,
        cuenta_origen=cuenta_origen,
        cuenta_destino=cuenta_destino,
        vinculados=distinta and conocido is not None,
    )
    if conocido is None:
        return traspaso
    traspaso.salida = conocido
    traspaso.entrada = conocido
    traspaso.movimientos = [
        {"cuenta": cuenta_origen, "signo": "-", "importe": dinero.a_texto(conocido), "clase": TRASPASO},
        {"cuenta": cuenta_destino, "signo": "+", "importe": dinero.a_texto(conocido), "clase": TRASPASO},
    ]
    # `ingreso_operativo` y `gasto_operativo` no se tocan: se quedan en cero **a propósito**. Esta
    # función es el sitio donde alguien «arreglaría» el caso A07 sumando la entrada como ingreso, y
    # por eso hay una prueba que comprueba los dos ceros.
    return traspaso


# --------------------------------------------------------------------------
# 8. Las subvenciones: prevista, concedida y cobrada son tres estados distintos
# --------------------------------------------------------------------------
#
# El contrato, en S13: «Subvención prevista, concedida y cobrada son estados distintos. **No sumar
# previsión al ingreso cobrado**». Es el mismo error de siempre con otra ropa: una ayuda que se
# espera no es dinero que ha entrado, y meterla en el ingreso del año hace que el agricultor crea que
# tiene un dinero que todavía no tiene. Hay una prueba que falla si la previsión se suma.
PREVISTA = "prevista"
CONCEDIDA = "concedida"
COBRADA = "cobrada"

ESTADOS_DE_UNA_SUBVENCION: tuple[str, ...] = (PREVISTA, CONCEDIDA, COBRADA)

# Qué estado es «más» que otro, para poder decir «esto ha avanzado» sin inventarse una escala. El
# orden es el de la realidad: primero se pide, después se concede y solo al final entra el dinero.
ORDEN_DE_LOS_ESTADOS_DE_UNA_SUBVENCION: dict[str, int] = {
    PREVISTA: 0,
    CONCEDIDA: 1,
    COBRADA: 2,
}


def estado_de_una_subvencion(*, prevista: bool, concedida: bool, cobrada: bool) -> str:
    """En qué punto está una ayuda. El orden de las preguntas es el del expediente.

    Se contesta con el estado **más avanzado** de los tres que consten, y no con el primero: una
    ayuda concedida no deja de estar concedida porque además se haya pedido. Y una ayuda de la que no
    consta nada no es «prevista»: es que no se sabe, y eso se dice con una cadena vacía.
    """
    if cobrada:
        return COBRADA
    if concedida:
        return CONCEDIDA
    if prevista:
        return PREVISTA
    return ""


def ingreso_cobrado_de_subvenciones(subvenciones: list[dict]) -> Decimal:
    """El dinero de ayudas que **ha entrado de verdad**. La previsión no entra aquí, y es a propósito.

    Cada subvención es un diccionario con `importe` (o `None`) y `estado`. Solo suman las que están
    `cobrada`. Una ayuda concedida pero no cobrada **no es un ingreso**: es un derecho, y se enseña
    aparte, con su palabra. Y un importe que no consta no suma cero: no suma.
    """
    total = dinero.CERO
    for subvencion in subvenciones:
        if (subvencion.get("estado") or "") != COBRADA:
            continue
        total = dinero.suma(total, dinero.a_decimal(subvencion.get("importe")))
    return total


def importe_previsto_de_subvenciones(subvenciones: list[dict]) -> Decimal:
    """Lo que se espera cobrar y **todavía no ha entrado**. Se dice aparte, nunca sumado al ingreso."""
    total = dinero.CERO
    for subvencion in subvenciones:
        if (subvencion.get("estado") or "") == COBRADA:
            continue
        total = dinero.suma(total, dinero.a_decimal(subvencion.get("importe")))
    return total


# --------------------------------------------------------------------------
# 9. El coste de las averías (lo que el T14 dejó declarado como del T13)
# --------------------------------------------------------------------------
#
# El T14 apuntó **qué** se rompió, cuándo y si ya está arreglado, y dejó escrito que **el coste es de
# este ticket** (`docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`, fila del T14). Y el coste no se apunta en
# la avería: **es un gasto** —con su factura y su pago, como cualquier otro— que además dice de qué
# avería salió. Hay dos motivos, y los dos importan:
#
#   1. **Un importe en dos sitios acaba diciendo dos cosas.** Si la avería guardara su coste y además
#      existiera la factura del taller, el día que se corrija una de las dos cifras el programa
#      tendría dos verdades sobre el mismo dinero.
#   2. **La reparación se reparte como cualquier otro gasto**: por área entre las tierras en las que
#      trabaja esa máquina, o sin asignar. Guardarlo dentro de la avería lo dejaría fuera de las
#      cuentas por tierra, que es justo lo que el contrato pide en S13.
#
# Y una regla que se ve en las pruebas: **una avería con su coste no está arreglada por eso**.
# «Arreglada» es un dato del taller y «coste» es un dato de la cuenta; una reparación de 900 € puede
# estar pagada y la máquina seguir en el taller, y al revés.


@dataclass
class CosteDeUnaAveria:
    """Lo que ha costado una avería, con lo que no se sabe dicho aparte."""

    averia_id: int | None = None
    # **`None` cuando no consta ningún gasto de esa avería.** No es un cero: es que no hay ningún
    # apunte de lo que costó, y un cero diría que la reparación salió gratis.
    coste: Decimal | None = None
    gastos: int = 0
    # Cuántos de esos gastos no tienen importe. Sin este número, un coste que solo suma la mitad
    # parecería el coste entero.
    sin_importe: int = 0
    # Lo que de esa avería está en la campaña, separado por dónde se ha puesto.
    directo: Decimal = dinero.CERO
    repartido: Decimal = dinero.CERO
    sin_asignar: Decimal = dinero.CERO
    arreglada: bool | None = None

    def completo(self) -> bool:
        """¿Se sabe **todo** lo que costó? Es lo que decide si un margen puede ser completo."""
        return self.gastos > 0 and self.sin_importe == 0 and self.coste is not None

    def como_dict(self) -> dict:
        return {
            "averia_id": self.averia_id,
            "coste": dinero.a_texto(self.coste),
            "gastos": self.gastos,
            "sin_importe": self.sin_importe,
            "directo": dinero.a_texto(self.directo),
            "repartido": dinero.a_texto(self.repartido),
            "sin_asignar": dinero.a_texto(self.sin_asignar),
            "arreglada": self.arreglada,
            "completo": self.completo(),
        }


def coste_de_una_averia(
    gastos: list[dict] | None, *, averia_id: int | None = None, arreglada: bool | None = None
) -> CosteDeUnaAveria:
    """Suma los gastos de una avería, separando lo directo, lo repartido y lo sin asignar.

    Cada gasto es un diccionario con `importe` (o `None`), `clase` (`directo`, `repartido` o
    `sin_asignar`) y `anulado`. Un gasto anulado **no cuenta**: sigue en el cuaderno, tachado y con
    su motivo, pero el coste que revirtió no se suma.

    **Y un gasto sin importe no suma cero: se cuenta.** El coste que se enseña es el de lo que
    consta, y `sin_importe` dice cuántos gastos no entraron. Es la diferencia entre «esta reparación
    costó 900 €» y «de esta reparación constan 900 € y hay un gasto del que no se sabe el importe».
    """
    coste = CosteDeUnaAveria(averia_id=averia_id, arreglada=arreglada)
    for gasto in gastos or []:
        if gasto.get("anulado"):
            continue
        coste.gastos += 1
        importe = dinero.a_decimal(gasto.get("importe"))
        if importe is None:
            coste.sin_importe += 1
            continue
        coste.coste = dinero.suma(coste.coste, importe)
        clase = gasto.get("clase") or DIRECTO
        if clase == REPARTIDO:
            coste.repartido = dinero.suma(coste.repartido, importe)
        elif clase == SIN_ASIGNAR_CLASE:
            coste.sin_asignar = dinero.suma(coste.sin_asignar, importe)
        else:
            coste.directo = dinero.suma(coste.directo, importe)
    return coste


def coste_de_las_averias(gastos: list[dict] | None) -> dict[int, CosteDeUnaAveria]:
    """El coste de **cada** avería de una máquina o de la finca, para poder enseñarlas una a una.

    Se agrupa por `averia_id`, así que un gasto que no salga de ninguna avería (una reparación sin
    avería apuntada, que es lo normal cuando se arregla lo que no se había apuntado) se queda fuera
    y se dice: `sin_averia`.
    """
    por_averia: dict[int, CosteDeUnaAveria] = {}
    sin_averia = 0
    for gasto in gastos or []:
        if gasto.get("anulado"):
            continue
        averia_id = gasto.get("averia_id")
        if averia_id is None:
            sin_averia += 1
            continue
        suyo = por_averia.get(int(averia_id))
        if suyo is None:
            suyo = CosteDeUnaAveria(averia_id=int(averia_id))
            por_averia[int(averia_id)] = suyo
        suyo.gastos += 1
        importe = dinero.a_decimal(gasto.get("importe"))
        if importe is None:
            suyo.sin_importe += 1
            continue
        suyo.coste = dinero.suma(suyo.coste, importe)
        clase = gasto.get("clase") or DIRECTO
        if clase == REPARTIDO:
            suyo.repartido = dinero.suma(suyo.repartido, importe)
        elif clase == SIN_ASIGNAR_CLASE:
            suyo.sin_asignar = dinero.suma(suyo.sin_asignar, importe)
        else:
            suyo.directo = dinero.suma(suyo.directo, importe)
    if sin_averia:
        # Se devuelve también, con la clave `-1`, para que el informe pueda decir cuántos gastos de
        # reparación no cuelgan de ninguna avería (y así nadie crea que el coste de las averías es
        # todo lo que se ha gastado en reparaciones).
        por_averia[-1] = CosteDeUnaAveria(averia_id=None, gastos=sin_averia)
    return por_averia


# --------------------------------------------------------------------------
# 10. El margen y la caja: dos tarjetas distintas, y una puede estar incompleta
# --------------------------------------------------------------------------
#
# El contrato lo pide dos veces y con las mismas palabras: «Margen operativo y caja tienen tarjetas
# distintas» (S13) y «Sin cuentas completas mostrar "Con los importes registrados", no beneficio
# total de la explotación» (S01). Y la parte que más importa de este ticket: «**no construir un
# margen con datos que faltan**».
#
# Son dos cosas distintas de verdad:
#
#   · el **margen operativo** es lo que ha costado y lo que se ha ganado **con lo que consta**, tenga
#     el dinero entrado o no. Es la cuenta de si la campaña ha salido a cuenta.
#   · la **caja** es el dinero que hay y lo que ha entrado y salido de verdad, hoy. Un agricultor
#     puede tener un margen bueno y la caja vacía (todo vendido y sin cobrar), y al revés.
#
# Mezclarlas es «mentir con números» —así lo dice el contrato— porque la respuesta a «¿gano dinero?»
# y a «¿puedo pagar el gasóleo?» no es la misma.


@dataclass
class CosteDeUnConcepto:
    """Lo que un cultivo (o una tierra, o una máquina) ha costado y ha dejado, con sus tres columnas.

    Las tres columnas son las que el contrato pide enseñar por separado en S13, y **no se suman en
    una sola cifra sin decirlo**: un coste directo es lo que pone el papel y uno repartido es una
    estimación acordada con el agricultor, y son dos cosas de fiabilidad distinta.
    """

    concepto: str
    directos: Decimal = dinero.CERO
    repartidos: Decimal = dinero.CERO
    sin_asignar: Decimal = dinero.CERO
    ingresos: Decimal = dinero.CERO
    # Cuántos costes de este concepto **no tienen importe**. Es lo que decide si el margen se puede
    # enseñar: con uno de estos, el margen **no se calcula** y se dice.
    costes_que_no_se: int = 0
    ingresos_que_no_se: int = 0
    # Lo que se ha cobrado de esos ingresos, que es lo que va a la caja (y no al margen).
    cobrado: Decimal = dinero.CERO

    def coste_conocido(self) -> Decimal:
        return dinero.suma(self.directos, self.repartidos, self.sin_asignar)

    def completo(self) -> bool:
        """¿Se puede calcular el margen? Solo si **no falta ni un importe** por saber.

        Es la regla que más importa de este ticket: da igual que falte un coste de 20 € o de
        20.000 €. Mientras falte uno, el margen no se calcula: se enseña lo que consta y se dice que
        está incompleto.
        """
        return self.costes_que_no_se == 0 and self.ingresos_que_no_se == 0

    def margen(self) -> Decimal | None:
        """Lo que queda, o `None` si no se puede saber. **Nunca un cero que parezca un resultado.**"""
        if not self.completo():
            return None
        return dinero.redondea(self.ingresos - self.coste_conocido())

    def como_dict(self) -> dict:
        return {
            "concepto": self.concepto,
            "directos": dinero.a_texto(self.directos),
            "repartidos": dinero.a_texto(self.repartidos),
            "sin_asignar": dinero.a_texto(self.sin_asignar),
            "coste_conocido": dinero.a_texto(self.coste_conocido()),
            "ingresos": dinero.a_texto(self.ingresos),
            "cobrado": dinero.a_texto(self.cobrado),
            "margen": dinero.a_texto(self.margen()),
            "completo": self.completo(),
            "costes_que_no_se": self.costes_que_no_se,
            "ingresos_que_no_se": self.ingresos_que_no_se,
        }


def margen_por_concepto(
    costes: list[dict] | None, ingresos: list[dict] | None
) -> dict[str, CosteDeUnConcepto]:
    """El margen por cultivo, por tierra o por máquina: una entrada por concepto.

    Cada **coste** es un diccionario con `concepto`, `importe` (o `None`) y `clase` (`directo`,
    `repartido` o `sin_asignar`). Cada **ingreso** lleva `concepto`, `importe` (o `None`) y `cobrado`
    (lo que de verdad ha entrado).

    **Los tres errores que esto cierra, y que son el ticket entero:**

      1. **Un importe que no consta no suma cero**: se cuenta en `costes_que_no_se` y el margen de
         ese concepto se queda en `None`.
      2. **Un coste sin asignar sigue siendo un coste conocido**: aparece en su columna y suma en
         `coste_conocido`, así que el total no se queda corto por no saber a quién cargárselo.
      3. **Lo cobrado no es lo ganado**: `ingresos` es lo registrado (para el margen) y `cobrado` es
         lo que ha entrado (para la caja), y son dos columnas distintas.
    """
    cuenta: dict[str, CosteDeUnConcepto] = {}

    def _de(concepto: str) -> CosteDeUnConcepto:
        clave = concepto or ""
        if clave not in cuenta:
            cuenta[clave] = CosteDeUnConcepto(concepto=clave)
        return cuenta[clave]

    for coste in costes or []:
        suyo = _de(str(coste.get("concepto") or ""))
        importe = dinero.a_decimal(coste.get("importe"))
        if importe is None:
            suyo.costes_que_no_se += 1
            continue
        clase = coste.get("clase") or DIRECTO
        if clase == REPARTIDO:
            suyo.repartidos = dinero.suma(suyo.repartidos, importe)
        elif clase == SIN_ASIGNAR_CLASE:
            suyo.sin_asignar = dinero.suma(suyo.sin_asignar, importe)
        else:
            suyo.directos = dinero.suma(suyo.directos, importe)

    for ingreso in ingresos or []:
        suyo = _de(str(ingreso.get("concepto") or ""))
        importe = dinero.a_decimal(ingreso.get("importe"))
        if importe is None:
            suyo.ingresos_que_no_se += 1
            continue
        suyo.ingresos = dinero.suma(suyo.ingresos, importe)
        suyo.cobrado = dinero.suma(suyo.cobrado, dinero.a_decimal(ingreso.get("cobrado")) or dinero.CERO)

    return cuenta


@dataclass
class Caja:
    """El dinero que hay y el que se ha movido. **No es el margen, y por eso es otro tipo.**

    Los tres números que la hacen útil y que no salen del margen: lo que ha entrado de verdad, lo que
    ha salido de verdad y lo que se debe (a proveedores) y le deben (clientes). Un agricultor con
    50.000 € de margen y 30.000 € pendientes de cobro tiene un problema de caja que el margen no
    enseña.
    """

    entrado: Decimal = dinero.CERO
    salido: Decimal = dinero.CERO
    por_cobrar: Decimal = dinero.CERO
    por_pagar: Decimal = dinero.CERO
    # Las ayudas que se esperan y **no han entrado**. Van aquí, aparte, y no dentro de `entrado`: es
    # la mitad del contrato que dice que la previsión no se suma al ingreso cobrado.
    ayudas_previstas: Decimal = dinero.CERO
    ayudas_cobradas: Decimal = dinero.CERO
    importes_que_no_se: int = 0

    def saldo(self) -> Decimal:
        return dinero.redondea(self.entrado - self.salido)

    def como_dict(self) -> dict:
        return {
            "entrado": dinero.a_texto(self.entrado),
            "salido": dinero.a_texto(self.salido),
            "saldo": dinero.a_texto(self.saldo()),
            "por_cobrar": dinero.a_texto(self.por_cobrar),
            "por_pagar": dinero.a_texto(self.por_pagar),
            "ayudas_previstas": dinero.a_texto(self.ayudas_previstas),
            "ayudas_cobradas": dinero.a_texto(self.ayudas_cobradas),
            "importes_que_no_se": self.importes_que_no_se,
        }


def caja(
    *,
    cobros: list[dict] | None = None,
    pagos: list[dict] | None = None,
    por_cobrar: list[Decimal | None] | None = None,
    por_pagar: list[Decimal | None] | None = None,
    subvenciones: list[dict] | None = None,
) -> Caja:
    """La caja: lo que ha entrado, lo que ha salido y lo que está pendiente. **Sin contar previsiones.**

    Un cobro o un pago **anulado** no cuenta (revirtió su efecto y sigue en el cuaderno, tachado).
    Un importe que no consta no suma cero: se cuenta en `importes_que_no_se`, porque un saldo que
    calla que le faltan movimientos es un saldo que miente.
    """
    cuenta = Caja()
    for cobro in cobros or []:
        if cobro.get("anulado"):
            continue
        importe = dinero.a_decimal(cobro.get("importe"))
        if importe is None:
            cuenta.importes_que_no_se += 1
            continue
        cuenta.entrado = dinero.suma(cuenta.entrado, importe)
    for pago in pagos or []:
        if pago.get("anulado"):
            continue
        importe = dinero.a_decimal(pago.get("importe"))
        if importe is None:
            cuenta.importes_que_no_se += 1
            continue
        cuenta.salido = dinero.suma(cuenta.salido, importe)
    for importe in por_cobrar or []:
        cuenta.por_cobrar = dinero.suma(cuenta.por_cobrar, importe)
    for importe in por_pagar or []:
        cuenta.por_pagar = dinero.suma(cuenta.por_pagar, importe)
    cuenta.ayudas_cobradas = ingreso_cobrado_de_subvenciones(subvenciones or [])
    cuenta.ayudas_previstas = importe_previsto_de_subvenciones(subvenciones or [])
    return cuenta


@dataclass
class CuentaDeLaExplotacion:
    """El resumen de la pantalla de cuentas, con los cinco registros separados y contados.

    **Los cinco contadores no se mezclan, y ese es el punto.** Es la forma de poder comprobar en una
    prueba que conciliar un pago no cambia el número de gastos y que recibir un traspaso no cambia el
    número de ingresos: si fueran una sola cuenta, el fallo no se vería.
    """

    gastos: int = 0
    inversiones: int = 0
    facturas: int = 0
    pagos: int = 0
    movimientos: int = 0
    gastos_sin_importe: int = 0
    coste_conocido: Decimal = dinero.CERO
    pagado: Decimal = dinero.CERO
    pendiente: Decimal | None = dinero.CERO
    sin_asignar: Decimal = dinero.CERO
    # Cuántos gastos han quedado sin repartir, y por qué. Se cuenta aquí para que el pie de la lista
    # pueda decir «hay 3 sin saber a qué van» en vez de enseñar un total que parece completo.
    sin_asignar_cuantos: int = 0
    margen: Decimal | None = None
    margen_completo: bool = False

    def como_dict(self) -> dict:
        return {
            "gastos": self.gastos,
            "inversiones": self.inversiones,
            "facturas": self.facturas,
            "pagos": self.pagos,
            "movimientos": self.movimientos,
            "gastos_sin_importe": self.gastos_sin_importe,
            "coste_conocido": dinero.a_texto(self.coste_conocido),
            "pagado": dinero.a_texto(self.pagado),
            "pendiente": dinero.a_texto(self.pendiente),
            "sin_asignar": dinero.a_texto(self.sin_asignar),
            "sin_asignar_cuantos": self.sin_asignar_cuantos,
            "margen": dinero.a_texto(self.margen),
            "margen_completo": self.margen_completo,
        }


def cuenta_de_la_explotacion(
    *,
    gastos: list[dict] | None = None,
    inversiones: list[dict] | None = None,
    facturas: list[dict] | None = None,
    pagos: list[dict] | None = None,
    movimientos: list[dict] | None = None,
    trozos_de_reparto: list[dict] | None = None,
    ingresos: Decimal | None = None,
) -> CuentaDeLaExplotacion:
    """Cierra la cuenta de la finca: qué costó, qué se ha pagado, qué falta y qué está sin asignar.

    **Lo que esta función NO hace, y es lo que la hace servir: no crea nada.** Recibe los cinco
    registros ya existentes y los cuenta. Por eso una prueba puede llamarla antes y después de
    conciliar un pago y exigir que `gastos` no se haya movido: conciliar no crea gastos.
    """
    cuenta = CuentaDeLaExplotacion()
    cuenta.gastos = len(gastos or [])
    cuenta.inversiones = len(inversiones or [])
    cuenta.facturas = len(facturas or [])
    cuenta.pagos = len(pagos or [])
    cuenta.movimientos = len(movimientos or [])

    for gasto in gastos or []:
        if gasto.get("anulado"):
            continue
        importe = dinero.a_decimal(gasto.get("importe"))
        if importe is None:
            cuenta.gastos_sin_importe += 1
            continue
        cuenta.coste_conocido = dinero.suma(cuenta.coste_conocido, importe)

    for pago in pagos or []:
        if pago.get("anulado"):
            continue
        importe = dinero.a_decimal(pago.get("importe"))
        if importe is None:
            continue
        cuenta.pagado = dinero.suma(cuenta.pagado, importe)

    # El pendiente es `None` en cuanto hay un gasto cuyo importe no consta: no se puede decir cuánto
    # falta por pagar de lo que no se sabe cuánto costó. Es la regla del «no lo sé» en el pie de la
    # pantalla, y es la que impide que un total parezca completo cuando no lo está.
    if cuenta.gastos_sin_importe:
        cuenta.pendiente = None
    else:
        falta = dinero.CERO
        for gasto in gastos or []:
            if gasto.get("anulado"):
                continue
            suyo = pendiente_de(gasto.get("importe"), gasto.get("pagado"))
            if suyo is not None:
                falta = dinero.suma(falta, suyo)
        cuenta.pendiente = dinero.redondea(falta)

    for trozo in trozos_de_reparto or []:
        if trozo.get("anulado"):
            continue
        if (trozo.get("destino_tipo") or "") != SIN_ASIGNAR:
            continue
        importe = dinero.a_decimal(trozo.get("importe"))
        if importe is None:
            continue
        cuenta.sin_asignar = dinero.suma(cuenta.sin_asignar, importe)
        cuenta.sin_asignar_cuantos += 1

    # El margen de la finca se calcula sumando los de cada concepto, y solo sale si **todos** están
    # completos: un margen total con un cultivo incompleto sería un número que parece un resultado.
    # La cuenta no depende del día: el vencimiento se mira gasto a gasto, en su propio estado.
    if ingresos is not None:
        completo = cuenta.gastos_sin_importe == 0
        cuenta.margen_completo = completo
        cuenta.margen = dinero.redondea(ingresos - cuenta.coste_conocido) if completo else None
    return cuenta
