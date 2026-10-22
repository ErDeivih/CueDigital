"""**Las fotos de la PAC: identidad, consistencia al guardar y el fichero exacto** (18/10/2026).

### ***Los dos defectos que la revision reprodujo, y que estas pruebas fijan***

  ***1 · Se podia recuperar la foto del año equivocado.*** *Se guardaba 2027 version 1 y 2028 version 1, y
  `GET /api/pac/foto/{version}` **solo miraba la version**: contestaba siempre la de 2027. **Una direccion que no
  lleva el año no identifica nada.***

  ***2 · Guardar no conservaba necesariamente lo evaluado.*** *Se evaluaba una tierra, se cambiaba su alias
  despues y se guardaba: **la foto se llevaba el alias nuevo sin decir nada**, y lo que quedaba guardado no era lo
  que se habia visto.*

### ***Como se corrigen***

  · **la identidad lleva el año** -`/api/pac/foto/{anio}/{version}`- **y ademas el id** -`/api/pac/foto/id/{id}`,
    que no depende de contar nada-; y al guardar se devuelven **los dos enlaces** ya compuestos;
  · **al guardar se manda `huella_de_la_fuente`**, la que devolvio el escenario que se mostro. Si la finca ha
    cambiado, **409** con lo evaluado, lo que hay y **`se_puede_recalcular`**. *No se sustituye nada en silencio.*

***Y el contenido lo calcula SIEMPRE el servidor***: *la huella solo dice «esto es lo que te ensene»; un navegador
no acredita datos de la finca.*
"""

from __future__ import annotations

import csv
import io


def _evaluar(cliente, cuenta, cuerpo: dict) -> dict:
    respuesta = cliente.post("/api/pac/escenario", headers=cuenta["cabeceras"], json=cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["escenario"]


def _guardar(cliente, cuenta, cuerpo: dict):
    return cliente.post("/api/pac/foto", headers=cuenta["cabeceras"], json=cuerpo)


def _la_foto(cliente, cuenta, cuerpo: dict) -> dict:
    respuesta = _guardar(cliente, cuenta, cuerpo)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _las_filas_del_csv(respuesta) -> list[list[str]]:
    assert respuesta.status_code == 200, respuesta.text
    return list(csv.reader(io.StringIO(respuesta.text.lstrip("\ufeff")), delimiter=";"))


# -----------------------------------------------------------------------------------------------------------
# ***1 · La identidad: dos años con la version 1 no se confunden***
# -----------------------------------------------------------------------------------------------------------


def test_dos_anios_con_la_VERSION_1_no_se_confunden(cliente, cuenta, campana, crear_parcela):
    """***El defecto, tal y como se reprodujo.***

    *Se guarda 2027 version 1 y 2028 version 1. **Las dos direcciones devuelven lo suyo**, y el id tambien.*
    """
    crear_parcela(alias="La de los dos años")

    la_de_2027 = _la_foto(cliente, cuenta, {"anio": 2027})
    la_de_2028 = _la_foto(cliente, cuenta, {"anio": 2028})
    assert (la_de_2027["version"], la_de_2028["version"]) == (1, 1), "las dos son la version 1 de su año"

    el_de_2027 = cliente.get(la_de_2027["el_detalle"], headers=cuenta["cabeceras"])
    el_de_2028 = cliente.get(la_de_2028["el_detalle"], headers=cuenta["cabeceras"])
    assert el_de_2027.status_code == 200 and el_de_2028.status_code == 200
    assert el_de_2027.json()["anio"] == 2027, f"***2027/1 devolvio {el_de_2027.json()['anio']}***"
    assert el_de_2028.json()["anio"] == 2028, f"***2028/1 devolvio {el_de_2028.json()['anio']}***"

    # *Y por id, que no depende de contar versiones.*
    por_id = cliente.get(la_de_2028["por_id"], headers=cuenta["cabeceras"])
    assert por_id.status_code == 200
    assert por_id.json()["id"] == la_de_2028["id"]
    assert por_id.json()["anio"] == 2028
    # *Y el fichero del 2028 dice 2028.*
    el_fichero = _las_filas_del_csv(cliente.get(la_de_2028["el_fichero"], headers=cuenta["cabeceras"]))
    assert "2028" in el_fichero[0][1], el_fichero[0]


def test_y_el_anio_que_no_existe_no_devuelve_la_de_otro(cliente, cuenta, campana, crear_parcela):
    """*Antes, pedir un año sin fotos podia contestar la de otro año. **Ahora, 404.***"""
    crear_parcela(alias="La del año que no hay")
    _la_foto(cliente, cuenta, {"anio": 2027})
    assert (
        cliente.get("/api/pac/foto/2031/1", headers=cuenta["cabeceras"]).status_code == 404
    ), "***un año sin fotos no puede contestar la de otro***"


# -----------------------------------------------------------------------------------------------------------
# ***2 · Lo que se guarda es lo que se evaluo***
# -----------------------------------------------------------------------------------------------------------


def test_si_la_finca_cambia_entre_evaluar_y_guardar_NO_se_guarda_nada(cliente, cuenta, campana, crear_parcela):
    """***El defecto, tal y como se reprodujo.***

    *Se evalua. Se cambia el alias de la tierra. Se guarda con la huella de lo evaluado. **409**, y el historial
    sigue **vacio**.*
    """
    la_parcela = crear_parcela(alias="Alias visto al evaluar")
    el_evaluado = _evaluar(cliente, cuenta, {"anio": 2027})
    la_huella_evaluada = el_evaluado["huella_de_la_fuente"]
    assert la_huella_evaluada, "el escenario tiene que traer su huella"

    # *Alguien cambia el alias de la tierra entre la vista previa y el guardado.*
    correccion = cliente.put(
        f"/api/parcelas/{la_parcela['id']}",
        headers=cuenta["cabeceras"],
        json={"alias": "Alias cambiado antes de guardar"},
    )
    assert correccion.status_code in (200, 204), correccion.text

    el_intento = _guardar(cliente, cuenta, {"anio": 2027, "huella_de_la_fuente": la_huella_evaluada})

    assert el_intento.status_code == 409, (
        f"***guardar lo de antes con la finca cambiada NO puede salir bien***: {el_intento.text[:300]}"
    )
    el_conflicto = el_intento.json()["detail"]
    assert el_conflicto["se_puede_recalcular"] is True, el_conflicto
    assert el_conflicto["huella_que_se_evaluo"] == la_huella_evaluada
    assert el_conflicto["huella_de_ahora"] != la_huella_evaluada
    assert el_conflicto["no_se_ha_guardado_nada"]

    # ***Y no se ha guardado nada***: *el historial esta vacio, que es la prueba de que no hubo sustitucion.*
    el_historial = cliente.get("/api/pac/historial", headers=cuenta["cabeceras"])
    assert el_historial.status_code == 404 or not el_historial.json().get("las_fotos"), (
        el_historial.text[:300]
    )


def test_y_recalcular_guarda_lo_de_ahora_diciendolo(cliente, cuenta, campana, crear_parcela):
    """***La salida del conflicto***: *recalcular es una decision explicita, y guarda lo de ahora.*

    *Lo que se guarda es lo que el servidor calcula **ahora**, y la huella guardada es la de este momento: **no se
    queda una foto que diga una cosa y una huella que diga otra**.*
    """
    la_parcela = crear_parcela(alias="Alias primero")
    el_evaluado = _evaluar(cliente, cuenta, {"anio": 2027})
    cliente.put(
        f"/api/parcelas/{la_parcela['id']}",
        headers=cuenta["cabeceras"],
        json={"alias": "Alias de ahora"},
    )

    la_foto = _la_foto(
        cliente,
        cuenta,
        {"anio": 2027, "huella_de_la_fuente": el_evaluado["huella_de_la_fuente"], "recalcular": True},
    )
    assert la_foto["version"] == 1, la_foto

    el_detalle = cliente.get(la_foto["el_detalle"], headers=cuenta["cabeceras"]).json()
    el_recinto = next(
        uno for uno in el_detalle["el_escenario"]["los_recintos"] if uno["parcela_id"] == la_parcela["id"]
    )
    assert el_recinto["alias"] == "Alias de ahora", (
        f"***recalcular guarda lo de ahora***: {el_recinto['alias']}"
    )


def test_sin_cambios_la_huella_coincide_y_se_guarda(cliente, cuenta, campana, crear_parcela):
    """*El camino bueno: evaluar y guardar sin tocar nada, con la huella.*"""
    crear_parcela(alias="La que no cambia")
    el_evaluado = _evaluar(cliente, cuenta, {"anio": 2027})
    la_foto = _la_foto(
        cliente, cuenta, {"anio": 2027, "huella_de_la_fuente": el_evaluado["huella_de_la_fuente"]}
    )
    assert la_foto["version"] == 1, la_foto

    # ***Son dos huellas distintas, y conviene no confundirlas***: *la de la foto identifica **el contenido
    # guardado** -para poder decir «este fichero es esta foto»-, y `huella_de_la_fuente` identifica **los datos de
    # los que se calculo** -para detectar que la finca cambio-. Lo que tiene que coincidir, si nada cambio, es
    # **la de la fuente**, y eso es lo que se mira.*
    el_detalle = cliente.get(la_foto["el_detalle"], headers=cuenta["cabeceras"]).json()
    assert el_detalle["el_escenario"]["huella_de_la_fuente"] == el_evaluado["huella_de_la_fuente"], (
        "***si nada cambio, lo guardado es exactamente lo que se evaluo***"
    )
    assert len(la_foto["huella"]) == 64, la_foto["huella"]


# -----------------------------------------------------------------------------------------------------------
# ***3 · Concurrencia: dos guardados a la vez***
# -----------------------------------------------------------------------------------------------------------


def test_dos_guardados_a_la_vez_no_pisan_ninguna_version(cliente, cuenta, campana, crear_parcela):
    """***Ni un 500, ni una version sobrescrita*** — y **dos iguales son la misma foto**.

    *Dos guardados simultaneos **del mismo contenido** piden el mismo numero y encuentran la misma huella: **los dos
    contestan la version 1**, que es una sola fila. **Ninguno se pierde y ninguno pisa al otro**, que es lo que
    importa.*

    ***Y la version sube cuando la evaluacion cambia***, que es el otro lado: *se comprueba aqui mismo cambiando la
    finca y guardando otra vez.*
    """
    la_parcela = crear_parcela(alias="La de la carrera")

    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock
    from sqlalchemy import event
    from app.database import engine

    # Pausar la primera petición ANTES de leer max; la segunda confirma su foto.
    # El orden antiguo (huella -> max) crea dos filas en esta intercalación.
    bloqueada, continuar = Event(), Event()
    mutex = Lock()

    def antes_de_leer_max(_conexion, _cursor, sql, _parametros, _contexto, _muchas):
        if "max(fotos_de_la_pac.version)" not in sql:
            return
        with mutex:
            primera = not bloqueada.is_set()
            if primera:
                bloqueada.set()
        if primera and not continuar.wait(15):
            raise TimeoutError("La segunda foto no liberó la primera petición")

    event.listen(engine, "before_cursor_execute", antes_de_leer_max)
    try:
        with ThreadPoolExecutor(max_workers=1) as los_hilos:
            primera = los_hilos.submit(_guardar, cliente, cuenta, {"anio": 2027})
            try:
                assert bloqueada.wait(15), "No se alcanzó la consulta de versión"
                segunda = _guardar(cliente, cuenta, {"anio": 2027})
            finally:
                continuar.set()
            las_dos = [primera.result(timeout=15), segunda]
    finally:
        event.remove(engine, "before_cursor_execute", antes_de_leer_max)

    los_codigos = sorted(una.status_code for una in las_dos)
    assert los_codigos == [200, 200], (
        f"***las dos tienen que salir bien***: {[una.text[:200] for una in las_dos]}"
    )
    # ***Un solo id y una sola version***: *el mismo contenido es la misma foto, se pidan a la vez o no.*
    los_ids = {una.json()["id"] for una in las_dos}
    las_versiones = {una.json()["version"] for una in las_dos}
    assert los_ids == {list(los_ids)[0]}, f"***dos filas para el mismo contenido***: {los_ids}"
    assert las_versiones == {1}, f"***y una sola version***: {las_versiones}"
    assert cliente.get("/api/pac/foto/2027/1", headers=cuenta["cabeceras"]).status_code == 200

    # ***Y el otro lado, con la finca cambiada: version 2.***
    cliente.put(
        f"/api/parcelas/{la_parcela['id']}",
        headers=cuenta["cabeceras"],
        json={"alias": "La de la carrera, corregida"},
    )
    la_de_verdad = _la_foto(cliente, cuenta, {"anio": 2027})
    assert la_de_verdad["version"] == 2, f"***una evaluacion distinta SI es otra version***: {la_de_verdad}"


def test_el_mismo_contenido_guardado_dos_veces_es_la_MISMA_foto(cliente, cuenta, campana, crear_parcela):
    """***La respuesta perdida no llena el historial de fotos iguales*** (19/10/2026).

    *El movil guardaba, se perdia la respuesta, reintentaba, y quedaba una segunda version **con el mismo
    contenido**. La huella es del contenido, asi que **dos evaluaciones identicas son la misma foto**: se contesta la
    que ya estaba, con `ya_estaba` para poder decirlo.*
    """
    crear_parcela(alias="La del reintento")

    la_primera = _la_foto(cliente, cuenta, {"anio": 2027})
    assert la_primera["version"] == 1 and la_primera["ya_estaba"] is False, la_primera

    la_repetida = _la_foto(cliente, cuenta, {"anio": 2027})
    assert la_repetida["id"] == la_primera["id"], f"***tiene que ser la misma foto***: {la_repetida}"
    assert la_repetida["version"] == 1, la_repetida
    assert la_repetida["ya_estaba"] is True, la_repetida

    # *Y en el historial hay UNA, no dos.*
    el_historial = cliente.get("/api/pac/foto/historial", headers=cuenta["cabeceras"]).json()
    las_de_2027 = [una for una in el_historial["las_fotos"] if una["anio"] == 2027]
    assert len(las_de_2027) == 1, f"***el reintento no puede dejar dos fotos***: {las_de_2027}"


# -----------------------------------------------------------------------------------------------------------
# ***4 · Aislamiento entre fincas***
# -----------------------------------------------------------------------------------------------------------


def test_otra_finca_no_puede_leer_la_foto(cliente, cuenta, campana, crear_parcela, crear_cuenta):
    """***Ni por año y version, ni por id.***"""
    crear_parcela(alias="La de la finca de al lado")
    la_foto = _la_foto(cliente, cuenta, {"anio": 2027})

    la_otra = crear_cuenta("la-de-al-lado@ejemplo.test")
    for camino in (la_foto["el_detalle"], la_foto["por_id"], la_foto["el_fichero"]):
        respuesta = cliente.get(camino, headers=la_otra["cabeceras"])
        assert respuesta.status_code == 404, f"***{camino} no es suya***: {respuesta.status_code}"


# -----------------------------------------------------------------------------------------------------------
# ***5 · El fichero es exactamente la foto***
# -----------------------------------------------------------------------------------------------------------


def test_la_exportacion_coincide_con_el_detalle_y_conserva_la_version(cliente, cuenta, campana, crear_parcela):
    """*Recinto a recinto, y con la version y el año en la cabecera.*"""
    crear_parcela(alias="La del fichero")
    la_foto = _la_foto(cliente, cuenta, {"anio": 2027})
    el_detalle = cliente.get(la_foto["el_detalle"], headers=cuenta["cabeceras"]).json()

    las_filas = _las_filas_del_csv(cliente.get(la_foto["el_fichero"], headers=cuenta["cabeceras"]))
    las_de_los_recintos = las_filas[2:]

    assert len(las_de_los_recintos) == len(el_detalle["el_escenario"]["los_recintos"])
    for uno in el_detalle["el_escenario"]["los_recintos"]:
        la_fila = next((f for f in las_de_los_recintos if f[1] == (uno.get("alias") or "")), None)
        assert la_fila is not None, f"***falta {uno.get('alias')} en el fichero***"
        assert la_fila[7] == ("si" if uno.get("completa") else "no"), la_fila
        assert la_fila[8] == " ".join(uno.get("falta") or []), la_fila

    assert "version 1" in las_filas[0][0], las_filas[0]
    assert "2027" in las_filas[0][1], las_filas[0]


def test_y_guardar_no_cambia_el_paquete_ni_afirma_elegibilidad(cliente, cuenta, campana, crear_parcela):
    """*Ni el paquete cambia, ni el fichero lleva una columna de elegibilidad.*"""
    crear_parcela(alias="La de la elegibilidad")
    antes = cliente.get("/api/pac/paquete", headers=cuenta["cabeceras"]).json()
    la_foto = _la_foto(cliente, cuenta, {"anio": 2027})
    despues = cliente.get("/api/pac/paquete", headers=cuenta["cabeceras"]).json()
    assert despues == antes, "***guardar una foto no puede cambiar el paquete***"

    las_filas = _las_filas_del_csv(cliente.get(la_foto["el_fichero"], headers=cuenta["cabeceras"]))
    los_nombres = " ".join(las_filas[1]).lower()
    for prohibida in ("elegib", "subvencion", "importe", "ayuda"):
        assert prohibida not in los_nombres, f"***no puede llevar «{prohibida}»***"
