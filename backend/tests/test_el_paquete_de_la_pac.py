"""**El paquete preparatorio de la PAC** (CRM-09, 17/10/2026).

### ***Por que existe***

*`app/pac.py` tenia las tres piezas que la cola pide -el porcentaje con numerador y denominador, la tierra
sin cultivo que **no** se pinta de verde, y la fuente que no se aplica si es de otra campaña- **y no lo
llamaba nadie**: su unico consumidor era su propia prueba. **El mismo patron que `paneles.py`.***

Lo que defiende esta prueba, y es lo que el contrato pide con sus palabras:

  1. ***«paquete preparatorio por recinto: referencias, superficie, cultivos, practica… y cuestiones
     pendientes»***: una entrada por tierra, con lo que hay y **con lo que falta**.
  2. ***«falta area/cultivo/evidencia -> incompleto»***: una tierra sin cultivo **no es una tierra sin
     sembrar**: es una tierra de la que **no consta**, y el paquete lo dice.
  3. ***«tierra sin cultivo no desaparece para pintar verde»***: el porcentaje va sobre **toda la finca**, y
     las hectareas que se quedan fuera **se dicen** -no se esconden en el denominador-.
  4. ***«fuente de otra campaña/comunidad no se aplica»***, y **sin fuente no se puede decir que nada sea
     elegible**: la respuesta lo dice en voz alta.
  5. ***«no envio directo ni garantia de elegibilidad»***: la advertencia **viaja con el paquete**.
"""

from __future__ import annotations


def el_paquete(cliente, cuenta, **consulta) -> dict:
    respuesta = cliente.get("/api/pac/paquete", headers=cuenta["cabeceras"], params=consulta)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def la_tierra(datos: dict, parcela_id: int) -> dict:
    return next(una for una in datos["las_tierras"] if una["parcela_id"] == parcela_id)


def test_cada_tierra_dice_lo_que_hay_y_lo_que_FALTA(cliente, cuenta, campana, crear_parcela):
    """*«Paquete preparatorio por recinto… y cuestiones pendientes»*, y *«falta cultivo -> incompleto»*."""
    con_cultivo = crear_parcela(alias="La sembrada", superficie_ha=6.0)
    sin_cultivo = crear_parcela(alias="La que no consta", superficie_ha=4.0)
    cliente.post(
        f"/api/parcelas/{con_cultivo['id']}/cultivos",
        headers=cuenta["cabeceras"],
        json={
            "campana_id": campana["id"],
            "especie": "Trigo blando",
            "ecorregimen": "siembra directa",
            "superficie_cultivada_ha": "6.00",
        },
    )

    datos = el_paquete(cliente, cuenta)
    la_sembrada = la_tierra(datos, con_cultivo["id"])
    la_otra = la_tierra(datos, sin_cultivo["id"])

    # **La que tiene cultivo y ecorregimen**: *lo unico que le puede faltar es la referencia del SIGPAC, y si
    # falta se dice -no se da por buena-.*
    assert la_sembrada["cultivo"]["especie"] == "Trigo blando", la_sembrada
    assert la_sembrada["cultivo"]["ecorregimen"] == "siembra directa"
    assert "falta_cultivo" not in la_sembrada["falta"], la_sembrada["falta"]
    assert "falta_ecorregimen" not in la_sembrada["falta"], la_sembrada["falta"]

    # ***Y la que no tiene cultivo: lo dice, y queda incompleta.***
    assert la_otra["cultivo"] is None
    assert "falta_cultivo" in la_otra["falta"], la_otra["falta"]
    assert la_otra["completa"] is False, "***una tierra de la que no consta el cultivo NO esta completa***"

    assert datos["las_incompletas"] >= 1, "y el paquete cuenta cuantas quedan"


def test_el_porcentaje_va_sobre_TODA_la_finca_no_sobre_lo_sembrado(cliente, cuenta, campana, crear_parcela):
    """***«Tierra sin cultivo no desaparece para pintar verde».***

    *10 ha de finca con 6 sembradas son el **60%**, no el 100%: con el denominador tramposo -solo las 6-, un
    año malo saldria al 100% y nadie veria las 4 ha que se han quedado fuera.*
    """
    la_mitad = crear_parcela(alias="Sembrada a medias", superficie_ha=6.0)
    la_otra = crear_parcela(alias="En barbecho", superficie_ha=4.0)
    cliente.post(
        f"/api/parcelas/{la_mitad['id']}/cultivos",
        headers=cuenta["cabeceras"],
        json={"campana_id": campana["id"], "especie": "Cebada", "superficie_cultivada_ha": "6.00"},
    )

    el_resumen = el_paquete(cliente, cuenta)["el_resumen"]

    assert el_resumen["denominador"] == 10.0, f"***el denominador es TODA la finca***: {el_resumen}"
    assert el_resumen["numerador"] == 6.0, el_resumen
    assert el_resumen["porcentaje"] == 60.0, f"***60%, no 100%***: {el_resumen}"
    # ***Y las hectareas que se quedan fuera, dichas***: no se esconden en el numerador.
    assert el_resumen["sin_cultivo"] == 4.0, f"***las 4 ha se dicen***: {el_resumen}"
    assert el_resumen["se_queda_fuera"] == 4.0, el_resumen


def test_sin_fuente_legal_NO_se_dice_que_nada_sea_elegible(cliente, cuenta, crear_parcela):
    """*«Ninguna competencia autoriza usar su interpretacion como norma».*"""
    crear_parcela(alias="Una cualquiera", superficie_ha=1.0)

    datos = el_paquete(cliente, cuenta)

    assert datos["la_fuente"] is None, f"***no hay fuente cargada, y se dice***: {datos['la_fuente']}"
    assert datos["aviso_de_la_fuente"], "***y con ella, lo que no se puede afirmar***"
    assert "elegible" in datos["aviso_de_la_fuente"].lower(), datos["aviso_de_la_fuente"]


def test_la_advertencia_de_que_NO_es_la_declaracion_viaja_con_el_paquete(cliente, cuenta, crear_parcela):
    """***«No envio directo ni garantia de elegibilidad».***

    *Tiene que viajar **en la respuesta** y no solo en la pantalla, porque el paquete se puede guardar y
    reenviar: la advertencia tiene que ir con el.*
    """
    crear_parcela(alias="Una cualquiera", superficie_ha=1.0)

    datos = el_paquete(cliente, cuenta)

    assert datos["no_es_garantia"], "la advertencia tiene que venir"
    # ***Con sus tildes***: *el texto es el que ve el agricultor, y «garantía» lleva tilde. Buscar la forma sin
    # tilde es buscar una cadena que no esta en ningun sitio -y el fallo era de la prueba, no del codigo-.*
    assert "garantía de elegibilidad" in datos["no_es_garantia"].lower(), datos["no_es_garantia"]
    assert "declaración" in datos["no_es_garantia"].lower(), datos["no_es_garantia"]


def test_la_superficie_DECLARADA_y_la_MEDIDA_se_dicen_por_separado(cliente, cuenta, crear_parcela):
    """*Son dos cosas distintas, y `superficies.py` tiene esa distincion escrita: no se suman ni se confunden.*"""
    crear_parcela(alias="La del recinto", superficie_ha=2.43)

    una = el_paquete(cliente, cuenta)["las_tierras"][0]

    assert "superficie_ha" in una, "lo que mide el recinto"
    # ***Y la del SIGPAC, aparte***: *lo que mide el recinto y lo que la administracion tiene apuntado pueden
    # no coincidir, y el asesor necesita las dos. Y **no se llama «declarada»**, porque esa columna no existe.*
    assert "superficie_sigpac_ha" in una, "***y la del SIGPAC, aparte***"
    assert "superficie_declarada_ha" not in una, "***no hay superficie declarada: no se inventa***"
