"""La semilla y su etiqueta: leer el papel y cuadrar las dos cifras (T10, 03/10/2026).

## Qué hay aquí y qué no

Aquí está **la lógica pura** del T10, la que se puede probar sin base de datos y sin servidor:

  1. **Leer las letras de la etiqueta** de una semilla y sacar de ahí los campos que un agricultor
     necesita para saber qué está sembrando. Primero se busca **el texto de verdad** (el PDF del
     proveedor trae las letras dentro) y el lector de fotos **solo si no hay texto** —un escaneo o
     una foto del móvil—; eso no se escribe otra vez aquí: se usa `facturas.texto_del_documento`,
     que es la puerta única de la lectura de papeles. Si no hay lector de letras instalado, **se
     dice** y la ficha se rellena a mano.
  2. **Cuadrar la dosis por hectárea con la cantidad total**, que es lo que el T10 existe para no
     confundir.

Lo que **no** hay aquí: ni una escritura. **La lectura de una etiqueta no guarda nada.** Lo que
devuelve es una **propuesta**, y una semilla solo existe cuando el agricultor dice que sí a lo que se
le ha enseñado (`POST /api/semillas`). Por eso este módulo no toca la base de datos: no puede crear
un hecho ni queriendo.

## Las dos cifras, y por qué no se pueden mezclar

«Dos kilos por hectárea» y «dos kilos» son cosas distintas, y confundirlas es un error de diez veces
(el caso A02 del contrato). En esta casa eso se resuelve de tres maneras, y las tres están aquí:

  1. **Cada cifra tiene su nombre y su unidad** (`dosis_por_ha` con `unidad_dosis`, `cantidad_total`
     con `unidad_cantidad`), y no se guardan nunca en el mismo sitio.
  2. **La que falta se calcula si se puede** —`dosis × hectáreas = total`— y **se dice que se ha
     calculado** (`dosis_calculada` / `cantidad_total_calculada`). Un número calculado se puede
     revisar; uno inventado, no.
  3. **Si no se puede calcular, se queda vacía**: `None` es «no lo sé», y **nunca** se convierte en
     un cero, que diría «no sembré nada» (la regla que gobierna el proyecto entero,
     `docs/T02_VALORES_POR_DEFECTO.md`).

Y una cuarta, que es de unidades: **los litros no se suman con los kilos**. Si la dosis viene en
`kg/ha` y el total en litros, no se convierte nada —no sabemos la densidad— y se dice que las dos
cifras no se pueden comparar, en vez de sacar un número que no significa nada
(`servicios.se_pueden_sumar`).
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass, field

from . import facturas, legal, servicios, textos

# Cómo se han rellenado los datos de una semilla. Se guarda en `Semilla.leida_de` y no es un adorno:
# si dentro de un año un poder germinativo está mal, lo primero que hay que saber es si lo escribió
# una persona o lo leyó un programa.
CAMINOS_DE_LECTURA = ("mano", "foto", "pdf", "escaneo", "texto")

# En qué se mide una dosis de siembra y en qué se cuenta una cantidad de semilla.
#
# **Esta lista es nuestra, y se dice.** No hay un catálogo oficial cargado de unidades de siembra como
# el de los productos (el SIEX publica 287 catálogos, y este no está entre los que tenemos): son las
# formas en que se escribe una dosis de semilla en un papel de verdad —kilos por hectárea, gramos por
# hectárea, unidades (plantones de hortícolas) y litros—. Si el agricultor necesita otra, la ficha se
# rellena igual: la unidad es un campo de texto en la base de datos; esto es solo la lista que se
# ofrece para no teclear.
UNIDADES_DE_DOSIS = ("kg/ha", "g/ha", "ud/ha", "L/ha")
UNIDADES_DE_CANTIDAD = ("kg", "g", "ud", "L")

# Los datos de la etiqueta, con el nombre con el que se cuentan en la respuesta y en la pantalla.
CAMPOS_DE_LA_ETIQUETA = (
    "especie",
    "variedad",
    "casa_comercial",
    "proveedor",
    "numero_lote_proveedor",
    "dosis_recomendada_por_ha",
    "unidad_dosis",
    "fecha_envasado",
    "fecha_caducidad",
    "poder_germinativo_pct",
    "pureza_pct",
    "tratada",
)


# --------------------------------------------------------------------------
# El texto del papel
# --------------------------------------------------------------------------


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    return "".join(caracter for caracter in descompuesto if not unicodedata.combining(caracter))


def _plano(texto: str) -> str:
    """El texto en minúsculas, sin acentos y con los espacios de sobra fuera. Para comparar."""
    return re.sub(r"\s+", " ", _sin_acentos(texto).lower()).strip()


def _lineas(texto: str) -> list[tuple[str, str]]:
    """Cada línea del papel, en su forma original y en su forma llana (para buscar)."""
    devueltas: list[tuple[str, str]] = []
    for linea in (texto or "").replace("\r\n", "\n").split("\n"):
        limpia = linea.strip()
        if limpia:
            devueltas.append((limpia, _plano(limpia)))
    return devueltas


def _etiqueta_y_valor(linea_llana: str, etiquetas: tuple[str, ...]) -> str | None:
    """El valor que va detrás de una etiqueta, o `None` si esa línea no habla de eso.

    **Se busca por el texto de la etiqueta y no por la posición** (`AGENTS.md`, la receta de leer un
    fichero oficial): las etiquetas de semilla cambian de sitio y de orden entre casas, y buscar «la
    columna 3» devolvería un dato de otro sitio en cuanto cambie la maqueta.
    """
    for etiqueta in etiquetas:
        encontrado = re.match(
            rf"^{re.escape(etiqueta)}\s*(?:n[.ºo°]?\s*)?[:\-]\s*(.+)$",
            linea_llana,
        )
        if encontrado:
            valor = encontrado.group(1).strip(" .;:-")
            if valor:
                return valor
    return None


def _valor_con_su_forma_original(linea_original: str, linea_llana: str, etiquetas):
    """Lo mismo, pero devolviendo el valor **como está escrito en el papel** y no en minúsculas.

    Importa para lo que lee el agricultor: «Veza común» no es «veza comun», y el nombre de una
    variedad se escribe como lo escribe quien la vende.
    """
    valor_llano = _etiqueta_y_valor(linea_llana, etiquetas)
    if valor_llano is None:
        return None
    # El valor llano empieza en algún sitio de la línea original: se busca por su longitud, que es la
    # misma porque `_plano` no cambia el número de letras que no sean acentos… salvo cuando quita un
    # acento. Por eso se corta la línea original por el mismo separador y se coge lo de después.
    corte = re.match(r"^[^:\-]*(?:[:\-])\s*", linea_original)
    if not corte:
        return valor_llano
    devuelto = linea_original[corte.end() :].strip(" .;:-")
    return devuelto or valor_llano


def _primer_token(valor: str | None, maximo: int = 80) -> str:
    """Solo la primera palabra: un número de lote es un número de lote, no la frase de al lado."""
    if not valor:
        return ""
    return valor.split()[0].strip(".,;:")[:maximo]


# --------------------------------------------------------------------------
# La propuesta
# --------------------------------------------------------------------------


@dataclass
class EtiquetaLeida:
    """Lo que se ha podido leer de una etiqueta. **Es una propuesta, no un dato.**

    Cada campo vacío es «no lo he leído», y así se queda: la pantalla los enseña vacíos para que el
    agricultor los rellene. Lo que **no** se hace es rellenar un hueco con un valor parecido ni con
    un cero.
    """

    especie: str = ""
    variedad: str = ""
    casa_comercial: str = ""
    proveedor: str = ""
    numero_lote_proveedor: str = ""
    dosis_recomendada_por_ha: float | None = None
    unidad_dosis: str = ""
    fecha_envasado: dt.date | None = None
    fecha_caducidad: dt.date | None = None
    poder_germinativo_pct: float | None = None
    pureza_pct: float | None = None
    # Sí / no / **no lo sé**. Tres respuestas, no dos (`docs/T02_VALORES_POR_DEFECTO.md`).
    tratada: bool | None = None

    # Cómo se ha leído y con qué. `como_se_leyo` en el idioma de `CAMINOS_DE_LECTURA`.
    como_se_leyo: str = ""
    idioma_del_lector: str = ""
    texto_crudo: str = ""
    # Por qué no se ha podido leer (o por qué se ha leído a medias). Son frases del servidor.
    avisos: list[str] = field(default_factory=list)
    # **Lo que el papel dice y no se puede apuntar tal cual.** Es distinto de un aviso: aquí hay un
    # dato delante, y lo que falta es cómo apuntarlo. El caso que lo trajo: una caducidad escrita
    # «02/2027» (mes y año) —inventarle el día sería afirmar algo que el papel no dice— y una dosis
    # «120 kg» sin decir por hectárea.
    dudas: list[str] = field(default_factory=list)

    @property
    def leidos(self) -> list[str]:
        """Los campos que **de verdad** se han leído. Es lo que se le enseña al agricultor."""
        devueltos: list[str] = []
        for campo in CAMPOS_DE_LA_ETIQUETA:
            valor = getattr(self, campo)
            if valor not in (None, ""):
                devueltos.append(campo)
        return devueltos

    @property
    def hay_algo(self) -> bool:
        return bool(self.leidos)

    def resumen(self) -> dict:
        return {
            "campos_leidos": self.leidos,
            "cuantos": len(self.leidos),
            "como_se_leyo": self.como_se_leyo,
            "idioma_del_lector": self.idioma_del_lector,
        }


def leer_etiqueta(contenido: bytes) -> EtiquetaLeida:
    """Lee una etiqueta de semilla y devuelve **una propuesta**. No guarda nada.

    El camino del texto es el de siempre (`facturas.texto_del_documento`): el PDF del proveedor trae
    las letras dentro y se leen sin equivocarse; el escaneo y la foto del móvil pasan por el lector
    de letras, y si no está instalado se dice en vez de inventarse lo que pone el papel.
    """
    leida = EtiquetaLeida()
    lectura = facturas.FacturaLeida()
    texto = facturas.texto_del_documento(contenido, lectura)
    leida.como_se_leyo = lectura.como_se_leyo
    leida.idioma_del_lector = lectura.idioma_del_lector
    leida.avisos.extend(lectura.avisos)
    if not texto:
        if not leida.avisos:
            leida.avisos.append(textos.MENSAJES["SM1_etiqueta_ilegible"])
        return leida
    leida.texto_crudo = texto
    return lo_que_dice_la_etiqueta(leida, texto)


def lo_que_dice_la_etiqueta(leida: EtiquetaLeida, texto: str) -> EtiquetaLeida:
    """Saca los campos del texto de la etiqueta. **Todo lo que no encuentre se queda vacío.**

    Está separado de `leer_etiqueta` para poder probar el lector de campos **sin lector de letras**:
    el texto de una etiqueta de verdad, pegado en un `.txt`, se lee por el mismo camino que una foto
    (una vez que el lector de fotos ha hecho su trabajo, lo que queda es texto), y así la parte que
    de verdad se puede equivocar —las expresiones que buscan cada dato— se prueba en cualquier
    ordenador, tenga o no tenga instalado el programa que lee fotos.
    """
    lineas = _lineas(texto)

    def primero(etiquetas: tuple[str, ...]) -> str:
        for original, llana in lineas:
            valor = _valor_con_su_forma_original(original, llana, etiquetas)
            if valor:
                return valor.strip()[:200]
        return ""

    leida.especie = primero(("especie", "especie botanica", "nombre comun")) or leida.especie
    leida.variedad = primero(("variedad", "cv", "cultivar")) or leida.variedad
    leida.casa_comercial = primero(
        ("casa comercial", "casa", "marca", "obtentor", "envasado por", "envasado")
    ) or leida.casa_comercial
    leida.proveedor = primero(
        ("proveedor", "suministrado por", "distribuido por", "vendedor", "vende")
    ) or leida.proveedor
    leida.numero_lote_proveedor = _primer_token(
        primero(
            (
                "numero de lote",
                # **Estas cuatro formas son la misma y hay que escribirlas todas**, porque el texto se
                # compara en su forma llana: «N.º» se descompone en «n.o» y «Nº» en «no» (el símbolo
                # ordinal pierde la raya al quitar los acentos). Escribir solo «nº de lote» dejaba una
                # etiqueta de verdad sin su número de lote, en silencio.
                "n.o de lote",
                "no de lote",
                "n de lote",
                "lote",
                "partida",
            )
        )
    ) or leida.numero_lote_proveedor

    _lee_la_dosis(leida, lineas)
    _lee_las_fechas(leida, lineas, texto)
    _lee_los_porcentajes(leida, lineas)
    _lee_si_viene_tratada(leida, texto)
    return leida


def _lee_la_dosis(leida: EtiquetaLeida, lineas: list[tuple[str, str]]) -> None:
    """La dosis que recomienda el fabricante, **solo si el papel dice que es por hectárea**.

    Aquí está la mitad del T10. Un papel que dice «DOSIS: 120 kg» **no** ha dicho 120 kg por
    hectárea: puede ser lo que lleva el saco. Apuntarlo como dosis por hectárea sería el error de
    diez veces, así que en ese caso no se apunta nada y se le dice al agricultor lo que pone el
    papel, para que lo mire él.
    """
    for _original, llana in lineas:
        valor = _etiqueta_y_valor(llana, ("dosis recomendada", "dosis de siembra", "dosis", "siembra"))
        if not valor:
            continue
        numero = _numero_de(valor)
        if numero is None:
            continue
        unidad = _unidad_de(valor)
        if "/ha" in unidad.replace(" ", "") or "por hectarea" in llana or "por ha" in llana:
            leida.dosis_recomendada_por_ha = numero
            leida.unidad_dosis = (unidad or "").replace(" ", "")[:20]
            return
        leida.dudas.append(
            textos.MENSAJES["SM2_dosis_sin_decir_por_hectarea"].format(
                dice=f"{numero:g} {unidad}".strip()
            )
        )
        return


def _lee_las_fechas(leida: EtiquetaLeida, lineas: list[tuple[str, str]], texto: str) -> None:
    """Las dos fechas del papel. Una fecha de mes y año **no se completa con un día inventado**.

    Se prueban **todas** las formas en que una etiqueta escribe cada fecha antes de rendirse: un
    papel puede traer «ENVASADO: 02/2027» en una esquina y «FECHA DE ENVASADO: 12/01/2026» debajo.
    Lo primero es una duda que se enseña; lo segundo, un dato.
    """
    etiquetas_envasado = (
        "fecha de envasado",
        "fecha de envase",
        "fecha de empaquetado",
        "envasado",
        "empaquetado",
    )
    etiquetas_caducidad = (
        "fecha de caducidad",
        "fecha de vencimiento",
        "consumir antes de",
        "valido hasta",
        "valida hasta",
        "vencimiento",
        "caducidad",
    )
    leida.fecha_envasado, duda_envasado = _busca_una_fecha(lineas, etiquetas_envasado)
    if duda_envasado:
        leida.dudas.append(
            textos.MENSAJES["SM3_fecha_sin_dia"].format(
                que=textos.MENSAJES["SM4_el_envasado"], dice=duda_envasado
            )
        )
    leida.fecha_caducidad, duda_caducidad = _busca_una_fecha(lineas, etiquetas_caducidad)
    if duda_caducidad:
        leida.dudas.append(
            textos.MENSAJES["SM3_fecha_sin_dia"].format(
                que=textos.MENSAJES["SM5_la_caducidad"], dice=duda_caducidad
            )
        )
    if leida.fecha_caducidad is None and not duda_caducidad:
        # Ni la fecha ni una duda: la etiqueta no habla de la caducidad. Se dice, para que nadie crea
        # que la semilla «no caduca» ni que el programa se ha olvidado de mirarlo.
        leida.dudas.append(textos.MENSAJES["SM6_la_etiqueta_no_dice_la_caducidad"])


def _busca_una_fecha(
    lineas: list[tuple[str, str]], etiquetas: tuple[str, ...]
) -> tuple[dt.date | None, str]:
    """La primera fecha completa que traiga una de esas etiquetas, y si no, el mes y año que diga.

    Devuelve `(fecha, "")` cuando ha leído una fecha entera, `(None, "02/2027")` cuando el papel solo
    dice el mes y el año —que es una duda, no un dato— y `(None, "")` cuando no dice nada.
    """
    parcial = ""
    for _original, llana in lineas:
        valor = _etiqueta_y_valor(llana, etiquetas)
        if not valor:
            continue
        fecha = _fecha_de(valor)
        if fecha is not None:
            return fecha, ""
        mes_y_anio = _mes_y_anio(valor)
        if mes_y_anio and not parcial:
            parcial = f"{mes_y_anio[0]:02d}/{mes_y_anio[1]}"
    return None, parcial


def _lee_los_porcentajes(leida: EtiquetaLeida, lineas: list[tuple[str, str]]) -> None:
    """El poder germinativo y la pureza. **Los dos pueden no venir, y entonces se quedan vacíos.**"""
    for _original, llana in lineas:
        if leida.poder_germinativo_pct is None:
            valor = _etiqueta_y_valor(
                llana, ("poder germinativo", "germinacion", "facultad germinativa", "germinativo")
            )
            if valor:
                leida.poder_germinativo_pct = _porcentaje_de(valor)
        if leida.pureza_pct is None:
            valor = _etiqueta_y_valor(llana, ("pureza especifica", "pureza"))
            if valor:
                leida.pureza_pct = _porcentaje_de(valor)


def _lee_si_viene_tratada(leida: EtiquetaLeida, texto: str) -> None:
    """¿Viene tratada la semilla? Tres respuestas: sí, no, y no se sabe.

    **El orden importa y es el fallo que esto evita:** «SEMILLA NO TRATADA» contiene la palabra
    «tratada», así que buscarla primero convertiría una semilla sin tratar en una tratada —y al
    revés—, que es un dato con consecuencias (la semilla tratada tiene sus propias reglas de
    manejo). Se busca primero la negación, y **«no lo dice» no es «no»**.

    **Y las negaciones son más de una, y esto lo cazó la revisión.** Buscar solo `sin tratar` dejaba
    fuera la frase más normal de un saco —«SEMILLA SIN TRATAMIENTO», «NO LLEVA TRATAMIENTO», «NO SE HA
    APLICADO NINGÚN TRATAMIENTO»—, que acababa marcando la semilla como **tratada**, justo al revés de
    lo que dice el papel. Las dos listas están aquí, enteras y a la vista, para que la siguiente forma
    de escribirlo se añada en un solo sitio.
    """
    llano = _plano(texto)
    for negacion in NEGACIONES_DE_TRATAMIENTO:
        if negacion in llano:
            leida.tratada = False
            return
    for afirmacion in AFIRMACIONES_DE_TRATAMIENTO:
        if re.search(rf"\b{afirmacion}\b", llano):
            leida.tratada = True
            return


# Las formas de decir que la semilla **no** viene tratada. Se buscan antes que las afirmaciones y con el
# texto ya llano (minúsculas y sin tildes), así que van escritas así.
NEGACIONES_DE_TRATAMIENTO = (
    "no tratada",
    "no tratado",
    "no tratadas",
    "no tratados",
    "sin tratar",
    "sin tratamiento",
    "no viene tratada",
    "no viene tratado",
    "no lleva tratamiento",
    "no lleva ningun tratamiento",
    "no se ha aplicado ningun tratamiento",
    "no se ha aplicado tratamiento",
    "sin curar",
    "no curada",
)

# Y las de decir que sí. Son palabras sueltas, así que se buscan con límites de palabra.
AFIRMACIONES_DE_TRATAMIENTO = (
    "tratada",
    "tratado",
    "tratadas",
    "tratados",
    "curada",
    "curasemillas",
    "tratamiento",
)


# --------------------------------------------------------------------------
# Números, unidades y fechas de un papel
# --------------------------------------------------------------------------


def _numero_de(texto: str) -> float | None:
    """El primer número del texto, en formato español. `None` si no hay ninguno."""
    encontrado = re.search(r"\d+(?:[.,]\d+)?", texto or "")
    if not encontrado:
        return None
    return facturas.numero_espanol(encontrado.group(0))


# Las formas en que se escribe una unidad de semilla en un papel, **de la más larga a la más corta**:
# si se probara «kg» antes que «kilos», «120 kilos» saldría como «k» + basura. Es el mismo cuidado que
# con las palabras de un catálogo: la primera que encaja gana, así que la más específica va delante.
_UNIDADES_ESCRITAS = (
    r"millones\s+de\s+semillas",
    r"millones",
    r"semillas",
    r"unidades?",
    r"plantones?",
    r"uds?",
    r"ud",
    r"kilos?",
    r"kilogramos?",
    r"kg",
    r"gramos?",
    r"mililitros?",
    r"ml",
    r"litros?",
    r"g",
    r"l",
)
_UNIDAD_ESCRITA = re.compile(
    rf"(?:{'|'.join(_UNIDADES_ESCRITAS)})\s*(?:/|por\s*)?\s*(?:ha|hectareas?|m2|m²)?"
)

# **Y la unidad se guarda en su forma corta y de siempre**, no como la escriba el papel. Esto salió de
# la revisión, y el daño era real: el papel escribe «120 kg **por hectárea**» —que es como lo escribe
# media España, más normal que `kg/ha`— y lo que se guardaba era `kgporhectarea`. Eso no es una unidad,
# es una palabra: el desplegable de la dosis (que ofrece `kg/ha`, `g/ha`, `ud/ha` y `L/ha`) se quedaba
# sin su opción, y la siembra podía acabar sin unidad y sin descontar del almacén.
#
# Se traduce **lo que es la misma cosa dicha de otra manera**, y nada más: no se convierte una unidad
# en otra (los litros no son kilos) ni se inventa la que no viene.
_UNIDADES_EN_SU_FORMA_CORTA = {
    "kilo": "kg",
    "kilos": "kg",
    "kilogramo": "kg",
    "kilogramos": "kg",
    # **Las formas cortas también están aquí, y faltaban.** El texto se compara en su forma llana, así
    # que un papel que escribe «2 L/ha» llega aquí como `l/ha`, y esa clave no estaba: la unidad se
    # quedaba en minúscula y no coincidía con la que ofrece la pantalla (`L/ha`), así que el
    # desplegable de la dosis se quedaba sin su opción. Lo cazó la segunda pasada de la revisión.
    "kg": "kg",
    "g": "g",
    "l": "L",
    "ml": "mL",
    "ud": "ud",
    "gramo": "g",
    "gramos": "g",
    "litro": "L",
    "litros": "L",
    "mililitro": "mL",
    "mililitros": "mL",
    "unidad": "ud",
    "unidades": "ud",
    "uds": "ud",
    "millonesdesemillas": "millones",
    "millones": "millones",
    "semillas": "semillas",
    "planton": "plantones",
    "plantones": "plantones",
    "hectarea": "ha",
    "hectareas": "ha",
    "ha": "ha",
    "m2": "m2",
    "m²": "m2",
}


def _unidad_de(texto: str) -> str:
    """La unidad que va **detrás del número**, en su forma corta (`kg/ha`, `kg`, `ud/ha`).

    Se busca **detrás del número** y no en todo el texto: en «DOSIS: 120 kg/ha» la unidad es `kg/ha`,
    pero en «120 sacos de 25 l» lo que hay detrás del 120 no es una unidad y decirlo sería inventarse
    la unidad de la dosis.

    Y se devuelve **siempre en la misma forma** (`kg/ha`, no `kilos por hectárea`): la unidad es un dato
    con el que después se hacen cuentas y se eligen opciones en pantalla, así que dos maneras de
    escribir la misma unidad partirían en dos lo que es una sola cosa.
    """
    llano = _plano(texto)
    numero = re.search(r"\d+(?:[.,]\d+)?", llano)
    if not numero:
        return ""
    encontrado = _UNIDAD_ESCRITA.search(llano[numero.end() :])
    if not encontrado:
        return ""
    # «kg por hectárea», «kilos/hectárea» y «kg / ha» son la misma unidad: se parten por el separador
    # y cada trozo se pone en su forma corta. Lo que no se reconozca se queda como está escrito (mejor
    # una unidad rara que una inventada).
    trozo = re.sub(r"\s+", " ", encontrado.group(0)).strip()
    partes = re.split(r"\s*(?:/|\bpor\b)\s*", trozo)
    partes = [re.sub(r"\s+", "", parte) for parte in partes if parte.strip()]
    partes = [_UNIDADES_EN_SU_FORMA_CORTA.get(parte, parte) for parte in partes]
    if not partes:
        return ""
    return "/".join(partes[:2]) if len(partes) > 1 else partes[0]


def _porcentaje_de(texto: str) -> float | None:
    """Un porcentaje del papel. Una cifra sin `%` **no** se toma por un porcentaje.

    «PUREZA 99,2 %» son 99,2; «PUREZA 99,2» puede ser cualquier cosa. Sin el signo se queda vacío y
    el agricultor lo escribe, que es mejor que apuntar un número que quizá era otra cosa.
    """
    if "%" not in (texto or ""):
        return None
    numero = _numero_de(texto)
    if numero is None or numero < 0 or numero > 100:
        return None
    return numero


def _fecha_de(texto: str) -> dt.date | None:
    """Una fecha del papel **con día, mes y año**. Sin día no hay fecha, y no se inventa."""
    encontrado = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", texto or "")
    if not encontrado:
        return None
    dia, mes, anio = (int(grupo) for grupo in encontrado.groups())
    if anio < 100:
        anio += 2000
    try:
        return dt.date(anio, mes, dia)
    except ValueError:
        return None


def _mes_y_anio(texto: str) -> tuple[int, int] | None:
    """Una fecha escrita como mes y año («02/2027»), que es como la escriben muchas etiquetas."""
    encontrado = re.search(r"\b(\d{1,2})[/\-.](\d{4})\b", texto or "")
    if not encontrado:
        return None
    mes, anio = int(encontrado.group(1)), int(encontrado.group(2))
    if not 1 <= mes <= 12:
        return None
    return mes, anio


# --------------------------------------------------------------------------
# La dosis y la cantidad total: la cuenta que no se puede confundir
# --------------------------------------------------------------------------


def cuadra_las_dos_cifras(
    *,
    dosis_por_ha: float | None,
    unidad_dosis: str | None,
    cantidad_total: float | None,
    unidad_cantidad: str | None,
    superficie_ha: float | None,
) -> dict:
    """Deja la dosis y la cantidad total en su sitio, y dice lo que ha tenido que calcular.

    Devuelve las seis cosas —las dos cifras, sus dos unidades y los dos avisos de «esto lo he
    calculado»— más `falta` (lo que hay que preguntar) y `avisos` (lo que hay que decir).

    LO QUE HACE, EN ORDEN:

      1. **Si vienen las dos**, no se toca ninguna. Y se comprueba la aritmética
         (`dosis × hectáreas = total`, con un 1 % de margen por los redondeos del papel): si no
         cuadra, **se dice con los dos números** y no se bloquea nada —el agricultor puede tener
         razón: puede haber sembrado a mano una parte—.
      2. **Si falta la total** y hay dosis y hectáreas, se calcula y se marca
         (`cantidad_total_calculada`). La unidad del total sale del numerador de la dosis
         (`legal.unidad_de_una_dosis`: `kg/ha` → `kg`), que es lo que evita mezclar litros con kilos.
      3. **Si falta la dosis** y hay total y hectáreas, se calcula igual (`dosis_calculada`).
      4. **Si no se puede calcular**, se queda **vacía** y se pide. Nunca un cero: un cero diría
         «no sembré nada».

    Y la unidad del total que venga dicha **manda** sobre la que se deduzca: si el agricultor dice
    que son 2.000 unidades, son unidades, aunque la dosis venga en kg/ha. Lo que no se hace es
    convertirlas (`servicios.se_pueden_sumar`): sin la equivalencia, esa cuenta sería inventada.
    """
    dosis = dosis_por_ha
    unidad_de_la_dosis = (unidad_dosis or "").strip() or None
    total = cantidad_total
    unidad_del_total = (unidad_cantidad or "").strip() or None
    superficie = superficie_ha

    dosis_calculada = False
    total_calculado = False
    falta: list[str] = []
    avisos: list[str] = []
    sin_cuadrar: str = ""

    if dosis is not None and dosis < 0:
        dosis = None
        avisos.append(textos.MENSAJES["SM7_una_dosis_negativa"])
    if total is not None and total < 0:
        total = None
        avisos.append(textos.MENSAJES["SM7_una_dosis_negativa"])
    if superficie is not None and superficie <= 0:
        superficie = None

    if dosis is not None and total is None and superficie is not None:
        total = round(dosis * superficie, 4)
        total_calculado = True
        if not unidad_del_total:
            deducida = legal.unidad_de_una_dosis(unidad_de_la_dosis)
            unidad_del_total = deducida or None
        avisos.append(
            textos.MENSAJES["SM8_la_cantidad_la_he_calculado"].format(
                total=legal.formatea_numero(total),
                unidad=unidad_del_total or textos.MENSAJES["SM9_sin_unidad"],
                dosis=legal.formatea_numero(dosis),
                unidad_dosis=unidad_de_la_dosis or textos.MENSAJES["SM9_sin_unidad"],
                superficie=legal.formatea_numero(superficie),
            )
        )
    elif total is not None and dosis is None and superficie is not None:
        dosis = round(total / superficie, 4)
        dosis_calculada = True
        if not unidad_de_la_dosis:
            unidad_de_la_dosis = f"{unidad_del_total}/ha" if unidad_del_total else None
        avisos.append(
            textos.MENSAJES["SM10_la_dosis_la_he_calculado"].format(
                dosis=legal.formatea_numero(dosis),
                unidad_dosis=unidad_de_la_dosis or textos.MENSAJES["SM9_sin_unidad"],
                total=legal.formatea_numero(total),
                unidad=unidad_del_total or textos.MENSAJES["SM9_sin_unidad"],
                superficie=legal.formatea_numero(superficie),
            )
        )
    elif dosis is not None and total is not None and superficie is not None:
        esperado = round(dosis * superficie, 4)
        if esperado > 0 and abs(esperado - total) > max(0.01, esperado * 0.01):
            sin_cuadrar = textos.MENSAJES["SM11_las_dos_cifras_no_cuadran"].format(
                dosis=legal.formatea_numero(dosis),
                unidad_dosis=unidad_de_la_dosis or textos.MENSAJES["SM9_sin_unidad"],
                superficie=legal.formatea_numero(superficie),
                esperado=legal.formatea_numero(esperado),
                total=legal.formatea_numero(total),
                unidad=unidad_del_total or textos.MENSAJES["SM9_sin_unidad"],
            )
            avisos.append(sin_cuadrar)
        # Y las unidades también se comprueban: litros con kilos no se comparan, y decirlo es lo que
        # impide que alguien mire los dos números y crea que cuadran.
        if (
            unidad_del_total
            and unidad_de_la_dosis
            and legal.unidad_de_una_dosis(unidad_de_la_dosis)
            and not servicios.se_pueden_sumar(
                unidad_del_total, legal.unidad_de_una_dosis(unidad_de_la_dosis)
            )
        ):
            avisos.append(
                textos.MENSAJES["SM12_las_unidades_no_se_pueden_comparar"].format(
                    una=unidad_del_total, otra=unidad_de_la_dosis
                )
            )
            # **Y no se convierte nada.** Se quedan las dos como estaban: una cuenta entre litros y
            # kilos necesita la densidad, que no sabemos.
            total_calculado = False
            dosis_calculada = False

    if dosis is None and total is None:
        falta.append("dosis_por_ha")
        falta.append("cantidad_total")
    elif dosis is None:
        falta.append("dosis_por_ha")
    elif total is None:
        falta.append("cantidad_total")
    if superficie is None:
        falta.append("superficie_ha")

    return {
        "dosis_por_ha": dosis,
        "unidad_dosis": unidad_de_la_dosis,
        "cantidad_total": total,
        "unidad_cantidad": unidad_del_total,
        "dosis_calculada": dosis_calculada,
        "cantidad_total_calculada": total_calculado,
        "superficie_ha": superficie,
        "falta": falta,
        "avisos": avisos,
        "no_cuadra": sin_cuadrar,
    }
