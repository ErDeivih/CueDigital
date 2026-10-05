"""Los contactos: la misma persona o empresa, apuntada una sola vez (T11, 03/10/2026).

**POR QUÉ EXISTE ESTE FICHERO, Y QUÉ ES LO QUE HACE**

En este programa el nombre de quien te vende el producto, de quien te compra la cosecha o de quien
te asesora está escrito **a mano, en texto libre**, en siete sitios distintos: el proveedor de una
factura, el de un albarán, el comprador de una venta, el laboratorio de un análisis, el proveedor de
un producto del catálogo, el de un artículo del almacén, y el nombre de un aplicador o de un asesor.
Eso quiere decir que el mismo señor se teclea una vez por cada papel que firma, y que dos formas de
escribir su nombre conviven sin que nadie sepa que son la misma persona.

Aquí está **la mitad que se puede probar sin base de datos**: qué campos guardan un nombre escrito,
qué papeles puede hacer un contacto, y —esto es lo importante— **cuándo dos nombres escritos se
pueden juntar en una ficha y cuándo no**.

**LO QUE ESTE FICHERO NO HACE, Y ES A PROPÓSITO**

No escribe nada. No toca la base de datos, no la abre y no tiene ninguna función que guarde. La
propuesta de la migración se calcula aquí y se enseña; quien la confirma es el agricultor, y quien
escribe es `routers/contactos_api.py`. Es la misma separación que en el T10 (`app/semillas.py`): una
lectura es una propuesta, y una propuesta no crea hechos.

**LA REGLA QUE GOBIERNA TODO LO DE ABAJO: NO SE FUSIONA NADA QUE NO SE PUEDA ASEGURAR**

El ticket lo dice con estas palabras: *«Dos personas distintas con el mismo nombre, un proveedor y su
hermano, «Cooperativa X» y «Cooperativa X S.L.», un nombre con una tilde y otro sin ella: si no se
puede asegurar que son el mismo, no se fusionan»*. De ahí salen las tres decisiones que están en el
código y que no se pueden «mejorar» sin romper el ticket:

  1. **El mismo nombre escrito igual (cambiando solo mayúsculas) sí se junta.** Todo en mayúsculas en
     una factura y con minúsculas en un albarán no son dos personas: es la misma tecleada de dos
     maneras. La comparación `clave_exacta` **no quita las tildes ni los puntos**: «José» y
     «Jose» no son lo mismo aquí, y por eso acaban en «se parecen» en vez de juntarse solos.
  2. **Que se parezcan se dice, y no se junta.** Una tilde de menos, un «S.L.» de más, una letra
     cambiada: se enseña al agricultor con los dos nombres delante para que decida él, y el programa
     **no toca nada**. El error de fusionar a un proveedor con su hermano no se puede deshacer: los
     documentos se quedarían apuntando a quien no es.
  3. **El mismo NIF es una prueba, y con prueba se puede juntar… si el nombre la acompaña.** Dos
     textos distintos con el mismo NIF/CIF son la misma persona o la misma empresa, y eso no es una
     sospecha: es la única excepción, y está escrita así en el ticket («o se juntan solo si hay una
     prueba que lo demuestre, como el mismo NIF»). **Pero el NIF no basta él solo** (y esto lo cazó la
     revisión independiente): un NIF tecleado mal es el error más fácil del mundo, así que la unión por
     NIF exige además que los nombres sean compatibles (`nombres_compatibles`). Si el NIF coincide y
     los nombres no tienen nada que ver, eso no es una prueba de nada: es que uno de los dos papeles
     está mal escrito, y se enseña para que decida el agricultor.

Y una cuarta, que sale de la segunda: **dos textos idénticos con dos NIF distintos NO se juntan**.
Eso es exactamente «dos personas distintas con el mismo nombre», y es la prueba que pide el contrato
en E5 («dos contactos homónimos no se mezclan»). El código los aparta y lo dice.
"""

from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Los papeles que puede hacer un contacto
# --------------------------------------------------------------------------
#
# **Un contacto puede hacer varios papeles a la vez, y eso es lo normal en el campo**: la misma
# cooperativa te vende la semilla, te compra el trigo y te lleva el remolque. Por eso los papeles van
# en su propia tabla (`models.PapelDeUnContacto`) y no en una columna: una columna sola obligaría a
# elegir uno, y elegir uno es perder los otros.
#
# Las claves son de máquina (van a la base de datos y a la API) y **las palabras que se leen están en
# `textos.py`** (`CONTACTOS["papeles"][clave]`), como todo lo que ve el agricultor. Hay una prueba
# que exige que cada clave de aquí tenga su texto allí: una clave sin texto deja un hueco en pantalla
# sin que nada reviente.
#
# **Ojo con la palabra «fitosanitario»**: está en la lista de palabras prohibidas de `textos.py`, así
# que el papel del que te vende el producto para las plantas se llama, en la pantalla, «quien te vende
# el producto». Aquí la clave sí lo dice, porque la clave no la lee nadie.
PAPELES: tuple[str, ...] = (
    "proveedor",
    "proveedor_semilla",
    "proveedor_abono",
    "comprador",
    "asesor",
    "aplicador",
    "transportista",
    "taller",
    "laboratorio",
    "veterinario",
    "arrendador",
    "otro",
)


# --------------------------------------------------------------------------
# Dónde está escrito hoy un nombre, y con qué papel
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CampoDeTexto:
    """Una columna del cuaderno donde el agricultor ha escrito un nombre a mano.

    Los cinco datos que lleva cada una, y para qué sirve cada uno:

      · `tabla` y `campo` — **dónde está el texto**. Son la dirección del enlace: el enlace del T11
        se guarda como `(tabla, campo, registro_id)`, así que estas dos cadenas no se pueden cambiar
        sin migrar los enlaces que ya existan. Hay una prueba que las fija una por una.
      · `campo_nif` — la columna que tiene el NIF/CIF de ese mismo papel, cuando la hay. **Es la
        prueba** que permite juntar dos textos distintos (§ la cabecera). Cuando una tabla no la
        tiene, se queda en `None` y esa tabla nunca puede aportar pruebas: se dice, no se supone.
      · `papel` — qué papel hace por defecto quien está escrito ahí. Es lo que hace que la misma
        cooperativa acabe con dos papeles (proveedor en una factura y comprador en una venta) en vez
        de con uno.
      · `clave` — la clave del texto que nombra esa tabla en pantalla (`textos.CONTACTOS`). Aquí va
        la clave y no la frase: **ni una palabra para el agricultor fuera de `textos.py`**.
      · `referencia` — de qué columnas se saca el dato que le permite al agricultor reconocer de qué
        documento se trata («Factura 2026/00123», «el albarán del 12/03»). Se devuelven como una
        lista de trozos y **los junta la pantalla**: el servidor no compone frases. La fecha va
        aparte, en `campo_fecha`, para que la formatee la pantalla y no venga ya mezclada con el
        número.
    """

    tabla: str
    campo: str
    papel: str
    clave: str
    campo_nif: str | None = None
    referencia: tuple[str, ...] = ()
    # La columna con la fecha del documento, si la tiene. Vacío es «no tiene fecha», no «hoy».
    campo_fecha: str | None = None


# **Las siete puertas por las que hoy entra un nombre escrito a mano.** Se han buscado una por una
# mirando `models.py`, y están todas las que hay: no se ha inventado ninguna ni se ha dejado ninguna
# fuera a propósito. Lo que NO está aquí, y por qué:
#
#   · `tratamientos.aplicador_id` y `tratamientos.asesor_id` — **no son texto libre**: son claves a
#     las tablas `aplicadores` y `asesores`, que ya son fichas. Por eso el enlace se hace en esas dos
#     tablas y **el tratamiento queda enlazado de rebote** (el contacto al que apunta su aplicador).
#     Duplicar aquí el enlace sería tener dos verdades de lo mismo.
#   · `explotaciones.*` — son los datos del titular, no un contacto de la agenda.
#   · `semillas.proveedor` — la semilla es un artículo del almacén, y su proveedor es el del albarán
#     con el que entró (o el de la ficha del producto).
#   · **`articulos` NO tiene proveedor**, y esto se descubrió escribiendo la prueba que ata esta lista
#     a los modelos: el proveedor de un artículo del almacén es el de la **recepción** con la que
#     entró, no una columna suya. La lista tenía una puerta que no existía, y la prueba la cazó antes
#     de que llegara a producción. Es el motivo por el que `test_las_tablas_y_las_columnas_existen_de_verdad`
#     existe.
ENLACES: tuple[CampoDeTexto, ...] = (
    CampoDeTexto(
        tabla="facturas",
        campo="proveedor",
        campo_nif="proveedor_nif",
        papel="proveedor",
        clave="facturas",
        referencia=("numero_factura",),
        campo_fecha="fecha",
    ),
    CampoDeTexto(
        tabla="recepciones",
        campo="proveedor",
        campo_nif="proveedor_nif",
        papel="proveedor",
        clave="albaranes",
        referencia=("numero_albaran",),
        campo_fecha="fecha",
    ),
    CampoDeTexto(
        tabla="ventas_de_cosecha",
        campo="comprador",
        papel="comprador",
        clave="ventas",
        referencia=("numero_albaran",),
        campo_fecha="fecha",
    ),
    CampoDeTexto(
        tabla="analiticas",
        campo="laboratorio",
        campo_nif="nif_laboratorio",
        papel="laboratorio",
        clave="analisis",
        referencia=("numero_informe",),
        campo_fecha="fecha_toma_muestra",
    ),
    CampoDeTexto(
        tabla="productos_fitosanitarios",
        campo="proveedor",
        papel="proveedor",
        clave="productos",
        referencia=("nombre_comercial", "numero_registro"),
    ),
    CampoDeTexto(
        tabla="aplicadores",
        campo="nombre",
        campo_nif="nif",
        papel="aplicador",
        clave="aplicadores",
        referencia=(),
    ),
    CampoDeTexto(
        tabla="asesores",
        campo="nombre",
        campo_nif="nif",
        papel="asesor",
        clave="asesores",
        referencia=(),
    ),
)


def campos_por_tabla() -> dict[str, tuple[CampoDeTexto, ...]]:
    """Los campos de texto agrupados por tabla.

    Existe para poder comprobar de un vistazo que la lista no tiene dos entradas de la misma tabla y
    el mismo campo (dos enlaces al mismo sitio serían dos verdades), y para que quien lea esto vea
    qué tablas tienen **más de un** nombre escrito (hoy ninguna, y el día que la haya sale aquí).
    """
    agrupados: dict[str, list[CampoDeTexto]] = {}
    for enlace in ENLACES:
        agrupados.setdefault(enlace.tabla, []).append(enlace)
    return {tabla: tuple(campos) for tabla, campos in agrupados.items()}


def el_campo(tabla: str, campo: str) -> CampoDeTexto | None:
    """El campo de texto de esa tabla y esa columna, o `None`.

    **`None` quiere decir «esa puerta no existe»**, y quien llame tiene que contestar 404 en vez de
    inventarse un enlace: por aquí entra un dato del navegador, y un nombre de tabla que no está en
    la lista no puede acabar en una consulta.
    """
    for enlace in ENLACES:
        if enlace.tabla == tabla and enlace.campo == campo:
            return enlace
    return None


# --------------------------------------------------------------------------
# Comparar dos nombres escritos: qué se puede asegurar y qué no
# --------------------------------------------------------------------------


def limpia(texto: str | None) -> str:
    """El texto tal y como lo escribió el agricultor, sin espacios de sobra.

    **Esto NO se usa para guardar su nombre.** Lo que él escribió se queda como está: el nombre que
    enseñamos en la ficha de un contacto lo escribe él, y el texto original no se toca nunca. Esto es
    solo para comparar.
    """
    return " ".join((texto or "").split())


def clave_exacta(texto: str | None) -> str:
    """La forma en que dos textos cuentan como **el mismo nombre escrito igual**.

    Se quitan los espacios de sobra y se pasa a minúsculas, y **nada más**: ni tildes, ni puntos, ni
    abreviaturas. Que una factura traiga «COOPERATIVA AGRÍCOLA DE PEÑARANDA» y un albarán
    «Cooperativa Agrícola de Peñaranda» son la misma empresa escrita de dos maneras, y tratar eso como
    dos personas obligaría al agricultor a juntarlas a mano una por una.

    Lo que **no** se hace aquí es lo que hace `clave_parecida`: quitar tildes. «José Pérez» y «Jose
    Perez» pueden ser la misma persona o dos hermanos, y el ticket pide expresamente que esos dos no
    se junten solos. Acaban en la lista de «se parecen», que se enseña y no se toca.
    """
    return limpia(texto).casefold()


def _sin_tildes(texto: str) -> str:
    """El texto sin acentos y sin nada que no sea letra, número o espacio."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    sin = "".join(letra for letra in descompuesto if not unicodedata.combining(letra))
    limpio = "".join(letra if (letra.isalnum() or letra.isspace()) else " " for letra in sin)
    return " ".join(limpio.split())


def clave_parecida(texto: str | None) -> str:
    """La forma «de parecido»: sin tildes, sin puntos, sin comas y en minúsculas.

    Dos textos que coinciden aquí **se parecen mucho** (uno es el otro con una tilde de menos, o con
    un punto de más), y por eso se enseñan juntos al agricultor. **No se juntan solos**: coincidir
    aquí no es una prueba, es una sospecha, y el ticket prohíbe fusionar por sospecha.
    """
    return _sin_tildes(limpia(texto).casefold())


# A partir de aquí, dos nombres escritos distintos se consideran «parecidos». **El número está medido,
# no elegido a ojo**: se calcularon las siete comparaciones que importan y se puso el umbral justo por
# encima de la más alta de las que NO deben avisar.
#
#   Se avisa (son el mismo nombre escrito de otra manera):
#     · «agrícola peñaranda» / «agricola penaranda»  — lo caza la regla 1 (sin tildes), no el número
#     · «cooperativa x» / «cooperativa x sl»         — lo caza la regla 2 (prefijo por palabras)
#     · «laboratorio agrario» / «laboratorio agragio» → 0,9474
#
#   No se avisa (serían dos personas distintas, y el aviso sería ruido):
#     · «cooperativa x» / «cooperativa z»   → 0,9231  ← el más alto de los que NO deben avisar
#     · «juan» / «juana»                    → 0,8889
#     · «luis» / «luisa»                    → 0,8889
#     · «transportes lopez» / «transportes perez» → 0,8824
#
# Con 0,93 las siete caen del lado que les toca, y el margen es estrecho a propósito: **entre 0,9231 y
# 0,9474 no hay nada que decidir a gusto**. Si alguien baja el número, «Cooperativa X» y
# «Cooperativa Z» empiezan a avisar de que podrían ser la misma; si lo sube, el aviso de una errata
# («Agragio» por «Agrario») deja de salir y el agricultor acaba con dos fichas de la misma empresa sin
# que nadie se lo diga.
UMBRAL_DE_PARECIDO = 0.93


def se_parecen(uno: str | None, otro: str | None) -> bool:
    """¿Estos dos nombres escritos podrían ser la misma persona?

    Tres maneras, y las tres significan «míralo tú», nunca «son el mismo»:

      1. **Iguales quitando tildes, puntos y mayúsculas** («José Pérez» / «Jose Perez»).
      2. **Uno es el principio del otro por palabras** («Cooperativa X» / «Cooperativa X S.L.»),
         que es la forma en que se escribe de más o de menos la razón social.
      3. **Muy parecidos letra a letra** (una errata: «Agragio» por «Agrario»).

    Devuelve `False` cuando los dos textos son ya el mismo nombre exacto: entonces no hay nada que
    avisar, porque se juntan por su cuenta y con razón.
    """
    if clave_exacta(uno) == clave_exacta(otro):
        return False
    primero, segundo = clave_parecida(uno), clave_parecida(otro)
    if not primero or not segundo:
        return False
    if primero == segundo:
        return True
    if primero.startswith(segundo + " ") or segundo.startswith(primero + " "):
        return True
    return difflib.SequenceMatcher(None, primero, segundo).ratio() >= UMBRAL_DE_PARECIDO


def nombres_compatibles(uno: str | None, otro: str | None) -> bool:
    """¿Estos dos nombres son **el mismo escrito de dos maneras**?

    Es la condición que tiene que cumplir el NIF para poder juntar dos textos, y existe por un fallo
    que encontró la revisión independiente: el NIF se usaba como prueba **él solo**, así que un NIF
    tecleado mal (un dígito cambiado, el número de otro proveedor, un CIF repetido) fundía a dos
    personas distintas en una ficha, la marcaba como **segura** y el guion `--migrar` la apuntaba sin
    que el agricultor viera nada. Un NIF no puede llevarse por delante media agenda.

    «Compatibles» quiere decir una de estas dos cosas, y las dos significan que el nombre **no
    contradice** al NIF:

      · **Escritos igual** (mayúsculas aparte): «Cooperativa X» y «COOPERATIVA X».
      · **Que se parezcan** (`se_parecen`): «Cooperativa Agricola de Peñaranda» y «COOPERATIVA
        AGRÍCOLA DE PEÑARANDA S.C.L.» son la misma empresa escrita de dos maneras, y ahí el NIF sí
        confirma lo que el nombre ya decía.

    Lo que **no** es compatible: «Juan García López» y «Pedro López Ruiz» con el mismo NIF. Eso no es
    una prueba de nada: es que uno de los dos papeles está mal escrito, y quien lo sabe es el
    agricultor.
    """
    if clave_exacta(uno) == clave_exacta(otro):
        return True
    return se_parecen(uno, otro)


def _todos_los_nombres_son_compatibles(escritos: list[Escrito]) -> bool:
    """¿**Todos** los nombres de este grupo son compatibles entre sí, dos a dos?

    Dos a dos y no «cada uno con el primero», y esa diferencia importa: con la comprobación floja,
    «Cooperativa X» y «Cooperativa X S.L.» (compatibles con el primero) dejarían entrar a «Transportes
    López» en la misma ficha sin que nadie se diera cuenta. Es la misma trampa que la fusión en cadena:
    un grupo solo es seguro si **ninguna pareja** de sus nombres se contradice.
    """
    for indice, uno in enumerate(escritos):
        for otro in escritos[indice + 1 :]:
            if not nombres_compatibles(uno.texto, otro.texto):
                return False
    return True


def nif_normalizado(texto: str | None) -> str | None:
    """El NIF/CIF en su forma comparable: sin puntos, sin guiones, sin espacios y en mayúsculas.

    Una empresa escribe su CIF de cuatro maneras en cuatro papeles («B-34.123.456», «b34123456»), y
    las cuatro son el mismo número. Como el NIF es **la única prueba** que permite juntar dos textos
    distintos (§ la cabecera), tiene que compararse bien: si aquí se colara un espacio, la prueba no
    se vería y dos fichas de la misma empresa se quedarían separadas.

    Vacío es `None`, nunca `""`: «no lo sé» no es «el NIF vacío».
    """
    limpio = "".join(letra for letra in (texto or "").upper() if letra.isalnum())
    return limpio or None


# --------------------------------------------------------------------------
# La propuesta de la migración
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Escrito:
    """Un nombre escrito a mano, tal y como está hoy en el cuaderno.

    No es una copia guardada: se lee del cuaderno cada vez que se pide la propuesta, y por eso la
    propuesta siempre habla de lo que hay **ahora**. Es la diferencia entre proponer y crear hechos.
    """

    tabla: str
    campo: str
    registro_id: int
    texto: str
    nif: str | None = None
    papel: str = ""
    clave: str = ""
    referencia: tuple[str, ...] = ()
    fecha: str | None = None

    @property
    def clave_exacta(self) -> str:
        return clave_exacta(self.texto)

    @property
    def clave_parecida(self) -> str:
        return clave_parecida(self.texto)

    @property
    def nif_limpio(self) -> str | None:
        return nif_normalizado(self.nif)


@dataclass
class Propuesta:
    """Una ficha de contacto que **se le propone** al agricultor, con los textos que la formarían.

    Lleva `segura` y `motivo` y no un simple «vale/no vale», porque son tres cosas distintas y el
    agricultor tiene que poder leer cuál es la suya:

      · `segura=True` — se puede apuntar sin miedo: o el nombre está escrito igual, o hay un NIF que
        prueba que es el mismo.
      · `segura=False` — **se enseña y no se toca**: «se parecen» o «el mismo nombre con dos NIF».
        El programa no junta nada y le dice por qué.

    Y `pareja` es **cuáles dos nombres** han hecho saltar el aviso de «se parecen». Hace falta decirlo
    porque el grupo de los parecidos enseña **todos** los nombres que están en juego (que es lo que el
    agricultor necesita para decidir), y sin la pareja esa lista se leería como «estos cuatro se
    parecen entre sí», que no es lo mismo ni es verdad.
    """

    nombre: str
    escritos: list[Escrito] = field(default_factory=list)
    segura: bool = False
    motivo: str = ""
    nombres: list[str] = field(default_factory=list)
    nifs: list[str] = field(default_factory=list)
    pareja: tuple[str, str] | None = None

    @property
    def papeles(self) -> list[str]:
        """Los papeles que le tocarían, sin repetir y en el orden del catálogo."""
        suyos = {escrito.papel for escrito in self.escritos if escrito.papel}
        return [papel for papel in PAPELES if papel in suyos]


def _el_nombre_del_grupo(textos: list[str]) -> str:
    """Con qué nombre se propone la ficha, cuando el mismo nombre está escrito de varias maneras.

    Gana el que más veces aparece (el agricultor escribe más veces el bueno), y si hay empate el más
    largo, que es el que no se ha comido nada por el camino. **No se inventa ni se compone**: sale de
    los textos que él escribió.
    """
    cuenta: dict[str, int] = {}
    for texto in textos:
        cuenta[texto] = cuenta.get(texto, 0) + 1
    return sorted(cuenta, key=lambda texto: (-cuenta[texto], -len(texto), texto))[0]


def _propuesta(nombre: str, escritos: list[Escrito], *, segura: bool, motivo: str) -> Propuesta:
    return Propuesta(
        nombre=nombre,
        escritos=sorted(escritos, key=lambda uno: (uno.tabla, uno.campo, uno.registro_id)),
        segura=segura,
        motivo=motivo,
        nombres=sorted({escrito.texto for escrito in escritos}),
        # **Los NIF normalizados, no tal y como están escritos.** De esto depende que `aplicar` pueda
        # copiar el NIF a la ficha: si aquí salieran «B-34.123.456» y «b34123456» como dos valores
        # distintos, la ficha se apuntaría **sin NIF** aunque la prueba esté delante. Se descubrió con
        # la prueba del mismo NIF con dos formas de escribirlo, y era un agujero de verdad.
        nifs=sorted(
            {
                limpio
                for escrito in escritos
                if (limpio := nif_normalizado(escrito.nif))
            }
        ),
    )


def proponer(escritos: list[Escrito]) -> list[Propuesta]:
    """Los contactos que se le proponen al agricultor a partir de los nombres que ya están escritos.

    **No escribe nada y no decide nada**: devuelve la lista para que él la mire. El orden es: primero
    lo que se puede apuntar sin miedo, después lo que hay que mirar, y dentro de cada bloque por
    número de textos (lo que más se repite primero, que es lo que más trabajo ahorra).

    Los cuatro pasos, y por qué en ese orden:

      1. **Se agrupa por el nombre escrito igual** (`clave_exacta`, sin quitar tildes).
      2. **Se mira el NIF dentro de cada grupo.** Un grupo con el mismo nombre y **dos NIF distintos**
         es «dos personas con el mismo nombre»: se aparta y se dice, no se junta. Es el caso que pide
         el contrato en E5.
      3. **Dos grupos distintos con el mismo NIF se juntan solo si además los nombres son
         compatibles** (§ `nombres_compatibles`). El nombre de la ficha es el del grupo con más textos,
         y las otras formas de escribirlo **no se pierden**: se ven en los enlaces, que guardan lo que
         decía cada papel.
      4. **Los grupos que se parecen (y no se pueden juntar) se enseñan juntos**, con los dos nombres
         delante, para que decida el agricultor. Aquí no se toca nada.
    """
    con_nombre = [escrito for escrito in escritos if limpia(escrito.texto)]
    if not con_nombre:
        return []

    # --- 1. Por nombre escrito igual
    grupos: dict[str, list[Escrito]] = {}
    for escrito in con_nombre:
        grupos.setdefault(escrito.clave_exacta, []).append(escrito)

    # --- 2. Y por NIF: la prueba junta lo que el nombre no junta **cuando los nombres acompañan**
    #
    # **Solo participan los grupos que tienen UN solo NIF.** Un grupo con el mismo nombre y dos NIF
    # distintos es «dos personas con el mismo nombre» (el caso de E5), y si se dejara participar en
    # esta unión, un NIF mal tecleado en uno de los dos papeles podría fusionar media agenda. Se
    # aparta antes, que es donde tiene que apartarse.
    def nifs_del_grupo(clave: str) -> set[str]:
        return {
            escrito.nif_limpio for escrito in grupos[clave] if escrito.nif_limpio
        }

    def el_unico_nif(clave: str) -> str | None:
        suyos = nifs_del_grupo(clave)
        return next(iter(suyos)) if len(suyos) == 1 else None

    familia_de: dict[str, list[str]] = {clave: [clave] for clave in grupos}
    con_prueba: dict[str, list[str]] = {}
    for clave in sorted(grupos):
        prueba = el_unico_nif(clave)
        if prueba:
            con_prueba.setdefault(prueba, []).append(clave)
    for _nif, claves in sorted(con_prueba.items()):
        if len(claves) < 2:
            continue
        juntas = sorted(claves)
        for clave in juntas:
            familia_de[clave] = juntas

    # --- 3. Las propuestas
    vistas: set[tuple[str, ...]] = set()
    propuestas: list[Propuesta] = []
    for clave in sorted(grupos):
        familia = tuple(familia_de[clave])
        if familia in vistas:
            continue
        vistas.add(familia)
        suyos = [escrito for una in familia for escrito in grupos[una]]
        nifs = {escrito.nif_limpio for escrito in suyos if escrito.nif_limpio}
        nombre = _el_nombre_del_grupo([escrito.texto for escrito in suyos])
        if len(nifs) > 1:
            # Dos personas con el mismo nombre. **No se junta, y se dice por qué.**
            propuestas.append(
                _propuesta(nombre, suyos, segura=False, motivo="el_mismo_nombre_dos_nif")
            )
        elif len(familia) > 1 and _todos_los_nombres_son_compatibles(suyos):
            # El NIF es una prueba **y los nombres la acompañan**: es la misma empresa escrita de dos
            # maneras, o el mismo nombre con el mismo número.
            propuestas.append(_propuesta(nombre, suyos, segura=True, motivo="mismo_nif"))
        elif len(familia) > 1:
            # **El NIF coincide y los nombres no.** Esto es lo que la revisión independiente cazó, y
            # es lo más peligroso que ha tenido este fichero: un NIF tecleado mal (un dígito, un
            # número de otro proveedor, un CIF repetido) fundía a dos personas distintas en una ficha,
            # la marcaba como **segura**, el guion `--migrar` la apuntaba solo y no salía en ningún
            # aviso. Un NIF no puede llevarse por delante media agenda: se enseña con los dos nombres
            # y el número delante, y **decide el agricultor**.
            propuestas.append(
                _propuesta(nombre, suyos, segura=False, motivo="mismo_nif_nombres_distintos")
            )
        else:
            propuestas.append(_propuesta(nombre, suyos, segura=True, motivo="el_mismo_nombre"))

    # --- 4. Los que se parecen y no se han podido juntar
    seguras = [propuesta for propuesta in propuestas if propuesta.segura]
    for indice, una in enumerate(seguras):
        for otra in seguras[indice + 1 :]:
            if not se_parecen(una.nombre, otra.nombre):
                continue
            propuestas.append(
                Propuesta(
                    nombre=_el_nombre_del_grupo([una.nombre, otra.nombre]),
                    escritos=sorted(
                        una.escritos + otra.escritos,
                        key=lambda escrito: (escrito.tabla, escrito.campo, escrito.registro_id),
                    ),
                    segura=False,
                    motivo="se_parecen",
                    nombres=sorted({*una.nombres, *otra.nombres}),
                    nifs=sorted({*una.nifs, *otra.nifs}),
                    # **Los dos nombres que se parecen, y no los cuatro del grupo.** Es lo que hace que
                    # el aviso se pueda leer sin que parezca que todos se parecen con todos.
                    pareja=tuple(sorted((una.nombre, otra.nombre))),
                )
            )

    propuestas.sort(
        key=lambda propuesta: (not propuesta.segura, -len(propuesta.escritos), propuesta.nombre)
    )
    return propuestas


def resumen_de_la_propuesta(propuestas: list[Propuesta]) -> dict:
    """Los números de la propuesta, contados aquí y no en la pantalla.

    Se devuelven cuatro, y son todos los que el agricultor necesita para decidir: cuántas fichas se le
    proponen, cuántos nombres escritos se enlazarían con ellas, y —**lo que no se puede dejar de
    decir**— a cuántos se les ha avisado de que se parecen a otro y a cuántos no se les ha podido
    juntar porque el mismo nombre lleva dos NIF. Un «0» aquí no es «no hay nada»: es un número de
    verdad, y por eso `fichas` cuenta solo las que se pueden apuntar sin miedo.
    """
    seguras = [propuesta for propuesta in propuestas if propuesta.segura]
    return {
        "fichas": len(seguras),
        "nombres": sum(len(propuesta.escritos) for propuesta in seguras),
        # Lo que hay que mirar a mano, contado aparte porque es lo que el ticket protege. Los tres
        # motivos son distintos y se cuentan por separado: dos nombres que se parecen, el mismo nombre
        # con dos NIF, y el mismo NIF con dos nombres que no se parecen (el que encontró la revisión).
        "se_parecen": sum(1 for propuesta in propuestas if propuesta.motivo == "se_parecen"),
        "homonimos": sum(
            1 for propuesta in propuestas if propuesta.motivo == "el_mismo_nombre_dos_nif"
        ),
        "nif_con_nombres_distintos": sum(
            1
            for propuesta in propuestas
            if propuesta.motivo == "mismo_nif_nombres_distintos"
        ),
    }
