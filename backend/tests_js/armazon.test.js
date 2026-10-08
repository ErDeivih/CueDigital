/**
 * Las comprobaciones del armazón nuevo: el menú agrupado (07/10/2026).
 *
 * POR QUÉ EXISTE ESTE FICHERO
 *
 * El encargo del rediseño (`docs/REDISENO_V0_STITCH_20261007.md`, apartado 3) pide un menú con esta
 * forma: «Inicio; Campo (Tierras y mapa, Trabajos, Cultivos y PAC, Almacén); Gestión (Documentos,
 * Cuentas, Personas, Maquinaria); Cuaderno; Normativa; Ajustes», y avisa de dos cosas que son las que
 * aquí se comprueban:
 *
 *   1. **«La agrupación es visual, no introduce pantallas intermedias obligatorias»**: los renglones
 *      siguen llevando a su pantalla de siempre, y el grupo es un nombre, no un paso de más.
 *   2. **El grupo «Normativa» no existe** en el programa (no hay ninguna pantalla que sea eso). Un
 *      renglón que no lleva a ninguna parte es peor que no tenerlo, así que lo que se comprueba es que
 *      **no** se ha inventado un renglón para llenar ese hueco.
 *
 * QUÉ SE COMPRUEBA, Y EN QUÉ SE APOYA
 *
 *  - **El componente** (`web/react/piezas/marco.js`): con `grupos` pinta cada grupo con su nombre y
 *    cada renglón dentro del suyo, en el orden que venga; **sin `grupos`** pinta la lista plana de
 *    siempre (que es lo que ya había, y por eso las pruebas que ya existían en `react.test.js` no se
 *    tocan). Cada renglón conserva su `data-accion`, sus `data-*`, su `id="menu-<clave>"` y su
 *    `aria-current` cuando está activo.
 *  - **La tabla de `app.js`** (`MODULOS` y `GRUPOS_DEL_MENU`), que es de donde salen los renglones y
 *    sus grupos. Se lee con un lector propio (abajo) porque `app.js` no exporta nada: es el arranque de
 *    la aplicación, no una biblioteca.
 *  - **El botón que abre el menú en el móvil**: su acción tiene que ser **literal**
 *    (`data-accion="menu-abrir"`), no una variable. El motivo está escrito en el guardián de Python que
 *    lee las acciones del código (`tests/test_los_botones_hacen_algo.py`): las acciones que salen por
 *    variable no se pueden leer de un fichero, así que no hay forma de saber si alguien las atiende.
 *
 * CÓMO SE PRUEBA SIN NAVEGADOR
 *
 * Igual que `react.test.js`: los ficheros de `web/vendor` son UMD, se cargan con `vm.runInThisContext`
 * (como los carga el navegador con una etiqueta `<script>`) y dejan `React`, `htm` y `ReactDOMServer` en
 * los globales. Con `renderToStaticMarkup` se convierte el componente en HTML sin necesidad de un DOM.
 * **No hay ninguna dependencia nueva**: estas pruebas corren en cualquier sitio donde haya Node.
 *
 * Y una regla de la casa que aquí se cumple a rajatabla, porque este fichero **lee e interpreta** otro
 * fichero (`app.js`): *un test que lee ficheros y los interpreta necesita su propia prueba*. Está al
 * final, y comprueba que el lector encuentra los 22 renglones y los 5 grupos y que **no se cree** una
 * acción puesta por variable. Si el lector se rompiera, las pruebas de arriba se pondrían rojas en vez
 * de pasar comprobando nada.
 */

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

// ---------------------------------------------------------------------------
// El arnés: React y htm, como los deja `index.html`
// ---------------------------------------------------------------------------

// Los ficheros UMD se asignan a `self` cuando no hay un sistema de módulos, que es el caso del
// navegador. Node no tiene `self`, así que se le pone: es lo único que hace falta.
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
// El lector de las tablas de `app.js`
// ---------------------------------------------------------------------------

const LA_WEB = new URL("../web/", import.meta.url);

/**
 * Recorta de un código la lista que empieza en `const <nombre> = [`, contando corchetes.
 *
 * **Se salta los comentarios y las cadenas**, y eso no es un lujo: el comentario de al lado de una
 * tabla de este proyecto lleva corchetes y paréntesis a montones, y contar corchetes sin mirar si
 * están dentro de un comentario deja la tabla cortada por la mitad (y la prueba pasando, que es peor).
 * Se aprendió en este mismo repositorio con `quita_comentarios_js`, que se comía medio `app.js` por un
 * `/*` dentro de unas comillas.
 */
function recortaLaLista(codigo, nombre) {
  const marca = `const ${nombre} = [`;
  const inicio = codigo.indexOf(marca);
  if (inicio < 0) throw new Error(`no encuentro la tabla «${nombre}» en app.js`);
  const desde = inicio + marca.length - 1;
  let profundidad = 0;
  for (let i = desde; i < codigo.length; i += 1) {
    const caracter = codigo[i];
    const siguiente = codigo[i + 1];
    if (caracter === '"' || caracter === "'" || caracter === "`") {
      i = finalDeLaCadena(codigo, i);
      continue;
    }
    if (caracter === "/" && siguiente === "/") {
      while (i < codigo.length && codigo[i] !== "\n") i += 1;
      continue;
    }
    if (caracter === "/" && siguiente === "*") {
      i = codigo.indexOf("*/", i) + 1;
      continue;
    }
    if (caracter === "[") profundidad += 1;
    else if (caracter === "]") {
      profundidad -= 1;
      if (profundidad === 0) return codigo.slice(desde, i + 1);
    }
  }
  throw new Error(`la tabla «${nombre}» de app.js no se cierra`);
}

/** El índice de la comilla que cierra la cadena que empieza en `desde`. */
function finalDeLaCadena(codigo, desde) {
  const cierre = codigo[desde];
  for (let i = desde + 1; i < codigo.length; i += 1) {
    if (codigo[i] === "\\") {
      i += 1;
      continue;
    }
    if (codigo[i] === cierre) return i;
  }
  return codigo.length;
}

/** Una de las tablas de `app.js`, leída como dato (`MODULOS`, `GRUPOS_DEL_MENU`).
 *
 * Se pasa por `JSON` a propósito: lo que devuelve `vm.runInNewContext` es un dato de **otro mundo**
 * (otro realm de JavaScript), y su `Array` no es el `Array` de aquí: compararlo con `assert.deepEqual`
 * falla aunque tenga el mismo contenido. Costó una vuelta verlo — las pruebas se ponían rojas con
 * «actual: [] expected: []»—, así que se convierte a dato de este mundo al leerlo y no en cada prueba.
 */
function listaDeAppJs(nombre) {
  const codigo = readFileSync(new URL("app.js", LA_WEB), "utf8");
  const texto = recortaLaLista(codigo, nombre);
  const lista = vm.runInNewContext(`(${texto})`, {});
  if (!Array.isArray(lista)) throw new Error(`«${nombre}» no es una lista en app.js`);
  return JSON.parse(JSON.stringify(lista));
}

const MODULOS = listaDeAppJs("MODULOS");
const GRUPOS_DEL_MENU = listaDeAppJs("GRUPOS_DEL_MENU");

// ---------------------------------------------------------------------------
// Los textos y los datos de las pruebas
// ---------------------------------------------------------------------------

/** Los textos del armazón, copiados de `textos.py` (los mismos que usa `react.test.js`). */
const TEXTOS = {
  // La búsqueda global (07/10/2026): su nombre sale del servidor, como el de los demás módulos.
  buscar: { titulo: "Buscar" },
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

/** Un renglón de módulo, como lo prepara `app.js` para el componente. */
function renglon(clave, accion, datos, activo = false) {
  return { clave, etiqueta: `MÓDULO ${clave}`, accion, datos, activo };
}

/** Un grupo, como lo prepara `app.js` para el componente. */
function grupo(clave, etiqueta, modulos) {
  return { clave, etiqueta, modulos };
}

/** El HTML del armazón, tal y como lo dibujaría React. */
async function htmlDelMarco(cambios = {}) {
  const { Marco } = await import(`../web/react/piezas/marco.js?prueba=${Math.random()}`);
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(Marco, {
      textos: structuredClone(TEXTOS),
      cuenta: "David Pérez Velasco",
      campana: "2026",
      modulos: [],
      ...cambios,
    }),
  );
}

/** Los renglones del menú que hay en un HTML, con sus atributos, en el orden en que salen. */
function renglonesDe(html) {
  const renglones = [];
  for (const encontrado of html.matchAll(/<button\b([^>]*)>/g)) {
    const atributos = {};
    for (const atributo of encontrado[1].matchAll(/([a-z-]+)="([^"]*)"/g)) {
      atributos[atributo[1]] = atributo[2];
    }
    const id = atributos.id || "";
    if (!id.startsWith("menu-")) continue;
    renglones.push({
      id,
      clave: id.slice("menu-".length),
      accion: atributos["data-accion"] || "",
      datos: Object.fromEntries(
        Object.entries(atributos).filter(([nombre]) => nombre.startsWith("data-")),
      ),
      clases: (atributos.class || "").split(" ").filter(Boolean),
      activo: atributos["aria-current"] === "page",
      posicion: encontrado.index,
    });
  }
  return renglones;
}

/** Cuántas veces aparece un texto en un HTML. */
function cuantasVeces(html, texto) {
  return html.split(texto).length - 1;
}

/** Los `id` de los renglones, en el orden en que salen. */
function idsDe(html) {
  return renglonesDe(html).map((renglon) => renglon.id);
}

// ---------------------------------------------------------------------------
// 1. La tabla de `app.js`: los grupos y los renglones
// ---------------------------------------------------------------------------

test("la tabla de grupos es la del contrato: los cinco, y ninguno inventado", () => {
  const claves = GRUPOS_DEL_MENU.map((uno) => uno.clave);
  assert.deepEqual(
    claves,
    ["inicio", "campo", "gestion", "cuaderno", "ajustes"],
    "los grupos del menú no son los cinco del contrato, o no están en su orden",
  );
  // **«Normativa» no está, y es a propósito**: no hay ninguna pantalla que sea eso. Si alguien mete un
  // grupo para llenar el hueco del encargo, esta prueba lo dice.
  const inventados = claves.filter((clave) => /normativ/i.test(clave));
  assert.deepEqual(inventados, [], "se ha inventado un grupo «Normativa» que no lleva a ninguna parte");
});

test("cada renglón del menú lleva su grupo, y es uno de los cinco", () => {
  const claves = new Set(GRUPOS_DEL_MENU.map((uno) => uno.clave));
  const sinGrupo = MODULOS.filter((modulo) => !modulo.grupo).map((modulo) => modulo.clave);
  assert.deepEqual(sinGrupo, [], `estos renglones no están en ningún grupo: ${sinGrupo}`);
  const deOtroSitio = MODULOS.filter((modulo) => !claves.has(modulo.grupo)).map(
    (modulo) => `${modulo.clave} → ${modulo.grupo}`,
  );
  assert.deepEqual(deOtroSitio, [], `estos renglones dicen un grupo que no existe: ${deOtroSitio}`);
});

test("los renglones del menú son 22, sin repeticiones, y ningún grupo se queda vacío", () => {
  assert.equal(MODULOS.length, 22, `el menú tiene ${MODULOS.length} renglones y el contrato dice 22`);
  const claves = MODULOS.map((modulo) => modulo.clave);
  assert.equal(new Set(claves).size, claves.length, `hay renglones repetidos: ${claves}`);
  // Un grupo sin renglones es un nombre que promete algo que no está (la misma regla que la barra de
  // acciones vacía). Cada uno de los cinco tiene que llevar al menos uno.
  const vacios = GRUPOS_DEL_MENU.filter(
    (uno) => !MODULOS.some((modulo) => modulo.grupo === uno.clave),
  ).map((uno) => uno.clave);
  assert.deepEqual(vacios, [], `estos grupos saldrían con su nombre y sin ningún renglón: ${vacios}`);
  // Y ningún renglón inventado para llenar el hueco del encargo.
  const sospechosos = MODULOS.filter((modulo) =>
    /normativ/i.test(`${modulo.clave} ${modulo.texto} ${modulo.accion} ${JSON.stringify(modulo.datos || {})}`),
  ).map((modulo) => modulo.clave);
  assert.deepEqual(sospechosos, [], `hay renglones que no llevan a ninguna pantalla: ${sospechosos}`);
});

test("el nombre de cada grupo está en el servidor (`menu.grupo_<clave>`)", () => {
  // Ninguna frase para el agricultor se escribe en `app.js` ni en el componente: los nombres de los
  // grupos salen de `textos.py` como los de los renglones.
  const malos = GRUPOS_DEL_MENU.filter((uno) => uno.texto !== `menu.grupo_${uno.clave}`).map(
    (uno) => `${uno.clave} → ${uno.texto}`,
  );
  assert.deepEqual(malos, [], `estos grupos no piden su nombre al servidor: ${malos}`);
  const sinTexto = GRUPOS_DEL_MENU.filter((uno) => !uno.texto?.trim()).map((uno) => uno.clave);
  assert.deepEqual(sinTexto, [], `estos grupos saldrían sin nombre: ${sinTexto}`);
});

test("la agrupación es visual: ningún grupo lleva acción propia, y cada renglón lleva la suya", () => {
  // **Esto es el «no introduce pantallas intermedias obligatorias» del encargo**, dicho de la única
  // forma que se puede comprobar leyendo: un grupo que tuviera acción sería un paso de más entre el
  // agricultor y su pantalla. Y cada renglón tiene que seguir llevando a la suya por sí solo.
  const conAccion = GRUPOS_DEL_MENU.filter(
    (uno) => uno.accion || uno.datos || uno.ir || uno.destino,
  ).map((uno) => uno.clave);
  assert.deepEqual(conAccion, [], `estos grupos llevan acción propia y serían una pantalla de más: ${conAccion}`);
  const sinAccion = MODULOS.filter((modulo) => typeof modulo.accion !== "string" || !modulo.accion).map(
    (modulo) => modulo.clave,
  );
  assert.deepEqual(sinAccion, [], `estos renglones no llevan a ninguna parte: ${sinAccion}`);
});

// ---------------------------------------------------------------------------
// 2. El componente: con `grupos` y sin `grupos`
// ---------------------------------------------------------------------------

test("con `grupos`, cada grupo sale con su nombre y cada renglón dentro de su grupo, en el orden que venga", async () => {
  // Etiquetas inventadas y únicas a propósito: así lo que se busca en el HTML es el nombre del grupo y
  // no una palabra que aparezca también en un renglón.
  const grupos = [
    grupo("campo", "GRUPO-UNO", [
      renglon("alfa", "ir-inicio"),
      renglon("beta", "inicio", { ir: "mis_cosas" }),
    ]),
    grupo("gestion", "GRUPO-DOS", [renglon("gamma", "gastos-ver")]),
  ];
  const html = await htmlDelMarco({ modulos: [], grupos });

  const posiciones = grupos.map((uno) => html.indexOf(uno.etiqueta));
  posiciones.forEach((posicion, indice) => {
    assert.ok(posicion >= 0, `el grupo «${grupos[indice].etiqueta}» no sale en el menú`);
    assert.equal(
      cuantasVeces(html, grupos[indice].etiqueta),
      1,
      `el nombre del grupo «${grupos[indice].etiqueta}» sale más de una vez (o está partido)`,
    );
  });

  for (const [indice, uno] of grupos.entries()) {
    const desde = posiciones[indice];
    const hasta = indice + 1 < grupos.length ? posiciones[indice + 1] : html.length;
    const suyos = uno.modulos.map((modulo) => html.indexOf(`id="menu-${modulo.clave}"`));
    suyos.forEach((posicion, posicionEnElGrupo) => {
      const modulo = uno.modulos[posicionEnElGrupo];
      assert.ok(posicion >= 0, `falta el renglón ${modulo.clave}`);
      assert.ok(
        posicion > desde && posicion < hasta,
        `el renglón ${modulo.clave} no está dentro del grupo «${uno.etiqueta}»`,
      );
    });
    assert.deepEqual(
      suyos,
      [...suyos].sort((a, b) => a - b),
      `los renglones de «${uno.etiqueta}» no salen en el orden en que vienen`,
    );
  }
});

test("el orden de los grupos y de los renglones es el que llega, y no se toca", async () => {
  // El orden lo manda el servidor (`app.js`). Si el componente tuviera uno propio, esta prueba saldría
  // roja: es la misma prueba que ya protege el orden de los botones de la pantalla de inicio.
  const grupos = [
    grupo("campo", "GRUPO-UNO", [renglon("alfa", "ir-inicio"), renglon("beta", "inicio")]),
    grupo("gestion", "GRUPO-DOS", [renglon("gamma", "gastos-ver")]),
  ];
  const alReves = [...grupos].reverse().map((uno) => ({
    ...uno,
    modulos: [...uno.modulos].reverse(),
  }));
  const html = await htmlDelMarco({ modulos: [], grupos: alReves });
  const ids = idsDe(html);
  assert.deepEqual(ids, ["menu-gamma", "menu-beta", "menu-alfa"], `salen así: ${ids}`);
  assert.ok(
    html.indexOf("GRUPO-DOS") < html.indexOf("GRUPO-UNO"),
    "los grupos salen en un orden que no es el que se le pasa",
  );
});

test("con `grupos` no se cuelan renglones de más ni se pierde ninguno", async () => {
  const grupos = [
    grupo("campo", "GRUPO-UNO", [renglon("alfa", "ir-inicio"), renglon("beta", "inicio")]),
    grupo("gestion", "GRUPO-DOS", [renglon("gamma", "gastos-ver")]),
  ];
  const html = await htmlDelMarco({ modulos: [], grupos });
  assert.deepEqual(idsDe(html), ["menu-alfa", "menu-beta", "menu-gamma"]);
});

test("con `grupos` no se pinta además la lista plana (serían renglones repetidos)", async () => {
  // Si el armazón pintara las dos listas, el agricultor vería su menú con los renglones duplicados: unos
  // dentro de su grupo y otros sueltos debajo.
  const modulos = [renglon("suelto", "ir-inicio")];
  const grupos = [grupo("campo", "GRUPO-UNO", [renglon("alfa", "ir-inicio")])];
  const html = await htmlDelMarco({ modulos, grupos });
  assert.ok(!html.includes('id="menu-suelto"'), "con grupos se sigue pintando además la lista plana");
  assert.ok(html.includes('id="menu-alfa"'), "con grupos no se pintan los renglones de los grupos");
});

test("sin `grupos`, el armazón pinta la lista plana de siempre", async () => {
  // Es lo que ya había antes de este cambio, y no se puede romper: hay pantallas y pruebas que cuentan
  // con ese menú. Las pruebas de `react.test.js` siguen valiendo para este caso.
  const modulos = [
    renglon("alfa", "ir-inicio"),
    renglon("beta", "inicio", { ir: "mis_cosas" }),
    renglon("gamma", "facturas-abrir", undefined, true),
  ];
  const html = await htmlDelMarco({ modulos });
  assert.deepEqual(idsDe(html), ["menu-alfa", "menu-beta", "menu-gamma"]);
  for (const etiqueta of GRUPOS_DEL_MENU.map((uno) => uno.texto)) {
    assert.ok(!html.includes(etiqueta), `sin grupos no se pinta ningún nombre de grupo (sale «${etiqueta}»)`);
  }
  assert.ok(html.includes('data-accion="facturas-abrir"'), "la lista plana ha perdido su acción");
});

test("cada renglón conserva su acción, sus datos, su `id` y su `aria-current` cuando está activo", async () => {
  // Es lo que lee el manejador de clics delegado de `document`, así que un renglón agrupado tiene que
  // salir **exactamente** igual que salía suelto: mismo `id`, misma acción y mismos `data-*`.
  const grupos = [
    grupo("campo", "GRUPO-UNO", [
      renglon("alfa", "ir-inicio"),
      renglon("beta", "inicio", { ir: "mis_cosas" }, true),
    ]),
  ];
  const html = await htmlDelMarco({ modulos: [], grupos });
  const [alfa, beta] = renglonesDe(html);

  assert.equal(alfa.id, "menu-alfa");
  assert.equal(alfa.accion, "ir-inicio");
  assert.equal(alfa.activo, false, "marca como activo un renglón que no lo está");
  assert.ok(alfa.clases.includes("menu-enlace"), "el renglón ha perdido la clase del menú");

  assert.equal(beta.id, "menu-beta");
  assert.equal(beta.accion, "inicio");
  assert.equal(beta.datos["data-ir"], "mis_cosas", "el renglón ha perdido su data-ir");
  assert.equal(beta.activo, true, "el renglón activo ha perdido su aria-current");
  assert.equal(
    renglonesDe(html).filter((uno) => uno.activo).length,
    1,
    "hay más de un renglón marcado como el que se está viendo",
  );
});

test("con los 22 renglones de verdad, agrupados salen los mismos que en la lista plana", async () => {
  // Esta es la prueba que ata el componente con la tabla de `app.js`: si al agrupar se perdiera un
  // renglón (o el grupo de un renglón estuviera mal escrito), aquí se ve.
  const planos = MODULOS.map((modulo) => ({
    clave: modulo.clave,
    etiqueta: modulo.texto,
    accion: modulo.accion,
    datos: modulo.datos,
    activo: false,
  }));
  const grupos = GRUPOS_DEL_MENU.map((uno) =>
    grupo(
      uno.clave,
      uno.texto,
      planos.filter((_renglon, indice) => MODULOS[indice].grupo === uno.clave),
    ),
  );

  const planoHtml = await htmlDelMarco({ modulos: planos });
  const agrupadoHtml = await htmlDelMarco({ modulos: [], grupos });

  assert.equal(idsDe(planoHtml).length, 22, "la lista plana no lleva los 22 renglones");
  assert.deepEqual(
    idsDe(agrupadoHtml).sort(),
    idsDe(planoHtml).sort(),
    "al agrupar los renglones no son los mismos que en la lista plana",
  );
  // Y cada uno está dentro del grupo que le toca: el nombre de su grupo sale antes que él y **no hay
  // ningún otro nombre de grupo en medio** (si lo hubiera, el renglón estaría colgado del grupo que no es).
  for (const modulo of MODULOS) {
    const suyo = grupos.find((uno) => uno.clave === modulo.grupo);
    const posicionSuyo = agrupadoHtml.indexOf(suyo.etiqueta);
    const posicionRenglon = agrupadoHtml.indexOf(`id="menu-${modulo.clave}"`);
    assert.ok(
      posicionSuyo >= 0 && posicionRenglon > posicionSuyo,
      `${modulo.clave} no sale después del nombre de su grupo`,
    );
    const enMedio = grupos
      .filter((otro) => {
        const posicion = agrupadoHtml.indexOf(otro.etiqueta);
        return posicion > posicionSuyo && posicion < posicionRenglon;
      })
      .map((otro) => otro.clave);
    assert.deepEqual(enMedio, [], `entre el grupo de ${modulo.clave} y su renglón hay otro grupo: ${enMedio}`);
  }
});

// ---------------------------------------------------------------------------
// 3. El botón que abre el menú debajo de 64 rem
// ---------------------------------------------------------------------------

/** Todos los ficheros que se sirven al navegador (`.js` y `.html`), sin `vendor`. */
function ficherosServidos() {
  const ficheros = [];
  const recorrer = (carpeta) => {
    for (const entrada of readdirSync(carpeta, { withFileTypes: true })) {
      if (entrada.isDirectory()) {
        // `vendor` es React y `htm` tal y como los publica su fabricante: ahí no se escribe nada nuestro.
        if (entrada.name === "vendor") continue;
        recorrer(new URL(`${entrada.name}/`, carpeta));
      } else if (/\.(js|html)$/.test(entrada.name)) {
        ficheros.push(new URL(entrada.name, carpeta));
      }
    }
  };
  recorrer(LA_WEB);
  return ficheros;
}

/**
 * Las formas en que el código escribe una acción, **las mismas que lee el guardián de Python**
 * (`tests/test_los_botones_hacen_algo.py`): si una acción sale por variable, ese guardián no la ve.
 */
function formasDeLaAccion(accion) {
  return [
    new RegExp(`data-accion=["']${accion}["']`),
    new RegExp(`data-accion=\\$\\{["'\`]${accion}["'\`]\\}`),
    new RegExp(`\\baccion=["']${accion}["']`),
    new RegExp(`\\baccion=\\$\\{["'\`]${accion}["'\`]\\}`),
    new RegExp(`\\baccion:\\s*["'\`]${accion}["'\`]`),
  ];
}

/** ¿Alguna de las formas literales de esa acción está en este código? */
function accionLiteral(codigo, accion) {
  return formasDeLaAccion(accion).some((forma) => forma.test(codigo));
}

/** Dónde (fichero:línea) se escribe una acción, con las formas literales. */
function dondeSeEscribe(accion) {
  const sitios = [];
  for (const fichero of ficherosServidos()) {
    const lineas = readFileSync(fichero, "utf8").split("\n");
    lineas.forEach((linea, numero) => {
      if (accionLiteral(linea, accion)) {
        sitios.push(`${fichero.pathname.split("/web/")[1]}:${numero + 1}`);
      }
    });
  }
  return sitios;
}

test("el botón de abrir el menú está en lo que se sirve, y con la acción literal", () => {
  const sitios = dondeSeEscribe("menu-abrir");
  assert.ok(
    sitios.length > 0,
    "no hay ninguna acción literal «menu-abrir» en lo que se sirve: debajo de 64 rem el menú no se " +
      "podría abrir (y si está puesta por variable, el guardián de Python no puede saber si alguien " +
      "la atiende)",
  );
  // Y su acción la tiene que atender el manejador de clics, que es uno solo para toda la aplicación.
  const app = readFileSync(new URL("app.js", LA_WEB), "utf8");
  assert.ok(
    /nombre === ["']menu-abrir["']/.test(app),
    `el botón se pinta (${sitios.join(", ")}) y el manejador de clics no lo atiende`,
  );
});

test("el botón de cerrar el menú está en lo que se sirve, y con la acción literal", () => {
  const sitios = dondeSeEscribe("menu-cerrar");
  assert.ok(sitios.length > 0, "no hay ninguna acción literal «menu-cerrar»: el panel no se podría cerrar");
  const app = readFileSync(new URL("app.js", LA_WEB), "utf8");
  assert.ok(
    /nombre === ["']menu-cerrar["']/.test(app),
    `el botón se pinta (${sitios.join(", ")}) y el manejador de clics no lo atiende`,
  );
});

// ---------------------------------------------------------------------------
// 4. Los guardianes del propio lector
//
// Este fichero lee `app.js` y lo interpreta, así que necesita su propia prueba: si el lector se
// rompiera, las pruebas de arriba pasarían sin comprobar nada (la regla está en `AGENTS.md`).
// ---------------------------------------------------------------------------

test("el lector de las tablas de `app.js` lee lo que dice leer", () => {
  assert.equal(MODULOS.length, 22, `el lector ha encontrado ${MODULOS.length} renglones y hay 22`);
  assert.equal(GRUPOS_DEL_MENU.length, 5, `el lector ha encontrado ${GRUPOS_DEL_MENU.length} grupos`);
  assert.equal(MODULOS[0].clave, "panel", "el lector no está leyendo la tabla de verdad");
  assert.ok(
    MODULOS.every((modulo) => typeof modulo.clave === "string" && modulo.clave.length > 0),
    "hay renglones sin clave: el lector ha leído mal la tabla",
  );
});

test("el buscador de acciones literales no se cree una acción puesta por variable", () => {
  // La rotura a propósito: con la acción por variable, el buscador tiene que decir que **no**. Si
  // dijera que sí, la prueba del botón de abrir el menú estaría verde sin comprobar nada.
  assert.equal(accionLiteral('<button data-accion="menu-abrir">', "menu-abrir"), true);
  assert.equal(accionLiteral("html`<button accion=${laQueSea}>`", "menu-abrir"), false);
  assert.equal(accionLiteral("data-accion=${otra} accion: laDeCadaUno", "menu-abrir"), false);
  assert.equal(accionLiteral('const x = { accion: "menu-abrir" }', "menu-abrir"), true);
});
