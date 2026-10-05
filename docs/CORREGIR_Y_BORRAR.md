# Corregir y borrar lo que uno ha introducido

> **Rondas 91 y 92.** Esto cambia una regla que estaba escrita desde el primer día —«nada se borra»—, así
> que tiene su documento: lo que se decidió, por qué, y qué sigue prohibido. La ronda 91 lo hizo con los
> apuntes del cuaderno; la 92, con las tierras y los grupos.

## Lo que pidió el dueño del proyecto

Literal, por mensaje:

> «recuerda también dejar borrar las cosas que introduzca porque puede que me equivoque, o modificar
> también»

Y tenía razón por una razón que se ve en sus propios datos: hasta esta ronda **su cuaderno estaba
vacío** (64 tierras traídas del cuaderno de la Junta, y ni un tratamiento, ni un abono, ni un trabajo).
Va a empezar a meter cientos de apuntes a mano, y la mitad de las equivocaciones se ven **después** de
guardar: la dosis, la tierra, el día, los kilos.

Lo que había antes no servía para eso:

| Antes de la ronda 91 | Después |
|---|---|
| Un apunte mal metido se podía **anular**, y solo **justo después** de guardarlo (el botón DESHACER de la pantalla de «apuntado»). | Se puede **corregir** o **borrar** desde su ficha en «mi cuaderno», a los tres días o al mes. |
| Un abono, un trabajo o una cosecha **no salían en ninguna pantalla** después de guardarlos: solo se listaban los tratamientos. | Lo apuntado este año sale entero, los cuatro tipos, de lo más nuevo a lo más viejo. |
| Lo único que se podía anular era un tratamiento o un abono. | Los cuatro tipos de apunte se anulan, se corrigen y se borran. |

## La regla de siempre, y cómo se sigue cumpliendo

`models.py` decía: *«Nada se borra. Los registros se anulan y se conserva el rastro. Un cuaderno que se
puede editar sin dejar huella no sirve en una inspección.»*

Eso sigue siendo verdad, y es lo que hay que proteger. Lo de esta ronda **no la deroga: la cumple por
otra vía**, escribiendo en la tabla de auditoría (`auditoria`) en las dos operaciones:

| Qué se hace | Qué pasa con la fila | Qué queda escrito |
|---|---|---|
| **Corregir** | La **misma** fila (`id`), con los valores nuevos | `accion="corregir"` y **campo por campo lo que decía antes y lo que dice ahora** |
| **Borrar** | La fila **desaparece** del cuaderno | `accion="borrar"` y **el registro entero que había**, con la fecha, la finca y quién lo borró |
| **Anular** | Se queda, con `anulado=True` y su motivo | `accion="anular"` y el motivo |

O sea: en el cuaderno no está, y **el programa sí sabe que existió**. Lo que no se puede hacer —ni antes
ni ahora— es que un dato desaparezca sin que quede constancia.

### Por qué corregir en la misma fila y no creando otro apunte

Porque el identificador que viaja a la Junta de cada actividad (`IdAjena`) **es el `id` de la fila**
(ver `iuws_mapeo.py`). Si al corregir se creara otra fila, la Junta tendría dos actividades donde hubo
una —la mala y la buena— y el cuaderno diría que se trató dos veces. Corrigiendo en el sitio, la
actividad es la misma y con los datos buenos.

## Lo único que no se puede borrar: un apunte firmado

La firma es la prueba de lo que había apuntado en un momento dado, y `models.Firma` dice, con razón,
que **una firma no se borra nunca**. Si se borrara el apunte, la firma se quedaría apuntando a algo que
ya no existe y parecería que el cuaderno está respaldado cuando no lo está.

En ese caso el servidor contesta **409** con un mensaje que dice qué hacer («anúlalo: queda tachado, con
su motivo, y la firma sigue cuadrando»), y la pantalla **no ofrece borrar**: ofrece anular. Un aviso que
manda a hacer algo que no existe deja al agricultor sin salida, así que el botón está ahí mismo.

Y si se corrige un apunte que estaba firmado, la firma se queda y el programa ya sabe decir lo que
corresponde: *«este cuaderno se firmó, pero después se ha cambiado algo. Vuelve a firmarlo»*.

## Cómo se corrige, sin escribir un segundo formulario

Corregir **abre el mismo asistente** que apuntar, con lo que ya estaba puesto
(`estado.asistente.borrador`) y con `estado.corregir = {id}`. Al final, el botón no dice APUNTARLO sino
**GUARDAR LOS CAMBIOS**, y lo que se manda es un `PUT` a ese apunte en vez de un `POST`.

La razón de reutilizar el asistente es la de siempre en este proyecto: **el asistente ya es el
formulario** (65 pasos con sus campos, sus listas y sus comprobaciones). Una pantalla de corregir aparte
sería un segundo formulario del mismo apunte, y el día que se añada un dato, el de corregir se quedaría
sin él sin que nadie se entere.

Lo mismo que se aprobó con «lo mismo que la última vez»: el asistente sabe abrirse con un borrador
puesto, y lo único que hacía falta era **traducir el apunte guardado a ese borrador**
(`borradorDeTratamiento` en `nucleo.js`, y los de abono, trabajo y cosecha en `app.js`).

### Y las reglas son las mismas que al apuntar

Un apunte corregido pasa por **las mismas comprobaciones** que uno nuevo (la dosis de la etiqueta, la
superficie de la tierra, las fechas, los días de espera). Si no, corregir sería la puerta de atrás para
meter en el cuaderno lo que el alta no deja. Y los números que calcula el programa (el abono puro, los
kilos totales, el fin del plazo de seguridad) **se vuelven a calcular**, no se copian.

## Lo que se encontró haciendo esto

Tres campos que el agricultor contestaba y **se perdían por el camino** (los tres, mirando el código
campo a campo, comparando lo que manda el formulario con lo que acepta la API):

1. **La máquina con la que se cosechó.** El asistente la preguntaba desde la ronda 5 y el navegador la
   mandaba, pero `CosechaEntrada` no tenía el campo: Pydantic la descartaba **en silencio**. El
   contenido mínimo del CUE pide la maquinaria en su hoja de labores, así que era un dato del cuaderno
   que se quedaba vacío para siempre.
2. **Las observaciones de una labor.** Se guardaban y `LaborSalida` no las devolvía: no se notaba
   mientras ninguna pantalla las enseñaba, pero al poder corregir una labor, el formulario se rellenaba
   con lo que devuelve la API y **corregirla borraba las observaciones sin decir nada**.
3. **Qué se cosechó** (`producto`, dentro de `detalles`) y el **asesoramiento** de un tratamiento: lo
   mismo, se perdían al corregir.

Para que no vuelva a pasar hay una prueba que compara los dos lados, campo a campo:
`tests/test_el_formulario_manda_todo.py`.

Y uno más, de la misma familia: `etiquetaDeValor()` en `app.js` daba por hecho que las tablas del
servidor son **listas** de `{valor, texto}`, y `etiquetas_labor` es un **diccionario**. Pedir el nombre
de una práctica del campo reventaba con «lista.find is not a function»; no se veía porque el único sitio
que lo pedía tenía otra tabla delante que respondía primero.

## Lo que sigue igual

- **La lista del cuaderno no es un editor.** Se corrige abriendo el apunte, con el asistente entero: no
  hay casillas sueltas que se puedan tocar sin querer.
- **Corregir y borrar necesitan cobertura.** La cola de sin cobertura es para **apuntar** (guarda los
  apuntes y los manda con `POST` cuando hay red): no sirve para cambiar algo que ya está en el
  servidor ni para borrarlo. Si no hay cobertura, se dice.
- **El cuaderno firmado sigue avisando** cuando algo cambia después de firmarlo, que es para lo que
  está.

---

# Y ahora las tierras y los grupos (ronda 92)

Lo mismo, pero con **lo que el agricultor dio de alta él**: las tierras, el cultivo declarado de una
tierra y los grupos de parcelas. Una tierra con la referencia del SIGPAC mal copiada es exactamente la
clase de cosa que hay que poder arreglar, y hasta esta ronda la única salida era pedirle a alguien que
la tocara en la base de datos.

## Qué se puede hacer ya

| Qué | Cómo |
|---|---|
| **Corregir una tierra** | `PUT /api/parcelas/{id}`, desde los dos botones de su tarjeta en «Mis parcelas, productos y máquinas». Pasa por **las mismas comprobaciones y las mismas cuentas** que el alta (el sistema, la zona de nitratos del listado oficial). |
| **Borrar una tierra** | `DELETE /api/parcelas/{id}`. **Si tiene apuntes, no se borra**: se contesta 409 diciendo cuántas cosas dependen de ella y qué hacer. |
| **Cambiar o quitar el cultivo declarado** | `POST /api/parcelas/{id}/cultivos` ya sustituía (no deja dos cultivos por campaña); lo que faltaba era poder quitarlo: `DELETE /api/parcelas/{id}/cultivos/{campana_id}`. |
| **Corregir un grupo** | `PUT /api/grupos/{id}`. Un grupo lo junta el programa, así que lo único que se pregunta es **cómo se llama** («Cebada (3 parcelas)» es como lo llama el programa; él lo llamará «el de mi hermano»). |
| **Borrar un grupo** | `DELETE /api/grupos/{id}`. Si algún apunte lo usó, no se borra (409): esos apuntes dejarían de decir dónde se hizo. |

Los botones son **los mismos dos** que en los apuntes (CORREGIR y BORRAR, con el mismo texto y las
mismas clases), y la pantalla que pregunta antes de borrar es **la misma**: cambia lo que enseña.

## Por qué una tierra con apuntes no se borra

Porque borrar una tierra que tiene doce apuntes dentro **destruiría el cuaderno de campo en silencio**:
doce tratamientos o abonos se quedarían sin decir dónde se hicieron, y nadie se enteraría hasta que
llegara una inspección. El servidor cuenta lo que depende de ella —**las siete tablas** que apuntan a
`parcela_id`: tratamientos, abonos, labores, el cultivo declarado, análisis, ventas y planes de
abono— y lo dice con su número, con la salida a mano: borrar o corregir esos apuntes primero, o
corregir la tierra en vez de borrarla. La lista de tablas **se saca de la base de datos** (de sus
relaciones), no de una lista escrita a mano: el día que se añada un apunte nuevo que se hace en una
tierra, cuenta solo.

Y hay un detalle que tampoco se inventa: **borrar una tierra que está dentro de un grupo sí se puede**.
La tabla que las junta no es un apunte, es la lista de tierras con las que se apunta de una vez, y su
fila desaparece sola: el grupo se queda sin esa tierra y sigue siendo un grupo.

## Lo que la corrección NO toca, y por qué

Aquí está la trampa de esta ronda, y es la misma que la de la máquina de la cosecha: **un dato que el
formulario no puede mandar de vuelta se pierde al corregir**. La regla que se aplica ahora, calculada y
en un solo sitio (`_columnas_que_una_correccion_no_toca`):

> **Lo que no se acepta al dar de alta y se devuelve al leer, no se toca al corregir.**

| Tabla | No se toca | Por qué |
|---|---|---|
| `parcelas` | `geometria` | La **forma del trozo**. Está en la entrada (la manda el alta cuando se elige el recinto en el mapa) pero **no en la salida**: el listado manda la línea que se pinta, no el texto del polígono. Sin esta regla, corregir el *alias* de una tierra le borraba la forma y el mapa se quedaba sin el dibujo. |
| | `superficie_sigpac_ha` | La superficie del recinto entero (hoja 2.1 del cuaderno de la Junta). No está ni en la entrada. |
| | `creada_en` | Cuándo se apuntó. **Se llama en femenino** («la parcela») y se le escapaba a la lista de `correcciones.py`, que protege `creado_en`: corregir una tierra intentaba escribirla a nulo y reventaba. Se encontró en la primera ejecución de las pruebas. |
| `grupos_parcelas` | `creado_automaticamente` | Si lo juntó el programa o el agricultor. No se pregunta y decide qué se le ofrece después. |

Y una consecuencia que se dice en voz alta: **corregir la forma de una tierra no se puede desde la
aplicación**. Si algún día hace falta, el camino es devolver la forma en la respuesta o una ruta propia
para el dibujo, no meterla en el formulario a la brava. Está comentado en el código, en el sitio donde
se toma la decisión.

## Lo que dijo Stitch, y lo que se ha hecho con ello

Se le pidieron dos láminas nuevas (`docs/stitch/rediseno/borrar_un_apunte.png` y
`corregir_un_apunte.png`, ronda 92) y **se aplicó lo que mejoraba algo de verdad**:

| Lo que propone | Qué se ha hecho |
|---|---|
| La caja de lo que va a desaparecer, **con su rótulo** («Lo que vas a borrar») | ✅ Se puso: `resumenDelApunte` sabe llevar un título, y la pantalla que pregunta lo usa. Una caja de datos sin título es una caja de datos. |
| Que se vea **en cada paso** que se está corrigiendo, no solo en el título | ✅ Se puso: la propiedad `modo` del asistente («CORRIGIENDO LO APUNTADO»), pegada a la barra de progreso. En el paso 6 de 9 el título ya no se lee. |
| El botón de volver, diciendo **«SIN GUARDAR»** | ✅ Se puso: con la pantalla llena de datos puestos, creer que ya se ha guardado algo es la forma más fácil de perder un arreglo. |
| Explicar qué significa **anular** un apunte firmado | ✅ Se puso: en la misma pantalla que lo ofrece, debajo del aviso, con lo que queda en el cuaderno («se queda tachado, con el día y el motivo»). |
| El resumen de **qué ha cambiado** («Superficie: 4,90 → 4,29») | ❌ **No se puede hacer todavía**: el cambio queda en la auditoría, pero ninguna respuesta de la API devuelve el antes y el después. Queda apuntado en `docs/stitch/LO_QUE_FALTA_POR_DISENAR.md` como idea que necesita función nueva. |
| «Tu firma sigue siendo válida» después de corregir | ❌ **Rechazado, y es lo contrario de lo que dice este programa**: si un cuaderno firmado cambia, la firma **ya no cuadra** y el programa dice «vuelve a firmarlo». Copiar esa frase sería mentirle al agricultor sobre lo que protege su firma. |
| «VER EL HISTORIAL DE CAMBIOS» en el final de una corrección | ❌ Todavía no: el rastro existe (en `auditoria`) y **no se ve en ninguna pantalla**. Hacerlo bien es una pantalla y una ruta nuevas; queda en la lista de ideas con función nueva. |
| «Motivo registrado: corrección de hectáreas reales» | ❌ No se pide un motivo para corregir: lo que se guarda es **qué cambió**, campo por campo, que es más útil que una frase. |
| Una pista debajo de los dos botones de la lista explicando la diferencia | ❌ Rechazado por sitio: la tarjeta ya lleva cinco datos; el que explica la diferencia es la pantalla que pregunta, y ahí está. |

---

# Y ahora todo lo demás (ronda 93)

Con las tierras y los grupos ya hechos, quedaba lo que David da de alta o apunta **fuera del cuaderno**:
las fichas de lo que se usa —**productos, abonos, quién aplica, asesores, máquinas y naves**—, los
**análisis** de laboratorio, lo que ha **vendido**, el **plan de abono**, los **papeles**, las
**facturas**, las **medidas** preventivas y las **campañas**.

## Cómo se hizo sin repetir la misma pantalla nueve veces

Lo que hace falta para corregir y borrar algo es siempre lo mismo, y ahora está en **un registro**
(`OTRAS_COSAS`, en `app.js`): de dónde sale su lista, por dónde se manda el cambio, cómo se cuenta en
una ficha y con qué formulario se abre. Añadir una cosa son cuatro líneas:

```js
producto: cosaDeUnMaestro("producto", "corregir.que_es_producto", () => estado.productos),
```

Y los dos botones son **una pieza nueva** (`react/piezas/acciones_de_una_ficha.js`), que estaba escrita a
mano en cuatro pantallas y se estaba copiando a las que venían. Con la pieza, la siguiente lista que se
añada son dos líneas; sin ella, serían cuatro copias más de lo mismo y una de ellas se olvidaría de algo.

## Lo que se puede hacer ya con cada cosa

| Cosa | Corregir | Borrar |
|---|---|---|
| **Un producto** | Se abre **el mismo formulario del alta** con lo que ya estaba puesto (nombre, nº de etiqueta, dosis máxima, plazo, lote, compra…). Pasa por las mismas comprobaciones. | Sí, si no lo usa ningún tratamiento ni el almacén. |
| **Un abono** | Igual: su riqueza N-P-K mal apuntada se arregla sin borrarlo. | Sí, si no está en ningún abono echado. |
| **Quién aplica / un asesor** | Igual (carne, ROPO, titulación…). | Sí, si no está en ningún tratamiento. |
| **Una máquina / una nave** | Igual (ROMA, ITV, tipo, uso…). | Sí, si no está en ningún apunte. |
| **Un análisis** | Se abre el asistente del análisis con sus datos y **sus números del boletín**. | Sí, salvo que un plan de abono se apoye en él. |
| **Una venta** | El asistente de la venta, con su fecha, su producto, sus kilos, su comprador y su albarán. | Sí. |
| **El plan de abono** | El asistente del plan. **Un plan se puede corregir sin ningún problema: es una previsión, no un apunte.** | Sí, salvo que haya abonos apuntados contra él. |
| **Los papeles** | Se abre **la misma pantalla con la que se guardó un papel** (título, tipo, carpeta, fecha, quién, notas), con sus seis campos puestos y el botón diciendo «GUARDAR CAMBIOS». No se usa el asistente: un papel tiene su formulario, y corregir con otra pantalla sería corregir con una copia que se quedaría sin los campos nuevos. | Sí, y se lleva por delante el fichero guardado (que es lo que se pide en una inspección: un papel borrado no puede seguir descargándose). |
| **Las facturas** | Se abre **la misma pantalla con la que se confirma una factura leída**, pero con lo que ya está guardado dentro y el botón diciendo «SÍ, GUARDAR LOS CAMBIOS»: corregir una factura es el mismo trabajo (mirar el papel y arreglar lo que esté mal), así que no hay una pantalla nueva. El título no puede decir «esto es lo que he leído» —nadie ha leído nada— y el volver lleva a la lista de facturas. Al guardar se manda un `PUT` a **esa** factura, no un alta: si fuera un alta, el agricultor tendría dos y contaría dos veces lo comprado. | Sí, desde la lista de facturas, con la pregunta de siempre. El servidor lo impide si con eso el almacén se quedaría en negativo. |
| **Las medidas preventivas** | Ya se podían cambiar desde siempre (es su pantalla). **Y guardarlas estaba roto sin que nadie lo supiera**: la pantalla mandaba un `POST` a `/api/medidas` y esa ruta **solo acepta `PUT`** (está escrita así a propósito: no se crea un apunte más, se sustituye la declaración entera), así que contestaba 405 y el agricultor leía «No se ha podido» cada vez que intentaba declarar lo que hace en su finca. Está arreglado, con su prueba. | Quitar la declaración entera, con su pregunta: la finca vuelve a estar «sin declarar» y el programa vuelve a preguntar. **No es lo mismo que «no hago ninguna»**, y por eso son dos cosas distintas: «no hago ninguna» es una respuesta y se guarda; quitarla deja la pregunta sin contestar. |
| **Una campaña** (un año del cuaderno) | Se abre **su formulario** (el año, las dos fechas y si está terminado), con lo que ya estaba puesto y el «sí o no» marcado como estaba. Y **se puede empezar un año nuevo**, que era la otra mitad que faltaba: hasta esta ronda la campaña la creaba el programa al darse de alta la cuenta, así que cuando llegaba el año siguiente el cuaderno se quedaba apuntando en el año viejo. | Sí, **si el año está vacío**. La pantalla lo dice antes de que se intente: el BORRAR de un año con cosas dentro sale apagado y al lado se explica por qué. Un año vacío sí se puede quitar —es la única forma de deshacer un año creado de más—, y el año que se está llevando también, si está vacío: bloquearlo convertiría un error corregible en un error para siempre. |

## Corregir una factura: la misma pantalla, y **tres datos que viajan sin que se pregunten**

Una factura se corrige en la pantalla que confirma lo que se ha leído («Esto es lo que he leído»), porque
corregirla **es el mismo trabajo**: mirar el papel y arreglar lo que esté mal. Lo único que cambia es que
el título dice «Esto es lo que tienes guardado» (nadie ha leído nada), la pista avisa de que lo de antes
queda en el historial, y el botón de volver lleva **a la lista de facturas**, que es de donde se salió.

Y ahí estaba el peligro, que es el mismo de las otras dos veces: **esta pantalla no pregunta todo lo que
una factura guardada tiene dentro**, así que corregirla podía borrar datos sin decir nada. Son tres:

1. **Las notas de la factura** (`notas`): el formulario no las tiene y el servidor las habría puesto a
   cero, porque al corregir se copian los campos del formulario uno a uno.
2. **El número de registro y el lote de cada línea** (`numero_registro`, `lote`): vienen del papel y se
   enseñan, pero **no se pueden escribir** en esta pantalla.
3. **El abono al que está enganchada una línea** (`fertilizante_id`): no se pregunta en ninguna pantalla.

Los tres viajan ahora tal cual (`facturaComoInterpretacion()` los copia y `recogeLaInterpretacion()` los
vuelve a mandar), y hay una prueba que lo comprueba en el `PUT`. La regla, escrita otra vez porque es la
tercera vez que aparece: **lo que la pantalla no pregunta tiene que viajar igual, o corregir se lleva por
delante lo que no se ve.**

Lo que **no** se toca al corregir es el fichero del justificante (ni su huella): este formulario no manda
fichero, y para cambiarlo está su propia puerta (`POST /api/facturas/{id}/fichero`), que además borra el
viejo. Y corregir una factura anulada no la resucita: el estado de anulación no es un dato que el
formulario pueda mandar.

## Los años del cuaderno: la última cosa que faltaba, y la que más pesa

De la campaña cuelga **el año entero**: cada apunte guarda su `campana_id`, y el identificador que viaja a
la Junta es el de la fila. Hasta esta ronda `GET/POST/PUT/DELETE /api/campanas` estaban en el servidor y
**no los pedía ninguna pantalla**, así que había dos agujeros de verdad:

1. Un año mal escrito —2027 donde iba 2026— dejaba **todos los apuntes de ese año** colgando de un año que
   no es el suyo, y no había forma de arreglarlo.
2. Cuando llegaba el año siguiente, **no había forma de empezar el cuaderno de ese año**: el programa
   seguía apuntando en el año viejo.

Ahora hay una pantalla («Los años de mi cuaderno», `react/pantallas/campanas.js`) a la que se entra desde
**«Mis datos»**, que es la pantalla de la finca y del cuaderno. Cada año se enseña con su año en grande, sus
dos fechas, si es **el que estás llevando**, si está cerrado y **cuánto hay dentro** —ese número lo cuenta
el servidor (`cuantas_cosas`), porque es lo que explica por qué un año no se puede quitar—; y cada uno
lleva sus dos botones, con el de borrar **apagado** cuando hay cosas dentro (diseño de Stitch: el agricultor
lo ve antes de pulsarlo, en vez de descubrirlo al pulsar).

Dos cosas que se decidieron y conviene saber:

- **El año que se propone al empezar uno nuevo es el siguiente al último que tiene**, con las fechas del año
  natural puestas. No es inventar un dato: es lo que iba a escribir, y lo cambia si su cosecha empieza en
  septiembre (la pista de la pantalla lo dice).
- **«Campaña» no se le dice nunca al agricultor.** Él dice «el año». La palabra del programa se queda en el
  código y en esta documentación.

## Un fallo que solo se vio probando contra un servidor de verdad: guardar las medidas

Al comprobar esta ronda contra un servidor de verdad salió un fallo que llevaba ahí desde que existe la
pantalla de las medidas preventivas: **la aplicación guardaba con `POST` y el servidor solo acepta `PUT`**
en `/api/medidas`. La ruta está escrita con `PUT` **a propósito** («no se crea un apunte más, se sustituye
la declaración entera»), así que un `POST` contesta **405** y el agricultor veía «No se ha podido» cada vez
que intentaba declarar lo que hace en su finca.

Por qué no lo cazó ninguna prueba, y es lo que hay que recordar: **la copia de la API que usan las pruebas
de JavaScript contesta por la ruta y no por el método** (`fetch` falso devuelve por `"/api/medidas"` tanto
si se pide con `GET` como si se manda con `POST`), así que el `POST` equivocado pasaba por bueno. Ahora hay
una prueba que exige el método (`PUT` y **no** `POST`) y el encargo está escrito donde se lee.

Y de paso se abrió la puerta que faltaba: **quitar la declaración entera**. Es distinto de «no hago
ninguna» —una respuesta— y deja la finca sin contestar, que es lo que hace falta para volver a empezar. Se
pregunta antes, como todo lo que quita algo del cuaderno.

## Dos fallos que aparecieron al hacer esto

Y los dos son de la misma familia: **un dato que se pierde al corregir, sin que salte ningún error**.

1. **El botón de volver llevaba a la pantalla de inicio.** Decía «VOLVER A MIS TIERRAS» y el nombre de esa
   pantalla (`mis_cosas`) no estaba en la lista de destinos de `irAInicio`, y un destino que no está cae
   en el `default`. Estaba desde la ronda 92 y no lo veía ninguna prueba porque **la prueba miraba lo que
   dice el botón (`data-ir`) y no en qué pantalla acaba**. Ahora hay una que pulsa el botón y comprueba
   la pantalla.
2. **Corregir un análisis le quitaba los nueve números del boletín.** El paso de la clase de análisis
   vaciaba el diccionario de números «para que no quedaran números de tierra en un análisis de agua», y al
   corregir pasaba por ahí con la clase que ya tenía: vaciaba lo que venía del boletín. Ahora solo vacía
   **si la clase ha cambiado de verdad**. Lo cazó una prueba que comprueba que los números viajan en el
   `PUT`.

Los dos están arreglados y con su prueba.

## Lo que sigue sin poder hacerse, y por qué

- **Corregir la forma de una tierra** (el dibujo del mapa): la forma se puede mandar al dar de alta pero
  no se devuelve al leer, así que el formulario no la tiene. Se explica en el apartado de la ronda 92.
- **Cambiar de sitio un apunte** (que un tratamiento apuntado en una tierra pase a otra): se corrige el
  apunte entero con el asistente, que incluye la tierra, así que sí se puede.
- **Deshacer un borrado**: el rastro existe (en `auditoria`) y no hay pantalla que lo enseñe. Es una idea
  apuntada en `docs/stitch/LO_QUE_FALTA_POR_DISENAR.md`, con lo que haría falta para hacerla bien.


