"""**Lo que le ha costado a una máquina tenerla parada**, que es lo que enseña su ficha.

CRM-07 #7, 14/10/2026. El informe pide «**el coste en la ficha de la máquina**». El cálculo ya existía
(`gastos.coste_de_las_averias`, y la puerta `GET /gastos/averias` avería por avería); lo que faltaba era
**poder pedirlo de una máquina sola y con su total**, que es lo que la ficha necesita.

Lo que se fija aquí, y las dos últimas son las que este módulo no perdona:

 1. **Solo las averías de ESA máquina**, no las de la finca entera.
 2. **El total** de lo que cuesta tenerla parada, con **cuántos gastos** lo forman.
 3. ***Y cuántos de esos gastos NO tienen importe***: un total que solo suma la mitad y no lo dice parece
    el total entero. Por eso hay `sin_importe` y `completo`.
 4. **Y las reparaciones de esa máquina que no cuelgan de ninguna avería** también son suyas, y también
    se cuentan: si no, el total mentiría por abajo.
 5. Y la máquina **de otra finca** contesta 404, como todo lo demás.
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


def un_gasto(cliente, cabeceras, campana_id: int, clave: str, concepto: str, **campos):
    cuerpo = {"campana_id": campana_id, "concepto": concepto, "categoria": "reparacion",
              "clave_de_reenvio": clave}
    cuerpo.update(campos)
    respuesta = cliente.post("/api/gastos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_el_coste_de_una_maquina_trae_solo_sus_averias(cliente, cuenta, campana):
    cabeceras = cuenta["cabeceras"]
    landini = una_maquina(cliente, cabeceras, "El Landini")
    fendt = una_maquina(cliente, cabeceras, "El Fendt")
    la_del_landini = una_averia(cliente, cabeceras, landini["id"], "Se rompió el eje")
    la_del_fendt = una_averia(cliente, cabeceras, fendt["id"], "Se rompió el embrague")
    un_gasto(cliente, cabeceras, campana["id"], "r-landini", "Eje del Landini",
             maquina_id=landini["id"], averia_id=la_del_landini["id"], importe="900.00")
    un_gasto(cliente, cabeceras, campana["id"], "r-fendt", "Embrague del Fendt",
             maquina_id=fendt["id"], averia_id=la_del_fendt["id"], importe="300.00")

    suyo = cliente.get(f"/api/gastos/averias?maquina_id={landini['id']}", headers=cabeceras).json()

    assert [uno["averia_id"] for uno in suyo["averias"]] == [la_del_landini["id"]], (
        "la ficha de una máquina no enseña lo que se ha roto la del vecino"
    )
    assert suyo["total"]["texto_coste"] == "900,00 €"
    assert suyo["total"]["gastos"] == 1
    assert suyo["total"]["completo"] is True


def test_un_gasto_sin_importe_se_cuenta_y_el_total_lo_dice(cliente, cuenta, campana):
    """***Un total que solo suma la mitad y no lo dice parece el total entero.***"""
    cabeceras = cuenta["cabeceras"]
    maquina = una_maquina(cliente, cabeceras, "El Landini")
    averia = una_averia(cliente, cabeceras, maquina["id"], "Se rompió el eje")
    un_gasto(cliente, cabeceras, campana["id"], "r-1", "El eje", maquina_id=maquina["id"],
             averia_id=averia["id"], importe="900.00")
    # Y una reparación **sin importe**: se apunta y no se sabe lo que costó.
    un_gasto(cliente, cabeceras, campana["id"], "r-2", "La mano de obra", maquina_id=maquina["id"],
             averia_id=averia["id"])

    suyo = cliente.get(f"/api/gastos/averias?maquina_id={maquina['id']}", headers=cabeceras).json()

    assert suyo["total"]["gastos"] == 2, "los dos gastos existen"
    assert suyo["total"]["sin_importe"] == 1, "y uno no tiene importe"
    assert suyo["total"]["completo"] is False, "así que el total NO está completo, y se dice"
    assert suyo["total"]["texto_coste"] == "900,00 €", (
        "lo que se sabe se enseña igual: lo que no se puede es llamarlo «el total»"
    )


def test_las_reparaciones_de_la_maquina_sin_averia_tambien_son_suyas(cliente, cuenta, campana):
    """Un gasto de la máquina que no cuelga de ninguna avería **también** le ha costado a ella."""
    cabeceras = cuenta["cabeceras"]
    maquina = una_maquina(cliente, cabeceras, "El Landini")
    averia = una_averia(cliente, cabeceras, maquina["id"], "Se rompió el eje")
    un_gasto(cliente, cabeceras, campana["id"], "r-1", "El eje", maquina_id=maquina["id"],
             averia_id=averia["id"], importe="900.00")
    un_gasto(cliente, cabeceras, campana["id"], "r-2", "Un repaso del motor",
             maquina_id=maquina["id"], importe="200.00")

    suyo = cliente.get(f"/api/gastos/averias?maquina_id={maquina['id']}", headers=cabeceras).json()

    assert suyo["total"]["texto_coste"] == "1.100,00 €", "el repaso también le costó a esa máquina"
    assert suyo["reparaciones_sin_averia"]["cuantos"] == 1
    assert suyo["reparaciones_sin_averia"]["importe"] == "200.00"


def test_la_maquina_de_otra_finca_no_es_tuya(cliente, cuenta, crear_cuenta):
    el_vecino = crear_cuenta("el-vecino-coste@ejemplo.es", "El vecino")
    suya = una_maquina(cliente, el_vecino["cabeceras"], "El del vecino")

    respuesta = cliente.get(f"/api/gastos/averias?maquina_id={suya['id']}", headers=cuenta["cabeceras"])

    assert respuesta.status_code == 404, respuesta.text
