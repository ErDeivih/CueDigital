"""**La foto evaluada: lo ensenado al asesor no cambia, y el fichero es esa foto** (18/10/2026, CRM-09).

### ***Lo que el contrato pide, con sus palabras***

  *«**la exportacion coincide con el detalle y conserva la version evaluada**»*.

### ***Por que la foto guarda el CONTENIDO y no la receta***

*El escenario **se calcula y se tira** -que es lo correcto para **comparar**-, pero **ensenar** es otra cosa: hace
falta que lo que se enseno **siga siendo lo mismo** dentro de un año. **Por eso la foto guarda el escenario
entero**, y la exportacion lo **lee** en vez de recalcularlo: si recalculara, un cambio en la finca haria que el
fichero dijera una cosa y la foto otra.*
"""

from __future__ import annotations

import csv
import io


def _la_foto(cliente, cuenta, cuerpo: dict | None = None) -> dict:
    respuesta = cliente.post(
        "/api/pac/foto", headers=cuenta["cabeceras"], json=cuerpo or {"anio": 2027}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _las_filas_del_csv(cliente, cuenta, version: int) -> list[list[str]]:
    respuesta = cliente.get(
        f"/api/pac/foto/{version}/exportar", headers=cuenta["cabeceras"]
    )
    assert respuesta.status_code == 200, respuesta.text
    el_texto = respuesta.text.lstrip("\ufeff")
    return list(csv.reader(io.StringIO(el_texto), delimiter=";"))


def test_guardar_una_foto_le_pone_version_y_fecha(cliente, cuenta, campana, crear_parcela):
    """***La primera foto es la version 1***, *con su huella, y no toca el paquete.*"""
    crear_parcela(alias="La de la primera foto")
    antes = cliente.get("/api/pac/paquete", headers=cuenta["cabeceras"]).json()

    la_foto = _la_foto(cliente, cuenta)

    assert la_foto["version"] == 1, la_foto
    assert la_foto["anio"] == 2027
    assert len(la_foto["huella"]) == 64, la_foto["huella"]
    assert la_foto["creada_en"], la_foto
    assert la_foto["es_hipotesis"] is True and la_foto["no_es_garantia"] is True
    assert la_foto["toca_lo_guardado"] is False

    despues = cliente.get("/api/pac/paquete", headers=cuenta["cabeceras"]).json()
    assert despues == antes, "***guardar una foto no puede cambiar el paquete***"


def test_dos_fotos_son_la_1_y_la_2(cliente, cuenta, campana, crear_parcela):
    """*La version sube, y cada foto es la suya.*"""
    crear_parcela(alias="La de las dos fotos")
    la_primera = _la_foto(cliente, cuenta)
    la_segunda = _la_foto(cliente, cuenta)

    assert (la_primera["version"], la_segunda["version"]) == (1, 2), (la_primera, la_segunda)
    assert la_primera["creada_en"] <= la_segunda["creada_en"]


def test_la_exportacion_COINCIDE_con_el_detalle(cliente, cuenta, campana, crear_parcela):
    """***El fichero y el detalle dicen lo mismo***, *recinto a recinto.*

    *Es la mitad del contrato: «la exportacion **coincide con el detalle**».*
    """
    crear_parcela(alias="La del fichero")
    la_foto = _la_foto(cliente, cuenta)
    el_detalle = cliente.get(
        f"/api/pac/foto/{la_foto['version']}", headers=cuenta["cabeceras"]
    ).json()["el_escenario"]

    las_filas = _las_filas_del_csv(cliente, cuenta, la_foto["version"])
    las_de_los_recintos = las_filas[2:]  # *las dos primeras son la cabecera y los nombres de columna*

    assert len(las_de_los_recintos) == len(el_detalle["los_recintos"]), (
        f"***el fichero tiene que traer los mismos recintos***: {len(las_de_los_recintos)} "
        f"frente a {len(el_detalle['los_recintos'])}"
    )
    por_referencia = {fila[0]: fila for fila in las_de_los_recintos}
    for uno in el_detalle["los_recintos"]:
        la_fila = por_referencia.get(uno.get("referencia") or "")
        assert la_fila is not None, f"***falta el recinto en el fichero***: {uno.get('alias')}"
        assert la_fila[1] == (uno.get("alias") or ""), la_fila
        assert la_fila[7] == ("si" if uno.get("completa") else "no"), la_fila
        assert la_fila[8] == " ".join(uno.get("falta") or []), la_fila


def test_y_CONSERVA_la_version_evaluada(cliente, cuenta, campana, crear_parcela, db_sesion):
    """***Cambiar la finca despues NO cambia lo que se enseno.***

    *Se guarda la foto, se siembra una tierra -con el cultivo de verdad, en la base-, y **la foto y su fichero
    siguen diciendo lo mismo**: eso es «conserva la version evaluada».*
    """
    la_parcela = crear_parcela(alias="La que cambia despues")
    la_foto = _la_foto(cliente, cuenta)

    el_antes = cliente.get(f"/api/pac/foto/{la_foto['version']}", headers=cuenta["cabeceras"]).json()
    las_filas_antes = _las_filas_del_csv(cliente, cuenta, la_foto["version"])

    # *Ahora se siembra la tierra de verdad, con la puerta del cultivo.*
    cliente.post(
        "/api/cultivos",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "parcela_id": la_parcela["id"],
            "especie": "cebada",
            "ecorregimen": "secano",
            "superficie_cultivada_ha": 2.0,
        },
    )

    el_despues = cliente.get(f"/api/pac/foto/{la_foto['version']}", headers=cuenta["cabeceras"]).json()
    las_filas_despues = _las_filas_del_csv(cliente, cuenta, la_foto["version"])

    assert el_despues == el_antes, "***la foto guardada no puede cambiar***"
    assert las_filas_despues == las_filas_antes, "***ni el fichero que se saca de ella***"

    # *Y la cabecera del fichero lleva la version y el año: el papel dice de que es.*
    assert "version 1" in las_filas_antes[0][0], las_filas_antes[0]
    assert "2027" in las_filas_antes[0][1], las_filas_antes[0]


def test_la_foto_no_afirma_elegibilidad(cliente, cuenta, campana, crear_parcela):
    """***Ni una columna de elegibilidad***: *este programa no la afirma, y el fichero tampoco.*

    *Y una foto que no existe es un 404, no una inventada.*
    """
    crear_parcela(alias="La de la elegibilidad")
    la_foto = _la_foto(cliente, cuenta)
    las_filas = _las_filas_del_csv(cliente, cuenta, la_foto["version"])

    los_nombres = " ".join(las_filas[1]).lower()
    for prohibida in ("elegib", "subvencion", "importe", "ayuda"):
        assert prohibida not in los_nombres, (
            f"***el fichero no puede llevar «{prohibida}»***: {las_filas[1]}"
        )

    assert cliente.get(
        f"/api/pac/foto/{la_foto['version'] + 99}", headers=cuenta["cabeceras"]
    ).status_code == 404
