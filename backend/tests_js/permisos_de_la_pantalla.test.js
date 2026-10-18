/**
 * **Los permisos de la pantalla, por el EFECTO REAL de cada accion** (18/10/2026).
 *
 * ### ***Lo que la revision independiente demostro, y que esta prueba fija***
 *
 * *El clasificador anterior miraba **el sufijo del nombre** -`guardar`, `anular`, `quitar`...-. Y se quedaba
 * corto con **siete** acciones, que la revision reproduce una a una:*
 *
 *     contacto-borrar-si   -> borraElContacto        (DELETE del contacto)
 *     fusion-hacer         -> mandarCambio            (POST de fusion)
 *     fusion-deshacer      -> mandarCambio            (POST)
 *     contacto-nota        -> apunta una nota
 *     contacto-baja        -> cambia el uso del contacto
 *     banco-deshacer       -> deshace una conciliacion
 *     bandeja-confirmar    -> confirma un papel
 *
 * ***«Una confirmacion puede ser precisamente la operacion destructiva.»*** *Con el clasificador viejo, un
 * usuario de consulta **veia el boton de fusionar** y solo se enteraba al pulsarlo.*
 *
 * ### ***Y por que esta prueba no es circular***
 *
 *  1. **Las siete de la revision se nombran una a una** y tienen que estar en el inventario. *Eso no lo
 *     descubre el analisis: lo dijo la revision.*
 *  2. **El inventario se vuelve a sacar del codigo** y se compara. *Si alguien anade un manejador que escribe y
 *     no lo apunta, **falla y lo nombra**.*
 *  3. **Y `Boton` se prueba con `fusion-hacer`**, que es el caso que la revision reprodujo: con la escritura
 *     apagada, **no se pinta**.
 *  4. **Y las de sesion no se esconden**: *`entrar` es el boton de entrar; esconderlo dejaria al agricultor
 *     fuera.*
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

const APP = readFileSync(new URL("../web/app.js", import.meta.url), "utf8");

/**
 * **Vuelve a sacar del codigo las acciones que escriben**, con el mismo criterio con el que se hizo el
 * inventario: *la funcion que atiende cada accion, y si esa funcion -o la que llama directamente- manda algo
 * que no es un GET.*
 */
function lasQueEscribenSegunElCodigo() {
  const lineas = APP.split("\n");
  const funciones = [];
  for (const [i, linea] of lineas.entries()) {
    const m = linea.match(/^(?:export )?(?:async )?function (\w+)/);
    if (m) funciones.push([i, m[1]]);
  }
  const cuerpos = new Map();
  for (const [i, nombre] of funciones.entries()) {
    const fin = funciones[i + 1] ? funciones[i + 1][0] : lineas.length;
    cuerpos.set(funciones[i][1], lineas.slice(funciones[i][0], fin).join("\n"));
  }
  const mandaAlgo = (cuerpo) =>
    /method:\s*"(POST|PUT|PATCH|DELETE)"/.test(cuerpo) || /\bmandarCambio\(/.test(cuerpo);
  const escritoras = new Set([...cuerpos].filter(([, cuerpo]) => mandaAlgo(cuerpo)).map(([n]) => n));

  // ***Las acciones del despacho, con su linea.*** *Con objetos y no con pares: `acciones.entries()` sobre un
  // array de pares devuelve el par entero, y el analisis acababa comparando `[linea, nombre]` con nombres
  // -el fallo lo canto la propia prueba, que volco pares donde esperaba acciones-.*
  const acciones = [];
  for (const [i, linea] of lineas.entries()) {
    const m = linea.match(/if \(nombre === "([\w-]+)"\)/);
    if (m) acciones.push({ linea: i, accion: m[1] });
  }
  const salen = new Set();
  for (const [i, suya] of acciones.entries()) {
    const siguiente = acciones[i + 1];
    const fin = siguiente ? siguiente.linea : Math.min(suya.linea + 40, lineas.length);
    const cuerpo = lineas.slice(suya.linea, fin).join("\n");
    const llamadas = new Set(Array.from(cuerpo.matchAll(/\b(\w+)\(/g), (x) => x[1]));
    if (mandaAlgo(cuerpo) || [...llamadas].some((n) => escritoras.has(n))) salen.add(suya.accion);
  }
  return salen;
}

test("***las siete que la revision demostro*** estan en el inventario", async () => {
  const { escribeEstaAccion } = await import(`../web/react/acciones.js?prueba=${Math.random()}`);

  // *Nombradas una a una: **esto no lo descubre el analisis, lo dijo la revision**.*
  for (const accion of [
    "contacto-borrar-si",
    "fusion-hacer",
    "fusion-deshacer",
    "contacto-nota",
    "contacto-baja",
    "banco-deshacer",
    "bandeja-confirmar",
  ]) {
    assert.ok(
      escribeEstaAccion(accion),
      `***«${accion}» ESCRIBE y el inventario tiene que saberlo***: con el clasificador por sufijos, ` +
        `un usuario de consulta veia el boton y solo se enteraba al pulsarlo`,
    );
  }
});

test("y el inventario coincide con lo que dice el codigo", async () => {
  const { LAS_QUE_ESCRIBEN, LAS_DE_SESION } = await import(
    `../web/react/acciones.js?prueba=${Math.random()}`
  );
  const segunElCodigo = lasQueEscribenSegunElCodigo();

  const sinApuntar = [...segunElCodigo].filter(
    (a) => !LAS_QUE_ESCRIBEN.has(a) && !LAS_DE_SESION.has(a),
  );
  assert.deepEqual(
    sinApuntar.sort(),
    [],
    "***estas acciones ESCRIBEN y no estan en el inventario***: " +
      `${sinApuntar.join(", ")}. Anadelas a \`LAS_QUE_ESCRIBEN\` en \`react/acciones.js\`, ` +
      "o a `LAS_DE_SESION` si son de entrar o cambiar de finca.",
  );

  const deMas = [...LAS_QUE_ESCRIBEN].filter((a) => !segunElCodigo.has(a));
  assert.deepEqual(
    deMas.sort(),
    [],
    `***estas estan en el inventario y el codigo ya no las escribe***: ${deMas.join(", ")}. ` +
      "Se quitan, o el inventario miente.",
  );
});

test("***el caso que la revision reprodujo***: con escritura apagada, `fusion-hacer` NO se pinta", async () => {
  const { Boton, ponerSiSePuedeEscribir } = await import(
    `../web/react/componentes.js?prueba=${Math.random()}`
  );
  const pintar = (accion) =>
    globalThis.ReactDOMServer.renderToStaticMarkup(
      globalThis.React.createElement(Boton, { accion, etiqueta: "FUSIONAR" }),
    );

  ponerSiSePuedeEscribir(false);
  try {
    assert.equal(
      pintar("fusion-hacer"),
      "",
      "***«fusion-hacer» fusiona y NO puede salir sin permiso***: lo reprodujo la revision",
    );
    // *Y lo que no escribe se sigue viendo.*
    assert.ok(pintar("gastos-ver").includes("data-accion"), "***y ver si sale***");
  } finally {
    ponerSiSePuedeEscribir(true);
  }
});

test("***pero entrar NO se esconde***: esconderlo dejaria al agricultor fuera", async () => {
  const { escribeEstaAccion } = await import(`../web/react/acciones.js?prueba=${Math.random()}`);

  for (const accion of ["entrar", "entrar-certificado", "cambiar-finca", "finca-entrar"]) {
    assert.ok(
      !escribeEstaAccion(accion),
      `***«${accion}» es de SESION, no de datos***: no puede esconderse`,
    );
  }
});

test("y una accion de consulta normal no escribe", async () => {
  const { escribeEstaAccion } = await import(`../web/react/acciones.js?prueba=${Math.random()}`);

  for (const accion of ["gastos-ver", "ir-inicio", "tierras-buscar", "papel-ver", "volver"]) {
    assert.ok(!escribeEstaAccion(accion), `***«${accion}» no escribe***`);
  }
});
