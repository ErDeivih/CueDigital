# Estado exclusivo de CUE Digital

> **PARADO A PROPÓSITO el 11/10/2026, por indicación de David** («tenemos que parar, deja documentado la tarea
> para continuar más adelante y para el loop»). **Antes de nada, lee `CONTINUAR-AQUI.md`**: tiene el estado
> medido, lo que se terminó, lo que falta, los comandos y **las diez trampas que ya han costado rondas** (entre
> ellas que `textos.py` usa CRLF y que un `import` que no entra revienta el esquema del proyecto). Nada quedó a
> medias: el último commit está verde (**Python 4813 · 0**, **JavaScript 1088 · 0**) y la base del agricultor
> **intacta**.

Actualizado: 11/10/2026 (CRM-00 EN_REVISION: código cerrado, pendiente la revisión visual). No sustituye el
estado global de los demás proyectos del laboratorio.

- En curso: **CRM-01 (ventas y cobros)**. Inventariado y medido; ver `CRM-01-INVENTARIO.md`. Guion de
  recorrido nuevo: **30 comprobaciones · 0 fallos**. Siguiente paso del ticket: la **tabla de aplicaciones
  del cobro** (el reparto de un ingreso entre varias deudas), que es el criterio que hoy no se cumple.
- **CRM-00 EN_REVISION**: todo su código está hecho, medido y commiteado; lo único que falta es el criterio
  «capturas vistas por un revisor con visión», que **no puede cumplir DeepSeek** (el modelo no acepta
  imágenes). Alternativa manual: las tres capturas están en `F:\EspacioCodigo\CueDigital\docs\capturas\` y
  basta mirarlas —en la de 1440, `APUNTAR`, `A+` y `Salir` tienen que verse enteros a la derecha—.
- Bloqueo declarado aparte: **PostgreSQL** sin entorno para ensayarlo. El SQL de la migración ya es el de
  cada motor (`anulada = false` en PostgreSQL), pero eso acredita el SQL, **no** el comportamiento en ese
  motor; queda como límite y no se promete equivalencia.
- Destino: `F:\EspacioCodigo\CueDigital`.
- Base real: prohibida para pruebas. Referencia de huella en VERIFICACION.
- Dependencias externas: corpus OCR autorizado, fuentes legales vigentes por campaña,
  fuente meteo y proveedor satélite; banco externo fuera del recorrido por fichero.
- Última evidencia: 33 pruebas específicas y 6 del laboratorio verdes (revisor); guion de la ficha de la
  compra **53 comprobaciones · 0 fallos** con la barra corregida (DeepSeek, 11/10/2026).

## Registro que el coordinador debe mantener

| Ticket | Estado | Responsable y ficheros | Evidencia / commit | Próximo paso |
|---|---|---|---|---|
| CRM-00 | EN_REVISION | DeepSeek (código); pendiente revisor con visión | Commits `9b6c37c`, `e492e71`, `e1e0a6a`. Barra: reproducido el defecto (acciones fuera de ventana a 1440) y corregido; guion del navegador **53·0**. Variaciones del papel: 4 pruebas y tabla del tratamiento en el contrato. Legado sin huella: probado. SQL portable. Guardián de texto **sustituido** por dos comprobaciones de comportamiento. Suites: **4750 · 0** Python y **1082 · 0** JS | Mirar las capturas; si la barra está bien, CERRAR |
| CRM-01 | EN_CURSO | DeepSeek (un escritor por fichero). Inventario y plan: `CRM-01-INVENTARIO.md`. Hecho: `app/models.py`, `app/schemas.py`, `app/routers/ventas_api.py`, `app/database.py`, `scripts/comprobar_las_ventas_y_los_cobros_de_punta_a_punta.py`, `tests/test_las_aplicaciones_de_un_cobro.py`, `tests/test_lo_que_no_se_apunta_dos_veces.py`, `docs/CONTRATO_IMPLEMENTACION_CRM.md` | **Reparto hecho**: `aplicaciones_de_cobro` + alta con `aplicaciones` + invariantes (422) + dinero contado por aplicaciones + migración. **33 · 0** en el guion; **8** pruebas del reparto y **6** de los índices, todas verdes; JS **1082 · 0**. Contrato §0 al día. **Falta**: (1) la **pantalla** del reparto — `cobro_nuevo.js` para elegir varias facturas y las aplicaciones en la ficha del cobro y en la de la factura (el servidor ya las manda en `cobro.aplicaciones`)—; (2) los **filtros** de la lista de ventas al volver (`estado.filtroVentas` en memoria, `ventas` fuera de `LISTADOS` en `rutas.js:242`); (3) los **importes en los documentos** (cuaderno PDF/CSV y hoja de la Junta sin importe, precio ni pendiente); (4) la **revisión visual** y las capturas | Terminar (1), (2) y (3), y pasar a CRM-02 |

| CRM-02 | EN_CURSO | DeepSeek (un escritor por fichero); inventario por **subagente de solo lectura** en curso. Depende de CRM-01 (hecho salvo la revisión visual). Informe: `CRM-02-INVENTARIO.md` (cuando llegue) | Encargo de `COLA.md:75-94`: importar extracto por fichero (formato **existente**, sin PSD2 ni credenciales), vista previa aceptadas/rechazadas/duplicadas por fila sin destruir el original, huella del lote e identidad por formato, UI partida (sin conciliar / candidatos) con las aplicaciones y el resto a la vista antes de confirmar, y **deshacer conserva el extracto y libera aplicaciones**. Once criterios de aceptación (fichero repetido no duplica; dos operaciones iguales legítimas se conservan; 1210 → 400+810; documento pagado en dos movimientos; 500 entre cuentas propias no altera ingresos/gastos; desconciliar y reconciliar dejan los mismos saldos; moneda distinta no se suma; no se enlaza deuda de otra explotación; huella del lote; identidad por formato; propuesta no silenciosa) | **Ya tocado en CRM-01**: la conciliación del banco leía la columna vieja del cobro y ofrecía para conciliar un ingreso ya repartido (corregido, con `servicios.lo_cobrado_de_una_factura` y probado en el recorrido) | Inventariar (en curso) y después implementar contra los once criterios |

| CRM-03 | EN_CURSO | DeepSeek; inventario por **subagente de solo lectura** en curso. Depende de CRM-01 (hecho salvo la revisión visual). Informe: `CRM-03-INVENTARIO.md` (cuando llegue) | Encargo de `COLA.md:96-106`: ficha de persona/empresa con **roles múltiples**, NIF opcional, canales, direcciones, notas con autor, trabajos/documentos/saldos; **nombre histórico de los documentos al renombrar**; **homónimos que no se fusionan por nombre** (propuesta y fusión solo confirmada, con auditoría); **actividad y tarea próxima** con fecha y responsable, distinguiendo finalizada / vencida / sin fecha; y **privacidad por permiso** (si no se puede ver el dinero, desaparece también de la respuesta). Aceptación: proveedor que también es cliente; dos homónimos; cambio de razón social; el saldo abre sus registros; contacto inactivo conserva relaciones; notas visibles solo donde corresponden. Referencia: patrón de ficha/actividad de CRM documentado en Odoo o Frappe, **no campañas de marketing** | Nada tocado todavía | Inventariar (en curso) y después medir los seis criterios |

Estados permitidos: LISTO, EN_CURSO, EN_REVISION, CERRADO, BLOQUEADO_EXTERNO.
No marcar CERRADO por documentación sola. Al iniciar, registrar ruta de informes, dependencias,
criterios y propiedad de ficheros. Al terminar, registrar resultado y siguiente LISTO.
Al bloquear, indicar motivo observable, alternativa manual y ticket independiente que continúa.

## Historial

- 11/10/2026: creado el perfil y la cola; verificación de la entrega de compras y del laboratorio.
- 11/10/2026: CRM-00 en curso. Corregida la medición de visibilidad (contención en ventana y en ancestros
  que recortan) y, con ella, reproducido el defecto del revisor. Causa raíz medida: `.boton-principal` trae
  del móvil `flex: 1 1 45%` y dentro de la barra estiraba `APUNTAR` a 536 px, empujando `A+` y `Salir`
  fuera de la ventana; además los botones de la barra medían 35 px, por debajo del suelo de 40 px que fija
  `DESIGN.md`. Corregido en `estilos.css` (2,9 rem y el botón principal sin estirar) y anotado en el
  contrato. La tabla del resumen ya dice 4746/1081. No se ha tocado lógica de compras.
- 11/10/2026: CRM-00 a EN_REVISION. El SQL de la migración se escribe según el motor y una factura legada
  sin huella tiene su caso (se puede verificar el mismo contenido; otro contenido es conflicto y **no se
  inventa la petición perdida**). Las variaciones del papel quedan probadas y documentadas en una tabla del
  contrato: el mismo número y año con **otro total** se apunta con aviso `AL48…` (antes era mudo), a la que
  hay **sin importe** se le dice que lo ponga corrigiéndola (`AL49…`), y el mismo número en otro año no
  avisa. El guardián de texto de la clave de pantalla se sustituyó por dos comprobaciones de comportamiento
  (el arnés de JS aprendió a leer el `FormData`, que antes registraba como `null`). Suites: 4750 · 0 y
  1082 · 0. Pendiente **solo** la revisión visual, que DeepSeek no puede hacer.
- 11/10/2026: **CRM-01, primer paso de la implementación**. Creada la tabla `AplicacionDeUnCobro`
  (`aplicaciones_de_cobro`: cobro, factura, importe, `anulado` + motivo, con índice único filtrado por
  `anulado = 0`), hermana de `AplicacionDeUnPago` y con el patrón que documentan las dos referencias
  estudiadas («documento + tabla hija de aplicaciones; deshacer desvincula y no borra»). Comprobado que no
  rompe nada: las pruebas del dinero de las ventas, las de la revisión T12, las del dinero sin conciliar y
  las de la migración del reenvío siguen en verde. **Falta** que alguien la use: la migración de los cobros
  que ya existen, el alta con reparto (`aplicaciones` en `CobroEntrada`), el `sin_aplicar` derivado, las
  pruebas de las tres cifras del encargo y el guion de recorrido ampliado.
**Y la causa de fondo, encontrada midiendo el navegador (11/10/2026)**: la tabla del escritorio **ya es una
tabla de verdad** —13 columnas, dentro de `.solo-escritorio`, con su contenedor de desplazamiento— pero
**cada fila mide 278 px** en vez de ~32. Con **letra de móvil (18 px) y 13 columnas a 1440 px, a cada columna
le tocan ~110 px**, así que el texto de la celda se parte y **la fila deja de ser una fila y se convierte en un
párrafo**. No es solo que la letra sea grande: **es que con letra de móvil una tabla de 13 columnas no cabe y
se deshace**. Un CRM enseña esas 13 columnas en una línea de 32 px; este enseña tres o cuatro renglones por
pantalla. **Hipótesis fuerte, con la evidencia delante** (13 columnas, 18 px, fila de 278 px, HTML de la fila
mirado): lo que la cierra es **contar en cuántas líneas se parte cada celda**, y eso es lo primero de la
ronda siguiente. El medidor (`scripts/medir_la_densidad_de_la_interfaz.py`) ya mide el `tr` y no la celda
estirada —era un defecto de mi instrumento, y daba 277,9 px por partida doble—.

## Encargo nuevo del dueño del producto (11/10/2026): **la interfaz no lee como un CRM**

Palabras suyas, mirando las capturas de `docs/capturas/`: *«no me gusta nada, no se parece a un CRM normal,
parece una UI para niños pequeños»*. **Es la revisión visual que llevaba rondas esperando, y es negativa**:
se acepta y no se discute.

**Medido antes de proponer nada** (`backend/web/estilos.css`): la causa no es un descuido, es una **decisión**
—tipografía grande y objetivos de 64 px **para el agricultor con guantes en el campo**— aplicada **también al
escritorio**, que es donde se lee como infantil.

| token | hoy | un CRM de escritorio |
|---|---|---|
| `--letra` | **18 px** | 13–14 px |
| `--t-pregunta` / `--t-titulo` | **1,45 / 1,5 rem** (~26–27 px) | 16–18 px |
| `--toque` | **64 px** | filas de 28–32 px |
| `--radio` | **14 px** | 2–6 px |
| fondos | `--aviso-fondo #ffe9a8`, `--fondo-suave #f4f6f3` | grises neutros, el dato manda |

**Lo que decidió el dueño, y son sus palabras:** la **complejidad va en el PC** («que es donde van los CRM»);
el **móvil no es muy necesario**: solo para *subir una factura, un resumen rápido y apuntar un trabajo
fácilmente*. Y dos herramientas: **Stitch** para rediseñar y **REA** para mirar CRM de competencia.

**Y hay una pista que cambia el plan: el proyecto YA tiene diseño de Stitch.** `docs/stitch/` tiene **49
ficheros** —un JSON por pantalla con su HTML y su captura—, las carpetas `escritorio/` y `rediseno/`,
`pantallas.json`, `diseno.json` y **`LO_QUE_FALTA_POR_DISENAR.md`** (17 KB), más un guion
(`scripts/bajar_capturas_de_stitch.py`) que descarga las capturas que Stitch ya hizo. Así que **no hay que
inventar el aspecto: hay que leer el diseño que ya existe y aplicarlo**. En marcha, dos subagentes de solo
lectura: uno para sacar de ahí **los números del sistema de diseño** y qué pantallas faltan, y otro para
conseguir **cifras reales de un CRM** (Odoo/ERPNext; REA solo si hay un objetivo concreto en la máquina, sin
tocar procesos ajenos y sin instalar nada).

**Y la densidad, medida antes y después (11/10/2026, cuatro rondas de trabajo):**

| lo que se mide | antes | **ahora** | el escritorio de Stitch |
|---|---|---|---|
| **fila de la tabla de ventas** | **277,9 px** | **54,2 px** | ~34 |
| ventas por pantalla (1440) | ~4 | **~20** | 20+ |
| cuerpo / título | 18 / 24 px | **16 / 20** | 14 / 20 |
| radio de control | 14 px | **8** | 8 |
| **botón de la pantalla** | 44 px | **34** | 34 |
| celda de acciones (5 botones) | 278 px, botones de 46 | **54 px, botones de 26** | — |
| celda «De dónde» | 232 px (8 renglones) | **una línea** con puntos suspensivos | — |
| armazón | menú 272 · panel 320 | **menú 240 · panel 340** | 240 / 340 |

**Los tres culpables, encontrados midiendo celda por celda** (no leyendo el CSS): los **tokens de móvil**
aplicados al escritorio; la **columna de acciones con cinco botones apilados**; y **un texto largo de verdad**
(una descripción de sitio) partido en ocho renglones dentro de una columna de 100 px. **Ninguno se veía en la
captura: se veía «feo» y no se sabía por qué.**

**Y tres fallos de mi instrumento en este bloque, todos del mismo tipo** (contados porque el producto no
falló ni una vez): (1) el medidor daba la altura de la **celda estirada**, no de la fila; (2) medía el
**primer botón del documento** —el de la cabecera— y por eso me hizo creer dos rondas que un cambio no
funcionaba; (3) puse `min-height: 34px` en un botón que seguía midiendo 44, porque **el alto lo mandan el
relleno y el borde**, no el `min-height`. Los tres se resolvieron **midiendo el elemento concreto**.

**La densidad del escritorio, cerrada y contrastada con CRM reales (11/10/2026).** Las cifras de referencia no
son opinión: el segundo subagente **no encontró ningún CRM en la máquina** —ni instalado, ni en Docker, ni APK,
ni puerto CDP— y lo dijo en vez de rellenar el hueco, así que las sacó del **SCSS que Odoo 17 y Frappe 15
despliegan** y de la documentación oficial de `frappe-ui`, con enlace. Lo que dicen y lo que hay ahora:

| lo que se mide | antes | **ahora** | Odoo 17 | Frappe 15 |
|---|---|---|---|---|
| **ancho del contenido** | **704 px** (44 rem, centrado) | **~1300 px** | ancho completo | barra 224 + tabla |
| **fila de tabla** | 277,9 px | **46,2** | ~37 | **40** |
| **cabecera de tabla** | 50 px | **28,9** | — | **30** |
| cuerpo | 18 px | **16** | 14 | 14 |
| botón de pantalla / de cabecera | 44 / 48 | **34 / 38** | ~33 | **28** |
| radio | 14 px | **8** | 4 | 2–3 / 8 |

**Y el hallazgo más gordo salió del informe de la competencia, no del CSS**: `.pantalla` estaba topada en
**44 rem = 704 px** y centrada —en un monitor de 1440, **menos de la mitad del ancho** con franjas vacías—.
Eso es el patrón de la aplicación de móvil, y con los 18 px de letra es lo que más hacía que una pantalla de
despacho pareciera de teléfono. Medido: 704 → **1402,5 px**. Los formularios de dentro conservan su tope (34
rem) para que una línea de texto no se estire.

**Y hay un sexto punto que el informe deja escrito y conviene no perder**: en un CRM **el color se reserva a
los estados** (la acción primaria de Frappe es `gray-900`, casi negra) y la jerarquía la dan la **tipografía y
la línea de 1 px**, no el color. Aquí la paleta es la misma que la del sistema de diseño del proyecto y **no se
ha tocado**: si se quiere ese tono, es un cambio de otra ronda y con su decisión.

**Cuatro fallos más de mi instrumento en este bloque** (el producto no falló ni una vez): el medidor daba la
altura de la **celda estirada** y no de la fila; medía el **primer botón del documento** (el de la cabecera) y
me hizo creer dos rondas que un cambio no funcionaba; puse `min-height` en un botón cuyo alto lo manda el
**relleno**; y en la cabecera de la tabla el alto lo mandaba **su botón de ordenar**, no el `th`. Los cuatro se
resolvieron **midiendo la propiedad concreta con `getComputedStyle`**, no leyendo el fichero.

**Y una prueba que medía la decisión vieja, actualizada con el motivo (11/10/2026).** La comprobación de
CRM-00 (`scripts/comprobar_la_ficha_de_la_compra_en_el_navegador.py`) exigía **área de toque de 44 px en
todas las anchuras**, y era correcto mientras el escritorio usaba los controles del móvil. Con la densidad
nueva los botones de la barra están en **34 px** —medido—, así que **habría fallado**. Se ha cambiado a: **44
px donde hay dedo (el móvil, que tiene su propia comprobación a 390 px) y 30 px en el escritorio**, con la
decisión del dueño escrita en el propio comentario (*«que la complejidad esté para PC»*). **No es aflojar una
prueba para que pase**: es que medía una decisión que ha cambiado, y la nueva está escrita al lado. Vuelve a
pasar en 1440 y en 1024 (**código 0**).

- 11/10/2026: **ABIERTO — una prueba intermitente, con nombre: `tests/test_la_compra_se_anda_entera.py`.**
  El recuento dijo «4792 recogidas, **1 fallos**» en sus **dos** vueltas y, al correr la suite entera a mano,
  salió **verde**: intermitente. **Y el instrumento era el problema**: el recuento ya escribía un informe XML
  con los nombres de los que fallan y **no los imprimía**, así que hubo que correr la suite otra vez para
  averiguar cuál era y el nombre se perdió. **Arreglado el instrumento** (ahora imprime `FALLA: …` leyéndolo
  del mismo XML, y la extracción se validó contra el XML real sin volver a correr la suite) **y con eso el
  fallo tiene nombre**: el **recorrido de la compra** (`test_la_compra_se_anda_entera`). **No reproduce solo**:
  cuatro vueltas de ese fichero, las cuatro en verde. O sea que **necesita el contexto de la suite entera**
  (estado compartido, orden, o tiempo), y eso es lo que hay que reproducir: correr la suite completa en bucle
  hasta que vuelva a salir y quedarse con la traza. **No se declara nada en verde mientras esto siga vivo**,
  porque una prueba que a veces falla no es una prueba que pasa.
  **Y la causa ya está leída del XML de cuando falló** (11/10/2026, en la misma ronda): no falla la compra,
  falla el **guion del recorrido** al correr como subproceso —
  `subprocess.TimeoutExpired: … comprobar_la_compra_de_punta_a_punta.py … timed out after 600 seconds`—. O
  sea: **el guion no terminó en los 600 segundos** que le da la prueba. Y encaja con lo que esta prueba ya
  tenía escrito de sí misma («con la máquina cargada… el arranque se pasó de los cuarenta y la prueba se puso
  roja **sin que la compra tuviera nada roto**», por lo que el margen se subió a 60 s): es **contención**, no la
  compra —el recuento corre la suite **dos veces seguidas** y yo tenía además otras corridas en marcha—.
  **Y ahora ya dice por qué se quedó** (11/10/2026, ronda siguiente): el `TimeoutExpired` pelado se ha
  cambiado por un mensaje que dice que **no es que la compra esté rota**, si el **servidor sigue vivo**, y
  enseña **lo que el guion llegó a imprimir** y **lo que dijo el servidor**. Demostrado forzando el timeout en
  una **copia temporal** (y borrándola después), que es la misma técnica con la que se comprobó que las tres
  pruebas de CRM-02 podían ponerse rojas. **Y la causa del atasco queda explicada, no supuesta**: el guion
  **sí** pone `timeout=30` en cada llamada al servidor (así que no se cuelga en una sola), y lo que hubo fue
  **carga**: el recuento corre la suite **dos veces seguidas** y yo tenía **además otra suite corriendo**. Es
  decir: **el fallo lo provoqué yo** al paralelizar suites en la misma máquina, no el producto. Se cierra como
  explicado, con el instrumento mejorado para la próxima vez, y con la lección escrita: **no correr dos suites
  a la vez en este equipo**.
- 11/10/2026: **CRM-03, el primer arreglo: el alta y la migración de nombres dejan rastro.** Era el requisito
  pendiente que la revisión del T11 tenía **fichado con líneas exactas** (`docs/REVISION_T11.md:364-368`) y,
  de todo lo que le falta al ticket, **lo más barato**: no hacía falta tabla nueva —`correcciones.py` ya sabe
  apuntar en la auditoría— sino que el alta y la migración **pasaran por él**. Hecho: se expone
  `correcciones.apuntar` (el apunte existía, pero era de guion bajo y llamarlo desde fuera es lo que no se
  debe), el alta guarda sus campos **con la misma forma que una corrección** (`{campo: [antes, ahora]}`) y solo
  los que se escribieron, y la migración guarda **una** fila con el resumen (fichas, enlaces, textos tocados)
  —no una por ficha, que ya la deja el alta de cada una: lo que hay que poder contestar es «¿quién apuntó
  estas veinte de golpe?»—. **Y un detalle que salió al hacerlo**: el parámetro de la migración se llamaba
  `_usuario` porque **no se usaba**; ahora sí, así que pierde el guion bajo, y el **guion** que la llama
  (`scripts/migrar_contactos.py`) se ha actualizado —era el único sitio que lo llamaba—. Prueba nueva que
  **mira la fila de la auditoría** (no la respuesta), exigiendo el autor, la forma del apunte y que un campo
  vacío **no** deje rastro. Suite entera: **4791 · 0**. **Pendiente de este hilo**: la migración tiene el
  rastro puesto pero **sin prueba propia** (el alta sí la tiene).
- 11/10/2026: **CRM-02, las tres pruebas que faltaban, hechas y verificadas por mí.** Las escribió un
  subagente como **único escritor de su fichero** (`tests/test_lo_que_pide_crm_02.py`) y yo las **verifiqué
  antes de commitearlas**: pasan (3 · 0), afirman sobre **números concretos y por identificador**, y —lo que
  importa— afirman sobre **filas de la base** (dos filas de conciliación con `{400, 810}` contra los dos
  papeles, `imputado == 1210.00`, `por_conciliar == "0.00"`, y que los dos movimientos son **distintos**:
  `primero["id"] != segundo["id"]`). Y apliqué mi propia regla: **comprobé que pueden ponerse rojas**,
  invirtiendo una expectativa en una **copia temporal** (no en su fichero) —se puso roja leyendo la fila de
  verdad de la base— y borrando la copia después. Con esto, los criterios (c), (d) y (f) de CRM-02 dejan de
  estar «a medias por falta de prueba». **El subagente no llegó a entregar informe** (lo interrumpí cuando su
  fichero llevaba diez minutos quieto y ya estaba verificado, para que no lo reescribiera después de mi
  comprobación). Suite entera: **4788 · 0**.
- 11/10/2026: **CRM-03 inventariado — y vuelve a corregir el punto de partida: el módulo ya existe y es el
  ticket T11.** Lo que ya cumple **no es poco**: el **nombre histórico** de los documentos al renombrar (con
  `textos_tocados:0` como dato y con pruebas), que **dos homónimos no se fusionan por nombre** (el índice no
  es único **a propósito**, y hay una prueba que **falla si alguien añade la unicidad**), los **roles
  múltiples** (un proveedor que también es cliente) y el **NIF opcional**. Lo que falta, medido: **canales**
  (solo un teléfono y un correo), **direcciones** (una), **notas con autor** (un campo que el `PUT`
  sobreescribe), **trabajos** relacionados (ningún modelo de trabajo con `contacto_id`), **saldos** (no hay
  ninguna función que agregue dinero por contacto, aunque **seis tablas** ya llevan `contacto_id` y **ninguna
  consulta filtra por él**), **tareas/próximas acciones** (no existe) y **privacidad por permiso** (los únicos
  papeles son TITULAR/AYUDANTE y solo gobiernan **quién entra**: el filtro no está **ni en el servidor ni en la
  pantalla**). Y los tres hallazgos que cambian el plan: (1) **T11 ya cubre** lo difícil, así que se **añade**;
  (2) **la auditoría del alta y de la migración** es un hueco **ya diagnosticado con líneas exactas**
  (`docs/REVISION_T11.md:364-368`) y es **el arreglo más barato** —por ahí se empieza—; (3) el permiso por
  materia **no se puede cerrar dentro de CRM-03** sin decidir antes qué permisos hay, porque toca todas las
  puertas que devuelven dinero. Todo en `CRM-03-INVENTARIO.md`, con las 66 + 6 + 47 pruebas que ya existen
  como red de seguridad.
- 11/10/2026: **CRM-02, los dos defectos del inventario, aclarados donde se leen** — y uno **no era un
  defecto**. (1) El comentario del índice único de una línea de extracto decía que «es parcial a propósito: si
  algún día una línea se anula, su clave tiene que quedar libre», pero ese `Index` **no lleva `where`** y la
  tabla **no tiene columna de anulación**: un índice parcial sobre una columna que no existe no se puede
  escribir, así que el comentario prometía algo imposible y quien lo leyera daría por hecho que anular una
  línea libera su clave. Ahora dice la verdad **y deja escrito lo que habrá que hacer** cuando la anulación
  exista (la columna y el `where`, como en el reenvío de facturas). (2) El vínculo de una conciliación
  (`documento_id`) **no lleva clave foránea, y no es un olvido ni se puede arreglar con una**: apunta a
  **tablas distintas** según `clase` (un cobro, una factura nuestra, una factura de compra…), y una clave
  foránea va contra **una** tabla. Es una referencia polimórfica, y lo defiende el **código** por tres sitios
  —`obtener_de_la_explotacion` al conciliar, `revisa_una_conciliacion` devolviendo «es de otra finca» y
  `proponer_conciliaciones` descartando el papel ajeno—, cada uno con su prueba. Queda escrito ahí mismo.
  (La lección de método: el inventario lo apuntó como hueco y **la mitad era cierta** —la base no lo defiende—,
  pero la otra mitad no: no todo lo que falta se arregla añadiendo una restricción.) Banco y migraciones en
  verde; base del agricultor intacta.
- 11/10/2026: **CRM-02, el criterio que no cumplía (la moneda), cerrado y con el defecto reproducido**.
  **Lo primero fue medir, y la medición corrigió mi suposición**: puse la comprobación en la casilla del
  importe, donde una línea con `USD` pegado ya se rechazaba —con un motivo malo, «no se ha podido leer», pero
  se rechazaba—; el defecto de verdad estaba **en la columna de la divisa**, que se ignora en silencio. Y se
  reprodujo: con `Fecha;Concepto;Importe;Divisa` y `1.000,00;USD`, **y un perfil que declara que sin signo el
  dinero entra** —configuración normal—, esa línea se apuntaba como **1.000,00 €** y engordaba los ingresos de
  la campaña. Arreglado en `app/extractos.py`: la columna de la divisa se busca **por el nombre de su
  cabecera** (`divisa`, `moneda`, `currency`…, nunca por su posición) y la fila de otra moneda se **rechaza
  con su motivo** (`moneda_distinta`, con su frase en `textos.py` y su mapa en el router), igual que ya se
  rechazan las letras `C`/`D` del signo porque significan cosas contrarias según el banco. **No se convierte**
  —no hay de dónde sacar el cambio, y `dinero.py` dice que no convierte—: se rechaza, que es lo que el
  criterio pide. **Seis pruebas nuevas** (`tests/test_la_moneda_que_no_es_el_euro.py`), y las tres suites del
  banco, los textos y los gastos en verde. Suite entera: **4783 · 0**.
- 11/10/2026: **CRM-02 inventariado, con dos subagentes de solo lectura.** El inventario **corrige la
  suposición de partida**: el módulo **no está sin tocar** —`CRM-02` no aparece en el repositorio, pero lo que
  describe **es el ticket T20, ya construido**: 5 tablas, 2.293 + 1.987 líneas, una pantalla de 1.156 y
  **91 + 43 pruebas en verde**—. De los **once criterios, seis ya cumplen** (a, b, e, h, i, k), tres están **a
  medias** (c: 1210→400+810 sin prueba en el banco; d: un papel pagado con dos movimientos, sin prueba; f:
  deshacer **y volver a conciliar**, sin prueba) y **uno no cumple**: **g, la moneda** —no hay moneda en
  ninguna tabla y **un importe en otra divisa se lee como euros y se suma**, que es un número mal en
  silencio—. El inventario encontró además **dos defectos que no eran del ticket**: un comentario que promete
  un índice parcial que el código no puede ser (`models.py:1783-1791`) y un vínculo de conciliación **sin
  clave foránea** (`models.py:1870`), con la barrera entre fincas solo en el código. Las **referencias**
  (Odoo/ERPNext, con enlace y cita) confirman las decisiones que ya tenía el programa —la línea del extracto
  es evidencia y no un asiento; deshacer quita contrapartidas y no el movimiento; la propuesta se confirma a
  mano— y aportan dos que no: **el fichero de origen entra en la comparación de duplicados**, y **en N43 no
  hay identificador único por apunte**, así que la estrategia de identidad **no puede ser la misma por
  formato**. Todo en `CRM-02-INVENTARIO.md`, con el plan en orden de dependencia (la moneda primero).
  Suites: Python **4776 · 0**, JavaScript **1086 · 0**.
- 11/10/2026: **CRM-01, las capturas de la pantalla del reparto, hechas** para la revisión visual que no
  puede hacer quien escribe esto. Guion nuevo `scripts/capturar_la_pantalla_del_reparto.py`: monta el caso del
  encargo (350 € que saldan una deuda de 100 y otra de 250), entra **como entra el agricultor** (con su vale
  guardado, no una maqueta) y deja **tres capturas con su tamaño medido**: `cobro-reparto-movil.png`
  (390×1400), `cobro-reparto-escritorio.png` (1440×900) y `cobro-reparto-escritorio-1024.png` (1024×900), en
  `docs/capturas/`. Y comprueba **sin ojos** lo que se puede: una casilla por factura, cada una **diciendo lo
  que le queda por cobrar** (100,00 y 250,00 en el texto de la página), que se pueden marcar a la vez, que se
  explica que sin importe se aplica lo que le queda, y que **ningún control se sale de la ventana en los tres
  anchos**. **16 comprobaciones · 0 fallos.** Lo que sigue sin poder acreditarse aquí: que la pantalla se
  **vea** bien, que es lo que tiene que mirar una persona.
- 11/10/2026: **CRM-01, la pantalla del reparto, hecha** — la última pieza de comportamiento del ticket.
  `cobro_nuevo.js` tiene ahora **una casilla por factura** con **lo que le queda por cobrar** y un importe
  **opcional**: si no se escribe, a cada una se le aplica lo que le queda, que es lo que se quiere casi
  siempre; y el importe se escribe cuando se cobra **menos** de lo que se debe. `guardarElCobro` manda
  `aplicaciones` **cuando hay más de una** marcada y la factura suelta cuando hay una —nunca las dos, que el
  servidor contesta 422 con razón—, y el reparto va en el borrador para que un envío fallido no lo pierda.
  Los tres rótulos nuevos son **del servidor** (`textos.COBRO`), y el guardián de textos en verde.
  **Prueba de comportamiento nueva** (`interfaz.test.js`): las dos facturas del encargo marcadas → al
  servidor llegan **dos aplicaciones** con lo que le queda a cada una, **no** `factura_emitida_id`, y con la
  clave de reenvío. JS **1086 · 0**. **Fallo de instrumento mío, anotado**: usé `document.querySelectorAll`
  para leer las casillas y el `document` de mentira de las pruebas **no tiene selectores** (solo
  `getElementById`), así que la prueba existente del cobro reventó con un `TypeError`; se leen **una a una por
  su identificador**, que es como lee los campos el resto de `app.js`.
- 11/10/2026: **CRM-01, el recorrido prueba el reparto desde las otras pantallas** (sección 7 nueva del
  guion): el dinero **sin asignar de verdad** sale en su lista y el **repartido a mano no**; y en el banco,
  las dos deudas del reparto **no** se ofrecen como pendientes ni el ingreso repartido se ofrece para
  conciliar otra vez. Guion: **39 comprobaciones · 0 fallos** (eran 33). Con el código de antes de los
  barridos, esas seis comprobaciones nuevas **fallan** —que es lo que las hace valer—. **Fallo de instrumento
  mío, anotado**: puse `/api/pendientes` y la puerta real es **`/api/bancos/pendientes`** (el prefijo del
  router es `/api/bancos`), así que la respuesta era un 404 con `detail` y mi bucle recorría las claves de un
  diccionario; ahora el guion **comprueba que la respuesta es una lista** antes de recorrerla, para que un
  camino equivocado se vea como un fallo y no como un `AttributeError`.
- 11/10/2026: **CRM-01, la regla del dinero de un cobro, en un solo sitio**. Estaba escrita tres veces
  (la ficha y la lista de lo que se vende, el margen y la conciliación del banco) y esa es exactamente la
  forma en la que el reparto se quedó sin contar en cinco pantallas. Ahora vive en **`servicios.py`**
  (`lo_cobrado_de_una_factura` y `lo_cobrado_por_factura`, la segunda para recorrer una campaña entera sin
  una consulta por factura) y **los tres sitios llaman ahí**; en `ventas_api` queda el nombre delegando, para
  no tocar sus llamadas. Está en `servicios.py` por el **precedente de la casa**: la regla hermana de las
  compras (`lo_pagado_de_un_gasto`) se mudó allí el 09/10/2026 por el mismo motivo —«una regla, un sitio»— y
  el comentario de `gastos_api` lo decía. Verificado: las siete suites del dinero, el banco y el coste en
  verde, y el guion de recorrido **33 · 0** contra un servidor real.
- 11/10/2026: **CRM-01, el barrido de la columna vieja, hecho — y aparecieron dos sitios más, uno de
  ellos un número.** Buscando en todo `app/` las lecturas de `importe_imputado` y de la columna de la
  factura del cobro aparecieron **dos fuera del módulo de ventas**:
  - **`gastos_api.py` (el margen de lo que se vende)**: sumaba `importe_imputado` agrupando por la columna de
    la factura, así que un cobro repartido entre varias deudas **no contaba en ninguna** y esa venta salía
    **sin cobrar** en la pantalla del margen —el número con el que el agricultor decide qué sembrar—. Ahora
    suma **las aplicaciones**.
  - **`extractos_api.py` (la conciliación del banco, que es de CRM-02)**: por un lado daba la factura por
    **pendiente** aunque estuviera cobrada con un reparto; por otro, el bucle de documentos por conciliar
    buscaba `factura_emitida_id IS NULL`, que en un reparto va vacío **a propósito**, así que ofrecía para
    conciliar **un ingreso ya conciliado a mano y por su importe entero**. Ahora los dos miran las
    aplicaciones y lo que separa «asignado» de «sin asignar» es **tener o no tener aplicaciones**.
  Con esto, **la cuenta de sitios que leían el dato viejo es cinco** (el `cobrado` de la factura, la ficha
  del cobro, la lista del dinero sin asignar, el margen y la conciliación) y **los cinco están corregidos**.
  Suite entera de Python **4774 · 0**, recuentos al día por el recuento real, base del agricultor intacta.
  **Queda pendiente de este hilo**: que la regla del dinero viva en **un solo sitio** (`ventas.py`) y no en
  tres consultas parecidas, que es lo que evita el sexto sitio.
- 11/10/2026: **CRM-01, la tercera vez que aparece el mismo defecto, y cerrada**. Buscando si quedaba algún
  sitio que leyera la columna vieja del cobro apareció uno: **`solo=sin_asignar`** (`ventas_api.py`) filtraba
  por `factura_emitida_id is None`, y en un reparto esa columna va vacía **a propósito** → el agricultor veía
  su ingreso **recién repartido a mano** en la lista del dinero «que todavía no sé de qué factura es», justo
  debajo de la frase que dice que está esperando a que se le diga. Ahora lo que separa los dos casos es
  **tener o no tener aplicaciones**, que es donde vive el reparto, con su prueba (y con un dinero de verdad
  sin asignar al lado, para que la lista no esté vacía por casualidad). Los tres sitios del mismo defecto
  —el `cobrado` de la factura, la ficha del cobro y esta lista— están corregidos y con prueba cada uno.
  Guion de recorrido **33 · 0**; las cinco suites del dinero de las ventas, en verde.
- 11/10/2026: **CRM-01, la ficha de un cobro repartido, arreglada** (defecto real que salió al ir a
  enseñarlo): la ficha miraba `factura_numero`, que en un reparto va **vacío a propósito** —el dinero vive en
  las aplicaciones—, así que un ingreso repartido entre dos deudas decía **«sin factura»**: justo lo contrario
  de lo que acaba de hacer el agricultor. Ahora, cuando el cobro tiene más de una aplicación, la ficha dice
  **a qué facturas va y cuánto a cada una** (`textos.COBRO["repartido_entre"]`, nuevo, porque el rótulo de
  antes dice «Va a **la** factura», en singular); con una sola sigue igual, y sin ninguna sigue diciendo que
  no se sabe de cuál es. **Dos pruebas de React** (`tests_js/react.test.js`, con el HTML estático como las
  demás): el reparto (las dos facturas, sus partes, y que **no** aparece la frase de «no sé de qué factura
  es») y el control (una sola factura y el dinero sin asignar, sin cambios). JS **1085 · 0**, recuentos al día
  y guardianes en verde. **Falta de la pantalla**: poder **elegir varias facturas** al apuntar un cobro
  (`cobro_nuevo.js`), que hoy solo deja una.
- 11/10/2026: **CRM-01, el cuaderno dice por cuánto se vendió**. Las dos salidas del cuaderno
  (`app/routers/cuaderno.py`: `exportar_csv` y el PDF) decían qué se vendió, cuánto y a quién **pero no por
  cuánto** —la mitad que se mira en una inspección— y **ninguna prueba** miraba si el documento llevaba
  dinero. Añadidas las columnas **Importe** y **Precio** (cabeceras, anchos del PDF y las dos filas) con
  `dinero.formatea`, y con la regla de la casa cuando el precio no consta: **«Falta el importe»**, nunca
  `0,00 €` —que sería afirmar una venta de cero euros—. Tres pruebas nuevas (`test_lo_que_no_se_sabe_no_es_cero_en_el_cuaderno.py`)
  que **miran el documento** (el texto del CSV y el del PDF, con `pdfplumber`), no el código de estado.
  **Falta de este criterio**: la **hoja de la Junta** (`app/cuaderno_cyl_exportar.py`), que sigue sin
  importes. Verificado con los nueve ficheros de pruebas que tocan el cuaderno y las ventas, en verde.
- 11/10/2026: **CRM-01, el código muerto, señalado donde está**. `LISTADOS`/`esUnListado` (`rutas.js`) no
  tiene **un solo consumidor** en el programa: su única prueba es la que comprueba que la función hace lo que
  dice. En vez de borrar código ajeno, se ha dejado **escrito encima** —con el dato de la medición— que hoy
  nadie lo usa, que lo que conserva la vista de una lista es que **sus filtros viajen en la dirección**, y que
  no se conecte una lista a `LISTADOS` esperando arreglar sus filtros, porque no los arregla. Es exactamente
  el desvío que me costó una ronda a mí. JS **1083 · 0** y base del agricultor intacta.
- 11/10/2026: **CRM-01, la carrera de la clave de un cobro, arreglada** (y la encontró la suite entera, no
  la prueba sola): dos envíos simultáneos con la misma clave pasaban los dos por la comprobación del código,
  chocaban con el índice único de la base y el `IntegrityError` **salía sin manejar** → el móvil que
  reintentaba recibía un **500** en vez de su cobro. Arreglado como en las facturas de compra: se recoge y se
  contesta el cobro que ya estaba. **Y el `try` tiene que envolver el `flush`, no solo el `commit`** —el
  choque salta al insertar—: medido, con el `try` solo en el `commit` la prueba seguía fallando **2 de cada 6
  vueltas**; envolviendo el `flush`, **8 de 8 en verde**. Recuentos al día: **4770 · 0** Python y **1083 · 0**
  JS, con la suite entera en verde después de todos los cambios de CRM-01 (tabla, migración, router,
  esquemas, pantallas).
- 11/10/2026: **CRM-01, los filtros de la lista de ventas, arreglados**. Medido antes de tocar: `ventas` no
  estaba en `TABLA_DE_LA_PANTALLA` (`app.js:801`), sus filtros vivían en `estado.filtroVentas` sin escribirse
  en la dirección, y **`esUnListado` no lo usaba nadie** en todo el programa (el mecanismo `LISTADOS` está
  declarado y sin conectar: es código muerto que promete una función que no existe — queda anotado, sin
  decidir, en `CRM-01-INVENTARIO.md`). Arreglado por el camino que sí usa la casa: **los filtros viajan en la
  dirección** (`parametrosDeLaPantalla` los escribe, `abrirLaPantalla` los lee) y, al abrir con un filtro
  puesto, **la tabla se vuelve a pedir con él** —la del arranque se pide sin filtros—, porque si no el filtro
  estaría en la dirección y no en la pantalla. **Prueba de comportamiento nueva** (`tests_js/interfaz.test.js`)
  que exige las dos mitades: que la dirección lo lleve y que al volver llegue al servidor. JS: **1083 · 0**.
- 11/10/2026: **CRM-01, el hueco de los índices cerrado**. La revisión independiente había medido que
  **ninguna prueba disparaba** los índices únicos de las ventas (`uq_venta_reenvio`, `uq_cobro_reenvio`,
  `uq_factura_emitida_reenvio`, `uq_ajuste_reenvio` y el nuevo de las aplicaciones). Ya se disparan:
  **6 pruebas nuevas** (`test_lo_que_no_se_apunta_dos_veces.py`, todas en verde) que exigen el
  `IntegrityError` en la segunda fila con la misma clave —venta, cobro y factura emitida por la puerta de
  verdad, ajuste sobre una entrega real, y **dos aplicaciones vivas del mismo cobro contra la misma
  factura**—, más el aislamiento (la misma clave en otra finca), anular liberando la clave (la segunda
  aplicación entra con la primera anulada) y **dos envíos concurrentes** del mismo cobro, que dejan **un**
  cobro y ninguna respuesta opaca. Es el mismo patrón con el que se cerró el duplicado comercial de las
  compras: lo que cierra una carrera es el índice, y hay que hacerlo fallar para demostrarlo.
- 11/10/2026: **CRM-01, el reparto hecho**. Un cobro ya se reparte entre varias deudas: `CobroEntrada`
  acepta `aplicaciones` (una fila por factura, con `AplicacionDeUnCobroSalida` para enseñarlas), con las dos
  invariantes de las referencias comprobadas y dichas con palabras (**Σ aplicaciones ≤ importe** → 422 «no
  se puede repartir más de lo que entró»; **ninguna aplicación > el pendiente de su deuda** → 422 «solo le
  quedan X por cobrar»), y con una factura suelta y un reparto a la vez rechazados. El dinero de una factura
  se cuenta **por las aplicaciones** (también el `cobrado` de su ficha, que sumaba la columna vieja: eso era
  un defecto real que la prueba del reparto destapó —la factura de 100 seguía pendiente—). Los dos sitios
  que decían «esto es T20 y no se hace aquí» están corregidos: el docstring de `Cobro` y este perfil.
  **Probado**: 8 pruebas nuevas (`test_las_aplicaciones_de_un_cobro.py`) y el guion de recorrido en
  **33 comprobaciones · 0 fallos** (350 entre 100/250 con 0 sin asignar; 400 con 350 aplicado → `50,00 €` sin
  asignar; anular el cobro devuelve **las dos** deudas; aislamiento 404). Suites: JS 1082 · 0 y las de
  ventas, T12 y dinero sin conciliar en verde.
- 11/10/2026: **CRM-01 en curso**. Inventariado con una **revisión independiente** (que corrigió y amplió el
  primer reconocimiento: más ficheros de pruebas de los que yo vi, y tres huecos que yo no había medido) y
  con un **informe de referencias** (ERPNext *Payment Entry* y Odoo, documentación oficial; ninguna de las
  dos documenta idempotencia, y el patrón que las dos usan es «documento + tabla hija de aplicaciones con el
  sin aplicar **derivado**»). Guion de recorrido nuevo: **30 comprobaciones · 0 fallos**, con los seis
  criterios de la cola medidos uno a uno. La inconsistencia conocida del **201** en el reenvío de un cobro
  queda **medida y no como fallo**, porque David la aceptó como secundaria «siempre que no cree otra
  operación» —y no la crea: mismo identificador y el dinero sin doblar—.


---

## ESTADO A 14/10/2026 (tras cerrar la Entrega 5)

**Lo entregado del encargo**, con su verificación:

| entrega | estado | su instrumento |
|---|---|---|
| **1 · Saldo del contacto** | **cerrada** | recorrido andado + pruebas de servidor |
| **2 · Canales y direcciones múltiples** | **cerrada** | 19 pruebas + el espejo corregido |
| **3 · Próximas acciones** | **cerrada** | **283 comprobaciones · 0 fallos** en navegador |
| **4 · Permisos por materia** | **cerrada** | 5 pruebas + las puertas con `PuedeModificar`/`PuedeVerLoEconomico` |
| **5 · Fusión de contactos** | **cerrada** | 14 pruebas de servidor + **4 de pantalla** + 19 comprobaciones andadas |
| **6 · Recorrido integrado** | **cerrada** | **36 comprobaciones · 0 fallos** en navegador |
| **CRM-04 · Servicios a terceros** | **el servidor entero**; el almacén, a medias y **con la pregunta hecha** | 9 pruebas + 16 comprobaciones andadas |

**Recuentos**: **4921 pruebas de Python** (0 fallos, medido con el instrumento de la casa) y **1112 de JavaScript** (0 fallos). *El recuento de Python es de antes de las últimas pruebas: hay que volver a ponerlo al día con `poner_al_dia_el_recuento_de_pruebas.py`, y **correrlo solo**, sin nadie más escribiendo.*

**La base del agricultor**: intacta en **todas** las comprobaciones (`CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12`).

### TRABAJO LISTO (se puede empezar hoy, sin depender de nadie)

1. **El movimiento de almacén del CRM-04**, por el camino que ya está medido: `MovimientoDeExistencias` con `origen_tipo = "trabajo_a_tercero"` e `origen_id`. **Falta la decisión (a)/(b)** de la pregunta de abajo para el «qué y cuánto».
2. **CRM-05 (costes, inversiones y economía)**: **el inventario del origen de cada coste y cada ingreso** está corriéndose (`CRM-05-ORIGEN-DE-CADA-COSTE.md`). Con ese informe, el resto del ticket es implementable.
3. **El recuento de Python al día** (y con la máquina para mí solo).
4. **Volver a andar los dos recorridos** después de los últimos arreglos de la fusión (los andados son de antes del arreglo de `apiJson`/`fusionado_con_id`).

### TRABAJO BLOQUEADO (y por qué, y por quién)

| qué | quién lo desbloquea |
|---|---|
| **El «qué producto y cuánto» del insumo del CRM-04** | **el dueño**: ¿se apunta **en el parte** (cómodo, cambia el modelo) o **como movimiento enlazado al trabajo** (menos cambio)? |
| **La revisión visual** (las capturas y los tamaños del contrato) | **una persona con ojos**: ni las verificadoras ni yo aceptamos imágenes. *Está pedido.* |
| **La letra y los botones** (40→34 px y 16→14 px que propuse) | **el dueño**: *no se toca sin autorización específica*, y el encargo lo prohíbe |

**Y lo que NO está bloqueado aunque lo parezca** ✓: *el CRM-05 **no depende** del almacén del CRM-04* — así que **no hay bloqueo general**, solo dos preguntas concretas y **cuatro trabajos listos**.

## LISTA DE TRABAJO, AL DÍA (14/10/2026, tras cerrar el hueco 4 del CRM-06)

### LISTO — se puede empezar hoy, sin depender de nadie

| qué | dónde estoy | nota |
|---|---|---|
| **CRM-07 · insumos, semillas, abonos y máquinas** | **inventario en marcha** (subagente) | su aritmética es **pura** (5 L − 2 − 3 = 0; anular 2 → 2; 2 L en 4 ha → 0,5 L/ha; **sin área → desconocido**; 600 kg en 3 ha con N 15 % → 200 kg/ha y 30 kg N/ha; **P desconocido si falta**) y se prueba sin base de datos |
| **CRM-08 · fiabilidad transversal** | **inventario en marcha** (subagente) | borradores, permisos, edición concurrente, restauración. Dos reglas del contrato que valen su peso: *«no trasladar CTRL+Z a una anulación legal ni deshacer una firma con una tecla»* y *«no último escritor silencioso»* |
| **CRM-11 · paneles integrados y personalización** | sin empezar | depende de *«datos acreditados de sus módulos»* — y los módulos (contactos, notas, tareas, economía) ya están entregados |

### BLOQUEADO — y por qué, con nombre y apellido

| qué | qué falta | quién |
|---|---|---|
| **CRM-06 · la superficie «trabajada»** | **una decisión**: ¿es magnitud propia o es la declarada? La casa la llama *«área trabajada/declarada»* (`versiones_de_recinto.py:11`) y el contrato pide *«declaradas, oficiales y trabajadas separadas»*. **Si es propia, hay migración** | el dueño |
| **CRM-06 · PAC en la ficha** | **una decisión**: ¿qué enseña esa sección? Lo que ya está (referencia SIGPAC, superficie, cultivo declarado), el cuaderno de la Junta, o **ayudas y expediente** — que **hoy no existen en el modelo**. *Ojo: el ticket de verdad del PAC es el **CRM-09*** | el dueño |
| **CRM-09 · preparación PAC** | depende de **CRM-06 y CRM-07**, y pide **consultar fuentes legales por ámbito/año/vigencia** (BOE, FEGA, MAPA, Junta, BOCyL) al implementar las reglas | CRM-07 y fuentes |
| **CRM-10 · meteo y satélite** | depende de CRM-06 y de *«fuente disponible»* | fuente externa |
| **CRM-12 · lectura de papeles evaluada** | *«corpus autorizado»* — no bloquea la entrada manual | el dueño |

### EL RECUENTO, dicho claro ✗

**Los recuentos están 17 por detrás en Python y 1 en JavaScript** ✗ — *mis pruebas de hoy* ✓.
- **`poner_al_dia_el_recuento_de_pruebas.py` está corriendo ahora** ✓ (~1 h, la suite dos veces) y es **el único que debe escribir esos números**: *hacerlo a mano sería el «contador alternativo» que el encargo prohíbe* ✓.
- **Mientras corre, los guardianes de recuento están rojos** ✗ (*comparan README/AGENTS/lista con la realidad* ✓) — y **el script es quien los pone verdes** ✓.
- **Y si al terminar sigue corto** (*porque contó antes de mi última prueba* ✓), **se vuelve a lanzar** ✓, *no se toca a mano* ✓.

### LO QUE DEJÓ HOY (tres commits)

| commit | qué |
|---|---|
| `3dd9b37` | *la tierra como clase de vínculo* — cuatro sitios: la lista, el diccionario `clase → modelo`, **las clases que se sugieren** y **su nombre** |
| `3b2a6ac` | *los papeles pedidos por la tierra* — `GET /bandeja?clase=tierra&entidad_id=N`, con función nueva y aditiva |
| `2590023` | *la sección en la ficha* — la cuarta puerta, la sección copiada de Cultivos y **las frases en los tres sitios** |

## CRM-07 · LOS 12 HUECOS, ORDENADOS POR LO QUE CUESTAN (14/10/2026)

Del inventario medido (`CRM-07-LO-QUE-YA-EXISTE.md`, §8). **Lo que ya está hecho de este ticket es enorme**:
el insumo con producto/lote/autorización separados ✓, el descuento por una sola puerta ✓, la anulación que
revierte sin borrar ✓, los nutrientes calculados aparte con `None` si falta la riqueza ✓, y las cinco
obligaciones de máquina separadas y **sin calcular una sola fecha** ✓ (con una prueba que prohíbe `timedelta`
en ese módulo). **Cuatro suites grandes** (129 + 61 + 59 + 53 pruebas).

| # | hueco | coste | estado |
|---|---|---|---|
| **1** | La composición del abono no se podía dejar en «no consta» desde la pantalla | **pantalla + textos** | ✅ **HECHO** (14/10/2026) |
| **5** | **No hay prueba de que cambiar la etiqueta no cambie el apunte firmado** | **una prueba de comportamiento** | 🔜 **siguiente** (diseñada) |
| **3** | **El total de abono no se puede convertir a kg/ha en el apunte** | **conectar una puerta**: `gastos.abono_por_hectarea` (`gastos.py:871`) **existe, está probada con las cifras del contrato, y no la llama ningún router** ✗ | 🔜 **siguiente** |
| **10** | `ProductoFitosanitario.foto_etiqueta` no lo usa nadie | conectar | listo |
| **11** | La composición del abono no guarda su unidad | **una columna** | listo (migración) |
| **4** | La autorización del producto no se guarda en el apunte (contrato: «vigente/histórica») | **una columna + la copia** (como `dosis_maxima_etiqueta`) | listo (migración) |
| **2** | La semilla no tiene `categoria_semilla` ni comprada/propia | **dos columnas + catálogo + pantalla** | listo (migración) |
| **6** | La aplicabilidad de una obligación no tiene documento ni fecha | **dos columnas** | listo (migración) |
| **7** | La avería no tiene taller, y el coste no está en la ficha de la máquina | columna + clase de vínculo + pantalla | listo |
| **8** | «Horas acumuladas» no se acumulan: es un número a mano | diseño | listo |
| **9** | «Reserva» no existe como cosa visible | pantalla | listo |
| **12** | En PostgreSQL no se ha probado nada de esto | driver + migraciones | **bloqueado**: hace falta un servidor PG |

**El patrón, cuarta vez esta semana**: *lo que falta casi nunca es construir, es **llegar***. El reparto del
CRM-05, el «no consta» del abono, la sección de papeles y ahora `abono_por_hectarea`: **el caso raro ya está
resuelto en el código y lo que falta es poder alcanzarlo.**

### Y lo que está en vuelo (14/10/2026)

- **El recuento de pruebas corriendo** (`poner_al_dia_el_recuento_de_pruebas.py`) — y **el proyecto congelado
  hasta que termine**: *si se edita mientras corre, el número se mueve entre sus dos corridas y el guion sale
  con razón en rojo.* **Medido: 4986 de Python y 1117 de JavaScript** (los documentos decían 4982 y 1112).
- **Un lote sin commitear**: el defecto del envoltorio (la ficha no enseñaba sus papeles), el «pon 0» que se va
  del formulario del abono, **ocho pruebas nuevas**, el guion de captura `capturar_la_ficha_de_una_tierra.py`
  y su captura. *Se commitea cuando el número esté puesto.*
