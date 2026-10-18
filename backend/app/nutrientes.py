"""**Lo que aporta un abono, con su unidad y su base** (CRM-07, 17/10/2026).

Los criterios de la revision, literales:

    La etiqueta puede expresar nutrientes en **porcentaje en masa** y, para liquidos, **equivalentes
    masa/volumen**. Conservar **valor, unidad, base y fuente**.
    Fuente: BOE-A-2013-7540, anexo II: etiquetado de productos liquidos; contempla kg/hl y g/L ademas del
    porcentaje en masa.

    **No confundir concentracion, cantidad comprada, cantidad aplicada y dosis por hectarea.**

    Ejemplos de aceptacion:
      - 600 kg en 3 ha, N 15 % m/m: 200 kg de producto/ha y 30 kg N/ha.
      - 20 L a 100 g N/L en 2 ha: 2 kg N totales y 1 kg N/ha.
      - 20 L a 15 % m/m: **sin densidad no calcular kg N; mostrar el dato que falta**.

    Conservar N, P2O5 y K2O con su **especie quimica declarada**; **no llamarlos P y K sin conversion**.

--------------------------------------------------------------------------------------------------
***LO QUE ESTE MODULO NO HACE, Y ES LO MAS IMPORTANTE***
--------------------------------------------------------------------------------------------------

**No adivina.** Un lito de un producto al 15 % m/m **no pesa un kilo**: pesa lo que diga su densidad, y si
la densidad no consta, **no se calcula** y se dice que falta. Es la misma regla que gobierna el
cuenta-horas -«lo que no se sabe no se convierte en cero»- aplicada a la etiqueta de un abono.

Y por eso todas las respuestas que no se pueden afirmar son **`None`**, nunca `0`: un cero diria «este
abono no aporta fosforo», y lo que pasa es que nadie lo ha declarado. La casa ya tiene esa distincion en
`Fertilizante.riqueza_p` (tres estados), y aqui se respeta.

***Y las cuatro magnitudes NO se mezclan***, que es lo que el criterio avisa de no confundir:

  * **la concentracion** -lo que dice la etiqueta: 15 % m/m, 100 g/L-,
  * **la cantidad comprada** -los sacos, los litros que hay en el almacen-,
  * **la cantidad aplicada** -lo que se echa en esa parcela ese dia-,
  * **y la dosis por hectarea** -lo que toca a cada hectarea-.

Este modulo trabaja con las dos ultimas, y las devuelve **separadas y con su unidad** para que nadie las
sume por parecerse.
"""

from __future__ import annotations

from typing import Any, Mapping

# --------------------------------------------------------------------------- las bases
#
# **La base es parte del dato**, no un adorno: «15» no dice nada si no se sabe si son 15 % en masa o 15 g
# por litro, y el anexo II del BOE admite las tres formas. Guardarla es lo que permite no confundirlas.
PORCENTAJE_EN_MASA = "porcentaje_masa"
GRAMOS_POR_LITRO = "gramos_por_litro"
KILOGRAMOS_POR_HECTOLITRO = "kilogramos_por_hectolitro"
LAS_BASES = (PORCENTAJE_EN_MASA, GRAMOS_POR_LITRO, KILOGRAMOS_POR_HECTOLITRO)

# Y las del **producto**, que no son las mismas: un solido se cuenta en kilos y un liquido en litros.
KILOS = "kg"
LITROS = "L"
LAS_UNIDADES_DEL_PRODUCTO = (KILOS, LITROS)

# ***Los nutrientes, con su especie quimica declarada***: en la etiqueta el fosforo va como **P2O5** y el
# potasio como **K2O**, no como P y K. Llamarlos «P» y «K» sin conversion seria cambiar la magnitud, y eso es
# justo lo que el criterio prohibe.
LOS_NUTRIENTES = ("n", "p2o5", "k2o")
LOS_NOMBRES = {"n": "N", "p2o5": "P2O5", "k2o": "K2O"}

# Los motivos por los que una cuenta **no se puede** hacer. Se devuelven como codigos, no como un `None`
# mudo: «no se sabe» tiene que poder decirse, y decir **que** falta es lo unico util.
FALTA_LA_DENSIDAD = "falta_la_densidad"
FALTA_LA_SUPERFICIE = "falta_la_superficie"
LA_BASE_NO_VALE_PARA_ESA_UNIDAD = "esa_base_no_vale_para_esa_unidad"
LA_UNIDAD_DEL_PRODUCTO_NO_ES_DE_LAS_QUE_HAY = "la_unidad_del_producto_no_es_de_las_que_hay"
LA_BASE_NO_ES_DE_LAS_QUE_HAY = "la_base_no_es_de_las_que_hay"

# El hectolitro, que es lo que hace falta para pasar de kg/hl a kilos.
LITROS_EN_UN_HECTOLITRO = 100.0


def la_base_es_de_las_que_hay(base: str) -> bool:
    return (base or "").strip() in LAS_BASES


def la_unidad_es_de_las_que_hay(unidad: str) -> bool:
    return (unidad or "").strip() in LAS_UNIDADES_DEL_PRODUCTO


def _los_kilos_de_nutriente_por_unidad_de_producto(
    *, base: str, riqueza: float, unidad: str, densidad_kg_por_litro: float | None
) -> tuple[float | None, str | None]:
    """Los kilos de nutriente que hay en **una** unidad de producto (un kilo o un litro).

    ***LA UNIDAD DEL PRODUCTO NO ES UN ADORNO*** (17/10/2026, y esto lo cazo la primera corrida de las
    pruebas): las mismas palabras significan cosas distintas segun lo que se cuente.

      * **`%` en masa sobre un SOLIDO**: sale directo. Un kilo de producto son mil gramos, y el 15 % de un
        kilo son 150 g **sin pesar nada mas**. Pedir densidad aqui daria «no se sabe» donde **si se sabe**.
      * **`%` en masa sobre un LIQUIDO**: el porcentaje es de la **masa**, y un litro pesa lo que diga su
        densidad. Sin ella **no hay cuenta**, y decirlo es la respuesta -es el caso estrella del criterio-.
      * **`g/L` y `kg/hl`**: son masa **por volumen**, o sea que solo valen para un liquido. En un solido
        devuelven **`None` con su motivo**, en vez de un numero que saldria de dividir por algo que no
        existe.

    Devuelve `(kilos, motivo)`: o el numero, o `None` y **por que** no se puede.
    """
    if base == PORCENTAJE_EN_MASA:
        if unidad == KILOS:
            return riqueza / 100.0, None
        return (None, FALTA_LA_DENSIDAD) if densidad_kg_por_litro is None else (
            riqueza / 100.0 * densidad_kg_por_litro,
            None,
        )
    if base == GRAMOS_POR_LITRO:
        # 100 g/L son 0,1 kg por litro.
        if unidad != LITROS:
            return None, LA_BASE_NO_VALE_PARA_ESA_UNIDAD
        return riqueza / 1000.0, None
    if base == KILOGRAMOS_POR_HECTOLITRO:
        # 1 hl son 100 L, asi que 1 kg/hl son 0,01 kg por litro.
        if unidad != LITROS:
            return None, LA_BASE_NO_VALE_PARA_ESA_UNIDAD
        return riqueza / LITROS_EN_UN_HECTOLITRO, None
    return None, LA_BASE_NO_ES_DE_LAS_QUE_HAY


def el_aporte(
    *,
    cantidad: float,
    unidad: str,
    riquezas: Mapping[str, float | None],
    base: str,
    superficie_ha: float | None = None,
    densidad_kg_por_litro: float | None = None,
) -> dict[str, Any]:
    """***Lo que aporta una aplicacion de abono***, con su unidad y su base, y **lo que falta para saberlo**.

    Entra lo que se sabe -los kilos o los litros, la superficie, lo que dice la etiqueta y su base- y sale:

      * `producto`: la cantidad aplicada y **la dosis por hectarea**, en la unidad del producto.
      * `nutrientes`: para `n`, `p2o5` y `k2o`, los **kilos totales** y los **kilos por hectarea**.
      * `lo_que_falta`: los datos que impiden una cuenta, **dichos**. Lista vacia si no falta ninguno.

    **Nada que no se pueda afirmar sale como `None`, nunca como `0`.** Un `0` diria «este abono no lleva
    fosforo»; `None` dice «nadie lo ha declarado», que es lo que pasa de verdad.
    """
    falta: list[str] = []

    if not la_unidad_es_de_las_que_hay(unidad):
        falta.append(LA_UNIDAD_DEL_PRODUCTO_NO_ES_DE_LAS_QUE_HAY)
    if not la_base_es_de_las_que_hay(base):
        falta.append(LA_BASE_NO_ES_DE_LAS_QUE_HAY)
    if falta:
        # Sin saber en que se cuenta el producto ni en que se declara el nutriente no hay nada que
        # calcular: se dice y se para, en vez de sacar numeros de la nada.
        return {
            "producto": {"cantidad": cantidad, "unidad": unidad, "por_hectarea": None},
            "nutrientes": {cual: {"total_kg": None, "por_hectarea_kg": None} for cual in LOS_NUTRIENTES},
            "lo_que_falta": falta,
            "la_base": base,
        }

    # ***La base tiene que pegar con la unidad del producto.*** Los g/L y los kg/hl **son** masa por volumen:
    # en un solido no significan nada, y decir «no vale» es mejor que inventarse una densidad que nadie ha
    # medido. El % m/m si vale para las dos, porque es masa sobre masa.
    if unidad == LITROS and base == PORCENTAJE_EN_MASA and densidad_kg_por_litro is None:
        # ***El caso estrella del criterio***: 20 L a 15 % m/m **no** son 3 kg de nada. Falta la densidad, y
        # se dice que falta en vez de dar un numero que seria falso.
        falta.append(FALTA_LA_DENSIDAD)

    # **La dosis por hectarea** sale de la cantidad y la superficie. Sin superficie **no se sabe**, y no es
    # cero: es que no consta en cuantas hectareas se ha echado.
    if superficie_ha is None or superficie_ha <= 0:
        falta.append(FALTA_LA_SUPERFICIE)
        producto_por_hectarea = None
    else:
        producto_por_hectarea = cantidad / superficie_ha

    nutrientes: dict[str, dict[str, float | None]] = {}
    for cual in LOS_NUTRIENTES:
        riqueza = riquezas.get(cual)
        if riqueza is None:
            # **«No consta»**, que no es lo mismo que cero.
            nutrientes[cual] = {"total_kg": None, "por_hectarea_kg": None}
            continue
        por_unidad, motivo = _los_kilos_de_nutriente_por_unidad_de_producto(
            base=base,
            riqueza=float(riqueza),
            unidad=unidad,
            densidad_kg_por_litro=densidad_kg_por_litro,
        )
        if motivo is not None or por_unidad is None:
            nutrientes[cual] = {"total_kg": None, "por_hectarea_kg": None}
            if motivo is not None and motivo not in falta:
                falta.append(motivo)
            continue
        total = cantidad * por_unidad
        nutrientes[cual] = {
            "total_kg": round(total, 4),
            "por_hectarea_kg": (
                None if producto_por_hectarea is None else round(total / superficie_ha, 4)
            ),
        }

    return {
        "producto": {
            "cantidad": cantidad,
            "unidad": unidad,
            "por_hectarea": None if producto_por_hectarea is None else round(producto_por_hectarea, 4),
        },
        "nutrientes": nutrientes,
        "lo_que_falta": falta,
        "la_base": base,
    }


def el_aporte_de_la_riqueza_porcentual(
    *, cantidad: float, unidad: str, superficie_ha: float | None, riquezas: Mapping[str, float | None]
) -> dict[str, Any]:
    """El atajo para lo que ya hay guardado: **las columnas antiguas son porcentajes en masa**.

    `Fertilizante.riqueza_n` y `RegistroFertilizacion.riqueza_n` **no dicen su base** porque son de antes,
    y el criterio manda **mantenerlas compatibles**: lo que siempre significaron es **% m/m**, asi que se
    leen asi. No se reinterpreta nada: se dice lo que eran.
    """
    return el_aporte(
        cantidad=cantidad,
        unidad=unidad,
        riquezas=riquezas,
        base=PORCENTAJE_EN_MASA,
        superficie_ha=superficie_ha,
    )
