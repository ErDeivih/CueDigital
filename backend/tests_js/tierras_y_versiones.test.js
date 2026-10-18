/**
 * T06 — Las tierras en el mapa y en la tabla, y lo que ha sido una tierra (03/10/2026).
 *
 * **Qué comprueba este fichero.** Las seis cosas que el encargo pide probar, más las que salieron al
 * escribirlas:
 *
 *  1. **La búsqueda y los filtros** de la tabla: por nombre **y por referencia del SIGPAC**, y por lo
 *     sembrado, el pueblo, la revisión y lo que se puede declarar.
 *  2. **El grupo «sin forma»**: una tierra a la que no le ha llegado el polígono sigue en la lista,
 *     dentro de su grupo, y no se le dibuja un cuadro. Y **fuera** del grupo tampoco desaparece: lleva
 *     su etiqueta en la columna de la forma.
 *  3. **La selección múltiple**: se marcan varias, el recuento lo dice, y hay botón de marcarlas
 *     todas las que se ven.
 *  4. **El vínculo fila ↔ polígono**: la tierra enfocada enciende su fila **y** su trozo, y tocar
 *     cualquier trozo lleva la misma acción con **su** identificador (así que enfoca su fila).
 *  5. **Que la previsualización no escribe**: el lote que se ensaya se arma sin inventar un solo
 *     número, el ensayo solo puede acabar en la ruta que lee, y la pantalla lo dice con sus palabras.
 *  6. **Los cuatro estados de la comparación**: `igual`, `cambiado`, `desaparecido` y `nuevo`, cada uno
 *     con su palabra del servidor.
 *
 * Sin navegador, con el mismo arnés que `react.test.js`: los ficheros de `vendor/` se cargan con
 * `vm.runInThisContext` y el componente se dibuja con `renderToStaticMarkup`. **No hay `jsdom` ni
 * ninguna dependencia nueva.**
 *
 * Los textos son los de `textos.py`, copiados uno a uno como en los demás ficheros de pruebas: si se
 * inventaran aquí, esto comprobaría una pantalla que el agricultor no tiene.
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
// Los textos, tal y como los sirve el servidor
// ---------------------------------------------------------------------------

/** `textos.TIERRA_Y_MAPA`, que viaja en `/api/parcelas/vista`. */
const TEXTOS = {
  titulo: "Mis tierras, en el mapa y en la tabla",
  explica:
    "Aquí están todas tus tierras a la vez. En la lista ves sus hectáreas, su pueblo y lo que tienen sembrado este año; en el mapa, su forma.",
  buscar: "Buscar por su nombre o por su referencia del SIGPAC",
  buscar_boton: "BUSCAR",
  filtros_titulo: "Filtros",
  filtro_cultivo: "Qué tienen sembrado",
  filtro_municipio: "El pueblo",
  filtro_revision: "Si lo has revisado",
  filtro_pac: "Lo que puedes declarar",
  filtro_todas: "TODAS",
  pac_con_referencia: "Con los tres números de la referencia",
  pac_sin_referencia: "Con la referencia a medias",
  pac_con_hectareas: "Con hectáreas dichas",
  pac_sin_hectareas: "Sin hectáreas dichas",
  quitar_filtros: "QUITAR LOS FILTROS",
  sin_filtros_titulo: "Con esos filtros no hay ninguna tierra",
  sin_filtros_pista: "Prueba a quitar alguno.",
  agrupar_titulo: "Agrupar la lista",
  agrupar_no: "Sin agrupar",
  agrupar_cultivo: "Por lo que tienen sembrado",
  agrupar_municipio: "Por pueblo",
  agrupar_forma: "Por si se les ha medido la forma",
  grupo_con_forma: "Con su forma medida",
  grupo_sin_forma: "Sin forma",
  sin_forma: "SIN FORMA",
  con_forma: "Medida",
  sin_forma_explica: "De esta tierra no ha llegado el polígono, así que no se puede dibujar.",
  sin_cultivo: "Sin decir qué tiene",
  sin_hectareas: "Sin hectáreas dichas",
  sin_pueblo: "Sin pueblo dicho",
  revision_sin_version: "Sin ninguna versión de este año",
  col_marcar: "Marcar",
  marcar_todas: "MARCAR LAS QUE SE VEN",
  desmarcar_todas: "QUITAR LA SELECCIÓN",
  marcadas_uno: "Has marcado 1 tierra",
  marcadas_varios: "Has marcado {cuantas} tierras",
  ninguna_marcada: "No has marcado ninguna tierra.",
  marcar_esta: "Marcar esta tierra",
  col_numero: "N.º",
  col_nombre: "Nombre",
  col_referencia: "Referencia SIGPAC",
  col_hectareas: "Hectáreas",
  col_cultivo: "Qué tiene este año",
  col_pueblo: "Pueblo",
  col_revision: "Revisión",
  col_forma: "Forma",
  col_acciones: "Acciones",
  tabla_etiqueta: "Tus tierras",
  ver_versiones: "VER LO QUE HA SIDO",
  abrir_en_el_mapa: "VERLA EN EL MAPA",
  pie_filtrado: "Ves {cuantas} de {total} tierras",
  pie_todas: "{cuantas} tierras",
  pie_sin_forma: "Sin forma: {cuantas}",
  pie_sin_cultivo: "Sin decir qué tienen este año: {cuantas}",
  pie_sin_hectareas: "Sin hectáreas dichas: {cuantas}",
  mapa_titulo: "El mapa de la finca",
  mapa_explica: "Debajo están tus trozos, con la forma que tienen apuntada.",
  encajar: "ENCAJAR TODA LA FINCA",
  acercar: "ACERCAR",
  alejar: "ALEJAR",
  ver_mis_tierras: "QUITAR LOS LINDEROS DE MIS TIERRAS",
  ocultar_mis_tierras: "VER LOS LINDEROS DE MIS TIERRAS",
  cambiar_capa: "Qué se ve debajo",
  leyenda: "Leyenda",
  lo_da: "Lo da: {servicio}",
  fecha_de_la_imagen: "De cuándo es la imagen: {cuando}",
  fecha_sin_saber: "No se sabe: el servicio que da la imagen no dice de qué día es.",
  sin_forma_que_ensenar:
    "No hay ninguna tierra con su forma medida, así que no hay nada que dibujar en el mapa.",
  imagen_no_llega:
    "No se ha podido traer la imagen del mapa. Tus linderos siguen dibujados y la lista funciona igual.",
  leyenda_foto: "La foto del campo vista desde el aire. Es la ortofoto del IGN (PNOA).",
  leyenda_linderos: "Las rayas que separan los trozos de tierra, tal y como los tiene el SIGPAC.",
  leyenda_cultivo: "Lo que se declaró que hay sembrado en cada trozo, según el SIGPAC.",
  leyenda_mis_tierras: "Las rayas gruesas son tus tierras.",
  capa_avisos_no_esta: "La capa de avisos no está puesta porque el SIGPAC no publica ese servicio.",

};

/** `textos.VERSIONES_EN_PANTALLA`, que viaja en el mismo sitio. */
const TEXTOS_DE_LAS_VERSIONES = {
  titulo: "Lo que ha sido esta tierra",
  explica: "Una tierra no es siempre la misma: su forma, su uso y sus hectáreas cambian.",
  sin_versiones: "De esta tierra todavía no hay ninguna versión guardada.",
  de_que_ano: "El año",
  de_quien: "Quién lo dijo",
  cuando_se_miro: "Cuándo se miró",
  sin_fecha_de_consulta: "No se apuntó cuándo se miró.",
  referencia: "La referencia",
  sin_referencia_numeros: "No vinieron los números de la referencia.",
  le_falta_el_recinto: "Le falta el número de recinto",
  como_esta: "Cómo está",
  el_area_de_la_forma: "Lo que mide la forma que vino",
  el_area_del_sigpac: "Lo que dice el SIGPAC",
  el_area_declarada: "Las hectáreas que declaras",
  no_se_sabe: "No se sabe",
  comparar_titulo: "Comparar dos años",
  comparar_explica: "Elige un año y otro, y el programa te dice qué recintos están igual.",
  comparar_antes: "El año de antes",
  comparar_despues: "El año de ahora",
  comparar_boton: "COMPARAR",
  comparar_falta: "Elige los dos años y vuelve a pulsar.",
  comparar_sin_datos: "Todavía no hay versiones de dos años distintos.",
  que_cambio: "Qué cambió",
  no_cambio_nada: "No cambió nada",
  cuenta_iguales: "Iguales",
  cuenta_cambiados: "Cambiados",
  cuenta_desaparecidos: "Desaparecidos",
  cuenta_nuevos: "Nuevos",
  traer_titulo: "Traer lo de otro año",
  traer_explica: "Primero se enseña lo que cambiaría y no se apunta nada.",
  traer_de_anio: "Lo que esta tierra tenía en {anio}, según {fuente}",
  ensayar: "ENSAYARLO SIN APUNTAR NADA",
  ensayando: "Mirando qué cambiaría…",
  recintos_que_trae: "Recintos que trae",
  tierras_nuevas: "Tierras que se darían de alta",
  no_se_ha_apuntado:
    "Esto es solo un ensayo: no se ha apuntado nada de nada. Si te cuadra, pulsa el botón de abajo.",
  apuntarlo: "SÍ, APUNTARLO",
  apuntando_el_lote: "Apuntándolo…",
  apuntado_el_lote:
    "Ya está apuntado: {creadas} versiones nuevas y {actualizadas} puestas al día, con «igual» en {iguales}.",
  lo_que_no_se_pudo: "Lo que no se ha podido tener en cuenta",
  trozos_que_se_pisan: "Trozos que se pisan",
  superficies_que_no_cuadran: "Superficies que no cuadran",
  volver_a_las_tierras: "VOLVER A MIS TIERRAS",
};

/** Los cuatro estados de la comparación, tal y como los sirve `textos.VERSIONES_DE_RECINTO`. */
const ESTADOS = {
  estado_igual: "Igual",
  estado_cambiado: "Cambiado",
  estado_desaparecido: "Desaparecido",
  estado_nuevo: "Nuevo",
};

/** Las tres capas del mapa, tal y como las sirve `/api/mapa/estado`. */
const CAPAS = {
  foto: {
    titulo: "La foto del campo",
    servicio: "IGN (PNOA)",
    leyenda: TEXTOS.leyenda_foto,
    fecha: null,
    fecha_texto: TEXTOS.fecha_sin_saber,
    se_puede_ocultar: true,
  },
  linderos: {
    titulo: "Los linderos",
    servicio: "SIGPAC (FEGA)",
    leyenda: TEXTOS.leyenda_linderos,
    fecha: null,
    fecha_texto: TEXTOS.fecha_sin_saber,
    se_puede_ocultar: true,
  },
  cultivo: {
    titulo: "Lo que se declaró",
    servicio: "SIGPAC (FEGA)",
    leyenda: TEXTOS.leyenda_cultivo,
    fecha: null,
    fecha_texto: TEXTOS.fecha_sin_saber,
    se_puede_ocultar: true,
  },
};

/** Una caja de verdad, alrededor de unas coordenadas de Salamanca. */
const CAJA = { oeste: -5.56, sur: 40.9, este: -5.49, norte: 40.96 };

/**
 * Las tierras de prueba: 64 no hacen falta para comprobar el comportamiento, pero sí que haya
 * **nombres largos**, tierras sin forma, sin hectáreas, sin cultivo y con la referencia a medias.
 */
function unaTierra(cambios = {}) {
  return {
    id: 1,
    numero: 1,
    alias: "El Prado de arriba",
    referencia: "37-70-0-0-503-51-1",
    provincia: "Salamanca",
    municipio: "Peñaranda de Bracamonte",
    sistema: "secano",
    superficie_ha: 2.43,
    superficie_sigpac_ha: 2.79,
    tiene_forma: true,
    forma: null,
    anillos: [
      [
        [-5.56, 40.9],
        [-5.55, 40.9],
        [-5.55, 40.91],
        [-5.56, 40.91],
      ],
    ],
    cultivo: "Trigo blando · Craklin · secano",
    cultivo_clave: "Trigo blando",
    estado_revision: "revisado",
    estado_revision_texto: "Revisado",
    anio_de_la_version: 2026,
    fuente_texto: "SIGPAC",
    tiene_referencia_completa: true,
    area_declarada_ha: 2.5,
    tiene_hectareas_dichas: true,
    superficie_texto: "2,43 ha",
    forma_texto: TEXTOS.con_forma,
    revision_texto: "Revisado",
    ...cambios,
  };
}

const TIERRAS = [
  unaTierra(),
  unaTierra({
    id: 2,
    numero: 2,
    alias: "La Vega del río, junto al puente viejo",
    referencia: "37-70-0-0-504-12-1",
    municipio: "Macotera",
    cultivo: "Cebada · secano",
    cultivo_clave: "Cebada",
  }),
  unaTierra({
    id: 3,
    numero: 3,
    alias: "El alto sin medir",
    // **Sin forma**: no ha venido el polígono. Ni un anillo, ni un cuadro inventado.
    tiene_forma: false,
    forma: null,
    anillos: [],
    forma_texto: "",
    // Y sin hectáreas dichas ni cultivo: los dos «no lo sé» de la casa.
    superficie_ha: null,
    superficie_texto: "",
    tiene_hectareas_dichas: false,
    area_declarada_ha: null,
    cultivo: "",
    cultivo_clave: "",
    estado_revision: null,
    estado_revision_texto: "",
    revision_texto: "",
    // Referencia a medias: le falta el número de recinto.
    referencia: "37-70-0-0-505-3",
    tiene_referencia_completa: false,
  }),
];

/** La vista entera, como la sirve `/api/parcelas/vista`. */
function unaVista(cambios = {}) {
  return {
    textos: TEXTOS,
    textos_de_las_versiones: TEXTOS_DE_LAS_VERSIONES,
    campana_id: 1,
    campana_anio: 2026,
    tierras: TIERRAS.map((tierra) => ({ ...tierra })),
    totales: {
      tierras: 3,
      con_forma: 2,
      sin_forma: 1,
      sin_cultivo: 1,
      sin_hectareas: 1,
      sin_revision: 1,
    },
    mapa: { hay_forma: true, tierras_con_forma: 2, caja: { ...CAJA } },
    filtros: {
      cultivos: [
        { valor: "Cebada", texto: "Cebada", cuantas: 1 },
        { valor: "Trigo blando", texto: "Trigo blando", cuantas: 1 },
        { valor: "sin_cultivo", texto: TEXTOS.sin_cultivo, cuantas: 1 },
      ],
      municipios: [
        { valor: "Macotera", texto: "Macotera", cuantas: 1 },
        { valor: "Peñaranda de Bracamonte", texto: "Peñaranda de Bracamonte", cuantas: 1 },
        { valor: "sin_pueblo", texto: TEXTOS.sin_pueblo, cuantas: 0 },
      ],
      revisiones: [
        { valor: "revisado", texto: "Revisado", cuantas: 2 },
        { valor: "sin_version", texto: TEXTOS.revision_sin_version, cuantas: 1 },
      ],
      pac: [
        { valor: "con_referencia", texto: TEXTOS.pac_con_referencia, cuantas: 2 },
        { valor: "sin_referencia", texto: TEXTOS.pac_sin_referencia, cuantas: 1 },
        { valor: "con_hectareas", texto: TEXTOS.pac_con_hectareas, cuantas: 2 },
        { valor: "sin_hectareas", texto: TEXTOS.pac_sin_hectareas, cuantas: 1 },
      ],
    },
    ...cambios,
  };
}

/**
 * El mapa, tal y como lo prepara `app.js`.
 *
 * **La leyenda se arma aquí con la capa que se esté mirando**, igual que la arma `app.js`: si se
 * pasara siempre la de la foto, la prueba de la leyenda comprobaría la capa equivocada y pasaría sin
 * mirar lo que dice comprobar.
 */
function unMapa(cambios = {}) {
  const capa = cambios.capa || "foto";
  const suya = CAPAS[capa];
  return {
    capa,
    ver_mis_tierras: true,
    capas: CAPAS,
    url: `/api/mapa/imagen?capa=${capa}`,
    caja: { ...CAJA },
    ancho: 900,
    alto: 600,
    tiene_forma: true,
    fallo: "",
    capa_avisos_no_esta: TEXTOS.capa_avisos_no_esta,
    leyenda: [
      "Lo da: " + suya.servicio,
      suya.leyenda,
      "De cuándo es la imagen: " + TEXTOS.fecha_sin_saber,
      TEXTOS.leyenda_mis_tierras,
    ],
    alNoLlegarLaImagen: () => {},
    ...cambios,
  };
}

function propiedades(cambios = {}) {
  return {
    textos: { tierras: TEXTOS, mapa: {}, acciones: { volver: "VOLVER" } },
    vista: unaVista(),
    filtro: { q: "", cultivo: "", municipio: "", revision: "", pac: "" },
    grupo: "",
    marcadas: [],
    elegida: null,
    mapa: unMapa(),
    aviso: "",
    ...cambios,
  };
}

async function cargarTierras() {
  return import(`../web/react/pantallas/tierras_mapa.js?prueba=${Math.random()}`);
}

async function cargarVersiones() {
  return import(`../web/react/pantallas/tierra_versiones.js?prueba=${Math.random()}`);
}

async function htmlDeLasTierras(cambios = {}) {
  const { PantallaTierrasDeLaExplotacion } = await cargarTierras();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaTierrasDeLaExplotacion, propiedades(cambios)),
  );
}

async function htmlDeLasVersiones(cambios = {}) {
  const { PantallaVersionesDeUnaTierra } = await cargarVersiones();
  return globalThis.ReactDOMServer.renderToStaticMarkup(
    React.createElement(PantallaVersionesDeUnaTierra, {
      textos: { versiones: TEXTOS_DE_LAS_VERSIONES, mapa: {}, acciones: { volver: "VOLVER" } },
      tierra: {
        id: 1,
        titulo: "El Prado de arriba",
        abrir_en_el_mapa: TEXTOS.abrir_en_el_mapa,
        filas: [{ etiqueta: TEXTOS.col_referencia, valor: "37-70-0-0-503-51-1" }],
      },
      versiones: [],
      comparar: { puede: false, anios: [], comparacion: null },
      traer: [],
      ensayo: null,
      aviso: "",
      ...cambios,
    }),
  );
}

// ---------------------------------------------------------------------------
// Lectores del HTML: se mira como lo miraría una persona
// ---------------------------------------------------------------------------

/**
 * Lo que de verdad se lee en el HTML: el texto que hay entre las etiquetas.
 *
 * **Los números sueltos no son frases.** Un recuento («3», «1»), unas hectáreas («2,43 ha» es un dato
 * ya preparado por `app.js`) o un porcentaje son **datos del servidor**, no texto escrito a mano; la
 * prueba persigue las frases, y contarlos como frases obligaría a meter cada número en la lista de
 * textos del servidor, que es justo lo contrario de lo que se quiere comprobar.
 */
function frasesVisibles(html) {
  return html
    .replace(/<span class="icono"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<span class="flecha"[^>]*>[^<]*<\/span>/g, "")
    .replace(/<[^>]*>/g, "\u0000")
    .split("\u0000")
    .map((trozo) => trozo.trim())
    .filter((trozo) => trozo && !/^[\d.,%\s]+$/.test(trozo));
}

/** Las etiquetas de una clase, con sus atributos, para poder mirarlos uno a uno. */
function etiquetasCon(html, nombre, clase) {
  const patron = new RegExp(`<${nombre}\\b([^>]*class="[^"]*${clase}[^"]*"[^>]*)>`, "g");
  return [...html.matchAll(patron)].map((encontrado) => encontrado[1]);
}

/** Los valores de los atributos `data-lo-que-sea` de una lista de etiquetas. */
function datosDe(etiquetas, atributo) {
  return etiquetas
    .map((etiqueta) => {
      const encontrado = etiqueta.match(new RegExp(`${atributo}="([^"]*)"`));
      return encontrado ? encontrado[1] : null;
    })
    .filter((valor) => valor !== null);
}

/** Las filas de la tabla, con el texto de cada celda, ya recortado. */
function filasDeLaTabla(html) {
  const cuerpo = html.slice(html.indexOf("<tbody"));
  return [...cuerpo.matchAll(/<tr\b([^>]*)>([\s\S]*?)<\/tr>/g)].map((encontrado) => {
    const celdas = [...encontrado[2].matchAll(/<t[hd]\b[^>]*>([\s\S]*?)<\/t[hd]>/g)].map((celda) =>
      celda[1]
        .replace(/<[^>]*>/g, " ")
        .replace(/\s+/g, " ")
        .trim(),
    );
    const tipo = encontrado[1].match(/class="([^"]*)"/);
    return { clases: tipo ? tipo[1] : "", celdas };
  });
}

/** Los nombres de las tierras que salen en la tabla, en orden. */
function nombresDeLaTabla(html) {
  return datosDe(etiquetasCon(html, "button", "tabla-enlace"), "data-id");
}

// ---------------------------------------------------------------------------
// 1. La búsqueda y los filtros
// ---------------------------------------------------------------------------

test("el buscador encuentra por el nombre y por la referencia del SIGPAC", async () => {
  const { filtrarLasTierras } = await cargarTierras();

  // Por el nombre, y **sin tildes**: el agricultor escribe con una mano y con guantes.
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { q: "penaranda" }).map((una) => una.id),
    [],
    "el nombre de una tierra no lleva el pueblo: por «penaranda» no puede salir ninguna",
  );
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { q: "PRADO" }).map((una) => una.id),
    [1],
    "la búsqueda por el nombre no encuentra El Prado",
  );
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { q: "vega del rio" }).map((una) => una.id),
    [2],
    "la búsqueda no perdona las tildes: quien escribe «rio» no encuentra «río»",
  );
  // Y por trozos de la referencia del SIGPAC, que es la otra forma de nombrar una tierra.
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { q: "504-12" }).map((una) => una.id),
    [2],
    "la búsqueda por la referencia no encuentra el trozo escrito",
  );
  // Sin nada escrito no se esconde nada: un buscador vacío no es un filtro.
  assert.equal(filtrarLasTierras(TIERRAS, { q: "" }).length, 3);
  assert.equal(filtrarLasTierras(TIERRAS, {}).length, 3);
});

test("los cuatro filtros de la tabla dejan las tierras que toca", async () => {
  const { filtrarLasTierras } = await cargarTierras();

  assert.deepEqual(filtrarLasTierras(TIERRAS, { cultivo: "Cebada" }).map((una) => una.id), [2]);
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { cultivo: "sin_cultivo" }).map((una) => una.id),
    [3],
    "«sin decir qué tiene» no encuentra la tierra a la que le falta el cultivo",
  );
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { municipio: "Macotera" }).map((una) => una.id),
    [2],
  );
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { revision: "revisado" }).map((una) => una.id),
    [1, 2],
  );
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { revision: "sin_version" }).map((una) => una.id),
    [3],
    "«sin versión» y «sin revisar» no son lo mismo: esta tierra no la ha mirado nadie",
  );
  // Los cuatro hechos del filtro de lo que se puede declarar.
  assert.deepEqual(filtrarLasTierras(TIERRAS, { pac: "sin_referencia" }).map((una) => una.id), [3]);
  assert.deepEqual(filtrarLasTierras(TIERRAS, { pac: "sin_hectareas" }).map((una) => una.id), [3]);
  assert.equal(filtrarLasTierras(TIERRAS, { pac: "con_hectareas" }).length, 2);
  // Y **los filtros se suman**: cada uno quita, ninguno devuelve.
  assert.deepEqual(
    filtrarLasTierras(TIERRAS, { cultivo: "Cebada", municipio: "Macotera", revision: "revisado" }).map(
      (una) => una.id,
    ),
    [2],
  );
  assert.deepEqual(filtrarLasTierras(TIERRAS, { cultivo: "Cebada", municipio: "Peñaranda de Bracamonte" }), []);
});

test("un filtro que no se conoce no vacía la lista", async () => {
  // Es la misma decisión que en `rutas.js` con los parámetros de una dirección: un valor que quizá
  // venga de una pantalla más nueva no puede dejar al agricultor sin sus tierras. Vale para los dos
  // filtros que son **códigos de una lista cerrada** (la revisión y lo que se puede declarar).
  const { filtrarLasTierras } = await cargarTierras();
  assert.equal(filtrarLasTierras(TIERRAS, { pac: "lo_que_sea" }).length, 3);
  assert.equal(filtrarLasTierras(TIERRAS, { revision: "lo_que_sea" }).length, 3);
  // Y los otros tres filtran por **lo que hay escrito en la tierra**, así que un valor que no tiene
  // nadie devuelve cero tierras: el valor es un dato (el nombre de un cultivo, el de un pueblo).
  assert.deepEqual(filtrarLasTierras(TIERRAS, { cultivo: "Girasol" }), []);
  assert.deepEqual(filtrarLasTierras(TIERRAS, { municipio: "Soria" }), []);
  assert.deepEqual(filtrarLasTierras(TIERRAS, { q: "no-existe" }), []);
});

test("la pantalla enseña las tierras que pasan el filtro, y lo dice en el pie", async () => {
  const html = await htmlDeLasTierras({ filtro: { q: "vega" } });

  assert.match(html, /La Vega del río/, "la tierra buscada no sale");
  assert.doesNotMatch(html, /El Prado de arriba/, "sale una tierra que no casa con la búsqueda");
  // **Y el mapa también**: dibuja las tierras que pasan el filtro, no las de toda la finca. Es lo que
  // pide el contrato («el mapa respeta la selección declarada»).
  const poligonos = datosDe(etiquetasCon(html, "polygon", "t06-tierra"), "data-id");
  assert.deepEqual(poligonos, ["2"], "el mapa no respeta el filtro");
  // Y con los filtros puestos se dice **cuántas de cuántas**, que es lo que pide el contrato (A16).
  assert.match(html, /Ves 1 de 3 tierras/);
});

test("con un filtro que no deja ninguna tierra se dice, y hay botón para quitarlo", async () => {
  // Un estado vacío que no deja salida es lo que este proyecto prohíbe: si se dice que no hay nada,
  // se da el botón que lo arregla.
  const html = await htmlDeLasTierras({ filtro: { q: "no-existe-esta-tierra" } });

  assert.match(html, /Con esos filtros no hay ninguna tierra/);
  assert.match(html, /data-accion="t06-quitar-filtros"/, "el aviso no lleva su botón");
});

// ---------------------------------------------------------------------------
// 2. El grupo «sin forma»
// ---------------------------------------------------------------------------

test("agrupando por forma sale el grupo «Sin forma», con la tierra que no la tiene", async () => {
  const { agruparLasTierras } = await cargarTierras();

  const bloques = agruparLasTierras(TIERRAS, "forma", TEXTOS);

  assert.equal(bloques.length, 2);
  assert.equal(bloques[0].titulo, TEXTOS.grupo_con_forma);
  assert.deepEqual(bloques[0].tierras.map((una) => una.id), [1, 2]);
  assert.equal(bloques[1].titulo, "Sin forma");
  assert.deepEqual(bloques[1].tierras.map((una) => una.id), [3]);
});

test("la tierra sin forma sigue en la tabla y no se le dibuja nada", async () => {
  const html = await htmlDeLasTierras({ grupo: "forma" });

  // Está, con su nombre y su etiqueta.
  assert.match(html, /El alto sin medir/, "la tierra sin forma ha desaparecido de la tabla");
  assert.match(html, /SIN FORMA/, "no se dice que a esa tierra le falta la forma");
  // Y en el mapa **no hay ningún polígono suyo**: ni un cuadro en medio de la finca.
  const poligonos = datosDe(etiquetasCon(html, "polygon", "t06-tierra"), "data-id");
  assert.deepEqual(poligonos.sort(), ["1", "2"], "se ha dibujado un trozo de la tierra sin forma");
});

test("agrupar por lo sembrado y por pueblo deja las que no lo tienen al final", async () => {
  const { agruparLasTierras } = await cargarTierras();

  const porCultivo = agruparLasTierras([...TIERRAS].reverse(), "cultivo", TEXTOS);
  assert.deepEqual(porCultivo.map((bloque) => bloque.titulo), [
    "Cebada",
    "Trigo blando",
    TEXTOS.sin_cultivo,
  ]);

  const porPueblo = agruparLasTierras(TIERRAS, "municipio", TEXTOS);
  assert.deepEqual(porPueblo.map((bloque) => bloque.titulo), [
    "Macotera",
    "Peñaranda de Bracamonte",
  ]);

  // Y sin agrupar hay **un solo grupo sin título**: un camino solo, no dos.
  const sinAgrupar = agruparLasTierras(TIERRAS, "", TEXTOS);
  assert.equal(sinAgrupar.length, 1);
  assert.equal(sinAgrupar[0].titulo, "");
  assert.equal(sinAgrupar[0].tierras.length, 3);
});

// ---------------------------------------------------------------------------
// 3. La selección múltiple
// ---------------------------------------------------------------------------

test("la selección múltiple marca las tierras que se han elegido, y solo esas", async () => {
  const html = await htmlDeLasTierras({ marcadas: [1, 3] });

  const casillas = etiquetasCon(html, "input", "t06-casilla").length
    ? etiquetasCon(html, "input", "t06-casilla")
    : [...html.matchAll(/<input\b([^>]*data-accion="t06-marcar"[^>]*)>/g)].map((uno) => uno[1]);

  const marcadas = casillas
    .filter((casilla) => /checked/.test(casilla))
    .map((casilla) => casilla.match(/data-id="([^"]*)"/)[1]);
  assert.deepEqual(marcadas.sort(), ["1", "3"], "las casillas marcadas no son las que se eligieron");

  // Y cada casilla lleva **su** identificador y su acción: el manejador de clics sabe qué marcar.
  assert.equal(casillas.length, 3, "tiene que haber una casilla por tierra");
  for (const casilla of casillas) {
    assert.match(casilla, /data-accion="t06-marcar"/);
    assert.ok(casilla.match(/data-id="\d+"/), `una casilla no dice de qué tierra es: ${casilla}`);
  }
  assert.match(html, /Has marcado 2 tierras/, "no se dice cuántas se han marcado");
});

test("el recuento de lo marcado va en singular cuando es una, y los botones están", async () => {
  const html = await htmlDeLasTierras({ marcadas: [2] });

  // «1 tierras» es lo primero que hace desconfiar de un programa (regla de la casa). El texto es del
  // servidor; el número lo pone el componente, porque es él quien sabe qué hay marcado.
  assert.match(html, /Has marcado 1 tierra/);
  assert.doesNotMatch(html, /Has marcado 1 tierras/);
  assert.match(html, /data-accion="t06-marcar-todas"/);
  assert.match(html, /data-accion="t06-desmarcar-todas"/);
});

test("sin marcar ninguna se dice, en vez de dejar el hueco en blanco", async () => {
  const html = await htmlDeLasTierras();
  assert.match(html, /No has marcado ninguna tierra\./);
});

// ---------------------------------------------------------------------------
// 4. El vínculo entre la fila y el polígono
// ---------------------------------------------------------------------------

test("la tierra enfocada enciende su fila y su trozo: el vínculo, en los dos sentidos", async () => {
  const html = await htmlDeLasTierras({ elegida: 2 });

  // 1. Su **fila** está encendida, y solo la suya.
  const filas = filasDeLaTabla(html);
  const encendidas = filas.filter((fila) => fila.clases.includes("tabla-fila-elegida"));
  assert.equal(encendidas.length, 1, `hay ${encendidas.length} filas encendidas`);
  assert.ok(
    encendidas[0].celdas.some((celda) => celda.includes("La Vega")),
    "la fila encendida no es la de la tierra elegida",
  );

  // 2. Su **trozo** está encendido en el mapa.
  const poligonos = etiquetasCon(html, "polygon", "t06-tierra");
  const elegidos = poligonos.filter((poligono) => poligono.includes("t06-tierra-elegida"));
  assert.equal(elegidos.length, 1, "no hay exactamente un trozo encendido");
  assert.match(elegidos[0], /data-id="2"/, "el trozo encendido no es el de la tierra elegida");

  // 3. Y **cada trozo lleva la acción de enfocar su fila**: así tocar el mapa enciende su renglón,
  //    que es la otra mitad del contrato.
  for (const poligono of poligonos) {
    assert.match(poligono, /data-accion="t06-elegir-fila"/, `un trozo no enfoca su fila: ${poligono}`);
    assert.match(poligono, /data-id="\d+"/, "un trozo no dice de qué tierra es");
  }

  // 4. Y la fila también lleva la acción con su identificador (el nombre es un botón, no la fila).
  const nombres = etiquetasCon(html, "button", "tabla-enlace");
  assert.equal(nombres.length, 3);
  assert.deepEqual(datosDe(nombres, "data-id"), ["1", "2", "3"]);
});

test("la tierra marcada se distingue de la elegida, y las dos se ven", async () => {
  // Elegir (mirar su trozo) y marcar (juntarla con otras) son dos cosas distintas y no pueden
  // confundirse: el agricultor puede estar mirando una y tener tres marcadas.
  const html = await htmlDeLasTierras({ elegida: 1, marcadas: [2] });

  const poligonos = etiquetasCon(html, "polygon", "t06-tierra");
  const uno = poligonos.find((poligono) => poligono.includes('data-id="1"'));
  const dos = poligonos.find((poligono) => poligono.includes('data-id="2"'));

  assert.match(uno, /t06-tierra-elegida/);
  assert.doesNotMatch(uno, /t06-tierra-marcada/);
  assert.match(dos, /t06-tierra-marcada/);
  assert.doesNotMatch(dos, /t06-tierra-elegida/);
});

test("los puntos del trozo se colocan con el norte arriba y dentro de la imagen", async () => {
  const { puntosDelTrozo } = await cargarTierras();

  const puntos = puntosDelTrozo(
    [
      [
        [-5.56, 40.96],
        [-5.49, 40.96],
        [-5.49, 40.9],
        [-5.56, 40.9],
      ],
    ],
    CAJA,
    900,
    600,
  );

  assert.equal(puntos.length, 1, "un anillo es un polígono");
  const esquinas = puntos[0].split(" ").map((par) => par.split(",").map(Number));
  assert.deepEqual(esquinas[0], [0, 0], "el noroeste de la caja no cae en la esquina de arriba");
  assert.deepEqual(esquinas[2], [900, 600], "el sureste no cae en la esquina de abajo");
  for (const [x, y] of esquinas) {
    assert.ok(x >= 0 && x <= 900 && y >= 0 && y <= 600, `un punto se sale de la imagen: ${x}, ${y}`);
  }
});

test("un trozo partido en dos son dos polígonos, y uno sin forma no es ninguno", async () => {
  const { puntosDelTrozo } = await cargarTierras();

  const dos = puntosDelTrozo(
    [
      [
        [-5.56, 40.9],
        [-5.55, 40.9],
        [-5.55, 40.91],
      ],
      [
        [-5.5, 40.95],
        [-5.49, 40.95],
        [-5.49, 40.96],
      ],
    ],
    CAJA,
    900,
    600,
  );
  assert.equal(dos.length, 2, "los dos trozos tienen que ser dos polígonos separados, no una lista");
  // Y sin anillos (o con una caja imposible) no se dibuja nada: lo que no se ha medido no se inventa.
  assert.deepEqual(puntosDelTrozo([], CAJA, 900, 600), []);
  assert.deepEqual(puntosDelTrozo([[[]]], CAJA, 900, 600), []);
  assert.deepEqual(puntosDelTrozo([[[0, 0], [1, 1], [2, 2]]], null, 900, 600), []);
});

// ---------------------------------------------------------------------------
// 5. El mapa: capas, leyenda y lo que pasa cuando una imagen no llega
// ---------------------------------------------------------------------------

test("las capas salen del servidor y la elegida se ve marcada, con su nombre", async () => {
  const html = await htmlDeLasTierras({ mapa: unMapa({ capa: "linderos" }) });

  for (const capa of Object.values(CAPAS)) {
    assert.ok(html.includes(capa.titulo), `no sale la capa «${capa.titulo}»`);
  }
  const botones = etiquetasCon(html, "button", "boton-elegido")
    .concat(etiquetasCon(html, "button", "boton-claro"))
    .filter((boton) => boton.includes('data-accion="t06-capa"'));
  const elegido = botones.filter((boton) => boton.includes('data-elegido="1"'));
  assert.equal(elegido.length, 1, "no hay exactamente una capa elegida");
  assert.match(elegido[0], /data-valor="linderos"/);
});

test("la leyenda dice qué enseña la capa, de quién es y que la fecha no se sabe", async () => {
  const html = await htmlDeLasTierras({ mapa: unMapa({ capa: "linderos" }) });

  assert.match(html, /Lo da: SIGPAC \(FEGA\)/);
  assert.match(html, /Las rayas que separan los trozos de tierra/);
  // **La fecha no se inventa**: los servicios no dicen de qué día es la imagen, y se dice eso.
  assert.match(html, /De cuándo es la imagen: No se sabe/);
  assert.match(html, /La capa de avisos no está puesta porque el SIGPAC no publica ese servicio\./);
  // Y el usuario puede quitar las capas: el botón de los linderos lo dice.
  assert.match(html, /data-accion="t06-ver-mis-tierras"/);
});

test("cuando una imagen no llega, se avisa, no se borran los linderos y la lista sigue", async () => {
  const html = await htmlDeLasTierras({
    mapa: unMapa({ fallo: TEXTOS.imagen_no_llega }),
  });

  assert.match(html, /No se ha podido traer la imagen del mapa/);
  assert.match(html, /Tus linderos siguen dibujados y la lista funciona igual/);
  // La foto **no** se queda puesta sin fecha: en su sitio va el aviso.
  assert.doesNotMatch(html, /<img class="t06-imagen"/, "la imagen vieja se ha quedado en la pantalla");
  // Y los trozos siguen ahí, que es lo que el contrato prohíbe borrar.
  const poligonos = datosDe(etiquetasCon(html, "polygon", "t06-tierra"), "data-id");
  assert.deepEqual(poligonos.sort(), ["1", "2"], "los linderos se han borrado con la imagen");
  // Y la tabla sigue entera.
  assert.equal(nombresDeLaTabla(html).length, 3);
});

test("sin ninguna forma que enseñar se dice, en vez de dibujar un cuadro en otra provincia", async () => {
  const html = await htmlDeLasTierras({
    vista: unaVista({
      tierras: TIERRAS.map((tierra) => ({ ...tierra, anillos: [], tiene_forma: false })),
      mapa: { hay_forma: false, tierras_con_forma: 0, caja: null },
    }),
    mapa: unMapa({ tiene_forma: false, caja: null, url: "" }),
  });

  assert.match(html, /No hay ninguna tierra con su forma medida/);
  assert.equal(etiquetasCon(html, "polygon", "t06-tierra").length, 0, "se ha dibujado un trozo inventado");
  // Y las tierras siguen todas en la tabla: sin forma no es sin datos.
  assert.equal(nombresDeLaTabla(html).length, 3);
});

test("quitar los linderos deja la foto y no dibuja ni un polígono", async () => {
  const html = await htmlDeLasTierras({
    mapa: unMapa({ ver_mis_tierras: false, leyenda: [] }),
  });

  assert.equal(etiquetasCon(html, "polygon", "t06-tierra").length, 0);
  assert.match(html, /data-accion="t06-ver-mis-tierras"/);
  // El botón dice lo que va a hacer ahora: volver a enseñarlos.
  assert.match(html, /VER LOS LINDEROS DE MIS TIERRAS/);
});

// ---------------------------------------------------------------------------
// 6. Las dos pantallas no llevan ni una frase escrita a mano
// ---------------------------------------------------------------------------

/** La frase del servidor para las tierras, ya rellenada como la rellena `app.js`. */
function textosDelServidorDeLasTierras() {
  const dichos = new Set(Object.values(TEXTOS));
  // Los que llevan huecos: los rellena el componente (o `app.js`), así que aquí se añaden ya
  // escritos. El pie es la única frase **compuesta**: las cuatro líneas del servidor unidas con « · »,
  // que es la misma forma que usa el pie de la tabla del cuaderno (`tablaDeApuntes`).
  for (const frase of [
    "3 tierras",
    "Sin forma: 1",
    "Sin decir qué tienen este año: 1",
    "Sin hectáreas dichas: 1",
    "3 tierras · Sin forma: 1 · Sin decir qué tienen este año: 1 · Sin hectáreas dichas: 1",
    "Ves 1 de 3 tierras · Sin forma: 1",
    "Lo da: IGN (PNOA)",
    "De cuándo es la imagen: " + TEXTOS.fecha_sin_saber,
    "Has marcado 1 tierra",
  ]) {
    dichos.add(frase);
  }
  // Los datos: nombres de tierras, pueblos, cultivos, referencias, los números ya en castellano y los
  // años. **No son frases**: son lo que hay en el cuaderno del agricultor, ya preparado por `app.js`
  // (que es quien tiene los números y las frases del servidor que los envuelven).
  for (const tierra of TIERRAS) {
    for (const dato of [
      tierra.alias,
      tierra.referencia,
      tierra.municipio,
      tierra.cultivo,
      tierra.numero,
      tierra.superficie_texto,
      tierra.forma_texto,
      tierra.revision_texto,
    ]) {
      if (dato !== null && dato !== undefined && dato !== "") dichos.add(String(dato));
    }
  }
  for (const opcion of [
    ...unaVista().filtros.cultivos,
    ...unaVista().filtros.municipios,
    ...unaVista().filtros.revisiones,
    ...unaVista().filtros.pac,
  ]) {
    dichos.add(opcion.texto);
  }
  for (const capa of Object.values(CAPAS)) dichos.add(capa.titulo);
  dichos.add("VOLVER");
  return dichos;
}

test("la pantalla de las tierras no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLasTierras({ grupo: "forma", marcadas: [1] });
  const delServidor = textosDelServidorDeLasTierras();
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});
test("la pantalla de las versiones no lleva ni una frase escrita a mano", async () => {
  const html = await htmlDeLasVersiones({
    versiones: [unaVersion()],
    comparar: {
      puede: true,
      anios: [{ valor: 2026, texto: "2026" }],
      antes: 2025,
      despues: 2026,
      comparacion: unaComparacion(),
    },
    traer: [{ fuente: "sigpac", campana: "1", pista: "Lo que esta tierra tenía en 2025, según SIGPAC" }],
    ensayo: unEnsayo({ aplicada: false }),
  });
  const delServidor = new Set([
    ...Object.values(TEXTOS_DE_LAS_VERSIONES),
    ...Object.values(TEXTOS),
    ...Object.values(ESTADOS),
    // Los datos: la tierra, sus años y lo que dice cada versión.
    "El Prado de arriba",
    "37-70-0-0-503-51-1",
    "2026",
    "2025",
    "2026 · SIGPAC",
    "2,79 ha",
    "2,50 ha",
    "Revisado",
    "1,80 ha",
    "VOLVER",
    // Lo que une `app.js` (la frase del servidor con el dato dentro).
    "Lo que esta tierra tenía en 2025, según SIGPAC",
    "Recintos que trae · SIGPAC 2025",
    "Qué cambió: la forma del trozo",
    "Qué cambió: la referencia",
    "Qué cambió: la superficie del SIGPAC",
    // Los títulos de los cambios: `app.js` une la tierra con su referencia del servidor.
    "El Prado de arriba · 37-70-0-0-503-51-1",
    "El Prado de arriba · 37-70-0-0-503-52-1",
    "El Prado de arriba · 37-70-0-0-503-53-1",
    // El resumen de la comparación lo escribe el servidor (`textos.MENSAJES.R13…`) y llega entero.
    "1 iguales, 1 cambiados, 1 desaparecidos y 1 nuevos",
    // Y los cuatro recuentos son **números**, no frases: los cuenta el servidor.
    "1",
    "3",
  ]);
  for (const frase of frasesVisibles(html)) {
    assert.ok(delServidor.has(frase), `frase escrita a mano: «${frase}»`);
  }
});

// ---------------------------------------------------------------------------
// 7. Lo que ha sido una tierra: las versiones, la comparación y el ensayo
// ---------------------------------------------------------------------------

/** Una versión, tal y como la deja `app.js` después de leerla del servidor. */
function unaVersion() {
  return {
    id: 4,
    titulo: "2026 · SIGPAC",
    como_esta: "Revisado",
    filas: [
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.referencia, valor: "37-70-0-0-503-51-1" },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.el_area_de_la_forma, valor: "2,79 ha" },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.el_area_del_sigpac, valor: "2,79 ha" },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.el_area_declarada, valor: "2,50 ha" },
      {
        etiqueta: TEXTOS_DE_LAS_VERSIONES.cuando_se_miro,
        valor: TEXTOS_DE_LAS_VERSIONES.sin_fecha_de_consulta,
      },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.como_esta, valor: "Revisado" },
    ],
    avisos: [],
  };
}

/** Una comparación con **los cuatro estados**, que es lo que pide el contrato. */
function unaComparacion() {
  return {
    resumen: "1 iguales, 1 cambiados, 1 desaparecidos y 1 nuevos",
    cuenta: [
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.cuenta_iguales, valor: 1, clase: "bien" },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.cuenta_cambiados, valor: 1, clase: "mirar" },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.cuenta_desaparecidos, valor: 1, clase: "mirar" },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.cuenta_nuevos, valor: 1, clase: "voluntario" },
    ],
    cambios: [
      {
        estado_texto: "Igual",
        clase: "bien",
        titulo: "El Prado de arriba · 37-70-0-0-503-51-1",
        que_cambio: "No cambió nada",
      },
      {
        estado_texto: "Cambiado",
        clase: "mirar",
        titulo: "El Prado de arriba · 37-70-0-0-503-51-1",
        que_cambio: "Qué cambió: la forma del trozo",
      },
      {
        estado_texto: "Desaparecido",
        clase: "mirar",
        titulo: "El Prado de arriba · 37-70-0-0-503-52-1",
        que_cambio: "Qué cambió: la referencia",
      },
      {
        estado_texto: "Nuevo",
        clase: "voluntario",
        titulo: "El Prado de arriba · 37-70-0-0-503-53-1",
        que_cambio: "",
      },
    ],
  };
}

/** Lo que devuelve `/api/versiones/previsualizar`, ya preparado por `app.js`. */
function unEnsayo(cambios = {}) {
  return {
    titulo: "Recintos que trae · SIGPAC 2025",
    filas: [
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.recintos_que_trae, valor: 3 },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.cuenta_iguales, valor: 1 },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.cuenta_cambiados, valor: 1 },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.cuenta_nuevos, valor: 1 },
      { etiqueta: TEXTOS_DE_LAS_VERSIONES.tierras_nuevas, valor: 0 },
    ],
    detalle: [
      {
        estado_texto: "Cambiado",
        clase: "mirar",
        titulo: "El Prado de arriba · 37-70-0-0-503-51-1",
        que_cambio: "Qué cambió: la superficie del SIGPAC",
      },
    ],
    avisos: [],
    apuntado: "",
    sin_apuntar: TEXTOS_DE_LAS_VERSIONES.no_se_ha_apuntado,
    apuntando: false,
    ...cambios,
  };
}

test("la ficha enseña las cuatro cosas de una versión, y las tres áreas separadas", async () => {
  const html = await htmlDeLasVersiones({
    versiones: [unaVersion()],
    comparar: { puede: false, anios: [], comparacion: null },
  });

  assert.match(html, /2026 · SIGPAC/, "no sale el año ni la fuente de la versión");
  assert.match(html, /Lo que mide la forma que vino/);
  assert.match(html, /Lo que dice el SIGPAC/);
  assert.match(html, /Las hectáreas que declaras/);
  // Y sin versión no se inventa una tabla vacía: se dice, y se ofrece traer lo de otro año.
  const sinNada = await htmlDeLasVersiones();
  assert.match(sinNada, /De esta tierra todavía no hay ninguna versión guardada\./);
});

test("los cuatro estados de la comparación salen cada uno con su palabra", async () => {
  const html = await htmlDeLasVersiones({
    versiones: [unaVersion()],
    comparar: {
      puede: true,
      anios: [{ valor: 2025, texto: "2025" }, { valor: 2026, texto: "2026" }],
      antes: 2025,
      despues: 2026,
      comparacion: unaComparacion(),
    },
  });

  for (const estado of ["Igual", "Cambiado", "Desaparecido", "Nuevo"]) {
    assert.ok(html.includes(`>${estado}<`) || html.includes(estado), `no sale el estado «${estado}»`);
  }
  // Los cuatro totales, y el porqué de cada cambio.
  assert.match(html, /Iguales/);
  assert.match(html, /Cambiados/);
  assert.match(html, /Desaparecidos/);
  assert.match(html, /Nuevos/);
  assert.match(html, /Qué cambió: la forma del trozo/);
  // Y **comparar no toca nada**: la pantalla solo tiene el botón de comparar, que lee.
  assert.match(html, /data-accion="t06-comparar"/);
  assert.doesNotMatch(html, /data-accion="t06-apuntar-lote"/, "la comparación ofrece apuntar algo");
});

test("sin dos años con versiones no se ofrece comparar, y se dice por qué", async () => {
  const html = await htmlDeLasVersiones({
    versiones: [unaVersion()],
    comparar: { puede: false, anios: [], comparacion: null, sin_datos: TEXTOS_DE_LAS_VERSIONES.comparar_sin_datos },
  });

  assert.match(html, /Todavía no hay versiones de dos años distintos\./);
  assert.doesNotMatch(html, /data-accion="t06-comparar"/);
});

test("la previsualización dice que no ha apuntado nada, y el botón de apuntarlo está aparte", async () => {
  const html = await htmlDeLasVersiones({
    versiones: [unaVersion()],
    traer: [{ fuente: "sigpac", campana: "1", pista: "Lo que esta tierra tenía en 2025, según SIGPAC" }],
    ensayo: unEnsayo({ aplicada: false }),
  });

  // Los cuatro números del plan, que los da el servidor.
  assert.match(html, /Recintos que trae/);
  assert.match(html, /Tierras que se darían de alta/);
  // **La frase que deja claro que mirar no es apuntar.**
  assert.match(html, /Esto es solo un ensayo: no se ha apuntado nada de nada\./);
  assert.doesNotMatch(html, /Ya está apuntado:/, "dice que se ha apuntado algo que solo se ha ensayado");
  // Y el botón de apuntarlo **solo sale cuando hay un ensayo delante**.
  assert.match(html, /data-accion="t06-apuntar-lote"/);
  assert.match(html, /SÍ, APUNTARLO/);
  // Y sin ensayo no hay botón de apuntar nada: primero se mira.
  const sinEnsayo = await htmlDeLasVersiones({ versiones: [unaVersion()] });
  assert.doesNotMatch(sinEnsayo, /data-accion="t06-apuntar-lote"/);
});

test("después de apuntarlo, la pantalla dice qué se ha escrito y ya no ofrece apuntarlo otra vez", async () => {
  const html = await htmlDeLasVersiones({
    versiones: [unaVersion()],
    ensayo: unEnsayo({
      aplicada: true,
      sin_apuntar: "",
      apuntado: "Ya está apuntado: 2 versiones nuevas y 1 puestas al día, con «igual» en 1.",
    }),
  });

  assert.match(html, /Ya está apuntado: 2 versiones nuevas y 1 puestas al día/);
  assert.doesNotMatch(html, /Esto es solo un ensayo/);
  assert.doesNotMatch(html, /data-accion="t06-apuntar-lote"/);
});

test("lo que el ensayo no ha podido tener en cuenta se dice, no se calla", async () => {
  const html = await htmlDeLasVersiones({
    versiones: [unaVersion()],
    ensayo: unEnsayo({
      avisos: [
        { titulo: TEXTOS_DE_LAS_VERSIONES.lo_que_no_se_pudo, lineas: ["El recinto 3 no trae ni referencia ni forma."] },
        {
          titulo: TEXTOS_DE_LAS_VERSIONES.superficies_que_no_cuadran,
          lineas: ["Se llevan un 4 % entre la forma y el SIGPAC."],
        },
      ],
    }),
  });

  assert.match(html, /Lo que no se ha podido tener en cuenta/);
  assert.match(html, /El recinto 3 no trae ni referencia ni forma\./);
  assert.match(html, /Superficies que no cuadran/);
});

test("el lote que se ensaya lleva los números que vinieron y no se inventa ninguno", async () => {
  // **Esta es la mitad del ensayo que se puede comprobar sin servidor**, y la que importa: si aquí se
  // rellenara un número que no vino, al otro lado se daría de alta una tierra que no es.
  const { loteDesdeLasVersiones } = await cargarVersiones();

  const versiones = [
    {
      parcela_id: 7,
      fuente: "sigpac",
      campana_id: 1,
      provincia: "37",
      municipio: "70",
      agregado: 0,
      zona: 0,
      poligono: 503,
      numero_parcela: 51,
      numero_recinto: 1,
      geometria: "POLYGON((0 0, 1 0, 1 1))",
      area_sigpac_ha: 2.79,
      area_declarada_ha: null,
      uso_sigpac: "TA",
    },
    {
      parcela_id: 8,
      fuente: "agricultor",
      campana_id: 1,
      provincia: "37",
      municipio: "70",
      agregado: null,
      zona: null,
      poligono: 504,
      numero_parcela: 12,
      numero_recinto: null,
      geometria: null,
      area_sigpac_ha: null,
      area_declarada_ha: 1.8,
      uso_sigpac: null,
    },
  ];

  const lote = loteDesdeLasVersiones(versiones, { campanaId: 2, fuente: "sigpac" });

  assert.equal(lote.campana_id, 2, "el lote no va al año que toca");
  assert.equal(lote.fuente, "sigpac");
  assert.equal(lote.recintos.length, 1, "se ha colado un recinto de otra fuente");
  const recinto = lote.recintos[0];
  assert.equal(recinto.parcela_id, 7, "sin la tierra, el servidor daría de alta una repetida");
  assert.equal(recinto.numero_recinto, 1);
  assert.equal(recinto.area_sigpac_ha, 2.79);
  // **Y lo que no vino no se manda**: `area_declarada_ha` estaba vacía, y un `null` explícito no es
  // lo mismo que no mandarlo (`CAMPOS_QUE_UNA_IMPORTACION_NO_BORRA`).
  assert.ok(
    !("area_declarada_ha" in recinto),
    "se manda la superficie declarada vacía, y eso podría borrar la que el agricultor puso",
  );
  // Y con otro año sin versiones de esa fuente, el lote sale vacío en vez de con recintos de otra.
  assert.deepEqual(loteDesdeLasVersiones(versiones, { campanaId: 2, fuente: "medicion_en_campo" }).recintos, []);
});

test("el ensayo solo puede acabar en la ruta que lee, y solo el botón de apuntar escribe", async () => {
  // Se lee el propio `app.js`, como hace `tests_js/rutas.test.js` con «rutas.js no toca el navegador»:
  // es la forma de comprobar que **previsualizar no escribe** sin levantar un servidor. Lo que se
  // persigue: que el camino del ensayo no tenga ninguna forma de escribir, ni por descuido.
  const app = readFileSync(new URL("../web/app.js", import.meta.url), "utf8");

  // 1. La función del botón de ensayar manda el lote a la ruta que **solo lee**, y su cuerpo entero no
  //    tiene ninguna forma de escribir. Se le quitan los comentarios, como hace la prueba de Python
  //    `quita_comentarios`: el comentario de la función de al lado **habla** de la ruta que escribe, y
  //    sin quitarlo la prueba se creería que eso es código.
  const desde = app.indexOf("async function ensayarTraerLoDeOtroAnio");
  const hasta = app.indexOf("async function apuntarElLoteEnsayado");
  assert.ok(desde > 0 && hasta > desde, "no encuentro la función del ensayo en `app.js`");
  const ensayar = app
    .slice(desde, hasta)
    .replace(/(?:\/\*[\s\S]*?\*\/|\/\/[^\n]*)/g, "");
  assert.match(ensayar, /apiJson\("\/api\/versiones\/previsualizar"/, "el ensayo no lee del servidor");
  assert.doesNotMatch(ensayar, /versiones\/aplicar/, "la función del ensayo llama a algo que escribe");

  // 2. Y en toda la aplicación hay **una sola** llamada a cada ruta: la de leer y la de escribir. Si
  //    alguien añadiera otra, esto lo caza.
  const previsualizar = [...app.matchAll(/apiJson\("\/api\/versiones\/previsualizar"/g)];
  const aplicar = [...app.matchAll(/apiJson\("\/api\/versiones\/aplicar"/g)];
  assert.equal(previsualizar.length, 1, "previsualizar se pide desde más de un sitio");
  assert.equal(aplicar.length, 1, "hay más de un sitio que puede escribir versiones");

  // 3. Y esa única llamada que escribe está dentro de la función del botón de apuntarlo.
  const apuntar = app.slice(hasta);
  assert.ok(
    apuntar.indexOf("/api/versiones/aplicar") < apuntar.indexOf("return pantallaVersionesDeUnaTierra();"),
    "la llamada que escribe no está en el botón de apuntarlo",
  );
});

test("los años que se pueden comparar son los que tienen versiones, del más nuevo al más viejo", async () => {
  const { aniosConVersiones } = await cargarVersiones();

  const anios = aniosConVersiones([
    { anio: 2025, campana_id: 3, fuente: "sigpac" },
    { anio: 2026, campana_id: 1, fuente: "sigpac" },
    { anio: 2025, campana_id: 3, fuente: "agricultor" },
  ]);

  assert.deepEqual(anios, [
    { anio: 2026, campana_id: 1 },
    { anio: 2025, campana_id: 3 },
  ]);
  // Una versión sin año no se ofrece: comparar con un año que no se sabe no es comparar.
  assert.deepEqual(aniosConVersiones([{ anio: null, campana_id: 1 }]), []);
  assert.deepEqual(aniosConVersiones([]), []);
});

// ---------------------------------------------------------------------------
// 8. La finca **de verdad**: 64 tierras y NINGUNA con forma (03/10/2026)
//
// **Este apartado existe por un dato medido, no por una precaución.** El coordinador midió los datos
// reales del agricultor sobre una copia de `backend/cuedigital.db` (mismo sha256 que el original) y
// salió esto: **64 tierras en su explotación y 0 con geometría** — todas van sin polígono—, con
// nombres de hasta 42 caracteres que llevan dentro el paréntesis y las hectáreas
// (`503/10059-1 BARBECHO TRADICIONAL (3.54 ha)`).
//
// O sea que **el grupo «sin forma» no es un cajón de excepciones: es la finca entera**, y el caso «no
// hay nada que dibujar en el mapa» **es el caso normal**. Las pruebas de arriba usan tres tierras
// inventadas; estas usan la forma de los datos de verdad (64 filas, ninguna con forma, un nombre de
// 42 caracteres) para que la pantalla no se apoye en «casi todas tienen forma».
//
// **Lo que NO se hace aquí:** leer la base del agricultor. Los datos están escritos a mano con la
// forma que tienen los suyos (y por eso hay 64 y un nombre largo idéntico al de verdad). La base real
// se miró una vez, sobre una copia en la carpeta temporal, y lo que se vio está contado en
// `docs/T06_MAPA_Y_TIERRA.md` §5.2 bis.
// ---------------------------------------------------------------------------

/** El nombre más largo que tiene de verdad el agricultor, con sus 42 caracteres. */
const EL_NOMBRE_MAS_LARGO = "503/10059-1 BARBECHO TRADICIONAL (3.54 ha)";

/** Una finca como la de verdad: 64 tierras y **ninguna** con su forma medida. */
function laFincaDeVerdad() {
  const tierras = [];
  for (let numero = 1; numero <= 64; numero += 1) {
    tierras.push(
      unaTierra({
        id: numero,
        numero,
        // Los cinco nombres largos son de verdad así: el número del recinto, lo que hay y las
        // hectáreas entre paréntesis.
        alias:
          numero === 29
            ? EL_NOMBRE_MAS_LARGO
            : numero === 16
              ? "501/5030-1 BARBECHO TRADICIONAL (0.24 ha)"
              : numero === 21
                ? "502/205-1 BARBECHO TRADICIONAL (4.08 ha)"
                : `502/${200 + numero}-1 BARBECHO TRADICIONAL (1.65 ha)`,
        referencia: `37-70-0-0-502-${200 + numero}-1`,
        municipio: numero % 9 === 0 ? "MACHACON" : "CALVARRASA DE ARRIBA",
        // **Ninguna con forma**: es el dato real.
        tiene_forma: false,
        forma: null,
        anillos: [],
        forma_texto: "",
        superficie_texto: "1,65 ha",
        cultivo: numero % 6 === 0 ? "" : "BARBECHO TRADICIONAL · secano",
        cultivo_clave: numero % 6 === 0 ? "" : "BARBECHO TRADICIONAL",
        // Y sin ninguna versión de este año: tampoco hay ninguna en los datos de verdad.
        estado_revision: null,
        estado_revision_texto: "",
        revision_texto: "",
        anio_de_la_version: null,
        fuente_texto: null,
      }),
    );
  }
  return {
    textos: TEXTOS,
    textos_de_las_versiones: TEXTOS_DE_LAS_VERSIONES,
    campana_id: 1,
    campana_anio: 2026,
    tierras,
    totales: {
      tierras: 64,
      con_forma: 0,
      sin_forma: 64,
      sin_cultivo: 10,
      sin_hectareas: 0,
      sin_revision: 64,
    },
    // **El mapa no tiene nada que dibujar**: ni caja, ni un centro inventado.
    mapa: { hay_forma: false, tierras_con_forma: 0, caja: null },
    filtros: {
      cultivos: [{ valor: "BARBECHO TRADICIONAL", texto: "BARBECHO TRADICIONAL", cuantas: 54 }],
      municipios: [{ valor: "CALVARRASA DE ARRIBA", texto: "CALVARRASA DE ARRIBA", cuantas: 57 }],
      revisiones: [{ valor: "sin_version", texto: TEXTOS.revision_sin_version, cuantas: 64 }],
      pac: [{ valor: "con_referencia", texto: TEXTOS.pac_con_referencia, cuantas: 64 }],
    },
  };
}

test("con las 64 tierras de verdad sin forma, todas caen en el grupo «Sin forma»", async () => {
  const { agruparLasTierras, filtrarLasTierras } = await cargarTierras();
  const vista = laFincaDeVerdad();

  assert.equal(vista.tierras.length, 64);
  assert.equal(filtrarLasTierras(vista.tierras, {}).length, 64, "sin filtro tienen que salir las 64");

  const bloques = agruparLasTierras(vista.tierras, "forma", TEXTOS);
  assert.equal(bloques.length, 1, "con ninguna forma medida solo puede haber un grupo");
  assert.equal(bloques[0].titulo, "Sin forma");
  assert.equal(bloques[0].tierras.length, 64);
});

test("sin ninguna forma que dibujar, la tabla sigue con sus 64 filas y el mapa lo dice", async () => {
  const html = await htmlDeLasTierras({
    vista: laFincaDeVerdad(),
    mapa: unMapa({ tiene_forma: false, caja: null, url: "" }),
  });

  // La tabla entera, con una casilla por tierra: sin forma no es sin datos.
  assert.equal(nombresDeLaTabla(html).length, 64, "no salen las 64 tierras");
  assert.equal(
    (html.match(/data-accion="t06-marcar"/g) || []).length,
    64,
    "no hay una casilla por tierra",
  );
  // **Ni un polígono inventado**, y el mapa dice por qué no hay nada que ver.
  assert.equal(etiquetasCon(html, "polygon", "t06-tierra").length, 0, "se ha dibujado una forma que no existe");
  assert.match(html, /No hay ninguna tierra con su forma medida/);
  // Y ninguna petición de imagen: sin caja no se le pide nada al servicio de mapas.
  assert.doesNotMatch(html, /<img class="t06-imagen"/, "se ha pedido una foto sin saber de dónde");

  // **Y el nombre de 42 caracteres sale entero**, con su paréntesis y sus hectáreas dentro.
  assert.ok(html.includes(EL_NOMBRE_MAS_LARGO), "el nombre largo no sale entero");
  // El pie, con los recuentos de verdad.
  assert.match(html, /64 tierras/);
  assert.match(html, /Sin forma: 64/);
});

test("la tierra sin forma lleva su etiqueta también sin agrupar (con las 64 de verdad)", async () => {
  // El fallo que esto persigue: que la etiqueta «SIN FORMA» solo saliera dentro del grupo. Con la
  // finca de verdad, mirar la lista sin agrupar escondería justo el dato que hay que arreglar.
  const html = await htmlDeLasTierras({
    vista: laFincaDeVerdad(),
    mapa: unMapa({ tiene_forma: false, caja: null, url: "" }),
  });

  const etiquetas = (html.match(/SIN FORMA/g) || []).length;
  assert.equal(etiquetas, 64, `hay ${etiquetas} etiquetas «SIN FORMA» y son 64 tierras`);
});

test("el filtro de la revisión no dice «sin revisar» de una tierra que no tiene versión", async () => {
  // Con los datos de verdad, **ninguna** tierra tiene versión de este año, así que la única opción
  // que se puede ofrecer es «Sin ninguna versión de este año». «Sin revisar» afirmaría que alguien
  // miró algo, y no lo ha mirado nadie.
  const html = await htmlDeLasTierras({
    vista: laFincaDeVerdad(),
    mapa: unMapa({ tiene_forma: false, caja: null, url: "" }),
  });

  assert.match(html, /Sin ninguna versión de este año/);
  assert.doesNotMatch(html, /data-valor="sin_revisar"/, "se ofrece «sin revisar» y nadie ha revisado nada");
});

// ---------------------------------------------------------------------------
// 9. Los otros dos hallazgos de los datos de verdad (03/10/2026)
// ---------------------------------------------------------------------------

test("el mismo pueblo escrito de dos formas se filtra y se agrupa como uno solo", async () => {
  // **El caso de verdad**: el cuaderno del agricultor escribe `MACHACON` (como lo escribe la Junta) y
  // la lista oficial dice `Machacón` (con tilde): el mismo pueblo escrito de dos maneras según quién
  // lo escriba. Y hay tierras con dos espacios de más dentro del nombre, de teclearlo a mano. Con el
  // cotejo literal, elegir el pueblo dejaría fuera las tierras escritas de la otra manera y saldrían
  // **dos grupos del mismo pueblo** (el agricultor pensaría que tiene tierras en otro sitio).
  //
  // **(Y aquí se corrigió un dato falso, 03/10/2026.)** Este docstring decía que estaba medido con
  // `CALVARRASA DE ARRIBA` en 54 tierras y `Calvarrasa de Arriba` en 1, y no era verdad: se contaron
  // los 65 registros de toda la base sin separar por explotación. En la finca del agricultor hay 7
  // municipios y ninguno repetido con otra ortografía. **Los datos de abajo son inventados a
  // propósito** (dos formas del mismo pueblo es lo que hay que probar) y el pueblo que se use para
  // escribirlos da igual; lo que el comentario tiene que dejar claro es el motivo, no el ejemplo.
  const { filtrarLasTierras, agruparLasTierras } = await cargarTierras();
  const tierras = [
    unaTierra({ id: 1, municipio: "CALVARRASA DE ARRIBA" }),
    unaTierra({ id: 2, municipio: "CALVARRASA DE ARRIBA" }),
    unaTierra({ id: 3, municipio: "Calvarrasa de Arriba" }),
    unaTierra({ id: 4, municipio: "MACHACON" }),
  ];

  // 1. El filtro deja las tres, se escriba el pueblo como se escriba.
  assert.deepEqual(
    filtrarLasTierras(tierras, { municipio: "CALVARRASA DE ARRIBA" }).map((una) => una.id),
    [1, 2, 3],
  );
  assert.deepEqual(
    filtrarLasTierras(tierras, { municipio: "calvarrasa de ARRIBA" }).map((una) => una.id),
    [1, 2, 3],
  );
  // 2. Y se agrupa en **un solo grupo**, con la forma que más veces está escrita.
  const bloques = agruparLasTierras(tierras, "municipio", TEXTOS);
  const delPueblo = bloques.filter((bloque) => paraBuscarDelGrupo(bloque.titulo) === "calvarrasa de arriba");
  assert.equal(delPueblo.length, 1, `el mismo pueblo sale en ${delPueblo.length} grupos`);
  assert.equal(delPueblo[0].titulo, "CALVARRASA DE ARRIBA", "el título no es la forma más escrita");
  assert.deepEqual(delPueblo[0].tierras.map((una) => una.id), [1, 2, 3]);
  // 3. **Y el nombre de la tierra no se toca**: cada fila sigue enseñando su pueblo tal cual. Sin
  //    agrupar salen las dos formas escritas, cada una en su fila.
  const html = await htmlDeLasTierras({ vista: unaVista({ tierras }), mapa: unMapa() });
  assert.equal(
    (html.match(/CALVARRASA DE ARRIBA/g) || []).length,
    2,
    "las dos tierras escritas en mayúsculas no enseñan su pueblo",
  );
  assert.match(html, /Calvarrasa de Arriba/, "la forma corta ha desaparecido de su fila");
  // Y agrupando, el rótulo del grupo es la forma más escrita y las tres filas caen dentro.
  const agrupado = await htmlDeLasTierras({
    vista: unaVista({ tierras }),
    grupo: "municipio",
    mapa: unMapa(),
  });
  assert.equal((agrupado.match(/CALVARRASA DE ARRIBA/g) || []).length, 3, "el rótulo del grupo no sale");
});

/** El quitador de tildes del componente, para comparar títulos en la prueba de arriba. */
function paraBuscarDelGrupo(texto) {
  return String(texto || "")
    .toLocaleLowerCase("es")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
}

test("dos tierras con el mismo nombre se distinguen, y a la tierra no se le cambia el nombre", async () => {
  // **Medido en los datos de verdad**: hay tierras que se llaman exactamente igual —hasta con la misma
  // superficie—, así que en una tabla con selección el agricultor no puede elegirlas. El programa **no
  // le cambia el nombre a sus tierras**: le dice que está repetido, y el número de la fila (que ya
  // estaba) es lo que le deja elegir una.
  //
  // **En su finca son 59 nombres distintos de 64 tierras** (en toda la base son 60 de 65, porque hay una
  // tierra más en otra explotación, y por eso aquí se dice cuál es cuál). El número se pone con lo que
  // es para que quien lo vuelva a medir y le salga 60 sepa que no se ha equivocado: ha medido otra cosa.
  const elMismo = "507/24-1 TRIGO BLANDO (0.46 ha)";
  const tierras = [
    unaTierra({ id: 1, numero: 1, alias: elMismo, nombre_repetido_texto: "Hay 3 tierras con este mismo nombre." }),
    unaTierra({ id: 2, numero: 2, alias: elMismo, nombre_repetido_texto: "Hay 3 tierras con este mismo nombre." }),
    unaTierra({ id: 3, numero: 3, alias: elMismo, nombre_repetido_texto: "Hay 3 tierras con este mismo nombre." }),
    unaTierra({ id: 4, numero: 4, alias: "507/91-3 AVENA (1 ha)", nombre_repetido_texto: "" }),
  ];
  const html = await htmlDeLasTierras({ vista: unaVista({ tierras }), mapa: unMapa() });

  // El nombre se queda **tal cual**: ni un sufijo, ni un número pegado, ni un «(2)». Se cuentan los
  // botones de la tabla (el nombre también sale en el `title` de su trozo en el mapa, y eso no es una
  // fila).
  const nombres = [...html.matchAll(/class="tabla-enlace"[^>]*>([^<]*)</g)].map((uno) => uno[1]);
  assert.equal(nombres.filter((nombre) => nombre === elMismo).length, 3, "el nombre no sale tres veces");
  assert.equal(nombres.length, 4, `salen ${nombres.length} filas y son 4`);
  assert.doesNotMatch(html, /\(2\)/, "se le ha añadido algo al nombre de sus tierras");
  // Y las tres lo dicen, cada una en su fila.
  assert.equal((html.match(/Hay 3 tierras con este mismo nombre\./g) || []).length, 3);
  // Y se distinguen por su número, que ya estaba en la tabla: 1, 2 y 3.
  const numeros = filasDeLaTabla(html).map((fila) => fila.celdas[1]).filter(Boolean);
  assert.deepEqual(numeros, ["1", "2", "3", "4"]);
});

test("cuando varias tierras comparten el recinto, se encienden todas y se dice cuántas", async () => {
  // **Medido en los datos de verdad**: hay más tierras que referencias distintas, porque el cuaderno
  // de la Junta parte un mismo recinto en varias líneas de cultivo. Al tocar el trozo **no se elige
  // una fila al azar**.
  //
  // **En su finca son 51 referencias distintas de 64 tierras** (en toda la base, 52 de 65: la tierra de
  // más está en otra explotación). Y no es un caso raro: la referencia `37-70-0-0-507-24-1` la comparten
  // **9 tierras** y otra 6. El número va con lo que es, para que quien lo vuelva a medir sepa qué ha
  // medido.
  const { agruparLasTierras } = await cargarTierras();
  const comun = "37-70-0-0-507-24-1";
  const tierras = [
    unaTierra({ id: 1, numero: 1, alias: "507/24-1 TRIGO BLANDO", referencia: comun, clave_recinto: comun }),
    unaTierra({ id: 2, numero: 2, alias: "507/24-1 BARBECHO", referencia: comun, clave_recinto: comun }),
    unaTierra({ id: 3, numero: 3, alias: "507/91-3 AVENA", referencia: "37-70-0-0-507-91-3", clave_recinto: "37-70-0-0-507-91-3" }),
  ];
  assert.equal(agruparLasTierras(tierras, "", TEXTOS).length, 1);

  const html = await htmlDeLasTierras({
    vista: unaVista({ tierras }),
    elegida: 1,
    mismoRecinto: [1, 2],
    mapa: unMapa({ recinto_compartido_texto: "Esta forma la comparten 2 tierras." }),
  });

  // Las dos filas del mismo recinto están encendidas; la otra, no.
  const filas = filasDeLaTabla(html).filter((fila) => fila.clases.includes("tabla-fila-elegida"));
  assert.equal(filas.length, 2, `hay ${filas.length} filas encendidas y son 2`);
  assert.ok(filas[0].celdas.some((celda) => celda.includes("507/24-1 TRIGO BLANDO")));
  assert.ok(filas[1].celdas.some((celda) => celda.includes("507/24-1 BARBECHO")));
  // Y sus dos trozos también (los dos son el mismo polígono, así que se encienden los dos).
  const poligonos = etiquetasCon(html, "polygon", "t06-tierra-elegida");
  assert.equal(poligonos.length, 2, "solo se ha encendido un trozo");
  // Y se dice cuántas son, que es lo que hace que el agricultor lo entienda.
  assert.match(html, /Esta forma la comparten 2 tierras\./);
});

test("una tierra sola no dice nada de recintos compartidos", async () => {
  // La frase solo sale cuando de verdad hay más de una: decirla siempre sería ruido, y el agricultor
  // dejaría de leerla.
  const html = await htmlDeLasTierras({
    vista: unaVista(),
    elegida: 1,
    mismoRecinto: [1],
    mapa: unMapa({ recinto_compartido_texto: "" }),
  });

  assert.doesNotMatch(html, /Esta forma la comparten/);
});

// ---------------------------------------------------------------------------
// 10. Lo que encontró la revisión de T06 (03/10/2026)
// ---------------------------------------------------------------------------

test("las hectáreas que declaras se ven en la fila cuando la tierra no tiene dicha su superficie", async () => {
  // **Hallazgo D1 de la revisión.** La columna «Hectáreas» es la superficie de la tierra —y esa es la
  // regla que usan a la vez la fila, el pie y el filtro—, así que una tierra sin superficie sale con
  // su etiqueta; pero **lo que el agricultor declara ese año no puede quedar invisible**: se enseña
  // debajo, con su nombre, para no mezclar dos magnitudes distintas.
  const tierras = [
    unaTierra({
      id: 1,
      superficie_ha: null,
      superficie_texto: "",
      area_declarada_ha: 2.5,
      tiene_hectareas_dichas: false,
      hectareas_declaradas_texto: "Las que declaras este año: 2,50 ha",
    }),
    unaTierra({ id: 2, superficie_texto: "2,43 ha", area_declarada_ha: null, hectareas_declaradas_texto: "" }),
  ];
  const html = await htmlDeLasTierras({ vista: unaVista({ tierras }), mapa: unMapa() });

  // La fila sigue diciendo que la superficie de la tierra no se sabe…
  assert.match(html, /Sin hectáreas dichas/);
  // …y debajo, con su nombre, lo que sí se sabe.
  assert.match(html, /Las que declaras este año: 2,50 ha/);
  // La otra tierra, que sí tiene superficie, no lleva la pista: no hay nada que aclarar.
  assert.equal((html.match(/Las que declaras este año/g) || []).length, 1);
});

test("cuando la finca no cabe en una imagen, se dice, en vez de culpar a la cobertura", async () => {
  // **Hallazgo D7 de la revisión.** El servicio de mapas no da una caja de más de medio grado: si la
  // finca está repartida en más, la pantalla tiene que decir **eso**, y no dejar que el agricultor
  // lea el aviso de la imagen que no llega («puede ser la cobertura»), que manda a mirar donde no es.
  const html = await htmlDeLasTierras({
    vista: unaVista({ mapa: { hay_forma: true, tierras_con_forma: 2, caja: { oeste: -5.56, sur: 40.9, este: -5.05, norte: 40.9 }, se_puede_ensenar_entera: false } }),
    mapa: unMapa({ no_caben_todas_texto: "Tus tierras están repartidas en más de lo que cabe en una imagen del mapa." }),
  });

  assert.match(html, /Tus tierras están repartidas en más de lo que cabe en una imagen del mapa\./);
  // Y sin ese caso, la frase no sale.
  const normal = await htmlDeLasTierras({ mapa: unMapa({ no_caben_todas_texto: "" }) });
  assert.doesNotMatch(normal, /están repartidas en más de lo que cabe/);
});
