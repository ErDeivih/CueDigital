"""**Comparar años, totales del calendario y filtros con cantidades por unidad** (IMP-13, 06/11/2026).

David quiere profundizar en lo que ya existe, no en otra pantalla: **historial** (comparar años de un
vistazo), **calendario** (totales por día y del mes) y **filtros por tipo** (por tierra y por fechas,
con las cantidades separadas por unidad).

Lo que se comprueba aquí, y por qué cada cosa:

  · **El resumen de cada año del historial**: cuántos apuntes, cuántas labores y tratamientos, la suma
    de los kg/ha de los abonos, **en qué meses se abonó**, el kg/ha de la cosecha y si hubo siembra. Y
    **sin años vacíos**: un año sin datos no aparece.
  · **El `null` de verdad**: si a un abono le falta su kg/ha, la suma de abonos es `None` y no una
    cifra más pequeña. Como la columna del kg/ha de hoy es obligatoria, ese caso se prueba sobre la
    función que hace la cuenta, con un apunte fabricado: es el único sitio donde se puede probar la
    regla sin mentir en la base.
  · **Los totales del calendario**: por día y del mes, con las **hectáreas a `null`** si a algún
    trabajo le falta la superficie, y las **cantidades agrupadas por unidad**, sin sumar kilos con
    metros cúbicos.
  · **Los filtros**: por tierra, por fechas y los dos a la vez; y que **los tipos y sus cuentas se
    recalculan sobre lo filtrado**, no sobre toda la campaña.
  · **Lo que no vale**: una tierra de otra finca contesta 404; un rango al revés o de más de un año,
    422; sin sesión, 401.

Los datos se apuntan por las puertas de verdad de la aplicación (labores, abonos, tratamientos y
cosecha), no fabricando filas a mano.
"""

from __future__ import annotations

import pytest

from app import nuevo

CAMPANA_DE_EJEMPLO = 2026


# --------------------------------------------------------------------------- andamiaje


def _campana(cliente, cabeceras, anio: int) -> dict:
    respuesta = cliente.post(
        "/api/campanas",
        headers=cabeceras,
        json={"anio": anio, "fecha_inicio": f"{anio}-01-01", "fecha_fin": f"{anio}-12-31"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _labor(
    cliente,
    cabeceras,
    campana_id: int,
    parcela_id: int,
    fecha: str,
    *,
    tipo="laboreo",
    apero=None,
    superficie_ha=4.0,
    **cambios,
):
    """Una labor apuntada como la apunta el asistente (el apero va en `detalles["subtipo"]`)."""
    datos = {
        "campana_id": campana_id,
        "tipo": tipo,
        "fecha": fecha,
        "parcela_id": parcela_id,
        "superficie_ha": superficie_ha,
        "detalles": {"subtipo": apero} if apero else None,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/labores", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _abono(
    cliente,
    cabeceras,
    campana_id: int,
    parcela_id: int,
    fecha: str,
    fertilizante_id: int,
    *,
    kg_ha: float = 300.0,
    superficie_ha: float = 4.0,
    **cambios,
):
    datos = {
        "campana_id": campana_id,
        "fecha": fecha,
        "parcela_id": parcela_id,
        "superficie_ha": superficie_ha,
        "fertilizante_id": fertilizante_id,
        "kg_ha_producto": kg_ha,
        "modo_aplicacion": "al suelo",
        "momento": "fondo",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/fertilizaciones", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _tratamiento(cliente, cabeceras, campana_id: int, parcela_id: int, fecha: str, producto_id: int):
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
    respuesta = cliente.post("/api/tratamientos", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _cosecha(cliente, cabeceras, campana_id: int, parcela_id: int, fecha: str, kg: float):
    datos = {
        "campana_id": campana_id,
        "fecha": fecha,
        "parcela_id": parcela_id,
        "producto": "Trigo blando",
        "cantidad_kg": kg,
    }
    respuesta = cliente.post("/api/cosecha", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _la_tierra(cliente, cabeceras, parcela_id: int) -> dict:
    respuesta = cliente.get(f"/api/nuevo/tierra/{parcela_id}", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _los_trabajos(cliente, cabeceras, **params) -> dict:
    respuesta = cliente.get("/api/nuevo/trabajos", headers=cabeceras, params=params or None)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _el_calendario(cliente, cabeceras, **params) -> dict:
    respuesta = cliente.get("/api/nuevo/calendario", headers=cabeceras, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------- sin sesión


def test_sin_sesion_las_tres_puertas_contestan_401(cliente):
    for ruta in ("/api/nuevo/tierra/1", "/api/nuevo/calendario", "/api/nuevo/trabajos"):
        assert cliente.get(ruta).status_code == 401, ruta


# --------------------------------------------------------------------------- historial (comparar años)


def test_el_historial_compara_dos_anios_con_su_resumen(
    cliente, cuenta, campana, crear_parcela, producto, fertilizante
):
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    de_2025 = _campana(cliente, cuenta["cabeceras"], 2025)

    # 2025: siembra, un arado, un abono en abril y la cosecha.
    _labor(
        cliente, cuenta["cabeceras"], de_2025["id"], tierra["id"], "2025-03-01",
        tipo="siembra", cultivo="Cebada", variedad="Meseta", dosis_siembra_kg_ha=150.0,
    )
    _labor(cliente, cuenta["cabeceras"], de_2025["id"], tierra["id"], "2025-03-05", apero="arado")
    _abono(
        cliente, cuenta["cabeceras"], de_2025["id"], tierra["id"], "2025-04-10",
        fertilizante["id"], kg_ha=200.0,
    )
    _cosecha(cliente, cuenta["cabeceras"], de_2025["id"], tierra["id"], "2025-07-20", 8000.0)

    # 2026: un cultivador, un abono en marzo, un tratamiento y la cosecha.
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-01", apero="cultivador")
    _abono(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-15",
        fertilizante["id"], kg_ha=300.0,
    )
    _tratamiento(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-04-01", producto["id"]
    )
    _cosecha(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-07-20", 20_000.0)

    datos = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])
    assert [anio["anio"] for anio in datos["historial"]] == [2026, 2025], "ni 2024 ni huecos"

    el_2026 = datos["historial"][0]["resumen"]
    assert el_2026 == {
        "n_apuntes": 4,
        "n_labores": 1,
        "n_tratamientos": 1,
        "abonos_kg_ha": 300.0,
        "abonos_meses": [3],
        "cosecha_kg_ha": 5000.0,
        "siembra": False,
    }

    el_2025 = datos["historial"][1]["resumen"]
    assert el_2025 == {
        "n_apuntes": 4,
        "n_labores": 2,  # la siembra también es una labor del día
        "n_tratamientos": 0,
        "abonos_kg_ha": 200.0,
        "abonos_meses": [4],
        "cosecha_kg_ha": 2000.0,
        "siembra": True,
    }


def test_los_meses_del_abono_se_juntan_sin_repetir_y_ordenados(
    cliente, cuenta, campana, crear_parcela, fertilizante
):
    """Dos abonos en el mismo mes y uno en otro: la lista de meses va ordenada y sin repetir."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _abono(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-05-02", fertilizante["id"], kg_ha=100.0)
    _abono(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-15", fertilizante["id"], kg_ha=50.0)
    _abono(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-05-20", fertilizante["id"], kg_ha=25.0)

    resumen = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])["historial"][0]["resumen"]
    assert resumen["abonos_meses"] == [3, 5]
    assert resumen["abonos_kg_ha"] == 175.0  # la suma de las tres dosis por hectárea


def test_si_a_un_abono_le_falta_el_kg_ha_la_suma_es_null():
    """**La regla del `null`**, probada donde se puede: con un apunte fabricado.

    Hoy el kg/ha del abono es una columna obligatoria, así que la base no puede tener un abono sin
    ella; pero la regla de la casa es que una suma a la que le falta un sumando no es una suma, y eso
    se prueba aquí para que nadie la «arregle» sumando lo que hay.
    """
    con_todo = {
        "siembra": None,
        "labores": [],
        "tratamientos": [],
        "cosecha": None,
        "abonos": [
            {"fecha": "2026-03-01", "mes": 3, "producto": "A", "kg": 100.0, "kg_ha": 250.0},
            {"fecha": "2026-04-01", "mes": 4, "producto": "B", "kg": 100.0, "kg_ha": 150.0},
        ],
    }
    assert nuevo._el_resumen_de_un_anio(con_todo, 2)["abonos_kg_ha"] == 400.0

    falta_uno = {
        **con_todo,
        "abonos": [
            {"fecha": "2026-03-01", "mes": 3, "producto": "A", "kg": 100.0, "kg_ha": 250.0},
            {"fecha": "2026-04-01", "mes": 4, "producto": "B", "kg": None, "kg_ha": None},
        ],
    }
    resumen = nuevo._el_resumen_de_un_anio(falta_uno, 2)
    assert resumen["abonos_kg_ha"] is None
    # Y los meses sí se saben, aunque falte la dosis.
    assert resumen["abonos_meses"] == [3, 4]


def test_un_anio_sin_abonos_no_se_inventa(cliente, cuenta, campana, crear_parcela):
    """Sin abonos, la suma de dosis es 0 (la suma de nada es cero) y la lista de meses va vacía."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-01", apero="arado")

    resumen = _la_tierra(cliente, cuenta["cabeceras"], tierra["id"])["historial"][0]["resumen"]
    assert resumen["abonos_kg_ha"] == 0.0
    assert resumen["abonos_meses"] == []
    assert resumen["cosecha_kg_ha"] is None
    assert resumen["siembra"] is False


# --------------------------------------------------------------------------- calendario (totales)


def test_el_calendario_trae_totales_por_dia_y_del_mes(
    cliente, cuenta, campana, crear_parcela, fertilizante
):
    una = crear_parcela(alias="El Prado", superficie_ha=4.0)
    otra = crear_parcela(alias="La Era", superficie_ha=2.0)

    # El 10: un abono en kilos y un riego en metros cúbicos. **Dos unidades, no se suman.**
    _abono(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-10", fertilizante["id"], kg_ha=300.0)
    _labor(
        cliente, cuenta["cabeceras"], campana["id"], otra["id"], "2026-03-10",
        tipo="riego", superficie_ha=2.0, volumen_agua=300.0, unidad_agua="m3",
    )
    # El 12: una labor con su superficie y otra sin ella: las hectáreas del día no se saben.
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-12", apero="arado")
    _labor(
        cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-12",
        tipo="poda", superficie_ha=None,
    )

    datos = _el_calendario(cliente, cuenta["cabeceras"], desde="2026-03-01", hasta="2026-03-31")
    assert [dia["fecha"] for dia in datos["dias"]] == ["2026-03-10", "2026-03-12"]

    el_diez = datos["dias"][0]["totales"]
    assert el_diez == {
        "n": 2,
        "hectareas": 6.0,
        "cantidades_por_unidad": {"kg": 1200.0, "m3": 300.0},
    }
    el_doce = datos["dias"][1]["totales"]
    assert el_doce == {"n": 2, "hectareas": None, "cantidades_por_unidad": {}}

    # Y el total del mes: lo mismo, sumado, sin mezclar unidades.
    assert datos["totales"]["n"] == 4
    assert datos["totales"]["por_tipo"] == {"abono": 1, "labor": 3}
    assert datos["totales"]["hectareas"] is None
    assert datos["totales"]["cantidades_por_unidad"] == {"kg": 1200.0, "m3": 300.0}


def test_el_calendario_de_un_dia_sin_cantidades_ni_superficie_no_inventa(
    cliente, cuenta, campana, crear_parcela
):
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _labor(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], "2026-03-05",
        tipo="poda", superficie_ha=None,
    )
    datos = _el_calendario(cliente, cuenta["cabeceras"], desde="2026-03-01", hasta="2026-03-31")
    assert datos["dias"][0]["totales"] == {
        "n": 1,
        "hectareas": None,
        "cantidades_por_unidad": {},
    }


# --------------------------------------------------------------------------- filtros de trabajos


def _tres_labores(cliente, cuenta, campana, una, otra) -> None:
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-01", apero="arado")
    _labor(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-04-01", apero="cultivador")
    _labor(
        cliente, cuenta["cabeceras"], campana["id"], otra["id"], "2026-03-02",
        apero="grada", superficie_ha=2.0,
    )


def test_el_filtro_por_tierra_cambia_los_tipos_y_sus_cuentas(cliente, cuenta, campana, crear_parcela):
    una = crear_parcela(alias="El Prado", superficie_ha=4.0)
    otra = crear_parcela(alias="La Era", superficie_ha=2.0)
    _tres_labores(cliente, cuenta, campana, una, otra)

    todos = _los_trabajos(cliente, cuenta["cabeceras"])
    assert {tipo["clave"]: tipo["n"] for tipo in todos["tipos"]} == {
        "arado": 1,
        "cultivador": 1,
        "grada": 1,
    }

    solo_una = _los_trabajos(cliente, cuenta["cabeceras"], parcela_id=una["id"])
    assert {tipo["clave"]: tipo["n"] for tipo in solo_una["tipos"]} == {
        "arado": 1,
        "cultivador": 1,
    }, "las cuentas son de lo filtrado, no de toda la campaña"
    assert {fila["tierra_alias"] for fila in solo_una["trabajos"]} == {"El Prado"}
    assert solo_una["resumen"]["n"] == 2
    assert solo_una["resumen"]["hectareas"] == 8.0


def test_el_filtro_por_fechas_y_el_combinado(cliente, cuenta, campana, crear_parcela):
    una = crear_parcela(alias="El Prado", superficie_ha=4.0)
    otra = crear_parcela(alias="La Era", superficie_ha=2.0)
    _tres_labores(cliente, cuenta, campana, una, otra)

    marzo = _los_trabajos(
        cliente, cuenta["cabeceras"], desde="2026-03-01", hasta="2026-03-31"
    )
    assert {tipo["clave"] for tipo in marzo["tipos"]} == {"arado", "grada"}
    assert [fila["fecha"] for fila in marzo["trabajos"]] == ["2026-03-02", "2026-03-01"]

    combinado = _los_trabajos(
        cliente,
        cuenta["cabeceras"],
        parcela_id=una["id"],
        desde="2026-03-01",
        hasta="2026-03-31",
        tipo="arado",
    )
    assert combinado["elegido"] == "arado"
    assert [fila["fecha"] for fila in combinado["trabajos"]] == ["2026-03-01"]
    assert combinado["resumen"]["n"] == 1
    assert combinado["resumen"]["por_tipo"] == {
        "arado": {"n": 1, "hectareas": 4.0, "cantidades_por_unidad": {}}
    }


def test_las_cantidades_del_resumen_van_por_unidad(
    cliente, cuenta, campana, crear_parcela, fertilizante
):
    """En el resumen de los trabajos, los kilos y los metros cúbicos van cada uno en su sitio."""
    una = crear_parcela(alias="El Prado", superficie_ha=4.0)
    _abono(cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-10", fertilizante["id"], kg_ha=300.0)
    _labor(
        cliente, cuenta["cabeceras"], campana["id"], una["id"], "2026-03-11",
        tipo="riego", volumen_agua=300.0, unidad_agua="m3",
    )

    datos = _los_trabajos(cliente, cuenta["cabeceras"], desde="2026-03-01", hasta="2026-03-31")
    assert datos["resumen"]["cantidades_por_unidad"] == {"kg": 1200.0, "m3": 300.0}
    assert datos["resumen"]["por_tipo"]["abono"]["cantidades_por_unidad"] == {"kg": 1200.0}
    assert datos["resumen"]["por_tipo"]["riego"]["cantidades_por_unidad"] == {"m3": 300.0}
    assert datos["resumen"]["hectareas"] == 8.0


def test_una_tierra_de_otra_finca_contesta_404(cliente, cuenta, crear_cuenta):
    otro = crear_cuenta("otro@ejemplo.test")
    suya = cliente.post(
        "/api/parcelas", headers=otro["cabeceras"], json={"alias": "Tierra ajena", "superficie_ha": 1.0}
    )
    assert suya.status_code == 201, suya.text

    respuesta = cliente.get(
        "/api/nuevo/trabajos", headers=cuenta["cabeceras"], params={"parcela_id": suya.json()["id"]}
    )
    assert respuesta.status_code == 404, respuesta.text


def test_un_rango_al_reves_es_un_422(cliente, cuenta):
    respuesta = cliente.get(
        "/api/nuevo/trabajos",
        headers=cuenta["cabeceras"],
        params={"desde": "2026-03-31", "hasta": "2026-03-01"},
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "anterior" in respuesta.json()["detail"]


def test_un_rango_de_mas_de_un_anio_es_un_422(cliente, cuenta):
    respuesta = cliente.get(
        "/api/nuevo/trabajos",
        headers=cuenta["cabeceras"],
        params={"desde": "2025-01-01", "hasta": "2026-03-01"},
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "año" in respuesta.json()["detail"]


def test_el_filtro_por_fechas_no_se_queda_dentro_de_la_campana_activa(
    cliente, cuenta, campana, crear_parcela
):
    """Pedir un año anterior con `desde`/`hasta` tiene que traerlo: las fechas mandan sobre la campaña."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    de_2025 = _campana(cliente, cuenta["cabeceras"], 2025)
    _labor(cliente, cuenta["cabeceras"], de_2025["id"], tierra["id"], "2025-05-05", apero="grada")

    datos = _los_trabajos(
        cliente, cuenta["cabeceras"], desde="2025-01-01", hasta="2025-12-31"
    )
    assert [fila["fecha"] for fila in datos["trabajos"]] == ["2025-05-05"]

    # Y sin fechas, se mira la campaña activa (2026), donde no hay nada.
    assert _los_trabajos(cliente, cuenta["cabeceras"])["trabajos"] == []
