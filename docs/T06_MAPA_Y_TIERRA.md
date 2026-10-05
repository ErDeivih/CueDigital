# T06 / E2 — Mapa de explotación con selección y filtros, y lista de tierras sin geometría

> **Qué es este documento.** La entrega de T06 contada sin adornos: **qué se ha construido**, **qué
> había ya** y se ha reutilizado, **qué no se ha hecho y por qué**, **las decisiones con su motivo** y
> los **recuentos reales** de pruebas, leídos del XML y de la salida de `node --test`.
>
> **Manda lo que digan el código y las pruebas**, no este documento. Todo lo que se afirma aquí se
> puede comprobar con el comando que se escribe al lado.

Última actualización: **03/10/2026** (la fecha del reloj de la máquina donde se ha hecho el trabajo).

---

## 1. Qué se ha construido

### 1.1. Las dos direcciones nuevas (`backend/web/react/rutas.js`)

| Clave | Dirección | Qué es |
|---|---|---|
| `tierras_mapa` | `#/tierras/mapa` | **Las tierras de la finca**: la tabla con buscador, filtros, agrupación y selección, y el mapa de la finca al lado, enlazados. |
| `tierra_versiones` | `#/tierras/<id>/versiones` | **Lo que ha sido una tierra**: sus versiones por año y por fuente, la comparación de dos años y el ensayo de una importación. |

**Por qué no se ha usado `#/tierras` para la primera**, que era lo natural: `#/tierras` es la pantalla
de siempre («Mis parcelas, productos y máquinas»), con su buscador y su tabla desde el 30/09/2026, y
media docena de pruebas y todos los enlaces guardados cuentan con ella. La vista nueva es **una vista
más de las mismas tierras**, y se le ha dado su propia dirección en vez de cambiarle el contenido a la
que ya había. Está escrito en el propio módulo.

Las dos cumplen la regla de T04 para tener dirección: **volver a su dirección las reconstruye
enteras** (la primera pide `/api/parcelas/vista`, la segunda las versiones de esa tierra).

### 1.2. La pantalla de las tierras (`backend/web/react/pantallas/tierras_mapa.js`)

Lo que pide el contrato §2.1, punto por punto:

1. **La tabla** con el número con el que el agricultor llama a la tierra, su nombre, su referencia del
   SIGPAC, sus hectáreas, lo que tiene sembrado, su pueblo, si tiene forma y si se ha revisado. Y una
   casilla para marcarla.
2. **Buscador por nombre y por referencia del SIGPAC**, y **cuatro filtros**: lo sembrado, el pueblo,
   la revisión y lo que se puede declarar. Las opciones y sus recuentos **los da el servidor**.
3. **Agrupación**: por lo sembrado, por pueblo o **por si se les ha medido la forma**. En esa última
   sale **el grupo «Sin forma»** del contrato, y una tierra sin polígono **también lleva su etiqueta
   «SIN FORMA»** en su columna aunque no se agrupe: que le falte la forma no puede depender de cómo
   esté ordenada la lista.
4. **Selección múltiple**: casilla por fila, recuento en singular y en plural («Has marcado 1 tierra» /
   «Has marcado 3 tierras»), y los dos botones de marcar todas las que se ven y de quitar la selección.
5. **El mapa de la finca**: los trozos de verdad encima de la capa elegida, con su leyenda, su
   servicio y la fecha de la imagen. Se puede encajar la finca, acercar, alejar y **quitar las capas**
   (la imagen y las rayas de las tierras, por separado).

### 1.3. La ficha de una tierra (`backend/web/react/pantallas/tierra_versiones.js`)

Lo que T05 dejó pedido («la ficha de una tierra con sus versiones y la previsualización de una
importación están por hacer en la interfaz, y son de T06»):

* **Sus versiones**, de la más nueva a la más vieja, cada una con su año, su fuente, cómo está (la
  frase del servidor: «Sin forma: no ha venido el polígono», «La referencia está a medias…»,
  «Sin revisar»), su referencia y **las tres áreas cada una con su nombre**: lo que mide la forma que
  vino, lo que dice el SIGPAC y lo que declara el agricultor. Cualquiera puede venir vacía y entonces
  se dice **«No se sabe»**, nunca un cero.
* **Comparar dos años** con los cuatro estados del contrato (`igual`, `cambiado`, `desaparecido`,
  `nuevo`), sus cuatro recuentos y **el porqué de cada cambio** («Qué cambió: la forma del trozo»).
  Comparar solo lee (`GET /api/versiones/comparar`).
* **Ensayar traer lo de otro año**: se arma el lote con lo que esa tierra tenía en otro año y se manda
  a `POST /api/versiones/previsualizar`, que **no escribe**. La pantalla dice con sus palabras que no
  se ha apuntado nada y ofrece, **aparte**, el botón de apuntarlo, que es el único sitio de toda la
  aplicación que llama a `/api/versiones/aplicar`.

### 1.4. El servidor

**Una ruta nueva** (`backend/app/routers/parcelas.py`):

```
GET /api/parcelas/vista      todas las tierras de la finca con lo que la pantalla necesita
```

Va **antes** de `/parcelas/{parcela_id}` en el fichero a propósito: si se declarara detrás, el tramo
dinámico se comería la petición e intentaría leer «vista» como un número.

Devuelve, de una sola vez y del mismo momento (es lo que evita que el pie diga «64» sobre una lista
de 63):

| Qué | Detalle |
|---|---|
| `tierras` | Una por tierra: su número, su nombre, su referencia, su pueblo, sus hectáreas (o `null`), si tiene forma, **sus anillos de coordenadas de verdad**, lo que tiene sembrado, el estado de revisión de la versión de este año y los dos hechos del filtro de la PAC. |
| `totales` | **Solo recuentos** de la finca entera: tierras, con forma, sin forma, sin decir el cultivo, sin hectáreas dichas y sin versión de este año. |
| `mapa` | `hay_forma` y **la caja que envuelve las formas que de verdad hay** (o `null`, y entonces la pantalla lo dice en vez de abrir el mapa en un sitio cualquiera). |
| `filtros` | Lo que se puede elegir en cada filtro, **sacado de las tierras que hay**, con cuántas caen en cada opción. |

**Y `/api/mapa/estado` dice más** (`backend/app/routers/mapa.py`): cada capa lleva su `leyenda`, su
`servicio`, su `fecha` (vacía, ver §4.2), su `fecha_texto` y `se_puede_ocultar`. Y añade
`leyenda_de_mis_tierras`, `capa_avisos_no_esta` y `si_no_llega_una_imagen`.

### 1.5. Los textos (`backend/app/textos.py`, al final)

Dos bloques nuevos, registrados en `textos_visibles()`: `TIERRA_Y_MAPA` (la tabla, los filtros, el
grupo «sin forma», la leyenda del mapa y lo que pasa cuando una imagen no llega) y
`VERSIONES_EN_PANTALLA` (la ficha, la comparación y el ensayo). Se sirven en `/api/interfaz` (claves
`tierras` y `versiones`) **y** viajan dentro de `/api/parcelas/vista`.

**Por qué en los dos sitios**, que fue una decisión de verdad y no una duplicación por descuido: la
ficha de una tierra **se puede abrir directamente por su dirección** (`#/tierras/2/versiones`) sin
haber pasado por la pantalla del mapa, y entonces no hay ninguna vista descargada de la que sacar sus
palabras. Lo de `/api/interfaz` está guardado en el móvil, así que la ficha tiene sus textos **sin
cobertura**; lo de la vista queda como respaldo. Se descubrió porque una prueba de cableado salió con
el título vacío.

### 1.6. Lo que se ha comprobado **con los datos de verdad** (03/10/2026)

El coordinador midió los datos reales del agricultor sobre una **copia** de `backend/cuedigital.db`
(mismo sha256 que el original, `71456b0b…`; el original no se ha abierto). El dato que cambia el
significado de «datos representativos» es este:

| Hecho real | Número |
|---|---|
| Tierras | **64 en la explotación del agricultor** (65 en toda la base: 1 es de otra explotación, la del id 3) |
| **Tierras con forma (geometría)** | **0 de 64** — **todas van sin polígono** |
| Nombre de tierra más largo | **42 caracteres**: `503/10059-1 BARBECHO TRADICIONAL (3.54 ha)` |
| Tierras sin decir el cultivo | 10 |
| Zona de nitratos **sin saber** | 62 de 65 |
| Versiones de recinto | **0** (ninguna tierra tiene versión de ningún año) |

**Consecuencia, y es la que manda:** el grupo «sin forma» **no es un cajón de excepciones: es la
finca entera**, y el caso «no hay nada que dibujar en el mapa» **es el caso normal**, no el raro.

Se ha recorrido con esos datos **de verdad** (por la API, contra un servidor con la copia temporal) y
en un **navegador de verdad**. Lo que salió está en §5.2 bis.

### 1.7. Y tres cosas más que salieron al mirar esos datos, y que cambiaron el código

Midiendo la copia aparecieron **tres defectos de verdad**. Los dos últimos se midieron **en su finca**
(64 tierras, 59 nombres y 51 referencias); el primero —el de los pueblos— está justificado por el caso
de `MACHACON` contra `Machacón`, que es de sus datos, aunque **el primer ejemplo que se puso aquí era
un recuento mal hecho y está corregido más abajo**. Los tres están arreglados, con su motivo escrito en
el código y con pruebas que los sujetan.

| Lo que se midió | Qué pasaba | Qué se ha hecho |
|---|---|---|
| **El mismo pueblo escrito de dos maneras**: **`MACHACON`, que es como lo escribe el cuaderno de la Junta (sin tilde), contra `Machacón`, que es como lo escribe la lista oficial del INE (con tilde)** —que es de donde el formulario lo coge al elegirlo—, y **nombres con dos espacios de dentro** de teclearlos a mano | Con el cotejo literal del texto (o juntando solo por mayúsculas, que es lo que hacía el servidor al principio), el filtro y la agrupación tratarían **el mismo pueblo como dos**: dos entradas en la lista de pueblos, dos grupos, y el agricultor pensando que tiene tierras en otro sitio. **Y peor: el número de la opción y las filas que salen al elegirla no cuadran** —dice 3 y enseña 4—, que es lo que hace que deje de creerse los números del filtro | Se filtra y se agrupa **sin distinguir mayúsculas, tildes ni espacios de dentro**, con **la misma normalización en el servidor y en la pantalla**, y el recuento se suma. **El dato guardado y el que enseña cada fila NO se tocan**: el nombre del pueblo de sus tierras es suyo. El rótulo de la opción es **la forma que más veces está escrita de verdad**, nunca una inventada |
| **Nombres de tierras repetidos**: 64 tierras y solo 59 nombres distintos; `507/91-3 AVENA (1 ha)` tres veces y tres nombres más dos veces cada uno. La pareja de `507/24-1 BARBECHO TRADICIONAL (4.44 ha)` comparte **nombre, referencia y superficie** | En una tabla con búsqueda y selección, el agricultor **no puede distinguir** dos filas iguales para elegir una | El servidor cuenta cuántas tierras se llaman igual y **la fila lo dice** («Hay 2 tierras con este mismo nombre. Míralas por su número y su referencia…»). El número de la tierra ya estaba en la tabla y es lo que le deja elegir. **No se renombra nada**: el nombre es suyo |
| **Varias tierras comparten el recinto**: 64 tierras y solo **51 referencias distintas**; una la comparten **9** tierras y otra 6, porque el cuaderno de la Junta parte un mismo recinto en varias líneas de cultivo | Al tocar ese trozo en el mapa, ¿qué fila se enfoca? Elegir una al azar sería mentir: las nueve son el mismo trozo | El servidor da a cada tierra su **`clave_recinto`** (la referencia normalizada; si no la hay, la huella de la forma; y si no hay ninguna de las dos, su propia tierra, porque de ella no se puede afirmar que comparta nada). Al tocar el trozo **se encienden todas las de ese recinto** y se dice cuántas: «Esta forma la comparten 9 tierras…» |

> **Un ejemplo que estuvo mal aquí, y se deja escrito para que no vuelva.** En la primera versión de
> esta tabla el motivo del cotejo era «`CALVARRASA DE ARRIBA` en 54 tierras y `Calvarrasa de Arriba` en
> 1», y decía «medido». **Era falso**: ese recuento salía de medir **toda la base sin filtrar por
> explotación**, y la base tiene más de una. En **su finca** hay **7 municipios y ninguno repetido con
> otra ortografía**; la tierra escrita `Calvarrasa de Arriba` está en **otra explotación** (la 3), y el
> pueblo que faltaba en la lista de la suya es **`CALVARRASA DE ABAJO`**, que es **otro pueblo
> distinto**. Lo encontró la revisión de T06.
>
> **Lo que el error no cambia, y es lo que importa: el cotejo sigue haciendo falta, y por este motivo:**
> su cuaderno escribe **`MACHACON`** (como lo escribe la Junta, sin tilde) y la lista oficial del INE
> escribe **`Machacón`** (con tilde) — **el mismo pueblo escrito de dos maneras según quién lo
> escriba**, y el día que apunte una tierra más eligiendo el pueblo de la lista tendrá las dos en la
> misma finca. A eso se suman los nombres con dos espacios de dentro, de teclearlos a mano. **Nadie
> tiene que quitar el cotejo pensando que el ejemplo era el único motivo.**
>
> Y la lección de método, que es la que vale para el próximo número que alguien escriba aquí:
> **cualquier cifra sobre «los datos del agricultor» tiene que decir sobre qué finca se midió.** Una
> base puede tener varias explotaciones, y un recuento de toda la base no es un recuento de su finca.

**Los tres se han vuelto a comprobar con los datos reales** después de arreglarlos (§5.2 bis). Y hay
que decir con precisión **cómo se midió cada uno, porque en el primero se midió mal**:

* **El de los pueblos está justificado por `MACHACON` contra `Machacón`** (cuaderno de la Junta contra
  lista oficial del INE) y por los nombres con espacios de dentro. **No** por el ejemplo de
  «Calvarrasa de Arriba», que era un recuento de **toda la base sin filtrar por explotación** (ver el
  recuadro de arriba): en su finca hay **7 municipios y ninguno repetido con otra ortografía**. El
  arreglo sigue haciendo falta y está **probado con pruebas de unidad** (tres formas → una sola opción,
  con el recuento sumado); se disparará el día que una importación traiga la forma con tilde, que es
  justo lo que pasa cuando se juntan el cuaderno de la Junta y la lista del INE.
* **El de los nombres repetidos y el de los recintos compartidos sí son de su finca**, medidos
  filtrando por su explotación: 64 tierras, 59 nombres y 51 referencias.

### 1.8. Y la revisión del ticket: lo que encontró y lo que se ha arreglado

Otro agente revisó T06 con su propio fichero de pruebas (`backend/tests/test_revision_t06.py`), y sus
hallazgos eran de verdad. Los once primeros son los que importan; **siete eran defectos reales** y
están arreglados, con su motivo escrito en el código. Se cuentan aquí porque forman parte del trabajo
entregado:

| # | Lo que encontró | Cómo está ahora |
|---|---|---|
| **D1** | Una tierra traída del cuaderno de la Junta **sin superficie** pero con hectáreas declaradas en su versión salía diciendo «Sin hectáreas dichas» mientras el pie decía que no había ninguna así, y el filtro no ofrecía esa opción. Dos cosas que no pueden ser verdad a la vez | **«Hectáreas dichas» es la superficie de la tierra**, y esa es la regla que usan a la vez la fila, el pie y el filtro. **Y lo declarado no queda invisible**: la fila lo enseña debajo, con su nombre («Las que declaras este año: 2,50 ha»), sin mezclar las dos magnitudes |
| **D2** | El mapa contaba **2** tierras con forma y la tabla **1**, en la misma respuesta: el mapa miraba `geometria` (escrita) y la tabla los anillos que se pueden dibujar | Los dos cuentan **el mismo dato** (los anillos). El mapa se calcula desde las tierras ya montadas, no volviendo a leer el WKT |
| **D3** | El servidor juntaba las formas de escribir un pueblo **solo por mayúsculas** y la pantalla coteja quitando también **tildes y espacios de dentro**: «MACHACON» (cuaderno de la Junta) y «Machacón» (lista del INE) salían como dos opciones, una diciendo 3 tierras y enseñando 4 | La llave para juntarlas es **la misma normalización que la pantalla** (`_como_se_busca`, espejo de `nucleo.sinTildes`). Con eso el número de la opción y las filas que salen cuadran siempre |
| **D7** | Con una finca repartida en más de medio grado, la caja que daba la vista **la rechazaba su propio `/api/mapa/imagen`** con 422, y el agricultor leía «puede ser la cobertura» delante de un fallo que no tiene nada que ver con la cobertura | La caja que se da **es siempre una que este programa acepta**, `se_puede_ensenar_entera` dice que no se ve toda la finca, **`extension` guarda la envolvente sin recortar** (no se pierde dónde están las de fuera) y la pantalla lo dice con sus palabras. Elegir una tierra en la tabla centra el mapa en ella aunque esté fuera de la parte que se veía |
| **D9** | El recuento de recintos sin forma del ensayo llevaba la etiqueta **«No se sabe»**: en pantalla se leía «No se sabe: 3», y no es un dato que no se sepa —es un recuento— | Lleva su nombre: «Recintos sin su forma medida» |
| **D11** | La vista de las tierras **se pedía una sola vez por sesión y nada la olvidaba**: después de apuntar, corregir o borrar una tierra, la pantalla seguía contando las de antes | `olvidarLaVistaDeLasTierras()` en `cargarDatos()`, que es por donde pasa volver a leer la finca: cualquier pantalla que recargue los datos se lleva la vista por delante |
| **—** | El guardián de las direcciones (`tests_js/rutas.test.js`) se quedó corto cuando el otro agente añadió `semillas` y `siembras` | Se apuntaron las dos en la tabla de pantallas (ese fichero es de este ticket) |
| **—** | Los tres documentos del recuento y el par caché/versión se desincronizaron con las pantallas nuevas del otro agente | Puestos al día: **3534 pruebas de Python y 805 de JavaScript**, caché `-65` con la versión del pie en `-65` |

**Dos cosas que la revisión también cazó y NO eran de este ticket**, y se dejan dichas para que no se
pierdan: su prueba de «si no se puede crear un índice, la base se queda entera y se dice en
castellano» falla por el índice `uq_recepcion_reenvio` de T05/T09 (no es de T06), y su guardián de las
tablas que apuntan a una tierra está esperando una tabla `siembras` que es de otro agente.

### 1.9. Las pruebas

| Fichero | Qué cubre | Cuántas |
|---|---|---|
| `backend/tests_js/tierras_y_versiones.test.js` | **NUEVO.** La búsqueda y los filtros, el grupo «sin forma», la selección múltiple, el vínculo fila ↔ polígono, los puntos del trozo, las capas y la leyenda, la imagen que no llega, la previsualización que no escribe, los cuatro estados de la comparación, el lote sin números inventados, **la finca de verdad (64 tierras, ninguna con forma, el nombre de 42 caracteres)**, **el pueblo escrito de dos formas**, **los nombres repetidos** y **las tierras que comparten recinto**, y las dos pantallas sin frases escritas a mano. | **39** |
| `backend/tests_js/interfaz.test.js` | **+6 pruebas de cableado**: la dirección abre la pantalla y pide la vista, los filtros viajan en la dirección, tocar una fila enfoca su trozo (y no mueve el mapa si el trozo no existe), **ensayar no escribe**, apuntar es lo único que escribe, y la vista que no llega se dice. | **+6** |
| `backend/tests_js/rutas.test.js` | Las dos direcciones nuevas en la tabla, en la ida y la vuelta y en la lista que impide volver atrás. | (3 pruebas tocadas) |
| `backend/tests/test_t06_tierras_y_mapa.py` | **NUEVO.** Los recuentos, la tierra sin forma, que **no haya ningún total de hectáreas**, la caja del mapa (sin formas, con formas, agrandada al mínimo y **recortada al máximo con su envolvente aparte**), los filtros con su recuento, el aislamiento entre fincas, la versión de la campaña, los anillos de un multipolígono, lo que `/api/mapa/estado` dice de sus capas y **los tres hallazgos de los datos de verdad** (el pueblo de dos formas, los nombres repetidos y las tierras que comparten recinto) **más los de la revisión** (el pueblo con tilde y sin tilde, las hectáreas de la fila y del pie, y la caja que acepta el propio programa). | **28** |

**Total: 47 pruebas nuevas de JavaScript y 28 de Python (75 nuevas).**

Y hay que añadir el fichero del revisor, `backend/tests/test_revision_t06.py`, con **42 pruebas** escritas
contra este ticket por otro agente: **las 42 en verde** con los arreglos de §1.8. Su fichero no es de
este ticket y no se ha tocado.

**Y una cosa que se ha separado a propósito para no confundir dos cosas distintas:**

| Lo que se ha probado | Con qué datos |
|---|---|
| La tabla, los filtros, la búsqueda, el grupo «sin forma», la selección múltiple, la previsualización que no escribe, los cuatro estados de la comparación y el ensayo | **Con la forma de los datos de verdad**: 64 tierras, **ninguna con su forma medida**, el nombre de 42 caracteres y los tres hallazgos de §1.7 (`tests_js/tierras_y_versiones.test.js`, apartados 8 y 9) |
| El grupo «sin forma» **con las 64 filas dentro**, que la tabla siga sirviendo sin mapa, que no se dibuje ni un polígono, que no se pida ninguna imagen, el aviso de los nombres repetidos y que el nombre largo salga **entero** a 390, 1024 y 1440 px | **Con una copia temporal de los datos reales**, por la API y en un navegador de verdad (§5.2 bis) |
| El vínculo fila ↔ polígono, los puntos de un trozo, las capas del mapa, la imagen que no llega y la comparación de dos campañas **con formas** | **Inventado a propósito**: en los datos reales **no hay ni una geometría**, así que hubo que **sembrar formas sintéticas** en base temporal para poder probarlo. Está dicho aquí y en el apartado 8 del fichero de pruebas |
| La importación por lote y su previsualización | **Con formas sintéticas** también, por el mismo motivo |
| Que **nueve** tierras del mismo recinto se enciendan juntas y se diga cuántas | La lista de quién comparte recinto, **con los datos reales** (el recinto `37-70-0-0-507-24-1` lo comparten 9 tierras, números 50 a 58). Que el trozo se encienda y la frase salga, con **formas sintéticas**, porque las nueve tierras de verdad no tienen polígono |

---

## 2. Qué había ya, y se ha reutilizado (no se ha duplicado)

* **`/api/mapa/imagen`** y **`/api/mapa/punto`** (`routers/mapa.py`) siguen siendo los que traen y
  sirven las imágenes del IGN y del SIGPAC: el navegador no habla con ningún servicio de fuera. La
  pantalla nueva solo compone la dirección de la imagen con la caja que se está mirando.
* **`geo.anillos_de_un_wkt`** y **`geo.rectangulo_de_un_wkt`** (T05) son los que sacan los anillos y
  la caja: **no se ha escrito ninguna geometría nueva**. Un multipolígono sale en anillos separados
  porque es lo que esa función devuelve, y hay una prueba que lo fija.
* **`servicios.los_cultivos_de_la_finca`** es la misma lista que usa «qué hay sembrado», así que la
  tabla nueva y aquella pantalla **no pueden decir cosas distintas** de la misma tierra.
* **`versiones_de_recinto`** (T05) entero: `listar`, `comparar_dos_campanas`, `plan_de_importacion` y
  `aplicar_importacion`, con sus textos (`texto_de_la_fuente`, `texto_del_estado_de_revision`). La
  pantalla nueva **no calcula ninguna comparación**: la pide.
* **`componentes.js`**: el botón, el botón sencillo, el aviso de error y la frase. Se le ha añadido
  **una pieza nueva**, `OpcionesParaElegir` (un rótulo y una fila de opciones donde una está elegida),
  porque la necesitan las dos pantallas nuevas y escribirla dos veces es lo que ese fichero existe
  para evitar.
* **`nucleo.js`**: `sinTildes` (el mismo buscador que «mis cosas») y `rellena`. **No se ha escrito un
  segundo quitador de tildes.**
* **`rutas.js`**, el armazón de T04, el manejador de clics único y el patrón de los campos
  descontrolados (`defaultValue` + `id`), tal y como manda `docs/REACT.md`.
* **El catálogo de la casa**: `docs/T02_VALORES_POR_DEFECTO.md` (vacío no es cero),
  `docs/SERVICIOS_DEL_SIGPAC.md` (las direcciones y qué devuelve cada servicio) y
  `docs/T05_IDENTIDAD_Y_VERSIONES_DEL_RECINTO.md` (las versiones y la importación repetible).

---

## 3. Decisiones, con su motivo

### 3.1. La vista va en **una sola llamada**, y **no filtra** en el servidor

`/api/parcelas/vista` devuelve todas las tierras y todos los recuentos. **Filtrar es cosa de la
pantalla**, y hay tres motivos que se suman:

1. **El buscador tiene que responder sin cobertura.** Con la lista ya descargada, escribir «prado» no
   puede depender de que haya red.
2. **El pie tiene que poder decir «ves 10 de 64»**: para eso hacen falta las filas que se ven (las
   cuenta la pantalla) y el total de la finca (lo da el servidor).
3. **Los recuentos de cada opción sí los calcula el servidor**, y se calculan sobre **todas** las
   tierras. Así el número que se lee al lado de «Trigo» no cambia porque el agricultor haya escrito
   algo en el buscador, que es lo que pasaría si se contara sobre lo que se ve.

**Lo que esto cuesta, y se dice:** el día que una finca tenga 3.000 tierras, traerlas todas con sus
anillos en una respuesta será demasiado. Hoy son 64.

### 3.2. Los filtros son de dos clases, y **no se comportan igual** a propósito

* `q`, `cultivo` y `municipio` filtran por **lo que hay escrito en la tierra**. Pedir un cultivo que no
  tiene nadie devuelve **cero tierras**, y es correcto: el valor es un dato.
* `revision` y `pac` filtran por **un código de una lista cerrada**. Un valor que la pantalla no
  conoce **no filtra**: puede venir de una versión más nueva del programa o de una dirección guardada
  hace meses, y vaciarle la lista al agricultor por eso sería peor que no filtrar. Es la misma
  decisión que toma `rutas.js` con los parámetros que no entiende.

### 3.3. El grupo «sin forma», y por qué además cada fila lleva su etiqueta

**Con los datos de verdad esto no es un caso raro: es el 100 % de la finca.** 64 tierras y **ninguna
con su forma medida**, así que el grupo «sin forma» lleva las 64 filas dentro y el mapa no tiene nada
que dibujar. La pantalla está hecha para eso: la tabla es la que sirve, el mapa es lo que falta, y se
dice. Lo que **no** se hace es apoyarse en «casi todas tienen forma».

El contrato pide que una fila sin polígono siga en la tabla **y en un grupo «sin forma»**. Se cumple
de las dos maneras: agrupando por forma sale el grupo (con las 64), **y** cada fila lleva su etiqueta
«SIN FORMA» en su columna se agrupe como se agrupe. El motivo: si la etiqueta solo saliera dentro del
grupo, mirar la lista sin agrupar —que es lo normal— escondería justo el dato que hay que arreglar.

Y **no se le dibuja nada**: en el mapa no hay ni un polígono. Lo que no se ha medido no se inventa
(`AGENTS.md` §3.3).

### 3.4. El filtro de la PAC son **cuatro hechos**, y ninguno dice «cumple»

`con_referencia` / `sin_referencia` (están o no los tres números del recinto) y `con_hectareas` /
`sin_hectareas` (se sabe o no alguna hectárea de esa tierra). **El programa no dice «cumple la PAC» ni
«está declarada»** porque eso no lo sabe: no ha hablado con la Junta. Es la regla de
`AGENTS.md` §2.3 y hay una prueba que impide que alguien «arregle» el filtro añadiendo esa palabra.

### 3.5. El mapa **no puede saltar a otra provincia**, y está garantizado por construcción

La caja que se mira sale de la caja de la finca, que la calcula el servidor **con las formas que de
verdad hay**; y al acercarse o al enfocar una tierra la caja **se queda dentro de la de la finca** (el
centro se desplaza lo justo para que el borde no se salga). No hay ninguna forma de pedirle
coordenadas a mano a esta pantalla. Y sin ninguna forma medida (`hay_forma` en falso, `caja` vacía) no
se abre el mapa: se dice.

**Un detalle que costó una prueba:** si las formas son tan pequeñas que la caja mide menos de lo que
el servicio de mapas acepta (0,0008 grados, unos 90 metros), se **agranda alrededor de su propio
centro** hasta ese mínimo —la misma finca, más de cerca—. La cuenta lleva un pelo de margen porque
restar dos `float` da 0,0007999999999999119 y el servidor rechazaba su propia caja. Está visto en la
prueba `test_una_forma_minuscula_se_agranda_al_minimo_sin_cambiar_de_sitio`.

### 3.6. El enlace entre la fila y el polígono es **una acción con un identificador**

El nombre de una fila y cada trozo del mapa llevan **la misma acción** (`t06-elegir-fila`) con el
identificador de la tierra. Así el manejador de clics único de `app.js` enfoca la tierra por el mismo
camino en los dos sentidos, sin dos manejadores que se puedan separar. El componente pinta la fila
encendida (`tabla-fila-elegida`) y el trozo encendido (`t06-tierra-elegida`), y **marcar** (juntar
tierras) se distingue de **elegir** (mirar un trozo): una lleva raya discontinua y la otra el amarillo
de la casa.

### 3.7. El mapa dibuja **las tierras que pasan el filtro**

Lo pide el contrato («el mapa respeta la selección declarada») y es lo que hace útil filtrar por lo
sembrado: se ven en el mapa solo esos trozos. El pie sigue diciendo el total de la finca, así que el
agricultor nunca pierde de vista cuántas se está dejando fuera.

### 3.8. **Ninguna cifra que el servidor no haya dado**

* El pie son **recuentos**: «Ves 10 de 64 tierras» y tres «sin…» de la finca entera.
* **No hay ningún total de hectáreas**, y hay una prueba que lo impide: la mitad de las tierras puede
  tener la superficie en blanco, y sumarlas como cero sería una cifra falsa; sumar solo las conocidas
  diría menos de lo que parece.
* Los cuatro recuentos de la comparación y del ensayo los da el servidor.
* **Ni un porcentaje, ni una media, ni una nota.**

### 3.9. Una imagen que no llega: se avisa, no se borra nada y no se deja la foto vieja
Es exactamente lo que pide el contrato §2.1. Cuando el `<img>` de una capa falla:

1. **no se borra ningún polígono** (las rayas de las tierras siguen dibujadas);
2. **no se deja la foto vieja puesta**, porque una foto que no es la de esta caja —y sin fecha— es
   peor que no tener foto: en su sitio va el aviso;
3. y **se dice qué puede hacer mientras tanto** («Tus linderos siguen dibujados y la lista funciona
   igual: puedes seguir mirando y trabajando»). La tabla sigue entera.

El `if` que impide repetir el intento es lo que evita que la pantalla se quede dando vueltas cuando
una capa no está disponible: sin él, cada repintado volvería a pedir la imagen que ya falló.

**Y un fallo que encontraron los datos de verdad, contado porque es de los que no se ven.** Con la
finca real (ninguna forma medida) no hay caja, así que no hay dirección de imagen; pero la pantalla
pintaba igualmente un `<img src="">`. El navegador pedía **la propia página** como si fuera una foto,
esa petición fallaba, y el agricultor acababa leyendo **«No se ha podido traer la imagen del mapa»**
cuando lo que pasa es que no hay nada que enseñar. Un aviso que habla de un fallo que no ha ocurrido
es peor que no decir nada: manda a mirar la cobertura cuando el problema es que faltan las formas. Se
arregló en el componente (**sin dirección no se pinta imagen**) y lo cazó el navegador con los datos
reales: `IMAGENES: 0` (§5.2 bis).

### 3.10. Previsualizar y apuntar son **dos caminos separados**, y hay pruebas de los dos

La previsualización se pide a `/api/versiones/previsualizar`, que solo lee. El botón de apuntar es el
**único sitio** de la aplicación que llama a `/api/versiones/aplicar`, y hay tres comprobaciones
distintas de que es así:

1. La función del ensayo **no contiene** ninguna llamada a la ruta que escribe (se lee su código, sin
   comentarios, en `tests_js/tierras_y_versiones.test.js`).
2. En todo `app.js` hay **una sola** llamada a cada ruta, y la de escribir está dentro de la función
   del botón de apuntar.
3. Con un servidor de mentira delante: después de ensayar, el registro de peticiones **no tiene**
   ningún `POST /api/versiones/aplicar`; después de pulsar el botón, sí.

Y la pantalla lo dice con palabras: mientras `aplicada` sea falso, se lee «Esto es solo un ensayo: no
se ha apuntado nada de nada»; el botón de apuntarlo sale aparte y **solo cuando hay un ensayo delante**.

### 3.11. El lote se arma copiando los números que vinieron, y **sin rellenar ninguno**

`loteDesdeLasVersiones` es una función pura y exportada, con prueba propia. Copia los siete números de
la referencia tal y como vinieron, la forma y las dos áreas de la fuente; y **lo que no vino no se
manda** (un `null` explícito no es lo mismo que no mandarlo: al otro lado,
`CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA` existe justo para que el SIGPAC no se lleve por delante las
hectáreas que declaró el agricultor).

---

## 4. Lo que **no** se ha hecho, y por qué

### 4.1. Medir distancia y área sobre el mapa: **no se ha hecho**

Lo nombra el contrato («medir distancia/área»). No está, y el motivo es que **no hay ninguna función
que mida sobre la pantalla**: `geo.area_ha` mide un WKT en el servidor, y una regla sobre el mapa
necesita convertir píxeles a metros con la proyección bien hecha y decidir qué se hace con una línea
de tres puntos. Escribirlo a medias habría dado un número con pinta de exacto y sin serlo, que es
justo lo que este proyecto prohíbe. **No se ofrece un botón que no mida nada.**

### 4.2. La fecha de la imagen: **no se sabe, y se dice**

El contrato pide el cambio de capa «con su leyenda y su fecha». La leyenda está (qué enseña cada capa
y quién la da). La fecha **no se puede saber**, y está comprobado, no supuesto:

```powershell
# 03/10/2026, contra los dos servicios de verdad
https://www.ign.es/wms-inspire/pnoa-ma?service=WMS&request=GetCapabilities   -> 200, sin ninguna dimensión de tiempo
https://sigpac-hubcloud.es/wms?service=WMS&request=GetCapabilities           -> 200, sin ninguna dimensión de tiempo
```

Ninguno de los dos publica de qué día es la imagen. Poner la fecha de hoy afirmaría que la ortofoto es
de hoy —y la ortofoto puede ser de hace ocho años—, así que lo que se hace es **decirlo en la
pantalla**: «De cuándo es la imagen: No se sabe: el servicio que da la imagen no dice de qué día es».
El hueco está preparado (`capa.fecha` y `capa.fecha_texto`) para el día que un servicio lo publique.

### 4.3. La capa de «avisos»: **no existe ningún servicio que la dé**

El contrato la nombra («cambiar ortofoto/SIGPAC/cultivos/avisos»). Las tres que hay son las que hay:
la ortofoto del IGN, los linderos del SIGPAC y el cultivo declarado del SIGPAC (`sigpac.CAPAS_DEL_MAPA`,
comprobadas contra los servicios de verdad). **No se ofrece un botón de avisos** y la pantalla dice por
qué (`capa_avisos_no_esta`). Hay una prueba que impide que alguien «arregle» el hueco añadiendo una
capa vacía.

### 4.4. Lo que no viaja en la dirección

El zoom y el punto que se está mirando en el mapa **no** van en la dirección (sí van los filtros, la
agrupación, la capa, la tierra enfocada y las tierras marcadas). Meter coordenadas en la barra de
direcciones es una decisión que T04 dejó abierta a propósito, y este ticket no la ha tomado.

### 4.5. Las dos pantallas nuevas **no se recorren en un navegador de verdad**

`scripts/comprobar_en_un_navegador.py` **no es de este ticket** y su lista de rutas no incluye las dos
pantallas nuevas, así que no se ha tocado. **Lo que está comprobado:** el guion entero pasa contra un
servidor aislado (incluidas las tres anchuras, 390, 1024 y 1440 px, y la pantalla «las tierras» de
siempre, que comparte con la nueva el armazón, el botón y el aviso). **Lo que NO está comprobado:** que
las dos pantallas nuevas se dibujen en un navegador de verdad. Se pide en §7.

### 4.6. Cosas del contrato que no se han hecho, dichas con su nombre

* **La exportación de la vista** («exportar vista»): no hay ningún botón que saque a CSV lo que se está
  viendo. Existe la descarga de datos de la finca entera (`sacar-datos`), que es otra cosa.
* **Elegir columnas y paginación**: no están. La tabla enseña siempre las mismas diez columnas y las 64
  tierras de una vez (con desplazamiento horizontal cuando no caben). El contrato §2.4 los pide para
  las tablas; en esta entrega no ha habido tiempo, y es más honesto decirlo que poner un botón que no
  haga nada.
* **Las tarjetas del móvil**: la lista de esta pantalla es una tabla con desplazamiento horizontal en
  el móvil, no una tarjeta por tierra como en «mis cosas». El contrato pide que en móvil no haya
  «tabla comprimida», y una tabla que se desplaza no se comprime, pero **no es la tarjeta** que pide
  §2.4.
* **`scripts/humo.py`**: no se ha tocado (no es de este ticket). No tiene ningún caso de T06; se pide
  en §7.

---

## 5. Cómo se comprueba

```powershell
cd F:\EspacioCodigo\CueDigital\backend

# Las pruebas nuevas y las que vigilan lo que se ha tocado
..\.venv\Scripts\python.exe -m pytest tests\test_t06_tierras_y_mapa.py -q --junit-xml=$env:TEMP\t06_py.xml
node --test tests_js/tierras_y_versiones.test.js

# La suite entera
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\t06_todo.xml
node --test "tests_js/*.test.js"

# El recorrido contra un servidor de verdad, **aislado** (nunca la base del agricultor)
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\t06_humo.db"
$env:CUEDIGITAL_ADJUNTOS="$env:TEMP\t06_adjuntos"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8010
..\.venv\Scripts\python.exe scripts\humo.py http://127.0.0.1:8010
..\.venv\Scripts\python.exe scripts\comprobar_en_un_navegador.py http://127.0.0.1:8010
```

### 5.1. Los recuentos, medidos

| Qué | Pruebas | Fallos | Errores |
|---|---|---|---|
| `tests/test_t06_tierras_y_mapa.py` (nuevo) | **28** | 0 | 0 |
| `tests_js/tierras_y_versiones.test.js` (nuevo) | **41** | 0 | 0 |
| `tests_js/interfaz.test.js` (con **6 nuevas**: 300 → 306) | **306** | 0 | 0 |
| `tests_js/rutas.test.js` (pruebas ampliadas) | **45** | 0 | 0 |
| `tests/test_revision_t06.py` (del revisor, contra este ticket) | **42** | **0** | 0 |
| Suite de Python entera | **3536** | **0** | 0 |
| Suite de JavaScript entera | **805** | 0 | 0 |
| `scripts/humo.py` (servidor aislado) | 79 comprobaciones | ver §5.4 | — |
| `scripts/comprobar_en_un_navegador.py` (servidor aislado) | todas | **0** | — |

**Estas cifras están medidas justo antes de escribir esto y después no se ha tocado ni una línea**
(§8.2). Con el ticket entero, las dos suites están en verde: **3536 pruebas de Python con 0 fallos y 1
saltada, y 805 de JavaScript con 0**.

**Y una medición que conviene enseñar tal cual, porque engaña:** la primera pasada de esta misma
medición dio **3538 pruebas de Python con 2 fallos**, los dos en `_comprobacion_navegador.html`. Ese
fichero **no es del proyecto**: lo escribe `scripts/comprobar_en_un_navegador.py` dentro de
`backend/web/` *mientras corre* y lo borra al terminar (había 14 procesos de Chrome abiertos en ese
momento). La prueba de ficheros de texto **se parametriza sobre todos los ficheros del repositorio**,
así que su aparición suma dos casos y esos dos fallan por la marca de orden de bytes que lleva. No es
un fallo de este ticket y no se «arregla» tocando nada: se arregla **no midiendo mientras corre ese
guion**. Queda dicho para que nadie pierda una tarde con ello.

La suite de Python empezó en **3282** pruebas con 0 fallos. Con **solo este ticket** son **3310** (las
28 nuevas, §1.9). El resto es de los otros tickets que están entrando a la vez (T05, T09, T10 y T15).

Los tres documentos que llevan el recuento (`README.md`, `AGENTS.md`,
`docs/LO_QUE_PIDE_LA_JUNTA.md`) dicen **3536 pruebas de Python y 805 de JavaScript**. Se han peleado un
poco: los tres agentes que estamos tocando el árbol los poníamos al día a la vez y en un momento dado
decían números distintos —la prueba que los vigila lo cazó en cuanto pasó—. Queda escrito porque es lo
que va a volver a pasar: **el recuento de varios tickets a la vez solo se cierra cuando todos han
parado.**

### 5.2. Un recorrido a mano contra el servidor aislado, con sus resultados

Además de las suites, el 03/10/2026 se hizo un recorrido entero contra el servidor de verdad
(`http://127.0.0.1:8010`, base de datos en el temporal): se dio de alta una cuenta, una tierra **con
forma** y otra **sin forma**, y se llamó a lo que este ticket ha construido. Lo que salió, tal cual:

```
tierra sin forma: 201  superficie: None            <- «no lo sé», y no un cero
vista: 200
  tierras: [('El Prado de arriba', True, 1), ('El alto sin medir', False, 0)]
  totales: {"tierras": 2, "con_forma": 1, "sin_forma": 1, "sin_cultivo": 2,
            "sin_hectareas": 1, "sin_revision": 2}
  caja: {"hay_forma": true, "tierras_con_forma": 1,
         "caja": {"oeste": -5.56, "sur": 40.9, "este": -5.55, "norte": 40.91}}
  pac: [('con_referencia', 1), ('sin_referencia', 1), ('con_hectareas', 1), ('sin_hectareas', 1)]
imagen del mapa: 200  image/jpeg  68126 bytes      <- la ortofoto del IGN, de verdad
  fecha: None | No se sabe: el servicio que da la imagen no dice de qué día es
interfaz tiene tierras: True  y versiones: True

previsualizar: 200   aplicada: False
  versiones antes: 0   y después de ensayar: 0     <- NO escribe
aplicar: 200         aplicada: True
  versiones de la tierra: [(2026, 'SIGPAC', 'Sin forma: no ha venido el polígono', False)]
```

Las tres cosas que este recorrido demuestra y que ninguna prueba de unidad demuestra sola: que la
**imagen del mapa llega de verdad** (el servidor habla con el IGN y devuelve un `image/jpeg` de 68 KB),
que **previsualizar no cambia el número de versiones**, y que una importación apuntada deja la versión
con la frase «Sin forma: no ha venido el polígono» y `tiene_forma` en falso, que es el contrato §2.1
(«un polígono ausente no se inventa») cumplido de punta a punta.

### 5.2 bis. **La finca de verdad**: 64 tierras, ninguna con forma, en un navegador de verdad

Este apartado existe porque el coordinador midió los datos reales y el resultado cambia lo que
significa «datos representativos»: **0 de 64 tierras tienen geometría**. O sea que el caso «no hay
nada que dibujar» **es el caso normal**, no el raro, y había que verlo con los datos de verdad y no
solo con los tres inventados de las pruebas de unidad.

**Cómo se ha hecho, y qué se ha tocado.** Se copió `backend/cuedigital.db` a la carpeta **temporal**
(`t06_real.db`, mismo sha256 `71456b0b…` que el original; **el original no se ha abierto**), se levantó
un servidor aislado sobre esa copia, y para poder mirar los datos por la API se hizo **una sola
escritura en la copia**: dar acceso de ayudante a una cuenta nueva sobre la explotación del agricultor
(`accesos_a_fincas`), que es exactamente lo que hace la aplicación cuando dos personas llevan la misma
finca. **No se cambió ni una tierra, ni una campaña, ni un cultivo, ni una hectárea.**

**Lo que dice la API con esos datos** (`GET /api/parcelas/vista`):

```
tierras: 64          con forma: 0        sin forma: 64
sin decir el cultivo: 10                  sin hectáreas dichas: 0
sin ninguna versión de este año: 64       campaña: 2026
mapa: hay_forma=False   tierras_con_forma=0   caja=None        <- no hay nada que dibujar
NO hay ningún total de superficie: True
la zona de nitratos NO aparece en la respuesta: True
tierras con la referencia completa: 64 de 64
municipios distintos: 7
cultivos del filtro: 6 opciones (la mayor, 19 tierras)
revisión: [('Sin ninguna versión de este año', 64)]     <- no se ofrece «sin revisar», que afirmaría
pac: [('con_referencia', 64), ('con_hectareas', 64)]       que alguien miró algo
```

**Y la pantalla, en un navegador de verdad** (Chrome sin ventana, la pantalla pintada con esos 64
datos reales y el `estilos.css` de la aplicación; los 390 px **dentro de un hueco de 390**, porque al
navegador sin ventana no se le puede pedir una ventana más estrecha de 500 px):

| Se le pidió | Ancho de la página / el que cabe | ¿Cabe? | Nombre de 42 caracteres | ¿Entero? | Puntos suspensivos | Ancho de la columna | Renglones | Filas | Nombres repetidos avisados | Casillas | Trozos dibujados | Imágenes | ¿Dice que no hay forma? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **390 px** | 375 / 390 | **sí** | `503/10059-1 BARBECHO TRADICIONAL (3.54 ha)` | **sí** | `clip` | 206 px | 2 | **64** | **9** | **64** | **0** | **0** | **sí** |
| 1024 px | 1009 / 1024 | **sí** | el mismo | **sí** | `clip` | 186 px | 3–4 | 64 | 9 | 64 | 0 | 0 | sí |
| 1440 px | 1425 / 1440 | **sí** | el mismo | **sí** | `clip` | 296 px | 2 | 64 | 9 | 64 | 0 | 0 | sí |

Lo que dicen esos números, uno por uno:

* **La página no se sale de lo ancho en ninguna de las tres anchuras.** La tabla es la que se desplaza
  dentro de su hueco, que es lo que manda el CSS (`.t06-tabla-scroll`).
* **El nombre largo sale entero** en las tres: `text-overflow: clip`, sin recortar y sin puntos
  suspensivos. A 390 px ocupa dos renglones en una columna de 206 px (se le dio un mínimo a esa
  columna **a raíz de esta medición**: antes se quedaba en 105 px y el nombre ocupaba tres renglones).
* **Las 64 tierras están las 64 veces**, cada una con su casilla: sin forma no es sin datos.
* **9 filas avisan de que su nombre está repetido** (§1.7), y la columna del nombre no se rompe por
  llevar el aviso dentro: 2 renglones a 390 px y a 1440, 3–4 a 1024.
* **Cero polígonos dibujados y cero imágenes pedidas.** Con los datos reales se descubrió aquí un
  fallo de verdad (§3.9): la pantalla pintaba un `<img src="">`, el navegador pedía la propia página
  como si fuera una foto y el agricultor acababa leyendo «No se ha podido traer la imagen del mapa»
  cuando lo que pasa es que no hay nada que enseñar. Arreglado y con su prueba.
* **La pantalla dice que no hay ninguna forma medida**, que es la frase que tiene que salir en la
  finca de verdad.

**Y el vínculo fila ↔ polígono y la comparación de campañas, con estos datos, no se pueden ver**: no
hay ni una geometría y no hay ni una versión. Para poder probarlos **se sembraron formas y versiones
sintéticas en base temporal**, y así está dicho en §1.6 y §1.7, en el apartado 8 del fichero de
pruebas y aquí: **lo que se ha probado con datos de verdad y lo que se ha tenido que inventar para
probar.**

**Y las cosas de §1.7, comprobadas con los datos reales después de arreglarlas. Esta medición es de su
finca (filtrando por su explotación, que es lo que hay que hacer siempre):**

```
pueblos escritos en las 64 tierras de SU FINCA (7 municipios, ninguno repetido con otra ortografía):
  CALVARRASA DE ARRIBA 54 · MACHACON 3 · TERRADILLOS 2 · PELABRAVO 2 · ARAPILES 1 ·
  CARBAJOSA DE LA SAGRADA 1 · CALVARRASA DE ABAJO 1
opciones del filtro: las 7 formas escritas, con sus 7 recuentos exactos (ninguna inventada)
  -> NO hay aquí dos formas del mismo pueblo: la tierra escrita «Calvarrasa de Arriba» está en
     OTRA explotación de la base (la 3), y CALVARRASA DE ABAJO es otro pueblo distinto.
     El cotejo sin tildes sigue haciendo falta por MACHACON (cuaderno de la Junta) contra
     Machacón (lista oficial del INE), y por los nombres con dos espacios de dentro.

64 tierras y 59 nombres distintos: 507/91-3 AVENA (1 ha) tres veces, y tres nombres más dos veces
  «507/24-1 BARBECHO TRADICIONAL (4.44 ha)»: 2 filas (n.º 52 y 53) con la MISMA referencia y la
  MISMA superficie -> el programa lo dice en las dos filas y el número es lo que las distingue

64 tierras y 51 recintos distintos: 37-70-0-0-507-24-1 lo comparten 9 tierras (n.º 50 a 58) y
  37-70-0-0-507-91-3 lo comparten 6 -> al tocar ese trozo se encienden las nueve, no una al azar
```

La copia temporal se borró al terminar, para no dejar datos del agricultor (con su NIF) en la carpeta
temporal de la máquina.

### 5.3. La comprobación en un navegador de verdad, entera

```
[OK] 390 px · las tierras: la aplicación está montada dentro del hueco, no en blanco
[OK] 1024 px · ... (las 24 rutas que recorre el guion)
[OK] 1440 px · ...
[OK] no queda ningún fichero de la comprobación dentro de la aplicación

RESULTADO: la interfaz se abre y se dibuja en un navegador de verdad
```

### 5.4. Lo que sale en rojo, y de quién es

* **`scripts/humo.py`: 70 `[OK]` y 9 `[FALLO]`**, y **ninguno es de T06**. Los nueve están en el
  dictado (3b: «ha reconocido la parcela por su nombre», «ha reconocido el producto…», «el dictado NO
  ha guardado nada») y en el certificado y la firma (11 y 12). Las dos cosas necesitan **algo de
  fuera que aquí no está**: el dictado necesita un modelo configurado
  (`CUEDIGITAL_CERTIFICADO` no, un proveedor sí) y el certificado necesita `CUEDIGITAL_CERTIFICADO`.
  El guion se para ahí (`KeyError: 'firmante_nif'`) y por eso no llega al final. **La sección del mapa
  entera pasa**, incluidas las cuatro comprobaciones de `/api/mapa/estado` que este ticket ha
  ampliado.
* El resto de la suite de Python: **0 fallos** en la última medición (3536 pruebas).
* **Los dos fallos de la medición anterior** eran `tests/test_ficheros_de_texto.py` sobre
  `_comprobacion_navegador.html`, el fichero **transitorio** que escribe dentro de la aplicación el
  guion de comprobación en un navegador mientras corre (§5.1). Con ese guion parado, no aparecen.
* **Y lo que sí era mío, arreglado y comprobado**: el `NameError` de §8.1 (una llamada sin el guion
  bajo después de renombrar), la revisión de T06 encontró **siete defectos reales** que ya están
  corregidos (§1.8), y dos guardianes de ficheros que son de este ticket (`tests_js/rutas.test.js` y
  `tests_js/interfaz.test.js`) se quedaron cortos cuando los otros agentes añadieron `semillas` y
  `siembras`: se pusieron al día (la tabla de direcciones, la lista de módulos del menú y la copia de
  textos del servidor del fichero de pruebas).

### 5.5. Ninguna prueba toca la base del agricultor

`tests/conftest.py` fija `CUEDIGITAL_DATABASE_URL` y `CUEDIGITAL_ADJUNTOS` a una carpeta temporal antes
de importar nada de `app`. El recorrido de humo y el del navegador se han pasado **contra un servidor
aislado**, con la base en el temporal (`CUEDIGITAL_DATABASE_URL=sqlite:///$env:TEMP\t06_humo.db`):
`backend/cuedigital.db` **no se ha abierto en ningún momento**.

---

## 6. Ficheros

**Creados:**

```
backend/web/react/pantallas/tierras_mapa.js        Las tierras: tabla, filtros, grupos, selección y mapa
backend/web/react/pantallas/tierra_versiones.js    Lo que ha sido una tierra: versiones, comparación y ensayo
backend/tests_js/tierras_y_versiones.test.js       31 pruebas de comportamiento
backend/tests/test_t06_tierras_y_mapa.py           19 pruebas del servidor
docs/T06_MAPA_Y_TIERRA.md                          Este documento
```

**Modificados (todos con las herramientas de edición, nunca reescribiendo desde PowerShell — ver §8):**

```
backend/app/textos.py               + TIERRA_Y_MAPA y VERSIONES_EN_PANTALLA (al final), registrados
backend/app/schemas.py              + los esquemas de la vista (al final)
backend/app/routers/parcelas.py     + GET /api/parcelas/vista y sus tres funciones de recuento
backend/app/routers/mapa.py         /api/mapa/estado dice la leyenda, la fecha y qué pasa si no llega
backend/app/routers/interfaz.py     + "tierras" y "versiones" (con su motivo escrito)
backend/web/react/componentes.js    + OpcionesParaElegir (la fila de botones de elegir)
backend/web/react/rutas.js          + las dos direcciones nuevas
backend/web/react/pantallas/tierras_mapa.js  (creado arriba)
backend/web/app.js                  el cableado: importaciones, estado, direcciones, 20 acciones y las
                                    funciones de las dos pantallas
backend/web/estilos.css             + las reglas de T06, todas con las variables del :root
backend/web/service-worker.js       + los dos ficheros en la caché del campo y versión 64
backend/tests_js/rutas.test.js      las dos direcciones en la tabla y en la ida y la vuelta
backend/tests_js/interfaz.test.js   + 6 pruebas de cableado y la copia de los textos nuevos
docs/REACT.md                       la tabla de pantallas, el apartado de T06 y los recuentos
README.md, AGENTS.md, docs/LO_QUE_PIDE_LA_JUNTA.md   los recuentos de pruebas (compartidos)
```

---

## 7. Lo que hace falta de otros, y lo que se pide

**Desde el 03/10/2026 este ticket no toca código.** El coordinador ha dado `models.py`, `schemas.py`,
`textos.py`, `web/**` y `tests_js/**` en exclusiva al ticket T10 (semillas), así que lo que sigue son
peticiones para él, con el fichero y lo que habría que hacer. **Nada de esto está a medias: son mejoras
y comprobaciones que faltan, no defectos conocidos.**

1. **`scripts/comprobar_en_un_navegador.py`**: añadir `#/tierras/mapa` y `#/tierras/<id>/versiones` a
   su lista de rutas. Es lo único que falta para poder decir que **las dos pantallas nuevas se dibujan
   en un navegador de verdad**: hoy se ha medido la pantalla de las tierras con los datos reales
   pintada aparte (con el mismo componente y el mismo CSS, §5.2 bis), pero no dentro de la aplicación
   entera.
2. **`scripts/humo.py`**: el caso 34 que ha añadido el coordinador está muy bien y comprueba lo que
   más importa (que los recuentos cuadren con las filas y que una tierra sin forma siga en la lista
   sin anillos ni dibujo). Lo que le añadiría, y está razonado en el informe final: **(a)** que
   `totales.con_forma` y `mapa.tierras_con_forma` sean el mismo número (fue el defecto D2 de la
   revisión: decían 2 y 1 en la misma respuesta); **(b)** que la caja que da la vista **la acepte el
   propio `/api/mapa/imagen`** (defecto D7: la rechazaba con 422 y el agricultor leía «puede ser la
   cobertura») y que `extension` contenga `caja`; **(c)** que **el recuento de cada opción de los
   filtros cuadre con las filas que devuelve** —el contrato que más se rompió en este ticket: el filtro
   del pueblo llegó a decir 3 y enseñar 4—; y **(d)** que la respuesta **no traiga ningún total de
   superficie** ni un campo que se le parezca.
3. **Las columnas elegibles y la paginación** de la tabla (§4.6): las pide el contrato para todas las
   tablas y aquí no han entrado. Es trabajo aparte y hay que decidir si va en este ticket o en otro.
4. **La fecha de la imagen** (§4.2) y **la capa de avisos** (§4.3): dependen de que un servicio de
   fuera publique algo que hoy no publica. No es código pendiente.
5. **Una decisión, si el coordinador quiere otra cosa**: cuando la finca pasa de medio grado hay una
   tensión real entre «la caja que da la vista la acepta el propio programa» (D7) y «la caja envuelve
   todas las formas». Se ha resuelto **recortando la que se pide** y publicando la envolvente en
   `extension`, y el revisor ya lee así las dos pruebas. Si se prefiere lo contrario (devolver la
   envolvente y recortar en la pantalla), son **dos líneas** de `parcelas.py` y una de `app.js`.

---

## 8. Dos cosas que salieron mal, contadas como fueron

### 8.1. Un renombrado de última hora dejó una llamada sin el guion bajo

Al montar la respuesta de `GET /api/parcelas/vista` se llamaba `la_clave_del_recinto_de_una_tierra(...)`
y la función se llama `_la_clave_del_recinto_de_una_tierra` (con guion bajo, porque es privada del
módulo). El servidor devolvía **500** y la traza lo decía sin rodeos:

```
File "backend/app/routers/parcelas.py", line 406, in las_tierras_de_la_finca
    clave_recinto=la_clave_del_recinto_de_una_tierra(parcela),
NameError: name 'la_clave_del_recinto_de_una_tierra' is not defined.
Did you mean: '_la_clave_del_recinto_de_una_tierra'?
```

Lo encontró el caso de T06 que el coordinador añadió a `scripts/humo.py`: **antes de eso, ninguna prueba
de las 19 mías lo había visto**, porque todas pasan por el cliente de pruebas de FastAPI y ese error
estaba en el camino… de la respuesta entera. Con el fallo dentro, **14 de las 19 pruebas estaban en
rojo**; el arreglo es una letra.

**Lo que hay que aprender de esto, y por eso queda escrito:** un renombrado al final es justo el cambio
que ninguna prueba caza si la suite ya se corrió antes, y aquí había dos formas de no caer:

1. **correr la suite después del último cambio, no antes**; y
2. **pasar el recorrido contra un servidor de verdad**, que es donde se ve un 500 de verdad y no un
   `NameError` atrapado por el arnés.

### 8.2. El informe dio por buenas unas cifras medidas antes del último cambio

El informe anterior decía «suite de Python 3422, 0 fallos». Ese número **se midió de verdad**, pero
**antes** del último cambio del árbol, y el árbol que se entregó tenía el `NameError` de §8.1 y, por
tanto, estaba en rojo por mi culpa. Un dato medido antes de la última edición no es el dato de lo que
se entrega.

**La regla que queda para este documento y para los que vengan: los recuentos se miden justo antes de
escribirlos, y si después se toca una sola línea, se vuelven a medir o se dice que no se han medido.**
Los recuentos de §5.1 se han medido así, en la última pasada y sin tocar nada después.

---

## 9. Una trampa del entorno que ha vuelto a morder, y se deja escrita

Al renombrar una función dentro de `tierras_mapa.js` se usó **`Get-Content -Raw | Set-Content` de
PowerShell**, que es justo lo que `AGENTS.md` §7 prohíbe: el fichero se decodificó como cp1252 y se
reescribió como UTF-8, así que **todos los acentos quedaron como «Ã³»** y el fichero empezó a tener
marca de orden de bytes. Lo cazó `tests/test_ficheros_de_texto.py`, que existe exactamente para esto.
La vuelta atrás se hizo **línea a línea** (codificar a cp1252 y decodificar como UTF-8), como manda el
mismo apartado, y **una línea no se pudo deshacer** porque llevaba un byte (`0x8D`) que no existe en
cp1252: se reescribió a mano. El fichero quedó sin marca de orden de bytes, sin mojibake y compilando.

Lo que se aprende y queda dicho: **para tocar un fichero con acentos, la herramienta de edición, nunca
un `-replace` de PowerShell.** Aquí ha costado una hora de trabajo que no hacía falta.
