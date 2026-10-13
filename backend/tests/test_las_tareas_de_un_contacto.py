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


def _la_de_titulo(respuesta, titulo: str) -> dict:
    """**La tarea que se acaba de crear, buscada por su título**, y no por su posición.

    POR QUÉ ESTE AYUDANTE, y me costó tres «defectos» falsos: yo hacía `_sus_tareas(…)[0]` dando por hecho que la
    primera de la respuesta era la que había creado. **No lo es**: la respuesta trae **todas** las tareas de la ficha,
    ordenadas, y la primera puede ser otra —así que completé **la tarea equivocada** y luego le eché la culpa al
    filtro por estado y al orden, que **funcionaban bien**—. Se busca por el título, que es lo que identifica lo que
    uno acaba de apuntar.
    """
    suyas = [tarea for tarea in _sus_tareas(respuesta) if tarea["titulo"] == titulo]
    assert len(suyas) == 1, f"tiene que haber una sola «{titulo}»: {[t['titulo'] for t in _sus_tareas(respuesta)]}"
    return suyas[0]


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
    suya = _la_de_titulo(respuesta, "Llevar la factura")
    assert suya["estado"] == models.Tarea.PENDIENTE, f"la fecha no la cancela: {suya}"
    assert suya["vencida"] is True, f"pero se dice que está vencida: {suya}"
    assert suya["fecha_prevista"] == ayer, "y conserva su día, que es el dato que el agricultor puso"


def test_una_tarea_de_hoy_no_esta_vencida(cliente, cuenta):
    """El día de hoy no está pasado: lo de hoy es **lo de hoy**, no lo vencido."""
    ficha = _un_contacto(cliente, cuenta)
    hoy = dt.date.today().isoformat()
    suya = _la_de_titulo(
        _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Llamar hoy", fecha_prevista=hoy)
    , "Llamar hoy")
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

# ---------------------------------------------------------------------------
# Las puertas de la lista y del cierre (Entrega 3)
# ---------------------------------------------------------------------------


def _la_lista(cliente, cuenta, **filtros):
    respuesta = cliente.get("/api/tareas", headers=cuenta["cabeceras"], params=filtros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["tareas"]


def test_la_lista_filtra_por_responsable_estado_y_vencimiento(cliente, cuenta):
    """**Los tres filtros del encargo**, y cada uno deja fuera lo que tiene que dejar fuera."""
    ficha = _un_contacto(cliente, cuenta)
    ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    hoy = dt.date.today().isoformat()
    _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Vencida de Ana", responsable="Ana", fecha_prevista=ayer)
    _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="De hoy de Ana", responsable="Ana", fecha_prevista=hoy)
    _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Sin fecha de Luis", responsable="Luis")
    hecha = _la_de_titulo(
        _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Ya hecha", responsable="Ana"), "Ya hecha"
    )
    cliente.post(f"/api/tareas/{hecha['id']}/completar", headers=cuenta["cabeceras"])

    assert len(_la_lista(cliente, cuenta)) == 4, "sin filtros están todas"
    assert [t["titulo"] for t in _la_lista(cliente, cuenta, responsable="Luis")] == ["Sin fecha de Luis"]
    assert [t["titulo"] for t in _la_lista(cliente, cuenta, estado="hecha")] == ["Ya hecha"]
    assert [t["titulo"] for t in _la_lista(cliente, cuenta, vencimiento="vencidas")] == ["Vencida de Ana"]
    assert [t["titulo"] for t in _la_lista(cliente, cuenta, vencimiento="hoy")] == ["De hoy de Ana"]
    assert [t["titulo"] for t in _la_lista(cliente, cuenta, vencimiento="sin_fecha")] == ["Sin fecha de Luis"]


def test_la_lista_pone_primero_lo_que_hay_que_hacer(cliente, cuenta):
    """**El orden es el del trabajo**: lo pendiente antes que lo cerrado, y dentro, lo vencido arriba.

    Y **lo que no tiene fecha va al final** de lo pendiente: una tarea sin día no está «para ya», y ponerla arriba
    sería mentir con el orden.
    """
    ficha = _un_contacto(cliente, cuenta)
    ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    manana = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Sin fecha")
    _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Mañana", fecha_prevista=manana)
    _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Vencida", fecha_prevista=ayer)
    hecha = _la_de_titulo(_apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Hecha"), "Hecha")
    cliente.post(f"/api/tareas/{hecha['id']}/completar", headers=cuenta["cabeceras"])

    assert [t["titulo"] for t in _la_lista(cliente, cuenta)] == [
        "Vencida",
        "Mañana",
        "Sin fecha",
        "Hecha",
    ], "vencido primero, luego el día, luego sin fecha, y lo cerrado al final"


def test_reprogramar_cambia_solo_lo_que_se_manda(cliente, cuenta):
    """**Corrección parcial**: se mueve el día y el responsable se queda.

    Es el mismo cuidado que en los canales: lo que no viene **no se toca**. Y **quitar la fecha** (mandándola nula a
    propósito) deja la tarea **sin fecha**, que es una decisión del agricultor y no un descuido.
    """
    ficha = _un_contacto(cliente, cuenta)
    ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    manana = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    suya = _la_de_titulo(
        _apuntar_una_tarea(
            cliente, cuenta, ficha["id"], titulo="Llevar la factura", responsable="Ana", fecha_prevista=ayer
        ),
        "Llevar la factura",
    )

    movida = cliente.put(
        f"/api/tareas/{suya['id']}", headers=cuenta["cabeceras"], json={"fecha_prevista": manana}
    )
    assert movida.status_code == 200, movida.text
    despues = movida.json()["tareas"][0]
    assert despues["fecha_prevista"] == manana, f"el día tiene que cambiar: {despues}"
    assert despues["responsable"] == "Ana", f"y el responsable quedarse: {despues}"
    assert despues["titulo"] == "Llevar la factura", "y el título también"
    assert despues["vencida"] is False, "y ya no está vencida"

    # **Quitarle la fecha** a propósito.
    sin_fecha = cliente.put(
        f"/api/tareas/{suya['id']}", headers=cuenta["cabeceras"], json={"fecha_prevista": None}
    )
    assert sin_fecha.status_code == 200, sin_fecha.text
    assert sin_fecha.json()["tareas"][0]["fecha_texto"] == "Sin fecha", sin_fecha.json()["tareas"][0]


def test_completar_apunta_quien_y_cuando(cliente, cuenta, db_sesion):
    """**Quién y cuándo**, que es lo que pide el encargo. Y la tarea **no se borra**: se queda hecha."""
    ficha = _un_contacto(cliente, cuenta)
    suya = _la_de_titulo(_apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Llamar"), "Llamar")

    hecha = cliente.post(f"/api/tareas/{suya['id']}/completar", headers=cuenta["cabeceras"])
    assert hecha.status_code == 200, hecha.text
    despues = hecha.json()["tareas"][0]
    assert despues["estado"] == models.Tarea.HECHA, despues
    assert despues["completada_por"], f"tiene que quedar quién: {despues}"
    assert despues["completada_en"], f"y cuándo: {despues}"
    # Y sigue en la lista: hecha, no borrada.
    assert [t["titulo"] for t in _la_lista(cliente, cuenta, estado="hecha")] == ["Llamar"]


def test_cerrar_dos_veces_no_deja_dos_trazas(cliente, cuenta, db_sesion):
    """**Las acciones repetidas no duplican trazas** (la frase del encargo).

    El agricultor toca dos veces con los guantes: el segundo toque **no** puede ser un segundo cierre, ni cambiar la
    hora del primero (que es el dato que dice cuándo se hizo de verdad).
    """
    ficha = _un_contacto(cliente, cuenta)
    suya = _la_de_titulo(_apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Llamar"), "Llamar")
    primera = cliente.post(f"/api/tareas/{suya['id']}/completar", headers=cuenta["cabeceras"]).json()["tareas"][0]
    segunda = cliente.post(f"/api/tareas/{suya['id']}/completar", headers=cuenta["cabeceras"]).json()["tareas"][0]
    assert segunda["completada_en"] == primera["completada_en"], "el segundo toque no puede mover la hora"

    db_sesion.expire_all()
    trazas = list(
        db_sesion.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == "tarea",
                models.Auditoria.entidad_id == suya["id"],
                models.Auditoria.accion == "tarea_completar",
            )
        )
    )
    assert len(trazas) == 1, f"una sola traza, y hay {len(trazas)}"


def test_cancelar_no_borra_y_lo_dice(cliente, cuenta):
    """**Cancelar no es borrar**: la tarea se queda, cancelada, con quién y cuándo."""
    ficha = _un_contacto(cliente, cuenta)
    suya = _la_de_titulo(
        _apuntar_una_tarea(cliente, cuenta, ficha["id"], titulo="Ya no hace falta"), "Ya no hace falta"
    )
    cancelada = cliente.post(f"/api/tareas/{suya['id']}/cancelar", headers=cuenta["cabeceras"])
    assert cancelada.status_code == 200, cancelada.text
    despues = cancelada.json()["tareas"][0]
    assert despues["estado"] == models.Tarea.CANCELADA, despues
    assert despues["cancelada_por"] and despues["cancelada_en"], f"con quién y cuándo: {despues}"
    assert [t["titulo"] for t in _la_lista(cliente, cuenta, estado="cancelada")] == ["Ya no hace falta"]


def test_las_tareas_de_otra_finca_no_se_ven_ni_se_cierran(cliente, cuenta, crear_cuenta):
    """**Aislamiento en la lista**: la otra finca no ve nada, y no puede cerrar lo que no es suyo."""
    mia = _un_contacto(cliente, cuenta)
    suya = _la_de_titulo(_apuntar_una_tarea(cliente, cuenta, mia["id"], titulo="Mía"), "Mía")
    otro = crear_cuenta("otro-lista@ejemplo.test")

    assert _la_lista(cliente, otro) == [], "la otra finca no ve las tareas de esta"
    cerrar = cliente.post(f"/api/tareas/{suya['id']}/completar", headers=otro["cabeceras"])
    assert cerrar.status_code == 404, f"tiene que dar 404 y ha dado {cerrar.status_code}"
    mover = cliente.put(f"/api/tareas/{suya['id']}", headers=otro["cabeceras"], json={"titulo": "Robada"})
    assert mover.status_code == 404, mover.status_code
