# D08 — El corpus y el proveedor: dos opciones medidas, y la que se elige

> **Para qué es este documento.** El corte **D08** del encargo pide dos cosas que necesitan material de
> fuera: un **corpus de facturas reales** para medir el OCR, y una **fuente de meteo y satélite** con
> fuente, licencia, fecha y resolución. La regla de decisión de David es: **proponer DOS opciones
> concretas con coste, licencia y límite de uso, y elegir la más barata que cumpla**; si las dos
> tuvieran coste relevante, se para y se pregunta (nivel 3, `PROTOCOLO-AUTONOMIA.md`).
>
> **Lo que este documento sí hace**: mide las opciones y elige. **Lo que NO hace**: cerrar D08. La
> precisión del OCR sobre facturas de verdad **sigue sin medirse**, porque el corpus aún no existe en
> este repositorio. Eso es exactamente lo que hay que aportar para cerrarlo.
>
> Fecha de la consulta de precios y licencias: **04/11/2026**. Rama:
> `integracion/cloud-estabilizacion-2026-10-21`. Documento anterior sobre el mismo bloqueo:
> [`../backend/docs/PENDIENTE_D08.md`](../backend/docs/PENDIENTE_D08.md).
>
> **Estado (noche del 04/11/2026): APARCADO por decisión de David.** No va a aportar ahora las 30
> facturas con permiso. Este documento **se queda como está** —las dos opciones de cada decisión,
> medidas y con su elección— y sirve cuando llegue el corpus. **D08 no bloquea nada más** y no se
> persigue; está escrito en [`../ESPECIFICACION.md`](../ESPECIFICACION.md).
>
> **Cómo se lee.** Todo lo que va con enlace está **comprobado en la página oficial** el 04/11/2026.
> Lo que es estimación se dice «estimación». Lo que no se ha podido comprobar se dice «no verificado»
> y **no se usa para decidir**. Ninguna cifra de este documento está puesta de memoria.

---

## 0 · La decisión, en una tabla

Aquí no hay una decisión sino **tres**, y en las tres sale la misma respuesta: la opción de **0 €**.

| # | qué se decide | Opción A (la elegida) | Opción B (referencia) | ¿Coste relevante en la elegida? |
|---|---|---|---|---|
| 1 | **Corpus** de facturas para medir el OCR | Facturas reales del titular y sus proveedores, **con permiso escrito** | Corpus públicos abiertos (FATURA + CORD) | **No: 0 €** |
| 2 | **Proveedor de OCR** | **Tesseract local** (lo ya construido) | Azure AI Document Intelligence (nube) | **No: 0 €** (+ CPU del servidor) |
| 3 | **Meteo y satélite** | **AEMET OpenData + Copernicus Data Space Ecosystem** | Sentinel Hub (plan Basic) | **No: 0 €** |

**Consecuencia directa**: como en las tres la opción más barata que cumple cuesta **0 €**, **no se para
a preguntar por dinero**: es una decisión de **nivel 2**, que se toma, se hace y se anota con su motivo
en [`../DECISIONES.md`](../DECISIONES.md). Lo que **sí** queda pendiente es **material que solo puede
aportar David** (las facturas con su permiso); eso no es una decisión de dinero, es una petición
concreta y está en el apartado 6 con su modelo de permiso.

**Un matiz que hay que decir en la misma tabla**: la opción de 0 € del **OCR** cumple en **coste y
licencia**, pero **en calidad todavía no se puede decir que cumpla**: eso es lo que mide el corpus.
Las otras dos (corpus y meteo) sí cumplen en las tres dimensiones.

---

## 1 · Qué significa «medido» en este documento, y qué no

La regla de David pide **tres dimensiones** para cada opción. Se han medido así:

| dimensión | cómo se ha medido | qué queda fuera |
|---|---|---|
| **Coste** | Precio público de la página oficial del proveedor, consultada el 04/11/2026 (con enlace). Si el precio es a presupuesto, se escribe «no publicado» | La conversión USD→EUR cuando el proveedor publica en dólares; se dice |
| **Licencia** | Nombre y términos literales de la licencia o nota legal: si permite **uso comercial en un producto que se vende**, si exige **atribución** y si permite **redistribuir** | La interpretación jurídica fina: **esto no es asesoría legal** |
| **Límite de uso** | Cupo publicado (peticiones/min, mes, páginas, documentos) y fechas de renovación | El límite global de AEMET, que **no está publicado**; se dice |

**Y una cosa que no se mide aquí**: la **precisión del OCR sobre facturas reales**. Eso es lo que
mide el corpus cuando llegue. Hoy solo hay `7 comprobaciones · 0 fallos` sobre una factura
**sintética** fabricada por `backend/scripts/medir_el_ocr_por_campo.py`, y el propio proyecto ya dice
que eso no acredita leer facturas de verdad (`backend/docs/PENDIENTE_D08.md:48-56`). Este documento
**no convierte ese 7/7 en una métrica de calidad**: elegir proveedor no es aprobar el lector.

---

## 2 · Decisión 1 — el corpus de facturas

### 2.1 Qué tiene que permitir el corpus

El corpus no es «unas facturas para probar»: es el **material de medida**. Para que sirva tiene que
permitir medir **campo por campo, y documento por documento**, que es lo que exige el contrato
(`backend/app/lectura_evaluada.py:1-17`, y la regla de no confirmar compras/pagos ni autorización
fitosanitaria a partir del OCR sin revisión, `backend/app/lectura_evaluada.py:7-9`).

Los campos que deciden son **seis** (`backend/app/lectura_evaluada.py:34-41`):
`proveedor_nif`, `numero_factura`, `fecha`, `base_imponible`, `cuota_iva` y `total`. El instrumento
que ya existe mide **siete** etiquetas, porque cuenta además el **nombre del proveedor**
(`backend/scripts/medir_el_ocr_por_campo.py:55-63`). Y hay que medir **los tres formatos por
separado**, porque fallan distinto (`backend/app/facturas.py:685-741`): PDF con texto, PDF escaneado
y foto.

Y el corpus tiene que poder **citarse**: cada factura se identifica por **emisor + número de factura +
página**, y el informe de medición la cita una por una. Es la condición de la especificación
(«el corpus debe poder citarse (documento, página)», [`../ESPECIFICACION.md`](../ESPECIFICACION.md):9-10).
El corpus en sí **no se publica ni se mete en el repositorio**: son papeles con NIF y datos de
personas, y la regla del proyecto es que lo que sube el agricultor no va ni a la base de datos ni al
repositorio (`AGENTS.md` §3.10). Se guarda como `datos/adjuntos`: fuera del control de versiones.

### 2.2 Opción A (la elegida) — facturas reales del titular y de sus proveedores, con permiso escrito

**Qué es.** Facturas reales de proveedor agrícola español (abonos, fitosanitarios, semillas,
transporte) en los **tres formatos** que llegan de verdad: PDF nativo del proveedor, PDF escaneado y
foto de móvil. Es lo que pide `backend/docs/PENDIENTE_D08.md:50-56`.

| dimensión | medida |
|---|---|
| **Coste** | **0 € puntual y 0 € recurrente.** No hay proveedor ni precio externo que consultar: el material lo aporta el titular y sus proveedores. El coste real es **tiempo** (ver más abajo), no dinero |
| **Licencia** | **No es una licencia estándar; es un permiso escrito por emisor** (modelo en el anexo). Condiciones mínimas: uso **exclusivo** para evaluar la lectura, **sin redistribución**, confidencialidad, acceso limitado y **borrado** al cerrar la medición |
| **Límite de uso** | Sin cupo técnico ni caducidad: el límite son **las facturas que se consigan** y la **vigencia del permiso** |
| **Patrón** | **7 valores por factura**, tecleados por una persona que lee el papel (nunca sacados del OCR): proveedor, NIF, número, fecha, base, IVA, total. Con 30 facturas son **210 valores**. Si se miden además las líneas de la factura, **6 más por línea** (descripción, cantidad, unidad, precio unitario, importe y nº de registro; `backend/app/facturas.py:184-202`) |

**El detalle que hay que resolver bien: los datos personales.** Los campos que se miden incluyen el
**NIF y el nombre del proveedor**. Por eso **anonimizar no vale**: borrar el NIF destruye justo el
campo que más consecuencia tiene (un NIF mal leído te hace pagar a quien no es). La protección se hace
con **confidencialidad y no redistribución**, no con anonimización:

- el corpus **no entra en el repositorio** (va a `datos/adjuntos`, que está en el `.gitignore`);
- no se publica ni se comparte con terceros;
- el permiso dice para qué se usa y que se borra al terminar;
- el acceso queda limitado a quien hace la medición.

La base jurídica concreta del tratamiento de esos datos la tiene que validar **quien asesore en
protección de datos**: este documento **no es asesoría jurídica**. El texto oficial está en el
Reglamento (UE) 2016/679, <https://eur-lex.europa.eu/eli/reg/2016/679/oj> (consultado el 04/11/2026:
la página respondió **HTTP 202 sin cuerpo**, así que no se cita su texto, solo su dirección).

**Por qué 30 facturas, y qué se puede y qué no se puede concluir con 30.** Es una **propuesta**, no una
medida:

- 30 facturas (10 por formato) permiten **detectar fallos gruesos** —por ejemplo, que el NIF salga mal
  en una de cada diez—, y son suficientes para saber **si el camino sirve**.
- Con 30 documentos, el margen de error de una proporción al 95 % es de aproximadamente **±18 puntos**
  (1,96 · √(0,25/30) ≈ 0,18). **No sirve para certificar** «acierta el 95 %».
- Para estimar un error por campo con **±5 puntos** harían falta unos **384 documentos**
  (1,96² · 0,25 / 0,05² ≈ 384). Por eso el piloto de 30 es el **primer escalón**: si sale bien y hace
  falta certificar, se pide más material o se declara el margen que se tiene.

**Trabajo de anotación**: 7 valores × 30 facturas = **210 valores**. A una media de dos a cuatro
minutos por factura (leer el papel y teclearlo), son **1–2 horas** — *estimación, no medida*.

### 2.3 Opción B (referencia) — corpus públicos abiertos: FATURA + CORD

| dimensión | medida |
|---|---|
| **Coste** | **0 €** |
| **Licencia** | **CC BY 4.0**: permite uso comercial y redistribución **con atribución** |
| **Límite de uso** | FATURA: 10.000 imágenes y 30.000 JSON; CORD: 1.000 recibos. Sin registro ni caducidad |
| **Patrón** | Viene con las anotaciones (cajas, texto y clase en FATURA; `gt_parse` en CORD), pero hay que **mapear sus clases a nuestros campos** |

**[FATURA](https://zenodo.org/records/8261508)** (Zenodo, consultado el 04/11/2026): 10.000 imágenes
JPG y 30.000 JSON, 50 plantillas, 24 clases, idioma declarado `eng`, **generadas sintéticamente**,
CC BY 4.0, 363,5 MB.
**[CORD](https://github.com/clovaai/cord)** (consultado el 04/11/2026): **1.000 recibos reales
indonesios**, imagen + anotaciones, CC BY 4.0.

**Y por eso no cumple.** No es un problema de licencia (la licencia es buena): es que **no sirve para
medir lo que hay que medir**:

- FATURA es **sintética**: tiene el mismo defecto que la factura que ya se fabrica aquí, así que no
  mide facturas de verdad;
- FATURA está en **inglés** y **no tiene clase NIF**; CORD son **recibos indonesios**, sin NIF español
  y sin el IVA de aquí.

Faltando el NIF y el tipo de IVA **no se pueden medir los seis campos críticos**. La opción es válida
para otra cosa —un banco de robustez del lector, si algún día se quiere— pero **no sustituye a la
medición**.

**Descartados, y por qué** (verificado el 04/11/2026):

| corpus | por qué no |
|---|---|
| [DocILE](https://docile.rossum.ai/) | Los datos se ceden **«for research purposes»**; el MIT es del código, no de los datos |
| [FUNSD](https://github.com/crcresearch/FUNSD) | «non-commercial, research, and educational»: no vale para un producto que se vende |
| SROIE | **Licencia oficial no verificada** (la página del RRC no cargó); una copia de terceros en Hugging Face dice CC BY 2.0, y una copia de terceros no es la fuente de los derechos |
| [IDSEM](https://zenodo.org/records/6373179) | 75.000 facturas de luz españolas, CC BY 4.0, pero **generadas** y en PDF con texto: no ejercitan el lector de fotos |

### 2.4 Tabla comparativa y elección

| | **A: propias con permiso** | **B: FATURA + CORD** |
|---|---|---|
| Coste | 0 € | 0 € |
| Licencia | permiso escrito (confidencialidad, no redistribución) | CC BY 4.0 (atribución) |
| Uso comercial | sí, dentro del permiso | sí, con atribución |
| Límite | las facturas que se consigan | 10.000 + 1.000, sin caducidad |
| Patrón | 7 valores × factura (210 con 30) | incluido, pero hay que mapear clases |
| Campos críticos medibles | **6 de 6** | **no: falta NIF y falta IVA español** |
| Formato e idioma | PDF, escaneo y foto; español | JPG; inglés (FATURA) e indonesio (CORD) |
| ¿Cierra la medición? | **sí, cuando llegue el material** | no |

**Se elige la A**: es **la más barata que cumple** (0 €) y **la única que mide los campos que
deciden** sobre facturas españolas reales en los tres formatos. Su dependencia no es dinero: es que
David **autorice y aporte el material** (apartado 6).

### 2.5 Cómo se enchufa al instrumento que ya existe

Hoy `backend/scripts/medir_el_ocr_por_campo.py` hace tres cosas que hay que cambiar para un corpus
real:

1. **Fabrica** una factura en HTML y la captura como PNG (`:31-52` y `:80-88`). Para el corpus se
   sustituye por **leer un directorio** + un **JSON de patrón por factura** (los 7 valores).
2. **Llama directamente a `ocr.leer_texto`** (`:91`). Para medir lo que el agricultor se encuentra hay
   que pasar por la **puerta única de lectura**: `facturas.texto_del_documento`
   (`backend/app/facturas.py:685`), que decide solo entre PDF con texto (`:707-718`), escaneo
   (`:719-727`) y foto (`:746-760`), y apunta **cómo** se ha leído.
3. **Compara subcadenas en el texto crudo** (`:94-99`). La comparación por campo ya está escrita:
   `lectura_evaluada.lo_leido_por_campo` (`backend/app/lectura_evaluada.py:44-76`) distingue
   **acertado / fallado / sin leer**, y hay un resumen por campo (`:93-112`).

Lo que hay que añadir: extraer con `facturas.leer_factura` (`backend/app/facturas.py:645-682`) y
presentar el resultado **por campo × formato**, sin un «leído correctamente» global (el módulo ya
explica por qué: `backend/app/lectura_evaluada.py:25-30`). No hace falta base de datos ni fixtures: es
un instrumento manual, y el corpus vive fuera del repositorio. La factura sintética **se queda** como
prueba de humo del propio instrumento (que sigue funcionando el día que se toque).

---

## 3 · Decisión 2 — el proveedor de OCR

### 3.1 Opción A (la elegida) — Tesseract local, que es lo que ya está construido

**Qué es.** Tesseract como **programa aparte**, no como librería de Python (`backend/app/ocr.py:7-16`).
Está integrado y probado: idioma `spa+eng` por orden de preferencia (`backend/app/ocr.py:52`), 60
segundos de espera (`:56`), 3 páginas por documento (`:65`) e imagen a 1600 px (`:68`). El español se
carga desde `data/ocr/tessdata` sin tocar la instalación del sistema (`backend/app/ocr.py:76-88`).

| dimensión | medida |
|---|---|
| **Coste** | **0 € de licencia**, puntual y recurrente. El coste real es **CPU del servidor**, y **no está medido** (el guion no mide tiempo y el repo no tiene banco de CPU): se dice, no se estima una cifra |
| **Licencia** | **Apache License 2.0** ([texto oficial de Tesseract](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE), consultado el 04/11/2026): permite uso comercial, modificación y redistribución conservando licencia y atribuciones; sin copyleft y sin cuotas. El paquete de idioma `spa` viene de `tessdata_fast`, también [Apache 2.0](https://github.com/tesseract-ocr/tessdata_fast/blob/main/LICENSE) |
| **Límite de uso** | **Ninguno contractual.** Los técnicos son los del código: 60 s, 3 páginas, idiomas instalados. La **calidad con facturas españolas reales no está medida**: solo hay 7/7 sobre una sintética (`backend/docs/PENDIENTE_D08.md:27-46`) |
| **Datos** | La factura **no sale del servidor**: no hay tercero ni transferencia internacional por el OCR. Esto es un argumento técnico, **no asesoría jurídica**: el servidor sigue tratando datos personales y necesita las mismas garantías que sin OCR |

### 3.2 Opción B (referencia) — OCR en la nube: Azure AI Document Intelligence (Read)

| dimensión | medida |
|---|---|
| **Coste** | **1,50 USD por 1.000 páginas** en el primer tramo, y **0,60 USD/1.000** a partir de 1.000.000 páginas al mes, región **West Europe**. API oficial de precios de Azure y página de precios, consultadas el 04/11/2026: <https://azure.microsoft.com/en-us/pricing/details/document-intelligence/>. Se publica en **USD**: la conversión a euros **no está verificada** |
| **Licencia** | Uso comercial bajo los **Microsoft Product Terms (Online Services)**; el **DPA** (contrato de encargado de tratamiento) rige el tratamiento y la seguridad de los datos personales, y el recurso en región UE queda en el **EU Data Boundary**. El **EU Data Boundary está confirmado** (<https://learn.microsoft.com/en-us/privacy/eudb/eu-data-boundary-learn>, consultado el 04/11/2026); la URL concreta de los Product Terms devolvió **HTTP 403** en la consulta, así que **el texto del DPA no se cita aquí**: se enlaza solo el índice oficial (<https://www.microsoft.com/licensing/terms/product/ForOnlineServices/EAEAS>) |
| **Límite de uso** | 2.000 páginas por análisis, 500 MB por fichero, 15 peticiones/s por defecto (ampliable). Sin cupo mensual propio: pago por uso. <https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/service-limits?view=doc-intel-4.0.0> |

**Coste anual estimado.** En el repositorio **no hay una cifra de facturas al año** (se ha buscado y no
aparece). Con un escenario **supuesto** de 500 facturas al año de una página: 500 × 1,50 / 1.000 =
**0,75 USD al año**; con 2.000 páginas, 3,00 USD al año. Es un escenario, no una medida.

### 3.3 Tabla comparativa y elección

| | **A: Tesseract local** | **B: Azure Read (nube)** |
|---|---|---|
| Licencia | Apache 2.0 | Product Terms + DPA |
| Uso comercial | sí | sí |
| Coste | 0 € + CPU no medida | 1,50 USD/1.000 págs.; 0,75 USD/año en el escenario |
| Límite | ninguno contractual; 3 págs./60 s en el código | 2.000 págs., 500 MB, 15 peticiones/s |
| Español | sí (`spa+eng`) | sí (Read) |
| Datos | **no salen del servidor** | salen a Microsoft (región UE) |
| Calidad con facturas reales | **no medida** | **no medida** |
| Qué hay que cambiar | nada: ya está | API, clave, DPA y coste por uso |

**Se elige la A (Tesseract local)**: es **la más barata que cumple en coste, licencia y límite** (0 €),
la licencia permite vender el producto, no tiene límite contractual y **la factura no sale del
servidor**. La nube no se justifica a este volumen y añade un tercero, un DPA y una salida de datos.

**Y una condición, escrita para que no se olvide**: **en calidad no se puede afirmar que cumpla**
hasta que el corpus la mida. Si el corpus del apartado 2 muestra fallos críticos (un NIF o un total
que no se pueden revisar), **Azure Read es el recambio natural y su coste es despreciable** (céntimos
al año en el escenario). **No se contrata nada antes de esa medición.**

---

## 4 · Decisión 3 — meteo y satélite

### 4.1 Qué haría la aplicación con esto, y qué está obligada a guardar

Hoy **no hay ni una línea** de meteo, clima, satélite, NDVI ni Copernicus en `backend/app/` (comprobado
y documentado en `backend/docs/PENDIENTE_D08.md:60-74`). Pero la aplicación **ya guarda las condiciones
del tratamiento**: temperatura, humedad, viento y dirección del viento
(`backend/app/models.py:1175-1178`, con sus preguntas en `backend/app/textos.py:1862-1878`). La meteo
encaja ahí, y con una utilidad legal concreta: el viento es lo que se pregunta cuando hay una queja de
un vecino, y el plazo de espera depende de la lluvia.

Lo que el encargo exige (`docs/ENCARGO_DEEPSEEK_2026-10-19.md:407-410`) es que **cada dato lleve
fuente, licencia, fecha y resolución**, y que **observado, estimado y pronóstico sean estados
distintos** —en el dato y no en un comentario—. Eso se traduce en campos obligatorios del apunte:
`estado`, `fuente`, `licencia`, `fecha_dato`, `fecha_consulta`, `resolucion_m` y `metodo`.

### 4.2 Opción A (la elegida) — 0 €: AEMET OpenData + Copernicus Data Space Ecosystem

**Hallazgo de partida, y es importante**: **ningún proveedor de 0 € cubre a la vez meteo y satélite**.
Hacen falta **dos piezas**, y las dos son de la administración pública y gratuitas.

#### 4.2.1 AEMET OpenData (meteo)

| dimensión | medida |
|---|---|
| **Coste** | **0 €** puntual y recurrente. «Es de libre uso y gratuito» (FAQ oficial de OpenData, v1.4, 28/07/2025: <https://opendata.aemet.es/centrodedescargas/docs/FAQs220424.pdf>); la página oficial describe la descarga gratuita de los datos del Anexo II de la resolución de 30/12/2015: <https://www.aemet.es/es/datos_abiertos/AEMET_OpenData> |
| **Licencia** | Reutilización permitida **«para fines comerciales y no comerciales»**, con cesión gratuita y no exclusiva de derechos (`https://www.aemet.es/es/nota_legal`, consultada el 04/11/2026). Condiciones: **citar a AEMET** (`© AEMET` o «Información elaborada por la Agencia Estatal de Meteorología»; en servicios de valor añadido, «Fuente: AEMET»), mencionar la fecha de última actualización cuando conste, y **no insinuar que AEMET patrocina o avala** el producto |
| **Límite de uso** | **40 conexiones por minuto por usuario**, más un límite global de conexiones **no publicado** (FAQ 3.5). No hay cupo diario ni mensual publicado |
| **Registro** | **API key gratuita** por correo (confirmación en unos 5 días, sin caducidad; se pueden pedir varias) (FAQ 1.11-1.12) |
| **Dato** | Observación de **estación** y predicción: municipal a 7 días y horaria a 2 días, «al menos actualizada diariamente» (<https://www.aemet.es/es/datos_abiertos/catalogo>). Los modelos numéricos (HARMONIE-AROME) **no son datos abiertos** (FAQ 4.3) |
| **Resolución y frescura** | **Municipio** (previsión) y **estación** (observación): **nunca de parcela**. Las climatologías diarias van con unos 4 días de retraso (FAQ 4.2); el retardo exacto de la observación horaria **no está verificado**. Una predicción de ayer no es la de hoy: se guarda la fecha de emisión |

#### 4.2.2 Copernicus Data Space Ecosystem (satélite y NDVI)

| dimensión | medida |
|---|---|
| **Coste** | **0 €** con registro |
| **Licencia** | Datos Sentinel **«free, full and open»**: la nota legal permite reproducción, distribución, comunicación pública y adaptación/combinación **sin restricción** —la nota no usa la palabra «comercial», así que aquí se escribe lo que dice—, con la nota `Copernicus Sentinel data [año]` o, si se modifica, `Contains modified Copernicus Sentinel data [año]` (Legal Notice: <https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice>, consultado el 04/11/2026). Los Términos del portal exigen registro; **los contenidos del portal distintos de los datos Sentinel no son comerciales ni redistribuibles**, y **prohíben crear varias cuentas para saltarse cupos** (<https://dataspace.copernicus.eu/terms-and-conditions>) |
| **Límite de uso** | Usuarios generales: **10.000 peticiones/mes, 300/min; 10.000 unidades de proceso (PU)/mes** según la tabla de cuotas; CDSE documenta una ampliación temporal a **30.000** en un PDF aparte, **no garantizada**, así que **se planifica con 10.000**; descarga de **12 TB/30 días**; renovación el día 1 de cada mes (<https://documentation.dataspace.copernicus.eu/Quotas.html>). La propia ESA avisa de que esas cuotas pueden bajar: se comprobarán antes de desplegar |
| **Dato** | **Sentinel-2 L2A**; el **NDVI se calcula**, no viene servido. Resolución **10 m en B02, B03, B04 y B08** (20 m las demás), **revisita de 5 días** con la constelación nominal (con un solo satélite, 10 días), franja de 290 km, L2A sistemático desde el 13/12/2018 (<https://sentiwiki.copernicus.eu/web/s2-mission>, consultado el 04/11/2026) |
| **Resolución y frescura** | 1 PU = salida de 512×512 px, 3 bandas, 1 muestra/píxel, ≤16 bits; mínimo 0,01 PU. **La frescura es la del paso del satélite**, y **las nubes y sombras pueden inutilizar la observación**: un NDVI de hace tres semanas no se enseña como «cómo está el cultivo hoy» (`backend/docs/PENDIENTE_D08.md:64-74`). La latencia de publicación de L2A **no está verificada** |

### 4.3 Opción B (referencia) — comercial: Sentinel Hub vía CREODIAS

| dimensión | medida |
|---|---|
| **Coste** | **999 €/año + IVA** (plan Basic). Tramos publicados: Exploration **300 €/año** —marcado **no comercial / investigación**—, Basic **999**, Enterprise-S **5.000**, Enterprise-L **10.000 €/año** (<https://creodias.eu/pricing/sh-pricing/>, consultado el 04/11/2026) |
| **Licencia** | Los **mismos datos Sentinel**, con el mismo Legal Notice y la misma atribución. El contrato completo de CREODIAS/Sentinel Hub **no se ha verificado**; la página publica precio y cupos, no los términos completos |
| **Límite de uso** | Basic: **70.000 PU/mes, 700.000 peticiones/mes, 500/min** |
| **Dato** | Sentinel-2 L2A con la misma resolución y revisita que la opción gratuita, más servicios (OGC, Statistical API, BYOC). Requiere contrato con CloudFerro/CREODIAS |

**La meteo comercial, y por qué no compite.** **No hay precio público verificado**: Meteomatics remite a
«habla con nuestros expertos» (<https://www.meteomatics.com/en/pricing/>, consultado el 04/11/2026) →
**no publicado**; Open-Meteo tiene plan comercial pero **no publica importes**, y su capa gratuita
**prohíbe expresamente el uso comercial** (<https://open-meteo.com/en/pricing>), así que no vale como
opción de 0 €.

### 4.4 Uso estimado, sacado del código

De `backend/scripts/datos_representativos.py`: **64 tierras** en **4 municipios**, superficies de
**1,20 a 9,60 ha**, 3 campañas, 24 tratamientos y 24 trabajos (12 + 12).

- **Meteo.** La unidad de caché es el **municipio**, no la tierra. Con 4 municipios y la API HATEOAS de
  AEMET (2 peticiones por descarga: la primera devuelve la URL), previsión diaria + horaria ≈ **16
  peticiones/día**; observación por estación ≈ **4–8/día**. Total: **≈ 20–30 peticiones/día ≈ 600–900
  al mes**. Cabe de sobra en 40 conexiones/minuto (media < 0,05/min) **si se cachea**.
- **Satélite.** 1 petición por tierra y fecha. A 10 m, una tierra de ~5 ha ocupa unos 500×500 px ≈
  **1 PU**; con ~6 fechas al mes: 64 × 6 = **384 peticiones ≤ 400 PU/mes**. El piloto de 3 tierras
  serían ~18 peticiones/mes. Cabe en 10.000 peticiones y 10.000 PU/mes con **más del 95 % de margen**;
  las descargas son megas, no TB.
- **Sensibilidad.** Sin cachear y por tierra (64 × 2) serían ~128 peticiones/día en meteo: sigue lejos
  del límite por minuto, pero **el límite global de AEMET no está publicado**, así que **cachear no es
  opcional**.

### 4.5 Tabla comparativa y elección

| | **A: 0 € (AEMET + CDSE)** | **B: comercial (Sentinel Hub Basic)** |
|---|---|---|
| Coste | **0 €** | **999 €/año + IVA** |
| Licencia | AEMET: reutilización comercial con atribución; Sentinel: free/full/open con nota | Igual en los datos; contrato CREODIAS no verificado |
| Límite | AEMET 40 conexiones/min + global no publicado; CDSE 10.000 peticiones/mes, 10.000 PU/mes, 12 TB/30 días | 70.000 PU/mes, 700.000 peticiones/mes, 500/min |
| Registro | API key gratuita de AEMET + cuenta gratuita de CDSE | Contrato con CREODIAS |
| ¿Cumple con el uso estimado? | **sí, con > 95 % de margen** | sí, pero pagando lo que no hace falta |

**Se elige la A**: es **la más barata que cumple** (0 €), las dos fuentes permiten **uso comercial con
atribución**, cubren las dos necesidades y el uso estimado queda muy por debajo de los cupos. La B
solo se justificaría con SLA, con volumen o si algún día se agota el cupo gratuito; su primer tramo es
**999 €/año + IVA**, que a este uso no se puede defender.

**Condiciones que se aceptan al elegirla** (y que habrá que cumplir en el código y en la pantalla):

1. **Atribución visible** en el dato y en la pantalla: `© AEMET` / «Fuente: AEMET» con la fecha, y
   `Copernicus Sentinel data 2026` / `Contains modified Copernicus Sentinel data 2026` cuando el NDVI
   se calcule (está modificado). Nunca presentar AEMET ni Copernicus como socios o avalistas.
2. **Caché con metadatos**: fuente, licencia, fecha del dato, fecha de consulta y resolución.
3. **No revender el dato en crudo**: se vende la aplicación, no el fichero, y los contenidos del portal
   CDSE distintos de los datos Sentinel no son comerciales ni redistribuibles.
4. **No crear cuentas múltiples** para sortear cupos: lo prohíben los términos.

### 4.6 Cómo se haría sin inventar (la tarea siguiente)

Como con el SIGPAC (`docs/SERVICIOS_DEL_SIGPAC.md`): **una llamada de verdad, su respuesta guardada como
ejemplo, y el analizador escrito contra ese ejemplo**; las pruebas **no salen a internet** y la prueba
de humo sí. Y con la regla de siempre: **sin clave, se dice y se sigue** (`backend/app/ocr.py` ya hace
eso con el lector de fotos). Las claves van en variables de entorno `CUEDIGITAL_…`, **nunca en el
repositorio ni en un `.env` versionado**, y el endpoint irá detrás de sesión y finca, con la matriz de
roles escrita en [`QUIEN_ENTRA_EN_LA_FINCA.md`](QUIEN_ENTRA_EN_LA_FINCA.md).

---

## 5 · La regla de David, aplicada

| decisión | Opción A | Opción B | ¿Coste relevante en la A? | elegida | nivel |
|---|---|---|---|---|---|
| Corpus | 0 € | 0 € | no | **A** | 2 |
| Proveedor de OCR | 0 € | 0,75 USD/año (escenario) | no | **A** | 2 |
| Meteo y satélite | 0 € | **999 €/año + IVA** | no | **A** | 2 |

**Por qué no es nivel 3.** El nivel 3 se dispara cuando **las dos opciones tienen coste relevante**.
Aquí la más barata que cumple cuesta **0 €** en las tres decisiones, así que la elección **no
compromete dinero**. Lo que **sí** queda fuera de nuestro alcance es **el material del corpus**, y por
eso se pide en el apartado siguiente: no es una compra, es una aportación.

**Y lo que NO cambia** (importante para revisar la decisión): ni el esquema de la base de datos, ni las
rutas, ni los textos del agricultor. Las tres decisiones se pueden revertir sin tocar datos: el corpus
se puede cambiar, el lector de OCR se puede sustituir por otro sin cambiar `facturas.py` (la puerta
única ya está separada, `backend/app/facturas.py:685`), y una fuente de meteo se puede cambiar
guardando de nuevo su `fuente` y su `licencia`.

---

## 6 · Lo que hay que pedirle a David (concreto, y sin dinero)

Esto es lo único que bloquea la medición, y es una **petición**, no una compra:

1. **Autorizar y aportar 30 facturas** de la explotación y de sus proveedores: **10 en PDF del
   proveedor, 10 escaneadas y 10 fotografiadas con el móvil**. Tienen que ser de los tipos que llegan
   de verdad (abonos, fitosanitarios, semillas, transporte). **No salen de su servidor**: se guardan
   fuera del repositorio, como `datos/adjuntos`, y se borran al terminar.
2. **El permiso escrito del emisor** de cada factura (o del titular, cuando la factura sea suya), con
   el modelo del anexo. Sin permiso no se mide.
3. **Alguien que lea el papel y teclee el patrón**: los 7 valores de cada factura. **1–2 horas** para
   las 30 (estimación).
4. **Dos altas gratuitas**, cuando toque implementar la meteo: la **API key de AEMET** (se pide por
   correo; tarda unos 5 días) y una **cuenta de Copernicus Data Space Ecosystem**. Las dos son gratis;
   no hay que contratar nada.

Y si no hay facturas posibles: **D08 sigue abierto**, y se dice en la pantalla y en el estado. Lo que
**no** se hará es sustituir la medición por una factura sintética y llamarlo «evaluado».

---

## 7 · Límites de esta propuesta, dichos y no escondidos

**Verificado en la página oficial el 04/11/2026** (con enlace en cada apartado): nota legal de AEMET y
reutilización comercial; FAQ de AEMET (límite de 40 conexiones/min, key gratuita); Legal Notice de
Sentinel y licencia CC BY 4.0 de FATURA y CORD; cuotas de CDSE; precios de Sentinel Hub vía CREODIAS;
Apache 2.0 de Tesseract; precio y límites de Azure Read; condiciones de DocILE y FUNSD; y en el
repositorio, los ficheros y líneas que se citan (`facturas.py`, `ocr.py`, `lectura_evaluada.py`,
`medir_el_ocr_por_campo.py`, `datos_representativos.py`).

**Y revisado por un revisor independiente el 04/11/2026**, punto por punto, contra las mismas páginas
oficiales: **13 puntos confirmados, 5 matizados y 0 falsos**. Los 5 matices ya están incorporados aquí
y son estos: (1) el cupo de Copernicus son **10.000 PU/mes** según la tabla de cuotas, y los 30.000
solo constan en un PDF aparte como ampliación temporal —se planifica con 10.000—; (2) la nota legal de
Sentinel no usa la palabra «comercial», así que se cita lo que dice; (3) Sentinel-2 tiene **cuatro**
bandas a 10 m, y los 5 días son de la constelación nominal; (4) el umbral del PDF son **40 caracteres
sin espacios**, no «40 letras» (`backend/app/facturas.py:716`); (5) la URL de los Product Terms de
Microsoft dio **403** y el texto del DPA no se cita.

**No verificado, y por eso no se usa como argumento**: el retardo exacto de la observación horaria de
AEMET; la latencia de publicación de Sentinel-2 L2A; el contrato completo y las condiciones de caché de
CREODIAS/Sentinel Hub; la asignación mensual del nivel gratuito de Azure (F0); la conversión USD→EUR de
Azure; el **texto literal del DPA de Microsoft** (la URL citada dio 403); el **precio del plan comercial
de Open-Meteo** (no publicado); la cifra del **límite global de AEMET** (existe, no se publica); los
**30.000 PU** de Copernicus (solo en el PDF, no en la tabla); el coste de CPU de Tesseract; y **la
calidad del OCR con facturas reales**, que es precisamente lo que va a medir el corpus.

**Estimaciones, marcadas como tales**: 30 facturas (10/10/10) y 1–2 horas de anotación; 500 facturas al
año en el escenario de Azure (0,75 USD/año); 6 fechas de satélite al mes y ~1 PU por tierra de 5 ha; y
el uso de meteo de 20–30 peticiones/día, derivado de los 4 municipios y de la API HATEOAS.

**Y lo que este documento NO es**: no es asesoría jurídica —ni de protección de datos, ni de licencias,
ni fiscal— y **no cierra D08**. Deja elegido el camino y medido el coste; la medición del OCR y la
construcción de la meteo son trabajo aparte.

---

## Anexo · Modelo de permiso escrito para las facturas

> Para copiar y firmar **por cada emisor** (o por el titular, si la factura es suya). No es un modelo
> jurídico: es la lista mínima de lo que hay que dejar dicho para que el corpus se pueda usar sin
> sorpresas.

```
PERMISO DE USO DE FACTURAS PARA EVALUAR LA LECTURA AUTOMÁTICA

Quien firma: ...................................................., con NIF ................,
en nombre de .................................................... (el emisor / el titular).

Autoriza el uso de las facturas que se relacionan al dorso —número, fecha y páginas— con esta
finalidad y estas condiciones:

1. FINALIDAD: evaluar la precisión de la lectura automática de facturas (campo por campo) en el
   programa CUE Digital. No se usan para ninguna otra cosa.
2. NO REDISTRIBUCIÓN: no se publican, no se comparten con terceros y no se incorporan al producto.
3. CONFIDENCIALIDAD Y ACCESO: solo accede a ellas quien hace la medición, y quedan guardadas fuera
   del repositorio del programa.
4. PLAZO Y BORRADO: se usan mientras dure la medición y se borran al terminarla, dejando constancia
   del borrado.
5. DATOS PERSONALES: las facturas llevan nombres y NIF, que son justamente algunos de los campos que
   se miden; por eso no se anonimizan. El tratamiento se limita a lo que dice este permiso.

Fecha y firma: ....................................................
```

Y en el registro de la medición se apunta, por factura: **emisor, número, página, formato y quién
autorizó**, para que el informe pueda **citar cada documento** y para saber qué se borra al final.
