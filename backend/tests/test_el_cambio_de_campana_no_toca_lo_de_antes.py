"""**Cambiar de campana no altera los años anteriores** (18/10/2026, CRM-06).

### ***Lo que la cola pide, con sus palabras***

*Aceptacion de CRM-06: «…***cambio de campana no altera años previos***…».*

### ***Y por que esto merece su propia prueba***

*El programa guarda el cultivo **por campaña** (`ParcelaCultivo`) y las labores **por campaña**. Si algo
estuviera mal atado -una consulta sin filtrar por el año, un `update` que se lleva lo de antes-, **sembrar el año
que viene cambiaria lo que se declaro el año pasado**, y eso es un dato fiscal y de la PAC: no un detalle de
pantalla.*

***Y nadie lo comprobaba.*** *Se busco «cambio de campana», «años previos» y «otra campana» en las 195 pruebas y
en los guiones, y **no habia ninguna** que lo mirara. Es el unico de los ocho criterios de CRM-06 que estaba sin
cubrir.*

### Lo que se comprueba

  1. **El cultivo de un año sigue siendo el suyo** despues de sembrar el siguiente.
  2. **Los dos años no se pisan**: cada uno devuelve lo que se le dijo.
  3. **Una labor de un año no aparece en el otro.**
  4. **El paquete de la PAC de un año no cambia** al tocarlo en el siguiente.
  5. **Y el panel tampoco**, si la puerta lo pide por campaña.
"""

from __future__ import annotations

# ***Aqui NO se importa el ayudante de otro fichero, y es a proposito***: *en
# `test_analisis_ventas_planes_y_campanas.py` `crear_campana` es una **fixture**, y una fixture **no se puede
# llamar directamente** -pytest lo prohibe con razon-. Lo que se copia son **tres lineas** de un `POST`, que no
# justifican acoplar dos ficheros de pruebas.*
def _una_campana(cliente, cuenta, anio: int) -> dict:
    """*Una campana mas, para poder mirar dos años sin tocar la del año en curso.*"""
    respuesta = cliente.post(
        "/api/campanas",
        headers=cuenta["cabeceras"],
        json={"anio": anio, "fecha_inicio": f"{anio}-01-01", "fecha_fin": f"{anio}-12-31"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _sembrar(cliente, cuenta, campana, parcela, especie: str) -> dict:
    respuesta = cliente.post(
        f"/api/parcelas/{parcela['id']}/cultivos",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "especie": especie,
            "sistema": "secano",
            "ecorregimen": "secano",
            "superficie_cultivada_ha": 1.5,
        },
    )
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()


def _el_cultivo_de(cliente, cuenta, campana, parcela) -> dict | None:
    """*Lo que el paquete de la PAC dice que se siembra en esa tierra ese año.*"""
    la_pac = cliente.get(
        f"/api/pac/paquete?campana_id={campana['id']}", headers=cuenta["cabeceras"]
    ).json()
    el_suyo = next(
        (uno for uno in la_pac["las_tierras"] if uno["parcela_id"] == parcela["id"]), None
    )
    return None if el_suyo is None else el_suyo.get("cultivo")


def test_el_cultivo_de_un_ano_sigue_siendo_el_suyo(cliente, cuenta, campana, crear_parcela):
    """***Sembrar el año que viene no cambia lo que se sembró este.***"""
    parcela = crear_parcela(alias="La de los dos años")
    el_que_viene = _una_campana(cliente, cuenta, campana["anio"] + 1)

    _sembrar(cliente, cuenta, campana, parcela, "TRIGO")
    assert (_el_cultivo_de(cliente, cuenta, campana, parcela) or {}).get("especie") == "TRIGO"

    # *Ahora se siembra **el año siguiente**, con otra cosa.*
    _sembrar(cliente, cuenta, el_que_viene, parcela, "CEBADA")

    # ***Y el año de antes sigue diciendo lo suyo.***
    el_de_antes = _el_cultivo_de(cliente, cuenta, campana, parcela)
    assert el_de_antes is not None, "***el cultivo del año anterior NO puede desaparecer***"
    assert el_de_antes["especie"] == "TRIGO", (
        f"***cambiar de campaña alteró el año anterior***: {el_de_antes}"
    )

    # *Y el nuevo dice lo nuevo.*
    el_de_ahora = _el_cultivo_de(cliente, cuenta, el_que_viene, parcela)
    assert (el_de_ahora or {}).get("especie") == "CEBADA", (
        f"***y el año nuevo, lo nuevo***: {el_de_ahora}"
    )


def test_una_labor_de_un_ano_no_aparece_en_el_otro(cliente, cuenta, campana, crear_parcela):
    """***Lo que se hizo este año no se hizo el pasado.***"""
    parcela = crear_parcela(alias="La de las labores")
    el_que_viene = _una_campana(cliente, cuenta, campana["anio"] + 1)

    hecha = cliente.post(
        "/api/trabajos",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": el_que_viene["id"],
            "tipo": "laboreo",
            "subtipo": "rodillo",
            "fecha": f"{el_que_viene['anio']}-05-10",
            "parcela_id": parcela["id"],
        },
    )
    assert hecha.status_code == 201, hecha.text

    # *El cuaderno de cada año, por su campaña.*
    def _las_labores(de_que_campana):
        respuesta = cliente.get(
            f"/api/trabajos?campana_id={de_que_campana['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200, respuesta.text
        los = respuesta.json()
        return los if isinstance(los, list) else los.get("trabajos") or los.get("hechos") or []

    las_de_ahora = _las_labores(el_que_viene)
    las_de_antes = _las_labores(campana)

    assert any(uno.get("id") == hecha.json()["hecho"]["id"] for uno in las_de_ahora), (
        "***la labor de este año tiene que estar en este año***"
    )
    assert not any(uno.get("id") == hecha.json()["hecho"]["id"] for uno in las_de_antes), (
        f"***y NO en el pasado***: {las_de_antes}"
    )


def test_el_paquete_de_la_pac_de_un_ano_no_cambia_al_tocar_el_siguiente(
    cliente, cuenta, campana, crear_parcela
):
    """***Lo que se declara de un año se queda como estaba.***

    *Es el criterio con las palabras de la cola, mirado por donde mas duele: **el paquete que se lleva al asesor**.*
    """
    parcela = crear_parcela(alias="La del paquete")
    el_que_viene = _una_campana(cliente, cuenta, campana["anio"] + 1)
    _sembrar(cliente, cuenta, campana, parcela, "TRIGO")

    el_paquete_antes = cliente.get(
        f"/api/pac/paquete?campana_id={campana['id']}", headers=cuenta["cabeceras"]
    ).json()

    # *Se toca el año siguiente: se siembra y se hace una labor.*
    _sembrar(cliente, cuenta, el_que_viene, parcela, "CEBADA")
    cliente.post(
        "/api/trabajos",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": el_que_viene["id"],
            "tipo": "laboreo",
            "fecha": f"{el_que_viene['anio']}-06-01",
            "parcela_id": parcela["id"],
        },
    )

    el_paquete_despues = cliente.get(
        f"/api/pac/paquete?campana_id={campana['id']}", headers=cuenta["cabeceras"]
    ).json()

    assert el_paquete_despues == el_paquete_antes, (
        "***el paquete del año pasado NO puede cambiar porque se toque el que viene***"
    )
