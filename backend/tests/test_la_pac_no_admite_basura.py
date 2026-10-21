"""**La PAC no admite basura, y lo guardado no se reescribe** (19/10/2026).

### ***Lo que pide la revision, con sus palabras***

*«Validar entrada con esquemas, años, campos y recintos de la explotacion. **Los errores de datos deben ser
claros, sin 500 ni cambios parciales**»*, y en otro sitio: ***«historial inmutable»***.

### ***Por que esto merece sus propias pruebas***

*Una puerta que **casi siempre** valida es una puerta que un dia escribe media fila. Y lo que aqui se guarda es
**lo que se le ensena al asesor**: si una foto se pudiera reescribir, dejaria de ser una foto.*

*Lo que se comprueba, y **en la puerta, no en la funcion***:*

  1. **un año que no es un año** -> **422**, y no 500;
  2. **un recinto que no es de la finca** -> **422** y **dice cuales**;
  3. **una superficie negativa** -> **422**;
  4. **una bateria de basura** -> **nunca un 500 y nunca algo escrito**;
  5. **una foto guardada no se puede cambiar ni borrar**: *no hay puerta que lo haga, y dos lecturas devuelven lo
     mismo.*
"""

from __future__ import annotations


def _basura(cliente, cuenta, cuerpo: dict):
    return cliente.post("/api/pac/escenario", headers=cuenta["cabeceras"], json=cuerpo)


def test_un_anio_que_no_es_un_anio_se_rechaza_con_422(cliente, cuenta):
    """***422 y no 500***: *un año imposible es un error de quien llama, no del programa.*"""
    for el_malo in (1800, 2500, "mil", None):
        la_respuesta = _basura(cliente, cuenta, {"anio": el_malo})
        assert la_respuesta.status_code == 422, (
            f"***anio={el_malo!r} tenia que dar 422***: {la_respuesta.status_code} {la_respuesta.text[:200]}"
        )


def test_un_recinto_que_no_es_de_la_finca_se_DICE(cliente, cuenta, campana, crear_parcela):
    """***Y se dice cual***: *evaluar una tierra que no es de la finca seria evaluar otra cosa.*

    *Ignorarlo en silencio seria peor: el agricultor veria una evaluacion que **no** incluye lo que pidio, y
    creeria que si.*
    """
    crear_parcela(alias="La de la finca")
    la_respuesta = _basura(
        cliente, cuenta, {"anio": 2027, "cambios": {"999999": {"cultivo": {"especie": "trigo"}}}}
    )

    assert la_respuesta.status_code == 422, la_respuesta.text[:300]
    el_cuerpo = la_respuesta.json().get("detail") or {}
    assert 999999 in (el_cuerpo.get("los_que_no_son_suyos") or []), el_cuerpo
    assert el_cuerpo.get("mensaje"), "***y tiene que decirlo con palabras***"


def test_una_superficie_negativa_se_rechaza(cliente, cuenta, campana, crear_parcela):
    """*Una tierra no tiene hectareas negativas: es un error de quien llama.*"""
    la_parcela = crear_parcela(alias="La de la superficie imposible")
    la_respuesta = _basura(
        cliente,
        cuenta,
        {
            "anio": 2027,
            "cambios": {str(la_parcela["id"]): {"cultivo": {"especie": "trigo", "superficie_cultivada_ha": -5}}},
        },
    )
    assert la_respuesta.status_code == 422, la_respuesta.text[:300]


def test_una_bateria_de_basura_NO_da_500_ni_escribe_nada(cliente, cuenta, campana, crear_parcela):
    """***Ni un 500 y ni una fila***: *el contrato lo pide asi, «sin 500 ni cambios parciales».*"""
    crear_parcela(alias="La de la basura")
    el_antes = cliente.get("/api/pac/paquete", headers=cuenta["cabeceras"]).json()

    las_basuras = [
        {},
        {"anio": 2027, "cambios": "no soy un diccionario"},
        {"anio": 2027, "cambios": {"uno": {"cultivo": {"especie": "trigo"}}}},
        {"anio": 2027, "cambios": {"1": {"cultivo": "no soy un cultivo"}}},
        {"anio": [2027]},
        {"anio": 2027, "campana_id": "la de al lado"},
        {"anio": 2027, "contra": "no soy cambios"},
    ]
    for la_basura in las_basuras:
        la_respuesta = cliente.post(
            "/api/pac/escenario", headers=cuenta["cabeceras"], json=la_basura
        )
        assert la_respuesta.status_code != 500, (
            f"***un 500 con {la_basura!r}***: {la_respuesta.text[:300]}"
        )
        assert la_respuesta.status_code in (200, 422), la_respuesta.status_code

    # ***Y no se ha escrito nada***: *el paquete sale exactamente igual.*
    el_despues = cliente.get("/api/pac/paquete", headers=cuenta["cabeceras"]).json()
    assert el_despues == el_antes, "***la basura no puede tocar la finca***"


def test_una_foto_guardada_NO_se_puede_cambiar_ni_borrar(cliente, cuenta, campana, crear_parcela):
    """***«Historial inmutable», comprobado por donde se puede comprobar.***

    *No basta con que no haya un boton: **se mira que la aplicacion no tenga la puerta** -un `PUT`, un `PATCH` o un
    `DELETE` sobre una foto-, porque una puerta que existe se acaba llamando.*
    """
    # ***Se mira el contrato PUBLICADO*** (`/openapi.json`), no el objeto de Python: *es lo que de verdad se
    # sirve, y es lo que un cliente -o un ataque- puede llamar. Si una puerta no esta ahi, no existe.*
    #
    # *Y no vale mirar `app.main.app`: **no es la aplicacion montada** -tiene 44 rutas y ninguna de la PAC-, asi
    # que la prueba habria pasado **sin mirar nada**. Con el contrato, si no hay ruta, no hay nada que mirar y el
    # `assert` de abajo lo dice.*
    el_contrato = cliente.get("/openapi.json").json()
    las_de_la_foto = {
        camino: sorted(lo_que_hay)
        for camino, lo_que_hay in (el_contrato.get("paths") or {}).items()
        if camino.startswith("/api/pac/foto")
    }
    assert las_de_la_foto, "***tiene que haber puertas de fotos en el contrato***"
    for camino, los_metodos in las_de_la_foto.items():
        assert not (set(los_metodos) & {"put", "patch", "delete"}), (
            f"***{camino} admite {los_metodos}: una foto guardada no se reescribe***"
        )


def test_y_dos_lecturas_de_la_misma_foto_dan_lo_mismo(cliente, cuenta, campana, crear_parcela):
    """***Lo guardado se lee igual siempre***, *aunque la finca cambie por debajo.*"""
    crear_parcela(alias="La de la lectura repetida")
    la_foto = cliente.post(
        "/api/pac/foto", headers=cuenta["cabeceras"], json={"anio": 2027}
    ).json()

    la_primera = cliente.get(la_foto["el_detalle"], headers=cuenta["cabeceras"]).json()
    la_segunda = cliente.get(la_foto["el_detalle"], headers=cuenta["cabeceras"]).json()
    assert la_primera == la_segunda, "***dos lecturas seguidas no pueden dar cosas distintas***"
    assert la_primera["huella"] == la_foto["huella"], "***ni cambiar la huella***"
    assert la_primera["creada_en"] == la_foto["creada_en"], "***ni la fecha***"

    # *Y por id, lo mismo.*
    la_por_id = cliente.get(la_foto["por_id"], headers=cuenta["cabeceras"]).json()
    assert la_por_id["el_escenario"] == la_primera["el_escenario"], (
        "***el id y el año tienen que dar la misma foto***"
    )
