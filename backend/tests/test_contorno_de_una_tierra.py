"""**Aplicar a una tierra existente el contorno y los datos de una parcela del SIGPAC** (IMP-15).

David quiere el SIGPAC con ventana propia: elegir una parcela y **usarla** en una tierra que ya está
dada de alta. Lo que se comprueba aquí:

  · **Que se escribe lo que manda el SIGPAC**: la forma (y con ella el dibujo, que se calcula solo),
    la superficie SIGPAC, el uso, el coeficiente, la región y la admisibilidad. Y que **lo que el
    SIGPAC manda nulo se queda nulo**, no en un cero (un CSP de 0 en un pasto diría que no se puede
    cobrar, que es una afirmación que nadie ha hecho).
  · **Que no se pisa lo que el agricultor ya había escrito**: si la tierra ya tenía su referencia o su
    municipio, se quedan como estaban.
  · **Que repetir no rompe nada**: la segunda vez no hay cambios ni una segunda fila en el rastro.
  · **Que los errores son los que dicen ser**: 404 si la tierra no es de la finca, 401 sin sesión, 403
    sin permiso **sin llamar al SIGPAC**, 422 si no hay ni referencia ni códigos (o la referencia no
    vale), 409 si el recinto no trae dibujo y 503 si no hay red.

**No se sale a internet**: el SIGPAC se sustituye con `monkeypatch` por lo que contestó de verdad,
que está guardado en `data/sigpac/recinto_de_ejemplo_503_51.json`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import models, sigpac
from test_los_permisos_por_materia import _sin_capacidad  # noqa: E402 — el andamiaje, prestado

RAIZ = Path(__file__).resolve().parents[2]
SIGPAC = RAIZ / "data" / "sigpac"

# La parcela del ejemplo guardado: 37 / 70 / 0 / 0 / 503 / 51 / 1.
SU_REFERENCIA_EN_EL_VISOR = "37:70:0:0:503:51"
SU_REFERENCIA = "37-70-0-0-503-51-1"
SU_MUNICIPIO = "Calvarrasa de Arriba"
SU_PROVINCIA = "Salamanca"


def _el_recinto_de_verdad() -> sigpac.Recinto:
    """El recinto que devolvió el SIGPAC, guardado tal cual (con su wkt y su admisibilidad nula)."""
    guardado = json.loads((SIGPAC / "recinto_de_ejemplo_503_51.json").read_text(encoding="utf-8"))
    recinto = sigpac.lee_recinto(json.dumps(guardado))
    assert recinto is not None and recinto.wkt, "el ejemplo guardado tiene que traer forma"
    return recinto


@pytest.fixture
def sigpac_de_verdad(monkeypatch):
    """El SIGPAC sin salir a internet: contesta lo que contestó y se guardó.

    Se cuenta cada llamada para poder comprobar que **sin permiso no se llama a nadie**.
    """
    recinto = _el_recinto_de_verdad()
    llamadas: dict[str, int] = {"recintos": 0, "recinto": 0}

    def pedir_recintos(busqueda):
        llamadas["recintos"] += 1
        return [recinto]

    def pedir_recinto(referencia):
        llamadas["recinto"] += 1
        return recinto

    monkeypatch.setattr(sigpac, "pedir_recintos", pedir_recintos)
    monkeypatch.setattr(sigpac, "pedir_recinto", pedir_recinto)
    return {"recinto": recinto, "llamadas": llamadas, "monkeypatch": monkeypatch}


def _la_tierra(crear_parcela, **cambios):
    datos = {
        "alias": "El Prado",
        "superficie_ha": 4.0,
        # **Vacía a propósito**: la tierra se apuntó a mano y no tiene nada de la referencia (la
        # fixture de las pruebas trae una por defecto, y aquí se quita para ver que se rellena).
        "ref_sigpac": None,
        "provincia": "",
        "municipio": "",
        "codigo_ine": None,
        "poligono": None,
        "numero_parcela": None,
        "numero_recinto": None,
        "agregado": 0,
        "zona": 0,
    }
    datos.update(cambios)
    return crear_parcela(**datos)


def _la_auditoria():
    """La consulta de las filas del rastro de esta acción, para contar cuántas hay."""
    from sqlalchemy import select

    return select(models.Auditoria).where(
        models.Auditoria.accion == "aplicar_el_contorno_del_sigpac"
    )


def _aplicar(cliente, cabeceras, parcela_id: int, cuerpo: dict):
    return cliente.post(
        f"/api/parcelas/{parcela_id}/contorno", headers=cabeceras, json=cuerpo
    )


# --------------------------------------------------------------------------- sin sesión y permisos


def test_sin_sesion_no_se_aplica_nada(cliente, crear_parcela):
    tierra = crear_parcela(alias="El Prado", superficie_ha=4.0)
    respuesta = cliente.post(
        f"/api/parcelas/{tierra['id']}/contorno", json={"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 401, respuesta.text


def test_sin_permiso_de_modificar_contesta_403_y_no_llama_al_sigpac(
    cliente, cuenta, crear_parcela, db_sesion, sigpac_de_verdad
):
    """**El permiso va antes de la red**: sin capacidad no se pide ni un recinto al FEGA."""
    tierra = _la_tierra(crear_parcela)
    _sin_capacidad(db_sesion, cuenta, "puede_modificar")

    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 403, respuesta.text
    assert sigpac_de_verdad["llamadas"] == {"recintos": 0, "recinto": 0}


def test_una_tierra_de_otra_finca_contesta_404(cliente, cuenta, crear_cuenta):
    otro = crear_cuenta("otro@ejemplo.test")
    suya = cliente.post(
        "/api/parcelas", headers=otro["cabeceras"], json={"alias": "Tierra ajena", "superficie_ha": 1.0}
    )
    assert suya.status_code == 201, suya.text

    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], suya.json()["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 404, respuesta.text


# --------------------------------------------------------------------------- lo que sí hace


def test_aplica_la_forma_y_los_datos_oficiales(
    cliente, cuenta, crear_parcela, db_sesion, sigpac_de_verdad
):
    tierra = _la_tierra(crear_parcela)
    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert datos["actualizada"] is True
    assert datos["recinto"]["referencia"] == SU_REFERENCIA
    assert len(datos["recinto"]["puntos"]) > 3
    # Lo que ha cambiado, campo por campo (y sin el dibujo, que se calcula).
    assert "geometria" in datos["cambios"]
    assert "superficie_sigpac_ha" in datos["cambios"]

    db_sesion.expire_all()
    parcela = db_sesion.get(models.Parcela, tierra["id"])
    assert parcela.geometria == sigpac_de_verdad["recinto"].wkt
    # **El dibujo se calcula solo del WKT**: no es una columna y ahora ya se puede pintar.
    assert parcela.dibujo is not None and parcela.dibujo.startswith("M")
    assert parcela.centro is not None
    # Los datos oficiales del recinto.
    assert parcela.superficie_sigpac_ha == 4.9016
    assert parcela.uso_sigpac == "TA"
    assert parcela.coef_regadio == 0.0
    assert parcela.region == 2
    # **El SIGPAC manda `admisibilidad: null` en este recinto, y se guarda nulo**: un 0 ahí sería
    # afirmar un CSP que nadie ha publicado.
    assert parcela.admisibilidad is None
    # Y la referencia, que estaba vacía, queda puesta con su pueblo y su provincia.
    assert parcela.ref_sigpac == SU_REFERENCIA
    assert (parcela.poligono, parcela.numero_parcela, parcela.numero_recinto) == (503, 51, 1)
    assert parcela.codigo_ine == "37070"
    assert parcela.municipio == SU_MUNICIPIO
    assert parcela.provincia == SU_PROVINCIA
    # Y la respuesta lleva la tierra ya actualizada.
    assert datos["tierra"]["superficie_sigpac_ha"] == 4.9016
    assert datos["tierra"]["coef_regadio"] == 0.0


def test_la_respuesta_de_la_tierra_lleva_lo_que_se_ha_puesto(
    cliente, cuenta, crear_parcela, sigpac_de_verdad
):
    tierra = _la_tierra(crear_parcela)
    datos = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    ).json()
    assert datos["tierra"]["id"] == tierra["id"]
    assert datos["tierra"]["alias"] == "El Prado"
    assert datos["tierra"]["region"] == 2
    assert datos["tierra"]["uso_sigpac"] == "TA"


def test_tambien_vale_con_los_codigos_sueltos(cliente, cuenta, crear_parcela, sigpac_de_verdad):
    """La otra forma de decir la parcela: municipio y provincia de la lista, y los números."""
    tierra = _la_tierra(crear_parcela)
    respuesta = _aplicar(
        cliente,
        cuenta["cabeceras"],
        tierra["id"],
        {
            "municipio": SU_MUNICIPIO,
            "provincia": SU_PROVINCIA,
            "poligono": 503,
            "parcela": 51,
            "recinto": 1,
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["recinto"]["referencia"] == SU_REFERENCIA


def test_no_pisa_lo_que_el_agricultor_ya_habia_escrito(
    cliente, cuenta, crear_parcela, db_sesion, sigpac_de_verdad
):
    """Si la tierra ya tenía su referencia y su pueblo, **manda lo suyo**: no se sobrescribe."""
    tierra = crear_parcela(
        alias="El Prado",
        superficie_ha=4.0,
        ref_sigpac="37-70-0-0-503-51-9",
        municipio="Peñaranda de Bracamonte",
        provincia="Salamanca",
        codigo_ine="37250",
    )
    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 200, respuesta.text

    db_sesion.expire_all()
    parcela = db_sesion.get(models.Parcela, tierra["id"])
    assert parcela.ref_sigpac == "37-70-0-0-503-51-9"
    assert parcela.municipio == "Peñaranda de Bracamonte"
    assert parcela.codigo_ine == "37250"
    # Pero la forma y los datos del recinto sí se ponen: es lo que se ha venido a hacer.
    assert parcela.geometria == sigpac_de_verdad["recinto"].wkt
    assert "ref_sigpac" not in respuesta.json()["cambios"]
    assert "municipio" not in respuesta.json()["cambios"]


def test_repetirlo_no_cambia_nada_ni_apunta_dos_veces(
    cliente, cuenta, crear_parcela, db_sesion, sigpac_de_verdad
):
    """Idempotente: la segunda vez, la tierra igual y `cambios` vacío (y sin segunda fila en el rastro)."""
    tierra = _la_tierra(crear_parcela)
    primera = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert primera.status_code == 200, primera.text
    assert primera.json()["cambios"], "la primera vez sí hay algo que cambiar"

    segunda = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["cambios"] == []
    assert segunda.json()["tierra"] == primera.json()["tierra"]

    db_sesion.expire_all()
    rastro = list(db_sesion.scalars(_la_auditoria()))
    assert len(rastro) == 1, "la acción se apunta una vez, no en cada reintento"


# --------------------------------------------------------------------------- lo que no vale


def test_sin_referencia_ni_codigos_contesta_422(cliente, cuenta, crear_parcela):
    tierra = _la_tierra(crear_parcela)
    respuesta = _aplicar(cliente, cuenta["cabeceras"], tierra["id"], {})
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["detail"]


def test_una_referencia_que_no_se_entiende_contesta_422(cliente, cuenta, crear_parcela):
    tierra = _la_tierra(crear_parcela)
    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": "esto no es una referencia"}
    )
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["detail"]


def test_un_recinto_sin_dibujo_contesta_409(cliente, cuenta, crear_parcela, sigpac_de_verdad):
    """El recinto existe pero no trae forma: no se le pone un cuadro a la tierra."""
    sin_forma = sigpac_de_verdad["recinto"]
    sin_forma.wkt = None
    tierra = _la_tierra(crear_parcela)

    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 409, respuesta.text
    assert "dibujo" in respuesta.json()["detail"]


def test_sin_red_contesta_503(cliente, cuenta, crear_parcela, sigpac_de_verdad):
    def sin_red(referencia):
        raise sigpac.SigpacNoContesta("sin red")

    sigpac_de_verdad["monkeypatch"].setattr(sigpac, "pedir_recinto", sin_red)
    tierra = _la_tierra(crear_parcela)

    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 503, respuesta.text


def test_varios_trozos_sin_decir_cual_contesta_422(cliente, cuenta, crear_parcela, sigpac_de_verdad):
    """Si la parcela tiene varios trozos y no se dice cuál, no se coge «el que salga»."""
    dos = [sigpac_de_verdad["recinto"], sigpac_de_verdad["recinto"]]
    sigpac_de_verdad["monkeypatch"].setattr(sigpac, "pedir_recintos", lambda busqueda: dos)
    tierra = _la_tierra(crear_parcela)

    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 422, respuesta.text
    assert "recinto" in respuesta.json()["detail"]


def test_el_recinto_que_no_existe_contesta_404(cliente, cuenta, crear_parcela, sigpac_de_verdad):
    sigpac_de_verdad["monkeypatch"].setattr(sigpac, "pedir_recinto", lambda referencia: None)
    tierra = _la_tierra(crear_parcela)

    respuesta = _aplicar(
        cliente, cuenta["cabeceras"], tierra["id"], {"referencia": SU_REFERENCIA_EN_EL_VISOR}
    )
    assert respuesta.status_code == 404, respuesta.text
