/*
 * bandeja.test.js — las pruebas de la bandeja de los papeles (T08, S10, 06/10/2026).
 *
 * POR QUÉ ESTÁN AQUÍ Y NO EN `interfaz.test.js`
 *
 * La pantalla está escrita en React (`web/react/pantallas/bandeja.js`) y en el DOM de mentira de
 * `interfaz.test.js` React no se puede montar. Así que se prueba **contra el componente**: se le dan las
 * propiedades y se mira el HTML que produce con `renderToStaticMarkup`, igual que con las demás pantallas
 * migradas. No hay `jsdom` ni ninguna dependencia nueva.
 *
 * QUÉ SE COMPRUEBA, Y POR QUÉ ESAS COSAS
 *
 * Las dos reglas del ticket tienen aquí su prueba que muerde, y son la mitad del fichero:
 *
 *  1. **El original no se toca nunca.** El nombre del fichero, su tamaño y su huella **se enseñan y no se
 *     editan**: no hay ningún campo para ellos, y hay un botón para ver el fichero. Además, la huella del
 *     original **no cambia al confirmar** (eso se comprueba en el servidor, en `tests/test_bandeja.py`).
 *  2. **Lo leído es una propuesta, no un dato.** La pantalla **no dice que la lectura esté bien**: no
 *     aparece la palabra «confianza» ni un `%` por ningún lado, y sí aparece la frase que dice que no se
 *     puede medir. Y **no se puede confirmar sin haber revisado**: el botón de confirmar solo sale cuando
 *     el servidor dice que se puede.
 *
 * Y además, las cosas del recorrido que se rompen solas si nadie las mira:
 *
 *  3. **Un duplicado se dice antes de apuntarlo** y **no hay botón de subirlo**: si el fichero ya estaba,
 *     el único camino que queda es ver el papel que ya estaba o elegir otro fichero.
 *  4. **Un importe que no consta se enseña como hueco y nunca como cero.** Se comprueba de la manera que
 *     muerde: al total de una propuesta se le pasa un `0,00 €` **con el dato a nulo**, y la pantalla tiene
 *     que enseñar su palabra («No consta») y **no** el cero.
 *  5. **Enlazar no crea nada**: la pantalla lo dice, y no ofrece ningún botón de crear un gasto ni una
 *     factura (`tests/test_los_botones_hacen_algo.py` caza una acción que nadie atienda, y aquí se caza una
 *     acción que prometa crear algo).
 *  6. **Las rectificativas dejan las dos**: se dice a quién corrige y quién corrige a este.
 *  7. **El estado se ve siempre y dice qué hacer con él**: «recién subido», «sin leer» y «revisado, sin
 *     confirmar» no son lo mismo, y la pantalla no los junta.
 *
 * LA COPIA DE LOS TEXTOS (`BANDEJA`, aquí abajo) son **las claves que esta pantalla lee**, y su bloque
 * completo para `app/textos.py` está en `docs/T08_BANDEJA.md`. Va aparte, con una clave por línea, para que
 * la prueba de Python del ticket pueda leerla y compararla con lo que sirve el servidor. Aquí además se
 * comprueba —leyendo el informe— que **no hay ninguna clave que esté en esta copia y no esté en el bloque
 * que se integra**: una clave así saldría en blanco en la pantalla de verdad y ninguna prueba se enteraría.
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

const RUTA_DE_LA_PANTALLA = new URL("../web/react/pantallas/bandeja.js", import.meta.url);
const RUTA_DEL_INFORME = new URL("../../docs/T08_BANDEJA.md", import.meta.url);

// ---------------------------------------------------------------------------
// La copia de los textos que lee esta pantalla
// ---------------------------------------------------------------------------

/**
 * El bloque `BANDEJA` de `textos.py`, con **las claves que lee esta pantalla**.
 *
 * Aquí **no** están las que lee el servidor y la pantalla recibe ya resueltas, y se dice para que nadie
 * las busque en balde: `cuantos` y `cuantos_uno` (el pie de la lista lo compone el servidor con
 * `con_cuenta`), `eso_ya_no_esta`, las cuatro `estado_<estado>` y las seis `clase_<clase>` (llegan escritas
 * en `etiqueta_estado` y `etiqueta_clase`, que es la regla de este programa: el vocabulario vive en el
 * servidor), y los cuatro rótulos que `app.js` pone dentro del formulario (`guardar`, `cancelar`,
 * `guardando` y `revisar_titulo`/`revisar_pista`). Esas están en el bloque del informe y las revisa la
 * prueba de Python del ticket; aquí solo están las que la pantalla lee de verdad.
 */
const BANDEJA = {
  titulo: "La bandeja de los papeles",
  explica:
    "Aquí llega lo que todavía no has mirado: la foto de una factura, el ticket del gasóleo, el certificado de una máquina. El papel se guarda tal y como llega, y nada entra en tu cuaderno hasta que tú lo confirmes.",
  sin_papeles:
    "La bandeja está vacía: no tienes ningún papel esperando. Sube uno con el botón de aquí arriba cuando te llegue.",
  sin_resultados: "Ningún papel coincide con lo que buscas. Prueba con otras letras o pulsa VER TODO.",
  faltan_por_decir_de_que_son:
    "Hay papeles a los que todavía no has dicho de qué son. Ábrelos y dilo: un papel que no se sabe qué es no sirve de nada en una inspección.",
  no_consta: "No consta",
  si: "Sí",
  no: "No",
  buscando: "Buscando…",
  // --- subir ---
  subir_titulo: "Subir un papel",
  subir_explica:
    "Elige el fichero (una foto o un PDF) y di de qué es. El papel se guarda tal y como llegó.",
  nada_se_apunta:
    "Subir no apunta nada al cuaderno: solo guarda el papel. Lo que se lea de él es una propuesta, y la confirmas tú.",
  fichero: "El papel, en una foto o en un PDF",
  fichero_pista: "Hazle una foto al papel o elige el fichero que ya tienes.",
  fichero_elegido: "El fichero que has elegido es",
  de_que_es: "¿De qué es?",
  de_que_es_pista: "Si todavía no lo sabes, déjalo en «no lo sé» y díselo luego desde la bandeja.",
  no_lo_se_todavia: "Todavía no lo sé",
  decir_de_que_es: "DECIR DE QUÉ ES",
  comprobar_el_fichero: "COMPROBAR EL FICHERO",
  comprobando: "Comprobando…",
  subir_el_papel: "SUBIR EL PAPEL",
  subiendo: "Subiendo…",
  olvidar_el_fichero: "ELEGIR OTRO FICHERO",
  lo_que_se_ha_comprobado: "Lo que he visto del fichero",
  la_huella: "Su huella",
  la_huella_pista:
    "Es la huella del fichero tal y como llegó. Sirve para saber que este papel es este y no otro, y no cambia nunca.",
  tamano: "Cuánto ocupa",
  ya_estaba: "Este mismo papel ya lo tienes",
  ya_estaba_explica:
    "No se ha guardado otra vez: el mismo papel no puede estar dos veces. Es este:",
  del_que_ya_estaba_subido: "Lo subiste el",
  abrir_el_que_ya_estaba: "VER EL PAPEL QUE YA TENÍA",
  no_estaba: "Este papel no lo tenías: puedes subirlo.",
  // --- la lista ---
  lista_titulo: "Lo que hay que revisar",
  lista_explica:
    "Cada papel, con cómo está y qué le falta. Los que confirmes salen de aquí y se ven en LOS PAPELES.",
  buscar: "Buscar en la bandeja",
  buscar_pista: "Escribe parte del nombre o de quién te lo dio.",
  buscar_boton: "BUSCAR",
  ver_todo: "VER TODO",
  cuales_ver: "Cuáles ver",
  todos_los_tipos: "De todo",
  lo_que_es: "Qué es",
  el_dia_del_papel: "El día del papel",
  de_quien: "De quién",
  el_fichero: "El fichero",
  sin_fichero: "Sin fichero",
  su_lectura: "Su lectura",
  tiene_propuesta: "Leído, sin revisar",
  sin_propuesta: "Todavía no se ha leído",
  enlazado_con: "Va con",
  sin_enlazar: "Sin enlazar con nada",
  abrir: "MIRAR ESTE PAPEL",
  los_papeles: "VER TODOS LOS PAPELES",
  // --- la ficha ---
  ficha_titulo: "Este papel",
  el_original: "El papel, tal y como llegó",
  el_original_explica:
    "Este es el fichero que subiste. El programa no lo cambia nunca: lo que se lee de él va aparte.",
  ver_el_original: "VER EL ORIGINAL",
  sin_fichero_aviso:
    "Este papel está apuntado sin su fichero. Súbelo desde LOS PAPELES para poder leerlo.",
  // --- la propuesta ---
  la_propuesta: "Lo que el programa ha leído",
  la_propuesta_explica:
    "Esto es una propuesta, no un dato: nada de esto ha entrado en tu cuaderno.",
  no_se_mide_la_lectura:
    "El programa no dice si esta lectura está bien: para eso habría que compararla con muchísimas facturas de verdad, y esa colección todavía no existe. Mírala tú, campo por campo.",
  leer_el_papel: "LEER EL PAPEL",
  leyendo: "Leyendo el papel…",
  no_hay_propuesta: "De este papel no hay ninguna lectura. Puedes escribir los datos a mano.",
  este_papel_no_lo_se_leer:
    "De este tipo de papel todavía no sé leer nada. Escribe los datos a mano y quedan guardados igual.",
  avisos_titulo: "Lo que hay que mirar de esta lectura",
  las_lineas: "Las líneas que he leído",
  sin_lineas: "No he reconocido ninguna línea. Puede ser una factura de servicios.",
  lineas_leidas: "Líneas leídas",
  lineas_que_cuadran: "Con la cuenta bien",
  la_cuenta_cuadra: "La cuenta cuadra",
  la_cuenta_no_cuadra: "La cuenta no cuadra: mírala antes de guardar",
  cuadra_el_total: "La base más el IVA da el total",
  suman_las_lineas: "Las líneas suman la base",
  cantidad: "Cuánto",
  precio: "El precio",
  importe: "El importe",
  proveedor: "El proveedor",
  nif_del_proveedor: "Su NIF",
  numero_de_factura: "El número de factura",
  fecha: "La fecha",
  base_imponible: "La base",
  cuota_de_iva: "El IVA",
  tipo_de_iva: "El tipo de IVA",
  total: "El total",
  descartada: "Esta lectura la descartaste: no te servía.",
  // --- revisar y confirmar ---
  lo_aceptado: "Lo que has aceptado",
  lo_aceptado_explica: "Esto es lo que queda de este papel. Todavía no está confirmado.",
  revisar: "REVISAR Y DECIR QUÉ QUEDA",
  sin_aceptar_nada: "Todavía no has dicho qué queda de este papel.",
  hay_que_revisar_antes:
    "Antes de confirmar hay que decir qué queda: revisa la lectura o escribe los datos a mano.",
  confirmar: "CONFIRMAR ESTE PAPEL",
  confirmando: "Confirmando…",
  confirmar_explica:
    "Al confirmarlo, lo que has aceptado pasa al papel con tu nombre y la fecha. El fichero no se toca.",
  ya_esta_en_los_papeles: "Este papel ya está confirmado y se ve en LOS PAPELES.",
  confirmado_por: "Lo confirmaste tú",
  confirmado_en: "Cuándo",
  motivo: "¿Por qué no te sirve?",
  descartar_pista: "Dímelo, para que quede apuntado por qué este papel se escribió a mano.",
  descartar_la_propuesta: "ESTA LECTURA NO ME SIRVE",
  // --- enlazar ---
  enlazar_titulo: "Con qué va este papel",
  enlazar_explica:
    "Un papel puede ir con una compra, un gasto, una venta, una máquina, un trabajo o una inspección.",
  no_crea_nada:
    "Enlazar no crea nada: ni un gasto, ni una factura, ni una venta. Solo dice con qué va este papel.",
  de_que_clase: "¿Con qué quieres enlazarlo?",
  buscar_candidato: "Buscar lo que ya tienes",
  buscar_candidato_pista: "Escribe parte del nombre si no lo encuentras en la lista.",
  buscar_candidatos: "BUSCAR",
  cual_de_ellos: "¿Cuál de ellos?",
  elige_uno: "Elige uno",
  enlazar: "ENLAZARLO",
  enlazando: "Enlazando…",
  enlazado_titulo: "Con esto va",
  desenlazar: "QUITARLO DE AHÍ",
  sin_candidatos: "No hay nada de eso en tu cuaderno. Apúntalo primero en su pantalla y vuelve.",
  // --- rectificar ---
  rectificar_titulo: "Este papel corrige a otro",
  rectificar_explica:
    "Si es la factura corregida que sustituye a la anterior, dilo aquí. Las dos quedan: la corregida sigue ahí, marcada, y no se borra.",
  a_que_papel: "¿A qué papel corrige?",
  elige_el_papel: "Elige el papel",
  rectificar: "DECIR QUE CORRIGE A ESE",
  rectifica_a: "Corrige a",
  rectificada_por: "Este papel está corregido por",
  nadie_lo_ha_corregido: "Este papel no corrige a ninguno ni lo ha corregido nadie.",
  volver_a_la_bandeja: "VOLVER A LA BANDEJA",
  // --- y qué hacer con él, según cómo esté (el servidor manda el estado ya en palabras) ---
  que_hacer_recien_subido: "Falta decir de qué es: elige su tipo y el papel sale de «recién subido».",
  que_hacer_clasificado: "Falta mirarlo: léelo (o escríbelo a mano) y di qué queda.",
  que_hacer_propuesta_revisada: "Ya has dicho qué queda: confírmalo cuando quieras.",
};

const TEXTOS = { bandeja: BANDEJA, acciones: { volver: "VOLVER" } };

/**
 * Las seis clases de vínculo, como las sirve el servidor: `[{valor, texto}]`.
 *
 * Van aquí, y no dentro de cada prueba, porque **sus textos son datos del servidor**: la prueba de las
 * frases a mano tiene que saber que esas frases vienen de las propiedades y no del componente.
 */
const CLASES = [
  { valor: "compra", texto: "Una compra de lo que has comprado" },
  { valor: "gasto", texto: "Un gasto" },
  { valor: "venta", texto: "Una venta de tu cosecha" },
  { valor: "maquina", texto: "Una máquina" },
  { valor: "trabajo", texto: "Un trabajo hecho" },
  { valor: "inspeccion", texto: "Una inspección de una máquina" },
];

const TIPOS = [
  { valor: "factura", etiqueta: "Una factura" },
  { valor: "inspeccion", etiqueta: "Un certificado de inspección" },
];

const ESTADOS = [
  { valor: "sin_revisar", etiqueta: "Sin revisar" },
  { valor: "recien_subido", etiqueta: "Recién subido" },
  { valor: "clasificado", etiqueta: "Sin leer" },
  { valor: "propuesta_revisada", etiqueta: "Revisado, sin confirmar" },
  { valor: "confirmado", etiqueta: "Confirmado" },
  { valor: "todos", etiqueta: "Todos" },
];

// ---------------------------------------------------------------------------
// Los datos, tal y como los prepara `app.js`
// ---------------------------------------------------------------------------

/** Una cabecera (lo leído o lo aceptado): el dato en texto decimal **y** su versión escrita. */
function unaCabecera(cambios = {}) {
  const campos = {
    proveedor: "Ferretería del Páramo",
    proveedor_nif: "B12345678",
    numero_factura: "2026/0042",
    fecha: "2026-10-01",
    base_imponible: "810.00",
    cuota_iva: "170.10",
    tipo_iva_pct: "21.00",
    total: "980.10",
    ...(cambios.campos || {}),
  };
  const textos = {
    proveedor: "Ferretería del Páramo",
    proveedor_nif: "B12345678",
    numero_factura: "2026/0042",
    fecha: "01/10/2026",
    base_imponible: "810,00 €",
    cuota_iva: "170,10 €",
    tipo_iva_pct: "21,00 €",
    total: "980,10 €",
    ...(cambios.textos || {}),
  };
  return { campos, textos };
}

/** Una línea leída, con lo que el servidor añade de su versión escrita. */
function unaLinea(cambios = {}) {
  return {
    descripcion: "Gasóleo agrícola",
    cantidad: "300",
    texto_cantidad: "300",
    unidad: "L",
    precio_unitario: "1.200000",
    texto_precio_unitario: "1,2000 €",
    importe: "360.00",
    texto_importe: "360,00 €",
    numero_registro: "",
    la_cuenta_cuadra: true,
    producto_sugerido: "",
    ...cambios,
  };
}

/** La propuesta, tal y como la devuelve `GET /api/bandeja/<id>`. */
function unaPropuesta(cambios = {}) {
  const { campos, textos } = unaCabecera(cambios);
  return {
    clase: "factura",
    como_se_leyo: "texto",
    leido_en: "2026-10-06T09:00:00",
    campos,
    textos,
    lineas: [unaLinea()],
    avisos: [],
    lineas_leidas: 1,
    lineas_que_cuadran: 1,
    cuadra_el_total: true,
    suman_las_lineas: true,
    ...cambios,
  };
}

/** Un papel de la bandeja, con sus `texto_*` ya escritos (los pone `app.js` con `enEuros`). */
function unPapel(cambios = {}) {
  return {
    id: 5,
    titulo: "factura-del-gasoleo",
    tipo: "factura",
    etiqueta_tipo: "Una factura",
    carpeta: "Facturas",
    estado: "clasificado",
    etiqueta_estado: "Sin leer",
    sin_revisar: true,
    fecha: "2026-10-01",
    texto_fecha: "01/10/2026",
    quien: "Ferretería del Páramo",
    tiene_fichero: true,
    nombre_del_fichero: "factura-gasoleo.pdf",
    tipo_del_fichero: "application/pdf",
    bytes: 20480,
    texto_tamano: "20,0 KB",
    huella: "9f2c0a5b3e4d5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8",
    como_se_leyo: "texto",
    propuesta_descartada: false,
    la_propuesta: unaPropuesta(),
    lo_aceptado: null,
    se_puede_leer: true,
    se_puede_confirmar: false,
    se_puede_descartar_la_propuesta: true,
    confirmado_en: null,
    confirmado_por: null,
    texto_confirmado_en: "",
    rectifica_a: null,
    rectificada_por: [],
    vinculos: [],
    clases_sugeridas: ["compra", "gasto"],
    cuantos_candidatos: { compra: 3, gasto: 12, venta: 4, maquina: 6, trabajo: 20, inspeccion: 2 },
    creado_en: "2026-10-06T09:00:00",
    ...cambios,
  };
}

/** Un papel ya revisado (con lo aceptado) pero sin confirmar: el único que se puede confirmar. */
function unPapelRevisado(cambios = {}) {
  const { campos, textos } = unaCabecera();
  return unPapel({
    estado: "propuesta_revisada",
    etiqueta_estado: "Revisado, sin confirmar",
    lo_aceptado: { campos, textos },
    se_puede_confirmar: true,
    se_puede_descartar_la_propuesta: false,
    ...cambios,
  });
}

/** Lo que contesta `POST /api/bandeja/comprobar`: la huella, el tamaño y si ya estaba. */
function unComprobado(cambios = {}) {
  return {
    huella: "9f2c0a5b3e4d5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8",
    bytes: 20480,
    texto_tamano: "20,0 KB",
    nombre_del_fichero: "factura-gasoleo.pdf",
    tipo_del_fichero: "application/pdf",
    ya_estaba: false,
    donde: null,
    el_que_ya_estaba: null,
    que_hacer: "",
    ...cambios,
  };
}

/** Y el mismo, cuando el papel ya estaba: con el que ya había y con qué hacer. */
function unComprobadoQueYaEstaba(cambios = {}) {
  return unComprobado({
    ya_estaba: true,
    donde: "la_bandeja",
    el_que_ya_estaba: {
      id: 3,
      titulo: "La factura del abono de mayo",
      numero_factura: "",
      texto_subido: "03/10/2026",
    },
    que_hacer: "Este mismo papel ya lo tienes: «La factura del abono de mayo», del 03/10/2026.",
    ...cambios,
  });
}

/** Un formulario, tal y como lo monta `app.js` (la revisión de un papel). */
function unFormulario(cambios = {}) {
  return {
    titulo: "Decide qué queda",
    pista: "Corrige lo que haga falta y guarda.",
    guardar: "GUARDAR LO QUE QUEDA",
    cancelar: "DEJARLO",
    guardando: "Guardando…",
    datos: { clase: "revision", id: 5 },
    bloques: [
      { tipo: "texto", id: "bandeja-proveedor", etiqueta: "El proveedor", valor: "Ferretería del Páramo" },
      { tipo: "texto", id: "bandeja-numero", etiqueta: "El número de factura", valor: "2026/0042" },
      { tipo: "fecha", id: "bandeja-fecha", etiqueta: "La fecha", valor: "2026-10-01" },
      { tipo: "numero", id: "bandeja-total", etiqueta: "El total", valor: "980.10" },
    ],
    ...cambios,
  };
}

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

async function cargarLaPantallaModulo() {
  // El `?prueba=` con un número al azar es obligatorio: sin él, Node devuelve el módulo ya cargado por otra
  // prueba y la caché de módulos hace que las pruebas se pisen.
  return import(`../web/react/pantallas/bandeja.js?prueba=${Math.random()}`);
}

async function htmlDe(componente, propiedades) {
  const modulo = await cargarLaPantallaModulo();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(modulo[componente], propiedades),
  );
}

const htmlDeLaBandeja = (cambios = {}) =>
  htmlDe("PantallaDeLaBandeja", {
    textos: structuredClone(TEXTOS),
    papeles: [],
    tipos: structuredClone(TIPOS),
    estados: structuredClone(ESTADOS),
    clases: structuredClone(CLASES),
    resumen: "",
    cuantos: 0,
    sinDecirDeQueEs: 0,
    estadoElegido: "sin_revisar",
    tipoElegido: "",
    filtro: "",
    ficheroElegido: "",
    tipoNuevoElegido: "",
    comprobado: null,
    comprobando: false,
    subiendo: false,
    formulario: null,
    guardando: false,
    error: "",
    aviso: "",
    ...cambios,
  });

const htmlDeUnaFicha = (cambios = {}) =>
  htmlDe("PantallaDeUnPapelDeLaBandeja", {
    textos: structuredClone(TEXTOS),
    papel: unPapel(),
    tipos: structuredClone(TIPOS),
    candidatos: [],
    papelesParaRectificar: [],
    clases: structuredClone(CLASES),
    claseElegida: "gasto",
    claseBuscada: "",
    buscandoCandidatos: false,
    formulario: null,
    guardando: false,
    cargando: false,
    error: "",
    aviso: "",
    ...cambios,
  });

/** Los `data-accion` que salen pintados, en el orden en que salen. */
function accionesDe(html) {
  return [...html.matchAll(/data-accion="([a-z0-9_-]+)"/g)].map((encontrado) => encontrado[1]);
}

/** Los botones del HTML: su acción y todos sus `data-*`. */
function botonesDe(html) {
  return [...html.matchAll(/<button[^>]*>/g)].map((encontrado) => {
    const etiqueta = encontrado[0];
    const accion = (etiqueta.match(/data-accion="([^"]*)"/) || [])[1] || "";
    const datos = {};
    for (const dato of etiqueta.matchAll(/data-(?!accion)[a-z-]+="([^"]*)"/g)) {
      datos[dato[0].split("=")[0].replace("data-", "")] = dato[1];
    }
    return { accion, ...datos };
  });
}

/** Los `id` de los campos que salen pintados, en el orden en que salen. */
function idsDe(html) {
  return [...html.matchAll(/(?<![\w-])id="([^"]+)"/g)].map((encontrado) => encontrado[1]);
}

/**
 * Todos los textos de una estructura anidada, **incluidos los números**.
 *
 * Los números entran porque la pantalla enseña algunos tal cual llegan del servidor (cuántas líneas trae la
 * lectura, cuántos papeles hay): un número no es una frase escrita a mano, y sin esto la prueba de las
 * frases a mano los tomaría por frases inventadas.
 */
function todosLosTextos(valor) {
  if (typeof valor === "string") return [valor];
  if (typeof valor === "number") return [String(valor)];
  if (Array.isArray(valor)) return valor.flatMap(todosLosTextos);
  if (valor && typeof valor === "object") return Object.values(valor).flatMap(todosLosTextos);
  return [];
}

/** Lo que de verdad se lee: el texto que hay entre las etiquetas. */
function frasesVisibles(html) {
  return html
    .replace(/<span class="icono"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<span class="flecha"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<[^>]*>/g, "\u0000")
    .split("\u0000")
    .map((trozo) => trozo.trim())
    .filter(Boolean);
}

/** La pantalla sin sus comentarios, que es lo que se lee para buscar cosas prohibidas. */
function laPantallaSinComentarios() {
  return readFileSync(RUTA_DE_LA_PANTALLA, "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

// ===========================================================================
// 1. Subir: el original entra tal y como llega, y el duplicado se dice antes
// ===========================================================================

test("subir tiene su fichero y su tipo, y no hay forma de subir sin haber comprobado antes", async () => {
  // **La prueba que impide que el duplicado se cuele.** Al elegir el fichero todavía no hay nada
  // comprobado, así que el botón de subir **no puede estar**: si estuviera, el agricultor subiría el papel
  // sin que nadie le haya dicho que ese mismo papel ya lo tenía.
  const html = await htmlDeLaBandeja({ ficheroElegido: "factura-gasoleo.pdf" });

  for (const campo of ["bandeja-fichero", "bandeja-tipo-nuevo"]) {
    assert.ok(idsDe(html).includes(campo), `falta el campo «${campo}» de la subida`);
  }
  assert.match(html, /type="file"/, "no hay dónde elegir el fichero del papel");
  assert.match(html, /accept="\.pdf/, "el campo no admite un PDF");
  assert.match(html, /\.jpg/, "el campo no admite una foto");

  const acciones = accionesDe(html);
  assert.ok(acciones.includes("bandeja-comprobar"), "no hay forma de comprobar el fichero");
  assert.ok(!acciones.includes("bandeja-subir"), "se puede subir un papel sin haberlo comprobado antes");
  // Y se dice que subir no apunta nada al cuaderno, que es lo que hay que saber antes de empezar.
  assert.match(html, /Subir no apunta nada al cuaderno/);
});

test("cuando el papel ya estaba se dice, con cuál era, y no se ofrece subirlo", async () => {
  // **La prueba central del duplicado.** Se enseña la huella del fichero, se dice que ese mismo papel ya
  // está, se enseña **cuál** (con su nombre y el día en que se subió) y se dice qué hacer. Y el botón de
  // subir **desaparece**: las dos salidas que quedan son ver el que ya estaba o elegir otro fichero.
  const html = await htmlDeLaBandeja({
    ficheroElegido: "factura-gasoleo.pdf",
    comprobado: unComprobadoQueYaEstaba(),
  });

  assert.match(html, /Este mismo papel ya lo tienes/, "no se dice que el papel ya estaba");
  assert.match(html, /La factura del abono de mayo/, "no se enseña cuál era el que ya estaba");
  assert.match(html, /03\/10\/2026/, "no se dice de cuándo era el que ya estaba");
  assert.match(html, /20,0 KB/, "no se enseña lo que ocupa el fichero");
  assert.match(html, /9f2c0a5b/, "no se enseña la huella del fichero");

  const acciones = accionesDe(html);
  assert.ok(!acciones.includes("bandeja-subir"), "se puede subir un papel que ya estaba");
  assert.ok(acciones.includes("bandeja-abrir"), "no hay forma de ver el papel que ya estaba");
  assert.ok(acciones.includes("bandeja-olvidar-fichero"), "no hay forma de elegir otro fichero");

  const abrir = botonesDe(html).filter((boton) => boton.accion === "bandeja-abrir");
  assert.deepEqual(abrir.map((boton) => boton.id), ["3"], "el botón no dice qué papel abrir");
});

test("cuando no lo tenía, se dice y se puede subir", async () => {
  const html = await htmlDeLaBandeja({
    ficheroElegido: "factura-gasoleo.pdf",
    comprobado: unComprobado(),
  });
  assert.match(html, /Este papel no lo tenías/);
  assert.ok(accionesDe(html).includes("bandeja-subir"), "no hay forma de subir el papel");
  assert.ok(!accionesDe(html).includes("bandeja-abrir"), "se ofrece abrir un papel que no existe");
});

test("la lista enseña el estado, lo que es y qué hacer con cada papel", async () => {
  // Un papel sin revisar tiene que **parecer** un papel sin revisar, y la lista tiene que decir qué hacer
  // con él: sin eso, la bandeja es una lista de nombres sin salida.
  const html = await htmlDeLaBandeja({
    papeles: [
      unPapel({ id: 7, titulo: "El ticket del taller", estado: "recien_subido", etiqueta_estado: "Recién subido" }),
      unPapelRevisado({ id: 8, titulo: "factura-del-abono" }),
    ],
    resumen: "Tienes 2 papeles en la bandeja.",
    sinDecirDeQueEs: 1,
  });

  assert.match(html, /El ticket del taller/);
  assert.match(html, /Recién subido/, "no se dice cómo está el papel");
  assert.match(html, /Falta decir de qué es/, "no se dice qué hacer con un papel recién subido");
  assert.match(html, /Revisado, sin confirmar/);
  assert.match(html, /Ya has dicho qué queda/, "no se dice qué hacer con un papel ya revisado");
  assert.match(html, /Una factura/, "no se dice de qué es el papel");
  assert.match(html, /01\/10\/2026/, "no se enseña el día del papel");
  assert.match(html, /factura-gasoleo\.pdf/, "no se enseña el fichero que tiene");
  assert.match(html, /20,0 KB/, "no se dice lo que ocupa el original");
  assert.match(html, /Hay papeles a los que todavía no has dicho de qué son/);
  assert.match(html, /Tienes 2 papeles en la bandeja/);

  const abrir = botonesDe(html).filter((boton) => boton.accion === "bandeja-abrir");
  assert.deepEqual(abrir.map((boton) => boton.id).sort(), ["7", "8"], "los botones no dicen qué papel abrir");
});

test("sin papeles se dice qué hacer, y con un filtro que no encuentra nada también", async () => {
  const vacia = await htmlDeLaBandeja();
  assert.match(vacia, /La bandeja está vacía/);
  const conFiltro = await htmlDeLaBandeja({ filtro: "pepito" });
  assert.match(conFiltro, /Ningún papel coincide con lo que buscas/);
  assert.ok(accionesDe(conFiltro).includes("bandeja-ver-todas"), "no hay forma de quitar el filtro");
});

test("el buscador, el estado y el tipo llevan su campo con su id", async () => {
  const html = await htmlDeLaBandeja();
  for (const campo of ["bandeja-buscar", "bandeja-estado", "bandeja-tipo"]) {
    assert.ok(idsDe(html).includes(campo), `falta el campo «${campo}», y app.js lo busca`);
  }
  // El desplegable del estado lleva las palabras del servidor, y ninguna inventada aquí.
  for (const palabra of ["Sin revisar", "Recién subido", "Sin leer", "Revisado, sin confirmar", "Confirmado", "Todos"]) {
    assert.ok(html.includes(palabra), `no sale «${palabra}» en el desplegable del estado`);
  }
  // Y el del tipo, con el nuevo («Un certificado de inspección»), que es lo que el T14 dejó pendiente.
  assert.ok(html.includes("Un certificado de inspección"), "no sale el tipo del certificado de inspección");
});

// ===========================================================================
// 2. El original siempre a la vista, y sin poder tocarlo
// ===========================================================================

test("la ficha enseña el original y no hay ningún campo para cambiarlo", async () => {
  // **La primera regla del ticket, comprobada en la pantalla.** El nombre del fichero, su tamaño y su
  // huella se enseñan; y **no existe ningún campo** para ninguno de los tres. Lo único que se puede hacer
  // con el original es verlo.
  const html = await htmlDeUnaFicha();

  assert.match(html, /factura-gasoleo\.pdf/, "no se enseña el nombre del fichero");
  assert.match(html, /20,0 KB/, "no se enseña lo que ocupa");
  assert.match(html, /9f2c0a5b/, "no se enseña la huella");
  assert.match(html, /El programa no lo cambia nunca/, "no se dice que el original no se toca");
  assert.ok(accionesDe(html).includes("bandeja-original"), "no hay forma de ver el original");

  const ids = idsDe(html);
  for (const prohibido of ["bandeja-huella", "bandeja-fichero-nombre", "bandeja-fichero-ruta", "bandeja-fichero-bytes"]) {
    assert.ok(!ids.includes(prohibido), `hay un campo para «${prohibido}»: el original se podría reescribir`);
  }
  // Y el nombre del fichero y la huella no salen dentro de ningún `input`.
  assert.doesNotMatch(html, /<input[^>]*value="[^"]*9f2c0a5b/, "la huella está en un campo editable");
});

test("un papel sin fichero lo dice, en vez de enseñar un hueco sin explicación", async () => {
  const html = await htmlDeUnaFicha({
    papel: unPapel({ tiene_fichero: false, nombre_del_fichero: null, texto_tamano: "", huella: null }),
  });
  assert.match(html, /Este papel está apuntado sin su fichero/);
  assert.ok(!accionesDe(html).includes("bandeja-original"), "se ofrece ver un fichero que no está");
});

// ===========================================================================
// 3. Ni un porcentaje, ni una palabra sobre lo buena que es la lectura
// ===========================================================================

test("la pantalla no dice que la lectura esté bien, y dice que no se puede medir", async () => {
  // **La prueba que muerde.** El corpus para medir la lectura (T07) no existe, así que la pantalla no puede
  // dar un porcentaje ni decir que ha leído algo correctamente. Se pinta una propuesta entera (con sus
  // líneas, sus cuentas y sus avisos) y se mira el HTML entero.
  const html = await htmlDeUnaFicha({
    papel: unPapel({
      la_propuesta: unaPropuesta({
        avisos: ["En 2 líneas la cuenta de cantidad × precio no da el importe."],
        lineas: [unaLinea(), unaLinea({ descripcion: "Filtro de aceite", la_cuenta_cuadra: false, texto_importe: "18,00 €" })],
        lineas_leidas: 2,
        lineas_que_cuadran: 1,
      }),
    }),
  });

  assert.match(html, /El programa no dice si esta lectura está bien/, "no se dice que no se puede medir");
  assert.doesNotMatch(html, /%/, "la pantalla da un porcentaje de la lectura");
  for (const prohibida of ["confianza", "leído correctamente", "leida correctamente", "precisión", "acierto", "fiabilidad"]) {
    assert.ok(!html.toLowerCase().includes(prohibida), `la pantalla dice «${prohibida}» de la lectura`);
  }
  // Y lo que sí se dice es un hecho comprobable: si la cuenta de cada línea cuadra.
  assert.match(html, /La cuenta cuadra/);
  assert.match(html, /La cuenta no cuadra/);
  assert.match(html, /En 2 líneas la cuenta de cantidad × precio no da el importe/);
  assert.match(html, /Líneas leídas/);
});

test("la lectura no es un dato: se dice, y las líneas que no se han leído se dicen también", async () => {
  const html = await htmlDeUnaFicha();
  assert.match(html, /Esto es una propuesta, no un dato/, "no se dice que la lectura es una propuesta");
  // Y de un papel que no se sabe leer se dice, con la puerta de escribirlo a mano al lado.
  const sinLector = await htmlDeUnaFicha({
    papel: unPapel({
      tipo: "contrato",
      etiqueta_tipo: "Un contrato",
      se_puede_leer: false,
      la_propuesta: null,
    }),
  });
  assert.match(sinLector, /De este tipo de papel todavía no sé leer nada/);
  assert.match(sinLector, /De este papel no hay ninguna lectura/);
  assert.ok(!accionesDe(sinLector).includes("bandeja-leer"), "se ofrece leer un papel que no se sabe leer");
});

// ===========================================================================
// 4. Un importe que no consta es un hueco, y nunca un cero
// ===========================================================================

test("un importe que no consta se enseña como hueco: ni un cero, ni un total inventado", async () => {
  // **Esta prueba muerde a propósito.** A la propuesta se le pasa un `textos.total` de `0,00 €` **con el
  // dato a nulo**: si la pantalla se fiara del texto en vez de mirar el dato, enseñaría un cero y el
  // agricultor leería que el papel pone cero euros. Lo que tiene que salir es su palabra, y el cero no
  // puede aparecer por ningún lado.
  const html = await htmlDeUnaFicha({
    papel: unPapel({
      la_propuesta: unaPropuesta({
        campos: { total: null, base_imponible: null, cuota_iva: null, tipo_iva_pct: null },
        textos: { total: "0,00 €", base_imponible: "0,00 €", cuota_iva: "0,00 €", tipo_iva_pct: "0,00 €" },
        lineas: [unaLinea({ importe: null, texto_importe: "0,00 €", precio_unitario: null, texto_precio_unitario: "" })],
      }),
    }),
  });

  assert.match(html, /No consta/, "no se dice que el importe no consta");
  assert.doesNotMatch(html, /0,00 €/, "la pantalla ha enseñado un cero donde el importe no consta");
  assert.doesNotMatch(html, /0,00/, "la pantalla ha enseñado un cero donde el importe no consta");
  // Y lo que sí se sabe de esa línea se sigue enseñando.
  assert.match(html, /Gasóleo agrícola/);
});

// ===========================================================================
// 5. Confirmar: solo cuando hay algo aceptado, y con lo aceptado a la vista
// ===========================================================================

test("no se puede confirmar sin haber revisado, y se dice qué hacer antes", async () => {
  // **La segunda regla del ticket.** Sin nada aceptado, el botón de confirmar **no existe**, y en su sitio
  // está la frase que dice qué hacer. El servidor también lo impide (contesta 409), y esto es la mitad de
  // la pantalla: que no se pueda ni intentar.
  const sinRevisar = await htmlDeUnaFicha({ papel: unPapel({ se_puede_confirmar: false }) });
  assert.ok(!accionesDe(sinRevisar).includes("bandeja-confirmar"), "se puede confirmar sin haber revisado");
  assert.match(sinRevisar, /Todavía no has dicho qué queda de este papel/);
  assert.match(sinRevisar, /Antes de confirmar hay que decir qué queda/);
  assert.ok(accionesDe(sinRevisar).includes("bandeja-revisar"), "no hay forma de revisar el papel");
});

test("con lo aceptado delante, se puede confirmar y se dice que el fichero no se toca", async () => {
  const html = await htmlDeUnaFicha({ papel: unPapelRevisado() });
  assert.ok(accionesDe(html).includes("bandeja-confirmar"), "no hay forma de confirmar un papel revisado");
  assert.match(html, /Esto es lo que queda de este papel/);
  assert.match(html, /Ferretería del Páramo/, "no se enseña lo aceptado");
  assert.match(html, /980,10 €/, "no se enseña el importe aceptado");
  assert.match(html, /El fichero no se toca/, "no se dice que confirmar no toca el original");
  // Y el botón dice sobre qué papel actúa.
  const confirmar = botonesDe(html).filter((boton) => boton.accion === "bandeja-confirmar");
  assert.deepEqual(confirmar.map((boton) => boton.id), ["5"]);
});

test("un papel confirmado dice que ya está en los papeles, con quién y cuándo", async () => {
  const html = await htmlDeUnaFicha({
    papel: unPapelRevisado({
      estado: "confirmado",
      etiqueta_estado: "Confirmado",
      sin_revisar: false,
      confirmado_por: "David",
      texto_confirmado_en: "06/10/2026",
    }),
  });
  assert.match(html, /Este papel ya está confirmado y se ve en LOS PAPELES/);
  assert.match(html, /David/, "no se dice quién lo confirmó");
  assert.match(html, /06\/10\/2026/, "no se dice cuándo lo confirmó");
});

test("descartar la lectura pide el motivo y no borra lo leído", async () => {
  const html = await htmlDeUnaFicha({ papel: unPapel({ se_puede_descartar_la_propuesta: true }) });
  assert.ok(idsDe(html).includes("bandeja-motivo-descartar"), "no hay dónde decir por qué no sirve");
  assert.ok(accionesDe(html).includes("bandeja-descartar"), "no hay forma de descartar la lectura");
  // Y cuando ya hay algo aceptado, descartar no se ofrece: lo que se hace es revisar otra vez.
  const yaRevisado = await htmlDeUnaFicha({ papel: unPapelRevisado() });
  assert.ok(!accionesDe(yaRevisado).includes("bandeja-descartar"), "se puede descartar una lectura ya aceptada");
  // La lectura descartada sigue a la vista, con su aviso.
  const descartada = await htmlDeUnaFicha({ papel: unPapel({ propuesta_descartada: true }) });
  assert.match(descartada, /Esta lectura la descartaste/);
});

test("el formulario de revisar sale con sus campos y dice qué se está guardando", async () => {
  const html = await htmlDeUnaFicha({ formulario: unFormulario(), guardando: true });
  assert.match(html, /Decide qué queda/);
  for (const campo of ["bandeja-proveedor", "bandeja-numero", "bandeja-fecha", "bandeja-total"]) {
    assert.ok(idsDe(html).includes(campo), `falta el campo «${campo}» del formulario, y app.js lo lee`);
  }
  const guardar = botonesDe(html).filter((boton) => boton.accion === "bandeja-guardar");
  assert.deepEqual(guardar.map((boton) => boton.clase), ["revision"]);
  assert.deepEqual(guardar.map((boton) => boton.id), ["5"]);
  // Y el formulario es el de la ficha: el que se guarda es **ese** papel.
  assert.ok(idsDe(html).includes("bandeja-tipo-del-papel"), "no se puede decir de qué es el papel");
});

test("un papel recién subido se puede clasificar desde su ficha", async () => {
  // Sin esto, el aviso «falta decir de qué es» sería una instrucción que no se puede seguir.
  const html = await htmlDeUnaFicha({
    papel: unPapel({ estado: "recien_subido", etiqueta_estado: "Recién subido", tipo: "otros" }),
  });
  assert.ok(idsDe(html).includes("bandeja-tipo-del-papel"), "no hay dónde decir de qué es el papel");
  const clasificar = botonesDe(html).filter((boton) => boton.accion === "bandeja-clasificar");
  assert.deepEqual(clasificar.map((boton) => boton.id), ["5"], "el botón no dice qué papel se clasifica");
});

// ===========================================================================
// 6. Enlazar: no crea nada, se puede quitar, y las rectificativas dejan las dos
// ===========================================================================

test("enlazar dice que no crea nada y no ofrece crear nada", async () => {
  // La regla «un pago conciliado no crea un segundo gasto», por el lado de los papeles.
  const html = await htmlDeUnaFicha({
    candidatos: [{ valor: "gasto:12", texto: "Un gasto · Gasóleo · 01/10/2026" }],
  });
  assert.match(html, /Enlazar no crea nada/, "no se dice que enlazar no crea nada");
  assert.ok(idsDe(html).includes("bandeja-clase"), "no se puede elegir con qué clase enlazarlo");
  assert.ok(idsDe(html).includes("bandeja-candidato"), "no se puede elegir con qué enlazarlo");
  assert.ok(accionesDe(html).includes("bandeja-enlazar"), "no hay forma de enlazar");
  assert.match(html, /Gasóleo · 01\/10\/2026/, "los candidatos no llegan a la pantalla");
  // **Y el botón tiene que decir QUÉ papel enlaza.** Se encontró pulsando: el botón se pintaba sin su
  // `data-id`, así que `app.js` recibía un cero, se salía por su comprobación de siempre (`if (!id)`) y
  // **no pasaba nada**: ni enlace, ni aviso, ni error. Un botón que se pulsa y no hace nada es peor que
  // uno que no está. Los demás botones de la ficha ya llevaban su identificador; este se quedó sin él.
  const enlazar = botonesDe(html).filter((boton) => boton.accion === "bandeja-enlazar");
  assert.deepEqual(
    enlazar.map((boton) => boton.id),
    ["5"],
    "el botón de enlazar no dice qué papel se está enlazando",
  );
  // El valor de la opción lleva la clase y el identificador (`gasto:12`), que es lo que `app.js` parte
  // para mandar el enlace: la pantalla no lo toca, pero tiene que llegar tal cual.
  assert.match(html, /value="gasto:12"/, "el candidato no lleva su clase en el valor");

  // Y las seis clases, con sus palabras del servidor.
  for (const palabra of ["Un gasto", "Una venta de tu cosecha", "Una máquina", "Un trabajo hecho", "Una inspección de una máquina"]) {
    assert.ok(html.includes(palabra), `no sale la clase «${palabra}»`);
  }
  // Lo que **no** puede haber: ninguna acción que prometa crear algo.
  for (const accion of accionesDe(html)) {
    assert.doesNotMatch(accion, /crear|nuevo|nueva/, `la ficha ofrece «${accion}»: enlazar no crea nada`);
  }
});

test("todos los botones de la ficha dicen sobre qué papel actúan", async () => {
  // **El guardián que faltaba.** El manejador de clics de `app.js` empieza por `const id =
  // Number(elemento.dataset.id || 0)` y, si no hay identificador, se sale sin hacer nada: ni guarda, ni
  // avisa, ni falla. Así que un botón pintado sin su `data-id` es un botón muerto que **no se nota**:
  // pasó con el de enlazar, que se quedó sin él mientras todos los demás lo llevaban, y solo se descubrió
  // pulsándolo en un navegador de verdad. Esta prueba recorre **todas** las acciones que necesitan el
  // papel y comprueba que lo llevan, para que el siguiente que se olvide no llegue a producción.
  const necesitan_el_papel = [
    "bandeja-original",
    "bandeja-leer",
    "bandeja-confirmar",
    "bandeja-clasificar",
    "bandeja-revisar",
    "bandeja-descartar",
    "bandeja-enlazar",
    "bandeja-rectificar",
  ];
  const html = await htmlDeUnaFicha({
    // Con candidatos y con un papel que se puede corregir, para que **todos** esos botones se pinten: si
    // no, la prueba pasaría por no haber mirado nada.
    candidatos: [{ valor: "gasto:12", texto: "Un gasto · Gasóleo · 01/10/2026" }],
    papelesParaRectificar: [{ valor: 3, texto: "La factura del abono de mayo" }],
  });
  const pintados = botonesDe(html).filter((boton) => necesitan_el_papel.includes(boton.accion));
  assert.ok(
    pintados.length >= 6,
    `solo se han pintado ${pintados.length} de esos botones: la prueba no está mirando lo que cree`,
  );
  for (const boton of pintados) {
    assert.equal(
      boton.id,
      "5",
      `el botón «${boton.accion}» no dice sobre qué papel actúa: pulsarlo no haría nada`,
    );
  }
});

test("sin candidatos se dice qué hacer, y no se enseña un desplegable vacío", async () => {
  const html = await htmlDeUnaFicha({ candidatos: [] });
  assert.match(html, /No hay nada de eso en tu cuaderno/);
  assert.ok(!idsDe(html).includes("bandeja-candidato"), "se ofrece elegir cuando no hay nada que elegir");
  assert.ok(!accionesDe(html).includes("bandeja-enlazar"), "se puede enlazar sin nada que enlazar");
  assert.ok(accionesDe(html).includes("bandeja-buscar-candidatos"), "no hay forma de volver a buscar");
});

test("lo enlazado se enseña con su nombre y se puede quitar de ahí", async () => {
  const html = await htmlDeUnaFicha({
    papel: unPapel({
      vinculos: [
        { id: 1, clase: "gasto", etiqueta_clase: "Un gasto", entidad_id: 12, que_es: "Un gasto · Gasóleo · 01/10/2026", creado_en: "2026-10-06T09:00:00" },
        { id: 2, clase: "maquina", etiqueta_clase: "Una máquina", entidad_id: 4, que_es: "Una máquina · El tractor", creado_en: "2026-10-06T09:00:00" },
      ],
    }),
  });
  assert.match(html, /Un gasto · Gasóleo/);
  assert.match(html, /Una máquina · El tractor/);
  const quitar = botonesDe(html).filter((boton) => boton.accion === "bandeja-desenlazar");
  assert.deepEqual(quitar.map((boton) => boton.clase), ["gasto", "maquina"], "el botón no dice qué enlace quita");
  assert.deepEqual(quitar.map((boton) => boton.entidad), ["12", "4"]);
  // Y sin nada enlazado, se dice, y no se ofrece quitar nada.
  const sinNada = await htmlDeUnaFicha();
  assert.match(sinNada, /Sin enlazar con nada/);
  assert.ok(!accionesDe(sinNada).includes("bandeja-desenlazar"), "se ofrece quitar un enlace que no hay");
});

test("las rectificativas: se dice a quién corrige este y quién lo ha corregido, y las dos quedan", async () => {
  const html = await htmlDeUnaFicha({
    papel: unPapel({
      rectifica_a: { id: 2, titulo: "La factura de septiembre" },
      rectificada_por: [{ id: 9, titulo: "La factura corregida de octubre" }],
    }),
    papelesParaRectificar: [{ valor: 3, texto: "La factura del abono de mayo" }],
  });
  assert.match(html, /Corrige a/);
  assert.match(html, /La factura de septiembre/);
  assert.match(html, /Este papel está corregido por/);
  assert.match(html, /La factura corregida de octubre/);
  assert.match(html, /Las dos quedan/, "no se dice que la corregida sigue ahí");
  assert.ok(idsDe(html).includes("bandeja-rectifica-a"), "no se puede elegir a qué papel corrige");
  assert.ok(accionesDe(html).includes("bandeja-rectificar"), "no hay forma de decir que corrige a otro");

  const rectificar = botonesDe(html).filter((boton) => boton.accion === "bandeja-rectificar");
  assert.deepEqual(rectificar.map((boton) => boton.id), ["5"], "el botón no dice qué papel corrige");
});

// ===========================================================================
// 7. Las acciones: la lista entera, y ninguna de más
// ===========================================================================

test("las acciones que pinta la pantalla son las del informe, y ninguna más", async () => {
  // **Esta prueba fija la lista.** El manejador de clics de `app.js` es uno solo: una acción que se pinte y
  // nadie atienda es un botón que se pulsa y no hace nada. La lista con lo que hace cada una está en
  // `docs/T08_BANDEJA.md`, y si alguien inventa una acción nueva, aquí se ve.
  const esperadas = new Set([
    "bandeja-comprobar",
    "bandeja-subir",
    "bandeja-olvidar-fichero",
    "bandeja-abrir",
    "bandeja-filtrar",
    "bandeja-ver-todas",
    "bandeja-ver",
    "bandeja-clasificar",
    "bandeja-leer",
    "bandeja-revisar",
    "bandeja-guardar",
    "bandeja-cancelar",
    "bandeja-confirmar",
    "bandeja-descartar",
    "bandeja-buscar-candidatos",
    "bandeja-enlazar",
    "bandeja-desenlazar",
    "bandeja-rectificar",
    "bandeja-original",
    "papel-ver-todos",
    "ir-inicio",
  ]);

  const vistas = new Set();
  // Todas las ramas que pueden pintar un botón: la lista llena, la vacía, con un filtro que no encuentra
  // nada, con el fichero elegido, con el duplicado, con lo comprobado, con el formulario abierto, y la
  // ficha en sus cuatro estados y con todas sus partes.
  const ramas = [
    await htmlDeLaBandeja(),
    await htmlDeLaBandeja({ filtro: "pepito" }),
    await htmlDeLaBandeja({ papeles: [unPapel()], sinDecirDeQueEs: 1 }),
    await htmlDeLaBandeja({ ficheroElegido: "factura.pdf", comprobando: true }),
    await htmlDeLaBandeja({ ficheroElegido: "factura.pdf", comprobado: unComprobado(), subiendo: true }),
    await htmlDeLaBandeja({ ficheroElegido: "factura.pdf", comprobado: unComprobadoQueYaEstaba() }),
    await htmlDeLaBandeja({ formulario: unFormulario(), guardando: true }),
    await htmlDeUnaFicha(),
    await htmlDeUnaFicha({ papel: unPapel({ estado: "recien_subido", etiqueta_estado: "Recién subido" }) }),
    await htmlDeUnaFicha({ papel: unPapelRevisado() }),
    await htmlDeUnaFicha({ papel: unPapel({ tiene_fichero: false, nombre_del_fichero: null, huella: null }) }),
    await htmlDeUnaFicha({
      papel: unPapel({
        vinculos: [{ id: 1, clase: "gasto", entidad_id: 12, que_es: "Un gasto · Gasóleo", creado_en: "2026-10-06T09:00:00" }],
      }),
      candidatos: [{ valor: 12, texto: "Un gasto · Gasóleo" }],
      papelesParaRectificar: [{ valor: 3, texto: "La factura del abono" }],
      buscandoCandidatos: true,
    }),
    await htmlDeUnaFicha({ formulario: unFormulario() }),
  ];
  for (const html of ramas) for (const accion of accionesDe(html)) vistas.add(accion);

  const de_mas = [...vistas].filter((accion) => !esperadas.has(accion));
  const de_menos = [...esperadas].filter((accion) => !vistas.has(accion));
  assert.deepEqual(de_mas, [], "hay acciones que nadie ha decidido y que el manejador de clics no atiende");
  assert.deepEqual(de_menos, [], "hay acciones del informe que la pantalla no pinta");
});

test("ninguna acción va puesta por variable, para que el guardián pueda leerlas", async () => {
  // `tests/test_los_botones_hacen_algo.py` lee las acciones del código: una puesta por variable **no se
  // puede leer**, y un botón que no hiciera nada pasaría desapercibido. Esta pantalla es nueva, así que no
  // está en la lista de los ficheros que sí pueden hacerlo.
  //
  // Se quitan los comentarios antes de mirar, y no es un detalle: el comentario de cabecera de este fichero
  // **nombra la forma prohibida** para explicarla, y sin quitarlo la prueba se pondría roja por el texto
  // que la documenta.
  const fuente = laPantallaSinComentarios();
  const dinamicas = [...fuente.matchAll(/data-accion=\$\{/g), ...fuente.matchAll(/\baccion=\$\{/g)];
  assert.deepEqual(dinamicas, [], "hay acciones puestas por variable en la bandeja");
  assert.ok(fuente.includes('accion="bandeja-subir"'), "el quitador se ha comido el fichero");
});

// ===========================================================================
// 8. Ni una frase escrita a mano, y ninguna clave en blanco
// ===========================================================================

/**
 * Un vocabulario de mentira que **apunta qué claves se leen**.
 *
 * Es la forma de comprobar dos cosas de una vez, y las dos son el mismo defecto: una clave que la pantalla
 * lee y no está en los textos **sale en blanco en la pantalla** (y no revienta nada, así que ninguna prueba
 * se entera), y una frase que está y no la lee nadie es una frase que se queda vieja.
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

test("la pantalla no lee ninguna frase que no esté en los textos, y no le sobra ninguna", async () => {
  const usadas = new Set();
  const textos = { bandeja: vocabularioQueApuntaLasClaves(usadas), acciones: vocabularioQueApuntaLasClaves(new Set()) };

  // Se recorren **todas** las ramas de las dos pantallas. Si una clave solo se lee en una de esas ramas y
  // nadie la recorre, esta prueba no la vería: por eso están todas, incluidas las que parecen raras (un
  // papel sin fichero, una lectura descartada, un duplicado, un candidato de cada clase).
  await htmlDeLaBandeja({ textos });
  await htmlDeLaBandeja({ textos, filtro: "x", estadoElegido: "confirmado", tipoElegido: "factura", resumen: "Tienes 2" });
  await htmlDeLaBandeja({ textos, papeles: [unPapel()], sinDecirDeQueEs: 1 });
  await htmlDeLaBandeja({
    textos,
    // Un papel sin fichero, otro al que todavía no se ha leído nada y otro con algo enlazado: son las tres
    // ramas de la lista que, sin pasar por aquí, dejarían tres frases sin leer y la prueba no las vería.
    papeles: [
      unPapel({ id: 6, tiene_fichero: false, nombre_del_fichero: null, texto_tamano: "", la_propuesta: null }),
      unPapel({
        id: 7,
        vinculos: [{ id: 1, clase: "gasto", entidad_id: 12, que_es: "Un gasto · Gasóleo", creado_en: "x" }],
      }),
    ],
  });
  await htmlDeLaBandeja({ textos, ficheroElegido: "factura.pdf", comprobando: true });
  await htmlDeLaBandeja({ textos, ficheroElegido: "factura.pdf", comprobado: unComprobado(), subiendo: true });
  await htmlDeLaBandeja({ textos, ficheroElegido: "factura.pdf", comprobado: unComprobado(), subiendo: false });
  await htmlDeLaBandeja({ textos, ficheroElegido: "factura.pdf", comprobado: unComprobadoQueYaEstaba() });
  await htmlDeLaBandeja({ textos, formulario: unFormulario() });
  await htmlDeLaBandeja({ textos, formulario: unFormulario({ error: "Algo ha fallado" }) });
  await htmlDeLaBandeja({ textos, error: "Algo ha fallado", aviso: "Un aviso" });
  await htmlDeLaBandeja({ textos, papeles: [unPapel({ rectificada_por: [{ id: 9, titulo: "Otra" }] })] });

  await htmlDeUnaFicha({ textos });
  await htmlDeUnaFicha({ textos, papel: unPapelRevisado() });
  await htmlDeUnaFicha({ textos, papel: unPapelRevisado(), guardando: true });
  await htmlDeUnaFicha({
    textos,
    papel: unPapel({
      estado: "recien_subido",
      etiqueta_estado: "Recién subido",
    }),
  });
  await htmlDeUnaFicha({
    textos,
    papel: unPapel({
      estado: "confirmado",
      etiqueta_estado: "Confirmado",
      confirmado_por: "David",
      texto_confirmado_en: "06/10/2026",
    }),
  });
  await htmlDeUnaFicha({
    textos,
    papel: unPapel({
      propuesta_descartada: true,
      la_propuesta: unaPropuesta({
        avisos: ["Un aviso"],
        lineas: [unaLinea({ la_cuenta_cuadra: false })],
        // Y con las dos cuentas sin cuadrar, que es lo que hace que se lean las dos respuestas («No»), y no
        // solo la buena. Sin esta rama, la frase del «No» no la leería nadie y esta prueba lo diría.
        cuadra_el_total: false,
        suman_las_lineas: false,
      }),
    }),
  });
  await htmlDeUnaFicha({
    textos,
    papel: unPapel({ la_propuesta: unaPropuesta({ lineas: [], lineas_leidas: 0, lineas_que_cuadran: 0 }) }),
  });
  await htmlDeUnaFicha({
    textos,
    papel: unPapel({ tipo: "contrato", se_puede_leer: false, la_propuesta: null }),
  });
  await htmlDeUnaFicha({
    textos,
    papel: unPapel({ tiene_fichero: false, nombre_del_fichero: null, huella: null, texto_tamano: "" }),
  });
  await htmlDeUnaFicha({
    textos,
    papel: unPapel({
      rectifica_a: { id: 2, titulo: "La de septiembre" },
      rectificada_por: [{ id: 9, titulo: "La corregida" }],
      vinculos: [{ id: 1, clase: "gasto", entidad_id: 12, que_es: "Un gasto · Gasóleo", creado_en: "x" }],
    }),
    candidatos: [{ valor: 12, texto: "Un gasto · Gasóleo" }],
    papelesParaRectificar: [{ valor: 3, texto: "La factura del abono" }],
    buscandoCandidatos: true,
    guardando: true,
    cargando: true,
    error: "Algo ha fallado",
    aviso: "Un aviso",
  });
  await htmlDeUnaFicha({ textos, papel: unPapel({ se_puede_descartar_la_propuesta: false }), papelesParaRectificar: [] });
  await htmlDeUnaFicha({ textos, formulario: unFormulario() });

  const sin_frase = [...usadas].filter((clave) => !(clave in BANDEJA) && clave !== "volver");
  assert.deepEqual(
    sin_frase.sort(),
    [],
    "estas claves las lee la pantalla y no están en la copia de los textos: saldrían en blanco",
  );
  const sin_usar = Object.keys(BANDEJA).filter((clave) => !usadas.has(clave));
  assert.deepEqual(sin_usar.sort(), [], "estas frases están escritas y no las lee nadie");
});

test("cada clave de la copia está en el bloque que se integra en textos.py", async () => {
  // **La prueba que ata la copia al informe.** Estas pruebas usan su propia copia de los textos; el bloque
  // que de verdad se integra en `app/textos.py` está en `docs/T08_BANDEJA.md`. Si la copia tuviera una clave
  // que no está allí, la prueba de arriba pasaría y **en la pantalla de verdad esa frase saldría en blanco**.
  const informe = readFileSync(RUTA_DEL_INFORME, "utf8");
  const faltan = Object.keys(BANDEJA).filter((clave) => !informe.includes(`"${clave}":`));
  assert.deepEqual(faltan.sort(), [], "estas claves no están en el bloque de textos del informe");
});

test("la lista no lleva ni una frase escrita a mano", async () => {
  // Todo lo que se lee tiene que ser un texto del servidor o un dato que viene en las propiedades. Se
  // incluyen **los datos** en la lista de lo permitido porque la pantalla enseña frases que vienen del
  // servidor (el aviso del duplicado, el nombre de lo enlazado, el estado de un papel): lo que esta prueba
  // caza es una frase **escrita dentro del componente**.
  const props = {
    papeles: [unPapel(), unPapelRevisado({ id: 8 })],
    comprobado: unComprobadoQueYaEstaba(),
    formulario: unFormulario(),
    resumen: "Tienes 2 papeles en la bandeja.",
    sinDecirDeQueEs: 1,
    ficheroElegido: "factura-gasoleo.pdf",
  };
  const html = await htmlDeLaBandeja(props);
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS),
    ...todosLosTextos(TIPOS),
    ...todosLosTextos(ESTADOS),
    ...todosLosTextos(props),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

test("la ficha no lleva ni una frase escrita a mano", async () => {
  const props = {
    papel: unPapelRevisado({
      rectifica_a: { id: 2, titulo: "La factura de septiembre" },
      rectificada_por: [{ id: 9, titulo: "La corregida" }],
      vinculos: [{ id: 1, clase: "gasto", entidad_id: 12, que_es: "Un gasto · Gasóleo", creado_en: "x" }],
    }),
    candidatos: [{ valor: 12, texto: "Un gasto · Gasóleo" }],
    papelesParaRectificar: [{ valor: 3, texto: "La factura del abono" }],
    formulario: unFormulario(),
    aviso: "Un aviso",
  };
  const html = await htmlDeUnaFicha(props);
  const delServidor = new Set([
    ...todosLosTextos(TEXTOS),
    ...todosLosTextos(TIPOS),
    ...todosLosTextos(CLASES),
    ...todosLosTextos(props),
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

test("ninguna frase de la copia lleva jerga", async () => {
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
  for (const [clave, frase] of Object.entries(BANDEJA)) {
    for (const prohibida of prohibidas) {
      assert.ok(!frase.toLowerCase().includes(prohibida), `«${clave}» lleva «${prohibida}»`);
    }
  }
});

// ===========================================================================
// 9. La pantalla es pura, y ningún fallo deja al agricultor sin salida
// ===========================================================================

test("la pantalla no toca el navegador y no hace cuentas con el dinero", async () => {
  // El componente es **puro**: recibe propiedades y devuelve un elemento. Si tocara el navegador no se
  // podría probar sin uno; y si sumara o formateara importes, el total de la pantalla y el del servidor
  // dejarían de coincidir por céntimos, que es justo lo que este proyecto no puede permitirse.
  const codigo = laPantallaSinComentarios();
  for (const prohibida of ["fetch(", "localStorage", "sessionStorage", "document.", "window."]) {
    assert.ok(!codigo.includes(prohibida), `bandeja.js usa «${prohibida}»`);
  }
  for (const prohibido of ["parseFloat", "parseInt", "toFixed", "Number(", "Math."]) {
    assert.ok(!codigo.includes(prohibido), `la pantalla usa «${prohibido}» para hacer cuentas`);
  }
  assert.ok(!/\+\s*[a-zA-Z_$][\w.$]*\.(importe|total)/.test(codigo), "la pantalla suma importes");
  assert.ok(codigo.includes("export function PantallaDeLaBandeja"), "el quitador se ha comido el fichero");
  assert.ok(codigo.includes("export function pantallaDeUnPapelDeLaBandeja"), "falta el elemento montado de la ficha");
});

test("un fallo del servidor se enseña con su motivo, y no deja la pantalla en blanco", async () => {
  const html = await htmlDeUnaFicha({ error: "El fichero de ese papel ya no está. Vuelve a subirlo." });
  assert.match(html, /El fichero de ese papel ya no está/, "el motivo del servidor no llega al agricultor");
  assert.match(html, /role="alert"/, "el aviso no se anuncia solo");
  // Y la pantalla sigue estando: se puede volver a intentarlo.
  assert.ok(accionesDe(html).includes("bandeja-revisar"), "un fallo deja al agricultor sin poder reintentar");
});
