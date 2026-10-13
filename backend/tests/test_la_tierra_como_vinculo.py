"""La tierra como clase de vinculo: un papel se puede enlazar con un trozo del mapa (CRM-06, 14/10/2026).

**Por que existe.** El contrato del ticket pide, para la ficha de una tierra: *«resumen, historia, cultivos,
trabajos, economia, **documentos** y PAC»*. Y los documentos **no se podian enlazar con una tierra**: habia seis
clases de vinculo (`compra`, `gasto`, `venta`, `maquina`, `trabajo`, `inspeccion`) y ninguna era la tierra.

**Lo que se prueba aqui** es lo que el contrato de la casa prohibe romper: que las seis de siempre sigan estando,
que la nueva entre, que apunte al modelo correcto y que **no abra la puerta a la tierra de otra finca** — que es
lo unico que la base no puede comprobar sola, porque `clase`/`entidad_id` **no son una clave ajena a proposito**.
"""

from __future__ import annotations

from app import bandeja, models
from app.routers import bandeja_api

LAS_SEIS_DE_SIEMPRE = ("compra", "gasto", "venta", "maquina", "trabajo", "inspeccion")


def test_las_seis_de_siempre_siguen_estando():
    # **Lo que el contrato prohibe romper**: los papeles que el agricultor ya tiene enlazados apuntan a estas
    # seis, y si alguna desapareciera se quedarian con una clase que no existe.
    for clase in LAS_SEIS_DE_SIEMPRE:
        assert clase in bandeja.CLASES_DE_VINCULO, f"la clase «{clase}» se ha perdido"


def test_la_tierra_es_una_clase_de_vinculo():
    assert bandeja.TIERRA == "tierra"
    assert bandeja.TIERRA in bandeja.CLASES_DE_VINCULO
    # Y la puerta que dice si una clase vale tiene que aceptarla.
    assert bandeja.es_una_clase_de_vinculo(bandeja.TIERRA)
    assert not bandeja.es_una_clase_de_vinculo("lo_que_sea")


def test_la_tierra_apunta_a_una_parcela_y_no_a_otra_cosa():
    # El diccionario clase -> modelo es lo que hace que el router pueda COMPROBAR que la entidad es de esta
    # finca. Si apuntara a otro modelo, la comprobacion miraria la tabla equivocada.
    assert bandeja_api._el_modelo_de_la_clase(bandeja.TIERRA) is models.Parcela


def test_ninguna_clase_se_repite():
    assert len(bandeja.CLASES_DE_VINCULO) == len(set(bandeja.CLASES_DE_VINCULO)), bandeja.CLASES_DE_VINCULO
