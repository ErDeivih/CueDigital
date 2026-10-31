// Puerta de D01: ejecuta el diagnóstico publicado de la revisión del 23/10/2026.
//
//   node docs/revision-2026-10-19/_probar-cola.mjs
//
// Corre las dos formas del guion —la normal y `--concurrencia`— y falla si cualquiera
// de las dos sale con código distinto de 0. El guion ya es una regresión: sus
// aserciones dicen la propiedad que tiene que cumplir la cola.
import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const raiz = join(aqui, "..", "..");
const guion = join(aqui, "reproducir-cola.mjs");

for (const argumentos of [[], ["--concurrencia"]]) {
  const nombre = argumentos.length ? "concurrencia" : "recorrido";
  const resultado = spawnSync(process.execPath, [guion, ...argumentos], {
    cwd: raiz,
    stdio: "inherit",
  });
  if (resultado.status !== 0) {
    console.error(`reproducir-cola.mjs (${nombre}) salió con ${resultado.status}`);
    process.exit(resultado.status ?? 1);
  }
}

console.log("reproducir-cola.mjs: recorrido y concurrencia correctos");
