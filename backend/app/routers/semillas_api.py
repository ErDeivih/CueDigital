"""Las semillas, las fotos de etiqueta y las siembras (T10, 03/10/2026).

## Qué añade esto a lo que ya había

El almacén (T09) ya sabe lo que entra, en qué lote y lo que sale. Lo que no sabía es **qué es una
semilla**: un insumo que se compra como cualquier otro, pero del que hay que apuntar lo que pone la
etiqueta —especie, variedad, casa, dosis recomendada, poder germinativo, pureza y si viene tratada—
y que después **se siembra en una tierra concreta**, con una dosis por hectárea y una cantidad total.

Este router añade tres cosas:

  1. **La semilla** (`POST /api/semillas`): un artículo del almacén con los datos de su etiqueta. **No
     hay un segundo almacén**: la semilla cuelga de un `articulo` y todo lo que entra y sale de ella
     pasa por las mismas puertas que lo demás (`articulos`, `lotes`, `recepciones`, `movimientos`).
  2. **La lectura de la etiqueta** (`POST /api/semillas/etiqueta`): se sube la foto, se lee lo que se
     puede y **se enseña para que el agricultor lo confirme**. Esta puerta **no guarda nada** —ni la
     semilla, ni el artículo, ni el fichero—, y eso no es un detalle: es lo que hace que una foto no
     pueda crear un dato por su cuenta. Lo que no se ha leído se queda **vacío**, y si no hay lector
     de letras instalado se dice.
  3. **La siembra** (`POST /api/siembras`): «en esta tierra sembré esta semilla». Y la semilla que se
     siembra **sale del almacén por la puerta que ya existe** (`POST /api/almacen/salidas`), con
     `apunte_tipo="siembra"`: no hay una segunda forma de descontar producto, así que el libro del
     almacén sigue cuadrando y una anulación devuelve lo que salió sin tocar el libro.

## Las tres reglas que este fichero cumple y no se pueden doblar

  · **La cantidad total no es la dosis por hectárea.** Van en columnas distintas, con su unidad cada
    una, y cuando una se calcula a partir de la otra **se dice** (`cantidad_total_calculada`,
    `dosis_calculada` y su aviso). Si no se puede calcular, se queda vacía y se pide.
  · **Un dato que no se sabe no es un cero.** Ni la dosis, ni el total, ni el poder germinativo, ni la
    pureza, ni si viene tratada (que tiene tres respuestas). Y una semilla sin cantidad conocida **no
    descuenta nada del almacén**, con su motivo escrito: restar «lo que sea» sería peor que no restar.
  · **Nada ocurre dos veces.** Reenviar la misma petición (la cola del móvil, un botón pulsado dos
    veces) devuelve la siembra que ya había **sin volver a descontar**, y corregir una siembra que ya
    había descontado anula la salida vieja y apunta la nueva: nunca quedan dos descuentos.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import (
    adjuntos,
    correcciones,
    models,
    ocr,
    semillas as logica,
    servicios,
    textos,
)
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    AnulacionEntrada,
    EtiquetaLeidaSalida,
    SalidaDeAlmacenEntrada,
    SemillaEntrada,
    SemillaSalida,
    SiembraEntrada,
    SiembraSalida,
)
# **La puerta de las salidas, importada tal cual.** Es la mitad de este ticket: la semilla que se
# siembra sale del almacén por donde sale todo lo demás, no por un camino nuevo. Llamarla aquí, en
# vez de copiar su lógica, es lo que garantiza que las dos formas de descontar no se separen nunca
# (las comprobaciones de reenvío, la unidad del lote, el aviso de que el envase se queda en negativo
# y la auditoría son las mismas).
from .almacen_api import sacar_de_un_lote

router = APIRouter(prefix="/api/semillas", tags=["semillas"])
# Las siembras van en su propio prefijo y en el mismo fichero porque son el mismo ticket y se miran
# juntas: una semilla sin siembra es una ficha, y una siembra sin semilla no existe.
router_siembras = APIRouter(prefix="/api/siembras", tags=["siembras"])

# Lo que se admite como foto de una etiqueta: lo mismo que un boletín de laboratorio (un PDF o la
# foto que hace el móvil). No se inventa otra lista: `adjuntos.py` es el único sitio donde se decide
# qué ficheros se aceptan y cómo se guardan.
TIPOS_DE_ETIQUETA = adjuntos.TIPOS_BOLETIN


# --------------------------------------------------------------------------
# La semilla: el artículo del almacén con lo que dice su etiqueta
# --------------------------------------------------------------------------


def _la_semilla(
    db, semilla: models.Semilla, *, con_siembras: bool = True
) -> dict:
    """La semilla con su nombre de artículo, lo que queda y sus envases, todo contado aquí.

    **Ni una cuenta en la pantalla.** Lo que queda sale de `servicios.existencias_del_almacen`, que es
    quien sabe decirlo: `saldo` con su unidad cuando se puede saber y, cuando no, `saldo: None` con el
    motivo. Un almacén del que no se sabe lo que queda nunca se convierte en un cero.
    """
    articulo = db.get(models.Articulo, semilla.articulo_id)
    nombre = articulo.nombre if articulo else ""
    unidad = articulo.unidad if articulo else None

    existencias = servicios.existencias_del_almacen(
        db, explotacion_id=semilla.explotacion_id, articulo_id=semilla.articulo_id
    )
    envases: list[dict] = []
    queda: dict | None = None
    if existencias:
        fila = existencias[0]
        # **Una semilla que no ha entrado nunca en el almacén no dice «queda 0».** El almacén sabe
        # contar un envase vacío (cero es un cero), pero un artículo **sin ningún envase y sin ningún
        # movimiento** no tiene nada que contar: el programa no sabe cuánta semilla hay en la nave
        # —puede estar el saco entero y sin albarán—, así que dice que no se puede saber y por qué.
        # Esto salió de la revisión: el camino normal del ticket (comprar, hacer la foto, confirmar)
        # acababa enseñando «Te queda 0» con el saco en la nave.
        sin_nada_apuntado = fila.get("sin_movimientos") and not fila.get("cuantos_lotes")
        if sin_nada_apuntado:
            queda = {
                "saldo": None,
                "unidad": fila.get("unidad") or (unidad or None),
                "motivo": textos.MENSAJES["SM35_no_ha_entrado_para_saber_lo_que_queda"],
                "motivo_codigo": "SM35_no_ha_entrado_para_saber_lo_que_queda",
                "cuantos_lotes": 0,
                "entradas": None,
                "salidas": None,
            }
        else:
            queda = {
                "saldo": fila.get("saldo"),
                "unidad": fila.get("unidad") or (unidad or None),
                "motivo": fila.get("motivo") or "",
                "motivo_codigo": fila.get("motivo_codigo") or "",
                "cuantos_lotes": fila.get("cuantos_lotes", 0),
                "entradas": fila.get("entradas"),
                "salidas": fila.get("salidas"),
            }
        for de_lote in fila.get("lotes", []):
            envases.append(
                {
                    "lote_id": de_lote["lote_id"],
                    "numero_lote": de_lote["numero_lote"],
                    "fecha_caducidad": de_lote["fecha_caducidad"],
                    "caducado": de_lote["caducado"],
                    "presentacion": de_lote["presentacion"],
                    "saldo": de_lote.get("saldo"),
                    "unidad": de_lote.get("unidad") or (unidad or None),
                    "motivo": de_lote.get("motivo") or "",
                }
            )

    cuantas_siembras = 0
    if con_siembras:
        cuantas_siembras = sum(
            1
            for siembra in db.scalars(
                select(models.Siembra).where(
                    models.Siembra.explotacion_id == semilla.explotacion_id,
                    models.Siembra.semilla_id == semilla.id,
                )
            )
            if not siembra.anulada
        )

    return {
        "id": semilla.id,
        "articulo_id": semilla.articulo_id,
        "nombre": nombre,
        "unidad": unidad,
        "categoria": articulo.categoria if articulo else "semilla",
        "especie": semilla.especie,
        "variedad": semilla.variedad,
        "casa_comercial": semilla.casa_comercial,
        "proveedor": semilla.proveedor,
        "numero_lote_proveedor": semilla.numero_lote_proveedor,
        "dosis_recomendada_por_ha": semilla.dosis_recomendada_por_ha,
        "unidad_dosis": semilla.unidad_dosis,
        "fecha_envasado": semilla.fecha_envasado,
        "fecha_caducidad": semilla.fecha_caducidad,
        "poder_germinativo_pct": semilla.poder_germinativo_pct,
        "pureza_pct": semilla.pureza_pct,
        "tratada": semilla.tratada,
        "leida_de": semilla.leida_de,
        "idioma_del_lector": semilla.idioma_del_lector,
        "tiene_foto": bool(semilla.etiqueta_ruta),
        "creada_en": semilla.creada_en,
        "queda": queda,
        "envases": envases,
        "siembras": cuantas_siembras,
    }


def _los_campos_de_la_etiqueta(datos: SemillaEntrada, semilla: models.Semilla) -> None:
    """Pasa al modelo lo que ha confirmado el agricultor, dejando vacío lo que no venga.

    Dos cuidados que están dichos porque alguien los va a querer «arreglar»:

      1. **Un campo que no viene se queda en `None`**, no en cero ni en cadena vacía: `None` es «no lo
         sé» y es lo que hace que la pantalla pueda decir «La etiqueta no lo dice».
      2. **El nombre del artículo y la unidad se recortan**, porque son los que se ven en la lista del
         almacén y un nombre con espacios de sobra descuadra la comparación con otras listas.
    """
    semilla.especie = _texto_o_nada(datos.especie, 120)
    semilla.variedad = _texto_o_nada(datos.variedad, 120)
    semilla.casa_comercial = _texto_o_nada(datos.casa_comercial, 120)
    semilla.proveedor = _texto_o_nada(datos.proveedor, 200)
    semilla.numero_lote_proveedor = _texto_o_nada(datos.numero_lote_proveedor, 80)
    semilla.dosis_recomendada_por_ha = datos.dosis_recomendada_por_ha
    semilla.unidad_dosis = _texto_o_nada(datos.unidad_dosis, 20)
    semilla.fecha_envasado = datos.fecha_envasado
    semilla.fecha_caducidad = datos.fecha_caducidad
    semilla.poder_germinativo_pct = datos.poder_germinativo_pct
    semilla.pureza_pct = datos.pureza_pct
    semilla.tratada = datos.tratada


def _texto_o_nada(valor: str | None, largo: int) -> str | None:
    limpio = (valor or "").strip()
    return limpio[:largo] or None


def _la_dosis_necesita_unidad(datos: SemillaEntrada) -> None:
    """Una dosis sin unidad no dice nada: se dice, en vez de apuntar un número suelto."""
    if datos.dosis_recomendada_por_ha is not None and not (datos.unidad_dosis or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("SM14_falta_la_unidad_de_la_dosis"),
        )


@router.post("", response_model=SemillaSalida, status_code=status.HTTP_201_CREATED)
def dar_de_alta_una_semilla(
    datos: SemillaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Dar de alta una semilla: **el artículo del almacén y su etiqueta, de una vez**.

    Esta es la puerta que confirma. Lo que llega aquí es lo que el agricultor ha visto y ha dicho que
    sí (o lo que ha escrito él a mano), y por eso el artículo y la semilla se crean juntos: una
    semilla sin artículo no se podría comprar ni sacar del almacén, y un artículo «semilla» sin
    etiqueta no diría qué se está sembrando.

    **El artículo se crea con la categoría `semilla`**, y ahí está la mitad de la decisión de este
    ticket: la semilla es un insumo del almacén como cualquier otro (aparece en el libro, entra por
    albarán, sale por una salida), y lo único que añade esta tabla es lo que pone el papel.
    """
    _la_dosis_necesita_unidad(datos)
    nombre = (datos.nombre or "").strip()[:200]
    if datos.articulo_id is None and not nombre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=textos.mensaje("SM13_falta_el_nombre")
        )

    if datos.articulo_id is not None:
        # La semilla ya está en el almacén (llegó por albarán, o estaba en la nave). Se le cuelga la
        # etiqueta a **su** artículo: dar de alta otro con el mismo nombre partiría en dos las
        # existencias de la misma semilla, que es el fallo que este camino existe para impedir.
        articulo = obtener_de_la_explotacion(
            db, models.Articulo, datos.articulo_id, explotacion.id
        )
        ya_tiene = db.scalar(
            select(models.Semilla).where(
                models.Semilla.explotacion_id == explotacion.id,
                models.Semilla.articulo_id == articulo.id,
            )
        )
        if ya_tiene is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=textos.mensaje("SM33_esa_semilla_ya_tiene_su_etiqueta"),
            )
        cambios_del_articulo = {}
        if nombre and articulo.nombre != nombre:
            cambios_del_articulo["nombre"] = [articulo.nombre, nombre]
            articulo.nombre = nombre
        if articulo.categoria != "semilla":
            # Decir «esto es una semilla» es lo que hace esta puerta: el artículo pasa a la pestaña de
            # las semillas del almacén, que es donde el agricultor lo va a buscar. Y queda apuntado.
            cambios_del_articulo["categoria"] = [articulo.categoria, "semilla"]
            articulo.categoria = "semilla"
        if (articulo.unidad or None) != _texto_o_nada(datos.unidad, 10) and datos.unidad:
            cambios_del_articulo["unidad"] = [articulo.unidad, _texto_o_nada(datos.unidad, 10)]
            articulo.unidad = _texto_o_nada(datos.unidad, 10)
    else:
        articulo = models.Articulo(
            explotacion_id=explotacion.id,
            nombre=nombre,
            categoria="semilla",
            unidad=_texto_o_nada(datos.unidad, 10),
        )
        db.add(articulo)
        db.flush()
        cambios_del_articulo = {}
    if cambios_del_articulo:
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                usuario_id=usuario.id,
                entidad="articulo",
                entidad_id=articulo.id,
                accion="corregir",
                datos=cambios_del_articulo,
            )
        )

    semilla = models.Semilla(
        explotacion_id=explotacion.id,
        articulo_id=articulo.id,
        # De dónde salieron los datos: si no lo dice quien llama, los ha escrito una persona.
        leida_de=(
            datos.leida_de
            if datos.leida_de in logica.CAMINOS_DE_LECTURA
            else "mano"
        ),
        idioma_del_lector=_texto_o_nada(datos.idioma_del_lector, 20),
    )
    _los_campos_de_la_etiqueta(datos, semilla)
    db.add(semilla)
    db.flush()
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="semilla",
            entidad_id=semilla.id,
            accion="crear",
            datos={
                "nombre": articulo.nombre,
                "especie": semilla.especie,
                "variedad": semilla.variedad,
                "leida_de": semilla.leida_de,
            },
        )
    )
    db.commit()
    db.refresh(semilla)
    return _la_semilla(db, semilla)


@router.get("", response_model=list[SemillaSalida])
def listar_las_semillas(explotacion: ExplotacionActual, db: Db) -> list[dict]:
    """Las semillas de la finca, cada una con lo que queda y con sus envases.

    Se ordenan por el nombre del artículo, que es como las reconoce el agricultor en la nave, y **lo
    que queda lo cuenta el servidor** (nunca la pantalla): es la única forma de que la lista y el
    libro del almacén no puedan decir cosas distintas.
    """
    return [
        _la_semilla(db, semilla)
        for semilla in db.scalars(
            select(models.Semilla)
            .join(models.Articulo, models.Articulo.id == models.Semilla.articulo_id)
            .where(models.Semilla.explotacion_id == explotacion.id)
            .order_by(models.Articulo.nombre)
        )
    ]


@router.post("/etiqueta", response_model=EtiquetaLeidaSalida)
async def leer_la_etiqueta(
    explotacion: ExplotacionActual, db: Db, fichero: UploadFile = File(...)
) -> EtiquetaLeidaSalida:
    """Mira la foto de una etiqueta y cuenta lo que ha entendido. **No guarda absolutamente nada.**

    Ni la semilla, ni el artículo, ni el fichero: se lee, se devuelve la propuesta y ahí se acaba. Es
    la regla del proyecto para todo lo que lee un programa —el dictado, una factura y ahora una
    etiqueta—: **lo que se lee es una propuesta, y un hecho solo cuando el agricultor dice que sí**.
    Por eso la respuesta lleva `guardado: false` escrito en el dato y no en un comentario.

    Lo que se devuelve, y por qué cada cosa:

      · **los campos que se han leído**, cada uno con su nombre;
      · **`campos_leidos`**, que es la lista de los que de verdad se han podido sacar (la pantalla la
        usa para decir «he leído 6 datos» en vez de callarse);
      · **`como_se_leyo`** y **`idioma_del_lector`**: con qué se ha leído, que es lo que permite
        entender una errata («las palabras con eñe pueden salir cambiadas»);
      · **`dudas`**: lo que el papel sí dice y no se puede apuntar tal cual (una caducidad de mes y
        año, una dosis sin decir si es por hectárea). Es distinto de un hueco: aquí hay un dato.
    """
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS_DE_ETIQUETA)
    leida = logica.leer_etiqueta(contenido)
    return EtiquetaLeidaSalida(
        nombre="",
        especie=leida.especie,
        variedad=leida.variedad,
        casa_comercial=leida.casa_comercial,
        proveedor=leida.proveedor,
        numero_lote_proveedor=leida.numero_lote_proveedor,
        dosis_recomendada_por_ha=leida.dosis_recomendada_por_ha,
        unidad_dosis=leida.unidad_dosis,
        fecha_envasado=leida.fecha_envasado,
        fecha_caducidad=leida.fecha_caducidad,
        poder_germinativo_pct=leida.poder_germinativo_pct,
        pureza_pct=leida.pureza_pct,
        tratada=leida.tratada,
        campos_leidos=leida.leidos,
        como_se_leyo=leida.como_se_leyo,
        idioma_del_lector=leida.idioma_del_lector,
        hay_lector=ocr.hay_lector(),
        texto_crudo=leida.texto_crudo[:4000],
        avisos=leida.avisos,
        dudas=leida.dudas,
        guardado=False,
    )


@router.get("/{semilla_id}", response_model=SemillaSalida)
def ver_una_semilla(
    semilla_id: int, explotacion: ExplotacionActual, db: Db
) -> dict:
    semilla = obtener_de_la_explotacion(db, models.Semilla, semilla_id, explotacion.id)
    return _la_semilla(db, semilla)


@router.put("/{semilla_id}", response_model=SemillaSalida)
def corregir_una_semilla(
    semilla_id: int,
    datos: SemillaEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Corregir lo que pone la etiqueta.

    **Existe porque una etiqueta se teclea y se teclea mal.** El poder germinativo y la pureza los
    lee una persona del papel —o los propone un lector de fotos y se confirman—, y un número mal
    copiado en la ficha se queda ahí para siempre si no hay dónde arreglarlo. Es la misma lección que
    el proyecto ya tiene escrita: **un dato con puerta de entrada y sin puerta de corrección acaba
    siendo un dato falso**.

    Corregir no borra nada: la fila sigue siendo la misma y en la auditoría queda **qué decía antes y
    qué dice ahora**, campo por campo (`correcciones.corregir`). Lo que **no** se toca aquí es lo que
    ya pasó: las siembras y los movimientos del almacén son hechos y siguen como estaban.
    """
    _la_dosis_necesita_unidad(datos)
    semilla = obtener_de_la_explotacion(db, models.Semilla, semilla_id, explotacion.id)
    articulo = db.get(models.Articulo, semilla.articulo_id)
    # **Lo que la petición no manda, se queda como estaba** (la misma regla que en la siembra y que el
    # proyecto ya tiene escrita: «al corregir, lo que el formulario no pregunta tiene que viajar
    # igual»). Aquí se veía claro con el nombre —corregir el poder germinativo no puede borrar cómo se
    # llama la semilla— y vale igual para la variedad, la casa y todo lo demás: quien no manda la
    # variedad no está diciendo que no tenga, está diciendo que de eso no habla.
    enviados = datos.model_fields_set
    nombre = (datos.nombre or "").strip()[:200] or (articulo.nombre if articulo else "")
    if not nombre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=textos.mensaje("SM13_falta_el_nombre")
        )
    lo_que_hay = {
        "especie": datos.especie if "especie" in enviados else semilla.especie,
        "variedad": datos.variedad if "variedad" in enviados else semilla.variedad,
        "casa_comercial": (
            datos.casa_comercial if "casa_comercial" in enviados else semilla.casa_comercial
        ),
        "proveedor": datos.proveedor if "proveedor" in enviados else semilla.proveedor,
        "numero_lote_proveedor": (
            datos.numero_lote_proveedor
            if "numero_lote_proveedor" in enviados
            else semilla.numero_lote_proveedor
        ),
        "dosis_recomendada_por_ha": (
            datos.dosis_recomendada_por_ha
            if "dosis_recomendada_por_ha" in enviados
            else semilla.dosis_recomendada_por_ha
        ),
        "unidad_dosis": datos.unidad_dosis if "unidad_dosis" in enviados else semilla.unidad_dosis,
        "fecha_envasado": (
            datos.fecha_envasado if "fecha_envasado" in enviados else semilla.fecha_envasado
        ),
        "fecha_caducidad": (
            datos.fecha_caducidad if "fecha_caducidad" in enviados else semilla.fecha_caducidad
        ),
        "poder_germinativo_pct": (
            datos.poder_germinativo_pct
            if "poder_germinativo_pct" in enviados
            else semilla.poder_germinativo_pct
        ),
        "pureza_pct": datos.pureza_pct if "pureza_pct" in enviados else semilla.pureza_pct,
        "tratada": datos.tratada if "tratada" in enviados else semilla.tratada,
    }

    preparada = models.Semilla(
        explotacion_id=explotacion.id,
        articulo_id=semilla.articulo_id,
        leida_de=(
            datos.leida_de if datos.leida_de in logica.CAMINOS_DE_LECTURA else semilla.leida_de
        ),
        idioma_del_lector=_texto_o_nada(datos.idioma_del_lector, 20) or semilla.idioma_del_lector,
        **lo_que_hay,
    )
    # **`creada_en` se copia a mano, y no es un descuido.** `correcciones.corregir` copia todas las
    # columnas del registro preparado al guardado menos las de su lista de «no se toca», y esa lista
    # está escrita en masculino (`creado_en`, `anulado`): en esta tabla la columna es `creada_en`, así
    # que si no se copiara aquí, la corrección la pondría a nulo y la base la rechazaría (NOT NULL).
    # Se copia **el mismo valor**, así que no cuenta como cambio y no ensucia la auditoría.
    preparada.creada_en = semilla.creada_en
    # La foto no se toca al corregir la etiqueta: tiene su propia puerta (subirla) y borrarla sin
    # querer sería perder el papel que sostiene todo esto.
    preparada.etiqueta_nombre = semilla.etiqueta_nombre
    preparada.etiqueta_ruta = semilla.etiqueta_ruta
    preparada.etiqueta_tipo = semilla.etiqueta_tipo
    preparada.etiqueta_bytes = semilla.etiqueta_bytes

    if articulo is not None and articulo.nombre != nombre:
        cambios_del_articulo = {"nombre": [articulo.nombre, nombre]}
        articulo.nombre = nombre
    else:
        cambios_del_articulo = {}
    if articulo is not None and (articulo.unidad or None) != _texto_o_nada(datos.unidad, 10):
        cambios_del_articulo["unidad"] = [articulo.unidad, _texto_o_nada(datos.unidad, 10)]
        articulo.unidad = _texto_o_nada(datos.unidad, 10)

    correcciones.corregir(
        db,
        guardado=semilla,
        preparado=preparada,
        entidad="semilla",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    if cambios_del_articulo:
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                usuario_id=usuario.id,
                entidad="articulo",
                entidad_id=articulo.id,
                accion="corregir",
                datos=cambios_del_articulo,
            )
        )
        db.commit()
    return _la_semilla(db, semilla)


@router.post("/{semilla_id}/etiqueta", response_model=SemillaSalida)
async def subir_la_foto_de_la_etiqueta(
    semilla_id: int,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    fichero: UploadFile = File(...),
) -> dict:
    """Guardar la foto de la etiqueta con la semilla.

    **El fichero va al disco y en la base de datos solo queda la referencia** (nombre, ruta relativa,
    tipo y tamaño): un móvil hace fotos de cuatro megas y meterlas en una columna haría que la copia
    de seguridad del agricultor dejase de poderse manejar. El nombre que manda el navegador **no se
    usa como ruta**: la pone el programa, con la carpeta de la finca y un identificador aleatorio
    (`app/adjuntos.py`).
    """
    semilla = obtener_de_la_explotacion(db, models.Semilla, semilla_id, explotacion.id)
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, TIPOS_DE_ETIQUETA)
    nombre, ruta, tipo, tamano = adjuntos.guardar_en_disco(
        explotacion_id=explotacion.id,
        prefijo="etiqueta-semilla",
        fichero=fichero,
        contenido=contenido,
        permitidos=TIPOS_DE_ETIQUETA,
    )
    anterior = semilla.etiqueta_ruta
    semilla.etiqueta_nombre = nombre
    semilla.etiqueta_ruta = ruta
    semilla.etiqueta_tipo = tipo
    semilla.etiqueta_bytes = tamano
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="semilla",
            entidad_id=semilla.id,
            accion="subir_etiqueta",
            datos={"fichero": nombre, "tipo": tipo, "bytes": tamano},
        )
    )
    db.commit()
    db.refresh(semilla)
    # El fichero viejo se borra **después** de guardar el nuevo: si se borrara antes y fallara el
    # guardado, el agricultor se quedaría sin el papel que acababa de subir.
    if anterior and anterior != ruta:
        adjuntos.borrar_del_disco(anterior)
    return _la_semilla(db, semilla)


@router.get("/{semilla_id}/etiqueta")
def ver_la_foto_de_la_etiqueta(
    semilla_id: int, explotacion: ExplotacionActual, db: Db
) -> FileResponse:
    """La foto de la etiqueta. La sirve el programa, y **solo si es de esta finca**."""
    semilla = obtener_de_la_explotacion(db, models.Semilla, semilla_id, explotacion.id)
    if not semilla.etiqueta_ruta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Esta semilla no tiene la foto de la etiqueta.",
        )
    return FileResponse(
        adjuntos.ruta_segura(semilla.etiqueta_ruta),
        media_type=semilla.etiqueta_tipo or "application/octet-stream",
        filename=semilla.etiqueta_nombre or "etiqueta",
    )


# --------------------------------------------------------------------------
# La siembra: «en esta tierra sembré esta semilla»
# --------------------------------------------------------------------------


def _la_salida_viva(db, siembra: models.Siembra) -> models.MovimientoDeExistencias | None:
    """La salida del almacén que sostiene esta siembra, si la hay.

    Se busca entre **las que cuentan**: si la salida está anulada, esta siembra no está descontando
    nada, y decirlo es la mitad de poder explicarle al agricultor por qué la semilla que queda no ha
    bajado.
    """
    return db.scalar(
        select(models.MovimientoDeExistencias).where(
            models.MovimientoDeExistencias.explotacion_id == siembra.explotacion_id,
            models.MovimientoDeExistencias.origen_tipo == "siembra",
            models.MovimientoDeExistencias.origen_id == siembra.id,
            models.MovimientoDeExistencias.anulado.is_(False),
        )
    )


def _la_siembra(db, siembra: models.Siembra, *, avisos: list[str] | None = None) -> dict:
    """La siembra con los nombres resueltos y **si ha descontado del almacén o no, y por qué**."""
    semilla = db.get(models.Semilla, siembra.semilla_id)
    articulo = db.get(models.Articulo, semilla.articulo_id) if semilla else None
    parcela = db.get(models.Parcela, siembra.parcela_id)
    lote = db.get(models.Lote, siembra.lote_id) if siembra.lote_id else None

    salida = _la_salida_viva(db, siembra) if not siembra.anulada else None
    if siembra.anulada:
        descuenta, porque = False, textos.MENSAJES["SM29_la_siembra_esta_anulada"]
    elif salida is not None:
        descuenta, porque = True, ""
    elif siembra.cantidad_total is None:
        descuenta, porque = False, textos.MENSAJES["SM16_no_se_puede_sacar_sin_cantidad"]
    else:
        descuenta, porque = False, textos.MENSAJES["SM17_no_se_puede_sacar_sin_envase"]

    return {
        "id": siembra.id,
        "semilla_id": siembra.semilla_id,
        "parcela_id": siembra.parcela_id,
        "lote_id": siembra.lote_id,
        "fecha": siembra.fecha,
        "superficie_ha": siembra.superficie_ha,
        "dosis_por_ha": siembra.dosis_por_ha,
        "unidad_dosis": siembra.unidad_dosis,
        "cantidad_total": siembra.cantidad_total,
        "unidad_cantidad": siembra.unidad_cantidad,
        "dosis_calculada": siembra.dosis_calculada,
        "cantidad_total_calculada": siembra.cantidad_total_calculada,
        "notas": siembra.notas,
        "anulada": siembra.anulada,
        "motivo_anulacion": siembra.motivo_anulacion,
        "creada_en": siembra.creada_en,
        "semilla": articulo.nombre if articulo else None,
        "tierra": parcela.alias if parcela else None,
        "numero_lote": lote.numero_lote if lote else None,
        "descuenta": descuenta,
        "no_descuenta_porque": porque,
        "movimiento_id": salida.id if salida else None,
        "avisos": avisos or [],
    }


def _las_cifras(datos: SiembraEntrada) -> dict:
    """Cuadra la dosis y la cantidad total con la superficie (ver `semillas.cuadra_las_dos_cifras`)."""
    return logica.cuadra_las_dos_cifras(
        dosis_por_ha=datos.dosis_por_ha,
        unidad_dosis=datos.unidad_dosis,
        cantidad_total=datos.cantidad_total,
        unidad_cantidad=datos.unidad_cantidad,
        superficie_ha=datos.superficie_ha,
    )


def _lo_que_se_corrige(datos: SiembraEntrada, siembra: models.Siembra) -> dict:
    """Lo que se va a escribir al corregir: **lo que manda la petición, y lo que ya constaba**.

    ESTO ES LA REGLA DEL PROYECTO, Y AQUÍ FALTABA. «Al corregir, lo que el formulario no pregunta
    tiene que viajar igual»: una petición que no manda la fecha **no está diciendo que no había
    fecha**, está diciendo que de eso no habla. Sin esta mezcla, corregir la cantidad desde fuera de
    la pantalla —o desde una pantalla futura que no pregunte el día— dejaba la siembra **sin fecha**,
    que es el día de la siembra que se enseña en una inspección. Lo cazó la revisión del T10.

    Se distingue «no lo manda» de «lo manda vacío» con `model_fields_set`: quien manda `fecha: null`
    está diciendo que la borre (y se borra); quien no manda `fecha` no dice nada (y se queda la que
    había). Es la única forma de que las dos cosas se puedan hacer.
    """
    enviados = datos.model_fields_set

    def suyo(campo: str, lo_que_habia):
        return getattr(datos, campo) if campo in enviados else lo_que_habia

    return {
        "semilla_id": suyo("semilla_id", siembra.semilla_id),
        "parcela_id": suyo("parcela_id", siembra.parcela_id),
        "lote_id": suyo("lote_id", siembra.lote_id),
        "fecha": suyo("fecha", siembra.fecha),
        "superficie_ha": suyo("superficie_ha", siembra.superficie_ha),
        "dosis_por_ha": suyo("dosis_por_ha", siembra.dosis_por_ha),
        "unidad_dosis": suyo("unidad_dosis", siembra.unidad_dosis),
        "cantidad_total": suyo("cantidad_total", siembra.cantidad_total),
        "unidad_cantidad": suyo("unidad_cantidad", siembra.unidad_cantidad),
        "notas": suyo("notas", siembra.notas),
    }


def _las_cifras_de(lo_que_hay: dict) -> dict:
    """La cuenta de la dosis y el total, con los valores que se van a escribir."""
    return logica.cuadra_las_dos_cifras(
        dosis_por_ha=lo_que_hay.get("dosis_por_ha"),
        unidad_dosis=lo_que_hay.get("unidad_dosis"),
        cantidad_total=lo_que_hay.get("cantidad_total"),
        unidad_cantidad=lo_que_hay.get("unidad_cantidad"),
        superficie_ha=lo_que_hay.get("superficie_ha"),
    )


def _la_clave(datos) -> str | None:
    return ((datos.clave_de_reenvio or datos.id_local or "") or "").strip()[:120] or None


def _el_lote_comprobado(
    db, lote_id: int | None, semilla: models.Semilla, explotacion
) -> models.Lote | None:
    """El envase del que sale la semilla, comprobando que es suyo.

    Dos comprobaciones y las dos importan: que el envase sea de esta finca (lo hace
    `obtener_de_la_explotacion`, que contesta **404 y no 403**) y que sea **de esta semilla**. Sin la
    segunda, un agricultor con dos semillas podría descontar la que no es, y el libro diría que salió
    de un saco que sigue lleno.
    """
    if lote_id is None:
        return None
    lote = obtener_de_la_explotacion(db, models.Lote, lote_id, explotacion.id)
    if lote.articulo_id != semilla.articulo_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("SM19_el_envase_no_es_de_esta_semilla"),
        )
    return lote


def _sacar_la_semilla_del_almacen(
    *,
    db,
    explotacion,
    usuario,
    siembra: models.Siembra,
    lote: models.Lote,
    cantidad: float,
    unidad: str,
    clave: str | None,
    aceptar_descuadre: bool,
):
    """Saca del almacén lo que se ha sembrado, **por la puerta de las salidas que ya existe**.

    Esta función no resta nada por su cuenta: llama a `almacen_api.sacar_de_un_lote`, que es el único
    sitio del programa que saca producto de un lote con un apunte detrás. Así la siembra hereda todo
    lo que esa puerta ya hace bien —el reenvío, el aviso de que el envase se queda en negativo, la
    unidad del lote, la auditoría— y no hay dos formas de descontar que un día digan cosas distintas.

    Si la puerta contesta que no (el envase se quedaría en negativo y el agricultor no lo ha
    confirmado), la excepción sube y **la siembra no se guarda**: la transacción entera se deshace, así
    que no puede quedar una siembra apuntada sin su salida ni una salida sin su siembra.
    """
    return sacar_de_un_lote(
        datos=_datos_de_la_salida(
            siembra=siembra,
            lote=lote,
            cantidad=cantidad,
            unidad=unidad,
            clave=clave,
            aceptar_descuadre=aceptar_descuadre,
        ),
        explotacion=explotacion,
        usuario=usuario,
        db=db,
        respuesta=Response(),
    )


def _datos_de_la_salida(
    *, siembra, lote, cantidad, unidad, clave, aceptar_descuadre
) -> SalidaDeAlmacenEntrada:
    """La petición con la que una siembra saca la semilla del almacén (por la puerta de las salidas).

    **Sin clave de reenvío propia, y esto lo cazó la revisión.** Aquí se ponía `«{clave}:salida»`, y
    eso hacía un daño que se ve en el libro: si el agricultor **anula** la siembra y la cola del móvil
    reenvía la misma petición (la misma clave, que es lo que hace la cola), la siembra nueva se creaba
    bien pero su salida **no**, porque la puerta encontraba por esa clave la salida VIEJA —que sigue
    viva: solo su siembra está anulada— y la daba por buena. La semilla no volvía a salir del almacén
    y la respuesta decía que no descontaba «porque no se sabe de qué envase sale», con el envase
    elegido.

    La protección de verdad no era esa clave: es la comprobación de la puerta por **apunte y envase**
    (una siembra nueva tiene su propio identificador, así que no choca con la salida de la anulada), y
    el reenvío de la misma petición lo corta antes el propio `POST /api/siembras`, que reconoce la
    siembra por su clave y devuelve la que ya había **sin volver a llamar aquí**.
    """
    return SalidaDeAlmacenEntrada(
        apunte_tipo="siembra",
        apunte_id=siembra.id,
        lote_id=lote.id,
        cantidad=cantidad,
        unidad=unidad,
        fecha=siembra.fecha,
        motivo=None,
        aceptar_descuadre=aceptar_descuadre,
        clave_de_reenvio=None,
    )


def _lo_que_hay_que_decir(sobre_el_descuento: list[str], cifras: dict) -> list[str]:
    avisos = list(cifras.get("avisos") or [])
    avisos.extend(sobre_el_descuento)
    return avisos


@router_siembras.post("", response_model=SiembraSalida, status_code=status.HTTP_201_CREATED)
def sembrar_una_semilla(
    datos: SiembraEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    respuesta: Response,
) -> dict:
    """Apuntar que en una tierra se sembró una semilla, **y sacarla del almacén de una vez**.

    LO QUE HACE, EN ORDEN, Y POR QUÉ EN ESE ORDEN:

      1. **Comprueba que la semilla y la tierra son de esta finca** (`404`, no `403`, como todo en este
         programa: no se filtra si un identificador existe en otra finca).
      2. **Mira si esta misma petición ya se atendió** (la clave de reenvío). Si sí, devuelve la
         siembra que ya había **sin volver a descontar**: es la cola del móvil, que reintenta al
         volver la cobertura, y un botón pulsado dos veces.
      3. **Cuadra las dos cifras** con la superficie: la que falte se calcula y se dice, y si no se
         puede calcular se queda vacía.
      4. **Saca del almacén** lo que se ha sembrado, por la puerta de las salidas, si se sabe cuánto y
         de qué envase. Si no se sabe alguna de las dos cosas, **no se resta nada** y se dice por qué
         con su frase: antes un hueco que un número inventado.
    """
    semilla = obtener_de_la_explotacion(db, models.Semilla, datos.semilla_id, explotacion.id)
    obtener_de_la_explotacion(db, models.Parcela, datos.parcela_id, explotacion.id)
    lote = _el_lote_comprobado(db, datos.lote_id, semilla, explotacion)

    clave = _la_clave(datos)
    if clave:
        ya = db.scalar(
            select(models.Siembra).where(
                models.Siembra.explotacion_id == explotacion.id,
                models.Siembra.clave_de_reenvio == clave,
                models.Siembra.anulada.is_(False),
            )
        )
        if ya is not None:
            respuesta.status_code = status.HTTP_200_OK
            return _la_siembra(
                db, ya, avisos=[textos.MENSAJES["SM20_la_siembra_ya_estaba"]]
            )

    cifras = _las_cifras(datos)
    siembra = models.Siembra(
        explotacion_id=explotacion.id,
        parcela_id=datos.parcela_id,
        semilla_id=semilla.id,
        lote_id=lote.id if lote else None,
        fecha=datos.fecha,
        superficie_ha=cifras["superficie_ha"],
        dosis_por_ha=cifras["dosis_por_ha"],
        unidad_dosis=cifras["unidad_dosis"],
        cantidad_total=cifras["cantidad_total"],
        unidad_cantidad=cifras["unidad_cantidad"],
        dosis_calculada=cifras["dosis_calculada"],
        cantidad_total_calculada=cifras["cantidad_total_calculada"],
        notas=(datos.notas or "").strip()[:500] or None,
        clave_de_reenvio=clave,
    )
    db.add(siembra)
    db.flush()

    sobre_el_descuento: list[str] = []
    if cifras["cantidad_total"] is None:
        # No se sabe cuánto se sembró: **no se resta nada**. No es un cero, es un hueco, y se dice.
        sobre_el_descuento.append(textos.MENSAJES["SM16_no_se_puede_sacar_sin_cantidad"])
    elif cifras["unidad_cantidad"] is None:
        sobre_el_descuento.append(textos.MENSAJES["SM17_no_se_puede_sacar_sin_envase"])
    elif lote is None:
        # Se sabe cuánto, pero no de dónde sale. Aquí está lo que evita restar de un envase que no es.
        sobre_el_descuento.append(
            textos.MENSAJES["SM18_la_semilla_no_esta_en_el_almacen"]
            if not _tiene_envases(db, semilla)
            else textos.MENSAJES["SM17_no_se_puede_sacar_sin_envase"]
        )
    else:
        _sacar_la_semilla_del_almacen(
            db=db,
            explotacion=explotacion,
            usuario=usuario,
            siembra=siembra,
            lote=lote,
            cantidad=cifras["cantidad_total"],
            unidad=cifras["unidad_cantidad"],
            clave=clave,
            aceptar_descuadre=datos.aceptar_descuadre,
        )

    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="siembra",
            entidad_id=siembra.id,
            accion="crear",
            datos={
                "semilla": semilla.id,
                "tierra": siembra.parcela_id,
                "superficie_ha": siembra.superficie_ha,
                "dosis_por_ha": siembra.dosis_por_ha,
                "unidad_dosis": siembra.unidad_dosis,
                "cantidad_total": siembra.cantidad_total,
                "unidad_cantidad": siembra.unidad_cantidad,
                "calculada": siembra.cantidad_total_calculada or siembra.dosis_calculada,
                "lote_id": siembra.lote_id,
            },
        )
    )
    if clave is None:
        sobre_el_descuento.append(textos.MENSAJES["SM21_no_se_pudo_comprobar_si_ya_estaba"])
    db.commit()
    db.refresh(siembra)
    return _la_siembra(
        db, siembra, avisos=_lo_que_hay_que_decir(sobre_el_descuento, cifras)
    )


def _tiene_envases(db, semilla: models.Semilla) -> bool:
    """¿Esta semilla tiene algún envase dado de entrada en el almacén?"""
    return (
        db.scalar(
            select(models.Lote.id).where(
                models.Lote.explotacion_id == semilla.explotacion_id,
                models.Lote.articulo_id == semilla.articulo_id,
            )
        )
        is not None
    )


@router_siembras.get("", response_model=list[SiembraSalida])
def listar_las_siembras(
    explotacion: ExplotacionActual, db: Db, parcela_id: int | None = None
) -> list[dict]:
    """Lo que se ha sembrado, con la semilla y la tierra resueltas y **si descontó o no y por qué**.

    Las anuladas salen también: no se borran, se quedan tachadas con su motivo (y lo que salió del
    almacén vuelve a contar). Esconderlas haría que el agricultor no pudiera entender por qué la
    semilla que le queda no es la que él calcula.
    """
    consulta = select(models.Siembra).where(models.Siembra.explotacion_id == explotacion.id)
    if parcela_id is not None:
        obtener_de_la_explotacion(db, models.Parcela, parcela_id, explotacion.id)
        consulta = consulta.where(models.Siembra.parcela_id == parcela_id)
    siembras = list(
        db.scalars(
            consulta.order_by(
                models.Siembra.fecha.is_(None),
                models.Siembra.fecha.desc(),
                models.Siembra.id.desc(),
            )
        )
    )
    return [_la_siembra(db, siembra) for siembra in siembras]


@router_siembras.get("/{siembra_id}", response_model=SiembraSalida)
def ver_una_siembra(siembra_id: int, explotacion: ExplotacionActual, db: Db) -> dict:
    siembra = obtener_de_la_explotacion(db, models.Siembra, siembra_id, explotacion.id)
    return _la_siembra(db, siembra)


@router_siembras.put("/{siembra_id}", response_model=SiembraSalida)
def corregir_una_siembra(
    siembra_id: int,
    datos: SiembraEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Corregir una siembra **sin que queden dos descuentos**.

    ESTA ES LA PARTE DEL TICKET QUE MÁS CUIDADO TIENE, y se resuelve así:

      · Lo que cambia de la siembra (la tierra, la fecha, las hectáreas, las dos cifras, las notas) se
        corrige **en la misma fila**, y en la auditoría queda lo que decía antes
        (`correcciones.corregir`).
      · Y si lo que cambia es **lo que salió del almacén** —la cantidad, la unidad, el envase o la
        fecha—, la salida vieja se **anula** (con su motivo: se corrigió la siembra) y se apunta una
        nueva por la puerta de las salidas. Nunca se reescribe la cantidad de un movimiento por
        detrás: eso dejaría el libro diciendo algo que nadie apuntó. Y nunca quedan dos vivas: la
        anulada sigue en el libro, tachada, y no cuenta.
      · Si lo que había no había descontado nada porque faltaba un dato, y ahora el dato está, la
        salida se apunta ahora. Es el camino de «me faltaba la cantidad y ya la sé».
    """
    siembra = obtener_de_la_explotacion(db, models.Siembra, siembra_id, explotacion.id)
    if siembra.anulada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("SM23_la_siembra_esta_anulada"),
        )
    # **Lo que ya constaba y la petición no vuelve a mandar, se queda.** Ver `_lo_que_se_corrige`.
    lo_que_hay = _lo_que_se_corrige(datos, siembra)
    semilla = obtener_de_la_explotacion(db, models.Semilla, lo_que_hay["semilla_id"], explotacion.id)
    if lo_que_hay["semilla_id"] != siembra.semilla_id:
        # **La semilla de una siembra guardada no se cambia, y se dice por qué.** La salida del almacén
        # pertenece a un artículo: si se cambiara la semilla, el descuento que había dejaría de contar
        # (porque el envase es de la otra semilla) y la siembra pasaría a decir que se sembró otra cosa
        # **sin que nadie haya visto nada** — el agricultor vería la semilla volver al almacén sola. Lo
        # que hay que hacer es anular esta y apuntar la nueva, que es lo que dice el mensaje. Lo cazó la
        # revisión del T10: antes se cambiaba en silencio.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("SM34_la_semilla_no_se_cambia"),
        )
    obtener_de_la_explotacion(db, models.Parcela, lo_que_hay["parcela_id"], explotacion.id)
    lote = None
    if lo_que_hay["lote_id"] is not None:
        lote = _el_lote_comprobado(db, lo_que_hay["lote_id"], semilla, explotacion)

    cifras = _las_cifras_de(lo_que_hay)
    anterior = _la_salida_viva(db, siembra)
    sobre_el_descuento: list[str] = []

    cantidad = cifras["cantidad_total"]
    unidad = cifras["unidad_cantidad"]
    quiere_descontar = cantidad is not None and unidad is not None and lote is not None

    if anterior is not None and (
        not quiere_descontar
        or abs((anterior.cantidad or 0) - cantidad) > 1e-9
        or (anterior.unidad or "") != unidad
        or anterior.lote_id != lote.id
        or anterior.fecha != lo_que_hay["fecha"]
    ):
        # Lo que había ya no vale: se anula con su motivo y se apunta lo nuevo. **Nada se borra**: la
        # salida vieja se queda en el libro, tachada, y deja de contar.
        anterior.anulado = True
        anterior.motivo_anulacion = textos.MENSAJES["SM30_la_salida_se_corrigio"]
        db.add(
            models.Auditoria(
                explotacion_id=explotacion.id,
                usuario_id=usuario.id,
                entidad="movimiento_de_existencias",
                entidad_id=anterior.id,
                accion="anular",
                datos={"motivo": anterior.motivo_anulacion, "por": f"siembra {siembra.id}"},
            )
        )
        db.flush()
        if quiere_descontar:
            sobre_el_descuento.append(
                textos.MENSAJES["SM25_lo_que_salio_cambio"].format(
                    antes=anterior.cantidad,
                    ahora=cantidad,
                    unidad=unidad,
                )
            )
    elif anterior is None and quiere_descontar:
        # Antes no se pudo descontar (faltaba la cantidad o el envase) y ahora sí.
        sobre_el_descuento.append(
            textos.MENSAJES["SM31_ahora_si_descuenta"].format(
                cantidad=cantidad, unidad=unidad
            )
        )

    if quiere_descontar:
        _sacar_la_semilla_del_almacen(
            db=db,
            explotacion=explotacion,
            usuario=usuario,
            siembra=siembra,
            lote=lote,
            cantidad=cantidad,
            unidad=unidad,
            clave=_la_clave(datos),
            aceptar_descuadre=datos.aceptar_descuadre,
        )
    elif cantidad is None:
        sobre_el_descuento.append(textos.MENSAJES["SM16_no_se_puede_sacar_sin_cantidad"])
    elif lote is None:
        sobre_el_descuento.append(textos.MENSAJES["SM17_no_se_puede_sacar_sin_envase"])

    preparada = models.Siembra(
        explotacion_id=explotacion.id,
        parcela_id=lo_que_hay["parcela_id"],
        semilla_id=semilla.id,
        lote_id=lote.id if lote else None,
        fecha=lo_que_hay["fecha"],
        superficie_ha=cifras["superficie_ha"],
        dosis_por_ha=cifras["dosis_por_ha"],
        unidad_dosis=cifras["unidad_dosis"],
        cantidad_total=cifras["cantidad_total"],
        unidad_cantidad=cifras["unidad_cantidad"],
        dosis_calculada=cifras["dosis_calculada"],
        cantidad_total_calculada=cifras["cantidad_total_calculada"],
        notas=(lo_que_hay["notas"] or "").strip()[:500] or None,
        # **La clave no se toca al corregir**, y esto no es un detalle: si se perdiera, un reenvío de
        # la petición original (la cola del móvil) ya no reconocería esta siembra y apuntaría otra,
        # con su descuento. Es la misma trampa que el proyecto ya tiene contada para las correcciones.
        clave_de_reenvio=siembra.clave_de_reenvio,
        # Y los tres campos que `correcciones.corregir` copiaría a nulo porque su lista de «no se
        # toca» está escrita en masculino (`anulado`, `creado_en`) y estas columnas son femeninas: sin
        # esto, corregir una siembra reventaría contra la base con un NOT NULL. Se copian los mismos
        # valores, así que no cuentan como cambio ni ensucian la auditoría.
        anulada=siembra.anulada,
        motivo_anulacion=siembra.motivo_anulacion,
        creada_en=siembra.creada_en,
    )
    correcciones.corregir(
        db,
        guardado=siembra,
        preparado=preparada,
        entidad="siembra",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    db.refresh(siembra)
    return _la_siembra(
        db, siembra, avisos=_lo_que_hay_que_decir(sobre_el_descuento, cifras)
    )


@router_siembras.post("/{siembra_id}/anular", response_model=SiembraSalida)
def anular_una_siembra(
    siembra_id: int,
    datos: AnulacionEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
) -> dict:
    """Anular una siembra, con su motivo. **Y lo que salió del almacén vuelve a contar.**

    Esto es lo mejor de haber hecho que la semilla salga por la puerta de las salidas: anular la
    siembra devuelve la semilla al almacén **sin tocar el libro**. El movimiento se queda donde está,
    con su fecha, su cantidad y quién lo apuntó, y deja de contar porque
    `servicios.estado_de_los_origenes` mira si la siembra está anulada (igual que un tratamiento
    anulado: «anular 2 L devuelve 2»). Nada se borra y no hay dos descuentos que deshacer.

    Un motivo es obligatorio y tiene que tener al menos tres letras: dentro de dos años, el motivo es
    lo único que explica por qué esa semilla no se sembró.
    """
    siembra = obtener_de_la_explotacion(db, models.Siembra, siembra_id, explotacion.id)
    if siembra.anulada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje("SM23_la_siembra_esta_anulada"),
        )
    motivo = (datos.motivo or "").strip()
    if len(motivo) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=textos.mensaje("SM24_falta_el_motivo_para_anular"),
        )
    tenia_salida = _la_salida_viva(db, siembra) is not None
    siembra.anulada = True
    siembra.motivo_anulacion = motivo[:500]
    db.add(
        models.Auditoria(
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="siembra",
            entidad_id=siembra.id,
            accion="anular",
            datos={"motivo": siembra.motivo_anulacion, "tenia_salida": tenia_salida},
        )
    )
    db.commit()
    db.refresh(siembra)
    avisos = [textos.MENSAJES["SM32_lo_que_salio_vuelve_a_contar"]] if tenia_salida else []
    return _la_siembra(db, siembra, avisos=avisos)
