# CUE Digital: revisión técnica, de producto y de experiencia

Fecha: 19/10/2026. Base inspeccionada: `dc0e4a5`, checkout `/workspace/CueDigital`, rama local `work`.
Autor: revisión realizada en el entorno cloud con datos ficticios. Los cambios están en el árbol de trabajo.

**Continuidad:** lo anterior identifica la instantánea inicial. Leer el cierre del **21/10/2026**
al final: ambas entregas están integradas, pero la revisión independiente mantiene D01 abierto.

**Decisión: apta para continuar desarrollo y preparar un piloto; todavía no para una venta general.**
La cantidad de funciones y de pruebas es importante, pero una suite verde no evita por sí sola los
defectos de aislamiento y de identidad reproducidos aquí. No se certifica ausencia de errores,
cumplimiento normativo, seguridad completa ni equivalencia con PostgreSQL.

Esta revisión actualiza la evidencia, no reemplaza los contratos CRM ni convierte sus pendientes en hechos.
Leer junto a [contrato CRM](CONTRATO_IMPLEMENTACION_CRM.md), [matriz normativa](MATRIZ_NORMATIVA_CRM.md),
[especificación de marca y UX](ESPEC_MARCA_UX_2026-10-19.md) y
[encargo de implementación](ENCARGO_DEEPSEEK_2026-10-19.md).

## Alcance y límites de la revisión

- Inventario estático de los 96 módulos Python de `backend/app`: 84.741 líneas, 1.818 funciones y
  357 declaraciones HTTP al generar el [inventario](INVENTARIO_REVISION_2026-10-19.md).
  Las líneas incluyen comentarios; los recuentos describen tamaño, no calidad ni cobertura.
- Análisis de referencias indefinidas en `app` y `scripts`, y de variables indefinidas, claves
  duplicadas y código inalcanzable en todo el JavaScript propio. Se excluye el vendor de terceros.
- Lectura de contratos, arquitectura, autenticación, permisos, persistencia, restauración,
  cola local, arranque, PAC, textos, navegación, montaje React, PWA, diseño y CI.
- Suites completas, regresiones específicas, servidor real, humo y revisión de capturas de escritorio
  y móvil con una finca ficticia de 64 tierras, 20 contactos, 8 máquinas, compras, trabajos y banco.
- Inventariar todas las rutas no significa haber intentado todas las combinaciones de estados,
  permisos, importaciones, concurrencia y dispositivos. No se ha efectuado un pentest ni una
  certificación fiscal, normativa o de accesibilidad. Windows queda configurado en CI, no ejecutado aquí.

## Hallazgos que bloquean la comercialización

### R01 — La cola puede escribir en otra finca: P0, pendiente

Código: `backend/web/app.js`, `enviarOApuntar`, `mandarPendientes`, `api`, `salir`;
`backend/web/nucleo.js`, `crearCola`. Clave global: `cuedigital.pendientes`.

La cola persiste al salir, pero no guarda una identidad de cuenta/finca que limite su envío.
Al volver a entrar, `api()` firma las peticiones con el token de la cuenta actual.
Una tierra nueva no necesita referenciar un ID de la finca antigua: puede crearse en la nueva.

Reproducción realizada en Chromium y servidor temporal: cola de origen A (explotación 2),
reconexión con B (explotación 1), `POST /api/parcelas` pendiente con alias
`AUDITORIA_COLA_ORIGEN_A`. Resultado: tierra 66 creada en B. No es una hipótesis sobre permisos del servidor:
el servidor recibe una orden válida de B porque el cliente perdió su origen.

Además, `cuedigital.ultimo` y `cuedigital.rechazados` son globales. `crearCola.escribir` puede devolver
`false` por cuota/permisos y `apuntar` no propaga ese fallo: la interfaz puede afirmar que algo quedó
guardado sin haberse persistido. Son defectos distintos dentro del mismo bloque de fiabilidad.

**No resuelto por este cambio.** Requiere aislamiento, migración de las colas existentes, recuperación
de entradas sin dueño y pruebas de cambio de cuenta/finca, almacenamiento y respuesta perdida. Ticket D01.

### R02 — Las fotos PAC no identifican el año: P0, pendiente

Código: `backend/app/routers/pac_api.py`, `guardar_la_foto_de_la_pac`, `_la_foto` y exportación;
`models.FotoDeLaPac`.

El alta numera por explotación/año; el detalle consulta por explotación/versión sin año.
Reproducido en esta revisión: guardar 2027 → v1; guardar 2028 → v1;
abrir `/api/pac/foto/1` para la segunda → contenido de 2027.
El defecto ya estaba documentado el 18/10 y sigue presente en esta rama.

El alta también vuelve a calcular en vez de guardar una evaluación identificada que el usuario haya visto.
La revisión anterior reproduce una modificación entre evaluar y guardar; la lectura actual confirma que
se sigue recalculando. `max(version)+1` necesita garantía transaccional e idempotencia, no solo una consulta.

**No resuelto por este cambio.** Debe cerrarse identidad + evaluación + concurrencia y el recorrido de pantalla,
no solo cambiar la consulta para elegir otra fila. Ticket D02.

### R03 — Preparación para exposición comercial: P0/P1 según despliegue, pendiente

`security.py` declara límites todavía pendientes: intentos de acceso, revocación, rotación y doble factor.
Los tokens duran 30 días; no contienen una versión de credenciales para revocarlos al cambiar una clave.
La clave aleatoria de desarrollo invalida accesos al reiniciar y no sustituye la configuración de producción.

Antes de exponer un servicio: definir instalación aislada o SaaS compartido, HTTPS/proxy fiable,
secretos persistentes, límites de autenticación y de recursos, recuperación de cuenta,
privacidad/retención, actualización y restauración. No activar confianza en cabeceras de certificado
en una aplicación accesible directamente. Ticket D06; la matriz de roles actual debe conservarse.

## Correcciones aplicadas

| Problema | Cambio | Evidencia relevante |
|---|---|---|
| CI se bloqueaba al 71 % | El cliente ASGI entrega una petición, espera la respuesta y después desconecta; espera acotada | Se conservan las 13 pruebas de protección de descargas, incluidos controles positivos |
| Chromium instalado pero recorridos dicen que no existe | Detección Linux/macOS/PATH y la misma detección en pruebas y guion de comprobación | Recorridos reales, no omisiones artificiales |
| Una migración fallaba al necesitar reconstruir una tabla | Importación local de `models` en la rama que sí reconstruye | Nueva prueba con una venta antigua, copia, fila conservada, FK reparada e idempotencia |
| `Decimal` no estaba definido en anotaciones de servicios | Importación explícita | Ruff sobre todo el backend propio |
| Rectificar un papel rompía la acción | `alQueCorrije` → variable elegida `alQueCorrige` | Prueba de botón que exige POST y cuerpo con el ID seleccionado |
| Subir justificante sin elegir fichero lanzaba `ReferenceError` | Obtención del aviso mediante los textos del servidor | Prueba que exige aviso y ausencia de envío |
| Estado inicial declaraba `medidas` dos veces | Una única declaración | ESLint `no-dupe-keys` |
| Una prueba de caja del mapa dependía de IGN | Doble solo del proveedor; endpoint, validación, caja y bytes reales del ensayo se comprueban | Regresión de mapa sin dependencia de red; conexión real permanece separada |
| Restaurar podía pisar una base con WAL abierto en Linux | Preparación de WAL con SQLite antes de sustituir archivos; rechazo si está en uso; tolerar sidecars ya cerrados por SQLite | Base temporal con conexión viva conserva sus dos filas; restauración tras caída conserva la vuelta atrás |
| Entrada descentrada y sin identidad | Formulario centrado, marca común, símbolo vectorial, CTA verde, favicon y nombre instalable | Capturas de navegador y prueba de coherencia de marca/API/icono |
| Rótulos verdes sobre fondo verde apenas legibles | Texto blanco usando los tokens existentes | Capturas de menú y barra |
| Indicadores mostraban claves y decimales técnicos | Presentación española, unidades legibles, tarjetas separadas, campaña explícita al pedir el panel | Prueba con cantidad, cero y desconocido; recorrido de panel |
| El vocabulario del panel podía incluir la moneda en respuestas restringidas | Las etiquetas de unidad también respetan la capacidad económica | Cuatro pruebas de privacidad conservadas, con control positivo del titular |
| Indicadores desplazaban las acciones del campo | Se conservan los seis botones y su orden y se muestran antes de las métricas | Capturas móviles |
| CI carecía de controles para estos fallos | Python Linux/Windows, navegador obligatorio, límite por caso, JUnit y análisis estático | Validación local; SHA de las acciones comprobados contra sus etiquetas remotas |

El guardado de restauración sigue siendo una operación de mantenimiento **con la aplicación parada**.
La comprobación de WAL no acredita restauración concurrente ni un sistema completo de copias de adjuntos.

## UI/UX: lo que impide una experiencia comercial sólida

1. **Dos caminos a las tierras.** `#/tierras` mezcla parcelas, productos y máquinas;
   `#/tierras/mapa` ofrece la vista nueva. Hay nombres largos y contextos que abren el camino heredado.
   Mantener un modelo y una ficha canónica, y migrar enlaces con compatibilidad. CRM-06 / D04.
2. **Filtros que ocupan la pantalla antes de ver las tierras.** En escritorio, los botones de cultivo,
   municipio y estado se apilan; a 1440 px la tabla/mapa queda por debajo del primer pliegue.
   La capacidad existe, la jerarquía necesita otro diseño. No resolver reduciendo la letra. D04.
3. **Menú largo y vocabulario irregular.** Se mezclan módulos, objetos y frases: una cuenta necesita
   reconocer Tierras, Trabajo, Almacén, Cuentas, Personas y Cuaderno sin leer párrafos de navegación.
   Mantener la voz clara en ayuda y acciones; nombres breves y estables en despacho. D04.
4. **Fallos que aparentan vacío.** `cargarDatos` convierte numerosas peticiones fallidas en `[]` o `null`.
   Deben distinguirse vacío, sin permiso, dato antiguo y fallo con reintento. No se puede interpretar
   «0 facturas» cuando falló la consulta. D03.
5. **Montaje y rendimiento.** `montar.js` crea raíces React nuevas y conserva historiales de montajes
   en arrays también en producción. Revisar propiedad de cada raíz, desmontaje, foco y memoria antes
   de modularizar las más de 24.000 líneas de `app.js`. D07.
6. **PAC aún necesita un recorrido de decisión completo.** Hipótesis, comparación, evaluación versionada,
   historial y exportación deben abrir la misma identidad, sin prometer elegibilidad. D02.
7. **No basta con capturas bonitas.** Faltan pruebas de usabilidad con agricultores autorizados,
   teclado, zoom y sol real. Validar tareas, comprensión del dinero/desconocido y recuperación. D05.

## Funcionalidades y promesas

| Área | Base que existe | Qué debe cerrarse antes de ampliar la promesa |
|---|---|---|
| Tierras/campañas | Altas, historial, geometría, tabla/mapa y versiones | Ficha única, filtros/contexto, solapes y superficies distintas visibles |
| Trabajo/insumos | Planificación, ejecución, consumos, anulación y auditoría | Recuperación sin cobertura y carreras entre dispositivos |
| Compras/almacén | Factura, albarán, lote, gasto y pagos vinculados | Estados y navegación uniforme; ninguna suma económica doble |
| Ventas/banco | Entregas, facturación interna, cobros y conciliación por fichero | Repartos y permisos visibles; no anunciar banca conectada ni fiscalidad certificada |
| Personas/maquinaria | Roles, actividad, tareas, reservas, averías y contadores | Acceso por el mismo registro y obligaciones con aplicabilidad acreditada |
| Cuaderno/PAC | Informes, firmas, reglas documentadas y paquete preparatorio | R02, fuentes vigentes por ámbito/año y revisión agronómica |
| OCR/dictado | Propuestas revisables; OCR local español disponible | Corpus autorizado y evaluación por campo; no prometer precisión no medida |
| Meteo/satélite | Hay especificación y puntos de continuidad | Fuente, licencia, cobertura y piloto; no venderlo como integración comprobada |

## Resultados y evidencia

Verificación final local, cerrada el **20 de octubre de 2026**:

| Comprobación | Resultado |
|---|---|
| Suite Python completa | 5.539 pruebas recogidas: **5.537 superadas, 2 omitidas**, 7 avisos; 12 min 9 s |
| Suite JavaScript completa | **1.146 superadas**, sin fallos ni omisiones |
| Ruff y ESLint | Sin errores en las comprobaciones configuradas |
| Contrato visual `DESIGN.md` | 0 errores y 0 avisos |
| Dependencias Python (`pip check`) | Sin incompatibilidades declaradas |
| Humo con servidor y base temporal | **465 comprobaciones correctas y 1 fallida**: consulta externa SIGPAC bloqueada por el proxy con HTTP 403 |
| Vistas medidas en Chromium | 32 vistas; sin desbordamiento horizontal de página en las medidas conservadas |

Las dos omisiones Python son un escenario de saldo que intenta pagar una factura ya pagada
(el servidor lo rechaza con 422) y una prueba OCR que requiere un entorno solo inglés, cuando
este dispone del modelo español. El primer escenario debe sustituirse por un caso válido;
no acredita que el saldo a favor esté probado. Los siete avisos proceden de API obsoletas
de Starlette/httpx y de la constante antigua para HTTP 422.

La suite completa y el recorrido real de navegador se ejecutaron en Linux. La matriz Windows
y GitHub Actions están configuradas, pero **no se han ejecutado aquí**. SIGPAC y otros servicios
externos necesitan verificación desde una red autorizada; no se ha sustituido ese fallo por éxito.
Estos resultados no cierran R01/R02 ni equivalen a una certificación para comercializar.

Comandos reproducibles desde `backend`:

```bash
../.venv/bin/python -m pytest tests --timeout=180 --timeout-method=thread -o addopts="--strict-markers -v" -o faulthandler_timeout=60 --junitxml=/tmp/cue-python.xml
node --test "tests_js/*.test.js"
```

Desde la raíz: `ruff check --select F821,F822,F823,E9 backend/app backend/scripts`;
`npx --yes --package eslint@9.39.1 eslint --config .github/eslint.config.mjs "backend/web/**/*.js" --ignore-pattern "**/vendor/**"`;
`npx --yes -p @google/design.md designmd lint DESIGN.md`.

Las capturas y reproducciones de esta instancia están en `/workspace/scratch/cuedigital-review/`.
No incluyen cuentas reales ni tokens. Los JSON privados de preparación permanecen en `/tmp` y no deben versionarse.
Los resultados locales no prueban que GitHub Actions se haya ejecutado: no se ha hecho push ni publicado una release.

Evidencia conservada en el repositorio para el siguiente agente:

- [Entrada anterior](revision-2026-10-19/entrada-antes.png) y [entrada con marca](revision-2026-10-19/entrada-despues.png).
- [Inicio móvil anterior](revision-2026-10-19/inicio-movil-antes.png) y [acciones móviles primero](revision-2026-10-19/inicio-movil-despues.png).
- [Tierras en escritorio: filtro por compactar](revision-2026-10-19/tierras-escritorio.png).
- [Mediciones de 32 vistas y cabecera táctil](revision-2026-10-19/mediciones.json) y
  [reproducciones de los bloqueos](revision-2026-10-19/reproducciones.txt).

Las 32 medidas corresponden a 14 rutas en 1440/390 y a inicio/tierras en 1024/320. Comprobar
ancho de página no basta para descartar solapes: se verificaron además rectángulos de los controles
de cabecera y objetivos de 44 px a 320/390/712. Las capturas revisadas representan esos datos ficticios,
no pruebas sobre hardware móvil, cartografía externa disponible ni entrevistas con agricultores.

## Cierre de lanzamiento

No cerrar por una suma de tests: R01/R02 deben tener regresión que falle antes del arreglo y recorrido real,
sin pérdida de datos al migrar. Después: errores/recuperación, permisos de producción, copias/restauración,
revisión visual, prueba con usuarios y revisión de fuentes/licencias. El registro y disponibilidad legal de
la marca CUE Digital requieren comprobación propia; un SVG original no acredita una marca registrada.

## Integración y revisión independiente — 21/10/2026

Rama de entrega: `integracion/cloud-estabilizacion-2026-10-21`. Conserva el commit cloud `c09b793`
y los diez commits Windows hasta `8392f4d`, unidos mediante el merge `1252d49`. No se ha fusionado
`main` ni `principal`. Los documentos y el código viajan juntos por Git: el agente Windows no
necesita encontrar el ZIP del 20/10 ni aplicar de nuevo su parche. Comandos y orden de continuidad
en [el encargo actualizado](ENCARGO_DEEPSEEK_2026-10-19.md).

Se conservaron ambos conjuntos de cambios. Los conflictos manuales fueron recuentos documentales;
se revisaron además las combinaciones automáticas de `app.js`, núcleo y textos. `app.js` conserva
el formato LF de la entrega Windows; `schemas.py` conserva su CRLF. Versión/caché `2026-10-21-78`.
El servidor temporal del recorrido PAC aísla ahora también adjuntos, además de la base.

### Corrección adicional aplicada

El nuevo `sesionDelToken` interpretaba un JWT de tres partes y leía la parte central. Sin embargo,
`security.crear_token` emite **dos partes: carga.firma**, con usuario/finca en la primera.
Sus pruebas inventaban un JWT y no comprobaban ese contrato. Corregidos lector y fixtures, y
eliminada la deducción desde `estado.yo` cuando el vale no se puede interpretar. Nueva regresión
cruzada: Python genera un token real y Node ejecuta el lector de producción, verificando `32:47`.
No se usa esta lectura local como autorización: el servidor sigue comprobando firma y permisos.

### D01 no está cerrado: defectos reproducidos tras integrar

La revisión no acepta como cierre las etiquetas del resumen del otro agente. Sus avances de filtrado,
token capturado en el vaciado y control positivo se conservan. Quedan estas reproducciones:

| Caso | Evidencia y efecto | Corrección exigida |
|---|---|---|
| Primera respuesta perdida | Primer POST sin clave; la cola añade una distinta después. Con servidor real y base temporal una intención creó **dos trabajos**, IDs ficticios 14 y 15 | Sellar identidad antes del primer intento y reutilizarla; cubrir todas las rutas encolables |
| Cambio durante el primer envío | A inicia POST; se cambia a B antes de rechazar su promesa. El pendiente queda con dueño **B** | Capturar contexto de origen antes del primer `await`, no solo al vaciar |
| Identidad entre instancias | Dos colas con el mismo reloj generan igual ID; `quitar` de uno elimina **los dos** | Identidad resistente a reinicio/pestañas y escrituras locales coordinadas |
| Almacén bloqueado al arrancar | `almacenSeguro` sustituye disco por memoria; `apuntar` sigue devolviendo `guardado: true` | Distinguir persistencia durable, conservar formulario y evitar falso guardado |
| Fallo al apartar rechazo | Guardar rechazados lanza y se oculta; se borra el original. Resultado: **0 pendientes, 0 rechazados** | No quitar hasta confirmar persistencia del rechazo, con su dueño y recuperación |

Los cinco casos se ejecutaron sobre funciones originales extraídas de `app.js` en una VM con
colaboradores controlados. No son un recorrido completo de interfaz. **Además**, la duplicación
del primer caso se contrastó contra API real, con pérdida de respuesta simulada después de confirmar
la escritura. No se usaron datos reales. Diagnóstico reproducible:

```bash
node docs/revision-2026-10-19/reproducir-cola.mjs
```

Su salida 1 significa «defectos reproducidos», no un test de aceptación verde. Debe convertirse
en regresiones al corregir D01. Resultados conservados en
[reproducciones](revision-2026-10-19/reproducciones.txt). Último apunte y rechazados siguen con claves
globales; sus permisos, migración y recuperación también forman parte de D01. La idempotencia
del servidor no evita por sí sola pérdidas por almacenamiento o escrituras entre pestañas.

### D02 y continuidad

Se han integrado identidad año/versión e ID, huella/conflicto, historial, exportación y deduplicación
PAC. El recorrido real comprueba 16 casos y el de cola 9, ambos sin fallos. No certifican todas las
condiciones del encargo. Antes de cerrar D02 revisar fotos antiguas, ausencia de huella (admite guardar
el estado actual), `recalcular`, campaña ajena/inexistente, datos desconocidos e identidad de reglas/fuentes.

**La revisión adicional contra servidor real confirma dos defectos D02:**

- En el escenario ficticio había 10 tierras sin superficie. `/paquete` conserva denominador y porcentaje
  `null`; `/escenario` los convierte en `290 ha` y `0 %`, ignorando los datos ausentes en su suma. Un
  subtotal conocido no es la superficie total. Debe conservar desconocido o explicitar cobertura parcial,
  sin presentar un porcentaje completo. Reproducir con alta de tierra de superficie `null` y comparar
  ambos resúmenes para la misma campaña; cubrir también superficie cultivada desconocida.
- `POST /escenario` con `{"anio":2027,"campana_id":999999}` devuelve 200 y un escenario. `POST /foto`
  con ese mismo cuerpo también devuelve 200 y crea una foto. La campaña no existe: `_la_campana`
  devuelve `None` y el cálculo sigue. Rechazar campaña explícita inexistente/ajena antes de evaluar o
  guardar, con 404 y sin escritura; no confundir con omitir el parámetro. Respuestas conservadas en
  el mismo fichero de reproducciones. No se ha probado aquí el caso de campaña ajena con otra cuenta.

La numeración correcta es **D01 cola, D02 PAC, D03 fallos y recuperación**. D03 ya está definido
en el encargo: distinguir carga/vacío/fallo/permiso/dato antiguo, conservar contexto y formulario,
y ofrecer reintento. No hace falta otra decisión del propietario para leerlo o comenzar el corte.

### Verificación de la entrega integrada

Las comprobaciones siguientes corresponden al código integrado de `390187f` (más los añadidos
posteriores de documentación). El primer intento Python se interrumpió al añadir la regresión del token;
no se cuenta como ejecución completa. La ejecución final se inició de nuevo con los 5.566 casos.

| Comprobación local | Resultado |
|---|---|
| Python completo | **5.564 superadas, 2 omitidas**, 0 fallos; 7 avisos; 6 min 43 s |
| JavaScript completo | **1.157 superadas**, 0 fallos, 0 omisiones |
| Recorrido PAC en Chromium y servidor temporal | **16 comprobaciones, 0 fallos** |
| Recorrido cola tras corregir el lector del token | **9 comprobaciones, 0 fallos** |
| Humo completo en servidor/base/adjuntos temporales nuevos | **483 comprobaciones correctas**, salida 0 |
| Ruff / ESLint | Sin errores en las reglas configuradas |
| Contrato visual oficial | 0 errores, 0 avisos |
| `pip check` y comprobación de espacios del diff | Correctos |

Las dos omisiones son las de saldo y OCR explicadas en el cierre del 20/10; los avisos tampoco
son fallos. El humo de esta ejecución sí obtuvo respuesta de SIGPAC; el bloqueo de red del 20/10 es histórico.
No se ha probado IUWS autenticado ni PostgreSQL. Los recorridos positivos no cubren las reproducciones
adicionales de D01/D02: estas siguen pendientes aunque las suites existentes pasen.

La rama está publicada con CI configurada para `integracion/**`, además de `main` y pull requests.
**No se ha verificado el resultado de GitHub Actions ni ejecutado Windows desde este entorno.**
Los comandos para repetir las suites son los de la sección anterior; la regresión nueva necesita
Python y Node, disponibles en el setup y en la matriz CI. No se ha hecho merge en principal.
