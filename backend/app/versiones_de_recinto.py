"""Las versiones del recinto y la importación repetible de un lote (T05, 02/10/2026).

## Qué problema resuelve

`Parcela` guarda **lo que una tierra es hoy**. El contrato (§2.1, y la entrega T05 de su §7)
pide algo más: **qué era ese recinto en cada campaña, según qué fuente, y cuándo se consultó**.
Lo dice con estas palabras:

    «Separar tierra que el agricultor reconoce, recinto SIGPAC de una campaña y superficie
    declarada a la PAC. […] Guardar una versión por campaña y fuente, con referencia completa,
    polígono válido, área de la geometría, área SIGPAC, área trabajada/declarada, fecha de
    consulta y estado de revisión. Nunca sustituir hectáreas declaradas por las calculadas.»

Eso es lo que hace `models.VersionDeRecinto` y lo que gobierna este módulo.

## Las cuatro reglas que no se pueden saltar

1. **Las hectáreas declaradas no se sustituyen por las calculadas.** En el código se ve literal:
   `area_declarada_ha` sale **solo** de `entrada.area_declarada_ha`. El área de la forma la calcula
   `geo.area_ha` y va a su propio campo. Ninguna de las tres áreas se rellena desde otra.
2. **Lo que no se sabe se queda vacío, nunca en 0.** Un recinto sin superficie entra con
   `area_sigpac_ha = None` (no con 0,0) y el programa dice «no se sabe la superficie». Es la regla
   que gobierna el proyecto entero (`docs/T02_VALORES_POR_DEFECTO.md`, hallazgo A7).
3. **Nunca se inventa un polígono.** Un recinto sin forma entra igual, con `geometria = None`, y
   sale en el grupo «sin forma» de la lista. No se le dibuja nada.
4. **La versión no toca el alias, las notas ni el historial de la tierra.** Este módulo escribe en
   `versiones_de_recinto` y, al dar de alta una tierra que no existía, en `parcelas` **solo para
   crearla**. No hay ni una línea que cambie el alias de una tierra que ya está.

## Importación repetible: qué significa aquí, exactamente

El contrato llama a esto «importación repetible sobre copia». Se traduce en tres cosas que se
pueden medir, no en una promesa:

  · **Primero se previsualiza y no se escribe nada.** `plan_de_importacion` solo lee. Devuelve
    cuántos recintos son nuevos, cuántos cambian, cuántos están iguales y cuántos no traen forma.
  · **Aplicar dos veces el mismo lote no crea nada la segunda vez.** La segunda aplicación
    encuentra la versión de cada recinto y **no encuentra diferencias**, así que no escribe: ni
    versiones nuevas, ni cambios, ni rastro en la auditoría. La prueba lo mide contando filas, no
    afirmándolo.
  · **Solo se escribe lo que cambia, y un campo que no viene no se borra.** Si el SIGPAC manda el
    recinto otra vez sin la superficie declarada —que la declaró el agricultor—, su superficie
    declarada sigue donde estaba.

## Por qué hay **una versión por tierra, campaña y fuente**

Es lo que dice el contrato, literal: «una versión por campaña y fuente». Y encaja con el modelo de
hoy, en el que **una tierra es un recinto** (`Parcela` guarda una referencia del SIGPAC, con su
número de recinto). El día que una tierra pueda llevar varios recintos —el `VinculoTierraRecinto`
del contrato §11, que todavía no existe—, hará falta una fila por vínculo; mientras tanto, dos
recintos distintos de la misma tierra en la misma campaña y fuente son un dato contradictorio, y
**el programa lo dice en vez de guardar el último y callarse** (`R6_recinto_repetido`).

## Lo que este módulo NO hace, y se dice

  · **No corrige los solapes.** Los detecta y los cuenta (`solapes`), que es lo que pide el
    contrato: «detectar solapes y diferencias de superficie y decirlo, sin corregirlo solo».
  · **No decide a qué tierra pertenece un recinto que no se puede saber.** Si la referencia viene
    sin el número de recinto y hay dos tierras que podrían ser, **no se adivina ninguna**: el
    recinto sale en la lista de lo que no se ha podido tener en cuenta, diciendo qué falta. Es mejor
    un lote importado a medias y explicado que uno completo con una tierra inventada.
  · **No rellena la fecha de consulta con la de hoy.** Si el lote no la dice, se queda en blanco:
    poner la fecha de hoy afirmaría una consulta que quizá se hizo en marzo.
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select

from . import catalogos, geo, legal, models, schemas, sigpac, textos

# --------------------------------------------------------------------------
# Las fuentes y los estados
# --------------------------------------------------------------------------

# Las fuentes que el contrato nombra (T05). No hay más, y una fuente que no esté en esta lista se
# rechaza diciéndolo: guardar un lote «de donde sea» haría que dentro de un año nadie supiera de
# dónde salió un dato, que es justo lo que la versión existe para conservar.
FUENTES = ("sigpac", "cuaderno_de_la_junta", "agricultor", "medicion_en_campo")

# **Cuál manda cuando dos versiones empatan** (02/10/2026). El contrato dice «una versión por campaña y
# fuente», así que la misma tierra puede tener en la misma campaña **la del SIGPAC y la del agricultor**
# con la misma clave de recinto. La tabla de tierras enseña una sola —de ella salen el estado de revisión
# y las hectáreas declaradas—, y hasta hoy decidía **el orden que le salía al plan de la base**:
# `routers/parcelas.py` ordenaba por `(parcela_id, clave)` y se quedaba con la primera, así que en SQLite
# ganaba una y en PostgreSQL la otra. **La misma tierra enseñaba cosas distintas según el motor.** Lo
# encontró por fin la suite corriendo contra PostgreSQL: en
# `tests/test_revision_t06.py::test_dos_fuentes_del_mismo_ano_no_se_deciden_por_el_orden_de_importacion`
# (que existía justo por esto: su autor intentó romperlo con SQLite, no pudo, y dejó escrito que el código
# se apoyaba en «el orden que le sale al plan»).
#
# El orden lo decide **quién lo dijo**, no cómo se llama la fuente:
#
#   1. lo que se **midió en el campo**,
#   2. lo que **declaró el agricultor**,
#   3. lo que trajo **su cuaderno de la Junta**,
#   4. y por último la **importación oficial del SIGPAC**.
#
# No es una preferencia estética: es la regla de que **lo que el agricultor corrige no puede quedar
# tapado por lo que trajo la administración**. Si dos versiones empatan en la misma fuente (no debería
# pasar, pero puede), decide el identificador más alto: la más nueva.
PRIORIDAD_DE_FUENTES = ("medicion_en_campo", "agricultor", "cuaderno_de_la_junta", "sigpac")

# El estado de revisión de una versión. Empieza en «sin revisar»: importar no es revisar.
ESTADOS_DE_REVISION = ("sin_revisar", "revisado", "con_dudas")

# Los cuatro estados de la comparación, con los nombres del contrato (§2.1: «previsualización de
# `igual/cambiado/desaparecido/nuevo`»).
IGUAL = "igual"
CAMBIADO = "cambiado"
DESAPARECIDO = "desaparecido"
NUEVO = "nuevo"

# Qué se compara entre dos versiones, y con qué nombre se le cuenta al agricultor. El nombre es una
# clave de `textos.VERSIONES_DE_RECINTO`: **ni una frase se escribe aquí**, que es la regla de
# `AGENTS.md` §3.1.
#
# Lo que NO se compara, y por qué: el **estado de revisión** (marcar algo como revisado no es que el
# recinto haya cambiado, y decirlo llenaría la lista de cambios que no lo son) y la **fecha de
# consulta** (dice cuándo se miró, no cómo es el recinto).
CAMPOS_QUE_SE_COMPARAN = (
    ("referencia", "campo_referencia"),
    ("poligono_valido", "campo_referencia_completa"),
    ("geometria", "campo_geometria"),
    ("area_geometria_ha", "campo_area_geometria"),
    ("area_sigpac_ha", "campo_area_sigpac"),
    ("area_declarada_ha", "campo_area_declarada"),
    ("uso_sigpac", "campo_uso"),
)

# Los siete números de una referencia, en su orden. Es el orden de `sigpac.Referencia` y el que usa
# la clave de una versión.
CAMPOS_DE_LA_REFERENCIA = (
    "provincia",
    "municipio",
    "agregado",
    "zona",
    "poligono",
    "numero_parcela",
    "numero_recinto",
)

# A partir de qué diferencia se avisa de que dos superficies del mismo recinto no cuadran.
#
# **De dónde sale el 2 %.** No es un número puesto a ojo: la única comprobación que se puede hacer
# con datos oficiales es el recinto de ejemplo del SIGPAC
# (`data/sigpac/recinto_de_ejemplo.json`, que trae su WKT y su superficie oficial de 2,7923 ha).
# El área de ese WKT, medida con `geo.area_ha`, sale 2,788534 ha: **un 0,13 % menos**. El 2 % es
# unas quince veces ese error, así que no salta por cómo se mide, y sigue siendo lo bastante fino
# para que una parcela de una hectárea avise cuando se le van 200 m². Y no es un límite legal: es el
# punto a partir del cual merece la pena que alguien mire. Por debajo también se dice cuánto se
# llevan, simplemente no se marca como aviso.
UMBRAL_DE_DIFERENCIA = 0.02


class LoteQueNoSePuedeAplicar(ValueError):
    """El lote no se puede ni mirar, y se dice por qué con un mensaje ya escrito.

    `codigo_http` lo usa el router: un dato que falta es un 400, y algo que es de otra finca es un
    **404** y no un 403, para no decir si ese identificador existe en otro cuaderno (`deps.py`).
    """

    def __init__(self, mensaje: str, codigo_http: int = 400) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo_http = codigo_http


# --------------------------------------------------------------------------
# Leer lo que viene en el lote, sin inventar nada
# --------------------------------------------------------------------------


def texto_de_la_fuente(fuente: str) -> str:
    """Cómo se llama esa fuente en la pantalla, o su código si no se conoce.

    Un código desconocido se devuelve tal cual **a propósito**: es lo que guarda la base y lo que
    hay que mirar para arreglarlo. Devolver «SIGPAC» por defecto sería inventarse el origen.
    """
    return textos.VERSIONES_DE_RECINTO.get(f"fuente_{fuente}", fuente)


def texto_del_estado(estado: str) -> str:
    """`igual`, `cambiado`… en palabras, que es como lo lee el agricultor."""
    return textos.VERSIONES_DE_RECINTO.get(f"estado_{estado}", estado)


def texto_del_estado_de_revision(estado: str) -> str:
    return textos.VERSIONES_DE_RECINTO.get(f"revision_{estado}", estado)


def numeros_de_la_referencia(entrada: schemas.RecintoDelLote) -> dict:
    """Los siete números de la referencia, **tal y como vengan**. Ninguno se rellena.

    Se aceptan las tres formas que existen de verdad (el papel del SIGPAC con sus siete números, el
    visor con seis y la referencia catastral de veinte caracteres) y se leen con **el mismo lector
    que usa el mapa** (`sigpac.lee_busqueda`): tener dos formas de entender una referencia es la
    manera más rápida de que un día digan cosas distintas.

    Si el recinto trae los números uno a uno, mandan esos: son los que ha leído quien tiene el papel
    delante. Un texto de referencia que no se entiende **no se adivina**: se ignora, y quien llama
    se queda con lo que sí venía.
    """
    leidos: dict = {}
    if (entrada.referencia or "").strip():
        try:
            busqueda = sigpac.lee_busqueda(entrada.referencia)
        except sigpac.ReferenciaInvalida:
            busqueda = None
        if busqueda is not None:
            leidos = {
                "provincia": str(busqueda.provincia),
                "municipio": str(busqueda.municipio),
                "agregado": busqueda.agregado,
                "zona": busqueda.zona,
                "poligono": busqueda.poligono,
                "numero_parcela": busqueda.parcela,
                "numero_recinto": busqueda.recinto,
            }

    for campo in ("provincia", "municipio"):
        valor = getattr(entrada, campo, None)
        if valor is not None and str(valor).strip():
            leidos[campo] = str(valor).strip()
    for campo in ("agregado", "zona", "poligono", "numero_parcela", "numero_recinto"):
        valor = getattr(entrada, campo, None)
        if valor is not None:
            leidos[campo] = int(valor)
    return leidos


def referencia_completa(numeros: dict) -> str | None:
    """La referencia de los siete números como texto, **solo si están todos**.

    Una referencia a la que le falta el recinto no identifica a nadie, así que no se devuelve como
    si fuera una referencia: se devuelve `None` y el recinto queda marcado (`poligono_valido`).
    """
    if any(
        numeros.get(campo) is None or str(numeros.get(campo)).strip() == ""
        for campo in CAMPOS_DE_LA_REFERENCIA
    ):
        return None
    return "-".join(str(numeros[campo]) for campo in CAMPOS_DE_LA_REFERENCIA)


def clave_del_recinto(numeros: dict, geometria: str | None) -> str:
    """Con qué recinto hablaba esa importación, dentro de su tierra, su campaña y su fuente.

    **Es la pieza que hace que importar dos veces no duplique nada**, así que su criterio está
    escrito y probado:

      · Si hay referencia, la clave es la referencia —completa o a medias—. Dos recintos de la misma
        tierra a los que les falta el mismo trozo y traen los mismos números son, para el programa,
        el mismo recinto: **no se pueden distinguir**, y tratarlos como dos sería inventarse una
        diferencia que nadie ha visto.
      · Si no hay ninguna referencia, la clave es la **huella de la forma**: dos formas distintas
        son dos recintos, y la misma forma dos veces es el mismo.
      · Si no hay ni referencia ni forma, la clave es vacía y ese recinto **no se puede apuntar**:
        quien llama lo dice en vez de guardar algo que no se sabe qué es.
    """
    completa = referencia_completa(numeros)
    if completa is not None:
        # **La referencia completa es la clave, tal cual.** Antes se llegaba aquí solo por el camino
        # de abajo, que deja en blanco los ceros, y salía `37-70---507-24-1`: una referencia con los
        # ceros comidos que **no se puede cotejar con ningún papel** —y es la que se guarda en
        # `versiones_de_recinto.clave` y la que sale en la respuesta—. Lo encontró la revisión
        # independiente (D7, 03/10/2026). Con esto, la clave de un recinto completo **es** su
        # referencia, y de paso `agregado = 0` («es cero») deja de dar lo mismo que `agregado` sin
        # decir («no lo sé»), que es la regla de la casa.
        return completa[:80]

    partes = [str(numeros.get(campo) or "") for campo in CAMPOS_DE_LA_REFERENCIA]
    if any(partes):
        return "-".join(partes)[:80]
    if geometria:
        huella = hashlib.sha256(geometria.strip().encode("utf-8")).hexdigest()[:8]
        return f"forma:{huella}"
    return ""


# --------------------------------------------------------------------------
# Comparar dos versiones: igual / cambiado / desaparecido / nuevo
# --------------------------------------------------------------------------


def que_cambio(antes: dict, despues: dict) -> list[str]:
    """Qué se ha movido entre dos versiones, con el nombre de cada cosa ya escrito.

    Se comparan los datos que da la fuente (la referencia, la forma, las tres superficies y el uso).

    **Una limitación que se dice en vez de esconderse:** la forma se compara **por el texto que
    vino**, no por si las dos formas son la misma dibujada de otra manera. Un recinto cuyos vértices
    vengan en otro orden saldrá como «cambiado» aunque sea el mismo trozo, y eso el agricultor lo ve
    en la pantalla y puede decidir. Comparar formas de verdad es calcular su intersección, y aquí
    eso no se hace.
    """
    cambiado: list[str] = []
    for campo, nombre in CAMPOS_QUE_SE_COMPARAN:
        if antes.get(campo) != despues.get(campo):
            cambiado.append(textos.VERSIONES_DE_RECINTO[nombre])
    return cambiado


def comparar(antes: list[dict], despues: list[dict]) -> list[dict]:
    """Compara dos conjuntos de versiones y dice en cuál de los cuatro estados está cada recinto.

    **Es una función pura y no escribe nada**: se puede llamar tantas veces como haga falta antes de
    decidir, que es lo que el contrato llama «previsualización».

    Cada versión se reconoce por **(tierra, fuente)**, que es lo que dice el contrato («una versión
    por campaña y fuente»). Por eso el SIGPAC de 2025 se compara con el SIGPAC de 2026, y lo que
    dijo el agricultor con lo que dijo el agricultor: mezclar fuentes diría «cambiado» de un recinto
    que solo ha mirado otra. Si se quiere comparar una fuente concreta, se filtran las dos listas.
    """
    mapa_antes = {_identidad(version): version for version in antes}
    mapa_despues = {_identidad(version): version for version in despues}
    salida: list[dict] = []
    for identidad in sorted(set(mapa_antes) | set(mapa_despues), key=lambda clave: str(clave)):
        en_antes = mapa_antes.get(identidad)
        en_despues = mapa_despues.get(identidad)
        if en_antes is None:
            estado, cambios = NUEVO, []
        elif en_despues is None:
            estado, cambios = DESAPARECIDO, []
        else:
            cambios = que_cambio(en_antes, en_despues)
            estado = CAMBIADO if cambios else IGUAL
        salida.append(
            {
                "clave": (en_despues or en_antes).get("clave"),
                "parcela_id": identidad[0],
                "fuente": identidad[1],
                "estado": estado,
                "estado_texto": texto_del_estado(estado),
                "que_cambio": cambios,
                "antes": en_antes,
                "despues": en_despues,
                "referencia": (en_despues or en_antes).get("referencia"),
            }
        )
    return salida


def _identidad(version: dict) -> tuple:
    """(tierra, fuente): lo que hace que dos versiones hablen del mismo recinto."""
    return (version.get("parcela_id"), version.get("fuente"))


def cuantos_por_estado(comparacion: list[dict]) -> dict:
    """Los cuatro totales, que es lo primero que se mira de una comparación."""
    return {
        IGUAL: sum(1 for cambio in comparacion if cambio["estado"] == IGUAL),
        CAMBIADO: sum(1 for cambio in comparacion if cambio["estado"] == CAMBIADO),
        DESAPARECIDO: sum(1 for cambio in comparacion if cambio["estado"] == DESAPARECIDO),
        NUEVO: sum(1 for cambio in comparacion if cambio["estado"] == NUEVO),
    }


# --------------------------------------------------------------------------
# Solapes y diferencias de superficie
# --------------------------------------------------------------------------


def texto_del_solape(como: str) -> str:
    return textos.VERSIONES_DE_RECINTO.get(f"solape_{como}", como)


def buscar_solapes(recintos: list[dict]) -> list[schemas.SolapeEntreRecintos]:
    """Qué recintos se pisan entre sí. **Detecta y lo dice; no toca nada.**

    Primero se comparan los rectángulos que envuelven cada forma, que es una cuenta de cuatro
    números: si no se tocan, las formas tampoco, y eso descarta la mayoría de las parejas sin
    calcular nada. Solo cuando los rectángulos se tocan se mira si un vértice de uno cae dentro del
    otro. El porqué de los tres finales (`si`, `puede`, `no`) está en `geo.se_solapan`.

    Un recinto sin forma no se compara con nadie: de él no se sabe ni que sí ni que no, y decir «no
    se pisan» sería afirmar algo que nadie ha comprobado.
    """
    solapes: list[schemas.SolapeEntreRecintos] = []
    con_forma = [
        recinto
        for recinto in recintos
        if recinto.get("geometria") and recinto.get("clave")
    ]
    for indice, uno in enumerate(con_forma):
        for otro in con_forma[indice + 1 :]:
            if uno["clave"] == otro["clave"]:
                # Es el mismo recinto visto dos veces (el del lote y el que ya estaba guardado):
                # compararlo consigo mismo diría que se pisa siempre, y eso no es un solape.
                continue
            como = geo.se_solapan(uno["geometria"], otro["geometria"])
            if como in (geo.SOLAPE_SEGURO, geo.SOLAPE_POSIBLE):
                solapes.append(
                    schemas.SolapeEntreRecintos(
                        clave_a=uno["clave"],
                        clave_b=otro["clave"],
                        referencia_a=uno.get("referencia"),
                        referencia_b=otro.get("referencia"),
                        como=como,
                        como_texto=texto_del_solape(como),
                    )
                )
    return solapes


def diferencia_de_superficie(recinto: dict) -> schemas.DiferenciaDeSuperficie:
    """Qué se llevan entre sí las tres superficies de un recinto, y si eso merece un aviso.

    Las tres magnitudes son distintas **por definición** —la forma que vino, lo que dice el SIGPAC y
    lo que el agricultor declara—, así que una diferencia no es un error: es un motivo para mirar.
    Lo que no se hace nunca es cambiarlas para que cuadren.
    """
    conocidas = [
        valor
        for valor in (
            recinto.get("area_geometria_ha"),
            recinto.get("area_sigpac_ha"),
            recinto.get("area_declarada_ha"),
        )
        if valor is not None
    ]
    comunes = {
        "clave": recinto["clave"],
        "referencia": recinto.get("referencia"),
        "area_geometria_ha": recinto.get("area_geometria_ha"),
        "area_sigpac_ha": recinto.get("area_sigpac_ha"),
        "area_declarada_ha": recinto.get("area_declarada_ha"),
    }
    if len(conocidas) < 2:
        # Con una sola superficie no hay nada que comparar, y eso **no es que cuadre**.
        return schemas.DiferenciaDeSuperficie(
            **comunes, texto=textos.mensaje("R10_sin_dos_superficies")
        )

    diferencia = max(conocidas) - min(conocidas)
    mayor = max(conocidas)
    porcentaje = (diferencia / mayor) if mayor else None
    aviso = porcentaje is not None and porcentaje >= UMBRAL_DE_DIFERENCIA
    texto = (
        textos.mensaje(
            "R11_superficies_que_no_cuadran",
            diferencia=legal.formatea_numero(diferencia, 4),
            porcentaje=legal.formatea_numero((porcentaje or 0) * 100, 1),
        )
        if aviso
        else textos.mensaje(
            "R12_superficies_que_cuadran", diferencia=legal.formatea_numero(diferencia, 4)
        )
    )
    return schemas.DiferenciaDeSuperficie(
        **comunes,
        diferencia_ha=round(diferencia, 6),
        porcentaje=round(porcentaje, 6) if porcentaje is not None else None,
        aviso=aviso,
        texto=texto,
    )


# --------------------------------------------------------------------------
# Preparar el lote: leer, enlazar con las tierras y ver qué cambiaría
# --------------------------------------------------------------------------


class _RecintoPreparado:
    """Un recinto del lote ya leído, enlazado con su tierra y comparado con lo que hay.

    Se llama «preparado» a propósito: **está todo decidido y no se ha escrito nada**. Es lo que hace
    que la previsualización y la aplicación no puedan decir cosas distintas: las dos usan esto.
    """

    def __init__(self, clave: str, entrada: schemas.RecintoDelLote) -> None:
        self.clave = clave
        self.entrada = entrada
        self.numeros: dict = {}
        self.parcela: models.Parcela | None = None
        self.tierra_nueva = False
        self.version: models.VersionDeRecinto | None = None
        self.valores: dict = {}
        self.que_cambia: list[str] = []
        self.estado = NUEVO
        self.saltado: str | None = None
        # **Por qué se saltó**, en código (`R6_recinto_repetido`, `R8_referencia_a_medias`…), y no solo
        # el texto que se le enseña. Hace falta para no pisar un aviso con otro: un lote puede traer el
        # mismo recinto dos veces **y además** una tercera línea que lo contradice, y en ese caso el
        # aviso bueno es el de la contradicción —«no se ha guardado ninguno»—, mientras que el de «se ha
        # tenido en cuenta el primero» hay que poder retirarlo. Sin el código, el programa diría las dos
        # cosas de la misma tierra.
        self.motivo: str | None = None
        # **Con qué se reconoce que dos renglones del lote hablan del mismo recinto**, y qué dice cada
        # uno. Hacen falta juntos: dos renglones del mismo recinto **con los mismos datos** son el
        # mismo apunte repetido (se queda uno, y ya está), y **con datos distintos** son una
        # contradicción (no se guarda ninguno, porque no se sabe cuál es el bueno).
        self.identidad: tuple | None = None
        self.huella: tuple | None = None

    @property
    def parcela_id(self) -> int | None:
        return self.parcela.id if self.parcela is not None else None

    @property
    def tiene_forma(self) -> bool:
        return bool(self.valores.get("geometria"))


def _campana_del_lote(db, explotacion_id: int, lote: schemas.LoteDeRecintosEntrada):
    """La campaña del lote, comprobando que es de esta finca. Falla si no se puede saber cuál es."""
    if lote.campana_id is not None:
        campana = db.get(models.Campana, lote.campana_id)
        if campana is None or campana.explotacion_id != explotacion_id:
            # 404 y no 403: no se dice si ese año existe en otro cuaderno.
            raise LoteQueNoSePuedeAplicar(textos.mensaje("R2_ano_que_no_es_tuyo"), 404)
        return campana
    if lote.anio is not None:
        campana = db.scalar(
            select(models.Campana).where(
                models.Campana.explotacion_id == explotacion_id,
                models.Campana.anio == lote.anio,
            )
        )
        if campana is None:
            raise LoteQueNoSePuedeAplicar(
                textos.mensaje("R3_ano_sin_crear", anio=lote.anio), 404
            )
        return campana
    raise LoteQueNoSePuedeAplicar(textos.mensaje("R1_lote_sin_ano"))


def _fuente_del_lote(lote: schemas.LoteDeRecintosEntrada) -> str:
    """La fuente, comprobando que es una de las que existen. Sin fuente no hay versión."""
    fuente = (lote.fuente or "").strip()
    if fuente not in FUENTES:
        raise LoteQueNoSePuedeAplicar(
            textos.mensaje(
                "R4_fuente_desconocida",
                fuente=fuente or textos.VERSIONES_DE_RECINTO["sin_fuente"],
                fuentes=", ".join(texto_de_la_fuente(conocida) for conocida in FUENTES),
            )
        )
    return fuente


def _tierra_por_la_referencia(db, explotacion_id: int, numeros: dict) -> tuple:
    """La tierra que ya tiene esa referencia, si la tiene. Devuelve `(tierra, cuantas_candidatas)`.

    Se busca primero por la referencia completa, que es como la guarda el programa al traer una tierra
    del SIGPAC (`Parcela.ref_sigpac`). **Y si no aparece por ahí, se buscan sus números**, porque una
    tierra puede tener la referencia escrita de otra manera o no tenerla: el polígono, la parcela y
    **el número de recinto** juntos sí la identifican, y encontrarla es lo que impide dar de alta una
    tierra que ya existe.

    Cuando la referencia viene a medias se busca solo por los números que hay, **y si salen varias
    tierras no se elige ninguna** — quien llama tiene que decir cuál es, porque pegar el recinto en la
    tierra equivocada es peor que no pegarlo.

    **Y lo mismo vale cuando la referencia está completa, que es el caso de este agricultor.** Aquí
    estaba el fallo: se buscaba por la referencia completa con `db.scalar(...)`, que devuelve **la
    primera** que coincida, y se decía que había **una** candidata. Con los datos de verdad eso pega el
    recinto en la tierra equivocada **sin decir nada**: su cuaderno parte un mismo recinto del SIGPAC
    en varias líneas de cultivo, así que hay referencias **completas y válidas** que comparten varias
    tierras (`37-70-0-0-507-24-1` la comparten **nueve**, y `37-70-0-0-507-91-3` seis). Importar un
    lote con esa referencia le colgaba la versión a una de las nueve, elegida por el orden en que
    salieran de la base, y las otras ocho se quedaban sin ella en silencio.

    Ahora, si la referencia completa la tienen varias tierras, se devuelven **como candidatas** y no se
    elige ninguna: quien llama lo dice con `R9_tierra_ambigua` y el recinto se salta, que es lo mismo
    que ya se hacía con las referencias a medias. **No enlazar es recuperable; enlazar mal, no.**

    Esto es lo que cumple «no duplique una tierra que ya existe con la misma referencia: la enlaza»,
    con la salvedad de que **solo se enlaza cuando no hay duda de con cuál**.
    """
    consulta = select(models.Parcela).where(models.Parcela.explotacion_id == explotacion_id)
    completa = referencia_completa(numeros)
    # **Las dos búsquedas se juntan, y una tierra cuenta una sola vez.** Aquí estaba la segunda mitad
    # del fallo (03/10/2026, lo encontró la revisión independiente): si la referencia escrita de la
    # forma canónica la tenía **una** tierra, se devolvía esa y se acababa —sin mirar que hubiera
    # **otra** tierra con los mismos números pero la referencia escrita de otra manera—. El recinto se
    # colgaba de la primera sin decir nada, que es exactamente lo que esta función existe para evitar.
    # Ahora se buscan las dos cosas y, si entre las dos sale más de una tierra, no se elige ninguna.
    candidatas: list[models.Parcela] = []
    vistas: set[int] = set()
    if completa is not None:
        for parcela in db.scalars(consulta.where(models.Parcela.ref_sigpac == completa)):
            candidatas.append(parcela)
            vistas.add(parcela.id)

    filtros = []
    for campo, columna in (
        ("agregado", models.Parcela.agregado),
        ("zona", models.Parcela.zona),
        ("poligono", models.Parcela.poligono),
        ("numero_parcela", models.Parcela.numero_parcela),
        ("numero_recinto", models.Parcela.numero_recinto),
    ):
        if numeros.get(campo) is not None:
            filtros.append(columna == int(numeros[campo]))
    if filtros:
        for parcela in db.scalars(consulta.where(*filtros)):
            if parcela.id not in vistas:
                candidatas.append(parcela)
                vistas.add(parcela.id)

    if len(candidatas) == 1:
        return candidatas[0], 1
    return None, len(candidatas)


def _valores_de_la_entrada(
    entrada: schemas.RecintoDelLote, numeros: dict, campana, fuente: str, fecha_consulta
) -> dict:
    """Los valores que tendría la versión con lo que trae **esta** entrada.

    El área de la forma se calcula; las otras dos se copian de lo que dijo la fuente; y la declarada
    sale **solo** de `entrada.area_declarada_ha`. No hay ninguna línea que copie una de otra.
    """
    geometria = (entrada.geometria or "").strip() or None
    estado = (entrada.estado_revision or "").strip()
    return {
        "campana_id": campana.id,
        "fuente": fuente,
        "fecha_consulta": fecha_consulta,
        "clave": "",
        "referencia": referencia_completa(numeros),
        "provincia": numeros.get("provincia"),
        "municipio": numeros.get("municipio"),
        "agregado": numeros.get("agregado"),
        "zona": numeros.get("zona"),
        "poligono": numeros.get("poligono"),
        "numero_parcela": numeros.get("numero_parcela"),
        "numero_recinto": numeros.get("numero_recinto"),
        "poligono_valido": referencia_completa(numeros) is not None,
        "geometria": geometria,
        "area_geometria_ha": geo.area_ha(geometria),
        "area_sigpac_ha": entrada.area_sigpac_ha,
        "area_declarada_ha": entrada.area_declarada_ha,
        "uso_sigpac": (entrada.uso_sigpac or "").strip() or None,
        "pendiente_pct": entrada.pendiente_pct,
        # **El estado de revisión no lo publica ninguna fuente: lo pone una persona.** Si la entrada
        # no lo dice, se queda en «no lo ha dicho» (`None`) y manda lo que ya hubiera (ver
        # `CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA`). Antes se ponía `sin_revisar` cuando la entrada
        # callaba, y eso **borraba en silencio** que alguien ya lo hubiera revisado: el mismo fallo
        # que llevarse por delante las hectáreas declaradas, pero con otro campo.
        "estado_revision": estado if estado in ESTADOS_DE_REVISION else None,
    }


# Los campos que una importación **nunca borra**: si la entrada no los trae, se queda lo que había.
# Es la misma decisión que en el resto del programa: un dato que no viene no es un dato que se sabe
# que ya no está. Y el caso que más importa es `area_declarada_ha`: la declaró el agricultor, y una
# consulta al SIGPAC que no la mencione no puede llevársela por delante.
CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA = (
    "fecha_consulta",
    "provincia",
    "municipio",
    "agregado",
    "zona",
    "poligono",
    "numero_parcela",
    "numero_recinto",
    "geometria",
    "area_sigpac_ha",
    "area_declarada_ha",
    "uso_sigpac",
    "pendiente_pct",
    # **El estado de revisión, también.** Lo pone una persona —ella o su técnico—, no la fuente que
    # manda el lote: una consulta al SIGPAC que no lo mencione no puede devolver a «sin revisar» algo
    # que ya estaba revisado. Es el mismo motivo por el que no se borra `area_declarada_ha`.
    "estado_revision",
)


def _fundir_con_lo_que_hay(valores: dict, version: models.VersionDeRecinto | None) -> dict:
    """Lo que trae la entrada, más lo que ya estaba y la entrada no menciona.

    Devuelve los valores **finales** de la versión, que son los que se comparan con los guardados
    para saber si hay algo que escribir. Sin esto, la importación repetible no sería medible: la
    segunda aplicación compararía lo que trae la entrada (con huecos) contra lo guardado (sin ellos)
    y creería que hay cambios que no hay.
    """
    if version is None:
        # Una versión **nueva** sí empieza sin revisar: no había nada que conservar. Es el único caso
        # en el que el estado se pone solo.
        nuevos = dict(valores)
        if nuevos.get("estado_revision") is None:
            nuevos["estado_revision"] = "sin_revisar"
        return nuevos
    finales = dict(valores)
    for campo in CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA:
        if finales.get(campo) is None:
            finales[campo] = getattr(version, campo)
    # La clave, la referencia y el área de la forma se recalculan con lo que haya quedado: si la
    # entrada trajo el número de recinto que faltaba, la referencia pasa a estar completa y eso
    # **es** un cambio que hay que escribir. Y si la forma cambia, el área no puede quedarse
    # mintiendo (por eso se calcula aquí y no se copia).
    numeros = {campo: finales.get(campo) for campo in CAMPOS_DE_LA_REFERENCIA}
    finales["clave"] = clave_del_recinto(numeros, finales.get("geometria"))
    finales["referencia"] = referencia_completa(numeros)
    finales["poligono_valido"] = finales["referencia"] is not None
    finales["area_geometria_ha"] = geo.area_ha(finales.get("geometria"))
    return finales


def _que_cambia(valores: dict, version: models.VersionDeRecinto) -> list[str]:
    """Qué se movería si se guardaran estos valores, con el nombre de cada cosa."""
    return que_cambio(
        {campo: getattr(version, campo) for campo, _nombre in CAMPOS_QUE_SE_COMPARAN},
        valores,
    )


def preparar_el_lote(db, explotacion_id: int, lote: schemas.LoteDeRecintosEntrada) -> tuple:
    """Lee el lote entero y lo deja preparado, **sin escribir nada**.

    Devuelve `(campaña, fuente, preparados, problemas)`. Los «problemas» son los recintos que no se
    han podido tener en cuenta, cada uno con su motivo escrito: no se calla ninguno.
    """
    campana = _campana_del_lote(db, explotacion_id, lote)
    fuente = _fuente_del_lote(lote)
    preparados: list[_RecintoPreparado] = []
    problemas: list[str] = []
    tierras_ya_vistas: set = set()

    for indice, entrada in enumerate(lote.recintos, start=1):
        numeros = numeros_de_la_referencia(entrada)
        geometria = (entrada.geometria or "").strip() or None
        clave = clave_del_recinto(numeros, geometria)
        # **Lo que se le enseña al agricultor es la referencia, no la clave.** No son lo mismo: la
        # clave deja en blanco los ceros a propósito (`37-70---507-24-1`), porque para identificar un
        # recinto da igual que el agregado sea 0 o no venga —así una referencia a medias y la misma
        # completa no se tratan como dos—. Pero enseñada como si fuera una referencia es **un número
        # mal escrito**, y el agricultor lo lee y no reconoce su tierra. Se enseña la referencia
        # completa cuando la hay; si no, la clave, que entonces es lo único que identifica al recinto.
        como_se_llama = referencia_completa(numeros) or clave
        if not clave:
            problemas.append(textos.mensaje("R5_recinto_sin_datos", cuantos=indice))
            continue

        preparado = _RecintoPreparado(clave, entrada)
        preparado.numeros = numeros
        # Lo que este renglón dice, para poder comparar dos renglones del mismo recinto sin haberlos
        # resuelto todavía (los que se saltan no llegan a tener `valores`).
        preparado.huella = (
            geometria,
            entrada.area_sigpac_ha,
            entrada.area_declarada_ha,
            (entrada.uso_sigpac or "").strip() or None,
            entrada.pendiente_pct,
            (entrada.estado_revision or "").strip() or None,
        )

        if entrada.parcela_id is not None:
            parcela = db.get(models.Parcela, entrada.parcela_id)
            if parcela is None or parcela.explotacion_id != explotacion_id:
                # 404: no se dice si esa tierra existe en otro cuaderno.
                raise LoteQueNoSePuedeAplicar(textos.mensaje("R7_tierra_ajena"), 404)
            preparado.parcela = parcela
        else:
            parcela, candidatas = _tierra_por_la_referencia(db, explotacion_id, numeros)
            if parcela is not None:
                preparado.parcela = parcela
            elif candidatas > 1:
                # Varias tierras podrían ser: no se elige ninguna.
                preparado.motivo = "R9_tierra_ambigua"
                preparado.saltado = textos.mensaje(
                    preparado.motivo, clave=como_se_llama, cuantas=candidatas
                )
                problemas.append(preparado.saltado)
                preparados.append(preparado)
                continue
            elif referencia_completa(numeros) is None:
                # Una referencia a medias no identifica a nadie, y dar de alta una tierra con ella
                # sería inventarse una tierra. Se dice qué falta.
                preparado.motivo = "R8_referencia_a_medias"
                preparado.saltado = textos.mensaje(preparado.motivo, clave=como_se_llama)
                problemas.append(preparado.saltado)
                preparados.append(preparado)
                continue
            else:
                preparado.tierra_nueva = True

        # Una versión por tierra, campaña y fuente: dos recintos distintos de la misma tierra en el
        # mismo lote son un dato contradictorio, y se dice en vez de guardar el último y callarse.
        identidad = ("tierra", preparado.parcela_id) if preparado.parcela_id else ("ref", clave)
        preparado.identidad = identidad
        if identidad in tierras_ya_vistas:
            preparado.motivo = "R6_recinto_repetido"
            preparado.saltado = textos.mensaje(preparado.motivo, clave=como_se_llama)
            problemas.append(preparado.saltado)
            preparados.append(preparado)
            continue
        tierras_ya_vistas.add(identidad)

        valores = _valores_de_la_entrada(
            entrada, numeros, campana, fuente, lote.fecha_consulta
        )
        valores["clave"] = clave

        version = None
        if preparado.parcela is not None:
            version = db.scalar(
                select(models.VersionDeRecinto).where(
                    models.VersionDeRecinto.explotacion_id == explotacion_id,
                    models.VersionDeRecinto.parcela_id == preparado.parcela.id,
                    models.VersionDeRecinto.campana_id == campana.id,
                    models.VersionDeRecinto.fuente == fuente,
                )
            )
        preparado.version = version
        preparado.valores = _fundir_con_lo_que_hay(valores, version)
        if version is None:
            preparado.estado = NUEVO
            preparado.que_cambia = []
        else:
            preparado.que_cambia = _que_cambia(preparado.valores, version)
            preparado.estado = CAMBIADO if preparado.que_cambia else IGUAL
        preparados.append(preparado)

    # **Y el orden del lote no puede decidir qué se guarda.** Aquí estaba un defecto de verdad (lo
    # encontró la revisión independiente, 03/10/2026): dos renglones del mismo recinto —el modelo
    # guarda **una versión por tierra, campaña y fuente**— y el programa se quedaba con **el primero
    # que llegara** avisando del segundo. Consecuencia: el mismo lote **en otro orden** dejaba guardado
    # otro recinto, así que la importación dejaba de ser repetible, reescribía la versión y apuntaba en
    # auditoría un cambio que nadie había pedido.
    #
    # Ahora se miran los grupos de renglones que hablan del mismo recinto, y hay dos casos que **no**
    # son el mismo:
    #
    #   · **El mismo apunte repetido** (mismos datos): se queda uno y se dice del resto. Es el reenvío
    #     del móvil, y tiene que seguir funcionando sin protestar.
    #   · **Dos renglones que se contradicen** (mismo recinto, datos distintos): **no se guarda
    #     ninguno**, porque no se sabe cuál es el bueno y elegir por el orden en que vengan es elegir a
    #     cara o cruz. Es el mismo principio que con las tierras ambiguas: no guardar es recuperable,
    #     guardar el que no es, no.
    #
    # La identidad vale para las dos cosas: una tierra que ya existe (`("tierra", id)`) y una tierra
    # que se va a dar de alta en esta misma importación (`("ref", clave)`). Faltaba la segunda —lo
    # encontró la revisión— y por eso en una finca **nueva** el orden seguía decidiendo.
    grupos: dict[tuple, list] = {}
    for preparado in preparados:
        if preparado.identidad is not None:
            grupos.setdefault(preparado.identidad, []).append(preparado)
    for miembros in grupos.values():
        if len(miembros) < 2:
            continue
        if len({miembro.huella for miembro in miembros}) == 1:
            continue  # es el mismo apunte repetido: ya se queda el primero y se dice del resto
        for preparado in miembros:
            if preparado.saltado:
                # **Saltado por otro motivo** —su referencia a medias, su tierra ambigua, su recinto sin
                # datos—: su aviso es el suyo y se queda, porque ese es su problema de verdad.
                if preparado.motivo != "R6_recinto_repetido":
                    continue
                # Y si el aviso que tenía era el de «Se ha tenido en cuenta el primero», **aquí ya no es
                # verdad**: en este grupo no se guarda ninguno. Se **sustituye**, y se quita el viejo de
                # la lista de problemas: si no, el programa diría las dos cosas de la misma tierra
                # («vale el primero» y «no vale ninguno»), que es justo lo que no puede pasar.
                if preparado.saltado in problemas:
                    problemas.remove(preparado.saltado)
            preparado.motivo = "R14_dos_recintos_de_la_misma_tierra"
            preparado.saltado = textos.mensaje(
                preparado.motivo,
                clave=preparado.valores.get("referencia") or preparado.clave,
            )
            problemas.append(preparado.saltado)

    return campana, fuente, preparados, problemas


# --------------------------------------------------------------------------
# El plan (la previsualización) y su aplicación
# --------------------------------------------------------------------------


def _recintos_para_mirar(db, explotacion_id: int, campana, fuente: str, preparados: list) -> list[dict]:
    """Los recintos con los que se buscan solapes: los del lote y los que ya están guardados.

    **Por qué también los guardados.** El caso que de verdad importa es el de dos recintos que se
    pisan sin estar los dos en el mismo lote: el agricultor importa hoy el recinto de una tierra y
    el mes que viene el de la de al lado. Comparar solo lo que viene en el lote no vería ese caso.

    **Y por qué se deja fuera lo que ya estaba guardado de estas mismas tierras.** Lo que se compara
    son recintos distintos entre sí. La versión vieja de una tierra que viene en el lote **no es otro
    recinto**: es el mismo, con la forma de antes, y compararla con la nueva diría que «se pisan»
    cuando lo que ha pasado es que el recinto ha cambiado. Eso no es un solape y no se avisa.
    """
    recintos: list[dict] = []
    del_lote = {preparado.clave for preparado in preparados if not preparado.saltado}
    tierras_del_lote = {
        preparado.parcela_id for preparado in preparados if preparado.parcela_id is not None
    }
    for preparado in preparados:
        if preparado.saltado:
            continue
        recintos.append(
            {
                "clave": preparado.clave,
                "referencia": preparado.valores.get("referencia"),
                "geometria": preparado.valores.get("geometria"),
            }
        )
    guardadas = db.scalars(
        select(models.VersionDeRecinto).where(
            models.VersionDeRecinto.explotacion_id == explotacion_id,
            models.VersionDeRecinto.campana_id == campana.id,
            models.VersionDeRecinto.fuente == fuente,
        )
    )
    for version in guardadas:
        if version.clave in del_lote or version.parcela_id in tierras_del_lote:
            continue
        recintos.append(
            {
                "clave": version.clave,
                "referencia": version.referencia,
                "geometria": version.geometria,
            }
        )
    return recintos


def plan_de_importacion(
    db, explotacion_id: int, lote: schemas.LoteDeRecintosEntrada
) -> schemas.PlanDeImportacion:
    """**Qué pasaría** si se importara este lote. No escribe nada: solo lee.

    Es la previsualización que pide el contrato antes de aplicar (T05: «importación repetible sobre
    copia»), y devuelve los cuatro números que hay que mirar antes de decidir: nuevos, cambiados,
    iguales y sin forma.
    """
    campana, fuente, preparados, problemas = preparar_el_lote(db, explotacion_id, lote)
    return _el_plan(db, explotacion_id, campana, fuente, lote, preparados, problemas)


def _el_plan(db, explotacion_id, campana, fuente, lote, preparados, problemas):
    """El plan, ya montado, con los recintos, los solapes y las cuentas de superficie."""
    anios = _anios_de_las_campanas(db, explotacion_id)
    tierras = _nombres_de_las_tierras(db, explotacion_id)
    detalle: list[schemas.RecintoEnElPlan] = []
    for preparado in preparados:
        if preparado.saltado:
            continue
        detalle.append(
            schemas.RecintoEnElPlan(
                clave=preparado.clave,
                estado=preparado.estado,
                estado_texto=texto_del_estado(preparado.estado),
                parcela_id=preparado.parcela_id,
                tierra=tierras.get(preparado.parcela_id) if preparado.parcela_id else None,
                referencia=preparado.valores.get("referencia"),
                poligono_valido=bool(preparado.valores.get("poligono_valido")),
                sin_forma=not preparado.tiene_forma,
                que_cambia=list(preparado.que_cambia),
                area_geometria_ha=preparado.valores.get("area_geometria_ha"),
                area_sigpac_ha=preparado.valores.get("area_sigpac_ha"),
                area_declarada_ha=preparado.valores.get("area_declarada_ha"),
            )
        )

    recintos = _recintos_para_mirar(db, explotacion_id, campana, fuente, preparados)
    diferencias = [
        diferencia_de_superficie(
            {
                "clave": preparado.clave,
                "referencia": preparado.valores.get("referencia"),
                "area_geometria_ha": preparado.valores.get("area_geometria_ha"),
                "area_sigpac_ha": preparado.valores.get("area_sigpac_ha"),
                "area_declarada_ha": preparado.valores.get("area_declarada_ha"),
            }
        )
        for preparado in preparados
        if not preparado.saltado
    ]

    return schemas.PlanDeImportacion(
        campana_id=campana.id,
        anio=anios.get(campana.id),
        fuente=fuente,
        fuente_texto=texto_de_la_fuente(fuente),
        recintos_en_el_lote=len(lote.recintos),
        nuevos=sum(1 for uno in detalle if uno.estado == NUEVO),
        cambiados=sum(1 for uno in detalle if uno.estado == CAMBIADO),
        iguales=sum(1 for uno in detalle if uno.estado == IGUAL),
        sin_forma=sum(1 for uno in detalle if uno.sin_forma),
        # **Solo las que de verdad se van a dar de alta.** Antes contaba también las saltadas, así que el
        # ensayo prometía tierras que al aplicar no se creaban (lo encontró la auditoría del 05/10/2026):
        # el recuento que el agricultor lee **antes de decidir** tiene que ser el mismo que sale después.
        tierras_nuevas=sum(
            1 for preparado in preparados if preparado.tierra_nueva and not preparado.saltado
        ),
        detalle=detalle,
        solapes=buscar_solapes(recintos),
        diferencias_de_superficie=diferencias,
        problemas=problemas,
        aplicada=False,
    )


def aplicar_importacion(
    db,
    explotacion,
    lote: schemas.LoteDeRecintosEntrada,
    usuario_id: int | None = None,
) -> schemas.PlanDeImportacion:
    """Importa el lote de verdad: **idempotente**, y sin inventar nada que no venga.

    Se apoya en el mismo `preparar_el_lote` que la previsualización, así que lo que se enseña antes
    de aplicar y lo que pasa al aplicar salen de la misma cuenta.

    Lo que **no** escribe, y es lo que hace que se pueda aplicar dos veces seguidas:
      · una versión que ya está igual no se toca (ni la fila, ni la fecha, ni la auditoría);
      · un campo que la entrada no trae no se borra;
      · una tierra que ya existe con la misma referencia **se enlaza, no se duplica**.
    """
    campana, fuente, preparados, problemas = preparar_el_lote(db, explotacion.id, lote)

    creadas = 0
    actualizadas = 0
    tierras_creadas: list[int] = []
    for preparado in preparados:
        if preparado.saltado:
            continue
        if preparado.parcela is None:
            # Se apunta en el propio recinto preparado para que el plan que se devuelve diga la
            # tierra de verdad y no un hueco.
            preparado.parcela = dar_de_alta_la_tierra(db, explotacion.id, preparado)
            db.flush()
            tierras_creadas.append(preparado.parcela.id)

        if preparado.version is None:
            db.add(
                models.VersionDeRecinto(
                    explotacion_id=explotacion.id,
                    parcela_id=preparado.parcela.id,
                    **preparado.valores,
                )
            )
            db.add(
                models.Auditoria(
                    explotacion_id=explotacion.id,
                    usuario_id=usuario_id,
                    entidad="version_de_recinto",
                    accion="crear",
                    datos={
                        "parcela_id": preparado.parcela.id,
                        "campana_id": campana.id,
                        "fuente": fuente,
                        "clave": preparado.clave,
                        "referencia": preparado.valores.get("referencia"),
                    },
                )
            )
            creadas += 1
        elif preparado.que_cambia:
            # Lo que había se apunta en la auditoría **antes** de cambiarlo: si un día alguien
            # pregunta por qué esta tierra dice otra cosa, la respuesta está ahí.
            antes = {
                campo: getattr(preparado.version, campo)
                for campo, _nombre in CAMPOS_QUE_SE_COMPARAN
            }
            for campo, valor in preparado.valores.items():
                setattr(preparado.version, campo, valor)
            db.add(
                models.Auditoria(
                    explotacion_id=explotacion.id,
                    usuario_id=usuario_id,
                    entidad="version_de_recinto",
                    entidad_id=preparado.version.id,
                    accion="actualizar",
                    datos={
                        "antes": antes,
                        "ahora": {
                            campo: getattr(preparado.version, campo)
                            for campo, _nombre in CAMPOS_QUE_SE_COMPARAN
                        },
                        "que_cambio": list(preparado.que_cambia),
                    },
                )
            )
            actualizadas += 1

    db.commit()

    plan = _el_plan(db, explotacion.id, campana, fuente, lote, preparados, problemas)
    plan.aplicada = True
    plan.versiones_creadas = creadas
    plan.versiones_actualizadas = actualizadas
    plan.tierras_creadas = tierras_creadas
    plan.tierras_nuevas = len(tierras_creadas)
    return plan


def dar_de_alta_la_tierra(db, explotacion_id: int, preparado: _RecintoPreparado) -> models.Parcela:
    """Da de alta la tierra de un recinto que no existía, **con lo que el lote trae y nada más**.

    Se llama solo cuando la referencia está completa: una tierra sin su referencia no se puede
    reconocer después, y crearla sería inventarse una tierra (además de duplicarla en cuanto llegara
    la buena). El motivo está en `preparar_el_lote`.

    Lo que **no** se hace aquí:
      · **no se copia la superficie del SIGPAC a la que se cultiva** —son magnitudes distintas a
        propósito—: `superficie_ha` es la declarada, y si el lote no la trae, se queda en blanco;
      · **no se toca `superficie_oficial`**: la declarada no es oficial;
      · **no se rellena el alias de nadie**: el alias del agricultor es suyo, y esto solo crea
        tierras nuevas, que todavía no tienen nombre (se les pone uno que sale de la referencia y él
        lo cambia cuando quiera).
    """
    numeros = preparado.numeros
    municipio, provincia, codigo_ine = _el_pueblo_del_recinto(numeros)
    alias = (preparado.entrada.alias or "").strip() or _alias_que_sale_de_la_referencia(numeros)
    parcela = models.Parcela(
        explotacion_id=explotacion_id,
        alias=alias[:120],
        ref_sigpac=preparado.valores.get("referencia"),
        provincia=provincia,
        municipio=municipio,
        codigo_ine=codigo_ine,
        agregado=numeros.get("agregado") or 0,
        zona=numeros.get("zona") or 0,
        poligono=numeros.get("poligono"),
        numero_parcela=numeros.get("numero_parcela"),
        numero_recinto=numeros.get("numero_recinto"),
        # La que se cultiva: la declarada, y si no se sabe, en blanco (nunca 0, hallazgo A7).
        superficie_ha=preparado.valores.get("area_declarada_ha"),
        superficie_oficial=False,
        superficie_sigpac_ha=preparado.valores.get("area_sigpac_ha"),
        uso_sigpac=preparado.valores.get("uso_sigpac"),
        pendiente_pct=preparado.valores.get("pendiente_pct"),
        geometria=preparado.valores.get("geometria"),
    )
    db.add(parcela)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion_id,
            entidad="parcela",
            accion="crear_desde_un_lote_de_recintos",
            datos={
                "ref_sigpac": parcela.ref_sigpac,
                "superficie_ha": parcela.superficie_ha,
                "superficie_sigpac_ha": parcela.superficie_sigpac_ha,
            },
        )
    )
    return parcela


def _el_pueblo_del_recinto(numeros: dict) -> tuple[str, str, str | None]:
    """El nombre del pueblo y de la provincia, **si el listado oficial los conoce**.

    El SIGPAC manda los códigos numéricos del municipio y de la provincia, y esos son los del INE,
    así que con el listado que ya tiene el programa se sabe el nombre. Es la misma cuenta que hace
    el alta de una tierra desde el SIGPAC (`routers/parcelas.py`), y **si no se encuentran, se
    quedan en blanco**: no se deduce la provincia del nombre de un pueblo.
    """
    provincia = numeros.get("provincia")
    municipio = numeros.get("municipio")
    if provincia is None or municipio is None:
        return "", "", None
    try:
        codigo = f"{int(provincia):02d}{int(municipio):03d}"
    except (TypeError, ValueError):
        return "", "", None
    encontrado = catalogos.municipio_por_codigo_ine(codigo)
    if encontrado is None:
        return "", "", None
    return encontrado.nombre, encontrado.provincia, encontrado.codigo_ine


def _alias_que_sale_de_la_referencia(numeros: dict) -> str:
    """Un nombre para una tierra recién traída, sacado de su referencia.

    Es el mismo criterio que usa el alta desde el SIGPAC —«Parcela 503, recinto 1»—, y no es un
    nombre inventado: son los números del recinto del agricultor. Él lo cambia por el nombre con el
    que llama a esa tierra cuando quiera.

    Se llama **solo cuando la referencia está completa** (una tierra no se da de alta con una
    referencia a medias: no se podría reconocer después), así que los dos números están siempre.
    """
    return f"Parcela {numeros['numero_parcela']}, recinto {numeros['numero_recinto']}"


# --------------------------------------------------------------------------
# Leer las versiones y compararlas (lo que usan las rutas)
# --------------------------------------------------------------------------


def _anios_de_las_campanas(db, explotacion_id: int) -> dict:
    return {
        campana.id: campana.anio
        for campana in db.scalars(
            select(models.Campana).where(models.Campana.explotacion_id == explotacion_id)
        )
    }


def _nombres_de_las_tierras(db, explotacion_id: int) -> dict:
    return {
        parcela.id: parcela.alias
        for parcela in db.scalars(
            select(models.Parcela).where(models.Parcela.explotacion_id == explotacion_id)
        )
    }


def como_salida(
    version: models.VersionDeRecinto, anios: dict, tierras: dict
) -> schemas.VersionDeRecintoSalida:
    """Una versión, con los nombres ya resueltos y la frase que dice cómo está.

    La frase (`como_esta`) es lo que hace visible el recinto **sin forma**: no se calla ni se le
    dibuja un cuadro. Es la regla del contrato («un polígono ausente no se inventa») contada en
    castellano.
    """
    tiene_forma = bool(version.geometria)
    return schemas.VersionDeRecintoSalida(
        id=version.id,
        parcela_id=version.parcela_id,
        tierra=tierras.get(version.parcela_id),
        campana_id=version.campana_id,
        anio=anios.get(version.campana_id),
        fuente=version.fuente,
        fuente_texto=texto_de_la_fuente(version.fuente),
        fecha_consulta=version.fecha_consulta,
        clave=version.clave,
        referencia=version.referencia,
        provincia=version.provincia,
        municipio=version.municipio,
        agregado=version.agregado,
        zona=version.zona,
        poligono=version.poligono,
        numero_parcela=version.numero_parcela,
        numero_recinto=version.numero_recinto,
        poligono_valido=version.poligono_valido,
        geometria=version.geometria,
        tiene_forma=tiene_forma,
        area_geometria_ha=version.area_geometria_ha,
        area_sigpac_ha=version.area_sigpac_ha,
        area_declarada_ha=version.area_declarada_ha,
        uso_sigpac=version.uso_sigpac,
        pendiente_pct=version.pendiente_pct,
        estado_revision=version.estado_revision,
        estado_texto=texto_del_estado_de_revision(version.estado_revision),
        como_esta=_como_esta(version, tiene_forma),
        creada_en=version.creada_en,
    )


def _como_esta(version: models.VersionDeRecinto, tiene_forma: bool) -> str:
    """La frase que dice de un vistazo cómo está esta versión."""
    if not tiene_forma:
        return textos.VERSIONES_DE_RECINTO["como_esta_sin_forma"]
    if not version.poligono_valido:
        return textos.VERSIONES_DE_RECINTO["como_esta_referencia_a_medias"]
    return texto_del_estado_de_revision(version.estado_revision)


def _como_diccionario(version: models.VersionDeRecinto) -> dict:
    """Los datos comparables de una versión, sin nombres resueltos ni nada de la base."""
    return {
        "clave": version.clave,
        "parcela_id": version.parcela_id,
        "fuente": version.fuente,
        "referencia": version.referencia,
        **{campo: getattr(version, campo) for campo, _nombre in CAMPOS_QUE_SE_COMPARAN},
    }


def listar(
    db,
    explotacion_id: int,
    parcela_id: int | None = None,
    campana_id: int | None = None,
    fuente: str | None = None,
) -> list[schemas.VersionDeRecintoSalida]:
    """Las versiones de una tierra o de toda la finca, con sus nombres ya resueltos.

    **Con la lista se ve el grupo «sin forma»**, que es lo que pide el contrato: un recinto sin
    polígono no desaparece de la tabla, sale con su `tiene_forma` en falso y su frase.
    """
    consulta = (
        select(models.VersionDeRecinto)
        .where(models.VersionDeRecinto.explotacion_id == explotacion_id)
        .order_by(
            models.VersionDeRecinto.parcela_id,
            models.VersionDeRecinto.campana_id.desc(),
            models.VersionDeRecinto.clave,
        )
    )
    if parcela_id is not None:
        consulta = consulta.where(models.VersionDeRecinto.parcela_id == parcela_id)
    if campana_id is not None:
        consulta = consulta.where(models.VersionDeRecinto.campana_id == campana_id)
    if fuente is not None:
        consulta = consulta.where(models.VersionDeRecinto.fuente == fuente)
    anios = _anios_de_las_campanas(db, explotacion_id)
    tierras = _nombres_de_las_tierras(db, explotacion_id)
    return [como_salida(version, anios, tierras) for version in db.scalars(consulta)]


def comparar_dos_campanas(
    db,
    explotacion_id: int,
    campana_antes,
    campana_despues,
    parcela_id: int | None = None,
    fuente: str | None = None,
) -> schemas.ComparacionDeVersiones:
    """`igual / cambiado / desaparecido / nuevo` entre dos campañas, con el porqué.

    Se puede pedir de **una tierra** (la ficha de una parcela) o de **toda la explotación**. Lo que
    hace es leer las versiones de las dos campañas y llamar a `comparar`, que es una función pura:
    **esta consulta no escribe nada**, así que se puede pedir tantas veces como haga falta antes de
    decidir.
    """
    def _leer(campana_id: int) -> list[models.VersionDeRecinto]:
        consulta = select(models.VersionDeRecinto).where(
            models.VersionDeRecinto.explotacion_id == explotacion_id,
            models.VersionDeRecinto.campana_id == campana_id,
        )
        if parcela_id is not None:
            consulta = consulta.where(models.VersionDeRecinto.parcela_id == parcela_id)
        if fuente is not None:
            consulta = consulta.where(models.VersionDeRecinto.fuente == fuente)
        return list(db.scalars(consulta))

    objetos_antes = _leer(campana_antes.id)
    objetos_despues = _leer(campana_despues.id)
    cambios = comparar(
        [_como_diccionario(version) for version in objetos_antes],
        [_como_diccionario(version) for version in objetos_despues],
    )
    cuantos = cuantos_por_estado(cambios)
    anios = {campana_antes.id: campana_antes.anio, campana_despues.id: campana_despues.anio}
    tierras = _nombres_de_las_tierras(db, explotacion_id)
    por_identidad_antes = {_identidad(_como_diccionario(v)): v for v in objetos_antes}
    por_identidad_despues = {_identidad(_como_diccionario(v)): v for v in objetos_despues}

    detalle: list[schemas.CambioDeUnRecinto] = []
    for cambio in cambios:
        identidad = (cambio["parcela_id"], cambio["fuente"])
        antes = por_identidad_antes.get(identidad)
        despues = por_identidad_despues.get(identidad)
        detalle.append(
            schemas.CambioDeUnRecinto(
                clave=cambio["clave"] or "",
                parcela_id=cambio["parcela_id"],
                tierra=tierras.get(cambio["parcela_id"]),
                fuente=cambio["fuente"],
                fuente_texto=texto_de_la_fuente(cambio["fuente"]),
                estado=cambio["estado"],
                estado_texto=cambio["estado_texto"],
                referencia=cambio["referencia"],
                que_cambio=cambio["que_cambio"],
                antes=como_salida(antes, anios, tierras) if antes is not None else None,
                despues=como_salida(despues, anios, tierras) if despues is not None else None,
            )
        )
    return schemas.ComparacionDeVersiones(
        parcela_id=parcela_id,
        tierra=tierras.get(parcela_id) if parcela_id is not None else None,
        campana_antes=campana_antes.id,
        anio_antes=campana_antes.anio,
        campana_despues=campana_despues.id,
        anio_despues=campana_despues.anio,
        fuente=fuente,
        iguales=cuantos[IGUAL],
        cambiados=cuantos[CAMBIADO],
        desaparecidos=cuantos[DESAPARECIDO],
        nuevos=cuantos[NUEVO],
        cambios=detalle,
        resumen=textos.mensaje(
            "R13_resumen_de_la_comparacion",
            iguales=cuantos[IGUAL],
            cambiados=cuantos[CAMBIADO],
            desaparecidos=cuantos[DESAPARECIDO],
            nuevos=cuantos[NUEVO],
        ),
    )
