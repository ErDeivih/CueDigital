import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

/**
 * ***D01 · que el dueño no se derive tarde, otra vez*** (22/10/2026).
 *
 * *La revisión independiente reprodujo dos cruces de contexto en `app.js`:*
 *
 *   · *la respuesta **200** de A guardaba `cuedigital.ultimo.2:2` **con datos de A**;*
 *   · *y un **422** del vaciado de A acababa en `cuedigital.rechazados.2:2`.*
 *
 * *La causa era la misma en los dos: **la clave se hacía con la sesión que hubiera cuando la respuesta llegaba**, no con
 * el dueño capturado al empezar.*
 *
 * ***Esto no prueba el comportamiento*** *-para eso haría falta entrar con una cuenta mientras la otra tiene una
 * petición en vuelo, y eso no lo puede hacer este arnés sin un camino de entrada por el DOM-.* ***Lo que prueba es que
 * el código no puede volver a derivarlo***: *si alguien cambia `laClaveRechazados` por `laClaveDe(...)` dentro del
 * vaciado, o quita el `procesador` del turno, o pinta el último apunte sin mirar el contexto, **esta prueba falla**.*
 *
 * *Es el mismo recurso que la casa ya usa con «no queda ni un `innerHTML` de pantallas»: leer el fuente y exigir la
 * forma.*
 */

const EL_FUENTE = readFileSync(new URL("../web/app.js", import.meta.url), "utf8");

/** *El trozo de `app.js` que va desde una marca hasta la siguiente función de primer nivel.* */
function elTrozoDesde(laMarca) {
  const desde = EL_FUENTE.indexOf(laMarca);
  assert.notEqual(desde, -1, `no encuentro ${JSON.stringify(laMarca)} en app.js`);
  const siguiente = EL_FUENTE.indexOf("\nfunction ", desde);
  return EL_FUENTE.slice(desde, siguiente === -1 ? EL_FUENTE.length : siguiente);
}



test("el vaciado de la cola NO deriva la clave de los rechazos de la sesión de ahora", () => {
  // *La marca del vaciado: el vale fijado al empezar.*
  const elVaciado = elTrozoDesde("async function mandarPendientes()");

  assert.ok(
    elVaciado.includes("const laClaveRechazados"),
    "***el vaciado tiene que capturar la clave de los rechazos al empezar***",
  );
  // ***La regla exacta***: *al empezar **sí** se puede preguntar por la sesión -es el mismo instante en que se captura
  // el vale-, y de hecho se usa como respaldo cuando no hay sesión. **Lo que no puede es preguntarse DESPUÉS de
  // esperar**, que es el defecto: para entonces la sesión puede ser otra.*
  const elPrimerEspera = elVaciado.indexOf("await ");
  assert.notEqual(elPrimerEspera, -1, "el vaciado espera respuestas: tiene que haber un `await`");
  const loQueVaDespuesDeEsperar = elVaciado.slice(elPrimerEspera);
  assert.ok(
    !/laClaveDe\(\s*CLAVE_RECHAZADOS\s*\)/.test(loQueVaDespuesDeEsperar),
    "***después del primer `await` no puede haber `laClaveDe(CLAVE_RECHAZADOS)`: preguntaría por la sesión de ese instante, que puede ser otra***",
  );
  // ***Y la clave capturada es la que se LE PASA al vaciado***: *desde el 22/10 el bucle vive en `nucleo.js` -para
  // poder probarlo-, así que lo que hay que exigir aquí es que se le entregue la clave del origen, no que la use.*
  assert.ok(
    /claveRechazados:\s*laClaveRechazados/.test(elVaciado),
    "***el vaciado recibe la clave capturada, no una que se calcule dentro***",
  );
  assert.ok(
    elVaciado.includes("await vaciarLaCola("),
    "***y la decisión es la función probada, no un bucle propio sin pruebas***",
  );
});

test("el turno se pide con el procesador de esta pestaña, no solo con el dueño", () => {
  const elVaciado = elTrozoDesde("async function mandarPendientes()");

  assert.ok(
    /pedirElTurno\([\s\S]*?procesador:\s*elProcesador\(\)/.test(elVaciado),
    "***sin `procesador`, dos pestañas de la misma cuenta reciben las dos el turno***",
  );
  assert.ok(
    /soltarElTurno\([\s\S]*?procesador:\s*elProcesador\(\)/.test(elVaciado),
    "***y se suelta con el mismo, para no quitarle el turno a otra pestaña***",
  );
});

test("el último apunte se guarda con el dueño capturado y se pinta solo si el contexto sigue", () => {
  const elBloque = elTrozoDesde("if (guardarComoUltimo) {");

  assert.ok(
    /laClaveConDueno\(\s*CLAVE_ULTIMO\s*,\s*laSesion\s*\)/.test(elBloque),
    "***la clave tiene que salir del dueño capturado antes del `await`***",
  );
  assert.ok(
    /esDelMismoContexto\(\s*laSesion\s*,\s*laSesionDeAhora\(\)\s*\)/.test(elBloque),
    "***y el estado visible solo se toca si el contexto de origen sigue siendo el de ahora***",
  );
});

test("la sesión y el vale se capturan ANTES del primer `await`", () => {
  const laFuncion = elTrozoDesde("async function enviarOApuntar");

  const laSesion = laFuncion.indexOf("const laSesion = laSesionDeAhora()");
  const elToken = laFuncion.indexOf("const elToken = estado.token");
  const elPrimerEspera = laFuncion.indexOf("await ");

  assert.notEqual(laSesion, -1, "***la sesión se captura al empezar***");
  assert.notEqual(elToken, -1, "***y el vale también***");
  assert.ok(elPrimerEspera !== -1, "***la función tiene un `await`***");
  assert.ok(
    laSesion < elPrimerEspera && elToken < elPrimerEspera,
    "***capturarlas después del `await` es justo el defecto: para cuando llega la respuesta, la sesión puede ser otra***",
  );
});
