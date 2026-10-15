"""Esquemas de entrada y salida de la API.

Decisión: los campos que el agricultor NO tiene por qué saber (dosis máxima de
etiqueta, plazo de espera, fecha de fin de plazo, abono puro) se aceptan en la
entrada pero son opcionales, y si no vienen se rellenan solos desde el producto o
el abono. El agricultor no debe teclear un dato que ya está en la etiqueta.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from . import dinero, models, textos


# --------------------------------------------------------------------------
# Lo que se acepta tiene que **caber** donde se guarda (revisión del T12, 03/10/2026)
#
# **Por qué existe esto, con el defecto delante.** Los campos de texto que rellenan las pantallas del dinero
# acaban en columnas con tope (`varchar(200)`, `varchar(120)`…), y nadie comprobaba que quepan. **SQLite no
# comprueba la longitud de un `varchar`** —guarda las 250 letras y contesta 201— y **PostgreSQL sí**, así
# que la misma petición funciona en el ordenador del agricultor y **tumba la operación entera** en
# producción (`StringDataRightTruncation`, un 500 y el apunte sin guardar). Es exactamente el defecto que ya
# llegó una vez con `auditoria.accion` en 30 caracteres.
#
# Se arregla en **los esquemas y no en el router** por un motivo: aquí está la puerta de todo lo que entra, y
# una comprobación en el router se puede olvidar en el siguiente endpoint. Y el ancho **se lee del modelo**
# (`models.VentaDeCosecha.comprador` mide lo que mide su columna), no se escribe a mano: si un día se
# ensancha la columna, el tope del esquema se ensancha con ella y nadie tiene que acordarse.
# --------------------------------------------------------------------------


def _cabe_en_la_columna(modelo: type, campo: str) -> int:
    """Cuánto cabe en la columna de ese campo, **leído del modelo**.

    Devolver el número desde la columna y no escribirlo a mano es lo que impide el defecto de arriba: un
    tope escrito dos veces se separa el día que alguien toca una de las dos.
    """
    columna = modelo.__table__.columns.get(campo)
    assert columna is not None, f"{modelo.__tablename__} no tiene la columna {campo}"
    ancho = getattr(columna.type, "length", None)
    assert ancho, f"{modelo.__tablename__}.{campo} no dice cuánto mide"
    return int(ancho)


def _el_que_no_cabe(modelo: type, datos: dict) -> str | None:
    """El primer campo de ese cuerpo cuyo texto no cabe en su columna, o `None`.

    Se mira por **el nombre del campo**, que en estos esquemas es el mismo que el de su columna, y solo los
    que van a una columna de texto con tope. Lo que se compara es el texto **ya recortado**, que es lo que
    de verdad se va a guardar (los esquemas recortan los espacios de los extremos).
    """
    for campo, valor in (datos or {}).items():
        if not isinstance(valor, str):
            continue
        columna = modelo.__table__.columns.get(campo)
        if columna is None:
            continue
        ancho = getattr(columna.type, "length", None)
        if ancho and len(valor.strip()) > ancho:
            return campo
    return None


def _revisa_lo_que_no_cabe(modelo: type):
    """El validador que rechaza, con la frase del agricultor, lo que no cabe en su columna.

    Va en `mode="before"` a propósito: así la frase la da esta comprobación y no el mensaje en inglés de
    Pydantic («String should have at most 200 characters»), que no dice nada a quien lee la pantalla.
    """

    def _el_validador(cls, datos):  # noqa: ANN001 - la firma la pone Pydantic
        if isinstance(datos, dict):
            sobra = _el_que_no_cabe(modelo, datos)
            if sobra:
                raise ValueError(textos.mensaje("D13_algo_es_mas_largo_de_lo_que_cabe", campo=sobra))
        return datos

    return model_validator(mode="before")(classmethod(_el_validador))


def _un_importe_que_cabe(valor, *, es_precio: bool = False):
    """Un importe en `Decimal`, rechazando el `float` **y lo que no puede ser un importe de verdad**.

    Son las dos puertas que la revisión del T12 encontró abiertas en el módulo del dinero:

      · Un `float` (un número de JSON en vez de una cadena) ya perdió céntimos antes de entrar.
      · Un importe de **veintidós cifras enteras** no cabe en la columna donde se guarda: en SQLite entra y
        **en PostgreSQL tumba la operación entera**. El tope no es el ancho de la columna sino lo que puede
        ser una venta de esta finca (ver `dinero.MAXIMO_DE_UN_IMPORTE`), y se dice con una frase.
    """
    numero = dinero.a_decimal(valor)
    if not dinero.cabe_en_el_dinero(numero, es_precio=es_precio):
        raise ValueError(
            textos.mensaje(
                "D12_ese_importe_es_demasiado_grande",
                maximo=dinero.formatea(dinero.MAXIMO_DE_UN_PRECIO if es_precio else dinero.MAXIMO_DE_UN_IMPORTE),
            )
        )
    return numero


# **Un importe que entra, con la regla del dinero de la casa.** Se declara una vez y se usa en todos
# los importes de entrada, en vez de repetir un validador por campo: así el día que se añade un importe
# nuevo, escribir este tipo es lo único que hay que hacer para que herede las dos puertas —«se acepta
# como lo escribe un agricultor» (`dinero.de_texto`: «254,10», «1.234,56») y «un número de coma
# flotante se rechaza»—. Sin esto, el importe de un gasto escrito con coma se rechazaba con un 422 y
# el agricultor veía «No se ha podido» sin saber por qué.
ImporteDeEntrada = Annotated[Decimal, BeforeValidator(_un_importe_que_cabe)]
ImporteDeEntradaOpcional = Annotated[Decimal | None, BeforeValidator(_un_importe_que_cabe)]


class EntradaBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class SalidaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# Explotación y campañas
# --------------------------------------------------------------------------


class ExplotacionEntrada(EntradaBase):
    nombre: str = Field(min_length=1, max_length=200)
    nif: str = Field(min_length=1, max_length=20)
    codigo_siex: str | None = None
    ccaa: str = "Castilla y León"
    provincia: str = ""
    municipio: str = ""
    # **Tres estados** (A13, 05/10/2026): `None` es «no lo sé». Antes nacía en `False`, y ese «no» que nadie
    # había dicho apagaba la comprobación ecológica y salía en el documento que se firma.
    produccion_ecologica: bool | None = None
    # Los datos de la portada del cuaderno de la Junta (hoja 1.1). Ver `models.Explotacion`.
    registro_nacional: str | None = None
    registro_autonomico: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    codigo_postal: str | None = None
    telefono: str | None = None
    correo: str | None = None


class ExplotacionSalida(SalidaBase):
    id: int
    nombre: str
    nif: str
    codigo_siex: str | None
    ccaa: str
    provincia: str
    municipio: str
    produccion_ecologica: bool | None
    registro_nacional: str | None = None
    registro_autonomico: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    codigo_postal: str | None = None
    telefono: str | None = None
    correo: str | None = None


class CampanaEntrada(EntradaBase):
    anio: int = Field(ge=2000, le=2100)
    fecha_inicio: dt.date
    fecha_fin: dt.date


class CampanaCorreccion(CampanaEntrada):
    """Una campaña, para **corregirla**: lo mismo que al crearla, más si está cerrada.

    **Por qué `cerrada` está aquí y no en `CampanaEntrada`.** Al crear un año no se decide nada
    sobre eso —nace abierto—, y por eso el alta no lo pregunta. Pero sí es un dato que cambia
    (cerrar el año cuando se ha terminado, o volver a abrirlo porque se quedó algo sin apuntar) y
    `CampanaSalida` lo devuelve, así que el formulario de corregir lo tiene en la mano: es
    justamente la regla de la casa —lo que se devuelve al leer se puede mandar de vuelta—.

    **Y es obligatorio, no opcional, a propósito:** si se pudiera omitir, corregir solo el año de
    una campaña cerrada la **volvería a abrir sin que nadie lo pidiera**, que es un cambio en el
    cuaderno que el agricultor no ha hecho. Mejor que la petición falle y se diga, que abrir un año
    que estaba cerrado en silencio.
    """

    cerrada: bool


class CampanaSalida(SalidaBase):
    id: int
    anio: int
    fecha_inicio: dt.date
    fecha_fin: dt.date
    cerrada: bool
    # Cuántas cosas del cuaderno hay apuntadas dentro de ese año (ronda 93), o `null` si no se ha contado.
    #
    # POR QUÉ ES OPCIONAL Y NO UN CERO. **Un cero es un dato, y aquí un cero sería mentira**: la lista de
    # campañas lo cuenta (`listar_campanas`, que es donde hace falta, porque es lo que explica por qué un
    # año no se puede quitar), pero `/api/campanas/actual` no lo cuenta y devuelve `null`. Rellenarlo con
    # cero diría que el año que el agricultor está llevando está vacío, y eso no lo sabe nadie sin contar.
    cuantas_cosas: int | None = None
    # **Y de esas cosas, cuáles son apuntes del cuaderno** (30/09/2026). Hizo falta al mirar la pantalla con
    # los datos de verdad: el año decía «Tiene 54 cosas apuntadas dentro» y el cuaderno del mismo año decía
    # «0 apuntes en el cuaderno». Las dos cosas eran verdad —las 54 eran las tierras con su cultivo dicho, que
    # también cuelgan del año— y el agricultor no podía entenderlo. Ahora el año dice **cuántos apuntes tiene**
    # (tratamientos, abonos, labores, cosechas, análisis y ventas, que es lo que él cuenta) y, aparte, lo que
    # hay dentro que no son apuntes: los cultivos dichos (`tierras_con_cultivo`) y el resto (`otras_cosas`).
    #
    # Los tres son `null` cuando no se han contado (la misma razón que `cuantas_cosas`: un cero sería mentira).
    apuntes: int | None = None
    tierras_con_cultivo: int | None = None
    otras_cosas: int | None = None


# --------------------------------------------------------------------------
# Parcelas y grupos
# --------------------------------------------------------------------------


class ParcelaEntrada(EntradaBase):
    alias: str = Field(min_length=1, max_length=120)
    ref_sigpac: str | None = None
    provincia: str = ""
    municipio: str = ""
    codigo_ine: str | None = None
    poligono: int | None = None
    numero_parcela: int | None = None
    numero_recinto: int | None = None
    agregado: int = 0
    zona: int = 0
    referencia_catastral: str | None = None
    # **Opcional, y `None` es «no lo sé», no «cero»** (A7 de `docs/T02_VALORES_POR_DEFECTO.md`).
    # Antes era obligatoria y admitía el 0, así que la única forma de apuntar una tierra traída sin
    # superficie era escribir un cero que después cerraba la puerta a tratarla. Se puede dar de alta
    # la tierra sin la superficie y apuntarla más tarde: el cuaderno tiene que recoger lo que ha
    # pasado, y lo que no se sabe se queda en blanco.
    superficie_ha: float | None = Field(default=None, ge=0)
    superficie_oficial: bool = False
    uso_sigpac: str | None = None
    # secano | regadio | **None = no lo sé** (A10, 05/10/2026). Nacía en `"secano"`, así que **toda tierra
    # nueva quedaba declarada de secano** sin que nadie lo hubiera dicho, y la exportación de la Junta
    # escribía «S» en la casilla del sistema. Ver la nota larga en `models.Parcela.sistema`.
    sistema: str | None = None
    pendiente_pct: float | None = None
    # **Los dos, con tres estados** (A12, 05/10/2026): `None` es «no lo sé», no «aquí no hay agua». De
    # ellos dependen las restricciones de abonado y la franja de seguridad de un tratamiento, así que un
    # `False` que nadie ha dicho aligera las reglas que le aplican al agricultor.
    masa_agua_cerca: bool | None = None
    captacion_consumo_humano: bool | None = None
    zona_vulnerable_nitratos: bool | None = None
    geometria: str | None = None


class ReferenciaSigpacEntrada(EntradaBase):
    """La referencia de un recinto, tal y como la escribe el agricultor.

    Se aceptan guiones, espacios, puntos o barras: cada uno la copia de donde puede (del papel
    del SIGPAC, del visor o de un correo del técnico) y sería absurdo exigirle un formato.
    """

    ref_sigpac: str = Field(min_length=5, max_length=60)


class ParcelaDesdeSigpac(ReferenciaSigpacEntrada):
    """Dar de alta una parcela trayendo los datos del SIGPAC.

    El SIGPAC aporta los datos físicos del recinto, pero no los nombres del municipio y la
    provincia. Estos últimos son opcionales y se comprueban antes de deducir la zona vulnerable.
    """

    alias: str | None = Field(default=None, max_length=120)
    # A10: ver la nota de `ParcelaEntrada.sistema`. El SIGPAC no trae el sistema de explotación.
    sistema: str | None = None
    # No se heredan de la explotación: una parcela puede estar en otro municipio.
    provincia: str | None = None
    municipio: str | None = None
    # La referencia catastral, si el agricultor la tiene en el papel. Si no la manda, la pide el
    # programa al SIGPAC (`refcatparcela`), que es quien manda. El campo faltaba: se podía guardar
    # la del SIGPAC pero no la suya, y hay agricultores que llevan la suya apuntada.
    referencia_catastral: str | None = Field(default=None, max_length=30)


class BuscarRecintosEntrada(EntradaBase):
    """Los datos para **buscar** los trozos de una parcela en el SIGPAC.

    Se puede mandar de dos maneras, y las dos son las que tiene el agricultor delante:

    1. **`referencia`**: lo que haya copiado. Vale la del visor del SIGPAC (`37:70:0:0:503:51`),
       los siete números del papel y la referencia catastral del Catastro.
    2. **Los campos sueltos**: el municipio y la provincia **elegidos de la lista** y el polígono
       y la parcela. Es lo que hacen las aplicaciones oficiales del FEGA para «Añadir recintos de
       SigPac», con las seis casillas: provincia, municipio, agregado, zona, polígono y parcela.

    Se admite lo uno o lo otro porque el agricultor puede tener el papel delante o no, y
    obligarle a un camino cuando tiene el otro en la mano es la forma de que no lo haga.
    """

    referencia: str | None = Field(default=None, max_length=60)
    provincia: str | None = Field(default=None, max_length=60)
    municipio: str | None = Field(default=None, max_length=120)
    poligono: int | None = Field(default=None, ge=0)
    parcela: int | None = Field(default=None, ge=0)
    agregado: int | None = Field(default=None, ge=0)
    zona: int | None = Field(default=None, ge=0)


class VariasParcelasDesdeSigpac(EntradaBase):
    """Traer de una vez los trozos que el agricultor ha marcado.

    Es lo que ahorra el trabajo de verdad: cuarenta parcelas son cuarenta referencias, y
    apuntarlas una a una es el momento en el que se abandona. Se admite **una lista de
    referencias** (una por línea, pegadas de donde sea) y se dan de alta todas, diciendo cuáles
    han ido bien y cuáles no y por qué.
    """

    referencias: list[str] = Field(min_length=1, max_length=200)
    # A10: ver la nota de `ParcelaEntrada.sistema`. Pegar cuarenta referencias no dice de qué sistema
    # son: el programa no lo adivina, lo pregunta.
    sistema: str | None = None
    alias: str | None = Field(default=None, max_length=120)
    provincia: str | None = Field(default=None, max_length=60)
    municipio: str | None = Field(default=None, max_length=120)
    # Si los trozos vienen de la misma parcela catastral, su referencia catastral es la misma y
    # se guarda en todos: es un dato que el agricultor ya ha pegado y no tiene por qué repetir.
    referencia_catastral: str | None = Field(default=None, max_length=30)


class ParcelaSalida(SalidaBase):
    id: int
    alias: str
    ref_sigpac: str | None
    provincia: str
    municipio: str
    # El código oficial del municipio (el del INE). Sale en la respuesta porque es con el que se
    # comprueba la zona vulnerable y con el que se identifica el pueblo delante de la Junta: si no
    # se viera, no se podría saber que la parcela está bien situada.
    codigo_ine: str | None = None
    superficie_ha: float | None
    superficie_oficial: bool
    # La superficie del recinto entero según el SIGPAC, cuando se sabe. Ver
    # `models.Parcela.superficie_sigpac_ha`: sirve para rellenar la hoja 2.1 del cuaderno de la
    # Junta, que pide las dos superficies por separado.
    superficie_sigpac_ha: float | None = None
    # A10: puede ser `None` porque no se sabe, y entonces no se puede escribir «S» ni «R» en el cuaderno.
    sistema: str | None
    masa_agua_cerca: bool | None
    captacion_consumo_humano: bool | None
    zona_vulnerable_nitratos: bool | None
    pendiente_pct: float | None
    uso_sigpac: str | None
    # Las tres partes de la referencia del SIGPAC, cada una por su número. El agricultor las tiene
    # en el papel de su parcela, así que verlas separadas es lo que le permite comprobar que la
    # que ha traído el programa es la suya.
    poligono: int | None = None
    numero_parcela: int | None = None
    numero_recinto: int | None = None
    # Las dos partes de la referencia que faltaban (agregado y zona) y la referencia catastral.
    # Salen en la respuesta para que la pantalla pueda enseñar la referencia **entera**, tal y como
    # la escribe el SIGPAC, y para que se pueda comprobar contra el papel del agricultor.
    agregado: int = 0
    zona: int = 0
    referencia_catastral: str | None = None
    # El centro del trozo, en `[longitud, latitud]`. Lo usa el mapa para abrirse en la tierra del
    # agricultor en vez de en un sitio cualquiera, y para poder centrar la vista en una parcela.
    centro: list[float] | None = None
    # La forma del trozo, lista para pintar en un `<path>` de SVG. Se calcula (ver
    # `models.Parcela.dibujo`) y **no** se manda el WKT: la línea que se pinta son unos cientos de
    # caracteres y el WKT es un texto largo que al móvil no le hace falta.
    dibujo: str | None = None


class CultivoEntrada(EntradaBase):
    """El cultivo que hay en una parcela durante una campaña.

    Tiene esquema propio y no un `dict` suelto porque las fechas tienen que llegar
    como fechas. Con un diccionario crudo llegaban como texto y la base de datos
    rechazaba el apunte al guardarlo.
    """

    campana_id: int
    especie: str = Field(min_length=1, max_length=120)
    variedad: str | None = None
    # A10: ver la nota de `ParcelaEntrada.sistema`. Un cultivo de campaña nace sin sistema declarado.
    sistema: str | None = None
    fecha_inicio: dt.date | None = None
    fecha_fin: dt.date | None = None
    # El ecorregimen (hoja 2.1 del cuaderno de la Junta) y la superficie cultivada de esa línea,
    # que no es la del recinto entero. Los dos se pueden dejar vacíos.
    ecorregimen: str | None = None
    superficie_cultivada_ha: float | None = Field(default=None, ge=0)


class GrupoEntrada(EntradaBase):
    nombre: str = Field(min_length=1, max_length=120)
    campana_id: int | None = None
    cultivo: str | None = None
    # A10: ver la nota de `ParcelaEntrada.sistema`. Un grupo de tierras no es de secano por nacer.
    sistema: str | None = None
    parcela_ids: list[int] = Field(default_factory=list)


class GrupoSalida(SalidaBase):
    id: int
    nombre: str
    campana_id: int | None
    cultivo: str | None
    # A10: `None` es «no lo sé»; el grupo puede existir sin que se haya dicho el sistema.
    sistema: str | None
    creado_automaticamente: bool
    parcela_ids: list[int] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Maestros
# --------------------------------------------------------------------------


class ProductoEntrada(EntradaBase):
    nombre_comercial: str = Field(min_length=1, max_length=200)
    tipo_producto: str | None = None
    numero_registro: str | None = None
    materia_activa: str | None = None
    dosis_maxima: float | None = Field(default=None, gt=0)
    unidad_dosis: str = "L/ha"
    plazo_seguridad_dias: int | None = Field(default=None, ge=0)
    lote: str | None = None
    fecha_caducidad: dt.date | None = None
    cantidad_comprada: float | None = Field(default=None, ge=0)
    unidad_compra: str = "L"
    fecha_compra: dt.date | None = None
    proveedor: str | None = None
    # La autorización del producto: **tres estados**. `None` es «no comprobado», y no puede ser el
    # defecto `True` que había: eso daba por autorizado y por permitido en ecológico un producto
    # del que nadie había dicho nada. Ver `models.ProductoFitosanitario.autorizado`.
    autorizado: bool | None = None
    permitido_ecologico: bool | None = None
    autorizacion_excepcional: str | None = None
    autorizacion_hasta: dt.date | None = None
    foto_etiqueta: str | None = None


class ProductoSalida(SalidaBase):
    id: int
    nombre_comercial: str
    tipo_producto: str | None = None
    numero_registro: str | None
    materia_activa: str | None
    dosis_maxima: float | None
    unidad_dosis: str
    plazo_seguridad_dias: int | None
    lote: str | None
    fecha_caducidad: dt.date | None
    autorizado: bool | None
    permitido_ecologico: bool | None
    # La compra. Faltaban aquí desde el principio: la tabla los tenía y la entrada los aceptaba,
    # pero **la salida no los devolvía**, así que ninguna pantalla podía enseñarlos. Es el mismo
    # tipo de fallo que un campo que se guarda y no se lee: parece que está y no está.
    cantidad_comprada: float | None = None
    unidad_compra: str = "L"
    fecha_compra: dt.date | None = None
    proveedor: str | None = None
    # La autorización del producto. Faltaban en la salida, y sin ellas no había forma de
    # rellenarlas desde ninguna pantalla: los valores se quedaban en su defecto (autorizado y
    # permitido en ecológico) y **las tres comprobaciones que dependen de esto no podían saltar
    # nunca**. Ver `docs/LO_QUE_PIDE_LA_JUNTA.md`, ronda 19.
    autorizacion_excepcional: str | None = None
    autorizacion_hasta: dt.date | None = None
    foto_etiqueta: str | None = None


class FertilizanteEntrada(EntradaBase):
    nombre: str = Field(min_length=1, max_length=200)
    tipo: str = "mineral"
    # **Tres estados también aquí** (A6 de `docs/T02_VALORES_POR_DEFECTO.md`). El defecto era
    # `0.0`, y con eso la ficha de un abono del que nadie había dicho la composición nacía diciendo
    # «0 % de nitrógeno, 0 % de fósforo y 0 % de potasio», que es una afirmación y no un hueco. El
    # abono también se crea desde una factura, y la factura **no trae la composición**: eso es
    # exactamente «no lo sé», y tiene que poder guardarse así en vez de inventarse tres ceros.
    riqueza_n: float | None = Field(default=None, ge=0, le=100)
    riqueza_p: float | None = Field(default=None, ge=0, le=100)
    riqueza_k: float | None = Field(default=None, ge=0, le=100)


class FertilizanteSalida(SalidaBase):
    id: int
    nombre: str
    tipo: str
    # `None` es «no consta la composición», y ninguna pantalla puede enseñarlo como un cero.
    riqueza_n: float | None
    riqueza_p: float | None
    riqueza_k: float | None


class AplicadorEntrada(EntradaBase):
    nombre: str = Field(min_length=1, max_length=200)
    nif: str | None = None
    es_empresa: bool = False
    numero_ropo: str | None = None
    numero_carne: str | None = None
    tipo_carne: str | None = None
    fecha_caducidad_carne: dt.date | None = None
    numero_reganip: str | None = None


class AplicadorSalida(SalidaBase):
    id: int
    nombre: str
    es_empresa: bool
    numero_ropo: str | None
    numero_carne: str | None
    fecha_caducidad_carne: dt.date | None
    # El tipo de carné (básico, cualificado) y el número del registro de equipos de aplicación
    # aérea. Estaban en la tabla y no salían en la respuesta, así que tampoco se podían pedir.
    tipo_carne: str | None = None
    numero_reganip: str | None = None


class AsesorEntrada(EntradaBase):
    nombre: str = Field(min_length=1, max_length=200)
    nif: str | None = None
    es_empresa: bool = False
    numero_ropo: str | None = None
    ambito: str | None = None
    entidad_certificacion: str | None = None
    telefono: str | None = None
    correo: str | None = None


class AsesorSalida(SalidaBase):
    id: int
    nombre: str
    es_empresa: bool
    numero_ropo: str | None
    ambito: str | None
    entidad_certificacion: str | None
    telefono: str | None
    correo: str | None


class EquipoEntrada(EntradaBase):
    nombre: str = Field(min_length=1, max_length=120)
    tipo: str | None = None
    # Las tres pestañas de la app oficial: propia, ajena y equipos que no van en el ROMA. Y el tipo,
    # la marca y el modelo, que es lo que pide la nota al pie de la hoja 1.3 del cuaderno.
    # **A11 (05/10/2026)**: nacía en `"propia"`, así que la máquina de otro quedaba como tuya y con
    # ITEAF, en la lista equivocada. `None` es «no consta de quién es» y el programa lo pregunta.
    titularidad: str | None = None
    marca: str | None = None
    modelo: str | None = None
    numero_roma: str | None = None
    numero_serie: str | None = None
    fecha_adquisicion: dt.date | None = None
    fecha_iteaf: dt.date | None = None
    fecha_proxima_iteaf: dt.date | None = None


class EquipoSalida(SalidaBase):
    id: int
    nombre: str
    tipo: str | None = None
    # A11: `None` es «no consta»; la ficha no se inventa de quién es la máquina.
    titularidad: str | None = None
    marca: str | None = None
    modelo: str | None = None
    numero_roma: str | None
    fecha_adquisicion: dt.date | None = None
    fecha_iteaf: dt.date | None
    fecha_proxima_iteaf: dt.date | None


class InstalacionEntrada(EntradaBase):
    alias: str = Field(min_length=1, max_length=120)
    tipo: str = "almacen"
    referencia_catastral: str | None = None
    municipio: str = ""
    uso: str | None = None
    superficie_m2: float | None = Field(default=None, ge=0)
    observaciones: str | None = None


class InstalacionSalida(SalidaBase):
    id: int
    alias: str
    tipo: str
    referencia_catastral: str | None
    municipio: str
    uso: str | None
    superficie_m2: float | None


# --------------------------------------------------------------------------
# La maquinaria de la finca (T14, E8, 03/10/2026)
#
# **Lo que estos esquemas NO hacen, y es lo que el ticket pide**: no aceptan ninguna fecha calculada
# ni ninguna obligación deducida. `proxima_fecha` de una inspección se guarda **tal cual la manda el
# agricultor**, que es lo que ponía el papel; la aplicabilidad de cada obligación se declara una por
# una y nace en «no lo sé». Ver `app/maquinaria.py`, que es donde está el porqué escrito entero.
# --------------------------------------------------------------------------


class MaquinaEntrada(EntradaBase):
    """Una máquina de la finca, tal y como la apunta el agricultor.

    **`clase`, `propiedad` y `disponibilidad` son obligatorias y no tienen valor por defecto.** Es
    una decisión, no un descuido: son las tres donde un valor de partida sería una afirmación que
    nadie ha hecho («es tuya», «está disponible») y donde el contrato avisa de los defectos
    permisivos. La pantalla las pregunta con sus botones, y una de las respuestas posibles es «no lo
    sé», que se guarda como tal.

    `clasificacion_tecnica` es lo que dice el papel sobre la clasificación de la máquina, y puede
    venir vacío: vacío es «no se sabe», y entonces la ficha lo pide en vez de suponerlo.

    **El nombre no lleva aquí su `min_length`, y es a propósito**: con un hueco de un espacio, la
    respuesta de Pydantic era un aviso en inglés («String should have at least 1 character») y el
    agricultor no sabía qué le pedían. Sin `min_length`, el nombre llega al router y quien contesta es
    `_el_nombre_hace_falta`, con la frase que dice **qué hacer** (`M11_esa_maquina_necesita_nombre`).
    """

    nombre: str = Field(default="", max_length=120)
    # **Estas tres no traen valor por defecto, y siguen sin traerlo: lo que cambia es DÓNDE se exigen.**
    # Son las tres donde un valor de partida sería una afirmación que nadie ha hecho («es tuya», «está
    # disponible»), así que al **dar de alta** una máquina el router las exige con su frase (M12/M13).
    # Pero al **corregir** una máquina, no mandarlas no es decir que no haya respuesta: es no hablar de
    # eso, y la respuesta que había se conserva (`_preparar_maquina_guardable`). Aquí no se pueden exigir
    # porque este mismo esquema sirve para las dos cosas —y corregir solo la matrícula desde la API
    # contestaba 422, cosa que midió la revisión independiente del T14 el 05/10/2026—.
    clase: str | None = None
    clasificacion_tecnica: str | None = Field(default=None, max_length=200)
    matricula: str | None = Field(default=None, max_length=30)
    numero_serie: str | None = Field(default=None, max_length=80)
    numero_roma: str | None = Field(default=None, max_length=60)
    marca: str | None = Field(default=None, max_length=80)
    modelo: str | None = Field(default=None, max_length=80)
    anio: int | None = Field(default=None, ge=1900, le=2100)
    propiedad: str | None = None
    horas: float | None = Field(default=None, ge=0)
    disponibilidad: str | None = None
    # **Es la misma máquina que el equipo de aplicación del cuaderno** (hoja 1.3), cuando lo es. Sirve
    # para no escribir el pulverizador dos veces, no para rellenar nada solo.
    equipo_aplicacion_id: int | None = None
    notas: str | None = None
    # El identificador de la petición (caso A12 del contrato), para que dos toques del mismo botón —o un
    # reintento del móvil— no den de alta dos veces la misma máquina. Lo manda la pantalla al abrir el
    # formulario, como en una inspección.
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Maquina, "clave_de_reenvio")
    )

    _revisa_lo_que_no_cabe = _revisa_lo_que_no_cabe(models.Maquina)


class MaquinaSalida(SalidaBase):
    id: int
    nombre: str
    clase: str
    clasificacion_tecnica: str | None
    matricula: str | None
    numero_serie: str | None
    numero_roma: str | None
    marca: str | None
    modelo: str | None
    anio: int | None
    propiedad: str
    horas: float | None
    disponibilidad: str
    equipo_aplicacion_id: int | None
    notas: str | None


class ObligacionEntrada(EntradaBase):
    """Lo que el agricultor declara de una obligación: si le toca, y de dónde sale eso.

    `aplicabilidad` nace en `no_se` **también aquí**, aunque el formulario mande siempre un valor: si
    alguien llama a la API sin decirlo, lo que queda guardado es «no se sabe», nunca «no le toca».
    """

    aplicabilidad: str = "no_se"
    origen: str = "no_se"
    # **El papel que demuestra la aplicabilidad, y de cuándo es** (CRM-07, 14/10/2026). El contrato
    # pide «aplicabilidad con **evidencia y fecha**»: `origen` decía que aquello salía de un documento
    # y **no decía cuál**. Los dos pueden quedar vacíos, y eso es un caso normal —el agricultor lo
    # sabe y no trae el papel—.
    documento_id: int | None = None
    # Y **no es `creado_en`**: esa es cuándo se apuntó esto; esta, de cuándo es el papel.
    fecha_de_la_evidencia: dt.date | None = None
    # **Cuándo se decidió** (CRM-07 #6, 14/10/2026). Lo manda el cliente porque **solo él sabe cuándo
    # lo decidió**; **quién** lo decidió no viene por aquí, y es a propósito: eso lo pone el servidor,
    # que es el único que sabe qué cuenta está usando el programa (ver `declarar_una_obligacion`).
    # Preguntárselo al navegador sería dejar que el agricultor dijera que decidió otro. Y no es
    # `creado_en`: esa es cuándo se apuntó, que puede ser mucho después del día en que se decidió.
    decidido_en: dt.date | None = None
    notas: str | None = None


class ObligacionSalida(SalidaBase):
    id: int
    tipo: str
    aplicabilidad: str
    origen: str
    documento_id: int | None
    fecha_de_la_evidencia: dt.date | None
    # **Quién lo decidió y el día que lo dijo** (CRM-07 #6, 14/10/2026). Aquí se devuelve el
    # **nombre**, no el identificador: la fila guarda `decidido_por_usuario_id` y el nombre se
    # resuelve al leerlo, que es la convención de la casa —la bandeja hace lo mismo con
    # `confirmado_por_usuario_id`, que se enseña como `Usuario.nombre`—. Y no se confunde con
    # `fecha_de_la_evidencia`, que es de cuándo es el papel: esta es de cuándo se decidió.
    decidido_por: str | None = None
    decidido_en: dt.date | None = None
    # Se dice **en el dato**, no solo en la pantalla: una obligación sin papel lo dice al leerla, para
    # que ninguna pantalla pueda callarlo por olvido. Es el mismo trato que la inspección.
    trae_papel: bool = False
    notas: str | None

    @model_validator(mode="after")
    def _dice_si_trae_papel(self):
        self.trae_papel = self.documento_id is not None
        return self


class InspeccionEntrada(EntradaBase):
    """Una inspección, un mantenimiento o una renovación: un hecho con su fecha.

    `proxima_fecha` es **la del papel**, copiada: el esquema no la calcula ni la rellena desde la
    fecha de la inspección. `resultado` nace en `no_consta`, que no es «favorable».
    """

    tipo: str
    fecha: dt.date
    resultado: str = "no_consta"
    proxima_fecha: dt.date | None = None
    documento_id: int | None = None
    notas: str | None = None
    # El identificador de la petición, para que el móvil pueda reintentar sin apuntar dos veces la
    # misma inspección cuando vuelve la cobertura (el caso A12 del contrato).
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InspeccionDeMaquina, "clave_de_reenvio")
    )

    _revisa_lo_que_no_cabe = _revisa_lo_que_no_cabe(models.InspeccionDeMaquina)


class InspeccionSalida(SalidaBase):
    id: int
    tipo: str
    fecha: dt.date
    resultado: str
    proxima_fecha: dt.date | None
    documento_id: int | None
    # Se dice **en el dato**, no solo en la pantalla: una inspección sin papel lo dice al leerla, para
    # que ninguna pantalla pueda callarlo por olvido.
    trae_papel: bool = False
    notas: str | None
    anulado: bool
    motivo_anulacion: str | None
    clave_de_reenvio: str | None = None

    @model_validator(mode="after")
    def _dice_si_trae_papel(self):
        self.trae_papel = self.documento_id is not None
        return self


class AveriaEntrada(EntradaBase):
    """Una avería: qué pasó, cuándo, y si ya está arreglada.

    **`resuelta` es obligatoria y admite tres respuestas** (`True`, `False` y `null` = «no lo sé»).
    No nace en ningún valor: dar por arreglada una máquina que no lo está, o al revés, es
    exactamente lo que este ticket no puede hacer.
    """

    fecha: dt.date
    que_paso: str = Field(min_length=1)
    resuelta: bool | None
    fecha_resuelta: dt.date | None = None
    horas: float | None = Field(default=None, ge=0)
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.AveriaDeMaquina, "clave_de_reenvio")
    )


class AveriaSalida(SalidaBase):
    id: int
    fecha: dt.date
    que_paso: str
    resuelta: bool | None
    fecha_resuelta: dt.date | None
    horas: float | None
    notas: str | None
    anulado: bool
    motivo_anulacion: str | None


class FuenteDeLaObligacionSalida(BaseModel):
    """De dónde sale una obligación: la norma que tenemos localizada, y lo que falta.

    Va en la respuesta y no solo en un comentario del código, por lo mismo que `iuws.QUE_FALTA`: el
    agricultor tiene que poder ver **por qué** el programa no le calcula una fecha, y quien herede
    esto tiene que saber qué falta sin leer el módulo entero.
    """

    norma: str | None = None
    url: str | None = None
    que_falta: str = ""


class EstadoDeUnaObligacionSalida(BaseModel):
    """La obligación con todo lo que enseña la ficha, ya decidido por `app/maquinaria.py`."""

    tipo: str
    aplicabilidad: str
    origen_de_la_aplicabilidad: str
    notas: str | None = None
    # El código del estado: las palabras las pone `textos.py` en la pantalla.
    situacion: str
    ultima_inspeccion: InspeccionSalida | None = None
    resultado: str
    # Tal cual venía del papel. Nunca una fecha sumada por el programa.
    proxima_fecha: dt.date | None = None
    dias: int | None = None
    # **El papel de la última INSPECCIÓN** («cómo salió»). Ojo: **no** es el de la aplicabilidad.
    documento_id: int | None = None
    trae_papel: bool = False
    # **Y el papel que demuestra QUE LE TOCA, con su fecha** (CRM-07, 14/10/2026). Van separados a
    # propósito: comparten el nombre de columna en la base pero **no son el mismo papel** —uno dice por
    # qué se sabe que la obligación le toca y el otro cómo salió la última—, y si se llamaran igual la
    # ficha enseñaría uno creyendo que es el otro. **Los dos son creíbles, y por eso hay que separarlos.**
    #
    # Y este esquema importa: es **el que lee la pantalla** (`GET /api/maquinaria/{id}` →
    # `_la_ficha`). Un campo que no esté aquí **no llega**, aunque la tabla y la puerta lo tengan: es
    # el mismo mal que el rótulo que faltaba en `SEMILLAS`, pero al revés —el dato existe, la pantalla
    # no lo ve, y **nadie se entera porque no da error**—.
    documento_de_la_aplicabilidad_id: int | None = None
    la_aplicabilidad_trae_papel: bool = False
    fecha_de_la_evidencia: dt.date | None = None
    # **Y quién lo decidió y cuándo, que es lo que lee la ficha** (CRM-07 #6, 14/10/2026). Van en
    # **este** esquema y no solo en `ObligacionSalida`, y ese es justo el detalle que se aprendió a
    # golpes en este mismo ticket: el que la pantalla lee es este (`GET /api/maquinaria/{id}` →
    # `_la_ficha`), así que un campo que falte aquí **no llega a la ficha** aunque la tabla y la
    # puerta lo tengan. El **nombre** lo resuelve el router: `app/maquinaria.py` es puro y no tiene
    # base de datos, así que de allí sale el identificador y de aquí, el nombre.
    decidido_por: str | None = None
    decidido_en: dt.date | None = None
    fuente: FuenteDeLaObligacionSalida


class ProximaRevisionSalida(BaseModel):
    fecha: dt.date | None = None
    tipo: str | None = None
    # La situación de la obligación que da esa fecha (`vencida`, `proxima`, `vigente`…). Va en el dato
    # para que la pantalla ponga su palabra sin volver a decidir el margen por su cuenta.
    situacion: str | None = None
    sin_fecha: int = 0
    vencidas: int = 0
    no_favorables: int = 0


class DocumentacionDeLaMaquinaSalida(BaseModel):
    inspecciones: int = 0
    con_papel: int = 0
    sin_papel: int = 0


class ResumenDeLaMaquinaSalida(BaseModel):
    proxima_revision: ProximaRevisionSalida
    documentacion: DocumentacionDeLaMaquinaSalida
    avisos: int = 0
    avisos_urgentes: int = 0
    disponibilidad: str


class AvisoDeMaquinaSalida(BaseModel):
    """Un aviso de una máquina: su código, su frase ya escrita y si es urgente.

    Reutiliza el texto del servidor (`textos.mensaje`) y no lo escribe la pantalla, que es la regla
    de la casa. `urgente` es lo que decide si sale arriba y con qué palabra, porque aquí el color
    solo no puede informar.
    """

    codigo: str
    mensaje: str
    tipo: str
    urgente: bool = False


class MaquinaEnLaTablaSalida(MaquinaSalida):
    """Una fila de la tabla de maquinaria: la máquina y lo que la tabla necesita de ella."""

    resumen: ResumenDeLaMaquinaSalida


class EquipoSinFichaSalida(BaseModel):
    """Un equipo de aplicación del cuaderno que todavía no está en la lista de maquinaria.

    **Por qué se enseña esto.** `EquipoAplicacion` no cubre toda la maquinaria (contrato §9), así que
    la lista de maquinaria es otra cosa; pero los equipos que ya estaban apuntados en el cuaderno
    **no pueden desaparecer** de la vista. Se enseñan aparte, diciendo qué son y con el botón para
    traerlos a la lista: así se completa lo que faltaba sin duplicar lo que ya había.
    """

    id: int
    nombre: str
    tipo: str | None = None
    # A11: `None` es «no consta». La lista de máquinas enseña esta casilla, así que no puede mentir.
    titularidad: str | None = None
    numero_roma: str | None = None
    fecha_proxima_iteaf: dt.date | None = None


class TablaDeLaMaquinariaSalida(BaseModel):
    """La tabla entera: las filas, los totales del conjunto y lo que falta por decir.

    `total` y `con_avisos` son **del conjunto entero**, no de la página que se ve: el contrato pide
    que las sumas no se calculen sobre lo que está a la vista.
    """

    maquinas: list[MaquinaEnLaTablaSalida]
    total: int
    con_avisos: int
    con_avisos_urgentes: int
    # Los equipos del cuaderno que no están en esta lista: ver `EquipoSinFichaSalida`.
    equipos_sin_ficha: list[EquipoSinFichaSalida] = []
    que_falta: list[dict] = []


class FichaDeUnaMaquinaSalida(BaseModel):
    """La ficha: la máquina, sus cinco obligaciones, sus inspecciones, sus averías y sus avisos."""

    maquina: MaquinaSalida
    obligaciones: list[EstadoDeUnaObligacionSalida]
    inspecciones: list[InspeccionSalida]
    averias: list[AveriaSalida]
    avisos: list[AvisoDeMaquinaSalida]
    resumen: ResumenDeLaMaquinaSalida
    que_falta: list[dict] = []
    fuente_de_las_obligaciones: dict[str, FuenteDeLaObligacionSalida] = {}


# --------------------------------------------------------------------------
# Registro obligatorio 1: tratamiento
# --------------------------------------------------------------------------


class TratamientoEntrada(EntradaBase):
    campana_id: int
    fecha: dt.date
    hora_inicio: str | None = None
    hora_fin: str | None = None

    # De qué clase es la aplicación. Por defecto, en la tierra, que es lo normal.
    tipo: str = "parcela"
    parcela_id: int | None = None
    grupo_id: int | None = None
    # Para tratamientos de instalaciones y postcosecha.
    instalacion_id: int | None = None
    producto_cosechado: str | None = None
    lote_cosecha: str | None = None

    superficie_tratada_ha: float | None = Field(default=None, gt=0)
    cultivo: str | None = None
    variedad: str | None = None
    plaga: str | None = None
    justificacion: str | None = None
    estado_cultivo: str | None = None
    producto_id: int | None = None
    lote_producto: str | None = None
    dosis: float | None = Field(default=None, gt=0)
    unidad_dosis: str = "L/ha"
    volumen_caldo_l_ha: float | None = Field(default=None, gt=0)
    unidad_cantidad_aplicada: str | None = None
    aplicador_id: int | None = None
    equipo_id: int | None = None
    # El asesoramiento del tratamiento. Opcional: no todos los tratamientos se consultan.
    asesor_id: int | None = None
    asesor_fecha: dt.date | None = None
    asesoramiento_validado: bool | None = None
    asesoramiento_contrato: bool | None = None
    temperatura_c: float | None = None
    humedad_pct: float | None = None
    viento_kmh: float | None = None
    viento_direccion: str | None = None
    franja_seguridad_respetada: bool | None = None
    # Estas dos se preguntan porque el interfaz de la Junta las pide: `AplicacionManual` es
    # obligatoria y `Eficacia` también. Vacío es «no lo sé», nunca «no».
    aplicado_a_mano: bool | None = None
    eficacia: str | None = None
    plazo_reentrada_dias: int | None = Field(default=None, ge=0)
    operadores_expuestos: int | None = Field(default=None, ge=0)
    medidas: list[str] = Field(default_factory=list)
    incidencias: str | None = None
    observaciones: str | None = None


class TratamientoSalida(SalidaBase):
    id: int
    campana_id: int
    fecha: dt.date
    tipo: str
    parcela_id: int | None
    grupo_id: int | None
    instalacion_id: int | None
    producto_cosechado: str | None
    lote_cosecha: str | None
    # Opcional: una nave no se mide en hectáreas. Se exige solo cuando la aplicación va
    # sobre la tierra, y eso lo comprueba `validaciones.py`.
    superficie_tratada_ha: float | None
    cultivo: str | None
    plaga: str | None
    justificacion: str | None
    # Estas tres se devuelven para que el agricultor pueda **repetir** este tratamiento: el atajo
    # «lo mismo que la última vez» necesita el producto, el aplicador y la máquina, y antes solo
    # los tenía el móvil donde se apuntó. Son datos suyos y no hay nada que esconder: sin ellos,
    # en un móvil nuevo el atajo no se podía ofrecer y la pantalla decía, encima, que no había
    # apuntado nada. Ver `ultimoDeLaFinca` en `web/nucleo.js`.
    producto_id: int | None = None
    aplicador_id: int | None = None
    equipo_id: int | None = None
    producto_nombre: str | None
    numero_registro: str | None
    materia_activa: str | None
    dosis: float | None
    unidad_dosis: str
    cantidad_total: float | None
    unidad_cantidad_aplicada: str | None = None
    plazo_seguridad_dias: int | None
    fecha_fin_plazo_seguridad: dt.date | None
    plazo_reentrada_dias: int | None
    # Tres estados: `True`, `False` y `None` («no se ha podido comprobar»). Ver el porqué en
    # `models.TratamientoFitosanitario.en_zona_vulnerable`. La pantalla tiene que poder
    # distinguirlos, así que aquí no puede ser un `bool` a secas.
    en_zona_vulnerable: bool | None
    anulado: bool
    medidas: list[str] = Field(default_factory=list)
    asesor_id: int | None = None
    asesor_fecha: dt.date | None = None
    asesoramiento_validado: bool | None = None
    asesoramiento_contrato: bool | None = None
    # --- Cómo se echó: las condiciones de la aplicación ---
    #
    # Estos campos estaban en la tabla desde el principio y **no salían en ninguna respuesta**,
    # así que ninguna pantalla podía enseñarlos: se guardaban y ahí se quedaban. Dos de ellos los
    # pide el contenido mínimo del CUE por su número (la hora, campo 3, y el estado de la planta,
    # campo 8), y el volcado declaraba la hora como un campo suyo que nunca se podía rellenar.
    hora_inicio: str | None = None
    hora_fin: str | None = None
    estado_cultivo: str | None = None
    volumen_caldo_l_ha: float | None = None
    franja_seguridad_respetada: bool | None = None
    # Estas dos se preguntan porque el interfaz de la Junta las pide: `AplicacionManual` es
    # obligatoria y `Eficacia` también. Vacío es «no lo sé», nunca «no».
    aplicado_a_mano: bool | None = None
    eficacia: str | None = None
    temperatura_c: float | None = None
    humedad_pct: float | None = None
    viento_kmh: float | None = None
    viento_direccion: str | None = None
    operadores_expuestos: int | None = None
    incidencias: str | None = None
    observaciones: str | None = None


# --------------------------------------------------------------------------
# Registro obligatorio 2: fertilización
# --------------------------------------------------------------------------


class FertilizacionEntrada(EntradaBase):
    campana_id: int
    fecha: dt.date
    parcela_id: int | None = None
    grupo_id: int | None = None
    superficie_ha: float = Field(gt=0)
    fertilizante_id: int | None = None
    # **Los kilos que se echaron** (CRM-07, 14/10/2026): es lo que el agricultor tiene delante
    # —los sacos— y lo que el contrato llama «600 kg en 3 ha». Si vienen, **el kg/ha se deduce**
    # y no se escribe a mano: *un numero escrito a mano es una cuenta que puede estar mal*.
    cantidad_total_kg: float | None = Field(default=None, gt=0)
    # Y el kg/ha sigue admitiendose: es el camino de siempre, y **lo ya guardado no se toca**.
    kg_ha_producto: float | None = Field(default=None, gt=0)
    modo_aplicacion: str | None = None
    momento: str | None = None
    plan_id: int | None = None
    # La hoja 6 del cuaderno de la Junta pide el nº de albarán (de dónde salió el abono) y el tipo
    # de fertilización, que allí se abrevia con tres códigos: (F) fertirrigación, (AF) abonado de
    # fondo y (AC) abonado de cobertera. Se guardan con el nombre largo y hay un test que comprueba
    # que solo se aceptan esos tres: un valor inventado aquí sería un dato falso en el cuaderno.
    numero_albaran: str | None = None
    tipo_fertilizacion: str | None = None
    # La factura de la que salió este abono, cuando se ha traído la factura.
    factura_id: int | None = None
    nitratos_agua_riego: float | None = Field(default=None, ge=0)
    observaciones: str | None = None


class FertilizacionSalida(SalidaBase):
    id: int
    campana_id: int
    fecha: dt.date
    parcela_id: int | None
    # El grupo, cuando el abono es de varias parcelas a la vez. Faltaba aquí desde el principio:
    # la tabla lo tenía y la entrada lo aceptaba, pero **la salida no lo devolvía**, así que
    # ninguna pantalla podía saber de qué grupo era un abono. Mismo fallo que el de la cantidad
    # comprada del producto, y lo encontró un test al apuntar un abono en un grupo.
    grupo_id: int | None = None
    superficie_ha: float
    fertilizante_nombre: str | None
    # **La composición y lo que aporta, con su tercer estado** (A6). `None` es «no consta la
    # composición de este abono»: no se puede calcular lo que aporta, y un cero aquí sería una
    # afirmación que acabaría en el documento que se firma y en la exportación a la Junta.
    riqueza_n: float | None
    riqueza_p: float | None
    riqueza_k: float | None
    kg_ha_producto: float
    cantidad_total_kg: float
    uf_n_ha: float | None
    uf_p_ha: float | None
    uf_k_ha: float | None
    uf_n_total: float | None
    uf_p_total: float | None
    uf_k_total: float | None
    plan_id: int | None
    # Los mismos tres estados que en los tratamientos: `None` es «no se ha podido comprobar».
    en_zona_vulnerable: bool | None
    anulado: bool
    # Lo que pide la hoja 6 del cuaderno: de dónde salió el abono y de qué tipo es.
    numero_albaran: str | None = None
    tipo_fertilizacion: str | None = None
    factura_id: int | None = None


# --------------------------------------------------------------------------
# El plan de abono del año (lo que la app oficial llama «recomendación de nutrientes»)
# --------------------------------------------------------------------------


class AbonoPrevisto(EntradaBase):
    """Un abono que se piensa echar: cuál, cuánto y en qué momento."""

    fertilizante_id: int | None = None
    nombre: str | None = None
    kg_ha: float | None = Field(default=None, ge=0)
    momento: str | None = None


class PlanAbonadoEntrada(EntradaBase):
    campana_id: int
    parcela_id: int | None = None
    grupo_id: int | None = None
    # Sin `min_length` ni `gt=0` a propósito: así un plan al que le falta el cultivo o la
    # superficie llega hasta `validaciones.py` y el agricultor recibe el aviso escrito
    # para él, en vez del error técnico del esquema, que no dice nada.
    cultivo: str = ""
    superficie_ha: float = Field(default=0.0, ge=0)
    produccion_esperada_kg_ha: float | None = Field(default=None, ge=0)
    necesidad_n: float | None = Field(default=None, ge=0)
    necesidad_p: float | None = Field(default=None, ge=0)
    necesidad_k: float | None = Field(default=None, ge=0)
    aportes_suelo_agua: float | None = Field(default=None, ge=0)
    detalle: list[AbonoPrevisto] = Field(default_factory=list)
    # Si se usó una herramienta para hacer el plan. El anexo II lo pide así, con un sí o un no.
    herramienta: bool | None = None
    notas: str | None = None
    # El análisis en el que se basa el plan. Opcional: hay agricultores que no tienen
    # análisis y hacen el plan igual.
    analitica_id: int | None = None


class PlanAbonadoSalida(SalidaBase):
    id: int
    campana_id: int
    parcela_id: int | None
    grupo_id: int | None
    cultivo: str
    superficie_ha: float
    produccion_esperada_kg_ha: float | None
    necesidad_n: float | None
    necesidad_p: float | None
    necesidad_k: float | None
    aportes_suelo_agua: float | None
    detalle: list | None
    herramienta: bool | None = None
    notas: str | None
    analitica_id: int | None


class PlanConLoAplicado(PlanAbonadoSalida):
    """El plan junto a lo que de verdad se ha echado.

    Es la parte que de verdad sirve: un plan sin saber si se está cumpliendo es un papel
    guardado en un cajón.
    """

    # Lo que se calcula al vuelo, y por eso está aquí y no en el plan a secas: qué había sembrado
    # en esa parcela la campaña anterior. **No se guarda**, se deduce del historial de cultivos,
    # así que no puede quedarse viejo.
    cultivo_precedente: str | None = None

    aplicado_n: float
    aplicado_p: float
    aplicado_k: float
    queda_n: float | None
    queda_p: float | None
    queda_k: float | None
    se_ha_pasado: bool
    apuntes: int
    mensaje: str
    # El análisis en el que se basa el plan, ya resuelto para poder enseñarlo sin una
    # segunda llamada. Es None cuando el plan no se apoya en ningún análisis.
    #
    # El tipo es `AnaliticaConSitio` y no `AnaliticaSalida` a propósito: con el genérico,
    # Pydantic recortaría el nombre de dónde salió la muestra y los nombres de cada número,
    # y la pantalla se quedaría sin lo único que hace útil al análisis.
    analisis: "AnaliticaConSitio | None" = None


# --------------------------------------------------------------------------
# Lo que se vende: cosecha comercializada y venta directa
#
# El contenido mínimo del CUE la llama «Cosecha comercializada y/o venta directa» y la sitúa
# a nivel de Explotación. La ruta y el modelo se llaman «venta» porque ya existe un
# `/api/cosecha` para lo que se recoge, y dos cosas llamadas «cosecha» serían una trampa.
# --------------------------------------------------------------------------


class VentaEntrada(EntradaBase):
    campana_id: int
    tipo: str = Field(default="comercializada", max_length=_cabe_en_la_columna(models.VentaDeCosecha, "tipo"))
    fecha: dt.date
    # La norma la llama «fecha (intervalo de tiempo)»: una partida puede salir en varios
    # días. Si no viene, la venta fue de un solo día.
    fecha_fin: dt.date | None = None
    # Sin `min_length` ni `gt=0` a propósito: así una venta a la que le falta el producto o
    # la cantidad llega hasta `validaciones.py` y el agricultor recibe el aviso escrito para
    # él, en vez del error técnico del esquema, que no dice nada.
    #
    # **Con `max_length` sí, y desde la revisión del T12**: lo que no quepa en su columna se rechaza en la
    # puerta con una frase, porque en PostgreSQL la fila no entra y la operación entera se pierde.
    producto: str = Field(default="", max_length=_cabe_en_la_columna(models.VentaDeCosecha, "producto"))
    variedad: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.VentaDeCosecha, "variedad"))
    cantidad: float | None = None
    unidad: str = Field(default="kg", max_length=_cabe_en_la_columna(models.VentaDeCosecha, "unidad"))
    lote: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.VentaDeCosecha, "lote"))
    comprador: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.VentaDeCosecha, "comprador")
    )
    numero_albaran: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.VentaDeCosecha, "numero_albaran")
    )
    parcela_id: int | None = None
    grupo_id: int | None = None
    observaciones: str | None = None

    # ── El dinero y el de quién es (T12, E6, 03/10/2026) ────────────────────────────────────
    #
    # **Todo opcional, y es la mitad del ticket.** Una entrega de 8.000 kg sin precio se apunta
    # igual: es el caso A08 del contrato, y bloquearla sería impedir apuntar lo que de verdad salió
    # de la finca. Lo que no se puede es convertirla en un ingreso de cero euros, y por eso el
    # importe que falta se queda en `None` y la pantalla lo dice.
    #
    # Los importes llegan como **texto decimal** (contrato §2: «cadenas decimales en intercambio») y
    # se convierten con `dinero.a_decimal`, que **rechaza los números de coma flotante** en vez de
    # redondearlos en silencio. El validador está aquí y no en el router para que la conversión sea
    # la misma en el alta, en la corrección y en cualquier sitio que use este esquema.
    importe: Decimal | None = None
    precio_unitario: Decimal | None = None
    vencimiento: dt.date | None = None
    contacto_id: int | None = None
    # De qué cosecha salió (la labor de tipo cosecha que ya existe). Ver `models.VentaDeCosecha`.
    cosecha_id: int | None = None
    # La clave con la que el móvil reconoce una petición repetida: reenviar la misma entrega
    # **devuelve la que ya había**, no crea otra (contrato §2).
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.VentaDeCosecha, "clave_de_reenvio")
    )

    @field_validator("importe", "precio_unitario", mode="before")
    @classmethod
    def _los_importes_son_exactos(cls, valor):
        """Convierte el importe a `Decimal` y **se niega a aceptar un `float`**.

        Un `float` que llegue aquí (un número de JSON en vez de una cadena) ya perdió céntimos
        antes de entrar, así que se rechaza con un mensaje que dice qué mandar. El porqué entero
        está en `app/dinero.py`.
        """
        return _un_importe_que_cabe(valor)

    # Y lo que no quepa en su columna se rechaza aquí, con la frase del agricultor (ver la cabecera).
    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.VentaDeCosecha)


class AjusteDeUnaEntrega(SalidaBase):
    """Una devolución o un ajuste de peso, humedad o calidad, ya listo para enseñarlo.

    Los `etiqueta_*` los pone el servidor y no la pantalla: los nombres de los cuatro tipos y de los
    cinco orígenes son texto del agricultor y viven en `textos.py`.
    """

    id: int
    tipo: str
    etiqueta_tipo: str = ""
    fecha: dt.date | None = None
    cantidad: float | None = None
    unidad: str | None = None
    importe: Decimal | None = None
    texto_importe: str = ""
    origen: str
    etiqueta_origen: str = ""
    motivo: str
    evidencia_descripcion: str | None = None
    # Si el ajuste trae el papel en sí. Cuando no lo trae, la pantalla lo dice («sin papel adjunto»)
    # en vez de dar por bueno que lo hay.
    tiene_papel: bool = False
    nombre_del_papel: str | None = None
    anulado: bool = False
    motivo_anulacion: str | None = None


class AjusteEntrada(EntradaBase):
    """Lo que se apunta de una devolución o de un ajuste de peso, humedad o calidad.

    **Este esquema no existía, y su ausencia era un defecto grave** (revisión del T12): el endpoint recibía
    un `dict` crudo y convertía los números y las fechas dentro, así que un importe mandado como número de
    JSON, un importe o una cantidad que no son números, o una fecha escrita en castellano, lanzaban
    `ErrorDeDinero`/`ValueError` **dentro del endpoint** y el servidor contestaba **500**. Como el móvil
    **reintenta los 5xx** (`app.js`, `mandarPendientes`), eso no era «un error feo»: era un apunte de dinero
    en la cola del móvil reintentándose para siempre.

    Ahora la puerta es la misma que la del cobro (`CobroEntrada`): se valida antes de entrar y lo que no vale
    contesta 422 con su frase, en vez de una traza del servidor.

    La `cantidad` y el `importe` son **diferencias con signo** (una devolución resta), así que se aceptan
    negativas; lo que no se acepta es una cantidad que no es un número, ni un importe que no cabe en su
    columna.
    """

    # `peso`, `humedad`, `calidad` y `devolucion` son las cuatro de `ventas.TIPOS_DE_AJUSTE`, y el router las
    # comprueba contra esa lista: aquí solo se acota el ancho, que es lo que rompía en PostgreSQL.
    tipo: str = Field(default="", max_length=_cabe_en_la_columna(models.AjusteDeEntrega, "tipo"))
    origen: str = Field(default="", max_length=_cabe_en_la_columna(models.AjusteDeEntrega, "origen"))
    motivo: str = ""
    fecha: dt.date | None = None
    cantidad: float | None = None
    unidad: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.AjusteDeEntrega, "unidad"))
    importe: Decimal | None = None
    evidencia_descripcion: str | None = Field(
        default=None,
        max_length=_cabe_en_la_columna(models.AjusteDeEntrega, "evidencia_descripcion"),
    )
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.AjusteDeEntrega, "clave_de_reenvio")
    )

    @field_validator("importe", mode="before")
    @classmethod
    def _el_importe_es_exacto(cls, valor):
        """El importe de un ajuste pasa por las mismas dos puertas que los demás: sin `float` y con tope.

        Y se admite **negativo**, que es lo normal aquí (una devolución resta): el tope se mide sobre el
        valor absoluto, así que `-40.50` entra y `-999999999999.99` no.
        """
        return _un_importe_que_cabe(valor)

    @field_validator("cantidad", mode="before")
    @classmethod
    def _la_cantidad_es_un_numero(cls, valor):
        """Una cantidad que no es un número se rechaza **aquí** y no dentro del endpoint.

        Antes llegaba al router y `dinero.de_texto` lanzaba `ErrorDeDinero` sin que nadie la recogiera: un
        500. Un `inf` o un `nan` tampoco valen: romperían todas las sumas del año.
        """
        if valor is None or valor == "":
            return None
        if isinstance(valor, str):
            numero = dinero.de_texto(valor)
            if numero is None:
                raise ValueError(f"«{valor}» no es una cantidad.")
            return float(numero)
        if isinstance(valor, float) and not (valor == valor and valor not in (float("inf"), float("-inf"))):
            raise ValueError("Esa cantidad no es un número que se pueda usar.")
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(f"«{valor}» no es una cantidad.")
        return float(valor)

    # Y lo que no quepa en su columna, con la frase del agricultor.
    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.AjusteDeEntrega)


class VentaSalida(SalidaBase):
    id: int
    campana_id: int
    tipo: str
    fecha: dt.date
    fecha_fin: dt.date | None
    producto: str
    variedad: str | None
    cantidad: float
    unidad: str
    lote: str | None
    comprador: str | None
    numero_albaran: str | None
    parcela_id: int | None
    grupo_id: int | None
    observaciones: str | None
    anulado: bool
    # Los kilos de esta venta, o None si va en unidades. Se calcula al vuelo para no guardar
    # dos veces el mismo dato: si un día cambia el factor de conversión, el apunte histórico
    # no se queda mintiendo.
    kilos: float | None = None
    # Y los kilos **con los ajustes aplicados** (una devolución de 3.000 kg deja la entrega en
    # 39.000): es lo que de verdad se llevó el comprador. Se calcula, no se guarda, por el mismo
    # motivo. Si alguna cantidad no se sabe, se queda en `None` y no en la cantidad apuntada.
    kilos_netos: float | None = None

    # ── El dinero (T12) ────────────────────────────────────────────────────────────────────
    #
    # `importe` es **lo que se sabe del importe de la entrega tal y como se guardó**: `None` quiere
    # decir «no se sabe», que no es cero (A08). `importe_total` es el importe **con los ajustes ya
    # aplicados**, que es lo que de verdad se cobra, y `cobrado`/`pendiente` son lo que ha entrado y
    # lo que falta. Los cuatro se calculan, no se guardan.
    contacto_id: int | None = None
    cosecha_id: int | None = None
    importe: Decimal | None = None
    importe_total: Decimal | None = None
    precio_unitario: Decimal | None = None
    vencimiento: dt.date | None = None
    cobrado: Decimal | None = None
    pendiente: Decimal | None = None
    # sin_importe | sin_facturar | sin_cobrar | cobrada_en_parte | cobrada | vencida.
    estado: str = ""
    facturada: bool = False
    factura_emitida_id: int | None = None
    factura_numero: str | None = None
    ajustes: list[AjusteDeUnaEntrega] = Field(default_factory=list)
    # Lo que se enseña ya escrito, para que la pantalla no componga frases de dinero.
    texto_importe: str = ""
    texto_importe_total: str = ""
    texto_cobrado: str = ""
    texto_pendiente: str = ""


class VentaConNombres(VentaSalida):
    """La venta con los nombres ya resueltos, para poder enseñarla sin más llamadas."""

    etiqueta_tipo: str
    donde: str
    etiqueta_unidad: str
    texto_cantidad: str
    etiqueta_estado: str = ""
    # De qué cosecha salió, dicho como el agricultor lo reconoce («El Prado, 12/07/2026»), o vacío.
    de_que_cosecha: str = ""


class InformeDeVentas(BaseModel):
    """El «Informe Cosechas Comercializadas» de la app oficial."""

    campana: int
    cuantas: int
    vendido_kg: float
    cosechado_kg: float
    queda_kg: float
    hay_unidades: bool
    titulos: list[str]
    filas: list[dict]
    vacio: str
    mensaje: str


# --------------------------------------------------------------------------
# La tabla de lo que se vende, con su pie (T12, E6, 03/10/2026)
#
# El contrato (§3, «Todas las tablas») pide tres cosas que no se pueden cumplir desde el navegador:
# el total del conjunto **filtrado** lo calcula el servidor (no la página visible), las fechas y las
# cantidades se ordenan **por valor** y no por el texto ya formateado, y el pie dice cuántos hay del
# total. Por eso la tabla es una respuesta del servidor y no una lista que la pantalla suma.
# --------------------------------------------------------------------------


class ColumnaDeUnaTabla(BaseModel):
    clave: str
    texto: str
    # Si esa columna se puede ordenar. Se dice desde el servidor porque el orden se hace allí.
    ordenable: bool = True


class TablaDeVentas(BaseModel):
    """Las entregas filtradas, sus columnas, el pie y los cuatro números del dinero.

    Los totales van **en texto decimal** (contrato §2) y salen de las mismas filas que se enseñan,
    así que el pie y el detalle no pueden decir cosas distintas. Lo que no se sabe se cuenta aparte
    (`sin_importe`), que es lo que impide que el pie parezca completo cuando no lo está.
    """

    columnas: list[ColumnaDeUnaTabla]
    filas: list[dict]
    pie: str
    avisos: list[str] = Field(default_factory=list)
    totales: dict
    # Cuántas hay contando el filtro y cuántas sin filtrar: el «10 de 64» del contrato.
    filtradas: int
    total: int


# --------------------------------------------------------------------------
# La factura emitida y los cobros (T12, E6, 03/10/2026)
# --------------------------------------------------------------------------
#
# **Aquí no hay ni un impuesto, ni un número de serie oficial, ni una palabra que haga pasar esto
# por un documento con validez ante nadie.** El contrato lo dice por escrito: «La emisión fiscal
# completa requiere especificación normativa propia antes de activarse como tal». Lo que se modela
# es la cuenta de gestión del agricultor —qué entregó, por cuánto y qué le deben— y los textos de la
# pantalla lo dicen tal cual.
# --------------------------------------------------------------------------


class FacturaEmitidaEntrada(EntradaBase):
    """Lo que hace falta para juntar varias entregas en una factura nuestra."""

    campana_id: int | None = None
    fecha: dt.date
    vencimiento: dt.date | None = None
    numero: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.FacturaEmitida, "numero"))
    cliente: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.FacturaEmitida, "cliente")
    )
    cliente_nif: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.FacturaEmitida, "cliente_nif")
    )
    contacto_id: int | None = None
    notas: str | None = None
    # Las entregas que van dentro. **Nunca vacío**: una factura sin nada dentro no es una factura, y
    # el router lo dice con palabras en vez de dejar un documento en blanco.
    entregas: list[int] = Field(default_factory=list)
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.FacturaEmitida, "clave_de_reenvio")
    )

    # Lo que no quepa en su columna se rechaza con la frase del agricultor (revisión del T12): el número
    # de una factura, su cliente y su NIF son texto del agricultor y tienen tope en la base.
    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.FacturaEmitida)


class LineaDeUnaFacturaEmitida(BaseModel):
    """Una entrega dentro de la factura, con su fotografía del día que se emitió."""

    id: int
    venta_id: int
    fecha: dt.date | None = None
    descripcion: str | None = None
    cantidad: float | None = None
    unidad: str | None = None
    importe: Decimal | None = None
    texto_importe: str = ""
    anulada: bool = False
    # Si la entrega ya no está (se borró), la línea se queda sin enlace y se dice.
    entrega_existe: bool = True
    # El importe que tiene **ahora** la entrega, si es distinto del que se facturó: la diferencia
    # observada que el contrato pide registrar sin reescribir lo emitido.
    importe_ahora: Decimal | None = None
    texto_importe_ahora: str = ""
    diferencia: bool = False


class AplicacionDeUnCobroSalida(BaseModel):
    """A qué factura va una parte de este cobro, y cuánto (CRM-01, 11/10/2026).

    Es lo que permite que un ingreso salde **varias** deudas: una fila por factura. Se enseña en la ficha del
    cobro y en la de la factura, para que se pueda comprobar de dónde sale cada cifra.
    """

    factura_emitida_id: int
    factura_numero: str | None = None
    importe: Decimal | None = None
    texto_importe: str = ""


class CobroDeUnaFactura(BaseModel):
    """Un cobro, tal y como se enseña (en la lista y dentro de la factura)."""

    id: int
    fecha: dt.date | None = None
    # La fecha con su rótulo del servidor («Fecha: 01/08/2026»), compuesta en el router: la ficha la enseña
    # tal cual, y una frase compuesta dentro de un componente es una frase escrita a mano.
    fecha_linea: str = ""
    importe: Decimal | None = None
    texto_importe: str = ""
    importe_imputado: Decimal | None = None
    texto_imputado: str = ""
    sin_asignar: Decimal | None = None
    texto_sin_asignar: str = ""
    # **A qué facturas va este dinero** (CRM-01): una fila por deuda. Un cobro que salda una sola factura
    # trae una; uno que salda tres, tres; y un dinero sin conciliar, ninguna.
    aplicaciones: list[AplicacionDeUnCobroSalida] = []
    factura_emitida_id: int | None = None
    factura_numero: str | None = None
    cliente: str | None = None
    contacto_id: int | None = None
    forma: str = "transferencia"
    etiqueta_forma: str = ""
    referencia: str | None = None
    notas: str | None = None
    anulado: bool = False
    motivo_anulacion: str | None = None


class FacturaEmitidaSalida(SalidaBase):
    id: int
    campana_id: int | None = None
    numero: str | None = None
    fecha: dt.date | None = None
    vencimiento: dt.date | None = None
    cliente: str | None = None
    cliente_nif: str | None = None
    contacto_id: int | None = None
    importe_total: Decimal | None = None
    texto_total: str = ""
    cobrado: Decimal | None = None
    texto_cobrado: str = ""
    pendiente: Decimal | None = None
    texto_pendiente: str = ""
    estado: str = ""
    etiqueta_estado: str = ""
    # Cómo se llama esta factura: «Factura F-2026-1 · Cooperativa» y, si no tiene número, su fecha. Lo
    # compone el servidor y no la pantalla: una frase compuesta dentro de un componente es una frase
    # escrita a mano, y aquí no hay ni una (`AGENTS.md` §3.1).
    titulo: str = ""
    # La fecha con su rótulo y el nombre con lo que queda por cobrar: las dos compuestas aquí, por el mismo
    # motivo. La segunda es la que permite **elegir** una factura en la lista de un cobro.
    fecha_linea: str = ""
    titulo_con_pendiente: str = ""
    anulada: bool = False
    motivo_anulacion: str | None = None
    notas: str | None = None
    lineas: list[LineaDeUnaFacturaEmitida] = Field(default_factory=list)
    cobros: list[CobroDeUnaFactura] = Field(default_factory=list)
    # Cuántas entregas van dentro y cuántas se pueden cobrar todavía.
    entregas: int = 0


class AplicacionDeUnCobroEntrada(BaseModel):
    """Una parte del cobro, contra una factura concreta (CRM-01, 11/10/2026).

    Es lo que permite repartir **un** ingreso entre **varias** deudas —el cliente que paga de una vez tres
    albaranes—, que es el caso que el encargo pide con números: 350 entre una deuda de 100 y otra de 250.
    """

    factura_emitida_id: int
    importe: Decimal | None = None

    @field_validator("importe", mode="before")
    @classmethod
    def _el_importe_es_exacto(cls, valor):
        return _un_importe_que_cabe(valor)


class CobroEntrada(EntradaBase):
    fecha: dt.date | None = None
    # Obligatorio y mayor que cero: un cobro de cero euros no es un cobro. Se comprueba en el router
    # para poder decirlo con palabras.
    importe: Decimal | None = None
    # **Una factura suelta** (el camino de siempre: este cobro salda esta factura) **o el reparto**, pero no
    # las dos cosas: `aplicaciones` manda cuando viene, porque es lo que permite varias deudas. Si vienen las
    # dos, se contesta 422 diciendo cuál sobra en vez de elegir por el agricultor.
    factura_emitida_id: int | None = None
    aplicaciones: list[AplicacionDeUnCobroEntrada] | None = None
    cliente: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.Cobro, "cliente"))
    contacto_id: int | None = None
    forma: str = Field(default="transferencia", max_length=_cabe_en_la_columna(models.Cobro, "forma"))
    referencia: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.Cobro, "referencia"))
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Cobro, "clave_de_reenvio")
    )

    @field_validator("importe", mode="before")
    @classmethod
    def _el_importe_es_exacto(cls, valor):
        """Sin `float` y con tope, como el de una entrega: un cobro de veintidós cifras **también** tumbaba
        la operación entera en PostgreSQL (revisión del T12)."""
        return _un_importe_que_cabe(valor)

    # Y lo que no quepa en su columna, con la frase del agricultor.
    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.Cobro)


class ConciliacionEntrada(EntradaBase):
    """A qué factura salda un cobro. Vacío es «quitar la asignación», y no borra nada."""

    factura_emitida_id: int | None = None


class RespuestaDeUnCobro(BaseModel):
    """Lo que se contesta al apuntar o conciliar un cobro: el cobro y lo que ha pasado después.

    Es lo que hace que la pantalla pueda decir **el número exacto** («de este cobro van 40 a la
    factura y le quedan 81 por cobrar») sin volver a preguntar nada y sin hacer cuentas en el
    navegador, que es donde el dinero perdería céntimos.
    """

    cobro: CobroDeUnaFactura
    ya_estaba: bool = False
    avisos: list[str] = Field(default_factory=list)
    factura: FacturaEmitidaSalida | None = None


# --------------------------------------------------------------------------
# Medidas preventivas de la explotación (gestión integrada de plagas)
#
# La app oficial las tiene en «Explotación: Medidas Preventivas», y el contenido mínimo
# del CUE las sitúa a nivel de Explotación. Se mandan y se devuelven TODAS de una vez,
# porque la pantalla es una sola con diez casillas y un botón de guardar.
# --------------------------------------------------------------------------


class MedidaEntrada(EntradaBase):
    """Una medida del catálogo con la respuesta del agricultor."""

    codigo: str = Field(min_length=1, max_length=40)
    aplicada: bool = True
    observaciones: str | None = None


class MedidasEntrada(EntradaBase):
    """La declaración entera de una finca.

    `aplicadas` es la lista de códigos marcados. Se manda como lista y no como un
    diccionario de `{codigo: sí/no}` porque es lo que de verdad manda la pantalla: las
    casillas marcadas. Lo que no venga en la lista se entiende como «no la aplico», que es
    exactamente lo que ve el agricultor cuando deja una casilla en blanco.
    """

    aplicadas: list[str] = Field(default_factory=list)
    observaciones: dict[str, str] = Field(default_factory=dict)


class MedidaSalida(SalidaBase):
    codigo: str
    aplicada: bool
    observaciones: str | None = None


class MedidaConPregunta(MedidaSalida):
    """La medida con la pregunta que se le enseña al agricultor.

    `etiqueta` es el nombre oficial, el que se imprime y se entrega. `pregunta` es lo que
    se lee en pantalla. La app nunca enseña la etiqueta sin explicarla.
    """

    pregunta: str
    etiqueta: str


class DeclaracionDeMedidas(BaseModel):
    """Lo que devuelve la pantalla de medidas preventivas."""

    medidas: list[MedidaConPregunta]
    aplicadas: list[str]
    declarada: bool
    cuantas: int
    mensaje: str
    explicacion: str
    # Códigos que llegaron y no están en el catálogo. Se devuelven para poder decirlo: un
    # código que el servidor no conoce significa que la pantalla y él se han
    # desincronizado, y eso no puede pasar en silencio.
    descartadas: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# Analíticas de laboratorio (la sección «Otras Actividades: Analíticas» del CUE)
# --------------------------------------------------------------------------


class ParametroEntrada(EntradaBase):
    """Un número del boletín: qué es y cuánto vale.

    `valor` admite texto además de número a propósito. El agricultor escribe en un móvil,
    y ahí «7,4» lleva coma. Si el esquema solo aceptara números, ese «7,4» se rechazaría
    con un error técnico que no dice nada, en vez de apuntarse. La conversión —y el
    descarte de lo que no sea un número— la hace `servicios.limpia_parametros`.

    `unidad` se acepta pero no se usa: la pone el catálogo. Se admite en la entrada para
    que una interfaz que la mande no reciba un error, pero el valor guardado es siempre
    el del catálogo, que es lo que hace comparables dos análisis de años distintos.
    """

    clave: str = Field(min_length=1, max_length=40)
    valor: float | str | None = None
    unidad: str | None = None


class AnaliticaEntrada(EntradaBase):
    campana_id: int
    tipo: str
    fecha_toma_muestra: dt.date
    fecha_resultado: dt.date | None = None
    parcela_id: int | None = None
    instalacion_id: int | None = None
    lote: str | None = None
    laboratorio: str | None = None
    nif_laboratorio: str | None = None
    numero_informe: str | None = None
    tipo_analisis: str | None = None
    sustancia_detectada: str | None = None
    parametros: list[ParametroEntrada] = Field(default_factory=list)
    observaciones: str | None = None


class AnaliticaSalida(SalidaBase):
    id: int
    campana_id: int
    tipo: str
    etiqueta_tipo: str = ""
    fecha_toma_muestra: dt.date
    fecha_resultado: dt.date | None
    parcela_id: int | None
    instalacion_id: int | None
    lote: str | None
    laboratorio: str | None
    nif_laboratorio: str | None
    numero_informe: str | None
    tipo_analisis: str | None
    sustancia_detectada: str | None
    parametros: list = Field(default_factory=list)
    fichero_nombre: str | None
    fichero_tipo: str | None
    fichero_bytes: int | None
    observaciones: str | None
    anulado: bool
    motivo_anulacion: str | None = None
    # Cuántos años hace que se cogió la muestra. Se calcula al vuelo para poder avisar de
    # que un análisis viejo no sirve para decidir el abono de hoy.
    anios: int | None = None


class AnaliticaConSitio(AnaliticaSalida):
    """El análisis con el nombre de dónde salió la muestra.

    Se resuelve en el servidor y no en la interfaz a propósito: la interfaz no tiene por
    qué saber que «varias parcelas» es un caso distinto de una parcela borrada, y si lo
    supiera, cada pantalla lo escribiría de una manera.
    """

    donde: str
    parametros_con_nombre: list[dict] = Field(default_factory=list)


class InformeDeAnalisis(BaseModel):
    """El «Informe Analíticas» de la app oficial: todos los análisis de la campaña."""

    campana: int
    cuantos: int
    filas: list[dict]
    titulos: list[str]
    vacio: str


# --------------------------------------------------------------------------
# Labores y anulación
# --------------------------------------------------------------------------


class LaborEntrada(EntradaBase):
    campana_id: int
    tipo: str
    fecha: dt.date
    parcela_id: int | None = None
    grupo_id: int | None = None
    superficie_ha: float | None = Field(default=None, ge=0)
    cultivo: str | None = None
    variedad: str | None = None
    detalles: dict | None = None
    observaciones: str | None = None
    # Siembra y plantación (bloque 6 del contenido mínimo del CUE).
    cantidad_semilla_kg: float | None = Field(default=None, ge=0)
    dosis_siembra_kg_ha: float | None = Field(default=None, ge=0)
    material_tratado: bool | None = None
    material_adquirido: bool | None = None
    fecha_adquisicion: dt.date | None = None
    # El bloque «uso de semilla tratada» del anexo II: qué tratamiento recibió la semilla, cuándo
    # y si funcionó. Hasta la ronda 5 solo se apuntaba «semilla tratada: sí».
    tratamiento_semilla: str | None = None
    fecha_tratamiento_semilla: dt.date | None = None
    eficacia_tratamiento_semilla: str | None = None
    lote_semilla: str | None = None
    siembra_directa: bool | None = None
    densidad_plantacion: float | None = Field(default=None, ge=0)
    marco_plantacion: str | None = None
    # Riego: el agua también es un dato del cuaderno.
    volumen_agua: float | None = Field(default=None, ge=0)
    unidad_agua: str | None = None
    origen_agua: str | None = None
    sistema_riego: str | None = None
    numero_contador: str | None = None
    nitratos_agua: float | None = Field(default=None, ge=0)
    # El pastoreo: dos preguntas que el interfaz de la Junta pide como obligatorias.
    animales_terceros: bool | None = None
    animales_propios: bool | None = None
    semillas_siembra: bool | None = None
    plantas_cosechadas: bool | None = None
    sin_cosechar_ambiental: bool | None = None
    restos_cosecha_depositados: bool | None = None
    fecha_establecimiento_cubierta: dt.date | None = None
    tipo_cobertura: str | None = None
    anchura_cubierta_m: float | None = Field(default=None, ge=0)
    anchura_libre_proyeccion_m: float | None = Field(default=None, ge=0)
    restos_desbroce_depositados: bool | None = None
    restos_poda_depositados: bool | None = None
    # **Con qué máquina.** El contenido mínimo del CUE lo pide en los bloques de labores y de
    # siembra, y antes no se podía ni apuntar: un tratamiento decía su máquina y una labor no.
    equipo_id: int | None = None


class LaborSalida(SalidaBase):
    id: int
    campana_id: int
    tipo: str
    fecha: dt.date
    parcela_id: int | None
    # El grupo, cuando la labor es de varias parcelas a la vez. Faltaba en la salida igual que en
    # los abonos: se guardaba y no se devolvía.
    grupo_id: int | None = None
    superficie_ha: float | None
    cultivo: str | None
    detalles: dict | None
    anulado: bool
    # Lo de la siembra y lo del riego, para poder enseñarlo y para el volcado oficial.
    cantidad_semilla_kg: float | None = None
    dosis_siembra_kg_ha: float | None = None
    material_tratado: bool | None = None
    material_adquirido: bool | None = None
    fecha_adquisicion: dt.date | None = None
    # El bloque «uso de semilla tratada» del anexo II: qué tratamiento recibió la semilla, cuándo
    # y si funcionó. Hasta la ronda 5 solo se apuntaba «semilla tratada: sí».
    tratamiento_semilla: str | None = None
    fecha_tratamiento_semilla: dt.date | None = None
    eficacia_tratamiento_semilla: str | None = None
    lote_semilla: str | None = None
    siembra_directa: bool | None = None
    densidad_plantacion: float | None = None
    marco_plantacion: str | None = None
    animales_terceros: bool | None = None
    animales_propios: bool | None = None
    semillas_siembra: bool | None = None
    plantas_cosechadas: bool | None = None
    sin_cosechar_ambiental: bool | None = None
    restos_cosecha_depositados: bool | None = None
    fecha_establecimiento_cubierta: dt.date | None = None
    tipo_cobertura: str | None = None
    anchura_cubierta_m: float | None = None
    anchura_libre_proyeccion_m: float | None = None
    restos_desbroce_depositados: bool | None = None
    restos_poda_depositados: bool | None = None
    # La máquina con la que se hizo la labor. Sale en la respuesta porque es lo que permite
    # enseñarla en el cuaderno y comprobar que es la que tiene la ITEAf en regla.
    equipo_id: int | None = None
    # **Lo que el agricultor escribió de la labor.** Se guardaba desde siempre y no se devolvía: no
    # se notaba porque ninguna pantalla lo enseñaba, pero al poder corregir una labor (ronda 91) el
    # fallo se vuelve grave —el formulario se rellena con lo que devuelve la API, así que corregir
    # una labor sin esto **borraba las observaciones sin decir nada**—. Un dato que se guarda y no
    # se devuelve es un dato que la siguiente pantalla pisa.
    observaciones: str | None = None
    volumen_agua: float | None = None
    unidad_agua: str | None = None
    origen_agua: str | None = None
    sistema_riego: str | None = None
    numero_contador: str | None = None
    nitratos_agua: float | None = None


class AnulacionEntrada(EntradaBase):
    motivo: str = Field(min_length=3, max_length=500)


class CosechaEntrada(EntradaBase):
    campana_id: int
    fecha: dt.date
    parcela_id: int
    producto: str | None = None
    cantidad_kg: float | None = Field(default=None, ge=0)
    semillas_siembra: bool | None = None
    plantas_cosechadas: bool | None = None
    sin_cosechar_ambiental: bool | None = None
    restos_cosecha_depositados: bool | None = None
    # **Con qué máquina se cosechó.** El asistente lo preguntaba desde la ronda 5 y el navegador lo
    # mandaba, pero este esquema no tenía el campo: Pydantic lo descartaba en silencio y el dato se
    # quedaba fuera del cuaderno. Se encontró en la ronda 91, al escribir la corrección de una
    # cosecha (que reutiliza este mismo esquema). El contenido mínimo del CUE pide la maquinaria en
    # su hoja de labores, y una cosecha es una labor.
    equipo_id: int | None = None


class AvisoSalida(BaseModel):
    codigo: str
    mensaje: str
    bloquea: bool
    campo: str | None = None


class ResultadoValidacion(BaseModel):
    puede_guardarse: bool
    avisos: list[AvisoSalida]


# --------------------------------------------------------------------------
# Cuenta
# --------------------------------------------------------------------------


class RegistroEntrada(EntradaBase):
    explotacion: ExplotacionEntrada
    nombre: str = Field(min_length=1, max_length=120)
    correo: str = Field(min_length=3, max_length=200)
    clave: str = Field(min_length=8, max_length=200)


class EntrarEntrada(EntradaBase):
    correo: str
    clave: str


class TokenSalida(BaseModel):
    token: str
    usuario_id: int
    explotacion_id: int
    nombre: str


# --- Las fincas de una cuenta y quién entra en ellas (ronda 89) -------------------------------


class FincaSalida(BaseModel):
    """Una finca en la que puede entrar esta cuenta."""

    id: int
    nombre: str
    municipio: str = ""
    # «titular» (la creó) o «ayudante» (se la han dado).
    papel: str
    # La finca en la que está apuntando ahora mismo.
    activa: bool
    # Las hectáreas que tiene apuntadas esa finca (la suma de sus tierras). Lo pidió el diseño de Stitch de
    # «quién entra en mi finca» (ronda 90): al elegir en cuál trabajas, el tamaño es lo que distingue una
    # finca de otra cuando se llaman parecido. Se cuenta con los datos que ya hay, y si no hay tierras
    # apuntadas vale cero.
    hectareas: float = 0.0
    # **Y cuántas de esas tierras no tienen la superficie apuntada** (A7, 03/10/2026). Sin este número, una
    # finca con tierras sin superficie enseñaba una suma **más pequeña que parecía completa** (SQL ignora los
    # `NULL` al sumar): es un dato que no se sabe convertido en un cero que parece un dato.
    tierras_sin_superficie: int = 0


class CambiarDeFincaEntrada(BaseModel):
    explotacion_id: int


class NuevaCuentaEnLaFincaEntrada(BaseModel):
    correo: str


class PersonaEnLaFincaSalida(BaseModel):
    usuario_id: int
    nombre: str
    correo: str
    papel: str
    eres_tu: bool
    se_puede_quitar: bool


class QuienEntraSalida(BaseModel):
    explotacion_id: int
    nombre: str
    soy_titular: bool
    personas: list[PersonaEnLaFincaSalida]


class AyudaCampo(BaseModel):
    campo: str
    titulo: str
    que_es: str
    por_que: str
    ejemplo: str
    si_falta: str


class AvisoGeneral(BaseModel):
    tipo: str
    mensaje: str
    urgente: bool = False


# --------------------------------------------------------------------------
# Borradores: de una frase a un apunte a medio hacer
#
# ESTE ESQUEMA ES EL CONTRATO PARA UN MODELO DE LENGUAJE.
#
# Si algún día se enchufa un modelo para entender el dictado o la foto de una
# etiqueta, tiene que devolver exactamente esto. Con Outlines o Guidance se le fuerza
# el esquema durante la generación, de modo que no puede añadir texto alrededor ni
# inventarse campos; y si aun así lo hiciera, Pydantic lo rechaza aquí.
#
# Decisión: `datos` es un diccionario libre y no un `TratamientoEntrada`. El motivo es
# que un borrador está INCOMPLETO por definición: solo tiene los campos que se han
# entendido. Obligarle a tener la forma completa animaría a rellenar los huecos con
# inventos, que es justo lo que no puede pasar en un cuaderno de campo.
# --------------------------------------------------------------------------


class BorradorEntrada(EntradaBase):
    texto: str = Field(min_length=3, max_length=2000)


class EntendidoSalida(BaseModel):
    etiqueta: str
    pregunta: str
    valor: str
    campo: str | None = None
    bruto: str | None = None


class FaltaSalida(BaseModel):
    campo: str
    pregunta: str


class BorradorSalida(BaseModel):
    tipo: str
    datos: dict
    entendido: list[EntendidoSalida]
    falta: list[FaltaSalida]
    fuente: str
    titulo: str
    intro: str
    falta_intro: str
    nada_entendido: str | None = None


# --------------------------------------------------------------------------
# La firma del cuaderno
# --------------------------------------------------------------------------


class FirmaEntrada(EntradaBase):
    """Lo que devuelve AutoFirma, más a qué se refiere."""

    entidad: str = Field(min_length=1, max_length=40)
    entidad_id: int | None = None
    campana_id: int | None = None
    huella: str = Field(min_length=64, max_length=64)
    nombre_del_fichero: str | None = None
    # El fichero de firma que devuelve AutoFirma, en base64. Es opcional: si no viene,
    # queda registrado quién firmó y qué se firmó, aunque no se guarde la firma.
    contenido: str | None = Field(default=None, max_length=2_000_000)


class FirmaSalida(SalidaBase):
    id: int
    entidad: str
    entidad_id: int | None
    campana_id: int | None
    huella: str
    algoritmo: str
    formato: str
    firmante_nif: str
    firmante_nombre: str
    nombre_del_fichero: str | None
    firmado_en: dt.datetime
    # Verdadero solo cuando se ha comprobado que la firma corresponde a este cuaderno y a este
    # certificado. Falso significa «no comprobada» o «no se pudo comprobar», y en los dos casos
    # `nota_verificacion` dice por qué.
    verificada_criptograficamente: bool
    nota_verificacion: str | None = None


class FicheroParaFirmar(BaseModel):
    """Lo que hay que firmar, y con qué orden."""

    entidad: str
    entidad_id: int | None
    campana_id: int | None
    huella: str
    nombre_del_fichero: str
    comando: str
    formato: str
    algoritmo: str
    contenido: str
    explicacion: str


class EstadoFirma(BaseModel):
    estado: str
    huella: str
    puede_firmar: bool
    nombre_del_fichero: str
    firma: FirmaSalida | None = None
    mensaje: str
    explicacion: str


# --------------------------------------------------------------------------
# La documentación anexa: los papeles que acompañan al cuaderno
# --------------------------------------------------------------------------


class DocumentoEntrada(EntradaBase):
    """Un papel que sube el agricultor, con lo que hace falta para poder encontrarlo luego.

    `titulo` es obligatorio y `carpeta` no: el título es lo que se lee en la lista, y un papel
    sin nombre es un papel que no se vuelve a encontrar. La carpeta, si no se dice, va a
    «Otros», que es mejor que dejarla vacía y que aparezca suelta en la lista.
    """

    titulo: str = Field(min_length=1, max_length=200)
    tipo: str = Field(default="otros", max_length=40)
    carpeta: str = Field(default="", max_length=80)
    fecha: dt.date | None = None
    quien: str | None = Field(default=None, max_length=200)
    notas: str | None = None
    campana_id: int | None = None


class DocumentoSalida(SalidaBase):
    id: int
    campana_id: int | None
    carpeta: str
    titulo: str
    tipo: str
    # El nombre del tipo en palabras («Un contrato»), resuelto en el servidor: el catálogo vive
    # aquí, y tener dos listas acabaría con las dos diciendo cosas distintas.
    etiqueta_tipo: str
    fecha: dt.date | None
    quien: str | None
    notas: str | None
    nombre_del_fichero: str | None
    tipo_del_fichero: str | None
    bytes: int | None
    # Si el fichero se ha subido de verdad. Un papel apuntado sin fichero es un recordatorio
    # («el contrato está en el cajón»), y eso hay que poder distinguirlo.
    tiene_fichero: bool
    anulado: bool
    motivo_anulacion: str | None
    creado_en: dt.datetime


# --------------------------------------------------------------------------
# La bandeja documental (T08, S10, 06/10/2026)
# --------------------------------------------------------------------------
#
# Lo que sale por estas puertas, con una regla que se repite y conviene leer una vez: **de cada cabecera
# van las dos cosas**, el dato (`campos`, con los importes en texto decimal, que es como viaja el dinero
# en este programa) y su versión escrita (`textos`, «980,10 €»). Y no es un adorno: es lo que hace que la
# pantalla pueda **no creerse el texto**. Cuando un campo no consta, su versión escrita sale vacía y quien
# decide qué se enseña es el dato, así que un importe que no consta se enseña como hueco y nunca como
# `0,00 €`.


class VinculoDeUnPapelSalida(SalidaBase):
    """Con qué va un papel, con el nombre de lo enlazado **ya compuesto** en el servidor.

    `que_es` es lo que se lee («Un gasto · Gasóleo · 01/10/2026»): el vocabulario vive en el servidor, y
    la pantalla no compone nombres ni enseña identificadores.
    """

    id: int
    clase: str
    etiqueta_clase: str
    entidad_id: int
    que_es: str
    creado_en: dt.datetime


class LaPropuestaSalida(SalidaBase):
    """Lo que el programa ha leído. **Es una propuesta, no un dato.**

    Lo que **no** lleva, y es lo más importante: ninguna medida de la calidad de la lectura. Ni un
    porcentaje, ni una confianza, ni un «leído correctamente». El corpus para medirlo (T07) no existe.
    Lo que sí lleva son las dos cuentas que el lector puede comprobar (si cuadra la base más el IVA, y
    si las líneas suman la base) y, en cada línea, si su cuenta cuadra.
    """

    clase: str
    como_se_leyo: str
    leido_en: str
    campos: dict
    textos: dict
    lineas: list[dict]
    avisos: list[str]
    lineas_leidas: int
    lineas_que_cuadran: int
    cuadra_el_total: bool
    suman_las_lineas: bool


class LoQueSeAceptoSalida(SalidaBase):
    """Lo que el agricultor ha aceptado de esa lectura. **Todavía no está confirmado.**"""

    campos: dict
    textos: dict


class PapelDeLaBandejaSalida(SalidaBase):
    """Un papel, con todo lo que hace falta para enseñarlo y para decidir qué hacer con él.

    Los tres `se_puede_*` los decide **el servidor** y no la pantalla. Ese es el detalle que hace que el
    recorrido no se pueda saltar desde el navegador: `se_puede_confirmar` es falso mientras no haya algo
    aceptado, así que una pantalla no puede confirmar lo que el servidor no deja confirmar.
    """

    id: int
    titulo: str
    tipo: str
    etiqueta_tipo: str
    carpeta: str
    # El estado **y su palabra ya resuelta**: la pantalla no traduce claves.
    estado: str
    etiqueta_estado: str
    sin_revisar: bool
    fecha: dt.date | None
    quien: str | None
    # El original: su nombre, su tipo, sus bytes (y lo que ocupa, ya escrito) y su huella.
    tiene_fichero: bool
    nombre_del_fichero: str | None
    tipo_del_fichero: str | None
    bytes: int | None
    texto_tamano: str
    huella: str | None
    como_se_leyo: str | None
    propuesta_descartada: bool
    la_propuesta: LaPropuestaSalida | None
    lo_aceptado: LoQueSeAceptoSalida | None
    se_puede_leer: bool
    se_puede_confirmar: bool
    se_puede_descartar_la_propuesta: bool
    confirmado_en: dt.datetime | None
    confirmado_por: str | None
    # A quién rectifica este papel y quiénes lo rectifican a él: las dos cosas, porque una rectificativa
    # deja las dos versiones y hay que poder ver la cadena desde los dos lados.
    rectifica_a: dict | None
    rectificada_por: list[dict]
    vinculos: list[VinculoDeUnPapelSalida]
    clases_sugeridas: list[str]
    cuantos_candidatos: dict
    creado_en: dt.datetime


class LaBandejaSalida(SalidaBase):
    """La bandeja entera: lo que hay que revisar, y el vocabulario para preguntarlo."""

    textos: dict
    papeles: list[PapelDeLaBandejaSalida]
    cuantos: int
    sin_revisar: int
    sin_decir_de_que_es: int
    resumen: str
    tipos: list[dict]
    estados: list[dict]
    clases: list[dict]


class ElFicheroComprobadoSalida(SalidaBase):
    """Lo que se ha visto del fichero **antes de apuntarlo**: su huella y si ese papel ya estaba.

    Esta puerta **no escribe nada**, y por eso existe: es lo que permite decir el duplicado antes de que
    nada haya cambiado.
    """

    huella: str
    bytes: int
    texto_tamano: str
    nombre_del_fichero: str
    tipo_del_fichero: str
    ya_estaba: bool
    donde: str | None
    el_que_ya_estaba: dict | None
    que_hacer: str


class LosCandidatosSalida(SalidaBase):
    """Con qué se puede enlazar un papel: lo que **ya existe** en el cuaderno, con su nombre compuesto."""

    clase: str
    etiqueta_clase: str
    items: list[dict]
    cuantos: int
    truncado: bool
    sin_candidatos: str


class LoQueHaPasadoSalida(SalidaBase):
    """Lo que devuelven las puertas que cambian algo: el papel **como ha quedado**, y lo que hay que decir."""

    papel: PapelDeLaBandejaSalida
    avisos: list[str]


# El plan apunta al análisis en el que se basa, y `AnaliticaSalida` está declarada más
# abajo (va con el resto de lo de analíticas). Pydantic no resuelve solo una referencia
# que aparece después, así que se reconstruye aquí, una vez está todo el módulo leído.
# Sin esta línea, pedir un plan falla con «AnaliticaSalida is not defined».
PlanConLoAplicado.model_rebuild()


# --------------------------------------------------------------------------
# El cuaderno de la Junta (Cuecyl): leerlo y traer sus tierras
# --------------------------------------------------------------------------


class LineaDeCuadernoSalida(SalidaBase):
    """Una línea de la hoja de parcelas del cuaderno, tal y como viene en el papel.

    Es lo que se le enseña al agricultor para que reconozca sus tierras **antes** de que se
    apunten: la referencia del SIGPAC, el pueblo, lo que tiene sembrado y las hectáreas.
    """

    orden: int
    ref_sigpac: str
    municipio: str
    uso_sigpac: str
    superficie_sigpac_ha: float | None
    superficie_cultivada_ha: float | None
    especie: str
    variedad: str | None
    ecorregimen: str | None
    # secano | regadio | "" (el papel no lo dice)
    sistema: str
    # True / False / None. `None` es «en el papel no está marcado», que no es lo mismo que «no».
    zona_nitratos: bool | None


class CuadernoLeidoSalida(SalidaBase):
    """Lo que trae el cuaderno, para poder enseñarlo antes de apuntar nada."""

    anio: int | None
    titular: str
    nif: str
    registro_autonomico: str | None
    localidad: str | None
    # Los números del resumen, contados en un solo sitio (`cuaderno_cyl.CuadernoLeido.resumen`).
    resumen: dict
    lineas: list[LineaDeCuadernoSalida]


class ImportacionDelCuadernoSalida(SalidaBase):
    """Qué ha pasado al traer las tierras, contado para que se pueda comprobar a ojo."""

    anio: int
    campana_id: int
    creadas: int
    # Tierras que ya estaban apuntadas y no tenían cultivo: se les ha puesto el del cuaderno.
    con_cultivo: int
    ya_estaban: int
    # Líneas leídas que no se han podido apuntar (les falta el polígono, la parcela o el recinto).
    sin_apuntar: int
    lineas_leidas: int
    tierras_en_el_cuaderno: int
    hectareas_declaradas: float
    # Los datos del titular que se han rellenado, en palabras («nº de registro», «dirección»…).
    titular_rellenado: list[str]
    avisos: list[str]


# --------------------------------------------------------------------------
# Facturas de compra
# --------------------------------------------------------------------------


class LineaDeFacturaEntrada(EntradaBase):
    """Una línea tal y como la confirma el agricultor en la pantalla.

    Todo es opcional menos la descripción: hay líneas de factura que solo son un texto y un importe
    («reparación del remolque»), y obligar a rellenar cantidad y precio dejaría fuera media factura.
    """

    descripcion: str = Field(min_length=1, max_length=200)
    cantidad: float | None = Field(default=None, ge=0)
    unidad: str | None = None
    precio_unitario: float | None = Field(default=None, ge=0)
    importe: float | None = Field(default=None, ge=0)
    numero_registro: str | None = None
    lote: str | None = None
    # A qué está enganchada la línea: a un producto de la cesta, a un abono, o a nada.
    producto_id: int | None = None
    fertilizante_id: int | None = None
    # «No lo tengo apuntado: créalo con estos datos». Cuando viene marcado, el programa da de alta
    # el producto con lo que dice la factura (nombre, número de registro, cantidad, unidad, fecha y
    # proveedor) y deja la línea enganchada a él. Es lo que hace que traer una factura sirva para
    # algo más que para guardar el papel: el producto acaba en la cesta y se puede usar al apuntar
    # un tratamiento. Si ya existe uno con el mismo nombre o el mismo número de registro, **no se
    # crea otro**: se engancha al que hay, porque dos fichas del mismo producto descuadrarían el
    # almacén.
    crear_producto: bool = False


class FacturaEntrada(EntradaBase):
    fecha: dt.date | None = None
    proveedor: str | None = None
    proveedor_nif: str | None = None
    numero_factura: str | None = None
    base_imponible: float | None = Field(default=None, ge=0)
    cuota_iva: float | None = Field(default=None, ge=0)
    tipo_iva_pct: float | None = Field(default=None, ge=0, le=100)
    total: float | None = Field(default=None, ge=0)
    notas: str | None = None
    # De dónde salió la propuesta: pdf | escaneo | foto | a mano.
    leida_por: str | None = None
    # **El identificador único de la petición** (contrato §2), con los dos nombres que usa la casa:
    # `clave_de_reenvio` (el del contrato) e `id_local` (el de la cola del móvil, `web/nucleo.js`).
    # Se aceptan los dos porque son la misma cosa, y perder la protección contra el doble apunte por
    # un nombre distinto sería el peor motivo para perderla —es lo que hace `almacen_api._la_clave`
    # con los albaranes—.
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Factura, "clave_de_reenvio")
    )
    id_local: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Factura, "clave_de_reenvio")
    )
    lineas: list[LineaDeFacturaEntrada] = Field(default_factory=list)


class LineaDeFacturaSalida(SalidaBase):
    id: int
    descripcion: str
    cantidad: float | None
    unidad: str | None
    precio_unitario: float | None
    importe: float | None
    numero_registro: str | None
    lote: str | None
    producto_id: int | None
    fertilizante_id: int | None
    # Los nombres, resueltos en el servidor: así la pantalla no tiene que cruzar listas y no puede
    # enseñar el nombre de un producto que ya no es.
    producto: str | None = None
    fertilizante: str | None = None
    # Si la cuenta de la línea cuadra (cantidad × precio = importe). Se calcula al devolverla, no se
    # guarda: así sigue siendo verdad si el agricultor corrige un número.
    cuadra: bool | None = None


class FacturaSalida(SalidaBase):
    id: int
    campana_id: int | None
    fecha: dt.date | None
    proveedor: str | None
    proveedor_nif: str | None
    numero_factura: str | None
    base_imponible: float | None
    cuota_iva: float | None
    tipo_iva_pct: float | None
    total: float | None
    notas: str | None
    leida_por: str | None
    tiene_fichero: bool
    nombre_del_fichero: str | None
    anulada: bool
    motivo_anulacion: str | None
    creada_en: dt.datetime
    # **Si esta factura ya estaba apuntada** (09/10/2026). El contrato §2 dice que reenviar el mismo
    # comando devuelve su resultado y no crea otro movimiento, así que la respuesta tiene que poder
    # decirlo: `ya_estaba` es «no se ha apuntado otra vez» y `como_se_reconocio` es **por qué** —
    # por la clave de reenvío (reenvío técnico) o por el número de factura y el proveedor (posible
    # duplicado comercial)—. Sin esto la pantalla no puede distinguir «guardada» de «ya la tenías».
    ya_estaba: bool = False
    como_se_reconocio: str | None = None
    # Y en palabras, para que la pantalla lo pueda enseñar tal cual: por qué no se ha apuntado otra
    # vez, o por qué no se ha podido comprobar si ya estaba.
    avisos: list[str] = Field(default_factory=list)
    lineas: list[LineaDeFacturaSalida] = Field(default_factory=list)


class LineaDeFacturaLeidaSalida(SalidaBase):
    """Una línea leída del documento, antes de que el agricultor la confirme."""

    descripcion: str
    cantidad: float | None
    unidad: str
    precio_unitario: float | None
    importe: float | None
    numero_registro: str
    cuadra: bool
    confianza: str
    producto_sugerido_id: int | None
    producto_sugerido: str
    como_se_sugiere: str


class FacturaLeidaSalida(SalidaBase):
    """Lo que el programa ha entendido del documento. **Es una propuesta.**

    Se llama «...Salida» y no «FacturaLeida» a propósito: en `app/facturas.py` hay una clase
    `FacturaLeida` que es la de dentro del programa, y tener dos cosas con el mismo nombre en el
    mismo sitio es la clase de lío que acaba en un dato mal leído.
    """

    proveedor: str
    proveedor_nif: str
    numero_factura: str
    fecha: dt.date | None
    base_imponible: float | None
    cuota_iva: float | None
    tipo_iva_pct: float | None
    total: float | None
    lineas: list[LineaDeFacturaLeidaSalida]
    # Cómo se ha leído (pdf, escaneo, foto) y con qué idioma, para poder decir si las palabras con
    # tilde pueden venir cambiadas.
    como_se_leyo: str
    idioma_del_lector: str
    texto_crudo: str
    avisos: list[str]
    resumen: dict
    # Si esa misma factura ya estaba subida (misma huella del fichero), con qué id.
    ya_estaba: int | None = None


# --------------------------------------------------------------------------
# El almacén: el artículo, el lote, el albarán y el libro de movimientos (T09)
#
# Criterio general de estos esquemas, y conviene tenerlo claro al leerlos: **casi todo es opcional**.
# No es dejadez: un albarán llega con la casilla de la cantidad borrada, o sin fecha, o sin el número
# de lote, y hay que poder apuntarlo igual —lo que llegó, llegó— y decir después qué no se sabe. Lo
# que sí es obligatorio es lo que hace falta para no confundir una cosa con otra: el tipo de
# movimiento, la unidad cuando hay cantidad, y el motivo cuando no hay ningún papel detrás.
# --------------------------------------------------------------------------


class ArticuloEntrada(EntradaBase):
    """Dar de alta lo que se guarda en el almacén: un producto, un abono, una semilla, otra cosa.

    `unidad` puede quedarse vacía: es «no se sabe en qué se cuenta», y el almacén dirá que no puede
    hacer la cuenta en vez de suponer que son litros.
    """

    nombre: str = Field(min_length=1, max_length=200)
    # fitosanitario | abono | semilla | otros. Ver `servicios.CATEGORIAS_DE_ARTICULO`.
    categoria: str = "otros"
    unidad: str | None = None
    producto_id: int | None = None
    fertilizante_id: int | None = None


class ArticuloSalida(SalidaBase):
    id: int
    nombre: str
    categoria: str
    unidad: str | None
    producto_id: int | None
    fertilizante_id: int | None
    creado_en: dt.datetime


class LoteEntrada(EntradaBase):
    """Un lote suelto, sin pasar por un albarán (para un ajuste o una entrada a mano)."""

    articulo_id: int
    numero_lote: str | None = None
    fecha_caducidad: dt.date | None = None
    presentacion: str | None = None
    contenido_por_envase: float | None = Field(default=None, gt=0)
    ubicacion: str | None = None


class LoteSalida(SalidaBase):
    id: int
    articulo_id: int
    numero_lote: str | None
    fecha_caducidad: dt.date | None
    presentacion: str | None
    contenido_por_envase: float | None
    ubicacion: str | None
    creado_en: dt.datetime


class LineaDeRecepcionEntrada(EntradaBase):
    """Una línea del albarán, tal y como la teclea o la confirma el agricultor.

    El artículo se puede decir de cuatro formas, y todas valen porque todas aparecen en la vida real:

      · `articulo_id` — ya está dado de alta en el almacén.
      · `producto_id` / `fertilizante_id` — el albarán trae un producto de la cesta o un abono, y el
        artículo se engancha a su ficha (o se crea enganchado a ella). Es lo que hace que el almacén
        hable de lo mismo que el resto del programa.
      · `nombre` — lo que pone el papel, para darlo de alta por primera vez.

    Lo que **no** se inventa: si no viene ninguna de las cuatro cosas, la línea no se puede apuntar y
    el programa lo dice.
    """

    articulo_id: int | None = None
    nombre: str | None = None
    categoria: str | None = None
    unidad: str | None = None
    producto_id: int | None = None
    fertilizante_id: int | None = None

    descripcion: str | None = None
    # Vacías son «no se sabe cuánto venía» y «no se sabe en qué se mide»: la línea se apunta igual.
    cantidad: float | None = Field(default=None, ge=0)
    unidad_de_la_cantidad: str | None = None

    numero_lote: str | None = None
    fecha_caducidad: dt.date | None = None
    presentacion: str | None = None
    contenido_por_envase: float | None = Field(default=None, gt=0)
    ubicacion: str | None = None
    # El enganche con la línea de la factura, cuando se conoce (ver `models.LineaDeRecepcion`).
    linea_factura_id: int | None = None


class RecepcionEntrada(EntradaBase):
    """El albarán que llega: la cabecera y sus líneas.

    Todo puede faltar menos las líneas: un albarán sin número, sin fecha o sin proveedor se apunta
    igual (llegó mercancía, y eso es un hecho), y lo que entonces no se puede comprobar —si ese
    albarán ya estaba dentro— se dice en la respuesta en vez de darse por bueno.
    """

    fecha: dt.date | None = None
    proveedor: str | None = None
    proveedor_nif: str | None = None
    numero_albaran: str | None = None
    notas: str | None = None
    # La factura, si la factura llega **antes** o a la vez que el albarán. Si llega después, se
    # engancha por su propia puerta (`POST /api/almacen/recepciones/{id}/factura`) y, en los dos
    # casos, **no se apunta ninguna cantidad por ella** (A15).
    factura_id: int | None = None
    lineas: list[LineaDeRecepcionEntrada] = Field(default_factory=list)

    # El identificador único de la petición. Es lo que hace que reenviar el mismo albarán devuelva
    # el mismo resultado en vez de crear otro: el contrato lo pide para todo comando de negocio, y
    # en el campo es la única defensa que hay contra la cola del móvil, que reintenta sin preguntar.
    clave_de_reenvio: str | None = None
    # El nombre que tiene ese identificador en la cola del móvil (`web/nucleo.js`: `id_local`). Se
    # acepta con los dos nombres a propósito: así la pantalla que lo mande no tiene que traducirlo, y
    # el día que se mande con el nombre del móvil tampoco se pierde la protección.
    id_local: str | None = None


class EnlaceDeLineaEntrada(EntradaBase):
    """Confirmar que esa línea del albarán es esa línea de la factura.

    Es el caso en que los dos papeles no cuadran del todo (una línea del albarán se facturó en dos,
    o al revés), que el contrato prevé: «factura y recepción pueden relacionarse parcialmente por
    líneas». Nada de esto mueve una cantidad: solo dice qué línea es cuál.
    """

    linea_de_recepcion_id: int
    linea_de_factura_id: int


class EnlazarLaFacturaEntrada(EntradaBase):
    """Decir de qué factura es un albarán que **ya está apuntado** (caso A15).

    **No lleva ninguna cantidad, y es a propósito.** La mercancía entró una vez, con el albarán; la
    factura solo dice de dónde salió y cuánto costó. Si este esquema aceptara cantidades, alguien
    acabaría metiéndolas por aquí y el almacén contaría la misma compra dos veces, que es el fallo
    que este ticket tenía que impedir.
    """

    factura_id: int
    # Lo que el agricultor confirma línea a línea, si las quiere casar. Vacío es «con el documento
    # entero me vale», que es lo normal.
    lineas: list[EnlaceDeLineaEntrada] = Field(default_factory=list)


class LineaDeRecepcionSalida(SalidaBase):
    id: int
    articulo_id: int
    lote_id: int
    descripcion: str | None
    cantidad: float | None
    unidad: str | None
    linea_factura_id: int | None
    # Los nombres resueltos en el servidor, como en las facturas: así la pantalla no cruza listas.
    articulo: str | None = None
    numero_lote: str | None = None
    fecha_caducidad: dt.date | None = None


class RecepcionSalida(SalidaBase):
    id: int
    fecha: dt.date | None
    proveedor: str | None
    proveedor_nif: str | None
    numero_albaran: str | None
    factura_id: int | None
    notas: str | None
    anulada: bool
    motivo_anulacion: str | None
    creada_en: dt.datetime
    lineas: list[LineaDeRecepcionSalida] = Field(default_factory=list)
    # Cuántas entradas ha metido en el libro. Cero en una recepción anulada.
    entradas: int = 0


class MovimientoEntrada(EntradaBase):
    """Apuntar a mano lo que pasó en el almacén: una entrada sin papel, una merma o un ajuste.

    El tipo y el motivo van juntos y no por capricho: una **merma** (un envase roto, lo que se
    estropea) y un **ajuste** (lo que sale al contar) no tienen ningún documento detrás, así que lo
    único que los explica es lo que escriba el agricultor. Y una entrada sin compra apuntada, igual.

    En un ajuste, `cantidad` es **la diferencia**: positiva si al contar había más de lo que dice el
    libro, negativa si había menos.
    """

    # entrada | merma | ajuste. Una salida de verdad se apunta con la puerta de las salidas, que
    # exige decir de qué apunte sale: así no se puede restar producto «porque sí».
    tipo: str
    articulo_id: int | None = None
    # El lote: o se dice cuál (`lote_id`), o se dice de qué artículo y con qué número, y se busca o
    # se crea. Un movimiento siempre acaba en un lote (ver `models.Lote`).
    lote_id: int | None = None
    numero_lote: str | None = None
    fecha_caducidad: dt.date | None = None
    presentacion: str | None = None
    contenido_por_envase: float | None = Field(default=None, gt=0)
    ubicacion: str | None = None

    fecha: dt.date | None = None
    cantidad: float | None = None
    unidad: str | None = None
    motivo: str | None = Field(default=None, max_length=500)
    # De dónde viene: `factura` (una compra sin albarán en la mano) o `manual` (nada). Y, cuando
    # viene de una factura, también su línea, si se sabe.
    origen_tipo: str | None = None
    origen_id: int | None = None
    linea_factura_id: int | None = None
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class SalidaDeAlmacenEntrada(EntradaBase):
    """Gastar de un lote, atado al apunte que lo gastó (un tratamiento o un abono).

    **Es la única forma de sacar producto del almacén con un apunte detrás**, y por eso el
    identificador del apunte es obligatorio: un consumo sin saber de qué tratamiento sale no se puede
    comprobar ni revertir cuando el apunte se anule.

    `cantidad` y `unidad` son opcionales a propósito: normalmente **el total lo dice el apunte**
    (`cantidad_total`, o los kilos del abono), y volver a teclearlo es la forma de que un día digan
    cosas distintas. Cuando no se mandan, se copian del apunte. Cuando el apunte no dice el total
    —solo la dosis por hectárea—, el programa **no lo multiplica por su cuenta**: pide el total, que
    es justo la confusión de diez veces que hay que evitar.

    `aceptar_descuadre` es la salida que tiene el agricultor cuando lo que sale es más de lo que el
    libro dice que hay: sin él se avisa y no se apunta; con él se apunta y queda marcado. Lo que no
    se hace nunca es apuntarlo en silencio ni impedirle registrar lo que de verdad pasó.
    """

    apunte_tipo: str
    apunte_id: int
    lote_id: int
    cantidad: float | None = Field(default=None, gt=0)
    unidad: str | None = None
    fecha: dt.date | None = None
    motivo: str | None = Field(default=None, max_length=500)
    aceptar_descuadre: bool = False
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class MovimientoSalida(SalidaBase):
    id: int
    articulo_id: int
    lote_id: int
    tipo: str
    fecha: dt.date | None
    cantidad: float | None
    unidad: str | None
    origen_tipo: str
    origen_id: int | None
    motivo: str | None
    usuario_id: int | None
    anulado: bool
    motivo_anulacion: str | None
    creado_en: dt.datetime
    # Los nombres resueltos en el servidor (el artículo y el número del lote), para que la pantalla no
    # tenga que cruzar listas ni enseñar un identificador.
    articulo: str | None = None
    numero_lote: str | None = None
    # **Si este movimiento cuenta o no**, y por qué. Un movimiento deja de contar cuando él mismo
    # está anulado o cuando lo está el apunte del que sale (un tratamiento anulado no gastó nada).
    # Va en el dato y no en un comentario: es lo que permite explicar una resta que no cuadra a ojo.
    cuenta: bool = True
    no_cuenta_porque: str | None = None


# --------------------------------------------------------------------------
# La semilla y la siembra (T10, 03/10/2026)
# --------------------------------------------------------------------------


class SemillaEntrada(EntradaBase):
    """Lo que pone la etiqueta de una semilla, tal y como lo confirma el agricultor.

    **Este esquema es la confirmación.** La lectura de una foto (`POST /api/semillas/etiqueta`) no
    guarda nada y devuelve una propuesta; una semilla existe cuando llega por aquí, que es cuando el
    agricultor ha dicho que sí a lo que se le enseñó. Por eso no hay ningún campo de «pendiente de
    confirmar»: lo que no se ha confirmado no está.

    Todo puede faltar menos el nombre del artículo: una semilla guardada de un año para otro puede
    haber perdido el papel, y eso no impide apuntarla. **Lo que no se hace es rellenar un hueco**:
    `poder_germinativo_pct` vacío es «la etiqueta no lo dice», y `tratada` tiene tres respuestas
    (`True`, `False` y `None` = «no lo sé»).
    """

    nombre: str | None = Field(default=None, max_length=200)
    # **O el artículo ya está en el almacén, o se da de alta ahora.** Las dos cosas pasan de verdad y
    # en las dos direcciones: hay quien compra la semilla y le hace la foto a la etiqueta al llegar a
    # casa (y entonces el artículo no existe todavía), y hay quien primero apunta el albarán y después
    # mira la etiqueta (y entonces el artículo ya está, con su entrada y su lote). Sin esto, la
    # etiqueta de una semilla que ya entró crearía **un segundo artículo con el mismo nombre**, que es
    # justo lo que no puede pasar en un almacén.
    articulo_id: int | None = None
    # En qué se cuenta esta semilla en el almacén (kg, g, ud, L). Vacío es «no se sabe en qué se
    # cuenta», y entonces el almacén dice que no puede hacer la cuenta en vez de suponer.
    unidad: str | None = None

    especie: str | None = None
    variedad: str | None = None
    casa_comercial: str | None = None
    proveedor: str | None = None
    numero_lote_proveedor: str | None = None

    # La dosis que recomienda el fabricante, **con su unidad**. No es lo que el agricultor siembra:
    # eso va en cada siembra.
    dosis_recomendada_por_ha: float | None = Field(default=None, ge=0)
    unidad_dosis: str | None = None

    fecha_envasado: dt.date | None = None
    fecha_caducidad: dt.date | None = None

    poder_germinativo_pct: float | None = Field(default=None, ge=0, le=100)
    pureza_pct: float | None = Field(default=None, ge=0, le=100)
    tratada: bool | None = None
    # **La categoria de la semilla** (CRM-07 #2, 14/10/2026): base, certificada, R1, R2… Ojo:
    # `categoria` (en la SALIDA) es la del ARTICULO, no esta. El catalogo es
    # `catalogos.CATEGORIAS_DE_SEMILLA`, que es quien la valida en la puerta, y **no hay valor por
    # defecto**: la ausencia es «No consta» (`None`), **no** «no certificada» — no haber registrado
    # la etiqueta no demuestra que el lote no este certificado.
    categoria_semilla: str | None = None
    # Y **de donde salio**: comprada o guardada de la cosecha propia.
    procedencia: str | None = None

    # De dónde salieron los datos. `mano` es «los ha escrito una persona», que es lo que es una ficha
    # tecleada; los demás los pone el servidor al leer una etiqueta y **no se aceptan de fuera** para
    # nada que no sea decir la verdad de cómo se rellenó esto.
    leida_de: str | None = None
    idioma_del_lector: str | None = None


class SemillaSalida(SalidaBase):
    id: int
    articulo_id: int
    nombre: str
    unidad: str | None
    categoria: str
    especie: str | None
    variedad: str | None
    casa_comercial: str | None
    proveedor: str | None
    numero_lote_proveedor: str | None
    dosis_recomendada_por_ha: float | None
    unidad_dosis: str | None
    fecha_envasado: dt.date | None
    fecha_caducidad: dt.date | None
    poder_germinativo_pct: float | None
    pureza_pct: float | None
    tratada: bool | None
    categoria_semilla: str | None
    procedencia: str | None
    leida_de: str
    idioma_del_lector: str | None
    tiene_foto: bool = False
    creada_en: dt.datetime
    # **Lo que queda, contado por el servidor.** `saldo` es `None` cuando no se puede saber (falta la
    # cantidad de una entrada, o hay unidades que no se pueden comparar) y entonces viene el motivo:
    # nunca un cero, que diría que no queda nada.
    queda: dict | None = None
    # Los envases de los que puede salir lo que se siembre, para poder elegir de dónde se descuenta.
    envases: list[dict] = Field(default_factory=list)
    # Las siembras de esta semilla, contadas (para poder decir «dónde la has sembrado»).
    siembras: int = 0


class EtiquetaLeidaSalida(BaseModel):
    """Lo que se ha leído de la foto de una etiqueta. **Es una propuesta, no un dato.**

    Cada campo vacío es «no lo he leído», y así se queda. `campos_leidos` dice **qué** se ha podido
    leer de verdad, `como_se_leyo` y `idioma_del_lector` dicen **con qué**, y `dudas` lleva lo que el
    papel sí dice pero no se puede apuntar tal cual (una caducidad de mes y año, una dosis sin decir
    si es por hectárea). `texto_crudo` va para que el agricultor pueda comprobarlo él mismo.
    """

    nombre: str = ""
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
    tratada: bool | None = None

    campos_leidos: list[str] = Field(default_factory=list)
    como_se_leyo: str = ""
    idioma_del_lector: str = ""
    hay_lector: bool = True
    texto_crudo: str = ""
    avisos: list[str] = Field(default_factory=list)
    dudas: list[str] = Field(default_factory=list)
    # Si no se ha podido leer nada, la pantalla ofrece escribirlo a mano. Y **nada de esto se ha
    # guardado**: se dice en el dato, no en un comentario.
    guardado: bool = False


class SiembraEntrada(EntradaBase):
    """«En esta tierra sembré esta semilla», con la dosis **y** la cantidad total.

    Las tres cifras son opcionales y **ninguna se inventa**:

      · `dosis_por_ha` — cuánto se siembra en cada hectárea, con su unidad.
      · `cantidad_total` — cuánto se ha gastado en la tierra entera, con su unidad.
      · `superficie_ha` — cuántas hectáreas se han sembrado.

    Si falta una de las dos primeras y hay superficie, el servidor **la calcula y lo dice**
    (`dosis_calculada` / `cantidad_total_calculada` en la respuesta). Si no se puede calcular, se
    queda vacía y se pide: un cero sería «no sembré nada».

    `lote_id` es de qué envase sale. Sin él **no se descuenta nada del almacén** y se dice por qué:
    restarlo de un envase cualquiera sería inventarse de dónde salió.
    """

    semilla_id: int
    parcela_id: int
    lote_id: int | None = None
    fecha: dt.date | None = None

    superficie_ha: float | None = Field(default=None, gt=0)
    dosis_por_ha: float | None = Field(default=None, ge=0)
    unidad_dosis: str | None = None
    cantidad_total: float | None = Field(default=None, ge=0)
    unidad_cantidad: str | None = None

    notas: str | None = Field(default=None, max_length=500)
    # Lo que sale del envase deja el lote en negativo (más de lo que el libro dice que hay). Sin esto
    # se avisa y no se apunta nada; con esto se apunta y queda marcado, que es lo que hace que el
    # agricultor pueda registrar lo que de verdad pasó (ver `SalidaDeAlmacenEntrada.aceptar_descuadre`).
    aceptar_descuadre: bool = False
    # La marca de la petición: es lo que hace que reenviar la misma siembra (el móvil sin cobertura,
    # un botón pulsado dos veces) **no descuente dos veces** del almacén.
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class SiembraSalida(SalidaBase):
    id: int
    semilla_id: int
    parcela_id: int
    lote_id: int | None
    fecha: dt.date | None
    superficie_ha: float | None
    dosis_por_ha: float | None
    unidad_dosis: str | None
    cantidad_total: float | None
    unidad_cantidad: str | None
    # «Este número lo ha calculado el programa»: el agricultor tiene que poder revisarlo.
    dosis_calculada: bool = False
    cantidad_total_calculada: bool = False
    notas: str | None
    anulada: bool
    motivo_anulacion: str | None
    creada_en: dt.datetime
    # Los nombres resueltos en el servidor: la semilla, la tierra y el envase, para que la pantalla no
    # cruce listas.
    semilla: str | None = None
    tierra: str | None = None
    numero_lote: str | None = None
    # **Si esta siembra ha descontado del almacén o no, y por qué.** Es lo que permite explicar por
    # qué la semilla que queda no ha bajado sin que nadie se entere.
    descuenta: bool = False
    no_descuenta_porque: str | None = None
    movimiento_id: int | None = None
    avisos: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# La versión del recinto y la importación de un lote (T05, 02/10/2026)
# --------------------------------------------------------------------------


class RecintoDelLote(EntradaBase):
    """Un recinto, tal y como lo cuenta la fuente que lo manda.

    **Todo es opcional menos tener algo con lo que identificarlo**, y eso es una decisión: lo que
    llega de fuera viene como viene. Un recinto del papel puede traer la referencia a medias, o no
    traer la forma, o no traer la superficie, y **eso no lo invalida**: entra igual y se dice qué
    falta. Lo que no se hace es rellenar un hueco con un valor parecido.

    La referencia se puede mandar de las tres formas que existen en el visor y en el papel (los
    siete números, los seis del visor, o la referencia catastral) en `referencia`, o número a
    número en sus campos. Si vienen las dos cosas, mandan los números sueltos: son los que ha
    leído quien mira el papel.
    """

    # "37-70-0-0-503-51-1", "37:70:0:0:503:51" o "37070A50300051000AQ". Se lee con el mismo lector
    # que usa el mapa (`sigpac.lee_busqueda`), para no tener dos formas de entender lo mismo.
    referencia: str | None = None
    provincia: str | None = None
    municipio: str | None = None
    agregado: int | None = None
    zona: int | None = None
    poligono: int | None = None
    numero_parcela: int | None = None
    numero_recinto: int | None = None
    # La tierra a la que pertenece, si ya se sabe. Si no viene, se busca por la referencia y, si no
    # existe, se da de alta la tierra (con el alias de aquí abajo, o con el que salga de la
    # referencia). **Nunca se duplica** una tierra que ya tiene esa misma referencia.
    parcela_id: int | None = None
    alias: str | None = None
    # WKT, como lo manda el SIGPAC. Vacío = recinto sin forma, que es una cosa de verdad.
    geometria: str | None = None
    # Las dos áreas que puede decir la fuente. **Ninguna se calcula desde la forma**: la de la forma
    # la calcula el programa (`geo.area_ha`) y va en su propio campo.
    area_sigpac_ha: float | None = Field(default=None, ge=0)
    area_declarada_ha: float | None = Field(default=None, ge=0)
    uso_sigpac: str | None = None
    pendiente_pct: float | None = None
    estado_revision: str | None = None


class LoQueDijoElAgricultor(EntradaBase):
    """**La forma de una tierra, dicha por el agricultor** (CRM-06, 14/10/2026).

    No es una consulta a ninguna fuente: es lo que el agricultor dice que es su tierra. Por eso el lote que se
    construye con esto lleva `fuente="agricultor"` y **`fecha_consulta` en blanco** — que es lo que manda el
    propio `LoteDeRecintosEntrada`: *poner la fecha de hoy afirmaría una consulta que quizá se hizo en marzo*.

    Y la `geometria` es obligatoria: esta puerta existe **para darle forma a una tierra que no la tiene**, así
    que sin forma no hay nada que hacer. *Un polígono no se inventa* (regla del módulo de versiones).
    """

    geometria: str
    campana_id: int | None = None

class LoteDeRecintosEntrada(EntradaBase):
    """Un lote de recintos de una campaña y de una fuente: lo que se importa de una vez.

    La campaña se puede decir por su identificador (`campana_id`) o por su año (`anio`); hace falta
    una de las dos. `fecha_consulta` es cuándo se consultó la fuente: **si no se dice, se queda en
    blanco**, porque poner la fecha de hoy afirmaría una consulta que quizá se hizo en marzo.
    """

    campana_id: int | None = None
    anio: int | None = None
    # sigpac | cuaderno_de_la_junta | agricultor | medicion_en_campo
    fuente: str
    fecha_consulta: dt.date | None = None
    recintos: list[RecintoDelLote] = Field(min_length=1)
    # La clave de reenvío del móvil (lo que manda la cola cuando apunta sin cobertura). Se acepta
    # para que reenviar el mismo lote no haga nada raro; el trabajo de verdad lo hace la unicidad
    # de (tierra, campaña, fuente, recinto), que no depende de que el cliente se acuerde de nada.
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class VersionDeRecintoSalida(SalidaBase):
    """Una versión del recinto, con lo que hace falta para leerla en una pantalla.

    Los nombres ya resueltos (`tierra`, `anio`, `fuente_texto`, `estado_texto`) van en la respuesta
    porque la pantalla no tiene que cruzar listas ni traducir códigos: es la misma decisión que en
    las facturas y en el almacén.
    """

    id: int
    parcela_id: int
    tierra: str | None = None
    campana_id: int
    anio: int | None = None
    fuente: str
    fuente_texto: str
    fecha_consulta: dt.date | None
    clave: str
    referencia: str | None
    provincia: str | None
    municipio: str | None
    agregado: int | None
    zona: int | None
    poligono: int | None
    numero_parcela: int | None
    numero_recinto: int | None
    poligono_valido: bool
    geometria: str | None
    # ¿Tiene forma? Es lo que pone el recinto en el grupo «sin forma» de la tabla (contrato §2.1).
    tiene_forma: bool
    # **Las tres áreas, cada una con su nombre y ninguna deducida de otra.** Cualquiera de las tres
    # puede venir vacía («no se sabe»), y vacía no es cero.
    area_geometria_ha: float | None
    area_sigpac_ha: float | None
    area_declarada_ha: float | None
    uso_sigpac: str | None
    pendiente_pct: float | None
    estado_revision: str
    estado_texto: str
    # La frase que dice cómo está esta versión de un vistazo, ya escrita: «Sin forma, no ha venido
    # el polígono», «Sin revisar»… Sale de `textos.py` como todo lo que lee el agricultor.
    como_esta: str
    creada_en: dt.datetime


class RecintoEnElPlan(SalidaBase):
    """Qué le va a pasar (o qué le ha pasado) a un recinto del lote.

    `estado` es `nuevo`, `cambiado` o `igual`. **`sin_forma` va aparte a propósito**: es un hecho
    del recinto, no un estado de la importación —un recinto puede ser nuevo *y* no tener forma—, y
    mezclarlos haría que la cuenta de «sin forma» no cuadrara con nada.
    """

    clave: str
    estado: str
    estado_texto: str
    parcela_id: int | None = None
    tierra: str | None = None
    referencia: str | None = None
    poligono_valido: bool
    sin_forma: bool
    # Qué cambia, ya escrito y en castellano («la forma del trozo», «las hectáreas que declaras»).
    que_cambia: list[str] = []
    area_geometria_ha: float | None = None
    area_sigpac_ha: float | None = None
    area_declarada_ha: float | None = None


class SolapeEntreRecintos(SalidaBase):
    """Dos recintos que se pisan, con lo que se ha podido comprobar y lo que no.

    `como` es `si` (un vértice de uno cae dentro del otro: hay solape seguro) o `puede` (los
    rectángulos se tocan pero ningún vértice cae dentro: hay que mirarlo). **No se corrige nada**:
    el contrato pide detectarlo y decirlo.
    """

    clave_a: str
    clave_b: str
    referencia_a: str | None = None
    referencia_b: str | None = None
    como: str
    como_texto: str


class DiferenciaDeSuperficie(SalidaBase):
    """Las cuentas de superficie de un recinto que no cuadran entre sí.

    Las tres magnitudes son distintas por definición (la forma que vino, lo que dice el SIGPAC y lo
    que el agricultor declara), así que una diferencia **no es un error**: es un aviso para mirarlo.
    """

    clave: str
    referencia: str | None = None
    area_geometria_ha: float | None = None
    area_sigpac_ha: float | None = None
    area_declarada_ha: float | None = None
    # La diferencia mayor, en hectáreas, entre las magnitudes que se conocen. Vacía si solo se
    # conoce una (con una sola cifra no hay nada que comparar).
    diferencia_ha: float | None = None
    porcentaje: float | None = None
    aviso: bool = False
    texto: str


class PlanDeImportacion(SalidaBase):
    """Lo que pasaría al importar el lote… y lo que ha pasado, si se ha aplicado.

    Es el mismo objeto para las dos cosas a propósito: la previsualización es el plan con
    `aplicada` en falso, y así lo que el agricultor ve antes de aplicar **no puede** decir una cosa
    distinta de lo que pasa después. Los cuatro números que pide el contrato son `nuevos`,
    `cambiados`, `iguales` y `sin_forma`; los tres primeros suman los recintos del lote y el cuarto
    los cuenta aparte (los que no traen polígono).
    """

    campana_id: int
    anio: int | None = None
    fuente: str
    fuente_texto: str
    recintos_en_el_lote: int
    nuevos: int
    cambiados: int
    iguales: int
    sin_forma: int
    tierras_nuevas: int
    detalle: list[RecintoEnElPlan] = []
    solapes: list[SolapeEntreRecintos] = []
    diferencias_de_superficie: list[DiferenciaDeSuperficie] = []
    # Lo que no se ha podido tener en cuenta, dicho en castellano y sin inventar nada. Una lista
    # vacía es «no ha habido ningún problema», que es distinto de «no se ha mirado».
    problemas: list[str] = []
    # Falso mientras es solo una previsualización: **previsualizar no escribe nada**.
    aplicada: bool = False
    versiones_creadas: int = 0
    versiones_actualizadas: int = 0
    tierras_creadas: list[int] = []


class CambioDeUnRecinto(SalidaBase):
    """Un recinto comparado entre dos campañas (o entre dos importaciones)."""

    clave: str
    parcela_id: int | None = None
    tierra: str | None = None
    fuente: str
    fuente_texto: str
    estado: str
    estado_texto: str
    referencia: str | None = None
    # Qué cambió, ya escrito: «la forma del trozo», «la superficie del SIGPAC»… Vacío cuando el
    # recinto está igual (y entonces no hay nada que explicar).
    que_cambio: list[str] = []
    antes: VersionDeRecintoSalida | None = None
    despues: VersionDeRecintoSalida | None = None


class ComparacionDeVersiones(SalidaBase):
    """`igual / cambiado / desaparecido / nuevo`, con el porqué y los cuatro totales.

    **Comparar no escribe nada**: se puede pedir tantas veces como haga falta antes de decidir.
    """

    parcela_id: int | None = None
    tierra: str | None = None
    campana_antes: int
    anio_antes: int | None = None
    campana_despues: int
    anio_despues: int | None = None
    # La fuente comparada, o vacío cuando se comparan todas por separado (el SIGPAC con el SIGPAC,
    # lo que dijo el agricultor con lo que dijo el agricultor).
    fuente: str | None = None
    iguales: int
    cambiados: int
    desaparecidos: int
    nuevos: int
    cambios: list[CambioDeUnRecinto] = []
    resumen: str


# --------------------------------------------------------------------------
# Las tierras de la finca, en el mapa y en la tabla (T06, 03/10/2026)
# --------------------------------------------------------------------------
#
# **Por qué esto es un esquema y no un `dict` suelto.** Porque la pantalla que lo lee es la más
# ancha de la aplicación (una tabla de 64 filas con siete columnas y un mapa al lado) y porque el
# contrato de T06 prohíbe inventarse cifras: si un número no está aquí, no se puede enseñar. Con el
# esquema, un campo que falte revienta en los tests en vez de salir en blanco delante del agricultor.
#
# **La regla que más importa aquí:** `superficie_ha` y las tres áreas de una versión son
# `float | None`, y `None` quiere decir **«no se sabe»**, nunca cero. La `superficie_conocida_ha` que
# no está en esta respuesta es a propósito: el programa no suma hectáreas que no conoce, y un total
# calculado en la pantalla sería una cifra que el servidor no ha dado (`docs/T02_VALORES_POR_DEFECTO.md`).


class OpcionDeUnFiltro(SalidaBase):
    """Una opción de un filtro, con **cuántas tierras caen en ella**.

    El recuento lo hace el servidor sobre todas las tierras de la finca. Que lo haga él y no la
    pantalla es lo que hace que el número sea el mismo se tenga el filtro que se tenga puesto: un
    recuento hecho en el navegador sobre las filas que se ven cambiaría al escribir en el buscador.
    """

    valor: str
    texto: str
    cuantas: int


class TierraEnLaVista(SalidaBase):
    """Una tierra, con lo que hace falta para ponerla en la tabla **y** para dibujarla en el mapa.

    `numero` es el número con el que el agricultor la llama («Tierra n.º 12»): su posición en la
    lista entera, ordenada por nombre, y **no cambia al filtrar ni al ordenar**.

    `puntos` son los vértices **de verdad** de su forma, en `[longitud, latitud]`. Vienen vacíos
    cuando la tierra no tiene forma apuntada, y entonces no se dibuja: lo que no se ha medido no se
    inventa. `forma` es el mismo dibujo de siempre (el que usan la tarjeta y el panel), que es para
    el hueco pequeño de una ficha y no para el mapa.
    """

    id: int
    numero: int
    alias: str
    referencia: str | None
    provincia: str
    municipio: str
    # A10: `None` es «no lo sé». La ficha de la tierra no puede inventarse el sistema.
    sistema: str | None
    # «No se sabe» es `None`, y `None` no es cero.
    superficie_ha: float | None
    superficie_sigpac_ha: float | None
    tiene_forma: bool
    forma: str | None
    # Los anillos **de verdad** de su forma, en `[longitud, latitud]`: uno por cada trozo de una
    # geometría multiparte y uno por cada agujero. Se mandan los anillos separados y no una lista
    # plana de puntos porque un `MULTIPOLYGON` unido en una sola lista dibujaría una raya de un trozo
    # al otro, que es una forma que nadie ha medido.
    anillos: list[list[list[float]]] = []
    # Lo que hay sembrado este año, ya escrito («Trigo · secano»), o vacío si no se ha dicho.
    cultivo: str
    # La especie a secas, que es por lo que filtra el filtro de lo sembrado. Se manda aparte del
    # texto de arriba porque el texto lleva la variedad y el secano o regadío, y filtrar por un
    # texto compuesto haría que dos tierras con el mismo trigo cayeran en filtros distintos.
    cultivo_clave: str
    # El estado de revisión de la versión más nueva de **esta campaña**, o `None` si esta tierra no
    # tiene ninguna versión de este año. Es lo que filtra el filtro de la revisión.
    estado_revision: str | None
    estado_revision_texto: str | None
    anio_de_la_version: int | None
    fuente_texto: str | None
    # Los tres hechos que miran los filtros de la PAC y de las hectáreas. Ninguno afirma nada: el
    # primero dice que están los tres números del recinto (polígono, parcela y recinto) y el segundo,
    # que **se sabe la superficie de esta tierra**. **No se dice «cumple» ni «está declarada»**,
    # porque eso no lo sabe este programa.
    #
    # **«Hectáreas dichas» es la superficie de la tierra (`superficie_ha`), y esa es la regla que
    # usan a la vez la columna de la tabla, el pie y el filtro.** Antes contaba también el área
    # declarada de la versión del año, y la revisión de T06 encontró lo que eso producía: una tierra
    # importada del cuaderno de la Junta **sin superficie** pero con hectáreas declaradas en su
    # versión salía en la tabla diciendo «Sin hectáreas dichas» mientras el pie decía que no había
    # ninguna así y el filtro no ofrecía esa opción. Dos cosas que no pueden ser verdad a la vez. Lo
    # que el agricultor declara ese año sigue teniendo su sitio, con su nombre, en la ficha de la
    # tierra (`area_declarada_ha`, «Las hectáreas que declaras»), que es donde las tres magnitudes
    # —la forma, el SIGPAC y lo declarado— van separadas a propósito.
    tiene_referencia_completa: bool
    area_declarada_ha: float | None
    tiene_hectareas_dichas: bool
    # **Con qué recinto del SIGPAC habla esta tierra**, ya normalizado (sin mayúsculas de sobra y sin
    # espacios de más). Con los datos de verdad esto no es un detalle: 65 tierras tienen solo **52
    # referencias distintas**, porque el cuaderno de la Junta parte un mismo recinto en varias líneas
    # de cultivo. Dos tierras con la misma clave **son el mismo trozo de tierra**, así que comparten
    # polígono; la pantalla lo dice y enciende las dos en vez de elegir una al azar.
    #
    # Se calcula en el servidor (y no en la pantalla) para que haya **una sola** forma de decidir si
    # dos tierras son el mismo recinto, y es la misma idea que `versiones_de_recinto.clave_del_recinto`:
    # la referencia si la hay, y si no la huella de la forma. Una tierra sin referencia y sin forma se
    # queda con su propia clave (`tierra:<id>`), porque de ella no se puede decir que comparta nada.
    clave_recinto: str
    # **Cuántas tierras de la finca se llaman igual que esta.** Con los datos de verdad, 65 tierras
    # tienen solo 60 nombres distintos: hay dos que se llaman `507/24-1 TRIGO BLANDO (0.46 ha)` y
    # tienen hasta la misma superficie. El programa **no renombra nada** (el nombre es del
    # agricultor), pero sí dice que el nombre está repetido, que es lo que le hace mirar el número de
    # la tierra y la referencia para saber cuál está eligiendo.
    cuantas_con_el_mismo_nombre: int


class TotalesDeLasTierras(SalidaBase):
    """Los recuentos de la finca entera, calculados en el servidor.

    Son los que sostienen el pie de la tabla («Ves 10 de 64 tierras»). Se calculan sobre **todas**
    las tierras, así que siguen diciendo lo mismo con un filtro puesto, que es justo lo que hace
    falta para que el agricultor sepa cuántas se está dejando fuera.
    """

    tierras: int
    con_forma: int
    sin_forma: int
    sin_cultivo: int
    sin_hectareas: int
    sin_revision: int


class CajaDelMapa(SalidaBase):
    """El rectángulo, en coordenadas de verdad, que envuelve todas las formas de la finca."""

    oeste: float
    sur: float
    este: float
    norte: float


class ElMapaDeLaFinca(SalidaBase):
    """Por dónde se puede abrir el mapa, y por dónde **no**.

    `hay_forma` es falso cuando ninguna tierra de la finca tiene forma apuntada. En ese caso `caja`
    va vacía **a propósito**: el mapa no se abre en un sitio cualquiera ni se dibuja un cuadro en
    medio de Castilla y León. La pantalla lo dice y ofrece la tabla, que funciona igual.
    """

    hay_forma: bool
    tierras_con_forma: int
    caja: CajaDelMapa | None = None
    # **¿Cabe toda la finca en una imagen del mapa?** El servicio oficial no da una caja de más de
    # `mapa.LADO_MAXIMO_GRADOS` (medio grado, unos 55 km), así que una finca repartida en más que eso
    # **no se puede enseñar entera**. Se dice aquí para que la pantalla se abra mirando una parte en
    # vez de pedir una imagen que el propio programa rechaza: el agricultor leería «puede ser la
    # cobertura» delante de un fallo que no tiene nada que ver con la cobertura (revisión de T06, D7).
    #
    # **Y `tierras_con_forma` cuenta lo mismo que `totales.con_forma`.** Se descubrió que no era así
    # (revisión de T06, D2: un recinto con la geometría escrita pero sin anillos que se puedan dibujar
    # salía contado en el mapa y no en la tabla, **en la misma respuesta**), y ahora los dos se cuentan
    # con el mismo dato: los anillos que de verdad se pueden dibujar.
    se_puede_ensenar_entera: bool = True
    # **Cuánto ocupan de verdad todas las formas**, sin recortar. Cuando la finca no cabe en una
    # imagen, `caja` es la parte que se puede pedir y `extension` es todo lo que hay: así **no se
    # pierde la información** de dónde están las tierras de fuera, aunque no se puedan dibujar de una
    # vez. Si la finca cabe entera, las dos cajas son la misma.
    #
    # Las dos cosas hacen falta y son una tensión de verdad: la revisión de T06 pidió que la caja que
    # da la vista **la acepte el propio programa** (D7: daba 1,02 grados, su `/api/mapa/imagen`
    # contestaba 422 y el agricultor leía «puede ser la cobertura» delante de un fallo que no tiene
    # nada que ver con eso) y que la caja **no se quede corta** y envuelva todas las formas. Con una
    # finca de más de medio grado las dos cosas no pueden ser la misma caja: se recorta la que se pide
    # y se dice entera la que hay.
    extension: CajaDelMapa | None = None


class FiltrosDeLasTierras(SalidaBase):
    """Lo que se puede elegir en cada filtro, **sacado de las tierras que hay**.

    No hay ninguna lista escrita a mano: los cultivos son los que están sembrados, los pueblos los
    que aparecen en las tierras y los estados de revisión los que tienen las versiones de este año.
    Un filtro que ofreciera una opción que no existe sería una promesa que no se puede cumplir.
    """

    cultivos: list[OpcionDeUnFiltro] = []
    municipios: list[OpcionDeUnFiltro] = []
    revisiones: list[OpcionDeUnFiltro] = []
    pac: list[OpcionDeUnFiltro] = []


class VistaDeLasTierras(SalidaBase):
    """Todo lo que necesita la pantalla de T06 para pintarse de una vez.

    Va entero en una respuesta y no en cinco llamadas porque la pantalla mezcla las tres cosas (la
    tabla, los filtros y el mapa) y **tienen que venir del mismo momento**: si los recuentos y las
    filas vinieran de dos peticiones distintas, el pie podría decir «64» sobre una lista de 63.

    `textos` viaja con los datos, como en `/api/mapa/estado` y `/api/cultivos`: las palabras son del
    servidor, y este endpoint no tiene entrada en `/api/interfaz` porque es el único que las usa.
    """

    textos: dict[str, str]
    # Las palabras de la ficha de una tierra y de la comparación de dos años, que las usa la pantalla
    # hermana. Van aquí para no tener que tocar `/api/interfaz`, que no es de este ticket.
    textos_de_las_versiones: dict[str, str]
    campana_id: int | None = None
    campana_anio: int | None = None
    tierras: list[TierraEnLaVista] = []
    totales: TotalesDeLasTierras
    mapa: ElMapaDeLaFinca
    filtros: FiltrosDeLasTierras


# --------------------------------------------------------------------------
# Los contactos (T11, 03/10/2026)
# --------------------------------------------------------------------------


class ContactoEntrada(EntradaBase):
    """La ficha de una persona o de una empresa, tal y como la escribe el agricultor.

    **Solo el nombre es obligatorio**, y no por comodidad: un proveedor del que solo tiene el nombre
    en la factura es un contacto que ya sirve para lo que existe esta sección (dejar de teclearlo cada
    vez). Lo que no se puede hacer es rellenar los huecos: sin teléfono, `telefono` va vacío y la
    pantalla no dice nada de teléfonos.

    `es_empresa` tiene **tres respuestas** y el defecto es «no lo sé» (`None`), no «es una persona»:
    hay nombres que no dicen qué hay detrás, y afirmarlo sería inventarse un dato.

    `papeles` son las claves del catálogo (`contactos.PAPELES`). Se admiten varios porque **los
    papeles se solapan**: la misma cooperativa te vende y te compra.
    """

    nombre: str = Field(min_length=1, max_length=200)
    es_empresa: bool | None = None
    nif: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=40)
    correo: str | None = Field(default=None, max_length=200)
    direccion: str | None = Field(default=None, max_length=200)
    localidad: str | None = Field(default=None, max_length=120)
    notas: str | None = None
    papeles: list[str] = []


class NombreEscrito(SalidaBase):
    """Un nombre escrito a mano en el cuaderno, con todo lo que hace falta para enseñarlo.

    `referencia` **no es una frase**: es una lista de trozos (el número de la factura, la fecha) y los
    junta la pantalla. `texto` es el nombre original y no se toca nunca.

    `enlace_id` va lleno cuando ese texto ya está enlazado con un contacto (el que sea). Es lo que
    permite que la pantalla diga «esto ya está enlazado» en vez de ofrecer un botón que daría error.
    """

    tabla: str
    campo: str
    registro_id: int
    texto: str
    nif: str | None = None
    papel: str = ""
    clave: str = ""
    referencia: list[str] = []
    fecha: dt.date | None = None
    # Vacío es «esa tabla no dice si está anulada» (`None`, no `False`).
    anulada: bool | None = None
    enlace_id: int | None = None
    contacto_id: int | None = None
    # **El texto que se enlazó no es el que hay ahora.** No es un fallo: el agricultor corrigió el
    # nombre del papel y el enlace es de antes. Se dice, y él decide si lo quita.
    texto_cambiado: bool = False
    texto_de_entonces: str | None = None


class EnlaceDeUnContacto(SalidaBase):
    """Un vínculo ya hecho: el mismo `NombreEscrito`, más de dónde salió el enlace."""

    id: int
    origen: str
    escrito: NombreEscrito


class NotaDeUnContactoEntrada(EntradaBase):
    """Una nota sobre una ficha: **solo el texto**. El autor y la fecha los pone el servidor.**

    No se acepta un autor escrito a mano: el autor es quien está apuntando, y eso lo sabe el servidor
    por su vale. Dejarlo venir del navegador sería poder firmar cosas que no ha escrito uno.
    """

    texto: str
    # **La clave de la acción** (13/10/2026). El navegador manda una por **acción** —no por clic— y el servidor la
    # usa para no apuntar dos veces la misma nota si la petición se reenvía: doble clic, respuesta perdida o
    # reintento del móvil sin cobertura. Es opcional para que el camino de siempre siga funcionando.
    clave_de_reenvio: str | None = None


class BajaDeUnContacto(EntradaBase):
    """Dar de baja a un contacto, o volver a usarlo: **el motivo es opcional**.

    No es obligatorio porque no todo el mundo quiere explicarlo, pero **se guarda si se escribe**: la
    auditoría está para poder contestar «¿por qué dejamos de trabajar con este?» dentro de un año.
    """

    motivo: str | None = None


class NotaDeUnContactoSalida(BaseModel):
    """Una nota de una ficha, con quién la escribió (CRM-03, criterio (f), 11/10/2026).

    `autor` puede ser `None` y **se dice**: hay notas que escribe el programa, y `None` es «no la
    escribió una persona». Inventarle un autor sería peor que no tenerlo.
    """

    id: int
    texto: str
    autor: str | None = None
    # **De quién es la nota, en tres estados** (13/10/2026): `persona` (se sabe quién), `sin_nombre` (la escribió
    # una persona y su nombre ya no está) o `el_programa` (no la escribió una persona). Sin este campo, «no hay
    # autor» se contaba como «lo apuntó el programa», y eso es afirmar algo que no se sabe.
    autor_estado: str
    creado_en: dt.datetime
    # La clave de la acción que la creó, para que el navegador pueda reconocer la suya si reintenta.
    clave_de_reenvio: str | None = None


class CanalDeUnContactoEntrada(EntradaBase):
    """Un teléfono, un correo o una dirección de una ficha (Entrega 2, 13/10/2026).

    **Lo que NO se valida, y es a propósito**: el teléfono no se trocea ni se le pone prefijo —se guarda
    tal y como se escribe, porque un programa que «arregla» un número puede dejar un número que no es el
    que hay que marcar— y la etiqueta es libre («administración», «el del almacén», «preguntar por
    Juan»), porque la vida no trae una lista cerrada y una etiqueta no rompe nada.

    **Lo que sí se exige**: que la clase sea una de las tres que hay y que venga **algo escrito**. Nada
    más: impedir guardar un dato legítimo es peor que guardarlo feo.
    """

    clase: str
    etiqueta: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    # Si nace o se pone como principal. El de su clase, que es lo que garantiza el índice parcial.
    principal: bool = False


class SaldoDeUnContacto(BaseModel):
    """Cuánto nos debe y cuánto le debemos, **separados y sin compensar** (13/10/2026).

    Los dos lados van aparte a propósito: que a la misma persona se le venda y se le compre es lo normal, y restar
    una deuda de la otra esconde las dos. Cada lado lleva sus **documentos** —para poder abrir de la cifra al
    papel— y `sin_importe`, que cuenta los que no se sabe cuánto valen: **un importe desconocido no es un cero**.

    `sin_asignar` es dinero que está y no se sabe de qué (un cobro o un pago sin aplicar) y **no rebaja ninguna
    deuda**; `para_revisar` son los **excesos** —se ha cobrado o pagado más de lo que valía el documento— que se
    marcan para mirarlos y **no se llaman anticipo**. `cobertura` dice hasta dónde llega este saldo y qué queda
    fuera, porque la factura de compra no tiene contacto y **no se adjudica por nombre**.
    """

    contacto_id: int
    # La moneda **se declara**: no hay columna de moneda en la base y `dinero.py` deja escrito que aquí todo es
    # euro, así que se dice en vez de suponerlo.
    moneda: str
    nos_debe: dict
    le_debemos: dict
    sin_asignar: dict
    para_revisar: list[dict]
    cobertura: dict


class CanalDeUnContactoSalida(BaseModel):
    """Un teléfono, un correo o una dirección de una ficha, con su etiqueta y su principal.

    Los valores van **tal cual se guardaron**: sin arreglar el teléfono y sin tocar el texto. `etiqueta`
    puede faltar —hay canales que nadie etiquetó— y entonces se dice con `None`.
    """

    id: int
    clase: str
    etiqueta: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    principal: bool


class EntradaDeUnaTarea(EntradaBase):
    """**Una próxima acción** (Entrega 3, 13/10/2026).

    `fecha_prevista` es un **día**, no un instante: la acción se piensa por días («el martes») y poner
    una hora obligaría a inventarla. Si no viene, la tarea queda **sin fecha**, que es una de las tres
    cosas que hay que poder distinguir (las otras: vencida y hecha).
    """

    titulo: str
    descripcion: str | None = None
    responsable: str | None = None
    # El día, en formato `AAAA-MM-DD`. `None` es «sin fecha», no «hoy».
    fecha_prevista: dt.date | None = None
    clave_de_reenvio: str | None = None


class CorreccionDeUnaTarea(EntradaBase):
    """**Corregir una tarea: todo opcional** (Entrega 3, 13/10/2026).

    POR QUÉ NO VALE LA ENTRADA DE CREAR, y me costó una prueba roja: allí `titulo` es **obligatorio**
    —porque una tarea sin saber qué hay que hacer no es nada—, así que un `PUT` que solo quería mover el
    día daba **422 «Field required»**. O sea que la corrección parcial que dejé documentada («lo que no
    viene no se toca») **era imposible**: la puerta exigía el título en cada cambio.

    Aquí **todo es opcional de verdad**, y quien decide qué se toca es `model_fields_set`: los campos que
    **vienen** en la petición. Un campo que no viene no se toca, y uno que viene nulo **sí** se vacía
    (eso es lo que permite «quitarle la fecha a una tarea»).
    """

    titulo: str | None = None
    descripcion: str | None = None
    responsable: str | None = None
    fecha_prevista: dt.date | None = None


class TareaSalida(BaseModel):
    """Cómo se cuenta una tarea, con lo que se **calcula** y no se guarda.

    `vencida` **se calcula al leer** (fecha anterior a hoy y todavía pendiente): no es un estado guardado,
    porque el encargo dice que una fecha vencida **no** transforma la tarea en cancelada, y un estado que
    hubiera que ir actualizando cada noche es una promesa que no se puede cumplir.
    """

    id: int
    contacto_id: int
    titulo: str
    descripcion: str | None = None
    responsable: str | None = None
    fecha_prevista: dt.date | None = None
    # El día **dicho con palabras** («15/10/2026») o «Sin fecha». El front no tiene que saber formatear
    # fechas, que es de donde salen los errores de formato y de zona.
    fecha_texto: str
    estado: str
    vencida: bool
    completada_en: dt.datetime | None = None
    completada_por: str | None = None
    cancelada_en: dt.datetime | None = None
    cancelada_por: str | None = None


class ListaDeTareas(BaseModel):
    """**La lista de lo que hay que hacer** (Entrega 3).

    Va envuelta en un diccionario con nombre (`tareas`) por el mismo motivo que las demás listas de la
    casa: el día que haya que decir algo **de la lista** —cuántas van vencidas, si hay más de las que se
    enseñan—, hay sitio donde ponerlo sin cambiar la forma de lo que ya viaja.
    """

    tareas: list[TareaSalida]


class ContactoSalida(SalidaBase):
    # **A quién remite esta ficha si se fusionó** (Entrega 5, 14/10/2026). Estaba en el MODELO pero no
    # aquí, así que el remitir **no se podía leer por la puerta**: la ficha de la que desapareció dice a
    # dónde fue, y sin este campo el cliente no tenía forma de saberlo. Lo midió la andadura de la fusión.
    fusionado_con_id: int | None = None
    """Un contacto con sus papeles y lo que se sabe de él.

    `enlaces` es **el número de enlaces que siguen vivos** (los que apuntan a un documento que todavía
    existe), y `nombres_escritos` son las formas distintas en que su nombre está escrito hoy en el
    cuaderno. Los dos los cuenta el servidor: la pantalla no suma nada.
    """

    id: int
    nombre: str
    es_empresa: bool | None = None
    nif: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    notas: str | None = None
    # Si se sigue trabajando con esta ficha (CRM-03, criterio (e)): **un contacto inactivo conserva sus
    # relaciones**, así que se enseña el estado en vez de esconder la ficha.
    #
    # **Sin valor por defecto, y es a propósito**: con `= True`, la primera versión tapaba el valor de
    # verdad —la respuesta no lo traía y el esquema rellenaba `True`—, así que una ficha de baja se leía
    # como activa. En una salida, un valor por defecto es una mentira esperando su turno: si falta el
    # dato, que falle.
    activo: bool
    # Las notas de la ficha, de la más nueva a la más vieja, con su autor (criterio (f)).
    #
    # **Sin valor por defecto**: la lista de contactos la manda vacía y la ficha la manda
    # llena, pero las dos la mandan. Un valor por defecto aquí taparía un olvido —que es lo que
    # pasó con `activo`—, y una ficha sin notas y una ficha con las notas olvidadas no son lo
    # mismo.
    notas_con_autor: list[NotaDeUnContactoSalida]
    # Los canales de la ficha (Entrega 2): sus teléfonos, correos y direcciones, con etiqueta y
    # principal. Va **sin valor por defecto**, por el mismo motivo que las notas.
    canales: list[CanalDeUnContactoSalida]
    # Las próximas acciones de la ficha (Entrega 3). **Sin valor por defecto**, como los canales y las
    # notas: una lista vacía parecería «este contacto no tiene nada pendiente», que es distinto de «no me
    # lo han mandado».
    tareas: list[TareaSalida]
    origen: str = "a_mano"
    # Los papeles que el agricultor le ha marcado.
    papeles: list[str] = []
    # **Y los que dicen sus propios papeles**, sacados de lo que está enlazado: si una factura suya
    # está enlazada con esta ficha, el proveedor de esa factura es él. No se marca solo —el agricultor
    # decide— pero se enseña, porque es la forma de que vea que los papeles se solapan.
    papeles_segun_lo_escrito: list[str] = []
    enlaces: int = 0
    nombres_escritos: list[str] = []


class FichaDelContacto(ContactoSalida):
    # **A quién remite esta ficha si se fusionó** (Entrega 5, 14/10/2026). Estaba en el MODELO pero no
    # aquí, así que el remitir **no se podía leer por la puerta**: la ficha de la que desapareció dice a
    # dónde fue, y sin este campo el cliente no tenía forma de saberlo. Lo midió la andadura de la fusión.
    fusionado_con_id: int | None = None
    """La ficha con sus vínculos uno por uno, que es lo que se mira al abrirla."""

    vivos: list[EnlaceDeUnContacto] = []


class PropuestaDeContacto(SalidaBase):
    """Una ficha que **se le propone** al agricultor a partir de los nombres que ya están escritos.

    `clave` es lo que se manda de vuelta para confirmarla, y `segura` dice si se puede apuntar sin
    miedo. Cuando `segura` es falso, `motivo` dice cuál de los dos casos es —«se parecen» o «el mismo
    nombre con dos NIF»— y **el servidor se niega a apuntarla aunque se lo pidan**: un «no se juntan»
    que solo estuviera en la pantalla se podría saltar desde fuera.
    """

    clave: str
    nombre: str
    segura: bool
    motivo: str
    papeles: list[str] = []
    nombres: list[str] = []
    nifs: list[str] = []
    # Los dos nombres que se parecen, cuando el motivo es «se parecen». Vacío en los demás casos.
    pareja: list[str] = []
    escritos: list[NombreEscrito] = []


class ResumenDeLaPropuesta(SalidaBase):
    fichas: int
    nombres: int
    se_parecen: int
    homonimos: int
    # El tercer motivo por el que dos nombres **no** se juntan: el mismo NIF con nombres que no se
    # parecen. Se cuenta aparte porque es un caso distinto (un NIF mal tecleado) y porque fue el
    # defecto que encontró la revisión independiente: mientras sea un número visible, no se puede
    # volver a colar en silencio.
    nif_con_nombres_distintos: int = 0


class RevisionDeLosNombres(SalidaBase):
    """La propuesta entera: **lo que hay que decidir y por qué**, contado por el servidor.

    `ya_enlazados` cuenta los nombres escritos que ya tienen dueño y por eso no salen en la propuesta:
    sin ese número, el agricultor vería que faltan facturas y no sabría por qué.

    `se_puede_deshacer` dice si hay alguna ficha que apuntó la migración y todavía se puede quitar. Va
    aquí y no lo decide la pantalla porque **la pantalla no puede saberlo**: una ficha de la migración
    que el agricultor ya ha corregido no se deshace, y eso lo sabe el servidor.
    """

    resumen: ResumenDeLaPropuesta
    propuestas: list[PropuestaDeContacto] = []
    ya_enlazados: int = 0
    total_escritos: int = 0
    se_puede_deshacer: bool = False


class ConfirmacionDeLaMigracion(EntradaBase):
    """Las propuestas que el agricultor confirma, **por su clave**.

    Se mandan claves y no nombres a propósito: lo que se aplica es la propuesta que el servidor
    recalcula, no lo que diga la petición. Si entre mirar y confirmar entra una factura nueva y la
    propuesta cambia, el servidor lo dice y no apunta nada a medias.
    """

    claves: list[str] = []


class ResultadoDeLaMigracion(SalidaBase):
    """Qué ha pasado, con los números de verdad y lo que **no** se ha hecho.

    `textos_tocados` va siempre a `0` y se devuelve a propósito: es la promesa del ticket escrita en
    el dato que se guarda, para que se pueda comprobar sin creerse un comentario.
    """

    fichas: int = 0
    enlaces: int = 0
    textos_tocados: int = 0
    nombres: list[str] = []
    avisos: list[str] = []
    contactos: list[int] = []


class DeshacerLaMigracion(SalidaBase):
    fichas: int = 0
    enlaces: int = 0
    # Las fichas que **no** se han borrado porque el agricultor las ha tocado después, con su motivo.
    se_quedan: list[str] = []
    textos_tocados: int = 0


class EnlaceEntrada(EntradaBase):
    """Enlazar un texto escrito con un contacto: dónde está el texto y punto.

    **No se manda el nombre.** Si se aceptara, se podría «enlazar» un texto que no existe escribiéndolo
    aquí, y eso sería crear un dato desde fuera. Lo que hace el servidor es leer el texto donde está de
    verdad y guardar lo que diga.
    """

    tabla: str = Field(min_length=1, max_length=60)
    campo: str = Field(min_length=1, max_length=60)
    registro_id: int


class PapelEntrada(EntradaBase):
    papel: str = Field(min_length=1, max_length=40)
    puesto: bool = True


# --------------------------------------------------------------------------
# Las cuentas de la explotación (T13, E7, 05/10/2026)
# --------------------------------------------------------------------------
#
# **Lo que estos esquemas tienen de particular, y por qué**: los importes son `Decimal | None` y
# **`None` quiere decir «no lo sé»**, no cero. Es la regla del encargo («un importe que no consta NO
# es cero: es “no lo sé”, y así tiene que viajar de punta a punta») y empieza aquí: si el esquema
# rechazara un importe vacío, el agricultor no podría apuntar la reparación de la que no se acuerda
# del precio, y acabaría escribiendo un cero que es mentira.
#
# Los campos de texto llevan su tope **leído del modelo** (`_cabe_en_la_columna`), como los del
# dinero del T12: un texto más largo que su columna en SQLite entra y **en PostgreSQL tumba la
# operación entera**.


class GastoEntrada(EntradaBase):
    """Lo que hace falta para apuntar un gasto. **Ningún importe es obligatorio.**"""

    campana_id: int | None = None
    fecha: dt.date | None = None
    vencimiento: dt.date | None = None
    concepto: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "concepto")
    )
    categoria: str = "otro"
    proveedor: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "proveedor")
    )
    proveedor_nif: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "proveedor_nif")
    )
    contacto_id: int | None = None
    factura_id: int | None = None
    maquina_id: int | None = None
    averia_id: int | None = None
    parcela_id: int | None = None
    cultivo: str | None = Field(default=None, max_length=_cabe_en_la_columna(models.Gasto, "cultivo"))
    # **Los cuatro pueden venir vacíos**, cada uno por su cuenta: el total escrito manda, si no se
    # suman base y cuota, si no se aplica el tipo a la base, y si no hay nada el gasto **no tiene
    # importe** (`gastos.importe_de_un_gasto`).
    base_imponible: ImporteDeEntradaOpcional = None
    cuota_iva: ImporteDeEntradaOpcional = None
    tipo_iva_pct: float | None = None
    importe: ImporteDeEntradaOpcional = None
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Gasto, "clave_de_reenvio")
    )

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.Gasto)


class InversionEntrada(EntradaBase):
    """Lo que hace falta para apuntar un bien que dura. **No es un gasto y no entra en el margen.**"""

    campana_id: int | None = None
    fecha: dt.date | None = None
    concepto: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "concepto")
    )
    categoria: str = "otro"
    proveedor: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "proveedor")
    )
    proveedor_nif: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "proveedor_nif")
    )
    contacto_id: int | None = None
    factura_id: int | None = None
    maquina_id: int | None = None
    parcela_id: int | None = None
    importe: ImporteDeEntradaOpcional = None
    valor_residual: ImporteDeEntradaOpcional = None
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.InversionDeLaFinca, "clave_de_reenvio")
    )

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.InversionDeLaFinca)


class TrozoDeRepartoEntrada(BaseModel):
    """Un trozo de un reparto hecho a mano: a dónde va y cuánto."""

    destino_tipo: str = "tierra"
    destino: str = ""
    # El importe de un trozo escrito a mano: la misma regla del dinero que los demás.
    importe: ImporteDeEntradaOpcional = None


class RepartoDeUnGastoEntrada(EntradaBase):
    """Cómo se reparte un gasto. **El método lo confirma el agricultor**, y por eso se pregunta.

    Los cuatro métodos (área, horas, consumo y manual) y lo que trae cada uno:

      · **area** — `parcela_ids`. Las hectáreas las lee el servidor de cada tierra: el agricultor no
        las teclea, y así no hay dos verdades sobre cuánto mide su parcela. **Si a una le falta la
        superficie, el reparto no se hace y el gasto se queda sin asignar.**
      · **horas** y **consumo** — `pesos`: las horas o los litros de cada sitio, que los dice él.
      · **manual** — `trozos`: los importes, uno a uno.
    """

    metodo: str = "manual"
    destino_tipo: str = "tierra"
    parcela_ids: list[int] = Field(default_factory=list)
    pesos: dict[str, Decimal | None] = Field(default_factory=dict)
    trozos: list[TrozoDeRepartoEntrada] = Field(default_factory=list)
    # Si el agricultor ha confirmado el método. **Nace en falso**: un reparto que hizo el programa y
    # nadie ha mirado no puede parecer confirmado.
    confirmado: bool = False
    # Por qué se deja sin asignar. Solo lo usa la puerta de «dejarlo sin asignar».
    porque: str = ""


class AplicacionDePagoEntrada(BaseModel):
    """Cuánto de un pago va contra un gasto. Sin importe, va lo que falte de ese gasto."""

    gasto_id: int
    # Y el de lo que un pago salda de un gasto: también como lo escribe un agricultor.
    importe: ImporteDeEntradaOpcional = None


class PagoEntrada(EntradaBase):
    """El dinero que sale, con lo que salda si ya se sabe.

    **`aplicaciones` puede venir vacío**, y entonces el pago se queda **sin conciliar** y se dice: es
    lo normal cuando se mira el banco antes que los papeles.
    """

    fecha: dt.date | None = None
    # **Obligatorio y mayor que cero**: un pago de cero euros no es un pago. Lo comprueba el router
    # con la frase del agricultor.
    importe: ImporteDeEntradaOpcional = None
    proveedor: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.PagoDeGasto, "proveedor")
    )
    contacto_id: int | None = None
    forma: str = "transferencia"
    referencia: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.PagoDeGasto, "referencia")
    )
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.PagoDeGasto, "clave_de_reenvio")
    )
    aplicaciones: list[AplicacionDePagoEntrada] = Field(default_factory=list)

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.PagoDeGasto)


class ConciliacionDePagoEntrada(BaseModel):
    """Decir contra qué gastos va un dinero que ya estaba apuntado. **No crea ningún gasto.**

    Con `automatico` y `gastos`, el dinero se reparte **por orden, el más antiguo primero**
    (`gastos.reparto_de_un_pago`): así la suma de lo aplicado es exactamente el dinero disponible y no
    hay ningún reparto por porcentaje, que es donde aparecerían los céntimos perdidos.
    """

    aplicaciones: list[AplicacionDePagoEntrada] = Field(default_factory=list)
    automatico: bool = False
    gastos: list[int] = Field(default_factory=list)


class SubvencionEntrada(EntradaBase):
    """Una ayuda, con sus tres importes. Los tres pueden venir, y ninguno es obligatorio."""

    campana_id: int | None = None
    concepto: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Subvencion, "concepto")
    )
    organismo: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Subvencion, "organismo")
    )
    fecha_solicitud: dt.date | None = None
    fecha_concesion: dt.date | None = None
    fecha_cobro: dt.date | None = None
    importe_previsto: ImporteDeEntradaOpcional = None
    importe_concedido: ImporteDeEntradaOpcional = None
    importe_cobrado: ImporteDeEntradaOpcional = None
    notas: str | None = None
    clave_de_reenvio: str | None = Field(
        default=None, max_length=_cabe_en_la_columna(models.Subvencion, "clave_de_reenvio")
    )

    _lo_que_no_cabe = _revisa_lo_que_no_cabe(models.Subvencion)

# --------------------------------------------------------------------------
# Los trabajos por tierra (T15, 05/10/2026)
# --------------------------------------------------------------------------


class InsumoDeUnTrabajoEntrada(EntradaBase):
    """Lo que un trabajo gasta de un envase, o lo que se piensa gastar.

    `cantidad` y `unidad` son opcionales: lo que no se sabe **no se resta** (se dice por qué), y un total
    inventado aquí sería un descuento que nadie ha hecho.
    """

    articulo_id: int | None = None
    lote_id: int | None = None
    cantidad: float | None = Field(default=None, gt=0)
    unidad: str | None = None
    # Para lo previsto: lo de cada hectárea, que es lo que permite estimar el total sin confundirlo con él.
    dosis_por_ha: float | None = Field(default=None, ge=0)
    aceptar_descuadre: bool = False


class TrabajoEntrada(EntradaBase):
    """Un trabajo **hecho**: lo que pasó, con su día y lo que se gastó de verdad."""

    campana_id: int
    tipo: str
    subtipo: str | None = None
    fecha: dt.date
    parcela_id: int | None = None
    grupo_id: int | None = None
    superficie_ha: float | None = Field(default=None, ge=0)
    cultivo: str | None = None
    variedad: str | None = None
    equipo_id: int | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None
    insumos: list[InsumoDeUnTrabajoEntrada] | None = None
    previsto_id: int | None = None
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class TrabajoPrevistoEntrada(EntradaBase):
    """Un trabajo **planificado**. Todo lo que no se sepa se queda en blanco."""

    campana_id: int
    tipo: str
    subtipo: str | None = None
    fecha_prevista: dt.date | None = None
    fecha_fin_prevista: dt.date | None = None
    parcela_id: int | None = None
    grupo_id: int | None = None
    superficie_ha: float | None = Field(default=None, ge=0)
    cultivo: str | None = None
    variedad: str | None = None
    equipo_id: int | None = None
    persona: str | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None
    lineas: list["LineaDeTrabajoPrevistoEntrada"] | None = None
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class LineaDeTrabajoPrevistoEntrada(EntradaBase):
    """Una tierra del plan, con **su cantidad dicha**. No se reparte el total por igual."""

    parcela_id: int
    superficie_ha: float | None = Field(default=None, ge=0)
    cantidad: float | None = Field(default=None, ge=0)
    unidad: str | None = None
    dosis_por_ha: float | None = Field(default=None, ge=0)
    articulo_id: int | None = None
    lote_id: int | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None


class MarcarHechoEntrada(EntradaBase):
    """Lo que de verdad se hizo, cuando se cumple un plan. **El plan no se copia: se apunta el hecho.**"""

    fecha: dt.date
    superficie_ha: float | None = Field(default=None, ge=0)
    cultivo: str | None = None
    variedad: str | None = None
    equipo_id: int | None = None
    horas: float | None = Field(default=None, ge=0)
    observaciones: str | None = None
    insumos: list[InsumoDeUnTrabajoEntrada] | None = None
    clave_de_reenvio: str | None = None
    id_local: str | None = None


class ReprogramarEntrada(EntradaBase):
    """Mover un plan de día, con su motivo. **Lo que ya se hizo no se mueve.**"""

    fecha_prevista: dt.date
    motivo: str | None = Field(default=None, max_length=500)
