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

# ---------------------------------------------------------------------------
# La fusión que MUEVE filas (Entrega 5, 14/10/2026)
# ---------------------------------------------------------------------------


def _fusionar(cliente, cuenta, origen: int, destino: int):
    return cliente.post(f"/api/contactos/{origen}/fusion/{destino}", headers=cuenta["cabeceras"])


def test_la_fusion_junta_lo_que_colgaba_de_las_dos(cliente, cuenta, db_sesion):
    """**Fusión dentro de una explotación**: lo del origen pasa al destino, y el origen **no se borra**.

    Es lo que el encargo pide con estas palabras: «el contacto fusionado debe remitir al destino para que sus enlaces
    antiguos sigan siendo comprensibles» y «no borrar físicamente el origen como atajo».
    """
    origen = _una_ficha(cliente, cuenta, "Origen que se fusiona", papeles=["transportista"])
    destino = _una_ficha(cliente, cuenta, "Destino que se queda")
    # Una tarea y un canal en el origen, y una tarea en el destino: después tienen que estar las dos allí.
    assert cliente.post(
        f"/api/contactos/{origen['id']}/tareas", headers=cuenta["cabeceras"], json={"titulo": "Del origen"}
    ).status_code == 200
    assert cliente.post(
        f"/api/contactos/{destino['id']}/tareas", headers=cuenta["cabeceras"], json={"titulo": "Del destino"}
    ).status_code == 200
    assert cliente.post(
        f"/api/contactos/{origen['id']}/canales",
        headers=cuenta["cabeceras"],
        json={"clase": "telefono", "telefono": "947 111 222"},
    ).status_code == 200

    fusion = _fusionar(cliente, cuenta, origen["id"], destino["id"])
    assert fusion.status_code == 200, fusion.text
    assert fusion.json()["fusionado"] == {"origen_id": origen["id"], "destino_id": destino["id"]}
    assert fusion.json()["movidas"]["tareas"] == 1, fusion.json()["movidas"]
    assert fusion.json()["movidas"]["canales_de_un_contacto"] == 1, fusion.json()["movidas"]

    # **Las dos tareas están en el destino**, y el canal también.
    db_sesion.expire_all()
    del_destino = cliente.get(f"/api/contactos/{destino['id']}", headers=cuenta["cabeceras"]).json()
    titulos = sorted(tarea["titulo"] for tarea in del_destino["tareas"])
    assert titulos == ["Del destino", "Del origen"], f"las dos tareas tienen que estar: {titulos}"
    assert del_destino["papeles"] == ["transportista"], f"y el papel del origen: {del_destino['papeles']}"

    # **Y el origen sigue existiendo, remitiendo al destino.**
    el_origen = db_sesion.get(models.Contacto, origen["id"])
    assert el_origen is not None, "el origen NO se borra"
    assert el_origen.nombre == "Origen que se fusiona", "y conserva su nombre, que es lo que hace comprensibles los enlaces"
    assert el_origen.fusionado_con_id == destino["id"], "y remite al destino"


def test_la_fusion_repetida_no_hace_nada_mas(cliente, cuenta, db_sesion):
    """**Fusión repetida segura**: la segunda vez contesta 409 y **no toca nada**.

    Y eso no es una comodidad: es lo que impide que una fusión hecha dos veces (un doble clic, un reintento) mueva
    filas de sitio dos veces.
    """
    origen = _una_ficha(cliente, cuenta, "Origen repetido")
    destino = _una_ficha(cliente, cuenta, "Destino repetido")
    assert _fusionar(cliente, cuenta, origen["id"], destino["id"]).status_code == 200

    otra_vez = _fusionar(cliente, cuenta, origen["id"], destino["id"])
    assert otra_vez.status_code == 409, f"la segunda vez tiene que negarse: {otra_vez.status_code}"
    # Y la huella de la fusión es la misma: no se ha movido nada de nuevo.
    db_sesion.expire_all()
    el_origen = db_sesion.get(models.Contacto, origen["id"])
    assert el_origen.fusionado_con_id == destino["id"], "sigue remitiendo al mismo destino"


def test_el_papel_repetido_se_queda_una_sola_vez(cliente, cuenta, db_sesion):
    """**La colisión dura**: los dos son `proveedor` y la base no admite el mismo papel dos veces.

    Después de fusionar, el papel está **una vez** (no se pierde nada: es el mismo papel) y la respuesta lo dice.
    """
    origen = _una_ficha(cliente, cuenta, "Proveedor uno", papeles=["proveedor"])
    destino = _una_ficha(cliente, cuenta, "Proveedor dos", papeles=["proveedor"])

    fusion = _fusionar(cliente, cuenta, origen["id"], destino["id"])
    assert fusion.status_code == 200, fusion.text
    assert fusion.json()["decisiones"]["papeles_repetidos"] == ["proveedor"], fusion.json()["decisiones"]

    db_sesion.expire_all()
    suyos = list(
        db_sesion.scalars(
            select(models.PapelDeUnContacto).where(models.PapelDeUnContacto.contacto_id == destino["id"])
        )
    )
    assert [papel.papel for papel in suyos] == ["proveedor"], f"una sola vez: {[p.papel for p in suyos]}"


def test_el_principal_repetido_se_aparta_pero_el_canal_no_se_pierde(cliente, cuenta, db_sesion):
    """**La otra colisión dura**: los dos tienen principal de teléfono, y solo puede haber uno.

    El del origen **no se borra**: se queda, pero deja de mandar. Perder un teléfono por fusionar sería el peor de los
    arreglos posibles.
    """
    origen = _una_ficha(cliente, cuenta, "Con telefono uno")
    destino = _una_ficha(cliente, cuenta, "Con telefono dos")
    for ficha, numero in ((origen, "947 111 111"), (destino, "947 222 222")):
        assert cliente.post(
            f"/api/contactos/{ficha['id']}/canales",
            headers=cuenta["cabeceras"],
            json={"clase": "telefono", "telefono": numero, "principal": True},
        ).status_code == 200

    fusion = _fusionar(cliente, cuenta, origen["id"], destino["id"])
    assert fusion.status_code == 200, fusion.text
    assert fusion.json()["decisiones"]["principales_apartados"] == ["telefono"], fusion.json()["decisiones"]

    db_sesion.expire_all()
    canales = list(
        db_sesion.scalars(
            select(models.CanalDeUnContacto).where(models.CanalDeUnContacto.contacto_id == destino["id"])
        )
    )
    numeros = sorted(canal.telefono for canal in canales)
    assert "947 111 111" in numeros and "947 222 222" in numeros, f"los DOS teléfonos siguen: {numeros}"
    principales = [canal for canal in canales if canal.principal]
    assert len(principales) == 1, f"y solo uno manda (lo garantiza un índice de la base): {len(principales)}"


def test_queda_la_auditoria_con_origen_destino_y_lo_que_se_movio(cliente, cuenta, db_sesion):
    """**La auditoría, con origen, destino, autor, fecha y decisiones** — y con la lista de lo que se movió.

    Esa lista es **lo único** que puede deshacer la fusión sin restaurar la base: `papeles_de_un_contacto` y
    `enlaces_de_contacto` no tienen columna de anulación.
    """
    origen = _una_ficha(cliente, cuenta, "Origen con auditoria")
    destino = _una_ficha(cliente, cuenta, "Destino con auditoria")
    assert cliente.post(
        f"/api/contactos/{origen['id']}/tareas", headers=cuenta["cabeceras"], json={"titulo": "Una tarea"}
    ).status_code == 200
    assert _fusionar(cliente, cuenta, origen["id"], destino["id"]).status_code == 200

    db_sesion.expire_all()
    apuntado = list(
        db_sesion.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == "contacto",
                models.Auditoria.entidad_id == destino["id"],
                models.Auditoria.accion == "fusion",
            )
        )
    )
    assert len(apuntado) == 1, f"tiene que quedar una fila: {len(apuntado)}"
    datos = apuntado[0].datos
    assert datos["origen_id"] == origen["id"] and datos["destino_id"] == destino["id"], datos
    assert datos["origen_nombre"] == "Origen con auditoria", "con el nombre que tenía"
    assert datos["movidas"]["tareas"], f"y la lista de lo que se movió: {datos}"
    assert apuntado[0].usuario_id is not None, "y con quién lo hizo"
    assert datos["saldo_origen_antes"] is not None and datos["saldo_destino_antes"] is not None, (
        "y los dos saldos de ANTES, que es con lo que se comprueba que la suma es la misma"
    )


def test_entre_explotaciones_no_se_fusiona_nada(cliente, cuenta, crear_cuenta, db_sesion):
    """**Intento entre explotaciones rechazado**: 404, por identificador, y **sin mover una fila**."""
    mia = _una_ficha(cliente, cuenta, "La mía para fusionar")
    otra = crear_cuenta(nombre="La otra finca", correo="fusion-ajena@ejemplo.test")
    ajena = cliente.post("/api/contactos", headers=otra["cabeceras"], json={"nombre": "La ajena"}).json()

    assert _fusionar(cliente, cuenta, mia["id"], ajena["id"]).status_code == 404, "la ajena como destino"
    assert _fusionar(cliente, cuenta, ajena["id"], mia["id"]).status_code == 404, "y como origen"

    db_sesion.expire_all()
    la_mia = db_sesion.get(models.Contacto, mia["id"])
    assert la_mia.fusionado_con_id is None, "y la mía sigue sin fusionar: no se ha movido nada"
