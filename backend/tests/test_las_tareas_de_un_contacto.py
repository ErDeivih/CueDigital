"""Las próximas acciones de un contacto (Entrega 3, 13/10/2026).

POR QUÉ. El cuaderno sabe lo que **ha pasado** —ventas, gastos, tratamientos— y no sabía lo que **queda por hacer**:
llamar al del pienso, llevar la factura, mirar si ha llegado la semilla. Eso vivía en la cabeza del agricultor o en
un papel, y por eso se olvida.

Lo que se prueba aquí es lo que el encargo pide con más cuidado, y por eso tiene su prueba cada cosa:

  · **Lo único que se exige es saber qué hay que hacer.** El responsable, la descripción y el día son opcionales de
    verdad: una tarea **sin fecha** es una tarea, y obligarla a tener fecha sería inventarla.
  · **Una fecha vencida NO cancela la tarea.** Sigue pendiente, con su fecha, y se dice que está vencida. Es la
    frase del encargo: *«la fecha vencida no transforma automáticamente una tarea en cancelada»*.
  · **Reenviar no duplica**: la misma clave devuelve la que ya había, sin apuntar otra ni dejar dos trazas.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app import database, models


def _un_contacto(cliente, cuenta, nombre: str = "Cooperativa de Peñaranda") -> dict:
    respuesta = cliente.post(
        "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": nombre}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _apuntar_una_tarea(cliente, cuenta, contacto_id: int, **tarea):
    return cliente.post(
        f"/api/contactos/{contacto_id}/tareas", headers=cuenta["cabeceras"], json=tarea
    )


def _sus_tareas(respuesta) -> list[dict]:
    return respuesta.json()["tareas"]


def test_una_tarea_con_titulo_se_apunta_y_se_ve_en_la_ficha(cliente, cuenta):
    """Lo mínimo: se apunta lo que hay que hacer y aparece en la ficha."""
    ficha = _un_contacto(cliente, cuenta)
    respuesta = _apuntar_una_tarea(
        cliente, cuenta, ficha["id"], titulo="Llamar por el pienso", responsable="Ana"
    )
    assert respuesta.status_code == 200, respuesta.text

    suyas = _sus_tareas(respuesta)
    assert len(suyas) == 1, f"tiene que estar la que se acaba de apuntar: {suyas}"
    assert suyas[0]["titulo"] == "Llamar por el pienso", suyas[0]
    assert suyas[0]["responsable"] == "Ana", suyas[0]
    assert suyas[0]["estado"] == models.Tarea.PENDIENTE, suyas[0]
    assert suyas[0]["vencida"] is False, "recién apuntada y sin fecha no puede estar vencida"


def test_una_tarea_sin_fecha_es_una_tarea_y_se_dice_con_palabras(cliente, cuenta):
    """**Sin fecha no es «hoy».** Se dice con palabras, y no está vencida por no tener fecha."""
    ficha = _un_contacto(cliente, cuenta)
    suyas = _sus_tareas(_apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Mirar la semilla"))
    assert suyas[0]["fecha_prevista"] is None, f"no se le inventa un día: {suyas[0]}"
    assert suyas[0]["fecha_texto"] == "Sin fecha", f"y se dice así: {suyas[0]['fecha_texto']}"
    assert suyas[0]["vencida"] is False, "sin fecha no se puede estar vencida"


def test_una_fecha_vencida_no_cancela_la_tarea(cliente, cuenta):
    """**La frase del encargo, comprobada**: una fecha pasada deja la tarea **pendiente** y **vencida**.

    Es la diferencia entre «se me pasó» y «ya no hay que hacerlo»: el programa no puede decidir por el agricultor que
    una tarea de la semana pasada ya no vale. Se dice que está vencida y él decide.
    """
    ficha = _un_contacto(cliente, cuenta)
    ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    respuesta = _apuntar_una_tarea(
        cliente, cuenta, ficha["id"], titulo="Llevar la factura", fecha_prevista=ayer
    )
    suya = _sus_tareas(respuesta)[0]
    assert suya["estado"] == models.Tarea.PENDIENTE, f"la fecha no la cancela: {suya}"
    assert suya["vencida"] is True, f"pero se dice que está vencida: {suya}"
    assert suya["fecha_prevista"] == ayer, "y conserva su día, que es el dato que el agricultor puso"


def test_una_tarea_de_hoy_no_esta_vencida(cliente, cuenta):
    """El día de hoy no está pasado: lo de hoy es **lo de hoy**, no lo vencido."""
    ficha = _un_contacto(cliente, cuenta)
    hoy = dt.date.today().isoformat()
    suya = _sus_tareas(
        _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Llamar hoy", fecha_prevista=hoy)
    )[0]
    assert suya["vencida"] is False, f"lo de hoy no está vencido: {suya}"
    assert suya["fecha_texto"] == dt.date.today().strftime("%d/%m/%Y"), suya["fecha_texto"]


def test_reenviar_la_misma_accion_no_duplica_la_tarea(cliente, cuenta, db_sesion):
    """**Reenviar no duplica**: misma clave, misma tarea, y **sin dejar dos trazas**.

    Es el patrón de la casa (notas, cobros), y aquí importa igual: el agricultor pulsa con guantes, o se le va la red,
    y volver a pulsar no puede apuntar dos veces la misma llamada.
    """
    ficha = _un_contacto(cliente, cuenta)
    clave = "tarea-de-prueba-1"
    primera = _apuntar_una_tarea(
        cliente, cuenta, ficha["id"], titulo="Llamar por el pienso", clave_de_reenvio=clave
    )
    assert primera.status_code == 200, primera.text
    segunda = _apuntar_una_tarea(
        cliente, cuenta, ficha["id"], titulo="Llamar por el pienso", clave_de_reenvio=clave
    )
    assert segunda.status_code == 200, segunda.text

    assert len(_sus_tareas(segunda)) == 1, f"no puede haber dos: {_sus_tareas(segunda)}"

    db_sesion.expire_all()
    trazas = list(
        db_sesion.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == "contacto",
                models.Auditoria.entidad_id == ficha["id"],
                models.Auditoria.accion == "tarea_crear",
            )
        )
    )
    assert len(trazas) == 1, f"ni dos trazas: {len(trazas)}"


def test_una_tarea_necesita_saber_que_hay_que_hacer(cliente, cuenta):
    """Lo único que se exige, y **con palabras**: sin título no se apunta, y se dice por qué.

    Y al revés: **lo demás no se exige**. Un responsable en blanco o una descripción vacía no impiden guardar, porque
    exigirlos sería obligar a inventar datos.
    """
    ficha = _un_contacto(cliente, cuenta)
    sin_titulo = _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="   ")
    assert sin_titulo.status_code == 422, sin_titulo.status_code
    assert "Escribe qué hay que hacer" in sin_titulo.text, sin_titulo.text

    # Sin responsable y sin descripción **sí** se guarda.
    sin_nada_mas = _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Regar el lunes")
    assert sin_nada_mas.status_code == 200, sin_nada_mas.text
    assert len(_sus_tareas(sin_nada_mas)) == 1, "lo que no se exige no puede impedir guardar"


def test_las_tareas_de_otra_finca_no_se_tocan(cliente, cuenta, crear_cuenta):
    """**Aislamiento**: 404, como la ficha."""
    mio = _un_contacto(cliente, cuenta)
    otro = crear_cuenta("otro-tareas@ejemplo.test")
    respuesta = cliente.post(
        f"/api/contactos/{mio['id']}/tareas",
        headers=otro["cabeceras"],
        json={"titulo": "Colarse"},
    )
    assert respuesta.status_code == 404, f"tiene que dar 404 y ha dado {respuesta.status_code}"
