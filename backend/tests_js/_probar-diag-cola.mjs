// TEMPORAL: ejecuta el diagnóstico de la cola (se borra cuando se sepa la causa).
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const elBackend = path.resolve(aqui, "..");
const elGuion = path.join(elBackend, "scripts", "diagnostico_de_la_cola_cuentas.py");

const resultado = spawnSync("python", [elGuion], {
  cwd: elBackend,
  stdio: "inherit",
  env: { ...process.env, PYTHONIOENCODING: "utf-8" },
});

process.exit(resultado.status ?? 1);
