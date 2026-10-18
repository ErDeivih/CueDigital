"""**El ensayo de restauracion sobre destino nuevo** (17/10/2026).

El ticket de la cola lo pide asi: *«Restauracion: base+adjuntos+configuracion necesaria, **ensayo sobre
destino nuevo**, integridad y…»*, y con estas palabras: *«nunca restaurar sobre la base real en las
pruebas»*.

***Lo que se prueba aqui***: que el ensayo **lleve la base a un destino que no existia**, que **compruebe
que ha llegado entera** -tabla por tabla, valor por valor-, y que **cuando no se puede, lo diga sin tocar
nada**.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app import database, models


def test_una_base_en_memoria_no_se_puede_ensayar_y_lo_dice(tmp_path):
    """***«No se puede, y no se toca nada.»***

    La base de las pruebas vive en memoria, y una base en memoria **no es un fichero**: no hay nada que
    copiar. *Lo honesto es parar y decirlo, no hacer un ensayo de mentira.*
    """
    destino = tmp_path / "restaurada.db"

    # ***Una base en memoria, dicha a proposito***: sin argumento, `crear_engine()` coge la del entorno -que
    # es un fichero-, y el caso que se quiere probar es justo el contrario.
    en_memoria = database.crear_engine("sqlite://")

    with pytest.raises(RuntimeError) as fallo:
        database.ensayar_la_restauracion(destino, motor=en_memoria)

    assert "no es un fichero de SQLite" in str(fallo.value), str(fallo.value)
    assert not destino.exists(), "***y no ha dejado un destino a medias***"


def test_el_ensayo_lleva_la_base_a_un_destino_nuevo_y_comprueba_que_llego(tmp_path):
    """***Lo que pide el ticket.*** Se escribe algo, se ensaya, y se mira que haya llegado **igual**.

    ***Y se mira de verdad***: no basta con que la copia se pueda abrir -un fichero a medias tambien se
    abre-. `igual` compara **cada tabla y cada valor** contra la base de origen.
    """
    origen = tmp_path / "la-de-verdad.db"
    motor = database.crear_engine(f"sqlite:///{origen}")
    models.Base.metadata.create_all(motor)
    with Session(motor) as sesion:
        sesion.add(models.Explotacion(nombre="La finca del ensayo", nif="12345678Z"))
        sesion.commit()

    destino = tmp_path / "restaurada.db"
    resultado = database.ensayar_la_restauracion(destino, motor=motor)

    assert destino.exists(), "***el ensayo no ha dejado la base restaurada***"
    assert resultado["igual"] is True, "***la copia no tiene lo mismo que la base***"
    assert resultado["entera"] is True, "la copia no esta entera"
    assert resultado["tablas"] > 0, "la copia no tiene ni una tabla"


def test_un_destino_que_ya_existe_no_es_un_destino_nuevo(tmp_path):
    """***Escribir encima de algo es justo lo que el ensayo no puede hacer.***

    *Un ensayo que machaque una base que ya estaba no prueba una restauracion: prueba una perdida.*
    """
    origen = tmp_path / "la-de-verdad.db"
    motor = database.crear_engine(f"sqlite:///{origen}")
    models.Base.metadata.create_all(motor)

    destino = tmp_path / "ya-estaba.db"
    destino.write_text("no soy una base, pero estoy aqui")

    with pytest.raises(FileExistsError) as fallo:
        database.ensayar_la_restauracion(destino, motor=motor)

    assert "ya existe" in str(fallo.value), str(fallo.value)
    assert destino.read_text() == "no soy una base, pero estoy aqui", (
        "***lo que ya estaba no se ha tocado***"
    )
