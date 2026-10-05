"""Las medidas preventivas de la explotación: la parte no química de la gestión de plagas.

La app oficial las tiene en «Explotación: Medidas Preventivas», y su texto es literal:
*«El apartado Medidas Preventivas permite anotar las medidas utilizadas en la explotación
para la gestión integrada de plagas. Para cumplimentarlo: marcar las medidas preventivas, y
Guardar. Es posible marcar varias medidas.»*

El contenido mínimo del CUE las sitúa **a nivel de Explotación**, en el bloque «GIP a nivel
de explotación», apartado 1.1 «Medidas preventivas/culturales», con un solo campo: «Medida
preventiva/cultural (según catálogo)».

**Por qué es un registro aparte, y no una casilla de cada tratamiento.** Son dos cosas
distintas y las dos hacen falta:

1. **Aquí**: lo que haces normalmente en tu finca. Se declara una vez, vale para todo el
   año, y es lo que se enseña en una inspección.
2. **En cada tratamiento** (`TratamientoFitosanitario.medidas`): lo que hiciste **esa vez**
   antes de decidir echar el producto.

Lo que une las dos: al apuntar un tratamiento, **lo que hayas declarado aquí ya sale
marcado**. Eso es lo que hace que la sección sirva de algo en vez de ser un formulario que
se rellena una vez y no se vuelve a mirar. Antes de esto, el campo `medidas` del tratamiento
existía en la base de datos pero **la pantalla no lo preguntaba nunca**, así que siempre
estaba vacío: el aviso de la gestión integrada de plagas no se podía cumplir de ninguna
manera.

Dos decisiones que conviene no deshacer:

* **Desmarcar una medida no la borra**: se queda con `aplicada=False`. Así, cuando alguien
  pregunte «¿esto lo hacías en 2024?», la respuesta está.
* **Se manda la declaración entera de una vez**, no casilla a casilla: la pantalla es una
  sola con diez casillas y un botón de guardar, y dos toques seguidos no pueden dejar la
  declaración a medias.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import catalogos, correcciones, models, servicios, textos, validaciones
from ..deps import Db, ExplotacionActual, UsuarioActual
from ..schemas import (
    DeclaracionDeMedidas,
    MedidaConPregunta,
    MedidasEntrada,
)

router = APIRouter(prefix="/api", tags=["medidas preventivas"])


def _mensaje(cuantas: int, declarada: bool) -> str:
    if not declarada:
        return textos.MEDIDAS["sin_declarar"]
    if cuantas == 0:
        return textos.MEDIDAS["declarada_ninguna"]
    if cuantas == 1:
        return textos.MEDIDAS["declarada_una"].format(cuantas=cuantas)
    return textos.MEDIDAS["declarada_varias"].format(cuantas=cuantas)


def _declaracion(db, explotacion) -> DeclaracionDeMedidas:
    """Las diez preguntas con la respuesta del agricultor, en el orden del catálogo.

    Se devuelven **siempre las diez**, aunque no haya declarado nada: la pantalla enseña
    las diez casillas y el agricultor marca las que haga. Si solo se devolvieran las
    marcadas, no habría forma de marcar la primera.
    """
    guardadas = {fila.medida: fila for fila in servicios.medidas_declaradas(db, explotacion_id=explotacion.id)}
    medidas = [
        MedidaConPregunta(
            codigo=medida.codigo,
            aplicada=bool(guardadas[medida.codigo].aplicada) if medida.codigo in guardadas else False,
            observaciones=(
                guardadas[medida.codigo].observaciones if medida.codigo in guardadas else None
            ),
            pregunta=medida.pregunta,
            etiqueta=medida.etiqueta,
        )
        for medida in catalogos.MEDIDAS_PREVENTIVAS
    ]
    aplicadas = [medida.codigo for medida in medidas if medida.aplicada]
    return DeclaracionDeMedidas(
        medidas=medidas,
        aplicadas=aplicadas,
        declarada=bool(guardadas),
        cuantas=len(aplicadas),
        mensaje=_mensaje(len(aplicadas), bool(guardadas)),
        explicacion=textos.MEDIDAS["explica"],
    )


@router.get("/medidas", response_model=DeclaracionDeMedidas)
def ver_medidas(explotacion: ExplotacionActual, db: Db) -> DeclaracionDeMedidas:
    """Lo que el agricultor ha dicho que hace sin echar producto, con las diez preguntas."""
    return _declaracion(db, explotacion)


@router.post("/medidas/validar")
def validar_medidas_endpoint(datos: MedidasEntrada, _: ExplotacionActual) -> dict:
    """Pregunta qué le falta a la declaración de medidas **antes** de guardarla.

    **Pide sesión desde el 03/10/2026, y antes no la pedía**: es la cuarta de las que la
    revisión de rutas sin sesión marcó como «debería pedir sesión»
    (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.20). De las cuatro es la que menos exponía
    —su cuerpo no lleva ningún identificador de finca—, pero la regla es la misma: lo que
    valida es la declaración **de una finca**, y para eso hay que entrar. No rompe nada:
    la pantalla y el recorrido ya mandan su vale.
    """
    avisos = validaciones.validar_medidas(aplicadas=datos.aplicadas)
    return {
        "puede_guardarse": not validaciones.hay_bloqueo(avisos),
        "avisos": [aviso.como_dict() for aviso in avisos],
    }


@router.put("/medidas", response_model=DeclaracionDeMedidas)
def declarar_medidas(
    datos: MedidasEntrada, explotacion: ExplotacionActual, db: Db
) -> DeclaracionDeMedidas:
    """Guarda la declaración entera.

    Se usa `PUT` y no `POST` a propósito: no se crea un apunte más, se **sustituye la
    declaración** de la finca. Y no hay endpoint para anularla, porque desmarcar las diez
    casillas es exactamente eso.

    Decisión sobre un código que no esté en el catálogo: **se descarta, no se rechaza la
    declaración entera.** Si el agricultor ha marcado siete medidas y una llega con un
    código que el servidor no conoce, lo que no puede pasar es que pierda las siete. Se
    guardan las siete y se le dice cuál se ha descartado, en `descartadas`.
    """
    desconocidas = sorted(
        codigo for codigo in datos.aplicadas if catalogos.medida_de(codigo) is None
    )
    servicios.declarar_medidas(
        db,
        explotacion_id=explotacion.id,
        aplicadas=[codigo for codigo in datos.aplicadas if codigo not in desconocidas],
        observaciones=datos.observaciones,
    )
    declaracion = _declaracion(db, explotacion)
    declaracion.descartadas = desconocidas
    return declaracion


@router.delete("/medidas", response_model=DeclaracionDeMedidas)
def quitar_la_declaracion(
    explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> DeclaracionDeMedidas:
    """Deja la finca **sin declarar** las medidas preventivas.

    POR QUÉ ESTO NO ES LO MISMO QUE MANDAR UNA LISTA VACÍA EN EL `PUT`, que es lo que se podría
    pensar. Son dos cosas distintas y hacen falta las dos:

      · `PUT` con la lista vacía = **«he dicho que no hago ninguna»**. El agricultor ha mirado las
        diez preguntas y ha contestado que ninguna, y eso es una respuesta: se guarda, sale en el
        informe con su mensaje (`declarada_ninguna` — «has dicho que no haces ninguna de estas
        cosas») y el aviso de los tratamientos sabe que ya se ha pronunciado.
      · `DELETE` = **«todavía no he dicho nada»**. La declaración no existe, la finca queda como una
        recién dada de alta y el programa **vuelve a preguntar** (`sin_declarar`: «todavía no has
        dicho qué haces sin echar producto»).

    Es la diferencia entre una respuesta y una pregunta sin contestar, y ninguna de las dos se puede
    decir con la otra. Por eso este endpoint existe aunque el `PUT` ya estuviera.

    QUÉ BORRA EXACTAMENTE, Y POR QUÉ BORRA ESO. **Todas las filas de la declaración de esta finca**,
    incluidas las que están sin marcar (`aplicada=False`). Esa parte es la que hay que explicar,
    porque parece historia y no lo es: `servicios.declarar_medidas` **crea una fila por cada una de
    las diez medidas del catálogo** en cuanto se declara algo, marcada o no, así que las no marcadas
    no son «lo que hacía antes»: son **las preguntas de hoy que quedaron sin marcar**. Si se
    quedaran, `GET /api/medidas` seguiría diciendo que la finca **está declarada** —con cero
    medidas— y el agricultor leería «has dicho que no haces ninguna de estas cosas», que es una
    frase que no ha dicho: una mentira dentro del cuaderno. Para que la finca vuelva a estar «sin
    declarar» no puede quedar ninguna fila, porque «declarada» es exactamente eso: que hay
    declaración.

    QUÉ NO BORRA, y también es a propósito:

      · Lo que se hizo en cada tratamiento (`TratamientoFitosanitario.medidas`) no se toca: **eso es
        lo que pasó ese día**, y quitarlo cambiaría apuntes del cuaderno que ya están hechos.
      · Y lo que había declarado no se pierde: **cada fila se va con su contenido entero a la
        auditoría** (`correcciones.borrar`), así que el programa sabe qué decía cada medida, si
        estaba marcada, con qué observaciones y qué día se quitó la declaración.
    """
    for fila in servicios.medidas_declaradas(db, explotacion_id=explotacion.id):
        correcciones.borrar(
            db,
            registro=fila,
            entidad="medida_preventiva",
            explotacion_id=explotacion.id,
            usuario_id=usuario.id,
        )
    return _declaracion(db, explotacion)


@router.get("/medidas/informe")
def informe_de_medidas(explotacion: ExplotacionActual, db: Db) -> dict:
    """El listado que se entrega: las medidas con su nombre oficial.

    Va declarado antes de cualquier ruta con identificador, por el mismo motivo que en las
    analíticas: FastAPI resuelve por orden de declaración y «informe» se leería como un
    identificador.
    """
    filas = servicios.medidas_declaradas(db, explotacion_id=explotacion.id)
    aplicadas = [fila for fila in filas if fila.aplicada]
    return {
        "titulo": textos.MEDIDAS["informe_titulo"],
        "de_la_finca": textos.MEDIDAS["de_la_finca"],
        "cuantas": len(aplicadas),
        "filas": [
            {
                "medida": catalogos.etiqueta_medida(fila.medida),
                "observaciones": fila.observaciones or "",
            }
            for fila in aplicadas
        ],
        "sin_nada": textos.MEDIDAS["informe_sin_nada"],
        "declarada": bool(filas),
        "mensaje": _mensaje(len(aplicadas), bool(filas)),
        "catalogo_aviso": textos.MEDIDAS["catalogo_aviso"],
    }
