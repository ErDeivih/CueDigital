"""**Lo que se puede decir de una lectura sin corpus** (CRM-12, 17/10/2026).

El contrato de la cola, con sus palabras:

    ***Medir precision por campo y documento… una confianza global no basta.***
    ***No confirmar compras/pagos ni autorizacion fitosanitaria a partir del OCR sin revision.***
    ***Duplicado de fichero por huella distinto de duplicado comercial.***
    Aceptacion: error de lectura conserva original y formulario; ***dato no leido vacio***.
"""

from __future__ import annotations

from app import lectura_evaluada as le

DE_VERDAD = {
    "proveedor_nif": "F37012345",
    "numero_factura": "2026/00123",
    "fecha": "2026-03-15",
    "base_imponible": 170.0,
    "total": 205.70,
}


# ---------------------------------------------------------------------------
# 1 · ***Campo a campo, que es lo que el contrato pide***
# ---------------------------------------------------------------------------


def test_un_campo_sin_leer_y_uno_mal_leido_no_se_cuentan_juntos():
    """***Son cosas distintas, y de distinto peligro.***

    *Un campo **sin leer** es molesto pero **honesto**: se ve que falta. Uno **mal leido** parece un dato, y
    se cuela. Por eso se cuentan por separado -y el contrato pide justo eso: «dato no leido vacio».*
    """
    campos = le.lo_leido_por_campo(
        leido={"proveedor_nif": "F37012345", "numero_factura": "2026/999", "total": None, "fecha": "", "base_imponible": 170.0},
        de_verdad=DE_VERDAD,
    )

    assert campos["acertados"] == ["proveedor_nif", "base_imponible"]
    assert campos["fallados"] == ["numero_factura"], "***un numero distinto es un fallo, no un hueco***"
    assert sorted(campos["sin_leer"]) == ["fecha", "total"], (
        f"***vacio es «sin leer», no «cero»: {campos['sin_leer']}***"
    )


def test_los_campos_criticos_van_aparte():
    """***Un 80% de acierto puede ser un desastre***: *depende de **cual** sea el 20%.*

    El NIF mal te hace pagar a quien no es; las notas mal, se corrigen sin mas.
    """
    campos = le.lo_leido_por_campo(
        leido={"proveedor_nif": "F37012345", "numero_factura": "2026/00123", "total": 999.0},
        de_verdad=DE_VERDAD,
    )
    assert campos["fallados"] == ["total"]
    assert campos["criticos_fallados"] == ["total"], "***el total es de los que hacen daño***"


def test_comparar_como_se_compara_un_numero_de_una_factura():
    """*`170.0` y `"170,00"` son el mismo importe, y `"F37012345"` y `"f37012345"` el mismo NIF.*

    *Darlos por mal leidos seria un fallo del medidor, no del lector.*
    """
    campos = le.lo_leido_por_campo(
        leido={"proveedor_nif": "f37012345", "base_imponible": "170,00"},
        de_verdad={"proveedor_nif": "F37012345", "base_imponible": 170.0},
    )
    assert campos["fallados"] == [], f"***no son fallos: {campos['fallados']}***"


def test_con_un_critico_mal_leido_no_se_puede_dar_por_bueno():
    """***Y es la pregunta que se hace de verdad***: *¿se puede seguir, o hay que mirarlo?*"""
    malo = le.lo_leido_por_campo(leido={"total": 1.0}, de_verdad=DE_VERDAD)
    assert malo["se_puede_dar_por_bueno"] is False

    bueno = le.lo_leido_por_campo(leido=dict(DE_VERDAD), de_verdad=DE_VERDAD)
    assert bueno["se_puede_dar_por_bueno"] is True, "***con todo bien, si se puede***"


def test_el_resumen_del_documento_no_esconde_un_porcentaje():
    """***No devuelve «un 80% de acierto»***: devuelve **cuantos de cada**, y si hay que revisar.

    *Un porcentaje unico tapa justo lo que hay que mirar.*
    """
    campos = le.lo_leido_por_campo(
        leido={"proveedor_nif": "F37012345", "numero_factura": "2026/00123", "total": 999.0},
        de_verdad=DE_VERDAD,
    )
    resumen = le.la_precision_de_un_documento(campos)

    assert "porcentaje" not in resumen, "***no hay un numero unico que lo resuma***"
    assert resumen["fallados"] == 1 and resumen["acertados"] == 2
    assert resumen["hay_que_revisar"] is True, "y se dice si hay que revisar"


# ---------------------------------------------------------------------------
# 2 · ***Los DOS duplicados, que no son el mismo***
# ---------------------------------------------------------------------------


def test_el_mismo_fichero_es_la_misma_huella():
    """*Dos veces la misma foto: **huellas iguales**. Es lo que evita subir dos veces lo mismo por pinchar dos
    veces.*"""
    assert le.es_el_mismo_fichero(huella_una="abc123", huella_otra="abc123")
    assert not le.es_el_mismo_fichero(huella_una="abc123", huella_otra="def456")
    assert not le.es_el_mismo_fichero(huella_una="", huella_otra=""), "sin huella no se afirma nada"


def test_el_mismo_papel_con_OTRO_fichero():
    """***El caso del contrato***: *«duplicado de fichero por huella **distinto** de duplicado comercial».*

    *La misma factura, fotografiada dos veces: **huellas distintas y el mismo papel**. Con solo la huella se
    apuntaria dos veces la misma compra.*
    """
    una = {"proveedor_nif": "F37012345", "numero_factura": "2026/00123"}
    otra = {"proveedor_nif": "f37012345", "numero_factura": "2026/00123"}

    assert not le.es_el_mismo_fichero(huella_una="foto-1", huella_otra="foto-2"), (
        "***son ficheros distintos***"
    )
    assert le.es_el_mismo_papel(una=una, otra=otra), "***y el mismo papel: se dice, y no se apunta dos veces***"


def test_y_al_reves_dos_papeles_distintos_con_la_misma_pinta():
    """*Dos facturas del mismo proveedor el mismo dia: **se parecen** y **no son la misma**.*

    *Confundirlas perderia la segunda.*
    """
    una = {"proveedor_nif": "F37012345", "numero_factura": "2026/00123"}
    otra = {"proveedor_nif": "F37012345", "numero_factura": "2026/00124"}
    assert not le.es_el_mismo_papel(una=una, otra=otra)


def test_sin_nif_o_sin_numero_no_se_puede_afirmar():
    """***«No lo se» no es «es el mismo».*** *Afirmar un duplicado sin los dos datos apuntaria de menos, que
    es tan malo como apuntar de mas.*"""
    assert not le.es_el_mismo_papel(
        una={"proveedor_nif": None, "numero_factura": "2026/00123"},
        otra={"proveedor_nif": "F37012345", "numero_factura": "2026/00123"},
    )
    assert not le.es_el_mismo_papel(
        una={"proveedor_nif": "F37012345", "numero_factura": ""},
        otra={"proveedor_nif": "F37012345", "numero_factura": "2026/00123"},
    )


# ---------------------------------------------------------------------------
# 3 · ***Lo que NO se hace con una lectura***
# ---------------------------------------------------------------------------


def test_una_lectura_no_confirma_nada_sola():
    """***La puerta que no se abre.*** *«No confirmar compras/pagos ni autorizacion fitosanitaria a partir del
    OCR sin revision.»*

    ***Devuelve `False` siempre, y con la lectura perfecta tambien***: *una funcion que devolviera `True` con
    buena precision seria la puerta por la que se cuela una compra que nadie ha visto.*
    """
    perfecta = le.lo_leido_por_campo(leido=dict(DE_VERDAD), de_verdad=DE_VERDAD)
    assert le.se_puede_confirmar_solo(campos=perfecta) is False, (
        "***ni con todo bien: alguien tiene que mirarlo***"
    )


def test_lo_no_leido_va_vacio_y_no_a_cero():
    """***«Dato no leido vacio»***, la aceptacion del contrato.

    *Rellenar un campo que no se ha leido con un cero -o con lo que «suele» valer- es inventarse un dato y
    meterlo en una factura. **El hueco se ve; el cero, no.***
    """
    limpio = le.lo_no_leido_va_vacio(
        {"total": None, "numero_factura": "   ", "base_imponible": 0.0, "proveedor": "COOP"}
    )

    assert limpio["total"] is None
    assert limpio["numero_factura"] is None, "***un espacio en blanco tampoco es un dato***"
    assert limpio["base_imponible"] == 0.0, "***y un cero de verdad se respeta: ese si se ha leido***"
    assert limpio["proveedor"] == "COOP"
