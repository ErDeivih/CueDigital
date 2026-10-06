/**
 * Pruebas de las pantallas de los trabajos (T15, 05/10/2026), **sin navegador**.
 *
 * POR QUÉ ESTÁN AQUÍ Y NO EN `interfaz.test.js`
 *
 * Las tres pantallas están escritas en React (`web/react/pantallas/trabajos.js`) y en el DOM de mentira
 * de `interfaz.test.js` React no se puede montar. Así que se prueban **contra el componente**: se le dan
 * las propiedades y se mira el HTML que producen con `renderToStaticMarkup`, igual que se hace con las
 * otras pantallas migradas. No hay `jsdom` ni ninguna dependencia nueva.
 *
 * QUÉ SE COMPRUEBA, Y POR QUÉ ESAS COSAS
 *
 *  1. **Que lo previsto y lo hecho no se mezclen.** Son **dos listas con dos títulos**, y un trabajo
 *     previsto lleva la frase que dice que no ha gastado nada. Si esto fallara, un plan parecería un
 *     trabajo hecho, que es el defecto que este ticket existe para no cometer.
 *  2. **Que lo anulado se vea y se explique.** Sale en su lista, con la palabra que dice que no cuenta y
 *     con su motivo: **nada se borra**.
 *  3. **Que los huecos se vean como huecos.** Un trabajo sin hectáreas o sin horas dice que no lo dice;
 *     la pantalla no escribe un cero, que diría «se trabajaron cero hectáreas».
 *  4. **Que cada modo de la ficha guarde por su puerta.** Planificar, cambiar de día, marcar lo hecho,
 *     corregir y anular son cinco acciones distintas —y solo una de ellas apunta un trabajo hecho—, así
 *     que la prueba mira **qué `data-accion` sale en cada modo**.
 *  5. **Que al marcar lo hecho se vea lo que se había pensado**, con la frase que dice que lo pensado no
 *     ha gastado nada.
 *  6. **Que ninguna frase esté escrita dentro del componente**: todas vienen de la copia de los textos
 *     del servidor que hay aquí abajo, y hay una prueba que comprueba que **no falta ninguna clave** que
 *     la pantalla lea (una clave que falte deja la frase en blanco en el campo, sin avisar).
 *
 * La copia de los textos (`AGENDA`, aquí abajo) es **la misma** que el informe del ticket pide añadir a
 * `app/textos.py`. Está escrita como un objeto aparte, con una clave por línea, para que la prueba de
 * Python pueda leerla y compararla con lo que la pantalla lee.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

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
// La copia de los textos: los mismos que sirve `/api/interfaz`
// ---------------------------------------------------------------------------

/**
 * El bloque `AGENDA` de `textos.py`, **clave por clave**.
 *
 * Va aparte (y no dentro de otro objeto) a propósito: la prueba de Python
 * (`tests/test_trabajos.py::TestLaCopiaDeLosTextosDelMovil`) lee este bloque y comprueba que no falte
 * ninguna clave que la pantalla lea. Si se inventaran aquí, estas pruebas comprobarían una pantalla que
 * el agricultor no tiene.
 */
const AGENDA = {
  titulo: "Los trabajos",
  explica: "Aquí tienes lo que tienes pensado hacer y lo que ya has hecho, en dos listas separadas. Lo que está pensado no ha gastado nada del almacén: lo que se gasta se apunta cuando el trabajo se hace.",
  buscando: "Buscando…",
  ver_el_cuaderno: "VER MI CUADERNO",
  volver_a_los_trabajos: "VOLVER A LOS TRABAJOS",
  previstos_titulo: "Lo que tengo pensado hacer",
  previstos_explica: "Lo que está pensado no es un trabajo hecho y no ha gastado nada.",
  previstos_vacio: "No tienes nada planificado. Cuando sepas lo que vas a hacer, apúntalo aquí.",
  planificar: "PLANIFICAR UN TRABAJO",
  planificar_titulo: "Planificar un trabajo",
  planificar_explica: "Apunta lo que piensas hacer. No gasta nada del almacén: eso se apunta el día que lo hagas, con lo que de verdad gastes.",
  guardar_previsto: "GUARDAR LO QUE PIENSO HACER",
  ya_lo_he_hecho: "YA LO HE HECHO",
  ya_esta_hecho: "Ya lo apuntaste como hecho:",
  cambiarlo_de_dia: "CAMBIARLO DE DÍA",
  cancelarlo: "CANCELARLO",
  reprogramar_titulo: "Cambiar de día este trabajo",
  reprogramar_explica: "Elige el día nuevo. El día que tenía queda apuntado, para que se pueda explicar el cambio.",
  cambiar_el_dia: "CAMBIARLO DE DÍA",
  hechos_titulo: "Lo que he hecho",
  hechos_explica: "Cada trabajo con su día, su tierra, su máquina y lo que se gastó. Lo anulado sale también, con su motivo.",
  hechos_vacio: "Todavía no has apuntado ningún trabajo hecho.",
  hecho_titulo: "Lo que he hecho de verdad",
  hecho_explica: "Apunta lo que de verdad has hecho: el día, las hectáreas y las horas de verdad, y lo que gastaste. No tiene que ser igual que lo que habías pensado.",
  lo_que_estaba_previsto: "Lo que tenías pensado",
  lo_previsto_no_gasta: "Lo pensado no ha gastado nada del almacén.",
  guardar_trabajo: "APUNTAR LO QUE HE HECHO",
  corregir_titulo: "Corregir este trabajo",
  corregirlo: "CORREGIRLO",
  guardar_correccion: "GUARDAR LA CORRECCIÓN",
  anular_titulo: "Anular este trabajo",
  anularlo: "ANULARLO",
  anular_explica: "Un trabajo no se borra: se anula y queda dicho por qué. Lo que había salido del almacén vuelve a contar.",
  anular_confirmar: "ANULARLO",
  motivo_anulacion: "Por qué lo anulas",
  motivo_anulacion_pista: "Escríbelo pensando en que lo vas a leer dentro de dos años.",
  guardando: "Guardando…",
  tipo: "Qué trabajo",
  tipo_pista: "Rodillo, cultivador, siembra, riego…",
  elige_el_trabajo: "Elige el trabajo",
  subtipo: "Con qué apero",
  subtipo_pista: "Solo para las labores de suelo: rodillo, cultivador, arado…",
  sin_decir: "Sin decir",
  tierra: "En qué tierra",
  elige_la_tierra: "Elige la tierra",
  dia: "Qué día lo hiciste",
  dia_pista: "El día de verdad, que es el que va al cuaderno.",
  dia_previsto: "Para qué día lo tienes pensado",
  dia_previsto_pista: "Si todavía no lo sabes, déjalo en blanco: se queda sin día.",
  hectareas: "Cuántas hectáreas has trabajado",
  hectareas_previstas: "Cuántas hectáreas piensas trabajar",
  hectareas_pista: "Si no lo sabes, déjalo en blanco. No se pone un cero.",
  horas: "Cuántas horas has estado",
  horas_previstas: "Cuántas horas piensas estar",
  horas_pista: "Si no lo sabes, déjalo en blanco.",
  maquina: "Con qué máquina",
  maquina_pista: "La máquina con la que lo hiciste. Si fue a mano, déjalo sin decir.",
  sin_maquina: "Sin máquina dicha",
  insumo: "Qué gastaste del almacén",
  insumo_pista: "De qué envase sale lo que gastaste. Si no gastaste nada, déjalo sin decir.",
  insumo_previsto_pista: "Lo que crees que vas a gastar. No se descuenta hasta que lo hagas.",
  sin_insumo: "No gasté nada",
  cantidad: "Cuánto",
  cantidad_pista: "El total gastado, no lo de cada hectárea.",
  unidad: "En qué se mide",
  observaciones: "Lo que quieras apuntar",
  repaso: "Antes de guardar, mira esto",
  historia_titulo: "Lo que ha pasado en esta tierra",
  que_hay_hoy: "Qué hay hoy",
  lo_que_esta_sembrado: "Lo que hay sembrado",
  variedad: "Variedad",
  desde_cuando: "Desde",
  sin_cultivo_declarado: "De esta tierra no consta que haya nada sembrado.",
  ultima_labor: "La última labor",
  historial_titulo: "Todo lo que ha pasado",
  historial_explica: "Sale todo, también lo anulado, con el motivo por el que se anuló. Nada se borra.",
  historial_vacio: "En esta tierra no hay ningún trabajo apuntado.",
  revisado: "Corregido después",
  firmado: "Está firmado: no se puede borrar, solo anular",
  observaciones_de_campo: "Lo que he visto en el campo",
  no_consta: "Lo que no consta",
  sin_tierras: "Para planificar un trabajo hace falta tener una tierra dada de alta.",
  anadir_tierra: "VER MIS TIERRAS",
  // **Lo que ha costado una tierra** (T13 + T15, 05/10/2026). Son de `textos.AGENDA`, como todas las de
  // arriba: esta copia es la que hace que la pantalla no pueda enseñar una frase inventada.
  costes_titulo: "Lo que ha costado esta tierra",
  costes_explica:
    "Lo que consta de esta tierra. Está separado en dos: lo que pone el papel y lo que se repartió desde las cuentas, que es una estimación. Lo que no se sabe se dice, no se cuenta como cero.",
  costes_directos: "Lo que pone el papel",
  costes_repartidos: "Lo repartido desde las cuentas",
  costes_total: "Lo que se sabe que ha costado",
  costes_sin_importe:
    "Hay {cuantos} gasto de esta tierra que no dice lo que costó, así que el total se queda corto.",
  costes_vacio: "De esta tierra no hay ningún gasto apuntado.",
  costes_directo_es: "Es un gasto que dice esta tierra.",
  costes_repartido_es: "Es un trozo que se repartió a esta tierra desde las cuentas.",
  ver_el_gasto: "VER EL GASTO",
};

/** El vocabulario de los tipos de trabajo: ya está en `textos.py` y se sirve en `/api/interfaz`. */
const TRABAJOS = [
  { id: "siembra", icono: "🌱", texto: "HE SEMBRADO" },
  { id: "laboreo", icono: "🚜", texto: "HE LABRADO LA TIERRA" },
];

const TEXTOS = {
  agenda: AGENDA,
  acciones: { volver: "VOLVER" },
  trabajos: TRABAJOS,
  trabajos_de_labor: [{ id: "laboreo", icono: "🚜", texto: "HE LABRADO LA TIERRA" }],
};

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

/** Los `data-accion` que salen pintados. */
function accionesDe(html) {
  return [...html.matchAll(/data-accion="([a-z0-9_-]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Los `id` de los campos que salen pintados. */
function camposDe(html) {
  return [...html.matchAll(/id="(trabajo-[a-z0-9_-]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Lo que de verdad se lee en el HTML: el texto que hay entre las etiquetas. */
function frasesVisibles(html) {
  return html
    .replace(/<[^>]*>/g, "\u0000")
    .split("\u0000")
    .map((trozo) => trozo.trim())
    .filter(Boolean);
}

async function cargar(nombre) {
  return import(`../web/react/pantallas/${nombre}.js?prueba=${Math.random()}`);
}

async function htmlDe(componente, propiedades) {
  const modulo = await cargar("trabajos");
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(modulo[componente], propiedades),
  );
}

/** Un trabajo previsto, tal y como lo prepara `app.js`. */
function lineaPrevista(cambios = {}) {
  return {
    id: 9,
    titulo: "Laboreo · cultivador",
    cuando: "Dentro de 19 días (20/04/2026)",
    tierra: "El Prado",
    gastaria: "Lo que gastaría: 250 litros de gasóleo",
    // La frase la monta `app.js` desde el texto del servidor: aquí se copia la misma para poder
    // comprobar que **sale en la pantalla** y no se queda en un comentario.
    no_gasta: AGENDA.lo_previsto_no_gasta,
    ...cambios,
  };
}

/** Un trabajo hecho, tal y como lo prepara `app.js`. */
function lineaHecha(cambios = {}) {
  return {
    id: 1,
    titulo: "Siembra · trigo blando",
    cuando: "01/03/2026",
    tierra: "El Prado",
    faltan: [],
    anulado: false,
    no_cuenta: "",
    motivo_anulacion: "",
    ...cambios,
  };
}

const htmlDeLaAgenda = (cambios = {}) =>
  htmlDe("PantallaDeLosTrabajos", {
    textos: TEXTOS,
    previstos: [],
    hechos: [],
    resumen: "",
    sin_decir: "",
    aviso: "",
    avisos: [],
    lo_que_no_se_sabe: [],
    error: "",
    cargando: false,
    puedePlanificar: true,
    ...cambios,
  });

const htmlDeUnTrabajo = (cambios = {}) =>
  htmlDe("PantallaDeUnTrabajo", {
    textos: TEXTOS,
    modo: "planificar",
    borrador: {},
    tipos: [{ valor: "laboreo", texto: "HE LABRADO LA TIERRA" }],
    subtipos: [{ valor: "rodillo", texto: "Rodillo" }],
    tierras: [{ valor: 3, texto: "El Prado" }],
    maquinas: [{ valor: 2, texto: "El tractor" }],
    insumos: [{ valor: 7, texto: "Gasóleo · 4471-A" }],
    unidades: [{ valor: "L", texto: "L" }],
    previsto: null,
    repaso: [],
    guardando: false,
    error: "",
    ...cambios,
  });

const htmlDeLaTierra = (cambios = {}) =>
  htmlDe("PantallaDeLaTierra", {
    textos: TEXTOS,
    tierra: { nombre: "El Prado", superficie: "3,00 ha" },
    historial: [],
    estado: null,
    no_consta: [],
    error: "",
    ...cambios,
  });

// ---------------------------------------------------------------------------
// 1. Lo previsto y lo hecho, en dos listas y sin mezclarse
// ---------------------------------------------------------------------------

test("un plan que ya se cumplió lo dice, y no ofrece volver a cumplirlo", async () => {
  // **El defecto que esto fija, encontrado pulsando.** La lista de lo pensado trae también los planes ya
  // cumplidos (y tiene que traerlos), y la pantalla les pintaba «YA LO HE HECHO» otra vez: el agricultor lo
  // pulsaba, rellenaba la ficha y el servidor contestaba **409** —«este trabajo ya estaba apuntado»—. Aquí
  // se comprueban las dos mitades: que se dice cuándo se hizo y que **no hay ningún botón** que no pueda
  // funcionar. El hecho sigue en la otra lista, con su CORREGIRLO y su ANULARLO.
  const html = await htmlDeLaAgenda({
    previstos: [lineaPrevista({ cuando_lo_hice: "20/11/2026" })],
    hechos: [lineaHecha()],
  });

  assert.match(html, /Ya lo apuntaste como hecho:/, "no se dice que ese plan ya se cumplió");
  assert.match(html, /20\/11\/2026/, "no se dice cuándo se hizo");
  const acciones = accionesDe(html);
  assert.ok(!acciones.includes("trabajo-hecho"), "se ofrece apuntar otra vez un trabajo ya apuntado");
  assert.ok(!acciones.includes("trabajo-cancelar"), "se ofrece cancelar un plan que ya se cumplió");
  // Y el hecho de la otra lista sigue teniendo lo suyo: no se ha quedado sin salida.
  assert.ok(acciones.includes("trabajo-corregir"), "el hecho se queda sin poder corregirse");
  assert.ok(acciones.includes("trabajo-anular"), "el hecho se queda sin poder anularse");

  // El contraste, para que la prueba no pase por haber escondido todo: un plan sin cumplir **sí** ofrece
  // su botón.
  const sinCumplir = await htmlDeLaAgenda({ previstos: [lineaPrevista()] });
  assert.ok(
    accionesDe(sinCumplir).includes("trabajo-hecho"),
    "un plan sin cumplir tiene que poder marcarse como hecho",
  );
});

test("la agenda enseña lo previsto y lo hecho en dos listas con su título", async () => {
  // Si esto fallara, un plan aparecería mezclado con lo hecho y el agricultor creería que ya lo hizo:
  // es el defecto que el ticket entero existe para no cometer (lo previsto no acredita trabajo hecho).
  const html = await htmlDeLaAgenda({ previstos: [lineaPrevista()], hechos: [lineaHecha()] });

  const tituloPrevistos = html.indexOf(AGENDA.previstos_titulo);
  const tituloHechos = html.indexOf(AGENDA.hechos_titulo);
  assert.ok(tituloPrevistos > 0, "no sale el título de lo que está pensado");
  assert.ok(tituloHechos > 0, "no sale el título de lo que se ha hecho");
  assert.ok(tituloPrevistos < tituloHechos, "lo pensado sale después de lo hecho");
  // Y cada cosa en su lista: lo previsto antes, lo hecho después.
  assert.ok(html.indexOf("cultivador") < html.indexOf("trigo blando"), "las dos listas están mezcladas");
});

test("un trabajo previsto dice que no ha gastado nada y lo que gastaría", async () => {
  // La mitad de la regla del encargo, dicha en la pantalla: lo pensado **no** ha gastado nada, y lo que
  // gastaría se enseña como estimación.
  const html = await htmlDeLaAgenda({ previstos: [lineaPrevista()] });
  assert.match(html, /Dentro de 19 días/);
  assert.match(html, /Lo que gastaría/);
  assert.ok(html.includes(AGENDA.lo_previsto_no_gasta), "no dice que lo pensado no ha gastado nada");
});

test("sin nada planificado se dice, y el botón de planificar está ahí", async () => {
  const html = await htmlDeLaAgenda();
  assert.ok(html.includes(AGENDA.previstos_vacio));
  assert.ok(html.includes(AGENDA.hechos_vacio));
  assert.ok(accionesDe(html).includes("trabajo-planificar"), "no hay forma de planificar un trabajo");
});

test("sin tierras no se puede planificar, y el aviso trae el botón que lo arregla", async () => {
  // Regla de la casa: al agricultor no se le deja sin salida. Si le decimos que le falta algo, le damos
  // el botón que lo arregla.
  const html = await htmlDeLaAgenda({ puedePlanificar: false });
  assert.ok(html.includes(AGENDA.sin_tierras), "no dice que hace falta una tierra");
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("t06-ver-mis-tierras"), "el aviso no lleva a donde se arregla");
  assert.ok(!acciones.includes("trabajo-planificar"), "se puede planificar sin tener tierras");
});

test("lo anulado sale, con su motivo y diciendo que no cuenta", async () => {
  // **Nada se borra**: el apunte anulado se queda, tachado y explicado. Esconderlo dejaría al agricultor
  // sin poder explicar su propio cuaderno.
  const html = await htmlDeLaAgenda({
    hechos: [
      lineaHecha({
        anulado: true,
        no_cuenta: "Este apunte está anulado: lo que había salido del almacén vuelve a contar.",
        motivo_anulacion: "Me equivoqué de tierra",
      }),
    ],
  });
  assert.match(html, /Me equivoqué de tierra/, "no sale el motivo de la anulación");
  assert.match(html, /vuelve a contar/, "no dice que lo anulado deja de contar");
  // Y sigue saliendo el botón de corregirlo: el apunte está, no ha desaparecido.
  assert.ok(accionesDe(html).includes("trabajo-corregir"));
});

test("los huecos de un trabajo se enseñan como huecos, nunca como ceros", async () => {
  // «No dice las horas» es un dato. Un «0 h» diría que no se estuvo ninguna hora, y eso es una
  // afirmación que nadie ha hecho.
  const html = await htmlDeLaAgenda({
    hechos: [lineaHecha({ faltan: ["No dice las hectáreas", "No dice las horas"] })],
  });
  assert.match(html, /No dice las hectáreas/);
  assert.match(html, /No dice las horas/);
  assert.doesNotMatch(html, /0 ha/, "la pantalla ha puesto un cero donde no había dato");
  assert.doesNotMatch(html, /0 h\b/, "la pantalla ha puesto un cero donde no había dato");
});

test("lo que no consta se dice con su explicación", async () => {
  // Aquí se ve la mitad del ticket que no se puede deducir: una lluvia no acredita nascencia, y después
  // de la cosecha no se sabe lo que quedó. Si no se dice, el hueco parece un olvido del programa.
  const html = await htmlDeLaAgenda({
    lo_que_no_se_sabe: [
      { texto: "Que haya llovido no quiere decir que la planta haya nacido.", cuantos: 0 },
      { texto: "Hay trabajos que no dicen cuántas hectáreas se trabajaron.", cuantos: 3 },
    ],
  });
  assert.ok(html.includes(AGENDA.no_consta), "no hay bloque de lo que no consta");
  assert.match(html, /no quiere decir que la planta haya nacido/);
  assert.match(html, /<strong>3<\/strong>/, "no dice cuántos trabajos no traen sus hectáreas");
});

// ---------------------------------------------------------------------------
// 2. La ficha: cada modo guarda por su puerta
// ---------------------------------------------------------------------------

test("planificar guarda con la acción de lo previsto, y no con la de lo hecho", async () => {
  // **La prueba que separa las dos mitades del ticket.** Planificar no puede llamar a la puerta que
  // apunta un trabajo hecho: esa es la que descuenta del almacén.
  const html = await htmlDeUnTrabajo({ modo: "planificar" });
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("trabajo-previsto-guardar"), "planificar no guarda por su puerta");
  assert.ok(!acciones.includes("trabajo-hecho-guardar"), "planificar apunta un trabajo hecho");
  assert.match(html, /GUARDAR LO QUE PIENSO HACER/);
});

test("marcar lo hecho guarda por la puerta que descuenta del almacén", async () => {
  const html = await htmlDeUnTrabajo({ modo: "hecho" });
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("trabajo-hecho-guardar"));
  assert.ok(!acciones.includes("trabajo-previsto-guardar"));
  assert.match(html, /APUNTAR LO QUE HE HECHO/);
});

test("al marcar lo hecho se ve lo que se había pensado, y que eso no ha gastado nada", async () => {
  // Sin esto, el agricultor apuntaría el plan como si fuera el hecho: es el caso A05 al revés.
  const html = await htmlDeUnTrabajo({
    modo: "hecho",
    previsto: { filas: [{ etiqueta: "Qué trabajo", valor: "Laboreo · cultivador" }] },
  });
  assert.match(html, /Lo que tenías pensado/);
  assert.match(html, /Laboreo · cultivador/);
  assert.ok(html.includes(AGENDA.lo_previsto_no_gasta), "no dice que lo pensado no gastó nada");
});

test("cambiar de día guarda por la puerta de reprogramar y solo deja tocar el día", async () => {
  // Reprogramar es su propia puerta porque **deja escrito el día que tenía antes**; y lo hecho no se
  // reprograma, que es lo que el contrato pide con esas palabras.
  const html = await htmlDeUnTrabajo({ modo: "reprogramar", borrador: { fecha_prevista: "2026-04-25" } });
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("trabajo-reprogramar"), "cambiar de día no guarda por su puerta");
  assert.ok(!acciones.includes("trabajo-hecho-guardar"));
  assert.match(html, /id="trabajo-fecha-prevista"/);
  // Los demás campos salen, para poder mirarlos, y **no se pueden tocar**: lo que se cambia aquí es el día.
  assert.match(html, /id="trabajo-superficie"[^>]*readonly/);
  assert.match(html, /id="trabajo-tipo"[^>]*disabled/);
});

test("corregir guarda por la puerta de la corrección, con el día de verdad a la vista", async () => {
  const html = await htmlDeUnTrabajo({ modo: "corregir", borrador: { fecha: "2026-03-01" } });
  assert.ok(accionesDe(html).includes("trabajo-guardar"));
  assert.match(html, /id="trabajo-fecha"/);
  assert.match(html, /GUARDAR LA CORRECCIÓN/);
});

test("anular pide el motivo y no borra nada", async () => {
  // Un trabajo no se borra: se anula con su motivo. Y el agricultor tiene que poder salir sin anular
  // —VOLVER A LOS TRABAJOS—, porque una pantalla que solo ofrece «anular» empuja a anular.
  const html = await htmlDeUnTrabajo({ modo: "anular" });
  const acciones = accionesDe(html);
  assert.ok(acciones.includes("trabajo-anular-confirmar"), "anular no confirma por su puerta");
  assert.match(html, /id="trabajo-motivo"/);
  assert.match(html, /Por qué lo anulas/);
  assert.match(html, /Escríbelo pensando en que lo vas a leer dentro de dos años/);
  assert.ok(acciones.includes("trabajos-ver"), "no hay forma de salir sin anular");
  // Y en el modo de anular **no** se puede cambiar el trabajo: solo se dice por qué se anula.
  assert.doesNotMatch(html, /id="trabajo-fecha"/);
});

test("el repaso de antes de guardar se enseña cuando el servidor lo trae", async () => {
  const html = await htmlDeUnTrabajo({ modo: "hecho", repaso: ["El envase se queda en 40 kg"] });
  assert.match(html, /Antes de guardar, mira esto/);
  assert.match(html, /El envase se queda en 40 kg/);
});

test("los huecos del formulario se piden vacíos, no con un cero", async () => {
  const html = await htmlDeUnTrabajo({ modo: "hecho" });
  assert.match(html, /id="trabajo-superficie"[^>]*value=""/);
  assert.match(html, /id="trabajo-horas"[^>]*value=""/);
  assert.match(html, /Si no lo sabes, déjalo en blanco/);
});

test("todas las acciones de la ficha son las que el ticket dice, y ninguna más", async () => {
  // Las acciones de esta pantalla las tiene que atender el manejador de clics de `app.js`, que es uno
  // solo. Esta prueba fija la lista: si alguien inventa una acción nueva, aquí se ve, y el informe del
  // ticket —con lo que tiene que hacer cada una— deja de valer.
  const esperadas = new Set([
    "trabajo-previsto-guardar",
    "trabajo-hecho-guardar",
    "trabajo-guardar",
    "trabajo-anular-confirmar",
    "trabajo-reprogramar",
    "trabajos-ver",
  ]);
  const vistas = new Set();
  for (const modo of ["planificar", "reprogramar", "hecho", "corregir", "anular"]) {
    for (const accion of accionesDe(await htmlDeUnTrabajo({ modo }))) vistas.add(accion);
  }
  const de_mas = [...vistas].filter((accion) => !esperadas.has(accion));
  const de_menos = [...esperadas].filter((accion) => !vistas.has(accion));
  assert.deepEqual(de_mas, [], "hay acciones que nadie ha decidido");
  assert.deepEqual(de_menos, []);
});

test("los campos del formulario son los que lee app.js", async () => {
  // Si un `id` cambia, `app.js` recoge vacío y el trabajo se guarda sin lo escrito, sin que salte nada.
  const campos = camposDe(await htmlDeUnTrabajo({ modo: "hecho" }));
  for (const campo of [
    "trabajo-tipo",
    "trabajo-subtipo",
    "trabajo-tierra",
    "trabajo-fecha",
    "trabajo-superficie",
    "trabajo-horas",
    "trabajo-maquina",
    "trabajo-insumo",
    "trabajo-cantidad",
    "trabajo-unidad",
    "trabajo-observaciones",
  ]) {
    assert.ok(campos.includes(campo), `falta el campo «${campo}», y app.js lo busca`);
  }
  const deUnPlan = camposDe(await htmlDeUnTrabajo({ modo: "planificar" }));
  assert.ok(deUnPlan.includes("trabajo-fecha-prevista"), "planificar no pregunta para qué día");
  assert.ok(!deUnPlan.includes("trabajo-fecha"), "un plan pregunta el día en que se hizo");
});

// ---------------------------------------------------------------------------
// 3. La historia de una tierra
// ---------------------------------------------------------------------------

test("la historia lleva todo lo que ha pasado, con lo anulado dentro y su motivo", async () => {
  const html = await htmlDeLaTierra({
    historial: [
      { titulo: "Siembra", cuando: "01/03/2026", filas: [{ etiqueta: "Hectáreas", valor: "3,00" }] },
      {
        titulo: "Laboreo · rodillo",
        cuando: "10/03/2026",
        filas: [],
        anulado: true,
        no_cuenta: "Este apunte está anulado: lo que había salido del almacén vuelve a contar.",
        motivo_anulacion: "No llegué a hacerlo",
      },
    ],
  });
  assert.match(html, /Siembra/);
  assert.match(html, /Laboreo · rodillo/, "el historial ha perdido un evento");
  assert.match(html, /No llegué a hacerlo/);
  assert.ok(html.includes(AGENDA.historial_explica));
});

test("la ficha de la tierra separa lo sembrado, la última labor, el historial y lo previsto", async () => {
  // El contrato lo pide así (S03): «separar última labor, cultivo declarado, observación de campo y
  // estimación». Mezclarlo es lo que hace que un programa parezca saber más de lo que sabe.
  const html = await htmlDeLaTierra({
    estado: {
      cultivo_declarado: { cultivo: "Trigo blando", variedad: "Craklin", fecha: "01/03/2026" },
      ultima_labor: true,
      ultima_labor_titulo: "Laboreo · rodillo",
      ultima_labor_cuando: "10/03/2026",
      previstos: [{ titulo: "Laboreo · cultivador", cuando: "Dentro de 19 días" }],
      observaciones: [{ texto: "Ha nacido parejo", cuando: "20/03/2026" }],
    },
  });
  assert.ok(html.includes(AGENDA.que_hay_hoy));
  assert.match(html, /Trigo blando/);
  assert.match(html, /Craklin/);
  assert.ok(html.includes(AGENDA.ultima_labor));
  assert.ok(html.includes(AGENDA.historial_titulo));
  assert.ok(html.includes(AGENDA.previstos_titulo), "lo previsto no sale aparte");
  assert.ok(html.includes(AGENDA.observaciones_de_campo));
});

test("una tierra sin nada sembrado lo dice, y no se inventa un cultivo", async () => {
  const html = await htmlDeLaTierra({ estado: { cultivo_declarado: null } });
  assert.ok(html.includes(AGENDA.sin_cultivo_declarado));
  assert.ok(html.includes(AGENDA.historial_vacio));
});

test("lo que ha costado la tierra sale con sus dos cifras y con el enlace a cada gasto", async () => {
  // **La mitad que le faltaba al recorrido de abrir una tierra** (T15 + T13, 05/10/2026): los trabajos
  // ya salían en el historial y el dinero no. Las dos cifras van separadas —lo que pone el papel y lo
  // repartido, que es una estimación— y **cada línea lleva su botón para abrir esa ficha del gasto**,
  // que es donde están sus repartos y sus pagos: un número del que no se puede llegar a sus apuntes no
  // sirve para comprobarlo.
  const html = await htmlDeLaTierra({
    costes: {
      directos: "250.00",
      texto_directos: "250,00 €",
      repartidos: "60.00",
      texto_repartidos: "60,00 €",
      total_conocido: "310.00",
      texto_total: "310,00 €",
      sin_importe: 1,
      filas: [
        {
          gasto_id: 7,
          que_es: "Gasóleo",
          fecha: "2026-03-04",
          importe: "250.00",
          texto_importe: "250,00 €",
          de_donde: "directo",
        },
        {
          gasto_id: 9,
          que_es: "Seguro de la finca",
          fecha: null,
          importe: "60.00",
          texto_importe: "60,00 €",
          de_donde: "repartido",
        },
      ],
    },
  });
  assert.ok(html.includes(AGENDA.costes_titulo), "no sale lo que ha costado la tierra");
  assert.ok(html.includes(AGENDA.costes_directos));
  assert.ok(html.includes(AGENDA.costes_repartidos), "las dos cifras no van separadas");
  assert.match(html, /250,00 €/);
  assert.match(html, /60,00 €/);
  // **Un total que calla que le faltan datos miente**: se dice cuántos no traen el importe.
  assert.match(html, /1 gasto de esta tierra que no dice lo que costó/);
  // Y cada línea lleva su enlace al registro: el botón que abre esa ficha del gasto.
  assert.match(html, /data-accion="gasto-abrir" data-id="7"/);
  assert.match(html, /data-accion="gasto-abrir" data-id="9"/);
  assert.ok(html.includes(AGENDA.costes_directo_es) && html.includes(AGENDA.costes_repartido_es));
});

test("sin costes no se enseña el bloque, y sin gastos se dice que no hay", async () => {
  // Lo primero es lo que pasa cuando las cuentas no contestan: la historia se enseña igual y el bloque
  // **no sale** (mejor que un bloque con ceros, que diría que esa tierra no ha costado nada).
  const sinCostes = await htmlDeLaTierra({});
  assert.ok(!sinCostes.includes(AGENDA.costes_titulo), "enseña costes que no le han llegado");
  const vacio = await htmlDeLaTierra({
    costes: { directos: "0.00", texto_directos: "0,00 €", repartidos: "0.00", texto_repartidos: "0,00 €", total_conocido: "0.00", texto_total: "0,00 €", sin_importe: 0, filas: [] },
  });
  assert.ok(vacio.includes(AGENDA.costes_vacio), "una tierra sin gastos no lo dice");
});

test("cuando el apero va detrás de la siembra, la pantalla lo explica", async () => {
  // «Un rodillo después de sembrar no borra el estado de siembra»: al ver un rodillo justo detrás de una
  // siembra, lo primero que se pregunta es si se ha perdido el cultivo. La pantalla lo dice.
  const html = await htmlDeLaTierra({
    estado: {
      cultivo_declarado: { cultivo: "Trigo blando", fecha: "01/03/2026" },
      apero_no_cambia: "Pasar el rodillo no cambia lo que tienes sembrado: la siembra sigue apuntada.",
    },
  });
  assert.match(html, /no cambia lo que tienes sembrado/);
  assert.match(html, /Trigo blando/, "la explicación ha borrado lo sembrado");
});

// ---------------------------------------------------------------------------
// 4. La pantalla no lleva ni una frase escrita a mano, y no le falta ninguna
// ---------------------------------------------------------------------------

/**
 * Un vocabulario de mentira que **apunta qué claves se leen**.
 *
 * Es la forma de comprobar dos cosas de una vez, y las dos son el mismo defecto: una clave que la
 * pantalla lee y no está en los textos **sale en blanco en la pantalla** (y no revienta nada, así que
 * ningún test se entera), y una frase que está y no la lee nadie es una frase que se queda vieja.
 */
function vocabularioQueApuntaLasClaves(usadas) {
  return new Proxy(
    {},
    {
      get(_destino, clave) {
        if (typeof clave !== "string") return undefined;
        usadas.add(clave);
        // El valor es la clave entre comillas angulares: así se ve en el HTML y se puede comprobar.
        return `«${clave}»`;
      },
    },
  );
}

test("la pantalla no lee ninguna frase que no esté en los textos", async () => {
  const usadas = new Set();
  const agenda = vocabularioQueApuntaLasClaves(usadas);
  const textos = { agenda, acciones: vocabularioQueApuntaLasClaves(new Set()) };

  // Se recorren **todas** las ramas de las tres pantallas: la lista con cosas y vacía, el aviso de que
  // no hay tierras, el estado de «cargando», los cinco modos de la ficha con su botón deshabilitado, la
  // tierra con labores y sin ninguna, y una línea revisada y firmada. Si una clave solo se lee en una de
  // esas ramas y nadie la recorre, esta prueba no la vería: por eso están todas.
  await htmlDeLaAgenda({
    textos,
    // Los dos casos de la lista de lo pensado: el plan que sigue pendiente y **el que ya se cumplió** (que
    // trae su día). Sin el segundo, la frase de «ya lo apuntaste como hecho» no la leería nadie y esta
    // prueba no la vería.
    previstos: [lineaPrevista(), lineaPrevista({ id: 10, cuando_lo_hice: "20/11/2026" })],
    hechos: [lineaHecha({ faltan: ["Falta algo"] })],
    lo_que_no_se_sabe: [{ texto: "Algo", cuantos: 1 }],
    aviso: "Un aviso",
    avisos: ["Otro aviso"],
  });
  await htmlDeLaAgenda({ textos, aviso: "Un aviso" }); // las dos listas vacías
  await htmlDeLaAgenda({ textos, cargando: true });
  await htmlDeLaAgenda({ textos, puedePlanificar: false });
  for (const modo of ["planificar", "reprogramar", "hecho", "corregir", "anular"]) {
    await htmlDeUnTrabajo({
      textos,
      modo,
      previsto: { filas: [{ etiqueta: "E", valor: "V" }] },
      repaso: ["Repaso"],
      guardando: true,
    });
  }
  await htmlDeLaTierra({
    textos,
    estado: {
      cultivo_declarado: { cultivo: "Trigo", variedad: "Craklin", fecha: "01/03/2026" },
      ultima_labor: true,
      ultima_labor_titulo: "Rodillo",
      ultima_labor_cuando: "10/03/2026",
      previstos: [{ titulo: "P", cuando: "C" }],
      observaciones: [{ texto: "O", cuando: "C" }],
      apero_no_cambia: "A",
    },
    historial: [
      {
        titulo: "Siembra",
        cuando: "01/03/2026",
        filas: [{ etiqueta: "Hectáreas", valor: "3,00" }],
        revisado: true,
        firmado: true,
        anulado: true,
        no_cuenta: "No cuenta",
        motivo_anulacion: "Un motivo",
      },
    ],
    no_consta: [{ texto: "N", cuantos: 0 }],
    // **Y el bloque de lo que ha costado** (T13 + T15): se recorre aquí para que sus frases cuenten como
    // leídas. Si no, la comprobación de abajo diría que están escritas y no las lee nadie —que es
    // exactamente lo que tiene que decir cuando alguien añade una frase y no la pinta—.
    costes: {
      directos: "1.00",
      texto_directos: "1,00 €",
      repartidos: "2.00",
      texto_repartidos: "2,00 €",
      total_conocido: "3.00",
      texto_total: "3,00 €",
      sin_importe: 1,
      filas: [
        { gasto_id: 7, que_es: "Gasóleo", fecha: "2026-03-04", texto_importe: "1,00 €", de_donde: "directo" },
        { gasto_id: 9, que_es: "Seguro", fecha: null, texto_importe: "2,00 €", de_donde: "repartido" },
      ],
    },
  });
  await htmlDeLaTierra({ textos, estado: { cultivo_declarado: null } });
  // Y la rama de la tierra **sin ningún gasto**, que también tiene su frase.
  await htmlDeLaTierra({
    textos,
    costes: {
      directos: "0.00",
      texto_directos: "0,00 €",
      repartidos: "0.00",
      texto_repartidos: "0,00 €",
      total_conocido: "0.00",
      texto_total: "0,00 €",
      sin_importe: 0,
      filas: [],
    },
  });

  const sin_frase = [...usadas].filter((clave) => !(clave in AGENDA));
  assert.deepEqual(
    sin_frase.sort(),
    [],
    "estas claves las lee la pantalla y no están en la copia de los textos: saldrían en blanco",
  );
  const sin_usar = Object.keys(AGENDA).filter((clave) => !usadas.has(clave));
  assert.deepEqual(sin_usar.sort(), [], "estas frases están escritas y no las lee nadie");
});

test("ninguna frase de la pantalla lleva jerga", async () => {
  // La regla de la casa, comprobada en la copia que usan estas pruebas: si una frase lleva una palabra
  // prohibida, el test de jerga de Python la cazaría al entrar en `textos.py`… si alguien se acuerda de
  // meterla. Aquí se caza antes.
  const prohibidas = [
    "error",
    "validación",
    "cumplimentar",
    "epígrafe",
    "dosificación",
    "trazabilidad",
    "interfaz",
    "sincronizar",
    "sesión",
    "campo obligatorio",
    "operación cultural",
    "fitosanitario",
    "dgc",
    "uhc",
  ];
  for (const [clave, frase] of Object.entries(AGENDA)) {
    for (const prohibida of prohibidas) {
      assert.ok(!frase.toLowerCase().includes(prohibida), `«${clave}» lleva «${prohibida}»`);
    }
  }
});

test("la pantalla no toca el navegador: ni fetch, ni localStorage, ni document", () => {
  // El componente es puro: recibe propiedades y devuelve un elemento. Si tocara el navegador, no se
  // podría probar sin uno y el servidor de ficheros no bastaría para servirla.
  const codigo = readFileSync(new URL("../web/react/pantallas/trabajos.js", import.meta.url), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
  for (const prohibida of ["fetch(", "localStorage", "sessionStorage", "document.", "window."]) {
    assert.ok(!codigo.includes(prohibida), `trabajos.js usa «${prohibida}»`);
  }
  assert.ok(codigo.includes("export function PantallaDeLosTrabajos"), "el quitador se ha comido el fichero");
});
