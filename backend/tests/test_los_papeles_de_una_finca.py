"""**Los papeles y lo que puede cada uno** (CRM-08, 17/10/2026).

El ticket pide *«permisos: propietario, colaborador y consulta segun modelo disponible, con **matriz por
accion y dato**»*.

***Y aqui habia un defecto de verdad***: `puede_modificar` y `puede_ver_lo_economico` son columnas que nacian
en **`True`** para todos, y `anadir_acceso` **solo ponia el papel**. Resultado: **cualquier acceso a una
finca podia modificarla y ver su dinero**, sin que el papel pintara nada.
"""

from __future__ import annotations

import pytest

from app import accesos, models


# ---------------------------------------------------------------------------
# 1 · La matriz, que es pura y se puede probar sin base
# ---------------------------------------------------------------------------


def test_el_titular_puede_todo():
    suyo = accesos.las_capacidades_de(accesos.TITULAR)

    assert suyo["puede_modificar"] is True
    assert suyo["puede_ver_lo_economico"] is True


def test_el_colaborador_trabaja_pero_NO_ve_las_cuentas():
    """***El corazon del arreglo.*** Apunta, corrige y quita -es un trabajador-, pero los saldos, los
    importes y los documentos con dinero **no salen en su respuesta**.

    Y la casa lo comprueba **en la puerta** y no en la pantalla: *«ocultar dinero tambien lo elimina de la
    respuesta»*.
    """
    suyo = accesos.las_capacidades_de(accesos.AYUDANTE)

    assert suyo["puede_modificar"] is True, "trabajar si"
    assert suyo["puede_ver_lo_economico"] is False, "***pero el dinero de la finca, NO***"


def test_el_consulta_mira_y_no_toca():
    suyo = accesos.las_capacidades_de(accesos.CONSULTA)

    assert suyo["puede_modificar"] is False, "***no toca nada***"
    assert suyo["puede_ver_lo_economico"] is False


def test_un_papel_que_no_existe_no_concede_NADA():
    """***Ante la duda, lo que menos concede.*** Un papel mal escrito no puede acabar dando permiso de
    escritura sobre la finca de nadie."""
    for inventado in ("", "  ", "dueno", "admin", None):
        suyo = accesos.las_capacidades_de(inventado)
        assert suyo["puede_modificar"] is False, f"***{inventado!r} no puede modificar***"
        assert suyo["puede_ver_lo_economico"] is False


def test_los_tres_papeles_estan_declarados():
    assert accesos.TITULAR == "titular"
    assert accesos.AYUDANTE == "ayudante"
    assert accesos.CONSULTA == "consulta"
    assert set(accesos.LOS_PAPELES) == {"titular", "ayudante", "consulta"}
    assert set(accesos.LAS_CAPACIDADES) == set(accesos.LOS_PAPELES), (
        "***cada papel de la lista tiene que tener su fila en la matriz***"
    )


# ---------------------------------------------------------------------------
# 2 · Y por la puerta de `anadir_acceso`, que es donde estaba el defecto
# ---------------------------------------------------------------------------


def _otra_finca(db):
    finca = models.Explotacion(nombre="La finca de la prueba", nif="12345678Z")
    db.add(finca)
    db.flush()
    return finca


def test_un_acceso_de_CONSULTA_NO_puede_modificar(db, cuenta):
    """***Lo que se arreglo***: antes, `anadir_acceso` ponia el papel y las dos capacidades se quedaban en el
    `True` por defecto de la columna, asi que un consulta **podia modificar** la finca.
    """
    finca = _otra_finca(db)
    usuario = db.get(models.Usuario, cuenta["usuario_id"])

    nuevo = accesos.anadir_acceso(db, usuario, finca.id, papel=accesos.CONSULTA)
    db.flush()

    assert nuevo.papel == accesos.CONSULTA
    assert nuevo.puede_modificar is False, "***un consulta NO modifica***"
    assert nuevo.puede_ver_lo_economico is False
    assert accesos.puede_entrar(db, usuario.id, finca.id) is True, "pero si entra"
    assert accesos.puede_modificar(db, usuario.id, finca.id) is False, "***y la puerta lo dice***"


def test_un_acceso_de_AYUDANTE_modifica_pero_no_ve_el_dinero(db, cuenta):
    finca = _otra_finca(db)
    usuario = db.get(models.Usuario, cuenta["usuario_id"])

    nuevo = accesos.anadir_acceso(db, usuario, finca.id, papel=accesos.AYUDANTE)
    db.flush()

    assert nuevo.puede_modificar is True
    assert nuevo.puede_ver_lo_economico is False, "***y esto es lo que antes estaba mal***"
    assert accesos.puede_modificar(db, usuario.id, finca.id) is True
    assert accesos.puede_ver_lo_economico(db, usuario.id, finca.id) is False


def test_un_papel_inventado_no_se_puede_dar(db, cuenta):
    """Y por la puerta **no entra**: un papel que no existe se rechaza en vez de crear un acceso raro."""
    finca = _otra_finca(db)
    usuario = db.get(models.Usuario, cuenta["usuario_id"])

    with pytest.raises(ValueError):
        accesos.anadir_acceso(db, usuario, finca.id, papel="dueno_de_todo")
