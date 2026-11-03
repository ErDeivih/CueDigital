// Puerta: la suite de Python completa.
//
//   node tests_js/_probar-python.mjs
//
// Equivale a `../.venv/Scripts/python.exe -m pytest -q` desde backend/.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..");
const delVenV = join(backend, "..", ".venv", "Scripts", "python.exe");
const python = existsSync(delVenV) ? delVenV : "python";

const resultado = spawnSync(python, ["-m", "pytest", "-q", "tests/test_aceptacion_copia_y_migracion.py", "tests/test_sesiones_y_limites.py"], {
  cwd: backend,
  stdio: "inherit",
});

if (resultado.error) {
  console.error(`no se pudo arrancar ${python}: ${resultado.error.message}`);
  process.exit(1);
}
process.exit(resultado.status ?? 1);
