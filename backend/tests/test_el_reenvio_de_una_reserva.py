"""**Un reenvio de reserva con la misma clave** (18/10/2026).

*La puerta escribe la clave -`ReservaDeMaquina` tiene su columna y su indice unico-, pero **no la consulta antes**.
Asi que un reenvio choca con el indice: **lo que hay que saber es que contesta**.

*Si contesta 500, es un fallo: el movil que reintenta sin cobertura se lleva un error del servidor en vez de la
reserva que ya tenia.*
"""

from __future__ import annotations


def test_una_reserva_reenviada_con_la_misma_clave_no_revienta(cliente, cuenta):
    """***El reintento devuelve la reserva que ya estaba***, *no un error del servidor.*"""
    maquina = cliente.post(
        "/api/maquinaria",
        headers=cuenta["cabeceras"],
        json={"nombre": "La del reenvio", "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
    ).json()

    lo_que_va = {
        "desde": "2027-03-10T08:00",
        "hasta": "2027-03-10T12:00",
        "estado": "pedida",
        "clave_de_reenvio": "reserva-reenvio",
    }
    primera = cliente.post(
        f"/api/maquinaria/{maquina['id']}/reservas", headers=cuenta["cabeceras"], json=lo_que_va
    )
    assert primera.status_code == 201, primera.text

    repetida = cliente.post(
        f"/api/maquinaria/{maquina['id']}/reservas", headers=cuenta["cabeceras"], json=lo_que_va
    )

    assert repetida.status_code in (200, 201), (
        f"***un reenvio con la misma clave NO puede dar {repetida.status_code}***: "
        f"{repetida.text[:400]}"
    )
    assert repetida.json()["id"] == primera.json()["id"], repetida.json()


def test_y_un_reenvio_con_OTRA_hora_es_un_conflicto_o_lo_que_sea_pero_no_un_500(cliente, cuenta):
    """*Si la misma clave trae otra hora, lo que no puede pasar es un 500.*"""
    maquina = cliente.post(
        "/api/maquinaria",
        headers=cuenta["cabeceras"],
        json={"nombre": "La de la otra hora", "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
    ).json()

    lo_que_va = {
        "desde": "2027-03-11T08:00",
        "hasta": "2027-03-11T12:00",
        "estado": "pedida",
        "clave_de_reenvio": "reserva-otra-hora",
    }
    assert cliente.post(
        f"/api/maquinaria/{maquina['id']}/reservas", headers=cuenta["cabeceras"], json=lo_que_va
    ).status_code == 201

    otra = cliente.post(
        f"/api/maquinaria/{maquina['id']}/reservas",
        headers=cuenta["cabeceras"],
        json={**lo_que_va, "desde": "2027-03-11T15:00", "hasta": "2027-03-11T18:00"},
    )

    assert otra.status_code < 500, f"***ni un 500***: {otra.status_code} {otra.text[:400]}"
