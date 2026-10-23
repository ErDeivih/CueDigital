import { test } from "node:test";
import assert from "node:assert/strict";

import {
  crearAlmacenMemoria,
  crearCola,
  esDelMismoContexto,
  laClaveConDueno,
  loQueSePuedeMandar,
  pedirElTurno,
  vaciarLaCola,
} from "../web/nucleo.js";

/**
 * ***D01 · la concurrencia local y las claves que se derivan tarde*** (22/10/2026).
 *
 * *Estas pruebas salen de la revisión independiente, que reprodujo dos huecos con promesas y un almacén controlado
 * (`docs/revision-2026-10-19/reproducciones.txt`):*
 *
 *   1. **dos procesadores de la misma cuenta reciben los dos `turno: true`**: *el dueño del turno era
 *      `cuenta:instalación`, **compartido** por las dos pestañas, y el lease lo trataba como reentrante;*
 *   2. **dos `apuntar` intercalados dejan un solo pendiente**: *los dos reescriben el array que leyeron.*
 *
 * *Y una tercera, que es la del cruce de contexto: **la clave de persistencia tiene que salir del dueño capturado al
 * empezar, no de la sesión que haya cuando la respuesta llega**.*
 *
 * ***Cada una tenía que fallar antes del arreglo.***
 */

// ---------------------------------------------------------------------------
// 1 · El turno: mismo dueño NO es el mismo procesador
// ---------------------------------------------------------------------------

test("dos procesadores de la misma cuenta NO reciben los dos el turno", () => {
  const almacen = crearAlmacenMemoria();
  const ahora = 1_000_000;
  // *El dueño compartido de antes: misma cuenta y misma instalación.*
  const elDueno = "1:1:la-instalacion";

  const una = pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-A", ahora, duraMs: 30000 });
  const otra = pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-B", ahora: ahora + 1, duraMs: 30000 });

  assert.equal(una.turno, true, "***la primera pestaña tiene que poder***");
  assert.equal(
    otra.turno,
    false,
    "***mismo dueño NO es el mismo procesador: dos pestañas de una cuenta no vacían a la vez***",
  );
});

test("y el MISMO procesador sí renueva su turno", () => {
  const almacen = crearAlmacenMemoria();
  const elDueno = "1:1:la-instalacion";

  const una = pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-A", ahora: 1_000_000, duraMs: 30000 });
  const otra = pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-A", ahora: 1_010_000, duraMs: 30000 });

  assert.equal(una.turno, true);
  assert.equal(otra.turno, true, "***el que ya tenía el turno lo renueva: no se bloquea a sí mismo***");
});

test("un turno SIN procesador -de antes- tampoco se da por reentrante", () => {
  // *Lo que quede de una versión anterior no dice de qué pestaña es: se trata como de otra y caduca sola.*
  const almacen = crearAlmacenMemoria();
  pedirElTurno(almacen, { dueno: "1:1:la-instalacion", ahora: 1_000_000, duraMs: 30000 });
  const otra = pedirElTurno(almacen, {
    dueno: "1:1:la-instalacion",
    procesador: "pestana-B",
    ahora: 1_000_001,
    duraMs: 30000,
  });
  assert.equal(otra.turno, false, "***un turno viejo no dice de qué pestaña es: no se reparte***");
});

// ---------------------------------------------------------------------------
// 2 · Las escrituras intercaladas: las dos intenciones sobreviven
// ---------------------------------------------------------------------------

test("dos apuntar intercalados conservan las DOS intenciones", () => {
  const almacen = crearAlmacenMemoria();
  const LA_CLAVE = "cuedigital.pendientes";
  let yaInterferi = false;

  // *El almacén que se intercala: en la **primera lectura**, otra pestaña apunta a la vez.*
  const elAlmacen = {
    getItem(clave) {
      const elValor = almacen.getItem(clave);
      if (!yaInterferi && clave === LA_CLAVE) {
        yaInterferi = true;
        const loQueHabia = elValor ? JSON.parse(elValor) : [];
        almacen.setItem(
          LA_CLAVE,
          JSON.stringify([...loQueHabia, { id_local: "de-la-otra-pestana", ruta: "/api/trabajos", datos: {} }]),
        );
      }
      return elValor;
    },
    setItem: (clave, valor) => almacen.setItem(clave, valor),
    removeItem: (clave) => almacen.removeItem(clave),
    esDurable: true,
  };

  const cola = crearCola(elAlmacen);
  const elMio = cola.apuntar({ ruta: "/api/trabajos", datos: { nota: "la mía" } });

  const losIds = cola.leer().map((uno) => uno.id_local);
  assert.ok(
    losIds.includes("de-la-otra-pestana"),
    `***la intención de la otra pestaña no se puede perder***: ${JSON.stringify(losIds)}`,
  );
  assert.ok(losIds.includes(elMio.id_local), `***y la mía tampoco***: ${JSON.stringify(losIds)}`);
  assert.equal(cola.tamano(), 2, "***tienen que quedar las dos, no una***");
});

// ---------------------------------------------------------------------------
// 3 · Las claves, del dueño del ORIGEN
// ---------------------------------------------------------------------------

test("la clave se hace con el dueño del ORIGEN, y sin dueño NO hay clave", () => {
  assert.equal(laClaveConDueno("cuedigital.ultimo", "1:1"), "cuedigital.ultimo.1:1");
  assert.equal(laClaveConDueno("cuedigital.rechazados", "2:9"), "cuedigital.rechazados.2:9");
  assert.equal(
    laClaveConDueno("cuedigital.ultimo", null),
    null,
    "***sin dueño no se escribe en un cubo compartido: mejor no guardarlo que mezclarlo***",
  );
});

test("un estado visible solo se toca si el contexto de origen sigue siendo el de ahora", () => {
  assert.equal(esDelMismoContexto("1:1", "1:1"), true, "***el dueño sigue dentro: se puede enseñar***");
  assert.equal(
    esDelMismoContexto("1:1", "2:2"),
    false,
    "***entró otra cuenta: la respuesta de la primera NO se le enseña***",
  );
  assert.equal(esDelMismoContexto(null, null), false, "***sin dueño de origen no se toca nada***");
  assert.equal(esDelMismoContexto("1:1", null), false, "***y si ya no hay sesión, tampoco***");
});


// ---------------------------------------------------------------------------
// 4 · El reinicio, la caducidad y el retorno del dueño (22/10/2026, D01)
// ---------------------------------------------------------------------------

test("***un turno CADUCADO deja entrar a otro procesador***", () => {
  const almacen = crearAlmacenMemoria();
  const elDueno = "1:1:la-instalacion";
  pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-A", ahora: 1_000_000, duraMs: 30000 });
  // *Pasados los 30 s, el turno caduca: **un cerrojo sin caducidad es una cola parada**.*
  const tarde = pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-B", ahora: 1_031_000, duraMs: 30000 });
  assert.equal(tarde.turno, true, "***caducado, el siguiente entra***");
});

test("***y al recargar la pestaña no se bloquea a sí misma***", () => {
  // *El procesador vive en `sessionStorage`: **sobrevive a la recarga de esa pestaña** y no se comparte con otra. Aquí
  // se prueba la parte pura: el mismo procesador, veinte segundos después, renueva su turno.*
  const almacen = crearAlmacenMemoria();
  const elDueno = "1:1:la-instalacion";
  pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-A", ahora: 1_000_000, duraMs: 30000 });
  const recargada = pedirElTurno(almacen, { dueno: elDueno, procesador: "pestana-A", ahora: 1_020_000, duraMs: 30000 });
  assert.equal(recargada.turno, true, "***una recarga de la misma pestaña no es otra pestaña***");
});

test("***cuando el dueño vuelve, sus apuntes se mandan***", async () => {
  const cola = crearCola(crearAlmacenMemoria());
  cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: "de A" }, cuenta: "1:1" });
  cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota: "de A, otra" }, cuenta: "1:1" });

  // *B entra: **no se manda lo de A**, y lo de A no se borra.*
  const comoB = loQueSePuedeMandar(cola, "2:2");
  assert.equal(comoB.suyos.length, 0, "***con B dentro no sale nada de A***");
  assert.equal(cola.tamano(), 2, "***y no se pierde: espera a su dueño***");

  // *Y A vuelve.*
  const comoA = loQueSePuedeMandar(cola, "1:1");
  assert.equal(comoA.suyos.length, 2, "***los dos, enteros***");

  const loQueSeGuarda = {};
  const elResumen = await vaciarLaCola({
    suyos: comoA.suyos,
    cola,
    claveRechazados: laClaveConDueno("cuedigital.rechazados", "1:1"),
    api: async () => ({ ok: true, status: 200, json: async () => null }),
    leer: (clave, porDefecto) => (clave in loQueSeGuarda ? loQueSeGuarda[clave] : porDefecto),
    guardar: (clave, valor) => {
      loQueSeGuarda[clave] = valor;
    },
    sesionDeAhora: () => "1:1",
    sesionDelOrigen: "1:1",
    motivoDelRechazo: () => "no",
  });

  assert.equal(elResumen.mandados, 2, "***vuelto el dueño, se mandan los dos***");
  assert.equal(cola.tamano(), 0, "***y la cola queda vacía: se mandaron de verdad***");
});
