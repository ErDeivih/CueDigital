import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * ***D07 · las trazas, acotadas*** (22/10/2026).
 *
 * *Lo que el encargo pide de la instrumentación es que **no quede en producción** o que esté **acotada**. Un
 * `console.log` olvidado en una pantalla es una traza que se queda para siempre en el navegador de un agricultor; y una
 * que imprima el vale o el contenido de una respuesta, además, es un dato de más en un sitio de menos.*
 *
 * ***Lo que hay hoy*** —y esto lo mantiene así—: *en toda la interfaz, **tres `console.error`**: el de una pantalla que no
 * se ha podido montar y dos de la conciliación de pagos. **Ni un `console.log`**.*
 *
 * ***La regla no es «ningún registro»***: *un error que no se puede leer es un error que no se puede arreglar —el
 * comentario de `app.js` lo dice: un `console.error` **no cambia el comportamiento** y hace que el fallo se pueda leer—.
 * **La regla es que no haya trazas de depuración y que ninguna lleve el vale.***
 */

const LA_RAIZ = fileURLToPath(new URL("..", import.meta.url));
const LA_WEB = join(LA_RAIZ, "web");

/** *Los ficheros de la interfaz que son del proyecto: fuera los paquetes de React y las pruebas.* */
function losFicherosDeLaWeb() {
  const encontrados = [];
  const recorrer = (carpeta) => {
    for (const nombre of readdirSync(carpeta)) {
      const ruta = join(carpeta, nombre);
      if (statSync(ruta).isDirectory()) {
        if (nombre !== "node_modules") recorrer(ruta);
        continue;
      }
      if (!nombre.endsWith(".js")) continue;
      // *Los paquetes de React vienen minificados y con `console` dentro: no son nuestros.*
      if (/^(react|react-dom)/.test(nombre)) continue;
      encontrados.push(ruta);
    }
  };
  recorrer(LA_WEB);
  return encontrados;
}

/** *Las líneas que de verdad son código: se quitan los comentarios de una línea.* */
function lasLineasDeCodigo(ruta) {
  return readFileSync(ruta, "utf8")
    .split("\n")
    .map((linea) => linea.split("//")[0])
    .filter((linea) => linea.trim().length > 0);
}

test("***no queda ni una traza de depuración en la interfaz***", () => {
  const lasDeDepuracion = [];
  for (const ruta of losFicherosDeLaWeb()) {
    for (const linea of lasLineasDeCodigo(ruta)) {
      if (/console\.(log|info|debug|table|trace|dir)\s*\(/.test(linea)) {
        lasDeDepuracion.push(`${ruta.replace(LA_RAIZ, "")}: ${linea.trim().slice(0, 90)}`);
      }
    }
  }
  assert.deepEqual(
    lasDeDepuracion,
    [],
    `***una traza de depuración se queda en el navegador del agricultor para siempre***: ${lasDeDepuracion.join(" | ")}`,
  );
});

test("***y ninguna traza de error lleva el vale ni lo guardado***", () => {
  // *Lo que no puede salir por consola: el vale, el almacén, ni el estado con la sesión dentro.*
  const loQueNoSale = /token|localStorage|sessionStorage|contrase|clave|password/i;
  const lasQueLlevan = [];
  for (const ruta of losFicherosDeLaWeb()) {
    const lineas = lasLineasDeCodigo(ruta);
    lineas.forEach((linea, indice) => {
      if (/console\.(error|warn)\s*\(/.test(linea) && loQueNoSale.test(linea)) {
        lasQueLlevan.push(`${ruta.replace(LA_RAIZ, "")}:${indice + 1}: ${linea.trim().slice(0, 90)}`);
      }
    });
  }
  assert.deepEqual(
    lasQueLlevan,
    [],
    `***una traza no puede llevar el vale ni lo guardado***: ${lasQueLlevan.join(" | ")}`,
  );
});

test("y las que hay son pocas y de error: el registro no es un diario", () => {
  // *El limite no es un capricho: si un dia crece sin querer, se ve aqui antes que en el navegador de nadie.*
  let losErrores = 0;
  for (const ruta of losFicherosDeLaWeb()) {
    for (const linea of lasLineasDeCodigo(ruta)) {
      if (/console\.error\s*\(/.test(linea)) losErrores += 1;
    }
  }
  assert.ok(
    losErrores <= 6,
    `***hay ${losErrores} trazas de error: si son mas, es un diario y no un aviso***`,
  );
});
