# CUE Digital como gestión integral de la explotación

**Paquete ejecutable ampliado (01/10/2026):**
[Contrato de implementación](CONTRATO_IMPLEMENTACION_CRM.md): veinte pantallas,
contratos de datos, recorridos y veinticuatro entregas para DeepSeek.
[Matriz normativa](MATRIZ_NORMATIVA_CRM.md): fuentes oficiales, alcance y reglas
pendientes de transcribir antes de activarlas. Estos documentos concretan este plan.

**Especificación de producto y encargos para agentes. 01/10/2026.** Este documento amplía el
cuaderno actual; no afirma que las funciones nuevas estén hechas. Antes de implementar, leer
`AGENTS.md`, `DESIGN.md`, `docs/GUIA_UI_UX.md` y los tests del módulo afectado. La base real
`backend/cuedigital.db` contiene el cuaderno de David: no se usa para pruebas ni migraciones de ensayo.

**Desarrollo fase por fase:** [`ESPECIFICACION_DETALLADA_CRM_2026.md`](ESPECIFICACION_DETALLADA_CRM_2026.md)
define los trabajos, lluvia, satélite, existencias, abono, PAC, Stitch y criterios de terminado
de E0 a E13. Leer ambos documentos juntos; las estimaciones siempre llevan fuente y límites.

## 1. Decisión de producto

La aplicación debe responder, sin buscar en dieciséis módulos, a cinco preguntas diarias:

1. **¿Qué tengo y dónde?** Las tierras de la explotación, su geometría comprobada, cultivo por año,
   estado, trabajos, producción, documentos y costes.
2. **¿Qué debo hacer?** Trabajos pendientes, datos por completar, inspecciones, pagos y cobros, plazos
   de la PAC, y avisos normativos con su causa y su acción.
3. **¿Qué ha pasado?** Historia por tierra, campaña, cultivo, máquina, cliente y proveedor; lo que
   se hizo, quién lo hizo, qué se compró y qué se vendió.
4. **¿Cómo van las cuentas?** Ingresos, gastos, inversiones, facturas por pagar o cobrar, movimientos
   bancarios conciliados y margen, siempre con origen y con «falta información» si procede.
5. **¿Qué puedo declarar o solicitar?** Preparación de la PAC y del cuaderno con evidencias por
   recinto y campaña, mostrando lo comprobado, lo incompatible y lo que exige revisión humana.

No convertir una estimación en una declaración oficial. El sistema ayuda a **preparar y revisar** la
PAC; el envío y la elegibilidad final dependen del procedimiento y de las fuentes oficiales de cada
campaña. No presentar «cumple» por el mero hecho de haber rellenado un campo.

### Dos modos, un mismo dato

- **En el campo (móvil, sin cobertura):** «Apuntar trabajo», «Ver esta tierra», «Foto de un papel»,
  «Pendiente de hoy». Botones grandes, una pregunta principal, borrador local y confirmación. Se
  conservarán los recorridos actuales que ya funcionan sin conexión.
- **En el despacho (ordenador):** una aplicación de gestión con búsqueda global, filtros guardables,
  tablas y fichas, calendario, mapa y varios paneles. Editar varias tierras, revisar documentos y
  conciliar dinero exige densidad de información y trazabilidad, no tarjetas de móvil estiradas.

Cada función tendrá una sola ubicación principal en la navegación y accesos contextuales desde las
fichas relacionadas. «Producto», «máquina» y «tierra» son entidades distintas; hoy comparten a veces
«Mis parcelas, productos y máquinas», lo que dificulta encontrarlas. El menú actual de 16 entradas
(`backend/web/app.js`, `MODULOS`) no debe ser el mapa conceptual futuro.

## 2. Lo comprobado en el repositorio; límites de la verificación

| Área | Evidencia actual | Lo que falta para la petición |
|---|---|---|
| Tierras | `Parcela`, `ParcelaCultivo`, importación CUECyL/SIGPAC, dibujo calculado y mapa de consulta por punto; 64 tierras constaban en la cuenta en la revisión anterior | Ficha unificada, calidad de referencias, geometrías de las tierras importadas, mapa de **toda** la explotación, historial y costes por recinto. No se han inspeccionado aquí los datos privados de la cuenta |
| Trabajos | `Labor`, tratamientos y abonos por campaña, con máquina opcional | Calendario de trabajos programados, partes para terceros, duración, coste, operario y estado. Distinguir planificado de realizado |
| Compras | `Factura` y `LineaDeFactura`; extracción PDF/foto, propuesta editable, avisos aritméticos, duplicado por huella, anulación y enlace al almacén | Evaluación con corpus representativo, cobros/pagos, vencimientos, tipos de gasto e inversión, reparto por tierra/campaña, conciliación bancaria. La factura de compra actual no es contabilidad completa |
| Ventas | `VentaDeCosecha` y API con fecha, producto, cantidad, comprador, albarán y origen; contraste cosechado/vendido | **No tiene precio ni importe** (decisión expresa en `models.py`), ni factura emitida, ni vencimiento ni cobro. Por tanto un panel de «ingresos por ventas» no puede salir de esta tabla |
| Maquinaria | `EquipoAplicacion`: ROMA, serie y fechas ITEAF | Inventario de tractores, remolques y otros equipos, ITV/ITEAF según tipo, seguro, mantenimiento, averías, documentos, costes y alertas |
| Personas | `Aplicador` y `Asesor`, con datos para el cuaderno | Agenda general de clientes, proveedores, propietarios, arrendadores, talleres y operarios; relaciones y permisos por finca |
| Economía/bancos | Importes de compras en facturas; no hay libro de tesorería | Cuentas, movimientos, pagos/cobros, conciliación, presupuestos, inversiones y resultado por año. No hay conexión bancaria |
| PAC | Cultivo por parcela y un texto opcional de ecorrégimen | Expediente anual por recinto, reglas versionadas, evidencias, diferencias con SIGPAC/solicitud previa y exportación verificable. No hay motor que pueda garantizar elegibilidad |
| UI | React/htm, 29 pantallas, menú de 16 módulos, tablas y dos paneles laterales; Stitch guardado | Investigación de tareas con David, arquitectura de información nueva, formularios de escritorio, búsqueda y estados de carga/vacío/error, accesibilidad y revisión visual con datos densos |

La auditoría dirigida del 01/10/2026 pasó en las pruebas de facturas, ventas, SIGPAC, parcelas,
mapa y geometría. La prueba de foto con OCR español se ejecutó; el único caso omitido era el aviso
para un equipo que **solo** tuviera OCR inglés, porque aquí está instalado el español. Es cobertura
de casos fabricados, no una medición de aciertos sobre facturas reales. La documentación anterior
(`docs/RESUMEN_PARA_CHATGPT.md`) es una fotografía fechada y contiene recuentos y estados viejos;
no usarla como prueba de que una capacidad económica o de PAC existe.

## 3. Navegación y pantallas propuestas

La barra global muestra **finca, campaña, búsqueda y «Apuntar»**. La campaña seleccionada debe ser
visible y modificable; cambiarla no modifica ningún dato. Buscar por alias, referencia SIGPAC,
producto, contacto, factura, máquina o número de documento devuelve resultados separados por tipo.

| Sección principal | Pantalla inicial | Ficha y acciones |
|---|---|---|
| Inicio | Panel personalizable con «hoy», alertas y resumen de explotación | Cada número abre su lista filtrada y explica fuente y fecha de actualización |
| Tierras y mapa | Lista/mapa sincronizados, campaña y capas | Tierra: identidad, recintos, geometría, cultivo, rotación, trabajos, producción, documentos, gasto, ingresos imputados y PAC |
| Trabajo | Calendario y partes; pendientes/realizados | Orden de trabajo, quién, máquina, parcela, duración, insumos, coste y prueba; duplicar una labor sin duplicar un apunte oficial |
| Compras y almacén | Entrada documental y cola «por revisar» | Factura, líneas, proveedor, vencimiento, pago, productos y asignación de costes |
| Ventas y clientes | Partidas de cosecha, documentos y cobros | Venta física, factura emitida cuando proceda, comprador, vencimiento y cobro; enlazar sin confundir cantidades con euros |
| Dinero | Tesorería, pendientes y resultado | Cuentas, movimientos, conciliación, gastos, ingresos, inversiones, presupuesto |
| Máquinas | Inventario y calendario de inspecciones | Vehículo/equipo, documentación, ITV o ITEAF aplicable, seguro, mantenimiento y costes |
| PAC y normas | Expediente por campaña y lista de comprobaciones | Recinto, práctica declarada, cálculo reproducible, evidencia, norma y enlace a trámite oficial |
| Contactos | Agenda con relaciones | Cliente, proveedor, arrendador, técnico, operario; documentos, trabajos y saldo relacionado |
| Cuaderno y documentos | Diario oficial, informes, papeles, firma y exportación | Mantener el CUE completo y sus reglas de anulación, sin mezclarlo con previsiones económicas |
| Ajustes | Preferencias, permisos y fuentes de datos | Columnas, vistas, categorías, paneles, alertas, conexiones y copias |

La información se organiza por **objeto y tarea**, no por los nombres de las tablas ni por la forma
del trámite. Por ejemplo, al abrir una tierra se ve su mapa y qué tiene este año, y desde allí sus
trabajos y su situación PAC. Un tratamiento sigue pudiendo abrirse en el cuaderno, pero aparece
también en esa tierra y en el calendario sin copiar el registro.

### Ficha de tierra: contrato mínimo

Cabecera con alias breve, referencia SIGPAC/catastral cuando exista, superficie declarada y
superficie SIGPAC **separadas**, titularidad/uso, cultivo de la campaña, estado de los datos y
enlace «ver en mapa». Pestañas: Resumen, Historia, Cultivos, Trabajo, Economía, PAC, Documentos.
Si la tierra llegó sin geometría, mostrar «Falta su forma» y un camino para buscar el recinto;
nunca dibujar un cuadrado supuesto. Si el alias importado contiene cultivo/hectáreas, ofrecer una
**propuesta reversible** de limpieza de nombres antes de escribir en las 64 tierras reales.

### Paneles de mando

Vistas iniciales: **Hoy**, **Tierras**, **Economía**, **PAC**, **Máquinas**. Todos admiten finca,
campaña y filtros claros. Un indicador lleva etiqueta, unidad, período, fuente, fórmula, fecha y
estado `completo/parcial/sin datos`. Nunca sumar kilos con unidades, euros con importes sin moneda,
hectáreas de recintos solapados ni compras con pagos. Ejemplos:

- Tierras: cultivadas/sin declarar, hectáreas por cultivo, labores atrasadas, alertas justificadas.
- Economía: facturas de compra vencidas, cobros vencidos, saldos conciliados, ingresos/gastos por
  campaña, inversiones por separado. Si no se han registrado ventas con precio, ingreso = «sin datos».
- Máquinas: inspecciones próximas y vencidas **solo para equipos a los que se haya determinado que
  aplica**, mantenimiento previsto y documentos faltantes.
- PAC: recintos listos para revisar, conflictos con geometría/SIGPAC, prácticas sin evidencia,
  advertencias por versión normativa, y acceso al trámite. «Listo para revisar» no significa
  «subvención concedida».

Personalización: ordenar y ocultar tarjetas, guardar vistas de tabla, umbrales de aviso **cuando
sean preferencias y no límites legales**, elegir pantalla de inicio. Configuración por usuario,
sin alterar datos compartidos de la finca. Debe existir «Restablecer vista» y una vista sencilla
predeterminada para no convertir la aplicación en un panel ininteligible.

## 4. Modelo de datos nuevo y reglas de integridad

Implementar migraciones aditivas y ensayar sobre **copia** de una base anonimizada; no cambiar
columnas existentes por intuición. Cada registro nuevo incluye `explotacion_id`, autor, fechas de
creación/cambio, auditoría y enlaces explícitos. Las cantidades físicas, dinero y estado legal son
conceptos distintos. Propuesta de entidades (nombres finales a decidir al implementar):

1. `Contacto`: nombre, tipo múltiple, NIF opcional, medios de contacto, dirección, notas,
   consentimiento de comunicaciones si procede. Relaciones `ContactoEnFinca` y referencias desde
   factura, venta, trabajo para terceros y documentos. Evitar duplicados por NIF cuando existe;
   dos personas con igual nombre pueden ser distintas.
2. `Activo`: tractor, remolque, pulverizador u otro; matrícula/ROMA/serie, propiedad, estado,
   adquisición, valor, baja. `ObligacionActivo`/`InspeccionActivo` guardan tipo, fecha, resultado,
   próximo vencimiento, documento y **norma/criterio aplicable**. `Mantenimiento` guarda
   avería/servicio, horas, proveedor y coste documentado. No aplicar ITV a todo lo llamado «máquina».
3. `TrabajoProgramado` y `ParteTrabajo`: tarea, parcela o cliente, fechas previstas/reales,
   operario, máquina, insumos, duración, coste, estado. Vincular un parte realizado al `Labor`,
   tratamiento o abono oficial que lo respalda; no crear dos apuntes oficiales al marcarlo hecho.
4. `DocumentoComercial`: compra, venta o justificante, estado de lectura y confirmación,
   identificador emisor+número+ejercicio, fichero y huella. Extender `Factura` gradualmente, sin
   deshacer los enlaces actuales a `LineaDeFactura` ni el almacén. `Vencimiento` y `PagoCobro`
   admiten pagos parciales, anticipos y devoluciones. Separar fecha de factura, vencimiento,
   fecha de pago y campaña agronómica.
5. `MovimientoEconomico`: ingreso/gasto/inversión/traspaso, importe `Decimal`, moneda, fecha,
   contraparte, categoría, documento, reparto a parcela/campaña/máquina. El origen puede ser
   manual, documento confirmado o banco; deduplicar, no contar tres veces la misma operación.
   Diferenciar devengo, tesorería y coste imputado en cada gráfico.
6. `CuentaFinanciera`, `MovimientoBancario`, `Conciliacion`: identificadores cifrados o reducidos
   para pantalla, origen del fichero/proveedor, fecha valor y operación, importe `Decimal`,
   referencia, estado y coincidencia confirmada. Ningún movimiento bancario crea por sí solo una
   factura ni certifica el gasto fiscal.
7. `ExpedientePAC`, `RecintoDeclarado`, `PracticaPAC`, `ReglaPAC`, `EvaluacionPAC`, `EvidenciaPAC`:
   por campaña, versión de norma y fuente. Guardar qué se declaró, qué consta en SIGPAC, qué se
   observó en el cuaderno y qué eligió el usuario; no sobrescribir una capa con otra.

Claves de unión: `parcela_id` interno estable, referencia SIGPAC con campaña/fecha de consulta y
geometría versionada; no presumir que el recinto oficial de 2026 conserva límites en 2027. En
importaciones, mostrar antes `nuevas/cambiadas/iguales/conflictos`, preservar alias y notas del
agricultor, y permitir deshacer el lote. Relaciones entre fincas siempre validadas en servidor.

## 5. Lectura de documentos, ventas y dinero: contrato verificable

### Facturas de compra

El flujo es **subir → detectar → revisar → confirmar → clasificar → conciliar**. La lectura no
escritora actual (`POST /api/facturas/leer`) debe conservarse. Añadir por campo: texto leído,
ubicación/página, método, propuesta, valor confirmado y si fue corregido. Si no se sabe, vacío;
si OCR y aritmética discrepan, revisión obligada. Comprobar como mínimo emisor/receptor, NIF,
número, fecha, líneas, bases por tipo de IVA, cuotas, total, descuentos, transporte, abonos y
moneda; una cuenta que no cuadra nunca se marca aprobada. Duplicados: huella exacta y
emisor+número+fecha/importes, con opción de inspeccionar ambos.

Corpus de aceptación **anonimizado y consentido**, con al menos PDF digital, escaneo, foto torcida,
varias páginas, varios tipos de IVA, rectificativa, albarán que no es factura, importe negativo,
distintas unidades y dos proveedores con maquetaciones diferentes. Medir extracción por campo
(precisión y omisiones), tiempo de corrección y errores de emparejamiento de producto; no prometer
un porcentaje sin medirlo. Guardar los archivos de ensayo fuera de datos reales y sin NIF visibles.

### Ventas

La `VentaDeCosecha` actual prueba **salida física**, no ingreso. Mantenerla intacta como evidencia
agronómica. Añadir, por separado, documento de venta/ingreso con precio, importe y condiciones,
enlazable a una o varias partidas y a un contacto. Cobro parcial no equivale a factura nueva.
Aceptar venta sin factura inmediata y factura que agrupa varias entregas. Revisar duplicados de
albarán, retornos y ventas anuladas. Comparar cosechado, vendido y existencias solo cuando las
unidades son convertibles y hay lote/origen suficiente.

### Pagos, cobros y bancos

Primera entrega: importar CSV/OFX/CAMT si el banco del usuario los exporta, **con vista previa y
confirmación**, sin contraseñas bancarias. Conciliar sugerencias por importe, fecha y referencia,
con elección humana si hay varias coincidencias. Un pago parcial deja saldo pendiente; un traspaso
entre cuentas propias no es ingreso ni gasto. Reconciliación reversible y auditada.

Segunda entrega, opcional: evaluar un proveedor autorizado de **información sobre cuentas** con
consentimiento explícito, alcance de solo lectura, renovación/revocación, secretos fuera de la base
ordinaria, y desconexión visible. No construir scraping de banca online ni pedir la contraseña
del banco. Validar proveedor y encaje legal antes de integrar; el acceso a cuentas no implica
permiso para iniciar pagos.

## 6. Mapa, tierras y PAC

El mapa de consulta actual usa imágenes PNOA/SIGPAC y una petición por punto; es útil para dar de
alta una tierra. La vista de gestión deberá mostrar **todos los polígonos disponibles** de la
explotación, con selector por lista/mapa, etiqueta legible, cultivo de campaña, superficie,
alertas, estado de carga y fecha de origen. A falta de geometría, poner la tierra en una lista
«sin forma» que lleva a buscarla. No situarla por un centro inventado.

Validaciones geográficas: geometría válida, orden de coordenadas y sistema de referencia,
polígonos con agujeros, multipartes, solapes, área calculada frente a área oficial/declarada,
referencia SIGPAC y año de consulta. La diferencia se muestra; no se corrige en silencio. Debe
haber capas separables de ortofoto, SIGPAC, tierras de la explotación y alertas, con atribución
de las fuentes. Un fallo del servicio externo deja disponible la última geometría guardada con
fecha y aviso de que puede estar desactualizada.

PAC por campaña: importar o transcribir **la solicitud real** y la información disponible del
SIGPAC; preparar la propuesta por recinto con cultivo principal/secundario, superficies, riego,
práctica de ecorrégimen y evidencias (siembra, rotación, cubierta, trabajos, fotos/documentos).
Motor de reglas **versionado por campaña y territorio**, con tabla `norma → artículo → condición →
datos → cálculo → resultado → explicación`. Estados: `cumple según datos conocidos`, `no cumple
según datos conocidos`, `no se puede comprobar`, `requiere criterio administrativo`. Un dato ausente
nunca se interpreta como «no» ni como cumplimiento. Comparación 2025/2026/2027 por recinto y
revisión de cambios SIGPAC. Exportar **informe preparatorio** y enlaces a trámites, no un envío
oficial supuesto.

La Orden/convocatoria anual de Castilla y León, el RD 1048/2022 y sus modificaciones, las BCAM y
las instrucciones de FEGA/Junta se revisan **para cada campaña** antes de activar una regla.
Un ecorrégimen no se resuelve con el texto libre `ParcelaCultivo.ecorregimen`; depende de
superficies agregadas, prácticas y excepciones. Añadir pruebas de casos límite y revisión de
asesor competente. El expediente muestra la versión de norma y la fecha de comprobación.

## 7. Normativa y fuentes: sistema de mantenimiento

Crear un registro de fuentes con URL oficial, organismo, versión/fecha de vigencia, campañas,
territorio, extracto de regla (redactado por el equipo), fecha de consulta y responsable de
revisión. Toda alerta legal enlaza su fuente desde la propia ficha; una regla sin fuente activa
queda como «no se puede comprobar». Las fuentes son **datos versionados**, no constantes escondidas
en la interfaz. Antes de cada campaña PAC se revisan convocatoria autonómica, normas estatales,
criterios FEGA y cartografía aplicable; guardar la versión usada para cada evaluación.

Fuentes oficiales comprobadas al redactar este encargo:

- [RD 1054/2022, art. 9 y anexo II: CUE y contenido](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23054).
- [RD 1048/2022: ayudas directas y prácticas de ecorrégimen](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23048).
- [Solicitud única PAC 2026 de Castilla y León](https://www.tramitacastillayleon.jcyl.es/web/jcyl/AdministracionElectronica/es/Plantilla100Detalle/1251181077932/Ayuda012/1285602207688/Propuesta), que identifica también el trámite de modificación SIGPAC.
- [Manual del visor SIGPAC: consulta de recintos](https://sigpac.mapa.gob.es/fega/visor/help/353Recinto.html) y [descarga de geometrías](https://sigpac.mapa.gob.es/fega/visor/help/3101Geometrias.html).
- [RD 1702/2011, arts. 3 y 5: equipos sujetos a ITEAF y periodicidad](https://www.boe.es/buscar/act.php?id=BOE-A-2011-19296).
- [RD 920/2017, anexo I: ITV de tractores y remolques según clase/edad](https://www.boe.es/buscar/act.php?id=BOE-A-2017-12841).
- [Banco de España: información sobre cuentas y proveedores habilitados](https://clientebancario.bde.es/pcb/es/blog/informacion_cuentas_iniciacion_pagos.html) y [Directiva (UE) 2015/2366](https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32015L2366).

Estas referencias fundamentan **qué comprobar**, no autorizan a codificar hoy un calendario
de inspecciones o una promesa de ayuda sin clasificar cada activo y cada expediente. El sistema
debe permitir registrar la próxima fecha que conste en el certificado y luego contrastarla con
la regla vigente, avisando si discrepan.

## 8. Seguridad, confianza y accesibilidad

- Permisos por finca y función: titular, ayudante, asesor y gestor, con lectura/escritura
  separadas para economía y datos bancarios. Nunca mostrar saldos a quien solo anota labores.
- Copias verificadas y restauración ensayada antes de migraciones; exportación de datos y
  documentos; historial de cambios y anulación. No perder apuntes sin cobertura.
- Datos personales y bancarios mínimos, cifrado de secretos, registro de accesos, caducidad y
  revocación de conexiones. No incluir credenciales, tokens ni NIF reales en pruebas/capturas.
- Navegación por teclado, foco visible, tablas con cabeceras y orden accesible, mensajes con
  palabras además de color; 390, 1024 y 1440 px como mínimos de revisión visual.
- «Lo sé / falta / no puedo comprobarlo» en todas las cifras y estados importantes.

## 9. Entregas para agentes de menor coste

Hacer **una entrega por vez**, con commit o diff revisable, sin abrir todos los módulos a la vez.
Cada entrega incluye mapa de archivos tocados, migración reversible si procede, prueba nueva que
falla antes y pasa después, captura real de escritorio/móvil cuando haya UI, y limitaciones.

| Orden | Entrega y límite | Aceptación concreta |
|---|---|---|
| E0 | Inventario de 29 pantallas y 16 entradas: tarea, datos, botón principal, duplicaciones, regreso y estados vacíos. Cinco recorridos observados con David o, si no está disponible, supuestos explícitos | Documento de problemas priorizados, con captura y ruta por problema; ninguna modificación de sus datos |
| E1 | Nueva navegación y búsqueda global; prototipo de Inicio/Tierras/Compras en desktop y móvil. Stitch puede proponer jerarquía, nunca datos ni textos normativos | Encontrar tierra, factura y trabajo desde inicio en ≤3 acciones; foco/teclado, 390/1024/1440 px; texto en `textos.py` |
| E2 | Ficha única de tierra y vista mapa/lista con las 64 tierras, geometría versionada por campaña | Ninguna tierra desaparece; sin geometría queda visible; no se modifica alias real; SIGPAC y superficie declarada diferenciados |
| E3 | Evaluación de lectura documental con corpus anonimizado, métricas por campo y lista de fallos; **sin cambiar OCR todavía** | Informe reproducible con aciertos/omisiones; comprobar foto real, PDF y caso sin OCR; registrar fuentes de discrepancia |
| E4 | Cola de facturas por revisar, corrección por campo, producto/lote y libro de existencias | Lo leído no se guarda sin confirmar; duplicado no aumenta almacén; 5 L comprados y 2+3 L usados dejan 0 L con origen trazable |
| E5 | Contactos y relaciones con facturas, ventas y trabajos | Alta/corrección/búsqueda; no mezclar contactos de fincas; migrar nombres libres mediante propuesta, sin sobreescribir |
| E6 | Ventas físicas + documento económico + cobros pendientes | Ingreso no se deriva de kilos; parcial/anulado/devuelto bien diferenciados; total en euros trazable al documento |
| E7 | Compras por pagar, gastos e inversiones; reparto por campaña/parcela/máquina; abono y nutrientes por ha | Sumas completas o parciales etiquetadas; composición desconocida no produce NPK inventado; sin doble cómputo |
| E8 | Inventario de máquinas, ITV/ITEAF y mantenimiento | Clasificación previa de equipo, fechas de certificado y regla citada; no alerta ITEAF a remolque por defecto |
| E9 | Calendario, partes, trabajos a terceros y estado de cada tierra derivado de la historia | Rodillo, cultivador y siembra actualizan la ficha en orden; trabajo previsto ≠ realizado; parcela ajena no contamina cuaderno propio |
| E10 | Paneles Hoy/Tierras/Economía/PAC/Máquinas; lluvia estimada y piloto Sentinel con vistas configurables | Cada tarjeta abre su origen; sin precio no muestra ingresos; lluvia y NDVI indican fuente, fecha, resolución y calidad |
| E11 | Importación bancaria manual y conciliación | Vista previa, idempotencia, traspasos excluidos de resultado, deshacer conciliación; sin credenciales bancarias |
| E12 | Expediente PAC anual y motor de reglas con dos prácticas piloto verificadas | Norma versionada, evidencia por recinto, cuatro estados, prueba de excepciones y revisión humana |
| E13 | Ampliar PAC y, solo tras validación externa, estudiar conexión bancaria de lectura | Fuentes de campaña y autorización documentadas; ninguna integración se da por terminada con mocks |

**Puertas de calidad por entrega:** `pytest`, `node --test`, humo con base desechable, `designmd
lint`, revisión de navegador a 390/1024/1440 px y datos densos, accesibilidad de teclado y
comparación con la captura anterior. Si la entrega es solo investigación o documentación, indicar
qué no se ha probado. No usar la base real ni enviar nada a bancos, FEGA o la Junta durante pruebas.

### Encargo reutilizable para un agente

> Lee `AGENTS.md`, `DESIGN.md` y `docs/PLAN_CRM_AGRARIO_2026.md`. Ejecuta **solo la entrega E[n]**.
> Empieza verificando el código y las pruebas existentes de ese recorrido. Entrega un cambio pequeño,
> completo y reversible, con tests, capturas y explicación de los datos que faltan. No toques
> `backend/cuedigital.db` ni secretos. No afirmes cumplimiento legal, dinero cobrado ni geometría
> oficial si la fuente no lo demuestra. Deja por escrito los bloqueos externos con URL y fecha.

## 10. Dependencias que no se pueden fabricar

Para validar completamente las funciones futuras hacen falta, según entrega: facturas y albaranes
reales anonimizados y autorizados para ensayos; ejemplos de ventas y pagos; documentos ITV/ITEAF
de las máquinas concretas; solicitud PAC previa y criterios aplicables a la campaña; y, para
banca automática, elección y consentimiento de un proveedor habilitado. La ausencia de alguno
no bloquea el diseño ni las pantallas vacías honestas, pero sí impide declarar terminada la
verificación de esa integración o de esa regla.
