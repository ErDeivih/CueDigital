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
  calcularTotales,
  decidirEstado,
  filtrarTierras,
  formateaNumero,
  proyeccionDeAnillo,
  proyeccionDePunto,
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
