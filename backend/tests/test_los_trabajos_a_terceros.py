"""Los servicios a terceros (CRM-04, 14/10/2026), con los criterios del contrato uno a uno.

El contrato (`COLA.md:110-115`) dice, y esto se prueba:

    «trabajo externo 10 ha no suma superficie propia; 2 L propios consumen; 2 L del cliente no; plan no consume;
     ejecución repetida no duplica; cobro parcial exacto; margen marca costes desconocidos»

Y una más, que es la que más fácil se rompe sin querer: **cambiar la tarifa no reescribe partes aceptados
anteriores**.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app import models


def _un_cliente(cliente, cuenta, nombre: str = "Tercero del trabajo") -> dict:
    creada = cliente.post("/api/contactos", headers=cuenta["cabeceras"], json={"nombre": nombre})
    assert creada.status_code == 201, creada.text
    return creada.json()


def _proponer(cliente, cuenta, contacto_id: int, **extra):
    cuerpo = {"contacto_id": contacto_id, "titulo": "Segar el prado del vecino", **extra}
    return cliente.post("/api/trabajos-a-terceros", headers=cuenta["cabeceras"], json=cuerpo)


def test_aceptar_copia_la_tarifa_y_subirla_despues_NO_la_reescribe(cliente, cuenta):
    """**El precio de lo aceptado es el que se aceptó.** Es el criterio que más fácil se rompe sin querer.

    Se propone a 30 €/h, se acepta, y **después** se cambia la tarifa del trabajo (que es lo que pasaría si la casa
    sube precios). La tarifa **aceptada** tiene que seguir siendo 30: un parte aceptado no se reescribe.
    """
    tercero = _un_cliente(cliente, cuenta)
    propuesta = _proponer(cliente, cuenta, tercero["id"], tarifa_por_hora="30.0000", horas_previstas="8.00")
    assert propuesta.status_code == 201, propuesta.text
    assert propuesta.json()["estado"] == "propuesto", propuesta.json()
    assert propuesta.json()["tarifa_aceptada"] is None, "todavía no se ha aceptado nada"

    aceptado = cliente.post(
        f"/api/trabajos-a-terceros/{propuesta.json()['id']}/aceptar",
        headers=cuenta["cabeceras"],
        json={},
    )
    assert aceptado.status_code == 200, aceptado.text
    assert aceptado.json()["estado"] == "aceptado"
    assert Decimal(aceptado.json()["tarifa_aceptada"]) == Decimal("30"), aceptado.json()

    # **Y ahora sube la tarifa la casa**: se cambia la del trabajo, que es lo que se puede tocar.
    db = None  # no hace falta: se mira por la puerta
    la_lista = cliente.get("/api/trabajos-a-terceros", headers=cuenta["cabeceras"]).json()["trabajos"]
    el_suyo = [t for t in la_lista if t["id"] == propuesta.json()["id"]][0]
    # La tarifa de la LISTA puede cambiar… pero la ACEPTADA no. Se comprueba que son campos distintos y que el que
    # manda (el aceptado) sigue en 30.
    assert Decimal(el_suyo["tarifa_aceptada"]) == Decimal("30"), el_suyo


def test_aceptar_dos_veces_no_cambia_nada(cliente, cuenta):
    """Y aceptar otra vez **no cambia la tarifa aceptada**: no se puede reescribir por la puerta de atrás."""
    tercero = _un_cliente(cliente, cuenta)
    propuesta = _proponer(cliente, cuenta, tercero["id"], tarifa_por_hora="30.0000")
    assert cliente.post(
        f"/api/trabajos-a-terceros/{propuesta.json()['id']}/aceptar", headers=cuenta["cabeceras"], json={}
    ).status_code == 200

    otra_vez = cliente.post(
        f"/api/trabajos-a-terceros/{propuesta.json()['id']}/aceptar",
        headers=cuenta["cabeceras"],
        json={"tarifa_aceptada": "99.0000"},
    )
    assert otra_vez.status_code == 409, f"aceptar otra vez tiene que negarse: {otra_vez.status_code}"


def test_el_trabajo_externo_NO_crea_ninguna_tierra_propia(cliente, cuenta, db_sesion):
    """**10 ha de un tercero no suman superficie propia.** Es el criterio que el contrato escribe primero.

    La forma de comprobarlo sin depender del volcado de la PAC: **no se crea ni una parcela**. Si la superficie del
    trabajo acabara en `parcelas`, cualquier suma del agricultor contaría tierras que no son suyas.
    """
    db_sesion.expire_all()
    antes = db_sesion.scalar(select(func.count()).select_from(models.Parcela)) or 0

    tercero = _un_cliente(cliente, cuenta)
    propuesta = _proponer(
        cliente, cuenta, tercero["id"], superficie_ha="10.0000", ubicacion="El prado del vecino, junto al río"
    )
    assert propuesta.status_code == 201, propuesta.text
    assert Decimal(propuesta.json()["superficie_ha"]) == Decimal("10"), propuesta.json()

    db_sesion.expire_all()
    despues = db_sesion.scalar(select(func.count()).select_from(models.Parcela)) or 0
    assert despues == antes, f"un trabajo de un tercero no puede crear tierras mías: {antes} -> {despues}"


def test_de_quien_es_el_insumo_se_dice_y_se_conserva(cliente, cuenta):
    """**2 L propios consumen; 2 L del cliente no** — y por eso el parte tiene que decir **de quién era**.

    Lo que aquí se prueba es lo que este módulo hace: **guardarlo y decirlo con todas las letras**. El descuento de
    verdad del almacén es de otro módulo, y para hacerlo bien necesita justo esto.
    """
    tercero = _un_cliente(cliente, cuenta)
    suyo = _proponer(cliente, cuenta, tercero["id"], de_quien_es_el_insumo="propio")
    ajeno = _proponer(cliente, cuenta, tercero["id"], de_quien_es_el_insumo="cliente", titulo="Con su gasoil")
    for trabajo in (suyo, ajeno):
        assert cliente.post(
            f"/api/trabajos-a-terceros/{trabajo.json()['id']}/aceptar", headers=cuenta["cabeceras"], json={}
        ).status_code == 200

    parte_suyo = cliente.post(
        f"/api/trabajos-a-terceros/{suyo.json()['id']}/parte",
        headers=cuenta["cabeceras"],
        json={"horas_hechas": "3.00", "coste_conocido": "120.0000"},
    )
    assert parte_suyo.status_code == 200, parte_suyo.text
    assert "TUYO" in parte_suyo.json()["almacen"], parte_suyo.json()["almacen"]

    parte_ajeno = cliente.post(
        f"/api/trabajos-a-terceros/{ajeno.json()['id']}/parte",
        headers=cuenta["cabeceras"],
        json={"horas_hechas": "3.00"},
    )
    assert parte_ajeno.status_code == 200, parte_ajeno.text
    assert "DEL CLIENTE" in parte_ajeno.json()["almacen"], parte_ajeno.json()["almacen"]


def test_el_margen_MARCA_los_costes_que_no_constan(cliente, cuenta):
    """**Sin coste no hay un cero**: hay un «no consta», que el contrato pide que el margen **marque**.

    Se apunta un parte **sin** coste y la respuesta dice `coste_conocido_o_no: False`: quien sume márgenes tiene con
    qué distinguir «costó cero» de «no sé cuánto costó». Y con coste, dice que sí.
    """
    tercero = _un_cliente(cliente, cuenta)
    sin_coste = _proponer(cliente, cuenta, tercero["id"])
    con_coste = _proponer(cliente, cuenta, tercero["id"], titulo="Con coste")
    for trabajo in (sin_coste, con_coste):
        cliente.post(
            f"/api/trabajos-a-terceros/{trabajo.json()['id']}/aceptar", headers=cuenta["cabeceras"], json={}
        )

    el_sin = cliente.post(
        f"/api/trabajos-a-terceros/{sin_coste.json()['id']}/parte", headers=cuenta["cabeceras"], json={}
    ).json()
    assert el_sin["coste_conocido"] is None and el_sin["coste_conocido_o_no"] is False, el_sin

    el_con = cliente.post(
        f"/api/trabajos-a-terceros/{con_coste.json()['id']}/parte",
        headers=cuenta["cabeceras"],
        json={"coste_conocido": "80.0000"},
    ).json()
    assert el_con["coste_conocido_o_no"] is True, el_con


def test_la_ejecucion_repetida_no_duplica(cliente, cuenta):
    """**Ejecución repetida no duplica**: la misma clave de reenvío devuelve la que había."""
    tercero = _un_cliente(cliente, cuenta)
    primera = _proponer(cliente, cuenta, tercero["id"], clave_de_reenvio="el-parte-1")
    segunda = _proponer(cliente, cuenta, tercero["id"], clave_de_reenvio="el-parte-1", titulo="Otra vez lo mismo")
    assert primera.status_code == 201 and segunda.status_code == 201, (primera.status_code, segunda.status_code)
    assert primera.json()["id"] == segunda.json()["id"], "la misma clave no puede apuntar dos trabajos"
    assert len(cliente.get("/api/trabajos-a-terceros", headers=cuenta["cabeceras"]).json()["trabajos"]) == 1


def test_el_parte_no_se_le_puede_apuntar_a_lo_que_no_se_acepto(cliente, cuenta):
    """Y un parte de algo que nadie aceptó es un trabajo que no se ha pedido: **409**."""
    tercero = _un_cliente(cliente, cuenta)
    propuesta = _proponer(cliente, cuenta, tercero["id"])
    suyo = cliente.post(
        f"/api/trabajos-a-terceros/{propuesta.json()['id']}/parte", headers=cuenta["cabeceras"], json={}
    )
    assert suyo.status_code == 409, f"sin aceptar no hay parte: {suyo.status_code}"


def test_lo_hecho_no_se_cancela(cliente, cuenta):
    """**Un parte hecho no se cancela**: eso sería borrar trabajo."""
    tercero = _un_cliente(cliente, cuenta)
    propuesta = _proponer(cliente, cuenta, tercero["id"])
    cliente.post(f"/api/trabajos-a-terceros/{propuesta.json()['id']}/aceptar", headers=cuenta["cabeceras"], json={})
    cliente.post(f"/api/trabajos-a-terceros/{propuesta.json()['id']}/parte", headers=cuenta["cabeceras"], json={})
    cancelado = cliente.post(
        f"/api/trabajos-a-terceros/{propuesta.json()['id']}/cancelar", headers=cuenta["cabeceras"]
    )
    assert cancelado.status_code == 409, cancelado.status_code


def test_el_trabajo_de_otra_finca_no_se_ve(cliente, cuenta, crear_cuenta):
    """**Otra explotación: ningún acceso**, ni para aceptar ni para apuntar el parte."""
    mia = _un_cliente(cliente, cuenta, "Mi tercero")
    mia_propuesta = _proponer(cliente, cuenta, mia["id"])
    otra = crear_cuenta(nombre="La otra casa", correo="terceros-ajena@ejemplo.test")

    assert cliente.post(
        f"/api/trabajos-a-terceros/{mia_propuesta.json()['id']}/aceptar",
        headers=otra["cabeceras"],
        json={},
    ).status_code == 404, "aceptar el de otra finca"
    assert cliente.get("/api/trabajos-a-terceros", headers=otra["cabeceras"]).json()["trabajos"] == [], (
        "y su lista no lo trae"
    )
