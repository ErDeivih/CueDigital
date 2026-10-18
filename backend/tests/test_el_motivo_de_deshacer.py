"""**El motivo de deshacer una conciliacion** (17/10/2026).

***Lo que habia***: el docstring de `deshacer_la_conciliacion` prometia *«con la fecha, quien lo deshizo **y
el motivo**»*, y el motivo era **un texto fijo**: `textos.mensaje("T20_deshacer_a_mano")` -«Se deshizo a
mano»-. *El agricultor **no podia decir el suyo**, y dentro de seis meses el unico que sabe por que se
deshizo ese vinculo es ese campo.*

***Y aqui importa mas que en otros sitios***: deshacer una conciliacion **toca dinero** -suelta el vinculo
entre un movimiento del banco y una factura-.

***Lo que se cambio***: `ConciliacionEntrada` gana un `motivo`, y la puerta guarda **el que le manden**. *El
texto de siempre se queda como red: la puerta no se rompe por no mandar motivo.*
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app import textos
from app.routers import extractos_api


# ---------------------------------------------------------------------------
# 1 · El esquema: el motivo entra
# ---------------------------------------------------------------------------


def test_la_entrada_de_deshacer_admite_el_motivo():
    """***El campo que faltaba.***

    *Antes solo tenia `imputaciones`, asi que **no habia forma de decir por que** -aunque el docstring lo
    prometia-.*
    """
    entrada = extractos_api.ConciliacionEntrada(motivo="Me he equivocado de factura")

    assert entrada.motivo == "Me he equivocado de factura"
    assert entrada.imputaciones == []


def test_y_sigue_siendo_opcional():
    """***La puerta no se rompe por no mandar motivo.***

    *Hay clientes -y pantallas- que deshacen sin decir nada, y tienen que seguir funcionando: lo que cambia es
    que **ahora se puede** decir, no que sea obligatorio.*
    """
    entrada = extractos_api.ConciliacionEntrada()
    assert entrada.motivo is None


def test_un_motivo_largo_se_rechaza():
    """***Y con su tope***, que es el ancho que ya tiene la columna.

    *Un motivo de mil letras no cabe en el rastro, y es mejor que lo diga la puerta a que lo corte la base.*
    """
    with pytest.raises(ValidationError):
        extractos_api.ConciliacionEntrada(motivo="x" * 400)


# ---------------------------------------------------------------------------
# 2 · ***Y la red: el texto de siempre sigue ahi***
# ---------------------------------------------------------------------------


def test_el_texto_de_siempre_sigue_existiendo():
    """***Y se comprueba, porque es lo que hace que el cambio no rompa nada.***

    *La puerta escribe `(datos.motivo or "").strip() or textos.mensaje("T20_deshacer_a_mano")`: si el motivo
    desapareciera de `textos`, **la propia puerta reventaria al deshacer sin motivo** -y eso es peor que no
    tener motivo-.*
    """
    assert textos.mensaje("T20_deshacer_a_mano"), "***la red tiene que seguir ahi***"


# ---------------------------------------------------------------------------
# 3 · Y la docena de cosas que NO se han tocado
# ---------------------------------------------------------------------------


def test_no_se_ha_tocado_lo_que_protege_el_dinero():
    """***Lo que este cambio NO hace***, dicho para que nadie lo confunda al leerlo:

      - **no borra ninguna conciliacion**: sigue marcandose `anulada`, con su fecha y su autor
      - **no toca el movimiento del banco**: la regla del contrato sigue igual
      - **no cambia lo que vuelve a quedar pendiente**

    *El cambio es **un campo mas en un sitio**, y nada mas.*
    """
    import inspect

    fuente = inspect.getsource(extractos_api.deshacer_la_conciliacion)
    assert "fila.anulada = True" in fuente, "***se sigue marcando, no se borra***"
    assert "fila.deshecha_en = ahora" in fuente, "***con su fecha***"
    assert "fila.deshecha_por_usuario_id = usuario.id" in fuente, "***y su autor***"
    assert "motivo_del_deshacer" in fuente, "***y (ahora si) su motivo***"
