/**
 * **Las metricas del panel, en el inicio** (CRM-11, 17/10/2026).
 *
 * ### ***Por que existe esta prueba***
 *
 * `app/paneles.py` tenia **el contrato entero** y ***no lo llamaba nadie***. Se le dio puerta
 * (`GET /api/panel`, con sus seis pruebas de Python) y **seguia sin pantalla**: *hoy `panel_api` seria tan
 * invisible para el agricultor como lo era el modulo*. Esta prueba defiende **la mitad que se ve**.
 *
 * Lo que comprueba, y es lo que el contrato pide con sus palabras -«***valor nullable, unidad, periodo,
 * finca/campana, filtros, cobertura, fuente y enlace***»-:
 *
 *   1. Que cada tarjeta diga **que mide** y **en que se mide**: el titulo con su cifra y su unidad.
 *   2. Que diga **de donde sale** (`fuente`) y **cuanto ha mirado** (`cobertura`).
 *   3. Que ***lo que no se sabe diga «no se sabe» y NUNCA un cero***.
 *   4. Que **sin metricas pedidas (`null`) la seccion no se pinte** -la distincion de la casa: *`null` es «no
 *      se han pedido», `[]` seria «se pidieron y no hay»*-.
 *   5. Y que **avise de que las cifras no se suman**, que es la mitad del contrato que evita el error de
 *      cabeza: *dos cifras en hectareas pueden contestar a preguntas distintas.*
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

/** Los textos, **los que manda el servidor** (`textos.LAS_METRICAS`), copiados uno a uno. */
const TEXTOS = {
  titulo: "El panel de la finca",
  explica:
    "Cada cifra dice en qué se mide y de dónde sale. Las que contestan a preguntas distintas no se suman entre sí, aunque se midan en lo mismo.",
  superficie_titulo: "La tierra que hay",
  superficie_pregunta: "lo que hay plantado en la finca",
  trabajo_titulo: "Trabajo acumulado",
  trabajo_pregunta: "lo que se ha pasado por encima de la tierra, contando cada vez",
  no_se_sabe: "No se sabe",
  sin_fuente: "no dice de dónde sale",
  cobertura: "Se han mirado {contadas} de {de}.",
  no_se_suman: "Estas cifras no se suman: contestan a preguntas distintas.",
};

function unaMetrica(cambios = {}) {
  return {
    clave: "superficie",
    titulo: TEXTOS.superficie_titulo,
    valor: 4.0,
    unidad: "ha_de_superficie",
    pregunta: TEXTOS.superficie_pregunta,
    fuente: "parcelas",
    periodo: "2026",
    cobertura: { contadas: 2, de: 2 },
    ...cambios,
  };
}

async function htmlDelInicio(cambios = {}) {
  // ***Se monta `pantallaDeInicio`, que es lo que monta la aplicacion*** (CRM-11, 17/10/2026): *montar
  // `PantallaInicio` directamente **es un atajo que esconde el defecto que esta prueba tiene que cazar** -el
  // envoltorio no reenviaba `lasMetricas`, y con el atajo la seccion salia en la prueba y **no en la
  // pantalla**. Lo encontro el recorrido; esta prueba se corrigio para que lo habria encontrado ella-.*
  const { pantallaDeInicio } = await import(
    `../web/react/pantallas/inicio.js?prueba=${Math.random()}`
  );
  const propiedades = {
    textos: { inicio: {}, maestros: {}, dictado: {}, panel_de_mando: {} },
    nombre: "Ana",
    campana: { anio: 2026 },
    hayParcelas: true,
    hayUltimo: false,
    sinUltimo: "",
    mando: null,
    ...cambios,
  };
  // *Con el envoltorio: `pantallaDeInicio(propiedades)` devuelve el elemento ya montado.*
  return globalThis.ReactDOMServer.renderToStaticMarkup(pantallaDeInicio(propiedades));
}

test("cada metrica dice QUE mide, en QUE se mide, de DONDE sale y CUANTO ha mirado", async () => {
  const html = await htmlDelInicio({
    lasMetricas: { textos: TEXTOS, las_metricas: [unaMetrica()], sin_comprobar: [] },
  });

  assert.ok(html.includes(TEXTOS.superficie_titulo), `***falta el titulo***:\n${html.slice(0, 600)}`);
  assert.ok(html.includes("4 ha_de_superficie"), "***falta la cifra con su unidad***");
  assert.ok(html.includes(TEXTOS.superficie_pregunta), "***falta la pregunta: no se sabe que mide***");
  assert.ok(html.includes("parcelas"), "***falta la fuente: un numero sin origen no se puede discutir***");
  assert.ok(html.includes("Se han mirado 2 de 2."), "***falta la cobertura***");
  assert.ok(html.includes(TEXTOS.no_se_suman), "***y falta el aviso de que no se suman***");
});

test("lo que NO se sabe dice «no se sabe», y NUNCA un cero", async () => {
  const html = await htmlDelInicio({
    lasMetricas: {
      textos: TEXTOS,
      las_metricas: [unaMetrica({ valor: null, cobertura: { contadas: 1, de: 2 } })],
      sin_comprobar: [],
    },
  });

  assert.ok(html.includes(TEXTOS.no_se_sabe), `***tiene que decirlo***:\n${html.slice(0, 600)}`);
  assert.ok(!html.includes(">0 ha_de_superficie<"), "***y NUNCA un cero***");
  assert.ok(!html.includes("0 ha_de_superficie"), "***un cero afirmaria que no hay***");
});

test("sin metricas pedidas (null) la seccion NO se pinta", async () => {
  // ***La distincion de la casa***: *`null` es «todavia no se han pedido» -ni se dice ni se pinta-; `[]`
  // seria «se pidieron y no hay ninguna».* Sin ella, el inicio diria «no hay nada» antes de preguntar.
  const html = await htmlDelInicio({ lasMetricas: null });

  assert.ok(!html.includes(TEXTOS.titulo), `***no se puede ensenar un panel que no se ha pedido***:\n${html.slice(0, 400)}`);
  assert.ok(!html.includes(TEXTOS.no_se_suman), "ni su aviso");
});

test("una metrica que no se puede dar por bueno lo dice", async () => {
  const laSuya = unaMetrica({ valor: null });
  const html = await htmlDelInicio({
    lasMetricas: { textos: TEXTOS, las_metricas: [laSuya], sin_comprobar: [laSuya] },
  });

  assert.ok(html.includes(TEXTOS.sin_fuente), `***«sin cumplimiento global que tape una regla critica no comprobada»***:\n${html.slice(0, 700)}`);
});
