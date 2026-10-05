# Lo que se apunta de cada tierra, campo por campo

> **Comprobado el 24/09/2026** contra el contenido mínimo del CUE (anexo II del Real Decreto
> 1054/2022), que es lo que el programa guarda en `app/iuws_contenido.py` campo por campo y con su
> número, y contra el mapeo de `app/iuws_mapeo.py`.
>
> Este documento existe porque la pregunta «¿está completo el registro de esta tierra?» no se puede
> contestar a ojo. Aquí está la respuesta con lo que hay y, sobre todo, **con lo que falta y por
> qué falta**, que son tres motivos muy distintos y mezclarlos sería mentir.

---

## 1. El registro pide trece bloques, y este programa los tiene todos

| Bloque del anexo II | De qué es | Campos | Obligatorios | Dónde se apunta |
|---|---|---|---|---|
| 1. Datos generales de la explotación | De la finca | 4 | 1 | *Mi finca* |
| 2. Datos del titular | De la persona | 4 | 2 | *Mi finca* |
| 3. Cosecha comercializada y venta directa | De lo vendido | 5 | 3 | *Lo que he vendido* |
| 5. Labores culturales | De los trabajos | 3 | 1 | *He hecho un trabajo* |
| 6. Siembra y plantación | De sembrar y plantar | 12 | 1 | *He sembrado* / *He plantado* |
| 8. Tratamientos fitosanitarios | De los productos | 23 | 2 | *He echado producto* |
| 8. Edificaciones e instalaciones | De las naves | 3 | 1 | *Mis cosas* → naves |
| 9. Maquinaria y equipos | De las máquinas | 1 | 1 | *Mis cosas* → máquinas |
| 9. Fertilización | De los abonos | 5 | 2 | *He abonado* |
| 9. Riego y fertirrigación | Del agua | 6 | 0 | *He regado* |
| 12. Datos de superficies | De las tierras | 5 | 1 | *Mis parcelas* (o el mapa) |
| 13. Analíticas | De los boletines | 6 | 2 | *Mis cuaderno* → análisis |
| GIP 1.1 Medidas preventivas | De lo que se hace antes | 1 | 1 | *Mi cuaderno* → medidas |

Los trece salen **también en el cuaderno impreso y en el fichero de datos** (ver el README, sección
«El cuaderno en papel»): un dato que se guarda y no sale en el papel es un dato que no existe.

## 2. Lo que se apunta **por tierra** (esto es lo que preguntabas)

Todo lo que se apunta de una actividad lleva **la parcela**, y hay una pantalla para cada cosa. Se
comprueba mirando qué tablas guardan `parcela_id` y qué formularios las escriben:

| Lo que se apunta | Tabla | Pantalla | Qué dice de la tierra |
|---|---|---|---|
| Qué hay sembrado este año | `ParcelaCultivo` | *Qué hay sembrado* | Cultivo, variedad, sistema y fechas, por campaña |
| Tratamientos | `TratamientoFitosanitario` | *He echado producto* | Producto, dosis, **plaga**, **por qué**, aplicador, **máquina**, plazo, franja, eficacia |
| Abonos | `RegistroFertilizacion` | *He abonado* | Abono, kilos, nutrientes, modo, momento, si está en zona de nitratos |
| Plan de abono | `PlanAbonado` | *El plan de abono* | Lo previsto por parcela, para compararlo con lo echado |
| Labores (labrar, podar, segar…) | `Labor` | *He hecho un trabajo* | Tipo de labor, superficie y **con qué máquina** |
| Riego | `Labor` (tipo riego) | *He regado* | Agua, **de dónde salió**, sistema de riego, **nº de contador** |
| Siembra y plantación | `Labor` (tipo siembra) | *He sembrado* | Semilla, dosis, **lote**, si venía tratada, si se compró, siembra directa |
| Pastoreo | `Labor` (tipo pastoreo) | *He hecho un trabajo* | Si el ganado era propio o de otros |
| Cosecha | `Labor` (tipo cosecha) | *He cogido la cosecha* | Kilos y qué salió (semilla, plantas, restos) |
| Venta de la cosecha | `VentaDeCosecha` | *Lo que he vendido* | Producto, cantidad, comprador, lote, albarán |
| Análisis | `Analitica` | *Mis análisis* | Suelo, agua, cultivo o residuos, con su boletín |

**Lo que esto quiere decir:** para cada tierra se puede contestar «¿qué se hizo, con qué, cuándo, con
qué máquina y con qué resultado?», que es exactamente lo que se pregunta en una inspección.

## 3. Lo que falta, y por qué falta (tres motivos, no uno)

### 3.1. Falta el **código de la DGC**, y no lo puede poner este programa

El volcado oficial no identifica la tierra por su referencia del SIGPAC, sino por un
**identificador único de cada DGC** que, según el anexo VI, lo genera **el CUE comercial** que envía
los datos. Es decir: no es un dato del agricultor ni nuestro, es un identificador que asigna la
administración. Afecta a todos los bloques de actividad (tratamientos, labores, siembra, cosecha,
pastoreo, cubierta, riego, análisis).

**Qué hacemos mientras tanto:** cada apunte se guarda con **su parcela y su referencia del SIGPAC**,
que identifica la tierra sin ninguna duda dentro de este cuaderno, y se puede enseñar en papel y
comprobar contra el visor. Está preguntado por escrito a la FEGA (ver
[`CORREO_LISTO_PARA_ENVIAR.md`](CORREO_LISTO_PARA_ENVIAR.md)).

### 3.2. Faltan los **valores de los catálogos oficiales**, que están detrás de un captcha

El interfaz de la Junta no quiere el texto («Pulgón», «Pozo», «Goteo») sino un **código** de sus
tablas: `PLAGAS`, `ENFERMEDADES`, `MALAS_HIERBAS`, `JUSTIFICACION_ACTUACION`, `EFICACIA_TRATAMIENTO`,
`SIST_RIEGO`, `UNIDADES_MEDIDA`, `TIPO_ANALISIS`, `MATERIAL_ANALIZADO`, `PROD_VEGETAL`… El programa
**sí guarda el dato** (con el nombre que usa el agricultor) y lo que falta es la equivalencia con el
código. Los valores no están publicados: la web de SIEX los tiene detrás de un captcha y solo
publica la estructura de las tablas.

**Qué hacemos mientras tanto:** se guarda el nombre, se dice en pantalla qué falta, y **no se
inventa ningún código**. Está en el correo a la FEGA, con las quince tablas identificadas.

### 3.3. Faltan **cuatro datos** que sí se pueden tapar aquí, y se van tapando

| Dato que faltaba | Estado |
|---|---|
| Las partes de la referencia SIGPAC que no se guardaban (`Agregado` y `Zona`) | **Hecho** (ronda 1 *de este cierre*): son columnas y se rellenan al traer la parcela |
| La `ReferenciaCatastral` que pide el anexo II | **Hecho** (ronda 2 *de este cierre*): la pone el SIGPAC (`refcatparcela`) o el agricultor, si la tiene |
| **La máquina con la que se hizo cada labor** (`Maquinaria` en labores y siembra) | **Hecho** (ronda 4 *de este cierre*): las labores ya preguntan con qué máquina, como los tratamientos |
| **Qué tratamiento recibió la semilla, cuándo y si funcionó** (`UsoSemillaTratada`) | **Hecho** (ronda 5 *de este cierre*): se pregunta **solo si** el agricultor ha dicho que la semilla venía tratada |
| `PlanAbonado.CultivoPrecedente` (el cultivo anterior) | **Hecho** (ronda 6 *de este cierre*): se rellena solo, del cultivo declarado en la campaña anterior; el agricultor no lo teclea |
| `PlanAbonado.Herramienta` (si se usó una herramienta para hacer el plan) | **Hecho** (ronda 6 *de este cierre*): se pregunta con un sí o un no, igual que el campo oficial |
| `Riego.TipoEnergia` y las buenas prácticas de riego | **Pendiente**, y son **opcionales** en el anexo II |

> Las «rondas» de esta tabla son las del plan de cierre del anexo II, no las del proyecto entero:
> para el número de ronda del proyecto, mira [`LO_QUE_PIDE_LA_JUNTA.md`](LO_QUE_PIDE_LA_JUNTA.md).

> **El marcador de por dónde va esto:** de los 113 campos obligatorios de los 18 bloques, **61 se
> pueden mandar hoy** y 52 esperan un catálogo oficial o una respuesta de la Junta. El número sube
> cada vez que el cuaderno recoge un dato más, y hay un test que lo comprueba
> (`tests/test_mapeo_oficial.py`), así que no puede quedarse viejo sin que salte.

## 4. Lo que el programa **no** recoge, y está declarado

Dos bloques que el documento oficial nombra y este programa no pide, porque la app de la Junta
tampoco los pide y porque pedirlos sería inventarse la forma: **energía utilizada** y **cubierta del
suelo** (solo se apunta cuando se hace un mantenimiento de cubierta, que es una labor de las que el
documento nombra). Están explicados uno por uno en
[`LO_QUE_PIDE_LA_JUNTA.md`](LO_QUE_PIDE_LA_JUNTA.md), apartado 2 bis.

> **Actualización (ronda 24 del proyecto):** el tercero de esa lista, la **evaluación del
> tratamiento**, ya **no** está aquí. Desde la ronda 23 el cuaderno pregunta cómo de bien funcionó,
> así que lo único que falta es la equivalencia con los códigos oficiales de FEGA. Se apunta porque
> una lista de «lo que no recogemos» que se queda vieja engaña igual que un dato inventado.

Y una regla que vale para todo lo de arriba: **si un dato no se sabe, no se escribe**. Los campos
vacíos son «no lo sé», nunca un cero de relleno ni un «no» sin comprobar.
