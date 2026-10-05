"""Leer una factura y sacar de ella lo que el cuaderno necesita.

## Por qué esto no es un adorno

El cuaderno de explotación de Castilla y León pide, en su hoja 9.1, la **«Empresa suministradora»**
y el **«Nº de factura»**; y en la hoja 6, el **«Nº de albarán»**. Y la hoja «doc» del propio
cuaderno dice que hay que conservar, junto al cuaderno y durante tres años, «las facturas u otros
documentos que justifiquen la adquisición de los productos fitosanitarios». O sea: la factura no es
un extra para llevar las cuentas de casa, **es un dato que el cuaderno pide**. Sin ella, esas
casillas se quedan vacías.

## Cómo se lee (y por qué así)

1. **Primero se busca el texto de verdad.** Un PDF que viene del proveedor por correo casi siempre
   tiene las letras dentro: se leen tal cual, con acentos y todo, sin equivocarse. Eso es lo primero
   que se intenta.
2. **Si el PDF no tiene letras, es un escaneo**, y entonces se dibuja cada página como una imagen y
   se le pasa al lector de letras (`app/ocr.py`).
3. **Si es una foto, se le pasa al lector de letras directamente.**
4. **Si no hay lector de letras instalado, se dice** y no se inventa nada: la factura se guarda como
   justificante y los datos los teclea el agricultor.

## Lo que hace que esto sea de fiar: las cuentas cuadran

Una lectura de una factura **se puede comprobar con aritmética**, y eso es lo que se hace aquí:

- En cada línea: **cantidad × precio = importe**. Si no da, la línea se marca como «no cuadra» y se
  dice, en vez de dar por buena una lectura que se ha equivocado de columna.
- En el total: **la suma de las líneas = la base imponible**, y **base + IVA = total**. Si no da,
  se avisa.

Y aun así, **el agricultor confirma**: la pantalla enseña lo que se ha leído, campo por campo, para
que lo corrija. Lo que aquí se llama «interpretación» es una **propuesta**, nunca un dato dado por
bueno. Eso es lo que hace que valga para una foto hecha con el móvil, que siempre trae alguna errata.
"""

from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata
from dataclasses import dataclass, field

from . import ocr, servicios

# --------------------------------------------------------------------------
# Los formatos de número y de fecha que se ven en una factura española
# --------------------------------------------------------------------------

# Las unidades que se escriben en una factura, cada una con la forma en la que se guardan aquí.
# Se acepta lo que escribe el proveedor («UDS», «Kgs», «Lts») porque cada uno lo escribe a su
# manera y rechazar la línea por eso sería absurdo: la unidad la acaba confirmando el agricultor.
UNIDADES = {
    "ud": "ud", "uds": "ud", "un": "ud", "unid": "ud", "unids": "ud", "unidad": "ud",
    "unidades": "ud", "u": "ud", "pza": "ud", "pzas": "ud", "pieza": "ud", "piezas": "ud",
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg", "kilogramo": "kg", "kilogramos": "kg",
    "g": "g", "gr": "g", "grs": "g", "gramo": "g", "gramos": "g",
    "l": "L", "lt": "L", "lts": "L", "litro": "L", "litros": "L",
    "ml": "ml", "cc": "ml", "mililitros": "ml",
    "t": "t", "tn": "t", "tns": "t", "tm": "t", "tonelada": "t", "toneladas": "t",
    "m3": "m3", "saco": "saco", "sacos": "saco", "bote": "bote", "botes": "bote",
    "bidon": "bidon", "bidones": "bidon", "garrafa": "garrafa", "garrafas": "garrafa",
    "caja": "caja", "cajas": "caja", "pack": "pack", "granel": "granel",
}

# Las palabras que avisan de que una línea **no** es un producto comprado, sino un total, un
# descuento o la cabecera de la tabla. Sin esta lista, «Base imponible 810,00» se leería como si
# fuera un producto que cuesta 810 euros.
NO_SON_PRODUCTOS = (
    "base imponible", "base liquidable", "base:", "subtotal", "total factura", "total a pagar",
    "total:", "importe total", "total base", "iva", "i.v.a", "i/v/a", "cuota", "recargo",
    "descuento", "dto", "portes", "transporte", "envio", "envío", "forma de pago", "vencimiento",
    "cant.", "cantidad", "precio", "importe", "descripcion", "descripción", "codigo", "código",
    "articulo", "artículo", "referencia", "n.i.f", "nif", "cif", "factura", "albaran", "albarán",
    "fecha", "cliente", "proveedor", "domicilio", "direccion", "dirección", "telefono", "teléfono",
    "suma", "suman", "liquidacion", "liquidación", "irpf", "retencion", "retención",
)

# Las etiquetas de los totales. Se buscan por trozos y sin acentos: en una foto el lector de letras
# puede poner «l.V.A.» o «IVA» y da igual.
ETIQUETAS_BASE = ("base imponible", "base liquidable", "importe base", "base:")
ETIQUETAS_TOTAL = (
    "total factura", "total a pagar", "importe total", "total de la factura", "total:",
    "total euros", "liquido a pagar", "líquido a pagar",
)
ETIQUETAS_IVA = ("iva", "i.v.a", "i/v/a", "impuesto sobre el valor anadido")

# Un número tal y como se escribe en una factura española: «1.234,56», «1234,56», «1234.56».
NUMERO = r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?"

# La cola de una línea de la tabla: cantidad, unidad (a veces no está) y precio, importe. Va
# anclada al final de la línea a propósito: es lo que hace que una descripción con números dentro
# («GLIFOSATO 36% SL 20 L») no se confunda con las columnas.
#
# El `ruido` que se admite entre la unidad y el precio (un guion bajo, una raya, un asterisco) no es
# un capricho: cuando el lector de letras mira una foto, las **rayas de la propia tabla** se cuelan
# como caracteres sueltos («TRIGO BLANDO 500 KG _ 0,38 190,00»). Sin esto, esa línea no se leía y el
# agricultor tenía que escribirla a mano.
#
# Ojo con la clase de caracteres, que aquí está el detalle: el guion bajo **no** es puntuación para
# una expresión regular (`\w` incluye la barra baja), así que hay que admitirlo a mano con `[\W_]`.
# Con `[^\w\s]` el guion bajo no encajaba y la línea seguía sin leerse.
RUIDO = r"[\W_]{1,4}"

COLA_DE_LA_TABLA = re.compile(
    rf"^(?P<descripcion>.*?)\s+"
    rf"(?P<cantidad>{NUMERO})\s*"
    rf"(?P<unidad>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{{1,6}})?\s*"
    rf"(?P<ruido>{RUIDO}\s*)?"
    rf"(?P<precio>\d+[.,]\d{{2}})\s+"
    rf"(?P<importe>\d+[.,]\d{{2}})\s*$"
)

# Y esta, para cuando la línea solo trae la cantidad y el importe (hay facturas que no ponen el
# precio unitario).
COLA_SIN_PRECIO = re.compile(
    rf"^(?P<descripcion>.*?)\s+"
    rf"(?P<cantidad>{NUMERO})\s*"
    rf"(?P<unidad>[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{{1,6}})?\s*"
    rf"(?P<ruido>{RUIDO}\s*)?"
    rf"(?P<importe>\d+[.,]\d{{2}})\s*$"
)

# El número de registro de un producto fitosanitario, cuando la factura lo pone con su etiqueta.
NUMERO_DE_REGISTRO = re.compile(
    r"(?:n[ºo°.]?\s*(?:de\s*)?(?:reg(?:istro)?|inscripci[oó]n)\.?|registro)\s*[:.]?\s*"
    r"([A-Z]{0,3}[- ]?\d{2,6}(?:[.\-/]\d{1,4})?)",
    re.IGNORECASE,
)


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _plano(texto: str) -> str:
    """El texto en minúsculas, sin acentos y con los espacios de sobra fuera. Para comparar."""
    return re.sub(r"\s+", " ", _sin_acentos(texto).lower()).strip()


def numero_espanol(texto: str) -> float | None:
    """Convierte «1.234,56», «1234,56» o «1234.56» en un número.

    Los tres formatos aparecen en facturas de verdad, y el mismo proveedor puede usar dos. La
    regla: si están los dos separadores, **el último es el decimal**; si solo hay punto y lleva
    exactamente tres cifras detrás, es un separador de miles («1.234» son mil doscientos treinta y
    cuatro, no uno con doscientos treinta y cuatro milésimas).

    Si no se puede leer, devuelve `None`: un cero sería peor que un hueco.
    """
    if texto is None:
        return None
    limpio = str(texto).strip().replace(" ", "").replace("\u00a0", "")
    if not limpio:
        return None
    limpio = re.sub(r"[€$]$", "", limpio)
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
        if len(partes) > 2 or (len(partes) == 2 and len(partes[1]) == 3):
            limpio = limpio.replace(".", "")
    try:
        return float(limpio)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Lo que se devuelve
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LineaLeida:
    """Una línea de la factura, tal y como se ha leído."""

    descripcion: str
    cantidad: float | None
    unidad: str
    precio_unitario: float | None
    importe: float | None
    numero_registro: str = ""
    # Si la cuenta de la línea cuadra (cantidad × precio = importe). Es la prueba de que la lectura
    # no se ha equivocado de columna.
    cuadra: bool = False
    # alta | media | baja. Va a la pantalla para que el agricultor sepa dónde mirar primero.
    confianza: str = "baja"
    # El producto de su cesta que más se parece a esta línea, si hay alguno. Con su número de
    # registro coincide, la sugerencia es segura.
    producto_sugerido_id: int | None = None
    producto_sugerido: str = ""
    como_se_sugiere: str = ""

    @property
    def clave(self) -> str:
        return _plano(self.descripcion)


@dataclass
class FacturaLeida:
    """Lo que se ha podido sacar del documento. **Es una propuesta, no un dato.**"""

    proveedor: str = ""
    proveedor_nif: str = ""
    numero_factura: str = ""
    fecha: dt.date | None = None
    base_imponible: float | None = None
    cuota_iva: float | None = None
    tipo_iva_pct: float | None = None
    total: float | None = None
    lineas: list[LineaLeida] = field(default_factory=list)
    # Cómo se ha leído: "pdf" (el PDF traía el texto), "escaneo" (el PDF era una imagen) o "foto".
    como_se_leyo: str = ""
    idioma_del_lector: str = ""
    texto_crudo: str = ""
    avisos: list[str] = field(default_factory=list)

    @property
    def cuadra_el_total(self) -> bool:
        """¿Cuadra lo que suma el documento? Base + IVA = total, y las líneas = base."""
        if self.base_imponible is None or self.total is None:
            return False
        if self.cuota_iva is None:
            return abs(self.total - self.base_imponible) < 0.02
        return abs((self.base_imponible + self.cuota_iva) - self.total) < 0.02

    @property
    def suman_las_lineas(self) -> bool:
        if self.base_imponible is None or not self.lineas:
            return False
        suma = sum(linea.importe or 0.0 for linea in self.lineas)
        return abs(suma - self.base_imponible) <= max(0.05, self.base_imponible * 0.01)

    def resumen(self) -> dict:
        return {
            "lineas": len(self.lineas),
            "lineas_que_cuadran": sum(1 for linea in self.lineas if linea.cuadra),
            "cuadra_el_total": self.cuadra_el_total,
            "suman_las_lineas": self.suman_las_lineas,
            "como_se_leyo": self.como_se_leyo,
            "idioma_del_lector": self.idioma_del_lector,
        }


# --------------------------------------------------------------------------
# Los trozos de la lectura
# --------------------------------------------------------------------------


def _fecha(texto: str) -> dt.date | None:
    """La fecha de la factura: la que va con su etiqueta y, si no la hay, la primera del papel."""
    etiquetada = re.search(
        r"(?i)fecha(?:\s+de\s+(?:la\s+)?factura)?\s*[:.]?\s*"
        r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})",
        texto,
    )
    candidatas = [etiquetada] if etiquetada else []
    candidatas.extend(re.finditer(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", texto))
    for encontrada in candidatas:
        if not encontrada:
            continue
        dia, mes, anio = (int(grupo) for grupo in encontrada.groups())
        if anio < 100:
            anio += 2000
        try:
            return dt.date(anio, mes, dia)
        except ValueError:
            continue
    return None


def _nifs(texto: str) -> list[str]:
    """Todos los NIF que aparecen en el documento, normalizados y sin repetir.

    Se busca con la forma española completa (DNI, NIE y CIF) y se normaliza igual que el
    certificado digital, para poder comparar.
    """
    encontrados: list[str] = []
    patron = re.compile(r"\b([A-ZXYZ]?[-\s]?\d{7,8}[-\s]?[A-Z0-9])\b", re.IGNORECASE)
    for encontrado in patron.finditer(texto.upper()):
        limpio = re.sub(r"[\s\-.]", "", encontrado.group(1))
        # Se quitan las palabras que se parecen a un NIF pero no lo son (un código de artículo, una
        # matrícula): tiene que tener la forma exacta.
        if re.fullmatch(r"\d{8}[A-Z]", limpio) or re.fullmatch(r"[XYZ]\d{7}[A-Z]", limpio) or re.fullmatch(
            r"[A-Z]\d{7}[0-9A-Z]", limpio
        ):
            if limpio not in encontrados:
                encontrados.append(limpio)
    return encontrados


def _proveedor(texto: str, nif_del_agricultor: str) -> tuple[str, str]:
    """Quién manda la factura y con qué NIF.

    El truco que hace esto fiable: **el NIF del agricultor ya se sabe**. En una factura hay dos
    NIF, el del que vende y el del que compra; el del agricultor es el que él ya tiene apuntado, y
    el proveedor es **el otro**. Así no hay que adivinar cuál es cuál.
    """
    nifs = _nifs(texto)
    propio = nif_del_agricultor.strip().upper()
    del_proveedor = [nif for nif in nifs if nif != propio]
    nif_proveedor = del_proveedor[0] if del_proveedor else (nifs[0] if nifs else "")

    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    proveedor = ""
    # 1. Una etiqueta que lo diga.
    for linea in lineas:
        etiquetada = re.search(
            r"(?i)(?:proveedor|vendedor|emisor|raz[oó]n social|empresa)\s*[:.]\s*(.+)", linea
        )
        if etiquetada:
            proveedor = etiquetada.group(1).strip()
            break
    # 2. Si no, las primeras líneas del papel, que es donde va el membrete. Se cortan en la línea
    #    del NIF, la dirección o el teléfono.
    if not proveedor:
        for linea in lineas[:6]:
            plano = _plano(linea)
            if not plano or len(plano) < 4:
                continue
            if any(
                palabra in plano
                for palabra in ("nif", "n.i.f", "cif", "c/", "calle", "poligono", "polígono",
                                "telefono", "teléfono", "fax", "www", "@", "factura")
            ):
                continue
            if re.fullmatch(r"[\d\s\-.,/]+", plano):
                continue
            proveedor = linea.strip()
            break
    # 3. Y si el nombre va en la línea de encima o de debajo del NIF, se coge esa.
    if not proveedor and nif_proveedor:
        for posicion, linea in enumerate(lineas):
            if nif_proveedor.replace("-", "") in re.sub(r"[\s\-.]", "", linea.upper()):
                for vecina in (lineas[posicion - 1] if posicion else "", linea):
                    limpio = re.sub(r"(?i)n\.?i\.?f\.?\s*[:.]?.*$", "", vecina).strip()
                    if len(_plano(limpio)) > 4:
                        proveedor = limpio
                        break
                break
    return proveedor[:200], nif_proveedor


def _numero_de_factura(texto: str) -> str:
    """El número de la factura. Tiene que llevar algún dígito: «Factura» a secas no es un número.

    Se miran las líneas una por una y **se saltan las de los totales**, y eso no es un detalle: sin
    ese salto, en una factura sin número se leía «TOTAL FACTURA: 980,10» y el número de factura
    acababa siendo «980». Un número de factura que en realidad es el total es un dato falso que
    además viaja al cuaderno.
    """
    # El número tiene que llevar **al menos un dígito**, y eso se le pide dentro de la propia
    # expresión con una comprobación por delante (`(?=...)`). Sin ella pasaba esto: en
    # «FACTURA NUM. 2026/00123», la primera forma encajaba con la «N» de «NUM» y se quedaba con el
    # «UM.» como número de factura, y como no llevaba dígitos se descartaba y el número de verdad
    # se perdía. Con la comprobación, el motor de expresiones sigue probando formas hasta dar con
    # «2026/00123».
    numero = r"(?=[A-Z0-9/\-._]*\d)([A-Z0-9][A-Z0-9/\-._]{2,24})"
    patrones = (
        rf"(?i)factura\s*(?:n[ºo°.^'\"*]{{0,3}}|n[uú]mero|num\.?|#)\s*[:.\-]?\s*{numero}",
        rf"(?i)(?:fra|fact)\.?\s*(?:n[ºo°.^'\"*]{{0,3}})\s*[:.\-]?\s*{numero}",
        rf"(?i)n[ºo°.^'\"*]{{0,3}}\s*(?:de\s*)?factura\s*[:.\-]?\s*{numero}",
        rf"(?i)factura\s*[:.\-]?\s*{numero}",
    )
    for linea in texto.splitlines():
        plano = _plano(linea)
        if any(
            palabra in plano
            for palabra in ("total", "base", "iva", "i.v.a", "importe", "subtotal", "suma")
        ):
            continue
        for patron in patrones:
            encontrado = re.search(patron, linea)
            if not encontrado:
                continue
            candidato = encontrado.group(1).strip(" .-")
            if not any(caracter.isdigit() for caracter in candidato):
                continue
            # Un número de factura no es una palabra suelta del castellano.
            if _plano(candidato) in ("de", "n", "numero", "num", "factura", "fra"):
                continue
            return candidato
    return ""


def _unidad(texto: str) -> str:
    limpio = _plano(texto or "")
    return UNIDADES.get(limpio, "")


def _es_ruido(descripcion: str) -> bool:
    """¿Esta línea es un producto o es la cabecera, un total o un pie de página?"""
    plano = _plano(descripcion)
    if len(plano) < 3:
        return True
    if re.fullmatch(r"[\d\s\-.,/%*]+", plano):
        return True
    return any(palabra in plano for palabra in NO_SON_PRODUCTOS)


def _numero_de_registro(descripcion: str) -> str:
    encontrado = NUMERO_DE_REGISTRO.search(descripcion)
    return encontrado.group(1).strip() if encontrado else ""


def _lineas_de_la_tabla(texto: str) -> list[LineaLeida]:
    """Las líneas de producto, sacadas de la tabla.

    Se recorren las líneas del texto y se mira si terminan en «… cantidad unidad precio importe».
    Ese anclaje al final es lo que hace que una descripción con números dentro («GLIFOSATO 36% SL
    20 L») no se confunda con las columnas.

    De cada línea se prueban **las dos formas** (con precio unitario y sin él) y se elige la mejor,
    donde «mejor» quiere decir: primero la que cuadra (cantidad × precio = importe), y después la
    que trae más datos. Antes se cogía la primera que encajara, y en una foto eso hacía que una
    línea con la raya de la tabla en medio se leyera como cantidad y importe en vez de como
    cantidad, precio e importe.
    """
    leidas: list[LineaLeida] = []
    for linea in texto.splitlines():
        limpia = linea.strip()
        if len(limpia) < 6 or _es_ruido(limpia):
            continue

        candidatas: list[LineaLeida] = []
        con_precio = COLA_DE_LA_TABLA.match(limpia)
        if con_precio:
            cantidad = numero_espanol(con_precio.group("cantidad"))
            precio = numero_espanol(con_precio.group("precio"))
            importe = numero_espanol(con_precio.group("importe"))
            descripcion = con_precio.group("descripcion").strip(" .-_")
            if descripcion and not _es_ruido(descripcion):
                cuadra = _cuadra(cantidad, precio, importe)
                candidatas.append(
                    LineaLeida(
                        descripcion=descripcion[:200],
                        cantidad=cantidad,
                        unidad=_unidad(con_precio.group("unidad") or ""),
                        precio_unitario=precio,
                        importe=importe,
                        numero_registro=_numero_de_registro(limpia),
                        cuadra=cuadra,
                        confianza="alta" if cuadra else "baja",
                    )
                )

        sin_precio = COLA_SIN_PRECIO.match(limpia)
        if sin_precio:
            cantidad = numero_espanol(sin_precio.group("cantidad"))
            importe = numero_espanol(sin_precio.group("importe"))
            descripcion = sin_precio.group("descripcion").strip(" .-_")
            if descripcion and not _es_ruido(descripcion):
                candidatas.append(
                    LineaLeida(
                        descripcion=descripcion[:200],
                        cantidad=cantidad,
                        unidad=_unidad(sin_precio.group("unidad") or ""),
                        precio_unitario=None,
                        importe=importe,
                        numero_registro=_numero_de_registro(limpia),
                        cuadra=False,
                        confianza="media",
                    )
                )
        if candidatas:
            leidas.append(
                sorted(
                    candidatas,
                    key=lambda candidata: (
                        candidata.cuadra,
                        candidata.precio_unitario is not None,
                        bool(candidata.unidad),
                    ),
                    reverse=True,
                )[0]
            )
    return leidas


def _cuadra(cantidad: float | None, precio: float | None, importe: float | None) -> bool:
    """cantidad × precio = importe, con margen para el redondeo de la factura."""
    if cantidad is None or precio is None or importe is None:
        return False
    if cantidad <= 0 or precio <= 0:
        return False
    return abs(cantidad * precio - importe) <= max(0.03, abs(importe) * 0.02)


def _un_solo_numero_en_la_linea(texto: str, etiquetas: tuple[str, ...]) -> float | None:
    """El número que va detrás de una etiqueta («Base imponible: 810,00»)."""
    for etiqueta in etiquetas:
        for encontrado in re.finditer(
            rf"(?i){re.escape(etiqueta)}[^0-9\-]{{0,20}}(?P<numero>{NUMERO})", texto
        ):
            valor = numero_espanol(encontrado.group("numero"))
            if valor is not None:
                return valor
    return None


def _totales(texto: str) -> tuple[float | None, float | None, float | None, float | None]:
    """Base imponible, cuota de IVA, tipo de IVA y total.

    Se busca de más a menos fiable: primero con la etiqueta, y después por las líneas del final del
    documento, que es donde van los totales en cualquier factura.
    """
    base = _un_solo_numero_en_la_linea(texto, ETIQUETAS_BASE)
    total = _un_solo_numero_en_la_linea(texto, ETIQUETAS_TOTAL)
    cuota: float | None = None
    tipo: float | None = None
    for encontrado in re.finditer(
        rf"(?i)(?:{ '|'.join(re.escape(e) for e in ETIQUETAS_IVA) })\s*"
        rf"(?P<tipo>\d{{1,2}}(?:[.,]\d{{1,2}})?)?\s*%?[^0-9\-]{{0,20}}(?P<cuota>{NUMERO})",
        texto,
    ):
        posible_tipo = numero_espanol(encontrado.group("tipo")) if encontrado.group("tipo") else None
        posible_cuota = numero_espanol(encontrado.group("cuota"))
        # El «21» de «IVA 21%» no puede ser la cuota: si el número es pequeño y redondo y hay otro
        # número detrás, el pequeño es el tipo.
        if posible_tipo is not None and posible_tipo in (0, 4, 5, 7, 10, 21) and posible_cuota:
            tipo, cuota = posible_tipo, posible_cuota
            break
        if posible_cuota is not None and posible_cuota not in (0, 4, 5, 7, 10, 21):
            cuota = posible_cuota
    return base, cuota, tipo, total


def _sugerir_producto(linea: LineaLeida, productos: list[dict]) -> LineaLeida:
    """Busca en la cesta del agricultor el producto del que habla esta línea.

    Dos caminos, y el primero es el bueno:

    1. **Por el número de registro.** Es el número único de cada producto fitosanitario: si la
       factura lo trae y coincide con uno de su cesta, no hay duda posible.
    2. **Por las palabras del nombre.** Se comparan en plano (sin acentos y en minúsculas) **palabra
       a palabra**, no el texto entero. Esto último costó un test: la factura pone «GLIFOSATO 36% SL
       20 L» y en la cesta está «Glifosato 36 SL», y buscar el nombre entero dentro del otro falla
       por el «%» de en medio. Con palabras, las tres del nombre («glifosato», «36», «sl») están en
       la descripción y la sugerencia sale sola.
    """
    if linea.numero_registro:
        buscado = re.sub(r"[\s\-.]", "", linea.numero_registro).upper()
        for producto in productos:
            suyo = re.sub(r"[\s\-.]", "", (producto.get("numero_registro") or "")).upper()
            if suyo and suyo == buscado:
                return _con_sugerencia(linea, producto, "por el número de registro")

    clave = linea.clave
    if not clave:
        return linea
    palabras_de_la_linea = set(_palabras(clave))
    for producto in productos:
        nombre = servicios.clave_de_producto(producto.get("nombre_comercial") or "")
        if not nombre or len(nombre) < 4:
            continue
        # 1. El nombre entero, dentro de la descripción o al revés (lo más seguro después del
        #    número de registro).
        if nombre in clave or clave in nombre:
            return _con_sugerencia(linea, producto, "por el nombre")
        # 2. Todas las palabras del nombre, dentro de la descripción.
        palabras_del_producto = _palabras(nombre)
        if not palabras_del_producto:
            continue
        if all(palabra in palabras_de_la_linea for palabra in palabras_del_producto):
            return _con_sugerencia(linea, producto, "por el nombre")
        # 3. Al menos dos palabras largas en común: «ABONO NPK 15-15-15» y «NPK 15-15-15».
        largas = [palabra for palabra in palabras_del_producto if len(palabra) >= 5]
        if len(largas) >= 2 and all(palabra in palabras_de_la_linea for palabra in largas):
            return _con_sugerencia(linea, producto, "por las palabras del nombre")
    return linea


def _palabras(texto: str) -> list[str]:
    """Las palabras con algo de miga de un texto plano: se descartan las de una o dos letras."""
    return [palabra for palabra in re.split(r"[^0-9a-z]+", texto) if len(palabra) >= 3]


def _con_sugerencia(linea: LineaLeida, producto: dict, como: str) -> LineaLeida:
    return LineaLeida(
        descripcion=linea.descripcion,
        cantidad=linea.cantidad,
        unidad=linea.unidad,
        precio_unitario=linea.precio_unitario,
        importe=linea.importe,
        numero_registro=linea.numero_registro,
        cuadra=linea.cuadra,
        confianza="alta" if linea.cuadra else linea.confianza,
        producto_sugerido_id=producto.get("id"),
        producto_sugerido=producto.get("nombre_comercial") or "",
        como_se_sugiere=como,
    )


# --------------------------------------------------------------------------
# La puerta de entrada
# --------------------------------------------------------------------------


def es_pdf(contenido: bytes) -> bool:
    return contenido[:5] == b"%PDF-"


def _parece_texto(contenido: bytes) -> str:
    """Si el fichero es texto (un `.txt` o un `.csv` pegado), se devuelve tal cual.

    Un proveedor pequeño puede mandar la factura como texto en el cuerpo de un correo y el
    agricultor pegarla en un fichero. Leerla cuesta nada y evita decirle «no puedo» a algo que sí
    se puede leer.
    """
    try:
        texto = contenido.decode("utf-8")
    except UnicodeDecodeError:
        try:
            texto = contenido.decode("latin-1")
        except UnicodeDecodeError:  # pragma: no cover - latin-1 no falla nunca
            return ""
    if not texto.strip():
        return ""
    # Si tiene muchos caracteres de control no es un texto: es un binario con suerte.
    imprimibles = sum(1 for caracter in texto if caracter.isprintable() or caracter in "\n\r\t")
    return texto if imprimibles / max(len(texto), 1) > 0.9 else ""


def _texto_de_un_pdf(contenido: bytes) -> str:
    """El texto que lleva dentro el PDF, página por página."""
    import pdfplumber

    trozos: list[str] = []
    with pdfplumber.open(io.BytesIO(contenido)) as documento:
        for pagina in documento.pages[: ocr.MAXIMO_PAGINAS]:
            trozos.append(pagina.extract_text() or "")
    return "\n".join(trozos).strip()


def leer_factura(
    contenido: bytes,
    *,
    nif_del_agricultor: str = "",
    productos: list[dict] | None = None,
) -> FacturaLeida:
    """Lee una factura y devuelve lo que ha entendido. **No guarda nada.**

    `productos` es la cesta del agricultor (nombre, número de registro y materia activa): con ella
    se puede decir «esta línea es el Glifosato que ya tienes apuntado», que es lo que convierte una
    lectura de números en algo que sirve.
    """
    leida = FacturaLeida()
    texto = texto_del_documento(contenido, leida)
    if not texto:
        if not leida.avisos:
            leida.avisos.append(
                "No he podido leer nada de ese documento. Prueba con una foto más derecha y con "
                "más luz, o escribe los datos a mano."
            )
        return leida

    leida.texto_crudo = texto
    leida.proveedor, leida.proveedor_nif = _proveedor(texto, nif_del_agricultor)
    leida.numero_factura = _numero_de_factura(texto)
    leida.fecha = _fecha(texto)
    (
        leida.base_imponible,
        leida.cuota_iva,
        leida.tipo_iva_pct,
        leida.total,
    ) = _totales(texto)

    conocidos = productos or []
    leida.lineas = [_sugerir_producto(linea, conocidos) for linea in _lineas_de_la_tabla(texto)]

    _anadir_avisos(leida)
    return leida


def texto_del_documento(contenido: bytes, leida: FacturaLeida) -> str:
    """Las letras que hay dentro de un papel, venga como venga. **La puerta única de la lectura.**

    POR QUÉ ES UNA FUNCIÓN APARTE (T10, 03/10/2026). Cuando llegó la foto de la etiqueta de una
    semilla hizo falta **exactamente esto**: primero el texto de verdad (un PDF del proveedor trae
    las letras dentro y se leen sin equivocarse) y el lector de fotos **solo si no hay texto** (un
    escaneo o una foto del móvil). Escribir un segundo lector de documentos habría sido tener dos
    caminos que un día se separan —el día que se cambie el idioma del lector, o el número de
    páginas, o el tamaño de la imagen—, así que esto se saca de `leer_factura` y lo usan las dos.

    Lo que **no** hace: entender nada. Devuelve las letras y apunta en `leida` **cómo** se ha leído
    (`como_se_leyo`), con qué idioma, y **por qué no se ha podido** (los avisos de la lectura, que no
    son los de la factura: esos los añade `_anadir_avisos`). Quien llame decide qué hacer con el
    texto.

    `leida` es obligatorio a propósito: es donde van los avisos, y un aviso que se pierde por el
    camino deja al agricultor sin saber por qué su foto no se ha leído.
    """
    if not contenido:
        leida.avisos.append("No has subido ningún fichero.")
        return ""

    if es_pdf(contenido):
        try:
            texto = _texto_de_un_pdf(contenido)
        except Exception as fallo:
            leida.avisos.append(
                f"No se ha podido abrir el PDF ({type(fallo).__name__}). Prueba con una foto."
            )
            return ""
        # Un PDF con menos de cuarenta letras es un escaneo: por dentro es una imagen.
        if len(re.sub(r"\s", "", texto)) >= 40:
            leida.como_se_leyo = "pdf"
            return texto
        if ocr.hay_lector():
            try:
                texto = ocr.leer_texto_de_un_pdf(contenido)
            except ocr.SinLector as problema:
                leida.avisos.append(str(problema))
                return ""
            leida.como_se_leyo = "escaneo"
            leida.idioma_del_lector = ocr.idioma_a_usar()
            return texto
        leida.avisos.append(
            "Ese PDF es un escaneo (por dentro es una imagen) y en este ordenador no está "
            "instalado el programa que lee las fotos. Súbeme una foto del papel o escribe los "
            "datos a mano."
        )
        return ""

    if texto_suelto := _parece_texto(contenido):
        # Un texto pegado o un `.txt`: se lee tal cual, sin lector de letras de por medio.
        leida.como_se_leyo = "texto"
        return texto_suelto

    # Cualquier otra cosa (un JPG, un WEBP, un HEIC…) se intenta como imagen.
    return _leer_una_imagen(contenido, leida)[0]




def _leer_una_imagen(contenido: bytes, leida: FacturaLeida) -> tuple[str, FacturaLeida]:
    if not ocr.hay_lector():
        leida.avisos.append(
            "En este ordenador no está instalado el programa que lee las fotos, así que de la "
            "foto no puedo sacar los datos. Se guardará como justificante y los escribes tú."
        )
        return "", leida
    try:
        texto = ocr.leer_texto(contenido)
        leida.como_se_leyo = "foto"
        leida.idioma_del_lector = ocr.idioma_a_usar()
        return texto, leida
    except ocr.SinLector as problema:
        leida.avisos.append(str(problema))
        return "", leida


def _anadir_avisos(leida: FacturaLeida) -> None:
    """Lo que hay que decirle al agricultor sobre la calidad de la lectura.

    Estos avisos no son para asustar: son para que sepa **dónde mirar** antes de dar el visto
    bueno. Y ninguno impide guardar la factura: la factura la confirma él.
    """
    if leida.como_se_leyo in ("foto", "escaneo") and "spa" not in (leida.idioma_del_lector or ""):
        leida.avisos.append(
            "Esto lo he leído de una imagen y el lector solo tiene el idioma inglés: los números "
            "están bien, pero mira las palabras con tilde o con eñe, que pueden salir cambiadas."
        )
    sin_cuadrar = [linea for linea in leida.lineas if not linea.cuadra]
    if sin_cuadrar:
        leida.avisos.append(
            f"En {len(sin_cuadrar)} línea(s) la cuenta de cantidad × precio no da el importe. "
            "Míralas antes de guardar: puede ser que haya leído un número de la columna de al lado."
        )
    if not leida.lineas:
        leida.avisos.append(
            "No he reconocido ninguna línea de producto. Puede ser una factura de servicios, o que "
            "la tabla esté en columnas que no he sabido separar: escribe las líneas a mano."
        )
    elif leida.base_imponible is not None and not leida.suman_las_lineas:
        suma = sum(linea.importe or 0.0 for linea in leida.lineas)
        leida.avisos.append(
            f"Las líneas suman {suma:.2f} y la base imponible del papel dice "
            f"{leida.base_imponible:.2f}. Puede faltar alguna línea por leer."
        )
    if leida.base_imponible is not None and leida.total is not None and not leida.cuadra_el_total:
        leida.avisos.append(
            "La base más el IVA no da el total que he leído. Repasa los tres números."
        )
    if not leida.numero_factura:
        leida.avisos.append(
            "No he encontrado el número de factura. Escríbelo tú: el cuaderno lo pide."
        )
    if not leida.proveedor_nif:
        leida.avisos.append("No he encontrado el NIF del proveedor.")
