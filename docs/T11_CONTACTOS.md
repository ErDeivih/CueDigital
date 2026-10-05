# T11 — Contactos reutilizables y enlaces; migración de textos sin fusiones inseguras

**Qué es esto.** El ticket T11 tenía dos mitades que se sostienen la una en la otra: **el contacto
apuntado una sola vez** (una persona o una empresa, con los papeles que hace con la finca y con
**enlaces** desde los nombres que ya están escritos en las facturas, las ventas y los análisis) y **la
migración de esos textos**, que es la mitad peligrosa: hay que proponer fichas a partir de lo que ya
está escrito **sin fusionar a dos que no se pueda asegurar que son el mismo**. Aquí se cuenta qué hay,
qué no hay y por qué, las decisiones que sostienen esto y **los recuentos de verdad** de las pruebas
que se han ejecutado.

Fecha: 03/10/2026.

---

## 1. Qué se puede hacer ahora (una línea por cosa)

1. **Apuntar una ficha de contacto** —persona o empresa, con su NIF/CIF, teléfono, correo, dirección,
   pueblo y notas— y **los papeles que hace con esta finca**: quien te vende el producto, quien te
   vende la semilla o el abono, quien te compra la cosecha, el técnico que te asesora, quien echa el
   producto, quien te lleva la mercancía, el taller, el laboratorio, el veterinario, quien te alquila
   la tierra y «otra cosa». **Los papeles se solapan**: se marcan de uno en uno y una misma cooperativa
   puede ser proveedor y comprador a la vez, que es lo normal en el campo.
2. **Enlazar un nombre que ya está escrito** con su ficha, sin teclearlo otra vez: se busca entre los
   nombres que hay escritos en las facturas, los albaranes, las ventas, los análisis, los productos del
   catálogo y las fichas de aplicadores y asesores, y se toca el que sea esa persona.
3. **Ver dónde está escrito el nombre de un contacto**, uno por uno, con el texto tal y como lo escribió
   él. **Quitar un enlace no borra el nombre**: el papel se queda exactamente como estaba.
4. **Ver la revisión de los nombres escritos**: el programa mira todo lo que hay escrito a mano, propone
   una ficha por cada nombre —agrupando los que están escritos igual y los que comparten NIF— y **dice
   aparte, sin tocarlos, los que se parecen y los que llevan el mismo nombre con dos NIF distintos**.
   El agricultor apunta las que quiera, una por una o todas las seguras.
5. **Deshacer la migración**: quita las fichas y los enlaces que apuntó el programa y **deja las que el
   agricultor haya corregido o enlazado él**, con su nombre en la respuesta.

---

## 2. Ficheros creados y tocados

### Nuevos

| Fichero | Qué es |
|---|---|
| `backend/app/contactos.py` | La lógica pura del T11: los papeles, **las siete puertas donde hay un nombre escrito**, y la comparación de nombres (qué se puede juntar y qué no). **No escribe nada**, ni puede. |
| `backend/app/routers/contactos_api.py` | Las doce puertas HTTP de los contactos, sus papeles, sus enlaces y la migración. |
| `backend/scripts/migrar_contactos.py` | El guion de la migración, con informe previo, `--migrar` y `--deshacer`. Llama a **las mismas** funciones que la pantalla. |
| `backend/tests/test_contactos.py` | Las pruebas de Python del ticket (55). |
| `backend/tests_js/contactos.test.js` | Las pruebas de JavaScript de las cuatro pantallas (32), con la copia de los textos del servidor. |
| `backend/web/react/pantallas/contactos.js` | La lista de fichas, la ficha de un contacto y la lista de nombres escritos para enlazarlos. |
| `backend/web/react/pantallas/revision_de_contactos.js` | La revisión de los nombres que ya están escritos: donde el programa **propone y no fusiona**. |
| `docs/T11_CONTACTOS.md` | Este documento. |

### Tocados

| Fichero | Qué se le ha hecho |
|---|---|
| `backend/app/models.py` | **Solo añadiendo**: tres tablas nuevas (`contactos`, `papeles_de_un_contacto`, `enlaces_de_contacto`). |
| `backend/app/schemas.py` | **Solo añadiendo**: los esquemas de entrada y salida del ticket. |
| `backend/app/textos.py` | **Solo añadiendo**: el bloque `CONTACTOS`, `MENSAJES_DE_LOS_CONTACTOS` y dos líneas en `textos_visibles()`. **Ni un texto de los que ya estaban se ha cambiado.** |
| `backend/app/routers/interfaz.py` | **Dos entradas**: el bloque `contactos` y la lista `papeles_de_un_contacto` (con su orden y su nombre). |
| `backend/app/main.py` | **Dos líneas**: el router del ticket. |
| `backend/web/app.js` | El estado, las cuatro pantallas, las diecinueve acciones del manejador de clics, el renglón del menú, las tablas de direcciones y la versión (a `2026-10-03-66`). |
| `backend/web/react/rutas.js` | Las dos direcciones: `#/contactos` y `#/contactos/revisar`. |
| `backend/web/service-worker.js` | Los dos ficheros nuevos en `FICHEROS` y la caché a `cuedigital-2026-10-03-66`. |
| `docs/REACT.md` | Las dos filas de la tabla de pantallas y el párrafo de la cuenta (cuarenta y uno). |
| `backend/tests/test_los_botones_hacen_algo.py` | **Una lista escrita a mano, ampliada con su motivo**: `contactos.js` pinta una acción por variable (la tarjeta de un nombre escrito solo lleva botón cuando hay una ficha con la que enlazar). Es justo lo que el docstring de esa prueba pide que se haga. |
| `backend/tests_js/rutas.test.js` | **La tabla de direcciones**, con las dos nuevas y su motivo. |
| `backend/tests_js/interfaz.test.js` | **La lista de módulos del menú** y la copia mínima de los textos de contactos (el nombre del renglón y los papeles). |
| `README.md`, `AGENTS.md`, `docs/LO_QUE_PIDE_LA_JUNTA.md` | Los recuentos de pruebas, que es lo que exige el guardián `test_lista_de_la_junta.py`. |

### Lo que NO se ha tocado

`backend/cuedigital.db` (**ni se ha abierto**: se ha trabajado sobre una copia, ver §5),
`docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`, `backend/scripts/humo.py` y
`backend/scripts/comprobar_en_un_navegador.py` (son del coordinador), `docs/T05_*.md`, `docs/T06_*.md`,
`docs/T09_*.md`, `docs/T10_*.md`, `docs/REVISION_*.md`, `backend/app/database.py` y **ninguna prueba de
Python o de JavaScript salvo las cuatro que se dicen arriba**, todas con su motivo escrito.

> **Aviso de coordinación, y es importante.** Mientras se hacía este ticket, **otro proceso de este
> mismo repositorio estaba escribiendo `backend/web/app.js` y `backend/tests_js/interfaz.test.js`** (la
> revisión del T10). Se detectó con «el fichero ha cambiado desde que lo leíste» y se confirmó midiendo
> las fechas y las huellas dos veces: `app.js` cambió a las 20:13 y `interfaz.test.js` a las 20:14,
> **después de mis últimas ediciones**. Se esperó a que parara y se retomó, como hizo el T10. Dos
> consecuencias que conviene saber:
>
> 1. **Dos pruebas de `interfaz.test.js` estuvieron en rojo un rato** («al guardar la siembra…» y
>    «anular una siembra…»): eran **suyas y a medio escribir** (les faltaba la respuesta del servidor de
>    mentira para `/api/siembras/7/anular`, y la lista de siembras devolvía `[]`). Cuando terminaron,
>    quedaron en verde **sin tocar yo nada**. Están en verde en el recuento de §5.
> 2. **Los números de pruebas de este documento son los de la última pasada**, medida con los ficheros
>    como están ahora. Si el otro proceso añade pruebas después, el número se mueve solo — y hay un
>    guardián que avisa.

---

## 3. Las decisiones que hay que entender antes de tocar esto

### 3.1. La regla que gobierna el ticket: **no se fusiona nada que no se pueda asegurar**

El ticket lo dice con estas palabras: *«Dos personas distintas con el mismo nombre, un proveedor y su
hermano, «Cooperativa X» y «Cooperativa X S.L.», un nombre con una tilde y otro sin ella: si no se puede
asegurar que son el mismo, no se fusionan»*. De ahí salen cuatro decisiones, y las cuatro están en el
código y en las pruebas:

| Los dos textos… | Qué hace el programa | Por qué |
|---|---|---|
| Están escritos **igual** (cambiando solo mayúsculas) | **Se juntan** en una ficha | «COOPERATIVA X» y «Cooperativa X» no son dos empresas: es la misma escrita de dos maneras |
| Llevan **el mismo NIF** y sus nombres **son el mismo escrito de dos maneras** (escritos igual, o que se parecen) | **Se juntan**, y la ficha se queda con el NIF | El NIF es **una prueba** —la única excepción que admite el ticket—, pero **no basta él solo**: la revisión independiente demostró que un NIF tecleado mal fundía a dos personas distintas (§8.4) |
| Llevan **el mismo NIF** y sus nombres **no se parecen en nada** | **NO se juntan**: se enseñan con los dos nombres y el NIF delante | Eso no es una prueba de nada: es que uno de los dos papeles está mal escrito. Y quien lo sabe es el agricultor |
| Son el mismo nombre y llevan **dos NIF distintos** | **NO se juntan**: se enseñan con los dos números | Son dos personas distintas con el mismo nombre, que es justo el caso que el contrato pide en E5 |
| **Se parecen** (una tilde de menos, un «S.L.» de más, una letra cambiada) | **NO se juntan**: se enseñan juntos, con los dos nombres delante | Coincidir no es una prueba, es una sospecha. Juntar a un proveedor con su hermano no se puede deshacer |

**Las tres formas de «no se juntan» se cuentan por separado** y salen en el resumen de la propuesta
(`se_parecen`, `homonimos` y `nif_con_nombres_distintos`), con su número: mientras sean números
visibles, un caso no se puede volver a colar en silencio.

**Y el «no» está en dos sitios, no solo en la pantalla.** Las propuestas inseguras se enseñan **sin
botón de apuntar** (una prueba de JavaScript lo comprueba) y **el servidor contesta 409 y no crea nada
aunque se lo pidan** (una prueba de Python manda la clave de una propuesta insegura como si fuera
segura). Un «no se fusiona» que solo viviera en la pantalla se podría saltar desde fuera.

### 3.2. El número del «se parecen» no se ha elegido a ojo: está medido

`contactos.UMBRAL_DE_PARECIDO = 0.93`, y el margen es estrecho por lo que hay a cada lado
(medido, no supuesto):

* **avisa**: «laboratorio agrario» / «laboratorio agragio» → 0,9474 (una errata);
* **no avisa**: «cooperativa x» / «cooperativa z» → 0,9231, «juan» / «juana» → 0,8889,
  «transportes lopez» / «transportes perez» → 0,8824.

Los otros dos casos del ticket (una tilde de menos, la razón social de más) **no dependen del número**:
los caza la regla de «igual quitando tildes» y la de «uno es el principio del otro por palabras».

### 3.3. El enlace va en su propia tabla, y por eso la migración se puede deshacer

La forma corta de hacer esto era poner un `contacto_id` en cada una de las siete tablas. **No se hizo**,
y el motivo es el ticket: entonces **quitar un enlace escribiría en un documento histórico** y deshacer
la migración exigiría acordarse de qué filas se tocaron. Aquí el enlace es una fila de
`enlaces_de_contacto` con `tabla`, `campo` y `registro_id` —el mismo patrón que `Firma`, que ya usa
`entidad` + `entidad_id`—, así que:

* los documentos **no se han tocado ni una vez**: en todo el T11 no hay un solo `UPDATE` sobre una
  tabla de documentos (hay una prueba que lo comprueba leyendo el guion);
* deshacer es **borrar lo que la migración creó**, exacto;
* y sale gratis una cosa que hacía falta: `nombre_de_entonces` guarda lo que decía el papel el día del
  enlace, así que el programa puede decir **«ojo, ahí pone otra cosa desde entonces»** sin haber tocado
  el texto nunca.

### 3.4. Un texto escrito no puede tener dos dueños

`enlaces_de_contacto` tiene una restricción única por `(explotacion_id, tabla, campo, registro_id)` y la
puerta de enlazar contesta 409 con el nombre de la ficha que ya lo tiene. Si el mismo proveedor de la
misma factura pudiera estar en dos fichas, el programa tendría dos verdades sobre el mismo papel.

**Y un enlace cuyo documento se ha borrado no se cuenta ni se enseña**: el agricultor puede borrar una
factura, y decir «3 vínculos» para que al abrirlos haya dos es peor que no decir nada. Se lee de lo que
hay, así que lo que ya no está no aparece.

### 3.5. Dos contactos con el mismo nombre **pueden** existir, y es a propósito

No hay ninguna restricción de unicidad sobre el nombre, y hay una prueba que lo fija (y que falla si
alguien la añade). Los hermanos que se llaman igual existen, y el programa tiene que poder apuntar a
cada uno. Lo que impide el trabajo duplicado no es una regla de unicidad: es que **el agricultor pueda
enlazar el nombre que ya está escrito en vez de teclearlo**.

### 3.6. La propuesta se confirma **por su clave**, y si cambia se dice

Cada propuesta lleva una clave: la huella de **los textos escritos que la forman**. Al confirmar, el
servidor **recalcula la propuesta** y comprueba que sigue siendo la misma; si entre mirar y confirmar
entra una factura nueva en esa ficha, contesta 409 y **no apunta nada**. Es la misma idea que la clave
de reenvío del almacén, aplicada a una decisión de datos: o se apunta lo que se enseñó, o no se apunta.

**Y la clave cubre también el texto, no solo dónde está** (§8.4, defecto 4): si entre mirar y confirmar
el papel se corrige de una forma que no cambia la agrupación —pasar «Cooperativa X» a «COOPERATIVA
X»—, la clave cambia y el servidor contesta 409. Antes solo cubría `tabla:campo:identificador`, así que
ese cambio entraba sin decir nada y se apuntaba una ficha con un nombre que el agricultor **no había
visto**.

**Y reenviar la misma confirmación devuelve su resultado** (§8.4, defecto 3), porque el contrato lo pide
así (§2: «Reenviar el mismo comando devuelve su resultado; no crea otro movimiento»). Antes, el segundo
envío contestaba 409 «la lista de nombres ha cambiado» — y era mentira: lo que había cambiado es que el
propio servidor acababa de enlazar esos nombres. El camino era real (un doble toque con guantes), y
ahora el servidor devuelve el mismo resultado diciendo que ya estaba apuntada, **y el botón se apaga
mientras la petición está en el aire**.

### 3.7. Deshacer no se lleva el trabajo del agricultor

Una ficha la crea la migración (`origen="migracion"`) o el agricultor (`origen="a_mano"`). Deshacer borra
**los enlaces de la migración** y **solo las fichas de la migración que no haya tocado nadie**; una ficha
que él ha corregido, o a la que le ha enlazado algo, tiene `editado_a_mano` y **se queda**, con su
nombre en la respuesta. Volver atrás no puede llevarse trabajo suyo, y callarlo haría creer que se ha
deshecho todo.

### 3.8. El guion hace exactamente lo mismo que la pantalla

`scripts/migrar_contactos.py` **llama a `contactos_api.aplicar_la_migracion` y a `deshacer_la_migracion`**
en vez de escribir las fichas por su cuenta, y usa `contactos.proponer` para agrupar. Si el guion tuviera
su propia copia de la regla, un día la pantalla diría una cosa y el guion otra — y ese es exactamente el
fallo que este ticket persigue. Hay una prueba que lo comprueba leyendo el fichero.

### 3.9. Y el informe del guion **no toca el esquema**

Esto se descubrió **ensayando sobre una copia de la base de verdad** y es el fallo más feo de los que ha
tenido este ticket: la primera versión ponía el esquema al día también sin `--migrar`, así que imprimía
«Esto es solo el informe: no se ha tocado nada» **después de haber reconstruido diecisiete columnas**.
Ahora el informe **no crea nada** (y lo dice: «esta base todavía no tiene las tablas de los contactos»), y
hay una prueba que compara la **huella del fichero** antes y después del informe. Que no cambie ni un byte
es lo que hace que el informe se pueda pasar sobre la base del agricultor sin miedo.

### 3.10. Faltaban dos cosas por el camino, y las dos las cazó una prueba

1. **Una puerta que no existía.** La lista de sitios con un nombre escrito tenía ocho entradas, y una era
   `articulos.proveedor`: **esa columna no existe** (el proveedor de un artículo del almacén es el de la
   **recepción** con la que entró). La prueba que ata la lista a los modelos lo dijo antes de que llegara
   a producción.
2. **Una tabla que no existía.** En una base antigua puede no estar todavía la tabla `recepciones` (el
   programa la crea al arrancar). El informe se cayó con una traza de SQLite. Ahora, una tabla que no está
   **no tiene nombres escritos**: no es un fallo, es un dato.

---

## 4. Lo que **no** se ha hecho, y por qué

1. **Las tablas del ordenador para las dos listas.** Las fichas y los nombres escritos se miran en
   tarjetas, como las demás listas que aún no tienen tabla (lo dice `docs/REACT.md`: «las tablas de las
   listas que quedan»). La tarjeta es la pieza que ya existe, y estas dos listas se miran de pie en la
   nave tanto como en el despacho.
2. **Fusionar dos fichas que ya existen.** El ticket prohíbe la fusión insegura y no pide una herramienta
   de fusión: lo que hay es **enlazar el nombre escrito con la ficha que toque** (y quitar el enlace de la
   otra), que hace lo mismo sin escribir en ningún documento y sin poder equivocarse en silencio.
3. **Enlazar desde la pantalla de la factura o de la venta.** El camino que hay es el contrario: desde la
   ficha se busca entre los nombres escritos. Añadirlo en cada documento sería tocar siete pantallas de
   otros tickets, y el ticket pide los enlaces y la migración, no un botón en cada papel. **Se dice aquí
   porque es una ausencia que se nota**: quien apunte una factura nueva tendrá que ir a la ficha a
   enlazarla.
4. **Enlazar el proveedor de una semilla o de un lote.** La semilla es un artículo del almacén y su
   proveedor es el del albarán con el que entró (o el de la ficha del producto). Enlazar también ahí sería
   el mismo dato contado dos veces.
5. **El `<select>` de los papeles en el asistente.** Los papeles se marcan en la ficha. El asistente no
   pregunta por contactos porque no los usa para nada: quien apunta un tratamiento sigue eligiendo su
   aplicador de la lista de siempre (`/api/aplicadores`), que no se ha tocado.
6. **Un catálogo oficial de papeles.** No existe: la lista de doce es **nuestra** y se dice en el código.
   Lo que sí sale del ticket y del contrato son los papeles que nombra (proveedor, comprador, asesor,
   aplicador, transportista, taller, laboratorio, veterinario, arrendador).

---

## 5. Las pruebas

### Python

```bash
cd backend
../.venv/Scripts/python.exe -m pytest -q -p no:randomly --junit-xml=$env:TEMP\final_t11.xml
```

**Recuento real: 3700 pruebas de Python en la suite entera** (65 son de este ticket) y **2 fallos, 0
errores y 1 saltada**. **Los dos fallos son el guardián de los recuentos** (`test_lista_de_la_junta.py`),
y no se pueden tocar desde aquí: el coordinador pidió expresamente que **no** se editaran los tres
documentos de recuentos (`README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md`), que siguen diciendo
**3678 de Python y 852 de JavaScript** mientras el árbol ya tiene **3700 y 867**. Es decir: el guardián
está **haciendo su trabajo** —un número escrito a mano en tres documentos se queda viejo solo— y **lo
alinea él al cerrar**. Fuera de esos dos, la suite entera está en verde, incluidas las 6 pruebas de la
revisión independiente (`tests/test_revision_t11.py`).

> **Medido después del último cambio, y esto se dice porque es una regla de la casa** (el T06 lo pagó:
> su informe dio por buenas unas cifras medidas antes de su última edición y el árbol que entregó estaba
> en rojo). El último cambio del ticket es de **JavaScript** —el rótulo del botón de buscar, §8.3— y de
> esta última ronda de arreglos; la suite de Python se ha vuelto a pasar **después**: 3700 pruebas, y los
> dos únicos rojos son el guardián de recuentos. La de JavaScript, que es la que toca esos cambios,
> también: **867 y 867**.
>
> **Y el total del proyecto sigue moviéndose sin que yo toque Python**: pasó de 3677 a 3678 entre dos
> pasadas mías y de 3678 a 3700 en esta última, porque **otros procesos siguen añadiendo pruebas del T10
> y del arranque** en el mismo árbol. Lo que no se mueve es lo mío: **65 pruebas de Python y 47 de
> JavaScript**.

> **Y una cosa que pasó de verdad, medida y contada.** Una pasada intermedia de la suite entera dio **3677
> pruebas y 1 fallo**, y el fallo era ese guardián: la documentación decía **3663** en un fichero y
> **3677** en otro, porque **los estábamos actualizando dos procesos a la vez** (yo y el del T10). Puesto
> el mismo número en los tres, el guardián pasó. Es exactamente el fallo que ese guardián existe para
> cazar, y por eso se cuenta aquí en vez de esconderse.

Las 65 pruebas propias, por lo que defienden:

* **La misma persona no se teclea dos veces**: tres facturas del mismo proveedor dan **una** ficha con
  tres enlaces; usar la ficha dos veces no crea una segunda; y el mismo nombre en una factura y en una
  venta le da **dos papeles** (proveedor y comprador), que es lo que enseña que los papeles se solapan.
* **Lo que no se puede asegurar no se junta**: una tilde de menos («Agrícola» / «Agricola»), una razón
  social de más («Cooperativa X» / «Cooperativa X S.L.»), el mismo nombre con dos NIF, y —al revés— que
  **las mayúsculas de más sí son el mismo nombre**. Y que **el servidor no junta nada aunque se lo
  pidan** (409 y la base se queda vacía).
* **El mismo NIF sí es una prueba**: dos formas de escribir la misma empresa con el mismo CIF se juntan,
  la ficha se queda **con el NIF** y las dos formas de escribirla no se pierden. **Y solo cuando el
  nombre acompaña** (§8.4, defecto 1): el mismo NIF con dos nombres que no se parecen **no se junta**.
* **La migración no toca ni una letra**: mirar la revisión dos veces no escribe nada (se cuentan las
  fichas, los enlaces y los papeles antes y después); aplicar no cambia **ningún** texto escrito
  (comparado letra a letra, y `textos_tocados: 0`); y el enlace guarda lo que decía el papel.
* **Y revierte**: deshacer quita las fichas y los enlaces, deja los textos como estaban, y **respeta la
  ficha que el agricultor ha corregido** (que se queda, con su nombre en la respuesta).
* **Enlazar no borra el nombre**: ni al enlazar, ni al quitar el enlace, ni al **cambiar el nombre de la
  ficha** (el texto de la factura se lee antes y después); y si el papel ha cambiado desde el enlace, se
  dice (`texto_cambiado`, con lo que decía entonces).
* **Las puertas cerradas**: no se puede enlazar desde una tabla que no está en la lista (404), ni un
  hueco (409), ni un texto que ya tiene dueño (409 con el nombre de la ficha), ni un papel inventado
  (422, y **sin guardar la mitad**); y borrar una ficha **no toca ningún texto**.
* **De otra finca no se ve nada**: 404 (y no 403) en la ficha, sus papeles, sus enlaces y sus enlaces de
  nombres escritos de otra finca, y esa finca no ve ni una ficha ni un nombre escrito.
* **Sin vale de sesión**: 401 en las siete puertas.
* **La lista de puertas y las columnas de verdad**: las siete puertas, sin repetir, y cada tabla y cada
  columna **existen en los modelos** (la prueba que cazó `articulos.proveedor`); las tres tablas nuevas
  llevan `explotacion_id`; y **no hay ninguna restricción de unicidad en el nombre**.
* **La comparación de nombres, sola**: las mayúsculas, la tilde, el prefijo, los apellidos distintos, el
  NIF con puntos y guiones, el nombre que gana cuando hay dos formas de escribirlo, un nombre en blanco
  que no propone nada, y los cinco números del resumen.
* **Las cuatro ramas de la regla del NIF** (§8.4): nombre igual + mismo NIF → segura; nombres que se
  parecen + mismo NIF → segura; **nombres que no se parecen + mismo NIF → NO segura**, con su motivo y
  con el NIF delante, y **el servidor no la apunta aunque se lo pidan**; y el mismo nombre con dos NIF →
  no segura. Más el caso de tres nombres con el mismo NIF donde uno no encaja (que es lo que demuestra
  que la comprobación es **dos a dos** y no «cada uno con el primero»), y el caso cruzado de papeles
  (proveedor + laboratorio) que midió la revisión.
* **El guion no apunta la del NIF con nombres distintos**: se fabrica una base con los dos NIF iguales,
  se pasa `--migrar` **de verdad** y se comprueba que no crea ninguna ficha, que lo dice con esas
  palabras y que la huella de los nombres escritos no cambia.
* **El reenvío de la misma confirmación** (§8.4): la segunda vez contesta **200 con el mismo resultado**
  (misma ficha, mismos enlaces), con el aviso de que ya estaba apuntada, y sin duplicar nada (una ficha y
  dos enlaces después de tres envíos). Y el 409 sigue existiendo para lo que de verdad ha cambiado: con
  los textos de esa propuesta repartidos (uno enlazado y otro no) sí contesta 409.
* **La clave cubre el texto** (§8.4): si entre mirar y confirmar el papel pasa de «Cooperativa X» a
  «COOPERATIVA X», el servidor contesta 409 y no apunta nada; y en pequeño, que la huella de la misma
  propuesta cambia con el texto y no cambia sin él.
* **El guion de la migración**: el informe **no cambia ni un byte** de la base (huella del fichero), el
  viaje de ida y vuelta cuadra y no toca los nombres, y el guion usa **la misma** regla que la pantalla
  (nombra `aplicar_la_migracion`, `deshacer_la_migracion` y `proponer`, y no tiene ni un `UPDATE`).
* **La copia de los textos de JavaScript** no se queda vieja (texto por texto contra el servidor), lleva
  todos los papeles y **exactamente** los nombres de las tablas que piden las puertas.

### JavaScript

**Divididas en dos mitades, y la segunda es la que faltaba (§9.2, defecto 2):** unas prueban **lo que se
pinta** (los componentes, sin navegador) y otras **pulsan los botones de verdad** contra el manejador
delegado de `app.js`, con un DOM y un servidor de mentira, y miran **lo que sale por la puerta**.

```bash
cd backend
node --test "tests_js/*.test.js"          # el total del proyecto: 867, 867 en verde
node --test tests_js/contactos.test.js    # las de este ticket: 47, 47 en verde
```

**Las que pintan** comprueban: la lista de fichas y su estado vacío; que una ficha sin ningún nombre
enlazado **no diga «0 papeles»**; los ocho `id` de la ficha; que «¿es una persona o una empresa?» tenga
**tres** respuestas; que los papeles **se marquen de uno en uno y a la vez** (con su `data-elegido`);
que «dónde está escrito su nombre» enseñe **el texto del papel** y su botón de quitar; el aviso de que
el papel ha cambiado desde el enlace; que borrar **pregunte antes**; los tres bloques de la revisión; que
**lo que se puede apuntar lleve su botón y lo que se parece NO**; que el botón de apuntar salga
**apagado** mientras la petición está en el aire; y que **ninguna frase esté escrita a mano**.

**Y las que pulsan** (las nuevas de esta ronda, contra el manejador de verdad):
AÑADIR UNA FICHA + GUARDAR manda el alta con lo escrito; sin nombre **no se molesta al servidor** y se
dice qué falta; abrir una ficha la pide y GUARDAR manda un **PUT** (no un alta); marcar un papel manda el
papel y si se pone o se quita; ENLAZAR UN NOMBRE pide los que están sin dueño y ENLAZAR manda **dónde
está el texto** (y **no** el nombre, que lo lee el servidor del papel); QUITAR EL ENLACE manda el borrado
con el identificador del vínculo; BORRAR **no llama al servidor hasta que se confirma**, y «MEJOR NO»
deja la ficha como estaba; APUNTAR ESTA FICHA manda su clave; **APUNTARLAS TODAS manda las seguras y
ninguna de las que hay que mirar**; DESHACER manda el deshacer y enseña lo que se ha quedado; desde la
lista se llega a la revisión y el buscador filtra por lo escrito; y el doble toque se prueba **con la
primera petición todavía en el aire**, comprobando que la pantalla dice que está enviando y que después
vuelve a su sitio.

### Comprobado en un navegador de verdad

**1. El guion del coordinador, tal cual.** `scripts/comprobar_en_un_navegador.py` **es suyo y no se ha
tocado**. Se ha lanzado contra un servidor de verdad (con su base en una carpeta temporal) y **termina
en verde**: `RESULTADO: la interfaz se abre y se dibuja en un navegador de verdad`, con las capturas
guardadas en la carpeta temporal y el fichero de la comprobación borrado al terminar. Recorre, entre
otras, las dos pantallas de T10 a 390, 1024 y 1440 px.

**2. Y las dos pantallas nuevas de T11, con la misma técnica** (Chrome sin ventana y `--dump-dom`),
desde un guion que vive en la carpeta temporal y no en el repositorio. Ese guion crea una cuenta, siembra
tres ventas con el mismo nombre y uno que se parece, abre `#/contactos` y `#/contactos/revisar` **por su
dirección** a 390, 1024 y 1440 px y comprueba, en cada una, que **se ha medido en un hueco de verdad**
(390, 1024 y 1440 px), que la pantalla tiene contenido (7.280 y 8.838 caracteres), que **no se sale de lo
ancho** y que **no aparece el aviso de emergencia de React**. Resultado: **30 de 30 en verde**, con
capturas en la carpeta temporal y el fichero que escribe dentro de `backend/web/` **borrado al terminar**
(y comprobado que no está).

De la captura de 1024 px se ve lo que defiende el ticket: la revisión dice **«Se te proponen 2 fichas,
con 3 nombres escritos»**, el bloque **«Se pueden apuntar»** con los dos nombres escritos iguales y su
botón, y —más abajo— el bloque **«Estos los tienes que mirar tú»** con el que se parece, **sin ningún
botón de apuntar**.

### El recorrido de humo, contra un servidor aislado

```bash
# en una terminal, con su base en el temporal:
CUEDIGITAL_DATABASE_URL=sqlite:///$env:TEMP\t11_servidor\servidor.db python -m uvicorn app.main:app --port 8011
../.venv/Scripts/python.exe scripts/humo.py http://127.0.0.1:8011
```

**70 `[OK]` y 9 `[FALLO]`**, y **los nueve son los mismos que ya estaban documentados** en
`docs/T06_MAPA_Y_TIERRA.md` §5.4 (tres del dictado y seis del certificado y la firma, que necesitan algo
de fuera que aquí no está: un modelo configurado y un certificado). Ninguno tiene que ver con este
ticket: **el guion no tiene ninguna comprobación de contactos**, y las secciones 1 a 10 ter pasan
enteras. `scripts/humo.py` es del coordinador: **si conviene añadirle un caso de contactos, son cuatro
líneas y las tiene que hacer él.**

### El guion de la migración, ensayado sobre una copia de la base de verdad

**No se ha abierto la base del agricultor.** Se copió a una carpeta temporal y **se comprobó su huella
SHA-256 antes de usarla**: `71456b0b1e1fe444593939571f16580e5702c53047185837dc270abf3696ba0d`, la misma
que traía. Sobre esa copia, y en este orden:

| Paso | Resultado |
|---|---|
| Informe (sin `--migrar`) | **La huella del fichero no cambia**: ni un byte. 3 fincas: la de David **0 nombres escritos**, «Prueba» 0, y la finca de la prueba del navegador **1** («Laboratorio Agrario de Villamuriel», de un análisis). |
| `--migrar` | 1 ficha y 1 enlace. `textos escritos tocados: 0`, y **la huella de los nombres escritos es la misma antes y después**. |
| `--deshacer` | 1 ficha quitada y 1 enlace deshecho. Los textos, otra vez idénticos. |

Y después **se cerró el motor de la base y se borró la carpeta temporal**, y se volvió a medir la huella
de la base real: **la misma**. Lo que este ensayo enseña, y conviene decirlo: **en la base de David no
hay hoy ningún nombre escrito a mano en ninguna factura, venta ni análisis**, así que la migración no
tiene nada que hacer en ella. Está construida y probada, y hará su trabajo el día que haya papeles.

---

## 6. Lo que no se ha podido comprobar

1. **La migración sobre una base con muchos nombres escritos.** El ensayo sobre la copia de la base real
   tiene **1** nombre escrito (y en la finca de David, **0**), así que lo que está probado a fondo es el
   caso pequeño: la suite usa bases de prueba con tres y seis nombres. Una base con cientos de facturas
   repetidas del mismo proveedor no se ha visto.
2. **Los recuentos de pruebas en un repositorio que se mueve.** Mientras se hacía este ticket **otro
   proceso estaba añadiendo pruebas del T10** (ver el aviso de §2), así que los números exactos son los de
   la última pasada y no una constante.
3. **El aspecto en un móvil de verdad, con el sol de frente y con manos de agricultor.** Eso exige la
   prueba con tres agricultores (apartado 5.18 del documento del MVP). Lo que sí se ha medido es que las
   dos pantallas **no se salen de lo ancho** a 390, 1024 y 1440 px y que usan las piezas y las clases de
   siempre (la tarjeta, el campo, el botón, la barra de acciones), así que heredan el comportamiento del
   armazón del T04.
4. **Enlazar desde la pantalla de la factura o de la venta.** No existe (§4.3). Está comprobado por la
   puerta HTTP y por la pantalla de la ficha, pero **no por el camino que el agricultor haría con una
   factura delante**, porque ese camino no está.
5. **El caso de dos contactos homónimos creados a mano y usados a la vez.** Está probado que la base lo
   permite y que la migración no los junta, pero no hay ninguna pantalla que enseñe «tienes dos Juan
   García» al elegir uno: el aviso existe en la **revisión de los nombres escritos**, no al elegir un
   contacto para un papel.

---

## 7. Lo que hace falta de otros, y lo que se pide

1. **Al coordinador: las dos pantallas nuevas en `scripts/comprobar_en_un_navegador.py`.** Hoy **no se
   recorren** con su guion. Añadirlas son cuatro líneas en su lista `PANTALLAS`, y con eso quedarían
   cubiertas por la comprobación que él mantiene (y que sí tiene, desde el T10, la medida estrecha de
   verdad a 390 px dentro de un hueco). Lo mismo para un caso de contactos en `scripts/humo.py`.
2. **Nada de fuera, para este ticket.** No hay ningún servicio de terceros: los contactos son datos del
   agricultor y todo lo que se comprueba es local. Lo único que el ensayo pidió es **una copia de su base
   de datos**, y esa copia ya está borrada.
3. **Y una decisión suya, si quiere tomarla:** el renglón del menú se llama «Las personas y las
   empresas» y va entre los análisis y el plan. Si prefiere otro nombre o otro sitio, es **una línea** en
   la tabla `MODULOS` de `app.js` y su texto en `textos.py`.

---

## 8. Tres cosas que salieron mal, contadas como fueron

Van aquí y no escondidas porque es lo que se espera de este proyecto: las tres se encontraron, se
arreglaron y **se les escribió su prueba**, que es lo que hace que no vuelvan.

### 8.1. El informe decía «no se ha tocado nada» y por debajo había puesto el esquema al día

Es el más feo. La primera versión de `scripts/migrar_contactos.py` llamaba a `database.crear_tablas()`
**siempre**, y esa función no solo crea tablas: **reconstruye las que ya existen** para que ciertas
columnas puedan decir «no se sabe» (la migración del T02). O sea que el informe imprimía «Esto es solo el
informe: no se ha tocado nada» después de haber reconstruido **diecisiete columnas** de la base del
agricultor.

Lo cazó el ensayo sobre una copia de su base: la primera pasada imprimió la lista de columnas
reconstruidas **antes** del informe. Ahora el informe **no crea nada** y lo dice al revés («esta base
todavía no tiene las tablas de los contactos»), y hay una prueba que compara la **huella del fichero
entero** antes y después de pasar el informe. Que eso sea verdad es lo que permite mirar la base de
verdad sin miedo.

### 8.2. Una puerta que no existía: `articulos.proveedor`

La lista de sitios con un nombre escrito tenía ocho entradas, y una era la del proveedor de un artículo
del almacén. **Esa columna no existe**: el proveedor de un artículo es el de la **recepción** con la que
entró. La lista tenía una puerta inventada y la prueba que la ata a los modelos
(`test_las_tablas_y_las_columnas_existen_de_verdad`) lo dijo **antes** de que llegara a producción —
porque el resto de pruebas pasaban: una tabla de más en una lista no rompe nada hasta que alguien la usa.

### 8.3. La pregunta del campo, dentro del botón

Al mirar la captura de 390 px se vio que el botón de buscar decía **«Buscar por el nombre»**: era el
mismo texto que la pregunta del campo, puesto en los dos sitios. Se arregló con un rótulo aparte
(`buscar_boton`: «BUSCAR»), que ya estaba escrito en `textos.py` y **no lo usaba nadie** — o sea que la
primera versión tenía un texto sin usar y un botón con la pregunta entera dentro.

Lo que enseña: **una captura del ancho estrecho encuentra cosas que ninguna prueba mira**, y por eso el
contrato pide los tres anchos y no solo el de escritorio. La prueba del rótulo se añadió con el arreglo
(el botón tiene que decir «BUSCAR»), pero lo que lo encontró fue mirar la captura.

---

## 9. La revisión independiente: cuatro defectos y lo que se hizo con ellos

**Esto se añade después, y se añade entero.** El ticket se entregó, se congeló y lo revisó otro agente con
sus propias pruebas (`docs/REVISION_T11.md` y `backend/tests/test_revision_t11.py`, 6 pruebas: 4 que
fallaban mientras el defecto existiera y 2 que fijan lo que **no** se pudo romper). Encontró **cuatro
defectos** y este apartado cuenta qué era cada uno, qué se cambió y **con qué prueba se sabe** que ya no
está. Las 6 pruebas de la revisión **están en verde** y no se han tocado ni ellas ni el informe.

### 9.1. GRAVEDAD ALTA — el NIF fusionaba a dos personas distintas y lo llamaba «seguro»

**Qué pasaba.** `contactos.proponer` unía dos grupos de nombres cuando compartían un NIF **sin mirar si
los nombres tenían algo que ver**. Así que un NIF tecleado mal —un dígito cambiado, el número de otro
proveedor, un CIF repetido— fundía a dos personas en una ficha con `motivo="mismo_nif"` y
`segura=True`. Y como era «segura», **no salía en ningún aviso**: la pantalla la ponía en «Se pueden
apuntar» con su botón, «APUNTARLAS TODAS» la incluía y `migrar_contactos.py --migrar` la apuntaba sola.
La tabla del §3.1 decía «Son **el mismo nombre** y llevan el mismo NIF → se juntan»: la primera mitad de
esa frase **no estaba en el código**. La revisión lo midió con dos facturas de «Juan García López» y
«Pedro López Ruiz» con el mismo NIF, y también cruzando papeles (un proveedor y un laboratorio).

**Qué se cambió.** Juntar por NIF exige ahora que **los nombres sean compatibles**
(`contactos.nombres_compatibles`): escritos igual (mayúsculas aparte) **o** que se parezcan. Si el NIF
coincide y los nombres no tienen nada que ver, la propuesta sale **no segura** con su motivo propio
(`mismo_nif_nombres_distintos`), y se enseña con **los dos nombres y el NIF delante** para que decida el
agricultor. La comprobación es **dos a dos**, no «cada uno con el primero»: con la comprobación floja, un
tercer nombre distinto entraría por la puerta del que sí se parece al primero.

**Con qué se sabe que ya no está.** `TestDefecto1ElNifNoPuedeFusionarDosNombresQueNoSeParecen` (la
prueba de la revisión) y cinco pruebas mías: la rama del nombre igual + mismo NIF (sigue segura), la de
los nombres que se parecen + mismo NIF (sigue segura), la de los nombres distintos (no segura, con su
motivo, su NIF, el contador `nif_con_nombres_distintos` y **409 si se manda su clave**), el caso de tres
nombres donde uno no encaja, y el caso cruzado de papeles. Y **`--migrar` no la apunta**: se fabrica una
base con los dos NIF iguales, se pasa el guion de verdad y se comprueba que no crea ninguna ficha.

### 9.2. MEDIA — ningún botón de contacto se pulsaba en ninguna prueba

**Qué pasaba.** Mis 32 pruebas de JavaScript **pintaban** las pantallas y leían los `data-accion` del
HTML: no había ni un `pulsar(...)`, ni un `dispatchEvent`, ni una llamada al manejador. En este programa
todos los clics los atiende **un manejador delegado** de `app.js` que lee `data-accion`, así que un botón
cuya acción no llegue al manejador **se pinta, se pulsa y no pasa nada**, sin ningún error. Es
exactamente lo que en el T10 escondió el botón «SEMBRAR ESTA SEMILLA».

**Qué se cambió.** Se copió el arnés que ya existía en `tests_js/semillas.test.js` (un DOM de mentira,
`localStorage` con el vale, un `fetch` que apunta lo que se manda y un `pulsar()` contra el manejador
delegado) y se escribieron **quince pruebas que pulsan de verdad** los once botones que escriben:
`contacto-nuevo`, `contacto-guardar` (alta y corrección), `contacto-borrar-si`, `contacto-papel`,
`contacto-enlazar-abrir`, `contacto-enlazar`, `contacto-desenlazar`, `contactos-revisar-abrir`,
`contacto-migracion-apuntar`, `contacto-migracion-todas` y `contacto-migracion-deshacer`. Lo que se mira
no es lo que se pinta: es **lo que sale por la puerta** (la petición con sus datos) y en qué pantalla
acaba.

**Con qué se sabe que ya no está.** `TestDefecto2LosBotonesDeLosContactosNoSePulsanEnNingunaPrueba` (la
prueba de la revisión, que busca un clic de verdad para cada uno de esos once) y las quince pruebas
nuevas. **La revisión comprobó además que no había ningún botón roto** (19 acciones pintadas, cada una
con los `data-*` que su manejador lee y ninguna sin palabra) — o sea que esto era un hueco de pruebas, no
un botón que no funcionara, y conviene no confundir las dos cosas.

### 9.3. MEDIA — reenviar la misma confirmación contestaba 409 y decía una mentira

**Qué pasaba.** `POST /api/contactos/migracion/aplicar` recalculaba la propuesta con los textos
**libres**; en el reenvío esos nombres ya tenían dueño (los había enlazado el propio servidor), así que la
clave no aparecía y contestaba **409 «La lista de nombres ha cambiado desde que la miraste»** — y no había
cambiado nada. El contrato (§2) pide lo contrario: *«Reenviar el mismo comando devuelve su resultado; no
crea otro movimiento»*. Y el camino era real: **el botón de apuntar no se deshabilitaba mientras
enviaba**, así que un doble toque con guantes hacía exactamente eso.

**Qué se cambió.** Dos cosas:

1. **La propuesta se recalcula sobre TODOS los textos escritos**, no solo sobre los libres, así que la
   misma propuesta se vuelve a encontrar después de aplicarla. Si todos sus textos están enlazados con
   **la misma** ficha, el servidor devuelve **el mismo resultado** de aquella vez (misma ficha, mismos
   enlaces) con el aviso de que ya estaba apuntada; si están repartidos entre dos fichas, o unos sí y
   otros no, entonces sí ha cambiado algo de verdad y se contesta 409. (El 409 sigue existiendo, y hay
   una prueba que lo fija con los textos a medias.)
2. **El botón de apuntar se apaga mientras la petición está en el aire** (`enviando`), que es lo que el
   T10 hace con `guardando`.

**Con qué se sabe que ya no está.** `TestDefecto3ReenviarLaMismaConfirmacion` (la prueba de la revisión) y
dos mías: el reenvío devuelve 200 con los mismos números y sin duplicar (una ficha y dos enlaces tras
tres envíos), el 409 sigue saliendo cuando los textos están a medias, y el doble toque se prueba **con la
primera petición todavía en el aire** (la pantalla dice que está enviando y después vuelve a su sitio),
más el `disabled` sobre el HTML del componente.

> **Un fallo mío dentro de este arreglo, y lo cuento porque es el tipo de fallo que este proyecto
> persigue.** La primera versión de la comprobación de «ya está apuntada» era `if duenos:` sobre un
> conjunto que, con los textos **sin enlazar**, venía con un `None` dentro — y `{None}` es verdadero en
> Python. Resultado: **el primer envío** contestaba 409 «la lista ha cambiado». Lo cazaron mis propias
> pruebas del ticket, que se pusieron siete en rojo de golpe, y ahora se mira «todos y cada uno con
> dueño» y no «hay algún dueño».

### 9.4. BAJA — la clave de la propuesta no cubría el texto

**Qué pasaba.** La clave era la huella de **dónde** están los textos (`tabla:campo:identificador`), no de
lo que dicen. Si entre mirar y confirmar el papel se corregía de una forma que no cambia la agrupación
—pasar «Cooperativa X» a «COOPERATIVA X»—, la clave seguía valiendo y el servidor apuntaba una ficha con
un nombre que el agricultor **no había visto**. El §3.6 prometía «o se apunta lo que se enseñó, o no se
apunta», y con esa huella la promesa no se cumplía.

**Qué se cambió.** La huella incluye **el texto tal y como se enseña**: cualquier corrección entre mirar
y confirmar cambia la clave y el servidor contesta 409, como ya hacía con los demás cambios.

**Con qué se sabe que ya no está.** `TestDefecto4LaClaveNoCubreElTexto` (la prueba de la revisión) y dos
mías: el caso completo por la API (cambiar el papel entre mirar y confirmar → 409 y ninguna ficha) y la
comprobación en pequeño (la misma propuesta con el texto cambiado da otra clave; con el mismo texto, la
misma).

> **Lo que la clave cubre exactamente, dicho sin pasarse:** el texto **tal y como se enseña**, que es el
> que devuelve el servidor ya sin espacios de más (`contactos.limpia`). Un cambio que solo mueva espacios
> de dentro del nombre no cambia lo que el agricultor vio en pantalla, así que tampoco cambia la clave.
> La revisión lo señaló como imprecisión de mi §3.1/§3.4 («el texto tal y como lo escribió él»), y tiene
> razón: **lo que se guarda en el papel no se toca** —eso es exacto—, pero lo que la API devuelve en
> `texto` viene ya limpio.

### 9.5. Y la limpieza que el propio informe había señalado

`textos.CONTACTOS["tabla_almacen"]` («Algo del almacén») **no lo pedía nadie**: sobraba de la octava
puerta (`articulos.proveedor`) que se quitó en el §8.2. Se ha borrado, con su línea en la copia de los
textos de `tests_js/contactos.test.js`, y hay una prueba que ata la lista de nombres de tablas a las
puertas de verdad (`test_la_copia_lleva_las_tablas_donde_hay_un_nombre_escrito`), para que no vuelva a
quedar uno de más.
