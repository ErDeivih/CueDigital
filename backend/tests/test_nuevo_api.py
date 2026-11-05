"""Las dos puertas del armazón nuevo: `/api/nuevo/hoy` y `/api/nuevo/tierras` (IMP-1, 05/11/2026).

La interfaz nueva vive aparte, en `/nuevo/`, y **no lee la pantalla vieja**: pide estos dos endpoints
ligeros. Lo que se comprueba aquí, y por qué cada cosa:

  · **Que sin sesión no se ve nada**: las dos puertas contestan `401`, y eso se comprueba en el
    servidor, no escondiendo un botón (`AGENTS.md` §3.5).
  · **Que `hoy` cuenta la finca de verdad**: la campaña que se está llevando, cuántas tierras hay y
    cuántas hectáreas, la cuenta que ha entrado, y los últimos apuntes **del más nuevo al más viejo y
    como mucho cinco**. Si no hay apuntes, la lista va vacía y **no se rellena con nada**.
  · **Que `tierras` agrupa por municipio con su rectángulo**, dibuja la forma de la tierra con los
    puntos de su WKT y trae el cultivo del año y los de los años anteriores **sin inventar ninguno**.
  · **Que una finca no ve las tierras de otra** (aislamiento entre fincas).
  · **Que una superficie que no consta no se convierte en un cero**: si a una tierra le falta la
    superficie, el total de la finca **no se sabe** y va como `None` (`app/superficies.py`).

Los datos se crean con los fixtures de `conftest.py` y con las puertas de verdad de la aplicación: lo
que se prueba es lo que el agricultor tendría delante, no un objeto fabricado a mano.
"""

from __future__ import annotations

from app import geo

# Dos cuadrados de un grado de lado (unos 100 m en la realidad): uno en Peñaranda y otro lejos, para
# que se note si el agrupamiento por municipio o el rectángulo se cruzan de sitio.
CUADRADO = "POLYGON((-5.0 41.0, -4.99 41.0, -4.99 41.01, -5.0 41.01, -5.0 41.0))"
CUADRADO_LEJOS = "POLYGON((-4.5 40.5, -4.49 40.5, -4.49 40.51, -4.5 40.51, -4.5 40.5))"


def _campana(cliente, cabeceras, anio: int) -> dict:
    """Crea una campaña de un año, como lo hace la pantalla de los años."""
    respuesta = cliente.post(
        "/api/campanas",
        headers=cabeceras,
        json={
            "anio": anio,
            "fecha_inicio": f"{anio}-01-01",
            "fecha_fin": f"{anio}-12-31",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _sembrar(cliente, cabeceras, parcela_id: int, campana_id: int, especie: str, **cambios) -> dict:
    datos = {"campana_id": campana_id, "especie": especie}
    datos.update(cambios)
    respuesta = cliente.post(
        f"/api/parcelas/{parcela_id}/cultivos", headers=cabeceras, json=datos
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------- el anillo del mapa


def test_el_anillo_son_los_puntos_del_wkt():
    """`geo.puntos_del_wkt` devuelve los vértices en `(longitud, latitud)` y no cierra el anillo.

    Es lo que necesita el mapa: pintar la tierra con los puntos de verdad. El último punto del WKT
    repite el primero, así que no se devuelve dos veces.
    """
    assert geo.puntos_del_wkt(CUADRADO) == [
        (-5.0, 41.0),
        (-4.99, 41.0),
        (-4.99, 41.01),
        (-5.0, 41.01),
    ]
    # Sin forma no hay puntos, y eso no es un error: una tierra apuntada a mano no tiene dibujo.
    assert geo.puntos_del_wkt(None) == []
    assert geo.puntos_del_wkt("") == []


# --------------------------------------------------------------------------- sin sesión


def test_sin_sesion_las_dos_puertas_contestan_401(cliente):
    """La puerta es la que autoriza: sin vale no se ve nada, ni con la dirección a mano."""
    for ruta in ("/api/nuevo/hoy", "/api/nuevo/tierras"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 401, (ruta, respuesta.text)


# --------------------------------------------------------------------------- hoy


def test_hoy_de_una_finca_recien_creada(cliente, cuenta, campana):
    respuesta = cliente.get("/api/nuevo/hoy", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert datos["finca"] == {
        "nombre": "David Pérez Velasco",
        "municipio": "Peñaranda de Bracamonte",
        "provincia": "Salamanca",
    }
    assert datos["campana"] == {"id": campana["id"], "anio": campana["anio"]}
    assert datos["cuenta"] == {"nombre": "David", "correo": "david@ejemplo.test"}
    # La finca está creada y sin tierras: cero tierras y cero hectáreas **de verdad**, no un vacío.
    assert datos["tierras"] == {"n": 0, "ha": 0.0}
    # Y sin apuntes la lista va vacía: no se rellena con nada.
    assert datos["ultimos"] == []


def test_hoy_los_ultimos_apuntes_van_del_mas_nuevo_al_mas_viejo(
    cliente,
    cuenta,
    campana,
    crear_parcela,
    nuevo_tratamiento,
    nueva_fertilizacion,
):
    """Un tratamiento, una labor y un abono: los tres salen, ordenados por fecha de verdad."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=2.43)

    tratamiento = cliente.post(
        "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
    )
    assert tratamiento.status_code == 201, tratamiento.text

    labor = cliente.post(
        "/api/labores",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "tipo": "laboreo",
            "fecha": "2026-03-15",
            "parcela_id": tierra["id"],
            "superficie_ha": 2.43,
        },
    )
    assert labor.status_code == 201, labor.text

    abono = cliente.post(
        "/api/fertilizaciones", headers=cuenta["cabeceras"], json=nueva_fertilizacion()
    )
    assert abono.status_code == 201, abono.text

    respuesta = cliente.get("/api/nuevo/hoy", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    ultimos = respuesta.json()["ultimos"]

    # El tratamiento es del 1 de mayo, la labor del 15 de marzo y el abono del 20 de febrero.
    assert [uno["tipo"] for uno in ultimos] == ["tratamiento", "labor", "fertilizacion"]
    assert [uno["fecha"] for uno in ultimos] == ["2026-05-01", "2026-03-15", "2026-02-20"]
    # La tierra es la que el agricultor reconoce, y el título sale de lo que apuntó.
    assert [uno["tierra"] for uno in ultimos] == ["El Prado", "El Prado", "El Prado"]
    assert ultimos[0]["titulo"] == "Ejemplo 25 EC"  # el nombre del producto aplicado
    assert ultimos[1]["titulo"] == "Laboreo"  # la etiqueta de su trabajo
    assert ultimos[2]["titulo"] == "Nitrato amónico 33,5%"  # el nombre del abono


def test_hoy_como_mucho_cinco_apuntes(cliente, cuenta, campana, parcela):
    """Seis labores, cinco huecos: se quedan las cinco más nuevas."""
    for dia in range(1, 7):
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "laboreo",
                "fecha": f"2026-01-{dia:02d}",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        assert respuesta.status_code == 201, respuesta.text

    ultimos = cliente.get("/api/nuevo/hoy", headers=cuenta["cabeceras"]).json()["ultimos"]
    assert len(ultimos) == 5
    assert [uno["fecha"] for uno in ultimos] == [
        "2026-01-06",
        "2026-01-05",
        "2026-01-04",
        "2026-01-03",
        "2026-01-02",
    ]


def test_hoy_un_apunte_sin_tierra_lo_dice(cliente, cuenta, nuevo_tratamiento_en_instalacion):
    """Un tratamiento de una nave no tiene tierra, y la respuesta lo dice con esas palabras."""
    respuesta = cliente.post(
        "/api/tratamientos",
        headers=cuenta["cabeceras"],
        json=nuevo_tratamiento_en_instalacion(),
    )
    assert respuesta.status_code == 201, respuesta.text

    ultimos = cliente.get("/api/nuevo/hoy", headers=cuenta["cabeceras"]).json()["ultimos"]
    assert ultimos[0]["tierra"] == "sin tierra"


def test_hoy_si_falta_una_superficie_el_total_no_se_inventa(cliente, cuenta, crear_parcela):
    """Una tierra sin superficie: el total de hectáreas **no se sabe**, y va como `None`.

    Sumar solo las que se conocen daría una cifra más pequeña que la de verdad, y en una declaración
    eso no es un redondeo: es un número falso (`app/superficies.py`).
    """
    crear_parcela(alias="Con superficie", superficie_ha=2.43)
    crear_parcela(alias="Sin superficie", superficie_ha=None)

    datos = cliente.get("/api/nuevo/hoy", headers=cuenta["cabeceras"]).json()
    assert datos["tierras"] == {"n": 2, "ha": None}


# --------------------------------------------------------------------------- tierras


def test_tierras_agrupa_por_municipio_con_su_rectangulo(cliente, cuenta, crear_parcela):
    crear_parcela(
        alias="1/5-1 AVENA",
        municipio="Peñaranda de Bracamonte",
        superficie_ha=2.0,
        geometria=CUADRADO,
    )
    crear_parcela(
        alias="1/5-2 BARBECHO",
        municipio="Peñaranda de Bracamonte",
        superficie_ha=3.0,
    )
    crear_parcela(
        alias="7/2-1 TRIGO",
        municipio="Macotera",
        superficie_ha=1.5,
        geometria=CUADRADO_LEJOS,
    )

    respuesta = cliente.get("/api/nuevo/tierras", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert datos["totales"] == {"n": 3, "ha": 6.5, "municipios": 2}

    # Los municipios con más tierras primero, que es como se leen los filtros de la pantalla.
    assert [uno["nombre"] for uno in datos["municipios"]] == [
        "Peñaranda de Bracamonte",
        "Macotera",
    ]
    penaranda, macotera = datos["municipios"]
    assert penaranda["n"] == 2
    assert penaranda["ha"] == 5.0
    # El rectángulo sale de **los puntos de las tierras con forma**: la que no tiene forma no aporta.
    assert penaranda["bbox"] == [-5.0, 41.0, -4.99, 41.01]
    assert macotera["bbox"] == [-4.5, 40.5, -4.49, 40.51]

    por_alias = {una["alias"]: una for una in datos["tierras"]}
    con_forma = por_alias["1/5-1 AVENA"]
    assert con_forma["anillo"] == [
        [-5.0, 41.0],
        [-4.99, 41.0],
        [-4.99, 41.01],
        [-5.0, 41.01],
    ]
    assert con_forma["centro"] == [-4.995, 41.005]
    # La que se apuntó a mano no tiene forma, y eso se dice con `None`, no con un cuadro inventado.
    sin_forma = por_alias["1/5-2 BARBECHO"]
    assert sin_forma["anillo"] is None
    assert sin_forma["centro"] is None


def test_tierras_trae_el_cultivo_del_anio_y_los_de_los_anios_anteriores(
    cliente, cuenta, campana, crear_parcela, db
):
    """El cultivo de la campaña activa y hasta tres años atrás, del más nuevo al más viejo."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=2.43)
    otra = crear_parcela(alias="La Era", superficie_ha=1.0)
    de_2025 = _campana(cliente, cuenta["cabeceras"], campana["anio"] - 1)
    de_2024 = _campana(cliente, cuenta["cabeceras"], campana["anio"] - 2)
    de_2023 = _campana(cliente, cuenta["cabeceras"], campana["anio"] - 3)
    de_2022 = _campana(cliente, cuenta["cabeceras"], campana["anio"] - 4)

    _sembrar(
        cliente,
        cuenta["cabeceras"],
        tierra["id"],
        campana["id"],
        "Trigo blando",
        variedad="Craklin",
        superficie_cultivada_ha=2.43,
    )
    for campana_vieja, especie, variedad in (
        (de_2025, "Cebada", "Meseta"),
        (de_2024, "Barbecho", None),
        (de_2023, "Girasol", None),
        (de_2022, "Veza", None),
    ):
        _sembrar(
            cliente,
            cuenta["cabeceras"],
            tierra["id"],
            campana_vieja["id"],
            especie,
            variedad=variedad,
            superficie_cultivada_ha=2.0,
        )
    # La otra tierra no tiene nada sembrado este año: su cultivo va a `None`, no a un invento.
    _sembrar(cliente, cuenta["cabeceras"], otra["id"], de_2025["id"], "Avena")

    datos = cliente.get("/api/nuevo/tierras", headers=cuenta["cabeceras"]).json()
    por_alias = {una["alias"]: una for una in datos["tierras"]}

    assert por_alias["El Prado"]["cultivo"] == {"nombre": "Trigo blando", "variedad": "Craklin"}
    assert por_alias["El Prado"]["otros_anios"] == [
        {"anio": campana["anio"] - 1, "cultivo": "Cebada", "superficie_ha": 2.0, "variedad": "Meseta"},
        {"anio": campana["anio"] - 2, "cultivo": "Barbecho", "superficie_ha": 2.0, "variedad": None},
        {"anio": campana["anio"] - 3, "cultivo": "Girasol", "superficie_ha": 2.0, "variedad": None},
    ]
    # La Era no tiene cultivo este año y solo uno del año pasado.
    assert por_alias["La Era"]["cultivo"] is None
    assert por_alias["La Era"]["otros_anios"] == [
        {"anio": campana["anio"] - 1, "cultivo": "Avena", "superficie_ha": None, "variedad": None}
    ]


def test_los_atributos_del_sigpac_viajan_en_la_respuesta(cliente, cuenta, crear_parcela):
    """`coef_regadio`, `region` y `admisibilidad` están en el contrato aunque hoy valgan `None`.

    Los añade otro compañero a `models.Parcela`; aquí se leen con `getattr` para no romper mientras
    llegan, así que lo que se comprueba es que **el hueco existe** y que no se rellena con un número
    inventado.
    """
    crear_parcela(alias="El Prado")
    tierra = cliente.get("/api/nuevo/tierras", headers=cuenta["cabeceras"]).json()["tierras"][0]
    for campo in ("coef_regadio", "region", "admisibilidad"):
        assert campo in tierra
        assert tierra[campo] is None or isinstance(tierra[campo], (int, float))


# --------------------------------------------------------------------------- aislamiento


def test_una_finca_no_ve_las_tierras_de_otra(cliente, cuenta, crear_parcela, crear_cuenta):
    """Dos agricultores: cada uno ve lo suyo y nada del otro."""
    crear_parcela(alias="El Prado", superficie_ha=2.43)
    otro = crear_cuenta("otro@ejemplo.test")
    respuesta = cliente.post(
        "/api/parcelas",
        headers=otro["cabeceras"],
        json={"alias": "Tierra ajena", "superficie_ha": 100.0, "municipio": "Macotera"},
    )
    assert respuesta.status_code == 201, respuesta.text

    las_mias = cliente.get("/api/nuevo/tierras", headers=cuenta["cabeceras"]).json()
    assert [una["alias"] for una in las_mias["tierras"]] == ["El Prado"]
    assert las_mias["totales"] == {"n": 1, "ha": 2.43, "municipios": 1}

    las_suyas = cliente.get("/api/nuevo/tierras", headers=otro["cabeceras"]).json()
    assert [una["alias"] for una in las_suyas["tierras"]] == ["Tierra ajena"]
    assert las_suyas["totales"] == {"n": 1, "ha": 100.0, "municipios": 1}

    # Y lo mismo en `hoy`: los apuntes y los números son de su finca.
    assert cliente.get("/api/nuevo/hoy", headers=otro["cabeceras"]).json()["tierras"] == {
        "n": 1,
        "ha": 100.0,
    }


def test_no_se_puede_pedir_la_campana_de_otra_finca(cliente, cuenta, crear_cuenta, crear_parcela):
    """Una campaña que no es de esta finca da 404, no los datos de la otra."""
    crear_parcela()
    otro = crear_cuenta("otro@ejemplo.test")
    campana_ajena = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()

    respuesta = cliente.get(
        f"/api/nuevo/tierras?campana_id={campana_ajena['id']}", headers=cuenta["cabeceras"]
    )
    assert respuesta.status_code == 404, respuesta.text
