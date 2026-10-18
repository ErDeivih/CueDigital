"""**Las lecturas del cuenta-horas, por las puertas** (CRM-07 #8, 14/10/2026).

Aquí se anda lo que se puede andar por la API: apuntar una lectura, ver la **cuenta** que sale en la
ficha, corregirla sin destrozarla, anularla y comprobar que lo que no se sabe se dice.

Las **reglas** del acumulado -los tramos, la sustitución, los huecos- se prueban en
`test_el_cuenta_horas_de_una_maquina.py`, sobre la función pura. Esto es la puerta.
"""


from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app import models
import datetime as dt
import pytest
def _una_maquina(cliente, cabeceras, nombre: str) -> dict:
    respuesta = cliente.post(
        "/api/maquinaria",
        headers=cabeceras,
        json={"nombre": nombre, "clase": "tractor", "propiedad": "propia", "disponibilidad": "disponible"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _una_lectura(cliente, cabeceras, maquina_id: int, **campos) -> dict:
    cuerpo = {"fecha": "2026-03-01", "valor": 1000.0, "unidad": "horas"}
    cuerpo.update(campos)
    return cliente.post(f"/api/maquinaria/{maquina_id}/lecturas", headers=cabeceras, json=cuerpo)


def _la_ficha(cliente, cabeceras, maquina_id: int) -> dict:
    respuesta = cliente.get(f"/api/maquinaria/{maquina_id}", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_una_lectura_se_apunta_y_la_ficha_dice_lo_que_marca(cliente, cuenta):
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini del contador")

    respuesta = _una_lectura(cliente, cabeceras, maquina["id"])
    assert respuesta.status_code == 201, respuesta.text
    suya = respuesta.json()
    assert suya["valor"] == 1000
    assert suya["unidad"] == "horas"
    assert suya["fecha_texto"] == "01/03/2026", "la fecha se lee como se lee en España"

    ficha = _la_ficha(cliente, cabeceras, maquina["id"])
    assert len(ficha["lecturas"]) == 1
    assert ficha["contador"]["marca"] == 1000
    assert ficha["contador"]["unidad"] == "horas"


def test_con_dos_lecturas_la_ficha_dice_cuanto_ha_subido(cliente, cuenta):
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Fendt del contador")
    _una_lectura(cliente, cabeceras, maquina["id"], fecha="2026-03-01", valor=1000.0)
    _una_lectura(cliente, cabeceras, maquina["id"], fecha="2026-06-01", valor=1250.0)

    contador = _la_ficha(cliente, cabeceras, maquina["id"])["contador"]

    assert contador["subido"] == 250
    assert contador["marca"] == 1250
    assert contador["sin_decir"] == 0


def test_una_maquina_sin_lecturas_no_dice_que_ha_trabajado_cero_horas(cliente, cuenta):
    """***No se sabe, y se dice***: `subido` sale 0 porque es una suma, y **`sin_decir` lo cuenta**."""
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini sin lecturas")

    contador = _la_ficha(cliente, cabeceras, maquina["id"])["contador"]

    assert contador["cuantas"] == 0
    assert contador["sin_decir"] >= 1
    assert "no_hay_ninguna_lectura" in contador["lo_que_falta"]


def test_corregir_el_valor_NO_cambia_la_unidad_de_kilometros_a_horas(cliente, cuenta):
    """***La regla A1, y aquí hay una trampa de verdad.***

    `unidad` trae «horas» por defecto en el esquema, así que corregir solo el valor de una lectura **en
    kilómetros** la habría pasado a horas **sin que nadie lo haya dicho**. Se distingue «no lo manda» de
    «lo manda» con `model_fields_set`, como en la avería y en la obligación.
    """
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "La furgoneta del contador")
    lectura = _una_lectura(
        cliente, cabeceras, maquina["id"], valor=50_000.0, unidad="kilometros"
    ).json()

    # Se corrige **sin mandar la unidad**: es el caso de «me equivoqué en la cifra».
    respuesta = cliente.put(
        f"/api/maquinaria/{maquina['id']}/lecturas/{lectura['id']}",
        headers=cabeceras,
        json={"fecha": "2026-03-01", "valor": 50_123.0},
    )
    assert respuesta.status_code == 200, respuesta.text

    suya = _la_ficha(cliente, cabeceras, maquina["id"])["lecturas"][0]
    assert suya["valor"] == 50_123
    assert suya["unidad"] == "kilometros", (
        "***corregir la cifra NO puede cambiar lo que se mide: lo que la petición no manda, no se borra***"
    )


def test_una_lectura_anulada_deja_de_contar_y_queda_con_su_motivo(cliente, cuenta):
    """Anular no es borrar: se queda tachada y **deja de contar** en el acumulado."""
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini que se anula")
    _una_lectura(cliente, cabeceras, maquina["id"], fecha="2026-03-01", valor=1000.0)
    mala = _una_lectura(cliente, cabeceras, maquina["id"], fecha="2026-04-01", valor=99_999.0).json()
    _una_lectura(cliente, cabeceras, maquina["id"], fecha="2026-06-01", valor=1250.0)

    respuesta = cliente.post(
        f"/api/maquinaria/{maquina['id']}/lecturas/{mala['id']}/anular",
        headers=cabeceras,
        json={"motivo": "Me equivoqué de máquina"},
    )
    assert respuesta.status_code == 200, respuesta.text

    ficha = _la_ficha(cliente, cabeceras, maquina["id"])
    assert len(ficha["lecturas"]) == 3, "la lectura sigue en el cuaderno"
    assert ficha["contador"]["subido"] == 250, "***pero no cuenta: el acumulado no se dispara***"
    suya = next(una for una in ficha["lecturas"] if una["id"] == mala["id"])
    assert suya["anulado"] is True
    assert suya["motivo_anulacion"] == "Me equivoqué de máquina"


def test_una_unidad_que_no_existe_se_rechaza_diciendo_cuales_hay(cliente, cuenta):
    """Un contador mide horas o kilómetros, y **no se suman entre sí**."""
    cabeceras = cuenta["cabeceras"]
    maquina = _una_maquina(cliente, cabeceras, "El Landini de la unidad rara")

    respuesta = _una_lectura(cliente, cabeceras, maquina["id"], unidad="fanegas")

    assert respuesta.status_code == 422, respuesta.text
    dicho = str(respuesta.json())
    assert "horas o kilómetros" in dicho, f"el aviso no dice qué se puede poner: {dicho[:200]}"


def test_una_lectura_de_otra_finca_no_es_tuya(cliente, cuenta, crear_cuenta):
    el_vecino = crear_cuenta("el-vecino-contador@ejemplo.es", "El vecino")
    suya = _una_maquina(cliente, el_vecino["cabeceras"], "El tractor del vecino")
    lectura = _una_lectura(cliente, el_vecino["cabeceras"], suya["id"]).json()
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "El Landini mio")

    respuesta = cliente.post(
        f"/api/maquinaria/{mia['id']}/lecturas",
        headers=cabeceras,
        json={"fecha": "2026-03-01", "valor": 10.0, "unidad": "horas"},
    )
    assert respuesta.status_code == 201, "lo que se prueba es que la lectura del vecino no viaja"
    assert cliente.get(
        f"/api/maquinaria/{mia['id']}", headers=cabeceras
    ).json()["lecturas"][0]["id"] != lectura["id"]


# ---------------------------------------------------------------------------
# El aislamiento, con pruebas que lo INTENTAN (15/10/2026)
# ---------------------------------------------------------------------------
#
# El barrido de `test_revision_t14` mira **nombres** en el codigo de cada ruta, y eso no demuestra que el
# ayudante filtre: lo demuestra esto. Se intenta corregir y anular una lectura que no es tuya, por las dos
# vias que hay -otra finca, y otra maquina **de la misma finca**-, y las dos tienen que contestar 404.


def test_no_se_puede_corregir_una_lectura_de_OTRA_FINCA(cliente, cuenta, crear_cuenta):
    """***El aislamiento no se hereda de la maquina: se comprueba en la lectura.***"""
    el_vecino = crear_cuenta("el-vecino-lectura@ejemplo.es", "El vecino")
    suya = _una_maquina(cliente, el_vecino["cabeceras"], "El tractor del vecino")
    lectura = _una_lectura(cliente, el_vecino["cabeceras"], suya["id"]).json()
    mia = _una_maquina(cliente, cuenta["cabeceras"], "El mio de la lectura")

    respuesta = cliente.put(
        f"/api/maquinaria/{mia['id']}/lecturas/{lectura['id']}",
        headers=cabeceras_de(cuenta),
        json={"fecha": "2026-03-01", "valor": 10.0, "unidad": "horas"},
    )

    assert respuesta.status_code == 404, respuesta.text
    # Y la del vecino sigue como estaba: no se ha tocado nada suyo.
    suyas = _la_ficha(cliente, el_vecino["cabeceras"], suya["id"])["lecturas"]
    assert len(suyas) == 1 and suyas[0]["valor"] == 1000


def test_no_se_puede_anular_una_lectura_de_OTRA_MAQUINA_de_la_misma_finca(cliente, cuenta):
    """***Ni siquiera dentro de la misma finca.*** Una lectura es de **su** maquina, y el camino lo dice."""
    cabeceras = cabeceras_de(cuenta)
    la_otra = _una_maquina(cliente, cabeceras, "El otro tractor")
    lectura = _una_lectura(cliente, cabeceras, la_otra["id"]).json()
    mia = _una_maquina(cliente, cabeceras, "El mio")

    respuesta = cliente.post(
        f"/api/maquinaria/{mia['id']}/lecturas/{lectura['id']}/anular",
        headers=cabeceras,
        json={"motivo": "Esta no es de esta maquina"},
    )

    assert respuesta.status_code == 404, respuesta.text
    suyas = _la_ficha(cliente, cabeceras, la_otra["id"])["lecturas"]
    assert len(suyas) == 1, "y la lectura sigue viva en SU maquina"
    assert suyas[0]["anulado"] is False, "***sin anular: el 404 no ha hecho nada***"


def cabeceras_de(cuenta: dict) -> dict:
    """Las cabeceras de una cuenta, que es lo que piden las llamadas."""
    return cuenta["cabeceras"]


# ---------------------------------------------------------------------------
# El rastro: quien, cuando y que decia antes (CRM-07 #8, 17/10/2026)
# ---------------------------------------------------------------------------
#
# El contrato pide, para toda entidad de negocio, **autor, fecha, version y estado de anulacion**. La casa
# tiene `correcciones` para eso, y `corregir` y `anular` ya pasaban por ahi... pero **un alta no pasa por
# ninguno de los dos**, que es exactamente la carencia que `correcciones.apuntar` vino a tapar. Estas tres
# pruebas son el rastro de las tres cosas.


def _el_rastro_de(db, lectura_id: int, accion: str):
    return db.scalar(
        select(models.Auditoria).where(
            models.Auditoria.entidad == "lectura_de_contador",
            models.Auditoria.entidad_id == lectura_id,
            models.Auditoria.accion == accion,
        )
    )


def test_el_alta_de_una_lectura_deja_rastro_con_su_autor(cliente, cuenta, db):
    """***Un alta tambien se apunta.***"""
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La del rastro")
    lectura = _una_lectura(cliente, cabeceras, mia["id"]).json()

    # ***Si no aparece, que la prueba DIGA que hay*** (17/10/2026): un `assert None is not None` no dice
    # nada, y buscar a ciegas es lo que me ha tenido dando vueltas todo el dia.
    todos = list(
        db.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == "lectura_de_contador",
                models.Auditoria.entidad_id == lectura["id"],
            )
        )
    )
    rastro = next((uno for uno in todos if uno.accion == "alta"), None)

    assert rastro is not None, (
        f"***el alta de una lectura tiene que dejar rastro***; "
        f"los que hay son: {[(uno.accion, uno.datos) for uno in todos]!r}"
    )
    assert rastro.usuario_id is not None, "***y con autor: saber QUIEN lo apunto es la mitad del rastro***"
    assert rastro.explotacion_id is not None, "y en su explotacion"
    # ***Se compara con lo que la PUERTA devolvio, no con lo que yo esperaba*** (17/10/2026): escribir la
    # fecha a mano es inventarse el dato, y asi la prueba falla el dia que el ayudante cambie de fecha por
    # defecto -que es lo que paso- sin que nada este mal.
    assert rastro.datos.get("fecha") == lectura["fecha"], f"y con su fecha: {rastro.datos!r}"
    assert rastro.datos.get("valor") == lectura["valor"]
    assert rastro.datos.get("unidad") == lectura["unidad"]


def test_la_correccion_guarda_LO_QUE_DECIA_ANTES_y_lo_que_dice_ahora(cliente, cuenta, db):
    """***Corregir no es borrar: queda el antes y el ahora.***"""
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La corregida")
    lectura = _una_lectura(cliente, cabeceras, mia["id"]).json()

    respuesta = cliente.put(
        f"/api/maquinaria/{mia['id']}/lecturas/{lectura['id']}",
        headers=cabeceras,
        json={"fecha": "2026-01-01", "valor": 1100.0},
    )
    assert respuesta.status_code == 200, respuesta.text

    rastro = _el_rastro_de(db, lectura["id"], "corregir")
    assert rastro is not None, "***la correccion tiene que dejar rastro***"
    assert rastro.usuario_id is not None, "y con autor"
    # **`{campo: [antes, ahora]}`**, que es lo que devuelve `correcciones.corregir`.
    assert rastro.datos.get("valor") == [1000.0, 1100.0], (
        f"***y con el valor de antes y el de ahora: {rastro.datos!r}***"
    )
    # Y lo que NO se toco **no aparece como cambiado**: la unidad sigue siendo la misma.
    assert "unidad" not in rastro.datos or rastro.datos.get("unidad") == ["horas", "horas"]


def test_la_anulacion_guarda_su_motivo(cliente, cuenta, db):
    """***Una lectura tachada sin decir por que no sirve dentro de un ano.***"""
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La anulada")
    lectura = _una_lectura(cliente, cabeceras, mia["id"]).json()

    respuesta = cliente.post(
        f"/api/maquinaria/{mia['id']}/lecturas/{lectura['id']}/anular",
        headers=cabeceras,
        json={"motivo": "Me equivoque de maquina"},
    )
    assert respuesta.status_code == 200, respuesta.text

    rastro = _el_rastro_de(db, lectura["id"], "anular")
    assert rastro is not None, "***la anulacion tiene que dejar rastro***"
    assert rastro.usuario_id is not None
    assert rastro.datos.get("motivo") == "Me equivoque de maquina", f"y con su motivo: {rastro.datos!r}"


def test_ningun_rastro_del_cuenta_horas_apunta_a_la_nada(cliente, cuenta, db):
    """***Un rastro sin `entidad_id` no lleva a ninguna parte.***

    Es un defecto que se cazo el 17/10/2026 al anadir el rastro del alta: la auditoria se escribia **antes
    del `flush`**, asi que `lectura.id` todavia era `None` y quedaba una fila que **no apunta a nada**. No
    rompia nada -por eso hay que vigilarlo con una prueba y no con cuidado-, y el mismo criterio que la casa
    usa con las etiquetas del rastro (`test_las_etiquetas_del_rastro_caben.py`).
    """
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La del rastro huerfano")
    lectura = _una_lectura(cliente, cabeceras, mia["id"]).json()
    cliente.post(
        f"/api/maquinaria/{mia['id']}/lecturas/{lectura['id']}/anular",
        headers=cabeceras,
        json={"motivo": "Da igual, es para que haya rastro"},
    )

    huerfanos = list(
        db.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == "lectura_de_contador",
                models.Auditoria.entidad_id.is_(None),
            )
        )
    )

    assert huerfanos == [], (
        f"***hay rastros que no apuntan a ninguna lectura: {[uno.accion for uno in huerfanos]!r}***"
    )


# ---------------------------------------------------------------------------
# El reenvio seguro (CRM-07 #8, 17/10/2026)
# ---------------------------------------------------------------------------
#
# El navegador manda una clave por **accion** -no por clic- porque el agricultor toca dos veces con los
# guantes, porque la respuesta se puede perder por el camino y porque el movil reintenta sin cobertura. Lo
# que hay que poder decir es: (1) el reenvio legitimo **no apunta dos lecturas**; (2) la misma clave con
# **otros datos** es un **conflicto**, no un «ya esta»; (3) eso mismo es lo que **distingue** un reenvio de
# una lectura **corregida despues**; y (4) la unicidad esta **en la base**, no en una consulta.


def test_reenviar_la_misma_lectura_devuelve_la_que_ya_estaba(cliente, cuenta):
    """***Un doble toque con los guantes no apunta dos lecturas.***"""
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La del reenvio")
    la_clave = "accion-123"
    primera = _una_lectura(cliente, cabeceras, mia["id"], clave_de_reenvio=la_clave).json()
    otra_vez = _una_lectura(cliente, cabeceras, mia["id"], clave_de_reenvio=la_clave).json()

    assert otra_vez["id"] == primera["id"], "***el reenvio devuelve la que ya estaba, no otra***"
    cuantas = _la_ficha(cliente, cabeceras, mia["id"])["lecturas"]
    assert len(cuantas) == 1, f"y en la ficha hay una sola: {len(cuantas)}"


def test_la_misma_clave_con_otros_datos_es_un_CONFLICTO(cliente, cuenta):
    """***Contestar «ya esta» daria por guardado algo que NO se guardo.***"""
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La del conflicto")
    la_clave = "accion-456"
    _una_lectura(cliente, cabeceras, mia["id"], clave_de_reenvio=la_clave)

    respuesta = cliente.post(
        f"/api/maquinaria/{mia['id']}/lecturas",
        headers=cabeceras,
        json={
            "fecha": "2026-03-01",
            "valor": 9999.0,
            "unidad": "horas",
            "clave_de_reenvio": la_clave,
        },
    )

    assert respuesta.status_code == 409, respuesta.text
    assert len(_la_ficha(cliente, cabeceras, mia["id"])["lecturas"]) == 1, "y no se ha apuntado nada"


def test_un_reenvio_de_una_lectura_YA_CORREGIDA_no_pasa_por_reenvio(cliente, cuenta):
    """***Distinguir la peticion original de una lectura corregida despues***, que es lo que pide el encargo.

    Se apunta con una clave, se **corrige** la lectura, y entonces llega el reenvio de la peticion
    **original**: sus datos ya no son los que hay. Devolverla en silencio seria que el agricultor diera por
    guardado lo que mando cuando en el cuaderno pone otra cosa.
    """
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La corregida y reenviada")
    la_clave = "accion-789"
    primera = _una_lectura(cliente, cabeceras, mia["id"], clave_de_reenvio=la_clave).json()

    cliente.put(
        f"/api/maquinaria/{mia['id']}/lecturas/{primera['id']}",
        headers=cabeceras,
        json={"fecha": primera["fecha"], "valor": 4321.0},
    )

    respuesta = cliente.post(
        f"/api/maquinaria/{mia['id']}/lecturas",
        headers=cabeceras,
        json={
            "fecha": primera["fecha"],
            "valor": primera["valor"],
            "unidad": primera["unidad"],
            "clave_de_reenvio": la_clave,
        },
    )

    assert respuesta.status_code == 409, (
        "***el reenvio de la original ya no coincide con lo que hay en el cuaderno***"
    )


def test_el_indice_unico_impide_dos_lecturas_con_la_misma_clave(db, cliente, cuenta):
    """***La unicidad esta EN LA BASE, no en una consulta.***

    Una consulta de «¿ya esta?» antes de insertar deja una ventana: dos peticiones **a la vez** no se ven la
    una a la otra. Lo que cierra la ventana es el indice, y esto lo comprueba **saltandose la puerta**: se
    meten dos filas con la misma clave y la segunda tiene que reventar. Si el indice no estuviera, esta
    prueba pasaria y la puerta tendria un agujero que no se ve.
    """
    cabeceras = cuenta["cabeceras"]
    mia = _una_maquina(cliente, cabeceras, "La del indice")
    _una_lectura(cliente, cabeceras, mia["id"], clave_de_reenvio="la-de-la-primera")
    guardada = db.scalar(
        select(models.LecturaDeContador).where(models.LecturaDeContador.maquina_id == mia["id"])
    )

    def _una_fila(clave):
        return models.LecturaDeContador(
            explotacion_id=guardada.explotacion_id,
            maquina_id=mia["id"],
            fecha=dt.date(2026, 5, 1),
            valor=1.0,
            unidad="horas",
            clave_de_reenvio=clave,
        )

    db.add(_una_fila("la-misma-clave"))
    db.commit()
    db.add(_una_fila("la-misma-clave"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    # ***Y las que NO traen clave no chocan entre si***: el indice es **parcial**, y sin el `WHERE` todas
    # esas filas -que son la mayoria, porque se apuntan desde la pantalla- chocarian por tener `NULL`.
    for _ in range(3):
        db.add(_una_fila(None))
    db.commit()
