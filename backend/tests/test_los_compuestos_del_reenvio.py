"""**Lo compuesto tambien se compara: las lineas, las horas y los insumos** (18/10/2026).

### ***El hueco que esto cierra***

*`reenvios.la_misma_accion` recorria los campos de la peticion y **saltaba los que no eran columna**, con un
comentario que decia «de esas se ocupa la puerta». **La puerta no se ocupaba.***

*Y no son campos de adorno: el plan guarda sus **lineas** en otra tabla -`LineaDeTrabajoPrevisto`-, y la labor
guarda sus **insumos** como **salidas de almacen**. Asi que un reintento con **otras** lineas u **otros** insumos
devolvia la fila que ya habia **como si fuera lo que se acaba de mandar** -y las filas hijas se quedaban con los
datos de la **primera** vez-.*

***Eso es una perdida silenciosa***, la misma que el 409 existe para impedir. *Y la revision lo pide con estas
palabras: **«cada puerta debe acreditar los datos compuestos que el ayudante no compara»**.*

### ***Y las horas, que se guardan con otro nombre***

*`horas` en la peticion es `horas_previstas` en la fila. Sin `traducir`, el campo **no se encontraba** y se
saltaba -o sea, cambiar las horas de un plan y reintentar no daba conflicto-.*
"""

from __future__ import annotations


def un_plan(cliente, cuenta, campana, parcela, **cambios) -> dict:
    lo_que_va = {
        "campana_id": campana["id"],
        "tipo": "laboreo",
        "fecha_prevista": "2026-11-10",
        "parcela_id": parcela["id"],
        "horas": 3,
        "lineas": [{"parcela_id": parcela["id"], "superficie_ha": "2.50", "horas": "3"}],
        "clave_de_reenvio": "plan-compuesto",
        **cambios,
    }
    return cliente.post("/api/trabajos/previstos", headers=cuenta["cabeceras"], json=lo_que_va)


def test_el_plan_con_las_MISMAS_lineas_no_se_apunta_dos_veces(cliente, cuenta, campana, crear_parcela):
    """*Un reintento legitimo, con **las mismas lineas**, devuelve el mismo plan.*"""
    parcela = crear_parcela(alias="La del plan compuesto")

    primera = un_plan(cliente, cuenta, campana, parcela)
    assert primera.status_code == 201, primera.text
    repetida = un_plan(cliente, cuenta, campana, parcela)

    assert repetida.status_code in (200, 201), repetida.text
    assert repetida.json()["previsto"]["id"] == primera.json()["previsto"]["id"], (
        "***el mismo reenvio devuelve el mismo plan***"
    )


def test_y_con_OTRA_linea_es_un_conflicto(cliente, cuenta, campana, crear_parcela):
    """***Y con otra linea, 409.***

    *Es el caso que se perdia en silencio: la puerta habia creado las lineas de la **primera** vez, y el reintento
    con otras devolvia el plan viejo como si se hubieran guardado.*
    """
    parcela = crear_parcela(alias="La de la otra linea")
    primera = un_plan(cliente, cuenta, campana, parcela)
    assert primera.status_code == 201, primera.text

    otra = un_plan(
        cliente, cuenta, campana, parcela,
        lineas=[{"parcela_id": parcela["id"], "superficie_ha": "9.99", "horas": "3"}],
    )

    assert otra.status_code == 409, (
        f"***las lineas son parte de la accion: cambiarlas NO puede devolver el plan viejo***: {otra.text}"
    )


def test_y_con_OTRAS_horas_es_un_conflicto(cliente, cuenta, campana, crear_parcela):
    """***`horas` se guarda como `horas_previstas`***: *sin la traduccion, cambiar las horas no daba conflicto.*"""
    parcela = crear_parcela(alias="La de las horas")
    assert un_plan(cliente, cuenta, campana, parcela).status_code == 201

    otra = un_plan(cliente, cuenta, campana, parcela, horas=40)

    assert otra.status_code == 409, (
        f"***las horas previstas son parte de la accion***: {otra.text}"
    )


def test_una_labor_cuyos_insumos_NO_se_escriben_no_da_conflicto(cliente, cuenta, campana, crear_parcela):
    """***Y el camino de los insumos que la puerta se salta.***

    *Un insumo **sin envase** no se saca del almacen -la puerta lo dice en un aviso y no toca nada-. Compararlo
    seria pedirle a la base algo que nunca se le mando, asi que **la comparacion los salta igual**: un reintento
    asi devuelve la misma labor, y **no hay nada escrito que pueda haber cambiado**.*
    """
    parcela = crear_parcela(alias="La de los insumos sueltos")
    lo_que_va = {
        "campana_id": campana["id"],
        "tipo": "laboreo",
        "fecha": "2026-11-11",
        "parcela_id": parcela["id"],
        # *Sin `lote_id`: la puerta no lo escribe.*
        "insumos": [{"cantidad": "5", "unidad": "kg"}],
        "clave_de_reenvio": "labor-sin-envase",
    }

    primera = cliente.post("/api/trabajos", headers=cuenta["cabeceras"], json=lo_que_va)
    assert primera.status_code == 201, primera.text
    repetida = cliente.post("/api/trabajos", headers=cuenta["cabeceras"], json=lo_que_va)

    assert repetida.status_code in (200, 201), (
        f"***un insumo que no se escribe no puede dar conflicto***: {repetida.text}"
    )
    assert repetida.json()["hecho"]["id"] == primera.json()["hecho"]["id"], repetida.json()
