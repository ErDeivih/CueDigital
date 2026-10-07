# Rediseño del CRM: referencia de v0 y desarrollo con Stitch

Fecha: 07/10/2026. Encargo de David: usar pocos créditos de v0 para decidir la
estructura visual y continuar con Stitch. Este documento prepara implementación;
no acredita que la aplicación instalada haya cambiado ni que sus recorridos estén
verificados. No sustituye CONTRATO_IMPLEMENTACION_CRM.md ni la matriz normativa.

## 1. Material y procedencia

- v0: chat privado `nEYnqUdzxHx`, modelo `v0-mini`, una generación aceptada.
  Consumo declarado por su API: 0,3593494 créditos. La primera solicitud a v1 fue
  rechazada con 422 por un identificador de modelo antiguo; no produjo diseño.
- Código original de referencia: `stitch/crm_20261007/v0_referencia.zip`.
  Es un prototipo Next.js, NO una sustitución del programa ni una dependencia nueva.
- Stitch: proyecto privado `4406163742903972555`. Acceso POST comprobado con HTTP
  200. Un GET con 405 no demuestra que el servicio sea inaccesible.
- Las claves se usan para la petición, no se incluyen en el material entregado.
  Solo se enviaron ejemplos sintéticos; ninguna tierra, factura ni persona real.
- La vista privada de v0 solicita acceso en el navegador sin sesión. Para revisarla
  se preparó una vista local temporal con su código, sin tocar el servidor real.
  Se vio la composición y se comprobó que el menú abre a 712 px y muestra Cuentas.
  Hay capturas `v0_referencia.jpg` y `v0_menu_712.jpg`. Esto no verifica todas sus
  funciones ni la aplicación real. No abrir la privacidad para mostrarlo.

Las capturas `cd-ui/inicio-1440.png`, `tierras-1440.png`, `cuaderno-1440.png` y
`cuentas-1440.png` tienen la misma huella SHA-256 (prefijo `6c7984cf2476ad87`):
son la pantalla de entrada. No acreditan la revisión visual de esas cuatro páginas.
Esto tampoco prueba que el fallo siga en la versión actual: hay que capturar una
sesión autenticada en una base aislada y comprobar el título antes de guardar.

## 2. Dirección visual que se adopta

Una aplicación de gestión reconocible: menú lateral claro, cabecera de contexto,
una acción principal por pantalla, tablas legibles, pendientes que llevan al sitio
donde resolverlos y fichas únicas. El cuaderno se obtiene de los registros; el
usuario no tiene que buscar otra pantalla para escribir de nuevo el mismo hecho.

Mantener el verde principal `#1f4a2c`, fondo `#f4f6f3`, panel blanco, texto
`#10190f` y secundario `#43503f`. Usar los demás colores del DESIGN.md existente
para avisos. No copiar los verdes, grises y amarillos adicionales de v0 sin medir
contraste y actualizar contrato y CSS. Separación por bordes, sin sombras ni degradados.

En despacho: menú de referencia 240 px, cabecera mínima 64 px con altura adaptable,
márgenes 24 px, paneles de borde fino, radios 8 px. Propuesta de cuerpo 16 px
mínimo, títulos 24/20 px, cifras 26 px y controles de 44 px mínimo. Estas medidas
son una PROPUESTA para el modo despacho: antes de aplicarlas, acordar y actualizar
las reglas de DESIGN.md y sus pruebas que hoy fijan otros tamaños. En campo conservar
18 px de cuerpo, botones grandes y las reglas de uso con una mano y sin cobertura.
La preferencia de letra grande también afecta al despacho. Nada de etiquetas de 10 px.

Las dos experiencias usan las mismas entidades y operaciones. No duplicar cuentas,
existencias, trabajos ni formularios para construir otro programa paralelo.

## 3. Armazón y navegación

Menú: Inicio; Campo (Tierras y mapa, Trabajos, Cultivos y PAC, Almacén);
Gestión (Documentos, Cuentas, Personas, Maquinaria); Cuaderno; Normativa; Ajustes.
La agrupación es visual, no introduce pantallas intermedias obligatorias.

Cabecera: explotación, campaña agrícola, búsqueda global, Nuevo apunte y pendientes.
En Cuentas mostrar también el ejercicio económico cuando difiera de la campaña.
Cambiar de finca debe limpiar selección y datos de la finca anterior antes de pintar.
El filtro de campaña no debe esconder silenciosamente documentos sin campaña asignada.

Enlaces permanentes, Atrás/Adelante, recarga y apertura desde otro módulo conservan
identidad y contexto. La miga refleja la pantalla actual; v0 la deja fija en Tierras
y eso se descarta. Login carece de menú de negocio y no deja abrir fichas sin sesión.

Por debajo del ancho que permita tabla y panel, el panel baja o se abre como ficha;
no se comprime la columna Acciones fuera del ancho. A 712 px y en cualquier ancho
intermedio, Menú siempre ofrece todas las secciones, incluidas Cuentas y Normativa.
En móvil, acción de apuntar a mano y navegación compacta. Foco al abrir/cerrar,
Escape solo cierra contenedores seguros; nunca anula un trabajo ni pierde un formulario.

## 4. Familias de pantallas y comportamiento

| Familia | Composición | Acción y evidencia imprescindibles |
|---|---|---|
| Inicio | Resumen de campaña, Para resolver, trabajos próximos, actividad reciente, cuentas conocidas | Cada cifra abre su lista filtrada; fecha de corte y cobertura; permisos en cifras |
| Tierras | Búsqueda/filtros, tabla y mapa sincronizados, detalle de selección | Nombre largo, superficie, cultivo, última labor, pendientes, forma disponible; sin forma permanece en la lista |
| Ficha de tierra | Identidad, referencias, forma real, cultivo de campaña y siguiente trabajo; secciones Historia/Cultivos/Productos y abono/Cosecha y cuentas/Documentos y PAC | Rodillo no borra siembra; lluvia no acredita nascencia; distinguir observado/declarado/estimado |
| Trabajos | Lista y calendario con los mismos filtros; ficha; formulario por tipo | Fecha prevista y realizada distintas; líneas por tierra; revisión de dosis/consumos; guardado único |
| Cultivos y PAC | Histórico y planificación separados; superficies por compromiso; escenarios | Fuente, versión y ámbito de regla; cálculo explicable; falta de dato no es cumplimiento |
| Almacén | Existencia física, lotes, entradas/salidas y documentos | Compra no es recepción; consumo enlaza al trabajo; cantidades y unidades trazables |
| Documentos | Bandeja pendientes/revisados, original al lado del formulario | Lectura propone; confirmación crea; duplicado detectado; fecha, proveedor, líneas, IVA y total revisables |
| Cuentas | Resumen registrado, pestañas Gastos/Ingresos/Cobros y pagos/Extractos; tabla y ficha | Parcial, pendiente, vencido separados; caja no es resultado; un movimiento no se cuenta dos veces |
| Personas | Tabla por relación, ficha única, contacto, trabajos/documentos/cuentas vinculados | Cliente externo distinto de finca propia; datos opcionales y permisos |
| Maquinaria | Tabla y calendario de inspecciones; ficha, documentos e historial | ITV/ITEAF y próxima revisión en equipos, no en tierras; fecha desconocida no es vigente |
| Cuaderno | Campaña, apartados y pendientes reales, revisión/exportación | Vacío no es completo; firmas y anulaciones conservadas; documento descargado verificado |
| Normativa | Biblioteca por obligación, año y ámbito; fuente/artículo/vigencia | Abrir desde el aviso conservando registro; mostrar qué dato falta y qué hacer |
| Ajustes | Explotaciones, usuarios/permisos, vistas y preferencias, fuentes, copia y restauración | Persistencia por usuario; restaurar configuración; no permitir personalizar cálculos legales |

## 5. Contrato de componentes

Construir y probar primero: ArmazonDespacho, CabeceraContexto, MenuModulos,
CabeceraPagina, TarjetaResumen, ListaPendientes, BarraFiltros, TablaGestion,
PanelDetalle, FichaEntidad, FormularioRegistro, VisorDocumento, EstadoDatos y
ReferenciaNormativa. Adaptarlos a React/htm y las piezas actuales sin importar Next.js,
Tailwind, shadcn ni un proceso de compilación por copiar el prototipo.

Tabla: orden por valor real, búsqueda, filtros removibles, columnas, selección,
pie filtrados/total, acción Abrir accesible por teclado. Exportación dice seleccionados,
filtrados o todos. Agregados del servidor sobre el conjunto correspondiente, no sobre
las ocho filas visibles. Identificadores estables; mantener filtros al volver de ficha.

Formulario: dos columnas si cabe; una en móvil. Etiqueta persistente, unidad junto al
campo, obligatorios según operación, sección avanzada plegable que conserva valores.
Revisión previa muestra dónde, cuándo, producto/lote/cantidad y efectos del registro.
Permitir guardar hechos incompletos con pendientes cuando proceda; no inventar para cerrar.

Todos los componentes contemplan: cargando, vacío inicial, sin resultados por filtro,
error, sin permiso, dato desconocido, copia antigua, sin conexión, pendiente de enviar,
conflicto y guardado. Un control visible debe funcionar o explicar su indisponibilidad.
No copiar botones decorativos del prototipo. Textos finales exclusivamente en textos.py.

## 6. Qué se rechaza expresamente del prototipo v0

El CSS devuelto tiene cuerpo 14 px y varias etiquetas de 10–12 px: no se acepta.
La cuadrícula de cuadrados no es un mapa: no se importará como geometría.
Su columna Inspección en parcelas confunde inspecciones de equipos con estado del
cultivo. Falta decir el cultivo no equivale a una tierra sin cultivo: el filtro correcto
es Falta decir el cultivo. Su superficie sintética no valida cuentas reales.
Varias pestañas, filtros, búsqueda, selección de año y botones son decorativos.
La fila pulsable no sustituye a un enlace de apertura manejable por teclado.
La cifra de ocho filas no representa paginación terminada. No aceptar todas las
declaraciones de accesibilidad del generador sin comprobación independiente.

## 7. Orden de implementación para DeepSeek

1. Base aislada con 64 tierras sintéticas, nombres largos, diez sin cultivo dicho,
   tres sin forma, dos campañas con historiales distintos, documentos pendientes,
   pago parcial y una inspección vencida. No modificar la base real.
2. Revisar los PNG de Stitch y el código de v0 con esta lista de rechazos. Acordar
   tokens de despacho en DESIGN.md/CSS/pruebas; no cambiar tamaños de campo al hacerlo.
3. Implementar armazón y navegación completos con login, ancho intermedio y permisos.
4. Implementar Inicio → Tierras → ficha → Registrar trabajo → historial actualizado.
5. Implementar Documentos → propuesta → confirmación → gasto/compra/recepción según
   hecho real; Cuentas → pago parcial → extracto → conciliación sin duplicados.
6. Aplicar las mismas familias al resto de módulos, incluidos estados incompletos,
   normativa contextual y la experiencia móvil. No crear una segunda ficha de entidad.
7. Revisar visualmente cada página autenticada y cerrar recorridos funcionales completos.

Solicitar a Stitch las familias pendientes con el mismo sistema de diseño, el
contrato específico S01–S20 y datos sintéticos. Reutilizar piezas antes de pedir
variantes casi iguales. Si una generación tarda, consultar su estado: no repetir
la petición de creación y cobrar dos veces por un resultado aún en marcha.

## 8. Aceptación medible

Capturas de sesión real de prueba a 390/712/1024/1440 px, con título y datos visibles
distintos por ruta. Comprobar Menú, Cuentas, filtros, ficha, vuelta, formularios,
mapa sin geometría y acciones de tabla. Ninguna captura de login cuenta como esa ruta.
Zoom REAL 200 %, teclado sin ratón, foco y retorno; no simular zoom estrechando solo
la ventana. Contraste medido y texto legible. Mantener los números de documentos
según pruebas medidas: añadir referencias no equivale a añadir funcionalidad.

Facturas: comprobar original y campos corregidos; no crear gasto dos veces al
reenviar. Trabajos: entrada 5 L y consumos 2+3 L dejan 0 L físicamente y una sola
historia; corrección y anulación revierten solo sus efectos. Cuentas: factura
1.000 €, pago 600 €, pendiente 400 €; conciliación no repite ingreso/gasto.
Estas comprobaciones complementan los contratos existentes, no los reemplazan.

Cerrar cada lote con pruebas afectadas y la verificación completa exigida por
AGENTS.md para código; humo y navegador aislados. PostgreSQL o evaluación OCR no
ejecutados se declaran pendientes. No afirmar cero fallos futuros por pasar una suite.

## 9. Goal listo para el implementador

```text
/goal Rehacer la experiencia de CUE Digital como CRM agrario de despacho y campo
siguiendo docs/REDISENO_V0_STITCH_20261007.md, el contrato S01–S20, la matriz normativa,
DESIGN.md y los diseños Stitch referenciados. Primero verifica el estado actual y
prepara base aislada de 64 tierras sintéticas. Entrega armazón y navegación, después
Inicio/Tierras/ficha/trabajo y Documentos/Cuentas, y extiende las mismas piezas a
todos los módulos. Conserva datos reales, firmas, permisos, existencias y trazabilidad.
Usa subagentes para inventario de rutas/contratos, revisión funcional y revisión visual;
asigna un solo escritor por fichero y espera a que termine antes de transferirlo.
Integra en lotes revisables; no copies la tecnología ni los errores del prototipo v0.
Usa Stitch con el mismo sistema para familias faltantes, sin datos reales ni secretos.
Cada control visible funciona, cada número explica su alcance y cada desconocido sigue
siendo desconocido. Verifica recorridos con navegador autenticado, 390/712/1024/1440 px,
zoom real 200 %, teclado, red interrumpida y exportaciones abiertas. Corre las pruebas
del contrato y actualiza seguimiento con evidencia, pendientes y bloqueos concretos.
No declares terminado el CRM porque existan diseños o porque las suites estén verdes.
```

## 10. Resultado de los encargos y revisión visual

Material en `stitch/crm_20261007/`; HTML, explicaciones y encargos originales en
`stitch_material.zip`. Son referencias de diseño, no código de producción.

| Encargo | Resultado | Uso permitido en implementación |
|---|---|---|
| Inicio | Error explícito: servicio temporalmente no disponible | Usar la estructura de v0 y el contrato S01; falta un diseño Stitch terminado |
| Tierras, primera versión | Generada; revisada y descartada por contenido y distribución | `tierras_descartado.png`: evidencia de errores, no modelo a copiar |
| Tierras, corrección | Generada y revisada | `tierras_propuesta.png`: dirección preferida para tabla, filtros y mapa debajo; aún no aprobación de todos los detalles |
| Ficha de tierra | Error explícito: servicio temporalmente no disponible | Falta diseño terminado; implementar el contrato S03 con las piezas compartidas |
| Revisar factura | Generada con original y revisión en paralelo | `documentos_borrador.png`: conservar composición; rechazar textos inventados |
| Campo, registrar trabajo | Generada | `campo_borrador.png`: conservar pasos y controles grandes; rechazar textos inventados |

El sistema automático creado por Stitch, `assets/30f0b60d129c485a9378305cc34702d2`,
se llamó AgroCUE Enterprise e introdujo una supuesta autoridad institucional que
no pedimos. Esa es una contaminación de diseño, no una fuente legal. Se intentó
actualizarlo con las reglas revisadas; el servicio rechazó la actualización con
«Request contains an invalid argument», incluso tras consultar su esquema.
NO reutilizar ese sistema como contrato aceptado. Para futuras generaciones crear
un sistema limpio desde el DESIGN.md revisado y comprobar sus instrucciones antes
de generar; conservar el identificador anterior solo como trazabilidad.

Errores concretos de los borradores: conexiones SIEX/REGEPA inexistentes, «51 listas
PAC/SIEX», «trazabilidad garantizada», «78 % de certeza» sin evaluación, identificación
profesional inventada, bloqueo de abonos no fundamentado y «almacenamiento seguro
garantizado en memoria del tractor». Nada de eso entra en la aplicación.

En la propuesta corregida de Tierras, la tabla ya deja ver Ver y nombres largos;
el filtro es removible y el mapa se declara ficticio. Falta ajustar el selector de
finca/campaña para que no se monte con la franja superior; mantener Cultivos y PAC
en el menú; revisar textos de las tarjetas y eliminar cualquier sombra que el HTML
haya añadido. La ficha de ejemplo y sus importes/superficies siguen siendo sintéticos.

Verificación local de esta entrega: 4.537 casos Python recogidos, **4.536 pasan y
1 omitido**; **1.048 JavaScript pasan**. El documento nuevo añade dos comprobaciones
de integridad de texto y explica el cambio de recuento. No se modificó código de la
aplicación, DESIGN.md ni CSS. No se repitieron humo ni recorrido completo del servidor:
esta entrega no acredita una nueva versión funcional del CRM. La base real no se abrió
ni migró. La vista temporal de referencia se para al terminar la revisión.
