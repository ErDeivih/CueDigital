# BACKLOG — CueDigital

> Rama: `integracion/cloud-estabilizacion-2026-10-21`. HEAD al crear este fichero: `8b5c4af`.
> Regla del protocolo: **nunca menos de 5 tareas listas**; se elige la de **más valor**, se ejecuta,
> se pasa la puerta y se actualiza esto. Una tarea de Nivel 3 se marca `esperando decisión` y se
> sigue con la siguiente.

## Reglas de la sesión (límites duros)

- **No se toca el `.env`.** (Hoy no hay ninguno versionado; si aparece uno, no se lee ni se escribe.)
- **No se tocan las fixtures de firma**: `backend/tests/fixtures/firma_cades/`.
- **No se abren ni se cambian ramas.** Se trabaja en `integracion/cloud-estabilizacion-2026-10-21`.
- **Puerta para dar algo por terminado**: `pytest` + `node --test "tests_js/*.test.js"` + humo/recorrido
  que toque, y `commit` + `push`. Sin push no está terminado.
- Lo que no esté claro de alcance = **Nivel 3**: se marca aquí y se sigue con otra tarea.

## Alcance nuevo (2026-11-04): el producto agrícola

> David cambió el rumbo: **la interfaz anterior no le gustaba y el producto se rehace** como la
> herramienta digital del agricultor de Castilla y León. Manda [`ALCANCE-AGRICOLA.md`](ALCANCE-AGRICOLA.md).
> La investigación está en [`docs/INVESTIGACION-AGRICOLA.md`](docs/INVESTIGACION-AGRICOLA.md) y la
> propuesta de pantallas en [`docs/ARQUITECTURA-DE-PANTALLAS.md`](docs/ARQUITECTURA-DE-PANTALLAS.md).
> **Lo de abajo (D01, D07, EST…) queda en pausa** salvo lo que sirva a este alcance; **D08 quedó
> decidido** (corpus pendiente de material de David) y no se persigue ahora.

### AGR-0 · Investigación, arquitectura y primer paquete visual — **HECHO (2026-11-04)**

- **Nivel**: 2.
- **Qué hay**: cuatro líneas de investigación con **URL y fecha en cada afirmación** y lo pendiente
  marcado (`docs/INVESTIGACION-AGRICOLA.md`: SIGPAC, PAC/subvenciones, cuaderno digital, competencia);
  la propuesta de **11 pantallas P0 con flujos, estados y fases** (`docs/ARQUITECTURA-DE-PANTALLAS.md`);
  el **sistema de diseño** agrícola (`designs/cue-agricola-design-system/`, contraste AA calculado) y
  los **artboards** (`designs/cue-agricola/`) para revisar el aspecto antes de implementar.
- **Comprobado el 04/11/2026**: `/IUWS/api/version` contesta 200 sin certificado (v3.11.4); la
  convocatoria PAC 2026 en BOCYL (1-feb→30-abr, ampliada al 15-may); el SIGPAC publica GeoPackage por
  provincia con licencia CC BY 4.0; la vía de CyL prohíbe la explotación comercial de su SHP.
- **Pendiente**: la aprobación de David (AGR-1).

### AGR-1 · Aprobación de David: arquitectura y aspecto — **CERRADA (2026-11-05)**

- **Nivel**: 3 (decisión de producto). **Aprobada con ocho correcciones**, que se aplican en AGR-9 y
  están incorporadas en `docs/ARQUITECTURA-DE-PANTALLAS.md` (apartado 0).
- Queda abierto lo que depende de terceros: el formato de importación de la PAC, los vídeos de
  referencia de David, las regiones/importes de CyL, los valores de los catálogos y las licencias.

### AGR-9 · Aplicar las ocho correcciones al canvas y la doctrina §8 — **HECHO (2026-11-05)**

- **Nivel**: 2.
- **Qué**: el canvas tiene **10 artboards** y `check` con **0 problemas**: Main «Mis tierras» con
  tierras agrupadas por municipio, mapa por zona, zoom y selección, y el panel de la tierra con
  **otros años**; `desktop-alta-tierras` (importar una PAC o a mano, sin prometer formatos);
  `desktop-pac-historico` (años, evolución editable con producción y variedad, traer una PAC);
  `movil-factura-foto` (foto fija y revisión campo a campo); `movil-productos-dosis` (dosis por
  hectárea y total, favoritos); `movil-apuntar` (qué necesita para valer, favoritos); `movil-ficha-parcela`
  (otros años).
- **Doctrina §8 aplicada**: fuera «Ortofoto simulada, sin conexión», la sticky «Datos de ejemplo» y
  todos los textos de desarrollador; barrido con 0 textos técnicos, 0 jerga, 0 sombras y 0 emoji.
- **Para revisar**: el canvas se abre con el enlace que da el Lead; `check` no renderiza (la skill lo
  prohíbe), así que el aspecto real lo ve David.

### AGR-10 · Histórico de la PAC y evolución de una tierra

- **Nivel**: 2 (la parte de canales ya está verificada; queda un formato **pendiente**).
- **Qué**: por tierra, una tabla por campaña (año, cultivo, superficie, variedad y producción estimada
  kg/ha), con las celdas que vienen de la administración distintas de las que se escriben; importar o
  corregir años.
- **Canales verificados el 05/11/2026**: exportación de **recintos por campaña 2023–2026** de la Junta
  (texto/Excel, sin certificado), **Cuecyl `.xlsx`** de la campaña y **S-X en PDF con texto**. **No hay
  fichero oficial de la solicitud PAC declarada**; «Documentos del expediente» y la descarga del
  Cuecyl de años anteriores siguen pendientes.
- **Lo que falta de motor**: que la importación del Cuecyl escriba las **versiones de recinto** de su
  campaña (hoy crea campaña, tierras y cultivos, pero no versiones).
- **Criterio**: lo que no consta queda vacío; el SIGPAC solo da 2025–2026 y la Junta recintos
  2023–2026, y lo anterior se declara; se puede exportar la evolución.

### AGR-11 · Productos, abonos, dosis y favoritos

- **Nivel**: 2.
- **Qué**: elegir producto/abono con la dosis por hectárea (de la etiqueta o la última vez), total
  calculado y favoritos; la dosis no se inventa y el total se distingue de la dosis.
- **Criterio**: un tratamiento se apunta con producto, dosis y total correctos; los favoritos se
  guardan por finca y cuenta; sin dosis conocida, el campo queda vacío y se avisa.

### AGR-12 · Facturas de fotos con revisión campo a campo

- **Nivel**: 2.
- **Qué**: foto → propuesta (proveedor, NIF, número, fecha, base, IVA, total) con revisión campo a
  campo y el original a la vista; si no hay lector, se guarda el justificante y se teclea.
- **Criterio**: nada se guarda sin revisar; lo no leído queda vacío; no se promete precisión (el corpus
  de D08 está aparcado).

### AGR-13 · La doctrina §8 en todos los textos nuevos

- **Nivel**: 1.
- **Qué**: ningún texto nuevo explica cómo está hecha la pantalla ni cómo se calcula un número; los
  textos de desarrollador se borran. Los textos del agricultor siguen en `app/textos.py`.
- **Criterio**: recorrido de textos de las pantallas nuevas y retirada de lo que no sirve para decidir.

### AGR-2 · Armazón nuevo + «Hoy» + «Mis parcelas»

- **Nivel**: 2. **Siguiente en cuanto AGR-1 esté aprobado.**
- **Criterio**: la navegación nueva se recorre en navegador a **390, 1024 y 1440 px**, con los cuatro
  estados (vacío, cargando, error, sin permiso), y **la interfaz anterior sigue sirviendo** hasta que
  la nueva cubra cada recorrido.

### AGR-3 · Traer las parcelas del SIGPAC en lote

- **Nivel**: 2.
- **Qué**: descarga del **GeoPackage por provincia** del FEGA (campaña actual y anterior), caché
  local, y guardar por recinto `uso_sigpac`, `coef_regadio`, `region` y `admisibilidad` (CSP, `float |
  None`: nulo = no consta). Licencia: CC BY 4.0 con cita al FEGA y al Catastro al distribuir recintos.
- **Criterio**: pruebas contra el ejemplo guardado (sin internet) y humo contra el FEGA; un recinto
  de verdad con su mapa y su ficha; ningún dato inventado donde el SIGPAC trae nulo.

### AGR-4 · Correcciones documentales de la investigación

- **Nivel**: 1.
- **Qué**: las seis del apartado 8 de `docs/INVESTIGACION-AGRICOLA.md`: documentar el GeoPackage en
  `docs/SERVICIOS_DEL_SIGPAC.md`; añadir la cita al Catastro y la regla de capas no HVD; documentar la
  vía CyL y su restricción comercial; tipar `Recinto.admisibilidad` como `float | None` (CSP); corregir
  la atribución del «contenido mínimo» (anexo II son 4 apartados); añadir la disposición final novena y
  las exenciones del plan de abonado.

### AGR-5 · Apuntar en 30 segundos (los 8 datos mínimos) y cola sin cobertura

- **Nivel**: 2.
- **Criterio**: un tratamiento apuntado en el móvil en 3 pantallas y ≤8 campos; se puede guardar en el
  móvil y llega solo al recuperar la red; el apunte rechazado se aparta con su motivo; los 3 datos
  restantes (eficacia, observaciones) se completan al cerrar el día sin invalidar el apunte.

### AGR-6 · Paquete PAC: superficies, región y lo que falta

- **Nivel**: 2.
- **Criterio**: por recinto, superficie SIGPAC frente a cultivada, cultivo, región y lo que falta;
  cargar la convocatoria como fuente versionada (hoy `la_fuente` es `null`); enlace al trámite exacto;
  **no se presenta ni se firma desde el programa** (la vía oficial es la app de la Junta con certificado).

### AGR-7 · Preguntar a la administración lo que solo ella puede contestar

- **Nivel**: 3 (depende de terceros).
- **Qué**: licencia del SHP SIGPAC de CyL (CIT); campañas históricas y cupos (FEGA); licencia PNOA
  (IGN); especificación del `.xlsx` del Cuecyl, valores de los catálogos, volcado mensual y código de
  DGC (Junta/FEGA). Las preguntas exactas están en el apartado 7.3 de la investigación.

### AGR-8 · Exportar PDF/Excel y el Cuecyl de ida y vuelta

- **Nivel**: 2.
- **Criterio**: se exporta **lo filtrado** con fecha y fuente; el fichero del Cuecyl se lee, se rellena
  y se vuelve a exportar sin duplicar tierras ni pisar lo escrito (`app/cuaderno_cyl.py` ya lo hace).

## Trabajo anterior (en pausa, por si vuelve)

### 1. D01-R1 · El buzón de rechazos, conectado en las dos orillas — **HECHO (2026-11-04)**

- **Nivel**: 2 (cambia la forma del dato local de rechazos, con migración y reversible). Anotado en `DECISIONES.md`.
- **Por qué era lo primero**: era una **pérdida de datos** en el camino del agricultor. El
  escritor nuevo (`cola.rechazos`, una clave por rechazo) existía pero **no estaba enchufado**, y la
  pantalla seguía leyendo el array compartido `cuedigital.rechazados.<cuenta>`. Dos rechazos
  simultáneos se pisaban: uno desaparecía y **no quedaba ni pendiente ni rechazado**.
- **Qué se ha hecho**: el vaciado escribe con `buzon: cola.rechazos`; `pintarAvisoPendientes` lee del
  buzón (solo los de la cuenta abierta); `crearBuzonDeRechazos.migrarDesde/migrarSiHaceFalta` trae lo
  que quedara en las listas viejas —comprobando antes de borrar, conservando lo corrupto y sin borrar
  si el origen cambia—; el instrumento de aceptación lee las dos formas.
- **Pruebas**: JS **1.228** (eran 1.221; +7), incluida la del enchufe (escribe en una clave propia, no
  en la lista, y la pantalla lo lee de ahí). Recorrido de la cola en Chromium: **9/9**. Python: ver
  cierre de sesión.
- **Pendiente de esta tarea**: nada. La aceptación de dos pestañas sigue en la tarea 3.

### 2. D01-I · Reparar el instrumento de medición de D01 — **HECHO (2026-11-04)**

- **Nivel**: 1.
- **Por qué**: la verificación independiente de la P0 **no se podía correr**:
  - `node docs/revision-2026-10-19/reproducir-cola.mjs` (modo normal) **abortaba**:
    `ReferenceError: duenoDelTurno is not defined` — el arnés extrae `mandarPendientes` de
    `app.js` y no inyectaba sus dependencias actuales (23-25/10). Un `exit 1` por eso se lee como
    «defecto reproducido» sin serlo;
  - `--concurrencia` **sí** corría, pero medía `crearCola`, la cola **de array**, que la aplicación
    **ya no usa para apuntar** (`app.js:447` usa `crearColaPorIntenciones`; `crearCola` solo se
    importa y no se usa). Su `exit 1` ya no acreditaba una pérdida en el camino real.
- **Qué se ha hecho**: se inyectan las dependencias que faltan y **se mide el camino real** (cola por
  intención y buzón de rechazos). `--concurrencia` informa por separado el camino real (veredicto),
  la cola de array (historia, ya no enchufada) y el turno sin IndexedDB (limitación declarada).
- **Evidencia**: `docs/revision-2026-10-19/reproducciones.txt`, sección «04/11/2026 · D01: el
  instrumento, reparado y apuntando al camino real», con la salida completa de los dos modos.
  Veredicto: camino real **conserva las dos intenciones**; el array viejo sigue perdiendo, y se dice.
- **Lo que este instrumento NO prueba** (y por eso existe la tarea 3): dos pestañas reales, `opener`,
  recarga, cierre, caducidad con un POST pendiente, almacenamiento lleno y retorno del dueño.

### 3. D01-A · Aceptación con dos pestañas reales (el cierre de D01) — **SIGUIENTE**

- **Nivel**: 1 (arnés y pruebas); 2 si toca persistencia.
- **Por qué**: es **el criterio que impide cerrar D01** (P0 para el piloto). Falta el arnés:
  `scripts/navegador_cdp.py` maneja **un solo destino** (`_orden` sin `sessionId`).
- **Aceptación**: `Target.createTarget`/`attachToTarget` con `flatten`, `sessionId` en cada orden;
  y el guion de la revisión punto por punto: apuntar/apuntar, apuntar/quitar con barrera tras la
  última lectura, ventanas con `opener`, recarga, cierre, caducidad con un POST pendiente,
  almacenamiento lleno y retorno del dueño.

### 4. D07 · Ciclo de vida de las raíces de React y retención

- **Nivel**: 1.
- **Por qué**: `montajes` 2→102 y `montajesDelMarco` 2→101 en una sesión de 100 transiciones; se
  crea una raíz por montaje y no se desmonta. Dos intentos de arreglo se revirtieron por romper
  reservas: **el tercero empieza por las cinco pruebas de montaje**, no por el registro de raíces.
- **Aceptación**: reservas + cuatro flujos + scroll 16/16; ≥100 transiciones SPA con `timeOrigin`
  constante e identidad de pantalla; registro de raíces creadas/desmontadas/activas; `montajes` y
  `montajesDelMarco` acotados.

### 5. EST · Estabilizar la suite de Python

- **Nivel**: 1.
- **Por qué**: cinco pruebas de recorrido han fallado **en algún momento** bajo la suite entera y
  las cinco pasan solas. Mecanismo localizado: la prueba solo mira `returncode == 0` y
  `«Fallos: 0»`, y es el **guion** el que cuenta un fallo cuando una pantalla no se asienta bajo
  carga. Una suite que falla al azar deja de creerse.
- **Aceptación**: causa reproducida, no solo escondida; la espera es por **señal de la pantalla**
  (no por segundos fijos); N corridas seguidas de la suite completa en verde.

### 6. D02/D03 · Certificar las combinaciones que la revisión no cubrió

- **Nivel**: 1.
- **Por qué**: la revisión del 23/10 da por bueno el trabajo anterior de PAC/identidad y de
  fallo/vacío/permisos, pero **no certifica todas sus combinaciones** (una carrera PAC ya se
  coló una vez).
- **Aceptación**: matriz de casos límite de identidad/evaluación (campaña inexistente, foto repetida,
  corrección concurrente) y de fallo/vacío/permiso, con prueba que falle antes.

### 7. D06-L · Límites de acceso, revocación de sesiones y recuperación de copias

- **Nivel**: 2 (esquema reversible + migración; la validación en despliegue es aparte).
- **Por qué**: el encargo pide límites, revocación y secretos/copias **locales**, y eso **no está
  bloqueado por un proveedor**. Lo que sí está bloqueado es validarlo en un HTTPS/Postgres real.
- **Aceptación**: revocación de sesión con prueba de que el token revocado deja de valer; límite de
  intentos; copia/restauración con ensayo de restauración (ya hay base en `tests/`).

### 8. INV · `INVESTIGACION.md`: gestión documental con firma electrónica (competencia)

- **Nivel**: 1 (investigación; **si la propuesta cambia alcance, es Nivel 3**).
- **Por qué**: la ficha `AGENTE.md` **encarga esta investigación** y el fichero **no existe**. Toda
  investigación termina en fichero con propuesta ejecutable, no en opinión.
- **Aceptación**: qué se miró (con enlace/captura), qué hace la competencia (firma, trazabilidad,
  custodia, verificación), qué nos falta, qué adoptamos y por qué, y **una propuesta concreta de
  tarea Nivel 1/2**.

### 9. DOC · `ESPECIFICACION.md`: el índice vinculante

- **Nivel**: 1.
- **Por qué**: `AGENTE.md` dice «lee `ESPECIFICACION.md`; si no existe, **eso** es la tarea». No
  existe: la especificación real está repartida en `docs/CONTRATO_IMPLEMENTACION_CRM.md`,
  `docs/ESPECIFICACION_DETALLADA_CRM_2026.md`, `docs/MATRIZ_NORMATIVA_CRM.md` y `DESIGN.md`.
- **Aceptación**: un solo fichero que diga qué manda para cada materia, qué está implementado y qué
  no, con enlaces y sin duplicar el contenido.

### 10. IUWS · Catálogos y mapeo de los 18 bloques (parte local)

- **Nivel**: 2 la parte local; **Nivel 3** la prueba autenticada (catálogos tras captcha y entorno
  de la Junta).
- **Por qué**: el descriptor oficial está inventariado (107 bloques, 402 campos, 175 obligatorios)
  pero la exportación oficial sigue pendiente. Lo que no depende de credenciales se puede hacer.
- **Aceptación**: mapeo campo por campo con «de dónde sale», lo que falta marcado como tal, y
  exportación local contra el esquema JSON oficial con prueba.

### 11. D08 · Corpus y proveedor — **APARCADO (04/11/2026, noche)**; la elección de 0 € se queda escrita

- **Nivel**: 2. **Decisión de David**: no va a aportar ahora las 30 facturas con permiso, así que el
  corpus queda **aparcado**. El trabajo hecho (las dos opciones de cada decisión, medidas a coste 0)
  **se queda como está** en [`docs/D08_CORPUS_Y_PROVEEDOR.md`](docs/D08_CORPUS_Y_PROVEEDOR.md) y sirve
  cuando llegue el corpus. **D08 no bloquea nada más.** Escrito en `ESPECIFICACION.md`.
- **Lo que NO se hace ahora**: ni se busca otro corpus, ni se mide el OCR, ni se persigue el asunto.

- **Nivel**: 2 (la propuesta y la elección, con su motivo en `DECISIONES.md`). Contratar un proveedor
  habría sido nivel 3; **no se contrata nada**.
- **Qué se ha decidido**: **corpus** = facturas reales del titular y sus proveedores **con permiso
  escrito** (0 €); **OCR** = Tesseract local (0 €, ya construido); **meteo y satélite** = AEMET
  OpenData + Copernicus Data Space Ecosystem (0 €, con atribución).
- **Por qué esas y no las otras**: la regla pide dos opciones medidas y la más barata que cumpla.
  Documento: [`docs/D08_CORPUS_Y_PROVEEDOR.md`](docs/D08_CORPUS_Y_PROVEEDOR.md), con las dos opciones
  de cada decisión, coste/licencia/límite con URL y fecha (04/11/2026), el uso estimado a partir de
  `datos_representativos.py`, tabla comparativa y elección. Verificado por un revisor independiente.
- **Lo que sigue bloqueado y de quién**: **el material del corpus** —30 facturas (10 PDF del
  proveedor, 10 escaneadas, 10 fotos) con **permiso escrito del emisor** y los **7 valores de patrón**
  de cada una (210 valores)—. Es de David; **no es dinero**. Sin eso, el OCR no se puede medir y D08
  no se cierra.
- **Lo que ya se puede hacer sin esperar**: la tarea 12 (el instrumento listo para el corpus) y la
  tarea 13 (meteo y satélite con el ejemplo guardado y sin clave).

### 12. D08-1 · El instrumento del OCR, listo para un corpus real

- **Nivel**: 1.
- **Por qué**: `scripts/medir_el_ocr_por_campo.py` mide 7 campos sobre una factura **sintética** y llama
  a `ocr.leer_texto` directamente; para medir de verdad tiene que aceptar un **directorio de corpus +
  patrón JSON**, pasar por la **puerta única** (`facturas.texto_del_documento`, que separa PDF con
  texto, escaneo y foto) y comparar con `lectura_evaluada.lo_leido_por_campo` (acertado / fallado / sin
  leer).
- **Aceptación**: el guion acepta corpus y patrón; informa **por campo × formato**; la factura
  sintética sigue pasando **7/7** como humo del propio instrumento; el corpus vive **fuera del
  repositorio**; el guion no sale a internet.

### 13. D08-2 · Meteo y satélite con el ejemplo guardado, y sin clave

- **Nivel**: 2 (módulo nuevo y una variable de entorno; sin tocar esquema).
- **Por qué**: la fuente ya está elegida (AEMET + Copernicus) y se puede construir lo que no depende de
  la clave: una llamada real, su respuesta guardada como ejemplo en `data/` y el analizador escrito
  contra ese ejemplo, como se hizo con el SIGPAC.
- **Aceptación**: atribución visible y en `textos.py`; el dato lleva **estado** (observado / estimado /
  pronóstico), **fuente**, **licencia**, **fecha del dato**, **fecha de consulta** y **resolución**;
  sin clave **se dice y se sigue** (nunca un dato inventado); pruebas **sin internet** contra el
  ejemplo guardado y humo contra el servicio de verdad; endpoint detrás de **sesión y finca** (matriz
  de roles en `docs/QUIEN_ENTRA_EN_LA_FINCA.md`); claves en `CUEDIGITAL_…`, nunca en el repositorio.

## Deuda anotada, no priorizada

- `backend/web/app.js:22` importa `crearCola` y no lo usa (limpieza; arrastra la confusión del
  instrumento de D01). No se ha tocado para no romper las pruebas que aún miden la cola vieja.
- **Arreglado de paso el 04/11**: `tests/test_la_migracion_de_los_nitratos_es_idempotente.py`
  fallaba **solo según la página de códigos de la consola**: el guion de la migración se lanzaba en
  una tubería sin `PYTHONIOENCODING=utf-8` y reventaba al imprimir un carácter fuera de cp1252,
  devolviendo 1 con la migración hecha. Ahora el subproceso va en UTF-8 y, si falla, el test
  **enseña la salida del guion** en vez de solo el código de salida.
- `BUILD`/CI: CI en Windows y Linux configurada en `.github/workflows/ci.yml`, sin resultados
  remotos consultados en este turno.
