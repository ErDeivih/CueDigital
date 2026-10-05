"""Borradores: convertir lo que el agricultor dice en un apunte a medio hacer.

Esta es la aplicación práctica de la idea de "salida estructurada" para modelos
pequeños: **el esquema es el contrato, y el modelo no puede salirse de él**.

Cómo está montado, y por qué así:

1. **Primero las reglas, y funcionan hoy.** Todo lo que se puede sacar sin ningún
   modelo se saca aquí, con reglas y con los catálogos que ya tiene la explotación
   (sus parcelas, sus productos, sus abonos). El agricultor que dice "hoy he echado
   dos litros de herbicida en el prado" obtiene un borrador relleno **sin contratar
   nada y sin conexión a ningún modelo**.

2. **El modelo es una mejora opcional, no un requisito.** El punto donde se enchufa
   está marcado más abajo, en `redacta_borrador`. Un modelo tendría que devolver
   EXACTAMENTE esta misma estructura. Con Outlines o Guidance se le fuerza el esquema
   en el momento de generar, así que no puede contestar "Aquí tienes tu JSON:" ni
   inventarse un campo. Y aunque se lo saltara, Pydantic lo rechaza al validar.

3. **Un dato que no se sabe, se deja en blanco.** Nunca se rellena "algo parecido".
   Si no se reconoce el producto, `producto_id` se queda vacío y se le pregunta. Un
   número de etiqueta inventado en un cuaderno de campo es una sanción; un hueco es
   una pregunta.

4. **Siempre se enseña lo que se ha entendido.** Cada dato extraído viaja con la
   frase exacta de la que salió, para que el agricultor pueda comprobarlo. Es la idea
   de "Generative UI": la respuesta no es un texto de chat, es una tarjeta con el
   formulario relleno y el botón de apuntarlo.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Normalización de texto
# --------------------------------------------------------------------------


def sin_tildes(texto: str) -> str:
    """Quita tildes y pasa a minúsculas.

    Hace falta porque lo que llega de un dictado o de una foto no trae las tildes
    donde uno espera, y "pulgon" tiene que encontrar "pulgón".
    """
    descompuesto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").lower()


def palabras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", sin_tildes(texto))


def numero_para_leer(valor: float) -> str:
    """Un número como lo escribe una persona: 2 -> "2", 2.5 -> "2,5", 2.43 -> "2,43".

    Hace falta porque los números que salen de una palabra ("dos litros") son enteros,
    y los que salen de una cifra ("2,5 litros") son decimales. Sin esto, el agricultor
    vería "2.0 ha" con un punto, que en castellano no se lee.
    """
    texto = f"{float(valor):.4f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


# --------------------------------------------------------------------------
# Números: en cifra y en palabra
# --------------------------------------------------------------------------

PALABRAS_NUMERO: dict[str, float] = {
    "cero": 0,
    "un": 1, "uno": 1, "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veinticinco": 25,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
    "cien": 100,
    "medio": 0.5,
    "media": 0.5,
    "unos": 1,
    "unas": 1,
}

# Las unidades que se reconocen, con su forma canónica.
UNIDADES: dict[str, str] = {
    "l": "L", "litro": "L", "litros": "L", "lt": "L", "litros.": "L",
    "ml": "mL", "cc": "mL", "mililitros": "mL",
    "kg": "kg", "kilo": "kg", "kilos": "kg", "quilo": "kg", "quilos": "kg",
    "g": "g", "gramo": "g", "gramos": "g",
    "ha": "ha", "hectarea": "ha", "hectareas": "ha",
    "t": "t", "tonelada": "t", "toneladas": "t",
    "%": "%",
}

UNIDADES_PATRON = "|".join(sorted((re.escape(u) for u in UNIDADES), key=len, reverse=True))


@dataclass(frozen=True)
class Cantidad:
    """Un número con su unidad, tal y como aparecía en la frase."""

    valor: float
    unidad: str
    bruto: str


def _a_numero(texto: str) -> float | None:
    limpio = texto.strip().replace(" ", "")
    # En castellano se escribe "0,8" y también "1.234,5".
    limpio = limpio.replace(".", "").replace(",", ".") if "," in limpio else limpio
    try:
        return float(limpio)
    except ValueError:
        return None


def extrae_cantidades(texto: str) -> list[Cantidad]:
    """Saca de la frase los números que llevan unidad.

    Reconoce tanto cifras ("2 litros", "0,8 l/ha") como palabras ("dos litros"),
    porque un dictado casi nunca devuelve cifras.
    """
    plano = sin_tildes(texto)
    encontradas: list[Cantidad] = []
    vistas: set[tuple[int, int]] = set()

    # 1. Cifras: "2 litros", "0,8 l", "2,5 ha"
    patron_cifra = re.compile(rf"(\d+(?:[.,]\d+)?)\s*({UNIDADES_PATRON})\b", re.IGNORECASE)
    for coincidencia in patron_cifra.finditer(plano):
        valor = _a_numero(coincidencia.group(1))
        unidad = UNIDADES.get(coincidencia.group(2).lower())
        if valor is None or unidad is None:
            continue
        encontradas.append(Cantidad(valor, unidad, coincidencia.group(0).strip()))
        vistas.add(coincidencia.span())

    # 2. Palabras: "dos litros", "medio litro", "tres hectareas"
    patron_palabra = re.compile(
        rf"\b({'|'.join(PALABRAS_NUMERO)})\s+({UNIDADES_PATRON})\b", re.IGNORECASE
    )
    for coincidencia in patron_palabra.finditer(plano):
        if any(inicio <= coincidencia.start() < fin for inicio, fin in vistas):
            continue
        valor = PALABRAS_NUMERO.get(coincidencia.group(1).lower())
        unidad = UNIDADES.get(coincidencia.group(2).lower())
        if valor is None or unidad is None:
            continue
        encontradas.append(Cantidad(valor, unidad, coincidencia.group(0).strip()))

    return encontradas


def extrae_por_unidad(texto: str) -> dict[str, float]:
    """La primera cantidad de cada unidad. Útil porque cada dato usa la suya."""
    resultado: dict[str, float] = {}
    for cantidad in extrae_cantidades(texto):
        resultado.setdefault(cantidad.unidad, cantidad.valor)
    return resultado


# --------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------

MESES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

MENSAJES_DE_FECHA = {
    "hoy": 0,
    "ayer": 1,
    "anteayer": 2,
    "antes de ayer": 2,
    "esta manana": 0,
    "esta tarde": 0,
    "anoche": 1,
}


def extrae_fecha(texto: str, hoy: dt.date | None = None) -> dt.date | None:
    """Entiende "hoy", "ayer", "el 3 de mayo" y "3/5".

    Decisión sobre el año: si la fecha que se deduce cae más de seis meses en el
    futuro, se entiende que es del año pasado. Es lo que pasa cuando en enero alguien
    dice "lo eché en diciembre": doce meses de diferencia no tienen sentido en un
    cuaderno, y seis meses de margen cubren la campaña entera.
    """
    hoy = hoy or dt.date.today()
    plano = sin_tildes(texto)

    for expresion, dias_atras in MENSAJES_DE_FECHA.items():
        if re.search(rf"\b{re.escape(expresion)}\b", plano):
            return hoy - dt.timedelta(days=dias_atras)

    # "el 3 de mayo", "3 de mayo"
    coincidencia = re.search(
        rf"\b(\d{{1,2}})\s+de\s+({'|'.join(MESES)})\b", plano
    )
    if coincidencia:
        dia, mes = int(coincidencia.group(1)), MESES[coincidencia.group(2)]
        return _fecha_con_ano_razonable(dia, mes, hoy)

    # "3/5", "03/05", "3-5-2026"
    coincidencia = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", plano)
    if coincidencia:
        dia, mes = int(coincidencia.group(1)), int(coincidencia.group(2))
        if coincidencia.group(3):
            ano = int(coincidencia.group(3))
            ano = ano + 2000 if ano < 100 else ano
            try:
                return dt.date(ano, mes, dia)
            except ValueError:
                return None
        return _fecha_con_ano_razonable(dia, mes, hoy)

    return None


def _fecha_con_ano_razonable(dia: int, mes: int, hoy: dt.date) -> dt.date | None:
    try:
        candidata = dt.date(hoy.year, mes, dia)
    except ValueError:
        return None
    if (candidata - hoy).days > 180:
        try:
            return dt.date(hoy.year - 1, mes, dia)
        except ValueError:
            return None
    return candidata


# --------------------------------------------------------------------------
# Reconocer cosas de la explotación
# --------------------------------------------------------------------------


# Palabras que no distinguen nada: artículos y preposiciones.
PALABRAS_VACIAS = {
    "el", "la", "los", "las", "de", "del", "en", "y", "e", "o", "u",
    "un", "una", "unos", "unas", "al", "con", "para",
}

# Sufijos de formulación de los productos. Un agricultor dice "ejemplo 25", no
# "Ejemplo 25 EC", y sin quitarlos no habría forma de reconocerlo.
FORMULACIONES = {
    "ec", "sc", "wg", "sl", "od", "cs", "ew", "wp", "sg", "gr", "dp",
    "fs", "me", "pb", "rb", "tb", "se", "zc", "ew", "ac", "as",
}


def _palabras_significativas(nombre: str) -> list[str]:
    """Las palabras de un nombre que de verdad sirven para reconocerlo.

    Se quitan los artículos ("El Prado" -> "prado"), los números y porcentajes
    ("Nitrato amónico 33,5%" -> "nitrato amonico") y los sufijos de formulación
    ("Ejemplo 25 EC" -> "ejemplo"). Lo que queda es lo que el agricultor dice de
    verdad.

    Se exigen tres letras mínimo: con dos, cualquier nombre coincidiría con cualquier
    palabra.
    """
    tokens = re.findall(r"[a-z0-9]+", sin_tildes(nombre))
    return [
        token
        for token in tokens
        if token not in PALABRAS_VACIAS
        and token not in FORMULACIONES
        and not token.isdigit()
        and len(token) >= 3
    ]


def busca_por_nombre(
    texto: str, candidatos: list, campo: str = "nombre"
) -> tuple[object | None, str | None]:
    """Busca en la frase una parcela, un producto o un abono.

    Devuelve el candidato y las palabras que lo han delatado, para poder enseñárselas
    al agricultor ("Lo has dicho así: «prado»").

    Cómo se compara, y por qué así:

    - **Se exige que aparezcan TODAS las palabras significativas del nombre**, no una
      cualquiera. Buscar por palabras sueltas haría que un producto llamado "Total"
      apareciese cada vez que alguien dice "en total", y que "Prado" saltase dentro de
      "emprado".
    - **Se queda con el nombre más largo que encaje.** Si hay una parcela "El Prado" y
      otra "El Prado Alto", y el agricultor dice "el prado alto", es la segunda.
    - **Un nombre sin palabras significativas no se busca.** "A1" o "La" no identifican
      nada, y aceptarlos sería inventar.
    """
    plano = sin_tildes(texto)
    en_la_frase = set(re.findall(r"[a-z0-9]+", plano))

    mejor: object | None = None
    mejor_bruto: str | None = None
    mejor_puntos = 0

    for candidato in candidatos:
        nombre = getattr(candidato, campo, None) or ""
        significativas = _palabras_significativas(nombre)
        if not significativas:
            continue
        if not all(palabra in en_la_frase for palabra in significativas):
            continue
        puntos = sum(len(palabra) for palabra in significativas)
        if puntos > mejor_puntos:
            mejor = candidato
            mejor_puntos = puntos
            mejor_bruto = " ".join(significativas)

    return mejor, mejor_bruto


# --------------------------------------------------------------------------
# Reconocer la intención
# --------------------------------------------------------------------------

CLAVES_TRATAMIENTO = (
    "he echado", "echado", "he tratado", "tratado", "pulverizado", "fumigado",
    "herbicida", "insecticida", "fungicida", "producto",
)
CLAVES_ABONO = ("abonado", "he abonado", "abono", "fertilizado", "fertilizante", "nitrato", "estercol")
CLAVES_COSECHA = ("cosechado", "he cogido", "cogido", "recogido", "he segado", "segado")
CLAVES_LABOR = {
    "siembra": ("sembrado", "he sembrado", "sembrar", "sembre"),
    "plantacion": ("plantado", "he plantado", "plantar", "plante"),
    "riego": ("regado", "he regado", "regar", "riego", "regue"),
    "poda": ("podado", "he podado", "poda", "podar", "pode"),
    "desbroce": ("desbrozado", "desbroce", "he desbrozado"),
    "laboreo": ("arado", "gradeado", "labrado", "he arado"),
}

CLAVES_JUSTIFICACION = {
    "Aviso de la Junta": ("aviso", "avisos", "la junta", "boletin"),
    "Me lo dijo mi técnico": ("tecnico", "asesor", "ingeniero", "el de la cooperativa"),
    "Me lo pidió el comprador": ("comprador", "cliente", "industria"),
    "Tratamiento de prevención": ("prevenir", "prevencion", "por si acaso"),
}

# Palabras que delatan el problema. No pretenden ser un catálogo: son las que de
# verdad salen en una conversación. Si no se reconoce ninguna, se deja en blanco.
CLAVES_PLAGA = (
    "pulgon", "pulgones", "hierba", "hierbas", "malas hierbas", "avena", "vallico",
    "mildiu", "oidio", "roya", "septoria", "fusarium", "botritis", "mosca",
    "oruga", "gorgojo", "pulgilla", "chinche", "acaros", "arano rojo", "trips",
    "topillo", "caracoles", "babosas", "cochinilla", "antracnosis",
)


def reconoce_tipo(texto: str) -> str:
    """Qué ha hecho: echar producto, abonar, cosechar o un trabajo del campo."""
    plano = sin_tildes(texto)
    if any(clave in plano for clave in CLAVES_ABONO):
        return "fertilizacion"
    if any(clave in plano for clave in CLAVES_TRATAMIENTO):
        return "tratamiento"
    if any(clave in plano for clave in CLAVES_COSECHA):
        return "cosecha"
    for tipo, claves in CLAVES_LABOR.items():
        if any(clave in plano for clave in claves):
            return tipo
    return "tratamiento"


def reconoce_justificacion(texto: str) -> str | None:
    plano = sin_tildes(texto)
    for justificacion, claves in CLAVES_JUSTIFICACION.items():
        if any(clave in plano for clave in claves):
            return justificacion
    if any(clave in plano for clave in CLAVES_PLAGA):
        return "Vi la plaga o la hierba en el campo"
    return None


def reconoce_plaga(texto: str) -> str | None:
    """Devuelve la palabra del problema tal y como se dijo, con mayúscula."""
    plano = sin_tildes(texto)
    for clave in CLAVES_PLAGA:
        if clave in plano:
            return clave.capitalize()
    return None


# --------------------------------------------------------------------------
# El borrador
# --------------------------------------------------------------------------

# Qué hace falta para poder guardar cada tipo de apunte. Se usa para decirle al
# agricultor exactamente qué le falta, en vez de un "faltan datos".
OBLIGATORIOS: dict[str, tuple[str, ...]] = {
    "tratamiento": ("parcela_id", "fecha", "justificacion", "producto_id"),
    "fertilizacion": ("parcela_id", "fecha", "fertilizante_id", "kg_ha_producto"),
    "cosecha": ("parcela_id", "fecha"),
    "riego": ("parcela_id", "fecha"),
    "siembra": ("parcela_id", "fecha"),
    "plantacion": ("parcela_id", "fecha"),
    "poda": ("parcela_id", "fecha"),
    "desbroce": ("parcela_id", "fecha"),
    "laboreo": ("parcela_id", "fecha"),
}

# Qué pregunta hay que hacer por cada dato que falta. Se reutilizan las preguntas del
# asistente: el agricultor ve la misma frase que vería rellenándolo a mano.
ETIQUETA_DE_CAMPO = {
    "parcela_id": "comun.parcela_id",
    "fecha": "comun.fecha",
    "justificacion": "tratamiento.justificacion",
    "producto_id": "tratamiento.producto_id",
    "fertilizante_id": "fertilizacion.fertilizante_id",
    "kg_ha_producto": "fertilizacion.kg_ha_producto",
    "superficie_ha": "comun.superficie_ha",
}


def _apunta(
    entendido: list[dict],
    etiqueta: str,
    valor,
    campo: str | None = None,
    bruto: str | None = None,
) -> None:
    """Apunta un dato entendido, con la frase de la que salió y dónde va.

    `campo` es el nombre del dato en el formulario, o None si se ha entendido pero no
    se puede colocar solo. Un `campo` vacío es importante: significa "he oído esto,
    pero no sé dónde ponerlo, decídelo tú". Es el caso de "dos litros", que puede ser
    la dosis por hectárea o el total, y adivinar mal ahí es un error de diez veces.
    """
    if valor in (None, ""):
        return
    entrada: dict = {"etiqueta": etiqueta, "valor": valor, "campo": campo}
    if bruto:
        entrada["bruto"] = bruto
    entendido.append(entrada)


# "por hectárea" dicho de cualquier forma. Decide si un número de litros es una dosis.
POR_HECTAREA = re.compile(r"/\s*ha\b|por\s+(la\s+)?hectarea|por\s+ha\b|en\s+cada\s+hectarea")


def redacta_borrador(
    texto: str,
    *,
    parcelas: list | None = None,
    productos: list | None = None,
    abonos: list | None = None,
    hoy: dt.date | None = None,
) -> dict:
    """Convierte una frase en un apunte a medio hacer.

    **Aquí es donde se enchufaría un modelo de lenguaje.** La firma no cambiaría: un
    modelo recibiría la frase y los catálogos, y tendría que devolver esta misma
    estructura. Con Outlines o Guidance se le fuerza el esquema al generar; sin ellos,
    se valida con Pydantic y, si no cuadra, se cae a las reglas de aquí. En ningún
    caso el modelo escribe directamente en el cuaderno: esto solo produce un borrador
    que el agricultor tiene que confirmar.

    `fuente` dice de dónde ha salido: "reglas" hoy, "modelo" cuando se enchufe.
    """
    parcelas = parcelas or []
    productos = productos or []
    abonos = abonos or []
    hoy = hoy or dt.date.today()
    entendido: list[dict] = []

    tipo = reconoce_tipo(texto)
    datos: dict = {}

    # --- dónde ---
    parcela, bruto_parcela = busca_por_nombre(texto, parcelas, "alias")
    if parcela is not None:
        datos["parcela_id"] = parcela.id
        _apunta(entendido, "comun.parcela_id", parcela.alias, "parcela_id", bruto_parcela)

    # --- cuándo ---
    fecha = extrae_fecha(texto, hoy)
    if fecha is not None:
        datos["fecha"] = fecha.isoformat()
        _apunta(entendido, "comun.fecha", fecha.isoformat(), "fecha")

    # --- qué producto o qué abono ---
    if tipo == "fertilizacion":
        abono, bruto_abono = busca_por_nombre(texto, abonos, "nombre")
        if abono is not None:
            datos["fertilizante_id"] = abono.id
            _apunta(
                entendido,
                "fertilizacion.fertilizante_id",
                abono.nombre,
                "fertilizante_id",
                bruto_abono,
            )
        por_unidad = extrae_por_unidad(texto)
        if "kg" in por_unidad:
            datos["kg_ha_producto"] = por_unidad["kg"]
            _apunta(
                entendido,
                "fertilizacion.kg_ha_producto",
                por_unidad["kg"],
                "kg_ha_producto",
                f"{numero_para_leer(por_unidad['kg'])} kg",
            )
        elif "t" in por_unidad:
            kilos = por_unidad["t"] * 1000
            datos["kg_ha_producto"] = kilos
            _apunta(
                entendido,
                "fertilizacion.kg_ha_producto",
                kilos,
                "kg_ha_producto",
                f"{numero_para_leer(por_unidad['t'])} t",
            )
    else:
        producto, bruto_producto = busca_por_nombre(texto, productos, "nombre_comercial")
        if producto is not None:
            datos["producto_id"] = producto.id
            _apunta(
                entendido,
                "tratamiento.producto_id",
                producto.nombre_comercial,
                "producto_id",
                bruto_producto,
            )

    # --- el problema y el motivo ---
    if tipo == "tratamiento":
        plaga = reconoce_plaga(texto)
        if plaga:
            datos["plaga"] = plaga
            _apunta(entendido, "tratamiento.plaga", plaga, "plaga")
        justificacion = reconoce_justificacion(texto)
        if justificacion:
            datos["justificacion"] = justificacion
            _apunta(entendido, "tratamiento.justificacion", justificacion, "justificacion")

    # --- cuánta superficie ---
    por_unidad = extrae_por_unidad(texto)
    superficie = por_unidad.get("ha")
    clave_superficie = "superficie_ha" if tipo == "fertilizacion" else "superficie_tratada_ha"
    # **`parcela.superficie_ha is not None` no es un detalle** (03/10/2026, A7). La superficie de una tierra
    # puede ser «no lo sé» (una tierra traída del cuaderno de la Junta sin esa casilla), y sin esta
    # comprobación esto reventaba con un `TypeError` al dictar «he echado dos litros en el prado»: comparar
    # un número con `None` no se puede. Antes no reventaba porque la tierra valía `0.0`, y lo que hacía era
    # peor: **cambiaba las hectáreas que había dicho el agricultor por un cero**. Sin saber la superficie, se
    # respeta la que él ha dicho y el servidor avisa de que falta el dato de la tierra.
    if (
        superficie is not None
        and parcela is not None
        and parcela.superficie_ha is not None
        and superficie > parcela.superficie_ha
    ):
        # Se queda la de la parcela, que es la que consta. El agricultor la puede
        # cambiar en el asistente, y el servidor volverá a comprobarlo de todas formas.
        superficie = parcela.superficie_ha
    if superficie is not None:
        datos[clave_superficie] = superficie
        _apunta(
            entendido,
            "comun.superficie_ha",
            superficie,
            clave_superficie,
            f"{numero_para_leer(superficie)} ha",
        )

    # --- cuánto producto ---
    # Aquí está la trampa de esta función. "Dos litros" puede ser la dosis por
    # hectárea o el total empleado, y confundirlos es un error de diez veces en un
    # dato que la ley mira. Así que NO se adivina:
    #   - si dice "por hectárea", es la dosis;
    #   - si además ha dicho la superficie, se reparte y se enseña la cuenta;
    #   - si no, se apunta lo que se ha oído SIN colocarlo, y se le pregunta.
    litros = por_unidad.get("L")
    if tipo == "tratamiento" and litros is not None:
        if POR_HECTAREA.search(sin_tildes(texto)):
            datos["dosis"] = litros
            datos.setdefault("unidad_dosis", "L/ha")
            _apunta(
                entendido,
                "tratamiento.dosis",
                litros,
                "dosis",
                f"{numero_para_leer(litros)} L/ha",
            )
        elif superficie:
            datos["dosis"] = round(litros / superficie, 4)
            datos.setdefault("unidad_dosis", "L/ha")
            _apunta(
                entendido,
                "tratamiento.dosis",
                datos["dosis"],
                "dosis",
                f"{numero_para_leer(litros)} L en {numero_para_leer(superficie)} ha",
            )
        else:
            _apunta(
                entendido,
                "tratamiento.dosis",
                litros,
                None,
                f"{numero_para_leer(litros)} L",
            )

    # --- qué falta ---
    falta = []
    for campo in OBLIGATORIOS.get(tipo, ("parcela_id", "fecha")):
        if datos.get(campo) in (None, ""):
            falta.append({"campo": campo, "etiqueta": ETIQUETA_DE_CAMPO.get(campo, "")})

    return {
        "tipo": tipo,
        "datos": datos,
        "entendido": entendido,
        "falta": falta,
        "fuente": "reglas",
    }
