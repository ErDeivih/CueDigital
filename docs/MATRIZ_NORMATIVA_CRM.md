# Matriz normativa y de evidencias del CRM

Revisión documental: 01/10/2026. Especificación para implementación; no certificación
de cumplimiento. Complementa CONTRATO_IMPLEMENTACION_CRM.md. Los enlaces consolidados
facilitan lectura; para activar una regla conservar también publicación oficial y
modificaciones aplicables. La fecha de consulta no equivale a vigencia ni a campaña.

## 1. Registro obligatorio de cada regla

Campos: identificador estable, título, autoridad, territorio, artículo/anexo,
URL oficial, fecha de publicación, vigencia desde/hasta, campañas, versión,
documento y huella, fecha de revisión, responsable de revisión, tipo de obligación,
destinatarios, condiciones de aplicación, datos requeridos, fórmula, excepciones,
resultado cuando faltan datos y casos de prueba. Estados: localizada, transcrita,
revisada, activa, sustituida. Solo activa participa en comprobaciones concluyentes.

Tipos distintos: obligación general, condición de ayuda solicitada, compromiso
concedido, recomendación técnica y dato informativo. El usuario ve la diferencia.
Una regla sustituida sigue disponible para reproducir un informe histórico.
Si una excepción autonómica contradice la base, no elegir automáticamente: exigir
ámbito, periodo y revisión. Un resultado guarda versión de reglas y datos utilizados.

## 2. Fuentes y traducción a requisitos

### N01 — Condicionalidad: BCAM y requisitos legales

Fuente: [RD 1049/2022, anexo II](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23049).
La consulta mostró consolidación de 09/10/2024. BCAM 7 contempla alternativas de
rotación/diversificación; no debe confundirse con el ecorrégimen de rotación.

Requisito de producto: ficha propia de condicionalidad, historial suficiente,
superficies y clasificaciones, alternativa aplicable y excepciones documentadas.
Antes de activar, transcribir íntegramente la práctica elegida con sus umbrales y
definiciones. No copiar porcentajes del ecorrégimen a BCAM. Pruebas: ambas alternativas,
límites exactos, historial ausente y exención acreditada/no acreditada.

### N02 — Ecorrégimen elegido y planificación

Fuente: [RD 1048/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23048),
especialmente artículos 36 y 37 para rotación y siembra directa. La reapertura de
este enlace tuvo un fallo temporal en esta ronda; la fuente ya se consultó en la
preparación de la especificación anterior. Revalidar su redacción al activar reglas.

No congelar como constantes los fragmentos encontrados por buscador: existen
redacciones históricas con diferencias en superficies y excepciones. La unidad de
evaluación y la definición de cultivo importan tanto como el porcentaje.
Guardar práctica solicitada por ámbito, tipología de superficie, parcelas incluidas,
área elegible, cultivos principales/secundarios y justificación de exclusiones.
Un plan con reglas 2026 puede compararse para 2027 como simulación marcada; no
presentarlo como verificación definitiva de una convocatoria aún no incorporada.

### N03 — Solicitud y compromisos de Castilla y León

Fuentes: [portal PAC de la Junta](https://pac.jcyl.es/web/jcyl/PAC/es/Plantilla100Detalle/1284146916532/Normativa/1284293478518/Texto)
y [incorporación a agroambiente y agricultura ecológica 2026](https://www.tramitacastillayleon.jcyl.es/web/jcyl/AdministracionElectronica/es/Plantilla100Detalle/1251181050732/Ayuda012/1285611475254/Propuesta).
Esta última convocatoria contempla nuevos compromisos durante 2026–2028 para
los regímenes enumerados en ella. No inferir que cualquier ayuda dura tres años.

Modelo: Compromiso con expediente, régimen, solicitud, resolución, fecha inicial/final,
superficie/unidades comprometidas y condiciones documentadas. Seguimiento anual
enlazado al mismo compromiso; cambios, cesiones o renuncias conservan resolución.
Pendiente antes de automatizar: leer bases y resolución concreta de cada régimen.
Prueba: cambiar campaña conserva compromiso; solicitud sin concesión no se muestra
como ayuda concedida. Plazos se obtienen por campaña y sus ampliaciones.

### N04 — Excepciones locales y avisos

Fuente: [resolución de 9 de agosto de 2024 sobre topillo en CyL](https://pac.jcyl.es/web/BlobServer?blobcol=urldata&blobheader=application%2Fpdf%3Bcharset%3DUTF-8&blobkey=urldata&blobnocache=true&blobtable=MungoBlobs&blobwhere=822%2F259%2FResoluci%C3%B3n+de+actuaciones+por+alta+poblaci%C3%B3n+de+topillo+campesino.pdf).
El documento identifica campañas 2023/2024 y 2024/2025. Sirve para demostrar que una
flexibilidad tiene ámbito temporal, no para extenderla automáticamente a 2026/2027.
Guardar comarca/municipio, práctica afectada y vigencia. Prueba negativa: resolución
de otra comunidad o campaña no desbloquea una labor en la explotación.

### N05 — Productos y registro de tratamientos

Fuentes: [RD 1311/2012, anexo III](https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605)
y [registro oficial MAPA](https://servicio.mapa.gob.es/regfiweb/Productos/Index).
Ficha de producto y autorización de uso son entidades distintas. La marca no basta
para identificar formulación o uso permitido. Conservar consulta y etiqueta utilizadas.

Matriz de captura por destino: parcela/cultivo, semilla, instalaciones y postcosecha.
Extraer de fuente vigente campos exigibles y documentos asociados; mapear cada uno a
formulario, modelo, informe y prueba. No usar una dosis máxima global como autorización
para cualquier cultivo/plaga. Tratamientos históricos se comprueban a su fecha.
Pendientes: usos específicos, autorizaciones excepcionales y límites de aplicaciones
necesitan evidencia contextual. Falta de acceso al registro = no comprobado.

### N06 — Fertilización y nitratos

Fuentes: [RD 1051/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23052)
y [Orden MAV/398/2022, publicación oficial](https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf).
El proyecto conserva fuentes y cálculos de los anexos; revisar su cobertura antes de
añadir reglas. No confundir cálculo de nutrientes con plan de abonado completo.

Datos: cultivo/rendimiento previsto y justificación, análisis, aportes de agua y otras
fuentes, composición del abono con unidades, área realmente abonada, fecha y técnica.
Separar N total, fracciones y disponibilidad cuando la regla lo requiera. P y P2O5 no
son la misma magnitud. Límites por cultivo y restricciones temporales son reglas
separadas; ventanas relativas a siembra/cosecha necesitan esas fechas.
Pruebas: provincia ausente, zona desconocida, análisis ausente y cultivo sin equivalencia
no producen cumplimiento. No declarar que el software sustituye al asesor exigible.

### N07 — Semillas, certificación y variedades

Fuentes: [Ley 30/2006](https://www.boe.es/buscar/act.php?id=BOE-A-2006-13555),
[Ley 3/2000](https://www.boe.es/buscar/act.php?id=BOE-A-2000-414),
[catálogos MAPA](https://servicio.mapa.gob.es/germenwai/)
y [legislación técnica por especie](https://www.mapa.gob.es/es/agricultura/legislacion/legislacion-nacional-semillas).
La certificación de material y la protección de la variedad regulan aspectos distintos.

Implementar tres ejes independientes: identidad varietal, categoría/certificación del
lote y derechos/condiciones de uso. Para reempleo, revisar régimen aplicable y supuestos
de la excepción del agricultor; no asumir libertad general ni prohibición universal.
La exigencia de semilla certificada de una ayuda requiere su fuente específica.
Guardar etiqueta, factura, procedencia y documentos de autorización si corresponden.
Prueba: semilla comprada sin etiqueta no queda certificada por defecto; semilla propia
queda documentable sin declararla automáticamente ilícita.

### N08 — Material ecológico

Fuente de localización: [informe oficial MAPA sobre autorizaciones de semilla no
ecológica](https://www.mapa.gob.es/es/alimentacion/temas/produccion-eco/informesemillasnoeco_2021_definitivo_tcm30-617875.pdf).
Es un informe histórico, no una autorización vigente para el usuario. Identifica la
base pública de oferta y el tratamiento separado de autorizaciones.

Requisito: condición ecológica de explotación, producto y lote con evidencias
independientes. Incorporar autorización individual, periodo, especie/variedad y
cantidad cuando corresponda. Antes de activar reglas revisar normativa europea
vigente y procedimiento de la autoridad competente en CyL. No deducir permiso por
ausencia en catálogo ni por una autorización concedida a otra persona.

### N09 — Inspecciones de maquinaria

Fuentes: [RD 1702/2011 ITEAF](https://www.boe.es/buscar/act.php?id=BOE-A-2011-19296)
y [RD 920/2017 ITV](https://www.boe.es/buscar/act.php?id=BOE-A-2017-12841).
Dos obligaciones diferentes. Crear reglas por clasificación técnica, fechas y ámbito,
con exclusiones expresas. Fecha del documento de inspección prevalece como evidencia
registrada; discrepancia con cálculo abre revisión. No llamar a ITEAF «ITV» en etiquetas.
Prueba: tractor, remolque y equipo de aplicación no comparten un vencimiento universal.

### N10 — Cuaderno propio e intercambio

Fuentes: [RD 1054/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23054)
y [Orden APA/204/2023](https://www.boe.es/buscar/act.php?id=BOE-A-2023-5699).
Separar llevanza de registros, formato exigible y comunicación a la Administración.
No convertir la voluntariedad general del CUE en exención de cualquier obligación
sectorial. Mantener requisitos de formato/plazo como reglas independientes con
destinatarios y excepciones. IUWS no condiciona la navegación del CRM.

## 3. Fuentes técnicas que no son normas

| Fuente | Uso permitido en el producto | Límite que debe verse |
|---|---|---|
| [AEMET OpenData](https://opendata.aemet.es/dist/) | Estaciones y previsiones mediante conectores separados | Medición en estación no equivale a lluvia medida en la tierra |
| [ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview) | Estimación espacial histórica | Reanálisis, resolución aproximada de 9 km; no pluviómetro |
| [Copernicus estadísticas](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical.html) | Índices por polígono | Deben enmascararse nubes y ausencia de datos explícitamente |
| [SIGPAC geometrías](https://sigpac.mapa.gob.es/fega/visor/help/3101Geometrias.html) | Referencias y exportación geométrica | No acredita titularidad ni corrige automáticamente la declaración |
| [Banco de España sobre servicios de cuentas](https://clientebancario.bde.es/pcb/es/blog/informacion_cuentas_iniciacion_pagos.html) | Diseñar conexión consentida de consulta | Lectura de cuentas y orden de pago son servicios distintos |

## 4. Trabajo legal pendiente, acotado para agentes

L01: transcribir BCAM 7 vigente en reglas y casos; L02: artículos 36/37 completos,
con denominadores/excepciones; L03: anexos y resoluciones CyL de cada compromiso
realmente elegido; L04: matriz de campos de tratamientos por destino y fecha;
L05: fuentes de semillas por especie y ayudas solicitadas; L06: producción ecológica
y autorizaciones actuales; L07: clasificación ITV/ITEAF por máquina real; L08:
revisar obligaciones de facturación antes de emitir facturas fiscales; L09: actualizar
fechas sectoriales del cuaderno desde normas vigentes, sin copiar resúmenes antiguos.

Cada encargo entrega fuente oficial exacta, localizador, tabla de entradas/salidas,
excepciones y pruebas. No basta enlazar un real decreto entero. Si falta resolución
individual o compromiso elegido, pedir ese dato cuando se implemente esa función;
las demás fases pueden continuar. El motor legal solo activa lo revisado, y el panel
muestra cuántas comprobaciones siguen pendientes. Esta matriz no pretende haber
transcrito todos los requisitos de todas las ayudas ni sustituir esa revisión.
