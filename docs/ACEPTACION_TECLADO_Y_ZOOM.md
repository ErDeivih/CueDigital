# Aceptación del teclado y del zoom: qué se ha medido, con qué, y qué no

Fecha de este documento: **07/10/2026**.

**Qué es este documento.** El resultado de comprobar, **en un navegador de verdad**, las dos cosas que el
encargo pide y que la comprobación que ya existía no podía hacer: **el recorrido con el teclado** (abrir una
ficha, rellenar un formulario, guardar, cerrar el diálogo y volver, con la tecla correspondiente en cada
paso y mirando **quién tiene el foco**) y **el zoom real al 200 %** (la escala del dispositivo y el zoom de
página). Cada afirmación de aquí lleva su número: el que ha salido de la ejecución, no el que se esperaba.

**Qué NO es.**

* No es una prueba de la suite: los tests no levantan navegadores. Esto es una comprobación a mano,
  repetible, con un servidor de pruebas **de usar y tirar** (puerto **8022**, base en `%TEMP%`).
* **No se ha tocado la base del agricultor** (`backend/cuedigital.db`) ni el servidor del puerto 8000.
* **No se ha tocado `comprobar_en_un_navegador.py`** (la prueba de los 720 px sigue viviendo allí, sin
  cambios míos). En el momento de medir, ese fichero estaba modificado en el árbol de trabajo **por otro
  trabajo en curso**; yo solo lo he leído.
* **No es una prueba de accesibilidad completa.** Aquí se mide el foco, el orden del tabulador y el nombre
  accesible de los controles. **No** se ha usado un lector de pantalla, y lo que no se puede medir desde el
  programa se dice en §6 con sus pasos manuales.

**Cómo se ha hecho.** Con `backend/scripts/navegador_cdp.py`, que abre Chrome sin ventana y lo maneja por
el **protocolo de depuración (CDP)**: es lo único que puede mandar **teclas de verdad** (un `KeyboardEvent`
inventado con `dispatchEvent` no mueve el foco). Todo el recorrido es de teclado: se escribe, se tabula y se
pulsa `Enter`. **El ratón no se usa en ningún momento**: `navegador_cdp.pulsar()`, que manda un clic de
verdad, no se llama ni una vez en este guion.

**Ficheros sobre los que se ha medido** (hash de la copia de trabajo en el momento de las medidas):

| Fichero | Líneas | SHA-256 (12) |
|---|---|---|
| `backend/scripts/navegador_cdp.py` | 397 | `D5D807878770` |
| `backend/web/app.js` | 21894 | `37659C047458` |
| `backend/web/estilos.css` | 2067 | `69AD90C64CD8` |
| `backend/web/react/rutas.js` | 522 | `A3DD83A40F8A` |

**Lo que se ha escrito** (y solo esto):

| Fichero | Qué es | Líneas | SHA-256 (12) |
|---|---|---|---|
| `backend/scripts/comprobar_teclado_y_zoom.py` | La comprobación: el recorrido con teclado y el zoom al 200 %, con su recuento de comprobaciones y de fallos | 1280 | `D2E0B5BE621F` |
| `docs/ACEPTACION_TECLADO_Y_ZOOM.md` | Este informe | 512 | (el del fichero que estás leyendo, que cambia con cada edición: no se pone) |

Se apoya en `backend/scripts/navegador_cdp.py` (la herramienta de CDP, que no se ha tocado: `D5D807878770`) y
su humo es `backend/scripts/humo_cdp.py` (tampoco se ha tocado: `F566F1C4DE1D`).

**El resultado de la ejecución que se cita en todo el documento** (la definitiva, con el fichero en su
versión final):

```
Comprobaciones: 193   Fallos: 0
Hallazgos: 15 medidas, 8 distintos (los mismos salen en cada pasada de zoom)
```

---

## 0. Lo que pedía el encargo, y lo que ha salido

| Lo que pedía | Cómo se ha comprobado | Resultado |
|---|---|---|
| Recorrido con teclado: abrir ficha, rellenar, guardar, cerrar el diálogo y volver | Tres pasadas del recorrido entero (una por cada forma de zoom), con la tecla y **el foco medido** en cada paso, y el guardado comprobado **contra el servidor** | **Hecho, 3 de 3 pasadas completas**; acabaron en `#/?campana=2026&finca=23` (§1) |
| Foco visible | `getComputedStyle` sobre el elemento con el foco, comparado con **el mismo elemento sin el foco** (un clon fuera de la pantalla) | **6 paradas medidas, las 6 con cambio visible**; el detalle y el contraste, en §2 |
| Orden de navegación | Tabulación completa desde el principio: **6 paseos** (las tres pantallas del recorrido, con los dos anchos), con la pantalla **recién cargada** | **Sin saltos de región, anillo cerrado y Mayús+Tab al revés** en los 6; el orden exacto y 3 hallazgos, en §3 |
| Ausencia de controles inaccesibles | Recuento y nombre accesible de todos los `button`, `a`, `input`, `select` y `textarea` visibles, y `tabindex="-1"` | **183 controles contados en 6 pantallas, todos con nombre y ninguno vetado** (§4) |
| Zoom real al 200 %, dos formas | Escala del dispositivo desde el arranque (`--force-device-scale-factor=2`) y zoom de página con **Ctrl+«=» de verdad** | `devicePixelRatio` **2** en las dos; la primera **no cambia el ancho lógico** (1424 px) y la segunda lo baja a **712 px** (§5) |
| La prueba de 720 px, con su alcance | Leída, no tocada | Es una prueba de **adaptación de pantalla**, no de zoom (§5.4) |

---

## 1. El recorrido con teclado, paso a paso

El recorrido es el del encargo y se ejecuta **entero tres veces**: con la escala 1 (1440 px), con la escala
del dispositivo al 200 % y con el zoom de página al 200 %. Los números de esta tabla son los de la primera
pasada; las otras dos dan lo mismo (y lo dicen así sus propias comprobaciones).

Antes de la tabla, dos cosas que hay que saber para leerla:

* **El «diálogo» de esta aplicación no es una ventana modal.** Se midió: en `web/` no hay ni un
  `role="dialog"`, ni un `<dialog>`, ni un `aria-modal`. Lo que hay son **paneles que se abren y se cierran
  en su sitio** (el de anular, con su motivo, su confirmar y su cancelar) y **pantallas que preguntan**
  («¿Seguro que quieres borrarlo?»). El recorrido cierra **el panel de anular**, que es el diálogo que esta
  pantalla tiene.
* **`Escape` no cierra nada**, y se midió por qué: `web/app.js` no tiene **ni un** `keydown`, `keyup` ni
  `keypress` (se buscó: cero coincidencias; tampoco en `web/react/`, ni en `web/nucleo.js`). La única salida
  del diálogo es **tabular hasta su botón**. Es un hallazgo, no un adorno (§8, H3).

| # | Paso | Tecla | Quién tiene el foco (medido) | Qué se comprueba | Qué salió |
|---|---|---|---|---|---|
| 1 | Cargar la pantalla de entrar (`#/`, sin sesión) | — | `BODY` | El foco está donde lo deja el navegador al cargar | **OK** |
| 2 | Primera tabulación | `Tab` | `button#menu-panel[ir-inicio]` «Panel» | Que el foco se mueve (y a dónde) | **OK** |
| 3 | Ir al campo del correo | `Tab` ×24 | `input#correo` | Que el campo es alcanzable con el teclado | **OK** (y **H2**: 24 pulsaciones) |
| 4 | Escribir el correo | teclas | `input#correo` | Que lo escrito **está** en el campo (no puesto por JavaScript) | **OK** — el campo vale el correo de la prueba |
| 5 | Pasar a la clave | `Tab` | `input#clave` | Que el orden del formulario es correo → clave | **OK** |
| 6 | Escribir la clave | teclas | `input#clave` | Que se entra con lo tecleado | **OK** |
| 7 | Pulsar ENTRAR | `Tab` ×1 + `Enter` | `button[entrar]` | Que `Enter` **entra de verdad**: aparece el inicio y queda el token | **OK** |
| 8 | Ir a «Mis cuentas» por el menú | `Tab` ×15 + `Enter` | `button#menu-cuentas[gastos-ver]` | Que el renglón del menú se alcanza con el teclado | **OK** |
| 9 | Abrir la ficha | `Tab` ×27 + `Enter` | `button[gasto-abrir]` «VER ESTE GASTO→» | Que la ficha que se abre **es la del gasto** («Gasóleo para el tractor») | **OK** |
| 10 | Pulsar CORREGIR | `Tab` ×3 + `Enter` | `button[gasto-nuevo]` | Que el formulario se abre **con lo que ya estaba puesto** | **OK** |
| 11 | Ir al concepto | `Tab` ×1 | `input#gasto-concepto` | Que el primer campo del formulario recibe el foco | **OK** |
| 12 | Cambiar el concepto | 23 × `Backspace` + teclas | `input#gasto-concepto` | Que el valor del campo es el texto nuevo, tecleado | **OK** — «Gasóleo de la siega (escala 1 (1440 px))» |
| 13 | Ir al importe | `Tab` ×12 | 11 botones de categoría y luego `input#gasto-importe` | Que el importe es alcanzable **y por dónde se pasa** | **OK** (el orden del formulario, abajo) |
| 14 | Escribir el importe | 6 × `Backspace` + teclas | `input#gasto-importe` | Que el valor es «300,50» | **OK** |
| 15 | Pulsar GUARDAR | `Tab` ×12 + `Enter` | `button[gasto-guardar]` | Que el formulario **se cierra solo** y la ficha vuelve con el concepto nuevo | **OK** |
| 16 | Comprobar el guardado **en el servidor** | — (API) | — | Que el servidor tiene el concepto y **300,50 €** | **OK** — `Gasóleo de la siega (…)`, `300.5` |
| 17 | Abrir el diálogo de anular | `Tab` ×4 + `Enter` | `button[gasto-anular]` | Que la pregunta se abre con su motivo, su confirmar y su cancelar | **OK** |
| 18 | Intentar cerrarlo con `Escape` | `Escape` | (el mismo botón) | Si la aplicación escucha el teclado | **El panel sigue abierto** (medido): es **H3** |
| 19 | Cerrar el diálogo con su botón | `Tab` ×3 + `Enter` | `button[gasto-cancelar]` | Que su botón sí lo cierra y **no se anula nada** (comprobado en el servidor) | **OK** |
| 20 | Volver a la lista | `Tab` ×5 + `Enter` | `button[gastos-ver]` «VOLVER→» | Que se vuelve a la lista de cuentas | **OK** (`#/cuentas`) |
| 21 | Volver al inicio | `Tab` ×10 + `Enter` | `button[ir-inicio]` (el de la pantalla) | Que el recorrido acaba donde empieza | **OK** — acabó en `#/?campana=2026&finca=23` |

**Las tres pasadas acabaron en la misma dirección**: `#/?campana=2026&finca=23` (el inicio, con su año y su
finca). La tercera (zoom de página al 200 %) entra **por la dirección de la pantalla** (`#/cuentas`) en vez
de por el menú, y el motivo está medido: a 712 px ese menú no se dibuja (§5.2 y H4).

### El orden del formulario, medido (no supuesto)

Del campo del concepto al del importe hay **12 pulsaciones**, porque en medio están **los 11 botones de la
categoría del gasto**: «Abono», «Producto para las plagas…», «Semilla», «Gasóleo», «Reparación», «Trabajo de
otro», «Alquiler», «Seguro», «Impuesto», «Cuota», «Otra cosa», y después el importe.

Decirlo importa porque **esta comprobación se equivocó primero aquí**: daba por hecho que después del
concepto venía el importe, escribía «300,50» con el foco en un botón y el navegador lo metía en el campo
anterior, así que el concepto acabó guardado como «…300,50» y el importe en blanco. Se vio porque el
servidor devolvía el concepto con los cinco caracteres de más. Ahora se tabula **hasta el importe** y se
apunta por dónde se pasa.

---

## 2. El foco visible

**Cómo se mide.** `getComputedStyle` sobre el elemento que tiene el foco **y** sobre el mismo elemento *sin*
el foco (un clon suyo, fuera de la pantalla, que se quita en la misma vuelta de JavaScript). Se compara y se
dice **qué cambia**: contorno, sombra, borde, fondo o letra. Hacerlo así es lo que impide que un borde de
siempre —que está con foco y sin él— pase por señal de foco.

**Lo medido** (pasada de la escala 1; las otras dos dan lo mismo):

| Dónde tiene el foco | Qué cambia | Contorno medido | Contraste del contorno |
|---|---|---|---|
| `input#correo` | `contorno`, `borde` | `solid 4px rgb(255, 210, 74)` | **1,44 : 1** sobre el fondo `rgb(255, 255, 255)` |
| `button[entrar]` | `contorno` | `auto 1px rgb(16, 16, 16)` | no se puede (lo pinta el navegador) |
| `button#menu-cuentas` (renglón del menú) | `contorno`, `borde`, `fondo`, `letra` | `auto 1px rgb(16, 16, 16)` | no se puede (lo pinta el navegador) |
| `button[gasto-abrir]` (lista de ordenador) | `contorno` | `solid 3px rgb(255, 210, 74)` | **1,44 : 1** sobre el fondo `rgb(255, 255, 255)` |
| `input#gasto-concepto` | `contorno`, `borde` | `solid 4px rgb(255, 210, 74)` | **1,44 : 1** sobre el fondo `rgb(255, 255, 255)` |
| `input#gasto-importe` | `contorno`, `borde` | `solid 4px rgb(255, 210, 74)` | **1,44 : 1** sobre el fondo `rgb(255, 255, 255)` |
| `button[gasto-guardar]` | `contorno` | `auto 1px rgb(16, 16, 16)` | no se puede (lo pinta el navegador) |

**Qué dice esto, y de dónde sale en el código:**

* Los **campos** (`input`, `select`, `textarea`) llevan un contorno amarillo de 4 px **y** un cambio de color
  de borde: `estilos.css:588-593` (`input:focus{outline:4px solid var(--foco); border-color: var(--verde)}`),
  con `--foco: #ffd24a` en `estilos.css:51`.
* Los **botones** y los **enlaces** no tienen ninguna regla de foco propia: lo único que cambia es el
  contorno que pinta el navegador (`outline-style: auto`). El renglón del menú, además, cambia el fondo
  (`estilos.css:1272-1275`, `.menu-enlace:focus-visible`) y la «VER ESTE GASTO» de la tabla de ordenador
  cambia el contorno por el de la aplicación (`estilos.css:1813-1814`, `.tabla-enlace:focus-visible:
  outline: 3px solid var(--foco)`). **En el móvil esa misma ficha no es un enlace de tabla y vuelve al
  contorno del navegador** (medido: a 712 px, `auto 1px`), lo que significa que **el mismo botón se ve
  distinto según el ancho**.
* **El contraste que sí se puede calcular es bajo: 1,44 : 1.** Es el amarillo `#ffd24a` sobre el blanco del
  fondo de la tarjeta. La WCAG pide 3 : 1 para un indicador de foco (criterio 1.4.11, «contraste no
  textual»). **Lo digo como medición, no como veredicto de incumplimiento**: el anillo va *fuera* del borde y
  se apoya en el fondo de la tarjeta, que es el que se ha medido; lo que no se puede medir desde el programa
  es cómo se ve eso **pintado** a 200 % en una pantalla de verdad, y eso queda en §6.

**Lo que no se puede medir con esto** (y por eso no se afirma): el color **pintado** de un contorno
`outline-style: auto`. El navegador no expone de qué color lo dibuja (suele ser un anillo de dos tonos), así
que para los botones y los enlaces **no hay número de contraste**, solo el hecho de que cambia.

---

## 3. El orden de navegación

**Cómo se mide.** Se carga la pantalla **de nuevo** y se tabula desde el principio, apuntando la secuencia
entera. Dos trampas que costaron una vuelta cada una y que conviene saber:

1. **`document.body.focus()` no pone el foco al principio.** El cuerpo no es enfocable, así que el navegador
   no lo mueve y **Chrome sigue desde el último elemento que tuvo el foco**. La primera versión de esta
   comprobación medía el inicio y le salía «el contenido de la pantalla y luego el menú»: era el foco
   continuando desde donde estaba, no el orden de la pantalla.
2. **React pinta en dos tiempos.** Si se tabula mientras el contenedor se está llenando, se mide una
   pantalla a medias (pasó: el paseo empezó en la pantalla del error, con un solo botón, y siguió por el menú
   recién montado). Ahora se espera a que la firma de la pantalla (controles, controles **visibles**, texto y
   armazón) se repita dos veces seguidas **y haya algo que tabular**, y si el paseo sale con las primeras
   pulsaciones en el cuerpo, **se repite**.

**El orden que sale** (que es el del HTML: `#marco` → `header.cabecera` → `#pantalla`, `index.html:23-38`):

| Pantalla | Paradas | Orden, por bloques |
|---|---|---|
| La pantalla de entrar (1440) | **29** | menú (21) → barra: APUNTAR, A+, Salir (3) → `#correo`, `#clave` (2) → ENTRAR, «Es mi primera vez» (2) → cuerpo |
| El inicio (1440) | **32** | menú (21) → barra (3) → contenido de la pantalla (7: «Qué hay sembrado», los tres botones de apuntar, «Sacar en papel», «Guardar los datos…», «Firmar el cuaderno») → cuerpo |
| La lista de cuentas (1440) | **35** | menú (21) → barra (3) → contenido (10: buscar, «Ver todas», ordenar por fecha, **la ficha del gasto**, los cuatro «Apuntar…», «El banco y los papeles», «Volver») → cuerpo |
| El inicio con el zoom al 200 % (712) | **13** | cabecera del móvil (3: «🌾 Mi cuaderno», A+, Salir) → contenido (8) → cuerpo |
| La lista de cuentas con el zoom al 200 % (712) | **13** | cabecera (3) → contenido (9: buscar, ver todas, **la ficha del gasto**, los cuatro «Apuntar…», el banco, volver) → cuerpo |

La secuencia de la pantalla de entrar, entera (es la que enseña el problema del hallazgo H2):

```
  1. button#menu-panel         «Panel»                      ← el menú del armazón de escritorio
  2. button#menu-cuaderno      «Mi cuaderno»
  …  (los 21 módulos)  …
 21. button#menu-ayuda         «Ayuda»
 22. button[ir-inicio]         «APUNTAR»
 23. button[cambiar-letra]     «A+»
 24. button[salir]             «Salir»
 25. input#correo              «»                            ← el primer campo, 24 pulsaciones después
 26. input#clave               «»
 27. button[entrar]            «ENTRAR→»
 28. button[cambiar-modo-entrar] «Es mi primera vez→»
 29. BODY                                                    ← y vuelve a empezar
```

**Sin trampas.** En las **seis pasadas** (las cinco filas de la tabla; la lista de cuentas a 1440 se mide dos
veces, en las dos primeras pasadas de zoom, y da exactamente lo mismo) la secuencia **se cierra en anillo**:
el último elemento de la pantalla vuelve a llevar al primero, así que **no hay ningún sitio del que no se
pueda salir tabulando** (es la comprobación «el tabulador recorre N paradas y vuelve a la primera»). Además:

* Ninguna pulsación se queda en el mismo sitio (se comprueba que dos paradas seguidas no son el mismo
  elemento).
* **Mayús+Tab recorre la misma lista al revés**, elemento por elemento (las seis pasadas).
* Las **regiones van seguidas**: `armazon → pantalla`, dos cambios como mucho y ninguno de vuelta (el
  segundo es el del anillo, al cerrarse). En el móvil el orden es el mismo con otro reparto: la cabecera y el
  contenido.

**Hallazgos de este apartado:**

* **H2 — En la pantalla de entrar, el formulario está detrás de todo el menú.** Hacen falta **24
  pulsaciones** de `Tab` para llegar al campo «Tu correo», porque el armazón de escritorio se tabula entero
  antes. Ese menú no le sirve de nada a quien todavía no ha entrado (y de hecho sus renglones llevan a
  pantallas que, sin sesión, se pintan vacías: **H5**). En el móvil (712 px) son **3 pulsaciones**, porque
  ese menú no se dibuja.
* **H4 — A 712 px (el zoom de página al 200 %) no se llega a «Mis cuentas» con el teclado.** El menú de
  módulos está en el documento pero `checkVisibility()` es falso (medido), y la pantalla de inicio de ese
  ancho no lleva a las cuentas: sus botones son «He echado producto», «He abonado», «He hecho un trabajo»,
  «Mi cuaderno», «Sacar en papel», «No sé qué pulsar», «Dímelo con la voz» y «Mis parcelas, productos y
  máquinas». En esta comprobación se llega **por la dirección** (`#/cuentas`), que es la única puerta que
  queda a ese ancho, y se dice en el propio informe de la ejecución.

---

## 4. Los controles accesibles

**Cómo se mide.** En cada pantalla se cuentan todos los `button`, `a`, `input`, `select` y `textarea`
**visibles** (`checkVisibility()`) y se les busca el nombre accesible por este orden: `aria-label`, lo que
apunte `aria-labelledby`, `title`, su `<label for>`, la etiqueta que lo envuelve, su propio texto, el `value`
(solo en botones de formulario) y —lo último, y se apunta aparte porque es lo más flojo— el **marcador**
(`placeholder`). Se busca también `tabindex="-1"`.

| Pantalla | Controles visibles | Botones | Enlaces | Campos | Listas | Textos | Sin nombre | `tabindex="-1"` |
|---|---|---|---|---|---|---|---|---|
| La pantalla de entrar | 28 | 26 | 0 | 2 | 0 | 0 | **ninguno** | ninguno |
| El inicio | 31 | 31 | 0 | 0 | 0 | 0 | **ninguno** | ninguno |
| La lista de cuentas (1440) | 34 | 33 | 0 | 1 | 0 | 0 | **ninguno** | ninguno |
| La ficha del gasto (1440) | 29 | 29 | 0 | 0 | 0 | 0 | **ninguno** | ninguno |
| El formulario del gasto (1440) | 49 | 42 | 0 | 7 | 0 | 0 | **ninguno** | ninguno |
| La lista de cuentas (712) | 12 | 11 | 0 | 1 | 0 | 0 | **ninguno** | ninguno |

**183 controles contados en total, todos con nombre accesible y ninguno con `tabindex="-1"`.** No hay
enlaces (`a`) en ninguna de estas pantallas: todo son botones. Tampoco hay ningún control que solo tenga
nombre por el marcador. Y el dato de fondo: **la aplicación no usa `tabindex` en ningún sitio** (se buscó en
`web/`: solo aparece dentro de los ficheros de React de `vendor/`), así que el «vetado» no es una práctica
de aquí.

---

## 5. El zoom, en sus dos formas (que no son la misma)

Las tres cosas que se pueden llamar «zoom» se han medido por separado, y **no valen lo mismo**:

| Qué es | Cómo se pone | `devicePixelRatio` | Píxeles lógicos de la ventana | Qué mide de verdad |
|---|---|---|---|---|
| **Escala del dispositivo** | `--force-device-scale-factor=2` **al arrancar** el navegador (es lo que hace Windows al poner la pantalla al 200 %) | **2** | **1424** (no cambia) | Que cada píxel lógico se pinta con dos físicos. **La pantalla no se recompone**: sale la misma versión de ordenador |
| **Zoom de página** | **Ctrl+«=» de verdad**, 5 pulsaciones (100 → 110 → 125 → 150 → 175 → 200) | **2** | **712** (de 1424) | Que al ampliar **caben menos píxeles lógicos**: la pantalla se recompone como si la ventana midiera la mitad. Es lo que hace el agricultor con Ctrl+«+» |
| **Pellizco** (`Emulation.setPageScaleFactor`, que es lo que usa `navegador_cdp.zoom`) | Por protocolo | 2 (el que hubiera) | **712** (no cambia) | Que **acerca la imagen sin recomponer la pantalla**. **No es el zoom de página** y así se dice |

### 5.1. La escala del dispositivo al 200 %

* El navegador se abre **ya con la escala puesta** (`--force-device-scale-factor=2`), que es como pasa en
  Windows. Medido: `window.devicePixelRatio` = **2**.
* **El ancho lógico no cambia**: la ventana sigue viendo **1424 px** de CSS, así que sigue saliendo el
  armazón de ordenador con su menú de módulos (`#menu-cuentas` dibujado y visible, medido con
  `checkVisibility()`).
* **El recorrido entero funciona igual**: las mismas 27 pulsaciones para abrir la ficha, las mismas 12 para
  llegar al importe, el mismo guardado (comprobado en el servidor) y el mismo final. La lista de cuentas da
  **35 paradas**, exactamente las mismas que a escala 1.
* **Lo que NO mide esto**: que el agricultor vea *más grande* la letra (eso depende del sistema operativo y
  de la pantalla), ni el detalle pintado (subpíxeles, nitidez), ni el tamaño físico de las cosas. Mide que
  la aplicación **se comporta igual** con `devicePixelRatio` 2.

### 5.2. El zoom de página al 200 %

* Se amplía **con la tecla**: `Ctrl` + `=` (el mismo atajo que Ctrl+«+»), **5 pulsaciones**. Medido: de
  `devicePixelRatio` 1 a **2**, y la ventana de **1424 a 712 px lógicos**.
* **La pantalla no se sale de lo que cabe**: `scrollWidth` 704 ≤ `clientWidth` 704 en la lista y en la ficha
  (la regla de la prueba que ya existía, con ±1 px de redondeo).
* **El recorrido entero funciona al 200 %**: entrar (3 pulsaciones al campo del correo), la lista, la ficha,
  el formulario (12 pulsaciones al importe), guardar, el diálogo de anular (Escape no cierra; su botón sí) y
  volver. El guardado se comprobó **en el servidor** también en esta pasada.
* **Lo que mide**: que la pantalla **se recompone** a la mitad de ancho lógico y sigue siendo utilizable —el
  armazón se convierte en la cabecera del móvil, las tarjetas sustituyen a las tablas…—.
* **Lo que NO mide**: cómo se ve de nítido o de grande en una pantalla real a 200 %; eso es del sistema y de
  los ojos de quien mira (§6).

### 5.3. Y el pellizco, que no es ninguna de las dos

Medido con el zoom de página ya puesto: `Emulation.setPageScaleFactor(2)` **no cambia** los píxeles lógicos
que caben (la ventana sigue en 712) y sube `visualViewport.scale` a **2**. Acerca la imagen, no recompone la
pantalla: por eso **no se usa como prueba del zoom de página** y se dice expresamente en la salida del
guion. Es la pieza que usa `navegador_cdp.zoom()`; aquí se ha medido para poder deslindarla.

### 5.4. La prueba de los 720 px que ya existía: su alcance, dicho bien

Vive en `backend/scripts/comprobar_en_un_navegador.py` (sección «4 bis», junto a los 1024 px) y **no se ha
tocado**. Lo que hace: abre la pantalla con `--dump-dom` en una ventana de 720 px (pidiendo 736 por el marco
de 16 px) y comprueba que se dibuja y que se puede apuntar («Apuntar algo de hoy» / «APUNTAR»). Su propio
comentario lo dice con honestidad: *«No es el zoom de verdad —eso solo lo prueba un navegador con la
ampliación puesta—, pero sí es el ancho al que equivale»*.

**Su alcance correcto: es una comprobación de adaptación de pantalla a 720 px CSS**, el ancho al que equivale
una ventana de 1440 px con el zoom al 200 %. Comparte con el zoom de página la consecuencia del **reflujo**
(que la versión de ordenador no quepa y tenga que salir la del móvil), y **no** comprueba nada de lo que hace
que el zoom sea zoom:

* no pone la ampliación (no hay `devicePixelRatio` 2, ni `visualViewport`),
* no mide lo pintado (escala, nitidez, subpíxeles),
* no usa el teclado (ni foco, ni orden, ni `Escape`),
* no mira si un control tiene nombre accesible,
* no comprueba que la pantalla no se salga a *ese* ancho (esa comprobación existe, pero por otro camino y con
  otros anchos).

Por eso las dos pruebas se quedan: **la de 720 px dice que la pantalla se adapta; esta dice que se puede
usar y que el zoom es el de verdad.** No son equivalentes y no se presentan como si lo fueran.

---

## 6. Lo que NO se ha podido automatizar, con sus pasos manuales

Estas cuatro cosas **no** las he podido comprobar desde el programa. Se escriben con sus pasos exactos y con
lo que sí he podido medir; lo que no he visto, no se dice que se haya visto.

### 6.1. El aspecto del foco y del texto pintados al 200 % (nitidez, grosor real, contraste a la vista)

* **Pasos**: abrir la aplicación en Chrome en el ordenador, poner la pantalla de Windows al 200 %
  (Configuración → Sistema → Pantalla → Escala 200 %) y, además, `Ctrl` + `+` hasta el 200 % en el navegador;
  entrar, y recorrer con `Tab` el inicio, la lista de cuentas, una ficha y el formulario. De cada parada,
  anotar: ¿se ve **dónde** está el foco? ¿se distingue el contorno del fondo? ¿la letra sigue siendo legible?
  Repetir con la pantalla al 100 % y el zoom al 200 % solo, que son dos cosas distintas.
* **Lo que yo he podido medir**: los valores declarados y los cambios de estilo (contorno, borde, fondo,
  letra) y el contraste del contorno de la aplicación contra el fondo, **1,44 : 1** (§2). Y que a 200 % de
  zoom la pantalla no se sale de lo que cabe.
* **Lo que no**: si ese amarillo se ve con el sol de frente, si el anillo `auto` del navegador se distingue a
  200 %, y el contraste **pintado** de ese anillo `auto` (el navegador no expone su color). **No presento la
  medición como equivalente a mirarlo.**

### 6.2. Un lector de pantalla (que anuncie el nombre y el estado de lo que tiene el foco)

* **Pasos**: con NVDA (o Narrador) en marcha, entrar en la aplicación y recorrer con `Tab` la lista de
  cuentas y el formulario de un gasto. Se tiene que oír **el nombre de cada botón y de cada campo**, y al
  abrir el panel de anular, su motivo y sus dos botones. En la ficha, `Tab` no puede quedarse en silencio.
* **Lo que yo he medido**: que los 183 controles de las seis pantallas de §4 tienen **nombre accesible** por
  texto, `aria-label`, `title` o su etiqueta, y que no hay `tabindex="-1"`. También que el panel de anular no
  se anuncia como diálogo (no hay `role="dialog"` ni `aria-modal`), así que un lector **no** va a decir «diálogo»: leerá sus textos como parte de la página.
* **Lo que no**: el orden y la forma en que lo lee un lector de verdad. Eso no se puede automatizar aquí.

### 6.3. La vuelta atrás del navegador con el teclado (Alt+←)

* **Pasos**: entrar, ir a las cuentas, abrir una ficha, pulsar `Alt` + `←` (y otra vez), y comprobar en qué
  pantalla se queda y **si el foco sigue en algo razonable** (y no en el cuerpo del documento). Repetir
  después de guardar una corrección, y también dentro del formulario, con un campo a medio rellenar.
* **Lo que yo he medido**: que la aplicación **sí** escucha el historial del navegador —`app.js:5026`
  (`popstate`), y escribe la dirección con `pushState` (`app.js:1090`)—, así que `Alt` + `←` cambia de
  dirección y reconstruye la pantalla; y que **la aplicación no llama ni una vez a `.focus()`** en todo
  `web/` (se buscó: cero coincidencias), así que no recoloca el foco a propósito en ningún sitio. Lo que
  pasa con el foco al volver atrás es, por tanto, lo que decida el navegador.
* **Lo que no**: dónde queda el foco después de `Alt` + `←` en cada caso, que es justo lo que hay que mirar
  a mano.

### 6.4. El móvil de verdad, con su teclado y con el dedo

* **Pasos**: abrir la aplicación en el móvil, entrar, y con un teclado Bluetooth (o con el del sistema)
  recorrer la lista de cuentas y el formulario de un gasto con `Tab` y `Enter`; después hacer lo mismo con el
  dedo. Comprobar que el foco se ve al tabular y que lo que se escribe entra en el campo que toca.
* **Lo que yo he medido**: que a 712 px (que es el ancho lógico que deja el zoom al 200 % y se parece al de un
  móvil) la aplicación funciona y el recorrido se completa, y que el menú de módulos desaparece del teclado
  (**H4**).
* **Lo que no**: un móvil de verdad, su teclado, su lector y su pantalla. El ancho de un móvil (390 px) no se
  ha mirado aquí: eso ya lo mira `comprobar_en_un_navegador.py` a 390 px, que es su trabajo.

---

## 7. Cómo se repite

**Preparar el servidor de pruebas** (una base de usar y tirar, en el puerto 8022; **no** se toca la base del
agricultor ni el servidor del 8000):

```powershell
cd F:\EspacioCodigo\CueDigital\backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\cd-teclado.db"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8022     # en otra terminal
```

**La comprobación entera** (crea su propia cuenta y su propio gasto; no toca nada de nadie):

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe scripts\comprobar_teclado_y_zoom.py http://127.0.0.1:8022
```

**Lo que imprime, en números** (esta es la ejecución que se cita en todo el documento):

```
Comprobaciones: 193   Fallos: 0
Hallazgos: 15 medidas, 8 distintos (los mismos salen en cada pasada de zoom)
Dónde acabó cada recorrido:
  · escala 1 (1440 px): #/?campana=2026&finca=23 — entrar → menú → lista (#/cuentas) → ficha → formulario
    → guardado → pregunta de anular → lista → inicio
  · escala del dispositivo 2 (1440 px lógicos): #/?campana=2026&finca=23 — (lo mismo)
  · zoom de página 2 (712 px lógicos): #/?campana=2026&finca=23 — entrar → dirección → lista (#/cuentas)
    → ficha → formulario → guardado → pregunta de anular → lista → inicio
```

**El `campana=2026` y el `finca=23` son de la cuenta que crea cada ejecución** (el guion se da de alta una
cuenta nueva y le siembra una tierra y un gasto): si se repite, esos números serán otros. Lo que importa es
que **el recorrido acaba en `#/`**, el inicio, con su año y su finca puestos.

Sale con **código 0** si no hay fallos y con **1** si hay alguno (y los lista al final). Si no hay Chrome ni
Edge en la máquina, lo dice y sale con **2**: sin navegador no se puede comprobar ni el teclado ni el zoom.

**Opciones**, para no esperar de más:

* `--solo-escala-1`: solo el recorrido de la escala 1 (1440 px).
* `--solo-zoom`: solo las dos pasadas de zoom.
* `--romper outline` / `--romper nombre`: rompe a propósito una comprobación **dentro del navegador** (no se
  toca ningún fichero) para ver que las comprobaciones pueden fallar.

### Las comprobaciones **pueden** fallar (se ha probado a romperlas)

**Quitando el contorno del foco** (`--romper outline`: se inyecta una hoja de estilos que pone
`outline: none; box-shadow: none` en botones, enlaces y campos):

```
Comprobaciones: 70   Fallos: 3
  [FALLO] el botón de entrar: el foco se ve en button[entrar] — cambia nada
          (contorno «none 3px rgb(13, 43, 24)», sombra «none», borde «3px solid rgb(13, 43, 24)»)
  [FALLO] el botón de abrir la ficha: el foco se ve en button[gasto-abrir] — cambia nada
          (contorno «none 3px rgb(31, 74, 44)», sombra «none», borde «0px none rgb(31, 74, 44)»)
  [FALLO] el botón de guardar: el foco se ve en button[gasto-guardar] — cambia nada
          (contorno «none 3px rgb(13, 43, 24)», sombra «none», borde «3px solid rgb(13, 43, 24)»)
```

Es exactamente lo que se esperaba: son los tres botones cuyo **único** cambio de foco era el contorno del
navegador. Los **campos** siguen en verde, y con razón: en ellos el foco también cambia el color del borde
(`input:focus{border-color: var(--verde)}`), así que hay otra señal. Eso demuestra que la comprobación mide
**el cambio**, no la presencia de un borde cualquiera.

**Dejando un botón sin nombre accesible** (`--romper nombre`: se le quita el texto y sus `aria-label`/`title`
al primer botón de cada pantalla):

```
Comprobaciones: 70   Fallos: 5
  [FALLO] la pantalla de inicio: … sin nombre: ['button[cultivo-ver-todos] «»']
  [FALLO] la lista de cuentas · escala 1 (1440 px): … sin nombre: ['button[gastos-ver-todas] «»']
  [FALLO] la ficha del gasto · escala 1 (1440 px): … sin nombre: ['button[gasto-repartir] «»']
  [FALLO] el formulario del gasto · escala 1 (1440 px): … sin nombre: ['button[gasto-elegir] «»']
  [FALLO] la pantalla de entrar: … sin nombre: ['button[entrar] «»']
```

**Las roturas se deshacen solas**: se hacen en la página, no en el código. El árbol queda como estaba.

### Lo que se ha ejecutado, y lo que no

* Se ha ejecutado **solo este guion**: **17 veces** en total (las que hicieron falta para ajustarlo, las
  definitivas y las cuatro de rotura; cada una deja su salida entera). **No se ha corrido `pytest` ni
  `node --test`**: hay otros agentes trabajando en el árbol y la suite entera no es de esta tarea. El guion
  **no es un test** de la suite (levanta navegadores y necesita un servidor).
* **Lo mío son dos ficheros y nada más**: `backend/scripts/comprobar_teclado_y_zoom.py` y este documento.
  Se dice con nombres porque en este árbol hay **otros trabajos en curso**: el guion aparece en `git status`
  como modificado porque otro agente ha hecho un `git commit` del árbol a mitad de esta tarea (el commit
  `d7a6d36` se llevó una versión intermedia del guion), y `backend/scripts/comprobar_en_un_navegador.py`
  aparece modificado **por otro trabajo, no por mí**.
* No se ha tocado `backend/cuedigital.db`, ni ningún servidor que no fuera el **8022** de la prueba (que se
  levanta y se apaga para esto: no queda ninguno mío en marcha).

---

## 8. Los hallazgos, juntos

Son 8 distintos (15 medidas: los mismos salen en cada pasada de zoom). **Ninguno es un fallo de la
comprobación**: la comprobación mide el teclado y el zoom, y estos son cosas que ha encontrado al medir. Se
listan con lo que se ha medido y con el sitio del código donde está el motivo.

| # | Hallazgo | Medido | Dónde está el motivo |
|---|---|---|---|
| **H1** | Entrar desde la dirección **`#/entrar`** deja al agricultor en **«Esa dirección no lleva a ninguna parte»** aunque la cuenta se haya abierto (la única salida es su botón de volver al principio) | La cuenta se abre (`token` guardado) y la pantalla dice «Esa dirección no lleva a ninguna parte…» | `entrar` **no está en la tabla de rutas** de `web/react/rutas.js`. Esa dirección la abre `humo_cdp.py` (el humo de la herramienta del teclado), así que a quien la use le pasa esto. `comprobar_en_un_navegador.py` abre la dirección pelada (`direccion/`) y por eso no le pasa |
| **H2** | En la pantalla de entrar hacen falta **24 pulsaciones** de `Tab` para llegar al campo «Tu correo» | 24 pulsaciones, medidas; el menú entero (21 renglones) va antes | El armazón de escritorio se dibuja también sin sesión (`web/react/piezas/marco.js`), y el orden del HTML lo pone antes de la pantalla (`index.html:23-38`) |
| **H3** | **`Escape` no cierra el diálogo** (ni ningún otro sitio): hay que tabular hasta su botón | Con el panel de anular abierto, `Escape` lo deja abierto | **No hay ni un `keydown`/`keyup`/`keypress` en `web/`** (cero coincidencias en `app.js`, `web/react/` y `nucleo.js`) y **tampoco hay ni una llamada a `.focus()`**: la aplicación nunca mueve el foco por su cuenta |
| **H4** | Con el **zoom de página al 200 %** (712 px) **no se llega a «Mis cuentas» con el teclado** desde el inicio: hay que escribir la dirección | `#menu-cuentas` existe pero `checkVisibility()` es falso, y el inicio de ese ancho no tiene botón de cuentas | El menú de módulos se esconde por debajo de 64 rem (`estilos.css:1217`, dentro del `@media`) y la pantalla de inicio de ese ancho no ofrece las cuentas |
| **H5** | **Sin sesión, una dirección de dentro pinta la pantalla**: escribir `#/cuentas` con la sesión cerrada dibuja «Mis cuentas», 8 controles y **21 renglones de menú** (con los datos vacíos) | Medido con el token quitado y recargando: vuelve la pantalla de entrar; al cambiar la dirección, se pinta la pantalla igual | El manejador de la dirección (`app.js:5026`, `popstate` → `abrirLaDireccion`, `app.js:1126`) **pinta la pantalla sin mirar el token**; el único sitio que mira la sesión es `arrancar()` (`app.js:21904`), que corre **una vez por carga** |
| **H6** | Los **botones y enlaces no tienen estilo de foco propio**: lo único que cambia es el contorno que pinta el navegador (`outline-style: auto`, 1 px) | Medido en `button[entrar]`, `button[gasto-guardar]` y en la ficha de la lista a 712 px | En `estilos.css` solo hay reglas de foco para los campos (588-593), para el renglón del menú (1272-1275, fondo) y para dos enlaces de tabla (1469, 1813-1814) |
| **H7** | El **mismo botón se ve distinto según el ancho**: la ficha del gasto es un enlace de tabla en el ordenador (contorno amarillo de 3 px, el de la aplicación) y un botón suelto en el móvil (contorno del navegador) | Medido a 1440: `solid 3px rgb(255, 210, 74)`; a 712: `auto 1px rgb(16, 16, 16)` | `estilos.css:1813-1814` (`.tabla-enlace:focus-visible`) frente a la pieza `.boton`, que no tiene regla de foco |
| **H8** | El contraste del contorno de foco de la aplicación es **1,44 : 1** (amarillo `#ffd24a` sobre el fondo blanco de la tarjeta) | Calculado con la razón de contraste de la WCAG sobre los colores que da `getComputedStyle` | `--foco: #ffd24a` (`estilos.css:51`) aplicado como `outline: 4px solid var(--foco)`. **Es una medición, no un veredicto**: el anillo se apoya en el fondo de la tarjeta y lo pintado no se ha podido ver (§6.1) |

### 8.1 Y lo que se ha hecho después de este informe (coordinador, commit `66b9633`)

* **H5 está arreglado**: `abrirLaDireccion` mira el token antes de abrir nada, así que sin sesión se pide
  entrar en vez de pintar la pantalla de dentro. Comprobado en un navegador de verdad
  (`scripts/humo_con_sesion.py`): con el token quitado, `#/tierras` pinta el formulario de entrar.
* **H1 no se arregla, y se explica por qué**: `#/entrar` **no lleva a ninguna pantalla a propósito**. La
  pantalla de entrar es un paso, y una dirección que al recargar deja al agricultor en un formulario a medias
  es peor que no tenerla; hay una prueba que defiende esa decisión (`tests_js/rutas.test.js`, «un paso de un
  formulario no tiene dirección, y eso es una decisión»). Lo que sí se ha corregido es **el guion del
  proyecto que entraba por ahí**: `scripts/humo_cdp.py` entra por `/`, que es la puerta de verdad.
* **H2, H3, H4, H6, H7 y H8 siguen abiertos**, tal y como están medidos aquí. El más claro para el agricultor
  que va con el teclado es **H3** (Escape no cierra el diálogo).
* **Y se ha vuelto a medir después de esos cambios: `193 comprobaciones, 0 fallos`** (sobre `450ab05`), con
  los mismos hallazgos.

---

## 9. Lo que se deja dicho, en cuatro líneas

1. **El recorrido con teclado funciona entero, y está medido paso a paso** (con quién tiene el foco en cada
   uno y con el guardado comprobado en el servidor), también **al 200 %**, en sus dos formas de zoom.
2. **El zoom ya no es una simulación**: la escala del dispositivo se pone al arrancar el navegador
   (`devicePixelRatio` 2, el ancho lógico **no** cambia) y el zoom de página se pone **con la tecla**
   (de 1424 a 712 px lógicos). El pellizco se mide aparte y se dice que no es lo mismo.
3. **La prueba de 720 px se queda como está y con su alcance dicho**: es adaptación de pantalla, no zoom.
4. **Lo que no se puede medir desde aquí está escrito con sus pasos manuales** (§6), y lo que sí se ha medido
   va con su número, no con un «se ve bien».
