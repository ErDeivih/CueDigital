"""La bandeja documental por la API: subir, mirar, confirmar y enlazar (T08, S10).

## Las puertas que tiene, y qué hace cada una

| Puerta | Qué hace | Qué **no** hace |
|---|---|---|
| `POST /api/bandeja/comprobar` | lee el fichero que se va a subir, le calcula la huella y dice si ese mismo papel ya estaba | no escribe **nada** en la base |
| `POST /api/bandeja/subir` | guarda el papel con su fichero **tal y como llegó** y lo deja en la bandeja | no lee nada y, si es un duplicado, no crea ninguna ficha |
| `GET /api/bandeja` | la bandeja entera, reconstruida al abrir su dirección | no ordena nada por «calidad de la lectura»: eso no se puede medir |
| `GET /api/bandeja/candidatos` | las cosas del cuaderno con las que se puede enlazar, por clase | no inventa candidatos: solo ofrece lo que ya existe |
| `GET /api/bandeja/{id}` | la ficha de un papel: el original, la propuesta, lo aceptado, sus enlaces y sus rectificaciones | no deja tocar el fichero ni la huella |
| `POST /api/bandeja/{id}/clasificar` | dice de qué es el papel | no cambia nada más |
| `POST /api/bandeja/{id}/leer` | lee el fichero y guarda **la propuesta** | no confirma nada: leer no es revisar |
| `POST /api/bandeja/{id}/revisar` | guarda **lo que el agricultor acepta** de la lectura | no lo pasa al papel todavía |
| `POST /api/bandeja/{id}/descartar` | dice que la lectura no sirve (queda guardada, con su motivo) | no borra lo leído |
| `POST /api/bandeja/{id}/confirmar` | pasa lo aceptado al papel, con quién y cuándo | **no acepta campos**: sin revisar antes, no se confirma |
| `POST /api/bandeja/{id}/vincular` | enlaza el papel con una compra, un gasto, una venta, una máquina, un trabajo o una inspección | **no crea** el gasto, ni la factura, ni la venta |
| `POST /api/bandeja/{id}/desvincular` | quita ese enlace, dejando el rastro | no borra lo enlazado |
| `POST /api/bandeja/{id}/rectificar` | dice a qué papel rectifica este | no borra ni tapa al rectificado |

El original **no tiene puerta propia aquí**: se ve y se descarga con la que ya existe
(`GET /api/documentos/{id}/fichero`), porque un papel es el mismo papel se mire desde donde se mire.
Y el fichero **no se puede reescribir** por ninguna de estas puertas: lo único que se puede subir es
un papel nuevo.

## Las tablas y los esquemas que necesita

Los integra el coordinador en `app/models.py` y `app/schemas.py`, y **el bloque literal está en
`docs/T08_BANDEJA.md`**: las columnas nuevas de `documentos_anexos` (la huella, el estado de la
revisión, la propuesta, lo aceptado, quién confirmó y a quién rectifica) y la tabla
`vinculos_de_documento`. Mientras no estén, `tests/test_bandeja.py` **se salta las pruebas de este
recorrido diciendo exactamente qué falta** (el patrón del T13 y del T20), en vez de dar un verde que
no comprueba nada.

## Lo que estas puertas NO hacen, cada una con su motivo

1. **No dicen si la lectura es buena.** Ni «leído correctamente», ni un porcentaje, ni una confianza.
   El corpus para medirlo es el T07, que está bloqueado: afirmarlo sería inventarse un número. Lo
   único que se dice de una línea es si **su cuenta cuadra** (cantidad × precio = importe), que es
   aritmética y se comprueba sin corpus.
2. **No confirman nada solas.** `confirmar` **no acepta campos**: los campos se aceptan en `revisar`.
   Así «confirmar sin que nadie lo haya mirado» no es un descuido que haya que vigilar, es una puerta
   que no existe.
3. **No reescriben el original.** La huella se calcula al subir y no se vuelve a calcular nunca: ni al
   leer, ni al revisar, ni al confirmar.
4. **No duplican lo que ya existe**: el alta del papel y la subida del fichero se hacen llamando a las
   puertas que ya tiene el programa (`documentos_api.crear` y `documentos_api.subir_fichero`). Tener
   dos caminos que guardan ficheros en disco sería tener dos sitios donde equivocarse con las rutas.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select

from .. import adjuntos, bandeja, dinero, facturas, models, textos
from ..deps import Db, ExplotacionActual, UsuarioActual
from ..schemas import (
    DocumentoEntrada,
    ElFicheroComprobadoSalida,
    LaBandejaSalida,
    LaPropuestaSalida,
    LoQueHaPasadoSalida,
    LoQueSeAceptoSalida,
    LosCandidatosSalida,
    PapelDeLaBandejaSalida,
    VinculoDeUnPapelSalida,
)
from . import documentos_api

router = APIRouter(prefix="/api", tags=["la bandeja"])

# Cuántos candidatos se ofrecen de una vez para enlazar. No es un tope de datos —el agricultor puede
# buscar por texto— sino de pantalla: una lista de doscientos gastos en un móvil no se puede usar.
MAXIMO_DE_CANDIDATOS = 50


# ==========================================================================
# Ayudas de esta pantalla
# ==========================================================================


def _el_papel(db: Db, explotacion, documento_id: int) -> models.DocumentoAnexo:
    """El papel, comprobando que es de esta finca.

    Se contesta 404 y no 403 cuando es de otra, como en todo el programa: así no se puede averiguar
    qué identificadores existen en otra finca probando números.
    """
    papel = db.get(models.DocumentoAnexo, documento_id)
    if papel is None or papel.explotacion_id != explotacion.id:
        raise HTTPException(
            status_code=404, detail=textos.mensaje("T08_ese_papel_no_esta_en_tu_bandeja")
        )
    return papel


def _el_rastro(
    db: Db, explotacion_id: int, documento_id: int, *, accion: str, datos: dict, usuario_id: int | None
) -> None:
    """La fila del rastro de auditoría: quién, cuándo y qué.

    `accion` es un texto fijo y tiene que caber en `auditoria.accion` (mide 80). Hay un guardián en el
    programa (`tests/test_las_etiquetas_del_rastro_caben.py`) que lee todas las etiquetas y avisa.
    """
    db.add(
        models.Auditoria(
            explotacion_id=explotacion_id,
            usuario_id=usuario_id,
            entidad="documento",
            entidad_id=documento_id,
            accion=accion,
            datos=datos,
        )
    )


def _una_fecha(fecha: dt.date | None) -> str:
    """Una fecha escrita como se escribe aquí. Vacía si no consta: nunca «01/01/1970»."""
    return fecha.strftime("%d/%m/%Y") if fecha else ""


def _cuando(datetime_o_nada) -> str:
    """La fecha de un «cuándo» que puede no constar (la de subir un papel, por ejemplo)."""
    if not isinstance(datetime_o_nada, dt.datetime):
        return ""
    return _una_fecha(datetime_o_nada.date())


def _la_propuesta_guardada(papel) -> dict | None:
    """La propuesta que tiene guardada ese papel. Lo que no se puede leer es «no lo sé», no un fallo."""
    return bandeja.de_json(getattr(papel, "propuesta", None))


def _lo_aceptado_guardado(papel) -> dict:
    """Lo que el agricultor aceptó de ese papel, tal y como se guardó (puede estar vacío)."""
    return bandeja.de_json(getattr(papel, "datos_confirmados", None)) or {}


def _el_aviso_escrito(aviso: str) -> str:
    """Un aviso, en palabras del agricultor.

    Los avisos del lector de facturas **ya vienen escritos** (`facturas.py` los escribe para él), y
    los que son de este ticket se guardan **como clave** (`bandeja.propuesta_sin_leer`) porque
    `bandeja.py` no escribe textos. Aquí se traducen los segundos y se dejan pasar los primeros: una
    clave conocida se convierte, y lo que no es una clave se enseña tal cual.
    """
    return textos.mensaje(aviso) if aviso in textos.MENSAJES else aviso


def _con_los_importes_escritos(campos: dict | None) -> dict:
    """Una cabecera (leída o aceptada), con **todos sus campos escritos** además del dato.

    El dato viaja como texto decimal (`"980.10"`), que es como se guarda el dinero en todo el programa;
    lo que se lee es `"980,10 €"`, y eso lo escribe `dinero.formatea`, que es el único sitio del
    programa que sabe escribir un importe. La fecha se escribe como se escribe aquí (`31/12/2026`) y
    los textos (el proveedor, el número de factura) van tal cual.

    Se mandan **los dos**: el dato y su versión escrita. Y no es un adorno: es lo que hace que la
    pantalla pueda no creerse el texto. Cuando un campo no consta, su versión escrita sale **vacía**, y
    quien decide qué se enseña es el dato (`unDato`, en `bandeja.js`). Un `0,00 €` en el sitio de un
    importe que no consta diría que el papel pone cero euros, que es lo contrario de lo que dice.
    """
    valores = dict(campos or {})
    escritos: dict = {}
    for campo in bandeja.CAMPOS_DE_LA_CABECERA:
        if campo in bandeja.CAMPOS_DE_DINERO:
            escritos[campo] = dinero.formatea(dinero.de_texto(valores.get(campo)))
        elif campo in bandeja.CAMPOS_DE_FECHA:
            escritos[campo] = _la_fecha_escrita(valores.get(campo))
        else:
            escritos[campo] = valores.get(campo) or ""
    return {"campos": valores, "textos": escritos}


def _la_fecha_escrita(valor: str | None) -> str:
    """Una fecha guardada en ISO, escrita como se lee aquí. Lo que no se entiende queda vacío."""
    if not valor:
        return ""
    try:
        return _una_fecha(dt.date.fromisoformat(str(valor)))
    except ValueError:
        return ""


def _el_precio_escrito(valor: str | None) -> str:
    """Un precio por unidad, con las cifras que trae.

    Un precio pactado puede llevar más de dos decimales (`0,2350 €/kg`) y redondearlo al céntimo aquí
    sería enseñar otro precio del que se pactó —el mismo motivo por el que `dinero` guarda los
    precios con seis cifras—. Se enseñan las que tiene, y como mucho seis.
    """
    numero = dinero.de_texto(valor)
    if numero is None:
        return ""
    cifras = max(2, min(-numero.as_tuple().exponent, dinero.DECIMALES_DE_UN_PRECIO))
    return dinero.formatea(numero, cifras)


def _las_lineas_escritas(lineas: list[dict] | None) -> list[dict]:
    """Las líneas leídas, con su importe y su precio escritos. **Sin ningún juicio sobre la lectura.**"""
    salida: list[dict] = []
    for linea in lineas or []:
        copia = dict(linea)
        copia["texto_importe"] = dinero.formatea(dinero.de_texto(linea.get("importe")))
        copia["texto_precio_unitario"] = _el_precio_escrito(linea.get("precio_unitario"))
        # Una cantidad se lee con coma («1,5 kg»), y lo que no consta se queda en blanco.
        copia["texto_cantidad"] = (linea.get("cantidad") or "").replace(".", ",")
        salida.append(copia)
    return salida


def _la_propuesta_como_sale(papel) -> LaPropuestaSalida | None:
    """La propuesta guardada, con lo que hace falta para enseñarla y nada más.

    Se añaden aquí, y no se guardan, **cuántas líneas hay, cuántas cuadran y si las cuentas del papel
    cuadran**: son las tres cosas que el lector sí puede comprobar. Lo que no se añade es ninguna
    medida de la calidad de la lectura, porque no hay con qué medirla.
    """
    propuesta = _la_propuesta_guardada(papel)
    if not propuesta:
        return None
    lineas = _las_lineas_escritas(propuesta.get("lineas"))
    return LaPropuestaSalida(
        clase=propuesta.get("clase") or "",
        como_se_leyo=propuesta.get("como_se_leyo") or "",
        leido_en=propuesta.get("leido_en") or "",
        **_con_los_importes_escritos(propuesta.get("campos")),
        lineas=lineas,
        avisos=[_el_aviso_escrito(aviso) for aviso in (propuesta.get("avisos") or [])],
        lineas_leidas=len(lineas),
        lineas_que_cuadran=len([linea for linea in lineas if linea.get("la_cuenta_cuadra")]),
        cuadra_el_total=bool(propuesta.get("cuadra_el_total")),
        suman_las_lineas=bool(propuesta.get("suman_las_lineas")),
    )


def _lo_aceptado_como_sale(papel) -> LoQueSeAceptoSalida | None:
    """Lo que el agricultor aceptó, con sus importes escritos. Vacío es «todavía no ha decidido»."""
    aceptado = _lo_aceptado_guardado(papel)
    if not aceptado:
        return None
    return LoQueSeAceptoSalida(**_con_los_importes_escritos(aceptado))


def _la_entidad(db: Db, modelo, entidad_id: int | None, explotacion_id: int):
    """La cosa enlazada, si sigue existiendo y es de esta finca. Si no, `None`.

    **Tolerante a propósito.** Un gasto se puede borrar y una labor también, y un vínculo que apunte a
    algo que ya no está no puede tumbar la lista entera de la bandeja con un error del servidor: lo
    que se dice es que eso ya no está en el cuaderno, que es la verdad y además se puede arreglar.
    """
    if not entidad_id:
        return None
    fila = db.get(modelo, int(entidad_id))
    if fila is None or getattr(fila, "explotacion_id", None) != explotacion_id:
        return None
    return fila


def _el_modelo_de_la_clase(clase: str):
    """Qué tabla hay detrás de cada clase de vínculo. Una sola lista, para que no puedan discrepar."""
    return {
        bandeja.COMPRA: models.Factura,
        bandeja.GASTO: models.Gasto,
        bandeja.VENTA: models.VentaDeCosecha,
        bandeja.MAQUINA: models.Maquina,
        bandeja.TRABAJO: models.Labor,
        bandeja.TIERRA: models.Parcela,  # el papel de una tierra: se comprueba que sea de esta finca, como las demas
        bandeja.INSPECCION: models.InspeccionDeMaquina,
    }[clase]


def _la_tierra(db: Db, explotacion, parcela_id: int | None) -> str:
    """El nombre de la tierra de un trabajo. Un número de parcela no le dice nada a nadie."""
    tierra = _la_entidad(db, models.Parcela, parcela_id, explotacion.id)
    return tierra.alias if tierra else ""


def _el_nombre_de_lo_enlazado(db: Db, explotacion, clase: str, entidad_id: int) -> str:
    """Cómo se llama lo que está enlazado, en las palabras del agricultor.

    Se compone aquí y no en la pantalla por la regla de siempre: el vocabulario vive en el servidor. Y
    lo que **no** se enseña nunca es un identificador («gasto:37»), que es un dato del programa y no
    el nombre de nada.
    """
    partes: list[str] = [textos.BANDEJA[bandeja.clave_de_la_clase(clase)]]
    fila = _la_entidad(db, _el_modelo_de_la_clase(clase), entidad_id, explotacion.id)
    if fila is not None:
        if clase == bandeja.COMPRA:
            partes += [fila.proveedor, fila.numero_factura, _una_fecha(fila.fecha)]
        elif clase == bandeja.GASTO:
            partes += [fila.concepto, fila.proveedor, _una_fecha(fila.fecha)]
        elif clase == bandeja.VENTA:
            partes += [fila.producto, fila.comprador, _una_fecha(fila.fecha)]
        elif clase == bandeja.MAQUINA:
            partes += [fila.nombre, fila.matricula]
        elif clase == bandeja.TRABAJO:
            partes += [_la_tierra(db, explotacion, fila.parcela_id), _una_fecha(fila.fecha)]
        elif clase == bandeja.INSPECCION:
            maquina = _la_entidad(db, models.Maquina, fila.maquina_id, explotacion.id)
            partes += [maquina.nombre if maquina else "", _una_fecha(fila.fecha)]
    else:
        # El vínculo está, pero lo enlazado ya no: se dice, en vez de dejar un hueco o un número.
        partes.append(textos.BANDEJA["eso_ya_no_esta"])
    return " · ".join([str(parte) for parte in partes if parte])


def _los_vinculos(db: Db, explotacion, documento_id: int) -> list:
    return list(
        db.scalars(
            select(models.VinculoDeDocumento)
            .where(
                models.VinculoDeDocumento.explotacion_id == explotacion.id,
                models.VinculoDeDocumento.documento_id == documento_id,
            )
            .order_by(models.VinculoDeDocumento.id)
        )
    )


def _los_vinculos_como_salen(db: Db, explotacion, documento_id: int) -> list[VinculoDeUnPapelSalida]:
    return [
        VinculoDeUnPapelSalida(
            id=vinculo.id,
            clase=vinculo.clase,
            etiqueta_clase=textos.BANDEJA[bandeja.clave_de_la_clase(vinculo.clase)],
            entidad_id=vinculo.entidad_id,
            que_es=_el_nombre_de_lo_enlazado(db, explotacion, vinculo.clase, vinculo.entidad_id),
            creado_en=vinculo.creado_en,
        )
        for vinculo in _los_vinculos(db, explotacion, documento_id)
    ]


def _los_vinculos_en_crudo(db: Db, explotacion, documento_id: int) -> list[dict]:
    """Los vínculos como diccionarios, para las comprobaciones de este router (no para la pantalla)."""
    return [
        {"clase": vinculo.clase, "entidad_id": vinculo.entidad_id}
        for vinculo in _los_vinculos(db, explotacion, documento_id)
    ]


def _las_rectificaciones(db: Db, explotacion, papel) -> tuple[dict | None, list[dict]]:
    """A quién rectifica este papel y quiénes lo rectifican a él.

    **La relación se guarda en un solo sitio** (`rectifica_a_id`, en la rectificativa) y «esta está
    rectificada» se deduce de ahí: dos columnas que se apunten la una a la otra acabarían diciendo
    cosas distintas el día que una se cambie sin la otra.
    """
    a_quien: dict | None = None
    if papel.rectifica_a_id:
        otro = _la_entidad(db, models.DocumentoAnexo, papel.rectifica_a_id, explotacion.id)
        if otro is not None:
            a_quien = {"id": otro.id, "titulo": otro.titulo}
    quienes = [
        {"id": anexo.id, "titulo": anexo.titulo}
        for anexo in db.scalars(
            select(models.DocumentoAnexo).where(
                models.DocumentoAnexo.explotacion_id == explotacion.id,
                models.DocumentoAnexo.rectifica_a_id == papel.id,
            )
        )
    ]
    return a_quien, quienes


def _la_cadena_de_rectificaciones(db: Db, explotacion) -> dict:
    """Quién rectifica a quién, tal y como está hoy. Es lo que se recorre para buscar un círculo."""
    return {
        anexo.id: anexo.rectifica_a_id
        for anexo in db.scalars(
            select(models.DocumentoAnexo).where(
                models.DocumentoAnexo.explotacion_id == explotacion.id,
                models.DocumentoAnexo.rectifica_a_id.is_not(None),
            )
        )
    }


def _cuantos_candidatos(db: Db, explotacion) -> dict:
    """Cuántas cosas hay de cada clase, para poder decir «hay 12 gastos donde enlazarlo» **antes** de
    que el agricultor elija, en vez de que se encuentre una lista vacía sin explicación."""
    cuantos: dict = {}
    for clase, columna in (
        (bandeja.COMPRA, "anulada"),
        (bandeja.GASTO, "anulado"),
        (bandeja.VENTA, "anulado"),
        (bandeja.MAQUINA, None),
        (bandeja.TRABAJO, "anulado"),
        (bandeja.INSPECCION, "anulado"),
    ):
        modelo = _el_modelo_de_la_clase(clase)
        consulta = select(func.count()).select_from(modelo).where(
            modelo.explotacion_id == explotacion.id
        )
        if columna is not None:
            consulta = consulta.where(getattr(modelo, columna).is_(False))
        cuantos[clase] = int(db.scalar(consulta) or 0)
    return cuantos


def _como_sale_un_papel(
    db: Db, explotacion, papel, cuantos_candidatos: dict | None = None
) -> PapelDeLaBandejaSalida:
    """El papel con todo lo que la pantalla necesita para enseñarlo y para decidir qué hacer.

    Los tres `se_puede_*` los decide **el servidor** y no la pantalla, y ese es el detalle que hace
    que el recorrido no se pueda saltar desde el navegador: `se_puede_confirmar` es falso mientras no
    haya algo aceptado, y una pantalla no puede confirmar lo que el servidor no deja confirmar.

    `cuantos_candidatos` se pasa hecho desde la lista (donde se cuenta una vez para todos los papeles)
    y se calcula aquí cuando se abre una ficha sola: contar seis tablas por papel sería trabajar de
    más por un dato que es el mismo para toda la bandeja.
    """
    propuesta = _la_propuesta_guardada(papel)
    aceptado = _lo_aceptado_guardado(papel)
    estado = getattr(papel, "estado_revision", None) or bandeja.CLASIFICADO
    a_quien, quienes = _las_rectificaciones(db, explotacion, papel)
    confirma = (
        _la_entidad(db, models.Usuario, papel.confirmado_por_usuario_id, explotacion.id)
        if papel.confirmado_por_usuario_id
        else None
    )
    return PapelDeLaBandejaSalida(
        id=papel.id,
        titulo=papel.titulo,
        tipo=papel.tipo,
        etiqueta_tipo=bandeja.etiqueta_de_papel(papel.tipo),
        carpeta=papel.carpeta or documentos_api.CARPETA_POR_DEFECTO,
        estado=estado,
        etiqueta_estado=textos.BANDEJA[bandeja.clave_del_estado(estado)],
        sin_revisar=bandeja.esta_sin_revisar(estado),
        fecha=papel.fecha,
        quien=papel.quien,
        tiene_fichero=bool(papel.fichero_ruta),
        nombre_del_fichero=papel.fichero_nombre,
        tipo_del_fichero=papel.fichero_tipo,
        bytes=papel.fichero_bytes,
        texto_tamano=bandeja.describe_el_tamano(papel.fichero_bytes),
        huella=papel.huella,
        como_se_leyo=papel.como_se_leyo,
        propuesta_descartada=bool(papel.propuesta_descartada),
        la_propuesta=_la_propuesta_como_sale(papel),
        lo_aceptado=_lo_aceptado_como_sale(papel),
        se_puede_leer=bandeja.se_puede_leer(papel.tipo) and bool(papel.fichero_ruta),
        se_puede_confirmar=bandeja.se_puede_confirmar(
            estado, hay_algo_aceptado=bandeja.hay_algo_aceptado(aceptado)
        ),
        se_puede_descartar_la_propuesta=bandeja.se_puede_descartar_la_propuesta(
            hay_propuesta=bandeja.tiene_algo(propuesta),
            hay_algo_aceptado=bandeja.hay_algo_aceptado(aceptado),
        ),
        confirmado_en=papel.confirmado_en,
        confirmado_por=confirma.nombre if confirma else None,
        rectifica_a=a_quien,
        rectificada_por=quienes,
        vinculos=_los_vinculos_como_salen(db, explotacion, papel.id),
        clases_sugeridas=list(bandeja.clases_que_se_sugieren(papel.tipo)),
        cuantos_candidatos=(
            cuantos_candidatos if cuantos_candidatos is not None else _cuantos_candidatos(db, explotacion)
        ),
        creado_en=papel.creado_en,
    )


def _lo_que_ha_pasado(
    db: Db, explotacion, papel, avisos: list[str] | None = None
) -> LoQueHaPasadoSalida:
    """Lo que devuelven las puertas que cambian algo: el papel **como ha quedado** y lo que hay que decir.

    Se devuelve siempre el papel entero, y así la pantalla no tiene que recomponer nada: enseña lo que
    el servidor acaba de decir que hay.
    """
    return LoQueHaPasadoSalida(
        papel=_como_sale_un_papel(db, explotacion, papel),
        avisos=[aviso for aviso in (avisos or []) if aviso],
    )


def _los_papeles_con_la_huella(db: Db, explotacion, huella: str | None) -> list[dict]:
    """Los papeles de esta finca con esa misma huella, **en cualquier estado**.

    No se limita a los que están sin revisar: un papel ya confirmado con la misma huella sigue siendo
    el mismo papel, y subirlo otra vez crearía una segunda ficha de algo que ya está en el cuaderno.
    """
    if not huella:
        return []
    return [
        {
            "id": papel.id,
            "titulo": papel.titulo,
            "huella": papel.huella,
            "estado": getattr(papel, "estado_revision", None) or "",
            "creado_en": papel.creado_en,
        }
        for papel in db.scalars(
            select(models.DocumentoAnexo).where(
                models.DocumentoAnexo.explotacion_id == explotacion.id,
                models.DocumentoAnexo.huella == huella,
            )
        )
    ]


def _las_facturas_con_la_huella(db: Db, explotacion, huella: str | None) -> list[dict]:
    """Las facturas de compra con esa misma huella.

    Se miran **porque el mismo papel puede haber entrado por la puerta de las facturas**: esa tabla
    guarda su huella desde que se construyó el lector (`models.Factura.huella`), y una foto que ya
    está en el cuaderno como factura no puede volver a entrar como papel suelto sin decirlo.
    """
    if not huella:
        return []
    return [
        {
            "id": factura.id,
            "titulo": factura.proveedor or factura.numero_factura or "",
            "huella": factura.huella,
            "numero_factura": factura.numero_factura,
        }
        for factura in db.scalars(
            select(models.Factura).where(
                models.Factura.explotacion_id == explotacion.id,
                models.Factura.huella == huella,
            )
        )
    ]


def _como_se_dice_el_duplicado(decision: dict) -> str:
    """El aviso del duplicado, **con el papel que ya estaba y dónde está**.

    Dice qué había antes y de cuándo es, que es lo que permite decidir sin miedo: un «ya lo tienes» a
    secas obliga al agricultor a buscar entre sus papeles cuál de todos ellos es.
    """
    ya_estaba = decision.get("ya_estaba") or {}
    if decision.get("donde") == "una_factura_de_compra":
        return textos.mensaje(
            "T08_el_mismo_papel_esta_en_una_factura",
            quien=ya_estaba.get("titulo") or textos.BANDEJA["no_consta"],
            numero=ya_estaba.get("numero_factura") or textos.BANDEJA["no_consta"],
        )
    return textos.mensaje(
        "T08_el_mismo_papel_ya_estaba",
        titulo=ya_estaba.get("titulo") or textos.BANDEJA["no_consta"],
        cuando=_cuando(ya_estaba.get("creado_en")) or textos.BANDEJA["no_consta"],
    )


# ==========================================================================
# La bandeja y la subida
# ==========================================================================


def _los_papeles_de_la_bandeja(
    db: Db, explotacion, *, estado: str, tipo: str | None, texto: str | None
) -> list:
    """Los papeles que se están mirando, ya filtrados.

    El filtro de texto se hace **en memoria y no en SQL** a propósito: lo que se busca es por el
    título y por el «de quién» sin acentos ni mayúsculas («albaran» tiene que encontrar «Albarán»), y
    eso es una comparación de las palabras del agricultor, no del motor de la base.
    """
    consulta = select(models.DocumentoAnexo).where(
        models.DocumentoAnexo.explotacion_id == explotacion.id,
        models.DocumentoAnexo.anulado.is_(False),
    )
    if estado == "sin_revisar":
        consulta = consulta.where(
            models.DocumentoAnexo.estado_revision.in_(bandeja.ESTADOS_SIN_REVISAR)
        )
    elif estado and estado != "todos":
        if not bandeja.es_un_estado(estado):
            raise HTTPException(
                status_code=422,
                detail=textos.mensaje(
                    "T08_ese_estado_no_existe", estados=", ".join(bandeja.ESTADOS)
                ),
            )
        consulta = consulta.where(models.DocumentoAnexo.estado_revision == estado)
    if tipo:
        consulta = consulta.where(models.DocumentoAnexo.tipo == tipo)
    papeles = list(
        db.scalars(
            consulta.order_by(
                models.DocumentoAnexo.creado_en.desc(), models.DocumentoAnexo.id.desc()
            )
        )
    )
    if texto:
        papeles = [
            papel
            for papel in papeles
            if bandeja.se_parece_a_lo_que_se_busca(texto, papel.titulo, papel.quien, papel.notas)
        ]
    return papeles


def _los_papeles_que_cuelgan_de(db: Db, explotacion, papeles: list, clase: str | None, entidad_id: int | None) -> list:
    """**Los papeles enlazados con algo concreto** (CRM-06, 14/10/2026).

    POR QUE EXISTE. La bandeja filtraba por estado, por tipo de papel y por texto, y **por nada de aquello con
    lo que un papel esta enlazado**. Para ver los papeles de una tierra habia que traerse la bandeja entera y
    cruzarla en la pantalla — que es justo lo contrario de lo que este proyecto hace: **lo que el servidor
    puede decir, no lo cruza la pantalla**.

    Y se dice **de esta finca**: `clase`/`entidad_id` **no son una clave ajena a proposito** (apuntan a varias
    tablas), asi que quien comprueba que la entidad sea de la finca es esto, como en la puerta de vincular.

    Si la clase no existe, se devuelve **la lista vacia** en vez de inventarse nada: quien pregunta por una
    clase que no hay no tiene papeles, y el aviso con la lista de las que hay lo da la puerta al vincular.
    """
    if not clase and entidad_id is None:
        return papeles
    if clase and not bandeja.es_una_clase_de_vinculo(clase):
        return []
    suyos = db.execute(
        select(models.VinculoDeDocumento.documento_id).where(
            models.VinculoDeDocumento.explotacion_id == explotacion.id,
            *( [models.VinculoDeDocumento.clase == clase] if clase else [] ),
            *( [models.VinculoDeDocumento.entidad_id == entidad_id] if entidad_id is not None else [] ),
        )
    ).scalars().all()
    enlazados = set(suyos)
    return [papel for papel in papeles if getattr(papel, "id", None) in enlazados]


@router.get("/bandeja", response_model=LaBandejaSalida)
def la_bandeja(
    explotacion: ExplotacionActual,
    db: Db,
    estado: str = "sin_revisar",
    tipo: str | None = None,
    texto: str | None = None,
    clase: str | None = None,
    entidad_id: int | None = None,
) -> LaBandejaSalida:
    """La bandeja entera, **reconstruida al abrirla**: es lo que hace que su dirección se pueda
    enlazar y recargar.

    Por defecto salen **los que están sin revisar**, que es lo que es una bandeja: lo que ha llegado y
    espera a alguien. Los confirmados se pueden pedir (`estado=confirmado` o `estado=todos`) porque
    «¿qué era ese papel que confirmé ayer?» es una pregunta normal.

    El orden es **del más nuevo al más viejo y por cuándo se subió**, no por la fecha del papel: esto
    es una cola de lo que acaba de llegar, y una factura de marzo subida hoy está recién llegada.
    """
    b = textos.BANDEJA
    papeles = _los_papeles_de_la_bandeja(db, explotacion, estado=estado, tipo=tipo, texto=texto)
    papeles = _los_papeles_que_cuelgan_de(db, explotacion, papeles, clase, entidad_id)
    cuantos_candidatos = _cuantos_candidatos(db, explotacion)
    salida = [
        _como_sale_un_papel(db, explotacion, papel, cuantos_candidatos) for papel in papeles
    ]
    return LaBandejaSalida(
        textos=b,
        papeles=salida,
        cuantos=len(salida),
        sin_revisar=len([papel for papel in salida if papel.sin_revisar]),
        sin_decir_de_que_es=len(
            [papel for papel in salida if papel.estado == bandeja.RECIEN_SUBIDO]
        ),
        resumen=textos.con_cuenta(b, "cuantos", len(salida)) if salida else b["sin_papeles"],
        tipos=[
            {"valor": cada_uno, "etiqueta": bandeja.etiqueta_de_papel(cada_uno)}
            for cada_uno in bandeja.TIPOS_DE_PAPEL
        ],
        estados=[
            {"valor": "sin_revisar", "etiqueta": b["sin_revisar"]},
            *[
                {"valor": cada_uno, "etiqueta": b[bandeja.clave_del_estado(cada_uno)]}
                for cada_uno in bandeja.ESTADOS
            ],
            {"valor": "todos", "etiqueta": b["todos_los_estados"]},
        ],
        clases=[
            {"valor": clase, "etiqueta": b[bandeja.clave_de_la_clase(clase)]}
            for clase in bandeja.CLASES_DE_VINCULO
        ],
    )


@router.post("/bandeja/comprobar", response_model=ElFicheroComprobadoSalida)
async def comprobar_el_fichero(
    explotacion: ExplotacionActual,
    db: Db,
    fichero: UploadFile = File(...),
) -> ElFicheroComprobadoSalida:
    """Lee el fichero, le calcula la huella y dice **si ese mismo papel ya estaba**. No escribe nada.

    Es la puerta que hace que el duplicado se diga **antes de apuntarlo**: aquí no se ha creado
    ninguna fila ni se ha guardado ningún fichero, así que el agricultor puede decidir con el dato
    delante («este mismo papel ya lo tienes: la factura del abono, del 3 de octubre») sin que nada
    haya cambiado todavía.
    """
    contenido, _tipo = await adjuntos.leer_el_fichero(fichero, adjuntos.TIPOS_DOCUMENTO)
    huella = bandeja.huella_de(contenido)
    decision = bandeja.decision_sobre_el_duplicado(
        huella,
        papeles=_los_papeles_con_la_huella(db, explotacion, huella),
        facturas=_las_facturas_con_la_huella(db, explotacion, huella),
    )
    ya_estaba = decision.get("ya_estaba") or {}
    return ElFicheroComprobadoSalida(
        huella=huella,
        bytes=len(contenido),
        texto_tamano=bandeja.describe_el_tamano(len(contenido)),
        nombre_del_fichero=(fichero.filename or "")[:200],
        tipo_del_fichero=(fichero.content_type or "")[:120],
        ya_estaba=bool(decision.get("duplicado")),
        donde=decision.get("donde"),
        el_que_ya_estaba=(
            {
                "id": ya_estaba.get("id"),
                "titulo": ya_estaba.get("titulo") or "",
                "numero_factura": ya_estaba.get("numero_factura") or "",
                "texto_subido": _cuando(ya_estaba.get("creado_en")),
            }
            if ya_estaba
            else None
        ),
        que_hacer=_como_se_dice_el_duplicado(decision) if decision.get("duplicado") else "",
    )


@router.post(
    "/bandeja/subir", response_model=LoQueHaPasadoSalida, status_code=status.HTTP_201_CREATED
)
async def subir_a_la_bandeja(
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    fichero: UploadFile = File(...),
    tipo: str | None = Form(default=None),
    titulo: str | None = Form(default=None),
    fecha: str | None = Form(default=None),
    quien: str | None = Form(default=None),
) -> LoQueHaPasadoSalida:
    """Sube un papel a la bandeja: **el fichero se guarda tal y como llegó**, con su huella.

    Tres cosas que hace y tres que no:

    * **Guarda el original** con el nombre que decide el programa (`app/adjuntos.py`) y calcula su
      huella. El nombre que manda el navegador se guarda **solo para enseñarlo**.
    * **No crea dos fichas del mismo papel**: si esa huella ya está, se contesta 409 **sin escribir
      nada** y se dice cuál era el que ya estaba.
    * **No lee el papel.** Leer es una puerta aparte (`/leer`) y lo que sale de ella es una propuesta:
      subir un papel no puede meter ningún dato en el cuaderno.

    El tipo es opcional: si no se dice, el papel nace **recién subido** y la bandeja pide que se diga
    de qué es. Si se dice, nace clasificado y se archiva en la carpeta que le toca por su tipo (una
    sugerencia: en «los papeles» se puede cambiar de sitio).
    """
    if tipo and not bandeja.es_un_tipo_de_papel(tipo):
        raise HTTPException(
            status_code=422,
            detail=textos.mensaje("T08_ese_tipo_no_existe", tipos=", ".join(bandeja.TIPOS_DE_PAPEL)),
        )
    try:
        fecha_del_papel = dt.date.fromisoformat(bandeja.fecha_escrita(fecha)) if fecha else None
    except bandeja.DatoQueNoVale as fallo:
        raise HTTPException(status_code=422, detail=textos.mensaje(fallo.clave)) from fallo

    contenido, _tipo_del_fichero = await adjuntos.leer_el_fichero(fichero, adjuntos.TIPOS_DOCUMENTO)
    huella = bandeja.huella_de(contenido)
    decision = bandeja.decision_sobre_el_duplicado(
        huella,
        papeles=_los_papeles_con_la_huella(db, explotacion, huella),
        facturas=_las_facturas_con_la_huella(db, explotacion, huella),
    )
    if decision.get("duplicado"):
        # **No se ha escrito nada**: ni fila, ni fichero en disco. Es la regla del ticket («subir dos
        # veces el mismo papel no crea dos fichas») y por eso la comprobación va antes que todo lo demás.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_como_se_dice_el_duplicado(decision)
        )

    # El alta del papel y la subida del fichero **se hacen con las puertas que ya existen**: tener dos
    # caminos que escriben ficheros en disco sería tener dos sitios donde equivocarse con las rutas, y
    # la comprobación del tipo, de la campaña y del tamaño se hereda de allí.
    tipo_del_papel = tipo or "otros"
    guardado = documentos_api.crear(
        DocumentoEntrada(
            titulo=bandeja.titulo_por_defecto(titulo or fichero.filename, tipo_del_papel),
            tipo=tipo_del_papel,
            carpeta=bandeja.carpeta_sugerida_para(tipo_del_papel)
            or documentos_api.CARPETA_POR_DEFECTO,
            fecha=None,
            quien=(quien or "").strip() or None,
        ),
        explotacion,
        db,
    )
    # El fichero se rebobina porque se ha leído entero para calcular la huella: sin esto, la puerta de
    # subida leería cero bytes y guardaría un papel vacío.
    fichero.file.seek(0)
    await documentos_api.subir_fichero(
        documento_id=guardado.id, explotacion=explotacion, db=db, fichero=fichero
    )

    papel = _el_papel(db, explotacion, guardado.id)
    papel.huella = huella
    papel.estado_revision = bandeja.estado_al_subirlo(tipo)
    # La fecha y el «de quién» pueden venir del formulario de la subida, que es lo que permite apuntar
    # un papel sin leerlo. Son **lo que el agricultor ha escrito**, no lo que el programa ha leído.
    if fecha_del_papel:
        papel.fecha = fecha_del_papel
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="subir_a_la_bandeja",
        datos={"huella": huella, "bytes": papel.fichero_bytes, "tipo": papel.tipo},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, [textos.mensaje("T08_papel_en_la_bandeja")])


@router.get("/bandeja/candidatos", response_model=LosCandidatosSalida)
def los_candidatos(
    explotacion: ExplotacionActual, db: Db, clase: str, texto: str | None = None
) -> LosCandidatosSalida:
    """Con qué se puede enlazar un papel: las cosas que **ya existen** en el cuaderno.

    Va aparte de la ficha porque un agricultor puede tener cientos de gastos y no se le pueden mandar
    todos en cada apertura: se piden los de la clase que está mirando y, si no encuentra el suyo,
    escribe parte del nombre. Lo que se devuelve viene **con su nombre ya compuesto**: la pantalla no
    enseña identificadores.
    """
    if not bandeja.es_una_clase_de_vinculo(clase):
        raise HTTPException(
            status_code=422,
            detail=textos.mensaje("T08_esa_clase_no_existe", clases=", ".join(bandeja.CLASES_DE_VINCULO)),
        )
    todos = _los_candidatos_de_una_clase(db, explotacion, clase)
    filtrados = [
        candidato for candidato in todos if bandeja.se_parece_a_lo_que_se_busca(texto, candidato["texto"])
    ]
    return LosCandidatosSalida(
        clase=clase,
        etiqueta_clase=textos.BANDEJA[bandeja.clave_de_la_clase(clase)],
        # **El valor de cada opción lleva la clase y el identificador** (`gasto:12`), como en la
        # conciliación del banco, y no solo el número. No es un capricho: así lo que se elige en el
        # desplegable lleva consigo **de qué es**, y el botón de enlazar no tiene que ir a preguntárselo a
        # otro campo de la pantalla, que podría haber cambiado después de elegir.
        items=[
            {"valor": f"{clase}:{candidato['id']}", "texto": candidato["texto"]}
            for candidato in filtrados[:MAXIMO_DE_CANDIDATOS]
        ],
        cuantos=len(filtrados),
        truncado=len(filtrados) > MAXIMO_DE_CANDIDATOS,
        sin_candidatos="" if filtrados else textos.mensaje("T08_no_hay_nada_que_enlazar"),
    )


def _los_candidatos_de_una_clase(db: Db, explotacion, clase: str) -> list[dict]:
    """Los candidatos de una clase, del más nuevo al más viejo y con su nombre ya escrito."""
    etiqueta = textos.BANDEJA[bandeja.clave_de_la_clase(clase)]
    candidatos: list[dict] = []

    def anade(valor: int, *partes) -> None:
        candidatos.append(
            {
                "id": valor,
                "texto": " · ".join([etiqueta, *[str(parte) for parte in partes if parte]]),
            }
        )

    if clase == bandeja.COMPRA:
        for factura in db.scalars(
            select(models.Factura)
            .where(
                models.Factura.explotacion_id == explotacion.id,
                models.Factura.anulada.is_(False),
            )
            .order_by(models.Factura.fecha.desc().nullslast(), models.Factura.id.desc())
        ):
            anade(factura.id, factura.proveedor, factura.numero_factura, _una_fecha(factura.fecha))
    elif clase == bandeja.GASTO:
        for gasto in db.scalars(
            select(models.Gasto)
            .where(models.Gasto.explotacion_id == explotacion.id, models.Gasto.anulado.is_(False))
            .order_by(models.Gasto.fecha.desc().nullslast(), models.Gasto.id.desc())
        ):
            anade(gasto.id, gasto.concepto, gasto.proveedor, _una_fecha(gasto.fecha))
    elif clase == bandeja.VENTA:
        for venta in db.scalars(
            select(models.VentaDeCosecha)
            .where(
                models.VentaDeCosecha.explotacion_id == explotacion.id,
                models.VentaDeCosecha.anulado.is_(False),
            )
            .order_by(models.VentaDeCosecha.fecha.desc(), models.VentaDeCosecha.id.desc())
        ):
            anade(venta.id, venta.producto, venta.comprador, _una_fecha(venta.fecha))
    elif clase == bandeja.MAQUINA:
        for maquina in db.scalars(
            select(models.Maquina)
            .where(models.Maquina.explotacion_id == explotacion.id)
            .order_by(models.Maquina.nombre)
        ):
            anade(maquina.id, maquina.nombre, maquina.matricula)
    elif clase == bandeja.TRABAJO:
        # Un trabajo es **lo que se ha hecho** (`labores`): un papel demuestra algo que pasó, y de un
        # trabajo que todavía está previsto no hay nada que demostrar.
        for labor in db.scalars(
            select(models.Labor)
            .where(models.Labor.explotacion_id == explotacion.id, models.Labor.anulado.is_(False))
            .order_by(models.Labor.fecha.desc(), models.Labor.id.desc())
        ):
            anade(labor.id, _la_tierra(db, explotacion, labor.parcela_id), _una_fecha(labor.fecha))
    elif clase == bandeja.INSPECCION:
        for inspeccion in db.scalars(
            select(models.InspeccionDeMaquina)
            .where(
                models.InspeccionDeMaquina.explotacion_id == explotacion.id,
                models.InspeccionDeMaquina.anulado.is_(False),
            )
            .order_by(models.InspeccionDeMaquina.fecha.desc(), models.InspeccionDeMaquina.id.desc())
        ):
            maquina = _la_entidad(db, models.Maquina, inspeccion.maquina_id, explotacion.id)
            anade(inspeccion.id, maquina.nombre if maquina else "", _una_fecha(inspeccion.fecha))
    return candidatos


@router.get("/bandeja/{documento_id}", response_model=PapelDeLaBandejaSalida)
def la_ficha_de_un_papel(
    documento_id: int, explotacion: ExplotacionActual, db: Db
) -> PapelDeLaBandejaSalida:
    """La ficha de un papel: **el original a un lado y la propuesta al otro**.

    Se reconstruye entera al abrir su dirección, y por eso se puede enlazar, recargar y mandar a quien
    ayuda. También se puede abrir la de un papel ya confirmado: lo que se mira entonces es el papel,
    con su estado, y la pantalla dice que ya está en «los papeles».
    """
    return _como_sale_un_papel(db, explotacion, _el_papel(db, explotacion, documento_id))


# ==========================================================================
# Clasificar, leer, revisar, confirmar
# ==========================================================================


@router.post("/bandeja/{documento_id}/clasificar", response_model=LoQueHaPasadoSalida)
def clasificar_el_papel(
    documento_id: int, datos: dict, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Dice de qué es el papel. Es lo que saca un papel de «recién subido».

    **No pierde nada de lo que ya había**: si el papel tenía una lectura o unos datos aceptados, siguen
    ahí. Lo que sí cambia es el estado, que vuelve a «clasificado», así que hay que revisarlo otra vez
    antes de confirmarlo. Y es a propósito: si el papel resulta ser otra cosa de lo que se creía (un tique
    que era una factura, un contrato que era un albarán), lo que se había aceptado hay que mirarlo otra vez
    con eso en la cabeza. Lo contrario —dejar el papel confirmable con una revisión hecha para otro tipo de
    papel— sería dar por bueno algo que nadie ha vuelto a mirar.
    """
    papel = _el_papel(db, explotacion, documento_id)
    tipo = str((datos or {}).get("tipo") or "").strip()
    if not bandeja.es_un_tipo_de_papel(tipo):
        raise HTTPException(
            status_code=422,
            detail=textos.mensaje("T08_ese_tipo_no_existe", tipos=", ".join(bandeja.TIPOS_DE_PAPEL)),
        )
    anterior = papel.tipo
    papel.tipo = tipo
    papel.estado_revision = bandeja.estado_al_clasificar()
    # La carpeta es una sugerencia: solo se mueve si el agricultor no la había decidido ya (el papel
    # sigue en la carpeta por defecto de la bandeja).
    sugerida = bandeja.carpeta_sugerida_para(tipo)
    if sugerida and papel.carpeta == documentos_api.CARPETA_POR_DEFECTO:
        papel.carpeta = sugerida
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="clasificar_en_la_bandeja",
        datos={"antes": anterior, "ahora": tipo},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel)


@router.post("/bandeja/{documento_id}/leer", response_model=LoQueHaPasadoSalida)
async def leer_el_papel(
    documento_id: int, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Lee el papel y guarda **la propuesta**. No confirma nada y **no cambia el estado**.

    Cuatro decisiones que se ven en lo que se devuelve:

    * **El original se lee del disco, del fichero que se guardó**, y no de lo que mande el navegador:
      lo que se lee es lo que hay.
    * **La lectura se guarda como propuesta** (en su columna), no en los campos del papel. Subir,
      leer y confirmar son tres actos distintos, y entre el segundo y el tercero el papel tiene que
      seguir diciendo lo mismo que decía.
    * **Si el fichero del disco no es el que se subió, se para.** Comparar la huella antes de leer es
      lo que impide guardar la lectura de un fichero y apuntarla como si fuera de este papel.
    * **No se dice si la lectura es buena**: se guardan los avisos del lector y las dos únicas cosas
      que se pueden comprobar (si las líneas cuadran y si la base más el IVA da el total). El corpus
      para medirla no existe, y eso lo dice la pantalla, no un número inventado aquí.

    De un papel que este programa no sabe leer todavía (un contrato, un albarán) **se dice que no se
    puede**, y la propuesta se guarda con su motivo para que al volver a abrirlo se sepa por qué no
    hay nada y se puedan escribir los datos a mano.
    """
    papel = _el_papel(db, explotacion, documento_id)
    if not papel.fichero_ruta:
        raise HTTPException(
            status_code=409, detail=textos.mensaje("T08_sin_fichero_no_se_puede_leer")
        )

    avisos: list[str] = []
    if not bandeja.se_puede_leer(papel.tipo):
        propuesta = bandeja.propuesta_sin_leer("T08_este_papel_no_lo_se_leer")
    else:
        contenido = adjuntos.ruta_segura(papel.fichero_ruta).read_bytes()
        if papel.huella and not bandeja.es_el_mismo_papel(bandeja.huella_de(contenido), papel.huella):
            raise HTTPException(status_code=409, detail=textos.mensaje("T08_el_fichero_ha_cambiado"))
        leida = facturas.leer_factura(
            contenido,
            nif_del_agricultor=explotacion.nif or "",
            productos=_la_cesta_del_agricultor(db, explotacion),
        )
        propuesta = bandeja.propuesta_de_factura(leida)
        avisos = [_el_aviso_escrito(aviso) for aviso in leida.avisos]
    papel.propuesta = bandeja.a_json(propuesta)
    papel.como_se_leyo = propuesta.get("como_se_leyo") or None
    papel.propuesta_descartada = False
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="leer_el_papel",
        datos={"como_se_leyo": papel.como_se_leyo, "lineas": len(propuesta.get("lineas") or [])},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, avisos)


def _la_cesta_del_agricultor(db: Db, explotacion) -> list[dict]:
    """Los productos que el agricultor tiene apuntados, para que la lectura los reconozca.

    Se le pasan al lector porque es lo que convierte una lectura de números en algo que sirve («esta
    línea es el Glifosato que ya tienes en la cesta»). Van como diccionarios sencillos porque es lo
    que el lector espera, y así esta pantalla no arrastra el modelo entero del almacén.
    """
    return [
        {
            "id": producto.id,
            "nombre_comercial": producto.nombre_comercial,
            "numero_registro": producto.numero_registro,
        }
        for producto in db.scalars(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == explotacion.id
            )
        )
    ]


@router.post("/bandeja/{documento_id}/revisar", response_model=LoQueHaPasadoSalida)
def revisar_la_propuesta(
    documento_id: int, datos: dict, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Guarda **lo que el agricultor acepta** de la lectura. Aquí es donde lo leído se vuelve suyo.

    Se puede hacer con la lectura delante (aceptando lo que propone, corregido o no) o **a mano**,
    cuando el papel no se ha podido leer: en los dos casos lo que se guarda es lo que él ha escrito, y
    el papel queda en «propuesta revisada», que **no es confirmado**.

    Los campos del papel (`quien` y `fecha`) **todavía no se tocan**: eso pasa al confirmar, que es el
    acto en el que el agricultor dice «esto es lo que queda». Entre revisar y confirmar, el papel
    sigue diciendo lo que decía, y eso es lo que permite revisar hoy y confirmar mañana.
    """
    papel = _el_papel(db, explotacion, documento_id)
    try:
        aceptados = bandeja.campos_aceptados((datos or {}).get("campos"))
    except bandeja.DatoQueNoVale as fallo:
        raise HTTPException(status_code=422, detail=textos.mensaje(fallo.clave)) from fallo
    if not bandeja.hay_algo_aceptado(aceptados):
        raise HTTPException(status_code=422, detail=textos.mensaje("T08_no_has_aceptado_nada"))
    papel.datos_confirmados = bandeja.a_json(aceptados)
    papel.estado_revision = bandeja.estado_al_revisar()
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="revisar_la_propuesta",
        datos={"campos": aceptados},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, [textos.mensaje("T08_revisado_sin_confirmar")])


@router.post("/bandeja/{documento_id}/descartar", response_model=LoQueHaPasadoSalida)
def descartar_la_propuesta(
    documento_id: int, datos: dict, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Dice que la lectura no sirve. **No la borra**: queda guardada, con su motivo.

    Lo leído es un dato del programa aunque no se acepte: dentro de un año, «¿por qué escribí esto a
    mano?» se contesta mirando lo que el programa había leído y el motivo por el que se descartó. Y el
    estado vuelve a «clasificado»: el papel sigue sin revisar, que es la verdad.
    """
    papel = _el_papel(db, explotacion, documento_id)
    if not bandeja.se_puede_descartar_la_propuesta(
        hay_propuesta=bandeja.tiene_algo(_la_propuesta_guardada(papel)),
        hay_algo_aceptado=bandeja.hay_algo_aceptado(_lo_aceptado_guardado(papel)),
    ):
        raise HTTPException(
            status_code=409, detail=textos.mensaje("T08_no_hay_lectura_que_descartar")
        )
    motivo = str((datos or {}).get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=422, detail=textos.mensaje("T08_dime_por_que_no_sirve"))
    papel.propuesta_descartada = True
    papel.estado_revision = bandeja.estado_al_clasificar()
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="descartar_la_propuesta",
        datos={"motivo": motivo},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, [textos.mensaje("T08_lectura_descartada")])


@router.post("/bandeja/{documento_id}/confirmar", response_model=LoQueHaPasadoSalida)
def confirmar_el_papel(
    documento_id: int, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Confirma el papel: **lo aceptado pasa al papel**, con quién y cuándo.

    **Esta puerta no acepta campos, y es la decisión más importante del ticket.** Los campos se aceptan
    en `/revisar`. Si confirmar aceptara campos, «confirmar sin que nadie haya mirado la lectura»
    volvería a ser posible con una llamada bien hecha, y la regla «el programa propone y el agricultor
    confirma» dependería de que la pantalla se acordara de pedirlo. Así no depende de nadie: sin haber
    revisado, aquí se contesta 409 y se dice qué hacer.

    Lo que cambia al confirmar: los campos del papel (`quien` y `fecha`, que son los que el papel
    tiene), el estado, y quién y cuándo. Lo que **no cambia nunca**: el fichero, su nombre y **su
    huella**. El original es el original antes y después de confirmar.
    """
    papel = _el_papel(db, explotacion, documento_id)
    aceptado = _lo_aceptado_guardado(papel)
    if not bandeja.se_puede_confirmar(
        getattr(papel, "estado_revision", None) or "",
        hay_algo_aceptado=bandeja.hay_algo_aceptado(aceptado),
    ):
        raise HTTPException(status_code=409, detail=textos.mensaje("T08_hay_que_revisar_antes"))
    for campo, valor in bandeja.para_el_papel(aceptado).items():
        setattr(papel, campo, valor)
    papel.estado_revision = bandeja.CONFIRMADO
    papel.confirmado_en = dt.datetime.now()
    papel.confirmado_por_usuario_id = usuario.id
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="confirmar_el_papel",
        datos={"campos": aceptado, "huella": papel.huella},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, [textos.mensaje("T08_papel_confirmado")])


# ==========================================================================
# Enlazar, desenlazar y rectificar
# ==========================================================================


@router.post("/bandeja/{documento_id}/vincular", response_model=LoQueHaPasadoSalida)
def vincular_el_papel(
    documento_id: int, datos: dict, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Enlaza el papel con algo que **ya existe**: una compra, un gasto, una venta, una máquina, un
    trabajo o una inspección.

    **No crea nada.** Ni un gasto, ni una factura, ni una venta: el vínculo apunta a una fila que ya
    está en el cuaderno. Es la mitad del ticket: la bandeja no puede ser una segunda puerta por la que
    entren datos sin pasar por la pantalla que los pide con sus comprobaciones.

    Y **un papel puede estar enlazado con varias cosas a la vez** (una factura de gasóleo va con el
    gasto y con el tractor), así que no hay tope: lo único que no se admite es el mismo enlace dos
    veces.

    El único sitio donde además se escribe algo es la inspección: `InspeccionDeMaquina.documento_id`
    existe desde el T14 y es **el campo que enseña la ficha de la máquina**, así que enlazar un
    certificado con su inspección lo rellena. Si esa inspección ya trae otro papel, se dice en vez de
    pisarlo: el papel que demuestra una inspección es uno.
    """
    papel = _el_papel(db, explotacion, documento_id)
    clase = str((datos or {}).get("clase") or "").strip()
    entidad_id = (datos or {}).get("entidad_id")
    if not bandeja.es_una_clase_de_vinculo(clase):
        raise HTTPException(
            status_code=422,
            detail=textos.mensaje(
                "T08_esa_clase_no_existe", clases=", ".join(bandeja.CLASES_DE_VINCULO)
            ),
        )
    if not entidad_id:
        raise HTTPException(status_code=422, detail=textos.mensaje("T08_dime_con_que_lo_enlazo"))
    enlazado = _la_entidad(db, _el_modelo_de_la_clase(clase), int(entidad_id), explotacion.id)
    if enlazado is None:
        raise HTTPException(status_code=404, detail=textos.mensaje("T08_eso_no_esta_en_tu_cuaderno"))
    if bandeja.ya_esta_vinculado(
        _los_vinculos_en_crudo(db, explotacion, papel.id), clase, entidad_id
    ):
        raise HTTPException(status_code=409, detail=textos.mensaje("T08_ya_estaba_enlazado"))

    if clase == bandeja.INSPECCION:
        if enlazado.documento_id and enlazado.documento_id != papel.id:
            raise HTTPException(
                status_code=409, detail=textos.mensaje("T08_esa_inspeccion_ya_tiene_papel")
            )
        enlazado.documento_id = papel.id

    db.add(
        models.VinculoDeDocumento(
            explotacion_id=explotacion.id,
            documento_id=papel.id,
            clase=clase,
            entidad_id=int(entidad_id),
            creado_por_usuario_id=usuario.id,
        )
    )
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="enlazar_el_papel",
        datos={"clase": clase, "entidad_id": int(entidad_id)},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, [textos.mensaje("T08_papel_enlazado")])


@router.post("/bandeja/{documento_id}/desvincular", response_model=LoQueHaPasadoSalida)
def desvincular_el_papel(
    documento_id: int, datos: dict, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Quita un enlace. **No borra nada de lo enlazado**: ni el gasto, ni la factura, ni el papel.

    Lo que había queda escrito en la auditoría (quién, cuándo y con qué estaba enlazado), que es como
    este programa cumple la regla de «nada desaparece sin rastro»: la fila del vínculo se va —dejarla
    «quitada» sería arrastrar filas que ya no dicen nada y que contarían como dependencia del papel
    para siempre, impidiendo borrarlo con un motivo que ya no es verdad— y lo que había, no.
    """
    papel = _el_papel(db, explotacion, documento_id)
    clase = str((datos or {}).get("clase") or "").strip()
    entidad_id = (datos or {}).get("entidad_id")
    if not bandeja.es_una_clase_de_vinculo(clase) or not entidad_id:
        raise HTTPException(status_code=422, detail=textos.mensaje("T08_dime_que_enlace_quito"))
    vinculo = db.scalar(
        select(models.VinculoDeDocumento).where(
            models.VinculoDeDocumento.explotacion_id == explotacion.id,
            models.VinculoDeDocumento.documento_id == papel.id,
            models.VinculoDeDocumento.clase == clase,
            models.VinculoDeDocumento.entidad_id == int(entidad_id),
        )
    )
    if vinculo is None:
        raise HTTPException(status_code=404, detail=textos.mensaje("T08_ese_enlace_no_esta"))
    if clase == bandeja.INSPECCION:
        inspeccion = _la_entidad(db, models.InspeccionDeMaquina, int(entidad_id), explotacion.id)
        if inspeccion is not None and inspeccion.documento_id == papel.id:
            inspeccion.documento_id = None
    db.delete(vinculo)
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="desenlazar_el_papel",
        datos={"clase": clase, "entidad_id": int(entidad_id)},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, [textos.mensaje("T08_papel_desenlazado")])


@router.post("/bandeja/{documento_id}/rectificar", response_model=LoQueHaPasadoSalida)
def rectificar_a_otro_papel(
    documento_id: int, datos: dict, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db
) -> LoQueHaPasadoSalida:
    """Dice a qué papel rectifica este (la factura corregida rectifica a la anterior).

    **Las dos quedan**: la rectificada se marca —se deduce de que hay otra que la apunta— y sigue
    consultable, y la ficha dice cuál rectifica a cuál. Lo que no se hace es tapar ni borrar la
    rectificada: sin ella, la corrección no se puede entender, que es justo lo contrario de lo que
    hace una rectificativa.

    Y se comprueban las dos cosas que dejarían la cadena sin sentido: un papel **no se rectifica a sí
    mismo** ni puede cerrar un **círculo** (`bandeja.hay_ciclo`), que es lo que pasaría al equivocarse
    dos veces seguidas. Si el agricultor se equivocó de papel, vuelve a decirlo y apunta al bueno:
    rectificar es cambiar esta columna, y lo que había queda en la auditoría.
    """
    papel = _el_papel(db, explotacion, documento_id)
    al_que_rectifica = (datos or {}).get("rectifica_a_id")
    se_puede, motivo = bandeja.puede_rectificar_a(papel.id, al_que_rectifica)
    if not se_puede:
        raise HTTPException(status_code=422, detail=textos.mensaje(motivo))
    otro = _el_papel(db, explotacion, int(al_que_rectifica))
    if bandeja.hay_ciclo(_la_cadena_de_rectificaciones(db, explotacion), papel.id, otro.id):
        raise HTTPException(status_code=409, detail=textos.mensaje("T08_esto_haria_un_circulo"))
    anterior = papel.rectifica_a_id
    papel.rectifica_a_id = otro.id
    _el_rastro(
        db,
        explotacion.id,
        papel.id,
        accion="rectificar_a_otro_papel",
        datos={"antes": anterior, "ahora": otro.id},
        usuario_id=usuario.id,
    )
    db.commit()
    db.refresh(papel)
    return _lo_que_ha_pasado(db, explotacion, papel, [textos.mensaje("T08_rectifica_a_otro")])
