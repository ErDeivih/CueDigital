"""**El paquete preparatorio de la PAC, recinto por recinto** (CRM-09, 17/10/2026).

El contrato de la cola lo pide con estas palabras:

    Campaña -> compromisos elegidos -> recintos -> cultivos principales/secundarios -> evidencias -> evaluacion.
    ***Paquete preparatorio por recinto: referencias, superficie, cultivos, practica, documentos y cuestiones
    pendientes. No envio directo ni garantia de elegibilidad.***
    Aceptacion: ***fuente de otra campaña/comunidad no se aplica***; ***falta area/cultivo/evidencia ->
    incompleto***.

***Y lo que esta puerta NO hace, y es lo primero que hay que decir***: **no dice si nada es elegible.** *La
cola lo manda con esas palabras -«ninguna competencia autoriza usar su interpretacion como norma»-, y aqui no
hay ninguna fuente legal cargada, asi que el paquete lo **dice en voz alta** en vez de callarse.*

***Lo que si hace***: *recoger **por tierra** lo que el asesor necesita -la referencia, la superficie, lo que
se siembra, el ecorregimen y **lo que falta**- y resumir la finca **sin el denominador tramposo**.*

*Las tres piezas salen de `app/pac.py`, que existia **y no lo llamaba nadie***:

  · `tierra_sin_cultivo_no_se_pinta_de_verde` -***«tierra sin cultivo no desaparece para pintar verde»***:
    *el porcentaje va sobre **toda** la finca, y las hectareas que se quedan fuera **se dicen**-.*
  · `la_que_aplica` -***«fuente de otra campaña/comunidad no se aplica»***-.
  · y `el_porcentaje`, que **no da un cero cuando no hay denominador**.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .. import models, pac, superficies, textos
# ***`PuedeModificar` y `UsuarioActual` son DEPENDENCIAS, no parametros.*** *Con `from __future__ import
# annotations` sus nombres son texto, asi que si no se importan FastAPI no los resuelve y **los trata como
# parametros de consulta**: la puerta contestaba 422 pidiendo `usuario` y `puede_modificar` en la direccion.*
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual
from ..schemas import EscenarioDeLaPacEntrada, FotoDeLaPacEntrada

router = APIRouter(prefix="/api/pac", tags=["pac"])


def _la_campana(db, explotacion_id: int, campana_id: int | None):
    consulta = select(models.Campana).where(models.Campana.explotacion_id == explotacion_id)
    if campana_id is not None:
        return db.scalar(consulta.where(models.Campana.id == campana_id))
    return db.scalar(consulta.order_by(models.Campana.anio.desc()))


def _el_cultivo_de_la_tierra(cultivo) -> dict | None:
    """**Lo que se siembra en esa tierra esa campaña**, o `None` si no consta.

    *`None` no es un hueco que se pueda rellenar: es **una de las cosas que hacen incompleto el paquete**.*
    """
    if cultivo is None:
        return None
    return {
        "especie": cultivo.especie,
        "variedad": cultivo.variedad,
        "sistema": cultivo.sistema,
        "ecorregimen": cultivo.ecorregimen,
        "superficie_cultivada_ha": cultivo.superficie_cultivada_ha,
    }


def _lo_que_falta(parcela, cultivo) -> list[str]:
    """***Las cuestiones pendientes de una tierra***, dichas con su clave.

    *Es la mitad del contrato*: *«falta area/cultivo/evidencia -> **incompleto**»*. *Una tierra sin superficie
    no es una tierra de cero hectareas, y una sin cultivo no es una tierra sin sembrar: es una tierra de la
    que **no consta**.*
    """
    # ***La regla vive en `pac.py`*** (18/10/2026): *la usa tambien **el escenario del año que viene**, y dos
    # copias de la misma regla acaban diciendo cosas distintas de la misma tierra.*
    return pac.lo_que_falta_para_la_pac(
        superficie_ha=parcela.superficie_ha,
        referencia=parcela.ref_sigpac,
        cultivo=None if cultivo is None else {"ecorregimen": cultivo.ecorregimen},
    )


@router.get("/paquete")
def el_paquete_de_la_pac(
    explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> dict:
    """**El paquete para el asesor: una entrada por recinto, y lo que falta dicho.**"""
    la_campana = _la_campana(db, explotacion.id, campana_id)
    el_anio = la_campana.anio if la_campana is not None else None

    tierras = list(
        db.scalars(select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id))
    )
    # **El cultivo de esa campaña, por tierra.** *Sin campaña no hay cultivo que buscar, y entonces **todas**
    # las tierras salen con la cuestion pendiente -que es la verdad, no un hueco-.*
    por_tierra: dict[int, models.ParcelaCultivo] = {}
    if la_campana is not None:
        for cultivo in db.scalars(
            select(models.ParcelaCultivo).where(
                models.ParcelaCultivo.explotacion_id == explotacion.id,
                models.ParcelaCultivo.campana_id == la_campana.id,
            )
        ):
            por_tierra[cultivo.parcela_id] = cultivo

    las_tierras = []
    for parcela in tierras:
        cultivo = por_tierra.get(parcela.id)
        falta = _lo_que_falta(parcela, cultivo)
        las_tierras.append(
            {
                "parcela_id": parcela.id,
                "alias": parcela.alias,
                "referencia": parcela.ref_sigpac,
                "superficie_ha": parcela.superficie_ha,
                # ***La del SIGPAC es otra cosa*** y se dice aparte: *lo que mide el recinto y lo que la
                # administracion tiene apuntado pueden no coincidir, y el asesor necesita las dos.*
                #
                # *No se llama «declarada»: **no hay ninguna columna de superficie declarada** -se busco, y
                # `Parcela` tiene `superficie_ha` y `superficie_sigpac_ha`-. Inventar una tercera habria sido
                # enseñar un dato que no existe, que es justo lo que esta casa no hace.*
                "superficie_sigpac_ha": parcela.superficie_sigpac_ha,
                "cultivo": _el_cultivo_de_la_tierra(cultivo),
                "falta": falta,
                # ***`completa` es la pregunta del asesor***: *¿puedo llevar esto a la declaracion o me falta
                # algo?*
                "completa": not falta,
            }
        )
    las_tierras.sort(key=lambda una: (una["completa"], una["alias"] or ""))

    # ── El resumen, **sin el denominador tramposo** ──
    la_superficie = superficies.la_superficie_de_la_finca(tierras)
    con_cultivo: float | None
    superficies_cultivadas = [
        cultivo.superficie_cultivada_ha for cultivo in por_tierra.values()
    ]
    if any(una is None for una in superficies_cultivadas):
        # *A una tierra le falta la superficie cultivada: **el total no se sabe**.*
        con_cultivo = None
    else:
        con_cultivo = round(sum(float(una) for una in superficies_cultivadas), 4)

    if la_superficie["total"] is None or con_cultivo is None:
        el_resumen = {
            "de_que": "superficie con cultivo sobre el total de la finca",
            "unidad": "ha",
            "numerador": con_cultivo,
            "denominador": la_superficie["total"],
            # ***`None`, no cero***: *cero por ciento y «no se sabe» son cosas distintas, y un cero pinta un
            # mapa de verde que no es verdad.*
            "porcentaje": None,
            "sin_cultivo": None,
            "se_queda_fuera": None,
            "aviso": textos.PAC["falta_superficie"],
        }
    else:
        el_resumen = pac.tierra_sin_cultivo_no_se_pinta_de_verde(
            superficie_total=la_superficie["total"], superficie_con_cultivo=con_cultivo
        )

    # ── La fuente legal ──
    # ***Aqui no hay ninguna cargada***, *y se dice: la cola manda consultar el BOE, el FEGA, el MAPA y la
    # Junta **al implementar las reglas**, y sin esa fuente este programa no puede decir si algo es elegible.*
    # *Lo que si hace `pac.la_que_aplica` es **no aplicar** una fuente de otra campaña o de otra comunidad el
    # dia que la haya.*
    la_fuente = pac.la_que_aplica(
        [],
        ambito="autonomico",
        campana=el_anio or 0,
        cuando=dt.date.today(),
    )
    return {
        "textos": textos.PAC,
        "campana_id": la_campana.id if la_campana is not None else None,
        "campana_anio": el_anio,
        # ***`None` es «no hay fuente», y con eso ya se sabe lo que se puede afirmar.***
        "la_fuente": la_fuente,
        "aviso_de_la_fuente": textos.PAC["sin_fuente"] if la_fuente is None else "",
        "las_tierras": las_tierras,
        "el_resumen": el_resumen,
        "las_incompletas": sum(1 for una in las_tierras if not una["completa"]),
        # ***Y la advertencia, en la respuesta y no solo en la pantalla***: *«no envio directo ni garantia de
        # elegibilidad» tiene que viajar con el paquete, porque el paquete se puede guardar y reenviar.*
        "no_es_garantia": textos.PAC["no_es_garantia"],
    }


# -----------------------------------------------------------------------------------------------------------
# ***El escenario del año que viene***
# -----------------------------------------------------------------------------------------------------------


# -----------------------------------------------------------------------------------------------------------
# ***La PAC: el escenario, las fotos y el historial*** (18/10/2026, segunda entrega)
# -----------------------------------------------------------------------------------------------------------


def _los_cambios(cambios) -> dict:
    """*Los cambios, en la forma que entiende `pac.el_escenario`.* *Ya vienen validados por el esquema, asi que
    aqui solo se quitan los `None`: **lo que no se manda no se cambia**.*"""
    return {
        int(la_parcela): el_cambio.model_dump(exclude_none=True)
        for la_parcela, el_cambio in (cambios or {}).items()
    }


def _el_escenario_de_ahora(explotacion, db, *, anio: int, campana_id, cambios) -> dict:
    """***El escenario que sale de la finca AHORA.*** *Con su huella de la fuente, que es lo que lo identifica.*"""
    el_paquete = el_paquete_de_la_pac(explotacion=explotacion, db=db, campana_id=campana_id)
    las_suyas = {uno["parcela_id"] for uno in el_paquete.get("las_tierras") or []}
    los_ajenos = sorted(set(cambios or {}) - las_suyas)
    if los_ajenos:
        # ***Se dice, no se ignora***: *evaluar un recinto que no es de la finca seria evaluar otra cosa.*
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": textos.PAC["esos_recintos_no_son_tuyos"],
                "los_que_no_son_suyos": los_ajenos,
            },
        )
    return pac.el_escenario(el_paquete, anio=anio, cambios=cambios)


@router.post("/escenario")
def el_escenario_del_ano_que_viene(
    datos: EscenarioDeLaPacEntrada, explotacion: ExplotacionActual, db: Db
) -> dict:
    """***Un escenario del año que viene***: *una **hipotesis**, separada de lo declarado y de lo realizado.*

    *El contrato lo pide asi: «escenario siguiente año separado de lo declarado y de lo realizado. Comparar
    alternativas **sin consumir**».*

    ***Esta puerta no escribe nada***: *lee el paquete -que es lo que la finca tiene de verdad-, le aplica los
    cambios **en memoria** y devuelve otra cosa, dicha con su capa. **Editar el escenario no cambia el historial
    porque no hay historial que tocar.***

    ***Y devuelve `huella_de_la_fuente`***: *la identidad de lo que se ha evaluado. **Quien enseñe esto tiene que
    mandarla al guardar**, y si la finca cambia mientras tanto, el servidor lo dira en vez de sustituirlo.*

    *Es `POST` y no `GET` porque lo que se manda es **un juego de cambios por recinto**, que no cabe en una
    direccion; **no porque escriba**.*
    """
    los_cambios = _los_cambios(datos.cambios)
    el_suyo = _el_escenario_de_ahora(
        explotacion, db, anio=datos.anio, campana_id=datos.campana_id, cambios=los_cambios
    )
    la_contestacion = {"escenario": el_suyo, "textos": textos.PAC}
    if datos.contra is not None:
        el_otro = _el_escenario_de_ahora(
            explotacion, db, anio=datos.anio, campana_id=datos.campana_id, cambios=_los_cambios(datos.contra)
        )
        la_contestacion["contra"] = el_otro
        la_contestacion["comparacion"] = pac.comparar_alternativas(el_suyo, el_otro)
    return la_contestacion


def _la_identidad_de(la_foto) -> dict:
    """***La identidad completa de una foto, y sus enlaces*** (18/10/2026).

    *La revision demostro que **`GET /foto/{version}` no identificaba nada** con dos años: la version 1 de 2027 y
    la de 2028 se contestaban la misma. **La direccion tiene que llevar el año** -o el id-, y aqui se devuelven
    las dos, para que quien la guarde no tenga que componerlas.*
    """
    return {
        "id": la_foto.id,
        "anio": la_foto.anio,
        "version": la_foto.version,
        "huella": la_foto.huella,
        "creada_en": la_foto.creada_en,
        # ***Los enlaces, con el año dentro***: *una version sin su año no identifica nada.*
        "el_detalle": f"/api/pac/foto/{la_foto.anio}/{la_foto.version}",
        "el_fichero": f"/api/pac/foto/{la_foto.anio}/{la_foto.version}/exportar",
        "por_id": f"/api/pac/foto/id/{la_foto.id}",
        "es_hipotesis": True,
        "no_es_garantia": True,
    }


def _la_foto_por_anio_y_version(db, explotacion, anio: int, version: int):
    la_foto = db.scalar(
        select(models.FotoDeLaPac).where(
            models.FotoDeLaPac.explotacion_id == explotacion.id,
            models.FotoDeLaPac.anio == anio,
            models.FotoDeLaPac.version == version,
        )
    )
    if la_foto is None:
        raise HTTPException(
            status_code=404,
            detail=f"No hay ninguna foto de {anio} en la version {version}.",
        )
    return la_foto


def _la_foto_por_id(db, explotacion, foto_id: int):
    la_foto = db.scalar(
        select(models.FotoDeLaPac).where(
            models.FotoDeLaPac.explotacion_id == explotacion.id,
            models.FotoDeLaPac.id == foto_id,
        )
    )
    if la_foto is None:
        raise HTTPException(status_code=404, detail="Esa foto no es de esta finca.")
    return la_foto


@router.post("/foto")
def guardar_la_foto_de_la_pac(
    datos: FotoDeLaPacEntrada,
    explotacion: ExplotacionActual,
    usuario: UsuarioActual,
    db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """***Guarda lo que se le ha ensenado al asesor***, y **solo si sigue siendo lo mismo**.

    ### ***El defecto que esto cierra***

    *Antes se recalculaba al guardar: *el agricultor evaluaba una tierra, **cambiaba el alias de esa tierra
    despues**, y guardaba. **La foto se llevaba el alias nuevo sin decir nada**, y lo que quedaba guardado **no era
    lo que habia visto**.

    ***Ahora se manda `huella_de_la_fuente`*** -la que devolvio el escenario que se mostro- y se compara con la de
    ahora:

      · **coincide**: se guarda **lo que el servidor calcula ahora**, que es exactamente lo que se le mostro;
      · **no coincide**: **409**, con lo que se evaluo, lo que hay y **`se_puede_recalcular`**. *No se sustituye
        nada en silencio.*
      · **y sin huella** se guarda lo de ahora, que es lo que quieren los guiones; se dice en el docstring.

    ***Y no se acepta el contenido del cliente***: *un navegador puede mandar cualquier cosa. Lo que se guarda lo
    calcula **el servidor**, y la huella solo dice «esto es lo que te ensene».*

    ### La numeracion

    *`max+1` dentro del año. **Dos guardados a la vez** pueden pedir el mismo numero: el indice unico lo corta, se
    reintenta con el siguiente y **no se pisa ninguna version**; si no cabe, **409 dicho**, nunca un 500.*
    """
    los_cambios = _los_cambios(datos.cambios)
    el_suyo = _el_escenario_de_ahora(
        explotacion, db, anio=datos.anio, campana_id=datos.campana_id, cambios=los_cambios
    )
    la_huella_de_ahora = el_suyo["huella_de_la_fuente"]

    if datos.huella_de_la_fuente and datos.huella_de_la_fuente != la_huella_de_ahora and not datos.recalcular:
        # ***El conflicto, dicho***: *lo que se evaluo, lo que hay, y la salida.*
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": textos.PAC["la_finca_cambio_al_guardar"],
                "huella_que_se_evaluo": datos.huella_de_la_fuente,
                "huella_de_ahora": la_huella_de_ahora,
                "se_puede_recalcular": True,
                "no_se_ha_guardado_nada": textos.PAC["no_se_ha_guardado_nada"],
                "lo_que_hay_ahora": el_suyo,
            },
        )

    el_texto = json.dumps(el_suyo, ensure_ascii=False, sort_keys=True)
    la_huella = hashlib.sha256(el_texto.encode("utf-8")).hexdigest()

    # ***Y si ya hay una foto con ESTE MISMO contenido, se devuelve esa*** (19/10/2026).
    #
    # *El contrato pide «idempotencia tras respuesta perdida», y aqui pasaba lo contrario: **el movil guardaba, se
    # perdia la respuesta, reintentaba, y quedaba una segunda version con el MISMO contenido**. No era corrupcion
    # -`max+1` y el indice unico aguantaban-, pero **el historial se llenaba de fotos iguales** y el agricultor no
    # sabia cual ensenar.*
    #
    # ***La huella es del contenido, asi que dos evaluaciones identicas son la misma foto.*** *Si quiere una
    # version nueva, cambia algo -que es lo que una version nueva significa-.*
    for _intento in range(5):
        # ***La huella se mira DENTRO del intento, no antes*** (19/10/2026): *dos guardados simultaneos del mismo
        # contenido **no se ven** al mirar -los dos miran antes de insertar-, el perdedor choca con el indice unico
        # y reintenta. **Si la comprobacion esta fuera, el reintento no vuelve a mirar y crea la version 2 con el
        # mismo contenido** -que es justo lo que se venia a evitar-.*
        #
        # *Aqui, en cambio, cuando el perdedor reintenta **la otra ya esta commiteada**, la encuentra y devuelve
        # esa. Se vio porque la prueba de concurrencia daba `{1, 2}` unas veces y `{1}` otras: **una prueba que a
        # veces pasa es una prueba que no prueba**.*
        la_que_ya_estaba = db.scalar(
            select(models.FotoDeLaPac).where(
                models.FotoDeLaPac.explotacion_id == explotacion.id,
                models.FotoDeLaPac.anio == datos.anio,
                models.FotoDeLaPac.huella == la_huella,
            )
        )
        if la_que_ya_estaba is not None:
            # *`ya_estaba` va en la respuesta para que la pantalla lo diga: **no es un fallo, es la misma foto**.*
            return {**_la_identidad_de(la_que_ya_estaba), "ya_estaba": True}

        la_ultima = (
            db.scalar(
                select(func.max(models.FotoDeLaPac.version)).where(
                    models.FotoDeLaPac.explotacion_id == explotacion.id,
                    models.FotoDeLaPac.anio == datos.anio,
                )
            )
            or 0
        )
        la_foto = models.FotoDeLaPac(
            explotacion_id=explotacion.id,
            anio=datos.anio,
            version=la_ultima + 1,
            huella=la_huella,
            el_contenido=el_texto,
            usuario_id=usuario.id,
        )
        db.add(la_foto)
        try:
            db.commit()
        except IntegrityError:
            # ***Otra se guardo a la vez con el mismo numero***: *no es un error del programa, es una carrera; se
            # reintenta con el siguiente. **Ninguna version se pisa**, porque el indice unico no deja.*
            db.rollback()
            continue
        db.refresh(la_foto)
        return {**_la_identidad_de(la_foto), "ya_estaba": False}

    raise HTTPException(
        status_code=409,
        detail={
            "mensaje": textos.PAC["otra_foto_a_la_vez"],
            "no_se_ha_guardado_nada": textos.PAC["no_se_ha_guardado_nada"],
        },
    )


@router.get("/foto/historial")
def el_historial_de_las_fotos(
    explotacion: ExplotacionActual, db: Db, anio: int | None = None
) -> dict:
    """***Las fotos guardadas, de la mas nueva a la mas vieja.*** *Es lo que la pantalla llama «historial».*

    *Y no se puede borrar ni corregir una foto: **una version evaluada es un papel que se enseno**.*
    """
    consulta = select(models.FotoDeLaPac).where(
        models.FotoDeLaPac.explotacion_id == explotacion.id
    )
    if anio is not None:
        consulta = consulta.where(models.FotoDeLaPac.anio == anio)
    las_fotos = list(
        db.scalars(
            consulta.order_by(
                models.FotoDeLaPac.anio.desc(), models.FotoDeLaPac.version.desc()
            )
        )
    )
    return {
        "las_fotos": [_la_identidad_de(una) for una in las_fotos],
        "cuantas": len(las_fotos),
        "es_hipotesis": True,
        "no_es_garantia": True,
    }


@router.get("/foto/id/{foto_id}")
def la_foto_por_su_id(foto_id: int, explotacion: ExplotacionActual, db: Db) -> dict:
    """***Por su id***: *la identidad inmutable, que no depende de ningun año ni de contar versiones.*"""
    la_foto = _la_foto_por_id(db, explotacion, foto_id)
    return {**_la_identidad_de(la_foto), "el_escenario": json.loads(la_foto.el_contenido)}


@router.get("/foto/id/{foto_id}/exportar")
def exportar_la_foto_por_su_id(foto_id: int, explotacion: ExplotacionActual, db: Db) -> Response:
    """*El fichero de esa foto, por su id.*"""
    return _el_fichero_de_la_foto(_la_foto_por_id(db, explotacion, foto_id))


@router.get("/foto/{anio}/{version}")
def la_foto_guardada(anio: int, version: int, explotacion: ExplotacionActual, db: Db) -> dict:
    """***El detalle de la foto***, *identificada por **año y version**: una version sin su año no dice cual es.*"""
    la_foto = _la_foto_por_anio_y_version(db, explotacion, anio, version)
    return {**_la_identidad_de(la_foto), "el_escenario": json.loads(la_foto.el_contenido)}


@router.get("/foto/{anio}/{version}/exportar")
def exportar_la_foto(anio: int, version: int, explotacion: ExplotacionActual, db: Db) -> Response:
    """***El fichero, y es EXACTAMENTE la foto.***

    *El contrato lo pide asi: «**la exportacion coincide con el detalle y conserva la version evaluada**». **No se
    vuelve a calcular nada**: se lee el contenido guardado y se escribe.*

    *La cabecera lleva **la version, el año y la fecha**; y **no lleva ninguna columna de elegibilidad**, porque
    este programa no la afirma.*
    """
    return _el_fichero_de_la_foto(_la_foto_por_anio_y_version(db, explotacion, anio, version))


def _el_fichero_de_la_foto(la_foto) -> Response:
    """*El CSV de una foto guardada. **Una sola forma de escribirlo**, para que el id y el año den lo mismo.*"""
    el_escenario = json.loads(la_foto.el_contenido)
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(
        [
            f"version {la_foto.version}",
            f"año {la_foto.anio}",
            f"hecha {la_foto.creada_en}",
            f"huella {la_foto.huella[:16]}",
        ]
    )
    escritor.writerow(
        [
            "referencia", "alias", "superficie_ha", "especie", "variedad", "ecorregimen",
            "superficie_cultivada_ha", "completa", "falta",
        ]
    )
    for uno in el_escenario.get("los_recintos") or []:
        el_cultivo = uno.get("cultivo") or {}
        escritor.writerow(
            [
                uno.get("referencia") or "",
                uno.get("alias") or "",
                _un_numero_texto(uno.get("superficie_ha")),
                el_cultivo.get("especie") or "",
                el_cultivo.get("variedad") or "",
                el_cultivo.get("ecorregimen") or "",
                _un_numero_texto(el_cultivo.get("superficie_cultivada_ha")),
                "si" if uno.get("completa") else "no",
                " ".join(uno.get("falta") or []),
            ]
        )
    el_cuerpo = "\ufeff" + salida.getvalue()
    return Response(
        content=el_cuerpo.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="pac-{la_foto.anio}-v{la_foto.version}.csv"'
            )
        },
    )


def _un_numero_texto(valor) -> str:
    """*Un numero, o **la casilla en blanco** si no consta.* *Un `0` ahi seria decir que esa tierra tiene cero
    hectareas, que es lo contrario de «no consta».*"""
    return "" if valor is None else str(valor)
