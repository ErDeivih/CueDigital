# T10 — Semillas, fotos de etiqueta y asignación a siembra

**Qué es esto.** El ticket T10 tenía tres mitades: **la semilla como artículo del almacén con los datos
de su etiqueta**, **la foto de la etiqueta como propuesta** (que no crea nada hasta que el agricultor
dice que sí) y **la asignación de una semilla a una siembra**, con la dosis por hectárea y la cantidad
total, cada una con su nombre y su unidad. Aquí se cuenta qué hay, qué no hay y por qué, las decisiones
que sostienen esto y **los recuentos de verdad** de las pruebas que se han ejecutado.

Fecha: 03/10/2026.

---

## 1. Qué se puede hacer ahora (una línea por cosa)

1. **Dar de alta una semilla con lo que pone su etiqueta** —especie, variedad, casa comercial,
   proveedor, número de lote del envase, dosis recomendada por hectárea, fecha de envasado y de
   caducidad, poder germinativo, pureza y si viene tratada— **y que sea un artículo del almacén**:
   aparece en el libro, entra por albarán y sale cuando se siembra. No hay un segundo almacén.
2. **Hacerle una foto a la etiqueta y que el programa diga lo que ha leído.** Se sube el fichero, se
   lee lo que se puede (primero el texto de verdad de un PDF; si es una foto o un escaneo, con el lector
   de letras) y **se enseña dentro del formulario, campo a campo, para que el agricultor lo corrija y lo
   confirme**. Lo que no se ha leído se queda **vacío**; lo que el papel sí dice pero no se puede
   apuntar tal cual (una caducidad de mes y año, una dosis sin decir si es por hectárea) sale en su
   propio bloque, con esas palabras. **La lectura no guarda nada**: ni la semilla, ni el artículo, ni el
   fichero.
3. **Confirmar** esa propuesta (o escribirla a mano, o coger la etiqueta de un insumo que ya entró por
   albarán sin crear un segundo artículo con el mismo nombre). Entonces sí: se crea la semilla y, si se
   hizo la foto, se guarda **con** ella.
4. **Ver las semillas con lo que queda de cada una**, contado por el servidor: el saldo con su unidad y,
   cuando no se puede saber, «No se puede saber lo que queda» con su motivo. Nunca un cero.
5. **Sembrar una semilla**: se dice en qué tierra, cuándo, cuántas hectáreas y cuánto se siembra en cada
   hectárea **y** cuánto se ha gastado en total, **cada cifra con su nombre y su unidad**. Si falta una
   de las dos y hay hectáreas, el servidor la calcula **y lo dice**; si no se puede calcular, se queda
   vacía y se pide. La semilla **sale del almacén** por la puerta de las salidas que ya existía.
6. **Corregir y anular una siembra sin que queden dos descuentos**: corregir lo que salió del almacén
   anula la salida vieja (que se queda en el libro, tachada) y apunta la nueva; anular la siembra
   **devuelve la semilla al almacén sin tocar el libro**, porque la salida deja de contar sola.
7. **Corregir la etiqueta** de una semilla guardada (un poder germinativo mal copiado se arregla, y
   queda el rastro de lo que decía antes en la auditoría), y **guardar o ver la foto** del papel.

---

## 2. Ficheros creados y tocados

### Nuevos

| Fichero | Qué es |
|---|---|
| `backend/app/semillas.py` | La lógica pura del T10: leer una etiqueta y sacar sus campos, y cuadrar la dosis con la cantidad total. **No escribe nada**, ni puede. |
| `backend/app/routers/semillas_api.py` | Las once puertas HTTP de las semillas y las siembras (dos prefijos: `/api/semillas` y `/api/siembras`). |
| `backend/tests/test_semillas.py` | Las pruebas de Python del ticket. |
| `backend/tests_js/semillas.test.js` | Las pruebas de JavaScript de las cuatro pantallas, con la copia de los textos del servidor. |
| `backend/web/react/pantallas/semillas.js` | La lista de semillas y la ficha de una semilla (alta, corrección y **confirmación de lo leído**). |
| `backend/web/react/pantallas/siembras.js` | Lo que se ha sembrado y el formulario de «en esta tierra sembré esta semilla». |
| `docs/T10_SEMILLAS.md` | Este documento. |

### Tocados

| Fichero | Qué se le ha hecho |
|---|---|
| `backend/app/models.py` | **Solo añadiendo**: dos tablas nuevas (`semillas` y `siembras`). |
| `backend/app/schemas.py` | **Solo añadiendo**: `SemillaEntrada`, `SemillaSalida`, `EtiquetaLeidaSalida`, `SiembraEntrada` y `SiembraSalida`. |
| `backend/app/textos.py` | **Solo añadiendo**: el bloque `SEMILLAS`, `MENSAJES_DE_LAS_SEMILLAS` (33 mensajes `SM*`, con `MENSAJES.update` al final, como el bloque del almacén) y dos líneas en `textos_visibles()`. **Ni un texto de los que ya estaban se ha cambiado.** |
| `backend/app/servicios.py` | **Tres líneas, y son la mitad del ticket**: `siembra` entra en `APUNTES_QUE_GASTAN`, `lo_que_gasta_un_apunte` sabe contestar de una siembra y `estado_de_los_origenes` sabe que una siembra anulada deja de contar. |
| `backend/app/facturas.py` | El lector de papeles se saca a `texto_del_documento()`, que es lo que usan la factura y la etiqueta: **un solo camino de lectura**, no dos. |
| `backend/app/routers/almacen_api.py` | **No se ha tocado.** La semilla sale por su puerta (`sacar_de_un_lote`), importada tal cual desde el router de las semillas. |
| `backend/app/routers/interfaz.py` | **Tres líneas**: se sirve el bloque `semillas` y las dos listas de unidades (dosis y cantidad). |
| `backend/app/main.py` | **Dos líneas**: los dos routers del ticket. |
| `backend/web/app.js` | El estado, las cuatro pantallas, las trece acciones del manejador de clics, el menú, las tablas de direcciones y la versión (a `2026-10-03-65`). |
| `backend/web/react/rutas.js` | Las dos direcciones: `#/semillas` y `#/semillas/siembras`. |
| `backend/web/service-worker.js` | Los dos ficheros nuevos en `FICHEROS` y la caché a `cuedigital-2026-10-03-65`. |
| `docs/REACT.md` | Las dos filas de la tabla de pantallas y el párrafo de la cuenta (treinta y nueve). |
| `backend/tests/test_las_tierras_se_pueden_corregir.py` | **Una prueba existente, actualizada explicando el motivo**: la lista de tablas que apuntan a una tierra ahora tiene nueve (`siembras` entra, porque una siembra se hace en una tierra). Ver el apartado 4. |
| `README.md`, `AGENTS.md`, `docs/LO_QUE_PIDE_LA_JUNTA.md` | Los recuentos de pruebas, que es lo que exige el guardián `test_lista_de_la_junta.py`. |

### Lo que NO se ha tocado

`backend/cuedigital.db` (ni se ha abierto), `docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`, `backend/scripts/**`,
`backend/app/database.py`, `docs/T05_*.md`, `docs/T06_*.md`, `docs/T09_*.md`, `docs/REVISION_*.md`, las
pruebas de JavaScript que ya existían y ninguna prueba de Python salvo la del apartado 4 (que fallaba por
mi culpa y se ha actualizado con su motivo escrito).

> **Aviso de coordinación, y es importante.** Mientras se hacía este ticket, **otro proceso de este
> mismo repositorio estaba escribiendo `backend/web/app.js`** (el T06 que se estaba cerrando): lo detecté
> porque las herramientas de edición rechazaban mis cambios con «el fichero ha cambiado desde que lo
> leíste», y lo confirmé midiendo la huella del fichero dos veces seguidas. Se esperó a que parara, se
> hicieron los cambios de `app.js` de una vez y **`node --check` y la suite entera se ejecutaron después**.
> Si algo de `app.js` del T06 falta, es por esto, y conviene mirarlo.

---

## 3. Las decisiones que hay que entender antes de tocar esto

### 3.1. Una semilla es un artículo del almacén, y lo único que añade es el papel

`semillas` cuelga de `articulos` (una etiqueta por artículo, con una restricción única) y **no hay un
segundo almacén**: lo que se compra, lo que entra y lo que sale de una semilla son las mismas filas que
las de cualquier otro insumo. Si la semilla ya entró por albarán, la etiqueta **se cuelga de su
artículo** (`articulo_id`); si no existe todavía, se crea el artículo con la categoría `semilla`. Intentar
colgar una segunda etiqueta del mismo artículo se rechaza (409) con el motivo escrito: dos fichas de la
misma semilla partirían las existencias en dos.

### 3.2. La cantidad total no es la dosis por hectárea (y los litros no son los kilos)

Es el corazón del ticket y está en cuatro sitios a la vez:

1. **Columnas distintas** (`dosis_por_ha` con `unidad_dosis`, `cantidad_total` con `unidad_cantidad`).
2. **Campos distintos en la pantalla**, cada uno con su nombre («Cuánto se siembra en cada hectárea» y
   «Cuánto se ha gastado en total») y con su propio desplegable de unidad.
3. **Si falta una y hay hectáreas, se calcula y se dice** (`cantidad_total_calculada` / `dosis_calculada`
   + un aviso con la cuenta entera: «120,00 kg/ha por 2,00 hectáreas son 240,00 kg»). Un número calculado
   se puede revisar; uno inventado, no.
4. **Si no se puede calcular, se queda vacía y se pide.** Y si las dos vienen y no cuadran, **se dicen los
   dos números** y no se bloquea nada (puede haber sembrado a mano una parte). Si las unidades no se
   pueden comparar (litros con kilos), no se convierte nada: se dice que no se pueden comparar, porque la
   densidad no la sabemos.

### 3.3. Un dato que no se sabe no es un cero

El poder germinativo y la pureza **no vienen en todas las etiquetas**. Cuando no vienen, se quedan en
`None`, la pantalla escribe «La etiqueta no lo dice» y una prueba lo fija. «¿Viene tratada?» tiene **tres**
respuestas (`True`, `False` y `None` = «no lo sé»), y la lectura de la etiqueta busca primero la negación
(«SEMILLA NO TRATADA» contiene la palabra «tratada»: leerla al revés sería un dato grave, y tiene su
prueba). La dosis y la cantidad total se guardan y se enseñan igual: `None` es «no lo sé», y **una siembra
de la que no se sabe cuánto se sembró no descuenta nada del almacén**, con su motivo escrito.

### 3.4. La semilla sale del almacén por la puerta que ya existía

`POST /api/almacen/salidas` es la **única** forma de sacar producto con un apunte detrás, y una siembra lo
es. El router de las semillas la llama **importando la función, no copiándola**: así la siembra hereda el
reenvío, el aviso de que el envase se queda en negativo (con su «sí, la diferencia es de verdad»), la
comprobación de la unidad del lote y la auditoría, y no hay dos formas de restar que un día digan cosas
distintas. Y de ahí sale lo mejor: **anular una siembra devuelve lo que salió sin tocar el libro**, porque
`servicios.estado_de_los_origenes` mira si la siembra está anulada (igual que un tratamiento anulado).

`origen_tipo="siembra"` **no** se ha añadido a `ORIGENES_DE_UN_MOVIMIENTO` a propósito: esa lista es lo
que acepta la puerta de los movimientos a mano, y una persona no puede decir «es que viene de una
siembra». Si se añadiera, se podría apuntar una salida a mano diciendo eso, que es justo la segunda forma
de restar que el ticket prohíbe.

### 3.5. Corregir no puede dejar dos descuentos (ni quedarse sin ninguno)

Corregir una siembra hace dos cosas, en la misma transacción:

- Lo que cambia de la siembra (tierra, fecha, hectáreas, las dos cifras, notas) se corrige **en la misma
  fila**, con lo que decía antes en la auditoría (`correcciones.corregir`).
- Y si cambia **lo que salió del almacén** (cantidad, unidad, envase o fecha), la salida vieja se **anula**
  con su motivo —se queda en el libro, tachada, y deja de contar— y se apunta una nueva por la puerta de
  las salidas. Nunca dos vivas, y nunca reescribir la cantidad de un movimiento por detrás.

Dos cosas que se han aprendido escribiendo esto y están fijadas por pruebas:

1. **La clave de reenvío no se puede perder al corregir.** `correcciones.corregir` copia todas las columnas
   del registro preparado, y si `clave_de_reenvio` no se copiara, un reenvío de la petición original (la
   cola del móvil) **no reconocería la siembra y apuntaría otra, con su descuento**.
2. **Una corrección parcial no puede dejar la siembra sin descuento.** Si la petición no manda `lote_id`
   (cosa que pasa en cuanto una pantalla no pregunte el envase), el envase que ya constaba **se mantiene**;
   para quitar el descuento está ANULAR, que además deja el motivo escrito.

### 3.6. Leer una foto es una propuesta: la puerta de la lectura no escribe

`POST /api/semillas/etiqueta` lee y contesta, y **no escribe nada** —ni el artículo, ni la semilla, ni el
fichero en disco—. Hay dos pruebas que lo miran **por el otro lado**: después de leer una etiqueta, la
lista de semillas está vacía, el almacén está vacío y no hay ni un fichero nuevo en la carpeta de
adjuntos. Y la respuesta lo dice en el dato (`guardado: false`), no en un comentario.

**Con qué se lee, dicho sin adornos:** primero **el texto que trae dentro el papel** (un PDF del
proveedor se lee sin equivocarse, y hay una prueba con un PDF de verdad); solo si no hay texto (un escaneo
o una foto del móvil) se llama al **lector de letras** (Tesseract), y **si no está instalado se dice** y la
ficha se rellena a mano. El camino de la lectura es el mismo que el de las facturas
(`facturas.texto_del_documento`), no otro.

### 3.7. La pantalla no calcula nada

Lo que queda en el almacén, lo que ha salido y lo que el programa ha calculado **llegan contados del
servidor**, con su unidad. La pantalla solo prepara las filas (en `app.js`, que es quien tiene los datos) y
las pinta. Un número que la pantalla sacara por su cuenta podría no ser el que se guardó, y es exactamente
el fallo que el T09 ya dejó escrito.

### 3.8. Los textos de las semillas viven dentro del bloque `semillas`, que sí se sirve

`/api/interfaz` sirve los bloques **por su nombre**, y los textos que llegan solo dentro de una respuesta
de la API **no se guardan en el móvil**: sin cobertura, esa pantalla saldría en blanco justo cuando más
falta hace. Por eso los textos nuevos van en un bloque propio (`SEMILLAS`) **servido** por
`/api/interfaz`, y no dentro de las respuestas. **Son 158: 125 claves del bloque y 33 mensajes `SM*`**
(la cuenta la midió la revisión; este documento decía «200 y pico», y no era la cifra que hay). El T09 no
pudo hacer esto porque su ticket no le dejaba tocar los routers; aquí sí, y son tres líneas.

---

## 4. La prueba que ya existía y se ha actualizado (con su motivo)

`tests/test_las_tierras_se_pueden_corregir.py::TestLoQueSeCuentaAntesDeBorrar::test_las_tablas_que_apuntan_a_una_tierra_se_cuentan_todas`
enumera **por su nombre** las tablas que apuntan a una tierra, y decía ocho. Con `siembras` son **nueve**.
No se ha tocado el código que cuenta (sale de las tablas de verdad), solo la lista esperada, y se ha
escrito **por qué**:

> Una siembra **es un apunte que se hace en una tierra**, así que cuenta como dependencia: una tierra con
> siembras apuntadas no se puede borrar (se corrige, que es lo que de verdad quiere quien se ha
> equivocado al escribirla), y el mensaje que sale es el mismo que para cualquier otro apunte
> (`B2_tierra_con_apuntes`).

Es justo lo que el propio docstring de esa prueba pide que se haga el día que aparezca la novena
(«esta prueba falla y obliga a decidir: o cuenta como dependencia, o hay que escribir por qué no»).

---

## 5. Las pruebas

### Python

```bash
cd backend
../.venv/Scripts/python.exe -m pytest -q -p no:randomly --junit-xml=$env:TEMP\completa.xml
```

**Recuento real: 3536 pruebas de Python en la suite entera** (45 nuevas son de este ticket) y **0 fallos,
0 errores y 1 saltada** (la que se salta sola si en el ordenador no está puesto el programa que lee fotos;
**en esta máquina sí lo está y se ejecutó**). El recuento de la documentación se ha puesto al día
(`README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md`), que es lo que vigila
`tests/test_lista_de_la_junta.py`.

> El número de la suite es el de la ejecución que se cita en el informe final, no una constante: mientras
> se hacía este ticket **otro proceso del mismo repositorio estaba añadiendo pruebas del T06** a la vez
> (ver el aviso del apartado 2), así que el total se mueve con lo que entre por el otro lado.

Las 45 pruebas propias, por lo que defienden:

- **Leer la etiqueta**: los campos de una etiqueta de verdad (texto y PDF), una dosis sin decir por
  hectárea (que **no** se apunta como dosis), una caducidad de mes y año (que **no** se completa con un
  día inventado), lo que no viene y se queda vacío, «NO TRATADA» que no se lee al revés, un porcentaje sin
  el signo `%`, una etiqueta que no habla de la caducidad, y **una foto de verdad leída con el lector de
  letras** (esa se salta sola si el lector no está instalado, como las de las facturas).
- **La lectura no crea nada**: sin confirmar no hay semilla, ni artículo, ni fichero en el disco.
- **Lo que no se sabe no es un cero**: sin poder germinativo, sin pureza, sin saber si viene tratada, un
  envase del que no se sabe la cantidad (saldo `None` con su motivo) y una siembra sin cantidad (que dice
  que no descuenta).
- **La dosis no es el total**: se calcula la que falta y se dice; sin hectáreas no se calcula y se pide;
  2 L en 4 ha son 0,5 L/ha; litros con kilos no se comparan; cuando no cuadran se dicen los dos números;
  una cantidad negativa no se apunta.
- **Sembrar descuenta una sola vez**: el descuento, el reenvío de la misma petición (200 y sin descontar
  otra vez), dos siembras distintas que descuentan las dos, un envase de otra semilla que se rechaza, y el
  envase que se queda en negativo (409 y, con la confirmación del agricultor, se apunta y queda marcado).
- **Corregir y anular sin duplicar**: corregir la cantidad deja un solo descuento vivo (440 = 500 − 60) con
  la salida vieja tachada; anular devuelve la semilla al almacén sin tocar el libro; una siembra anulada no
  se corrige; anular sin motivo no vale; una siembra que no descontaba y ahora sí; y la marca de reenvío
  que sobrevive a la corrección.
- **La semilla es un artículo del almacén**: el alta, que no se crea dos veces el mismo artículo, la dosis
  sin unidad que se rechaza, la foto que se sube y se sirve, el nombre del fichero que **no** decide la
  ruta (con `../../app/main.py`, mirando el disco) y la corrección de la etiqueta con su rastro.
- **De otra finca no se ve nada**: `404` (y no `403`) en la semilla, la siembra, su foto y su anulación, y
  `401` sin vale de sesión.
- **La copia de los textos de JavaScript** no se queda vieja (clave por clave, y con los dos mensajes).

### JavaScript

```bash
cd backend
node --test "tests_js/*.test.js"
```

**805 pruebas, 805 en verde** (24 nuevas del T10). Las 24 comprueban, contra el componente y sin
navegador: la lista de semillas y su estado vacío, una semilla de la que no se sabe lo que queda (que
**no** se pinta como un cero), los catorce `id` de la ficha, el teclado de números del móvil, un poder
germinativo vacío que sale vacío, las tres respuestas de «¿viene tratada?», la propuesta leída y su aviso
de que no se ha guardado nada, lo que el papel dice y no se puede apuntar, el filete de la foto, la lista
de siembras, **las dos cifras en dos campos distintos con su unidad**, el «Lo ha calculado el programa»,
el envase que se elige de los suyos, lo que queda dicho por el servidor, el botón de anular solo al
corregir, y que **ninguna frase esté escrita a mano** en las cuatro pantallas.

### Comprobado en un navegador de verdad

**1. El guion del coordinador, tal cual.** `scripts/comprobar_en_un_navegador.py` **es suyo y no se ha
tocado**. Se ha lanzado contra un servidor de verdad (con su base en una carpeta temporal) y **las 24 rutas
que recorre dan todas `[OK]`**: la interfaz se abre, se dibuja y no se ha roto nada de lo que ya había.

**2. Y las dos pantallas nuevas, con la misma técnica** (Chrome sin ventana y `--dump-dom`), desde un
guion **que vive en la carpeta temporal y no en el repositorio** (el del coordinador es suyo y no se
edita). Ese guion crea una cuenta, siembra una tierra, un albarán con una semilla, su etiqueta y una
siembra, abre `#/semillas` y `#/semillas/siembras` **por su dirección** a tres anchos y comprueba, en cada
uno, que sale el título del servidor, que la pantalla tiene contenido, que **no se sale de lo ancho** y que
**no aparece el aviso de emergencia de React**. Resultado: **6 de 6 en verde** (390, 1024 y 1440 px), con
capturas guardadas en la carpeta temporal, y el fichero que ese guion escribe dentro de `backend/web/`
**borrado al terminar** (y comprobado que no está).

De las capturas salen tres cosas que confirman lo que defiende este ticket: la tarjeta de la semilla dice
«Te queda 300,00 kg» (500 kg del albarán menos los 200 kg de la siembra, o sea que **el descuento pasó por
el almacén**), la pureza sale como «La etiqueta no lo dice» **y no como un cero**, y la tarjeta de la
siembra enseña **las dos cifras en dos renglones distintos, cada una con su nombre y su unidad**
(«Cuánto se siembra en cada hectárea: 200,00 kg/ha» y «Cuánto se ha gastado en total: 200,00 kg»).

> **Lo que ese guion no mide bien, y se dice:** a 390 px Chrome no baja de 500 px de ventana, así que la
> medición estrecha de verdad es la que hace el guion del coordinador **con un hueco dentro de la página**
> (`pagina_estrecha`), y **esas dos pantallas no están en su lista**: lo que se ha comprobado es que **no se
> salen de lo ancho** en ninguna de las tres medidas y que usan las mismas piezas y clases que las demás
> (`tarjeta`, `campo`, `barra-acciones`), así que heredan el comportamiento de 390 px del armazón del T04.
> **Añadirlas a la lista `PANTALLAS` del guion son cuatro líneas, y eso lo tiene que hacer el coordinador.**

---

## 6. Lo que NO se ha hecho, y por qué

1. **La tabla del ordenador para las dos listas.** Las semillas y las siembras van en tarjetas, como las
   demás listas que aún no tienen tabla (lo dice `docs/REACT.md`: «las tablas de las listas que quedan»).
   La tarjeta es la pieza que ya existe para el móvil, y estas dos listas se miran de pie en la nave.
2. **Borrar una semilla.** La semilla no se borra: es un artículo del almacén y tiene movimientos detrás.
   Lo que no está hecho es darla de baja (una semilla que ya no se usa). No estaba en el ticket.
3. **Elegir la semilla dentro del formulario de la siembra.** Se entra desde la ficha de la semilla
   («SEMBRAR ESTA SEMILLA»), así que la semilla y sus envases ya vienen elegidos. Cambiar la semilla de
   una siembra guardada **no se puede** y se dice por qué (409): la salida del almacén pertenece a un
   artículo, así que para cambiar de semilla hay que anular y apuntar la nueva.
4. **Las siembras no entran en el texto que se firma.** Lo midió la revisión y es un límite que conviene
   saber: `firma.texto_del_cuaderno` escribe tratamientos, abonos y labores, así que una siembra **no va
   dentro del fichero firmado** (la huella no cambia al apuntarla, y el contrato del ticket se cumple tal
   como está escrito). Meterla ahí cambiaría la firma de los cuadernos, y eso es una decisión del
   coordinador, no de este ticket.
5. **`leida_de` es una declaración de quien llama, no una comprobación del servidor.** `POST /api/semillas`
   acepta `leida_de: "foto"` aunque no haya ninguna foto (lo señaló la revisión, sin contarlo como
   defecto): la regla del ticket —que **leer no cree nada**— se cumple, pero el dato que dice «esto lo leyó
   un programa del papel» lo escribe quien llama.
6. **Un catálogo oficial de especies y variedades.** No está cargado y no se ha inventado: la especie y la
   variedad son texto libre, tal como vienen en el papel. Las listas de unidades (dosis y cantidad) **son
   nuestras** y se dice en el código: no hay catálogo oficial de unidades de siembra cargado.
7. **La lectura de la etiqueta con un lector de letras en el servidor de verdad.** Depende de que
   Tesseract esté instalado en la máquina donde corre el programa. Si no está, el programa **lo dice** y
   la ficha se rellena a mano; eso está probado (con el lector apagado a propósito).
8. **Las cuatro pantallas nuevas en el guion del navegador.** Ver el apartado 5: el guion es del
   coordinador y no se puede editar desde este ticket.

---

## 7. La revisión del ticket: los diez defectos que salieron, y cómo quedaron

El coordinador revisó el T10 con su propia batería de pruebas (`backend/tests/test_revision_t10.py`, 49
pruebas). Salieron **nueve defectos** —los ocho del informe más el de la unidad en minúscula— y, al
escribir la prueba que faltaba, **un décimo que encontré yo**. Los diez están arreglados, y todos tienen
su prueba también en `backend/tests/test_semillas.py` (para que la suite del ticket los defienda sola).
Se cuentan aquí porque son la parte del trabajo que de verdad cambió el programa:

| # | Defecto | Qué pasaba de verdad | Cómo quedó |
|---|---|---|---|
| 1 | **Anular una siembra y reenviar la misma petición no volvía a descontar** | La salida se apuntaba con la clave de reenvío `«…:salida»`, así que al reenviar (la cola del móvil reenvía la misma) la puerta del almacén encontraba **la salida vieja** —viva, solo que su siembra estaba anulada— y la daba por buena: el almacén no se movía y la respuesta decía que no descontaba «porque no se sabe de qué envase sale», con el envase escrito en la misma respuesta | La salida de una siembra **no lleva clave propia**: la protección de verdad es la comprobación de la puerta por **apunte y envase**, y el reenvío lo corta antes el propio `POST /api/siembras` (que reconoce la siembra por su clave y devuelve la que ya había sin volver a llamar) |
| 2 | **Una segunda salida a mano descontaba dos veces** | `POST /api/almacen/salidas` con `apunte_tipo="siembra"` y otro envase del mismo artículo creaba una segunda salida viva: la comprobación «ya estaba» era por apunte **y envase** | Para una siembra la comprobación es **por apunte** (una siembra guarda **un** lote: no puede salir de dos envases). Para un tratamiento o un abono sigue siendo por apunte y envase, que ahí sí es legítimo gastar dos garrafas |
| 3 | **«SEMILLA SIN TRATAMIENTO» se leía como tratada** | La negación que se buscaba era `sin tratar`, que no encaja en `sin tratamiento` (hay letras de más): la frase más normal de un saco marcaba la semilla **al revés** | Las negaciones son ahora una lista a la vista (`NEGACIONES_DE_TRATAMIENTO`), y se buscan antes que las afirmaciones: `sin tratamiento`, `no lleva tratamiento`, `no se ha aplicado ningún tratamiento`… |
| 4 | **La unidad se guardaba como `kgporhectarea`** | «120 kg **por hectárea**» —que es como lo escribe media España— se guardaba pegado, y eso no es una unidad: el desplegable de la dosis se quedaba sin su opción y la siembra podía acabar sin unidad (y sin descontar) | La unidad se guarda **siempre en su forma corta** (`kg/ha`), traduciendo solo lo que es la misma cosa dicha de otra manera: `kilos`→`kg`, `por hectárea`→`/ha`, `hectárea`→`ha` |
| 5 | **Una semilla sin ninguna entrada decía «queda 0»** | El camino normal del ticket (comprar, hacer la foto, confirmar) enseñaba «Te queda 0» con el saco en la nave: sin ningún movimiento el almacén contestaba cero | Un artículo **sin ningún envase y sin ningún movimiento** no dice cero: dice «no se puede saber lo que queda» con su motivo. Un envase que existe y está vacío **sí** es cero, y eso se respeta (es la regla del almacén) |
| 6 | **Una corrección parcial borraba la fecha** | El `PUT` escribía lo que mandaba la petición y lo que no mandaba, a nulo: corregir la cantidad desde fuera dejaba la siembra **sin el día en que se sembró** | Se distingue «no lo manda» de «lo manda vacío» (`model_fields_set`): lo que no viene **se queda como estaba**, y `null` explícito borra. Vale para la fecha, las hectáreas, el envase, las notas y todo lo demás |
| 7 | **Cambiar la semilla de una siembra se hacía en silencio** | El documento decía que no se puede y el código sí: la semilla volvía al almacén sola y la siembra pasaba a decir que se sembró otra cosa, sin un aviso | Se rechaza con `409` y su mensaje: **se anula esta siembra y se apunta la nueva** |
| 8 | **La cuenta que hace el servidor no llegaba a la pantalla** | El aviso con la cuenta (`… son 300,00 kg`) solo existe en la respuesta de guardar; `app.js` lo guardaba y **lo ponía a nulo tres líneas después**, antes de pintar. El agricultor leía un total que no había escrito él como si lo hubiera escrito él | La cuenta y los avisos del servidor **se enseñan en la lista de lo sembrado**, que es lo que queda delante después de guardar (es lo mismo que hace la salida del almacén del T09) |
| 9 | **«2 L/ha» se leía `l/ha`, y la pantalla ofrece `L/ha`** | El arreglo del defecto 4 traducía cada trozo de la unidad a su forma corta, pero la tabla no tenía las formas cortas (`l`, `kg`, `g`, `ml`), así que lo que escribe media España se quedaba en minúsculas: el desplegable de la dosis se quedaba sin esa opción y **la siembra podía acabar sin unidad (y sin descontar)** | La tabla tiene también las formas cortas (`l`→`L`, `ml`→`mL`…) y **la pantalla ofrece siempre la unidad que ya consta**, aunque no esté en la lista del servidor |
| 10 | **No había ninguna puerta para llegar a sembrar** | *Este lo encontré yo al escribir la prueba que faltaba, no la revisión.* Ninguna pantalla pintaba el botón `siembra-nueva`: el manejador de clics lo atendía, el texto (`SEMBRAR ESTA SEMILLA`) estaba escrito y la pantalla del formulario existía, pero **no había forma de abrirla** desde la interfaz. La familia de fallo que este proyecto persigue: un dato que existe y una puerta que falta | El botón sale en la ficha de la semilla, **solo cuando la semilla ya está guardada** (no se puede sembrar lo que todavía no existe) |

> **Y un defecto de método, que es el que enseñó a los demás:** **el camino de guardar de la pantalla no
> lo probaba nadie.** Las pruebas de JavaScript pintaban las cuatro pantallas y miraban sus campos, sus
> textos y sus opciones, pero **ninguna pulsaba `semilla-guardar`, `siembra-guardar` ni `siembra-anular`**
> (lo midió la revisión buscando esas acciones en los seis ficheros de `tests_js/`). Y ahí estaba,
> exactamente, el defecto 8: una pantalla que enseña lo que le llega puede estar perfecta y no llegarle
> nunca nada. Ahora hay **seis pruebas en `tests_js/interfaz.test.js`** que pulsan esos botones con el DOM
> y el servidor de mentira, comprueban **lo que llega al servidor** (la dosis y el total en campos
> distintos y con su unidad, lo que no se sabe en blanco y no en cero, el motivo de una anulación, la
> marca de reenvío) y que **no se manda nada** cuando falta un dato o no se ha elegido la foto. De
> escribirlas salió el defecto 10.

> **Lo que de esto se aprende, y va más allá de este ticket**: los ocho son la misma familia de fallo que
> el proyecto ya tiene escrita en `AGENTS.md` —**un dato que existe y que no llega a quien tiene que
> leerlo**, o una comprobación que está en un sitio y no en el otro—. El 1 y el 2 son «dos formas de
> descontar lo mismo»; el 6 y el 8, «lo que no se pregunta se pierde»; el 3 y el 4, «lo que se lee del
> papel hay que leerlo en la forma en que lo escribe la gente»; el 5 y el 7, «un dato que no se sabe no
> se convierte en una afirmación».

---

## 8. Lo que no se ha podido comprobar

1. **Una foto de una etiqueta de verdad, de un saco de verdad.** La lectura se ha probado con un papel
   de etiqueta **dibujado y rasterizado** (que es lo que sale del móvil, y pasa por el mismo lector) y
   con PDFs con el texto dentro. Lo que **no** se ha probado es una foto hecha con el móvil, torcida,
   con sombras y con el plástico del saco brillando. Es la prueba que hay que hacer antes de fiarse.
2. **Los recuentos de pruebas en un repositorio que se mueve.** Mientras se hacía este ticket **otro
   proceso estaba escribiendo `app.js` y añadiendo pruebas del T06** al mismo tiempo, así que los números
   exactos de la suite son los de la ejecución que se cita en el informe final, no una constante.
3. **La cola del móvil mandando una siembra sin cobertura de verdad.** Está probado que el reenvío con la
   misma clave no descuenta dos veces y que sin cobertura el apunte se queda en el móvil, pero **no se ha
   cortado la red de un móvil real**.
4. **El aspecto en un móvil de verdad, con el sol de frente, y con manos de agricultor.** Eso exige la
   prueba con tres agricultores (apartado 5.18 del documento del MVP) y no se puede hacer desde aquí. Lo
   que sí se ha comprobado es que la pantalla usa las piezas y las clases de siempre (la tarjeta, el
   campo, el botón, la barra de acciones), así que hereda el comportamiento a 390, 1024 y 1440 px del
   armazón del T04.
5. **La lectura de una etiqueta en otro idioma del lector.** El proyecto ya tiene pagada esa trampa con
   las facturas (con el español instalado, «Nº» se lee «N*»), y aquí se ha cuidado en las expresiones
   (`n.º`, `nº`, `n.o` y `no` son la misma etiqueta en su forma llana, y eso se descubrió con la prueba de
   un nombre de lote). No se ha probado con una foto real en inglés.
