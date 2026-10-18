import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");

/*
 * la_ficha_de_la_maquina.test.js — **la forma del objeto que prepara `unaMaquinaPreparada`**.
 *
 * POR QUE EXISTE ESTA PRUEBA (15/10/2026)
 *
 * `lecturas` y `contador` se escribieron **dentro del `map` de averias**, asi que se colgaban de **cada
 * averia** y en una maquina **sin averias desaparecian**. El sintoma parecia una cache fantasma -la
 * seccion no se pintaba y todo lo demas estaba en orden- y costo **nueve rondas** de diagnostico.
 * ***La sangria no cambia el alcance: la llave cierra donde cierra.***
 *
 * Por eso se invoca la **funcion de verdad**, extraida de `web/app.js`, y no una copia de su forma: si
 * alguien la mueve de sitio, la prueba lo ve. Los ayudantes de formato se sustituyen por un saco que
 * devuelve texto vacio, porque aqui **solo importan las llaves**, no los rotulos.
 */

const APP = process.env.CUEDIGITAL_APP_JS || join(RAIZ, "web", "app.js");

/** Extrae del fichero el texto de una funcion del nivel exterior, de `function x(` a la siguiente. */
function extraeLaFuncion(nombre) {
  const lineas = readFileSync(APP, "utf8").split("\n");
  const i = lineas.findIndex((l) => l.startsWith("function " + nombre + "("));
  assert.ok(i >= 0, "no encuentro `" + nombre + "` en el nivel exterior de " + APP);
  let j = i + 1;
  while (j < lineas.length && !/^(async )?function /.test(lineas[j])) j += 1;
  return { fuente: lineas.slice(i, j).join("\n"), linea: i + 1 };
}

/**
 * La funcion real, con un saco de ayudantes de mentira para todo nombre libre.
 *
 * `encima` deja **sustituir algunos** -por ejemplo `t`, para poder comprobar **que frase** se elige y no
 * solo que la funcion devuelve algo-.
 */
function laFuncionDeVerdad(nombre, encima) {
  const { fuente, linea } = extraeLaFuncion(nombre);
  const ayudantes = new Proxy(
    {},
    {
      // ***LOS GLOBALES DE VERDAD SE DEJAN PASAR*** (16/10/2026). Con `has: () => true` a secas, el
      // saco tapaba tambien `Number`, `Boolean` y compania: `Number.isFinite(...)` se convertia en una
      // llamada a una funcion de mentira y la prueba fallaba por el arnes, no por el codigo.
      has: (_, clave) => !(clave in globalThis),
      get: (_, clave) =>
        encima && Object.prototype.hasOwnProperty.call(encima, clave) ? encima[clave] : () => "",
    },
  );
  // `with` va en modo no estricto: el cuerpo de `new Function` lo es mientras no diga lo contrario.
  const fabrica = new Function("ayudantes", "with (ayudantes) { return (" + fuente + "); }");
  const suya = fabrica(ayudantes);
  assert.equal(typeof suya, "function", "no he podido montar `" + nombre + "` (linea " + linea + ")");
  return suya;
}

/** Una ficha como la manda el servidor, con lo minimo para que la funcion no tropiece. */
function unaFicha(cambios) {
  return Object.assign(
    {
      maquina: { id: 1, nombre: "El Landini", clase: "tractor" },
      obligaciones: [],
      inspecciones: [],
      averias: [],
      avisos: [],
      lecturas: [],
      contador: { subido: 250, cuantas: 2, sin_decir: 0, unidad: "horas", marca: 1250, lo_que_falta: [] },
    },
    cambios || {},
  );
}

const UNA_AVERIA = { id: 7, fecha: "2026-04-01", que_paso: "Se rompio el eje del ventilador" };

test("la ficha lleva el cuenta-horas en el nivel EXTERIOR, y tambien sin averias", () => {
  const prepara = laFuncionDeVerdad("unaMaquinaPreparada");

  const sinAverias = prepara(unaFicha());
  assert.ok("lecturas" in sinAverias, "sin averias, `lecturas` tiene que seguir en el objeto exterior");
  assert.ok("contador" in sinAverias, "sin averias, `contador` tiene que seguir en el objeto exterior");
  assert.equal(sinAverias.contador.marca, 1250, "y con su dato, no perdido por el camino");
  assert.deepEqual(sinAverias.lecturas, []);
});

test("***una averia NO lleva el cuenta-horas dentro***", () => {
  const prepara = laFuncionDeVerdad("unaMaquinaPreparada");

  const conUna = prepara(unaFicha({ averias: [UNA_AVERIA] }));

  assert.equal(conUna.averias.length, 1, "la averia sigue estando");
  assert.ok("lecturas" in conUna, "y el cuenta-horas sigue siendo de la MAQUINA");
  assert.ok("contador" in conUna, "y el cuenta-horas sigue siendo de la MAQUINA");
  assert.ok(
    !("lecturas" in conUna.averias[0]),
    "***una averia no lleva `lecturas`: eso fue el fallo de las nueve rondas***",
  );
  assert.ok(
    !("contador" in conUna.averias[0]),
    "***una averia no lleva `contador`: eso fue el fallo de las nueve rondas***",
  );
});


/*
 * EL CUENTA-HORAS DE LA PANTALLA: `elCuentaHorasDeLaMaquina`
 *
 * La revision del 16/10/2026 reprodujo que con **1.200 -> 1.000** el servidor ya senalaba la incoherencia
 * y la **pantalla** devolvia «Ha subido: 0 h» **sin aviso**: un cero calculado sobre tramos que no
 * cuadran pasaba por dato acreditado, y la incidencia se quedaba en el tintero.
 *
 * Aqui se invoca la funcion real y se comprueba **que frase elige**, sustituyendo `t` por una marca que
 * lleva el nombre de la clave: asi la prueba dice QUE palabra se uso, no solo que hay algo.
 */

const PALABRAS = () => new Proxy({}, { get: (_, clave) => "[" + String(clave) + "]" });

function elCuentaDeVerdad() {
  return laFuncionDeVerdad("elCuentaHorasDeLaMaquina", {
    textosDeLaMaquinaria: () => ({ maquinaria: PALABRAS() }),
    t: (clave) => "[" + String(clave) + "]",
    rellena: (plantilla, datos) => plantilla + " " + JSON.stringify(datos || {}),
  });
}

test("***un cero NO se presenta como total acreditado cuando hay tramos incoherentes***", () => {
  const elCuenta = elCuentaDeVerdad();

  const suyo = elCuenta({
    subido: 0,
    cuantas: 2,
    sin_decir: 0,
    cobertura_incompleta: true,
    incoherentes: [
      {
        desde: "2026-01-01",
        hasta: "2026-02-01",
        subido: -200,
        motivo: "una_lectura_va_para_atras_sin_sustitucion",
      },
    ],
    unidad: "horas",
    marca: 1000,
    tramos: [],
    lo_que_falta: ["una_lectura_va_para_atras_sin_sustitucion"],
  });

  assert.ok(
    suyo.subido_texto.includes("contador_ha_subido_parcial"),
    "el subtotal tiene que ir con la banda: «de lo que se puede afirmar»",
  );
  assert.ok(
    !suyo.subido_texto.includes("[contador_ha_subido]"),
    "***y NO como si fuera el total acreditado***",
  );
  assert.ok(
    suyo.incidencias_texto.includes("contador_va_para_atras"),
    "***la incidencia se ENSENA: callarla era el fallo***",
  );
  assert.equal(suyo.cobertura_incompleta, true);
  assert.ok(suyo.subido_texto.includes("0 h"), "la cifra se sigue ensenando, pero con su banda");
});

test("y cuando todo cuadra se dice el total, sin banda ni incidencias", () => {
  const elCuenta = elCuentaDeVerdad();

  const suyo = elCuenta({
    subido: 250,
    cuantas: 2,
    sin_decir: 0,
    cobertura_incompleta: false,
    incoherentes: [],
    unidad: "horas",
    marca: 1250,
    tramos: [],
    lo_que_falta: [],
  });

  assert.ok(suyo.subido_texto.includes("[contador_ha_subido]"), "la frase del total");
  assert.ok(!suyo.subido_texto.includes("parcial"), "sin banda");
  assert.equal(suyo.incidencias_texto, "", "y sin incidencias que ensenar");
  assert.equal(suyo.noSeSabeTexto, "");
});

test("***una unidad desconocida no se llama horas, ni se inventa un cero***", () => {
  const elCuenta = elCuentaDeVerdad();

  const suyo = elCuenta({
    subido: null,
    cuantas: 2,
    sin_decir: 0,
    cobertura_incompleta: true,
    incoherentes: [],
    unidad: null,
    marca: null,
    tramos: [],
    lo_que_falta: ["las_lecturas_no_son_de_la_misma_unidad"],
  });

  assert.equal(suyo.subido_texto, "", "***ni «0 h» ni ninguna otra cifra***");
  assert.ok(suyo.noSeSabeTexto.includes("contador_unidades_distintas"), "y se dice por que no se sabe");
});
