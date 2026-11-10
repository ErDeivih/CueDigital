"""**La ficha de la tierra, el calendario y los filtros por tipo** (IMP-6, 05/11/2026).

David lo pidió en este orden: *tierra primero* (elegir la tierra y ver **qué trabajo se ha hecho hoy**
sobre ella), **historial** por años con las **cantidades por hectárea** y los **meses** del abono,
**calendario** por días y **filtros por tipo** con las tierras y las cantidades de toda la explotación.

Lo que se comprueba aquí:

  · **La tierra de otra finca contesta 404** (y no 403: no se dice si existe en otro cuaderno).
  · **Una tierra sin apuntes devuelve las listas vacías y el resumen a cero**: no se rellena un año ni
    una cifra para que la pantalla tenga algo que enseñar.
  · **El trabajo de hoy es el de hoy**: lo de ayer no entra.
  · **El historial va de más nuevo a más viejo**, no se rellena un año vacío, y las dosis salen por
    hectárea (kg/ha del abono, l/ha del tratamiento, kg/ha de la cosecha) con el mes del abono.
  · **El calendario agrupa por día**, solo devuelve los días con algo y respeta el rango (y un rango al
    revés o de más de un año es un 422, no una consulta que devuelva media vida).
  · **Los filtros devuelven solo el tipo elegido**, con su resumen, y un tipo que no existe en el
    vocabulario contesta 422.

Los datos se crean por las puertas de verdad de la aplicación (labores, tratamientos, abonos y
cosecha), no fabricando filas a mano: lo que se prueba es lo que el agricultor tendría delante.
"""

from __future__ import annotations

import datetime as dt

CAMPANA_DE_EJEMPLO = 2026


def _campana(cliente, cabeceras, anio: int) -> dict:
    respuesta = cliente.post(
        "/api/campanas",
        headers=cabeceras,
        json={"anio": anio, "fecha_inicio": f"{anio}-01-01", "fecha_fin": f"{anio}-12-31"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _labor(
    cliente, cabeceras, campana_id: int, parcela_id: int, fecha: str, *, tipo="laboreo", apero=None, **cambios
):
    """Apunta una labor como la apunta el asistente: el apero va en `detalles["subtipo"]`.

    Es donde lo guarda el programa hoy (`routers/trabajos_api._el_subtipo` lo lee de ahí mientras la
    columna `Labor.subtipo` no se rellene), así que las pruebas usan la misma puerta que el agricultor.
    """
    datos = {
        "campana_id": campana_id,
        "tipo": tipo,
        "fecha": fecha,
        "parcela_id": parcela_id,
        "superficie_ha": 4.0,
        "detalles": {"subtipo": apero} if apero else None,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/labores", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _tratamiento(cliente, cabeceras, campana_id: int, parcela_id: int, fecha: str, producto_id: int, **cambios):
    datos = {
        "campana_id": campana_id,
        "fecha": fecha,
        "parcela_id": parcela_id,
        "superficie_tratada_ha": 4.0,
        "cultivo": "Trigo blando",
        "plaga": "Roya amarilla",
        "justificacion": "Vi la plaga o la hierba en el campo",
        "producto_id": producto_id,
        "dosis": 0.8,
        "franja_seguridad_respetada": True,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/tratamientos", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _abono(cliente, cabeceras, campana_id: int, parcela_id: int, fecha: str, fertilizante_id: int, **cambios):
    datos = {
        "campana_id": campana_id,
        "fecha": fecha,
        "parcela_id": parcela_id,
        "superficie_ha": 4.0,
        "fertilizante_id": fertilizante_id,
        "kg_ha_producto": 300.0,
        "modo_aplicacion": "al suelo",
        "momento": "fondo",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/fertilizaciones", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _cosecha(cliente, cabeceras, campana_id: int, parcela_id: int, fecha: str, kg: float, **cambios):
    datos = {
        "campana_id": campana_id,
        "fecha": fecha,
        "parcela_id": parcela_id,
        "producto": "Trigo blando",
        "cantidad_kg": kg,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/cosecha", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _la_tierra(cliente, cabeceras, parcela_id: int) -> dict:
    respuesta = cliente.get(f"/api/nuevo/tierra/{parcela_id}", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------- sin sesión y 404


def test_sin_sesion_las_tres_puertas_contestan_401(cliente):
    for ruta in (
        "/api/nuevo/tierra/1",
        "/api/nuevo/calendario",
        "/api/nuevo/trabajos",
    ):
        assert cliente.get(ruta).status_code == 401, ruta


def test_una_tierra_de_otra_finca_contesta_404(cliente, cuenta, crear_cuenta):
    otro = crear_cuenta("otro@ejemplo.test")
    suya = cliente.post(
        "/api/parcelas", headers=otro["cabeceras"], json={"alias": "Tierra ajena", "superficie_ha": 1.0}
    )
    assert suya.status_code == 201, suya.text
    respuesta = cliente.get(f"/api/nuevo/tierra/{suya.json()['id']}", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 404, respuesta.text


def test_una_tierra_sin_apuntes_no_se_rellena(cliente, cuenta, crear_parcela):
    """Nada inventado: listas vacías y el resumen a cero, sin fechas ni kg/ha de relleno."""
    tierra = crear_parcela(alias="El Alto", superficie_ha=3.0)
    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])

    # La ficha trae una cosa más desde el 10/11/2026: **el cuaderno guiado** (`guia`), que dice qué
    # toca hacer. En una tierra sin apuntes ni cultivo solo puede decir que falta el cultivo: **sin
    # fecha inventada**, que es la regla de la casa.
    assert set(datos) == {"tierra", "trabajo_de_hoy", "historial", "resumen", "guia"}
    assert datos["guia"] == [
        {"codigo": "cultivo", "fecha": None, "estado": "sin-fecha", "dias": None}
    ]
    assert datos["tierra"]["alias"] == "El Alto"
    assert datos["trabajo_de_hoy"] == []
    assert datos["historial"] == []
    assert datos["resumen"] == {
        "n_apuntes": 0,
        "primera_fecha": None,
        "ultima_fecha": None,
        "kg_ha_ultima_cosecha": None,
    }


# --------------------------------------------------------------------------- trabajo de hoy


def test_el_trabajo_de_hoy_es_el_de_hoy(cliente, cuenta, campana, crear_parcela):
    """Lo de ayer no es el trabajo de hoy: solo entra el apunte con la fecha de hoy."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    hoy = dt.date.today().isoformat()
    ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()

    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], ayer, apero="arado")
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], hoy, apero="cultivador")

    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])
    assert [uno["fecha"] for uno in datos["trabajo_de_hoy"]] == [hoy]
    assert datos["trabajo_de_hoy"][0]["tipo"] == "labor"
    assert datos["trabajo_de_hoy"][0]["titulo"] == "Cultivador"
    assert datos["trabajo_de_hoy"][0]["hectareas"] == 4.0
    # Y el de ayer sigue en el historial: no desaparece, solo no es «lo de hoy».
    assert any(
        labor["fecha"] == ayer
        for anio in datos["historial"]
        for labor in anio["labores"]
    )


# --------------------------------------------------------------------------- historial


def test_el_historial_va_de_mas_nuevo_a_mas_viejo_y_no_rellena_anios_vacios(
    cliente, cuenta, campana, crear_parcela, producto, fertilizante
):
    """Un elemento por año con datos: 2026 con todo, 2025 con una labor, y 2024 **no está**."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    de_2025 = _campana(cliente, cuenta["cabeceras"], 2025)

    # 2025: una labor de suelo, para que el año exista.
    _labor(cliente, cuenta["cabeceras"], de_2025["id"], tierra["id"], "2025-03-10", apero="grada")

    # 2026: siembra (labor), un abono en marzo y un tratamiento en abril.
    _labor(
        cliente,
        cuenta["cabeceras"],
        campana["id"],
        tierra["id"],
        "2026-02-20",
        tipo="siembra",
        cultivo="Trigo blando",
        variedad="Craklin",
        dosis_siembra_kg_ha=180.0,
    )
    _abono(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-15", fertilizante["id"])
    _tratamiento(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-04-02", producto["id"])

    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])
    assert [anio["anio"] for anio in datos["historial"]] == [2026, 2025]

    el_2026 = datos["historial"][0]
    # La siembra sale con su dosis de semilla y también como labor del día.
    assert el_2026["siembra"] == {
        "fecha": "2026-02-20",
        "cultivo": "Trigo blando",
        "variedad": "Craklin",
        "dosis_semilla_kg_ha": 180.0,
    }
    assert [labor["titulo"] for labor in el_2026["labores"]] == ["Siembra"]
    # El abono, con su mes y su kg/ha.
    assert el_2026["abonos"] == [
        {
            "fecha": "2026-03-15",
            "mes": 3,
            "producto": "Nitrato amónico 33,5%",
            "kg": 1200.0,
            "kg_ha": 300.0,
        }
    ]
    assert el_2026["tratamientos"] == [
        {
            "fecha": "2026-04-02",
            "producto": "Ejemplo 25 EC",
            "dosis": 0.8,
            "dosis_unidad": "L/ha",
            "materia_activa": "Tebuconazol",
        }
    ]

    # Y el año viejo tiene lo suyo y nada más.
    el_2025 = datos["historial"][1]
    assert el_2025["siembra"] is None
    assert [labor["labor"] for labor in el_2025["labores"]] == ["grada"]
    assert el_2025["abonos"] == []


def test_el_cultivo_del_anio_sale_del_declarado_y_si_no_de_la_siembra(
    cliente, cuenta, campana, crear_parcela
):
    """La cabecera de cada año dice qué se sembró: lo declarado manda, y si no hay, lo de la siembra."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    # Solo la labor de siembra, sin declarar el cultivo de la campaña.
    _labor(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-02-20",
        tipo="siembra", cultivo="Cebada", variedad="Meseta", dosis_siembra_kg_ha=150.0,
    )
    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])
    assert datos["historial"][0]["cultivo"] == "Cebada"
    assert datos["historial"][0]["variedad"] == "Meseta"

    # Y cuando el agricultor declara el cultivo del año, manda lo declarado.
    respuesta = cliente.post(
        f"/api/parcelas/{tierra['id']}/cultivos",
        headers=cuenta["cabeceras"],
        json={"campana_id": campana["id"], "especie": "Trigo blando", "variedad": "Craklin",
              "superficie_cultivada_ha": 4.0},
    )
    assert respuesta.status_code == 201, respuesta.text
    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])
    assert datos["historial"][0]["cultivo"] == "Trigo blando"
    assert datos["historial"][0]["variedad"] == "Craklin"


def test_la_cosecha_da_los_kilos_por_hectarea(cliente, cuenta, campana, crear_parcela):
    """Una cosecha de 20.000 kg en una tierra de 4 ha son 5.000 kg/ha, y el resumen lo dice."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _cosecha(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-07-20", 20_000.0)

    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])
    assert datos["historial"][0]["cosecha"] == {
        "fecha": "2026-07-20",
        "kg": 20_000.0,
        "kg_ha": 5_000.0,
    }
    assert datos["resumen"]["kg_ha_ultima_cosecha"] == 5_000.0


def test_las_fechas_del_resumen_son_la_primera_y_la_ultima(cliente, cuenta, campana, crear_parcela):
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-01-15", apero="arado")
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-05-15", apero="grada")

    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])
    assert datos["resumen"]["n_apuntes"] == 2
    assert datos["resumen"]["primera_fecha"] == "2026-01-15"
    assert datos["resumen"]["ultima_fecha"] == "2026-05-15"


# --------------------------------------------------------------------------- calendario


def test_el_calendario_agrupa_por_dia_y_respeta_el_rango(cliente, cuenta, campana, crear_parcela):
    una = crear_parcela(alias="El Prado", superficie_ha=4.0)
    otra = crear_parcela(alias="La Era", superficie_ha=2.0)
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-10", apero="arado")
    _labor(cliente, cuenta["cabeceras"], campana["id"], otra["id"], "2026-03-10", apero="grada")
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-12", apero="cultivador")
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-04-01", apero="grada")

    datos = cliente.get(
        "/api/nuevo/calendario", headers=cuenta["cabeceras"],
        params={"desde": "2026-03-01", "hasta": "2026-03-31"},
    ).json()

    assert (datos["desde"], datos["hasta"]) == ("2026-03-01", "2026-03-31")
    assert [dia["fecha"] for dia in datos["dias"]] == ["2026-03-10", "2026-03-12"]
    assert [len(dia["trabajos"]) for dia in datos["dias"]] == [2, 1]
    # Cada trabajo lleva su tierra, y sin repetir la de al lado.
    primero = datos["dias"][0]["trabajos"]
    assert {trabajo["tierra_alias"] for trabajo in primero} == {"El Prado", "La Era"}
    assert datos["totales"]["por_tipo"] == {"labor": 3}
    assert datos["totales"]["n"] == 3
    # **Y desde el IMP-13 el mes trae también sus hectáreas y sus cantidades por unidad**: las
    # hectáreas son 4 + 2 + 4, y estas tres labores no apuntan cantidad, así que no hay unidades
    # (ni se rellena con un cero que afirmaría algo).
    assert datos["totales"]["hectareas"] == 12.0
    assert datos["totales"]["cantidades_por_unidad"] == {}


def test_el_calendario_sin_fechas_mira_el_mes_en_curso(cliente, cuenta):
    hoy = dt.date.today()
    datos = cliente.get("/api/nuevo/calendario", headers=cuenta["cabeceras"]).json()
    assert datos["desde"] == hoy.replace(day=1).isoformat()
    assert datos["hasta"][:7] == hoy.strftime("%Y-%m")
    assert datos["dias"] == []


def test_un_rango_al_reves_es_un_422_que_se_entiende(cliente, cuenta):
    respuesta = cliente.get(
        "/api/nuevo/calendario", headers=cuenta["cabeceras"],
        params={"desde": "2026-03-31", "hasta": "2026-03-01"},
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "anterior" in respuesta.json()["detail"]


def test_un_rango_de_mas_de_un_ano_es_un_422(cliente, cuenta):
    respuesta = cliente.get(
        "/api/nuevo/calendario", headers=cuenta["cabeceras"],
        params={"desde": "2025-01-01", "hasta": "2026-03-01"},
    )
    assert respuesta.status_code == 422, respuesta.text


def test_una_fecha_imposible_es_un_422(cliente, cuenta):
    respuesta = cliente.get(
        "/api/nuevo/calendario", headers=cuenta["cabeceras"],
        params={"desde": "2026-02-30", "hasta": "2026-03-01"},
    )
    assert respuesta.status_code == 422, respuesta.text


# --------------------------------------------------------------------------- filtros


def test_los_filtros_devuelven_solo_el_tipo_elegido_y_su_resumen(
    cliente, cuenta, campana, crear_parcela, producto
):
    una = crear_parcela(alias="El Prado", superficie_ha=4.0)
    otra = crear_parcela(alias="La Era", superficie_ha=2.0)
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-01", apero="arado")
    _labor(cliente, cuenta["cabeceras"], campana["id"], otra["id"], "2026-03-02", apero="arado", superficie_ha=2.0)
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-03", apero="cultivador")
    _tratamiento(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-04-02", producto["id"])

    todos = cliente.get("/api/nuevo/trabajos", headers=cuenta["cabeceras"]).json()
    # Los tipos que se ofrecen salen de lo que hay, con su recuento.
    assert {tipo["clave"]: tipo["n"] for tipo in todos["tipos"]} == {
        "arado": 2,
        "cultivador": 1,
        "tratamiento": 1,
    }
    assert todos["elegido"] is None
    # Trazabilidad: cada fila lleva su tierra y su municipio.
    assert {(fila["tierra_alias"], fila["municipio"]) for fila in todos["trabajos"]} == {
        ("El Prado", "Peñaranda de Bracamonte"),
        ("La Era", "Peñaranda de Bracamonte"),
    }

    solo_arado = cliente.get(
        "/api/nuevo/trabajos", headers=cuenta["cabeceras"], params={"tipo": "arado"}
    ).json()
    assert solo_arado["elegido"] == "arado"
    assert {fila["tipo"] for fila in solo_arado["trabajos"]} == {"arado"}
    assert solo_arado["resumen"] == {
        "n": 2,
        "hectareas": 6.0,
        # **Lo que añade el IMP-13**: las cantidades se agrupan por unidad (estas dos labores no
        # apuntan cantidad, así que el diccionario va vacío en vez de con un cero).
        "cantidades_por_unidad": {},
        "por_tipo": {
            "arado": {"n": 2, "hectareas": 6.0, "cantidades_por_unidad": {}},
        },
    }


def test_un_tipo_del_vocabulario_sin_datos_devuelve_lista_vacia(cliente, cuenta, campana, crear_parcela):
    """`grada` es un tipo del programa: si este año no hay, se dice con la lista vacía, no con un error."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-01", apero="arado")

    datos = cliente.get(
        "/api/nuevo/trabajos", headers=cuenta["cabeceras"], params={"tipo": "grada"}
    ).json()
    assert datos["elegido"] == "grada"
    assert datos["trabajos"] == []
    assert datos["resumen"]["n"] == 0
    assert datos["resumen"]["hectareas"] is None or datos["resumen"]["hectareas"] == 0.0


def test_un_tipo_que_no_existe_contesta_422_con_los_que_valen(cliente, cuenta):
    respuesta = cliente.get(
        "/api/nuevo/trabajos", headers=cuenta["cabeceras"], params={"tipo": "inventado"}
    )
    assert respuesta.status_code == 422, respuesta.text
    detalle = respuesta.json()["detail"]
    assert "cultivador" in detalle["tipos"]


def test_los_trabajos_se_pueden_pedir_de_otra_campana(cliente, cuenta, campana, crear_parcela):
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    de_2025 = _campana(cliente, cuenta["cabeceras"], 2025)
    _labor(cliente, cuenta["cabeceras"], de_2025["id"], tierra["id"], "2025-03-01", apero="arado")
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-01", apero="grada")

    de_la_2025 = cliente.get(
        "/api/nuevo/trabajos", headers=cuenta["cabeceras"], params={"campana_id": de_2025["id"]}
    ).json()
    assert [fila["fecha"] for fila in de_la_2025["trabajos"]] == ["2025-03-01"]


# --------------------------------------------------------------------------- aislamiento


def test_los_trabajos_de_otra_finca_no_salen(cliente, cuenta, campana, crear_parcela, crear_cuenta):
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-01", apero="arado")

    otro = crear_cuenta("otro@ejemplo.test")
    suyos = cliente.get("/api/nuevo/trabajos", headers=otro["cabeceras"]).json()
    assert suyos["trabajos"] == []
    assert suyos["tipos"] == []
    su_calendario = cliente.get(
        "/api/nuevo/calendario", headers=otro["cabeceras"],
        params={"desde": "2026-01-01", "hasta": "2026-12-31"},
    ).json()
    assert su_calendario["dias"] == []
