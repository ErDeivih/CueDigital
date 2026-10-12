"""CRM-03, criterio (f): **las notas se apuntan, con quién las escribió y cuándo**.

POR QUÉ EXISTE. Hasta hoy la ficha de un contacto tenía **un campo de notas** y nada más: al corregirla se
perdía lo de antes, y no se sabía quién había escrito qué. En una finca eso importa: «este nos dejó tirados en
la campaña del 24» es una nota que conviene poder atribuir, y en la misma casa dos personas apuntan cosas
distintas sobre el mismo proveedor.

**Lo que se ha decidido, y conviene no deshacerlo:**

1. **Las notas no se corrigen: se apuntan.** Son el diario de la ficha —lo que se va sabiendo—, no un dato que se
   pone al día. Si algo se escribió mal, se escribe otra nota diciéndolo, y así **queda lo de antes**, que es lo
   que un diario tiene que hacer. Por eso `NotaDeUnContacto` **no entra** en `correcciones`.
2. **El autor lo pone el servidor**, de su vale. Aceptarlo del navegador sería poder firmar cosas que no ha
   escrito uno, y un autor que se puede escribir a mano no vale para nada.
3. **El autor puede faltar y se dice**: hay notas que escribe el programa, y `None` es «no la escribió una
   persona». Inventarle un autor sería peor que no tenerlo.
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def _una_ficha(cliente, cuenta, nombre: str) -> dict:
    respuesta = cliente.post(
        "/api/contactos",
        headers=cuenta["cabeceras"],
        json={"nombre": nombre, "papeles": ["proveedor"]},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _apuntar(cliente, cuenta, contacto_id: int, texto: str):
    return cliente.post(
        f"/api/contactos/{contacto_id}/notas",
        headers=cuenta["cabeceras"],
        json={"texto": texto},
    )


def test_las_notas_se_apuntan_con_su_autor_y_su_fecha(cliente, cuenta):
    """Lo que pide el criterio (f), por la puerta de verdad."""
    ficha = _una_ficha(cliente, cuenta, "Suministros del Páramo, S.L.")

    primera = _apuntar(cliente, cuenta, ficha["id"], "Nos dejó tirados en la campaña del 24.")
    assert primera.status_code == 200, primera.text
    segunda = _apuntar(cliente, cuenta, ficha["id"], "Ha cambiado de dueño y ahora pagan bien.")
    assert segunda.status_code == 200, segunda.text

    notas = segunda.json()["notas_con_autor"]
    assert len(notas) == 2, f"la ficha tiene que llevar sus dos notas: {notas}"
    # **De la más nueva a la más vieja**: lo último que se supo es lo que se quiere leer primero.
    assert notas[0]["texto"] == "Ha cambiado de dueño y ahora pagan bien.", (
        f"la primera tiene que ser la última apuntada: {[nota['texto'] for nota in notas]}"
    )
    assert notas[1]["texto"] == "Nos dejó tirados en la campaña del 24."
    for nota in notas:
        assert nota["autor"], f"cada nota dice quién la escribió: {nota}"
        assert nota["creado_en"], f"y cuándo: {nota}"


def test_una_nota_vacia_no_se_apunta(cliente, cuenta):
    """Una nota que no dice nada no es una nota: se contesta con palabras, y no se guarda."""
    ficha = _una_ficha(cliente, cuenta, "Taller de prueba")
    vacia = _apuntar(cliente, cuenta, ficha["id"], "   ")
    assert vacia.status_code == 422, f"una nota vacía no se apunta: {vacia.status_code} {vacia.text}"
    assert "tiene que decir algo" in vacia.text, f"y se dice con palabras: {vacia.text}"


def test_el_autor_de_una_nota_no_lo_pone_el_navegador(cliente, cuenta, db_sesion):
    """**El autor lo pone el servidor**: mandarlo desde el navegador no cambia nada.

    Un autor que se puede escribir a mano no vale para nada: es la misma regla que en la auditoría.
    """
    ficha = _una_ficha(cliente, cuenta, "Cooperativa de Peñaranda")
    respuesta = cliente.post(
        f"/api/contactos/{ficha['id']}/notas",
        headers=cuenta["cabeceras"],
        json={"texto": "Una nota con autor fingido.", "autor": "Otro que no soy yo", "usuario_id": 9999},
    )
    assert respuesta.status_code == 200, respuesta.text
    nota = db_sesion.scalars(
        select(models.NotaDeUnContacto).where(models.NotaDeUnContacto.contacto_id == ficha["id"])
    ).one()
    assert nota.usuario_id != 9999, "el `usuario_id` que venga del navegador no se usa"
    assert respuesta.json()["notas_con_autor"][0]["autor"] != "Otro que no soy yo"


def test_una_nota_no_se_puede_corregir_ni_borrar(cliente, cuenta, db_sesion):
    """**Y no hay puerta para corregirla ni para borrarla, y es a propósito** (11/10/2026).

    Un diario que se puede reescribir no es un diario. Si una nota está mal, se apunta otra diciéndolo —y las dos
    quedan, que es lo que hace que sirva para acordarse de lo que pasó—. Esta prueba existe para que nadie añada
    un `PUT` ni un `DELETE` sin leer este motivo.
    """
    ficha = _una_ficha(cliente, cuenta, "Recambios del Páramo")
    assert _apuntar(cliente, cuenta, ficha["id"], "Una nota.").status_code == 200

    nota = db_sesion.scalars(
        select(models.NotaDeUnContacto).where(models.NotaDeUnContacto.contacto_id == ficha["id"])
    ).one()
    for metodo in ("put", "delete", "patch"):
        respuesta = getattr(cliente, metodo)(
            f"/api/contactos/{ficha['id']}/notas/{nota.id}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code in (404, 405), (
            f"no puede haber puerta para {metodo.upper()} una nota: contesta {respuesta.status_code}"
        )
