"""La bandeja documental: el papel que llega, desde que se sube hasta que se archiva (T08, S10).

## Qué es esto y por qué no es «los papeles»

`app/routers/documentos_api.py` es **el archivador**: los papeles ya revisados, ordenados en carpetas,
con su índice para copiar. Esto es **la bandeja de entrada**: lo que acaba de llegar y todavía no se
ha mirado. Son dos vistas del **mismo papel** —la misma fila de `documentos_anexos`, el mismo fichero
en disco— y eso es a propósito: si la bandeja guardara sus propios papeles, el agricultor tendría el
mismo contrato en dos sitios y uno de los dos estaría viejo.

## Las dos reglas que no se pueden romper, y cómo se cumplen aquí

1. **El original no se toca nunca.** El fichero se guarda tal y como llegó y no se reescribe con lo
   que el programa *cree* haber leído. Lo que sostiene esa promesa es un dato: la **huella** del
   fichero (`huella_de`), que se calcula al subirlo y **no se vuelve a calcular ni al leer ni al
   confirmar**. Si se recalculara al confirmar y el fichero hubiera cambiado, el programa diría que
   es otro papel y el duplicado se colaría. Hay una prueba que lo muerde.
2. **Lo leído es una propuesta, no un dato.** La lectura vive en `propuesta_de_factura`, que devuelve
   un diccionario **aparte de los campos del papel**: nada de lo que se lee entra en `titulo`,
   `fecha` o `quien` por su cuenta. Lo que entra en el papel es lo que el agricultor ha aceptado
   (`campos_aceptados`), y **confirmar no acepta campos**: hay que haber revisado antes, y por eso
   «confirmar sin mirar» no es un descuido posible, es una puerta que no existe.

## Lo que este módulo NO hace, y por qué se dice

* **No lee facturas**: para eso está `app/facturas.py`, que ya existe y que es el modelo exacto de
  «proponer sin guardar». Aquí solo se **traduce** su lectura (`FacturaLeida`) a lo que la bandeja
  guarda, con los importes en texto decimal y **sin ninguna palabra sobre lo buena que es la
  lectura**. Ni porcentajes, ni «leído correctamente», ni confianza: el corpus para medirlo (T07) no
  existe, así que no se puede afirmar nada de eso. Lo que se dice de cada línea es un hecho
  comprobable (la cuenta cuadra o no).
* **No escribe en la base de datos ni habla con FastAPI.** Esto son cuentas y decisiones, y se puede
  probar entero sin servidor. Quien guarda es `app/routers/bandeja_api.py`.
* **No crea un gasto, ni una factura, ni una venta.** Enlazar escribe un vínculo con algo que **ya
  existe** (`CLASES_DE_VINCULO`), y esa es la mitad del ticket: la bandeja no es una segunda puerta
  por la que entren datos al cuaderno.

## Por qué este módulo importa `facturas` (y con él `ocr`, `servicios` y `models`)

Porque reutilizarlo es el encargo: escribir un segundo lector de facturas sería tener dos caminos que
un día dicen cosas distintas. Lo que se importa es el **lector**, no la base de datos: aquí no hay ni
una consulta.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from decimal import Decimal

from . import catalogos, dinero, facturas, ocr

# ==========================================================================
# 1. De qué es el papel: los tipos
# ==========================================================================
#
# Los cuatro tipos que ya había (`catalogos.TIPOS_DOCUMENTO`) **no se tocan ni se sustituyen**: son
# los que nombra el documento de la Junta (contrato, factura, albarán de Sigfito) más «otros», que
# está porque el documento sigue con «etc.». Lo que este ticket añade son cuatro tipos que hoy no
# tienen sitio y que se están apuntando mal:
#
#   · **`inspeccion`**: el certificado de la ITV o de la ITEAF de una máquina. Es el más importante de
#     los cuatro y el que el T14 dejó escrito que faltaba (`app/models.InspeccionDeMaquina.documento_id`
#     ya apunta a un papel, y hasta hoy ese papel se apuntaba como «otros»).
#   · **`ticket`**: el tique del gasóleo o del taller. No es una factura —no lleva NIF casi nunca— y
#     meterlo como «factura» ensuciaría la lista de facturas.
#   · **`albaran`**: el albarán de entrega de grano o de compra, que **no es** el de envases de
#     Sigfito. Son dos papeles distintos y con el mismo nombre se confundirían.
#   · **`analitica`**: el boletín de un laboratorio en papel. Sus números tienen su sección propia;
#     aquí está **el papel**, que es lo que se enseña en una inspección.
TIPOS_NUEVOS = ("inspeccion", "ticket", "albaran", "analitica")

# Las etiquetas de los cuatro nuevos, con el mismo estilo que las que ya hay en `catalogos` («Un
# contrato», «Una factura»). Van aquí **además de** en el catálogo compartido a propósito: este
# fichero tiene que funcionar hoy, y el catálogo lo integra el coordinador. En cuanto las etiquetas
# estén allí, manda el catálogo (`etiqueta_de_papel` lo prefiere) y estas quedan de repuesto.
ETIQUETAS_NUEVAS = {
    "inspeccion": "Un certificado de inspección",
    "ticket": "Un ticket de compra",
    "albaran": "Un albarán de entrega",
    "analitica": "Un boletín de análisis",
}

# La lista entera, **sin repetir y en orden**: los cuatro de siempre primero —para que el agricultor
# los encuentre donde estaban— y luego los nuevos. `dict.fromkeys` es lo que hace que esto siga
# valiendo el día que las etiquetas y los tipos se integren en el catálogo: si el catálogo ya trae
# «inspeccion», no aparece dos veces.
TIPOS_DE_PAPEL = tuple(dict.fromkeys((*catalogos.TIPOS_DOCUMENTO, *TIPOS_NUEVOS)))


def etiqueta_de_papel(tipo: str) -> str:
    """Cómo se llama ese tipo de papel, en palabras del agricultor.

    Se prefiere la etiqueta del catálogo compartido: es la que usa el resto del programa y la que
    acabará teniendo los cuatro tipos nuevos. Si todavía no la tiene, se usa la de aquí.
    """
    if tipo in catalogos.ETIQUETA_DOCUMENTO:
        return catalogos.ETIQUETA_DOCUMENTO[tipo]
    return ETIQUETAS_NUEVAS.get(tipo, catalogos.ETIQUETA_DOCUMENTO["otros"])


def es_un_tipo_de_papel(tipo: str) -> bool:
    """Si ese tipo es uno de los que se pueden apuntar. Un tipo inventado se rechaza con la lista."""
    return tipo in TIPOS_DE_PAPEL


def carpeta_sugerida_para(tipo: str) -> str | None:
    """En qué carpeta de «los papeles» cae un papel de ese tipo, si se sabe.

    **Es una sugerencia, no una obligación**, igual que `catalogos.CARPETAS_SUGERIDAS`: el agricultor
    archiva como quiere y puede cambiarla. Se pone porque un papel que llega por la bandeja y se queda
    en «Otros» es un papel que hay que volver a colocar a mano, y esa vuelta no aporta nada. Lo que
    **no** se hace es inventar una carpeta que no exista: los tipos de los que no se sabe nada caen a
    «Otros», que es donde va todo lo que no se ha decidido.
    """
    return {
        "factura": "Facturas",
        "ticket": "Facturas",
        "albaran": "Facturas",
        "contrato": "Contratos",
        "albaran_sigfito": "Envases",
        "inspeccion": "Licencias y permisos",
    }.get(tipo)


# ==========================================================================
# 2. En qué punto va la revisión: los estados
# ==========================================================================
#
# Cuatro estados, y los cuatro se ven en la pantalla con su palabra. La regla de fondo es una:
# **mientras no esté confirmado, el papel está «sin revisar»**, y eso se ve.
#
#   · `recien_subido` — está el fichero y nadie ha dicho de qué es.
#   · `clasificado` — ya se sabe de qué es. Aquí se queda también **después de leerlo**: leer no
#     cambia de estado a nada, porque leer no es revisar. Ese es el detalle que más importa.
#   · `propuesta_revisada` — el agricultor ha mirado la lectura y ha decidido qué queda
#     (`campos_aceptados`). Todavía **no** es un dato del cuaderno: los campos del papel siguen como
#     estaban.
#   · `confirmado` — lo aceptado ha pasado al papel, con quién y cuándo. Aquí el papel sale de la
#     bandeja y se ve en «los papeles».
RECIEN_SUBIDO = "recien_subido"
CLASIFICADO = "clasificado"
PROPUESTA_REVISADA = "propuesta_revisada"
CONFIRMADO = "confirmado"

ESTADOS = (RECIEN_SUBIDO, CLASIFICADO, PROPUESTA_REVISADA, CONFIRMADO)

# Los que cuentan como «sin revisar»: todo menos el confirmado. Se escribe como resta y no a mano
# para que el día que haya un estado más no se quede fuera sin que nadie lo note. **Y es la lista que usa
# la consulta de la bandeja** (`in_(ESTADOS_SIN_REVISAR)`), que deja fuera a los papeles que ya tenía el
# agricultor antes de este ticket: esos no tienen estado ninguno (nacieron antes), así que no han pasado por
# la bandeja y no aparecen en ella.
ESTADOS_SIN_REVISAR = tuple(estado for estado in ESTADOS if estado != CONFIRMADO)


def es_un_estado(estado: str) -> bool:
    """Si ese estado existe. Un estado que no está en la lista no se puede guardar."""
    return estado in ESTADOS


def esta_sin_revisar(estado: str) -> bool:
    """Si ese papel todavía está en la bandeja, esperando a alguien.

    **Esto es lo que la pantalla llama «sin revisar», y es la mitad del ticket**: un papel que nadie
    ha mirado no puede parecer un papel revisado.

    Se pregunta por lo que **no** está confirmado, y no por la lista de los tres estados de antes: un papel
    con un estado que no se entiende (un dato tocado a mano, una versión más nueva del programa) no está
    confirmado, así que se trata como pendiente. Es la misma prudencia que en todo el programa: ante la
    duda, un papel de más esperando en la bandeja es mejor que un papel que nadie ha mirado dado por bueno.
    """
    return estado != CONFIRMADO


def estado_al_subirlo(tipo: str | None) -> str:
    """Con qué estado nace un papel que se acaba de subir.

    Si el agricultor ya ha dicho de qué es, nace **clasificado** (y no tiene sentido hacerle pasar por
    «recién subido», que es un estado del que no se aprende nada). Si no lo ha dicho —«no lo sé
    todavía»— nace **recién subido**, y la pantalla dice que falta decir de qué es.
    """
    return CLASIFICADO if tipo else RECIEN_SUBIDO


def estado_al_clasificar() -> str:
    """Decir de qué es un papel lo deja clasificado, y no toca nada más.

    No se pierde lo que hubiera: un papel clasificado otra vez sigue con su propuesta y con lo que el
    agricultor hubiera aceptado.
    """
    return CLASIFICADO


def estado_al_revisar() -> str:
    """Mirar la lectura y decidir qué queda deja el papel en «propuesta revisada». **Nunca en
    confirmado**: confirmar es un acto aparte, con su botón, y el encargo lo pide así."""
    return PROPUESTA_REVISADA


def se_puede_confirmar(estado: str, *, hay_algo_aceptado: bool) -> bool:
    """Si ese papel se puede confirmar ya.

    **La regla entera del ticket, en una función**: no se confirma lo que nadie ha mirado. Hace falta
    que esté en «propuesta revisada» **y** que haya algo aceptado, porque un papel revisado sin nada
    aceptado es un papel del que no se ha decidido qué queda.
    """
    return estado == PROPUESTA_REVISADA and hay_algo_aceptado


def se_puede_descartar_la_propuesta(*, hay_propuesta: bool, hay_algo_aceptado: bool) -> bool:
    """Si tiene sentido decir «esta lectura no me sirve».

    Solo cuando hay una lectura que descartar y **no** se ha aceptado ya nada de ella: si ya se
    aceptó, lo que hay que hacer es revisar otra vez, no descartar (descartar ahí borraría una
    decisión del agricultor sin decírselo).
    """
    return hay_propuesta and not hay_algo_aceptado


# ==========================================================================
# 3. La huella: el mismo papel no entra dos veces
# ==========================================================================
#
# El SHA-256 del fichero **no se escribe otra vez aquí**. El programa ya tiene dos copias
# (`ocr.huella`, que es la que usa el lector de facturas, y `extractos.huella_del_fichero`) y una
# tercera sería una tercera cosa que un día cambia sola. Se usa la del lector de facturas, que es
# quien lee el mismo fichero que se sube aquí, y se reexporta con el nombre de este ticket para que
# quien lea el router no tenga que averiguarlo. Hay una prueba que exige que sean la misma.
huella_de = ocr.huella


def es_el_mismo_papel(una_huella: str | None, otra_huella: str | None) -> bool:
    """Si esas dos huellas son del mismo fichero.

    **Una huella vacía no es igual a otra huella vacía.** Un papel apuntado a mano —«el contrato está
    en el cajón»— no tiene fichero, y por tanto no tiene huella: decir que dos papeles sin fichero son
    el mismo sería inventarse un duplicado, y ese error acabaría impidiendo apuntar dos contratos
    distintos que no se han escaneado.
    """
    if not una_huella or not otra_huella:
        return False
    return str(una_huella) == str(otra_huella)


def decision_sobre_el_duplicado(
    huella: str | None, *, papeles: list[dict] | None = None, facturas: list[dict] | None = None
) -> dict:
    """¿Este fichero ya lo tenía el agricultor? Devuelve la decisión, **y no escribe nada**.

    Se mira en dos sitios, y los dos importan:

    * **los papeles** de la bandeja y de «los papeles» (los que tienen la misma huella), porque subir
      dos veces el mismo papel no puede crear dos fichas; y
    * **las facturas de compra** (`models.Factura.huella`, que ya existía), porque el mismo papel
      puede haber entrado por la puerta de las facturas y volver a entrar por aquí.

    `papeles` y `facturas` son listas de diccionarios ya leídos (`{id, titulo, estado, ...}`) a
    propósito: así esta decisión se prueba sin base de datos, que es lo que permite comprobar que
    **el aviso sale antes de apuntar nada**.
    """
    iguales = [papel for papel in (papeles or []) if es_el_mismo_papel(huella, papel.get("huella"))]
    if iguales:
        return {"duplicado": True, "donde": "la_bandeja", "ya_estaba": iguales[0]}

    repetidas = [
        factura for factura in (facturas or []) if es_el_mismo_papel(huella, factura.get("huella"))
    ]
    if repetidas:
        return {"duplicado": True, "donde": "una_factura_de_compra", "ya_estaba": repetidas[0]}

    return {"duplicado": False, "donde": None, "ya_estaba": None}


# ==========================================================================
# 4. La lectura: una propuesta, y nada más que una propuesta
# ==========================================================================
#
# De qué papeles se puede proponer algo hoy, y de cuáles no. Son dos —la factura y el ticket—, y el
# ticket va con la factura porque un tique es una factura pequeña: el mismo lector saca el proveedor,
# la fecha y el total. **Lo demás no se lee**, y no se disimula: un contrato no tiene un lector, y
# decir «no he podido leerlo» cuando lo que pasa es que no se intenta sería mentir por omisión.
TIPOS_QUE_SE_LEEN = ("factura", "ticket")

# Lo que se le ofrece al agricultor de una lectura de cabecera. Es la lista de campos que se pueden
# aceptar y corregir, y está en un solo sitio para que la pantalla y el servidor no puedan discrepar.
CAMPOS_DE_LA_CABECERA = (
    "proveedor",
    "proveedor_nif",
    "numero_factura",
    "fecha",
    "base_imponible",
    "cuota_iva",
    "tipo_iva_pct",
    "total",
)
CAMPOS_DE_DINERO = ("base_imponible", "cuota_iva", "tipo_iva_pct", "total")
CAMPOS_DE_FECHA = ("fecha",)


class DatoQueNoVale(ValueError):
    """Un dato que el agricultor ha escrito y no se entiende.

    Lleva **la clave del texto** que hay que enseñarle (`textos.mensaje(...)`), y no la frase: los
    textos viven en `textos.py`, y este módulo no los escribe. Quien la ve es el router, que la
    convierte en el aviso de la pantalla.
    """

    def __init__(self, clave: str):
        super().__init__(clave)
        self.clave = clave


def se_puede_leer(tipo: str) -> bool:
    """Si de un papel de ese tipo se puede proponer algo hoy."""
    return tipo in TIPOS_QUE_SE_LEEN


def _dinero_como_texto(valor, *, es_precio: bool = False) -> str | None:
    """Un número leído, en el texto decimal con el que se guarda. `None` sigue siendo «no lo sé».

    Se entra por `dinero.cantidad_a_decimal` y **no** por `dinero.a_decimal`, y el motivo está
    escrito: el lector de facturas devuelve números de coma flotante (es lo que da su expresión
    regular) y `a_decimal` los rechaza a la cara. `cantidad_a_decimal` los convierte **por su texto**
    (`repr`), que es exacto para lo que el lector ha leído: `1234.56` sigue siendo `1234.56` y no
    1234.5599999999999.

    Se redondea al céntimo (o a las cifras de un precio, que son más) porque un dinero con quince
    decimales no es dinero: es la basura de la coma flotante y nadie la puede cuadrar.
    """
    if valor is None:
        return None
    decimales = dinero.DECIMALES_DE_UN_PRECIO if es_precio else dinero.DECIMALES_DE_UN_IMPORTE
    return dinero.a_texto(dinero.cantidad_a_decimal(valor), decimales)


def _cantidad_como_texto(valor) -> str | None:
    """Una cantidad (kilos, litros), sin ceros de relleno: `500` y `1.5`, no `500.000000`."""
    if valor is None:
        return None
    numero = dinero.cantidad_a_decimal(valor)
    return format(numero.normalize(), "f") if numero is not None else None


def _fecha_como_texto(fecha: dt.date | None) -> str | None:
    return fecha.isoformat() if fecha else None


def propuesta_de_factura(
    leida: facturas.FacturaLeida, *, leido_en: dt.datetime | None = None
) -> dict:
    """Traduce lo que ha leído el lector de facturas a lo que la bandeja guarda. **No guarda nada.**

    Lo que se devuelve es un diccionario que se puede escribir en JSON tal cual (las fechas y los
    importes van en texto), y **con los campos aparte de los del papel**: esto es una propuesta, y el
    sitio donde vive es este, no `titulo`, `fecha` ni `quien`.

    **Lo que NO lleva, y es lo más importante de la función: ninguna medida de la calidad de la
    lectura.** No hay porcentaje, ni «confianza alta», ni «leído correctamente». El corpus para
    medirla (T07) no existe, así que afirmarlo sería inventarse un número. De cada línea se dice lo
    único que se puede comprobar sin corpus: **si la cuenta cuadra** (cantidad × precio = importe),
    que es aritmética y no opinión.
    """
    return {
        "clase": "factura",
        "como_se_leyo": leida.como_se_leyo or "",
        "leido_en": (leido_en or dt.datetime.now()).isoformat(timespec="seconds"),
        "campos": {
            "proveedor": leida.proveedor or None,
            "proveedor_nif": leida.proveedor_nif or None,
            "numero_factura": leida.numero_factura or None,
            "fecha": _fecha_como_texto(leida.fecha),
            "base_imponible": _dinero_como_texto(leida.base_imponible),
            "cuota_iva": _dinero_como_texto(leida.cuota_iva),
            "tipo_iva_pct": _dinero_como_texto(leida.tipo_iva_pct),
            "total": _dinero_como_texto(leida.total),
        },
        "lineas": [
            {
                "descripcion": linea.descripcion,
                "cantidad": _cantidad_como_texto(linea.cantidad),
                "unidad": linea.unidad or "",
                "precio_unitario": _dinero_como_texto(linea.precio_unitario, es_precio=True),
                "importe": _dinero_como_texto(linea.importe),
                "numero_registro": linea.numero_registro or "",
                # Un hecho comprobable, no una opinión: la multiplicación de esta línea da su importe.
                "la_cuenta_cuadra": bool(linea.cuadra),
                "producto_sugerido": linea.producto_sugerido or "",
            }
            for linea in leida.lineas
        ],
        # Los avisos del lector, tal cual: son suyos y ya están escritos para el agricultor
        # («en 3 líneas la cuenta no da el importe»). No se reescriben aquí para no tener dos
        # maneras de decir lo mismo.
        "avisos": list(leida.avisos),
        # Las dos cuentas que el lector sí puede comprobar. Son hechos, y por eso se enseñan.
        "cuadra_el_total": bool(leida.cuadra_el_total),
        "suman_las_lineas": bool(leida.suman_las_lineas),
    }


def propuesta_sin_leer(motivo: str, *, leido_en: dt.datetime | None = None) -> dict:
    """La propuesta de un papel del que **no se ha podido proponer nada**, con su motivo.

    `motivo` es **la clave de un texto** (`textos.mensaje`), no la frase: aquí no se escriben textos.
    Se guarda igual, para que al volver a abrir el papel se siga sabiendo por qué no hay nada, en vez
    de encontrar un hueco sin explicación.
    """
    return {
        "clase": "ninguna",
        "como_se_leyo": "",
        "leido_en": (leido_en or dt.datetime.now()).isoformat(timespec="seconds"),
        "campos": {},
        "lineas": [],
        "avisos": [motivo],
        "cuadra_el_total": False,
        "suman_las_lineas": False,
    }


def a_json(propuesta: dict | None) -> str | None:
    """La propuesta, en el texto que se guarda. `None` no es `"null"`: un papel sin propuesta no
    tiene ninguna, y eso es una columna vacía, no un JSON que diga «nada»."""
    if propuesta is None:
        return None
    return json.dumps(propuesta, ensure_ascii=False)


def de_json(texto: str | None) -> dict | None:
    """La propuesta guardada, de vuelta. Lo que no se puede leer **no revienta**: es «no lo sé».

    Una columna de texto puede acabar con cualquier cosa dentro (una migración a medias, un fichero
    tocado a mano). Que eso tumbe la ficha del papel con un error del servidor sería peor que decir
    que de ese papel no consta ninguna lectura.
    """
    if not texto:
        return None
    try:
        leido = json.loads(texto)
    except (ValueError, TypeError):
        return None
    return leido if isinstance(leido, dict) else None


def tiene_algo(propuesta: dict | None) -> bool:
    """Si esa propuesta trae algo que mirar (campos o líneas). Una propuesta vacía no es una propuesta."""
    if not propuesta:
        return False
    return bool(propuesta.get("campos")) or bool(propuesta.get("lineas"))


def campos_de_la_propuesta(propuesta: dict | None) -> dict:
    """Solo los campos de cabecera de una propuesta, y solo los que existen.

    Se filtra por `CAMPOS_DE_LA_CABECERA` para que lo que se le enseña al agricultor y lo que se
    puede aceptar sean **la misma lista**: si la lectura trajera un campo de más, no llegaría a la
    pantalla como si fuera aceptable.
    """
    if not propuesta:
        return {}
    return {
        campo: propuesta.get("campos", {}).get(campo)
        for campo in CAMPOS_DE_LA_CABECERA
        if campo in (propuesta.get("campos") or {})
    }


def campos_aceptados(campos: dict | None) -> dict:
    """Lo que el agricultor ha aceptado, normalizado y listo para guardar.

    Tres reglas, y las tres tienen consecuencia:

    1. **Un campo en blanco es «no lo sé», no «déjalo como estaba».** Se guarda como `None` y al
       aplicarlo al papel lo deja vacío: si borra un importe porque el papel no lo trae, el papel no
       puede quedarse con el que el programa había leído.
    2. **Los importes van como texto decimal** (`"980.10"`), que es como viaja el dinero en todo el
       programa. Un importe que no se entiende **no se guarda a medias**: se levanta `DatoQueNoVale`.
    3. **Una fecha sin sentido no se inventa.** Se admite lo que se escribe en España
       (`31/12/2026`) y el formato de la base (`2026-12-31`); lo que no encaje, se dice.
    """
    limpio: dict = {}
    for campo in CAMPOS_DE_LA_CABECERA:
        valor = (campos or {}).get(campo)
        if isinstance(valor, str):
            valor = valor.strip() or None
        if valor is None:
            limpio[campo] = None
            continue
        if campo in CAMPOS_DE_DINERO:
            try:
                numero = dinero.de_texto(str(valor))
            except dinero.ErrorDeDinero as fallo:
                raise DatoQueNoVale("T08_ese_importe_no_se_entiende") from fallo
            limpio[campo] = dinero.a_texto(numero) if numero is not None else None
            continue
        if campo in CAMPOS_DE_FECHA:
            limpio[campo] = fecha_escrita(str(valor))
            continue
        limpio[campo] = str(valor)
    return limpio


def fecha_escrita(texto: str | None) -> str | None:
    """Una fecha escrita a mano, en el formato de la base. Lo que no se entiende, se dice.

    Se admiten las dos formas que aparecen de verdad: la de la base (`2026-12-31`, que es la que
    manda el navegador cuando la fecha la ha puesto un campo de fecha) y la de un papel español
    (`31/12/2026`, `31-12-2026`), que es como la escribiría el agricultor a mano. Adivinar entre
    `03/04` y `04/03` **no se hace**: aquí el formato de la base no es ambiguo, y lo que llega del
    lector ya viene en ISO.
    """
    if texto is None:
        return None
    limpio = texto.strip()
    if not limpio:
        return None
    try:
        return dt.date.fromisoformat(limpio).isoformat()
    except ValueError:
        pass
    partes = limpio.replace("-", "/").replace(".", "/").split("/")
    if len(partes) == 3 and all(parte.isdigit() for parte in partes):
        dia, mes, anio = (int(parte) for parte in partes)
        if anio < 100:
            anio += 2000
        try:
            return dt.date(anio, mes, dia).isoformat()
        except ValueError as fallo:
            raise DatoQueNoVale("T08_esa_fecha_no_existe") from fallo
    raise DatoQueNoVale("T08_esa_fecha_no_se_entiende")


def hay_algo_aceptado(campos: dict | None) -> bool:
    """Si de esa revisión ha quedado algo.

    Un conjunto de campos con **todo en blanco** no es una decisión: es alguien que ha abierto la
    pantalla y la ha dejado. Confirmarlo dejaría un papel confirmado del que no se sabe nada, que es
    justo lo que el ticket prohíbe.
    """
    return any(valor not in (None, "") for valor in (campos or {}).values())


def para_el_papel(campos: dict | None) -> dict:
    """Lo que de lo aceptado pasa a los campos del papel: **su quién y su fecha, y nada más**.

    El papel tiene cuatro campos propios (`titulo`, `fecha`, `quien`, `notas`) y aquí se tocan dos:

    * `quien` es el proveedor del papel, que es exactamente lo que el agricultor ha aceptado;
    * `fecha` es la fecha del papel, no la de hoy.

    **`titulo` y `notas` no se tocan a propósito.** El título lo puso el agricultor al subirlo (o sale
    del nombre del fichero) y las notas son suyas: escribir ahí lo que el programa ha leído sería
    meter texto suyo sin que lo haya escrito, y eso es lo contrario de «lo leído es una propuesta».
    El importe y el número de factura **no tienen columna en el papel** y no se inventa una: quedan en
    lo aceptado, que es donde se ven.
    """
    aceptados = campos or {}
    fecha = aceptados.get("fecha")
    return {
        "quien": aceptados.get("proveedor") or None,
        "fecha": dt.date.fromisoformat(fecha) if fecha else None,
    }


# ==========================================================================
# 5. Enlazar con lo que ya existe
# ==========================================================================
#
# **Los cinco del encargo más la inspección.** Seis clases, y cada una apunta a una tabla que ya
# existe. Enlazar escribe un vínculo y **no crea nada**: ni un gasto, ni una factura, ni una venta.
#
# La sexta —`inspeccion`— está porque el T14 dejó el hueco abierto: `InspeccionDeMaquina.documento_id`
# ya apunta a un papel, y sin esta clase el certificado de una ITEAF no se podía atar a su inspección
# desde ningún sitio.
COMPRA = "compra"
GASTO = "gasto"
VENTA = "venta"
MAQUINA = "maquina"
TRABAJO = "trabajo"
INSPECCION = "inspeccion"

CLASES_DE_VINCULO = (COMPRA, GASTO, VENTA, MAQUINA, TRABAJO, INSPECCION)

# A qué suele ir un papel de cada tipo. **Es una sugerencia de pantalla, no una regla**: el programa
# no puede saber que una factura de la cooperativa no va con una máquina (un apero comprado también
# trae factura), así que no se prohíbe nada; lo que se hace es poner delante lo que suele ser.
CLASES_SUGERIDAS = {
    "factura": (COMPRA, GASTO),
    "ticket": (GASTO, COMPRA),
    "albaran": (VENTA, COMPRA, TRABAJO),
    "albaran_sigfito": (GASTO,),
    "contrato": (MAQUINA, TRABAJO, COMPRA),
    "inspeccion": (INSPECCION, MAQUINA),
    "analitica": (TRABAJO,),
    "otros": (),
}


def es_una_clase_de_vinculo(clase: str) -> bool:
    """Si esa clase existe. Una clase inventada se rechaza con la lista de las que hay."""
    return clase in CLASES_DE_VINCULO


def clases_que_se_sugieren(tipo: str) -> tuple[str, ...]:
    """Las clases que se le ponen delante al agricultor para un papel de ese tipo."""
    return CLASES_SUGERIDAS.get(tipo, ())


def ya_esta_vinculado(vinculos: list[dict], clase: str, entidad_id: int | str) -> bool:
    """Si ese papel ya está enlazado con eso.

    Enlazar dos veces lo mismo no es un error grave, pero es un dato de más que confunde: en una
    inspección parece que el papel demuestra dos veces lo mismo. Un vínculo quitado **no está en esta
    lista** (se borra su fila y queda el rastro en la auditoría), así que volver a enlazar algo que se
    quitó es un enlace nuevo y se admite.
    """
    return any(
        vinculo.get("clase") == clase and str(vinculo.get("entidad_id")) == str(entidad_id)
        for vinculo in (vinculos or [])
    )


# ==========================================================================
# 6. Las rectificativas
# ==========================================================================
#
# Una factura rectificada por otra: **las dos quedan**. La que rectifica dice a quién rectifica
# (`rectifica_a_id`) y la rectificada se marca por deducción —hay otra que la apunta—, que es lo que
# hace que no pueda haber dos sitios diciendo cosas distintas.
#
# Y una regla que hay que comprobar en algún sitio, porque un ciclo no se ve hasta que se mira la
# cadena entera: **un papel no puede rectificarse a sí mismo ni a quien ya lo rectifica**. Sin esta
# comprobación, dos toques equivocados dejan la cadena dando vueltas y la pantalla cuenta «esta
# factura rectifica a la que la rectifica», que no quiere decir nada.
def puede_rectificar_a(documento_id: int | None, al_que_rectifica_id: int | None) -> tuple[bool, str]:
    """Si ese papel puede rectificar a ese otro. Devuelve `(se_puede, clave_del_motivo)`."""
    if not al_que_rectifica_id:
        return False, "T08_dime_a_que_papel_rectifica"
    if documento_id and int(documento_id) == int(al_que_rectifica_id):
        return False, "T08_un_papel_no_se_rectifica_a_si_mismo"
    return True, ""


def hay_ciclo(cadena: dict[int, int | None], desde: int, hasta: int) -> bool:
    """Si poner «`desde` rectifica a `hasta`» cierra un círculo.

    `cadena` es «quién rectifica a quién» tal y como está hoy: `{rectificativa: rectificada}`. Se
    recorre hacia arriba desde `hasta` —a quién rectifica, y a quién rectifica ese, y así— y si se
    vuelve a pasar por `desde`, el círculo se cierra y no se deja. Se corta a los cien saltos porque
    una cadena de papeles más larga que eso no es una cadena de facturas: es un dato roto, y quedarse
    dando vueltas dentro sería peor que decirlo.
    """
    visto = {int(hasta)}
    actual: int | None = int(hasta)
    for _ in range(100):
        if actual is None:
            return False
        if int(actual) == int(desde):
            return True
        actual = cadena.get(int(actual))
        if actual is None:
            return False
        if int(actual) in visto:
            return False
        visto.add(int(actual))
    return False


# ==========================================================================
# 7. Lo que hay que decir de un papel, con sus palabras
# ==========================================================================


def clave_del_estado(estado: str) -> str:
    """La clave del texto de un estado: `estado_<estado>`.

    Se compone aquí, y no en el JavaScript, porque las claves son del servidor: el día que haya un
    estado más, la pantalla no tiene que enterarse. Y se comprueba que el estado exista, para que un
    estado roto diga «no lo sé» en vez de buscar una clave que no está.
    """
    return f"estado_{estado}" if es_un_estado(estado) else "estado_desconocido"


def clave_de_la_clase(clase: str) -> str:
    """La clave del texto de una clase de vínculo: `clase_<clase>`."""
    return f"clase_{clase}" if es_una_clase_de_vinculo(clase) else "clase_desconocida"


def describe_el_tamano(bytes_del_fichero: int | None) -> str:
    """El tamaño de un fichero, escrito para que se entienda.

    **No es una frase, son unidades**, igual que el `€` de `dinero.formatea`: el agricultor no lee
    «1048576» de un tirón y «1,0 MB» sí. Cuando no consta, se devuelve vacío: un `0 bytes` diría que
    el papel llegó vacío, que es otra cosa (y un fichero vacío no se admite).
    """
    if bytes_del_fichero is None:
        return ""
    if bytes_del_fichero < 1024:
        return f"{bytes_del_fichero} bytes"
    if bytes_del_fichero < 1024 * 1024:
        return f"{_con_coma(bytes_del_fichero / 1024)} KB"
    return f"{_con_coma(bytes_del_fichero / (1024 * 1024))} MB"


def _con_coma(numero: float) -> str:
    """Un número con decimales, con la coma de aquí: `1,4` y no `1.4`."""
    return f"{numero:.1f}".replace(".", ",")


def titulo_por_defecto(nombre_del_fichero: str | None, tipo: str) -> str:
    """Cómo se llama un papel del que el agricultor no ha escrito el nombre.

    Se usa el nombre del fichero **sin su extensión**, que es lo que tiene delante cuando lo elige
    (`factura-abril.pdf` → «factura-abril»): es reconocible y lo escribió él. Si no hay nombre, se usa
    el del tipo («Una factura»), porque un papel sin título es un papel que no se vuelve a encontrar
    —y el título es obligatorio en `documentos_anexos`—.
    """
    limpio = (nombre_del_fichero or "").strip()
    if "." in limpio:
        limpio = limpio.rsplit(".", 1)[0]
    limpio = limpio.strip()[:200]
    return limpio or etiqueta_de_papel(tipo)


# ==========================================================================
# 8. Las palabras con las que se busca un papel
# ==========================================================================


def se_parece_a_lo_que_se_busca(texto_buscado: str | None, *campos: str | None) -> bool:
    """Si alguno de esos campos contiene lo que el agricultor ha escrito para buscar.

    Se compara **sin acentos y en minúsculas**, que es como busca la gente: «albaran» tiene que
    encontrar «Albarán». Sin esto, el buscador de la bandeja fallaría justo con las palabras del
    campo (que llevan tilde) y parecería roto.
    """
    buscado = _plano(texto_buscado or "")
    if not buscado:
        return True
    return any(buscado in _plano(campo or "") for campo in campos)


def _plano(texto: str) -> str:
    """Texto en minúsculas, sin acentos y con los espacios de sobra fuera.

    Es el mismo truco del lector de facturas (`facturas._plano`), y se escribe aquí otra vez porque
    aquel es privado de su módulo: importar una función con guion bajo de otro fichero ata los dos
    para siempre, y esto son cuatro líneas que no van a cambiar.
    """
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    sin_acentos = "".join(caracter for caracter in descompuesto if not unicodedata.combining(caracter))
    return re.sub(r"\s+", " ", sin_acentos.lower()).strip()


# ==========================================================================
# 9. Los importes de una propuesta, para poder enseñarlos
# ==========================================================================


def importes_de_una_propuesta(propuesta: dict | None) -> dict[str, Decimal | None]:
    """Los importes de una propuesta, en `Decimal`, para que quien los enseñe los formatee.

    Se devuelven en `Decimal` (y no en texto ni en coma flotante) porque **el formateo del dinero es
    de `dinero.formatea`**, que es el único sitio del programa que sabe escribir `1.234,56 €`. Y lo
    que no consta sigue siendo `None`: un importe en blanco no es un cero.
    """
    if not propuesta:
        return {}
    salida: dict[str, Decimal | None] = {}
    for campo in CAMPOS_DE_DINERO:
        valor = propuesta.get("campos", {}).get(campo)
        salida[campo] = dinero.de_texto(valor) if valor else None
    return salida
