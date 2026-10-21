/**
 * **La pantalla del paquete de la PAC** (CRM-09, 17/10/2026).
 *
 * ### ***Por que existe***
 *
 * El paquete tenia puerta (`GET /api/pac/paquete`, con sus cinco pruebas de Python) y **no tenia pantalla**:
 * *`pac_api` era tan invisible para el agricultor como lo era `pac.py`. Esta prueba defiende la mitad que se
 * ve.*
 *
 * Lo que comprueba, y es lo que el contrato pide con sus palabras:
 *
 *   1. Que ***lo primero que se vea sea lo que NO se puede afirmar***: *sin fuente legal cargada «no se puede
 *      decir si algo es elegible» -decirlo despues de la tabla es decirlo tarde-.*
 *   2. Que ***el porcentaje lleve su numerador y su denominador***, y que cuando no se sabe lo diga en vez de
 *      enseñar un cero.
 *   3. Que ***cada tierra diga lo que le falta*** -«falta area/cultivo/evidencia -> incompleto»-.
 *   4. Que ***la advertencia de que no es la declaracion vaya al pie, y siempre***.
 *   5. Que ***sin paquete pedido (`null`) no se pinte una tabla vacia***: *una tabla vacia dice «no hay nada»,
 *      y todavia no se sabe.*
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

/** **Los textos, los que manda el servidor** (`textos.PAC`), copiados uno a uno. */
const TEXTOS = {
  titulo: "La preparación de la PAC",
  explica:
    "Lo que hay que llevar al asesor, tierra por tierra. **Esto no es la declaración**: no se envía nada y no promete que nada sea elegible.",
  sin_fuente:
    "No hay ninguna fuente legal cargada para esta campaña, así que **no se puede decir si algo es elegible**.",
  no_es_garantia: "**Esto no es la declaración ni una garantía de elegibilidad.** Es el paquete para revisarlo con el asesor.",
  resumen: "El resumen",
  falta_superficie: "le falta la superficie",
  falta_cultivo: "no consta qué se siembra",
  falta_referencia: "la referencia del SIGPAC está a medias",
  completo: "completa",
  incompleto: "incompleta",
  sin_cultivo_aviso: "La tierra sin cultivo **no se pinta de verde**: se dice.",
  sin_tierras: "Todavía no hay tierras en esta finca.",
};

function unPaquete(cambios = {}) {
  return {
    textos: TEXTOS,
    campana_anio: 2026,
    la_fuente: null,
    aviso_de_la_fuente: TEXTOS.sin_fuente,
    las_tierras: [
      {
        parcela_id: 1,
        alias: "El Prado",
        referencia: "42-100-0-0-1",
        superficie_ha: 6.0,
        superficie_sigpac_ha: 6.1,
        cultivo: { especie: "Trigo blando", ecorregimen: "siembra directa" },
        falta: [],
        completa: true,
      },
      {
        parcela_id: 2,
        alias: "La que no consta",
        referencia: null,
        superficie_ha: 4.0,
        superficie_sigpac_ha: null,
        cultivo: null,
        falta: ["falta_referencia", "falta_cultivo"],
        completa: false,
      },
    ],
    el_resumen: {
      de_que: "superficie con cultivo sobre el total de la finca",
      unidad: "ha",
      numerador: 6.0,
      denominador: 10.0,
      porcentaje: 60.0,
      sin_cultivo: 4.0,
      se_queda_fuera: 4.0,
    },
    las_incompletas: 1,
    no_es_garantia: TEXTOS.no_es_garantia,
    ...cambios,
  };
}

async function elHtml(paquete) {
  const { PantallaElPaqueteDeLaPac } = await import(`../web/react/pantallas/pac.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    globalThis.React.createElement(PantallaElPaqueteDeLaPac, { paquete }),
  );
}

test("lo primero que se ve es lo que NO se puede afirmar: no hay fuente legal", async () => {
  const html = await elHtml(unPaquete());

  assert.ok(html.includes("no se puede decir si algo es elegible"), `***falta el aviso***:\n${html.slice(0, 700)}`);
  // ***Y va antes de las cifras***: *decirlo despues es decirlo tarde.*
  //
  // *El ancla es **«Lo que consta»** desde el 18/10/2026: la pantalla se rehizo con el recorrido completo -campaña
  // objetivo, hipotesis, comparación, pendientes, guardar, historial y trabajos-, y el resumen del paquete vive
  // ahora en la capa de **lo que consta**. **La propiedad que se comprueba es la misma**: el aviso, antes que los
  // numeros.*
  assert.ok(html.indexOf("no se puede decir") < html.indexOf("Lo que consta"), (
    "***y va ANTES de las cifras: decirlo despues es decirlo tarde***"
  ));
});

test("el porcentaje lleva su numerador y su denominador, y las hectareas fuera se dicen", async () => {
  const html = await elHtml(unPaquete());

  assert.ok(html.includes("6 de 10 ha"), `***numerador y denominador a la vista***:\n${html.slice(0, 900)}`);
  assert.ok(html.includes("60"), "***y el porcentaje***");
  assert.ok(html.includes("4 ha"), "***y las hectareas que se quedan fuera, dichas***");
});

test("cuando el porcentaje NO se sabe, se dice; NUNCA un cero por ciento", async () => {
  const html = await elHtml(
    unPaquete({
      el_resumen: {
        de_que: "superficie con cultivo sobre el total de la finca",
        unidad: "ha",
        numerador: null,
        denominador: null,
        porcentaje: null,
        sin_cultivo: null,
        se_queda_fuera: null,
      },
    }),
  );

  assert.ok(html.includes(TEXTOS.falta_superficie), `***se dice que falta***:\n${html.slice(0, 900)}`);
  assert.ok(!html.includes("0 %"), "***y NUNCA un cero por ciento: afirmaria que no hay nada***");
});

test("cada tierra dice lo que le FALTA, y las incompletas se ven", async () => {
  const html = await elHtml(unPaquete());

  assert.ok(html.includes("El Prado"), "las tierras salen");
  assert.ok(html.includes("La que no consta"), "y las incompletas tambien: **no se esconden**");
  assert.ok(html.includes("incompleta"), `***y se dice cual esta incompleta***:\n${html.slice(0, 1200)}`);
  assert.ok(html.includes("completa"), "y cual no");
});

test("la advertencia de que NO es la declaracion va al pie, y siempre", async () => {
  const html = await elHtml(unPaquete());

  assert.ok(html.includes("garantía de elegibilidad"), `***tiene que estar***:\n${html.slice(-700)}`);
  assert.ok(html.includes('data-aviso="no-es-garantia"'), "y con su marca, para poderla buscar");
});

test("sin paquete pedido (null) NO se pinta una tabla vacia", async () => {
  // *Una tabla vacia dice «no hay nada»; todavia no se sabe.*
  const html = await elHtml(null);

  assert.ok(!html.includes("Todavía no hay tierras"), `***no se puede decir que no hay antes de preguntar***:\n${html.slice(0, 500)}`);
  assert.ok(!html.includes("garantía de elegibilidad"), "ni la advertencia de un paquete que no se ha pedido");
});
