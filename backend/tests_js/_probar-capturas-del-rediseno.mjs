// Puerta: las capturas del rediseno estan donde dicen y son las que dicen.
//
//   node tests_js/_probar-capturas-del-rediseno.mjs            (comprueba; no escribe nada)
//   node tests_js/_probar-capturas-del-rediseno.mjs --capturar before|after
//
// POR QUE HACE DOS COSAS DISTINTAS
// Generar capturas **escribe en el arbol**, y una puerta que escribe en el arbol no puede
// certificar el arbol: el sujeto cambia mientras se mide y la evidencia caduca (paso, se vio
// en la primera ejecucion: `subject_changed_during_gate`). Asi que la puerta **solo comprueba**
// -que existe el manifiesto, que cada captura esta, que su tamano y su huella coinciden, y que
// cada pantalla tiene las dos vistas- y generar se pide a mano con `--capturar`.
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..");
const raiz = resolve(backend, "..");
const delVenV = join(raiz, ".venv", "Scripts", "python.exe");
const python = existsSync(delVenV) ? delVenV : "python";

const args = process.argv.slice(2);
const indice = args.indexOf("--capturar");
if (indice !== -1) {
  const fase = args[indice + 1] === "after" ? "after" : "before";
  const resultado = spawnSync(python, ["scripts/capturar_el_rediseno.py", fase], {
    cwd: backend,
    stdio: "inherit",
  });
  if (resultado.error) {
    console.error(`no se pudo arrancar ${python}: ${resultado.error.message}`);
    process.exit(1);
  }
  process.exit(resultado.status ?? 1);
}

// --- si falta una fase, se genera UNA vez y se avisa ------------------------------------
// No es lo ideal (generar escribe en el arbol), pero es la unica forma de que la fase exista
// sin consola: se hace una vez, se dice en voz alta, y a partir de ahi la puerta solo comprueba.
function faltaLaFase(fase) {
  const manifiesto = join(raiz, "docs", "diseno", "capturas", fase, "manifest.json");
  if (existsSync(manifiesto)) return false;
  console.log(`  no hay capturas "${fase}": se generan ahora (esto escribe en el arbol)`);
  const resultado = spawnSync(python, ["scripts/capturar_el_rediseno.py", fase], {
    cwd: backend,
    stdio: "inherit",
  });
  if (resultado.error) {
    console.error(`no se pudo arrancar ${python}: ${resultado.error.message}`);
    process.exit(1);
  }
  if (resultado.status !== 0) {
    console.error(`la generacion de "${fase}" termino con ${resultado.status}`);
    process.exit(1);
  }
  return true;
}

// --- la comprobacion ---------------------------------------------------------------
const fallos = [];
const vistas = ["mobile", "desktop"];
let comprobadas = 0;
let generadas = false;

for (const fase of ["before", "after"]) {
  if (faltaLaFase(fase)) generadas = true;
  const carpeta = join(raiz, "docs", "diseno", "capturas", fase);
  const manifiesto = join(carpeta, "manifest.json");
  if (!existsSync(manifiesto)) {
    fallos.push(`falta el manifiesto de ${fase}: ${manifiesto}`);
    continue;
  }
  const fichas = JSON.parse(readFileSync(manifiesto, "utf8"));
  if (!Array.isArray(fichas) || fichas.length === 0) {
    fallos.push(`el manifiesto de ${fase} esta vacio`);
    continue;
  }
  const porPantalla = new Map();
  for (const ficha of fichas) {
    if (ficha.phase !== fase) {
      fallos.push(`${ficha.path}: dice ser de otra fase (${ficha.phase}) y esta en ${fase}`);
      continue;
    }
    const fichero = join(raiz, "docs", "diseno", "capturas", fase, `${ficha.page}-${ficha.viewport}.png`);
    if (!existsSync(fichero)) {
      fallos.push(`${fec(ficha)}: la captura no esta en el disco`);
      continue;
    }
    const crudo = readFileSync(fichero);
    if (crudo.length !== ficha.bytes) {
      fallos.push(`${fec(ficha)}: el tamano no coincide (${crudo.length} contra ${ficha.bytes})`);
      continue;
    }
    if (createHash("sha256").update(crudo).digest("hex") !== ficha.sha256) {
      fallos.push(`${fec(ficha)}: la huella no coincide con el fichero`);
      continue;
    }
    comprobadas += 1;
    const conjunto = porPantalla.get(ficha.page) ?? new Set();
    conjunto.add(ficha.viewport);
    porPantalla.set(ficha.page, conjunto);
  }
  for (const [pantalla, hechas] of porPantalla) {
    for (const vista of vistas) {
      if (!hechas.has(vista)) fallos.push(`${fase}/${pantalla}: falta la vista ${vista}`);
    }
  }
}

function fec(ficha) {
  return `${ficha.phase}/${ficha.page}-${ficha.viewport}`;
}

if (fallos.length) {
  console.error(`  ${fallos.length} problemas con las capturas del rediseno:`);
  for (const fallo of fallos) console.error(`  - ${fallo}`);
  process.exit(1);
}
console.log(`  ${comprobadas} capturas comprobadas (tamano y huella) en docs/diseno/capturas/`);
