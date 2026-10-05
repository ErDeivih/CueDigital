# CueDigital como aplicación de gestión (especificaciones nuevas)

> **Qué es este documento.** David lo pidió así el 30/09/2026: *«no está rehecha la ui, sigue siendo muy
> parecida, debe ser responsive para usarse en pc y móvil, no solo móvil. Hacer una versión para pc que
> parezca una aplicación de gestión tipo SAP, porque actualmente no es una app usable de gestión. Vuelve a
> usar Stitch, incluso, como debes rehacer prácticamente todo, empezar de nuevo con las specs,
> funcionalidades, planes, páginas, ui, etc.»*
>
> Esto es esa vuelta a empezar, escrita antes de tocar el diseño. **Lo que ya funciona no se tira**: el
> cuaderno, el registro de la Junta, los cálculos, el sin cobertura y las 3422 + 771 pruebas se quedan. Lo
> que se rehace es **la forma**: qué páginas hay, cómo se navega, qué se ve en un ordenador y qué en un
> móvil, y cómo se ve.

---

## 1. La decisión de fondo: una aplicación, dos formas de usarla

Hoy la aplicación es **una sola columna de 44 rem centrada, con botones de 64 px, y sin un solo
`@media`**: en un ordenador se ve un móvil en el centro de la pantalla. Eso es lo que hay que cambiar.

A partir de aquí, **la misma aplicación** (mismos datos, mismas reglas, mismo servidor) se ve de dos
maneras, y la que se enseña la decide el ancho de la pantalla:

| | **En el despacho (PC)** | **En el campo (móvil)** |
|---|---|---|
| Cuándo se usa | Por la tarde, sentado, con ratón y teclado, para cuadrar el año, revisar números y sacar papeles | De pie, con una mano, con sol, a veces con guantes y sin cobertura |
| Qué se viene a hacer | Ver el estado de todo de un vistazo, filtrar, comparar, ordenar, corregir en masa, sacar documentos | Apuntar una cosa que acaba de pasar, en dos minutos |
| Cómo se navega | **Menú lateral fijo** con los módulos + barra de arriba con la finca, la campaña y el usuario | Pantalla de inicio con seis acciones grandes; cada pantalla tiene su VOLVER |
| Cómo se ve una lista | **Tabla** con columnas, orden, filtros, totales al pie y acciones por fila | **Tarjetas** grandes, una detrás de otra, con lo que hace falta para reconocerla |
| Cómo se ve un dato | **Panel de detalle** al lado de la lista, sin salir de la página | Pantalla propia, con su VOLVER |
| Cómo se teclea | Formulario **en dos columnas**, con el resumen al lado | Un paso por pantalla, una pregunta cada vez |
| Tamaño de los botones | 32-40 px de alto (ratón) | 64 px de alto (dedo, con guantes) |

**La regla que sostiene esto:** los datos, los textos y las acciones son **los mismos** en las dos formas.
Lo que cambia es cómo se colocan. Nada de dos programas que se separan: una página de escritorio que enseña
lo mismo que la de móvil, con los mismos textos del servidor y los mismos `data-accion`, para que el
manejador de clics siga siendo **uno solo**.

---

## 2. Quién la usa

- **David**, agricultor, 64 tierras en una finca de Castilla y León, sin conocimientos de informática.
- **La persona que le ayuda** (hoy, en el programa, con el papel de «ayuda en la finca»).

Lo que esto obliga, y no es negociable:

1. **Nada de datos inventados.** Lo que no se sabe se deja en blanco o se dice «—». Ni un cero que parezca
   un dato.
2. **Todo lo que se pide se explica al lado**, en una frase, y en las palabras del agricultor (nunca
   «campaña», nunca «registro»: «el año», «el apunte»).
3. **Todo aviso lleva su salida.** Una frase que dice que algo falta, sin el botón que lo arregla, no vale.
4. **Nada se pierde sin dejar rastro.** Corregir y borrar queda escrito por dentro (`auditoria`), y lo que
   está en uso no se borra: se dice qué lo usa.
5. **Funciona sin cobertura** para apuntar, y **no** deja apuntes a medias: lo que no se puede hacer sin
   red se dice claro.

---

## 3. Módulos y páginas

Los módulos son los del menú lateral del ordenador. **Todas las páginas de la columna «PC» existen ya o
están pedidas a Stitch en `docs/stitch/escritorio/`**; la columna «móvil» dice si esa página ya existe en
la versión de móvil (**sí**), si es la misma en una columna (**igual**) o si hay que hacerla (**nueva**).

| Módulo | Páginas | Qué se hace | PC | Móvil |
|---|---|---|---|---|
| **Panel** | Panel de mando | Cuatro números del año, lo que falta por completar con su botón, los últimos apuntes, sacar el cuaderno | nueva | sí (es «Mi cuaderno») |
| **Cuaderno** | La tabla de apuntes · Apuntar (producto / abono / trabajo / cosecha) · La ficha de un apunte · Anular un apunte firmado · Firmar el año | Apuntar, buscar, filtrar, comparar, corregir, borrar y anular; firmar el cuaderno del año | nueva + existentes | sí |
| **Tierras** | La tabla de tierras · La ficha de una tierra (con su forma, sus cultivos y sus apuntes) · Alta de una tierra (SIGPAC, mapa o a mano) · Decir qué hay sembrado · Grupos de tierras | Ver y mantener las 64 tierras, decir qué tienen cada año y agruparlas para apuntar de una vez | nueva + existentes | sí |
| **Almacén** | Los números del almacén · La ficha de un producto (compras, gastos, lo que queda) · La cesta | Saber qué se compró, qué se echó y qué queda, con las cuentas a la vista | nueva + existentes | sí |
| **Compras y facturas** | La tabla de facturas · Añadir una factura (leerla o a mano) · La interpretación de lo leído · El papel de la factura · Los papeles del cuaderno | Guardar el papel que demuestra la compra, y que sus líneas cuadren con el almacén | nueva + existentes | sí |
| **Análisis** | La tabla de análisis · Apuntar un análisis · El boletín del laboratorio · El plan de abono del año | Los números del laboratorio y la previsión de abono, que la ley pide desde 2026 | nueva + existentes | sí |
| **Ventas** | La tabla de ventas · Apuntar una venta | De dónde salió cada partida: producto, kilos, comprador y albarán | nueva + existentes | sí |
| **Productos y máquinas** | Las seis fichas (productos, abonos, quién aplica, quién asesora, máquinas, naves) | Dar de alta lo que se usa, una vez, y corregirlo cuando cambia | nueva + existentes | sí |
| **Años del cuaderno** | La tabla de años · Corregir un año · Empezar un año nuevo | Los años del cuaderno, cuál se está llevando y qué tiene cada uno dentro | nueva | **nueva** (hecha el 30/09) |
| **La Junta** | Sacar el cuaderno (el fichero) · Traer las tierras del cuaderno de la Junta · Lo que pide la Junta | Mandar el cuaderno y traer las tierras sin teclearlas | nueva + existentes | sí |
| **Ayuda y datos** | Mis datos y mi finca · Quién entra en mi finca · La ayuda · Lo que obliga la ley | Los datos del titular, quién más apunta, y las respuestas a «¿esto es obligatorio?» | nueva + existentes | sí |

**Trece módulos, y ninguna página se pierde**: las que ya existen se colocan dentro del módulo que les toca.
Lo único que desaparece es la pantalla de inicio con seis botones **en el ordenador** (ahí manda el menú);
en el móvil se queda, porque ahí sí es la mejor entrada.

---

## 4. Los tres flujos que tienen que salir bien

### 4.1 Apuntar un tratamiento (el que más se usa)

| Paso | En el móvil | En el ordenador | Criterio de aceptación |
|---|---|---|---|
| 1 | Inicio → «HE ECHO PRODUCTO» → elegir tierra (tarjetas) | Menú → Cuaderno → «APUNTAR» → elegir tierra (lista con buscador) | Se elige la tierra en dos toques/dos clics, y se ve cuál está elegida |
| 2 | Fecha (con HOY y AYER), hectáreas (se rellenan solas) | Igual, dentro del formulario de dos columnas | El número de hectáreas viene puesto con la superficie de la tierra y se puede cambiar |
| 3 | Producto, dosis y unidad | Igual | El plazo de seguridad se ve **antes** de guardar: «Hasta aquí no puedes coger la cosecha» |
| 4 | Quién aplica, máquina, medidas previas, observaciones | Igual | Los cuatro son opcionales y se pueden dejar en blanco |
| 5 | Resumen y «APUNTARLO» | Resumen al lado, siempre visible, y «APUNTARLO» | Lo apuntado se ve en una pantalla de confirmación con DESHACER y CORREGIR |

### 4.2 Corregir o borrar algo que ya está apuntado

Ya está hecho y **no se toca** (rondas 91-93): cada ficha tiene **CORREGIR** y **BORRAR**; corregir abre el
mismo formulario con lo que había; borrar **pregunta antes** y enseña lo que va a desaparecer; lo que está
en uso contesta «esto lo usa N apuntes»; un apunte firmado no se borra, se anula.

Lo que cambia con el rediseño: en el ordenador, esas dos acciones van **en la fila de la tabla**, y la
pregunta de borrar sale **en el panel de al lado**, sin cambiar de página.

### 4.3 Empezar el año y sacar el cuaderno

1. Menú → Años del cuaderno → «EMPEZAR UN AÑO NUEVO» → el año propuesto y sus fechas → guardar.
2. Durante el año, el selector de campaña de la barra de arriba dice en qué año se está apuntando.
3. Menú → La Junta → «SACAR EL CUADERNO» → el fichero, y «FIRMAR EL CUADERNO» cuando esté revisado.

**Criterio de aceptación:** el año que se está llevando se ve **siempre** en la barra de arriba, y ningún
apunte puede acabar en un año que no sea el suyo sin que se vea.

---

## 5. Lo que NO se cambia (y por qué)

Estas cosas son decisiones del proyecto, están probadas y el rediseño no las toca:

1. **Los textos los sirve el servidor** (`textos.py`) y ninguna pantalla escribe una frase para el
   agricultor. Hay una prueba que lo comprueba frase por frase.
2. **Los colores viven en el `:root`** de `estilos.css`. Ningún componente pone un color.
3. **Un solo manejador de clics**, en `document`, que lee `data-accion` y `data-*`.
4. **Los formularios son no controlados**: los campos los pinta React con su `id` y los lee `app.js`. Es lo
   que permite que las pruebas escriban como lo haría una persona.
5. **Sin cobertura se puede apuntar** (cola en el móvil); corregir y borrar necesitan red y lo dicen.
6. **Nada de datos inventados** y **ningún aviso sin salida**.
7. **El cuaderno de la Junta** y su formato (`iuws`) no se tocan.

---

## 6. El plan, por fases

Cada fase termina con las pruebas en verde y con la comprobación en un navegador de verdad, que ya existe
(`scripts/comprobar_en_un_navegador.py`).

| Fase | Qué se hace | Cómo se sabe que está bien |
|---|---|---|
| **0. Especificaciones** (esta) | Este documento, y los diseños de escritorio pedidos a Stitch | Este documento existe y los diseños están en `docs/stitch/escritorio/` |
| **1. El armazón — HECHA el 30/09/2026** | Una plantilla de aplicación con **menú lateral y barra de arriba** para el ordenador; en móvil, la cabecera de siempre. La pantalla deja de ser una columna de 44 rem en pantalla ancha | Hecho y comprobado: en 1440 px se ve menú + barra + la pantalla con todo el ancho; en 500 px se ve exactamente como antes. Ver «Lo que trajo la fase 1», aquí debajo |
| **2. Las tablas — EMPEZADA el 30/09/2026** | Las listas (tierras, apuntes, facturas, análisis, ventas, maestros, años) pasan a **tabla** en el ordenador: columnas, orden, filtros, totales al pie, acciones por fila | **Hechas seis**: la de **tierras** (64 filas, orden por cabecera, total de hectáreas), la del **cuaderno** (los apuntes del año), la de los **años del cuaderno**, la de las **facturas** (con su columna de papel y el total del año al pie), la del **almacén** (con lo comprado, lo echado y lo que queda) y la de **qué hay sembrado** (30/09/2026: una fila por tierra, con lo de este año y lo de los anteriores). Faltan las demás listas, que ya tienen la pieza hecha |
| **3. Los paneles de detalle — EMPEZADA el 30/09/2026** | Ficha al lado de la lista, sin cambiar de página, con CORREGIR y BORRAR ahí mismo | Elegir una fila enseña su ficha al lado; en móvil sigue abriendo su pantalla. **Hechos dos**: el de una **tierra** (sus datos, lo que le falta y su botón de decir qué tiene) y el de un **producto del almacén** (sus cuentas, de dónde sale lo comprado y su motivo) |
| **4. El panel de mando — HECHA el 30/09/2026** | La página de entrada del ordenador: cuatro números, lo que falta, los últimos apuntes | **Hecha y comprobada**: al entrar desde un pc se ve el panel de mando —cuatro tarjetas (**Apuntes este año**, **Hectáreas tratadas**, **Lo que has vendido** y **Tus tierras**, esta última diciendo a cuántas les falta su cultivo—, **lo que falta por completar** con su botón en el mismo renglón, **los últimos apuntes** en una tabla corta con el enlace a la lista entera, la fila de **apuntar algo de hoy** y el bloque de **cierre y trámites** (el cuaderno en papel, los datos en un fichero y la firma). En el móvil no cambia nada: los seis botones de siempre siguen ahí. Ver «Lo que trajo la fase 4», aquí debajo |
| **5. Los formularios** | Alta y corrección en dos columnas con el resumen al lado | Apuntar en el ordenador se hace sin bajar de la primera pantalla |
| **6. Las pantallas que faltan** | Ventas, análisis, almacén, plan de abono y la Junta, con la misma estructura | Cada módulo del menú lleva a algo que funciona |
| **7. Repaso** | Móvil completo otra vez, `DESIGN.md` con la parte de escritorio, y los números de la documentación | Todas las pruebas, `humo` y navegador en verde |

## 6 bis. Lo que trajo la fase 1 (30/09/2026)

Lo que ya está hecho y comprobado, para que nadie lo vuelva a hacer:

1. **El armazón** (`react/piezas/marco.js`): el menú lateral con los 16 módulos y la barra de
   arriba. Se monta **fuera** del contenedor de las pantallas (`#marco`, en `index.html`) y solo
   cuando cambia el módulo, para que el menú no parpadee; las pruebas de cableado siguen contando
   pantallas como siempre (hay dos listas: `montajes` y `montajesDelMarco`).
2. **El módulo activo lo dice la pantalla, no el botón**: una tabla en `app.js`
   (`MODULO_DE_LA_PANTALLA`) traduce el componente que está puesto al renglón del menú que se marca.
   Así «Mi cuaderno» marca lo mismo se abra desde el menú, desde la pantalla de inicio o desde el
   aviso de lo que falta.
3. **El CSS, con sus dos lados**: `@media (min-width: 64rem)` pone el menú, la barra y el ancho; y
   `@media (max-width: 63.99rem)` **esconde el armazón en el móvil** a propósito (ahí manda la
   pantalla de inicio, sin menús que aprender).
4. **La cabecera de móvil se esconde en el ordenador**: su trabajo lo hace la barra. Sigue en el
   HTML porque la usa el móvil.
5. **Lo que NO trajo, y es lo que falta**: las tablas (fase 2), los paneles de detalle (3), el panel
   de mando de verdad (4) y los formularios en dos columnas (5). Hoy, en el ordenador, **los
   contenidos siguen siendo las mismas pantallas de móvil** con el marco nuevo alrededor: es la
   mitad del camino que David pidió.

**Lo que la fase 1 NO cambia, y hay que respetarlo**: los textos del servidor, los colores del
`:root`, el manejador de clics único, los formularios no controlados y las 3422 + 771 pruebas. Las
únicas medidas nuevas viven en el `@media` del ordenador.

## 6 ter. Lo que trajo la fase 2 (30/09/2026): la tabla de tierras

1. **La pieza `react/piezas/tabla.js`**: columnas (con su `data-campo` si se pueden ordenar), filas con sus
   celdas y sus botones, y el total del pie. **No calcula nada**: lo prepara `app.js`. La usará cada lista
   que se pase a tabla, así que la siguiente cuesta la mitad.
2. **La tabla de las 64 tierras** en «Mis parcelas, productos y máquinas»: Nº, Nombre, Referencia SIGPAC,
   Pueblo, Hectáreas (a la derecha y con dos decimales), Qué tiene este año (en ámbar y **con palabras**
   cuando le falta decirlo) y Acciones. Las dos formas —tabla y tarjetas— van en el mismo HTML y el CSS
   enseña la que toca.
3. **Ordenar por cualquier columna**: se pulsa su cabecera y la lista se ordena; se vuelve a pulsar y se le
   da la vuelta. La flecha la pone el CSS y la columna lleva `aria-sort`. El orden es **de la pantalla**, así
   que en el móvil las tarjetas salen en el mismo orden.
4. **El total del pie**: «2 tierras · 8,10 ha» (y con el buscador puesto, «1 de 2 tierras…», para que un
   filtro no parezca una pérdida de tierras).
5. **La tabla del cuaderno** (los apuntes del año, en «Mi cuaderno»): Fecha · Clase · Qué · Tierra ·
   Hectáreas · Cultivo · Acciones, **con lo último apuntado arriba** y el total de hectáreas tratadas al
   pie. Se ordena por cualquier columna, y **cada tabla se acuerda de su propio orden**: mirar las tierras
   por hectáreas no cambia el orden del cuaderno. Los apuntes firmados llevan su etiqueta «Firmado», que es
   lo que explica por qué a ese no se le da a borrar (se anula).
6. **La tabla de los años del cuaderno**: Año · Empieza · Termina · Qué tiene dentro · Estado · Acciones.
   Lo que tiene dentro cada año va en su celda, y el que no se puede quitar lo dice ahí mismo (es lo que
   explica que su BORRAR salga apagado).
7. **La tabla de las facturas**: Fecha · Quién te lo vendió · Nº de factura · Base · IVA · Total · El papel
   · Acciones, con el total del año al pie. **Un total que no se sabe no es un cero**: se deja en blanco y
   el pie indica que falta una cifra, sin presentar una suma parcial como total anual. La factura sin papel guardado lleva su aviso en ámbar: es lo
   primero que se pide en una inspección.
8. **Lo que falta de esta fase**: las tablas de los seis «maestros» (productos, abonos, quién aplica,
   asesores, máquinas y naves), las de los análisis y las ventas, y los **filtros** de verdad (hoy el de
   tierras es el buscador que ya había).

## 6 quater. Lo que trajo la fase 2 bis y la fase 3 (30/09/2026)

1. **La tabla del almacén** (`cesta-ver`): Producto · Comprado · Echado · Te queda · Estado · Acciones, con el
   pie diciendo **cuántos productos hay y cuántos hay que mirar** («2 productos en el almacén · 1 hay que
   mirarlo», con su singular escrito bien). Un dato que no se sabe sale con un guion, no con un cero. **El
   número de registro no está en la tabla** —está en el panel y en la tarjeta del móvil—: fue la primera
   columna que se quitó al mirar la captura, porque ensanchaba lo justo para que los dos botones de la última
   columna se apilaran; es la misma decisión que con el pueblo y la referencia del SIGPAC en las tierras.
2. **El panel de al lado, en dos listas**: el de una tierra (fase 3) y el de un producto del almacén. Se toca
   el **nombre** —que es un botón, no la fila entera: en una tabla, tocar una fila para abrir algo es lo que
   menos se espera— y su ficha sale al lado, con sus botones. Volver a tocar el mismo nombre cierra el panel.
3. **De dónde sale lo comprado, por fin en pantalla**: el servidor lo mandaba desde siempre
   (`comprado_de_donde`: «facturas» o «ficha») y **ninguna pantalla lo enseñaba**, así que el agricultor veía
   un número sin poder comprobarlo. Ahora está en el panel. Cuando no hay origen, la fila no se pone: un
   origen inventado es peor que no tenerlo.
4. **Corregir y borrar en la tabla y en la tarjeta del almacén**: los mismos dos botones que lleva el renglón
   de ese producto en «mis parcelas, productos y máquinas» (`botonesDeCorregirYBorrar`). Hasta hoy, desde el
   almacén no había forma de arreglar una cantidad mal escrita sin salir de la pantalla.
5. **Cada tabla ordena la suya, y repinta SU pantalla.** Esto estaba roto: el manejador de «ordenar-tabla»
   solo miraba si la tabla era la del cuaderno, así que pulsar una cabecera en la tabla de facturas ordenaba
   **la lista de tierras** y llevaba al agricultor a otra pantalla sin decirle nada. Ahora las cinco tablas
   (tierras, cuaderno, facturas, años, almacén) tienen su clave, su orden de entrada —facturas y años empiezan
   por lo más nuevo, que es como lo cuenta el agricultor— y su pantalla.
6. **La etiqueta corta de «le falta decir qué tiene»**: en la celda de la tabla, «Falta decirlo» en vez de la
   frase entera, que ocupaba tres renglones y dejaba la columna alta y estrecha. Lo mismo con el estado de un
   producto del almacén («Cuadra», «No se compara»…). La frase larga sigue en la tarjeta del móvil y en el
   panel de al lado.
7. **Tres arreglos de la forma que solo se ven en una captura**, y que valen para todas las tablas:
   - **Las celdas de una fila cuadran con las columnas.** La pieza de la tabla **siempre** pinta al final la
     celda de las acciones, y cada `tablaDe…` añadía además una celda vacía de más: con una celda de más, los
     botones de la fila caían en una columna **sin cabecera**, la tabla se ensanchaba sola y el encabezado no
     quedaba encima de sus botones. Estaba mal en las cinco tablas, y ahora hay una prueba que lo impide
     (`celdas = columnas − 1`).
   - **La barra de botones de una fila no se parte**: con la columna de las acciones estrecha, CORREGIR y
     BORRAR se ponían uno debajo de otro y cada fila ocupaba dos renglones.
   - **La cabecera de una tabla dentro de `.tabla-scroll` se pega a su caja**, no a la ventana: con el
     `top: var(--alto-barra)` de la cabecera fija, la primera fila quedaba tapada.
8. **Lo que NO se ha copiado del diseño de Stitch del almacén**: las tarjetas de números y la columna de
   **gasto en euros** por producto. Ese número (un gasto por producto sumado para el año) no existe en el
   programa, y ponerlo de adorno sería inventarse un dato. El día que exista, tiene su columna.

## 6 quinquies. Lo que trajo la revisión de la interfaz (30/09/2026)

David preguntó si hacía falta «alguna revisión más de ui, funcionalidad y disposición de páginas y
elementos». Se hizo la que faltaba de verdad —**mirar el escritorio con sus 64 tierras**, y no con la finca
de prueba de dos tierras con la que se habían hecho todas las capturas— y está entera en
[`REVISION_DE_LA_UI.md`](REVISION_DE_LA_UI.md), con sus capturas y su estado. Lo arreglado:

1. **A 1024 px (un portátil pequeño), la tabla de tierras dejaba fuera la columna de Acciones**: con el panel
   al lado, a la tabla le quedaban 22 rem cuando necesita 30 (menú 17 + márgenes 4 + panel 20 + hueco 1 + tabla
   30 = **72 rem**). Ahora, **por debajo de 72 rem el panel pasa debajo de la tabla**, y a partir de ahí sigue
   al lado. Es CSS y tiene su prueba con la cuenta escrita.
2. **«54 cosas apuntadas dentro» frente a «0 apuntes en el cuaderno».** El número del año contaba también el
   cultivo dicho de cada tierra, y el agricultor lo leía como apuntes: dos números que parecían
   contradecirse. Ahora el servidor manda **el desglose** (`apuntes`, `tierras_con_cultivo`, `otras_cosas`) y
   la pantalla dice «0 apuntes · 54 tierras con su cultivo dicho». El total sigue siendo el que impide borrar
   un año con cosas dentro.
3. **La tabla de «qué hay sembrado»**, que se había quedado fuera de la lista de tablas por hacer y es la más
   larga después de las tierras. Seis columnas y el pie «64 tierras · 54 con su cultivo dicho».
4. **Y la frase larga del año, en corto dentro de la celda** («Hay cosas dentro»), como se hizo con «Falta
   decirlo» en las tierras y «Cuadra» en el almacén.

Queda pendiente de esa revisión: **el nombre de las tierras trae dentro las hectáreas y el cultivo**
(«501/10015-1 VEZA VELLOSA (4,44 ha)»), que viene de la importación del cuaderno de la Junta y **toca datos
suyos**: está apuntado con su arreglo propuesto y no se toca hasta que él lo diga. Y las dos pasadas que
faltan de la revisión (el inventario de páginas y elementos, y la revisión funcional con la ley delante).

## 6 sexies. Lo que trajo la fase 4 (30/09/2026): el panel de mando

Lo que se ve al entrar desde un ordenador, y **por qué era la fase que más se notaba**: hasta hoy esa
pantalla era **la del móvil estirada** —ocho botones de ancho completo, uno detrás de otro, en un monitor de
1440 px—. Un programa de gestión, al abrirse, enseña **el estado**; no una lista de botones que hay que
pulsar para enterarse de cómo va el año.

1. **La pieza nueva** (`react/piezas/panel_de_mando.js`): las cuatro tarjetas de números, lo que falta con su
   botón, los últimos apuntes en una tabla corta, la fila de apuntar y el cierre. **No calcula nada**: todo se
   lo prepara `app.js` (`datosDelPanelDeMando`).
2. **La misma pantalla, dos formas**: `inicio.js` enseña el panel en pantalla ancha y **los seis botones del
   móvil en el móvil** (`.solo-escritorio` y `.solo-movil`). No hay una pantalla nueva, ni un módulo nuevo en
   el menú, ni dos sitios donde arreglar lo mismo.
3. **Los cuatro números salen de datos que ya estaban cargados**: los apuntes del año, las hectáreas de las
   tierras, lo vendido y lo que hay dicho de cada tierra. Ni una petición más (eso importa en el campo).
4. **Lo que falta es la misma lista del cuaderno** (`estado.faltantes`), con los mismos botones: si fueran dos
   listas, el día que una cambie la otra diría otra cosa.
5. **Los últimos apuntes son los mismos cinco de la tabla del cuaderno**, con la misma función y los mismos
   datos, y su enlace lleva a la lista entera.
6. **La tarjeta del gasto en fitosanitarios del diseño NO está**, y es a propósito: ese número no existe en el
   programa (no hay un gasto por producto sumado para el año). En su sitio va la tarjeta de las tierras, que
   además dice lo que hay que hacer («10 sin decir qué tienen este año»).
7. **Y un arreglo que salió de aquí, que vale para toda la aplicación**: `conCuenta` (el ayudante que elige
   entre singular y plural) solo miraba `<clave>_uno`, y hay textos cuyo singular está escrito `_una` porque
   el sustantivo es femenino («1 venta apuntada»). Con una sola venta, el panel decía «1 ventas apuntadas».
   Ahora prueba **las dos formas**, y hay una prueba en `tests_js/nucleo.test.js`. Es la segunda vez que este
   tropiezo cuesta un rato: la primera fueron los pies de las tablas.

## 6 septies. La segunda tanda de diseños de escritorio y lo que ha traído (30/09/2026)

David preguntó si se estaba usando Stitch para las pantallas nuevas. La respuesta honesta era **a medias**: el
armazón, el panel de mando, la tabla del cuaderno y el almacén salieron de cinco diseños pedidos antes de
empezar, pero **la tabla de «qué hay sembrado», la de las facturas y la de los años se construyeron copiando
la forma de las otras** —que es justo lo que no se quiere—. Así que se han pedido **seis diseños más**
(`cultivos`, `facturas`, `campanas`, `ventas`, `analisis` y `maestros`), y de ellos ya se ha aplicado lo que
toca a las pantallas que existen:

1. **El filtro de las que faltan** (de `escritorio/cultivos.png`): la franja de «A 10 parcelas les falta decir
   qué tienen este año» lleva ahora **el botón VER SOLO LAS QUE FALTAN**, que enseña esas y solo esas para
   irlas diciendo una detrás de otra, y **siempre la vuelta** (VERLAS TODAS). El pie dice «1 de 64 tierras»
   mientras el filtro está puesto, porque un filtro sin decirlo parece una pérdida de tierras. Es **el primer
   filtro de verdad** de las tablas: lo que David pidió con «tablas con filtros y orden».
2. **La alerta de rotación, en su propia columna**: antes iba como letra pequeña debajo del cultivo, y con 64
   tierras eso no se ve al recorrer la lista. Ahora tiene su columna y su etiqueta en ámbar.
3. **El dibujo de la forma de la tierra y sus últimos apuntes** en el panel de al lado (de
   `escritorio/estructura.png`): la forma ya venía en la ficha desde la ronda 78 y el panel era el único sitio
   donde una tierra salía sin su dibujo; y «lo último que le has hecho» es la pregunta que se hace al mirar
   una tierra en el despacho. Los apuntes se sacan de los que ya están cargados: ni una petición más.
4. **El botón ANULARLO en los apuntes firmados y el pie con los firmados** (de `escritorio/cuaderno.png`): un
   apunte firmado no se borra, se anula; la pantalla que pregunta ya lo decía, pero el botón seguía diciendo
   BORRAR. Y al pie se dice cuántos están firmados, que es lo que mira una inspección.
5. **La franja de números de facturas** (de `escritorio/facturas.png`) ya enseña cuántas hay, base, IVA,
   total del año y cuántas no tienen papel. Si falta una cifra, su suma se enseña como «—»; el pie deja de
   presentar una suma parcial como si fuese el total del año. Las tarjetas del móvil no cambian.
6. **Los tres diseños de `ventas`, `analisis` y `maestros`** están pedidos y guardados, esperando a que esas
   pantallas se hagan en el ordenador (fase 6).



**Orden de trabajo**: 1 → 2 → 3 → 4 (es donde está el salto que David nota) → 5 → 6 → 7.

---

## 7. Lo que todavía hay que decidir con David

1. **En qué año trabajas.** Hoy el programa usa siempre el año más alto. Si se crea el 2027, todo lo que se
   apunte va al 2027 y no hay forma de seguir en el 2026. ¿Se pone un selector de año en la barra de arriba,
   como el de finca? (Recomendado: sí.)
2. **Qué se enseña en las cuatro tarjetas del panel** (los números del año). Los que propongo: apuntes del
   año, hectáreas tratadas, lo vendido y gasto en fitosanitarios.
3. **La versión de móvil**: si el menú lateral aparece también en el móvil, será un menú que se abre con un
   botón (una cosa más que aprender) o no aparece. Lo recomendado: **en el móvil no hay menú**: se sigue
   entrando por la pantalla de inicio, que es lo que ya conoce.
4. **Imprimir en el ordenador**: ¿hace falta el cuaderno en papel con formato de folio (A4), además del
   fichero para la Junta? Es lo que suele pedir una inspección cuando no llevas el móvil.

---

## 8. Cómo se comprueba que el rediseño no rompe nada

1. **Las pruebas del proyecto entero** (3422 de Python y 771 de JavaScript) tienen que seguir en verde. Las
   de cableado (`tests_js/interfaz.test.js`) pulsan botones de verdad: si una acción se pierde en la versión
   de escritorio, fallan.
2. **La comprobación en un navegador de verdad** (`scripts/comprobar_en_un_navegador.py`) tiene que
   recorrer **las dos formas**: la de móvil (390 px) y **una nueva de escritorio (1440 px)**, con las mismas
   rutas y los mismos textos.
3. **La marca de versión** en el pie (`versión 2026-10-01-57`) dice qué se está viendo. Si en un navegador
   se ve una pantalla vieja, el pie lo delata.
4. **`humo.py`** contra un servidor de verdad sigue pasando.

---

## 9. Encargos de interfaz que pueden seguir otros agentes

La revisión del 01/10/2026 cerró dos detalles pequeños: los números anuales de facturas ya se ven
juntos, y una factura sin importe deja el total anual pendiente; el pie del filtro «solo las que faltan»
ya no añade «0 con su cultivo dicho». Quedan estas tareas de más recorrido:

1. **Formularios de escritorio, fase 5.** Preparar un formulario en dos columnas con su resumen a la
   vista, empezando por una sola alta y corrección frecuente. Tomar la jerarquía del diseño de Stitch
   correspondiente; conservar los mismos campos, validaciones, acciones y orden de lectura en móvil.
2. **Listas que faltan, fase 6.** Pasar ventas, análisis y los seis maestros a la pieza de tabla, con
   orden, filtros visibles y salida clara del filtro. Usar los diseños guardados en
   `docs/stitch/escritorio/`; si una cifra no existe en los datos, mostrar que falta, nunca calcularla
   a partir de suposiciones.
3. **Repaso visual con 64 tierras.** Comprobar en navegador de verdad a 1024 y 1440 px las columnas,
   botones, foco de teclado y panel lateral. Revisar también 390 px para que las tarjetas y el flujo de
   alta sigan completos. Documentar con captura cada defecto concreto antes de cambiar CSS.

Para aceptar cada tarea: pruebas Python y JavaScript, humo con base desechable, `designmd lint` y
recorrido visual. No usar `backend/cuedigital.db` para pruebas ni guardar claves de Stitch en el proyecto.
