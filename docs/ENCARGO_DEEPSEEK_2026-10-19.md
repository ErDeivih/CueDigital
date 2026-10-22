# Encargo de continuidad para DeepSeek — CUE Digital

Fecha: 19/10/2026. Objetivo: cerrar fiabilidad y experiencia para un piloto comercial verificable.

## Prioridad vigente tras revisión independiente — 22/10/2026

**Un solo agente ejecutor**, sobre la misma rama integrada y conservando trabajo posterior.
La entrega `99e0873` está incorporada. No repetir sus 54 rondas ni buscar el ZIP.
Los estados de la entrega del implementador no sustituyen esta revisión.

1. **D01, P0: respuestas que llegan tras cambiar de cuenta.** Los cinco casos de cola anteriores
   pasan ahora. Se reprodujeron otros dos con promesas controladas: A inicia POST; entra B;
   la respuesta 200 de A termina guardando `cuedigital.ultimo.2:2` con datos de A. Y un 422
   del vaciado de A termina en `cuedigital.rechazados.2:2`. Capturar también las claves de
   persistencia antes del primer await; no derivarlas de la sesión actual al terminar.
   Actualizar el estado visible solo si sigue perteneciendo al contexto de origen. Probar
   éxito, rechazo, almacenamiento fallido, cambio de finca y retorno posterior del dueño.
   Ver evidencias en `docs/revision-2026-10-19/reproducciones.txt`.
   **Concurrencia local también reproducida:** dos procesadores de la misma cuenta/instalación
   reciben ambos `turno: true`: el dueño del lease es compartido y se considera reentrante.
   Una intercalación controlada de dos `apuntar` deja solo un pendiente porque ambos reescriben
   el array leído. Usar identidad de procesador/pestaña y persistencia transaccional o coordinación
   que conserve ambas intenciones. Probar dos escrituras intercaladas, reinicio y caducidad;
   desduplicar en servidor no recupera un comando que se perdió antes de enviarse.
2. **D04/D05, P1: aplicar la revisión con visión**, ya hecha en
   `backend/docs/REVISION_CON_VISION.md`. Cabecera a 1024 sin solapes; resultados de tierras
   visibles con filtros avanzados plegables; resolver el acceso de trabajo duplicado sin
   cambiar las seis acciones contractuales. Capturas nuevas con viewport real y comprobación
   de identidad de pantalla. No basta con que el ancho de documento no desborde.
3. **D07: corregir primero el instrumento.** No usar `nav.abrir` en cada transición: recarga
   el documento y borra precisamente la memoria que se quiere medir. Exigir timeOrigin
   constante y verificar sesión SPA; después resolver ciclo de vida de raíces y trazas.
4. **D06 local:** límites de acceso, revocación de sesiones y gestión de secretos/copias no
   requieren esperar a un proveedor para escribir y probar el código. Separar este trabajo
   de la validación de un despliegue concreto, que sí necesita su entorno definido.
5. Continuar el resto del encargo con criterios y evidencia; D08 necesita material autorizado.

También se corrigió una carrera PAC descubierta por la suite completa: el guardado miraba
la huella y después el máximo de versión; otra foto podía confirmarse entre ambas consultas
y terminar en dos IDs para el mismo contenido. Ahora lee primero la versión y después la
huella; el índice de versión obliga a reintentar si una confirmación posterior se intercala.
La prueba fuerza esa secuencia con eventos, falla con el código anterior y pasa con el nuevo.
No repetir el arreglo ni sustituir esa prueba por rondas aleatorias que eventualmente pasen.

El scroll se ha corregido en esta revisión: React confirma el contenido antes de restaurar
posición. `medir_la_vuelta_de_la_ficha.py` ahora falla si no se conserva y pasa 16/16 a
1440 y 390; con el montaje anterior falla 6 casos. No volver al diagnóstico de «alguien escribe
cero después» sin una reproducción nueva. La revisión visual ya no necesita otro modelo:
está hecha y solicita cambios concretos. Las medidas antiguas sobre rutas inválidas o
ventanas distintas no acreditan los tamaños declarados; repetirlas con controles positivos.

## Entrega integrada y revisión independiente — 21/10/2026

La rama `integracion/cloud-estabilizacion-2026-10-21` conserva la entrega cloud y los diez commits
Windows hasta `8392f4d`. Se han integrado con una fusión, no recreado ni descartado sus commits.
**Usar esta rama de Git; el ZIP del 20/10 ya no es el mecanismo de continuidad.** No aplicar su parche
otra vez encima. El árbol Windows `F:\EspacioCodigo\CueDigital` sigue siendo un destino válido.
Antes de cambiar de rama, revisar `git status` y conservar cualquier trabajo pendiente.

```bash
git fetch origin refs/heads/integracion/cloud-estabilizacion-2026-10-21:refs/remotes/origin/integracion/cloud-estabilizacion-2026-10-21
git switch -c integracion/cloud-estabilizacion-2026-10-21 --track origin/integracion/cloud-estabilizacion-2026-10-21
```

El segundo comando crea la rama local si no existe; si ya existe, comprobar su estado y cambiar a ella
sin recrearla. No tocar `main` ni `principal`. Los informes describen primero la auditoría histórica:
leer también el cierre del 21/10 de `REVISION_PRODUCTO_2026-10-19.md` antes de repetir un arreglo.

**Numeración canónica: D01 = cola, D02 = PAC, D03 = fallos/recuperación.** La entrega Windows
intercambiaba D01/D02 al no disponer del encargo. No abrir otro plan con esos números al revés.

### D01 sigue ABIERTO: reproducciones independientes sobre el código integrado

1. `sesionDelToken` esperaba un JWT de tres partes, pero `security.crear_token` emite `carga.firma`.
   **Corregido en esta integración**, con prueba que entrega un token creado por Python al lector JS.
   No volver a deducir el contexto de `estado.yo` si el vale no se puede leer.
2. `enviarOApuntar` hace el primer POST sin sellar la clave. Tras pérdida de respuesta, la cola añade
   una clave nueva: se reprodujeron **dos trabajos reales** para una sola intención. Sellar identidad
   ANTES del primer intento y conservarla en todos los caminos; inventariar todas las rutas encolables.
3. Si A inicia un envío, cambia a B y después falla la red, `apuntarSinCobertura` asigna el dueño B.
   Capturar cuenta/finca/token/datos antes de cualquier `await`, también para el primer envío, no solo
   el vaciado. Probar con promesas controladas: no hace falta depender de temporizadores aleatorios.
4. Dos instancias con reloj idéntico generan el mismo `id_local`; confirmar uno elimina ambos.
   Identidad resistente a reinicios/pestañas y persistencia que no pierda escrituras concurrentes.
   No basta la idempotencia del servidor para resolver pérdidas locales antes del envío.
5. Si localStorage falla desde el arranque, `almacenSeguro` devuelve memoria y la cola dice `guardado`.
   La prueba de `setItem` que lanza después de crear la cola no cubría esta sustitución. Distinguir
   persistencia durable de memoria; conservar formulario y no prometer guardado sin confirmación.
6. Si falla guardar rechazados, `guardar` oculta el fallo y después `cola.quitar` borra el original.
   Reproducido sin pendientes ni rechazo conservado. Transferencia durable antes de quitar, con dueño,
   identidad/ruta/datos y recuperación; 401/403 no son rechazos definitivos. Un 401 antiguo tampoco
   debe cerrar una cuenta nueva que entró mientras la petición estaba en vuelo.
7. Último apunte y rechazados continúan con claves globales. Cerrar aislamiento y migración completos,
   no solo el filtrado de pendientes, y comprobar que los apuntes sin dueño se distinguen de los ajenos.

Evidencia y diagnóstico ejecutable: `docs/revision-2026-10-19/reproducciones.txt` y
`node docs/revision-2026-10-19/reproducir-cola.mjs`. Este diagnóstico espera reproducir defectos
(y sale con código 1); NO contarlo como suite verde. Extrae funciones originales y controla sus
colaboradores en VM; no equivale a un recorrido de UI. El caso adicional de duplicación se contrastó
contra servidor real aislado. Convertir estos casos en regresiones de comportamiento al arreglarlos.

### D02: avances comprobados, contrato completo por revisar

La identidad año/versión e ID, conflicto por huella, exportación y deduplicación de contenido están
integrados. El recorrido real PAC pasa 16 comprobaciones; no confundir eso con cierre de cada criterio.
**También se reprodujeron con servidor real dos defectos pendientes:**

- Con tierras sin superficie, el paquete devuelve denominador/porcentaje `null`, pero el escenario
  suma los valores conocidos ignorando las ausencias y muestra total `290` y `0 %`. Desconocido no
  es cero ni un total completo. Conservar desconocido o separar subtotal conocido/cobertura, sin
  publicar porcentaje completo. Probar además superficie cultivada desconocida y comparar alternativas.
- Una campaña inexistente (`campana_id=999999`) permite evaluar y guardar una foto, ambos con 200.
  Si se pide una campaña explícita inexistente o ajena, rechazar sin revelar datos (404) antes de
  evaluar/guardar; distinguirlo de no enviar campaña. Probar ambos endpoints y ninguna escritura.

Revisar además compatibilidad/migración de fotos previas, falta de huella (`None` permite guardar lo
actual), `recalcular=True` y reglas/fuentes que forman la identidad.
Distinguir reintento de la misma intención y nueva evaluación: deduplicar por contenido es la política
implementada, pero no sustituye toda la identidad de una orden ni su consistencia ante cambios posteriores.

Cerrar D01 por sus regresiones y completar D02; después D03 según su especificación más abajo.
D03 consiste en distinguir carga, vacío real, fallo, permiso y dato antiguo, con reintento y formulario,
filtros, finca y campaña conservados. No interpretar un `.catch(() => [])` como «no hay datos».
Continuar los cortes restantes con sus criterios y evidencias. No volver a buscar el paquete por discos.

**La aplicación YA existe en el repositorio privado `ErDeivih/CueDigital`.** No crear otra app, otro
repositorio ni una maqueta independiente. Trabajar sobre los modelos, rutas, pantallas React/HTM,
datos oficiales, fixtures y pruebas existentes. No reconstruir el frontend con Vite/Next ni sustituir
FastAPI como consecuencia de este encargo. No instalar servicios de pago para completar una pantalla.

## Antes de implementar

1. Usar el checkout existente donde se integra el trabajo: `/workspace/CueDigital` en cloud,
   o `F:\EspacioCodigo\CueDigital` en Windows. Comprobar su identidad con Git, no solo su ruta.
   No crear worktrees salvo petición expresa: la tarea cloud ya está aislada.
2. Leer `AGENTS.md`, `CONTEXTO_PARA_EL_CHAT.md`, `DESARROLLO_EN_LA_NUBE.md`, `DESIGN.md`,
   `docs/CONTRATO_IMPLEMENTACION_CRM.md`, `docs/MATRIZ_NORMATIVA_CRM.md` y esta entrega.
3. Leer `docs/REVISION_PRODUCTO_2026-10-19.md`, `docs/ESPEC_MARCA_UX_2026-10-19.md`,
   `contexto_agentes/REVISION_PAC_2026-10-18.md` y la cola existente. No tratar cifras históricas como estado actual.
4. Comprobar `git status`, rama y HEAD, y usar la entrega integrada indicada arriba.
   La auditoría original partía de `dc0e4a5`; los resultados de esa base no certifican la integración.
   No resetear cambios pendientes ni aplicar de nuevo el antiguo parche cloud.
5. Inventariar para cada ticket: pantalla → acción → ruta → modelo → efectos → permiso → prueba.
   Reproducir el fallo y conservar evidencia de su estado anterior antes del arreglo.

El setup es `bash .codex/setup.sh` desde la raíz; Python 3.12, Node 24, SQLite para desarrollo.
No hay instalación npm ni compilación del frontend. Las herramientas de lint de CI son herramientas
de desarrollo, no una cadena nueva de producción. Nunca usar `backend/cuedigital.db` o adjuntos reales
para ensayos. Usar base, carpeta de adjuntos, puerto y perfil de navegador temporales.

## Qué incorpora esta entrega y se debe conservar

- Corrección del simulador ASGI que bloqueaba pytest, sin eliminar sus controles positivos.
- Navegador portable, corrección de la rama de reconstrucción de FK y pruebas con una venta antigua.
- Protección previa de restauración con WAL vivo; exige aplicación parada y conserva la base si rechaza.
- Correcciones de rectificación documental y aviso al subir una factura sin fichero, con pruebas de acciones.
- Marca CUE Digital, símbolo propio, entrada centrada, rótulos contrastados e icono instalable coherente.
- Acciones móviles antes de las métricas; cifras españolas, unidades legibles y campaña explícita del panel.
- CI Linux/Windows, navegador obligatorio, límite por test, JUnit, Ruff y ESLint, acciones fijadas por SHA.

No deshacer estas correcciones para recuperar una captura anterior ni resolver una regresión desactivando
una prueba. Las pruebas nuevas deben comprobar comportamiento; un texto presente en un fichero no
acredita que una acción funcione. Los resultados finales están en el cierre del informe de revisión.

## Orden de ejecución y relación con la cola existente

| Corte | Prioridad | CRM existente | Depende de | Salida cerrable |
|---|---|---|---|---|
| D01 Cola y almacenamiento con dueño | P0 | CRM-08 | Ninguno | No hay envíos cruzados ni falsos guardados |
| D02 Fotos y evaluación PAC | P0 | CRM-09 | Identidad/contexto actual | Una versión identifica exactamente lo visto y exportado |
| D03 Errores, contexto y recuperación | P1 | CRM-08 / CRM-11 | D01 | Fallo nunca aparenta vacío ni pierde el formulario |
| D04 Tierras y despacho coherente | P1 | CRM-06 / CRM-00 | D03 | Lista/mapa/ficha únicos y filtros útiles |
| D05 Identidad y tareas completas | P1 | CRM-00 / CRM-01 / CRM-11 | D04 | Marca aplicada y recorridos comprensibles en móvil/PC |
| D06 Piloto y operación comercial | P0 antes de exposición | CRM-08 | D01, D02 | Acceso, copia, restauración y despliegue ensayados |
| D07 Rendimiento y mantenimiento | P1 | Transversal | Regresiones de los cortes anteriores | Navegación estable y memoria acotada |
| D08 Integraciones y alcance ampliado | P2 | CRM-10 / CRM-12 | Fuentes/corpus/accesos | Solo promesas medidas y documentadas |

Se adelanta la fiabilidad dentro del contrato existente; no se abre un segundo plan de CRM.
Máximo un escritor por fichero compartido. No mezclar una migración crítica y un rediseño amplio
en una entrega imposible de revisar. Cerrar D01 y D02 antes de ampliar promesas de producto.

## D01 — Cola local, cuenta, finca y persistencia

**Defecto reproducido:** un alta de tierra pendiente de A se envía al entrar como B y se crea en B.
No depende de un ID ajeno ni de un fallo de autorización: `api()` usa el token actual.

Rutas iniciales: `backend/web/nucleo.js` (`crearCola`), `backend/web/app.js`
(`enviarOApuntar`, `mandarPendientes`, `api`, `salir`, cambio de finca, `CLAVE_ULTIMO`, `CLAVE_RECHAZADOS`),
pruebas JS de núcleo/interfaz y regresión con servidor/navegador reales.

Contrato de datos propuesto:

- Comando persistido: versión de esquema, ID estable de comando, usuario creador, finca de origen,
  campaña cuando proceda, método/ruta, datos, fecha del hecho y fecha local de creación.
  No persistir un token de acceso dentro de cada apunte.
- Almacenamiento por cuenta/finca; último apunte, borrador, rechazados y pendientes siguen el mismo contexto.
  La clave no puede contener `sin-cuenta` como propietario compartido.
- El reenvío captura su contexto al empezar y no adopta otro si cambia la cuenta/finca mientras espera.
  El servidor deriva la autorización del token y rechaza una orden cuyo contexto declarado no coincide.
- La misma clave de comando debe tener garantía idempotente en todas las altas que la cola permita.
  `Date.now` o un contador reiniciado no bastan como identidad entre pestañas/reinicios.
- Si no hay identidad utilizable o persistencia confirmada, no contestar «guardado en el móvil».
  Conservar el formulario y explicar la acción necesaria. No perder el dato por cuota o almacenamiento privado.
- Evitar dos procesadores concurrentes de la cola en eventos `online`, arranque y varias pestañas.
  Bloqueo/lease con caducidad y autoridad de idempotencia en el servidor, sin depender solo del bloqueo local.

**Migración:** las entradas de la clave global antigua no tienen dueño fiable. No asignarlas a quien esté
conectado al actualizar. Conservarlas en cuarentena, impedir su envío y ofrecer recuperación documentada
con comprobación del origen. No mostrar contenido de otra cuenta como un borrador propio. No borrarlas
para conseguir que la prueba pase; probar actualización con datos locales ya existentes.

Aceptación obligatoria:

1. A sin red apunta una tierra, cierra, entra B con red: B no recibe la tierra, ni ve su contenido como suyo.
2. A vuelve con red: solo sus comandos correctos se envían, una vez; quedan sus rechazos recuperables.
3. Misma cuenta con dos fincas: no hay cruces; cambiar durante una petición no vacía la cola equivocada.
4. Respuesta perdida, reintento y dos pestañas no duplican ni consumen dos veces.
5. `setItem` que lanza, cuota agotada, JSON local corrupto y navegador reiniciado no producen un falso éxito.
6. Las entradas antiguas sin dueño permanecen recuperables y nunca se autoenvían como B.
7. Si falta permiso o caduca el acceso, no descartar como «rechazado definitivo» una orden válida pendiente.

## D02 — Identidad PAC, evaluación y versión guardada

Rutas iniciales: `backend/app/routers/pac_api.py`, `app/pac.py`, `models.FotoDeLaPac`,
`web/react/pantallas/pac.js`, router y acciones de `app.js`, pruebas de escenarios/fotos/exportación.

Contrato:

- Cada foto tiene un ID inmutable, explotación, año objetivo, versión, autor/fecha y huella del contenido.
  Verificar las restricciones existentes antes de crear índices o migraciones; preservar todas las fotos.
- Propuesta de API canónica: `GET /api/pac/fotos/{foto_id}` y su exportación, listado por año,
  respuesta de alta con `id`, `anio`, `version` y enlaces inequívocos. Adaptar los nombres a la convención
  vigente si hay una mejor opción, manteniendo esta semántica.
- Compatibilidad: una dirección antigua por versión debe exigir año si es ambigua o devolver conflicto
  explicable. Nunca `first`, `limit(1)` ni cambiar el orden para ocultar la ambigüedad.
- Evaluar devuelve una identidad/huella validada por servidor y asociada a su finca, entradas, reglas y datos
  de origen. Guardar esa evaluación exacta. Si la base cambió, conflicto explícito y opción de recalcular.
  No confiar en un JSON libre del cliente para afirmar que representa el estado real.
- Numeración garantizada por transacción/restricción de base y tratamiento de colisión. Reintentar la misma
  petición devuelve la misma foto; una nueva intención crea otra versión. Nunca sobrescribir una foto.
- Exportar devuelve el mismo contenido de la foto y su huella/identidad. Una campaña ajena o foto de otra
  finca da 404 sin filtrar metadatos. Registro de modificaciones fuera de la foto no la altera.

Pruebas mínimas: 2027 v1 y 2028 v1, varias versiones de cada año, segunda finca, respuesta perdida,
dos guardados simultáneos, actualización con fotos existentes, cambio de alias/cultivo/superficie entre
evaluar y guardar, reglas de otro ámbito/año y exportación de la versión elegida.

Recorrido: abrir campaña de origen → elegir año objetivo → editar hipótesis → comparar alternativas →
ver datos pendientes → evaluar → guardar versión → abrir historial → abrir/exportar esa misma versión.
Comprobar que no se cambia lo declarado, no se consumen existencias y no se inventa elegibilidad.

## D03 — Fallo, vacío, permisos y contexto

Inventariar los `.catch(() => [])`/`null` de `cargarDatos` y las cargas de módulos.
Introducir estados explícitos de carga/success/fallo/restringido/dato local antiguo, con reintento por
sección. Un fallo de facturas no implica cero facturas ni deja guardar una propuesta con referencias vacías.

Conservar borrador, filtros, finca y campaña al reintentar. Un 401 no debe mezclar el contexto anterior con
una nueva cuenta. Un 403 no debe reintentarse como alta sin cobertura. El borrado/anulación requiere motivo
y conserva auditoría. Aplicar el contrato de estados de la especificación UX.

Probar red caída, 500, 401, 403, 404 de registro y lista legítimamente vacía. No basta con devolver cadenas
distintas: comprobar controles, foco, ausencia de cifras falsas y persistencia del contenido del formulario.

## D04 — Una experiencia de tierras y despacho

Cerrar la doble puerta `#/tierras` / `#/tierras/mapa` con una ruta/ficha canónica y compatibilidad.
Reutilizar el filtrado, mapa, geometrías, versiones y selección existentes. No crear tablas paralelas para
simular lo que el servidor ya sabe hacer. Tabla de enlaces antiguos/nuevos antes de mover acciones.

En 1440×900: búsqueda, contexto y filtros activos visibles junto a resultados útiles; opciones avanzadas
plegables; tabla/mapa sincronizados por ID. En 1024: ninguna columna de acciones queda fuera de la página.
En móvil: tarjetas útiles y filtros breves; sin forzar a atravesar todos los municipios/cultivos antes de
ver las tierras. Nunca reducir controles por debajo del suelo del diseño para hacerlos caber.

Aceptar con 64 tierras, búsqueda que devuelve 8, filtro cruzado de cultivo y pueblo, tierra sin geometría,
polígono con agujero, selección múltiple, exportación filtrada y regreso desde la ficha con scroll/filtros
conservados. Probar enlace directo, recarga, Atrás/Adelante y cambio de campaña sin cambiar la historia.

## D05 — Marca, móvil y flujos de dinero/documentos

Aplicar `docs/ESPEC_MARCA_UX_2026-10-19.md` y `DESIGN.md`: conservar símbolo, paleta, voz y datos reales;
extenderlos a informes y estados. Entregar variantes de icono, impresión/monocromo y PWA instalada.
El propietario debe verificar disponibilidad de nombre/marca/dominio antes de fijar la identidad comercial.

Cerrar cuatro cortes de experiencia completos: tierra → trabajo → consumo; compra → recepción → lote →
gasto → pago; venta → factura → cobro parcial → pendiente; papel → propuesta → confirmación/rectificación.
Cada total abre sus registros por ID y conserva contexto. Revisar también texto de ayuda, vacío, error,
conflicto y sin permiso. No usar visuales de «cumple» o «pagado» cuando solo falta un dato.

Capturas de 320/390/712/1024/1440, zoom 200 %, tabulador/Escape, foco de regreso, lector de pantalla,
contraste y controles táctiles. Revisión con visión: si el modelo no ve imágenes, mantener EN_REVISION
hasta que un revisor que sí las vea emita resultado. Prueba de tareas con usuarios, no solo opinión estética.

## D06 — Operación y comercialización

Preparar primero un piloto por instalación aislada, coherente con la arquitectura actual. Si se elige
SaaS compartido, presentar antes su contrato de aislamiento, operación, soporte, cuotas y costes; no
declarar que las pruebas SQLite equivalen a un servicio multiusuario de producción.

- Configuración de producción: secreto persistente y rotación, HTTPS, proxy de certificados fiable,
  límites de intentos y tamaños, permisos de almacenamiento y logs que no contengan datos privados.
- Sesiones: revocación al cambiar clave/retirar acceso, cierre y recuperación de cuenta verificables;
  decidir segundo factor según despliegue. Conservar la matriz de permisos y probar enlaces directos.
- Copia: base coherente, adjuntos, configuración necesaria y versiones, con cifrado/retención definidos.
  Restaurar en destino nuevo; abrir documentos y comprobar vínculos/firmas, no solo `quick_check`.
- Actualización: copia previa, migración idempotente ensayada, comprobación posterior y vuelta atrás real.
  No restaurar encima de una aplicación viva, ni borrar un WAL porque Linux deje hacerlo.
- Si PostgreSQL es el destino comercial, levantar una instancia desechable y ejecutar aceptaciones y
  migraciones esenciales en ese motor. Si no se puede, dejar la promesa limitada a SQLite.
- Inventario de licencias del código/vendor/datos/cartografía, privacidad y retención, soporte,
  alcance fiscal/normativo y condiciones de servicio. Una revisión de software no es asesoría jurídica.

Las pruebas que requieren proveedor/certificado real permanecen separadas y documentadas.
SIGPAC e IUWS devolvieron 403 del proxy en esta revisión. Solicitar solo dominio/acceso que siga faltando,
por ajustes seguros; nunca pedir certificados, tokens o bases agrícolas en chat ni guardarlos en fixtures.

## D07/D08 — Después de cerrar lo anterior

D07: medir navegación prolongada, peticiones de arranque y memoria; una raíz React controlada por
contenedor, desmontaje/foco correctos, historial de instrumentación fuera de producción o acotado.
Extraer `app.js` por dominio después de asegurar contratos de eventos y rutas, sin una reescritura masiva.

D08: OCR con corpus autorizado y resultados por campo; meteo/satélite con fuente/licencia/fecha/resolución
y estados observado/estimado/pronóstico distintos; reglas legales con autoridad/ámbito/campaña/versión.
Avanzar tareas independientes mientras falte un acceso; no sustituir lo desconocido por un mock presentado
como integración disponible. No inventar datos del agricultor, precios, geometrías ni normativa.

## Criterio de cierre de cada corte

1. Reproducción anterior y regresión que detecta el defecto; código propio con cambios revisables.
2. Pruebas afectadas y ambas suites completas, indicando fallos/omitidos y sus causas.
3. Humo con servidor/base/adjuntos temporales; separar el fallo de un proveedor del flujo interno.
4. Si afecta UI: capturas actuales vistas, teclado, foco, tamaños y contrato de diseño coherente.
5. Si afecta persistencia: migración idempotente con copia, dos ejecuciones, datos anteriores conservados,
   concurrencia y rollback/recuperación. No tocar datos reales.
6. Actualizar contrato y cola existentes con commit/evidencia y próximo paso. No cerrar por una captura,
   por un test que no ejecutó casos ni por un script que devolvió cero ignorando fallos.

Desde `backend`: `../.venv/bin/python -m pytest tests --timeout=180 --timeout-method=thread`
y `node --test "tests_js/*.test.js"`. En Windows usar el intérprete de `.venv/Scripts`.
Para lint, usar exactamente los comandos de `.github/workflows/ci.yml`. Una modificación de UI exige
además `designmd lint DESIGN.md`. Mantener todos los casos y controles positivos.

El repositorio comprueba sus recuentos en README, AGENTS y `docs/LO_QUE_PIDE_LA_JUNTA.md`.
Medir la colección real antes de actualizar esos tres números: añadir documentación también puede
añadir casos parametrizados de revisión UTF-8. No desactivar ese guardián ni sumar estimaciones.
Se conserva una omisión previa del caso de exceso de cobro: el escenario intenta imputar a una factura
ya saldada y la API lo rechaza; no acredita el recorrido alternativo de saldo sin asignar. Cerrarlo en D05
con un escenario válido, sin permitir una sobreimputación para que pase una prueba.

## Objetivo para pegar al agente

```text
Continúa CUE Digital en el repositorio existente ErDeivih/CueDigital. La aplicación ya está hecha
en /workspace/CueDigital; no crees otra app ni copies una plantilla genérica. Lee AGENTS.md y
docs/ENCARGO_DEEPSEEK_2026-10-19.md, junto al contrato CRM, la revisión de producto y la especificación UX.
Verifica HEAD y cambios locales y conserva la entrega anterior.
Empieza por D01 (cola aislada, migración y persistencia) y D02 (fotos/evaluación PAC inequívocas).
Cierra cada corte con reproducción, regresión, recorrido real y evidencia, y continúa los cortes
independientes autorizados sin parar tras un resumen. Mantén un escritor por fichero compartido.
No uses bases, adjuntos ni certificados reales. No desactives pruebas ni conviertas fallos en vacíos.
Conserva FastAPI, React/HTM sin compilación, el lenguaje agrario claro y la identidad CUE Digital.
No declares el producto comercializable mientras existan bloqueos P0 o falte la revisión visual
y operativa. Si no puedes ver capturas, entrégalas con medidas a un revisor con visión y deja
la revisión pendiente. Registra límites externos concretos y continúa el trabajo independiente.
```
