"""**La puerta del apero**: el subtipo de una labor de suelo se apunta y se guarda (IMP-9, 05/11/2026).

El hueco que cierra: `models.Labor.subtipo` existe desde el T15 y `trabajos_api._el_subtipo` la lee,
pero **`LaborEntrada` no aceptaba `subtipo`**, así que el apero (rodillo, cultivador, arado, grada,
fresadora) solo entraba por `detalles` —un JSON del que no se puede consultar ni sumar—. La app nueva
manda `subtipo` en el alta de la labor y este es el contrato:

  · **Se guarda en su columna**, y se lee de vuelta (la ficha de la tierra y el historial ya lo
    enseñan con `_el_subtipo`).
  · **Se comprueba contra el vocabulario del programa** (`trabajos.SUBTIPOS_DE_LABOREO`): un apero que
    no está se contesta con **422 y la lista de los que valen**.
  · **Solo en una labor de suelo**: un apero en una poda no significa nada y se rechaza.
  · **No es obligatorio**: una labor de suelo sin apero se sigue apuntando igual, y la app vieja —que
    no manda el campo— no se rompe. Lo que ya estaba en `detalles` se sigue aceptando.

Las pruebas usan las puertas de verdad (TestClient) y miran la columna en la base: lo que se comprueba
es que el dato queda guardado donde se puede consultar, no solo que la petición responda 201.
"""

from __future__ import annotations

import pytest

from app import models, trabajos

CAMPANA_DE_EJEMPLO = 2026


def _una_labor(cliente, cabeceras, campana_id: int, parcela_id: int, **cambios):
    datos = {
        "campana_id": campana_id,
        "tipo": "laboreo",
        "fecha": "2026-03-10",
        "parcela_id": parcela_id,
        "superficie_ha": 4.0,
    }
    datos.update(cambios)
    return cliente.post("/api/labores", headers=cabeceras, json=datos)


def _el_apero_guardado(db_sesion, labor_id: int) -> str | None:
    """El apero **en su columna**, que es donde tiene que estar."""
    db_sesion.expire_all()
    labor = db_sesion.get(models.Labor, labor_id)
    assert labor is not None, "la labor tiene que estar guardada"
    return labor.subtipo


# --------------------------------------------------------------------------- sin sesión


def test_sin_sesion_no_se_apunta_el_apero(cliente):
    respuesta = cliente.post(
        "/api/labores",
        json={"campana_id": 1, "tipo": "laboreo", "fecha": "2026-03-10", "subtipo": "arado"},
    )
    assert respuesta.status_code == 401, respuesta.text


# --------------------------------------------------------------------------- el apero se guarda


def test_el_apero_se_guarda_en_su_columna(cliente, cuenta, campana, crear_parcela, db_sesion):
    """`subtipo="arado"` en el alta: se guarda en la columna y se lee de vuelta."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = _una_labor(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], subtipo="arado"
    )
    assert respuesta.status_code == 201, respuesta.text

    assert _el_apero_guardado(db_sesion, respuesta.json()["id"]) == "arado"

    # Y la ficha de la tierra (que lee con `_el_subtipo`) lo enseña como un trabajo de arado.
    ficha = cliente.get(f"/api/nuevo/tierra/{tierra['id']}", headers=cuenta["cabeceras"]).json()
    labores = [labor for anio in ficha["historial"] for labor in anio["labores"]]
    assert [labor["labor"] for labor in labores] == ["arado"]
    assert labores[0]["titulo"] == "Arado"


@pytest.mark.parametrize("apero", list(trabajos.SUBTIPOS_DE_LABOREO))
def test_todos_los_aperos_del_vocabulario_valen(
    cliente, cuenta, campana, crear_parcela, db_sesion, apero
):
    """Los seis del catálogo entran y se guardan: la lista del programa y la de la puerta son la misma."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = _una_labor(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], subtipo=apero
    )
    assert respuesta.status_code == 201, respuesta.text
    assert _el_apero_guardado(db_sesion, respuesta.json()["id"]) == apero


def test_el_apero_se_normaliza(cliente, cuenta, campana, crear_parcela, db_sesion):
    """Espacios de más y mayúsculas: se guarda la palabra del catálogo, no lo que venga."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = _una_labor(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], subtipo="  grada  "
    )
    assert respuesta.status_code == 201, respuesta.text
    assert _el_apero_guardado(db_sesion, respuesta.json()["id"]) == "grada"


# --------------------------------------------------------------------------- lo que no vale


def test_un_apero_que_no_esta_dice_cuales_valen(cliente, cuenta, campana, crear_parcela):
    """«Vertedera» no está en el vocabulario del programa: 422 y la lista de los que sí."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = _una_labor(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], subtipo="vertedera"
    )
    assert respuesta.status_code == 422, respuesta.text
    # El mensaje tiene que servir para corregirlo: nombra los que valen.
    for apero in trabajos.SUBTIPOS_DE_LABOREO:
        assert apero in respuesta.text, (apero, respuesta.text)
    # Y no se ha guardado nada: no queda una labor a medias sin apero.
    assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).status_code == 200
    assert cliente.get("/api/labores", headers=cuenta["cabeceras"]).json() == []


def test_el_apero_solo_vale_en_una_labor_de_suelo(cliente, cuenta, campana, crear_parcela):
    """Un apero en una poda no significa nada: se rechaza con 422 en vez de guardarlo."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = _una_labor(
        cliente,
        cuenta["cabeceras"],
        campana["id"],
        tierra["id"],
        tipo="poda",
        subtipo="arado",
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "laboreo" in respuesta.text
    assert cliente.get("/api/labores", headers=cuenta["cabeceras"]).json() == []


# --------------------------------------------------------------------------- no rompe lo de antes


def test_sin_apero_la_labor_se_sigue_apuntando(cliente, cuenta, campana, crear_parcela, db_sesion):
    """No es obligatorio: la app vieja no lo manda y una labor de suelo sin apero es una labor."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = _una_labor(cliente, cuenta["cabeceras"], campana["id"], tierra["id"])
    assert respuesta.status_code == 201, respuesta.text
    assert _el_apero_guardado(db_sesion, respuesta.json()["id"]) is None


def test_lo_que_ya_estaba_en_detalles_se_sigue_aceptando(
    cliente, cuenta, campana, crear_parcela, db_sesion
):
    """Compatibilidad: el asistente guardaba el apero en `detalles`. Sigue entrando, y ahora en su columna."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = _una_labor(
        cliente,
        cuenta["cabeceras"],
        campana["id"],
        tierra["id"],
        detalles={"subtipo": "grada"},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert _el_apero_guardado(db_sesion, respuesta.json()["id"]) == "grada"


# --------------------------------------------------------------------------- la otra puerta del alta


def _un_trabajo(cliente, cabeceras, campana_id: int, parcela_id: int, **cambios):
    datos = {
        "campana_id": campana_id,
        "tipo": "laboreo",
        "fecha": "2026-03-10",
        "parcela_id": parcela_id,
        "superficie_ha": 4.0,
    }
    datos.update(cambios)
    return cliente.post("/api/trabajos", headers=cabeceras, json=datos)


def test_la_puerta_de_los_trabajos_tambien_valida_el_apero(
    cliente, cuenta, campana, crear_parcela, db_sesion
):
    """`POST /api/trabajos` es la otra puerta del alta de una labor: misma regla y mismo 422."""
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)

    bien = _un_trabajo(cliente, cuenta["cabeceras"], campana["id"], tierra["id"], subtipo="rodillo")
    assert bien.status_code == 201, bien.text
    assert _el_apero_guardado(db_sesion, bien.json()["hecho"]["id"]) == "rodillo"

    mal = _un_trabajo(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], subtipo="vertedera"
    )
    assert mal.status_code == 422, mal.text
    assert "cultivador" in mal.text

    fuera_de_suelo = _un_trabajo(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], tipo="poda", subtipo="arado"
    )
    assert fuera_de_suelo.status_code == 422, fuera_de_suelo.text


# --------------------------------------------------------------------------- y se lee de vuelta


def test_la_salida_del_cuaderno_tambien_devuelve_el_apero(cliente, cuenta, campana, crear_parcela):
    """`GET /api/labores` devuelve `subtipo`: el dato se guarda **y se puede leer por su puerta**.

    Faltaba en `LaborSalida` desde el T15: el apero viajaba en la columna y la ficha lo enseñaba, pero
    la lista del cuaderno no lo devolvía, así que la pantalla que lo apunta no podía comprobar lo que
    había guardado. Es la familia de «dato guardado y sin puerta de vuelta», que este proyecto ya pagó
    varias veces.
    """
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    creada = _una_labor(
        cliente, cuenta["cabeceras"], campana["id"], tierra["id"], subtipo="fresadora"
    )
    assert creada.status_code == 201, creada.text

    listado = cliente.get(
        f"/api/labores?campana_id={campana['id']}", headers=cuenta["cabeceras"]
    )
    assert listado.status_code == 200, listado.text
    labores = {labor["id"]: labor for labor in listado.json()}
    assert labores[creada.json()["id"]]["subtipo"] == "fresadora"

