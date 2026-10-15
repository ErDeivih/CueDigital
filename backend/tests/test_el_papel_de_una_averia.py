"""**El papel de una avería** (CRM-07 #7, 14/10/2026) — y el presupuesto, que es el MISMO papel.

El informe del dueño pedía dos cosas: «**el documento de la avería**» y «**el presupuesto**». Y al
preguntarle por el presupuesto contestó: *«**un PAPEL que se engancha a la avería**»*. Así que las dos
cosas del informe son **una**: el parte del taller, la factura de la reparación o el presupuesto son
papeles, y la avería guarda **cuál**.

Lo que se fija aquí, y la segunda es la que más importa:

 1. El papel se apunta y se lee **con su título**, resuelto al leer y no guardado en la fila.
 2. ***Corregir una avería SIN mandar el taller ni el papel NO LOS BORRA.*** Es la regla A1 de esta casa
    (`docs/T02_VALORES_POR_DEFECTO.md`: «lo que la petición no manda, no se borra»), y el taller la
    incumplía: el PUT **reemplaza la fila entera**, así que mandar una corrección sin el taller lo
    borraba. Se descubrió al escribir el papel, que sí lo hace bien porque copié el patrón de la
    obligación, y se arreglaron los dos a la vez.
 3. El papel de **otra finca** no se puede apuntar: contesta 404, como todo lo demás.
 4. Y **borrar un papel que una avería usa contesta 409**, sin que haya que apuntar la avería en ninguna
    lista: `correcciones.tablas_que_apuntan_a` descubre la tabla **por el nombre de la columna**.
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
    respuesta = cliente.post(f"/api/maquinaria/{maquina_id}/averias", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _un_papel(cliente, cabeceras, titulo: str, **cambios) -> dict:
    cuerpo = {"titulo": titulo, "tipo": "factura", "carpeta": "Reparaciones"}
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/documentos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _la_averia_de_la_ficha(cliente, cabeceras, maquina_id: int) -> dict:
    """La avería **tal y como la devuelve la ficha**, que es donde el agricultor la lee."""
    ficha = cliente.get(f"/api/maquinaria/{maquina_id}", headers=cabeceras)
    assert ficha.status_code == 200, ficha.text
    averias = ficha.json().get("averias") or []
    assert averias, "la ficha no trae ninguna avería"
    return averias[0]


def test_el_papel_se_apunta_y_la_ficha_dice_cual_es(cliente, cuenta):
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini del papel")
    papel = _un_papel(cliente, cabeceras, "Factura del taller, 480 €")
    _una_averia(cliente, cabeceras, maquina["id"], documento_id=papel["id"])

    suya = _la_averia_de_la_ficha(cliente, cabeceras, maquina["id"])

    assert suya["documento_id"] == papel["id"]
    assert suya["papel"] == "Factura del taller, 480 €", (
        "la ficha tiene que decir CUÁL es el papel, no solo su identificador"
    )
    assert suya["trae_papel"] is True


def test_una_averia_sin_papel_lo_dice(cliente, cuenta):
    """Vacio es un caso normal -la mayoria se arreglan uno mismo-, y **se dice**, no se calla."""
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Fendt sin papel")
    _una_averia(cliente, cabeceras, maquina["id"])

    suya = _la_averia_de_la_ficha(cliente, cabeceras, maquina["id"])

    assert suya["documento_id"] is None
    assert suya["papel"] is None
    assert suya["trae_papel"] is False


def test_corregir_una_averia_sin_mandarlos_no_borra_el_taller_ni_el_papel(cliente, cuenta):
    """***Lo que la petición no manda, no se borra*** (regla A1).

    El PUT **reemplaza la fila entera**, así que hay que distinguir «no lo manda» de «lo manda vacío», y
    se distingue con `model_fields_set`. Sin eso, volver a la ficha solo para decir «ya está arreglada»
    se llevaba por delante el papel y el taller, que es justo lo que el agricultor había apuntado.
    """
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini que se arregla")
    papel = _un_papel(cliente, cabeceras, "Presupuesto del taller")
    averia = _una_averia(cliente, cabeceras, maquina["id"], documento_id=papel["id"])

    # Se corrige **sin mandar** `documento_id`: es el caso de «ya está arreglada y no toco lo demás».
    respuesta = cliente.put(
        f"/api/maquinaria/{maquina['id']}/averias/{averia['id']}",
        headers=cabeceras,
        json={"fecha": "2026-04-01", "que_paso": "Se rompió el eje del ventilador", "resuelta": True},
    )
    assert respuesta.status_code == 200, respuesta.text

    suya = _la_averia_de_la_ficha(cliente, cabeceras, maquina["id"])
    assert suya["resuelta"] is True, "la corrección sí se aplica"
    assert suya["documento_id"] == papel["id"], (
        "***y el papel NO se borra por no mandarlo***: lo que la petición no manda, no se borra"
    )
    assert suya["papel"] == "Presupuesto del taller"


def test_el_papel_de_otra_finca_no_se_puede_apuntar(cliente, cuenta, crear_cuenta):
    el_vecino = crear_cuenta("el-vecino-papel@ejemplo.es", "El vecino")
    suyo = _un_papel(cliente, el_vecino["cabeceras"], "Factura del vecino")
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini del vecino")

    respuesta = cliente.post(
        f"/api/maquinaria/{maquina['id']}/averias",
        headers=cabeceras,
        json={
            "fecha": "2026-04-01",
            "que_paso": "Se rompió el eje",
            "resuelta": False,
            "documento_id": suyo["id"],
        },
    )

    assert respuesta.status_code == 404, respuesta.text


def test_borrar_un_papel_que_una_averia_usa_contesta_409(cliente, cuenta):
    """***El 409 sale gratis***: no hay ninguna lista que apuntar.

    `correcciones.tablas_que_apuntan_a("documento_id")` descubre las tablas **por el nombre de la
    columna**, así que en cuanto la avería tuvo su `documento_id` empezó a contar. Lo que sí se puede
    hacer siempre es **anular** el papel, que lo deja con su motivo y con su fichero.
    """
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini con papel en uso")
    papel = _un_papel(cliente, cabeceras, "Factura que no se puede borrar")
    _una_averia(cliente, cabeceras, maquina["id"], documento_id=papel["id"])

    respuesta = cliente.delete(f"/api/documentos/{papel['id']}", headers=cabeceras)

    assert respuesta.status_code == 409, respuesta.text
