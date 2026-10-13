"""El margen de un trabajo a un tercero (CRM-04, 14/10/2026).

**Por qué existe esta puerta.** El contrato del ticket pide *«margen marca costes desconocidos»*, y el parte ya
apuntaba el coste **pero no había nada que lo comparara con el ingreso**. Y un margen que trata un coste que no
consta como un cero **miente**: diría que un trabajo sin coste apuntado es todo beneficio.

**Lo que se prueba aquí es eso**: que cuando falta una de las dos mitades **el margen no se calcula** y **se dice
cuál falta**. Es la diferencia entre «no lo sé» y «cero», que es lo que este módulo pide en todas partes.
"""

from __future__ import annotations


def _un_contacto(cliente, cuenta, nombre: str) -> int:
    respuesta = cliente.post("/api/contactos", headers=cuenta["cabeceras"], json={"nombre": nombre})
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()["id"]


def _un_trabajo(cliente, cuenta, contacto_id: int, nombre: str, clave: str | None = None) -> dict:
    # **El trabajo es PARA ALGUIEN**: la puerta exige `contacto_id` (y hace bien: un trabajo sin cliente no es
    # un trabajo). Lo aprendí de un 422, no suponiéndolo.
    cuerpo = {
        "contacto_id": contacto_id,
        "titulo": nombre,
        "de_quien_es_el_insumo": "propio",
    }
    if clave:
        cuerpo["clave_de_reenvio"] = clave
    respuesta = cliente.post("/api/trabajos-a-terceros", headers=cuenta["cabeceras"], json=cuerpo)
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()


def _su_margen(cliente, cuenta, trabajo: dict) -> dict:
    respuesta = cliente.get(f"/api/trabajos-a-terceros/{trabajo['id']}/margen", headers=cuenta["cabeceras"])
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_sin_coste_apuntado_el_margen_NO_se_calcula_y_se_dice_cual_falta(cliente, cuenta):
    # **Un trabajo recién apuntado no tiene coste.** Y no se puede decir «margen 0»: no es que costara cero, es
    # que no se sabe. La bandera lo dice, y el margen viene vacío.
    contacto = _un_contacto(cliente, cuenta, "Cliente del margen")
    trabajo = _un_trabajo(cliente, cuenta, contacto, "Sin coste todavía")
    margen = _su_margen(cliente, cuenta, trabajo)
    assert margen["coste_conocido_o_no"] is False, margen
    assert margen["coste_conocido"] is None, margen
    assert margen["margen"] is None, f"un coste que no consta no puede ser un cero: {margen}"


def test_con_coste_pero_sin_nada_facturado_tampoco_se_calcula(cliente, cuenta):
    # El otro lado: el coste sí consta y el ingreso no. Tampoco hay margen que enseñar — y no puede salir
    # negativo por lo que todavía no se ha facturado.
    contacto = _un_contacto(cliente, cuenta, "Cliente con coste")
    trabajo = _un_trabajo(cliente, cuenta, contacto, "Con coste y sin facturar", clave="margen-sin-facturar-1")
    # **Y hay que ACEPTARLO antes**: la puerta lo exige («solo se le puede apuntar el parte a un trabajo
    # aceptado»), que es el flujo que pide el contrato —propuesta, aceptación, parte—. Lo aprendí de su 409.
    aceptado = cliente.post(
        f"/api/trabajos-a-terceros/{trabajo['id']}/aceptar", headers=cuenta["cabeceras"], json={}
    )
    assert aceptado.status_code == 200, aceptado.text
    apuntado = cliente.post(
        f"/api/trabajos-a-terceros/{trabajo['id']}/parte",
        headers=cuenta["cabeceras"],
        json={"coste_conocido": "125.50"},
    )
    assert apuntado.status_code == 200, apuntado.text
    margen = _su_margen(cliente, cuenta, trabajo)
    assert margen["coste_conocido_o_no"] is True, margen
    assert float(margen["coste_conocido"]) == 125.50, margen
    assert margen["facturado_o_no"] is False, margen
    assert margen["facturado"] is None, margen
    assert margen["margen"] is None, f"sin ingreso no hay margen, ni negativo: {margen}"


def test_el_trabajo_de_otra_finca_no_se_puede_ni_mirar(cliente, cuenta, crear_cuenta):
    # **Aislamiento**: la puerta filtra por la finca. Ni los importes ni la clave.
    contacto = _un_contacto(cliente, cuenta, "Cliente de mi finca")
    trabajo = _un_trabajo(cliente, cuenta, contacto, "De mi finca")
    otra = crear_cuenta("otro-del-margen@ejemplo.test")  # la fabrica pide un correo, y es obligatorio
    respuesta = cliente.get(f"/api/trabajos-a-terceros/{trabajo['id']}/margen", headers=otra["cabeceras"])
    assert respuesta.status_code in (403, 404), f"otra finca no debería verlo: {respuesta.status_code}"
    assert "margen" not in respuesta.text.lower(), "y no puede filtrarse ni el nombre del campo"
