# Revisión de la aplicación: qué se ha mirado y qué ha salido

> **Qué es este documento.** David preguntó si hacía falta «alguna revisión más de UI, funcionalidad y
> disposición de páginas y elementos». Esto es esa revisión, hecha **mirando la aplicación de verdad**:
> capturas de un navegador real, con **los datos de su cuenta** (64 tierras importadas del cuaderno de
> la Junta), a tamaño de ordenador y de portátil pequeño.
>
> Cada cosa que sale lleva **qué es** (un fallo, una fase que falta, o un dato que se ve sucio), **la
> prueba** (la captura) y **el arreglo propuesto**, con su prioridad. Nada de «mejorar el aspecto»: lo
> que está aquí se puede comprobar y se puede medir.

## Estado de los ocho puntos (actualizado al terminar la revisión, 30/09/2026)

| # | Qué | Estado |
|---|---|---|
| 1 | A 1024 px el panel se comía la tabla de tierras | **ARREGLADO**: por debajo de 72 rem el panel pasa debajo de la tabla (`estilos.css`), con su prueba en `tests/test_el_armazon_del_ordenador.py` y comprobado con sus 64 tierras a 1024 px |
| 2 | «54 cosas apuntadas dentro» frente a «0 apuntes en el cuaderno» | **ARREGLADO**: el servidor manda el desglose (`apuntes`, `tierras_con_cultivo`, `otras_cosas`) y la pantalla lo dice por su nombre: «0 apuntes · 54 tierras con su cultivo dicho». Con cinco pruebas nuevas en Python y en JavaScript |
| 3 | La frase larga del año dentro de la celda | **ARREGLADO**: en la celda va «Hay cosas dentro»; la frase entera sigue en la ficha del año y en la pantalla que pregunta |
| 4 | El panel de inicio y «lo que falta» son un muro de bloques de móvil | **ARREGLADO** (era la **fase 4**): al entrar desde un ordenador ahora se ve el **panel de mando** —cuatro tarjetas de números, lo que falta con su botón en el mismo renglón, los últimos apuntes y el cierre del año—. En el móvil no cambia nada. Con sus pruebas y comprobado con sus 64 tierras |
| 5 | «Qué hay sembrado» con 64 tierras son 64 tarjetas | **ARREGLADO**: tiene su tabla (Tierra · Hectáreas · Este año hay · Otros años · Estado · Acciones), con el pie «64 tierras · 54 con su cultivo dicho». Con su prueba y su ruta en la comprobación del navegador |
| 6 | Los formularios son una columna de móvil estirada | **PENDIENTE** (es la **fase 5**) |
| 7 | El nombre de las tierras trae dentro las hectáreas y el cultivo | **PENDIENTE**: toca datos suyos y **David no lo ha autorizado**, así que no se ha tocado nada. Queda apuntado con su arreglo propuesto |
| 8 | Detalles sueltos (los tres) | **PENDIENTE** (van con la fase 5) |

Los números del arreglo: **2922 pruebas de Python y 641 de JavaScript en verde**, humo en «todo correcto», la comprobación del navegador con **8 rutas de escritorio** y 44 de móvil, y la versión `2026-09-30-55` (la misma cadena en la caché del service worker).

## Cómo se ha mirado (y cómo se repite)

Con la herramienta de revisión `revision_escritorio.py` (fuera del repositorio, **solo lectura**: entra
en la cuenta, navega y hace capturas; no escribe nada):

1. Entra en la cuenta, mira cuántas tierras y apuntes hay (para saber con qué se está mirando).
2. Recorre los **16 módulos del menú** en un Chrome sin ventana, pulsando de verdad, y comprueba que
   cada ruta encuentra sus botones (si no, la captura sería de otra pantalla).
3. Deja una captura por módulo a **1440×900** (el tamaño del diseño) y, en los cinco con más datos
   dentro, también a **1024×768**, que es el ancho mínimo en el que entra la versión de ordenador
   (64 rem) y por tanto **donde la disposición se rompe antes**.

Con lo que hay en la cuenta el 30/09/2026: **64 tierras**, **0 tratamientos**, **0 productos**, 0
facturas. O sea: lo único con muchos datos son las tierras —que es justo lo que hay que mirar—, y las
tablas del almacén y de facturas solo se han visto con los datos de prueba de la comprobación del
navegador (1-2 filas).

## Lo que ha salido

### 1. A 1024 px de ancho, la tabla de tierras se sale de la pantalla — **FALLO, prioridad alta** ✅ *arreglado*

- **Qué pasa.** Con la ventana a 1024×768 (un portátil pequeño, y el mínimo del diseño), de la tabla de
  tierras solo se ven **Nº, Nombre y Hectáreas**: «Qué tiene este año» y la columna de **Acciones**
  quedan fuera de la vista y hay que desplazar la tabla en horizontal para llegar al botón de cada
  fila. Está en `tierras-1024x768.png` y `tierras-con-panel-1024x768.png`.
- **Por qué.** Las cuentas, medidas: menú 17 rem (272 px) + márgenes 64 px = **688 px de contenido**;
  el panel de al lado se lleva 20 rem (320 px) + 16 px de hueco, así que a la tabla le quedan **352 px**
  cuando su ancho mínimo es **480 px** (30 rem). No cabe, y la tabla se desplaza.
- **Arreglo propuesto (solo CSS).** Dentro del bloque de escritorio, **por debajo de 72 rem (1152 px
  —que es donde 480 + 320 + 16 + 272 + 64 empieza a caber—) el panel deja de ir al lado y pasa debajo
  de la tabla**, a todo el ancho. El agricultor sigue viendo la tabla entera y el panel justo debajo, y
  a partir de 1152 px vuelve la disposición de dos columnas.
- **Prueba que lo impide.** En `test_el_armazon_del_ordenador.py` (las medidas del CSS) y en la
  comprobación del navegador, con una ruta a 1024 px.

### 2. «54 cosas apuntadas dentro» frente a «0 apuntes en el cuaderno» — **FALLO de confusión, prioridad alta** ✅ *arreglado*

- **Qué pasa.** La tabla de los años dice del 2026 **«Tiene 54 cosas apuntadas dentro»**, y la pantalla
  de «mi cuaderno» del mismo año dice **«0 apuntes en el cuaderno»**. Las dos cosas son verdad a la vez
  y el agricultor no puede entenderlo: parece que una de las dos miente. Está en `anos-1440x900.png` y
  `cuaderno-1440x900.png`.
- **Por qué.** El número que enseña el año lo cuenta `_cuantas_cosas_hay_dentro` (`explotacion.py`):
  **todo lo que cuelga de la campaña**, y ahí entra **el cultivo declarado de cada tierra**. Su cuenta
  2026 tiene 54 tierras con el cultivo dicho (64 tierras menos las 10 que faltan) y 0 apuntes.
  El número **es el correcto para lo que se usa** (el guardián que impide borrar un año con cosas
  dentro: si se borrara, se llevarían por delante los 54 cultivos), pero **no vale para enseñarlo como
  «qué tiene dentro»**: lo que el agricultor cuenta como apuntes son los tratamientos, abonos, labores,
  cosechas, análisis y ventas.
- **Arreglo propuesto.** Que el servidor mande **los dos números** —cuántos apuntes del cuaderno y
  cuánto más hay dentro (cultivos, planes, facturas, papeles, firmas)— y que la celda diga qué son:
  «Sin apuntes · 54 tierras con su cultivo dicho». El guardián del borrado sigue usando el total.
  Son dos textos nuevos en `textos.py` y una prueba que compruebe que **la suma cuadra** con el total.

### 3. La frase larga del año dentro de la celda pone las filas altas — **FALLO de forma, prioridad media-baja** ✅ *arreglado*

- **Qué pasa.** En la tabla de los años, la celda «Qué tiene dentro» lleva la frase entera («Aquí
  dentro hay cosas apuntadas: primero quítalas y después podrás quitar el año.») en su etiqueta ámbar,
  y cada fila ocupa dos renglones de alto. Está en `anos-1440x900.png`.
- **Por qué es el mismo fallo que ya se arregló dos veces** («Falta decirlo» en las tierras, «Cuadra» en
  el almacén): una frase de dos líneas dentro de una celda.
- **Arreglo.** En la celda va la etiqueta corta («Hay cosas dentro»), y la frase entera se queda en la
  ficha del año y en la tarjeta del móvil (donde ya está).

### 4. El panel de inicio y «lo que falta por completar» son un muro de bloques de móvil — **FASE 4, prioridad alta**

- **Qué pasa.** El panel (la pantalla de entrada del ordenador) son **ocho botones de ancho completo**
  apilados, y «mi cuaderno» enseña **diez bloques enormes** de «lo que falta por completar», cada uno
  con su frase larga y un botón «Qué hay sembrado» a todo lo ancho. En un monitor de 1440 eso es un
  móvil estirado: se ven tres cosas a la vez donde cabrían veinte. Está en `panel-1440x900.png` y
  `cuaderno-1440x900.png`.
- **Por qué.** Es exactamente la **fase 4** del plan («el panel de mando», que es donde David nota el
  salto) y no está hecha. «Lo que falta por completar», además, es una **lista**: en el ordenador tiene
  que ir en renglones compactos (una tierra por línea, con su botón a la derecha), no en tarjetas.
- **Arreglo.** Fase 4 con el diseño que ya se pidió a Stitch (`docs/stitch/escritorio/panel.png`): cuatro
  números del año, «lo que falta» en lista compacta con su botón, los últimos apuntes y la franja de
  acciones documentales.

### 5. «Qué hay sembrado» con 64 tierras son 64 tarjetas gigantes — **TABLA QUE FALTA, prioridad alta** ✅ *arreglado*

- **Qué pasa.** La pantalla de «qué hay sembrado» enseña una tarjeta grande por tierra (nombre,
  hectáreas, «este año hay», «otros años» y un botón enorme). Con 64 tierras son 64 bloques: en el
  monitor se ven **tres**. Está en `cultivos-1440x900.png`.
- **Por qué.** Esta pantalla **no estaba en la lista de tablas pendientes** (la lista tenía los seis
  maestros, los análisis y las ventas): se quedó fuera y es —después de las tierras— **la lista más
  larga del programa** (una fila por tierra y año).
- **Arreglo.** Añadirla a la fase 2: tabla con **Tierra · Hectáreas · Este año hay · Otros años ·
  Estado («Al día» / «Falta rellenar») · Acciones**, con el pie diciendo cuántas faltan. La tarjeta se
  queda para el móvil, que es donde se lee de una en una.

### 6. Los formularios son una columna de móvil estirada — **FASE 5, prioridad media**

- **Qué pasa.** «Lo que hago sin echar producto» (las diez medidas) son diez renglones de 1150 px de
  ancho con una casilla pequeña a la izquierda, y el botón de guardar queda muy abajo. Lo mismo
  pasará con el asistente de apuntar (que en el móvil es una pregunta por pantalla). Está en
  `medidas-1440x900.png`.
- **Por qué.** Fase 5 del plan (formularios en dos columnas con el resumen al lado), con su diseño ya
  pedido (`docs/stitch/escritorio/formulario.png`).
- **Arreglo.** En el ordenador, las medidas en **dos columnas** (se ven las diez de un vistazo) y el
  resto de formularios en dos columnas con el resumen al lado.

### 7. El nombre de las tierras trae dentro las hectáreas y el cultivo — **DATO, prioridad alta (toca sus datos)**

- **Qué pasa.** Las 64 tierras se llaman así: **«501/10015-1 VEZA VELLOSA (4,44 ha)»**, y ese nombre se
  repite en todas las pantallas. Como además la tabla tiene su columna de hectáreas y su columna de
  cultivo, **el mismo dato sale tres veces** en la misma fila y el nombre se parte en dos o tres
  renglones. Viene de **la importación del cuaderno de la Junta** (que es de donde salieron esas
  tierras), y los decimales vienen con punto («0.46 ha») mientras el programa escribe coma («0,44»).
  Está en `tierras-1440x900.png`, `cultivos-1440x900.png` y `cuaderno-1440x900.png`.
- **Por qué importa.** Es lo primero que se ve en la pantalla más usada, y hace que la tabla parezca
  desordenada cuando el programa está haciendo lo correcto.
- **Arreglo propuesto.** Al **traer las tierras del cuaderno de la Junta**, guardar el nombre **sin** las
  hectáreas ni el cultivo (que ya tienen su campo) y con la coma decimal: «501/10015-1». Para las que ya
  están dentro, un repaso que quite ese añadido del nombre **enseñando antes lo que va a cambiar y
  tierra por tierra** (y que el agricultor pueda dejarlo como está si lo prefiere). **No se toca ningún
  dato suyo sin que él lo vea**: es su cuaderno.

### 8. Detalles sueltos (prioridad baja, se arreglan de paso)

1. **«QUÉ TIENE ESTE AÑO» se parte en dos líneas** en la cabecera de la tabla de tierras
   (`tierras-1440x900.png`). Cabe en una si la columna recibe un poco más de ancho.
2. **El campo de fichero de «traer mis tierras» es el del navegador sin estilo** («Seleccionar archivo
   | Ningún archivo seleccionado»), pequeño y distinto a todo lo demás (`junta-1440x900.png`). El
   diseño pide una caja grande para el fichero.
3. **El botón VOLVER del final de cada pantalla** se repite en el escritorio, donde el menú ya está
   siempre a la izquierda. No estorba, pero es la única cosa de la versión de ordenador que sobra;
   se puede esconder solo en el ordenador (`almacen-1440x900.png`, `anos-1440x900.png`).

## Lo que está bien (y conviene no romperlo)

- **La tabla de tierras a 1440**: 64 filas, columnas alineadas, el pie «64 tierras · …» y el panel de
  al lado con la ficha. Se lee de arriba abajo, que es lo que se pidió.
- **La tabla de los años**: cabeceras que ordenan con su flecha, el estado del año en su etiqueta y el
  pie «3 años en tu cuaderno».
- **El menú lateral**: marca el módulo en el que estás con fondo, barra amarilla y `aria-current`, y la
  barra de arriba dice el año y la cuenta.
- **Nada se ha roto al cambiar de tamaño**: entre 1440 y 1024 el armazón, la barra y las pantallas
  siguen ahí (lo que falla a 1024 es solo el ancho de la tabla, el punto 1).

## Las otras dos pasadas (pendientes)

### Pasada 2: el inventario de páginas y elementos

Un mapa **pantalla por pantalla**: título, qué acciones tiene, **dónde está el botón principal**, cómo se
vuelve, qué información se repite y qué falta. Sirve para dos cosas: encontrar lo que se hace de tres
formas distintas, y **dárselo a otra IA para que opine sin ver el código** (una IA no puede juzgar la
disposición si no sabe qué hay en cada pantalla).

### Pasada 3: la funcionalidad, con la ley delante

Cruzar `docs/LO_QUE_PIDE_LA_JUNTA.md` (los 21 puntos) con lo que hace el programa, y buscar los sitios
donde el agricultor **se queda tirado**: filtros que no existen (buscar dentro del año, filtrar los
apuntes por tierra o por producto), cuadrar el almacén contra las facturas, imprimir el cuaderno en
papel con formato de folio, y los avisos que no tienen salida.

### Y lo que se le puede pedir a otra IA (ChatGPT), que es distinto

No puede ver la aplicación, así que lo que rinde de verdad es darle **el inventario de la pasada 2 y dos
o tres capturas** (una de escritorio, una de móvil y el panel) y pedirle juicio sobre **jerarquía y
disposición**, no sobre el código. Lo que no tiene sentido es pedirle una revisión «a ciegas» de la
interfaz a partir de un resumen de texto: eso ya lo hace este documento.
