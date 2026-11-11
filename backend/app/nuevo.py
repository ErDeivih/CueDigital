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
import io
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import HTTPException

from .guia import lo_que_toca
from . import catalogos, dinero, gastos, geo, iuws, models, superficies
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


# ===========================================================================
# IMP-4 · Importar el cuaderno del cliente, el resumen y «qué falta» (05/11/2026)
# ===========================================================================
#
# David lo pidió por este orden: *(2) importar el cuaderno digital de un cliente y reconocer la
# parcela automáticamente*, *(5) gastos e ingresos* y *(7) un cuaderno guiado que diga qué falta*.
#
# **Lo que NO se hace aquí, y es lo que más importa: repetir la lógica que ya está.** La lectura del
# Cuecyl, la importación idempotente, las cuentas de las ventas y el informe de lo que falta llevan
# rondas escritas y probadas; estas tres puertas **las llaman**. Si esto se copiara, un día la
# pantalla nueva y la vieja dirían cosas distintas de la misma finca, que es el fallo que este
# programa persigue en todas partes.

# Cuántos ejemplos de lo que falta se enseñan en el resumen. El listado entero tiene su propia
# puerta (`/api/nuevo/que-falta`), y el resumen es un resumen.
LIMITE_DE_EJEMPLOS = 3


def _como_si_lo_acabaran_de_subir(contenido: bytes, nombre: str | None):
    """El fichero en la forma que espera la función de leer del cuaderno (`UploadFile`).

    Hace falta porque el fichero se lee **dos veces** con la misma función de la casa: una para
    decir qué trae (sin escribir nada) y otra para importarlo. Volver a envolver los mismos bytes es
    más honesto que tener dos lectores: uno que enseña y otro que apunta podrían no coincidir.
    """
    from fastapi import UploadFile

    return UploadFile(file=io.BytesIO(contenido), filename=nombre or "")


# Los datos del titular que el cuaderno trae y que la función de la casa **no** copia a propósito
# (`cuaderno_cyl_api._rellenar_los_huecos_del_titular`): el nombre y el NIF. El motivo escrito allí
# sigue siendo bueno —el cuaderno escribe el NIF con el formato de su registro, «0-70922320-A», que no
# es un DNI— y por eso aquí **se normaliza** antes de rellenarlo, en vez de copiarlo tal cual.
#
# **El municipio no está en esta lista, y no es un olvido**: la hoja 1.1 del cuaderno trae la
# localidad y la provincia, que sí se copian, pero **no trae el municipio**. Deducirlo del nombre de
# la localidad sería inventar (una localidad puede pertenecer a un municipio con otro nombre), y la
# casa ya prohíbe deducir la provincia del nombre de un municipio (`AGENTS.md` §3.3). El municipio se
# pide en la pantalla de la finca. Queda dicho en el informe de la tarea.
CAMPOS_QUE_LA_CASA_NO_COPIA = ("nombre", "NIF")


def _el_nif_del_papel(nif: str | None) -> str | None:
    """El NIF del cuaderno en la forma de un documento: «0-70922320-A» → «70922320A».

    Se quitan los guiones, los espacios y los ceros de la izquierda, que son del **formato del
    registro de la Junta** y no del documento. Si lo que queda no tiene la forma de un NIF español
    (nueve caracteres), se devuelve `None`: **no se rellena el NIF con algo que no lo parece**, porque
    es el dato que identifica al titular delante de la administración.
    """
    limpio = re.sub(r"[^0-9A-Za-z]", "", nif or "").upper()
    if len(limpio) > 9 and limpio[0].isdigit():
        limpio = limpio.lstrip("0")
    return limpio if len(limpio) == 9 else None


def _rellenar_lo_que_la_casa_no_copia(db: Session, explotacion, generales) -> list[str]:
    """Rellena el nombre y el NIF del titular **solo si estaban vacíos**, y dice qué ha rellenado.

    Lo que el agricultor ya había escrito no se toca nunca: si él puso su nombre de una manera, manda
    la suya. Es la misma regla que la función de la casa, aplicada a los dos campos que aquella deja
    fuera a propósito (ver `CAMPOS_QUE_LA_CASA_NO_COPIA`).
    """
    rellenados: list[str] = []
    if generales.nombre and not (explotacion.nombre or "").strip():
        explotacion.nombre = generales.nombre.strip()
        rellenados.append("nombre")
    if not (explotacion.nif or "").strip():
        nif = _el_nif_del_papel(generales.nif)
        if nif is not None:
            explotacion.nif = nif
            rellenados.append("NIF")
    if rellenados:
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                entidad="explotacion",
                entidad_id=explotacion.id,
                accion="rellenar_el_titular_desde_el_cuaderno",
                datos={"campos": rellenados},
            )
        )
        db.commit()
    return rellenados


async def importar_cuaderno(db: Session, *, explotacion, fichero) -> dict:
    """**Leer el cuaderno, rellenar la finca e importar las tierras, todo en una llamada.**

    Es la puerta que hace que el agricultor nuevo no teclee nada: sube el fichero que descarga de la
    Junta y se queda con sus tierras y con los datos de su finca puestos. Devuelve **en una sola
    respuesta** lo que traía el fichero, lo que se ha apuntado, lo que se ha rellenado de la finca, lo
    que falta del cuaderno y cómo ha quedado la finca en números — que es lo que la pantalla necesita
    para decir «ya está» sin pedir nada más.

    **Repetir la llamada no duplica nada**: la importación de la casa reconoce cada tierra por su
    referencia del SIGPAC, su cultivo y sus hectáreas. Es lo que se prueba en
    `tests/test_nuevo_importar.py`.
    """
    from .routers import cuaderno_cyl_api

    contenido = await fichero.read()
    nombre = fichero.filename

    # 1 · Se lee, con la misma función que `/api/cuaderno-cyl/leer` (y su 422 con mensaje).
    leido = await cuaderno_cyl_api._leer_lo_que_han_subido(
        _como_si_lo_acabaran_de_subir(contenido, nombre)
    )

    # 2 · Se importa, con la misma función que `/api/cuaderno-cyl/importar`. El permiso de modificar
    #     lo ha comprobado ya la dependencia de la puerta (`PuedeModificar`), por eso aquí va `None`:
    #     no es que no se compruebe, es que se comprobó antes de abrir el fichero.
    importado = await cuaderno_cyl_api.importar_el_cuaderno(
        explotacion=explotacion,
        db=db,
        puede_modificar=None,
        fichero=_como_si_lo_acabaran_de_subir(contenido, nombre),
    )

    # 3 · Y los dos huecos que la función de la casa no toca (nombre y NIF), con su normalización.
    rellenados_extra = _rellenar_lo_que_la_casa_no_copia(db, explotacion, leido.generales)
    finca_actualizada = list(importado.titular_rellenado) + rellenados_extra

    # 4 · Los números y lo que falta, ya con la finca al día.
    campana = (
        db.get(models.Campana, importado.campana_id)
        if importado.campana_id is not None
        else None
    )
    las_tierras = _las_tierras(db, explotacion.id)
    return {
        "leido": {
            "anio": leido.anio,
            "titular": leido.generales.nombre,
            "nif": leido.generales.nif,
            "registro_autonomico": leido.generales.registro_autonomico or None,
            "localidad": leido.generales.localidad or None,
            "resumen": leido.resumen(),
            "avisos": list(leido.avisos),
        },
        "importado": importado.model_dump(),
        "finca_actualizada": finca_actualizada,
        "que_falta": _lo_que_falta_resumido(_las_faltas(db, explotacion, campana)),
        "tierras": {
            "n": len(las_tierras),
            "ha": _las_hectareas(las_tierras),
            "municipios": len(_los_municipios(las_tierras)),
        },
    }


# --------------------------------------------------------------------------- lo que falta


def _las_faltas(db: Session, explotacion, campana: models.Campana | None) -> list[dict]:
    """Todo lo que falta, con **dónde se arregla** y si bloquea. Ni una cosa inventada.

    Son dos listas y las dos son de verdad:

      1. **Lo que falta en el cuaderno** (el informe del escritor del Cuecyl): qué dato pide cada hoja
         y no está puesto, y en qué pantalla se pone. `bloquea` es `False` porque no impide nada:
         el agricultor puede descargar su cuaderno con huecos y rellenarlos después.
      2. **Lo que falta para presentarlo en la Junta** (`iuws.QUE_FALTA`): los catálogos oficiales,
         el alta del dominio, el certificado y el código SIEX. Eso **sí bloquea** el volcado, y lo
         dice cada uno en su ficha. Aquí el «dónde se arregla» es **de quién depende**, que es lo que
         ya dice el propio módulo (`quien`): FEGA, David o cada agricultor.

    Si la finca no tiene ninguna campaña no hay cuaderno que comparar, y se devuelven solo los del
    interfaz: **no se inventa una campaña para poder contar más cosas**.
    """
    from .cuaderno_cyl_exportar import escribe_el_cuaderno

    items: list[dict] = []
    if campana is not None:
        escrito = escribe_el_cuaderno(db, explotacion, campana)
        items.extend(
            {"que": falta.que_falta, "donde": falta.donde_se_pone, "bloquea": False}
            for falta in escrito.faltan
        )
    items.extend(
        {"que": falta.que, "donde": falta.quien, "bloquea": falta.bloquea}
        for falta in iuws.QUE_FALTA
    )
    return items


def _lo_que_falta_resumido(items: list[dict]) -> dict:
    """El resumen de lo que falta: cuántas hay y los primeros ejemplos, **de la misma lista**."""
    return {
        "faltan": len(items),
        "ejemplos": [uno["que"] for uno in items[:LIMITE_DE_EJEMPLOS]],
    }


def que_falta(db: Session, *, explotacion) -> dict:
    """**Qué le falta a esta finca para tener el cuaderno entero y para poder presentarlo.**"""
    campana = la_campana_activa(db, explotacion.id)
    items = _las_faltas(db, explotacion, campana)
    return {"faltan": len(items), "items": items}


# --------------------------------------------------------------------------- el resumen


def _numero(valor) -> float | None:
    """Un importe de la casa (texto decimal o `Decimal`) al número del contrato nuevo.

    **El resto del programa lleva el dinero en texto decimal** a propósito (contrato §2: un `float`
    pierde céntimos antes de entrar). El contrato de esta pantalla pide números, así que la conversión
    se hace **aquí, una sola vez y al final**: las cuentas se hacen con `Decimal` y solo el número que
    viaja al navegador es `float`. `None` sigue siendo `None`: un importe que no consta no es un cero.
    """
    cantidad = dinero.a_decimal(valor)
    return None if cantidad is None else float(cantidad)


def _de_la_campana(consulta, campana: models.Campana | None):
    """Acota a la campaña cuando se está mirando un año. Sin campaña, se mira la finca entera."""
    if campana is None:
        return consulta
    return consulta.where(models.Gasto.campana_id == campana.id)


def _la_cuenta_de_los_gastos(db: Session, explotacion, campana) -> dict:
    """Qué se ha gastado y qué queda por pagar, **con la cuenta que ya hace la pantalla de cuentas**.

    Se le pasan a `gastos.cuenta_de_la_explotacion` los gastos de la campaña con lo que se ha pagado de
    cada uno (la misma función que usa su ficha), y ella decide: si algún gasto no dice lo que costó,
    **el total es `None`** — `gastos_sin_importe` lo cuenta y el pendiente ya lo devuelve vacío—. Sumar
    solo los que se conocen daría una cifra más pequeña que la de verdad.
    """
    from . import servicios

    filas = []
    consulta = select(models.Gasto).where(models.Gasto.explotacion_id == explotacion.id)
    for gasto in db.scalars(_de_la_campana(consulta, campana)):
        filas.append(
            {
                "anulado": bool(gasto.anulado),
                "importe": gasto.importe,
                "pagado": servicios.lo_pagado_de_un_gasto(
                    db, explotacion_id=explotacion.id, gasto_id=gasto.id
                ),
            }
        )
    cuenta = gastos.cuenta_de_la_explotacion(gastos=filas)
    return {
        "total": None if cuenta.gastos_sin_importe else _numero(cuenta.coste_conocido),
        "pendiente": _numero(cuenta.pendiente),
    }


def _la_cuenta_de_las_ventas(db: Session, explotacion, campana) -> dict:
    """Lo vendido, lo cobrado y lo que falta por cobrar, **con la cuenta de la pantalla de ventas**.

    Se llama a la función del router de ventas (`_el_dinero_de_la_campana`) en vez de repetir su
    consulta: es la que sabe que una entrega con importe pero sin facturar **no** es dinero pendiente
    de cobro. Si alguna entrega no dice su importe, el total y el pendiente no se saben (`None`); lo
    cobrado sí, porque un cobro siempre trae su importe.
    """
    from .routers import ventas_api

    if campana is None:
        return {"total": 0.0, "cobrado": 0.0, "pendiente": 0.0}
    suyo = ventas_api._el_dinero_de_la_campana(db, explotacion, campana)
    sin_importe = suyo["sin_importe"]
    return {
        "total": None if sin_importe else _numero(suyo["importe"]),
        "cobrado": _numero(suyo["cobrado"]),
        "pendiente": None if sin_importe else _numero(suyo["pendiente"]),
    }


def resumen(db: Session, *, explotacion) -> dict:
    """**El dinero de la finca en la campaña que se está llevando, y lo que falta del cuaderno.**

    Cada número va por su lado y no se suman entre ellos: lo gastado y lo vendido son dinero de signo
    distinto y de naturaleza distinta, y el cuaderno no es dinero. Y `facturas` cuenta las facturas de
    compra del año (las anuladas no), que es lo que el agricultor llama «tener los papeles».
    """
    campana = la_campana_activa(db, explotacion.id)
    items = _las_faltas(db, explotacion, campana)
    consulta_facturas = select(models.Factura).where(
        models.Factura.explotacion_id == explotacion.id,
        models.Factura.anulada.is_(False),
    )
    if campana is not None:
        consulta_facturas = consulta_facturas.where(models.Factura.campana_id == campana.id)
    return {
        "gastos": _la_cuenta_de_los_gastos(db, explotacion, campana),
        "ventas": _la_cuenta_de_las_ventas(db, explotacion, campana),
        "cuaderno": _lo_que_falta_resumido(items),
        "facturas": {"n": len(list(db.scalars(consulta_facturas)))},
    }


# ===========================================================================
# IMP-6 · La ficha de la tierra, el calendario y los filtros por tipo (05/11/2026)
# ===========================================================================
#
# David lo pidió en este orden: **tierra primero** (elegir la tierra y ver qué se ha hecho **hoy**
# sobre ella), **historial** por años con las cantidades por hectárea y los meses del abono, **calendario**
# por días y **filtros por tipo de trabajo** con las tierras y las cantidades de toda la explotación.
#
# **De dónde sale cada cosa, y por qué no se inventa nada**:
#
#   · **La labor del día** son las `Labor` (con su `tipo` y su apero en `subtipo`), que es donde el
#     agricultor apunta «hoy he pasado el cultivador». Una cosecha **también es una labor**
#     (`tipo="cosecha"`), y sus kilos viven en sus `detalles` (`{"producto", "cantidad_kg"}`), que es
#     donde los deja `routers/registros._preparar_cosecha_guardable`.
#   · **La siembra** puede estar en dos sitios: la `Labor` de tipo siembra (el trabajo del día) y la
#     ficha de la semilla (`Siembra`, que además dice la dosis y el lote). No se suman ni se duplican:
#     si las dos hablan del **mismo día y la misma tierra**, es el mismo hecho y se cuenta una vez
#     (se queda la labor, que es el apunte del día, y la ficha de la semilla aporta la dosis). Está
#     escrito abajo, en `_los_apuntes`.
#   · **Las cantidades por hectárea no se recalculan a mano**: se usa `superficies.la_dosis_por_hectarea`,
#     que es la única cuenta de la casa que divide una cantidad por una superficie y sabe cuándo **no**
#     se puede (`None` si falta alguno de los dos).
#
# **Lo que el vocabulario del programa NO tiene, y conviene decirlo**: el apero «vertedera» no existe en
# el catálogo del programa (`trabajos.SUBTIPOS_DE_LABOREO`: rodillo, cultivador, arado, grada, fresadora
# y otro). El equivalente que el agricultor puede apuntar es **arado**. Aquí **no se traduce una cosa en
# la otra** —sería inventar una equivalencia—: los filtros salen del vocabulario de verdad, y si se
# quiere decir «vertedera» se cambia la etiqueta en el catálogo y sale sola en las tres puertas.

# Las claves de los apuntes que no son labores.
CLAVE_LABOR = "labor"
CLAVE_SIEMBRA = "siembra"
CLAVE_TRATAMIENTO = "tratamiento"
CLAVE_ABONO = "abono"
CLAVE_COSECHA = "cosecha"
CLAVE_OTROS = "otros"

# Un rango de calendario mayor que un año no es un calendario: es una consulta que devolvería miles de
# filas para pintar una rejilla que el agricultor no puede mirar. Se dice con un 422 y su motivo.
MAXIMO_DE_DIAS_EN_EL_CALENDARIO = 366


def _la_etiqueta_de_un_tipo(clave: str) -> str:
    """El nombre llano de un tipo de trabajo, **sacado del catálogo que ya existe**.

    Las labores tienen su etiqueta en `catalogos.ETIQUETA_LABOR` (la misma que se enseña en la agenda
    del cuaderno viejo) y los aperos se escriben con su propia palabra («arado», «grada»): son las que
    el agricultor dice. **No se inventa un texto nuevo aquí**: lo que se lee en pantalla es cosa de la
    pantalla nueva; esto es la etiqueta del dato.
    """
    return catalogos.ETIQUETA_LABOR.get(clave) or (clave or "").replace("_", " ").capitalize()


def _la_suma_de_hectareas(valores: list[float | None]) -> float | None:
    """La suma de las hectáreas, **o `None` si a algún apunte le falta**.

    Es la regla de la casa (`superficies.py`): un total al que le falta un sumando no es un total más
    pequeño, es un total que no se sabe. Así la pantalla puede decir «no lo sabemos» en vez de enseñar
    una cifra que se queda corta.
    """
    if any(valor is None for valor in valores):
        return None
    return round(sum(float(valor) for valor in valores), 4)


def _el_apero_de_una_labor(labor: models.Labor) -> str | None:
    """El apero de una labor de suelo (arado, cultivador, grada…), **leído como lo lee la casa**.

    El dato puede estar en la columna `Labor.subtipo` o, mientras la columna no se rellene, dentro de
    `Labor.detalles["subtipo"]` —así lo guarda hoy el asistente—. En vez de mirar los dos sitios aquí
    otra vez, se pregunta a la función que ya sabe hacerlo (`routers/trabajos_api._el_subtipo`): si
    mañana cambia dónde vive, cambia en un solo sitio y estas puertas lo ven.
    """
    from .routers.trabajos_api import _el_subtipo

    return _el_subtipo(labor)


def _la_clave_de_una_labor(labor: models.Labor) -> str:
    """Con qué nombre se filtra una labor: **su apero si es una labor de suelo, y si no su tipo**.

    Es lo que David llama «tipo de trabajo»: un pase de cultivador se filtra por `cultivador`, no por
    «laboreo» (que no le dice nada); una poda, por `poda`. Los valores salen del catálogo, así que si
    mañana se añade un apero sale solo.
    """
    from . import trabajos

    apero = _el_apero_de_una_labor(labor)
    if labor.tipo == "laboreo" and apero in trabajos.SUBTIPOS_DE_LABOREO:
        return apero
    return labor.tipo or CLAVE_OTROS


def _el_apunte_de_una_labor(labor: models.Labor) -> dict:
    """Una labor normalizada, con lo que necesitan las tres puertas y nada inventado."""
    clave = _la_clave_de_una_labor(labor)
    es_cosecha = labor.tipo == CLAVE_COSECHA
    detalles = labor.detalles if isinstance(labor.detalles, dict) else {}
    kg = detalles.get("cantidad_kg") if es_cosecha else None
    producto = detalles.get("producto") if es_cosecha else None
    if clave == "riego":
        cantidad, unidad = labor.volumen_agua, labor.unidad_agua
    else:
        cantidad, unidad = None, None
    return {
        "tipo": CLAVE_COSECHA if es_cosecha else CLAVE_LABOR,
        "clave": CLAVE_COSECHA if es_cosecha else clave,
        "fecha": labor.fecha,
        "titulo": (
            (f"Cosecha de {producto}" if producto else catalogos.ETIQUETA_LABOR.get(CLAVE_COSECHA, "Cosecha"))
            if es_cosecha
            else _la_etiqueta_de_un_tipo(clave)
        ),
        "detalle": labor.cultivo or producto or None,
        "parcela_id": labor.parcela_id,
        "campana_id": labor.campana_id,
        "cantidad": kg if es_cosecha else cantidad,
        "unidad": "kg" if es_cosecha else unidad,
        "hectareas": labor.superficie_ha,
        "por_hectarea": None,  # se rellena después, cuando se sabe la superficie
        "unidad_por_hectarea": "kg/ha" if es_cosecha else None,
        "producto": producto,
        "materia_activa": None,
        "dosis": None,
        "dosis_unidad": None,
        "kg": kg,
        "kg_ha": None,
        "mes": labor.fecha.month if labor.fecha else None,
        "cultivo": labor.cultivo,
        "variedad": labor.variedad,
        "dosis_semilla_kg_ha": labor.dosis_siembra_kg_ha,
        "labor_clave": clave,
    }


def _el_apunte_de_una_siembra(siembra: models.Siembra, semillas: dict) -> dict:
    """La ficha de una semilla sembrada, normalizada.

    **Sin fecha no entra en el historial ni en el calendario**: no se puede colocar en un día, y ponerle
    la de hoy sería inventarse cuándo se sembró. La dosis viaja en su unidad tal y como se apuntó, y la
    de kg/ha solo se da cuando la dosis está en kilos por hectárea (no se convierte una dosis en
    unidades a kilos: eso sería un número inventado).
    """
    semilla = semillas.get(siembra.semilla_id)
    especie = (semilla.especie if semilla is not None else None) or ""
    variedad = (semilla.variedad if semilla is not None else None) or None
    unidad_dosis = siembra.unidad_dosis or (semilla.unidad_dosis if semilla is not None else None)
    dosis_kg_ha = siembra.dosis_por_ha if (unidad_dosis or "").lower() in ("kg/ha", "kg / ha") else None
    return {
        "tipo": CLAVE_SIEMBRA,
        "clave": CLAVE_SIEMBRA,
        "fecha": siembra.fecha,
        "titulo": " · ".join(parte for parte in (especie or None, variedad) if parte) or "Siembra",
        "detalle": f"Lote {siembra.lote_id}" if siembra.lote_id else None,
        "parcela_id": siembra.parcela_id,
        "campana_id": None,  # la siembra no cuelga del año; se coloca por su fecha
        "cantidad": siembra.cantidad_total,
        "unidad": siembra.unidad_cantidad,
        "hectareas": siembra.superficie_ha,
        "por_hectarea": siembra.dosis_por_ha,
        "unidad_por_hectarea": unidad_dosis,
        "producto": especie or None,
        "materia_activa": None,
        "dosis": siembra.dosis_por_ha,
        "dosis_unidad": unidad_dosis,
        "kg": None,
        "kg_ha": None,
        "mes": siembra.fecha.month if siembra.fecha else None,
        "cultivo": especie or None,
        "variedad": variedad,
        "dosis_semilla_kg_ha": dosis_kg_ha,
        "labor_clave": CLAVE_SIEMBRA,
    }


def _el_apunte_de_un_tratamiento(tratamiento: models.TratamientoFitosanitario) -> dict:
    """Un tratamiento, con su producto, su dosis y la superficie tratada de ese día."""
    return {
        "tipo": CLAVE_TRATAMIENTO,
        "clave": CLAVE_TRATAMIENTO,
        "fecha": tratamiento.fecha,
        "titulo": tratamiento.producto_nombre or tratamiento.plaga or "Producto aplicado",
        "detalle": tratamiento.materia_activa or tratamiento.plaga or None,
        "parcela_id": tratamiento.parcela_id,
        "campana_id": tratamiento.campana_id,
        "cantidad": tratamiento.cantidad_total,
        "unidad": tratamiento.unidad_cantidad_aplicada,
        "hectareas": tratamiento.superficie_tratada_ha,
        "por_hectarea": tratamiento.dosis,
        "unidad_por_hectarea": tratamiento.unidad_dosis,
        "producto": tratamiento.producto_nombre,
        "materia_activa": tratamiento.materia_activa,
        "dosis": tratamiento.dosis,
        "dosis_unidad": tratamiento.unidad_dosis,
        # **Hasta cuándo dura el plazo de seguridad** (11/11/2026): la cuenta atrás del apunte. La
        # fecha sale de la del tratamiento más los días que decía la etiqueta; si el plazo no está
        # apuntado, se queda en `None` (no se inventa una fecha).
        "plazo_seguridad_dias": tratamiento.plazo_seguridad_dias,
        "plazo_hasta": (
            (tratamiento.fecha + dt.timedelta(days=int(tratamiento.plazo_seguridad_dias))).isoformat()
            if tratamiento.fecha is not None and tratamiento.plazo_seguridad_dias is not None
            else None
        ),
        "kg": None,
        "kg_ha": None,
        "mes": tratamiento.fecha.month if tratamiento.fecha else None,
        "cultivo": tratamiento.cultivo,
        "variedad": tratamiento.variedad,
        "dosis_semilla_kg_ha": None,
        "labor_clave": CLAVE_TRATAMIENTO,
    }


def _el_apunte_de_un_abono(abono: models.RegistroFertilizacion) -> dict:
    """Un abono, con sus kilos y su dosis por hectárea **tal y como se apuntó**."""
    return {
        "tipo": CLAVE_ABONO,
        "clave": CLAVE_ABONO,
        "fecha": abono.fecha,
        "titulo": abono.fertilizante_nombre or "Abono",
        "detalle": abono.tipo or None,
        "parcela_id": abono.parcela_id,
        "campana_id": abono.campana_id,
        "cantidad": abono.cantidad_total_kg,
        "unidad": "kg" if abono.cantidad_total_kg is not None else None,
        "hectareas": abono.superficie_ha,
        "por_hectarea": abono.kg_ha_producto,
        "unidad_por_hectarea": "kg/ha" if abono.kg_ha_producto is not None else None,
        "producto": abono.fertilizante_nombre,
        "materia_activa": None,
        "dosis": abono.kg_ha_producto,
        "dosis_unidad": "kg/ha" if abono.kg_ha_producto is not None else None,
        "kg": abono.cantidad_total_kg,
        "kg_ha": abono.kg_ha_producto,
        "mes": abono.fecha.month if abono.fecha else None,
        "cultivo": None,
        "variedad": None,
        "dosis_semilla_kg_ha": None,
        "labor_clave": CLAVE_ABONO,
    }


def _los_apuntes(
    db: Session,
    explotacion_id: int,
    *,
    parcela_id: int | None = None,
    desde=None,
    hasta=None,
    campana: models.Campana | None = None,
) -> list[dict]:
    """Todos los apuntes de la finca (o de una tierra) que caen en lo que se pide, normalizados.

    Se junta lo que el agricultor apunta de verdad —labores, siembras, tratamientos y abonos—, se
    descarta **lo anulado** (un apunte anulado no pasó) y se ordena por fecha. Las siembras sin fecha
    no entran: no hay día en el que ponerlas.

    **La siembra apuntada dos veces no se cuenta dos veces**: si el mismo día y en la misma tierra hay
    una labor de tipo siembra y una ficha de semilla, es el mismo hecho visto desde dos sitios; se queda
    la labor y la ficha aporta la dosis. Sin esa regla, el filtro de `siembra` enseñaría dos filas del
    mismo día con la misma tierra, y eso es exactamente lo que hace desconfiar de un cuaderno.
    """
    parcelas = {
        parcela.id: parcela
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
    filas: list[dict] = []

    consulta_labores = select(models.Labor).where(
        models.Labor.explotacion_id == explotacion_id,
        models.Labor.anulado.is_(False),
    )
    if parcela_id is not None:
        consulta_labores = consulta_labores.where(models.Labor.parcela_id == parcela_id)
    if campana is not None:
        consulta_labores = consulta_labores.where(models.Labor.campana_id == campana.id)
    if desde is not None:
        consulta_labores = consulta_labores.where(models.Labor.fecha >= desde)
    if hasta is not None:
        consulta_labores = consulta_labores.where(models.Labor.fecha <= hasta)
    for labor in db.scalars(consulta_labores):
        filas.append(_el_apunte_de_una_labor(labor))

    consulta_tratamientos = select(models.TratamientoFitosanitario).where(
        models.TratamientoFitosanitario.explotacion_id == explotacion_id,
        models.TratamientoFitosanitario.anulado.is_(False),
    )
    if parcela_id is not None:
        consulta_tratamientos = consulta_tratamientos.where(
            models.TratamientoFitosanitario.parcela_id == parcela_id
        )
    if campana is not None:
        consulta_tratamientos = consulta_tratamientos.where(
            models.TratamientoFitosanitario.campana_id == campana.id
        )
    if desde is not None:
        consulta_tratamientos = consulta_tratamientos.where(
            models.TratamientoFitosanitario.fecha >= desde
        )
    if hasta is not None:
        consulta_tratamientos = consulta_tratamientos.where(
            models.TratamientoFitosanitario.fecha <= hasta
        )
    for tratamiento in db.scalars(consulta_tratamientos):
        filas.append(_el_apunte_de_un_tratamiento(tratamiento))

    consulta_abonos = select(models.RegistroFertilizacion).where(
        models.RegistroFertilizacion.explotacion_id == explotacion_id,
        models.RegistroFertilizacion.anulado.is_(False),
    )
    if parcela_id is not None:
        consulta_abonos = consulta_abonos.where(
            models.RegistroFertilizacion.parcela_id == parcela_id
        )
    if campana is not None:
        consulta_abonos = consulta_abonos.where(
            models.RegistroFertilizacion.campana_id == campana.id
        )
    if desde is not None:
        consulta_abonos = consulta_abonos.where(models.RegistroFertilizacion.fecha >= desde)
    if hasta is not None:
        consulta_abonos = consulta_abonos.where(models.RegistroFertilizacion.fecha <= hasta)
    for abono in db.scalars(consulta_abonos):
        filas.append(_el_apunte_de_un_abono(abono))

    # Las siembras no cuelgan de la campaña: se colocan por su fecha, y sin fecha no se colocan.
    consulta_siembras = select(models.Siembra).where(
        models.Siembra.explotacion_id == explotacion_id,
        models.Siembra.anulada.is_(False),
        models.Siembra.fecha.is_not(None),
    )
    if parcela_id is not None:
        consulta_siembras = consulta_siembras.where(models.Siembra.parcela_id == parcela_id)
    if desde is not None:
        consulta_siembras = consulta_siembras.where(models.Siembra.fecha >= desde)
    if hasta is not None:
        consulta_siembras = consulta_siembras.where(models.Siembra.fecha <= hasta)
    if campana is not None:
        consulta_siembras = consulta_siembras.where(
            models.Siembra.fecha >= campana.fecha_inicio,
            models.Siembra.fecha <= campana.fecha_fin,
        )
    for siembra in db.scalars(consulta_siembras):
        filas.append(_el_apunte_de_una_siembra(siembra, semillas))

    # La siembra que ya tiene su labor el mismo día, en la misma tierra, no se repite.
    siembras_con_su_labor = {
        (fila["parcela_id"], fila["fecha"])
        for fila in filas
        if fila["tipo"] == CLAVE_LABOR and fila["clave"] == CLAVE_SIEMBRA
    }
    filas = [
        fila
        for fila in filas
        if not (
            fila["tipo"] == CLAVE_SIEMBRA
            and (fila["parcela_id"], fila["fecha"]) in siembras_con_su_labor
        )
    ]

    # La dosis por hectárea de una cosecha, con la superficie de la labor o, si no la trae, la de la
    # tierra: una cosecha se apunta sobre la tierra entera y sin ella no hay kg/ha que dar.
    for fila in filas:
        if fila["tipo"] == CLAVE_COSECHA:
            superficie = fila["hectareas"]
            if superficie is None and fila["parcela_id"] in parcelas:
                superficie = parcelas[fila["parcela_id"]].superficie_ha
                fila["hectareas"] = superficie
            fila["por_hectarea"] = superficies.la_dosis_por_hectarea(
                cantidad=fila["cantidad"], superficie_tratada_ha=superficie
            )
            fila["kg_ha"] = fila["por_hectarea"]
        fila["parcela_alias"] = (
            parcelas[fila["parcela_id"]].alias if fila["parcela_id"] in parcelas else SIN_TIERRA
        )
        fila["municipio"] = (
            parcelas[fila["parcela_id"]].municipio if fila["parcela_id"] in parcelas else ""
        )

    filas.sort(key=lambda fila: (fila["fecha"], fila["tipo"], fila["parcela_id"] or 0), reverse=True)
    return filas


def _el_apunte_para_la_agenda(fila: dict) -> dict:
    """Un apunte con la forma de `trabajo_de_hoy` y del calendario: lo justo para pintarlo."""
    return {
        "tipo": fila["tipo"],
        "titulo": fila["titulo"],
        "tierra_id": fila["parcela_id"],
        "tierra_alias": fila["parcela_alias"],
        "cantidad": fila["cantidad"],
        "unidad": fila["unidad"],
        "hectareas": fila["hectareas"],
    }


def _el_resumen_de_un_anio(elemento: dict, n_apuntes: int) -> dict:
    """**El resumen de un año del historial**, para poder comparar dos años de un vistazo.

    Lo que dice, y lo que **no** hace:

      · `abonos_kg_ha` es **la suma de las dosis por hectárea** de los abonos de ese año (una suma de
        intensidades, no de kilos: los kilos de cada abono se ven en su fila). Si a **alguno** le
        falta su kg/ha, la suma es **`None`**: una suma a la que le falta un sumando no es una suma,
        es una cifra que miente por pequeña. Sin abonos es `0.0`, que es la verdad de ese año.
      · `abonos_meses` son los meses en los que se abonó, **ordenados y sin repetir**.
      · `cosecha_kg_ha` es el kg/ha de la cosecha del año, o `None` si no hubo o si no se sabe. **No se
        rellena con la de otro año.**
      · `siembra` dice si ese año tiene siembra apuntada (en la labor del día o en la ficha de la
        semilla: las dos cuentan como la siembra del año).
    """
    dosis = [abono["kg_ha"] for abono in elemento["abonos"]]
    falta_alguna = any(una is None for una in dosis)
    abonos_kg_ha = None if falta_alguna else round(sum(float(una) for una in dosis), 4)
    cosecha = elemento["cosecha"] or {}
    return {
        "n_apuntes": n_apuntes,
        "n_labores": len(elemento["labores"]),
        "n_tratamientos": len(elemento["tratamientos"]),
        "abonos_kg_ha": abonos_kg_ha,
        "abonos_meses": sorted(
            {abono["mes"] for abono in elemento["abonos"] if abono["mes"] is not None}
        ),
        "cosecha_kg_ha": cosecha.get("kg_ha"),
        "siembra": elemento["siembra"] is not None,
    }


def _el_historial(filas: list[dict], cultivos_por_anio: dict[int, dict]) -> list[dict]:
    """El historial de una tierra: **un elemento por año con datos, del más nuevo al más viejo**.

    No se rellena un año vacío: si en 2023 no hay nada apuntado, 2023 no está. Y cada año lleva lo que
    de verdad hay —siembra, labores, tratamientos, abonos y cosecha—, con la dosis por hectárea y el
    mes del abono, que es lo que David pidió ver.

    El año de un apunte es **el de su campaña** cuando la trae (es la campaña que eligió el agricultor)
    y, si no, el de su fecha. Una siembra no cuelga de ninguna campaña, así que va por su fecha.
    """
    anios: dict[int, dict] = {}
    # Cuántos apuntes tiene cada año, que es lo que dice el `resumen` de ese año. Se cuenta al pasar
    # (incluida la ficha de la semilla, que es un apunte aunque no sea una labor más).
    cuantos: dict[int, int] = defaultdict(int)

    def _del_anio(anio: int) -> dict:
        if anio not in anios:
            cultivo = cultivos_por_anio.get(anio) or {}
            anios[anio] = {
                "anio": anio,
                "cultivo": cultivo.get("especie"),
                "variedad": cultivo.get("variedad"),
                "superficie_ha": cultivo.get("superficie_cultivada_ha"),
                "siembra": None,
                "labores": [],
                "tratamientos": [],
                "abonos": [],
                "cosecha": None,
            }
        return anios[anio]

    # Los años de los cultivos declarados también son años con datos: una tierra con su cultivo
    # apuntado y sin labores no es un año vacío.
    for anio, cultivo in cultivos_por_anio.items():
        _del_anio(anio)

    for fila in sorted(filas, key=lambda una: una["fecha"]):
        anio = fila["fecha"].year if fila["fecha"] else None
        if anio is None:
            continue
        elemento = _del_anio(anio)
        cuantos[anio] += 1
        if fila["tipo"] == CLAVE_COSECHA:
            elemento["cosecha"] = {
                "fecha": fila["fecha"].isoformat(),
                "kg": fila["kg"],
                "kg_ha": fila["kg_ha"],
            }
        elif fila["tipo"] == CLAVE_TRATAMIENTO:
            elemento["tratamientos"].append(
                {
                    "fecha": fila["fecha"].isoformat(),
                    "producto": fila["producto"],
                    "dosis": fila["dosis"],
                    "dosis_unidad": fila["dosis_unidad"],
                    "materia_activa": fila["materia_activa"],
                    # La cuenta atrás del plazo de seguridad, para que se vea en el historial.
                    "plazo_hasta": fila.get("plazo_hasta"),
                }
            )
        elif fila["tipo"] == CLAVE_ABONO:
            elemento["abonos"].append(
                {
                    "fecha": fila["fecha"].isoformat(),
                    "mes": fila["mes"],
                    "producto": fila["producto"],
                    "kg": fila["kg"],
                    "kg_ha": fila["kg_ha"],
                }
            )
        else:
            # **La siembra puede venir de la labor del día o de la ficha de la semilla**, y las dos
            # son la siembra del año: se rellena el bloque `siembra` con la primera que llegue (las
            # filas van de más vieja a más nueva, así que es la del principio de la campaña). Y la
            # labor se queda además en `labores`, porque para el agricultor fue un trabajo del día.
            if fila["clave"] == CLAVE_SIEMBRA and elemento["siembra"] is None:
                elemento["siembra"] = {
                    "fecha": fila["fecha"].isoformat(),
                    "cultivo": fila["cultivo"] or fila["producto"],
                    "variedad": fila["variedad"],
                    "dosis_semilla_kg_ha": fila["dosis_semilla_kg_ha"],
                }
            if fila["tipo"] == CLAVE_SIEMBRA:
                # La ficha de la semilla no es una labor más: ya está dicha en `siembra`.
                continue
            elemento["labores"].append(
                {
                    "fecha": fila["fecha"].isoformat(),
                    "labor": fila["labor_clave"],
                    "titulo": fila["titulo"],
                    "mes": fila["mes"],
                    "detalle": fila["detalle"],
                }
            )

    for elemento in anios.values():
        elemento["labores"].sort(key=lambda una: una["fecha"], reverse=True)
        elemento["tratamientos"].sort(key=lambda uno: uno["fecha"], reverse=True)
        elemento["abonos"].sort(key=lambda uno: uno["fecha"], reverse=True)
        # **El cultivo del año: primero el declarado y, si no lo hay, el de la siembra.** El declarado
        # (la hoja 2.1 del cuaderno) manda; pero una tierra que solo tiene la labor de siembra apuntada
        # también sabe qué se sembró ese año, y callarlo dejaría la cabecera del año en blanco teniendo
        # el dato delante. No se rellena nada más: la superficie sigue siendo la del cultivo declarado.
        if elemento["cultivo"] is None and elemento["siembra"]:
            elemento["cultivo"] = elemento["siembra"]["cultivo"]
            elemento["variedad"] = elemento["siembra"]["variedad"]
        # **El resumen del año**, para poder comparar dos años de un vistazo (IMP-13). Va al final,
        # cuando ya están todas las listas del año y sus cuentas.
        elemento["resumen"] = _el_resumen_de_un_anio(elemento, cuantos[anio])

    return [anios[anio] for anio in sorted(anios, reverse=True)]


def la_ficha_de_la_tierra(db: Session, *, explotacion, parcela_id: int) -> dict:
    """**La ficha de una tierra: qué se ha hecho hoy, qué se hizo los años anteriores y su resumen.**

    Es la primera pantalla que David quiere: elegir la tierra y ver **el trabajo de hoy** sin buscar
    nada. Debajo, el historial por años. Y siempre de una tierra **de esta finca**: una tierra de otra
    contesta 404 (`obtener_de_la_explotacion`), que es la regla de la casa para no decir si un
    identificador existe en otro cuaderno.
    """
    parcela = obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    campana = la_campana_activa(db, explotacion.id)

    # Lo de la campaña activa, para el bloque de la tierra: su cultivo y los años anteriores.
    cultivos = _los_cultivos(db, explotacion.id).get(parcela.id, {})
    tierra = _una_tierra(parcela, cultivos, campana)

    filas = _los_apuntes(db, explotacion.id, parcela_id=parcela.id)
    hoy = dt.date.today()
    trabajo_de_hoy = [
        {
            "tipo": fila["tipo"],
            "fecha": fila["fecha"].isoformat(),
            "titulo": fila["titulo"],
            "detalle": fila["detalle"],
            "cantidad": fila["cantidad"],
            "unidad": fila["unidad"],
            "hectareas": fila["hectareas"],
            "por_hectarea": fila["por_hectarea"],
            "unidad_por_hectarea": fila["unidad_por_hectarea"],
        }
        for fila in filas
        if fila["fecha"] == hoy
    ]

    # Los cultivos declarados de la tierra, por año: es el «qué se sembró» de cada campaña.
    cultivos_por_anio: dict[int, dict] = {}
    for fila in db.execute(
        select(models.ParcelaCultivo, models.Campana.anio)
        .join(models.Campana, models.Campana.id == models.ParcelaCultivo.campana_id)
        .where(
            models.ParcelaCultivo.explotacion_id == explotacion.id,
            models.ParcelaCultivo.parcela_id == parcela.id,
        )
    ).all():
        cultivo, anio = fila
        cultivos_por_anio[anio] = {
            "especie": cultivo.especie,
            "variedad": cultivo.variedad,
            "superficie_cultivada_ha": cultivo.superficie_cultivada_ha,
        }

    historial = _el_historial(filas, cultivos_por_anio)

    # **El cuaderno guiado** (10/11/2026): qué toca hacer en esta tierra y a partir de cuándo. Se
    # calcula con los plazos que están apuntados en cada tratamiento (los de la etiqueta, copiados
    # el día de la aplicación) y con si la tierra tiene cultivo declarado en la campaña. No se
    # inventa ninguna fecha: si no hay plazo apuntado, no hay aviso.
    tratamientos_con_plazo = [
        {
            "fecha": fila.fecha,
            "plazo_seguridad_dias": fila.plazo_seguridad_dias,
            "plazo_reentrada_dias": fila.plazo_reentrada_dias,
        }
        for fila in db.execute(
            select(models.TratamientoFitosanitario)
            .where(
                models.TratamientoFitosanitario.explotacion_id == explotacion.id,
                models.TratamientoFitosanitario.parcela_id == parcela.id,
            )
            .order_by(models.TratamientoFitosanitario.fecha.desc())
        ).scalars()
    ]
    guia = lo_que_toca(
        hoy=hoy,
        tratamientos=tratamientos_con_plazo,
        tiene_cultivo=bool(cultivos.get(campana.id)) if campana is not None else False,
    )

    fechas = [fila["fecha"] for fila in filas if fila["fecha"] is not None]
    ultima_cosecha = next((fila for fila in filas if fila["tipo"] == CLAVE_COSECHA), None)
    return {
        "tierra": tierra,
        "trabajo_de_hoy": trabajo_de_hoy,
        "historial": historial,
        "guia": guia,
        "resumen": {
            "n_apuntes": len(filas),
            "primera_fecha": min(fechas).isoformat() if fechas else None,
            "ultima_fecha": max(fechas).isoformat() if fechas else None,
            "kg_ha_ultima_cosecha": ultima_cosecha["kg_ha"] if ultima_cosecha else None,
        },
    }


def _las_cantidades_por_unidad(filas: list[dict]) -> dict[str, float]:
    """**Lo que se puede sumar, por unidad**: kilos con kilos y metros cúbicos con metros cúbicos.

    Es la regla de la casa para lo que se mide en varias unidades: **no se suman unidades distintas**
    aunque las dos sean un número (ver `AGENTS.md` §4). Un apunte sin cantidad o sin unidad no entra
    en ningún total: no se puede colocar en una suma que significa algo.
    """
    totales: dict[str, float] = {}
    for fila in filas:
        if fila["cantidad"] is None or not fila["unidad"]:
            continue
        totales[fila["unidad"]] = round(
            totales.get(fila["unidad"], 0.0) + float(fila["cantidad"]), 4
        )
    return totales


def _los_totales_de_un_conjunto(filas: list[dict]) -> dict:
    """Los totales de un conjunto de apuntes: cuántos, cuántas hectáreas y cuánto de cada unidad.

    Las hectáreas van a `None` **si a algún apunte le falta la superficie**: un total al que le falta
    un sumando no es un total (misma regla que en las superficies de la finca).
    """
    return {
        "n": len(filas),
        "hectareas": _la_suma_de_hectareas([fila["hectareas"] for fila in filas]),
        "cantidades_por_unidad": _las_cantidades_por_unidad(filas),
    }


def _comprobar_el_rango(desde, hasta) -> None:
    """Un rango de fechas que se pueda mirar: al derecho y de como mucho un año.

    Un final anterior al principio y un rango de más de un año se contestan con un **422 que se
    entiende**, no con una consulta que devuelva media vida del agricultor. Cuando solo viene uno de
    los dos extremos no hay rango que comprobar: es una lista abierta por el otro lado.
    """
    if desde is None or hasta is None:
        return
    if hasta < desde:
        raise HTTPException(
            status_code=422,
            detail="El último día no puede ser anterior al primero.",
        )
    if (hasta - desde).days > MAXIMO_DE_DIAS_EN_EL_CALENDARIO:
        raise HTTPException(
            status_code=422,
            detail=(
                "No se pueden mirar más de un año de golpe (366 días). Elige un tramo más corto."
            ),
        )


def calendario(db: Session, *, explotacion, desde=None, hasta=None) -> dict:
    """**Qué se ha hecho cada día**, en el rango que se pida (por defecto, el mes en curso).

    Solo vuelven los días con algo: el calendario ya sabe qué días están vacíos, y mandar los 31 días con
    su lista vacía sería mandar nada. Sin `desde` ni `hasta` se mira el mes de hoy, que es el que el
    agricultor tiene delante al abrir la agenda.

    **Cada día lleva sus totales** (cuántos trabajos, cuántas hectáreas y cuánto de cada unidad) y el
    mes lleva los suyos, además de los recuentos por tipo. Las cantidades **nunca se suman entre
    unidades distintas**: 1.200 kg y 300 m³ son dos números en el mismo diccionario, no una suma.

    **El rango se comprueba**: un final anterior al principio y un rango de más de un año se contestan
    con un 422 que se entiende.
    """
    hoy = dt.date.today()
    desde = desde or hoy.replace(day=1)
    hasta = hasta or _el_ultimo_dia_del_mes(desde)
    _comprobar_el_rango(desde, hasta)

    filas = _los_apuntes(db, explotacion.id, desde=desde, hasta=hasta)
    por_dia: dict[dt.date, list[dict]] = defaultdict(list)
    for fila in filas:
        por_dia[fila["fecha"]].append(fila)

    dias = [
        {
            "fecha": fecha.isoformat(),
            "trabajos": [_el_apunte_para_la_agenda(fila) for fila in del_dia],
            "totales": _los_totales_de_un_conjunto(del_dia),
        }
        for fecha, del_dia in sorted(por_dia.items())
    ]
    por_tipo: dict[str, int] = defaultdict(int)
    for fila in filas:
        por_tipo[fila["tipo"]] += 1
    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "dias": dias,
        "totales": {
            "por_tipo": dict(por_tipo),
            **_los_totales_de_un_conjunto(filas),
        },
    }


def _el_ultimo_dia_del_mes(fecha: dt.date) -> dt.date:
    """El último día de ese mes, sin librerías de calendario y sin cuentas raras."""
    siguiente = fecha.replace(day=28) + dt.timedelta(days=4)
    return siguiente - dt.timedelta(days=siguiente.day)


def trabajos(
    db: Session,
    *,
    explotacion,
    tipo: str | None = None,
    campana_id: int | None = None,
    parcela_id: int | None = None,
    desde=None,
    hasta=None,
) -> dict:
    """**Los trabajos de la finca, con sus tierras y sus cantidades, filtrables por tipo, tierra y fechas.**

    Es la trazabilidad de toda la explotación: cada fila lleva **su tierra y su municipio**, para poder
    contestar «¿dónde se pasó el cultivador?» sin abrir tierra por tierra, y **el filtro se puede
    acotar** a una tierra y a un tramo de días.

    **El ámbito, contado bien**: con `desde`/`hasta` manda el rango de fechas (mirar el año pasado no
    puede quedarse vacío porque la campaña activa sea esta); sin fechas se mira la campaña activa, que
    es lo que el agricultor tiene delante. Si se pide una campaña concreta, se usa esa.

    Los tipos de la lista salen de **lo que hay en el conjunto ya filtrado** (con su recuento): si se
    mira una tierra, las cuentas son de esa tierra, y así la pantalla no ofrece un filtro que no lleva a
    nada. Un `tipo` que el programa conoce pero que no tiene datos devuelve la lista vacía y su resumen
    a cero; uno que no existe en el vocabulario contesta **422 con la lista de los que valen**, no un 500.

    **Las cantidades van por unidad** (`kg`, `m3`, `litros`…): nunca se suman unidades distintas, porque
    un total que mezcla kilos y litros no significa nada.
    """
    from . import trabajos as el_modulo_de_trabajos

    if parcela_id is not None:
        # De esta finca o 404: no se dice si un identificador existe en otro cuaderno.
        obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    _comprobar_el_rango(desde, hasta)

    campana: models.Campana | None = None
    if campana_id is not None:
        campana = la_campana_activa(db, explotacion.id, campana_id)
    elif desde is None and hasta is None:
        campana = la_campana_activa(db, explotacion.id)
    # Y si hay fechas y no se ha pedido campaña, **no se acota por campaña**: el rango manda.

    filas = _los_apuntes(
        db,
        explotacion.id,
        parcela_id=parcela_id,
        desde=desde,
        hasta=hasta,
        campana=campana,
    )

    # El vocabulario de tipos que el programa conoce: las labores de su catálogo, los aperos de suelo y
    # los dos registros que no son labores.
    vocabulario = list(catalogos.TIPOS_LABOR) + list(el_modulo_de_trabajos.SUBTIPOS_DE_LABOREO)
    vocabulario += [CLAVE_TRATAMIENTO, CLAVE_ABONO]

    if tipo is not None and tipo not in vocabulario and tipo != CLAVE_OTROS:
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": "Ese tipo de trabajo no está en el vocabulario del programa.",
                "tipos": vocabulario,
            },
        )

    elegidas = [fila for fila in filas if tipo is None or fila["clave"] == tipo]

    cuantas: dict[str, int] = defaultdict(int)
    for fila in filas:
        cuantas[fila["clave"]] += 1
    # Los tipos que se ofrecen: los que tienen algo **en lo filtrado**, de más a menos. Y si hay apuntes
    # cuya clave no está en el vocabulario (una labor de un tipo nuevo), se dicen como «otros».
    tipos = [
        {"clave": clave, "etiqueta": _la_etiqueta_de_un_tipo(clave), "n": cuantas[clave]}
        for clave in sorted(cuantas, key=lambda una: (-cuantas[una], una))
    ]

    por_tipo: dict[str, dict] = {}
    for fila in elegidas:
        suyo = por_tipo.setdefault(fila["clave"], {"n": 0, "hectareas": [], "filas": []})
        suyo["n"] += 1
        suyo["hectareas"].append(fila["hectareas"])
        suyo["filas"].append(fila)
    resumen_por_tipo = {
        clave: {
            "n": datos["n"],
            "hectareas": _la_suma_de_hectareas(datos["hectareas"]),
            "cantidades_por_unidad": _las_cantidades_por_unidad(datos["filas"]),
        }
        for clave, datos in por_tipo.items()
    }

    return {
        "tipos": tipos,
        "elegido": tipo,
        "trabajos": [
            {
                "fecha": fila["fecha"].isoformat(),
                "tipo": fila["clave"],
                "titulo": fila["titulo"],
                "tierra_id": fila["parcela_id"],
                "tierra_alias": fila["parcela_alias"],
                "municipio": fila["municipio"],
                "cantidad": fila["cantidad"],
                "unidad": fila["unidad"],
                "hectareas": fila["hectareas"],
                "por_hectarea": fila["por_hectarea"],
            }
            for fila in elegidas
        ],
        "resumen": {
            **_los_totales_de_un_conjunto(elegidas),
            "por_tipo": resumen_por_tipo,
        },
    }
