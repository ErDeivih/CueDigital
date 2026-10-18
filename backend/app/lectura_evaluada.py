"""**Lo que se puede decir de una lectura sin corpus: por campo, y con dos duplicados** (CRM-12, 17/10/2026).

El contrato de la cola lo pide asi:

    ***Medir precision por campo y documento, correcciones necesarias y fallos criticos; una confianza
    global no basta.*** Documento sintetico util para pruebas funcionales, no evaluacion representativa real.
    ***No confirmar compras/pagos ni autorizacion fitosanitaria a partir del OCR sin revision.***
    ***Duplicado de fichero por huella distinto de duplicado comercial.***
    Aceptacion: error de lectura conserva original y formulario; ***dato no leido vacio***; …

***Y aqui esta lo que este modulo defiende***: **una lectura no se aprueba en conjunto**. *«Leido
correctamente» no es un dato: es un resumen que tapa justo lo que hay que mirar.* Lo que sirve es **campo a
campo** -el NIF salio bien, el total salio mal-, y eso se puede medir **sin tener el corpus delante**.

***Y las dos mitades del modulo son las dos frases del contrato***: la precision por campo, y los dos
duplicados que **no son el mismo**.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# ***La precision, POR CAMPO***
# ---------------------------------------------------------------------------
#
# ***Por que no basta una confianza global***: un papel con el NIF bien y el total mal sale «leido» al 80% de
# campos, y ese 80% **no dice cual esta mal**. *Y cual esta mal es lo unico que importa: el NIF mal te hace
# pagar a quien no es; el total mal, pagar de mas.*
#
# ***Y la casa ya lo tenia decidido***: `bandeja.py` dice, con estas palabras, que **no** da porcentajes ni
# «leido correctamente» ni confianza. Esto no lo contradice: lo **mide por dentro**, para saber donde falla.

# ***Los campos que tienen consecuencia***: si uno de estos sale mal y nadie lo mira, pasa algo. *Los demas
# -unas notas, una descripcion- se corrigen sin mas.*
CAMPOS_CRITICOS = (
    "proveedor_nif",
    "numero_factura",
    "fecha",
    "base_imponible",
    "cuota_iva",
    "total",
)


def lo_leido_por_campo(*, leido: dict, de_verdad: dict) -> dict:
    """***Campo a campo: que salio bien, que salio mal y que no se leyo.***

    ***Y las tres cosas se cuentan por separado***, porque son distintas:

      - **acertados**: coinciden
      - **fallados**: hay un valor, y **no** coincide -*lo peligroso: parece un dato*-
      - **sin leer**: el lector devolvio vacio -*molesto, pero honesto: se ve que falta*-

    *Un campo sin leer es mejor que uno mal leido, y por eso no se cuentan juntos.*
    """
    acertados, fallados, sin_leer = [], [], []
    for campo, esperado in de_verdad.items():
        suyo = leido.get(campo)
        # ***Un campo vacio no es un cero, ni una cadena vacia un valor***: no se ha leido.
        if suyo is None or (isinstance(suyo, str) and not suyo.strip()):
            sin_leer.append(campo)
        elif _el_mismo_valor(suyo, esperado):
            acertados.append(campo)
        else:
            fallados.append(campo)

    criticos_fallados = [c for c in fallados if c in CAMPOS_CRITICOS]
    criticos_sin_leer = [c for c in sin_leer if c in CAMPOS_CRITICOS]
    return {
        "acertados": acertados,
        "fallados": fallados,
        "sin_leer": sin_leer,
        # ***Los que tienen consecuencia, aparte***: *es lo que hay que mirar antes de dar nada por bueno.*
        "criticos_fallados": criticos_fallados,
        "criticos_sin_leer": criticos_sin_leer,
        "se_puede_dar_por_bueno": not criticos_fallados,
    }


def _el_mismo_valor(uno, otro) -> bool:
    """***Comparar como se compara un numero de una factura***: sin ceros de mas y sin mayusculas de mas.

    *`170.0` y `"170,00"` son el mismo importe, y `"F37012345"` y `"f37012345"` el mismo NIF. Darlo por mal
    leido seria un fallo del medidor, no del lector.*
    """
    if uno is None or otro is None:
        return uno == otro
    try:
        return abs(float(str(uno).replace(",", ".")) - float(str(otro).replace(",", "."))) < 0.005
    except (TypeError, ValueError):
        return str(uno).strip().casefold() == str(otro).strip().casefold()


def la_precision_de_un_documento(campos: dict) -> dict:
    """***El resumen del documento, dicho sin tapar nada.***

    ***Y no devuelve un «porcentaje de acierto»***: devuelve **cuantos de cada**, y **si se puede dar por
    bueno**. *Un 80% suena bien y puede ser un desastre: depende de **cual** sea el 20%.*
    """
    acertados = len(campos.get("acertados") or [])
    fallados = len(campos.get("fallados") or [])
    sin_leer = len(campos.get("sin_leer") or [])
    total = acertados + fallados + sin_leer
    return {
        "campos": total,
        "acertados": acertados,
        "fallados": fallados,
        "sin_leer": sin_leer,
        # ***Cero fallos criticos es lo unico que aprueba***: *los no criticos se corrigen, los criticos
        # hacen daño.*
        "se_puede_dar_por_bueno": bool(campos.get("se_puede_dar_por_bueno")),
        "hay_que_revisar": bool(campos.get("criticos_fallados")) or bool(campos.get("criticos_sin_leer")),
    }


# ---------------------------------------------------------------------------
# ***Los DOS duplicados, que no son el mismo***
# ---------------------------------------------------------------------------


def es_el_mismo_fichero(*, huella_una: str, huella_otra: str) -> bool:
    """***Duplicado DE FICHERO***: la misma foto, el mismo PDF. *La huella es lo que se subio.*

    *Es el que evita que alguien suba dos veces la misma foto por pinchar dos veces.* **No dice nada de si la
    compra es la misma.**
    """
    return bool(huella_una) and huella_una == huella_otra


def es_el_mismo_papel(*, una: dict, otra: dict) -> bool:
    """***Duplicado COMERCIAL***: **el mismo papel con otro fichero**. *Mismo proveedor, mismo numero.*

    ***Y por que son dos cosas distintas*** -lo dice el contrato-: *una factura se puede fotografiar dos veces
    -huellas distintas, **mismo papel**-, y dos fotos distintas pueden ser dos facturas del mismo proveedor el
    mismo dia -misma pinta, **papeles distintos**-. Confundirlos lleva a lo contrario en cada caso: **no
    apuntar la compra dos veces** por un lado, y **no perder la segunda** por el otro.*

    ***Y sin NIF o sin numero no se puede afirmar***: *se devuelve falso, que es lo honesto. «No lo se» no es
    «es el mismo».*
    """
    nif_una, nif_otra = _el_texto(una.get("proveedor_nif")), _el_texto(otra.get("proveedor_nif"))
    num_una, num_otra = _el_texto(una.get("numero_factura")), _el_texto(otra.get("numero_factura"))
    if not nif_una or not nif_otra or not num_una or not num_otra:
        return False
    return nif_una == nif_otra and num_una == num_otra


def _el_texto(valor) -> str:
    return str(valor or "").strip().casefold()


# ---------------------------------------------------------------------------
# ***Y lo que NO se hace con una lectura***
# ---------------------------------------------------------------------------


def se_puede_confirmar_solo(*, campos: dict) -> bool:
    """***Una lectura no confirma nada sola.*** El contrato: *«no confirmar compras/pagos ni autorizacion
    fitosanitaria a partir del OCR sin revision»*.

    ***Devuelve siempre `False`, y es a proposito***: *por muy bien que haya salido la lectura, alguien tiene
    que mirarla. Una funcion que devolviera `True` cuando la precision es alta seria la puerta por la que se
    cuela una compra que nadie ha visto.*
    """
    return False


def lo_no_leido_va_vacio(leido: dict) -> dict:
    """***«Dato no leido vacio»***, la aceptacion del contrato.

    ***Y no es un detalle de estilo***: *rellenar un campo que no se ha leido con un cero -o con lo que
    «suele» valer- es inventarse un dato y meterlo en una factura. **El hueco se ve; el cero, no.***
    """
    limpio = {}
    for campo, valor in leido.items():
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            limpio[campo] = None
        else:
            limpio[campo] = valor
    return limpio
