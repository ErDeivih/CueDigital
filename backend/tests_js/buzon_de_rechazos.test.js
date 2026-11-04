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

// ---------------------------------------------------------------------------
// ***Lo que quedó en la lista vieja, se trae al buzón*** (04/11/2026, D01-R1)
// ---------------------------------------------------------------------------
//
// *Hasta hoy cada cuenta guardaba sus rechazos en **una lista** (`cuedigital.rechazados.<cuenta>`). Al pasar al
// buzón, lo que ya estaba en esas listas **no puede quedarse invisible**: se migra, con la misma regla que la cola de
// pendientes —comprobar antes de borrar, y conservar lo que no se puede leer—.*

const LA_LISTA_VIEJA = JSON.stringify([
  { id_local: "viejo-1", ruta: "/api/trabajos", datos: { nota: "una", clave_de_reenvio: "r-1" }, motivo: "no vale" },
  { id_local: "viejo-2", ruta: "/api/gastos", cuenta: "2:2", motivo: "tampoco" },
]);

test("***una lista vieja se trae al buzón, con su dueño, y no se borra hasta comprobarla***", () => {
  const elAlmacen = crearAlmacenMemoria({ "cuedigital.rechazados.1:1": LA_LISTA_VIEJA });
  const elBuzon = crearBuzonDeRechazos(elAlmacen);

  const elParte = elBuzon.migrarDesde();

  assert.equal(elParte.migrados, 2);
  assert.equal(elParte.borradas, 1);
  assert.equal(elAlmacen.getItem("cuedigital.rechazados.1:1"), null, "***verificado que están, el origen se va***");
  const losSuyos = elBuzon.leer();
  assert.deepEqual(losSuyos.map((uno) => uno.id_local).sort(), ["viejo-1", "viejo-2"]);
  assert.equal(
    losSuyos.find((uno) => uno.id_local === "viejo-1").cuenta,
    "1:1",
    "***el dueño de la clave rellena el hueco de los que no lo llevaban***",
  );
  assert.equal(
    losSuyos.find((uno) => uno.id_local === "viejo-2").cuenta,
    "2:2",
    "***y el dueño que ya traía el registro no se pisa***",
  );
  assert.equal(
    losSuyos.find((uno) => uno.id_local === "viejo-1").datos.clave_de_reenvio,
    "r-1",
    "***con su clave original: recuperarlo no puede crear una intención duplicada***",
  );
});

test("***migrar dos veces no duplica nada***", () => {
  const elAlmacen = crearAlmacenMemoria({ "cuedigital.rechazados.1:1": LA_LISTA_VIEJA });
  const elBuzon = crearBuzonDeRechazos(elAlmacen);
  elBuzon.migrarDesde();

  const laSegunda = elBuzon.migrarDesde();

  assert.equal(laSegunda.migrados, 0, "***el origen ya no está: no hay nada que traer***");
  assert.equal(elBuzon.tamano(), 2, "***y no se ha duplicado ni uno***");
});

test("***una lista rota se conserva y no se convierte en «no hay rechazos»***", () => {
  const elAlmacen = crearAlmacenMemoria({ "cuedigital.rechazados.1:1": "{roto" });
  const elBuzon = crearBuzonDeRechazos(elAlmacen);

  const elParte = elBuzon.migrarDesde();

  assert.equal(elParte.corruptos, 1);
  assert.equal(elParte.borradas, 0, "***no se borra lo que no se ha podido leer***");
  assert.equal(elAlmacen.getItem("cuedigital.rechazados.1:1"), "{roto", "***el original sigue ahí***");
});

test("***si no se puede guardar, la lista vieja NO se borra***", () => {
  const base = crearAlmacenMemoria({ "cuedigital.rechazados.1:1": LA_LISTA_VIEJA });
  const elRoto = {
    esDurable: true,
    getItem: (k) => base.getItem(k),
    setItem: (k, v) => {
      if (String(k).startsWith("cuedigital.rechazado.")) throw new Error("sin sitio");
      base.setItem(k, v);
    },
    removeItem: (k) => base.removeItem(k),
    get length() {
      return base.length;
    },
    key: (i) => base.key(i),
  };

  const elParte = crearBuzonDeRechazos(elRoto).migrarDesde();

  assert.equal(elParte.migrados, 0);
  assert.equal(elParte.borradas, 0, "***no se borra lo que no se ha copiado***");
  assert.equal(base.getItem("cuedigital.rechazados.1:1"), LA_LISTA_VIEJA, "***y el origen sigue entero***");
});

test("***si el origen CAMBIA entre la comprobación y el borrado, no se borra***", () => {
  const base = crearAlmacenMemoria({ "cuedigital.rechazados.1:1": LA_LISTA_VIEJA });
  let elPrimero = true;
  const elQueCambiaElOrigen = {
    esDurable: true,
    getItem: (k) => base.getItem(k),
    setItem: (k, v) => {
      base.setItem(k, v);
      // *Una pestaña vieja apunta otro rechazo justo mientras se migra.*
      if (elPrimero) {
        elPrimero = false;
        base.setItem(
          "cuedigital.rechazados.1:1",
          JSON.stringify([...JSON.parse(LA_LISTA_VIEJA), { id_local: "recien-llegado", motivo: "nuevo" }]),
        );
      }
    },
    removeItem: (k) => base.removeItem(k),
    get length() {
      return base.length;
    },
    key: (i) => base.key(i),
  };

  const elParte = crearBuzonDeRechazos(elQueCambiaElOrigen).migrarDesde();

  assert.equal(elParte.borradas, 0, "***borrar una lista que otro acaba de usar perdería lo suyo***");
  assert.ok(
    String(base.getItem("cuedigital.rechazados.1:1")).includes("recien-llegado"),
    "***y lo que llegó después sigue donde estaba***",
  );
});

test("***el buzón nuevo no se confunde con la lista vieja***", () => {
  const elAlmacen = crearAlmacenMemoria({
    "cuedigital.rechazado.ya": JSON.stringify({ id_local: "ya", motivo: "de antes" }),
  });
  const elBuzon = crearBuzonDeRechazos(elAlmacen);

  const elParte = elBuzon.migrarDesde();

  assert.equal(elParte.migrados, 0, "***el buzón no se migra a sí mismo***");
  assert.equal(elBuzon.tamano(), 1);
  assert.equal(elBuzon.leer()[0].motivo, "de antes");
});
