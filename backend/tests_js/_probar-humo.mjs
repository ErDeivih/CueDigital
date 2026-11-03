// Puerta: el humo contra un servidor temporal de verdad.
//
//   node tests_js/_probar-humo.mjs
//
// Equivale a `../.venv/Scripts/python.exe scripts/andar_el_humo.py` desde backend/.
// Ese andador levanta uvicorn con base y adjuntos temporales y lo tira al terminar.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..");
const delVenV = join(backend, "..", ".venv", "Scripts", "python.exe");
const python = existsSync(delVenV) ? delVenV : "python";

const resultado = spawnSync(python, ["scripts/andar_el_humo.py"], {
  cwd: backend,
  stdio: "inherit",
});

if (resultado.error) {
  console.error(`no se pudo arrancar ${python}: ${resultado.error.message}`);
  process.exit(1);
}
process.exit(resultado.status ?? 1);
