# La revisión visual de D05, y su estado

> **Actualización independiente 22/10:** la revisión con visión ya está hecha en
> [REVISION_CON_VISION.md](REVISION_CON_VISION.md). Resultado: **CAMBIOS_SOLICITADOS**.
> Las capturas originales tenían rutas/tamaños incorrectos y han sido sustituidas.
> Las afirmaciones y medidas históricas de abajo no constituyen aprobación visual.

> **Estado: EN_REVISION.** *Las capturas están hechas y las medidas sin vista, también. **La revisión con visión
> no se ha podido hacer**: el modelo de esta sesión **no acepta imágenes** — contesta «does not declare image
> input» —, y el encargo dice, con estas palabras: «si el modelo no ve imágenes, mantener **EN_REVISION** hasta que
> un revisor que sí las vea emita resultado».*

---

## 1 · Lo que sí está hecho

### Las capturas, de las cinco anchuras que pide el encargo

*Sacadas de la aplicación de verdad, con **una cuenta y unos datos temporales**: tres tierras con forma, para que las
pantallas no salgan vacías. En `docs/capturas-de-anchuras/`, tres pantallas por anchura —**inicio**, **tierras**
(`#/tierras/mapa`) y **cuaderno**—:*

    320x700 · 390x844 · 712x900 · 1024x768 · 1440x900

*El guion que las saca: `scripts/capturar_las_anchuras.py`.*

### Lo que se mide sin ver (`scripts/medir_el_tacto_y_el_foco.py`)

| medida | móvil (390) | ordenador (1440) |
|---|---|---|
| **controles táctiles** | **0 por debajo de 44×44** en inicio y tierras | *algunos de 40 px de alto — es un ratón, no un dedo* |
| **el foco se ve** | **sí**: `outline: 3px solid` con el **tabulador** | ídem |
| **lo que se pulsa, con el teclado** | *se llega tabulando* | ídem |

***Y un falso negativo, cazado y corregido***: *la primera versión de la comprobación del foco decía «no se ve»,
porque enfocaba **con código** (`.focus()`) y el CSS usa **`:focus-visible`** — que **no se activa así**. *Con el
**tabulador**, el contorno aparece: `BUTTON solid 3px rgb(13, 43, 24)`.* **La aplicación estaba bien; la medición
estaba mal.**

### El contraste, medido con la fórmula (`scripts/medir_el_contraste.py`)

*Sobre los colores que el navegador tiene puestos de verdad — `getComputedStyle`, subiendo a buscar el fondo efectivo
cuando el del elemento es transparente — y con la fórmula de la WCAG:*

| pantalla | el peor contraste | textos por debajo de 4,5 | por debajo de 3,0 |
|---|---|---|---|
| inicio | **6,37:1** | **0** | **0** |
| tierras | **6,37:1** | **0** | **0** |
| cuaderno | **6,3:1** | **0** | **0** |

***La paleta pasa la WCAG AA con margen*** — *el mínimo para texto normal es 4,5 y el peor texto de estos tres
pantallas está en 6,3.*

*Lo que esto **no** mide: el contraste **sentido** — un texto fino sobre un fondo claro se lee peor de lo que dice el
número —. **Eso solo lo ve quien mira**, y es otra vez la revisión con visión.*

### Escape y el foco de regreso (`scripts/verificar_el_escape_y_el_foco.py`)

***En el móvil, con el menú abierto:***

    se abre el menú                →  ***su botón de cerrar se ve*** (1)
    se pulsa Escape                →  ***el menú se cierra*** (0)
    y el foco                      →  ***vuelve al botón que lo abrió*** (`menu-abrir`)

***Las dos comprobaciones pasan.*** *Y por el camino salieron dos cosas que no eran de la aplicación: `#/inicio` **no
es una dirección** —el inicio es la raíz— y **el menú vive fuera de `#pantalla`**, así que medir su texto no dice
nada; hay que mirar su propio botón.*

### El zoom al 200 % y lo que se anuncia (`scripts/medir_el_zoom_y_lo_que_se_anuncia.py`)

| medida | inicio | tierras | cuaderno |
|---|---|---|---|
| **al 200 %**, ¿hay que arrastrar la página? | **no** | **no** | **no** |
| **el zoom se aplicó** (`visualViewport.scale`) | **2,00** | **2,00** | **2,00** |
| **lo que se pulsa, sin nombre** | **0** | **0** | **0** |
| **campos sin etiqueta** | **0** | **0** | **0** |
| **zonas `aria-live`** | 3 | 3 | 3 |

***Y el detalle que salva la comprobación***: *se mide **la escala de verdad** —`visualViewport.scale`— porque **un
zoom que no se aplica deja la comprobación vacía**: *si la página no cambia, decir «no se desborda» no prueba nada.*

***Lo que esto no comprueba***: *que el lector de pantalla **lea bien** lo que anuncia —el orden, el tono, si
interrumpe—. Eso necesita un lector de verdad, y no está hecho.*

---

## 2 · Lo que NO está hecho, y no se puede dar por bueno

**La revisión con visión**: *contraste real de cada texto sobre su fondo, jerarquía, si algo «se ve bien» a 320 px,
si los estados de error y vacío se distinguen a simple vista.*

*No la he hecho. **No la puedo hacer** con este modelo.*

**Cómo cerrarla**: *abrir `docs/capturas-de-anchuras/` —quince imágenes— y revisarlas; o pasar un revisor con
visión sobre ellas. **Hasta entonces, D05 no está cerrado.**

---

## 3 · Y lo que el encargo pide además, que sigue pendiente

- ~~el zoom al 200 %~~ — **HECHO** (*sin desbordamiento, y con la escala comprobada*);
- ~~Escape y foco de regreso~~ — **HECHO** (con el menú del móvil, que es lo que tapa la pantalla);
- **lector de pantalla de verdad** (*que se anuncie bien*: *los nombres y las etiquetas están medidos —0 sin
  nombre, 0 sin etiqueta, 3 zonas vivas—, pero **que se lean bien necesita un lector real**);
- ~~contraste medido~~ — **HECHO** (*no a ojo: la relación calculada sobre los colores reales*);
- ~~los cuatro recorridos completos~~ — **UNO EMPEZADO**: *tierra → trabajo → consumo, ver abajo*;
- **los otros tres**: *compra → recepción → lote → gasto → pago; venta → factura → cobro parcial → pendiente;
  papel → propuesta → confirmación/rectificación*.

---

## 4 · El primer recorrido: tierra → trabajo → consumo

*`scripts/verificar_el_recorrido_de_la_tierra.py`. **Por las puertas de verdad** —las mismas que usa la pantalla—,
no inventando filas en la base.*

| comprobación | |
|---|---|
| **la tierra se da de alta** por `POST /api/parcelas` | **201** ✅ |
| **el trabajo se apunta en ella** por `POST /api/tratamientos` | **201** ✅ |
| **la tierra sale en la lista** `#/tierras/mapa`, con su nombre | ✅ |
| **el cuaderno RECHAZA un tratamiento con un producto sin número de registro** | `V1_sin_registro` ✅ |
| **y RECHAZA uno sin decir por qué se echó** | `V10_sin_justificacion` ✅ |

***Las dos últimas no estaban en el guion: las destapó el recorrido.*** *Al intentar apuntar el tratamiento, el
cuaderno lo rechazó dos veces —primero por el producto, luego por la justificación—, y eso **es la aplicación
haciendo su trabajo**: un tratamiento sin producto identificable no vale para la Junta. **Comprobarlo vale más que
lo que se buscaba.***

### ***Lo que NO se ha podido comprobar, y es la mitad de lo que pedía el encargo***

**«Cada total abre sus registros por ID»**. *Las fichas —`#/apunte?id=N` y `#/tierra?id=N`— **contestan «esa
dirección no lleva a ninguna parte»***, también con la campaña y la finca en la dirección. **La aplicación las abre
por otro camino que no he encontrado**, y el botón de la fila de la lista **marca** —es la casilla de la selección
múltiple—, no abre la ficha.

### ***Corrección del 22/10/2026: el «defecto» no existe. Estaba equivocado yo.***

*Ayer se documentó aquí que las fichas no tenían dirección, con pruebas:*

    #/apunte?id=1  ·  #/apunte/1  ·  #/tierra?id=1  ·  #/tierra/1   ->  todas «no lleva a ninguna parte»

***Y la conclusión era falsa.*** *Las direcciones **son de camino, no de consulta**, y lo dice `react/rutas.js` con
todas las letras:*

    #/tierras/12              ***la ficha de una tierra***  — «funciona siempre: recargando, abriendo un enlace
                                directo, sin cobertura»
    #/cuaderno/<id>           ***un apunte***
    #/tierras/mapa            la vista de las tierras      (esta sí se usaba bien)

***Comprobado, y el enlace es permanente:***

| | |
|---|---|
| `#/tierras/1` abre la ficha de la tierra | ✅ |
| y al recargarla, lo mismo | ✅ |
| `#/cuaderno/1` abre el apunte | ✅ |
| y también aguanta la recarga | ✅ |

***Lo que falló fue el método***: *se probaron cuatro formas **inventadas** mirando el escritor de la dirección
—`apuntarLaDireccion`, que escribe `parametros`— en vez de **la tabla de patrones del lector** (`PANTALLAS`, en
`react/rutas.js`), que es la que manda. **Cuatro intentos y una conclusión falsa, cuando la respuesta estaba en la
cabecera de un módulo que no se abrió.***

***No había nada que arreglar en la aplicación.*** *El encargo dice «cada total abre sus registros por ID»: **se
cumple**.*

---

## 5 · El tercer recorrido: venta → factura → cobro parcial → pendiente

*`scripts/verificar_el_recorrido_del_dinero.py`. **Por las puertas de verdad**, comprobando **A06**, que el contrato
pide con nombre: **una factura de 121 con un pago de 40 deja 81 pendientes**.*

| comprobación | |
|---|---|
| **la venta se apunta, con su importe** (`POST /api/ventas`) | **201** ✅ |
| **la entrega se factura** (`POST /api/facturas-emitidas`) | **201** ✅ |
| **se apunta un cobro PARCIAL de 40** (`POST /api/cobros`) | **201** ✅ |
| **de 121 pagados 40 quedan 81** | `pendiente: 81.00` ✅ |
| **la venta sale en la tabla, con su 121** (`#/ventas`) | ✅ |
| **`#/ventas/facturas/1` abre la factura, con su pendiente** | ✅ |
| **y al recargarla, lo mismo** | ✅ |

***El pendiente no es cero***: *ese es el defecto que tendría un programa que diera la factura por cobrada al primer
pago, y aquí no pasa.*

***Y una dirección que NO existe, a propósito***: *`#/ventas/1` **no** es una pantalla — una venta es **una fila de la
tabla**, no una ficha. La tabla de patrones (`PANTALLAS`, en `react/rutas.js`) tiene `ventas/:id/importe` y
`ventas/:id/ajuste`, pero **no `ventas/:id`**; la ficha es **de la factura**: `#/ventas/facturas/:id`.*

***Eso es lo que se aprendió de la rectificación del 22/10***: *antes de decir «esto no existe», **se mira la tabla de
patrones del lector**, no la forma en que uno recuerda la dirección.*

---

## 6 · El cuarto recorrido: papel → propuesta → confirmación (lo que se puede andar sin OCR)

*`scripts/verificar_el_recorrido_del_papel.py`. **El código dice de sí mismo**: «**subir un papel no puede meter
ningún dato en el cuaderno**; leer es una puerta aparte y lo que sale de ella es una propuesta». **Eso es lo que se
comprueba.***

| comprobación | |
|---|---|
| **el papel se sube a la bandeja** (`POST /api/bandeja/subir`) | **201** ✅ |
| **y SUBIR no mete nada en el cuaderno** (*0 tratamientos antes y después*) | ✅ |
| **el papel sale en la bandeja** (`#/papeles/bandeja`) | ✅ |
| **su ficha se abre por su ID** (`#/papeles/bandeja/1`) | ✅ |
| **y aguanta la recarga** | ✅ |

***La segunda es la que importa***: *subir un papel **no** escribe en el cuaderno. **La separación entre «lo que llega»
y «lo que se apunta» está, y está medida.***

***Y una dirección que se acertó a la primera, por mirar la tabla de patrones***: *la bandeja **no** es `#/bandeja`,
es **`#/papeles/bandeja`** —«la lista vive dentro de la familia de los papeles, que es el renglón del menú del que
sale»—, y la ficha de un papel es `#/papeles/bandeja/<id>`.*

### ***Lo que NO se ha andado, y por qué***

***El OCR y la propuesta.*** *`POST /api/bandeja/<id>/leer` **es la puerta del OCR**, y sin proveedor **no lee un PNG de
un píxel**. La separación está comprobada —subir no escribe, leer propone, confirmar escribe—, pero **el recorrido
«papel → propuesta → confirmación» no se ha andado entero**: falta un lector de verdad.*

*El encargo lo prevé: «las pruebas que requieren proveedor… permanecen separadas y documentadas». **Esta lo está.***

---

## 7 · El segundo recorrido: compra → recepción → lote → gasto → pago

*`scripts/verificar_el_recorrido_de_la_compra.py`. **El más largo de los cuatro, andado entero por las puertas de
verdad.***

| paso | puerta | |
|---|---|---|
| **la compra** | `POST /api/facturas` (*multipart: los datos y el papel*) | **201** ✅ |
| **el artículo y su lote** | `POST /api/almacen/articulos` · `/lotes` | **201** ✅ |
| **la recepción** | `POST /api/almacen/recepciones` | **201** ✅ |
| **el gasto** | `POST /api/gastos` | **201** ✅ |
| **el pago** | `POST /api/gastos/pagos` | **201** ✅ |

***La cadena entera, de la compra al pago.***

### ***Y dos errores que enseñaron la forma, en vez de estorbar***

*Los dos primeros intentos fallaron, y **los mensajes decían exactamente qué hacer**:*

- *`«Un albarán sin decir qué venía no apunta nada. Escribe al menos una cosa: qué producto, cuánto y de qué lote.»`*
  → *el albarán lleva **líneas**, no datos sueltos en la raíz;*
- *`«"fitosanitarios" no es ninguna de las categorías que hay (abono, fitosanitario, semilla, gasoleo…). Elige una de
  la lista o apúntalo como "Otra cosa" y escribe en el concepto lo que fue.»`* → *`fitosanitario`, **singular**.

***Eso es lo que el encargo llama «revisar también el texto de ayuda, vacío, error»: un error que dice qué hacer.***

### ***Y la compra, en el navegador — ya añadida***

*El guion se quedó primero en las cinco puertas; **le faltaba abrir la compra en el navegador**. Ya está:*

| | |
|---|---|
| **`#/compras/1` abre la compra, con su proveedor** | ✅ |
| **y aguanta la recarga** | ✅ |

    Comprobaciones: 7   Fallos: 0

***Y la dirección se acertó a la primera por mirar la tabla de patrones***: *`compras/:id` está, y se leyó **antes**
de escribir el guion. **La lección de la rectificación, aplicada dos veces seguidas.***
