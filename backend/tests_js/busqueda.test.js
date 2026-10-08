/**
 * La búsqueda global: lo que la pantalla tiene que enseñar, ya traducido.
 *
 * Es la parte con decisiones —cómo se llama cada grupo, qué se dice cuando no se ha buscado nada, qué se
 * dice cuando un grupo se ha cortado— y por eso vive en `nucleo.js`: **aquí se prueba sin navegador**. La
 * pantalla que venga después solo tiene que pintar lo que esto devuelve.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

import { losGruposDeLaBusqueda } from "../web/nucleo.js";

// ---------------------------------------------------------------------------
// La pantalla, dibujada de verdad con React (sin navegador: `renderToStaticMarkup`)
// ---------------------------------------------------------------------------

globalThis.self = globalThis;

function cargarDeVendor(nombre) {
  const codigo = readFileSync(new URL(`../web/vendor/${nombre}`, import.meta.url), "utf8");
  vm.runInThisContext(codigo, { filename: nombre });
}

cargarDeVendor("react.production.min.js");
cargarDeVendor("react-dom-server-legacy.browser.production.min.js");
cargarDeVendor("htm.umd.js");

async function htmlDeLaBusqueda(propiedades) {
  const modulo = await import(`../web/react/pantallas/buscar.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    globalThis.React.createElement(modulo.PantallaBuscar, propiedades),
  );
}

const TEXTOS_PANTALLA = {
  buscar: {
    titulo: "Buscar",
    caja: "Buscar en tu cuaderno",
    pista: "Escribe al menos dos letras.",
    boton: "BUSCAR",
    ver: "VER",
    sin_buscar: "Escribe lo que buscas y pulsa BUSCAR.",
    sin_resultados: "No hay nada que se llame así.",
    cortado: "Hay más de los que caben aquí: afina lo que buscas.",
    grupo_tierras: "Tierras",
    grupo_gastos: "Gastos",
  },
};

const TEXTOS = {
  sin_buscar: "Escribe lo que buscas y pulsa BUSCAR.",
  sin_resultados: "No hay nada que se llame así.",
  cortado: "Hay más de los que caben aquí: afina lo que buscas.",
  grupo_tierras: "Tierras",
  grupo_gastos: "Gastos",
};

const UNA_RESPUESTA = {
  texto: "prado",
  buscado: true,
  motivo: "",
  grupos: [
    {
      clave: "tierras",
      cuantos: 1,
      cortado: false,
      resultados: [{ id: 7, etiqueta: "El Prado de arriba", detalle: "ES-P-00001-0001" }],
    },
  ],
};

test("cada grupo sale con su nombre del servidor y con sus resultados", () => {
  const salida = losGruposDeLaBusqueda(UNA_RESPUESTA, TEXTOS);
  assert.equal(salida.se_busco, true);
  assert.equal(salida.mensaje, "", "con resultados no se dice nada más");
  assert.equal(salida.grupos.length, 1);
  assert.equal(salida.grupos[0].titulo, "Tierras");
  assert.deepEqual(salida.grupos[0].lineas, [
    {
      etiqueta: "El Prado de arriba",
      detalle: "ES-P-00001-0001",
      // **Y a dónde lleva** (07/10/2026): cada línea trae su acción y su identificador, que es lo que hace
      // que un resultado se pueda abrir en vez de solo leerse.
      accion: "tierra-historia",
      id: 7,
    },
  ]);
});

test("un grupo nuevo sin nombre en los textos sale con su clave, no en blanco", () => {
  // Es a propósito: un grupo que el servidor añada mañana y no tenga su nombre en los textos se enseña con
  // su clave antes que dejar un hueco que nadie entiende.
  const salida = losGruposDeLaBusqueda(
    { buscado: true, grupos: [{ clave: "aperos", cuantos: 1, resultados: [{ etiqueta: "Rodillo" }] }] },
    TEXTOS,
  );
  assert.equal(salida.grupos[0].titulo, "aperos");
});

test("un resultado sin detalle no enseña un guion ni un cero", () => {
  // El detalle es el importe, la matrícula o el teléfono, y puede no constar. Un guion ahí diría que hay un
  // dato; un cero, que costó cero.
  const salida = losGruposDeLaBusqueda(
    { buscado: true, grupos: [{ clave: "gastos", cuantos: 1, resultados: [{ etiqueta: "Gasóleo" }] }] },
    TEXTOS,
  );
  assert.equal(salida.grupos[0].lineas[0].detalle, "");
});

test("el grupo cortado lo dice, y el que no se ha cortado no dice nada", () => {
  // Un grupo de diez resultados que en realidad son cuarenta, sin avisar, hace creer que solo hay diez.
  const cortado = losGruposDeLaBusqueda(
    { buscado: true, grupos: [{ clave: "tierras", cuantos: 10, cortado: true, resultados: [] }] },
    TEXTOS,
  );
  assert.equal(cortado.grupos[0].cortado, true);
  assert.equal(cortado.grupos[0].aviso_cortado, TEXTOS.cortado);

  const entero = losGruposDeLaBusqueda(UNA_RESPUESTA, TEXTOS);
  assert.equal(entero.grupos[0].aviso_cortado, "", "sin cortar no se avisa de nada");
});

test("«no se ha buscado» y «no hay nada» no son lo mismo", () => {
  // Con menos de dos letras el servidor no busca, y eso **no es un fracaso de la búsqueda**: son dos cosas
  // distintas y se dicen distinto.
  const sinBuscar = losGruposDeLaBusqueda({ texto: "p", buscado: false, motivo: "muy_corto", grupos: [] }, TEXTOS);
  assert.equal(sinBuscar.se_busco, false);
  assert.equal(sinBuscar.mensaje, TEXTOS.sin_buscar);

  const sinNada = losGruposDeLaBusqueda({ texto: "helicoptero", buscado: true, grupos: [] }, TEXTOS);
  assert.equal(sinNada.se_busco, true);
  assert.equal(sinNada.mensaje, TEXTOS.sin_resultados);
});

test("sin respuesta del servidor no se inventa nada", () => {
  // Si la búsqueda no ha llegado, no hay grupos y no se dice «no hay nada»: no se sabe.
  const salida = losGruposDeLaBusqueda(null, TEXTOS);
  assert.deepEqual(salida.grupos, []);
  assert.equal(salida.se_busco, false);
  assert.equal(salida.mensaje, TEXTOS.sin_buscar);
});

test("la pantalla dibuja el cuadro, el botón y los grupos con sus resultados", async () => {
  const html = await htmlDeLaBusqueda({
    textos: TEXTOS_PANTALLA,
    resultado: UNA_RESPUESTA,
  });
  assert.match(html, /Buscar en tu cuaderno/, "no sale el cuadro de buscar");
  assert.match(html, /id="buscar_global"/, "el cuadro no tiene su identificador");
  assert.match(html, /data-accion="buscar"/, "el botón no lleva la acción que lee el manejador de clics");
  assert.match(html, /BUSCAR/, "no sale el botón");
  assert.match(html, /Tierras/, "no sale el nombre del grupo, que viene del servidor");
  assert.match(html, /El Prado de arriba/, "no sale el resultado");
  assert.match(html, /ES-P-00001-0001/, "no sale el detalle del resultado");
});

test("y cada resultado **lleva a su ficha**", async () => {
  // **Un resultado que no lleva a ninguna parte no es un resultado, es un cartel** (encargo del rediseño,
  // 07/10/2026): cada línea trae su botón con la acción de su grupo y el identificador de ese resultado, que
  // es lo que el manejador de la aplicación necesita para abrir su ficha.
  const html = await htmlDeLaBusqueda({ textos: TEXTOS_PANTALLA, resultado: UNA_RESPUESTA });
  assert.match(html, /data-accion="tierra-historia"/, "un resultado de tierras no abre la ficha de su tierra");
  assert.match(html, /data-id="7"/, "el botón del resultado no lleva su identificador");
  assert.match(html, /VER/, "el botón no dice lo que hace");
});

test("cada grupo lleva a lo que tiene que llevar, y los papeles a su lista", async () => {
  // La decisión de a dónde lleva cada grupo está en `nucleo.js`, y se prueba aquí sin navegador.
  const salida = losGruposDeLaBusqueda(
    {
      texto: "x",
      buscado: true,
      grupos: [
        { clave: "tierras", cuantos: 1, resultados: [{ id: 1, etiqueta: "Una tierra" }] },
        { clave: "gastos", cuantos: 1, resultados: [{ id: 2, etiqueta: "Un gasto" }] },
        { clave: "personas", cuantos: 1, resultados: [{ id: 3, etiqueta: "Una persona" }] },
        { clave: "maquinas", cuantos: 1, resultados: [{ id: 4, etiqueta: "Una máquina" }] },
        { clave: "papeles", cuantos: 1, resultados: [{ id: 5, etiqueta: "Un papel" }] },
      ],
    },
    TEXTOS,
  );
  const acciones = salida.grupos.map((grupo) => grupo.lineas[0].accion);
  assert.deepEqual(
    acciones,
    ["tierra-historia", "gasto-abrir", "contacto-abrir", "maquina-ver", "papel-ver-todos"],
    "algún grupo no lleva a donde tiene que llevar",
  );
  // **Y los papeles, a su lista y no al fichero**: abrir el fichero es descargarlo, y una descarga no se
  // dispara sola al mirar unos resultados.
  assert.equal(salida.grupos[4].lineas[0].accion, "papel-ver-todos");
  // Y un grupo que el servidor añada mañana sin acción conocida: se enseña, pero **sin botón que no lleva a
  // ningún sitio**.
  const conGrupoNuevo = losGruposDeLaBusqueda(
    { buscado: true, grupos: [{ clave: "aperos", cuantos: 1, resultados: [{ id: 9, etiqueta: "Rodillo" }] }] },
    TEXTOS,
  );
  assert.equal(conGrupoNuevo.grupos[0].lineas[0].accion, "", "un grupo nuevo no puede inventarse una acción");
});

test("la pantalla dice que un grupo se ha cortado, y no lo calla", async () => {
  const html = await htmlDeLaBusqueda({
    textos: TEXTOS_PANTALLA,
    resultado: {
      texto: "cuesta",
      buscado: true,
      grupos: [{ clave: "tierras", cuantos: 10, cortado: true, resultados: [] }],
    },
  });
  assert.match(html, /afina lo que buscas/, "un grupo cortado sin avisar hace creer que solo hay diez");
});

test("con el cuadro vacío la pantalla no dice que no hay nada: dice que no se ha buscado", async () => {
  const html = await htmlDeLaBusqueda({ textos: TEXTOS_PANTALLA, resultado: null });
  assert.match(html, /Escribe lo que buscas/, "no se dice que hay que buscar");
  assert.doesNotMatch(html, /No hay nada que se llame/, "no se ha buscado, así que no se puede decir que no haya nada");
});
