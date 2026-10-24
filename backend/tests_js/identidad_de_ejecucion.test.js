import { test } from "node:test";
import assert from "node:assert/strict";

import {
  crearAlmacenMemoria,
  duenoDelTurno,
  identidadDeEjecucion,
  identidadPersistente,
} from "../web/nucleo.js";

/**
 * ***D01 · la identidad que no se copia con `opener`*** (23/10/2026).
 *
 * *`sessionStorage` **se copia al abrir una ventana con `opener`**: padre e hija comparten `cuedigital.procesador`, así
 * que las dos pedían el turno **como la misma pestaña** y las dos lo recibían.*
 *
 * *La separación es la que lo cierra: **la de ejecución vive en memoria** —ninguna copia de almacenamiento la trae— y la
 * persistente sirve solo para reconocer una **recarga**.*
 */

test("***la identidad de ejecución es la misma dentro de una carga***", () => {
  assert.equal(identidadDeEjecucion(), identidadDeEjecucion(), "***es estable: la misma ejecución, la misma***");
  assert.match(identidadDeEjecucion(), /./);
});

test("***y la persistente se guarda aparte, para reconocer la recarga***", () => {
  const elAlmacen = crearAlmacenMemoria();
  const una = identidadPersistente(elAlmacen);
  const otra = identidadPersistente(elAlmacen);
  assert.equal(una, otra, "***al recargar se lee la misma: la pestaña se reconoce***");
  assert.match(una, /./);
});

test("***dos ventanas con la MISMA pestaña persistente no son el mismo dueño***", () => {
  // *El caso de `opener`: la persistente **copiada**, la ejecución **de cada una**.*
  const laCopiada = "la-misma-pestana";
  const elPadre = duenoDelTurno({
    cuenta: "1:1",
    instalacion: "inst",
    persistente: laCopiada,
    ejecucion: "ejecucion-padre",
  });
  const laHija = duenoDelTurno({
    cuenta: "1:1",
    instalacion: "inst",
    persistente: laCopiada,
    ejecucion: "ejecucion-hija",
  });

  assert.notEqual(
    elPadre,
    laHija,
    "***padre e hija comparten cuenta, instalación Y sessionStorage: aun así tienen que ser dueños distintos***",
  );
});

test("y el mismo proceso conserva su dueño: el turno se puede renovar", () => {
  const uno = duenoDelTurno({ cuenta: "1:1", instalacion: "inst", persistente: "p", ejecucion: "e" });
  const dos = duenoDelTurno({ cuenta: "1:1", instalacion: "inst", persistente: "p", ejecucion: "e" });
  assert.equal(uno, dos, "***el que ya tenía el turno lo renueva: no se bloquea a sí mismo***");
});
