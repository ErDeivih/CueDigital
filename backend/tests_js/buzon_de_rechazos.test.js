import { test } from "node:test";
import assert from "node:assert/strict";

import { crearAlmacenMemoria, crearBuzonDeRechazos } from "../web/nucleo.js";

/**
 * ***R1 · dos rechazos simultáneos ya no se pisan*** (24/10/2026, E1).
 *
 * ***El defecto, medido por la revisión***: *cada vaciado leía **una vez** el array de rechazados antes del primer
 * `await`, le hacía `push` y lo guardaba. Dos vaciados de A y de B leían **los dos** vacío: A guardaba `[A]`, B guardaba
 * `[B]`, y **A desaparecía** — pendientes `[]` y rechazados `[B]`.*
 *
 * ***La regla***: *un rechazo es **un registro suyo**; **guardar no lee**, así que no se puede pisar el de nadie.*
 */

test("***dos rechazos que llegan a la vez quedan LOS DOS***", () => {
  const elAlmacen = crearAlmacenMemoria();
  const elBuzon = crearBuzonDeRechazos(elAlmacen);

  // *Los dos a la vez, sin esperar uno a que termine el otro.*
  const elDeA = elBuzon.apuntar({ id_local: "A", ruta: "/api/trabajos", cuenta: "1:1", motivo: "no vale" });
  const elDeB = elBuzon.apuntar({ id_local: "B", ruta: "/api/trabajos", cuenta: "1:1", motivo: "no vale" });

  assert.equal(elDeA.guardado, true);
  assert.equal(elDeB.guardado, true, "***guardar no lee: no hay nada que pisar***");

  const losIds = elBuzon.leer().map((uno) => uno.id_local).sort();
  assert.deepEqual(losIds, ["A", "B"], "***antes quedaba uno; ahora quedan los dos***");
});

test("***el rechazo conserva dueño, ruta y la clave original***", () => {
  const elBuzon = crearBuzonDeRechazos(crearAlmacenMemoria());
  elBuzon.apuntar({
    id_local: "C",
    ruta: "/api/trabajos",
    cuenta: "2:9",
    datos: { tipo: "laboreo", clave_de_reenvio: "la-original" },
    motivo: "no vale",
  });

  const [elSuyo] = elBuzon.leer();
  assert.equal(elSuyo.cuenta, "2:9");
  assert.equal(elSuyo.ruta, "/api/trabajos");
  assert.equal(
    elSuyo.datos.clave_de_reenvio,
    "la-original",
    "***con la clave original: recuperar no puede crear una intención duplicada***",
  );
  assert.equal(elSuyo.motivo, "no vale");
});

test("***y una sin id tampoco se pierde ni borra a las demás***", () => {
  const elBuzon = crearBuzonDeRechazos(crearAlmacenMemoria());
  const elSuyo = elBuzon.apuntar({ ruta: "/api/trabajos", motivo: "sin id" });
  const otro = elBuzon.apuntar({ id_local: "D", ruta: "/api/trabajos", motivo: "con id" });

  assert.ok(elSuyo.id_local, "***se le pone id: si no, no se puede ni quitar ni reenviar***");
  assert.equal(elBuzon.tamano(), 2);
  assert.equal(otro.guardado, true);
});

test("***quitar se lleva el suyo y solo el suyo***", () => {
  const elBuzon = crearBuzonDeRechazos(crearAlmacenMemoria());
  elBuzon.apuntar({ id_local: "A", ruta: "/api/x" });
  elBuzon.apuntar({ id_local: "B", ruta: "/api/x" });

  elBuzon.quitar("A");

  assert.deepEqual(
    elBuzon.leer().map((uno) => uno.id_local),
    ["B"],
    "***quitarlo uno no puede llevarse el de al lado***",
  );
});

test("***un rechazo corrupto no se convierte en «no hay rechazados»***", () => {
  const elAlmacen = crearAlmacenMemoria();
  elAlmacen.setItem("cuedigital.rechazado.roto", "{esto no es json");
  const elBuzon = crearBuzonDeRechazos(elAlmacen);

  assert.equal(elBuzon.tamano(), 1);
  assert.equal(elBuzon.losCorruptos().length, 1, "***se ve que está roto, en vez de desaparecer***");
});
