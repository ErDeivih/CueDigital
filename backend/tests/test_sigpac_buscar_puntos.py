"""**La búsqueda de recintos manda los puntos de la forma** (IMP-4, 05/11/2026).

La ventana del SIGPAC de la app nueva dibuja de golpe los recintos que devuelve una búsqueda, y para
eso no puede depender de `tiene_dibujo`: necesita los puntos. Así que cada recinto trae su `puntos`
en `[longitud, latitud]`, **el mismo lector que usa `/api/nuevo/tierras`** (`geo.puntos_del_wkt`),
para que las dos ventanas dibujen igual.

Dos cosas que se comprueban, y la segunda es la que más importa:

1. Un recinto **con forma** trae sus puntos, y son los de su WKT.
2. Un recinto **sin forma** trae `null`. Un cuadro inventado en el mapa es peor que no dibujar: el
   agricultor marcaría una tierra por la forma de otra.

Y que **no se rompe lo que ya había**: los campos que la pantalla vieja usa (`recinto`, `referencia`,
`superficie_ha`, `uso`, `pendiente_pct`, `tiene_dibujo`, `region`, `admnisibilidad`…) siguen ahí.

**No se sale a internet**: se responde con las respuestas **de verdad** guardadas en `data/sigpac/`
(la misma técnica que `tests/test_parcelas_por_codigos.py`), que es lo que la casa exige — un test que
depende de que el SIGPAC del FEGA esté disponible es una lotería.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import geo

RAIZ = Path(__file__).resolve().parents[2]
SIGPAC = RAIZ / "data" / "sigpac"

# La parcela del ejemplo guardado: 37 / 70 / 0 / 0 / 503 / 51.
SU_PARCELA_EN_EL_VISOR = "37:70:0:0:503:51"


def _guardado(nombre: str):
    return json.loads((SIGPAC / nombre).read_text(encoding="utf-8"))


@pytest.fixture
def sigpac_de_verdad(monkeypatch):
    """El SIGPAC de verdad, sin salir a internet: contesta lo que contestó y se guardó.

    La lista de la búsqueda se monta con **dos recintos** de la misma parcela: el del ejemplo
    guardado y una copia suya con el número 2 (lo único que cambia es el número, para poder mirar en
    la misma respuesta un recinto con forma y otro sin ella). El segundo **no tiene `wkt`**, que es
    como llega un recinto que no tiene dibujo.
    """
    import httpx

    lista = _guardado("recintos_de_ejemplo.json")
    detalle = _guardado("recinto_de_ejemplo_503_51.json")

    segundo = dict(detalle[0])
    segundo["recinto"] = 2
    segundo.pop("wkt")  # un recinto sin forma: el SIGPAC no manda la geometría
    con_forma = dict(detalle[0])

    # La lista con los dos trozos: el guardado y su copia con el recinto 2.
    dos_trozos = json.loads(json.dumps(lista))
    copia = json.loads(json.dumps(lista["features"][0]))
    copia["properties"]["recinto"] = 2
    dos_trozos["features"].append(copia)

    class Respuesta:
        status_code = 200

        def __init__(self, cuerpo):
            self.text = json.dumps(cuerpo)

    def get_falso(url, **kwargs):
        if "collections/recintos" in url:
            return Respuesta(dos_trozos)
        # La dirección de la ficha de un recinto, tal y como la arma `sigpac.url_recinto`:
        # https://…/query/recinfo/37/70/0/0/503/51/1.json
        if url.endswith("/recinfo/37/70/0/0/503/51/1.json"):
            return Respuesta([con_forma])
        if url.endswith("/recinfo/37/70/0/0/503/51/2.json"):
            return Respuesta([segundo])
        return Respuesta([])

    monkeypatch.setattr(httpx, "get", get_falso)
    return {"con_forma": con_forma, "sin_forma": segundo}


def _los_trozos(cliente, cuenta) -> list[dict]:
    respuesta = cliente.post(
        "/api/sigpac/buscar",
        headers=cuenta["cabeceras"],
        json={"referencia": SU_PARCELA_EN_EL_VISOR},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["recintos"]


def test_un_recinto_con_forma_trae_sus_puntos(cliente, cuenta, sigpac_de_verdad):
    trozos = _los_trozos(cliente, cuenta)
    el_primero = trozos[0]

    assert el_primero["recinto"] == 1
    assert el_primero["tiene_dibujo"] is True
    # Los puntos son exactamente los de su forma, en longitud y latitud.
    assert el_primero["puntos"] == [
        [longitud, latitud] for longitud, latitud in geo.puntos_del_wkt(sigpac_de_verdad["con_forma"]["wkt"])
    ]
    # Y son un anillo de verdad: más de tres puntos y todos números.
    assert len(el_primero["puntos"]) > 3
    for longitud, latitud in el_primero["puntos"]:
        assert isinstance(longitud, float) and isinstance(latitud, float)


def test_un_recinto_sin_forma_trae_nulos_y_no_se_inventa_el_dibujo(cliente, cuenta, sigpac_de_verdad):
    trozos = _los_trozos(cliente, cuenta)
    assert len(trozos) == 2, "el ejemplo monta dos recintos, uno con forma y otro sin ella"

    el_segundo = trozos[1]
    assert el_segundo["recinto"] == 2
    assert el_segundo["tiene_dibujo"] is False
    # **Sin forma es `None`**, no una lista vacía ni un cuadro de relleno.
    assert el_segundo["puntos"] is None


def test_no_se_rompe_la_forma_de_la_respuesta_que_ya_habia(cliente, cuenta, sigpac_de_verdad):
    """Los campos que usa la pantalla vieja siguen ahí, con sus mismos nombres y su mismo significado."""
    datos = cliente.post(
        "/api/sigpac/buscar",
        headers=cuenta["cabeceras"],
        json={"referencia": SU_PARCELA_EN_EL_VISOR},
    ).json()

    # La respuesta de la búsqueda, igual que antes.
    assert {"textos", "busqueda", "referencia_catastral", "municipio", "encontrados", "recintos", "mensaje"} <= set(datos)

    trozo = datos["recintos"][0]
    assert {
        "recinto",
        "referencia",
        "superficie_ha",
        "uso_sigpac",
        "uso",
        "pendiente_pct",
        "altitud",
        "coeficiente_regadio",
        "region",
        "admisibilidad",
        "tiene_dibujo",
        "puntos",  # ← lo único nuevo
    } == set(trozo)
    # Y los valores siguen siendo los del recinto de verdad.
    assert trozo["referencia"] == "37-70-0-0-503-51-1"  # las siete partes, con el recinto
    assert trozo["superficie_ha"] == 4.9016
    assert trozo["uso"] == "TIERRAS ARABLES"
    assert trozo["region"] == 2
