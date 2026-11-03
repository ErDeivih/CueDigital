// Puerta: todos los recorridos reales, cada uno con su servidor temporal.
//
//   node tests_js/_probar-recorridos.mjs
//
// Equivale a `../.venv/Scripts/python.exe scripts/verificar_todos_los_recorridos.py`
// desde backend/.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..");
const delVenV = join(backend, "..", ".venv", "Scripts", "python.exe");
const python = existsSync(delVenV) ? delVenV : "python";

const resultado = spawnSync(python, ["scripts/verificar_todos_los_recorridos.py"], {
  cwd: backend,
  stdio: "inherit",
});

if (resultado.error) {
  console.error(`no se pudo arrancar ${python}: ${resultado.error.message}`);
  process.exit(1);
}
process.exit(resultado.status ?? 1);
