"""El dinero: céntimos exactos, sin coma flotante en ningún paso.

## Por qué existe este módulo (T12, E6)

Hasta este ticket el programa **no guardaba ni un importe de venta**: lo que se apuntaba de una
entrega era el producto, la cantidad y el día, y el precio estaba en otra parte que no se había
construido. Con el dinero entran tres formas de perder céntimos que en un cuaderno de campo no se
notan hasta que el agricultor echa la cuenta con su libreta, y las tres se cierran aquí:

1. **Sumar con números de coma flotante.** En una máquina, `0,10 + 0,20` **no** da `0,30`: da
   `0,30000000000000004`. Con dos apuntes no se ve; con un año de entregas, el total de la pantalla
   y la suma de las filas dejan de coincidir por unos céntimos, y eso es justo lo que hace
   desconfiar de un programa. Aquí todo se calcula con `decimal.Decimal`, que suma como se suma en
   un papel.
2. **Guardar el importe como número en la base.** La base de este programa es SQLite (y PostgreSQL
   en producción), y SQLite **no tiene un tipo decimal**: un `Numeric` de SQLAlchemy allí acaba
   pasando por `float` (el dialecto lo dice: `supports_native_decimal = False`), o sea, el mismo
   problema que el punto 1 pero escondido dentro del motor. Por eso el importe se guarda como
   **texto decimal canónico** (`"121.00"`), que es exacto en los dos motores, se lee con los ojos y
   no depende de ninguna conversión.
3. **Redondear a euros.** Un pendiente de `80,999` no es `80` ni `81` a ojo: es un céntimo perdido.
   El redondeo se hace **al céntimo** y con una regla escrita (`ROUND_HALF_UP`, la de una factura
   normal: si sobra medio céntimo, se sube), y se prueba con números que fallarían con la regla de
   Python por defecto, que redondea a par.

## Lo que este módulo NO hace, y por qué se dice

- **No convierte monedas.** Aquí todo está en euros y no hay ninguna tabla de cambios. Un importe en
  otra moneda se guardaría como si fuera un euro, así que no se admite: el contrato lo sitúa fuera
  de esta entrega («no se pretende construir contabilidad fiscal certificada»).
- **No decide el importe de un documento.** Solo hace las cuentas. Quién multiplica cantidad por
  precio y cuándo se redondea es una decisión de negocio y está en `app/ventas.py`, con su prueba.
- **No formatea para la pantalla mezclando idiomas.** `formatea` escribe como se escribe un importe
  en España (`1.234,56 €`), y el símbolo se pone aquí y no en el JavaScript por la regla de este
  programa: los textos viven en el servidor.
"""

from __future__ import annotations

import decimal
from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

# **El contexto decimal, fijado una vez y no en cada operación.** Sirve para que una división de
# dos importes (un precio por kilo, un reparto) no arrastre la precisión por defecto del intérprete
# ni cambie según quién ejecute el programa. La precisión es holgada a propósito: lo que se calcula
# a medias no puede perder céntimos antes de redondear.
CONTEXTO = decimal.Context(prec=28)


class ErrorDeDinero(ValueError):
    """Un importe que no se puede aceptar.

    Es una excepción y no un aviso de pantalla a propósito: quien la ve es quien escribe el
    programa (un importe que llega como número de coma flotante, un texto que no es un número).
    Lo que ve el agricultor es el aviso escrito de `validaciones.py`, en sus palabras.
    """


# Cuántos decimales tiene un importe de dinero. Dos, como el céntimo.
DECIMALES_DE_UN_IMPORTE = 2

# Y cuántos puede tener un precio por unidad. **Más de dos, y no es un capricho**: en el campo un
# precio se pacta por kilo y lleva más cifras («0,2350 €/kg»), y redondearlo al céntimo antes de
# multiplicar por 42.000 kg sería un error de decenas de euros. Se guarda con las cifras que se
# pactaron y se redondea **el importe**, que es lo único que se cobra.
DECIMALES_DE_UN_PRECIO = 6

# La precisión del texto guardado en la base: 18 cifras enteras y 6 decimales es lo que aguanta un
# importe grande con las cifras de un precio. Se guarda como texto, así que no hay desbordamiento:
# esto solo evita que se cuele un número con un montón de cifras por un error de quien llama.
MAXIMO_DE_CIFRAS = 24

# **Y hasta dónde puede llegar un importe de verdad, que NO es el tope de la columna.** Esto se añadió en la
# revisión del T12, con un defecto medido delante: `a_texto` no miraba cuántos caracteres devolvía, así que
# un importe de 22 cifras enteras salía como un texto de 27 en una columna de 24. **En SQLite entraba sin
# decir nada; en PostgreSQL fallaba la operación entera** (`StringDataRightTruncation`) y el agricultor veía
# un 500. Es el mismo defecto del `varchar(30)` del rastro, y por la puerta del dinero.
#
# El tope no se pone en el ancho de la columna sino en **lo que puede ser una venta de esta finca**: una
# explotación de Castilla y León no cobra cien millones de euros por una entrega, así que por encima de eso
# hay una cifra de más al teclear (o una multiplicación mal hecha), y el programa lo dice en vez de
# guardarlo. Deja **doce caracteres de holgura** en la columna de 24, para que nadie tenga que volver a
# mirar si cabe.
#
# Y lo mismo con el precio por unidad: un millón de euros por kilo es un error de tecleo, no un precio.
MAXIMO_DE_UN_IMPORTE = Decimal("99999999.99")
MAXIMO_DE_UN_PRECIO = Decimal("999999.999999")

CERO = Decimal("0.00")


def cabe_en_el_dinero(valor: Decimal | None, *, es_precio: bool = False) -> bool:
    """Si ese importe está dentro de lo que puede ser un importe de verdad.

    Es la comprobación que faltaba (revisión del T12): el tope de la columna no es el tope del dinero, y lo
    que no puede pasar es que un número que no cabe se guarde en un motor y reviente en el otro. Quien
    llama decide qué frase darle al agricultor; aquí solo se dice si cabe.
    """
    if valor is None:
        return True
    tope = MAXIMO_DE_UN_PRECIO if es_precio else MAXIMO_DE_UN_IMPORTE
    return abs(valor) <= tope


def a_decimal(valor: object) -> Decimal | None:
    """Un importe en `Decimal`, venga como venga. `None` sigue siendo «no se sabe».

    **Los números de coma flotante se rechazan, y esto es lo importante de la función.** Un
    `float` que llega hasta aquí (un `2.35` escrito en el código, un JSON que mandó un número en vez
    de una cadena) ya perdió la cuenta: `Decimal(2.35)` es `2,350000000000000088817841970012523...`,
    y aceptarlo sería meter la coma flotante por la puerta de atrás justo en el módulo que existe
    para no usarla. El contrato lo pide con estas palabras: «Importes Decimal en servidor y cadenas
    decimales en intercambio; no usar Float para cálculos nuevos».

    Los `bool` también se rechazan: en Python `True` es un `int` que vale 1, y un importe de «sí»
    no es un importe.
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        raise ErrorDeDinero("Un importe no puede ser verdadero o falso.")
    if isinstance(valor, Decimal):
        if not valor.is_finite():
            raise ErrorDeDinero("Un importe no puede ser infinito ni «no es un número».")
        return valor
    if isinstance(valor, int):
        # Un entero sí vale: `121` es exacto en cualquier motor y significa 121 euros.
        return Decimal(valor)
    if isinstance(valor, float):
        raise ErrorDeDinero(
            "Un importe no se acepta como número de coma flotante: mándalo como texto decimal "
            "(por ejemplo \"121.00\"). Un Float ya ha perdido céntimos antes de llegar aquí."
        )
    if isinstance(valor, str):
        return de_texto(valor)
    raise ErrorDeDinero(f"Esto no es un importe: {type(valor).__name__}.")


def de_texto(texto: str | None) -> Decimal | None:
    """Un importe escrito a mano, en `Decimal`. Vacío es «no se sabe» (`None`), no cero.

    Se acepta lo que escribe un agricultor y lo que manda un programa, con **la misma regla que ya
    usa el lector de facturas del programa** (`facturas.numero_espanol`), porque tener dos reglas
    para «qué significa este número» es tener dos verdades: si están los dos separadores, el último
    es el decimal; si solo hay punto y lleva exactamente tres cifras detrás, es un separador de
    miles («1.234» son mil doscientos treinta y cuatro euros).

    **Con una excepción que sí importa aquí y no en una factura: si lo que va delante del punto es
    un cero, el punto es decimal.** «0.235» es un precio de veintitrés céntimos y medio el kilo, no
    doscientos treinta y cinco euros; y sin esta excepción, un precio pactado con tres cifras se
    guardaría multiplicado por mil. Se paga con que «0.235» no pueda querer decir «235», que es una
    lectura que nadie escribe.

    Y **`de_texto` no pasa por `float` en ningún momento**: la regla se aplica sobre el texto y el
    número se construye con `Decimal`, que es exacto. Es la diferencia entre esta función y la del
    lector de facturas, y el motivo de que no se llame a aquella.
    """
    if texto is None:
        return None
    if isinstance(texto, Decimal):
        return a_decimal(texto)
    limpio = str(texto).strip().replace(" ", "").replace("\u00a0", "")
    if not limpio:
        return None
    limpio = limpio.removesuffix("€").strip()
    # El signo se queda aparte para poder decidir sobre las cifras sin él (un ajuste puede ser
    # negativo: una devolución resta kilos y euros).
    signo = ""
    if limpio.startswith(("+", "-")):
        signo, limpio = limpio[0], limpio[1:]
    tiene_coma = "," in limpio
    tiene_punto = "." in limpio
    if tiene_coma and tiene_punto:
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif tiene_coma:
        limpio = limpio.replace(",", ".")
    elif tiene_punto:
        partes = limpio.split(".")
        entero = partes[0]
        if len(partes) > 2 or (
            len(partes) == 2
            and len(partes[1]) == 3
            # La excepción del cero: «0.235» es un precio, no doscientos treinta y cinco.
            and entero not in ("", "0")
        ):
            limpio = limpio.replace(".", "")
    limpio = f"{signo}{limpio}"
    if limpio in ("", "-", "+", "."):
        return None
    try:
        numero = Decimal(limpio)
    except decimal.InvalidOperation as fallo:
        # Un texto que no es un número devuelve «no se sabe». Escribir cero sería peor: diría que el
        # agricultor cobró cero euros.
        raise ErrorDeDinero(f"«{texto}» no es un importe.") from fallo
    if not numero.is_finite():
        raise ErrorDeDinero(f"«{texto}» no es un importe.")
    return numero


def cantidad_a_decimal(valor: object) -> Decimal | None:
    """Una **cantidad** (kilos, litros, hectáreas) en `Decimal`. No es lo mismo que un importe.

    POR QUÉ HAY DOS FORMAS DE LEER UN NÚMERO EN ESTE MÓDULO, Y POR QUÉ ESO NO ES UN DESCUIDO. Un
    importe **no puede** llegar como número de coma flotante: media de las reglas de este ticket es
    que el dinero no pase por ahí, y `a_decimal` lo rechaza a la cara. Una cantidad, en cambio, el
    programa la guarda como número decimal desde el primer día —`cantidad`, `superficie_ha`,
    `dosis`— y rechazarla obligaría a migrar medio esquema para arreglar algo que aquí no está roto:
    **una cantidad no se cobra**. Lo que se hace con ella es multiplicarla por un precio, y ese
    producto se redondea **al céntimo, una sola vez** (`producto`), así que el error de la cantidad
    (una parte entre billones) no puede mover un céntimo.

    Lo que sí se hace, y es la mitad del cuidado: se convierte **por su texto** (`repr`, que es el
    decimal más corto que da ese mismo número) y no con `Decimal(float)`, que arrastraría las
    diecisiete cifras de la representación binaria. Un `8.000,0` se lee como `8000.0`, no como
    `8000.0000000000001`.
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        raise ErrorDeDinero("Una cantidad no puede ser verdadero o falso.")
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, float):
        return Decimal(repr(valor))
    return de_texto(str(valor))


def redondea(valor: Decimal | None, decimales: int = DECIMALES_DE_UN_IMPORTE) -> Decimal | None:
    """Un importe redondeado a esa cantidad de decimales, **hacia arriba cuando sobra medio**.

    POR QUÉ `ROUND_HALF_UP` Y NO LA REGLA POR DEFECTO. El redondeo por defecto de Python (y del
    módulo `decimal`) es «al par»: `0,125` a dos decimales da `0,12`, y `0,135` da `0,14`. Eso es
    correcto para no acumular sesgo en estadística, y **es lo que no se espera al cuadrar una
    cuenta**: el agricultor que echa la cuenta a mano redondea `0,125` a `0,13`. Aquí se usa la
    regla de la calle, dicha por escrito y probada con el número que las distingue (`0,125` y
    `0,135` dan los dos el de arriba).
    """
    if valor is None:
        return None
    cuantia = Decimal(1).scaleb(-decimales)
    return valor.quantize(cuantia, rounding=decimal.ROUND_HALF_UP, context=CONTEXTO)


def a_texto(valor: Decimal | None, decimales: int = DECIMALES_DE_UN_IMPORTE) -> str | None:
    """El importe en su forma canónica de texto: `"121.00"`, sin exponente y sin ceros de más.

    Es la forma en la que se guarda y la que viaja en el JSON (el contrato: «cadenas decimales en
    intercambio»). El punto como separador decimal —y no la coma— porque esto es un dato, no algo
    que se lee: la coma se pone al enseñarlo, con `formatea`.

    Acepta también un texto que ya venga en esa forma (lo que devuelve la API) y un entero: se convierte
    primero con `a_decimal`, que es quien sabe qué vale y qué no. Así esta función sirve para **volver a
    normalizar** un importe que viene de fuera sin obligar a quien llama a acordarse de convertir antes.

    **Y comprueba que el texto quepa en su columna** (revisión del T12). Esto era el defecto: la columna
    mide `MAXIMO_DE_CIFRAS` y un importe de 22 cifras enteras devolvía un texto de 27, que en SQLite se
    guardaba y **en PostgreSQL tumbaba la operación entera**. Aquí se para con una excepción clara en vez de
    dejar que lo descubra el motor, y el tope de verdad —el de un importe que puede ser una venta— lo
    comprueba `cabe_en_el_dinero`, que es quien tiene la frase del agricultor.
    """
    if valor is None:
        return None
    redondeado = redondea(a_decimal(valor), decimales)
    # `quantize` siempre deja el número en forma fija (nada de `1E+2`), que es lo que hace que el
    # texto se pueda volver a leer y comparar sin sorpresas.
    texto = format(redondeado, "f")
    if len(texto) > MAXIMO_DE_CIFRAS:
        raise ErrorDeDinero(
            f"Ese importe no cabe donde se guarda: «{texto}» mide {len(texto)} cifras y el sitio "
            f"admite {MAXIMO_DE_CIFRAS}. Rechazarlo es mejor que guardarlo a medias."
        )
    return texto


def formatea(valor: Decimal | None, decimales: int = DECIMALES_DE_UN_IMPORTE) -> str:
    """Un importe para leerlo: `1.234,56 €`. Si no se sabe, **vacío**, nunca `0,00 €`.

    Los ceros de la izquierda y el separador de miles se ponen aquí, a mano y sin librerías: el
    formato de un idioma que no sea el del agricultor sería peor que no formatear.
    """
    if valor is None:
        return ""
    redondeado = redondea(valor, decimales)
    entero, _, fraccion = format(abs(redondeado), "f").partition(".")
    miles = ""
    while len(entero) > 3:
        miles = "." + entero[-3:] + miles
        entero = entero[:-3]
    texto = f"{entero}{miles}"
    if decimales:
        texto = f"{texto},{fraccion.ljust(decimales, '0')[:decimales]}" if fraccion else f"{texto},{'0' * decimales}"
    return f"{'-' if redondeado < 0 else ''}{texto} €"


def suma(*valores: Decimal | None) -> Decimal:
    """La suma exacta. Un valor que no se sabe (`None`) **no cuenta como cero**: se ignora.

    Es la regla del proyecto entera («un dato que no se sabe queda en blanco, no se rellena con un
    cero»), y aquí tiene una consecuencia que se ve: el total de lo pendiente de cobro suma solo lo
    que se conoce, y quien quiera saber si falta algo tiene que preguntar cuántos importes no se
    saben (`cuantos_sin_saber`). Un total que calla que le faltan datos es un total que miente.
    """
    total = CERO
    for valor in valores:
        if isinstance(valor, float):
            # Un `float` colado en una suma de dinero es el fallo que este módulo existe para
            # evitar, así que se para aquí con un mensaje claro en vez de sumarlo en silencio.
            raise ErrorDeDinero(
                "Hay un número de coma flotante dentro de una suma de dinero: mira de dónde sale "
                "y conviértelo con `dinero.a_decimal` al leerlo."
            )
        convertido = a_decimal(valor)
        if convertido is not None:
            total += convertido
    return total


def resta(uno: Decimal | None, otro: Decimal | None) -> Decimal | None:
    """`uno - otro`, los dos redondeados al céntimo. Si falta cualquiera de los dos, no se sabe.

    **Restar no se puede inventar.** El pendiente de una factura (`importe - cobrado`) solo existe
    si se sabe el importe: si no se sabe, no es cero, es que no se puede decir. Devolver `0,00 €`
    ahí sería decirle al agricultor que no le deben nada, que es lo contrario de la verdad.
    """
    if uno is None or otro is None:
        return None
    if isinstance(uno, float) or isinstance(otro, float):
        raise ErrorDeDinero(
            "Hay un número de coma flotante dentro de una resta de dinero: conviértelo con "
            "`dinero.a_decimal` al leerlo."
        )
    primero = redondea(uno)
    segundo = redondea(otro)
    if primero is None or segundo is None:
        return None
    return redondea(primero - segundo)


def producto(cantidad: Decimal | None, precio: Decimal | None, decimales: int = DECIMALES_DE_UN_IMPORTE) -> Decimal | None:
    """`cantidad × precio`, redondeado **una sola vez**, al final.

    El redondeo va al final y no en cada factor, y es la mitad del motivo de que esta función
    exista: `0,2350 €/kg × 42.000 kg` son `9.870,00 €` exactos, pero redondear antes el precio al
    céntimo daría `0,24 × 42.000 = 10.080,00 €`, doscientos diez euros de más. El precio se guarda
    con las cifras que se pactaron y aquí se redondea el resultado, que es lo único que se cobra.
    """
    if cantidad is None or precio is None:
        return None
    uno = a_decimal(cantidad)
    otro = a_decimal(precio)
    if uno is None or otro is None:
        return None
    return redondea(CONTEXTO.multiply(uno, otro), decimales)


def cuantos_sin_saber(*valores: object) -> int:
    """Cuántos de esos valores no se saben (`None` o vacío).

    Existe para poder decirlo en pantalla: «faltan 3 importes» es lo que convierte un total en algo
    en lo que se puede confiar. Sin este número, el pie de una tabla suma lo que hay y **parece**
    que cuadra.
    """
    faltan = 0
    for valor in valores:
        if valor is None:
            faltan += 1
            continue
        if isinstance(valor, str) and not valor.strip():
            faltan += 1
    return faltan


def es_cero(valor: Decimal | None) -> bool:
    """Si un importe conocido vale exactamente cero. **No se sabe no es cero.**"""
    conocido = a_decimal(valor)
    return conocido is not None and conocido == 0


class ImporteExacto(TypeDecorator):
    """Una columna de dinero: `Decimal` en Python, texto decimal canónico en la base.

    POR QUÉ TEXTO Y NO `Numeric`, que es lo que uno escribiría primero. Porque la base de este
    programa guarda el cuaderno en SQLite, y allí `Numeric` **no es exacto**: el dialecto de
    SQLAlchemy lo dice (`supports_native_decimal = False`) y convierte el valor a `float` al
    guardarlo y lo vuelve a `Decimal` al leerlo. O sea: exactamente la coma flotante que este
    módulo existe para evitar, metida dentro del motor y sin que se vea en el código. Un texto
    decimal es exacto en SQLite y en PostgreSQL, se lee en un visor con los ojos y no depende de
    ninguna conversión del dialecto.

    Lo que se pierde, y se dice para que nadie lo busque: **en SQL no se puede sumar ni ordenar por
    esta columna**. Las sumas y los totales se hacen en Python, con `decimal`, que es lo que el
    contrato pide («el servidor devuelve el agregado del conjunto filtrado»), y para ordenar por
    importe se ordena en memoria con el `Decimal` ya leído, nunca por el texto: `"9.00"` es mayor
    que `"121.00"` como texto y menor como número.
    """

    impl = String(MAXIMO_DE_CIFRAS)
    cache_ok = True

    def __init__(self, decimales: int = DECIMALES_DE_UN_IMPORTE):
        self.decimales = decimales
        super().__init__(length=MAXIMO_DE_CIFRAS)

    def process_bind_param(self, value, dialect):  # noqa: ANN001 - la firma la pone SQLAlchemy
        if value is None:
            return None
        # Aquí se redondea como última red: quien llama ya debería haber redondeado, y esto evita
        # que un `Decimal("80.999")` acabe guardado con tres cifras y descuadre la lectura.
        return a_texto(a_decimal(value), self.decimales)

    def process_result_value(self, value, dialect):  # noqa: ANN001 - la firma la pone SQLAlchemy
        if value is None:
            return None
        return a_decimal(value)


# Los dos tipos que usan los modelos, con nombre propio para que se lea en `models.py` qué es cada
# columna: un importe (dos cifras) o un precio por unidad (las que se pactaron).
Dinero = ImporteExacto(DECIMALES_DE_UN_IMPORTE)
Precio = ImporteExacto(DECIMALES_DE_UN_PRECIO)
