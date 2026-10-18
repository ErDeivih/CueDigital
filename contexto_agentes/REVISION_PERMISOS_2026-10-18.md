# Permisos: revisión independiente y estabilización

Fecha: 18/10/2026. Destino F:\EspacioCodigo\CueDigital.
HEAD observado: 949c595. 59 ficheros modificados y 56 sin seguimiento: 115 rutas de fichero
pendientes en total, no 115 funciones verificadas. El agente declara pérdida y reconstrucción
de modelos por un checkout; esta revisión no acredita la reconstrucción completa.
No se ha editado código del CRM ni ejecutado migraciones sobre la base real.

## P1: el panel expone dinero sin permiso económico — reproducido

`backend/app/routers/panel_api.py`, función `el_panel`, recibe ExplotacionActual y Db,
pero no comprueba puede_ver_lo_economico. Construye la métrica gastos y su valor.

Reproducción contra TestClient real y base temporal de las fixtures:
1. Crear campaña actual, contacto y gasto de 123.45 EUR en esa campaña.
2. Poner AccesoAFinca.puede_ver_lo_economico=False mediante el ayudante de pruebas existente.
3. GET /api/contactos/{id}/saldo: 403. Confirma que la restricción está activa.
4. GET /api/panel: 200, las_metricas contiene gastos con valor=123.45 y unidad=EUR.

No basta con ocultarlo en Inicio: el dinero ya viaja por la red. Filtrar en servidor las
métricas económicas para conservar el panel agronómico, o proteger la ruta completa si
ese es el contrato elegido. No sustituir el dinero prohibido por cero ni dejarlo en
subtotales, cobertura, enlaces o respuestas alternativas.
Agregar regresión con importe conocido, no solo panel vacío; titular autorizado lo ve,
cuenta sin capacidad no lo recibe y otra explotación no puede consultarlo.

## P2: la cobertura de botones por sufijos es incompleta — demostrado

`componentes.js`: ACCIONES_QUE_ESCRIBEN es guardar/anular/quitar/borrar/subir/emitir.
El clasificador REAL escribeEstaAccion devuelve false para:
- contacto-borrar-si
- fusion-hacer
- contacto-nota
- contacto-baja
- banco-deshacer
- bandeja-confirmar

Ejemplos confirmados en los manejadores:
- contacto-borrar-si llama borrarElContacto, que hace DELETE /api/contactos/{id}.
- fusion-hacer hace POST /api/contactos/{origen}/fusion/{destino} directamente.
- fusion-deshacer también hace POST.

El informe que dice que contacto-borrar-si y fusion-hacer no escriben es incorrecto.
Una confirmación puede ser precisamente la operación destructiva.
Renderizado el componente REAL de fusión con ponerSiSePuedeEscribir(false) y vista previa
válida: el HTML sigue conteniendo data-accion="fusion-hacer". La regla CSS tampoco
incluye ese nombre. Esto acredita un defecto de interfaz, no prueba por sí solo que el
servidor permita fusionar o borrar sin capacidad.

Los guardianes no son una garantía universal: descubren candidatos usando sufijos y
después comparan listas de sufijos. Una acción fuera de ese vocabulario queda fuera de
la comprobación. Las 14 pruebas pasan con el defecto presente.

Solución: inventario de acciones por el efecto real y capacidad requerida. Usar metadatos
explícitos compartidos para preparar los controles; cubrir también botones HTML y
confirmaciones. Desconocido es pendiente de clasificar, no «seguro que consulta».
Mantener controles de servidor como autoridad. No añadir infinitos sufijos sin revisar
los manejadores: «nuevo» puede abrir un formulario, «deshacer» puede escribir y «sacar»
puede exportar o retirar existencias según el contexto.

Pruebas de comportamiento: cuenta de consulta, abrir fichas y confirmaciones por URL,
no ofrecer escrituras; llamada directa al servidor devuelve 403 y no cambia datos.
Titular conserva las operaciones. Usuario sin dinero conserva consulta agronómica.

## Permiso desconocido

loQuePuedoHacer retorna modificar/economico=true antes de cargar capacidades;
ponerSiSePuedeEscribir(undefined) permite escribir. Es un diseño permisivo de UI.
No se ha reproducido una fuga transitoria por ese camino. Revisar cambio de cuenta/finca,
sesión expirada y permisos aún cargando: usar un estado explícito pendiente y no heredar
capacidades de la cuenta anterior. Probar esos escenarios antes de declarar cierre.

## Qué se verificó y qué no

- 14/14 pruebas JavaScript de permisos pasan, pese al hueco descrito.
- test_los_permisos_por_materia.py + test_el_panel.py + test_el_paquete_de_la_pac.py:
  ejecución terminada con salida 0.
- Reproducciones adicionales en memoria, sin crear ficheros de pruebas en el destino:
  clasificador real, renderizado React real y llamada a API con permiso económico quitado.
- No se han repetido suite completa, navegador real, ni todos los módulos reconstruidos.
- Huella real conservada:
  CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12.

## Orden de recuperación y continuación

1. Congelar nuevas funcionalidades. Guardar una copia recuperable completa de código
   pendiente y ficheros nuevos fuera del destino. Validar que incluye models.py,
   lecturas, reservas y nutrientes; un patch de tracked files no incluye los nuevos.
   No git checkout/reset/clean sobre el trabajo pendiente.
2. Corregir la exposición económica de /api/panel con regresión real.
3. Sustituir la falsa cobertura universal por clasificación explícita de acciones;
   cubrir fusión, borrado confirmado, notas, tareas, reservas, conciliaciones y deshacer.
4. Revisar los modelos reconstruidos contra esquemas, rutas, cálculos y migración:
   columnas, nulabilidad, defaults, relaciones, claves e índices. Ensayo sobre copia
   de un esquema anterior; no declarar reconstrucción exacta usando solo suite verde.
5. Comprobar los 24 casos de reenvío por contrato: índice no basta. Identidad original,
   datos distintos, correcciones posteriores, simultaneidad y relaciones hijas.
   reenvios.py omite campos que no existen como columna: cada puerta debe acreditar
   los datos compuestos (insumos, repartos, etc.) que el ayudante no compara.
6. Recorridos de titular, consulta y ayudante sin dinero; luego checks de AGENTS sobre
   una revisión estable. Cerrar la integración en commits revisables; no acumular
   otra jornada entera de trabajo funcional sin control de versiones.
7. Retomar recorrido pendiente de superficies y verificaciones visuales con capturas.
8. PAC en navegación del escritorio, manteniendo las acciones móviles previstas.
   El encargo ya incluye PAC: no bloquear todo el trabajo por el número antiguo de
   botones de Inicio. Registrar la decisión de navegación en el contrato.
   Investigar fuentes públicas oficiales por campaña/ámbito/versión. Si una regla no
   tiene fuente suficiente, marcarla pendiente sin afirmar elegibilidad. No declarar
   toda la investigación legal bloqueada porque David no haya aportado un documento.

No matar Chrome por nombre ni tocar sesiones ajenas. Procesos solo del perfil/PID de
pruebas creado y registrado por el agente. No generar más infraestructura para tapar
fallos del producto. Dos intentos sin evidencia nueva: reproducción mínima y revisión.
El nuevo objetivo debe ser estabilización con criterios de cierre, después continuidad;
no una cadena indefinida de guardianes sobre cadenas de texto.

## Revisión posterior de la entrega — HEAD 42928fa

El trabajo ya está consolidado en estabilizacion-2026-10-18 y el árbol está limpio.
Se confirma el filtrado económico de /api/panel y la sustitución de los sufijos por un
inventario explícito. Ejecutadas las pruebas del panel sin dinero, denegación del servidor,
compuestos, insumos y reenvío de reservas: 22 pruebas, salida 0. Las cinco pruebas JS de
permisos pasan. No se han repetido la suite completa ni el recorrido de Chrome.
Base real con la huella anterior. No se ha editado el código del destino.

### El recorrido de roles todavía no acredita lo anunciado

verificar_el_recorrido_sin_dinero.py abre únicamente la raíz/Inicio; recoge su HTML y
comprueba que no aparecen siete acciones de contactos, fusión, banco y bandeja.
No visita las pantallas que contienen esas acciones. Esa ausencia no prueba el filtrado:
las siete pueden faltar también en el Inicio del titular.

Además, AYUDANTE tiene puede_modificar=True y puede_ver_lo_economico=False. No debería
usarse su falta de botones de escritura como prueba de consulta: son capacidades distintas.
La cuenta de consulta requiere modificar=False. No hay que añadir una puerta de producto
para poder probarla: una fixture de servidor aislado puede preparar el acceso y después
el navegador ejercita la aplicación real con su sesión.

Completar el recorrido, sin repetir el rescate:
- Afirmar explícitamente los permisos de cada cuenta desde /api/cuenta/yo.
- Titular: abrir el contexto donde existe cada acción y comprobar que puede usarla.
- Consulta: abrir esos mismos contextos y confirmaciones por URL; no ofrecer escritura;
  llamada directa denegada y datos intactos.
- Ayudante sin dinero: permitir las escrituras agronómicas autorizadas y no recibir
  importes en Inicio, documentos, fichas o respuestas económicas restringidas.
- Probar cambiar entre cuentas y fincas en el mismo navegador, incluida carga de capacidades.
- Comprobar visibilidad y foco: hidden permanece en el HTML; no usar únicamente ausencia
  de data-accion para evaluar controles ocultados mediante DOM.
- Esperar IDs y datos del contexto concreto; no una pantalla ajena ni solo un título global.

### Migraciones: alcance concreto, no todo o nada

Las pruebas citadas sí ensayan cambios sobre copias: columnas antiguas de fertilizantes
y un índice ausente de lecturas. Eso acredita esos caminos concretos. No es equivalente
a una migración integral de toda la instalación anterior con filas relacionadas, adjuntos,
duplicados históricos, reintento e interrupción. No decir que no hay ensayos, ni que esos
dos ensayos garantizan todas las migraciones de los modelos reconstruidos.

No reescribir los ocho commits por estética de fin de línea. Conservar la rama y cerrar
estos límites con verificaciones concretas; después continuar superficies y PAC.
