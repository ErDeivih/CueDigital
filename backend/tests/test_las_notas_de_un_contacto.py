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

def test_reenviar_la_misma_accion_apunta_una_sola_nota(cliente, cuenta, db_sesion):
    """**El reenvío seguro** (13/10/2026, revisión): una acción, una nota.

    Tres casos que pasan de verdad y que hay que cubrir con la misma pieza: **el doble clic** (el agricultor toca
    dos veces con los guantes), **la respuesta que se pierde** por el camino y **el reintento del móvil** cuando
    no hay cobertura. Los tres llegan al servidor como la **misma acción**, con la misma clave.
    """
    ficha = _una_ficha(cliente, cuenta, "Cooperativa de Peñaranda")
    clave = "nota-1712345678-abc123"
    primera = cliente.post(
        f"/api/contactos/{ficha['id']}/notas",
        headers=cuenta["cabeceras"],
        json={"texto": "Se le apuntó el teléfono nuevo.", "clave_de_reenvio": clave},
    )
    assert primera.status_code == 200, primera.text
    # Y ahora el reenvío: **la misma acción**, otra vez.
    segunda = cliente.post(
        f"/api/contactos/{ficha['id']}/notas",
        headers=cuenta["cabeceras"],
        json={"texto": "Se le apuntó el teléfono nuevo.", "clave_de_reenvio": clave},
    )
    assert segunda.status_code == 200, segunda.text

    suyas = list(
        db_sesion.scalars(
            select(models.NotaDeUnContacto).where(models.NotaDeUnContacto.contacto_id == ficha["id"])
        )
    )
    assert len(suyas) == 1, f"la misma acción no puede apuntar dos notas: hay {len(suyas)}"
    assert len(segunda.json()["notas_con_autor"]) == 1, "y la ficha contesta con una sola"
    # La segunda contesta **lo que ya había**, no una copia nueva.
    assert segunda.json()["notas_con_autor"][0]["id"] == primera.json()["notas_con_autor"][0]["id"], (
        "el reenvío tiene que contestar la nota que ya estaba"
    )


def test_dos_acciones_voluntarias_con_el_mismo_texto_son_dos_notas(cliente, cuenta, db_sesion):
    """Y **lo que se protege es la acción, no el texto** (13/10/2026, revisión).

    Dos veces que el agricultor apunta lo mismo **a propósito** son dos notas: puede querer dejar constancia dos
    veces —una por cada visita— y el programa no es quién para decidir que sobra una. Sin clave de reenvío, cada
    llamada es una acción nueva.
    """
    ficha = _una_ficha(cliente, cuenta, "Taller de prueba")
    for _ in range(2):
        respuesta = cliente.post(
            f"/api/contactos/{ficha['id']}/notas",
            headers=cuenta["cabeceras"],
            json={"texto": "Le volví a llamar."},
        )
        assert respuesta.status_code == 200, respuesta.text
    suyas = list(
        db_sesion.scalars(
            select(models.NotaDeUnContacto).where(models.NotaDeUnContacto.contacto_id == ficha["id"])
        )
    )
    assert len(suyas) == 2, f"dos acciones voluntarias son dos notas: hay {len(suyas)}"


def test_la_nota_del_programa_se_distingue_de_la_de_una_persona_sin_nombre(cliente, cuenta, db_sesion):
    """**No se inventa el autor** (13/10/2026, revisión), y los tres estados se distinguen.

    Antes, si el nombre del autor no aparecía, la pantalla decía «Lo apuntó el programa» —y eso es **afirmar algo
    que no se sabe**: una nota escrita por una persona cuyo nombre ya no está no es una nota del programa. Ahora
    se dice lo que se sabe en cada caso.
    """
    ficha = _una_ficha(cliente, cuenta, "Recambios del Páramo")

    # 1. Una persona, con su nombre: se sabe quién la escribió.
    cliente.post(
        f"/api/contactos/{ficha['id']}/notas",
        headers=cuenta["cabeceras"],
        json={"texto": "La escribió una persona de la casa."},
    )
    # 2. Una nota del programa: sin autor y se dice así.
    db_sesion.add(
        models.NotaDeUnContacto(
            explotacion_id=cuenta["explotacion_id"],
            contacto_id=ficha["id"],
            usuario_id=None,
            texto="La apuntó el programa al migrar los papeles.",
        )
    )
    # 3. Una persona **cuyo nombre ya no está**: el usuario existe, pero su nombre se quedó sin poner. Se hace así
    #    —y no con un `usuario_id` inventado— porque la clave ajena **no deja** apuntar a un usuario que no
    #    existe: el programa lo impide, y la prueba tiene que respetarlo. Lo que sí ocurre es que el nombre no se
    #    pueda enseñar, y eso es lo que se comprueba.
    sin_nombre = models.Usuario(
        explotacion_id=cuenta["explotacion_id"],
        nombre="",
        correo="sin-nombre@ejemplo.test",
        clave_hash="no-hace-falta",
    )
    db_sesion.add(sin_nombre)
    db_sesion.flush()
    db_sesion.add(
        models.NotaDeUnContacto(
            explotacion_id=cuenta["explotacion_id"],
            contacto_id=ficha["id"],
            usuario_id=sin_nombre.id,
            texto="La escribió alguien que ya no está en la casa.",
        )
    )
    db_sesion.commit()

    notas = cliente.get(f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"]).json()["notas_con_autor"]
    por_texto = {nota["texto"]: nota for nota in notas}
    assert len(por_texto) == 3, f"las tres notas tienen que estar: {list(por_texto)}"

    la_de_la_persona = por_texto["La escribió una persona de la casa."]
    assert la_de_la_persona["autor_estado"] == "persona", la_de_la_persona
    assert la_de_la_persona["autor"], "y con su nombre"

    la_del_programa = por_texto["La apuntó el programa al migrar los papeles."]
    assert la_del_programa["autor_estado"] == "el_programa", la_del_programa
    assert la_del_programa["autor"] is None

    la_sin_nombre = por_texto["La escribió alguien que ya no está en la casa."]
    assert la_sin_nombre["autor_estado"] == "sin_nombre", (
        f"una persona cuyo nombre ya no está **no** es el programa: {la_sin_nombre}"
    )
    assert la_sin_nombre["autor"] is None, "y no se le inventa un nombre"


def test_una_nota_no_se_puede_apuntar_en_un_contacto_de_otra_finca(cliente, cuenta, crear_cuenta):
    """**Aislamiento entre explotaciones** (13/10/2026, revisión): 404, y no se filtra si existe en otra finca.

    La misma regla que en todo el programa: no se contesta «no es tuya» (eso ya diría que existe), se contesta que
    no está.
    """
    mia = _una_ficha(cliente, cuenta, "Mi proveedor")
    otra = crear_cuenta("otro-agricultor@ejemplo.test")
    respuesta = cliente.post(
        f"/api/contactos/{mia['id']}/notas",
        headers=otra["cabeceras"],
        json={"texto": "Esta nota no debería entrar."},
    )
    assert respuesta.status_code == 404, (
        f"un contacto de otra finca tiene que dar 404, y ha dado {respuesta.status_code}: {respuesta.text}"
    )
