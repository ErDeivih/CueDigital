# El rediseño de la interfaz (rondas 76 a 90, 28 y 29/09/2026)

Aquí están los diseños que devolvió **Stitch** cuando se le pidió rehacer la interfaz entera, con sus
capturas al lado. Se guardan para poder mirarlos sin depender de Stitch ni de una dirección de Google que
caduca, y para que quede escrito **qué se pidió y qué salió**.

## Cómo se pidió

1. **El proyecto**: `CueDigital - cuaderno de campo y digital` en Stitch (MCP,
   `https://stitch.googleapis.com/mcp`). La clave de la API **no está en el repositorio**: se pasa por
   variable de entorno o por un fichero temporal, igual que la del certificado.
2. **El sistema de diseño**: se le subió **nuestro `DESIGN.md`** (`upload_design_md` +
   `create_design_system_from_design_md`), así que diseña con nuestros colores, nuestros tipos y nuestras
   medidas (letra de 18 px, botones de 64 px, contraste alto, sin sombras ni degradados).
3. **Lo que se le pide de cada pantalla** está en `backend/scripts/disenar_con_stitch.py`: qué tiene que
   resolver esa pantalla, con **el texto real de `textos.py`**, y las reglas del campo (móvil, una mano,
   sol, sin menús escondidos, sin barra de pestañas, iconos dibujados y no emoji).

## Lo que hay

| Fichero | Pantalla |
|---|---|
| `inicio.png` / `inicio_grande.png` | La pantalla de inicio («¿Qué has hecho hoy?») |
| `asistente.png` / `asistente_grande.png` | Un paso del asistente (elegir la tierra) |
| `mi_cuaderno.png` / `mi_cuaderno_grande.png` | «Mi cuaderno», con sus bloques |
| `mis_tierras.png` / `mis_tierras_grande.png` | La lista de tierras |

Cada uno lleva su `.html` (el diseño tal cual lo devolvió Stitch, con sus trazos de icono dentro) y su
`*_explicacion.md` (lo que Stitch cuenta de por qué lo ha hecho así). `inicio_grande.png` y sus hermanos
son la misma captura pedida más grande (`=s1600`), que es la que se puede mirar de verdad.

## Qué se ha aplicado ya (rondas 76 a 88)

**Ronda 76 — el lenguaje de los botones y los iconos:**

- **Los botones**: el botón normal pasa a ser una **tarjeta blanca con borde grueso oscuro** y el verde
  sólido se reserva para **la acción principal**. Antes eran todos verdes y sólidos, así que «HE ECHO
  PRODUCTO» se veía igual que «NO SÉ QUÉ PULSAR»: no había jerarquía.
- **Los iconos**: los emoji se cambian por **dibujos de línea en SVG** (`componentes.js`), con los trazos
  del diseño. La clave sigue siendo el emoji del texto del servidor, así que `textos.py` no se toca.
- **El cuadro del icono**: el dibujo va dentro de un cuadrado con su borde, como en el diseño.
- **La pantalla de inicio** usa ya el botón común (antes tenía su propia copia del botón).

**Ronda 77 — las tarjetas de las tierras y el asistente:**

- **La tarjeta de una tierra** (`react/piezas/tarjeta.js`, entonces `tarjeta_de_tierra.js`): el **dibujo de la forma de la
  tierra**, su superficie, su pueblo, sus **avisos dentro de la tarjeta** (zona de nitratos, masa de agua
  cerca: datos que ya se saben, no suposiciones) y **la palabra «ELEGIDA»** con el círculo marcado en la
  que acaba de tocar. Con 51 tierras, una fila de texto no se distingue de la de al lado.
- **La barra de progreso por tramos** y el **«Paso 1 de 13»** en palabras, para saber cuánto queda.
- **La barra de botones pegada abajo** (`.asistente-acciones`): con una mano y de pie en el campo, el
  botón de SEGUIR tiene que estar donde llega el pulgar.
- **La captura** del paso de elegir la tierra se guarda en la carpeta temporal al comprobar en un
  navegador de verdad (`scripts/comprobar_en_un_navegador.py`).

**Ronda 78 — las tierras de «Mis parcelas, productos y máquinas» (`mis_tierras.png`):**

- **La lista de tierras de esa pantalla son tarjetas**, con el **rótulo de arriba** («Tierra n.º 1»),
  `el nombre`, `la superficie con su palabra`, `el pueblo` y los datos **con su nombre delante**
  (`Referencia oficial SIGPAC` y el código: un `37-70-0-0-503-51` suelto no dice qué es).
- **Lo que hay sembrado este año va dentro de la tarjeta**, en su fila (`Cultivo de este año`), y si le
  falta decirlo sale **en ámbar, dentro de la misma tarjeta**, con el pie que dice qué pasa al tocarla
  (`DECIR QUÉ HAY SEMBRADO` / `VER O CAMBIAR LO QUE HAY SEMBRADO`). Antes esa lista **no hacía nada**: era
  un muro de renglones iguales de los que no se podía sacar nada.
- **Cuántas tierras hay** se dice debajo del título de la sección («Tienes 1 tierra apuntada»): la lista se
  corta al final de la pantalla y sin eso no se sabe si están todas.
- **Las tarjetas de esta pantalla no eligen: abren.** Por eso van **sin el círculo** de elegir, que
  prometería una elección que ahí no existe.
- **Las otras seis secciones se quedan como estaban** (productos, abonos, quién aplica, quién asesora,
  máquinas y naves): son diez o doce cosas y se leen de un tirón. Una tarjeta por abono sería más ruido
  que ayuda, y el diseño no pide eso.
- **La captura de «mis cosas»** se guarda también al comprobar en un navegador de verdad.

**Ronda 79 — los apuntes de «Mi cuaderno», como fichas (`mi_cuaderno.png`):**

- **Cada apunte de producto es una ficha**: su número («Apunte 1»), su fecha y **cada dato con su nombre
  delante** —`Tierra y parcela`, `Hectáreas tratadas`, `Cuánto por hectárea`, `Cultivo` y `Hasta aquí no
  puedes coger la cosecha:` con su fecha—. Antes era un renglón con «TRIGO BLANDO · 4,90 ha · 0,80 L/ha»:
  tres datos seguidos, sin decir cuál era cuál y **sin la tierra donde se echó**, que es justo lo que se
  pregunta cuando llega una inspección.
- **`+ APUNTAR OTRO TRATAMIENTO` dentro del bloque**, con el mismo dibujo que en la pantalla de inicio.
  Antes, apuntar uno nuevo desde aquí obligaba a volver al inicio y buscarlo: en la pantalla que más se
  mira, dos pasos de más.
- **La pieza de la tarjeta cambia de nombre**: `react/piezas/tarjeta.js`. Sirve para tres cosas ya (elegir
  una tierra, mirar las tierras de la finca y leer los apuntes), y **con acción se pinta como botón y sin
  ella como un trozo de pantalla que se lee** (un apunte no se toca: un botón que no hace nada promete una
  salida y no la da).
- **La captura de «mi cuaderno»** ya se guardaba; ahora enseña las fichas de los apuntes.

**Ronda 80 — «mi cuaderno» de un vistazo, y lo que hay que enseñar al inspector:**

- **El bloque verde de la inspección.** «Sacar mi cuaderno para la Junta» pasa a ser un **bloque con fondo
  verde oscuro** —el único bloque oscuro de la aplicación—, con su explicación en blanco y el botón de
  sacar el cuaderno **a lo ancho y dentro del bloque**, y los otros dos debajo. Es lo único de esa pantalla
  que se hace **con alguien delante** (el inspector, en el campo, esperando): hay que encontrarlo sin leer
  nada. La lista de «lo que te falta para tenerlo completo» queda **fuera del verde**, en blanco, porque
  eso se lee con calma.
- **La frase de un vistazo**, debajo del título: «Te falta 1 cosa por apuntar», «Te faltan 3 cosas por
  apuntar» o «No te falta nada por apuntar». Es lo primero que se lee al abrir la pantalla que más se mira,
  y contesta a la pregunta con la que se abre: «¿tengo el cuaderno al día?». **Solo se dice si el servidor
  ha contestado** lo que falta: con la lista sin llegar, decir «no te falta nada» sería afirmar lo que no
  se sabe.

**Ronda 81 — el número de cada bloque, con su palabra:**

- **«2 ventas apuntadas · 44.000 kg»** y **«1 análisis guardado»**, cada uno en su línea destacada debajo
  del título del bloque, y **en singular cuando es uno** (eso ya estaba en los apuntes de producto).
  Antes el de las ventas decía «2 · 44.000 Kilos» —que ni dice qué se cuenta ni se lee bien: «Kilos» es un
  rótulo de campo y va en mayúscula— y el de los análisis, «1 · Dónde se aprovecha esto:», que es la
  explicación de para qué sirve un análisis puesta justo donde va el número.
- **La comprobación en un navegador de verdad ahora siembra una venta**, para que ese bloque se vea con su
  número y no con su frase de «todavía no has apuntado ninguna venta».

**Ronda 82 — el buscador de tierras (`mis_tierras.png`, «Buscar entre tus fincas»):**

- **En el paso de elegir la tierra**, donde de verdad se elige, hay un **buscador**: se escribe un trozo del
  nombre, del pueblo o del número del SIGPAC y la lista se queda con lo que casa. Con **51 tierras**, antes
  era recorrer cincuenta y una tarjetas con el pulgar para apuntar dónde se ha echado el producto.
- **No hace falta poner tildes** («penaranda» encuentra «Peñaranda de Bracamonte»), y el número del SIGPAC
  se puede escribir como salga: «503», «503-51» o «37 70 503» encuentran la misma tierra (los ceros sueltos
  de la referencia no distinguen nada).
- **Lo escrito no se borra al buscar** y hay **VERLAS TODAS** siempre a mano. Si la búsqueda no encuentra
  nada, se dice y el aviso lleva su botón: una lista vacía sin salida es un agricultor creyendo que ha
  perdido sus tierras.
- **El buscador se vacía al empezar un apunte nuevo**: un filtro que sobrevive sin verse es la forma más
  fácil de que alguien crea que le faltan tierras.
- **La comprobación en un navegador de verdad ahora siembra una segunda tierra** y recorre el buscador de
  verdad (escribir, pulsar BUSCAR) comprobando que la lista se filtra: es lo único que no se puede ver en un
  DOM de mentira, porque ahí el campo que pinta React no existe.

**Ronda 83 — la ayuda, cada cosa con su nombre:**

- **Los seis puntos de la ley** («Llevar el cuaderno al día», «Mandar los datos a la Junta», «Con un programa
  tuyo», «Las fechas que importan», «Cuándo será obligatorio del todo» y «Lo que todavía no está aclarado»)
  salen **cada uno con su título**. Antes eran seis párrafos largos seguidos bajo un solo rótulo: no se sabía
  dónde acababa uno y empezaba el siguiente, y para encontrar «lo de mandarlo a la Junta» había que leerlos
  todos.
- **Los diez porqués** («Para qué sirve el cuaderno», «En papel o en el móvil», «Qué pasa si no lo llevo»…),
  igual: **cada uno con su nombre**. Eran párrafos seguidos, sin caja ni título, en la pantalla a la que va
  quien no entiende algo.
- **Los saltos de línea del texto se respetan** (`.apunte-detalle` con `white-space: pre-line`): el porqué del
  cuaderno explica «sirve para tres cosas» y las enumera, y los tres motivos salían seguidos en un párrafo
  corrido.
- **Dos pruebas nuevas** en `test_sin_jerga.py` que impiden que el siguiente porqué o el siguiente punto de
  la ley llegue **sin nombre** (y que el título no sea el rótulo del apartado repetido), más otra que exige
  que los títulos sean títulos y no párrafos.

**Ronda 84 — los números, en singular cuando son uno:**

- **`«A 1 parcelas les falta decir qué tienen este año»` → `«A 1 parcela le falta decir qué tiene este año»`**,
  en «qué hay sembrado».
- **`«Tienes 1 productos apuntados»` → `«Tienes 1 producto apuntado»`**, en «lo que tengo en el almacén»… y
  esa frase **no la enseñaba nadie**: el servidor la calculaba y la mandaba, y la pantalla no la leía. Ahora
  va en su línea destacada, como el número de las tierras y el de los apuntes del cuaderno.
- **`«Tienes 1 papeles guardados»` → `«Tienes 1 papel guardado»`**, en «los papeles».
- **`«1 cosas apuntadas esperando a que haya cobertura»` → `«1 apunte esperando a que haya cobertura»`**, en
  el aviso de la cabecera: el que sale justo cuando el agricultor está en el campo sin cobertura.
- **`«1 hojas de 25 llevan datos tuyos»` → `«1 hoja de 25 lleva datos tuyos»`**, en el bloque verde de la
  inspección de «mi cuaderno».
- **Un ayudante para no repetirlo** (`con_cuenta`, en `textos.py`, y su gemelo `conCuenta` en `nucleo.js`
  para los textos que compone la interfaz): el singular se escribe al lado del plural (`_uno`) y se elige con
  el número. **Dos pruebas nuevas** (`TestSingularYPlural`) exigen que los textos de cuenta tengan las dos
  formas, y otras dos comprueban que la frase sale entera en singular y en plural, contra la API de verdad
  (los papeles).

**Ronda 85 — los números del plan de abono, y la flecha donde toca:**

- **La tabla del plan de abono** («Tenías previsto · Llevas · Te queda») salía con **tres números y solo dos
  rótulos**: el tercero había que adivinarlo. Ahora la cabecera nombra los tres, y cuando alguien se ha
  pasado, en el tercer sitio no va un número sino la palabra **«Pasado»** —un texto del servidor que existía
  y no usaba nadie—. Antes iba un ⚠️ suelto: un dato sin nombre no se puede leer.
- **«Lo hice: Sí» → «Lo hice con una herramienta: Sí»**, en el detalle del plan: el rótulo no decía el qué
  (la pregunta del asistente es «¿Has usado un programa o una herramienta para hacerlo?»).
- **Los botones de las medidas preventivas pierden la flecha.** En esta aplicación la flecha significa «esto
  te lleva a otro sitio», y esos botones **marcan y desmarcan una cosa en la misma pantalla**: mentían. Lo
  que dice que se marca es el cuadro del icono (✅ / ⬜). Los tres botones de abajo (GUARDAR, NINGUNA,
  VOLVER) siguen llevándola, porque esos sí salen de la pantalla.

**Ronda 86 — las ventas, cada dato con su nombre:**

- **La ficha de una venta** deja de ser una línea corrida —«42.000,00 kg · Venta a comprador · Cooperativa
  Agrícola de Peñaranda · Partida L-2026-07 · Albarán ALB-2026-118 · El Prado»— y pasa a tener **cada dato en
  su fila con su rótulo**: `Cuánto`, `Cómo lo vendiste`, `A quién`, `Partida`, `Albarán` y `De dónde`. El
  comprador se adivinaba por el contexto, pero «L-2026-07» y «ALB-2026-118» no dicen qué son. Los rótulos ya
  estaban escritos en `textos.py` —son los de la tabla de la Junta— y solo se usaban dos.
- **La pantalla «Lo que he vendido» entra en la comprobación de un navegador de verdad** (no estaba), con la
  venta de la prueba: es lo único que garantiza que los datos llegan hasta la ficha que se dibuja.
- **El bloque de «mi cuaderno» sigue con la línea corta**, a propósito: enseña cuatro ventas de un tirón y con
  seis filas cada una no cabría. La ficha con nombre está a un toque, en su pantalla.

**Ronda 87 — el buscador de tierras también en «mis cosas»:**

- **El buscador que pide el diseño** («Buscar entre tus fincas», en la pantalla de tierras) está ya en las
  dos pantallas donde hay tierras: en el paso del asistente, donde se elige una (ronda 82), y ahora en «Mis
  parcelas, productos y máquinas», que es donde el diseño lo dibuja.
- **El número de la tierra no cambia al buscar**: la que es «Tierra n.º 2» en la lista entera sigue siéndolo
  cuando sale sola. Renumerarla al buscar sería mentirle: es como la llama el agricultor.
- **Un filtro por pantalla, y a propósito**: el del asistente y el de «mis cosas» son dos. Con uno solo,
  buscar «prado» al apuntar un tratamiento dejaría «mis cosas» enseñando una tierra de las 51 sin que nadie
  lo hubiera pedido allí (y su cuenta de arriba seguiría diciendo 51).
- **Si no casa ninguna se dice**, con el aviso y su botón para volver a verlas todas. El aviso de «todavía
  no tienes parcelas» sería mentira —las tiene— y sin salida un filtro es una lista de tierras que ha
  desaparecido.
- **La comprobación en un navegador de verdad recorre también este buscador** (escribir «suertes» y
  comprobar que la otra tierra desaparece), con su propio campo y su propio filtro.

**Ronda 88 — la pantalla del SIGPAC, sin lo que sobra:**

- **Sin barra de progreso y sin «Paso 1 de 1».** Traer una tierra del SIGPAC es un asistente de **un solo
  paso**: una barra llena y un «Paso 1 de 1» no cuentan nada y empujaban hacia abajo lo que sí importa. La
  barra sigue saliendo en los asistentes de verdad (trece pasos para apuntar un tratamiento).
- **La explicación de la referencia sale una vez, no dos.** El paso llevaba como pista el mismo texto que la
  casilla de la referencia («Pega lo que tengas: la del visor…, los siete números del papel…, la referencia
  catastral…»), así que la pantalla lo decía **dos veces**: arriba y debajo de la casilla. Ahora arriba va lo
  que explica la pantalla entera («Si tienes la referencia del trozo, el programa trae solo la superficie…»,
  el texto del SIGPAC que ya existía) y debajo de la casilla queda la explicación de la casilla.

**Ronda 90 — Stitch para TODO, pantalla por pantalla (lo que pidió David):**

David lo pidió así: *«usa mucho más Stitch, para cualquier diseño, para cualquier mínima cosa, hazle caso
en las ideas, no pares hasta tener toda la app cubierta con todas las funcionalidades y ui refactorizadas y
perfectas»*. Hasta esta ronda, de las 28 pantallas solo **cuatro** tenían diseño propio: las demás se habían
ido mejorando con las ideas que Stitch dio para aquellas cuatro. Lo que se ha hecho aquí es cambiar eso:

1. **La lista de trabajo, escrita**: [`docs/stitch/LO_QUE_FALTA_POR_DISENAR.md`](../LO_QUE_FALTA_POR_DISENAR.md)
   tiene **todas** las pantallas y **todas** las piezas, con cuáles tienen diseño y cuáles no. Esa lista es
   la que manda hasta que no quede nada sin diseñar.
2. **Los encargos, escritos** en `backend/scripts/disenar_con_stitch.py`: se han añadido **veinticinco**
   encargos (las 24 pantallas que no tenían diseño + una lámina con las piezas que se repiten en todas), con
   **el texto real de `textos.py`** y las reglas del campo. Cada uno dice qué tiene que resolver esa pantalla
   y qué tiene que verse de un vistazo, no cómo tiene que ser por dentro.
3. **Se le piden a Stitch** con el proyecto `4347842392867690825` y nuestro sistema de diseño, y las capturas
   se guardan aquí mismo (`<clave>.png`, `<clave>_grande.png`, `<clave>.html`, `<clave>_explicacion.md`).
4. **El guion aguanta una tanda larga**: `--nuevas` pide solo lo que no tiene diseño pedido (así se puede
   retomar sin duplicar nada) y **una pantalla que falle no para las demás** (en la primera tanda, «la ayuda»
   se cortó a mitad y el guion se paró entero dejando veintiuna sin pedir; se arregló en el mismo cambio).

**Lo aplicado en esta ronda, con su diseño mirado** (cada uno con su captura en esta carpeta y sus pruebas):

- **«Lo que tengo en el almacén»** (`cesta.png`): **cada producto lleva su etiqueta de estado** —«Las cuentas
  cuadran», «Sin saber cuánto compraste», «No se puede comparar», «Míralo»— porque con la lista llena lo
  primero que se busca es **cuál hay que mirar**, y eso no se saca de tres números sueltos; **«Te queda» cierra
  la tarjeta, en su recuadro y con el número grande** (es la pregunta con la que se entra ahí, y estaba en
  medio y del mismo tamaño que «Compraste»); y **el motivo de por qué no se puede restar va en su franja de
  aviso**, no como un párrafo suelto.
  - Y una cosa que se arregló de paso: **la fila de «Te queda» ahora sale siempre**, también cuando no se sabe
    (con un guion y su motivo debajo). Antes no salía, y el agricultor veía la tarjeta sin la fila que había
    ido a buscar.
- **«Los análisis»** (`analiticas.png`): **la edad del boletín en su etiqueta** —«De este año (2026)», «Hace 2
  años (2024)»—, al lado del nombre: un boletín viejo no vale lo mismo que uno de este año y eso había que
  leerlo; **los números del boletín en su bloque y en dos columnas**, con el número grande (ocho o nueve
  números en renglones había que leerlos uno a uno); y **el papel del laboratorio con lo que hay que hacer al
  lado**: sin papel, la frase va en su franja de aviso y **el botón de subirlo es el de color de acción**,
  porque es lo único que le falta a ese análisis.
- **«La ayuda»** (`ayuda.png`): **los dos puntos de la ley que contestan sí o no llevan su etiqueta** —«Sí es
  obligatorio» y «Es voluntario»—. Es la primera pregunta de quien empieza («¿yo esto tengo que mandarlo?») y
  ahora se contesta sin leer el párrafo. Los otros cuatro puntos no son obligación ni voluntad —son
  explicaciones— y por eso no llevan etiqueta.
- **«Qué hay sembrado»** (`cultivos.png`): **cada tierra lleva su etiqueta de estado** («Al día» / «Falta
  rellenar»): con más de cincuenta tierras, lo que se viene a buscar aquí es a cuáles les falta decirlo; **a la
  que le falta, se le dice en su franja de aviso y su botón es el grande** (es lo único que le falta); y **el
  aviso de que repites el cultivo del año pasado pasa a su franja**, dentro de la tarjeta, como los avisos de
  una tierra.
- **«La revisión de lo dictado»** (`borrador.png`): **lo que has dicho, entero y arriba** («Has dicho: …»). Lo
  único que veía el agricultor eran los datos ya colocados: si el programa oyó mal una palabra, no tenía con
  qué compararlo, y es él el único que puede darse cuenta. Y **lo que falta para poder apuntarlo va en su caja
  de aviso**, porque es lo que impide terminar.
- **«Traer las tierras del cuaderno de la Junta»** (`cuaderno_de_la_junta.png`): **la barra de las tres fases**
  (elegir el fichero, mirar el resumen, ver el resultado), porque son tres pantallas en una y sin una señal de
  dónde estás la impresión es que no se acaba nunca; y **el aviso de que leer el fichero no apunta nada**,
  justo antes del botón: es la duda que tiene el agricultor con el dedo encima.
- **«Los papeles»** (`documentos.png`): **el botón de guardar un papel, también arriba** (con diez papeles
  guardados, el de abajo queda a dos pantallas de scroll y guardar es a lo que se entra); y **al papel al que le
  falta el fichero se le dice en su franja y su botón de subirlo es el grande**, mientras que uno con fichero se
  descarga con un botón claro.
- **«Dímelo con la voz»** (`dictado.png`): **el botón de HABLAR va primero y el recuadro de lo escrito debajo**
  (hablar es la acción principal, no un plan B: antes el recuadro iba arriba y se leía como un formulario), y
  se dice que **lo escrito se puede corregir con el dedo**.
- **La confirmación de «apuntado»** (`hecho.png` y la lámina de piezas): **la ficha de lo que se acaba de
  apuntar** —la tierra y la fecha— debajo del «Apuntado»: la pantalla decía «Apuntado» y nada más, así que el
  agricultor no podía comprobar que se había entendido lo que él quería apuntar. **El plazo de espera en su
  franja de aviso**, porque es el dato que puede costarle la cosecha y estaba en un párrafo suelto del mismo
  aspecto que el resto; y **los botones en el orden del diseño**: primero el de volver al inicio —el que se
  pulsa el 99 % de las veces— y debajo el de deshacer, **con su explicación** («por si te has confundido de
  tierra, producto o dosis»). Antes el botón que puede borrar un apunte era el primero que encontraba el dedo.
- **«Mis datos»** (`mis_datos.png`): **los once campos van numerados** (el número lo pone el CSS con un
  contador, así que el rótulo sigue siendo el del servidor), porque es un formulario largo y sin números no se
  sabe cuánto queda; y **el botón de «quién entra en mi finca» lleva su explicación** debajo («Añadir otra
  cuenta que apunte en tu finca»), que sin ella no se sabe qué hay dentro.
- **«Lo que hago sin echar producto»** (`medidas.png`): **las diez medidas van numeradas** y las que están
  marcadas lo dicen **con palabras** («Hecho en mi finca»), además del visto y del color: es la regla del
  proyecto de no informar solo con el color, y aquí lo que está en juego es una obligación.
- **«Mis facturas»** (`facturas.png`): **cada factura dice si tiene su papel** —«Foto del papel guardada» o la
  franja de aviso de que no lo tiene— con su botón: **VER LA FACTURA** o **SUBIR LA FOTO DEL PAPEL**. Y esto
  no era solo estética: el servidor sabía desde la ronda 40 si la factura tenía su papel (`tiene_fichero`) y
  los dos caminos (`GET` y `POST /api/facturas/{id}/fichero`), y **el texto del botón estaba escrito sin
  puerta**: ninguna pantalla lo pedía, así que una factura escrita a mano se quedaba sin papel para siempre
  —y el papel es justo lo que se pide en una inspección—. También lleva la cuenta de cuántas hay
  («1 factura guardada»), como las demás listas.
- **«El plan de abono del año»** (`planes.png`): **cada plan lleva su veredicto en una etiqueta** —«En regla»
  o «Alerta: exceso»—, que es la primera pregunta al abrir esto («¿voy bien?») y antes había que leerse la
  tabla entera; y **el aviso de cuándo es obligatorio** el plan, arriba y en su franja. Ese texto llevaba
  **desde la ronda 60 en el vocabulario sin que lo leyera ninguna pantalla**: es lo que contesta a «¿esto me
  hace falta?».
- **«Quién entra en mi finca»** (`quien_entra.png`): **cada finca dice sus hectáreas** (el servidor las
  cuenta: la suma de las tierras de esa finca), porque al elegir en cuál trabajas el tamaño es lo que
  distingue una finca de otra cuando se llaman parecido; **la finca en la que ya estás lo dice con palabras**
  («Estás trabajando aquí ahora») en vez de quedarse sin botón y sin explicación; **se dice qué puede hacer
  quien ayuda** («Puede apuntar lo que se haga en la finca con su propio móvil. No puede decidir quién entra
  ni quitar cuentas»), que es lo que hace de verdad el servidor; y el botón de quitar el acceso va **en rojo**
  (`boton-peligro`), que es lo que es.
- **«Lo que he vendido»** (`ventas.png`): **la fecha en su renglón y el producto debajo en grande** (antes
  iban los dos seguidos en la misma línea: así la ficha se lee por partes, cuándo y qué); y **la cuenta de
  cuántas van y cuánto ha salido de la finca** («2 ventas apuntadas · 44.000 kg»), que es la misma línea que
  lleva el bloque de «mi cuaderno» desde la ronda 81 y aquí no estaba.
- **«Parcelas que se llevan igual»** (`grupos.png`): **las tierras de cada grupo, una por línea y con sus
  hectáreas** (antes era una línea con los nombres separados por puntos: «El Prado · La Vega · El Alto», y con
  seis tierras no se sabía ni cuál era cuál ni cuánto tenía cada una); y **la etiqueta que dice de quién es el
  grupo** («Lo juntó el programa.» / «Juntado por ti.»), que es lo que dice si puede cambiarlo.
- **«Decir qué hay sembrado»** (`decir_cultivo.png`): **las cinco preguntas numeradas** (el número lo pone el
  CSS con un contador, como en «mis datos» y en las medidas) y, sobre la primera, **la etiqueta «Hace falta»**;
  y **el aviso de arriba** que quita el miedo al formulario: «Rellena lo que sepas y pulsa GUARDAR. Lo único
  que hace falta de verdad es el cultivo: lo demás, si no estás seguro, déjalo en blanco.»
- **«Guardar un papel»** (`nuevo_documento.png`): **los seis campos numerados**, la etiqueta **«Hace falta»**
  en el nombre (que es lo único obligatorio), **las carpetas que ya tiene para tocarlas** en vez de
  escribirlas (en el móvil, y con guantes, escribir el nombre de la carpeta es lo que más cuesta) y **el papel
  se sube en la misma pantalla**. Esto último no era estética: antes había que guardar el papel, ir a la lista
  y subir la foto desde allí, y el camino de subirla con el papel recién creado ya existía en el servidor
  (`POST /api/documentos/{id}/fichero`). Si la subida falla, el papel **ya está apuntado** y se dice: perder el
  apunte por un fichero que falla sería lo peor que puede pasar aquí.
  - Lo que **no** se ha aplicado del diseño, con su motivo: la barra verde de arriba («LO QUE VA AL
    ARCHIVADOR») que enseña el papel mientras se escribe. Sería un resumen **vivo**, y eso pide que la pantalla
    guarde el estado de los campos; aquí los campos los lee `app.js` por su `id` (formularios no controlados,
    la decisión que sostiene toda la aplicación). Se apunta como idea, no se hace a medias.
- **«Firmar el cuaderno»** (`firmar.png`): **el estado de la firma, en su etiqueta** —«Todavía no has firmado
  el cuaderno de este año» o «Ojo: este cuaderno se firmó el 15/03/2026, pero después se ha cambiado algo»— y
  **el aviso de que sin certificado no se puede firmar**. La pantalla solo enseñaba los tres pasos: **el
  estado no se veía en ninguna parte** (ni que ya estuviera firmado, ni que la firma se hubiera quedado
  vieja), y el texto del aviso del certificado estaba escrito desde siempre sin que lo leyera nadie.
- **«Añadir una factura»** (`nueva_factura.png`): **el fichero es una caja grande que se toca entera** —lo que
  se viene a hacer aquí es darle el papel al programa, y un campo de fichero pelado no se ve como algo que se
  toca—, y **el trato claro**: «El programa solo intenta leer el papel. Nada se guarda en el cuaderno hasta que
  tú lo mires en pantalla y digas que está bien.» El campo sigue siendo el mismo, con su `id` (es como lo lee
  `app.js`), oculto dentro de la etiqueta.
- **«Esto es lo que he leído»** (`interpretacion_factura.png`): **la línea cuya cuenta no cuadra lleva su
  etiqueta arriba** («Revisar números») y el aviso va en su franja, con su señal. Con tres o cuatro líneas, el
  aviso del final no dice cuál es sin leer la pantalla entera.
- **«Traer la tierra del SIGPAC»** (`traer_del_sigpac.png`): **el camino rápido va primero**. Pegar la
  referencia ahorra teclear seis datos y estaba **abajo del todo, después de los seis campos que ahorra**: ahora
  hay dos caminos con su nombre («El camino rápido» y «O si lo prefieres: buscar por partes») y los seis datos
  del camino largo van numerados. Se deja **un solo botón** de buscar, y no dos como el diseño: los dos caminos
  hacen la misma búsqueda, y el programa ya sabe cuál usar por lo que esté relleno.
- **«Buscar mi tierra en el mapa»** (`mapa.png`): **la confirmación de que el SIGPAC ha contestado**, con su
  recordatorio: «Comprobado en el SIGPAC: hay una parcela bajo la cruz. Mira abajo si los datos coinciden con tu
  papel.» Lo que garantiza que se apunta la tierra que es, es que él compare los datos con su papel.
- **«Entrar»** (`entrar.png`): **revisada y sin cambios**. El diseño enseña lo que ya hace: el título, la
  explicación de para qué sirve (el texto de los porqués), los campos con su pista, el botón grande de entrar,
  el del certificado **después** del de correo y clave, y el botón para pasar al otro camino. Lo único que
  propone de más es un rótulo («CAMINO RÁPIDO») sobre el camino de entrar, y en esta pantalla solo hay dos
  caminos y el botón de abajo ya dice cuál es cuál.
- **La lámina de piezas** (`piezas.png`): **revisada pieza por pieza** contra lo que hay. La tarjeta de una
  tierra (con sus avisos dentro y la palabra «ELEGIDA»), la lista de botones para elegir, el campo con su ayuda
  de cuatro rótulos, los tres avisos (normal, de error y el de lo que está esperando a mandarse), la barra de
  botones del asistente y el estado vacío **ya estaban** como los dibuja la lámina. Y de la pieza del
  **bloque de apuntado** salió lo único que faltaba y que se ha aplicado: **la confirmación no enseñaba lo que
  se acababa de apuntar**. Ahora lleva su ficha —la tierra y la fecha— debajo del «Apuntado», que es lo que
  permite comprobar que se ha entendido lo que él quería apuntar.

**Los veinticinco encargos están pedidos a Stitch** y las capturas van llegando a esta carpeta con su `_grande`,
su `.html` y su `_explicacion.md`. Lo que queda por aplicar, pantalla por pantalla, se apunta en
[`LO_QUE_FALTA_POR_DISENAR.md`](../LO_QUE_FALTA_POR_DISENAR.md), que es la lista viva.

**Lo que el diseño de esta ronda pedía y NO se ha aplicado, con el motivo:**

5. **El bloque verde oscuro para el «¿para qué sirve esto?» del almacén**: el diseño lo dibuja en verde oscuro,
   y la ronda 80 decidió que **el bloque oscuro es el de la inspección** («Sacar mi cuaderno para la Junta»),
   el único bloque oscuro de la aplicación, porque es lo único que se hace **con alguien delante**. Un segundo
   bloque oscuro para una explicación le quitaría a aquel lo que lo hace útil.
6. **Las explicaciones de la ayuda que se abren al pulsarlas** («Pulsa en cada tema para entender por qué te
   ayuda»): aquí el agricultor va justo a leer eso. Esconder el contenido detrás de un toque añade un paso y
   una cosa que aprender en la pantalla que se abre precisamente cuando no se entiende algo. Lo que sí se
   abre son **las cuatro tablas largas del final** (dosis de nitrógeno y periodos), que es lo que ya hacía.
7. **«Ver entradas y salidas de este producto»** (un botón dentro de la tarjeta del almacén, en el diseño):
   eso **sería una pantalla nueva**, con su acceso, sus pruebas y su sitio en la caché del campo. Queda
   apuntado en `LO_QUE_FALTA_POR_DISENAR.md` como propuesta; hoy el producto se mira en su ficha («Mis cosas»)
   y sus apuntes, en «mi cuaderno».
8. **«Te llega para unas N hectáreas»** (el diseño lo calcula con el gasto medio de los apuntes): es una
   cuenta que hoy **no hace el servidor**, y hacerla con datos de mentira en la pantalla sería justo lo que
   este proyecto no hace. Queda apuntado como propuesta para el servidor.

## Qué queda por aplicar, y por qué (cerrado en la ronda 88)

Esta tabla era la lista de lo que faltaba para el rediseño de la ronda 76. **Ya está cerrada** (ronda 88):
cada punto está hecho o decidido, con su motivo. Lo que sigue son las decisiones, no una lista de tareas
pendientes. **Lo que falta del diseño nuevo —las veinticinco pantallas y piezas de la ronda 90— está en
[`LO_QUE_FALTA_POR_DISENAR.md`](../LO_QUE_FALTA_POR_DISENAR.md)**, que es la lista viva.

| Del diseño | Qué ha pasado |
|---|---|
| **Las tarjetas de tierras** en las demás listas (los análisis, el plan) | **Hecho**: las listas donde se elige una tierra usan la tarjeta desde la ronda 77 (el asistente, con sus tres pasos: tratamiento, venta y análisis) y desde la 78 («mis cosas») |
| **El buscador «Buscar entre tus fincas»** de la pantalla de tierras | **Hecho en las dos pantallas de tierras** (el paso de elegir la tierra, ronda 82; «Mis parcelas, productos y máquinas», ronda 87) |
| **Las tarjetas de productos, máquinas y naves** | **No se hacen, y se dice por qué**: al ir a hacerlas se comprobó que **el dato que hace falta para elegir ya está en el botón** —el número de la etiqueta y los días de espera en los productos, los tres números del abono en los abonos— y que esas cosas **no tienen forma que dibujar**, que es lo que hace útil la tarjeta de una tierra (51 tierras y todas iguales de color) |
| **Los demás bloques de «mi cuaderno»** (lo que falta, las medidas, el plan y la firma) | **Hechos**: los apuntes (ronda 79), el bloque de la inspección y la frase de un vistazo (ronda 80), los números de cada bloque (ronda 81) y los del plan (ronda 85) |
| **La cabecera** («CUE Digital» y la pastilla de la letra) | **La pastilla de la letra ya estaba** («A+», en la cabecera de siempre). El nombre «CUE Digital» no se pone: la cabecera dice **«Mi cuaderno»**, que es como llama David a esto |
| **El aviso de la campaña** en la cabecera («Campaña 2026») | **No se aplica**: el diseño lo dibuja en una cabecera que lleva el título de la pantalla debajo; aquí el título vive dentro de cada pantalla y el año ya se ve donde importa (el inicio, «Hola · 2026», y cada bloque que es de la campaña). La cabecera es lo único que se ve siempre, y repetir ahí un dato que ya está en pantalla es gastar el sitio más valioso |
| **La franja «Guardado en este teléfono…»** del asistente | **No se aplica**: el aviso de lo que está pendiente de mandar **ya existe** y sale en la cabecera de toda la aplicación (`#aviso-pendientes`, con su texto en singular y en plural desde la ronda 84). Añadir otra franja dentro del asistente sería decir lo mismo dos veces |
| **La ayuda al final de la lista de tierras** («¿no encuentras una tierra o el SIGPAC está mal?») | **No se aplica**: la frase tiene que decir **a quién se llama y con qué número**, y ese dato no lo tenemos. Escribir un teléfono inventado en la pantalla de un agricultor es lo que este proyecto no hace |
| **La barra de pestañas de abajo** (Cuaderno / Parcelas / Historial / Ajustes) | **No se aplica**: el proyecto tiene la regla de no meter menús que haya que aprender. Todo lo que hace falta está en la pantalla de inicio, y una barra de pestañas añadiría pantallas nuevas que hoy no existen |

**Y el resumen de todo el rediseño, en una página, está en
[`docs/MEJORAR_LA_INTERFAZ_CON_STITCH.md`](../../MEJORAR_LA_INTERFAZ_CON_STITCH.md)**: qué se pidió, qué se
aplicó ronda a ronda, qué no y por qué, y los comandos para comprobarlo.
