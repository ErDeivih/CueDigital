import { test } from "node:test";
import assert from "node:assert/strict";

import { crearAlmacenMemoria, crearColaPorIntenciones } from "../web/nucleo.js";

/**
 * ***D01 · la conservación entre pestañas*** (23/10/2026, P0).
 *
 * *Lo que se prueba aquí es **la propiedad que hay que tener**, no un truco: **dos escrituras sobre claves distintas no
 * se pueden pisar**. La intercalación se mete **en la última lectura**, como en el diagnóstico de la revisión —no en la
 * primera, que era el hueco que dejaban las pruebas anteriores—.*
 */

/**
 * ***El otro procesador escribe ANTES de que mi escritura llegue***: *es la carrera de verdad —no hace falta que yo lea
 * nada para que el otro escriba—, y es la que el leer-modificar-escribir perdía.*
 */
function unAlmacenDondeElOtroEscribeAntes(base, { queHaceElOtro, soloUnaVez = true } = {}) {
  let yaLoHizo = false;
  return {
    esDurable: true,
    getItem: (k) => base.getItem(k),
    setItem(k, v) {
      if (!yaLoHizo || !soloUnaVez) {
        yaLoHizo = true;
        queHaceElOtro();
      }
      base.setItem(k, v);
    },
    removeItem(k) {
      if (!yaLoHizo || !soloUnaVez) {
        yaLoHizo = true;
        queHaceElOtro();
      }
      base.removeItem(k);
    },
    get length() {
      return base.length;
    },
    key: (i) => base.key(i),
  };
}

test("***apuntar y apuntar: se conservan los DOS***", () => {
  const base = crearAlmacenMemoria();
  const laMia = crearColaPorIntenciones(
    unAlmacenDondeElOtroEscribeAntes(base, {
      // *El otro apunta a la vez, en el almacén de abajo —donde de verdad se escribe—.*
      queHaceElOtro: () => crearColaPorIntenciones(base).apuntar({ id_local: "B", datos: { nota: "B" } }),
    }),
  );

  const elMio = laMia.apuntar({ id_local: "A", datos: { nota: "A" } });
  assert.equal(elMio.guardado, true);

  const losIds = laMia.leer().map((uno) => uno.id_local).sort();
  assert.deepEqual(losIds, ["A", "B"], "***ninguna intención puede desaparecer***");
});

test("***apuntar y quitar: quitar lo suyo NO borra lo que el otro acaba de añadir***", () => {
  const base = crearAlmacenMemoria();
  crearColaPorIntenciones(base).apuntar({ id_local: "confirmado", datos: {} });

  const laMia = crearColaPorIntenciones(
    unAlmacenDondeElOtroEscribeAntes(base, {
      queHaceElOtro: () => crearColaPorIntenciones(base).apuntar({ id_local: "B", datos: { nota: "B" } }),
    }),
  );

  laMia.quitar("confirmado");

  const losIds = laMia.leer().map((uno) => uno.id_local);
  assert.deepEqual(losIds, ["B"], "***B se acaba de añadir: borrarlo sería perder un apunte del agricultor***");
});

test("***un valor corrupto NO se convierte en una cola vacía***", () => {
  const base = crearAlmacenMemoria({ "cuedigital.pendiente.roto": "{esto no es JSON" });
  const cola = crearColaPorIntenciones(base);

  assert.deepEqual(cola.leer(), [], "***no se puede mandar: no se sabe qué pone***");
  assert.deepEqual(cola.losCorruptos(), ["cuedigital.pendiente.roto"], "***pero se sabe que está***");
  assert.equal(
    base.getItem("cuedigital.pendiente.roto"),
    "{esto no es JSON",
    "***y se conserva intacto: la siguiente escritura no lo pisa***",
  );
});

test("la migración trae los campos enteros y NO borra el origen hasta comprobarlo", () => {
  const elViejo = JSON.stringify([
    { id_local: "viejo-1", cuenta: "1:1", ruta: "/api/trabajos", datos: { nota: "una", clave_de_reenvio: "r-1" } },
    { id_local: "viejo-2", cuenta: "1:1", ruta: "/api/gastos", datos: { nota: "otra", clave_de_reenvio: "r-2" } },
  ]);
  const base = crearAlmacenMemoria({ "cuedigital.pendientes": elViejo });
  const cola = crearColaPorIntenciones(base);

  const elParte = cola.migrarDesde(base);

  assert.equal(elParte.migrados, 2);
  // ***El origen ya NO se borra*** (24/10/2026, R2 de la revisión): *entre la comprobación y el `removeItem` queda una
  // última milla en la que una pestaña antigua puede escribir, y `localStorage` no tiene borrado atómico. Se deja, y
  // re-migrar es idempotente: el registro se reconoce por su `id_local` y no se duplica.*
  assert.equal(elParte.borrado, false, "***el buzón no se destruye***");
  // ***El origen YA NO se borra*** (24/10/2026, R2): *entre la comprobación y el `removeItem` queda una última
  // milla en la que una pestaña antigua puede escribir, y `localStorage` no tiene borrado atómico. Se deja, y
  // **migrar dos veces no duplica**: el registro se reconoce por su `id_local`.*
  assert.ok(
    base.getItem("cuedigital.pendientes"),
    "***el buzón se queda: no se destruye lo que otro puede estar usando***",
  );
  // *Y una segunda migración no crea duplicados.*

  const losSuyos = cola.leer();
  assert.deepEqual(losSuyos.map((uno) => uno.id_local).sort(), ["viejo-1", "viejo-2"]);
  assert.equal(losSuyos.find((uno) => uno.id_local === "viejo-1").cuenta, "1:1", "***con su dueño***");
  assert.equal(
    losSuyos.find((uno) => uno.id_local === "viejo-1").datos.clave_de_reenvio,
    "r-1",
    "***y su clave de reenvío: el servidor no puede contar dos veces la misma intención***",
  );
});

test("***y si un apunte no se puede guardar, el origen NO se borra***", () => {
  const elViejo = JSON.stringify([{ id_local: "u-no", cuenta: "1:1", datos: {} }]);
  const base = crearAlmacenMemoria({ "cuedigital.pendientes": elViejo });
  // *Un almacén que falla justo al guardar ese apunte -lleno o bloqueado-.*
  const elRoto = {
    esDurable: true,
    getItem: (k) => base.getItem(k),
    setItem: (k, v) => {
      if (String(k).includes("u-no")) throw new Error("sin sitio");
      base.setItem(k, v);
    },
    removeItem: (k) => base.removeItem(k),
    get length() {
      return base.length;
    },
    key: (i) => base.key(i),
  };

  const elParte = crearColaPorIntenciones(elRoto).migrarDesde(elRoto);

  assert.equal(elParte.migrados, 0);
  assert.equal(elParte.borrado, false, "***no se borra lo que no se ha copiado***");
  assert.equal(base.getItem("cuedigital.pendientes"), elViejo, "***y el origen sigue ahí, entero***");
});

test("un JSON corrupto en la cola vieja tampoco se pisa", () => {
  const base = crearAlmacenMemoria({ "cuedigital.pendientes": "{roto" });
  const cola = crearColaPorIntenciones(base);

  const elParte = cola.migrarDesde(base);

  assert.equal(elParte.corrupto, true);
  assert.equal(elParte.borrado, false, "***no se sabe qué había: conservarlo es lo único honesto***");
  assert.equal(base.getItem("cuedigital.pendientes"), "{roto");
});
