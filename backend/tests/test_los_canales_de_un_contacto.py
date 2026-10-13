"""Los canales de un contacto: varios teléfonos, correos y direcciones (Entrega 2, 13/10/2026).

POR QUÉ. Hasta hoy la ficha tenía **un** teléfono, **un** correo y **una** dirección, y eso no es lo que pasa: una
cooperativa tiene el de administración y el del almacén, la persona de contacto tiene su móvil, y la dirección de
entrega no es la de la sede. Con un solo hueco, el agricultor apunta uno y **pierde los otros**.

Aquí se prueba **la migración**: lo que ya estaba apuntado en las cuatro columnas de siempre pasa a ser el canal
**principal** de su clase, **tal cual estaba** —sin arreglar el teléfono, sin inventar prefijos, sin tocar un
texto—, y **correrla dos veces no duplica nada**. Las puertas y la pantalla van en sus pruebas.
"""

from __future__ import annotations

from sqlalchemy import select

from app import database, models


def _un_contacto_con_todo(cliente, cuenta, **cambios) -> dict:
    datos = {
        "nombre": "Cooperativa Agrícola de Peñaranda",
        "telefono": "947 123 456",
        "correo": "administracion@cooperativa.test",
        "direccion": "Calle Mayor 3",
        "localidad": "Peñaranda de Bracamonte",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/contactos", headers=cuenta["cabeceras"], json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _los_canales_de(db_sesion, contacto_id: int) -> list[models.CanalDeUnContacto]:
    db_sesion.expire_all()
    return list(
        db_sesion.scalars(
            select(models.CanalDeUnContacto).where(models.CanalDeUnContacto.contacto_id == contacto_id)
        )
    )


def test_la_migracion_lleva_lo_que_ya_estaba_a_su_canal_principal(cliente, cuenta, db_sesion):
    """Lo que ya estaba apuntado **no se pierde**: pasa a ser el principal de su clase, tal cual."""
    ficha = _un_contacto_con_todo(cliente, cuenta)
    assert _los_canales_de(db_sesion, ficha["id"]) == [], "de partida no hay canales: son nuevos"

    llevados = database.llevar_los_canales_de_los_contactos_a_su_tabla()
    assert llevados >= 3, f"tenía que llevarse el teléfono, el correo y la dirección: {llevados}"

    suyos = _los_canales_de(db_sesion, ficha["id"])
    assert sorted(canal.clase for canal in suyos) == ["correo", "direccion", "telefono"], (
        f"una clase por cada cosa apuntada: {[(c.clase, c.telefono, c.correo, c.direccion) for c in suyos]}"
    )
    assert all(canal.principal for canal in suyos), "y lo que ya estaba es lo **principal** de su clase"

    # **Tal cual estaba apuntado.** Ni el teléfono se «arregla» ni la dirección se reescribe.
    el_telefono = next(canal for canal in suyos if canal.clase == "telefono")
    assert el_telefono.telefono == "947 123 456", f"el teléfono se ha tocado: {el_telefono.telefono}"
    assert el_telefono.etiqueta is None, "y no se le inventa una etiqueta que nadie ha escrito"

    la_direccion = next(canal for canal in suyos if canal.clase == "direccion")
    assert la_direccion.direccion == "Calle Mayor 3", la_direccion.direccion
    assert la_direccion.localidad == "Peñaranda de Bracamonte", (
        f"la dirección se lleva con su localidad, que es como se apunta: {la_direccion.localidad}"
    )


def test_la_migracion_se_puede_correr_dos_veces(cliente, cuenta, db_sesion):
    """**Idempotencia**: correrla otra vez no duplica ni un canal.

    Es lo que pide el encargo al cerrar una migración, y aquí importa de verdad: este paso se ejecuta **en cada
    arranque** del programa, así que una migración que se repitiera iría llenando la tabla de copias.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()
    cuantos = len(_los_canales_de(db_sesion, ficha["id"]))
    assert cuantos == 3, cuantos

    otra_vez = database.llevar_los_canales_de_los_contactos_a_su_tabla()
    assert otra_vez == 0, f"la segunda vuelta no puede llevar nada, y ha llevado {otra_vez}"
    assert len(_los_canales_de(db_sesion, ficha["id"])) == cuantos, "y no puede haber duplicados"


def test_una_ficha_sin_datos_no_crea_ningun_canal(cliente, cuenta, db_sesion):
    """Una ficha de la que no se sabe nada **no inventa canales vacíos**: no hay nada que llevar."""
    respuesta = cliente.post(
        "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Solo el nombre"}
    )
    assert respuesta.status_code == 201, respuesta.text
    suya = respuesta.json()

    database.llevar_los_canales_de_los_contactos_a_su_tabla()
    assert _los_canales_de(db_sesion, suya["id"]) == [], "sin teléfono, sin correo y sin dirección no hay canal"


def test_la_migracion_no_toca_los_campos_de_siempre(cliente, cuenta, db_sesion):
    """**Copia, no traslada**: los cuatro campos de la ficha se quedan como están.

    Los leen cinco sitios (la exportación, la búsqueda global, la ficha, la tabla y la corrección), así que moverlos
    sería romper cinco cosas para ganar ninguna. Y lo que un documento diga de un contacto **no se toca nunca**.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()

    db_sesion.expire_all()
    la_ficha = db_sesion.get(models.Contacto, ficha["id"])
    assert la_ficha.telefono == "947 123 456", la_ficha.telefono
    assert la_ficha.correo == "administracion@cooperativa.test", la_ficha.correo
    assert la_ficha.direccion == "Calle Mayor 3", la_ficha.direccion
    assert la_ficha.localidad == "Peñaranda de Bracamonte", la_ficha.localidad

# ---------------------------------------------------------------------------
# Las puertas: crear, elegir principal y lo que se exige
# ---------------------------------------------------------------------------


def _apuntar_un_canal(cliente, cuenta, contacto_id: int, **canal):
    return cliente.post(
        f"/api/contactos/{contacto_id}/canales", headers=cuenta["cabeceras"], json=canal
    )


def test_se_pueden_apuntar_varios_canales_de_la_misma_clase(cliente, cuenta, db_sesion):
    """**Varios teléfonos con su etiqueta**, que es lo que no se podía hasta hoy.

    El de siempre sigue siendo el principal —no se toca— y el nuevo se apunta con su etiqueta. La ficha devuelve
    los dos, y los cuatro campos de siempre **no se han movido**.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()

    nuevo = _apuntar_un_canal(
        cliente, cuenta, ficha["id"], clase="telefono", etiqueta="almacén", telefono="947 999 111"
    )
    assert nuevo.status_code == 200, nuevo.text

    canales = nuevo.json()["canales"]
    telefonos = [canal for canal in canales if canal["clase"] == "telefono"]
    assert len(telefonos) == 2, f"los dos teléfonos tienen que estar: {canales}"
    el_principal = [canal for canal in telefonos if canal["principal"]]
    assert len(el_principal) == 1, f"y uno solo principal: {telefonos}"
    assert el_principal[0]["telefono"] == "947 123 456", (
        f"el principal sigue siendo el de siempre: {el_principal[0]}"
    )
    assert any(canal["etiqueta"] == "almacén" for canal in telefonos), "y el nuevo con su etiqueta"


def test_elegir_principal_aparta_al_que_lo_era(cliente, cuenta, db_sesion):
    """**Un principal por clase**: al elegir uno nuevo, el anterior deja de serlo.

    Y lo garantiza **la base**, con un índice parcial: si la puerta pusiera primero el nuevo, la base rechazaría el
    cambio. Por eso se aparta al anterior antes, en la misma transacción.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()
    _apuntar_un_canal(cliente, cuenta, ficha["id"], clase="correo", etiqueta="almacén", correo="almacen@coop.test")

    suyos = _los_canales_de(db_sesion, ficha["id"])
    el_nuevo = next(canal for canal in suyos if canal.etiqueta == "almacén")

    elegido = cliente.post(
        f"/api/contactos/{ficha['id']}/canales/{el_nuevo.id}/principal", headers=cuenta["cabeceras"], json={}
    )
    assert elegido.status_code == 200, elegido.text

    los_correos = [canal for canal in elegido.json()["canales"] if canal["clase"] == "correo"]
    principales = [canal for canal in los_correos if canal["principal"]]
    assert len(principales) == 1, f"no puede haber dos principales del correo: {los_correos}"
    assert principales[0]["id"] == el_nuevo.id, f"y el principal tiene que ser el elegido: {principales[0]}"


def test_un_canal_nuevo_puede_nacer_principal(cliente, cuenta, db_sesion):
    """Y si nace principal, el que lo era **deja de serlo en la misma transacción** (nunca hay dos ni ninguno)."""
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()

    nacido = _apuntar_un_canal(
        cliente, cuenta, ficha["id"], clase="telefono", etiqueta="el móvil", telefono="600 111 222", principal=True
    )
    assert nacido.status_code == 200, nacido.text
    los_telefonos = [canal for canal in nacido.json()["canales"] if canal["clase"] == "telefono"]
    principales = [canal for canal in los_telefonos if canal["principal"]]
    assert len(principales) == 1, f"uno solo: {los_telefonos}"
    assert principales[0]["telefono"] == "600 111 222", f"y es el nuevo: {principales[0]}"


def test_lo_que_se_exige_a_un_canal_y_lo_que_no(cliente, cuenta):
    """**Se exige la clase y que haya algo escrito. No se exige formato.**

    Es la decisión del encargo con estas palabras: *«Validar sin impedir guardar información legítima»*. Un teléfono
    que es «preguntar por Juan» **se guarda**: es lo que hay apuntado en el papel.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)

    mala_clase = _apuntar_un_canal(cliente, cuenta, ficha["id"], clase="whatsapp", telefono="600")
    assert mala_clase.status_code == 422, mala_clase.status_code
    assert "no es un teléfono" in mala_clase.text, mala_clase.text

    vacio = _apuntar_un_canal(cliente, cuenta, ficha["id"], clase="telefono", etiqueta="sin número")
    assert vacio.status_code == 422, vacio.status_code
    assert "Escribe el teléfono" in vacio.text, vacio.text

    # Y lo legítimo entra **tal cual**, aunque no parezca un teléfono.
    raro = _apuntar_un_canal(
        cliente, cuenta, ficha["id"], clase="telefono", etiqueta="el del bar", telefono="preguntar por Juan"
    )
    assert raro.status_code == 200, raro.text
    assert any(
        canal["telefono"] == "preguntar por Juan" for canal in raro.json()["canales"]
    ), "lo que está apuntado en el papel se guarda tal cual"


def test_los_canales_de_otra_finca_no_se_tocan(cliente, cuenta, crear_cuenta):
    """**Aislamiento**: 404, como la ficha."""
    mio = _un_contacto_con_todo(cliente, cuenta)
    otro = crear_cuenta("otro-canal@ejemplo.test")
    respuesta = cliente.post(
        f"/api/contactos/{mio['id']}/canales",
        headers=otro["cabeceras"],
        json={"clase": "telefono", "telefono": "600 000 000"},
    )
    assert respuesta.status_code == 404, f"tiene que dar 404 y ha dado {respuesta.status_code}"

def test_corregir_un_canal_no_pierde_lo_que_no_se_manda(cliente, cuenta, db_sesion):
    """**Corrección parcial**: se cambia el número y la etiqueta se queda.

    Es el encargo con sus palabras: *«evitar […] pérdida de datos al corregir»*. En la práctica es la diferencia
    entre arreglar un número y borrar de paso cómo se llamaba ese número.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    creado = _apuntar_un_canal(
        cliente, cuenta, ficha["id"], clase="telefono", etiqueta="almacén", telefono="947 999 111"
    ).json()["canales"]
    suyo = next(canal for canal in creado if canal["etiqueta"] == "almacén")

    corregido = cliente.put(
        f"/api/contactos/{ficha['id']}/canales/{suyo['id']}",
        headers=cuenta["cabeceras"],
        json={"clase": "telefono", "telefono": "947 999 222"},
    )
    assert corregido.status_code == 200, corregido.text
    el_mismo = next(canal for canal in corregido.json()["canales"] if canal["id"] == suyo["id"])
    assert el_mismo["telefono"] == "947 999 222", f"el número tiene que cambiar: {el_mismo}"
    assert el_mismo["etiqueta"] == "almacén", (
        f"y la etiqueta quedarse: no se mandó, así que no se toca: {el_mismo}"
    )


def test_quitar_un_canal_deja_el_rastro_y_no_toca_los_demas(cliente, cuenta, db_sesion):
    """**Quitar** borra el canal pero **deja el rastro** en la auditoría, y no toca los otros.

    El encargo pide «conservar los registros antiguos»: el dato en sí no vale, el rastro sí. Y un teléfono que ya no
    es de nadie no tiene nada que conservar —**no es un documento**—.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()
    creado = _apuntar_un_canal(cliente, cuenta, ficha["id"], clase="telefono", etiqueta="el viejo", telefono="111")
    suyo = next(canal for canal in creado.json()["canales"] if canal["etiqueta"] == "el viejo")

    quitado = cliente.delete(
        f"/api/contactos/{ficha['id']}/canales/{suyo['id']}", headers=cuenta["cabeceras"]
    )
    assert quitado.status_code == 200, quitado.text
    assert all(canal["id"] != suyo["id"] for canal in quitado.json()["canales"]), "ya no está"
    # **Y los demás siguen**: el de siempre no se ha tocado.
    assert any(canal["telefono"] == "947 123 456" for canal in quitado.json()["canales"]), "el de siempre sigue"

    # El rastro, en la auditoría.
    db_sesion.expire_all()
    rastro = list(
        db_sesion.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == "contacto",
                models.Auditoria.entidad_id == ficha["id"],
                models.Auditoria.accion == "canal_quitar",
            )
        )
    )
    assert len(rastro) == 1, f"tiene que quedar el rastro de lo que se quitó: {len(rastro)}"
    assert rastro[0].datos["valor"] == ["111", None], f"con su valor, para poder saber qué había: {rastro[0].datos}"


def test_al_quitar_el_principal_otro_de_su_clase_lo_sustituye(cliente, cuenta, db_sesion):
    """**Una clase con valores no se queda sin principal**: al quitar el que lo era, lo es el más antiguo.

    Si no, la pantalla enseñaría los teléfonos **sin decir cuál usar**, que es justo lo que el principal evita.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    database.llevar_los_canales_de_los_contactos_a_su_tabla()
    # El de siempre es el principal; se apunta otro y se quita **el principal**.
    creado = _apuntar_un_canal(cliente, cuenta, ficha["id"], clase="telefono", etiqueta="otro", telefono="222")
    el_de_siempre = next(
        canal
        for canal in creado.json()["canales"]
        if canal["clase"] == "telefono" and canal["principal"]
    )
    assert el_de_siempre["telefono"] == "947 123 456", el_de_siempre

    quitado = cliente.delete(
        f"/api/contactos/{ficha['id']}/canales/{el_de_siempre['id']}", headers=cuenta["cabeceras"]
    )
    assert quitado.status_code == 200, quitado.text
    los_telefonos = [canal for canal in quitado.json()["canales"] if canal["clase"] == "telefono"]
    principales = [canal for canal in los_telefonos if canal["principal"]]
    assert len(principales) == 1, f"la clase no puede quedarse sin principal: {los_telefonos}"
    assert principales[0]["telefono"] == "222", f"y lo es el que queda: {principales[0]}"

def test_la_migracion_de_los_canales_CORRE_AL_ARRANCAR(cliente, cuenta, db_sesion):
    """**La prueba que faltaba: pasa por `crear_tablas`, no llama a la migración a mano.**

    POR QUÉ IMPORTA, y es una lección que costó un defecto real. Todas las demás pruebas de este fichero llamaban a
    `llevar_los_canales_de_los_contactos_a_su_tabla()` **directamente**, así que comprobaban que la migración
    *funciona* pero **no que esté cableada** —y el cableado es la mitad del trabajo—. Y pasó lo que tenía que pasar:
    la llamada dentro de `crear_tablas` quedó **detrás de un `return`**, o sea **código muerto**, y las fichas que ya
    existían se quedaban **sin canales** al arrancar (y sin bloque en la pantalla, porque el bloque solo sale si hay
    alguno). **Lo encontró la verificación en navegador, no una prueba.**

    Así que esta prueba hace lo que hace el programa al arrancar: **llama a `crear_tablas`** y mira a ver si el canal
    está. Si alguien vuelve a mover la llamada detrás de un `return`, esto se pone rojo.
    """
    ficha = _un_contacto_con_todo(cliente, cuenta)
    assert _los_canales_de(db_sesion, ficha["id"]) == [], "de partida no hay canales: son nuevos"

    database.crear_tablas()

    suyos = _los_canales_de(db_sesion, ficha["id"])
    assert sorted(canal.clase for canal in suyos) == ["correo", "direccion", "telefono"], (
        "el arranque tiene que llevar lo que ya estaba a su canal, y ha llevado "
        f"{[(canal.clase, canal.telefono, canal.correo) for canal in suyos]}"
    )
    assert all(canal.principal for canal in suyos), "y como principal de su clase, que es como estaban apuntados"
