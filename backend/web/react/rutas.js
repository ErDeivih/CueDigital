/*
 * rutas.js — La dirección de cada pantalla: de dirección a pantalla y de pantalla a dirección.
 *
 * POR QUÉ EXISTE (T04 / E1, 02/10/2026)
 *
 * Hasta hoy la aplicación **no tenía direcciones**. Estaba medido: cero `pushState`, cero
 * `location.hash` y cero `history` en todo `backend/web/`. Eso quiere decir tres cosas que se notan
 * todos los días: ninguna ficha se puede enlazar ni mandar a nadie, el botón «atrás» del móvil saca de
 * la aplicación en vez de volver a la lista, y recargar devuelve al agricultor al principio. Con 64
 * tierras, volver al principio es volver a buscar la tierra desde cero.
 *
 * POR QUÉ LA DIRECCIÓN VA DESPUÉS DE UN `#` Y NO ES UN CAMINO
 *
 * Esta es la decisión que hay que entender antes de tocar nada, y es por dos motivos que se suman:
 *
 *  1. **El servidor no tiene «fallback» de aplicación de una sola página.** Los ficheros de la web se
 *     montan en `/` con `StaticFiles(..., html=True)`, que sirve un fichero por su nombre y punto. Una
 *     dirección de camino como `/tierras/12` no es ningún fichero: el servidor contesta **404**, así
 *     que recargar la ficha de una tierra sería encontrarse con una pantalla que no existe. Y no se
 *     arregla añadiendo una regla al servidor, porque el segundo motivo lo dejaría igual.
 *  2. **La aplicación tiene que abrirse sin cobertura.** La abre el *service worker* desde la caché, y
 *     lo que sirve de la caché es el `index.html`. Cualquier dirección que no sea la raíz no está en la
 *     caché, así que sin cobertura daría igualmente un error.
 *
 * La parte que va **después del `#` no llega nunca al servidor**: la corta el navegador antes de pedir
 * nada. Por eso `#/tierras/12` funciona siempre —recargando, abriendo un enlace directo, sin cobertura
 * y con el servidor caído—, y por eso esta aplicación enruta por fragmento y no por camino. **Es la
 * única forma de que una ficha tenga dirección sin tocar el servidor.**
 *
 * QUÉ ES Y QUÉ NO ES ESTE FICHERO
 *
 * Este fichero es **el traductor**: solo pasa de dirección a pantalla y de pantalla a dirección. No
 * llama a `fetch`, no lee `localStorage`, no toca el DOM, no usa `history` y no mira `window`: lo que
 * hable con el navegador lo hará `app.js` (escuchar `hashchange`, escribir en la barra de direcciones),
 * que es donde ya vive todo lo demás. Así esto se puede probar entero sin navegador —es lo que hace
 * `tests_js/rutas.test.js`— y no hay dos sitios que decidan lo mismo.
 *
 * Y **no lleva ni una frase para el agricultor**: aquí no hay textos, solo direcciones. Las palabras
 * salen de `textos.py` por propiedades, como en todo lo demás.
 */

/**
 * La tabla de las pantallas: la clave de cada una y la forma de su dirección.
 *
 * `patron` son los tramos que van después del `#`, en orden:
 *
 *  - un tramo de **texto fijo** tiene que coincidir con lo que ponga la dirección;
 *  - un tramo que **empieza por `:`** es el identificador de una ficha, tiene que ser un número entero
 *    y sale en `parametros` con el nombre que sigue a los dos puntos.
 *
 * **Las claves son las del menú**, tal y como están en la tabla `MODULOS` de `app.js` —`almacen`,
 * `facturas`, `anos`, `grupos`, `cultivos`, `analisis`, `plan`, `ventas`, `medidas`, `papeles`,
 * `junta`, `datos`, `ayuda`, y `cuaderno` y `tierras`—, para que un módulo y su dirección se llamen
 * igual y nadie tenga que traducir. Con tres excepciones, dichas aquí para que no sorprendan:
 *
 *  1. **`inicio`**: el menú llama `panel` a su primer renglón («Panel»), y aquí la pantalla se llama
 *     `inicio` porque es lo que es (la pantalla de inicio, `#/`). «Panel» es el nombre del renglón.
 *  2. **`tierra`**: la ficha de una tierra, que no está en el menú porque no se llega a ella desde
 *     un módulo: se llega desde la lista (`#/tierras` → `#/tierras/12`).
 *  3. **`apunte`**: lo mismo con un apunte del cuaderno (`#/cuaderno` → `#/cuaderno/<id>`).
 *
 * **El orden de la tabla importa** cuando dos patrones encajan con el mismo número de tramos: gana el
 * que va antes. Por eso los tramos de texto fijo van antes que los de identificador (el día que exista
 * `#/tierras/nueva`, tiene que ir por encima de `#/tierras/:id`). Los patrones se agrupan por familia
 * —todo lo de `tierras` junto, todo lo de `cuaderno` junto—, y dentro de cada familia el tramo fijo va
 * antes que el identificador.
 *
 * **Lo que NO está aquí, y por qué (T04, segunda entrega).** Las pantallas que son **un paso de un
 * formulario** no tienen dirección: el asistente de apuntar (sus 65 pasos), «lo he apuntado», el alta
 * de un papel, el alta de una factura, el paso del SIGPAC y la pantalla de entrar. Una dirección que
 * al recargar deja al agricultor en un formulario a medias —o, peor, en un formulario **vacío**
 * creyendo que ya había guardado— es peor que no tenerla: lo que esos pasos llevan escrito vive en la
 * memoria de la sesión y no se puede reproducir desde una barra de direcciones. `app.js` los tiene
 * apuntados en `PANTALLAS_SIN_DIRECCION` y **no les escribe ninguna**, así que la dirección se queda
 * en la de la pantalla de la que salieron. Lo que sí tiene dirección es **el borrador** (`#/borrador`),
 * que es una pantalla a la que se vuelve, y **el dictado** (`#/dictado`), que es la puerta de la que
 * sale el borrador.
 */
export const PANTALLAS = [
  // La pantalla de inicio: no lleva tramos. `""`, `"#"`, `"#/"` y `"/"` son esta, las cuatro.
  { clave: "inicio", patron: [] },
  { clave: "tierras", patron: ["tierras"] },
  // **Los trabajos (T15, 05/10/2026)**: la agenda, y la historia de una tierra (`#/tierras/<id>/historial`).
  // Las dos piden sus datos al servidor al abrir su dirección, así que se pueden enlazar y recargar. La
  // ficha de un trabajo **no tiene dirección**: es un formulario, y uno que al recargar saldría vacío es
  // peor que no tenerla. El tramo de texto fijo (`historial`) va **antes** que el identificador, como en
  // todas las familias de esta tabla.
  { clave: "trabajos", patron: ["trabajos"] },
  { clave: "trabajo_tierra", patron: ["tierras", ":id", "historial"] },
  // **Las tierras en el mapa y en la tabla** (T06, 03/10/2026). Es la vista que pide el contrato en su
  // apartado 2.1: las 64 tierras con buscador, filtros, agrupación, selección múltiple y el mapa de la
  // finca al lado, enlazados. Va **con su propio tramo de texto fijo** y no en `tierras` por un motivo
  // concreto: `#/tierras` es la pantalla de siempre («mis parcelas, productos y máquinas»), que tiene
  // su buscador y su tabla desde antes, y cambiarle el contenido habría roto todos los enlaces y todas
  // las pruebas que ya contaban con ella. Esta es **una vista más de las mismas tierras**, y su
  // dirección se lee sola. Y va **antes** que `tierra` (`:id`) porque los tramos fijos van delante de
  // los identificadores en esta tabla.
  { clave: "tierras_mapa", patron: ["tierras", "mapa"] },
  { clave: "tierra", patron: ["tierras", ":id"] },
  // **Lo que ha sido una tierra** (T06): sus versiones por año y por fuente, la comparación de dos años
  // y el ensayo de una importación. Se llega desde el mapa de las tierras y desde la ficha, y volver a
  // su dirección la reconstruye entera (pide las versiones al servidor), así que tiene dirección.
  { clave: "tierra_versiones", patron: ["tierras", ":id", "versiones"] },
  // **La búsqueda global** (07/10/2026, del encargo del rediseño): su dirección propia, para que recargar
  // deje al agricultor donde estaba y el enlace se pueda guardar. Es la puerta de la pantalla mientras el
  // renglón del menú llega (está especificado, con sus cuatro números, en `docs/ESTADO_DEL_REDISENO.md`).
  { clave: "buscar", patron: ["buscar"] },
  { clave: "normativa", patron: ["normativa"] },
  // Decir qué hay sembrado **en una tierra**: es de una tierra, así que su identificador va en el camino.
  // Sin él, recargar dejaría al agricultor en la lista de lo sembrado y tendría que volver a buscar
  // cuál de sus 51 tierras era (que es el mismo motivo por el que la ficha de una tierra tiene dirección).
  { clave: "decir_cultivo", patron: ["tierras", ":id", "cultivo"] },
  { clave: "cuaderno", patron: ["cuaderno"] },
  // Firmar el cuaderno: un tramo de texto fijo, y va **antes** que el apunte (`:id`) porque los tramos
  // fijos van siempre delante de los identificadores en esta tabla.
  { clave: "firmar", patron: ["cuaderno", "firmar"] },
  { clave: "apunte", patron: ["cuaderno", ":id"] },
  { clave: "almacen", patron: ["almacen"] },
  // El libro del almacén (T09, 03/10/2026): lo que ha llegado, lo que queda envase por envase y lo que ha
  // pasado. Es otro sitio y no un paso, así que tiene su dirección: se puede enlazar y recargar. Y va
  // **antes** que la ficha del albarán, porque los tramos de texto fijo van delante de los identificadores.
  { clave: "libro_almacen", patron: ["almacen", "libro"] },
  // La ficha de un albarán: su identificador en el camino, como en una tierra. Al recargar, `app.js`
  // vuelve a pedir ese albarán al servidor (el libro no se descarga al arrancar), y si no hay cobertura
  // dice que no lo ha podido comprobar en vez de decir que no existe.
  { clave: "recepcion", patron: ["almacen", "recepcion", ":id"] },
  // **La ficha de una compra** (S11, 09/10/2026): lo que dice la factura, lo que ha entrado, lo que se
  // ha pagado y lo que queda, en un sitio. Va con su identificador porque es una ficha y no una lista:
  // se puede enlazar, recargar y volver a ella, y al recargar `app.js` la pide al servidor.
  { clave: "compra", patron: ["compras", ":id"] },
  // **Las semillas y lo que se ha sembrado** (T10, 03/10/2026). Las dos se reconstruyen enteras al abrir
  // su dirección —se piden al servidor—, así que se pueden enlazar, recargar y mandar a quien ayuda.
  // La semilla va **antes** que la siembra en la tabla por el orden de esta lista (no encajan las dos
  // con la misma dirección: son dos tramos contra dos tramos con el segundo distinto, así que no se
  // pisan), y las dos van con texto fijo y no con un identificador: son listas, no fichas, y una lista
  // no necesita su identificador en la barra de direcciones.
  { clave: "semillas", patron: ["semillas"] },
  { clave: "siembras", patron: ["semillas", "siembras"] },
  // **Las personas y las empresas** (T11, 03/10/2026). Se reconstruyen enteras al abrir su dirección
  // —piden sus datos al servidor—, así que se pueden enlazar, recargar y mandar a quien ayuda.
  // Las dos van con texto fijo y no con un identificador: son una lista y una revisión, no fichas, y
  // una lista no necesita su identificador en la barra de direcciones. La revisión **tiene** que poder
  // recargarse: es una decisión sobre datos, y volver a mirarla después de pensarlo es lo normal. Va
  // después de `contactos` por el orden de esta tabla (dos tramos contra uno: no se pisan).
  { clave: "contactos", patron: ["contactos"] },
  { clave: "revisar_contactos", patron: ["contactos", "revisar"] },
  // **La ficha de un contacto** (Entrega 1, 13/10/2026): con su identificador, como la de una compra o un
  // gasto. Va **despues** de `revisar_contactos` a proposito: `:id` tambien casaria con «revisar», y el literal
  // tiene que ir primero (lo dice la nota de arriba de esta tabla). Sin direccion no se puede recargar la ficha
  // ni volver a ella, que es lo que la revision midio.
  { clave: "contacto", patron: ["contactos", ":id"] },
  { clave: "facturas", patron: ["facturas"] },
  // Revisar una factura **que ya está guardada**: su identificador va en el camino, y con él la pantalla
  // se vuelve a armar entera con lo que hay en el cuaderno. Lo que se acaba de leer de una foto **no**
  // tiene dirección: esa lectura no está guardada en ningún sitio y no se puede reproducir.
  { clave: "interpretacion_factura", patron: ["facturas", ":id"] },
  { clave: "anos", patron: ["anos"] },
  { clave: "grupos", patron: ["grupos"] },
  { clave: "cultivos", patron: ["cultivos"] },
  { clave: "analisis", patron: ["analisis"] },
  { clave: "plan", patron: ["plan"] },
  { clave: "ventas", patron: ["ventas"] },
  // **El dinero de lo que se vende** (T12, E6, 03/10/2026): la factura nuestra, juntar entregas,
  // apuntar el importe de una entrega, sus ajustes y los cobros. Todas se reconstruyen enteras al
  // abrir su dirección —piden sus datos al servidor—, así que se pueden enlazar, recargar y mandar a
  // quien ayuda. **Los tramos de texto fijo van antes que los identificadores** en esta tabla, y por
  // eso `facturas`, `cobros` y `facturar` van por encima de `:id`: si no, `#/ventas/cobros` se leería
  // como la entrega número «cobros», que no existe.
  { clave: "facturas_emitidas", patron: ["ventas", "facturas"] },
  { clave: "facturar_entregas", patron: ["ventas", "facturar"] },
  { clave: "cobros", patron: ["ventas", "cobros"] },
  // Un cobro nuevo es **una pantalla a la que se va** (y se puede volver a mirar), no un paso de nada:
  // por eso tiene dirección. Se escribe con palabra fija y va antes que la ficha de un cobro.
  { clave: "cobro_nuevo", patron: ["ventas", "cobros", "nuevo"] },
  { clave: "factura_emitida", patron: ["ventas", "facturas", ":id"] },
  // Poner el importe de una entrega y apuntar un ajuste suyo: son de una entrega, así que su
  // identificador va en el camino. Sin él, recargar dejaría al agricultor en la lista teniendo que
  // buscar cuál de sus entregas era.
  { clave: "venta_importe", patron: ["ventas", ":id", "importe"] },
  { clave: "venta_ajuste", patron: ["ventas", ":id", "ajuste"] },
  // **Las cuentas de la explotación** (T13, 05/10/2026). La lista se reconstruye entera al abrir su
  // dirección —pide sus datos al servidor— y **la ficha de un gasto también** (se pide a su puerta),
  // así que las dos se pueden enlazar, recargar y mandar a quien ayuda. El tramo de texto fijo va
  // **antes** que el identificador, como en todas las familias de esta tabla: el día que exista
  // `#/cuentas/nuevo`, tiene que ir por encima de `#/cuentas/:id`.
  { clave: "gastos", patron: ["cuentas"] },
  // **El extracto del banco y la conciliación (T20, E11, 05/10/2026).** La lista vive **dentro de la
  // familia de las cuentas** (`#/cuentas/bancos`), que es el renglón del menú del que sale, por los mismos
  // motivos que las demás listas de esta tabla: se reconstruye entera al abrir su dirección —pide sus
  // datos al servidor—, así que se puede enlazar, recargar y mandar a quien ayuda. Y **el tramo de texto
  // fijo va antes que el identificador**, como en todas las familias: si no, `#/cuentas/bancos` se leería
  // como la ficha del gasto número «bancos», que no existe.
  { clave: "bancos", patron: ["cuentas", "bancos"] },
  // Y **la ficha de un movimiento tiene su dirección** (`#/cuentas/bancos/12`): al recargarla se vuelven a
  // pedir sus propuestas al servidor, así que no sale vacía. Lo que **no** tiene dirección son sus
  // formularios (subir el fichero, el alta de una cuenta, la forma de escribir del banco, la corrección
  // del importe): al recargar saldrían vacíos, y eso es peor que no tener dirección.
  { clave: "banco_movimiento", patron: ["cuentas", "bancos", ":id"] },
  { clave: "gasto", patron: ["cuentas", ":id"] },
  { clave: "medidas", patron: ["medidas"] },
  // **La maquinaria y una máquina** (T14, 03/10/2026). La lista se reconstruye entera al abrir su
  // dirección —pide sus datos al servidor—, y la ficha de una máquina **también** (se pide a su puerta),
  // así que se pueden enlazar, recargar y mandar a quien ayuda. El tramo de texto fijo va **antes** que el
  // identificador, como en todas las familias de esta tabla: el día que exista `#/maquinaria/nueva`, tiene
  // que ir por encima de `#/maquinaria/:id`.
  { clave: "maquinaria", patron: ["maquinaria"] },
  { clave: "maquina", patron: ["maquinaria", ":id"] },
  { clave: "papeles", patron: ["papeles"] },
  // **La bandeja documental (T08, S10, 06/10/2026).** La lista vive **dentro de la familia de los
  // papeles** (`#/papeles/bandeja`), que es el renglón del menú del que sale: la bandeja es lo que llega
  // y hay que revisar, y «los papeles» es lo que ya está archivado. Se reconstruye entera al abrir su
  // dirección —pide sus datos al servidor—, así que se puede enlazar, recargar y mandar a quien ayuda.
  // Y el tramo de texto fijo va **antes** que el identificador, como en todas las familias: si no,
  // `#/papeles/bandeja` se leería como un papel llamado «bandeja», que no existe.
  { clave: "bandeja", patron: ["papeles", "bandeja"] },
  // Y **la ficha de un papel tiene su dirección** (`#/papeles/bandeja/12`): al recargarla se vuelven a
  // pedir al servidor su propuesta, sus enlaces y sus candidatos, así que no sale vacía. Lo que **no**
  // tiene dirección son sus formularios (la revisión de lo que queda y la comprobación del fichero que se
  // está subiendo): al recargar saldrían vacíos, y eso es peor que no tener dirección.
  { clave: "bandeja_papel", patron: ["papeles", "bandeja", ":id"] },
  { clave: "junta", patron: ["junta"] },
  { clave: "datos", patron: ["datos"] },
  // Quién entra en la finca: es un destino de «mis datos» (pide sus dos listas al servidor), no un paso
  // de nada. Se escribe con guion porque es una dirección, y las direcciones se leen mejor con guiones.
  { clave: "quien_entra", patron: ["datos", "quien-entra"] },
  { clave: "ayuda", patron: ["ayuda"] },
  // El mapa: se abre de cero y se centra solo, así que volver a su dirección lo reconstruye. Lo que
  // todavía NO viaja en la dirección es dónde se estaba mirando (el zoom y el punto elegido): se dice
  // en el contrato (`docs/T04_CONTRATO_NAVEGACION.md`), no se calla.
  { clave: "mapa", patron: ["mapa"] },
  // El dictado y su revisión. El dictado es una pantalla a la que se va (tiene su botón en la pantalla de
  // inicio) y el borrador es lo que sale de él: es la pantalla a la que se vuelve a mirar lo entendido.
  // Abrir `#/borrador` sin haber dictado no inventa una revisión: lleva al dictado, que es donde nace.
  { clave: "dictado", patron: ["dictado"] },
  { clave: "borrador", patron: ["borrador"] },
];

/**
 * Las pantallas que son **una lista con buscador y con orden**, que son las que tienen algo que
 * recordar cuando el agricultor entra en una ficha y vuelve.
 *
 * Son exactamente las seis listas que hoy tienen tabla en `app.js` (su tabla `ORDEN_DE_ENTRADA`:
 * `tierras`, `apuntes`, `facturas`, `anos`, `cesta` y `cultivos`), con el nombre que cada una tiene en
 * esta tabla. Se dice aquí, y no en `app.js`, porque es la misma lista vista desde los dos lados: si
 * mañana una lista nueva quiere recordar su vista, tiene que entrar en los dos sitios.
 */
/**
 * **Hoy NINGUNA pantalla usa esto, y conviene saberlo antes de perder el tiempo con ello** (11/10/2026).
 *
 * POR QUÉ ESTÁ ESCRITO Y NO SE USA. Este mecanismo pretendía que una lista recordara su vista (su buscador y
 * su orden) por su clave. Se midió al arreglar los filtros de lo que se vende (CRM-01): **`esUnListado` no
 * tiene un solo consumidor en todo el programa** —ni en `app.js`, ni en las pantallas de React, ni en otro
 * módulo—, y su única prueba es la que comprueba que la función hace lo que dice. Lo que de verdad conserva
 * la vista de una lista en este programa es **otra cosa**: los filtros **viajan en la dirección**
 * (`parametrosDeLaPantalla` los escribe y `abrirLaPantalla` los lee), que es lo que permite recargar,
 * mandar el enlace y volver de una ficha sin perder nada. Eso se comprueba con una prueba de
 * comportamiento (`tests_js/interfaz.test.js`, la de los filtros de ventas).
 *
 * Así que: **no conectes una lista a `LISTADOS` esperando que eso arregle sus filtros** —no los arregla, no
 * lo usa nadie—; escribe sus filtros en la dirección, como las demás. Y si alguien decide conectar esto o
 * retirarlo, que lo haga sabiendo lo que hay: es una lista de claves sin lector.
 */
export const LISTADOS = ["tierras", "cuaderno", "facturas", "anos", "almacen", "cultivos"];

/**
 * Los parámetros de consulta que son **un número** y por eso se leen como número.
 *
 * POR QUÉ NO SE LEEN TODOS COMO TEXTO, QUE SERÍA LO FÁCIL. Porque `2026 === "2026"` es falso, y el
 * fallo que eso produce es de los que no se ven: el agricultor abre una dirección con la campaña
 * puesta, la pantalla la compara con la suya, no coincide, y **el filtro no se aplica**. Nadie ve un
 * error; solo se ve una lista que no es la que se pidió. Los cuatro son identificadores o cuentas: el
 * `id` de la ficha que se está mirando, la `campana` y la `finca` en las que se trabaja, y el `sentido`
 * del orden de una tabla (que vale 1 o -1). Todo lo demás —el buscador `q`, el nombre del campo por el
 * que se ordena, y cualquier parámetro que no conozcamos— viaja como texto, que es lo que de verdad es.
 */
const SON_NUMEROS = ["id", "campana", "finca", "sentido"];

/** ¿Es un número entero escrito con dígitos? (`"12"` sí, `"-3"`, `"1.5"`, `"abc"` y `""` no). */
function esNumeroEntero(texto) {
  if (typeof texto !== "string" || texto === "") return false;
  // Se mira letra a letra y no con una expresión regular a propósito: así este fichero no necesita
  // nada del navegador ni ninguna dependencia, y se lee de un vistazo qué se acepta.
  for (const letra of texto) {
    if (letra < "0" || letra > "9") return false;
  }
  return true;
}

/** Un entero que puede llevar signo delante: es lo que vale el sentido de una tabla (1 o -1). */
function esEntero(texto) {
  if (typeof texto !== "string" || texto === "") return false;
  const sinSigno = texto.startsWith("-") || texto.startsWith("+") ? texto.slice(1) : texto;
  return esNumeroEntero(sinSigno);
}

/**
 * El valor de un parámetro **en su única forma posible**.
 *
 * Esto es lo que hace que la ida y la vuelta cuadren: `escribir` y `leer` usan la misma función, así
 * que `2026`, `"2026"` y `"007"` acaban los tres en el mismo sitio (`2026`), y una dirección escrita
 * dos veces con los mismos datos sale **igual**.
 */
function canonico(nombre, valor) {
  if (!SON_NUMEROS.includes(nombre)) return valor;
  return esEntero(valor) ? Number(valor) : valor;
}

/**
 * Lo que hay que leer de una dirección: el camino por un lado y la consulta por otro.
 *
 * Se acepta lo que un agricultor o un navegador pueden escribir de verdad: con `#` o sin él, con barra
 * o sin ella (`#/tierras/12`, `/tierras/12`, `#/tierras/12/`), y en mayúsculas, porque el teclado del
 * móvil pone la primera letra en mayúscula y no se le puede pedir a nadie que lo escriba en minúscula.
 */
function partes(direccion) {
  const texto = typeof direccion === "string" ? direccion : "";
  const sinAlmohadilla = texto.startsWith("#") ? texto.slice(1) : texto;
  const corte = sinAlmohadilla.indexOf("?");
  return {
    camino: corte === -1 ? sinAlmohadilla : sinAlmohadilla.slice(0, corte),
    consulta: corte === -1 ? "" : sinAlmohadilla.slice(corte + 1),
  };
}

/** El texto de un trozo de dirección, desescapado. Lo que no se puede desescapar se deja tal cual. */
function desescapa(texto) {
  try {
    return decodeURIComponent(texto);
  } catch (fallo) {
    // Un `%` suelto (`?q=50%`) no puede tumbar la aplicación: se lee como está escrito y la dirección
    // se leerá como se pueda. Aquí **nada lanza**: una dirección rara devuelve «desconocida», nunca un
    // aviso rojo delante del agricultor.
    return texto;
  }
}

/**
 * La consulta, en parámetros.
 *
 * Cuatro decisiones que se ven en el código y que están dichas para que nadie las cambie sin querer:
 *
 *  1. **Un parámetro vacío es como no estar** (`?campana=&q=`). Un filtro en blanco es lo mismo que no
 *     ponerlo, y así una dirección escrita por nosotros y esa misma dirección con los huecos puestos
 *     valen lo mismo (dos formas de decir lo mismo son dos entradas en el historial).
 *  2. **El nombre se lee en minúscula** (`?Campana=` es `campana`), por lo del teclado del móvil.
 *  3. **Repetido, gana el primero** (`?campana=2026&campana=2027` deja 2026), que es lo que hace
 *     `URLSearchParams`, que es con lo que se escriben las direcciones de verdad.
 *  4. **Lo que no conocemos no se tira**: se queda como texto. Un filtro que no entendemos es
 *     justamente lo que no hay que borrar en silencio.
 */
function leerLaConsulta(consulta) {
  const salida = {};
  if (typeof consulta !== "string" || consulta === "") return salida;
  for (const trozo of consulta.split("&")) {
    if (trozo === "") continue;
    const corte = trozo.indexOf("=");
    const nombre = desescapa(corte === -1 ? trozo : trozo.slice(0, corte))
      .trim()
      .toLocaleLowerCase("es");
    const valor = desescapa(corte === -1 ? "" : trozo.slice(corte + 1));
    if (nombre === "" || valor === "") continue;
    if (nombre in salida) continue;
    salida[nombre] = canonico(nombre, valor);
  }
  return salida;
}

/** ¿Encaja esta dirección con esta pantalla? Devuelve los parámetros de ruta, o `null`. */
function encajan(pantalla, tramos) {
  if (pantalla.patron.length !== tramos.length) return null;
  const salida = {};
  for (let i = 0; i < tramos.length; i++) {
    const esperado = pantalla.patron[i];
    if (esperado.startsWith(":")) {
      // El identificador de una ficha **tiene que ser un número entero**. Si no lo es, no es esta
      // pantalla (`#/tierras/abc` no es la ficha de una tierra, es una dirección que no existe).
      if (!esNumeroEntero(tramos[i])) return null;
      salida[esperado.slice(1)] = Number(tramos[i]);
    } else if (esperado !== tramos[i]) {
      return null;
    }
  }
  return salida;
}

/**
 * Lee una dirección: `{ pantalla, parametros, desconocida }`.
 *
 *  - `pantalla` es la clave de la tabla (`"inicio"`, `"tierras"`, `"tierra"`…).
 *  - `parametros` es un objeto con los parámetros de ruta (el `id`, **como número entero**) y los de
 *    consulta (`campana`, `finca`, `q`, `orden`, `sentido`…).
 *  - `desconocida` es `true` cuando la dirección no es de ninguna pantalla conocida **o cuando el
 *    identificador no es un número entero válido**. En ese caso `pantalla` va vacía y `parametros`
 *    también: el módulo no adivina media dirección.
 *
 * **Lo que este módulo NO puede saber, y por eso no lo dice:** si la tierra 12 existe o si es de este
 * agricultor. Eso lo decide el servidor (que contesta 404, y no 403, para no contar si existe en otra
 * finca). Aquí no hay ningún estado «no existe» ni «no es tuya»: inventarse uno sería enseñar un aviso
 * equivocado encima de un dato que sí existe.
 *
 * Nada de excepciones: una dirección rara devuelve `desconocida: true`, nunca revienta.
 */
export function leer(direccion) {
  const { camino, consulta } = partes(direccion);
  const deConsulta = leerLaConsulta(consulta);
  const tramos = camino
    .split("/")
    .filter((trozo) => trozo !== "")
    .map((trozo) => desescapa(trozo).toLocaleLowerCase("es"));
  for (const pantalla of PANTALLAS) {
    const deRuta = encajan(pantalla, tramos);
    if (deRuta) {
      // Los de la ruta mandan sobre los de la consulta con el mismo nombre: el identificador del camino
      // es el de la ficha que se está mirando, y `?id=` no puede cambiarlo desde fuera.
      return { pantalla: pantalla.clave, parametros: { ...deConsulta, ...deRuta }, desconocida: false };
    }
  }
  return { pantalla: "", parametros: {}, desconocida: true };
}

/** La consulta de una dirección: `campana=2026&q=El%20Prado`. Sin valores vacíos y en orden estable. */
function escribirLaConsulta(parametros, deRuta) {
  const trozos = [];
  // **En orden alfabético por el nombre**, y no en el orden en que los pase quien llama: dos direcciones
  // con los mismos filtros tienen que escribirse **igual**. Si no, el historial se llena de direcciones
  // distintas que llevan al mismo sitio, y «atrás» da dos pasos para volver a lo mismo.
  for (const nombre of Object.keys(parametros).sort()) {
    // El identificador ya viaja en el camino: escribirlo otra vez en la consulta sería una dirección con
    // dos verdades dentro.
    if (deRuta.includes(nombre)) continue;
    const valor = parametros[nombre];
    // Vacío o nulo **no se escribe**: un parámetro que no dice nada es un parámetro de más.
    if (valor === null || valor === undefined || valor === "") continue;
    const texto = String(canonico(nombre, String(valor)));
    if (texto === "") continue;
    trozos.push(`${encodeURIComponent(nombre)}=${encodeURIComponent(texto)}`);
  }
  return trozos.join("&");
}

/**
 * Escribe la dirección de una pantalla: `escribir("tierra", {id: 12, campana: 2026})` →
 * `"#/tierras/12?campana=2026"`.
 *
 * Cumple la **ida y la vuelta**: `leer(escribir(pantalla, parametros))` devuelve la misma pantalla y
 * los mismos parámetros, en su forma canónica (los números como números, los textos como textos, y los
 * valores vacíos fuera). Eso es lo que hace que se pueda recargar, enlazar y compartir una dirección.
 *
 * Devuelve `""` —y no una excepción— en dos casos que son un fallo de quien llama y no del agricultor:
 * una pantalla que no está en la tabla, y una ficha a la que le falta el identificador (o no es un
 * número). `""` no es una dirección: quien la reciba **no debe cambiar la barra de direcciones**, y
 * tiene `esConocida` para comprobarlo antes. Devolver `"#/"` en esos casos sería decir que la pantalla
 * existe, que es lo que no es verdad.
 */
export function escribir(pantalla, parametros = {}) {
  const tabla = PANTALLAS.find((una) => una.clave === pantalla);
  if (!tabla) return "";
  const datos = parametros || {};
  const tramos = [];
  const deRuta = [];
  for (const esperado of tabla.patron) {
    if (!esperado.startsWith(":")) {
      tramos.push(esperado);
      continue;
    }
    const nombre = esperado.slice(1);
    deRuta.push(nombre);
    const valor = datos[nombre];
    const texto = valor === null || valor === undefined ? "" : String(valor);
    if (!esNumeroEntero(texto)) return "";
    tramos.push(String(Number(texto)));
  }
  const consulta = escribirLaConsulta(datos, deRuta);
  return `#/${tramos.join("/")}${consulta ? `?${consulta}` : ""}`;
}

/** ¿Esta clave es una pantalla de la tabla? Sirve para no construir una dirección que no lleva a nada. */
export function esConocida(pantalla) {
  return PANTALLAS.some((una) => una.clave === pantalla);
}

/** Las claves de todas las pantallas, en el orden de la tabla. */
export function pantallas() {
  return PANTALLAS.map((una) => una.clave);
}

/** ¿Esta pantalla es una lista con buscador y orden (y por tanto con una vista que recordar)? */
export function esUnListado(pantalla) {
  return LISTADOS.includes(pantalla);
}

/**
 * La dirección de una ficha, para el enlace de una fila de la lista.
 *
 * Los parámetros que se le pasan **viajan con ella**: es lo que hace que volver de la ficha devuelva a
 * la lista con la campaña y los filtros que el agricultor tenía puestos (el `id` de la fila manda sobre
 * lo que venga en `parametros`, que es de donde sale la lista, no la ficha).
 */
export function enlaceDeTierra(id, parametros = {}) {
  return escribir("tierra", { ...(parametros || {}), id });
}

/** Lo mismo para un apunte del cuaderno: `#/cuaderno/34?campana=2026`. */
export function enlaceDeApunte(id, parametros = {}) {
  return escribir("apunte", { ...(parametros || {}), id });
}

/** La dirección de una vista (lo que devuelve `leer`), que es lo que se guarda para volver. */
export function direccionDe(vista) {
  const suya = vista || {};
  return escribir(suya.pantalla, suya.parametros);
}

/**
 * La memoria de las vistas: lo que hace que **volver del detalle no pierda los filtros**.
 *
 * POR QUÉ ES UNA FUNCIÓN Y NO UN ESTADO DE ESTE MÓDULO. Porque un estado guardado dentro del módulo no
 * se puede probar sin ensuciar las pruebas de al lado (una prueba deja la campaña 2026 apuntada y la
 * siguiente la encuentra puesta), y porque el día que haya dos listas abiertas —o una prueba que monte
 * la aplicación dos veces— las dos se pisarían. Aquí **la memoria la trae quien llama** y estas
 * funciones no la tocan: devuelven una copia nueva. `app.js` decide dónde vive (su `estado`).
 *
 * Lo que se guarda es una vista del tipo que devuelve `leer` (`{pantalla, parametros}`), pero este
 * módulo **no la interpreta**: guarda y devuelve lo que le den, para poder guardar también, si hace
 * falta, la página por la que iba o la fila que estaba elegida. Con `direccionDe` se vuelve a la
 * dirección.
 *
 * `null` (o nada) como vista **olvida** la clave: una vista vacía no es una vista.
 */
export function recuerda(memoria, clave, vista) {
  const copia = { ...(memoria || {}) };
  if (!clave) return copia;
  if (vista === null || vista === undefined) {
    delete copia[clave];
    return copia;
  }
  copia[clave] = vista;
  return copia;
}

/** La vista guardada, o `null` si no hay ninguna. Lo que no se ha guardado no existe. */
export function recupera(memoria, clave) {
  const guardada = (memoria || {})[clave];
  return guardada === undefined ? null : guardada;
}

/** La memoria sin esa vista. */
export function olvida(memoria, clave) {
  const copia = { ...(memoria || {}) };
  delete copia[clave];
  return copia;
}
