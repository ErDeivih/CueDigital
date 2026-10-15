"""**La vida de una avería**: nace, se corrige, se anula y se borra — y lo que falta se dice.

CRM-07 #7, 14/10/2026. Las tres pruebas que el informe del dueño dejaba pendientes, más una que salió al
hacer el papel.

 1. ***Una avería sin decir qué pasó contesta un 422 que se puede LEER.*** El esquema ya lo exigía
    (`que_paso: str = Field(min_length=1)`), pero **un 422 de FastAPI no dice nada que el agricultor
    entienda**: la pantalla enseñaba «No se ha podido» y él no podía saber que le faltaba escribir. Se
    comprueba en la puerta -como el `G53` de los gastos- para poder decirlo con una frase que diga **cómo
    arreglarlo**.
 2. **Anular una avería no es borrarla**: se queda en el cuaderno, tachada y con su motivo, y deja de
    contar.
 3. **Y borrar** se lleva la fila, que es lo que se hace cuando se apuntó por error.
"""


def _una_maquina(cliente, cabeceras, nombre: str) -> dict:
    respuesta = cliente.post(
        "/api/maquinaria",
        headers=cabeceras,
        json={"nombre": nombre, "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _una_averia(cliente, cabeceras, maquina_id: int, **cambios) -> dict:
    cuerpo = {"fecha": "2026-04-01", "que_paso": "Se rompió el eje del ventilador", "resuelta": False}
    cuerpo.update(cambios)
    return cliente.post(f"/api/maquinaria/{maquina_id}/averias", headers=cabeceras, json=cuerpo)


def _las_averias(cliente, cabeceras, maquina_id: int) -> list[dict]:
    ficha = cliente.get(f"/api/maquinaria/{maquina_id}", headers=cabeceras)
    assert ficha.status_code == 200, ficha.text
    return ficha.json().get("averias") or []


def test_una_averia_sin_decir_que_paso_dice_como_arreglarlo(cliente, cuenta):
    """***El 422 tiene que poder leerse.*** Un `min_length=1` del esquema contesta un cuerpo de validación
    de FastAPI, y eso en la pantalla es «No se ha podido»: el agricultor no sabe qué le falta."""
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini sin qué pasó")

    respuesta = _una_averia(cliente, cabeceras, maquina["id"], que_paso="")

    assert respuesta.status_code == 422, respuesta.text
    dicho = str(respuesta.json())
    assert "decir qué pasó" in dicho, f"el aviso no dice qué falta: {dicho[:200]}"
    assert "eje del ventilador" in dicho, (
        "y tampoco dice CÓMO arreglarlo: la frase trae un ejemplo de lo que se espera"
    )


def test_se_anula_una_averia_y_se_queda_en_el_cuaderno(cliente, cuenta):
    """**Anular no es borrar**: la avería se queda, con su motivo, y deja de contar."""
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Fendt que se anula")
    averia = _una_averia(cliente, cabeceras, maquina["id"]).json()

    respuesta = cliente.post(
        f"/api/maquinaria/{maquina['id']}/averias/{averia['id']}/anular",
        headers=cabeceras,
        json={"motivo": "Se apuntó en la máquina que no era"},
    )
    assert respuesta.status_code == 200, respuesta.text

    suyas = _las_averias(cliente, cabeceras, maquina["id"])
    assert len(suyas) == 1, "anular no se lleva la fila: se queda en el cuaderno"
    assert suyas[0]["anulado"] is True
    assert suyas[0]["motivo_anulacion"] == "Se apuntó en la máquina que no era"


def test_se_borra_una_averia_apuntada_por_error(cliente, cuenta):
    """Borrar sí se la lleva: es para lo que se apuntó mal."""
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini del borrado")
    averia = _una_averia(cliente, cabeceras, maquina["id"]).json()

    respuesta = cliente.delete(
        f"/api/maquinaria/{maquina['id']}/averias/{averia['id']}", headers=cabeceras
    )
    assert respuesta.status_code in (200, 204), respuesta.text

    assert _las_averias(cliente, cabeceras, maquina["id"]) == []
