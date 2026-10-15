"""La maquinaria de la finca: la lista, la ficha, las inspecciones y las averías (T14, E8).

QUÉ HAY AQUÍ, Y POR QUÉ ES UN ROUTER NUEVO

El contrato pide una pantalla de maquinaria (`/maquinaria`, S16) con una tabla y una ficha que
**separa cinco cosas que hoy se mezclarían**: ITV, ITEAF, mantenimiento, seguro y ROMA. Hasta este
ticket lo único que había era `EquipoAplicacion` —«una máquina de echar producto»—, que existe para la
hoja 1.3 del cuaderno de la Junta y para decir con qué se echó cada tratamiento. El propio contrato lo
avisa en su §9: «`EquipoAplicacion` no cubre toda la maquinaria». Así que este router trabaja con
`models.Maquina`, y **no ha reutilizado el de echar producto como si fuera el inventario**: un remolque
dado de alta ahí habría acabado con un número de ROMA pedido y una ITEAF que no le toca.

Y **lo que no hace, que es lo más importante de este fichero**: no calcula ninguna fecha de
vencimiento, no deduce qué inspección le toca a una máquina por su nombre ni por su clase, y no da por
buena una obligación que nadie ha declarado. El porqué está escrito entero en `app/maquinaria.py`; aquí
solo se cumplen sus reglas:

  · La aplicabilidad de cada obligación la declara el agricultor y nace en «no lo sé».
  · La próxima fecha de una inspección es **la que trae el papel**, copiada tal cual.
  · Cuando no se sabe algo, se dice y se pide (el aviso `M9…`, `M7…`, `M8…`), en vez de enseñar una
    fecha sacada de la manga.

LO QUE SE CONSERVA DE LOS DEMÁS ROUTERS, A PROPÓSITO

  · Todo pasa por `obtener_de_la_explotacion`, que contesta **404 y no 403** para no contar si un
    identificador existe en otra finca.
  · Corregir una máquina no da de alta otra: se cambia esa y queda en la auditoría
    (`correcciones.corregir`), como las demás fichas de lo que se usa.
  · Una inspección o una avería **no se borra sin rastro**: se puede corregir, se puede anular con su
    motivo (y queda en la auditoría) y se puede borrar si fue un apunte equivocado.
  · El móvil que reintenta no apunta dos veces: `clave_de_reenvio`.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from .. import correcciones, maquinaria, models, textos
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AnulacionEntrada,
    AveriaEntrada,
    AveriaSalida,
    EquipoSinFichaSalida,
    FichaDeUnaMaquinaSalida,
    InspeccionEntrada,
    InspeccionSalida,
    MaquinaEntrada,
    MaquinaSalida,
    ObligacionEntrada,
    ObligacionSalida,
    TablaDeLaMaquinariaSalida,
)

router = APIRouter(prefix="/api", tags=["maquinaria"])


# --------------------------------------------------------------------------
# Las tablas que son **parte** de la máquina, y las que no
# --------------------------------------------------------------------------
#
# Esto existe por un motivo concreto y se ve en los dos sitios donde se usa (borrar una máquina y
# contar lo que la usa):
#
#   · Las **obligaciones**, las **inspecciones** y las **averías** de una máquina **no son otra cosa
#     que la usa**: son la máquina. Decir «esa máquina no se puede quitar porque la usan 3 cosas»
#     cuando las tres cosas son sus propias inspecciones sería absurdo, y es el mismo cuidado que
#     tiene `facturas_api` con las líneas de una factura.
#   · Cualquier otra tabla que mañana apunte a una máquina (una labor que diga con qué tractor se
#     hizo, por ejemplo) **sí** es una dependencia de verdad, y entonces se contesta 409 en vez de
#     dejar el apunte sin decir con qué se trabajó. La cuenta se saca de las tablas de verdad, no de
#     una lista escrita a mano, y hay una prueba que la lista: el día que aparezca la cuarta tabla,
#     esa prueba avisa y obliga a decidir.
TABLAS_QUE_SON_PARTE_DE_LA_MAQUINA: tuple[str, ...] = (
    "obligaciones_de_maquina",
    "inspecciones_de_maquina",
    "averias_de_maquina",
)


def _tablas_que_usan_una_maquina() -> list:
    """Las tablas que apuntan a una máquina y **no son parte de ella**. Ver la nota de arriba."""
    return [
        modelo
        for modelo in correcciones.tablas_que_apuntan_a("maquina_id")
        if modelo.__tablename__ not in TABLAS_QUE_SON_PARTE_DE_LA_MAQUINA
    ]


# --------------------------------------------------------------------------
# Comprobaciones que valen para el alta y para la corrección
# --------------------------------------------------------------------------


def _una_de_la_lista(valor: str, lista: tuple[str, ...], *, codigo: str, **extra) -> str:
    """Comprueba que lo que llega es una de las respuestas posibles, y lo dice con la frase del agricultor.

    **Por qué no basta con una lista cerrada en el esquema.** Porque el mensaje que da Pydantic está en
    inglés y habla de «input», y aquí el que lee es un agricultor. Y por qué se comprueba **aquí y no en
    el formulario**: el formulario es una comodidad, no una puerta; la puerta es esta.
    """
    limpio = (valor or "").strip().lower()
    if limpio not in lista:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje(codigo, valor=valor, **extra),
        )
    return limpio


def _el_papel_es_de_esta_finca(db: Db, explotacion, documento_id: int | None) -> None:
    """Si se apunta un papel, tiene que ser un papel de esta finca (y si no está, 404).

    Es la mitad del aislamiento entre fincas: sin esto, se podría dejar una inspección apuntando al
    documento de otra persona, y al abrirlo se vería su papel.
    """
    if documento_id is not None:
        obtener_de_la_explotacion(db, models.DocumentoAnexo, documento_id, explotacion.id)


def _el_equipo_es_de_esta_finca(db: Db, explotacion, equipo_id: int | None) -> None:
    """Y si la máquina dice ser uno de los equipos del cuaderno, tiene que ser un equipo de esta finca."""
    if equipo_id is not None:
        obtener_de_la_explotacion(db, models.EquipoAplicacion, equipo_id, explotacion.id)


def _el_equipo_no_esta_enlazado(
    db: Db, explotacion, equipo_id: int | None, *, permitido: int | None = None
) -> None:
    """Un equipo del cuaderno **es una máquina, no dos**: el enlace es único.

    `desde-equipo` ya lo comprobaba, pero por la puerta del alta y de la corrección se podía enlazar el
    mismo equipo a dos fichas distintas: quedaban dos máquinas diciendo ser el mismo pulverizador y, al
    corregir una, no se sabía cuál era la buena (lo encontró la revisión del ticket). Aquí se comprueba
    en un solo sitio, y `permitido` es la máquina que se está corrigiendo, para que guardarla sin tocar
    el enlace no se conteste a sí misma.
    """
    if equipo_id is None:
        return
    ya = db.scalar(
        select(models.Maquina).where(
            models.Maquina.explotacion_id == explotacion.id,
            models.Maquina.equipo_aplicacion_id == equipo_id,
        )
    )
    if ya is not None and (permitido is None or ya.id != permitido):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("M15_ese_equipo_ya_esta_en_la_lista", maquina=ya.nombre),
        )


def _llevar_al_cuaderno(db: Db, explotacion, maquina) -> None:
    """Lo que se apunta en la ficha de la máquina **llega al equipo del cuaderno**, si son la misma.

    **POR QUÉ HACE FALTA ESTO, Y POR QUÉ ES TANTO UN DATO COMO UNA PROMESA.** La hoja 1.3 del cuaderno de
    la Junta —el papel y el fichero que se le entregan— se compone de `EquipoAplicacion`
    (`routers/cuaderno._fila_de_la_maquina`: nombre, tipo, número de ROMA, número de serie y las dos
    fechas de la ITEAF). Si las dos fichas de la misma máquina se pudieran separar, el agricultor
    corregiría el ROMA en la pantalla nueva —que es donde el programa le dice que se corrige— y **el
    cuaderno que manda a la Junta seguiría llevando el número viejo**, sin que nada se lo diga. Eso es
    exactamente lo que no puede pasar en un cuaderno de campo.

    Lo que se copia es **lo que ya estaba escrito en la máquina**, no nada calculado: los datos que la
    hoja 1.3 pide (nombre, ROMA, serie, marca, modelo) y las dos fechas de la ITEAF, que salen de **la
    última inspección apuntada** —tal cual, con su fecha y su próxima fecha—.

    **Y lo que NO se hace: borrar.** Si la máquina no tiene ninguna inspección de la ITEAF, las fechas
    del equipo se quedan como estaban: vaciarlas sería tirar un dato que el agricultor escribió en la
    hoja 1.3 y que quizá apuntó allí y no aquí. Lo que sí se copia siempre son los datos de identidad,
    que son los mismos en las dos fichas.
    """
    if getattr(maquina, "equipo_aplicacion_id", None) is None:
        return
    equipo = db.get(models.EquipoAplicacion, maquina.equipo_aplicacion_id)
    if equipo is None or equipo.explotacion_id != explotacion.id:
        return
    equipo.nombre = maquina.nombre
    equipo.marca = maquina.marca
    equipo.modelo = maquina.modelo
    equipo.numero_roma = maquina.numero_roma
    equipo.numero_serie = maquina.numero_serie
    ultima = maquinaria.ultima_inspeccion(
        _inspecciones_de(db, explotacion, maquina.id), "iteaf"
    )
    if ultima is not None and ultima.fecha is not None:
        equipo.fecha_iteaf = ultima.fecha
        equipo.fecha_proxima_iteaf = ultima.proxima_fecha
    db.add(equipo)


def _el_nombre_hace_falta(nombre: str | None) -> str:
    """Una máquina sin nombre no se puede guardar, y se dice con la frase que explica por qué."""
    limpio = (nombre or "").strip()
    if not limpio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=textos.mensaje("M11_esa_maquina_necesita_nombre"),
        )
    return limpio


def _preparar_maquina_guardable(
    datos: MaquinaEntrada, explotacion, *, actual: models.Maquina | None = None
) -> models.Maquina:
    """Comprueba una máquina y la devuelve lista para guardar, **sin guardarla**.

    Lo usan el alta y la corrección, y **es a propósito**: las dos tienen que pasar por las mismas
    comprobaciones. Aquí es donde se comprueba que la clase, la propiedad y la disponibilidad están en
    sus listas, que el nombre hace falta, y que el papel y el equipo que se enlazan son de esta finca.
    """
    _el_nombre_hace_falta(datos.nombre)
    # **Las tres respuestas se exigen al dar de alta y se conservan al corregir.**
    # Son las tres donde un valor de partida sería una afirmación que nadie ha hecho, así que **no nacen
    # contestadas**: al dar de alta una máquina, si no vienen, se dice (M12/M13) —y ahí está la mitad del
    # ticket—. Pero al **corregir**, no mandarlas no es decir que no haya respuesta: es no hablar de eso,
    # y la que había se queda. Antes eran obligatorias en el esquema, así que **corregir solo la matrícula
    # desde la API contestaba 422** y la máquina no se corregía (lo midió la revisión independiente del
    # T14, 05/10/2026). Se resuelven aquí, que es donde se sabe si esto es un alta o una corrección.
    respuestas = {}
    for campo, lista, codigo in (
        ("clase", maquinaria.CLASES_DE_MAQUINA, "M12_eso_no_es_una_clase_de_maquina"),
        ("propiedad", maquinaria.PROPIEDADES, "M13_eso_no_es_una_de_las_respuestas"),
        ("disponibilidad", maquinaria.DISPONIBILIDADES, "M13_eso_no_es_una_de_las_respuestas"),
    ):
        dicho = getattr(datos, campo)
        if not (dicho or "").strip():
            if actual is None:
                # Un alta sin esta respuesta: se dice con la frase del agricultor, no se inventa nada.
                _una_de_la_lista("", lista, codigo=codigo)
            respuestas[campo] = getattr(actual, campo)
            continue
        respuestas[campo] = _una_de_la_lista(dicho, lista, codigo=codigo)
    # El papel y el equipo que se enlazan los comprueba quien llama (`crear_maquina` y
    # `corregir_maquina`), que es quien tiene la sesión a mano para buscar en esta finca.
    return models.Maquina(explotacion_id=explotacion.id, **{**datos.model_dump(), **respuestas})


# --------------------------------------------------------------------------
# Leer lo que hay
# --------------------------------------------------------------------------


def _maquinas_de_la_finca(db: Db, explotacion) -> list[models.Maquina]:
    return list(
        db.scalars(
            select(models.Maquina)
            .where(models.Maquina.explotacion_id == explotacion.id)
            .order_by(models.Maquina.nombre)
        )
    )


def _la_maquina_de(db: Db, explotacion, maquina_id: int) -> models.Maquina:
    """La máquina, comprobando que es de esta finca. Se usa donde hay que escribir en el cuaderno."""
    return obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)


def _obligaciones_de(db: Db, explotacion, maquina_id: int) -> list[models.ObligacionDeMaquina]:    return list(
        db.scalars(
            select(models.ObligacionDeMaquina).where(
                models.ObligacionDeMaquina.explotacion_id == explotacion.id,
                models.ObligacionDeMaquina.maquina_id == maquina_id,
            )
        )
    )


def _inspecciones_de(db: Db, explotacion, maquina_id: int) -> list[models.InspeccionDeMaquina]:
    return list(
        db.scalars(
            select(models.InspeccionDeMaquina)
            .where(
                models.InspeccionDeMaquina.explotacion_id == explotacion.id,
                models.InspeccionDeMaquina.maquina_id == maquina_id,
            )
            .order_by(models.InspeccionDeMaquina.fecha.desc(), models.InspeccionDeMaquina.id.desc())
        )
    )


def _averias_de(db: Db, explotacion, maquina_id: int) -> list[models.AveriaDeMaquina]:
    return list(
        db.scalars(
            select(models.AveriaDeMaquina)
            .where(
                models.AveriaDeMaquina.explotacion_id == explotacion.id,
                models.AveriaDeMaquina.maquina_id == maquina_id,
            )
            .order_by(models.AveriaDeMaquina.fecha.desc(), models.AveriaDeMaquina.id.desc())
        )
    )


def _los_avisos(maquina, obligaciones, inspecciones, averias) -> list[dict]:
    """Los avisos de una máquina, **con la frase ya escrita**.

    El texto se pide por su código a `textos.py`, que es la regla de la casa: ni una frase para el
    agricultor escrita en un router. El módulo puro (`maquinaria.py`) devuelve el código y los datos;
    aquí se convierte en lo que se enseña.
    """
    salida = []
    for aviso in maquinaria.avisos_de_una_maquina(
        maquina=maquina, obligaciones=obligaciones, inspecciones=inspecciones, averias=averias
    ):
        datos = dict(aviso["datos"])
        if datos.get("obligacion"):
            # La obligación se nombra con la palabra que el agricultor lee («ITV», «ITEAF»…), y esa
            # palabra vive en `textos.py` como todo lo demás.
            datos["obligacion"] = textos.MAQUINARIA_DE_LA_FINCA.get(
                f"obligacion_{datos['obligacion']}", datos["obligacion"]
            )
        salida.append(
            {
                "codigo": aviso["codigo"],
                "mensaje": textos.mensaje(aviso["codigo"], **datos),
                "tipo": aviso["tipo"],
                "urgente": aviso["urgente"],
            }
        )
    return salida


def _el_resumen(maquina, obligaciones, inspecciones, averias) -> dict:
    return maquinaria.resumen_de_una_maquina(
        maquina=maquina, obligaciones=obligaciones, inspecciones=inspecciones, averias=averias
    )


def _fila_de_la_tabla(db: Db, explotacion, maquina) -> dict:
    """Una fila: la máquina y el resumen que calcula `maquinaria.py`. Ver `maquinaria.resumen_de_una_maquina`."""
    obligaciones = _obligaciones_de(db, explotacion, maquina.id)
    inspecciones = _inspecciones_de(db, explotacion, maquina.id)
    averias = _averias_de(db, explotacion, maquina.id)
    return {
        **MaquinaSalida.model_validate(maquina).model_dump(),
        "resumen": _el_resumen(maquina, obligaciones, inspecciones, averias),
    }


def _los_equipos_sin_ficha(db: Db, explotacion) -> list[dict]:
    """Los equipos de echar producto del cuaderno que **todavía no están en la lista de maquinaria**.

    Es la mitad de la puerta de calidad del ticket: `EquipoAplicacion` no cubre toda la maquinaria, así
    que la lista es otra cosa; pero lo que ya estaba apuntado no puede desaparecer de la vista. Se
    enseñan aparte, diciendo qué son, y con el botón de traerlos.
    """
    ligados = set(
        db.scalars(
            select(models.Maquina.equipo_aplicacion_id).where(
                models.Maquina.explotacion_id == explotacion.id,
                models.Maquina.equipo_aplicacion_id.is_not(None),
            )
        )
    )
    equipos = db.scalars(
        select(models.EquipoAplicacion)
        .where(models.EquipoAplicacion.explotacion_id == explotacion.id)
        .order_by(models.EquipoAplicacion.nombre)
    )
    return [
        EquipoSinFichaSalida(
            id=equipo.id,
            nombre=equipo.nombre,
            tipo=equipo.tipo,
            titularidad=equipo.titularidad,
            numero_roma=equipo.numero_roma,
            fecha_proxima_iteaf=equipo.fecha_proxima_iteaf,
        ).model_dump()
        for equipo in equipos
        if equipo.id not in ligados
    ]


@router.get("/maquinaria", response_model=TablaDeLaMaquinariaSalida)
def listar_maquinaria(explotacion: ExplotacionActual, db: Db) -> dict:
    """La tabla de la maquinaria: una fila por máquina, con lo que la tabla pide.

    El contrato (§4, S16) pide estas columnas: máquina, tipo, matrícula o serie, propiedad o alquiler,
    horas, **próxima revisión**, documentación y disponibilidad. La próxima revisión sale de la fecha
    que traiga el papel, y **puede venir vacía con su cuenta de lo que falta por saber**: una tabla que
    solo enseña la fecha más próxima y calla las obligaciones sin fecha diría que está todo mirado.

    Los totales son **del conjunto entero**, no de lo que se ve: lo pide el contrato («las sumas no se
    calculan sobre la página visible»).
    """
    filas = [_fila_de_la_tabla(db, explotacion, maquina) for maquina in _maquinas_de_la_finca(db, explotacion)]
    return {
        "maquinas": filas,
        "total": len(filas),
        "con_avisos": sum(1 for fila in filas if fila["resumen"]["avisos"] > 0),
        "con_avisos_urgentes": sum(1 for fila in filas if fila["resumen"]["avisos_urgentes"] > 0),
        "equipos_sin_ficha": _los_equipos_sin_ficha(db, explotacion),
        "que_falta": list(maquinaria.QUE_FALTA),
    }


@router.get("/maquinaria/que-falta")
def que_falta_de_la_maquinaria() -> list[dict]:
    """Lo que el programa todavía no sabe calcular, para poder decirlo en la pantalla.

    No lleva finca ni máquina: es lo mismo para todo el mundo. Se sirve también por aquí (y no solo
    dentro de la tabla y de la ficha) porque la pantalla de ayuda lo enseña sin abrir ninguna máquina.
    """
    return list(maquinaria.QUE_FALTA)


@router.get("/maquinaria/avisos")
def avisos_de_la_maquinaria(
    explotacion: ExplotacionActual, db: Db, fecha: dt.date | None = None, maquina_id: int | None = None
) -> list[dict]:
    """**Los avisos al planificar un trabajo**: qué máquina no está para trabajar y a cuál se le ha
    pasado o se le va a pasar una inspección.

    Es lo que el contrato pide con dos palabras («avisos al planificar trabajo»), y se sirve aparte de
    la tabla porque quien lo necesita es otro sitio: el paso del asistente en el que se elige con qué
    máquina se hizo (o se va a hacer) un trabajo. Ahí no se está mirando una lista, se está decidiendo
    si se puede contar con ella.

    `fecha` es la fecha del trabajo, y sirve para que el aviso hable del día que importa: una
    inspección que vence mañana no impide el trabajo de hoy, y una que venció la semana pasada sí.
    """
    referencia = fecha
    consulta = select(models.Maquina).where(models.Maquina.explotacion_id == explotacion.id)
    if maquina_id is not None:
        consulta = consulta.where(models.Maquina.id == maquina_id)
    salida: list[dict] = []
    for maquina in db.scalars(consulta.order_by(models.Maquina.nombre)):
        obligaciones = _obligaciones_de(db, explotacion, maquina.id)
        inspecciones = _inspecciones_de(db, explotacion, maquina.id)
        averias = _averias_de(db, explotacion, maquina.id)
        los_suyos = maquinaria.avisos_de_una_maquina(
            maquina=maquina,
            obligaciones=obligaciones,
            inspecciones=inspecciones,
            averias=averias,
            referencia=referencia,
        )
        for aviso in maquinaria.avisos_al_planificar(los_suyos):
            datos = dict(aviso["datos"])
            if datos.get("obligacion"):
                datos["obligacion"] = textos.MAQUINARIA_DE_LA_FINCA.get(
                    f"obligacion_{datos['obligacion']}", datos["obligacion"]
                )
            salida.append(
                {
                    "codigo": aviso["codigo"],
                    "mensaje": textos.mensaje(aviso["codigo"], **datos),
                    "tipo": aviso["tipo"],
                    "urgente": aviso["urgente"],
                    "maquina_id": maquina.id,
                    "maquina": maquina.nombre,
                    # **Si esta máquina es uno de los equipos del cuaderno, se dice cuál**, y eso es lo
                    # que permite enseñar el aviso justo donde se elige la máquina para un trabajo: el
                    # asistente ofrece los equipos de la hoja 1.3, así que necesita poder pasar de uno de
                    # esos equipos a su máquina sin descargarse la lista entera.
                    "equipo_aplicacion_id": maquina.equipo_aplicacion_id,
                }
            )
    return salida


@router.post(
    "/maquinaria/desde-equipo/{equipo_id}",
    response_model=MaquinaSalida,
    status_code=status.HTTP_201_CREATED,
)
def traer_un_equipo_del_cuaderno(
    equipo_id: int, explotacion: ExplotacionActual, db: Db
) -> models.Maquina:
    """Trae a la lista de maquinaria un equipo de echar producto **que ya estaba en el cuaderno**.

    **POR QUÉ EXISTE ESTO, Y POR QUÉ NO SE COPIA TODO.** La puerta de calidad del ticket dice que
    `EquipoAplicacion` no cubre toda la maquinaria, y de ahí salen dos obligaciones: no usar el de
    echar producto como si fuera el inventario, y **no dejar fuera lo que ya estaba apuntado**. Esto
    resuelve la segunda: el pulverizador que ya estaba en la hoja 1.3 del cuaderno se trae aquí, y se
    enlazan los dos (`equipo_aplicacion_id`), de forma que corregirlo una vez lo corrige en los dos
    sitios y **no hay dos fichas de la misma máquina**.

    **Lo que se copia y lo que NO.**
      · Se copia lo que el agricultor ya había escrito: el nombre, el número de ROMA, la marca, el
        modelo y el número de serie.
      · **No se copia su titularidad como propiedad**, salvo cuando dice «propia», que es lo único que
        se puede traducir sin inventar: en el cuaderno «ajena» significa «no es del titular», que no es
        lo mismo que «alquilada». Lo que no se sabe se queda en «no lo sé», y su clase se pone como
        equipo de echar producto, que es lo que era.
      · **No se copia ninguna fecha de vencimiento calculada**, porque no hay ninguna: si el equipo ya
        tenía apuntada su última inspección y la fecha de la próxima, esas dos fechas se traen como una
        inspección de la máquina (con su resultado en «no lo pone el papel», que es la verdad: el equipo
        no guardaba el resultado) para que no se pierdan al dejar de mirar la hoja del cuaderno.
      · **Y si el cuaderno solo tenía la fecha de la próxima** —la hoja 1.3 las pregunta por separado—, esa
        fecha **no se pierde**: se guarda en su obligación (`proxima_fecha_declarada`) y la ficha dice que
        se sabe cuándo toca y **no** cuándo fue la última. Antes se quedaba sin traer, el equipo dejaba de
        salir en «los que todavía no están en la lista» y **la fecha desaparecía de la vista** (lo encontró
        la revisión del ticket).
      · Y lo **que no se puede deducir no se rellena**: la clasificación técnica se queda vacía y la
        pantalla la pide, que es justo lo que el contrato manda.
    """
    equipo = obtener_de_la_explotacion(db, models.EquipoAplicacion, equipo_id, explotacion.id)
    _el_equipo_no_esta_enlazado(db, explotacion, equipo.id)

    maquina = models.Maquina(
        explotacion_id=explotacion.id,
        nombre=equipo.nombre,
        clase="equipo_de_aplicacion",
        # **Vacía a propósito**: es lo que la ficha pide y lo que impide deducir qué le toca.
        clasificacion_tecnica=None,
        matricula=None,
        numero_serie=equipo.numero_serie,
        numero_roma=equipo.numero_roma,
        marca=equipo.marca,
        modelo=equipo.modelo,
        propiedad=maquinaria.PROPIA if (equipo.titularidad or "") == "propia" else maquinaria.NO_SE,
        horas=None,
        disponibilidad=maquinaria.NO_SE,
        equipo_aplicacion_id=equipo.id,
    )
    db.add(maquina)
    db.flush()

    # Y las fechas que ya estaban escritas, cada una donde puede vivir. **Se trae todo lo que hay**, que es
    # lo que impide que una fecha del cuaderno desaparezca de la vista al traer el equipo.
    if equipo.fecha_iteaf is not None:
        db.add(
            models.InspeccionDeMaquina(
                explotacion_id=explotacion.id,
                maquina_id=maquina.id,
                tipo="iteaf",
                fecha=equipo.fecha_iteaf,
                resultado=maquinaria.NO_CONSTA,
                proxima_fecha=equipo.fecha_proxima_iteaf,
                notas=(
                    "Traída del cuaderno de la Junta: es la última inspección que ya estaba apuntada "
                    "en este equipo."
                ),
            )
        )
    if equipo.fecha_iteaf is not None or equipo.fecha_proxima_iteaf is not None:
        db.add(
            models.ObligacionDeMaquina(
                explotacion_id=explotacion.id,
                maquina_id=maquina.id,
                tipo="iteaf",
                aplicabilidad=maquinaria.SI,
                # Lo dice el agricultor (lo tenía apuntado él), no una regla del programa.
                origen=maquinaria.ORIGEN_EL_AGRICULTOR,
                # **La próxima, cuando no hay inspección de la que sacarla.** Una inspección sin fecha no
                # diría cuándo fue, así que no se inventa: se guarda aquí y la ficha lo dice.
                proxima_fecha_declarada=(
                    equipo.fecha_proxima_iteaf if equipo.fecha_iteaf is None else None
                ),
                notas=(
                    "Lo tenías apuntado en el cuaderno para este equipo."
                    if equipo.fecha_iteaf is not None
                    else (
                        "En el cuaderno tenías apuntada la fecha de la próxima inspección, pero no la "
                        "de la última. Mírala en el papel y apúntala en su ficha."
                    )
                ),
            )
        )
    db.commit()
    return maquina


def _quien_lo_decidio(db: Db, explotacion, usuario_id: int | None) -> str | None:
    """El **nombre** de la cuenta que decidió, o `None` si no consta.

    **Por qué se resuelve al leer y no al escribir** (CRM-07 #6, 14/10/2026): la fila guarda el
    identificador y la ficha enseña el nombre, que es la convención de la casa —la bandeja guarda
    `confirmado_por_usuario_id` y enseña `Usuario.nombre`—. Es el mismo camino, escrito aquí porque
    el ayudante de la bandeja es suyo y privado.

    Y es **tolerante a propósito**, igual que aquel: una cuenta que ya no está, o que es de otra
    finca, **no puede tumbar la ficha entera con un error del servidor**. Lo que se dice es que no
    consta quién lo decidió, que es la verdad y además se puede arreglar volviendo a declararlo.
    """
    if not usuario_id:
        return None
    quien = db.get(models.Usuario, int(usuario_id))
    if quien is None or getattr(quien, "explotacion_id", None) != explotacion.id:
        return None
    return quien.nombre


def _la_ficha(db: Db, explotacion, maquina) -> dict:
    obligaciones = _obligaciones_de(db, explotacion, maquina.id)
    inspecciones = _inspecciones_de(db, explotacion, maquina.id)
    averias = _averias_de(db, explotacion, maquina.id)
    estados = maquinaria.estado_de_todas_las_obligaciones(
        obligaciones=obligaciones, inspecciones=inspecciones
    )
    # **El nombre de quien decidió se resuelve aquí, y solo aquí** (CRM-07 #6, 14/10/2026): de
    # `app/maquinaria.py` sale el identificador —esa función es pura y no tiene base de datos— y el
    # nombre se pone en este mismo estado que lee la ficha, para que la pantalla no tenga que volver
    # a buscar a nadie. Si la cuenta ya no está o es de otra finca, queda en `None` y no revienta.
    for estado in estados.values():
        estado["decidido_por"] = _quien_lo_decidio(
            db, explotacion, estado.get("decidido_por_usuario_id")
        )
    return {
        "maquina": maquina,
        # En el orden de la ficha (ITV, ITEAF, mantenimiento, seguro y ROMA), **las cinco siempre**:
        # una máquina de la que no se ha declarado nada enseña las cinco en «no se sabe», que es como
        # el agricultor se entera de que existen.
        "obligaciones": [estados[tipo] for tipo in maquinaria.OBLIGACIONES],
        "inspecciones": inspecciones,
        "averias": averias,
        "avisos": _los_avisos(maquina, obligaciones, inspecciones, averias),
        "resumen": _el_resumen(maquina, obligaciones, inspecciones, averias),
        "que_falta": list(maquinaria.QUE_FALTA),
        "fuente_de_las_obligaciones": maquinaria.FUENTE_DE_LA_OBLIGACION,
    }


@router.get("/maquinaria/{maquina_id}", response_model=FichaDeUnaMaquinaSalida)
def ficha_de_una_maquina(maquina_id: int, explotacion: ExplotacionActual, db: Db) -> dict:
    """La ficha entera: los datos, las cinco obligaciones, las inspecciones, las averías y los avisos."""
    maquina = obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)
    return _la_ficha(db, explotacion, maquina)


# --------------------------------------------------------------------------
# Dar de alta, corregir y quitar una máquina
# --------------------------------------------------------------------------


@router.post("/maquinaria", response_model=MaquinaSalida, status_code=status.HTTP_201_CREATED)
def crear_maquina(
    datos: MaquinaEntrada, explotacion: ExplotacionActual, db: Db
) -> models.Maquina:
    """Da de alta una máquina. **No le supone ninguna obligación**: eso lo declara el agricultor.

    **Y si el móvil reintenta la misma petición, no se apunta dos veces** (caso A12 del contrato): la
    pantalla manda `clave_de_reenvio` al abrir el formulario, y aquí se busca antes de crear. La clave
    se cierra **por finca**, como en las inspecciones, y un alta sin clave se comporta como siempre.
    """
    _el_equipo_es_de_esta_finca(db, explotacion, datos.equipo_aplicacion_id)
    _el_equipo_no_esta_enlazado(db, explotacion, datos.equipo_aplicacion_id)
    clave = (datos.clave_de_reenvio or "").strip() or None
    if clave:
        ya = db.scalar(
            select(models.Maquina).where(
                models.Maquina.explotacion_id == explotacion.id,
                models.Maquina.clave_de_reenvio == clave,
            )
        )
        if ya is not None:
            return ya
    maquina = _preparar_maquina_guardable(datos, explotacion)
    db.add(maquina)
    db.flush()
    # Y lo que se acaba de apuntar **llega al equipo del cuaderno**, si esta máquina es ese equipo.
    _llevar_al_cuaderno(db, explotacion, maquina)
    db.commit()
    return maquina


@router.put("/maquinaria/{maquina_id}", response_model=MaquinaSalida)
def corregir_maquina(
    maquina_id: int,
    datos: MaquinaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.Maquina:
    """Corrige una máquina. **No da de alta otra: cambia esa ficha.**

    Es lo que más se corrige de todo esto: la matrícula mal copiada, las horas, el número de ROMA o la
    clasificación técnica, que es un texto que se copia de un papel y del papel al programa se cambia
    una letra. Corrigiendo en el sitio, las inspecciones y las averías siguen colgando de la misma
    máquina, y lo que decía antes queda escrito en la auditoría.
    """
    maquina = obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)
    _el_equipo_es_de_esta_finca(db, explotacion, datos.equipo_aplicacion_id)
    # El mismo equipo no puede estar en dos máquinas; y la que se está corrigiendo **no se estorba a sí
    # misma** (guardarla sin tocar el enlace tiene que poder hacerse).
    _el_equipo_no_esta_enlazado(
        db, explotacion, datos.equipo_aplicacion_id, permitido=maquina.id
    )
    # **El identificador de la petición no se toca al corregir.** El constructor lo copia del cuerpo (que
    # casi nunca lo manda), así que sin esto **corregir una máquina borraría la clave con la que se dio de
    # alta** —y esa clave es lo único que evita que un reintento tardío de la cola del móvil dé de alta la
    # misma máquina otra vez—. Se guarda la que había y se deja como estaba.
    la_clave_del_alta = maquina.clave_de_reenvio
    preparado = _preparar_maquina_guardable(datos, explotacion, actual=maquina)
    preparado.clave_de_reenvio = la_clave_del_alta
    correcciones.corregir(
        db,
        guardado=maquina,
        preparado=preparado,
        entidad="maquina",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    # **Y la corrección llega al cuaderno**: es lo que hace verdad que corregir una vez lo corrige en los
    # dos sitios (ver `_llevar_al_cuaderno`).
    _llevar_al_cuaderno(db, explotacion, maquina)
    db.commit()
    return maquina


@router.delete("/maquinaria/{maquina_id}")
def quitar_maquina(
    maquina_id: int, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> dict:
    """Quita una máquina de la lista, **si no la usa ningún apunte y no tiene nada dentro**.

    Las dos condiciones son la misma regla vista desde dos sitios, y las dos se dicen con su cuenta:

      · Si un apunte del cuaderno dice que se trabajó con esta máquina, quitarla lo dejaría sin decir
        con qué se trabajó. Se contesta 409 y se dice qué hacer.
      · Si la máquina tiene inspecciones o averías apuntadas, quitarla se lleva por delante **lo que le
        pasaron**, que es justo lo que hay que poder enseñar en una inspección. También se dice, y se
        ofrece lo que sí vale: borrar o anular esas inspecciones y después quitar la máquina.
    """
    maquina = obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)
    dependencias = sum(
        correcciones.cuantas_filas_apuntan_a(db, modelo, "maquina_id", maquina_id, explotacion.id)
        for modelo in _tablas_que_usan_una_maquina()
    )
    if dependencias:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("M14_esa_maquina_no_se_puede_quitar", cuantas=dependencias),
        )
    dentro = len(_inspecciones_de(db, explotacion, maquina_id)) + len(_averias_de(db, explotacion, maquina_id))
    if dentro:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje_con_cuenta("M19_esa_maquina_tiene_cosas_apuntadas", dentro),
        )
    # Las obligaciones declaradas **sí se van con la máquina**: no son otra cosa que la máquina, y no
    # cuentan como dependencia (ver `TABLAS_QUE_SON_PARTE_DE_LA_MAQUINA`). Pero **se borran una a una y con
    # su rastro en la auditoría** (`correcciones.borrar`), y eso es una decisión, no una comodidad:
    #
    #   · **El rastro primero.** Antes se borraban con una sola sentencia (`delete(...)`) y de la
    #     declaración de cada una —«la ITV de este remolque no le toca, y lo dice el papel»— no quedaba
    #     nada escrito: lo que el agricultor había contestado desaparecía sin que el programa supiera que
    #     existió, que es justo lo contrario de la regla de la casa (lo encontró la revisión del ticket).
    #   · Y de paso resuelve el orden: cada borrado se confirma antes de tocar la máquina, así que la base
    #     de datos nunca ve una obligación apuntando a una máquina que ya no está (que es lo que reventaba
    #     cuando los dos borrados iban en la misma operación, porque entre las dos tablas no hay ninguna
    #     relación declarada que fije el orden).
    for obligacion in _obligaciones_de(db, explotacion, maquina_id):
        correcciones.borrar(
            db,
            registro=obligacion,
            entidad="obligacion_de_maquina",
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
        )
    correcciones.borrar(
        db, registro=maquina, entidad="maquina", explotacion_id=explotacion.id, usuario_id=usuario.id
    )
    return {"borrado": True, "id": maquina_id}


# --------------------------------------------------------------------------
# Las cinco obligaciones: qué le toca a esta máquina, y de dónde sale
# --------------------------------------------------------------------------


@router.put("/maquinaria/{maquina_id}/obligaciones/{tipo}", response_model=ObligacionSalida)
def declarar_una_obligacion(
    maquina_id: int,
    tipo: str,
    datos: ObligacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.ObligacionDeMaquina:
    """Dice si a esta máquina le toca una obligación, y de dónde sale eso.

    **Esto es lo que sustituye al cálculo prohibido.** El programa no sabe —ni puede saber, con lo que
    tiene transcrito— qué inspección le toca a una máquina por su nombre o por su clase; lo que hace es
    **preguntarlo**, guardar la respuesta con su origen y avisar de lo que falte. Y si el agricultor no
    contesta nada, la obligación se queda en «no lo sé», que no es lo mismo que «no le toca».

    Es un `PUT` porque **hay una sola respuesta por máquina y obligación**, y volver a contestar
    corrige la anterior (con su rastro en la auditoría) en vez de añadir otra.
    """
    obligacion_tipo = _una_de_la_lista(
        tipo, maquinaria.OBLIGACIONES, codigo="M17_eso_no_es_una_de_las_cinco_cosas"
    )
    aplicabilidad = _una_de_la_lista(
        datos.aplicabilidad,
        maquinaria.APLICABILIDADES,
        codigo="M13_eso_no_es_una_de_las_respuestas",
    )
    origen = _una_de_la_lista(
        datos.origen,
        maquinaria.ORIGENES_DE_LA_APLICABILIDAD,
        codigo="M13_eso_no_es_una_de_las_respuestas",
    )
    # **El papel tiene que ser de esta finca**, y es el mismo ayudante que usa la inspección (arriba):
    # sin esto, un `documento_id` de otra explotación se guardaría y la ficha enseñaría un papel ajeno.
    _el_papel_es_de_esta_finca(db, explotacion, datos.documento_id)
    obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)

    obligacion = db.scalar(
        select(models.ObligacionDeMaquina).where(
            models.ObligacionDeMaquina.explotacion_id == explotacion.id,
            models.ObligacionDeMaquina.maquina_id == maquina_id,
            models.ObligacionDeMaquina.tipo == obligacion_tipo,
        )
    )
    if obligacion is None:
        obligacion = models.ObligacionDeMaquina(
            explotacion_id=explotacion.id,
            maquina_id=maquina_id,
            tipo=obligacion_tipo,
            aplicabilidad=aplicabilidad,
            origen=origen,
            documento_id=datos.documento_id,
            fecha_de_la_evidencia=datos.fecha_de_la_evidencia,
            # **Quién lo declara lo pone el servidor, y la fecha la manda el cliente** (CRM-07 #6,
            # 14/10/2026). El autor es **quien está usando el programa**, y eso lo sabe `usuario`;
            # preguntárselo al navegador sería dejar que el agricultor dijera que decidió otro. La
            # fecha sí viene en la petición: **solo él sabe cuándo lo decidió**. Y **cada declaración
            # es una decisión nueva de quien la hace**, así que el autor se reescribe siempre, tanto
            # al dar de alta como al corregir.
            decidido_por_usuario_id=usuario.id,
            decidido_en=datos.decidido_en,
            notas=datos.notas,
        )
        db.add(obligacion)
        db.flush()
        # **El alta TAMBIEN deja rastro** (CRM-07 #6, 14/10/2026). Esta rama volvia sin pasar por
        # `correcciones.corregir`, asi que **declarar una obligacion por primera vez no escribia ni una
        # linea de auditoria** —y el contrato pide justo eso: poder leer **por que se sabe que le toca y
        # de cuando es**. Lo encontro el recorrido, no las pruebas: las de modelo miraban la fila, y la
        # fila estaba bien. Es el mismo hueco que tenia el alta de una semilla.
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                usuario_id=usuario.id,
                entidad="obligacion_de_maquina",
                entidad_id=obligacion.id,
                accion="crear",
                datos={
                    "aplicabilidad": obligacion.aplicabilidad,
                    "origen_de_la_aplicabilidad": obligacion.origen,
                    "documento_id": obligacion.documento_id,
                    # **Las fechas van como texto, y no es un detalle de estilo**: `datos` es una
                    # columna JSON y **una `date` no se puede escribir tal cual** —revienta al guardar
                    # y la declaración entera se pierde con un 500—. En las correcciones lo resuelve
                    # `correcciones._como_se_guarda`; aquí, que el diccionario se escribe a mano, se
                    # deja escrito al escribirlo, como en la auditoría de ventas y de gastos.
                    "fecha_de_la_evidencia": (
                        obligacion.fecha_de_la_evidencia.isoformat()
                        if obligacion.fecha_de_la_evidencia
                        else None
                    ),
                    # **Y quién lo decidió y cuándo, también en el rastro del alta** (CRM-07 #6): el
                    # contrato pide poder leer **quién afirmó qué y el día que lo dijo**, y el alta de
                    # una obligación es justo donde se afirma por primera vez.
                    "decidido_por_usuario_id": obligacion.decidido_por_usuario_id,
                    "decidido_en": (
                        obligacion.decidido_en.isoformat() if obligacion.decidido_en else None
                    ),
                    "notas": obligacion.notas,
                },
            )
        )
        db.commit()
        return obligacion

    # **El papel y su fecha van con la regla A1** («lo que la petición no manda, no se borra», y su
    # gemela: lo que ya estaba, si no se manda, se queda). `aplicabilidad`, `origen` y `notas` siguen
    # como estaban —este `PUT` es la declaración entera de la obligación, y ese es su contrato—, pero
    # **estos dos son nuevos** y una llamada antigua que no los conozca **no puede borrarlos por no
    # nombrarlos**: es exactamente el fallo que costó la ronda del #2 de semillas.
    preparada = models.ObligacionDeMaquina(
        explotacion_id=explotacion.id,
        maquina_id=maquina_id,
        tipo=obligacion_tipo,
        aplicabilidad=aplicabilidad,
        origen=origen,
        documento_id=(
            datos.documento_id
            if "documento_id" in datos.model_fields_set
            else obligacion.documento_id
        ),
        fecha_de_la_evidencia=(
            datos.fecha_de_la_evidencia
            if "fecha_de_la_evidencia" in datos.model_fields_set
            else obligacion.fecha_de_la_evidencia
        ),
        # **Cada declaración es una decisión nueva de quien la hace** (CRM-07 #6, 14/10/2026): el
        # autor se reescribe **siempre**, aunque la petición no lo nombre, porque el autor no lo pone
        # el cliente sino el servidor. Y la fecha va con la **regla A1** de la casa («lo que la
        # petición no manda, no se borra»), igual que el papel y su fecha de aquí arriba.
        decidido_por_usuario_id=usuario.id,
        decidido_en=(
            datos.decidido_en
            if "decidido_en" in datos.model_fields_set
            else obligacion.decidido_en
        ),
        notas=datos.notas,
    )
    correcciones.corregir(
        db,
        guardado=obligacion,
        preparado=preparada,
        entidad="obligacion_de_maquina",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return obligacion


# --------------------------------------------------------------------------
# Las inspecciones
# --------------------------------------------------------------------------


def _la_inspeccion_de_esta_maquina(db: Db, explotacion, maquina_id: int, inspeccion_id: int):
    inspeccion = obtener_de_la_explotacion(
        db, models.InspeccionDeMaquina, inspeccion_id, explotacion.id
    )
    if inspeccion.maquina_id != maquina_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    return inspeccion


def _una_inspeccion_guardable(datos: InspeccionEntrada, explotacion, db: Db) -> dict:
    """Comprueba lo que llega y lo deja en valores, **sin inventar ni calcular ninguna fecha**."""
    tipo = _una_de_la_lista(
        datos.tipo, maquinaria.OBLIGACIONES, codigo="M17_eso_no_es_una_de_las_cinco_cosas"
    )
    resultado = _una_de_la_lista(
        datos.resultado,
        maquinaria.RESULTADOS_DE_UNA_INSPECCION,
        codigo="M13_eso_no_es_una_de_las_respuestas",
    )
    _el_papel_es_de_esta_finca(db, explotacion, datos.documento_id)
    return {
        "tipo": tipo,
        "fecha": datos.fecha,
        "resultado": resultado,
        # **Tal cual viene.** El esquema no la calcula y aquí tampoco: si el agricultor no la ha
        # copiado del papel, se queda vacía y la pantalla dice que no se sabe cuándo toca.
        "proxima_fecha": datos.proxima_fecha,
        "documento_id": datos.documento_id,
        "notas": datos.notas,
    }


@router.post(
    "/maquinaria/{maquina_id}/inspecciones",
    response_model=InspeccionSalida,
    status_code=status.HTTP_201_CREATED,
)
def apuntar_una_inspeccion(
    maquina_id: int,
    datos: InspeccionEntrada,
    explotacion: ExplotacionActual,
    db: Db,
) -> models.InspeccionDeMaquina:
    """Apunta una inspección, un mantenimiento o una renovación.

    Tres cosas que hace a propósito, y las tres son del contrato:

      · **Se puede apuntar sin papel.** `documento_id` es opcional y la respuesta dice `trae_papel`;
        el contrato pide que una inspección sin documento se apunte igual y que **se diga que no lo
        trae**. Hay máquinas cuyo certificado está en el taller o en el móvil del mecánico.
      · **El resultado puede quedar en «no lo pone el papel»**, que no es «favorable».
      · **Si el móvil reintenta, no se apunta dos veces**: `clave_de_reenvio` es el identificador de la
        petición, y repetirla devuelve lo que ya se apuntó en vez de crear otra (caso A12).
    """
    obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)
    datos_limpios = _una_inspeccion_guardable(datos, explotacion, db)

    clave = (datos.clave_de_reenvio or "").strip() or None
    if clave:
        # **La clave se cierra POR MÁQUINA, no solo por finca.** Faltaba el `maquina_id` y era un
        # defecto de verdad (lo encontró la revisión independiente del T14, 05/10/2026): la misma clave
        # para otra máquina —un guion que importe una lista, un cliente nuevo, una clave reutilizada—
        # contestaba **la inspección de la primera** y la segunda no se apuntaba. El agricultor cree que
        # la ha apuntado y no está. La clave la elige quien apunta, así que el programa no puede dar por
        # hecho que sea única entre máquinas.
        ya = db.scalar(
            select(models.InspeccionDeMaquina).where(
                models.InspeccionDeMaquina.explotacion_id == explotacion.id,
                models.InspeccionDeMaquina.maquina_id == maquina_id,
                models.InspeccionDeMaquina.clave_de_reenvio == clave,
            )
        )
        if ya is not None:
            return ya

    inspeccion = models.InspeccionDeMaquina(
        explotacion_id=explotacion.id,
        maquina_id=maquina_id,
        clave_de_reenvio=clave,
        **datos_limpios,
    )
    db.add(inspeccion)
    db.flush()
    # **Y la ITEAF llega al cuaderno**: la hoja 1.3 del cuaderno de la Junta se compone del equipo, con su
    # última fecha de inspección y la de la próxima. Si el agricultor las apunta donde el programa le dice
    # —aquí—, el papel que se entrega tiene que llevarlas (ver `_llevar_al_cuaderno`).
    _llevar_al_cuaderno(db, explotacion, _la_maquina_de(db, explotacion, maquina_id))
    db.commit()
    return inspeccion


@router.put(
    "/maquinaria/{maquina_id}/inspecciones/{inspeccion_id}", response_model=InspeccionSalida
)
def corregir_una_inspeccion(
    maquina_id: int,
    inspeccion_id: int,
    datos: InspeccionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.InspeccionDeMaquina:
    """Corrige una inspección: la fecha mal copiada, el resultado o la fecha de la próxima.

    Se corrige **en la misma fila** y queda en la auditoría, por el mismo motivo que en todo el
    programa: lo que había antes tiene que poder saberse.
    """
    inspeccion = _la_inspeccion_de_esta_maquina(db, explotacion, maquina_id, inspeccion_id)
    datos_limpios = _una_inspeccion_guardable(datos, explotacion, db)
    preparada = models.InspeccionDeMaquina(
        explotacion_id=explotacion.id,
        maquina_id=maquina_id,
        clave_de_reenvio=inspeccion.clave_de_reenvio,
        **datos_limpios,
    )
    correcciones.corregir(
        db,
        guardado=inspeccion,
        preparado=preparada,
        entidad="inspeccion_de_maquina",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    # Y la corrección llega al cuaderno (su hoja 1.3 lleva estas fechas).
    _llevar_al_cuaderno(db, explotacion, _la_maquina_de(db, explotacion, maquina_id))
    db.commit()
    return inspeccion


@router.post(
    "/maquinaria/{maquina_id}/inspecciones/{inspeccion_id}/anular",
    response_model=InspeccionSalida,
)
def anular_una_inspeccion(
    maquina_id: int,
    inspeccion_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.InspeccionDeMaquina:
    """Anula una inspección con su motivo: **se queda en el cuaderno, tachada, y deja de contar**.

    Es lo que hace falta cuando la inspección que se apuntó no era de esta máquina o estaba ya
    repetida: la fila se queda (nada se borra sin rastro) pero **no cuenta ni para la última inspección
    ni para la próxima fecha**, así que la ficha deja de enseñarla como si fuera la buena.
    """
    inspeccion = _la_inspeccion_de_esta_maquina(db, explotacion, maquina_id, inspeccion_id)
    inspeccion.anulado = True
    inspeccion.motivo_anulacion = datos.motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="inspeccion_de_maquina",
            entidad_id=inspeccion.id,
            accion="anular",
            datos={"motivo": datos.motivo},
        )
    )
    # Y el cuaderno se pone al día: lo anulado **deja de contar** para la última inspección, así que la
    # hoja 1.3 tampoco puede seguir llevándolo.
    _llevar_al_cuaderno(db, explotacion, _la_maquina_de(db, explotacion, maquina_id))
    db.commit()
    return inspeccion


@router.delete("/maquinaria/{maquina_id}/inspecciones/{inspeccion_id}")
def borrar_una_inspeccion(
    maquina_id: int,
    inspeccion_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Borra una inspección apuntada por error, dejando escrito lo que había en la auditoría.

    Es la otra mitad de «corregir, anular y reenviar»: un apunte que no llegó a pasar se quita, y el
    programa sigue sabiendo que estuvo (lo cuenta `app/correcciones.py`).
    """
    inspeccion = _la_inspeccion_de_esta_maquina(db, explotacion, maquina_id, inspeccion_id)
    correcciones.borrar(
        db,
        registro=inspeccion,
        entidad="inspeccion_de_maquina",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    # Y el cuaderno se pone al día con lo que queda: si la inspección borrada era la última ITEAF que
    # había, la hoja 1.3 **no** se queda con una fecha que ya no está apuntada en ningún sitio. Se
    # recalcula desde las que quedan; si no queda ninguna, `_llevar_al_cuaderno` no toca las fechas (no
    # las vacía: lo que el agricultor escribió en la hoja 1.3 no lo borra esta pantalla por su cuenta).
    _llevar_al_cuaderno(db, explotacion, _la_maquina_de(db, explotacion, maquina_id))
    db.commit()
    return {"borrado": True, "id": inspeccion_id}


# --------------------------------------------------------------------------
# Las averías
# --------------------------------------------------------------------------


def _la_averia_de_esta_maquina(db: Db, explotacion, maquina_id: int, averia_id: int):
    averia = obtener_de_la_explotacion(db, models.AveriaDeMaquina, averia_id, explotacion.id)
    if averia.maquina_id != maquina_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    return averia


@router.post(
    "/maquinaria/{maquina_id}/averias", response_model=AveriaSalida, status_code=status.HTTP_201_CREATED
)
def apuntar_una_averia(
    maquina_id: int, datos: AveriaEntrada, explotacion: ExplotacionActual, db: Db
) -> models.AveriaDeMaquina:
    """Apunta una avería: qué pasó, cuándo y si ya está arreglada.

    **`resuelta` no tiene valor por defecto**: el esquema la exige y admite también «no lo sé». Dar por
    arreglada una máquina que no lo está (o al revés) es de las cosas que este ticket no puede hacer, y
    por eso no se puede guardar sin contestar.

    La avería **no cambia sola la disponibilidad de la máquina**: son dos datos distintos, y el que
    sabe si se puede contar con ella es el agricultor. La pantalla los enseña juntos, sin mezclarlos.
    """
    obtener_de_la_explotacion(db, models.Maquina, maquina_id, explotacion.id)
    clave = (datos.clave_de_reenvio or "").strip() or None
    if clave:
        # Por máquina, por el mismo motivo que en una inspección: ver `apuntar_una_inspeccion`.
        ya = db.scalar(
            select(models.AveriaDeMaquina).where(
                models.AveriaDeMaquina.explotacion_id == explotacion.id,
                models.AveriaDeMaquina.maquina_id == maquina_id,
                models.AveriaDeMaquina.clave_de_reenvio == clave,
            )
        )
        if ya is not None:
            return ya
    averia = models.AveriaDeMaquina(
        explotacion_id=explotacion.id,
        maquina_id=maquina_id,
        fecha=datos.fecha,
        que_paso=datos.que_paso,
        resuelta=datos.resuelta,
        fecha_resuelta=datos.fecha_resuelta,
        horas=datos.horas,
        notas=datos.notas,
        clave_de_reenvio=clave,
    )
    db.add(averia)
    db.commit()
    return averia


@router.put("/maquinaria/{maquina_id}/averias/{averia_id}", response_model=AveriaSalida)
def corregir_una_averia(
    maquina_id: int,
    averia_id: int,
    datos: AveriaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.AveriaDeMaquina:
    """Corrige una avería: lo normal es volver para decir que **ya está arreglada**."""
    averia = _la_averia_de_esta_maquina(db, explotacion, maquina_id, averia_id)
    preparada = models.AveriaDeMaquina(
        explotacion_id=explotacion.id,
        maquina_id=maquina_id,
        fecha=datos.fecha,
        que_paso=datos.que_paso,
        resuelta=datos.resuelta,
        fecha_resuelta=datos.fecha_resuelta,
        horas=datos.horas,
        notas=datos.notas,
        clave_de_reenvio=averia.clave_de_reenvio,
    )
    correcciones.corregir(
        db,
        guardado=averia,
        preparado=preparada,
        entidad="averia_de_maquina",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return averia


@router.post("/maquinaria/{maquina_id}/averias/{averia_id}/anular", response_model=AveriaSalida)
def anular_una_averia(
    maquina_id: int,
    averia_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> models.AveriaDeMaquina:
    """Anula una avería con su motivo: se queda tachada y **deja de avisar**."""
    averia = _la_averia_de_esta_maquina(db, explotacion, maquina_id, averia_id)
    averia.anulado = True
    averia.motivo_anulacion = datos.motivo
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="averia_de_maquina",
            entidad_id=averia.id,
            accion="anular",
            datos={"motivo": datos.motivo},
        )
    )
    db.commit()
    return averia


@router.delete("/maquinaria/{maquina_id}/averias/{averia_id}")
def borrar_una_averia(
    maquina_id: int,
    averia_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Borra una avería apuntada por error, dejando el rastro en la auditoría."""
    averia = _la_averia_de_esta_maquina(db, explotacion, maquina_id, averia_id)
    correcciones.borrar(
        db,
        registro=averia,
        entidad="averia_de_maquina",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"borrado": True, "id": averia_id}
