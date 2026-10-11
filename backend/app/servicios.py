"""Lógica de negocio: cómo se construye un registro a partir de lo que manda el agricultor.

Está separado de los routers a propósito. Las reglas de "rellena esto solo, calcula
esto otro, copia lo de la etiqueta" son el corazón del programa y tienen que poder
probarse sin levantar un servidor ni hacer peticiones HTTP.
"""

from __future__ import annotations

import datetime as dt
import unicodedata
from dataclasses import dataclass

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from . import borradores, catalogos, correcciones, dinero, geo, legal, models, textos
from .schemas import FertilizacionEntrada, TratamientoEntrada


def en_zona_de_nitratos(parcela: models.Parcela | None) -> bool | None:
    """Si la tierra está en zona vulnerable a nitratos, o `None` si no se ha podido comprobar.

    **Esto era un `bool(parcela.zona_vulnerable_nitratos) if parcela else False`**, y estaba mal
    por lo mismo que estaba mal en otros sitios: convertía «no lo sé» en «no». `None` aquí no
    quiere decir que la aplicación se hiciera fuera de la zona, quiere decir que nadie lo ha
    comprobado: la tierra puede no tener municipio con código INE, o el listado oficial de zonas
    vulnerables puede no estar cargado (`models.py`, `zona_vulnerable_nitratos`).

    Y tampoco vale para un apunte **de un grupo de tierras**: esas tierras pueden estar unas
    dentro y otras fuera, así que la respuesta honesta es «no se ha podido comprobar».

    Importa más de lo que parece, porque este dato se copia en el apunte y entra en el documento
    que se firma: un `False` inventado allí es una afirmación por escrito de que la aplicación se
    hizo fuera de zona vulnerable.
    """
    if parcela is None:
        return None
    return parcela.zona_vulnerable_nitratos


def preparar_tratamiento(
    datos: TratamientoEntrada,
    *,
    explotacion_id: int,
    producto: models.ProductoFitosanitario | None,
    parcela: models.Parcela | None,
    plazo_seguridad_dias: int | None = None,
    cultivo_declarado: str | None = None,
) -> models.TratamientoFitosanitario:
    """Rellena los datos del producto y calcula lo que el agricultor no debe calcular.

    Todo lo que venga de la etiqueta se COPIA al registro. Es deliberado: el
    cuaderno tiene que decir lo que decía la etiqueta el día de la aplicación. Si
    mañana alguien corrige la ficha del producto, el apunte histórico no cambia.

    `cultivo_declarado` es el cultivo que el agricultor dijo que hay este año en esa parcela
    (ver `cultivo_declarado`). Se usa **solo si el apunte no trae uno**, y es lo que la app
    oficial de la Junta llama un «campo calculado»: el agricultor ya ha dicho qué tiene en la
    parcela esta campaña, así que volver a preguntárselo en cada tratamiento sobra. Y sin esto el
    campo «Cultivo» de cada tratamiento se quedaba vacío, que es como estaba: el asistente no lo
    preguntaba nunca y el volcado oficial lo mandaba en blanco.
    """
    plazo = plazo_seguridad_dias
    if plazo is None and producto is not None:
        plazo = producto.plazo_seguridad_dias

    cantidad_total = None
    if datos.dosis is not None and datos.superficie_tratada_ha:
        cantidad_total = legal.cantidad_total(datos.dosis, datos.superficie_tratada_ha)

    fecha_fin = (
        legal.fecha_fin_plazo_seguridad(datos.fecha, plazo) if plazo is not None else None
    )

    medidas = [codigo for codigo in datos.medidas if codigo in catalogos.CODIGOS_MEDIDA]

    tratamiento = models.TratamientoFitosanitario(
        explotacion_id=explotacion_id,
        campana_id=datos.campana_id,
        fecha=datos.fecha,
        hora_inicio=datos.hora_inicio,
        hora_fin=datos.hora_fin,
        parcela_id=datos.parcela_id,
        grupo_id=datos.grupo_id,
        tipo=getattr(datos, "tipo", None) or "parcela",
        instalacion_id=getattr(datos, "instalacion_id", None),
        producto_cosechado=getattr(datos, "producto_cosechado", None),
        lote_cosecha=getattr(datos, "lote_cosecha", None),
        superficie_tratada_ha=datos.superficie_tratada_ha or 0.0,
        cultivo=datos.cultivo or cultivo_declarado,
        variedad=datos.variedad,
        plaga=datos.plaga,
        justificacion=datos.justificacion,
        estado_cultivo=datos.estado_cultivo,
        producto_id=producto.id if producto else None,
        producto_nombre=producto.nombre_comercial if producto else None,
        numero_registro=producto.numero_registro if producto else None,
        materia_activa=producto.materia_activa if producto else None,
        lote_producto=datos.lote_producto or (producto.lote if producto else None),
        dosis=datos.dosis,
        unidad_dosis=datos.unidad_dosis,
        dosis_maxima_etiqueta=producto.dosis_maxima if producto else None,
        cantidad_total=cantidad_total,
        unidad_cantidad_aplicada=datos.unidad_cantidad_aplicada,
        volumen_caldo_l_ha=datos.volumen_caldo_l_ha,
        plazo_seguridad_dias=plazo,
        fecha_fin_plazo_seguridad=fecha_fin,
        plazo_reentrada_dias=getattr(datos, "plazo_reentrada_dias", None),
        aplicador_id=datos.aplicador_id,
        equipo_id=datos.equipo_id,
        # El asesoramiento: quién lo asesoró y qué dijo. Ver `catalogos.AMBITOS_ASESOR` y los
        # campos 44 a 53 del bloque de tratamientos del contenido mínimo.
        asesor_id=getattr(datos, "asesor_id", None),
        asesor_fecha=getattr(datos, "asesor_fecha", None),
        asesoramiento_validado=getattr(datos, "asesoramiento_validado", None),
        asesoramiento_contrato=getattr(datos, "asesoramiento_contrato", None),
        temperatura_c=datos.temperatura_c,
        humedad_pct=datos.humedad_pct,
        viento_kmh=datos.viento_kmh,
        viento_direccion=datos.viento_direccion,
        franja_seguridad_respetada=datos.franja_seguridad_respetada,
        aplicado_a_mano=getattr(datos, "aplicado_a_mano", None),
        eficacia=getattr(datos, "eficacia", None),
        # «No lo sabemos» se guarda como «no lo sabemos». Ver `en_zona_de_nitratos`.
        en_zona_vulnerable=en_zona_de_nitratos(parcela),
        operadores_expuestos=datos.operadores_expuestos,
        incidencias=datos.incidencias,
        observaciones=datos.observaciones,
    )
    tratamiento.medidas = medidas
    return tratamiento


def preparar_fertilizacion(
    datos: FertilizacionEntrada,
    *,
    explotacion_id: int,
    fertilizante: models.Fertilizante | None,
    parcela: models.Parcela | None,
) -> models.RegistroFertilizacion:
    """Calcula el abono puro (unidades fertilizantes).

    Es el cálculo que más se equivoca a mano y el que de verdad mira la
    administración: los kilos de producto no dicen nada por sí solos.

    **Y cuando la composición no se sabe, no se calcula: se guarda que no se sabe** (A6 de
    `docs/T02_VALORES_POR_DEFECTO.md`). Antes, un abono apuntado sin ficha en el catálogo —o con una
    ficha sin composición, que es lo que deja el abono creado desde una factura— se guardaba con
    `0.0` en los tres nutrientes y con las unidades fertilizantes a cero. Ese cero no se quedaba en
    una pantalla: entraba en el documento que se firma («Nitrógeno (%): 0») y en el plan de abono
    del año, y decía que ese estiércol no aporta nitrógeno. Lo que pasa es que nadie lo ha
    declarado, y eso es `None`, no `0.0`.

    Los apuntes y las fichas **que ya están guardados no se tocan**: los que tienen su `0.0` lo
    conservan, porque ahí no hay forma de distinguir un cero declarado de un cero puesto por el
    programa (mismo criterio que en A1 y A2, y es lo que hace que las firmas ya hechas sigan
    cuadrando).
    """
    riqueza_n = fertilizante.riqueza_n if fertilizante else None
    riqueza_p = fertilizante.riqueza_p if fertilizante else None
    riqueza_k = fertilizante.riqueza_k if fertilizante else None

    cantidad_total_kg = round(datos.kg_ha_producto * datos.superficie_ha, 4)

    return models.RegistroFertilizacion(
        explotacion_id=explotacion_id,
        campana_id=datos.campana_id,
        fecha=datos.fecha,
        parcela_id=datos.parcela_id,
        grupo_id=datos.grupo_id,
        superficie_ha=datos.superficie_ha,
        fertilizante_id=fertilizante.id if fertilizante else None,
        fertilizante_nombre=fertilizante.nombre if fertilizante else None,
        tipo=fertilizante.tipo if fertilizante else "mineral",
        riqueza_n=riqueza_n,
        riqueza_p=riqueza_p,
        riqueza_k=riqueza_k,
        kg_ha_producto=datos.kg_ha_producto,
        cantidad_total_kg=cantidad_total_kg,
        uf_n_ha=legal.uf_por_hectarea(datos.kg_ha_producto, riqueza_n),
        uf_p_ha=legal.uf_por_hectarea(datos.kg_ha_producto, riqueza_p),
        uf_k_ha=legal.uf_por_hectarea(datos.kg_ha_producto, riqueza_k),
        uf_n_total=legal.unidades_fertilizantes(cantidad_total_kg, riqueza_n),
        uf_p_total=legal.unidades_fertilizantes(cantidad_total_kg, riqueza_p),
        uf_k_total=legal.unidades_fertilizantes(cantidad_total_kg, riqueza_k),
        modo_aplicacion=datos.modo_aplicacion,
        momento=datos.momento,
        plan_id=datos.plan_id,
        # Lo que pide la hoja 6 del cuaderno de la Junta: el nº de albarán de donde salió el abono y
        # de qué tipo de abonado se trata (fondo, cobertera o fertirrigación).
        numero_albaran=(datos.numero_albaran or "").strip() or None,
        tipo_fertilizacion=tipo_de_fertilizacion(datos.tipo_fertilizacion),
        factura_id=datos.factura_id,
        # Lo mismo que en los tratamientos: `None` es «no comprobado», nunca «no».
        en_zona_vulnerable=en_zona_de_nitratos(parcela),
        nitratos_agua_riego=datos.nitratos_agua_riego,
        observaciones=datos.observaciones,
    )


# Los tres tipos de abonado que distingue la hoja 6 del cuaderno de la Junta, con el nombre largo
# que se guarda. Los códigos del papel son (F), (AF) y (AC).
TIPOS_DE_FERTILIZACION = {
    "fondo": "fondo",
    "cobertera": "cobertera",
    "fertirrigacion": "fertirrigacion",
    "fertirrigación": "fertirrigacion",
    "af": "fondo",
    "ac": "cobertera",
    "f": "fertirrigacion",
}


def tipo_de_fertilizacion(valor: str | None) -> str | None:
    """El tipo de abonado, con el nombre que usa la hoja 6 del cuaderno.

    **No se inventa nada**: lo que no sea uno de los tres tipos que dice el cuaderno se queda
    vacío, en vez de guardarse tal cual y acabar en el volcado como un valor que no existe. Los
    códigos del papel (F, AF, AC) se traducen a su nombre, porque guardar la sigla haría que nadie
    supiera qué significa dentro de un año.

    Quien lo llame **antes** de guardar (el endpoint del abono) comprueba que el valor está en la
    lista y avisa si no: un tipo inventado escrito por la pantalla es un fallo del programa, no un
    dato que falte, y callarlo escondería el fallo.
    """
    limpio = (valor or "").strip().lower()
    return TIPOS_DE_FERTILIZACION.get(limpio)


# --------------------------------------------------------------------------
# El plan de abono del año
# --------------------------------------------------------------------------


def plan_que_le_toca(
    db: Session,
    *,
    explotacion_id: int,
    campana_id: int | None,
    parcela_id: int | None,
    plan_id: int | None = None,
) -> models.PlanAbonado | None:
    """Con qué plan hay que comparar un abono.

    Si el agricultor ha dicho a qué plan va, ese. Si no, **el plan de esa parcela y esa
    campaña**, porque nadie se va a acordar de enlazar cada abono a mano y el aviso de
    pasarse tiene que salir igual. Esa es toda la gracia del plan.
    """
    if plan_id is not None:
        plan = db.get(models.PlanAbonado, plan_id)
        if plan is not None and plan.explotacion_id == explotacion_id:
            return plan
        return None
    if parcela_id is None or campana_id is None:
        return None
    return db.scalar(
        select(models.PlanAbonado)
        .where(
            models.PlanAbonado.explotacion_id == explotacion_id,
            models.PlanAbonado.campana_id == campana_id,
            models.PlanAbonado.parcela_id == parcela_id,
        )
        .order_by(models.PlanAbonado.id.desc())
        .limit(1)
    )


def lo_aplicado_contra_el_plan(
    db: Session, *, explotacion_id: int, plan
) -> tuple[float, float, float, int]:
    """Lo que se lleva echado contra un plan, en kilos de nutriente por hectárea.

    Cuenta **todo lo que se ha echado en la parcela del plan**, esté enlazado o no. Un
    apunte anulado no cuenta: lo que se anuló no se echó.

    Se devuelven los tres nutrientes y cuántos apuntes son.

    **Un apunte del que no consta la composición no suma cero** (A6 de
    `docs/T02_VALORES_POR_DEFECTO.md`): se queda fuera de la suma, porque sumar `0.0` diría que no
    aportó nada y lo que pasa es que no se sabe. Quien enseña esta comparación tiene que decirlo, y
    lo dice el aviso `F9_composicion_sin_comprobar`, que sale al apuntar un abono de esa tierra.
    """
    if plan is None:
        return (0.0, 0.0, 0.0, 0)

    condiciones = [models.RegistroFertilizacion.plan_id == plan.id]
    if plan.parcela_id is not None:
        condiciones.append(
            and_(
                models.RegistroFertilizacion.parcela_id == plan.parcela_id,
                models.RegistroFertilizacion.campana_id == plan.campana_id,
            )
        )

    apuntes = list(
        db.scalars(
            select(models.RegistroFertilizacion).where(
                models.RegistroFertilizacion.explotacion_id == explotacion_id,
                or_(*condiciones),
                models.RegistroFertilizacion.anulado.is_(False),
            )
        )
    )
    return (
        round(sum(a.uf_n_ha for a in apuntes if a.uf_n_ha is not None), 4),
        round(sum(a.uf_p_ha for a in apuntes if a.uf_p_ha is not None), 4),
        round(sum(a.uf_k_ha for a in apuntes if a.uf_k_ha is not None), 4),
        len(apuntes),
    )


# --------------------------------------------------------------------------
# Analíticas
# --------------------------------------------------------------------------


def limpia_parametros(tipo: str, parametros) -> list[dict]:
    """Deja solo los números que existen de verdad para esa clase de análisis.

    Es la puerta que impide que se cuele un parámetro inventado. Si llega una clave que
    no está en el catálogo, se descarta en silencio en vez de guardarse: guardarla daría
    un cuaderno con un número que después nadie sabe interpretar. Un valor vacío o no
    numérico también se descarta, porque un boletín sin ese número no es un cero: es que
    no lo trae, y apuntar un cero sería apuntar un dato falso.

    `unidad` se copia del catálogo y no se acepta de fuera: así todos los análisis de la
    misma clase se pueden comparar entre años sin mirar si venían en las mismas unidades.
    """
    limpios: list[dict] = []
    vistas: set[str] = set()
    for parametro in parametros or []:
        if isinstance(parametro, dict):
            clave = parametro.get("clave")
            valor = parametro.get("valor")
        else:
            clave = getattr(parametro, "clave", None)
            valor = getattr(parametro, "valor", None)
        if not clave or clave in vistas:
            continue
        conocido = catalogos.parametro_de(tipo, clave)
        if conocido is None:
            continue
        if valor is None or valor == "":
            continue
        # El agricultor escribe en el móvil y ahí se pone coma: «7,4». Se acepta, porque
        # rechazarlo con un error técnico sería justo lo contrario de lo que hace falta.
        if isinstance(valor, str):
            valor = valor.strip().replace(",", ".")
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            continue
        if numero != numero:  # NaN, que llega cuando un cuadro de texto se queda en blanco
            continue
        vistas.add(clave)
        limpios.append({"clave": clave, "valor": numero, "unidad": conocido.unidad})
    return limpios


def valor_de_parametro(analitica, clave: str) -> float | None:
    """Un número concreto de un análisis, o None si ese boletín no lo trae."""
    for parametro in analitica.parametros or []:
        if isinstance(parametro, dict) and parametro.get("clave") == clave:
            valor = parametro.get("valor")
            try:
                return float(valor)
            except (TypeError, ValueError):
                return None
    return None


def preparar_analitica(datos, *, explotacion_id: int) -> models.Analitica:
    """Construye el análisis a partir de lo que manda el agricultor.

    Lo único que se toca es la lista de números, que pasa por el catálogo. El resto se
    guarda tal cual lo ha escrito: es lo que pone el boletín del laboratorio.
    """
    valores = datos.model_dump(exclude={"parametros"})
    return models.Analitica(
        explotacion_id=explotacion_id,
        **valores,
        parametros=limpia_parametros(datos.tipo, datos.parametros),
    )


def analiticas_de_una_parcela(
    db: Session, *, explotacion_id: int, parcela_id: int, tipo: str | None = None
) -> list[models.Analitica]:
    """Los análisis de una parcela, del más nuevo al más viejo. Sin los anulados."""
    consulta = select(models.Analitica).where(
        models.Analitica.explotacion_id == explotacion_id,
        models.Analitica.parcela_id == parcela_id,
        models.Analitica.anulado.is_(False),
    )
    if tipo is not None:
        consulta = consulta.where(models.Analitica.tipo == tipo)
    return list(db.scalars(consulta.order_by(models.Analitica.fecha_toma_muestra.desc())))


# --------------------------------------------------------------------------
# Medidas preventivas de la explotación
# --------------------------------------------------------------------------


def medidas_declaradas(
    db: Session, *, explotacion_id: int, solo_aplicadas: bool = False
) -> list[models.MedidaPreventivaDeclarada]:
    """Lo que el agricultor ha declarado que hace en su finca.

    Se devuelven **en el orden del catálogo** y no por identificador: el agricultor tiene
    que ver siempre las mismas diez preguntas en el mismo orden, o cada vez que entre
    creerá que le preguntan cosas distintas.
    """
    consulta = select(models.MedidaPreventivaDeclarada).where(
        models.MedidaPreventivaDeclarada.explotacion_id == explotacion_id
    )
    if solo_aplicadas:
        consulta = consulta.where(models.MedidaPreventivaDeclarada.aplicada.is_(True))
    orden = {medida.codigo: posicion for posicion, medida in enumerate(catalogos.MEDIDAS_PREVENTIVAS)}
    filas = list(db.scalars(consulta))
    return sorted(filas, key=lambda fila: orden.get(fila.medida, len(orden)))


def codigos_de_medidas_aplicadas(db: Session, *, explotacion_id: int) -> list[str]:
    """Solo los códigos de las medidas que aplica.

    Es lo que se marca por defecto al apuntar un tratamiento: casi siempre lo que se hizo
    antes de echar producto es lo que se hace siempre, así que el agricultor solo tiene
    que confirmar en vez de volver a marcar diez casillas.
    """
    return [fila.medida for fila in medidas_declaradas(db, explotacion_id=explotacion_id, solo_aplicadas=True)]


def declarar_medidas(
    db: Session,
    *,
    explotacion_id: int,
    aplicadas: list[str],
    observaciones: dict[str, str] | None = None,
) -> list[models.MedidaPreventivaDeclarada]:
    """Guarda la declaración entera de medidas preventivas de una finca.

    Se manda **la lista completa**, no un cambio suelto, porque la pantalla es una sola
    con diez casillas y un botón de guardar: si se mandara casilla a casilla, dos toques
    seguidos dejarían la declaración a medias.

    Decisión sobre las medidas que no están en la lista: **no se borran**, se quedan con
    `aplicada=False`. Así queda la historia («esto lo hacía y dejé de hacerlo») y no hay
    forma de perder un dato por desmarcar una casilla. Lo que sí se descarta es un código
    que no esté en el catálogo: guardarlo daría una medida sin nombre que no se puede
    entregar a la administración.
    """
    observaciones = observaciones or {}
    puestas = {codigo for codigo in aplicadas if catalogos.medida_de(codigo)}

    existentes = {
        fila.medida: fila
        for fila in db.scalars(
            select(models.MedidaPreventivaDeclarada).where(
                models.MedidaPreventivaDeclarada.explotacion_id == explotacion_id
            )
        )
    }

    resultado: list[models.MedidaPreventivaDeclarada] = []
    for medida in catalogos.MEDIDAS_PREVENTIVAS:
        fila = existentes.get(medida.codigo)
        aplicada = medida.codigo in puestas
        nota = (observaciones.get(medida.codigo) or "").strip() or None
        if fila is None:
            fila = models.MedidaPreventivaDeclarada(
                explotacion_id=explotacion_id,
                medida=medida.codigo,
                aplicada=aplicada,
                observaciones=nota,
            )
            db.add(fila)
        else:
            fila.aplicada = aplicada
            fila.observaciones = nota
        resultado.append(fila)

    db.add(
        models.Auditoria(
            explotacion_id=explotacion_id,
            entidad="medidas_preventivas",
            accion="declarar",
            datos={"aplicadas": sorted(puestas), "cuantas": len(puestas)},
        )
    )
    db.commit()
    return resultado


@dataclass(frozen=True)
class Nitrogeno:
    """Lo que se lleva echado en una tierra, **y lo que no se ha podido contar**.

    Existe porque un solo número no puede contar la verdad entera de este cálculo (A4 y A6 de
    `docs/T02_VALORES_POR_DEFECTO.md`). Antes esto era un `float` y el hueco se rellenaba con un
    cero: un abono apuntado en un grupo de tierras, o un abono del que no consta la composición,
    sumaban exactamente lo mismo que no haber echado nada. Aquí el hueco se declara:

      · `kg_n_ha`: los kilos de nitrógeno por hectárea que **sí** se han podido contar.
      · `apuntes`: cuántos apuntes han entrado en esa cuenta.
      · `sin_atribuir`: apuntes de un grupo de tierras de los que **no se puede saber qué tierra
        llevó qué**. No están dentro de `kg_n_ha` y quien llame tiene que decirlo.
      · `sin_composicion`: apuntes de los que **no consta la composición**, así que no se puede
        calcular lo que aportan. Tampoco están dentro del total, y tampoco se pueden callar: el
        total es una parte de lo que se echó, no todo.
    """

    kg_n_ha: float = 0.0
    apuntes: int = 0
    sin_atribuir: int = 0
    sin_composicion: int = 0

    @property
    def esta_completo(self) -> bool:
        """¿Se ha podido contar todo lo que hay apuntado en esa tierra?"""
        return not self.sin_atribuir and not self.sin_composicion


# La tolerancia al comparar la superficie de un apunte con la del grupo entero: la misma que usa
# `legal.supera_superficie` para las superficies, porque el redondeo de cuatro decimales del SIGPAC
# no puede convertir en «no cuadra» lo que es el mismo número escrito de otra forma.
TOLERANCIA_DE_SUPERFICIE = 1e-4


def _grupos_que_llevan_la_tierra(db: Session, *, explotacion_id: int, parcela_id: int):
    """Los grupos de tierras que llevan dentro esta parcela."""
    return list(
        db.scalars(
            select(models.GrupoParcelas).where(
                models.GrupoParcelas.explotacion_id == explotacion_id,
                models.GrupoParcelas.parcelas.any(models.Parcela.id == parcela_id),
            )
        )
    )


def superficie_contada_del_grupo(grupo) -> float | None:
    """La superficie sumada de las tierras de un grupo, o `None` si no se puede sumar.

    **Una suma a la que le falta un número no es una suma: es una parte.** Si alguna tierra del grupo
    no dice cuántas hectáreas tiene (A7 de `docs/T02_VALORES_POR_DEFECTO.md`), devolver la suma de
    las demás daría un total que parece bueno y no lo es, y con él se decidiría si un apunte cupo
    dentro del grupo o no. Por eso se devuelve `None` y quien llama dice que no lo ha podido
    comprobar.

    Se calcula al vuelo y no se guarda, por el mismo motivo que en `validaciones._superficie_del_grupo`:
    cambiar las tierras del grupo dejaría el número viejo mintiendo.
    """
    if grupo is None:
        return None
    parcelas = getattr(grupo, "parcelas", None) or []
    if not parcelas:
        return None
    if any(parcela.superficie_ha is None for parcela in parcelas):
        return None
    return round(sum(parcela.superficie_ha for parcela in parcelas), 4)


def _nitrogeno_en_la_tierra(
    db: Session,
    *,
    explotacion_id: int,
    parcela_id: int | None,
    campana_id: int,
    solo_organico: bool,
    sin_esta: int | None = None,
) -> Nitrogeno:
    """Lo que se lleva echado en una tierra, contando también lo que se apuntó por grupo.

    **Por qué esto cuenta los abonos de un grupo** (A4 de `docs/T02_VALORES_POR_DEFECTO.md`). Un
    abono apuntado en un grupo de tierras no lleva `parcela_id` —es lo que manda la pantalla al
    elegir el grupo—, así que hasta ahora no contaba para **ninguna** tierra, y el tope de 170 kg de
    la Orden MAV/398/2022 no saltaba aunque se pasara de verdad: el programa *creía* estar
    comprobando un límite legal y no lo comprobaba.

    **Cómo se cuenta, y por qué así y no de otra forma.** Lo que se le suma a cada tierra es la dosis
    **por hectárea** del apunte (`uf_n_ha`), nunca los kilos totales del grupo repartidos entre las
    tierras. No es un reparto: un grupo es una **unidad homogénea de cultivo** —`models.GrupoParcelas`
    dice literalmente «parcelas que se llevan igual»— y lo que se apuntó es lo que se echó **en cada
    hectárea** de ese conjunto, así que la misma cifra vale para cada tierra del grupo y se cuenta
    una sola vez en cada una. Repartir los kilos **totales** sí sería inventarse un reparto (y por eso
    aquí no se usan nunca: ni `cantidad_total_kg` ni `uf_*_total`).

    **Y cuando no se puede atribuir, se dice.** Un apunte de grupo no se le suma a la tierra cuando
    no se sabe si esa tierra lo recibió:

      · **No cuadra la superficie**: el apunte dice que se abonaron menos hectáreas que las que suma
        el grupo, así que se abonó una parte del grupo y **no se sabe cuál**. El caso normal, en
        cambio, es que cuadre: la pantalla manda la superficie entera del grupo.
      · **No se sabe la superficie del grupo**: si alguna tierra del grupo no dice cuántas hectáreas
        tiene, no hay con qué comparar (A7).

    En los dos casos el apunte se cuenta en `sin_atribuir` y el aviso lo dice, porque callar sería
    dejar creyendo que el tope se ha comprobado.

    Un apunte que lleva **grupo y tierra a la vez** cuenta como de la tierra: el agricultor dijo
    dónde, y contarlo además como de grupo lo contaría dos veces.
    """
    if parcela_id is None:
        # Un apunte que se está apuntando sobre un grupo entero: aquí no hay una tierra de la que
        # hablar. Quien comprueba eso dice que no lo ha podido comprobar (ver `_reglas_de_nitratos`).
        return Nitrogeno()

    def de_esta_cantidad(registro) -> bool:
        return solo_organico is False or catalogos.es_abono_organico(registro.tipo)

    def sin_excluir(registro) -> bool:
        return sin_esta is None or registro.id != sin_esta

    resultado = Nitrogeno()

    def suma(registro, aporte_por_hectarea) -> None:
        nonlocal resultado
        if aporte_por_hectarea is None:
            # No consta la composición (A6). No es un cero: es un hueco, y se declara.
            resultado = Nitrogeno(
                resultado.kg_n_ha,
                resultado.apuntes + 1,
                resultado.sin_atribuir,
                resultado.sin_composicion + 1,
            )
            return
        resultado = Nitrogeno(
            round(resultado.kg_n_ha + aporte_por_hectarea, 4),
            resultado.apuntes + 1,
            resultado.sin_atribuir,
            resultado.sin_composicion,
        )

    def sin_atribuir_uno() -> None:
        nonlocal resultado
        resultado = Nitrogeno(
            resultado.kg_n_ha,
            resultado.apuntes,
            resultado.sin_atribuir + 1,
            resultado.sin_composicion,
        )

    # --- lo que se apuntó en esta tierra ---
    suyos = db.scalars(
        select(models.RegistroFertilizacion).where(
            models.RegistroFertilizacion.explotacion_id == explotacion_id,
            models.RegistroFertilizacion.parcela_id == parcela_id,
            models.RegistroFertilizacion.campana_id == campana_id,
            models.RegistroFertilizacion.anulado.is_(False),
        )
    )
    for registro in suyos:
        if sin_excluir(registro) and de_esta_cantidad(registro):
            suma(registro, registro.uf_n_ha)

    # --- y lo que se apuntó en un grupo que lleva esta tierra ---
    for grupo in _grupos_que_llevan_la_tierra(
        db, explotacion_id=explotacion_id, parcela_id=parcela_id
    ):
        superficie_del_grupo = superficie_contada_del_grupo(grupo)
        del_grupo = db.scalars(
            select(models.RegistroFertilizacion).where(
                models.RegistroFertilizacion.explotacion_id == explotacion_id,
                models.RegistroFertilizacion.grupo_id == grupo.id,
                # Un apunte con grupo **y** tierra ya ha contado arriba, como de la tierra.
                models.RegistroFertilizacion.parcela_id.is_(None),
                models.RegistroFertilizacion.campana_id == campana_id,
                models.RegistroFertilizacion.anulado.is_(False),
            )
        )
        for registro in del_grupo:
            if not sin_excluir(registro) or not de_esta_cantidad(registro):
                continue
            if superficie_del_grupo is None or abs(
                registro.superficie_ha - superficie_del_grupo
            ) > TOLERANCIA_DE_SUPERFICIE:
                sin_atribuir_uno()
                continue
            suma(registro, registro.uf_n_ha)

    return resultado


def nitrogeno_organico_en_la_parcela(
    db: Session, *, explotacion_id: int, parcela_id: int | None, campana_id: int, sin_esta: int | None = None
) -> Nitrogeno:
    """Los kilos de nitrógeno por hectárea que ya se han echado como estiércol o purín.

    Es lo que hace falta para poder comprobar la regla de los 170 kg de la Orden
    MAV/398/2022. Se cuentan **solo los abonos orgánicos y órgano-minerales**: los de fábrica
    (minerales) no entran en esa regla.

    Se suman los aportes por hectárea de todos los apuntes del año en esa parcela. Es una
    aproximación, y conviene decir por qué: si un agricultor abona media parcela en marzo y la
    otra media en octubre, cada apunte dice los kilos por hectárea **de la parte que abonó**, y
    sumarlos da el total del año en el conjunto. Que es justo lo que mide la norma.

    Los apuntes anulados no cuentan: lo que se anuló no se echó. Y **lo que se apuntó en un grupo
    del que forma parte esta tierra sí cuenta**, con el porqué escrito en `_nitrogeno_en_la_tierra`.
    Devuelve un `Nitrogeno` y no un número porque hay aportes que no se pueden atribuir y hay que
    poder decirlo (ver `Nitrogeno`).
    """
    return _nitrogeno_en_la_tierra(
        db,
        explotacion_id=explotacion_id,
        parcela_id=parcela_id,
        campana_id=campana_id,
        solo_organico=True,
        sin_esta=sin_esta,
    )


def nitrogeno_aplicado_en_la_parcela(
    db: Session, *, explotacion_id: int, parcela_id: int | None, campana_id: int, sin_esta: int | None = None
) -> Nitrogeno:
    """Todo el nitrógeno por hectárea apuntado en esa parcela en el año, sea del tipo que sea.

    Es lo que se compara con el plan de abono, que sí cuenta los tres nutrientes de cualquier
    origen. Mismo criterio que `nitrogeno_organico_en_la_parcela` para los grupos y para la
    composición desconocida.
    """
    return _nitrogeno_en_la_tierra(
        db,
        explotacion_id=explotacion_id,
        parcela_id=parcela_id,
        campana_id=campana_id,
        solo_organico=False,
        sin_esta=sin_esta,
    )


# --------------------------------------------------------------------------
# Lo que se vende
# --------------------------------------------------------------------------


def clave_de_producto(nombre: str | None) -> str:
    """El nombre de un producto, en una forma que se pueda comparar.

    «Trigo blando», «TRIGO BLANDO» y «trigo  blando» son lo mismo, y el agricultor los
    escribirá de las tres maneras. Sin esto, dos apuntes del mismo producto no se podrían
    reconocer nunca.
    """
    if not nombre:
        return ""
    return " ".join(borradores.sin_tildes(nombre).lower().split())


def lo_cosechado_en_la_campana(db: Session, *, explotacion_id: int, campana_id: int) -> float:
    """Los kilos que se ha apuntado que se cogieron en la campaña.

    Se leen de las labores de tipo cosecha, que es donde los guarda `/api/cosecha`
    (`detalles = {producto, cantidad_kg}`). Se cuentan **en total y no por producto** a
    propósito: el apunte de la cosecha no siempre dice de qué producto es, así que comparar
    por producto daría por buenos casos que no lo son.

    Las labores anuladas no cuentan: lo que se anuló no se cogió.
    """
    total = 0.0
    for labor in db.scalars(
        select(models.Labor).where(
            models.Labor.explotacion_id == explotacion_id,
            models.Labor.campana_id == campana_id,
            models.Labor.tipo == "cosecha",
            models.Labor.anulado.is_(False),
        )
    ):
        detalles = labor.detalles or {}
        cantidad = detalles.get("cantidad_kg")
        try:
            total += float(cantidad)
        except (TypeError, ValueError):
            continue
    return round(total, 4)


def lo_vendido_en_la_campana(
    db: Session, *, explotacion_id: int, campana_id: int, sin_esta: int | None = None
) -> tuple[float, int]:
    """Los kilos vendidos en la campaña, y cuántas ventas son.

    Solo se suman las ventas cuya unidad se puede pasar a kilos. Las que van en unidades
    (lechugas, por ejemplo) **no se pueden sumar con kilos** y se quedan fuera del total: es
    mejor un total que significa algo que uno que mezcla peras con manzanas. Esas ventas
    siguen contando en `cuantas`, que es lo que se enseña aparte.

    `sin_esta` deja fuera una venta concreta: sirve para comprobar una venta contra el resto
    sin contarla dos veces al corregirla.
    """
    total = 0.0
    cuantas = 0
    for venta in db.scalars(
        select(models.VentaDeCosecha).where(
            models.VentaDeCosecha.explotacion_id == explotacion_id,
            models.VentaDeCosecha.campana_id == campana_id,
            models.VentaDeCosecha.anulado.is_(False),
        )
    ):
        if sin_esta is not None and venta.id == sin_esta:
            continue
        cuantas += 1
        kilos = catalogos.kilos_de_una_venta(venta.cantidad, venta.unidad)
        if kilos is not None:
            total += kilos
    return (round(total, 4), cuantas)


def resumen_de_ventas(
    db: Session, *, explotacion_id: int, campana_id: int
) -> dict[str, float | int]:
    """Lo vendido y lo cosechado en la campaña, para el informe y para los avisos."""
    vendido, cuantas = lo_vendido_en_la_campana(
        db, explotacion_id=explotacion_id, campana_id=campana_id
    )
    cosechado = lo_cosechado_en_la_campana(
        db, explotacion_id=explotacion_id, campana_id=campana_id
    )
    return {
        "vendido_kg": vendido,
        "cosechado_kg": cosechado,
        "ventas": cuantas,
        "queda_kg": round(cosechado - vendido, 4),
    }


# --------------------------------------------------------------------------
# La cesta de la compra: cuánto producto entró y cuánto ha salido
#
# La app oficial de la Junta tiene el apartado «Cesta de la compra» para anotar la *adquisición*
# de productos fitosanitarios, y un botón «Situación Cesta» que enseña «las cantidades adquiridas
# y gastadas de los distintos productos fitosanitarios utilizados en la campaña».
#
# Aquí faltaba la mitad: el producto se daba de alta con su número de registro y su dosis, y los
# campos de la compra (`cantidad_comprada`, `unidad_compra`, `fecha_compra`, `proveedor`) estaban
# en la tabla **y no los usaba nadie**. O sea que no se podía contestar a «¿me queda producto
# para tratar esta parcela?», que es la pregunta que se hace de verdad, ni al libro de movimientos
# que mira una inspección.
#
# Lo que hay que tener claro al leer esto: **restar no siempre se puede**. Un producto se compra
# en litros y se echa con una dosis en «kg/ha». Cuando las unidades no son de la misma familia,
# NO se resta: se dice que no se puede comparar. Ver `legal.se_pueden_comparar`.
# --------------------------------------------------------------------------


def lo_gastado_de_un_producto(
    db: Session, *, explotacion_id: int, producto_id: int, campana_id: int | None
) -> tuple[float, int]:
    """Cuánto producto se ha echado y en cuántos apuntes.

    Se suman los totales de los tratamientos de ese producto. `cantidad_total` ya viene en la
    unidad que se echa (litros, kilos, mililitros o gramos), porque se calculó como dosis por
    hectáreas tratadas al apuntar.
    """
    consulta = select(models.TratamientoFitosanitario).where(
        models.TratamientoFitosanitario.explotacion_id == explotacion_id,
        models.TratamientoFitosanitario.producto_id == producto_id,
        models.TratamientoFitosanitario.anulado.is_(False),
    )
    if campana_id is not None:
        consulta = consulta.where(models.TratamientoFitosanitario.campana_id == campana_id)
    tratamientos = list(db.scalars(consulta))
    total = sum(
        tratamiento.cantidad_total
        for tratamiento in tratamientos
        if tratamiento.cantidad_total is not None
    )
    return round(total, 4), len(tratamientos)


def cultivo_precedente(db: Session, explotacion, plan) -> str | None:
    """Qué había sembrado en esa parcela la campaña anterior.

    **Se calcula, no se guarda.** El anexo II pide, en el plan de abono, el cultivo precedente, y el
    programa ya sabe cuál era: cada campaña tiene sus cultivos declarados por parcela. Deducirlo de
    ahí es mejor que preguntarlo otra vez, porque el agricultor no tiene por qué acordarse y porque
    un dato guardado se queda viejo el día que corrija el historial.

    `None` cuando no hay campaña anterior, cuando el plan es de un grupo de parcelas o cuando aquel
    año no se declaró nada: las tres cosas son «no lo sé», no «no había nada».

    Está aquí y no en el enrutador del plan porque lo usan **dos sitios**: la pantalla del plan (que
    lo enseña) y el cuaderno de la Junta (que lo escribe en su hoja 9.1.2). Con dos copias, un día
    una de las dos diría otra cosa.
    """
    if plan.parcela_id is None or plan.campana_id is None:
        return None
    campana = db.get(models.Campana, plan.campana_id)
    if campana is None:
        return None
    anterior = db.scalar(
        select(models.Campana)
        .where(
            models.Campana.explotacion_id == explotacion.id,
            models.Campana.anio < campana.anio,
        )
        .order_by(models.Campana.anio.desc())
        .limit(1)
    )
    if anterior is None:
        return None
    declarado = cultivo_declarado(
        db,
        explotacion_id=explotacion.id,
        parcela_id=plan.parcela_id,
        campana_id=anterior.id,
    )
    return declarado.especie if declarado is not None else None


def comprado_de_un_producto(
    db: Session,
    *,
    explotacion_id: int,
    producto: models.ProductoFitosanitario,
    excluyendo_factura_id: int | None = None,
) -> tuple[float | None, str, list[dict], str]:
    """Cuánto se ha comprado de este producto, y de dónde sale ese número.

    Devuelve `(cantidad, de_donde, compras, motivo)`:

    * **`de_donde`** es `"facturas"` si el número sale de las facturas apuntadas, `"ficha"` si sale
      del dato que el agricultor escribió a mano en la ficha del producto, y `""` si no hay nada.
    * **`compras`** es el detalle de las líneas de factura (proveedor, número, fecha, cantidad,
      unidad e importe). Es lo que hay que poder enseñar cuando alguien pregunta de dónde salió.
    * **`motivo`** dice, en palabras, por qué no se ha podido sumar cuando no se ha podido.

    **Las facturas mandan sobre la ficha**, y esto es una decisión que conviene entender: la ficha
    del producto tiene un solo número («compré 20 litros») y una factura tiene líneas con fecha, con
    proveedor y con número. Si hay facturas, ese número viejo de la ficha ya no vale y sumar los dos
    contaría la misma compra dos veces. Si no hay facturas, se usa el de la ficha, que es lo que hay.

    Y cuando las unidades no se pueden comparar —comprado en «botes» y el producto llevado en
    litros— **no se suma nada**: se dice por qué. Es la misma regla que sigue el resto del programa:
    es mejor no contestar que contestar mal.

    `excluyendo_factura_id` responde a **«¿qué diría la cesta si esa factura no estuviera?»**, y lo
    usa el borrado de una factura (`facturas_api.borrar_factura`) para no dejar el cuadre contando lo
    que se echó sin la compra que lo sostenía. Se recorre el mismo camino que cuando la factura no
    existe de verdad —incluida la vuelta a la cifra de la ficha del producto—, que es lo que hace que
    la respuesta sea la de verdad y no una parecida.
    """
    consulta = (
        select(models.LineaDeFactura)
        .join(models.Factura, models.Factura.id == models.LineaDeFactura.factura_id)
        .where(
            models.LineaDeFactura.explotacion_id == explotacion_id,
            models.LineaDeFactura.producto_id == producto.id,
            models.Factura.anulada.is_(False),
        )
    )
    if excluyendo_factura_id is not None:
        consulta = consulta.where(models.LineaDeFactura.factura_id != excluyendo_factura_id)
    lineas = list(db.scalars(consulta.order_by(models.Factura.fecha)))
    if not lineas:
        if producto.cantidad_comprada is None:
            return None, "", [], ""
        return producto.cantidad_comprada, "ficha", [], ""

    unidad_del_producto = (producto.unidad_compra or "").strip()
    compras: list[dict] = []
    total = 0.0
    cuantas_cuentan = 0
    unidades_distintas: set[str] = set()
    for linea in lineas:
        factura = linea.factura
        compras.append(
            {
                "factura_id": factura.id,
                "proveedor": factura.proveedor or "",
                "numero_factura": factura.numero_factura or "",
                "fecha": factura.fecha,
                "cantidad": linea.cantidad,
                "unidad": linea.unidad or "",
                "importe": linea.importe,
                "descripcion": linea.descripcion,
            }
        )
        if linea.cantidad is None:
            continue
        if legal.se_pueden_comparar(linea.unidad or "", unidad_del_producto):
            convertida = legal.convierte(linea.cantidad, linea.unidad or "", unidad_del_producto)
            if convertida is not None:
                total += convertida
                cuantas_cuentan += 1
                continue
        unidades_distintas.add((linea.unidad or "?").strip() or "?")

    if not cuantas_cuentan:
        motivo = textos.MENSAJES["A21_unidades_distintas"].format(
            comprado=", ".join(sorted(unidades_distintas)) or "?",
            gastado=unidad_del_producto or "?",
        )
        return None, "facturas", compras, motivo
    return round(total, 4), "facturas", compras, ""


def lo_que_queda_de_un_producto(
    comprado: float | None, gastado: float, unidad_compra: str | None, unidad_gastado: str | None
) -> tuple[bool, float | None]:
    """Cuánto queda de un producto, y si las dos unidades se pueden comparar para saberlo.

    Devuelve `(se_puede_comparar, queda)`. `queda` es `None` cuando no se puede restar —unidades de
    familias distintas, o no se sabe cuánto se compró—, que es la respuesta honesta: el programa
    prefiere no contestar a inventarse un número (`legal.se_pueden_comparar`).

    **Está aquí, y no dentro de la pantalla de la cesta, porque la cuenta la hacen dos sitios**: la
    cesta que ve el agricultor (`situacion_de_la_cesta`) y el borrado de una factura, que necesita
    saber qué diría la cesta **si esa factura no estuviera** antes de dejar que se borre
    (`facturas_api.borrar_factura`). Con dos copias, un día una de las dos diría otra cosa.
    """
    comparable = legal.se_pueden_comparar(unidad_compra, unidad_gastado)
    if not comparable or comprado is None:
        return comparable, None
    gastado_en_la_unidad = legal.convierte(gastado, unidad_gastado, unidad_compra)
    if gastado_en_la_unidad is None:
        return comparable, None
    return comparable, round(comprado - gastado_en_la_unidad, 4)


def comprado_por_producto(db: Session, *, explotacion_id: int) -> list[dict]:
    """Lo comprado de cada producto, con las facturas de donde sale. El cuadre de las compras.

    Es la mitad de la pregunta «¿cuadra lo que he comprado con lo que he echado?»: aquí está lo
    comprado con su factura, y en `/api/cesta` está lo echado con su apunte. Las dos cosas juntas
    son lo que mira una inspección.
    """
    productos = list(
        db.scalars(
            select(models.ProductoFitosanitario)
            .where(models.ProductoFitosanitario.explotacion_id == explotacion_id)
            .order_by(models.ProductoFitosanitario.nombre_comercial)
        )
    )
    devuelto: list[dict] = []
    for producto in productos:
        comprado, de_donde, compras, motivo = comprado_de_un_producto(
            db, explotacion_id=explotacion_id, producto=producto
        )
        if not compras and comprado is None:
            continue
        devuelto.append(
            {
                "producto_id": producto.id,
                "nombre_comercial": producto.nombre_comercial,
                "numero_registro": producto.numero_registro,
                "unidad_compra": (producto.unidad_compra or "").strip(),
                "comprado": comprado,
                "de_donde": de_donde,
                "compras": compras,
                "motivo": motivo,
            }
        )
    return devuelto


def situacion_de_la_cesta(
    db: Session, *, explotacion_id: int, campana_id: int | None
) -> list[dict]:
    """Cada producto, con lo que se compró, lo que se ha echado y lo que queda.

    Devuelve las cuentas **y las explicaciones**: por qué no se puede comparar un producto, o por
    qué sale que se ha gastado más de lo que se compró. Eso último no es una acusación: lo normal
    es que el producto venga de la campaña anterior, y el aviso lo dice.
    """
    productos = list(
        db.scalars(
            select(models.ProductoFitosanitario)
            .where(models.ProductoFitosanitario.explotacion_id == explotacion_id)
            .order_by(models.ProductoFitosanitario.nombre_comercial)
        )
    )
    situacion: list[dict] = []
    for producto in productos:
        gastado, apuntes = lo_gastado_de_un_producto(
            db, explotacion_id=explotacion_id, producto_id=producto.id, campana_id=campana_id
        )
        gastado_en_total, apuntes_en_total = lo_gastado_de_un_producto(
            db, explotacion_id=explotacion_id, producto_id=producto.id, campana_id=None
        )
        unidad_compra = (producto.unidad_compra or "").strip()
        unidad_gastado = legal.unidad_de_una_dosis(
            # La unidad de lo que se echa se saca de la dosis del producto. Si el producto no
            # tiene dosis puesta, no hay nada de donde sacarla y se dice.
            producto.unidad_dosis
        )
        # Lo comprado sale de las **facturas** si las hay, y si no, del número que el agricultor
        # escribió en la ficha del producto. Ver `comprado_de_un_producto`.
        comprado, de_donde, compras, motivo_de_lo_comprado = comprado_de_un_producto(
            db, explotacion_id=explotacion_id, producto=producto
        )
        comparable, queda = lo_que_queda_de_un_producto(
            comprado, gastado, unidad_compra, unidad_gastado
        )

        motivo = ""
        if comprado is None:
            # Si no se ha podido sumar porque las unidades de la factura no son comparables, se dice
            # eso, que es más útil que «no has apuntado cuánto compraste».
            motivo = motivo_de_lo_comprado or textos.MENSAJES["A20_sin_cantidad_comprada"]
        elif not comparable:
            motivo = textos.MENSAJES["A21_unidades_distintas"].format(
                comprado=unidad_compra or "?", gastado=unidad_gastado or "?"
            )
        elif queda is not None and queda < 0:
            motivo = textos.MENSAJES["A22_gastado_mas_que_comprado"]
            if apuntes_en_total > apuntes:
                motivo += " " + textos.MENSAJES["A23_de_otra_campana"]

        situacion.append(
            {
                "producto_id": producto.id,
                "nombre_comercial": producto.nombre_comercial,
                "numero_registro": producto.numero_registro,
                "materia_activa": producto.materia_activa,
                "fecha_compra": producto.fecha_compra,
                "proveedor": producto.proveedor,
                "unidad_compra": unidad_compra,
                "unidad_gastado": unidad_gastado,
                "comprado": comprado,
                # De dónde sale el «comprado»: de las facturas apuntadas o de la ficha del
                # producto. Se enseña en la pantalla, porque un número sin su origen no se puede
                # comprobar.
                "comprado_de_donde": de_donde,
                "compras": compras,
                "gastado": gastado,
                "apuntes": apuntes,
                "gastado_en_total": gastado_en_total,
                "queda": queda,
                "se_puede_comparar": comparable,
                "motivo": motivo,
                "producto": producto,
            }
        )
    return situacion


# --------------------------------------------------------------------------
# El libro de movimientos del almacén (T09, 03/10/2026)
#
# ## Cómo convive esto con la cesta, que es lo que de verdad importa aquí
#
# La cesta (`situacion_de_la_cesta`, ahí arriba) **no se ha tocado y sigue diciendo lo mismo**: lo
# comprado sale de las líneas de las facturas y lo gastado de los tratamientos, y la resta se hace
# cada vez que se mira. Todas las cuentas de la pantalla del almacén siguen saliendo de ahí.
#
# Este libro es **otra cosa**: lo que entró de verdad (el albarán), en qué lote, y lo que salió con
# su apunte detrás. Y la regla que hace que las dos vistas puedan existir sin mentir es esta:
#
#   **no se suman nunca.** El saldo del libro se calcula solo con movimientos; la cesta, solo con
#   facturas y tratamientos. Si alguien sumara las dos, cada litro comprado contaría dos veces —una
#   por la factura y otra por la entrada—, que es exactamente el fallo que el encargo prohíbe. Hay
#   una prueba que fija las dos mitades: que recibir un albarán **no cambia ni un número de la
#   cesta**, y que el saldo del libro sale solo de movimientos.
#
# Y una consecuencia que se dice en la pantalla en vez de esconderse: un agricultor que tenga
# facturas apuntadas y ningún albarán recibido verá su almacén vacío en esta vista. **No es que se
# hayan perdido sus existencias**: es que las facturas no meten mercancía, la mete el albarán. Eso
# lo dice `existencias_del_almacen` con `facturas_sin_recibir`.
#
# ## Lo que se puede restar y lo que no
#
# Un litro y un kilo **no se restan** (hace falta la densidad, que no sabemos), y una cantidad sin
# unidad no se resta de nada. Cuando no se puede, la respuesta es «no se puede saber» con su motivo:
# nunca un número inventado y nunca un cero, que diría que no queda producto.
# --------------------------------------------------------------------------

# Las cuatro cosas que pueden pasar en un almacén. Ver `models.MovimientoDeExistencias`.
TIPOS_DE_MOVIMIENTO = ("entrada", "salida", "merma", "ajuste")
# Y de dónde viene cada uno. `manual` es «lo apunta una persona porque pasó algo que no está en
# ningún papel»: una entrada sin factura, una merma, un conteo.
#
# **`siembra` no está en esta lista a propósito** (T10, 03/10/2026). Esta tupla es lo que la puerta de
# los movimientos a mano (`POST /api/almacen/movimientos`) acepta como `origen_tipo`, y una persona no
# puede decir «es que viene de una siembra»: eso lo pone el programa cuando la siembra descuenta por
# la puerta de las salidas (`POST /api/almacen/salidas`, que **no** mira esta lista). Añadirlo aquí
# dejaría apuntar una salida a mano diciendo que viene de una siembra, que es justo la segunda forma
# de restar que el ticket prohíbe. El origen `siembra` existe en el libro —`estado_de_los_origenes` lo
# conoce— pero solo lo escribe el camino de la siembra.
ORIGENES_DE_UN_MOVIMIENTO = ("recepcion", "tratamiento", "fertilizacion", "factura", "manual")
# Los apuntes del cuaderno que gastan producto. Son los únicos que pueden sostener una salida.
#
# **La siembra entra aquí en el T10 (03/10/2026)**, y entra por el mismo motivo que el tratamiento y
# el abono: la semilla que se siembra sale del almacén, y lo que sale tiene que venir de un apunte
# para poder comprobarse y, sobre todo, **revertirse**. Sin esto habría que restar la semilla por
# otra puerta, y un almacén con dos formas de descontar es un almacén que un día no cuadra.
APUNTES_QUE_GASTAN = ("tratamiento", "fertilizacion", "siembra", "labor")
# Las cuatro pestañas del almacén (contrato §4 y la pantalla S08: «productos de tratamiento, abonos,
# semillas y otros insumos»). Las etiquetas que lee el agricultor están en `textos.ALMACEN`; aquí
# viven los códigos, que es lo que se guarda.
CATEGORIAS_DE_ARTICULO = ("fitosanitario", "abono", "semilla", "otros")


def categoria_valida(valor: str | None) -> str:
    """La categoría de un artículo, o «otros» si no es ninguna de las que hay.

    No se rechaza una categoría desconocida: se guarda como «otras cosas». El agricultor no pierde
    nada —su producto sigue en el almacén y se puede usar— y la lista de las cuatro clases no se
    llena de valores sueltos que después nadie sabe de dónde salieron.
    """
    limpio = (valor or "").strip().lower()
    return limpio if limpio in CATEGORIAS_DE_ARTICULO else "otros"


def normaliza_para_comparar(texto: str | None) -> str:
    """Un texto en la forma en la que se compara: sin tildes, sin mayúsculas y sin espacios de más.

    Se usa para reconocer **el mismo albarán** apuntado dos veces. «Cooperativa Agrícola» y
    «COOPERATIVA AGRICOLA  » son el mismo proveedor, y si se compararan tal cual, el mismo albarán
    entraría dos veces en el almacén: justo lo que hay que impedir.

    Lo que **no** hace: adivinar. No quita guiones ni ceros a la izquierda del número, porque
    «A-123» y «A123» pueden ser dos albaranes distintos de verdad y unirlos sería peor que no unirlos.
    """
    if not texto:
        return ""
    sin_tildes = "".join(
        letra
        for letra in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(letra) != "Mn"
    )
    return " ".join(sin_tildes.split()).strip().upper()


def clave_de_un_albaran(
    proveedor: str | None, proveedor_nif: str | None, numero_albaran: str | None
) -> str | None:
    """La clave con la que se reconoce un albarán ya apuntado, o `None` si no se puede reconocer.

    Son **el proveedor y el número**, y nada más. El número solo no vale: dos proveedores distintos
    numeran sus albaranes como quieren y el «1234» de uno no es el del otro. Y si falta cualquiera de
    los dos, la respuesta es `None` —«no se puede comprobar»—, que **no** es lo mismo que «no estaba»:
    cuando no se puede comprobar, el programa lo dice en vez de dar por bueno que no hay duplicado.

    Del proveedor se usa el NIF si está (identifica sin lugar a dudas) y si no el nombre. Para
    comparar dos papeles hay que usar `el_mismo_albaran`, porque lo normal es que el NIF venga en uno
    y no en el otro.
    """
    numero = normaliza_para_comparar(numero_albaran)
    if not numero:
        return None
    quien = normaliza_para_comparar(proveedor_nif) or normaliza_para_comparar(proveedor)
    if not quien:
        return None
    return f"{quien}|{numero}"


def el_mismo_albaran(
    *,
    proveedor: str | None,
    proveedor_nif: str | None,
    numero_albaran: str | None,
    otro_proveedor: str | None,
    otro_proveedor_nif: str | None,
    otro_numero_albaran: str | None,
) -> bool:
    """¿Estos dos papeles son el mismo albarán? Es lo que impide meterlo dos veces.

    El número tiene que coincidir, y después el proveedor. Y aquí está el detalle que importa: **el
    NIF viene en un papel y no en el otro** —la mitad de los albaranes solo traen el nombre—, así que
    comparar «NIF o nombre» a secas no reconocería el mismo albarán apuntado dos veces, que es
    exactamente el fallo que hay que evitar. Se comparan las dos cosas que se puedan comparar:

      · Si los dos papeles traen NIF: manda el NIF, aunque el nombre esté escrito de otra manera.
      · Si solo uno lo trae: se comparan los nombres.
      · Si no se puede comparar nada (uno solo trae nombre y el otro solo NIF), **se dan por el
        mismo**: en la duda, no duplicar es lo que protege el almacén, y deshacerlo es tan fácil como
        anular y volver a apuntar.
    """
    if normaliza_para_comparar(numero_albaran) != normaliza_para_comparar(otro_numero_albaran):
        return False
    if not normaliza_para_comparar(numero_albaran):
        return False
    nombre = normaliza_para_comparar(proveedor)
    otro_nombre = normaliza_para_comparar(otro_proveedor)
    nif = normaliza_para_comparar(proveedor_nif)
    otro_nif = normaliza_para_comparar(otro_proveedor_nif)
    if nif and otro_nif:
        return nif == otro_nif
    if nombre and otro_nombre:
        return nombre == otro_nombre
    return True


def clave_de_una_factura(
    proveedor: str | None, proveedor_nif: str | None, numero_factura: str | None
) -> str | None:
    """La clave con la que se reconoce una factura ya apuntada, o `None` si no se puede reconocer.

    Es la misma regla que `clave_de_un_albaran`, y por el mismo motivo: **el proveedor y el número**,
    y nada más. El número solo no vale —dos proveedores numeran como quieren— y si falta cualquiera de
    los dos la respuesta es `None`, que es «no se puede comprobar» y **no** es «no estaba». Cuando no
    se puede comprobar, el programa lo dice (`AL27…`) en vez de dar por bueno que no hay duplicado.

    Para comparar dos facturas de verdad hay que usar `el_misma_factura`, porque lo normal es que el
    NIF venga en una y no en la otra.
    """
    numero = normaliza_para_comparar(numero_factura)
    if not numero:
        return None
    quien = normaliza_para_comparar(proveedor_nif) or normaliza_para_comparar(proveedor)
    if not quien:
        return None
    return f"{quien}|{numero}"


def el_misma_factura(
    *,
    proveedor: str | None,
    proveedor_nif: str | None,
    numero_factura: str | None,
    fecha: dt.date | None = None,
    total: float | None = None,
    otro_proveedor: str | None,
    otro_proveedor_nif: str | None,
    otro_numero_factura: str | None,
    otra_fecha: dt.date | None = None,
    otro_total: float | None = None,
) -> bool:
    """¿Estas dos facturas son **el mismo papel**? Es lo que separa el reenvío del duplicado.

    El contrato (§ S10) dice que el posible duplicado se reconoce **por emisor, número, fecha y
    total**, y que el duplicado exacto se reconoce por la huella. Aquí se hace la parte del papel,
    con las mismas precauciones que `el_mismo_albaran` y una más:

      · **El número y el proveedor**, como en los albaranes: el NIF manda cuando los dos lo traen, si
        solo uno lo trae se comparan los nombres, y si no se puede comparar nada **se dan por el
        mismo**: en la duda, no duplicar es lo que protege las cuentas.
      · **El año, no el día.** Es el año lo que hace que dos «1234» sean distintos —las numeraciones
        se reinician—, y el día es justo el campo que más se equivoca al leer una foto. Dos facturas
        del mismo proveedor, con el mismo número, en el mismo año y por el mismo dinero son el mismo
        papel; si el día baila, es que una de las dos está mal apuntada, y eso se dice (`AL28…`) en
        vez de apuntar dos veces.
      · **El total**, y solo si lo traen las dos: sin total no se puede comparar, y entonces **no se
        usa como excusa para duplicar**.
    """
    if normaliza_para_comparar(numero_factura) != normaliza_para_comparar(otro_numero_factura):
        return False
    if not normaliza_para_comparar(numero_factura):
        return False

    nombre = normaliza_para_comparar(proveedor)
    otro_nombre = normaliza_para_comparar(otro_proveedor)
    nif = normaliza_para_comparar(proveedor_nif)
    otro_nif = normaliza_para_comparar(otro_proveedor_nif)
    if nif and otro_nif:
        if nif != otro_nif:
            return False
    elif nombre and otro_nombre:
        if nombre != otro_nombre:
            return False
    # Y si no se puede comparar el proveedor (uno trae solo nombre y el otro solo NIF), se dan por el
    # mismo, como en los albaranes.

    if fecha is not None and otra_fecha is not None and fecha.year != otra_fecha.year:
        return False
    if total is not None and otro_total is not None and abs(total - otro_total) >= 0.005:
        return False
    return True


def _la_huella_de(partes: dict) -> str:
    """El resumen, en una huella: `sha256` del texto canónico de esos datos.

    Canónico quiere decir **el mismo para los mismos datos**: las claves ordenadas, sin espacios de más y
    sin escapar los acentos, para que dos cuerpos que dicen lo mismo den la misma huella y uno que cambia
    un céntimo dé otra.
    """
    import hashlib
    import json as _json

    texto = _json.dumps(partes, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _el_importe_de_una_huella(valor):
    """Un número, en texto, para que entre en la huella: `663.0` y `"663.00"` son lo mismo."""
    return dinero.a_texto(dinero.cantidad_a_decimal(valor))


def _la_fecha_de_una_huella(valor):
    """Una fecha, en texto `AAAA-MM-DD`, venga como `date` o como el texto que devuelve SQLite."""
    if valor is None:
        return None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)[:10]


def _las_partes_de_una_factura(
    *,
    fecha,
    proveedor,
    proveedor_nif,
    numero_factura,
    base_imponible,
    cuota_iva,
    tipo_iva_pct,
    total,
    notas,
    lineas,
) -> dict:
    """Los datos de una factura que entran en la huella del comando, normalizados.

    **Lo que NO entra, y es a propósito** (09/10/2026): ni el `producto_id` ni el `fertilizante_id` de las
    líneas. Esos los puede **inferir el servidor** al guardar (`_producto_de_la_factura` engancha la línea
    con un producto de la cesta a partir del número de registro o del nombre), así que no forman parte de
    lo que dice la petición: si entraran, la huella de la petición y la de lo guardado **no coincidirían**
    y el reenvío del comando original daría un conflicto falso —que es justo lo que la huella viene a
    arreglar—. Lo que entra es lo que dice el papel: la fecha, quién, el número, los importes y las líneas
    con su descripción, cantidad, unidad, precio e importe.
    """
    return {
        "fecha": _la_fecha_de_una_huella(fecha),
        "proveedor": (proveedor or "").strip(),
        "proveedor_nif": (proveedor_nif or "").strip(),
        "numero_factura": (numero_factura or "").strip(),
        "base_imponible": _el_importe_de_una_huella(base_imponible),
        "cuota_iva": _el_importe_de_una_huella(cuota_iva),
        "tipo_iva_pct": _el_importe_de_una_huella(tipo_iva_pct),
        "total": _el_importe_de_una_huella(total),
        "notas": (notas or "").strip(),
        "lineas": [
            {
                "descripcion": (linea.get("descripcion") or "").strip(),
                "cantidad": _el_importe_de_una_huella(linea.get("cantidad")),
                "unidad": (linea.get("unidad") or "").strip(),
                "precio_unitario": _el_importe_de_una_huella(linea.get("precio_unitario")),
                "importe": _el_importe_de_una_huella(linea.get("importe")),
                "numero_registro": (linea.get("numero_registro") or "").strip(),
                "lote": (linea.get("lote") or "").strip(),
            }
            for linea in lineas
        ],
    }


def clave_del_papel_de_una_factura(
    proveedor: str | None,
    proveedor_nif: str | None,
    numero_factura: str | None,
    fecha,
    total,
) -> str | None:
    """Lo que identifica a **este documento**: de quién es, su número, su año y su total. O `None`.

    Es la clave con la que **la base** impide que el mismo papel entre dos veces (el índice único
    `uq_factura_papel`), y sale de los cuatro campos que el contrato §S10 nombra para el posible
    duplicado comercial: *«por emisor/número/fecha/total»*. Se calcula con la misma normalización que usa
    la búsqueda del código (`clave_de_una_factura` + `normaliza_para_comparar`), para que las dos digan lo
    mismo.

    **Por qué hace falta teniendo la búsqueda.** Buscar antes de insertar **no es una garantía**: dos
    peticiones simultáneas pueden pasar las dos por la comprobación antes de que ninguna haya escrito, y
    entonces quedan dos facturas del mismo papel. Con esto, la segunda **falla en la base** y la puerta
    contesta con la que ya estaba. Lo que no se puede garantizar es lo que no se sabe: sin proveedor o sin
    número la clave es `None`, y ahí la protección es la de siempre (avisar, `AL27…`).

    El total entra porque **es parte del papel**: dos facturas del mismo número con distinto total son dos
    documentos distintos (y hay una prueba que lo deja escrito). El año entra en vez de la fecha exacta
    porque es el año lo que reinicia las numeraciones, y el día es el campo que más se equivoca al leer una
    foto: si baila, es que una de las dos está mal apuntada, y para eso está el aviso.
    """
    if clave_de_una_factura(proveedor, proveedor_nif, numero_factura) is None:
        return None
    quien = normaliza_para_comparar(proveedor_nif) or normaliza_para_comparar(proveedor)
    numero = normaliza_para_comparar(numero_factura)
    anio = ""
    if fecha is not None:
        anio = str(getattr(fecha, "year", "") or str(fecha)[:4])
    el_total = dinero.a_texto(dinero.cantidad_a_decimal(total)) or ""
    return f"{quien}|{numero}|{anio}|{el_total}"[:200]


def la_huella_de_una_peticion_de_factura(entrada) -> str:
    """El resumen del **cuerpo con el que se atiende una petición de factura**: su huella.

    **Para qué.** La clave de reenvío dice «esta petición ya se atendió», pero no dice **qué traía**. Con
    la huella se separan las dos cosas que la clave sola confundía (09/10/2026):

      · **El reenvío de siempre**: lo que llega tiene la misma huella que el comando original, así que es
        el mismo comando otra vez —el móvil que reintenta sin cobertura— y se contesta con su resultado
        actual, aunque la factura se haya corregido o anulado después.
      · **Otra cosa con la misma clave**: la huella no coincide. Eso no es un reenvío, es una petición
        distinta usando una clave ajena, y es un **conflicto**.

    Se calcula **siempre desde la petición** —al apuntar y al reenviar—, así que las dos veces pasan por
    la misma normalización y coinciden por construcción. La variante de lo ya guardado
    (`la_huella_de_una_factura_guardada`) existe para las facturas de antes de que hubiera huella, y sus
    datos pasan por las mismas reglas.
    """
    return _la_huella_de(
        _las_partes_de_una_factura(
            fecha=entrada.fecha,
            proveedor=entrada.proveedor,
            proveedor_nif=entrada.proveedor_nif,
            numero_factura=entrada.numero_factura,
            base_imponible=entrada.base_imponible,
            cuota_iva=entrada.cuota_iva,
            tipo_iva_pct=entrada.tipo_iva_pct,
            total=entrada.total,
            notas=entrada.notas,
            lineas=[linea.model_dump() for linea in entrada.lineas],
        )
    )


def la_huella_de_una_factura_guardada(factura, lineas) -> str:
    """La huella del comando de una factura **ya guardada**, para las que son de antes.

    La usa la migración (`database.rellenar_la_huella_del_comando`) para las facturas que ya tenían clave
    de reenvío cuando esto no existía: se rellena con **lo que la factura dice hoy**. Si nadie la ha
    corregido, esa huella es la de su comando original y su reenvío se reconoce; si se corrigió, lo que
    llegue distinto dará conflicto —la parte prudente de la duda, mejor que aceptar en silencio algo que
    no se puede comprobar—.

    `factura` y `lineas` son filas tal y como salen de la base (diccionarios o `RowMapping`).
    """
    def de_la_fila(fila, campo):
        try:
            return fila[campo]
        except (KeyError, TypeError, IndexError):
            return None

    return _la_huella_de(
        _las_partes_de_una_factura(
            fecha=de_la_fila(factura, "fecha"),
            proveedor=de_la_fila(factura, "proveedor"),
            proveedor_nif=de_la_fila(factura, "proveedor_nif"),
            numero_factura=de_la_fila(factura, "numero_factura"),
            base_imponible=de_la_fila(factura, "base_imponible"),
            cuota_iva=de_la_fila(factura, "cuota_iva"),
            tipo_iva_pct=de_la_fila(factura, "tipo_iva_pct"),
            total=de_la_fila(factura, "total"),
            notas=de_la_fila(factura, "notas"),
            lineas=[
                {
                    "descripcion": de_la_fila(linea, "descripcion"),
                    "cantidad": de_la_fila(linea, "cantidad"),
                    "unidad": de_la_fila(linea, "unidad"),
                    "precio_unitario": de_la_fila(linea, "precio_unitario"),
                    "importe": de_la_fila(linea, "importe"),
                    "numero_registro": de_la_fila(linea, "numero_registro"),
                    "lote": de_la_fila(linea, "lote"),
                }
                for linea in lineas
            ],
        )
    )


def lo_pagado_de_un_gasto(db: Session, *, explotacion_id: int, gasto_id: int):
    """Cuánto dinero de los pagos **vivos** está aplicado a este gasto.

    Se suman **las aplicaciones**, no los pagos: es lo que hace que un pago de 500 € contra tres gastos
    cuente 60 en uno, 40 en otro y 400 en el tercero, y no 500 en cada uno (que es la forma fácil de
    contar el mismo dinero tres veces).

    **Está aquí y no en `gastos_api` desde el 09/10/2026**, cuando llegó la ficha de la compra: esa
    ficha enseña «pagado» y «pendiente» de un gasto, y si se calcularan con otra copia de la regla
    podrían salir **dos cifras distintas del mismo dinero** en dos pantallas. Una regla, un sitio.
    """
    aplicaciones = list(
        db.scalars(
            select(models.AplicacionDeUnPago)
            .join(models.PagoDeGasto, models.PagoDeGasto.id == models.AplicacionDeUnPago.pago_id)
            .where(
                models.AplicacionDeUnPago.explotacion_id == explotacion_id,
                models.AplicacionDeUnPago.gasto_id == gasto_id,
                models.PagoDeGasto.anulado.is_(False),
            )
        )
    )
    return dinero.suma(*[aplicacion.importe for aplicacion in aplicaciones])


def lo_cobrado_de_una_factura(
    db: Session, *, explotacion_id: int, factura_id: int, sin_este_cobro: int | None = None
):
    """Cuánto dinero de los cobros **vivos** está aplicado a esta factura nuestra.

    Se suman **las aplicaciones**, no los cobros. Y no es un detalle: un ingreso puede saldar **varias**
    deudas —350 repartidos entre una factura de 100 y otra de 250—, así que la columna `factura_emitida_id`
    del cobro va **vacía a propósito** cuando hay reparto. Sumando esa columna, la factura aparecía pendiente
    aunque estuviera cobrada, y el dinero se perdía de vista en cinco sitios distintos.

    **Está aquí y no en `ventas_api` desde el 11/10/2026**, por el mismo motivo por el que
    `lo_pagado_de_un_gasto` está aquí al lado (y es el patrón de la casa): esa regla la usan **tres** sitios
    —la ficha y la lista de lo que se vende, el **margen** de una venta y la **conciliación del banco**—, y
    con una copia en cada uno ya se vio lo que pasa: cinco pantallas leyendo el dato viejo y cinco cifras
    del mismo dinero. **Una regla, un sitio.**

    `sin_este_cobro` deja fuera las aplicaciones de un cobro concreto, y hace falta al **reimputar**: si al
    cambiar un cobro se contara su propio dinero, el pendiente saldría recortado por él mismo y el segundo
    pago se imputaría de menos.
    """
    condiciones = [
        models.AplicacionDeUnCobro.explotacion_id == explotacion_id,
        models.AplicacionDeUnCobro.factura_emitida_id == factura_id,
        models.AplicacionDeUnCobro.anulado.is_(False),
        # **Y la aplicación de un cobro anulado no cuenta**: anular el cobro devuelve la deuda a estar
        # pendiente, y el dinero de una factura no puede depender de que todos los caminos de anulación se
        # acuerden de marcar también su aplicación.
        models.Cobro.anulado.is_(False),
    ]
    if sin_este_cobro is not None:
        condiciones.append(models.AplicacionDeUnCobro.cobro_id != sin_este_cobro)
    aplicaciones = db.scalars(
        select(models.AplicacionDeUnCobro)
        .join(models.Cobro, models.Cobro.id == models.AplicacionDeUnCobro.cobro_id)
        .where(*condiciones)
    )
    return dinero.suma(*[aplicacion.importe for aplicacion in aplicaciones])


def lo_cobrado_por_factura(db: Session, *, explotacion_id: int) -> dict[int, Decimal]:
    """Lo cobrado de **cada** factura de la explotación, de una vez: `{factura_id: lo cobrado}`.

    Es la misma regla que `lo_cobrado_de_una_factura`, en la forma que necesita quien tiene que recorrer
    todas las facturas de una campaña (el margen de lo que se vende, 11/10/2026) **sin hacer una consulta
    por factura**. Las facturas sin ningún cobro no salen en el diccionario: quien lo lea tiene que tratar
    el «no está» como un cero, que es lo que es.
    """
    aplicaciones = db.scalars(
        select(models.AplicacionDeUnCobro)
        .join(models.Cobro, models.Cobro.id == models.AplicacionDeUnCobro.cobro_id)
        .where(
            models.AplicacionDeUnCobro.explotacion_id == explotacion_id,
            models.AplicacionDeUnCobro.anulado.is_(False),
            models.Cobro.anulado.is_(False),
        )
    )
    por_factura: dict[int, Decimal] = {}
    for aplicacion in aplicaciones:
        por_factura[aplicacion.factura_emitida_id] = dinero.suma(
            por_factura.get(aplicacion.factura_emitida_id, dinero.CERO),
            dinero.a_decimal(aplicacion.importe) or dinero.CERO,
        )
    return por_factura


def se_pueden_sumar(unidad_a: str | None, unidad_b: str | None) -> bool:
    """¿Estas dos cantidades se pueden meter en la misma cuenta?

    Sí cuando son la misma unidad, y sí cuando son de la misma familia y la conversión es exacta
    (1 L = 1000 mL, que no es una aproximación). **No** cuando una es volumen y la otra masa
    (`legal.se_pueden_comparar`), y tampoco cuando falta la unidad: sin saber en qué se mide una
    cantidad, no se puede restar de nada.
    """
    uno = (unidad_a or "").strip()
    otro = (unidad_b or "").strip()
    if not uno or not otro:
        return False
    if uno.lower() == otro.lower():
        return True
    return legal.se_pueden_comparar(uno, otro)


def pasa_a_la_unidad(cantidad: float | None, de: str | None, a: str | None) -> float | None:
    """Una cantidad en otra unidad de su familia. `None` cuando no se puede, nunca un número al azar."""
    if cantidad is None:
        return None
    uno = (de or "").strip()
    otro = (a or "").strip()
    if not uno or not otro:
        return None
    if uno.lower() == otro.lower():
        return cantidad
    return legal.convierte(cantidad, uno, otro)


def saldo_de_un_conjunto(
    movimientos: list[dict], unidad_del_articulo: str | None = None
) -> dict:
    """La cuenta de un conjunto de movimientos: lo que entró, lo que salió y lo que queda.

    Devuelve las cuatro cuentas por separado, el saldo y —esto es lo que importa— **si se ha podido
    calcular**. Las tres formas de no poder son distintas y se dicen por separado:

      · **Falta la cantidad o la unidad de algún movimiento.** Un albarán sin la cantidad legible
        deja el lote sin poder cuadrar: no se puede saber lo que queda hasta que se apunte.
      · **Hay unidades que no se pueden comparar** (litros con kilos, o una unidad que no
        conocemos). Sumarlas daría un número que no significa nada.
      · **El saldo sale negativo.** Eso **sí** se devuelve tal cual, porque es un dato: significa
        que falta apuntar una entrada o que hay una salida de más, y el contrato prohíbe convertirlo
        en cero («saldo negativo señala falta de entrada o revisión, no inventa una compra»).

    La unidad de la cuenta es la de **lo que entró** (es como lo piensa el agricultor: «entraron
    5 litros y llevo 2 gastados»). Si no ha entrado nada, la del artículo.
    """
    entradas = salidas = mermas = ajustes = 0.0
    sin_cantidad: list[dict] = []
    sin_unidad: list[dict] = []
    unidades_raras: list[str] = []

    # **Un lote sin ningún movimiento no es un misterio: está a cero**, y eso se sabe. Se dice con
    # un 0 y no con un «no se puede saber», que es para cuando falta un dato de verdad.
    if not movimientos:
        return {
            "entradas": 0.0,
            "salidas": 0.0,
            "mermas": 0.0,
            "ajustes": 0.0,
            "unidad": (unidad_del_articulo or "").strip() or None,
            "movimientos_sin_cantidad": 0,
            "unidades_que_no_cuadran": [],
            "movimientos": 0,
            "sin_movimientos": True,
            "saldo": 0.0,
            "motivo_codigo": "",
            "motivo": "",
        }

    unidad = ""
    for movimiento in movimientos:
        if movimiento.get("tipo") == "entrada" and (movimiento.get("unidad") or "").strip():
            unidad = movimiento["unidad"].strip()
            break
    if not unidad:
        unidad = (unidad_del_articulo or "").strip()

    for movimiento in movimientos:
        tipo = movimiento.get("tipo")
        cantidad = movimiento.get("cantidad")
        suya = (movimiento.get("unidad") or "").strip()
        # Las dos formas de no poder contar son distintas y se dicen por separado: no es lo mismo un
        # movimiento del que no se sabe **cuánto** que uno del que no se sabe **en qué se mide**.
        if cantidad is None:
            sin_cantidad.append(movimiento)
            continue
        if not suya:
            sin_unidad.append(movimiento)
            continue
        if not unidad:
            # No hay unidad de referencia: se adopta la del primer movimiento con unidad.
            unidad = suya
        if not se_pueden_sumar(suya, unidad):
            unidades_raras.append(suya)
            continue
        en_la_unidad = pasa_a_la_unidad(cantidad, suya, unidad)
        if en_la_unidad is None:
            unidades_raras.append(suya)
            continue
        if tipo == "entrada":
            entradas += en_la_unidad
        elif tipo == "salida":
            salidas += en_la_unidad
        elif tipo == "merma":
            mermas += en_la_unidad
        elif tipo == "ajuste":
            ajustes += en_la_unidad

    cuentas = {
        "entradas": round(entradas, 4),
        "salidas": round(salidas, 4),
        "mermas": round(mermas, 4),
        "ajustes": round(ajustes, 4),
        "unidad": unidad or None,
        "movimientos_sin_cantidad": len(sin_cantidad),
        "movimientos_sin_unidad": len(sin_unidad),
        "unidades_que_no_cuadran": sorted(set(unidades_raras)),
        "movimientos": len(movimientos),
        "sin_movimientos": False,
    }

    if sin_cantidad:
        cuentas["saldo"] = None
        cuentas["motivo_codigo"] = "AL30_falta_la_cantidad"
        cuentas["motivo"] = textos.mensaje_con_cuenta(
            "AL30_falta_la_cantidad", len(sin_cantidad)
        )
        return cuentas
    if sin_unidad:
        cuentas["saldo"] = None
        cuentas["motivo_codigo"] = "AL32_falta_la_unidad"
        cuentas["motivo"] = textos.mensaje_con_cuenta("AL32_falta_la_unidad", len(sin_unidad))
        return cuentas
    if unidades_raras:
        cuentas["saldo"] = None
        cuentas["motivo_codigo"] = "AL31_unidades_que_no_cuadran"
        cuentas["motivo"] = textos.MENSAJES["AL31_unidades_que_no_cuadran"].format(
            unidades=", ".join(sorted(set(unidades_raras))),
            cuenta=unidad or "?",
        )
        return cuentas
    if not unidad:
        # Ni un solo movimiento con unidad: no hay nada que contar, y no es un cero, es un «no sé».
        cuentas["saldo"] = None
        cuentas["motivo_codigo"] = "AL32_falta_la_unidad"
        cuentas["motivo"] = textos.mensaje_con_cuenta("AL32_falta_la_unidad", len(movimientos))
        return cuentas

    saldo = entradas - salidas - mermas + ajustes
    cuentas["saldo"] = round(saldo, 4)
    cuentas["motivo_codigo"] = "AL33_saldo_negativo" if saldo < 0 else ""
    cuentas["motivo"] = textos.MENSAJES["AL33_saldo_negativo"] if saldo < 0 else ""
    return cuentas


def estado_de_los_origenes(
    db: Session, *, explotacion_id: int, movimientos: list[models.MovimientoDeExistencias]
) -> dict[tuple[str, int], str]:
    """Qué movimientos dejan de contar por culpa del documento del que salen, y por qué.

    **Aquí está la mitad de la regla de que nada se borra.** Un movimiento no se toca cuando se
    anula el albarán, el tratamiento o la factura del que sale: lo que se hace es dejar de contarlo
    y decir por qué. Así el libro sigue enseñando lo que se apuntó, con su fecha y su autor, y a la
    vez la cuenta es la de verdad:

      · **El albarán anulado** no metió nada: sus entradas dejan de contar.
      · **El tratamiento anulado** no gastó nada: su salida deja de contar (esto es A01: «anular 2 L
        devuelve 2»). Y no hay que tocar el libro para conseguirlo.
      · **La factura anulada** ya no sostiene la compra que la acompañaba.
      · Y si el documento **ya no está** (borrado), tampoco se cuenta: no se puede comprobar nada de
        él, y contarlo sería dar por bueno lo que no se puede mirar.

    Se consulta en dos tandas por tipo en vez de una por movimiento: con doscientos movimientos,
    preguntar de uno en uno son doscientas consultas para contestar lo mismo.
    """
    consultas = {
        "recepcion": (models.Recepcion, "anulada"),
        "tratamiento": (models.TratamientoFitosanitario, "anulado"),
        "fertilizacion": (models.RegistroFertilizacion, "anulado"),
        "factura": (models.Factura, "anulada"),
        # La siembra (T10, 03/10/2026). Es lo que hace que **anular una siembra devuelva al almacén lo
        # que salió sin tocar el libro**: la salida sigue apuntada con su fecha y su autor, y deja de
        # contar, igual que la de un tratamiento anulado. Sin esta línea, anular una siembra dejaría la
        # semilla descontada para siempre y habría que ir a borrar el movimiento a mano.
        "siembra": (models.Siembra, "anulada"),
        # Las labores (T15, 05/10/2026). Es lo que hace que **anular un trabajo devuelva al almacén lo
        # que gastó sin tocar el libro**, igual que un tratamiento o una siembra anulados (A01/A04): el
        # movimiento se queda con su fecha y su autor, y deja de contar.
        "labor": (models.Labor, "anulado"),
    }
    codigos = {
        "recepcion": "AL34_el_albaran_esta_anulado",
        "tratamiento": "AL35_el_apunte_esta_anulado",
        "fertilizacion": "AL35_el_apunte_esta_anulado",
        "factura": "AL36_la_factura_esta_anulada",
        "siembra": "SM29_la_siembra_esta_anulada",
        "labor": "AL35_el_apunte_esta_anulado",
    }
    por_tipo: dict[str, set[int]] = {}
    for movimiento in movimientos:
        origen = movimiento.origen_tipo
        if origen in consultas and movimiento.origen_id:
            por_tipo.setdefault(origen, set()).add(movimiento.origen_id)

    anulados: dict[tuple[str, int], str] = {}
    for origen, identificadores in por_tipo.items():
        modelo, columna = consultas[origen]
        encontrados = {
            fila.id
            for fila in db.scalars(
                select(modelo).where(
                    modelo.explotacion_id == explotacion_id,
                    modelo.id.in_(identificadores),
                )
            )
        }
        for identificador in identificadores:
            if identificador not in encontrados:
                anulados[(origen, identificador)] = textos.MENSAJES["AL37_el_documento_ya_no_esta"]
                continue
            registro = db.get(modelo, identificador)
            if getattr(registro, columna):
                anulados[(origen, identificador)] = textos.MENSAJES[codigos[origen]]
    return anulados


def un_movimiento_cuenta(
    movimiento: models.MovimientoDeExistencias,
    *,
    anulados: dict[tuple[str, int], str],
) -> tuple[bool, str | None]:
    """Si este movimiento entra en la cuenta, y si no, por qué. Ver `estado_de_los_origenes`."""
    if movimiento.anulado:
        return False, textos.MENSAJES["AL38_el_movimiento_esta_anulado"]
    if movimiento.origen_id is not None:
        motivo = anulados.get((movimiento.origen_tipo, movimiento.origen_id))
        if motivo:
            return False, motivo
    return True, None


def movimientos_del_almacen(
    db: Session,
    *,
    explotacion_id: int,
    articulo_id: int | None = None,
    lote_id: int | None = None,
    tipo: str | None = None,
    desde=None,
    hasta=None,
    solo_los_que_cuentan: bool = False,
) -> list[dict]:
    """El libro, con los nombres resueltos y diciendo cuáles cuentan y cuáles no.

    Se devuelve como lista de diccionarios y no como filas del modelo a propósito: cada movimiento
    lleva encima su artículo, su lote y **si cuenta**. Sin ese último dato, una resta que no cuadre a
    ojo es inexplicable para el agricultor, y lo único que se le puede decir es «el programa se ha
    equivocado», que es mentira.

    Se filtra **por fechas** y no por campaña: el libro no cuelga del año (el porqué, en
    `models.MovimientoDeExistencias`), y un movimiento se busca por el día en que pasó. Un movimiento
    **sin fecha** no entra en un rango: no se sabe si estaba dentro, así que no se puede afirmar.
    """
    consulta = select(models.MovimientoDeExistencias).where(
        models.MovimientoDeExistencias.explotacion_id == explotacion_id
    )
    if articulo_id is not None:
        consulta = consulta.where(models.MovimientoDeExistencias.articulo_id == articulo_id)
    if lote_id is not None:
        consulta = consulta.where(models.MovimientoDeExistencias.lote_id == lote_id)
    if tipo is not None:
        consulta = consulta.where(models.MovimientoDeExistencias.tipo == tipo)
    if desde is not None or hasta is not None:
        consulta = consulta.where(models.MovimientoDeExistencias.fecha.is_not(None))
    if desde is not None:
        consulta = consulta.where(models.MovimientoDeExistencias.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(models.MovimientoDeExistencias.fecha <= hasta)
    # Los apuntes más nuevos primero, y los que no tienen fecha al final: un movimiento sin fecha no
    # es el más antiguo, es uno del que no se sabe cuándo fue.
    movimientos = list(
        db.scalars(
            consulta.order_by(
                models.MovimientoDeExistencias.fecha.is_(None),
                models.MovimientoDeExistencias.fecha.desc(),
                models.MovimientoDeExistencias.id.desc(),
            )
        )
    )
    anulados = estado_de_los_origenes(
        db, explotacion_id=explotacion_id, movimientos=movimientos
    )
    nombres_de_articulo = {
        articulo.id: articulo.nombre
        for articulo in db.scalars(
            select(models.Articulo).where(models.Articulo.explotacion_id == explotacion_id)
        )
    }
    numeros_de_lote = {
        lote.id: lote.numero_lote
        for lote in db.scalars(
            select(models.Lote).where(models.Lote.explotacion_id == explotacion_id)
        )
    }

    devueltos: list[dict] = []
    for movimiento in movimientos:
        cuenta, porque = un_movimiento_cuenta(movimiento, anulados=anulados)
        if solo_los_que_cuentan and not cuenta:
            continue
        devueltos.append(
            {
                "id": movimiento.id,
                "articulo_id": movimiento.articulo_id,
                "articulo": nombres_de_articulo.get(movimiento.articulo_id),
                "lote_id": movimiento.lote_id,
                "numero_lote": numeros_de_lote.get(movimiento.lote_id),
                "tipo": movimiento.tipo,
                "fecha": movimiento.fecha,
                "cantidad": movimiento.cantidad,
                "unidad": movimiento.unidad,
                "origen_tipo": movimiento.origen_tipo,
                "origen_id": movimiento.origen_id,
                "motivo": movimiento.motivo,
                "usuario_id": movimiento.usuario_id,
                "anulado": movimiento.anulado,
                "motivo_anulacion": movimiento.motivo_anulacion,
                "creado_en": movimiento.creado_en,
                "cuenta": cuenta,
                "no_cuenta_porque": porque,
            }
        )
    return devueltos


def un_movimiento_del_almacen(
    db: Session, *, explotacion_id: int, movimiento_id: int
) -> dict | None:
    """Un movimiento del libro, con sus nombres y diciendo si cuenta. `None` si no es de esta finca.

    Se recorre la misma función que el listado (`movimientos_del_almacen`) en vez de montar el
    diccionario a mano: así lo que se devuelve al apuntar algo es **exactamente** lo mismo que se
    devuelve al consultarlo después, incluido el «cuenta / no cuenta». Montarlo dos veces es la forma
    de que un día digan cosas distintas.
    """
    for fila in movimientos_del_almacen(db, explotacion_id=explotacion_id):
        if fila["id"] == movimiento_id:
            return fila
    return None


def existencias_del_almacen(
    db: Session, *, explotacion_id: int, articulo_id: int | None = None
) -> list[dict]:
    """Lo que hay en el almacén, **por artículo y por lote**, con lo que queda de cada lote.

    Es la pregunta que se hace de verdad —«¿me queda producto para tratar esta parcela?»— y la que
    mira una inspección, pero por lote: un artículo tiene varios envases con números distintos, y
    cada uno lleva su cuenta.

    Tres cosas que se dicen en vez de esconderse:

      1. **Un lote del que no se sabe la cantidad o la unidad** sale con `saldo: null` y su motivo.
         No con un cero: un cero diría que no queda nada y el agricultor iría a comprar por nada.
      2. **Un saldo negativo se devuelve tal cual**, marcado. Significa que falta una entrada o que
         hay una salida de más, y las dos cosas se arreglan mirándolo, no tapándolo con un cero.
      3. **Un lote caducado o del que no se sabe la caducidad se marca.** «No lo sé» no es «está
         bien»: el contrato lo pide así («vencimiento desconocido no es vigente»), y aquí se
         devuelve `caducado` (sí/no/no se sabe) sin decidir por nadie qué hacer con él.

    Y lo que **no** se hace: no se suman los lotes de un artículo que están en unidades distintas, ni
    se mete aquí lo comprado por factura sin albarán. Eso último se declara aparte
    (`facturas_sin_recibir`) para que un almacén vacío no parezca unas existencias perdidas.
    """
    hoy = legal.hoy()
    consulta = select(models.Articulo).where(models.Articulo.explotacion_id == explotacion_id)
    if articulo_id is not None:
        consulta = consulta.where(models.Articulo.id == articulo_id)
    articulos = list(db.scalars(consulta.order_by(models.Articulo.nombre)))

    devueltos: list[dict] = []
    for articulo in articulos:
        lotes = list(
            db.scalars(
                select(models.Lote)
                .where(
                    models.Lote.explotacion_id == explotacion_id,
                    models.Lote.articulo_id == articulo.id,
                )
                .order_by(models.Lote.fecha_caducidad.is_(None), models.Lote.fecha_caducidad, models.Lote.id)
            )
        )
        # Los movimientos del artículo se leen **una vez** y se reparten por lote: preguntarlos lote a
        # lote serían tantas consultas como envases tenga el almacén, para contestar lo mismo.
        todos_los_movimientos = movimientos_del_almacen(
            db, explotacion_id=explotacion_id, articulo_id=articulo.id, solo_los_que_cuentan=True
        )
        por_lote: dict[int, list[dict]] = {}
        for movimiento in todos_los_movimientos:
            por_lote.setdefault(movimiento["lote_id"], []).append(movimiento)

        filas_de_lotes: list[dict] = []
        for lote in lotes:
            movimientos = por_lote.get(lote.id, [])
            cuenta = saldo_de_un_conjunto(movimientos, articulo.unidad)
            caducado: bool | None
            if lote.fecha_caducidad is None:
                caducado = None
            else:
                caducado = lote.fecha_caducidad < hoy
            filas_de_lotes.append(
                {
                    "lote_id": lote.id,
                    "numero_lote": lote.numero_lote,
                    "fecha_caducidad": lote.fecha_caducidad,
                    # Tres estados: sí caducado, no caducado y «no se sabe cuándo caduca».
                    "caducado": caducado,
                    "presentacion": lote.presentacion,
                    "contenido_por_envase": lote.contenido_por_envase,
                    "ubicacion": lote.ubicacion,
                    # El desglose de un lote concreto, para poder contestar «¿y esto de dónde sale?».
                    # Y con él vienen las cuentas de ese lote (entradas, salidas, saldo).
                    "movimientos_del_lote": movimientos,
                    **cuenta,
                }
            )

        cuenta_del_articulo = saldo_de_un_conjunto(todos_los_movimientos, articulo.unidad)
        con_caducidad = [fila for fila in filas_de_lotes if fila["fecha_caducidad"] is not None]
        devueltos.append(
            {
                "articulo_id": articulo.id,
                "nombre": articulo.nombre,
                "categoria": articulo.categoria,
                "unidad": articulo.unidad,
                "producto_id": articulo.producto_id,
                "fertilizante_id": articulo.fertilizante_id,
                "lotes": filas_de_lotes,
                "cuantos_lotes": len(filas_de_lotes),
                "caducados": sum(1 for fila in filas_de_lotes if fila["caducado"] is True),
                "sin_caducidad_apuntada": sum(
                    1 for fila in filas_de_lotes if fila["fecha_caducidad"] is None
                ),
                "con_caducidad_apuntada": len(con_caducidad),
                # Lo que vale del artículo entero: **solo si se puede sumar**, que es cuando todos sus
                # lotes están en unidades que se pueden comparar entre sí.
                **cuenta_del_articulo,
                # Y lo que está comprado pero no ha entrado: ver la decisión de arriba.
                "facturas_sin_recibir": facturas_de_un_articulo_sin_recibir(
                    db, explotacion_id=explotacion_id, articulo=articulo
                ),
            }
        )
    return devueltos


def el_saldo_fisico_de_una_cesta(db: Session, *, explotacion_id: int) -> dict:
    """El saldo **físico** de cada artículo, relacionado con la cesta **por identificador**.

    Es la pieza que hace que las dos pantallas que enseñan «te queda» digan lo mismo. Hasta hoy la cesta
    (`situacion_de_la_cesta`) contestaba con facturas menos tratamientos y el almacén con el libro de
    movimientos, y los dos números podían no parecerse. Aquí se juntan **sin sumarlos**: el número que se
    enseña es el físico, y lo que dice la cesta viaja al lado con su nombre.

    La lógica pura —qué es una entrada, qué es un consumo y cómo se relacionan producto, artículo y
    lote— vive en `app/existencias.py`, que se prueba sin base de datos ni servidor. Aquí solo se leen
    las filas y se le pasan.

    **Lo que no se hace:** unir dos cosas por el nombre, sumar los dos libros, ni convertir en cero un
    producto que no tenga artículo. Un dato sin correlación **queda pendiente** y se declara
    (`pendientes`, con su aviso `A24`).

    **Devuelve `por_articulo` con la clave `articulo_id`**, que es el identificador del artículo del
    almacén (`Articulo.id`). Es `None` cuando el producto de la cesta **no tiene artículo**: entonces el
    producto no está en `por_articulo` y sale en `pendientes`. La puerta de la cesta se queda con ese
    `articulo_id` y **no vuelve a relacionar nada**: relacionar dos veces es como un día las dos
    relaciones dicen cosas distintas.

    `apuntes` es la lista de consumos ya apuntados en el cuaderno (los tratamientos de la campaña, con
    `origen_tipo="tratamiento"`). Se pasan para poder decir «este consumo está apuntado y no ha salido de
    ningún envase», que es una de las cosas que hay que revisar. Sin ellos, el cruce se hace con los
    propios movimientos del almacén y se detecta igual el mismo consumo por las dos puertas.
    """
    # **El import va aquí dentro y no arriba a propósito**: `app/existencias.py` importa este módulo
    # en su cabecera (`from . import legal, servicios, textos`), así que importarlo arriba sería un
    # ciclo entre los dos. Dentro de la función no hay ciclo, y el módulo ya está cargado cuando se
    # llama a esto.
    from . import existencias

    articulos = list(
        db.scalars(
            select(models.Articulo).where(models.Articulo.explotacion_id == explotacion_id)
        )
    )
    movimientos = movimientos_del_almacen(
        db, explotacion_id=explotacion_id, solo_los_que_cuentan=True
    )
    apuntes = [
        {
            "origen_tipo": "tratamiento",
            "origen_id": tratamiento.id,
            "producto_id": tratamiento.producto_id,
            "cantidad": tratamiento.cantidad_total,
            "unidad": (tratamiento.unidad_cantidad_aplicada or "").strip()
            or legal.unidad_de_una_dosis(tratamiento.unidad_dosis),
        }
        for tratamiento in db.scalars(
            select(models.TratamientoFitosanitario).where(
                models.TratamientoFitosanitario.explotacion_id == explotacion_id,
                models.TratamientoFitosanitario.anulado.is_(False),
            )
        )
    ]
    # **La relación se calcula una vez, aquí**, y viaja en la respuesta: así la puerta de la cesta no
    # tiene que volver a relacionar por su cuenta (y no puede equivocarse haciéndolo de otra manera).
    relacion = existencias.la_relacion_por_identificador(
        [
            {
                "id": articulo.id,
                "producto_id": articulo.producto_id,
                "fertilizante_id": articulo.fertilizante_id,
            }
            for articulo in articulos
        ]
    )
    por_producto: dict[int, dict] = {}
    for fila in situacion_de_la_cesta(db, explotacion_id=explotacion_id, campana_id=None):
        por_producto[fila["producto_id"]] = {
            "producto_id": fila["producto_id"],
            # El identificador del artículo del almacén, que es lo que engancha las dos vistas. `None`
            # es «este producto no tiene artículo», y entonces sale en `pendientes` con su aviso.
            "articulo_id": existencias.el_articulo_de_una_ficha(
                "producto", fila["producto_id"], relacion
            ),
            "nombre_comercial": fila["nombre_comercial"],
            "numero_registro": fila["numero_registro"],
            "unidad_compra": fila["unidad_compra"],
            "comprado": fila["comprado"],
            "comprado_de_donde": fila["comprado_de_donde"],
            "gastado": fila["gastado"],
            "apuntes": fila["apuntes"],
        }
    vista = existencias.el_saldo_fisico_de_una_cesta(
        list(por_producto.values()),
        [
            {
                "id": articulo.id,
                "nombre": articulo.nombre,
                "categoria": articulo.categoria,
                "unidad": articulo.unidad,
                "producto_id": articulo.producto_id,
                "fertilizante_id": articulo.fertilizante_id,
            }
            for articulo in articulos
        ],
        movimientos,
        apuntes=apuntes,
        compra_sin_entrar=lo_comprado_que_no_ha_entrado(db, explotacion_id=explotacion_id),
    )
    return {
        "por_articulo": {fila.articulo_id: fila for fila in vista["articulos"]},
        "por_producto": por_producto,
        "pendientes": vista["pendientes"],
        "compra_sin_entrar": vista["compra_sin_entrar"],
        "avisos": vista["avisos"],
        "sin_saldo_conocido": vista["sin_saldo_conocido"],
        "descuadres": vista["descuadres"],
    }


def lo_comprado_que_no_ha_entrado(db: Session, *, explotacion_id: int) -> list[dict]:
    """Lo que está comprado por factura y **todavía no ha entrado** en el almacén.

    Existe por un motivo muy concreto, y es de sentido común: un agricultor que viene de la versión
    anterior tiene sus facturas apuntadas y ningún albarán, así que en esta vista su almacén sale
    vacío. **Eso no es que el programa le haya perdido el producto**: es que las facturas no meten
    mercancía, la mete el albarán. Sin esta lista, el silencio parecería una pérdida, y con ella se
    contesta además a una pregunta útil de verdad: «¿qué me falta por recibir?».

    Se agrupa por producto o abono (que es lo que engancha la factura con el almacén) y se dice
    cuántas líneas son. Lo que **no** se hace es sumarle esto a las existencias: son dos listas
    distintas, y sumarlas contaría cada litro dos veces.
    """
    lineas = list(
        db.scalars(
            select(models.LineaDeFactura)
            .join(models.Factura, models.Factura.id == models.LineaDeFactura.factura_id)
            .where(
                models.LineaDeFactura.explotacion_id == explotacion_id,
                models.Factura.anulada.is_(False),
            )
        )
    )
    # Quién tiene ya algo dentro del almacén: si tiene una entrada, no está «sin entrar».
    articulos = list(
        db.scalars(
            select(models.Articulo).where(models.Articulo.explotacion_id == explotacion_id)
        )
    )
    con_entrada: set[tuple[str, int]] = set()
    for articulo in articulos:
        if articulo.producto_id is None and articulo.fertilizante_id is None:
            continue
        # **Solo cuentan las entradas que cuentan** (03/10/2026). Sin esto, un albarán anulado seguía
        # contando como entrada: el artículo pasaba a «ya está dentro del almacén» y desaparecía del
        # aviso «comprado y aún sin entrar». El agricultor anulaba el albarán porque se había
        # equivocado, y el programa dejaba de avisarle de que ese producto no había entrado —ni
        # entró—, así que se quedaba creyendo que lo tenía. Un movimiento anulado no cuenta para el
        # saldo (es lo que dice el propio libro), y aquí tampoco puede contar para el aviso.
        movimientos = movimientos_del_almacen(
            db,
            explotacion_id=explotacion_id,
            articulo_id=articulo.id,
            tipo="entrada",
            solo_los_que_cuentan=True,
        )
        if not movimientos:
            continue
        if articulo.producto_id is not None:
            con_entrada.add(("producto", articulo.producto_id))
        else:
            con_entrada.add(("fertilizante", articulo.fertilizante_id))

    productos = {
        producto.id: producto
        for producto in db.scalars(
            select(models.ProductoFitosanitario).where(
                models.ProductoFitosanitario.explotacion_id == explotacion_id
            )
        )
    }
    abonos = {
        abono.id: abono
        for abono in db.scalars(
            select(models.Fertilizante).where(models.Fertilizante.explotacion_id == explotacion_id)
        )
    }

    agrupadas: dict[tuple[str, int], dict] = {}
    for linea in lineas:
        if linea.producto_id is not None:
            clave = ("producto", linea.producto_id)
            nombre = productos[linea.producto_id].nombre_comercial if linea.producto_id in productos else None
            unidad = productos[linea.producto_id].unidad_compra if linea.producto_id in productos else None
        elif linea.fertilizante_id is not None:
            clave = ("fertilizante", linea.fertilizante_id)
            nombre = abonos[linea.fertilizante_id].nombre if linea.fertilizante_id in abonos else None
            unidad = None
        else:
            # Una línea sin enganchar (unas botas, una reparación) no es nada del almacén.
            continue
        if not nombre or clave in con_entrada:
            continue
        fila = agrupadas.setdefault(
            clave,
            {"que_es": clave[0], "identificador": clave[1], "nombre": nombre, "unidad": unidad, "lineas": 0},
        )
        fila["lineas"] += 1
    return sorted(agrupadas.values(), key=lambda fila: fila["nombre"])


def facturas_de_un_articulo_sin_recibir(
    db: Session, *, explotacion_id: int, articulo: models.Articulo
) -> int:
    """Cuántas líneas de factura de este artículo no tienen ninguna recepción detrás.

    Sirve para poder decir en la pantalla **por qué el almacén está vacío aunque haya compras**:
    las facturas no meten mercancía, la mete el albarán. Sin este número, un agricultor que viene de
    la versión anterior vería su almacén a cero y creería que el programa le ha perdido el producto.
    """
    if articulo.producto_id is None and articulo.fertilizante_id is None:
        return 0
    consulta = (
        select(models.LineaDeFactura)
        .join(models.Factura, models.Factura.id == models.LineaDeFactura.factura_id)
        .where(
            models.LineaDeFactura.explotacion_id == explotacion_id,
            models.Factura.anulada.is_(False),
        )
    )
    if articulo.producto_id is not None:
        consulta = consulta.where(models.LineaDeFactura.producto_id == articulo.producto_id)
    else:
        consulta = consulta.where(
            models.LineaDeFactura.fertilizante_id == articulo.fertilizante_id
        )
    lineas = list(db.scalars(consulta))
    if not lineas:
        return 0
    recibidas = set(
        db.scalars(
            select(models.LineaDeRecepcion.linea_factura_id).where(
                models.LineaDeRecepcion.explotacion_id == explotacion_id,
                models.LineaDeRecepcion.linea_factura_id.is_not(None),
            )
        )
    )
    return sum(1 for linea in lineas if linea.id not in recibidas)


def el_lote_de_un_numero(
    db: Session, *, explotacion_id: int, articulo_id: int, numero_lote: str | None
) -> models.Lote | None:
    """El lote de ese número para ese artículo, si ya está apuntado.

    La comparación del número es por su forma normalizada (sin mayúsculas ni espacios de más) por el
    mismo motivo que la del albarán: «4471-A» y «4471-a» son el mismo envase, y abrir dos lotes para
    el mismo bote partiría la cuenta en dos y ninguna de las dos diría la verdad.
    """
    buscado = normaliza_para_comparar(numero_lote)
    for lote in db.scalars(
        select(models.Lote).where(
            models.Lote.explotacion_id == explotacion_id,
            models.Lote.articulo_id == articulo_id,
        )
    ):
        if normaliza_para_comparar(lote.numero_lote) == buscado:
            return lote
    return None


def lote_para_apuntar(
    db: Session,
    *,
    explotacion_id: int,
    articulo: models.Articulo,
    numero_lote: str | None = None,
    fecha_caducidad=None,
    presentacion: str | None = None,
    contenido_por_envase: float | None = None,
    ubicacion: str | None = None,
) -> models.Lote:
    """El lote de ese número para ese artículo, **el que ya hay o uno nuevo**.

    Si el número ya está apuntado para ese artículo, se devuelve el mismo lote: el envase que ya
    estaba en el almacén no se duplica porque llegue otro albarán con el mismo número. Y si el
    número no está, se crea.

    **Lo que no se hace: cambiarle la caducidad a un lote que ya existe.** Un lote caduca una vez, y
    dos papeles que dicen fechas distintas no se arreglan eligiendo una: se dice que no cuadran y el
    agricultor mira el envase, que es el que manda. Se devuelve lo que ya había y quien llama avisa.
    """
    ya = el_lote_de_un_numero(
        db, explotacion_id=explotacion_id, articulo_id=articulo.id, numero_lote=numero_lote
    )
    if ya is not None:
        return ya
    lote = models.Lote(
        explotacion_id=explotacion_id,
        articulo_id=articulo.id,
        numero_lote=(numero_lote or "").strip() or None,
        fecha_caducidad=fecha_caducidad,
        presentacion=(presentacion or "").strip()[:80] or None,
        contenido_por_envase=contenido_por_envase,
        ubicacion=(ubicacion or "").strip()[:120] or None,
    )
    db.add(lote)
    db.flush()
    return lote


def lo_que_gasta_un_apunte(
    db: Session, *, explotacion_id: int, apunte_tipo: str, apunte_id: int
) -> dict:
    """Qué cantidad y qué unidad dice el apunte que se gastó, sin inventarse nada.

    Es lo que permite que una salida del almacén no haya que teclearla otra vez: el tratamiento ya
    sabe cuánto se echó. Y es también donde se evita **la confusión de diez veces**: la dosis por
    hectárea **no** es la cantidad total, así que si el apunte solo tiene la dosis, aquí no se
    multiplica por la superficie por cuenta propia: se dice que no se sabe el total y que lo escriba
    quien lo sabe.

    Devuelve `cantidad` y `unidad` (los dos `None` si el apunte no lo dice), la fecha del apunte —que
    es la del movimiento—, la superficie y **la dosis por hectárea ya calculada** (A02), que se enseña
    para que se vea qué número es cada uno.
    """
    if apunte_tipo == "tratamiento":
        apunte = db.get(models.TratamientoFitosanitario, apunte_id)
        if apunte is None or apunte.explotacion_id != explotacion_id:
            return {"existe": False}
        unidad = (apunte.unidad_cantidad_aplicada or "").strip() or legal.unidad_de_una_dosis(
            apunte.unidad_dosis
        )
        return {
            "existe": True,
            "anulado": apunte.anulado,
            "cantidad": apunte.cantidad_total,
            "unidad": unidad or None,
            "fecha": apunte.fecha,
            "superficie_ha": apunte.superficie_tratada_ha,
            "dosis_por_ha": legal.dosis_por_hectarea(
                apunte.cantidad_total, apunte.superficie_tratada_ha
            ),
            # De dónde sale el total, para poder explicarlo: de lo que el agricultor escribió en el
            # apunte (`cantidad_total`, que el programa calcula como dosis × hectáreas al guardarlo).
            "como_se_sabe": "cantidad_total",
        }
    if apunte_tipo == "labor":
        # Un trabajo hecho (T15). La cantidad de lo que gasta la dice su propio apunte de salida —el
        # router la manda—, y aquí se contesta lo que se sabe del trabajo: que existe, si está anulado y
        # de qué día es. **Lo que la labor no sabe es el total de cada insumo** (un insumo sin cantidad
        # no se resta), así que `cantidad` va en `None` y la puerta de las salidas pedirá el total en vez
        # de inventárselo.
        apunte = db.get(models.Labor, apunte_id)
        if apunte is None or apunte.explotacion_id != explotacion_id:
            return {"existe": False}
        return {
            "existe": True,
            "anulado": apunte.anulado,
            "cantidad": None,
            "unidad": None,
            "fecha": apunte.fecha,
            "superficie_ha": apunte.superficie_ha,
            "dosis_por_ha": None,
            "como_se_sabe": "lo_dice_el_apunte_de_salida",
        }
    if apunte_tipo == "fertilizacion":
        apunte = db.get(models.RegistroFertilizacion, apunte_id)
        if apunte is None or apunte.explotacion_id != explotacion_id:
            return {"existe": False}
        return {
            "existe": True,
            "anulado": apunte.anulado,
            # Los kilos de abono siempre se saben: el apunte guarda kg/ha × hectáreas.
            "cantidad": apunte.cantidad_total_kg,
            "unidad": "kg",
            "fecha": apunte.fecha,
            "superficie_ha": apunte.superficie_ha,
            "dosis_por_ha": apunte.kg_ha_producto,
            "como_se_sabe": "cantidad_total_kg",
        }
    if apunte_tipo == "siembra":
        # Una siembra (T10, 03/10/2026). Se contesta lo mismo que en las otras dos, y con el mismo
        # cuidado: **la cantidad total es lo que se gastó** y `dosis_por_ha` es lo de cada hectárea,
        # en sus campos separados. Cuando la siembra no dice el total (porque no se pudo calcular),
        # `cantidad` va en `None` y la puerta de las salidas pide el total en vez de multiplicarlo.
        apunte = db.get(models.Siembra, apunte_id)
        if apunte is None or apunte.explotacion_id != explotacion_id:
            return {"existe": False}
        return {
            "existe": True,
            "anulado": apunte.anulada,
            "cantidad": apunte.cantidad_total,
            "unidad": (apunte.unidad_cantidad or "").strip() or None,
            "fecha": apunte.fecha,
            "superficie_ha": apunte.superficie_ha,
            "dosis_por_ha": apunte.dosis_por_ha,
            "como_se_sabe": (
                "cantidad_total_calculada"
                if apunte.cantidad_total_calculada
                else "cantidad_total"
            ),
        }
    return {"existe": False}


# --------------------------------------------------------------------------
# El cultivo que hay en cada parcela este año
#
# La app oficial de la Junta lo tiene como la pestaña «Características DGC» (el cultivo de la
# parcela) y la pestaña «Historial Cultivos» (los cultivos de las campañas anteriores). Y avisa
# de que el cultivo de cada actuación es un **campo calculado**: no se pregunta en cada apunte,
# se sabe porque ya se ha dicho qué hay en la parcela.
#
# En este programa la tabla `ParcelaCultivo` existía desde las primeras rondas, con su endpoint,
# y **no la usaba ninguna pantalla**. Las consecuencias eran tres, y las tres se arreglan aquí:
#
# 1. El agricultor no podía decir qué tiene sembrado. El cuaderno se lo pedía —«a El Prado le
#    falta decir qué cultivo tiene este año»— y no había forma de contestarle.
# 2. El campo «Cultivo» de **todos** los tratamientos y labores salía vacío, porque el asistente
#    no lo preguntaba y nadie lo rellenaba. El volcado oficial lo mandaba en blanco.
# 3. El aviso V5 («en esa fecha no había cultivo en esta parcela») **no podía saltar nunca**:
#    dependía de este dato, y este dato no había manera de meterlo.
# --------------------------------------------------------------------------


def cultivo_declarado(
    db: Session, *, explotacion_id: int, parcela_id: int | None, campana_id: int | None
) -> models.ParcelaCultivo | None:
    """El cultivo que el agricultor ha dicho que hay en esa parcela esa campaña.

    `None` es una respuesta normal y frecuente: todavía no lo ha dicho. Y no es lo mismo que
    decir que la parcela está vacía.
    """
    if parcela_id is None or campana_id is None:
        return None
    return db.scalar(
        select(models.ParcelaCultivo).where(
            models.ParcelaCultivo.explotacion_id == explotacion_id,
            models.ParcelaCultivo.parcela_id == parcela_id,
            models.ParcelaCultivo.campana_id == campana_id,
        )
    )


def los_cultivos_de_la_finca(
    db: Session, *, explotacion_id: int, campana_id: int | None
) -> list[dict]:
    """Cada parcela con lo que tiene este año y lo que tuvo los años anteriores.

    Se devuelven **todas las parcelas**, también las que no tienen cultivo declarado: son
    justamente las que hay que enseñar, porque son las que están a medias. Una lista que solo
    enseñara las que están bien no serviría para arreglar nada.
    """
    parcelas = list(
        db.scalars(
            select(models.Parcela)
            .where(models.Parcela.explotacion_id == explotacion_id)
            .order_by(models.Parcela.alias)
        )
    )
    todos = list(
        db.scalars(
            select(models.ParcelaCultivo).where(
                models.ParcelaCultivo.explotacion_id == explotacion_id
            )
        )
    )
    campanas = {
        campana.id: campana.anio
        for campana in db.scalars(
            select(models.Campana).where(models.Campana.explotacion_id == explotacion_id)
        )
    }

    por_parcela: dict[int, list[models.ParcelaCultivo]] = {}
    for cultivo in todos:
        por_parcela.setdefault(cultivo.parcela_id, []).append(cultivo)

    def como_dict(cultivo: models.ParcelaCultivo) -> dict:
        return {
            "id": cultivo.id,
            "campana_id": cultivo.campana_id,
            "anio": campanas.get(cultivo.campana_id),
            "especie": cultivo.especie,
            "variedad": cultivo.variedad,
            "sistema": cultivo.sistema,
            "fecha_inicio": cultivo.fecha_inicio,
            "fecha_fin": cultivo.fecha_fin,
        }

    finca = []
    for parcela in parcelas:
        suyos = por_parcela.get(parcela.id, [])
        de_este_ano = next((c for c in suyos if c.campana_id == campana_id), None)
        anteriores = sorted(
            (c for c in suyos if c.campana_id != campana_id),
            key=lambda c: campanas.get(c.campana_id) or 0,
            reverse=True,
        )
        finca.append(
            {
                "parcela_id": parcela.id,
                "alias": parcela.alias,
                "superficie_ha": parcela.superficie_ha,
                "sistema": parcela.sistema,
                "uso_sigpac": parcela.uso_sigpac,
                "actual": como_dict(de_este_ano) if de_este_ano else None,
                "anteriores": [como_dict(c) for c in anteriores],
                # El agricultor mira esto para ver si le falta algo: se lo decimos calculado.
                "falta_decirlo": de_este_ano is None,
                # Y si repite el mismo cultivo dos años seguidos, se dice: la rotación es una
                # de las medidas preventivas del cuaderno, y verlo aquí ayuda a decidir.
                "repite_el_del_ano_pasado": bool(
                    de_este_ano
                    and anteriores
                    and (anteriores[0].especie or "").strip().lower()
                    == (de_este_ano.especie or "").strip().lower()
                ),
            }
        )
    return finca


# --------------------------------------------------------------------------
# Grupos de parcelas (unidad homogénea de cultivo)
# --------------------------------------------------------------------------


def crear_grupos_automaticos(
    db: Session,
    *,
    explotacion_id: int,
    campana_id: int | None,
    radio_km: float = geo.RADIO_UHC_KM,
) -> list[models.GrupoParcelas]:
    """Agrupa parcelas que se llevan igual: mismo cultivo y mismo sistema, y cerca.

    Es la función que ahorra de verdad trabajo al agricultor: con seis parcelas de
    trigo segadas al mismo tiempo, un tratamiento debería costar UN apunte, no seis.
    """
    consulta = select(models.Parcela).where(models.Parcela.explotacion_id == explotacion_id)
    parcelas = list(db.scalars(consulta))
    if not parcelas:
        return []

    cultivos: dict[int, models.ParcelaCultivo] = {}
    if campana_id is not None:
        for cultivo in db.scalars(
            select(models.ParcelaCultivo).where(
                models.ParcelaCultivo.explotacion_id == explotacion_id,
                models.ParcelaCultivo.campana_id == campana_id,
            )
        ):
            cultivos[cultivo.parcela_id] = cultivo

    centros = {parcela.id: geo.centroide_wkt(parcela.geometria) for parcela in parcelas}

    # Clave de agrupación: cultivo + sistema. Sin cultivo declarado, la parcela se
    # queda fuera: agrupar a ciegas juntaría parcelas que no se llevan igual.
    cubos: dict[tuple[str, str], list[models.Parcela]] = {}
    for parcela in parcelas:
        cultivo = cultivos.get(parcela.id)
        if cultivo is None:
            continue
        clave = (cultivo.especie.strip().lower(), cultivo.sistema or parcela.sistema)
        cubos.setdefault(clave, []).append(parcela)

    grupos_creados: list[models.GrupoParcelas] = []
    for (especie, sistema), candidatas in cubos.items():
        if len(candidatas) < 2:
            continue
        # Agrupación por cercanía: se coge una parcela sin grupo y se le van
        # añadiendo las compatibles que estén a menos del radio.
        pendientes = list(candidatas)
        while pendientes:
            semilla = pendientes.pop(0)
            grupo = [semilla]
            resto: list[models.Parcela] = []
            for otra in pendientes:
                if geo.estan_cerca(centros[semilla.id], centros[otra.id], radio_km):
                    grupo.append(otra)
                else:
                    resto.append(otra)
            pendientes = resto
            if len(grupo) < 2:
                continue
            nombre = f"{especie.title()} ({len(grupo)} parcelas)"
            existente = db.scalar(
                select(models.GrupoParcelas).where(
                    models.GrupoParcelas.explotacion_id == explotacion_id,
                    models.GrupoParcelas.nombre == nombre,
                    models.GrupoParcelas.campana_id == campana_id,
                )
            )
            if existente is not None:
                continue
            nuevo = models.GrupoParcelas(
                explotacion_id=explotacion_id,
                nombre=nombre,
                campana_id=campana_id,
                cultivo=especie,
                sistema=sistema,
                creado_automaticamente=True,
            )
            nuevo.parcelas = list(grupo)
            db.add(nuevo)
            grupos_creados.append(nuevo)

    db.commit()
    return grupos_creados


def parcelas_que_no_se_pueden_juntar(
    db: Session, *, explotacion_id: int, campana_id: int | None
) -> dict:
    """Por qué no se ha podido juntar cada parcela que se ha quedado fuera.

    Existe para poder decirlo. Antes, el cálculo automático se callaba: pulsabas el botón, no
    pasaba nada, y no había forma de saber si era porque ya estaban juntas o porque faltaba algo.
    Un botón que no hace nada y no dice por qué es peor que no tenerlo.

    Las tres razones son las tres de verdad, y cada una se arregla de una manera distinta:
    sin cultivo declarado (se dice en «qué hay sembrado»), sin forma en el mapa (no hay dónde
    mirar si está cerca) y sin otra parcela igual con la que juntarse.
    """
    parcelas = list(
        db.scalars(select(models.Parcela).where(models.Parcela.explotacion_id == explotacion_id))
    )
    cultivos: dict[int, models.ParcelaCultivo] = {}
    if campana_id is not None:
        for cultivo in db.scalars(
            select(models.ParcelaCultivo).where(
                models.ParcelaCultivo.explotacion_id == explotacion_id,
                models.ParcelaCultivo.campana_id == campana_id,
            )
        ):
            cultivos[cultivo.parcela_id] = cultivo

    sin_cultivo = [p.alias for p in parcelas if p.id not in cultivos]
    sin_forma = [
        p.alias
        for p in parcelas
        if p.id in cultivos and geo.centroide_wkt(p.geometria) is None
    ]

    # Y de las que sí se pueden mirar, cuántas comparten cultivo y sistema con al menos otra.
    por_clave: dict[tuple[str, str], int] = {}
    for parcela in parcelas:
        cultivo = cultivos.get(parcela.id)
        if cultivo is None or geo.centroide_wkt(parcela.geometria) is None:
            continue
        clave = (cultivo.especie.strip().lower(), cultivo.sistema or parcela.sistema)
        por_clave[clave] = por_clave.get(clave, 0) + 1
    solas = [
        p.alias
        for p in parcelas
        if p.id in cultivos
        and geo.centroide_wkt(p.geometria) is not None
        and por_clave[
            (
                cultivos[p.id].especie.strip().lower(),
                cultivos[p.id].sistema or p.sistema,
            )
        ]
        < 2
    ]

    return {
        "sin_cultivo": sin_cultivo,
        "sin_forma": sin_forma,
        "solas": solas,
        "se_podrian_juntar": sum(1 for cuantos in por_clave.values() if cuantos >= 2),
    }


# --------------------------------------------------------------------------
# Qué se queda quieto cuando el agricultor corrige algo (rondas 92 y 94)
# --------------------------------------------------------------------------


def columnas_que_una_correccion_no_toca(modelo, entrada, salida) -> list[str]:
    """Las columnas de esa tabla que una corrección **deja como estaban**, y por qué.

    **La regla: solo se corrige lo que el formulario puede mandar de vuelta, y el formulario se
    rellena con lo que devuelve la API.** Una columna que la API no acepta al dar de alta
    (`entrada`) o que no devuelve nunca (`salida`) es un dato que el agricultor no puede ni ver ni
    escribir: si la corrección la copiara del registro preparado, **la borraría sin que nadie se
    entere**.

    Se **calcula** en vez de escribirse a mano a propósito: vale sola el día que se añada una columna
    nueva —lo que no se puede mandar, no se toca— y hay una prueba, por cada cosa que se corrige, que
    exige que salgan exactamente las que salen hoy.

    En las **tierras** protege la forma del trozo, la superficie oficial del SIGPAC y la fecha en que
    se apuntó; en un **papel** (`documentos_api`) protege su fichero: el nombre de disco, la ruta, el
    tipo y los bytes, que el formulario de corregir no manda —y no debe, porque cambiar de fichero
    tiene su propia puerta (`POST /api/documentos/{id}/fichero`), que además borra el viejo—. Meter
    un papel en otro sitio no puede dejarlo **sin su contrato**.

    Está aquí, y no en cada router, porque la regla es la misma para todo lo que se corrige. En
    `parcelas.py` quedó una copia con su nombre de siempre (`_columnas_que_una_correccion_no_toca`),
    de la ronda 92, que se unificará el día que se toque ese fichero.
    """
    acepta_la_entrada = set(entrada.model_fields)
    devuelve_la_salida = set(salida.model_fields)
    return [
        nombre
        for nombre in correcciones.campos_corregibles(modelo)
        if nombre not in acepta_la_entrada or nombre not in devuelve_la_salida
    ]
