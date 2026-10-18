"""**La migracion del indice del reenvio, ensayada SOBRE UNA COPIA** (CRM-07 #8, 17/10/2026).

El indice unico del reenvio no lo crea una herramienta aparte: lo pone **el arranque**
(`database.py::asegurar_indices`), que ya sabe crear los indices que falten y rehacer los que cambiaron
**sin tocar ni una fila** -lo tiene medido la casa: «las huellas de todas las tablas quedan iguales»-.

Lo que se ensaya aqui es eso, y **sobre una copia**, que es lo que pide el encargo: una instalacion que ya
venia arrancada **no tiene el indice**, y al actualizar tiene que recibirlo. Se comprueba:

  1. Que sobre una copia **sin** el indice, `asegurar_indices` lo crea.
  2. Que la copia **se puede abrir y consultar** despues (no se ha dejado a medias).
  3. Y que el indice **hace su trabajo**: dos lecturas con la misma clave, la segunda revienta.

***Por que sobre una copia y no sobre una base de verdad***: una migracion de esquema se ensaya donde se
puede repetir. La copia se hace con `shutil`, y la base original de esta prueba es un fichero temporal.
"""

from __future__ import annotations

import shutil

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.database import asegurar_indices, crear_engine

EL_INDICE = "uq_lectura_de_contador_reenvio"


def _una_base_sin_el_indice(donde) -> object:
    """Una base con el esquema de hoy pero **sin** el indice, como la de una instalacion ya arrancada."""
    motor = crear_engine("sqlite:///" + str(donde).replace("\\", "/"))
    models.Base.metadata.create_all(motor)
    with motor.begin() as conexion:
        conexion.execute(text(f"DROP INDEX IF EXISTS {EL_INDICE}"))
    return motor


def test_el_indice_del_reenvio_se_crea_al_arrancar_SOBRE_UNA_COPIA(tmp_path):
    """***Una instalacion que ya venia arrancada recibe el indice al actualizar.***"""
    original = tmp_path / "el-cuaderno.db"
    motor = _una_base_sin_el_indice(original)

    # Se comprueba que de verdad **no** estaba, que si no la prueba no prueba nada.
    with motor.connect() as conexion:
        antes = conexion.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"), {"n": EL_INDICE}
        ).fetchall()
    assert antes == [], "***la base de partida NO tiene que tener el indice***"

    # ***Sobre una COPIA***, que es lo que se ensaya: la original se queda quieta.
    copia = tmp_path / "la-copia.db"
    shutil.copyfile(original, copia)
    motor_copia = crear_engine("sqlite:///" + str(copia).replace("\\", "/"))

    creados, cambiados = asegurar_indices(motor_copia)

    assert EL_INDICE in creados, f"***el arranque tiene que crear el indice; ha creado: {creados!r}***"
    with motor_copia.connect() as conexion:
        ahora = conexion.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"), {"n": EL_INDICE}
        ).fetchall()
    assert ahora, "***y tiene que estar de verdad en la copia***"
    # **Y la copia se puede usar**: no se ha dejado a medias.
    with Session(motor_copia) as sesion:
        assert sesion.execute(text("SELECT count(*) FROM lecturas_de_contador")).scalar() == 0

# ***Y que el indice HACE SU TRABAJO*** no se repite aqui: ya lo comprueba
# `test_las_lecturas_del_contador::test_el_indice_unico_impide_dos_lecturas_con_la_misma_clave`, que mete
# dos filas con la misma clave y comprueba que la segunda revienta. **Dos pruebas de lo mismo no son el
# doble de seguridad: son una que se queda sin mantener.** Esta solo mira lo que es suyo: que el arranque
# cree el indice que falta **sobre una copia**.
