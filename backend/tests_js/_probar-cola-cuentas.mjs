// Puerta de diagnóstico: la cola sin conexión no cruza cuentas.
//
//   node backend/tests_js/_probar-cola-cuentas.mjs
//
// Corre `scripts/verificar_que_la_cola_no_cruza_cuentas.py` y devuelve su código.
// Existe para poder ver la salida literal (las líneas `[FALLO]` con su `encontre`)
// sin tener que ejecutar los 188 recorridos completos.
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..");
const guion = join(backend, "scripts", "verificar_que_la_cola_no_cruza_cuentas.py");

const resultado = spawnSync("python", [guion], {
  cwd: backend,
  stdio: "inherit",
  env: { ...process.env, PYTHONIOENCODING: "utf-8" },
});
process.exit(resultado.status ?? 1);
