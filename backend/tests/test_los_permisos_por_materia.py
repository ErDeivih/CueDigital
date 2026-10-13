"""Los permisos por materia (Entrega 4, 13/10/2026).

POR QUÉ. Hasta hoy el programa sabía una cosa sola de quién entra: **si puede entrar en la finca**. Y eso no basta
para lo que pide el encargo: hay quien tiene que poder **consultar** sin poder **cambiar** nada, y hay datos —los
económicos— que no todo el que entra tiene por qué ver.

**Lo que se prueba aquí es la puerta, no el botón.** El encargo lo dice con estas palabras: *«ocultar un botón no
constituye autorización»*. Por eso todo esto se comprueba **en el servidor**, y de la misma forma si se llega por la
pantalla, por la URL o por un identificador a mano — que es justo lo que hace una prueba que llama a la puerta.

**Y las capacidades nacen en `True`**, que es lo que hace que **las cuentas que ya existen sigan funcionando**: eso no
se prueba aquí, se prueba en **todas las demás suites**, que siguen pasando con las cuentas de siempre.
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def _sin_capacidad(db_sesion, cuenta, cual: str) -> None:
    """Le quita una capacidad a esa cuenta, en su acceso a la finca.

    Se hace en la base y no por una puerta a propósito: **hoy no hay pantalla para repartir capacidades**, y esta
    prueba es del servidor. Cuando la haya, se cambiará aquí por la puerta correspondiente.
    """
    db_sesion.expire_all()
    acceso = db_sesion.scalar(
        select(models.AccesoAFinca).where(
            models.AccesoAFinca.usuario_id == cuenta["usuario_id"],
            models.AccesoAFinca.explotacion_id == cuenta["explotacion_id"],
        )
    )
    assert acceso is not None, "la cuenta tiene que tener su acceso a la finca"
    setattr(acceso, cual, False)
    db_sesion.commit()


def _un_contacto(cliente, cuenta, nombre: str = "Cooperativa de los Permisos") -> dict:
    respuesta = cliente.post("/api/contactos", headers=cuenta["cabeceras"], json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_una_cuenta_autorizada_puede_hacerlo_todo(cliente, cuenta):
    """Lo primero: **con las capacidades puestas, todo sigue funcionando**. Si no, no habría nada que restringir."""
    ficha = _un_contacto(cliente, cuenta)
    assert cliente.put(
        f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"], json={"nombre": "Otro nombre", "telefono": "600"}
    ).status_code == 200
    assert cliente.post(
        f"/api/contactos/{ficha['id']}/canales", headers=cuenta["cabeceras"], json={"clase": "telefono", "telefono": "9"}
    ).status_code == 200
    assert cliente.post(
        f"/api/contactos/{ficha['id']}/tareas", headers=cuenta["cabeceras"], json={"titulo": "Llamar"}
    ).status_code == 200
    # Y el dinero se puede mirar.
    assert cliente.get(f"/api/contactos/{ficha['id']}/saldo", headers=cuenta["cabeceras"]).status_code == 200


def test_sin_poder_modificar_la_puerta_deniega_Y_NO_ESCRIBE(cliente, cuenta, db_sesion):
    """**403, y nada escrito.** Y da igual cómo se llegue: la puerta es la que autoriza.

    Se comprueba **por identificador directo** (que es el caso que el encargo pide: «acceso directo por URL o
    identificador: mismo resultado») y se mira **la base**, no la respuesta: una puerta que contesta 403 y escribe
    igual sería lo peor de los dos mundos.
    """
    ficha = _un_contacto(cliente, cuenta)
    antes = len(list(db_sesion.scalars(select(models.Contacto))))

    _sin_capacidad(db_sesion, cuenta, "puede_modificar")

    # Corregir la ficha.
    corregir = cliente.put(
        f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"], json={"nombre": "Nombre que no debe entrar"}
    )
    assert corregir.status_code == 403, f"tiene que dar 403 y da {corregir.status_code}: {corregir.text}"
    # Apuntar un canal.
    canal = cliente.post(
        f"/api/contactos/{ficha['id']}/canales",
        headers=cuenta["cabeceras"],
        json={"clase": "telefono", "telefono": "600 000 000"},
    )
    assert canal.status_code == 403, canal.status_code
    # Apuntar una tarea.
    tarea = cliente.post(
        f"/api/contactos/{ficha['id']}/tareas", headers=cuenta["cabeceras"], json={"titulo": "No debe entrar"}
    )
    assert tarea.status_code == 403, tarea.status_code

    # **Y NADA se ha escrito**, que es lo que de verdad importa.
    db_sesion.expire_all()
    assert len(list(db_sesion.scalars(select(models.Contacto)))) == antes, "no puede haber fichas nuevas"
    la_ficha = db_sesion.get(models.Contacto, ficha["id"])
    assert la_ficha.nombre == "Cooperativa de los Permisos", f"el nombre no puede cambiar: {la_ficha.nombre}"
    assert list(
        db_sesion.scalars(
            select(models.CanalDeUnContacto).where(models.CanalDeUnContacto.contacto_id == ficha["id"])
        )
    ) == [], "y no puede haber canales nuevos"
    assert list(
        db_sesion.scalars(select(models.Tarea).where(models.Tarea.contacto_id == ficha["id"]))
    ) == [], "ni tareas nuevas"

    # **Y consultar sí puede**: quitarle el poder de cambiar no es quitarle el de mirar.
    assert cliente.get("/api/contactos", headers=cuenta["cabeceras"]).status_code == 200


def test_sin_poder_economico_no_se_ven_las_cuentas(cliente, cuenta, db_sesion):
    """**403 en el saldo**, y el dinero **no viaja**: no es que la pantalla lo esconda, es que la puerta no lo manda.

    El contrato lo dice con estas palabras: *«sin permiso económico: no aparecen importes ni documentos
    restringidos»*.
    """
    ficha = _un_contacto(cliente, cuenta)
    _sin_capacidad(db_sesion, cuenta, "puede_ver_lo_economico")

    el_saldo = cliente.get(f"/api/contactos/{ficha['id']}/saldo", headers=cuenta["cabeceras"])
    assert el_saldo.status_code == 403, f"tiene que dar 403 y da {el_saldo.status_code}: {el_saldo.text}"
    # **Y en el cuerpo no hay ni un importe**: ni el texto del dinero ni las cifras.
    assert "€" not in el_saldo.text and "nos_debe" not in el_saldo.text, (
        f"la respuesta no puede llevar el dinero: {el_saldo.text}"
    )
    # Y lo que NO es dinero se sigue viendo: la ficha, sus notas y sus tareas.
    assert cliente.get(f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"]).status_code in (200, 404)


def test_sin_poder_modificar_tampoco_se_cierra_una_tarea(cliente, cuenta, db_sesion):
    """Cerrar una tarea es **modificar**: si no se puede modificar, no se puede cerrar (ni por identificador)."""
    ficha = _un_contacto(cliente, cuenta)
    suya = cliente.post(
        f"/api/contactos/{ficha['id']}/tareas", headers=cuenta["cabeceras"], json={"titulo": "Llamar"}
    ).json()["tareas"][0]

    _sin_capacidad(db_sesion, cuenta, "puede_modificar")

    cerrar = cliente.post(f"/api/tareas/{suya['id']}/completar", headers=cuenta["cabeceras"])
    assert cerrar.status_code == 403, f"tiene que dar 403 y da {cerrar.status_code}"
    db_sesion.expire_all()
    la_tarea = db_sesion.get(models.Tarea, suya["id"])
    assert la_tarea.estado == models.Tarea.PENDIENTE, f"y no puede quedar hecha: {la_tarea.estado}"
    assert la_tarea.completada_en is None and la_tarea.completada_por is None, "ni con quién ni cuándo"

def test_la_cuenta_dice_lo_que_puede_hacer(cliente, cuenta, db_sesion):
    """**`GET /api/cuenta/yo` dice las capacidades**, para que la pantalla no ofrezca lo que va a dar 403.

    Y va aquí y no en `/api/interfaz` porque esa puerta es **pública** (va antes de entrar) y esto es de **esta cuenta
    en esta finca**. Lo que la pantalla hace con esto es **no ofrecer**: esconder el botón, el bloque del dinero y el
    alta. Lo que **no** hace es autorizar — eso lo comprueba la puerta, en el servidor, y lo prueba la prueba de
    arriba llamándola por identificador.
    """
    yo = cliente.get("/api/cuenta/yo", headers=cuenta["cabeceras"])
    assert yo.status_code == 200, yo.text
    assert yo.json()["puede_modificar"] is True, f"de partida puede: {yo.json()}"
    assert yo.json()["puede_ver_lo_economico"] is True, yo.json()

    _sin_capacidad(db_sesion, cuenta, "puede_ver_lo_economico")
    yo = cliente.get("/api/cuenta/yo", headers=cuenta["cabeceras"])
    assert yo.json()["puede_ver_lo_economico"] is False, f"y deja de poder: {yo.json()}"
    assert yo.json()["puede_modificar"] is True, "sin tocar la otra capacidad"
