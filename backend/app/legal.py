"""Cálculos legales del cuaderno de campo.

Estas funciones son puras a propósito: son el núcleo normativo del programa y
tienen que poder probarse sin base de datos ni servidor. Si un cálculo de plazo
de seguridad o de unidades fertilizantes está mal, el cuaderno no vale nada, así
que van aparte y con tests propios.
"""

from __future__ import annotations

import datetime as dt

# Días que se consideran "próximo" a efectos de avisos al agricultor.
DIAS_AVISO_CARNE = 30
DIAS_AVISO_ITEAF = 60
DIAS_AVISO_PLAZO_SEGURIDAD = 7
# Una autorización excepcional es un permiso temporal para un producto que no está autorizado con
# carácter general. Se avisa con mes y medio, que es lo que se tarda en pedir otra o en buscar la
# alternativa.
DIAS_AVISO_AUTORIZACION = 45


def hoy() -> dt.date:
    return dt.date.today()


def fecha_fin_plazo_seguridad(fecha_aplicacion: dt.date, dias_plazo: int) -> dt.date:
    """Primer día en que se puede cosechar.

    El plazo de seguridad son los días que deben transcurrir DESDE la aplicación.
    Por eso se suma, no se resta: si se aplica el 1 de mayo con 21 días de plazo,
    se puede cosechar a partir del 22 de mayo.
    """
    if dias_plazo < 0:
        raise ValueError("Los días de espera no pueden ser negativos")
    return fecha_aplicacion + dt.timedelta(days=dias_plazo)


def dias_para_poder_cosechar(
    fecha_aplicacion: dt.date, dias_plazo: int, referencia: dt.date | None = None
) -> int:
    """Cuántos días faltan para poder cosechar. 0 o menos significa que ya se puede."""
    referencia = referencia or hoy()
    fin = fecha_fin_plazo_seguridad(fecha_aplicacion, dias_plazo)
    return (fin - referencia).days


def se_puede_cosechar(
    fecha_aplicacion: dt.date, dias_plazo: int, fecha_cosecha: dt.date
) -> bool:
    return fecha_cosecha >= fecha_fin_plazo_seguridad(fecha_aplicacion, dias_plazo)


def unidades_fertilizantes(kg_producto: float, riqueza_pct: float | None) -> float | None:
    """Kilogramos de nutriente puro.

    Es lo que mira la administración: los kilos de producto no dicen nada, porque
    un saco al 33,5 % y otro al 20 % no aportan lo mismo. Ejemplo: 300 kg de un
    abono 33,5 % aportan 100,5 kg de nitrógeno.

    **Si no se sabe la riqueza, no hay cuenta que hacer, y la respuesta es `None`** (A6 de
    `docs/T02_VALORES_POR_DEFECTO.md`). `riqueza_pct = None` significa «no consta la composición»,
    y eso no es un cero: multiplicar por cero daría 0 kg de nutriente, que en el documento que se
    firma se lee como «este abono no aporta nada de nitrógeno», y es mentira —lo que pasa es que
    nadie lo ha declarado—. Devolver `None` obliga a quien llama a decidir qué hacer con ese hueco,
    que es justo lo que no se puede saltar.
    """
    if riqueza_pct is None:
        return None
    return round(kg_producto * riqueza_pct / 100.0, 4)


def uf_por_hectarea(kg_ha_producto: float, riqueza_pct: float | None) -> float | None:
    """Las unidades fertilizantes por hectárea, o `None` si no se sabe la riqueza."""
    return unidades_fertilizantes(kg_ha_producto, riqueza_pct)


def cantidad_total(dosis: float, superficie_ha: float) -> float:
    """Cantidad de producto a emplear: dosis por hectárea × hectáreas."""
    return round(dosis * superficie_ha, 4)


def dosis_por_hectarea(
    cantidad_total: float | None, superficie_ha: float | None
) -> float | None:
    """La vuelta de la cuenta de arriba: qué dosis salió por hectárea.

    **Existe para no confundir las dos cosas, que es un fallo de diez veces** (el caso de aceptación
    A02 del contrato: 2 L en 4 ha son 0,5 L/ha, y si no se sabe el área la dosis es **desconocida**,
    no 2). El total es lo que se gastó y la dosis es lo que se gasta por hectárea; el mismo número
    significa una cosa u otra según dónde esté, y por eso aquí no se devuelve un número cuando falta
    uno de los dos datos.

    Y devuelve `None`, nunca 0, cuando falta la superficie o cuando vale cero. En esta base, un
    tratamiento sin superficie apuntada se guarda con un 0 heredado (`servicios.preparar_tratamiento`),
    así que un cero **no** significa «se trató cero hectáreas»: significa que no consta. Dividir por
    él daría un número infinito o una excepción, y las dos cosas son peores que decir que no se sabe.
    """
    if cantidad_total is None or superficie_ha is None or superficie_ha <= 0:
        return None
    return round(cantidad_total / superficie_ha, 4)


def supera_dosis_etiqueta(dosis: float, dosis_maxima: float, tolerancia: float = 1e-6) -> bool:
    """¿Se pasa el agricultor de la dosis de la etiqueta?

    Se admite una tolerancia mínima para no bloquear por redondeos de la propia
    etiqueta (0,8 L/ha escrito como 0,8000001).
    """
    return dosis > dosis_maxima + tolerancia


def supera_superficie(
    superficie_usada: float, superficie_parcela: float | None, tolerancia: float = 1e-4
) -> bool:
    """La superficie tratada o abonada no puede pasar de la de la parcela.

    La tolerancia de 0,0001 ha (1 m²) existe porque el SIGPAC da superficies con
    cuatro decimales y redondear a mano provoca bloqueos absurdos.

    **Y si no se sabe la superficie de la parcela, no se puede decir que se pase** (A7 de
    `docs/T02_VALORES_POR_DEFECTO.md`). `superficie_parcela = None` es «no lo sé», no «cero
    hectáreas»: comparar contra un cero bloquearía cualquier apunte y dejaría la tierra inutilizable,
    que es el defecto que había. Aquí se contesta que no se pasa —no se puede afirmar lo contrario— y
    **quien llama tiene que avisar de que no lo ha podido comprobar**, que es el tercer final que
    pide `AGENTS.md`. Callar sería peor que las dos cosas.
    """
    if superficie_parcela is None:
        return False
    return superficie_usada > superficie_parcela + tolerancia


def esta_vigente(fecha_caducidad: dt.date | None, referencia: dt.date | None = None) -> bool:
    """Vigencia de un carné o de una inspección. Sin fecha, se considera no vigente."""
    if fecha_caducidad is None:
        return False
    return fecha_caducidad >= (referencia or hoy())


def dias_hasta(fecha: dt.date | None, referencia: dt.date | None = None) -> int | None:
    if fecha is None:
        return None
    return (fecha - (referencia or hoy())).days


def caduca_pronto(fecha_caducidad: dt.date | None, dias_aviso: int, referencia: dt.date | None = None) -> bool:
    """¿Caduca dentro del margen de aviso, pero todavía vale?"""
    restantes = dias_hasta(fecha_caducidad, referencia)
    if restantes is None:
        return False
    return 0 <= restantes <= dias_aviso


def formatea_fecha(fecha: dt.date | None) -> str:
    """Fecha en el formato que se lee en España: 12/05/2026."""
    if fecha is None:
        return "sin fecha"
    return fecha.strftime("%d/%m/%Y")


def formatea_numero(valor: float, decimales: int = 2) -> str:
    """Número en castellano, con coma decimal.

    La app le habla a un agricultor español: "0,8 L/ha" se lee bien, "0.8 L/ha" no.
    """
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


def formatea_medida(valor: float | None, unidad: str, decimales: int = 2) -> str:
    """Un número con su unidad, listo para imprimir: «7,2 %», «12 mg/L», «7,1».

    Cuando el parámetro no tiene unidad (el pH, sin ir más lejos) no se deja un hueco
    detrás del número: se devuelve el número solo.
    """
    if valor is None:
        return "sin dato"
    numero = formatea_numero(valor, decimales)
    return f"{numero} {unidad}".strip()


# --------------------------------------------------------------------------
# Las unidades: cuánto producto hay en el almacén
#
# Esto existe para responder a una pregunta que se hace de verdad: «¿me queda bastante
# producto para tratar esta parcela, o tengo que ir a comprar?». Y para el libro de movimientos,
# que es lo que mira una inspección: cuánto entró y cuánto salió.
#
# **El problema, y por qué esto no es una regla de tres.** Un producto se compra en una unidad
# (litros, kilos) y se echa con una dosis que se mide en otra («L/ha», «mL/hL»). Para restar una
# cosa de la otra hay que estar hablando de lo mismo. Y no siempre lo es: si alguien compró
# kilos y echa dosis en litros, esos números **no se pueden comparar**, y decir «te quedan
# -3 kg» sería inventarse un dato.
#
# Así que hay tres familias —volumen, masa y… ninguna— y dentro de cada familia solo se convierte
# lo que es exacto: 1 L = 1000 mL, 1 kg = 1000 g, y 1 cc = 1 mL (es la misma cantidad con dos
# nombres, no una aproximación). Un litro de un producto y un kilo del mismo producto **no** se
# convierten el uno en el otro: eso depende de la densidad, que no la sabemos y que cambia de un
# producto a otro.
# --------------------------------------------------------------------------

# La unidad «base» de cada familia y cuánto vale cada nombre. `cc` y `mL` son lo mismo.
FAMILIA_VOLUMEN = "volumen"
FAMILIA_MASA = "masa"

UNIDADES_BASE = {
    "l": (FAMILIA_VOLUMEN, 1000.0, "L"),
    "litro": (FAMILIA_VOLUMEN, 1000.0, "L"),
    "litros": (FAMILIA_VOLUMEN, 1000.0, "L"),
    "ml": (FAMILIA_VOLUMEN, 1.0, "mL"),
    "cc": (FAMILIA_VOLUMEN, 1.0, "mL"),
    "kg": (FAMILIA_MASA, 1000.0, "kg"),
    "kilo": (FAMILIA_MASA, 1000.0, "kg"),
    "kilos": (FAMILIA_MASA, 1000.0, "kg"),
    "g": (FAMILIA_MASA, 1.0, "g"),
    "gr": (FAMILIA_MASA, 1.0, "g"),
    "gramo": (FAMILIA_MASA, 1.0, "g"),
    "gramos": (FAMILIA_MASA, 1.0, "g"),
}


def unidad_de_una_dosis(unidad_dosis: str | None) -> str:
    """Qué unidad tiene lo que se echa, sacada de la dosis.

    La dosis dice «L/ha», «kg/ha», «mL/hL» o «g/hL». La cantidad total que se echa está en el
    numerador: litros, kilos, mililitros o gramos. El denominador (hectáreas o hectolitros) ya
    se ha usado para calcular el total, así que aquí no hace falta.
    """
    if not unidad_dosis:
        return ""
    return (unidad_dosis.split("/")[0] or "").strip()


def familia_y_factor(unidad: str | None) -> tuple[str, float, str] | None:
    """La familia de una unidad, cuánto vale y su nombre corto. `None` si no se conoce.

    Devolver `None` es una respuesta legítima y frecuente: significa «con esta unidad no sé
    hacer cuentas», y quien llama tiene que decirlo en vez de suponer.
    """
    if not unidad:
        return None
    return UNIDADES_BASE.get(unidad.strip().lower())


def a_la_unidad_base(cantidad: float | None, unidad: str | None) -> float | None:
    """Pasa una cantidad a la unidad base de su familia (mL o g). `None` si no se sabe.

    `None` **no** es cero: es «no lo sé». Un cero diría que no queda producto, y eso es una
    afirmación muy distinta.
    """
    if cantidad is None:
        return None
    datos = familia_y_factor(unidad)
    if datos is None:
        return None
    return round(cantidad * datos[1], 6)


def se_pueden_comparar(unidad_a: str | None, unidad_b: str | None) -> bool:
    """¿Se pueden restar estas dos cantidades sin inventarse nada?

    Solo si están en la misma familia. Un litro y un kilo no: haría falta la densidad.
    """
    datos_a = familia_y_factor(unidad_a)
    datos_b = familia_y_factor(unidad_b)
    if datos_a is None or datos_b is None:
        return False
    return datos_a[0] == datos_b[0]


def convierte(cantidad: float, de: str | None, a: str | None) -> float | None:
    """Pasa una cantidad de una unidad a otra de su misma familia. `None` si no se puede.

    Ejemplo: 2,5 L a mL son 2500. Y 2500 mL a L son 2,5. Si las unidades son de familias
    distintas, devuelve `None` en vez de un número que no significa nada.
    """
    origen = familia_y_factor(de)
    destino = familia_y_factor(a)
    if origen is None or destino is None or origen[0] != destino[0]:
        return None
    return round(cantidad * origen[1] / destino[1], 6)


def nombre_corto_de_unidad(unidad: str | None) -> str:
    """El nombre con el que se enseña una unidad: «L», «kg», «mL». Vacío si no se conoce."""
    datos = familia_y_factor(unidad)
    return datos[2] if datos else (unidad or "")


def anios_transcurridos(fecha: dt.date | None, referencia: dt.date | None = None) -> int | None:
    """Cuántos años han pasado desde esa fecha.

    Se usa para decir en voz alta «este análisis es de hace tres años», que es la
    información que de verdad ayuda a decidir si sirve para el abono de este año. No se
    dice «está caducado»: ningún análisis caduca por ley, y afirmarlo sería inventarse
    una norma.
    """
    if fecha is None:
        return None
    referencia = referencia or hoy()
    anios = referencia.year - fecha.year
    if (referencia.month, referencia.day) < (fecha.month, fecha.day):
        anios -= 1
    return max(anios, 0)


def mas_reciente(analisis: list, referencia: dt.date | None = None):
    """El análisis más nuevo de una lista, o None si la lista está vacía.

    Se ordena por fecha de toma de muestra, que es la fecha real del dato, y no por
    fecha del resultado ni por la de apunte: un boletín puede tardar un mes en llegar.
    """
    vigentes = [a for a in analisis if getattr(a, "fecha_toma_muestra", None) is not None]
    if not vigentes:
        return None
    return max(vigentes, key=lambda a: a.fecha_toma_muestra)
