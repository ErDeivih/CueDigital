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

from .. import models, pac, superficies, textos
# ***`PuedeModificar` y `UsuarioActual` son DEPENDENCIAS, no parametros.*** *Con `from __future__ import
# annotations` sus nombres son texto, asi que si no se importan FastAPI no los resuelve y **los trata como
# parametros de consulta**: la puerta contestaba 422 pidiendo `usuario` y `puede_modificar` en la direccion.*
from ..deps import Db, ExplotacionActual, PuedeModificar, UsuarioActual

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


@router.post("/escenario")
def el_escenario_del_ano_que_viene(
    datos: dict, explotacion: ExplotacionActual, db: Db, campana_id: int | None = None
) -> dict:
    """***Un escenario del año que viene***: *una **hipotesis**, separada de lo declarado y de lo realizado.*

    *El contrato lo pide asi: «escenario siguiente año separado de lo declarado y de lo realizado. Comparar
    alternativas **sin consumir**».*

    ***Esta puerta no escribe nada***: *lee el paquete -que es lo que la finca tiene de verdad-, le aplica los
    cambios que se le mandan **en memoria** y devuelve otra cosa, dicha con su capa. **Editar el escenario no
    cambia el historial porque no hay historial que tocar**, y comparar dos alternativas no consume ninguna.*

    *Es `POST` y no `GET` porque lo que se manda es **un juego de cambios por recinto**, que no cabe razonablemente
    en una direccion; **no porque escriba**.*

    *Y **no dice si es elegible**: un escenario no es una solicitud, y este programa **no envia nada**.*
    """
    el_paquete = el_paquete_de_la_pac(explotacion=explotacion, db=db, campana_id=campana_id)
    # *El año siguiente al de la campaña que se esta mirando. Si no hay campaña, se queda en el que digan.*
    el_anio = datos.get("anio") or ((el_paquete.get("campana_anio") or 0) + 1)

    el_suyo = pac.el_escenario(el_paquete, anio=el_anio, cambios=datos.get("cambios"))
    la_contestacion = {
        "escenario": el_suyo,
        # *Las palabras de la casa, las mismas del paquete: el escenario no inventa un idioma nuevo.*
        "textos": el_paquete.get("textos"),
    }
    if datos.get("contra") is not None:
        el_otro = pac.el_escenario(el_paquete, anio=el_anio, cambios=datos.get("contra"))
        la_contestacion["contra"] = el_otro
        la_contestacion["comparacion"] = pac.comparar_alternativas(el_suyo, el_otro)
    return la_contestacion


def _la_foto(db, explotacion, version: int) -> models.FotoDeLaPac:
    """*La foto de esa version, o 404: **no se inventa una foto que no existe**.*"""
    la_foto = db.scalar(
        select(models.FotoDeLaPac).where(
            models.FotoDeLaPac.explotacion_id == explotacion.id,
            models.FotoDeLaPac.version == version,
        )
    )
    if la_foto is None:
        raise HTTPException(status_code=404, detail=textos.PAC["sin_fuente"])
    return la_foto


@router.post("/foto")
def guardar_la_foto_de_la_pac(
    datos: dict, explotacion: ExplotacionActual, usuario: UsuarioActual, db: Db,
    puede_modificar: PuedeModificar,
) -> dict:
    """***Guarda lo que se le ha ensenado al asesor***, con su version y su fecha.

    *El escenario se calcula y se tira -que es lo correcto para **comparar**-, pero **ensenar** es otra cosa:
    hace falta que lo que se enseno **siga siendo lo mismo** dentro de un año. Eso es esta foto.*

    *Guarda **el contenido**, no la receta: si la finca cambia, la foto no. Y la `huella` dice cual es cual.*
    """
    el_paquete = el_paquete_de_la_pac(explotacion=explotacion, db=db, campana_id=datos.get("campana_id"))
    el_anio = int(datos.get("anio") or ((el_paquete.get("campana_anio") or 0) + 1))
    el_suyo = pac.el_escenario(el_paquete, anio=el_anio, cambios=datos.get("cambios"))
    el_texto = json.dumps(el_suyo, ensure_ascii=False, sort_keys=True)
    la_huella = hashlib.sha256(el_texto.encode("utf-8")).hexdigest()

    la_ultima = (
        db.scalar(
            select(func.max(models.FotoDeLaPac.version)).where(
                models.FotoDeLaPac.explotacion_id == explotacion.id,
                models.FotoDeLaPac.anio == el_anio,
            )
        )
        or 0
    )
    la_foto = models.FotoDeLaPac(
        explotacion_id=explotacion.id,
        anio=el_anio,
        version=la_ultima + 1,
        huella=la_huella,
        el_contenido=el_texto,
        usuario_id=usuario.id,
    )
    db.add(la_foto)
    db.commit()
    db.refresh(la_foto)
    return {
        "version": la_foto.version,
        "anio": la_foto.anio,
        "huella": la_foto.huella,
        "creada_en": la_foto.creada_en,
        "cuantos_recintos": len(el_suyo.get("los_recintos") or []),
        # ***Y lo que la foto NO es***, dicho con la misma claridad que el paquete.
        "es_hipotesis": True,
        "no_es_garantia": True,
        "toca_lo_guardado": False,
    }


@router.get("/foto/{version}")
def la_foto_guardada(version: int, explotacion: ExplotacionActual, db: Db) -> dict:
    """***El detalle de la foto***, *que es exactamente lo que se exporta.*"""
    la_foto = _la_foto(db, explotacion, version)
    return {
        "version": la_foto.version,
        "anio": la_foto.anio,
        "huella": la_foto.huella,
        "creada_en": la_foto.creada_en,
        "el_escenario": json.loads(la_foto.el_contenido),
    }


@router.get("/foto/{version}/exportar")
def exportar_la_foto(version: int, explotacion: ExplotacionActual, db: Db) -> Response:
    """***El fichero, y es EXACTAMENTE la foto.***

    *El contrato lo pide asi: «**la exportacion coincide con el detalle y conserva la version evaluada**».*
    *Por eso **no se vuelve a calcular nada**: se lee el contenido guardado y se escribe. Si se recalculara, un
    cambio en la finca haria que el fichero dijera una cosa y la foto otra.*

    *La cabecera lleva **la version, el año y la fecha**, para que el papel que se lleva al asesor diga de que
    es; y **no lleva ninguna columna de elegibilidad**, porque este programa no la afirma.*
    """
    la_foto = _la_foto(db, explotacion, version)
    el_escenario = json.loads(la_foto.el_contenido)

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow([f"version {la_foto.version}", f"año {la_foto.anio}", f"hecha {la_foto.creada_en}"])
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
            "Content-Disposition": f'attachment; filename="pac-{la_foto.anio}-v{la_foto.version}.csv"'
        },
    )


def _un_numero_texto(valor) -> str:
    """*Un numero, o **la casilla en blanco** si no consta.* *Un `0` ahi seria decir que esa tierra tiene cero
    hectareas, que es lo contrario de «no consta».*"""
    return "" if valor is None else str(valor)
