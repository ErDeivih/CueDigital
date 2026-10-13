"""La vista previa de una fusión de dos fichas (Entrega 5, 14/10/2026).

Es la mitad de la fusión que se puede hacer **sin mover una fila**: mirar qué hay en las dos fichas y **decir qué
colisiones** aparecerían, para que el agricultor decida. La fusión que mueve filas va después y con esto delante.

Lo que se prueba aquí:
- que la vista previa **cuenta** lo que cuelga de cada ficha (las once tablas del inventario);
- que **enseña las colisiones duras** (`papel` repetido, principal repetido por clase, y las dos con notas escritas
  en el campo de texto único de la ficha, que es donde se pierde algo);
- que **sin permiso económico no manda ningún importe** —el contrato: «sin permiso económico: no aparecen importes ni
  documentos restringidos»— pero sí los recuentos, que no son importes;
- y que **una ficha de otra finca no se ve**, ni por identificador.
"""

from __future__ import annotations

from sqlalchemy import select

from app import models


def _una_ficha(cliente, cuenta, nombre: str, **extra) -> dict:
    creada = cliente.post("/api/contactos", headers=cuenta["cabeceras"], json={"nombre": nombre, **extra})
    assert creada.status_code == 201, creada.text
    return creada.json()


def _la_previa(cliente, cuenta, origen: int, destino: int):
    return cliente.get(f"/api/contactos/{origen}/fusion/{destino}", headers=cuenta["cabeceras"])


def test_la_vista_previa_cuenta_lo_que_cuelga_de_cada_ficha(cliente, cuenta):
    """**Cuenta las once tablas**, las seis del dinero y las cinco que cuelgan, sin tocar nada."""
    origen = _una_ficha(cliente, cuenta, "Origen de la fusión")
    destino = _una_ficha(cliente, cuenta, "Destino de la fusión")
    # Un canal y una tarea en el origen, para que se note que mira de verdad.
    assert cliente.post(
        f"/api/contactos/{origen['id']}/canales",
        headers=cuenta["cabeceras"],
        json={"clase": "telefono", "telefono": "947 000 000"},
    ).status_code == 200
    assert cliente.post(
        f"/api/contactos/{origen['id']}/tareas", headers=cuenta["cabeceras"], json={"titulo": "Llamar"}
    ).status_code == 200

    previa = _la_previa(cliente, cuenta, origen["id"], destino["id"])
    assert previa.status_code == 200, previa.text
    suya = previa.json()
    # Las seis del dinero y las cinco que cuelgan: están todas, aunque sea a cero.
    assert set(suya["origen"]["dinero"]) == {
        "ventas_de_cosecha", "facturas_emitidas", "cobros", "gastos", "inversiones_de_la_finca", "pagos_de_gasto",
    }, suya["origen"]["dinero"]
    assert set(suya["origen"]["cuelgan"]) == {
        "papeles_de_un_contacto", "enlaces_de_contacto", "canales_de_un_contacto", "tareas", "notas_de_un_contacto",
    }, suya["origen"]["cuelgan"]
    # Y cuenta lo que hay: el canal que se ha apuntado y su tarea.
    assert suya["origen"]["cuelgan"]["canales_de_un_contacto"] >= 1, suya["origen"]["cuelgan"]
    assert suya["origen"]["cuelgan"]["tareas"] == 1, suya["origen"]["cuelgan"]
    assert suya["destino"]["cuelgan"]["tareas"] == 0, "el destino no tiene ninguna"
    # **Y no mueve nada**: las dos fichas siguen donde estaban.
    assert cliente.get(f"/api/contactos/{origen['id']}", headers=cuenta["cabeceras"]).status_code == 200
    assert cliente.get(f"/api/contactos/{destino['id']}", headers=cuenta["cabeceras"]).status_code == 200


def test_la_vista_previa_ensena_las_colisiones_duras(cliente, cuenta):
    """**Lo que hay que decidir, dicho**: papel repetido, principal repetido y las dos con notas escritas.

    Ninguna de las tres la puede resolver la fusión sola: la primera y la segunda porque la base no las admite (índices
    únicos) y la tercera porque `Contacto.notas` es **un solo campo de texto** y no hay sitio para las dos.
    """
    origen = _una_ficha(cliente, cuenta, "Origen con papeles", papeles=["proveedor"], notas="Hablé con Ana.")
    destino = _una_ficha(cliente, cuenta, "Destino con papeles", papeles=["proveedor"], notas="Me debe una factura.")

    previa = _la_previa(cliente, cuenta, origen["id"], destino["id"])
    assert previa.status_code == 200, previa.text
    colisiones = {c["que"] for c in previa.json()["colisiones"]}
    assert "papel_repetido" in colisiones, f"los dos son proveedor: {colisiones}"
    assert "las_dos_tienen_notas_escritas" in colisiones, (
        f"las dos tienen notas escritas y solo hay un campo: {colisiones}"
    )
    # Y cada colisión dice **qué hacer**, que es lo que convierte esto en algo que se puede decidir.
    for colision in previa.json()["colisiones"]:
        assert colision["que_hacer"].strip(), f"cada colisión tiene que decir qué hacer: {colision}"
        assert colision["por_que"].strip(), f"y por qué: {colision}"


def test_sin_poder_economico_no_viaja_ningun_importe(cliente, cuenta, db_sesion):
    """**Ni un importe**, pero sí los recuentos —que no son importes—. El contrato lo pide con esas palabras."""
    origen = _una_ficha(cliente, cuenta, "Origen sin permiso")
    destino = _una_ficha(cliente, cuenta, "Destino sin permiso")

    db_sesion.expire_all()
    acceso = db_sesion.scalar(
        select(models.AccesoAFinca).where(
            models.AccesoAFinca.usuario_id == cuenta["usuario_id"],
            models.AccesoAFinca.explotacion_id == cuenta["explotacion_id"],
        )
    )
    acceso.puede_ver_lo_economico = False
    db_sesion.commit()

    previa = _la_previa(cliente, cuenta, origen["id"], destino["id"])
    assert previa.status_code == 200, previa.text
    assert previa.json()["saldos"] is None, "sin permiso no hay saldos"
    assert previa.json()["saldos_por_que_no"], "y se dice por qué"
    # **Lo que sí va**: los recuentos, que no son importes.
    assert previa.json()["origen"]["cuelgan"]["tareas"] == 0
    # Y en el cuerpo **no hay ni una cifra de dinero**.
    assert "€" not in previa.text, f"la respuesta no puede llevar importes: {previa.text[:400]}"


def test_la_ficha_de_otra_finca_no_se_ve(cliente, cuenta, crear_cuenta):
    """**Otra explotación: ningún acceso.** Ni por identificador, ni como origen ni como destino.

    Y el 404 es intencionado: así no se puede ni saber que esa ficha existe (el mismo cuidado que en el resto).
    """
    mia = _una_ficha(cliente, cuenta, "La mía")
    otra = crear_cuenta(nombre="Otra finca", correo="otra-finca@ejemplo.test")
    ajena = cliente.post("/api/contactos", headers=otra["cabeceras"], json={"nombre": "La ajena"})
    assert ajena.status_code == 201, ajena.text
    id_ajeno = ajena.json()["id"]

    assert _la_previa(cliente, cuenta, mia["id"], id_ajeno).status_code == 404, "la ajena como destino"
    assert _la_previa(cliente, cuenta, id_ajeno, mia["id"]).status_code == 404, "y como origen"
