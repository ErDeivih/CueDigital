/**
 * Pruebas de las pantallas de las semillas y las siembras (T10, 03/10/2026), **sin navegador**.
 *
 * POR QUÉ ESTÁN AQUÍ Y NO EN `interfaz.test.js`
 *
 * Estas pantallas están escritas en React (`web/react/pantallas/semillas.js` y `siembras.js`), y en el
 * DOM de mentira de `interfaz.test.js` React no se puede montar. Así que se prueban **contra el
 * componente**: se le dan las propiedades y se mira el HTML que produce con `renderToStaticMarkup`,
 * igual que se hace con las otras pantallas migradas (`react.test.js`). No hay `jsdom` ni ninguna
 * dependencia nueva.
 *
 * QUÉ SE COMPRUEBA, Y POR QUÉ ESAS COSAS
 *
 *  1. **Que la dosis por hectárea y la cantidad total sean dos campos distintos**, cada uno con su
 *     unidad y con su nombre, y que **el número que ha calculado el programa se diga**. Confundir las
 *     dos cifras es un error de diez veces, y es el corazón de este ticket.
 *  2. **Que lo que no se sabe salga en blanco**: un poder germinativo vacío se pinta vacío y no como
 *     un cero, y «¿viene tratada?» tiene tres respuestas (sí, no y no lo sé).
 *  3. **Que una etiqueta leída no se dé por buena sola**: cuando lo que hay es una propuesta, la
 *     pantalla dice que hasta que no se pulse GUARDAR no hay ninguna semilla apuntada.
 *  4. **Que ninguna frase esté escrita dentro del componente**: todas vienen de la copia de los textos
 *     del servidor que hay aquí abajo (y una prueba de Python comprueba que esa copia no se queda
 *     vieja: un test que lee ficheros necesita su propia prueba).
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

import { montajes } from "../web/react/montar.js";

// ---------------------------------------------------------------------------
// El arnés: React y htm, como los deja `index.html`
// ---------------------------------------------------------------------------

globalThis.self = globalThis;

function cargarDeVendor(nombre) {
  const codigo = readFileSync(new URL(`../web/vendor/${nombre}`, import.meta.url), "utf8");
  vm.runInThisContext(codigo, { filename: nombre });
}

cargarDeVendor("react.production.min.js");
cargarDeVendor("htm.umd.js");
cargarDeVendor("react-dom-server-legacy.browser.production.min.js");

const React = globalThis.React;

// ---------------------------------------------------------------------------
// Los textos: los mismos que sirve el servidor
// ---------------------------------------------------------------------------

/**
 * La copia de los textos de las semillas, **tal y como los sirve `/api/interfaz`**.
 *
 * Si se inventaran aquí, estas pruebas comprobarían una pantalla que el agricultor no tiene. La
 * prueba de Python (`tests/test_semillas.py::TestLaCopiaDeLosTextosNoSeQuedaVieja`) lee este fichero
 * y comprueba, clave por clave, que dice lo mismo que el servidor.
 */
const TEXTOS = {
  semillas: {
    titulo: "Mis semillas",
    explica:
      "Aquí tienes las semillas que usas, con lo que pone su etiqueta y lo que te queda de cada una. La semilla es una cosa más del almacén: entra con el albarán y sale cuando la siembras.",
    vacia: "Todavía no has dado de alta ninguna semilla. Cuando apuntes una, aquí verás su etiqueta y lo que te queda.",
    cuantas: "Tienes {cuantas} semillas dadas de alta.",
    cuantas_una: "Tienes 1 semilla dada de alta.",
    buscando: "Buscando…",
    que_se_puede_hacer: "¿Qué quieres hacer?",
    anadir: "AÑADIR UNA SEMILLA",
    anadir_pista: "Escribe lo que pone la etiqueta del envase",
    volver_al_inicio: "VOLVER AL INICIO",
    ver_las_siembras: "VER LO QUE HE SEMBRADO",
    leer_etiqueta: "HACERLE UNA FOTO A LA ETIQUETA",
    leer_lo_que_pone: "LEER LO QUE PONE (NO SE GUARDA NADA)",
    leer_etiqueta_pista:
      "Hazle una foto a la etiqueta del envase. Si se puede leer, te enseño lo que he entendido para que lo mires antes de guardarlo.",
    ficha_titulo: "Una semilla nueva",
    ficha_titulo_corregir: "Corregir esta semilla",
    ficha_explica:
      "Escribe lo que pone la etiqueta. Lo que no venga en el papel, déjalo en blanco: se queda vacío y ya está, no se pone un cero.",
    ficha_explica_propuesta:
      "Esto es lo que he leído de la foto. Míralo y corrígelo: hasta que no pulses el botón de abajo, no se ha guardado nada. Lo que no he podido leer está en blanco.",
    articulo_del_almacen: "¿Es algo que ya tienes en el almacén?",
    articulo_del_almacen_pista:
      "Si la semilla ya entró con un albarán, elígela aquí: se le cuelga la etiqueta a lo que ya hay, en vez de apuntar dos veces la misma semilla.",
    articulo_nuevo: "No, es nueva: la apunto ahora",
    nombre_del_articulo: "Cómo la llamas tú",
    nombre_del_articulo_pista:
      "El nombre con el que la reconoces en el almacén. Es el que verás en la lista y en el libro.",
    especie: "Qué semilla es",
    especie_pista: "La especie, como viene en la etiqueta: veza común, trigo blando, cebada…",
    variedad: "La variedad",
    variedad_pista: "El nombre de la variedad, si el papel lo dice.",
    casa_comercial: "La casa que la vende",
    casa_comercial_pista: "Quien la produce o la envasa: lo que pone arriba del todo en la etiqueta.",
    proveedor: "A quién se la compraste",
    proveedor_pista: "El proveedor o la cooperativa, si quieres apuntarlo.",
    numero_lote_proveedor: "El número de lote del envase",
    numero_lote_proveedor_pista:
      "El número que va impreso en el saco. Es con el que te avisan si hay un problema con esa partida.",
    dosis_recomendada: "Cuánto recomienda sembrar por hectárea",
    dosis_recomendada_pista:
      "Lo que dice la etiqueta, no lo que tú siembras. Puedes sembrar otra cosa: eso se apunta en cada siembra.",
    unidad_de_la_dosis: "En qué se mide",
    sin_decir: "Sin decir",
    fecha_envasado: "Cuándo se envasó",
    fecha_caducidad: "Hasta cuándo vale",
    fecha_caducidad_pista: "Si el papel no lo dice, déjalo en blanco: «no lo he mirado» no es «no caduca».",
    poder_germinativo: "Poder germinativo",
    poder_germinativo_pista: "El porcentaje del papel. No viene en todas las etiquetas.",
    pureza: "Pureza",
    pureza_pista: "El porcentaje del papel. Tampoco viene en todas.",
    no_lo_dice: "La etiqueta no lo dice",
    tratada: "¿Viene tratada?",
    tratada_pista:
      "Si el envase dice que la semilla viene tratada con algo, márcalo aquí. Es un dato que importa al manejarla.",
    tratada_si: "Sí viene tratada",
    tratada_no: "No viene tratada",
    tratada_no_se: "No lo sé",
    guardar: "GUARDAR LA SEMILLA",
    guardando: "Guardando…",
    subir_la_foto: "SUBIR LA FOTO",
    ver_la_foto: "VER LA FOTO DE LA ETIQUETA",
    la_foto_se_guarda: "La foto se guarda con la semilla, así que dentro de un año puedes volver a mirarla.",
    no_confirmada:
      "Esto es solo lo que he leído. Hasta que no pulses GUARDAR LA SEMILLA, no hay ninguna semilla apuntada.",
    lo_que_dice_el_papel: "Lo que dice el papel y no he podido apuntar",
    lo_que_dice_el_papel_explica:
      "Esto lo he leído, pero tal y como está escrito no se puede apuntar. Míralo y ponlo donde toque.",
    leido_a_mano: "Lo has escrito tú",
    leido_de_foto: "Leído de la foto de la etiqueta",
    leido_de_pdf: "Leído del PDF de la etiqueta",
    leido_de_escaneo: "Leído del escaneo de la etiqueta",
    leido_de_texto: "Leído de lo que has pegado",
    campos_leidos: "He podido leer {cuantos} datos de la etiqueta.",
    campos_leidos_uno: "He podido leer 1 dato de la etiqueta.",
    idioma_de_la_lectura: "Leído con el idioma {idioma}",
    volver_a_las_semillas: "VOLVER A MIS SEMILLAS",
    lo_que_queda: "Lo que te queda",
    sin_saber_lo_que_queda: "No se puede saber lo que queda",
    sin_semillas:
      "Todavía no tienes ninguna semilla dada de alta, así que no hay de dónde descontar lo que siembres. Apunta una y vuelve aquí.",
    siembras_titulo: "Lo que he sembrado",
    siembras_explica:
      "Cada siembra dice en qué tierra, de qué semilla y cuánto. Lo que siembras sale del almacén en el mismo momento, así que la semilla que te queda es la de verdad.",
    siembras_vacia:
      "Todavía no has apuntado ninguna siembra. Cuando siembres, aquí lo tendrás y la semilla saldrá del almacén.",
    cuantas_siembras: "Tienes {cuantas} siembras apuntadas.",
    cuantas_siembras_uno: "Tienes 1 siembra apuntada.",
    siembra_titulo: "Sembrar una semilla",
    siembra_titulo_corregir: "Corregir esta siembra",
    // La puerta para llegar al formulario de sembrar: sin ella, la pantalla existía y no se podía abrir.
    sembrar_esta: "SEMBRAR ESTA SEMILLA",
    sembrar_esta_pista: "Apunta en qué tierra la has sembrado y sale del almacén",
    siembra_explica:
      "Dime en qué tierra la has sembrado y cuánto. Si me das una de las dos cifras y las hectáreas, la otra la saco yo y te lo digo.",
    siembra_semilla: "¿Qué semilla?",
    siembra_tierra: "¿En qué tierra?",
    siembra_elige_la_tierra: "Elige la tierra",
    siembra_fecha: "¿Cuándo?",
    siembra_superficie: "¿Cuántas hectáreas has sembrado?",
    siembra_superficie_pista:
      "Las hectáreas que has sembrado. Con esto y una de las dos cifras de abajo, la otra la saco yo.",
    siembra_dosis: "Cuánto se siembra en cada hectárea",
    siembra_dosis_pista: "Lo que siembras en cada hectárea. No es lo que has gastado en total: son cosas distintas.",
    siembra_cantidad_total: "Cuánto se ha gastado en total",
    siembra_cantidad_total_pista: "Lo que has gastado en la tierra entera. Es lo que sale del almacén.",
    siembra_unidad_total: "En qué se mide el total",
    siembra_envase: "De qué envase sale",
    siembra_envase_pista:
      "De qué saco sale la semilla. Sin esto no se puede descontar del almacén, porque no se sabe de dónde quitar.",
    siembra_sin_envase: "No sé de qué envase sale",
    siembra_notas: "Lo que quieras apuntar",
    guardar_siembra: "GUARDAR LA SIEMBRA",
    guardando_siembra: "Guardando…",
    calculado: "Lo ha calculado el programa",
    calculado_pista:
      "Este número no lo has escrito tú: sale de la dosis por las hectáreas. Míralo, y si no es así, cámbialo.",
    siembra_anular: "ANULAR ESTA SIEMBRA",
    siembra_motivo_anulacion: "Por qué la anulas",
    siembra_motivo_anulacion_pista:
      "Una siembra no se borra: se anula y queda dicho por qué. Así el cuaderno se puede explicar.",
    siembra_anulada: "Siembra anulada. Lo que había salido del almacén vuelve a contar.",
    siembra_no_descuenta: "Esta siembra no ha descontado nada del almacén",
    siembra_no_descuenta_pista:
      "Falta saber cuánto se sembró o de qué envase sale. Mientras no se sepa, no se resta nada: antes un hueco que un número inventado. Corrígela cuando lo sepas.",
    volver_a_las_siembras: "VOLVER A LO QUE HE SEMBRADO",
  },
  // Los dos mensajes que la pantalla enseña tal cual (los del servidor, con su código).
  mensajes: {
    SM16_no_se_puede_sacar_sin_cantidad:
      "No se ha sacado nada del almacén porque no se sabe cuánto se sembró. Dime la cantidad total o la dosis por hectárea con las hectáreas, y la siembra descuenta.",
    SM20_la_siembra_ya_estaba:
      "Esta siembra ya estaba apuntada: no se ha descontado otra vez. Si querías cambiarla, pulsa CORREGIRLA.",
  },
};

function textosDePrueba() {
  return structuredClone(TEXTOS);
}

// ---------------------------------------------------------------------------
// Un lector del HTML: para mirar lo que se ve como lo miraría una persona
// ---------------------------------------------------------------------------

/** Los `id` de los campos, en el orden en que salen. */
function idsDe(html) {
  return [...html.matchAll(/(?<![\w-])id="([^"]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Todos los textos de una estructura anidada, sean diccionarios o listas. */
function todosLosTextos(valor) {
  if (typeof valor === "string") return [valor];
  if (Array.isArray(valor)) return valor.flatMap(todosLosTextos);
  if (valor && typeof valor === "object") return Object.values(valor).flatMap(todosLosTextos);
  return [];
}

/** Lo que de verdad se lee en el HTML: el texto que hay entre las etiquetas. */
function frasesVisibles(html) {
  return html
    .replace(/<span class="tarjeta-aviso-icono"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<span class="flecha"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<[^>]*>/g, "\u0000")
    .split("\u0000")
    .map((trozo) => trozo.trim())
    .filter(Boolean);
}

/** Los `data-accion` que salen pintados. */
function accionesDe(html) {
  return [...html.matchAll(/data-accion="([a-z0-9_-]+)"/g)].map((encontrado) => encontrado[1]);
}

async function cargar(nombre) {
  return import(`../web/react/pantallas/${nombre}.js?prueba=${Math.random()}`);
}

async function htmlDe(nombre, componente, propiedades) {
  const modulo = await cargar(nombre);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(modulo[componente], propiedades),
  );
}

const htmlDeLasSemillas = (cambios = {}) =>
  htmlDe("semillas", "PantallaDeLasSemillas", {
    textos: textosDePrueba(),
    tarjetas: [],
    resumen: "",
    error: "",
    cargando: false,
    ...cambios,
  });

const htmlDeUnaSemilla = (cambios = {}) =>
  htmlDe("semillas", "PantallaDeUnaSemilla", {
    textos: textosDePrueba(),
    borrador: {},
    propuesta: null,
    articulos: [],
    unidades_dosis: [],
    unidades_cantidad: [],
    corrigiendo: false,
    guardando: false,
    error: "",
    ...cambios,
  });

const htmlDeLasSiembras = (cambios = {}) =>
  htmlDe("siembras", "PantallaDeLasSiembras", {
    textos: textosDePrueba(),
    tarjetas: [],
    resumen: "",
    puedeSembrar: true,
    error: "",
    cargando: false,
    ...cambios,
  });

const htmlDeUnaSiembra = (cambios = {}) =>
  htmlDe("siembras", "PantallaDeUnaSiembra", {
    textos: textosDePrueba(),
    borrador: { parcela_id: 3, fecha: "2026-03-01" },
    semilla: "Veza común Villalobos",
    tierras: [{ valor: 3, texto: "El Prado" }],
    envases: [{ valor: 7, texto: "4471-A" }],
    unidades_dosis: [{ valor: "kg/ha", texto: "kg/ha" }],
    unidades_cantidad: [{ valor: "kg", texto: "kg" }],
    calculado: null,
    quedar: null,
    corrigiendo: false,
    guardando: false,
    error: "",
    ...cambios,
  });

// ---------------------------------------------------------------------------
// La lista de semillas
// ---------------------------------------------------------------------------

test("la lista de semillas sale con su título, su explicación y su botón de añadir", async () => {
  const html = await htmlDeLasSemillas();
  assert.match(html, /Mis semillas/);
  assert.match(html, /La semilla es una cosa más del almacén/);
  assert.ok(accionesDe(html).includes("semilla-nueva"), "falta el botón de añadir una semilla");
  assert.ok(accionesDe(html).includes("siembras-ver"), "falta el camino a lo que se ha sembrado");
});

test("sin ninguna semilla se dice, y con su botón para salir de ahí", async () => {
  const html = await htmlDeLasSemillas();
  assert.match(html, /Todavía no has dado de alta ninguna semilla/);
  assert.ok(
    accionesDe(html).includes("semilla-nueva"),
    "un aviso sin el botón que lo arregla deja al agricultor sin salida",
  );
});

test("cada semilla sale como una tarjeta con lo que queda de ella", async () => {
  const html = await htmlDeLasSemillas({
    tarjetas: [
      {
        id: 4,
        etiqueta: "Veza común Villalobos",
        rotulo: "Veza común · Villalobos",
        lineas: ["Te queda 320 kg", "Vence el 12/01/2028"],
        filas: [{ etiqueta: "Poder germinativo", valor: "92 %" }],
        avisos: ["La etiqueta no dice la pureza"],
      },
    ],
    resumen: "Tienes 1 semilla dada de alta.",
  });
  assert.match(html, /Veza común Villalobos/);
  assert.match(html, /Te queda 320 kg/);
  assert.match(html, /Poder germinativo/);
  assert.match(html, /La etiqueta no dice la pureza/);
  assert.match(html, /Tienes 1 semilla dada de alta/);
  assert.ok(accionesDe(html).includes("semilla-abrir"));
});

test("una semilla de la que no se sabe lo que queda lo dice, y no pone un cero", async () => {
  // Lo que queda lo prepara `app.js` con lo que contesta el servidor (`saldo: null` + su motivo): la
  // pantalla **no lo convierte en un cero**, y eso es lo que se comprueba aquí.
  const html = await htmlDeLasSemillas({
    tarjetas: [
      {
        id: 4,
        etiqueta: "Veza común Villalobos",
        lineas: ["No se puede saber lo que queda"],
        filas: [],
        avisos: [],
      },
    ],
  });
  assert.match(html, /No se puede saber lo que queda/);
  assert.doesNotMatch(html, /Te queda 0/);
});

// ---------------------------------------------------------------------------
// La ficha de una semilla
// ---------------------------------------------------------------------------

test("la ficha pide los datos de la etiqueta, cada uno con su id", async () => {
  const html = await htmlDeUnaSemilla();
  assert.deepEqual(idsDe(html).filter((id) => id !== "semilla-foto"), [
    "semilla-articulo",
    "semilla-nombre",
    "semilla-especie",
    "semilla-variedad",
    "semilla-casa",
    "semilla-proveedor",
    "semilla-lote",
    "semilla-dosis",
    "semilla-unidad-dosis",
    "semilla-envasado",
    "semilla-caducidad",
    "semilla-germinativo",
    "semilla-pureza",
    "semilla-tratada",
  ]);
});

test("los números se piden con el teclado de números del móvil", async () => {
  const html = await htmlDeUnaSemilla();
  for (const id of ["semilla-dosis", "semilla-germinativo", "semilla-pureza"]) {
    const campo = html.split(`id="${id}"`)[1].split(">")[0];
    assert.match(campo, /inputmode="decimal"/i, `${id} no pide el teclado de números: ${campo}`);
  }
});

test("un poder germinativo que no se sabe sale en blanco, nunca como un cero", async () => {
  const html = await htmlDeUnaSemilla({ borrador: { poder_germinativo_pct: null, pureza_pct: null } });
  const campo = html.split('id="semilla-germinativo"')[1].split(">")[0];
  assert.match(campo, /value=""/, `un hueco se está pintando como un número: ${campo}`);
  assert.doesNotMatch(campo, /value="0/, `un hueco se está pintando como un cero: ${campo}`);
  assert.match(html, /La etiqueta no lo dice/, "tiene que decir que dejarlo en blanco es lo correcto");
});

test("«¿viene tratada?» tiene tres respuestas, no dos", async () => {
  const html = await htmlDeUnaSemilla();
  const select = html.split('id="semilla-tratada"')[1].split("</select>")[0];
  assert.match(select, /Sí viene tratada/);
  assert.match(select, /No viene tratada/);
  assert.match(select, /No lo sé/);
});

test("lo que se ha leído de la foto se enseña y se dice que no está guardado", async () => {
  const html = await htmlDeUnaSemilla({
    borrador: { nombre: "Veza común", especie: "VEZA COMUN", poder_germinativo_pct: 92 },
    propuesta: {
      como_se_leyo_texto: "Leído de la foto de la etiqueta",
      resumen_campos: "He podido leer 3 datos de la etiqueta.",
      idioma_texto: "Leído con el idioma español",
      avisos: ["Mira las palabras con tilde, que pueden salir cambiadas."],
      dudas: [],
      campos_leidos: ["especie", "poder_germinativo_pct"],
    },
  });
  assert.match(html, /Leído de la foto de la etiqueta/);
  assert.match(html, /He podido leer 3 datos de la etiqueta/);
  assert.match(html, /Mira las palabras con tilde/);
  assert.match(html, /Hasta que no pulses GUARDAR LA SEMILLA, no hay ninguna semilla apuntada/);
  // Y los valores leídos van **dentro de su campo**, que es donde el agricultor los corrige.
  assert.match(html.split('id="semilla-especie"')[1].split(">")[0], /value="VEZA COMUN"/);
});

test("sin foto no se habla de ninguna lectura", async () => {
  const html = await htmlDeUnaSemilla();
  assert.doesNotMatch(html, /Leído de la foto/);
  assert.doesNotMatch(html, /GUARDAR LA SEMILLA, no hay ninguna semilla apuntada/);
});

test("lo que el papel dice y no se puede apuntar se enseña aparte", async () => {
  const html = await htmlDeUnaSemilla({
    propuesta: {
      como_se_leyo_texto: "Leído de la foto de la etiqueta",
      resumen_campos: "",
      idioma_texto: "",
      avisos: [],
      dudas: ["De la caducidad la etiqueta solo dice 02/2027 (mes y año)"],
      campos_leidos: ["especie"],
    },
  });
  assert.match(html, /Lo que dice el papel y no he podido apuntar/);
  assert.match(html, /solo dice 02\/2027/);
});

test("el filete de la foto está siempre, y solo al corregir se ofrece guardar el papel", async () => {
  const nueva = await htmlDeUnaSemilla();
  assert.ok(idsDe(nueva).includes("semilla-foto"), "no se puede leer una etiqueta sin poder subirla");
  assert.ok(accionesDe(nueva).includes("semilla-leer-foto"));
  assert.ok(!accionesDe(nueva).includes("semilla-subir-foto"), "todavía no hay semilla con la que guardarla");

  const corrigiendo = await htmlDeUnaSemilla({ corrigiendo: true, semillaId: 4 });
  assert.match(corrigiendo, /Corregir esta semilla/);
  assert.ok(accionesDe(corrigiendo).includes("semilla-subir-foto"));
  assert.ok(accionesDe(corrigiendo).includes("semilla-ver-foto"));
});

test("la puerta para sembrar una semilla sale solo cuando la semilla ya existe", async () => {
  // **Esta puerta faltaba, y se descubrió al escribir la prueba que pulsa los botones de guardar**
  // (`interfaz.test.js`): el manejador atendía `siembra-nueva`, el texto estaba escrito y la pantalla
  // del formulario existía, pero **ninguna pantalla pintaba el botón**, así que no había forma de
  // llegar a sembrar. Es la familia de fallo que este proyecto persigue: un dato que existe y una
  // puerta que falta.
  const sinGuardar = await htmlDeUnaSemilla();
  assert.ok(
    !accionesDe(sinGuardar).includes("siembra-nueva"),
    "no se puede sembrar una semilla que todavía no está guardada",
  );

  const guardada = await htmlDeUnaSemilla({ semillaId: 4, corrigiendo: true });
  assert.ok(
    accionesDe(guardada).includes("siembra-nueva"),
    "no hay ningún botón que lleve al formulario de sembrar",
  );
  assert.match(guardada, /SEMBRAR ESTA SEMILLA/);
  // Y el botón lleva el identificador de la semilla: sin él, la aplicación no sabría qué se siembra.
  assert.match(guardada, /data-accion="siembra-nueva"[^>]*data-id="4"/);
});

// ---------------------------------------------------------------------------
// Lo que se ha sembrado
// ---------------------------------------------------------------------------

test("la lista de siembras sale con su título y el aviso de que está vacía", async () => {
  const html = await htmlDeLasSiembras();
  assert.match(html, /Lo que he sembrado/);
  assert.match(html, /Todavía no has apuntado ninguna siembra/);
});

test("sin semillas dadas de alta, el aviso lleva el botón que lo arregla", async () => {
  const html = await htmlDeLasSiembras({ puedeSembrar: false });
  assert.match(html, /Todavía no tienes ninguna semilla dada de alta/);
  assert.ok(accionesDe(html).includes("semilla-nueva"), "el aviso deja al agricultor sin salida");
});

test("una siembra sale con sus dos cifras, cada una con su nombre", async () => {
  const html = await htmlDeLasSiembras({
    tarjetas: [
      {
        id: 2,
        etiqueta: "El Prado",
        rotulo: "01/03/2026",
        lineas: ["Veza común Villalobos", "1,00 ha"],
        filas: [
          { etiqueta: "Cuánto se siembra en cada hectárea", valor: "200,00 kg/ha" },
          { etiqueta: "Cuánto se ha gastado en total", valor: "200,00 kg" },
        ],
        avisos: [],
      },
    ],
    resumen: "Tienes 1 siembra apuntada.",
  });
  assert.match(html, /Cuánto se siembra en cada hectárea/);
  assert.match(html, /Cuánto se ha gastado en total/);
  assert.match(html, /200,00 kg\/ha/);
  assert.match(html, /Tienes 1 siembra apuntada/);
  assert.ok(accionesDe(html).includes("siembra-abrir"));
});

// ---------------------------------------------------------------------------
// El formulario de una siembra: la dosis no es el total
// ---------------------------------------------------------------------------

test("la dosis por hectárea y la cantidad total son dos campos distintos y con su unidad", async () => {
  const html = await htmlDeUnaSiembra();
  const ids = idsDe(html);
  for (const id of [
    "siembra-tierra",
    "siembra-fecha",
    "siembra-superficie",
    "siembra-dosis",
    "siembra-unidad-dosis",
    "siembra-cantidad",
    "siembra-unidad-cantidad",
    "siembra-envase",
    "siembra-notas",
  ]) {
    assert.ok(ids.includes(id), `falta el campo ${id}`);
  }
  // **Y son dos, no uno**: cada uno con su etiqueta y con su propia unidad, que es lo que impide que
  // un día se lean como el mismo número (el error de diez veces del ticket).
  assert.ok(ids.includes("siembra-dosis") && ids.includes("siembra-cantidad"));
  assert.match(html, /Cuánto se siembra en cada hectárea/);
  assert.match(html, /Cuánto se ha gastado en total/);
  assert.match(html, /Lo que siembras en cada hectárea. No es lo que has gastado en total/);
  // Y la unidad de cada una se elige en su propio desplegable.
  assert.match(html, /En qué se mide<\/label>/);
  assert.match(html, /En qué se mide el total<\/label>/);
});

test("los números de una siembra se piden con el teclado de números del móvil", async () => {
  const html = await htmlDeUnaSiembra();
  for (const id of ["siembra-superficie", "siembra-dosis", "siembra-cantidad"]) {
    const campo = html.split(`id="${id}"`)[1].split(">")[0];
    assert.match(campo, /inputmode="decimal"/i, `${id} no pide el teclado de números`);
  }
});

test("lo que ha calculado el programa se dice, con su explicación", async () => {
  const sin = await htmlDeUnaSiembra();
  assert.doesNotMatch(sin, /Lo ha calculado el programa/);

  const con = await htmlDeUnaSiembra({
    calculado: {
      cantidad_total: true,
      dosis_por_ha: false,
      total_en_palabras: "La cantidad total la he calculado yo: 200,00 kg/ha por 1,00 hectáreas son 200,00 kg.",
      dosis_en_palabras: "",
    },
  });
  assert.match(con, /Lo ha calculado el programa/);
  assert.match(con, /200,00 kg\/ha por 1,00 hectáreas son 200,00 kg/);
  assert.match(con, /si no es así, cámbialo/);
});

test("la semilla de la que sale no es un desplegable: ya viene elegida", async () => {
  const html = await htmlDeUnaSiembra();
  assert.match(html, /Veza común Villalobos/);
  assert.ok(!idsDe(html).includes("siembra-semilla"), "la semilla no se elige dos veces");
});

test("el envase del que sale se elige de los que tiene esa semilla", async () => {
  const html = await htmlDeUnaSiembra({
    envases: [
      { valor: 7, texto: "4471-A (te quedan 320 kg)" },
      { valor: 9, texto: "Sin número (no se sabe lo que queda)" },
    ],
  });
  const select = html.split('id="siembra-envase"')[1].split("</select>")[0];
  assert.match(select, /4471-A \(te quedan 320 kg\)/);
  assert.match(select, /Sin número/);
  assert.match(select, /No sé de qué envase sale/);
});

test("lo que queda de la semilla lo dice el servidor, y si no se sabe, se dice", async () => {
  const con = await htmlDeUnaSiembra({ quedar: { saldo: 320, unidad: "kg", motivo: "" } });
  assert.match(con, /Lo que te queda/);
  assert.match(con, /320 kg/);

  const sin = await htmlDeUnaSiembra({
    quedar: { saldo: null, unidad: null, motivo: "Falta la cantidad de una entrada." },
  });
  assert.match(sin, /No se puede saber lo que queda/);
  assert.match(sin, /Falta la cantidad de una entrada/);
});

test("la lista de siembras enseña la cuenta que ha hecho el servidor", async () => {
  // **Esto lo cazó la revisión del T10.** El aviso con la cuenta (`… son 300,00 kg`) solo viene en la
  // respuesta de guardar: al volver a leer la siembra ya no está. Si la pantalla lo tira, el
  // agricultor lee un total que no ha escrito él como si lo hubiera escrito él, y no puede revisarlo.
  const conCuenta = await htmlDeLasSiembras({
    aviso: "Siembra apuntada",
    calculado: {
      cantidad_total: true,
      dosis_por_ha: false,
      total_en_palabras:
        "La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg.",
      dosis_en_palabras: "",
      avisos: ["La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg."],
    },
    avisos: [
      "La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg.",
      "La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg.",
    ],
  });
  assert.match(conCuenta, /Lo ha calculado el programa/);
  assert.match(conCuenta, /120,00 kg\/ha por 2,50 hectáreas son 300,00 kg/);
  assert.match(conCuenta, /si no es así, cámbialo/);
  // La frase no se repite dos veces (una por el cuadro y otra por la lista de avisos).
  assert.equal(
    (conCuenta.match(/Lo ha calculado el programa/g) || []).length,
    1,
    "el cuadro de lo calculado sale dos veces",
  );

  const sinNada = await htmlDeLasSiembras();
  assert.doesNotMatch(sinNada, /Lo ha calculado el programa/);
});

test("la lista de siembras no lleva ni una frase escrita a mano", async () => {
  const delServidor = new Set(todosLosTextos(TEXTOS));
  for (const texto of [...delServidor]) {
    delServidor.add(texto.replace(/\{[a-z_]+\}/g, "3"));
  }
  const html = await htmlDeLasSiembras({
    aviso: "Siembra apuntada",
    calculado: {
      cantidad_total: true,
      dosis_por_ha: false,
      total_en_palabras:
        "La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg.",
      dosis_en_palabras: "",
      avisos: ["La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg."],
    },
  });
  const permitidas = new Set([
    "Siembra apuntada",
    "La cantidad total la he calculado yo: 120,00 kg/ha por 2,50 hectáreas son 300,00 kg.",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(
      delServidor.has(frase) || permitidas.has(frase),
      `frase escrita a mano en la lista de siembras: «${frase}»`,
    );
  }
});

test("el botón de anular solo sale al corregir, y pide el motivo", async () => {
  const nueva = await htmlDeUnaSiembra();
  assert.ok(!accionesDe(nueva).includes("siembra-anular"));
  assert.ok(!idsDe(nueva).includes("siembra-motivo"));

  const corrigiendo = await htmlDeUnaSiembra({ corrigiendo: true });
  assert.match(corrigiendo, /Corregir esta siembra/);
  assert.ok(accionesDe(corrigiendo).includes("siembra-anular"));
  assert.ok(idsDe(corrigiendo).includes("siembra-motivo"));
  assert.match(corrigiendo, /Una siembra no se borra: se anula y queda dicho por qué/);
});

test("lo que el servidor dice de una siembra que no descuenta no se cambia aquí", async () => {
  const html = await htmlDeUnaSiembra({
    aviso: "",
  });
  assert.ok(!/Esta siembra no ha descontado nada/.test(html), "el formulario no inventa estados");
});

// ---------------------------------------------------------------------------
// Ni una frase escrita a mano
// ---------------------------------------------------------------------------

test("las cuatro pantallas usan los textos del servidor y no frases propias", async () => {
  const delServidor = new Set(todosLosTextos(TEXTOS));
  for (const texto of [...delServidor]) {
    // Los huecos que `app.js` rellena con datos no cambian la frase: se aceptan la plantilla entera y
    // las frases que salen de meterle dentro lo que el servidor ha contestado (un número, un idioma).
    delServidor.add(texto.replace(/\{[a-z_]+\}/g, "3"));
    delServidor.add(texto.replace(/\{[a-z_]+\}/g, "español"));
  }
  // Lo que la pantalla recibe ya montado (lo prepara `app.js` con textos del servidor) y lo que son
  // datos, no frases.
  const permitidas = new Set([
    "Veza común Villalobos",
    "Veza común · Villalobos",
    "El Prado",
    "4471-A",
    "4471-A (te quedan 320 kg)",
    "Sin número (no se sabe lo que queda)",
    "200,00 kg/ha",
    "200,00 kg",
    "320 kg",
    "Te queda 320 kg",
    "1,00 ha",
    "01/03/2026",
    "92 %",
    "Mira las tildes",
    "La pureza no viene en el papel",
    "De la caducidad la etiqueta solo dice 02/2027 (mes y año)",
    "Falta la cantidad de una entrada.",
    "Lo que dice el papel y no he podido apuntar",
    "La cantidad total la he calculado yo: 200,00 kg/ha por 1,00 hectáreas son 200,00 kg.",
    "kg/ha",
    "kg",
    "-",
    "·",
  ]);
  const pantallas = [
    await htmlDeLasSemillas({
      tarjetas: [
        {
          id: 4,
          etiqueta: "Veza común Villalobos",
          rotulo: "Veza común · Villalobos",
          lineas: ["Te queda 320 kg"],
          filas: [{ etiqueta: "Poder germinativo", valor: "92 %" }],
          avisos: ["La pureza no viene en el papel"],
        },
      ],
      resumen: "Tienes 1 semilla dada de alta.",
    }),
    await htmlDeUnaSemilla({
      borrador: { nombre: "Veza común" },
      propuesta: {
        como_se_leyo_texto: "Leído de la foto de la etiqueta",
        resumen_campos: "He podido leer 1 dato de la etiqueta.",
        idioma_texto: "Leído con el idioma español",
        avisos: ["Mira las tildes"],
        dudas: ["De la caducidad la etiqueta solo dice 02/2027 (mes y año)"],
        campos_leidos: ["especie"],
      },
      unidades_dosis: [{ valor: "kg/ha", texto: "kg/ha" }],
    }),
    await htmlDeLasSiembras({
      tarjetas: [
        {
          id: 2,
          etiqueta: "El Prado",
          rotulo: "01/03/2026",
          lineas: ["Veza común Villalobos"],
          filas: [{ etiqueta: "Cuánto se siembra en cada hectárea", valor: "200,00 kg/ha" }],
          avisos: [],
        },
      ],
      resumen: "Tienes 1 siembra apuntada.",
    }),
    await htmlDeUnaSiembra({
      calculado: {
        cantidad_total: true,
        dosis_por_ha: false,
        total_en_palabras: "La cantidad total la he calculado yo: 200,00 kg/ha por 1,00 hectáreas son 200,00 kg.",
        dosis_en_palabras: "",
      },
      quedar: { saldo: 320, unidad: "kg", motivo: "" },
      corrigiendo: true,
    }),
  ];
  for (const html of pantallas) {
    for (const frase of frasesVisibles(html)) {
      assert.ok(
        delServidor.has(frase) || permitidas.has(frase),
        `frase escrita a mano en una pantalla de semillas: «${frase}»`,
      );
    }
  }
});

// ===========================================================================
// 4. El camino de guardar, con los botones PULSADOS DE VERDAD
//
// POR QUÉ ESTE APARTADO, Y ES UNA CORRECCIÓN DE LA REVISIÓN DEL T10
//
// Todo lo de arriba pinta las pantallas con `renderToStaticMarkup` y mira lo que **salen**: sus
// campos, sus textos, sus opciones. Eso está bien, pero **no dice nada de si el botón hace algo**: se
// puede pintar un botón con su `data-accion` perfecto y que el manejador de clics no lo atienda, o que
// lo atienda y mande la mitad de los datos. La revisión lo midió buscando estas acciones en los seis
// ficheros de `tests_js/`: **`semilla-guardar`, `siembra-guardar` y `siembra-anular` no los pulsaba
// nadie**. Y es justo donde vivía el defecto 8 (la cuenta del servidor se tiraba antes de pintar).
//
// Aquí se pulsan **de verdad**: se despacha el clic por el manejador delegado que lee `data-accion`
// —el mismo camino que recorre un dedo en el móvil—, y se mira **lo que sale por la puerta** (el
// cuerpo de la petición que llega al servidor de mentira). Llamar a la función de guardar directamente
// no valdría: la prueba pasaría aunque el botón estuviera mal cableado, que es lo que hay que cazar.
//
// Y EL ARNÉS, QUE ES UNA COPIA PEQUEÑA A PROPÓSITO
//
// El DOM de mentira y el servidor de mentira completos viven en `tests_js/interfaz.test.js`, que es
// donde están las pruebas de toda la interfaz. Aquí hay **una copia reducida a lo que estas pruebas
// necesitan** (un DOM con los cuatro nodos que `app.js` busca, `localStorage` con el vale puesto, y un
// `fetch` que apunta lo que se manda). Se copia y no se importa a propósito: importar aquel fichero
// **registraría sus 300 pruebas dos veces** dentro de esta ejecución. Lo que se comparte de verdad —el
// apuntador de montajes— sí se importa (`web/react/montar.js`), que es de donde lo lee la aplicación.
// ===========================================================================

/** Los cuatro nodos que `app.js` busca al arrancar, y nada más. */
function crearNodo(id = "") {
  const clases = new Set();
  return {
    id,
    innerHTML: "",
    textContent: "",
    className: "",
    dataset: {},
    classList: {
      add: (c) => clases.add(c),
      remove: (c) => clases.delete(c),
      contains: (c) => clases.has(c),
      toggle: () => {},
    },
    appendChild() {},
    remove() {},
    click() {},
  };
}

function montarEntorno() {
  const nodos = new Map();
  for (const id of ["pantalla", "aviso-pendientes", "cabecera-texto", "pie", "marco"]) {
    nodos.set(id, crearNodo(id));
  }
  const almacen = new Map();
  almacen.set("cuedigital.token", "token-de-prueba");
  const manejadores = {};
  const entorno = {
    nodos,
    manejadores,
    document: {
      getElementById: (id) => nodos.get(id) || null,
      createElement: () => crearNodo(),
      addEventListener: (tipo, manejador) => {
        manejadores[tipo] = manejador;
      },
      body: crearNodo("body"),
    },
    window: {
      addEventListener: (tipo, manejador) => {
        manejadores[tipo] = manejador;
      },
      scrollTo() {},
      confirm: () => true,
      location: { hash: "" },
      history: {
        pushState(_e, _t, url) {
          entorno.window.location.hash = url;
        },
        replaceState(_e, _t, url) {
          entorno.window.location.hash = url;
        },
      },
      localStorage: {
        getItem: (clave) => (almacen.has(clave) ? almacen.get(clave) : null),
        setItem: (clave, valor) => almacen.set(clave, String(valor)),
        removeItem: (clave) => almacen.delete(clave),
      },
    },
    navigator: { onLine: true },
    URL: { createObjectURL: () => "blob:x", revokeObjectURL() {} },
  };
  return entorno;
}

/** Una respuesta que dice que no, como la del servidor de verdad (`{detail: …}` y su estado). */
function falla(detalle, estado = 400) {
  return { FALLA: { detail: detalle }, ESTADO: estado };
}

/**
 * El servidor de mentira: apunta lo que se le pide y contesta lo que dice la tabla.
 *
 * `retener` es la lista de rutas (`"POST /api/siembras/7/anular"`) cuyas respuestas se quedan **en el
 * aire** hasta que la prueba las suelta con `suelta()`: es la única forma de probar el doble toque de
 * verdad (el segundo toque con la primera petición todavía sin contestar), que es cuando el botón se
 * deshabilita. Las demás rutas contestan al momento, o la aplicación no llega ni a arrancar.
 */
function montarServidor(respuestas = {}, { retener = [] } = {}) {
  const llamadasConMetodo = [];
  const enviados = [];
  const pendientes = [];
  const fetchFalso = (ruta, opciones = {}) => {
    const metodo = (opciones.method || "GET").toUpperCase();
    llamadasConMetodo.push(`${metodo} ${ruta}`);
    let enviado = null;
    if (typeof opciones.body === "string" && opciones.body) {
      try {
        enviado = JSON.parse(opciones.body);
      } catch (error) {
        enviado = opciones.body;
      }
    }
    enviados.push({ metodo, ruta, cuerpo: enviado });
    // La tabla se mira **con el método delante** (`"POST /api/semillas"`) y, si ahí no está, por la
    // ruta a secas (`"/api/semillas"`, que es la lista); y si no está en ninguna, una lista vacía, que
    // es lo que contesta el servidor de verdad a una finca sin nada apuntado.
    const conMetodo = respuestas[`${metodo} ${ruta}`];
    const crudo = conMetodo !== undefined ? conMetodo : respuestas[ruta] !== undefined ? respuestas[ruta] : [];
    const contestar = () => {
      if (crudo && typeof crudo === "object" && "FALLA" in crudo) {
        return {
          ok: false,
          status: crudo.ESTADO || 400,
          headers: { get: () => "application/json" },
          json: async () => crudo.FALLA,
          text: async () => JSON.stringify(crudo.FALLA),
          blob: async () => ({ size: 0 }),
        };
      }
      return {
        ok: crudo !== undefined,
        status: crudo !== undefined ? 200 : 404,
        headers: { get: () => "application/json" },
        json: async () => crudo,
        text: async () => JSON.stringify(crudo),
        blob: async () => ({ size: 0 }),
      };
    };
    if (!retener.includes(`${metodo} ${ruta}`)) return Promise.resolve(contestar());
    return new Promise((resolver) => pendientes.push(() => resolver(contestar())));
  };
  const suelta = () => {
    const enElAire = pendientes.splice(0, pendientes.length);
    for (const resolver of enElAire) resolver();
  };
  return { fetchFalso, llamadasConMetodo, enviados, suelta };
}

/**
 * Arranca la aplicación de verdad (`web/app.js`) con el DOM y el servidor de mentira.
 *
 * Se importa con marca en la URL para que cada prueba arranque de cero, igual que hace
 * `interfaz.test.js`: Node no reutiliza el módulo y el estado de la aplicación empieza limpio.
 */
async function arrancarCon(respuestas = {}, { retener = [] } = {}) {
  const entorno = montarEntorno();
  const servidor = montarServidor(respuestas, { retener });
  const definir = (nombre, valor) =>
    Object.defineProperty(globalThis, nombre, { value: valor, configurable: true, writable: true });
  definir("document", entorno.document);
  definir("window", entorno.window);
  definir("navigator", entorno.navigator);
  definir("URL", entorno.URL);
  definir("fetch", servidor.fetchFalso);
  definir("localStorage", entorno.window.localStorage);
  await import(`../web/app.js?semillas=${Math.random()}`);
  await new Promise((resolver) => setTimeout(resolver, 80));
  return { entorno, servidor };
}

/**
 * Pulsa un botón **por el mismo camino que un dedo**: el manejador delegado que lee `data-accion`.
 *
 * `elemento.dataset` es lo que el manejador lee (`data-id`, `data-campo`, `data-valor`…), y `closest`
 * devuelve el propio elemento porque en la aplicación el clic se busca desde el objetivo hacia arriba.
 */
async function pulsar(entorno, accion, datos = {}) {
  const elemento = { dataset: { accion, ...datos } };
  elemento.closest = () => elemento;
  await entorno.manejadores.click({ target: { closest: () => elemento } });
  await new Promise((resolver) => setTimeout(resolver, 40));
}

/** Escribe en una casilla del formulario, como lo haría el agricultor con el teclado. */
function escribir(entorno, id, valor) {
  const nodo = entorno.nodos.get(id) || { id, value: "" };
  nodo.value = valor;
  entorno.nodos.set(id, nodo);
}

/** La última pantalla que se le ha pedido a React. */
function ultimoMontaje() {
  return montajes[montajes.length - 1].elemento;
}

/** Cuántas veces se ha llamado a una ruta con un método (`"POST /api/…"`). */
function cuantasVeces(servidor, metodoYRuta) {
  return servidor.llamadasConMetodo.filter((una) => una === metodoYRuta).length;
}

/** Lo que se ha mandado a una ruta (la última vez). */
function loMandado(servidor, ruta, metodo = "POST") {
  const deEsa = servidor.enviados.filter((uno) => uno.metodo === metodo && uno.ruta === ruta);
  return deEsa[deEsa.length - 1];
}

/** Una semilla como la devuelve `GET /api/semillas`. */
function unaSemillaGuardada(cambios = {}) {
  return {
    id: 4,
    articulo_id: 9,
    nombre: "Veza común Villalobos",
    unidad: "kg",
    categoria: "semilla",
    especie: "Veza común",
    variedad: "Villalobos",
    casa_comercial: "Semillas del Duero",
    proveedor: null,
    numero_lote_proveedor: "4471-A",
    dosis_recomendada_por_ha: 120.0,
    unidad_dosis: "kg/ha",
    fecha_envasado: null,
    fecha_caducidad: "2028-01-12",
    poder_germinativo_pct: 92.0,
    pureza_pct: null,
    tratada: false,
    leida_de: "mano",
    idioma_del_lector: null,
    tiene_foto: false,
    creada_en: "2026-01-20T10:00:00",
    queda: { saldo: 500.0, unidad: "kg", motivo: "", motivo_codigo: "", cuantos_lotes: 1 },
    envases: [
      {
        lote_id: 8,
        numero_lote: "4471-A",
        fecha_caducidad: "2028-01-12",
        caducado: false,
        presentacion: "saco",
        saldo: 500.0,
        unidad: "kg",
        motivo: "",
      },
    ],
    siembras: 0,
    ...cambios,
  };
}

/** Una siembra como la devuelve `GET /api/siembras`. */
function unaSiembraGuardada(cambios = {}) {
  return {
    id: 7,
    semilla_id: 4,
    parcela_id: 1,
    lote_id: 8,
    fecha: "2026-03-01",
    superficie_ha: 1.0,
    dosis_por_ha: 200.0,
    unidad_dosis: "kg/ha",
    cantidad_total: 200.0,
    unidad_cantidad: "kg",
    dosis_calculada: false,
    cantidad_total_calculada: false,
    notas: null,
    anulada: false,
    motivo_anulacion: null,
    creada_en: "2026-03-01T09:00:00",
    semilla: "Veza común Villalobos",
    tierra: "El Prado",
    numero_lote: "4471-A",
    descuenta: true,
    no_descuenta_porque: null,
    movimiento_id: 3,
    avisos: [],
    ...cambios,
  };
}

/**
 * Lo que la aplicación pide al arrancar, para que arranque de verdad.
 *
 * `app.js` pide el vocabulario y los datos de la finca al empezar; con esto contesta lo mínimo y las
 * listas que estas pruebas necesitan. Lo que no esté en la tabla contesta una lista vacía (que es lo
 * que hace el servidor de verdad con una finca sin nada apuntado).
 */
function lasRespuestasDeArranque(cambios = {}) {
  return {
    "/api/interfaz": {
      semillas: TEXTOS.semillas,
      mensajes: TEXTOS.mensajes,
      unidades_dosis_semilla: ["kg/ha", "g/ha", "ud/ha", "L/ha"],
      unidades_cantidad_semilla: ["kg", "g", "ud", "L"],
      acciones: {},
      aviso: {},
      etiquetas: {},
      rotulos: {},
      menu: {},
      marco: {},
    },
    "/api/campanas/actual": { id: 1, anio: 2026 },
    "/api/parcelas": [{ id: 1, alias: "El Prado", superficie_ha: 2.43 }],
    ...cambios,
  };
}

// ---------------------------------------------------------------------------
// Los tres botones: uno por uno
// ---------------------------------------------------------------------------

test("al pulsar GUARDAR LA SEMILLA se manda lo que ha escrito el agricultor", async () => {
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({ "POST /api/semillas": unaSemillaGuardada() }),
  );
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-nueva");
  assert.equal(ultimoMontaje().type.name, "PantallaDeUnaSemilla", "no se abre la ficha");

  escribir(entorno, "semilla-nombre", "Veza común Villalobos");
  escribir(entorno, "semilla-especie", "Veza común");
  escribir(entorno, "semilla-variedad", "Villalobos");
  escribir(entorno, "semilla-dosis", "120");
  escribir(entorno, "semilla-unidad-dosis", "kg/ha");
  escribir(entorno, "semilla-pureza", ""); // el papel no la trae
  escribir(entorno, "semilla-tratada", "no_se"); // y no se sabe si viene tratada
  await pulsar(entorno, "semilla-guardar");

  assert.equal(cuantasVeces(servidor, "POST /api/semillas"), 1, "el botón no manda la semilla");
  const cuerpo = loMandado(servidor, "/api/semillas").cuerpo;
  assert.equal(cuerpo.nombre, "Veza común Villalobos", "el nombre escrito no llega");
  assert.equal(cuerpo.especie, "Veza común");
  assert.equal(cuerpo.dosis_recomendada_por_ha, 120, "la dosis no llega como número");
  assert.equal(cuerpo.unidad_dosis, "kg/ha");
  assert.equal(cuerpo.pureza_pct, null, "un hueco se está guardando como un número");
  assert.equal(cuerpo.tratada, null, "«no lo sé» se está guardando como «no»");
  assert.equal(cuerpo.leida_de, "mano");
});

test("si el servidor dice que no, el aviso se ve y el formulario NO se vacía", async () => {
  // **Esto es lo que hace que alguien pueda corregir sin volver a teclearlo todo**, y es una de las
  // cosas que la revisión pedía: al guardar y fallar, la pantalla se vuelve a pedir a React, y si lo
  // que había escrito el agricultor no viaja en esa petición, **lo pierde**.
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "POST /api/semillas": falla("Esa semilla ya está apuntada. Mírala en tu lista."),
    }),
  );
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-nueva");
  escribir(entorno, "semilla-nombre", "Veza común Villalobos");
  escribir(entorno, "semilla-especie", "Veza común");
  escribir(entorno, "semilla-dosis", "120");
  escribir(entorno, "semilla-unidad-dosis", "kg/ha");
  await pulsar(entorno, "semilla-guardar");

  assert.equal(cuantasVeces(servidor, "POST /api/semillas"), 1);
  const pantalla = ultimoMontaje();
  assert.equal(pantalla.type.name, "PantallaDeUnaSemilla", "se ha salido de la ficha al fallar");
  assert.equal(pantalla.props.error, "Esa semilla ya está apuntada. Mírala en tu lista.", "el motivo no se ve");
  assert.equal(pantalla.props.borrador.nombre, "Veza común Villalobos", "el formulario se ha vaciado");
  assert.equal(pantalla.props.borrador.especie, "Veza común", "se ha perdido lo escrito");
  assert.equal(pantalla.props.borrador.dosis_recomendada_por_ha, "120");
});

test("al pulsar GUARDAR LA SIEMBRA se manda con el envase del que sale", async () => {
  // **El envase es lo que hace que la semilla salga del almacén.** Una siembra sin `lote_id` no
  // descuenta nada, y por eso esta prueba mira el cuerpo que sale por la puerta: la de pantalla sola
  // no lo cazaba porque nunca se pulsaba el botón.
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/semillas": [unaSemillaGuardada()],
      "POST /api/siembras": unaSiembraGuardada({ cantidad_total_calculada: true }),
    }),
  );
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "semilla-abrir", { id: 4 });
  await pulsar(entorno, "siembra-nueva", { id: 4 });
  assert.equal(ultimoMontaje().type.name, "PantallaDeUnaSiembra", "no se abre el formulario de sembrar");

  escribir(entorno, "siembra-tierra", "1");
  escribir(entorno, "siembra-fecha", "2026-03-01");
  escribir(entorno, "siembra-superficie", "2,5");
  escribir(entorno, "siembra-dosis", "120");
  escribir(entorno, "siembra-unidad-dosis", "kg/ha");
  escribir(entorno, "siembra-cantidad", "");
  escribir(entorno, "siembra-unidad-cantidad", "kg");
  escribir(entorno, "siembra-envase", "8");
  await pulsar(entorno, "siembra-guardar");

  assert.equal(cuantasVeces(servidor, "POST /api/siembras"), 1, "el botón no manda la siembra");
  const cuerpo = loMandado(servidor, "/api/siembras").cuerpo;
  assert.equal(cuerpo.lote_id, 8, "la siembra se manda SIN envase: no descontaría del almacén");
  assert.equal(cuerpo.parcela_id, 1);
  assert.equal(cuerpo.dosis_por_ha, 120);
  assert.equal(cuerpo.cantidad_total, null, "el total vacío se manda como un cero");
  assert.equal(cuerpo.unidad_cantidad, "kg");
  assert.equal(cuerpo.superficie_ha, 2.5, "la coma del móvil no se entiende");
  assert.ok(cuerpo.clave_de_reenvio, "la siembra no viaja con su marca de reenvío");
  assert.equal(cuerpo.aceptar_descuadre, false);
});

test("al pulsar ANULAR se manda una sola vez, y un segundo toque no manda otra", async () => {
  // **El doble toque.** El segundo toque se da **con la primera petición todavía en el aire** (el
  // servidor de mentira las retiene hasta que se le dice), que es cuando de verdad pasa: en cuanto
  // contesta, la pantalla ya no es el formulario y el botón no está. Y el botón se deshabilita mientras
  // guarda (eso se comprueba abajo, en el componente): las dos cosas juntas son las que hacen que una
  // siembra no se anule dos veces.
  const { entorno, servidor } = await arrancarCon(
    lasRespuestasDeArranque({
      "/api/siembras": [unaSiembraGuardada()],
      "POST /api/siembras/7/anular": unaSiembraGuardada({ anulada: true, descuenta: false }),
    }),
    { retener: ["POST /api/siembras/7/anular"] },
  );
  await pulsar(entorno, "semillas-ver");
  await pulsar(entorno, "siembras-ver");
  await pulsar(entorno, "siembra-abrir", { id: 7 });
  escribir(entorno, "siembra-motivo", "Me equivoqué de tierra");

  const primera = pulsar(entorno, "siembra-anular"); // no se espera: sigue en el aire
  const segunda = pulsar(entorno, "siembra-anular"); // el segundo toque, con la primera sin contestar
  servidor.suelta();
  await primera;
  await segunda;

  assert.equal(
    cuantasVeces(servidor, "POST /api/siembras/7/anular"),
    1,
    "el doble toque ha mandado dos anulaciones de la misma siembra",
  );
  const cuerpo = loMandado(servidor, "/api/siembras/7/anular").cuerpo;
  assert.equal(cuerpo.motivo, "Me equivoqué de tierra", "el motivo no llega");
  assert.equal(ultimoMontaje().type.name, "PantallaDeLasSiembras", "después de anular no se vuelve a la lista");
});

test("el botón de anular se deshabilita mientras guarda (y eso es lo que corta el doble toque)", async () => {
  // La otra mitad de la prueba de arriba, y la que se ve en un navegador: con `guardando` puesto, el
  // botón sale `disabled`, así que un segundo dedo no dispara nada. Se comprueba en el componente
  // porque es donde se pinta.
  const conElBoton = await htmlDeUnaSiembra({ corrigiendo: true, guardando: true });
  const boton = conElBoton.split('data-accion="siembra-anular"')[1].split(">")[0];
  assert.match(boton, /disabled/, "el botón de anular sigue vivo mientras guarda: dos toques, dos anulaciones");
  const guardar = conElBoton.split('data-accion="siembra-guardar"')[1].split(">")[0];
  assert.match(guardar, /disabled/, "el botón de guardar sigue vivo mientras guarda");
});
