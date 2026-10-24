/*
 * cola_en_indexeddb.js — La cola de apuntes y el turno, **en IndexedDB** (23/10/2026, D01).
 *
 * POR QUÉ ESTE FICHERO
 *
 * La cola guardaba **un array** en `localStorage`: apuntar era leerlo, añadir y escribirlo, y **dos pestañas que apuntan
 * a la vez se pisan** — una intención desaparece sin ruido. Y **no se arregla releyendo**: el diagnóstico de la revisión
 * devuelve, en la lectura, el valor **anterior** a la escritura del otro, así que la segunda lectura también puede ser
 * vieja. *Releer y fusionar solo cubre la intercalación de la **primera** lectura.*
 *
 * Y el turno (una pestaña vacía a la vez) tenía el mismo mal: **los dos leen «no hay turno» y los dos escriben**.
 *
 * LO QUE CAMBIA AQUÍ
 *
 *   · **las intenciones**: *cada una es un registro suyo, y `apuntar`/`quitar` **no leen nada** — un `add` y un `delete`
 *     sobre su clave—. *Dos escrituras sobre registros distintos no se pueden pisar*;*
 *   · **el turno**: *se lee y se escribe **dentro de la misma transacción** (`readwrite` sobre su registro), que es
 *     **atómico por definición**: ninguna otra pestaña se puede intercalar. Es la pieza que el `localStorage` no podía
 *     dar y por la que la exclusión no se podía demostrar.*
 *
 * Y LO QUE NO PROMETE
 *
 * *Si no hay IndexedDB, **esto no se usa y la aplicación no dice que vacía una sola pestaña**.* La revisión es explícita:
 * «no prometer exclusión con un `fallback` al mismo `read/modify/write`».
 */

const NOMBRE_DE_LA_BASE = "cuedigital";
const LA_VERSION = 1;
const ALMACEN_DE_INTENCIONES = "intenciones";
const ALMACEN_DEL_TURNO = "turno";

/** *¿Se puede usar IndexedDB aquí?* */
export function hayIndexedDb() {
  try {
    return typeof indexedDB !== "undefined" && indexedDB !== null;
  } catch (error) {
    return false;
  }
}

/** *Abre la base -y la crea la primera vez con sus dos almacenes-.* */
export function abrirLaBase() {
  return new Promise((resolver, rechazar) => {
    if (!hayIndexedDb()) {
      rechazar(new Error("sin IndexedDB"));
      return;
    }
    const laPeticion = indexedDB.open(NOMBRE_DE_LA_BASE, LA_VERSION);
    laPeticion.onupgradeneeded = () => {
      const base = laPeticion.result;
      if (!base.objectStoreNames.contains(ALMACEN_DE_INTENCIONES)) {
        base.createObjectStore(ALMACEN_DE_INTENCIONES, { keyPath: "id_local" });
      }
      if (!base.objectStoreNames.contains(ALMACEN_DEL_TURNO)) {
        base.createObjectStore(ALMACEN_DEL_TURNO, { keyPath: "clave" });
      }
    };
    laPeticion.onsuccess = () => resolver(laPeticion.result);
    laPeticion.onerror = () => rechazar(laPeticion.error);
  });
}

/**
 * ***La base transaccional del turno***: *lo que come `pedirElTurnoTransaccional` de `nucleo.js`.*
 *
 * *Lee y escribe **dentro de una sola transacción** `readwrite`: **entre la lectura y la escritura no se puede meter
 * nadie**, y eso es lo que hace que la exclusión sea demostrable.*
 */
export function baseDelTurno(base) {
  return {
    transaccion(clave, cambia) {
      return new Promise((resolver, rechazar) => {
        let elAnterior = null;
        let elNuevo = null;
        const laTransaccion = base.transaction([ALMACEN_DEL_TURNO], "readwrite");
        const elAlmacen = laTransaccion.objectStore(ALMACEN_DEL_TURNO);
        const laLectura = elAlmacen.get(clave);
        laLectura.onsuccess = () => {
          elAnterior = laLectura.result ? { ...laLectura.result } : null;
          const loQueToca = cambia(elAnterior ? { ...elAnterior } : null);
          if (loQueToca === undefined) {
            elNuevo = elAnterior;
            return;
          }
          if (loQueToca === null) {
            elNuevo = null;
            elAlmacen.delete(clave);
            return;
          }
          elNuevo = { ...loQueToca, clave };
          elAlmacen.put(elNuevo);
        };
        laLectura.onerror = () => rechazar(laLectura.error);
        laTransaccion.oncomplete = () => resolver({ anterior: elAnterior, nuevo: elNuevo });
        laTransaccion.onerror = () => rechazar(laTransaccion.error);
        laTransaccion.onabort = () => rechazar(laTransaccion.error || new Error("transacción abortada"));
      });
    },
  };
}

/**
 * ***La cola de intenciones***, con la misma cara que `crearColaPorIntenciones`: `leer`, `apuntar`, `quitar`, `tamano`,
 * `vaciar` y `migrarDesde`.
 *
 * *`apuntar` y `quitar` **no leen**: `add`/`put` y `delete` sobre el registro de esa intención. Es la propiedad que hace
 * que dos pestañas no se pisen, y **no depende de que la lectura sea fresca** — porque no hay lectura.*
 */
export function colaEnIndexedDb(base, opciones = {}) {
  const reloj = opciones.reloj || (() => new Date().toISOString());

  function unaTransaccion(modo, hacer) {
    return new Promise((resolver, rechazar) => {
      const laTransaccion = base.transaction([ALMACEN_DE_INTENCIONES], modo);
      const elAlmacen = laTransaccion.objectStore(ALMACEN_DE_INTENCIONES);
      let elResultado;
      try {
        elResultado = hacer(elAlmacen);
      } catch (error) {
        rechazar(error);
        return;
      }
      laTransaccion.oncomplete = () => resolver(elResultado);
      laTransaccion.onerror = () => rechazar(laTransaccion.error);
      laTransaccion.onabort = () => rechazar(laTransaccion.error || new Error("transacción abortada"));
    });
  }

  return {
    leer() {
      return unaTransaccion("readonly", (elAlmacen) => {
        const los = [];
        const laPeticion = elAlmacen.openCursor();
        laPeticion.onsuccess = () => {
          const elCursor = laPeticion.result;
          if (!elCursor) return;
          los.push(elCursor.value);
          elCursor.continue();
        };
        return los;
      });
    },

    async tamano() {
      const los = await this.leer();
      return los.length;
    },

    /** ***Apunta, sin leer.*** *Es lo que hace que dos apuntes a la vez no se pisen.* */
    apuntar(apunte) {
      const idLocal = apunte.id_local || opciones.nuevoId();
      const conId = {
        ...apunte,
        id_local: idLocal,
        apuntado_en: apunte.apuntado_en || reloj(),
        datos:
          apunte.datos && typeof apunte.datos === "object" && !apunte.datos.clave_de_reenvio
            ? { ...apunte.datos, clave_de_reenvio: idLocal }
            : apunte.datos,
      };
      return unaTransaccion("readwrite", (elAlmacen) => {
        elAlmacen.put(conId);
        return conId;
      }).then((elGuardado) => ({ ...elGuardado, guardado: true, durable: true }));
    },

    /** ***Quita lo suyo, y solo lo suyo***: *`delete` de su clave.* */
    quitar(idLocal) {
      return unaTransaccion("readwrite", (elAlmacen) => {
        elAlmacen.delete(idLocal);
        return true;
      });
    },

    vaciar() {
      return unaTransaccion("readwrite", (elAlmacen) => {
        elAlmacen.clear();
        return true;
      });
    },

    /**
     * ***Trae lo que había en `localStorage`***: *el array viejo, y también las claves por intención de la versión
     * anterior. **No se borra el origen hasta comprobar que están todos**, y **un JSON corrupto se conserva** —no se
     * convierte en una cola vacía que la siguiente escritura pisaría—.*
     */
    async migrarDesde(almacenViejo, claveVieja = "cuedigital.pendientes") {
      if (!almacenViejo || !almacenViejo.getItem) return { migrados: 0, corrupto: false, borrado: false };
      const losViejos = [];
      let corrupto = false;
      let bruto = null;
      try {
        bruto = almacenViejo.getItem(claveVieja);
      } catch (error) {
        bruto = null;
      }
      if (bruto !== null && bruto !== undefined) {
        if (Array.isArray(bruto)) losViejos.push(...bruto);
        else {
          try {
            const leido = JSON.parse(bruto);
            if (Array.isArray(leido)) losViejos.push(...leido);
            else corrupto = true;
          } catch (error) {
            corrupto = true;
          }
        }
      }
      // *Y las claves por intención de la versión anterior, que también pueden estar.*
      const cuantas = Number(almacenViejo.length) || 0;
      for (let i = 0; i < cuantas; i += 1) {
        let clave = null;
        try {
          clave = almacenViejo.key(i);
        } catch (error) {
          clave = null;
        }
        if (typeof clave !== "string" || !clave.startsWith("cuedigital.pendiente.")) continue;
        try {
          const uno = JSON.parse(almacenViejo.getItem(clave));
          if (uno && typeof uno === "object") losViejos.push(uno);
        } catch (error) {
          corrupto = true;
        }
      }
      let migrados = 0;
      for (const viejo of losViejos) {
        if (!viejo || typeof viejo !== "object") continue;
        try {
          await this.apuntar(viejo);
          migrados += 1;
        } catch (error) {
          // *Si no se puede guardar, no se borra nada del origen.*
        }
      }
      // *Solo se borra el origen si están **todos**.*
      const losQueTienen = await this.leer();
      const losIds = new Set(losQueTienen.map((uno) => String(uno.id_local)));
      const estanTodos = losViejos
        .filter((v) => v && typeof v === "object" && v.id_local)
        .every((v) => losIds.has(String(v.id_local)));
      let borrado = false;
      if (estanTodos && !corrupto) {
        try {
          almacenViejo.removeItem(claveVieja);
          borrado = true;
        } catch (error) {
          borrado = false;
        }
      }
      return { migrados, corrupto, borrado };
    },
  };
}
