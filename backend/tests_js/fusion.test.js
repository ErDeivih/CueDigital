/**
 * La fusión: **cuándo la pantalla PARA y cuándo no** (Entrega 5, 14/10/2026).
 *
 * POR QUÉ ESTA PRUEBA, Y POR QUÉ AQUÍ. La vista previa avisa de las colisiones, y hay una que **no puede decidir
 * nadie**: las dos fichas con el campo de notas escrito (`Contacto.notas` es un campo de texto único, y la de una se
 * perdería). El servidor **se niega** (409) desde la ronda 98, con su prueba en rojo. Lo que faltaba por medir es **la
 * pantalla**: que **no ofrezca** el botón cuando hay que parar, y que **sí lo ofrezca** cuando la colisión se puede
 * resolver.
 *
 * Y se mide **aquí**, no en el navegador: es una pregunta **pura** —una función que recibe `previa` y devuelve HTML—
 * así que un recorrido andado es un instrumento **frágil** para ella. *Siete rondas de navegador por no haberla
 * escrito antes.*
 *
 * El dibujo es el de la casa: `renderToStaticMarkup` sobre el componente, sin navegador (como `busqueda.test.js`).
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

globalThis.self = globalThis;

function cargarDeVendor(nombre) {
  const codigo = readFileSync(new URL(`../web/vendor/${nombre}`, import.meta.url), "utf8");
  vm.runInThisContext(codigo, { filename: nombre });
}

cargarDeVendor("react.production.min.js");
cargarDeVendor("react-dom-server-legacy.browser.production.min.js");
cargarDeVendor("htm.umd.js");

async function htmlDeLaFusion(propiedades) {
  const modulo = await import(`../web/react/pantallas/fusion.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    globalThis.React.createElement(modulo.PantallaDeLaFusion, propiedades),
  );
}

const TEXTOS = {
  fusion: {
    titulo: "Juntar dos fichas que son la misma",
    pista: "…",
    la_que_desaparece: "La que desaparece",
    la_que_se_queda: "La que se queda",
    elije_una: "Elige una",
    ver_lo_que_pasa: "Ver lo que va a pasar",
    esto_es_lo_que_pasa: "Esto es lo que va a pasar",
    que: "Qué",
    de_la_que_desaparece: "De la que desaparece",
    de_la_que_se_queda: "De la que se queda",
    no_choca_nada: "No choca nada: se puede juntar tal cual.",
    lo_que_choca: "Lo que choca, y qué hacer",
    esto_no_lo_puede_decidir_la_pantalla: "Esto NO lo puede decidir la pantalla: hay que decidirlo antes.",
    fusionarlas: "Juntarlas",
    el_origen_no_se_borra: "La que desaparece NO se borra.",
  },
};

/** Una vista previa con lo mínimo que la pantalla mira: las once tablas y sus colisiones. */
function unaPrevia(colisiones) {
  return {
    origen: { dinero: { ventas_de_cosecha: 1 }, cuelgan: { tareas: 2 } },
    destino: { dinero: { ventas_de_cosecha: 0 }, cuelgan: { tareas: 0 } },
    colisiones,
  };
}

const LAS_NOTAS = [
  {
    que: "las_dos_tienen_notas_escritas",
    por_que: "`Contacto.notas` es un campo de texto único: no hay sitio para las dos",
    que_hacer: "hay que decidir cuáles se quedan, o copiarlas a mano antes",
    para_la_fusion: true,
  },
];

test("con una colisión que no se puede decidir, la pantalla NO ofrece juntarlas", async () => {
  const html = await htmlDeLaFusion({
    textos: TEXTOS,
    contactos: [],
    origen_id: "1",
    destino_id: "2",
    previa: unaPrevia(LAS_NOTAS),
  });
  assert.ok(
    !html.includes("Juntarlas"),
    `no puede ofrecer el botón si hay que decidir antes: ${html.slice(0, 300)}`,
  );
  assert.ok(
    html.includes("NO lo puede decidir"),
    `y tiene que decir por qué para: ${html.slice(0, 300)}`,
  );
  // Y la colisión se enseña con su porqué y su qué-hacer, que es lo que el agricultor tiene que leer.
  assert.ok(html.includes("campo de texto único"), "el porqué de la colisión tiene que verse");
  assert.ok(html.includes("copiarlas a mano"), "y qué puede hacer");
});

test("con una colisión que SÍ se puede resolver, la pantalla ofrece juntarlas", async () => {
  // El otro lado, que es el que impide pasarse de listo: **negarse de más también sería un defecto**.
  const se_puede = [{ que: "el_papel_repetido", por_que: "hay dos papeles iguales", que_hacer: "se juntan" }];
  const html = await htmlDeLaFusion({
    textos: TEXTOS,
    contactos: [],
    origen_id: "1",
    destino_id: "2",
    previa: unaPrevia(se_puede),
  });
  assert.ok(html.includes("Juntarlas"), `aquí sí se puede juntar: ${html.slice(0, 300)}`);
  assert.ok(!html.includes("NO lo puede decidir"), "y no tiene que decir que hay que parar");
});

test("sin colisiones, tampoco para, y lo dice", async () => {
  const html = await htmlDeLaFusion({
    textos: TEXTOS,
    contactos: [],
    origen_id: "1",
    destino_id: "2",
    previa: unaPrevia([]),
  });
  assert.ok(html.includes("Juntarlas"), "no hay nada que decidir: se puede juntar");
  assert.ok(html.includes("No choca nada"), "y se dice que no choca nada");
});

test("con la vista previa sin cargar, no se ofrece juntar nada a ciegas", async () => {
  const html = await htmlDeLaFusion({
    textos: TEXTOS,
    contactos: [],
    origen_id: "",
    destino_id: "",
    previa: null,
  });
  assert.ok(!html.includes("Juntarlas"), "sin vista previa no se junta nada");
});
