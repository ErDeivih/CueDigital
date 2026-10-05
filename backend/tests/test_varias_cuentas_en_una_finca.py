"""Varias cuentas en la misma finca (ronda 89).

POR QUÉ ESTAS PRUEBAS

Hasta la ronda 89 una cuenta estaba atada a una finca. David lo pidió al revés: «quiero que una
explotación puedan acceder varias cuentas, no solo 1». Lo que hay que poder demostrar aquí es que eso se
hizo **sin romper el aislamiento**, que es la regla de seguridad del proyecto: cada finca sigue viendo solo
lo suyo y lo de otra finca sigue contestando 404.

Las cuatro cosas que se prueban:

  1. Que el titular puede dar acceso a otra cuenta y las dos ven **los mismos datos**.
  2. Que un ayudante usa la finca entera pero **no decide quién entra**.
  3. Que **quitar el acceso lo quita de verdad**: ni la finca en la lista, ni el vale viejo sirve, ni se
     puede cambiar a ella.
  4. Que una instalación de antes sigue funcionando: la cuenta que ya existía **sin** acceso a su finca se
     queda con él al arrancar (`asegurar_accesos`), que es lo que evita que al actualizar nadie pueda
     entrar.
"""

from __future__ import annotations

import pytest

from app import accesos, models
from app.database import SessionLocal


def _crear_parcela(cliente, cabeceras, alias: str = "El Prado") -> dict:
    respuesta = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={
            "alias": alias,
            "ref_sigpac": "37-455-12-3",
            "superficie_ha": 2.43,
            "superficie_oficial": True,
            "sistema": "secano",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


class TestQuienEntraEnMiFinca:
    def test_una_cuenta_nueva_es_titular_de_su_finca(self, cliente, cuenta):
        fincas = cliente.get("/api/fincas", headers=cuenta["cabeceras"]).json()
        assert len(fincas) == 1, fincas
        assert fincas[0]["papel"] == "titular"
        assert fincas[0]["activa"] is True, "su finca no sale como la que está usando"
        assert fincas[0]["nombre"] == "David Pérez Velasco"

        quien = cliente.get("/api/fincas/quien-entra", headers=cuenta["cabeceras"]).json()
        assert quien["soy_titular"] is True
        assert len(quien["personas"]) == 1
        assert quien["personas"][0]["eres_tu"] is True
        assert quien["personas"][0]["papel"] == "titular"

    def test_el_titular_da_acceso_a_otra_cuenta_y_las_dos_ven_lo_mismo(
        self, cliente, cuenta, crear_cuenta
    ):
        """**La prueba que importa**: dos cuentas, un cuaderno."""
        _crear_parcela(cliente, cuenta["cabeceras"])
        ayuda = crear_cuenta("mujer@ejemplo.test", nombre="María")

        # Al principio la otra cuenta no ve la finca de David.
        assert len(cliente.get("/api/fincas", headers=ayuda["cabeceras"]).json()) == 1

        anadida = cliente.post(
            "/api/fincas/quien-entra",
            headers=cuenta["cabeceras"],
            json={"correo": "mujer@ejemplo.test"},
        )
        assert anadida.status_code == 201, anadida.text
        personas = {p["correo"]: p for p in anadida.json()["personas"]}
        assert personas["mujer@ejemplo.test"]["papel"] == "ayudante"
        assert personas["david@ejemplo.test"]["papel"] == "titular"

        # Ahora esa cuenta ve las dos fincas: la suya y la de David, y puede ponerse en la de David.
        suyas = cliente.get("/api/fincas", headers=ayuda["cabeceras"]).json()
        assert len(suyas) == 2, suyas
        de_david = [f for f in suyas if f["nombre"] == "David Pérez Velasco"]
        assert len(de_david) == 1 and de_david[0]["papel"] == "ayudante"

        cambio = cliente.post(
            "/api/fincas/cambiar",
            headers=ayuda["cabeceras"],
            json={"explotacion_id": de_david[0]["id"]},
        )
        assert cambio.status_code == 200, cambio.text
        vale_nuevo = {"Authorization": f"Bearer {cambio.json()['token']}"}

        # **Y ve las tierras de la finca de David**, que es lo que se ha pedido: el mismo cuaderno.
        parcelas = cliente.get("/api/parcelas", headers=vale_nuevo).json()
        assert [p["alias"] for p in parcelas] == ["El Prado"], parcelas
        # Y su finca propia sigue estando, sin tierras.
        vuelta = cliente.post(
            "/api/fincas/cambiar",
            headers=vale_nuevo,
            json={"explotacion_id": ayuda["explotacion_id"]},
        )
        assert vuelta.status_code == 200, vuelta.text
        vale_suyo = {"Authorization": f"Bearer {vuelta.json()['token']}"}
        assert cliente.get("/api/parcelas", headers=vale_suyo).json() == []
        # Y su finca propia vuelve a ser la que está usando.
        fincas_suyas = cliente.get("/api/fincas", headers=vale_suyo).json()
        assert [
            f["id"] for f in fincas_suyas if f["activa"]
        ] == [ayuda["explotacion_id"]], fincas_suyas

    def test_un_ayudante_usa_la_finca_pero_no_decide_quién_entra(
        self, cliente, cuenta, crear_cuenta
    ):
        ayuda = crear_cuenta("hijo@ejemplo.test", nombre="Hijo")
        cliente.post(
            "/api/fincas/quien-entra",
            headers=cuenta["cabeceras"],
            json={"correo": "hijo@ejemplo.test"},
        )
        cambio = cliente.post(
            "/api/fincas/cambiar",
            headers=ayuda["cabeceras"],
            json={"explotacion_id": cuenta["explotacion_id"]},
        )
        vale = {"Authorization": f"Bearer {cambio.json()['token']}"}

        # Apuntar, sí: es el mismo cuaderno y tiene que poder trabajar.
        parcela = _crear_parcela(cliente, vale, alias="La Vega")
        assert parcela["alias"] == "La Vega"

        # Decidir quién entra, no.
        otro = crear_cuenta("vecino@ejemplo.test", nombre="Vecino")
        meter = cliente.post(
            "/api/fincas/quien-entra",
            headers=vale,
            json={"correo": "vecino@ejemplo.test"},
        )
        assert meter.status_code == 403, meter.text

        quitar = cliente.request(
            "DELETE",
            f"/api/fincas/quien-entra/{otro['usuario_id']}",
            headers=vale,
        )
        assert quitar.status_code == 404, "no debería ni poder mirar a quién quitar"

        # Y lo que sí puede es quitarse él mismo.
        largarse = cliente.request(
            "DELETE",
            f"/api/fincas/quien-entra/{ayuda['usuario_id']}",
            headers=vale,
        )
        assert largarse.status_code == 200, largarse.text

    def test_quitar_el_acceso_lo_quita_de_verdad(self, cliente, cuenta, crear_cuenta):
        """Ni sale en la lista, ni vale el vale viejo, ni se puede cambiar a esa finca."""
        _crear_parcela(cliente, cuenta["cabeceras"])
        ayuda = crear_cuenta("tecnico@ejemplo.test", nombre="Técnico")
        cliente.post(
            "/api/fincas/quien-entra",
            headers=cuenta["cabeceras"],
            json={"correo": "tecnico@ejemplo.test"},
        )
        cambio = cliente.post(
            "/api/fincas/cambiar",
            headers=ayuda["cabeceras"],
            json={"explotacion_id": cuenta["explotacion_id"]},
        )
        vale_de_david = {"Authorization": f"Bearer {cambio.json()['token']}"}
        assert cliente.get("/api/parcelas", headers=vale_de_david).status_code == 200

        quitar = cliente.request(
            "DELETE",
            f"/api/fincas/quien-entra/{ayuda['usuario_id']}",
            headers=cuenta["cabeceras"],
        )
        assert quitar.status_code == 200, quitar.text

        # 1. Ya no está en la lista de quien entra.
        quien = cliente.get("/api/fincas/quien-entra", headers=cuenta["cabeceras"]).json()
        assert [p["correo"] for p in quien["personas"]] == ["david@ejemplo.test"]
        # 2. El vale viejo ya no vale.
        assert cliente.get("/api/parcelas", headers=vale_de_david).status_code == 401
        # 3. Y no se puede volver a cambiar a esa finca.
        volver = cliente.post(
            "/api/fincas/cambiar",
            headers=ayuda["cabeceras"],
            json={"explotacion_id": cuenta["explotacion_id"]},
        )
        assert volver.status_code == 404, volver.text
        # 4. Y esa cuenta sigue teniendo la suya, para no quedarse sin trabajar.
        fincas = cliente.get("/api/fincas", headers=ayuda["cabeceras"]).json()
        assert len(fincas) == 1 and fincas[0]["papel"] == "titular"

    def test_el_titular_no_se_puede_quitar_de_su_finca(self, cliente, cuenta):
        """Una finca sin titular se queda sin quien la gestiona."""
        quitar = cliente.request(
            "DELETE",
            f"/api/fincas/quien-entra/{cuenta['usuario_id']}",
            headers=cuenta["cabeceras"],
        )
        assert quitar.status_code == 409, quitar.text
        # Y la finca sigue siendo suya.
        assert cliente.get("/api/fincas", headers=cuenta["cabeceras"]).json()[0]["activa"] is True

    def test_no_se_puede_dar_acceso_a_una_cuenta_que_no_existe(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/fincas/quien-entra",
            headers=cuenta["cabeceras"],
            json={"correo": "nadie@ejemplo.test"},
        )
        assert respuesta.status_code == 404
        assert "dé de alta primero" in respuesta.json()["detail"], respuesta.json()

    def test_no_se_puede_dar_dos_veces_el_mismo_acceso(self, cliente, cuenta, crear_cuenta):
        crear_cuenta("repetida@ejemplo.test", nombre="Repetida")
        primera = cliente.post(
            "/api/fincas/quien-entra",
            headers=cuenta["cabeceras"],
            json={"correo": "repetida@ejemplo.test"},
        )
        assert primera.status_code == 201
        segunda = cliente.post(
            "/api/fincas/quien-entra",
            headers=cuenta["cabeceras"],
            json={"correo": "repetida@ejemplo.test"},
        )
        assert segunda.status_code == 409, segunda.text


class TestElAislamientoNoSeRompe:
    def test_una_finca_que_no_es_tuya_no_se_puede_elegir(
        self, cliente, cuenta, crear_cuenta
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.post(
            "/api/fincas/cambiar",
            headers=otro["cabeceras"],
            json={"explotacion_id": cuenta["explotacion_id"]},
        )
        assert respuesta.status_code == 404, respuesta.text
        # Y sigue viendo lo suyo, que no tiene nada.
        assert cliente.get("/api/parcelas", headers=otro["cabeceras"]).json() == []

    def test_un_vale_de_una_finca_sin_acceso_no_vale(self, cliente, cuenta, crear_cuenta):
        """Un vale viejo (o hecho a mano) para una finca que no es tuya no sirve para nada."""
        from app import security

        otro = crear_cuenta("curioso@ejemplo.test")
        falso = security.crear_token(otro["usuario_id"], cuenta["explotacion_id"])
        respuesta = cliente.get(
            "/api/parcelas", headers={"Authorization": f"Bearer {falso}"}
        )
        assert respuesta.status_code == 401, respuesta.text

    def test_lo_de_otra_finca_sigue_contestando_404(
        self, cliente, cuenta, crear_cuenta
    ):
        parcela = _crear_parcela(cliente, cuenta["cabeceras"])
        otro = crear_cuenta("ajeno@ejemplo.test")
        assert cliente.get(f"/api/parcelas/{parcela['id']}", headers=otro["cabeceras"]).status_code == 404


class TestUnaInstalacionDeAntes:
    def test_la_cuenta_que_ya_existia_se_queda_con_su_acceso(self, cliente, cuenta):
        """Es lo que evita que, al actualizar el programa, nadie pueda entrar.

        Se simula la instalación de antes borrando el acceso a mano (como estaría en una base de datos
        anterior a esta ronda) y se llama a `asegurar_accesos`, que es lo que hace el programa al arrancar.
        """
        with SessionLocal() as sesion:
            for fila in sesion.query(models.AccesoAFinca).all():
                sesion.delete(fila)
            sesion.commit()

        # Sin acceso, el vale no vale: no se puede entrar en una finca sin permiso.
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).status_code == 401

        with SessionLocal() as sesion:
            puestos = accesos.asegurar_accesos(sesion)
        assert puestos == 1, puestos

        # Y con el acceso puesto, todo vuelve a funcionar.
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).status_code == 200
        fincas = cliente.get("/api/fincas", headers=cuenta["cabeceras"]).json()
        assert len(fincas) == 1 and fincas[0]["papel"] == "titular"

    def test_asegurar_accesos_no_repite_ni_pisa_nada(self, cliente, cuenta):
        """Se puede llamar todas las veces que haga falta: es lo que hace el arranque."""
        with SessionLocal() as sesion:
            assert accesos.asegurar_accesos(sesion) == 0
            assert accesos.asegurar_accesos(sesion) == 0
        assert len(cliente.get("/api/fincas", headers=cuenta["cabeceras"]).json()) == 1


class TestLasHectareasDeCadaFinca:
    """Cuántas hectáreas tiene cada finca, en la lista de fincas (ronda 90).

    Lo pidió el diseño de Stitch de «quién entra en mi finca»: al elegir en qué finca trabajas, el tamaño es
    lo que distingue una finca de otra cuando se llaman parecido. Es una cuenta hecha con datos que ya
    tenemos —la suma de las tierras de esa finca— y la hace el servidor, que es de quien es el dato.
    """

    def test_la_finca_dice_sus_hectareas(self, cliente, cuenta):
        for alias in ("El Prado", "La Vega"):
            _crear_parcela(cliente, cuenta["cabeceras"], alias=alias)

        fincas = cliente.get("/api/fincas", headers=cuenta["cabeceras"]).json()
        # Cada tierra de `_crear_parcela` tiene 2,43 ha.
        assert fincas[0]["hectareas"] == pytest.approx(4.86, abs=0.01), fincas[0]

    def test_sin_tierras_apuntadas_son_cero(self, cliente, cuenta):
        """Un cero aquí no es un dato inventado: es que esa finca no tiene tierras apuntadas todavía."""
        fincas = cliente.get("/api/fincas", headers=cuenta["cabeceras"]).json()
        assert fincas[0]["hectareas"] == 0.0

    def test_cada_finca_dice_las_suyas_y_no_las_de_la_otra(self, cliente, cuenta, crear_cuenta):
        """La suma va por finca, como todo lo demás en este programa."""
        _crear_parcela(cliente, cuenta["cabeceras"])
        otra = crear_cuenta(correo="ana@ejemplo.test", nombre="Ana")
        for alias in ("Las del río", "La Isla", "El Soto"):
            _crear_parcela(cliente, otra["cabeceras"], alias=alias)
        # Ana (titular de su finca) le da acceso a David, así que David puede entrar en las dos y su lista
        # trae las hectáreas de cada una.
        respuesta = cliente.post(
            "/api/fincas/quien-entra",
            headers=otra["cabeceras"],
            json={"correo": "david@ejemplo.test"},
        )
        assert respuesta.status_code == 201, respuesta.text

        suyas = {
            finca["id"]: finca["hectareas"]
            for finca in cliente.get("/api/fincas", headers=cuenta["cabeceras"]).json()
        }
        assert len(suyas) == 2, suyas
        assert suyas[cuenta["explotacion_id"]] == pytest.approx(2.43, abs=0.01), suyas
        assert suyas[otra["explotacion_id"]] == pytest.approx(7.29, abs=0.01), suyas
