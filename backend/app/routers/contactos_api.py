"""Los contactos: la misma persona o empresa apuntada una sola vez (T11, 03/10/2026).

## Qué había, y qué añade esto

El cuaderno guarda el nombre de un proveedor, de un comprador, de un laboratorio o de un asesor
**escrito a mano en ocho sitios**: el proveedor de una factura y de un albarán, el comprador de una
venta, el laboratorio de un análisis, el proveedor de un producto del catálogo y el de un artículo
del almacén, y el nombre de un aplicador y de un asesor. La consecuencia es la de siempre: el mismo
señor se teclea una vez por papel, y dos formas de escribirlo conviven sin que nadie sepa que son la
misma persona.

Aquí hay tres cosas:

  1. **La ficha del contacto** (`/api/contactos`): una persona o una empresa, con sus datos y con
     **los papeles que hace con esta finca**, que se pueden solapar (la misma cooperativa te vende la
     semilla y te compra el trigo).
  2. **El enlace** (`/api/contactos/{id}/enlaces`): decir «este nombre que ya está escrito en esta
     factura es esta persona». El texto **no se toca**: sigue donde estaba y sigue diciendo lo mismo.
  3. **La revisión de los nombres** (`/api/contactos/migracion`): lo que ya está escrito, agrupado en
     fichas que **se le proponen al agricultor**, con los casos que no se pueden juntar señalados uno
     por uno.

## Las tres reglas que este fichero cumple, y que no se pueden doblar

  · **La migración propone; no crea hechos.** `GET /api/contactos/migracion` no escribe nada (hay una
    prueba que mira la base antes y después), y lo que apunta `POST .../aplicar` es exactamente la
    propuesta que el agricultor ha confirmado por su clave: el servidor **recalcula** la propuesta y
    comprueba que sigue siendo la misma. Si entre mirar y confirmar entra una factura, lo dice.
  · **Lo que no se puede asegurar no se junta, ni aunque se lo pidan.** Las propuestas inseguras (dos
    nombres que se parecen, o el mismo nombre con dos NIF) **se enseñan y no se apuntan**: el
    servidor contesta 409 y no crea nada. Un «no se fusiona» que solo viviera en la pantalla se
    podría saltar desde fuera, y este es justo el fallo que el ticket prohíbe.
  · **No se borra ni se reescribe ni un texto histórico.** En todo el fichero no hay ni un `UPDATE`
    sobre una tabla de documentos. Los enlaces viven en su propia tabla, y por eso deshacer la
    migración es borrar lo que creó. El resultado lo dice en el dato (`textos_tocados: 0`), no en un
    comentario.
"""

from __future__ import annotations

import datetime as dt
import hashlib

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .. import contactos as logica
from .. import saldos
from .. import correcciones, models, textos
from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
from ..schemas import (
    ConfirmacionDeLaMigracion,
    BajaDeUnContacto,
    CanalDeUnContactoEntrada,
    EntradaDeUnaTarea,
    SaldoDeUnContacto,
    NotaDeUnContactoEntrada,
    ContactoEntrada,
    ContactoSalida,
    DeshacerLaMigracion,
    EnlaceEntrada,
    FichaDelContacto,
    NombreEscrito,
    PapelEntrada,
    ResultadoDeLaMigracion,
    RevisionDeLosNombres,
)

router = APIRouter(prefix="/api/contactos", tags=["contactos"])

# Los dos orígenes de un enlace y de una ficha. Son dos cadenas cortas y van a la base, así que
# viven aquí como constantes: escribirlas a mano en ocho sitios es la forma de que un día una diga
# «migración» con tilde y deshacer deje de encontrarla.
A_MANO = "a_mano"
DE_LA_MIGRACION = "migracion"


# --------------------------------------------------------------------------
# Leer lo que hay escrito, sin tocar nada
# --------------------------------------------------------------------------


def _el_modelo(tabla: str):
    """El modelo de esa tabla, por su nombre, o `None`.

    Hace falta porque los enlaces apuntan a ocho tablas distintas. **Se busca en las tablas de
    verdad**, así que una tabla que no exista devuelve `None` y quien llama contesta 404: por aquí
    entra un nombre que viene del navegador y no puede acabar dentro de una consulta.
    """
    for mapper in models.Base.registry.mappers:
        if mapper.class_.__tablename__ == tabla:
            return mapper.class_
    return None


def _los_enlaces(db, explotacion_id: int) -> dict[tuple[str, str, int], models.EnlaceDeContacto]:
    """Todos los enlaces de la finca, por dónde está el texto.

    Se leen de una vez y no uno por uno: lo que se hace con ellos es contestar «¿este texto ya tiene
    dueño?» para cada nombre escrito, y eso son ocho consultas por fila si se preguntara al revés.
    """
    enlaces = db.scalars(
        select(models.EnlaceDeContacto).where(
            models.EnlaceDeContacto.explotacion_id == explotacion_id
        )
    )
    return {(e.tabla, e.campo, e.registro_id): e for e in enlaces}


def _el_texto_escrito(fila, enlace: logica.CampoDeTexto) -> str:
    """El nombre tal y como está escrito hoy. Es lo único que se lee de la fila."""
    return logica.limpia(getattr(fila, enlace.campo, None))


def _las_tablas_que_hay(db) -> set[str]:
    """Los nombres de las tablas que existen **de verdad** en esta base.

    **Por qué hace falta, con el caso que lo trajo.** En una instalación vieja puede no estar todavía
    alguna de las tablas donde se busca un nombre escrito: el programa las crea al arrancar, pero el
    guion de la migración (`scripts/migrar_contactos.py`) **no las crea cuando solo está mirando** —eso
    cambiaría el esquema y el informe dice que no toca nada—, así que al leer la base del agricultor se
    encontró con que `recepciones` no existía y el informe se cayó con una traza de SQLite. Se descubrió
    ensayando sobre una copia de la base de verdad, que es justo para lo que se ensaya.

    Una tabla que no está no tiene nombres escritos: no es un fallo, es un dato.
    """
    from sqlalchemy import inspect as inspeccionar

    return set(inspeccionar(db.get_bind()).get_table_names())


def _los_escritos(
    db, explotacion_id: int, *, con_enlaces: bool = True, tablas: set[str] | None = None
) -> list[dict]:
    """**Todos los nombres escritos a mano en esta finca**, con de dónde son y si ya tienen dueño.

    Lo que devuelve cada uno es un diccionario preparado para `schemas.NombreEscrito`, y las tres
    cosas que conviene entender:

      · **El texto sale de la fila, se lee ahora.** No hay ninguna copia guardada, así que la
        propuesta y la lista de vínculos hablan siempre de lo que hay de verdad.
      · **Un enlace cuyo documento ya no existe no aparece**, porque se recorre lo que hay: si el
        agricultor borró la factura, su enlace no puede salir en ninguna lista como si existiera.
      · **`texto_cambiado`** se calcula comparando lo que hay con `nombre_de_entonces`: el enlace no
        se rompe cuando el agricultor corrige el nombre del papel, pero se dice, porque puede que ya
        no sea el mismo.
    """
    enlaces = _los_enlaces(db, explotacion_id) if con_enlaces else {}
    if tablas is None:
        tablas = _las_tablas_que_hay(db)
    escritos: list[dict] = []
    for enlace in logica.ENLACES:
        # **Una tabla que no está en esta base no tiene nombres escritos.** Ver `_las_tablas_que_hay`.
        if enlace.tabla not in tablas:
            continue
        modelo = _el_modelo(enlace.tabla)
        if modelo is None:  # pragma: no cover — la lista de campos y los modelos van juntos
            continue
        filas = db.scalars(
            select(modelo).where(modelo.explotacion_id == explotacion_id)
        )
        for fila in filas:
            texto = _el_texto_escrito(fila, enlace)
            if not texto:
                # **Un nombre en blanco no es un nombre.** No se propone nada con él ni se ofrece
                # enlazarlo: lo que hay que hacer con esa factura es rellenarla, y eso ya lo dice la
                # pantalla de facturas.
                continue
            referencia = [
                str(getattr(fila, columna, "") or "")
                for columna in enlace.referencia
                if getattr(fila, columna, None)
            ]
            fecha = getattr(fila, enlace.campo_fecha, None) if enlace.campo_fecha else None
            suyo = enlaces.get((enlace.tabla, enlace.campo, fila.id))
            escritos.append(
                {
                    "tabla": enlace.tabla,
                    "campo": enlace.campo,
                    "registro_id": fila.id,
                    "texto": texto,
                    "nif": logica.limpia(getattr(fila, enlace.campo_nif, None))
                    if enlace.campo_nif
                    else None,
                    "papel": enlace.papel,
                    "clave": enlace.clave,
                    "referencia": referencia,
                    "fecha": fecha if isinstance(fecha, dt.date) else None,
                    "anulada": _esta_anulada(fila),
                    "enlace_id": suyo.id if suyo else None,
                    "contacto_id": suyo.contacto_id if suyo else None,
                    "texto_cambiado": bool(
                        suyo and logica.limpia(suyo.nombre_de_entonces) != texto
                    ),
                    "texto_de_entonces": suyo.nombre_de_entonces if suyo else None,
                }
            )
    escritos.sort(key=lambda uno: (uno["tabla"], uno["campo"], uno["registro_id"]))
    return escritos


def _esta_anulada(fila) -> bool | None:
    """Si ese documento está anulado, cuando la tabla lo dice. `None` es «esa tabla no lo dice».

    **No es lo mismo que `False`**, y por eso hay tres respuestas: una factura que no se puede anular
    (el producto del catálogo, un aplicador) no está «no anulada», es que ahí esa pregunta no existe.
    """
    for nombre in ("anulada", "anulado"):
        if hasattr(fila, nombre):
            return bool(getattr(fila, nombre))
    return None


def _lo_que_escribe_cada_papel(escritos: list[dict]) -> dict[int, list[str]]:
    """El papel que le toca a cada contacto **según lo que hay escrito**, por contacto.

    Es lo que hace visible que los papeles se solapan: la misma cooperativa sale como proveedor por
    una factura y como comprador por una venta, y los dos papeles son suyos sin que nadie los marque
    a mano. Se usa en la pantalla de la revisión, para avisar de que una ficha que ya existe tendría
    otro papel más.
    """
    papeles: dict[int, list[str]] = {}
    for escrito in escritos:
        if not escrito["contacto_id"] or not escrito["papel"]:
            continue
        suyos = papeles.setdefault(escrito["contacto_id"], [])
        if escrito["papel"] not in suyos:
            suyos.append(escrito["papel"])
    return papeles


# --------------------------------------------------------------------------
# La ficha de un contacto
# --------------------------------------------------------------------------


def _los_papeles(db, contacto: models.Contacto) -> list[str]:
    """Los papeles de un contacto, en el orden del catálogo (no en el que se marcaron)."""
    suyos = {
        papel.papel
        for papel in db.scalars(
            select(models.PapelDeUnContacto).where(
                models.PapelDeUnContacto.explotacion_id == contacto.explotacion_id,
                models.PapelDeUnContacto.contacto_id == contacto.id,
            )
        )
    }
    return [papel for papel in logica.PAPELES if papel in suyos]


def _pintar_contacto(
    contacto: models.Contacto,
    *,
    papeles: list[str],
    escritos: list[dict] | None,
    papeles_escritos: dict[int, list[str]] | None = None,
) -> dict:
    """Un contacto con sus papeles, sus enlaces vivos y las formas en que está escrito su nombre.

    **`enlaces` cuenta solo los vivos.** Un enlace cuyo documento se ha borrado no se cuenta ni se
    enseña: decir «3 vínculos» y que al abrirlos haya dos es peor que no decir nada.
    """
    suyos = [uno for uno in (escritos or []) if uno["contacto_id"] == contacto.id]
    return {
        "id": contacto.id,
        "nombre": contacto.nombre,
        # **El estado, que hay que decir** (CRM-03, criterio (e), 11/10/2026). Se cuenta aquí y **no se deja
        # con un valor por defecto en el esquema**: la primera versión ponía `activo: bool = True` en
        # `ContactoSalida` y, como esta respuesta no lo traía, **el esquema rellenaba `True` y tapaba el valor
        # de verdad** —una ficha de baja se leía como activa—. Lo cazó la prueba del criterio (e). Un valor por
        # defecto en una salida es una mentira que espera su turno: si falta el dato, tiene que fallar.
        "activo": contacto.activo,
        # **La lista no lleva las notas**: se leen al abrir la ficha, que es cuando se miran. Se manda la lista
        # vacía —y se manda— porque el esquema la exige: una ficha sin notas y una ficha a la que se le han
        # olvidado no pueden leerse igual.
        "notas_con_autor": [],
        "canales": [],
        "tareas": [],
        "es_empresa": contacto.es_empresa,
        "nif": contacto.nif,
        "telefono": contacto.telefono,
        "correo": contacto.correo,
        "direccion": contacto.direccion,
        "localidad": contacto.localidad,
        "notas": contacto.notas,
        "origen": contacto.origen,
        "papeles": papeles,
        # Los que dicen sus papeles, sin repetir los que ya tiene marcados: lo que se enseña es lo que
        # le falta por marcar, no la lista entera otra vez.
        "papeles_segun_lo_escrito": [
            papel
            for papel in (papeles_escritos or {}).get(contacto.id, [])
            if papel not in papeles
        ],
        "enlaces": len(suyos),
        "nombres_escritos": sorted({uno["texto"] for uno in suyos}),
    }


CLASES_DE_CANAL = ("telefono", "correo", "direccion")


def _los_canales(db, contacto: models.Contacto) -> list[dict]:
    """Los canales de una ficha, **el principal de cada clase primero** y luego los demás por etiqueta.

    Se ordena así porque es como se lee: lo que hay que usar, arriba.
    """
    suyos = list(
        db.scalars(
            select(models.CanalDeUnContacto).where(
                models.CanalDeUnContacto.explotacion_id == contacto.explotacion_id,
                models.CanalDeUnContacto.contacto_id == contacto.id,
            )
        )
    )
    suyos.sort(key=lambda canal: (canal.clase, not canal.principal, (canal.etiqueta or "").lower(), canal.id))
    return [
        {
            "id": canal.id,
            "clase": canal.clase,
            "etiqueta": canal.etiqueta,
            "telefono": canal.telefono,
            "correo": canal.correo,
            "direccion": canal.direccion,
            "localidad": canal.localidad,
            "principal": canal.principal,
        }
        for canal in suyos
    ]


def _el_canal_de_la_ficha(db, explotacion_id: int, contacto_id: int, canal_id: int):
    """El canal **de esa ficha**, o 404. No se contesta «no es tuyo»: eso ya diría que existe."""
    canal = db.scalar(
        select(models.CanalDeUnContacto).where(
            models.CanalDeUnContacto.explotacion_id == explotacion_id,
            models.CanalDeUnContacto.contacto_id == contacto_id,
            models.CanalDeUnContacto.id == canal_id,
        )
    )
    if canal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=textos.mensaje("C7_no_existe"))
    return canal


def _apartar_el_principal_de_su_clase(db, contacto: models.Contacto, clase: str) -> None:
    """Quita de principal al que lo era **de esa clase**, para que el nuevo pueda serlo.

    **Va antes de poner el nuevo, y no es un detalle de estilo**: el índice parcial de la base garantiza **un solo
    principal por clase y ficha**, así que si se pusiera primero el nuevo, la base rechazaría el cambio. Se hace en
    la misma transacción que el alta, de modo que **nunca hay dos principales ni ninguno**.
    """
    el_que_era = db.scalar(
        select(models.CanalDeUnContacto).where(
            models.CanalDeUnContacto.explotacion_id == contacto.explotacion_id,
            models.CanalDeUnContacto.contacto_id == contacto.id,
            models.CanalDeUnContacto.clase == clase,
            models.CanalDeUnContacto.principal.is_(True),
        )
    )
    if el_que_era is not None:
        el_que_era.principal = False


def _un_canal_guardable(datos) -> dict:
    """Lo que se guarda de un canal, **comprobando solo lo que hay que comprobar**.

    La clase tiene que ser una de las tres y tiene que venir **algo escrito**; y de lo que venga, se guarda lo que
    corresponda a su clase. **No se valida el formato**: un teléfono se guarda tal cual (ver el modelo).
    """
    clase = (datos.clase or "").strip()
    if clase not in CLASES_DE_CANAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C7_esa_clase_de_canal_no_existe"),
        )
    suyos = {
        "telefono": logica.limpia(datos.telefono) or None,
        "correo": logica.limpia(datos.correo) or None,
        "direccion": logica.limpia(datos.direccion) or None,
        "localidad": logica.limpia(datos.localidad) or None,
    }
    if not any(suyos[clase] for clase in (clase,) if suyos.get(clase)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C7_un_canal_necesita_algo_escrito"),
        )
    # Lo que no es de su clase **no se guarda**, aunque venga: un teléfono con dirección dentro es un dato cruzado.
    return {
        "clase": clase,
        "etiqueta": logica.limpia(datos.etiqueta) or None,
        "telefono": suyos["telefono"] if clase == "telefono" else None,
        "correo": suyos["correo"] if clase == "correo" else None,
        "direccion": suyos["direccion"] if clase == "direccion" else None,
        "localidad": suyos["localidad"] if clase == "direccion" else None,
    }


def _una_tarea(tarea: models.Tarea, hoy: dt.date | None = None) -> dict:
    """Una tarea, con **lo que se calcula** al leer.

    **`vencida` no se guarda**: se calcula (fecha anterior a hoy **y** todavía pendiente). El encargo lo dice con
    estas palabras: *«la fecha vencida no transforma automáticamente una tarea en cancelada»*. Si fuera un estado
    guardado haría falta algo que pasara por las filas cada noche, y lo que no se ejecuta no se puede prometer.

    **Y la fecha se dice con palabras** («15/10/2026») o «Sin fecha»: el front no tiene que saber formatear fechas,
    que es de donde salen los errores de formato y de zona horaria. «Sin fecha» **no es** «hoy».
    """
    hoy = hoy or dt.date.today()
    return {
        "id": tarea.id,
        "contacto_id": tarea.contacto_id,
        "titulo": tarea.titulo,
        "descripcion": tarea.descripcion,
        "responsable": tarea.responsable,
        "fecha_prevista": tarea.fecha_prevista,
        "fecha_texto": (
            tarea.fecha_prevista.strftime("%d/%m/%Y") if tarea.fecha_prevista else "Sin fecha"
        ),
        "estado": tarea.estado,
        "vencida": bool(
            tarea.fecha_prevista
            and tarea.estado == models.Tarea.PENDIENTE
            and tarea.fecha_prevista < hoy
        ),
        "completada_en": tarea.completada_en,
        "completada_por": tarea.completada_por,
        "cancelada_en": tarea.cancelada_en,
        "cancelada_por": tarea.cancelada_por,
    }


def _las_tareas(db, contacto: models.Contacto) -> list[dict]:
    """Las tareas de una ficha: **primero lo que hay que hacer**, y dentro de eso lo más antiguo primero.

    El orden es el del trabajo: las pendientes antes que las hechas, y entre las pendientes **lo vencido arriba**,
    porque es lo que se ha pasado de fecha. Lo que ya está hecho o cancelado va al final y no estorba.
    """
    suyas = list(
        db.scalars(
            select(models.Tarea).where(
                models.Tarea.explotacion_id == contacto.explotacion_id,
                models.Tarea.contacto_id == contacto.id,
            )
        )
    )
    suyas.sort(
        key=lambda t: (
            t.estado != models.Tarea.PENDIENTE,
            # Sin fecha va **después** de las que tienen día: una tarea sin día no está «para ya».
            t.fecha_prevista is None,
            t.fecha_prevista or dt.date.max,
            t.id,
        )
    )
    return [_una_tarea(t) for t in suyas]


def _las_notas(db, contacto: models.Contacto) -> list[dict]:
    """Las notas de una ficha, **de la más nueva a la más vieja**, con el nombre de quien la escribió.

    Va aquí, en `_la_ficha`, y **no** en `_pintar_contacto`: aquella no recibe la sesión de la base (11/10/2026,
    y costó una ronda entera de trabajo perdido por meterlo ahí).

    El nombre del autor se busca con una consulta aparte en vez de con una relación: son pocas notas por ficha y
    así esta pantalla no arrastra el modelo de usuarios entero. Si el autor no está —o la escribió el programa—,
    se dice con `None` y la pantalla lo enseña como «el programa».
    """
    suyas = list(
        db.scalars(
            select(models.NotaDeUnContacto)
            .where(models.NotaDeUnContacto.contacto_id == contacto.id)
            .order_by(models.NotaDeUnContacto.creado_en.desc(), models.NotaDeUnContacto.id.desc())
        )
    )
    los_autores = [nota.usuario_id for nota in suyas if nota.usuario_id]
    nombres = (
        {
            fila.id: fila.nombre
            for fila in db.scalars(select(models.Usuario).where(models.Usuario.id.in_(los_autores)))
        }
        if los_autores
        else {}
    )
    # **Tres estados y no dos** (13/10/2026). Antes, si el nombre del autor no aparecía, la pantalla decía «Lo
    # apuntó el programa» —y eso es **afirmar algo que no se sabe**: una nota escrita por una persona cuyo nombre
    # ya no está no es una nota del programa. Se distinguen:
    #
    #   - `el_programa`: la nota no tiene autor porque la escribió el programa.
    #   - `sin_nombre`: **la escribió una persona, pero su nombre ya no se puede poner** (el usuario se borró, o su
    #     ficha ya no está). Se dice eso, que es lo que se sabe, en vez de inventar un autor o culpar al programa.
    #   - `persona`: se sabe quién la escribió, y se dice su nombre.
    return [
        {
            "id": nota.id,
            "texto": nota.texto,
            # **Un nombre vacío no es un nombre**: si el nombre del autor se quedó sin poner, se contesta `None`
            # —que es «no se sabe» en esta casa— y el estado lo explica. Devolver `""` sería enseñar un hueco en
            # la pantalla y dejar creer que el autor es alguien sin nombre. (Lo cazó la prueba de los tres
            # estados, 13/10/2026.)
            "autor": (nombres.get(nota.usuario_id) or None) if nota.usuario_id else None,
            "autor_estado": _el_estado_del_autor(nota, nombres),
            "creado_en": nota.creado_en,
            "clave_de_reenvio": nota.clave_de_reenvio,
        }
        for nota in suyas
    ]


def _el_estado_del_autor(nota, nombres: dict) -> str:
    """De quién es la nota, con los tres estados de arriba. **No se inventa un autor y no se culpa al programa.**"""
    if not nota.usuario_id:
        return "el_programa"
    return "persona" if nombres.get(nota.usuario_id) else "sin_nombre"



def _la_ficha(db, contacto: models.Contacto, escritos: list[dict]) -> dict:
    """La ficha con sus vínculos uno por uno, que es lo que se mira al abrirla."""
    suyos = [uno for uno in escritos if uno["contacto_id"] == contacto.id]
    enlaces = {uno["enlace_id"]: uno for uno in suyos}
    origenes = {
        fila.id: fila.origen
        for fila in db.scalars(
            select(models.EnlaceDeContacto).where(
                models.EnlaceDeContacto.explotacion_id == contacto.explotacion_id,
                models.EnlaceDeContacto.contacto_id == contacto.id,
            )
        )
    }
    return {
        **_pintar_contacto(
            contacto,
            papeles=_los_papeles(db, contacto),
            escritos=escritos,
            papeles_escritos=_lo_que_escribe_cada_papel(escritos),
        ),
        # **Las notas, con su autor** (CRM-03, criterio (f)): la lista entera, de la más nueva a la más vieja.
        # El campo `notas` de siempre se queda como está —es el texto libre de la ficha— y esto es el diario.
        "notas_con_autor": _las_notas(db, contacto),
        # **Y sus canales** (Entrega 2): con su etiqueta y su principal. La lista de contactos manda
        # la lista vacía, igual que con las notas: se miran al abrir la ficha.
        "canales": _los_canales(db, contacto),
        # **Y sus próximas acciones** (Entrega 3): lo que hay que hacer con este contacto, con lo
        # pendiente y lo vencido primero. La lista manda la lista vacía, como con las notas.
        "tareas": _las_tareas(db, contacto),
        "vivos": [
            {
                "id": identificador,
                "origen": origenes.get(identificador, A_MANO),
                "escrito": escrito,
            }
            for identificador, escrito in sorted(enlaces.items())
        ],
    }


def _el_contacto_de_la_finca(db, explotacion_id: int, contacto_id: int) -> models.Contacto:
    """**404 y no 403**, como todo: no se filtra si un contacto existe en otra finca."""
    return obtener_de_la_explotacion(db, models.Contacto, contacto_id, explotacion_id)


def _guardar_los_papeles(db, contacto: models.Contacto, papeles: list[str]) -> list[str]:
    """Deja los papeles del contacto en los que vengan, y devuelve los que se han quedado."""
    quiere = list(dict.fromkeys(papeles))
    tiene = {
        fila.papel: fila
        for fila in db.scalars(
            select(models.PapelDeUnContacto).where(
                models.PapelDeUnContacto.explotacion_id == contacto.explotacion_id,
                models.PapelDeUnContacto.contacto_id == contacto.id,
            )
        )
    }
    for papel, fila in tiene.items():
        if papel not in quiere:
            db.delete(fila)
    for papel in quiere:
        if papel not in tiene:
            db.add(
                models.PapelDeUnContacto(
                    explotacion_id=contacto.explotacion_id,
                    contacto_id=contacto.id,
                    papel=papel,
                )
            )
    return [papel for papel in logica.PAPELES if papel in quiere]


def _papeles_que_se_quedan(db, contacto: models.Contacto, datos) -> None:
    """Toca los papeles de la ficha **solo si la petición habla de ellos**.

    ESTA ES LA REGLA DEL PROYECTO, Y AQUÍ FALTABA (lo encontró la auditoría del 05/10/2026): un campo
    que no viene **no está diciendo que no haya ninguno**, está diciendo que de eso no habla. Antes,
    `papeles` valía `[]` cuando la petición no lo mandaba, y `_guardar_los_papeles` borra todo lo que no
    venga en la lista: corregir el teléfono desde la API —o desde una pantalla futura que no pregunte
    los papeles— **dejaba la ficha sin ninguno**, en silencio y sin que nadie lo hubiera pedido.

    Se distingue «no lo manda» de «lo manda vacío» con `model_fields_set`: quien manda `papeles: []`
    está diciendo que los quite (y se quitan); quien no manda `papeles` no dice nada (y se quedan). Es
    la misma forma —y el mismo motivo— que en la siembra (`semillas_api._lo_que_se_corrige`), y lo que
    pide el contrato §2: comparación de cambios, no sobreescritura.
    """
    if "papeles" not in datos.model_fields_set:
        return
    _guardar_los_papeles(db, contacto, _comprobar_los_papeles(datos.papeles))


def _comprobar_los_papeles(papeles: list[str]) -> list[str]:
    """**Un papel que no está en el catálogo se dice, no se filtra en silencio.**

    Y se comprueba **antes** de escribir nada, que es lo que importa: `correcciones.corregir` guarda
    en el mismo momento en que se la llama, así que una comprobación hecha después dejaría la
    corrección aplicada y encima contestaría 422, como si no hubiera pasado nada. Se descubrió
    escribiendo esta misma puerta.
    """
    desconocidos = sorted({papel for papel in papeles if papel not in logica.PAPELES})
    if desconocidos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C6_ese_papel_no_existe", papeles=", ".join(desconocidos)),
        )
    return list(dict.fromkeys(papeles))



# --------------------------------------------------------------------------
# Las puertas: la lista, el alta y la revisión
# --------------------------------------------------------------------------


@router.get("", response_model=list[ContactoSalida])
def listar(
    db: Db,
    explotacion: ExplotacionActual,
    _usuario: UsuarioActual,
    q: str = Query(default="", max_length=120),
) -> list[dict]:
    """Los contactos de la finca, con sus papeles y cuántos nombres suyos hay escritos.

    El buscador **no distingue tildes ni mayúsculas** (`app/contactos.py`), y eso es a propósito: quien
    busca «jose» quiere encontrar a «José», y quien escribe con el pulgar en el móvil no pone tildes.
    Lo que **no** hace es juntar nada: buscar no fusiona fichas.
    """
    consulta = select(models.Contacto).where(
        models.Contacto.explotacion_id == explotacion.id
    )
    contactos = list(db.scalars(consulta.order_by(models.Contacto.nombre)))
    escritos = _los_escritos(db, explotacion.id)
    papeles_escritos = _lo_que_escribe_cada_papel(escritos)
    buscado = logica.clave_parecida(q)
    salida = []
    for contacto in contactos:
        if buscado and buscado not in logica.clave_parecida(contacto.nombre):
            continue
        salida.append(
            _pintar_contacto(
                contacto,
                papeles=_los_papeles(db, contacto),
                escritos=escritos,
                papeles_escritos=papeles_escritos,
            )
        )
    return salida


@router.post("", response_model=ContactoSalida, status_code=status.HTTP_201_CREATED)
def crear(
    datos: ContactoEntrada, db: Db, explotacion: ExplotacionActual, usuario: UsuarioActual
) -> dict:
    """Da de alta una ficha.

    **No se comprueba si ya hay una con el mismo nombre, y es a propósito.** El contrato pide que dos
    contactos con el mismo nombre **no se mezclen** (E5): dos hermanos pueden llamarse igual, y el
    programa tiene que poder apuntar a cada uno. Lo que impide el trabajo duplicado no es una regla de
    unicidad, es que el agricultor pueda enlazar el nombre que ya está escrito en vez de teclearlo.
    """
    nombre = logica.limpia(datos.nombre)
    if not nombre:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C7_un_contacto_necesita_nombre"),
        )
    contacto = models.Contacto(
        explotacion_id=explotacion.id,
        nombre=nombre,
        es_empresa=datos.es_empresa,
        nif=logica.limpia(datos.nif) or None,
        telefono=logica.limpia(datos.telefono) or None,
        correo=logica.limpia(datos.correo) or None,
        direccion=logica.limpia(datos.direccion) or None,
        localidad=logica.limpia(datos.localidad) or None,
        notas=logica.limpia(datos.notas) or None,
        origen=A_MANO,
    )
    papeles = _comprobar_los_papeles(datos.papeles)
    db.add(contacto)
    db.flush()
    _guardar_los_papeles(db, contacto, papeles)
    # **El alta deja rastro** (CRM-03, 11/10/2026). Es el requisito que la revisión del T11 tenía fichado
    # (`docs/REVISION_T11.md:364-368`): el contrato pide autor para toda entidad de negocio y una ficha se
    # podía apuntar sin que quedara quién. Se guarda con la **misma forma** que una corrección —`{campo:
    # [antes, ahora]}`, y en un alta el «antes» es nada—, para que la auditoría se lea igual venga de donde
    # venga. Los campos vacíos no se apuntan: un rastro lleno de `null` no dice nada.
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=contacto.id,
        accion="crear",
        datos={
            campo: [None, valor]
            for campo, valor in (
                ("nombre", contacto.nombre),
                ("es_empresa", contacto.es_empresa),
                ("nif", contacto.nif),
                ("telefono", contacto.telefono),
                ("correo", contacto.correo),
                ("direccion", contacto.direccion),
                ("localidad", contacto.localidad),
                ("notas", contacto.notas),
                # Y **qué papeles** se le pusieron: un proveedor que también es cliente se apunta aquí, y es
                # de las cosas que más se corrigen después.
                ("papeles", list(papeles) or None),
            )
            if valor not in (None, "")
        },
    )
    db.commit()
    db.refresh(contacto)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.post("/{contacto_id}/baja", response_model=ContactoSalida)
def dar_de_baja(
    contacto_id: int,
    datos: BajaDeUnContacto,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Deja de usarse, sin borrarlo**: el criterio (e) de CRM-03 (11/10/2026).

    El motivo por el que existe esta puerta y no vale con borrar la ficha: **el pasado sigue apuntándole**. Sus
    facturas, sus ventas y sus papeles no se van a ir, así que borrar la ficha las dejaría huérfanas —y borrar
    el pasado no es lo que el agricultor pide cuando dice «con este ya no trabajo»—.

    La vuelta (`/alta`) es la misma puerta al revés, y las dos **dejan traza**: quién lo hizo y, si lo escribió,
    por qué. Dar de baja **no** es una corrección de los datos (`correcciones.CAMPO_QUE_NO_SE_TOCA` lo tiene
    fuera a propósito): es una decisión, y va con **su propia acción** en la auditoría.

    **Reenviarla no apunta dos veces**: si ya está de baja, se contesta la ficha tal cual sin escribir nada. El
    agricultor toca dos veces con los guantes, y el programa no puede contar dos bajas donde hubo una.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    if not contacto.activo:
        return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))
    contacto.activo = False
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=contacto.id,
        accion="baja",
        datos={"activo": [True, False], "motivo": [None, logica.limpia(datos.motivo) or None]},
    )
    db.commit()
    db.refresh(contacto)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.post("/{contacto_id}/alta", response_model=ContactoSalida)
def volver_a_usarlo(
    contacto_id: int,
    datos: BajaDeUnContacto,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Vuelve a usarse** (11/10/2026): la misma puerta al revés, con su traza.

    Existe porque dar de baja no puede ser de un solo sentido: un proveedor con el que se dejó de trabajar
    vuelve, y volver a apuntarlo duplicaría su ficha —y sus facturas viejas apuntan a la de antes—.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    if contacto.activo:
        return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))
    contacto.activo = True
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=contacto.id,
        accion="alta",
        datos={"activo": [False, True], "motivo": [None, logica.limpia(datos.motivo) or None]},
    )
    db.commit()
    db.refresh(contacto)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


def _la_nota_de_esta_accion(db, explotacion_id: int, clave: str):
    """La nota que guardó esa acción, si ya se guardó. `None` si no hay ninguna.

    **Buscada por la clave y por la finca**, que es lo que hace que la clave de una finca no choque con la de otra.
    """
    if not clave:
        return None
    return db.scalar(
        select(models.NotaDeUnContacto).where(
            models.NotaDeUnContacto.explotacion_id == explotacion_id,
            models.NotaDeUnContacto.clave_de_reenvio == clave,
        )
    )


def _lo_que_contesta_una_accion_ya_guardada(ya, contacto, texto: str, db, explotacion) -> dict:
    """Lo que se contesta cuando esa acción **ya se había guardado** (13/10/2026, revisión).

    Se compara **la acción entera** —la nota, su contacto y su texto— y no solo la clave:

      - **Coincide**: es un reenvío legítimo (doble clic, respuesta perdida, reintento sin cobertura). Se contesta
        la ficha, con la nota que ya estaba, y **no se apunta otra**.
      - **No coincide**: llegó la misma clave con **otro texto** o en **otro contacto**. Entonces **409** y no se
        toca nada. Contestar «ya está» aquí sería dar por guardado algo que **no se guardó**: el agricultor editó
        lo que había escrito, la respuesta se había perdido, y su texto nuevo desaparecería sin que nadie se
        entere. El navegador conserva el borrador y lo explica; con eso, lo que escribió no se pierde.

    Se usa desde los dos caminos: el de la consulta previa y el de la colisión al guardar.
    """
    if ya.contacto_id == contacto.id and (ya.texto or "") == texto:
        return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=textos.mensaje("C7_la_accion_ya_se_guardo_de_otra_manera"),
    )


@router.post("/{contacto_id}/canales", response_model=ContactoSalida)
def apuntar_un_canal(
    contacto_id: int,
    datos: CanalDeUnContactoEntrada,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Apunta un teléfono, un correo o una dirección más** (Entrega 2, 13/10/2026).

    Los cuatro campos de siempre en la ficha **no se tocan**: esto es para los demás (el del almacén, el móvil de
    quien atiende, la dirección de entrega). Si nace como principal, el que lo era de su clase **deja de serlo en
    la misma transacción**.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    lo_suyo = _un_canal_guardable(datos)
    if datos.principal:
        _apartar_el_principal_de_su_clase(db, contacto, lo_suyo["clase"])
    canal = models.CanalDeUnContacto(
        explotacion_id=explotacion.id, contacto_id=contacto.id, principal=bool(datos.principal), **lo_suyo
    )
    db.add(canal)
    db.flush()
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=contacto.id,
        accion="canal_crear",
        datos={"clase": [None, canal.clase], "etiqueta": [None, canal.etiqueta]},
    )
    db.commit()
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.post("/{contacto_id}/canales/{canal_id}/principal", response_model=ContactoSalida)
def el_canal_principal(
    contacto_id: int,
    canal_id: int,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Elige cuál es el principal de su clase** (Entrega 2, 13/10/2026).

    Uno y solo uno por clase, y eso lo garantiza la base con un índice parcial: aquí se **aparta** al que lo era
    antes de poner al nuevo, en la misma transacción. Si ya era el principal, no se apunta nada —el agricultor toca
    dos veces con los guantes y el programa no puede contar dos cambios donde hubo uno—.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    canal = db.scalar(
        select(models.CanalDeUnContacto).where(
            models.CanalDeUnContacto.explotacion_id == explotacion.id,
            models.CanalDeUnContacto.contacto_id == contacto.id,
            models.CanalDeUnContacto.id == canal_id,
        )
    )
    if canal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=textos.mensaje("C7_no_existe"))
    if not canal.principal:
        _apartar_el_principal_de_su_clase(db, contacto, canal.clase)
        canal.principal = True
        correcciones.apuntar(
            db,
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
            entidad="contacto",
            entidad_id=contacto.id,
            accion="canal_principal",
            datos={"clase": [None, canal.clase], "canal_id": [None, canal.id]},
        )
        db.commit()
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.put("/{contacto_id}/canales/{canal_id}", response_model=ContactoSalida)
def corregir_un_canal(
    contacto_id: int,
    canal_id: int,
    datos: CanalDeUnContactoEntrada,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Corrige un canal sin perder lo que no se manda** (Entrega 2, 13/10/2026).

    La corrección es **parcial**: si el formulario solo manda el teléfono, la etiqueta **se queda como estaba**. Es
    lo que pide el encargo con estas palabras —*«evitar […] pérdida de datos al corregir»*— y en la práctica es la
    diferencia entre arreglar un número y borrar de paso cómo se llamaba ese número.

    **La clase no se cambia**: un teléfono no se convierte en una dirección. Si hay que cambiar de clase, se quita el
    canal y se apunta el otro, y así las dos cosas quedan en la auditoría.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    canal = _el_canal_de_la_ficha(db, explotacion.id, contacto.id, canal_id)
    antes = {
        "etiqueta": canal.etiqueta,
        "telefono": canal.telefono,
        "correo": canal.correo,
        "direccion": canal.direccion,
        "localidad": canal.localidad,
    }
    # **Solo lo que viene.** `None` en la entrada es «no lo mandes», no «bórralo»: para dejar una etiqueta en blanco
    # se manda vacía, y eso es una decisión del formulario, no un descuido de la puerta.
    for campo in ("telefono", "correo", "direccion", "localidad", "etiqueta"):
        if getattr(datos, campo) is not None:
            setattr(canal, campo, logica.limpia(getattr(datos, campo)) or None)
    if not any(getattr(canal, campo) for campo in ("telefono", "correo", "direccion")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C7_un_canal_necesita_algo_escrito"),
        )
    # Los cambios, para la auditoría. **Se arma aparte y no dentro de la llamada**: mezclar claves escritas a mano
    # con una comprensión en el mismo diccionario **no es Python válido**, y rompió el fichero entero cuando lo
    # intenté (lo cazó la comprobación de arranque, que es para lo que está).
    los_cambios = {"etiqueta": [antes["etiqueta"], canal.etiqueta]}
    for campo in ("telefono", "correo", "direccion", "localidad"):
        if antes[campo] != getattr(canal, campo):
            los_cambios[campo] = [antes[campo], getattr(canal, campo)]
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=contacto.id,
        accion="canal_corregir",
        datos=los_cambios,
    )
    db.commit()
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.delete("/{contacto_id}/canales/{canal_id}", response_model=ContactoSalida)
def quitar_un_canal(
    contacto_id: int,
    canal_id: int,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Quita un canal** (Entrega 2, 13/10/2026).

    Se borra la fila —un teléfono que ya no es de nadie no tiene nada que conservar, y **no es un documento**—, pero
    **la auditoría se queda**: se apunta qué se quitó, con su etiqueta y su valor, así que dentro de un año se puede
    saber que existió. Eso es lo que pide el encargo al decir *«conservar los registros antiguos»*: el dato en sí no
    vale, el rastro sí.

    **Y si el que se quita era el principal, otro de su clase pasa a serlo** (el más antiguo de los que quedan),
    porque una clase con valores no puede quedarse sin ninguno: la pantalla enseñaría el teléfono sin decir cuál
    usar. Es la otra mitad de la regla del principal, y por eso está escrita aquí.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    canal = _el_canal_de_la_ficha(db, explotacion.id, contacto.id, canal_id)
    era_principal = canal.principal
    clase = canal.clase
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=contacto.id,
        accion="canal_quitar",
        datos={
            "clase": [clase, None],
            "etiqueta": [canal.etiqueta, None],
            "valor": [canal.telefono or canal.correo or canal.direccion, None],
        },
    )
    db.delete(canal)
    db.flush()
    if era_principal:
        el_siguiente = db.scalar(
            select(models.CanalDeUnContacto)
            .where(
                models.CanalDeUnContacto.explotacion_id == explotacion.id,
                models.CanalDeUnContacto.contacto_id == contacto.id,
                models.CanalDeUnContacto.clase == clase,
            )
            .order_by(models.CanalDeUnContacto.id)
            .limit(1)
        )
        if el_siguiente is not None:
            el_siguiente.principal = True
    db.commit()
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.post("/{contacto_id}/tareas", response_model=ContactoSalida)
def apuntar_una_tarea(
    contacto_id: int,
    datos: EntradaDeUnaTarea,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Apunta una próxima acción con este contacto** (Entrega 3, 13/10/2026).

    Lo único que se exige es **saber qué hay que hacer** (el título). El responsable, la descripción y el día son
    opcionales de verdad: una tarea **sin fecha** es una tarea («llamar al del pienso algún día»), y obligarla a
    tener fecha sería inventarla.

    **Reenviar no duplica**: si viene la misma clave de reenvío, se devuelve la ficha con la tarea que ya había, sin
    apuntar otra ni dejar dos trazas. Es el mismo patrón que las notas y los cobros.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    titulo = logica.limpia(datos.titulo)
    if not titulo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C7_una_tarea_necesita_titulo"),
        )
    if datos.clave_de_reenvio:
        la_misma = db.scalar(
            select(models.Tarea).where(
                models.Tarea.explotacion_id == explotacion.id,
                models.Tarea.clave_de_reenvio == datos.clave_de_reenvio,
            )
        )
        if la_misma is not None:
            # **La acción ya estaba hecha**: se devuelve lo que hay, sin apuntar nada nuevo.
            return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))
    tarea = models.Tarea(
        explotacion_id=explotacion.id,
        contacto_id=contacto.id,
        titulo=titulo,
        descripcion=logica.limpia(datos.descripcion) or None,
        responsable=logica.limpia(datos.responsable) or None,
        fecha_prevista=datos.fecha_prevista,
        estado=models.Tarea.PENDIENTE,
        clave_de_reenvio=datos.clave_de_reenvio,
    )
    db.add(tarea)
    db.flush()
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=contacto.id,
        accion="tarea_crear",
        datos={"titulo": [None, tarea.titulo], "fecha_prevista": [None, str(tarea.fecha_prevista or "")]},
    )
    db.commit()
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.get("/{contacto_id}/saldo", response_model=SaldoDeUnContacto)
def el_saldo(
    contacto_id: int,
    db: Db,
    explotacion: ExplotacionActual,
    _usuario: UsuarioActual,
) -> dict:
    """**Cuánto nos debe y cuánto le debemos**, con los documentos que lo explican (13/10/2026).

    Se apoya en `app/saldos.py`, que a su vez usa **la regla única del dinero** (`app/servicios.py`): aquí no se
    suma dinero por cuenta propia.

    **Y se busca el contacto con `_el_contacto_de_la_finca`**, que es lo que hace que el saldo de un contacto de
    otra finca **no se pueda ver** ni sabiendo su identificador: contesta 404, igual que la ficha.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    return saldos.el_saldo_de_un_contacto(db, explotacion_id=explotacion.id, contacto_id=contacto.id)


@router.post("/{contacto_id}/notas", response_model=ContactoSalida)
def apuntar_una_nota(
    contacto_id: int,
    datos: NotaDeUnContactoEntrada,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Apunta una nota en la ficha, con quién la escribe y cuándo** (CRM-03, criterio (f), 11/10/2026).

    Las notas **no se corrigen: se apuntan**. Son el diario de la ficha, así que si algo se escribió mal se
    escribe otra nota diciéndolo —y así queda lo de antes, que es lo que un diario tiene que hacer—.

    **El autor lo pone el servidor**, de su vale: aceptarlo del navegador sería poder firmar cosas que no ha
    escrito uno.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    texto = logica.limpia(datos.texto)
    if not texto:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C7_una_nota_necesita_texto"),
        )
    # **El reenvío seguro, con la identidad COMPLETA de la acción** (13/10/2026, revisión).
    #
    # La clave sola no basta: identifica **una acción**, y una acción es *esta nota, en este contacto, con este
    # texto*. Si llega la misma clave con **otro texto** o en **otro contacto**, no es un reenvío: es que el
    # agricultor editó lo que había escrito (o el navegador cruzó dos formularios), y contestar «ya está» sería
    # dar por guardado algo que **no se guardó** —pérdida silenciosa—. En ese caso se contesta **409** y no se
    # toca nada: el navegador conserva el borrador y lo explica.
    clave = (datos.clave_de_reenvio or "").strip()
    if clave:
        ya = _la_nota_de_esta_accion(db, explotacion.id, clave)
        if ya is not None:
            return _lo_que_contesta_una_accion_ya_guardada(ya, contacto, texto, db, explotacion)

    db.add(
        models.NotaDeUnContacto(
            explotacion_id=explotacion.id,
            contacto_id=contacto.id,
            usuario_id=usuario.id,
            texto=texto,
            clave_de_reenvio=clave or None,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # **Y la colisión, que es de verdad** (13/10/2026, revisión): la consulta de arriba y el guardado son dos
        # operaciones, así que dos peticiones simultáneas pueden encontrar la clave libre las dos. El índice
        # único impide duplicar la nota, pero **alguien tiene que recoger el choque**: se deshace lo intentado, se
        # lee lo que quedó y se contesta como corresponde. Sin esto, el agricultor vería un error del servidor
        # (500) y no sabría si su nota se guardó.
        db.rollback()
        ya = _la_nota_de_esta_accion(db, explotacion.id, clave)
        if ya is None:
            raise
        return _lo_que_contesta_una_accion_ya_guardada(ya, contacto, texto, db, explotacion)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))



@router.get("/escritos", response_model=list[NombreEscrito])
def listar_los_escritos(
    db: Db,
    explotacion: ExplotacionActual,
    _usuario: UsuarioActual,
    q: str = Query(default="", max_length=120),
    sin_enlazar: bool = Query(default=False),
) -> list[dict]:
    """Los nombres escritos a mano que se pueden enlazar, con buscador.

    `sin_enlazar=true` deja solo los que no tienen dueño: es lo que necesita la pantalla de enlazar,
    porque ofrecer un botón para enlazar algo que ya está enlazado daría un error sin explicación.
    """
    escritos = _los_escritos(db, explotacion.id)
    buscado = logica.clave_parecida(q)
    salida = []
    for escrito in escritos:
        if sin_enlazar and escrito["enlace_id"]:
            continue
        if buscado and buscado not in logica.clave_parecida(escrito["texto"]):
            continue
        salida.append(escrito)
    return salida


@router.get("/migracion", response_model=RevisionDeLosNombres)
def la_revision(db: Db, explotacion: ExplotacionActual, _usuario: UsuarioActual) -> dict:
    """**Lo que se le propone al agricultor**, calculado ahora y sin escribir nada.

    Lo que ya está enlazado no entra en la propuesta: ya tiene dueño. Y lo que no se puede juntar sale
    igualmente, con `segura: false` y su motivo, porque **callarlo sería lo peor**: el agricultor
    tiene que saber que esas dos fichas que se parecen existen y que el programa no las ha tocado.
    """
    escritos = _los_escritos(db, explotacion.id)
    libres = [uno for uno in escritos if not uno["enlace_id"]]
    propuestas = logica.proponer([_como_escrito(uno) for uno in libres])
    return {
        "resumen": logica.resumen_de_la_propuesta(propuestas),
        "propuestas": [
            {
                "clave": _la_clave(propuesta),
                "nombre": propuesta.nombre,
                "segura": propuesta.segura,
                "motivo": propuesta.motivo,
                "papeles": propuesta.papeles,
                "nombres": propuesta.nombres,
                "nifs": propuesta.nifs,
                "pareja": list(propuesta.pareja or ()),
                "escritos": [
                    _el_escrito_suelto(escrito, libres) for escrito in propuesta.escritos
                ],
            }
            for propuesta in propuestas
        ],
        "ya_enlazados": len(escritos) - len(libres),
        "total_escritos": len(escritos),
        # **Si hay algo que deshacer lo dice el servidor**, y no lo adivina la pantalla: una ficha de la
        # migración que el agricultor ha corregido **no se deshace** (es suya), y eso solo se sabe aquí.
        "se_puede_deshacer": _hay_algo_de_la_migracion(db, explotacion.id),
    }


def _hay_algo_de_la_migracion(db, explotacion_id: int) -> bool:
    """¿Queda en esta finca alguna ficha que apuntó la migración y todavía se pueda quitar?"""
    for contacto in db.scalars(
        select(models.Contacto).where(
            models.Contacto.explotacion_id == explotacion_id,
            models.Contacto.origen == DE_LA_MIGRACION,
        )
    ):
        if not contacto.editado_a_mano:
            return True
    return bool(
        db.scalars(
            select(models.EnlaceDeContacto).where(
                models.EnlaceDeContacto.explotacion_id == explotacion_id,
                models.EnlaceDeContacto.origen == DE_LA_MIGRACION,
            )
        ).first()
    )


def _como_escrito(escrito: dict) -> logica.Escrito:
    """Pasa lo leído de la base a lo que entiende la lógica pura (`app/contactos.py`)."""
    return logica.Escrito(
        tabla=escrito["tabla"],
        campo=escrito["campo"],
        registro_id=escrito["registro_id"],
        texto=escrito["texto"],
        nif=escrito["nif"],
        papel=escrito["papel"],
        clave=escrito["clave"],
        referencia=tuple(escrito["referencia"]),
    )


def _el_escrito_suelto(suyo: logica.Escrito, todos: list[dict]) -> dict:
    """Vuelve a poner el escrito en su forma de salida, con lo que se leyó de su fila."""
    for escrito in todos:
        if (
            escrito["tabla"] == suyo.tabla
            and escrito["campo"] == suyo.campo
            and escrito["registro_id"] == suyo.registro_id
        ):
            return escrito
    return {
        "tabla": suyo.tabla,
        "campo": suyo.campo,
        "registro_id": suyo.registro_id,
        "texto": suyo.texto,
        "nif": suyo.nif,
        "papel": suyo.papel,
        "clave": suyo.clave,
        "referencia": list(suyo.referencia),
    }


def _la_clave(propuesta: logica.Propuesta) -> str:
    """La clave con la que el agricultor confirma una propuesta.

    Es la huella de **los textos escritos que la forman, con lo que dicen**: la tabla, el campo, el
    identificador **y el texto tal y como se enseña**.

    Las dos mitades hacen falta, y las dos vienen de un fallo medido:

      · **Dónde están** (tabla, campo, identificador), para que una factura nueva en esa misma ficha
        cambie la clave y el servidor lo diga en vez de apuntar algo distinto de lo que se le enseñó.
      · **Lo que dicen** (el texto), porque **sin esto se podía confirmar algo distinto de lo
        enseñado**: si entre mirar y confirmar el papel se corregía de una forma que no cambia la
        agrupación —pasar «Cooperativa X» a «COOPERATIVA X»—, la clave seguía valiendo y se apuntaba
        una ficha con un nombre que el agricultor no había visto. Lo encontró la revisión
        independiente: el §3.6 del documento promete «o se apunta lo que se enseñó, o no se apunta», y
        sin el texto en la huella esa promesa no se cumplía.

    Se usa el texto **tal y como se enseña** (ya sin espacios de más, que es lo que devuelve
    `_los_escritos`): lo que tiene que cubrir la clave es lo que el agricultor ha visto en la
    pantalla, y eso es exactamente lo que se guarda aquí.
    """
    trozos = sorted(
        f"{escrito.tabla}:{escrito.campo}:{escrito.registro_id}:{escrito.texto}"
        for escrito in propuesta.escritos
    )
    return hashlib.sha256("|".join(trozos).encode("utf-8")).hexdigest()[:16]


@router.post("/migracion/aplicar", response_model=ResultadoDeLaMigracion)
def aplicar_la_migracion(
    datos: ConfirmacionDeLaMigracion,
    db: Db,
    explotacion: ExplotacionActual,
    # Se llamaba `_usuario` porque **no se usaba**; desde el 11/10/2026 sí: la migración deja rastro con
    # quién la hizo, que es el requisito que faltaba. Un guion bajo delante de un parámetro que se usa sería
    # decir que no se usa.
    usuario: UsuarioActual,
) -> dict:
    """**Apunta las fichas que el agricultor confirma**, y solo esas.

    Cuatro comprobaciones antes de escribir una sola fila, y las cuatro existen por un fallo que ya ha
    dolido en este proyecto:

      1. **La clave tiene que existir** entre las propuestas de ahora. Si no está, la propuesta ha
         cambiado (o nunca existió) y se contesta 409 sin apuntar nada.
      2. **La propuesta tiene que ser segura.** Si alguien manda la clave de un grupo que «se parece»,
         que tiene dos NIF o que comparte NIF con nombres distintos, se contesta 409: el «no se
         fusiona» no puede vivir solo en la pantalla.
      3. **Reenviar el mismo comando devuelve su resultado.** El contrato lo pide con todas las letras
         (§2: «Reenviar el mismo comando devuelve su resultado; no crea otro movimiento»), y había un
         camino de verdad: **el botón de apuntar no se deshabilitaba mientras enviaba**, así que un
         doble toque (con guantes, con el móvil lento) mandaba la misma confirmación dos veces. La
         segunda contestaba 409 «la lista de nombres ha cambiado» — y era mentira: lo que había
         cambiado era que **el propio servidor** acababa de enlazar esos nombres. Ahora, si todos los
         textos de esa propuesta ya están enlazados con **la misma** ficha, se devuelve el resultado
         de aquella vez y se dice que ya estaba apuntado. Es la misma idea que la clave de reenvío del
         almacén.
      4. **Nada de apuntar media petición.** Las comprobaciones se hacen todas antes de crear nada: o
         entran todas las fichas confirmadas, o no entra ninguna.

    **Y la propuesta se recalcula sobre TODOS los textos escritos, no solo sobre los que están
    libres.** Es lo que hace posible el reenvío: en cuanto el servidor enlaza un nombre, ese nombre
    deja de estar libre, y la propuesta de la que formaba parte desaparecería —con su clave— si solo
    se miraran los libres. Mirando todos, la misma propuesta se vuelve a encontrar y se puede
    contestar «esto ya está apuntado» en vez de «la lista ha cambiado».
    """
    escritos = _los_escritos(db, explotacion.id)
    propuestas = {
        _la_clave(propuesta): propuesta
        for propuesta in logica.proponer([_como_escrito(uno) for uno in escritos])
    }
    por_sitio = {
        (uno["tabla"], uno["campo"], uno["registro_id"]): uno for uno in escritos
    }
    pedidas = list(dict.fromkeys(datos.claves))
    elegidas: list[logica.Propuesta] = []
    repetidas: list[tuple[logica.Propuesta, models.Contacto]] = []
    for clave in pedidas:
        propuesta = propuestas.get(clave)
        if propuesta is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=textos.mensaje("C4_la_propuesta_ha_cambiado"),
            )
        if not propuesta.segura:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=textos.mensaje("C3_eso_no_se_puede_juntar_solo"),
            )
        # ¿Esta propuesta ya se apuntó? Solo cuenta como reenvío si **todos** sus textos están
        # enlazados con **la misma** ficha. Si están repartidos entre dos fichas, o unos sí y otros
        # no, entonces sí que ha cambiado algo de verdad y se dice con el 409 de siempre.
        #
        # **Ojo con el `None`, que es el fallo que tuvo esta comprobación antes de estar escrita así**:
        # un texto sin enlazar trae `contacto_id = None`, y un conjunto `{None}` es verdadero en
        # Python, así que la primera versión daba 409 en el **primer** envío —el de una propuesta sin
        # enlazar todavía—. Por eso se mira «todos y cada uno con dueño», y no «hay algún dueño».
        suyos = [
            por_sitio.get((uno.tabla, uno.campo, uno.registro_id)) for uno in propuesta.escritos
        ]
        enlazados = [uno["contacto_id"] for uno in suyos if uno and uno["contacto_id"]]
        duenos = set(enlazados)
        if len(enlazados) == len(propuesta.escritos) and len(duenos) == 1:
            contacto = db.get(models.Contacto, duenos.pop())
            if contacto is not None:
                repetidas.append((propuesta, contacto))
                continue
        if duenos:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=textos.mensaje("C4_la_propuesta_ha_cambiado"),
            )
        elegidas.append(propuesta)
    if not elegidas and not repetidas:
        return {
            "fichas": 0,
            "enlaces": 0,
            "textos_tocados": 0,
            "nombres": [],
            "avisos": [textos.mensaje("C8_no_has_elegido_ninguna")],
            "contactos": [],
        }

    fichas: list[int] = []
    nombres: list[str] = []
    enlaces = 0
    for propuesta in elegidas:
        contacto = models.Contacto(
            explotacion_id=explotacion.id,
            nombre=propuesta.nombre,
            # **El NIF se copia de los papeles, y solo cuando es el mismo en todos.** Si hubiera dos,
            # esta propuesta no sería segura y no habría llegado hasta aquí.
            nif=propuesta.nifs[0] if len(propuesta.nifs) == 1 else None,
            origen=DE_LA_MIGRACION,
        )
        db.add(contacto)
        db.flush()
        for papel in propuesta.papeles:
            db.add(
                models.PapelDeUnContacto(
                    explotacion_id=explotacion.id, contacto_id=contacto.id, papel=papel
                )
            )
        for escrito in propuesta.escritos:
            db.add(
                models.EnlaceDeContacto(
                    explotacion_id=explotacion.id,
                    contacto_id=contacto.id,
                    tabla=escrito.tabla,
                    campo=escrito.campo,
                    registro_id=escrito.registro_id,
                    # **Lo que decía el papel el día del enlace.** Es lo que permite decir después
                    # «ojo, ahí pone otra cosa», sin haber tocado nunca el texto.
                    nombre_de_entonces=escrito.texto,
                    origen=DE_LA_MIGRACION,
                )
            )
            enlaces += 1
        fichas.append(contacto.id)
        nombres.append(contacto.nombre)
    # Y las que ya estaban apuntadas: **el mismo resultado que la primera vez**, para que reenviar sea
    # inofensivo, más el aviso de que no se ha apuntado dos veces.
    avisos: list[str] = []
    for propuesta, contacto in repetidas:
        fichas.append(contacto.id)
        nombres.append(contacto.nombre)
        enlaces += len(propuesta.escritos)
        avisos.append(textos.mensaje("C11_ya_estaba_apuntada", nombre=contacto.nombre))
    # **Y la migración deja rastro** (CRM-03, 11/10/2026), que es la otra mitad del requisito pendiente del
    # T11: hasta hoy se podía meter de golpe todo el cuaderno de nombres en las fichas y no quedaba quién lo
    # hizo ni cuántas. Va **una sola fila** con el resumen —y no una por ficha, que ya la deja el alta de cada
    # una—: lo que hay que poder contestar es «¿quién apuntó estas veinte de golpe?».
    correcciones.apuntar(
        db,
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
        entidad="contacto",
        entidad_id=None,
        accion="migrar_nombres",
        datos={
            "fichas": [None, len(fichas)],
            "enlaces": [None, enlaces],
            "textos_tocados": [None, 0],
        },
    )
    db.commit()
    return {
        "fichas": len(fichas),
        "enlaces": enlaces,
        "textos_tocados": 0,
        "nombres": nombres,
        "avisos": avisos,
        "contactos": fichas,
    }


@router.post("/migracion/deshacer", response_model=DeshacerLaMigracion)
def deshacer_la_migracion(
    db: Db, explotacion: ExplotacionActual, usuario: UsuarioActual
) -> dict:
    """**Vuelve atrás**: quita lo que creó la migración y **deja lo que el agricultor ha hecho suyo**.

    Las dos reglas, y la segunda es la que importa:

      1. Se borran **los enlaces de la migración** (los que apuntan a un texto escrito). El texto del
         documento **no se toca**: se queda exactamente como estaba, que es la promesa del ticket.
      2. Una ficha que creó la migración se borra **solo si no le queda ningún enlace y nadie la ha
         editado**. Si el agricultor le puso el teléfono, le quitó un papel o le enlazó otra cosa,
         esa ficha **es suya** y se queda, con su nombre, en la lista de `se_quedan` y su motivo
         escrito. Volver atrás no puede llevarse trabajo suyo.
    """
    enlaces_de_la_migracion = list(
        db.scalars(
            select(models.EnlaceDeContacto).where(
                models.EnlaceDeContacto.explotacion_id == explotacion.id,
                models.EnlaceDeContacto.origen == DE_LA_MIGRACION,
            )
        )
    )
    quitados = len(enlaces_de_la_migracion)
    for enlace in enlaces_de_la_migracion:
        db.delete(enlace)
    db.flush()

    vivas = {
        enlace.contacto_id
        for enlace in db.scalars(
            select(models.EnlaceDeContacto).where(
                models.EnlaceDeContacto.explotacion_id == explotacion.id
            )
        )
    }
    se_quedan: list[str] = []
    borradas = 0
    for contacto in list(
        db.scalars(
            select(models.Contacto).where(
                models.Contacto.explotacion_id == explotacion.id,
                models.Contacto.origen == DE_LA_MIGRACION,
            )
        )
    ):
        if contacto.id in vivas or contacto.editado_a_mano:
            se_quedan.append(textos.mensaje("C9_esta_ficha_es_tuya", nombre=contacto.nombre))
            continue
        for papel in list(
            db.scalars(
                select(models.PapelDeUnContacto).where(
                    models.PapelDeUnContacto.contacto_id == contacto.id
                )
            )
        ):
            db.delete(papel)
        # **El vaciado se hace antes de borrar la ficha, y no de una vez al final.** La base tiene una
        # clave ajena de los papeles al contacto, y aunque SQLAlchemy ordena los borrados por
        # dependencias, dejarlo explícito es lo que hace que esto no dependa de cómo ordene otro día.
        # Se descubrió con un «FOREIGN KEY constraint failed» en la prueba de deshacer.
        db.flush()
        # Con auditoría, como todo lo que se borra: la ficha desaparece y el programa sabe que
        # existió. Es la misma puerta que usan los apuntes (`correcciones.borrar`).
        correcciones.borrar(
            db,
            registro=contacto,
            entidad="contacto",
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
        )
        borradas += 1
    db.commit()
    return {
        "fichas": borradas,
        "enlaces": quitados,
        "se_quedan": se_quedan,
        "textos_tocados": 0,
    }


# --------------------------------------------------------------------------
# Una ficha: leerla, corregirla, borrarla, sus papeles y sus enlaces
# --------------------------------------------------------------------------


@router.get("/{contacto_id}", response_model=FichaDelContacto)
def leer(
    contacto_id: int, db: Db, explotacion: ExplotacionActual, _usuario: UsuarioActual
) -> dict:
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.put("/{contacto_id}", response_model=FichaDelContacto)
def corregir(
    contacto_id: int,
    datos: ContactoEntrada,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """Corrige la ficha, **dejando en la auditoría lo que decía antes**.

    Y de ahí sale una cosa que el contrato pide con todas las letras: **cambiar el nombre de un
    contacto no cambia ninguna factura**. El nombre escrito en el papel es del papel, no de la ficha;
    lo único que cambia es a quién apunta el enlace. Hay una prueba que lo comprueba leyendo el texto
    de la factura antes y después.

    La ficha queda marcada como `editado_a_mano`, y eso es lo que impide que deshacer la migración se
    lleve por delante una ficha que el agricultor ya ha hecho suya.

    **Y los papeles solo se tocan si la petición habla de ellos** (05/10/2026). Ver `_papeles_que_se_quedan`.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    nombre = logica.limpia(datos.nombre)
    if not nombre:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C7_un_contacto_necesita_nombre"),
        )
    preparado = models.Contacto(
        explotacion_id=explotacion.id,
        nombre=nombre,
        es_empresa=datos.es_empresa,
        nif=logica.limpia(datos.nif) or None,
        telefono=logica.limpia(datos.telefono) or None,
        correo=logica.limpia(datos.correo) or None,
        direccion=logica.limpia(datos.direccion) or None,
        localidad=logica.limpia(datos.localidad) or None,
        notas=logica.limpia(datos.notas) or None,
        origen=contacto.origen,
        editado_a_mano=True,
    )
    # `correcciones.corregir` copia campo a campo y apunta en la auditoría los que cambian. Se le pasa
    # el estado de la migración ya puesto para que **corregir no convierta una ficha de la migración en
    # una suya**: eso lo decide `editado_a_mano`, que va a `True`.
    correcciones.corregir(
        db,
        guardado=contacto,
        preparado=preparado,
        entidad="contacto",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    _papeles_que_se_quedan(db, contacto, datos)
    db.commit()
    db.refresh(contacto)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.delete("/{contacto_id}", status_code=status.HTTP_200_OK)
def borrar(
    contacto_id: int, db: Db, explotacion: ExplotacionActual, usuario: UsuarioActual
) -> dict:
    """Borra la ficha, con sus papeles y sus enlaces, y **sin tocar ningún texto escrito**.

    Lo que se va es la ficha, no el nombre: las facturas, las ventas y los análisis siguen diciendo
    exactamente lo que decían, y esos nombres vuelven a aparecer en la pantalla de enlazar para que el
    agricultor pueda darles dueño otra vez. Borrar una ficha equivocada no puede llevarse por delante
    ni un dato del cuaderno, y por eso se dice en la respuesta (`textos_tocados: 0`).
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    for enlace in list(
        db.scalars(
            select(models.EnlaceDeContacto).where(
                models.EnlaceDeContacto.explotacion_id == explotacion.id,
                models.EnlaceDeContacto.contacto_id == contacto.id,
            )
        )
    ):
        db.delete(enlace)
    for papel in list(
        db.scalars(
            select(models.PapelDeUnContacto).where(
                models.PapelDeUnContacto.contacto_id == contacto.id
            )
        )
    ):
        db.delete(papel)
    # El vaciado, antes de borrar la ficha (ver el mismo cuidado en `deshacer_la_migracion`).
    db.flush()
    correcciones.borrar(
        db,
        registro=contacto,
        entidad="contacto",
        explotacion_id=explotacion.id,
        usuario_id=usuario.id,
    )
    return {"hecho": True, "textos_tocados": 0}


@router.post("/{contacto_id}/papeles", response_model=FichaDelContacto)
def marcar_un_papel(
    contacto_id: int,
    datos: PapelEntrada,
    db: Db,
    explotacion: ExplotacionActual,
    _usuario: UsuarioActual,
) -> dict:
    """Pone o quita **un** papel, sin tocar los demás.

    Va aparte de la corrección de la ficha por un motivo práctico: en la pantalla los papeles son
    botones que se marcan y se desmarcan de uno en uno, y mandar la ficha entera para marcar un papel
    obligaría a leer los campos de texto del formulario, que es justo donde este programa ha perdido
    datos más veces.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    if datos.papel not in logica.PAPELES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=textos.mensaje("C6_ese_papel_no_existe", papeles=datos.papel),
        )
    papeles = _los_papeles(db, contacto)
    if datos.puesto and datos.papel not in papeles:
        papeles.append(datos.papel)
    if not datos.puesto and datos.papel in papeles:
        papeles.remove(datos.papel)
    _guardar_los_papeles(db, contacto, papeles)
    contacto.editado_a_mano = True
    db.commit()
    db.refresh(contacto)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.post("/{contacto_id}/enlaces", response_model=FichaDelContacto)
def enlazar(
    contacto_id: int,
    datos: EnlaceEntrada,
    db: Db,
    explotacion: ExplotacionActual,
    _usuario: UsuarioActual,
) -> dict:
    """Enlaza un nombre escrito con esta ficha. **El texto no se toca: se lee y se guarda lo que dice.**

    Las cuatro cosas que se comprueban, y por qué cada una:

      1. **La puerta existe** (`contactos.ENLACES`): si no, 404. Por aquí entra un nombre de tabla del
         navegador y no puede acabar dentro de una consulta.
      2. **El documento es de esta finca**: si no, 404 (y no 403, como todo).
      3. **El documento tiene un nombre escrito**: enlazar un hueco no es enlazar nada, y se dice.
      4. **Ese texto no está ya enlazado**: si lo está, 409 con el nombre de la ficha que lo tiene. Un
         texto con dos dueños serían dos verdades sobre el mismo papel.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    campo = logica.el_campo(datos.tabla, datos.campo)
    if campo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=textos.mensaje("C2_eso_no_se_puede_enlazar")
        )
    modelo = _el_modelo(campo.tabla)
    fila = db.get(modelo, datos.registro_id) if modelo else None
    if fila is None or getattr(fila, "explotacion_id", None) != explotacion.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    texto = _el_texto_escrito(fila, campo)
    if not texto:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=textos.mensaje("C5_ahi_no_hay_nombre")
        )
    ya = db.scalars(
        select(models.EnlaceDeContacto).where(
            models.EnlaceDeContacto.explotacion_id == explotacion.id,
            models.EnlaceDeContacto.tabla == campo.tabla,
            models.EnlaceDeContacto.campo == campo.campo,
            models.EnlaceDeContacto.registro_id == datos.registro_id,
        )
    ).first()
    if ya is not None:
        dueno = db.get(models.Contacto, ya.contacto_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=textos.mensaje(
                "C10_ese_nombre_ya_tiene_dueno", nombre=(dueno.nombre if dueno else "")
            ),
        )
    db.add(
        models.EnlaceDeContacto(
            explotacion_id=explotacion.id,
            contacto_id=contacto.id,
            tabla=campo.tabla,
            campo=campo.campo,
            registro_id=datos.registro_id,
            nombre_de_entonces=texto,
            origen=A_MANO,
        )
    )
    contacto.editado_a_mano = True
    db.commit()
    db.refresh(contacto)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))


@router.delete("/{contacto_id}/enlaces/{enlace_id}", response_model=FichaDelContacto)
def quitar_el_enlace(
    contacto_id: int,
    enlace_id: int,
    db: Db,
    explotacion: ExplotacionActual,
    _usuario: UsuarioActual,
) -> dict:
    """Quita el vínculo. **El nombre escrito se queda donde estaba**, con sus letras.

    Es la mitad de la promesa del ticket, y por eso está escrita aquí: quitar un vínculo no es borrar
    un dato, es dejar de decir a quién apunta. La factura sigue diciendo «Cooperativa Agrícola de
    Peñaranda» después de desenlazarla, exactamente igual que antes de enlazarla.
    """
    contacto = _el_contacto_de_la_finca(db, explotacion.id, contacto_id)
    enlace = db.get(models.EnlaceDeContacto, enlace_id)
    if (
        enlace is None
        or enlace.explotacion_id != explotacion.id
        or enlace.contacto_id != contacto.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Eso no está en tu cuaderno."
        )
    db.delete(enlace)
    contacto.editado_a_mano = True
    db.commit()
    db.refresh(contacto)
    return _la_ficha(db, contacto, _los_escritos(db, explotacion.id))
