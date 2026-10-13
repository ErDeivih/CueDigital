"""La fusión y el campo de notas de la ficha (Entrega 5, 14/10/2026).

**POR QUÉ ESTA PRUEBA EXISTE, Y POR QUÉ LA PRIMERA QUE ESCRIBÍ NO VALÍA.**

La vista previa de la fusión avisa de una colisión que llama «las dos tienen notas escritas», y su propio texto dice
por qué: *`Contacto.notas` es **un campo de texto único**, no la tabla de notas: no hay sitio para las dos, eso se ve
aquí y **el humano decide***. O sea: la puerta **no puede** quedarse con una de las dos por su cuenta.

Mi primera prueba llenó las notas **por la puerta de las notas** —que las guarda en la **tabla**
`notas_de_un_contacto`, y esas **sí** se mueven enteras, no se pierde ninguna— así que estaba midiendo **otra cosa**:
la puerta la juntaba (200) y yo lo llamé defecto. **No lo era.** Lo que hay que llenar es **el campo de la ficha**, que
es el que la vista previa mira.
"""

from __future__ import annotations


def _una_ficha(cliente, cuenta, nombre: str) -> dict:
    creada = cliente.post("/api/contactos", headers=cuenta["cabeceras"], json={"nombre": nombre})
    assert creada.status_code == 201, creada.text
    return creada.json()


def _con_notas_en_la_ficha(cliente, cuenta, ficha: dict, texto: str) -> None:
    """Llena **el campo de texto de la ficha**, que es el que la vista previa mira. Se manda el nombre también
    porque la corrección distingue «no lo mando» de «lo mando vacío»."""
    puesta = cliente.put(
        f"/api/contactos/{ficha['id']}",
        headers=cuenta["cabeceras"],
        json={"nombre": ficha["nombre"], "notas": texto},
    )
    assert puesta.status_code == 200, puesta.text
    leida = cliente.get(f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"]).json()
    assert (leida.get("notas") or "").strip() == texto, f"no se ha guardado el campo: {leida.get('notas')!r}"


def test_la_vista_previa_avisa_de_las_dos_notas_escritas(cliente, cuenta):
    """**La vista previa lo dice**, y con su motivo: es lo que el humano tiene que ver antes de decidir."""
    una = _una_ficha(cliente, cuenta, "Hermanos Pérez (el viejo)")
    otra = _una_ficha(cliente, cuenta, "Hermanos Pérez (el nuevo)")
    _con_notas_en_la_ficha(cliente, cuenta, una, "Le gusta que le llamen por la mañana.")
    _con_notas_en_la_ficha(cliente, cuenta, otra, "Tiene dos naves.")

    previa = cliente.get(f"/api/contactos/{una['id']}/fusion/{otra['id']}", headers=cuenta["cabeceras"])
    assert previa.status_code == 200, previa.text
    las_que = [c["que"] for c in previa.json()["colisiones"]]
    assert "las_dos_tienen_notas_escritas" in las_que, f"la previa tiene que avisarlo: {las_que}"
    la_suya = [c for c in previa.json()["colisiones"] if c["que"] == "las_dos_tienen_notas_escritas"][0]
    assert "campo de texto" in la_suya["por_que"], la_suya["por_que"]
    assert la_suya.get("que_hacer"), "y tiene que decir qué hacer"


def test_con_el_campo_de_notas_lleno_en_las_dos_la_fusion_se_NIEGA(cliente, cuenta):
    """**Y la puerta no puede decidir por el humano.** Es el criterio de la Entrega 4 de este mismo encargo, con sus
    palabras: *«ocultar un botón no constituye autorización»*. Si la vista previa dice «hay que decidir», la puerta no
    puede quedarse con una de las dos notas y seguir como si nada.

    Se exige **409** y que **no se haya movido nada**: las dos fichas enteras, con su nota cada una, y ninguna
    fusionada.
    """
    una = _una_ficha(cliente, cuenta, "Hermanos Pérez (el viejo)")
    otra = _una_ficha(cliente, cuenta, "Hermanos Pérez (el nuevo)")
    la_de_una = "Le gusta que le llamen por la mañana."
    la_de_otra = "Tiene dos naves."
    _con_notas_en_la_ficha(cliente, cuenta, una, la_de_una)
    _con_notas_en_la_ficha(cliente, cuenta, otra, la_de_otra)

    negada = cliente.post(f"/api/contactos/{una['id']}/fusion/{otra['id']}", headers=cuenta["cabeceras"])
    assert negada.status_code == 409, (
        f"la puerta no puede quedarse con una de las dos notas: {negada.status_code} {negada.text[:200]}"
    )
    assert "notas" in negada.text.lower(), negada.text

    for ficha, nota in ((una, la_de_una), (otra, la_de_otra)):
        suya = cliente.get(f"/api/contactos/{ficha['id']}", headers=cuenta["cabeceras"]).json()
        assert (suya.get("notas") or "").strip() == nota, f"se ha perdido una nota: {suya.get('notas')!r}"
        assert not suya.get("fusionado_con_id"), "y ninguna ha quedado fusionada"


def test_si_solo_una_tiene_notas_escritas_la_fusion_SI_se_hace(cliente, cuenta):
    """**Y el otro lado, que es el que importa para no pasarse de listo**: con **una sola** ficha con notas, no hay
    nada que decidir y la fusión se hace. *Negarse de más también sería un defecto.*"""
    con_notas = _una_ficha(cliente, cuenta, "El del prado (con notas)")
    sin_notas = _una_ficha(cliente, cuenta, "El del prado")
    _con_notas_en_la_ficha(cliente, cuenta, con_notas, "Le gusta que le llamen por la mañana.")

    hecha = cliente.post(f"/api/contactos/{con_notas['id']}/fusion/{sin_notas['id']}", headers=cuenta["cabeceras"])
    assert hecha.status_code == 200, f"con una sola no hay nada que decidir: {hecha.status_code} {hecha.text[:200]}"
