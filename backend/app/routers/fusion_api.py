"""La vista previa de una fusión de dos fichas (Entrega 5, 14/10/2026).

**Esto es la mitad que se puede hacer sin riesgo**: mirar y contar lo que hay en las dos fichas, y decir **qué
colisiones** aparecerían al juntarlas. No mueve ni una fila.

POR QUÉ ES UNA PUERTA APARTE. El encargo pide, para la fusión: «Elegir origen y destino», «Mostrar vista previa de
datos, documentos, notas y tareas» y «Resolver conflictos **explícitamente**». Lo tercero es lo que hace falta aquí:
una fusión no puede decidir por su cuenta qué se hace cuando las dos fichas tienen un papel igual, o cuando las dos
tienen canal principal del mismo tipo, o cuando las dos tienen notas **en el campo de texto único de la ficha** (que
no es la tabla de notas, y por eso no hay sitio para las dos). Eso se ve aquí, y el humano decide.

LO QUE SE MIRA, Y DE DÓNDE SALE. Las once tablas que llevan `contacto_id` están contadas en
`FUSION-INVENTARIO.md`, que se hizo midiendo el esquema real: seis del dinero (`ventas_de_cosecha`,
`facturas_emitidas`, `cobros`, `gastos`, `inversiones_de_la_finca` y `pagos_de_gasto`) y cinco que cuelgan de la ficha
(`papeles_de_un_contacto`, `enlaces_de_contacto`, `canales_de_un_contacto`, `tareas` y `notas_de_un_contacto`).
**Ninguna de las once tiene `ON DELETE`**: lo que se olvide al fusionar no lo avisa la base.

Y EL DINERO: los **importes** solo salen con la capacidad económica (`PuedeVerLoEconomico` lo comprueba la puerta del
saldo, y aquí se pregunta lo mismo). Sin ella, la vista previa dice **cuántos documentos** hay de cada clase —que no
es un importe— y **no manda ninguna cifra**. El contrato: «sin permiso económico: no aparecen importes ni documentos
restringidos».
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from .. import accesos, models, saldos, textos
from ..deps import Db, ExplotacionActual, UsuarioActual

router = APIRouter(prefix="/api/contactos", tags=["contactos"])


# **Las once tablas, con su nombre y su modelo.** El orden es el de la fusión: primero el dinero, después lo que
# cuelga de la ficha. Se escriben a mano y no con un bucle sobre el modelo porque una fusión toca lo que toca, y eso
# se dice con nombres, no con una regla que mañana incluya una tabla que no se pensó.
LAS_DEL_DINERO: tuple[tuple[str, type], ...] = (
    ("ventas_de_cosecha", models.VentaDeCosecha),
    ("facturas_emitidas", models.FacturaEmitida),
    ("cobros", models.Cobro),
    ("gastos", models.Gasto),
    ("inversiones_de_la_finca", models.InversionDeLaFinca),
    ("pagos_de_gasto", models.PagoDeGasto),
)

LAS_QUE_CUELGAN: tuple[tuple[str, type], ...] = (
    ("papeles_de_un_contacto", models.PapelDeUnContacto),
    ("enlaces_de_contacto", models.EnlaceDeContacto),
    ("canales_de_un_contacto", models.CanalDeUnContacto),
    ("tareas", models.Tarea),
    ("notas_de_un_contacto", models.NotaDeUnContacto),
)


def _la_ficha(db: Db, explotacion_id: int, contacto_id: int) -> models.Contacto:
    """La ficha, **comprobando que es de esta finca**. Devolver 404 es intencionado: así no se puede ni saber que
    existe una ficha de otro (el mismo cuidado que `obtener_de_la_explotacion`)."""
    contacto = db.scalar(
        select(models.Contacto).where(
            models.Contacto.id == contacto_id,
            models.Contacto.explotacion_id == explotacion_id,
        )
    )
    if contacto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=textos.mensaje("C7_no_existe"))
    return contacto


def _cuantas(db: Db, modelo, contacto_id: int) -> int:
    return db.scalar(select(func.count()).select_from(modelo).where(modelo.contacto_id == contacto_id)) or 0


def _lo_que_tiene(db: Db, contacto: models.Contacto) -> dict:
    """Lo que cuelga de una ficha, **contado**. Los importes NO van aquí: van aparte y con permiso."""
    return {
        "dinero": {nombre: _cuantas(db, modelo, contacto.id) for nombre, modelo in LAS_DEL_DINERO},
        "cuelgan": {nombre: _cuantas(db, modelo, contacto.id) for nombre, modelo in LAS_QUE_CUELGAN},
        # **Los papeles y los canales, con su detalle**, porque son donde están las dos colisiones duras.
        "papeles": sorted(
            papel.papel
            for papel in db.scalars(
                select(models.PapelDeUnContacto).where(models.PapelDeUnContacto.contacto_id == contacto.id)
            )
        ),
        "canales_principales": {
            canal.clase: canal.etiqueta
            for canal in db.scalars(
                select(models.CanalDeUnContacto).where(
                    models.CanalDeUnContacto.contacto_id == contacto.id,
                    models.CanalDeUnContacto.principal.is_(True),
                )
            )
        },
        # **Sus notas escritas**: el campo de texto de la ficha. Se dice si tiene o no, porque es donde se pierde.
        "tiene_sus_notas_escritas": bool((contacto.notas or "").strip()),
        "nombre": contacto.nombre,
        "activo": bool(contacto.activo) if contacto.activo is not None else None,
    }


def _las_colisiones(uno: dict, otro: dict) -> list[dict]:
    """**Lo que hay que decidir antes de fusionar**, dicho una por una y con la instrucción de qué hacer.

    No se resuelve nada aquí: se enseña. El encargo pide «resolver conflictos explícitamente», y una fusión que
    eligiera sola estaría decidiendo por el agricultor.
    """
    colisiones: list[dict] = []

    repetidos = sorted(set(uno["papeles"]) & set(otro["papeles"]))
    if repetidos:
        colisiones.append(
            {
                "que": "papel_repetido",
                "detalle": repetidos,
                "por_que": "la base no admite el mismo papel dos veces en la misma ficha "
                "(`uq_papel_del_contacto`), así que hay que quedarse con uno",
                "que_hacer": "el papel se queda una sola vez: no se pierde nada, porque es el mismo papel",
            }
        )

    for clase in sorted(set(uno["canales_principales"]) & set(otro["canales_principales"])):
        colisiones.append(
            {
                "que": "principal_repetido",
                "detalle": clase,
                "por_que": "la base admite **un solo principal por clase** (`uq_canal_principal_del_contacto`)",
                "que_hacer": "al del origen se le quita el «principal»: los dos canales se conservan, "
                "pero solo uno manda",
            }
        )

    if uno["tiene_sus_notas_escritas"] and otro["tiene_sus_notas_escritas"]:
        colisiones.append(
            {
                "que": "las_dos_tienen_notas_escritas",
                "detalle": None,
                "por_que": "`Contacto.notas` es **un campo de texto único**, no la tabla de notas: "
                "no hay sitio para las dos y la de una se perdería",
                "que_hacer": "hay que decidir cuáles se quedan, o copiarlas a mano antes: esto **no lo puede "
                "decidir la fusión**",
            }
        )

    return colisiones


@router.get("/{contacto_id}/fusion/{destino_id}")
def la_vista_previa_de_una_fusion(
    contacto_id: int,
    destino_id: int,
    db: Db,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
) -> dict:
    """**Qué pasaría si se juntaran estas dos fichas**, sin tocar nada.

    El origen es `contacto_id` (el que se va a quedar sin uso) y el destino es `destino_id` (el que se queda). Se
    devuelven las dos fichas, lo que cuelga de cada una, **las colisiones que habría que decidir** y —solo con la
    capacidad económica— **los dos saldos**, para poder comprobar después que la suma es la misma.
    """
    if contacto_id == destino_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Una ficha no se puede fusionar consigo misma.",
        )
    origen = _la_ficha(db, explotacion.id, contacto_id)
    destino = _la_ficha(db, explotacion.id, destino_id)

    lo_del_origen = _lo_que_tiene(db, origen)
    lo_del_destino = _lo_que_tiene(db, destino)

    respuesta: dict = {
        "origen": lo_del_origen,
        "destino": lo_del_destino,
        "colisiones": _las_colisiones(lo_del_origen, lo_del_destino),
        # **Lo que la fusión NO va a tocar, dicho para que nadie lo tema**: el texto de los documentos se queda
        # exactamente como está (los enlaces llevan `nombre_de_entonces`), y el autor y la fecha de cada nota son de
        # quien la escribió.
        "se_conserva": [
            "el texto y el identificador de cada documento: solo cambia de qué ficha cuelga",
            "el autor y la fecha de cada nota",
            "el nombre que decía cada papel (`nombre_de_entonces`)",
            "los importes y las asignaciones: no se compensa nada entre sentidos distintos",
        ],
    }

    # **El dinero, solo con permiso.** Sin él, ni los saldos ni las cifras: los recuentos de arriba no son importes.
    if accesos.puede_ver_lo_economico(db, usuario.id, explotacion.id):
        respuesta["saldos"] = {
            "origen": saldos.el_saldo_de_un_contacto(db, explotacion_id=explotacion.id, contacto_id=origen.id),
            "destino": saldos.el_saldo_de_un_contacto(db, explotacion_id=explotacion.id, contacto_id=destino.id),
        }
    else:
        respuesta["saldos"] = None
        respuesta["saldos_por_que_no"] = (
            "Tu cuenta no puede ver las cuentas de esta finca, así que la vista previa no lleva importes."
        )

    return respuesta
