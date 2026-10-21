import { test } from "node:test";
import assert from "node:assert/strict";

import { crearAlmacenMemoria, crearCola, loQueSePuedeMandar } from "../web/nucleo.js";

/**
 * ***La cola de una cuenta no se manda con el vale de otra*** (19/10/2026).
 *
 * *El fallo, tal y como se reprodujo*: *se apuntaba un trabajo sin cobertura en una finca, se entraba con otra
 * cuenta y, al volver la red, **el trabajo se escribia en la finca equivocada** -o se quedaba en un 404 sin que
 * nadie supiera por que-. La cola guardaba `{tipo, ruta, datos}` **sin decir de quien era**.*
 *
 * *Ahora cada apunte lleva su cuenta y `loQueSePuedeMandar` separa **tres** montones: los suyos -que son los
 * unicos que se mandan-, **los de otra cuenta** -que esperan sin perderse- y **los que no tienen cuenta**, que son
 * los de antes de esta correccion y **no se adivinan**.*
 */

function unaColaCon({ deA = 0, deB = 0, sinCuenta = 0 } = {}) {
  const cola = crearCola(crearAlmacenMemoria());
  for (let n = 0; n < deA; n += 1) {
    cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: `de A ${n}` }, cuenta: "1:1" });
  }
  for (let n = 0; n < deB; n += 1) {
    cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: `de B ${n}` }, cuenta: "2:9" });
  }
  for (let n = 0; n < sinCuenta; n += 1) {
    cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: `antigua ${n}` } });
  }
  return cola;
}

test("cada cuenta manda lo suyo y NO lo de la otra", () => {
  const cola = unaColaCon({ deA: 2, deB: 3, sinCuenta: 1 });

  const comoA = loQueSePuedeMandar(cola, "1:1");
  assert.deepEqual(comoA.suyos.map((a) => a.datos.nota), ["de A 0", "de A 1"]);
  assert.equal(comoA.deOtraCuenta.length, 3, "***lo de B no se manda nunca como A***");
  assert.equal(comoA.sinCuenta.length, 1);

  const comoB = loQueSePuedeMandar(cola, "2:9");
  assert.equal(comoB.suyos.length, 3);
  assert.equal(comoB.deOtraCuenta.length, 2);
});

test("sin sesion conocida NO se manda nada, y nada se da por perdido", () => {
  const cola = unaColaCon({ deA: 2, deB: 1 });

  const sinSesion = loQueSePuedeMandar(cola, null);
  assert.equal(sinSesion.suyos.length, 0, "***«no se de quien es» no es «es de quien este ahora»***");
  assert.equal(sinSesion.deOtraCuenta.length, 3);

  // *Y la cola sigue entera: preguntar no gasta nada.*
  assert.equal(cola.tamano(), 3);
});

test("un apunte SIN cuenta no se adivina, y no se pierde", () => {
  const cola = unaColaCon({ sinCuenta: 2 });
  const suyo = loQueSePuedeMandar(cola, "1:1");
  assert.equal(suyo.suyos.length, 0, "***mandarlo seria escribir en una finca que no se sabe***");
  assert.equal(suyo.sinCuenta.length, 2);
  assert.equal(cola.tamano(), 2);
});
