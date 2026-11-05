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
  agruparPorMunicipio,
  ajustarBbox,
  bboxDelConjunto,
  bboxDeMunicipio,
  cajaDeLosRecintos,
  calcularTotales,
  colorDeTierra,
  colorDeUso,
  decidirEstado,
  filtrarTierras,
  formateaNumero,
  importeEnTexto,
  leyendaDe,
  normalizaImportacion,
  normalizaQueFalta,
  normalizaResumen,
  paletaDeUso,
  proyeccionDeAnillo,
  proyeccionDePunto,
  puntoDelMapa,
  recintosConPuntos,
  referenciasDeTexto,
  rutaDeAnillo,
  sinMapa,
  textos,
  textoRelleno,
  urlDelMapa,
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
