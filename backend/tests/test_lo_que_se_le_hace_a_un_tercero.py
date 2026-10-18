"""**El trabajo que se le hace a un tercero** (CRM-04, 17/10/2026).

***Este fichero de pruebas no existia porque el modulo no existia.*** La tabla `trabajos_para_terceros` esta
desde el 14/10 -con su clave de reenvio y su indice unico-, y **no habia ni una linea de logica que la
usara**. *La mitad de una funcionalidad es la clase de cosa que parece hecha desde fuera.*

El contrato del CRM-04, con sus palabras:

    Trabajo externo con ubicacion y superficie ***separadas*** de tierras/PAC propias.
    ***Insumo del cliente no descuenta almacen propio; insumo propio si.***
    Maquina, horas, operario, ***desplazamiento y coste conocido por separado***.
    ***Cambiar tarifa no reescribe partes aceptados.***
    Aceptacion: ***trabajo externo 10 ha no suma superficie propia***; 2 L propios consumen; 2 L del…
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import servicios_a_terceros as s


# ---------------------------------------------------------------------------
# 1 · ***«Trabajo externo 10 ha no suma superficie propia»***
# ---------------------------------------------------------------------------


def test_diez_hectareas_de_un_tercero_no_suman_superficie_propia():
    """***El caso de aceptacion del contrato, tal cual.***

    *Y por eso la ubicacion y la superficie viven en su tabla y no en `parcelas`: si estuvieran alli,
    cualquier suma de superficie del agricultor -y el volcado de la PAC- **contaria tierras que no son
    suyas**.*
    """
    suya = s.la_superficie_del_tercero(10.0)

    assert suya["superficie_ha"] == 10.0, "***el trabajo existe y se ve***"
    assert suya["suma_a_lo_propio"] is False, "***y NO se suma a la superficie de casa***"
    assert suya["magnitud"] == "lo_de_un_tercero", "***y lleva su magnitud, para que no se sume por descuido***"
    assert suya["motivo"], "***y el porque, dentro del dato***"


def test_la_comprobacion_usa_la_regla_de_siempre_no_una_segunda():
    """***Una sola regla en todo el programa.***

    *Dos reglas que tienen que coincidir acaban no coincidiendo. Aqui se llama a la de `superficies`, no se
    escribe otra.*
    """
    assert s.se_puede_sumar_a_lo_propio(magnitud="lo_de_un_tercero") is False
    assert s.se_puede_sumar_a_lo_propio(magnitud="lo_que_se_cultiva") is True


# ---------------------------------------------------------------------------
# 2 · ***«Insumo del cliente no descuenta almacen propio; el propio si»***
# ---------------------------------------------------------------------------


def test_el_insumo_del_cliente_no_descuenta_el_almacen_de_casa():
    """***El caso que el contrato escribe con mas detalle***: *«2 L propios consumen; 2 L del cliente no»*.

    *El insumo del cliente no ha estado nunca en el almacen del agricultor, asi que descontarlo seria
    inventarse una salida.*
    """
    del_cliente = s.de_quien_es_el_insumo(s.DEL_CLIENTE)
    propio = s.de_quien_es_el_insumo(s.PROPIO)

    assert del_cliente["descuenta_el_almacen_propio"] is False
    assert propio["descuenta_el_almacen_propio"] is True
    assert del_cliente["motivo"] and propio["motivo"], "***y el porque, en los dos***"


def test_un_insumo_que_no_es_de_nadie_se_para():
    with pytest.raises(ValueError):
        s.de_quien_es_el_insumo("de_nadie")


# ---------------------------------------------------------------------------
# 3 · ***«Cambiar tarifa no reescribe partes aceptados»***
# ---------------------------------------------------------------------------


def UN_TRABAJO(**cambios):
    cuerpo = {"estado": s.PROPUESTO, "tarifa_por_hora": 30.0, "titulo": "Labrar al vecino"}
    cuerpo.update(cambios)
    return cuerpo


def test_aceptar_copia_la_tarifa_y_a_partir_de_ahi_es_del_parte():
    """***«El precio de un trabajo aceptado es el que se acepto, no el que la casa tenga hoy en la lista.»***

    *Por eso el parte lleva la tarifa, las horas, la maquina, el operario y el desplazamiento **copiados**:
    son las condiciones con las que se acepto.*
    """
    aceptado = s.aceptar(trabajo=UN_TRABAJO(), tarifa=35.0, quien=7, cuando=dt.date(2026, 5, 1))

    assert aceptado["estado"] == s.ACEPTADO
    assert aceptado["tarifa_aceptada"] == 35.0, "***la tarifa se COPIA, no se referencia***"
    assert aceptado["aceptado_por"] == 7
    assert aceptado["aceptado_en"] == dt.date(2026, 5, 1)


def test_cambiar_la_tarifa_de_la_casa_no_toca_un_parte_aceptado():
    """***Y no lanza un error***: *cambiar la tarifa es legitimo; lo que no puede es **reescribir hacia
    atras**.*

    *Un error aqui obligaria a no poder cambiar la tarifa mientras haya un parte abierto, que es peor.*
    """
    aceptado = s.aceptar(trabajo=UN_TRABAJO(), tarifa=35.0, quien=7, cuando=dt.date(2026, 5, 1))
    despues = s.cambiar_la_tarifa_de_la_casa(trabajo=aceptado, tarifa_nueva=50.0)

    assert despues["tarifa_aceptada"] == 35.0, "***el parte sigue con la suya***"
    assert despues["no_se_toca"], "***y se dice que no se ha tocado***"


def test_pero_uno_que_solo_se_propuso_si_se_puede_cambiar():
    """*Antes de aceptar, la tarifa es una propuesta: se cambia sin romper nada.*"""
    propuesto = s.cambiar_la_tarifa_de_la_casa(trabajo=UN_TRABAJO(), tarifa_nueva=50.0)
    assert propuesto["tarifa_por_hora"] == 50.0
    assert propuesto["no_se_toca"] is None


def test_aceptar_dos_veces_no_es_aceptar_es_reescribir():
    """***Y por eso no se puede***: *aceptar dos veces lo mismo reescribiria lo que ya se acepto, que es justo
    lo que la regla prohibe.*
    """
    aceptado = s.aceptar(trabajo=UN_TRABAJO(), tarifa=35.0, quien=7, cuando=dt.date(2026, 5, 1))
    with pytest.raises(s.NoSePuedePasar):
        s.aceptar(trabajo=aceptado, tarifa=99.0, quien=8, cuando=dt.date(2026, 6, 1))


# ---------------------------------------------------------------------------
# 4 · ***El recorrido, y lo que no se deshace***
# ---------------------------------------------------------------------------


def test_el_recorrido_es_el_del_modelo_y_no_hay_mas():
    """*Propuesto -> aceptado -> hecho, y cancelado. **Lo que se propone no es un trabajo, y lo aceptado no es
    lo hecho.***
    """
    assert s.se_puede_pasar_a(desde=s.PROPUESTO, hasta=s.ACEPTADO)
    assert s.se_puede_pasar_a(desde=s.ACEPTADO, hasta=s.HECHO)
    assert s.se_puede_pasar_a(desde=s.ACEPTADO, hasta=s.CANCELADO)


def test_lo_hecho_no_se_deshace_y_lo_cancelado_no_vuelve():
    """***Y no se «arregla» pasando por en medio***: *un trabajo cancelado que se convierte en hecho sin pasar
    por aceptado seria un parte que nadie acepto.*

    *Lo hecho se corrige -y queda el rastro-; lo cancelado, se hace otro.*
    """
    assert s.se_puede_pasar_a(desde=s.HECHO, hasta=s.PROPUESTO) is False
    assert s.se_puede_pasar_a(desde=s.CANCELADO, hasta=s.ACEPTADO) is False

    with pytest.raises(s.NoSePuedePasar) as fallo:
        s.el_paso(desde=s.HECHO, hasta=s.CANCELADO)
    assert "no se sale" in str(fallo.value), str(fallo.value)


# ---------------------------------------------------------------------------
# 5 · ***«El margen marca los costes desconocidos»***
# ---------------------------------------------------------------------------


def test_sin_coste_conocido_no_hay_margen_que_dar():
    """***«En vez de contar un cero.»***

    *Es la misma regla del contador y de los paneles: **un cero y un «no lo se» son cosas distintas**. Un
    margen calculado con un cero que no era cero **sale mejor de lo que es** -y ese es el error que hace tomar
    decisiones malas-.*
    """
    suyo = s.lo_que_se_sabe_del_margen(cobrado=500.0, coste_conocido=None)

    assert suyo["margen"] is None, "***no hay margen que dar***"
    assert suyo["hay_costes_que_no_constan"] is True
    assert suyo["aviso"], "***y se dice***"


def test_con_el_coste_conocido_el_margen_sale():
    suyo = s.lo_que_se_sabe_del_margen(cobrado=500.0, coste_conocido=300.0)
    assert suyo["margen"] == 200.0
    assert suyo["aviso"] is None


# ---------------------------------------------------------------------------
# 6 · ***«Desplazamiento y coste conocido por separado»***
# ---------------------------------------------------------------------------


def test_la_mano_de_obra_y_el_viaje_van_por_separado():
    """***El contrato lo pide con esas palabras***: *«maquina, horas, operario, **desplazamiento y coste
    conocido por separado**».*

    *Juntarlos en un numero hace imposible saber si el trabajo salio caro por las horas o por el viaje.*
    """
    suyo = s.lo_que_cuesta_el_trabajo(tarifa=30.0, horas=4.0, desplazamiento_km=40.0, precio_del_km=0.5)

    assert suyo["mano_de_obra"] == 120.0, "***las horas, por su lado***"
    assert suyo["desplazamiento"] == 20.0, "***y el viaje, por el suyo***"
    assert suyo["coste"] == 140.0
    assert suyo["hay_costes_que_no_constan"] is False


def test_sin_saber_el_viaje_el_coste_no_se_sabe():
    """*Y entonces se dice: **el viaje puede no saberse, y el total tampoco**.*"""
    suyo = s.lo_que_cuesta_el_trabajo(tarifa=30.0, horas=4.0, desplazamiento_km=40.0)

    assert suyo["mano_de_obra"] == 120.0, "***lo que si se sabe, se da***"
    assert suyo["desplazamiento"] is None
    assert suyo["coste"] is None, "***y el total no se inventa***"
    assert suyo["hay_costes_que_no_constan"] is True


def test_sin_tarifa_o_sin_horas_no_hay_nada_que_contar():
    suyo = s.lo_que_cuesta_el_trabajo(tarifa=None, horas=4.0)
    assert suyo["coste"] is None
    assert suyo["hay_costes_que_no_constan"] is True
