"""**Las reservas, por las puertas** (CRM-07 #9, 17/10/2026).

Las reglas del solape se prueban **puras** en `test_las_reservas_de_una_maquina.py`. Aqui se anda lo que
solo se puede andar por la puerta: que el **servidor** pare el solape, que se pueda anular, que una maquina
averiada no se reserve y que **no se crucen dos fincas**.

***El encargo pide los conflictos «en servidor»***, asi que probarlo por la funcion pura no bastaria: hay
que ver la respuesta.
"""

from __future__ import annotations


def _una_maquina(cliente, cabeceras, nombre: str) -> dict:
    respuesta = cliente.post(
        "/api/maquinaria",
        headers=cabeceras,
        json={"nombre": nombre, "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _una_reserva(cliente, cabeceras, maquina_id: int, desde: str, hasta: str):
    return cliente.post(
        f"/api/maquinaria/{maquina_id}/reservas",
        headers=cabeceras,
        json={"desde": desde, "hasta": hasta},
    )


def test_una_reserva_se_apunta_y_el_SOLAPE_LO_PARA_EL_SERVIDOR(cliente, cuenta):
    """***El conflicto se para en el servidor***, que es lo que pide el encargo.

    Y se comprueban los **limites del intervalo** por la puerta, no solo en la funcion pura: 9-11 y 11-13
    **caben las dos**, porque los extremos no se pisan.
    """
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "El de las reservas")

    primera = _una_reserva(cliente, cabeceras, mia["id"], "2026-03-02T09:00:00", "2026-03-02T11:00:00")
    assert primera.status_code == 201, primera.text

    encima = _una_reserva(cliente, cabeceras, mia["id"], "2026-03-02T10:00:00", "2026-03-02T12:00:00")
    assert encima.status_code == 409, f"***el solape lo tiene que parar el servidor***: {encima.text}"
    assert "reservada" in encima.text, f"y decir POR QUE: {encima.text}"

    # ***Los extremos no se pisan.***
    seguida = _una_reserva(cliente, cabeceras, mia["id"], "2026-03-02T11:00:00", "2026-03-02T13:00:00")
    assert seguida.status_code == 201, f"***11-13 cabe despues de 9-11***: {seguida.text}"

    # ***Y una reserva de duracion cero no es una reserva.***
    nada = _una_reserva(cliente, cabeceras, mia["id"], "2026-03-03T09:00:00", "2026-03-03T09:00:00")
    assert nada.status_code == 409, nada.text


def test_otra_maquina_a_la_misma_hora_SI_se_puede(cliente, cuenta):
    """De eso se trata: dos tractores reservados a la vez."""
    cabeceras = cuenta["cabeceras"]
    uno = _una_maquina(cliente, cabeceras, "El primero")
    otro = _una_maquina(cliente, cabeceras, "El segundo")

    assert _una_reserva(cliente, cabeceras, uno["id"], "2026-03-02T09:00:00", "2026-03-02T11:00:00").status_code == 201
    assert _una_reserva(cliente, cabeceras, otro["id"], "2026-03-02T09:00:00", "2026-03-02T11:00:00").status_code == 201


def test_ANULAR_libera_la_maquina(cliente, cuenta):
    """***Anular no es borrar***: la reserva se queda tachada y **deja de ocupar**."""
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "El que se libera")
    primera = _una_reserva(cliente, cabeceras, mia["id"], "2026-03-02T09:00:00", "2026-03-02T11:00:00").json()

    anulada = cliente.post(
        f"/api/maquinaria/{mia['id']}/reservas/{primera['id']}/anular",
        headers=cabeceras,
        json={"motivo": "Al final no hace falta"},
    )
    assert anulada.status_code == 200, anulada.text
    assert anulada.json()["anulada"] is True

    # Y ahora ese hueco esta libre.
    otra = _una_reserva(cliente, cabeceras, mia["id"], "2026-03-02T10:00:00", "2026-03-02T12:00:00")
    assert otra.status_code == 201, f"***el hueco tiene que quedar libre***: {otra.text}"

    # Y la anulada **sigue en el cuaderno**, tachada.
    todas = cliente.get(f"/api/maquinaria/{mia['id']}/reservas", headers=cabeceras).json()
    assert any(una["anulada"] for una in todas), "***anular no es borrar***"
    assert len(todas) == 2


def test_una_reserva_de_OTRA_FINCA_no_es_tuya(cliente, cuenta, crear_cuenta):
    """El aislamiento, por la puerta: ni corregirla ni anularla."""
    el_vecino = crear_cuenta("el-vecino-reservas@ejemplo.es", "El vecino")
    suya = _una_maquina(cliente, el_vecino["cabeceras"], "El del vecino")
    la_suya = _una_reserva(
        cliente, el_vecino["cabeceras"], suya["id"], "2026-03-02T09:00:00", "2026-03-02T11:00:00"
    ).json()
    mia = _una_maquina(cliente, cuenta["cabeceras"], "El mio de las reservas")

    corregir = cliente.put(
        f"/api/maquinaria/{mia['id']}/reservas/{la_suya['id']}",
        headers=cuenta["cabeceras"],
        json={"desde": "2026-03-02T09:00:00", "hasta": "2026-03-02T10:00:00"},
    )
    anular = cliente.post(
        f"/api/maquinaria/{mia['id']}/reservas/{la_suya['id']}/anular",
        headers=cuenta["cabeceras"],
        json={"motivo": "Esta no es mia"},
    )

    assert corregir.status_code == 404, corregir.text
    assert anular.status_code == 404, anular.text


def test_una_maquina_AVERIADA_no_se_reserva(cliente, cuenta):
    """***Indisponibilidad por averia***, que es lo que pide el encargo."""
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "El averiado")
    cliente.post(
        f"/api/maquinaria/{mia['id']}/averias",
        headers=cabeceras,
        json={"fecha": "2026-03-01", "que_paso": "Se le fue el embrague", "resuelta": False, "horas": 4},
    )

    intento = _una_reserva(cliente, cabeceras, mia["id"], "2026-03-02T09:00:00", "2026-03-02T11:00:00")

    assert intento.status_code == 409, f"***una maquina averiada no se reserva***: {intento.text}"
    assert "averiada" in intento.text, f"y se dice por que: {intento.text}"


def test_un_estado_que_no_existe_se_rechaza_diciendo_cuales_hay(cliente, cuenta):
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "El del estado")

    respuesta = cliente.post(
        f"/api/maquinaria/{mia['id']}/reservas",
        headers=cabeceras,
        json={
            "desde": "2026-03-02T09:00:00",
            "hasta": "2026-03-02T11:00:00",
            "estado": "inventado",
        },
    )

    assert respuesta.status_code == 422, respuesta.text
    assert "estado" in respuesta.text


# ---------------------------------------------------------------------------
# 9 · Dos peticiones A LA VEZ
# ---------------------------------------------------------------------------
#
# ***«Cambios concurrentes no producen dos reservas incompatibles»***, que es lo que pide el encargo, y lo
# unico del ticket que no se puede probar con una peticion sola.


def test_dos_peticiones_A_LA_VEZ_no_meten_dos_reservas_solapadas(cliente, cuenta, db):
    """***Se reproduce LA VENTANA, paso a paso y sin hilos*** -que es lo que lo hace reproducible-.

    Dos peticiones a la vez **miran antes de que ninguna escriba**: eso es la ventana, y se reproduce leyendo
    con **dos sesiones** y escribiendo despues, primero una y luego la otra.

    Lo que la cierra es la **segunda capa** -volver a comprobar despues del `flush`-, porque en SQLite
    `FOR UPDATE` no existe. ***Si esa segunda mirada no estuviera, esta prueba tendria DOS reservas solapadas
    y nadie se habria enterado***; con ella, la segunda se encuentra a la primera y contesta 409.

    Se hace **sin hilos a proposito**: un `sleep` y dos hilos dan una prueba que a veces pasa, y una prueba
    que a veces pasa no prueba nada.
    """
    import datetime as dt

    import pytest
    from fastapi import HTTPException
    from sqlalchemy.orm import Session

    from app import models, reservas
    from app.routers import maquinaria_api
    from app.schemas import ReservaDeMaquinaEntrada

    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "El de la carrera")
    la_explotacion = db.get(models.Explotacion, cuenta["explotacion_id"])
    el_usuario = db.get(models.Usuario, cuenta["usuario_id"])
    motor = db.get_bind()
    desde = dt.datetime(2026, 3, 2, 9, 0)
    hasta = dt.datetime(2026, 3, 2, 11, 0)
    lo_que_se_pide = ReservaDeMaquinaEntrada(desde=desde, hasta=hasta)

    def el_hueco(sesion):
        return reservas.la_que_choca(
            [
                maquinaria_api._una_reserva_en_datos(una)
                for una in maquinaria_api._las_reservas_de_la_maquina(sesion, la_explotacion, mia["id"])
            ],
            desde=desde,
            hasta=hasta,
            maquina_id=mia["id"],
        )

    with Session(motor) as una, Session(motor) as otra:
        # ***1 · LA VENTANA***: las dos miran, y las dos ven el hueco libre. Es lo que pasa de verdad cuando
        # dos peticiones entran a la vez: ninguna ha escrito todavia.
        assert el_hueco(una) is None, "***las dos tienen que ver el hueco libre: esa es la ventana***"
        assert el_hueco(otra) is None, "***las dos tienen que ver el hueco libre: esa es la ventana***"

        # ***2 · La primera escribe y cierra.***
        primera = maquinaria_api._apuntar_la_reserva_sin_pisar_a_otra(
            una, la_explotacion, el_usuario, mia["id"], lo_que_se_pide
        )
        assert primera.id, "la primera tiene que quedar escrita"

        # ***3 · Y la segunda, que ya habia mirado, intenta escribir.***
        with pytest.raises(HTTPException) as fallo:
            maquinaria_api._apuntar_la_reserva_sin_pisar_a_otra(
                otra, la_explotacion, el_usuario, mia["id"], lo_que_se_pide
            )

        assert fallo.value.status_code == 409, (
            "***la segunda tiene que encontrarse la primera: si no, hay dos reservas incompatibles***"
        )

    # ***4 · Y queda UNA.***
    todas = cliente.get(f"/api/maquinaria/{mia['id']}/reservas", headers=cabeceras).json()
    assert len(todas) == 1, f"***dos peticiones a la vez y UNA sola reserva: hay {len(todas)}***"
