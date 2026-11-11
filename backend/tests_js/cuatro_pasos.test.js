/**
 * El apunte en cuatro pasos y la cola sin cobertura (11/11/2026).
 *
 * Lo que se ata aquí es lo que tiene que seguir funcionando cuando no hay red:
 *  · la fecha en la que termina un plazo (la del trabajo más los días de la etiqueta);
 *  · la cola de apuntes guardados en el navegador, que no se puede perder ni duplicar.
 *
 * Sin red, sin servidor y sin navegador de verdad: solo el código.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  CLAVE_DE_LA_COLA,
  hashDeLaVista,
  vistaDelHash,
  normalizaFilaDeHistorial,
  fechaDePlazo,
  apuntesPendientes,
  encolarApunte,
  quitarApunteDeLaCola,
} from "../web/nuevo/modelo.js";

/** Un almacén de mentira, como el del navegador. */
function almacenDeMentira(inicial = null) {
  const datos = new Map();
  if (inicial !== null) datos.set(CLAVE_DE_LA_COLA, inicial);
  return {
    getItem: (clave) => (datos.has(clave) ? datos.get(clave) : null),
    setItem: (clave, valor) => datos.set(clave, valor),
    quitarTodo: () => datos.clear(),
    datos,
  };
}

const apunte = { parcela_id: 1, producto_id: 3, fecha: "2026-11-11", dosis: 1.5 };

test("el plazo de seguridad se cuenta desde el día del trabajo", () => {
  assert.equal(fechaDePlazo("2026-11-11", 15), "2026-11-26");
});

test("el plazo cruza el fin de mes sin equivocarse", () => {
  assert.equal(fechaDePlazo("2026-11-25", 10), "2026-12-05");
});

test("sin días de plazo no hay fecha, y no se inventa una", () => {
  assert.equal(fechaDePlazo("2026-11-11", null), null);
  assert.equal(fechaDePlazo("2026-11-11", undefined), null);
  assert.equal(fechaDePlazo("2026-11-11", ""), null);
});

test("una fecha que no se entiende no revienta", () => {
  assert.equal(fechaDePlazo("no-es-una-fecha", 15), null);
});

test("un apunte se guarda con su estado, no como el cuerpo a medias", () => {
  const almacen = almacenDeMentira();
  encolarApunte(almacen, apunte);
  const cola = apuntesPendientes(almacen);
  assert.equal(cola.length, 1);
  assert.equal(cola[0].estado, "pendiente de enviar");
  assert.equal(cola[0].parcela_id, 1);
  assert.ok(cola[0].guardado_en, "lleva la hora en la que se guardó");
});

test("sin cobertura se pueden guardar varios, y no se pisan", () => {
  const almacen = almacenDeMentira();
  encolarApunte(almacen, apunte);
  encolarApunte(almacen, { ...apunte, parcela_id: 2 });
  const cola = apuntesPendientes(almacen);
  assert.equal(cola.length, 2);
  assert.deepEqual(
    cola.map((uno) => uno.parcela_id),
    [1, 2],
  );
});

test("el que se manda sale de la cola, y los demás se quedan", () => {
  const almacen = almacenDeMentira();
  encolarApunte(almacen, apunte);
  encolarApunte(almacen, { ...apunte, parcela_id: 2 });
  const cola = quitarApunteDeLaCola(almacen, 0);
  assert.equal(cola.length, 1);
  assert.equal(cola[0].parcela_id, 2);
  assert.equal(apuntesPendientes(almacen)[0].parcela_id, 2);
});

test("un almacén sin nada no es un error: es una cola vacía", () => {
  assert.deepEqual(apuntesPendientes(almacenDeMentira()), []);
});

test("un almacén con basura dentro no tumba la pantalla", () => {
  assert.deepEqual(apuntesPendientes(almacenDeMentira("{esto no es json")), []);
});

test("un almacén que no deja guardar no rompe el apunte", () => {
  const roto = {
    getItem: () => null,
    setItem: () => {
      throw new Error("sin sitio");
    },
  };
  assert.equal(encolarApunte(roto, apunte).length, 1);
  assert.deepEqual(apuntesPendientes(roto), []);
});

// --------------------------------------------------------------------------- las pestañas y el hash

test("cada pestaña deja su hash para poder compartirla", () => {
  assert.equal(hashDeLaVista("tierras"), "#tierras");
  assert.equal(hashDeLaVista("apuntar"), "#apuntar");
});

test("sin vista no hay hash, y la URL no se queda con una almohadilla suelta", () => {
  assert.equal(hashDeLaVista(""), "");
  assert.equal(hashDeLaVista(null), "");
});

test("la vista se lee de la URL, con o sin la almohadilla", () => {
  assert.equal(vistaDelHash("#tierras"), "tierras");
  assert.equal(vistaDelHash("tierras"), "tierras");
  assert.equal(vistaDelHash(""), null);
  assert.equal(vistaDelHash("#"), null);
});
// ------------------------------------------------------------------- el plazo en el apunte

test("el apunte de un tratamiento enseña su plazo hasta la fecha", () => {
  const fila = normalizaFilaDeHistorial(
    {
      tipo: "tratamiento",
      fecha: "2026-11-11",
      producto: "ATRAPA",
      dosis: 1.5,
      dosis_unidad: "L/ha",
      plazo_hasta: "2026-11-26",
    },
    [],
  );
  assert.ok(fila.detalles.some((detalle) => detalle.includes("plazo hasta")), "dice que hay plazo");
  assert.ok(fila.detalles.some((detalle) => detalle.includes("26/11")), "con la fecha de fin");
});

test("sin plazo apuntado no se inventa una fecha de plazo", () => {
  const fila = normalizaFilaDeHistorial(
    { tipo: "tratamiento", fecha: "2026-11-11", producto: "ATRAPA" },
    [],
  );
  assert.ok(!fila.detalles.some((detalle) => detalle.includes("plazo")), "no se inventa");
});