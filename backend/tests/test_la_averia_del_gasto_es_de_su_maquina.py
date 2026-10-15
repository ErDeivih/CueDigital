"""**La avería de un gasto tiene que ser de la máquina que el gasto dice**.

CRM-07 #7, 14/10/2026. El gasto lleva `maquina_id` y `averia_id`, y cada uno se comprobaba **por
separado** contra la finca. Eso dejaba pasar un gasto que dice «máquina A» y cuelga de una avería de la
**B**, y entonces **el mismo coste sale en las dos fichas**: en la de A por su `maquina_id` y en la de B
porque la avería es suya. Y en las cuentas, como coste directo de una máquina que no lo ha tenido.

***No se puede comprobar «por separado» algo que tiene que encajar ENTRE SÍ.***

Los tres casos, y el tercero es el que impide que la comprobación se pase de lista:

 1. Un gasto de una avería **de su** máquina: se guarda.
 2. Un gasto que dice una máquina y una avería **de otra**: **422**, y el mensaje dice **cómo
    arreglarlo** (elegir una avería de esa máquina, o dejar solo la avería, que ya dice de cuál es).
 3. Y **sin máquina pero con avería**: se guarda igual. La avería ya dice de qué máquina es, y el coste
    sale en su ficha; obligar a repetir la máquina sería pedir el mismo dato dos veces.
"""


def una_maquina(cliente, cabeceras, nombre: str) -> dict:
    respuesta = cliente.post(
        "/api/maquinaria",
        headers=cabeceras,
        json={"nombre": nombre, "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def una_averia(cliente, cabeceras, maquina_id: int, que_paso: str) -> dict:
    respuesta = cliente.post(
        f"/api/maquinaria/{maquina_id}/averias",
        headers=cabeceras,
        json={"fecha": "2026-04-01", "que_paso": que_paso, "resuelta": False},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def un_gasto(cliente, cabeceras, campana_id: int, clave: str, **campos):
    cuerpo = {
        "campana_id": campana_id,
        "concepto": "Reparación del eje del ventilador",
        "categoria": "reparacion",
        "importe": "900.00",
        "clave_de_reenvio": clave,
    }
    cuerpo.update(campos)
    return cliente.post("/api/gastos", headers=cabeceras, json=cuerpo)


def test_un_gasto_puede_colgar_de_una_averia_de_su_maquina(cliente, cuenta, campana):
    maquina = una_maquina(cliente, cuenta["cabeceras"], "El Landini")
    averia = una_averia(cliente, cuenta["cabeceras"], maquina["id"], "Se rompió el eje")

    respuesta = un_gasto(
        cliente,
        cuenta["cabeceras"],
        campana["id"],
        "reparacion-1",
        maquina_id=maquina["id"],
        averia_id=averia["id"],
    )

    assert respuesta.status_code == 201, respuesta.text


def test_un_gasto_no_puede_colgar_de_una_averia_de_OTRA_maquina(cliente, cuenta, campana):
    """**El fallo**: «máquina A» con una avería de la B, y el coste sale en las dos fichas."""
    la_de_antes = una_maquina(cliente, cuenta["cabeceras"], "El Landini")
    la_de_ahora = una_maquina(cliente, cuenta["cabeceras"], "El Fendt")
    averia_del_landini = una_averia(cliente, cuenta["cabeceras"], la_de_antes["id"], "Se rompió el eje")

    respuesta = un_gasto(
        cliente,
        cuenta["cabeceras"],
        campana["id"],
        "reparacion-2",
        maquina_id=la_de_ahora["id"],
        averia_id=averia_del_landini["id"],
    )

    assert respuesta.status_code == 422, respuesta.text
    # **Y el mensaje dice QUE pasa y COMO arreglarlo**, que es la regla de esta casa: un error que no
    # dice que hacer deja al agricultor mirando una pantalla sin saber por donde salir.
    dicho = respuesta.json()["detail"]
    assert "otra máquina" in dicho, dicho
    assert "deja solo la avería" in dicho, dicho


def test_sin_maquina_pero_con_averia_se_guarda(cliente, cuenta, campana):
    """La avería ya dice de qué máquina es: repetirla no puede ser obligatorio."""
    maquina = una_maquina(cliente, cuenta["cabeceras"], "El Landini")
    averia = una_averia(cliente, cuenta["cabeceras"], maquina["id"], "Se rompió el eje")

    respuesta = un_gasto(
        cliente, cuenta["cabeceras"], campana["id"], "reparacion-3", averia_id=averia["id"]
    )

    assert respuesta.status_code == 201, respuesta.text
    # Y su coste sale en la ficha de la máquina, por la avería.
    coste = cliente.get("/api/gastos/averias", headers=cuenta["cabeceras"]).json()
    suya = next(uno for uno in coste["averias"] if uno["averia_id"] == averia["id"])
    assert suya["coste"] == "900.00"
