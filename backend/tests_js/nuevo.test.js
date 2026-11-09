/**
 * Pruebas del modelo de la interfaz nueva (`/nuevo/`), sin navegador.
 *
 * POR QUÉ ESTAS PRUEBAS
 *
 * La pantalla nueva tiene que decidir cosas que se pueden calcular sin pintar nada: cómo se
 * agrupan las tierras por municipio, cuánto suman, dónde cae el anillo de una tierra dentro de
 * la imagen del mapa, y qué se le enseña al agricultor en cada momento (cargando, sin permiso,
 * sin nada, o la lista). Eso vive en `web/nuevo/modelo.js` y se prueba aquí.
 *
 * Los textos que lee el agricultor se comprueban contra la lista de palabras prohibidas del
 * proyecto (`app/textos.py`), sin copiarla a mano: si mañana se añade una palabra a la lista,
 * esta prueba se entera sola.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { test } from "node:test";

import {
  agruparLoQueFalta,
  agruparPorDias,
  agruparPorMunicipio,
  ajustarBbox,
  avisoDeLaNota,
  avisoSinForma,
  bboxDelConjunto,
  bboxDeMunicipio,
  cajaDeLosRecintos,
  calcularTotales,
  camposInicialesDelSigpac,
  claveDeTipo,
  colorDeTierra,
  colorDeUso,
  comparativaDeAnios,
  cuerpoDeBusquedaPorMunicipio,
  cuerpoDeBusquedaPorReferencia,
  cuerpoDeLaFactura,
  cuerpoDeLaFertilizacion,
  cuerpoDeLaSiembra,
  cuerpoDeLaSiembraDelCuaderno,
  cuerpoDelAbono,
  cuerpoDelApunte,
  cuerpoDelContorno,
  cuerpoDelTratamiento,
  cuentaDeUnaSeccion,
  csvDeTrabajos,
  decidirEstado,
  destinoDeLaSeccion,
  dosisMaximaEnTexto,
  empezarPorLoPrimero,
  empezarPorLoQueBloquea,
  actualizadasDeLosContornos,
  primerBloqueoDeLoQueFalta,
  elAperoSeGuardaEnLabores,
  etiquetaDeProvinciaCache,
  etiquetaDeTrabajo,
  etiquetaDelRecintoEnElMapa,
  fechaDeHoyISO,
  fechaValidezEnTexto,
  faltasRellenables,
  filtrarPorTipo,
  filtrarTierras,
  formateaNumero,
  importeEnTexto,
  leyendaDe,
  lineasDeLosContornos,
  mensajesDeLaRespuesta,
  mesDeNumero,
  mesEnPalabras,
  mesesEnPalabras,
  nombreDeMes,
  normalizaAbonos,
  normalizaAperos,
  normalizaCacheSigpac,
  normalizaCalendario,
  normalizaHistorial,
  normalizaImportacion,
  normalizaMunicipios,
  normalizaProductos,
  normalizaPropuestaDeFactura,
  normalizaSemillas,
  normalizaQueFalta,
  normalizaResumen,
  normalizaTierra,
  normalizaTrabajo,
  normalizaTrabajos,
  numeroDe,
  ordenaLoQueFalta,
  paletaDeUso,
  puedeUsarseElRecinto,
  proyeccionDeAnillo,
  proyeccionDePunto,
  puntoDelMapa,
  queryDeTrabajos,
  recintoElegido,
  recintosConPuntos,
  referenciasDeTexto,
  rejillaDelMes,
  relacionDeTipos,
  resumenDeLoQueFalta,
  seccionesRellenables,
  tecnicasDeLoQueFalta,
  textoDeLasTecnicas,
  puedeAbrirLaTierraActualizada,
  riquezaEnTexto,
  rutaDeAnillo,
  rutaDeLaAplicacion,
  rutaDeLosContornos,
  sinCodigosDeLosContornos,
  sinMapa,
  sumaDeHectareas,
  textos,
  textoDeTotales,
  textoRelleno,
  totalDeLaAplicacion,
  textoDeFaltasSinListar,
  textoDeLasRellenables,
  textoDelAvisoDeBloqueo,
  totalesDeTrabajos,
  urlDeMiniatura,
  urlDelMapa,
  urlDeLaApi,
} from "../web/nuevo/modelo.js";

const AQUI = dirname(fileURLToPath(import.meta.url));

/** Palabras que no pueden salir en pantalla, sacadas de `app/textos.py`. */
function palabrasProhibidas() {
  const ruta = join(AQUI, "..", "app", "textos.py");
  const fuente = readFileSync(ruta, "utf8");
  const bloque = fuente.match(/PALABRAS_PROHIBIDAS[^=]*=\s*[[(]([\s\S]*?)\n[\]\])]/);
  assert.ok(bloque, "no se ha encontrado PALABRAS_PROHIBIDAS en app/textos.py");
  return [...bloque[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
}

function sinTildes(texto) {
  return String(texto)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

const TIERRAS = [
  {
    id: 1,
    alias: "Las Eras",
    municipio: "Cantalapiedra",
    superficie_ha: 12.34,
    uso_sigpac: "Cereal",
    cultivo: { nombre: "Trigo", variedad: "Adelanto" },
    centro: [-5.12, 41.12],
    anillo: [
      [-5.13, 41.11],
      [-5.11, 41.11],
      [-5.11, 41.13],
      [-5.13, 41.13],
    ],
    otros_anios: [],
  },
  {
    id: 2,
    alias: "El Molino",
    municipio: "Cantalapiedra",
    superficie_ha: 8.42,
    uso_sigpac: "Cereal",
    cultivo: null,
    centro: [-5.2, 41.2],
    anillo: null,
    otros_anios: [
      { anio: "2024/2025", cultivo: "Remolacha", superficie_ha: 8.4, variedad: "Belga" },
    ],
  },
  {
    id: 3,
    alias: "La Vega del Rincón",
    municipio: "Peñaranda de Bracamonte",
    superficie_ha: 5.6,
    uso_sigpac: null,
    cultivo: null,
    centro: null,
    anillo: null,
    otros_anios: [],
  },
];

test("las tierras se agrupan por municipio, con su cuenta y su superficie", () => {
  const grupos = agruparPorMunicipio(TIERRAS);

  assert.equal(grupos.length, 2);
  assert.deepEqual(
    grupos.map((g) => g.nombre),
    ["Cantalapiedra", "Peñaranda de Bracamonte"],
  );

  const cantalapiedra = grupos[0];
  assert.equal(cantalapiedra.n, 2);
  assert.equal(cantalapiedra.ha, 20.76);
  assert.deepEqual(
    cantalapiedra.tierras.map((t) => t.alias),
    ["El Molino", "Las Eras"],
  );
});

test("una tierra sin municipio no se pierde: va a su propio grupo", () => {
  const grupos = agruparPorMunicipio([{ id: 9, alias: "Sin papeles", municipio: null }]);

  assert.equal(grupos.length, 1);
  assert.equal(grupos[0].nombre, textos.tierras.sinMunicipio);
  assert.equal(grupos[0].n, 1);
});

test("los totales suman tierras, hectáreas y municipios", () => {
  const totales = calcularTotales(TIERRAS);

  assert.equal(totales.n, 3);
  assert.equal(totales.ha, 26.36);
  assert.equal(totales.municipios, 2);
});

test("si a una tierra le falta la superficie, no se enseña una suma que parece completa", () => {
  const conHueco = [
    ...TIERRAS,
    { id: 4, alias: "Sin superficie", municipio: "Cantalapiedra", superficie_ha: null },
  ];

  const totales = calcularTotales(conHueco);
  assert.equal(totales.n, 4);
  assert.equal(totales.ha, null);

  const grupo = agruparPorMunicipio(conHueco).find((g) => g.nombre === "Cantalapiedra");
  assert.equal(grupo.n, 3);
  assert.equal(grupo.ha, null);
});

test("una tierra sin anillo se dibuja como punto en su centro", () => {
  const bbox = [-5.3, 41, -5, 41.3];
  const punto = proyeccionDePunto(TIERRAS[1].centro, bbox, 100, 100);

  // El centro cae a un tercio del ancho y a un tercio del alto.
  assert.equal(Math.round(punto[0] * 1000), Math.round(((0.1 / 0.3) * 100) * 1000));
  assert.equal(Math.round(punto[1] * 1000), Math.round(((0.1 / 0.3) * 100) * 1000));
  assert.equal(sinMapa(TIERRAS[1]), false);
  assert.equal(sinMapa({ anillo: null, centro: null }), true);
});

test("el anillo se proyecta a la caja del municipio: el sur abajo y el oeste a la izquierda", () => {
  const bbox = [0, 0, 10, 10];
  const esquinas = proyeccionDeAnillo(
    [
      [0, 0],
      [10, 10],
    ],
    bbox,
    200,
    100,
  );

  assert.deepEqual(esquinas[0], [0, 100]); // oeste y sur: abajo a la izquierda
  assert.deepEqual(esquinas[1], [200, 0]); // este y norte: arriba a la derecha
});

test("la ruta del anillo se cierra para poder pintarla", () => {
  const ruta = rutaDeAnillo(TIERRAS[0].anillo, [-5.3, 41, -5, 41.3], 100, 100);

  assert.match(ruta, /^M[\s\S]*Z$/);
  assert.equal(rutaDeAnillo(null, [-5.3, 41, -5, 41.3], 100, 100), null);
});

test("sin token, sin permiso: no se pide nada y se ofrece entrar", () => {
  assert.equal(
    decidirEstado({ conToken: false, cargando: false, fallo: false, sinPermiso: false, hayDatos: true }),
    "sin-permiso",
  );
  assert.equal(
    decidirEstado({ conToken: true, cargando: false, fallo: false, sinPermiso: true, hayDatos: true }),
    "sin-permiso",
  );
});

test("mientras se pregunta, cargando; si no contesta, error", () => {
  assert.equal(
    decidirEstado({ conToken: true, cargando: true, fallo: false, sinPermiso: false, hayDatos: false }),
    "cargando",
  );
  assert.equal(
    decidirEstado({ conToken: true, cargando: false, fallo: true, sinPermiso: false, hayDatos: false }),
    "error",
  );
});

test("sin nada que enseñar es vacío, y con datos es la pantalla", () => {
  assert.equal(
    decidirEstado({ conToken: true, cargando: false, fallo: false, sinPermiso: false, hayDatos: false }),
    "vacio",
  );
  assert.equal(
    decidirEstado({ conToken: true, cargando: false, fallo: false, sinPermiso: false, hayDatos: true }),
    "listo",
  );
});

test("el buscador encuentra por nombre y por municipio, sin importar tildes ni mayúsculas", () => {
  assert.deepEqual(
    filtrarTierras(TIERRAS, "molino").map((t) => t.id),
    [2],
  );
  assert.deepEqual(
    filtrarTierras(TIERRAS, "PEÑARANDA").map((t) => t.id),
    [3],
  );
  assert.deepEqual(
    filtrarTierras(TIERRAS, "penaranda").map((t) => t.id),
    [3],
  );
  assert.equal(filtrarTierras(TIERRAS, "   ").length, 3);
});

test("el zoom conserva el centro y encoge o agranda la caja", () => {
  const bbox = [-10, 0, 10, 10];

  const dentro = ajustarBbox(bbox, 0.5);
  assert.deepEqual(dentro, [-5, 2.5, 5, 7.5]);

  const fuera = ajustarBbox(dentro, 2);
  assert.deepEqual(fuera, [-10, 0, 10, 10]);
});

test("la caja de un municipio se busca por su nombre; «ver todo» une las que hay", () => {
  const municipios = [
    { nombre: "Uno", n: 1, ha: 1, bbox: [0, 0, 1, 1] },
    { nombre: "Dos", n: 1, ha: 1, bbox: [2, 2, 3, 3] },
    { nombre: "Sin forma", n: 1, ha: 1, bbox: null },
  ];

  assert.deepEqual(bboxDeMunicipio(municipios, "Dos"), [2, 2, 3, 3]);
  assert.equal(bboxDeMunicipio(municipios, "Sin forma"), null);
  assert.deepEqual(bboxDelConjunto(municipios), [0, 0, 3, 3]);
});

test("la dirección de la ortofoto lleva la zona y el tamaño", () => {
  const url = urlDelMapa([-5.3, 41, -5, 41.3], 800, 600);
  const parametros = new URL(url, "http://localhost").searchParams;

  assert.equal(parametros.get("capa"), "foto");
  assert.equal(parametros.get("oeste"), "-5.300000");
  assert.equal(parametros.get("sur"), "41.000000");
  assert.equal(parametros.get("este"), "-5.000000");
  assert.equal(parametros.get("norte"), "41.300000");
  assert.equal(parametros.get("ancho"), "800");
  assert.equal(parametros.get("alto"), "600");
});

test("los números y las plantillas salen en castellano", () => {
  assert.equal(formateaNumero(1234.5, 1), "1.234,5");
  assert.equal(formateaNumero(12.34), "12,34");
  assert.equal(formateaNumero(0), "0");
  assert.equal(textoRelleno("{n} tierras · {ha} ha", { n: 3, ha: "12,34" }), "3 tierras · 12,34 ha");
});

test("lo que lee el agricultor no lleva jerga ni palabras de programador", () => {
  const visible = sinTildes(JSON.stringify(textos));

  for (const palabra of palabrasProhibidas()) {
    assert.ok(
      !visible.includes(sinTildes(palabra)),
      `el texto de la pantalla lleva una palabra prohibida: «${palabra}»`,
    );
  }

  for (const tecnica of ["token", "endpoint", "json", "fetch", "null", "undefined", "api"]) {
    assert.ok(
      !visible.includes(sinTildes(tecnica)),
      `el texto de la pantalla habla de cómo está hecho: «${tecnica}»`,
    );
  }
});

test("cada pantalla tiene sus textos, y están todos los estados", () => {
  for (const clave of ["hoy", "tierras", "nav", "comun"]) {
    assert.ok(textos[clave], `falta el bloque de textos «${clave}»`);
  }

  for (const estado of ["cargando", "fallo", "sinPermiso", "vacio", "reintentar", "entrar"]) {
    assert.ok(textos.comun[estado], `falta el texto del estado «${estado}»`);
  }

  assert.ok(textos.tierras.panel.sinOtrosAnios);
  assert.ok(textos.tierras.sinMapa);
  assert.ok(textos.tierras.mapaNoLlega);
  assert.ok(textos.hoy.contadorSinHa, "falta el contador para cuando no consta la superficie");
  assert.ok(textos.tierras.totalesSinHa, "faltan los totales para cuando no consta la superficie");
  assert.ok(textos.tierras.totalesUnoSinHa);
});


// ---------------------------------------------------------------------------
// El alta de tierras: colores del mapa, referencias pegadas y resumen del día
// ---------------------------------------------------------------------------

test("el mapa colorea por uso y la leyenda lleva palabra y cuenta", () => {
  const tierras = [
    { id: 1, uso_sigpac: "Cereal", cultivo: { nombre: "Trigo" } },
    { id: 2, uso_sigpac: "Cereal", cultivo: { nombre: "Cebada" } },
    { id: 3, uso_sigpac: "Olivar", cultivo: null },
    { id: 4, uso_sigpac: null, cultivo: null },
  ];

  const leyenda = leyendaDe(tierras, "uso");
  assert.equal(leyenda[0].valor, "Cereal");
  assert.equal(leyenda[0].n, 2);
  assert.equal(leyenda.find((t) => t.valor === "Olivar").n, 1);

  const sinUso = leyenda.find((t) => t.valor === null);
  assert.equal(sinUso.etiqueta, textos.tierras.sinUso);
  assert.equal(sinUso.color, "var(--ink-muted)");

  // Cada uso tiene su color, y dos usos distintos no se pintan igual.
  assert.equal(colorDeUso("Cereal", 0), paletaDeUso()[0]);
  assert.notEqual(leyenda[0].color, leyenda.find((t) => t.valor === "Olivar").color);
  assert.equal(colorDeTierra(tierras[0], leyenda), leyenda[0].color);
});

test("la leyenda por cultivo usa el cultivo del año; sin cultivo, un hueco con nombre", () => {
  const tierras = [
    { id: 1, uso_sigpac: "Cereal", cultivo: { nombre: "Trigo" } },
    { id: 2, uso_sigpac: "Cereal", cultivo: { nombre: "Trigo" } },
    { id: 3, uso_sigpac: "Olivar", cultivo: null },
  ];

  const leyenda = leyendaDe(tierras, "cultivo");
  assert.equal(leyenda[0].valor, "Trigo");
  assert.equal(leyenda[0].n, 2);
  assert.equal(leyenda.find((t) => t.valor === null).etiqueta, textos.tierras.sinCultivo);
});

test("las referencias pegadas se parten y se limpian", () => {
  const texto = "37:70:0:0:503:51; 37:70:0:0:503:52\n\n 37-70-0-0-503-51 ,, 42.1-2-3 ";
  assert.deepEqual(referenciasDeTexto(texto), [
    "37:70:0:0:503:51",
    "37:70:0:0:503:52",
    "37-70-0-0-503-51",
    "42.1-2-3",
  ]);
  assert.deepEqual(referenciasDeTexto("   "), []);
  assert.deepEqual(referenciasDeTexto(null), []);
});

test("los importes y las tarjetas de resumen salen en castellano", () => {
  assert.equal(importeEnTexto(1234.5), "1.234,5 €");
  assert.equal(importeEnTexto({ total: 987.65 }), "987,65 €");
  assert.equal(importeEnTexto(null), null);
  assert.equal(importeEnTexto(""), null);

  const resumen = normalizaResumen({
    gastos: { total: 1234.5, n: 3 },
    ventas: { importe: 5000, n: 2 },
    cuaderno: { apuntes: 12, sin_cerrar: 1 },
    facturas: { n: 4, total: 312.4 },
  });

  assert.equal(resumen.gastos.importe, "1.234,5 €");
  assert.equal(resumen.gastos.nota, "3 apuntes");
  assert.equal(resumen.ventas.importe, "5.000 €");
  assert.equal(resumen.cuaderno.nota, "1 sin cerrar");
  assert.equal(resumen.facturas.nota, "4 facturas");

  const vacio = normalizaResumen(null);
  assert.equal(vacio.gastos.importe, null);
  assert.equal(vacio.cuaderno.nota, null);
});

test("las tarjetas se leen con lo que manda el servidor de verdad", () => {
  // Lo que devuelve `/api/nuevo/resumen`: importes y pendientes, y lo que falta del cuaderno.
  const resumen = normalizaResumen({
    gastos: { total: 1234.5, pendiente: 120 },
    ventas: { total: 5000, cobrado: 5000, pendiente: 0 },
    cuaderno: { faltan: 3, ejemplos: ["Falta el registro"] },
    facturas: { n: 4 },
  });

  assert.equal(resumen.gastos.importe, "1.234,5 €");
  assert.equal(resumen.gastos.nota, "quedan 120 € por pagar");
  assert.equal(resumen.ventas.nota, "cobrado 5.000 €");
  assert.equal(resumen.cuaderno.nota, "faltan 3 cosas");
  assert.equal(resumen.facturas.nota, "4 facturas");
});

test("«qué falta» se lee con qué falta y dónde se arregla", () => {
  const lista = normalizaQueFalta({
    items: [
      { que: "Falta el número de registro", donde: "Mis datos" },
      { que: "Falta el cultivo de una tierra", donde: "Tierras" },
    ],
  });

  assert.equal(lista.length, 2);
  assert.equal(lista[0].que, "Falta el número de registro");
  assert.equal(lista[0].donde, "Mis datos");

  assert.deepEqual(normalizaQueFalta(null), []);
  assert.deepEqual(normalizaQueFalta({ items: [] }), []);
});

test("lo que se ha importado de un cuaderno se cuenta para poder enseñarlo", () => {
  const deUnaVez = normalizaImportacion({
    leido: { titular: "Ana", anio: 2026, lineas: [{}, {}, {}] },
    importado: { creadas: 3, ya_estaban: 1, sin_apuntar: 0, hectareas_declaradas: 12.5 },
    que_falta: ["Falta el registro"],
  });

  assert.equal(deUnaVez.titular, "Ana");
  assert.equal(deUnaVez.anio, 2026);
  assert.equal(deUnaVez.creadas, 3);
  assert.equal(deUnaVez.yaEstaban, 1);
  assert.equal(deUnaVez.falta.length, 1);

  const sinNada = normalizaImportacion(null);
  assert.equal(sinNada.titular, null);
  assert.equal(sinNada.creadas, null);
});

test("un toque en el mapa se traduce a coordenadas, y al revés", () => {
  const caja = [-5.3, 41, -5, 41.3];
  const punto = puntoDelMapa(400, 300, caja, 800, 600);

  assert.equal(Math.round(punto[0] * 1000) / 1000, -5.15);
  assert.equal(Math.round(punto[1] * 1000) / 1000, 41.15);

  const vuelta = proyeccionDePunto(punto, caja, 800, 600);
  assert.equal(Math.round(vuelta[0]), 400);
  assert.equal(Math.round(vuelta[1]), 300);

  assert.equal(puntoDelMapa(1, 1, null, 800, 600), null);
  assert.equal(puntoDelMapa(1, 1, [0, 1, 0, 1], 800, 600), null);
});


// ---------------------------------------------------------------------------
// La ventana del SIGPAC: los recintos de una búsqueda, dibujados todos
// ---------------------------------------------------------------------------

const RECINTOS_BUSCADOS = [
  {
    recinto: 2,
    referencia: "37:70:0:0:503:51",
    uso: "Cereal",
    puntos: [
      [-5.13, 41.11],
      [-5.11, 41.11],
      [-5.11, 41.13],
      [-5.13, 41.13],
    ],
  },
  { recinto: 3, referencia: "37:70:0:0:503:52", uso: "Pasto", puntos: null },
  {
    recinto: 4,
    referencia: "37:70:0:0:503:53",
    uso: "Olivar",
    puntos: [
      [-5.2, 41.2],
      [-5.1, 41.2],
      [-5.1, 41.3],
    ],
  },
];

test("los recintos de una búsqueda se dibujan todos, cada uno con su color", () => {
  const dibujados = recintosConPuntos(RECINTOS_BUSCADOS);

  assert.equal(dibujados.length, 2);
  assert.deepEqual(
    dibujados.map((recinto) => recinto.recinto),
    [2, 4],
  );
  assert.equal(dibujados[0].color, paletaDeUso()[0]);
  assert.notEqual(dibujados[0].color, dibujados[1].color);
  assert.deepEqual(recintosConPuntos(null), []);
  assert.deepEqual(recintosConPuntos([{ recinto: 9 }]), []);
});

test("el mapa se abre mirando a todos los recintos buscados, no a la finca", () => {
  const caja = cajaDeLosRecintos(recintosConPuntos(RECINTOS_BUSCADOS));

  assert.deepEqual(caja, [-5.2, 41.11, -5.1, 41.3]);

  assert.equal(cajaDeLosRecintos([]), null);
  assert.equal(cajaDeLosRecintos(null), null);

  // Un recinto diminuto no puede dar una caja de lado cero: el servidor no pinta una zona así.
  const diminuta = cajaDeLosRecintos([{ puntos: [[-5, 41], [-5, 41], [-5, 41]] }]);
  assert.ok(diminuta[2] > diminuta[0]);
  assert.ok(diminuta[3] > diminuta[1]);
});

test("el aviso de «sin dibujo» tiene su texto, para no pintar un cuadro que nadie ha medido", () => {
  assert.ok(textos.alta.sinPuntos);
  assert.ok(textos.alta.recintosEnElMapa);
});


// ---------------------------------------------------------------------------
// El trabajo: por día, por tipo, con sus hectáreas y su historial
// ---------------------------------------------------------------------------

const TRABAJOS = [
  { id: 1, tipo: "siembra", fecha: "2026-11-12", parcela_id: 2, superficie_ha: 8.42 },
  {
    id: 2,
    tipo: "labor",
    subtipo: "vertedera",
    fecha: "2026-11-12",
    parcela_id: 1,
    superficie_ha: 12.34,
  },
  {
    id: 3,
    tipo: "abono",
    fecha: "2026-03-14",
    parcela_id: 2,
    kg_ha: 220,
  },
  { id: 4, tipo: "labor", subtipo: "grada", fecha: "2026-03-01", parcela_id: 1 },
];

test("cada trabajo se llama en palabras: siembra, vertedera, grada, abono", () => {
  assert.equal(etiquetaDeTrabajo({ tipo: "siembra" }), "Siembra");
  assert.equal(etiquetaDeTrabajo({ tipo: "labor", subtipo: "vertedera" }), "Vertedera");
  assert.equal(etiquetaDeTrabajo({ tipo: "labor", subtipo: "cultivador" }), "Cultivador");
  assert.equal(etiquetaDeTrabajo({ tipo: "grada" }), "Grada");
  assert.equal(etiquetaDeTrabajo({ tipo: "tratamiento" }), "Tratamiento");
  assert.equal(etiquetaDeTrabajo({}), textos.trabajos.trabajo);
});

test("un trabajo trae su tierra y su municipio aunque solo venga el id", () => {
  const tierras = [{ id: 2, alias: "El Molino", municipio: "Cantalapiedra" }];
  const abono = normalizaTrabajo(TRABAJOS[2], tierras);

  assert.equal(abono.tierra, "El Molino");
  assert.equal(abono.municipio, "Cantalapiedra");
  assert.equal(abono.cantidad, 220);
  assert.equal(abono.unidad, "kg/ha");
  assert.equal(abono.porHectarea, true);
  assert.equal(abono.etiqueta, "Abono");
});

test("los trabajos se agrupan por día, del más nuevo al más viejo", () => {
  const dias = agruparPorDias(TRABAJOS.map((trabajo) => normalizaTrabajo(trabajo)));

  assert.deepEqual(
    dias.map((dia) => dia.fecha),
    ["2026-11-12", "2026-03-14", "2026-03-01"],
  );
  assert.equal(dias[0].n, 2);
});

test("el mes en rejilla empieza en lunes y trae los días que tiene", () => {
  const febrero2026 = rejillaDelMes(2026, 2);
  assert.equal(febrero2026.length % 7, 0);
  assert.deepEqual(
    febrero2026.filter((celda) => celda.delMes).map((celda) => celda.dia),
    Array.from({ length: 28 }, (_, indice) => indice + 1),
  );
  const primero = new Date(2026, 1, 1);
  assert.equal(febrero2026[0].fecha === null || new Date(febrero2026[0].fecha).getDay() === 1, true);
  assert.equal(new Date(primero).getDate(), 1);

  // 2024 fue bisiesto: un test que se fía de febrero no vale para todos los años.
  assert.equal(rejillaDelMes(2024, 2).filter((celda) => celda.delMes).length, 29);
  assert.equal(rejillaDelMes(2026, 2)[0].fecha, null);
});

test("el mes y la fecha se dicen en castellano", () => {
  assert.equal(nombreDeMes(2026, 11), "noviembre de 2026");
  assert.equal(nombreDeMes(2026, 13), "");
  assert.equal(mesEnPalabras("2026-03-14"), "marzo");
  assert.equal(mesEnPalabras(null), "");
});

test("las hectáreas se suman sin mezclarlas con kilos ni litros", () => {
  const resumen = sumaDeHectareas([
    { hectareas: 2.5 },
    { hectareas: null },
    { hectareas: 1 },
    { cantidad: 500, unidad: "kg/ha" },
  ]);

  assert.equal(resumen.ha, 3.5);
  assert.equal(resumen.n, 4);
  assert.equal(resumen.sinSuperficie, 2);
});

test("los filtros por tipo llevan su cuenta, y la vertedera es su propio tipo", () => {
  const normalizados = TRABAJOS.map((trabajo) => normalizaTrabajo(trabajo));
  const tipos = relacionDeTipos(normalizados);

  const vertedera = tipos.find((tipo) => tipo.clave === "labor:vertedera");
  assert.equal(vertedera.etiqueta, "Vertedera");
  assert.equal(vertedera.n, 1);

  assert.equal(filtrarPorTipo(normalizados, "labor:grada").length, 1);
  assert.equal(filtrarPorTipo(normalizados, "labor:vertedera")[0].id, 2);
  assert.equal(filtrarPorTipo(normalizados, null).length, 4);
  assert.equal(claveDeTipo({ tipo: "labor", subtipo: "grada" }), "labor:grada");
});

test("el calendario y la lista de trabajos se leen de lo que manda el servidor", () => {
  const calendario = normalizaCalendario({
    dias: [{ fecha: "2026-11-12", trabajos: [{ id: 1, tipo: "siembra" }] }],
    totales: { dias: 1 },
  });
  assert.equal(calendario.dias.length, 1);
  assert.equal(calendario.dias[0].n, 1);

  const trabajos = normalizaTrabajos({
    tipos: [{ clave: "siembra", etiqueta: "Siembra", n: 1 }],
    elegido: "siembra",
    trabajos: [{ id: 1, tipo: "siembra", superficie_ha: 8.42 }],
  });
  assert.equal(trabajos.elegido, "siembra");
  assert.equal(trabajos.resumen.ha, 8.42);
  assert.equal(trabajos.tipos.length, 1);
});

test("el historial de una tierra se agrupa por años, con sus kg/ha y su mes", () => {
  const historial = normalizaHistorial({
    historial: [
      { anio: 2026, tipo: "abono", fecha: "2026-03-14", kg_ha: 220, producto: "Nitrato" },
      { anio: 2025, tipo: "siembra", cultivo: "Trigo", variedad: "Adelanto", fecha: "2025-11-03" },
    ],
  });

  assert.deepEqual(
    historial.map((anio) => anio.anio),
    ["2026", "2025"],
  );
  const abono = historial[0].filas[0];
  assert.equal(abono.etiqueta, "Abono");
  assert.ok(abono.detalles.some((detalle) => detalle.includes("kg/ha")));
  assert.ok(abono.detalles.includes("marzo"));
  assert.ok(historial[1].filas[0].detalles.includes("Adelanto"));
});

test("la ficha de la tierra junta lo de hoy y el historial", () => {
  const ficha = normalizaTierra(
    {
      trabajo_de_hoy: [{ id: 1, tipo: "siembra", fecha: "2026-11-12" }],
      historial: [{ anio: 2025, tipo: "cosecha", kg_ha: 4900 }],
    },
    [],
  );
  assert.equal(ficha.trabajoDeHoy.length, 1);
  assert.equal(ficha.historial.length, 1);
});

test("la propuesta de factura se revisa y se guarda con los campos del servidor", () => {
  const propuesta = normalizaPropuestaDeFactura({
    proveedor: "  Ferretería El Páramo ",
    proveedor_nif: "B00000000",
    numero_factura: "2026/00123",
    fecha: "2026-02-18",
    base_imponible: 312.4,
    cuota_iva: 65.6,
    total: 378,
    lineas: [{ descripcion: "Herbicida", cantidad: 2, unidad: "L", precio_unitario: 15.5, importe: 31 }],
    avisos: [],
  });

  assert.equal(propuesta.total, 378);
  assert.equal(propuesta.fecha, "2026-02-18");
  assert.equal(propuesta.lineas.length, 1);

  const cuerpo = cuerpoDeLaFactura({ ...propuesta, proveedor: "  Ferretería  ", lineas: [...propuesta.lineas, { descripcion: "" }] });
  assert.equal(cuerpo.proveedor, "Ferretería");
  assert.equal(cuerpo.lineas.length, 1);
  assert.equal(cuerpo.lineas[0].precio_unitario, 15.5);
});

test("las cuatro pantallas nuevas tienen sus textos y sus cuatro estados", () => {
  for (const bloque of ["tierra", "calendario", "trabajos", "facturas", "mas"]) {
    assert.ok(textos[bloque], `falta el bloque de textos «${bloque}»`);
  }
  assert.ok(textos.tierra.historial);
  assert.ok(textos.calendario.sinNada);
  assert.ok(textos.trabajos.noDisponible);
  assert.ok(textos.facturas.noSeLeyo);
  assert.ok(textos.facturas.fotosDeMas);
});

test("el historial del servidor viene por años y por secciones, y se lee entero", () => {
  const historial = normalizaHistorial({
    historial: [
      {
        anio: 2026,
        cultivo: "Trigo",
        variedad: "Adelanto",
        superficie_ha: 12.3,
        siembra: { fecha: "2025-11-03", cultivo: "Trigo", variedad: "Adelanto", dosis_semilla_kg_ha: 210 },
        labores: [{ fecha: "2026-02-10", labor: "vertedera", titulo: "Vertedera", mes: "febrero" }],
        tratamientos: [{ fecha: "2026-04-02", producto: "Herbicida X", dosis: 2, dosis_unidad: "L/ha" }],
        abonos: [{ fecha: "2026-03-14", mes: "marzo", producto: "Nitrato", kg: 2700, kg_ha: 220 }],
        cosecha: { fecha: "2026-07-20", kg_ha: 4900 },
      },
      {
        anio: 2025,
        cultivo: "Cebada",
        variedad: null,
        superficie_ha: 12.3,
        siembra: null,
        labores: [],
        tratamientos: [],
        abonos: [],
        cosecha: null,
      },
    ],
  });

  const del2026 = historial[0];
  assert.equal(del2026.anio, "2026");
  assert.equal(del2026.cultivo, "Trigo");
  assert.equal(del2026.variedad, "Adelanto");
  assert.equal(del2026.filas.length, 5);

  const etiquetas = del2026.filas.map((fila) => fila.etiqueta);
  for (const esperada of ["Siembra", "Vertedera", "Tratamiento", "Abono", "Cosecha"]) {
    assert.ok(etiquetas.includes(esperada), `falta «${esperada}»: ${etiquetas.join(", ")}`);
  }

  const abono = del2026.filas.find((fila) => fila.etiqueta === "Abono");
  assert.ok(abono.detalles.some((detalle) => detalle.includes("220 kg/ha")));
  assert.ok(abono.detalles.includes("marzo"));

  const siembra = del2026.filas.find((fila) => fila.etiqueta === "Siembra");
  assert.ok(siembra.detalles.includes("Trigo"));
  assert.ok(siembra.detalles.some((detalle) => detalle.includes("210 kg/ha")));

  // Un año sin apuntes no se inventa con filas: se queda con su cultivo y sin lista.
  assert.equal(historial[1].filas.length, 0);
});

test("las filas de trabajos del servidor traen su clave, su alias y su municipio", () => {
  const datos = normalizaTrabajos(
    {
      tipos: [
        { clave: "abono", etiqueta: "Abono", n: 1 },
        { clave: "labor:vertedera", etiqueta: "Vertedera", n: 1 },
      ],
      elegido: "labor:vertedera",
      trabajos: [
        {
          fecha: "2026-03-14",
          tipo: "labor:vertedera",
          titulo: "Vertedera",
          tierra_id: 2,
          tierra_alias: "El Molino",
          municipio: "Cantalapiedra",
          hectareas: 8.42,
          cantidad: 220,
          unidad: "kg/ha",
          por_hectarea: true,
        },
      ],
    },
    [{ id: 2, alias: "El Molino" }],
  );

  const fila = datos.trabajos[0];
  assert.equal(fila.etiqueta, "Vertedera");
  assert.equal(fila.tierra, "El Molino");
  assert.equal(fila.municipio, "Cantalapiedra");
  assert.equal(fila.cantidad, 220);
  assert.equal(fila.porHectarea, true);
  assert.equal(claveDeTipo(fila), "labor:vertedera");
  assert.equal(datos.tipos.length, 2);
});


// ---------------------------------------------------------------------------
// Apuntar el trabajo del día desde la tierra
// ---------------------------------------------------------------------------

test("los aperos salen del servidor y no se inventan", () => {
  const deLaLista = normalizaAperos({ subtipos_de_laboreo: ["arado", "grada", "otro"] });
  assert.deepEqual(
    deLaLista.map((apero) => apero.clave),
    ["arado", "grada", "otro"],
  );
  assert.equal(deLaLista[0].etiqueta, "Arado");

  assert.deepEqual(normalizaAperos({ aperos: [{ clave: "rodillo", etiqueta: "Rodillo" }] }), [
    { clave: "rodillo", etiqueta: "Rodillo" },
  ]);
  // Sin lista del servidor no se rellena con aperos inventados: la pantalla dirá que no hay.
  assert.deepEqual(normalizaAperos(null), []);
  assert.deepEqual(normalizaAperos({}), []);
});

test("la fecha de hoy y el cuerpo del apunte son los que entiende el servidor", () => {
  assert.equal(fechaDeHoyISO(new Date(2026, 10, 5)), "2026-11-05");
  assert.equal(fechaDeHoyISO(new Date(2026, 0, 1)), "2026-01-01");

  const cuerpo = cuerpoDelApunte({
    campanaId: 3,
    apero: "grada",
    fecha: "2026-11-05",
    tierraId: 7,
    hectareas: "12,5",
    nota: "  ",
  });
  assert.deepEqual(cuerpo, {
    campana_id: 3,
    tipo: "laboreo",
    subtipo: "grada",
    fecha: "2026-11-05",
    parcela_id: 7,
    superficie_ha: 12.5,
    observaciones: null,
  });

  // Sin fecha se pone la de hoy y sin hectáreas queda «no consta», no un cero.
  const minimo = cuerpoDelApunte({ campanaId: 3, apero: "otro", tierraId: 7 });
  assert.equal(minimo.fecha, fechaDeHoyISO());
  assert.equal(minimo.superficie_ha, null);
  assert.equal(minimo.observaciones, null);
});

test("con «otro» apero se pide la nota, sin bloquear el apunte", () => {
  assert.equal(avisoDeLaNota("otro", ""), textos.apuntar.faltaNota);
  assert.equal(avisoDeLaNota("otro", "   "), textos.apuntar.faltaNota);
  assert.equal(avisoDeLaNota("otro", "Puse el tubo"), null);
  assert.equal(avisoDeLaNota("grada", ""), null);
});

test("la miniatura del contorno y la puerta que guarda el apero", () => {
  assert.equal(urlDeMiniatura(7), "/api/mapa/tierra/7.png?ancho=160&alto=120");
  assert.equal(urlDeMiniatura(12, 320, 240), "/api/mapa/tierra/12.png?ancho=320&alto=240");

  // La puerta de siempre todavía no admite el apero: se usa la que sí lo guarda, no se pierde.
  const sinSubtipo = { components: { schemas: { LaborEntrada: { properties: { tipo: {}, fecha: {} } } } } };
  const conSubtipo = { components: { schemas: { LaborEntrada: { properties: { subtipo: {} } } } } };
  assert.equal(elAperoSeGuardaEnLabores(sinSubtipo), false);
  assert.equal(elAperoSeGuardaEnLabores(conSubtipo), true);
  assert.equal(elAperoSeGuardaEnLabores(null), false);
});

test("la pantalla de apuntar tiene sus textos y sus estados", () => {
  for (const clave of ["titulo", "tierra", "que", "fecha", "hectareas", "nota", "guardar", "guardado", "noSeGuardo", "faltaNota", "sinTierra", "sinAperos", "cargando", "noDisponible", "guardarImagen"]) {
    assert.ok(textos.apuntar[clave], `falta el texto «${clave}» de apuntar`);
  }
  assert.ok(textos.apuntar.guardarImagen);
});

test("el mes del historial puede venir en número y se lee en palabras", () => {
  assert.equal(mesDeNumero(3), "marzo");
  assert.equal(mesDeNumero("11"), "noviembre");
  assert.equal(mesDeNumero(13), "");
  assert.equal(mesDeNumero(null), "");

  const historial = normalizaHistorial({
    historial: [
      {
        anio: 2026,
        labores: [{ fecha: "2026-11-05", labor: "grada", titulo: "Grada", mes: 11, detalle: null }],
      },
    ],
  });
  assert.ok(historial[0].filas[0].detalles.includes("noviembre"));
});


// ---------------------------------------------------------------------------
// Productos, abonos y dosis por hectárea
// ---------------------------------------------------------------------------

test("los productos y los abonos se leen del servidor, con su dosis y su riqueza", () => {
  const productos = normalizaProductos({
    productos: [
      { id: 1, nombre_comercial: "Herbicida X", materia_activa: "Glifosato", dosis_maxima: 3, unidad_dosis: "L/ha", plazo_seguridad_dias: 7 },
      { id: 2, nombre_comercial: "Sin dosis" },
    ],
  });
  assert.equal(productos.length, 2);
  assert.equal(productos[0].nombre, "Herbicida X");
  assert.equal(productos[0].materiaActiva, "Glifosato");
  assert.equal(productos[0].dosisMaxima, 3);
  assert.equal(productos[0].unidad, "L/ha");
  assert.equal(dosisMaximaEnTexto(productos[0]), "3 L/ha");
  assert.equal(dosisMaximaEnTexto(productos[1]), null);

  const abonos = normalizaAbonos({
    fertilizantes: [
      { id: 9, nombre: "Nitrato amónico", tipo: "simple", riqueza_n: 27, riqueza_p: null, riqueza_k: null },
    ],
  });
  assert.equal(abonos[0].nombre, "Nitrato amónico");
  assert.equal(riquezaEnTexto(abonos[0]), "N 27 %");
  assert.equal(riquezaEnTexto({ n: null, p: null, k: null }), null);
  assert.deepEqual(normalizaProductos(null), []);
  assert.deepEqual(normalizaAbonos({ fertilizantes: [] }), []);
});

test("la dosis por hectárea se multiplica por las hectáreas, sin mezclar kilos y litros", () => {
  assert.deepEqual(totalDeLaAplicacion(1.5, 12, "L/ha"), { cantidad: 18, unidad: "L" });
  assert.deepEqual(totalDeLaAplicacion(200, 12.5, "kg/ha"), { cantidad: 2500, unidad: "kg" });

  // Una dosis que ya es un total no se multiplica: no se inventa una cuenta.
  assert.deepEqual(totalDeLaAplicacion(30, 12, "kg"), { cantidad: 30, unidad: "kg" });

  // Sin hectáreas no hay total que enseñar, y sin dosis tampoco.
  assert.equal(totalDeLaAplicacion(1.5, null, "L/ha"), null);
  assert.equal(totalDeLaAplicacion(1.5, 0, "L/ha"), null);
  assert.equal(totalDeLaAplicacion(null, 12, "L/ha"), null);

  assert.equal(rutaDeLaAplicacion("producto"), "/api/tratamientos");
  assert.equal(rutaDeLaAplicacion("abono"), "/api/fertilizaciones");
});

test("los cuerpos del tratamiento y del abono son los que espera el servidor", () => {
  const tratamiento = cuerpoDelTratamiento({
    campanaId: 4,
    tierraId: 7,
    fecha: "2026-11-05",
    productoId: 1,
    dosis: 1.5,
    unidadDosis: "L/ha",
    hectareas: 12.5,
  });
  assert.deepEqual(tratamiento, {
    campana_id: 4,
    tipo: "parcela",
    fecha: "2026-11-05",
    parcela_id: 7,
    producto_id: 1,
    dosis: 1.5,
    unidad_dosis: "L/ha",
    superficie_tratada_ha: 12.5,
    plaga: null,
    justificacion: null,
    observaciones: null,
  });

  const abono = cuerpoDeLaFertilizacion({
    campanaId: 4,
    tierraId: 7,
    fecha: "2026-11-05",
    fertilizanteId: 9,
    hectareas: "12,5",
    dosisPorHa: 200,
  });
  assert.equal(abono.superficie_ha, 12.5);
  assert.equal(abono.kg_ha_producto, 200);
  assert.equal(abono.cantidad_total_kg, 2500);
  assert.equal(abono.unidad_del_producto, "kg");
  assert.equal(cuerpoDelTratamiento({ productoId: 1 }).fecha, fechaDeHoyISO());
});

test("lo que falta del cuaderno se agrupa por dónde se arregla y se dice si bloquea", () => {
  const secciones = agruparLoQueFalta([
    { que: "Falta el NIF", donde: "Mis datos", bloquea: true },
    { que: "Falta el teléfono", donde: "Mis datos", bloquea: false },
    { que: "Falta el cultivo de una tierra", donde: "Mis parcelas", bloquea: false },
  ]);

  assert.equal(secciones.length, 2);
  // Primero la sección que el agricultor puede rellenar en `/nuevo/`; «Mis datos» no tiene
  // pantalla nueva y se queda detrás, aunque bloquee.
  assert.equal(secciones[0].donde, "Mis parcelas");
  assert.equal(secciones[0].n, 1);
  assert.equal(secciones[0].bloquea, false);
  assert.equal(secciones[1].donde, "Mis datos");
  assert.equal(secciones[1].n, 2);
  assert.equal(secciones[1].bloquea, true);

  assert.deepEqual(agruparLoQueFalta(null), []);
  assert.deepEqual(agruparLoQueFalta([{ que: "" }]), []);

  // Y desde la respuesta del servidor: el aviso de lo que bloquea no se pierde por el camino.
  const deLaPuerta = normalizaQueFalta({
    items: [
      { que: "Falta el NIF", donde: "Mis datos", bloquea: true },
      { que: "Falta el teléfono", donde: "Mis datos", bloquea: false },
    ],
  });
  const delServidor = agruparLoQueFalta(deLaPuerta);
  assert.equal(delServidor[0].bloquea, true);
  assert.equal(delServidor[0].items[0].bloquea, true);
});

test("el cuaderno guiado y los productos tienen sus textos y sus estados", () => {
  for (const clave of ["titulo", "intro", "faltan", "faltaUna", "completo", "bloquea", "arreglar", "abrirJv", "cargando", "noDisponible"]) {
    assert.ok(textos.cuaderno[clave], `falta el texto «${clave}» del cuaderno`);
  }
  for (const clave of ["titulo", "productos", "abonos", "buscar", "dosisMaxima", "total", "aplicar", "guardar", "guardado", "noSeGuardo", "cargando", "noDisponible", "sinProductos", "sinAbonos", "sinDosis", "sinSuperficie", "verTrabajo"]) {
    assert.ok(textos.productos[clave], `falta el texto «${clave}» de productos`);
  }
  for (const clave of ["eligeTierra", "verCalendario", "verTrabajos", "verHoy", "verDelDia"]) {
    assert.ok(textos.siguiente[clave], `falta el texto «${clave}» del siguiente paso`);
  }
});

test("los avisos que el servidor escribe se leen en palabras de agricultor", () => {
  assert.deepEqual(
    mensajesDeLaRespuesta({
      detail: {
        puede_guardarse: false,
        avisos: [
          { codigo: "V1_sin_registro", mensaje: "Ese número de etiqueta no nos suena." },
          { codigo: "V2", mensaje: "  " },
        ],
      },
    }),
    ["Ese número de etiqueta no nos suena."],
  );
  assert.deepEqual(mensajesDeLaRespuesta({ detail: "No se puede guardar." }), ["No se puede guardar."]);
  assert.deepEqual(mensajesDeLaRespuesta({ detail: { mensaje: "Falta la dosis." } }), ["Falta la dosis."]);
  assert.deepEqual(mensajesDeLaRespuesta(null), []);
  assert.deepEqual(mensajesDeLaRespuesta({ detail: { avisos: [] } }), []);
});


// ---------------------------------------------------------------------------
// Comparar años, totales del calendario y bajar lo filtrado
// ---------------------------------------------------------------------------

test("los meses de abono se dicen en palabras, sin repetir y en orden", () => {
  assert.equal(mesesEnPalabras([3, 5]), "marzo, mayo");
  assert.equal(mesesEnPalabras(["mayo", 3, 3]), "marzo, mayo");
  assert.equal(mesesEnPalabras([11]), "noviembre");
  assert.equal(mesesEnPalabras([]), "");
  assert.equal(mesesEnPalabras(null), "");
});

test("los totales por unidad no mezclan kilos con litros", () => {
  const totales = totalesDeTrabajos([
    { hectareas: 10, cantidad: 200, unidad: "kg/ha" },
    { hectareas: 15.5, cantidad: 20, unidad: "kg/ha" },
    { hectareas: 2, cantidad: 30, unidad: "L/ha" },
    { hectareas: null, cantidad: null, unidad: null },
  ]);

  assert.equal(totales.n, 4);
  assert.equal(totales.hectareas, 27.5);
  assert.equal(totales.sinSuperficie, 1);
  assert.deepEqual(totales.porUnidad, [
    { unidad: "kg/ha", cantidad: 220 },
    { unidad: "L/ha", cantidad: 30 },
  ]);
  assert.equal(textoDeTotales(totales), "4 trabajos · 27,5 ha · 220 kg/ha · 30 L/ha");
  assert.equal(textoDeTotales({ n: 1, hectareas: 0, porUnidad: [] }), "1 trabajo");
});

test("la comparativa de años usa el resumen del servidor y, si no viene, lo cuenta", () => {
  const conResumen = comparativaDeAnios([
    {
      anio: "2026",
      cultivo: "Trigo",
      variedad: "Adelanto",
      superficie_ha: 12.5,
      resumen: { n_labores: 4, abonos_kg_ha: 220, abonos_meses: [3, 5], cosecha_kg_ha: 4900 },
      filas: [],
    },
  ]);
  assert.deepEqual(conResumen[0], {
    anio: "2026",
    cultivo: "Trigo",
    variedad: "Adelanto",
    superficie_ha: 12.5,
    abonoKgHa: 220,
    meses: "marzo, mayo",
    cosechaKgHa: 4900,
    labores: 4,
  });

  // Sin resumen se cuenta de las filas del año; lo que no consta se queda en null.
  const sinResumen = comparativaDeAnios([
    {
      anio: "2025",
      filas: [
        { tipo: "abono", cantidad: 180, unidad: "kg/ha", mes: 3, fecha: "2025-03-10" },
        { tipo: "abono", cantidad: 40, unidad: "kg/ha", mes: "mayo", fecha: "2025-05-02" },
        { tipo: "labor", etiqueta: "Grada" },
        { tipo: "cosecha", cantidad: 4600, unidad: "kg/ha" },
      ],
    },
  ]);
  assert.equal(sinResumen[0].abonoKgHa, 220);
  assert.equal(sinResumen[0].meses, "marzo, mayo");
  assert.equal(sinResumen[0].cosechaKgHa, 4600);
  assert.equal(sinResumen[0].labores, 1);
  assert.equal(sinResumen[0].superficie_ha, null);

  assert.deepEqual(comparativaDeAnios([]), []);
});

test("la dirección de los trabajos se compone con los filtros que hay", () => {
  assert.equal(queryDeTrabajos({}), "/api/nuevo/trabajos");
  assert.equal(queryDeTrabajos({ tipo: "laboreo" }), "/api/nuevo/trabajos?tipo=laboreo");
  assert.equal(
    queryDeTrabajos({ tipo: "laboreo", tierraId: 3, desde: "2026-01-01", hasta: "2026-06-30" }),
    "/api/nuevo/trabajos?tipo=laboreo&parcela_id=3&desde=2026-01-01&hasta=2026-06-30",
  );
  assert.equal(queryDeTrabajos({ tierraId: 7 }), "/api/nuevo/trabajos?parcela_id=7");
});

test("el CSV de lo filtrado lleva sus columnas y escapa lo que molesta", () => {
  const csv = csvDeTrabajos([
    {
      fecha: "2026-11-05",
      tipo: "laboreo",
      etiqueta: "Grada",
      tierra: "Las Eras",
      municipio: "Cantalapiedra",
      hectareas: 12.5,
      cantidad: 220,
      unidad: "kg/ha",
      porHectarea: true,
    },
    {
      fecha: "2026-11-06",
      tipo: "siembra",
      etiqueta: "Siembra; trigo",
      tierra: 'El "Molino"',
      municipio: null,
      hectareas: null,
      cantidad: null,
      unidad: null,
      porHectarea: false,
    },
  ]);

  const lineas = csv.trimEnd().split("\n");
  assert.equal(lineas[0], "fecha;tipo;título;tierra;municipio;hectáreas;cantidad;unidad;por hectárea");
  assert.equal(lineas[1], "2026-11-05;laboreo;Grada;Las Eras;Cantalapiedra;12,5;220;kg/ha;sí");
  assert.equal(lineas[2], '2026-11-06;siembra;"Siembra; trigo";"El ""Molino""";;;;;');
  assert.ok(csv.endsWith("\n"));
});


// ---------------------------------------------------------------------------
// La ventana del SIGPAC: buscar y usar la parcela
// ---------------------------------------------------------------------------

test("los municipios del INE se leen para el autocompletado, con su provincia", () => {
  const municipios = normalizaMunicipios({
    municipios: [
      { nombre: "Peñaranda de Bracamonte", provincia: "Salamanca", codigo_municipio: "70", codigo_provincia: "37" },
      { nombre: "" },
    ],
  });
  assert.equal(municipios.length, 1);
  assert.equal(municipios[0].nombre, "Peñaranda de Bracamonte");
  assert.equal(municipios[0].codigoMunicipio, "70");
  assert.equal(municipios[0].etiqueta, "Peñaranda de Bracamonte · Salamanca");
  assert.deepEqual(normalizaMunicipios(null), []);
});

test("se busca por la referencia pegada o por el pueblo elegido de la lista", () => {
  assert.deepEqual(cuerpoDeBusquedaPorReferencia("37:70:0:0:503:51"), { referencia: "37:70:0:0:503:51" });
  assert.deepEqual(cuerpoDeBusquedaPorReferencia("  37:70:0:0:503:51\n37:70:0:0:503:52 "), {
    referencia: "37:70:0:0:503:51",
  });
  assert.equal(cuerpoDeBusquedaPorReferencia("   "), null);

  const elegido = { nombre: "Peñaranda de Bracamonte", provincia: "Salamanca" };
  assert.deepEqual(
    cuerpoDeBusquedaPorMunicipio({ elegido, agregado: "0", zona: "", poligono: "5", parcela: "12" }),
    { municipio: "Peñaranda de Bracamonte", provincia: "Salamanca", agregado: 0, zona: 0, poligono: 5, parcela: 12 },
  );
  // Escribir el pueblo a mano no vale: hace falta el de la lista.
  assert.equal(cuerpoDeBusquedaPorMunicipio({ elegido: null, poligono: "5", parcela: "12" }), null);
  assert.equal(cuerpoDeBusquedaPorMunicipio({ elegido, poligono: "", parcela: "12" }), null);
});

test("el recinto elegido y su forma deciden si se puede usar", () => {
  const recintos = [
    { recinto: 2, referencia: "37:70:0:0:503:51", puntos: [[-5, 41], [-5, 41.1], [-5.1, 41.1]] },
    { recinto: 3, referencia: "37:70:0:0:503:52", tiene_dibujo: true },
    { recinto: 4, referencia: "37:70:0:0:503:53", tiene_dibujo: false },
  ];
  assert.equal(recintoElegido(recintos, 2).referencia, "37:70:0:0:503:51");
  assert.equal(recintoElegido(recintos, "3").recinto, 3);
  assert.equal(recintoElegido(recintos, 9), null);

  assert.equal(puedeUsarseElRecinto(recintos[0]), true);
  assert.equal(puedeUsarseElRecinto(recintos[1]), true);
  assert.equal(puedeUsarseElRecinto(recintos[2]), false);
  assert.equal(puedeUsarseElRecinto(null), false);
  assert.equal(avisoSinForma(recintos[2]), textos.ventana.sinForma);
  assert.equal(avisoSinForma(recintos[0]), null);

  // Para aplicar a una tierra va la referencia y **el número del recinto**, para no coger «el que salga».
  assert.deepEqual(cuerpoDelContorno(recintos[0]), { referencia: "37:70:0:0:503:51", recinto: 2 });
  assert.equal(cuerpoDelContorno(null), null);
});

test("la ventana del SIGPAC tiene sus textos", () => {
  for (const clave of ["titulo", "cerrar", "porReferencia", "porMunicipio", "municipio", "poligono", "parcela", "buscar", "usar", "sinForma", "anadida", "aplicada", "noSePudo"]) {
    assert.ok(textos.ventana[clave], `falta el texto «${clave}» de la ventana`);
  }
});


// ---------------------------------------------------------------------------
// Apuntar del día a día: labor, tratamiento, abono y siembra
// ---------------------------------------------------------------------------

test("las semillas del servidor se leen con su variedad y su dosis", () => {
  const semillas = normalizaSemillas({
    semillas: [
      { id: 5, nombre: "Trigo", variedad: "Adelanto", especie: "Trigo", dosis_recomendada_por_ha: 210, unidad_dosis: "kg/ha" },
      { id: 6, nombre: "" },
    ],
  });
  assert.equal(semillas.length, 1);
  assert.equal(semillas[0].variedad, "Adelanto");
  assert.equal(semillas[0].dosisRecomendada, 210);
  assert.deepEqual(normalizaSemillas(null), []);
});

test("el cuerpo de la siembra con semilla es el que espera el servidor", () => {
  const cuerpo = cuerpoDeLaSiembra({
    tierraId: 7,
    fecha: "2026-11-07",
    semillaId: 5,
    dosisPorHa: 210,
    hectareas: 12.5,
    nota: "  ",
  });
  assert.deepEqual(cuerpo, {
    semilla_id: 5,
    parcela_id: 7,
    fecha: "2026-11-07",
    superficie_ha: 12.5,
    dosis_por_ha: 210,
    unidad_dosis: "kg/ha",
    notas: null,
  });
  assert.equal(cuerpoDeLaSiembra({}).fecha, fechaDeHoyISO());
});

test("sin semillas se apunta la siembra del cuaderno, sin inventar ninguna", () => {
  const cuerpo = cuerpoDeLaSiembraDelCuaderno({
    campanaId: 4,
    tierraId: 7,
    fecha: "2026-11-07",
    cultivo: "Trigo",
    variedad: "Adelanto",
    dosisKgHa: 210,
    hectareas: 12.5,
    nota: "Sembrado con la sembradora del vecino",
  });
  assert.equal(cuerpo.tipo, "siembra");
  assert.equal(cuerpo.cultivo, "Trigo");
  assert.equal(cuerpo.variedad, "Adelanto");
  assert.equal(cuerpo.dosis_siembra_kg_ha, 210);
  assert.equal(cuerpo.cantidad_semilla_kg, 2625);
  assert.equal(cuerpo.superficie_ha, 12.5);
  assert.ok(cuerpo.observaciones);
  // Si no hay cultivo se queda en blanco, no se rellena con nada.
  assert.equal(cuerpoDeLaSiembraDelCuaderno({}).cultivo, null);
});

test("el abono se apunta por hectárea o en kilos totales, nunca las dos cosas", () => {
  const porHectarea = cuerpoDelAbono({
    campanaId: 4,
    tierraId: 7,
    fecha: "2026-11-07",
    fertilizanteId: 9,
    modo: "por_hectarea",
    dosisPorHa: 200,
    hectareas: 12.5,
  });
  assert.equal(porHectarea.kg_ha_producto, 200);
  assert.equal(porHectarea.cantidad_total_kg, 2500);
  assert.equal(porHectarea.unidad_del_producto, "kg");

  const total = cuerpoDelAbono({
    campanaId: 4,
    tierraId: 7,
    fecha: "2026-11-07",
    fertilizanteId: 9,
    modo: "total",
    kilosTotales: 2500,
    hectareas: 12.5,
  });
  assert.equal(total.cantidad_total_kg, 2500);
  assert.equal("kg_ha_producto" in total, false, "en modo total no se manda la dosis por hectárea");
});

test("el tratamiento lleva su plaga y su nota, y la siembra su total", () => {
  const cuerpo = cuerpoDelTratamiento({
    campanaId: 4,
    tierraId: 7,
    fecha: "2026-11-07",
    productoId: 1,
    dosis: 1.5,
    unidadDosis: "L/ha",
    hectareas: 12.5,
    plaga: "Avena loca",
    justificacion: "Vi pulgón",
    nota: "Con la cuba llena",
  });
  assert.equal(cuerpo.plaga, "Avena loca");
  assert.equal(cuerpo.justificacion, "Vi pulgón");
  assert.equal(cuerpo.observaciones, "Con la cuba llena");
  assert.equal(totalDeLaAplicacion(1.5, 12.5, "L/ha").cantidad, 18.75);
});

test("la vista de apuntar tiene sus cuatro pestañas y sus textos", () => {
  for (const pestana of ["pestanaLabor", "pestanaTratamiento", "pestanaAbono", "pestanaSiembra"]) {
    assert.ok(textos.apuntar[pestana], `falta la pestaña «${pestana}»`);
  }
  assert.ok(textos.apuntar.producto.guardar);
  assert.ok(textos.apuntar.abono.kilosTotales);
  assert.ok(textos.apuntar.siembra.sinSemillas);
  assert.ok(textos.apuntar.siembra.delCuaderno);
});

// ---------------------------------------------------------------------------
// Los contornos de toda la finca desde la ventana del SIGPAC
// ---------------------------------------------------------------------------

test("la caché de mapas del SIGPAC se lee sin inventar provincias", () => {
  assert.deepEqual(normalizaCacheSigpac(null), { cuantas: 0, provincias: [], atribucion: "", licencia: "" });
  const estado = normalizaCacheSigpac({
    cuantas: 1,
    atribucion: "FEGA",
    licencia: "CC BY 4.0 — FEGA",
    provincias: [
      { provincia: 37, nombre_provincia: "Salamanca", campana: 2025, fecha_validez: "2025-09-01", licencia: "CC BY 4.0 — FEGA" },
      { nombre_provincia: "Sin código" },
    ],
  });
  assert.equal(estado.cuantas, 1);
  assert.equal(estado.provincias.length, 1);
  assert.equal(estado.provincias[0].nombre, "Salamanca");
  assert.equal(estado.provincias[0].campana, 2025);
  assert.equal(estado.provincias[0].fechaValidez, "2025-09-01");
  assert.equal(estado.atribucion, "FEGA");
});

test("la provincia del mapa se enseña con su campaña y su validez", () => {
  assert.equal(fechaValidezEnTexto("2025-09-01"), "01/09/2025");
  assert.equal(fechaValidezEnTexto(""), "");
  assert.equal(fechaValidezEnTexto("no es una fecha"), "");
  assert.equal(
    etiquetaDeProvinciaCache({ provincia: 37, nombre: "Salamanca", campana: 2025, fechaValidez: "2025-09-01" }),
    "Salamanca · 2025 · válido hasta 01/09/2025",
  );
  assert.equal(etiquetaDeProvinciaCache({ provincia: 37 }), "Provincia 37");
  assert.equal(etiquetaDeProvinciaCache(null), "");
});

test("la dirección de los contornos es la del contrato y no se inventa", () => {
  assert.equal(rutaDeLosContornos(37, 2025), "/api/sigpac/cache/37/contornos?campana=2025");
  assert.equal(rutaDeLosContornos("37", null), "/api/sigpac/cache/37/contornos");
  assert.equal(rutaDeLosContornos(0, 2025), null);
  assert.equal(rutaDeLosContornos(53, 2025), null);
  assert.equal(rutaDeLosContornos("", 2025), null);
});

test("el resultado de los contornos se cuenta en singular y en plural", () => {
  assert.deepEqual(lineasDeLosContornos({ actualizadas: [{ id: 1 }], no_encontradas: [], sin_codigos: [], sin_forma: [] }), ["1 contorno puesto"]);
  assert.deepEqual(
    lineasDeLosContornos({
      actualizadas: [{ id: 1 }, { id: 2 }],
      no_encontradas: [{ id: 3 }],
      sin_codigos: [{ id: 4 }, { id: 5 }],
      sin_forma: [{ id: 6 }],
    }),
    ["2 contornos puestos", "1 tierra que no está en ese mapa", "2 tierras sin códigos del SIGPAC", "1 tierra sin forma"],
  );
  assert.deepEqual(lineasDeLosContornos({}), [textos.ventana.cache.nadaQueCasar]);
});

test("las tierras sin códigos del SIGPAC salen con su nombre y su motivo, sin inventarlo", () => {
  assert.deepEqual(sinCodigosDeLosContornos(null), []);
  assert.deepEqual(sinCodigosDeLosContornos({}), []);
  assert.deepEqual(sinCodigosDeLosContornos({ sin_codigos: "no es una lista" }), []);

  const tierras = sinCodigosDeLosContornos({
    sin_codigos: [
      {
        id: 3,
        alias: "La de dos trozos",
        motivo: "la referencia no dice el recinto y esa parcela tiene 2 recintos; elige uno",
      },
      { id: 4, alias: "A mano" },
      { id: 5 },
      "no es una tierra",
    ],
  });
  assert.deepEqual(tierras, [
    {
      id: 3,
      alias: "La de dos trozos",
      motivo: "la referencia no dice el recinto y esa parcela tiene 2 recintos; elige uno",
    },
    { id: 4, alias: "A mano", motivo: null },
    { id: 5, alias: textos.ventana.cache.tierraSinNombre, motivo: null },
  ]);
});

test("el resumen de los contornos lleva el motivo y no repite la frase", () => {
  const elMismo = "la referencia no dice el recinto y esa parcela tiene 2 recintos; elige uno";
  assert.deepEqual(
    lineasDeLosContornos({
      actualizadas: [],
      no_encontradas: [],
      sin_forma: [],
      sin_codigos: [
        { id: 1, motivo: elMismo },
        { id: 2, motivo: elMismo },
        { id: 3, motivo: "su municipio no está en el catálogo oficial" },
      ],
    }),
    [
      `2 tierras sin códigos del SIGPAC · ${elMismo}`,
      "1 tierra sin códigos del SIGPAC · su municipio no está en el catálogo oficial",
    ],
  );
  // El motivo ausente no se rellena con nada: se dice solo la cuenta, como siempre.
  assert.deepEqual(
    lineasDeLosContornos({ sin_codigos: [{ id: 1 }, { id: 2 }] }),
    ["2 tierras sin códigos del SIGPAC"],
  );
});

test("la ventana del SIGPAC tiene las palabras para elegir el recinto", () => {
  assert.equal(textos.ventana.cache.elegirRecinto, "Elegir el recinto en el SIGPAC");
  assert.ok(textos.ventana.cache.sinCodigosTitulo, "falta el título de la lista de las que no se pudieron poner");
  assert.equal(textos.ventana.cache.sinCodigosConMotivo, "{cuantas} · {motivo}");
});

// ---------------------------------------------------------------------------
// El cuaderno guiado y el recinto tocado en el mapa
// ---------------------------------------------------------------------------

test("el resumen del cuaderno cuenta lo que falta y lo que bloquea, sin inventar", () => {
  assert.deepEqual(resumenDeLoQueFalta(null), { faltan: 0, bloquean: 0 });
  const items = [
    { que: "a", donde: "Mis datos", bloquea: false },
    { que: "b", donde: "Tierras", bloquea: true },
    { que: "c", donde: "Trabajos", bloquea: true },
  ];
  assert.deepEqual(resumenDeLoQueFalta(items), { faltan: 3, bloquean: 2 });
});

test("cada sección del cuaderno dice «1 cosa» o «3 cosas»", () => {
  assert.equal(cuentaDeUnaSeccion(1), "1 cosa");
  assert.equal(cuentaDeUnaSeccion(3), "3 cosas");
  assert.equal(cuentaDeUnaSeccion(0), "0 cosas");
});

test("«Empezar por lo primero» va a lo que bloquea y, si no, al primer destino", () => {
  const paso = empezarPorLoPrimero([
    { que: "a", donde: "Mis datos → tu finca", bloquea: false },
    { que: "b", donde: "Tierras", bloquea: true },
  ]);
  assert.equal(paso.destino, "tierras");
  assert.equal(paso.item.que, "b");

  assert.equal(empezarPorLoPrimero([{ que: "x", donde: "Sin sitio" }, { que: "y", donde: "Trabajos" }]).destino, "calendario");
  assert.equal(empezarPorLoPrimero([{ que: "x", donde: "Sin sitio" }]), null);
  assert.equal(empezarPorLoPrimero([]), null);

  // El destino se decide por el nombre de la sección, y lo que no se sabe no se inventa.
  assert.equal(destinoDeLaSeccion("Mis tierras"), "tierras");
  assert.equal(destinoDeLaSeccion("Productos y abonos"), "productos");
  assert.equal(destinoDeLaSeccion("Lo que no se sabe"), null);
});

test("el recinto del mapa se nombra con lo que se sabe y lo que no consta se dice", () => {
  assert.equal(
    etiquetaDelRecintoEnElMapa({ recinto: 51, uso: "Cereal", superficie_ha: 1.2 }),
    "Recinto 51 · Cereal · 1,2 ha",
  );
  assert.equal(
    etiquetaDelRecintoEnElMapa({ recinto: 7 }),
    `Recinto 7 · ${textos.tierras.panel.noConsta} · ${textos.tierras.panel.noConsta}`,
  );
});

// ---------------------------------------------------------------------------
// El aviso de lo que bloquea el cuaderno
// ---------------------------------------------------------------------------

test("lo que bloquea va delante sin revolver el orden de lo demás", () => {
  const items = [
    { que: "a", donde: "Uno", bloquea: false },
    { que: "b", donde: "Uno", bloquea: true },
    { que: "c", donde: "Dos", bloquea: false },
    { que: "d", donde: "Dos", bloquea: true },
    { que: "e", donde: "Tres" },
  ];
  assert.deepEqual(ordenaLoQueFalta(items).map((item) => item.que), ["b", "d", "a", "c", "e"]);
  assert.deepEqual(ordenaLoQueFalta(null), []);
  assert.deepEqual(ordenaLoQueFalta([{ que: "" }]), []);

  // Y dentro de cada sección, igual: primero lo que bloquea.
  const secciones = agruparLoQueFalta(items);
  assert.deepEqual(secciones[0].items.map((item) => item.que), ["b", "a"]);
  assert.deepEqual(secciones[1].items.map((item) => item.que), ["d", "c"]);
});

test("el aviso de lo que bloquea se cuenta en singular y en plural", () => {
  assert.equal(textoDelAvisoDeBloqueo(1), "Hay 1 cosa que impide presentar el cuaderno.");
  assert.equal(textoDelAvisoDeBloqueo(3), "Hay 3 cosas que impiden presentar el cuaderno.");
  assert.equal(textoDelAvisoDeBloqueo(0), "Hay 0 cosas que impiden presentar el cuaderno.");
});

test("si el servidor cuenta más faltas de las que se ven, se dice", () => {
  assert.equal(textoDeFaltasSinListar(2, 40), "Faltan 40 cosas y aquí se ven 2. Las demás no se han podido mirar; vuelve a intentarlo.");
  assert.equal(textoDeFaltasSinListar(40, 40), null);
  assert.equal(textoDeFaltasSinListar(41, 40), null);
  assert.equal(textoDeFaltasSinListar(null, 40), null);
  assert.equal(textoDeFaltasSinListar(2, null), null);
});

test("«Empezar por lo que bloquea» solo va a lo que bloquea y tiene pantalla", () => {
  const items = [
    { que: "a", donde: "Sin sitio", bloquea: true },
    { que: "b", donde: "Trabajos", bloquea: false },
    { que: "c", donde: "Tierras", bloquea: true },
  ];
  const paso = empezarPorLoQueBloquea(items);
  assert.equal(paso.destino, "tierras");
  assert.equal(paso.item.que, "c");
  assert.equal(empezarPorLoQueBloquea([{ que: "b", donde: "Trabajos", bloquea: false }]), null);
  assert.equal(empezarPorLoQueBloquea([{ que: "a", donde: "Sin sitio", bloquea: true }]), null);
  assert.equal(empezarPorLoQueBloquea([]), null);
});

// ---------------------------------------------------------------------------
// «Lo primero» del cuaderno y las tierras que actualiza el SIGPAC
// ---------------------------------------------------------------------------

test("las secciones que se pueden rellenar salen antes que las técnicas, sin revolver el orden", () => {
  const secciones = agruparLoQueFalta([
    { que: "a", donde: "Sin sitio", bloquea: true },
    { que: "b", donde: "Mis parcelas", bloquea: false },
    { que: "c", donde: "Quien desarrolla", bloquea: true },
    { que: "d", donde: "Trabajos", bloquea: false },
  ]);
  assert.deepEqual(secciones.map((seccion) => seccion.donde), [
    "Mis parcelas",
    "Trabajos",
    "Sin sitio",
    "Quien desarrolla",
  ]);
});

test("«lo primero» se sabe aunque no tenga pantalla en la app nueva", () => {
  const conPantalla = primerBloqueoDeLoQueFalta([
    { que: "Falta el libro", donde: "Tierras", bloquea: false },
    { que: "Falta el número de registro", donde: "Tierras", bloquea: true },
  ]);
  assert.equal(conPantalla.item.que, "Falta el número de registro");
  assert.equal(conPantalla.destino, "tierras");

  const sinPantalla = primerBloqueoDeLoQueFalta([{ que: "Falta el certificado", donde: "Quien desarrolla", bloquea: true }]);
  assert.equal(sinPantalla.item.que, "Falta el certificado");
  assert.equal(sinPantalla.destino, null);

  assert.equal(primerBloqueoDeLoQueFalta([{ que: "Otra cosa", donde: "Tierras", bloquea: false }]), null);
  assert.equal(primerBloqueoDeLoQueFalta(null), null);
});

test("las tierras actualizadas se leen con lo que viene y sin inventar", () => {
  assert.deepEqual(actualizadasDeLosContornos(null), []);
  assert.deepEqual(actualizadasDeLosContornos({ actualizadas: [] }), []);
  assert.deepEqual(actualizadasDeLosContornos({ actualizadas: "no es una lista" }), []);

  const tierras = actualizadasDeLosContornos({
    actualizadas: [
      { id: 7, alias: "Las Eras", superficie_ha: 1.2, municipio: "Salamanca" },
      { parcela_id: 8, alias: "El Molino" },
      { id: 9, alias: "" },
      "no es una tierra",
    ],
  });
  assert.equal(tierras.length, 3);
  assert.deepEqual(tierras[0], { id: 7, alias: "Las Eras", detalle: "1,2 ha · Salamanca" });
  assert.deepEqual(tierras[1], { id: 8, alias: "El Molino", detalle: "" });
  assert.equal(tierras[2].alias, textos.ventana.cache.tierraSinNombre);
  assert.equal(tierras[2].detalle, "");
});

// ---------------------------------------------------------------------------
// La tierra que ya sabe la ventana del SIGPAC y las faltas que se rellenan aquí
// ---------------------------------------------------------------------------

test("la ventana del SIGPAC aprovecha lo que la tierra ya tiene, sin inventar", () => {
  const soloReferencia = camposInicialesDelSigpac({ id: 1, alias: "Las Eras", ref_sigpac: "37:70:0:0:503:51" });
  assert.equal(soloReferencia.referencia, "37:70:0:0:503:51");
  assert.equal(soloReferencia.municipio, "");
  assert.equal(soloReferencia.poligono, "");
  assert.equal(soloReferencia.recinto, "");

  const conCodigos = camposInicialesDelSigpac({
    id: 2,
    municipio: "Penaranda de Bracamonte",
    provincia: "Salamanca",
    agregado: 0,
    zona: 0,
    poligono: 12,
    numero_parcela: 34,
    numero_recinto: 7,
  });
  assert.equal(conCodigos.referencia, "");
  assert.equal(conCodigos.poligono, "12");
  assert.equal(conCodigos.parcela, "34");
  assert.equal(conCodigos.municipio, "Penaranda de Bracamonte");
  assert.equal(conCodigos.provincia, "Salamanca");
  assert.equal(conCodigos.recinto, "7");
  assert.equal(conCodigos.agregado, "0");

  // Los datos del servidor (la ficha de la parcela) mandan sobre la lista.
  const delServidor = camposInicialesDelSigpac(
    { id: 3, municipio: "Viejo" },
    { ref_sigpac: "37:70:0:0:1:2", municipio: "Nuevo", provincia: "Salamanca", numero_recinto: 9 },
  );
  assert.equal(delServidor.referencia, "37:70:0:0:1:2");
  assert.equal(delServidor.municipio, "Nuevo");
  assert.equal(delServidor.recinto, "9");

  assert.deepEqual(camposInicialesDelSigpac(null), {
    referencia: "",
    agregado: "",
    zona: "",
    poligono: "",
    parcela: "",
    municipio: "",
    provincia: "",
    recinto: "",
  });
});

test("el cuaderno cuenta las faltas que se pueden rellenar aquí, con la misma función de destinos", () => {
  const items = [
    { que: "a", donde: "Tierras", bloquea: true },
    { que: "b", donde: "Trabajos", bloquea: false },
    { que: "c", donde: "Productos y abonos", bloquea: false },
    { que: "d", donde: "Quien desarrolla la aplicación", bloquea: true },
    { que: "", donde: "Tierras" },
  ];
  assert.equal(faltasRellenables(items), 3);
  assert.equal(faltasRellenables([]), 0);
  assert.equal(faltasRellenables(null), 0);

  assert.equal(textoDeLasRellenables(3), "Puedes rellenar 3 de ellas aquí.");
  assert.equal(textoDeLasRellenables(1), "Puedes rellenar 1 de ellas aquí.");
  assert.equal(textoDeLasRellenables(0), "Ninguna de ellas se rellena desde aquí.");
});


test("el filtro deja fuera solo las secciones tecnicas y no inventa el total", () => {
  const secciones = agruparLoQueFalta([
    { que: "a", donde: "Tierras", bloquea: true },
    { que: "b", donde: "Quien desarrolla la aplicacion", bloquea: true },
    { que: "c", donde: "Trabajos", bloquea: false },
  ]);
  const visibles = seccionesRellenables(secciones);
  assert.deepEqual(visibles.map((s) => s.donde), ["Tierras", "Trabajos"]);
  assert.equal(tecnicasDeLoQueFalta([
    { que: "a", donde: "Tierras" },
    { que: "b", donde: "Quien desarrolla la aplicacion" },
    { que: "c", donde: "FEGA" },
  ]), 2);
  assert.equal(textoDeLasTecnicas(2), "2 quedan fuera: dependen de la aplicación o de la Junta.");
  assert.equal(textoDeLasTecnicas(1), "1 queda fuera: depende de la aplicación o de la Junta.");
  assert.equal(textoDeLasTecnicas(0), "");
});

test("cada tierra pintada se abre solo si el padre deja abrirla", () => {
  assert.equal(puedeAbrirLaTierraActualizada({ id: 7 }, () => {}), true);
  assert.equal(puedeAbrirLaTierraActualizada({ id: 7 }, null), false);
  assert.equal(puedeAbrirLaTierraActualizada({ id: 7 }, undefined), false);
  assert.equal(puedeAbrirLaTierraActualizada({}, () => {}), false);
  assert.equal(puedeAbrirLaTierraActualizada(null, () => {}), false);
  assert.equal(puedeAbrirLaTierraActualizada({ parcela_id: 9 }, () => {}), true);
});


/**
 * El front puede publicarse aparte del servidor (GitHub Pages llamando al servidor de casa).
 * `urlDeLaApi` es lo que decide si una ruta lleva delante el dominio de la API o no.
 */
test("sin dominio configurado, la ruta se queda como esta (lo normal)", () => {
  delete globalThis.CUEDIGITAL_API;
  assert.equal(urlDeLaApi("/api/nuevo/hoy"), "/api/nuevo/hoy");
  assert.equal(urlDeLaApi(""), "");
});

test("con el servidor apuntado, las rutas de la API llevan su dominio", () => {
  globalThis.CUEDIGITAL_API = "https://servidor.example/";
  assert.equal(urlDeLaApi("/api/nuevo/hoy"), "https://servidor.example/api/nuevo/hoy");
  assert.equal(urlDeLaApi("api/nuevo/tierras"), "https://servidor.example/api/nuevo/tierras");
  // Una direccion que ya trae dominio no se toca dos veces.
  assert.equal(urlDeLaApi("https://otro.example/x"), "https://otro.example/x");
  delete globalThis.CUEDIGITAL_API;
});

test("la barra final del servidor no duplica la barra de la ruta", () => {
  globalThis.CUEDIGITAL_API = "https://servidor.example///";
  assert.equal(
    urlDeLaApi("/api/mapa/tierra/1.png"),
    "https://servidor.example/api/mapa/tierra/1.png"
  );
  delete globalThis.CUEDIGITAL_API;
});
