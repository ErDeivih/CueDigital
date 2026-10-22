# La revisión visual de D05, y su estado

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

### ***El hallazgo***: las fichas no tienen dirección, y el camino del código está muerto

*Se probó a conciencia:*

    #/apunte?id=1                    ->  «Esa dirección no lleva a ninguna parte»
    #/apunte?id=1&campana=2026&finca=1 ->  «Esa dirección no lleva a ninguna parte»
    #/apunte/1                       ->  «Esa dirección no lleva a ninguna parte»
    #/tierra?id=1  ·  #/tierra/1      ->  «Esa dirección no lleva a ninguna parte»

***Y ningún botón de la interfaz produce esas direcciones.*** *En el cuaderno, cada apunte tiene **CORREGIR**,
**BORRAR** y **SACAR DE UN LOTE** — ninguno abre una ficha. Y la fila de la lista de tierras, al pulsarla, **marca**
(es la casilla de la selección múltiple), no abre la tierra.*

***Conclusión***: *el enrutador **tiene** las claves `apunte` y `tierra` —están en `DIRECCION_PROPIA` y en
`apuntarLaDireccion`, que escribe `?id=`—, pero **nada las produce y escribirlas a mano contesta «no lleva a ninguna
parte»**. El camino está **muerto**.*

***Y eso es un defecto contra el contrato***: *el encargo dice «cada total abre sus registros por ID y conserva
contexto», y **ese enlace permanente al registro no existe** para un apunte ni para una tierra. **No es que no se
haya comprobado: es que no está.***

*Lo que sí tienen dirección propia: la compra (`#/compras/<id>`), la tierra **en su pantalla** (`#/tierras/mapa`),
el apunte **en su lista** (`#/cuaderno`), y la PAC, la bandeja y el almacén. **Lo que falta es el registro suelto.***

### ***La causa, hasta donde se ha llegado — y lo que falta para cerrarla***

*Se descartaron dos explicaciones fáciles:*

- ***no es una carrera de arranque***: *`arrancarSesion` hace `await cargarDatos()` **antes** de`abrirLaDireccion()`,
  y se probó **con el cuaderno ya abierto** -«1 apunte en el cuaderno»- cambiando la dirección a mano:
  **también contesta «no lleva a ninguna parte»**;*
- ***no es que el apunte no exista***: *el cuaderno lo tiene cargado.*

***La hipótesis que queda***: *el bloque que debería abrirlo —`if (clave === "tierra" || clave === "apunte")`— **no
se ejecuta**: o el lector de la dirección no reconoce `apunte`/`tierra` como pantallas, o `parametros.id` llega
vacío y `Number(undefined)` no casa con ningún identificador. **Las dos se comprueban en un paso** —leyendo
`leerLaDireccion`— y **es lo primero de la próxima ronda.***

***No se ha tocado el código para arreglarlo***: *un `if` añadido a ciegas en el lector de direcciones, sin saber
cuál de las dos es, es la clase de arreglo que rompe otra cosa y no se nota hasta dentro de tres cortes.*

***Nada de eso está hecho.** Este documento dice lo que hay y lo que falta, sin redondear.*
