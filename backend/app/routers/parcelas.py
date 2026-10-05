"""Parcelas, cultivos y grupos de parcelas.

Decisión sobre la zona de nitratos: al dar de alta una parcela se intenta deducir
sola a partir del municipio, pero SOLO si el listado oficial está cargado. Si no lo
está, el campo se queda en "no lo sabemos" (None) y la aplicación pregunta. Nunca
se pone False por defecto, porque eso sería afirmar un dato que no tenemos.

Aquí está también el **conector con el SIGPAC**: dar de alta una parcela dándole solo la
referencia del recinto y que el resto venga solo. Ver `app/sigpac.py`.
"""

from __future__ import annotations

import hashlib
import unicodedata

import httpx
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, func, select

from .. import catalogos, correcciones, geo, models, servicios, sigpac, textos
from .. import versiones_de_recinto as versiones_de_recinto
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    BuscarRecintosEntrada,
    CajaDelMapa,
    CultivoEntrada,
    ElMapaDeLaFinca,
    FiltrosDeLasTierras,
    GrupoEntrada,
    GrupoSalida,
    OpcionDeUnFiltro,
    ParcelaDesdeSigpac,
    ParcelaEntrada,
    ParcelaSalida,
    ReferenciaSigpacEntrada,
    TierraEnLaVista,
    TotalesDeLasTierras,
    VariasParcelasDesdeSigpac,
    VistaDeLasTierras,
)

router = APIRouter(prefix="/api", tags=["parcelas"])

# Cuántos trozos se completan con sus datos en una búsqueda. Una parcela normal tiene uno o dos
# recintos; el tope está para que una parcela partida en cincuenta trozos no dispare cincuenta
# peticiones al SIGPAC y deje la pantalla pensando.
MAX_RECINTOS_POR_BUSQUEDA = 25


def _municipio_elegido(provincia: str | None, municipio: str | None) -> dict | None:
    """El municipio de la lista oficial, si el que se ha escrito está en ella.

    Se busca por nombre (sin tildes y sin mayúsculas) y devuelve también **el código INE**, que
    es lo que hace que después la comprobación de zona vulnerable no dependa de cómo se haya
    escrito el nombre del pueblo. Si no está en la lista no se inventa nada: se devuelve `None` y
    el municipio se queda tal y como lo ha escrito el agricultor.
    """
    if not municipio:
        return None
    candidatos = catalogos.busca_municipios(municipio, provincia=provincia, limite=5)
    exacto = next(
        (c for c in candidatos if c.nombre.lower() == municipio.strip().lower()), None
    )
    elegido = exacto or (candidatos[0] if len(candidatos) == 1 else None)
    if elegido is None:
        return None
    return {
        "nombre": elegido.nombre,
        "provincia": elegido.provincia,
        "codigo_ine": elegido.codigo_ine,
        "codigo_municipio": elegido.codigo_municipio,
        "codigo_provincia": elegido.codigo_provincia,
    }


def _busqueda_de_lo_que_ha_dicho(datos: BuscarRecintosEntrada) -> sigpac.Busqueda:
    """Arma la búsqueda con lo que haya mandado el agricultor.

    Dos caminos, y los dos tienen que llevar al mismo sitio: la referencia pegada (la del visor,
    los siete números o la catastral) o las casillas sueltas, con el municipio **elegido de la
    lista**. Si vienen las casillas y el municipio no está en la lista oficial, se dice: sin el
    código del municipio no se puede preguntar al SIGPAC, y adivinar el código sería inventarse
    dónde está la parcela.
    """
    if datos.referencia and datos.referencia.strip():
        return sigpac.lee_busqueda(datos.referencia)

    if datos.municipio and datos.poligono is not None and datos.parcela is not None:
        elegido = _municipio_elegido(datos.provincia, datos.municipio)
        if elegido is None:
            raise sigpac.ReferenciaInvalida(textos.MUNICIPIOS["no_esta_en_la_lista"])
        return sigpac.Busqueda(
            provincia=int(elegido["codigo_provincia"]),
            municipio=int(elegido["codigo_municipio"]),
            agregado=datos.agregado,
            zona=datos.zona,
            poligono=datos.poligono,
            parcela=datos.parcela,
        )

    raise sigpac.ReferenciaInvalida(textos.SIGPAC["busqueda_incompleta"])


def _alta_desde_recinto(
    db,
    explotacion,
    *,
    recinto: sigpac.Recinto,
    alias: str | None,
    municipio: str | None,
    provincia: str | None,
    sistema: str | None,
    referencia_catastral: str | None = None,
) -> models.Parcela:
    """Da de alta la parcela con los datos que ha traído el SIGPAC.

    Está aquí, y no dentro del endpoint, porque la usan **los dos caminos**: traer una parcela
    suelta y traer cuarenta de golpe. Si cada uno hiciera lo suyo, una de las dos formas acabaría
    rellenando la zona de nitratos de otra manera, y eso es justo lo que no puede pasar.

    **Y rellena todo lo que el SIGPAC sabe**, que es más de lo que se pedía antes:

    1. **El pueblo y la provincia**, si no los ha dicho el agricultor: el SIGPAC da los códigos
       numéricos del municipio y de la provincia, y esos códigos son los del INE, así que con la
       lista oficial se sabe el nombre. Antes se quedaba en blanco y la parcela salía sin pueblo.
    2. **La referencia catastral** (consulta `refcatparcela`), que el contenido mínimo del CUE
       pide por su nombre. Si el agricultor la ha pegado, manda la suya; si no, la pone el SIGPAC.
    3. **La zona de nitratos de verdad**, por cruce con la capa oficial (`intersection/nitratos`),
       que dice si **este trozo** cae dentro (y cuánto de él). La lista municipal solo dice si el
       **pueblo** está en una zona declarada, y eso es otra cosa: por eso lo oficial manda.

    Las dos últimas se preguntan **sin poder romper el alta**: si el servicio no contesta, la
    parcela se guarda igual, con lo que se sabe, y la zona se queda como la dejó la lista
    municipal (o en «no lo sé»). Un conector que impide apuntar una parcela cuando falla es peor
    que no tenerlo.
    """
    elegido = _municipio_elegido(provincia, municipio)
    municipio_final = (elegido or {}).get("nombre") or (municipio or "").strip()
    provincia_final = (elegido or {}).get("provincia") or (provincia or "").strip()
    codigo_ine = (elegido or {}).get("codigo_ine")

    # Si no hay nombre de pueblo, se busca por los códigos que da el SIGPAC. Es lo que permite
    # que una parcela elegida **tocando el mapa** salga con su pueblo y su provincia puestos.
    if not municipio_final or not provincia_final or not codigo_ine:
        por_codigos = catalogos.municipio_por_codigo_ine(
            f"{recinto.provincia:02d}{recinto.municipio:03d}"
            if recinto.provincia is not None and recinto.municipio is not None
            else None
        )
        if por_codigos is not None:
            municipio_final = municipio_final or por_codigos.nombre
            provincia_final = provincia_final or por_codigos.provincia
            codigo_ine = codigo_ine or por_codigos.codigo_ine

    busqueda = sigpac.Busqueda(
        provincia=recinto.provincia or 0,
        municipio=recinto.municipio or 0,
        agregado=recinto.agregado,
        zona=recinto.zona,
        poligono=recinto.poligono or 0,
        parcela=recinto.parcela or 0,
        recinto=recinto.recinto,
    )
    referencia = recinto.referencia

    # La referencia catastral: la del agricultor manda; si no la tiene, la pone el SIGPAC.
    catastral_final = (referencia_catastral or "").strip()
    if not catastral_final:
        try:
            catastral_final = sigpac.pedir_referencia_catastral(busqueda) or ""
        except sigpac.SigpacNoContesta:
            catastral_final = ""

    # La zona de nitratos: primero la capa oficial (por recinto), y si no se sabe, la lista de
    # municipios (por pueblo). Nunca se pone un «no» sin haberlo comprobado.
    en_zona: bool | None = None
    porcentaje: float | None = None
    if referencia is not None:
        try:
            respuesta = sigpac.zona_de_nitratos(referencia)
        except sigpac.SigpacNoContesta:
            respuesta = None
        if respuesta is not None:
            en_zona, porcentaje = respuesta
    if en_zona is None:
        en_zona = catalogos.es_zona_vulnerable(municipio_final, provincia_final, codigo_ine)

    parcela = models.Parcela(
        explotacion_id=explotacion.id,
        alias=(
            alias
            or f"Parcela {recinto.parcela}, recinto {recinto.recinto}"
        ).strip(),
        ref_sigpac=recinto.ref_sigpac,
        provincia=provincia_final,
        municipio=municipio_final,
        codigo_ine=codigo_ine,
        agregado=recinto.agregado or 0,
        zona=recinto.zona or 0,
        referencia_catastral=catastral_final or None,
        poligono=recinto.poligono,
        numero_parcela=recinto.parcela,
        numero_recinto=recinto.recinto,
        # **Y si el SIGPAC no manda la superficie, se queda en blanco: no se pone un cero**
        # (A7 de `docs/T02_VALORES_POR_DEFECTO.md`). El servicio puede no mandarla
        # (`sigpac.py`, `superficie: float | None = None`), y un cero ahí cierra la puerta a tratar
        # esa tierra. `superficie_oficial` dice «la superficie es la oficial, no una medida a ojo»,
        # así que sin superficie no hay nada oficial que declarar.
        superficie_ha=recinto.superficie,
        superficie_oficial=recinto.superficie is not None,
        # Y es la del recinto entero, que es justo la que pide la hoja 2.1 del cuaderno de la
        # Junta en su columna «Superficie SIGPAC (ha)».
        superficie_sigpac_ha=recinto.superficie,
        uso_sigpac=recinto.uso_sigpac,
        pendiente_pct=recinto.pendiente_media,
        # El sistema de explotación lo dice el agricultor en el mapa, no el SIGPAC. **Y si no lo ha
        # dicho, se queda en «no lo sé»** (A10 de `docs/T02_VALORES_POR_DEFECTO.md`): aquí ponía
        # `else "secano"`, así que una tierra de regadío traída sin tocar el botón quedaba declarada de
        # secano —y la casilla «Secano/Regadío» del cuaderno de la Junta se escribía con una «S»—.
        sistema=sistema if sistema in catalogos.SISTEMAS_EXPLOTACION else None,
        geometria=recinto.wkt,
        zona_vulnerable_nitratos=en_zona,
    )
    db.add(parcela)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="parcela",
            accion="crear_desde_sigpac",
            datos={
                "ref_sigpac": parcela.ref_sigpac,
                "superficie_ha": parcela.superficie_ha,
                "uso_sigpac": parcela.uso_sigpac,
                # Queda escrito de dónde salió cada dato que no ha puesto el agricultor, con el
                # porcentaje de la intersección: si alguien pregunta por qué esta parcela está
                # marcada como zona de nitratos, la respuesta está en el registro.
                "referencia_catastral": parcela.referencia_catastral,
                "zona_vulnerable_nitratos": parcela.zona_vulnerable_nitratos,
                "zona_vulnerable_porcentaje": porcentaje,
            },
        )
    )
    db.flush()
    return parcela


@router.get("/parcelas", response_model=list[ParcelaSalida])
def listar_parcelas(explotacion: ExplotacionActual, db: Db) -> list[models.Parcela]:
    return list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.alias)
        )
    )


def _la_campana_mas_nueva(db: Db, explotacion_id: int, campana_id: int | None) -> models.Campana | None:
    """La campaña que se está llevando, o la que digan. De esta finca, nunca de otra.

    Es la misma decisión que toma `/api/cultivos`: sin decir cuál, la más nueva, que es la que el
    agricultor tiene delante cuando abre el programa.
    """
    if campana_id is not None:
        return obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion_id)
    return db.scalar(
        select(models.Campana)
        .where(models.Campana.explotacion_id == explotacion_id)
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )


@router.get("/parcelas/vista", response_model=VistaDeLasTierras)
def las_tierras_de_la_finca(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> VistaDeLasTierras:
    """**Las tierras de la finca, en el mapa y en la tabla** (T06, 03/10/2026).

    ## Por qué existe, y por qué es una sola llamada

    Lo pide el contrato en su apartado 2.1: «Vista de las 64 tierras: tabla y mapa vinculados, con
    búsqueda por alias y referencia, filtros por cultivo/municipio/estado/PAC, agrupación y selección
    múltiple». Pintar eso con lo que ya había exigía cruzar `/api/parcelas`, `/api/cultivos` y
    `/api/versiones` en el navegador, y cruzar tres listas en la pantalla es la forma más segura de
    que un día digan cosas distintas: una tierra en la tabla, otra en el mapa y un total que no
    cuadra con ninguna. Aquí se cruzan **una vez, en el servidor**, y sale lo mismo para las tres
    cosas.

    ## Lo que este endpoint NO hace

      · **No filtra.** Devuelve todas las tierras y los recuentos de todas. Filtrar es cosa de la
        pantalla, y hay un motivo: el buscador tiene que responder **sin cobertura** (la lista ya
        está descargada) y el pie tiene que poder decir «ves 10 de 64». Los recuentos de cada opción
        sí los calcula el servidor, para que no cambien al escribir en el buscador.
      · **No suma hectáreas.** No hay ningún total de superficie en la respuesta: la mitad de las
        tierras puede tener la superficie en blanco («no lo sé», `T02`), y un total que sumara esas
        como cero sería una cifra falsa. Un total que solo sumara las conocidas diría menos de lo
        que parece, así que no se da ninguno.
      · **No inventa un centro.** Si ninguna tierra tiene forma, `mapa.hay_forma` es falso y `caja`
        viene vacía: la pantalla lo dice en vez de abrir el mapa en mitad de Castilla y León.
      · **No se sale de la finca.** Todo se lee con `explotacion.id` por delante, y la campaña se
        coge con `obtener_de_la_explotacion` (404 y no 403, para no decir si existe en otro cuaderno).
    """
    campana = _la_campana_mas_nueva(db, explotacion.id, campana_id)
    tierras = list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion.id)
            .order_by(models.Parcela.alias, models.Parcela.id)
        )
    )

    # Lo sembrado este año, por tierra. Se reutiliza la misma función que sirve «qué hay sembrado»
    # para que la tabla y aquella pantalla no puedan decir cosas distintas de la misma tierra.
    sembrado = {
        ficha["parcela_id"]: ficha
        for ficha in servicios.los_cultivos_de_la_finca(
            db, explotacion_id=explotacion.id, campana_id=campana.id if campana else None
        )
    }

    # **La versión que manda en la tabla**: una sola por tierra. De ella salen el estado de revisión y
    # las hectáreas declaradas, que son los dos datos que no están en la tierra (la tierra es «como es
    # hoy»; la versión es «qué se dijo de ella ese año y quién lo dijo»).
    #
    # **Y cuál manda cuando hay dos, se decide aquí y por escrito** (02/10/2026). Antes se ordenaba solo
    # por `(parcela_id, clave)` y se tomaba la primera con `setdefault`: con la misma tierra, la misma
    # campaña y la misma clave, **la del SIGPAC y la del agricultor empatan**, así que ganaba **el orden
    # que le saliera al plan de la base**. En SQLite salía una y en PostgreSQL la otra, o sea que la misma
    # tierra enseñaba cosas distintas según el motor. Lo destapó la suite corriendo contra PostgreSQL.
    # Ahora el desempate es explícito: primero la fuente con más autoridad (`versiones_de_recinto.
    # PRIORIDAD_DE_FUENTES`: lo medido en el campo, lo que declara el agricultor, su cuaderno de la
    # Junta y por último la importación oficial) y, si la fuente es la misma, la más nueva.
    prioridad_de_la_fuente = case(
        *(
            (models.VersionDeRecinto.fuente == fuente, posicion)
            for posicion, fuente in enumerate(versiones_de_recinto.PRIORIDAD_DE_FUENTES)
        ),
        else_=len(versiones_de_recinto.PRIORIDAD_DE_FUENTES),
    )
    versiones: dict[int, models.VersionDeRecinto] = {}
    if campana is not None:
        for version in db.scalars(
            select(models.VersionDeRecinto)
            .where(
                models.VersionDeRecinto.explotacion_id == explotacion.id,
                models.VersionDeRecinto.campana_id == campana.id,
            )
            .order_by(
                models.VersionDeRecinto.parcela_id,
                models.VersionDeRecinto.clave,
                prioridad_de_la_fuente,
                models.VersionDeRecinto.id.desc(),
            )
        ):
            versiones.setdefault(version.parcela_id, version)

    salida: list[TierraEnLaVista] = []    # **Cuántas tierras se llaman igual**, contadas antes de montar la respuesta: con los datos de
    # verdad hay 65 tierras y solo 60 nombres distintos, así que dos filas pueden tener el mismo
    # nombre y hasta la misma superficie. Se cuenta **el texto tal cual está guardado** (lo que el
    # agricultor ve en la pantalla), no una versión normalizada: dos nombres que solo se diferencian
    # en una mayúscula se ven distintos, y decir «está repetido» de ellos sería confundirle.
    cuantas_por_nombre: dict[str, int] = {}
    for parcela in tierras:
        cuantas_por_nombre[parcela.alias] = cuantas_por_nombre.get(parcela.alias, 0) + 1

    for posicion, parcela in enumerate(tierras, start=1):
        suyo = sembrado.get(parcela.id) or {}
        actual = suyo.get("actual") or None
        version = versiones.get(parcela.id)
        anillos = [
            [[lon, lat] for lon, lat in anillo]
            for anillo in geo.anillos_de_un_wkt(parcela.geometria)
        ]
        especie = ((actual or {}).get("especie") or "").strip()
        sistema = (actual or {}).get("sistema") or parcela.sistema
        salida.append(
            TierraEnLaVista(
                id=parcela.id,
                numero=posicion,
                alias=parcela.alias,
                referencia=parcela.ref_sigpac,
                provincia=parcela.provincia or "",
                municipio=parcela.municipio or "",
                sistema=sistema or "",
                superficie_ha=parcela.superficie_ha,
                superficie_sigpac_ha=parcela.superficie_sigpac_ha,
                tiene_forma=bool(anillos),
                forma=parcela.dibujo,
                anillos=anillos,
                cultivo=(
                    # Lo que hay sembrado, con su variedad y su secano o regadío, **y solo si hay
                    # especie**: sin especie no hay nada que decir, y poner «secano» a secas en la
                    # columna de lo sembrado sería contar un dato que no es el que se pregunta.
                    " · ".join(
                        texto
                        for texto in (
                            especie,
                            (actual or {}).get("variedad"),
                            catalogos.ETIQUETA_SISTEMA.get(sistema, ""),
                        )
                        if texto
                    )
                    if especie
                    else ""
                ),
                cultivo_clave=especie,
                estado_revision=version.estado_revision if version is not None else None,
                estado_revision_texto=(
                    versiones_de_recinto.texto_del_estado_de_revision(version.estado_revision)
                    if version is not None
                    else None
                ),
                anio_de_la_version=(campana.anio if version is not None and campana else None),
                fuente_texto=(
                    versiones_de_recinto.texto_de_la_fuente(version.fuente)
                    if version is not None
                    else None
                ),
                tiene_referencia_completa=(
                    parcela.poligono is not None
                    and parcela.numero_parcela is not None
                    and parcela.numero_recinto is not None
                ),
                area_declarada_ha=version.area_declarada_ha if version is not None else None,
                tiene_hectareas_dichas=(parcela.superficie_ha is not None),
                clave_recinto=_la_clave_del_recinto_de_una_tierra(parcela),
                cuantas_con_el_mismo_nombre=cuantas_por_nombre[parcela.alias],
            )
        )

    return VistaDeLasTierras(
        textos=textos.TIERRA_Y_MAPA,
        textos_de_las_versiones=textos.VERSIONES_EN_PANTALLA,
        campana_id=campana.id if campana else None,
        campana_anio=campana.anio if campana else None,
        tierras=salida,
        totales=_los_totales_de_las_tierras(salida),
        mapa=_el_mapa_de_la_finca(salida),
        filtros=_los_filtros_de_las_tierras(salida),
    )


def _como_se_busca(texto: str) -> str:
    """Un texto en la forma en la que **se coteja**: sin tildes, en minúsculas y con los espacios de
    dentro juntos.

    **Es la misma normalización que usa la pantalla** (`nucleo.sinTildes`, el mismo quitador de tildes
    del buscador de tierras), y tiene que serlo: si el servidor junta las opciones de un filtro de una
    manera y la pantalla coteja de otra, el número que se lee al lado de la opción y las filas que
    salen al elegirla **no cuadran**, y el agricultor deja de creerse los números del filtro.

    Lo encontró la revisión de T06 (D3) con dos casos que están a un paso de sus datos:

      · `MACHACON` (que es como lo escribe el cuaderno de la Junta, sin tilde) y `Machacón` (que es
        como lo escribe la lista oficial del INE, de donde el formulario lo coge al elegirlo). Un
        `.upper()` no los junta, porque la tilde sigue ahí;
      · `Calvarrasa  de Arriba` con dos espacios, que es lo que sale de teclear el nombre a mano. Un
        `.strip()` quita los de fuera y deja los de dentro.
    """
    sin_tildes = unicodedata.normalize("NFD", texto or "")
    sin_tildes = "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))
    return " ".join(sin_tildes.lower().split())


def _la_clave_del_recinto_de_una_tierra(parcela: models.Parcela) -> str:
    """Con qué recinto del SIGPAC habla una tierra, ya normalizado.

    **Por qué esto no es `versiones_de_recinto.clave_del_recinto`.** Aquella trabaja con los siete
    números de una referencia **tal y como vienen en un lote**, y una `Parcela` no los tiene así:
    guarda `provincia` y `municipio` como **nombres** («Salamanca», no «37»), que es lo que el
    agricultor escribe y lo que lee en su papel. La referencia buena de una tierra es su
    `ref_sigpac`, que es el texto con el que él la reconoce.

    Así que la clave es, por este orden:

      · **la referencia**, sin espacios de más y sin mayúsculas de sobra. Es lo que hace que las 65
        tierras de verdad, que traen solo 52 referencias distintas, se junten por donde tienen que
        juntarse: el cuaderno de la Junta parte un mismo recinto en varias líneas de cultivo, y esas
        líneas **son el mismo trozo de tierra**;
      · si no hay referencia, **la huella de la forma** (misma idea que en T05: dos formas iguales son
        el mismo recinto y dos distintas no);
      · y si no hay ni lo uno ni lo otro, **su propia tierra** (`tierra:<id>`): de una tierra sin
        referencia y sin forma no se puede decir que comparta nada con nadie, y decir que sí sería
        inventarse un recinto.
    """
    referencia = (parcela.ref_sigpac or "").strip()
    if referencia:
        return referencia.upper()[:80]
    if parcela.geometria:
        huella = hashlib.sha256(parcela.geometria.strip().encode("utf-8")).hexdigest()[:8]
        return f"forma:{huella}"
    return f"tierra:{parcela.id}"


def _los_totales_de_las_tierras(tierras: list[TierraEnLaVista]) -> TotalesDeLasTierras:
    """Los recuentos de la finca entera. **Solo cuentas**, ninguna medida ni ningún porcentaje."""
    return TotalesDeLasTierras(
        tierras=len(tierras),
        con_forma=sum(1 for tierra in tierras if tierra.tiene_forma),
        sin_forma=sum(1 for tierra in tierras if not tierra.tiene_forma),
        sin_cultivo=sum(1 for tierra in tierras if not tierra.cultivo_clave),
        sin_hectareas=sum(1 for tierra in tierras if not tierra.tiene_hectareas_dichas),
        sin_revision=sum(1 for tierra in tierras if tierra.estado_revision is None),
    )


def _el_mapa_de_la_finca(tierras: list[TierraEnLaVista]) -> ElMapaDeLaFinca:
    """El rectángulo que envuelve **las formas que de verdad hay**, o nada si no hay ninguna.

    **Se calcula desde las tierras ya montadas (`anillos`), y no volviendo a leer el WKT.** No es un
    detalle: la revisión de T06 encontró que, con la geometría escrita pero sin anillos que se puedan
    dibujar, el mapa contaba una tierra con forma y la tabla contaba otra, **en la misma respuesta**.
    Con un solo dato para los dos, eso no puede pasar.

    El rectángulo sale de las formas, no de una lista de provincias ni de un centro escrito a mano: es
    lo que hace que el mapa no pueda saltar a otra provincia.

    **Un detalle que importa:** si las formas son tan pequeñas que el rectángulo mide menos de lo que
    el servicio de mapas acepta (`LADO_MINIMO_GRADOS`), se **agranda alrededor de su propio centro**
    hasta ese mínimo. No se cambia de sitio: se enseña la misma finca más de cerca, que es lo único
    que se puede hacer cuando una tierra entera mide 40 metros.

    Y `se_puede_ensenar_entera` dice si la caja cabe en lo que el servicio acepta por arriba: una finca
    repartida en más de medio grado **no se puede enseñar de una vez**, y quien mira la pantalla tiene
    que saberlo antes de pedir la imagen.
    """
    con_forma = [tierra for tierra in tierras if tierra.tiene_forma and tierra.anillos]
    if not con_forma:
        return ElMapaDeLaFinca(hay_forma=False, tierras_con_forma=0, caja=None)

    longitudes = [punto[0] for tierra in con_forma for anillo in tierra.anillos for punto in anillo]
    latitudes = [punto[1] for tierra in con_forma for anillo in tierra.anillos for punto in anillo]
    oeste, este = min(longitudes), max(longitudes)
    sur, norte = min(latitudes), max(latitudes)
    from .mapa import LADO_MAXIMO_GRADOS, LADO_MINIMO_GRADOS

    lado = max(este - oeste, norte - sur)
    if lado < LADO_MINIMO_GRADOS:
        centro_lon = (oeste + este) / 2
        centro_lat = (sur + norte) / 2
        # **La cuenta lleva un pelo de margen a propósito.** Restar dos `float` no da el número
        # exacto (una caja de 0,0008 grados sale 0,0007999999999999119), así que sin el margen la
        # caja «agrandada» seguiría por debajo del mínimo que acepta el servicio de mapas y la
        # imagen se pediría con una caja que el propio programa rechaza.
        mitad = LADO_MINIMO_GRADOS / 2 * (1 + 1e-9)
        oeste, este = centro_lon - mitad, centro_lon + mitad
        sur, norte = centro_lat - mitad, centro_lat + mitad
        lado = max(este - oeste, norte - sur)

    # **Y por arriba hay otro tope, y es el que hacía daño** (revisión de T06, D7): el servicio de
    # mapas no acepta una caja de más de `LADO_MAXIMO_GRADOS` (medio grado, unos 55 km). Una finca
    # repartida en más que eso —dos pueblos lejanos, o una geometría mala— daba una caja que **el
    # propio `/api/mapa/imagen` de este programa rechazaba con 422**, y el agricultor leía «puede ser
    # la cobertura» delante de un fallo que no tiene nada que ver con la cobertura. Así que la caja
    # que se devuelve **es siempre una caja que este programa acepta**: se queda en el máximo,
    # centrada donde estaba, y `se_puede_ensenar_entera` dice que no se ve toda la finca.
    cabe_entera = lado <= LADO_MAXIMO_GRADOS
    entera = CajaDelMapa(oeste=oeste, sur=sur, este=este, norte=norte)
    if not cabe_entera:
        centro_lon = (oeste + este) / 2
        centro_lat = (sur + norte) / 2
        mitad = LADO_MAXIMO_GRADOS / 2 * (1 - 1e-12)
        oeste, este = centro_lon - mitad, centro_lon + mitad
        sur, norte = centro_lat - mitad, centro_lat + mitad
    return ElMapaDeLaFinca(
        hay_forma=True,
        tierras_con_forma=len(con_forma),
        caja=CajaDelMapa(oeste=oeste, sur=sur, este=este, norte=norte),
        se_puede_ensenar_entera=cabe_entera,
        extension=entera,
    )


def _los_filtros_de_las_tierras(tierras: list[TierraEnLaVista]) -> FiltrosDeLasTierras:
    """Lo que se puede elegir en cada filtro, **sacado de las tierras que hay**.

    Ni una lista escrita a mano: si un pueblo no está en ninguna tierra, no aparece en el filtro, y
    si un cultivo no lo tiene nadie sembrado tampoco. Cada opción lleva **cuántas tierras** caen en
    ella, con el mismo criterio con el que filtra la pantalla (las claves `*_clave`, los dos booleanos
    de la PAC y **el cotejo sin distinguir mayúsculas**), para que el número del filtro y las filas
    que salen al aplicarlo cuadren.

    ## El pueblo y el cultivo se juntan sin distinguir mayúsculas

    **Aquí hubo un ejemplo falso, y se deja escrito para que no vuelva** (lo cazó la revisión de T06,
    03/10/2026). Este texto decía: «con los datos de verdad del agricultor, el mismo pueblo está
    escrito de dos formas: `CALVARRASA DE ARRIBA` en 54 tierras y `Calvarrasa de Arriba` en 1, y está
    medido». **La medida estaba mal**: se contaron los 65 registros de **toda la base** sin filtrar
    por explotación, y la tierra escrita con minúsculas está en **otra finca**. En la finca del
    agricultor hay **7 municipios y ninguno repetido con otra ortografía**; la que falta de la lista
    es **`CALVARRASA DE ABAJO`, que es otro pueblo**.

    Y el caso de verdad está a un paso, así que el cotejo sigue haciendo falta: **su cuaderno escribe
    `MACHACON`** (sin tilde, como lo escribe la Junta) **y la lista oficial del INE dice `Machacón`**
    (con tilde) — el mismo pueblo escrito de dos maneras según quién lo escriba. También hay tierras
    con dos espacios de más dentro del nombre, que es lo que sale de teclearlo a mano.

    Si el filtro cotejara el texto tal cual, en la lista de pueblos saldrían **dos entradas para el
    mismo pueblo** y el agricultor creería que tiene tierras en otro sitio. **Cuidado con ampliar este
    comentario: cualquier número que se ponga aquí tiene que decir sobre qué finca y con qué filtro se
    midió**, porque «los datos del agricultor» y «toda la base» no son lo mismo —la base tiene más de
    una explotación— y este mismo error ya se copió a cinco sitios.

    Así que las opciones se juntan por su forma **normalizada y cada una lleva el recuento sumado**;
    para el rótulo se elige **la forma que más veces está escrita** (y si empatan, la primera por
    orden alfabético, para que la lista no cambie de aspecto entre dos pantallas iguales). Y hay una
    cosa que **no** se hace, que es la importante: **no se le cambia el texto al dato guardado ni al
    que se enseña en la fila**. El nombre del pueblo de sus tierras es suyo; el programa solo deja de
    tratarlo como si fueran dos.
    """

    def cuenta(criterio) -> int:
        return sum(1 for tierra in tierras if criterio(tierra))

    def opciones(pares: list[tuple[str, str, int]]) -> list[OpcionDeUnFiltro]:
        return [
            OpcionDeUnFiltro(valor=valor, texto=texto, cuantas=cuantas)
            for valor, texto, cuantas in pares
            if cuantas
        ]

    def juntando_sin_mayusculas(cual: str, comodin: str, comodin_texto: str) -> list[tuple[str, str, int]]:
        """Una opción por cada manera distinta de escribir lo mismo, con el recuento sumado.

        `cual` es `"municipio"` o `"cultivo_clave"`. El `valor` de la opción es **la forma que más se
        repite**, tal y como está escrita en el cuaderno: la pantalla coteja sin distinguir
        mayúsculas, tildes ni espacios de más (`paraBuscar` = `nucleo.sinTildes`), así que eligiendo
        esa forma salen **todas** las tierras de ese pueblo, se hayan escrito como se hayan escrito.
        La llave para juntarlas es `_como_se_busca`, **la misma normalización que la pantalla**.
        """
        formas: dict[str, dict[str, int]] = {}
        for tierra in tierras:
            escrito = (getattr(tierra, cual) or "").strip()
            if not escrito:
                continue
            normal = _como_se_busca(escrito)
            formas.setdefault(normal, {})
            formas[normal][escrito] = formas[normal].get(escrito, 0) + 1
        pares: list[tuple[str, str, int]] = []
        for porForma in formas.values():
            mas_usada = max(porForma.values())
            rotulo = sorted(nombre for nombre, cuantas in porForma.items() if cuantas == mas_usada)[0]
            pares.append((rotulo, rotulo, sum(porForma.values())))
        pares.append(
            (
                comodin,
                comodin_texto,
                cuenta(lambda t, n=cual: not (getattr(t, n) or "").strip()),
            )
        )
        return pares

    return FiltrosDeLasTierras(
        cultivos=opciones(
            juntando_sin_mayusculas(
                "cultivo_clave", "sin_cultivo", textos.TIERRA_Y_MAPA["sin_cultivo"]
            )
        ),
        municipios=opciones(
            juntando_sin_mayusculas("municipio", "sin_pueblo", textos.TIERRA_Y_MAPA["sin_pueblo"])
        ),
        revisiones=opciones(
            [
                (
                    estado,
                    versiones_de_recinto.texto_del_estado_de_revision(estado),
                    cuenta(lambda t, e=estado: t.estado_revision == e),
                )
                for estado in versiones_de_recinto.ESTADOS_DE_REVISION
            ]
            + [
                (
                    "sin_version",
                    textos.TIERRA_Y_MAPA["revision_sin_version"],
                    cuenta(lambda t: t.estado_revision is None),
                )
            ]
        ),
        pac=opciones(
            [
                (
                    "con_referencia",
                    textos.TIERRA_Y_MAPA["pac_con_referencia"],
                    cuenta(lambda t: t.tiene_referencia_completa),
                ),
                (
                    "sin_referencia",
                    textos.TIERRA_Y_MAPA["pac_sin_referencia"],
                    cuenta(lambda t: not t.tiene_referencia_completa),
                ),
                (
                    "con_hectareas",
                    textos.TIERRA_Y_MAPA["pac_con_hectareas"],
                    cuenta(lambda t: t.tiene_hectareas_dichas),
                ),
                (
                    "sin_hectareas",
                    textos.TIERRA_Y_MAPA["pac_sin_hectareas"],
                    cuenta(lambda t: not t.tiene_hectareas_dichas),
                ),
            ]
        ),
    )


def _columnas_que_una_correccion_no_toca(modelo, entrada, salida) -> list[str]:
    """Las columnas que la corrección **deja como estaban**, y por qué.

    **La regla: solo se corrige lo que el formulario puede mandar de vuelta, y el formulario se
    rellena con lo que devuelve la API.** Una columna que la API no acepta al dar de alta
    (`entrada`) o que no devuelve nunca (`salida`) es un dato que el agricultor no puede ni ver ni
    escribir: si la corrección la copiara del registro preparado, **la borraría sin que nadie se
    enterase**.

    Vale para las dos cosas que se corrigen en este fichero (la tierra y el grupo) y se **calcula**
    en vez de escribirse a mano a propósito: así vale sola el día que se añada una columna nueva
    —lo que no se puede mandar, no se toca—, y hay una prueba que exige que salgan exactamente las
    que salen hoy.

    En la **tierra** son tres, y las tres importan:

      · **`geometria`: la forma del trozo**, que es lo que dibuja el mapa y de donde sale el centro.
        Está en la entrada (el alta la manda, cuando se elige el recinto en el mapa) pero **no en la
        salida**, y no es un olvido: lo que viaja al móvil es la línea que se pinta, no el WKT
        entero, que son cientos de caracteres por tierra. Como el formulario de corregir no la
        tiene, sin esta regla ponerle el nombre bueno a una tierra **le borraba el dibujo** y el
        mapa se quedaba sin el trozo.
      · **`superficie_sigpac_ha`**: la superficie oficial del recinto entero, que solo sabe el
        conector del SIGPAC y que el cuaderno de la Junta pide aparte (hoja 2.1).
      · **`creada_en`**: cuándo se apuntó la tierra, que no es un dato que se corrija nunca. Se llama
        en femenino, así que se le escapa a la lista de `correcciones` (que protege `creado_en`) y
        hay que cuidarla aquí.

    En el **grupo** es una: `creado_automaticamente`, que dice si lo juntó el programa o el
    agricultor. No se pregunta en el formulario y es lo que decide qué se le ofrece después, así que
    ponerle el nombre bueno a un grupo no puede cambiarlo de dueño.

    El día que la forma del trozo tenga que poder corregirse, lo que hay que hacer es devolver
    `geometria` en `ParcelaSalida` (o hacer una ruta propia para el dibujo), y esta cuenta dejará de
    protegerla sola.
    """
    acepta_la_entrada = set(entrada.model_fields)
    devuelve_la_salida = set(salida.model_fields)
    return [
        nombre
        for nombre in correcciones.campos_corregibles(modelo)
        if nombre not in acepta_la_entrada or nombre not in devuelve_la_salida
    ]


def _preparar_parcela_guardable(
    datos: ParcelaEntrada, explotacion, *, actual: models.Parcela | None = None
) -> models.Parcela:
    """Comprueba una tierra y la devuelve lista para guardar, **sin guardarla**.

    Lo usan el alta y la corrección, y **es a propósito**: las dos tienen que pasar por las mismas
    comprobaciones y las mismas cuentas. Si la corrección copiara lo que manda el navegador sin
    más, una tierra corregida podría quedarse con un sistema que el alta no habría aceptado nunca, o
    con la zona de nitratos sin volver a mirar el listado oficial.

    `actual` es la tierra que se está corrigiendo, y sirve para **dejar quieto lo que el formulario
    no puede mandar**: la forma del trozo, la superficie del recinto y la fecha en que se apuntó
    (ver `_columnas_que_una_correccion_no_toca`). Es el mismo cuidado que ya se tuvo con el
    ecorregimen y la superficie cultivada al corregir el cultivo declarado.
    """
    # El sistema tiene que ser uno de los dos que distingue el cuaderno. Se rechaza con la lista
    # delante: guardarlo tal cual dejaría la tierra con un sistema que no existe.
    #
    # **Y «ninguno» es una respuesta válida** (A10 de `docs/T02_VALORES_POR_DEFECTO.md`): `None` es
    # «no lo sé», que es distinto de un sistema inventado. Antes esta comprobación rechazaba el
    # `None`, así que la única forma de guardar una tierra era declararla de secano o de regadío
    # aunque nadie lo supiera; ahora se puede apuntar sin decirlo y el programa lo pregunta.
    if datos.sistema is not None and datos.sistema not in catalogos.SISTEMAS_EXPLOTACION:
        raise HTTPException(
            status_code=422,
            detail=textos.mensaje("V23_sistema_desconocido"),
        )

    valores = datos.model_dump()
    # Zona vulnerable a nitratos. Tres casos, y el orden importa:
    #
    #   1. Si la lista oficial dice que SÍ, es que sí. No es una opinión del
    #      agricultor: es lo que dice la ley, y manda sobre lo que él haya puesto.
    #      Preguntarle está bien para cuando no sabemos nada, pero no para dejarle
    #      contradecir el listado oficial.
    #   2. Si él no lo sabe (None) y hay lista cargada, se deduce de ella.
    #   3. Si no hay lista cargada, se queda en None, que significa "no lo sé" y hace
    #      que la aplicación pregunte en vez de afirmar.
    # La dirección de la explotación no demuestra dónde está esta parcela.
    # Sin ubicación propia comprobable, el listado no puede decidir ni sí ni no.
    en_lista = catalogos.es_zona_vulnerable(
        valores.get("municipio"), valores.get("provincia"), valores.get("codigo_ine")
    )
    if en_lista is True:
        valores["zona_vulnerable_nitratos"] = True
    elif valores.get("zona_vulnerable_nitratos") is None:
        valores["zona_vulnerable_nitratos"] = en_lista

    parcela = models.Parcela(explotacion_id=explotacion.id, **valores)
    if actual is not None:
        # Lo que el formulario no puede mandar de vuelta se queda como estaba (ver la regla).
        for columna in _columnas_que_una_correccion_no_toca(
            models.Parcela, ParcelaEntrada, ParcelaSalida
        ):
            setattr(parcela, columna, getattr(actual, columna))
    return parcela


@router.post("/parcelas", response_model=ParcelaSalida, status_code=status.HTTP_201_CREATED)
def crear_parcela(
    datos: ParcelaEntrada, explotacion: ExplotacionActual, db: Db
) -> models.Parcela:
    parcela = _preparar_parcela_guardable(datos, explotacion)
    db.add(parcela)
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="parcela",
            accion="crear",
            datos={"alias": parcela.alias, "superficie_ha": parcela.superficie_ha},
        )
    )
    db.commit()
    return parcela


@router.post("/parcelas/desde-sigpac", response_model=ParcelaSalida, status_code=status.HTTP_201_CREATED)
def crear_parcela_desde_el_sigpac(
    datos: ParcelaDesdeSigpac, explotacion: ExplotacionActual, db: Db
) -> models.Parcela:
    """Trae los datos de un recinto del SIGPAC y da de alta la parcela.

    Es lo que ahorra teclear cuarenta parcelas por ocho datos cada una, que es el momento en el
    que la gente abandona una aplicación nueva. Se le da la referencia (la del papel del SIGPAC
    o la que dice el técnico) y el resto viene solo: superficie, pendiente, uso y el dibujo del
    trozo.

    Decisión sobre la provincia y el municipio: **el SIGPAC público solo publica sus códigos
    numéricos, no sus nombres**. El código SIGPAC no se equipara al INE sin correspondencia
    oficial verificada; el recinto de ejemplo usa 37-22 y Peñaranda de Bracamonte es 37246 en
    el listado municipal de IDECyL. Tampoco se copia el municipio de la explotación: una
    parcela puede estar en otro. Solo se identifican por los nombres que el usuario facilite.

    Si el SIGPAC no contesta, se dice y se deja meter la parcela a mano. Un conector que
    rellena la superficie con lo que le parece sería peor que no tenerlo.
    """
    # Se acepta cualquier forma de escribirla, no solo los siete números: la del visor del SIGPAC
    # (seis, con el recinto aparte) y la referencia catastral del Catastro llevan dentro los
    # mismos datos, y era absurdo rechazarlas teniéndolas el agricultor en la mano.
    try:
        busqueda = sigpac.lee_busqueda(datos.ref_sigpac)
    except sigpac.ReferenciaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

    if not busqueda.es_completa:
        raise HTTPException(
            status_code=422,
            detail=textos.SIGPAC["falta_el_recinto"],
        )

    try:
        recinto = sigpac.pedir_recinto(busqueda.con_recinto(busqueda.recinto or 0))
    except sigpac.SigpacNoContesta as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se ha podido preguntar al SIGPAC. Puede ser la cobertura o que el servicio "
                "no esté disponible. Se puede apuntar la parcela a mano y traerla otro día. "
                f"({error})"
            ),
        ) from None

    if recinto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"El SIGPAC no tiene ningún recinto con la referencia "
                f"{busqueda.con_recinto(busqueda.recinto or 0).como_texto()}. "
                "Mira que los siete números estén bien copiados."
            ),
        )

    parcela = _alta_desde_recinto(
        db,
        explotacion,
        recinto=recinto,
        alias=datos.alias,
        municipio=datos.municipio,
        provincia=datos.provincia,
        sistema=datos.sistema,
        referencia_catastral=busqueda.referencia_catastral or datos.referencia_catastral,
    )
    db.commit()
    return parcela


@router.get("/municipios")
def los_municipios(buscar: str | None = None, provincia: str | None = None) -> dict:
    """Los municipios de Castilla y León, para **elegir el pueblo en vez de escribirlo**.

    Es la lista oficial del INE, la misma numeración que el visor del SIGPAC y la referencia
    catastral (ver `data/municipios_ine_fuentes/`). Se sirve sin sesión porque no lleva datos de
    nadie: es la lista de municipios de la comunidad.

    Sin `buscar` se devuelven las provincias y el total, que es lo que hace falta para pintar el
    primer paso; con `buscar` se devuelven hasta 25 municipios que empiecen por lo escrito (o que
    lo lleven dentro), sin tildes y sin distinguir mayúsculas.
    """
    municipios = catalogos.busca_municipios(buscar or "", provincia=provincia)
    return {
        "textos": textos.MUNICIPIOS,
        "provincias": catalogos.provincias_con_municipios(),
        "municipios": [
            {
                "nombre": municipio.nombre,
                "provincia": municipio.provincia,
                "codigo_ine": municipio.codigo_ine,
                # El código de tres cifras que sale en el visor del SIGPAC («70 - CALVARRASA DE
                # ARRIBA») y el que va dentro de la referencia del recinto.
                "codigo_municipio": municipio.codigo_municipio,
                "codigo_provincia": municipio.codigo_provincia,
            }
            for municipio in municipios
        ],
        "cuantos": len(municipios),
        "total": len(catalogos.municipios_de_cyl()),
    }


@router.post("/sigpac/buscar")
def buscar_los_trozos(datos: BuscarRecintosEntrada, _: UsuarioActual) -> dict:
    """Busca los trozos (recintos) que hay en una parcela, para poder elegirlos.

    **Por qué existe esto.** Para traer una parcela del SIGPAC había que saberse los siete
    números, incluido el recinto. El agricultor no los sabe: en el visor su parcela se lee
    `37:70:0:0:503:51` y el recinto va en otra columna. Las aplicaciones oficiales del FEGA lo
    resuelven igual que esto: se meten provincia, municipio, agregado, zona, polígono y parcela,
    se pulsa buscar, y sale la lista de recintos para marcar los que son suyos.

    Devuelve, de cada trozo, lo que hace falta para reconocerlo: la superficie, el uso, la
    pendiente y si tiene dibujo. Los datos de cada recinto se piden **solo de los que ha
    encontrado esta búsqueda**, que son los de esa parcela y nada más.

    **Pide sesión desde el 03/10/2026, y antes no la pedía.** Es la ruta que **más llamadas de
    salida hace de todo el programa**: hasta **26** al SIGPAC del FEGA por cada petición (una
    lista y hasta 25 fichas, con 10 s de espera cada una), y la revisión de rutas sin sesión
    (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §5.1) encontró que **no había ningún límite**. Es
    decir: cualquiera que supiera la dirección podía encargar 26 llamadas al servicio público por
    petición, sin cuenta y sin tope, y el que se queda sin poder dar de alta sus tierras —si al
    FEGA le molesta el tráfico y corta la dirección— es el agricultor.

    Va con `UsuarioActual` y no con `ExplotacionActual` porque la búsqueda no lleva ninguna finca
    —se pregunta por un recinto del SIGPAC— pero **sí hace falta saber quién pregunta**: es la
    puerta por la que se pondrá el tope por cuenta. No rompe nada: la única pantalla que la llama
    ya manda su vale (`app.js:6999`, por `apiJson`, que siempre pone el vale).
    """
    try:
        busqueda = _busqueda_de_lo_que_ha_dicho(datos)
    except sigpac.ReferenciaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

    try:
        encontrados = sigpac.pedir_recintos(busqueda)
    except sigpac.SigpacNoContesta:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=textos.SIGPAC["sin_permiso_red"],
        ) from None

    datos_del_municipio = _municipio_elegido(datos.provincia, datos.municipio)
    trozos = []
    for recinto in encontrados[:MAX_RECINTOS_POR_BUSQUEDA]:
        detalle = sigpac.pedir_recinto(busqueda.con_recinto(recinto.recinto or 0))
        # Si de un recinto no se han podido traer los datos, se enseña con lo que se sabe: es
        # mejor poder marcar el trozo que no poder marcar ninguno porque uno haya fallado.
        completo = detalle or recinto
        trozos.append(
            {
                "recinto": completo.recinto,
                "referencia": completo.ref_sigpac,
                "superficie_ha": completo.superficie,
                "uso_sigpac": completo.uso_sigpac,
                "uso": sigpac.etiqueta_uso(completo.uso_sigpac),
                "pendiente_pct": completo.pendiente_media,
                "altitud": completo.altitud,
                "coeficiente_regadio": completo.coef_regadio,
                "tiene_dibujo": bool(completo.wkt),
            }
        )

    return {
        "textos": textos.SIGPAC,
        "busqueda": busqueda.como_texto(),
        "referencia_catastral": busqueda.referencia_catastral,
        "municipio": datos_del_municipio,
        "encontrados": len(trozos),
        "recintos": trozos,
        "mensaje": None if trozos else textos.SIGPAC["sin_recintos"],
    }


@router.post("/parcelas/desde-sigpac/varias")
def crear_varias_parcelas_desde_el_sigpac(
    datos: VariasParcelasDesdeSigpac, explotacion: ExplotacionActual, db: Db
) -> dict:
    """Da de alta **de una vez** todos los trozos que el agricultor ha marcado o pegado.

    Es lo que quita el trabajo de verdad: cuarenta parcelas son cuarenta referencias, y hacerlas
    de una en una es donde se abandona. Se admiten las tres formas de referencia que el
    agricultor tiene delante (la del visor, los siete números y la catastral).

    **No se para en el primer fallo.** Se intentan todas y se devuelve la cuenta con el motivo de
    cada una que no ha ido: si tres de cuarenta están mal copiadas, tener las otras treinta y
    siete dentro es lo que hace que el agricultor siga; tirarlo todo y decirle «error» no.
    """
    creadas: list[dict] = []
    fallos: list[dict] = []

    # Con varias referencias, el nombre que haya escrito el agricultor no puede ser el mismo para
    # todas: «El Prado» tres veces no distingue nada. Se le añade el trozo —«El Prado (trozo 2)»—,
    # que es como lo llamaría él. Con una sola, se respeta su nombre tal cual.
    varias = len([r for r in datos.referencias if (r or "").strip()]) > 1

    for texto_referencia in datos.referencias:
        crudo = (texto_referencia or "").strip()
        if not crudo:
            continue
        try:
            busqueda = sigpac.lee_busqueda(crudo)
            if not busqueda.es_completa:
                # Sin recinto no se puede traer: para eso está la búsqueda, que devuelve la lista
                # de trozos de la parcela y el agricultor marca los suyos.
                fallos.append({"referencia": crudo, "motivo": textos.SIGPAC["falta_el_recinto"]})
                continue
            referencia = busqueda.con_recinto(busqueda.recinto or 0)
            recinto = sigpac.pedir_recinto(referencia)
            if recinto is None:
                fallos.append({"referencia": crudo, "motivo": textos.SIGPAC["no_encontrado"]})
                continue
            parcela = _alta_desde_recinto(
                db,
                explotacion,
                recinto=recinto,
                alias=(
                    f"{(datos.alias or '').strip()} (trozo {recinto.recinto})"
                    if varias and (datos.alias or "").strip()
                    else datos.alias
                ),
                municipio=datos.municipio,
                provincia=datos.provincia,
                sistema=datos.sistema,
                referencia_catastral=busqueda.referencia_catastral or datos.referencia_catastral,
            )
        except sigpac.ReferenciaInvalida as error:
            fallos.append({"referencia": crudo, "motivo": str(error)})
            continue
        except sigpac.SigpacNoContesta:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=textos.SIGPAC["sin_permiso_red"],
            ) from None
        creadas.append({"id": parcela.id, "alias": parcela.alias, "ref_sigpac": parcela.ref_sigpac})

    db.commit()
    return {
        "textos": textos.SIGPAC,
        "creadas": creadas,
        "cuantas": len(creadas),
        "fallos": fallos,
        "mensaje": textos.mensaje_con_cuenta("parcelas_traidas", len(creadas)) if creadas else None,
    }


@router.get("/sigpac/estado")
def estado_del_sigpac() -> dict:
    """Qué datos oficiales del SIGPAC hay cargados, y de dónde salen.

    Se sirve sin sesión porque no lleva datos de nadie: es la información de qué hay descargado
    y cómo actualizarlo.
    """
    return {
        "textos": textos.SIGPAC,
        **sigpac.datos_disponibles(),
    }


@router.post("/sigpac/consultar")
def consultar_un_recinto(datos: ReferenciaSigpacEntrada, _: UsuarioActual) -> dict:
    """Pregunta al SIGPAC por un recinto **sin dar de alta nada**.

    Existe para poder comprobar una referencia antes de apuntarla: el agricultor no tiene por
    qué fiarse de que la ha copiado bien.

    **Pide sesión desde el 03/10/2026, y antes no la pedía.** Es la más grave de las cuatro rutas
    que la revisión de rutas sin sesión dejó marcadas como «debería pedir sesión»
    (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.17), y por un motivo concreto: **cada llamada
    sale a internet, al SIGPAC del FEGA, y no había ni caché ni límite**. Cualquiera que
    encontrara la dirección podía usar esta instalación como repetidor contra un servicio
    público, y el que se queda sin poder dar de alta sus tierras por eso —si al FEGA le molesta
    el tráfico y corta la dirección— es el agricultor. Con la sesión por delante, el que pregunta
    es quien tiene cuenta aquí.

    Pide `UsuarioActual` y no `ExplotacionActual` **a propósito**: lo que se consulta es un dato
    público del recinto y no hay ninguna finca metida en la pregunta; lo que hace falta es saber
    **quién** pregunta, no de qué finca es.
    """
    try:
        referencia = sigpac.lee_referencia(datos.ref_sigpac)
    except sigpac.ReferenciaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from None

    try:
        respuesta = httpx.get(
            sigpac.url_recinto(referencia), timeout=sigpac.ESPERA_SEGUNDOS, follow_redirects=True
        )
        respuesta.raise_for_status()
    except Exception as error:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se ha podido preguntar al SIGPAC ({type(error).__name__}).",
        ) from None

    recinto = sigpac.lee_recinto(respuesta.text)
    if recinto is None:
        return {
            "encontrado": False,
            "ref_sigpac": referencia.como_texto(),
            "mensaje": textos.SIGPAC["no_encontrado"],
        }
    return {
        "encontrado": True,
        "ref_sigpac": recinto.ref_sigpac,
        "superficie_ha": recinto.superficie,
        "pendiente_pct": recinto.pendiente_media,
        "uso_sigpac": recinto.uso_sigpac,
        "uso": sigpac.etiqueta_uso(recinto.uso_sigpac),
        "altitud": recinto.altitud,
        "tiene_dibujo": bool(recinto.wkt),
        "consulta": sigpac.url_recinto(referencia),
    }


@router.get("/cultivos")
def los_cultivos_de_la_finca(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> dict:
    """Qué hay sembrado en cada parcela este año, y qué hubo los años anteriores.

    Es la pestaña «Características DGC» y la de «Historial Cultivos» de la app oficial, juntas.
    Existe porque el cuaderno pedía este dato —«a El Prado le falta decir qué cultivo tiene este
    año»— y **no había ninguna forma de dárselo**: la tabla estaba, el endpoint estaba, y no lo
    usaba ninguna pantalla.

    Decisión: se devuelven **todas las parcelas**, también las que no tienen cultivo declarado.
    Son justamente las que hay que enseñar, porque son las que están a medias.
    """
    campana = None
    if campana_id is not None:
        campana = obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    else:
        campana = db.scalar(
            select(models.Campana)
            .where(models.Campana.explotacion_id == explotacion.id)
            .order_by(models.Campana.anio.desc())
            .limit(1)
        )

    finca = servicios.los_cultivos_de_la_finca(
        db, explotacion_id=explotacion.id, campana_id=campana.id if campana else None
    )
    faltan = [parcela for parcela in finca if parcela["falta_decirlo"]]
    return {
        "textos": textos.CULTIVOS,
        "parcelas": finca,
        "campana_id": campana.id if campana else None,
        "campana_anio": campana.anio if campana else None,
        "cuantos": len(finca),
        "faltan": len(faltan),
        # Las tres respuestas, con «no lo sé» (A10): ver `catalogos.SISTEMAS_PARA_ELEGIR`.
        "sistemas": catalogos.SISTEMAS_PARA_ELEGIR,
        "resumen": (
            textos.CULTIVOS["sin_parcelas"]
            if not finca
            else (
                textos.CULTIVOS["todo_dicho"]
                if not faltan
                else textos.con_cuenta(textos.CULTIVOS, "faltan", len(faltan))
            )
        ),
    }


@router.get("/parcelas/{parcela_id}", response_model=ParcelaSalida)
def ver_parcela(parcela_id: int, explotacion: ExplotacionActual, db: Db) -> models.Parcela:
    return obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)


@router.put("/parcelas/{parcela_id}", response_model=ParcelaSalida)
def corregir_parcela(
    parcela_id: int,
    datos: ParcelaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.Parcela:
    """Corrige una tierra ya apuntada. **No borra y no da de alta otra: cambia esa tierra.**

    POR QUÉ SE CORRIGE EN EL SITIO Y NO SE BORRA Y SE VUELVE A METER. Porque de esa tierra cuelgan
    los apuntes del cuaderno: borrarla obligaría a volver a apuntar todo lo que se hizo en ella, y
    los identificadores que viajan a la Junta cambiarían de una vez para otra. Corrigiendo aquí, la
    tierra sigue siendo la misma —mismo `id`— con los datos buenos, y lo que había antes queda
    escrito en la auditoría (`correcciones`).

    Y pasa por **las mismas comprobaciones y las mismas cuentas que el alta**, porque es la misma
    función (`_preparar_parcela_guardable`): el sistema y la zona de nitratos del listado oficial.
    """
    parcela = obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    preparado = _preparar_parcela_guardable(datos, explotacion, actual=parcela)
    correcciones.corregir(
        db,
        guardado=parcela,
        preparado=preparado,
        entidad="parcela",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return parcela


# --------------------------------------------------------------------------
# Qué se cuenta antes de borrar una tierra o un grupo
# --------------------------------------------------------------------------
#
# **Estas dos se han mudado a `correcciones.py`** (ronda 93): resultó que todo lo que se puede borrar
# tiene el mismo problema —un producto dentro de un tratamiento, una máquina usada en una labor, una
# campaña con apuntes—, así que la cuenta vive una sola vez y la usan todos los routers. Aquí quedan
# con su nombre de siempre (`_tablas_que_apuntan_a`) porque son las que usan las pruebas de esta
# parte, y renombrarlas no aportaría nada.
_tablas_que_apuntan_a = correcciones.tablas_que_apuntan_a
_cuantas_cosas_apuntan_a = correcciones.cuantas_filas_apuntan_a


def _cuantos_apuntes_tiene_la_tierra(db: Db, explotacion_id: int, parcela_id: int) -> int:
    """Cuántas cosas del cuaderno apuntan a esa tierra.

    Son las ocho que hay: tratamientos, abonos, labores, el cultivo declarado de una campaña,
    análisis, ventas, planes de abono y **la versión del recinto** (T05: la referencia y la forma
    que esa tierra tuvo en cada campaña y de qué fuente salió). Se cuentan **todas**, también las
    anuladas: siguen apuntando a esa tierra, y una tierra que desaparece con apuntes anulados
    encima sigue dejándolos sin sitio donde se hicieron.

    La lista no se escribe aquí: se saca de las tablas de verdad (`_tablas_que_apuntan_a`), así que
    el día que se añada otro apunte a una tierra esta cuenta lo incluye sola. Lo que hay que
    mantener al día es este comentario y la prueba que lo vigila
    (`test_las_tierras_se_pueden_corregir.py::test_las_tablas_que_apuntan_a_una_tierra_se_cuentan_todas`).
    """
    return sum(
        _cuantas_cosas_apuntan_a(db, modelo, "parcela_id", parcela_id, explotacion_id)
        for modelo in _tablas_que_apuntan_a("parcela_id")
    )


def _cuantos_apuntes_usan_el_grupo(db: Db, explotacion_id: int, grupo_id: int) -> int:
    """Cuántos apuntes del cuaderno se hicieron sobre ese grupo."""
    return sum(
        _cuantas_cosas_apuntan_a(db, modelo, "grupo_id", grupo_id, explotacion_id)
        for modelo in _tablas_que_apuntan_a("grupo_id")
    )


@router.delete("/parcelas/{parcela_id}")
def borrar_parcela(
    parcela_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Quita una tierra del cuaderno, **si no tiene nada apuntado encima**.

    POR QUÉ NO SE BORRA UNA TIERRA QUE TIENE APUNTES, aunque el agricultor lo pida. Es la única
    cosa que este programa no puede hacer: los tratamientos, los abonos, las labores, las cosechas,
    los análisis y las ventas apuntan a esa tierra por su identificador, y borrarla los dejaría sin
    decir **dónde se hizo el trabajo**, que es justo lo que se mira en una inspección. Sería
    destruir el cuaderno en silencio, y el cuaderno es lo único que este programa no puede
    estropear.

    Por eso no se borra y se calla: se contesta 409 diciendo **cuántas cosas dependen de ella y qué
    hacer**. Las dos salidas que se le dan son las que hay de verdad: borrar o corregir primero esos
    apuntes, o **corregir la tierra** en vez de borrarla —que es lo que quiere la mayoría de las
    veces que alguien se equivoca al escribirla (el nombre, las hectáreas)—.

    Si no depende nada de ella, se borra con `correcciones.borrar`, que deja escrito en la auditoría
    lo que había. Un apunte firmado no se puede borrar; una tierra **no se firma** (ver
    `firmas_api.ENTIDADES`), así que aquí no hay nada que comprobar por ese lado.
    """
    parcela = obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    dependencias = _cuantos_apuntes_tiene_la_tierra(db, explotacion.id, parcela_id)
    if dependencias:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B2_tierra_con_apuntes", dependencias),
        )
    correcciones.borrar(
        db,
        registro=parcela,
        entidad="parcela",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": parcela_id}


@router.get("/parcelas/{parcela_id}/cultivos")
def cultivos_de_parcela(parcela_id: int, explotacion: ExplotacionActual, db: Db) -> list[dict]:
    obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    cultivos = db.scalars(
        select(models.ParcelaCultivo).where(
            models.ParcelaCultivo.explotacion_id == explotacion.id,
            models.ParcelaCultivo.parcela_id == parcela_id,
        )
    )
    return [
        {
            "id": c.id,
            "campana_id": c.campana_id,
            "especie": c.especie,
            "variedad": c.variedad,
            "sistema": c.sistema,
            "fecha_inicio": c.fecha_inicio,
            "fecha_fin": c.fecha_fin,
            # El ecorregimen y la superficie cultivada vienen del cuaderno de la Junta cuando se
            # importa. Salen aquí para que la pantalla pueda enseñarlos y no sean un dato que se
            # guarda y no ve nadie.
            "ecorregimen": c.ecorregimen,
            "superficie_cultivada_ha": c.superficie_cultivada_ha,
        }
        for c in cultivos
    ]


@router.post("/parcelas/{parcela_id}/cultivos", status_code=status.HTTP_201_CREATED)
def asignar_cultivo(
    parcela_id: int, datos: CultivoEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    campana = obtener_de_la_explotacion(db, models.Campana, datos.campana_id, explotacion.id)

    # Una parcela tiene **un** cultivo por campaña. Si ya había uno, se corrige en vez de
    # añadir otro: dos cultivos a la vez en la misma parcela dejarían el cuaderno sin saber qué
    # había, y el agricultor que se equivoca al escribirlo tiene que poder arreglarlo sin que le
    # queden dos apuntes.
    existente = servicios.cultivo_declarado(
        db, explotacion_id=explotacion.id, parcela_id=parcela_id, campana_id=campana.id
    )
    if existente is not None:
        existente.especie = datos.especie
        existente.variedad = datos.variedad
        existente.sistema = datos.sistema
        existente.fecha_inicio = datos.fecha_inicio
        existente.fecha_fin = datos.fecha_fin
        # El ecorregimen y la superficie cultivada solo se pisan si vienen: la pantalla de
        # «qué hay sembrado» no los pregunta (los trae el cuaderno de la Junta al importar), así
        # que si se guardara lo que llega sin más, corregir el cultivo de una parcela importada
        # **borraría** esos dos datos sin que nadie se enterase.
        if datos.ecorregimen:
            existente.ecorregimen = datos.ecorregimen
        if datos.superficie_cultivada_ha is not None:
            existente.superficie_cultivada_ha = datos.superficie_cultivada_ha
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                entidad="parcela_cultivo",
                entidad_id=existente.id,
                accion="corregir_cultivo",
                datos={"especie": datos.especie, "campana_id": campana.id},
            )
        )
        db.commit()
        return {"id": existente.id, "especie": existente.especie, "corregido": True}

    cultivo = models.ParcelaCultivo(
        explotacion_id=explotacion.id,
        parcela_id=parcela_id,
        campana_id=campana.id,
        especie=datos.especie,
        variedad=datos.variedad,
        sistema=datos.sistema,
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
        ecorregimen=datos.ecorregimen,
        superficie_cultivada_ha=datos.superficie_cultivada_ha,
    )
    db.add(cultivo)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            entidad="parcela_cultivo",
            entidad_id=cultivo.id,
            accion="declarar_cultivo",
            datos={"especie": datos.especie, "campana_id": campana.id},
        )
    )
    db.commit()
    return {"id": cultivo.id, "especie": cultivo.especie, "corregido": False}


@router.delete("/parcelas/{parcela_id}/cultivos/{campana_id}")
def quitar_cultivo(
    parcela_id: int,
    campana_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Deja una tierra **sin decir qué tiene sembrado** ese año.

    Existe porque **quitar no es lo mismo que cambiar**. Un agricultor puede darse cuenta de que esa
    tierra estaba en barbecho, o de que el cultivo que declaró era de otra parcela: hasta ahora la
    única salida era escribir otro cultivo, que es dejar un dato falso en el cuaderno. Con esto, la
    tierra vuelve a salir en «Qué hay sembrado» como una a la que **le falta decirlo**, con su botón
    para volver a decirlo (`servicios.los_cultivos_de_la_finca`).

    Se quita con `correcciones.borrar`, así que queda en la auditoría lo que estaba declarado. La
    campaña se comprueba antes: la de otra finca contesta 404, como todo en esta API.
    """
    obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
    obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)

    cultivo = servicios.cultivo_declarado(
        db, explotacion_id=explotacion.id, parcela_id=parcela_id, campana_id=campana_id
    )
    # La tierra y la campaña ya se han comprobado, así que llegar aquí significa que es suya y que
    # ese año no tiene nada dicho: se dice tal cual, en vez del «eso no está en tu cuaderno», que
    # aquí no explicaría nada.
    if cultivo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=textos.mensaje("B4_no_hay_cultivo_que_quitar"),
        )

    correcciones.borrar(
        db,
        registro=cultivo,
        entidad="parcela_cultivo",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {
        "borrado": True,
        "id": cultivo.id,
        "parcela_id": parcela_id,
        "campana_id": campana_id,
    }


# --------------------------------------------------------------------------
# Grupos de parcelas
# --------------------------------------------------------------------------


@router.get("/grupos")
def listar_grupos(explotacion: ExplotacionActual, db: Db) -> list[dict]:
    grupos = db.scalars(
        select(models.GrupoParcelas).where(
            models.GrupoParcelas.explotacion_id == explotacion.id
        )
    )
    return [
        {
            "id": g.id,
            "nombre": g.nombre,
            "cultivo": g.cultivo,
            "sistema": g.sistema,
            "creado_automaticamente": g.creado_automaticamente,
            "parcela_ids": [p.id for p in g.parcelas],
            # **La suma, o `None` si a alguna tierra del grupo le falta la superficie** (A7). Una
            # suma a la que le falta un número no es una suma: devolver la de las demás daría un
            # total que parece bueno y con el que se decidiría si un apunte cupo dentro del grupo.
            # Y se dice cuántas tierras son las que no lo traen, para que la pantalla pueda
            # explicarlo en vez de enseñar un hueco.
            "superficie_total_ha": (
                None
                if any(p.superficie_ha is None for p in g.parcelas)
                else round(sum(p.superficie_ha for p in g.parcelas), 4)
            ),
            "tierras_sin_superficie": sum(
                1 for p in g.parcelas if p.superficie_ha is None
            ),
        }
        for g in grupos
    ]


def _preparar_grupo_guardable(
    datos: GrupoEntrada, explotacion, db: Db, *, actual: models.GrupoParcelas | None = None
) -> models.GrupoParcelas:
    """Comprueba un grupo y lo devuelve listo para guardar, **sin guardarlo**.

    Lo usan el alta y la corrección, para que las dos exijan lo mismo (al menos dos tierras, y todas
    de esta finca) y para que un grupo corregido no pueda quedarse con una tierra de otro.

    `actual` es el grupo que se está corrigiendo, y sirve para dejar quieto lo que el formulario no
    puede mandar: con él, ponerle el nombre bueno a un grupo **no cambia de quién es el grupo** (si
    lo juntó el programa, sigue siendo del programa), que es lo que decide qué se le ofrece después.
    """
    if len(datos.parcela_ids) < 2:
        raise HTTPException(
            status_code=422,
            detail=textos.mensaje("V24_grupo_de_una_sola_tierra"),
        )
    parcelas = [
        obtener_de_la_explotacion(db, models.Parcela, pid, explotacion.id)
        for pid in datos.parcela_ids
    ]
    grupo = models.GrupoParcelas(
        explotacion_id=explotacion.id,
        nombre=datos.nombre,
        campana_id=datos.campana_id,
        cultivo=datos.cultivo,
        sistema=datos.sistema,
    )
    grupo.parcelas = parcelas
    if actual is not None:
        # Lo que el formulario no puede mandar de vuelta se queda como estaba (ver la regla).
        for columna in _columnas_que_una_correccion_no_toca(
            models.GrupoParcelas, GrupoEntrada, GrupoSalida
        ):
            setattr(grupo, columna, getattr(actual, columna))
    return grupo


def _grupo_como_salida(grupo: models.GrupoParcelas) -> GrupoSalida:
    """El grupo tal y como lo devuelve la API.

    Se construye a mano porque el modelo no tiene un campo `parcela_ids`, y devolver el objeto tal
    cual fallaría al serializar.
    """
    return GrupoSalida(
        id=grupo.id,
        nombre=grupo.nombre,
        campana_id=grupo.campana_id,
        cultivo=grupo.cultivo,
        sistema=grupo.sistema,
        creado_automaticamente=grupo.creado_automaticamente,
        parcela_ids=[p.id for p in grupo.parcelas],
    )


@router.post("/grupos", response_model=GrupoSalida, status_code=status.HTTP_201_CREATED)
def crear_grupo(
    datos: GrupoEntrada, explotacion: ExplotacionActual, db: Db
) -> GrupoSalida:
    grupo = _preparar_grupo_guardable(datos, explotacion, db)
    db.add(grupo)
    db.commit()
    return _grupo_como_salida(grupo)


@router.put("/grupos/{grupo_id}", response_model=GrupoSalida)
def corregir_grupo(
    grupo_id: int,
    datos: GrupoEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> GrupoSalida:
    """Corrige un grupo: su nombre, su cultivo, su sistema y las tierras que lleva dentro.

    Un grupo **no es un dato del cuaderno** —es la lista de tierras con las que se apunta de una
    vez—, pero lo que se cambia **sí queda escrito**, y por un motivo de peso: los apuntes que ya se
    hicieron con él guardan su identificador, no el de cada tierra. Si el grupo cambia de tierras,
    hay que poder saber cuáles tenía el día que se apuntó aquel tratamiento, y por eso el cambio de
    tierras se apunta aparte (`corregir_tierras`), con las de antes y las de ahora.
    """
    grupo = obtener_de_la_explotacion(db, models.GrupoParcelas, grupo_id, explotacion.id)
    tierras_antes = sorted(parcela.id for parcela in grupo.parcelas)

    preparado = _preparar_grupo_guardable(datos, explotacion, db, actual=grupo)
    correcciones.corregir(
        db,
        guardado=grupo,
        preparado=preparado,
        entidad="grupo",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )

    grupo.parcelas = preparado.parcelas
    tierras_ahora = sorted(parcela.id for parcela in grupo.parcelas)
    if tierras_ahora != tierras_antes:
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                usuario_id=usuario.id,
                entidad="grupo",
                entidad_id=grupo.id,
                accion="corregir_tierras",
                datos={"tierras_antes": tierras_antes, "tierras_ahora": tierras_ahora},
            )
        )
    db.commit()
    return _grupo_como_salida(grupo)


@router.delete("/grupos/{grupo_id}")
def borrar_grupo(
    grupo_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Deshace un grupo: **las tierras no se tocan**, lo que desaparece es la agrupación.

    POR QUÉ NO SE BORRA UN GRUPO QUE SE HA USADO. Los apuntes hechos sobre un grupo —un tratamiento
    para las seis tierras de una vez, su abono, su labor— guardan **el identificador del grupo** y no
    el de cada tierra. Sin el grupo, esos apuntes se quedarían sin decir dónde se hizo el trabajo, y
    el cuaderno dejaría de poder contestar la pregunta que más se hace en una inspección. Cuando eso
    pasa se contesta 409 con **cuántos apuntes** lo usan, que es lo que hay que resolver antes.

    Si no lo ha usado nadie, se borra con `correcciones.borrar` (queda el rastro). Las filas que
    enganchan el grupo con sus tierras se van con él: la base de datos las borra en cascada
    (`grupo_parcela`, `ondelete="CASCADE"`).
    """
    grupo = obtener_de_la_explotacion(db, models.GrupoParcelas, grupo_id, explotacion.id)
    usos = _cuantos_apuntes_usan_el_grupo(db, explotacion.id, grupo_id)
    if usos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("B3_grupo_con_apuntes", usos),
        )
    correcciones.borrar(
        db,
        registro=grupo,
        entidad="grupo",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": grupo_id}


@router.post("/grupos/calcular")
def calcular_grupos(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> dict:
    """Agrupa solas las parcelas que se llevan igual (unidad homogénea de cultivo).

    Devuelve también **por qué no se han podido juntar las que se quedan fuera**. Sin eso, pulsar
    el botón y que no pase nada no dice si ya estaban juntas o si falta algo, y el agricultor se
    queda mirando una pantalla que no le contesta.

    Decisión: si no se dice la campaña, **se coge la del año en curso**. Antes no: se pasaba tal
    cual, y como el cultivo de cada parcela es por campaña, sin campaña no había ningún cultivo
    declarado con el que agrupar. El botón no hacía nada y no decía por qué. Lo encontró el test.
    """
    if campana_id is not None:
        obtener_de_la_explotacion(db, models.Campana, campana_id, explotacion.id)
    else:
        campana = db.scalar(
            select(models.Campana)
            .where(models.Campana.explotacion_id == explotacion.id)
            .order_by(models.Campana.anio.desc())
            .limit(1)
        )
        campana_id = campana.id if campana else None

    grupos = servicios.crear_grupos_automaticos(
        db, explotacion_id=explotacion.id, campana_id=campana_id
    )
    return {
        "grupos_creados": len(grupos),
        "nombres": [g.nombre for g in grupos],
        "campana_id": campana_id,
        "no_se_pudieron": servicios.parcelas_que_no_se_pueden_juntar(
            db, explotacion_id=explotacion.id, campana_id=campana_id
        ),
    }


@router.get("/zonas-vulnerables/estado")
def estado_zonas_vulnerables() -> dict:
    """¿Está cargado el listado oficial de zonas vulnerables?

    Es información para el agricultor y para quien administra: mientras no esté
    cargado, el programa no puede afirmar que una parcela NO está en zona de
    nitratos, y lo dice en vez de callarse.
    """
    cargados = catalogos.cargar_zonas_vulnerables()
    return {
        "cargado": catalogos.hay_datos_zonas_vulnerables(),
        "municipios": cargados,
        "explicacion": textos.ZONAS_VULNERABLES_ESTADO[
            "cargado" if catalogos.hay_datos_zonas_vulnerables() else "sin_datos"
        ],
    }
