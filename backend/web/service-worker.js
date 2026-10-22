/*
 * service-worker.js — Guarda la propia aplicación en el móvil para que se pueda
 * abrir SIN COBERTURA. Sin esto, el agricultor llega al campo, abre la página y se
 * encuentra un error del navegador: la página no carga, aunque sus datos estén.
 *
 * Decisión: aquí SOLO se guardan los ficheros de la aplicación (HTML, CSS, JS).
 * Las llamadas a /api/ NUNCA se guardan: son datos del agricultor, llevan su
 * identificación y tienen que ir siempre al servidor. Lo que se apunta sin cobertura
 * lo guarda `app.js` aparte, y eso ya está probado.
 *
 * Si el navegador no deja registrarlo (pasa cuando se entra por HTTP en vez de
 * HTTPS, salvo en localhost) la aplicación funciona igual: solo se pierde poder
 * abrirla sin cobertura. Por eso el registro falla en silencio.
 */

// El nombre lleva la fecha y un número: al cambiarlo, el navegador se guarda la versión nueva
// y borra la vieja. **Hay que subirlo siempre que se añada o cambie un fichero de la lista**,
// porque si no, un agricultor que abra la aplicación sin cobertura después de un despliegue se
// queda con los ficheros viejos. Por eso, al meter React, se subió el nombre en el mismo
// cambio: sin eso, el móvil tendría el `app.js` nuevo (que pide React) y la caché sin los
// ficheros de React, o sea una pantalla en blanco en el campo.
//
// Ronda 46: se subió otra vez, y esta vez la lista no cambió de tamaño: lo que cambió fue el
// CONTENIDO de dos ficheros que sí están en la lista (`app.js` y `nucleo.js`). Sin subir el
// número, el móvil de David seguiría con el `app.js` viejo, seguiría leyendo que su cuaderno
// está vacío y no tendría el atajo de repetir.
//
// Ronda 47: la lista crece con «los análisis». Es el caso de manual: si el `app.js` nuevo llega
// sin `/react/pantallas/analiticas.js` en la caché, el agricultor abre esa pantalla en el campo
// y se encuentra un hueco.
//
// Ronda 48: lo mismo con «dímelo con la voz», que además es la pantalla que se abre **en el
// campo**, con las manos ocupadas: es la que menos puede permitirse un hueco.
//
// Ronda 49: entra la revisión de lo dictado. Va con la anterior: sin las dos, el agricultor dicta
// en el campo, se queda sin cobertura y no puede ni revisar lo que ha dicho.
//
// Ronda 50: entra el formulario de guardar un papel, con sus seis campos.
//
// Ronda 53: entra la pantalla de firmar el cuaderno, que es la que se usa al final del año.
//
// Ronda 54: entra el plan de abono, que se consulta desde el campo tanto como desde casa.
//
// Ronda 55: entra la pantalla de entrar, que es la primera que se ve. Sin ella en la caché, quien
// abriera la aplicación sin cobertura se quedaría sin poder entrar.
//
// Ronda 56: entran las facturas (la lista y el alta). El agricultor mira sus facturas también desde
// el almacén, muchas veces sin cobertura.
//
// Ronda 57: entra la interpretación de una factura leída, que es la que confirma el agricultor.
//
// Ronda 58: entra el mapa del SIGPAC. Ojo con esta: **se toca con el dedo**, así que si falta en la
// caché el agricultor se queda mirando un mapa que no responde.
//
// Ronda 59: entra el formulario de decir qué hay sembrado, que es donde se contesta el aviso de que
// a una tierra le falta el cultivo.
//
// Ronda 61: entra traer las tierras del cuaderno de la Junta. Esta se usa **una vez** (cuando se
// empieza), y justo por eso conviene que esté en la caché: es lo primero que hace alguien nuevo.
//
// Ronda 62: entra la lista de botones del asistente (la tierra, la nave, el producto, el trabajo que
// se ha hecho). Es la pantalla que más se ve del asistente y la que se abre **en el campo**, con las
// manos ocupadas: si no estuviera guardada, el asistente no arrancaría sin cobertura.
//
// Ronda 63: entra el campo del asistente y su ayuda (la fecha, las hectáreas, la dosis). Son los pasos
// donde el agricultor **escribe**, y sin ellos el asistente se queda a medias en cuanto se sale de
// cobertura.
//
// Ronda 64: entra el grupo de campos del maestro (la ficha de un producto, de una máquina, de un asesor
// y los números del plan de abono). Son veinte pasos del asistente, los que más se usan.
//
// Ronda 65: no entra ningún fichero nuevo, pero **cambian los que ya estaban** (la lista de elegir sabe
// llevar su ayuda, el campo sabe no pintar una etiqueta vacía y el asistente tiene ocho pasos más en
// React). El número se sube igual: con la caché vieja, un móvil sin cobertura seguiría con las piezas de
// antes.
//
// Ronda 66: tampoco entra ningún fichero, y el asistente se queda en **62 de 65 pasos** en React (los
// tres resúmenes, los números del boletín y los pasos que mezclan dos cosas). Se sube el número por lo
// mismo: `app.js` y las piezas han cambiado.
//
// Ronda 67: el asistente se queda en **64 de 65** (solo falta el paso que trae la tierra del SIGPAC, que
// es una pantalla entera). El campo aprende a pedir números enteros, ejemplos dentro de la casilla y la
// ayuda encima, que es lo que necesitaba la pantalla de «cómo se echó».
//
// Ronda 68: entra **traer la tierra del SIGPAC**, que es la pantalla de buscar el recinto oficial dentro
// del asistente de dar de alta una tierra. Con ella el asistente se queda **entero en React** (65 de 65
// pasos): es la pantalla que ahorra más trabajo de todas, y se abre desde el campo.
//
// Ronda 69: entra la **confirmación**, la pieza con la que se pasaron de una vez las cinco pantallas de
// «guardado» (venta, análisis, plan, medidas y ficha de un maestro) y las que ofrecen un camino (traer la
// tierra del SIGPAC, el listado de papeles y las tierras traídas).
//
// Ronda 70: entra **«mi cuaderno»**, que es LA pantalla: la que más se mira y la que se abre en el
// almacén y en el campo. Con ella, todo lo que el agricultor ve de su cuaderno está en React.
//
// Ronda 71: no entra ningún fichero nuevo, pero cambian los que ya estaban (`app.js` deja de pintar los
// avisos de error a mano). Se sube el número por lo mismo de siempre: sin eso, un móvil sin cobertura
// seguiría con el `app.js` viejo.
//
// Ronda 72: entra **el asistente**, que es la pantalla que MÁS se usa de la aplicación (echar producto,
// abonar, sembrar, regar, coger la cosecha…) y **la que se abre en el campo, con las manos ocupadas**.
// Con ella la aplicación entera es React: no queda ni un `innerHTML` de pantallas.
//
// Ronda 76: entra **el rediseño de Stitch**. No hay fichero nuevo de pantallas (los iconos dibujados van
// dentro de `componentes.js`, que ya estaba en la lista), pero cambian los que ya había, así que se sube
// el número igual: con la caché vieja, un móvil sin cobertura seguiría con el aspecto de antes.
//
// Ronda 77: entra **la tarjeta de una tierra** (`react/piezas/tarjeta_de_tierra.js`), la pieza con la que
// se elige la tierra en el asistente. Es la lista que más se usa del año y **se abre en el campo**: si
// faltara en la caché, sin cobertura no se podría decir dónde se ha echado el producto.
//
// Rondas 78 y 79: la tarjeta sirve para tres cosas (elegir una tierra, mirar las tierras de la finca y
// leer los apuntes del cuaderno), así que **cambia de nombre**: `react/piezas/tarjeta.js`. El fichero
// viejo se quita de la lista y entra el nuevo: dejar el que ya no existe haría que la caché pidiera un
// fichero que no está (y `cache.add` lo daría por bueno con un 404 dentro).
//
// Ronda 89: entra **«quién entra en mi finca»** (`react/pantallas/quien_entra.js`), la pantalla con la que
// se le da acceso a otra cuenta y se cambia de finca. Se abre en casa y con calma, no en el campo, pero se
// guarda igual: la aplicación entera tiene que abrirse sin cobertura, y una pantalla que falta en la caché
// es un hueco que solo se nota cuando ya no hay red.
//
// Ronda 90: no entra ningún fichero nuevo, pero cambian todos los de las pantallas (el rediseño con Stitch,
// pantalla por pantalla). Se sube el número igual: con la caché vieja, un móvil sin cobertura seguiría con
// el aspecto de antes.
//
// Ronda 91: **corregir y borrar lo que uno ha introducido**. Tampoco entra ningún fichero nuevo —lo que
// cambia está en `app.js`, `nucleo.js`, `mi_cuaderno.js`, `hecho.js` y `estilos.css`, que ya estaban en la
// lista—, y se sube el número por lo de siempre: sin eso, el móvil de David seguiría con el `app.js` de
// antes y su cuaderno no tendría ni los botones de CORREGIR y BORRAR ni la lista de abonos y trabajos.
//
// Ronda 92: lo mismo para las **tierras y los grupos**, y con la misma cuenta: no hay fichero nuevo
// (`app.js`, `mis_cosas.js`, `grupos.js`, `asistente.js` y `resumen_del_apunte.js` ya estaban en la
// lista), pero cambian todos. Un móvil sin cobertura con la caché vieja no tendría los botones de
// CORREGIR y BORRAR de cada tierra.
//
// Ronda 93: entra **una pieza nueva**, `react/piezas/acciones_de_una_ficha.js`, que es la barra con
// CORREGIR y BORRAR que llevan ya todas las listas (las tierras, los grupos, los apuntes del cuaderno,
// lo que se usa, los análisis, las ventas y los planes). Estaba escrita a mano en cuatro pantallas y se
// estaba copiando a las demás: con la pieza, la siguiente lista que se añada son dos líneas. **Va en la
// lista o el agricultor abre una lista en el campo y no puede tocar nada.**
//
// Ronda 93 (segunda vez, y por eso el número sube otra vez): la lista de ficheros no cambia —la pieza ya
// estaba—, pero **`facturas.js` también la usa ahora**: la ficha de una factura ofrece BORRAR. El `-42` ya
// se había servido, así que un móvil que hubiera abierto la aplicación en ese rato se habría quedado con
// el `facturas.js` sin la barra de botones. Subir el número es lo único que hace que se la vuelva a bajar.
//
// Ronda 93 (tercera vez, y con el mismo motivo que la segunda): la lista tampoco cambia, pero ahora
// **`app.js` y `interpretacion_factura.js` cambian otra vez** para que una factura guardada se pueda
// corregir. Un móvil con el `-43` tendría el `app.js` sin ese camino: al pulsar CORREGIR en una factura
// no pasaría nada. El número sube cada vez que se sirve una versión y se toca un fichero de la lista;
// mientras el cambio no se haya servido, no hace falta subirlo, y aquí ya se había servido.
//
// Ronda 93 (cuarta vez): entra en la lista **`react/pantallas/campanas.js`**, la pantalla nueva de los años
// del cuaderno. Es el caso de manual otra vez: sin ella en la caché, el agricultor abre «los años de mi
// cuaderno» en el campo y se encuentra un hueco. Y con ella cambian también `app.js`, `mis_datos.js`,
// `componentes.js` y `acciones_de_una_ficha.js`, que ya estaban en la lista.
//
// Ronda 93 (quinta vez, y con el mismo motivo de siempre): la lista no cambia —`medidas.js` ya estaba—,
// pero cambian `app.js` (guardar las medidas con `PUT`, que es el método que el servidor acepta, y quitar
// la declaración) y `medidas.js` (el botón de quitarla). Sin subir el número, el móvil de David seguiría
// con el `app.js` que manda el `POST` que el servidor rechaza.
//
// Y sexta vez, el 30/09 por la tarde, con el mismo motivo de siempre: `app.js` cambia otra vez para **poner
// la versión en el pie** (lo pidió David: «no sé si estoy viendo lo nuevo o lo viejo»). El número de la
// caché y el que se enseña en el pie son **el mismo**, y hay una prueba que lo comprueba
// (`tests/test_la_version_visible.py`).
//
// Y séptima, el mismo día: entra **`react/piezas/marco.js`**, el armazón del ordenador. Es el caso de
// manual: sin él en la caché, un ordenador que abra la aplicación sin cobertura (o con la caché a medias
// justo después de este despliegue) se queda **sin menú y sin barra**.
//
// Y octava, el mismo día y por lo mismo: entra **`react/piezas/tabla.js`**, la tabla de las listas en el
// ordenador, y cambian `app.js`, `mis_cosas.js` y `estilos.css`. Un ordenador con la caché vieja vería la
// versión de móvil estirada, que es exactamente lo que David dijo que no quiere.
//
// Y novena: **la tabla del cuaderno** (los apuntes del año). Cambian `app.js`, `mi_cuaderno.js` y
// `textos.py`, que ya estaban en la lista, pero el número sube igual: un ordenador con la caché `-49`
// seguiría viendo los apuntes como tarjetas.
//
// Y décima: **las tablas de los años del cuaderno y de las facturas**. Otra vez sin ficheros nuevos, pero
// `app.js`, `campanas.js`, `facturas.js` y `textos.py` cambian: el número sube por el mismo motivo de
// siempre.
//
// Y undécima, el mismo día: **el panel de detalle al lado de la tabla** (fase 3). Cambian `tabla.js`,
// `app.js`, `estilos.css` y `textos.py`, que ya estaban en la lista.
//
// Y duodécima, el mismo día: **el panel de mando del ordenador** (fase 4). Entra **`react/piezas/panel_de_mando.js`**
// (la portada del pc: cuatro números, lo que falta, los últimos apuntes y el cierre), y cambian `inicio.js`,
// `app.js`, `estilos.css` y `textos.py`. Y otra vez por el mismo motivo de siempre: sin esta versión en la
// caché, un ordenador que abra la aplicación se queda con la pantalla de inicio del móvil estirada, que es
// justo lo que la fase 4 viene a arreglar.
//
// Y decimotercera: **lo que trajeron los seis diseños de escritorio nuevos** (30/09/2026): la tabla de «qué
// hay sembrado» con **el filtro de las que faltan** y **la alerta de rotación en su propia columna**, el
// **dibujo de la tierra y sus últimos apuntes** en el panel de al lado, el botón **ANULARLO** en los apuntes
// firmados y **el pie del cuaderno con los firmados**. Cambian `app.js`, `cultivos.js`, `tabla.js`,
// `estilos.css` y `textos.py`.
//
// Y decimocuarta, el 02/10/2026: **«no lo sé» deja de significar «sí» y deja de significar «no»** (los
// apartados A1 y A2 de `docs/T02_VALORES_POR_DEFECTO.md`). La autorización de un producto y la zona de
// nitratos de un apunte pasan a tener tres respuestas, y las fichas que dicen «no lo sé» tienen que
// enseñarlo marcado. Cambian `app.js` y `textos.py`, que ya estaban en la lista: sin subir el número, el
// móvil de David seguiría con el `app.js` que da por autorizado un producto del que nadie ha dicho nada.
//
// Y decimoquinta, el mismo día: **la respuesta elegida se lee**. Se miraba en un navegador la respuesta
// «No lo sé» recién añadida y salía verde oscuro sobre verde oscuro (1,5 a 1 de contraste): a `.boton-elegido`
// le faltaba el color de la letra. Entra `estilos.css`, que ya estaba en la lista.
//
// Y decimosexta, el mismo día: **las direcciones** (T04). Entra **`react/rutas.js`** —el enrutador: sin él
// en la caché, un móvil sin cobertura no puede traducir `#/tierras/12` a la pantalla de esa tierra, que es
// justo lo que la dirección viene a arreglar—, y cambian `app.js`, `estilos.css` y `textos.py`.
// Y decimoséptima, el 03/10/2026: **las pantallas que no tenían dirección** (segunda entrega de T04). Siete la
// tienen ya (el mapa, decir qué hay sembrado en una tierra, quién entra, la firma, la revisión de una factura,
// el dictado y su revisión) y seis pasos **no** la tienen a propósito. El service worker es *network-first*, así
// que quien tenga cobertura ya ve el `app.js` nuevo; subir el número es para que el móvil del campo, que abre
// sin cobertura, tenga también estas pantallas en su caché.
// Y decimoctava, el 03/10/2026: **el libro del almacén** (T09). Entran **seis pantallas nuevas** —el libro
// (lo que ha llegado, lo que queda envase por envase y el libro de movimientos), la ficha de un albarán,
// el alta de un albarán, una merma o un ajuste, sacar de un envase desde un apunte y decir de qué factura
// es un albarán—, y con ellas `app.js`, `cesta.js`, `mi_cuaderno.js`, `rutas.js` y `estilos.css`. Es el
// caso de manual que esta lista existe para cubrir: **la ficha de un albarán y el alta de un albarán se
// usan en el almacén, de pie y muchas veces sin cobertura**. Si uno de esos ficheros no estuviera en la
// caché, el agricultor abriría el libro en el campo y se encontraría un hueco.
// Y decimonovena, el 03/10/2026: **las tierras en el mapa y en la tabla, y lo que ha sido una tierra**
// (T06). Entran **dos pantallas nuevas** —`tierras_mapa.js` (la tabla de las 64 tierras con sus filtros,
// su agrupación, su selección y el mapa de la finca enlazado) y `tierra_versiones.js` (sus versiones por
// año y por fuente, la comparación de dos años y el ensayo de una importación)—, y con ellas cambian
// `app.js` (el cableado de las veinte acciones nuevas), `componentes.js` (la fila de botones de elegir,
// que usan las dos) y `rutas.js` (las dos direcciones nuevas). Se sube el número porque las dos se miran
// **en el campo**: la tabla de las tierras con el móvil en la mano es justo lo que no puede quedarse en
// blanco sin cobertura.
// Y vigésima, el 03/10/2026: **las semillas, las etiquetas y las siembras** (T10). Entran **dos pantallas
// nuevas** —`semillas.js` (la lista de semillas con lo que queda de cada una y la ficha donde se apunta
// lo que pone la etiqueta, incluida la lectura de una foto que **no guarda nada**) y `siembras.js` (lo
// que se ha sembrado y el formulario de «en esta tierra sembré esta semilla», que es lo que descuenta la
// semilla del almacén)—, y con ellas cambian `app.js`, `rutas.js` y `textos.py`. Es el caso de manual:
// **la semilla se siembra en el campo y sin cobertura**, así que si estos ficheros no están en la caché
// el agricultor abre la pantalla y se encuentra un hueco.
// Y vigésimo primera, el 03/10/2026: **las personas y las empresas** (T11). Entran **dos pantallas
// nuevas** —`contactos.js` (la lista de fichas, la ficha de una persona o una empresa con sus papeles y
// **dónde está escrito su nombre**, y la lista de nombres escritos para enlazarlos sin teclear una
// letra) y `revision_de_contactos.js` (la revisión de los nombres que ya están escritos, donde el
// programa **propone y no fusiona**)—, y con ellas cambian `app.js` y `rutas.js`. Se sube el número
// porque la ficha de un proveedor se mira en la nave y en el despacho, y porque la revisión de los
// nombres **es una decisión sobre datos**: abrirla sin cobertura y encontrarse un hueco sería justo lo
// contrario de lo que hace falta para decidir con calma.
// Y vigésimo segunda, el 03/10/2026: **el dinero de lo que se vende** (T12). Entran **siete pantallas
// nuevas** —la lista con su tabla y su pie, la factura nuestra (la lista, la ficha y el paso de juntar
// entregas), ponerle el importe a una entrega, apuntarle una devolución o un ajuste, y los cobros— más la
// pieza del campo de un importe. Se sube el número porque `ventas.js` cambia entero (la lista pasa a
// tabla) y porque «¿cuánto me deben?» es de las preguntas que el agricultor se hace con el móvil en la
// mano: si falta un fichero, esa pantalla es un hueco.
// Y vigésimo tercera, el 03/10/2026: **la maquinaria y sus inspecciones** (T14). Entra **un fichero con
// dos pantallas** —`maquinaria.js`: la lista con su tabla (máquina, tipo, matrícula o serie, propiedad,
// horas, próxima revisión, papeles y disponibilidad) y la ficha, que **separa las cinco obligaciones**
// (ITV, ITEAF, mantenimiento, seguro y ROMA)— con sus inspecciones y sus averías. Se sube el número porque
// esto se mira **en la nave y en el campo**: «¿puedo contar hoy con el tractor?» y «¿qué le toca pasar?»
// son preguntas que se hacen de pie, con el móvil en la mano, y una pantalla que no está en la caché es un
// hueco justo cuando más falta hace.
// Y vigésimo cuarta, el 05/10/2026: **las cuentas de la explotación** (T13). Entra **un fichero con
// dos pantallas** —`gastos.js`: la lista de lo que ha costado, con sus tres columnas de coste, la
// caja, las inversiones, las ayudas y el margen; y la ficha de un gasto, con sus repartos y su
// cuadre—. Se guarda para el campo por el mismo motivo que las demás, y aquí con más razón: las
// cuentas se miran también de pie en la nave, y una cifra de dinero a medias es peor que ninguna.
// Y vigésimo quinta, el mismo día: **los trabajos por tierra** (T15). Entra **otro fichero con tres
// pantallas** —`trabajos.js`: la agenda (lo que se piensa hacer y lo que se ha hecho, en dos listas
// separadas), la ficha de un trabajo (planificarlo, marcar lo que de verdad se hizo, cambiarlo de día,
// corregirlo o anularlo) y la historia de una tierra, con todo lo que ha pasado—. Se sube el número
// porque esto es, literalmente, el campo: lo que se piensa hacer se mira antes de salir y lo que se ha
// hecho se apunta allí mismo, donde peor va la cobertura.
// Y vigésimo sexta, el 05/10/2026: **el extracto del banco y la conciliación** (T20, la pantalla S14).
// Entra **un fichero con dos pantallas** —`bancos.js`: los movimientos con su estado y lo que les
// queda por cuadrar, y la ficha de uno, que es donde se dice contra qué papel va el dinero—, y cambian
// `app.js`, `rutas.js`, `gastos.js` (el botón que entra desde las cuentas) y `textos.py`. Se sube el
// número porque esto se mira **en el despacho y sin prisa**, y una pantalla de dinero que no está en la
// caché es un hueco justo cuando hay que decidir a qué factura va un cobro.
const CACHE = "cuedigital-2026-10-22-79";

const FICHEROS = [
  "/",
  "/index.html",
  "/estilos.css",
  "/app.js",
  "/nucleo.js",
  "/manifest.webmanifest",
  "/marca.svg",
  // La pantalla de inicio se pinta con React. Estos tres van aquí porque son tan parte de la
  // aplicación como `app.js`: sin ellos, la primera pantalla no se puede dibujar sin cobertura.
  // El de `react-dom-server` NO va: ese es solo para las pruebas, en el navegador no se usa.
  "/vendor/react.production.min.js",
  "/vendor/react-dom.production.min.js",
  "/vendor/htm.umd.js",
  // Las pantallas escritas en React.
  "/react/componentes.js",
  "/react/montar.js",
  // El enrutador (T04): traduce la dirección del navegador a la pantalla que se ve. Sin él, abrir una
  // dirección guardada sin cobertura no llevaría a ninguna parte.
  "/react/rutas.js",
  // **El inventario de acciones por su efecto real** (18/10/2026): *sin el, la pantalla no sabe que
  // botones esconder cuando no hay cobertura -ni cuando el usuario no puede escribir-.*
  "/react/acciones.js",
  "/react/pantallas/inicio.js",
  // **La preparacion de la PAC** (CRM-09): *su direccion es `#/pac`, y sin cobertura tiene que abrir.*
  "/react/pantallas/pac.js",
  "/react/pantallas/hecho.js",
  "/react/pantallas/mis_cosas.js",
  "/react/pantallas/documentos.js",
  "/react/pantallas/cesta.js",
  "/react/pantallas/cultivos.js",
  "/react/pantallas/ayuda.js",
  "/react/pantallas/mis_datos.js",
  "/react/pantallas/quien_entra.js",
  "/react/pantallas/medidas.js",
  "/react/pantallas/ventas.js",
  "/react/pantallas/grupos.js",
  "/react/pantallas/analiticas.js",
  "/react/pantallas/dictado.js",
  "/react/pantallas/borrador.js",
  "/react/pantallas/nuevo_documento.js",
  "/react/pantallas/firmar.js",
  "/react/pantallas/planes.js",
  "/react/pantallas/entrar.js",
  "/react/pantallas/facturas.js",
  "/react/pantallas/nueva_factura.js",
  "/react/pantallas/interpretacion_factura.js",
  "/react/pantallas/mapa.js",
  "/react/pantallas/decir_cultivo.js",
  "/react/pantallas/cuaderno_de_la_junta.js",
  "/react/pantallas/traer_del_sigpac.js",
  // Ronda 93: los años del cuaderno. Si no va en la lista, el agricultor abre esa pantalla sin cobertura y
  // se encuentra un hueco.
  "/react/pantallas/campanas.js",
  // T09 (03/10/2026): el libro del almacén y sus cuatro formularios. La ficha de un albarán y el alta de un
  // albarán se usan **en el almacén**, de pie y muchas veces sin cobertura: son las que menos pueden
  // permitirse un hueco.
  "/react/pantallas/libro_del_almacen.js",
  "/react/pantallas/nuevo_albaran.js",
  "/react/pantallas/recepcion.js",
  /* **La ficha de una compra** (S11, 09/10/2026): lo facturado, lo recibido, lo pagado y lo que queda.
   * Va en la caché por lo de siempre: es una pantalla que se mira con el papel delante, y eso puede
   * pasar en el almacén, donde no hay cobertura. */
  "/react/pantallas/compra.js",
  "/react/pantallas/movimiento_de_almacen.js",
  "/react/pantallas/sacar_de_un_lote.js",
  "/react/pantallas/enganchar_la_factura.js",
  // T06 (03/10/2026): las tierras en el mapa y en la tabla, y lo que ha sido una tierra.
  "/react/pantallas/tierras_mapa.js",
  "/react/pantallas/tierra_versiones.js",
  // La búsqueda global (07/10/2026): se guarda como las demás, para que la caja funcione también sin
  // cobertura (que es donde se busca «¿dónde está esto?» cuando no hay nada más que hacer).
  "/react/pantallas/buscar.js",
  "/react/pantallas/normativa.js",
  // T10 (03/10/2026): las semillas y lo que se ha sembrado. Las dos se miran **en la nave y en el
  // campo**: la lista de semillas para saber de cuál queda, y la siembra para apuntarla en el mismo
  // momento en que se está sembrando.
  "/react/pantallas/semillas.js",
  "/react/pantallas/siembras.js",
  // T11 (03/10/2026): las personas y las empresas. La ficha de un proveedor o de un comprador se mira
  // en la nave y en el despacho, y la revisión de los nombres escritos es una decisión sobre datos que
  // hay que poder mirar con calma: las dos son un hueco si faltan en la caché.
  "/react/pantallas/contactos.js",
  // **La pantalla de las tareas** (Entrega 3, 14/10/2026). Va aquí porque sin este fichero en la caché el
  // agricultor abre `#/tareas` **sin cobertura** y se encuentra una pantalla en blanco: es justo lo que la
  // prueba `test_todo_el_javascript_de_react_se_guarda_para_el_campo` vigila, y por eso la cazó.
  "/react/pantallas/tareas.js",
  "/react/pantallas/trabajos_a_terceros.js",
  "/react/pantallas/fusion.js",
  "/react/pantallas/revision_de_contactos.js",
  // La maquinaria (T14, 03/10/2026): la lista y la ficha de una máquina.
  "/react/pantallas/maquinaria.js",
  "/react/pantallas/gastos.js",
  // Los trabajos por tierra (T15, 05/10/2026): la agenda, la ficha de un trabajo y la historia de una
  // tierra, las tres en un fichero.
  "/react/pantallas/trabajos.js",
  // El banco y los papeles (T20, 05/10/2026): los movimientos y la ficha de uno. Se guarda para el
  // campo por el mismo motivo que las cuentas: el extracto se mira en el despacho y la conciliación
  // se piensa con calma, muchas veces sin cobertura.
  "/react/pantallas/bancos.js",
  // La bandeja documental (T08, S10, 06/10/2026): lo que llega y hay que revisar, y la ficha de un papel,
  // las dos en un fichero. Se guarda para el campo por el mismo motivo que las cuentas: un papel se mira
  // en la nave y en el despacho, y una pantalla que no está en la caché es un hueco justo cuando hay que
  // decidir si un papel entra en el cuaderno.
  "/react/pantallas/bandeja.js",
  // 30/09/2026: el armazón del ordenador (el menú lateral y la barra de arriba). Es lo primero que se pinta
  // al abrir la aplicación en un ordenador: sin este fichero en la caché, la pantalla sale sin menú.
  "/react/piezas/marco.js",
  // Y la tabla de las listas en el ordenador (mismo día): sin ella, «Mis parcelas» sale sin la tabla de las
  // 64 tierras.
  "/react/piezas/tabla.js",
  "/react/piezas/panel_de_mando.js",
  "/react/pantallas/mi_cuaderno.js",
  "/react/pantallas/asistente.js",
  // Las PIEZAS: componentes que no son una pantalla entera, sino un trozo de una (el resumen del
  // asistente, la lista de botones para elegir, el campo con su ayuda y un grupo de campos del maestro,
  // que se montan en el hueco del formulario).
  "/react/piezas/resumen_del_apunte.js",
  "/react/piezas/lista_para_elegir.js",
  "/react/piezas/campo.js",
  "/react/piezas/ayuda_de_un_campo.js",
  "/react/piezas/campos_del_maestro.js",
  "/react/piezas/confirmacion.js",
  "/react/piezas/tarjeta.js",
  // La barra de acciones de una ficha: CORREGIR y BORRAR (ronda 93).
  "/react/piezas/acciones_de_una_ficha.js",
  // T12 (03/10/2026): **el dinero de lo que se vende**. Son siete pantallas —la lista con su tabla y su
  // pie, la factura nuestra (la lista, la ficha y el paso de juntar entregas), ponerle el importe a una
  // entrega, apuntarle una devolución o un ajuste, y los cobros— más la pieza del campo de un importe.
  // Van todas aquí por lo de siempre: la cuenta de la factura se mira **en la nave y en el despacho**, y
  // «¿cuánto me deben?» es de las preguntas que no pueden quedarse en blanco por falta de cobertura.
  "/react/pantallas/ventas.js",
  "/react/pantallas/facturas_emitidas.js",
  "/react/pantallas/facturar_entregas.js",
  "/react/pantallas/factura_emitida.js",
  "/react/pantallas/venta_importe.js",
  "/react/pantallas/venta_ajuste.js",
  "/react/pantallas/cobros.js",
  "/react/pantallas/cobro_nuevo.js",
  "/react/piezas/campo_de_un_importe.js",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches
      .open(CACHE)
      // addAll falla entero si UN fichero falla. Se piden uno a uno para que un
      // despiste no deje la aplicación sin guardar nada.
      .then((cache) => Promise.all(FICHEROS.map((f) => cache.add(f).catch(() => null))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((claves) => Promise.all(claves.filter((c) => c !== CACHE).map((c) => caches.delete(c))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;

  // Solo se toca lo que se pide con GET. Un apunte (POST) va siempre al servidor.
  if (peticion.method !== "GET") return;

  const url = new URL(peticion.url);
  if (url.origin !== self.location.origin) return;

  // Los datos del agricultor no se guardan nunca en la caché del navegador.
  if (url.pathname.startsWith("/api/") || url.pathname === "/health") return;

  evento.respondWith(
    fetch(peticion)
      .then((respuesta) => {
        if (respuesta && respuesta.ok) {
          const copia = respuesta.clone();
          caches.open(CACHE).then((cache) => cache.put(peticion, copia));
        }
        return respuesta;
      })
      .catch(() =>
        caches.match(peticion).then((guardada) => {
          if (guardada) return guardada;
          // Si se pide una pantalla que no está guardada, se devuelve la portada:
          // es mejor eso que la pantalla de error del navegador.
          if (peticion.mode === "navigate") return caches.match("/");
          return new Response("Sin conexión", { status: 503, statusText: "Sin conexión" });
        }),
      ),
  );
});
