"""El aviso de solape entre las tierras de un grupo (CRM-06, 14/10/2026).

**Por que existe.** `superficie_contada_del_grupo` suma las hectareas de las tierras de un grupo y **no mira si
sus formas se pisan**: dos tierras solapadas cuentan **dos veces** la parte comun, y el total *«parece bueno y no
lo es»*. El contrato lo pide con estas palabras: *«formas solapadas no duplican superficie unica **sin
advertencia**»*.

**Y no corrige nada**, a proposito: el propio `geo.se_solapan` lo decidio — *«se avisa para que se mire, y no se
corrige nada… el contrato pide detectar solapes y decirlo, no arreglarlos por su cuenta»*.

Es una funcion **pura** —un grupo, ninguna base de datos— asi que se prueba con tierras de mentira.
"""

from __future__ import annotations

from app.servicios import solapes_del_grupo

# Dos cuadrados que se pisan de verdad (el segundo empieza dentro del primero), en WGS84.
UNO = "POLYGON((-4.7000 41.6000, -4.6900 41.6000, -4.6900 41.6100, -4.7000 41.6100, -4.7000 41.6000))"
PISADO = "POLYGON((-4.6995 41.6005, -4.6895 41.6005, -4.6895 41.6105, -4.6995 41.6105, -4.6995 41.6005))"
LEJOS = "POLYGON((-4.5000 41.4000, -4.4900 41.4000, -4.4900 41.4100, -4.5000 41.4100, -4.5000 41.4000))"


class UnaTierra:
    def __init__(self, id_: int, geometria: str | None) -> None:
        self.id = id_
        self.geometria = geometria


class UnGrupo:
    def __init__(self, *parcelas) -> None:
        self.parcelas = list(parcelas)


def test_dos_tierras_que_se_pisan_avisan_y_dicen_como(cliente=None):
    avisos = solapes_del_grupo(UnGrupo(UnaTierra(1, UNO), UnaTierra(2, PISADO)))
    assert len(avisos) == 1, f"una pareja que se pisa, un aviso: {avisos}"
    assert {avisos[0]["una"], avisos[0]["otra"]} == {1, 2}, avisos
    assert avisos[0]["como"] == "si", avisos
    # **Y se dice que significa**, porque «si» solo no explica nada a quien lo lee.
    assert avisos[0]["que_significa"], avisos


def test_dos_tierras_separadas_no_avisan_nada():
    # `no` no es un aviso: es que estan bien. Devolverlo tambien escondería el aviso entre lo que no lo es.
    assert solapes_del_grupo(UnGrupo(UnaTierra(1, UNO), UnaTierra(2, LEJOS))) == []


def test_una_tierra_sin_forma_tampoco_es_un_aviso_de_solape():
    # `no_se` es que falta la forma, y de eso ya se encarga la regla de A7: aqui no se inventa un solape.
    assert solapes_del_grupo(UnGrupo(UnaTierra(1, UNO), UnaTierra(2, None))) == []


def test_con_tres_tierras_solo_avisa_la_pareja_que_se_pisa():
    avisos = solapes_del_grupo(UnGrupo(UnaTierra(1, UNO), UnaTierra(2, PISADO), UnaTierra(3, LEJOS)))
    assert len(avisos) == 1, f"solo la pareja que se pisa: {avisos}"
    assert {avisos[0]["una"], avisos[0]["otra"]} == {1, 2}, avisos


def test_un_grupo_sin_tierras_no_avisa_nada():
    # El caso vacio: no puede reventar ni inventarse una pareja.
    assert solapes_del_grupo(UnGrupo()) == []
    assert solapes_del_grupo(None) == []
