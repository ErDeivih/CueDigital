"""El vocabulario de la interfaz, en una sola llamada.

La interfaz pide esto una vez al arrancar y lo guarda. Así funciona sin cobertura
después, y así el test que garantiza que no hay jerga cubre TODO lo que se ve en
pantalla, no solo los mensajes de la API.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import catalogos, contactos, gastos, legal, maquinaria, semillas, sigpac, textos, ventas

router = APIRouter(prefix="/api", tags=["interfaz"])


@router.get("/interfaz")
def interfaz() -> dict:
    return {
        # Pantallas
        "pantalla_inicio": textos.PANTALLA_INICIO,
        "pantalla_entrar": textos.PANTALLA_ENTRAR,
        "trabajos": list(textos.TRABAJOS),
        "cuaderno": textos.PANTALLA_CUADERNO,
        # El mapa: sus botones, sus avisos y las cuatro formas de contar la zona de nitratos.
        # Sin esto la pantalla sale con los botones en blanco: los textos viven aquí, y el
        # JavaScript solo los pide.
        "mapa": textos.MAPA,
        # Traer las tierras del cuaderno de la Junta: la pantalla que evita teclear 54 parcelas.
        "cuaderno_cyl": textos.CUADERNO_CYL,
        # Los datos del titular y de la finca: la portada del cuaderno de la Junta.
        "mis_datos": textos.MIS_DATOS,
        # Quién entra en la finca y en cuál se está trabajando (varias cuentas en la misma finca, ronda
        # 89). Sin esto, la pantalla sale con los botones en blanco: las palabras viven aquí y el
        # JavaScript solo las pide.
        "fincas": textos.FINCAS,
        # Qué es el registro electrónico, dónde se apunta y los enlaces oficiales.
        "registro_electronico": textos.REGISTRO_ELECTRONICO,
        # Las facturas de compra: subirlas, leerlas y confirmarlas.
        "facturas": textos.FACTURAS,
        # Dar de alta lo que se usa. Sin esto, al agricultor nuevo se le pide algo que
        # la aplicación no le deja hacer.
        "maestros": textos.MAESTROS,
        "dictado": textos.DICTADO,
        # Lo que se dice si los ficheros de React de `web/vendor/` no llegaran a cargarse:
        # sin esto, esa pantalla se quedaría en blanco, y el aviso de emergencia no tiene
        # ni una palabra escrita en el JavaScript.
        "react": textos.REACT,
        # **La búsqueda global** (07/10/2026): las palabras de la caja de la cabecera y de su pantalla de
        # resultados. La puerta ya está hecha y probada (`GET /api/buscar`, con sus cinco grupos); esto es
        # lo que le falta a la pantalla para no tener ni una frase escrita a mano.
        "buscar": textos.BUSCAR,
        # La normativa: las reglas de la matriz, con su fuente oficial (07/10/2026).
        "normativa": textos.NORMATIVA,
        "certificado": textos.CERTIFICADO,
        "firma": textos.FIRMA,
        "plan": textos.PLAN,
        "analitica": textos.ANALITICA,
        "ayuda": {
            "pantalla": textos.PANTALLA_AYUDA,
            "porques": textos.PORQUE,
            # El título corto de cada porqué y de cada punto de la ley (ronda 83): la pantalla de ayuda los
            # enseña **cada uno con su nombre**. Sin esto eran párrafos seguidos sin nombre, que se leen
            # como un muro.
            "porque_titulos": textos.PORQUE_TITULOS,
            "campos": [
                {"campo": campo, **datos} for campo, datos in sorted(textos.AYUDA.items())
            ],
            # Los cuatro rótulos de la ayuda de un campo («Qué es:», «Por qué te lo piden:»…). Salen
            # de `textos.py` y no del JavaScript: son frases que lee el agricultor.
            "rotulos_de_un_campo": textos.ROTULOS_DE_LA_AYUDA_DE_UN_CAMPO,
        },
        # Palabras de los botones y de los estados
        "acciones": textos.ACCIONES,
        "aviso": textos.INTERFAZ,
        "rotulos": textos.ROTULOS,
        "mensajes": textos.MENSAJES,
        # Lo que se le pregunta al agricultor, campo a campo. Las de las pantallas de
        # alta se juntan con las del asistente: para la interfaz son lo mismo.
        "etiquetas": {**textos.ETIQUETAS, **textos.ETIQUETAS_MAESTRO},
        # Listas para elegir
        "medidas_preventivas": [
            {"codigo": m.codigo, "pregunta": m.pregunta, "etiqueta": m.etiqueta}
            for m in catalogos.MEDIDAS_PREVENTIVAS
        ],
        # Las medidas preventivas de la finca: la sección que se declara una vez y vale
        # para todo el año, y que después alimenta el apunte de cada tratamiento.
        "medidas": textos.MEDIDAS,
        # El conector con el SIGPAC: traer la parcela sin teclearla.
        "sigpac": textos.SIGPAC,
        # Lo que se vende: la app oficial lo llama «cosecha comercializada».
        "venta": textos.VENTA,
        # **La factura nuestra y el cobro** (T12, E6, 03/10/2026): las palabras de las pantallas del
        # dinero. Van aquí, y no solo dentro de las respuestas de la API, por el mismo motivo que las
        # del almacén y las de los contactos: **esto se guarda en el móvil**, y una pantalla que se
        # abre sin cobertura tiene que tener sus palabras. Y hay una razón más en este caso: los
        # avisos de que la factura **no** es un documento con validez oficial tienen que salir siempre,
        # también cuando la pantalla se abre con datos que llegaron antes.
        "factura_emitida": textos.FACTURA_EMITIDA,
        "cobro": textos.COBRO,
        # Las dos listas cerradas del dinero, con su orden y con su nombre: los cuatro tipos de ajuste
        # (devolución, peso, humedad y calidad) y las cinco formas de cobro. El orden importa y por eso
        # no se saca de las claves del diccionario: unos botones que cambian de sitio se pulsan mal.
        "tipos_de_ajuste": [
            {"valor": valor, "texto": textos.VENTA["tipos_de_ajuste"][valor]}
            for valor in ventas.TIPOS_DE_AJUSTE
        ],
        "origenes_de_un_ajuste": [
            {"valor": valor, "texto": textos.VENTA["origenes_de_un_ajuste"][valor]}
            for valor in ventas.ORIGENES_DE_UN_AJUSTE
        ],
        # Los papeles que acompañan al cuaderno: la app oficial lo llama «Documentación».
        "documentos": textos.DOCUMENTOS,
        # Corregir y borrar lo que uno ha introducido (ronda 91): los dos botones de cada apunte,
        # el título y la pista de cuando se está corrigiendo y la pregunta de si de verdad se
        # quiere borrar. Sin esto, los botones salen en blanco: las palabras viven aquí.
        "corregir": textos.CORREGIR,
        # El libro de movimientos del producto: lo comprado, lo echado y lo que queda.
        "cesta": textos.CESTA,
        # Las semillas y las siembras (T10, 03/10/2026): lo que pone la etiqueta de una semilla, las
        # dos cifras de una siembra (la de cada hectárea y el total) y lo que se dice cuando una de
        # las dos no se sabe. Va aquí, y no solo dentro de las respuestas de la API, por el mismo
        # motivo que los del almacén: **esto se guarda en el móvil**, y una pantalla que se abre en el
        # campo sin cobertura tiene que tener sus palabras.
        "semillas": textos.SEMILLAS,
        # En qué se mide una dosis de siembra y en qué se cuenta una cantidad de semilla (T10).
        # **Son listas nuestras, y se dice**: no hay ningún catálogo oficial de unidades de siembra
        # cargado en el programa (el que hay es el de los productos), así que son las formas en que se
        # escribe una dosis de semilla en un papel de verdad. Se ofrecen para no teclear, no para
        # obligar: la unidad se guarda como texto.
        "unidades_dosis_semilla": list(semillas.UNIDADES_DE_DOSIS),
        "unidades_cantidad_semilla": list(semillas.UNIDADES_DE_CANTIDAD),
        # Las personas y las empresas (T11, 03/10/2026): la ficha de un contacto, los papeles que
        # puede hacer con la finca y lo que se dice al proponerle fichas a partir de los nombres que
        # el agricultor ya tiene escritos. Va aquí, y no solo dentro de las respuestas de la API, por
        # el mismo motivo que los del almacén y las semillas: **esto se guarda en el móvil**, y una
        # pantalla que se abre sin cobertura tiene que tener sus palabras.
        "contactos": textos.CONTACTOS,
        # **La lista de papeles, con su orden y con su nombre.** El orden importa y por eso no se
        # saca de las claves de un diccionario: los botones de marcar salen siempre en el mismo sitio,
        # y un cuestionario cuyas preguntas cambian de orden se contesta mal (guía de la interfaz,
        # apartado 3.9).
        "papeles_de_un_contacto": [
            {"valor": papel, "texto": textos.CONTACTOS["papeles"][papel]}
            for papel in contactos.PAPELES
        ],
        # Qué hay sembrado en cada parcela: las pestañas «Características DGC» e «Historial
        # Cultivos» de la app oficial.
        "cultivos": textos.CULTIVOS,
        # Las parcelas que se llevan igual y se apuntan de una vez (la «UHC» de la app oficial).
        "grupos": textos.GRUPOS,
        # Los años del cuaderno (la campaña), ronda 93. Es la pantalla nueva, y sus textos van aquí como
        # los de todas: el componente no escribe ni una frase.
        "campanas": textos.CAMPANAS,
        # El armazón de la aplicación en el ordenador (30/09/2026): el menú lateral y la barra de arriba.
        "menu": textos.MENU,
        # La barra con el contexto (T04, 03/10/2026): el rótulo de la finca y los nombres de los botones de
        # cambiar de finca y de campaña. Va aparte de `menu` porque `menu` es el vocabulario de siempre y
        # esto es lo nuevo; el armazón lee las dos y se queda con la que exista.
        "marco": textos.MARCO,
        # Y lo que se dice cuando una dirección no lleva a ninguna parte (T04): no es lo mismo una pantalla
        # que no existe, una ficha que no es tuya y algo que no se ha podido comprobar por falta de cobertura.
        "direccion": textos.DIRECCION,
        # Los nombres de las columnas de las tablas del ordenador (30/09/2026): son frases que lee el
        # agricultor («Qué tiene este año»), así que vienen de aquí y no de un componente.
        "tabla": textos.TABLA,
        # **La maquinaria de la finca (T14, E8, 03/10/2026).** Las palabras de la pantalla nueva: la
        # tabla, la ficha con sus cinco obligaciones separadas, los estados de cada una y los avisos de
        # antes de coger la máquina. Va aquí —y no solo dentro de las respuestas de la API— por el mismo
        # motivo que las del almacén y las de las semillas: **esto se guarda en el móvil**, y la lista de
        # maquinaria se mira en la nave, que es donde peor va la cobertura.
        #
        # Y hay una razón más, que es la del ticket: la ficha tiene que poder decir **«no se sabe»** y
        # **pedir la clasificación técnica** aunque el servidor no conteste. Si esas frases vivieran solo
        # en la respuesta, la pantalla se quedaría muda justo en el caso que más importa.
        "maquinaria": textos.MAQUINARIA_DE_LA_FINCA,
        # Las cinco obligaciones con su nombre y su explicación, **en el orden de la ficha** (ITV, ITEAF,
        # mantenimiento, seguro y ROMA). El orden no se saca de las claves del diccionario: unos botones
        # que cambian de sitio se pulsan mal, y aquí se eligen cinco cosas que se parecen mucho.
        "obligaciones_de_una_maquina": [
            {
                "valor": tipo,
                "texto": textos.MAQUINARIA_DE_LA_FINCA[f"obligacion_{tipo}"],
                "que_es": textos.MAQUINARIA_DE_LA_FINCA[f"que_es_{tipo}"],
            }
            for tipo in maquinaria.OBLIGACIONES
        ],
        # Las listas cerradas de la maquinaria, con su nombre y su porqué. **Todas son nuestras**: la
        # tabla oficial de clasificaciones técnicas por máquina **no está transcrita** (es el trabajo
        # legal L07 de la matriz normativa), y por eso la clasificación se pide como texto libre en vez
        # de ofrecer una lista que parecería oficial sin serlo.
        "clases_de_maquina": [
            {"valor": valor, "texto": textos.MAQUINARIA_DE_LA_FINCA[f"clase_{valor}"]}
            for valor in maquinaria.CLASES_DE_MAQUINA
        ],
        "propiedades_de_una_maquina": [
            {"valor": valor, "texto": textos.MAQUINARIA_DE_LA_FINCA[f"propiedad_{valor}"]}
            for valor in maquinaria.PROPIEDADES
        ],
        "disponibilidades_de_una_maquina": [
            {"valor": valor, "texto": textos.MAQUINARIA_DE_LA_FINCA[f"disponibilidad_{valor}"]}
            for valor in maquinaria.DISPONIBILIDADES
        ],
        "aplicabilidades_de_una_obligacion": [
            {"valor": valor, "texto": textos.MAQUINARIA_DE_LA_FINCA[f"aplicabilidad_{valor}"]}
            for valor in maquinaria.APLICABILIDADES
        ],
        "origenes_de_una_aplicabilidad": [
            {"valor": valor, "texto": textos.MAQUINARIA_DE_LA_FINCA[f"origen_{valor}"]}
            for valor in maquinaria.ORIGENES_DE_LA_APLICABILIDAD
        ],
        "resultados_de_una_inspeccion": [
            {"valor": valor, "texto": textos.MAQUINARIA_DE_LA_FINCA[f"resultado_{valor}"]}
            for valor in maquinaria.RESULTADOS_DE_UNA_INSPECCION
        ],
        # Lo que el programa **todavía no sabe calcular** (los plazos por clasificación técnica), con lo
        # que es, para qué haría falta y de quién depende. Se sirve aquí para que la pantalla pueda
        # decirlo sin abrir ninguna máquina: es la receta de `AGENTS.md`, y sin esto el agricultor
        # creería que una fecha que no aparece es un fallo del programa en vez de un dato que falta.
        "maquinaria_que_falta": list(maquinaria.QUE_FALTA),
        # **Las cuentas de la explotación (T13, E7, 05/10/2026).** Las palabras de la pantalla nueva:
        # sus tarjetas, sus estados, sus cuatro métodos de reparto y sus frases de «no lo sé». Va
        # aquí —y no solo dentro de las respuestas de la API— por el mismo motivo que las del almacén
        # y las de la maquinaria: **esto se guarda en el móvil**, y las cuentas se miran en el
        # despacho y también de pie en la parcela, que es donde peor va la cobertura.
        #
        # Y hay una razón más, que es la del ticket: la pantalla tiene que poder decir **«no lo sé»**
        # aunque el servidor no conteste. Si esas frases vivieran solo en la respuesta, la pantalla se
        # quedaría muda justo en el caso que más importa.
        "gastos": textos.GASTOS,
        # Las cuatro listas cerradas, **con su orden y con su nombre**. El orden no se saca de las
        # claves del diccionario: unos botones que cambian de sitio se pulsan mal.
        "categorias_de_gasto": [
            {"valor": clave, "texto": textos.GASTOS["categorias_de_gasto"][clave]}
            for clave in gastos.CATEGORIAS_DE_GASTO
        ],
        "categorias_de_inversion": [
            {"valor": clave, "texto": textos.GASTOS["categorias_de_inversion"][clave]}
            for clave in gastos.CATEGORIAS_DE_INVERSION
        ],
        "metodos_de_reparto": [
            {"valor": clave, "texto": textos.GASTOS["metodos_de_reparto"][clave]}
            for clave in gastos.METODOS_DE_REPARTO
        ],
        "formas_de_pago": [
            {"valor": clave, "texto": textos.GASTOS["formas_de_pago"][clave]}
            for clave in ventas.FORMAS_DE_COBRO
        ],
        # Y lo que el programa **todavía no sabe calcular** de las cuentas (la amortización, el
        # extracto del banco y el resumen del IVA), con lo que es, para qué haría falta y de quién
        # depende. Sin esto, el agricultor creería que una cifra que no aparece es un fallo del
        # programa en vez de un dato que falta (la receta de `AGENTS.md`).
        "gastos_que_falta": list(gastos.QUE_FALTA),
        # Los trabajos por tierra (T15, 05/10/2026): la agenda, la ficha de un trabajo y la historia de
        # una tierra. Sin esto, las tres pantallas salen con los botones en blanco.
        "agenda": textos.AGENDA,
        # **El extracto del banco y la conciliación (T20, E11, 06/10/2026).** Sin esto, la pantalla de S14
        # sale con todos sus botones y sus rótulos en blanco. Y va **aquí** y no solo dentro de la
        # respuesta de `/api/bancos/movimientos` porque la ficha de un movimiento se abre directamente por
        # su dirección (`#/cuentas/bancos/12`) y entonces no hay ninguna lista que traiga sus palabras; y
        # porque esto se guarda en el móvil (`localStorage`, la clave `cuedigital.interfaz`), así que la
        # pantalla sigue teniendo sus palabras **sin cobertura**.
        "bancos": textos.BANCOS,
        # **La bandeja documental (T08, S10, 06/10/2026).** Sin esto, la pantalla sale con todos sus
        # botones y sus rótulos en blanco. Y va **aquí** y no solo dentro de la respuesta de
        # `/api/bandeja` por el mismo motivo que los del banco: la ficha de un papel se abre
        # directamente por su dirección (`#/papeles/bandeja/12`) y entonces no hay ninguna lista que
        # traiga sus palabras; y porque esto se guarda en el móvil (`localStorage`, la clave
        # `cuedigital.interfaz`), así que la pantalla sigue teniendo sus palabras **sin cobertura**,
        # que es justo cuando se miran los papeles (en la nave, con el móvil en la mano).
        "bandeja": textos.BANDEJA,
        # **Las tierras en el mapa y en la tabla, y lo que ha sido una tierra** (T06, 03/10/2026): las
        # palabras de las dos pantallas nuevas. Se sirven aquí —y no solo dentro de
        # `/api/parcelas/vista`— por un motivo que se vio al escribirlas: la ficha de una tierra con sus
        # versiones **se puede abrir directamente por su dirección** (`#/tierras/2/versiones`) sin pasar
        # por la pantalla del mapa, y entonces no hay ninguna vista que traiga sus textos. Y esto sí
        # está guardado en el móvil (`localStorage`, la clave `cuedigital.interfaz`), así que la ficha
        # sigue teniendo sus palabras **sin cobertura**.
        "tierras": textos.TIERRA_Y_MAPA,
        "versiones": textos.VERSIONES_EN_PANTALLA,
        # El panel de detalle, al lado de la tabla (fase 3, 30/09/2026): lo que se ve al tocar el nombre de
        # una fila, sin cambiar de pantalla.
        "panel": textos.PANEL,
        # El panel de mando del ordenador (fase 4, 30/09/2026): la pantalla que se abre al entrar desde un
        # pc. Va aparte de `panel` a propósito: `panel` es la ficha de una fila, y esto es la portada.
        "panel_de_mando": textos.PANEL_DE_MANDO,
        "tipos_venta": [
            {"valor": valor, "texto": catalogos.ETIQUETA_VENTA[valor]}
            for valor in catalogos.TIPOS_VENTA
        ],
        "unidades_venta": [
            {"valor": valor, "texto": datos["etiqueta"], "corto": datos["corto"]}
            for valor, datos in catalogos.UNIDADES_VENTA.items()
        ],
        "justificaciones": list(catalogos.JUSTIFICACIONES),
        # El tipo de carné de quien echa el producto: los cuatro que distingue la hoja 1.2 del
        # cuaderno de la Junta (básico, cualificado, fumigador y piloto).
        "tipos_carne": [
            {"valor": valor, "texto": catalogos.ETIQUETA_CARNE[valor]}
            for valor in catalogos.TIPOS_CARNE
        ],
        # De quién es una máquina de echar producto: las tres pestañas de la app oficial (propia,
        # ajena y equipos sin ROMA), con palabras que se entienden.
        "titularidades_equipo": catalogos.TITULARIDADES_EQUIPO,
        "unidades": list(catalogos.UNIDADES_PRODUCTO),
        "unidades_dosis": list(catalogos.UNIDADES_DOSIS),
        # En qué se compra el producto: litros, kilos, mililitros… La dosis va por hectárea y la
        # compra va en un envase, así que son dos listas distintas y las dos hacen falta.
        "unidades_producto": list(catalogos.UNIDADES_PRODUCTO),
        # Secano, regadío **o «no lo sé»**: ver `catalogos.SISTEMAS_PARA_ELEGIR` (A10).
        "sistemas": catalogos.SISTEMAS_PARA_ELEGIR,
        # El asesor y el agua de riego. Las tres listas son NUESTRAS, no las oficiales: el
        # catálogo de la Junta para estos campos no está cargado (ver `catalogos.py`).
        "ambitos_asesor": [
            {"valor": valor, "texto": catalogos.ETIQUETA_AMBITO_ASESOR[valor]}
            for valor in catalogos.AMBITOS_ASESOR
        ],
        "origenes_agua": [
            {"valor": valor, "texto": catalogos.ETIQUETA_ORIGEN_AGUA[valor]}
            for valor in catalogos.ORIGENES_AGUA
        ],
        # Lista **nuestra**: el catálogo oficial de eficacia del tratamiento no lo tenemos, así
        # que aquí se ofrecen las cuatro respuestas del agricultor y se dice de dónde salen.
        "eficacia_del_tratamiento": [
            {"valor": valor, "texto": catalogos.ETIQUETA_EFICACIA[valor]}
            for valor in catalogos.EFICACIA_DEL_TRATAMIENTO
        ],
        "sistemas_riego": [
            {"valor": valor, "texto": catalogos.ETIQUETA_SISTEMA_RIEGO[valor]}
            for valor in catalogos.SISTEMAS_RIEGO
        ],
        "unidades_agua": [
            {"valor": valor, "texto": catalogos.ETIQUETA_UNIDAD_AGUA[valor]}
            for valor in catalogos.UNIDADES_AGUA
        ],
        "tipos_instalacion": [
            {"valor": valor, "texto": catalogos.ETIQUETA_INSTALACION[valor]}
            for valor in catalogos.TIPOS_INSTALACION
        ],
        # Las labores que no tienen botón propio en la pantalla de inicio (podar, labrar,
        # mantener la cubierta, pastorear…). Salen del servidor y no del JavaScript para que no
        # haya dos listas que se separen, y porque dos de ellas las nombra el documento oficial.
        "trabajos_de_labor": [dict(trabajo) for trabajo in textos.TRABAJOS_DE_LABOR],
        "etiquetas_labor": dict(catalogos.ETIQUETA_LABOR),
        "tipos_tratamiento": [
            {"valor": valor, "texto": catalogos.ETIQUETA_TRATAMIENTO[valor]}
            for valor in catalogos.TIPOS_TRATAMIENTO
        ],
        "tipos_abono": [
            {"valor": valor, "texto": catalogos.ETIQUETA_TIPO_ABONO[valor]}
            for valor in catalogos.TIPOS_FERTILIZANTE
        ],
        # Los análisis: de qué clase puede ser la muestra y qué números trae el boletín de
        # cada clase. La lista de números va por tipo porque un boletín de agua y uno de
        # tierra no traen lo mismo.
        "tipos_analitica": [
            {"valor": valor, "texto": catalogos.ETIQUETA_ANALITICA[valor]}
            for valor in catalogos.TIPOS_ANALITICA
        ],
        "parametros_analitica": {
            tipo: [
                {
                    "clave": parametro.clave,
                    "pregunta": parametro.pregunta,
                    "etiqueta": parametro.etiqueta,
                    "unidad": parametro.unidad,
                    "oficial": parametro.oficial,
                }
                for parametro in catalogos.parametros_de(tipo)
            ]
            for tipo in catalogos.TIPOS_ANALITICA
        },
        # Qué análisis hay que atar a una parcela y cuáles pueden ser de cualquier sitio.
        "analitica_de_parcela": list(catalogos.ANALITICA_DE_PARCELA),
        "modos_aplicacion": list(catalogos.MODOS_APLICACION_ABONO),
        "momentos": list(catalogos.MOMENTOS_ABONADO),
        # Las reglas de abono de las zonas de nitratos, con su número, y lo que el programa de
        # actuación pide y no tenemos cargado.
        "reglas_nitratos": [
            {
                "clave": regla.clave,
                "que": regla.que,
                "texto_valor": (
                    f"{legal.formatea_numero(regla.valor, 0)} {regla.unidad}".strip()
                    if regla.valor is not None
                    else ""
                ),
                "fuente": regla.fuente,
                "que_hace_la_app": regla.que_hace_la_app,
            }
            for regla in catalogos.reglas_nitratos()
        ],
        "limites_que_faltan": list(catalogos.limites_que_faltan()),
        "aportes_maximos_n": list(catalogos.nitratos_cyl.aportes_maximos()),
        "periodos_prohibidos_n": list(catalogos.nitratos_cyl.periodos_prohibidos()),
        # Las provincias
        "provincias": list(catalogos.PROVINCIAS_CYL),
        # Los usos del suelo del SIGPAC, tal y como los escribe el visor: «TA — TIERRAS ARABLES».
        # Se ofrecen para poder apuntar el uso de una parcela a mano, que hasta ahora no se podía
        # ni poner: el campo existía y ninguna pantalla lo preguntaba.
        "usos_sigpac": [
            {"valor": codigo, "texto": f"{codigo} — {nombre}"}
            for codigo, nombre in sorted(sigpac.usos_oficiales().items())
        ],
        # Los textos de la elección de municipio: es lo que hace que no haya que saberse el código
        # del pueblo, y por eso la pantalla y el servidor usan las mismas palabras.
        "municipios": textos.MUNICIPIOS,
        # Las fechas que el agricultor tiene que saber
        "plazos_legales": {
            "cuaderno_en_papel_hasta": legal.formatea_fecha(catalogos.FECHA_FIN_CUADERNO_PAPEL),
            "productos_electronico_desde": legal.formatea_fecha(
                catalogos.FECHA_REGISTRO_ELECTRONICO_FITOSANITARIOS
            ),
            "abonos_obligatorio_desde": legal.formatea_fecha(
                catalogos.FECHA_REGISTRO_OBLIGATORIO_FERTILIZACION
            ),
            "plan_de_abonado_obligatorio_desde": legal.formatea_fecha(
                catalogos.FECHA_PLAN_DE_ABONADO_OBLIGATORIO
            ),
            # Lo que la ley deja a voluntad del titular. Va aquí, en los datos y no solo en un
            # texto, porque es la frase que más se malinterpreta: la ley obliga a **tener** el
            # registro y a poder enseñarlo; **mandarlo** a la Junta no es obligatorio
            # (artículo 10.2 del Real Decreto 1054/2022). Y llevarlo con un programa propio está
            # permitido (artículo 10.3), con el contenido mínimo del anexo II.
            "enviar_a_la_junta_es_voluntario": catalogos.ENVIAR_EL_CUADERNO_A_LA_JUNTA_ES_VOLUNTARIO,
            "se_puede_usar_un_programa_propio": catalogos.SE_PUEDE_USAR_UN_PROGRAMA_PROPIO,
        },
    }
