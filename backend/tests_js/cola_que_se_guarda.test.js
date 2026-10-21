import { test } from "node:test";
import assert from "node:assert/strict";

import { crearAlmacenMemoria, crearCola, sesionDelToken } from "../web/nucleo.js";

/**
 * ***La cola dice si guardo, y sella lo que manda*** (19/10/2026).
 *
 * *Dos cosas que antes no hacía, y las dos costaban datos:*
 *
 *   ***1 · Decía que sí siempre.*** *`escribir` devuelve `false` cuando el almacén falla -modo privado, lleno, un
 *   navegador que lo bloquea-, y **ese resultado se tiraba**: el agricultor creía que había apuntado y el apunte
 *   no existía.*
 *
 *   ***2 · No llevaba clave de reenvío.*** *El servidor sabe reconocer un reintento por `clave_de_reenvio`
 *   (`reenvios.la_misma_accion`), y la cola no la mandaba: **una respuesta perdida que provoca un reintento -o
 *   dos pestañas vaciando la misma cola- mandaba lo mismo dos veces**.*
 */

function unAlmacenQueFalla() {
  return {
    getItem: () => null,
    setItem: () => {
      throw new Error("el almacen esta lleno");
    },
    removeItem: () => {},
  };
}

test("cuando el almacen falla, se DICE que no se guardo", () => {
  const cola = crearCola(unAlmacenQueFalla());

  const el_apunte = cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: "de campo" } });

  assert.equal(el_apunte.guardado, false, "***no puede decir que si cuando no se guardo***");
  assert.equal(cola.tamano(), 0, "***y no hay nada en la cola, porque no se pudo escribir***");
});

test("y cuando el almacen va, se dice que si", () => {
  const cola = crearCola(crearAlmacenMemoria());

  const el_apunte = cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: "de campo" } });

  assert.equal(el_apunte.guardado, true);
  assert.equal(cola.tamano(), 1, "***y el apunte esta***");
});

test("cada apunte lleva su clave de reenvio, que es su id_local", () => {
  const cola = crearCola(crearAlmacenMemoria());

  const el_apunte = cola.apuntar({
    tipo: "labor",
    ruta: "/api/trabajos",
    datos: { nota: "de campo", campana_id: 5 },
  });

  assert.equal(
    el_apunte.datos.clave_de_reenvio,
    el_apunte.id_local,
    "***la clave tiene que ser el id local: unico y estable***",
  );
  assert.equal(el_apunte.datos.campana_id, 5, "***y no puede perder nada de lo que traia***");
  assert.equal(el_apunte.datos.nota, "de campo");

  // *Y queda guardada en la cola, no solo en el objeto que devuelve.*
  const [el_de_la_cola] = cola.leer();
  assert.equal(el_de_la_cola.datos.clave_de_reenvio, el_de_la_cola.id_local);
});

test("y si quien apunta ya trae su clave, se respeta la suya", () => {
  const cola = crearCola(crearAlmacenMemoria());

  const el_apunte = cola.apuntar({
    tipo: "labor",
    ruta: "/api/trabajos",
    datos: { nota: "de campo", clave_de_reenvio: "la-que-traia" },
  });

  assert.equal(el_apunte.datos.clave_de_reenvio, "la-que-traia", "***no se pisa la de quien llama***");
});

test("dos apuntes distintos llevan claves distintas", () => {
  const cola = crearCola(crearAlmacenMemoria());

  const uno = cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: "uno" } });
  const otro = cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: "otro" } });

  assert.notEqual(uno.datos.clave_de_reenvio, otro.datos.clave_de_reenvio);
});

// ---------------------------------------------------------------------------
// ***La sesión sale del VALE, que es lo que `api()` manda***
// ---------------------------------------------------------------------------

function unVale(carga) {
  const trozo = Buffer.from(JSON.stringify(carga)).toString("base64url");
  return `${trozo}.firma-de-prueba`;
}

test("la sesion sale del vale, que es lo que de verdad viaja", () => {
  assert.equal(sesionDelToken(unVale({ uid: 2, eid: 7, exp: 1 })), "2:7");
  assert.equal(sesionDelToken(unVale({ uid: 9, eid: 9 })), "9:9");
});

test("y un vale que no se puede leer NO es una sesion: es null", () => {
  // *Con `null` la cola no manda nada, que es la respuesta segura.*
  for (const el_malo of [null, undefined, "", "no-es-un-vale", "a.b", "a.b.c", unVale({ uid: 2, eid: 7 }) + ".otra-parte", 42]) {
    assert.equal(sesionDelToken(el_malo), null, `***${String(el_malo)} no puede dar una sesion***`);
  }
});

test("y un vale sin cuenta tampoco", () => {
  // *Un vale que no dice de quien es no sirve para decidir de quien es un apunte.*
  assert.equal(sesionDelToken(unVale({ sub: "alguien", exp: 1 })), null);
  assert.equal(sesionDelToken(unVale({ uid: 2 })), null, "***sin finca no hay sesion***");
  assert.equal(sesionDelToken(unVale({ eid: 2 })), null, "***sin usuario tampoco***");
});
