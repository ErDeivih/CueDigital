import { test } from "node:test";
import assert from "node:assert/strict";

import { crearAlmacenMemoria, crearColaPorIntenciones } from "../web/nucleo.js";

/**
 * ***Migración conservadora*** (24/10/2026, E1 — R2 y R4 de la revisión).
 *
 * ***R4***: *una entrada **sin `id_local`** que no se puede guardar **borraba el origen**. El motivo: el bucle la saltaba
 * con `continue` y la comprobación final se hacía **solo con las que ya tenían id**, así que `every([])` daba `true` y se
 * borraba **sin haber guardado nada**.*
 *
 * ***R2***: *entre la última lectura y el `removeItem` del origen cabe **una pestaña antigua** que escriba. Se migraba
 * `[A]`, la vieja dejaba `[A, B]`, y **se borraba todo**: B desaparecía.*
 */

/** *El almacén del que se migra, con la opción de **interferir** como lo haría una pestaña antigua.* */
function unAlmacenViejo({ loQueHay, interfiere }) {
  const datos = { "cuedigital.pendientes": loQueHay };
  let lecturas = 0;
  return {
    datos,
    esDurable: true,
    getItem(clave) {
      // ***La pestaña antigua escribe JUSTO ANTES de la lectura de comparación*** (2ª lectura del origen): *se escribe
      // primero y se devuelve lo de ahora -que es lo que hace un `localStorage` de verdad-, así que la migración **ve**
      // que el buzón ha cambiado.*
      if (clave === "cuedigital.pendientes") {
        lecturas += 1;
        if (lecturas === 2 && interfiere) interfiere(datos);
      }
      return datos[clave] ?? null;
    },
    setItem(clave, valor) {
      datos[clave] = String(valor);
    },
    removeItem(clave) {
      delete datos[clave];
    },
    get length() {
      return Object.keys(datos).length;
    },
    key: (i) => Object.keys(datos)[i] ?? null,
  };
}

test("***R4: una entrada sin id que no se puede guardar NO borra el origen***", () => {
  const laVieja = '[{"ruta":"/api/trabajos","datos":{"nota":"sin id"}}]';
  const elAlmacenViejo = unAlmacenViejo({ loQueHay: laVieja });
  // *Un almacén que no deja guardar nada -lleno o bloqueado-.*
  const elSinSitio = {
    esDurable: true,
    getItem: () => null,
    setItem: () => {
      throw new Error("sin sitio");
    },
    removeItem: () => {},
    get length() {
      return 0;
    },
    key: () => null,
  };

  const elParte = crearColaPorIntenciones(elSinSitio).migrarDesde(elAlmacenViejo);

  assert.equal(elParte.migrados, 0);
  assert.equal(
    elParte.borrado,
    false,
    "***sin haber guardado nada no se puede borrar el origen***",
  );
  assert.equal(
    elAlmacenViejo.datos["cuedigital.pendientes"],
    laVieja,
    "***y el origen tiene que seguir ahí, entero***",
  );
});

test("y con sitio sí se migra, poniéndole id a la que no lo tenía", () => {
  const laVieja = '[{"ruta":"/api/trabajos","datos":{"nota":"sin id"}}]';
  const elAlmacenViejo = unAlmacenViejo({ loQueHay: laVieja });
  const laCola = crearColaPorIntenciones(crearAlmacenMemoria());

  const elParte = laCola.migrarDesde(elAlmacenViejo);

  assert.equal(elParte.migrados, 1);
  // ***El origen ya NO se borra*** (24/10/2026, R2): *queda una última milla entre la comprobación y el `removeItem` en la
  // que una pestaña antigua puede escribir, y `localStorage` **no tiene borrado atómico**. Se deja; re-migrar es
  // idempotente porque el registro se reconoce por su `id_local`.*
  assert.equal(elParte.borrado, false, "***el buzón no se destruye***");
  const losSuyos = laCola.leer();
  assert.equal(losSuyos.length, 1);
  assert.ok(losSuyos[0].id_local, "***y lleva un id, que es lo que permite quitarla y reenviarla***");
});

test("***R2: si una pestaña antigua escribe durante la migración, NO se borra su buzón***", () => {
  // *La vieja deja `[A, B]` justo después de que la nuestra haya copiado A.*
  const elAlmacenViejo = unAlmacenViejo({
    loQueHay: '[{"id_local":"A","datos":{"nota":"A"}}]',
    interfiere: (datos) => {
      datos["cuedigital.pendientes"] = '[{"id_local":"A","datos":{"nota":"A"}},{"id_local":"B","datos":{"nota":"B"}}]';
    },
  });
  const laCola = crearColaPorIntenciones(crearAlmacenMemoria());

  const elParte = laCola.migrarDesde(elAlmacenViejo);

  assert.equal(
    elParte.borrado,
    false,
    "***el origen ha cambiado desde que se leyó: borrarlo se lleva por delante lo que acaba de escribir la vieja***",
  );
  assert.match(
    elAlmacenViejo.datos["cuedigital.pendientes"],
    /"B"/,
    "***y B sigue en el buzón, que es de donde lo sacará la siguiente migración***",
  );
});

test("***y la migración siguiente sí se lleva lo que la vieja dejó***", () => {
  const elAlmacenViejo = unAlmacenViejo({
    loQueHay: '[{"id_local":"A","datos":{"nota":"A"}}]',
    interfiere: (datos) => {
      datos["cuedigital.pendientes"] = '[{"id_local":"A","datos":{"nota":"A"}},{"id_local":"B","datos":{"nota":"B"}}]';
    },
  });
  const laCola = crearColaPorIntenciones(crearAlmacenMemoria());

  laCola.migrarDesde(elAlmacenViejo); // *la primera: no borra, porque el origen cambió*
  const laSegunda = laCola.migrarDesde(elAlmacenViejo); // *la segunda: ya sin interferencia*

  assert.equal(laSegunda.borrado, false, "***tampoco borra: el buzón se queda, y es idempotente***");
  const losIds = laCola.leer().map((uno) => uno.id_local).sort();
  assert.deepEqual(losIds, ["A", "B"], "***y están los dos: ni A se pierde ni B desaparece***");
});
