"""**La edicion concurrente: version esperada y resolucion explicita** (CRM-08, 17/10/2026).

El ticket lo pide con estas palabras: *«Edicion concurrente: **version esperada** y **resolucion explicita**;
***no ultimo escritor silencioso***»*.

***Y la version no hay que inventarla***: la casa **ya apuntaba cada cambio** en `auditoria` -con quien y
cuando-, asi que **la version de un registro es su ultima fila de auditoria**. *Cero columnas nuevas.*
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import correcciones, models


def _un_apunte(db, cuenta, *, entidad="contacto", entidad_id=999):
    """Deja una fila de auditoria como las que deja el programa, **sin tocar el programa**."""
    correcciones.apuntar(
        db,
        explotacion_id=cuenta["explotacion_id"],
        usuario_id=cuenta["usuario_id"],
        entidad=entidad,
        entidad_id=entidad_id,
        accion="corregir",
        datos={"nombre": ["antes", "ahora"]},
    )
    db.commit()


# ---------------------------------------------------------------------------
# 1 · La version, que sale de la auditoria
# ---------------------------------------------------------------------------


def test_un_apunte_que_nadie_ha_tocado_va_por_la_version_cero(db, cuenta):
    """***`0` es un valor legitimo***: no se ha tocado nunca desde que se creo.

    Y es distinto de «no se sabe»: el apunte existe y nadie lo ha cambiado.
    """
    assert correcciones.la_version_de(db, entidad="contacto", entidad_id=999) == 0


def test_cada_correccion_sube_la_version(db, cuenta):
    """***La version de un registro es su ultima fila de auditoria***, y por eso **sube sola**."""
    _un_apunte(db, cuenta)
    primera = correcciones.la_version_de(db, entidad="contacto", entidad_id=999)
    assert primera > 0, "***tras una correccion, la version ya no es cero***"

    _un_apunte(db, cuenta)
    segunda = correcciones.la_version_de(db, entidad="contacto", entidad_id=999)
    assert segunda > primera, "***y cada correccion la sube***"


def test_la_version_es_DE_CADA_APUNTE_y_no_de_todos(db, cuenta):
    """***Y de cada uno***: que otro apunte cambie no cambia la version de este."""
    _un_apunte(db, cuenta, entidad_id=999)
    mia = correcciones.la_version_de(db, entidad="contacto", entidad_id=999)

    _un_apunte(db, cuenta, entidad_id=1000)
    assert correcciones.la_version_de(db, entidad="contacto", entidad_id=1000) != 0
    assert correcciones.la_version_de(db, entidad="contacto", entidad_id=999) == mia, (
        "***la de 999 no se ha movido***"
    )


def test_un_apunte_sin_id_no_tiene_version(db):
    """Y sin id -un apunte que aun no se ha guardado- la version es `0`, no un fallo."""
    assert correcciones.la_version_de(db, entidad="contacto", entidad_id=None) == 0


# ---------------------------------------------------------------------------
# 2 · Y la comprobacion, ANTES de tocar nada
# ---------------------------------------------------------------------------


def _un_registro(db, cuenta):
    """Un registro de verdad que se pueda corregir, y otro con los mismos campos."""
    guardado = models.Auditoria(
        explotacion_id=cuenta["explotacion_id"],
        entidad="contacto",
        entidad_id=999,
        accion="alta",
        fecha=dt.datetime(2026, 10, 17, 9, 0),
    )
    db.add(guardado)
    db.flush()
    return guardado


def test_si_la_version_CUADRA_se_corrige(db, cuenta):
    """El camino bueno: quien llama dice la version que tiene, y es la de verdad."""
    guardado = _un_registro(db, cuenta)
    # ***La auditoria se apunta AL REGISTRO*** -`guardado.id`-, que es de quien `corregir` mira la version.
    _un_apunte(db, cuenta, entidad_id=guardado.id)
    la_que_hay = correcciones.la_version_de(db, entidad="contacto", entidad_id=guardado.id)

    preparado = models.Auditoria(
        explotacion_id=cuenta["explotacion_id"],
        entidad="contacto",
        entidad_id=999,
        accion="corregir",
        fecha=dt.datetime(2026, 10, 17, 10, 0),
    )
    correcciones.corregir(
        db,
        guardado=guardado,
        preparado=preparado,
        entidad="contacto",
        explotacion_id=cuenta["explotacion_id"],
        usuario_id=cuenta["usuario_id"],
        version_esperada=la_que_hay,
    )
    assert guardado.accion == "corregir", "***con la version buena, se escribe***"


def test_si_la_version_NO_cuadra_se_levanta_el_error_Y_NO_SE_ESCRIBE_NADA(db, cuenta):
    """***«No ultimo escritor silencioso.»***

    ***Y lo que importa es el «no se escribe nada»***: se comprueba **antes** de tocar el registro, asi que
    un rechazo deja el apunte **exactamente como estaba**.
    """
    guardado = _un_registro(db, cuenta)
    _un_apunte(db, cuenta, entidad_id=guardado.id)  # alguien lo toco: ya no es la version del otro
    lo_de_antes = guardado.accion

    preparado = models.Auditoria(
        explotacion_id=cuenta["explotacion_id"],
        entidad="contacto",
        entidad_id=999,
        accion="corregir",
        fecha=dt.datetime(2026, 10, 17, 10, 0),
    )
    with pytest.raises(correcciones.VersionQueNoCuadra) as fallo:
        correcciones.corregir(
            db,
            guardado=guardado,
            preparado=preparado,
            entidad="contacto",
            explotacion_id=cuenta["explotacion_id"],
            usuario_id=cuenta["usuario_id"],
            version_esperada=1,  # la que el otro tenia, que ya no es la de verdad
        )

    assert guardado.accion == lo_de_antes, "***NO se ha escrito nada***"
    assert fallo.value.esperada == 1
    assert fallo.value.la_de_verdad != 1, "y el error dice por cual va"
    assert fallo.value.quien == cuenta["usuario_id"], "***y QUIEN lo cambio***"
    assert fallo.value.cuando is not None, "***y CUANDO***"


def test_sin_version_esperada_NO_se_comprueba_nada(db, cuenta):
    """***La compatibilidad***: `version_esperada=None` es el valor por defecto, y **no comprueba nada**.

    Es lo que hace que esto se pueda encender **puerta a puerta** sin tocar las dieciseis que ya corregian.
    """
    guardado = _un_registro(db, cuenta)
    _un_apunte(db, cuenta, entidad_id=guardado.id)

    preparado = models.Auditoria(
        explotacion_id=cuenta["explotacion_id"],
        entidad="contacto",
        entidad_id=999,
        accion="corregir",
        fecha=dt.datetime(2026, 10, 17, 10, 0),
    )
    correcciones.corregir(
        db,
        guardado=guardado,
        preparado=preparado,
        entidad="contacto",
        explotacion_id=cuenta["explotacion_id"],
    )
    assert guardado.accion == "corregir", "sin version esperada, se escribe como siempre"
