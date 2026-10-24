import { test } from "node:test";
import assert from "node:assert/strict";

import {
  pedirElTurnoTransaccional,
  soltarElTurnoTransaccional,
} from "../web/nucleo.js";

/**
 * ***D01 · el turno, con exclusión demostrable*** (23/10/2026).
 *
 * *Con `read/modify/write` sobre `localStorage` **no se puede demostrar**: los dos leen «no hay turno» y los dos escriben.
 * Aquí se prueba **sobre una base que serializa las transacciones**, que es lo que dan IndexedDB y, con otra forma, Web
 * Locks: **leer y escribir sin que nadie se intercale**.*
 */

/** *Una base que ejecuta las transacciones **de una en una**: lo que hace IndexedDB por dentro.* */
function unaBaseTransaccional() {
  const losRegistros = new Map();
  const laCola = [];
  let ocupada = false;
  const ejecutar = () => {
    if (ocupada) return;
    const siguiente = laCola.shift();
    if (!siguiente) return;
    ocupada = true;
    const { clave, cambia, resolver } = siguiente;
    const anterior = losRegistros.has(clave) ? losRegistros.get(clave) : null;
    const nuevo = cambia(anterior ? { ...anterior } : null);
    if (nuevo === null) losRegistros.delete(clave);
    else if (nuevo !== undefined) losRegistros.set(clave, nuevo);
    resolver({ anterior, nuevo: nuevo === undefined ? anterior : nuevo });
    ocupada = false;
    ejecutar();
  };
  return {
    transaccion(clave, cambia) {
      return new Promise((resolver) => {
        laCola.push({ clave, cambia, resolver });
        ejecutar();
      });
    },
  };
}

const LA_CLAVE = "cuedigital.cola.turno";

test("***dos adquisiciones a la vez: UNA gana, la otra no***", async () => {
  const base = unaBaseTransaccional();
  // *Las dos piden **a la vez**, sin esperar una a terminar la otra.*
  const [laDeA, laDeB] = await Promise.all([
    pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A", ahora: 1000 }),
    pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "B", ahora: 1000 }),
  ]);

  const lasQueGanaron = [laDeA.turno, laDeB.turno].filter(Boolean).length;
  assert.equal(
    lasQueGanaron,
    1,
    `***tiene que ganar UNA, no las dos***: A=${laDeA.turno}, B=${laDeB.turno}`,
  );
});

test("***y el que no la gana sabe de quién es***", async () => {
  const base = unaBaseTransaccional();
  const laDeA = await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A", ahora: 1000 });
  const laDeB = await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "B", ahora: 1000 });

  assert.equal(laDeA.turno, true);
  assert.equal(laDeB.turno, false);
  assert.equal(laDeB.procesador, "A", "***y dice quién lo tiene, para no quedarse esperando a ciegas***");
});

test("el mismo procesador SÍ renueva: no se bloquea a sí mismo", async () => {
  const base = unaBaseTransaccional();
  const una = await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A", ahora: 1000 });
  const dos = await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A", ahora: 1010 });
  assert.equal(una.turno, true);
  assert.equal(dos.turno, true);
});

test("***un turno CADUCADO deja entrar a otro***", async () => {
  const base = unaBaseTransaccional();
  await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A", ahora: 1000, duraMs: 30000 });
  const tarde = await pedirElTurnoTransaccional(base, {
    clave: LA_CLAVE,
    dueno: "1:1:inst",
    procesador: "B",
    ahora: 1031000,
  });
  assert.equal(tarde.turno, true, "***un cerrojo sin caducidad es una cola parada***");
});

test("y soltarlo deja entrar al siguiente", async () => {
  const base = unaBaseTransaccional();
  await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A", ahora: 1000 });
  await soltarElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A" });
  const laDeB = await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "B", ahora: 1001 });
  assert.equal(laDeB.turno, true);
});

test("***soltar el turno de OTRO no se lo quita***", async () => {
  const base = unaBaseTransaccional();
  await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "A", ahora: 1000 });
  await soltarElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "B" });
  const laDeB = await pedirElTurnoTransaccional(base, { clave: LA_CLAVE, dueno: "1:1:inst", procesador: "B", ahora: 1001 });
  assert.equal(laDeB.turno, false, "***B no puede quitarle el turno a A***");
});
