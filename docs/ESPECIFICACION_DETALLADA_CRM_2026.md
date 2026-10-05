# Especificación detallada del CRM agrario

**01/10/2026.** Desarrollo del [plan maestro](PLAN_CRM_AGRARIO_2026.md). Este texto es el contrato
funcional para agentes que implementen una entrega concreta, no una descripción de funciones ya
disponibles. `AGENTS.md` y `DESIGN.md` siguen mandando para el código y el diseño. La aplicación
debe servir en el despacho y en el campo; el cuaderno oficial y la base real de David se preservan.

## 1. Cómo decidir qué es verdad

Toda ficha, mapa, gráfico y aviso debe distinguir cinco niveles de información:

| Nivel | Ejemplo | Tratamiento en pantalla |
|---|---|---|
| Registrado por una persona | «Pasé el rodillo el 10/10» | Hecho, con autor, fecha, tierras y posible corrección/anulación |
| Comprobado en documento o fuente | Producto nº de registro, recinto SIGPAC, factura confirmada | Mostrar documento/URL, fecha de consulta y vigencia |
| Medido en la propia tierra | Pluviómetro del agricultor | Mostrar aparato, ubicación, fecha, unidad y posibles huecos |
| Estimado fuera de la tierra | Lluvia de estación próxima o rejilla, NDVI de satélite | Decir «estimación», resolución, distancia/nubes y rango de incertidumbre |
| Deducido por reglas | «Podría estar en buen momento para revisar la nascencia» | Hipótesis explicada, nunca un hecho ni una garantía normativa |

**No hay un único “estado de la tierra” almacenado como texto mutable.** Se reconstruye desde
sucesos fechados, cultivo y observaciones, y se acompaña de fecha y procedencia. «Sembrada» es
un hecho tras guardar la siembra; «bien nacida» exige observación de campo. La lluvia y el NDVI
pueden sugerir dónde mirar, pero no certificar nascencia, humedad del suelo, plaga o cosecha.

## 2. Modelo temporal de tierra y trabajos

### 2.1 Identidad de tierra y recinto

Separar **tierra que el agricultor reconoce**, **recinto SIGPAC de una campaña** y **superficie
declarada a la PAC**. Una tierra puede contener varios recintos; un recinto puede cambiar de
geometría, uso o superficie entre campañas. Guardar una versión por campaña y fuente, con
referencia completa, polígono válido, área de la geometría, área SIGPAC, área trabajada/declarada,
fecha de consulta y estado de revisión. Nunca sustituir hectáreas declaradas por las calculadas.

Vista de las 64 tierras: tabla y mapa vinculados, con búsqueda por alias y referencia, filtros
por cultivo/municipio/estado/PAC, agrupación y selección múltiple. Una fila sin polígono sigue
en la tabla y en un grupo «sin forma». Al seleccionar un polígono se enfoca la fila y viceversa;
el mapa no debe saltar a otra provincia ni inventar un centro. Cambios de SIGPAC: previsualización
de `igual/cambiado/desaparecido/nuevo`, sin modificar notas, alias o historia.

Controles del mapa: mover/acercar con ratón o dedo, encajar toda la finca, localizar una
tierra, cambiar ortofoto/SIGPAC/cultivos/avisos, medir distancia/área y comparar dos
campañas. Distinguir el polígono propio del contorno oficial con leyenda y fecha; el
usuario puede ocultar capas. Si falla una imagen WMS, no borrar los polígonos ni dejar
una fotografía vieja sin fecha. Probar alineación de capas, ejes y coordenadas con
recintos conocidos, geometrías multipartes, zonas al borde de provincia y 1024 px.

### 2.2 Taxonomía de trabajos

El código actual contiene `Labor.tipo` generales como `laboreo`, `siembra`, `riego`, `cosecha` y
`otra`. Añadir una clasificación estable **sin romper los códigos antiguos**: preparación de
suelo (cultivador, rodillo, arado, grada...), implantación, fertilización, tratamiento,
riego, seguimiento, cosecha y trabajo auxiliar. «Cultivador» y «rodillo» son subtipos de
máquina/operación, no sinónimos de siembra. Para cada apunte: fecha/hora, tierra(s), superficie
real, tipo/subtipo, cultivo/campaña, máquina, persona, insumos y dosis, duración, observación,
fotos, si está previsto/realizado/anulado y vínculo al asiento oficial cuando corresponda.

Puede hacerse una operación en varias tierras en una sesión, pero se guardan asignaciones
individuales de superficie y cantidad; la suma se comprueba antes de confirmar. El parte común
conserva quién y cuándo. Corregir una asignación no altera silenciosamente las demás.

### 2.3 Estado derivado y línea de tiempo

Cada tierra tiene una cronología ordenada por **fecha de ejecución**, no por fecha de entrada.
Ejemplo de cabecera el 16/10: «Veza sembrada el 12/10 · rodillo el 13/10 · lluvia estimada
15 mm desde entonces · nascencia sin comprobar». El último trabajo de cada clase aparece
también en la ficha y en la tabla; si se anula, se recalcula el estado desde el anterior.

Reglas de ejemplo, sujetas a validación agronómica antes de crear avisos:

- Rodillo registrado: etiqueta «Rodillo pasado» con fecha. No implica suelo compacto ni que
  haya sido suficiente; si se pasó antes de la siembra, mostrar ese orden real.
- Cultivador registrado: «Cultivador pasado». Si está planeado: «Pendiente», nunca «hecho».
- Siembra confirmada: «Sembrada», especie/variedad/lote/dosis y superficie. No deducir la
  especie de `alias` ni de la campaña anterior.
- Lluvia posterior: evento meteorológico separado. «Lluvia estimada tras la siembra» no
  cambia el hecho de siembra; puede generar tarea «comprobar nascencia».
- Sequía: indicador con ventana temporal, fuente y cobertura, sin afirmar sequía oficial ni
  estrés hídrico en la tierra solo por ausencia de lluvia en una estación.
- Tratamiento/abono: actualizar «última aplicación» y acumulados comprobados, no reemplazar
  el cultivo ni marcar automáticamente «cumple la PAC».

Definir una función pura `estado_parcela(parcela, campaña, eventos, observaciones, clima)`
o equivalente, con pruebas de eventos desordenados, repetidos, anulados y cambio de campaña.
El resultado contiene `hechos`, `estimaciones`, `avisos`, `faltan` y vínculos a sus fuentes.

### 2.4 Qué se ve en las tablas

Tabla de tierras: Nombre corto, SIGPAC, hectáreas, cultivo actual, último trabajo y fecha,
estado observado, lluvia estimada 7/30 días, PAC, acción. Tabla de trabajos: fecha,
tipo/subtipo, tierras, hectáreas, máquina, operario, insumos, estado, documento y coste.
Ambas permiten ordenar, buscar, filtrar, agrupar, elegir columnas, exportar vista y abrir
un panel lateral sin perder posición. Los totales usan **todas las filas filtradas**, no solo
las visibles por paginación. La pantalla muestra «N de M» cuando hay filtro y un botón
claro para quitarlo. En móvil: tarjeta breve y acceso al detalle, sin tabla comprimida.

## 3. Meteo, agua y satélite

### 3.1 Lluvia por tierra: tres fuentes posibles

1. **Medida local:** pluviómetro/manual/sensor del agricultor, con coordenada y fecha; es la
   mejor evidencia de ese punto, pero puede haber periodos sin lectura.
2. **AEMET:** estación observada, identificador, distancia/elevación, cobertura y fecha. La API
   pública incluye valores diarios por estación; **el dato de la estación no es la lluvia medida
   dentro de cada polígono**.
3. **Reanálisis o rejilla:** por ejemplo ERA5-Land (resolución nativa ~9 km); dar estimación
   espacial para tierras sin estación, con fuente y tamaño de celda. No presentarla con falsa
   precisión al litro o como medición parcelaria.

Prioridad configurable: medida local válida; si no existe, mostrar AEMET o rejilla con la
etiqueta adecuada. No promediar fuentes diferentes sin método y validación documentados.
Guardar serie por fuente y día con `valor_mm`, coordenada/celda, publicación, captura,
calidad/huecos. Sumar 7/30 días **solo si la cobertura temporal es completa**; si faltan
días, dar suma parcial etiquetada o «no se puede calcular». Separar observado, estimado y
previsión. La previsión no modifica el cuaderno histórico.
La clave necesaria para AEMET se guarda fuera del repositorio y su ausencia deja un estado
«sin fuente conectada»; la consulta externa se hace en servidor, con caché y límites.

En ficha de tierra: gráfico diario, lluvia acumulada desde siembra y última labor, comparación
con el promedio histórico **solo si se dispone de una serie comparable**, y un acceso para
añadir «he medido aquí X mm». Si hay varias tierras cercanas que caen en la misma celda,
podrán compartir estimación, pero se explica por qué.

### 3.2 Sequía y “buen momento”

No hacer un semáforo universal. Un indicador agronómico debe especificar cultivo, fase,
fecha de siembra, suelo (si se sabe), temperatura, lluvia, riego y observación, y mantener
el estado `insuficientes datos` cuando falten. Ejemplo prudente: «Lleva 20 días sin lluvia
registrada en la fuente X; conviene revisar esta tierra». No escribir «está seca» sin
medición/observación, ni «ahora toca tratar» por una señal meteorológica aislada. Cualquier
recomendación de aplicación de producto requiere además etiqueta, autorización y juicio humano.

### 3.3 Imágenes e índices satelitales

Piloto con imágenes Sentinel-2 L2A de Copernicus para **fechas concretas**, color natural,
infrarrojo y NDVI. Recortar por geometría verdadera, mostrar fecha/hora, fuente, nubes
sobre el polígono, píxeles válidos y resolución. El servicio estadístico permite percentiles
y máscara de nubes; usar máscara de nubes/nodata antes de cualquier serie. Si el recinto
es demasiado pequeño para suficientes píxeles independientes, o casi todo está nublado,
mostrar «no hay imagen útil». No fabricar un NDVI mediante una foto aérea RGB del PNOA.

Gráfico de evolución con puntos de adquisición, no línea continua que parezca medición
diaria. Comparar con otras fechas solo si hay cobertura y cultivo comparable. Un descenso
de NDVI es **señal para inspeccionar**: puede deberse a cosecha, siembra, sequía, nubes,
suelo desnudo o calibración. El usuario puede abrir la imagen y registrar una observación
de campo. Primero ensayar coste/cuota, latencia, licencias y resolución con 3 tierras de
tamaño distinto; después extender a 64 con caché, solicitudes agrupadas y actualización
programada razonable. Nada de consultas costosas en cada carga del panel.

Fuentes: [AEMET OpenData](https://opendata.aemet.es/dist/), [ERA5-Land en Copernicus](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview),
[Sentinel-2](https://sentinels.copernicus.eu/sentinel-data-access/sentinel-products/sentinel-2-data-products/collection-1-level-1c)
y [API estadística de Copernicus](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Statistical.html).

## 4. Productos, compras, etiquetas y existencias

### 4.1 Identificar el producto de verdad

El **nombre comercial** no basta: almacenar número de registro, titular, presentación,
formulación, unidad, lote, caducidad y versión/fecha de la etiqueta. Foto de anverso y
reverso y PDF oficial cuando exista. La cámara ofrece recorte/rotación y calidad de imagen;
la lectura automática propone campos, pero el usuario los confirma. Una foto de la etiqueta
no prueba que una dosis o uso esté autorizado; contrastar número de registro y condiciones
vigentes para el cultivo, plaga, método, fecha y zona en el [Registro oficial del MAPA](https://www.mapa.gob.es/es/agricultura/temas/sanidad-vegetal/productos-fitosanitarios/registro-productos/).
Si el registro no responde o no se encuentra una ficha vigente, mostrar «no comprobado».

El catálogo de la explotación referencia el registro oficial, pero conserva el nombre que
consta en la factura y el lote que consta en el envase. Una foto puede contener dos productos;
no fusionarlos por similitud de nombre. Separar **producto** (qué es), **presentación/envase**
(5 L), **lote** (trazabilidad) y **movimiento** (entró/salió/se devolvió/se perdió).

### 4.2 Libro de existencias por producto y lote

Movimientos: compra confirmada, entrada manual con motivo, consumo por tratamiento,
devolución, ajuste por inventario, merma/derrame y traspaso entre almacenes. Todos tienen
fecha, cantidad decimal, unidad, documento/persona y auditoría. Saldo = entradas válidas
− salidas válidas; anular un tratamiento revierte su consumo, sin borrar la historia.
No sumar litros con kilos ni envases de concentraciones diferentes. Conversiones solo con
factor documentado y aplicable a esa presentación.

**Caso obligatorio:** compra confirmada de 5 L, tratamiento de 2 L en tierra A y de 3 L en
tierra B: existencias 0 L, factura vinculada a los dos consumos, cada tierra enseña su dosis
por ha y el total real de producto. Si el usuario escribe «2 L/ha» en 1 ha, el consumo es
2 L; si escribe «2 L» en 1 ha, no se vuelve a multiplicar. Si A se anula, saldo 2 L y B
sigue intacta. Un intento de 4 L con saldo 3 L avisa y pide corregir, registrar entrada
o aceptar una discrepancia justificada según política del cuaderno; nunca altera a escondidas
una compra ni impide registrar lo que de verdad ocurrió. Saldo negativo queda marcado como
problema de inventario, no se convierte en cero.

Pruebas: compra duplicada, factura corregida/anulada, lote caducado, unidad incompatible,
tratamiento compartido entre parcelas, aplicación parcial, devolución y uso sin factura.
El almacén muestra saldo, origen de cada entrada/salida y fecha de última comprobación.

### 4.3 Aplicación fitosanitaria: campos y decisiones

En móvil: elegir tierra/grupo, fecha y superficie; producto/lote (buscable por marca, número
o foto), motivo/plaga, cantidad **por ha o total con unidad explícita**, máquina y aplicador,
condiciones/horario cuando correspondan, resultado y foto opcional. La pantalla resume antes
de guardar: «Tierra A · 1 ha · 2 L en total · 2 L/ha · quedarán 3 L del lote X».
La dosis máxima, plazo de seguridad y usos se comparan **con etiqueta/registro de la versión
aplicable**, no con un valor global aislado. Registrar avisos y permitir anotar lo sucedido
sin falsificar datos, conservando quién confirmó. Las exigencias mínimas del cuaderno y los
documentos a conservar proceden del [RD 1311/2012](https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605)
y de la [Orden APA/204/2023](https://www.boe.es/buscar/act.php?id=BOE-A-2023-5699).

## 5. Abono, nutrientes y plan

Catálogo de fertilizantes: nombre, clase, presentación, composición N/P₂O₅/K₂O **con unidad
y base declarada**, otros nutrientes, fabricante/lote, densidad si hace falta convertir
volumen a masa y documento/etiqueta. Por defecto no atribuir riqueza NPK a un nombre
parecido; la fuente es la etiqueta, ficha confirmada o análisis. Lotes y existencias usan
el mismo libro de movimientos, separado del de fitosanitarios por categoría.

Al apuntar aplicación: tierra, fecha, material, cantidad total y unidad, superficie realmente
abonada, kg/ha o L/ha, método, máquina, condiciones y, si aplica, agua de fertirrigación.
Calcular `kg de producto/ha = kg aplicados / ha tratadas`. Para un producto al 20 % N
**confirmado**, `kg N/ha = kg producto/ha × 0,20`; para P y K respetar las unidades
declaradas y mostrar la conversión. Si la composición es desconocida, mostrar cantidad
aplicada y «nutrientes sin calcular», no cero. En aplicaciones compartidas repartir
cantidades por tierra y comprobar suma. Relacionar con plan, análisis de suelo y límites
locales versionados; hacer visibles exceso, margen y datos faltantes, con fuente legal.

El plan anual distingue **recomendado/previsto/aplicado**, admite cambios de clima/cultivo
y conserva la versión anterior. El [RD 1051/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23052)
exige considerar, entre otros datos, los recintos, suelo, lluvia y nutrientes; no convertir
un cálculo simplificado en asesoramiento reconocido sin validación de la autoridad. La PAC
usa la evidencia del abono cuando la práctica lo pide, pero el apunte de abono no marca
automáticamente una ayuda como cumplida.

## 6. Planificación de cultivos y PAC

### 6.1 Calendario multiannual

Por cada recinto y campaña: cultivo principal y secundario, variedad, fechas previstas/reales,
secano/regadío, superficie elegida, cosecha previa, cubierta, barbecho, siembra directa y
práctica de ecorrégimen **solicitada**. Registrar por separado práctica **hecha** y ayuda
**solicitada/concedida**. La tabla permite comparar 2024–2027 y filtrar los recintos cuya
propuesta del próximo año todavía no está decidida. Vista de arrastrar/copiar campaña
solo genera borradores revisables, nunca declara superficies de forma automática.

«¿Qué puedo sembrar?» devuelve **escenarios**, no una lista binaria universal. Para cada
candidato: lo que sabemos (cultivo anterior, secano, hectáreas, práctica elegida), cómo
cambia el porcentaje global de rotación/diversificación, datos ausentes y artículos
aplicables. Puede decir «esta propuesta no alcanza el porcentaje calculado con los datos
actuales»; no «prohibido sembrar» salvo norma concreta interpretada y vigente. Hay otras
restricciones agronómicas/comerciales distintas de la PAC.

### 6.2 Comprobador de prácticas por campaña

Motor de reglas con versión, ámbito (secano/regadío, comarca, tamaño), periodo, fuentes,
entradas, fórmulas, excepciones y pruebas. Evaluar a **nivel de explotación y de recinto**;
los porcentajes de rotación no se deciden tierra a tierra. Los artículos 33–37 del
[RD 1048/2022](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23048) muestran que rotación
y siembra directa tienen ámbitos, porcentajes y excepciones distintos: no guardar
`ecorregimen="sí"` como prueba suficiente. Aplicar la redacción vigente en cada año y la
convocatoria de Castilla y León. Mostrar para cada regla: datos usados, operación, umbral,
resultado `compatible/incompatible/no comprobable/revisión administrativa`, evidencia y
enlace. Un cambio de cultivo en un recinto recalcula la propuesta del conjunto, sin
reescribir lo declarado en años cerrados.

### 6.3 Paquete para el día de la PAC

Hoja de trabajo por recinto: referencia, geometría y diferencias, superficie oficial y
declarada, cultivo previsto y real, uso, práctica, trabajos relevantes con fechas,
documentos, incidencias y preguntas pendientes. Resumen por explotación y práctica con
totales trazables y alertas. Exportar PDF/CSV/GeoJSON **preparatorios**, con fecha y
advertencia clara de que no son solicitud presentada. Verificar los nombres y campos con
la solicitud oficial del año antes de ofrecer una plantilla compatible. No conectar ni
enviar a la administración en esta fase.

## 7. Diseño CRM con Stitch: trabajo concreto

El aspecto actual no se arregla cambiando solo colores o copiando otra tabla. Primero
rediseñar la **arquitectura de información**, después patrones compartidos y finalmente
pantallas reales con datos densos. Aprovechar `backend/scripts/disenar_con_stitch.py` y
los once diseños de escritorio existentes como referencias, **no como producto final**.
La clave ya compartida en una conversación debe rotarse antes de nuevas llamadas; nunca
escribirla en el repositorio ni copiarla a prompts. Stitch no tiene herramienta callable
en este entorno; el agente que ejecute la fase usará el script existente con una clave
vigente en su entorno.

### 7.1 Paquete que se pasa a Stitch

Para cada pantalla: `DESIGN.md` vigente; persona y tarea; datos reales anonimizados
(64 tierras, años, importes de prueba, casos sin geometría); estado vacío, parcial,
error y sin cobertura; ancho 390/1024/1440; acción primaria; criterios de accesibilidad;
frases de `textos.py` ya disponibles; prohibición de saldos, teléfonos, fechas y «cumple»
inventados. Guardar prompt, ID, imagen y explicación en `docs/stitch/`, y registrar qué
se aceptó/rechazó. **No aplicar HTML generado sin revisar el flujo y los datos**.

### 7.2 Lote de pantallas y patrones a diseñar

1. Marco de escritorio: navegación agrupada, búsqueda global, finca/año, tarea rápida.
2. Inicio: trabajo de hoy, datos por revisar, mapa pequeño, avisos y paneles configurables.
3. Tierras: tabla + mapa sincronizados y ficha lateral para 64 parcelas.
4. Ficha completa de tierra: historia, labores, cultivo, meteo, satélite, economía y PAC.
5. Calendario y parte de trabajo: previsto, realizado y trabajo para terceros.
6. Almacén y producto: catálogo, lotes, libro de movimientos, foto de etiqueta.
7. Aplicación de producto: móvil rápido y escritorio, con dosis total/ha y saldo visible.
8. Abonado: composición, kg/ha, nutrientes y plan frente a real.
9. Compras: bandeja de OCR, corrección por campo y pagos pendientes.
10. Ventas: partida física, documento económico, cliente y cobro.
11. Dinero: facturas, movimientos, conciliación, inversión y resultado.
12. PAC: planificación de campaña, comparación de recintos y explicación de reglas.
13. Máquinas: fichas, inspecciones y calendario.
14. Contactos: agenda y ficha con relaciones.
15. Clima y satélite: serie temporal, fecha/nubes/calidad y observación en campo.

Se entrega **una familia primero** (Inicio + Tierras + Ficha), se prueba con David y se
ajusta el sistema antes de pedir las demás. Evaluación de cada diseño: encontrar una
tierra/factura/tarea en tres acciones o menos, ver qué falta, volver sin perder contexto,
tablas legibles a 1024, foco de teclado, lectura a pleno sol y ningún dato fingido.
Texto definitivo siempre en `textos.py`; CSS y `DESIGN.md` cambian juntos. Los componentes
de React se reutilizan, pero la navegación y los formularios pueden rehacerse.

### 7.3 Anatomía de la interfaz de escritorio

En 1440 px: navegación agrupada a la izquierda (Inicio; Tierras y trabajo; Compras y ventas;
Dinero; PAC; Personas y máquinas; Cuaderno y documentos), barra superior de finca/campaña/
búsqueda, cabecera con título y acción primaria, franja de filtros siempre visible, contenido
principal (tabla/calendario/mapa) y panel de detalle a la derecha **solo cuando quepa**. En
1024 px, el detalle pasa debajo o se abre como vista completa; ninguna acción queda fuera
por desplazamiento horizontal sin indicación. En 390 px, inicio de campo y tarjetas con las
acciones de registro primero. «Volver» conserva la lista, filtros y posición.

Una ficha tiene el mismo encabezado en cualquier entrada; sus pestañas son estables y
predecibles. Los formularios de escritorio pueden usar dos columnas y resumen lateral,
pero la secuencia de preguntas y validaciones es la misma que en móvil. En cada pantalla:
estados vacío, cargando, sin red, sin permiso, error recuperable y dato parcial. Los textos
son acciones concretas; no hay botones «Guardar» sin indicar qué se va a guardar.

### 7.4 Definición de los paneles y sus cifras

| Panel | Tarjetas iniciales | Fórmula/fuente obligatoria | Si falta información |
|---|---|---|---|
| Hoy | Trabajos previstos/vencidos, observaciones pendientes, alertas de plazo, papeles por revisar | Tareas y asientos de la finca/campaña, con fecha de ejecución | No convertir tarea sin fecha en «al día» |
| Tierras | Superficie por cultivo, tierras sin cultivar declarado, últimas labores, lluvia desde siembra, señales satelitales | Superficie seleccionada y sin solapes; eventos por parcela; serie meteo identificada | «Sin forma», «sin lluvia comparable», «imagen no útil por nubes» |
| Economía | Facturas por pagar, cobros pendientes, gastos/ingresos devengados, caja conciliada, inversión | Documentos confirmados y pagos vinculados; moneda y periodo | Sin precio ≠ 0 €; pagos sin factura quedan «por conciliar» |
| PAC | Recintos revisados, superficies por práctica, conflictos, evidencias pendientes | Expediente y motor de reglas **de esa campaña** | Norma o dato ausente = «no comprobado» |
| Máquinas | Próximas ITV/ITEAF, revisiones, averías abiertas, coste por activo | Activos clasificados, certificados, partes y facturas | Fecha de inspección desconocida ≠ «en regla» |

Cada tarjeta puede abrir su tabla filtrada y una explicación «cómo se ha calculado».
Personalización por usuario: elegir/ordenar tarjetas, columnas y vistas guardadas;
finca y campaña en la URL o estado navegable para que al volver no cambie el contexto.
Hay una vista inicial sencilla y «restablecer». Para gráficos anuales: comparación del
mismo concepto entre campañas, con criterios de imputación visibles; no unir años con
definiciones diferentes ni sumar valores parciales como completos.

## 8. Fases E0–E13: definición de terminado

El orden del plan maestro es orientativo; cada entrega empieza declarando dependencias.
Las siguientes listas especifican trabajo y pruebas, además de la tabla resumen del plan.

### E0 — Auditoría y mapa de tareas

Recorrer las 29 pantallas y 16 entradas con datos de muestra densos; inventariar para cada
una propósito, acción principal, rutas de entrada/salida, duplicaciones, filtros, campos,
estados y llamadas. Probar cinco tareas completas: hallar una tierra, registrar un trabajo,
comprar y gastar producto, consultar abono de una campaña, preparar un recinto PAC. Medir
pasos y puntos de duda; contrastar capturas 390/1024/1440. **Salida:** mapa de navegación
actual, problemas P0–P3 y propuesta de agrupación, sin modificar datos de usuario.

### E1 — Arquitectura de información y sistema visual

Prototipos Stitch del marco, Inicio y Tierras con casos llenos/vacíos; navegación única,
búsqueda y selector de finca/año. Probar que abrir factura o tierra y volver conserva
filtros y posición. Comparar dos variantes con tareas, no elegir por estética sola.
**Salida:** decisiones documentadas, componentes, `DESIGN.md`/CSS alineados, revisión
con teclado y lector de pantalla básico. No reescribir todos los módulos de una vez.

### E2 — Identidad de tierras y mapas

Versionar recintos/geometrías, tabla y mapa sincronizados, ficha lateral y 64 tierras
sin pérdida. Ensayar importación por lote, solapes y diferencias de superficie. Un
polígono ausente no se inventa. **Prueba:** tres recintos, uno cambiado y otro sin
geometría, visibles con origen y año; cambio de campaña no altera la historia.

### E3 — Medición de lectura de documentos

Corpus anonimizado de facturas, fotos, albaranes y etiquetas, con verdad de referencia
por campo. Registrar omisiones/falsos positivos, dependencia de Tesseract e idioma,
errores de importes y NIF. **Salida:** tabla de métricas, ejemplos de fallos y umbrales
acordados antes de cambiar el extractor. Sin afirmar precisión con solo tests sintéticos.

### E4 — Compras, producto y existencias

Rediseñar bandeja de OCR y corrección; enlazar producto y lote; crear libro de entradas,
consumos y ajustes. Comprobar etiqueta contra registro oficial en fecha de consulta.
**Prueba canónica:** 5 L comprados, 2 L en A y 3 L en B, saldo 0; anulación y factura
rectificativa recalculan y mantienen historia. No contar compra dos veces por foto/PDF.

### E5 — Contactos

Agenda con roles múltiples, búsqueda, duplicados, permisos y vínculos desde facturas,
ventas, maquinaria y partes. Migrar nombres libres con revisión. **Prueba:** dos
contactos homónimos no se mezclan; cambiar nombre muestra vínculos sin alterar
facturas históricas ni contactos de otra finca.

### E6 — Ventas y cobros

Mantener la salida física `VentaDeCosecha`; añadir documento económico, precios,
vencimientos, cobros parciales y devoluciones. **Prueba:** 10 t entregadas sin precio
no generan 0 € ni ingresos supuestos; al vincular factura de 8 t y dos cobros, se
mantienen saldos físicos y financieros distintos.

### E7 — Gastos, inversiones y abonado

Libro económico con coste por destino y fase de abonado ampliada: lote/composición,
kg producto/ha y kg N/P₂O₅/K₂O/ha, planificado frente a aplicado. **Prueba:** composición
desconocida produce nutrientes desconocidos; gasto de máquina no se duplica como
consumo de producto; factura impagada figura como deuda aunque aún no haya salida bancaria.

### E8 — Maquinaria e inspecciones

Tractores/remolques/pulverizadores y demás equipos, documentos, ITV/ITEAF según
clasificación y norma, mantenimientos y costes. **Prueba:** remolque recibe su regla
ITV aplicable, pulverizador su ITEAF, equipo excluido no recibe aviso falso; fecha
del certificado y calculada se comparan, no se sustituyen.

### E9 — Trabajos y estado de tierra

Calendario, planificado/realizado, partes para terceros y cronología derivada por
recinto. Añadir rodillo y cultivador sin invalidar `Labor.tipo` histórico. **Prueba:**
rodillo → cultivador → siembra cambia la ficha en cada paso; evento previsto no cambia
estado; anular siembra devuelve estado previo; trabajo a tercero no se atribuye a finca propia.

### E10 — Paneles, tiempo y satélite

Cinco paneles (Hoy, Tierras, Economía, PAC, Máquinas), filtros y personalización;
piloto meteorológico y Sentinel en tres tierras. **Prueba:** lluvia AEMET dice estación
y distancia, ERA5 dice estimación de rejilla, satélite nublado no dibuja NDVI fiable;
un panel sin precios dice «ingresos sin datos». Medir latencia/coste antes de escalar.

### E11 — Banco por fichero y conciliación

Importar movimiento en lectura previa, idempotencia, reglas de traspaso y
conciliación reversible. **Prueba:** dos importaciones del mismo extracto no duplican,
pago parcial reduce deuda, traspaso propio no altera resultado; sin clave bancaria.

### E12 — PAC piloto y planificación

Campañas y escenarios de cultivos, motor de reglas versionado para dos prácticas
revisadas contra BOE/convocatoria. **Prueba:** caso que cumple, que no cumple,
excepción y dato ausente; al cambiar un recinto, se recalculan porcentajes globales.
Se muestra la regla, su cálculo y la fecha; nunca «PAC aprobada».

### E13 — PAC completa y banca opcional

Extender prácticas una a una, con revisión experta y fuentes de cada campaña;
exportar paquete preparatorio. Solo si existe decisión expresa y proveedor habilitado,
integrar lectura bancaria consentida. **Prueba:** fuente desactualizada invalida la
evaluación; revocar conexión corta el acceso; ningún mock se presenta como conexión real.

## 9. Pruebas transversales y salida por fases

Además de las pruebas de código de `AGENTS.md`, cada entrega visual usa datos
representativos (64 tierras, recintos sin forma, compras sin precio, trabajos anulados,
dos fincas y dos campañas) y captura en 390/1024/1440 px. Antes de una migración:
copia restaurable, simulación sobre copia, número de filas antes/después, comprobación
de referencias y plan de vuelta. API y UI no muestran datos de otra finca ni saldos
a un usuario sin permiso. Offline: cola con estado visible, resolución de conflicto y
sin duplicar al volver cobertura. La aceptación humana observa tareas completas,
no solo que el botón “hace algo”.

El despliegue se hace por módulos activados gradualmente y con opción de volver a la
vista anterior mientras se valida. Se puede terminar E2 sin E10 (mapa sin satélite);
se puede terminar E4 sin conexión bancaria; no se puede dar por terminado E12 sin
fuentes legales versionadas. Cada agente documenta qué datos reales o permisos faltan
para comprobar la entrega completa.
