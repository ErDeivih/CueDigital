"""Lo que se vende: la cuenta de una entrega, de una factura nuestra y de un cobro.

## Qué separa este módulo, y por qué es lo primero del ticket

El contrato (§4, S12) empieza con una frase que es la entrega entera: **«Separar lote cosechado,
entrega/albarán, factura emitida y cobro»**. No son lo mismo y hasta hoy el programa los trataba
como si lo fueran (o, más exactamente, solo tenía el segundo y llamaba «venta» a todo):

  · **El lote cosechado** es lo que se recogió de la tierra: kilos de trigo de una parcela, un día.
    Ya existe en este programa y **no se duplica**: es la labor de tipo cosecha (`/api/cosecha`),
    con su producto y su cantidad. Una entrega dice de qué cosecha salió.
  · **La entrega (el albarán)** es lo que sale de la finca: a quién, cuánto, qué día y con qué
    número de papel. Es la tabla `ventas_de_cosecha` de siempre, que se queda donde está.
  · **La factura emitida** es un documento **nuestro**, de gestión, que agrupa una o varias
    entregas. Aquí no se emite ningún documento fiscal: el contrato dice que eso «requiere
    especificación normativa propia antes de activarse como tal», y este módulo no lo hace.
  · **El cobro** es el dinero que entra, y puede ser parcial. Es el único de los cuatro que es
    dinero cobrado, en vez de dinero prometido.

## La regla que gobierna todo lo de arriba: **el dinero se cuenta una vez**

De las tres formas en que un programa duplica ingresos, este módulo cierra las tres, y las tres
tienen su prueba:

1. **Al agrupar varias entregas en una factura.** El importe de la factura **es la suma de sus
   líneas**, no un número aparte que se pueda solapar con ellas. Y una entrega viva solo puede estar
   en una factura viva: lo impide un índice único en la base, no una comprobación amable.
2. **Al reenviar la misma entrega o el mismo cobro** (el móvil sin cobertura, un botón pulsado dos
   veces). Cada uno lleva su clave de reenvío y reenviar devuelve lo que ya había.
3. **Al cobrar.** Un cobro se imputa a **una** factura y con **una** cantidad (`importe_imputado`),
   así que el mismo dinero no puede estar contado en dos facturas. Un pago más grande que lo que se
   debe **no** deja la factura con pendiente negativo: lo que sobra queda dicho como «sin
   conciliar», a la espera de saber a qué va.

## Y lo que no se sabe, no se convierte en cero

Es el caso A08 del contrato y la regla de siempre del proyecto. Una venta de 8.000 kg **sin precio**
tiene cantidad conocida e **importe pendiente**: no es un ingreso de cero euros ni un ingreso
«supuesto». Aquí eso es un estado (`SIN_IMPORTE`), no un `0.00`, y el total de una pantalla que
suma importes **dice cuántos no se saben**.

## Este módulo no toca la base de datos

Son cuentas puras, con sus pruebas, como `legal.py`: se pueden probar sin servidor y sin esquema, y
por eso se puede comprobar con números que fallarían si el dinero fuera de coma flotante.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from . import dinero

# --------------------------------------------------------------------------
# Los estados de una entrega: seis, y cada uno dice qué hacer
# --------------------------------------------------------------------------
#
# Seis y no tres, porque cada uno es una cosa distinta para el agricultor y solo uno de ellos se
# arregla igual que otro:
#
#   · `sin_importe`   — se apuntaron los kilos y no se sabe por cuánto (A08). Lo que hay que hacer
#                       es poner el precio o el importe, no cobrar.
#   · `sin_facturar`  — hay importe y no está en ninguna factura nuestra. Lo que hay que hacer es
#                       facturarla (sola o con otras).
#   · `sin_cobrar`    — está en una factura y no ha entrado nada. Si pasó la fecha de vencimiento,
#                       el estado es `vencida`, que es el que hay que mirar de verdad.
#   · `cobrada_en_parte` — entró algo y falta algo. Es el caso A06 (121 € facturados, 40 € cobrados).
#   · `cobrada`       — no falta nada.
#   · `vencida`       — falta algo y ya pasó el día acordado. Se dice aparte de `sin_cobrar` porque
#                       es lo único de esta pantalla que exige una llamada de teléfono.
SIN_IMPORTE = "sin_importe"
SIN_FACTURAR = "sin_facturar"
SIN_COBRAR = "sin_cobrar"
COBRADA_EN_PARTE = "cobrada_en_parte"
COBRADA = "cobrada"
VENCIDA = "vencida"

ESTADOS = (
    SIN_IMPORTE,
    SIN_FACTURAR,
    SIN_COBRAR,
    COBRADA_EN_PARTE,
    COBRADA,
    VENCIDA,
)

# Los estados en los que todavía falta dinero **por cobrar**, que es lo que suma el pie de la tabla
# de pendientes. `sin_importe` no entra: no se sabe si falta algo, y meterlo como cero sería
# inventarse una cifra. Es la mitad financiera de la regla del A08.
ESTADOS_CON_PENDIENTE = (SIN_COBRAR, COBRADA_EN_PARTE, VENCIDA)


def estado_de_una_entrega(
    *,
    importe: Decimal | None,
    cobrado: Decimal | None,
    facturada: bool,
    vencimiento,
    hoy,
) -> str:
    """En qué estado está una entrega. Es una función pura: sus tres primeras pruebas son A06 y A08.

    El orden de las preguntas importa y es el del agricultor: primero «¿sé por cuánto?» (si no, no
    hay nada que cobrar), después «¿está en una factura?» (si no, todavía no se ha pedido el dinero)
    y solo entonces «¿me lo han pagado?».
    """
    conocido = dinero.a_decimal(importe)
    if conocido is None:
        return SIN_IMPORTE
    if not facturada:
        return SIN_FACTURAR
    # Lo recibido, con el hueco ya resuelto: un cobro que no se sabe (`None` o vacío) es cero
    # **recibido**, que aquí sí es la verdad —no hay ningún apunte de dinero a su favor—, y no se
    # confunde con un importe que no se sabe, que es otra cosa y se ha mirado tres líneas más arriba.
    recibido = dinero.a_decimal(cobrado) or dinero.CERO
    pendiente = pendiente_de(conocido, recibido)
    if pendiente is not None and pendiente <= 0:
        return COBRADA
    if recibido > 0:
        # Se cobró algo y sigue faltando algo: es A06 (121 facturados, 40 cobrados → faltan 81).
        # Que además esté vencida no cambia lo que hay que hacer —cobrar el resto—, así que el
        # estado se queda en «a medias» y el aviso de vencimiento va aparte, como dato de la fila.
        return COBRADA_EN_PARTE
    if vencimiento is not None and hoy is not None and vencimiento < hoy:
        return VENCIDA
    return SIN_COBRAR


def pendiente_de(importe: Decimal | None, cobrado: Decimal | None) -> Decimal | None:
    """Lo que falta por cobrar. `None` si no se sabe el importe; **nunca negativo**.

    Se dice «nunca negativo» porque es una decisión y no un descuido: si alguien cobró de más (una
    indemnización, un redondeo del comprador), el pendiente es `0,00 €` y el sobrante se dice aparte
    como dinero sin conciliar. Un pendiente de `-5,00 €` en una pantalla de cuentas no significa
    nada para quien la lee y hace imposible sumar la columna.
    """
    if importe is None:
        return None
    resto = dinero.resta(dinero.a_decimal(importe), dinero.a_decimal(cobrado) or dinero.CERO)
    if resto is None:
        return None
    return resto if resto > 0 else dinero.CERO


def importe_de_una_entrega(
    *,
    importe: Decimal | None,
    cantidad: Decimal | None,
    precio_unitario: Decimal | None,
    ajustes: list[Decimal] | None = None,
) -> Decimal | None:
    """El importe de una entrega: el que se escribió, o cantidad × precio, o **no se sabe**.

    Las tres reglas, y por qué en ese orden:

    1. **Lo que el agricultor escribió manda.** Si él vio el papel del comprador y pone 1.205,40 €,
       ese es el importe aunque la multiplicación dé otra cosa por medio céntimo. El programa no
       corrige lo que pone el papel de enfrente: la aritmética es para comprobar, no para mandar.
    2. **Si no lo escribió pero sabe el precio**, se multiplica: cantidad × precio, redondeando
       **una sola vez**, al final (ver `dinero.producto`).
    3. **Si no sabe ni una cosa ni la otra, el importe no se sabe.** Aquí está el A08: `None`, no
       `0.00`. Un cero sería un ingreso de cero euros en las cuentas del año, que es falso.

    `ajustes` son los deltas de las devoluciones y los ajustes de peso, humedad o calidad (T12). Se
    **suman al importe** y no recalculan el precio: una merma de humedad se acuerda en euros o en
    kilos sobre el total, no cambiando el precio del kilo, y recalcularlo convertiría un ajuste de
    calidad en una subida de precio encubierta.
    """
    base = dinero.a_decimal(importe)
    if base is None:
        base = dinero.producto(
            dinero.cantidad_a_decimal(cantidad), dinero.a_decimal(precio_unitario)
        )
    if base is None:
        return None
    if not ajustes:
        return dinero.redondea(base)
    return dinero.redondea(dinero.suma(base, *ajustes))


def cantidad_neta(cantidad: Decimal | None, ajustes_de_cantidad: list[Decimal] | None) -> Decimal | None:
    """Los kilos que de verdad se quedó el comprador, con los ajustes aplicados.

    **Un ajuste sin cantidad no cambia esta cuenta, y es lo correcto**: un ajuste de calidad
    acordado en euros no mueve ni un kilo. Y una cantidad que no se sabe sigue sin saberse: un
    ajuste sobre una entrega sin kilos no puede convertirla en una entrega de kilos.
    """
    if cantidad is None:
        return None
    if not ajustes_de_cantidad:
        return cantidad
    return dinero.redondea(dinero.suma(cantidad, *ajustes_de_cantidad), 4)


def reparto_de_un_cobro(importe: Decimal | None, pendiente: Decimal | None) -> tuple[Decimal, Decimal]:
    """Cuánto de un cobro se imputa a una factura y cuánto queda sin conciliar: `(imputado, sobrante)`.

    La cuenta es corta y hace falta que sea exacta: si entran 100 € y se deben 81 €, a la factura
    van **81** y quedan 19 sin conciliar (a espera de saber a qué factura van o de devolverlos). Lo
    que **no** se hace es dejar la factura en `-19`: un pendiente negativo no se puede sumar con los
    demás y no significa nada.

    Sin conciliar no quiere decir perdido: el cobro sigue apuntado con su importe entero, y la
    pantalla dice las dos cifras (lo imputado y lo que sobra), que es la única forma de que una
    cuenta cuadre sin inventarse nada.
    """
    entrante = dinero.a_decimal(importe) or dinero.CERO
    debido = dinero.a_decimal(pendiente)
    if debido is None or debido <= 0:
        return (dinero.CERO, dinero.redondea(entrante) or dinero.CERO)
    imputado = entrante if entrante <= debido else debido
    return (dinero.redondea(imputado), dinero.redondea(entrante - imputado))


def reparto_de_lo_cobrado(importes: list[Decimal | None], cobrado: Decimal | None) -> list[Decimal]:
    """Reparte el dinero cobrado de una factura entre sus entregas: `[lo de cada una]`.

    ## Por qué hace falta esto, y por qué se hace así

    Una factura puede llevar dentro varias entregas, y el dinero que entra es **de la factura**, no
    de una entrega concreta. Pero la pantalla de S12 enseña una fila por entrega con su «cobrado» y
    su «pendiente», y el ticket exige que **la suma de las filas dé el número del resumen**. Con el
    importe cobrado repetido en cada fila (lo fácil) la suma daría el triple en una factura de tres
    entregas, y con un reparto por porcentaje el programa se estaría inventando céntimos.

    La regla, que es la de cualquier cuenta corriente y no tiene nada de inventada: **lo cobrado se
    aplica a las entregas por orden, la más antigua primero**, y a cada una se le pone lo que le
    falta hasta completarla. Así:

      · cada entrega lleva **su** cobrado y **su** pendiente, y ninguno se repite;
      · la suma de las filas es exactamente lo cobrado de la factura (probado con A06);
      · y no hay ningún reparto por proporción, que es donde aparecerían los céntimos perdidos.

    El orden de la lista es el de las entregas (el que le pase quien llama, que las ordena por
    fecha). Si sobra dinero —se cobró más que el total de la factura—, el sobrante **no se reparte**:
    se queda en la factura como «sin conciliar», porque no es de ninguna entrega en concreto.
    """
    entrante = dinero.a_decimal(cobrado) or dinero.CERO
    reparto: list[Decimal] = []
    queda = entrante
    for importe in importes:
        suyo = dinero.a_decimal(importe)
        if suyo is None or suyo <= 0:
            # Una entrega sin importe conocido no puede llevar cobrado: no se sabe contra qué se
            # aplicaría. Su pendiente tampoco se puede calcular, y eso es la verdad (A08).
            reparto.append(dinero.CERO)
            continue
        if queda <= 0:
            reparto.append(dinero.CERO)
            continue
        puesto = suyo if suyo <= queda else queda
        reparto.append(dinero.redondea(puesto))
        queda = dinero.redondea(queda - puesto)
    return reparto


# --------------------------------------------------------------------------
# Los ajustes: devolución, peso, humedad y calidad
# --------------------------------------------------------------------------
#
# Cuatro tipos y no uno, porque **se dicen de cuatro maneras en el campo y se prueban de cuatro
# maneras**: una devolución es mercancía que vuelve, y un ajuste de humedad es un acuerdo sobre el
# precio de lo que ya se llevaron. Meterlos todos en «ajuste» obligaría a explicarlo en un texto
# libre, y un texto libre no se puede sumar ni contar.
TIPOS_DE_AJUSTE = ("devolucion", "peso", "humedad", "calidad")

# De dónde sale el número. Es una **lista cerrada** y es lo que impide el fallo que el ticket quiere
# evitar: «no un número suelto que cambie el importe sin decir de dónde sale». «otro» existe, y
# obliga a escribir el motivo; lo que no existe es dejarlo sin decir.
ORIGENES_DE_UN_AJUSTE = ("cliente", "bascula", "laboratorio", "acuerdo", "otro")

# Cómo entra el dinero. Es una lista nuestra y se dice: no hay ningún catálogo oficial de formas de
# cobro cargado en el programa, así que son las que aparecen en un papel de verdad.
FORMAS_DE_COBRO = ("transferencia", "efectivo", "cheque", "confirming", "otro")


@dataclass
class CuentaDeDinero:
    """Lo que suma un conjunto de entregas, con lo que no se sabe dicho aparte.

    Es el pie de la tabla de S12 y lo que hace que el resumen se pueda comparar con el detalle: los
    cuatro números salen de las **mismas** filas que se están enseñando (el servidor calcula el
    agregado del conjunto filtrado, como pide el contrato §3), no de una consulta distinta que
    podría decir otra cosa.
    """

    importe: Decimal = dinero.CERO
    facturado: Decimal = dinero.CERO
    cobrado: Decimal = dinero.CERO
    pendiente: Decimal = dinero.CERO
    entregas: int = 0
    # Cuántas entregas **no** entran en los totales por no saberse su importe. Sin este número, el
    # pie sería mentira por omisión: sumaría lo que hay y parecería completo.
    sin_importe: int = 0
    # Y cuántas están facturadas pero todavía sin cobrar del todo, que es lo que se ha venido a
    # mirar en esta pantalla.
    por_cobrar: int = 0
    estado_por_entrega: dict[int, str] = field(default_factory=dict)

    def como_dict(self) -> dict:
        """Los números ya en su forma de texto, que es como viajan (contrato §2)."""
        return {
            "importe": dinero.a_texto(self.importe),
            "facturado": dinero.a_texto(self.facturado),
            "cobrado": dinero.a_texto(self.cobrado),
            "pendiente": dinero.a_texto(self.pendiente),
            "entregas": self.entregas,
            "sin_importe": self.sin_importe,
            "por_cobrar": self.por_cobrar,
        }


def cuenta_de_dinero(filas: list[dict]) -> CuentaDeDinero:
    """Suma una lista de entregas ya contadas (cada una un diccionario con sus importes).

    Cada fila trae: `importe` (o `None`), `cobrado` (lo que se le ha imputado) y `facturada`. Los
    tres pueden faltar y ninguno se convierte en cero por su cuenta.

    **La distinción que hace que esto sirva**: `facturado` cuenta el importe de lo que está en una
    factura nuestra, `cobrado` el dinero que ha entrado y `pendiente` lo que falta **de lo
    facturado**. Una entrega con importe pero sin facturar suma en `importe` y **no** en
    `pendiente`: no es que no se lo deban, es que todavía no se le ha pedido.
    """
    cuenta = CuentaDeDinero()
    for fila in filas:
        cuenta.entregas += 1
        importe = dinero.a_decimal(fila.get("importe"))
        if importe is None:
            cuenta.sin_importe += 1
            continue
        cuenta.importe = dinero.suma(cuenta.importe, importe)
        if not fila.get("facturada"):
            continue
        cuenta.facturado = dinero.suma(cuenta.facturado, importe)
        cobrado = dinero.a_decimal(fila.get("cobrado")) or dinero.CERO
        cuenta.cobrado = dinero.suma(cuenta.cobrado, cobrado)
        falta = pendiente_de(importe, cobrado)
        cuenta.pendiente = dinero.suma(cuenta.pendiente, falta)
        if falta and falta > 0:
            cuenta.por_cobrar += 1
    return cuenta
