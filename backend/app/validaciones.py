"""Las validaciones legales del cuaderno.

Aquí está lo que hace que el programa sirva de verdad: no dejar apuntar algo que
la ley no permite, y decirlo en castellano. Cada regla devuelve un `Aviso` con
`bloquea=True` (no se puede guardar) o `bloquea=False` (se guarda, pero se avisa).

Decisión: un aviso que bloquea NUNCA deja al agricultor sin salida. Todos los
mensajes dicen qué hacer ahora, y todos están en `textos.MENSAJES` para que el
test `test_sin_jerga` los revise de una vez.

Decisión sobre zona de nitratos: los anexos III y V de la Orden MAV/398/2022
están cargados para consulta, pero no se bloquea automáticamente un abono
basándose solo en esas tablas. Hay que conocer la zona vulnerable, el cultivo,
las condiciones y las excepciones del caso. La regla de 170 kg N/ha en
estiércoles y otras condiciones conocidas se avisan por separado.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from . import catalogos, legal, nitratos_cyl, textos


@dataclass(frozen=True)
class Aviso:
    codigo: str
    mensaje: str
    bloquea: bool
    campo: str | None = None

    def como_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "mensaje": self.mensaje,
            "bloquea": self.bloquea,
            "campo": self.campo,
        }


def _aviso(codigo_mensaje: str, campo: str | None, bloquea: bool, **datos) -> Aviso:
    return Aviso(
        codigo=codigo_mensaje,
        mensaje=textos.mensaje(codigo_mensaje, **datos),
        bloquea=bloquea,
        campo=campo,
    )


def _aviso_con_cuenta(base: str, campo: str | None, bloquea: bool, *, cuantos: int) -> Aviso:
    """Un aviso que cuenta cosas, con la frase en singular o en plural.

    El `codigo` que viaja es el de la base —`..._uno` y `..._varios` son la misma cosa dicha de dos
    formas—, para que quien lo mire desde la pantalla o desde una prueba no tenga que saber cuántos
    había para reconocer el aviso. Y la frase sale de `textos.mensaje_con_cuenta`, porque «en esta
    tierra hay 1 abonos» es lo primero que hace desconfiar de un programa (`AGENTS.md` §4).
    """
    return Aviso(
        codigo=base,
        mensaje=textos.mensaje_con_cuenta(base, cuantos),
        bloquea=bloquea,
        campo=campo,
    )


def _hay_agua_al_lado(parcela) -> bool | None:
    """Si al lado de la tierra hay agua, **con tres respuestas**: sí, no y «no lo sé».

    POR QUÉ ESTO NO ES UN BOOLEANO (A12 de `docs/T02_VALORES_POR_DEFECTO.md`, 05/10/2026)
    ===============================================================================
    Los dos campos nacían en `False`, así que una tierra que nadie había contestado se leía como «aquí no
    hay ni río ni toma de agua». Y de eso dependen **dos cosas de la ley**: las restricciones de abonado de
    la Orden MAV/398/2022 y la **franja de seguridad** de un tratamiento. Es decir: un «no» que nadie ha
    dicho **aligeraba las reglas que le aplican al agricultor**, en silencio.

    Devuelve `True` si consta que hay agua, `False` si consta que no, y **`None` si no se sabe** —que no es
    ninguna de las dos, y por eso hay que poder decirlo—. Cuando la tierra no hay ni que preguntarlo
    (`parcela is None`), devuelve `None` también: sin tierra no se sabe, no es que no haya agua.
    """
    if parcela is None:
        return None
    if parcela.captacion_consumo_humano is True or parcela.masa_agua_cerca is True:
        return True
    if parcela.captacion_consumo_humano is False and parcela.masa_agua_cerca is False:
        return False
    return None


def _descripcion_agua(parcela) -> str | None:
    """Cómo se llama el agua que hay al lado, en palabras del agricultor.

    **Y `None` aquí quiere decir «no se sabe», no «no hay agua»** (A12, 05/10/2026): quien necesite
    distinguirlo tiene `_hay_agua_al_lado`, que sí devuelve las tres respuestas.
    """
    if parcela is None:
        return None
    if parcela.captacion_consumo_humano is True:
        return "una toma de agua para beber"
    if parcela.masa_agua_cerca is True:
        return "un río o un arroyo"
    return None


def hay_bloqueo(avisos: list[Aviso]) -> bool:
    return any(aviso.bloquea for aviso in avisos)


# --------------------------------------------------------------------------
# Tratamiento
# --------------------------------------------------------------------------


def _superficie_del_grupo(grupo) -> float | None:
    """La superficie sumada de las parcelas de un grupo. `None` si no hay grupo.

    Se calcula aquí y no se guarda en la base de datos a propósito: si se guardara, añadir o
    quitar una parcela del grupo dejaría el número viejo y la comprobación comprobaría mal.

    **Y devuelve `None` también cuando a alguna tierra del grupo le falta la superficie** (A7 de
    `docs/T02_VALORES_POR_DEFECTO.md`): una suma a la que le falta un número no es una suma, es una
    parte, y con ella se decidiría si el apunte cupo dentro del grupo. Cuando pasa eso,
    `_grupo_con_superficie_a_medias` lo dice para que quien llama avise en vez de callar.
    """
    if grupo is None:
        return None
    parcelas = getattr(grupo, "parcelas", None) or []
    if not parcelas:
        return None
    if any(p.superficie_ha is None for p in parcelas):
        return None
    return round(sum(p.superficie_ha for p in parcelas), 4)


def _grupo_con_superficie_a_medias(grupo) -> bool:
    """¿Es un grupo de tierras al que le falta la superficie de alguna?

    Se pregunta aparte de `_superficie_del_grupo` porque `None` ahí significa dos cosas muy
    distintas —«no hay grupo» y «no se sabe la superficie del grupo»— y confundirlas es no avisar.
    """
    if grupo is None:
        return False
    parcelas = getattr(grupo, "parcelas", None) or []
    return bool(parcelas) and any(p.superficie_ha is None for p in parcelas)


def _aviso_de_superficie_sin_comprobar(
    *, campo: str, donde: str, parcela=None
) -> Aviso:
    """El aviso de una tierra (o un grupo) del que no se sabe la superficie.

    **Es el tercer estado de A7** (`docs/T02_VALORES_POR_DEFECTO.md`). Antes, la superficie que no
    se sabía valía `0,0`, y como todas las comprobaciones de superficie comparan contra ella, la
    tierra dejaba de poder tratarse: cualquier superficie la superaba y el agricultor se encontraba
    con que **no podía apuntar lo que había hecho en el campo**, sin saber que el cero lo había
    puesto el programa.

    Ahora no se bloquea —el cuaderno tiene que recoger lo que de verdad ha pasado— pero **tampoco se
    calla**: se dice que no se ha podido comprobar y **dónde se arregla**, que es la regla de
    `AGENTS.md` §5 («no dejes al agricultor sin salida»). Y si el recinto del SIGPAC tiene su
    superficie guardada, se le dice cuál es **para que él decida**: proponer no es escribir, y la
    superficie del recinto entero no es la cultivada (`models.Parcela.superficie_sigpac_ha`).
    """
    sigpac = getattr(parcela, "superficie_sigpac_ha", None) if parcela is not None else None
    if sigpac is not None:
        return _aviso(
            "V26_tierra_sin_superficie_con_la_del_sigpac",
            campo,
            False,
            donde=donde,
            sigpac=legal.formatea_numero(sigpac, 2),
        )
    return _aviso("V25_tierra_sin_superficie", campo, False, donde=donde)


def validar_tratamiento(
    *,
    datos,
    parcela=None,
    producto=None,
    aplicador=None,
    equipo=None,
    explotacion=None,
    periodo_cultivo: tuple[dt.date | None, dt.date | None] | None = None,
    instalacion=None,
    hay_medidas_declaradas: bool | None = None,
    asesor=None,
    grupo=None,
) -> list[Aviso]:
    """Revisa un tratamiento antes de guardarlo.

    `datos` es el esquema de entrada (`schemas.TratamientoEntrada`): solo se leen
    atributos, así que también vale un objeto sencillo en los tests.

    `grupo` es la unidad homogénea de cultivo, cuando el tratamiento es de **varias parcelas a
    la vez**. Existe aquí por un agujero que se encontró en la ronda 17: la comprobación de que
    no se trata más superficie de la que hay **solo se hacía cuando había una parcela**, así que
    en un grupo no se comprobaba nada. Se podía apuntar un tratamiento de 100 hectáreas sobre un
    grupo de 5 y el programa no decía ni una palabra.
    """
    avisos: list[Aviso] = []

    # --- dónde ---
    #
    # No es lo mismo echar producto en la tierra que en una nave. La app oficial lo
    # tiene como cuatro secciones distintas (tratamiento, semilla tratada, postcosecha,
    # instalaciones); aquí es el mismo registro, y lo que cambia es qué se exige:
    # una parcela o una instalación.
    tipo = getattr(datos, "tipo", None) or "parcela"

    if tipo in catalogos.TRATAMIENTO_EN_INSTALACION:
        if datos.instalacion_id is None:
            avisos.append(_aviso("V20_sin_instalacion", "instalacion_id", True))
            return avisos
    elif datos.parcela_id is None and getattr(datos, "grupo_id", None) is None:
        avisos.append(_aviso("V18_sin_parcela", "parcela_id", True))
        return avisos  # sin parcela no tiene sentido seguir comprobando

    # --- superficie ---
    #
    # Una nave no se mide en hectáreas: la superficie se pide solo cuando la aplicación
    # va sobre la tierra. En una instalación se apunta el local, no una superficie.
    if tipo in catalogos.TRATAMIENTO_EN_PARCELA and not datos.superficie_tratada_ha:
        avisos.append(_aviso("V22_sin_superficie", "superficie_tratada_ha", True))

    # **Y si de la tierra no se sabe la superficie, no se puede comprobar que se pase** (A7). Antes
    # esa tierra valía `0,0` y cualquier superficie la superaba, así que el agricultor no podía
    # apuntar nada en ella. Ahora el apunte se puede guardar y se avisa de lo que no se ha podido
    # mirar, diciéndole dónde está el dato que falta.
    if parcela is not None and parcela.superficie_ha is None:
        avisos.append(
            _aviso_de_superficie_sin_comprobar(
                campo="superficie_tratada_ha", donde="esta tierra", parcela=parcela
            )
        )
    elif (
        parcela is not None
        and datos.superficie_tratada_ha
        and legal.supera_superficie(datos.superficie_tratada_ha, parcela.superficie_ha)
    ):
        avisos.append(
            _aviso(
                "V4_superficie_excedida",
                "superficie_tratada_ha",
                True,
                parcela=legal.formatea_numero(parcela.superficie_ha, 2),
                usada=legal.formatea_numero(datos.superficie_tratada_ha, 2),
            )
        )

    # --- y lo mismo cuando es en varias parcelas a la vez ---
    #
    # Esto es el agujero que se encontró en la ronda 17: sin grupo, la comprobación se saltaba
    # entera. Ahora se mira contra la superficie **sumada** de las parcelas del grupo, que es la
    # superficie de la que de verdad se está hablando. Y si a alguna tierra del grupo le falta su
    # superficie, se dice que no se ha podido comprobar en vez de dar el grupo por bueno.
    superficie_del_grupo = _superficie_del_grupo(grupo)
    if parcela is None and _grupo_con_superficie_a_medias(grupo):
        avisos.append(
            _aviso_de_superficie_sin_comprobar(
                campo="superficie_tratada_ha", donde="alguna tierra de este grupo"
            )
        )
    elif (
        parcela is None
        and superficie_del_grupo is not None
        and datos.superficie_tratada_ha
        and legal.supera_superficie(datos.superficie_tratada_ha, superficie_del_grupo)
    ):
        avisos.append(
            _aviso(
                "V4_superficie_excedida_grupo",
                "superficie_tratada_ha",
                True,
                parcela=legal.formatea_numero(superficie_del_grupo, 2),
                usada=legal.formatea_numero(datos.superficie_tratada_ha, 2),
            )
        )

    # --- producto ---
    if producto is None:
        avisos.append(_aviso("V1_sin_registro", "producto_id", True))
    else:
        if not producto.numero_registro:
            avisos.append(_aviso("V1_sin_registro", "producto_id", True))
        if producto.autorizado is False:
            avisos.append(_aviso("V1_no_autorizado", "producto_id", True))
        elif producto.autorizado is None:
            # **No saber no bloquea, pero no se calla.** El producto del que nadie ha comprobado
            # nada no se puede dar por bueno en silencio (es lo que hacía el defecto `True`), y
            # tampoco se puede impedir apuntar lo que de verdad ha pasado en el campo: el cuaderno
            # tiene que recogerlo. Ver `models.ProductoFitosanitario.autorizado`.
            avisos.append(_aviso("V1_autorizacion_sin_comprobar", "producto_id", False))
        if producto.autorizacion_hasta and producto.autorizacion_hasta < datos.fecha:
            avisos.append(
                _aviso(
                    "V1_autorizacion_caducada",
                    "producto_id",
                    True,
                    fecha=legal.formatea_fecha(producto.autorizacion_hasta),
                )
            )

        # --- dosis ---
        if (
            datos.dosis is not None
            and producto.dosis_maxima is not None
            and legal.supera_dosis_etiqueta(datos.dosis, producto.dosis_maxima)
        ):
            avisos.append(
                _aviso(
                    "V3_dosis_excedida",
                    "dosis",
                    True,
                    maximo=legal.formatea_numero(producto.dosis_maxima, 2),
                    unidad=producto.unidad_dosis,
                )
            )

        # --- caducidad del bote (avisa, no bloquea: puede quedar otro envase) ---
        if producto.fecha_caducidad and producto.fecha_caducidad < datos.fecha:
            avisos.append(
                _aviso(
                    "V16_producto_caducado",
                    "producto_id",
                    False,
                    fecha=legal.formatea_fecha(producto.fecha_caducidad),
                )
            )

        # --- ecológico ---
        #
        # **Tres estados** (A13, 05/10/2026). Antes esto era
        # `if explotacion is not None and getattr(explotacion, "produccion_ecologica", False)`, y como el
        # campo nacía en `False`, **la comprobación entera se apagaba** en cuanto nadie marcaba la casilla:
        # una finca ecológica podía echar un producto que no vale para ecológico y el programa no decía
        # nada, porque creía que la finca no era ecológica. Ahora:
        #
        #   · si **consta** que es ecológica, se comprueba como siempre;
        #   · si **no se sabe**, se dice que no se ha podido comprobar (no se calla ni se da por bueno);
        #   · y solo si **consta** que no es ecológica se calla, que es lo correcto.
        es_ecologica = None if explotacion is None else getattr(explotacion, "produccion_ecologica", None)
        if es_ecologica is None:
            avisos.append(_aviso("V15_no_se_si_la_finca_es_ecologica", "producto_id", False))
        elif es_ecologica:
            if producto.permitido_ecologico is False:
                avisos.append(_aviso("V15_no_ecologico", "producto_id", True))
            elif producto.permitido_ecologico is None:
                # La finca es ecológica y no consta que este producto se pueda usar ahí. Antes esto
                # no decía nada, porque el defecto era «sí se puede»: la comprobación que más
                # importa en una finca ecológica estaba apagada por un valor por defecto.
                avisos.append(_aviso("V15_no_se_si_es_ecologico", "producto_id", False))

    # --- por qué se trata ---
    if not datos.justificacion or not datos.justificacion.strip():
        avisos.append(_aviso("V10_sin_justificacion", "justificacion", True))

    # --- quién aplica ---
    if aplicador is not None:
        if not getattr(aplicador, "es_empresa", False):
            if not aplicador.numero_carne:
                avisos.append(
                    _aviso("V6_sin_carne", "aplicador_id", True, nombre=aplicador.nombre)
                )
            elif aplicador.fecha_caducidad_carne and (
                aplicador.fecha_caducidad_carne < datos.fecha
            ):
                avisos.append(
                    _aviso(
                        "V6_carne_caducado",
                        "aplicador_id",
                        True,
                        nombre=aplicador.nombre,
                        fecha=legal.formatea_fecha(aplicador.fecha_caducidad_carne),
                    )
                )

    # --- quién lo asesora ---
    #
    # Decisión sobre el número de ROPO: **bloquea**, igual que el carné del aplicador. El
    # motivo no es un capricho: el interfaz de la Junta rechaza un asesor que no encuentre en
    # el registro ROPO (error `ERROR_VALIDAR_ASESOR`, código 7), así que un apunte que no se
    # va a poder volcar es mejor no dejarlo guardar. Se le dice qué hacer, no solo que no.
    if asesor is not None:
        if not (getattr(asesor, "numero_ropo", None) or "").strip():
            avisos.append(_aviso("S1_sin_ropo_asesor", "asesor_id", True, nombre=asesor.nombre))
        # El asesoramiento sin fecha ni resultado es medio apunte: la norma pide las dos
        # cosas (campos 44 y 51 del bloque de tratamientos). Avisa y no bloquea, porque el
        # agricultor puede no acordarse del día exacto.
        if getattr(datos, "asesor_fecha", None) is None:
            avisos.append(_aviso("S2_asesor_sin_fecha", "asesor_fecha", False))
        if getattr(datos, "asesoramiento_validado", None) is None:
            avisos.append(_aviso("S3_asesor_sin_validar", "asesoramiento_validado", False))

    # --- con qué máquina ---
    if equipo is not None:
        if equipo.fecha_proxima_iteaf is None:
            avisos.append(
                _aviso("V7_sin_iteaf", "equipo_id", True, equipo=equipo.nombre)
            )
        elif equipo.fecha_proxima_iteaf < datos.fecha:
            avisos.append(
                _aviso(
                    "V7_iteaf_caducada",
                    "equipo_id",
                    True,
                    equipo=equipo.nombre,
                )
            )

    # --- fecha dentro del cultivo (avisa, no bloquea: el agricultor sabe más) ---
    if periodo_cultivo is not None:
        inicio, fin = periodo_cultivo
        if (inicio and datos.fecha < inicio) or (fin and datos.fecha > fin):
            avisos.append(_aviso("V5_fecha_fuera_de_cultivo", "fecha", False))

    # --- orilla sin tratar ---
    #
    # **Y si no se sabe si hay agua, se dice** (A12, 05/10/2026). Antes, con los dos campos en `False` por
    # defecto, una tierra sin contestar se leía como «aquí no hay agua»: **la franja de seguridad no se
    # comprobaba y el programa se callaba**. Ahora, cuando no consta, se avisa de que no se ha podido
    # comprobar —que es distinto de que no haya nada que respetar—.
    agua = _descripcion_agua(parcela)
    if agua:
        if getattr(datos, "franja_seguridad_respetada", None) is None:
            avisos.append(_aviso("V11_franja_seguridad", "franja_seguridad_respetada", False, agua=agua))
    elif _hay_agua_al_lado(parcela) is None:
        avisos.append(_aviso("V11_no_se_si_hay_agua", "franja_seguridad_respetada", False))

    # --- días de espera: informativo y muy útil ---
    plazo = plazo_de_espera(datos, producto)
    if plazo is not None:
        avisos.append(
            _aviso(
                "V8_dias_de_espera",
                None,
                False,
                fin=legal.formatea_fecha(legal.fecha_fin_plazo_seguridad(datos.fecha, plazo)),
            )
        )

    # --- ¿está el cuaderno a medias en medidas preventivas? ---
    #
    # Va el último a propósito: es un recordatorio de OTRA sección, no un problema de este
    # apunte. Si el agricultor se está pasando de la dosis, eso es lo urgente; esto, no.
    recordatorio = aviso_si_no_hay_medidas(hay_medidas=hay_medidas_declaradas)
    if recordatorio is not None:
        avisos.append(recordatorio)

    return avisos


def plazo_de_espera(datos, producto) -> int | None:
    """Los días de espera: manda lo que diga el agricultor, si lo dice."""
    propio = getattr(datos, "plazo_seguridad_dias", None)
    if propio is not None:
        return propio
    if producto is not None:
        return producto.plazo_seguridad_dias
    return None


# --------------------------------------------------------------------------
# Fertilización
# --------------------------------------------------------------------------


def validar_fertilizacion(
    *,
    datos,
    parcela=None,
    fertilizante=None,
    plan=None,
    aplicado_n_ha: float = 0.0,
    organico_n_ha: float = 0.0,
    total_n_ha: float = 0.0,
    cultivo=None,
    grupo=None,
    aportes_por_grupo_sin_comprobar: int = 0,
    apuntes_ya_sin_composicion: int = 0,
    tierras_del_grupo: list[dict] | None = None,
) -> list[Aviso]:
    """Revisa un abono antes de guardarlo.

    `organico_n_ha` son los kilos de nitrógeno **en forma de estiércol o purín** que ya se han
    echado este año en esa parcela, sin contar el que se está apuntando. Es lo que hace falta
    para poder comprobar la regla de los 170 kg.

    `aportes_por_grupo_sin_comprobar` y `apuntes_ya_sin_composicion` son las dos formas que tiene
    este cálculo de quedarse a medias (A4 y A6 de `docs/T02_VALORES_POR_DEFECTO.md`): apuntes
    hechos en varias tierras a la vez de los que no se sabe qué tierra llevó qué, y apuntes de los
    que no consta la composición. Se pasan ya contados desde `servicios`, que es quien mira la base
    de datos, para que esta función siga siendo pura.

    `tierras_del_grupo` es lo mismo, pero para un apunte que va sobre un grupo entero: la zona de
    nitratos y el nitrógeno que ya llevaba cada tierra, para poder comprobar el tope **tierra por
    tierra** en vez de callar. Lo prepara el router, que es quien puede mirar la base de datos.

    Decisión sobre las reglas de nitratos: **avisan, no bloquean.** Y no es por comodidad. El
    cuaderno tiene que recoger lo que de verdad ha pasado: si el agricultor se ha pasado, lo
    que hace falta es que quede escrito con su aviso, no que el programa le impida apuntarlo y
    el cuaderno acabe diciendo que ese abono no se echó. Además nuestros datos pueden estar
    incompletos: puede haber estiércol de una cuadrilla que no se apuntó.
    """
    avisos: list[Aviso] = []

    if datos.parcela_id is None and getattr(datos, "grupo_id", None) is None:
        avisos.append(_aviso("V18_sin_parcela", "parcela_id", True))
        return avisos

    if datos.kg_ha_producto is None or datos.kg_ha_producto <= 0:
        avisos.append(_aviso("F1_sin_cantidad", "kg_ha_producto", True))

    # **Si de la tierra no se sabe la superficie, no se puede comprobar que se pase** (A7): antes
    # esa tierra valía `0,0` y cualquier superficie la superaba, así que no se podía abonar. El
    # abono se guarda y se dice lo que no se ha podido mirar, con dónde se arregla.
    if parcela is not None and parcela.superficie_ha is None:
        avisos.append(
            _aviso_de_superficie_sin_comprobar(
                campo="superficie_ha", donde="esta tierra", parcela=parcela
            )
        )
    elif parcela is not None and legal.supera_superficie(
        datos.superficie_ha, parcela.superficie_ha
    ):
        avisos.append(
            _aviso(
                "F2_superficie_excedida",
                "superficie_ha",
                True,
                parcela=legal.formatea_numero(parcela.superficie_ha, 2),
                usada=legal.formatea_numero(datos.superficie_ha, 2),
            )
        )
    # Y cuando el abono es de varias parcelas a la vez, contra la superficie del grupo: sin
    # esto, abonar 100 hectáreas sobre un grupo de 5 pasaba sin que nadie dijera nada. Si a alguna
    # tierra del grupo le falta su superficie, se dice que no se ha podido comprobar.
    superficie_del_grupo = _superficie_del_grupo(grupo)
    if parcela is None and _grupo_con_superficie_a_medias(grupo):
        avisos.append(
            _aviso_de_superficie_sin_comprobar(
                campo="superficie_ha", donde="alguna tierra de este grupo"
            )
        )
    elif (
        parcela is None
        and superficie_del_grupo is not None
        and legal.supera_superficie(datos.superficie_ha, superficie_del_grupo)
    ):
        avisos.append(
            _aviso(
                "F2_superficie_excedida_grupo",
                "superficie_ha",
                True,
                parcela=legal.formatea_numero(superficie_del_grupo, 2),
                usada=legal.formatea_numero(datos.superficie_ha, 2),
            )
        )

    if parcela is not None and parcela.zona_vulnerable_nitratos:
        # El aviso dice las reglas que de verdad hay cargadas, con sus números, en vez de decir
        # «hay reglas más estrictas» y dejarlo ahí. Las que faltan se cuentan en la ayuda.
        avisos.append(
            _aviso(
                "F3_zona_nitratos",
                None,
                False,
                tope=catalogos.limite_de_estiercol_kg_n_ha(),
            )
        )

    if parcela is not None and parcela.sistema == "regadio" and getattr(datos, "plan_id", None) is None:
        avisos.append(_aviso("F4_sin_plan_regadio", "plan_id", False))

    # --- ¿se está pasando del plan del año? ---
    #
    # Avisa, no bloquea, y el motivo importa: el plan es una recomendación, no un
    # límite legal. El anexo III está cargado como tabla de referencia, pero su valor
    # puede variar con la cosecha esperada; el plan tampoco se usa como límite legal.
    if (
        plan is not None
        and plan.necesidad_n
        and fertilizante is not None
        and datos.kg_ha_producto
    ):
        nuevo = legal.uf_por_hectarea(datos.kg_ha_producto, fertilizante.riqueza_n)
        # Si no consta la composición no hay nada que comparar: `uf_por_hectarea` devuelve `None`, y
        # tratarlo como un cero diría que este abono no aporta nitrógeno. El aviso `F9` ya explica
        # que ese abono no se ha podido calcular (A6 de `docs/T02_VALORES_POR_DEFECTO.md`).
        total = None if nuevo is None else (aplicado_n_ha or 0.0) + nuevo
        if total is not None and total > plan.necesidad_n * 1.001:
            avisos.append(
                _aviso(
                    "F5_plan_excedido",
                    "kg_ha_producto",
                    False,
                    plan=legal.formatea_numero(plan.necesidad_n, 1),
                    total=legal.formatea_numero(total, 1),
                )
            )

    # --- la composición del abono: cuando no consta, se dice (A6) ---
    #
    # Es un aviso y no un bloqueo por el mismo motivo que los de nitratos: el abono se echó y el
    # cuaderno tiene que recogerlo. Lo que no puede es **calcular lo que aporta** ni entrar en el
    # tope de nitrógeno como si aportara cero, y eso es lo que se le dice, con dónde se arregla.
    if _composicion_desconocida(fertilizante):
        avisos.append(_aviso("F9_composicion_sin_comprobar", "fertilizante_id", False))
    if apuntes_ya_sin_composicion:
        avisos.append(
            _aviso_con_cuenta(
                "F10_lo_ya_apuntado_sin_composicion",
                None,
                False,
                cuantos=apuntes_ya_sin_composicion,
            )
        )

    # --- las reglas del programa de actuación de la zona de nitratos ---
    #
    # Se comprueban SOLO si la parcela está en zona vulnerable. Fuera de ella el Código de
    # Buenas Prácticas Agrarias es voluntario, y avisar de algo que no obliga sería ruido.
    # Y cuando no se sabe si está (o el abono es de un grupo de tierras), la función de dentro
    # dice que no se ha podido comprobar: eso no es ruido, es no dejar creer que se ha mirado.
    avisos.extend(
        _reglas_de_nitratos(
            datos=datos,
            parcela=parcela,
            fertilizante=fertilizante,
            organico_n_ha=organico_n_ha,
            total_n_ha=total_n_ha,
            cultivo=cultivo,
            aportes_por_grupo_sin_comprobar=aportes_por_grupo_sin_comprobar,
            tierras_del_grupo=tierras_del_grupo,
        )
    )

    return avisos


def _composicion_desconocida(fertilizante) -> bool:
    """¿Nos falta la composición de este abono?

    Tres casos, y los tres son «no lo sé» (A6 de `docs/T02_VALORES_POR_DEFECTO.md`): no hay ficha
    de abono en el catálogo —el abono se apuntó a mano, o lo creó una factura—, la ficha existe pero
    nadie le puso la composición, o solo declaró una parte. Se mira **cualquiera de los tres
    nutrientes** porque cada uno entra por su cuenta en el documento que se firma y en la cuenta del
    año: dejar el potasio en blanco y contestar «0 %» sería afirmar algo que nadie ha dicho.
    """
    if fertilizante is None:
        return True
    return any(
        getattr(fertilizante, nombre, None) is None
        for nombre in ("riqueza_n", "riqueza_p", "riqueza_k")
    )


def _reglas_de_nitratos(*, datos, parcela, fertilizante, organico_n_ha: float,
                       total_n_ha: float, cultivo,
                       aportes_por_grupo_sin_comprobar: int = 0,
                       tierras_del_grupo: list[dict] | None = None) -> list[Aviso]:
    """Las reglas de la Orden MAV/398/2022 que se pueden comprobar con lo que hay apuntado.

    Cada aviso lleva su número y su regla, y ninguno bloquea. Ver el porqué en
    `validar_fertilizacion`.

    **Tres finales, no dos.** Si la tierra está en zona vulnerable, se comprueban las reglas. Si
    se sabe que está fuera, no se comprueba nada (fuera de la zona el Código de Buenas Prácticas
    Agrarias es voluntario y avisar de algo que no obliga sería ruido). Y si **no se sabe** —la
    tierra no tiene comprobada su zona de nitratos, o el abono es de un grupo de tierras que
    pueden estar unas dentro y otras fuera— el programa lo dice: callar ahí dejaría al agricultor
    creyendo que sus abonos se han mirado, cuando no se ha mirado nada.

    **Y cuando el abono es de un grupo, se comprueba tierra por tierra** (`tierras_del_grupo`). El
    tope de los 170 kg es **por tierra y por año**, así que la única forma honesta de mirarlo en un
    apunte que va sobre varias tierras es mirar cada una con su propia historia: la misma dosis por
    hectárea que se está apuntando, sumada a lo que ya llevaba **esa** tierra. No hay ningún reparto
    en eso —no se reparten los kilos del grupo, se comprueba cada tierra con la dosis que de verdad
    se le va a echar— y es lo que evita el agujero de A4 en su otra mitad: un agricultor que abona
    **siempre** por grupo no habría visto nunca el aviso.
    """
    if parcela is None:
        return _reglas_de_nitratos_de_un_grupo(
            datos=datos,
            fertilizante=fertilizante,
            tierras_del_grupo=tierras_del_grupo,
            aportes_por_grupo_sin_comprobar=aportes_por_grupo_sin_comprobar,
        )

    if parcela.zona_vulnerable_nitratos is None:
        return [_aviso("N4_no_se_si_es_zona_de_nitratos", None, False)]

    if not parcela.zona_vulnerable_nitratos:
        return []

    avisos: list[Aviso] = []
    tipo = getattr(datos, "tipo", None) or (getattr(fertilizante, "tipo", None) if fertilizante else None)
    es_organico = catalogos.es_abono_organico(tipo)

    # --- lo que se apuntó en varias tierras a la vez y no se puede atribuir (A4) ---
    #
    # El tope de los 170 kg es **por tierra y por año**, así que lo que se echó en un grupo de
    # tierras habría que contarlo en cada una de ellas. Cuando no se puede saber cuál lo recibió,
    # el total del año es una parte de lo que se echó, y esta función no lo calla: si callara,
    # estaría dando por bueno un límite legal que no ha podido comprobar.
    if aportes_por_grupo_sin_comprobar:
        avisos.append(
            _aviso_con_cuenta(
                "F8_aporte_por_grupo_sin_comprobar",
                None,
                False,
                cuantos=aportes_por_grupo_sin_comprobar,
            )
        )

    # --- el tope de 170 kg de nitrógeno en forma de estiércoles, al año ---
    tope = catalogos.limite_de_estiercol_kg_n_ha()
    if tope is not None and es_organico and fertilizante is not None and datos.kg_ha_producto:
        nuevo = legal.uf_por_hectarea(datos.kg_ha_producto, fertilizante.riqueza_n)
        # Sin composición no hay cuenta que hacer: lo dice el aviso `F9`, que ya ha salido. Un cero
        # aquí sería dar por bueno que este estiércol no aporta nitrógeno (A6).
        total = None if nuevo is None else (organico_n_ha or 0.0) + nuevo
        if total is not None and total > tope * 1.001:
            avisos.append(
                _aviso(
                    "N1_estiercol_pasa_tope",
                    "kg_ha_producto",
                    False,
                    tope=legal.formatea_numero(tope, 0),
                    total=legal.formatea_numero(total, 1),
                    ya=legal.formatea_numero(organico_n_ha or 0.0, 1),
                    nuevo=legal.formatea_numero(nuevo, 1),
                )
            )

    # --- en pendiente, solo orgánicos sólidos ---
    #
    # Decisión: se avisa con **cualquier** abono orgánico, porque el programa no pregunta si es
    # sólido o líquido y no hay forma de saberlo. El propio aviso le dice al agricultor qué
    # tiene que comprobar, que es lo que puede hacer: el purín es líquido y el estiércol no.
    pendiente_maxima = catalogos.pendiente_maxima_para_organico_liquido()
    if (
        pendiente_maxima is not None
        and es_organico
        and parcela.pendiente_pct is not None
        and parcela.pendiente_pct > pendiente_maxima
    ):
        avisos.append(
            _aviso(
                "N2_pendiente_organico",
                None,
                False,
                pendiente=legal.formatea_numero(parcela.pendiente_pct, 1),
                maximo=legal.formatea_numero(pendiente_maxima, 0),
            )
        )

    # El Anexo III solo se compara cuando el cultivo declarado coincide literalmente
    # con una fila y existe cifra para su sistema. No se infiere una equivalencia entre
    # "trigo blando" y "Trigo y Triticale" ni se convierten casillas vacías en cero.
    if cultivo is not None and fertilizante is not None and datos.kg_ha_producto:
        celda = nitratos_cyl.aporte_de(cultivo.especie, cultivo.sistema)
        if celda is not None:
            nuevo = legal.uf_por_hectarea(datos.kg_ha_producto, fertilizante.riqueza_n)
            # Mismo caso que en el tope: sin composición no se puede comparar con la tabla, y el
            # aviso `F9` ya dice por qué. Rellenar con un cero sería inventarse el aporte.
            acumulado = None if nuevo is None else (total_n_ha or 0.0) + nuevo
            referencia = celda["maximo_kg_n_ha"]
            if acumulado is not None and acumulado > referencia * 1.001:
                avisos.append(_aviso(
                    "N3_tabla_cultivo", "kg_ha_producto", False,
                    cultivo=cultivo.especie,
                    sistema="con riego" if cultivo.sistema == "regadio" else "sin riego",
                    referencia=legal.formatea_numero(referencia, 1),
                    total=legal.formatea_numero(acumulado, 1),
                ))

    return avisos


def _reglas_de_nitratos_de_un_grupo(
    *,
    datos,
    fertilizante,
    tierras_del_grupo: list[dict] | None,
    aportes_por_grupo_sin_comprobar: int = 0,
) -> list[Aviso]:
    """Las reglas del tope cuando el abono se apunta sobre varias tierras a la vez.

    **Cómo se mira, y por qué así.** El tope de los 170 kg es **por tierra y por año**, así que la
    única forma honesta de comprobarlo en un apunte que va sobre un grupo es mirar **tierra por
    tierra**: la dosis por hectárea que se está apuntando, sumada a lo que ya llevaba esa tierra. No
    se reparte ningún kilo del grupo —no se puede, no se sabe qué tierra echó qué— y no se inventa
    nada: se comprueba cada tierra con la misma dosis, que es lo que significa apuntar por grupo
    (una unidad homogénea de cultivo: `models.GrupoParcelas`).

    Se nombra **la tierra que más llevaba**, que es la que hay que mirar primero, y el aviso dice de
    qué tierra habla. Si alguna tierra del grupo no tiene comprobada su zona de nitratos, se dice
    también (`N4`): puede estar dentro y no se ha podido mirar.

    `tierras_del_grupo` lo prepara quien llama (el router, que es quien mira la base de datos), con
    la zona y el nitrógeno ya contado de cada tierra. Si no viene, es un apunte de grupo del que no
    se sabe nada: se contesta lo mismo que antes, que no se ha podido comprobar.
    """
    if not tierras_del_grupo:
        return [_aviso("N4_no_se_si_es_zona_de_nitratos", None, False)]

    avisos: list[Aviso] = []
    if aportes_por_grupo_sin_comprobar:
        avisos.append(
            _aviso_con_cuenta(
                "F8_aporte_por_grupo_sin_comprobar",
                None,
                False,
                cuantos=aportes_por_grupo_sin_comprobar,
            )
        )

    sin_comprobar_la_zona = any(tierra["en_zona"] is None for tierra in tierras_del_grupo)
    if sin_comprobar_la_zona:
        avisos.append(_aviso("N4_no_se_si_es_zona_de_nitratos", None, False))

    tope = catalogos.limite_de_estiercol_kg_n_ha()
    tipo = getattr(datos, "tipo", None) or (getattr(fertilizante, "tipo", None) if fertilizante else None)
    nuevo = None
    if tope is not None and catalogos.es_abono_organico(tipo) and fertilizante is not None:
        nuevo = legal.uf_por_hectarea(datos.kg_ha_producto, fertilizante.riqueza_n)

    if nuevo is not None:
        en_zona = [
            tierra
            for tierra in tierras_del_grupo
            if tierra["en_zona"] is True and tierra["kg_n_ha"] is not None
        ]
        pasadas = [
            (tierra["kg_n_ha"] + nuevo, tierra)
            for tierra in en_zona
            if tierra["kg_n_ha"] + nuevo > tope * 1.001
        ]
        if pasadas:
            total, peor = max(pasadas, key=lambda pareja: pareja[0])
            avisos.append(
                _aviso(
                    "F11_tope_estiercol_en_una_tierra_del_grupo",
                    "kg_ha_producto",
                    False,
                    tierra=peor["alias"],
                    tope=legal.formatea_numero(tope, 0),
                    total=legal.formatea_numero(total, 1),
                    ya=legal.formatea_numero(peor["kg_n_ha"], 1),
                    nuevo=legal.formatea_numero(nuevo, 1),
                )
            )

    return avisos


# --------------------------------------------------------------------------
# El plan de abono del año
# --------------------------------------------------------------------------


def validar_plan(*, datos) -> list[Aviso]:
    """Comprueba un plan de abono antes de guardarlo.

    Un plan se puede corregir cuando haga falta —es una previsión, no un apunte— pero
    lo mínimo tiene que estar: qué se abona, dónde y cuánta superficie.
    """
    avisos: list[Aviso] = []

    if datos.parcela_id is None and getattr(datos, "grupo_id", None) is None:
        avisos.append(_aviso("V18_sin_parcela", "parcela_id", True))

    if not (getattr(datos, "cultivo", "") or "").strip():
        avisos.append(_aviso("F6_sin_cultivo_en_el_plan", "cultivo", True))

    if not datos.superficie_ha:
        avisos.append(_aviso("F7_sin_superficie_en_el_plan", "superficie_ha", True))

    return avisos


# --------------------------------------------------------------------------
# Medidas preventivas de la explotación (gestión integrada de plagas)
# --------------------------------------------------------------------------


def validar_medidas(*, aplicadas: list[str] | None) -> list[Aviso]:
    """Revisa la declaración de medidas preventivas de la finca.

    Decisión: **no bloquea nunca.** Marcar cero medidas es una respuesta legítima (hay
    fincas que de verdad no hacen ninguna de las diez), y bloquear ahí dejaría al
    agricultor sin poder cerrar su cuaderno por una pregunta que es suya. Lo que sí hace
    es decirlo, porque la gestión integrada de plagas exige **priorizar lo no químico**
    antes de tratar: si no hay ninguna medida apuntada, en una inspección no se puede
    demostrar que se hizo.
    """
    avisos: list[Aviso] = []
    if not aplicadas:
        avisos.append(_aviso("P1_sin_ninguna", "medidas", False))
    return avisos


def aviso_si_no_hay_medidas(*, hay_medidas: bool | None) -> Aviso | None:
    """El aviso que sale al apuntar un tratamiento cuando la finca no ha declarado nada.

    Vive aparte de `validar_tratamiento` para que se entienda por qué está ahí: no es una
    regla del tratamiento, es un recordatorio de que falta rellenar **otra** sección del
    cuaderno, la de medidas preventivas.

    `None` significa «no se ha podido mirar» (por ejemplo, un tratamiento de una nave, que
    no tiene nada que ver con la GIP de la explotación), y entonces no se dice nada.
    """
    if hay_medidas is None or hay_medidas:
        return None
    return _aviso("P2_tratamiento_sin_medidas", None, False)


# --------------------------------------------------------------------------
# Lo que se vende: cosecha comercializada y venta directa
# --------------------------------------------------------------------------

# Códigos de esta sección: «C» de comercializada.
#
# Decisión: lo que la norma marca con asterisco —fecha, producto y cantidad— **bloquea**, y
# lo que añadimos nosotros para la trazabilidad —comprador, lote, de dónde salió— **avisa y
# no bloquea**. La razón es que el agricultor vende muchas veces sin tener el papel delante,
# y negarle el apunte por no saber el número de albarán sería justo lo contrario de lo que
# hace falta: se apunta hoy y se completa mañana.


def validar_venta(
    *,
    datos,
    cosechado_kg: float | None = None,
    vendido_kg: float | None = None,
) -> list[Aviso]:
    """Revisa una venta antes de guardarla.

    `cosechado_kg` y `vendido_kg` son los totales de la campaña **sin contar esta venta**, y
    solo se usan para avisar. Se pasan ya calculados para que esta función siga siendo pura y
    se pueda probar sin base de datos, igual que las demás.
    """
    avisos: list[Aviso] = []

    if not (getattr(datos, "producto", "") or "").strip():
        avisos.append(_aviso("C1_sin_producto", "producto", True))

    if datos.fecha is None:
        avisos.append(_aviso("C3_sin_fecha", "fecha", True))

    if datos.cantidad is None or datos.cantidad <= 0:
        avisos.append(_aviso("C2_sin_cantidad", "cantidad", True))

    # Las dos fechas tienen un orden, y al revés es un error de tecleo.
    if (
        getattr(datos, "fecha_fin", None) is not None
        and getattr(datos, "fecha", None) is not None
        and datos.fecha_fin < datos.fecha
    ):
        avisos.append(_aviso("C4_fechas_cruzadas", "fecha_fin", True))

    if not (getattr(datos, "comprador", "") or "").strip():
        avisos.append(_aviso("C5_sin_comprador", "comprador", False))

    # --- ¿cuadra lo vendido con lo cosechado? ---
    #
    # Es la comprobación que de verdad sirve de esta sección: lo normal cuando alguien vende
    # más de lo que ha apuntado es que se haya olvidado de apuntar la cosecha, no que haya
    # vendido lo que no tiene. Avisa y no bloquea, porque el agricultor puede tener razón:
    # puede estar vendiendo de una cosecha de otro año.
    if vendido_kg is not None and cosechado_kg is not None:
        esta_venta = catalogos.kilos_de_una_venta(datos.cantidad, getattr(datos, "unidad", "kg"))
        if esta_venta is not None:
            total_vendido = (vendido_kg or 0.0) + esta_venta
            if (cosechado_kg or 0.0) <= 0 and total_vendido > 0:
                avisos.append(
                    _aviso(
                        "C6_venta_sin_cosecha",
                        None,
                        False,
                        vendido=legal.formatea_numero(total_vendido, 0),
                    )
                )
            elif total_vendido > (cosechado_kg or 0.0) * 1.001:
                avisos.append(
                    _aviso(
                        "C7_mas_de_lo_cosechado",
                        None,
                        False,
                        vendido=legal.formatea_numero(total_vendido, 0),
                        cosechado=legal.formatea_numero(cosechado_kg or 0.0, 0),
                    )
                )

    return avisos


# --------------------------------------------------------------------------
# Analíticas
# --------------------------------------------------------------------------


def validar_analitica(*, datos, parametros_limpios: list[dict] | None = None) -> list[Aviso]:
    """Revisa un análisis antes de guardarlo.

    Decisión: aquí NO se bloquea casi nada, y es a propósito. Un análisis es un dato que
    viene de fuera —del laboratorio—, no una decisión del agricultor que haya que impedir.
    Si el boletín no trae el nitrógeno, no se puede obligar a nadie a inventárselo: se
    guarda sin ese número y se avisa de que falta.

    Lo único que sí bloquea es lo que no tiene ningún sentido: un análisis sin decir qué
    se ha analizado, o sin el día en que se cogió la muestra. Sin esas dos cosas, el
    número no se puede usar para nada y el apunte acabaría siendo un papel suelto dentro
    del cuaderno.
    """
    avisos: list[Aviso] = []

    if not (getattr(datos, "tipo", "") or "").strip():
        avisos.append(_aviso("N1_sin_material", "tipo", True))
        return avisos  # sin saber qué es, no se puede comprobar nada más
    if datos.tipo not in catalogos.TIPOS_ANALITICA:
        avisos.append(_aviso("N1_sin_material", "tipo", True))
        return avisos

    if getattr(datos, "fecha_toma_muestra", None) is None:
        avisos.append(_aviso("N2_sin_fecha_de_muestra", "fecha_toma_muestra", True))

    # De dónde salió la muestra. Un análisis de tierra o de planta sin parcela no se puede
    # usar para el plan de abono de nadie, así que ahí sí se pide. El agua de una balsa o
    # un lote de grano ya mezclado pueden no ser de ninguna parcela: ahí no se pide.
    if datos.tipo in catalogos.ANALITICA_DE_PARCELA:
        if datos.parcela_id is None and getattr(datos, "instalacion_id", None) is None:
            avisos.append(_aviso("N3_sin_sitio", "parcela_id", True))

    # Las dos fechas tienen un orden. Al revés es un error de tecleo, y dejarlo pasar
    # haría que el análisis pareciera más viejo o más nuevo de lo que es.
    if (
        getattr(datos, "fecha_resultado", None) is not None
        and getattr(datos, "fecha_toma_muestra", None) is not None
        and datos.fecha_resultado < datos.fecha_toma_muestra
    ):
        avisos.append(_aviso("N4_fechas_cruzadas", "fecha_resultado", True))

    parametros = parametros_limpios if parametros_limpios is not None else []
    if not parametros:
        avisos.append(_aviso("N5_sin_numeros", "parametros", False))

    # Un análisis de restos sin decir qué han encontrado no sirve para nada: el comprador
    # pregunta justo por eso.
    if datos.tipo == "residuos" and not (getattr(datos, "sustancia_detectada", "") or "").strip():
        avisos.append(_aviso("N6_residuos_sin_sustancia", "sustancia_detectada", False))

    # El nitrato del agua de riego ya es abono que recibe el cultivo. No se compara con
    # ningún límite legal porque el programa de actuación de Castilla y León (Orden
    # MAV/398/2022) todavía no está cargado: inventarse el límite sería peor que avisar
    # sin cifra. Lo que sí se hace es decirle el número y que lo cuente.
    for parametro in parametros:
        if parametro.get("clave") == "nitratos" and (parametro.get("valor") or 0) > 0:
            avisos.append(
                _aviso(
                    "N7_agua_con_nitrato",
                    "parametros",
                    False,
                    valor=legal.formatea_numero(parametro["valor"], 1),
                )
            )

    anios = legal.anios_transcurridos(getattr(datos, "fecha_toma_muestra", None))
    if anios is not None and anios >= 3:
        avisos.append(_aviso("N8_analisis_viejo", "fecha_toma_muestra", False, anios=anios))

    if not (getattr(datos, "laboratorio", "") or "").strip():
        avisos.append(_aviso("N9_sin_laboratorio", "laboratorio", False))

    return avisos


# --------------------------------------------------------------------------
# Cosecha: la regla que más disgustos evita
# --------------------------------------------------------------------------


def validar_cosecha(
    *,
    fecha_cosecha: dt.date,
    tratamientos: list,
    producto_por_id: dict | None = None,
) -> list[Aviso]:
    """Comprueba que no se coseche antes de que se cumplan los días de espera.

    `tratamientos` son los tratamientos no anulados de esa parcela en esa campaña.

    **Tres finales, no dos** (A5 de `docs/T02_VALORES_POR_DEFECTO.md`). Si el plazo se sabe y no ha
    pasado, se **bloquea** con `V9_no_puedes_cosechar`. Si se sabe y ya ha pasado, no se dice nada.
    Y si **no se sabe** el plazo —el producto no lo trae en su ficha y el apunte lo heredó vacío—,
    antes no pasaba **nada**: el bucle saltaba el tratamiento y seguía, así que el agricultor
    cosechaba al día siguiente y su cuaderno no decía ni una palabra. Eso no era «no hay plazo»,
    era «no lo he comprobado», y ahora se dice con su aviso, que **no bloquea**: no se puede dejar
    al agricultor sin poder apuntar la cosecha que ha hecho, pero tampoco se le puede dejar
    creyendo que el programa lo ha mirado.

    `producto_por_id` es el respaldo por catálogo: si el apunte no tiene plazo pero su producto sí
    (por ejemplo, porque alguien rellenó la ficha del producto después), se usa el del producto.
    Quien llama tiene que pasarlo, o el respaldo no existe.
    """
    avisos: list[Aviso] = []
    producto_por_id = producto_por_id or {}

    bloqueante: Aviso | None = None
    sin_comprobar = 0

    for tratamiento in tratamientos:
        if getattr(tratamiento, "anulado", False):
            continue
        plazo = tratamiento.plazo_seguridad_dias
        if plazo is None and tratamiento.producto_id:
            producto = producto_por_id.get(tratamiento.producto_id)
            plazo = getattr(producto, "plazo_seguridad_dias", None)
        if plazo is None:
            # No se sabe: ni un permiso ni un silencio. Se cuenta y se dice al final.
            sin_comprobar += 1
            continue
        if bloqueante is None and not legal.se_puede_cosechar(
            tratamiento.fecha, plazo, fecha_cosecha
        ):
            fin = legal.fecha_fin_plazo_seguridad(tratamiento.fecha, plazo)
            restantes = (fin - fecha_cosecha).days
            bloqueante = _aviso(
                "V9_no_puedes_cosechar",
                "fecha",
                True,
                fecha=legal.formatea_fecha(tratamiento.fecha),
                dias=plazo,
                fin=legal.formatea_fecha(fin),
                restantes=restantes,
            )

    # El que bloquea va primero, que es lo urgente; el que dice «no lo he podido comprobar» va
    # detrás, porque no impide guardar y no es lo mismo.
    if bloqueante is not None:
        avisos.append(bloqueante)
    if sin_comprobar:
        avisos.append(
            _aviso_con_cuenta(
                "V27_plazo_de_seguridad_sin_comprobar",
                "fecha",
                False,
                cuantos=sin_comprobar,
            )
        )

    return avisos
