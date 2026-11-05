"""**Los datos del armazón nuevo** (`IMP-1`, 05/11/2026).

La interfaz nueva se sirve aparte, en `/nuevo/`, y la vieja sigue viva en `/`. Este módulo es la
mitad de servidor de esa app nueva: **dos respuestas ligeras con datos de verdad**, pensadas para que
la pantalla de inicio («hoy» y «tierras») se pueda pintar sin cruzar cinco listas en el navegador.

## Las cuatro reglas que gobiernan todo lo de aquí

1. **Nada se inventa.** Un dato que no está se queda en `None` (o en la lista vacía), nunca en un
   cero, en una cadena vacía rellena o en un nombre parecido. Es la regla de la casa (`AGENTS.md`
   §3.3) y en una pantalla de resumen es donde más fácil se rompe: un «0 ha» o un «0 apuntes» parece
   información y es una afirmación falsa.
2. **Las hectáreas no se suman saltándose una tierra.** El total de la finca sale de
   `superficies.la_superficie_de_la_finca`, que devuelve `None` **si a alguna tierra le falta la
   superficie**: un total al que le falta un sumando no es un total más pequeño, es un total que no
   se sabe (`app/superficies.py`). La pantalla nueva tiene que poder enseñar «no lo sabemos».
3. **Aislamiento entre fincas.** Todas las consultas llevan `explotacion_id` por delante, y la
   campaña que se pide se coge con `deps.obtener_de_la_explotacion` (404 y no 403, para no decir si
   un identificador existe en otro cuaderno). Una finca no ve las tierras de otra ni por la lista ni
   por la campaña.
4. **Los nombres son del agricultor.** El alias de la tierra, la especie y la variedad se devuelven
   tal y como están guardados. Lo único que se compone aquí es el **título corto** de un apunte, y
   sale siempre de un dato guardado (el producto, el abono, la etiqueta del trabajo o la semilla),
   con una palabra llana de respaldo cuando no hay ninguno.

## Lo que este módulo NO hace, y por qué

  · **No filtra, no busca y no pagina.** La pantalla nueva ya tiene los datos; filtrar en el servidor
    obligaría a una llamada por tecla y a decidir en dos sitios qué es «el mismo municipio».
  · **No calcula superficies nuevas.** Devuelve la cultivada y la del recinto tal y como están, que
    son dos magnitudes distintas a propósito (`models.Parcela`), y ninguna se deduce de la forma.
  · **No decide qué campaña está «activa» con el reloj.** Coge la más nueva de la finca, que es la
    misma decisión que ya toman `/api/campanas/actual` y `/api/cultivos`: si el agricultor todavía no
    ha creado la del año, la activa es la que tiene abierta y no una inventada con el año de hoy.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import catalogos, geo, models, superficies
from .deps import obtener_de_la_explotacion

# Cuántos apuntes recientes se devuelven en «hoy», y cuántos años atrás en la ficha de una tierra.
# Son números del contrato del armazón, no una preferencia: la pantalla de inicio tiene cinco huecos
# y la ficha de la tierra enseña tres años de rotación.
CUANTOS_ULTIMOS = 5
CUANTOS_ANIOS_ATRAS = 3

# Las cuatro clases de apunte que se mezclan en «lo último». Son las mismas que ya se apuntan en el
# cuaderno viejo; los códigos viajan así porque son los del contrato de la interfaz nueva.
TIPO_LABOR = "labor"
TIPO_TRATAMIENTO = "tratamiento"
TIPO_SIEMBRA = "siembra"
TIPO_FERTILIZACION = "fertilizacion"

# Lo que se pone cuando un apunte no tiene tierra (una nave, un almacén, un medio de transporte).
# Está pedido tal cual por el contrato y se dice con estas palabras, no con un hueco vacío.
SIN_TIERRA = "sin tierra"

# Las palabras de respaldo del título de un apunte, cuando el dato que lo describe no está. **No son
# datos inventados**: son la clase de apunte, y ninguna de ellas afirma nada sobre el campo.
TITULO_DE_RESPALDO = {
    TIPO_LABOR: "Trabajo",
    TIPO_TRATAMIENTO: "Producto aplicado",
    TIPO_SIEMBRA: "Siembra",
    TIPO_FERTILIZACION: "Abono",
}


# --------------------------------------------------------------------------- piezas comunes


def la_campana_activa(
    db: Session, explotacion_id: int, campana_id: int | None = None
) -> models.Campana | None:
    """La campaña pedida, o **la más nueva de esta finca**. `None` si la finca no tiene ninguna.

    Si viene un identificador, se comprueba que es de esta finca con `obtener_de_la_explotacion`:
    preguntar por la campaña de otro cuaderno da **404**, que es lo que impide usar este endpoint
    para averiguar si un identificador existe en otra finca.
    """
    if campana_id is not None:
        return obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion_id)
    return db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion_id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )


# Las coordenadas viajan con **seis decimales**, que son unos 10 cm en Castilla y León. No es una
# manía: la media de los vértices deja colas de coma flotante (`41.004999999999995`) que no dicen
# nada del campo y sí ensucian la respuesta, y un píxel de mapa no distingue más. Redondear aquí, una
# sola vez, evita que cada pantalla decida por su cuenta cuántos decimales enseñar.
DECIMALES_DE_LA_COORDENADA = 6


def _la_coordenada(valor: float) -> float:
    """Una coordenada, con los decimales del contrato (unos 10 cm)."""
    return round(valor, DECIMALES_DE_LA_COORDENADA)


def _la_campana(campana: models.Campana | None) -> dict:
    """La campaña como la espera la pantalla: `{"id": …, "anio": …}`, o los dos en `None`."""
    return {
        "id": campana.id if campana is not None else None,
        "anio": campana.anio if campana is not None else None,
    }


def _la_finca(explotacion: models.Explotacion) -> dict:
    """El nombre de la finca y su sitio. **Vacío es `None`, no una cadena vacía.**

    `Explotacion.municipio` y `provincia` nacen con `""` porque así lo hace la base, y una cadena
    vacía en una pantalla se lee como «hay un municipio» cuando no hay ninguno. Se convierten aquí,
    una sola vez, en vez de obligar a cada pantalla a acordarse.
    """
    return {
        "nombre": explotacion.nombre,
        "municipio": explotacion.municipio or None,
        "provincia": explotacion.provincia or None,
    }


def _las_hectareas(parcelas: list[models.Parcela]) -> float | None:
    """La superficie cultivada de esas tierras, **o `None` si a alguna le falta**.

    Se delega en `superficies.la_superficie_de_la_finca` a propósito: es la función que ya se usa en
    el panel y en el cuaderno, y tener aquí una suma propia sería la forma de que un día la pantalla
    nueva dijera un total y la vieja otro.
    """
    return superficies.la_superficie_de_la_finca(parcelas)["total"]


def _las_tierras(db: Session, explotacion_id: int) -> list[models.Parcela]:
    """Todas las tierras de la finca, por nombre y por identificador (el orden que se ve en la lista)."""
    return list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion_id)
            .order_by(models.Parcela.alias, models.Parcela.id)
        )
    )


# --------------------------------------------------------------------------- «hoy»


def _titulo_del_apunte(tipo: str, apunte, semillas: dict[int, models.Semilla]) -> str:
    """El título corto de un apunte, **sacado de un dato guardado** y nunca de una suposición.

    Cada clase de apunte se describe con lo que el agricultor reconoce de ese apunte: el producto que
    echó, el abono que gastó, la etiqueta del trabajo que hizo o la semilla que sembró. Si ese dato no
    está (una labor apuntada sin cultivo, un tratamiento sin producto), se dice la clase de apunte y
    se calla: poner un nombre parecido sería inventar lo que pasó en el campo.
    """
    if tipo == TIPO_TRATAMIENTO:
        return apunte.producto_nombre or apunte.plaga or TITULO_DE_RESPALDO[tipo]
    if tipo == TIPO_FERTILIZACION:
        return apunte.fertilizante_nombre or TITULO_DE_RESPALDO[tipo]
    if tipo == TIPO_LABOR:
        # La etiqueta del tipo de trabajo está en `catalogos.ETIQUETA_LABOR` (la misma que se enseña
        # en la agenda del cuaderno viejo): no se escribe aquí una segunda lista que pueda discrepar.
        return catalogos.ETIQUETA_LABOR.get(apunte.tipo) or apunte.cultivo or TITULO_DE_RESPALDO[tipo]
    if tipo == TIPO_SIEMBRA:
        semilla = semillas.get(apunte.semilla_id)
        return (semilla.especie if semilla is not None else None) or TITULO_DE_RESPALDO[tipo]
    return TITULO_DE_RESPALDO.get(tipo, "")


def _los_ultimos_apuntes(db: Session, explotacion_id: int) -> list[dict]:
    """Los apuntes más recientes de la finca, del más nuevo al más viejo, **como mucho cinco**.

    Se juntan las cuatro clases de apunte que el agricultor ve en su agenda (labores, tratamientos,
    siembras y abonos), se descartan los anulados —**un apunte anulado no pasó**, y enseñarlo en el
    resumen sería contradecir el cuaderno— y se ordena por fecha, que es lo que significa «último».
    Si dos apuntes son del mismo día, el desempate es por identificador: es arbitrario entre tablas
    distintas, pero **es estable**, y un resumen que cambia de orden sin que cambie nada es peor.

    Las siembras sin fecha no entran: no se pueden colocar en una lista ordenada por fecha, y ponerles
    la de hoy sería inventarse el día en que se sembró.
    """
    apuntes: list[tuple[dt.date, int, dict]] = []

    def _añadir(tipo: str, apunte, titulo: str) -> None:
        apuntes.append(
            (
                apunte.fecha,
                apunte.id,
                {
                    "tipo": tipo,
                    "fecha": apunte.fecha.isoformat(),
                    "tierra": tierras.get(apunte.parcela_id) or SIN_TIERRA,
                    "titulo": titulo,
                },
            )
        )

    # La tierra de cada apunte, resuelta de una vez: se pregunta por todas las tierras de la finca y
    # no una consulta por apunte.
    tierras = {
        parcela.id: parcela.alias
        for parcela in db.scalars(
            select(models.Parcela).where(models.Parcela.explotacion_id == explotacion_id)
        )
    }
    semillas = {
        semilla.id: semilla
        for semilla in db.scalars(
            select(models.Semilla).where(models.Semilla.explotacion_id == explotacion_id)
        )
    }

    labores = db.scalars(
        select(models.Labor)
        .where(
            models.Labor.explotacion_id == explotacion_id,
            models.Labor.anulado.is_(False),
        )
        .order_by(models.Labor.fecha.desc(), models.Labor.id.desc())
        .limit(CUANTOS_ULTIMOS)
    )
    for labor in labores:
        _añadir(TIPO_LABOR, labor, _titulo_del_apunte(TIPO_LABOR, labor, semillas))

    tratamientos = db.scalars(
        select(models.TratamientoFitosanitario)
        .where(
            models.TratamientoFitosanitario.explotacion_id == explotacion_id,
            models.TratamientoFitosanitario.anulado.is_(False),
        )
        .order_by(
            models.TratamientoFitosanitario.fecha.desc(),
            models.TratamientoFitosanitario.id.desc(),
        )
        .limit(CUANTOS_ULTIMOS)
    )
    for tratamiento in tratamientos:
        _añadir(
            TIPO_TRATAMIENTO, tratamiento, _titulo_del_apunte(TIPO_TRATAMIENTO, tratamiento, semillas)
        )

    siembras = db.scalars(
        select(models.Siembra)
        .where(
            models.Siembra.explotacion_id == explotacion_id,
            models.Siembra.anulada.is_(False),
            models.Siembra.fecha.is_not(None),
        )
        .order_by(models.Siembra.fecha.desc(), models.Siembra.id.desc())
        .limit(CUANTOS_ULTIMOS)
    )
    for siembra in siembras:
        _añadir(TIPO_SIEMBRA, siembra, _titulo_del_apunte(TIPO_SIEMBRA, siembra, semillas))

    abonos = db.scalars(
        select(models.RegistroFertilizacion)
        .where(
            models.RegistroFertilizacion.explotacion_id == explotacion_id,
            models.RegistroFertilizacion.anulado.is_(False),
        )
        .order_by(
            models.RegistroFertilizacion.fecha.desc(),
            models.RegistroFertilizacion.id.desc(),
        )
        .limit(CUANTOS_ULTIMOS)
    )
    for abono in abonos:
        _añadir(TIPO_FERTILIZACION, abono, _titulo_del_apunte(TIPO_FERTILIZACION, abono, semillas))

    apuntes.sort(key=lambda uno: (uno[0], uno[1]), reverse=True)
    return [uno[2] for uno in apuntes[:CUANTOS_ULTIMOS]]


def hoy(db: Session, *, explotacion: models.Explotacion, usuario: models.Usuario) -> dict:
    """Lo que la pantalla de inicio necesita para saludar y enseñar el día, en una sola llamada."""
    campana = la_campana_activa(db, explotacion.id)
    tierras = _las_tierras(db, explotacion.id)
    return {
        "finca": _la_finca(explotacion),
        "campana": _la_campana(campana),
        "cuenta": {"nombre": usuario.nombre, "correo": usuario.correo},
        "tierras": {"n": len(tierras), "ha": _las_hectareas(tierras)},
        "ultimos": _los_ultimos_apuntes(db, explotacion.id),
    }


# --------------------------------------------------------------------------- «tierras»


def _el_anillo(parcela: models.Parcela) -> list[list[float]] | None:
    """Los puntos del WKT en `[[longitud, latitud], …]`, o `None` si la tierra no tiene forma.

    `None` no es un error: una tierra apuntada a mano no se dibuja, y la pantalla lo dice. Devolver
    una lista vacía obligaría a cada pantalla a distinguir «no tiene forma» de «la forma está vacía»,
    que es el mismo error que ya se arregló en el mapa del cuaderno viejo.
    """
    puntos = geo.puntos_del_wkt(parcela.geometria)
    if not puntos:
        return None
    return [[_la_coordenada(longitud), _la_coordenada(latitud)] for longitud, latitud in puntos]


def _el_centro(parcela: models.Parcela) -> list[float] | None:
    """El centro de la tierra, o `None` si no hay forma con la que calcularlo."""
    centro = geo.centroide_wkt(parcela.geometria)
    return [_la_coordenada(centro[0]), _la_coordenada(centro[1])] if centro is not None else None


def _el_rectangulo(parcelas: list[models.Parcela]) -> list[float] | None:
    """El rectángulo que envuelve las tierras de un municipio: `[oeste, sur, este, norte]`.

    Se calcula con **los puntos de las tierras que tienen forma**; las que no la tienen no aportan
    nada y no se sustituyen por un punto inventado en mitad de la provincia. Si ninguna tiene forma,
    el municipio va sin rectángulo y el mapa lo dice en vez de abrirse en otro sitio.
    """
    puntos = [punto for parcela in parcelas for punto in geo.puntos_del_wkt(parcela.geometria)]
    if not puntos:
        return None
    longitudes = [punto[0] for punto in puntos]
    latitudes = [punto[1] for punto in puntos]
    return [
        _la_coordenada(min(longitudes)),
        _la_coordenada(min(latitudes)),
        _la_coordenada(max(longitudes)),
        _la_coordenada(max(latitudes)),
    ]


def _los_cultivos(db: Session, explotacion_id: int) -> dict[int, dict[int, tuple]]:
    """Lo sembrado, indexado por tierra y por campaña: `{parcela_id: {campana_id: (cultivo, anio)}}`.

    Se trae de una vez todo lo de la finca y se cruza en memoria: son decenas de filas, y una consulta
    por tierra y año sería la forma de que una lista de 64 tierras hiciera 64 consultas.
    """
    por_tierra: dict[int, dict[int, tuple]] = defaultdict(dict)
    filas = db.execute(
        select(models.ParcelaCultivo, models.Campana.anio)
        .join(models.Campana, models.Campana.id == models.ParcelaCultivo.campana_id)
        .where(models.ParcelaCultivo.explotacion_id == explotacion_id)
    ).all()
    for cultivo, anio in filas:
        por_tierra[cultivo.parcela_id][cultivo.campana_id] = (cultivo, anio)
    return por_tierra


def _el_cultivo(sembrado: dict[int, tuple] | None) -> dict | None:
    """El cultivo de la campaña activa, tal y como está guardado (sin variedad si no la hay)."""
    if not sembrado:
        return None
    cultivo, _anio = sembrado
    return {"nombre": cultivo.especie, "variedad": cultivo.variedad}


def _los_otros_anios(
    por_campana: dict[int, tuple], campana: models.Campana | None
) -> list[dict]:
    """Hasta tres campañas anteriores con su cultivo, de la más nueva a la más vieja.

    **Solo las que tienen cultivo declarado.** Un año sin nada apuntado no se rellena con un
    «sin datos» que parezca un cultivo: simplemente no está en la lista, y la pantalla enseña los que
    hay. La superficie de cada año es **la cultivada de ese cultivo** (`ParcelaCultivo`), no la de la
    tierra, y va en `None` cuando no consta.
    """
    if campana is None:
        return []
    anteriores = [
        (anio, cultivo)
        for campana_id, (cultivo, anio) in por_campana.items()
        if campana_id != campana.id and anio < campana.anio
    ]
    anteriores.sort(key=lambda par: par[0], reverse=True)
    return [
        {
            "anio": anio,
            "cultivo": cultivo.especie,
            "superficie_ha": cultivo.superficie_cultivada_ha,
            "variedad": cultivo.variedad,
        }
        for anio, cultivo in anteriores[:CUANTOS_ANIOS_ATRAS]
    ]


def _una_tierra(parcela: models.Parcela, por_campana: dict[int, tuple], campana) -> dict:
    """Una tierra como la espera la pantalla nueva, con su forma y su rotación."""
    sembrado = por_campana.get(campana.id) if campana is not None else None
    return {
        "id": parcela.id,
        "alias": parcela.alias,
        "municipio": parcela.municipio,
        "provincia": parcela.provincia,
        "superficie_ha": parcela.superficie_ha,
        "superficie_sigpac_ha": parcela.superficie_sigpac_ha,
        "uso_sigpac": parcela.uso_sigpac,
        # **Los tres atributos del SIGPAC que están llegando en paralelo** (`coef_regadio`, `region`,
        # `admisibilidad`) se leen con `getattr` para que esta puerta funcione igual antes y después
        # de que existan las columnas: si todavía no están, valen `None` y la pantalla lo dice. El
        # Lead limpiará el `getattr` cuando el otro compañero termine (`IMP-1`, 05/11/2026).
        "coef_regadio": getattr(parcela, "coef_regadio", None),
        "region": getattr(parcela, "region", None),
        "admisibilidad": getattr(parcela, "admisibilidad", None),
        "centro": _el_centro(parcela),
        "anillo": _el_anillo(parcela),
        "cultivo": _el_cultivo(sembrado),
        "otros_anios": _los_otros_anios(por_campana, campana),
    }


def _los_municipios(parcelas: list[models.Parcela]) -> list[dict]:
    """Las tierras agrupadas por municipio, con su recuento, sus hectáreas y su rectángulo.

    Se agrupa por el **texto tal y como está guardado**, que es lo que el agricultor escribió o lo que
    trajo el cuaderno de la Junta: juntar «Peñaranda» y «Peñaranda de Bracamonte» sería decidir por él
    que son el mismo sitio. Una tierra **sin municipio** cae en el grupo de nombre vacío, que es la
    forma de que la suma de los grupos sea siempre la de la finca (y de que ninguna tierra desaparezca
    de la pantalla por no tener pueblo).

    El orden es de más tierras a menos, y a igualdad por nombre: es el orden en el que se leen los
    filtros, y así no cambia de sitio cada vez que se abre la pantalla.
    """
    por_municipio: dict[str, list[models.Parcela]] = defaultdict(list)
    for parcela in parcelas:
        por_municipio[parcela.municipio].append(parcela)
    grupos = [
        {
            "nombre": municipio,
            "n": len(suyas),
            "ha": _las_hectareas(suyas),
            "bbox": _el_rectangulo(suyas),
        }
        for municipio, suyas in por_municipio.items()
    ]
    grupos.sort(key=lambda grupo: (-grupo["n"], grupo["nombre"]))
    return grupos


def tierras(
    db: Session,
    *,
    explotacion: models.Explotacion,
    campana_id: int | None = None,
) -> dict:
    """Las tierras de la finca, agrupadas por municipio y con lo que hay sembrado en cada una."""
    campana = la_campana_activa(db, explotacion.id, campana_id)
    las_tierras = _las_tierras(db, explotacion.id)
    cultivos = _los_cultivos(db, explotacion.id)
    municipios = _los_municipios(las_tierras)
    return {
        "campana": _la_campana(campana),
        "finca": {
            "nombre": explotacion.nombre,
            "municipio": explotacion.municipio or None,
        },
        "totales": {
            "n": len(las_tierras),
            "ha": _las_hectareas(las_tierras),
            # El número de municipios es **el número de grupos** que se devuelven, para que la
            # pantalla no pueda enseñar un recuento que no cuadre con las filas de al lado.
            "municipios": len(municipios),
        },
        "municipios": municipios,
        "tierras": [
            _una_tierra(parcela, cultivos.get(parcela.id, {}), campana) for parcela in las_tierras
        ],
    }
