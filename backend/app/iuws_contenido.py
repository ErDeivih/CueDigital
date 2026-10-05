"""El contenido mínimo del CUE, campo por campo, tal y como lo numera SIEX.

Fuente: `09_FEGA_Documento_Tecnico_SIEX_v3.11_CONTENIDO_MINIMO_CUE.pdf`, «Anexo II. Bloques
de información del contenido mínimo». Cada bloque lleva **el nombre y el número de campo que
le da el documento**, para que lo que sale de aquí se pueda cotejar línea a línea con el
papel sin tener que interpretar nada.

## Cómo está organizado, y por qué así

Cada bloque se describe con una lista de `Campo`, y cada `Campo` sabe de dónde sale su valor:

    Campo(numero=1, nombre="Superficie tratada (ha)", de="superficie_tratada_ha", tipo="numero")

El `de` es un atributo del registro. Se resuelve con `getattr` y **si no está, el campo sale
a `None`**. No hay valores por defecto ni de relleno: un campo vacío se distingue de un cero,
que es la diferencia entre «no lo sé» y «es cero», y en un volcado oficial esa diferencia
importa.

## Lo que este módulo NO hace

No genera el JSON del descriptor v3.11.4. El fichero y su esquema oficial están en
`data/iuws_fuentes/`, pero falta el mapeo completo (ver `iuws.py`). Lo que hace es volcar los datos en el
**orden del contenido mínimo**, que sí está documentado, con el identificador ajeno de cada
actividad ya puesto para poder corregirla después sin duplicarla.

## La marca de los catálogos

Muchos campos dicen «(según catálogo)»: hay que mandar un **código numérico** que no tenemos.
Esos campos salen con `catalogo=True` y **valor `None`**, y se listan aparte en
`campos_de_catalogo()`. Poner un número inventado sería lo peor que se puede hacer aquí: el
interfaz lo rechazaría, o peor, guardaría el producto equivocado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import catalogos, iuws, legal, sigpac


@dataclass(frozen=True)
class Campo:
    """Un campo del contenido mínimo, con su número y de dónde sale su valor."""

    numero: int
    nombre: str
    de: str | None = None
    tipo: str = "texto"
    # `True` cuando el documento dice «(según catálogo)»: el valor es un código, no un texto.
    catalogo: bool = False
    # De qué lista oficial sale el código, cuando la tenemos. Lo que falta por cargar está
    # en `catalogos.limites_que_faltan()` si una tabla no está disponible, y lo que falta
    # para poder enviar, en `iuws.QUE_FALTA`.
    catalogo_de: str | None = None
    obligatorio: bool = False
    nota: str = ""


@dataclass
class Bloque:
    """Un bloque del contenido mínimo: su nombre, su ámbito y sus campos."""

    clave: str
    nombre: str
    nivel: str
    campos: list[Campo] = field(default_factory=list)
    filas: list[dict] = field(default_factory=list)


# --------------------------------------------------------------------------
# Los bloques que se pueden rellenar con lo que hay en el cuaderno
#
# El orden es el del documento. El número de cada campo también.
# --------------------------------------------------------------------------

BLOQUES: dict[str, tuple[str, str, list[Campo]]] = {
    # --- bloques por explotación ---
    "datos_generales": (
        "1. Datos generales de la explotación",
        "explotacion",
        [
            Campo(1, "Código (del REA correspondiente)", "codigo_siex", obligatorio=True),
            Campo(9, "Entidad habilitada REA", tipo="codigo", catalogo=True),
            Campo(10, "Entidad habilitada CUE", tipo="codigo", catalogo=True),
            Campo(11, "CUE-Comercial", tipo="codigo", catalogo=True),
        ],
    ),
    "datos_titular": (
        "2. Datos del titular",
        "explotacion",
        [
            Campo(1, "NIF del titular", "nif", obligatorio=True),
            Campo(2, "Nombre / Razón Social", "nombre", obligatorio=True),
            Campo(8, "Provincia (listado INE)", "provincia"),
            Campo(9, "Municipio (listado INE)", "municipio"),
        ],
    ),
    "edificaciones": (
        "8. Datos de edificaciones e instalaciones",
        "instalacion",
        [
            Campo(1, "Edificaciones e instalaciones", "tipo", catalogo=True, obligatorio=True),
            Campo(2, "Referencia catastral", "referencia_catastral"),
            Campo(6, "Dimensión (superficie construida/instalada en m2)", "superficie_m2", "numero"),
        ],
    ),
    "maquinaria": (
        "9. Datos de Maquinaria y equipos",
        "equipo",
        [Campo(1, "Nº inscripción maquinaria (ROMA)", "numero_roma", obligatorio=True)],
    ),
    # --- bloques por superficie: la parcela y su cultivo ---
    "superficies": (
        "12. Datos de superficies",
        "parcela",
        [
            Campo(6, "Código de Polígono", "poligono", "entero"),
            Campo(7, "Código de Parcela", "numero_parcela", "entero"),
            Campo(8, "Código de Recinto", "numero_recinto", "entero"),
            Campo(15, "Superficie DGC (ha, dos decimales)", "superficie_ha", "numero", obligatorio=True),
            Campo(18, "Geometría (WKT)", "geometria"),
        ],
    ),
    # --- bloques por explotación del cuaderno ---
    "medidas_preventivas": (
        "GIP a nivel de explotación: 1.1 Medidas preventivas/culturales",
        "medida",
        [
            Campo(
                1,
                "Medida preventiva/cultural",
                "medida",
                catalogo=True,
                obligatorio=True,
                nota="El código del catálogo; el nombre oficial va aparte, en `etiqueta`.",
            )
        ],
    ),
    "cosecha_comercializada": (
        "3. Cosecha comercializada y/o venta directa",
        "venta",
        [
            # OJO con la numeración de este bloque, que es la del documento y no la que
            # parece: los campos 2 y 3 son de la venta a un comprador y los 4 y 5 son de la
            # venta directa. Es la única sección del contenido mínimo que numera dos veces lo
            # mismo, porque separa las dos clases de venta. Inventarse un campo 4 «Unidad»
            # habría sido un error: en la primera versión de esto estaba, y lo cazó el test
            # que coteja el número con el nombre.
            Campo(1, "Fecha (intervalo de tiempo)", "fecha", "fecha", obligatorio=True),
            Campo(
                2,
                "Producto vegetal (venta de cosecha comercializada)",
                "producto",
                catalogo=True,
                catalogo_de="producto",
                obligatorio=True,
            ),
            Campo(
                3,
                "Cantidad de producto vegetal (venta de cosecha comercializada)",
                "cantidad",
                "numero",
                obligatorio=True,
            ),
            Campo(
                4,
                "Producto vegetal (venta directa)",
                "producto",
                catalogo=True,
                catalogo_de="producto",
            ),
            Campo(
                5,
                "Cantidad de producto vegetal (venta directa)",
                "cantidad",
                "numero",
            ),
        ],
    ),
    # --- bloques por superficie del cuaderno ---
    "labores": (
        "5. Labores culturales",
        "labor",
        [
            Campo(1, "Fecha inicio", "fecha", "fecha", obligatorio=True),
            Campo(3, "Cultivo/s", "cultivo", catalogo=True, catalogo_de="producto"),
            Campo(4, "Superficie de labor (ha)", "superficie_ha", "numero"),
        ],
    ),
    # El agua de riego: el documento la sitúa en el SUBBLOQUE DE FERTIRRIGACIÓN del bloque de
    # fertilización (campos 34 a 42), porque «el agua que riegas también abona». Nosotros la
    # guardamos en la labor de riego, que es donde el agricultor la apunta cuando riega, y al
    # volcar se lleva a su sitio. Es una decisión, no un descuido: apuntar el agua en la
    # ficha de un abono que no se ha echado sería pedirle al agricultor que apunte algo que no
    # ha pasado.
    "riego": (
        "9. Fertilización: información del agua y del sistema de riego (fertirrigación)",
        "labor",
        [
            Campo(34, "Sistema de riego", "sistema_riego", catalogo=True),
            Campo(35, "Cantidad de agua", "volumen_agua", "numero"),
            Campo(37, "Unidad", "unidad_agua", catalogo=True),
            Campo(38, "Procedencia del agua de riego", "origen_agua", catalogo=True),
            Campo(40, "Nº contador", "numero_contador"),
            Campo(41, "N nítrico del agua (mg/l o ppm)", "nitratos_agua", "numero"),
        ],
    ),
    "siembra_plantacion": (
        "6. Siembra / Plantación",
        "siembra",
        [
            Campo(1, "Fecha inicio", "fecha", "fecha", obligatorio=True),
            Campo(3, "Cultivo", "cultivo", catalogo=True, catalogo_de="producto"),
            Campo(4, "Cantidad (kg de semilla)", "cantidad_semilla_kg", "numero"),
            Campo(5, "Dosis de siembra (kg semilla/ha)", "dosis_siembra_kg_ha", "numero"),
            # El campo 6 («Unidades de siembra», para la remolacha) **no se vuelca**: el
            # control de versiones del Anexo VI dice que «se elimina el campo UnidadesSiembra
            # del descriptor de CUE». Ponerlo sería volcar un campo que ya no existe.
            Campo(7, "Material tratado (S/N)", "material_tratado", "si_no"),
            Campo(8, "Material adquirido (S/N)", "material_adquirido", "si_no"),
            Campo(9, "Fecha de adquisición", "fecha_adquisicion", "fecha"),
            Campo(10, "N.º Lote de semilla adquirida", "lote_semilla"),
            Campo(11, "Superficie sembrada/plantada (ha)", "superficie_ha", "numero"),
            Campo(12, "Siembra directa (S/N)", "siembra_directa", "si_no"),
            Campo(14, "Densidad de plantación (nº plantas/ha)", "densidad_plantacion", "numero"),
            Campo(15, "Marco de plantación", "marco_plantacion"),
        ],
    ),
    "tratamientos": (
        "8. Tratamientos fitosanitarios",
        "tratamiento",
        [
            Campo(1, "Fecha inicio de tratamiento", "fecha", "fecha", obligatorio=True),
            Campo(3, "Hora de tratamiento", "hora_inicio"),
            Campo(5, "Superficie tratada (ha)", "superficie_tratada_ha", "numero", obligatorio=True),
            Campo(6, "Cultivo", "cultivo", catalogo=True, catalogo_de="producto"),
            Campo(
                8,
                "Estado fenológico",
                "estado_cultivo",
                catalogo=True,
                nota=(
                    "El documento lo pide «según catálogo», y el catálogo oficial de estados "
                    "fenológicos no lo tenemos cargado: va vacío y marcado. Lo que el agricultor "
                    "escribe en su cuaderno sale en el papel, no aquí."
                ),
            ),
            Campo(15, "Justificación de la actuación", "justificacion", catalogo=True),
            Campo(17, "Cantidad", "cantidad_total", "numero"),
            Campo(18, "Unidad de medida", "unidad_dosis", catalogo=True),
            Campo(22, "Nombre comercial", "producto_nombre"),
            Campo(24, "Número de registro", "numero_registro"),
            Campo(26, "Dosis", "dosis", "numero"),
            Campo(28, "Nombre del aplicador", "aplicador_nombre"),
            Campo(32, "NIF del aplicador", "aplicador_nif"),
            Campo(33, "Nº inscripción ROPO", "aplicador_ropo"),
            Campo(35, "Nº inscripción ROMA o REGANIP", "equipo_roma"),
            # El asesoramiento (campos 44 a 53). El 44 es la fecha y el 50 el número de ROPO
            # **del asesor**, que es un registro distinto del de aplicadores: el interfaz
            # rechaza el tratamiento si no lo encuentra en ROPO (error 7).
            Campo(44, "Fecha del asesoramiento", "asesor_fecha", "fecha"),
            Campo(45, "Nombre del asesor", "asesor_nombre"),
            Campo(49, "NIF del asesor", "asesor_nif"),
            Campo(50, "Nº inscripción ROPO del asesor", "asesor_ropo"),
            Campo(51, "Validación del tratamiento (Favorable/Desfavorable)", "asesoramiento_validado", "si_no"),
            Campo(53, "Contrato de asesoramiento (S/N)", "asesoramiento_contrato", "si_no"),
            Campo(54, "Eficacia del tratamiento", "eficacia", catalogo=True),
            Campo(55, "Observaciones", "observaciones"),
        ],
    ),
    "fertilizacion": (
        "9. Fertilización",
        "fertilizacion",
        [
            Campo(1, "Fecha de actuación o de inicio", "fecha", "fecha", obligatorio=True),
            Campo(3, "Cultivo", "cultivo", catalogo=True, catalogo_de="producto"),
            Campo(4, "Superficie aplicación", "superficie_ha", "numero", obligatorio=True),
            Campo(7, "Material fertilizante", "fertilizante_nombre", catalogo=True),
            Campo(8, "Detalle material fertilizante", "tipo", catalogo=True),
        ],
    ),
    "analiticas": (
        "13. Analíticas en caso de haberse realizado",
        "analitica",
        [
            Campo(1, "Material analizado", "tipo", catalogo=True, obligatorio=True),
            Campo(2, "Fecha de toma de muestra", "fecha_toma_muestra", "fecha", obligatorio=True),
            Campo(3, "Razón Social del Laboratorio", "laboratorio"),
            Campo(4, "NIF del Laboratorio", "nif_laboratorio"),
            Campo(5, "Nº boletín de análisis", "numero_informe"),
            Campo(6, "Tipo de análisis", "tipo_analisis", catalogo=True),
        ],
    ),
}

# Los nueve parámetros del suelo, con su número en el documento. Se añaden como campos
# propios de las analíticas de tierra: el documento los numera del 8 al 16 dentro del bloque.
PARAMETROS_SUELO_NUMERADOS = (
    (8, "Materia Orgánica (%)", "materia_organica"),
    (9, "Arena (%)", "arena"),
    (10, "Limo (%)", "limo"),
    (11, "Arcilla (%)", "arcilla"),
    (12, "pH", "ph"),
    (13, "Fósforo asimilable (ppm)", "fosforo_asimilable"),
    (14, "Potasio asimilable (ppm)", "potasio_asimilable"),
    (15, "Nitrógeno Total (%)", "nitrogeno_total"),
    (16, "Conductividad eléctrica a 25 ºC (dS/m)", "conductividad"),
)


def _numero(valor):
    """Un número tal y como lo espera un volcado: sin redondear a mano y sin ceros de más."""
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return round(numero, 4)


def _fecha(valor):
    """Fecha en formato ISO, que es el que se puede comparar y ordenar.

    El anexo usa `dd/mm/aaaa` en sus ejemplos, pero también avisa de que esos ejemplos no
    tienen por qué corresponder a la v2.6. Se manda ISO y **se dice** en el paquete, en vez de
    elegir a cara o cruz: cambiar el formato es una línea, adivinar mal es un volcado hecho
    polvo.
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor
    return valor.isoformat()


def _valor(registro, campo: Campo):
    """El valor de un campo, o None si no está.

    **Los campos «según catálogo» y el catálogo que tenemos.** Hasta la ronda 10 todos salían
    vacíos, porque no teníamos los códigos oficiales. Ahora sí tenemos los del SIGPAC
    (provincias, usos, aprovechamientos, incidencias y 933 productos), así que:

    * Si el campo tiene `catalogo_de` y el valor es un nombre que está en esa lista oficial, se
      manda **el código oficial**. Eso es lo que hace que el volcado sirva para algo.
    * Si el nombre no está en la lista, se manda `None`. **No se inventa un código**: un código
      mal puesto no da error al mandarlo, guarda el producto equivocado.
    * Si el campo es de un catálogo que no tenemos (tipo de producto fitosanitario, materia
      activa, estado fenológico, eficacia, unidad de medida), sale `None` como siempre.

    `registro` puede ser una fila de la base de datos o un diccionario. Los dos casos se
    contemplan porque algunos bloques necesitan aplanar el registro antes de volcarlo (un
    tratamiento, por ejemplo, guarda el aplicador y el equipo como identificadores y el
    contenido mínimo los pide como texto). Se descubrió con un test que daba el campo vacío:
    `getattr` sobre un diccionario no devuelve nada, y el volcado habría salido sin fechas.
    """
    if isinstance(registro, dict):
        valor = registro.get(campo.de) if campo.de else None
        detalles = registro.get("detalles")
    else:
        valor = getattr(registro, campo.de, None) if campo.de else None
        detalles = getattr(registro, "detalles", None)

    if valor is None and campo.de:
        # Algunos datos van dentro de un JSON (los detalles de una labor, por ejemplo).
        if isinstance(detalles, dict):
            valor = detalles.get(campo.de)

    if campo.catalogo:
        return _codigo_de_catalogo(campo, valor)

    if campo.tipo == "numero":
        return _numero(valor)
    if campo.tipo == "entero":
        return int(valor) if valor is not None else None
    if campo.tipo == "fecha":
        return _fecha(valor)
    if campo.tipo == "si_no":
        if valor is None:
            return None
        return "S" if valor else "N"
    if valor is None:
        return None
    return str(valor)


def _codigo_de_catalogo(campo: Campo, valor):
    """El código oficial de un valor, o None si no se puede saber.

    Hoy solo hay una lista oficial que podamos casar por nombre: la de productos del SIGPAC, que
    es la que el volcado llama «Producto vegetal (según catálogo)» y «Cultivo (según catálogo)».
    """
    if not campo.catalogo_de or valor is None:
        return None
    if campo.catalogo_de == "producto":
        codigo, _nombre = sigpac.busca_producto(str(valor))
        return codigo
    if campo.catalogo_de == "uso_sigpac":
        codigo = str(valor).strip().upper()
        return codigo if codigo in sigpac.usos_oficiales() else None
    return None


def fila(bloque: str, registro, *, identificador: str | None = None, **extra) -> dict:
    """Convierte un registro en una fila del bloque, con sus campos numerados.

    La clave de cada campo es `c{numero}`, y va acompañada de `c{numero}_nombre` la primera
    vez. Así el volcado se puede leer sin tener el documento delante, y a la vez se puede
    cotejar con él.
    """
    _nombre, _nivel, campos = BLOQUES[bloque]
    salida: dict = {}
    if identificador is not None:
        # El identificador ajeno: es lo que permite corregir una actividad ya cargada en vez
        # de duplicarla. Ver `iuws.id_ajeno`.
        salida["IdAjena"] = identificador
    for campo in campos:
        clave = f"c{campo.numero}"
        salida[clave] = _valor(registro, campo)
        salida[f"{clave}_nombre"] = campo.nombre
        if campo.catalogo:
            salida[f"{clave}_catalogo"] = True
    salida.update(extra)
    return salida


def campos_de_catalogo(bloque: str | None = None) -> list[dict]:
    """Los campos que no se pueden rellenar porque su valor es un código de catálogo.

    Se listan aparte para poder decir exactamente qué hace falta, en vez de mandar el campo
    vacío sin explicar por qué.
    """
    salida: list[dict] = []
    claves = [bloque] if bloque else list(BLOQUES)
    for clave in claves:
        if clave not in BLOQUES:
            continue
        nombre, _nivel, campos = BLOQUES[clave]
        for campo in campos:
            if campo.catalogo:
                salida.append(
                    {
                        "bloque": nombre,
                        "numero": campo.numero,
                        "campo": campo.nombre,
                        "obligatorio": campo.obligatorio,
                    }
                )
    return salida


def resumen_de_bloques() -> list[dict]:
    """Qué bloques se vuelcan, con cuántos campos y cuántos de ellos son de catálogo."""
    salida = []
    for clave, (nombre, nivel, campos) in BLOQUES.items():
        salida.append(
            {
                "clave": clave,
                "nombre": nombre,
                "nivel": nivel,
                "campos": len(campos),
                "de_catalogo": sum(1 for campo in campos if campo.catalogo),
                "obligatorios": sum(1 for campo in campos if campo.obligatorio),
                "fuente_del_documento": "Documento técnico SIEX v3.11, Anexo II",
            }
        )
    return salida


# --------------------------------------------------------------------------
# Volcado de una finca
# --------------------------------------------------------------------------


def _fila_de_tratamiento(db, tratamiento) -> dict:
    """Aplana un tratamiento con los nombres del aplicador y del equipo ya resueltos.

    Se resuelven aquí y no en el campo porque el contenido mínimo los pide como texto
    (nombre, NIF, ROPO, ROMA) y el tratamiento guarda identificadores.
    """
    from . import models

    aplicador = db.get(models.Aplicador, tratamiento.aplicador_id) if tratamiento.aplicador_id else None
    equipo = db.get(models.EquipoAplicacion, tratamiento.equipo_id) if tratamiento.equipo_id else None
    asesor = db.get(models.Asesor, tratamiento.asesor_id) if tratamiento.asesor_id else None
    return {
        "fecha": tratamiento.fecha,
        "hora_inicio": tratamiento.hora_inicio,
        "superficie_tratada_ha": tratamiento.superficie_tratada_ha,
        "cultivo": tratamiento.cultivo,
        "justificacion": tratamiento.justificacion,
        "cantidad_total": tratamiento.cantidad_total,
        "unidad_dosis": tratamiento.unidad_dosis,
        "producto_nombre": tratamiento.producto_nombre,
        "numero_registro": tratamiento.numero_registro,
        "dosis": tratamiento.dosis,
        "aplicador_nombre": getattr(aplicador, "nombre", None),
        "aplicador_nif": getattr(aplicador, "nif", None),
        "aplicador_ropo": getattr(aplicador, "numero_ropo", None),
        "equipo_roma": getattr(equipo, "numero_roma", None),
        "asesor_fecha": tratamiento.asesor_fecha,
        "asesor_nombre": getattr(asesor, "nombre", None),
        "asesor_nif": getattr(asesor, "nif", None),
        "asesor_ropo": getattr(asesor, "numero_ropo", None),
        "asesoramiento_validado": tratamiento.asesoramiento_validado,
        "asesoramiento_contrato": tratamiento.asesoramiento_contrato,
        # El estado de la planta. Lo pide el contenido mínimo en su campo 8, «Estado Fenológico
        # (según catálogo)», y **no estaba declarado en este bloque**: el campo existía en la
        # tabla, no se podía rellenar desde ninguna pantalla y el volcado ni siquiera lo nombraba.
        # Ahora se declara, y va con el resto de los campos de catálogo: vacío y marcado, porque
        # el catálogo oficial de estados fenológicos no lo tenemos.
        "estado_cultivo": tratamiento.estado_cultivo,
        "eficacia": None,
        "observaciones": tratamiento.observaciones,
    }


def contenido_de_la_finca(db, *, explotacion, campana) -> dict:
    """Todo lo del cuaderno de una campaña, en el orden del contenido mínimo.

    Se devuelve un diccionario con un bloque por sección, cada uno con sus filas. Cada fila
    lleva el `IdAjena` de su actividad y los campos numerados como en el documento.

    Decisión: las actividades anuladas **no** se vuelcan. Lo que se anuló no pasó, y mandarlo
    a la Junta sería mandar un dato que el agricultor ya dijo que no era bueno.
    """
    from sqlalchemy import select

    from . import models, servicios

    nif = explotacion.nif
    datos: dict = {"datos_explotacion": {}, "actividades": {}, "resumen": {}, "catalogos_que_faltan": []}

    # --- explotación y titular ---
    explotacion_fila = fila("datos_generales", explotacion)
    explotacion_fila.update(fila("datos_titular", explotacion))
    datos["datos_explotacion"] = explotacion_fila
    datos["actividades"]["datos_generales"] = [explotacion_fila]

    # --- medidas preventivas (a nivel de finca, sin campaña) ---
    medidas = [
        fila("medidas_preventivas", medida, identificador=iuws.id_ajeno(nif, "medida", medida.id),
             etiqueta=catalogos.etiqueta_medida(medida.medida))
        for medida in servicios.medidas_declaradas(db, explotacion_id=explotacion.id, solo_aplicadas=True)
    ]

    # --- tratamientos, separados por la clase que pide el documento ---
    tratamientos = list(
        db.scalars(
            select(models.TratamientoFitosanitario).where(
                models.TratamientoFitosanitario.explotacion_id == explotacion.id,
                models.TratamientoFitosanitario.campana_id == campana.id,
                models.TratamientoFitosanitario.anulado.is_(False),
            )
        )
    )
    de_parcela = [t for t in tratamientos if t.tipo in catalogos.TRATAMIENTO_EN_PARCELA]
    de_nave = [t for t in tratamientos if t.tipo == "instalaciones"]

    datos["actividades"]["tratamientos"] = [
        fila(
            "tratamientos",
            _fila_de_tratamiento(db, t),
            identificador=iuws.id_ajeno(nif, "tratamiento", t.id),
            DGC=t.parcela_id,
            IdAjenaBorrar=None,
        )
        for t in de_parcela
    ]
    datos["actividades"]["tratamientos_postcosecha"] = [
        fila(
            "tratamientos",
            _fila_de_tratamiento(db, t),
            identificador=iuws.id_ajeno(nif, "tratamiento", t.id),
            producto_cosechado=t.producto_cosechado,
            lote_cosecha=t.lote_cosecha,
        )
        for t in tratamientos
        if t.tipo == "postcosecha"
    ]
    datos["actividades"]["tratamientos_instalaciones"] = [
        fila(
            "tratamientos",
            _fila_de_tratamiento(db, t),
            identificador=iuws.id_ajeno(nif, "tratamiento", t.id),
            instalacion=t.instalacion_id,
            plazo_reentrada_dias=t.plazo_reentrada_dias,
        )
        for t in de_nave
    ]

    # --- fertilización ---
    datos["actividades"]["fertilizacion"] = [
        fila(
            "fertilizacion",
            {
                "fecha": registro.fecha,
                "cultivo": None,
                "superficie_ha": registro.superficie_ha,
                "fertilizante_nombre": registro.fertilizante_nombre,
                "tipo": registro.tipo,
            },
            identificador=iuws.id_ajeno(nif, "fertilizacion", registro.id),
            DGC=registro.parcela_id,
            kg_ha_producto=_numero(registro.kg_ha_producto),
            uf_n_ha=_numero(registro.uf_n_ha),
            uf_p_ha=_numero(registro.uf_p_ha),
            uf_k_ha=_numero(registro.uf_k_ha),
        )
        for registro in db.scalars(
            select(models.RegistroFertilizacion).where(
                models.RegistroFertilizacion.explotacion_id == explotacion.id,
                models.RegistroFertilizacion.campana_id == campana.id,
                models.RegistroFertilizacion.anulado.is_(False),
            )
        )
    ]

    # --- labores, con la siembra aparte porque el documento la numera aparte ---
    labores = list(
        db.scalars(
            select(models.Labor).where(
                models.Labor.explotacion_id == explotacion.id,
                models.Labor.campana_id == campana.id,
                models.Labor.anulado.is_(False),
            )
        )
    )
    datos["actividades"]["labores"] = [
        fila("labores", labor, identificador=iuws.id_ajeno(nif, "labor", labor.id), DGC=labor.parcela_id)
        for labor in labores
        if labor.tipo not in ("siembra", "plantacion", "riego")
    ]
    # El agua de riego va en su propio bloque, con la numeración del subbloque de
    # fertirrigación del documento. Ver la nota de `BLOQUES["riego"]`.
    datos["actividades"]["riego"] = [
        fila("riego", labor, identificador=iuws.id_ajeno(nif, "labor", labor.id), DGC=labor.parcela_id)
        for labor in labores
        if labor.tipo == "riego"
    ]
    datos["actividades"]["siembra_plantacion"] = [
        fila("siembra_plantacion", labor, identificador=iuws.id_ajeno(nif, "labor", labor.id), DGC=labor.parcela_id)
        for labor in labores
        if labor.tipo in ("siembra", "plantacion")
    ]

    # --- lo que se vende ---
    #
    # El documento numera la venta de cosecha comercializada en los campos 2 y 3, y la venta
    # directa en los 4 y 5. Así que cada venta rellena los suyos y deja los otros fuera: una
    # venta directa en el campo de la comercializada sería un dato mal puesto.
    filas_ventas = []
    for venta in db.scalars(
        select(models.VentaDeCosecha).where(
            models.VentaDeCosecha.explotacion_id == explotacion.id,
            models.VentaDeCosecha.campana_id == campana.id,
            models.VentaDeCosecha.anulado.is_(False),
        )
    ):
        fila_venta = fila(
            "cosecha_comercializada",
            venta,
            identificador=iuws.id_ajeno(nif, "venta", venta.id),
            tipo_venta=venta.tipo,
            comprador=venta.comprador,
            lote=venta.lote,
            numero_albaran=venta.numero_albaran,
            fecha_fin=_fecha(venta.fecha_fin),
            unidad=venta.unidad,
            kilos=catalogos.kilos_de_una_venta(venta.cantidad, venta.unidad),
        )
        if venta.tipo == "venta_directa":
            # Se queda solo con los campos de la venta directa (4 y 5) más la fecha.
            fila_venta = {
                clave: valor
                for clave, valor in fila_venta.items()
                if not clave.startswith("c2") and not clave.startswith("c3")
            }
        else:
            fila_venta = {
                clave: valor
                for clave, valor in fila_venta.items()
                if not clave.startswith("c4") and not clave.startswith("c5")
            }
        filas_ventas.append(fila_venta)
    datos["actividades"]["cosecha_comercializada"] = filas_ventas

    # --- analíticas, con los nueve números del suelo numerados como en el documento ---
    filas_analiticas = []
    for analitica in db.scalars(
        select(models.Analitica).where(
            models.Analitica.explotacion_id == explotacion.id,
            models.Analitica.anulado.is_(False),
        )
    ):
        fila_analitica = fila(
            "analiticas", analitica, identificador=iuws.id_ajeno(nif, "analitica", analitica.id)
        )
        for parametro in analitica.parametros or []:
            if not isinstance(parametro, dict):
                continue
            for numero, _nombre, clave in PARAMETROS_SUELO_NUMERADOS:
                if parametro.get("clave") == clave:
                    fila_analitica[f"c{numero}"] = _numero(parametro.get("valor"))
                    fila_analitica[f"c{numero}_nombre"] = _nombre
        filas_analiticas.append(fila_analitica)
    datos["actividades"]["analiticas"] = filas_analiticas

    # --- instalaciones y maquinaria ---
    datos["actividades"]["edificaciones"] = [
        fila("edificaciones", instalacion, identificador=iuws.id_ajeno(nif, "instalacion", instalacion.id))
        for instalacion in db.scalars(
            select(models.Instalacion).where(models.Instalacion.explotacion_id == explotacion.id)
        )
    ]
    datos["actividades"]["maquinaria"] = [
        fila("maquinaria", equipo, identificador=iuws.id_ajeno(nif, "equipo", equipo.id))
        for equipo in db.scalars(
            select(models.EquipoAplicacion).where(
                models.EquipoAplicacion.explotacion_id == explotacion.id
            )
        )
    ]

    # --- superficies: la parcela y su cultivo ---
    datos["actividades"]["superficies"] = [
        fila(
            "superficies",
            parcela,
            identificador=iuws.id_ajeno(nif, "parcela", parcela.id),
            referencia_sigpac=parcela.ref_sigpac,
        )
        for parcela in db.scalars(
            select(models.Parcela).where(models.Parcela.explotacion_id == explotacion.id)
        )
    ]

    datos["actividades"]["medidas_preventivas"] = medidas

    # --- resumen, para poder comprobarlo de un vistazo ---
    datos["catalogos_que_faltan"] = campos_de_catalogo()
    datos["resumen"] = {
        "bloques": resumen_de_bloques(),
        "filas_por_bloque": {clave: len(filas) for clave, filas in datos["actividades"].items()},
        "total_actividades": sum(len(filas) for filas in datos["actividades"].values()),
        "campos_de_catalogo": len(datos["catalogos_que_faltan"]),
        "generado_con": "documento técnico SIEX v3.11, Anexo II (contenido mínimo)",
    }
    return datos
