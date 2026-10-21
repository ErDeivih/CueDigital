# Cola de implementación del CRM y estudio de referencias

> **Prioridad del encargo del 19/10/2026:** la aplicación YA está en el repositorio
> `ErDeivih/CueDigital`, checkout cloud `/workspace/CueDigital`.
> Leer primero `docs/ENCARGO_DEEPSEEK_2026-10-19.md` y `docs/REVISION_PRODUCTO_2026-10-19.md`.
> Sus cortes D01–D08 mapean a los CRM existentes: empezar por aislamiento de la cola (CRM-08)
> e identidad/evaluación PAC (CRM-09), antes de ampliar funciones o declarar el producto vendible.
> **Actualización 21/10:** usar `integracion/cloud-estabilizacion-2026-10-21`; incluye los diez commits
> Windows hasta `8392f4d` y la entrega cloud. No hace falta el ZIP ni aplicar su parche otra vez.
> D01 es cola, D02 PAC y D03 fallos/recuperación. D01 sigue abierto por las reproducciones nuevas
> del cierre del informe; leerlas antes de declararlo resuelto. Continuar desde el checkout existente,
> tanto en Windows como en cloud, conservando cualquier trabajo pendiente.

Fecha: 11/10/2026. Los IDs CRM son entregas de continuidad, no sustituyen T01-T24 ni E0-E13.
Actualizar el contrato del destino al cerrar. Contratos aquí descritos son propuestas ejecutables,
no funciones acreditadas ni validaciones legales.

## Orden y dependencias

| Ticket | Entrega | Contrato existente | Depende de |
|---|---|---|---|
| CRM-00 | Cierre visual y estado de compras | S11 / T08-T09 | Entrega actual |
| CRM-01 | Ventas, entregas, factura y cobros | S12 / T12 | CRM-00 |
| CRM-02 | Extracto y dinero sin duplicar | S14 / T20 | CRM-01 |
| CRM-03 | Contactos y seguimiento | S15 / T11 | CRM-01; puede preceder CRM-02 |
| CRM-04 | Servicios a terceros | S17 / T16 | CRM-01, CRM-03 |
| CRM-05 | Costes, inversiones y panel económico | S13 / T13,T19 | CRM-01, CRM-02 |
| CRM-06 | Tierra, mapa e historia de campañas | S02-S06 / T05,T06,T15 | Núcleo actual; independiente de banco |
| CRM-07 | Insumos, semillas, abonos y maquinaria | S08,S09,S16 / T09,T10,T14 | CRM-06 y compra actual |
| CRM-08 | Fiabilidad: borradores, permisos, conflictos, recuperación | S20 / A12-A14 | Se aplica transversalmente; piloto tras CRM-00 |
| CRM-09 | Planificación PAC y paquete preparatorio | S07 / T21-T23 | CRM-06, CRM-07; fuentes revisadas |
| CRM-10 | Meteo, observaciones y satélite piloto | S18 / T17,T18 | CRM-06; fuente disponible |
| CRM-11 | Paneles integrados y personalización | Cinco paneles / T19 | Datos acreditados de sus módulos |
| CRM-12 | Lectura de papeles evaluada | S10 / T07,T08 | Corpus autorizado; no bloquea entrada manual |

No desplegar nuevas dependencias o pagar servicios para desbloquear una fila. Primero alternativas
disponibles y recorrido manual. PostgreSQL tiene ticket de compatibilidad transversal: si no hay entorno,
registrar límite y continuar SQLite sin prometer equivalencia.

## CRM-00: cierre pequeño, no otra investigación interminable

- Barra: controles totalmente dentro de viewport y de cualquier ancestro que recorte. Verificar el
  rectángulo completo, nombre legible, foco visible y activación. Un rectángulo con ancho positivo
  fuera de la pantalla no es visible. Considerar zoom y scrollbars, no asumir ancho útil = ventana.
- Capturas a 390, 1024 y 1440; el guion debe decir innerWidth y tamaño real de imagen.
- Resumen del contrato: 4746/1081 aportados, no 4736/1080 en la tabla actual. Obtener cifra real
  si se añaden ficheros: los guardianes parametrizados también suman casos.
- Migración: caso legado corregido antes de tener huella; explicitar que el original es desconocido.
  No deducir automáticamente una huella original de una versión ya editada.
- Revisar sin ampliar alcance el cambio de clave de papel ante variaciones de total y proveedor.
  Identidad del documento no es solo igualdad de importe. Incluir mismo emisor/número/año con total
  corregido, y datos incompletos. Documentar el tratamiento de conflicto comercial.
- Compatibilidad PostgreSQL: revisar booleanos, índices y conflictos. Ensayo separado si disponible.

Aceptación: acciones completas accesibles en la barra y capturas vistas por un revisor con visión;
pruebas nuevas fallan antes de los arreglos; tabla actual coherente. El recorrido de compra no se rehace.

## CRM-01: ventas y cobros

Inventariar `VentaDeCosecha`, `FacturaEmitida`, `Cobro` y aplicaciones existentes antes de crear entidades.
Estudiar Payment Entry de ERPNext para el reparto y Odoo para enlaces; usar lo observado/documentado,
no adoptar automáticamente su contabilidad o su normativa fiscal.

Flujo: cosecha/lote -> entrega -> venta -> documento comercial -> cobros aplicados.
Separar kilos entregados, kilos aceptados y ajustes justificados; precio sin conocer no es 0.
Precio, descuentos e impuestos conocidos con Decimal. Venta, factura y cobro no son tres ingresos.
Conservar original, revisiones, devoluciones y motivo. Una entrega puede facturarse más tarde o agruparse.
Definir fecha de cosecha, entrega, documento, vencimiento y cobro; campaña distinta de año del banco.

Pantallas: tabla con cliente, fecha, producto/cantidad/unidad, importe conocido, cobrado, pendiente y estado;
ficha única con resumen, entregas, documentos, cobros y auditoría. Acciones: añadir entrega, registrar
precio, aplicar cobro, corregir/anular según estado. Reutilizar componentes de compra, no copiar cálculos.

Aceptaciones:
- Venta de 1210 EUR: cobro 400 -> pendiente 810; cobro 810 -> 0 por ID, otras ventas intactas.
- Un cobro de 350 aplicado a dos deudas 100/250, aplicaciones suman 350 y saldo sin aplicar 0.
- Cobro de 400 con 350 aplicado: 50 sin asignar, no pago perdido ni ingreso nuevo.
- 8000 kg con precio desconocido: cantidad conocida, importe y margen incompletos.
- Devolución documentada conserva historia y ajuste de cantidad/importe; no editar originales firmados.
- Reenvío antes/después de corregir/anular; concurrencia; un resultado y efectos una vez.
- Recarga, volver con filtros y aislamiento entre fincas. Importes españoles en listas, fichas y documentos.

Emisión fiscal automatizada requiere contrato y fuentes oficiales propios antes de activarse;
si no se acreditan, entregar registro comercial y documentos claramente identificados sin promesa fiscal.

## CRM-02: banco por fichero y conciliación reversible

Inventariar CuentaBancaria, MovimientoDeExtracto, ConciliacionDeMovimiento, pagos y cobros.
Referencia: documentación de conciliación Odoo/ERPNext; demo solo si pública y con datos ficticios.
Primero un formato existente. No añadir PSD2 ni pedir credenciales bancarias para completar el flujo.

Importación: perfil de columnas, fecha operación/valor, signo, moneda, referencia y saldo si existe;
vista previa aceptadas/rechazadas/duplicadas y errores por fila sin destruir el original.
La misma fecha+importe no identifica unívocamente una operación: dos pagos iguales pueden ser reales.
Guardar huella del lote y estrategia de identidad por formato; resolver periodos solapados.

UI dividida: movimientos sin conciliar y candidatos de documentos/pagos. Antes de confirmar mostrar
aplicaciones, resto, contraparte y discrepancias. Propuesta automática no es confirmación silenciosa.
Deshacer conserva extracto y libera aplicaciones. Un movimiento ligado a un pago ya registrado
no crea otra salida de dinero. Traspaso propio no es ingreso/gasto operativo; comisión separada.

Aceptación: fichero repetido y solapado no duplican; dos operaciones iguales legítimas se conservan;
movimiento 1210 -> documentos 400+810; documento pagado en dos movimientos; 500 entre cuentas propias
no altera ingresos/gastos; desconciliar y reconciliar deja los mismos saldos; moneda distinta no se suma
sin conversión acreditada; no se enlaza una deuda de otra explotación.

## CRM-03: contactos y próximas acciones

Ficha de persona/empresa con roles múltiples, NIF opcional, canales, direcciones, notas con autor,
trabajos, documentos y saldos relacionados. Nombre histórico de documentos conservado al renombrar.
Homónimos no se fusionan por nombre; propuesta de duplicado y fusión solo confirmada, con auditoría.
Actividad y tarea próxima con fecha/responsable; finalizada, vencida y sin fecha diferenciadas.
Privacidad por permiso: ocultar dinero también lo elimina de la respuesta.

Referencia: patrón de ficha/actividad de CRM documentado en Odoo o Frappe, no campañas de marketing.
Aceptación: proveedor que también es cliente; dos homónimos; cambio de razón social;
saldo abre sus registros; contacto inactivo conserva relaciones; notas visibles solo donde corresponden.

## CRM-04: servicios a terceros

Cliente -> propuesta de trabajo -> aceptación -> parte realizado -> venta/documento -> cobro.
Trabajo externo con ubicación y superficie separadas de tierras/PAC propias.
Insumo del cliente no descuenta almacén propio; insumo propio sí. Máquina, horas, operario, tarifa,
desplazamiento y coste conocido por separado. Cambiar tarifa no reescribe partes aceptados anteriores.
Aceptación: trabajo externo 10 ha no suma superficie propia; 2 L propios consumen; 2 L del cliente no;
plan no consume; ejecución repetida no duplica; cobro parcial exacto; margen marca costes desconocidos.

## CRM-05: costes, inversiones y economía

Definir con el modelo actual cuál es el origen único de cada coste y cada ingreso. No sumar factura,
gasto derivado y banco como tres gastos. Compra almacenada, consumo, coste imputado y pago separados.
Coste por tierra/cultivo/máquina con método confirmado (área, horas, consumo o manual).
100 EUR en tres destinos: suma exacta con residual, reparto visible y reversible sin dinero duplicado.
Reparto de varias campañas explícito; fecha bancaria no cambia campaña agronómica.
Activo/inversión separado del gasto del cultivo; amortización solo con parámetros confirmados.
Ayuda prevista, concedida y cobrada separadas, no sumarlas entre sí.

Panel: registrado, pagado/cobrado, pendiente/vencido, costes sin asignar, inversiones y margen conocido.
Cada tarjeta abre lista con mismos filtros, fecha de corte y cobertura. Sobrepago es saldo a favor,
no deuda negativa sin explicación. Vencido por cuota/fecha pactada, no por fecha de factura.
Aceptación: suma de repartos=importe; paginar no cambia tarjeta; sin precio no hay ingreso cero;
cuenta 500 transferidos no aumenta margen; comparar campañas declara áreas y cobertura distintas.

## CRM-06: tierras, mapas y campañas

Referencias: farmOS (modelo de activos/registros), AGRIVI (funciones anunciadas), observación de mapas
en demo pública disponible. No inventar que hemos comprobado su motor ni copiar geometrías privadas.
Tabla/mapa sincronizados, filtros en URL, selección por ID, leyenda y capa/fuente/fecha.
Ficha única: resumen, historia, cultivos, trabajos, economía, documentos y PAC.
Forma desconocida en lista aparte con acción para completarla; nunca cuadrado supuesto.
Superficies declaradas, oficiales y trabajadas separadas. Cultivo por campaña y geometría versionada.

Aceptación: 64 tierras y diez filtradas -> 10/64 en tabla y selección coherente en mapa;
polígono con agujero/trozos y coordenadas válidas; elegir tierra abre misma ficha; trabajo realizado
actualiza historia y último hecho, plan no; rodillo después de siembra conserva cultivo y ambos eventos;
cambio de campaña no altera años previos; formas solapadas no duplican superficie única sin advertencia.
Vista móvil muestra tarea/ubicación útil sin forzar una tabla de escritorio estrecha.

## CRM-07: insumos y máquinas

Producto, autorización de uso y lote son distintos. Fotos de etiqueta/justificante como evidencia,
OCR propone, usuario confirma. Mantener registro oficial, marca, formulación, lote, caducidad,
cantidad/unidad y autorización vigente/histórica cuando esté comprobada.
Semilla: especie, variedad, categoría y evidencia, comprada/propia; no certificada por defecto.
Abono: composición con unidades, producto aplicado y nutrientes calculados separados; no asumir 0.

Aceptación: compra 5 L -> aplicar 2 y 3 en dos tierras -> 0; anular 2 -> 2;
2 L en 4 ha -> 0,5 L/ha, sin área -> desconocido; 600 kg en 3 ha con N 15 % acreditado
-> 200 kg/ha y 30 kg N/ha; P desconocido si falta. Cambio de etiqueta no cambia apunte firmado.
Reserva para planificar no es consumo. Unidades incompatibles no se convierten sin equivalencia acreditada.

Máquinas: ITV, ITEAF, mantenimiento, seguro y ROMA separados, aplicabilidad con evidencia y fecha.
Aviso vencido al planificar; fecha desconocida no significa vigente. Reparación enlaza gasto y taller.
Caso tractor/remolque/equipo de aplicación; avería -> reparación -> documento -> gasto -> pago;
horas acumuladas y próxima revisión solo con datos confirmados.

## CRM-08: fiabilidad transversal

Piloto en formulario de trabajo y factura: borrador por usuario/finca, guardar local, cierre/reapertura,
respuesta perdida, cola al reconectar, reintento después de anular y conflicto de dos pestañas.
Referencia de borradores: observar producto que lo resuelva; Obsidian es candidato, no comportamiento
equivalente demostrado. No trasladar CTRL+Z a una anulación legal ni deshacer una firma con una tecla.

Permisos: propietario, colaborador y consulta según modelo disponible, con matriz por acción y dato.
Servidor, adjuntos y exportaciones verifican aislamiento, también por enlace directo.
Edición concurrente: versión esperada y resolución explícita; no último escritor silencioso.
Restauración: base+adjuntos+configuración necesaria, ensayo sobre destino nuevo, integridad y referencias,
comprobación de firmas y apertura de documentos; nunca restaurar sobre la base real en las pruebas.
PostgreSQL, si soportado: mismas aceptaciones esenciales y migraciones, sin trasladar SQL SQLite a ciegas.

## CRM-09: preparación PAC

Campaña -> compromisos elegidos -> recintos -> cultivos principales/secundarios -> evidencias -> evaluación.
Fuente legal por ámbito/año/fecha de vigencia y versión. Consultar BOE, FEGA, MAPA, Junta y BOCyL al
implementar reglas; ninguna competencia autoriza usar su interpretación como norma.
Primero una práctica piloto con cálculos reproducibles, umbrales, exclusiones y datos pendientes.
Porcentajes con numerador/denominador; tierra sin cultivo no desaparece para pintar verde.
Escenario siguiente año separado de lo declarado y de lo realizado. Comparar alternativas sin consumir.
Paquete preparatorio por recinto: referencias, superficie, cultivos, práctica, documentos y cuestiones
pendientes. No envío directo ni garantía de elegibilidad.
Aceptación: fuente de otra campaña/comunidad no se aplica; falta área/cultivo/evidencia -> incompleto;
editar escenario no cambia historial; exportación coincide con detalle y conserva versión evaluada.

## CRM-10: meteo y satélite

Piloto en tres tierras antes de 64. Fuente elegida con licencia, resolución, cobertura, fecha y coste.
Lluvia observada, estimada y predicción separadas; intervalos de acumulación y datos ausentes visibles.
Siembra + lluvia puede sugerir revisar, no declarar nascencia ni humedad real sin evidencia.
Sequía meteorológica y condición del cultivo distintas. Observaciones manuales con autor/fecha/foto.
Satélite: adquisición, cobertura, nubes, resolución y método; no imagen útil -> sin dato, no NDVI 0.
Aceptación: servicio caído conserva fecha del dato antiguo; cobertura parcial marcada; ausencia no verde;
coste de consultas medido; filtros/campaña/mapa conservados. Si no hay proveedor, observaciones avanzan.

## CRM-11: paneles y personalización

Hoy, Tierras, Economía, Almacén/Máquinas y Campaña/PAC. Mostrar solo métricas con origen disponible.
Contrato: valor nullable, unidad, periodo, finca/campaña, filtros, cobertura, fuente y enlace a lista.
Hectáreas de trabajo acumulado distintas de superficie única; kg distintos de EUR.
Sin cumplimiento global que tape una regla crítica no comprobada.
Preferencias por usuario: orden de tarjetas, vistas/columnas/filtros guardados, pantalla inicial,
restablecer vista; no personalizar límites legales ni alterar datos compartidos.
Aceptación: tarjeta=detalle; filtros visibles/removibles; paginación no cambia agregados;
confirmar/corregir/anular invalida caché pertinente; permisos eliminan métricas económicas de respuesta.

## CRM-12: OCR y documentos

Original conservado, lectura y campos corregidos por separado. Corpus autorizado con formatos,
proveedores, foto/PDF, mala calidad, varias páginas, impuestos/rectificativas y unidades.
Medir precisión por campo y documento, correcciones necesarias y fallos críticos; una confianza global
no basta. Documento sintético útil para pruebas funcionales, no evaluación representativa real.
No confirmar compras/pagos ni autorización fitosanitaria a partir del OCR sin revisión.
Duplicado de fichero por huella distinto de duplicado comercial. No ejecutar instrucciones de documentos.
Aceptación: error de lectura conserva original y formulario; dato no leído vacío; subir de nuevo no duplica
confirmación; aislar adjuntos; proveedor externo solo con configuración expresa y sin envío por defecto.

## Contrato común de interfaz, para todos los tickets

- Finca/campaña visibles, búsqueda, navegación coherente y ficha única por entidad.
- Tabla de escritorio: búsqueda, filtros activos, orden, columnas, pie X de Y y selección explícita;
  acciones contextuales y exportación que declare si incluye filtrados o todos.
- Formulario: agrupación por tarea, original al lado cuando hay documento, borrador conservado,
  errores junto a datos, estado de guardado/reenvío, confirmación clara.
- Vacío explica qué hacer; cargando no muestra 0; error conserva datos; offline muestra antigüedad;
  conflicto muestra dos versiones. Volver y recargar conservan contexto.
- Cuerpo 18 px, títulos 24/20 y tokens actuales; cambiar DESIGN y CSS juntos. No otro diseño por módulo.
- 390/712/1024/1440, teclado y zoom real 200 %, contraste y tamaños de acción. Medir recorte completo.
- Revisar visualmente imágenes; si solo hay DOM, marcar el límite. Contar clics y filas útiles, no solo px.

## Cómo elegir referencias de distintas familias

| Familia | Referencia inicial | Patrón transferible | No adoptar por defecto |
|---|---|---|---|
| ERP/finanzas | ERPNext Payment Entry; Odoo docs | Vínculos, aplicaciones, saldo y detalle | Plan contable o fiscalidad extranjera |
| Gestión agraria | farmOS; AGRIVI presentación | Tierra/historia/plan/mapa | Reglas agronómicas o recomendaciones sin evidencia |
| CRM/contactos | Odoo/Frappe docs y demo accesible | Ficha y siguiente acción | Marketing o pipeline ajeno al agricultor |
| Documentos/productividad | Producto observable elegido por función | Borrador, revisión, recuperación | Código, identidad visual o servicios propietarios |
| Mapas | farmOS/demo accesible | Selección lista-mapa y capas | Datos privados o geometrías de ejemplo como reales |
| BI/gestión | Paneles documentados Odoo/ERPNext | Del número al registro, cobertura | Totales o gráficos sin datos propios |

Fuentes concretas y nivel de evidencia en VERIFICACION. Añadir referencias solo al verificar su utilidad.
No hay obligación de usar REA para todas las familias. Registrar lo observado, lo descartado y el criterio
medible del destino. «Todas las competencias» significa cubrir las tareas agrarias aprobadas, no clonar
todo lo que ofrecen aplicaciones de otros sectores.
