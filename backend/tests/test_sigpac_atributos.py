"""Los tres atributos oficiales del recinto que el SIGPAC manda y hoy se tiran (AGR-3).

### Qué se prueba y por qué

El SIGPAC devuelve, en la consulta de un recinto (`query/recinfo`), tres datos que el programa
leía y **no guardaba**: el coeficiente de regadío (`coef_regadio`), la región de la PAC
(`region`) y el coeficiente de subvencionabilidad en pastos, que en la consulta se llama
`admisibilidad` (CSP, 0–100). Los dos primeros los pide la PAC; el CSP decide si un pasto se
puede cobrar.

**El ejemplo no está inventado**: es la respuesta de verdad del recinto `37/22/0/0/501/427/1`,
bajada el 24/09/2026 con `backend/scripts/bajar_sigpac.py` y guardada en
`data/sigpac/recinto_de_ejemplo.json`. Ese recinto trae `"coef_regadio": 0`, `"region": 2` y
`"admisibilidad": null`, y ahí está justo la trampa: **el 0 del coeficiente es un dato
publicado** (ese recinto tiene coeficiente cero) y **el `null` de la admisibilidad es «no
consta»**. Rellenar el segundo con un 0 afirmaría que ese pasto no se puede cobrar, que es una
declaración, no un hueco.

Los nombres y el significado están verificados en `docs/INVESTIGACION-AGRICOLA.md`, apartado 1.3,
contra el modelo de datos oficial de la descarga
(`https://sigpac-hubcloud.es/html/sdsigpac/modelos/recintos-SIGPAC.html`) y la página de la
consulta del CSP (`https://sigpac-hubcloud.es/html/csp/consultas/codigoSigPac.html`).

**Los tests no salen a internet**: el endpoint se prueba con `httpx.get` sustituido por una
respuesta guardada, igual que `test_sigpac.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import sigpac

RUTA_DATOS = Path(__file__).resolve().parents[2] / "data" / "sigpac"


def respuesta_de_verdad() -> list[dict]:
    """El recinto de verdad del SIGPAC, tal y como lo devuelve el servicio.

    Devuelve una lista con un elemento porque es lo que contesta `recinfo`: un array JSON.
    """
    return json.loads((RUTA_DATOS / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))


class TestElParser:
    """`lee_recinto` tiene que sacar los tres, y no inventar ninguno."""

    def test_el_recinto_de_verdad_trae_su_coeficiente_de_regadio(self):
        recinto = sigpac.lee_recinto(respuesta_de_verdad())
        assert recinto is not None
        # 0 es un valor publicado, no un hueco: por eso se comprueba con `is not None` además de
        # con el número. Un `None` aquí sería «no consta», que es otra cosa.
        assert recinto.coef_regadio is not None
        assert recinto.coef_regadio == 0.0
        assert isinstance(recinto.coef_regadio, float)

    def test_el_recinto_de_verdad_trae_su_region_de_la_pac(self):
        recinto = sigpac.lee_recinto(respuesta_de_verdad())
        assert recinto is not None
        assert recinto.region == 2
        assert isinstance(recinto.region, int)

    def test_la_admisibilidad_nula_es_no_consta_y_nunca_cero(self):
        """El ejemplo real trae `"admisibilidad": null`: no aplica o no consta.

        Es el caso que importa: si aquí saliera un `0.0`, el programa estaría afirmando que ese
        recinto tiene coeficiente de subvencionabilidad cero.
        """
        recinto = sigpac.lee_recinto(respuesta_de_verdad())
        assert recinto is not None
        assert recinto.admisibilidad is None
        assert recinto.admisibilidad != 0

    def test_la_admisibilidad_con_valor_se_lee_como_numero(self):
        """El camino con dato (0–100). Se cambia **solo** ese valor del ejemplo real.

        El recinto guardado viene con `null` porque ese trozo no es pasto; para probar que un CSP
        de verdad se lee hay que ponerle uno, y se dice aquí para que nadie crea que el fichero
        trae un 87,5.
        """
        cuerpo = respuesta_de_verdad()
        cuerpo[0]["admisibilidad"] = 87.5
        recinto = sigpac.lee_recinto(cuerpo)
        assert recinto is not None
        assert recinto.admisibilidad == 87.5

    def test_un_campo_que_no_viene_queda_en_none_y_no_en_cero(self):
        """Un SIGPAC que no manda el campo no está diciendo «cero»: está callando."""
        cuerpo = respuesta_de_verdad()
        for campo in ("coef_regadio", "region", "admisibilidad"):
            del cuerpo[0][campo]
        recinto = sigpac.lee_recinto(cuerpo)
        assert recinto is not None
        assert recinto.coef_regadio is None
        assert recinto.region is None
        assert recinto.admisibilidad is None

    def test_un_valor_que_no_es_un_numero_queda_en_none_y_no_en_cero(self):
        """Si el servicio contesta texto raro, no se convierte en 0 ni se propaga el texto."""
        cuerpo = respuesta_de_verdad()
        cuerpo[0]["coef_regadio"] = "no consta"
        cuerpo[0]["region"] = ""
        cuerpo[0]["admisibilidad"] = "sin dato"
        recinto = sigpac.lee_recinto(cuerpo)
        assert recinto is not None
        assert recinto.coef_regadio is None
        assert recinto.region is None
        assert recinto.admisibilidad is None


class TestElAltaLosGuarda:
    """Dar de alta desde el SIGPAC tiene que dejar los tres en la parcela, y en la base."""

    @pytest.fixture
    def servidor_sigpac(self, monkeypatch):
        """`httpx.get` sustituido por el recinto de verdad guardado en el repositorio."""
        import httpx

        crudo = respuesta_de_verdad()

        class RespuestaFalsa:
            status_code = 200

            def __init__(self):
                self.text = json.dumps(crudo)

            def raise_for_status(self):
                return None

        llamadas: list[str] = []

        def get_falso(url, **kwargs):
            llamadas.append(url)
            return RespuestaFalsa()

        monkeypatch.setattr(httpx, "get", get_falso)
        return llamadas

    def test_la_parcela_trae_los_tres_y_se_guardan(
        self, cliente, cuenta, servidor_sigpac, db_sesion
    ):
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1", "alias": "El Prado"},
        )
        assert respuesta.status_code == 201, respuesta.text
        parcela = respuesta.json()
        assert parcela["coef_regadio"] == 0.0
        assert parcela["region"] == 2
        assert parcela["admisibilidad"] is None, "nulo = no consta, no 0"
        # Y lo mismo en la base: la respuesta podría mentir.
        from sqlalchemy import select

        from app import models

        guardada = db_sesion.scalar(select(models.Parcela))
        assert guardada is not None
        assert guardada.coef_regadio == 0.0
        assert guardada.region == 2
        assert guardada.admisibilidad is None

    def test_el_uso_del_recinto_no_se_pierde_al_guardar(
        self, cliente, cuenta, servidor_sigpac
    ):
        """El uso ya se copiaba; se comprueba que sigue copiándose junto a los tres nuevos."""
        parcela = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1"},
        ).json()
        assert parcela["uso_sigpac"] == "TA"

    def test_la_via_de_varias_tambien_los_guarda(
        self, cliente, cuenta, servidor_sigpac, db_sesion
    ):
        """Los dos caminos usan el mismo alta (`_alta_desde_recinto`), y esto lo ata."""
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac/varias",
            headers=cuenta["cabeceras"],
            json={"referencias": ["37-22-0-0-501-427-1"]},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["cuantas"] == 1
        from sqlalchemy import select

        from app import models

        guardada = db_sesion.scalar(select(models.Parcela))
        assert guardada.coef_regadio == 0.0
        assert guardada.region == 2
        assert guardada.admisibilidad is None

    def test_la_busqueda_de_trozos_ensena_los_tres_atributos(
        self, cliente, cuenta, monkeypatch
    ):
        """Al elegir el trozo hay que poder ver su región y su CSP antes de traerlo.

        El listado de trozos (OGC API Features) **no trae estos tres campos**: solo la pendiente y
        la altitud. Vienen de la consulta del recinto, que es la que se hace después por cada
        trozo; por eso lo que se enseña es el detalle completo, no la lista.
        """
        import httpx

        el_suyo = json.loads(
            (RUTA_DATOS / "recinto_de_ejemplo_503_51.json").read_text(encoding="utf-8")
        )
        trozos = json.loads(
            (RUTA_DATOS / "recintos_de_ejemplo.json").read_text(encoding="utf-8")
        )

        class Respuesta:
            status_code = 200

            def __init__(self, cuerpo):
                self.text = json.dumps(cuerpo)

            def raise_for_status(self):
                return None

        def get_falso(url, **kwargs):
            if "collections/recintos" in url:
                return Respuesta(trozos)
            if "recinfo/" in url:
                return Respuesta(el_suyo)
            return Respuesta([])

        monkeypatch.setattr(httpx, "get", get_falso)
        respuesta = cliente.post(
            "/api/sigpac/buscar",
            headers=cuenta["cabeceras"],
            json={"referencia": "37:70:0:0:503:51"},
        )
        assert respuesta.status_code == 200, respuesta.text
        trozo = respuesta.json()["recintos"][0]
        assert trozo["region"] == 2
        assert trozo["admisibilidad"] is None
        assert trozo["coeficiente_regadio"] == 0.0
