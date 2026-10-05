# Las facturas de compra: subirlas, leerlas y confirmarlas

Este documento cuenta **por qué el cuaderno necesita las facturas**, cómo se leen (un PDF, un papel
escaneado o una foto del móvil) y qué se hace con lo que se lee. Está escrito a partir de facturas
de ejemplo y de las hojas del cuaderno oficial de Castilla y León.

## 1. Por qué están aquí y no en un cajón

No es para llevar las cuentas de casa. **El cuaderno de la Junta pide datos que solo están en la
factura:**

| Hoja del cuaderno de la Junta | Qué pide | De dónde sale |
|---|---|---|
| **9.1** Información sobre fertilización (ecorregímenes) | **«Empresa suministradora»** y **«Nº de factura»** | Del proveedor y del número de factura |
| **6** Registro de fertilización | **«Nº de albarán»** | Del albarán o de la factura de esa compra |
| **3.1** Registro de actuaciones fitosanitarias | «Producto fitosanitario: nombre comercial y **nº de registro**» | El nº de registro viene impreso en la factura |
| **doc** Documentación a conservar | «Facturas u otros documentos que justifiquen la adquisición de los productos fitosanitarios», **durante al menos 3 años** | El fichero, guardado como justificante |

Y hay una segunda razón, que es la que preguntó David: **saber si cuadra lo que se compra con lo que
se echa**. Sin facturas, «¿me queda producto para tratar esta parcela?» no se puede contestar.

## 2. Cómo se lee un documento (y qué se puede y qué no)

Se prueban las tres cosas por orden, de la más fiable a la menos:

| Lo que sube el agricultor | Cómo se lee | Qué tal sale |
|---|---|---|
| **PDF del proveedor** (por correo) | Se lee su texto tal cual, con acentos y sin equivocarse | Perfecto: es el mejor caso |
| **PDF escaneado** (por dentro es una imagen) | Se dibuja cada página como imagen y se le pasa al lector de letras | Muy bien con el idioma instalado |
| **Foto del papel** (móvil) | Se le pasa al lector de letras | Bien: los números salen casi siempre; alguna palabra con tilde puede fallar |
| **Texto pegado** (`.txt`) | Se lee tal cual | Perfecto |
| **Sin lector de letras instalado** | No se lee: se dice y se escribe a mano | La factura se guarda igual, como justificante |

El lector de letras es **Tesseract**, un programa aparte (no una librería de Python), y es una
decisión: meter un OCR de Python de verdad (EasyOCR, PaddleOCR) son cientos de megas y modelos que
hay que descargar, y el proyecto quiere que sus dependencias se lean en dos minutos.

**El idioma importa, y se dice cuál se ha usado.** Tesseract no sabe español de fábrica. El
proyecto trae el español descargado en `data/ocr/tessdata/` (ver su `LEEME.md` y
`backend/scripts/bajar_idioma_ocr.py`), que se usa **sin tocar la instalación del sistema**. Si solo
hubiera inglés, la aplicación lo dice en la pantalla: los números se leen bien (los dígitos no son de
ningún idioma) pero las palabras con eñe salen cambiadas («PEÑARANDA» → «Pefiaranda»).

## 3. Lo que hace que esto sea de fiar: las cuentas cuadran

Una lectura de una factura **se puede comprobar con aritmética**, y eso es lo que se hace:

- En cada línea: **cantidad × precio = importe**. Si no da, la línea se marca como «no cuadra» y se
  dice en la pantalla, en vez de dar por buena una lectura que se ha equivocado de columna.
- En el total: **la suma de las líneas = base imponible**, y **base + IVA = total**.
- Y el **NIF del agricultor ya se sabe**: en una factura hay dos NIF (el que vende y el que compra),
  así que el proveedor es *el otro*. Sin esto, la mitad de las facturas saldrían con el NIF del
  propio agricultor como proveedor.

## 4. Y aun así, el agricultor confirma

**La lectura es una propuesta, nunca un dato.** La pantalla enseña lo que ha entendido —proveedor,
NIF, número, fecha, base, IVA, total y cada línea con su cantidad, su unidad, su precio y su
importe— todo editable, con los avisos de lo que no cuadra. Lo que se guarda es **lo que él da por
bueno**. Es lo que hace que se pueda leer una foto hecha con el móvil sin jugarse un dato del
cuaderno.

Además, en cada línea se dice **qué producto de su cesta es**, por dos caminos:

1. **Por el número de registro**, si la factura lo trae: es el número único de cada producto, no hay
   duda posible.
2. **Por las palabras del nombre** («GLIFOSATO 36% SL 20 L» → «Glifosato 36 SL»).

Y si el producto no está en su cesta, la línea ofrece **crearlo con los datos de la factura**
(nombre, número de registro, cantidad, unidad, fecha y proveedor). Lo que **no** se inventa es la
dosis máxima, el plazo de seguridad ni la materia activa: eso está en la etiqueta del bote, no en la
factura.

## 5. Qué se hace con lo que se guarda

| Qué | Dónde se ve |
|---|---|
| **Lo comprado de cada producto** | En «lo que tengo en el almacén», con la factura de la que sale cada compra |
| **Lo comprado contra lo echado** | En la misma pantalla: comprado, echado y lo que queda, con la resta **solo cuando las unidades se pueden comparar** |
| **El número de factura y el proveedor** | Es lo que rellenará las hojas 6 y 9.1 del cuaderno oficial |
| **El justificante** | El PDF o la foto, que se puede volver a ver y descargar |

Las decisiones que conviene no deshacer:

1. **Leer y guardar son dos puertas distintas** (`POST /api/facturas/leer` no escribe nada). Primero
   se enseña lo que se ha entendido, y solo después se guarda.
2. **Las facturas mandan sobre la ficha del producto.** Si hay facturas apuntadas, «lo comprado»
   sale de ellas; si no las hay, se usa el número que el agricultor escribió en la ficha. Sumar los
   dos contaría la misma compra dos veces.
3. **Una factura se anula con su motivo** y el fichero se queda: anular es dejar constancia de que ese
   papel existe y ya no cuenta. **Y desde la ronda 93 también se puede corregir y borrar**, porque David
   lo pidió así («deja borrar las cosas que introduzca porque puede que me equivoque, o modificar
   también»): corregirla cambia sus datos y sus líneas **y las cuentas se vuelven a comprobar**; borrarla
   se lleva la fila, sus líneas y su justificante del disco, y queda el rastro en la auditoría.
   **Lo que no se deja** es borrar una factura cuando con ella el almacén cuadraba y sin ella saldría
   «has gastado más de lo que has comprado»: ahí se contesta con el número de apuntes que se quedarían
   sin compra. Y la salida para una factura repetida es **anularla primero y borrarla después** (una
   anulada ya no cuenta en el almacén, así que la cuenta es la misma con la fila y sin ella). Todo el
   razonamiento está escrito en `facturas_api.borrar_factura` y en
   [`docs/CORREGIR_Y_BORRAR.md`](CORREGIR_Y_BORRAR.md).
4. **Un producto de otra finca no se puede enganchar** a esta factura, ni un abono.
5. **Subir dos veces la misma foto se avisa** (se compara la huella del fichero): apuntarla dos
   veces descuadraría el almacén y las cuentas.

## 6. Cómo se comprueba

| Qué | Cómo |
|---|---|
| La lectura de un PDF y de una foto | `backend/tests/test_facturas.py`: 61 pruebas. Las facturas de prueba **se fabrican** con `reportlab` (que ya es dependencia) porque las de verdad llevan el NIF y los precios de una persona |
| La lectura de una foto **de verdad** | El mismo fichero: dibuja el PDF como imagen y le pasa el lector de letras. Si en el ordenador no hay lector instalado, esa prueba se **salta** y lo dice |
| La pantalla | `backend/tests_js/interfaz.test.js`: leer sin guardar, confirmar lo que hay en pantalla, avisar de la factura repetida y no intentarlo sin conexión |
| Contra un servidor de verdad | `python scripts/humo.py <dirección>`, apartado **29** |
