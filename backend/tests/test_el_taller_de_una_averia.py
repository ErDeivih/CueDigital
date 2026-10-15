"""El **taller** de una avería: se apunta, se lee con su nombre, y no puede ser de otra finca.

CRM-07 #7, 14/10/2026. El informe del dueño lo pide así: «**taller de la avería**». Y es un **papel de
`Contacto`**, no una tabla nueva: el taller ya vivía ahí (`contactos.py` tiene el papel `taller`) y lo
que faltaba era **el enlace**.

Lo que se comprueba aquí, y por qué cada cosa:

 1. **Se apunta y se lee con su NOMBRE, no con su identificador.** La fila guarda el id; la pantalla
    enseña el nombre, que es la convención de la casa (igual que `decidido_por` y que la bandeja).
 2. **Y se puede cambiar de taller**, y la respuesta dice el **nuevo**. Este es el caso que se me
    escapó al escribirlo: el nombre se resuelve **al leer**, y en el PUT la lectura del cargador corre
    **antes** de corregir, así que sin volver a resolverlo la respuesta diría el taller **viejo**.
 3. **Sin taller no pasa nada**: vacío es **«no consta»**, no «ninguno». La mayoría de las averías se
    arreglan uno mismo, y obligar a decir un taller inventaría un dato que nadie ha dicho.
 4. **Y el taller de OTRA finca contesta 404**, con el mismo ayudante que usa un gasto para su contacto:
    sin eso, una avería podría apuntar al taller del vecino y el nombre saldría como si fuera suyo.

Las frases que se comprueban son las del servidor, no las de la pantalla: aquí se prueba la puerta.
"""


def un_contacto(cliente, cuenta, nombre: str) -> int:
    """Un contacto de la finca con el papel de taller, y devuelve su identificador."""
    respuesta = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={"nombre": nombre, "papeles": ["taller"]},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def una_maquina(cliente, cuenta, nombre: str = "El Landini") -> int:
    respuesta = cliente.post(
        "/api/maquinaria",
        headers=cuenta["cabeceras"],
        json={"nombre": nombre, "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def una_averia(cliente, cuenta, maquina_id: int, **cambios):
    datos = {"fecha": "2026-10-14", "que_paso": "Se ha roto el embrague", "resuelta": False}
    datos.update(cambios)
    return cliente.post(f"/api/maquinaria/{maquina_id}/averias", headers=cuenta["cabeceras"], json=datos)


def test_el_taller_se_apunta_y_se_lee_con_su_nombre(cliente, cuenta):
    maquina = una_maquina(cliente, cuenta)
    taller = un_contacto(cliente, cuenta, "Talleres El Camino")

    respuesta = una_averia(cliente, cuenta, maquina, taller_contacto_id=taller)

    assert respuesta.status_code == 201, respuesta.text
    guardada = respuesta.json()
    assert guardada["taller_contacto_id"] == taller, "el identificador se guarda tal cual"
    assert guardada["taller"] == "Talleres El Camino", (
        "y se lee el NOMBRE, no el identificador: es lo que la pantalla puede enseñar"
    )


def test_cambiar_de_taller_dice_el_nuevo_y_no_el_viejo(cliente, cuenta):
    """**El caso que se me escapó**: el cargador resuelve el nombre ANTES de corregir."""
    maquina = una_maquina(cliente, cuenta)
    el_de_antes = un_contacto(cliente, cuenta, "Talleres El Camino")
    el_de_ahora = un_contacto(cliente, cuenta, "El taller del pueblo")
    averia = una_averia(cliente, cuenta, maquina, taller_contacto_id=el_de_antes).json()

    respuesta = cliente.put(
        f"/api/maquinaria/{maquina}/averias/{averia['id']}",
        headers=cuenta["cabeceras"],
        json={
            "fecha": averia["fecha"],
            "que_paso": averia["que_paso"],
            "resuelta": True,
            "taller_contacto_id": el_de_ahora,
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["taller"] == "El taller del pueblo", (
        "la respuesta dice el taller de AHORA: resolverlo antes de corregir diria el viejo"
    )


def test_sin_taller_es_no_consta_y_la_averia_se_guarda_igual(cliente, cuenta):
    maquina = una_maquina(cliente, cuenta)

    respuesta = una_averia(cliente, cuenta, maquina)

    assert respuesta.status_code == 201, "una averia sin taller es lo mas normal del mundo"
    assert respuesta.json()["taller"] is None
    assert respuesta.json()["taller_contacto_id"] is None


def test_el_taller_de_otra_finca_no_es_tuyo(cliente, cuenta, crear_cuenta):
    """**No puede apuntar al taller del vecino**: el mismo ayudante que usa un gasto."""
    maquina = una_maquina(cliente, cuenta)
    el_vecino = crear_cuenta("el-vecino@ejemplo.es", "El vecino")
    suyo = cliente.post(
        "/api/contactos",
        headers=el_vecino["cabeceras"],
        json={"nombre": "Talleres del vecino", "papeles": ["taller"]},
    )
    assert suyo.status_code == 201, suyo.text

    respuesta = una_averia(cliente, cuenta, maquina, taller_contacto_id=suyo.json()["id"])

    assert respuesta.status_code == 404, respuesta.text
    assert "tu cuaderno" in respuesta.json()["detail"].lower(), respuesta.text
