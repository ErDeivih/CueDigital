import { test } from "node:test";
import assert from "node:assert/strict";

import { crearAlmacenMemoria, crearCola, vaciarLaCola } from "../web/nucleo.js";

/**
 * ***D01 · el vaciado de la cola, con sus efectos por fuera*** (22/10/2026).
 *
 * *El vaciado vivía soldado a `api` dentro de `app.js` y **no se podía probar** sin arrancar la aplicación entera. Ahora
 * la decisión está en `nucleo.js` y lo de fuera se inyecta: **mandar, guardar, leer y mirar la sesión**.*
 *
 * ***Lo que se prueba aquí es lo que la revisión independiente reprodujo***: *un 422 de A que acaba guardado bajo la
 * clave de B, un apunte que se pierde cuando el almacén falla, y el cruce cuando la cuenta cambia a mitad del vaciado.*
 */

function unaColaCon(notas) {
  const cola = crearCola(crearAlmacenMemoria());
  for (const nota of notas) {
    cola.apuntar({ tipo: "labor", ruta: "/api/trabajos", datos: { nota }, cuenta: "1:1" });
  }
  return cola;
}

/** *Un almacén de mentira con su contenido a la vista, y la opción de que **guarde en silencio sin guardar**.* */
function unAlmacen({ fallaAlGuardar = false, loQueYaHabia = {} } = {}) {
  const datos = { ...loQueYaHabia };
  return {
    datos,
    leer(clave, porDefecto) {
      return clave in datos ? JSON.parse(datos[clave]) : porDefecto;
    },
    guardar(clave, valor) {
      // ***Se calla, que es lo que hace el de verdad cuando el almacén está lleno o bloqueado.***
      if (fallaAlGuardar) return;
      datos[clave] = JSON.stringify(valor);
    },
  };
}

/** *Una respuesta del servidor, ya hecha.* */
function unaRespuesta({ ok = false, status = 500, cuerpo = null } = {}) {
  return { ok, status, json: async () => cuerpo };
}

const LA_CLAVE_DE_A = "cuedigital.rechazados.1:1";
const LA_CLAVE_DE_B = "cuedigital.rechazados.2:2";

function elVaciadoDe(cola, almacen, { respuestas, sesionDeAhora = () => "1:1", clave = LA_CLAVE_DE_A } = {}) {
  let cual = 0;
  return vaciarLaCola({
    suyos: cola.leer(),
    cola,
    claveRechazados: clave,
    api: async () => respuestas[Math.min(cual++, respuestas.length - 1)],
    leer: almacen.leer,
    guardar: almacen.guardar,
    sesionDeAhora,
    sesionDelOrigen: "1:1",
    motivoDelRechazo: (cuerpo) => (cuerpo && cuerpo.detail) || "no se pudo",
  });
}

test("200: se manda, se quita de la cola y se cuenta", async () => {
  const cola = unaColaCon(["uno", "dos"]);
  const almacen = unAlmacen();

  const elResumen = await elVaciadoDe(cola, almacen, { respuestas: [unaRespuesta({ ok: true, status: 200 })] });

  assert.deepEqual(elResumen, { mandados: 2, apartados: 0, paradoPor: null });
  assert.equal(cola.tamano(), 0, "***lo mandado no puede quedarse esperando***");
});

test("422: se aparta como rechazo, con su identidad, y NO se pierde", async () => {
  const cola = unaColaCon(["la que rechazan"]);
  const almacen = unAlmacen();
  const elApunte = cola.leer()[0];

  const elResumen = await elVaciadoDe(cola, almacen, {
    respuestas: [unaRespuesta({ status: 422, cuerpo: { detail: "Falta el total." } })],
  });

  assert.equal(elResumen.apartados, 1);
  assert.equal(cola.tamano(), 0, "***apartado no es perdido: sale de pendientes y entra en rechazados***");

  const losRechazos = almacen.leer(LA_CLAVE_DE_A, []);
  assert.equal(losRechazos.length, 1);
  assert.equal(losRechazos[0].id_local, elApunte.id_local, "***con su identidad***");
  assert.equal(losRechazos[0].ruta, "/api/trabajos", "***y su ruta***");
  assert.equal(losRechazos[0].motivo, "Falta el total.", "***y el motivo del servidor***");
  assert.equal(losRechazos[0].estado, 422);
});

test("***y el rechazo va a la clave del ORIGEN, no a la de la cuenta que entró después***", async () => {
  // *Es el caso reproducido: el 422 de A acababa en `cuedigital.rechazados.2:2`.*
  const cola = unaColaCon(["la de A"]);
  const almacen = unAlmacen({ loQueYaHabia: { [LA_CLAVE_DE_B]: JSON.stringify([{ id_local: "de-B" }]) } });
  let lasVeces = 0;

  await elVaciadoDe(cola, almacen, {
    respuestas: [unaRespuesta({ status: 422, cuerpo: { detail: "No vale." } })],
    // ***El cambio ocurre DURANTE la espera***: *la comprobación del principio pasa con A, la petición sale, y cuando
    // la respuesta llega ya está B dentro. **Es la reproducción exacta**: si se parase antes, no habría nada que
    // cruzar.*
    sesionDeAhora: () => (lasVeces++ === 0 ? "1:1" : "2:2"),
    clave: LA_CLAVE_DE_A,
  });

  assert.equal(almacen.leer(LA_CLAVE_DE_A, []).length, 1, "***el rechazo de A, en la libreta de A***");
  assert.deepEqual(
    almacen.leer(LA_CLAVE_DE_B, []),
    [{ id_local: "de-B" }],
    "***y la de B, intacta: el rechazo de uno no se le enseña al otro***",
  );
});

test("***si el almacén falla al guardar, el apunte SE QUEDA en la cola***", async () => {
  // *Antes se quitaba de la cola y el rechazo no se guardaba: quedaba **sin pendiente y sin rechazo**.*
  const cola = unaColaCon(["el que se perdería"]);
  const almacen = unAlmacen({ fallaAlGuardar: true });

  const elResumen = await elVaciadoDe(cola, almacen, {
    respuestas: [unaRespuesta({ status: 422, cuerpo: { detail: "No vale." } })],
  });

  assert.equal(elResumen.paradoPor, "no-se-pudo-apartar");
  assert.equal(cola.tamano(), 1, "***no se pierde: se queda esperando, que es lo que se puede hacer***");
});

test("401 y 403 paran el vaciado y NO se toman por rechazo", async () => {
  const cola = unaColaCon(["la de siempre"]);
  const almacen = unAlmacen();

  const elResumen = await elVaciadoDe(cola, almacen, { respuestas: [unaRespuesta({ status: 401 })] });

  assert.equal(elResumen.paradoPor, "sin-permiso");
  assert.equal(cola.tamano(), 1, "***tirar una orden válida del agricultor es lo que no se hace***");
  assert.equal(almacen.leer(LA_CLAVE_DE_A, []).length, 0, "***y no se apunta como rechazo***");
});

test("***si la cuenta cambia A MITAD, se para y no se manda el resto***", async () => {
  const cola = unaColaCon(["uno", "dos"]);
  const almacen = unAlmacen();
  let lasVeces = 0;

  const elResumen = await elVaciadoDe(cola, almacen, {
    respuestas: [unaRespuesta({ ok: true, status: 200 })],
    // *La primera vez que se mira, sigue A; a partir de la segunda, ya ha entrado B.*
    sesionDeAhora: () => (lasVeces++ === 0 ? "1:1" : "2:2"),
  });

  assert.equal(elResumen.paradoPor, "cambio-de-cuenta");
  assert.equal(elResumen.mandados, 1, "***solo el primero, que era el de A***");
  assert.equal(cola.tamano(), 1, "***y el segundo se queda para cuando vuelva su dueño***");
});

test("un 5xx para el vaciado sin apartar nada, y una red caída también", async () => {
  const cola = unaColaCon(["uno"]);
  const almacen = unAlmacen();

  const conServidorMalo = await elVaciadoDe(cola, almacen, { respuestas: [unaRespuesta({ status: 503 })] });
  assert.equal(conServidorMalo.paradoPor, "servidor");
  assert.equal(cola.tamano(), 1);

  const sinRed = await vaciarLaCola({
    suyos: cola.leer(),
    cola,
    claveRechazados: LA_CLAVE_DE_A,
    api: async () => {
      throw new TypeError("Failed to fetch");
    },
    leer: almacen.leer,
    guardar: almacen.guardar,
    sesionDeAhora: () => "1:1",
    sesionDelOrigen: "1:1",
    motivoDelRechazo: () => "no",
  });
  assert.equal(sinRed.paradoPor, "sin-red");
  assert.equal(cola.tamano(), 1, "***sin red no se pierde nada: se reintenta luego***");
});
