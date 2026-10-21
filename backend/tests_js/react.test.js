/**
 * Pruebas de la pantalla de inicio escrita en React, **sin navegador**.
 *
 * POR QUÉ ESTAS PRUEBAS EXISTEN Y DÓNDE ESTÁN
 *
 * La pantalla de inicio se pasó a React (`web/react/pantallas/inicio.js`). Las pruebas que
 * miraban su HTML desde `interfaz.test.js` ya no pueden funcionar allí: ese fichero monta un
 * DOM de mentira, y React necesita de verdad un nodo del navegador (con `ownerNode`,
 * `appendChild` real y un `innerHTML` que se pueda leer). En vez de rebajar lo que se
 * comprobaba, esas pruebas se han **reescrito aquí contra el componente**: se le piden las
 * propiedades y se mira el HTML que produce. Lo que comprobaban es exactamente lo mismo —los
 * seis botones y su orden, la clase del botón grande, los textos del servidor, el saludo, el
 * aviso de que falta la primera parcela— y además ahora se comprueba de verdad que ninguna
 * frase está escrita a mano dentro del componente.
 *
 * CÓMO SE PRUEBA SIN NAVEGADOR
 *
 * Los ficheros de `web/vendor` son UMD: se cargan con `vm.runInThisContext`, igual que los
 * carga el navegador con una etiqueta `<script>`, y dejan `React`, `htm` y `ReactDOMServer` en
 * los globales. Con `renderToStaticMarkup` se convierte un componente en HTML sin necesidad de
 * un DOM. **No hay `jsdom` ni ninguna otra dependencia**: no se mete una dependencia nueva
 * para probar una pantalla, y estas pruebas tienen que poder correr en cualquier sitio donde
 * haya Node.
 *
 * Los textos son los mismos que los de la copia de `interfaz.test.js` (allí, la clave
 * `/api/interfaz` de `RESPUESTAS`), y están copiados a propósito uno a uno: si se inventaran
 * aquí, estas pruebas comprobarían una pantalla que el agricultor no tiene.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

import { montajes, montarEn } from "../web/react/montar.js";

// ---------------------------------------------------------------------------
// El arnés: React y htm, como los deja `index.html`
// ---------------------------------------------------------------------------

// Los ficheros UMD se asignan a `self` cuando no hay un sistema de módulos, que es el caso del
// navegador. Node no tiene `self`, así que se le pone: es lo único que hace falta para que
// carguen igual que en la página.
globalThis.self = globalThis;

function cargarDeVendor(nombre) {
  const codigo = readFileSync(new URL(`../web/vendor/${nombre}`, import.meta.url), "utf8");
  vm.runInThisContext(codigo, { filename: nombre });
}

cargarDeVendor("react.production.min.js");
cargarDeVendor("htm.umd.js");
// El `react-dom` que monta en el navegador **no** se carga a propósito: así estas pruebas ven
// el mismo camino que ve el arranque sin navegador (la pantalla se le pide a React, pero no se
// monta). El caso «sí hay ReactDOM» se prueba aparte, con un ReactDOM de mentira.
cargarDeVendor("react-dom-server-legacy.browser.production.min.js");

const React = globalThis.React;

// ---------------------------------------------------------------------------
// Los textos: los mismos que sirve el servidor
// ---------------------------------------------------------------------------

/**
 * Los botones de la pantalla de inicio, tal y como los sirve `/api/interfaz`.
 *
 * Son los mismos textos que la copia de `interfaz.test.js` (allí, `BOTONES`), pero con las
 * pistas **enteras**: aquella copia recorta algunas para que las líneas no se hagan largas, y
 * aquí se copian tal y como las lee el agricultor. Una prueba de Python (`test_interfaz.py`,
 * «la copia nueva lleva los textos de la pantalla de inicio») avisa si esta copia se queda
 * atrás o dice otra cosa.
 */
const BOTONES = [
  { id: "echar_producto", icono: "💧", texto: "HE ECHADO PRODUCTO", pista: "bichos, hierbas, hongos", principal: true },
  { id: "abonar", icono: "🟤", texto: "HE ABONADO", pista: "abono para la tierra", principal: false },
  { id: "trabajo", icono: "🚜", texto: "HE HECHO UN TRABAJO", pista: "sembrar, regar, coger", principal: false },
  { id: "mi_cuaderno", icono: "📖", texto: "MI CUADERNO", pista: "ver lo que tengo apuntado", principal: false },
  { id: "papel", icono: "🖨️", texto: "SACAR EN PAPEL", pista: "para imprimir", principal: false },
  { id: "ayuda", icono: "❓", texto: "NO SÉ QUÉ PULSAR", pista: "te lo explico", principal: false },
];

const TEXTOS = {
  inicio: {
    saludo: "Hola",
    pregunta: "¿Qué has hecho hoy?",
    botones: BOTONES,
    repetir: {
      texto: "LO MISMO QUE LA ÚLTIMA VEZ",
      vacio: "Todavía no has apuntado nada. Empieza por el botón grande de arriba y en dos preguntas lo tienes.",
      sin_poder_repetir:
        "Este año ya has apuntado cosas, pero ningún tratamiento: el atajo de repetir sale con el primero que apuntes.",
    },
  },
  maestros: {
    antes_de_empezar: "Antes de empezar",
    falta_parcela: "Para poder apuntar cualquier cosa hace falta tener al menos una parcela. Se tarda un minuto.",
    anadir_primera_parcela: "AÑADIR MI PRIMERA PARCELA",
    mis_cosas: "MIS PARCELAS, PRODUCTOS Y MÁQUINAS",
  },
  dictado: {
    titulo: "Dímelo con la voz",
    pista_boton: "cuéntamelo con tus palabras",
  },
};

/**
 * Los textos de la salida de emergencia, los de `textos.REACT`.
 *
 * Estos no los usa el componente (los usa `montar.js`, y le llegan por su tercer argumento),
 * por eso están aparte de `TEXTOS`: el componente tiene que funcionar con los tres bloques y
 * nada más.
 */
const TEXTOS_DE_REACT = {
  sin_react: "Esta pantalla no se ha podido abrir. Vuelve a abrir la aplicación; si sigue igual, dile a quien te la instaló que falta un fichero del programa.",
  recargar: "VOLVER A ABRIRLA",
};

/** Una copia nueva de los textos: cada prueba puede tocarla sin estropear las demás. */
function textosDePrueba() {
  return structuredClone(TEXTOS);
}

/** Carga el componente con marca en la URL, igual que `interfaz.test.js` carga `app.js`. */
async function cargarInicio() {
  return import(`../web/react/pantallas/inicio.js?prueba=${Math.random()}`);
}

/** Las propiedades de la pantalla, con lo que quiera cambiar cada prueba. */
function propiedades(cambios = {}) {
  return {
    textos: textosDePrueba(),
    nombre: "",
    campana: null,
    hayParcelas: true,
    hayUltimo: false,
    ...cambios,
  };
}

/** El HTML de la pantalla, tal y como lo dibujaría React. */
async function htmlDeInicio(cambios = {}) {
  const { PantallaInicio } = await cargarInicio();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaInicio, propiedades(cambios)),
  );
}

// ---------------------------------------------------------------------------
// Un lector de botones: para mirar el HTML como lo miraría una persona
// ---------------------------------------------------------------------------

/**
 * Saca los botones del HTML con sus clases, sus acciones y sus textos.
 *
 * Se hace así, y no con búsquedas de texto sueltas, porque lo que importa es **qué botón**
 * lleva cada cosa: que haya un `data-ir="papel"` en cualquier sitio no dice nada si está en
 * el botón equivocado. Este lector es de mentira y vive en la prueba a propósito: si el
 * componente cambiara de forma, la prueba tiene que notarlo, no acomodarse.
 *
 * `icono` es **la clave del dibujo** (el emoji que trae el texto del servidor), que desde el rediseño
 * de la ronda 76 va en el `data-icono` del cuadro. Antes se leía el contenido del `<span class="icono">`,
 * y eso ya no vale: dentro va un `<svg>` con sus trazos. Se lee la clave del atributo, que es lo que
 * dice **qué icono es**, y así las pruebas siguen comprobando lo mismo que comprobaban.
 */
function botonesDe(html) {
  const botones = [];
  for (const encontrado of html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
    const atributos = {};
    for (const atributo of encontrado[1].matchAll(/([a-z-]+)="([^"]*)"/g)) {
      atributos[atributo[1]] = atributo[2];
    }
    const cuerpo = encontrado[2];
    const etiqueta = /<span class="texto">\s*<span>([\s\S]*?)<\/span>/.exec(cuerpo);
    const pista = /<span class="pista-boton">([\s\S]*?)<\/span>/.exec(cuerpo);
    const cuadro = /<span class="icono" aria-hidden="true" data-icono="([^"]*)">([\s\S]*?)<\/span>/.exec(
      cuerpo,
    );
    const emojiSuelto = /<span class="icono" aria-hidden="true">([^<]*)<\/span>/.exec(cuerpo);
    const flecha = /<span class="flecha" aria-hidden="true">([\s\S]*?)<\/span>/.exec(cuerpo);
    botones.push({
      clases: (atributos.class || "").split(" ").filter(Boolean),
      accion: atributos["data-accion"],
      ir: atributos["data-ir"],
      tipo: atributos["data-tipo"],
      etiqueta: etiqueta ? etiqueta[1] : "",
      pista: pista ? pista[1] : "",
      icono: cuadro ? cuadro[1] : emojiSuelto ? emojiSuelto[1] : "",
      // El dibujo (el `<svg>`) tal cual, para las pruebas que quieren comprobar que hay icono dibujado.
      dibujo: cuadro ? cuadro[2] : "",
      flecha: flecha ? flecha[1] : "",
    });
  }
  return botones;
}

/** Los seis botones que manda el servidor: los que llevan `data-accion="inicio"`. */
function botonesDelServidor(html) {
  return botonesDe(html).filter((boton) => boton.accion === "inicio");
}

/**
 * Los `id` de los campos que hay en el HTML, en el orden en que salen.
 *
 * Se usa para las pantallas con campos de formulario: los `id` **no son decoración**, son la única
 * forma que tiene `app.js` de leer lo que el agricultor ha escrito. Comprobar la lista entera de una
 * vez es lo que caza que un campo se quede sin su `id` o se renombre al pasar a React.
 */
function idsDe(html) {
  // `(?<![\w-])` delante de `id=` para no confundirlo con `data-id="1"`, que **no** es el `id` de un
  // campo: es el número de la tierra a la que pertenece el botón. Se descubrió al escribir esta
  // prueba, cuando la lista de campos acabó con un «1» que no era de nadie.
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
    // Los iconos (los emoji) van entre etiquetas como cualquier texto, y no son una frase:
    // son el dibujo del botón, y ya se comprueba aparte que son los del servidor. Se quitan
    // para no confundir «una frase escrita a mano» con «un icono».
    .replace(/<span class="icono"[^>]*>[^<]*<\/span>/g, "")
    // La flecha del final del botón es igual: sale del diseño de Stitch y no dice nada con
    // palabras. Se quita por el mismo motivo, y se comprueba aparte que está y que va marcada
    // con `aria-hidden` (ver «todos los botones llevan su flecha»).
    .replace(/<span class="flecha"[^>]*>[^<]*<\/span>/g, "")
    // El signo «!» de la franja de aviso de una tarjeta de tierra (ronda 78) es lo mismo: es el
    // dibujo que avisa de que ahí hay algo que mirar, y el aviso **va escrito al lado**. Se quita
    // aquí y se comprueba aparte, en la prueba de la tarjeta, que está y que va con `aria-hidden`.
    .replace(/<span class="tarjeta-aviso-icono"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<[^>]*>/g, "\u0000")
    .split("\u0000")
    .map((trozo) => trozo.trim())
    .filter(Boolean);
}

// ---------------------------------------------------------------------------
// Los seis botones
// ---------------------------------------------------------------------------

test("la pantalla sale con los seis botones, con su texto, su icono y su destino", async () => {
  const botones = botonesDelServidor(await htmlDeInicio());

  assert.equal(botones.length, 6, `salen ${botones.length} botones y tienen que salir 6`);
  botones.forEach((boton, indice) => {
    const esperado = BOTONES[indice];
    assert.equal(boton.ir, esperado.id, `el botón ${indice + 1} no lleva a ${esperado.id}`);
    assert.equal(boton.etiqueta, esperado.texto, `el botón ${esperado.id} no dice lo que toca`);
    assert.equal(boton.pista, esperado.pista, `el botón ${esperado.id} no lleva su pista`);
    assert.equal(boton.icono, esperado.icono, `el botón ${esperado.id} no lleva su icono`);
    // Los clics los atiende el manejador delegado de `document`, que lee esta acción.
    assert.equal(boton.accion, "inicio", `el botón ${esperado.id} no lleva data-accion="inicio"`);
    assert.ok(boton.clases.includes("boton"), `el botón ${esperado.id} no es un botón de la casa`);
  });
});

test("el orden de los botones es el que trae el servidor, y no se toca", async () => {
  const html = await htmlDeInicio();
  const posiciones = BOTONES.map((boton) => html.indexOf(`data-ir="${boton.id}"`));
  for (const [indice, posicion] of posiciones.entries()) {
    assert.ok(posicion >= 0, `falta el botón ${BOTONES[indice].id}`);
    if (indice > 0) {
      assert.ok(
        posicion > posiciones[indice - 1],
        `el botón ${BOTONES[indice].id} sale antes que el anterior: se ha cambiado el orden`,
      );
    }
  }
});

test("si el servidor cambia el orden de los botones, la pantalla lo sigue", async () => {
  // El orden lo manda el servidor (hay una prueba en Python que lo blinda). El componente no
  // tiene ningún orden propio: si lo tuviera, esta prueba saldría en rojo.
  const textos = textosDePrueba();
  textos.inicio.botones = [...textos.inicio.botones].reverse();
  const botones = botonesDelServidor(await htmlDeInicio({ textos }));
  assert.deepEqual(
    botones.map((boton) => boton.ir),
    BOTONES.map((boton) => boton.id).reverse(),
  );
});

test("el único botón grande es «he echado producto»", async () => {
  const grandes = botonesDe(await htmlDeInicio()).filter((b) => b.clases.includes("boton-principal"));
  assert.equal(grandes.length, 1, `hay ${grandes.length} botones grandes y solo puede haber uno`);
  assert.equal(grandes[0].ir, "echar_producto", "el botón grande no es el de echar producto");
});

test("los botones llevan las clases de siempre, que son las que dan el color", async () => {
  const botones = botonesDe(await htmlDeInicio());
  const porAccion = Object.fromEntries(botones.map((b) => [b.ir || b.accion, b]));
  assert.deepEqual(porAccion.echar_producto.clases, ["boton", "boton-principal"]);
  assert.deepEqual(porAccion.abonar.clases, ["boton"]);
  assert.deepEqual(porAccion.trabajo.clases, ["boton"]);
  assert.deepEqual(porAccion.mi_cuaderno.clases, ["boton"]);
  assert.deepEqual(porAccion.papel.clases, ["boton"]);
  assert.deepEqual(porAccion.ayuda.clases, ["boton"]);
  // Y ninguna clase de color escrita en el componente: los colores son del `estilos.css`.
  assert.ok(!/style="/.test(await htmlDeInicio()), "hay un style= puesto a mano en el HTML");
});

// ---------------------------------------------------------------------------
// El saludo
// ---------------------------------------------------------------------------

test("el saludo lleva el nombre del titular y el año de la campaña", async () => {
  const html = await htmlDeInicio({ nombre: "Juan", campana: { anio: 2026 } });
  assert.ok(html.includes("<h1>Hola, Juan · 2026</h1>"), `el saludo no sale bien: ${html.slice(0, 80)}`);
});

test("sin nombre, el saludo va solo", async () => {
  const html = await htmlDeInicio({ nombre: "", campana: { anio: 2026 } });
  assert.ok(html.includes("<h1>Hola · 2026</h1>"), `el saludo no sale bien: ${html.slice(0, 80)}`);
  assert.ok(!html.includes("null"), "se ha escrito un null en pantalla");
});

test("si no se sabe la campaña, no se escribe un hueco raro", async () => {
  // Antes, con una campaña a medias, en la cabecera se leía « · undefined». Lo que no se sabe
  // no se escribe: es mejor un saludo corto que un saludo con basura dentro.
  const sinCampana = await htmlDeInicio({ campana: null });
  assert.ok(sinCampana.includes("<h1>Hola</h1>"));
  const campanaSinAnio = await htmlDeInicio({ campana: { id: 1 } });
  assert.ok(campanaSinAnio.includes("<h1>Hola</h1>"), "se ha escrito el año sin saberlo");
  assert.ok(!campanaSinAnio.includes("undefined"), "aparece «undefined» en pantalla");
});

// ---------------------------------------------------------------------------
// Repetir, dictado y «mis cosas»
// ---------------------------------------------------------------------------

test("con algo apuntado antes, se ofrece repetirlo", async () => {
  const html = await htmlDeInicio({ hayUltimo: true });
  const repetir = botonesDe(html).find((boton) => boton.accion === "repetir");
  assert.ok(repetir, "no se ofrece repetir teniendo algo que repetir");
  assert.ok(html.includes("LO MISMO QUE LA ÚLTIMA VEZ"));
  assert.equal(repetir.icono, "🔁");
  assert.deepEqual(repetir.clases, ["boton", "boton-secundario"]);
  assert.ok(
    !html.includes(TEXTOS.inicio.repetir.vacio),
    "ofrece repetir y además dice que no hay nada que repetir",
  );
});

test("sin nada apuntado, se dice que no hay nada en vez de ofrecer repetir", async () => {
  const html = await htmlDeInicio({ hayUltimo: false });
  assert.ok(
    !botonesDe(html).some((boton) => boton.accion === "repetir"),
    "ofrece repetir sin haber nada que repetir",
  );
  assert.ok(
    html.includes(`<p class="pista-campo">${TEXTOS.inicio.repetir.vacio}</p>`),
    "no dice que no hay nada apuntado todavía",
  );
});

test("con apuntes pero sin nada que repetir, se dice eso y no que no haya nada", async () => {
  // El caso de verdad: una finca con abonos o trabajos apuntados y ningún tratamiento. Antes se
  // le decía «todavía no has apuntado nada», que es mentira, y encima mirando solo lo que
  // recordaba el móvil. La frase la elige `app.js` según los números del cuaderno.
  const html = await htmlDeInicio({
    hayUltimo: false,
    sinUltimo: TEXTOS.inicio.repetir.sin_poder_repetir,
  });
  assert.ok(
    html.includes(`<p class="pista-campo">${TEXTOS.inicio.repetir.sin_poder_repetir}</p>`),
    `no se dice por qué no se puede repetir: ${html.slice(0, 300)}`,
  );
  assert.ok(
    !html.includes(TEXTOS.inicio.repetir.vacio),
    "con apuntes en el cuaderno se sigue diciendo que no hay nada apuntado",
  );
});

test("el botón de la voz y el de mis cosas están, con su texto y su acción", async () => {
  const botones = botonesDe(await htmlDeInicio());
  const dictado = botones.find((boton) => boton.accion === "dictado");
  const misCosas = botones.find((boton) => boton.accion === "mis-cosas");

  assert.ok(dictado, "no está el botón de la voz: el agricultor no puede dictar");
  assert.equal(dictado.etiqueta, "Dímelo con la voz");
  assert.equal(dictado.pista, "cuéntamelo con tus palabras");
  assert.equal(dictado.icono, "🎤");
  assert.deepEqual(dictado.clases, ["boton", "boton-secundario"]);

  assert.ok(misCosas, "no está el botón de mis cosas");
  assert.equal(misCosas.etiqueta, "MIS PARCELAS, PRODUCTOS Y MÁQUINAS");
  assert.equal(misCosas.icono, "📋");
  assert.deepEqual(misCosas.clases, ["boton", "boton-claro"]);
});

// ---------------------------------------------------------------------------
// El agricultor que todavía no tiene ninguna parcela
// ---------------------------------------------------------------------------

test("sin parcelas, avisa y ofrece el botón que lo arregla", async () => {
  const html = await htmlDeInicio({ hayParcelas: false });
  assert.ok(html.includes("Antes de empezar"), "no avisa de que falta algo");
  assert.ok(html.includes(TEXTOS.maestros.falta_parcela), "no dice qué hace falta");

  const arreglo = botonesDe(html).find((boton) => boton.accion === "anadir-maestro");
  assert.ok(arreglo, "avisa pero no deja arreglarlo: es el bloqueo que tenía la aplicación");
  assert.equal(arreglo.etiqueta, "AÑADIR MI PRIMERA PARCELA");
  assert.equal(arreglo.tipo, "parcela");
  assert.equal(arreglo.icono, "📍");
  assert.deepEqual(arreglo.clases, ["boton", "boton-principal"]);
  assert.ok(
    html.indexOf("Antes de empezar") < html.indexOf("¿Qué has hecho hoy?"),
    "el aviso tiene que salir antes que la pregunta: es lo primero que hay que leer",
  );
  assert.ok(html.includes('<div class="aviso">'), "el aviso no lleva la clase de aviso de la casa");
});

test("con parcelas, el aviso de antes de empezar no aparece", async () => {
  const html = await htmlDeInicio({ hayParcelas: true });
  assert.ok(!html.includes("Antes de empezar"), "avisa de que falta una parcela teniéndolas");
  assert.ok(!html.includes("AÑADIR MI PRIMERA PARCELA"), "ofrece añadir la primera parcela teniéndolas");
  assert.ok(!botonesDe(html).some((boton) => boton.accion === "anadir-maestro"));
});

// ---------------------------------------------------------------------------
// Los textos: del servidor, y ni uno escrito a mano
// ---------------------------------------------------------------------------

test("los textos salen del servidor: si cambian allí, cambian en pantalla", async () => {
  const textos = textosDePrueba();
  textos.inicio.saludo = "Buenos días";
  textos.inicio.pregunta = "¿Qué toca hoy?";
  textos.inicio.botones[0].texto = "HE TRATADO";
  textos.maestros.antes_de_empezar = "Falta un dato";
  const html = await htmlDeInicio({ textos, hayParcelas: false });

  assert.ok(html.includes("Buenos días"), "el saludo no viene del servidor");
  assert.ok(html.includes("¿Qué toca hoy?"), "la pregunta no viene del servidor");
  assert.ok(html.includes("HE TRATADO"), "el texto del botón no viene del servidor");
  assert.ok(html.includes("Falta un dato"), "el aviso no viene del servidor");
  assert.ok(!html.includes("HE ECHADO PRODUCTO"), "el texto viejo sigue puesto: estaba escrito aquí");
});

test("en el HTML no hay ni una frase que no venga del servidor", async () => {
  // Sin nombre y sin campaña, para que el saludo sea exactamente el del servidor y se pueda
  // comparar frase a frase. Cualquier texto que no esté en la copia de los textos es una
  // frase escrita a mano dentro del componente, y eso está prohibido en este proyecto: si el
  // agricultor la puede leer, tiene que pasar por `textos.py` y por el test de la jerga.
  const html = await htmlDeInicio({ nombre: "", campana: null });
  const delServidor = new Set(todosLosTextos(TEXTOS));
  const escritasAMano = frasesVisibles(html).filter((frase) => !delServidor.has(frase));
  assert.deepEqual(escritasAMano, [], `hay frases escritas a mano en el componente: ${escritasAMano}`);
});

test("el texto del agricultor no se escapa dos veces", async () => {
  // En React no se usa `esc()`: React escapa solo. Si se llamara, el agricultor leería
  // «&amp;» en pantalla, que es exactamente el fallo que esto evita.
  const textos = textosDePrueba();
  textos.inicio.pregunta = "¿Has echado algo a las 8 & 9?";
  const html = await htmlDeInicio({ textos });
  assert.ok(html.includes("¿Has echado algo a las 8 &amp; 9?"), "el & no se escapa como toca");
  assert.ok(!html.includes("&amp;amp;"), "el texto se ha escapado dos veces");
});

test("sin los textos cargados, no se escribe la palabra «undefined»", async () => {
  // Pasa cuando la aplicación arranca sin cobertura y no hay copia guardada de los textos:
  // la pantalla se queda casi vacía, pero no con basura dentro.
  const html = await htmlDeInicio({ textos: {} });
  assert.ok(!html.includes("undefined"), `sale «undefined» en pantalla: ${html}`);
  assert.ok(!html.includes("null"), `sale «null» en pantalla: ${html}`);
  assert.ok(html.includes("<h1></h1>"), "la cabecera no sale vacía, sale con basura");
});

// ---------------------------------------------------------------------------
// El montaje: quien habla con ReactDOM
// ---------------------------------------------------------------------------

test("sin ReactDOM, la pantalla se apunta y no revienta", async () => {
  // Es el caso de estas pruebas y el del arranque sin navegador. Si esto reventara, `app.js`
  // no podría ni arrancar en las pruebas, y la primera noticia de un fallo sería un agricultor
  // delante de una pantalla en blanco.
  assert.equal(globalThis.ReactDOM, undefined, "esta prueba necesita que no haya ReactDOM");
  const { pantallaDeInicio } = await cargarInicio();
  const contenedor = { innerHTML: "lo de antes" };

  montajes.length = 0;
  const montado = montarEn(contenedor, pantallaDeInicio(propiedades()), {});
  assert.equal(montado, false, "dice que ha montado sin tener ReactDOM");
  assert.equal(montajes.length, 1, "no se ha apuntado lo que se pedía montar");
  assert.equal(montajes[0].contenedor, contenedor);
  assert.equal(montajes[0].motor, "apuntado");
});

test("la pantalla de inicio se le pide a React, y con los datos de la aplicación", async () => {
  const { PantallaInicio, pantallaDeInicio } = await cargarInicio();
  const elemento = pantallaDeInicio(
    propiedades({ nombre: "Juan", campana: { anio: 2026 }, hayParcelas: false, hayUltimo: true }),
  );

  // Es un elemento de React de verdad, no una cadena de HTML: eso es lo que distingue esta
  // pantalla de las que todavía se pintan a mano.
  assert.equal(typeof elemento, "object");
  assert.equal(elemento.type, PantallaInicio, "lo que se le pide a React no es la pantalla de inicio");
  assert.equal(elemento.props.nombre, "Juan");
  assert.deepEqual(elemento.props.campana, { anio: 2026 });
  assert.equal(elemento.props.hayParcelas, false);
  assert.equal(elemento.props.hayUltimo, true);
  assert.deepEqual(Object.keys(elemento.props.textos).sort(), ["dictado", "inicio", "maestros"]);
});

test("con ReactDOM, monta de verdad en el contenedor que se le dice", async () => {
  // ReactDOM de mentira: lo único que se comprueba aquí es **el contrato** —que se llame a
  // `createRoot` con el contenedor y a `render` con el elemento—, porque montar de verdad
  // necesita un navegador y eso se prueba en el móvil, no aquí.
  const llamadas = [];
  const anterior = globalThis.ReactDOM;
  globalThis.ReactDOM = {
    createRoot: (contenedor) => ({
      render: (elemento) => llamadas.push({ contenedor, elemento }),
    }),
  };
  try {
    const { PantallaInicio, pantallaDeInicio } = await cargarInicio();
    const contenedor = { innerHTML: "la pantalla anterior" };
    const elemento = pantallaDeInicio(propiedades());

    montajes.length = 0;
    assert.equal(montarEn(contenedor, elemento, {}), true, "no dice que haya montado");
    assert.equal(llamadas.length, 1, "no se ha llamado a render");
    assert.equal(llamadas[0].contenedor, contenedor, "no ha montado en el contenedor que se le dice");
    assert.equal(llamadas[0].elemento.type, PantallaInicio);
    assert.equal(montajes[0].motor, "react");
    // Se vacía el contenedor antes de montar: las pantallas que no están en React siguen
    // pintándose ahí con `innerHTML`, y si no se vaciara, React montaría al lado de lo que
    // hubiera puesto la pantalla anterior.
    assert.equal(contenedor.innerHTML, "");
  } finally {
    if (anterior === undefined) delete globalThis.ReactDOM;
    else globalThis.ReactDOM = anterior;
  }
});

// ---------------------------------------------------------------------------
// La salida de emergencia: nunca una pantalla en blanco
// ---------------------------------------------------------------------------

/**
 * Un DOM de mentira, pero con lo justo para que `montar.js` lo tome por un DOM de verdad:
 * un elemento de verdad tiene `nodeType` y sabe insertar hijos (el DOM de las otras pruebas,
 * que solo tiene las cuatro cosas que necesita la interfaz vieja, no los tiene).
 */
function nodoDeMentira() {
  const nodo = {
    nodeType: 1,
    nodeName: "DIV",
    className: "",
    textContent: "",
    innerHTML: "",
    hijos: [],
    atributos: {},
    manejadores: {},
    insertBefore: () => {},
    appendChild: (hijo) => nodo.hijos.push(hijo),
    setAttribute: (nombre, valor) => {
      nodo.atributos[nombre] = valor;
    },
    addEventListener: (tipo, manejador) => {
      nodo.manejadores[tipo] = manejador;
    },
  };
  return nodo;
}

/** Monta un navegador de mentira (y lo quita al terminar) mientras dura una prueba. */
function conNavegadorDeMentira(prueba) {
  const antes = { document: globalThis.document, location: globalThis.location };
  const contenedor = nodoDeMentira();
  let recargas = 0;
  globalThis.document = { createElement: () => nodoDeMentira() };
  globalThis.location = {
    reload: () => {
      recargas += 1;
    },
  };
  try {
    prueba({ contenedor, recargas: () => recargas });
  } finally {
    for (const [nombre, valor] of Object.entries(antes)) {
      if (valor === undefined) delete globalThis[nombre];
      else globalThis[nombre] = valor;
    }
  }
}

test("si React no ha llegado, el agricultor ve un aviso y un botón, no una pantalla en blanco", () => {
  conNavegadorDeMentira(({ contenedor }) => {
    montajes.length = 0;
    // `elemento = null` es lo que pasa de verdad cuando los ficheros de `vendor` no han
    // cargado: `pantallaDeInicio` no puede ni construir el elemento.
    assert.equal(montarEn(contenedor, null, TEXTOS_DE_REACT), false);

    assert.equal(montajes.length, 1, "no se ha apuntado el intento de montaje");
    assert.equal(montajes[0].elemento, null);

    // El aviso, con la clase de la casa y el texto del servidor.
    assert.equal(contenedor.hijos.length, 2, "no ha escrito el aviso y el botón");
    const [aviso, boton] = contenedor.hijos;
    assert.equal(aviso.className, "aviso");
    assert.equal(
      aviso.hijos[0].textContent,
      TEXTOS_DE_REACT.sin_react,
      "el aviso no dice lo que tiene que decir",
    );
    assert.equal(boton.className, "boton boton-principal");
    assert.equal(boton.textContent, TEXTOS_DE_REACT.recargar);
    assert.equal(boton.atributos["data-accion"], "recargar");
    assert.equal(typeof boton.manejadores.click, "function", "el botón no hace nada al tocarlo");
  });
});

test("el botón de la pantalla de emergencia vuelve a abrir la aplicación", () => {
  conNavegadorDeMentira(({ contenedor, recargas }) => {
    montarEn(contenedor, null, TEXTOS_DE_REACT);
    assert.equal(recargas(), 0, "ha recargado sin que nadie toque el botón");
    contenedor.hijos[1].manejadores.click();
    assert.equal(recargas(), 1, "el botón no recarga la aplicación");
  });
});

test("sin navegador de verdad no se escribe nada, pero tampoco se revienta", () => {
  // Es el caso de estas mismas pruebas: hay un `document` de mentira al que le faltan las
  // tripas de un DOM. Escribir ahí dentro no serviría de nada y podría romper el arranque.
  const contenedor = { innerHTML: "", hijos: [] };
  assert.equal(montarEn(contenedor, null, TEXTOS_DE_REACT), false);
  assert.equal(contenedor.innerHTML, "", "ha escrito en un DOM que no es un DOM");
});

// ---------------------------------------------------------------------------
// La barra de acciones de una ficha (ronda 93): CORREGIR y BORRAR
//
// Es el trozo que llevan **todas** las listas de la aplicación desde que todo se puede arreglar: los
// apuntes del cuaderno, las tierras, los grupos, las fichas de lo que se usa, los análisis, las ventas y
// los planes. Estaba escrito a mano en cuatro pantallas y se estaba copiando a las demás; con la pieza,
// la siguiente lista son dos líneas.
// ---------------------------------------------------------------------------

async function htmlDeAcciones(cambios = {}) {
  const { AccionesDeUnaFicha } = await import(
    `../web/react/piezas/acciones_de_una_ficha.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(AccionesDeUnaFicha, {
      acciones: [
        {
          etiqueta: "CORREGIR",
          accion: "cosa-corregir",
          datos: { tipo: "producto", id: 3 },
          clase: "boton-claro",
        },
        {
          etiqueta: "BORRAR",
          accion: "cosa-borrar",
          datos: { tipo: "producto", id: 3 },
          clase: "boton-peligro",
        },
      ],
      ...cambios,
    }),
  );
}

test("la barra de una ficha sale con sus dos botones, y con lo que hace cada uno", async () => {
  const html = await htmlDeAcciones();
  assert.match(html, /<div class="barra-acciones">/);
  // Cada botón lleva su acción **y de qué ficha es**: el manejador de clics es uno solo y lee de ahí.
  assert.match(
    html,
    /<button[^>]*data-accion="cosa-corregir"[^>]*data-tipo="producto"[^>]*data-id="3"/,
    "el botón de corregir no dice qué ficha es",
  );
  assert.match(
    html,
    /<button[^>]*data-accion="cosa-borrar"[^>]*data-tipo="producto"[^>]*data-id="3"/,
    "el botón de borrar no dice qué ficha es",
  );
  // **Corregir va primero, y solo borrar va marcado como peligro**: el que quita algo no puede ser el
  // que más a mano esté.
  assert.ok(html.indexOf("cosa-corregir") < html.indexOf("cosa-borrar"));
  const borrar = html.match(/<button[^>]*data-accion="cosa-borrar"[^>]*>/)[0];
  assert.match(borrar, /boton-peligro/);
  assert.doesNotMatch(html.match(/<button[^>]*data-accion="cosa-corregir"[^>]*>/)[0], /boton-peligro/);
});

test("una ficha sin acciones no deja la barra puesta y vacía", async () => {
  // Una barra vacía es un hueco con un borde, y promete botones que no están. Es la misma regla que la
  // tarjeta que no lleva el círculo de elegir cuando no se elige nada.
  assert.equal(await htmlDeAcciones({ acciones: [] }), "", "una ficha sin botones deja la barra");
  // Y la pista, sin botones, sí se pinta: es una frase, no una barra.
  const soloPista = await htmlDeAcciones({ acciones: [], pista: "Míralo antes de borrar." });
  assert.match(soloPista, /<p class="pista-campo">Míralo antes de borrar\.<\/p>/);
  assert.doesNotMatch(soloPista, /barra-acciones/);
});

test("la barra no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeAcciones();
  for (const fraseVisible of frasesVisibles(html)) {
    assert.ok(
      ["CORREGIR", "BORRAR"].includes(fraseVisible),
      `frase escrita a mano en la barra: «${fraseVisible}»`,
    );
  }
});

// ---------------------------------------------------------------------------
// La pantalla de confirmación («Apuntado…»), la segunda migrada a React
// ---------------------------------------------------------------------------

/**
 * Los textos de la confirmación, tal y como los sirve `/api/interfaz`.
 *
 * Son los mismos que usa la pantalla vieja: `aviso.apuntado_ok` (de `textos.INTERFAZ`),
 * `mensajes.sin_cobertura` y `mensajes.V8_dias_de_espera` (de `textos.MENSAJES`) y las palabras de
 * los dos botones (de `textos.ACCIONES`).
 */
const TEXTOS_DE_HECHO = {
  aviso: {
    apuntado_ok: "Apuntado. Si te has equivocado, pulsa DESHACER.",
    deshacer_pista: "Por si te has confundido de tierra, producto o dosis.",
  },
  mensajes: {
    sin_cobertura:
      "No hay cobertura. No te preocupes: lo hemos guardado en el móvil y se manda solo cuando llegues a casa.",
    V8_dias_de_espera:
      "Fíjate: con lo que has echado hoy, en esta parcela no podrás coger la cosecha hasta el {fin}.",
  },
  acciones: { deshacer: "DESHACER", volver: "VOLVER" },
  // Los textos de corregir (ronda 91). La misma pantalla sale después de **corregir** un apunte, y
  // entonces dice «Corregido» y ofrece volver a corregirlo en vez de deshacerlo.
  corregir: {
    boton: "CORREGIR",
    pista: "Está puesto lo que apuntaste. Cambia lo que esté mal y guárdalo.",
    boton_mejor_corregirlo: "MEJOR CORREGIRLO",
    hecho_titulo: "Corregido",
    hecho: "Ya está cambiado.",
  },
};

/** Carga la pantalla de confirmación con marca en la URL, como las demás. */
async function cargarHecho() {
  return import(`../web/react/pantallas/hecho.js?prueba=${Math.random()}`);
}

/** El HTML de la confirmación, tal y como lo dibujaría React. */
async function htmlDeHecho(resultado = {}, cambios = {}) {
  const { PantallaHecho } = await cargarHecho();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaHecho, {
      textos: structuredClone(TEXTOS_DE_HECHO),
      resultado,
      tipo: "tratamiento",
      ...cambios,
    }),
  );
}

/** El texto que se lee dentro del botón de una acción, quitando las etiquetas. */
function textoDeBoton(html, accion) {
  const encontrado = html.match(
    new RegExp(`<button\\b[^>]*data-accion="${accion}"[^>]*>([\\s\\S]*?)</button>`),
  );
  if (!encontrado) return "";
  // Se quitan las etiquetas y también la flecha (que es un `<span>` con una flecha dentro): el
  // texto del botón es su etiqueta, no la señal de que se pulsa.
  return encontrado[1]
    .replace(/<span class="flecha"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<[^>]*>/g, "")
    .trim();
}

test("la confirmación dice que se ha apuntado y ofrece deshacer", async () => {
  const html = await htmlDeHecho({ id: 42, datos: {} });
  assert.match(html, /Apuntado\. Si te has equivocado, pulsa DESHACER\./);

  const botones = botonesDe(html);
  const deshacer = botones.find((boton) => boton.accion === "deshacer");
  assert.ok(deshacer, "no hay botón de deshacer");
  assert.deepEqual(deshacer.clases, ["boton", "boton-peligro"]);
  assert.equal(deshacer.tipo, "tratamiento", "sin el tipo, el manejador no sabe qué deshacer");
  assert.match(html, /data-id="42"/);
  // Desde la ronda 90 el texto va en su hueco de texto, **con su explicación debajo** (diseño de Stitch
  // de esta pantalla): es el único botón que puede borrar un apunte y el que menos se sabía para qué
  // estaba. Es la misma forma que usa `Boton` cuando le dan una pista.
  const pista = TEXTOS_DE_HECHO.aviso.deshacer_pista;
  assert.match(
    html,
    new RegExp(`<span class="texto"><span>DESHACER<\\/span><span class="pista-boton">${pista.replace(/[.]/g, "\\$&")}`),
    "el botón de deshacer no lleva su explicación",
  );

  const volver = botones.find((boton) => boton.accion === "ir-inicio");
  assert.ok(volver, "no hay forma de volver al inicio: el agricultor se queda encerrado");
  // **Y desde la ronda 90 es el botón grande** y va primero: es lo que se hace el 99 % de las veces, y
  // así el botón de deshacer —el peligroso— deja de ser el primero que encuentra el dedo.
  assert.deepEqual(volver.clases, ["boton", "boton-principal"]);
  assert.equal(textoDeBoton(html, "ir-inicio"), "VOLVER");
  assert.ok(
    html.indexOf('data-accion="ir-inicio"') < html.indexOf('data-accion="deshacer"'),
    "el botón de deshacer sigue estando antes que el de volver",
  );
});

test("un apunte guardado sin id no ofrece deshacer (no hay nada que deshacer)", async () => {
  const html = await htmlDeHecho({ datos: {} });
  assert.equal(
    botonesDe(html).filter((boton) => boton.accion === "deshacer").length,
    0,
    "ofrece deshacer un apunte que no tiene identificador",
  );
  assert.ok(botonesDe(html).some((boton) => boton.accion === "ir-inicio"));
});

test("la pantalla de un apunte apuntado ofrece corregirlo, antes que deshacerlo", async () => {
  // **Ronda 91.** La mitad de las equivocaciones se ven aquí —el agricultor acaba de leer el resumen—, y
  // hasta esta ronda la única salida era DESHACER, que anula el apunte entero y lo deja tachado. Corregir
  // es lo que de verdad quiere: cambiar ese dato sin dejar hueco en el cuaderno.
  const html = await htmlDeHecho({ id: 42, datos: {} });
  const corregir = botonesDe(html).find((boton) => boton.accion === "hecho-corregir");
  assert.ok(corregir, "no se puede corregir lo que se acaba de apuntar");
  assert.equal(textoDeBoton(html, "hecho-corregir").includes("CORREGIR"), true);
  assert.equal(corregir.tipo, "tratamiento", "sin el tipo, el manejador no sabe qué corregir");
  assert.match(html, /data-id="42"/);
  // Va **antes** que deshacer y no es el botón de peligro: el que quita algo del cuaderno no puede ser
  // el primero que encuentra el dedo.
  assert.ok(
    html.indexOf('data-accion="hecho-corregir"') < html.indexOf('data-accion="deshacer"'),
    "el botón de corregir sale después del de deshacer",
  );
  assert.deepEqual(corregir.clases, ["boton", "boton-claro"]);
});

test("después de corregir la pantalla dice «Corregido» y no ofrece deshacer", async () => {
  // Decirle «Apuntado» a quien acaba de cambiar un apunte le haría pensar que tiene dos. Y el botón de
  // deshacer, ahí, invitaría a **anular** el apunte que el agricultor acaba de dejar bien: para quitarlo
  // está BORRAR, en su ficha del cuaderno.
  const html = await htmlDeHecho({ id: 42, datos: {}, corregido: true });
  assert.match(html, /<h1>Corregido<\/h1>/, "no dice que se ha corregido");
  assert.match(html, /Ya está cambiado\./, "no explica qué ha pasado con lo de antes");
  assert.equal(
    botonesDe(html).filter((boton) => boton.accion === "deshacer").length,
    0,
    "después de corregir se ofrece deshacer, que anularía el apunte recién arreglado",
  );
  assert.ok(botonesDe(html).some((boton) => boton.accion === "hecho-corregir"), "no se puede volver a corregir");
  assert.ok(botonesDe(html).some((boton) => boton.accion === "ir-inicio"));
});

test("los avisos del apunte salen en pantalla, y los que bloquean no", async () => {
  const html = await htmlDeHecho({
    id: 7,
    datos: {},
    avisos: [
      { codigo: "V1", mensaje: "La autorización de este producto está caducada.", bloquea: false },
      { codigo: "V2", mensaje: "Esto bloquea y no se ha guardado.", bloquea: true },
    ],
  });
  assert.match(html, /La autorización de este producto está caducada\./);
  assert.doesNotMatch(
    html,
    /Esto bloquea/,
    "enseña un aviso que bloquea: si bloquea, el apunte no se ha guardado y esta pantalla no sale",
  );
});

test("si el apunte se ha quedado en el móvil sin cobertura, se dice", async () => {
  const conCola = await htmlDeHecho({ id: 1, datos: {}, encolado: true });
  assert.match(conCola, /No hay cobertura\. No te preocupes/);
  const sinCola = await htmlDeHecho({ id: 1, datos: {} });
  assert.doesNotMatch(sinCola, /No hay cobertura/, "avisa de falta de cobertura cuando la hay");
});

test("la confirmación enseña lo que se acaba de apuntar", async () => {
  // De la lámina de piezas de Stitch (ronda 90): la pantalla decía «Apuntado» y nada más, así que el
  // agricultor no podía comprobar que se había entendido lo que él quería apuntar. La ficha es la misma que
  // la de las cuentas del almacén y la de los datos de una venta.
  const html = await htmlDeHecho(
    { id: 9, datos: { fecha: "2026-07-12" } },
    {
      queEs: "Tratamiento con producto",
      filas: [
        { etiqueta: "Tierra y parcela", valor: "El Prado" },
        { etiqueta: "¿Cuándo?", valor: "12/07/2026" },
      ],
    },
  );
  assert.match(html, /<h2>Tratamiento con producto<\/h2>/);
  assert.match(html, /<dt>Tierra y parcela<\/dt><dd>El Prado<\/dd>/);
  assert.match(html, /<dt>¿Cuándo\?<\/dt><dd>12\/07\/2026<\/dd>/);
  // Y sin filas (un apunte que quedó en la cola, sin datos del servidor) no se dibuja la ficha.
  assert.doesNotMatch(await htmlDeHecho({ datos: {} }), /class="resumen-dato"/);
});

test("los días de espera salen con la fecha en el formato de aquí", async () => {
  const html = await htmlDeHecho({
    id: 3,
    datos: { fecha_fin_plazo_seguridad: "2026-10-07" },
  });
  assert.match(html, /no podrás coger la cosecha hasta el 07\/10\/2026/);
  // **Y desde la ronda 90 en su franja de aviso** (diseño de Stitch de esta pantalla): es el dato que
  // puede costarle la cosecha, y estaba en un párrafo suelto del mismo aspecto que el resto.
  assert.match(html, /<p class="tarjeta-aviso tarjeta-aviso-grande"><span class="tarjeta-aviso-icono"/);
});

test("sin plazo de seguridad no se habla de días de espera", async () => {
  const html = await htmlDeHecho({ id: 3, datos: {} });
  assert.doesNotMatch(html, /días de espera|coger la cosecha/);
});

test("la confirmación no lleva ni una frase escrita a mano", async () => {
  const avisoDelServidor = "Un aviso del servidor.";
  const html = await htmlDeHecho({
    id: 5,
    datos: { fecha_fin_plazo_seguridad: "2026-10-07" },
    encolado: true,
    avisos: [{ codigo: "V1", mensaje: avisoDelServidor, bloquea: false }],
  });
  // Los textos que sí vienen del servidor: los bloques de textos y **el mensaje del aviso**, que
  // forma parte de la respuesta del apunte (no lo escribe el componente). Y las frases que salen de
  // rellenar un hueco: la plantilla es del servidor y lo único que se mete es la fecha.
  const delServidor = new Set([...todosLosTextos(TEXTOS_DE_HECHO), avisoDelServidor]);
  for (const texto of [...delServidor]) {
    delServidor.add(texto.replace(/\{[a-z_]+\}/g, "07/10/2026"));
  }
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Mis cosas»: las listas de lo que el agricultor tiene dado de alta
// ---------------------------------------------------------------------------

/**
 * Los textos y las secciones de «mis cosas», como los prepara `app.js` para el componente.
 *
 * Las secciones llegan **ya preparadas** (título, explicación, aviso de vacío, palabra del botón y
 * sus elementos) porque quien tiene los datos es `app.js`. Aquí se copian tal y como salen de allí
 * con los datos de las pruebas, que son los mismos que sirve `/api/interfaz`.
 */
const TEXTOS_DE_MIS_COSAS = {
  maestros: {
    titulo: "Mis parcelas, productos y máquinas",
    intro: "Aquí está todo lo que has dado de alta. Desde aquí puedes añadir más.",
  },
  acciones: { volver: "VOLVER" },
};

const SECCIONES = [
  {
    // La sección de las tierras va **como tarjetas** desde el rediseño (ronda 78), y por eso sus
    // elementos no son renglones: son ya lo que espera `Tarjeta`. Es la única sección así.
    tipo: "parcela",
    titulo: "Parcelas",
    pista: "Las tierras que llevas",
    vacio: "Todavía no has apuntado ninguna parcela.",
    anadir: "AÑADIR UNA PARCELA",
    cuantas: "Tienes 1 tierra apuntada",
    tarjetas: true,
    etiquetaDelDibujo: "La forma de tu parcela",
    // **Y la tabla, para el ordenador** (30/09/2026): la misma tierra, mirada de otra forma. Las dos van en
    // el HTML y el CSS enseña la que toca según el ancho.
    tabla: {
      clave: "tierras",
      etiqueta: "Tus tierras, en una tabla",
      columnas: [
        { texto: "Nº", campo: "numero", clase: "tabla-numero", ordenada: true, descendente: false, orden: "Ordenar por: Nº" },
        { texto: "Nombre", campo: "alias", ordenada: false, descendente: false, orden: "Ordenar por: Nombre" },
        { texto: "Hectáreas", campo: "superficie_ha", clase: "tabla-numero", ordenada: false, descendente: false, orden: "Ordenar por: Hectáreas" },
        { texto: "Qué tiene este año", campo: "cultivo", ordenada: false, descendente: false, orden: "Ordenar por: Qué tiene este año" },
        { texto: "Acciones" },
      ],
      filas: [
        {
          celdas: [
            { texto: "1", clase: "tabla-numero" },
            { texto: "El Prado" },
            { texto: "4,90", clase: "tabla-numero" },
            { estado: { texto: "Todavía no has dicho qué hay aquí este año.", tipo: "mirar" } },
            { texto: "" },
          ],
          acciones: [
            {
              etiqueta: "DECIR QUÉ HAY SEMBRADO",
              accion: "cultivo-decir",
              datos: { id: 7 },
              clase: "boton-claro",
            },
            {
              etiqueta: "CORREGIR",
              accion: "cosa-corregir",
              datos: { tipo: "parcela", id: 7 },
              clase: "boton-claro",
            },
          ],
        },
      ],
      resumen: "1 tierra · 4,90 ha",
    },
    elementos: [
      {
        etiqueta: "El Prado",
        rotulo: "Tierra n.º 1",
        lineas: ["4,90 hectáreas", "Medina del Campo"],
        filas: [{ etiqueta: "Referencia oficial SIGPAC", valor: "37-70-0-0-503-51" }],
        dibujo: "M 4 34.582 L 31.8 4.409 L 96 65.171 Z",
        avisos: ["Está en zona de nitratos"],
        pendiente: "Le falta decir qué tiene sembrado este año",
        accionTexto: "DECIR QUÉ HAY SEMBRADO",
        marca: false,
        elegida: false,
        accion: "cultivo-decir",
        datos: { id: 7 },
        textos: { elegida: "ELEGIDA" },
        // Y sus dos botones (ronda 92): corregir la tierra y borrarla. La segunda tierra va sin ellos
        // a propósito, para poder comprobar que una tarjeta sin acciones no deja la barra vacía.
        acciones: [
          {
            etiqueta: "CORREGIR",
            accion: "cosa-corregir",
            datos: { tipo: "parcela", id: 7 },
            clase: "boton-claro",
          },
          {
            etiqueta: "BORRAR",
            accion: "cosa-borrar",
            datos: { tipo: "parcela", id: 7 },
            clase: "boton-peligro",
          },
        ],
      },
    ],
  },
  {
    tipo: "producto",
    titulo: "Productos que he comprado",
    pista: "Lo que tienes para echar",
    vacio: "Todavía no has apuntado ningún producto.",
    anadir: "AÑADIR UN PRODUCTO",
    elementos: [{ nombre: "Glifosato 36 SL", detalle: "24.123 · 7 días", dibujo: "" }],
  },
  {
    tipo: "abono",
    titulo: "Abonos",
    pista: "Lo que echas a la tierra",
    vacio: "Todavía no has apuntado ningún abono.",
    anadir: "AÑADIR UN ABONO",
    elementos: [],
  },
  {
    tipo: "aplicador",
    titulo: "Quién aplica el producto",
    pista: "Las personas que echan producto",
    vacio: "Todavía no has apuntado a nadie.",
    anadir: "AÑADIR A QUIEN APLICA",
    elementos: [],
  },
  {
    tipo: "asesor",
    titulo: "Quién me asesora",
    pista: "El técnico que te aconseja",
    vacio: "Todavía no has apuntado a ningún asesor.",
    anadir: "AÑADIR UN ASESOR",
    elementos: [
      { nombre: "Ana García Ruiz", detalle: "ROPO ROPO-778 · Plagas (gestión integrada)", dibujo: "" },
    ],
  },
  {
    tipo: "equipo",
    titulo: "Máquinas de echar producto",
    pista: "Con lo que echas el producto",
    vacio: "Todavía no has apuntado ninguna máquina.",
    anadir: "AÑADIR UNA MÁQUINA",
    elementos: [],
  },
  {
    tipo: "instalacion",
    titulo: "Naves, almacenes e invernaderos",
    pista: "Donde guardas lo que compras",
    vacio: "Todavía no has apuntado ninguna nave.",
    anadir: "AÑADIR UNA NAVE",
    elementos: [{ nombre: "El almacén grande", detalle: "Almacén · Guardar el grano", dibujo: "" }],
  },
];

const ATAJOS = [
  { titulo: "Los papeles", explica: "Contratos, facturas y resguardos.", icono: "📄", accion: "papel-ver-todos" },
  { titulo: "Lo que tengo en el almacén", explica: "Lo comprado y lo que queda.", icono: "🧴", accion: "cesta-ver" },
  { titulo: "Lo que hay sembrado", explica: "El cultivo de cada parcela.", icono: "🌱", accion: "cultivo-ver-todos" },
  { titulo: "Grupos de parcelas", explica: "Parcelas que se llevan igual.", icono: "🔗", accion: "grupo-ver" },
];

/** Carga «mis cosas» con marca en la URL, como las demás pantallas. */
async function cargarMisCosas() {
  return import(`../web/react/pantallas/mis_cosas.js?prueba=${Math.random()}`);
}

/** El HTML de «mis cosas», tal y como lo dibujaría React. */
async function htmlDeMisCosas(cambios = {}) {
  const { PantallaMisCosas } = await cargarMisCosas();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaMisCosas, {
      textos: structuredClone(TEXTOS_DE_MIS_COSAS),
      secciones: structuredClone(SECCIONES),
      atajos: structuredClone(ATAJOS),
      ...cambios,
    }),
  );
}

test("mis cosas enseña las siete secciones con su botón de añadir", async () => {
  const html = await htmlDeMisCosas();
  for (const titulo of [
    "Parcelas",
    "Productos que he comprado",
    "Abonos",
    "Quién aplica el producto",
    "Quién me asesora",
    "Máquinas de echar producto",
    "Naves, almacenes e invernaderos",
  ]) {
    assert.match(html, new RegExp(`<h2>${titulo}</h2>`), `falta la sección ${titulo}`);
  }
  // Y el botón de añadir de cada una, con su `data-tipo`: es lo que lee el manejador para saber
  // qué alta abrir.
  for (const tipo of [
    "parcela",
    "producto",
    "abono",
    "aplicador",
    "asesor",
    "equipo",
    "instalacion",
  ]) {
    assert.match(html, new RegExp(`data-accion="anadir-maestro" data-tipo="${tipo}"`), `falta el botón de ${tipo}`);
  }
});

test("mis cosas enseña lo que ya hay dado de alta, con su detalle", async () => {
  const html = await htmlDeMisCosas();
  // Las tierras, como tarjeta: su número, su nombre, su superficie con su palabra, su pueblo y la
  // referencia del SIGPAC **con su nombre delante** (un «37-70-0-0-503-51» suelto no dice qué es).
  assert.match(html, /<span class="tarjeta-rotulo">Tierra n\.º 1<\/span>/);
  assert.match(html, /<span class="tarjeta-nombre">El Prado<\/span>/);
  assert.match(html, /<span class="tarjeta-linea">4,90 hectáreas<\/span>/);
  assert.match(html, /<span class="tarjeta-linea-suave">Medina del Campo<\/span>/);
  assert.match(html, /<span class="tarjeta-fila-etiqueta">Referencia oficial SIGPAC<\/span>/);
  assert.match(html, /<span class="tarjeta-fila-valor">37-70-0-0-503-51<\/span>/);
  // Y las otras secciones siguen con su renglón de siempre.
  assert.match(html, /Glifosato 36 SL/);
  assert.match(html, /El almacén grande/);
});

test("cuántas tierras hay se dice debajo del título de la sección", async () => {
  // La lista de tierras se corta al final de la pantalla: sin decirlo, el agricultor no sabe si las está
  // viendo todas o si el programa se ha dejado alguna por el camino.
  const html = await htmlDeMisCosas();
  assert.match(html, /<p class="cuantas">Tienes 1 tierra apuntada<\/p>/);
});

test("lo que le falta a una tierra va en su tarjeta, con el camino para arreglarlo", async () => {
  // Es lo que evita mandar al agricultor a otra pantalla a buscar la tierra por su nombre. Y la tarjeta
  // **no elige: abre** lo que hay sembrado en esa tierra, así que no lleva el círculo de elegir.
  const html = await htmlDeMisCosas();
  assert.match(html, /<span class="tarjeta-aviso">[\s\S]*Le falta decir qué tiene sembrado este año/);
  assert.match(html, /<span class="tarjeta-accion">DECIR QUÉ HAY SEMBRADO<span class="flecha"/);
  assert.match(html, /data-accion="cultivo-decir"/);
  assert.match(html, /data-id="7"/);
  assert.doesNotMatch(html, /tarjeta-marca/, "una lista que no se elige no puede llevar el círculo de elegir");
});

test("el buscador de tierras va encima de las tarjetas, y sin resultados se dice", async () => {
  // **Esto se añadió en la ronda 87.** El diseño pide el buscador en esta pantalla: con 51 tierras, mirar
  // una concreta era recorrerlas todas. Va **encima** de la lista, y cuando no encuentra nada lo dice en
  // vez de enseñar el aviso de «todavía no tienes parcelas» (que sería mentira: las tiene).
  const conBuscador = await htmlDeMisCosas({
    secciones: [
      {
        ...structuredClone(SECCIONES[0]),
        buscar: React.createElement("input", { id: "buscar_tierra_mis_cosas", defaultValue: "" }),
        cuantas: "Tienes 3 tierras apuntadas",
      },
      ...structuredClone(SECCIONES.slice(1)),
    ],
  });
  assert.match(conBuscador, /id="buscar_tierra_mis_cosas"/, "no lleva el buscador encima de las tarjetas");
  assert.ok(
    conBuscador.indexOf('id="buscar_tierra_mis_cosas"') <
      conBuscador.indexOf('<div class="tarjetas solo-movil">'),
    "el buscador sale después de las tarjetas",
  );
  // **Y por delante de la tabla también** (30/09/2026): el buscador filtra las dos formas de ver la lista,
  // así que tiene que estar por encima de las dos. El orden en el HTML es: buscador → tabla (ordenador) →
  // tarjetas (móvil), y el CSS enseña una u otra.
  assert.ok(
    conBuscador.indexOf('id="buscar_tierra_mis_cosas"') <
      conBuscador.indexOf('<div class="solo-escritorio">'),
    "el buscador sale después de la tabla",
  );

  const sinNada = await htmlDeMisCosas({
    secciones: [
      {
        ...structuredClone(SECCIONES[0]),
        elementos: [],
        cuantas: "Tienes 3 tierras apuntadas",
        sinResultados: {
          texto: "Con esas letras no encuentro ninguna tierra.",
          pista: "Prueba con menos letras, o míralo en la lista entera.",
          boton: {
            etiqueta: "VERLAS TODAS",
            accion: "buscar-tierra-limpiar-mis-cosas",
            clase: "boton-principal",
          },
        },
      },
      ...structuredClone(SECCIONES.slice(1)),
    ],
  });
  assert.match(sinNada, /Con esas letras no encuentro ninguna tierra\./, "no dice que no encuentra nada");
  assert.match(sinNada, /data-accion="buscar-tierra-limpiar-mis-cosas"/, "el aviso no lleva su salida");
  assert.doesNotMatch(
    sinNada.slice(0, sinNada.indexOf("<h2>Productos")),
    /Todavía no has apuntado ninguna parcela/,
    "dice que no tiene parcelas cuando lo que pasa es que la búsqueda no casa",
  );
});

test("una sección vacía dice que no hay nada, en vez de quedarse en blanco", async () => {
  const html = await htmlDeMisCosas();
  assert.match(html, /Todavía no has apuntado ningún abono\./);
  assert.match(html, /Todavía no has apuntado a nadie\./);
  // Y una sección con cosas **no** lleva ese aviso: sería decir dos cosas a la vez.
  const trozoDeParcelas = html.slice(html.indexOf("<h2>Parcelas</h2>"), html.indexOf("<h2>Productos"));
  assert.doesNotMatch(trozoDeParcelas, /Todavía no has apuntado ninguna parcela/);
});

test("el asesor sale con su número y con de qué asesora", async () => {
  // El número (ROPO) es lo que bloquea: sin él la Junta rechaza el tratamiento entero.
  const html = await htmlDeMisCosas();
  assert.match(html, /Ana García Ruiz/);
  assert.match(html, /ROPO ROPO-778/);
  assert.match(html, /Plagas \(gestión integrada\)/);
});

test("los cuatro atajos de abajo están, con su acción", async () => {
  const acciones = botonesDe(await htmlDeMisCosas())
    .map((boton) => boton.accion)
    // Las de añadir, la de volver, **las de las tarjetas de tierra** (que abren lo que hay sembrado en
    // esa tierra) y, desde la ronda 92, **las de cada tierra** (CORREGIR y BORRAR): los cuatro atajos son
    // los otros. Se filtran por su nombre y no por su sitio porque el orden de la pantalla es lo que
    // cambia cada vez que se añade algo a una sección, y una prueba que cuenta botones por posición se
    // rompe con cada mejora sin que nada esté mal.
    .filter(
      (accion) =>
        ![
          "anadir-maestro",
          "ir-inicio",
          "cultivo-decir",
          "cosa-corregir",
          "cosa-borrar",
          // Las cabeceras de la tabla de tierras también son botones (ordenan): no son atajos de abajo,
          // así que se quitan de esta cuenta como los botones de las tarjetas.
          "ordenar-tabla",
        ].includes(accion),
    );
  assert.deepEqual(acciones, ["papel-ver-todos", "cesta-ver", "cultivo-ver-todos", "grupo-ver"]);
});

// ---------------------------------------------------------------------------
// EL PANEL DE MANDO DEL ORDENADOR (fase 4, 30/09/2026)
//
// Es la pantalla que se abre al entrar desde un pc, y antes era la del móvil estirada: ocho botones de ancho
// completo, uno detrás de otro, en un monitor. Lo que hace un programa de gestión al abrirse es enseñar **el
// estado**: cuatro números, lo que falta por completar con su botón y lo último apuntado. El diseño del que
// sale está en `docs/stitch/escritorio/panel.png`.
// ---------------------------------------------------------------------------

/** Los textos del panel de mando, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DEL_MANDO = {
  panel_de_mando: {
    titulo: "Panel de mando",
    explica: "Cómo va el cuaderno de este año, de un vistazo: lo que llevas apuntado, lo que falta por completar y lo último que has hecho.",
    apuntes: "Apuntes este año",
    hectareas: "Hectáreas tratadas",
    hectareas_detalle: "de {hectareas} ha de tus tierras",
    vendido: "Lo que has vendido",
    tierras: "Tus tierras",
    tierras_sin_decir_uno: "1 sin decir qué tiene este año",
    tierras_sin_decir: "{cuantas} sin decir qué tienen este año",
    tierras_al_dia: "Todas con su cultivo dicho",
    falta_titulo: "Lo que falta por completar",
    falta_uno: "1 cosa por completar",
    falta: "{cuantas} cosas por completar",
    falta_vacio: "No te falta nada: el cuaderno está al día.",
    ultimos_titulo: "Los últimos apuntes",
    ultimos_vacio: "Todavía no has apuntado nada este año.",
    ver_todos_uno: "Ver el apunte del año",
    ver_todos: "Ver los {cuantas} apuntes del año",
    apuntar_titulo: "Apuntar algo de hoy",
    cierre_titulo: "Cierre y trámites",
    cierre_explica: "Lo que se saca del programa: el cuaderno en papel para imprimir, los datos en un fichero y la firma del año.",
  },
};

/** Lo que `app.js` le prepara al panel de mando, con datos de verdad. */
function mandoDePrueba(cambios = {}) {
  return {
    numeros: [
      { etiqueta: "Apuntes este año", valor: "12", detalle: "12 apuntes en el cuaderno" },
      { etiqueta: "Hectáreas tratadas", valor: "62,40 ha", detalle: "de 187,42 ha de tus tierras" },
      { etiqueta: "Lo que has vendido", valor: "42.000 kg", detalle: "2 ventas apuntadas" },
      { etiqueta: "Tus tierras", valor: "64", detalle: "10 sin decir qué tienen este año" },
    ],
    faltantes: {
      titulo: "Lo que falta por completar",
      cuantas: "1 cosa por completar",
      pendientes: [
        {
          mensaje: "A Las Suertes de Arriba le falta decir qué cultivo tiene este año.",
          accion: "cultivo-ver-todos",
          etiqueta: "Qué hay sembrado",
        },
      ],
      vacio: "No te falta nada: el cuaderno está al día.",
    },
    ultimos: {
      titulo: "Los últimos apuntes",
      columnas: ["Fecha", "Qué", "Tierra", "Hectáreas"],
      filas: [["02/05/2026", "Producto · Cobre 50 WP", "El Prado", "1,20 ha"]],
      vacio: "Todavía no has apuntado nada este año.",
      ver_todos: { etiqueta: "Ver los 24 apuntes del año", accion: "inicio", datos: { ir: "mi_cuaderno" } },
    },
    apuntar: [
      {
        etiqueta: "HE ECHADO PRODUCTO",
        pista: "bichos, hierbas, hongos",
        icono: "💧",
        accion: "inicio",
        datos: { ir: "echar_producto" },
        clase: "boton-principal",
      },
    ],
    cierre: {
      titulo: "Cierre y trámites",
      explica: "Lo que se saca del programa.",
      botones: [
        { etiqueta: "SACAR EN PAPEL", accion: "inicio", datos: { ir: "papel" }, clase: "boton-claro" },
        { etiqueta: "GUARDAR LOS DATOS EN UN FICHERO", accion: "sacar-datos", clase: "boton-claro" },
        { etiqueta: "FIRMAR EL CUADERNO", accion: "firmar-abrir", clase: "boton-claro" },
      ],
    },
    ...cambios,
  };
}

async function htmlDelMando(cambios = {}) {
  const { PanelDeMando } = await import(
    `../web/react/piezas/panel_de_mando.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PanelDeMando, {
      textos: structuredClone(TEXTOS_DEL_MANDO),
      ...mandoDePrueba(cambios),
    }),
  );
}

test("el panel de mando enseña los cuatro números del año", async () => {
  const html = await htmlDelMando();
  assert.match(html, /<h2>Panel de mando<\/h2>/);
  // Las cuatro tarjetas, con su etiqueta, su número en grande y su detalle.
  for (const [etiqueta, valor] of [
    ["Apuntes este año", "12"],
    ["Hectáreas tratadas", "62,40 ha"],
    ["Lo que has vendido", "42.000 kg"],
    ["Tus tierras", "64"],
  ]) {
    assert.match(
      html,
      new RegExp(`<p class="mando-numero-etiqueta">${etiqueta}</p><p class="mando-numero-valor">${valor}</p>`),
      `no sale la tarjeta de «${etiqueta}»`,
    );
  }
  // Y el detalle de cada una, que es el contexto sin el cual un número no dice nada.
  assert.match(html, /de 187,42 ha de tus tierras/);
  assert.match(html, /10 sin decir qué tienen este año/);
  // **La tarjeta del gasto en fitosanitarios NO está**, aunque el diseño de Stitch la trae: ese número no
  // existe en el programa y ponerlo sería inventarse un dato.
  assert.doesNotMatch(html, /Gasto/i);
});

test("lo que falta lleva su botón, y sin nada pendiente se dice que está al día", async () => {
  const html = await htmlDelMando();
  assert.match(html, /<h3>Lo que falta por completar<\/h3>/);
  assert.match(html, /<span class="etiqueta-estado etiqueta-estado-mirar">1 cosa por completar<\/span>/);
  assert.match(html, /A Las Suertes de Arriba le falta decir qué cultivo tiene este año\./);
  // Y **el botón que lo arregla**, con su acción (que es la misma del cuaderno del móvil).
  assert.match(html, /data-accion="cultivo-ver-todos"[^>]*>[\s\S]*?Qué hay sembrado/);

  // Sin pendientes, se dice que está al día en vez de dejar el bloque con un hueco.
  const alDia = await htmlDelMando({
    faltantes: { ...mandoDePrueba().faltantes, pendientes: [], cuantas: "" },
  });
  assert.match(alDia, /No te falta nada: el cuaderno está al día\./);
  assert.doesNotMatch(alDia, /etiqueta-estado-mirar/, "sin pendientes no puede salir la etiqueta de cuántas");
});

test("los últimos apuntes salen en su tabla, con el enlace a la lista entera", async () => {
  const html = await htmlDelMando();
  const cabeceras = [...html.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((uno) =>
    uno[1].replace(/<[^>]+>/g, "").trim(),
  );
  assert.deepEqual(cabeceras, ["Fecha", "Qué", "Tierra", "Hectáreas"]);
  assert.match(html, /<td>02\/05\/2026<\/td>/);
  assert.match(html, /Producto · Cobre 50 WP/);
  // El enlace a los apuntes del año: con un apunte, en singular.
  assert.match(html, /Ver los 24 apuntes del año/);
  // Y sin apuntes, se dice, en vez de una tabla vacía.
  const sinApuntes = await htmlDelMando({
    ultimos: { ...mandoDePrueba().ultimos, filas: [], ver_todos: null },
  });
  assert.match(sinApuntes, /Todavía no has apuntado nada este año\./);
  assert.doesNotMatch(sinApuntes, /<table/);
});

test("el panel de mando lleva a apuntar y al cierre del año", async () => {
  const html = await htmlDelMando();
  // Apuntar algo de hoy, con los mismos botones del móvil (texto, icono y pista del servidor).
  assert.match(html, /<h3>Apuntar algo de hoy<\/h3>/);
  assert.match(html, /data-accion="inicio"[^>]*data-ir="echar_producto"/);
  assert.match(html, /HE ECHADO PRODUCTO/);
  // Y el cierre: el cuaderno en papel, los datos en un fichero y la firma.
  assert.match(html, /<h3>Cierre y trámites<\/h3>/);
  const delCierre = html.split('class="mando-bloque mando-cierre"')[1];
  const acciones = [...delCierre.matchAll(/data-accion="([^"]+)"/g)].map((uno) => uno[1]);
  assert.deepEqual(acciones, ["inicio", "sacar-datos", "firmar-abrir"]);
});

// ---------------------------------------------------------------------------
// LA TABLA DEL ORDENADOR (30/09/2026)
//
// David lo pidió así: *«no es una app usable de gestión… hacer una versión para pc que parezca una
// aplicación de gestión»*. Lo que hace que un programa de gestión lo sea es **ver muchos datos a la vez en
// una tabla**: ordenarlos, compararlos y tocar una fila. La tabla es **una pieza** (`react/piezas/tabla.js`)
// porque la van a usar todas las listas; la primera es la de las 64 tierras.
// ---------------------------------------------------------------------------

async function htmlDeLaTabla(cambios = {}) {
  const { Tabla } = await import(`../web/react/piezas/tabla.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(Tabla, { tabla: structuredClone(SECCIONES[0].tabla), ...cambios }),
  );
}

test("la tabla lleva sus columnas, sus filas y el total del pie", async () => {
  const html = await htmlDeLaTabla();
  // El nombre de la tabla, para quien no ve la pantalla.
  assert.match(html, /aria-label="Tus tierras, en una tabla"/);
  // Las columnas, en su orden, con su nombre del servidor.
  const cabeceras = [...html.matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((uno) =>
    uno[1].replace(/<[^>]+>/g, "").trim(),
  );
  assert.deepEqual(cabeceras, [
    "Nº",
    "Nombre",
    "Hectáreas",
    "Qué tiene este año",
    "Acciones",
  ]);
  // Los datos de la tierra, cada uno en su celda.
  assert.match(html, /<span class="tabla-dato">El Prado<\/span>/);
  assert.match(html, /<td class="tabla-numero"><span class="tabla-dato">4,90<\/span><\/td>/);
  // El total, que es la cuenta que se viene a hacer en una tabla de tierras.
  assert.match(html, /<tfoot>[\s\S]*1 tierra · 4,90 ha/);
  // Y una tabla sin filas no se pinta: un cuadro vacío con cabeceras promete datos que no hay.
  assert.equal(await htmlDeLaTabla({ tabla: { ...SECCIONES[0].tabla, filas: [] } }), "");
});

test("la columna por la que se ordena es un botón, y dice hacia dónde va", async () => {
  // Ordenar es lo que se hace con 64 tierras («¿cuál es la más grande?»). El botón lleva el `data-campo` y
  // el `data-tabla` para que `app.js` sepa qué ordenar, y la flecha la pone el CSS: así el mismo componente
  // sirve para cualquier tabla sin escribir una frase dentro.
  const html = await htmlDeLaTabla();
  assert.match(
    html,
    /data-accion="ordenar-tabla" data-tabla="tierras" data-campo="numero"/,
    "la cabecera no lleva lo que hace falta para ordenar",
  );
  // La que ordena va marcada con su clase y con `aria-sort` (el color solo no informa, y quien no ve la
  // pantalla tiene que saber por dónde va el orden).
  assert.match(html, /<th scope="col" class="tabla-numero tabla-ordenada" aria-sort="ascending">/);
  assert.match(html, /title="Ordenar por: Nº"/);
  // Y las que no ordenan son texto, no botones: la de acciones no se ordena (no es un dato).
  assert.doesNotMatch(html, /data-campo="acciones"|data-campo=""/);
  // Dándole la vuelta, la marca cambia de sentido.
  const alReves = await htmlDeLaTabla({
    tabla: {
      ...structuredClone(SECCIONES[0].tabla),
      columnas: structuredClone(SECCIONES[0].tabla.columnas).map((columna) =>
        columna.campo === "numero" ? { ...columna, descendente: true } : columna,
      ),
    },
  });
  assert.match(alReves, /class="tabla-numero tabla-ordenada tabla-ordenada-abajo" aria-sort="descending"/);
});

test("una tierra a la que le falta decirlo lo dice con palabras, y con su botón", async () => {
  const html = await htmlDeLaTabla();
  // La celda de «qué tiene este año» dice lo que pasa con su etiqueta, no con un hueco ni un color suelto.
  assert.match(
    html,
    /<span class="etiqueta-estado etiqueta-estado-mirar">Todavía no has dicho qué hay aquí este año\.<\/span>/,
  );
  // Y en la columna de las acciones están las tres: la de la fila (decirlo) y las dos de siempre.
  const acciones = botonesDe(html)
    .map((boton) => boton.accion)
    .filter((accion) => accion !== "ordenar-tabla");
  assert.deepEqual(acciones, ["cultivo-decir", "cosa-corregir"]);
  assert.match(html, /data-accion="cultivo-decir" data-id="7"/);
});

test("la tabla y las tarjetas conviven, y el CSS enseña una u otra", async () => {
  // **Las dos formas van en el mismo HTML**: los mismos datos, los mismos botones y el mismo manejador de
  // clics. Lo que cambia es cuál se ve, y eso lo decide el ancho de la pantalla (el `@media` de
  // `estilos.css`). Si en vez de esto se eligiera con JavaScript, habría dos aplicaciones que se podrían
  // separar.
  const html = await htmlDeMisCosas();
  assert.match(html, /<div class="solo-escritorio"><table class="tabla"/);
  assert.match(html, /<div class="tarjetas solo-movil">/);
  // La tabla va antes que las tarjetas en el HTML: primero lo de la pantalla grande, y el mismo dato
  // después para el móvil. (El orden no cambia lo que se ve: solo se ve una.)
  assert.ok(html.indexOf('class="solo-escritorio"') < html.indexOf('class="tarjetas solo-movil"'));
});

test("el panel de al lado enseña la fila elegida, o dice que no hay ninguna", async () => {
  // **Fase 3, 30/09/2026.** La tabla y su ficha, juntas: se toca un nombre y se ve al lado. Lo que se
  // comprueba aquí es lo que se ve: la ficha con sus datos y sus botones cuando hay algo elegido, el aviso
  // de qué hacer cuando no, y que el nombre de la fila sea un botón (no la fila entera: en una tabla, eso es
  // lo que menos se espera).
  const conElegida = await htmlDeLaTabla({
    tabla: {
      ...structuredClone(SECCIONES[0].tabla),
      panel: {
        etiqueta: "La ficha de lo que has elegido",
        titulo: "La tierra que has elegido",
        detalle: "Tierra n.º 1",
        vacio: "Toca el nombre de una tierra de la lista y la verás aquí, con sus datos.",
        elegida: true,
        filas: [
          { etiqueta: "Referencia oficial SIGPAC", valor: "37-70-0-0-503-51" },
          { etiqueta: "Hectáreas", valor: "4,90 ha" },
        ],
        avisos: ["Le falta decir qué tiene sembrado este año"],
        acciones: [
          { etiqueta: "DECIR QUÉ HAY SEMBRADO", accion: "cultivo-decir", datos: { id: 7 }, clase: "boton-principal", sencillo: true },
          { etiqueta: "CORREGIR", accion: "cosa-corregir", datos: { tipo: "parcela", id: 7 }, clase: "boton-claro", sencillo: true },
        ],
      },
    },
  });
  assert.match(conElegida, /<div class="tabla-y-panel">/);
  assert.match(conElegida, /<aside class="panel-detalle" aria-label="La ficha de lo que has elegido">/);
  assert.match(conElegida, /<h2>La tierra que has elegido<\/h2>/);
  assert.match(conElegida, /<p class="pista-campo">Tierra n.º 1<\/p>/);
  // Los datos, con su nombre delante (la misma forma que las fichas de toda la aplicación).
  assert.match(conElegida, /<dt>Hectáreas<\/dt><dd>4,90 ha<\/dd>/);
  // Y lo que le falta, en su franja de aviso.
  assert.match(conElegida, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono" aria-hidden="true">!<\/span>Le falta decir/);
  // Con sus botones: el de la ficha y los dos de siempre. Se miran **los del panel** (a partir del
  // `<aside>`), porque los botones de la fila de la tabla son los mismos y contarlos juntos no diría nada.
  const delPanel = conElegida.split("<aside")[1];
  const acciones = botonesDe(delPanel).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["cultivo-decir", "cosa-corregir"]);

  // Sin nada elegido, el panel lo dice y no enseña una ficha en blanco.
  const sinElegida = await htmlDeLaTabla({
    tabla: {
      ...structuredClone(SECCIONES[0].tabla),
      panel: {
        etiqueta: "La ficha de lo que has elegido",
        titulo: "La tierra que has elegido",
        vacio: "Toca el nombre de una tierra de la lista y la verás aquí, con sus datos.",
        elegida: false,
      },
    },
  });
  assert.match(sinElegida, /Toca el nombre de una tierra de la lista/);
  assert.doesNotMatch(sinElegida, /resumen-dato/, "sin nada elegido no puede haber datos de nadie");
});

test("el nombre de una fila es un botón, y la fila entera no", async () => {
  // Se toca el nombre (como en cualquier programa de gestión) y así funciona con el teclado: un `<tr>` no
  // se puede enfocar, un botón sí. Y la fila elegida se marca para que se vea cuál es.
  const html = await htmlDeLaTabla({
    tabla: {
      ...structuredClone(SECCIONES[0].tabla),
      filas: [
        {
          ...structuredClone(SECCIONES[0].tabla.filas[0]),
          elegida: true,
          celdas: [{ texto: "1", clase: "tabla-numero" }, { texto: "El Prado", accion: "elegir-fila", datos: { tabla: "tierras", id: 7 } }],
        },
      ],
    },
  });
  assert.match(html, /<tr class="tabla-fila-elegida">/);
  assert.match(
    html,
    /<button type="button" class="tabla-enlace" data-accion="elegir-fila" data-tabla="tierras" data-id="7">El Prado<\/button>/,
  );
  // La fila **no** lleva acción: solo su nombre.
  assert.doesNotMatch(html, /<tr[^>]*data-accion/);
});

test("cada tierra de «mis cosas» sale con sus dos botones, debajo de su tarjeta", async () => {
  // **Ronda 92.** La tarjeta abre lo que hay sembrado en esa tierra (que es lo que se mira el 99 % de
  // las veces) y **debajo** van sus dos botones: corregirla (el nombre, las hectáreas, la referencia del
  // SIGPAC…) o borrarla. Van fuera de la tarjeta a propósito: la tarjeta ya hace una cosa, y meterle dos
  // botones dentro la convertiría en una caja que se toca y no hace nada.
  const html = await htmlDeMisCosas();
  const trozo = html.split('<div class="tarjeta-con-acciones">')[1];
  assert.ok(trozo, "la tierra no va en su caja con los botones debajo");
  const [antes, despues] = trozo.split('<div class="barra-acciones">');
  assert.match(antes, /<button[^>]*data-accion="cultivo-decir"/, "la tarjeta ha dejado de abrir el cultivo");
  assert.match(despues, /data-accion="cosa-corregir"[^>]*data-tipo="parcela"[^>]*data-id="7"/);
  assert.match(despues, /data-accion="cosa-borrar"[^>]*data-tipo="parcela"[^>]*data-id="7"/);
  assert.match(despues, />CORREGIR</);
  assert.match(despues, />BORRAR</);
  assert.match(despues, /boton-peligro/, "el botón de borrar no va marcado como peligro");
});

test("la tierra se dibuja con la forma que trae el SIGPAC, y se explica para quien no la ve", async () => {
  // **Esto cierra el último dato que entraba y no salía**: el SIGPAC devuelve la forma de cada
  // recinto desde la ronda 10 y durante diez rondas se guardó y no se veía en ninguna parte. Desde el
  // rediseño, el dibujo va dentro de la tarjeta de la tierra (es como el agricultor la reconoce: la ve
  // así en el visor del SIGPAC y en el papel).
  const html = await htmlDeMisCosas();
  assert.match(html, /class="dibujo-parcela"/, "no dibuja la tierra");
  assert.match(html, /M 4 34\.582 L 31\.8 4\.409 L 96 65\.171 Z/, "no pinta la forma que le llega");
  assert.match(html, /aria-label="El Prado"/, "el dibujo no se explica para quien no lo ve");
  // Y se dibuja **de verdad**, con sus etiquetas: no es un texto de HTML metido dentro de otro.
  assert.match(html, /<svg[^>]*>\s*<path d="M 4 34\.582/);
});

test("una tierra sin forma no se dibuja, y no se inventa un cuadro", async () => {
  // Una tierra apuntada a mano no tiene geometría. Un cuadro inventado parecería su tierra, y eso
  // es peor que no dibujar nada.
  const sinForma = structuredClone(SECCIONES);
  sinForma[0].elementos[0].dibujo = "";
  const html = await htmlDeMisCosas({ secciones: sinForma });
  assert.match(html, /<span class="tarjeta-nombre">El Prado<\/span>/, "no lista la tierra");
  assert.doesNotMatch(html, /dibujo-parcela/, "ha dibujado algo que no existe");
});

test("mis cosas no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeMisCosas();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_MIS_COSAS),
    ...todosLosTextos(SECCIONES),
    ...todosLosTextos(ATAJOS),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Los papeles»: las listas agrupadas por carpeta
// ---------------------------------------------------------------------------

const TEXTOS_DE_DOCUMENTOS = {
  documentos: {
    titulo: "Los papeles",
    explica:
      "Aquí guardas los papeles que acompañan al cuaderno: el contrato de la tierra, las facturas de lo que compras, los resguardos de los envases. El cuaderno dice lo que hiciste; estos papeles son los que lo demuestran.",
    sin_papeles:
      "Todavía no has guardado ningún papel. No hace falta que lo tengas todo: empieza por el contrato de la tierra, que es el que más se pide.",
    sin_carpeta: "Sin carpeta",
    para_que:
      "Si un día viene una inspección, esto es lo que te van a pedir junto con el cuaderno. Y si se te pierde el papel de verdad, aquí queda al menos apuntado.",
    tiene_fichero: "Con el papel subido",
    no_tiene_fichero: "Solo apuntado, sin el papel",
    descargar: "VER EL PAPEL",
    subir_fichero: "SUBIR EL PAPEL",
    sin_fichero:
      "Este papel está apuntado pero no has subido el fichero. Apúntalo igual: así no se te olvida que existe.",
    nuevo: "GUARDAR UN PAPEL",
    listado: "LISTA DE PAPELES, PARA COPIAR",
  },
  maestros: { titulo: "MIS PARCELAS, PRODUCTOS Y MÁQUINAS" },
  acciones: { volver: "VOLVER" },
};

const CARPETAS_DE_PRUEBA = [
  {
    nombre: "Facturas",
    papeles: [
      {
        id: 7,
        titulo: "Factura del abono",
        detalle: "Factura · 15/03/2026 · Cooperativa · Con el papel subido",
        tiene_fichero: true,
      },
      {
        id: 8,
        titulo: "Resguardo de Sigfito",
        detalle: "Resguardo de envases · Solo apuntado, sin el papel",
        tiene_fichero: false,
      },
    ],
  },
];

async function cargarDocumentos() {
  return import(`../web/react/pantallas/documentos.js?prueba=${Math.random()}`);
}

async function htmlDeDocumentos(cambios = {}) {
  const { PantallaDocumentos } = await cargarDocumentos();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDocumentos, {
      textos: structuredClone(TEXTOS_DE_DOCUMENTOS),
      carpetas: structuredClone(CARPETAS_DE_PRUEBA),
      sinCarpeta: [],
      total: 2,
      error: "",
      ...cambios,
    }),
  );
}

test("los papeles salen agrupados por carpeta, con su título y su detalle", async () => {
  const html = await htmlDeDocumentos();
  assert.match(html, /<h2>Facturas<\/h2>/);
  assert.match(html, /<strong>Factura del abono<\/strong>/);
  assert.match(html, /Factura · 15\/03\/2026 · Cooperativa · Con el papel subido/);
  assert.match(html, /<strong>Resguardo de Sigfito<\/strong>/);
});

test("un papel con fichero se descarga, y uno sin fichero se puede subir", async () => {
  // No son la misma cosa y no pueden llevar el mismo botón: uno se descarga y al otro hay que
  // subirle el fichero. Y al que no lo tiene se le dice, en vez de dejar un botón que no haría nada.
  const html = await htmlDeDocumentos();
  assert.match(html, /data-accion="papel-ver" data-id="7"/);
  assert.match(html, /data-accion="papel-subir" data-id="8"/);
  assert.doesNotMatch(html, /data-accion="papel-ver" data-id="8"/);
  assert.match(html, /Este papel está apuntado pero no has subido el fichero\./);
  assert.match(html, /SUBIR EL PAPEL/);
  assert.match(html, /VER EL PAPEL/);
});

test("el campo para subir el fichero lleva el mismo id que busca app.js", async () => {
  // **Esto no es un detalle de estilo.** Quien sube el fichero lo busca con
  // `document.getElementById("papel-" + id)`: si el id no sale igual, el botón de subir no encuentra
  // nada y no pasa nada al pulsarlo.
  const html = await htmlDeDocumentos();
  assert.match(html, /<input type="file" id="papel-8" class="oculto"\/>/);
});

test("si no hay ningún papel, se dice en vez de dejar la pantalla vacía", async () => {
  const vacia = await htmlDeDocumentos({ carpetas: [], total: 0 });
  assert.match(vacia, /Todavía no has guardado ningún papel\./);
  // Y si hay papeles, **no** se dice que no hay: sería contradecirse.
  assert.doesNotMatch(await htmlDeDocumentos(), /Todavía no has guardado ningún papel/);
});

test("un papel de una carpeta que no está en la lista no se esconde", async () => {
  // El agricultor puede escribir una carpeta a mano. Si su papel no cayera en ninguna carpeta
  // conocida y no se enseñara, parecería que se ha perdido.
  const suelto = [
    { id: 9, titulo: "Contrato del vecino", detalle: "Contrato · sin fichero", tiene_fichero: false },
  ];
  const html = await htmlDeDocumentos({ sinCarpeta: suelto });
  assert.match(html, /<h2>Sin carpeta<\/h2>/);
  assert.match(html, /Contrato del vecino/);
});

test("el error del servidor se enseña como un aviso, no como un texto suelto", async () => {
  const html = await htmlDeDocumentos({ error: "No se ha podido guardar el papel." });
  assert.match(html, /class="aviso aviso-error" role="alert"/);
  assert.match(html, /No se ha podido guardar el papel\./);
  // Y sin error no se dibuja ningún aviso de error: un hueco rojo vacío asusta sin motivo.
  assert.doesNotMatch(await htmlDeDocumentos(), /aviso-error/);
});

test("los cuatro botones de abajo están, con su acción", async () => {
  const acciones = botonesDe(await htmlDeDocumentos())
    .map((boton) => boton.accion)
    .filter((accion) => accion.startsWith("papel-ver-todos") || ["papel-nuevo", "papel-listado", "mis-cosas", "ir-inicio"].includes(accion));
  // **`papel-nuevo` sale dos veces y es a propósito** (ronda 90, diseño de Stitch de esta pantalla):
  // arriba, para no tener que bajar dos pantallas con diez papeles guardados, y abajo, al final de la
  // lista, como estaba. Es la misma acción, así que las dos las atiende el manejador de `document`.
  assert.deepEqual(acciones, ["papel-nuevo", "papel-nuevo", "papel-listado", "mis-cosas", "ir-inicio"]);
});

test("el papel al que le falta el fichero lo dice en su franja y su botón es el grande", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): subirle el fichero es lo único que le falta a ese
  // papel, así que es lo que tiene que destacar. Uno con fichero se descarga con un botón claro.
  const html = await htmlDeDocumentos();
  // El papel que ya tiene el fichero (id 7) se descarga con el botón claro.
  assert.match(html, /class="boton boton-claro" data-accion="papel-ver" data-id="7"/);
  // Y al que le falta (id 8) se le dice en su franja de aviso y el botón de subirlo es el grande.
  assert.match(html, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  assert.match(html, /class="boton boton-principal" data-accion="papel-subir" data-id="8"/);
  // El campo del fichero, que es como `app.js` lee el papel elegido, sigue con su `id`.
  assert.match(html, /<input type="file" id="papel-8" class="oculto"\/>/);

  // Y si todos los papeles tienen su fichero, no se avisa de nada que no falte.
  const todosConFichero = await htmlDeDocumentos({
    carpetas: [
      {
        nombre: "Facturas",
        papeles: [{ id: 7, titulo: "Factura del abono", detalle: "Con el papel subido", tiene_fichero: true }],
      },
    ],
  });
  assert.doesNotMatch(todosConFichero, /class="tarjeta-aviso"/, "avisa de algo que no falta");
});

// ---------------------------------------------------------------------------
// El almacén: el libro de movimientos de cada producto
// ---------------------------------------------------------------------------

/** Los textos del almacén, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_LA_CESTA = {
  cesta: {
    titulo: "Lo que tengo en el almacén",
    explica: "Aquí ves cuánto producto compraste, cuánto llevas echado y cuánto te queda. Sirve para dos cosas: saber si te llega para tratar la parcela, y tener el libro de entradas y salidas que se mira en una inspección.",
    vacia: "Todavía no has apuntado ningún producto. Cuando apuntes uno, aquí verás lo que te queda.",
    comprado: "Compraste",
    gastado: "Llevas echado",
    queda: "Te queda",
    apuntes: "En {cuantos} apuntes",
    cuando: "Cuándo",
    donde_lo_compraste: "Dónde lo compraste",
    // Las tres etiquetas de estado (ronda 90, del diseño de Stitch de esta pantalla).
    cuadra: "Las cuentas cuadran",
    mirar: "Míralo",
    sin_cantidad: "Sin saber cuánto compraste",
    no_se_puede_comparar: "No se puede comparar",
    para_que_sirve: "Si un día te preguntan cuánto producto has comprado y cuánto has echado, esto es la respuesta. Y si te queda poco, lo ves antes de quedarte sin él en mitad del tratamiento.",
    como_apuntarlo: "Cuánto compraste se apunta en la ficha del producto. Sin ese dato, aquí no salen las cuentas: no se inventan.",
    ir_a_productos: "MIS PRODUCTOS",
  },
  facturas: { titulo: "Mis facturas" },
  acciones: { volver: "VOLVER" },
};

/**
 * Un producto de los que prepara `app.js`: con sus filas ya contadas **y con la fila de «Te queda»
 * destacada y su etiqueta de estado**, que es como las manda `app.js` desde la ronda 90.
 */
function productoDePrueba(cambios = {}) {
  return {
    nombre_comercial: "Ejemplo 25 EC",
    materia_activa: "Tebuconazol",
    motivo: "",
    estado: { texto: "Las cuentas cuadran", tipo: "bien" },
    filas: [
      { etiqueta: "Compraste", valor: "10 L" },
      { etiqueta: "Llevas echado", valor: "2 L · En 1 apuntes" },
      { etiqueta: "Cuándo", valor: "15/03/2026" },
      { etiqueta: "Dónde lo compraste", valor: "Cooperativa de Peñaranda" },
      { etiqueta: "Te queda", valor: "8 L", destacada: true },
    ],
    ...cambios,
  };
}

async function cargarCesta() {
  return import(`../web/react/pantallas/cesta.js?prueba=${Math.random()}`);
}

async function htmlDeLaCesta(cambios = {}) {
  const { PantallaCesta } = await cargarCesta();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaCesta, {
      textos: structuredClone(TEXTOS_DE_LA_CESTA),
      productos: [productoDePrueba()],
      resumen: "Tienes 1 producto apuntado.",
      error: "",
      ...cambios,
    }),
  );
}

test("el almacén dice cuántos productos tiene, con su palabra", async () => {
  // **Esto se añadió en la ronda 84.** El servidor ya contaba los productos y mandaba la frase —«Tienes 1
  // producto apuntado.», «Tienes 3 productos apuntados.»—, pero **no la enseñaba nadie**: la pantalla no la
  // leía. Es la misma línea de cuenta que llevan «mis cosas» y «mi cuaderno».
  const html = await htmlDeLaCesta();
  assert.match(html, /<p class="cuantas">Tienes 1 producto apuntado\.<\/p>/);
  // Y sin productos no se dice ningún número: la frase del almacén vacío ya lo cuenta.
  const vacia = await htmlDeLaCesta({ productos: [], resumen: "asdf" });
  assert.doesNotMatch(vacia, /class="cuantas"/, "con el almacén vacío dice un número");
});

test("el almacén enseña lo comprado, lo echado y lo que queda", async () => {
  // **Esto existe desde la ronda 15**, cuando la pantalla se hizo para contestar a «¿me queda producto
  // para tratar esta parcela?»: los campos de la compra estaban en la base de datos y no los leía
  // ninguna pantalla.
  const html = await htmlDeLaCesta();
  assert.match(html, /Ejemplo 25 EC/);
  assert.match(html, /<dt>Compraste<\/dt><dd>10 L<\/dd>/);
  assert.match(html, /<dt>Llevas echado<\/dt><dd>2 L · En 1 apuntes<\/dd>/);
  assert.match(html, /Cooperativa de Peñaranda/);
  assert.match(html, /class="resumen-dato"/, "las cuentas no van con su formato de ficha");
});

test("«Te queda» cierra la tarjeta, en su recuadro y con el número grande", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): la pregunta con la que se entra aquí es «¿me queda
  // producto?», y esa fila estaba en medio y del mismo tamaño que «Compraste». Ahora va la última, en su
  // recuadro y con el número grande, que es lo que se lee de un vistazo desde la puerta del almacén.
  const html = await htmlDeLaCesta();
  assert.match(
    html,
    /<div class="resumen-dato resumen-destacado"><dt>Te queda<\/dt><dd><span class="dato-grande">8 L<\/span><\/dd><\/div>/,
    "«Te queda» no va destacada o no dice su número",
  );
  // Y va **después** de las demás filas de la tarjeta.
  assert.ok(
    html.indexOf("resumen-destacado") > html.indexOf("<dt>Dónde lo compraste</dt>"),
    "«Te queda» no cierra la tarjeta: sale antes que las demás filas",
  );
});

test("cada producto dice en una etiqueta si hay algo que mirar", async () => {
  // Del mismo diseño: con la lista llena, lo primero que se busca es **cuál hay que mirar**, y eso no se
  // saca de tres números sueltos. Las tres etiquetas dicen qué pasa **con palabras**: el color solo no
  // informa a quien no lo distingue.
  const bien = await htmlDeLaCesta();
  assert.match(bien, /class="etiqueta-estado etiqueta-estado-bien">Las cuentas cuadran</);

  const sinCompra = await htmlDeLaCesta({
    productos: [
      productoDePrueba({
        estado: { texto: "Sin saber cuánto compraste", tipo: "falta" },
        filas: [{ etiqueta: "Llevas echado", valor: "2 L" }, { etiqueta: "Te queda", valor: "—", destacada: true }],
      }),
    ],
  });
  assert.match(sinCompra, /class="etiqueta-estado etiqueta-estado-falta">Sin saber cuánto compraste</);
  // El guion se respeta: un cero sería un dato inventado.
  assert.match(sinCompra, /<span class="dato-grande">—<\/span>/);

  const raro = await htmlDeLaCesta({
    productos: [
      productoDePrueba({ estado: { texto: "No se puede comparar", tipo: "mirar" } }),
    ],
  });
  assert.match(raro, /class="etiqueta-estado etiqueta-estado-mirar">No se puede comparar</);
});

test("cuando no se puede hacer la cuenta, el almacén lo dice en vez de inventarla", async () => {
  // Un producto comprado en kilos y echado con dosis en litros no se puede restar sin saber la
  // densidad. Poner un número ahí sería peor que no ponerlo: el agricultor compraría o dejaría de
  // comprar con ese número delante.
  //
  // **Y desde la ronda 90 la fila de «Te queda» sí sale, con un guion.** Antes no salía: el agricultor
  // veía la tarjeta sin la fila que había ido a buscar y tenía que adivinar por qué. Un guion con su
  // motivo debajo contesta igual de bien que un número, y no se inventa nada.
  const sinCuenta = productoDePrueba({
    estado: { texto: "No se puede comparar", tipo: "mirar" },
    filas: [
      { etiqueta: "Compraste", valor: "10 kg" },
      { etiqueta: "Llevas echado", valor: "2 L · En 1 apuntes" },
      { etiqueta: "Te queda", valor: "—", destacada: true },
    ],
    motivo: "Un litro y un kilo no son lo mismo y no se pueden restar.",
  });
  const html = await htmlDeLaCesta({ productos: [sinCuenta] });
  assert.match(html, /<span class="dato-grande">—<\/span>/, "no puede decir cuánto queda si no lo sabe");
  assert.match(html, /no se pueden restar/, "tiene que decir por qué no se puede");
  // El motivo va en su franja de aviso, con su señal: es «algo que hay que mirar».
  assert.match(html, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono" aria-hidden="true">!<\/span>/);
});

test("el almacén lleva a las facturas, y dice para qué sirve", async () => {
  const html = await htmlDeLaCesta();
  assert.match(html, /data-accion="facturas-abrir"/, "el almacén no lleva a las facturas");
  assert.match(html, /class="ayuda-campo"/, "no explica para qué sirve");
});

test("un almacén vacío lo dice, y no enseña una lista en blanco", async () => {
  const vacia = await htmlDeLaCesta({ productos: [] });
  assert.match(vacia, /Todavía no has apuntado ningún producto\./);
  assert.doesNotMatch(vacia, /<ul class="lista">/, "ha dibujado una lista sin nada dentro");
  // Y con productos **no** se dice que está vacío: sería contradecirse.
  const conProductos = await htmlDeLaCesta();
  assert.doesNotMatch(conProductos, /Todavía no has apuntado ningún producto\./);
});

test("un dato que no se sabe sale con un guion, nunca con un cero", async () => {
  // Un cero sería un dato inventado. El guion lo pone `app.js` al preparar las filas, y aquí se
  // comprueba que la pantalla **no lo cambia**: lo enseña tal cual.
  const raro = productoDePrueba({
    filas: [{ etiqueta: "Te queda", valor: "—" }],
  });
  const html = await htmlDeLaCesta({ productos: [raro] });
  assert.match(html, /<dd>—<\/dd>/, "no respeta el guion de «no se sabe»");
});

test("el error del servidor se enseña como un aviso", async () => {
  const html = await htmlDeLaCesta({ error: "No se ha podido cargar el almacén." });
  assert.match(html, /class="aviso aviso-error" role="alert"/);
  assert.match(html, /No se ha podido cargar el almacén\./);
  assert.doesNotMatch(await htmlDeLaCesta(), /aviso-error/);
});

test("el almacén enseña la tabla en el ordenador y las tarjetas en el móvil", async () => {
  // **30/09/2026.** Es la misma lista mirada de dos formas, y las dos van en el mismo HTML: el CSS enseña
  // una u otra según el ancho (`.solo-escritorio` y `.solo-movil`). Se hace con CSS y no con JavaScript a
  // propósito: con dos caminos en JS, el día que uno cambie el otro se queda mintiendo.
  const tabla = {
    clave: "cesta",
    etiqueta: "Lo que tienes en el almacén, en una tabla",
    columnas: [{ texto: "Producto", campo: "nombre_comercial", ordenada: true, descendente: false }],
    filas: [
      {
        celdas: [
          { texto: "Ejemplo 25 EC", accion: "elegir-fila", datos: { tabla: "cesta", id: 1 } },
        ],
        acciones: [],
      },
    ],
    resumen: "1 producto en el almacén",
    panel: null,
  };
  const html = await htmlDeLaCesta({ tabla });

  assert.match(html, /<div class="solo-escritorio">/);
  assert.match(html, /<table class="tabla" aria-label="Lo que tienes en el almacén, en una tabla">/);
  assert.match(html, /<tfoot><tr><td colSpan="1">1 producto en el almacén<\/td><\/tr><\/tfoot>/);
  // Y la tarjeta del móvil, con su clase: el CSS es el que decide cuál se ve.
  assert.match(html, /<ul class="lista solo-movil">/);
  // Sin tabla (o sin productos) no se pinta ni la caja del ordenador: un `div` vacío es un hueco con borde.
  const sinTabla = await htmlDeLaCesta();
  assert.doesNotMatch(sinTabla, /solo-escritorio/);
});

test("un producto del almacén se puede corregir y borrar desde su ficha", async () => {
  // **30/09/2026.** David lo pidió así: «deja borrar las cosas que introduzca, porque puede que me
  // equivoque». Los dos botones los prepara `app.js` (son los mismos que lleva su renglón en «mis
  // parcelas, productos y máquinas»), y aquí se comprueba que la pantalla **los pinta** y que no se
  // inventa ninguno cuando no le llegan.
  const conBotones = productoDePrueba({
    acciones: [
      { etiqueta: "CORREGIR", accion: "cosa-corregir", datos: { tipo: "producto", id: 7 }, clase: "boton-claro" },
      { etiqueta: "BORRAR", accion: "cosa-borrar", datos: { tipo: "producto", id: 7 }, clase: "boton-peligro" },
    ],
  });
  const html = await htmlDeLaCesta({ productos: [conBotones] });
  assert.match(html, /data-accion="cosa-corregir"/);
  assert.match(html, /data-accion="cosa-borrar"/);
  // Y cada botón dice **de qué producto es**: sin su tipo y su identificador, pulsarlo no haría nada o
  // haría algo sobre otra ficha.
  assert.match(html, /data-tipo="producto"/);
  assert.match(html, /data-id="7"/);
  // Y sin acciones no se pinta ningún botón de esos: la pantalla no se los inventa.
  assert.doesNotMatch(await htmlDeLaCesta(), /CORREGIR/, "pinta un botón de corregir que no le han dado");
});

// ---------------------------------------------------------------------------
// La flecha de los botones (el detalle del diseño de Stitch)
// ---------------------------------------------------------------------------

test("todos los botones llevan su flecha, y va marcada para quien no la ve", async () => {
  // La flecha sale del diseño que generó Stitch (las capturas están en `docs/stitch/`): sirve para
  // que se vea de un vistazo que **ese botón lleva a algún sitio**. Y va con `aria-hidden`, porque
  // quien use un lector de pantalla ya oye que es un botón.
  const html = await htmlDeInicio();
  const botones = botonesDe(html);
  assert.ok(botones.length >= 6, "no hay botones que mirar");
  for (const boton of botones) {
    assert.equal(boton.flecha, "→", `el botón «${boton.accion}» no lleva flecha`);
  }
  assert.equal(
    (html.match(/<span class="flecha" aria-hidden="true">/g) || []).length,
    botones.length,
    "alguna flecha no se explica para quien no la ve",
  );
});

test("la flecha no cuenta como una frase escrita a mano", async () => {
  // Es una señal, no una palabra: si contara como texto, el guardián de «ninguna frase escrita a
  // mano» daría un falso aviso en todas las pantallas. Se comprueba que no aparece en las frases
  // visibles, que es justo lo que se revisa.
  const html = await htmlDeInicio();
  assert.ok(html.includes("flecha"), "la prueba no está mirando lo que cree");
  assert.ok(
    frasesVisibles(html).every((frase) => !frase.includes("→")),
    "la flecha se está contando como una frase de la pantalla",
  );
});

// ---------------------------------------------------------------------------
// «Qué hay sembrado»: el cultivo de cada tierra y su historial
// ---------------------------------------------------------------------------

/** Los textos de «qué hay sembrado», tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_CULTIVOS = {
  cultivos: {
    titulo: "Qué hay sembrado",
    explica: "Dinos qué hay este año en cada parcela. Con eso, cuando apuntes un tratamiento o una labor ya no tienes que escribir el cultivo: el programa ya lo sabe.",
    sin_parcelas: "Todavía no tienes parcelas. Añade la primera y después me dices qué hay sembrado.",
    para_que: "Sirve para tres cosas: el cuaderno de cada año dice qué había en la tierra, puedes ver qué sembraste los años anteriores —que es lo que ayuda a decidir la rotación— y el aviso de «en esa fecha no había cultivo» funciona.",
    falta_decirlo: "Todavía no has dicho qué hay aquí este año.",
    otros_anos: "Otros años",
    repite: "Aquí has puesto lo mismo que el año pasado. Si vas a repetir, apúntalo en las medidas preventivas: la rotación de cultivos es una de las que se piden.",
    decir: "DECIR QUÉ HAY SEMBRADO",
    cambiar: "CAMBIARLO",
    tiene: "Este año hay",
    cuando: "Desde",
    hasta: "Hasta",
    // Las dos etiquetas de estado (ronda 90, del diseño de Stitch de esta pantalla).
    al_dia: "Al día",
    falta_rellenar: "Falta rellenar",
  },
  maestros: { titulo: "Mis parcelas, productos y máquinas" },
  acciones: { volver: "VOLVER" },
};

/** Una tierra de las que prepara `app.js`. */
function tierraDePrueba(cambios = {}) {
  return {
    parcela_id: 1,
    alias: "El Prado",
    detalle: "4,90 ha · Secano",
    tiene_cultivo: true,
    estado: { texto: "Al día", tipo: "bien" },
    filas: [
      { etiqueta: "Este año hay", valor: "Maíz · Híbrido" },
      { etiqueta: "Desde", valor: "01/03/2026" },
    ],
    anteriores: "2025: Trigo · 2024: Girasol",
    repite: false,
    ...cambios,
  };
}

async function cargarCultivos() {
  return import(`../web/react/pantallas/cultivos.js?prueba=${Math.random()}`);
}

async function htmlDeCultivos(cambios = {}) {
  const { PantallaCultivos } = await cargarCultivos();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaCultivos, {
      textos: structuredClone(TEXTOS_DE_CULTIVOS),
      parcelas: [tierraDePrueba()],
      resumen: "Tienes 1 tierra de 2 con el cultivo apuntado.",
      error: "",
      ...cambios,
    }),
  );
}

test("qué hay sembrado enseña el cultivo de cada tierra y su historial", async () => {
  // **Esto cerró el fallo más raro de la ronda 16:** el cuaderno le decía al agricultor «a El Prado le
  // falta decir qué cultivo tiene este año» y no había ninguna forma de contestarle.
  const html = await htmlDeCultivos();
  assert.match(html, /<strong>El Prado<\/strong>/);
  assert.match(html, /<dt>Este año hay<\/dt><dd>Maíz · Híbrido<\/dd>/);
  assert.match(html, /<dt>Desde<\/dt><dd>01\/03\/2026<\/dd>/);
  assert.match(html, /Otros años: 2025: Trigo · 2024: Girasol/);
  assert.match(html, /data-accion="cultivo-decir" data-id="1"/);
});

test("una tierra sin cultivo dice que falta decirlo, y deja decirlo", async () => {
  // Un hueco en blanco dejaría al agricultor sin saber si el programa se ha equivocado.
  //
  // **Y desde la ronda 90, con el diseño de Stitch:** lo que falta se dice en su franja de aviso y el botón
  // de decirlo es el grande (el de color de acción), porque es lo único que le falta a esa tierra. Antes
  // era una pista en letra pequeña y un botón claro igual que el de las demás.
  const sinCultivo = tierraDePrueba({
    tiene_cultivo: false,
    estado: { texto: "Falta rellenar", tipo: "falta" },
    filas: [],
  });
  const html = await htmlDeCultivos({ parcelas: [sinCultivo] });
  assert.match(html, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  assert.match(html, /Todavía no has dicho qué hay aquí este año\./);
  assert.match(html, /DECIR QUÉ HAY SEMBRADO/);
  assert.match(html, /class="boton boton-principal" data-accion="cultivo-decir"/, "el botón no es el grande");
  assert.doesNotMatch(html, /<dt>/, "ha pintado una ficha de un cultivo que no existe");
});

test("cada tierra dice en una etiqueta si le falta algo", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): con más de cincuenta tierras, lo que se viene a
  // buscar aquí es **a cuáles les falta decir qué tienen**, y eso no se saca leyendo la ficha de cada una.
  const alDia = await htmlDeCultivos();
  assert.match(alDia, /class="etiqueta-estado etiqueta-estado-bien">Al día</);
  const sinCultivo = await htmlDeCultivos({
    parcelas: [
      tierraDePrueba({
        tiene_cultivo: false,
        estado: { texto: "Falta rellenar", tipo: "falta" },
        filas: [],
      }),
    ],
  });
  assert.match(sinCultivo, /class="etiqueta-estado etiqueta-estado-falta">Falta rellenar</);
});

test("el botón cambia de palabra según haya cultivo o no", async () => {
  const conCultivo = await htmlDeCultivos();
  assert.match(conCultivo, /CAMBIARLO/);
  assert.doesNotMatch(conCultivo, /DECIR QUÉ HAY SEMBRADO/);
});

test("si repites el cultivo del año pasado, se avisa", async () => {
  // No es para reñir: sembrar lo mismo dos años seguidos gasta la tierra, y la rotación es una de las
  // medidas preventivas que la ley pide.
  //
  // **Y desde la ronda 90 va en su franja de aviso**, dentro de la tarjeta (como los avisos de una tierra y
  // como el motivo del almacén): es «algo que hay que mirar», y en esta aplicación eso lleva su señal.
  const repite = tierraDePrueba({ repite: true });
  const html = await htmlDeCultivos({ parcelas: [repite] });
  assert.match(html, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  assert.match(html, /Aquí has puesto lo mismo que el año pasado/);
  assert.doesNotMatch(await htmlDeCultivos(), /lo mismo que el año pasado/);
});

test("sin tierras se dice, en vez de enseñar una lista vacía", async () => {
  const html = await htmlDeCultivos({ parcelas: [], resumen: "" });
  assert.match(html, /Todavía no tienes parcelas\./);
  assert.doesNotMatch(html, /<ul class="lista">/);
});

test("qué hay sembrado no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeCultivos();
  // Los textos del servidor incluyen **lo que trae cada tierra** (su nombre, su detalle y sus filas):
  // eso lo prepara `app.js` con datos del agricultor, no lo escribe el componente.
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_CULTIVOS),
    ...todosLosTextos(tierraDePrueba()),
    "Tienes 1 tierra de 2 con el cultivo apuntado.",
    // La línea del historial la compone el componente juntando **la etiqueta del servidor** («Otros
    // años») con **el dato del agricultor** («2025: Trigo · 2024: Girasol»). Las dos partes son del
    // servidor; lo único que hace el componente es poner los dos puntos en medio.
    `${TEXTOS_DE_CULTIVOS.cultivos.otros_anos}: ${tierraDePrueba().anteriores}`,
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// La ayuda: lo que obliga la ley, los porqués y los cuatro bloques de abajo
// ---------------------------------------------------------------------------

/** Los textos de la ayuda, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_LA_AYUDA = {
  pantalla: {
    titulo: "Ayuda",
    intro: "Aquí está explicado todo lo que te pide el programa, en palabras normales. Si algo no lo entiendes, no lo apuntes mal: déjalo en blanco y pregúntame.",
    repetir_no_se: "Si no sabes qué pulsar, empieza por el botón grande. ¿Has echado algo para los bichos o las hierbas? Ese es.",
    ley_titulo: "Qué te obliga la ley, y qué no",
    ley_llevar: "Llevar el cuaderno al día y poder enseñarlo si te lo piden: eso sí es obligatorio.",
    ley_mandar: "Mandar los datos a la Junta por internet es voluntario. Lo dice el artículo 10.2 del Real Decreto 1054/2022: la ley te obliga a tener el registro, no a enviarlo. Si no lo mandas, no estás incumpliendo nada.",
    ley_programa: "Puedes llevar el cuaderno con un programa tuyo, no hace falta usar el de la Junta: lo permite el artículo 10.3 del mismo real decreto, siempre que ese programa tenga todo lo que pide su anexo II. Este recoge los trece apartados que pide, y más abajo está apuntado lo que todavía no recoge por dentro, para que no te fíes de más.",
    ley_fechas: "Las fechas que importan: los abonos se registran desde el 1 de enero de 2026, y el registro de los tratamientos puede ir en papel hasta el 31 de diciembre de 2026: a partir del 1 de enero de 2027 tiene que ser electrónico. El plan de abono es obligatorio desde el 1 de septiembre de 2026.",
    ley_cuando_obligatorio: "Y una cosa que se dice poco: el cuaderno electrónico solo será obligatorio en el siguiente periodo de la PAC, el que viene después de 2027, y solo para las fincas de más de 30 hectáreas de cultivo —tierras de labor y cultivos permanentes, sin contar los pastos temporales—, las de más de 5 hectáreas de regadío o las que tengan invernaderos de más de 0,1 hectáreas. Para las demás será voluntario, como ahora.",
    ley_sin_confirmar: "Hay una cosa que todavía no está aclarada: si llevando el registro en tu programa hay que ir mandando los datos a la Junta cada cierto tiempo. Está preguntado por escrito y aquí se dirá lo que contesten.",
    porques_titulo: "Para qué sirve esto",
    campos_titulo: "Qué significa cada cosa",
    reglas_titulo: "Las reglas de abono de las zonas de nitratos",
    reglas_intro: "Estas son las reglas del programa de actuación de Castilla y León. Solo se aplican si tu parcela está en una zona declarada con problemas de nitratos.",
    regla_con_numero: "El número que importa:",
    la_app_avisa: "El programa te avisa",
    la_app_consulta: "La tabla está aquí para consultarla; el programa aún no comprueba tu caso",
    la_app_no_puede: "El programa no lo puede comprobar",
    aportes_titulo: "Cuánto nitrógeno permite la tabla para cada cultivo",
    aportes_pista: "Estas cifras son para parcelas en zona de nitratos. La tabla permite ajustar la dosis según la cosecha esperada. Si tu cultivo o forma de riego no aparece, no adivines el límite.",
    periodos_titulo: "Cuándo no se puede abonar",
    periodos_pista: "La fecha depende del cultivo y del abono. Algunas reglas cuentan desde la siembra o hasta la cosecha; consulta el caso concreto antes de echarlo.",
    lo_que_falta_titulo: "Lo que el programa todavía no puede comprobar",
    lo_que_falta_intro: "Esto no lo tenemos y por eso no te avisamos de ello. No es un olvido: se dice para que lo sepas y lo mires tú o tu técnico.",
    unidad_nitrogeno: "kg N/ha",
    sin_cifra: "La tabla no da una cifra para este caso",
    secano: "Sin riego",
    regadio: "Con riego",
    organicos: "Abonos orgánicos",
    minerales: "Abonos minerales",
  },
  acciones: { volver: "VOLVER" },
};

// Cada punto de la ley **con su nombre** (ronda 83): antes iban los seis con el mismo rótulo del apartado y
// se leían como un muro, sin saber dónde acababa uno y empezaba el siguiente.
//
// Y desde la ronda 90, **los dos que contestan sí o no llevan su etiqueta** (del diseño de Stitch de esta
// pantalla): son los que responden a la pregunta con la que se entra en la ayuda. Los otros cuatro son
// explicaciones y no llevan etiqueta, porque no la tienen.
const LEY_DE_PRUEBA = [
  { titulo: "Llevar el cuaderno al día", texto: "Llevar el cuaderno al día y poder enseñarlo si te lo piden: eso sí es obligatorio.", etiqueta: "Sí es obligatorio", tipo: "obligatorio" },
  { titulo: "Mandar los datos a la Junta", texto: "Mandar los datos a la Junta por internet es voluntario. Lo dice el artículo 10.2 del Real Decreto 1054/2022: la ley te obliga a tener el registro, no a enviarlo. Si no lo mandas, no estás incumpliendo nada.", etiqueta: "Es voluntario", tipo: "voluntario" },
  { titulo: "Con un programa tuyo", texto: "Puedes llevar el cuaderno con un programa tuyo, no hace falta usar el de la Junta: lo permite el artículo 10.3 del mismo real decreto, siempre que ese programa tenga todo lo que pide su anexo II. Este recoge los trece apartados que pide, y más abajo está apuntado lo que todavía no recoge por dentro, para que no te fíes de más.", etiqueta: "", tipo: "" },
  { titulo: "Las fechas que importan", texto: "Las fechas que importan: los abonos se registran desde el 1 de enero de 2026, y el registro de los tratamientos puede ir en papel hasta el 31 de diciembre de 2026: a partir del 1 de enero de 2027 tiene que ser electrónico. El plan de abono es obligatorio desde el 1 de septiembre de 2026.", etiqueta: "", tipo: "" },
  { titulo: "Cuándo será obligatorio del todo", texto: "Y una cosa que se dice poco: el cuaderno electrónico solo será obligatorio en el siguiente periodo de la PAC, el que viene después de 2027, y solo para las fincas de más de 30 hectáreas de cultivo —tierras de labor y cultivos permanentes, sin contar los pastos temporales—, las de más de 5 hectáreas de regadío o las que tengan invernaderos de más de 0,1 hectáreas. Para las demás será voluntario, como ahora.", etiqueta: "", tipo: "" },
  { titulo: "Lo que todavía no está aclarado", texto: "Hay una cosa que todavía no está aclarada: si llevando el registro en tu programa hay que ir mandando los datos a la Junta cada cierto tiempo. Está preguntado por escrito y aquí se dirá lo que contesten.", etiqueta: "", tipo: "" },
];

const PORQUES_DE_PRUEBA = [
  {
    titulo: "Para qué sirve el cuaderno",
    texto: "Desde 2013, si echas productos para las plagas en tu finca, la ley te obliga a apuntarlo. Es el cuaderno donde queda escrito todo lo que haces en el campo. Sirve para tres cosas:\n1. Cumplir la ley. Si viene una inspección, es lo que te van a pedir.\n2. Saber qué hiciste. Si un cliente pregunta por una partida, lo tienes apuntado.\n3. Poder vender. Sin cuaderno no puedes demostrar qué echaste ni cuándo.",
  },
  {
    titulo: "En papel o en el móvil",
    texto: "Puedes llevarlo en papel hasta el 31 de diciembre de 2026. A partir del 1 de enero de 2027 tiene que ser electrónico. Si lo llevas aquí, no se te pierde, te calcula solo los días de espera y te avisa de lo que falta.",
  },
  {
    titulo: "Cuánto tiempo hay que guardar los papeles",
    texto: "Desde que apuntas algo hasta que puedes tirarlo pasan 3 años: la ley dice que los registros y los papeles que los justifican (las facturas, los certificados de la máquina, el asesoramiento) se conservan «al menos durante los 3 años siguientes a su fecha de emisión». Es el artículo 16.3 del Real Decreto 1311/2012, y está escrito entero en el documento de lo que obliga la ley. Aquí no se borra nada solo: si algo se anula, se queda con su motivo.",
  },
];

const REGLAS_DE_PRUEBA = [
  {
    que: "Cuánto nitrógeno puede llevar el estiércol",
    texto_valor: "170 kg N/ha al año",
    con_numero: "El número que importa:",
    como_lo_hace: "El programa te avisa",
  },
  {
    que: "Si la parcela tiene pendiente",
    texto_valor: "",
    con_numero: "El número que importa:",
    como_lo_hace: "La tabla está aquí para consultarla; el programa aún no comprueba tu caso",
  },
];

async function cargarAyuda() {
  return import(`../web/react/pantallas/ayuda.js?prueba=${Math.random()}`);
}

async function htmlDeLaAyuda(cambios = {}) {
  const { PantallaAyuda } = await cargarAyuda();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaAyuda, {
      textos: structuredClone(TEXTOS_DE_LA_AYUDA),
      ley: structuredClone(LEY_DE_PRUEBA),
      porques: [...PORQUES_DE_PRUEBA],
      campos: [{ titulo: "Tu NIF", que_es: "El número que te identifica.", por_que: "Con él se sabe de qué finca son los apuntes." }],
      reglas: structuredClone(REGLAS_DE_PRUEBA),
      aportes: [{ cultivo: "Trigo", secano: "170 kg N/ha · Maíz", regadio: "Sin cifra oficial" }],
      periodos: [{ grupo_cultivos: "Cultivos de secano", organicos: "Del 1 de julio al 31 de agosto", minerales: "Del 1 de junio al 31 de agosto" }],
      limites: ["Falta el límite de la cebada: no está en la Orden."],
      ...cambios,
    }),
  );
}

test("la ayuda explica qué obliga la ley, con el artículo a la vista y cada punto con su nombre", async () => {
  // **Los títulos se añadieron en la ronda 83.** Los seis puntos salían seguidos bajo el mismo rótulo del
  // apartado, así que no se sabía dónde acababa uno y empezaba el siguiente, y para encontrar «lo de
  // mandarlo a la Junta» había que leerlos todos.
  const html = await htmlDeLaAyuda();
  assert.match(html, /Qué te obliga la ley, y qué no/, "no hay apartado de la ley");
  for (const titulo of [
    "Llevar el cuaderno al día",
    "Mandar los datos a la Junta",
    "Con un programa tuyo",
    "Las fechas que importan",
    "Cuándo será obligatorio del todo",
    "Lo que todavía no está aclarado",
  ]) {
    assert.match(html, new RegExp(`<strong>${titulo}</strong>`), `el punto «${titulo}» va sin su nombre`);
  }
  assert.match(html, /artículo 10\.2 del Real Decreto 1054\/2022/, "falta la cita del envío");
  assert.match(html, /artículo 10\.3/, "no dice que se puede usar un programa propio");
  assert.match(html, /Está preguntado por escrito/, "no dice lo que todavía no está aclarado: prometería de más");
});

test("los dos puntos de la ley que contestan sí o no lo dicen en su etiqueta", async () => {
  // Del diseño de Stitch de la ayuda (ronda 90): la primera pregunta de quien empieza es «¿yo esto tengo
  // que mandarlo?», y esa respuesta se lee en la etiqueta sin leer el párrafo. Solo la llevan los dos
  // puntos que de verdad contestan sí o no: los otros cuatro son explicaciones.
  const html = await htmlDeLaAyuda();
  assert.match(html, /class="etiqueta-estado etiqueta-estado-obligatorio">Sí es obligatorio</);
  assert.match(html, /class="etiqueta-estado etiqueta-estado-voluntario">Es voluntario</);
  assert.equal(
    (html.match(/class="etiqueta-estado/g) || []).length,
    2,
    "hay etiquetas donde no toca: solo dos de los seis puntos contestan sí o no",
  );
});

test("la ayuda enseña todos los porqués, cada uno con su nombre", async () => {
  const html = await htmlDeLaAyuda();
  assert.match(html, /Desde 2013, si echas productos para las plagas/);
  assert.match(html, /Puedes llevarlo en papel hasta el 31 de diciembre de 2026/);
  assert.match(html, /pasan 3 años/, "no explica el plazo de conservación");
  assert.match(html, /artículo 16\.3/, "y no dice de dónde sale");
  // Y cada uno con su título delante: sin él eran párrafos seguidos y sin nombre (ronda 83).
  for (const titulo of [
    "Para qué sirve el cuaderno",
    "En papel o en el móvil",
    "Cuánto tiempo hay que guardar los papeles",
  ]) {
    assert.match(html, new RegExp(`<strong>${titulo}</strong>`), `el porqué «${titulo}» va sin su nombre`);
  }
});

test("la ayuda dice qué hace el programa con cada regla del abono", async () => {
  // Con su número y con lo que hace el programa: avisar, consultarla o no poder. Sin eso, una lista
  // de reglas parece una lista de deberes.
  const html = await htmlDeLaAyuda();
  assert.match(html, /Cuánto nitrógeno puede llevar el estiércol/);
  assert.match(html, /170 kg N\/ha al año/);
  assert.match(html, /El programa te avisa/);
  assert.match(html, /La tabla está aquí para consultarla/);
});

test("los dos bloques largos se abren al pulsarlos, no ocupan la pantalla", async () => {
  // Son tablas largas: si estuvieran siempre abiertas, taparían lo demás. `<details>` es lo que ya
  // sabe abrir y cerrar un lector de pantalla sin una línea de JavaScript.
  const html = await htmlDeLaAyuda();
  assert.match(html, /<details><summary>Cuánto nitrógeno permite la tabla para cada cultivo/);
  assert.equal((html.match(/<details>/g) || []).length, 2, "no son dos bloques los que se abren");
});

test("lo que todavía no está confirmado se dice, no se esconde", async () => {
  const html = await htmlDeLaAyuda();
  assert.match(html, /Falta el límite de la cebada/);
  const sinLimites = await htmlDeLaAyuda({ limites: [] });
  assert.doesNotMatch(sinLimites, /Falta el límite de la cebada/);
});

test("la ayuda no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLaAyuda();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_LA_AYUDA),
    ...todosLosTextos(LEY_DE_PRUEBA),
    ...todosLosTextos(PORQUES_DE_PRUEBA),
    ...todosLosTextos(REGLAS_DE_PRUEBA),
    "Tu NIF",
    "El número que te identifica.",
    "Con él se sabe de qué finca son los apuntes.",
    "Trigo",
    "170 kg N/ha · Maíz",
    "Sin cifra oficial",
    "Cultivos de secano",
    "Del 1 de julio al 31 de agosto",
    "Del 1 de junio al 31 de agosto",
    "Falta el límite de la cebada: no está en la Orden.",
    // La línea del número la compone el componente juntando **el rótulo del servidor** («El número
    // que importa:») con **la cifra de la regla** («170 kg N/ha al año»). Las dos partes son del
    // servidor; lo único que hace el componente es ponerlas seguidas.
    `${TEXTOS_DE_LA_AYUDA.pantalla.regla_con_numero} ${REGLAS_DE_PRUEBA[0].texto_valor}`,
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Mis datos»: la portada del cuaderno, la primera pantalla con campos en React
// ---------------------------------------------------------------------------

/** Los textos de «mis datos», tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_MIS_DATOS = {
  mis_datos: {
    titulo: "Mis datos",
    explica: "Estos son los datos que van en la primera hoja del cuaderno: quién eres y cómo se llama tu explotación. Se piden una vez y valen para todos los años.",
    guardado: "Tus datos están guardados. La portada del cuaderno ya los lleva.",
    guardar: "GUARDAR MIS DATOS",
    nombre: "¿Cómo te llamas?",
    nombre_pista: "Como viene en el cuaderno de la Junta",
    nif: "Tu NIF",
    nif_pista: "Con la letra. Es lo que se compara con tu certificado al entrar",
    registro_autonomico: "Nº de registro de tu explotación",
    registro_autonomico_pista: "Lo trae tu cuaderno de la Junta, arriba del todo. Es el que se pone en la portada",
    registro_nacional: "Nº de registro nacional (si lo tienes)",
    registro_nacional_pista: "Si no lo sabes, déjalo en blanco",
    direccion: "Tu dirección",
    direccion_pista: "La calle y el número, como en el cuaderno",
    localidad: "Tu pueblo o ciudad",
    localidad_pista: "",
    codigo_postal: "Código postal",
    codigo_postal_pista: "",
    provincia: "Provincia",
    provincia_pista: "",
    municipio: "Pueblo donde tienes las tierras",
    municipio_pista: "Si tienes tierras en varios, pon el principal",
    telefono: "Un teléfono",
    telefono_pista: "Por si hay que avisarte de algo del cuaderno",
    correo: "Tu correo",
    correo_pista: "",
  },
  // El bloque de las fincas: el botón que lleva a «quién entra en mi finca» y su explicación (ronda 90).
  fincas: {
    titulo: "Quién entra en mi finca",
    pista_boton: "Añadir otra cuenta que apunte en tu finca",
  },
  acciones: { volver: "VOLVER" },
};

/** Los once campos, con un valor puesto, como los prepara `app.js`. */
const CAMPOS_DE_PRUEBA = [
  ["nombre", "David Pérez Velasco"],
  ["nif", "70922320A"],
  ["registro_autonomico", "0837267320"],
  ["registro_nacional", "0-70922320-A"],
  ["direccion", "C/ Río Segre 6"],
  ["localidad", "Salamanca"],
  ["codigo_postal", "37006"],
  ["provincia", "Salamanca"],
  ["municipio", "Calvarrasa de Arriba"],
  ["telefono", "634597458"],
  ["correo", "david@ejemplo.test"],
].map(([campo, valor]) => ({ campo, valor }));

async function cargarMisDatos() {
  return import(`../web/react/pantallas/mis_datos.js?prueba=${Math.random()}`);
}

async function htmlDeMisDatos(cambios = {}) {
  const { PantallaMisDatos } = await cargarMisDatos();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaMisDatos, {
      textos: structuredClone(TEXTOS_DE_MIS_DATOS),
      campos: structuredClone(CAMPOS_DE_PRUEBA),
      guardado: false,
      error: "",
      ...cambios,
    }),
  );
}

test("mis datos enseña los once campos, con lo que ya hay guardado", async () => {
  // La lista de lo que le falta al cuaderno dice «mis datos → tu finca», así que esta pantalla tiene
  // que existir y enseñar lo que ya está puesto: si no, esa lista manda a un sitio que no está.
  const html = await htmlDeMisDatos();
  assert.match(html, /<h1>Mis datos<\/h1>/);
  for (const { campo } of CAMPOS_DE_PRUEBA) {
    assert.match(html, new RegExp(`id="finca-${campo}"`), `falta el campo de ${campo}`);
  }
  assert.match(html, /id="finca-registro_autonomico" type="text" value="0837267320"/);
  assert.match(html, /id="finca-localidad" type="text" value="Salamanca"/);
});

test("los campos llevan su id, que es como los lee el programa al guardar", async () => {
  // **La decisión de esta pantalla.** El manejador de clics es uno solo y vive en `app.js`, así que
  // quien guarda es él, y lee los campos por su `id`. Si los `id` cambiaran, decenas de pruebas
  // dejarían de comprobar nada (y el botón de guardar dejaría de encontrar los datos).
  const html = await htmlDeMisDatos();
  assert.match(html, /id="finca-nombre"/);
  assert.match(html, /id="finca-nif"/);
  assert.match(html, /id="finca-correo"/);
  // Y el botón de guardar con su acción de siempre.
  assert.match(html, /data-accion="mis-datos-guardar"/);
});

test("el aviso de guardado solo sale cuando se ha guardado", async () => {
  const sinGuardar = await htmlDeMisDatos();
  assert.doesNotMatch(sinGuardar, /Tus datos están guardados/);
  const guardado = await htmlDeMisDatos({ guardado: true });
  // La frase entera es la del servidor, así que se comprueba desde la propia copia: si un día se
  // alarga o se acorta, esta prueba no se queda vieja.
  const fraseDeGuardado = TEXTOS_DE_MIS_DATOS.mis_datos.guardado;
  assert.match(guardado, new RegExp(`<p class="aviso">${fraseDeGuardado.replace(/[.()]/g, "\\$&")}<\\/p>`));
});

test("si no se ha podido guardar, se dice con el aviso de error", async () => {
  const html = await htmlDeMisDatos({ error: "El NIF no es válido." });
  assert.match(html, /class="aviso aviso-error" role="alert"/);
  assert.match(html, /El NIF no es válido\./);
});

test("el botón de volver lleva a mi cuaderno, que es de donde se viene", async () => {
  const html = await htmlDeMisDatos();
  assert.match(html, /data-accion="inicio" data-ir="mi_cuaderno"/);
});

test("los campos van numerados y el botón de las fincas lleva su explicación", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): es un formulario de once renglones y sin números no
  // se sabe cuánto queda. Los números los pone el CSS con un contador, así que aquí lo que se comprueba es
  // que la lista existe y que **los `id` de los campos siguen siendo los mismos** (es como los lee `app.js`
  // al guardar).
  const html = await htmlDeMisDatos();
  assert.match(html, /<ol class="campos-numerados">/);
  assert.equal(
    (html.match(/<li><div class="campo">/g) || []).length,
    CAMPOS_DE_PRUEBA.length,
    "los campos no van uno por renglón numerado",
  );
  assert.match(html, /data-accion="quien-entra-abrir"/);
  assert.match(
    html,
    /<span class="pista-boton">Añadir otra cuenta que apunte en tu finca<\/span>/,
    "el botón de las fincas va sin explicación",
  );
});

test("mis datos no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeMisDatos();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_MIS_DATOS),
    ...todosLosTextos(CAMPOS_DE_PRUEBA),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// Las medidas preventivas: los diez botones de marcar y sus notas
// ---------------------------------------------------------------------------

/** Los textos de las medidas, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_MEDIDAS = {
  medidas: {
    titulo: "Lo que hago sin echar producto",
    explica: "Antes de echar producto, la ley pide haber probado otras cosas. Marca las que hagas en tu finca: se apuntan una vez y valen para todo el año.",
    marcar_titulo: "Marca lo que hagas en tu finca",
    marcar_pista: "Toca las que hagas. Si te equivocas, vuelve a tocarla y se desmarca.",
    catalogo_aviso: "Las diez preguntas son las medidas de la gestión integrada de plagas. El listado oficial de la Junta se publica «según catálogo» y no trae los códigos: los de aquí son internos, y lo que se imprime es el nombre de cada medida.",
    guardar: "GUARDAR",
    no_hago_ninguna: "No hago ninguna de estas cosas",
    hecho_en_mi_finca: "Hecho en mi finca",
    observaciones: "Lo que quieras añadir",
    tus_palabras: "Tus palabras",
    // Quitar la declaración entera (ronda 93).
    quitar: "BORRAR LO QUE HE DICHO DE ESTAS MEDIDAS",
    quitar_pista:
      "Esto no es decir que no haces ninguna: es dejar la finca sin contestar, como si no lo hubieras mirado nunca. El programa volverá a preguntártelo.",
  },
  acciones: { volver: "VOLVER" },
};

/** Las medidas de la finca, como las prepara `app.js`. Dos marcadas y una no. */
const MEDIDAS_DE_PRUEBA = [
  { codigo: "rotacion", pregunta: "¿Cambias de cultivo de un año a otro?", marcada: true, nota: "Trigo y veza" },
  { codigo: "higiene", pregunta: "¿Limpias la máquina al pasar de una parcela a otra?", marcada: true, nota: "" },
  { codigo: "observacion", pregunta: "¿Miras el campo antes de decidir echar algo?", marcada: false, nota: "" },
];

async function cargarMedidas() {
  return import(`../web/react/pantallas/medidas.js?prueba=${Math.random()}`);
}

async function htmlDeMedidas(cambios = {}) {
  const { PantallaMedidas } = await cargarMedidas();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaMedidas, {
      textos: structuredClone(TEXTOS_DE_MEDIDAS),
      medidas: structuredClone(MEDIDAS_DE_PRUEBA),
      ...cambios,
    }),
  );
}

test("las medidas se preguntan en cristiano, no con su código", async () => {
  const html = await htmlDeMedidas();
  assert.match(html, /Marca lo que hagas en tu finca/);
  assert.match(html, /¿Cambias de cultivo de un año a otro\?/);
  assert.match(html, /¿Limpias la máquina al pasar de una parcela a otra\?/);
  assert.doesNotMatch(html, />rotacion</, "se está enseñando el código en vez de la pregunta");
});

test("una medida marcada se ve marcada, y sin marcar también", async () => {  // Con el icono además del color: el proyecto tiene la regla de no informar con el color en
  // solitario, y aquí se cumple (✅ / ⬜ se leen igual en una foto mala y con sol).
  const html = await htmlDeMedidas();
  const marcadas = botonesDe(html).filter((boton) => boton.clases.includes("boton-elegido"));
  assert.equal(marcadas.length, 2, `hay ${marcadas.length} marcadas y son dos`);
  for (const boton of marcadas) {
    assert.equal(boton.icono, "✅", "una medida marcada sin su señal de marcada");
  }
  const sinMarcar = botonesDe(html).filter((boton) => boton.clases.includes("boton-claro"));
  assert.ok(sinMarcar.some((boton) => boton.icono === "⬜"), "ninguna medida sin marcar con su señal");
});

test("las diez medidas van numeradas y las hechas lo dicen con palabras", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): son diez casillas y, sin números, no se sabe cuántas
  // quedan por mirar (el número lo pone el CSS con un contador, así que la pregunta sigue siendo la del
  // servidor). Y lo marcado se dice **con palabras** además del visto y del color.
  const html = await htmlDeMedidas();
  assert.match(html, /<ol class="medidas-numeradas">/);
  assert.equal(
    (html.match(/<li><span class="etiqueta-estado/g) || []).length,
    MEDIDAS_DE_PRUEBA.filter((uno) => uno.marcada).length,
    "las etiquetas de «hecho en mi finca» no salen solo en las marcadas",
  );
  assert.match(html, /<span class="etiqueta-estado etiqueta-estado-bien">Hecho en mi finca<\/span>/);
});

test("cada botón lleva su código, que es como sabe el programa cuál se ha tocado", async () => {
  const html = await htmlDeMedidas();
  for (const medida of MEDIDAS_DE_PRUEBA) {
    assert.match(html, new RegExp(`data-accion="medidas-marcar" data-codigo="${medida.codigo}"`));
  }
});

test("la nota solo se pide de la medida que está marcada", async () => {
  // Pedir diez notas siempre sería pedir diez cosas para nada.
  const html = await htmlDeMedidas();
  assert.match(html, /id="nota-rotacion"/, "no deja escribir tus palabras en la medida marcada");
  assert.doesNotMatch(html, /id="nota-observacion"/, "pide nota de una medida sin marcar");
  // Y con lo que ya había escrito, para no perderlo al repintar. (El orden de los atributos no se
  // comprueba: React los pone en su orden, y lo que importa es que el valor esté.)
  assert.match(html, /id="nota-rotacion"[^>]*value="Trigo y veza"/);
});

test("los botones de las medidas no llevan flecha: no llevan a ninguna parte", async () => {
  // **Esto se cambió en la ronda 85.** La flecha, en esta aplicación, significa «esto te lleva a otro
  // sitio» (ver `Flecha`, en `componentes.js`): en un botón que solo marca y desmarca una cosa en la misma
  // pantalla, mentía. Lo que dice que se marca es el cuadro del icono (✅ / ⬜).
  const html = await htmlDeMedidas();
  const soloLasMedidas = html.split('data-accion="medidas-guardar"')[0];
  assert.doesNotMatch(soloLasMedidas, /class="flecha"/, "una medida lleva flecha y no va a ningún sitio");
  // Y los de abajo sí la llevan: esos sí salen de aquí (guardar, ninguna, volver).
  assert.match(html, /data-accion="medidas-guardar"[\s\S]*class="flecha"/, "el de guardar perdió su flecha");
});

test("los tres botones de abajo están, con su acción", async () => {
  const html = await htmlDeMedidas();
  const acciones = botonesDe(html)
    .map((boton) => boton.accion)
    .filter((accion) => accion !== "medidas-marcar");
  assert.deepEqual(acciones, ["medidas-guardar", "medidas-ninguna", "inicio"]);
  assert.match(html, /data-accion="inicio" data-ir="mi_cuaderno"/);
});

test("quitar la declaración se ofrece solo si hay declaración, y va aparte", async () => {
  // **Ronda 93.** No es lo mismo que «no hago ninguna»: eso es una respuesta y esto deja la finca sin
  // contestar. Por eso **no está en la barra de guardar**, sino debajo y con su explicación: es el botón
  // que quita algo, y no puede ser el que más apetezca pulsar.
  const sin = await htmlDeMedidas();
  assert.doesNotMatch(sin, /BORRAR LO QUE HE DICHO/, "ofrece quitar una declaración que no existe");
  assert.doesNotMatch(sin, /dejar la finca sin contestar/);

  const con = await htmlDeMedidas({ hay_declaracion: true });
  assert.match(con, /data-accion="medidas-quitar"/);
  assert.match(con, /BORRAR LO QUE HE DICHO DE ESTAS MEDIDAS/);
  assert.match(con, /es dejar la finca sin contestar/);
  // Y va **después** de la barra de guardar: el botón de quitar no se toca por ir a guardar.
  assert.ok(
    con.indexOf('data-accion="medidas-quitar"') > con.indexOf('data-accion="medidas-guardar"'),
    "el botón de quitar va antes que el de guardar",
  );
  assert.deepEqual(
    botonesDe(con)
      .map((boton) => boton.accion)
      .filter((accion) => accion === "medidas-quitar"),
    ["medidas-quitar"],
  );
});

test("la pantalla avisa de dónde salen las diez preguntas", async () => {
  const html = await htmlDeMedidas();
  assert.match(html, /los de aquí son internos/);
});

test("las medidas no llevan ni una frase escrita a mano", async () => {
  const html = await htmlDeMedidas();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_MEDIDAS),
    ...todosLosTextos(MEDIDAS_DE_PRUEBA),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Lo que he vendido»: la cosecha comercializada
// ---------------------------------------------------------------------------

/** Los textos de las ventas, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_VENTAS = {
  venta: {
    titulo: "Lo que he vendido",
    explica: "Aquí se apunta lo que sale de la finca: a quién, cuánto y de qué parcelas salió. Es lo que cierra el cuaderno por arriba.",
    lo_que_se_separa: "Una cosa es lo que coges de la tierra, otra lo que sacas de la finca, otra la factura que haces y otra el dinero que entra.",
    sin_nada: "Todavía no has apuntado ninguna venta este año.",
    vacio_filtro: "Ninguna entrega contesta a esos filtros. Prueba a quitarlos.",
    dinero_fuera: "Aquí se apunta lo que te han de pagar y lo que te han pagado. La factura que se hace desde esta pantalla es tu cuenta de lo que has vendido: no es un documento con validez oficial.",
    anadir: "APUNTAR UNA VENTA",
    sin_comprador: "No lo has dicho",
    // Buscar y filtrar (T12): el campo lleva su `id` y sus dos botones.
    buscar: "Buscar entre lo que has vendido",
    buscar_pista: "Escribe el nombre del cliente, el producto o el número del albarán.",
    buscar_boton: "BUSCAR",
    buscar_limpiar: "VERLO TODO",
    solo_pendientes: "SOLO LO QUE FALTA POR COBRAR",
    solo_sin_importe: "SOLO LO QUE NO TIENE IMPORTE",
    // Las puertas a las otras dos pantallas del dinero y a las acciones de cada entrega.
    facturas_abrir: "MIS FACTURAS DE LO VENDIDO",
    cobros_abrir: "LO QUE ME HAN PAGADO",
    poner_importe: "PONER EL IMPORTE",
    facturar_esto: "FACTURAR ESTA ENTREGA",
    ajuste_poner: "APUNTAR UNA DEVOLUCIÓN O UN AJUSTE",
    // Los rótulos de la tabla de la Junta y **las ocho columnas del contrato** (§4, S12).
    tipo: "Cómo lo vendiste",
    tabla_cuanto: "Cuánto",
    tabla_quien: "A quién",
    tabla_lote: "Partida",
    tabla_donde: "De dónde",
    tabla_albaran: "Albarán",
    tabla_cliente: "Cliente",
    tabla_producto: "Producto",
    tabla_fecha: "Fecha",
    tabla_cantidad: "Cantidad",
    tabla_importe: "Importe",
    tabla_vencimiento: "Vencimiento",
    tabla_cobrado: "Cobrado",
    tabla_pendiente: "Pendiente",
    tabla_estado: "Estado",
    estado_vencida_pista: "Pasó el día acordado y sigue sin pagarse.",
  },
  acciones: { volver: "VOLVER", corregir: "CORREGIR", borrar: "BORRAR" },
};

/**
 * Una tabla de ventas de las que prepara `app.js`: sus columnas del servidor, sus filas con las celdas ya
 * escritas, el pie del conjunto filtrado y los avisos. **Los números llegan ya calculados y en texto**,
 * porque la pantalla no hace ni una cuenta de dinero.
 */
function tablaDeVentasDePrueba(cambios = {}) {
  return {
    clave: "ventas",
    etiqueta: "Lo que he vendido",
    columnas: [
      { texto: "Cliente", campo: "cliente", ordenada: false, descendente: false, orden: "Ordenar por: Cliente" },
      { texto: "Producto", campo: "producto", ordenada: false, descendente: false, orden: "Ordenar por: Producto" },
      { texto: "Fecha", campo: "fecha", ordenada: true, descendente: false, orden: "Ordenar por: Fecha" },
      { texto: "Pendiente", campo: "pendiente", ordenada: false, descendente: false, orden: "Ordenar por: Pendiente" },
      { texto: "Estado", campo: "", ordenada: false, descendente: false, orden: "" },
    ],
    filas: [
      {
        id: 7,
        cliente: "Cooperativa de Peñaranda",
        producto: "Trigo blando",
        fecha: "10/07/2026",
        fecha_linea: "Fecha: 10/07/2026",
        cantidad: "8.000,00 kg",
        importe: "1.839,50 €",
        importe_valor: "1839.50",
        importe_conocido: true,
        vencimiento: "20/08/2026",
        cobrado: "40,00 €",
        pendiente: "1.799,50 €",
        estado: "Cobrada en parte",
        estado_vencida: false,
        partida: "L-7",
        albaran: "ALB-2026-118",
        donde: "El Prado",
        facturada: true,
        factura_numero: "F-2026-1",
        de_que_cosecha: "Trigo blando · 01/07/2026",
        cosecha_linea: "¿De qué cosecha salió?: Trigo blando · 01/07/2026",
        celdas: [
          { texto: "Cooperativa de Peñaranda" },
          { texto: "Trigo blando" },
          { texto: "10/07/2026" },
          { texto: "1.799,50 €", clase: "tabla-numero" },
          { texto: "Cobrada en parte" },
        ],
        acciones: [
          { etiqueta: "APUNTAR UNA DEVOLUCIÓN O UN AJUSTE", accion: "venta-ajuste", datos: { id: 7 } },
          { etiqueta: "CORREGIR", accion: "cosa-corregir", datos: { tipo: "venta", id: 7 } },
          { etiqueta: "BORRAR", accion: "cosa-borrar", datos: { tipo: "venta", id: 7 } },
        ],
      },
    ],
    resumen: "1 entrega · 1.839,50 € · pendiente 1.799,50 €",
    // El pie va en los dos sitios y con el mismo texto: en la línea destacada de la pantalla (`pie`) y en
    // el pie de la tabla del ordenador (`resumen`, que es como lo llama la pieza `Tabla`).
    pie: "1 entrega · 1.839,50 € · pendiente 1.799,50 €",
    avisos: [],
    totales: { entregas: 1, sin_importe: 0, por_cobrar: 1, pendiente: "1799.50" },
    ...cambios,
  };
}

async function cargarVentas() {
  return import(`../web/react/pantallas/ventas.js?prueba=${Math.random()}`);
}

async function htmlDeVentas(cambios = {}) {
  const { PantallaVentas } = await cargarVentas();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaVentas, {
      textos: structuredClone(TEXTOS_DE_VENTAS),
      tabla: tablaDeVentasDePrueba(),
      ...cambios,
    }),
  );
}

test("la tabla de lo que se ha vendido sale con sus columnas y el pie del servidor", async () => {
  const html = await htmlDeVentas();
  assert.match(html, /Aquí se apunta lo que sale de la finca/);
  // **Las cuatro cosas separadas**, dichas antes de la tabla (T12, S12 del contrato).
  assert.match(html, /Una cosa es lo que coges de la tierra/);
  // La tabla, con sus cabeceras y una fila con los datos de verdad.
  assert.match(html, /<table class="tabla"/);
  assert.match(html, /<th scope="col" class="tabla-ordenada"|Cliente/);
  assert.match(html, /Cooperativa de Peñaranda/);
  assert.match(html, /1\.799,50 €/);
  // **Y el pie, que es la cuenta del conjunto filtrado que calcula el servidor**: la pantalla lo coloca, no
  // lo suma. Es lo que hace que el pie y las filas no puedan contradecirse.
  assert.match(html, /data-pie="ventas"/);
  assert.match(html, /1 entrega · 1\.839,50 € · pendiente 1\.799,50 €/);
  // La cabecera que ordena, que es lo que se hace con una lista de entregas.
  assert.match(html, /data-accion="ordenar-tabla"/);
});

test("la tabla dice en su cabecera si la columna se puede ordenar", async () => {
  const html = await htmlDeVentas();
  // «Estado» no se puede ordenar (no tiene campo) y sale como texto, no como botón: un botón que no hace
  // nada es peor que no tenerlo.
  assert.match(html, /<th scope="col" class="">Estado<\/th>/);
  // Y la cabecera ordenada lleva su flecha por el CSS y su `aria-sort`, no solo el color.
  assert.match(html, /aria-sort="ascending"/);
});

test("lo que no tiene importe no se cuenta como cero: se dice", async () => {
  // El caso A08 del contrato dicho en el pie: un total que suma lo que hay y **calla** que le faltan
  // importes parece que cuadra, y no cuadra.
  const html = await htmlDeVentas({
    tabla: tablaDeVentasDePrueba({
      avisos: ["A 1 entrega le falta el importe, así que no entra en estas cuentas."],
      totales: { entregas: 2, sin_importe: 1, por_cobrar: 0 },
    }),
  });
  assert.match(html, /le falta el importe, así que no entra en estas cuentas/);
  // Y el filtro de «lo que no tiene importe» dice **cuántas** son, con su número.
  assert.match(html, /SOLO LO QUE NO TIENE IMPORTE \(1\)/);
});

test("cada entrega lleva sus acciones, que son el recorrido del dinero", async () => {
  const html = await htmlDeVentas();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  // Poner el importe, facturarla y apuntar una devolución: lo que completa el recorrido de negocio. Y
  // corregirla o borrarla, que ya estaba.
  assert.ok(acciones.includes("venta-ajuste"), "no deja apuntar una devolución o un ajuste");
  assert.ok(acciones.includes("cosa-corregir"));
  assert.ok(acciones.includes("cosa-borrar"));
  // Esta entrega **ya tiene importe y ya está facturada**, así que no ofrece facturarla otra vez: es la
  // mitad de «al agrupar no se pueden duplicar los ingresos» dicha en la pantalla.
  assert.ok(!acciones.includes("ventas-facturar"), "ofrece facturar una entrega que ya está facturada");
  // Y las tres puertas de abajo.
  for (const esperada of ["ventas-nueva", "facturas-emitidas-ver", "cobros-ver", "inicio"]) {
    assert.ok(acciones.includes(esperada), `falta el botón ${esperada}`);
  }
});

test("una entrega sin importe ofrece ponerlo, y no ofrece facturarla", async () => {
  const tabla = tablaDeVentasDePrueba();
  tabla.filas[0].cedulas = undefined;
  const html = await htmlDeVentas({
    tabla: {
      ...tabla,
      filas: [
        {
          ...tabla.filas[0],
          importe: "",
          importe_conocido: false,
          facturada: false,
          estado: "Falta el importe",
          acciones: [
            { etiqueta: "PONER EL IMPORTE", accion: "venta-importe", datos: { id: 7 } },
            { etiqueta: "FACTURAR ESTA ENTREGA", accion: "ventas-facturar", datos: { id: 7 } },
          ],
        },
      ],
    },
  });
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.ok(acciones.includes("venta-importe"), "no ofrece ponerle el importe (caso A08)");
  assert.match(html, /Falta el importe/);
});

test("la barra de buscar y los dos filtros salen, con el campo que lee app.js", async () => {
  const html = await htmlDeVentas();
  // El `id` del campo es lo único que tiene `app.js` para leer lo escrito: sin él, buscar no haría nada.
  assert.match(html, /id="buscar_venta"/);
  assert.match(html, /data-accion="ventas-buscar"/);
  assert.match(html, /data-accion="ventas-solo-pendientes"/);
  assert.match(html, /data-accion="ventas-solo-sin-importe"/);
  // Y con un filtro puesto sale el botón de quitarlo: si no, el agricultor no sabría por qué ve cuatro
  // entregas de las cuarenta.
  const filtrada = await htmlDeVentas({ filtros: { q: "cebada", solo: "" } });
  assert.match(filtrada, /data-accion="ventas-ver-todas"/);
  assert.match(filtrada, /value="cebada"/);
});

test("sin nada se dice, y con un filtro puesto se dice otra cosa", async () => {
  const vacia = await htmlDeVentas({ tabla: tablaDeVentasDePrueba({ filas: [], resumen: "" }) });
  assert.match(vacia, /Todavía no has apuntado ninguna venta/);
  assert.doesNotMatch(vacia, /<table class="tabla"/, "ha dibujado una tabla sin nada dentro");
  // **Un filtro que no deja nada no es una lista vacía**: decir «todavía no has apuntado nada» cuando lo
  // que pasa es que el filtro no casa sería mentirle al agricultor.
  const filtrada = await htmlDeVentas({
    tabla: tablaDeVentasDePrueba({ filas: [], resumen: "" }),
    filtros: { q: "cebada", solo: "" },
  });
  assert.match(filtrada, /Ninguna entrega contesta a esos filtros/);
  assert.doesNotMatch(filtrada, /Todavía no has apuntado/);
});

test("el aviso de que la factura no es un documento oficial sale siempre", async () => {
  const html = await htmlDeVentas();
  assert.match(html, /no es un documento con validez oficial/);
});

test("las ventas no llevan ni una frase escrita a mano", async () => {
  // Sin ningún filtro puesto y con las cuentas a cero, **todo lo que se lee sale del servidor**: los
  // rótulos de las columnas, el estado de cada fila, el pie y los dos botones de filtro. Si alguien
  // escribiera una frase dentro del componente, este test la caza.
  const html = await htmlDeVentas({
    aviso: "Importe apuntado.",
    tabla: tablaDeVentasDePrueba({ totales: { entregas: 1, sin_importe: 0, por_cobrar: 0 } }),
  });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_VENTAS),
    ...todosLosTextos(tablaDeVentasDePrueba({ totales: { entregas: 1, sin_importe: 0, por_cobrar: 0 } })),
    "Importe apuntado.",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Quién entra en mi finca»: las cuentas que apuntan en el mismo cuaderno (ronda 89)
//
// Es la pantalla que hizo falta para lo que pidió David —«que una explotación puedan acceder varias
// cuentas, no solo 1»—: el servidor ya lo sabía hacer y no había forma de llegar desde el móvil.
// ---------------------------------------------------------------------------

/** Los textos de las fincas, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_LAS_FINCAS = {
  fincas: {
    titulo: "Quién entra en mi finca",
    explica: "En tu finca puede entrar más de una cuenta: la tuya y la de quien te ayude (tu mujer, tu hijo, el técnico). Todos ven lo mismo y apuntan en el mismo cuaderno. Tú decides quién entra.",
    cambiar_titulo: "En qué finca estás trabajando",
    cambiar_explica: "Si puedes entrar en más de una finca, aquí eliges en cuál estás apuntando. Lo que apuntes va a la finca que elijas.",
    estas_en: "Estás en",
    entrar_en: "PONME EN ESTA FINCA",
    la_tuya: "Tuya",
    papel_ayudante: "Ayudas en ella",
    anadir: "AÑADIR UNA CUENTA",
    que_correo: "¿Con qué correo entra?",
    que_correo_pista: "El correo con el que se dio de alta esa persona",
    anadir_pista: "La otra persona tiene que tener ya su cuenta hecha con ese correo: tú no puedes ponerle la clave.",
    quitar: "QUITARLE EL ACCESO",
    titular: "Tú (titular)",
    papel_titular: "El titular de la finca",
    ayudante: "Ayuda en la finca",
    tu_cuenta: "Tu cuenta",
    eres_el_titular: "Eres el titular de esta finca: puedes añadir y quitar cuentas.",
    no_eres_el_titular: "En esta finca decide el titular quién entra. Si quieres que entre otra persona, pídeselo al titular.",
    solo_una: "De momento solo entras tú.",
    anadida: "Ya puede entrar en tu finca.",
    quitada: "Ya no entra en tu finca.",
    // Lo que puede hacer quien ayuda y la etiqueta de la finca en la que se está (ronda 90).
    que_puede_ayudante:
      "Puede apuntar lo que se haga en la finca con su propio móvil. No puede decidir quién entra ni quitar cuentas.",
    estas_aqui: "Estás trabajando aquí ahora",
    // Los avisos que manda el **servidor** y que se leen tal cual en esta pantalla (por ejemplo, cuando
    // el correo que se escribe no es de ninguna cuenta). Se copia uno, que es el que usa la prueba del
    // aviso de error: los demás van por el mismo camino.
    cuenta_que_no_existe: "No hay ninguna cuenta con ese correo. Que se dé de alta primero (con su correo y su clave) y vuelve a añadirla.",
  },
  acciones: { volver: "VOLVER" },
};

/**
 * Quién entra en la finca, como lo prepara `app.js` a partir de `/api/fincas/quien-entra`.
 *
 * Dos cuentas: el titular (David) y su hijo, que ayuda. Es el caso de verdad, y el que hace falta para
 * comprobar que los papeles **no se confunden**: el mismo dato («titular») se lee de una forma cuando es
 * tuyo y de otra cuando es de otro.
 */
const PERSONAS_DE_PRUEBA = [
  {
    usuario_id: 1,
    nombre: "David Pérez Velasco",
    correo: "david@ejemplo.test",
    papel: "titular",
    eres_tu: true,
    se_puede_quitar: false,
  },
  {
    usuario_id: 4,
    nombre: "Ana Pérez",
    correo: "ana@ejemplo.test",
    papel: "ayudante",
    eres_tu: false,
    se_puede_quitar: true,
  },
];

/** Las mismas dos cuentas, pero mirando desde la de ayuda: ahí el titular es «otro». */
const PERSONAS_MIRANDO_EL_AYUDANTE = [
  { ...PERSONAS_DE_PRUEBA[0], eres_tu: false, se_puede_quitar: true },
  { ...PERSONAS_DE_PRUEBA[1], eres_tu: true, se_puede_quitar: true },
];

/** Las fincas en las que puede entrar la cuenta: una suya y otra en la que ayuda. */
const FINCAS_DE_PRUEBA = [
  {
    id: 1,
    nombre: "La finca de David",
    municipio: "Calvarrasa de Arriba",
    papel: "titular",
    activa: true,
    hectareas: "142,88 ha",
  },
  {
    id: 3,
    nombre: "Las del río",
    municipio: "Cabrerizos",
    papel: "ayudante",
    activa: false,
    hectareas: "18,50 ha",
  },
];

async function cargarQuienEntra() {
  return import(`../web/react/pantallas/quien_entra.js?prueba=${Math.random()}`);
}

async function htmlDeQuienEntra(cambios = {}) {
  const { PantallaQuienEntra } = await cargarQuienEntra();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaQuienEntra, {
      textos: structuredClone(TEXTOS_DE_LAS_FINCAS),
      finca: "La finca de David",
      fincas: structuredClone(FINCAS_DE_PRUEBA),
      personas: structuredClone(PERSONAS_DE_PRUEBA),
      soyTitular: true,
      aviso: "",
      error: "",
      ...cambios,
    }),
  );
}

test("la pantalla dice quién entra y en qué finca estás", async () => {
  const html = await htmlDeQuienEntra();
  const d = TEXTOS_DE_LAS_FINCAS.fincas;
  assert.match(html, new RegExp(`<h1>${d.titulo}</h1>`));
  assert.match(html, new RegExp(d.estas_en), "no dice en qué finca se está trabajando");
  assert.match(html, /La finca de David/);
  for (const persona of PERSONAS_DE_PRUEBA) {
    assert.match(html, new RegExp(persona.nombre), `no sale ${persona.nombre}`);
    assert.match(html, new RegExp(persona.correo.replace(/[.@]/g, "\\$&")), "no sale su correo");
  }
});

test("el mismo papel se lee distinto según quién mire", async () => {
  // **El fallo que esto evita**: decirle «Tú (titular)» al titular cuando quien está mirando es el
  // ayudante, o dejar al ayudante sin saber cuál de las dos cuentas es la suya.
  const delTitular = await htmlDeQuienEntra();
  assert.match(delTitular, /Tú \(titular\)/);
  assert.match(delTitular, /Ayuda en la finca/);
  assert.doesNotMatch(delTitular, /El titular de la finca/, "el titular se llama «tú» y también «él»");
  assert.doesNotMatch(delTitular, /Tu cuenta/);

  const delAyudante = await htmlDeQuienEntra({
    personas: structuredClone(PERSONAS_MIRANDO_EL_AYUDANTE),
    soyTitular: false,
  });
  assert.match(delAyudante, /El titular de la finca/);
  assert.match(delAyudante, /Tu cuenta/);
  assert.doesNotMatch(delAyudante, /Tú \(titular\)/, "el ayudante no es el titular de la finca");
});

test("el titular puede añadir cuentas y el ayudante no", async () => {
  // Solo el titular manda en quién entra: es la regla del servidor (403 «solo el titular»), y la pantalla
  // no puede ofrecer un botón que va a dar error. Al ayudante se le dice qué hacer para que entre alguien.
  const delTitular = await htmlDeQuienEntra();
  assert.deepEqual(idsDe(delTitular), ["persona-correo"], "no hay dónde escribir el correo");
  assert.match(delTitular, /data-accion="finca-anadir"/);
  assert.match(delTitular, new RegExp(TEXTOS_DE_LAS_FINCAS.fincas.eres_el_titular.slice(0, 30)));
  assert.match(delTitular, new RegExp(TEXTOS_DE_LAS_FINCAS.fincas.anadir_pista.slice(0, 30)));

  const delAyudante = await htmlDeQuienEntra({
    personas: structuredClone(PERSONAS_MIRANDO_EL_AYUDANTE),
    soyTitular: false,
  });
  assert.deepEqual(idsDe(delAyudante), [], "el ayudante tiene un campo que no le toca");
  assert.doesNotMatch(delAyudante, /data-accion="finca-anadir"/, "el ayudante puede añadir cuentas");
  assert.match(delAyudante, new RegExp(TEXTOS_DE_LAS_FINCAS.fincas.no_eres_el_titular.slice(0, 30)));
});

test("el botón de quitar solo sale donde se puede quitar", async () => {
  // Al titular de la finca no se le puede quitar (lo impide el servidor: una finca sin titular se queda
  // sin quien la gestiona), así que su botón **no se pinta**. Un botón que lleva a un error es peor que
  // no ponerlo.
  const html = await htmlDeQuienEntra();
  const quitar = botonesDe(html).filter((boton) => boton.accion === "finca-quitar");
  assert.equal(quitar.length, 1, `salen ${quitar.length} botones de quitar y solo hay una cuenta que se pueda quitar`);
  assert.match(html, /data-accion="finca-quitar" data-persona="4"/, "no dice a qué cuenta se le quita");
  assert.match(html, /QUITARLE EL ACCESO/);
});

test("de momento solo entras tú: se dice, en vez de dejar una lista de uno", async () => {
  const html = await htmlDeQuienEntra({
    personas: [structuredClone(PERSONAS_DE_PRUEBA[0])],
  });
  assert.match(html, new RegExp(TEXTOS_DE_LAS_FINCAS.fincas.solo_una));
});

test("cambiar de finca solo sale cuando hay más de una", async () => {
  // Con una sola finca, un bloque que enseña una lista de uno es ruido: no hay nada que elegir. Y en
  // cuanto hay dos, es lo que hace falta para no apuntar en la finca que no es.
  const una = await htmlDeQuienEntra({ fincas: [structuredClone(FINCAS_DE_PRUEBA[0])] });
  assert.doesNotMatch(una, new RegExp(TEXTOS_DE_LAS_FINCAS.fincas.cambiar_titulo));
  assert.doesNotMatch(una, /data-accion="finca-entrar"/);

  const dos = await htmlDeQuienEntra();
  assert.match(dos, new RegExp(TEXTOS_DE_LAS_FINCAS.fincas.cambiar_titulo));
  assert.match(dos, /Las del río/, "no sale la otra finca");
  assert.match(dos, /Ayudas en ella/, "no dice de qué va esa finca");
  // Cada finca lleva sus hectáreas (ronda 90, diseño de Stitch): al elegir en cuál trabajas, el tamaño es
  // lo que distingue una finca de otra cuando se llaman parecido. El número lo escribe `app.js`.
  assert.match(dos, /<span class="cuantas">142,88 ha<\/span>/, "la finca no dice sus hectáreas");
  assert.match(dos, /<span class="cuantas">18,50 ha<\/span>/);
  // Y el botón de ponerse en ella lleva **la otra**, no la que ya está puesta: en la finca en la que ya
  // se está no se pinta botón, porque no cambiaría nada; en su lugar se dice con palabras.
  assert.match(dos, /data-accion="finca-entrar" data-id="3"/);
  assert.doesNotMatch(dos, /data-accion="finca-entrar" data-id="1"/);
  assert.match(dos, /Estás trabajando aquí ahora/, "la finca activa se queda sin botón y sin decirlo");
});

test("se dice qué puede hacer quien ayuda", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): sin decirlo, el titular no sabe qué le está dando a
  // la otra persona. Es lo que hace de verdad el servidor: apunta con su cuenta y no decide quién entra.
  const html = await htmlDeQuienEntra();
  assert.match(html, /Puede apuntar lo que se haga en la finca con su propio móvil/);
  // Y no se le dice al titular de sí mismo: eso ya lo dice su propia frase.
  const soloTitular = await htmlDeQuienEntra({ personas: [structuredClone(PERSONAS_DE_PRUEBA[0])] });
  assert.doesNotMatch(soloTitular, /Puede apuntar lo que se haga en la finca/);
});

test("cuando la lista cambia se dice, y cuando algo falla se dice con el aviso de error", async () => {
  const anadida = await htmlDeQuienEntra({ aviso: TEXTOS_DE_LAS_FINCAS.fincas.anadida });
  assert.match(anadida, new RegExp(`<p class="aviso">${TEXTOS_DE_LAS_FINCAS.fincas.anadida}</p>`));
  assert.doesNotMatch(await htmlDeQuienEntra(), /class="aviso"/, "avisa sin que haya pasado nada");

  const conError = await htmlDeQuienEntra({ error: TEXTOS_DE_LAS_FINCAS.fincas.cuenta_que_no_existe });
  assert.match(conError, /class="aviso aviso-error" role="alert"/);
  assert.match(conError, /No hay ninguna cuenta con ese correo/);
});

test("el botón de volver lleva a mi cuaderno, que es de donde se viene", async () => {
  const html = await htmlDeQuienEntra();
  assert.match(html, /data-accion="inicio" data-ir="mi_cuaderno"/);
});

test("esta pantalla no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeQuienEntra();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_LAS_FINCAS),
    ...todosLosTextos(FINCAS_DE_PRUEBA),
    ...todosLosTextos(PERSONAS_DE_PRUEBA),
    "La finca de David",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// Los grupos de parcelas: las tierras que se llevan igual y se apuntan de una vez
// ---------------------------------------------------------------------------

/** Los textos de los grupos, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DE_GRUPOS = {
  grupos: {
    titulo: "Parcelas que se llevan igual",
    explica: "Cuando varias parcelas tienen lo mismo y se labran igual, se pueden apuntar de una vez: un tratamiento para las seis, en vez de seis apuntes.",
    faltan_cultivos: "Para juntarlas hace falta saber qué hay sembrado en cada una. Hay parcelas sin decirlo.",
    sin_grupos: "Todavía no has juntado ninguna parcela. Al apuntar un tratamiento, después de la lista de parcelas te saldrán los grupos que tengas.",
    para_que: "El cuaderno sigue diciendo qué se hizo en cada parcela, porque el grupo las lleva dentro. Lo que se ahorra es escribirlo seis veces.",
    calcular: "JUNTARLAS TÚ SOLO",
    automatico: "Lo juntó el programa.",
    // De quién es el grupo y el rótulo de sus tierras (ronda 90).
    juntado_por_ti: "Juntado por ti.",
    tierras_del_grupo: "Tierras que van juntas en este grupo:",
  },
  cultivos: { titulo: "Qué hay sembrado" },
  maestros: { titulo: "Mis parcelas, productos y máquinas" },
  acciones: { volver: "VOLVER" },
};

const GRUPOS_DE_PRUEBA = [
  {
    nombre: "Cebada (3 parcelas)",
    detalle: "3 parcelas · 10,00 ha · Cebada",
    parcelas: "El Prado · La Vega · El Alto",
    // Las tierras del grupo, una por una y con sus hectáreas (ronda 90).
    tierras: [
      { nombre: "El Prado", hectareas: "4,90 ha" },
      { nombre: "La Vega", hectareas: "3,20 ha" },
      { nombre: "El Alto", hectareas: "1,90 ha" },
    ],
    automatico: true,
  },
  {
    nombre: "Las del arroyo",
    detalle: "2 parcelas · 4,50 ha",
    parcelas: "El Soto · La Isla",
    tierras: [
      { nombre: "El Soto", hectareas: "2,50 ha" },
      { nombre: "La Isla", hectareas: "2,00 ha" },
    ],
    automatico: false,
  },
];

async function cargarGrupos() {
  return import(`../web/react/pantallas/grupos.js?prueba=${Math.random()}`);
}

async function htmlDeGrupos(cambios = {}) {
  const { PantallaGrupos } = await cargarGrupos();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaGrupos, {
      textos: structuredClone(TEXTOS_DE_GRUPOS),
      grupos: structuredClone(GRUPOS_DE_PRUEBA),
      faltanCultivos: 0,
      error: "",
      ...cambios,
    }),
  );
}

test("los grupos salen con sus parcelas y su superficie", async () => {
  const html = await htmlDeGrupos();
  assert.match(html, /Cebada \(3 parcelas\)/);
  assert.match(html, /3 parcelas · 10,00 ha · Cebada/);
  assert.match(html, /JUNTARLAS TÚ SOLO|CALCULAR/i, "no ofrece juntarlas");
});

test("cada grupo enseña sus tierras una por una y con sus hectáreas", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): antes era una línea con los nombres separados por
  // puntos («El Prado · La Vega · El Alto»), y con seis tierras no se sabía ni cuál era cuál ni cuánto tenía
  // cada una. Ahora van una por línea con sus hectáreas (el número lo pone el CSS con un contador).
  const html = await htmlDeGrupos();
  assert.match(html, /Tierras que van juntas en este grupo:/);
  assert.match(html, /<ol class="tierras-del-grupo">/);
  assert.match(html, /<li><span>El Prado<\/span><span>4,90 ha<\/span><\/li>/);
  assert.match(html, /<li><span>La Isla<\/span><span>2,00 ha<\/span><\/li>/);
  // Y de quién es el grupo, en su etiqueta: lo juntó el programa o lo juntó él.
  assert.match(html, /class="etiqueta-estado etiqueta-estado-voluntario">Lo juntó el programa\.</);
  assert.match(html, /class="etiqueta-estado etiqueta-estado-voluntario">Juntado por ti\.</);
});

test("un grupo hecho solo se distingue de uno hecho a mano", async () => {
  const html = await htmlDeGrupos();
  const automatico = TEXTOS_DE_GRUPOS.grupos.automatico;
  assert.equal(
    (html.match(new RegExp(automatico.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g")) || []).length,
    1,
    "el aviso de «hecho solo» sale donde no toca, o no sale donde toca",
  );
});

test("si faltan cultivos, se avisa y se da el botón que lo arregla", async () => {
  // **Esto importa de verdad**: el grupo automático se hace por cultivo, así que sin los cultivos
  // dichos el botón de calcular no puede hacer lo que promete. En vez de dejar un botón que no hace
  // nada, se dice y se lleva a donde se arregla (la regla de no dejar al agricultor sin salida).
  const html = await htmlDeGrupos({ faltanCultivos: 4 });
  assert.match(html, new RegExp(TEXTOS_DE_GRUPOS.grupos.faltan_cultivos.slice(0, 30)));
  assert.match(html, /data-accion="cultivo-ver-todos"/);
  // Y sin cultivos pendientes no se avisa de eso.
  assert.doesNotMatch(await htmlDeGrupos(), /data-accion="cultivo-ver-todos"/);
});

test("sin ningún grupo se dice, en vez de dejar la lista vacía", async () => {
  const vacia = await htmlDeGrupos({ grupos: [] });
  assert.match(vacia, /class="aviso"/);
  assert.doesNotMatch(vacia, /<ul class="lista">/, "ha dibujado una lista sin nada dentro");
});

test("los tres botones de abajo están, con su acción", async () => {
  const html = await htmlDeGrupos();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["grupo-calcular", "mis-cosas", "ir-inicio"]);
  assert.match(html, /class="boton boton-principal" data-accion="grupo-calcular"/);
});

test("los grupos no llevan ni una frase escrita a mano", async () => {
  const html = await htmlDeGrupos();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_GRUPOS),
    ...todosLosTextos(GRUPOS_DE_PRUEBA),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// El resumen del asistente: la primera PIEZA de React (no una pantalla entera)
//
// El asistente se pinta con la interfaz vieja, paso a paso. Lo que se ha migrado es **el resumen
// final**, que es el paso que más se ve, dejando que el paso diga `montar` en vez de `pintar`: React
// llena el hueco del formulario y el motor del asistente no se toca. Por eso este componente vive en
// `react/piezas/` y no en `react/pantallas/`: no es una pantalla, es un trozo.
//
// Lo que se comprueba aquí: que **solo salen las filas que tienen dato** (un resumen con cinco «—» no
// ayuda a repasar antes de guardar) y que el aviso del plazo de espera sale cuando toca, porque es lo
// que evita que el agricultor coja la cosecha antes de tiempo.
// ---------------------------------------------------------------------------

async function htmlDelResumen(cambios = {}) {
  const { ResumenDelApunte } = await import(
    `../web/react/piezas/resumen_del_apunte.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(ResumenDelApunte, {
      filas: [
        ["¿Dónde?", "El Prado"],
        ["¿Cuándo?", "10/04/2026"],
        ["Producto", "Glifosato 36 SL"],
        ["Por hectárea", "3,00 L/ha"],
        ["¿Por qué lo has echado?", "Vi la plaga o la hierba en el campo"],
      ],
      ...cambios,
    }),
  );
}

test("el resumen sale con sus filas de etiqueta y valor", async () => {
  const html = await htmlDelResumen();
  assert.match(html, /<dt>¿Dónde\?<\/dt><dd>El Prado<\/dd>/);
  assert.match(html, /<dt>Producto<\/dt><dd>Glifosato 36 SL<\/dd>/);
  assert.match(html, /<dt>Por hectárea<\/dt><dd>3,00 L\/ha<\/dd>/);
  // Y lo que no tiene dato **no se pinta**: quien decide qué filas hay es `app.js`, y esto no
  // inventa ninguna.
  assert.equal((html.match(/<dt>/g) || []).length, 5, "ha añadido filas que no le han dado");
});

test("el resumen puede llevar un rótulo encima, y sin él no deja el hueco", async () => {
  // **Ronda 92, del diseño de Stitch.** El resumen del asistente no lleva rótulo (la pregunta de arriba
  // ya dice qué es), pero el mismo trozo se usa en la pantalla que pregunta si de verdad se quiere
  // borrar algo, y allí lo que se lee **es lo que va a desaparecer**: una caja de datos sin título es una
  // caja de datos, y el agricultor tiene que saber de un vistazo qué está mirando.
  const conTitulo = await htmlDelResumen({ titulo: "Lo que va a desaparecer de tu cuaderno" });
  assert.match(conTitulo, /<h2>Lo que va a desaparecer de tu cuaderno<\/h2>/);
  assert.ok(
    conTitulo.indexOf("<h2>") < conTitulo.indexOf("<dl>"),
    "el rótulo sale después de los datos, donde no dice nada",
  );
  const sinTitulo = await htmlDelResumen();
  assert.doesNotMatch(sinTitulo, /<h2>/, "el resumen del asistente lleva un rótulo que no se le ha pedido");
});

test("el aviso del plazo de espera sale cuando toca, con sus días", async () => {
  // Es lo que evita que el agricultor coja la cosecha antes de tiempo.
  const html = await htmlDelResumen({
    espera: {
      texto: "Fíjate: con lo que has echado hoy, en esta parcela no podrás coger la cosecha hasta el 01/05/2026.",
      dias: "Faltan 21 días.",
    },
  });
  assert.match(html, /class="ayuda-campo"/);
  assert.match(html, /no podrás coger la cosecha hasta el 01\/05\/2026/);
  assert.match(html, /Faltan 21 días\./);
  // Y sin plazo de espera no se dibuja el bloque: un hueco con un aviso vacío asusta sin motivo.
  assert.doesNotMatch(await htmlDelResumen(), /ayuda-campo/);
  // Cuando no se pueden contar los días (la fecha no es de este año, por ejemplo), se dice el plazo
  // sin los días, pero no se inventa un número.
  const sinDias = await htmlDelResumen({
    espera: { texto: "No podrás coger la cosecha hasta el 01/05/2026.", dias: "" },
  });
  assert.match(sinDias, /No podrás coger la cosecha/);
  assert.doesNotMatch(sinDias, /Faltan/);
});

test("el resumen del apunte no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDelResumen({
    espera: { texto: "No podrás coger la cosecha hasta el 01/05/2026.", dias: "Faltan 21 días." },
  });
  const delServidor = new Set([
    "¿Dónde?",
    "El Prado",
    "¿Cuándo?",
    "10/04/2026",
    "Producto",
    "Glifosato 36 SL",
    "Por hectárea",
    "3,00 L/ha",
    "¿Por qué lo has echado?",
    "Vi la plaga o la hierba en el campo",
    "No podrás coger la cosecha hasta el 01/05/2026.",
    "Faltan 21 días.",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// La lista de botones del asistente: la segunda PIEZA de React
//
// La mitad de los pasos del asistente son la misma pantalla: una lista donde el agricultor toca la
// tierra, la nave, el producto o el trabajo que ha hecho. Estaban escritos siete veces en `app.js` y
// cada copia se acordaba de cosas distintas. Ahora hay **una pieza** (`react/piezas/lista_para_elegir.js`)
// y `app.js` le pasa los botones ya preparados.
//
// Lo que se comprueba aquí, y por qué:
//
//  1. **Los `data-*` de cada botón**, que son lo único que lee el manejador de clics de `app.js`: si
//     falta `data-campo`, el agricultor toca y no pasa nada.
//  2. **El que ya estaba elegido va marcado** (`boton-elegido`), que es como sabe volver atrás.
//  3. **El aviso va con el botón que lo arregla**: cuando no hay ninguna tierra dada de alta, un aviso
//     solo deja al agricultor sin salida.
//  4. Que no haya ni una frase escrita a mano.
// ---------------------------------------------------------------------------

/** Una lista de prueba: dos tierras (una ya elegida) y la salida de «no es una parcela». */
function listaDePrueba(cambios = {}) {
  return {
    bloques: [
      {
        botones: [
          {
            etiqueta: "El Prado",
            pista: "2,43 ha · secano",
            icono: "📍",
            accion: "elegir",
            datos: { campo: "parcela_id", valor: 1, superficie: 2.43 },
            clase: "boton-elegido",
          },
          {
            etiqueta: "La Vega",
            pista: "5,00 ha · regadío",
            icono: "📍",
            accion: "elegir",
            datos: { campo: "parcela_id", valor: 2, superficie: 5 },
            clase: "boton-claro",
          },
        ],
      },
      {
        titulo: "¿No es en una parcela?",
        pista: "Si has tratado una nave, dilo aquí",
        botones: [
          {
            etiqueta: "En una nave o un almacén",
            accion: "tipo-tratamiento",
            datos: { tipo: "instalaciones" },
            clase: "boton-claro",
          },
        ],
      },
    ],
    ...cambios,
  };
}

async function htmlDeLaLista(cambios = {}) {
  const { ListaParaElegir } = await import(
    `../web/react/piezas/lista_para_elegir.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(ListaParaElegir, listaDePrueba(cambios)),
  );
}

/** Los botones del HTML con sus `data-*` completos, que es lo que lee `app.js`. */
function botonesConDatos(html) {
  return [...html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)].map((encontrado) => {
    const atributos = {};
    for (const dato of encontrado[1].matchAll(/(data-[a-z-]+)="([^"]*)"/g)) {
      atributos[dato[1]] = dato[2];
    }
    const etiqueta = /<span class="texto">\s*<span>([\s\S]*?)<\/span>/.exec(encontrado[2]);
    // Los botones sencillos (los atajos de «HOY» y «AYER») no llevan el bloque `.texto` de los demás:
    // su texto va suelto dentro del botón, y hay que saber leerlo igual.
    const suelto = /^\s*([^<]+?)\s*$/.exec(encontrado[2]);
    return {
      ...atributos,
      clases: (/class="([^"]*)"/.exec(encontrado[1]) || ["", ""])[1].split(" ").filter(Boolean),
      etiqueta: etiqueta ? etiqueta[1] : suelto ? suelto[1] : "",
    };
  });
}

test("la lista saca sus botones con el texto, el icono y los datos que lee la aplicación", async () => {
  const botones = botonesConDatos(await htmlDeLaLista());
  assert.equal(botones.length, 3, `salen ${botones.length} botones y tienen que salir 3`);

  const tierras = botones.filter((boton) => boton["data-campo"] === "parcela_id");
  assert.equal(tierras.length, 2, "no salen las dos tierras");
  assert.equal(tierras[0]["data-accion"], "elegir", "la tierra no lleva la acción de elegir");
  assert.equal(tierras[0].etiqueta, "El Prado");
  assert.equal(tierras[0]["data-valor"], "1");
  // La superficie viaja con el botón: al elegir la tierra se apunta su superficie, que es lo normal
  // (casi siempre se trata la tierra entera). Sin este dato, el apunte saldría sin hectáreas.
  assert.equal(tierras[0]["data-superficie"], "2.43");

  // Y la salida de «no es una parcela» lleva su propia acción, que es la que cambia el tipo de sitio.
  const salida = botones.find((boton) => boton["data-accion"] === "tipo-tratamiento");
  assert.ok(salida, "no sale la salida de «no es una parcela»");
  assert.equal(salida["data-tipo"], "instalaciones");
});

test("la tierra que ya estaba elegida sale marcada", async () => {
  const botones = botonesConDatos(await htmlDeLaLista());
  const marcados = botones.filter((boton) => boton.clases.includes("boton-elegido"));
  assert.equal(marcados.length, 1, `hay ${marcados.length} botones marcados y solo puede haber 1`);
  assert.equal(marcados[0].etiqueta, "El Prado");
  // Y los demás son botones claros: si todos salieran marcados, el agricultor no sabría qué eligió.
  assert.ok(
    botones.filter((boton) => boton.clases.includes("boton-claro")).length === 2,
    "los que no están elegidos no son botones claros",
  );
});

test("cada bloque sale con su título y su pista, y sin título no deja un hueco", async () => {
  const html = await htmlDeLaLista();
  assert.match(html, /<h2>¿No es en una parcela\?<\/h2>/);
  assert.match(html, /<p class="pista-campo">Si has tratado una nave, dilo aquí<\/p>/);
  // El primer bloque no lleva ni título ni pista, y no puede salir un `<h2>` vacío en su lugar.
  assert.doesNotMatch(html, /<h2><\/h2>/, "sale un título vacío");
  assert.equal((html.match(/<h2>/g) || []).length, 1, "sale un título de más");
});

test("sin tierras, el aviso sale con el botón que lo arregla", async () => {
  // **Esto no es un adorno**: un aviso solo («todavía no tienes parcelas») deja al agricultor
  // encerrado, porque le dice que añada una y no le da dónde.
  const html = await htmlDeLaLista({
    bloques: [],
    aviso: {
      texto: "Todavía no tienes parcelas. Añade la primera.",
      boton: {
        etiqueta: "AÑADIR MI PRIMERA PARCELA",
        icono: "📍",
        accion: "anadir-maestro",
        datos: { tipo: "parcela" },
        clase: "boton-principal",
      },
    },
  });
  assert.match(html, /class="aviso"/);
  assert.match(html, /Todavía no tienes parcelas/);
  const botones = botonesConDatos(html);
  assert.equal(botones.length, 1, "el aviso no viene con su botón");
  assert.equal(botones[0]["data-accion"], "anadir-maestro");
  assert.equal(botones[0]["data-tipo"], "parcela");
  assert.ok(botones[0].clases.includes("boton-principal"), "el botón que lo arregla no es el grande");
  assert.equal(botones[0].etiqueta, "AÑADIR MI PRIMERA PARCELA");
});

test("con aviso no se enseñan los bloques: no hay nada que elegir", async () => {
  // Si salieran las dos cosas, el agricultor vería una lista vacía debajo del aviso.
  const html = await htmlDeLaLista({
    aviso: { texto: "Todavía no tienes parcelas. Añade la primera.", boton: null },
  });
  assert.doesNotMatch(html, /data-accion="elegir"/, "con aviso sigue saliendo la lista");
  assert.doesNotMatch(html, /data-accion="tipo-tratamiento"/, "con aviso sigue saliendo la salida");
});

test("la lista de elegir no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLaLista({
    aviso: null,
  });
  const delServidor = new Set([
    "El Prado",
    "2,43 ha · secano",
    "La Vega",
    "5,00 ha · regadío",
    "¿No es en una parcela?",
    "Si has tratado una nave, dilo aquí",
    "En una nave o un almacén",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
  // Y el aviso, cuando lo hay, también viene del servidor.
  const conAviso = await htmlDeLaLista({
    bloques: [],
    aviso: { texto: "Todavía no tienes parcelas.", boton: null },
  });
  for (const frase of frasesVisibles(conAviso)) {
    assert.equal(frase, "Todavía no tienes parcelas.", `frase escrita a mano: «${frase}»`);
  }
});

test("la lista puede llevar su ayuda debajo, que explica la pregunta entera", async () => {
  // Hay preguntas que se contestan eligiendo y necesitan su explicación debajo (el motivo por el que se
  // echó el producto, con qué máquina se aplicó). La ayuda va **después de los bloques**: explica la
  // pregunta entera, no uno de sus botones.
  const html = await htmlDeLaLista({ ayuda: AYUDA_DE_PRUEBA });
  assert.match(html, /class="ayuda-campo"/);
  assert.match(html, /<h3>¿Cuántas hectáreas has tratado\?<\/h3>/);
  // Y va la última: después de los botones, no antes.
  assert.ok(
    html.lastIndexOf("ayuda-campo") > html.lastIndexOf("data-accion"),
    "la ayuda sale antes que los botones",
  );
  // Sin ayuda no se dibuja nada de eso.
  assert.doesNotMatch(await htmlDeLaLista(), /ayuda-campo/);
});

test("el aviso puede llevar su explicación debajo", async () => {
  // Es para los avisos que dicen qué pasa **y qué se puede hacer igualmente** («el trabajo se apunta sin
  // máquina»), que es lo que evita que el agricultor crea que no puede seguir.
  const html = await htmlDeLaLista({
    bloques: [],
    aviso: { texto: "Todavía no has apuntado ninguna máquina.", pista: "El trabajo se apunta igual." },
  });
  assert.match(html, /<div class="aviso">Todavía no has apuntado ninguna máquina\.<\/div>/);
  assert.match(html, /<p class="pista-campo">El trabajo se apunta igual\.<\/p>/);
  assert.doesNotMatch(await htmlDeLaLista({ bloques: [], aviso: { texto: "Nada." } }), /pista-campo/);
});

// ---------------------------------------------------------------------------
// El campo y su ayuda: las piezas que hacen que el asistente pregunte escribiendo
//
// Son las que faltaban para poder migrar los pasos que **leen lo escrito** (la fecha, las hectáreas,
// la dosis, los kilos por hectárea). En `app.js` había tres funciones montando el mismo bloque
// (`pintaFecha`, `pintaNumero` y `pintaCamposMaestro`) y cada una se acordaba de cosas distintas.
//
// Lo que se comprueba aquí, y por qué cada cosa:
//
//  1. **El `id` del campo.** `app.js` lee lo escrito **por el `id`**; si cambia, el formulario se
//     rellena y se guarda vacío sin que salte ningún error. Es el peor fallo posible en esta pantalla.
//  2. **`inputmode="decimal"` en los números**: es lo que hace que en el móvil salga el teclado de
//     números con coma (aquí se escribe «2,43», no «2.43»).
//  3. **Los `data-*` de los atajos de la fecha** («HOY» y «AYER»): son los que hacen que apuntar lo de
//     hoy sean dos toques.
//  4. **El bloque de ayuda, con sus cuatro rótulos del servidor**, y que sin datos no se dibuje.
// ---------------------------------------------------------------------------

/** Los textos de un campo, como los manda el servidor. */
const AYUDA_DE_PRUEBA = {
  datos: {
    campo: "tratamiento.superficie_tratada_ha",
    titulo: "¿Cuántas hectáreas has tratado?",
    que_es: "La parte de la parcela que has tratado de verdad.",
    por_que: "Es lo que decide cuánto producto has gastado.",
    ejemplo: "Si has tratado media parcela de 2 hectáreas, pon 1.",
    si_falta: "Sin esto el cuaderno no cuadra con lo que has comprado.",
  },
  rotulos: {
    que_es: "Qué es:",
    por_que: "Para qué sirve:",
    ejemplo: "Un ejemplo:",
    si_falta: "Si no lo pones:",
  },
};

async function htmlDelCampo(cambios = {}) {
  const { Campo } = await import(`../web/react/piezas/campo.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(Campo, {
      id: "superficie_tratada_ha",
      etiqueta: "¿Cuántas hectáreas has tratado?",
      tipo: "numero",
      valor: "2,43",
      sufijo: "hectáreas",
      ayuda: AYUDA_DE_PRUEBA,
      ...cambios,
    }),
  );
}

test("un campo numérico lleva su id, su teclado de números y su pista", async () => {
  const html = await htmlDelCampo();
  // El `id` es lo único que tiene `app.js` para leer lo escrito: sin él, el campo se queda mudo.
  // `inputMode` se escribe así en el componente (es lo que React entiende) y el navegador lo deja en
  // el atributo `inputmode`, que es el que hace salir el teclado de números: por eso la comparación no
  // distingue mayúsculas, y por eso se comprueba también en un navegador de verdad.
  assert.match(
    html,
    /<input id="superficie_tratada_ha" type="text" inputMode="decimal" value="2,43"/i,
  );
  assert.match(html, /<label for="superficie_tratada_ha">¿Cuántas hectáreas has tratado\?<\/label>/);
  assert.match(html, /<p class="pista-campo">hectáreas<\/p>/);
  // Y va dentro de su bloque, como siempre: `.campo` es lo que le da el aire de la pantalla.
  assert.match(html, /<div class="campo">/);
});

test("un campo de fecha lleva su calendario y los dos atajos, con sus datos", async () => {
  const html = await htmlDelCampo({
    id: "fecha",
    etiqueta: "10/04/2026 — viernes, 10 de abril",
    tipo: "fecha",
    valor: "2026-04-10",
    sufijo: "",
    ayuda: null,
    botones: [
      { etiqueta: "HOY", accion: "fecha-rapida", datos: { campo: "fecha", valor: "2026-04-10" } },
      { etiqueta: "AYER", accion: "fecha-rapida", datos: { campo: "fecha", valor: "2026-04-09" } },
    ],
  });
  // El calendario del navegador, sin `inputmode`: en un móvil, el teclado de números tapa el calendario.
  assert.match(html, /<input id="fecha" type="date" value="2026-04-10"/);
  assert.doesNotMatch(html, /inputmode/, "la fecha lleva teclado de números y tapa el calendario");

  const botones = botonesConDatos(html);
  assert.equal(botones.length, 2, `salen ${botones.length} atajos y tienen que salir 2`);
  // El campo va en el botón porque un análisis tiene DOS fechas: «hoy» tiene que saber a cuál se refiere.
  assert.equal(botones[0]["data-accion"], "fecha-rapida");
  assert.equal(botones[0]["data-campo"], "fecha");
  assert.equal(botones[0]["data-valor"], "2026-04-10");
  assert.equal(botones[0].etiqueta, "HOY");
  assert.equal(botones[1]["data-valor"], "2026-04-09");
  assert.equal(botones[1].etiqueta, "AYER");
  // Son atajos, no caminos: no llevan icono ni flecha, como los tenía la interfaz de siempre.
  assert.doesNotMatch(html, /class="flecha"/, "los atajos llevan flecha y parecen un camino");
});

test("un campo de texto largo sale como área de escribir, con su id", async () => {
  const html = await htmlDelCampo({
    id: "observaciones",
    etiqueta: "¿Algo más que apuntar?",
    tipo: "area",
    valor: "Se dejó sin tratar la esquina del pozo",
    sufijo: "",
    ayuda: null,
  });
  assert.match(html, /<textarea id="observaciones">Se dejó sin tratar la esquina del pozo<\/textarea>/);
});

test("la ayuda de un campo sale con sus cuatro rótulos, y sin datos no se dibuja", async () => {
  const conAyuda = await htmlDelCampo();
  assert.match(conAyuda, /<div class="ayuda-campo">/);
  assert.match(conAyuda, /<h3>¿Cuántas hectáreas has tratado\?<\/h3>/);
  // Los cuatro rótulos, cada uno con su dato: son los que explican el campo a quien no sabe de normativa.
  for (const rotulo of ["Qué es:", "Para qué sirve:", "Un ejemplo:", "Si no lo pones:"]) {
    assert.match(conAyuda, new RegExp(`<span class="etiqueta-dato">${rotulo}</span>`), `falta «${rotulo}»`);
  }
  assert.match(conAyuda, /La parte de la parcela que has tratado de verdad\./);
  assert.match(conAyuda, /Sin esto el cuaderno no cuadra con lo que has comprado\./);

  // **Sin ayuda no se dibuja el bloque**: un hueco con cuatro rótulos y nada dentro es peor que nada.
  const sinAyuda = await htmlDelCampo({ ayuda: null });
  assert.doesNotMatch(sinAyuda, /ayuda-campo/);
  assert.doesNotMatch(sinAyuda, /etiqueta-dato/);
});

test("la ayuda sola, sin datos, no dibuja nada", async () => {
  const { AyudaDeUnCampo } = await import(
    `../web/react/piezas/ayuda_de_un_campo.js?prueba=${Math.random()}`
  );
  const vacia = globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(AyudaDeUnCampo, { datos: null, rotulos: AYUDA_DE_PRUEBA.rotulos }),
  );
  assert.equal(vacia, "", `sin datos ha dibujado algo: ${vacia}`);
});

test("un campo sin etiqueta no pinta el `<label>`", async () => {
  // Hay pasos en los que la pregunta ya es el título de la pantalla (las observaciones de un apunte, los
  // detalles de una labor): una etiqueta vacía solo estorba —un lector de pantalla lee un campo sin
  // nombre—. El campo sigue llevando su `id`, que es lo que importa.
  const html = await htmlDelCampo({
    id: "observaciones",
    etiqueta: "",
    tipo: "area",
    valor: "Sin tratar la esquina del pozo",
    sufijo: "",
    ayuda: null,
  });
  assert.doesNotMatch(html, /<label/, `ha pintado una etiqueta vacía: ${html}`);
  assert.match(html, /<textarea id="observaciones">Sin tratar la esquina del pozo<\/textarea>/);
});

test("el campo sabe pedir un número entero, con ejemplo y sin historial", async () => {
  // Es lo que necesitan las horas del tratamiento: el teclado de números **sin coma** (en una hora la
  // coma no pinta nada), un ejemplo dentro de la casilla («07:30») y sin el historial del navegador, que
  // tapa media pantalla en el móvil.
  const html = await htmlDelCampo({
    id: "hora_inicio",
    etiqueta: "¿A qué hora empezaste?",
    tipo: "entero",
    valor: "",
    sufijo: "",
    ayuda: null,
    placeholder: "07:30",
    autocompletar: "off",
  });
  assert.match(html, /<input id="hora_inicio" type="text" inputMode="numeric"/i);
  assert.match(html, /placeholder="07:30"/);
  assert.match(html, /autoComplete="off"/i);
  assert.match(html, /value=""/);
});

test("el área de escribir dice de qué alto sale", async () => {
  const html = await htmlDelCampo({
    id: "incidencias",
    etiqueta: "¿Pasó algo raro?",
    tipo: "area",
    valor: "",
    sufijo: "Cuéntalo con tus palabras",
    ayuda: null,
    filas: 2,
  });
  assert.match(html, /<textarea id="incidencias" rows="2"/);
  assert.match(html, /<p class="pista-campo">Cuéntalo con tus palabras<\/p>/);
});

test("la ayuda puede ir encima del campo, cuando es la introducción de la pantalla", async () => {
  // El primer campo de «cómo se echó» el producto la lleva encima: esa explicación se lee **antes** de
  // empezar a escribir, y es lo que hacía la interfaz de siempre.
  const html = await htmlDelCampo({ ayudaAntes: true });
  const posicionAyuda = html.indexOf("ayuda-campo");
  const posicionCampo = html.indexOf("<input");
  assert.ok(posicionAyuda > 0, "no ha pintado la ayuda");
  assert.ok(
    posicionAyuda < posicionCampo,
    `la ayuda sale después del campo: ${html.slice(0, 200)}`,
  );
  // Y por defecto va debajo, que es lo normal en todos los demás campos.
  const normal = await htmlDelCampo();
  assert.ok(normal.indexOf("ayuda-campo") > normal.indexOf("<input"), "la ayuda sale encima sin pedirlo");
});

test("un bloque del maestro puede llevar su título, para las pantallas con secciones", async () => {
  // «Cómo se echó» son varias secciones seguidas (la hora, el estado del cultivo, cómo estaba el día) y
  // cada una lleva su encabezado. En las fichas del maestro no se usa: allí el título es el del paso.
  const html = await htmlDeLosCampos({
    bloques: [
      {
        tipo: "texto",
        id: "estado_cultivo",
        etiqueta: "",
        valor: "",
        titulo: "¿Cómo estaba la planta?",
        pista: "Con tus palabras",
      },
    ],
  });
  assert.match(html, /<h2>¿Cómo estaba la planta\?<\/h2>/);
  // Y el campo va sin etiqueta, porque la pregunta es el título: no se repite dos veces.
  assert.doesNotMatch(html, /<label/, "pinta una etiqueta y el título: la pregunta sale dos veces");
});

test("el campo ni la ayuda llevan una frase escrita a mano", async () => {
  const html = await htmlDelCampo();
  const delServidor = new Set([
    ...todosLosTextos(AYUDA_DE_PRUEBA),
    "¿Cuántas hectáreas has tratado?",
    "hectáreas",
    "2,43",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
  // Y los atajos de la fecha, que son texto del servidor como todo lo demás.
  const conFecha = await htmlDelCampo({
    id: "fecha",
    tipo: "fecha",
    etiqueta: "10/04/2026 — viernes, 10 de abril",
    valor: "2026-04-10",
    sufijo: "",
    ayuda: null,
    botones: [{ etiqueta: "HOY", accion: "fecha-rapida", datos: { campo: "fecha", valor: "2026-04-10" } }],
  });
  const permitidas = new Set([...delServidor, "HOY", "10/04/2026 — viernes, 10 de abril", "2026-04-10"]);
  for (const frase of frasesVisibles(conFecha)) {
    assert.ok(permitidas.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// El grupo de campos del maestro: los datos de una ficha, varios a la vez
//
// Casi todos los pasos del asistente que no son una lista son varios datos seguidos: la ficha de un
// producto, la de una máquina, la de un asesor, los números del plan. Cada dato se pinta como un campo,
// **menos los que se contestan eligiendo**, que llevan sus botones dentro del mismo bloque (un sí o un
// no, la unidad, el tipo de carné). Lo que se comprueba aquí:
//
//  1. **El `id` de cada campo de escribir**, que es lo único que tiene `app.js` para leerlo.
//  2. **Los `data-campo` y `data-valor` de los botones de elegir**, y que el elegido salga marcado: es
//     como el agricultor sabe qué contestó cuando vuelve atrás.
//  3. Que un bloque **sin `tipo`** no se pinte, que es la señal de que `app.js` no lo ha sabido
//     preparar: mejor un hueco visible que un campo guardándose en el sitio que no es.
// ---------------------------------------------------------------------------

/** Un grupo de bloques de prueba: tres de escribir (uno con ayuda) y uno de elegir. */
function bloquesDePrueba(cambios = {}) {
  return {
    bloques: [
      {
        tipo: "texto",
        id: "nombre_comercial",
        etiqueta: "¿Cómo se llama el producto?",
        valor: "Ejemplo 25 EC",
        pista: "El nombre que viene en la etiqueta",
        ayuda: null,
      },
      {
        tipo: "numero",
        id: "dosis_maxima",
        etiqueta: "¿Cuánto se puede echar como mucho?",
        valor: "0,8",
        pista: "L/ha",
        ayuda: AYUDA_DE_PRUEBA,
      },
      {
        tipo: "fecha",
        id: "fecha_caducidad",
        etiqueta: "¿Hasta cuándo vale?",
        valor: "2028-06-30",
        pista: "",
        ayuda: null,
      },
      {
        tipo: "opciones",
        campo: "unidad_dosis",
        etiqueta: "¿En qué se mide?",
        pista: "Como venga en la etiqueta",
        ayuda: null,
        opciones: [
          { etiqueta: "L/ha", valor: "L/ha", elegido: true },
          { etiqueta: "kg/ha", valor: "kg/ha", elegido: false },
        ],
      },
    ],
    ...cambios,
  };
}

async function htmlDeLosCampos(cambios = {}) {
  const { CamposDelMaestro } = await import(
    `../web/react/piezas/campos_del_maestro.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(CamposDelMaestro, bloquesDePrueba(cambios)),
  );
}

test("los campos del maestro salen con su id, su tipo y su valor", async () => {
  const html = await htmlDeLosCampos();
  assert.match(html, /<input id="nombre_comercial" type="text" value="Ejemplo 25 EC"/);
  // El número con su teclado (para que salga la coma en el móvil) y la fecha con su calendario.
  assert.match(html, /<input id="dosis_maxima" type="text" inputMode="decimal" value="0,8"/i);
  assert.match(html, /<input id="fecha_caducidad" type="date" value="2028-06-30"/);
  assert.match(html, /<label for="nombre_comercial">¿Cómo se llama el producto\?<\/label>/);
  assert.match(html, /<p class="pista-campo">El nombre que viene en la etiqueta<\/p>/);
});

test("un dato que se contesta eligiendo lleva sus botones, con el campo y el valor", async () => {
  const html = await htmlDeLosCampos();
  const botones = botonesConDatos(html).filter((boton) => boton["data-accion"] === "elegir");
  assert.equal(botones.length, 2, `salen ${botones.length} botones y tienen que salir 2`);
  // El campo va en cada botón porque es lo que lee el manejador de clics de `app.js`: sin él, el
  // agricultor toca y no se apunta nada.
  assert.equal(botones[0]["data-campo"], "unidad_dosis");
  assert.equal(botones[0]["data-valor"], "L/ha");
  assert.equal(botones[1]["data-valor"], "kg/ha");
  // El que ya estaba elegido va marcado, y el otro no: es como se sabe qué se contestó.
  assert.ok(botones[0].clases.includes("boton-elegido"), "el elegido no sale marcado");
  assert.ok(botones[1].clases.includes("boton-claro"), "el que no se eligió sale como elegido");
  // La etiqueta de un bloque de elegir **no lleva `for`**: no apunta a ninguna casilla, porque la
  // casilla son los botones. Con un `for` suelto, un lector de pantalla buscaría un campo que no existe.
  assert.match(html, /<label>¿En qué se mide\?<\/label>/);
});

test("la ayuda va con el dato que la tiene, y solo con ese", async () => {
  const html = await htmlDeLosCampos();
  // Solo el bloque de la dosis lleva ayuda en esta prueba.
  assert.equal(
    (html.match(/class="ayuda-campo"/g) || []).length,
    1,
    "la ayuda sale en el sitio que no es",
  );
  assert.match(html, /<h3>¿Cuántas hectáreas has tratado\?<\/h3>/);
});

test("un bloque con un tipo que no se conoce se pinta como texto, en vez de desaparecer", async () => {
  // Un bloque con un `tipo` raro significa que `app.js` no ha sabido prepararlo. Se pinta como texto
  // (que es lo que hacía la interfaz de siempre) **a propósito**: entre un campo de más, que el
  // agricultor puede rellenar y se guarda en su sitio, y un campo que desaparece sin decir nada, el de
  // más. Un campo que no se pinta es un dato que se pierde sin que nadie se entere.
  const html = await htmlDeLosCampos({
    bloques: [{ tipo: "casillas", id: "un_dato_raro", etiqueta: "Esto se pinta igual", valor: "x" }],
  });
  assert.match(html, /<input id="un_dato_raro" type="text" value="x"/);
  assert.match(html, /<label for="un_dato_raro">Esto se pinta igual<\/label>/);
});

test("los campos del maestro no llevan ni una frase escrita a mano", async () => {
  const html = await htmlDeLosCampos();
  const delServidor = new Set([
    ...todosLosTextos(AYUDA_DE_PRUEBA),
    "¿Cómo se llama el producto?",
    "El nombre que viene en la etiqueta",
    "Ejemplo 25 EC",
    "¿Cuánto se puede echar como mucho?",
    "0,8",
    "L/ha",
    "kg/ha",
    "¿Hasta cuándo vale?",
    "2028-06-30",
    "¿En qué se mide?",
    "Como venga en la etiqueta",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// La confirmación: la pantalla que sale después de guardar algo
//
// Cinco pantallas de confirmación (venta, análisis, plan, medidas y ficha de un maestro) y tres que
// ofrecen un camino (traer la tierra del SIGPAC, el listado de papeles y las tierras traídas) son la misma
// forma: un título, la explicación de **para qué sirve** lo que se ha guardado, y sus botones. Estaban
// escritas a mano cinco veces en `app.js`.
//
// Lo que se comprueba aquí: que los botones llevan su acción y sus datos (los lee el manejador de clics),
// que los sencillos salen **sin flecha** (como estaban) y que la ayuda dice para qué sirve, que es lo que
// hace que el agricultor entienda que apuntar eso le vale para algo.
// ---------------------------------------------------------------------------

/** Una confirmación de prueba, con todo lo que puede llevar. */
function datosDeLaConfirmacion(cambios = {}) {
  return {
    titulo: "Apuntado",
    pista: "Se ha guardado en tu cuaderno.",
    ayuda: { titulo: "Dónde se usa:", texto: "Cuando la Junta te pregunte qué has vendido." },
    avisos: [{ texto: "Se han guardado 3 medidas." }],
    listas: [
      {
        titulo: "Estas no han entrado",
        pista: "Míralas y vuelve a probar",
        elementos: [{ cabecera: "37-70-0-0-503-51-1", detalle: "La referencia no existe" }],
      },
    ],
    archivo: { titulo: "¿Tienes el boletín a mano?", pista: "Puedes subirlo ahora", id: "informe-7" },
    acciones: [
      { etiqueta: "VER MIS VENTAS", accion: "ventas-ver", clase: "boton", sencillo: true },
      { etiqueta: "IR AL MAPA", icono: "🗺️", accion: "mapa-abrir", clase: "boton-principal" },
    ],
    ...cambios,
  };
}

async function htmlDeLaConfirmacion(cambios = {}) {
  const { Confirmacion } = await import(
    `../web/react/piezas/confirmacion.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(Confirmacion, datosDeLaConfirmacion(cambios)),
  );
}

test("la confirmación sale con su título, su pista y la ayuda de para qué sirve", async () => {
  const html = await htmlDeLaConfirmacion();
  assert.match(html, /<h1>Apuntado<\/h1>/);
  assert.match(html, /<p class="pista">Se ha guardado en tu cuaderno\.<\/p>/);
  // La ayuda dice para qué sirve lo que se acaba de guardar: sin ella, el agricultor no sabe qué gana
  // apuntando esto.
  assert.match(html, /<div class="ayuda-campo">/);
  assert.match(html, /<p><strong>Dónde se usa:<\/strong><\/p>/);
  assert.match(html, /<p>Cuando la Junta te pregunte qué has vendido\.<\/p>/);
  // Y todo eso es opcional: sin ayuda ni pista no se pinta nada de eso (no queda un hueco vacío).
  const sinAyuda = await htmlDeLaConfirmacion({ ayuda: null, pista: "" });
  assert.doesNotMatch(sinAyuda, /ayuda-campo/);
  assert.doesNotMatch(sinAyuda, /class="pista"/);
});

test("los botones de la confirmación llevan su acción, y los sencillos sin flecha", async () => {
  const html = await htmlDeLaConfirmacion();
  const botones = botonesConDatos(html);
  assert.equal(botones.length, 2, `salen ${botones.length} botones y tienen que salir 2`);
  // Los que se preparan con datos (`sencillo`) salen sin flecha, como estaban en estas pantallas.
  assert.equal(botones[0]["data-accion"], "ventas-ver");
  assert.ok(botones[0].clases.includes("boton"), "no es un botón de la casa");
  assert.doesNotMatch(html.slice(0, html.indexOf("mapa-abrir")), /class="flecha"/, "el sencillo lleva flecha");
  // Y el que lleva icono sale con el botón de casa, con su flecha (es un camino, no un atajo). El icono
  // es un **dibujo** desde el rediseño (ronda 76): el cuadro lleva su clave en `data-icono` y dentro va
  // el `<svg>`. 🗺️ todavía no tiene dibujo, así que sale el emoji de siempre: se comprueban las dos cosas.
  assert.equal(botones[1]["data-accion"], "mapa-abrir");
  assert.match(html, /<span class="icono" aria-hidden="true" data-icono="🗺️">/);
  const mapa = botonesDe(html).find((boton) => boton.accion === "mapa-abrir");
  assert.ok(mapa && mapa.dibujo.includes("🗺️"), "el cuadro del icono no lleva su clave");
  assert.match(html, /class="flecha" aria-hidden="true">→<\/span>/);
});

test("el aviso de la confirmación sale con su texto, y en rojo si es un error", async () => {
  const html = await htmlDeLaConfirmacion();
  assert.match(html, /<div class="aviso"><p>Se han guardado 3 medidas\.<\/p><\/div>/);
  // Un error sale con `role="alert"`, que es lo que hace que un lector de pantalla lo lea en voz alta.
  const conError = await htmlDeLaConfirmacion({ avisos: [{ texto: "No se ha podido", error: true }] });
  assert.match(conError, /<div class="aviso aviso-error" role="alert">No se ha podido<\/div>/);
  assert.doesNotMatch(await htmlDeLaConfirmacion({ avisos: [] }), /class="aviso"/);
});

test("las listas de la confirmación salen con su cabecera y su detalle", async () => {
  const html = await htmlDeLaConfirmacion();
  assert.match(html, /<h2>Estas no han entrado<\/h2>/);
  assert.match(html, /<p class="pista-campo">Míralas y vuelve a probar<\/p>/);
  assert.match(html, /<ul class="lista">/);
  assert.match(html, /<div class="apunte-cabecera"><span>37-70-0-0-503-51-1<\/span><\/div>/);
  assert.match(html, /<div class="apunte-detalle">La referencia no existe<\/div>/);
  assert.doesNotMatch(await htmlDeLaConfirmacion({ listas: [] }), /class="lista"/);
});

test("el bloque de subir un fichero sale con su id, que es lo que lee la aplicación", async () => {
  const html = await htmlDeLaConfirmacion();
  assert.match(html, /<h2>¿Tienes el boletín a mano\?<\/h2>/);
  assert.match(html, /<p class="pista-campo">Puedes subirlo ahora<\/p>/);
  // El `id` es el de siempre (`informe-<id>`): `app.js` lee el fichero por ahí.
  assert.match(html, /<input type="file" id="informe-7" accept="application\/pdf,image\/\*"\/>/);
  assert.doesNotMatch(await htmlDeLaConfirmacion({ archivo: null }), /type="file"/);
});

test("la confirmación no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLaConfirmacion();
  const delServidor = new Set([
    "Apuntado",
    "Se ha guardado en tu cuaderno.",
    "Dónde se usa:",
    "Cuando la Junta te pregunte qué has vendido.",
    "Se han guardado 3 medidas.",
    "Estas no han entrado",
    "Míralas y vuelve a probar",
    "37-70-0-0-503-51-1",
    "La referencia no existe",
    "¿Tienes el boletín a mano?",
    "Puedes subirlo ahora",
    "VER MIS VENTAS",
    "IR AL MAPA",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// Traer la tierra del SIGPAC: la pantalla que busca el recinto oficial
//
// Es la pantalla que ahorra más trabajo de todas (con 54 líneas, teclear cada tierra es la diferencia
// entre empezar y no empezar) y va **dentro** del asistente de dar de alta una tierra. Se migró como
// pantalla y no con las piezas del asistente porque tiene cosas que no tiene ningún paso: un desplegable,
// listas de `li` y el detalle de cada recinto.
//
// Lo que se comprueba aquí: que los `id` de los campos son los de siempre (es lo único que tiene `app.js`
// para leerlos: si cambia uno, el formulario se rellena y se guarda vacío), que las acciones de los
// botones son las de siempre (las lee el manejador de clics), que las provincias salen en el desplegable
// con la suya elegida y que los recintos llevan su referencia y su dibujo de marcado.
// ---------------------------------------------------------------------------

const TEXTOS_DEL_SIGPAC = {
  sigpac: {
    explica: "Pega lo que tengas: la del visor del SIGPAC, los siete números del papel o la referencia catastral.",
    provincia_parcela: "¿En qué provincia está esta parcela?",
    poligono: "El polígono",
    parcela: "El número de la parcela",
    o_pega_la_referencia: "Y si tienes la referencia a mano, pégala aquí y no hace falta rellenar nada más:",
    // Los dos caminos, cada uno con su nombre (ronda 90, del diseño de Stitch).
    camino_rapido: "El camino rápido",
    o_por_partes: "O si lo prefieres: buscar por partes",
    referencia_como_sea: "La referencia de tu trozo",
    referencia_ejemplo: "37-22-0-0-501-427-1",
    referencia_como_sea_pista: "Pega lo que tengas.",
    alias: "¿Cómo llamas tú a esa tierra?",
    sistema: "¿Es de secano o de regadío?",
    buscar: "BUSCAR MIS TROZOS",
    buscar_titulo: "Los trozos que hay en esa parcela",
    buscar_explica: "Marca los que sean tuyos.",
    traer_los_marcados: "TRAERME LOS MARCADOS",
    recinto_numero: "Trozo {numero}",
  },
  municipios: {
    elegir: "¿En qué pueblo está?",
    pista: "Escribe las primeras letras y elígelo de la lista",
    buscar: "BUSCAR EL PUEBLO",
    cualquiera: "Todas las provincias",
  },
};

/** Los datos del SIGPAC, ya preparados como los manda `app.js`. */
function datosDelSigpac(cambios = {}) {
  return {
    textos: TEXTOS_DEL_SIGPAC,
    datos: {
      provincias: [
        { valor: "Salamanca", etiqueta: "Salamanca", elegido: true },
        { valor: "Zamora", etiqueta: "Zamora", elegido: false },
      ],
      municipio: "Calvarrasa de Arriba",
      pueblos: [
        {
          etiqueta: "Calvarrasa de Arriba (Salamanca)",
          pista: "Código 37070",
          nombre: "Calvarrasa de Arriba",
          provincia: "Salamanca",
          elegido: true,
        },
      ],
      poligono: "503",
      parcela: "51",
      ref_sigpac: "",
      alias: "El llano",
      sistemas: [
        { valor: "secano", etiqueta: "Secano", elegido: true },
        { valor: "regadio", etiqueta: "Regadío", elegido: false },
      ],
      trozos: [
        {
          etiqueta: "Trozo 1",
          pista: "4,9016 ha · TA — TIERRAS ARABLES · Pendiente 1,00 % · Altitud 837 m",
          referencia: "37-70-0-0-503-51-1",
          marcado: true,
        },
      ],
      ...cambios,
    },
  };
}

async function htmlDelSigpac(cambios = {}) {
  const { PantallaTraerDelSigpac } = await import(
    `../web/react/pantallas/traer_del_sigpac.js?prueba=${Math.random()}`
  );
  const propiedades = datosDelSigpac();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaTraerDelSigpac, {
      textos: propiedades.textos,
      datos: { ...propiedades.datos, ...cambios },
    }),
  );
}

test("la pantalla del SIGPAC sale con sus campos, con el id de siempre", async () => {
  const html = await htmlDelSigpac();
  // Los `id` son lo único que tiene `app.js` para leer lo que se escribe (`recogeElSigpac`).
  for (const id of ["municipio_sigpac", "poligono_sigpac", "parcela_sigpac", "ref_sigpac", "alias_sigpac"]) {
    assert.ok(html.includes(`id="${id}"`), `falta el campo «${id}»`);
  }
  // El desplegable de provincias, con la suya elegida y la opción de «todas».
  assert.match(html, /<select id="provincia_sigpac">/);
  assert.match(html, /<option value="">Todas las provincias<\/option>/);
  assert.match(html, /<option value="Salamanca" selected="">/);
  // El ejemplo de la referencia va dentro de la casilla, que es lo que hace que se entienda qué pegar.
  assert.match(html, /placeholder="37-22-0-0-501-427-1"/);
  // Y el valor que ya había escrito vuelve puesto (el pueblo elegido, la parcela, el alias).
  assert.match(html, /id="municipio_sigpac"[^>]*value="Calvarrasa de Arriba"/);
  assert.match(html, /id="poligono_sigpac"[^>]*value="503"/);
});

test("el camino rápido (pegar la referencia) va antes que los seis campos", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): pegar la referencia ahorra teclear seis datos, y estaba
  // **abajo del todo**, después de los seis campos que ahorra. Ahora se lee el camino corto antes que el
  // largo, y los seis datos del camino largo van numerados (el número lo pone el CSS con un contador).
  const html = await htmlDelSigpac();
  assert.match(html, /<h2>El camino rápido<\/h2>/);
  assert.match(html, /<h2>O si lo prefieres: buscar por partes<\/h2>/);
  assert.ok(
    html.indexOf("El camino rápido") < html.indexOf("O si lo prefieres"),
    "el camino rápido sale después del largo",
  );
  assert.ok(
    html.indexOf('id="ref_sigpac"') < html.indexOf('id="poligono_sigpac"'),
    "la referencia sigue estando después de los campos que ahorra",
  );
  assert.match(html, /<ol class="campos-numerados">/);
  assert.equal(
    (html.match(/<li><div class="campo">|<li><div class="campo"/g) || []).length,
    6,
    "los seis datos del camino largo no van numerados",
  );
});

test("el desplegable de provincias sale como desplegable, no como una lista de botones", async () => {
  // Es lo que hace que en el móvil salga la rueda del sistema, que es más rápida que buscar entre
  // doscientos botones.
  const html = await htmlDelSigpac();
  assert.match(html, /<select id="provincia_sigpac">/);
  assert.match(html, /<option value="Zamora">Zamora<\/option>/);
  assert.doesNotMatch(html, /data-campo="provincia"/, "la provincia sale como botones");
});

test("los pueblos buscados salen como lista, con su código oficial", async () => {
  const html = await htmlDelSigpac();
  const botones = botonesConDatos(html).filter((boton) => boton["data-accion"] === "elegir-pueblo");
  assert.equal(botones.length, 1, `salen ${botones.length} pueblos y tiene que salir 1`);
  assert.equal(botones[0]["data-nombre"], "Calvarrasa de Arriba");
  assert.equal(botones[0]["data-provincia"], "Salamanca");
  // El código oficial (el del INE) es lo que se queda el programa al elegir el pueblo: sin él no se
  // puede preguntar al SIGPAC.
  assert.match(html, /Código 37070/);
  assert.match(html, /Calvarrasa de Arriba \(Salamanca\)/);
});

test("los recintos salen con su referencia, su detalle y el marcado", async () => {
  const html = await htmlDelSigpac();
  const trozos = botonesConDatos(html).filter((boton) => boton["data-accion"] === "marcar-trozo");
  assert.equal(trozos.length, 1, `salen ${trozos.length} recintos y tiene que salir 1`);
  assert.equal(trozos[0]["data-referencia"], "37-70-0-0-503-51-1");
  assert.ok(trozos[0].clases.includes("boton-elegido"), "el recinto marcado no sale marcado");
  // El detalle lo monta `app.js`: aquí solo se comprueba que llega tal cual.
  assert.match(html, /4,9016 ha · TA — TIERRAS ARABLES/);
  // Y la referencia se ve escrita debajo, para poder comprobarla contra el papel.
  assert.match(html, /<div class="apunte-detalle">37-70-0-0-503-51-1<\/div>/);
  // Sin recintos, la sección de los trozos no se dibuja: un botón que no lleva a nada estorba.
  const sinTrozos = await htmlDelSigpac({ trozos: [] });
  assert.doesNotMatch(sinTrozos, /TRAERME LOS MARCADOS/);
  assert.doesNotMatch(sinTrozos, /Los trozos que hay en esa parcela/);
  // (La lista de pueblos sí sigue: es otra lista, la de los pueblos que ha traído la búsqueda.)
  assert.match(sinTrozos, /class="lista"/);
});

test("los dos sistemas salen con sus botones y el elegido marcado", async () => {
  const html = await htmlDelSigpac();
  const sistemas = botonesConDatos(html).filter((boton) => boton["data-campo"] === "sistema");
  assert.deepEqual(
    sistemas.map((boton) => boton["data-valor"]),
    ["secano", "regadio"],
    "no salen los dos sistemas",
  );
  assert.ok(sistemas[0].clases.includes("boton-elegido"), "el secano no sale elegido por defecto");
  assert.ok(sistemas[1].clases.includes("boton-claro"));
});

test("la pantalla del SIGPAC no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDelSigpac();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DEL_SIGPAC),
    // Lo que monta `app.js`: el pueblo con su provincia, el código, el detalle del recinto y los valores.
    "Calvarrasa de Arriba (Salamanca)",
    "Código 37070",
    "Salamanca",
    "Zamora",
    "Secano",
    "Regadío",
    "4,9016 ha · TA — TIERRAS ARABLES · Pendiente 1,00 % · Altitud 837 m",
    "Calvarrasa de Arriba",
    "503",
    "51",
    "El llano",
    "Trozo 1",
    "37-70-0-0-503-51-1",
    "37-22-0-0-501-427-1",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Traer tus tierras del cuaderno de la Junta»: 51 tierras de una vez, pero mirándolas antes
//
// Es la pantalla que ahorra más trabajo de todas (con 54 líneas, teclear cada tierra es la diferencia
// entre empezar y no empezar) y tiene **tres estados**: el formulario, el resumen de lo que trae el
// fichero y el resultado. Lo que se conserva a propósito y se comprueba aquí: que **leer no apunta
// nada** (el resumen va aparte del resultado), que **los números a cero no se enseñan** (menos
// «tierras nuevas», que sale siempre) y que el campo del fichero conserva su `id`.
// ---------------------------------------------------------------------------

/** Los textos del cuaderno de la Junta, copiados de `textos.py`. */
const TEXTOS_DEL_CUADERNO_JUNTA = {
  cuaderno_cyl: {
    titulo: "Traer mis tierras del cuaderno de la Junta",
    explica:
      "Si ya llevas el cuaderno en la web de la Junta, puedes traer tus tierras de ahí y no tener que apuntarlas una a una.",
    como_se_hace:
      "Entra en la web de la Junta con tu certificado, descarga el fichero CuadernoExplotacion y súbelo aquí.",
    que_fichero: "El fichero del cuaderno (CuadernoExplotacion.xlsx)",
    traer: "TRAER MIS TIERRAS",
    eligiendo: "Eligiendo el fichero…",
    resumen_titulo: "Esto es lo que trae tu cuaderno",
    resumen_campana: "Campaña",
    resumen_titular: "Titular",
    resumen_lineas: "Líneas",
    resumen_tierras: "Tierras distintas",
    resumen_hectareas: "Hectáreas que declaras",
    resumen_pueblos: "Pueblos",
    lineas_titulo: "Las tierras que se van a apuntar",
    confirmar: "SÍ, TRAER ESTAS TIERRAS",
    volver: "VOLVER",
    avisos_titulo: "Conviene que mires esto",
    hecho_titulo: "Tus tierras ya están apuntadas",
    ver_tierras: "VER MIS TIERRAS",
    otra_vez: "Si vuelves a leer el fichero, lo que ya está apuntado no se duplica.",
  },
  acciones: { volver: "VOLVER" },
};

const RESUMEN_DE_PRUEBA = {
  filas: [
    ["Campaña", "2026"],
    ["Titular", "EXPLOTACIÓN DE EJEMPLO"],
    ["Líneas", "54"],
    ["Tierras distintas", "51"],
    ["Hectáreas que declaras", "128,28"],
  ],
  lineas: [["99-99-0-0-1-1-1 · PUEBLO DE EJEMPLO", "TRIGO BLANDO · 4,90 ha"]],
  avisos: ["Hay 3 líneas que no dicen el polígono, así que no se pueden apuntar."],
};

const RESULTADO_DE_PRUEBA = {
  cuentas: ["Tierras nuevas: 7", "Con cultivo: 6", "Ya estaban: 44"],
  sin_apuntar: "Líneas que no se han podido apuntar: 1",
  titular: "Se han rellenado tus datos: nombre, NIF y municipio.",
  avisos: [],
};

async function htmlDelCuadernoDeLaJunta(cambios = {}) {
  const { PantallaCuadernoDeLaJunta } = await import(
    `../web/react/pantallas/cuaderno_de_la_junta.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaCuadernoDeLaJunta, {
      textos: structuredClone(TEXTOS_DEL_CUADERNO_JUNTA),
      ...cambios,
    }),
  );
}

test("el formulario pide el fichero, con su id, y explica de dónde se descarga", async () => {
  const html = await htmlDelCuadernoDeLaJunta();
  assert.match(html, /Traer mis tierras del cuaderno de la Junta/);
  // Hay que decir cómo se consigue el fichero: sin eso, el agricultor no sabe qué subir.
  assert.match(html, /con tu certificado/);
  assert.match(html, /CuadernoExplotacion/);
  assert.match(html, /<label for="cuaderno-fichero">El fichero del cuaderno/);
  assert.match(html, /<input id="cuaderno-fichero" type="file" accept="\.xlsx,\.xlsm"\/>/);
  assert.match(html, /data-accion="cuaderno-leer"/);
  assert.match(html, /data-accion="cuaderno-volver"/);
  // Y no se enseña ni resumen ni resultado: no hay nada que enseñar todavía.
  assert.doesNotMatch(html, /Esto es lo que trae tu cuaderno/);
  assert.doesNotMatch(html, /Tus tierras ya están apuntadas/);
});

test("la pantalla dice en qué de sus tres fases está", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): son **tres pantallas en una** y sin una señal de
  // dónde estás, la impresión es que no se acaba nunca. La barra es la misma del asistente (con su
  // `role="progressbar"`, que es lo que la hace legible para quien no la ve).
  const fichero = await htmlDelCuadernoDeLaJunta();
  assert.match(fichero, /<div class="pasos" role="progressbar" aria-valuenow="1" aria-valuemax="3">/);
  const resumen = await htmlDelCuadernoDeLaJunta({ resumen: RESUMEN_DE_PRUEBA });
  assert.match(resumen, /aria-valuenow="2"/);
  const resultado = await htmlDelCuadernoDeLaJunta({ resultado: RESULTADO_DE_PRUEBA });
  assert.match(resultado, /aria-valuenow="3"/);
  // Los tres tramos están siempre, y los hechos van marcados.
  assert.equal((resultado.match(/class="paso paso-hecho"/g) || []).length, 3, "la fase 3 no está llena");
  assert.equal((fichero.match(/class="paso paso-hecho"/g) || []).length, 1, "la fase 1 no va por el primero");
});

test("antes de subir el fichero se dice que leerlo no apunta nada", async () => {
  // Es la duda que tiene el agricultor con el dedo encima del botón —«¿esto no me va a pisar lo que ya
  // tengo?»—, y la respuesta es la regla de esta pantalla (ronda 90, del diseño de Stitch).
  const html = await htmlDelCuadernoDeLaJunta({
    textos: {
      ...structuredClone(TEXTOS_DEL_CUADERNO_JUNTA),
      cuaderno_cyl: {
        ...structuredClone(TEXTOS_DEL_CUADERNO_JUNTA.cuaderno_cyl),
        no_apunta_nada: "Leer el fichero no apunta nada todavía: primero verás lo que trae.",
      },
    },
  });
  assert.match(html, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  assert.match(html, /Leer el fichero no apunta nada todavía/);
  // Y no sale en los otros dos estados: ahí ya se ha leído.
  const resumen = await htmlDelCuadernoDeLaJunta({ resumen: RESUMEN_DE_PRUEBA });
  assert.doesNotMatch(resumen, /Leer el fichero no apunta nada/);
});

test("mientras lee, el botón lo dice y no se puede volver a pulsar", async () => {
  const leyendo = await htmlDelCuadernoDeLaJunta({ leyendo: true });
  assert.match(leyendo, /Eligiendo el fichero…/);
  assert.match(leyendo, /data-accion="cuaderno-leer" disabled=""/);
  assert.doesNotMatch(await htmlDelCuadernoDeLaJunta(), /disabled/);
});

test("el resumen enseña lo que trae el fichero, con sus tierras y su aviso", async () => {
  // Es el paso que evita la sorpresa de encontrarse 51 parcelas sin saber de dónde salen.
  const html = await htmlDelCuadernoDeLaJunta({ resumen: RESUMEN_DE_PRUEBA });
  assert.match(html, /Esto es lo que trae tu cuaderno/);
  assert.match(html, /<dt>Campaña<\/dt><dd>2026<\/dd>/);
  assert.match(html, /<dt>Tierras distintas<\/dt><dd>51<\/dd>/);
  assert.match(html, /<dt>Hectáreas que declaras<\/dt><dd>128,28<\/dd>/);
  assert.match(html, /Las tierras que se van a apuntar/);
  assert.match(html, /99-99-0-0-1-1-1 · PUEBLO DE EJEMPLO/);
  assert.match(html, /TRIGO BLANDO · 4,90 ha/);
  assert.match(html, /Conviene que mires esto/);
  assert.match(html, /no dicen el polígono/);
  // Y aquí lo que se puede hacer es confirmar o volver: **todavía no se ha apuntado nada**.
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["cuaderno-traer", "cuaderno-volver"]);
  assert.doesNotMatch(html, /Tus tierras ya están apuntadas/);
});

test("el resultado dice lo que se ha apuntado, lo que ya estaba y lo que faltó", async () => {
  const html = await htmlDelCuadernoDeLaJunta({ resultado: RESULTADO_DE_PRUEBA });
  assert.match(html, /Tus tierras ya están apuntadas/);
  assert.match(html, /<p>Tierras nuevas: 7<\/p>/);
  assert.match(html, /<p>Con cultivo: 6<\/p>/);
  // Lo que no ha entrado se dice, y en rojo: un cuaderno con una línea menos sin avisar es un descuadre.
  assert.match(html, /class="aviso aviso-error">Líneas que no se han podido apuntar: 1/);
  assert.match(html, /Se han rellenado tus datos/);
  assert.match(html, /lo que ya está apuntado no se duplica/);
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["mis-cosas", "cuaderno-volver"]);
  // Y ya no se enseña el resumen: no hay nada que confirmar.
  assert.doesNotMatch(html, /Esto es lo que trae tu cuaderno/);
});

test("un resultado sin líneas perdidas no lleva el aviso en rojo", async () => {
  const html = await htmlDelCuadernoDeLaJunta({
    resultado: { ...RESULTADO_DE_PRUEBA, sin_apuntar: "" },
  });
  assert.doesNotMatch(html, /aviso-error/, "avisa de líneas perdidas que no hay");
});

test("si el fichero no vale, se dice con el aviso de error", async () => {
  const html = await htmlDelCuadernoDeLaJunta({
    error: "No se ha podido abrir el cuaderno. Comprueba que es el fichero que descarga la Junta.",
  });
  assert.match(html, /class="aviso aviso-error"/);
  assert.match(html, /No se ha podido abrir el cuaderno/);
  assert.doesNotMatch(await htmlDelCuadernoDeLaJunta(), /aviso-error/);
});

test("el cuaderno de la Junta no lleva ni una frase escrita a mano", async () => {
  for (const html of [
    await htmlDelCuadernoDeLaJunta(),
    await htmlDelCuadernoDeLaJunta({ resumen: RESUMEN_DE_PRUEBA }),
    await htmlDelCuadernoDeLaJunta({ resultado: RESULTADO_DE_PRUEBA }),
  ]) {
    const delServidor = new Set([
      ...todosLosTextos(TEXTOS_DEL_CUADERNO_JUNTA),
      ...todosLosTextos(RESUMEN_DE_PRUEBA),
      ...todosLosTextos(RESULTADO_DE_PRUEBA),
    ]);
    for (const frase of frasesVisibles(html)) {
      assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
    }
  }
});

// ---------------------------------------------------------------------------
// «Decir qué hay sembrado»: el formulario que cierra el aviso de «falta el cultivo»
//
// Cuando el cuaderno le dice al agricultor que a una tierra le falta el cultivo, este formulario es
// donde lo contesta. Dos cosas se conservan a propósito y se comprueban aquí: que **los cinco campos
// tengan su `id`** (los lee `app.js` al guardar) y que **lo que el agricultor ya había escrito no se
// borre** cuando la pantalla se repinta por un aviso del servidor: perder lo tecleado es la forma más
// rápida de que alguien abandone un formulario.
// ---------------------------------------------------------------------------

/** Los textos del formulario, copiados de `textos.py`. */
const TEXTOS_DEL_CULTIVO = {
  cultivos: {
    la_especie: "¿Qué hay sembrado?",
    la_especie_pista: "Escribe el cultivo, como viene en tus papeles",
    // El aviso de arriba y la etiqueta del campo que hace falta (ronda 90).
    rellenar_aviso:
      "Rellena lo que sepas y pulsa GUARDAR. Lo único que hace falta de verdad es el cultivo: lo demás, si no estás seguro, déjalo en blanco.",
    imprescindible: "Hace falta",
    variedad: "¿De qué variedad?",
    variedad_pista: "Si no la sabes, déjalo en blanco",
    sistema: "¿Es de secano o de regadío?",
    desde_cuando: "¿Desde cuándo?",
    hasta_cuando: "¿Hasta cuándo?",
    fechas_pista: "Si no lo sabes, déjalo en blanco: se puede poner después",
    // Cambiar y quitar lo que ya dijiste (ronda 93).
    corrigiendo: "ESTÁS CAMBIANDO LO QUE DIJISTE",
    quitar: "QUITAR EL CULTIVO DE ESTE AÑO",
    quitar_pista: "Si esta tierra está en barbecho, quítalo: volverá a salir como una a la que le falta decirlo.",
  },
  acciones: { guardar: "GUARDAR", volver: "VOLVER" },
  // El rótulo del botón de guardar cuando se está cambiando: **viene de `corregir`** y no se escribe en
  // el componente, para que sea el mismo en toda la aplicación.
  corregir: { boton_guardar: "GUARDAR LOS CAMBIOS" },
};

async function htmlDeDecirCultivo(cambios = {}) {
  const { PantallaDecirCultivo } = await import(
    `../web/react/pantallas/decir_cultivo.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDecirCultivo, {
      textos: structuredClone(TEXTOS_DEL_CULTIVO),
      parcela: { id: 1, detalle: "El Prado · 2,43 ha" },
      valores: { especie: "", variedad: "", desde: "", hasta: "" },
      sistemas: [
        { valor: "secano", texto: "Secano", elegido: true },
        { valor: "regadio", texto: "Regadío", elegido: false },
      ],
      ...cambios,
    }),
  );
}

test("los cinco campos están, con su id, y se dice de qué tierra son", async () => {
  const html = await htmlDeDecirCultivo();
  assert.deepEqual(idsDe(html), [
    "cultivo-especie",
    "cultivo-variedad",
    "cultivo-sistema",
    "cultivo-desde",
    "cultivo-hasta",
  ]);
  // (Los cinco, en el orden de la pantalla: la especie, la variedad, el sistema y las dos fechas.)
  // La cabecera dice de qué tierra se está hablando: es lo que evita apuntar el cultivo en otra.
  assert.match(html, /<p class="pista">El Prado · 2,43 ha<\/p>/);
  assert.match(html, /<label for="cultivo-especie">¿Qué hay sembrado\?<\/label>/);
  // Las fechas se eligen en un calendario, no se teclean.
  assert.match(html, /<input id="cultivo-desde" type="date"/);
  assert.match(html, /<input id="cultivo-hasta" type="date"/);
  // Y el sistema viene elegido (el de la parcela).
  assert.match(html, /<option value="secano" selected="">Secano<\/option>/);
  assert.match(html, /<option value="regadio">Regadío<\/option>/);
});

test("las cinco preguntas van numeradas y se dice cuál hace falta de verdad", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): son cinco casillas y, sin números, no se sabe cuánto
  // queda (el número lo pone el CSS con un contador). Y la tranquilidad de que nada es obligatorio salvo el
  // cultivo: sin eso, cinco casillas parecen un examen.
  const html = await htmlDeDecirCultivo();
  assert.match(html, /<ol class="campos-numerados">/);
  assert.equal(
    (html.match(/<li><div class="campo">/g) || []).length,
    5,
    "las cinco preguntas no van una por renglón numerado",
  );
  assert.match(html, /class="etiqueta-estado etiqueta-estado-obligatorio">Hace falta</);
  assert.match(html, /Lo único que hace falta de verdad es el cultivo/);
});

test("lo que el agricultor ya había escrito sale puesto", async () => {
  // Si la pantalla se repinta por un aviso, lo tecleado no se pierde.
  const html = await htmlDeDecirCultivo({
    valores: {
      especie: "Cebada de dos carreras",
      variedad: "Meseta",
      desde: "2026-03-01",
      hasta: "2026-07-15",
    },
    error: "Ese cultivo no lo conozco.",
  });
  assert.match(html, /id="cultivo-especie"[^>]*value="Cebada de dos carreras"/);
  assert.match(html, /id="cultivo-variedad"[^>]*value="Meseta"/);
  assert.match(html, /id="cultivo-desde"[^>]*value="2026-03-01"/);
  assert.match(html, /id="cultivo-hasta"[^>]*value="2026-07-15"/);
  // Y el aviso del servidor se ve.
  assert.match(html, /class="aviso aviso-error"/);
  assert.doesNotMatch(await htmlDeDecirCultivo(), /aviso-error/);
});

test("los dos botones están, con su acción y con la tierra", async () => {
  const html = await htmlDeDecirCultivo();
  const botones = botonesDe(html);
  assert.deepEqual(
    botones.map((boton) => boton.accion),
    ["cultivo-guardar", "cultivo-ver-todos"],
  );
  // El de guardar lleva el `data-id` de la tierra: sin él, `app.js` no sabe dónde guardar.
  assert.match(html, /data-accion="cultivo-guardar" data-id="1"/);
});

test("cambiarlo se dice, y se ofrece quitarlo solo si hay algo que quitar", async () => {
  // **Ronda 93.** La misma pantalla sirve para decir qué hay sembrado y para cambiarlo. Cuando se está
  // cambiando hay que decirlo —el agricultor que llega desde «CAMBIARLO» tiene que ver que está
  // arreglando lo que ya dijo— y hay que ofrecer **quitarlo**, que es distinto de cambiarlo: la tierra en
  // barbecho no tiene un cultivo que cambiar, tiene una declaración que sobra.
  const diciendo = await htmlDeDecirCultivo();
  assert.doesNotMatch(diciendo, /ESTÁS CAMBIANDO LO QUE DIJISTE/, "dice que cambia cuando está diciendo");
  assert.doesNotMatch(diciendo, /QUITAR EL CULTIVO/, "ofrece quitar algo que todavía no se ha dicho");
  assert.match(diciendo, />GUARDAR</, "el botón no dice GUARDAR al decir");

  const cambiando = await htmlDeDecirCultivo({ ya_dicho: true });
  assert.match(cambiando, /class="etiqueta-estado etiqueta-estado-mirar">ESTÁS CAMBIANDO LO QUE DIJISTE</);
  // El botón de guardar dice que se guardan **cambios**: decirle «GUARDAR» a quien está arreglando un dato
  // es la forma de que crea que está apuntando uno nuevo.
  assert.match(cambiando, />GUARDAR LOS CAMBIOS</);
  assert.doesNotMatch(cambiando, />GUARDAR</, "sigue invitando a guardar como si fuera nuevo");
  // Y el de quitar está, con su explicación y **fuera de la barra de guardar**: el botón que quita algo del
  // cuaderno no puede ser el que más apetezca pulsar (diseño de Stitch de la ronda 91).
  assert.match(cambiando, /data-accion="cultivo-quitar" data-id="1"/);
  assert.match(cambiando, /class="boton boton-peligro" data-accion="cultivo-quitar"|boton-peligro/);
  assert.match(cambiando, /Si esta tierra está en barbecho, quítalo/);
  // Los cinco campos siguen siendo los mismos, con sus `id`: lo único que cambia es lo de arriba.
  assert.deepEqual(idsDe(cambiando), [
    "cultivo-especie",
    "cultivo-variedad",
    "cultivo-sistema",
    "cultivo-desde",
    "cultivo-hasta",
  ]);
});

test("el formulario del cultivo no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeDecirCultivo({ error: "Ese cultivo no lo conozco." });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DEL_CULTIVO),
    // Las opciones del sistema salen del catálogo del servidor, no del componente.
    "Secano",
    "Regadío",
    "El Prado · 2,43 ha",
    "Ese cultivo no lo conozco.",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// El mapa del SIGPAC: el camino más corto para dar de alta una tierra
//
// **Es la primera pantalla migrada que se toca con el dedo**, y por eso lo que más importa aquí es
// que el **botón que se toca** (`.mapa-tocar`, con su `data-accion`) siga estando, con la cruz del
// centro y el trozo dibujado encima: el toque lo atiende el manejador delegado de `document`, que
// necesita saber **dónde** se ha tocado. Y cuando no se sabe por dónde empezar (sin parcelas y sin
// ubicación) **no se pinta un mapa**: se pide la ubicación o se dice, porque una caja de coordenadas
// inventada enseñaría el mapa de otro sitio.
// ---------------------------------------------------------------------------

/** Los textos del mapa, copiados de `textos.py`. */
const TEXTOS_DEL_MAPA = {
  mapa: {
    titulo: "El mapa",
    pista_mover: "Mueve el mapa y toca el trozo que es tuyo.",
    la_foto: "La foto del campo",
    los_linderos: "Los linderos",
    cargando: "Cargando el mapa",
    acercar: "ACERCAR",
    alejar: "ALEJAR",
    estoy_aqui: "ESTOY AQUÍ",
    poner_en_el_centro: "¿QUÉ HAY AQUÍ?",
    necesita_conexion: "El mapa necesita conexión.",
    encontrado_titulo: "Esto es lo que hay ahí",
    pregunta: "¿Es tuya esta tierra?",
    superficie: "Superficie",
    pueblo: "Pueblo",
    referencia_catastral: "Referencia catastral",
    zona_nitratos: "Zona de nitratos",
    apuntarla: "ESTA ES MI TIERRA",
    no_es_mia: "NO ES ESA",
    sin_centro: "No se puede saber por dónde empezar. Pulsa ESTOY AQUÍ.",
  },
  sigpac: {
    referencia_como_sea: "La referencia de tu trozo",
    uso: "Uso",
    sistema: "¿Es de secano o de regadío?",
    alias: "¿Cómo la llamas tú?",
  },
  acciones: { volver: "VOLVER" },
};

/** Lo que contesta el SIGPAC de un punto, ya preparado como lo manda `app.js`. */
function elegidoDePrueba(cambios = {}) {
  return {
    filas: [
      ["La referencia de tu trozo", "37-70-0-0-503-51-1"],
      ["Superficie", "4,9016 ha"],
      ["Uso", "TA — TIERRAS ARABLES"],
      ["Zona de nitratos", "No está en zona de nitratos"],
    ],
    sistema_etiqueta: "¿Es de secano o de regadío?",
    sistemas: [
      { valor: "secano", texto: "Secano", elegido: true },
      { valor: "regadio", texto: "Regadío", elegido: false },
    ],
    alias_etiqueta: "¿Cómo la llamas tú?",
    alias: "",
    ...cambios,
  };
}

async function htmlDelMapa(cambios = {}) {
  const { PantallaMapa } = await import(`../web/react/pantallas/mapa.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaMapa, {
      textos: structuredClone(TEXTOS_DEL_MAPA),
      centrado: true,
      imagenes: {
        foto: "/api/mapa/imagen?capa=foto&oeste=-5.5759&sur=40.9018&este=-5.5359&norte=40.9098",
        linderos: "/api/mapa/imagen?capa=linderos&oeste=-5.5759&sur=40.9018&este=-5.5359&norte=40.9098",
        vista: "0 0 900 600",
      },
      centro: "40,90580, -5,55590",
      ...cambios,
    }),
  );
}

test("el mapa lleva la foto, los linderos y el botón que se toca", async () => {
  const html = await htmlDelMapa({ poligono: "450.0,300.0 500.0,320.0 480.0,360.0" });
  assert.match(html, /class="mapa-vista"/);
  assert.match(html, /class="mapa-foto" src="\/api\/mapa\/imagen\?capa=foto/, "no pide la foto");
  assert.match(html, /class="mapa-linderos" src="\/api\/mapa\/imagen\?capa=linderos/);
  // El botón que se toca y la cruz del centro: sin ellos no hay mapa que usar con el dedo.
  assert.match(html, /class="mapa-tocar" data-accion="mapa-tocar"/);
  assert.match(html, /class="mapa-cruz"/);
  // Y el dibujo con su caja y el trozo dentro.
  assert.match(html, /<svg class="mapa-svg" viewBox="0 0 900 600"/);
  assert.match(html, /<polygon points="450.0,300.0 500.0,320.0 480.0,360.0"><\/polygon>/);
  // Sin trozo no se dibuja un polígono vacío.
  assert.doesNotMatch(await htmlDelMapa(), /<polygon/, "dibuja un trozo que no hay");
});

test("los botones del mapa están, con su acción", async () => {
  const html = await htmlDelMapa();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, [
    "mapa-tocar",
    "mapa-acercar",
    "mapa-alejar",
    "mapa-estoy-aqui",
    "mapa-preguntar",
    "mapa-volver",
  ]);
  // El de preguntar es el grande: es lo que hace el agricultor después de mover el mapa.
  assert.match(html, /class="boton boton-principal" data-accion="mapa-preguntar"/);
  assert.match(html, /40,90580, -5,55590/, "no enseña dónde está mirando");
  assert.match(html, /El mapa necesita conexión/, "no avisa de que hace falta cobertura");
});

test("sin saber por dónde empezar no se pinta el mapa, y se pide la ubicación", async () => {
  // Una caja de coordenadas inventada enseñaría el mapa de otro sitio. Es peor que no enseñarlo.
  const html = await htmlDelMapa({ centrado: false, error: TEXTOS_DEL_MAPA.mapa.sin_centro });
  assert.doesNotMatch(html, /class="mapa-vista"/, "pinta un mapa de un sitio que no es el suyo");
  assert.match(html, /data-accion="mapa-estoy-aqui"/, "no deja pedir la ubicación");
  assert.match(html, /No se puede saber por dónde empezar/);
});

test("lo que contesta el SIGPAC sale con sus filas y sus botones", async () => {
  const html = await htmlDelMapa({ elegido: elegidoDePrueba() });
  assert.match(html, /class="mapa-elegido"/);
  assert.match(html, /37-70-0-0-503-51-1/, "no enseña la referencia");
  assert.match(html, /<dt>Superficie<\/dt><dd>4,9016 ha<\/dd>/);
  assert.match(html, /TA — TIERRAS ARABLES/, "no enseña el uso como lo dice el SIGPAC");
  assert.match(html, /No está en zona de nitratos/);
  assert.match(html, /data-accion="mapa-apuntar"/);
  assert.match(html, /data-accion="mapa-no-es-esa"/);
  // El secano viene elegido y el regadío no: es el valor por defecto de la finca.
  assert.match(html, /class="boton boton-elegido" data-accion="elegir" data-campo="sistema" data-valor="secano"/);
  assert.match(html, /class="boton boton-claro" data-accion="elegir" data-campo="sistema" data-valor="regadio"/);
  // Y el campo del nombre conserva su `id`: lo lee `app.js` antes de repintar.
  assert.match(html, /<label for="alias_mapa">¿Cómo la llamas tú\?<\/label>/);
  // React escribe el valor inicial como `value` en el HTML estático (el campo no está
  // gobernado por React: lo lee `app.js` antes de repintar).
  assert.match(html, /<input id="alias_mapa" type="text" value=""/);
  // Sin nada elegido, el bloque no se dibuja.
  assert.doesNotMatch(await htmlDelMapa(), /class="mapa-elegido"/);
});

test("mientras busca, lo dice, y si algo falla se ve", async () => {
  const buscando = await htmlDelMapa({ cargando: true });
  assert.match(buscando, /class="mapa-cargando"/);
  assert.match(buscando, /Cargando el mapa/);
  const conError = await htmlDelMapa({ error: "Ahí no hay ninguna parcela del SIGPAC." });
  assert.match(conError, /class="aviso aviso-error"/);
  assert.match(conError, /no hay ninguna parcela/);
});

test("el mapa no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDelMapa({ elegido: elegidoDePrueba() });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DEL_MAPA),
    ...todosLosTextos(elegidoDePrueba()),
    // Las coordenadas del centro las monta `app.js` con los números ya en castellano: no son una
    // frase, son un dato.
    "40,90580, -5,55590",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// Los análisis: el boletín del laboratorio, con sus números y su papel
//
// Esta pantalla se pasa a React después de comprobar en un navegador de verdad que «mi cuaderno»
// contaba cero apuntes. Aquí estaban dos pruebas que miraban su HTML en el contenedor de mentira
// («la pantalla de análisis abre desde mi cuaderno» y «el apartado dice de dónde sale cada lista
// de números»): **se han reescrito contra el componente**, que es donde ahora se puede comprobar
// frase por frase, y en `interfaz.test.js` queda una que comprueba el cableado.
// ---------------------------------------------------------------------------

/** Los textos de los análisis, copiados de `textos.py` (los que sirve `/api/interfaz`). */
const TEXTOS_DE_ANALISIS = {
  analitica: {
    titulo: "Los análisis",
    explica:
      "Aquí se guardan los análisis que has mandado hacer: de la tierra, del agua, de la planta o de la cosecha. Con los números de la tierra se abona mejor, y el papel del laboratorio no se pierde.",
    sin_analisis: "Todavía no has apuntado ningún análisis.",
    anadir: "APUNTAR UN ANÁLISIS",
    sin_numeros: "Sin números apuntados: solo está guardado el boletín.",
    // El rótulo del bloque de números y las dos formas de decir de qué año es el boletín (ronda 90).
    numeros_titulo: "Los números del boletín",
    de_este_anio: "De este año",
    hace_anios: "Hace {anios} años",
    subir_informe: "SUBIR EL PAPEL DEL LABORATORIO",
    informe_ya_esta: "Ya tienes el boletín guardado.",
    descargar_informe: "DESCARGAR EL BOLETÍN",
    sin_informe:
      "De este análisis no tienes el papel guardado. Si lo tienes en el móvil o en papel, hazle una foto y súbela.",
    sin_oficial:
      "Los números que se guardan de cada clase de análisis son los que trae el boletín. De la tierra son los nueve que pide la administración; de lo demás, todavía no hay listado oficial.",
  },
  acciones: { volver: "VOLVER" },
};

/** Un análisis de los que prepara `app.js`: título, filas y números ya hechos. */
function analisisDePrueba(cambios = {}) {
  return {
    id: 4,
    titulo: "Análisis de La tierra de El Prado",
    filas: [
      ["De dónde salió", "El Prado"],
      ["Muestra cogida el", "14/02/2026"],
      ["Resultado el", "20/02/2026"],
      ["Laboratorio", "Laboratorio Agrario de Villamuriel"],
      ["Nº de boletín", "B-2026-77"],
    ],
    // La etiqueta de la edad del boletín, que `app.js` arma con el año (ronda 90).
    estado: { texto: "De este año (2026)", tipo: "bien" },
    numeros: [
      ["Materia orgánica", "1,80 %"],
      ["pH", "7,4"],
    ],
    linea_informe: "Ya tienes el boletín guardado. (boletin-2026.pdf)",
    tiene_informe: true,
    ...cambios,
  };
}

async function htmlDeAnalisis(cambios = {}) {
  const { PantallaAnaliticas } = await import(
    `../web/react/pantallas/analiticas.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaAnaliticas, {
      textos: structuredClone(TEXTOS_DE_ANALISIS),
      analisis: [analisisDePrueba()],
      ...cambios,
    }),
  );
}

test("un análisis sale con su título, su boletín y sus números", async () => {
  const html = await htmlDeAnalisis();
  assert.match(html, /Análisis de La tierra de El Prado/, "no dice cuál es");
  assert.match(html, /Laboratorio Agrario de Villamuriel/, "no dice quién lo hizo");
  assert.match(html, /14\/02\/2026/, "no dice cuándo se cogió la muestra");
  assert.match(html, /B-2026-77/, "no dice el número de boletín");
  assert.match(html, /1,80 %/, "no enseña los números del boletín");
});

test("el análisis dice de dónde sale cada lista de números", async () => {
  // Honestidad: de la tierra los parámetros los fija la norma; de lo demás, no. Que el
  // agricultor (y quien revise esto dentro de un año) lo sepa sin leer el código.
  assert.match(await htmlDeAnalisis(), /son los nueve que pide la administración/);
});

test("con el papel subido se puede descargar, y sin él no se ofrece", async () => {
  const conPapel = await htmlDeAnalisis();
  assert.match(conPapel, /data-accion="analisis-informe-subir"/);
  assert.match(conPapel, /data-accion="analisis-informe-bajar"/);
  assert.match(conPapel, /Ya tienes el boletín guardado\. \(boletin-2026\.pdf\)/);

  const sinPapel = await htmlDeAnalisis({
    analisis: [
      analisisDePrueba({
        linea_informe: TEXTOS_DE_ANALISIS.analitica.sin_informe,
        tiene_informe: false,
      }),
    ],
  });
  assert.match(sinPapel, /data-accion="analisis-informe-subir"/, "hay que poder subirlo siempre");
  assert.doesNotMatch(
    sinPapel,
    /data-accion="analisis-informe-bajar"/,
    "ofrece descargar un papel que no existe",
  );
});

test("el campo del fichero lleva el id con el que el programa lo lee", async () => {
  // El botón de subir el boletín busca el fichero por su `id` (`informe-<id>`), así que si el
  // componente lo cambiara, subir el papel dejaría de funcionar sin decir nada.
  const html = await htmlDeAnalisis();
  assert.match(html, /<input type="file" id="informe-4"[^>]*class="oculto"\/>/);
  assert.match(html, /data-id="4"/, "los botones no llevan de qué análisis son");
});

test("el boletín dice de qué año es, en su etiqueta", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): un boletín de hace tres años no vale lo mismo que
  // uno de este año, y eso hay que verlo sin leer la fecha de la muestra. Antes era una línea de texto
  // debajo de la ficha, que había que leer entera.
  const deEsteAnio = await htmlDeAnalisis();
  assert.match(deEsteAnio, /class="etiqueta-estado etiqueta-estado-bien">De este año \(2026\)</);

  const viejo = await htmlDeAnalisis({
    analisis: [
      analisisDePrueba({ estado: { texto: "Hace 2 años (2024)", tipo: "mirar" } }),
    ],
  });
  assert.match(viejo, /class="etiqueta-estado etiqueta-estado-mirar">Hace 2 años \(2024\)</);
});

test("los números del boletín van en su bloque, con su rótulo y su número grande", async () => {
  // Ocho o nueve números por boletín: en renglones con el rótulo a la izquierda había que leerlos uno a
  // uno para comparar dos campañas. En su caja, con el número grande, se leen de un vistazo.
  const html = await htmlDeAnalisis();
  assert.match(html, /<p class="pista-campo">Los números del boletín<\/p>/);
  assert.match(html, /<ul class="numeros">/);
  assert.match(
    html,
    /<li><span class="numero-etiqueta">Materia orgánica<\/span><span class="dato-grande">1,80 %<\/span><\/li>/,
    "los números no van con su nombre y su número grande",
  );
});

test("sin el papel del laboratorio, lo que falta se dice y el botón de subirlo es el grande", async () => {
  // Es lo único que le falta a ese análisis, así que es lo que tiene que destacar: la frase en su franja
  // de aviso y el botón de subirlo con el color de acción (antes eran dos botones claros iguales).
  const sinPapel = await htmlDeAnalisis({
    analisis: [
      analisisDePrueba({
        linea_informe: TEXTOS_DE_ANALISIS.analitica.sin_informe,
        tiene_informe: false,
      }),
    ],
  });
  assert.match(sinPapel, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  assert.match(sinPapel, /class="boton boton-principal" data-accion="analisis-informe-subir"/);
  // Y con el papel ya subido, la frase es una pista normal y el botón no es el grande.
  const conPapel = await htmlDeAnalisis();
  assert.match(conPapel, /class="boton boton-claro" data-accion="analisis-informe-subir"/);
  assert.doesNotMatch(conPapel, /class="tarjeta-aviso"/);
});

test("un boletín sin números copiados lo dice, en vez de enseñar una lista vacía", async () => {
  const html = await htmlDeAnalisis({ analisis: [analisisDePrueba({ numeros: [] })] });
  assert.match(html, /Sin números apuntados: solo está guardado el boletín\./);
  // Y no se dibujan dos listas: la de la ficha y una vacía debajo.
  assert.equal((html.match(/<dl>/g) || []).length, 1, "ha dibujado una lista de números vacía");
});

test("sin análisis se dice, en vez de dejar la pantalla en blanco", async () => {
  const vacia = await htmlDeAnalisis({ analisis: [] });
  assert.match(vacia, /class="aviso"/);
  assert.match(vacia, /Todavía no has apuntado ningún análisis\./);
  assert.doesNotMatch(vacia, /<h2>/, "ha dibujado la ficha de un análisis que no existe");
});

test("los dos botones de abajo están, con su acción", async () => {
  const html = await htmlDeAnalisis();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones.slice(-2), ["analisis-nuevo", "inicio"]);
  assert.match(html, /data-accion="inicio" data-ir="mi_cuaderno"/);
});

test("los análisis no llevan ni una frase escrita a mano", async () => {
  const html = await htmlDeAnalisis();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_ANALISIS),
    ...todosLosTextos(analisisDePrueba()),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Dímelo con la voz»: el atajo del campo, y nunca un requisito
//
// Esta pantalla trae el **primer campo de texto largo** que se migra: lo que se dicta o se teclea
// vive en el DOM (el campo conserva su `id`, `dictado-texto`, y lo lee `app.js`). Aquí se comprueba
// que el campo está, que se puede escribir en él y que sin voz se puede teclear igual.
// ---------------------------------------------------------------------------

/** Los textos del dictado, copiados de `textos.py` (los que sirve `/api/interfaz`). */
const TEXTOS_DE_DICTADO = {
  dictado: {
    titulo: "Dímelo con la voz",
    intro:
      "Cuéntame lo que has hecho y yo lo apunto. Después lo revisas tú: nada se guarda sin que lo veas.",
    boton: "HABLAR",
    pista_boton: "cuéntamelo con tus palabras",
    escribe: "Escribe lo que has hecho",
    escribe_pista:
      "Lo que digas queda escrito aquí. Si alguna palabra sale cambiada, corrígela con el dedo: lo que se apunta es lo que ponga aquí.",
    ejemplo: "Por ejemplo: «hoy he echado dos litros en el prado, había pulgón»",
    entender: "ENTENDERLO",
    no_se_puede:
      "Este navegador no sabe escuchar. Escribe lo que has hecho y dale a ENTENDERLO: funciona igual.",
    no_he_oido: "No he oído nada. Prueba otra vez, o escríbelo.",
  },
  acciones: { volver: "VOLVER" },
};

async function htmlDeDictado(cambios = {}) {
  const { PantallaDictado } = await import(
    `../web/react/pantallas/dictado.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDictado, {
      textos: structuredClone(TEXTOS_DE_DICTADO),
      puedeHablar: true,
      ...cambios,
    }),
  );
}

test("el dictado enseña el campo donde escribir, con su id", async () => {
  const html = await htmlDeDictado();
  assert.match(html, /Dímelo con la voz/);
  assert.match(html, /<label for="dictado-texto">Escribe lo que has hecho<\/label>/);
  assert.match(
    html,
    /<textarea id="dictado-texto" rows="3">/,
    "sin el campo no se puede escribir lo que has hecho",
  );
  assert.match(html, /hoy he echado dos litros en el prado/, "no enseña el ejemplo");
});

test("el botón de hablar va primero y el recuadro debajo, con lo que se puede hacer con él", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): hablar es la acción principal, no un plan B. Antes
  // el recuadro iba arriba y el botón debajo, y se leía como un formulario que había que rellenar.
  const html = await htmlDeDictado();
  assert.ok(
    html.indexOf('data-accion="dictado-hablar"') < html.indexOf('id="dictado-texto"'),
    "el botón de hablar no va antes que el recuadro",
  );
  // Y se dice que lo escrito se puede corregir con el dedo: sin eso, una palabra mal oída parece un
  // fallo del programa del que no se puede hacer nada.
  assert.match(html, /Si alguna palabra sale cambiada, corrígela con el dedo/);
});

test("lo que ya se ha dictado se queda escrito en el campo", async () => {
  const html = await htmlDeDictado({ escrito: "he echado glifosato en el prado" });
  assert.match(html, /<textarea id="dictado-texto" rows="3">he echado glifosato en el prado<\/textarea>/);
});

test("con voz en el navegador sale el botón de hablar, y sin voz se avisa", async () => {
  const conVoz = await htmlDeDictado();
  assert.match(conVoz, /data-accion="dictado-hablar"/);
  assert.match(conVoz, /class="boton boton-principal" data-accion="dictado-hablar"/);

  // Sin voz, se dice **y se deja escribir**: el dictado es un atajo, nunca un requisito.
  const sinVoz = await htmlDeDictado({ puedeHablar: false });
  assert.doesNotMatch(sinVoz, /data-accion="dictado-hablar"/, "ofrece dictar sin poder dictar");
  assert.match(sinVoz, /Este navegador no sabe escuchar/);
  assert.match(sinVoz, /id="dictado-texto"/, "sin voz se queda sin poder escribir");
});

test("si algo ha fallado, se dice con el aviso de error", async () => {
  const html = await htmlDeDictado({ error: TEXTOS_DE_DICTADO.dictado.no_he_oido });
  assert.match(html, /class="aviso aviso-error"/);
  assert.match(html, /No he oído nada\. Prueba otra vez, o escríbelo\./);
  // Y sin error no se dibuja el hueco rojo: asusta sin motivo.
  assert.doesNotMatch(await htmlDeDictado(), /aviso-error/);
});

test("los dos botones de abajo están, con su acción", async () => {
  const html = await htmlDeDictado();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["dictado-hablar", "dictado-entender", "ir-inicio"]);
  assert.match(html, /class="boton boton-claro" data-accion="ir-inicio"/);
});

test("el dictado no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeDictado({ escrito: "he echado glifosato en el prado" });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_DICTADO),
    "he echado glifosato en el prado",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// La revisión de lo dictado: lo que se ha entendido, antes de guardar nada
//
// Esta pantalla cierra el camino del dictado. Es la que enseña lo que el servidor ha entendido y
// **lo que no ha sabido colocar**, que no se tira: el agricultor lo ve y lo corrige. Las frases
// vienen dentro del propio borrador (las pone el servidor desde `textos.py`), así que lo que aquí
// se comprueba es que se pintan todas donde toca.
// ---------------------------------------------------------------------------

/** Los textos que acompañan al borrador, tal y como los sirve `/api/interfaz`. */
const TEXTOS_DEL_BORRADOR = {
  maestros: { sin_sitio_titulo: "Esto lo he oído pero no sé dónde ponerlo" },
  dictado: {
    apuntarlo: "ESTÁ BIEN, APUNTARLO",
    corregir: "CORREGIRLO A MANO",
    has_dicho: "Has dicho:",
  },
};

/** Un borrador de los que devuelve `POST /api/borradores/desde-texto`. */
function borradorDePrueba(cambios = {}) {
  return {
    tipo: "tratamiento",
    datos: { parcela_id: 1, producto_id: 5 },
    entendido: [
      { pregunta: "¿Dónde?", valor: "El Prado", campo: "parcela_id" },
      { pregunta: "¿Qué producto has echado?", valor: "Glifosato 36 SL", campo: "producto_id" },
      { pregunta: "¿Cuánto por hectárea?", valor: "2,00", campo: null },
    ],
    falta: [{ pregunta: "¿Cuándo?" }],
    fuente: "reglas",
    titulo: "Lo que he entendido",
    intro: "Mira si está bien. Completa lo que falte y apúntalo.",
    falta_intro: "Para poder apuntarlo me falta esto:",
    nada_entendido: null,
    ...cambios,
  };
}

async function htmlDelBorrador(cambios = {}, textos = {}) {
  const { PantallaBorrador } = await import(
    `../web/react/pantallas/borrador.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaBorrador, {
      textos: { ...structuredClone(TEXTOS_DEL_BORRADOR), ...textos },
      borrador: borradorDePrueba(cambios),
      dicho: "ayer por la tarde eché el tebuconazol en El Prado, a dos litros",
    }),
  );
}

test("lo que has dicho sale entero, para poder compararlo con lo entendido", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): lo único que veía el agricultor eran los datos ya
  // colocados, así que si el programa oyó mal una palabra no tenía con qué compararlo. Y es él el único
  // que puede darse cuenta.
  const html = await htmlDelBorrador();
  assert.match(html, /<strong>Has dicho:<\/strong> ayer por la tarde eché el tebuconazol en El Prado/);
  // Sin texto (por ejemplo si se llegó aquí sin dictar nada) no se dibuja el rótulo suelto.
  const sinDicho = globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(
      (await import(`../web/react/pantallas/borrador.js?prueba=${Math.random()}`)).PantallaBorrador,
      { textos: structuredClone(TEXTOS_DEL_BORRADOR), borrador: borradorDePrueba(), dicho: "" },
    ),
  );
  assert.doesNotMatch(sinDicho, /Has dicho:/, "enseña el rótulo sin lo que se ha dicho");
});

test("lo que se ha entendido sale con su pregunta y su valor", async () => {
  const html = await htmlDelBorrador();
  assert.match(html, /Lo que he entendido/);
  assert.match(html, /Mira si está bien\. Completa lo que falte y apúntalo\./);
  assert.match(html, /<dt>¿Dónde\?<\/dt><dd>El Prado<\/dd>/);
  assert.match(html, /<dt>¿Qué producto has echado\?<\/dt><dd>Glifosato 36 SL<\/dd>/);
});

test("lo que se ha oído y no se sabe dónde va no se tira: sale aparte", async () => {
  // Es la decisión de la pantalla vieja que se conserva: perder lo que se ha oído sería peor que
  // enseñarlo sin sitio. Y no se mezcla con lo colocado: va en su bloque.
  const html = await htmlDelBorrador();
  assert.match(html, /Esto lo he oído pero no sé dónde ponerlo/);
  assert.match(html, /¿Cuánto por hectárea\? <strong>2,00<\/strong>/);
  assert.match(html, /class="ayuda-campo"/);
  // Y el bloque solo sale si hay algo sin colocar.
  const sinNadaSuelto = await htmlDelBorrador({
    entendido: [{ pregunta: "¿Dónde?", valor: "El Prado", campo: "parcela_id" }],
  });
  assert.doesNotMatch(sinNadaSuelto, /class="ayuda-campo"/, "ha dibujado un bloque vacío");
});

test("sin nada entendido se dice, en vez de una ficha vacía", async () => {
  const html = await htmlDelBorrador({
    entendido: [],
    nada_entendido: "No he entendido nada de lo que has dicho. Prueba a decírmelo de otra forma.",
  });
  assert.match(html, /class="aviso"/);
  assert.match(html, /No he entendido nada de lo que has dicho/);
  assert.doesNotMatch(html, /<dl>/, "ha dibujado una ficha sin nada dentro");
});

test("lo que falta para poder apuntarlo se dice", async () => {
  const html = await htmlDelBorrador();
  // **Y desde la ronda 90 va en su caja de aviso** (diseño de Stitch): es lo que impide terminar, así que
  // tiene que verse como un aviso y no como un título suelto con una lista debajo.
  assert.match(html, /<div class="aviso"><strong>Para poder apuntarlo me falta esto:<\/strong>/);
  assert.match(html, /<li>¿Cuándo\?<\/li>/);
  // Y si no falta nada, no se dibuja la lista ni su título.
  const completo = await htmlDelBorrador({ falta: [] });
  assert.doesNotMatch(completo, /Para poder apuntarlo me falta esto:/);
});

test("los dos botones están, con su acción", async () => {
  const html = await htmlDelBorrador();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["borrador-apuntar", "borrador-corregir"]);
  assert.match(html, /class="boton" data-accion="borrador-apuntar"/);
  assert.match(html, /class="boton boton-claro" data-accion="borrador-corregir"/);
});

test("la revisión de lo dictado no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDelBorrador();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DEL_BORRADOR),
    ...todosLosTextos(borradorDePrueba()),
    // Lo que ha dicho el agricultor tampoco es una frase de la pantalla: es **lo que él contó**, y va
    // tal cual (ronda 90). El componente solo pone delante su rótulo del servidor.
    "ayer por la tarde eché el tebuconazol en El Prado, a dos litros",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Guardar un papel»: el formulario con más campos de los que ya están en React
//
// **Aquí lo que se juega es que los campos sigan teniendo su `id`.** React los pinta y `app.js` los
// lee por ese `id` al guardar (`guardarDocumento()`): si uno cambia, el agricultor rellena el
// formulario y se guarda un papel sin título, sin carpeta y sin fecha, sin que salte ningún error.
// Por eso hay una prueba que mira los seis `id` uno a uno, y otra —en `interfaz.test.js`— que
// rellena el formulario y comprueba lo que de verdad se manda al servidor.
// ---------------------------------------------------------------------------

/** Los textos del formulario de papeles, copiados de `textos.py`. */
const TEXTOS_DEL_FORMULARIO = {
  documentos: {
    nuevo: "GUARDAR UN PAPEL",
    para_que:
      "Si un día viene una inspección, esto es lo que te van a pedir junto con el cuaderno.",
    titulo_del_papel: "¿Qué es?",
    titulo_pista: "Por ejemplo: «Contrato de la finca del río» o «Factura del abono de mayo»",
    que_es: "¿De qué es?",
    carpeta: "¿En qué carpeta lo guardas?",
    carpeta_pista: "Como las tienes tú en casa. Si escribes una nueva, se crea.",
    fecha_del_papel: "¿De qué fecha es?",
    fecha_pista: "La del papel, no la de hoy. Si no lo sabes, déjalo en blanco.",
    quien: "¿De quién es o quién te lo dio?",
    quien_pista: "El proveedor, el dueño de la tierra, la cooperativa",
    notas: "¿Quieres apuntar algo más?",
    el_titulo: "Ponle un nombre al papel, para poder encontrarlo luego.",
    // Lo que trae el diseño de Stitch de esta pantalla (ronda 90).
    hace_falta: "Hace falta",
    toca_una: "Toca una de las que ya tienes, o escribe una nueva:",
    el_fichero: "El papel en sí (una foto o el PDF)",
    fichero_pista:
      "Si tienes el papel a mano, hazle una foto o elige el fichero: queda guardado con él. Si no lo tienes, apúntalo igual y súbelo cuando llegues a casa.",
  },
  acciones: { guardar: "GUARDAR", volver: "VOLVER" },
};

const TIPOS_DE_PAPEL = [
  { valor: "contrato", etiqueta: "Contrato de la tierra" },
  { valor: "factura", etiqueta: "Factura" },
  { valor: "otros", etiqueta: "Otros papeles" },
];

async function htmlDelFormulario(cambios = {}) {
  const { PantallaNuevoDocumento } = await import(
    `../web/react/pantallas/nuevo_documento.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaNuevoDocumento, {
      textos: structuredClone(TEXTOS_DEL_FORMULARIO),
      tipos: TIPOS_DE_PAPEL,
      carpetas: ["Contratos", "Facturas"],
      ...cambios,
    }),
  );
}

test("los campos van numerados, las carpetas se tocan y el papel se sube aquí", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90):
  //  · los seis renglones, numerados (el número lo pone el CSS con un contador);
  //  · el nombre del papel es lo único que hace falta de verdad, y lo dice su etiqueta;
  //  · las carpetas que ya tiene **se tocan** en vez de escribirlas: en el móvil, y con guantes, escribir el
  //    nombre de la carpeta es lo que más cuesta;
  //  · y el papel se puede subir **en esta misma pantalla**, que antes había que guardarlo, ir a la lista y
  //    subirlo desde allí.
  const html = await htmlDelFormulario();
  assert.match(html, /<ol class="campos-numerados">/);
  assert.equal((html.match(/<li><div class="campo">/g) || []).length, 6, "los seis campos no van numerados");
  assert.match(html, /class="etiqueta-estado etiqueta-estado-obligatorio">Hace falta</);
  const carpetas = botonesDe(html).filter((boton) => boton.accion === "papel-carpeta");
  assert.equal(carpetas.length, 2, `salen ${carpetas.length} botones de carpeta y son dos`);
  // El nombre va en el `data-nombre` (lo lee `app.js` para rellenar el campo) y como texto del botón.
  assert.match(html, /data-accion="papel-carpeta" data-nombre="Contratos">Contratos</);
  assert.match(html, /data-accion="papel-carpeta" data-nombre="Facturas">Facturas</);
  assert.match(html, /<input id="papel-fichero" type="file" accept="\.pdf,image\/\*"\/>/);
  assert.match(html, /Si tienes el papel a mano, hazle una foto/);
  // Y sin carpetas guardadas no se enseña una lista vacía.
  const sinCarpetas = await htmlDelFormulario({ carpetas: [] });
  assert.doesNotMatch(sinCarpetas, /data-accion="papel-carpeta"/);
});

test("los seis campos están, cada uno con su id", async () => {  // Los `id` no son decoración: son la única forma que tiene `app.js` de leer lo escrito.
  const html = await htmlDelFormulario();
  for (const id of [
    "papel-titulo",
    "papel-tipo",
    "papel-carpeta",
    "papel-fecha",
    "papel-quien",
    "papel-notas",
  ]) {
    assert.match(html, new RegExp(`id="${id}"`), `falta el campo ${id} o se ha cambiado de nombre`);
  }
  // Y cada campo con su etiqueta, atada a él: quien use un lector de pantalla tiene que oírlo.
  assert.match(html, /<label for="papel-titulo">¿Qué es\?<\/label>/);
  assert.match(html, /<label for="papel-notas">¿Quieres apuntar algo más\?<\/label>/);
});

test("las clases de papel salen del servidor, con «otros» elegido", async () => {
  // No se escriben aquí: en el servidor está el catálogo. Y «otros» viene elegido porque es el
  // caso de casi todos los papeles que no son ni contrato ni factura (era el valor por defecto).
  const html = await htmlDelFormulario();
  assert.match(html, /<option value="contrato">Contrato de la tierra<\/option>/);
  assert.match(html, /<option value="factura">Factura<\/option>/);
  assert.match(html, /<option value="otros" selected="">Otros papeles<\/option>/);
});

test("las carpetas que ya tiene se ofrecen para no volver a escribirlas", async () => {
  const html = await htmlDelFormulario();
  assert.match(html, /list="papel-carpetas"/, "el campo de carpeta no sugiere nada");
  assert.match(html, /<datalist id="papel-carpetas">/);
  assert.match(html, /<option value="Contratos"><\/option>/);
  assert.match(html, /<option value="Facturas"><\/option>/);
});

test("si no se ha podido guardar, se dice con el aviso de error", async () => {
  const html = await htmlDelFormulario({ error: TEXTOS_DEL_FORMULARIO.documentos.el_titulo });
  assert.match(html, /class="aviso aviso-error"/);
  assert.match(html, /Ponle un nombre al papel/);
  assert.doesNotMatch(await htmlDelFormulario(), /aviso-error/);
});

test("los dos botones están, con su acción y con su palabra", async () => {
  const html = await htmlDelFormulario();
  const botones = botonesDe(html)
    // Los botones de las carpetas para tocar (ronda 90) se comprueban en su propia prueba.
    .filter((boton) => boton.accion !== "papel-carpeta");
  assert.deepEqual(
    botones.map((boton) => boton.accion),
    ["papel-guardar", "papel-ver-todos"],
  );
  // **La palabra también se comprueba.** Aquí faltaba: el botón de guardar se quedó sin texto
  // (salía el botón vacío, solo con la flecha) porque la palabra no estaba en el bloque de textos
  // del servidor y nadie lo miraba. Un botón sin palabra parece un fallo del programa.
  assert.equal(botones[0].etiqueta, "GUARDAR");
  assert.equal(botones[1].etiqueta, "VOLVER");
  assert.match(html, /class="boton" data-accion="papel-guardar"/);
  assert.match(html, /class="boton boton-claro" data-accion="papel-ver-todos"/);
});

test("el formulario de papeles no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDelFormulario();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DEL_FORMULARIO),
    ...todosLosTextos(TIPOS_DE_PAPEL),
    "Contratos",
    "Facturas",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Firmar el cuaderno»: los tres pasos, y el campo del fichero con su id
//
// Firmar es lo que hace que el cuaderno valga delante de la administración, así que esta pantalla
// tiene dos cosas que no se pueden romper: que los tres pasos se lean enteros y que **el campo del
// fichero conserve su `id`** (`firma-fichero`), porque es como `app.js` recoge la firma al subirla.
// ---------------------------------------------------------------------------

/** Los textos de la firma, copiados de `textos.py`. */
const TEXTOS_DE_LA_FIRMA = {
  firma: {
    titulo: "Firmar el cuaderno",
    explica:
      "Firmar es lo que hace que el cuaderno valga delante de la administración: queda claro quién lo ha hecho y que nadie lo ha cambiado después.",
    paso_1: "1. Descarga este fichero",
    paso_2: "2. Fírmalo con AutoFirma",
    paso_3: "3. Sube aquí la firma",
    descargar: "DESCARGAR EL FICHERO",
    subir: "SUBIR LA FIRMA",
    instrucciones: "Abre el fichero con AutoFirma, fímalo y guarda la firma.",
    firmado_ok: "Firmado. Ya puedes comprobar que el cuaderno no se ha cambiado.",
    no_puede_firmar:
      "Para firmar hace falta que entres con tu certificado. Es lo que dice quién firma: sin él no se puede saber.",
    huella_no_cuadra:
      "Ese fichero de firma no corresponde a lo que hay ahora en el cuaderno. Vuelve a descargarlo y fírmalo otra vez.",
  },
  acciones: { volver: "VOLVER" },
};

async function htmlDeLaFirma(cambios = {}) {
  const { PantallaFirmar } = await import(
    `../web/react/pantallas/firmar.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaFirmar, {
      textos: structuredClone(TEXTOS_DE_LA_FIRMA),
      nombreDelFichero: "cuaderno_2026.txt",
      ...cambios,
    }),
  );
}

test("los tres pasos salen enteros, con el nombre del fichero", async () => {
  const html = await htmlDeLaFirma();
  assert.match(html, /1\. Descarga este fichero/);
  assert.match(html, /2\. Fírmalo con AutoFirma/);
  assert.match(html, /3\. Sube aquí la firma/);
  // El nombre del fichero va con el primer paso: es lo que el agricultor tiene que reconocer en su
  // carpeta de descargas para no firmar el fichero de otro año.
  assert.match(html, /<p class="pista-campo">cuaderno_2026\.txt<\/p>/);
  assert.match(html, /DOWNLOAD|DESCARGAR EL FICHERO/);
});

test("la pantalla dice en qué estado está la firma, y si aquí se puede firmar", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): antes solo salían los tres pasos, y **el estado no se
  // veía en ninguna parte** —ni que ya esté firmado, ni que la firma se haya quedado vieja porque después se
  // cambió algo—. El mensaje lo compone el servidor; aquí se comprueba que llega a la pantalla.
  const sinFirmar = await htmlDeLaFirma({ estado: "Todavía no has firmado el cuaderno de este año." });
  assert.match(sinFirmar, /class="etiqueta-estado etiqueta-estado-voluntario">Todavía no has firmado/);

  const cambiado = await htmlDeLaFirma({
    estado: "Ojo: este cuaderno se firmó el 15/03/2026, pero después se ha cambiado algo.",
  });
  assert.match(cambiado, /pero después se ha cambiado algo/);

  // Y el aviso de que sin certificado no se puede firmar: sin él, los tres pasos parecen poder terminarse y
  // el último no funciona.
  const sinCertificado = await htmlDeLaFirma({ avisos: [TEXTOS_DE_LA_FIRMA.firma.no_puede_firmar] });
  assert.match(sinCertificado, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  assert.match(sinCertificado, /Para firmar hace falta que entres con tu certificado\./);
  assert.doesNotMatch(await htmlDeLaFirma(), /class="tarjeta-aviso"/);
});

test("el campo del fichero conserva el id con el que el programa lo lee", async () => {
  const html = await htmlDeLaFirma();
  assert.match(
    html,
    /<label for="firma-fichero">SUBIR LA FIRMA<\/label>/,
    "el campo se ha quedado sin etiqueta o sin su id",
  );
  assert.match(html, /<input id="firma-fichero" type="file"\/>/, "no se puede elegir la firma");
});

test("el aviso de firmado solo sale cuando se acaba de firmar", async () => {
  const recienFirmado = await htmlDeLaFirma({
    firmado: TEXTOS_DE_LA_FIRMA.firma.firmado_ok,
  });
  assert.match(recienFirmado, /class="aviso"/);
  assert.match(recienFirmado, /Firmado\. Ya puedes comprobar/);
  // Y sin firmar no se dice que esté firmado: sería contradecirse.
  assert.doesNotMatch(await htmlDeLaFirma(), /class="aviso"/);
});

test("si la firma no cuadra, se dice con el aviso de error", async () => {
  const html = await htmlDeLaFirma({ error: TEXTOS_DE_LA_FIRMA.firma.huella_no_cuadra });
  assert.match(html, /class="aviso aviso-error"/);
  assert.match(html, /no corresponde a lo que hay ahora en el cuaderno/);
  assert.doesNotMatch(await htmlDeLaFirma(), /aviso-error/);
});

test("los tres botones están, con su acción", async () => {
  const html = await htmlDeLaFirma();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["firmar-descargar", "firmar-subir", "inicio"]);
  assert.match(html, /data-accion="firmar-descargar"/);
  assert.match(html, /class="boton boton-claro" data-accion="inicio" data-ir="mi_cuaderno"/);
});

test("la pantalla de firmar no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLaFirma({ firmado: TEXTOS_DE_LA_FIRMA.firma.firmado_ok });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_LA_FIRMA),
    "cuaderno_2026.txt",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// El plan de abono: lo previsto, lo aplicado y lo que queda
//
// Es la sección que la Junta llama «Recomendación de nutrientes», y lo que de verdad sirve de ella
// es que se vea cuando el agricultor **lleva más de lo previsto**: abonar de más tiene consecuencias
// en el agua y en la PAC. Dos cosas se conservan a propósito y se comprueban aquí: el aviso en rojo
// cuando se ha pasado, y que **no se pinte nada que no se sepa** (ni un «no» de relleno ni una fila
// vacía).
// ---------------------------------------------------------------------------

/** Los textos del plan, copiados de `textos.py`. */
const TEXTOS_DEL_PLAN = {
  plan: {
    titulo: "El plan de abono del año",
    explica:
      "Aquí apuntas lo que tenías previsto abonar y ves lo que llevas echado. Si te pasas, te avisa.",
    precedente: "El año anterior había",
    herramienta_pregunta: "Lo hice con una herramienta",
    sin_planes: "Todavía no tienes ningún plan de abono apuntado este año.",
    hacer: "HACER EL PLAN DE ABONO",
    se_basa_en: "Este plan se apoya en un análisis:",
    sin_analisis:
      "Este plan no se apoya en ningún análisis. Se puede hacer igual, pero con un análisis se afina más.",
    tabla_previsto: "Tenías previsto",
    tabla_aplicado: "Llevas",
    tabla_queda: "Te queda",
    tabla_pasado: "Pasado",
    kilos_por_hectarea: "kilos por hectárea",
    plan_de: "Plan de {cultivo}",
    pasado: "Ojo: llevas más de lo que tenías previsto. Míralo antes de seguir abonando.",
    // El veredicto de cada plan y cuándo es obligatorio (ronda 90, del diseño de Stitch).
    en_regla: "En regla",
    alerta_exceso: "Alerta: exceso",
    obligatorio:
      "El plan de abono es obligatorio desde el 1 de septiembre de 2026. En regadío lo es desde el 1 de enero de 2026, si el cultivo se sembró o se plantó entre marzo y junio.",
  },
  acciones: { volver: "VOLVER", si: "Sí", no: "No" },
};

/** Un plan de los que prepara `app.js`: todo contado y escrito. */
function planDePrueba(cambios = {}) {
  return {
    titulo: "Plan de Trigo blando",
    detalle: "El Prado · 2,43 ha · kilos por hectárea",
    precedente: "El año anterior había: Cebada",
    herramienta: "Lo hice con una herramienta: Sí",
    mensaje: "Vas bien: llevas 60,0 de los 100,0 previstos.",
    se_ha_pasado: false,
    estado: { texto: "En regla", tipo: "bien" },
    cabecera: "Tenías previsto · Llevas · Te queda",
    filas: [
      { nombre: "N", texto: "100,0 · 60,0 · 40,0" },
      { nombre: "P", texto: "40,0 · 10,0 · 30,0" },
    ],
    analisis: {
      titulo: "Análisis de La tierra de El Prado · 14/02/2026",
      numeros: [["Materia orgánica", "1,80 %"]],
    },
    ...cambios,
  };
}

async function htmlDePlanes(cambios = {}) {
  const { PantallaPlanes } = await import(
    `../web/react/pantallas/planes.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaPlanes, {
      textos: structuredClone(TEXTOS_DEL_PLAN),
      planes: [planDePrueba()],
      ...cambios,
    }),
  );
}

test("el plan enseña previsto, aplicado y lo que queda", async () => {
  const html = await htmlDePlanes();
  assert.match(html, /Plan de Trigo blando/, "no dice de qué cultivo");
  assert.match(html, /El Prado · 2,43 ha · kilos por hectárea/, "no dice la parcela ni la unidad");
  assert.match(html, /100,0 · 60,0 · 40,0/, "no enseña lo previsto, lo aplicado y lo que queda");
  assert.match(html, /Tenías previsto · Llevas · Te queda/, "no dice qué es cada una de las tres columnas");
});

test("el plan dice qué había el año anterior y si se usó una herramienta", async () => {
  // Las dos cosas las pide el anexo II y las dos llegan ya preparadas: el cultivo anterior lo
  // **calcula** el servidor (el agricultor no tiene por qué acordarse) y la herramienta es un sí o
  // un no.
  const html = await htmlDePlanes();
  assert.match(html, /El año anterior había: Cebada/);
  assert.match(html, /Lo hice con una herramienta: Sí/);
});

test("si no se sabe un dato, no se enseña nada", async () => {
  // Ni un «no» de relleno ni una fila con un hueco: lo que no se sabe, no se dice.
  const html = await htmlDePlanes({
    planes: [planDePrueba({ precedente: "", herramienta: "" })],
  });
  assert.doesNotMatch(html, /El año anterior había/, "dice el cultivo anterior sin saberlo");
  assert.doesNotMatch(html, /Lo hice con una herramienta:/, "dice si usó herramienta sin saberlo");
});

test("si se ha pasado, el aviso va en rojo", async () => {
  const pasado = await htmlDePlanes({
    planes: [
      planDePrueba({
        se_ha_pasado: true,
        mensaje: "Ojo: llevas más de lo que tenías previsto. Míralo antes de seguir abonando.",
      }),
    ],
  });
  assert.match(pasado, /class="aviso aviso-error"/);
  assert.match(pasado, /llevas más de lo que tenías previsto/);
  // Y si va bien, el aviso va normal: no se pone en rojo todo.
  assert.doesNotMatch(await htmlDePlanes(), /aviso-error/);
});

test("el plan dice en qué análisis se apoya, con sus números", async () => {
  const html = await htmlDePlanes();
  assert.match(html, /Este plan se apoya en un análisis:/);
  assert.match(html, /Análisis de La tierra de El Prado · 14\/02\/2026/);
  assert.match(html, /Materia orgánica/);
  // Y sin análisis se dice, en vez de dejar el hueco: no apoyarse en un análisis es una decisión.
  const sinAnalisis = await htmlDePlanes({ planes: [planDePrueba({ analisis: null })] });
  assert.match(sinAnalisis, /no se apoya en ningún análisis/);
});

test("sin ningún plan se dice, y se ofrece hacerlo", async () => {
  const vacia = await htmlDePlanes({ planes: [] });
  assert.match(vacia, /class="aviso"/);
  assert.match(vacia, /Todavía no tienes ningún plan de abono/);
  assert.doesNotMatch(vacia, /<h2>/, "ha dibujado el plan de un año que no existe");
});

test("los dos botones de abajo están, con su acción", async () => {
  const html = await htmlDePlanes();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["plan-hacer", "inicio"]);
  assert.match(html, /data-accion="inicio" data-ir="mi_cuaderno"/);
});

test("cada plan dice en una etiqueta si va bien o si se ha pasado", async () => {
  // Del diseño de Stitch de esta pantalla (ronda 90): «En regla» o «Alerta: exceso». Es la primera pregunta
  // al abrir esto —«¿voy bien?»— y antes había que leerse la tabla entera para contestarla.
  const enRegla = await htmlDePlanes();
  assert.match(enRegla, /class="etiqueta-estado etiqueta-estado-bien">En regla</);

  const pasado = await htmlDePlanes({
    planes: [
      planDePrueba({
        se_ha_pasado: true,
        estado: { texto: "Alerta: exceso", tipo: "mirar" },
        mensaje: "Ojo: llevas más de lo que tenías previsto. Míralo antes de seguir abonando.",
      }),
    ],
  });
  assert.match(pasado, /class="etiqueta-estado etiqueta-estado-mirar">Alerta: exceso</);
});

test("la pantalla dice desde cuándo es obligatorio el plan", async () => {
  // **El texto llevaba desde la ronda 60 en el vocabulario y no lo leía ninguna pantalla.** Es lo que
  // contesta a «¿esto me hace falta?», la primera pregunta de quien entra aquí.
  const html = await htmlDePlanes({ obligatorio: TEXTOS_DEL_PLAN.plan.obligatorio });
  assert.match(html, /<p class="tarjeta-aviso tarjeta-aviso-grande"><span class="tarjeta-aviso-icono"/);
  assert.match(html, /es obligatorio desde el 1 de septiembre de 2026/);
  // Y no se dibuja el hueco si el servidor no lo manda.
  assert.doesNotMatch(await htmlDePlanes(), /tarjeta-aviso/);
});

test("el plan de abono no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDePlanes();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DEL_PLAN),
    ...todosLosTextos(planDePrueba()),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// La pantalla de entrar: la puerta
//
// Es la primera que ve cualquiera, así que aquí lo que se comprueba es lo que no puede fallar: que
// **los seis campos conserven su `id`** (los lee `app.js` al entrar: si uno cambia, el agricultor
// escribe su correo y su clave y no entra, sin saber por qué), que en el modo de registrarse salgan
// los cuatro campos de la finca, y que **siempre haya una forma de entrar que no dependa del
// certificado**.
// ---------------------------------------------------------------------------

/** Los textos de la pantalla de entrar, copiados de `textos.py`. */
const TEXTOS_DE_ENTRAR = {
  pantalla_entrar: {
    titulo: "Mi cuaderno",
    crear: "CREAR MI CUADERNO",
    entrar: "ENTRAR",
    ya_tengo_cuenta: "Ya tengo cuenta",
    primera_vez: "Es mi primera vez",
    como_te_llamas: "¿Cómo te llamas?",
    tu_nif: "Tu NIF",
    tu_pueblo: "¿En qué pueblo está tu finca?",
    tu_provincia: "¿En qué provincia?",
    tu_correo: "Tu correo",
    tu_clave: "Tu clave",
  },
  ayuda: {
    porques: {
      papel_o_digital:
        "Puedes llevar el cuaderno en papel o con este programa: las dos valen. Lo que sí hay que hacer es llevarlo al día.",
    },
  },
  certificado: {
    boton: "ENTRAR CON MI CERTIFICADO",
    pista: "sin escribir la clave",
  },
  acciones: { volver: "VOLVER" },
};

/** La ayuda del campo del NIF, como la prepara `app.js` (con sus rótulos del servidor). */
const AYUDA_DEL_NIF = {
  campo: "explotacion.nif",
  titulo: "Tu NIF",
  que_es: "El número que te identifica en tus papeles.",
  por_que: "Con él se sabe de qué finca son los apuntes.",
  ejemplo: "70922320A",
  si_falta: "Sin NIF no se puede identificar la finca en el cuaderno.",
  rotulos: {
    que_es: "Qué es:",
    por_que: "Por qué te lo piden:",
    ejemplo: "Ejemplo:",
    si_falta: "Si te falta:",
  },
};

async function htmlDeEntrar(cambios = {}) {
  const { PantallaEntrar } = await import(
    `../web/react/pantallas/entrar.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaEntrar, {
      textos: structuredClone(TEXTOS_DE_ENTRAR),
      modo: "entrar",
      provincias: ["Salamanca", "Valladolid"],
      certificado: { configurado: false },
      ayudaDelNif: AYUDA_DEL_NIF,
      ...cambios,
    }),
  );
}

test("al entrar se piden el correo y la clave, con sus ids", async () => {
  const html = await htmlDeEntrar();
  // El contenedor del formulario conserva su `id` (estaba en la pantalla vieja) y después van
  // los dos campos, en este orden.
  assert.deepEqual(idsDe(html), ["formulario", "correo", "clave"]);
  assert.match(html, /<label for="correo">Tu correo<\/label>/);
  // `autoComplete` sale así en el HTML estático de las pruebas (React lo escribe con su nombre de
  // propiedad); en el navegador se convierte en `autocomplete`, que es lo que hace que el móvil
  // ofrezca la clave guardada.
  assert.match(html, /<input id="clave" type="password" autoComplete="current-password"\/>/);
  assert.match(html, /data-accion="entrar" data-modo="entrar"/);
  assert.match(html, /data-accion="cambiar-modo-entrar" data-modo="registro"/);
  // Y los campos de la finca **no** salen al entrar: solo al registrarse.
  assert.doesNotMatch(html, /id="nombre"/, "pide el nombre al entrar");
  assert.doesNotMatch(html, /id="nif"/, "pide el NIF al entrar");
});

test("al registrarse se piden los cuatro datos de la finca, con sus ids", async () => {
  const html = await htmlDeEntrar({ modo: "registro" });
  assert.deepEqual(idsDe(html), [
    "formulario",
    "nombre",
    "nif",
    "municipio",
    "provincia",
    "correo",
    "clave",
  ]);
  assert.match(html, /<option>Salamanca<\/option>/, "no ofrece las provincias del servidor");
  assert.match(html, /data-accion="entrar" data-modo="registro"/);
  assert.match(html, /CREAR MI CUADERNO/);
});

test("la ayuda del NIF sale con sus cuatro rótulos", async () => {
  const html = await htmlDeEntrar({ modo: "registro" });
  assert.match(html, /class="ayuda-campo"/);
  assert.match(html, /<h3>Tu NIF<\/h3>/);
  for (const rotulo of ["Qué es:", "Por qué te lo piden:", "Ejemplo:", "Si te falta:"]) {
    assert.ok(html.includes(rotulo), `falta el rótulo «${rotulo}» de la ayuda del campo`);
  }
  // Y sin ayuda para ese campo, no se dibuja el bloque: un hueco con rótulos vacíos no ayuda.
  const sinAyuda = await htmlDeEntrar({ modo: "registro", ayudaDelNif: null });
  assert.doesNotMatch(sinAyuda, /class="ayuda-campo"/);
});

test("el certificado solo sale si está configurado, y no tapa el correo y la clave", async () => {
  const conCertificado = await htmlDeEntrar({ certificado: { configurado: true } });
  assert.match(conCertificado, /data-accion="entrar-certificado"/);
  assert.match(conCertificado, /ENTRAR CON MI CERTIFICADO/);
  assert.match(conCertificado, /sin escribir la clave/, "no dice para qué sirve ese botón");
  // Los campos y el botón de entrar siguen ahí: siempre hay una forma de entrar sin certificado.
  assert.match(conCertificado, /id="correo"/);
  assert.match(conCertificado, /id="clave"/);
  assert.match(conCertificado, /data-accion="entrar" data-modo="entrar"/);

  // Y sin certificado configurado, el botón no se enseña: un botón que lleva a un error es peor.
  const sinCertificado = await htmlDeEntrar();
  assert.doesNotMatch(sinCertificado, /data-accion="entrar-certificado"/);
});

test("si algo falla al entrar o con el certificado, se dice", async () => {
  const html = await htmlDeEntrar({
    errorEntrar: "Ese correo y esa clave no cuadran. Míralo otra vez.",
    errorCertificado: "El certificado no se ha podido leer.",
  });
  assert.equal((html.match(/aviso aviso-error/g) || []).length, 2);
  assert.match(html, /no cuadran/);
  assert.match(html, /no se ha podido leer/);
  assert.doesNotMatch(await htmlDeEntrar(), /aviso-error/);
});

// ---------------------------------------------------------------------------
// Las facturas: la lista y el alta
//
// La factura es el papel que demuestra la compra, y de ella salen tres cosas: cuánto producto hay
// comprado, el número de factura y la empresa que lo vendió. Dos cosas se conservan a propósito y
// se comprueban aquí: **un total desconocido se enseña como «—» y no como cero** (un cero sería un
// dato inventado), y el **campo del fichero conserva su `id`**, que es como `app.js` coge la foto.
// ---------------------------------------------------------------------------

/** Los textos de las facturas, copiados de `textos.py`. */
const TEXTOS_DE_FACTURAS = {
  facturas: {
    titulo: "Mis facturas",
    explica:
      "Aquí guardas las facturas de lo que compras. Hazle una foto al papel o sube el fichero que te manda el proveedor: el programa lee lo que pone y te lo enseña para que lo confirmes.",
    anadir: "AÑADIR UNA FACTURA",
    que_fichero: "La factura: una foto o el fichero del proveedor",
    // El trato claro (ronda 90, del diseño de Stitch de esta pantalla).
    trato_claro:
      "El programa solo intenta leer el papel. Nada se guarda en el cuaderno hasta que tú lo mires en pantalla y digas que está bien.",
    como_se_hace:
      "Hazle la foto con luz y sin que se doble el papel. Si el proveedor te la manda en un fichero, súbelo tal cual.",
    leer: "LEER LA FACTURA",
    leyendo: "Leyendo la factura…",
    a_mano: "ESCRIBIRLA A MANO",
    volver: "VOLVER A MIS FACTURAS",
    sin_proveedor: "Sin proveedor",
    campo_total: "Total de la factura",
    lineas_titulo: "Líneas",
    // El papel de cada factura y su cuenta (ronda 90, del diseño de Stitch).
    papel_guardado: "Foto del papel guardada",
    ver_fichero: "VER LA FACTURA",
    subir_el_papel: "SUBIR LA FOTO DEL PAPEL",
    sin_fichero: "Esta factura no tiene ni la foto ni el fichero.",
    cuantas_uno: "1 factura guardada",
    cuantas: "{cuantas} facturas guardadas",
    sin_facturas: "Todavía no has subido ninguna factura.",
    sin_facturas_pista: "Empieza por la última que tengas a mano.",
    avisos_titulo: "Lo que se puede leer y lo que no",
    guardada: "Factura guardada.",
    guardada_pista:
      "Ya cuenta para saber cuánto producto tienes comprado. La verás en «lo que tengo en el almacén».",
    ver_almacen: "VER LO QUE TENGO EN EL ALMACÉN",
  },
  acciones: { volver: "VOLVER" },
};

/** Una factura de las que prepara `app.js`: todo contado y escrito. */
function facturaDePrueba(cambios = {}) {
  return {
    proveedor: "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
    detalle: "2026/00123 · 15/03/2026",
    total: "980,10 €",
    lineas: "1",
    tiene_fichero: true,
    ...cambios,
  };
}

async function htmlDeFacturas(cambios = {}) {
  const { PantallaFacturas } = await import(
    `../web/react/pantallas/facturas.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaFacturas, {
      textos: structuredClone(TEXTOS_DE_FACTURAS),
      facturas: [facturaDePrueba()],
      ...cambios,
    }),
  );
}

async function htmlDeNuevaFactura(cambios = {}) {
  const { PantallaNuevaFactura } = await import(
    `../web/react/pantallas/nueva_factura.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaNuevaFactura, {
      textos: structuredClone(TEXTOS_DE_FACTURAS),
      ...cambios,
    }),
  );
}

test("las facturas guardadas salen con su proveedor, su número y su total", async () => {
  const html = await htmlDeFacturas();
  assert.match(html, /Mis facturas/);
  assert.match(html, /COOPERATIVA AGRICOLA DE PEÑARANDA S\.C\.L\./);
  assert.match(html, /2026\/00123 · 15\/03\/2026/, "no enseña el número y la fecha juntos");
  assert.match(html, /980,10 €/, "no enseña el total");
  assert.match(html, /<dt>Líneas<\/dt><dd>1<\/dd>/, "no dice cuántas líneas trae");
});

test("sin facturas se dice, en vez de dejar la lista vacía", async () => {
  const vacia = await htmlDeFacturas({ facturas: [] });
  assert.match(vacia, /class="aviso"/);
  assert.match(vacia, /Todavía no has subido ninguna factura/);
  assert.doesNotMatch(vacia, /<ul class="lista">/, "ha dibujado una lista sin nada dentro");
});

test("el aviso del lector sale cuando lo hay", async () => {
  // Es donde el agricultor entiende por qué una factura se leyó mal.
  const conNota = await htmlDeFacturas({ lector: "Leo las facturas de texto y las fotos claras." });
  assert.match(conNota, /Lo que se puede leer y lo que no/);
  assert.match(conNota, /Leo las facturas de texto y las fotos claras/);
  assert.doesNotMatch(await htmlDeFacturas(), /Lo que se puede leer y lo que no/);
});

test("la confirmación de guardada lleva al almacén y a la lista", async () => {
  const html = await htmlDeFacturas({ guardada: "si" });
  assert.match(html, /Factura guardada\./);
  assert.match(html, /Ya cuenta para saber cuánto producto tienes comprado/);
  assert.match(html, /data-accion="cesta-ver"/);
  assert.match(html, /data-accion="facturas-abrir"/);
  // Y no se enseña la lista debajo: sería contradictorio.
  assert.doesNotMatch(html, /<ul class="lista">/);
});

test("los dos botones de la lista están, con su acción", async () => {
  const html = await htmlDeFacturas();
  const acciones = botonesDe(html)
    .map((boton) => boton.accion)
    // El botón del papel de cada factura (ronda 90) se comprueba en su propia prueba: aquí se mira que
    // los dos botones de abajo sigan estando.
    .filter((accion) => accion !== "factura-papel-ver" && accion !== "factura-papel-subir");
  assert.deepEqual(acciones, ["factura-nueva", "ir-inicio"]);
});

test("cada factura dice si tiene su papel, y ofrece verlo o subirlo", async () => {
  // **Esto faltaba entero** (diseño de Stitch de esta pantalla, ronda 90): el servidor sabía desde la
  // ronda 40 si la factura tenía su papel (`tiene_fichero`) y los dos caminos de verlo y subirlo
  // (`GET/POST /api/facturas/{id}/fichero`), y el texto del botón estaba escrito… pero **ninguna
  // pantalla lo pedía**, así que una factura escrita a mano se quedaba sin papel para siempre. Y el papel
  // es justo lo que se pide en una inspección.
  const conPapel = await htmlDeFacturas({
    facturas: [facturaDePrueba({ id: 5, tiene_fichero: true })],
  });
  assert.match(conPapel, /Foto del papel guardada/);
  assert.match(conPapel, /class="boton boton-claro" data-accion="factura-papel-ver" data-id="5"/);
  assert.doesNotMatch(conPapel, /data-accion="factura-papel-subir"/, "pide subir un papel que ya tiene");

  const sinPapel = await htmlDeFacturas({
    facturas: [facturaDePrueba({ id: 7, tiene_fichero: false })],
  });
  assert.match(sinPapel, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  assert.match(sinPapel, /Esta factura no tiene ni la foto ni el fichero\./);
  assert.match(sinPapel, /data-accion="factura-papel-subir" data-id="7"/);
  // Y el campo del fichero lleva su `id`, que es como `app.js` lee el papel elegido.
  assert.match(sinPapel, /<input type="file" id="factura-papel-7" class="oculto"\/>/);
});

test("la lista dice cuántas facturas hay", async () => {
  // Como en «mis cosas» y en el almacén (ronda 84): la cuenta va en su línea, en singular o en plural, y
  // la frase la decide el servidor con `con_cuenta`.
  const html = await htmlDeFacturas({ resumen: "1 factura guardada" });
  assert.match(html, /<p class="cuantas">1 factura guardada<\/p>/);
  // Sin facturas no se dice ningún número: la frase del almacén vacío ya lo cuenta.
  const vacia = await htmlDeFacturas({ facturas: [], resumen: "3 facturas guardadas" });
  assert.doesNotMatch(vacia, /class="cuantas"/, "dice un número con la lista vacía");
});

test("el alta pide el fichero con su id y ofrece las tres salidas", async () => {
  const html = await htmlDeNuevaFactura();
  // **El fichero va en una caja que se toca entera** (diseño de Stitch de esta pantalla, ronda 90): el campo
  // es el mismo, con su `id` (es como `app.js` lo lee), pero oculto dentro de la etiqueta, que es lo que se ve
  // y lo que se toca. Un campo de fichero pelado no se ve como algo que se toca.
  assert.match(html, /<label class="caja-fichero" for="factura-fichero">/);
  assert.match(html, /<input id="factura-fichero" class="oculto" type="file" accept="\.pdf,image\/\*"\/>/);
  assert.match(html, /La factura: una foto o el fichero del proveedor/);
  assert.match(html, /data-accion="factura-leer"/);
  assert.match(html, /data-accion="factura-mano"/);
  assert.match(html, /data-accion="facturas-abrir"/);
  // Y se dice cómo hacer la foto: sin eso, el agricultor no sabe qué subir.
  assert.match(html, /Hazle la foto con luz/);
  // Y el trato claro: nada se guarda hasta que él lo mire.
  assert.match(html, /Nada se guarda en el cuaderno hasta que tú lo mires/);
});

test("mientras se lee, el botón lo dice y no se puede volver a pulsar", async () => {
  // Sin esto, el agricultor puede mandar la misma factura dos veces.
  const leyendo = await htmlDeNuevaFactura({ leyendo: true });
  assert.match(leyendo, /Leyendo la factura…/);
  assert.match(leyendo, /data-accion="factura-leer" disabled=""/, "el botón sigue disponible");
  const parado = await htmlDeNuevaFactura();
  assert.match(parado, /LEER LA FACTURA/);
  assert.doesNotMatch(parado, /disabled/, "el botón no se puede pulsar sin estar leyendo");
});

test("si algo falla al leer, se dice con el aviso de error", async () => {
  const html = await htmlDeNuevaFactura({
    error: "No se ha podido leer la factura. Prueba otra vez o escríbela a mano.",
  });
  assert.match(html, /class="aviso aviso-error"/);
  assert.match(html, /Prueba otra vez o escríbela a mano/);
  assert.doesNotMatch(await htmlDeNuevaFactura(), /aviso-error/);
});

// ---------------------------------------------------------------------------
// La interpretación de una factura leída: lo leído es una propuesta, y se confirma
//
// **Es la pantalla que hace que leer una factura se pueda usar sin jugarse un dato del cuaderno.** Si
// esto fuera un «ya está guardado», el programa estaría metiendo en el cuaderno lo que ha adivinado
// de una foto. Por eso lo que se comprueba aquí es: que **todo lo leído esté en un campo editable**,
// que los `id` de esos campos sean los que lee `app.js` al guardar, que el aviso de la línea que no
// cuadra salga **solo** en esa línea, y que de dónde sale la lectura se diga.
// ---------------------------------------------------------------------------

/** Un dato leído, tal y como lo prepara `app.js`: campo con su etiqueta y su valor. */
function campoDePrueba(id, etiqueta, valor, tipo) {
  return { id, etiqueta, valor, tipo };
}

/** Lo leído de una factura, ya preparado como lo manda `app.js`. */
function leidaDePrueba(cambios = {}) {
  return {
    de_donde: "Leída de: Una foto",
    avisos: ["Esto lo he leído de una imagen y el lector solo tiene el idioma inglés."],
    cabecera: [
      campoDePrueba("factura-proveedor", "¿Quién te la hizo?", "COOPERATIVA AGRICOLA", "text"),
      campoDePrueba("factura-proveedor-nif", "Su NIF", "F37012345", "text"),
      campoDePrueba("factura-numero", "¿Qué número tiene la factura?", "2026/00123", "text"),
      campoDePrueba("factura-fecha", "¿De qué fecha es?", "2026-03-15", "date"),
      campoDePrueba("factura-base", "Base imponible", "810", "text"),
      campoDePrueba("factura-iva", "Cuota de IVA", "170,1", "text"),
      campoDePrueba("factura-tipo-iva", "Tipo de IVA", "21", "text"),
      campoDePrueba("factura-total", "Total de la factura", "980,1", "text"),
    ],
    lineas: [
      {
        descripcion: "GLIFOSATO 36% SL 20 L",
        cantidad: "2",
        unidad: "ud",
        precio: "85",
        importe: "170",
        opciones: [
          { valor: "", texto: "No es de la cesta", elegido: false },
          { valor: "nuevo", texto: "Es un producto nuevo, apúntalo", elegido: false },
          { valor: "1", texto: "Glifosato 36 SL", elegido: true },
        ],
        no_cuadra: false,
        sugerida: "Es este: Glifosato 36 SL, por el nombre",
        registro: "Número de registro que viene en la factura: 24.123",
      },
      {
        descripcion: "NITRATO AMONICO 33,5%",
        cantidad: "1000",
        unidad: "kg",
        precio: "0,45",
        importe: "999",
        opciones: [
          { valor: "", texto: "No es de la cesta", elegido: true },
          { valor: "nuevo", texto: "Es un producto nuevo, apúntalo", elegido: false },
        ],
        no_cuadra: true,
        sugerida: "",
        registro: "",
      },
    ],
    ...cambios,
  };
}

/** Los textos de la interpretación, copiados de `textos.py`. */
const TEXTOS_DE_LA_INTERPRETACION = {
  facturas: {
    interpretacion_titulo: "Esto es lo que he leído",
    interpretacion_pista:
      "Míralo y corrígelo antes de guardar. Lo que has leído de una foto puede traer erratas.",
    de_donde_sale_la_lectura: "Leída de",
    avisos_titulo: "Conviene que mires esto",
    lineas_titulo: "Lo que has comprado",
    lineas_pista: "Cada línea es un producto. Si alguna no te cuadra, corrígela o bórrala antes de guardar.",
    linea_descripcion: "Qué es",
    linea_cantidad: "Cuánto",
    linea_unidad: "En qué se mide",
    linea_precio: "A cómo",
    linea_importe: "Importe",
    linea_producto: "¿Es alguno de los tuyos?",
    linea_no_cuadra: "La cuenta no cuadra: mira la cantidad, el precio y el importe",
    // La etiqueta de la línea que hay que revisar (ronda 90).
    revisar_numeros: "Revisar números",
    confirmar: "SÍ, GUARDAR ESTA FACTURA",
    guardando: "Guardando la factura…",
    volver: "VOLVER",
    // Corregir una factura que ya está guardada (ronda 93): la misma pantalla, con otros tres textos.
    corregir_titulo: "Esto es lo que tienes guardado",
    corregir_pista: "Cambia lo que esté mal y guarda. Lo que había antes se queda apuntado en el cuaderno.",
    corregir_confirmar: "SÍ, GUARDAR LOS CAMBIOS",
    corregir_volver: "VOLVER A MIS FACTURAS",
  },
  acciones: { volver: "VOLVER" },
};

async function htmlDeLaInterpretacion(cambios = {}) {
  const { PantallaInterpretacionDeLaFactura } = await import(
    `../web/react/pantallas/interpretacion_factura.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaInterpretacionDeLaFactura, {
      textos: structuredClone(TEXTOS_DE_LA_INTERPRETACION),
      leida: leidaDePrueba(),
      ...cambios,
    }),
  );
}

test("todo lo leído sale en un campo editable, con los id que lee el programa", async () => {
  const html = await htmlDeLaInterpretacion();
  assert.match(html, /Esto es lo que he leído/);
  // Los ocho campos de la cabecera, con su `id` y con lo leído dentro.
  for (const id of [
    "factura-proveedor",
    "factura-proveedor-nif",
    "factura-numero",
    "factura-fecha",
    "factura-base",
    "factura-iva",
    "factura-tipo-iva",
    "factura-total",
  ]) {
    assert.ok(html.includes(`id="${id}"`), `falta el campo ${id}`);
  }
  assert.match(html, /id="factura-proveedor"[^>]*value="COOPERATIVA AGRICOLA"/);
  assert.match(html, /id="factura-total"[^>]*value="980,1"/);
  // Y los seis de cada línea, con el número de línea dentro del `id`.
  for (const sufijo of ["descripcion", "cantidad", "unidad", "precio", "importe"]) {
    assert.ok(html.includes(`id="factura-1-${sufijo}"`), `falta el campo factura-1-${sufijo}`);
  }
  assert.ok(html.includes('id="factura-1-producto"'), "falta el desplegable del producto");
  assert.match(html, /id="factura-0-descripcion"[^>]*value="GLIFOSATO 36% SL 20 L"/);
});

test("el aviso de la línea que no cuadra sale solo en esa línea", async () => {
  // Si saliera en todas, el agricultor dejaría de mirarlo: es la mitad del valor de esta pantalla.
  const html = await htmlDeLaInterpretacion();
  const avisos = html.match(/La cuenta no cuadra/g) || [];
  assert.equal(avisos.length, 1, `el aviso sale ${avisos.length} veces`);
  // Y va después de la línea que no cuadra (la segunda), no antes.
  const posicionAviso = html.indexOf("La cuenta no cuadra");
  const posicionSegunda = html.indexOf("NITRATO AMONICO");
  assert.ok(posicionSegunda > 0 && posicionAviso > posicionSegunda, "el aviso no está en su línea");
  // **Y desde la ronda 90 esa línea lleva su etiqueta arriba** (diseño de Stitch): con tres o cuatro líneas,
  // el aviso del final no dice cuál es sin leer la pantalla entera.
  assert.match(html, /class="etiqueta-estado etiqueta-estado-mirar">Revisar números</);
  assert.equal(
    (html.match(/Revisar números/g) || []).length,
    1,
    "la etiqueta de «revisar números» sale en líneas que cuadran",
  );
  // Y el aviso va en su franja, con su señal.
  assert.match(html, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
});

test("el producto sugerido sale elegido, y se dice por qué se sugiere", async () => {
  const html = await htmlDeLaInterpretacion();
  assert.match(html, /<option value="1" selected="">Glifosato 36 SL<\/option>/);
  assert.match(html, /Es este: Glifosato 36 SL, por el nombre/);
  // Y la línea que no tiene producto sugerido no se inventa uno: se queda en «no es de la cesta».
  assert.match(html, /<option value="" selected="">No es de la cesta<\/option>/);
  assert.match(html, /Número de registro que viene en la factura: 24\.123/);
});

test("se dice de dónde sale la lectura y los avisos que haya", async () => {
  const html = await htmlDeLaInterpretacion();
  assert.match(html, /Leída de: Una foto/);
  assert.match(html, /Conviene que mires esto/);
  assert.match(html, /el lector solo tiene el idioma inglés/);
  // Sin avisos no se dibuja el bloque: un hueco con un título y nada debajo no avisa de nada.
  const sinAvisos = await htmlDeLaInterpretacion({
    leida: leidaDePrueba({ avisos: [], de_donde: "" }),
  });
  assert.doesNotMatch(sinAvisos, /Conviene que mires esto/);
  assert.doesNotMatch(sinAvisos, /Leída de:/);
});

test("mientras guarda, el botón lo dice y no se puede volver a pulsar", async () => {
  // Sin esto, la misma factura se puede guardar dos veces.
  const guardando = await htmlDeLaInterpretacion({
    guardando: true,
    error: "No se ha podido guardar la factura.",
  });
  assert.match(guardando, /Guardando la factura…/);
  assert.match(guardando, /data-accion="factura-guardar" disabled=""/);
  assert.match(guardando, /class="aviso aviso-error"/, "no enseña el error al guardar");
  const parado = await htmlDeLaInterpretacion();
  assert.match(parado, /SÍ, GUARDAR ESTA FACTURA/);
  assert.doesNotMatch(parado, /disabled/, "el botón no se puede pulsar sin estar guardando");
});

test("los dos botones están, con su acción", async () => {
  const html = await htmlDeLaInterpretacion();
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["factura-guardar", "factura-nueva"]);
});

test("corregir una factura usa la misma pantalla, con su título y su vuelta a la lista", async () => {
  // **Ronda 93.** No hay pantalla nueva para corregir una factura, y es a propósito: corregirla es el
  // mismo trabajo que confirmar lo que se ha leído (mirar el papel y arreglar lo que esté mal). Lo que
  // cambia son tres textos y el destino del botón de volver, y eso es lo que se comprueba aquí.
  const html = await htmlDeLaInterpretacion({ corrigiendo: true });
  assert.match(html, /Esto es lo que tienes guardado/, "no dice que está enseñando lo guardado");
  assert.doesNotMatch(html, /Esto es lo que he leído/, "sigue diciendo que ha leído algo");
  assert.match(html, /Lo que había antes se queda apuntado en el cuaderno/);
  assert.match(html, /SÍ, GUARDAR LOS CAMBIOS/);
  assert.doesNotMatch(html, /SÍ, GUARDAR ESTA FACTURA/, "invita a guardar una factura nueva");
  // Y volver lleva **a la lista de facturas** (de donde se salió), no a «añadir una factura».
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["factura-guardar", "facturas-abrir"]);
  assert.match(html, /VOLVER A MIS FACTURAS/);
  // Los campos y las líneas se pintan igual: lo que se corrige es lo mismo que se confirma.
  for (const id of ["factura-proveedor", "factura-total", "factura-0-descripcion"]) {
    assert.ok(html.includes(`id="${id}"`), `al corregir falta el campo ${id}`);
  }
});

test("la interpretación no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLaInterpretacion({ error: "No se ha podido guardar la factura." });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_LA_INTERPRETACION),
    ...todosLosTextos(leidaDePrueba()),
    "No se ha podido guardar la factura.",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// Los años del cuaderno (ronda 93): la pantalla nueva
//
// Es la última cosa que faltaba por poder tocar desde la pantalla, y lo que enseña tiene que quedar claro
// sin que nadie lo explique: **en qué año está apuntando**, cuáles tiene, cuánto hay dentro de cada uno y
// por qué a uno no se le puede dar a BORRAR. Lo que se comprueba aquí es la pantalla; el cableado (de
// dónde salen los números y a dónde van los botones) está en `interfaz.test.js`.
// ---------------------------------------------------------------------------

/** Los textos de los años del cuaderno, copiados de `textos.py`. */
const TEXTOS_DE_LAS_CAMPANAS = {
  campanas: {
    titulo: "Los años de mi cuaderno",
    explica: "Tu cuaderno se lleva por años: lo que apuntas va al año en el que estás.",
    rotulo: "Año del cuaderno",
    el_que_llevo: "Estás apuntando en este",
    cerrado: "Año cerrado",
    abierto: "Año abierto",
    empieza: "Empieza",
    termina: "Termina",
    dentro_uno: "Tiene 1 cosa apuntada dentro",
    dentro_varios: "Tiene {cuantos} cosas apuntadas dentro",
    vacio: "No tiene nada apuntado",
    no_se_puede_quitar: "Aquí dentro hay cosas apuntadas: primero quítalas y después podrás quitar el año.",
    anadir: "EMPEZAR UN AÑO NUEVO",
    anadir_pista: "Cuando empiece el año que viene, hazlo aquí: lo que apuntes irá a ese año.",
    sin_campanas: "Todavía no hay ningún año en tu cuaderno.",
  },
  acciones: { volver: "VOLVER" },
  corregir: { boton: "CORREGIR", borrar: "BORRAR" },
};

/** Un año del cuaderno, como lo prepara `app.js`. */
function campanaDePrueba(cambios = {}) {
  return {
    id: 1,
    anio: "2026",
    desde: "01/09/2025",
    hasta: "31/08/2026",
    es_la_que_llevo: false,
    cerrada: false,
    dentro: "Tiene 42 cosas apuntadas dentro",
    se_puede_quitar: false,
    acciones: [
      { etiqueta: "CORREGIR", accion: "cosa-corregir", datos: { tipo: "campana", id: 1 } },
      { etiqueta: "BORRAR", accion: "cosa-borrar", datos: { tipo: "campana", id: 1 }, deshabilitado: true },
    ],
    ...cambios,
  };
}

async function htmlDeLasCampanas(cambios = {}) {
  const { PantallaCampanas } = await import(
    `../web/react/pantallas/campanas.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaCampanas, {
      textos: structuredClone(TEXTOS_DE_LAS_CAMPANAS),
      campanas: [campanaDePrueba()],
      ...cambios,
    }),
  );
}

test("cada año sale con su año, sus fechas y lo que tiene dentro", async () => {
  const html = await htmlDeLasCampanas({
    campanas: [
      campanaDePrueba(),
      campanaDePrueba({
        id: 3,
        anio: "2024",
        desde: "01/01/2024",
        hasta: "31/12/2024",
        cerrada: true,
        dentro: "No tiene nada apuntado",
        se_puede_quitar: true,
        acciones: [
          { etiqueta: "CORREGIR", accion: "cosa-corregir", datos: { tipo: "campana", id: 3 } },
          { etiqueta: "BORRAR", accion: "cosa-borrar", datos: { tipo: "campana", id: 3 } },
        ],
      }),
    ],
  });
  assert.match(html, /Los años de mi cuaderno/);
  // El rótulo de arriba y el año, que es lo que se viene a buscar (diseño de Stitch de esta pantalla).
  assert.equal((html.match(/Año del cuaderno/g) || []).length, 2, "falta el rótulo de alguna ficha");
  assert.match(html, /<strong class="campana-anio">2026<\/strong>/);
  assert.match(html, /<strong class="campana-anio">2024<\/strong>/);
  // Las dos fechas, cada una con su nombre delante: un «01/09/2025» suelto no dice qué es.
  assert.match(html, /Empieza<\/span><span class="tarjeta-fila-valor">01\/09\/2025/);
  assert.match(html, /Termina<\/span><span class="tarjeta-fila-valor">31\/08\/2026/);
  // Y cuánto hay dentro, que es lo que explica por qué un año no se puede quitar.
  assert.match(html, /Tiene 42 cosas apuntadas dentro/);
  assert.match(html, /No tiene nada apuntado/);
  assert.match(html, /Año cerrado/);
});

test("el año que estás llevando se dice, y el que no se puede quitar lo explica", async () => {
  // Las dos cosas que no se pueden deducir de la pantalla: **en cuál está apuntando** (que es lo que se
  // viene a mirar) y **por qué** a un año no se le puede dar a BORRAR.
  const html = await htmlDeLasCampanas({
    campanas: [campanaDePrueba({ es_la_que_llevo: true })],
  });
  assert.match(
    html,
    /class="etiqueta-estado etiqueta-estado-mirar">Estás apuntando en este/,
    "no se dice en qué año está apuntando",
  );
  assert.match(html, /Aquí dentro hay cosas apuntadas: primero quítalas y después podrás quitar el año/);
  // Y el aviso va en su franja, con su señal, como todos los de la aplicación.
  assert.match(html, /<p class="tarjeta-aviso"><span class="tarjeta-aviso-icono"/);
  // **El BORRAR de un año con cosas dentro sale apagado** (diseño de Stitch): el agricultor lo ve antes de
  // pulsarlo, en vez de descubrir al pulsar que el programa no le deja.
  assert.match(html, /data-accion="cosa-borrar"[^>]*disabled=""/);
  // Y el de un año vacío no: ahí sí se puede quitar.
  const vacio = await htmlDeLasCampanas({
    campanas: [
      campanaDePrueba({
        dentro: "No tiene nada apuntado",
        se_puede_quitar: true,
        acciones: [
          { etiqueta: "CORREGIR", accion: "cosa-corregir", datos: { tipo: "campana", id: 3 } },
          { etiqueta: "BORRAR", accion: "cosa-borrar", datos: { tipo: "campana", id: 3 } },
        ],
      }),
    ],
  });
  assert.doesNotMatch(vacio, /disabled/, "un año vacío no se puede quitar");
  assert.doesNotMatch(vacio, /primero quítalas y después/, "avisa de algo que no pasa");
});

test("sin años se dice, y siempre se puede empezar uno nuevo", async () => {
  // La pantalla tiene que funcionar también **vacía**: es el estado de una finca recién creada, y una
  // pantalla en blanco no dice si no hay años o si el programa está roto.
  const html = await htmlDeLasCampanas({ campanas: [] });
  assert.match(html, /Todavía no hay ningún año en tu cuaderno/);
  assert.match(html, /data-accion="campana-nueva"/);
  assert.match(html, /EMPEZAR UN AÑO NUEVO/);
  assert.match(html, /Cuando empiece el año que viene, hazlo aquí/);
});

test("los botones de cada año llevan su acción y su año", async () => {
  const html = await htmlDeLasCampanas({
    campanas: [
      campanaDePrueba({
        id: 7,
        anio: "2027",
        dentro: "No tiene nada apuntado",
        se_puede_quitar: true,
        acciones: [
          { etiqueta: "CORREGIR", accion: "cosa-corregir", datos: { tipo: "campana", id: 7 } },
          { etiqueta: "BORRAR", accion: "cosa-borrar", datos: { tipo: "campana", id: 7 } },
        ],
      }),
    ],
  });
  const acciones = botonesDe(html).map((boton) => boton.accion);
  // Los dos de la ficha, el de empezar un año y el de volver: sin el `data-id` del año, `app.js` no sabe
  // sobre cuál de ellos se ha pulsado (y con dos años en pantalla eso es borrar el que no es).
  assert.deepEqual(acciones, [
    "cosa-corregir",
    "cosa-borrar",
    "campana-nueva",
    "inicio",
  ]);
  assert.match(html, /data-accion="cosa-corregir" data-tipo="campana" data-id="7"/);
  assert.match(html, /data-accion="cosa-borrar" data-tipo="campana" data-id="7"/);
});

test("los años salen en tabla en el ordenador y en fichas en el móvil", async () => {
  // **30/09/2026.** La misma lista, dos formas, en el mismo HTML: el CSS enseña la que toca. Lo que se
  // comprueba aquí es que la tabla se pinta cuando `app.js` la manda y que las fichas siguen estando para
  // el móvil (si desaparecieran, el agricultor se quedaría sin la pantalla en el campo).
  const conTabla = await htmlDeLasCampanas({
    tabla: {
      clave: "anos",
      etiqueta: "Los años de tu cuaderno, en una tabla",
      columnas: [{ texto: "Año", campo: "anio_numero", clase: "tabla-numero", ordenada: true }],
      filas: [{ celdas: [{ texto: "2026", clase: "tabla-numero" }], acciones: [] }],
      resumen: "1 año en tu cuaderno",
    },
  });
  assert.match(conTabla, /<div class="solo-escritorio"><table class="tabla"/);
  assert.match(conTabla, /<ul class="lista solo-movil">/);
  assert.match(conTabla, /1 año en tu cuaderno/);
  // Y sin tabla (una pantalla que no la mande), no se pinta un cuadro vacío y las fichas siguen ahí.
  const sinTabla = await htmlDeLasCampanas();
  assert.doesNotMatch(sinTabla, /solo-escritorio/);
  assert.match(sinTabla, /<ul class="lista solo-movil">/);
});

test("la pantalla de los años no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLasCampanas({
    campanas: [campanaDePrueba({ es_la_que_llevo: true })],
    error: "No se han podido cargar tus años.",
  });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_LAS_CAMPANAS),
    ...todosLosTextos(campanaDePrueba({ es_la_que_llevo: true })),
    "No se han podido cargar tus años.",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

test("las facturas salen en tabla en el ordenador y en fichas en el móvil", async () => {
  // **30/09/2026**: la misma lista, dos formas. La tabla es lo que permite cuadrar el año de un vistazo
  // (fecha, proveedor, base, IVA, total y si está el papel) y las fichas siguen para el móvil.
  const conTabla = await htmlDeFacturas({
    tabla: {
      clave: "facturas",
      etiqueta: "Tus facturas, en una tabla",
      columnas: [{ texto: "Total", campo: "total_numero", clase: "tabla-numero", ordenada: true }],
      filas: [{ celdas: [{ texto: "750,20 €" }], acciones: [] }],
      resumen: "1 factura · 750,20 €",
    },
  });
  assert.match(conTabla, /<div class="solo-escritorio"><table class="tabla"/);
  assert.match(conTabla, /<ul class="lista solo-movil">/);
  assert.match(conTabla, /1 factura · 750,20 €/);
  const sinTabla = await htmlDeFacturas();
  assert.doesNotMatch(sinTabla, /solo-escritorio/);
  assert.match(sinTabla, /<ul class="lista solo-movil">/);
});

test("los números de las facturas aparecen juntos en el escritorio y distinguen lo desconocido", async () => {
  const html = await htmlDeFacturas({
    textos: {
      ...structuredClone(TEXTOS_DE_FACTURAS),
      facturas: { ...TEXTOS_DE_FACTURAS.facturas, resumen_cifras: "Los números de tus facturas" },
    },
    tabla: {
      clave: "facturas", etiqueta: "Tus facturas", columnas: [{ texto: "Total" }],
      filas: [{ celdas: [], acciones: [] }], resumen: "1 factura · falta decir el total",
      indicadores: [
        { etiqueta: "Facturas", valor: "1" },
        { etiqueta: "Total", valor: "—" },
        { etiqueta: "Sin el papel", valor: "1" },
      ],
    },
  });
  assert.match(html, /aria-label="Los números de tus facturas"/);
  assert.match(html, /<p class="mando-numero-etiqueta">Total<\/p><p class="mando-numero-valor">—<\/p>/);
  assert.match(html, /1 factura · falta decir el total/);
  assert.match(html, /<ul class="lista solo-movil">/);
});

test("las facturas no llevan ni una frase escrita a mano", async () => {
  for (const html of [
    await htmlDeFacturas(),
    await htmlDeFacturas({ guardada: "si", lector: "Leo las facturas de texto." }),
    await htmlDeNuevaFactura({ error: TEXTOS_DE_FACTURAS.facturas.no_se_pudo }),
  ]) {
    const delServidor = new Set([
      ...todosLosTextos(TEXTOS_DE_FACTURAS),
      ...todosLosTextos(facturaDePrueba()),
      "Leo las facturas de texto.",
    ]);
    for (const frase of frasesVisibles(html)) {
      assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
    }
  }
});

test("la pantalla de entrar no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeEntrar({ modo: "registro", certificado: { configurado: true } });
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DE_ENTRAR),
    ...todosLosTextos(AYUDA_DEL_NIF),
    // Las provincias también vienen del servidor, y son las que se ofrecen en su lista.
    "Salamanca",
    "Valladolid",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// «Mi cuaderno»: la pantalla que más se mira (ronda 70)
//
// Es la última grande que quedaba, y no es una pantalla más: son **nueve bloques** dentro de la misma
// pantalla (los apuntes de producto, lo que falta, lo que se ha vendido, las medidas, los análisis, el
// plan, la firma, el cuaderno de la Junta y el registro electrónico). Estaban escritos a mano en
// `app.js` como siete funciones `bloqueDe…` que devolvían HTML.
//
// Lo que se comprueba aquí, y por qué:
//
//  1. **Cada cosa que falta lleva el botón que la arregla** (si tiene pantalla propia). Es la regla del
//     proyecto, y en esta pantalla es donde más se nota: es la lista de «lo que te falta».
//  2. **El aviso va en rojo solo cuando de verdad hay algo que mirar** (un plan pasado de abono, las
//     medidas sin declarar). Mirar el color es lo que hace que se vea de un vistazo.
//  3. **Cada aviso lleva su texto como lo llevaba**: unos dentro de un `<p>` y otros suelto. No es un
//     descuido —el `<p>` añade aire por dentro— y por eso se comprueban las dos formas.
//  4. **Los botones salen donde salían**: la mayoría dentro de una `.barra-acciones`, pero el de firmar
//     y el de hacer el plan van **sueltos**: una barra con un solo botón no se ve igual.
//  5. **Lo que no hay, no se enseña**: los bloques que dependen de que el servidor mande un dato (la
//     firma y el cuaderno de la Junta) no pintan ni su título si no lo tienen.
// ---------------------------------------------------------------------------

/** Los textos de «mi cuaderno», copiados de `textos.py` (los mismos que la copia de `interfaz.test.js`). */
const TEXTOS_DE_MI_CUADERNO = {
  cuaderno: {
    titulo: "Mi cuaderno",
    sin_nada: "Todavía no has apuntado nada este año.",
    ver_papel: "SACAR EN PAPEL",
    sacar_datos: "GUARDAR LOS DATOS EN UN FICHERO",
    datos_pista: "Se abre con Excel",
    ley_pista:
      "Llevar el cuaderno es obligatorio; mandarlo a la Junta, no: es voluntario (artículo 10.2 del Real Decreto 1054/2022).",
    falta_titulo: "Lo que falta",
    falta_vacio: "Todo apuntado.",
  },
};

/**
 * Las propiedades que `app.js` le prepara a la pantalla, **con los nueve bloques llenos**.
 *
 * Se escriben aquí y no se sacan de `interfaz.test.js` porque allí lo que se comprueba es el cableado
 * (que `app.js` los prepare así); aquí, cómo se dibujan. Las frases son las de verdad: las de
 * `textos.py`, ya con sus huecos rellenos y los números en castellano, que es como llegan.
 */
function propsDeMiCuaderno(cambios = {}) {
  return {
    textos: TEXTOS_DE_MI_CUADERNO,
    apuntes: {
      titulo: "2 apuntes en el cuaderno",
      hay: true,
      vacio: "Todavía no has apuntado nada este año.",
      // Cada apunte, como lo prepara `app.js` desde la ronda 79: el producto es el nombre de la tarjeta,
      // la fecha su línea y el resto sus filas, **cada dato con su nombre delante**. **Y desde la ronda
      // 91 cada apunte trae sus dos botones** (`acciones`): CORREGIR y BORRAR. El segundo apunte va sin
      // ellos a propósito, para poder comprobar que una tarjeta sin acciones no deja la barra vacía.
      filas: [
        {
          etiqueta: "Glifosato 36 SL",
          rotulo: "Apunte 1",
          lineas: ["12/05/2026", "Producto"],
          filas: [
            { etiqueta: "Tierra y parcela", valor: "El Prado" },
            { etiqueta: "Hectáreas tratadas", valor: "4,90 ha" },
            { etiqueta: "Cuánto por hectárea", valor: "2,00 l/ha" },
            { etiqueta: "Cultivo", valor: "Trigo blando" },
            { etiqueta: "Hasta aquí no puedes coger la cosecha:", valor: "26/05/2026" },
          ],
          acciones: [
            {
              etiqueta: "CORREGIR",
              accion: "cosa-corregir",
              datos: { tipo: "tratamiento", id: 7 },
              clase: "boton-claro",
            },
            {
              etiqueta: "BORRAR",
              accion: "cosa-borrar",
              datos: { tipo: "tratamiento", id: 7 },
              clase: "boton-peligro",
            },
          ],
        },
        {
          etiqueta: "Cobre 50 WP",
          rotulo: "Apunte 2",
          lineas: ["20/06/2026", "Producto"],
          filas: [
            { etiqueta: "Tierra y parcela", valor: "La Viña" },
            { etiqueta: "Hectáreas tratadas", valor: "1,20 ha" },
          ],
        },
      ],
      acciones: [
        { etiqueta: "APUNTAR OTRO TRATAMIENTO", icono: "💧", accion: "inicio", datos: { ir: "echar_producto" }, clase: "boton-claro" },
      ],
    },
    faltantes: {
      titulo: "Lo que falta",
      vacio: "Todo apuntado.",
      resumen: "Te faltan 3 cosas por apuntar",
      pendientes: [
        {
          mensaje: "A El Prado le falta decir qué cultivo tiene este año.",
          accion: "cultivo-ver-todos",
          etiqueta: "Qué hay sembrado",
        },
        {
          mensaje: "Al cuaderno de la Junta le falta el número de registro de tu máquina.",
          accion: "",
          etiqueta: "",
        },
      ],
    },
    ventas: {
      titulo: "Lo que he vendido",
      hay: true,
      resumen: "2 ventas apuntadas · 44.000 kg",
      sin_nada: "Todavía no has apuntado ninguna venta este año.",
      filas: [
        {
          fecha: "18/07/2026 — 19/07/2026",
          producto: "Trigo blando",
          detalle: "42.000,00 kg · Venta a comprador · Cooperativa · El Prado",
        },
        {
          fecha: "02/08/2026",
          producto: "Cebada",
          detalle: "2.000,00 kg · Venta directa · Un vecino · El Prado",
        },
      ],
      acciones: [
        { etiqueta: "VER LO QUE HE VENDIDO", accion: "ventas-ver", principal: true, sencillo: true },
        { etiqueta: "APUNTAR UNA VENTA", accion: "ventas-nueva", sencillo: true },
      ],
    },
    medidas: {
      titulo: "Lo que hago sin echar producto",
      declarada: true,
      mensaje: "Tienes marcadas 2 medidas. Se pueden cambiar cuando quieras.",
      aplicadas: ["Rotación de cultivos", "Higiene y limpieza de equipos y maquinaria"],
      sin_declarar: "Todavía no has dicho qué haces sin echar producto.",
      explica: "Antes de echar producto, la ley pide haber probado otras cosas.",
      acciones: [
        { etiqueta: "VER LO QUE HAGO SIN PRODUCTO", accion: "medidas-ver", sencillo: true },
      ],
    },
    analiticas: {
      titulo: "Los análisis",
      hay: true,
      resumen: "1 análisis guardado",
      sin_analisis: "Todavía no has apuntado ningún análisis.",
      apunta_primero: "Apunta primero el análisis y luego podrás hacer el plan con él.",
      filas: [
        {
          titulo: "Análisis de La tierra de El Prado",
          fecha: "14/02/2026",
          detalle: "Materia orgánica: 1,80 % · pH: 7,40",
        },
      ],
      acciones: [
        { etiqueta: "VER LOS ANÁLISIS", accion: "analisis-ver", principal: true, sencillo: true },
        { etiqueta: "APUNTAR UN ANÁLISIS", accion: "analisis-nuevo", sencillo: true },
      ],
    },
    plan: {
      titulo: "El plan de abono del año",
      hay: true,
      mensaje: "Todavía no has apuntado ningún abono contra este plan.",
      se_ha_pasado: false,
      sin_planes: "Todavía no tienes ningún plan de abono apuntado este año.",
      obligatorio: "El plan de abono es obligatorio desde el 1 de septiembre de 2026.",
      acciones: [
        { etiqueta: "VER EL PLAN DE ABONO", accion: "plan-ver", principal: true, sencillo: true },
        { etiqueta: "HACER EL PLAN DE ABONO", accion: "plan-hacer", sencillo: true },
      ],
      botones: [{ etiqueta: "HACER EL PLAN DE ABONO", icono: "🧪", accion: "plan-hacer" }],
    },
    firma: {
      hay: true,
      titulo: "Firmar el cuaderno",
      mensaje: "Todavía no has firmado el cuaderno de este año.",
      no_puede_firmar: "Para firmar hace falta que entres con tu certificado.",
      explicacion: "Firmar es lo que hace que el cuaderno valga delante de la administración.",
      cambiado: false,
      puede: true,
      botones: [
        { etiqueta: "FIRMAR EL CUADERNO", icono: "✍️", accion: "firmar-abrir", principal: true },
      ],
    },
    cuaderno: {
      hay: true,
      titulo: "Sacar mi cuaderno para la Junta",
      explica: "Puedes sacarlo relleno con lo que tienes apuntado y entregarlo si te lo piden.",
      hojas: "9 hojas de 25 llevan datos",
      falta_titulo: "Lo que te falta para tenerlo completo",
      falta_pista: "Cada cosa dice dónde se apunta, para que puedas rellenarlo.",
      faltan: [
        {
          que_falta: "Las máquinas con las que echas el producto",
          donde: "Mis cosas → máquinas de echar producto",
          hoja: "Hoja: 1.3",
        },
        { que_falta: "El agua que has gastado", donde: "A mano en el fichero", hoja: "Hoja: 3.2" },
      ],
      todo_completo: "No le falta nada: lo tienes todo apuntado.",
      acciones: [
        { etiqueta: "SACAR MI CUADERNO", accion: "cuaderno-sacar", principal: true, sencillo: true },
        { etiqueta: "Mis datos", accion: "mis-datos-abrir", sencillo: true },
        { etiqueta: "TRAER MIS TIERRAS", accion: "cuaderno-de-la-junta-abrir", sencillo: true },
      ],
    },
    registro: {
      hay: true,
      titulo: "Dónde apunto lo que hago",
      que_es: "El registro electrónico es lo mismo que apuntas ahora en el papel, pero guardado en un programa.",
      donde: "Lo apuntas aquí, en esta aplicación, o en la aplicación de la Junta (el Cuecyl).",
      desde_cuando:
        "Hasta el 31 de diciembre de 2026 puedes seguir apuntando en papel. Desde el 1 de enero de 2027 tiene que ser electrónico.",
      es_voluntario: "Apuntarlo es obligatorio. Mandarlo a la Junta por internet es voluntario.",
      enlaces_titulo: "Los sitios oficiales, para lo que hay que traer de fuera",
      enlaces: [
        { texto: "Descargar tu cuaderno de la Junta (Cuecyl)", url: "https://particulares.ayg.jcyl.es" },
        {
          texto: "Productos autorizados y su número de registro (MAPA)",
          url: "https://www.mapa.gob.es/es/agricultura/temas/sanidad-vegetal/productos-fitosanitarios/registro-productos/",
        },
      ],
    },
    acciones: [
      { etiqueta: "🖨️ SACAR EN PAPEL", accion: "sacar-papel", principal: true, sencillo: true },
      { etiqueta: "💾 GUARDAR LOS DATOS EN UN FICHERO", accion: "sacar-datos", sencillo: true },
      { etiqueta: "VOLVER", accion: "ir-inicio", sencillo: true },
    ],
    ...cambios,
  };
}

async function htmlDeMiCuaderno(cambios = {}) {
  const { PantallaMiCuaderno } = await import(
    `../web/react/pantallas/mi_cuaderno.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaMiCuaderno, propsDeMiCuaderno(cambios)),
  );
}

test("los nueve bloques salen, en el orden de la pantalla", async () => {
  const html = await htmlDeMiCuaderno();
  const titulos = [...html.matchAll(/<h2>([\s\S]*?)<\/h2>/g)].map((encontrado) => encontrado[1]);
  assert.deepEqual(titulos, [
    "2 apuntes en el cuaderno",
    "Lo que falta",
    "Lo que he vendido",
    "Lo que hago sin echar producto",
    "Los análisis",
    "El plan de abono del año",
    "Firmar el cuaderno",
    "Sacar mi cuaderno para la Junta",
    "Dónde apunto lo que hago",
  ]);
  assert.match(html, /<h1>Mi cuaderno<\/h1>/, "no lleva el título de la pantalla");
  assert.match(html, /Llevar el cuaderno es obligatorio/, "no lleva la pista de la ley al final");
});

test("los apuntes de producto salen como tarjetas, cada dato con su nombre delante", async () => {
  // **Esto cambió en la ronda 79, y por qué.** Un apunte era un renglón con «Trigo blando · 4,90 ha ·
  // 2,00 l/ha»: tres datos seguidos sin decir cuál era cuál **y sin la tierra donde se echó**, que es lo
  // primero que se pregunta en una inspección. Ahora cada apunte es una tarjeta con su número, su fecha y
  // sus filas con el nombre delante.
  const html = await htmlDeMiCuaderno();
  assert.match(html, /<div class="tarjeta">/, "el apunte no se pinta como tarjeta");
  assert.match(html, /<span class="tarjeta-rotulo">Apunte 1<\/span>/);
  assert.match(html, /<span class="tarjeta-nombre">Glifosato 36 SL<\/span>/);
  assert.match(html, /<span class="tarjeta-linea">12\/05\/2026<\/span>/, "no enseña la fecha del apunte");
  for (const [etiqueta, valor] of [
    ["Tierra y parcela", "El Prado"],
    ["Hectáreas tratadas", "4,90 ha"],
    ["Cuánto por hectárea", "2,00 l/ha"],
    ["Cultivo", "Trigo blando"],
  ]) {
    assert.match(
      html,
      new RegExp(
        `<span class="tarjeta-fila"><span class="tarjeta-fila-etiqueta">${etiqueta}</span>` +
          `<span class="tarjeta-fila-valor">${valor}</span>`,
      ),
      `el apunte no lleva «${etiqueta}: ${valor}»`,
    );
  }
  // El plazo de seguridad, que es lo que impide cosechar, va como una fila más (su rótulo ya es la
  // pregunta y la fecha la respuesta). El apunte que no lo tiene **no lleva la fila**: no se deja hueco.
  assert.match(html, /Hasta aquí no puedes coger la cosecha:<\/span><span class="tarjeta-fila-valor">26\/05\/2026/);
  assert.doesNotMatch(html.split("Cobre 50 WP")[1], /Hasta aquí no puedes coger la cosecha/);
});

test("la tarjeta de un apunte no es un botón: un apunte se lee, no se toca", async () => {
  // **Un botón que no hace nada es peor que un texto**: promete una salida y no la da. La misma pieza
  // que pinta las tierras como botones pinta los apuntes como un trozo de pantalla, y por eso no llevan
  // ni acción ni el círculo de elegir.
  //
  // Y desde la ronda 91 los botones del apunte van **fuera de la tarjeta**, en su barra: lo que se
  // comprueba aquí es la tarjeta, así que se corta justo donde empieza esa barra.
  const html = await htmlDeMiCuaderno();
  const tarjeta = html.split('<div class="tarjeta-con-acciones">')[1].split('<div class="barra-acciones">')[0];
  assert.doesNotMatch(tarjeta, /<button/, "la tarjeta del apunte se ha pintado como un botón");
  assert.doesNotMatch(tarjeta, /data-accion/, "la tarjeta del apunte lleva una acción que no existe");
  assert.doesNotMatch(tarjeta, /tarjeta-marca/, "lleva el círculo de elegir, que ahí no significa nada");
  // Y el botón de apuntar otro tratamiento sí está, dentro de su bloque.
  const bloque = html.split("apuntes en el cuaderno")[1].split("<h2>")[0];
  assert.match(bloque, /data-accion="inicio" data-ir="echar_producto"/, "no deja apuntar otro desde aquí");
  assert.match(bloque, /APUNTAR OTRO TRATAMIENTO/);
});

test("cada apunte lleva sus dos botones: corregir y borrar (ronda 91)", async () => {
  // Lo que pidió el dueño del proyecto: «recuerda también dejar borrar las cosas que introduzca porque
  // puede que me equivoque, o modificar también». Cada apunte de la lista tiene que poder arreglarse
  // desde ahí mismo, y **cada botón tiene que decir de qué apunte es**: el manejador de clics lee
  // `data-tipo` y `data-id`, y sin ellos no sabe qué corregir (o corrige el de al lado).
  const html = await htmlDeMiCuaderno();
  const barra = html.split('<div class="tarjeta-con-acciones">')[1].split('<div class="barra-acciones">')[1].split("</div>")[0];
  assert.match(
    barra,
    /<button[^>]*data-accion="cosa-corregir"[^>]*data-tipo="tratamiento"[^>]*data-id="7"/,
    "el botón de corregir no dice qué apunte es",
  );
  assert.match(
    barra,
    /<button[^>]*data-accion="cosa-borrar"[^>]*data-tipo="tratamiento"[^>]*data-id="7"/,
    "el botón de borrar no dice qué apunte es",
  );
  assert.match(barra, />CORREGIR</, "no se lee el botón de corregir");
  assert.match(barra, />BORRAR</, "no se lee el botón de borrar");
  // **Corregir va primero**: el botón que puede quitar algo del cuaderno no puede ser el que más a mano
  // esté, y va marcado como peligro.
  assert.ok(
    barra.indexOf("cosa-corregir") < barra.indexOf("cosa-borrar"),
    "el botón de borrar sale antes que el de corregir",
  );
  assert.match(barra, /cosa-borrar[^>]*boton-peligro|boton-peligro[^>]*cosa-borrar/);
  // Y una tarjeta sin acciones no deja una barra vacía: la segunda no lleva ninguna.
  const segunda = html.split("Cobre 50 WP")[1];
  assert.doesNotMatch(
    segunda.split("</div></div>")[0],
    /barra-acciones/,
    "una tarjeta sin botones deja la barra puesta y vacía",
  );
});

test("el cuaderno de la Junta va en su bloque verde, con el botón dentro", async () => {
  // **El único bloque oscuro de la aplicación, y por qué (ronda 80).** Es lo único de esta pantalla que
  // se hace con alguien delante —el inspector, en el campo, esperando—, así que tiene que encontrarse sin
  // leer. El botón de sacar el cuaderno va **dentro** del verde; la lista de lo que falta, fuera y en
  // blanco: eso se lee con calma.
  const html = await htmlDeMiCuaderno();
  const bloque = html.split('<div class="bloque-junta">')[1].split("</div>")[0];
  assert.ok(bloque, "el cuaderno de la Junta no va en su bloque");
  assert.match(bloque, /<h2>Sacar mi cuaderno para la Junta<\/h2>/, "no lleva su título");
  assert.match(bloque, /data-accion="cuaderno-sacar"/, "el botón de sacarlo no está dentro del bloque");
  assert.match(bloque, /SACAR MI CUADERNO/);
  // Y lo que falta **no** va dentro del verde.
  const despues = html.split("Lo que te falta para tenerlo completo")[1];
  assert.match(despues, /Las máquinas con las que echas el producto/, "no dice qué falta");
  assert.doesNotMatch(despues.split("</div>")[0], /bloque-junta/, "lo que falta se ha metido en el verde");
});

test("la frase de un vistazo dice si falta algo, y sin el dato no se dice nada", async () => {
  // Es lo primero que se lee en la pantalla que más se mira, y contesta a la pregunta con la que se abre:
  // «¿tengo el cuaderno al día?». **Solo sale si el servidor ha contestado** lo que falta: decir «no te
  // falta nada» con la lista sin llegar sería afirmar lo que no se sabe.
  const html = await htmlDeMiCuaderno();
  assert.match(html, /<p class="cuantas">Te faltan 3 cosas por apuntar<\/p>/);
  const sinDato = await htmlDeMiCuaderno({
    faltantes: { titulo: "Lo que falta", vacio: "Todo apuntado.", pendientes: [], resumen: "" },
  });
  const principio = sinDato.split("apuntes en el cuaderno")[0];
  assert.doesNotMatch(principio, /class="cuantas"/, "afirma lo que no sabe: el servidor no ha contestado");
});

test("sin apuntes se dice, en vez de dejar la lista vacía", async () => {
  const html = await htmlDeMiCuaderno({
    apuntes: { titulo: "0 apuntes en el cuaderno", hay: false, filas: [], vacio: "Todavía no has apuntado nada este año." },
  });
  const bloque = html.split("0 apuntes en el cuaderno")[1].split("<h2>")[0];
  assert.match(bloque, /<p class="pista-campo">Todavía no has apuntado nada este año\.<\/p>/);
  assert.doesNotMatch(bloque, /<ul class="lista">/, "pinta una lista vacía en vez de decirlo");
});

test("cada cosa que falta lleva el botón que la arregla, y la que no tiene pantalla se queda con el texto", async () => {
  // La regla del proyecto: si le dices al agricultor que le falta algo, le das el botón que lo
  // arregla. El que no tiene pantalla propia (el agua, que se apunta a mano) se queda con su texto.
  const html = await htmlDeMiCuaderno();
  const conBoton = html.split("A El Prado le falta decir")[1].split("</li>")[0];
  assert.match(conBoton, /<div class="barra-acciones">/);
  assert.match(conBoton, /data-accion="cultivo-ver-todos"/);
  assert.match(conBoton, />Qué hay sembrado</);
  const sinBoton = html.split("le falta el número de registro")[1].split("</li>")[0];
  assert.doesNotMatch(sinBoton, /data-accion=/, "ofrece un botón que no lleva a ninguna parte");
});

test("sin nada pendiente se dice que está todo apuntado", async () => {
  const html = await htmlDeMiCuaderno({
    faltantes: { titulo: "Lo que falta", vacio: "Todo apuntado.", pendientes: [] },
  });
  assert.match(html, /<p class="pista-campo">Todo apuntado\.<\/p>/);
});

test("las ventas salen con su resumen, sus últimas y la puerta a todas", async () => {
  const html = await htmlDeMiCuaderno();
  // El resumen va en su línea destacada (`.cuantas`), como el de los apuntes y el de los análisis: es lo
  // que se lee de un vistazo para saber si falta apuntar una entrega (rediseño de la ronda 81).
  assert.match(html, /<p class="cuantas">2 ventas apuntadas · 44\.000 kg<\/p>/, "no dice qué cuenta ni cuánto");
  assert.match(html, /<span>18\/07\/2026 — 19\/07\/2026<\/span>/, "no enseña el intervalo de la venta");
  assert.match(html, /42\.000,00 kg · Venta a comprador · Cooperativa · El Prado/);
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.ok(acciones.includes("ventas-ver"), "no lleva a ver todas las ventas");
  assert.ok(acciones.includes("ventas-nueva"), "no deja apuntar una venta");
  // El botón de ver todas **solo sale si hay ventas**: sin ellas no lleva a ninguna parte.
  const sinVentas = await htmlDeMiCuaderno({
    ventas: {
      titulo: "Lo que he vendido",
      hay: false,
      resumen: "",
      filas: [],
      sin_nada: "Todavía no has apuntado ninguna venta este año.",
      acciones: [{ etiqueta: "APUNTAR UNA VENTA", accion: "ventas-nueva", sencillo: true }],
    },
  });
  assert.match(sinVentas, /Todavía no has apuntado ninguna venta este año/);
  assert.doesNotMatch(sinVentas, /data-accion="ventas-ver"/, "ofrece ver ventas que no hay");
});

test("las medidas declaradas salen con su nombre, y sin ninguna el aviso va en rojo", async () => {
  const html = await htmlDeMiCuaderno();
  assert.match(html, /Rotación de cultivos/);
  assert.match(html, /Higiene y limpieza de equipos y maquinaria/);
  assert.doesNotMatch(html.split("Lo que hago sin echar producto")[1].split("<h2>")[0], /aviso-error/);

  // Haber declarado que no hace ninguna es un aviso que hay que mirar, y se pinta en rojo.
  const ninguna = await htmlDeMiCuaderno({
    medidas: {
      titulo: "Lo que hago sin echar producto",
      declarada: true,
      mensaje: "Has dicho que no haces ninguna medida preventiva.",
      aplicadas: [],
      sin_declarar: "Todavía no has dicho qué haces sin echar producto.",
      explica: "Antes de echar producto, la ley pide haber probado otras cosas.",
      acciones: [{ etiqueta: "VER LO QUE HAGO SIN PRODUCTO", accion: "medidas-ver", sencillo: true }],
    },
  });
  assert.match(ninguna, /<div class="aviso aviso-error">/);
  assert.match(ninguna, /<p>Has dicho que no haces ninguna medida preventiva\.<\/p>/);
});

test("sin declarar las medidas se dice, y el aviso lleva su texto suelto", async () => {
  // Aquí el texto va **suelto**, no dentro de un `<p>`: es como estaba, y el aire de dentro del `<p>`
  // se nota en la altura de la pantalla.
  const html = await htmlDeMiCuaderno({
    medidas: {
      titulo: "Lo que hago sin echar producto",
      declarada: false,
      mensaje: "",
      aplicadas: [],
      sin_declarar: "Todavía no has dicho qué haces sin echar producto.",
      explica: "Antes de echar producto, la ley pide haber probado otras cosas.",
      acciones: [{ etiqueta: "MARCAR LO QUE HAGO", accion: "medidas-ver", sencillo: true }],
    },
  });
  assert.match(html, /<div class="aviso">Todavía no has dicho qué haces sin echar producto\.<\/div>/);
  assert.match(html, /Antes de echar producto, la ley pide haber probado otras cosas/);
  assert.match(html, /data-accion="medidas-ver"/);
});

test("los análisis salen con sus números, y sin ninguno se dice", async () => {
  const html = await htmlDeMiCuaderno();
  assert.match(html, /Análisis de La tierra de El Prado/);
  assert.match(html, /Materia orgánica: 1,80 % · pH: 7,40/);

  const sinNinguno = await htmlDeMiCuaderno({
    analiticas: {
      titulo: "Los análisis",
      hay: false,
      resumen: "",
      filas: [],
      sin_analisis: "Todavía no has apuntado ningún análisis.",
      apunta_primero: "Apunta primero el análisis y luego podrás hacer el plan con él.",
      acciones: [{ etiqueta: "APUNTAR UN ANÁLISIS", accion: "analisis-nuevo", sencillo: true }],
    },
  });
  assert.match(sinNinguno, /Todavía no has apuntado ningún análisis/);
  assert.match(sinNinguno, /Apunta primero el análisis/);
  assert.doesNotMatch(sinNinguno, /data-accion="analisis-ver"/, "ofrece ver análisis que no hay");
});

test("el plan, sin ninguno, avisa y ofrece hacerlo con un botón suelto y con su icono", async () => {
  // El botón de hacer el plan es lo único que se puede hacer en ese bloque, y por eso va suelto y con
  // su probeta: es el que empuja a hacerlo. Los demás van en su barra.
  const html = await htmlDeMiCuaderno({
    plan: {
      titulo: "El plan de abono del año",
      hay: false,
      mensaje: "",
      se_ha_pasado: false,
      sin_planes: "Todavía no tienes ningún plan de abono apuntado este año.",
      obligatorio: "El plan de abono es obligatorio desde el 1 de septiembre de 2026.",
      acciones: [],
      botones: [{ etiqueta: "HACER EL PLAN DE ABONO", icono: "🧪", accion: "plan-hacer" }],
    },
  });
  assert.match(html, /Todavía no tienes ningún plan de abono apuntado este año/);
  assert.match(html, /El plan de abono es obligatorio desde el 1 de septiembre de 2026/);
  // El icono del plan es **un dibujo** desde el rediseño (ronda 76): el cuadro lleva su clave y dentro
  // va el `<svg>` con los trazos. La clave sigue siendo el emoji que trae el servidor.
  assert.match(html, /<span class="icono" aria-hidden="true" data-icono="🧪">/);
  assert.match(html, /class="dibujo-icono"/, "el icono del plan no se ha dibujado");
  assert.match(html, /data-accion="plan-hacer"/);
  // Suelto, no dentro de una barra: es como estaba, y un botón en una barra no se ve igual.
  const bloque = html.split("El plan de abono del año")[1].split("<h2>")[0];
  assert.doesNotMatch(bloque, /<div class="barra-acciones">/, "ha metido el botón en una barra");
});

test("si te has pasado del plan, el aviso va en rojo", async () => {
  const html = await htmlDeMiCuaderno({
    plan: {
      ...propsDeMiCuaderno().plan,
      mensaje: "Ojo: llevas más de lo que tenías previsto.",
      se_ha_pasado: true,
    },
  });
  const bloque = html.split("El plan de abono del año")[1];
  assert.match(bloque, /<div class="aviso aviso-error">/);
  assert.match(bloque, /<p>Ojo: llevas más de lo que tenías previsto\.<\/p>/);
  assert.match(bloque, /data-accion="plan-ver"/);
});

test("la firma: sin poder firmar no sale el botón, y se dice por qué", async () => {
  // Un botón que lleva a un error es peor que no ponerlo.
  const html = await htmlDeMiCuaderno({
    firma: { ...propsDeMiCuaderno().firma, puede: false, botones: [] },
  });
  assert.doesNotMatch(html, /data-accion="firmar-abrir"/, "sale el botón sin poder firmar");
  assert.match(html, /<p>Para firmar hace falta que entres con tu certificado\.<\/p>/);
  // Los dos textos van dentro del **mismo** aviso, cada uno en su `<p>`: es como estaba.
  const aviso = html.split("Firmar el cuaderno")[1].split("</div>")[0];
  assert.match(aviso, /Todavía no has firmado el cuaderno de este año\./);
  assert.match(aviso, /hace falta que entres con tu certificado/);
});

test("si el cuaderno se cambió después de firmar, la firma se marca en rojo", async () => {
  const html = await htmlDeMiCuaderno({
    firma: {
      ...propsDeMiCuaderno().firma,
      cambiado: true,
      mensaje: "Ojo: este cuaderno se firmó, pero después se ha cambiado algo.",
    },
  });
  const bloque = html.split("Firmar el cuaderno")[1];
  assert.match(bloque, /<div class="aviso aviso-error">/);
  assert.match(bloque, /se ha cambiado algo/);
  assert.match(bloque, /data-accion="firmar-abrir"/, "sin el botón no se puede volver a firmar");
});

test("el cuaderno de la Junta dice las hojas, lo que falta con dónde se apunta y cómo sacarlo", async () => {
  const html = await htmlDeMiCuaderno();
  assert.match(html, /9 hojas de 25 llevan datos/);
  assert.match(html, /<h3>Lo que te falta para tenerlo completo<\/h3>/);
  assert.match(html, /<div class="apunte-detalle">Las máquinas con las que echas el producto<\/div>/);
  assert.match(html, /<div class="apunte-detalle">Mis cosas → máquinas de echar producto<\/div>/);
  assert.match(html, /<div class="apunte-detalle">Hoja: 1\.3<\/div>/);
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(
    acciones.filter((accion) => ["cuaderno-sacar", "mis-datos-abrir", "cuaderno-de-la-junta-abrir"].includes(accion)),
    ["cuaderno-sacar", "mis-datos-abrir", "cuaderno-de-la-junta-abrir"],
  );

  // Cuando ya está todo, se dice en vez de dejar la lista vacía.
  const completo = await htmlDeMiCuaderno({
    cuaderno: { ...propsDeMiCuaderno().cuaderno, faltan: [] },
  });
  assert.match(completo, /No le falta nada: lo tienes todo apuntado\./);
});

test("el registro electrónico sale con los enlaces oficiales, que se abren en otra pestaña", async () => {
  const html = await htmlDeMiCuaderno();
  assert.match(html, /mandarlo a la Junta, no: es voluntario/);
  assert.match(html, /<h3>Los sitios oficiales, para lo que hay que traer de fuera<\/h3>/);
  assert.match(
    html,
    /<a href="https:\/\/particulares\.ayg\.jcyl\.es" target="_blank" rel="noopener">Descargar tu cuaderno de la Junta \(Cuecyl\)<\/a>/,
  );
  assert.match(html, /registro-productos\//, "no está el enlace de los productos autorizados");
  // Los enlaces se abren **fuera** de la aplicación: si no, el agricultor pierde la pantalla donde
  // estaba apuntando (y en el móvil, la aplicación instalada se queda sin poder volver).
  assert.equal(
    [...html.matchAll(/<a /g)].length,
    [...html.matchAll(/rel="noopener"/g)].length,
    "hay un enlace que se abre sin protección",
  );
});

test("los tres botones de abajo llevan su emoji dentro del texto, y sin flecha", async () => {
  // Es como estaban escritos: estos tres no son los botones de la casa (no llevan el
  // `<span class="icono">` ni la flecha de salida). Se mira su HTML entero, porque el lector de botones
  // de estas pruebas saca la etiqueta de `<span class="texto">` y un botón sencillo no lo tiene.
  const html = await htmlDeMiCuaderno();
  assert.match(
    html,
    /<button type="button" class="boton" data-accion="sacar-papel">🖨️ SACAR EN PAPEL<\/button>/,
  );
  assert.match(
    html,
    /<button type="button" class="boton boton-claro" data-accion="sacar-datos">💾 GUARDAR LOS DATOS EN UN FICHERO<\/button>/,
  );
  assert.match(html, /<button type="button" class="boton boton-claro" data-accion="ir-inicio">VOLVER<\/button>/);
  // Y ninguna flecha ni icono sueltos dentro de los tres.
  for (const accion of ["sacar-papel", "sacar-datos", "ir-inicio"]) {
    const cuerpo = html.split(`data-accion="${accion}"`)[1].split("</button>")[0];
    assert.doesNotMatch(cuerpo, /<span/, `el botón ${accion} lleva dentro algo más que su texto`);
  }
});

test("el bloque que no tiene datos no se pinta, ni su título", async () => {
  // La firma y el cuaderno de la Junta solo están si el servidor los ha mandado: un bloque con su
  // título y un hueco debajo parece un fallo del programa.
  const html = await htmlDeMiCuaderno({
    firma: { hay: false, titulo: "Firmar el cuaderno", botones: [] },
    cuaderno: { hay: false, titulo: "Sacar mi cuaderno para la Junta", faltan: [], acciones: [] },
    registro: { hay: false, titulo: "Dónde apunto lo que hago", enlaces: [] },
  });
  assert.doesNotMatch(html, /Firmar el cuaderno/);
  assert.doesNotMatch(html, /Sacar mi cuaderno para la Junta/);
  assert.doesNotMatch(html, /Dónde apunto lo que hago/);
  // Y los apuntes y lo que falta sí siguen: son los dos que siempre están.
  assert.match(html, /2 apuntes en el cuaderno/);
  assert.match(html, /Lo que falta/);
});

test("mi cuaderno no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeMiCuaderno();
  const delServidor = new Set([
    ...todosLosTextos(propsDeMiCuaderno()),
    // Los tres botones de abajo llevan su emoji **dentro del texto** (es como estaban): esa frase la
    // monta `app.js` juntando el emoji con el texto del servidor, así que se añade aquí tal cual.
    "🖨️ SACAR EN PAPEL",
    "💾 GUARDAR LOS DATOS EN UN FICHERO",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// El aviso de error y el botón sencillo (las dos piezas de las pantallas de error)
//
// Son dos piezas de `componentes.js` que usa media aplicación, y desde la ronda 71 son **lo único que
// se ve cuando el servidor falla**: `avisarDelError()` (en `app.js`) compone un aviso de error con su
// botón de volver y lo monta en el sitio de la pantalla. Se prueban aquí, y no solo dentro de las
// pantallas, porque un cambio en `componentes.js` se lleva por delante todas a la vez — y porque hasta
// la ronda 71 ninguna prueba miraba estas dos piezas de frente.
// ---------------------------------------------------------------------------

/** El HTML de un componente de `componentes.js`, por su nombre de exportación. */
async function htmlDeComponente(nombre, propiedades) {
  const modulo = await import(`../web/react/componentes.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(modulo[nombre], propiedades),
  );
}

test("el aviso de error sale en rojo y se anuncia solo", async () => {
  // `role="alert"` no es adorno: es lo que hace que un lector de pantalla lo lea en voz alta en cuanto
  // aparece, sin que el agricultor tenga que ir a buscarlo.
  const html = await htmlDeComponente("AvisoDeError", { texto: "No se ha podido guardar." });
  assert.match(html, /^<div class="aviso aviso-error" role="alert">No se ha podido guardar\.<\/div>$/);
});

test("un aviso de error sin texto no se dibuja", async () => {
  // Un hueco con un borde rojo asusta sin motivo: si no hay nada que decir, no se pinta nada.
  assert.equal(await htmlDeComponente("AvisoDeError", { texto: "" }), "");
  assert.equal(await htmlDeComponente("AvisoDeError", {}), "");
});

test("lo que dice el servidor se enseña tal cual, sin que el navegador lo interprete", async () => {
  // El texto puede venir con cualquier cosa dentro (el nombre de un producto, un «<» de una medida):
  // tiene que verse como texto, no dibujarse como etiqueta. Es lo que hacía `esc()` en la interfaz
  // vieja, y ahora lo hace React.
  const html = await htmlDeComponente("AvisoDeError", { texto: "Mira <b>esto</b> & aquello" });
  assert.match(html, /Mira &lt;b&gt;esto&lt;\/b&gt; &amp; aquello/);
});

test("el botón sencillo sin clase es el botón pelado de los avisos de error", async () => {
  // `clase=""` da `class="boton"` a secas, que es como sale el VOLVER de los avisos de error; sin
  // decir nada sale `boton boton-claro`, que es el de los demás sitios.
  const pelado = await htmlDeComponente("BotonSencillo", {
    etiqueta: "VOLVER",
    accion: "ir-inicio",
    clase: "",
  });
  assert.match(pelado, /^<button type="button" class="boton" data-accion="ir-inicio">VOLVER<\/button>$/);
  const claro = await htmlDeComponente("BotonSencillo", {
    etiqueta: "VOLVER",
    accion: "ir-inicio",
  });
  assert.match(
    claro,
    /^<button type="button" class="boton boton-claro" data-accion="ir-inicio">VOLVER<\/button>$/,
  );
});

// ---------------------------------------------------------------------------
// Los iconos dibujados (rediseño con Stitch, ronda 76)
//
// Los iconos de los botones eran emoji, y se veían distintos en cada móvil (y con un estilo que no era
// el de la aplicación). Ahora son **dibujos de línea** en SVG, con los trazos del rediseño. La clave del
// dibujo sigue siendo el emoji que trae el texto del servidor, y por eso **`textos.py` no hay que
// tocarlo** para cambiar un icono.
// ---------------------------------------------------------------------------

test("el icono se dibuja: trazos, sin relleno y del color del texto", async () => {
  const html = await htmlDeComponente("Icono", { clave: "💧" });
  assert.match(html, /^<svg class="dibujo-icono" viewBox="0 0 24 24"/, "no es un dibujo");
  assert.match(html, /stroke="currentColor"/, "el dibujo no toma el color del texto");
  assert.match(html, /fill="none"/, "el dibujo lleva relleno (no es de línea)");
  assert.match(html, /stroke-width="2"|strokeWidth="2"/, "no lleva el trazo de la casa");
  assert.match(html, /aria-hidden="true"/, "el dibujo no va oculto para los lectores de pantalla");
  assert.match(html, /<path d="M12 2v6/, "no trae los trazos del dibujo");
});

test("un emoji sin dibujo se enseña tal cual, en vez de dejar un hueco", async () => {
  // Es lo que hace que añadir un botón nuevo no dependa de que alguien dibuje su icono: sale el emoji.
  const html = await htmlDeComponente("Icono", { clave: "🐑" });
  assert.equal(html, "🐑");
  assert.equal(await htmlDeComponente("Icono", { clave: "" }), "");
});

test("los dibujos que hay son los que dicen que hay", async () => {
  // Un inventario a la vista: si alguien añade un dibujo, esta lista se actualiza; si alguien lo quita,
  // el icono de ese botón vuelve a ser un emoji y hay que enterarse.
  const modulo = await import(`../web/react/componentes.js?prueba=${Math.random()}`);
  const claves = modulo.clavesConDibujo();
  for (const clave of ["💧", "🟤", "🚜", "📖", "🖨️", "❓", "🔁", "🎤", "📋", "📍", "🧪", "✍️"]) {
    assert.ok(claves.includes(clave), `falta el dibujo de ${clave}`);
    assert.ok(modulo.hayDibujo(clave), `hayDibujo() no reconoce ${clave}`);
  }
  assert.equal(modulo.hayDibujo("🐑"), false, "dice que hay dibujo de un emoji que no lo tiene");
});

// ---------------------------------------------------------------------------
// El asistente: la pantalla que envuelve cada pregunta (ronda 72)
//
// Es la pantalla que más se usa de la aplicación (echar producto, abonar, sembrar, regar, coger la
// cosecha…) y la última que quedaba por pasar a React. Lo que se comprueba aquí es **el envoltorio**: las
// barras de progreso, la pregunta, su pista, el aviso de error, el sitio del formulario y los botones.
// El formulario de cada paso es otra cosa (una pieza), y sus pruebas están más arriba en este fichero.
// ---------------------------------------------------------------------------

/** Las propiedades que `app.js` le prepara al asistente, como en el paso de la fecha de un tratamiento. */
function propsDelAsistente(cambios = {}) {
  return {
    titulo: "¿Cuándo lo has echado?",
    pista: "El día que lo echaste",
    indice: 1,
    total: 4,
    formulario: React.createElement("p", null, "El campo de la fecha"),
    error: "",
    botones: [
      { etiqueta: "VOLVER", accion: "asistente-atras", sencillo: true },
      { etiqueta: "DEJARLO", accion: "asistente-saltar", sencillo: true },
      { etiqueta: "SEGUIR", accion: "asistente-seguir", principal: true, sencillo: true },
    ],
    ...cambios,
  };
}

async function htmlDelAsistente(cambios = {}) {
  const { PantallaAsistente } = await import(
    `../web/react/pantallas/asistente.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaAsistente, propsDelAsistente(cambios)),
  );
}

test("las barras dicen por dónde va y cuántos pasos hay", async () => {
  // Es lo que le dice al agricultor —y a un lector de pantalla, con `role="progressbar"`— cuánto le
  // queda para acabar el apunte.
  const html = await htmlDelAsistente({ indice: 1, total: 4 });
  assert.match(html, /<div class="pasos" role="progressbar" aria-valuenow="2" aria-valuemax="4">/);
  const barras = [...html.matchAll(/<div class="(paso[^"]*)"><\/div>/g)].map((uno) => uno[1]);
  assert.deepEqual(barras, ["paso paso-hecho", "paso paso-hecho", "paso", "paso"]);
});

test("un asistente de un solo paso no lleva barra ni «Paso 1 de 1»", async () => {
  // **Esto se cambió en la ronda 88.** La pantalla del SIGPAC es un asistente de **un solo paso**: una barra
  // llena y un «Paso 1 de 1» no cuentan nada y empujan hacia abajo lo que sí importa.
  const html = await htmlDelAsistente({ indice: 0, total: 1, paso: "" });
  assert.doesNotMatch(html, /class="pasos"/, "un asistente de un paso lleva barra de progreso");
  assert.doesNotMatch(html, /class="paso-cuantos"/, "dice «Paso 1 de 1»");
  assert.match(html, /class="pregunta"/, "sin la barra se pierde la pregunta");
  // Y con más de un paso sigue habiendo barra: es lo que se acaba de arreglar, no lo que se ha quitado.
  assert.match(await htmlDelAsistente({ indice: 0, total: 2 }), /class="pasos"/);
});

test("la pregunta, su pista y el formulario del paso salen en su sitio", async () => {
  const html = await htmlDelAsistente();
  assert.match(html, /<p class="pregunta">¿Cuándo lo has echado\?<\/p>/);
  assert.match(html, /<p class="pista">El día que lo echaste<\/p>/);
  // El formulario va **dentro del hueco de siempre**, con su `id`: es lo que buscan las pruebas de los
  // pasos y la comprobación en un navegador de verdad.
  assert.match(html, /<div id="formulario"><p>El campo de la fecha<\/p><\/div>/);
  // Y en orden: primero la pregunta, luego el formulario.
  assert.ok(
    html.indexOf('class="pregunta"') < html.indexOf('id="formulario"'),
    "el formulario sale antes que la pregunta",
  );
});

test("sin pista no se deja el hueco", async () => {
  // Un paso sin explicación no pinta un párrafo vacío: el aire de más se nota y no dice nada.
  const html = await htmlDelAsistente({ pista: "" });
  assert.doesNotMatch(html, /class="pista"/);
  assert.match(html, /class="pregunta"/);
});

test("el error del paso sale en rojo, entre la pregunta y el formulario", async () => {
  // Lo que dice el servidor cuando el paso no puede seguir («dinos en qué parcela»): va donde el
  // agricultor está mirando, no al final de la pantalla.
  const html = await htmlDelAsistente({ error: "Dinos en qué parcela." });
  assert.match(html, /<div class="aviso aviso-error" role="alert">Dinos en qué parcela\.<\/div>/);
  assert.ok(
    html.indexOf('class="aviso aviso-error"') < html.indexOf('id="formulario"'),
    "el error sale después del formulario",
  );
  // Y cuando no hay error, no se pinta nada.
  assert.doesNotMatch(await htmlDelAsistente(), /aviso-error/);
});

test("los botones salen en su barra, con su acción y su forma", async () => {
  // VOLVER y DEJARLO son claros; SEGUIR (o APUNTARLO, en el resumen) es el principal. Los tres van
  // **sencillos**, sin icono y sin flecha, como estaban: no llevan a otra pantalla, hacen avanzar esta.
  // Y van dentro de `.asistente-acciones`, la barra **pegada abajo** (rediseño, ronda 77): con una mano
  // y de pie en el campo, el botón de seguir tiene que estar donde llega el pulgar.
  const html = await htmlDelAsistente();
  assert.match(html, /<div class="asistente-acciones"><button type="button" class="boton boton-claro" data-accion="asistente-atras">VOLVER<\/button>/);
  assert.match(
    html,
    /<button type="button" class="boton boton-claro" data-accion="asistente-saltar">DEJARLO<\/button>/,
  );
  assert.match(
    html,
    /<button type="button" class="boton" data-accion="asistente-seguir">SEGUIR<\/button><\/div>$/,
  );
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, ["asistente-atras", "asistente-saltar", "asistente-seguir"]);
});

test("el asistente no lleva ni una frase escrita a mano", async () => {
  // Todo lo que se lee (la pregunta, la pista, el error y las etiquetas de los botones) viene del
  // servidor. El formulario se deja fuera a propósito: es una pieza, y tiene sus propias pruebas.
  const props = propsDelAsistente({ error: "Dinos en qué parcela.", formulario: null });
  const html = await htmlDelAsistente({ error: "Dinos en qué parcela.", formulario: null });
  const delServidor = new Set(todosLosTextos(props));
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// La tarjeta de una tierra (rediseño con Stitch, ronda 77)
//
// En el asistente, la pregunta que más se repite es «¿en cuál?». Antes era una fila de texto igual que
// las demás, y con 51 tierras eso es elegir a ciegas: el tratamiento acaba apuntado en la tierra que no
// es, y eso no se nota hasta que alguien mira el cuaderno. La tarjeta lleva el dibujo de la forma de la
// tierra (que es como el agricultor la reconoce: la ve así en el SIGPAC), su superficie, su pueblo, sus
// avisos y la palabra «ELEGIDA» en la que acaba de tocar.
// ---------------------------------------------------------------------------

/** Una tierra de prueba, como la prepara `app.js` para la tarjeta. */
function tierraParaLaTarjeta(cambios = {}) {
  return {
    tarjeta: true,
    etiqueta: "El Prado",
    lineas: ["4,90 hectáreas", "Medina del Campo"],
    dibujo: "M10 10 L90 10 L90 90 Z",
    avisos: [],
    elegida: false,
    accion: "elegir",
    datos: { campo: "parcela_id", valor: 7, superficie: 4.9 },
    textos: { elegida: "ELEGIDA" },
    ...cambios,
  };
}

async function htmlDeLaTarjeta(cambios = {}) {
  const { Tarjeta } = await import(`../web/react/piezas/tarjeta.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(Tarjeta, tierraParaLaTarjeta(cambios)),
  );
}

test("la tarjeta de una tierra enseña su forma, su superficie y su pueblo", async () => {
  const html = await htmlDeLaTarjeta();
  assert.match(html, /class="dibujo-parcela"/, "no lleva el dibujo de la forma de la tierra");
  assert.match(html, /d="M10 10 L90 10 L90 90 Z"/, "el dibujo no es la forma de esa tierra");
  assert.match(html, /<span class="tarjeta-nombre">El Prado<\/span>/);
  assert.match(html, /<span class="tarjeta-linea">4,90 hectáreas<\/span>/);
  assert.match(html, /<span class="tarjeta-linea-suave">Medina del Campo<\/span>/);
});

test("una tierra sin forma dibujada no enseña un cuadro vacío", async () => {
  // Un cuadro vacío parece un fallo del programa: si no hay dibujo, no se enseña el hueco.
  const html = await htmlDeLaTarjeta({ dibujo: "" });
  assert.doesNotMatch(html, /tarjeta-dibujo/);
  assert.match(html, /<span class="tarjeta-nombre">El Prado<\/span>/, "el resto de la tarjeta sí sale");
});

test("la tierra elegida se dice con la palabra y con el círculo marcado", async () => {
  // El color no informa solo (regla de la casa): quien no distinga el verde tiene que poder leerlo.
  const html = await htmlDeLaTarjeta({ elegida: true });
  assert.match(html, /class="tarjeta tarjeta-elegida"/);
  assert.match(html, /<span class="tarjeta-etiqueta">ELEGIDA<\/span>/);
  assert.match(html, /class="tarjeta-marca tarjeta-marca-si"/);
  const sinElegir = await htmlDeLaTarjeta();
  assert.doesNotMatch(sinElegir, /ELEGIDA/, "una tierra sin elegir no puede decir ELEGIDA");
  assert.match(sinElegir, /class="tarjeta-marca"/, "no lleva su círculo sin marcar");
});

test("los avisos de la tierra van dentro de su tarjeta", async () => {
  // Es cuando se elige cuando importa saber que esa tierra está en zona de nitratos.
  const html = await htmlDeLaTarjeta({
    avisos: ["Está en zona de nitratos", "Tiene una masa de agua cerca"],
  });
  assert.match(html, /<span class="tarjeta-aviso">[\s\S]*Está en zona de nitratos<\/span>/);
  assert.match(html, /Tiene una masa de agua cerca/);
  assert.doesNotMatch(await htmlDeLaTarjeta(), /tarjeta-aviso/, "una tierra sin avisos no lleva franjas");
});

test("la tarjeta sigue siendo un botón, con su acción y sus datos", async () => {
  // **Sin esto, la tarjeta sería un dibujo bonito que no hace nada**: el manejador de clics de la
  // aplicación es uno solo, vive en `app.js` y lee `data-accion` y los demás `data-*`.
  const html = await htmlDeLaTarjeta();
  assert.match(html, /^<button type="button" class="tarjeta" data-accion="elegir"/);
  assert.match(html, /data-campo="parcela_id"/);
  assert.match(html, /data-valor="7"/);
  assert.match(html, /data-superficie="4.9"/);
});

test("la lista pinta tarjeta cuando el botón viene como tarjeta, y botón cuando no", async () => {
  // La pieza decide por el `tarjeta: true` que prepara `app.js`: no se adivina por los datos.
  const { ListaParaElegir } = await import(
    `../web/react/piezas/lista_para_elegir.js?prueba=${Math.random()}`
  );
  const html = globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(ListaParaElegir, {
      bloques: [
        {
          titulo: "¿Dónde?",
          botones: [
            tierraParaLaTarjeta(),
            { etiqueta: "El almacén grande", pista: "Nave", accion: "elegir", clase: "boton-claro" },
          ],
        },
      ],
    }),
  );
  assert.match(html, /class="tarjeta"/, "la tierra no se pinta como tarjeta");
  assert.match(html, /class="boton boton-claro" data-accion="elegir">[\s\S]*El almacén grande/);
});

// ---------------------------------------------------------------------------
// La tarjeta de una tierra, la segunda vez que hizo falta (ronda 78)
//
// En «Mis parcelas, productos y máquinas» la lista de tierras era el mismo muro de renglones, pero
// además **no se podía hacer nada con ella**. Ahí la tarjeta lleva tres cosas más: el rótulo de arriba
// («Tierra n.º 12», que es lo que permite decir «mira la doce» por teléfono), los datos con su nombre
// delante (una referencia del SIGPAC suelta no dice qué es) y el pie que dice qué pasa al tocarla. Y
// puede ir **sin el círculo de elegir**: en una lista donde no se elige nada, un círculo sin marcar
// promete algo que no ocurre.
// ---------------------------------------------------------------------------

test("el rótulo de la tierra va encima del nombre, y sin rótulo no se deja el hueco", async () => {
  const conRotulo = await htmlDeLaTarjeta({ rotulo: "Tierra n.º 12" });
  assert.match(conRotulo, /<span class="tarjeta-rotulo">Tierra n\.º 12<\/span>/);
  const sinRotulo = await htmlDeLaTarjeta();
  assert.doesNotMatch(sinRotulo, /tarjeta-rotulo/, "una tierra sin número no lleva el hueco del rótulo");
});

test("los datos con su nombre delante, que es lo que hace falta para un código", async () => {
  const html = await htmlDeLaTarjeta({
    filas: [
      { etiqueta: "Referencia oficial SIGPAC", valor: "37-70-0-0-503-51-1" },
      { etiqueta: "Cultivo de este año", valor: "Cebada · secano" },
    ],
  });
  assert.match(
    html,
    /<span class="tarjeta-fila"><span class="tarjeta-fila-etiqueta">Referencia oficial SIGPAC<\/span><span class="tarjeta-fila-valor">37-70-0-0-503-51-1<\/span>/,
  );
  assert.match(html, /<span class="tarjeta-fila-valor">Cebada · secano<\/span>/);
  assert.doesNotMatch(await htmlDeLaTarjeta(), /tarjeta-fila/, "sin datos con nombre no se pinta la fila");
});

test("lo que le falta a la tierra va en su franja, y el pie dice qué pasa al tocarla", async () => {
  const html = await htmlDeLaTarjeta({
    pendiente: "Le falta decir qué tiene sembrado este año",
    accionTexto: "DECIR QUÉ HAY SEMBRADO",
  });
  assert.match(html, /<span class="tarjeta-aviso">[\s\S]*Le falta decir qué tiene sembrado este año/);
  // El «!» de la franja es un dibujo, no una frase: va marcado con `aria-hidden` para que quien no ve
  // la pantalla no oiga un signo de exclamación suelto.
  assert.match(html, /<span class="tarjeta-aviso-icono" aria-hidden="true">!<\/span>/);
  assert.match(html, /<span class="tarjeta-accion">DECIR QUÉ HAY SEMBRADO<span class="flecha"/);
  const sinPendiente = await htmlDeLaTarjeta();
  assert.doesNotMatch(sinPendiente, /tarjeta-accion/, "una tierra sin nada pendiente no lleva pie de acción");
});

test("una tarjeta que no elige nada no lleva el círculo de elegir", async () => {
  // El círculo dice «esto se toca y queda elegido». En «mis cosas» la tarjeta **abre** lo que hay
  // sembrado en esa tierra: no se elige nada, así que el círculo sobra (y engañaría).
  const html = await htmlDeLaTarjeta({ marca: false, accion: "cultivo-decir", datos: { id: 7 } });
  assert.doesNotMatch(html, /tarjeta-marca/, "sigue prometiendo una elección que no existe");
  // Y sigue siendo un botón que hace algo: lo que cambia es lo que hace, no que lo haga.
  assert.match(html, /^<button type="button" class="tarjeta" data-accion="cultivo-decir"/);
  assert.match(html, /data-id="7"/);
});

// ---------------------------------------------------------------------------
// El armazón del ordenador: el menú lateral y la barra de arriba (30/09/2026)
//
// Lo pidió David: *«debe ser responsive para usarse en pc y móvil, no solo móvil… no es una app usable de
// gestión»*. Es **una pieza y no una pantalla** (`react/piezas/marco.js`): va fuera del contenedor de las
// pantallas y lleva a cada módulo. Lo que se comprueba aquí es lo que se ve dentro; el cableado (que se le
// pasen los módulos, la cuenta y el año, y que marque el módulo en el que se está) está en
// `tests_js/interfaz.test.js`.
// ---------------------------------------------------------------------------

/** Los textos del armazón, copiados de `textos.py`. */
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
  acciones: { volver: "VOLVER" },
};

/** Los módulos, como los prepara `app.js` (los tres primeros bastan para lo que se mira aquí). */
function modulosDePrueba() {
  return [
    { clave: "panel", etiqueta: "Panel", accion: "ir-inicio", activo: false },
    { clave: "cuaderno", etiqueta: "Mi cuaderno", accion: "inicio", datos: { ir: "mi_cuaderno" }, activo: true },
    { clave: "tierras", etiqueta: "Mis parcelas, productos y máquinas", accion: "inicio", datos: { ir: "mis_cosas" }, activo: false },
    { clave: "facturas", etiqueta: "Mis facturas", accion: "facturas-abrir", activo: false },
  ];
}

async function htmlDelMarco(cambios = {}) {
  const { Marco } = await import(`../web/react/piezas/marco.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(Marco, {
      textos: structuredClone(TEXTOS_DEL_MARCO),
      cuenta: "David Pérez Velasco",
      campana: "2026",
      modulos: modulosDePrueba(),
      ...cambios,
    }),
  );
}

test("el menú lleva todos los módulos, cada uno con su acción", async () => {
  const html = await htmlDelMarco();
  assert.match(html, /<p class="menu-marca">Menú<\/p>/);
  // Quién está apuntando, arriba: una cuenta puede entrar en varias fincas.
  assert.match(html, /<p class="menu-cuenta">David Pérez Velasco<\/p>/);
  // Cada módulo es un botón con su acción y sus datos: el mismo `data-accion` que el manejador de clics
  // de la aplicación, así que el menú y las pantallas no son dos mundos.
  for (const [id, accion] of [
    ["menu-panel", "ir-inicio"],
    ["menu-cuaderno", "inicio"],
    ["menu-tierras", "inicio"],
    ["menu-facturas", "facturas-abrir"],
  ]) {
    assert.ok(html.includes(`id="${id}"`), `falta el módulo ${id}`);
    assert.match(html, new RegExp(`id="${id}"[^>]*data-accion="${accion}"`), `${id} no lleva su acción`);
  }
  // Y los datos del módulo que los necesita (a dónde va `ir-inicio`).
  assert.match(html, /id="menu-cuaderno"[^>]*data-ir="mi_cuaderno"/);
});

test("el módulo en el que se está va marcado, y con palabras además del color", async () => {
  // El color solo no informa (regla de la casa): el módulo activo lleva su clase, su `aria-current` y va en
  // negrita. Sin esto, un menú no dice dónde estás, que es la mitad de para qué sirve.
  const html = await htmlDelMarco();
  assert.match(html, /id="menu-cuaderno" class="menu-enlace menu-activo"|class="menu-enlace menu-activo"[^>]*id="menu-cuaderno"/);
  assert.match(html, /id="menu-cuaderno"[^>]*aria-current="page"/);
  assert.equal(
    (html.match(/menu-activo/g) || []).length,
    1,
    "hay más de un módulo marcado como el que se está viendo",
  );
  // Y los demás no lo llevan.
  assert.doesNotMatch(html, /id="menu-panel"[^>]*menu-activo/);
});

test("la barra dice el año y la cuenta, y lleva el botón de apuntar", async () => {
  const html = await htmlDelMarco();
  // El año que se está llevando: es lo que evita apuntar en el año que no es.
  assert.match(html, /<span class="barra-rotulo">Campaña<\/span><span class="barra-valor">2026<\/span>/);
  assert.match(html, /<span class="barra-rotulo">Tu cuenta<\/span><span class="barra-valor">David Pérez Velasco<\/span>/);
  // Y los botones: el de cerrar el menú (que solo se ve cuando el menú se abre encima, en el móvil y en
  // las ventanas estrechas: 07/10/2026), apuntar (lo que más se usa), la letra grande y salir.
  const acciones = botonesDe(html).map((boton) => boton.accion);
  assert.deepEqual(acciones, [
    "menu-cerrar",
    "ir-inicio",
    "inicio",
    "inicio",
    "facturas-abrir",
    "ir-inicio",
    "cambiar-letra",
    "salir",
  ]);
  assert.match(html, /data-accion="ir-inicio">APUNTAR</);
});

test("sin año y sin cuenta no se queda un hueco", async () => {
  // Una finca recién creada no tiene año (o el agricultor acaba de entrar y no hay nombre guardado): el
  // hueco se tapa con la palabra del servidor, nunca con un guion ni con un cero.
  const html = await htmlDelMarco({ cuenta: "", campana: "" });
  assert.match(html, /<span class="barra-valor">Sin año<\/span>/);
  assert.match(html, /<p class="menu-cuenta">Tu cuenta<\/p>/);
});

test("el armazón no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDelMarco();
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS_DEL_MARCO),
    ...todosLosTextos({ modulos: modulosDePrueba() }),
    "David Pérez Velasco",
    "2026",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// La ficha de una compra (S11, 09/10/2026)
// ---------------------------------------------------------------------------

/** Los textos de la ficha, los mismos que sirve `/api/interfaz` en la clave `compra`. */
const TEXTOS_DE_LA_COMPRA = {
  titulo: "La compra",
  buscando: "Buscando la compra…",
  los_albaranes: "Los albaranes de esta compra",
  sin_albaran: "De esta compra no ha entrado nada todavía.",
  el_dinero: "El dinero de esta compra",
  sin_gasto: "De esta factura todavía no hay ningún gasto apuntado, así que no se puede decir cuánto se ha pagado.",
  los_pagos: "Los pagos",
  sin_lineas: "Esta factura no trae líneas apuntadas.",
  ver_el_albaran: "VER EL ALBARÁN",
  ver_el_gasto: "VER EL GASTO",
  // **Los cuatro rótulos de la tabla de líneas** (11/10/2026). Esta copia es a mano para que la prueba no
  // dependa del servidor, y por eso **hay que traer aquí cada frase nueva**: sin ellas, la tabla se pinta
  // con las cabeceras vacías y la prueba de la presentación lo dice —que es como se ha encontrado—.
  col_producto: "Producto",
  col_facturado: "Facturado",
  col_ha_entrado: "Ha entrado",
  col_falta: "Falta",
};

/** Una compra completa: las cuatro cifras, un albarán, sus líneas, un gasto y un pago. */
function unaCompraDePrueba(cambios = {}) {
  return {
    titulo: "COOPERATIVA AGRICOLA · 2026/00123",
    cuando: "15/03/2026 · COOPERATIVA AGRICOLA",
    cifras: [
      { etiqueta: "Facturado", valor: "663,00 €", pista: "Lo que dice la factura del proveedor." },
      { etiqueta: "Recibido", valor: "300,00 kg", pista: "Lo que ha entrado de verdad en el almacén. Lo mete el albarán, no la factura." },
      { etiqueta: "Pagado", valor: "200,00 €", pista: "El dinero que ya ha salido para esta compra." },
      { etiqueta: "Pendiente", valor: "463,00 €", pista: "Lo que queda por pagar de esta compra." },
    ],
    albaranes: [
      {
        id: 8,
        titulo: "A-2026-0001",
        cuando: "16/03/2026",
        trajo: "300,00 kg",
        anulado: "",
      },
    ],
    lineas: [
      {
        descripcion: "Abono compuesto 15-15-15",
        facturado: "500,00 kg",
        recibido: "De esta línea han entrado 300,00 kg de 500,00 kg.",
        falta: "Falta por llegar: 200,00 kg",
      },
    ],
    gastos: [
      {
        id: 165,
        concepto: "Compra de abono, factura 2026/00123",
        importe: "663.00",
        pagado: "Pagado: 200.00",
        pendiente: "Pendiente: 463.00",
      },
    ],
    pagos: [
      {
        cuando: "20/03/2026 · transferencia",
        importe: "200.00",
        aplicado: "De ese pago, a esta compra: 200.00",
      },
    ],
    avisos: [],
    las_lineas: "Lo que trae la factura",
    acciones: [{ etiqueta: "VOLVER A MIS FACTURAS", accion: "facturas-abrir", clase: "boton-claro" }],
    ...cambios,
  };
}

/** El HTML de la ficha, tal y como lo dibujaría React. */
async function htmlDeLaCompra({ textos = TEXTOS_DE_LA_COMPRA, compra = unaCompraDePrueba(), ...resto } = {}) {
  const { PantallaCompra } = await import(
    `../web/react/pantallas/compra.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaCompra, { textos, compra, cargando: false, error: "", ...resto }),
  );
}

test("la ficha de una compra enseña las cuatro cifras: facturado, recibido, pagado y pendiente", async () => {
  // **Es lo que el encargo pide ver de un vistazo**, y son cuatro cosas que se confunden con
  // facilidad: la factura no mete mercancía (la mete el albarán) y el dinero puede ir por partes.
  const html = await htmlDeLaCompra();
  for (const [etiqueta, cifra] of [
    ["Facturado", "663,00 €"],
    ["Recibido", "300,00 kg"],
    ["Pagado", "200,00 €"],
    ["Pendiente", "463,00 €"],
  ]) {
    assert.ok(html.includes(etiqueta), `falta la etiqueta «${etiqueta}»`);
    assert.ok(html.includes(cifra), `falta la cifra «${cifra}»`);
  }
  // Y cada una con la frase que dice de dónde sale: un número sin de dónde sale no se puede comprobar.
  assert.ok(html.includes("Lo mete el albarán"), "falta la pista de lo recibido");
});

test("la ficha lleva a sus albaranes y a sus gastos, y no los mete en la misma lista", async () => {
  // **Los enlaces de la ficha**: de aquí se va al albarán y al gasto, que es lo que permite comprobar
  // cada cifra en su sitio. Y son listas distintas a propósito: la mercancía y el dinero no se mezclan.
  const html = await htmlDeLaCompra();
  assert.match(
    html,
    /data-accion="albaran-abrir"[^>]*data-id="8"/,
    "el albarán de la compra no lleva a su ficha",
  );
  assert.match(
    html,
    /data-accion="gasto-abrir"[^>]*data-id="165"/,
    "el gasto de la compra no lleva a su ficha",
  );
  assert.ok(
    html.indexOf("Los albaranes de esta compra") < html.indexOf("El dinero de esta compra"),
    "la mercancía va antes que el dinero: es el orden en que pasan las cosas",
  );
});

test("la ficha presenta los cuatro indicadores en cuadricula, las lineas en tabla y el dinero aparte", async () => {
  // **La presentación, no solo el contenido** (11/10/2026). Lo pidió David con estas palabras: «cuatro
  // indicadores en una fila o cuadrícula en escritorio, líneas en tabla y documentos/pagos claramente
  // separados». El contenido ya estaba reunido; lo que faltaba era la forma, y sin una prueba se puede
  // volver a la columna de móvil sin que nadie se entere (que es lo que pasó: las clases de la ficha
  // **no existían** en `estilos.css` y salía en columna también en el ordenador).
  const html = await htmlDeLaCompra();

  // 1. Los cuatro indicadores, cada uno en su caja, dentro de la rejilla que `estilos.css` pone en fila.
  assert.match(html, /class="ficha-resumen-cifras"/, "la rejilla de las cuatro cifras no está");
  const cajas = html.match(/class="ficha-resumen"/g) || [];
  assert.equal(cajas.length, 4, `la rejilla tiene que tener cuatro cajas, tiene ${cajas.length}`);

  // 2. Las líneas, en una **tabla** de verdad, con sus cuatro columnas y dentro del contenedor que la
  //    desplaza en el móvil en vez de apilarla.
  assert.match(html, /<table class="tabla"/, "las líneas no van en una tabla");
  assert.match(html, /class="tabla-scroll ficha-lineas"/, "la tabla no está en su contenedor desplazable");
  for (const columna of ["Producto", "Facturado", "Ha entrado", "Falta"]) {
    assert.ok(
      html.includes(`>${columna}</th>`) || html.includes(columna),
      `falta la columna «${columna}» de la tabla de líneas`,
    );
  }
  assert.match(html, /<tbody>[\s\S]*<tr>/, "la tabla no trae sus filas");

  // 3. Los dos bloques: lo que ha llegado y el dinero, cada uno en su `section` con su raya.
  const bloques = html.match(/class="ficha-bloque"/g) || [];
  assert.equal(bloques.length, 2, `tienen que ser dos bloques separados, son ${bloques.length}`);
  const primero = html.indexOf('class="ficha-bloque"');
  const segundo = html.indexOf('class="ficha-bloque"', primero + 1);
  assert.ok(
    html.indexOf("Los albaranes de esta compra") > primero &&
      html.indexOf("Los albaranes de esta compra") < segundo,
    "los albaranes van en el bloque de lo que ha llegado",
  );
  assert.ok(
    html.indexOf("El dinero de esta compra") > segundo,
    "el dinero va en el segundo bloque, separado de la mercancía",
  );
});

test("la ficha dice lo que no se puede saber en vez de enseñar un cero", async () => {
  // La regla del «no lo sé» del programa entero: una línea sin enganche con el albarán **no** ha
  // recibido cero, es que no se puede saber. Y una compra de la que no ha entrado nada lo dice con sus
  // palabras, en vez de callarse.
  const html = await htmlDeLaCompra({
    compra: unaCompraDePrueba({
      albaranes: [],
      cifras: [
        { etiqueta: "Facturado", valor: "663,00 €", pista: "" },
        { etiqueta: "Recibido", valor: "Nada todavía", pista: "" },
        { etiqueta: "Pagado", valor: "0,00 €", pista: "" },
        { etiqueta: "Pendiente", valor: "663,00 €", pista: "" },
      ],
      lineas: [
        {
          descripcion: "Abono compuesto 15-15-15",
          facturado: "500,00 kg",
          recibido: "De esta línea no se puede saber cuánto ha entrado.",
          falta: "",
        },
      ],
      avisos: ["De esta factura no ha entrado nada al almacén todavía: la mercancía la mete el albarán."],
    }),
  });
  assert.ok(html.includes("Nada todavía"), "sin albaranes se dice, no se pone un cero");
  assert.ok(html.includes("no se puede saber"), "lo que no se sabe se declara");
  assert.ok(html.includes("la mercancía la mete el albarán"), "falta el aviso de por qué no ha entrado nada");
  assert.ok(
    html.includes("De esta compra no ha entrado nada todavía."),
    "sin albaranes, su lista lo dice",
  );
});

// ---------------------------------------------------------------------------
// El cobro repartido entre varias facturas (CRM-01, 11/10/2026)
// ---------------------------------------------------------------------------

/** Los textos del bloque del cobro, los que la ficha necesita para decir cada cosa. */
const TEXTOS_DEL_COBRO = {
  cobro: {
    imputado: "Va a la factura",
    sin_factura: "Todavía no sé de qué factura es",
    repartido_entre: "Repartido entre estas facturas",
    sin_asignar: "Sin asignar",
    forma: "Forma",
    etiqueta_forma: "Transferencia",
    cliente: "Cliente",
    referencia: "Referencia",
    sin_nada: "Todavía no has apuntado ningún cobro.",
    sin_asignar_titulo: "Cobros que todavía no sé de qué factura son",
    sin_asignar_explica: "Este dinero ha entrado y todavía no se sabe qué factura salda.",
    nuevo: "APUNTAR UN COBRO",
  },
  acciones: { volver: "VOLVER" },
};

async function htmlDeLosCobros({ cobros = [], ...resto } = {}) {
  const { pantallaDeCobros } = await import(
    `../web/react/pantallas/cobros.js?prueba=${Math.random()}`
  );
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(pantallaDeCobros, {
      textos: structuredClone(TEXTOS_DEL_COBRO),
      cobros,
      sin_asignar: [],
      resumen: "",
      error: "",
      ...resto,
    }),
  );
}

test("un cobro repartido entre varias facturas dice a cuáles va y cuánto a cada una", async () => {
  // **El caso que el encargo pide con números**: 350 repartidos entre una deuda de 100 y otra de 250. La
  // ficha miraba `factura_numero`, que en un reparto va **vacío a propósito** —el dinero vive en las
  // aplicaciones—, así que un ingreso repartido decía «sin factura»: justo lo contrario de lo que acaba de
  // hacer el agricultor. Esta prueba exige las dos partes de la respuesta y la ausencia de la mentira.
  const html = await htmlDeLosCobros({
    cobros: [
      {
        id: 1,
        fecha_linea: "",
        texto_importe: "350,00 €",
        aplicaciones: [
          { factura_emitida_id: 4, factura_numero: "F-2026-4", texto_importe: "100,00 €" },
          { factura_emitida_id: 5, factura_numero: "F-2026-5", texto_importe: "250,00 €" },
        ],
      },
    ],
  });
  assert.ok(
    html.includes("Repartido entre estas facturas"),
    `la ficha no dice que el cobro va a varias facturas:\n${html}`,
  );
  assert.ok(html.includes("F-2026-4") && html.includes("100,00 €"), "falta la primera factura y su parte");
  assert.ok(html.includes("F-2026-5") && html.includes("250,00 €"), "falta la segunda factura y su parte");
  assert.ok(
    !html.includes("Todavía no sé de qué factura es"),
    "un cobro repartido no puede decir que no se sabe de qué factura es: sí se sabe, va a dos",
  );
});

test("un cobro de una sola factura se sigue enseñando como siempre", async () => {
  // El control: lo de arriba no puede haber cambiado el caso de siempre —un cobro que salda una factura, que
  // es el A06—, ni el de un dinero que todavía no se sabe a qué va.
  const deUna = await htmlDeLosCobros({
    cobros: [
      {
        id: 1,
        fecha_linea: "",
        texto_importe: "40,00 €",
        factura_numero: "F-2026-1",
        aplicaciones: [{ factura_emitida_id: 1, factura_numero: "F-2026-1", texto_importe: "40,00 €" }],
      },
    ],
  });
  assert.ok(deUna.includes("Va a la factura") && deUna.includes("F-2026-1"), "el caso de una sola factura ha cambiado");
  assert.ok(!deUna.includes("Repartido entre estas facturas"), "con una sola factura no se habla de reparto");

  const sinSaber = await htmlDeLosCobros({
    cobros: [{ id: 2, fecha_linea: "", texto_importe: "300,00 €", aplicaciones: [] }],
  });
  assert.ok(
    sinSaber.includes("Todavía no sé de qué factura es"),
    "un dinero que no se sabe a qué va tiene que seguir diciéndolo",
  );
});


test("la lista de cobros, en el ordenador, va en tabla y dice a qué factura va cada uno", async () => {
  // **La tabla del ordenador de la lista de cobros** (11/10/2026). Se pasó de una tarjeta por cobro a una
  // tabla con columnas, y esto lo deja escrito: si alguien la quita, se entera.
  //
  // **Y con el caso que casi se cuela**: un cobro **repartido** entre varias facturas no lleva
  // `factura_numero` (el dinero vive en las aplicaciones) y la primera versión de la tabla caía en el
  // respaldo y escribía «Todavía no sé de qué factura es», justo lo contrario de la verdad. Aquí se exige
  // que diga **a qué facturas va**.
  const html = await htmlDeLosCobros({
    cobros: [
      {
        id: 1,
        fecha_linea: "20/07/2026",
        texto_importe: "350,00 €",
        cliente: "Cooperativa Agrícola de Peñaranda",
        etiqueta_forma: "Transferencia",
        aplicaciones: [
          { factura_emitida_id: 4, factura_numero: "F-2026-4", texto_importe: "100,00 €" },
          { factura_emitida_id: 5, factura_numero: "F-2026-5", texto_importe: "250,00 €" },
        ],
      },
      {
        id: 2,
        fecha_linea: "21/07/2026",
        texto_importe: "40,00 €",
        factura_numero: "F-2026-9",
        etiqueta_forma: "Efectivo",
      },
    ],
  });
  assert.ok(html.includes('class="tabla"'), `la lista de cobros no va en tabla:\n${html}`);
  assert.ok(html.includes("solo-escritorio"), "la tabla tiene que ir en la parte de escritorio");
  assert.ok(html.includes("F-2026-4") && html.includes("F-2026-5"), "un reparto tiene que decir a qué facturas va");
  assert.ok(
    !html.includes("Todavía no sé de qué factura es"),
    "un cobro repartido SÍ sabe de qué factura es: no puede decir lo contrario",
  );
  assert.ok(html.includes("F-2026-9"), "y un cobro de una sola factura, también");
  assert.ok(
    (html.match(/tabla-acciones/g) || []).length >= 2,
    "cada fila lleva su columna de acciones",
  );
});

// ---------------------------------------------------------------------------
// La ficha de un gasto: el camino de vuelta a la de su proveedor (Entrega 1)
// ---------------------------------------------------------------------------

/** El cargador de la ficha de un gasto, con la caché rota como los demás de este fichero. */
async function cargarLosGastos() {
  return import(`../web/react/pantallas/gastos.js?prueba=${Math.random()}`);
}

/** El HTML de la ficha de un gasto, tal y como lo dibujaría React. */
async function htmlDeUnGasto(gasto = {}, cambios = {}) {
  const { PantallaDeUnGasto } = await cargarLosGastos();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDeUnGasto, {
      textos: {
        gasto: { ficha_del_proveedor: "Ver la ficha de su proveedor" },
        acciones: { volver: "VOLVER" },
      },
      gasto,
      ...cambios,
    }),
  );
}

test("la ficha de un gasto lleva a la de su proveedor, y no lo enseña si no sabe de quién es", async () => {
  // **POR QUÉ** (Entrega 1, 13/10/2026). La revisión del saldo midió que, desde el documento, el botón «volver»
  // llevaba a la lista de cuentas y **no había forma de volver a la ficha del contacto**, así que el criterio
  // «ficha → cifra → documento → **vuelta**» no se podía andar.
  //
  // **El botón «volver» no se toca, y es una decisión**: esa pantalla se abre también desde la lista de cuentas, y
  // mandarla siempre al contacto rompería el camino normal. Lo que se añade es un **camino propio**, que además
  // sirve por sí mismo: mirar quién es el proveedor mientras se mira lo que se le compró. Y solo es posible porque
  // **la ficha del contacto tiene dirección** (`#/contactos/<id>`).
  const conProveedor = await htmlDeUnGasto({ id: 9, concepto: "Abono", contacto_id: 22 });
  assert.ok(
    conProveedor.includes("#/contactos/22"),
    `la ficha del gasto tiene que llevar a la de su proveedor:\n${conProveedor}`,
  );
  assert.ok(conProveedor.includes("Ver la ficha de su proveedor"), "y con su rótulo");

  // Y si el gasto **no sabe** de quién es, no se inventa un enlace: uno que no lleva a ninguna parte es peor que
  // ninguno.
  const sinProveedor = await htmlDeUnGasto({ id: 9, concepto: "Abono" });
  assert.ok(
    !sinProveedor.includes("#/contactos/"),
    `sin contacto no puede haber enlace a ninguna ficha:\n${sinProveedor}`,
  );
});

// ---------------------------------------------------------------------------
// La lista de lo que hay que hacer (Entrega 3): cargador y diagnostico
// ---------------------------------------------------------------------------

async function cargarLasTareas() {
  return import(`../web/react/pantallas/tareas.js?prueba=${Math.random()}`);
}

async function htmlDeLasTareas(cambios = {}) {
  const { PantallaDeLasTareas } = await cargarLasTareas();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaDeLasTareas, {
      textos: {
        tareas: {
          titulo: "Lo que hay que hacer",
          pista: "Lo próximo, de todos tus contactos.",
          todas: "Todas",
          de_hoy: "Para hoy",
          vencidas: "Vencidas",
          sin_fecha: "Sin fecha",
          cargando: "Mirando lo que tienes…",
          que: "Qué hay que hacer",
          cuando: "Para cuándo",
          quien: "Quién",
          con_quien: "Con quién",
          vencida: "Vencida",
          ver_la_ficha: "Ver la ficha",
          hecha: "Hecha",
          cancelar: "Cancelar",
          ya_hecha: "Ya hecha",
          ya_cancelada: "Cancelada",
          no_hay_ninguna: "No hay nada apuntado.",
        },
        acciones: { volver: "VOLVER" },
      },
      tareas: [
        { id: 1, contacto_id: 7, titulo: "Llevar la factura", fecha_texto: "12/10/2026", vencida: true, estado: "pendiente", responsable: "Ana" },
        { id: 2, contacto_id: 8, titulo: "Llamar por el pienso", fecha_texto: "14/10/2026", vencida: false, estado: "pendiente" },
        { id: 3, contacto_id: 7, titulo: "Ya hecha", fecha_texto: "Sin fecha", vencida: false, estado: "hecha" },
      ],
      filtros: { vencimiento: "vencidas" },
      contactos: { 7: "Cooperativa de Peñaranda" },
      cargando: false,
      error: "",
      aviso: "",
      ...cambios,
    }),
  );
}


test("la lista enseña lo que hay que hacer, marca lo vencido y solo deja cerrar lo pendiente", async () => {
  // **POR QUÉ** (Entrega 3, 13/10/2026). Esta es la pantalla donde el agricultor pregunta «¿qué tengo que hacer
  // hoy?», y tiene que decir tres cosas de un vistazo: **qué**, **para cuándo** y **con quién**. Lo vencido va
  // marcado (y **no** cancelado: eso lo decide él), y una tarea cerrada **no lleva botones**.
  //
  // **Y está escrita sobre lo que se ve**, no sobre lo que yo creía: antes de escribirla imprimí el HTML de verdad.
  const html = await htmlDeLasTareas();

  assert.ok(html.includes("Lo que hay que hacer"), `falta el título:\n${html}`);
  // Los cuatro filtros, y **el elegido marcado**: el que está puesto pierde la clase clara, así que se ve cuál manda.
  const filtros = [...html.matchAll(/data-accion="tareas-ver"[^>]*?(?:data-vencimiento="([a-z_]+)")?>/g)].map((c) => c[1] || "");
  assert.deepEqual(filtros.sort(), ["", "hoy", "sin_fecha", "vencidas"], `faltan filtros:\n${html}`);
  assert.ok(
    /data-accion="tareas-ver" data-vencimiento="vencidas">/.test(html),
    "el filtro puesto tiene que verse como el puesto (sin la clase clara)",
  );

  // La fila vencida: su día, la marca y la fila señalada.
  assert.ok(html.includes("12/10/2026"), "el día de la tarea");
  assert.ok(html.includes("fila-vencida"), "y la fila señalada como vencida");
  assert.ok(html.includes(">Vencida<"), "con su palabra");

  // **El enlace a la ficha del contacto**: con el nombre cuando se sabe, y con «Ver la ficha» cuando no.
  assert.ok(html.includes('href="#/contactos/7"') && html.includes("Cooperativa de Peñaranda"), "el enlace con su nombre");
  assert.ok(html.includes('href="#/contactos/8"') && html.includes("Ver la ficha"), "y sin nombre, un enlace que sirve igual");

  // **Los pares botón/tarea**: solo lo pendiente puede cerrarse, y cada botón dice qué tarea.
  const pares = [...html.matchAll(/data-accion="(tarea-[a-z]+)"[^>]*data-tarea="(\d+)"/g)].map((c) => [c[1], c[2]]);
  assert.deepEqual(
    pares.sort(),
    [
      ["tarea-cancelar", "1"],
      ["tarea-cancelar", "2"],
      ["tarea-completar", "1"],
      ["tarea-completar", "2"],
    ],
    `solo las pendientes pueden cerrarse:\n${html}`,
  );

  // Sin nada, se dice; y mientras se mira, también.
  const vacia = await htmlDeLasTareas({ tareas: [] });
  assert.ok(vacia.includes("No hay nada apuntado"), "sin tareas se dice, no se enseña una tabla vacía");
  const cargando = await htmlDeLasTareas({ tareas: [], cargando: true });
  assert.ok(cargando.includes("Mirando lo que tienes"), "y mientras se mira, se dice que se está mirando");
});

// ---------------------------------------------------------------------------
// ***D03: un fallo de facturas no es «no hay facturas»*** (21/10/2026)
// ---------------------------------------------------------------------------

test("con la carga fallida, las facturas dicen que no se pudo cargar, no que no hay", async () => {
  // *«Un fallo de facturas no implica cero facturas»* (encargo, D03). **La lista no puede afirmar nada sobre la
  // finca cuando lo que ha fallado es la red**: *«todavia no hay facturas» es una afirmacion sobre lo que el
  // agricultor tiene, y no se puede hacer sin haber podido preguntar.*
  const { PantallaFacturas } = await import(
    `../web/react/pantallas/facturas.js?prueba=${Math.random()}`
  );
  const textos = {
    facturas: {
      sin_facturas: "Todavía no hay facturas.",
      sin_facturas_pista: "Añade la primera cuando la tengas.",
      sin_facturas_fallo: "NO SE HAN PODIDO CARGAR LAS FACTURAS.",
    },
    acciones: {},
  };
  const pintar = (propiedades) =>
    globalThis.ReactDOMServer.renderToStaticMarkup(
      globalThis.React.createElement(PantallaFacturas, propiedades),
    );

  // *Con la carga fallida: **dice que no se pudo cargar**, y **NO** dice que no hay.*
  const conFallo = pintar({ textos, facturas: [], noSePudoCargar: true });
  assert.match(
    conFallo,
    /NO SE HAN PODIDO CARGAR LAS FACTURAS/,
    `***tiene que decir que no se pudo cargar***: ${conFallo.slice(0, 300)}`,
  );
  assert.ok(
    !conFallo.includes("Todavía no hay facturas"),
    `***y NO puede decir que no hay***: ${conFallo.slice(0, 300)}`,
  );

  // *Y el control positivo: con la lista vacía **de verdad**, sí se dice que no hay.*
  const sinFallo = pintar({ textos, facturas: [] });
  assert.match(
    sinFallo,
    /Todavía no hay facturas/,
    `***una lista vacia de verdad si lo dice***: ${sinFallo.slice(0, 300)}`,
  );
});

test("un fallo de cobros no se pinta como «no has cobrado nada»", async () => {
  // *El mismo patron que en facturas, en la pantalla del **dinero**: sin poder preguntar, no se puede afirmar
  // nada sobre lo que el agricultor ha cobrado.*
  const { PantallaCobros } = await import(`../web/react/pantallas/cobros.js?prueba=${Math.random()}`);
  const textos = {
    cobro: {
      titulo: "Los cobros",
      sin_nada: "Todavía no has cobrado nada.",
      sin_cobros_fallo: "NO SE HAN PODIDO CARGAR LOS COBROS.",
    },
    acciones: {},
  };
  const pintar = (propiedades) =>
    globalThis.ReactDOMServer.renderToStaticMarkup(
      globalThis.React.createElement(PantallaCobros, propiedades),
    );

  const conFallo = pintar({ textos, cobros: [], sin_asignar: [], noSePudoCargar: true });
  assert.match(conFallo, /NO SE HAN PODIDO CARGAR LOS COBROS/, conFallo.slice(0, 300));
  assert.ok(
    !conFallo.includes("Todavía no has cobrado nada"),
    `***y NO puede decir que no has cobrado***: ${conFallo.slice(0, 300)}`,
  );

  const sinFallo = pintar({ textos, cobros: [], sin_asignar: [] });
  assert.match(sinFallo, /Todavía no has cobrado nada/, sinFallo.slice(0, 300));
});

test("un fallo de ventas no se pinta como «no has vendido nada»", async () => {
  // *La tercera pantalla con el patron, y la **tercera de dinero**. Y aqui manda sobre el «vacio por filtro»:
  // sin datos que filtrar, decir «con ese filtro no hay nada» es mentira por partida doble.*
  const { PantallaVentas } = await import(`../web/react/pantallas/ventas.js?prueba=${Math.random()}`);
  const textos = {
    venta: {
      titulo: "Las ventas",
      sin_nada: "Todavía no has vendido nada.",
      vacio_filtro: "Con ese filtro no hay nada.",
      sin_ventas_fallo: "NO SE HAN PODIDO CARGAR LAS VENTAS.",
    },
    acciones: {},
    tabla: {},
  };
  const pintar = (propiedades) =>
    globalThis.ReactDOMServer.renderToStaticMarkup(
      globalThis.React.createElement(PantallaVentas, { textos, ...propiedades }),
    );

  const conFallo = pintar({ tabla: { filas: [] }, noSePudoCargar: true });
  assert.match(conFallo, /NO SE HAN PODIDO CARGAR LAS VENTAS/, conFallo.slice(0, 300));
  assert.ok(
    !conFallo.includes("Todavía no has vendido nada"),
    `***y NO puede decir que no has vendido***: ${conFallo.slice(0, 300)}`,
  );

  // *Y con un filtro puesto, un fallo **tampoco** es «no hay nada con ese filtro».*
  const conFiltro = pintar({ tabla: { filas: [] }, filtros: { q: "trigo" }, noSePudoCargar: true });
  assert.ok(
    !conFiltro.includes("Con ese filtro no hay nada"),
    `***sin datos, un filtro no puede decir nada***: ${conFiltro.slice(0, 300)}`,
  );

  const sinFallo = pintar({ tabla: { filas: [] } });
  assert.match(sinFallo, /Todavía no has vendido nada/, sinFallo.slice(0, 300));
});

