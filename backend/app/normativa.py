"""Las reglas de la normativa, sacadas de la matriz (07/10/2026).

**Nada de esto esta escrito a mano ni resumido**: sale de `docs/MATRIZ_NORMATIVA_CRM.md`, que es la fuente
unica. Si una regla cambia, se cambia **en la matriz** y se vuelve a extraer.

El modelo **no es de campos rigidos, y es a proposito**: la matriz no es uniforme -unas secciones dicen
`Fuente:` y otras `Fuentes:`, solo N01 usa la etiqueta de requisito, y **N09 avisa de que son dos obligaciones
diferentes**-. Por eso cada regla lleva:

- `codigo` y `titulo`, que si son uniformes.
- `fuentes`: **todas** las direcciones oficiales de la seccion, con el nombre con el que la matriz las cita.
  Es lo que hace que la pantalla se pueda **comprobar** en vez de creersela.
- `texto`: **lo que la matriz dice de esa regla, entero y sin tocar** -con sus avisos dentro, que es donde
  estan: en N01, «no copiar porcentajes del ecorregimen a BCAM»-.
- `tipo` y `estado`: **vacios a proposito**. La matriz define los cinco tipos y los cinco estados, pero no dice
  cual es cada regla, y rellenarlos a ojo seria inventar una clasificacion legal. La pantalla los ensena como
  «sin clasificar», y **solo `activa` participa en comprobaciones concluyentes**.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import textos


@dataclass(frozen=True)
class Fuente:
    """Una direccion oficial, con el nombre con el que la matriz la cita."""

    nombre: str
    enlace: str


@dataclass(frozen=True)
class Regla:
    """Una regla de la normativa, tal y como la cuenta la matriz."""

    codigo: str
    titulo: str
    fuentes: tuple[Fuente, ...]
    texto: str
    # **Lo que se enseña** (07/10/2026): `texto` es la matriz **tal cual**, que es documentación de trabajo
    # -«Implementar tres ejes independientes», «Prueba:», «IUWS no condiciona la navegación del CRM»-, y eso no
    # se le puede poner delante a un agricultor. Aquí va lo mismo dicho para él: qué tiene que tener apuntado y
    # qué no debe dar por hecho. **Sigue sin inventarse nada**: sale de la matriz, y el texto de trabajo se
    # conserva para poder comprobarlo.
    ayuda: str = ""
    tipo: str = ""
    estado: str = ""


LAS_REGLAS: tuple[Regla, ...] = (
    Regla(
        codigo='N01',
        titulo='Condicionalidad: BCAM y requisitos legales',
        fuentes=(
            Fuente(nombre='RD 1049/2022, anexo II', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2022-23049'),
        ),
        texto='Fuente: [RD 1049/2022, anexo II](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23049).\nLa consulta mostró consolidación de 09/10/2024. BCAM 7 contempla alternativas de\nrotación/diversificación; no debe confundirse con el ecorrégimen de rotación.\n\nRequisito de producto: ficha propia de condicionalidad, historial suficiente,\nsuperficies y clasificaciones, alternativa aplicable y excepciones documentadas.\nAntes de activar, transcribir íntegramente la práctica elegida con sus umbrales y\ndefiniciones. No copiar porcentajes del ecorrégimen a BCAM. Pruebas: ambas alternativas,\nlímites exactos, historial ausente y exención acreditada/no acreditada.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N01"],
    ),
    Regla(
        codigo='N02',
        titulo='Ecorrégimen elegido y planificación',
        fuentes=(
            Fuente(nombre='RD 1048/2022', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2022-23048'),
        ),
        texto='Fuente: [RD 1048/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23048),\nespecialmente artículos 36 y 37 para rotación y siembra directa. La reapertura de\neste enlace tuvo un fallo temporal en esta ronda; la fuente ya se consultó en la\npreparación de la especificación anterior. Revalidar su redacción al activar reglas.\n\nNo congelar como constantes los fragmentos encontrados por buscador: existen\nredacciones históricas con diferencias en superficies y excepciones. La unidad de\nevaluación y la definición de cultivo importan tanto como el porcentaje.\nGuardar práctica solicitada por ámbito, tipología de superficie, parcelas incluidas,\nárea elegible, cultivos principales/secundarios y justificación de exclusiones.\nUn plan con reglas 2026 puede compararse para 2027 como simulación marcada; no\npresentarlo como verificación definitiva de una convocatoria aún no incorporada.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N02"],
    ),
    Regla(
        codigo='N03',
        titulo='Solicitud y compromisos de Castilla y León',
        fuentes=(
            Fuente(nombre='portal PAC de la Junta', enlace='https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100Detalle/1284146916532/Normativa/1284293478518/Texto'),
            Fuente(nombre='incorporación a agroambiente y agricultura ecológica 2026', enlace='https://www.tramitacastillayleon.jcyl.es/web/jcyl/AdministracionElectronica/es/Plantilla100Detalle/1251181050732/Ayuda012/1285611475254/Propuesta'),
        ),
        texto='Fuentes: [portal PAC de la Junta](https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100Detalle/1284146916532/Normativa/1284293478518/Texto)\ny [incorporación a agroambiente y agricultura ecológica 2026](https://www.tramitacastillayleon.jcyl.es/web/jcyl/AdministracionElectronica/es/Plantilla100Detalle/1251181050732/Ayuda012/1285611475254/Propuesta).\nEsta última convocatoria contempla nuevos compromisos durante 2026–2028 para\nlos regímenes enumerados en ella. No inferir que cualquier ayuda dura tres años.\n\nModelo: Compromiso con expediente, régimen, solicitud, resolución, fecha inicial/final,\nsuperficie/unidades comprometidas y condiciones documentadas. Seguimiento anual\nenlazado al mismo compromiso; cambios, cesiones o renuncias conservan resolución.\nPendiente antes de automatizar: leer bases y resolución concreta de cada régimen.\nPrueba: cambiar campaña conserva compromiso; solicitud sin concesión no se muestra\ncomo ayuda concedida. Plazos se obtienen por campaña y sus ampliaciones.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N03"],
    ),
    Regla(
        codigo='N04',
        titulo='Excepciones locales y avisos',
        fuentes=(
            Fuente(nombre='resolución de 9 de agosto de 2024 sobre topillo en CyL', enlace='https://pac.jcyl.es/web/BlobServer?blobcol=urldata&blobheader=application%2Fpdf%3Bcharset%3DUTF-8&blobkey=urldata&blobnocache=true&blobtable=MungoBlobs&blobwhere=822%2F259%2FResoluci%C3%B3n+de+actuaciones+por+alta+poblaci%C3%B3n+de+topillo+campesino.pdf'),
        ),
        texto='Fuente: [resolución de 9 de agosto de 2024 sobre topillo en CyL](https://pac.jcyl.es/web/BlobServer?blobcol=urldata&blobheader=application%2Fpdf%3Bcharset%3DUTF-8&blobkey=urldata&blobnocache=true&blobtable=MungoBlobs&blobwhere=822%2F259%2FResoluci%C3%B3n+de+actuaciones+por+alta+poblaci%C3%B3n+de+topillo+campesino.pdf).\nEl documento identifica campañas 2023/2024 y 2024/2025. Sirve para demostrar que una\nflexibilidad tiene ámbito temporal, no para extenderla automáticamente a 2026/2027.\nGuardar comarca/municipio, práctica afectada y vigencia. Prueba negativa: resolución\nde otra comunidad o campaña no desbloquea una labor en la explotación.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N04"],
    ),
    Regla(
        codigo='N05',
        titulo='Productos y registro de tratamientos',
        fuentes=(
            Fuente(nombre='RD 1311/2012, anexo III', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605'),
            Fuente(nombre='registro oficial MAPA', enlace='https://servicio.mapa.gob.es/regfiweb/Productos/Index'),
        ),
        texto='Fuentes: [RD 1311/2012, anexo III](https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605)\ny [registro oficial MAPA](https://servicio.mapa.gob.es/regfiweb/Productos/Index).\nFicha de producto y autorización de uso son entidades distintas. La marca no basta\npara identificar formulación o uso permitido. Conservar consulta y etiqueta utilizadas.\n\nMatriz de captura por destino: parcela/cultivo, semilla, instalaciones y postcosecha.\nExtraer de fuente vigente campos exigibles y documentos asociados; mapear cada uno a\nformulario, modelo, informe y prueba. No usar una dosis máxima global como autorización\npara cualquier cultivo/plaga. Tratamientos históricos se comprueban a su fecha.\nPendientes: usos específicos, autorizaciones excepcionales y límites de aplicaciones\nnecesitan evidencia contextual. Falta de acceso al registro = no comprobado.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N05"],
    ),
    Regla(
        codigo='N06',
        titulo='Fertilización y nitratos',
        fuentes=(
            Fuente(nombre='RD 1051/2022', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2022-23052'),
            Fuente(nombre='Orden MAV/398/2022, publicación oficial', enlace='https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf'),
        ),
        texto='Fuentes: [RD 1051/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23052)\ny [Orden MAV/398/2022, publicación oficial](https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf).\nEl proyecto conserva fuentes y cálculos de los anexos; revisar su cobertura antes de\nañadir reglas. No confundir cálculo de nutrientes con plan de abonado completo.\n\nDatos: cultivo/rendimiento previsto y justificación, análisis, aportes de agua y otras\nfuentes, composición del abono con unidades, área realmente abonada, fecha y técnica.\nSeparar N total, fracciones y disponibilidad cuando la regla lo requiera. P y P2O5 no\nson la misma magnitud. Límites por cultivo y restricciones temporales son reglas\nseparadas; ventanas relativas a siembra/cosecha necesitan esas fechas.\nPruebas: provincia ausente, zona desconocida, análisis ausente y cultivo sin equivalencia\nno producen cumplimiento. No declarar que el software sustituye al asesor exigible.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N06"],
    ),
    Regla(
        codigo='N07',
        titulo='Semillas, certificación y variedades',
        fuentes=(
            Fuente(nombre='Ley 30/2006', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2006-13555'),
            Fuente(nombre='Ley 3/2000', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2000-414'),
            Fuente(nombre='catálogos MAPA', enlace='https://servicio.mapa.gob.es/germenwai/'),
            Fuente(nombre='legislación técnica por especie', enlace='https://www.mapa.gob.es/es/agricultura/legislacion/legislacion-nacional-semillas'),
        ),
        texto='Fuentes: [Ley 30/2006](https://www.boe.es/buscar/act.php?id=BOE-A-2006-13555),\n[Ley 3/2000](https://www.boe.es/buscar/act.php?id=BOE-A-2000-414),\n[catálogos MAPA](https://servicio.mapa.gob.es/germenwai/)\ny [legislación técnica por especie](https://www.mapa.gob.es/es/agricultura/legislacion/legislacion-nacional-semillas).\nLa certificación de material y la protección de la variedad regulan aspectos distintos.\n\nImplementar tres ejes independientes: identidad varietal, categoría/certificación del\nlote y derechos/condiciones de uso. Para reempleo, revisar régimen aplicable y supuestos\nde la excepción del agricultor; no asumir libertad general ni prohibición universal.\nLa exigencia de semilla certificada de una ayuda requiere su fuente específica.\nGuardar etiqueta, factura, procedencia y documentos de autorización si corresponden.\nPrueba: semilla comprada sin etiqueta no queda certificada por defecto; semilla propia\nqueda documentable sin declararla automáticamente ilícita.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N07"],
    ),
    Regla(
        codigo='N08',
        titulo='Material ecológico',
        fuentes=(
            Fuente(nombre='informe oficial MAPA sobre autorizaciones de semilla no\necológica', enlace='https://www.mapa.gob.es/es/alimentacion/temas/produccion-eco/informesemillasnoeco_2021_definitivo_tcm30-617875.pdf'),
        ),
        texto='Fuente de localización: [informe oficial MAPA sobre autorizaciones de semilla no\necológica](https://www.mapa.gob.es/es/alimentacion/temas/produccion-eco/informesemillasnoeco_2021_definitivo_tcm30-617875.pdf).\nEs un informe histórico, no una autorización vigente para el usuario. Identifica la\nbase pública de oferta y el tratamiento separado de autorizaciones.\n\nRequisito: condición ecológica de explotación, producto y lote con evidencias\nindependientes. Incorporar autorización individual, periodo, especie/variedad y\ncantidad cuando corresponda. Antes de activar reglas revisar normativa europea\nvigente y procedimiento de la autoridad competente en CyL. No deducir permiso por\nausencia en catálogo ni por una autorización concedida a otra persona.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N08"],
    ),
    Regla(
        codigo='N09',
        titulo='Inspecciones de maquinaria',
        fuentes=(
            Fuente(nombre='RD 1702/2011 ITEAF', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2011-19296'),
            Fuente(nombre='RD 920/2017 ITV', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2017-12841'),
        ),
        texto='Fuentes: [RD 1702/2011 ITEAF](https://www.boe.es/buscar/act.php?id=BOE-A-2011-19296)\ny [RD 920/2017 ITV](https://www.boe.es/buscar/act.php?id=BOE-A-2017-12841).\nDos obligaciones diferentes. Crear reglas por clasificación técnica, fechas y ámbito,\ncon exclusiones expresas. Fecha del documento de inspección prevalece como evidencia\nregistrada; discrepancia con cálculo abre revisión. No llamar a ITEAF «ITV» en etiquetas.\nPrueba: tractor, remolque y equipo de aplicación no comparten un vencimiento universal.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N09"],
    ),
    Regla(
        codigo='N10',
        titulo='Cuaderno propio e intercambio',
        fuentes=(
            Fuente(nombre='RD 1054/2022', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2022-23054'),
            Fuente(nombre='Orden APA/204/2023', enlace='https://www.boe.es/buscar/act.php?id=BOE-A-2023-5699'),
        ),
        texto='Fuentes: [RD 1054/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23054)\ny [Orden APA/204/2023](https://www.boe.es/buscar/act.php?id=BOE-A-2023-5699).\nSeparar llevanza de registros, formato exigible y comunicación a la Administración.\nNo convertir la voluntariedad general del CUE en exención de cualquier obligación\nsectorial. Mantener requisitos de formato/plazo como reglas independientes con\ndestinatarios y excepciones. IUWS no condiciona la navegación del CRM.',
        ayuda=textos.AYUDA_DE_LA_NORMATIVA["N10"],
    ),
)
