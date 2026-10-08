/**
 * Pruebas de las direcciones de la aplicación (`web/react/rutas.js`), sin navegador.
 *
 * POR QUÉ ESTAS PRUEBAS EXISTEN
 *
 * `rutas.js` es la pieza que traduce entre una dirección (`#/tierras/12?campana=2026`) y una pantalla. La
 * aceptación de T04 es exactamente eso: **abrir una ficha por su dirección, recargarla y volver
 * conservando la campaña y los filtros**. Si la traducción falla, no falla una pantalla: falla la forma de
 * llegar a todas, y el agricultor se queda mirando una pantalla que no es la que ha pedido, sin ningún
 * aviso.
 *
 * Por eso aquí no se prueba «que la función devuelva algo», se prueba **el contrato**, y cada prueba dice
 * en su comentario qué se rompe si falla:
 *
 *  1. que la dirección de la pantalla de inicio sea una y no cuatro;
 *  2. que el identificador de una ficha salga **como número** (si saliera como texto, `12 === "12"` sería
 *     falso y la ficha que se pide no sería la que se enseña);
 *  3. que una dirección desconocida se diga desconocida **sin reventar**, porque esto lo llama el arranque
 *     de la aplicación y un fallo aquí deja la pantalla en blanco;
 *  4. que la **ida y la vuelta** cuadren en las 25 pantallas de la tabla, con acentos y con espacios;
 *  5. que dos direcciones con los mismos filtros se escriban **igual** (si no, el historial se llena de
 *     direcciones distintas que llevan al mismo sitio);
 *  6. que la memoria de la vista de un listado guarde, devuelva y olvide, sin estado escondido dentro del
 *     módulo;
 *  7. y que el módulo **no toque el navegador**: ni `window`, ni `document`, ni `history`, ni `fetch`.
 *
 * **Y una que es una decisión, no una comprobación** (T04, segunda entrega): que **un paso de un formulario
 * no tenga dirección**. El asistente de apuntar, «lo he apuntado», la pantalla de entrar, el alta de un
 * papel y el alta de una factura **no están en la tabla a propósito** —lo que llevan dentro vive en la
 * memoria de la sesión y no se puede reproducir—, y aquí se comprueba que no están, para que nadie las
 * añada «por completitud» sin leer el porqué (ver el comentario de la tabla, en `rutas.js`).
 *
 * LO QUE ESTAS PRUEBAS NO COMPRUEBAN, Y SE DICE
 *
 *  - **No comprueban que el servidor tenga esa tierra**, ni que sea suya: eso lo decide el servidor (que
 *    contesta 404, y no 403, para no contar si el identificador existe en otra finca). Aquí no se inventa
 *    ningún estado «no existe» justo por eso.
 *  - **No comprueban el cableado**: que `app.js` escuche los cambios de la barra de direcciones y vuelva a
 *    pintar. El módulo es puro a propósito y quien habla con el navegador es `app.js`.
 *  - **No son la aceptación de T04**: falta el recorrido completo en un navegador de verdad (abrir una
 *    ficha, recargar y volver), que es lo que se hace con `scripts/comprobar_en_un_navegador.py`.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

import {
  LISTADOS,
  direccionDe,
  enlaceDeApunte,
  enlaceDeTierra,
  esConocida,
  esUnListado,
  escribir,
  leer,
  olvida,
  pantallas,
  recuerda,
  recupera,
} from "../web/react/rutas.js";

// ---------------------------------------------------------------------------
// La pantalla de inicio
// ---------------------------------------------------------------------------

test("la pantalla de inicio es la dirección vacía, escrita de las cuatro formas", () => {
  // Si esto fallara, entrar en la aplicación daría una dirección «desconocida»: la barra de direcciones
  // queda en «#» en cuanto se toca algo, y al recargar el agricultor se encontraría un aviso en vez de su
  // pantalla de inicio.
  for (const direccion of ["", "#", "#/", "/"]) {
    const leida = leer(direccion);
    assert.equal(leida.pantalla, "inicio", `«${direccion}» no es la pantalla de inicio`);
    assert.equal(leida.desconocida, false, `«${direccion}» se ha leído como desconocida`);
    assert.deepEqual(leida.parametros, {});
  }
});

test("el inicio también se escribe siempre igual", () => {
  // Una sola forma de escribir el inicio: si hubiera dos («#» y «#/»), dos pulsaciones seguidas del botón
  // de inicio llenarían el historial de direcciones distintas que llevan al mismo sitio.
  assert.equal(escribir("inicio"), "#/");
  assert.equal(escribir("inicio", {}), "#/");
  assert.equal(escribir("inicio", { campana: null, q: "" }), "#/");
  assert.equal(leer(escribir("inicio")).pantalla, "inicio");
});

test("lo que no es una dirección se lee como la dirección vacía", () => {
  // Esto lo llama el arranque de la aplicación con lo que haya en la barra de direcciones. Si llegara
  // `undefined` (una versión vieja del navegador, una llamada a medias), lo último que se puede hacer es
  // reventar: se enseña el inicio, que es donde estaba el agricultor.
  for (const nada of [null, undefined, 42, {}, [], true]) {
    const leida = leer(nada);
    assert.equal(leida.pantalla, "inicio", `${JSON.stringify(nada)} no se lee como el inicio`);
    assert.equal(leida.desconocida, false);
  }
});

// ---------------------------------------------------------------------------
// La ficha de una tierra: la aceptación de T04
// ---------------------------------------------------------------------------

test("la ficha de una tierra se lee con su identificador, su campaña y su finca", () => {
  const leida = leer("#/tierras/12?campana=2026&finca=3");
  assert.equal(leida.pantalla, "tierra");
  assert.equal(leida.desconocida, false);
  // El identificador sale como NÚMERO, y esto es lo que más se rompe de todo el módulo: con el `id` como
  // texto, la comparación con el de la tierra que trae el servidor es falsa, y la pantalla abriría la
  // ficha de ninguna tierra (o de la primera) sin decir nada.
  assert.equal(leida.parametros.id, 12);
  assert.equal(typeof leida.parametros.id, "number");
  // La campaña y la finca son identificadores: también salen como número, por el mismo motivo (el año que
  // se está llevando en `app.js` es un número, y `2026 === "2026"` es falso: el filtro no se aplicaría).
  assert.equal(leida.parametros.campana, 2026);
  assert.equal(leida.parametros.finca, 3);
});

test("la ficha se lee igual con barra final, sin ella y sin parámetros", () => {
  for (const direccion of ["#/tierras/12", "#/tierras/12/", "#/tierras//12"]) {
    const leida = leer(direccion);
    assert.equal(leida.pantalla, "tierra", `«${direccion}» no se lee como la ficha de una tierra`);
    assert.deepEqual(leida.parametros, { id: 12 });
  }
});

test("una dirección escrita sin la almohadilla también se entiende", () => {
  // Por si acaso: un enlace que se copia de la barra de direcciones puede llegar sin el `#` (por ejemplo,
  // pegado a mano quince veces). Lo que no llegue al servidor es cosa del navegador, no nuestra.
  const leida = leer("/tierras/12");
  assert.equal(leida.pantalla, "tierra");
  assert.deepEqual(leida.parametros, { id: 12 });
  assert.deepEqual(leer("/tierras").parametros, {});
  assert.equal(leer("/tierras").pantalla, "tierras");
});

test("la ficha de una tierra no se confunde con la lista de tierras", () => {
  // Dos pantallas distintas con direcciones distintas: si la lista se leyera como una ficha (o al revés),
  // entrar en «Mis tierras» abriría la ficha de la tierra número 0, que no existe.
  assert.equal(leer("#/tierras").pantalla, "tierras");
  assert.equal(leer("#/tierras").desconocida, false);
  assert.equal(leer("#/tierras/12").pantalla, "tierra");
  // Un tramo vacío al final **no es un identificador**: `#/cuaderno/` es la lista del cuaderno escrita con
  // una barra de más, no el apunte número «nada».
  assert.equal(leer("#/cuaderno/").pantalla, "cuaderno");
  assert.equal(leer("#/cuaderno/").desconocida, false);
  // Y un apunte del cuaderno es otra pareja igual.
  assert.equal(leer("#/cuaderno").pantalla, "cuaderno");
  assert.equal(leer("#/cuaderno/34").pantalla, "apunte");
  assert.equal(leer("#/cuaderno/34").parametros.id, 34);
});

test("los ceros de delante no cambian de qué tierra se habla", () => {
  // `#/tierras/012` es la tierra 12: la dirección es la misma cosa escrita de otra forma, y el módulo la
  // deja en su forma de siempre para que dos direcciones no parezcan dos fichas.
  const leida = leer("#/tierras/012");
  assert.equal(leida.pantalla, "tierra");
  assert.equal(leida.parametros.id, 12);
  assert.equal(escribir("tierra", { id: "012" }), "#/tierras/12");
});

// ---------------------------------------------------------------------------
// Lo que no conocemos: nunca una excepción
// ---------------------------------------------------------------------------

test("una dirección que no es de ninguna pantalla se dice desconocida, y no revienta", () => {
  const leida = leer("#/lo-que-sea");
  assert.equal(leida.desconocida, true);
  // Y no adivina media dirección: ni una pantalla a medias ni unos parámetros a medias.
  assert.equal(leida.pantalla, "");
  assert.deepEqual(leida.parametros, {});
});

test("un identificador que no es un número no es la ficha de nadie", () => {
  // Esto **no** es lo mismo que «esa tierra no existe», y la diferencia importa: si aquí se inventara un
  // estado de error, la pantalla diría «esa tierra no es tuya» de una dirección que simplemente está mal
  // escrita. Lo que no es un número entero no es una ficha: es una dirección desconocida.
  for (const mala of [
    "#/tierras/abc",
    "#/tierras/1.5",
    "#/tierras/-3",
    "#/tierras/12a",
    "#/tierras/0x12",
    "#/tierras/1 2",
    "#/cuaderno/abc",
    "#/cuaderno/1.5",
    "#/cuaderno/12/13",
  ]) {
    const leida = leer(mala);
    assert.equal(leida.desconocida, true, `«${mala}» debería ser una dirección desconocida`);
    assert.equal(leida.pantalla, "");
  }
});

test("una dirección rarísima se contesta que es desconocida, sin lanzar nada", () => {
  // Aquí está el motivo de que este módulo no lance nunca: lo llama el arranque de la aplicación, así que
  // una excepción con una dirección rara no es «una dirección que no se entiende», es **la aplicación que
  // no arranca** y un agricultor delante de una pantalla en blanco.
  for (const rara of [
    "#/tierras/%E0%A4%A", // un tanto por ciento que no es una dirección válida
    "#/tierras/12?campana=%E0%A4%A",
    "#%%%",
    "#/",
    "###",
    "#?",
    "#/tierras/12?&=&=x",
  ]) {
    const leida = leer(rara);
    assert.equal(typeof leida.desconocida, "boolean", `«${rara}» no se ha podido leer`);
    assert.equal(typeof leida.pantalla, "string");
    assert.equal(typeof leida.parametros, "object");
  }
});

// ---------------------------------------------------------------------------
// La ida y la vuelta, en todas las pantallas
// ---------------------------------------------------------------------------

test("la ida y la vuelta cuadra en todas las pantallas de la tabla", () => {
  // **Este es el contrato del módulo.** Si fallara en una sola pantalla, esa pantalla no se podría
  // recargar ni enlazar, que es justo la aceptación de T04 («abrir una ficha por URL, recargarla y volver
  // conservando campaña y filtros»). Se prueban todas, con el identificador de la ficha y con los
  // parámetros de la lista, porque son los dos caminos que existen.
  const identificadores = {
    tierra: { id: 12 },
    // T06 (03/10/2026): lo que ha sido una tierra. Lleva su identificador en el camino, como la ficha
    // de la tierra de la que es: sin él no tiene dirección (es la ficha de nada).
    tierra_versiones: { id: 12 },
    apunte: { id: 34 },
    // Las dos direcciones nuevas que llevan identificador en el camino: la tierra de la que se está
    // diciendo el cultivo y la factura que se está revisando. Sin él no tienen dirección (hay prueba
    // propia más abajo), así que van aquí para que la ida y la vuelta se compruebe con su forma completa.
    decir_cultivo: { id: 12 },
    interpretacion_factura: { id: 7 },
    // Y la ficha de un albarán (T09): su identificador va en el camino, así que se comprueba con su forma
    // completa. Sin él no tiene dirección (hay prueba propia más abajo), igual que una tierra.
    recepcion: { id: 5 },
    // T12 (03/10/2026): la ficha de una factura nuestra y las dos pantallas de una entrega (su importe y
    // su ajuste). Las tres llevan su identificador en el camino, así que se comprueban con su forma
    // completa; sin él no tienen dirección (hay prueba propia más abajo), igual que una tierra.
    factura_emitida: { id: 7 },
    venta_importe: { id: 4 },
    venta_ajuste: { id: 4 },
    // T14 (03/10/2026): la ficha de una máquina. Su identificador va en el camino, así que se comprueba
    // con su forma completa; sin él no tiene dirección (hay prueba propia más abajo), igual que una tierra.
    maquina: { id: 12 },
    // T13 (05/10/2026): la ficha de un gasto. Su identificador va en el camino, así que se comprueba con
    // su forma completa; sin él no tiene dirección (hay prueba propia más abajo), igual que una tierra.
    gasto: { id: 12 },
    // T15 (05/10/2026): la historia de una tierra. Como las demás fichas, su identificador va en el
    // camino; sin él no tiene dirección (lo comprueba la prueba de abajo, con `trabajo_tierra`).
    trabajo_tierra: { id: 12 },
    // T20 (05/10/2026): la ficha de un movimiento del banco, dentro de la familia de las cuentas.
    banco_movimiento: { id: 5 },
    // T08 (06/10/2026): la ficha de un papel de la bandeja, dentro de la familia de los papeles. Su
    // identificador va en el camino, igual que en las demás fichas; sin él no tiene dirección (lo
    // comprueba la prueba de abajo, con la lista de las que no la tienen sin su identificador).
    bandeja_papel: { id: 12 },
  };
  for (const pantalla of pantallas()) {
    const parametros = {
      ...(identificadores[pantalla] || {}),
      campana: 2026,
      finca: 3,
      q: "El Prado",
      orden: "numero",
      sentido: -1,
    };
    const direccion = escribir(pantalla, parametros);
    assert.ok(direccion.startsWith("#/"), `la dirección de ${pantalla} no empieza por «#/»`);
    const leida = leer(direccion);
    assert.equal(leida.desconocida, false, `«${direccion}» no se entiende`);
    assert.equal(leida.pantalla, pantalla, `«${direccion}» no vuelve a ${pantalla}`);
    assert.deepEqual(leida.parametros, parametros, `la ida y la vuelta cambia los datos de ${pantalla}`);
  }
});

test("la tabla de pantallas es la que es, y no se ha quedado corta", () => {
  // Las 13 claves del menú, el inicio, las fichas que salen de sus listas y las siete pantallas que
  // estrenaron dirección en la segunda entrega de T04. Si alguien añade un módulo al menú y no le pone
  // dirección, aquí se ve: sin dirección no hay enlace que mandar a nadie.
  //
  // **Y si alguien mete aquí un paso de un formulario, esto también se ve**: el asistente, «lo he apuntado»,
  // la pantalla de entrar y las dos altas (un papel y una factura) **no tienen dirección a propósito**
  // (hay una prueba propia para eso, aquí debajo). Una lista que creciera sola perdería esa decisión.
  assert.deepEqual(pantallas(), [
    "inicio",
    "tierras",
    // **Los trabajos (T15, 05/10/2026)**: la agenda (`#/trabajos`) y la historia de una tierra
    // (`#/tierras/<id>/historial`). Las dos piden sus datos al servidor al abrir su dirección, así que
    // se pueden enlazar, recargar y mandar a quien ayuda. **La ficha de un trabajo no tiene dirección a
    // propósito**: es un formulario, y uno que al recargar saldría vacío es peor que no tenerla.
    "trabajos",
    "trabajo_tierra",
    // T06 (03/10/2026): las tierras en el mapa y en la tabla, y lo que ha sido una tierra. Las dos se
    // reconstruyen enteras al abrir su dirección (la primera pide `/api/parcelas/vista` y la segunda
    // las versiones de esa tierra), así que las dos tienen dirección propia.
    "tierras_mapa",
    "tierra",
    "tierra_versiones",
    // **La búsqueda global** (07/10/2026, del encargo del rediseño): tiene dirección propia
    // (`#/buscar?texto=…`) porque **se puede enlazar y recargar** — lo que se busca viaja en la dirección,
    // que es lo que hace que volver a ella deje al agricultor donde estaba. Se apunta aquí por el mismo
    // motivo que las demás: esta lista es la que vigila que una pantalla nueva no se quede sin dirección.
    "buscar",
    "decir_cultivo",
    "cuaderno",
    "firmar",
    "apunte",
    "almacen",
    // T09 (03/10/2026): el libro del almacén y la ficha de un albarán. Son un sitio al que se vuelve —la
    // lista y la ficha—, así que tienen dirección: se pueden enlazar y recargar, y el botón «atrás» del
    // móvil vuelve a la lista en vez de sacar de la aplicación. Sus cuatro formularios (apuntar un
    // albarán, una merma, sacar de un envase y decir de qué factura es) **no la tienen a propósito**, y
    // la prueba de abajo lo comprueba.
    "libro_almacen",
    "recepcion",
    // T10/T15 (03/10/2026, del otro agente): las semillas y lo que hay sembrado. Se apuntan aquí
    // porque **este fichero es de T06** y esta lista es la que impide que una pantalla nueva se quede
    // sin dirección sin que nadie se entere; la prueba que las vigila es esta, así que la mantenemos
    // entre los dos.
    "semillas",
    "siembras",
    // T11 (03/10/2026): las personas y las empresas y la revisión de los nombres que ya están escritos.
    // Las dos se reconstruyen enteras al abrir su dirección —piden sus datos al servidor—, así que se
    // pueden enlazar, recargar y mandar a quien ayuda. La revisión **tiene que poder recargarse**: es
    // una decisión sobre datos, y volver a mirarla después de pensarlo es lo normal. La ficha de un
    // contacto y la lista para enlazar un nombre escrito **no tienen dirección a propósito** (son
    // formularios), y la prueba de abajo lo comprueba.
    "contactos",
    "revisar_contactos",
    "facturas",
    "interpretacion_factura",
    "anos",
    "grupos",
    "cultivos",
    "analisis",
    "plan",
    "ventas",
    // T12 (03/10/2026): el dinero de lo que se vende. La factura nuestra (la lista y la ficha), juntar
    // entregas en una factura, los cobros y las dos pantallas de una entrega (ponerle el importe y
    // apuntarle una devolución o un ajuste). **Las cinco se reconstruyen enteras al abrir su dirección**
    // —piden sus datos al servidor—, así que se pueden enlazar y recargar. Las dos que no la tienen son
    // formularios y están en la prueba de abajo: juntar entregas y apuntar un cobro.
    "facturas_emitidas",
    "facturar_entregas",
    "cobros",
    "cobro_nuevo",
    "factura_emitida",
    "venta_importe",
    "venta_ajuste",
    // T13 (05/10/2026): las cuentas de la explotación. La lista se reconstruye entera al abrir su
    // dirección —pide sus datos al servidor— y **la ficha de un gasto también** (se pide a su puerta),
    // así que las dos se pueden enlazar, recargar y mandar a quien ayuda. Los formularios de las cuentas
    // (apuntar un gasto, repartirlo, apuntar un pago, una inversión y una ayuda) **no tienen dirección a
    // propósito**: son formularios que al recargar saldrían vacíos. El tramo de texto fijo va antes que
    // el identificador, como en todas las familias de esta tabla, y las dos van **detrás de las ventas y
    // delante de las medidas**, que es donde el informe del ticket las pone.
    "gastos",
    // **El banco y los papeles (T20, 05/10/2026)**: los movimientos del extracto (`#/cuentas/bancos`) y la
    // ficha de uno (`#/cuentas/bancos/12`), donde se dice contra qué papel va el dinero. Las dos piden sus
    // datos al servidor al abrir su dirección, así que se pueden enlazar y recargar. Van **con las cuentas**
    // y no en un renglón propio del menú porque S14 es una sección de las cuentas (el contrato la dibuja
    // dentro de `/cuentas`), y **sus formularios no tienen dirección a propósito**: al recargar saldrían
    // vacíos. El tramo de texto fijo (`bancos`) va antes que el identificador, como en todas las familias
    // —y por eso van **antes** de `gasto` (`:id`)—.
    "bancos",
    "banco_movimiento",
    "gasto",
    "medidas",
    // T14 (03/10/2026): la maquinaria y la ficha de una máquina. Las dos piden sus datos al servidor al
    // abrir su dirección —la ficha, a su puerta—, así que se pueden enlazar, recargar y mandar a quien
    // ayuda. **Los tres formularios de la maquinaria** (apuntar una máquina, una inspección y una avería)
    // **no tienen dirección a propósito**: son formularios que al recargar saldrían vacíos, y un
    // formulario vacío que parece guardado es peor que no tener dirección.
    "maquinaria",
    "maquina",
    "papeles",
    // **La bandeja documental (T08, 06/10/2026)**: lo que llega y hay que revisar (`#/papeles/bandeja`) y
    // la ficha de un papel (`#/papeles/bandeja/12`), donde se mira el original con la propuesta al lado y
    // se confirma. Las dos piden sus datos al servidor al abrir su dirección, así que se pueden enlazar y
    // recargar. Van **con los papeles** porque la bandeja es la mesa de la entrada y «los papeles» es el
    // armario: es la misma familia, y el contrato la dibuja dentro de `/papeles`. **Sus formularios no
    // tienen dirección a propósito** (la revisión de lo que queda y la comprobación del fichero que se
    // está subiendo): al recargar saldrían vacíos. El tramo de texto fijo (`bandeja`) va **antes** que el
    // identificador, como en todas las familias —y por eso van **antes** de nada más dentro de `papeles`—.
    "bandeja",
    "bandeja_papel",
    "junta",
    "datos",
    "quien_entra",
    "ayuda",
    "mapa",
    "dictado",
    "borrador",
  ]);
  assert.equal(new Set(pantallas()).size, pantallas().length, "hay una pantalla repetida en la tabla");
});

test("una pantalla que no está en la tabla no tiene dirección, y eso no revienta", () => {
  // Devolver `#/` aquí sería decir que esa pantalla existe. Lo que se devuelve es «no hay dirección», y
  // quien la pida **no debe tocar la barra de direcciones**.
  assert.equal(escribir("lo-que-sea", {}), "");
  assert.equal(escribir("tierras/12", {}), "");
  assert.equal(escribir("", {}), "");
  // Y una ficha sin identificador (o con uno que no es un número) tampoco tiene dirección: apuntar a la
  // ficha de «nada» es peor que no apuntar a ninguna.
  assert.equal(escribir("tierra", {}), "");
  assert.equal(escribir("tierra", { id: "" }), "");
  assert.equal(escribir("tierra", { id: "abc" }), "");
  assert.equal(escribir("apunte", { id: null }), "");
  // Lo que sí se puede preguntar antes de escribirla.
  assert.equal(esConocida("tierra"), true);
  assert.equal(esConocida("tierras/12"), false);
  assert.equal(esConocida(""), false);
});

test("el enlace de una fila de la lista lleva al identificador de esa fila", () => {
  // Es lo que necesita `app.js` para que el nombre de una tierra de la tabla sea un enlace de verdad, con
  // su campaña y sus filtros dentro, que es lo que hace que al volver no se pierda nada.
  assert.equal(enlaceDeTierra(12), "#/tierras/12");
  assert.equal(enlaceDeTierra(12, { campana: 2026, q: "El Prado" }), "#/tierras/12?campana=2026&q=El%20Prado");
  assert.equal(enlaceDeApunte(34, { campana: 2026 }), "#/cuaderno/34?campana=2026");
  // El identificador de la fila manda sobre lo que venga en los parámetros de la lista.
  assert.equal(enlaceDeTierra(12, { id: 99 }), "#/tierras/12");
  assert.equal(leer(enlaceDeTierra(12, { campana: 2026 })).parametros.id, 12);
});

// ---------------------------------------------------------------------------
// Las direcciones de la segunda entrega de T04
//
// Trece pantallas no tenían dirección. De esas trece, siete **la estrenan aquí** —las que se pueden querer
// enlazar o volver a ellas— y seis se quedan **sin ella a propósito**, porque son pasos de un formulario
// (hay prueba para las dos cosas, y cada una dice qué se rompe si falla).
// ---------------------------------------------------------------------------

test("decir qué hay sembrado lleva la dirección de esa tierra", () => {
  // **Es lo primero que se echa en falta**: decir el cultivo es de una tierra concreta, y con la dirección
  // de la lista (`#/cultivos`) recargar dejaba al agricultor en la lista y tenía que volver a buscar cuál de
  // sus 51 tierras era. Con el identificador en el camino, el enlace se puede mandar y recargar.
  const leida = leer("#/tierras/12/cultivo");
  assert.equal(leida.pantalla, "decir_cultivo", "no se lee como «decir el cultivo»");
  assert.equal(leida.desconocida, false);
  assert.equal(leida.parametros.id, 12, "no se sabe de qué tierra se está diciendo");
  assert.equal(typeof leida.parametros.id, "number", "el identificador de la tierra sale como texto");
  // No se confunde con las otras dos pantallas de las tierras.
  assert.equal(leer("#/tierras/12").pantalla, "tierra");
  assert.equal(leer("#/tierras").pantalla, "tierras");
  assert.equal(leer("#/cultivos").pantalla, "cultivos");
  // Y se escribe con la campaña y la finca dentro, como todas.
  assert.equal(
    escribir("decir_cultivo", { id: 12, campana: 2026, finca: 3 }),
    "#/tierras/12/cultivo?campana=2026&finca=3",
  );
});

test("decir el cultivo aguanta lo que un agricultor escribe de verdad", () => {
  // Las cuatro formas que se cuelan siempre: sin la almohadilla, con barra de más, en mayúsculas (el
  // teclado del móvil pone la primera letra en mayúscula) y con el buscador puesto.
  for (const direccion of ["/tierras/12/cultivo", "#/tierras/12/cultivo/", "#/Tierras/12/Cultivo"]) {
    const leida = leer(direccion);
    assert.equal(leida.pantalla, "decir_cultivo", `«${direccion}» no se entiende`);
    assert.deepEqual(leida.parametros, { id: 12 }, `«${direccion}» no lleva a la tierra 12`);
  }
  const conFiltro = leer("#/tierras/2/cultivo?q=Pe%C3%B1aranda&campana=2026");
  assert.deepEqual(conFiltro.parametros, { id: 2, campana: 2026, q: "Peñaranda" });
  assert.equal(escribir("decir_cultivo", conFiltro.parametros), "#/tierras/2/cultivo?campana=2026&q=Pe%C3%B1aranda");
  // Y sin identificador (o con uno que no es un número) no hay dirección que escribir: apuntar a la tierra
  // «de nada» es peor que no apuntar a ninguna, y deja al agricultor en «no lleva a ninguna parte» en vez
  // de en una pantalla que no es.
  assert.equal(escribir("decir_cultivo", {}), "");
  assert.equal(escribir("decir_cultivo", { id: "" }), "");
  assert.equal(escribir("decir_cultivo", { id: "abc" }), "");
  assert.equal(escribir("decir_cultivo", { id: 12.5 }), "");
});

test("una dirección de decir el cultivo con tramos de más no es esa pantalla", () => {
  // Un identificador que no es un número, un tramo de más y una palabra que no es «cultivo»: nada de eso
  // es la pantalla de una tierra, y decir que sí abriría la ficha de ninguna tierra sin avisar.
  for (const mala of [
    "#/tierras/abc/cultivo",
    "#/tierras/1.5/cultivo",
    "#/tierras/-3/cultivo",
    "#/tierras/12a/cultivo",
    "#/tierras//cultivo",
    "#/tierras/12/cultivo/13",
    "#/tierras/12/lo-que-sea",
    "#/cultivos/12/cultivo",
  ]) {
    const leida = leer(mala);
    assert.equal(leida.desconocida, true, `«${mala}» debería ser una dirección desconocida`);
    assert.equal(leida.pantalla, "");
    assert.deepEqual(leida.parametros, {});
  }
});

test("revisar una factura guardada lleva la dirección de esa factura", () => {
  // La pantalla que confirma lo que se ha leído de una foto **y** la que corrige una factura guardada son
  // la misma. La guardada sí tiene dirección: se vuelve a armar con lo que hay en el cuaderno. Es lo que
  // hace que se pueda mandar a alguien «mira esta factura» y que recargar no devuelva a la lista.
  const leida = leer("#/facturas/9");
  assert.equal(leida.pantalla, "interpretacion_factura");
  assert.equal(leida.parametros.id, 9);
  assert.equal(typeof leida.parametros.id, "number");
  assert.equal(leer("#/facturas").pantalla, "facturas", "la lista de facturas ha dejado de ser la lista");
  assert.equal(
    escribir("interpretacion_factura", { id: 9, campana: 2026 }),
    "#/facturas/9?campana=2026",
  );
  // Sin identificador no hay dirección (la lectura de una foto no está guardada en ningún sitio).
  assert.equal(escribir("interpretacion_factura", {}), "");
  assert.equal(escribir("interpretacion_factura", { id: null }), "");
  assert.equal(escribir("interpretacion_factura", { id: "abc" }), "");
  // Y lo que no es una factura no es esa pantalla.
  for (const mala of ["#/facturas/abc", "#/facturas/1.5", "#/facturas/-9", "#/facturas/9/10"]) {
    assert.equal(leer(mala).desconocida, true, `«${mala}» debería ser una dirección desconocida`);
  }
});

test("quién entra cuelga de mis datos, y firmar del cuaderno", () => {
  // Las dos son destinos de otra pantalla (quién entra, de «mis datos»; firmar, del cuaderno) y no pasos de
  // nada: su dirección se puede mandar y volver a ella.
  const quien = leer("#/datos/quien-entra");
  assert.equal(quien.pantalla, "quien_entra");
  assert.deepEqual(quien.parametros, {});
  assert.equal(escribir("quien_entra", {}), "#/datos/quien-entra");
  assert.equal(leer("#/datos").pantalla, "datos", "«datos» ha dejado de ser mis datos");
  // Y el nombre del camino se lee como lo escribe un humano (con mayúsculas: el móvil las pone solo).
  assert.equal(leer("#/Datos/Quien-Entra").pantalla, "quien_entra");

  // Firmar: un tramo de texto fijo dentro del cuaderno. Lo que importa aquí es que **no se confunda con un
  // apunte**: `#/cuaderno/firmar` no es el apunte número «firmar», ni `#/cuaderno/34` es la pantalla de
  // firmar. Confundirlos abriría un apunte que no existe (o la firma en vez del apunte 34).
  const firma = leer("#/cuaderno/firmar");
  assert.equal(firma.pantalla, "firmar");
  assert.deepEqual(firma.parametros, {});
  assert.equal(leer("#/cuaderno/34").pantalla, "apunte");
  assert.equal(leer("#/cuaderno").pantalla, "cuaderno");
  assert.equal(escribir("firmar", { campana: 2026 }), "#/cuaderno/firmar?campana=2026");
  // Lo que no es ninguna de las dos cosas, tampoco.
  for (const mala of ["#/datos/lo-que-sea", "#/datos/quien-entra/1", "#/cuaderno/firmar/1", "#/cuaderno/34/firmar"]) {
    assert.equal(leer(mala).desconocida, true, `«${mala}» debería ser una dirección desconocida`);
  }
});

test("el mapa, el dictado y el borrador tienen su nombre y su dirección", () => {
  // Las tres se abren desde otra pantalla (el mapa, desde el alta de una parcela; el dictado, desde el
  // inicio) y ninguna está en el menú. Volver a su dirección las reconstruye: el mapa se centra solo y el
  // dictado enseña lo que ya se había contado.
  for (const [clave, direccion] of [
    ["mapa", "#/mapa"],
    ["dictado", "#/dictado"],
    ["borrador", "#/borrador"],
  ]) {
    assert.equal(leer(direccion).pantalla, clave, `«${direccion}» no se lee como ${clave}`);
    assert.equal(leer(direccion).desconocida, false);
    assert.equal(escribir(clave, {}), direccion, `«${clave}» no se escribe siempre igual`);
    assert.equal(leer("#/" + clave.toUpperCase()).pantalla, clave, `«${clave}» no aguanta mayúsculas`);
  }
  // Con la campaña y la finca dentro, como todas.
  assert.equal(escribir("mapa", { campana: 2026, finca: 3 }), "#/mapa?campana=2026&finca=3");
  // Y nada de media dirección: un tramo de más no es esa pantalla.
  for (const mala of ["#/mapa/12", "#/dictado/1", "#/borrador/x", "#/mapa/mapa"]) {
    assert.equal(leer(mala).desconocida, true, `«${mala}» debería ser una dirección desconocida`);
  }
});

test("un paso de un formulario no tiene dirección, y eso es una decisión", () => {
  // **Esta prueba defiende una decisión, no un cálculo.** El asistente de apuntar (65 pasos), «lo he
  // apuntado», la pantalla de entrar, el alta de un papel y el alta de una factura son **pasos**: lo que
  // llevan escrito vive en la memoria de la sesión (o es la confirmación de algo que se acaba de guardar) y
  // una dirección que al recargar deja al agricultor en un formulario a medias —o vacío, creyendo que ya
  // había guardado— es peor que no tenerla. Si alguien les añadiera una dirección «por completitud», el
  // agricultor que recargara en mitad de un apunte se encontraría otra cosa, y sin aviso.
  for (const paso of ["asistente", "hecho", "entrar", "nuevo_documento", "nueva_factura", "traer_del_sigpac"]) {
    assert.equal(esConocida(paso), false, `«${paso}» es un paso y no debería tener dirección`);
    assert.equal(escribir(paso, { tipo: "tratamiento" }), "", `«${paso}» ha escrito una dirección`);
  }
  // Y por el otro lado: escribirlas a mano **no lleva a ninguna parte**, y se dice con `desconocida` en vez
  // de adivinar a qué pantalla podrían referirse.
  for (const inventada of ["#/apuntar", "#/hecho", "#/entrar", "#/papeles/nuevo", "#/facturas/nueva"]) {
    assert.equal(leer(inventada).desconocida, true, `«${inventada}» no debería llevar a ninguna pantalla`);
  }
});

// ---------------------------------------------------------------------------
// Acentos, espacios, vacíos y orden
// ---------------------------------------------------------------------------

test("los acentos y los espacios de un filtro sobreviven a la ida y a la vuelta", () => {
  // Un buscador con «Peñaranda de Bracamonte» es el caso normal, no el raro: medio pueblo tiene tilde o
  // eñe. Si la ida y la vuelta lo estropeara, el agricultor buscaría su pueblo y la lista le saldría
  // vacía sin decirle por qué.
  const direccion = escribir("tierras", { q: "Peñaranda de Bracamonte" });
  assert.equal(direccion, "#/tierras?q=Pe%C3%B1aranda%20de%20Bracamonte");
  assert.equal(leer(direccion).parametros.q, "Peñaranda de Bracamonte");
  // Y lo que de verdad rompe a un montón de programas: una `&`, un `=` y una `#` dentro del valor.
  const dificil = "Prado & Vega = 3 #2";
  assert.equal(leer(escribir("tierras", { q: dificil })).parametros.q, dificil);
  // Y con el nombre de una tierra tal cual, que es como lo escribe el agricultor.
  const nombre = "La tierra de El Prado (Peñaranda)";
  assert.equal(leer(escribir("tierra", { id: 12, q: nombre })).parametros.q, nombre);
});

test("un filtro vacío no se escribe, y no hay dos direcciones para lo mismo", () => {
  // Un filtro en blanco es no tener filtro. Escribiendo `?q=&orden=` el historial tendría dos direcciones
  // que llevan al mismo sitio, y «atrás» daría dos pasos para volver a lo mismo.
  assert.equal(escribir("tierras", { q: "" }), "#/tierras");
  assert.equal(escribir("tierras", { q: null }), "#/tierras");
  assert.equal(escribir("tierras", { q: undefined }), "#/tierras");
  assert.equal(escribir("tierras", { q: "", orden: null, campana: undefined }), "#/tierras");
  assert.equal(escribir("tierras", { q: "", orden: "numero" }), "#/tierras?orden=numero");
  // Y al leer, un parámetro vacío es como no estar (lo mismo dicho al revés).
  assert.deepEqual(leer("#/tierras?campana=&q=&orden=").parametros, {});
  assert.deepEqual(leer("#/tierras?campana").parametros, {});
});

test("el orden de los parámetros es estable, se pasen como se pasen", () => {
  // Si el orden dependiera de cómo se llamó, dos direcciones con los mismos filtros se verían distintas:
  // el historial se llenaría de duplicados y el agricultor vería direcciones que no sabe si son la misma.
  const una = escribir("tierra", { id: 12, q: "El Prado", campana: 2026, finca: 3 });
  const otra = escribir("tierra", { finca: 3, campana: 2026, q: "El Prado", id: 12 });
  assert.equal(una, otra);
  assert.equal(una, "#/tierras/12?campana=2026&finca=3&q=El%20Prado");
  // Y no lleva el identificador dos veces (en el camino y en la consulta): una dirección con dos
  // verdades dentro es una dirección que no se sabe leer.
  assert.doesNotMatch(una, /\?.*id=/);
});

test("el parámetro repetido no inventa una lista: gana el primero, como el navegador", () => {
  // `URLSearchParams` —que es con lo que se escriben las direcciones de verdad— devuelve el primero. Aquí
  // se hace lo mismo, y se dice, para que no haya dos reglas.
  assert.deepEqual(leer("#/tierras?campana=2026&campana=2027").parametros, { campana: 2026 });
  assert.deepEqual(leer("#/tierras?q=uno&q=dos").parametros, { q: "uno" });
});

test("lo que el módulo no conoce no se tira: viaja como texto", () => {
  // Un parámetro que no entendemos puede ser un filtro de una pantalla que se añade mañana. Borrarlo en
  // silencio sería perder el filtro del agricultor, que es justo lo que este módulo viene a evitar.
  const leida = leer("#/tierras?lo_que_sea=1&q=El Prado");
  assert.deepEqual(leida.parametros, { lo_que_sea: "1", q: "El Prado" });
  assert.equal(escribir("tierras", leida.parametros), "#/tierras?lo_que_sea=1&q=El%20Prado");
});

test("el nombre de un parámetro se lee en minúscula, como lo escribe un móvil", () => {
  // En un teclado de móvil la primera letra sale en mayúscula. Pedirle a nadie que escriba `?campana=` en
  // minúscula a mano es pedirle que se equivoque.
  assert.deepEqual(leer("#/TIERRAS/12?Campana=2026").parametros, { id: 12, campana: 2026 });
  assert.equal(leer("#/Tierras/12").pantalla, "tierra");
});

// ---------------------------------------------------------------------------
// La memoria de la vista: volver del detalle sin perder los filtros
// ---------------------------------------------------------------------------

test("lo que se guarda se recupera, y lo que no se ha guardado no existe", () => {
  const vista = {
    pantalla: "tierras",
    parametros: { campana: 2026, q: "El Prado", orden: "numero", sentido: -1 },
  };
  const memoria = recuerda({}, "tierras", vista);
  assert.deepEqual(recupera(memoria, "tierras"), vista);
  // Lo que no se ha guardado **no existe**: `null`, y no un objeto vacío (que se leería como «hay una
  // vista sin filtros» y llevaría al agricultor a una lista distinta de la que dejó).
  assert.equal(recupera(memoria, "almacen"), null);
  assert.equal(recupera({}, "tierras"), null);
  assert.equal(recupera(undefined, "tierras"), null);
});

test("la memoria no se toca: se devuelve una copia", () => {
  // Porque la memoria vive en el `estado` de `app.js` y la puede estar usando otra cosa a la vez. Si estas
  // funciones tocaran el objeto que se les pasa, dos listas abiertas se pisarían y la vuelta desde una
  // ficha llevaría a los filtros de la otra.
  const antes = { tierras: { pantalla: "tierras" } };
  const despues = recuerda(antes, "almacen", { pantalla: "almacen" });
  assert.deepEqual(Object.keys(antes), ["tierras"], "se ha tocado la memoria que se le pasó");
  assert.deepEqual(Object.keys(despues).sort(), ["almacen", "tierras"]);
  // Y no hay estado escondido dentro del módulo: dos llamadas iguales no se acuerdan de nada.
  assert.equal(recupera(undefined, "tierras"), null);
  assert.equal(recupera({}, "tierras"), null);
});

test("olvidar una vista la quita, y las demás se quedan", () => {
  const memoria = recuerda(recuerda({}, "tierras", { pantalla: "tierras" }), "almacen", { pantalla: "almacen" });
  const sinTierras = olvida(memoria, "tierras");
  assert.equal(recupera(sinTierras, "tierras"), null);
  assert.deepEqual(recupera(sinTierras, "almacen"), { pantalla: "almacen" });
  assert.equal(recupera(memoria, "tierras") !== null, true, "olvidar se ha llevado por delante la memoria original");
  // Olvidar algo que no está no es un fallo: se queda como estaba.
  assert.deepEqual(olvida({}, "tierras"), {});
  assert.deepEqual(olvida(undefined, "tierras"), {});
});

test("una vista vacía no se guarda: es como olvidarla", () => {
  // Guardar «nada» y guardar «una vista sin filtros» tienen que ser lo mismo: si no, al volver de una
  // ficha el listado se pondría con unos filtros que nadie ha puesto.
  const memoria = recuerda({ tierras: { pantalla: "tierras" } }, "tierras", null);
  assert.equal(recupera(memoria, "tierras"), null);
  assert.deepEqual(recuerda({}, "", { pantalla: "tierras" }), {});
});

test("el recorrido que pide T04: lista → ficha → vuelta con los filtros puestos", () => {
  // Es el recorrido entero de la aceptación, contado con las cuatro piezas del módulo: se entra en el
  // listado con una campaña y un filtro, se guarda esa vista, se abre la ficha (que es un enlace de la
  // fila, con la vista dentro) y se vuelve a la dirección guardada.
  const listado = leer("#/tierras?campana=2026&finca=3&orden=numero&q=El%20Prado&sentido=1");
  assert.equal(listado.pantalla, "tierras");
  const memoria = recuerda({}, "tierras", listado);
  // Tocar una fila: el enlace lleva el identificador **y** la vista.
  const ficha = leer(enlaceDeTierra(12, listado.parametros));
  assert.equal(ficha.pantalla, "tierra");
  assert.equal(ficha.parametros.id, 12);
  assert.equal(ficha.parametros.campana, 2026);
  assert.equal(ficha.parametros.q, "El Prado");
  // Y volver: la dirección del listado, otra vez tal cual estaba.
  const vuelta = leer(direccionDe(recupera(memoria, "tierras")));
  assert.equal(vuelta.pantalla, "tierras");
  assert.deepEqual(vuelta.parametros, listado.parametros);
  // Si no hubiera memoria, `recupera` devuelve `null` y `direccionDe` no inventa una dirección: eso deja
  // al agricultor en el listado sin filtros, que es lo que hay que evitar, y por eso se guarda.
  assert.equal(direccionDe(recupera({}, "tierras")), "");
});

test("las listas con buscador y orden son seis, y son las que tienen tabla", () => {
  // Son las seis de `ORDEN_DE_ENTRADA` en `app.js` (tierras, apuntes, facturas, años, almacén y cultivos),
  // con el nombre que cada una tiene en esta tabla. Lo que no es una lista no tiene vista que recordar.
  for (const lista of LISTADOS) {
    assert.ok(esConocida(lista), `la lista «${lista}» no es una pantalla conocida`);
    assert.equal(esUnListado(lista), true);
  }
  assert.equal(esUnListado("tierra"), false);
  assert.equal(esUnListado("apunte"), false);
  assert.equal(esUnListado("inicio"), false);
});

// ---------------------------------------------------------------------------
// El módulo no toca el navegador
// ---------------------------------------------------------------------------

/**
 * El código de `rutas.js` sin sus comentarios.
 *
 * Hace falta de verdad, y por el mismo motivo por el que la prueba de Python quita los comentarios de
 * `app.js`: los comentarios de este módulo hablan de `window`, de `history` y de `fetch` **para decir que
 * no se usan**, y una prueba que buscara esas palabras en el fichero entero se creería lo que dice un
 * comentario en vez de lo que hace el código.
 *
 * Se recorre letra a letra y se saltan las cadenas con sus escapes. Aquí no hay expresiones regulares a
 * propósito (el módulo no usa ninguna), así que no hay que adivinar dónde empieza una: ese fue el fallo
 * que ya tuvo el quitador de comentarios de `test_interfaz.py`, cuando tomó el `/` de un `</span>` por el
 * principio de una expresión regular y se comió medio fichero.
 */
function sinComentarios(codigo) {
  let limpio = "";
  let i = 0;
  while (i < codigo.length) {
    const letra = codigo[i];
    const siguiente = codigo[i + 1];
    if (letra === "/" && siguiente === "*") {
      const fin = codigo.indexOf("*/", i + 2);
      i = fin === -1 ? codigo.length : fin + 2;
      continue;
    }
    if (letra === "/" && siguiente === "/") {
      const fin = codigo.indexOf("\n", i);
      i = fin === -1 ? codigo.length : fin;
      continue;
    }
    if (letra === '"' || letra === "'" || letra === "`") {
      const comilla = letra;
      limpio += letra;
      i += 1;
      while (i < codigo.length) {
        if (codigo[i] === "\\") {
          limpio += codigo[i] + (codigo[i + 1] || "");
          i += 2;
          continue;
        }
        limpio += codigo[i];
        const cerrada = codigo[i] === comilla;
        i += 1;
        if (cerrada) break;
      }
      continue;
    }
    limpio += letra;
    i += 1;
  }
  return limpio;
}

test("el quitador de comentarios de esta prueba se prueba a sí mismo", () => {
  // Un quitador que se coma el fichero es peor que no tener prueba: da la sensación de que revisa. Ya pasó
  // dos veces en este proyecto, y por eso los guardianes tienen su propia prueba.
  const ejemplo = [
    'const url = "https://ejemplo/lo//que-sea"; // aquí se habla de window',
    "/* y aquí de document */",
    "export const algo = 1;",
  ].join("\n");
  const limpio = sinComentarios(ejemplo);
  assert.ok(limpio.includes("https://ejemplo/lo//que-sea"), "se ha comido una cadena con barras dentro");
  assert.ok(limpio.includes("export const algo = 1;"), "se ha comido el código");
  assert.ok(!limpio.includes("window"), "no ha quitado el comentario de línea");
  assert.ok(!limpio.includes("document"), "no ha quitado el comentario de bloque");
});

test("rutas.js no toca el navegador: ni window, ni document, ni history, ni fetch", () => {
  // Este módulo es el que traduce, y nada más. Si usara `window` o `document`, no se podría probar entero
  // sin navegador (que es lo que hace este fichero) y un fallo aquí dejaría la pantalla en blanco. Si
  // usara `history` o `location`, habría dos sitios decidiendo la dirección —el módulo y `app.js`—, y el
  // día que se cambie uno la dirección y la pantalla dirían cosas distintas.
  const codigo = sinComentarios(
    readFileSync(new URL("../web/react/rutas.js", import.meta.url), "utf8"),
  );
  for (const prohibida of [
    "window",
    "document",
    "history",
    "location",
    "fetch",
    "localStorage",
    "sessionStorage",
    "navigator",
    "indexedDB",
  ]) {
    assert.doesNotMatch(codigo, new RegExp(`\\b${prohibida}\\b`), `rutas.js usa «${prohibida}»`);
  }
  // Y que el quitador no se haya comido el módulo: si se lo comiera, la prueba de arriba pasaría sin
  // mirar nada (que es exactamente el fallo que esto evita).
  assert.ok(codigo.includes("export function leer("), "el quitador se ha comido el módulo");
  assert.ok(codigo.includes("export function escribir("), "el quitador se ha comido el módulo");
  assert.ok(codigo.length > 1000, "el código que se está revisando es demasiado corto para ser el módulo");
});

test("llamar dos veces a lo mismo da lo mismo: el módulo no se acuerda de nada", () => {
  // Sin estado dentro del módulo, una prueba no puede ensuciar a la siguiente y una pantalla no puede
  // heredar los filtros de la anterior.
  assert.deepEqual(leer("#/tierras?campana=2026"), leer("#/tierras?campana=2026"));
  assert.equal(escribir("tierra", { id: 12 }), escribir("tierra", { id: 12 }));
  assert.deepEqual(pantallas(), pantallas());
  // Y la lista de pantallas que se devuelve es nueva: tocarla no cambia la tabla del módulo.
  const copia = pantallas();
  copia.push("inventada");
  assert.equal(esConocida("inventada"), false, "la tabla del módulo se ha podido tocar desde fuera");
});

// ---------------------------------------------------------------------------
// Toda dirección que se escribe tiene que poder abrirse (05/10/2026)
// ---------------------------------------------------------------------------

/**
 * Las direcciones que **se escriben y no se abren**, con su motivo por escrito.
 *
 * POR QUÉ EXISTE ESTA LISTA, Y POR QUÉ ESTÁ VACÍA. Una dirección que la aplicación escribe en la barra
 * del navegador y que luego no sabe abrir es la peor de las mentiras de un programa: el agricultor
 * recarga —o le manda el enlace a quien le ayuda— y aterriza en otra pantalla. Pasó de verdad: la
 * agenda de los trabajos (T15) escribía `#/trabajos`, y al abrir esa dirección la aplicación caía al
 * panel de mando, porque su clave no estaba en `ABRIR_LA_PANTALLA`. Lo encontró el guion del navegador
 * —que anota en el `<title>` en qué dirección ha acabado— y no lo había visto ninguna prueba. Hoy
 * **ninguna** dirección está en esta lista: las cuarenta y ocho se abren. Si alguna vez una no se puede
 * abrir, se escribe aquí **con su motivo**, que es lo que esta prueba exige en vez de dejarlo pasar.
 */
const DIRECCIONES_QUE_NO_SE_ABREN = {};

test("toda dirección de la tabla tiene su puerta en app.js, o su motivo escrito aquí", () => {
  const app = sinComentarios(readFileSync(new URL("../web/app.js", import.meta.url), "utf8"));
  // Las que se abren directamente por su clave (`tierras`, `almacen`, `mapa`…).
  const bloque = app.match(/const ABRIR_LA_PANTALLA = \{([\s\S]*?)\n\};/);
  assert.ok(bloque, "no se ha podido leer la tabla `ABRIR_LA_PANTALLA` de app.js");
  const enElMapa = new Set([...bloque[1].matchAll(/^\s*([a-z_]+):\s*\(\)/gm)].map((caza) => caza[1]));
  // Y las que se abren con un `if` dentro de `abrirLaPantalla`: hay claves que no están en el mapa
  // porque antes de abrir la pantalla hay que comprobar algo —si esa tierra es suya, si hay cobertura,
  // si ese identificador está entre los descargados— y esa comprobación vive en el `if`. (`abrirLaDireccion`
  // es la de arriba: lee la dirección y cambia de finca si hace falta; quien decide la pantalla es esta.)
  const funcion = app.match(/function abrirLaPantalla\(clave, parametros = \{\}\) \{([\s\S]*?)\n\}/);
  assert.ok(funcion, "no se ha podido leer `abrirLaPantalla` de app.js");
  const enLosIfs = new Set([...funcion[1].matchAll(/clave === "([a-z_]+)"/g)].map((caza) => caza[1]));

  const sinPuerta = pantallas().filter(
    (clave) =>
      !enElMapa.has(clave) && !enLosIfs.has(clave) && !(clave in DIRECCIONES_QUE_NO_SE_ABREN),
  );
  assert.deepEqual(
    sinPuerta,
    [],
    `estas direcciones se escriben y no hay quien las abra: ${sinPuerta.join(", ")}. ` +
      "Se añade su puerta en `app.js`, o se declara en `DIRECCIONES_QUE_NO_SE_ABREN` con su motivo.",
  );

  // Y la lista de excepciones no puede envejecer: una que ya se abra es una excepción que sobra, y un
  // motivo de tres palabras no es un motivo.
  for (const clave of Object.keys(DIRECCIONES_QUE_NO_SE_ABREN)) {
    assert.ok(
      !enElMapa.has(clave) && !enLosIfs.has(clave),
      `«${clave}» figura como que no se abre, y sí se abre: quítala de la lista`,
    );
    assert.ok(
      String(DIRECCIONES_QUE_NO_SE_ABREN[clave]).length > 20,
      `«${clave}» no dice por qué no se abre`,
    );
  }

  // Y que el lector no se haya comido el fichero: si se lo comiera, las dos listas saldrían vacías y
  // esta prueba pasaría sin mirar nada (el fallo que ya tuvo el quitador de comentarios de este mismo
  // fichero, y por eso tiene su propia prueba más abajo).
  assert.ok(enElMapa.size > 20, `la tabla de puertas leída es demasiado corta: ${enElMapa.size}`);
  assert.ok(enLosIfs.size > 10, `los «if» leídos son demasiado pocos: ${enLosIfs.size}`);
  assert.ok(funcion[1].length > 1000, "el cuerpo de `abrirLaPantalla` leído es demasiado corto");
});

// ---------------------------------------------------------------------------
// El armazón con contexto (`react/piezas/marco.js`), la otra mitad de T04
//
// POR QUÉ ESTA PARTE ESTÁ AQUÍ Y NO EN `react.test.js`. Es donde vive la prueba del armazón, pero en esta
// entrega **solo se pueden tocar los cuatro ficheros del ticket**, y `react.test.js` no es uno de ellos.
// Antes de dejar el cambio del armazón sin ninguna prueba (que es lo que no se puede hacer), se prueba
// aquí. Lo que se comprueba es exactamente lo que pide el ticket: que **sin** el prop `contexto` la barra
// se pinte como siempre —eso lo comprueba también `react.test.js`, sin tocarlo— y que **con** el prop
// salgan la finca y los botones de cambiar de campaña y de finca.
// ---------------------------------------------------------------------------

// Los ficheros de `vendor` son UMD: se cargan con `vm`, igual que los carga el navegador, y dejan `React`,
// `htm` y `ReactDOMServer` en los globales. Es lo mismo que hace `react.test.js` para poder ver el HTML de
// un componente sin montar un navegador.
globalThis.self = globalThis;

function cargarDeVendor(nombre) {
  const codigo = readFileSync(new URL(`../web/vendor/${nombre}`, import.meta.url), "utf8");
  vm.runInThisContext(codigo, { filename: nombre });
}

cargarDeVendor("react.production.min.js");
cargarDeVendor("htm.umd.js");
cargarDeVendor("react-dom-server-legacy.browser.production.min.js");

/** Las palabras del armazón, copiadas de `textos.py` (`MENU`) y las nuevas que se proponen para T04. */
const TEXTOS_DEL_MARCO = {
  menu: {
    titulo: "Menú",
    etiqueta: "El menú de la aplicación",
    panel: "Panel",
    cuenta: "Tu cuenta",
    sin_cuenta: "Tu cuenta",
    campana: "Campaña",
    sin_campana: "Sin año",
    apuntar: "APUNTAR",
    letra: "A+",
    letra_etiqueta: "Poner la letra más grande",
    salir: "Salir",
    salir_etiqueta: "Salir de la cuenta",
  },
  // Las que hacen falta para el contexto. Se prueban aquí en su propio bloque (`marco`) y también dentro
  // de `menu`, porque el armazón acepta las dos formas: la que `app.js` manda hoy (`menu`) y la que pide
  // el ticket (`marco`).
  marco: {
    finca: "Finca",
    sin_finca: "Sin finca",
    cambiar_campana: "Cambiar de campaña",
    cambiar_finca: "Cambiar de finca",
  },
  acciones: { volver: "VOLVER" },
};

/** Los módulos del menú, como los prepara `app.js` (con dos basta para lo que se mira aquí). */
const MODULOS = [
  { clave: "panel", etiqueta: "Panel", accion: "ir-inicio", activo: false },
  { clave: "tierras", etiqueta: "Mis parcelas, productos y máquinas", accion: "inicio", datos: { ir: "mis_cosas" }, activo: true },
];

/** El HTML del armazón, con los textos del servidor y las propiedades que se le pidan. */
async function htmlDelMarco(cambios = {}) {
  const { Marco } = await import(`../web/react/piezas/marco.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    globalThis.React.createElement(Marco, {
      textos: structuredClone(TEXTOS_DEL_MARCO),
      cuenta: "David Pérez Velasco",
      campana: "2026",
      modulos: MODULOS,
      ...cambios,
    }),
  );
}

/** El contexto de una cuenta que entra en dos fincas y lleva cinco años. */
function contextoDePrueba(cambios = {}) {
  return {
    finca: "El Prado",
    campana: 2026,
    campanas: [2026, 2025, 2024],
    fincas: [
      { id: 3, nombre: "El Prado", activa: true },
      { id: 7, nombre: "La Vega" },
    ],
    ...cambios,
  };
}

/** Los trozos de texto que se ven en un HTML: lo que hay entre `>` y `<`. */
function frasesVisibles(html) {
  return html
    .split(">")
    .map((trozo) => trozo.split("<")[0])
    .map((texto) => texto.trim())
    .filter((texto) => texto !== "");
}

test("sin contexto, la barra es exactamente la de siempre", async () => {
  // Es la condición que puso el ticket: **sin** el prop, la barra tiene que dibujarse igual que ahora, y
  // hay pruebas que comparan lo que se pinta hoy (`react.test.js`). Aquí se comprueba lo propio de este
  // fichero: que no aparece nada nuevo, ni una finca, ni un botón de cambiar nada.
  const sinNada = await htmlDelMarco();
  assert.match(sinNada, /<span class="barra-rotulo">Campaña<\/span><span class="barra-valor">2026<\/span>/);
  assert.match(sinNada, /<span class="barra-rotulo">Tu cuenta<\/span><span class="barra-valor">David Pérez Velasco<\/span>/);
  assert.doesNotMatch(sinNada, /barra-rotulo">Finca</, "sin contexto no se añade el dato de la finca");
  assert.doesNotMatch(sinNada, /cambiar-finca/, "sin contexto no hay botones de cambiar de finca");
  assert.doesNotMatch(sinNada, /cambiar-campana/, "sin contexto el año no se convierte en botones");
  // Y el mismo dibujo con el prop puesto a `null`, que es como lo manda `app.js` cuando no hay contexto.
  assert.equal(await htmlDelMarco({ contexto: null }), sinNada);
});

test("con contexto, la barra enseña la finca y deja cambiar de campaña y de finca", async () => {
  const html = await htmlDelMarco({ contexto: contextoDePrueba() });
  // La finca, con su rótulo del servidor.
  assert.match(html, /<span class="barra-rotulo">Finca<\/span>/);
  // Un botón por finca, con su identificador en `data-valor` (que es lo que lee el manejador de clics) y
  // la acción que el ticket fija.
  assert.match(html, /data-accion="cambiar-finca"[^>]*data-valor="3"/);
  assert.match(html, /data-accion="cambiar-finca"[^>]*data-valor="7"/);
  assert.match(html, />El Prado</);
  assert.match(html, />La Vega</);
  // Un botón por año, y la misma acción para las campañas.
  assert.match(html, /data-accion="cambiar-campana"[^>]*data-valor="2026"/);
  assert.match(html, /data-accion="cambiar-campana"[^>]*data-valor="2025"/);
  assert.match(html, /data-accion="cambiar-campana"[^>]*data-valor="2024"/);
  // Y la cuenta sigue donde estaba: lo que se añade no quita nada.
  assert.match(html, /<span class="barra-rotulo">Tu cuenta<\/span><span class="barra-valor">David Pérez Velasco<\/span>/);
  assert.match(html, /data-accion="ir-inicio">APUNTAR</);
});

test("se ve cuál está elegido, y no solo por el color", async () => {
  // Regla de la casa: lo que dice el color lo dice también una palabra o una marca. La finca en la que se
  // está y el año que se está llevando llevan su clase **y** `aria-current`, que es lo que lo dice en voz
  // alta a quien no ve la pantalla.
  const html = await htmlDelMarco({ contexto: contextoDePrueba() });
  assert.match(html, /class="boton-letra boton-elegido"[^>]*data-accion="cambiar-finca"[^>]*data-valor="3"[^>]*aria-current="true"/);
  assert.match(html, /class="boton-letra boton-elegido"[^>]*data-accion="cambiar-campana"[^>]*data-valor="2026"[^>]*aria-current="true"/);
  // Y los que no están elegidos no lo llevan: si lo llevaran todos, no diría nada.
  assert.doesNotMatch(html, /boton-elegido"[^>]*data-valor="7"/);
  assert.doesNotMatch(html, /boton-elegido"[^>]*data-valor="2025"/);
  // El año elegido también sale cuando `app.js` no manda la campaña dentro del contexto: se usa el mismo
  // dato que ya enseña la barra, para no tener dos verdades.
  const sinCampanaEnElContexto = await htmlDelMarco({ contexto: contextoDePrueba({ campana: "" }) });
  assert.match(sinCampanaEnElContexto, /data-accion="cambiar-campana"[^>]*data-valor="2026"[^>]*aria-current="true"/);
});

test("sin lista de fincas se enseña el nombre, y sin nombre se dice «Sin finca»", async () => {
  // El contexto puede llegar a medias (la lista de fincas se pide al servidor y puede tardar). Medio
  // contexto no puede dejar la barra en blanco ni inventarse un guion.
  const soloElNombre = await htmlDelMarco({ contexto: { finca: "El Prado" } });
  assert.match(soloElNombre, /<span class="barra-rotulo">Finca<\/span><span class="barra-valor">El Prado<\/span>/);
  assert.doesNotMatch(soloElNombre, /cambiar-finca/);
  // Y sin nombre, la palabra del servidor (nunca un hueco).
  const sinNombre = await htmlDelMarco({ contexto: { fincas: [] } });
  assert.match(sinNombre, /<span class="barra-valor">Sin finca<\/span>/);
  // Un contexto vacío es un contexto: sale la finca sin decir, y el año sigue siendo el de siempre.
  const vacio = await htmlDelMarco({ contexto: {} });
  assert.match(vacio, /<span class="barra-valor">Sin finca<\/span>/);
  assert.match(vacio, /<span class="barra-rotulo">Campaña<\/span><span class="barra-valor">2026<\/span>/);
});

test("una finca sin nombre o sin identificador no se pinta como botón", async () => {
  // Un botón que no dice a qué finca cambia es peor que no tenerlo: se toca, cambia de finca y el
  // agricultor no sabe a dónde ha ido. Lo que no se sabe se queda fuera, no se rellena con un hueco.
  const html = await htmlDelMarco({
    contexto: contextoDePrueba({
      fincas: [
        { id: 3, nombre: "El Prado", activa: true },
        { id: 7, nombre: "" },
        { nombre: "Sin identificador" },
        { id: null, nombre: "Sin identificador tampoco" },
      ],
    }),
  });
  assert.match(html, /data-accion="cambiar-finca"[^>]*data-valor="3"/);
  assert.equal((html.match(/data-accion="cambiar-finca"/g) || []).length, 1, "se ha pintado un botón de finca a medias");
});

test("los años llegan como años o como las fichas del servidor", async () => {
  // La pantalla de los años trabaja con lo que devuelve `/api/campanas` (`{id, anio…}`) y la barra, con el
  // año a secas. Se aceptan las dos, que es lo que evita que la barra enseñe un hueco el día que `app.js`
  // le pase la lista del servidor tal cual.
  const conFichas = await htmlDelMarco({
    contexto: contextoDePrueba({ campanas: [{ id: 1, anio: 2026 }, { id: 2, anio: 2025 }] }),
  });
  assert.match(conFichas, /data-accion="cambiar-campana"[^>]*data-valor="2026"/);
  assert.match(conFichas, /data-accion="cambiar-campana"[^>]*data-valor="2025"/);
  assert.doesNotMatch(conFichas, /data-valor="1"/);
});

test("las palabras nuevas vienen del servidor, y no del armazón", async () => {
  // El armazón no escribe ni una frase: los nombres de los módulos, los rótulos, los años y los nombres de
  // las fincas salen todos del servidor o son datos. Si alguien escribiera aquí «Finca» o «Cambiar de
  // campaña» a mano, esto se pondría rojo —y esas palabras dejarían de pasar por el filtro de la jerga.
  const html = await htmlDelMarco({ contexto: contextoDePrueba() });
  const delServidor = new Set([
    ...Object.values(TEXTOS_DEL_MARCO.menu),
    ...Object.values(TEXTOS_DEL_MARCO.marco),
    ...MODULOS.map((modulo) => modulo.etiqueta),
    "El Prado",
    "La Vega",
    "2026",
    "2025",
    "2024",
    "David Pérez Velasco",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano en el armazón: «${frase}»`);
  }
});

test("las palabras nuevas también valen dentro de `menu`, que es lo que manda `app.js` hoy", async () => {
  // El armazón lee las palabras nuevas de `textos.marco` y, si no están ahí, de `textos.menu` (el bloque
  // que ya se sirve). Las dos formas tienen que dar el mismo dibujo, o la integración dependería de dónde
  // se añada cada palabra.
  const textos = structuredClone(TEXTOS_DEL_MARCO);
  Object.assign(textos.menu, textos.marco);
  delete textos.marco;
  const conMenu = await htmlDelMarco({ textos, contexto: contextoDePrueba() });
  assert.equal(conMenu.trimStart(), (await htmlDelMarco({ contexto: contextoDePrueba() })).trimStart());
});
