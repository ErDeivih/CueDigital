// Puerta: la suite de JavaScript completa, de una en una.
//
//   node tests_js/_probar-js.mjs
//
// Equivale a `node --test --test-concurrency=1 tests_js/*.test.js` desde backend/.
// Node expande el patron de glob por si solo; pasarlo entre comillas es lo mismo.
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..");

const resultado = spawnSync(
  process.execPath,
  ["--test", "--test-concurrency=1", "tests_js/*.test.js"],
  { cwd: backend, stdio: "inherit" },
);

if (resultado.error) {
  console.error(`no se pudo arrancar node --test: ${resultado.error.message}`);
  process.exit(1);
}
process.exit(resultado.status ?? 1);
