/**
 * nucleo.js — La lógica de la aplicación que NO toca el navegador.
 *
 * Está separado de `app.js` a propósito: aquí está todo lo que se puede probar sin
 * abrir un navegador (formato de números y fechas, la cola de lo que queda pendiente
 * cuando no hay cobertura, repetir el último apunte, las comprobaciones que se pueden
 * hacer sin preguntar al servidor). Se prueba con `node --test tests_js/`.
 *
 * Regla: este fichero no usa `document`, `window` ni `fetch`. Si alguna vez hace
 * falta, se le pasa desde fuera.
 */

/** Formatea un número a la española: 0.8 -> "0,80", 1234.5 -> "1.234,50". */
export function formateaNumero(valor, decimales = 2) {
  if (valor === null || valor === undefined || valor === "") return "";
  const numero = typeof valor === "number" ? valor : Number(String(valor).replace(",", "."));
  if (!Number.isFinite(numero)) return "";
  const partes = numero.toFixed(decimales).split(".");
  partes[0] = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return partes.join(",");
}

/**
 * Convierte lo que escribe el agricultor en un número.
 *
 * En un teclado español se escribe "0,8", no "0.8". Sin esto, media aplicación
 * fallaría con el número más natural de escribir.
 *
 * Regla, y conviene entenderla porque tiene una ambigüedad inevitable:
 *
 *  - Si hay coma, la coma es el decimal y los puntos son millares: "1.234,5" -> 1234.5
 *  - Si hay varios puntos, todos son millares: "1.234.567" -> 1234567
 *  - Si hay UN punto con TRES decimales, se lee como millares, que es como se
 *    escribe en España: "1.234" -> 1234
 *  - Con cualquier otra longitud, el punto es decimal: "0.8" -> 0.8, "2.4317" -> 2.4317
 *
 * La ambigüedad de "1.234" es real y no se puede resolver sola. Se resuelve a favor
 * de los millares porque en kilos de abono (300, 1.000) es lo habitual, y porque si
 * alguien quería 1,234 hectáreas la comprobación de que no se puede tratar más
 * superficie de la que tiene la parcela lo caza al instante y con un aviso claro.
 *
 * Por eso, además, la pantalla enseña el número que ha entendido antes de apuntarlo.
 */
export function aNumero(texto) {
  if (texto === null || texto === undefined) return null;
  if (typeof texto === "number") return Number.isFinite(texto) ? texto : null;

  const limpio = String(texto).trim().replace(/\s/g, "");
  if (limpio === "") return null;

  let normalizado;
  if (limpio.includes(",")) {
    normalizado = limpio.replace(/\./g, "").replace(",", ".");
  } else {
    const cuantosPuntos = limpio.split(".").length - 1;
    if (cuantosPuntos === 0) {
      normalizado = limpio;
    } else if (cuantosPuntos > 1) {
      normalizado = limpio.replace(/\./g, "");
    } else {
      const [entera, decimal] = limpio.split(".");
      normalizado = decimal.length === 3 ? entera + decimal : `${entera}.${decimal}`;
    }
  }

  const numero = Number(normalizado);
  return Number.isFinite(numero) ? numero : null;
}

/** Fecha ISO (2026-05-01) -> "01/05/2026". */
export function formateaFecha(iso) {
  if (!iso) return "";
  const partes = String(iso).slice(0, 10).split("-");
  if (partes.length !== 3) return String(iso);
  return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

/** Fecha ISO -> "1 de mayo". Para textos que se leen, no para columnas. */
const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export function fechaEnPalabras(iso) {
  if (!iso) return "";
  const partes = String(iso).slice(0, 10).split("-");
  if (partes.length !== 3) return String(iso);
  const mes = MESES[Number(partes[1]) - 1] || "";
  return `${Number(partes[2])} de ${mes}`;
}

/** Días que faltan desde hoy hasta una fecha ISO. Negativo si ya pasó. */
export function diasHasta(iso, hoyISO) {
  if (!iso) return null;
  const destino = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
  const origen = new Date(`${hoyISO}T00:00:00`);
  if (Number.isNaN(destino.getTime()) || Number.isNaN(origen.getTime())) return null;
  return Math.round((destino - origen) / 86400000);
}

/** Suma días a una fecha ISO y devuelve otra fecha ISO. */
export function sumaDias(iso, dias) {
  const fecha = new Date(`${String(iso).slice(0, 10)}T00:00:00`);
  if (Number.isNaN(fecha.getTime())) return iso;
  fecha.setDate(fecha.getDate() + dias);
  return [fecha.getFullYear(), String(fecha.getMonth() + 1).padStart(2, "0"), String(fecha.getDate()).padStart(2, "0")].join("-");
}

// ---------------------------------------------------------------------------
// La cola de lo que queda por mandar
// ---------------------------------------------------------------------------

/**
 * Almacén en memoria con la misma cara que localStorage.
 *
 * Sirve para dos cosas: probar la cola sin navegador, y que la aplicación siga
 * funcionando (sin guardar nada, pero sin romperse) cuando el navegador tiene el
 * almacenamiento bloqueado, que pasa en modo privado.
 */
export function crearAlmacenMemoria(inicial = {}) {
  const datos = { ...inicial };
  return {
    // ***Y dice que NO es durable*** (21/10/2026): *esto es memoria del proceso; al cerrar el navegador se
    // pierde. Quien guarde aquí **no puede prometer que se guardó**, y sin esta marca no había forma de
    // distinguirlo de un `localStorage` de verdad —que es el falso éxito que el encargo reproduce-.*
    esDurable: false,
    getItem: (clave) => (clave in datos ? datos[clave] : null),
    setItem: (clave, valor) => {
      datos[clave] = String(valor);
    },
    removeItem: (clave) => {
      delete datos[clave];
    },
    // ***Y deja enumerar*** (23/10/2026, D01): *una cola de **una clave por intención** necesita poder recorrer las
    // claves, y sin esto el almacén de las pruebas no se parece al `localStorage` de verdad, que sí las da.*
    get length() {
      return Object.keys(datos).length;
    },
    key: (indice) => Object.keys(datos)[indice] ?? null,
  };
}

/**
 * ***Un identificador de comando, único aunque dos pestañas arranquen en el mismo milisegundo*** (21/10/2026).
 *
 * *Antes era `p${contador}-${new Date().toISOString()}`: **un contador que se reinicia** con cada pestaña y un
 * reloj que dos instancias comparten. Se reprodujo: **dos instancias generaban el mismo `id_local`, y confirmar
 * uno eliminaba los dos**.*
 *
 * *Aleatorio, y de la fuente criptográfica cuando la hay: `crypto.randomUUID`; si no, dos trozos de
 * `Math.random`. **Lo aleatorio no se reinicia al recargar**, que es lo que hacía falta.*
 */
export function unIdDeComando() {
  try {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
      return globalThis.crypto.randomUUID();
    }
  } catch (error) {
    // *Sin criptografía se sigue: hay respaldo.*
  }
  const unTrozo = () => Math.random().toString(36).slice(2, 10);
  return `c-${unTrozo()}-${unTrozo()}-${Date.now().toString(36)}`;
}

/**
 * La cola de apuntes que todavía no se han mandado.
 *
 * El agricultor apunta en el campo, sin cobertura. El apunte se guarda aquí y se
 * manda solo cuando vuelve a haber red. Se guarda en el móvil (localStorage), no en
 * memoria, porque si cierra el navegador lo apuntado no se puede perder.
 */
export function crearCola(almacen, opciones = {}) {
  const clave = opciones.clave || "cuedigital.pendientes";
  const reloj = opciones.reloj || (() => new Date().toISOString());
  const contador = { n: 0 };
  // ***Si el almacén sobrevive a cerrar el navegador*** (21/10/2026): *un `localStorage` sí; la memoria no. Si el
  // almacén no dice nada, se da por durable: los `localStorage` de verdad y los dobles de las pruebas lo son.*
  const esDurable = almacen.esDurable !== false;

  function leer() {
    try {
      const bruto = almacen.getItem(clave);
      if (!bruto) return [];
      const lista = JSON.parse(bruto);
      return Array.isArray(lista) ? lista : [];
    } catch (error) {
      // Si lo guardado está corrupto, se empieza de cero en vez de dejar la
      // aplicación bloqueada sin poder apuntar nada.
      return [];
    }
  }

  function escribir(lista) {
    try {
      almacen.setItem(clave, JSON.stringify(lista));
      return true;
    } catch (error) {
      return false;
    }
  }

  return {
    leer,
    tamano: () => leer().length,

    /**
     * ***Apunta algo para mandarlo, y DICE SI SE GUARDÓ*** (19/10/2026).
     *
     * ### ***Dos cosas que antes no hacía, y las dos costaban datos***
     *
     * ***1 · Decía que sí siempre.*** *`escribir` devuelve `false` cuando el almacén falla -modo privado,
     * almacenamiento lleno, un navegador que lo bloquea-, y **ese resultado se tiraba**: el agricultor creía que
     * había apuntado y **el apunte no existía**. Ahora se devuelve `guardado` y quien llama lo cuenta.*
     *
     * ***2 · No llevaba clave de reenvío.*** *El servidor sabe reconocer un reintento por `clave_de_reenvio`
     * (`reenvios.la_misma_accion`), y la cola **no la mandaba**: una respuesta perdida que provoca un reintento
     * -o **dos pestañas vaciando la misma cola**- mandaba lo mismo dos veces. Se sella con el `id_local`, que es
     * único y estable, **y si quien llama ya trae una, se respeta**.*
     */
    apuntar(apunte) {
      const lista = leer();
      contador.n += 1;
      // ***Y el id, aleatorio***: *no un contador que se reinicia con cada pestaña y un reloj que dos instancias
      // comparten. Con `unIdDeComando`, dos pestañas abiertas en el mismo milisegundo **no pueden generar el
      // mismo**, y confirmar uno no elimina los dos.*
      const idLocal = apunte.id_local || unIdDeComando();
      const conId = {
        ...apunte,
        id_local: idLocal,
        apuntado_en: apunte.apuntado_en || reloj(),
        datos:
          apunte.datos && typeof apunte.datos === "object" && !apunte.datos.clave_de_reenvio
            ? { ...apunte.datos, clave_de_reenvio: idLocal }
            : apunte.datos,
      };
      // ***Se relee JUSTO ANTES de escribir*** (22/10/2026, D01): *esto hacía leer → añadir → escribir, y si otra
      // pestaña apuntaba **entre la lectura y la escritura**, su intención **desaparecía** porque aquí se escribía el
      // array leído antes. La revisión lo reprodujo con un almacén controlado: **dos intenciones, un pendiente**.*
      //
      // *Volver a leer aquí -y añadir sobre lo fresco- conserva las dos. Y si la nuestra ya está (dos llamadas con el
      // mismo `id_local`), no se duplica.*
      const loFresco = leer();
      const yaEsta = loFresco.some((uno) => uno && uno.id_local === idLocal);
      const guardado = escribir(yaEsta ? loFresco : [...loFresco, conId]);
      // ***`guardado` y `durable` son dos cosas distintas*** (21/10/2026): *en memoria **se escribe** -no lanza- y
      // **se pierde al cerrar**. Devolver solo `guardado` era la mentira reproducida: el agricultor leía «guardado
      // en el móvil» y no había nada. **Quien prometa guardado tiene que mirar los dos.***
      return { ...conId, guardado, durable: guardado && esDurable };
    },

    quitar(idLocal) {
      escribir(leer().filter((apunte) => apunte.id_local !== idLocal));
    },

    vaciar() {
      escribir([]);
    },
  };
}

/**
 * Qué toca hacer con lo que hay pendiente.
 *
 * Devolver una decisión en vez de actuar es lo que permite probarlo: la interfaz
 * solo tiene que obedecer.
 */
export function decideQueHacer(cola, hayRed) {
  const cuantos = cola.tamano();
  if (cuantos === 0) return { accion: "nada", cuantos: 0 };
  if (!hayRed) return { accion: "esperar", cuantos };
  return { accion: "mandar", cuantos };
}

/**
 * ***Qué apuntes de la cola se pueden mandar con ESTA sesión*** (19/10/2026).
 *
 * ### ***El fallo, tal y como se reproducía***
 *
 * *La cola guardaba `{tipo, ruta, datos}` **sin decir de qué cuenta era cada apunte**, y `mandarPendientes` los
 * mandaba **todos con el vale que hubiera en ese momento**. Un trabajo apuntado sin cobertura en una finca,
 * mandado al reconectar con otra cuenta, **se escribía en la finca equivocada** -o se quedaba en un 404 sin que
 * nadie supiera por qué-. **Y en una aplicación donde el dinero y las labores son de cada finca, eso no es un
 * detalle de pantalla.***
 *
 * ### ***Y por eso hay tres montones, no dos***
 *
 *   · **`suyos`**: *los de la sesión abierta. **Son los únicos que se mandan.***
 *   · **`deOtraCuenta`**: *no se mandan **y no se borran**: se quedan esperando a que su dueño entre. **Perder un
 *     apunte del agricultor en silencio es lo que esta aplicación no puede hacer.***
 *   · **`sinCuenta`**: *los apuntados **antes** de esta corrección. **No se sabe de quién son, así que mandarlos
 *     sería adivinar**, y adivinar aquí es escribir en una finca que no es. Se quedan y se dicen.*
 *
 * *Es una función pura: **la interfaz solo tiene que obedecer**, y se puede probar sin navegador.*
 */
/** Lee usuario y finca del formato carga.firma que emite security.crear_token.
 * Solo identifica el contexto local; la firma y el permiso los comprueba el servidor.
 */
/**
 * ***¿Hay que cerrar la sesión con este 401?*** (21/10/2026, D03).
 *
 * *El encargo: «un **401 antiguo** tampoco debe cerrar una cuenta nueva que entró mientras la petición estaba en
 * vuelo».*
 *
 * *Y pasaba: `api` cerraba sesión con **cualquier** 401. El vaciado de la cola manda con **el vale capturado al
 * empezar** -para que un cambio de cuenta no se cuele-, así que si ese vale viejo vuelve con un 401, **se le cierra
 * la sesión a la cuenta nueva, que no ha fallado**.*
 *
 * ***La regla***: *solo se cierra si el vale que falló es **el de ahora**. Y si no hay vale que falló, **no se
 * cierra**: es preferible que tenga que volver a entrar a cerrarle una sesión buena.*
 */
export function hayQueCerrarLaSesion(elTokenQueFallo, elTokenDeAhora) {
  if (!elTokenQueFallo) return false;
  return elTokenQueFallo === elTokenDeAhora;
}

export function sesionDelToken(token) {
  if (!token || typeof token !== "string") return null;
  const partes = token.split(".");
  if (partes.length !== 2) return null;
  try {
    // *El trozo de en medio va en base64url; `atob` quiere base64 normal y el relleno.*
    const carga = partes[0].replace(/-/g, "+").replace(/_/g, "/");
    const conRelleno = carga.padEnd(Math.ceil(carga.length / 4) * 4, "=");
    const texto = globalThis.atob(conRelleno);
    const datos = JSON.parse(texto);
    if (datos.uid === undefined || datos.uid === null) return null;
    if (datos.eid === undefined || datos.eid === null) return null;
    return `${datos.uid}:${datos.eid}`;
  } catch (error) {
    // *Un vale que no se puede leer no es una sesión: es `null`, y se trata como tal.*
    return null;
  }
}

/**
 * ***La cola, con una clave por intención*** (23/10/2026, D01 — P0).
 *
 * ### ***El defecto que esto cierra, y por qué no lo cerraba releer***
 *
 * *La cola guardaba **un array** en una clave: apuntar era **leer el array, añadir y escribir el array**. Dos pestañas
 * que apuntan a la vez **leen lo mismo y una pisa a la otra**, y la intención perdida **desaparece sin ruido**.*
 *
 * ***Y no se arregla releyendo***: *el diagnóstico de la revisión devuelve, en la lectura, **el valor anterior** a la
 * escritura del otro — la intercalación ocurre **dentro de la lectura**—, así que la segunda lectura **también puede ser
 * vieja**. *Releer y fusionar solo cubre la intercalación de la **primera** lectura, que es lo que probaban las pruebas
 * anteriores.*
 *
 * ### ***Lo que sí lo cierra***
 *
 * *Cada intención vive **en su propia clave**, y:*
 *
 *   · **apuntar** = *`setItem` de su clave* — **sin leer nada**;
 *   · **quitar** = *`removeItem` de su clave* — **sin leer nada**;
 *   · **leer** = *recorrer las claves con el prefijo* — **sin escribir nada**.
 *
 * ***Dos escrituras sobre claves distintas no se pueden pisar***: *es la propiedad que hay que tener, y **no depende de
 * que la lectura sea fresca**.*
 *
 * ***Lo que necesita del almacén***: *`getItem`, `setItem`, `removeItem` **y poder enumerar** (`length` y `key(i)`, como
 * el `localStorage` de verdad). Sin enumerar no hay forma de listar sin volver al array compartido.*
 */
export function crearColaPorIntenciones(almacen, opciones = {}) {
  const prefijo = opciones.prefijo || "cuedigital.pendiente.";
  const reloj = opciones.reloj || (() => new Date().toISOString());
  const esDurable = almacen.esDurable !== false;

  /** *Las claves que son de esta cola.* */
  function lasClaves() {
    const claves = [];
    let cuantas = 0;
    try {
      cuantas = Number(almacen.length) || 0;
    } catch (error) {
      cuantas = 0;
    }
    for (let i = 0; i < cuantas; i += 1) {
      let clave = null;
      try {
        clave = almacen.key(i);
      } catch (error) {
        clave = null;
      }
      if (typeof clave === "string" && clave.startsWith(prefijo)) claves.push(clave);
    }
    return claves;
  }

  const laClaveDe = (idLocal) => `${prefijo}${idLocal}`;

  return {
    prefijo,

    /**
     * ***Lo que hay, recorriendo las claves.*** *Un valor corrupto **no se tira y no se reescribe**: se deja donde está
     * -para poder recuperarlo- y se aparta del listado, **diciéndolo** con `corruptos`.*
     */
    leer() {
      // ***Y si queda cola vieja, se trae al leer*** (23/10/2026): *migrar solo al arrancar dejaba fuera lo que apareciera
      // después -otra pestaña con la versión anterior, o un arranque que no llegó a migrar-. **Es idempotente**: si ya está
      // migrada, el origen no está y esto no hace nada.*
      this.migrarSiHaceFalta(almacen);
      const apuntes = [];
      for (const clave of lasClaves()) {
        try {
          const apunte = JSON.parse(almacen.getItem(clave));
          if (apunte && typeof apunte === "object") apuntes.push(apunte);
        } catch (error) {
          // *Corrupto: **se conserva** y no se toca. La siguiente escritura es de OTRA clave.*
        }
      }
      return apuntes;
    },

    /** *Las claves cuyo contenido no se puede leer: **no se pierden, pero no se pueden mandar**.* */
    losCorruptos() {
      const malos = [];
      for (const clave of lasClaves()) {
        try {
          const apunte = JSON.parse(almacen.getItem(clave));
          if (!apunte || typeof apunte !== "object") malos.push(clave);
        } catch (error) {
          malos.push(clave);
        }
      }
      return malos;
    },

    tamano() {
      return this.leer().length;
    },

    /**
     * ***Apunta, sin leer.*** *Es lo que hace que dos apuntes a la vez **no se pisen**: la escritura es de su propia
     * clave y no depende de lo que hubiera.*
     */
    apuntar(apunte) {
      const idLocal = apunte.id_local || unIdDeComando();
      const conId = {
        ...apunte,
        id_local: idLocal,
        apuntado_en: apunte.apuntado_en || reloj(),
        datos:
          apunte.datos && typeof apunte.datos === "object" && !apunte.datos.clave_de_reenvio
            ? { ...apunte.datos, clave_de_reenvio: idLocal }
            : apunte.datos,
      };
      let guardado = false;
      try {
        almacen.setItem(laClaveDe(idLocal), JSON.stringify(conId));
        // ***Y no se comprueba leyendo*** (23/10/2026): *una lectura puede ser **vieja** -es el defecto que se está
        // cerrando-, así que comprobar con ella daría «no guardado» sobre algo guardado. `setItem` **no lanza** cuando
        // guarda: si no lanza, está guardado.*
        guardado = true;
      } catch (error) {
        guardado = false;
      }
      return { ...conId, guardado, durable: guardado && esDurable };
    },

    /** ***Quita lo suyo, y solo lo suyo***: *`removeItem` de su clave, sin leer ni reescribir lo demás.* */
    quitar(idLocal) {
      try {
        almacen.removeItem(laClaveDe(idLocal));
        return almacen.getItem(laClaveDe(idLocal)) === null;
      } catch (error) {
        return false;
      }
    },

    /** *Borra lo de esta cola: **clave a clave**, enumerando.* */
    vaciar() {
      for (const clave of lasClaves()) {
        try {
          almacen.removeItem(clave);
        } catch (error) {
          /* si no se puede, se queda: no se finge que se ha vaciado */
        }
      }
    },

    /**
     * ***Trae lo que había en la cola vieja*** (el array), **sin perder nada y sin borrarla hasta comprobarlo**.
     *
     * *Cada apunte pasa con **su `id_local`, su cuenta, sus datos y su `clave_de_reenvio`**, tal cual. Después se
     * **relee uno a uno** y solo si están todos se borra el array viejo.*
     *
     * ***Un JSON corrupto no se convierte en una cola vacía***: *se deja el original donde está y se dice, porque
     * **la siguiente escritura lo sobrescribiría** y lo perdido no se podría recuperar.*
     */
    /** *Migra la cola vieja **si queda**, y solo si queda. Lo llaman `leer` y el arranque.* */
    migrarSiHaceFalta(almacenViejo, claveVieja = "cuedigital.pendientes") {
      let hay = null;
      try {
        hay = almacenViejo && almacenViejo.getItem ? almacenViejo.getItem(claveVieja) : null;
      } catch (error) {
        hay = null;
      }
      if (hay === null || hay === undefined) return null;
      return this.migrarDesde(almacenViejo, claveVieja);
    },

    migrarDesde(almacenViejo, claveVieja = "cuedigital.pendientes") {
      let bruto = null;
      try {
        bruto = almacenViejo.getItem(claveVieja);
      } catch (error) {
        bruto = null;
      }
      if (bruto === null) return { migrados: 0, corrupto: false, borrado: false };
      let viejos = null;
      if (Array.isArray(bruto)) {
        // ***El almacén puede devolver el valor ya como objeto*** (23/10/2026): *el de las pruebas lo guarda tal cual, y
        // suponer que siempre es texto convertía una cola buena en «corrupta».*
        viejos = bruto;
      } else {
        try {
          viejos = JSON.parse(bruto);
        } catch (error) {
          // *No se toca: se conserva para poder recuperarlo a mano.*
          return { migrados: 0, corrupto: true, borrado: false };
        }
      }
      if (!Array.isArray(viejos)) return { migrados: 0, corrupto: true, borrado: false };
      let migrados = 0;
      for (const viejo of viejos) {
        if (!viejo || typeof viejo !== "object") continue;
        const elApunte = this.apuntar(viejo);
        if (elApunte.guardado) migrados += 1;
      }
      // *Y solo se borra el origen si **están todos de verdad**.*
      const losIds = viejos.filter((v) => v && typeof v === "object" && v.id_local).map((v) => String(v.id_local));
      const estanTodos = losIds.every((id) => {
        try {
          return almacen.getItem(laClaveDe(id)) !== null;
        } catch (error) {
          return false;
        }
      });
      if (estanTodos) {
        try {
          almacenViejo.removeItem(claveVieja);
        } catch (error) {
          return { migrados, corrupto: false, borrado: false };
        }
        return { migrados, corrupto: false, borrado: true };
      }
      return { migrados, corrupto: false, borrado: false };
    },
  };
}

/**
 * ***La clave de un dato local, con el dueño que se capturó AL EMPEZAR*** (22/10/2026, D01).
 *
 * *La revisión independiente reprodujo esto: **A inicia el POST, entra B, y la respuesta 200 de A termina guardando
 * `cuedigital.ultimo.2:2` con datos de A** — y un 422 del vaciado de A acababa en `cuedigital.rechazados.2:2`.*
 *
 * ***El motivo***: *la clave se hacía con `laSesionDeAhora()` **cuando la respuesta llegaba**, no con el dueño del
 * origen. Entre el envío y la respuesta puede entrar otra cuenta, y entonces el dueño ya no es el mismo.*
 *
 * ***La regla***: *la clave sale de **un dueño que se pasa**, capturado antes del primer `await`. **Sin dueño no hay
 * clave** (`null`): es mejor no guardarlo que meterlo en un cubo compartido — la misma decisión que ya se tomó con el
 * borrador.*
 */
export function laClaveConDueno(claveBase, dueno) {
  if (!dueno) return null;
  return `${claveBase}.${dueno}`;
}

/**
 * ***¿Sigue siendo el mismo contexto?*** (22/10/2026, D01).
 *
 * *El encargo: «actualizar el estado visible **solo si sigue perteneciendo al contexto de origen**».*
 *
 * *Un 200 que llega tarde no puede pintar el «último apunte» de A en la pantalla de B, ni dar por bueno un rechazo de
 * otro. **Sin dueño de origen no se toca nada**: no se sabe de quién era.*
 */
export function esDelMismoContexto(duenoDelOrigen, sesionDeAhora) {
  if (!duenoDelOrigen) return false;
  return duenoDelOrigen === sesionDeAhora;
}

/**
 * ***La identidad de EJECUCIÓN, que no se copia al abrir una ventana*** (23/10/2026, D01).
 *
 * ***El defecto***: *`sessionStorage` **se copia al abrir una ventana con `opener`**. Comprobado en Chromium: **el padre y
 * la hija tienen el mismo `cuedigital.procesador`**, así que las dos piden el turno **como si fueran la misma** y las dos
 * lo reciben.*
 *
 * ***La regla***: **dos identidades, y separadas** —
 *
 *   · **de ejecución**: *la de **esta** carga de la aplicación. Vive **en memoria** y se genera al arrancar: **ninguna
 *     copia de almacenamiento la puede traer de otra ventana**;*
 *   · **persistente**: *la del dispositivo o la pestaña, para que **una recarga** se reconozca. **No sirve para
 *     distinguir dos ventanas** —y por eso no puede ser la única—.*
 *
 * *El turno se pide con **las dos**: la persistente dice «es la misma pestaña que antes»; la de ejecución, «es **esta**
 * ventana, y no la copia que abrí con `opener`».*
 */
let laDeEstaEjecucion = null;

/** *El id de **esta** carga. Único aunque otra ventana haya copiado el almacenamiento.* */
export function identidadDeEjecucion() {
  if (!laDeEstaEjecucion) laDeEstaEjecucion = unIdDeComando();
  return laDeEstaEjecucion;
}

/**
 * ***La identidad persistente***, para reconocer una **recarga** de la misma pestaña.
 *
 * *Sale del almacén que se le pase -`sessionStorage` en el navegador-, y **si no lo hay se genera y no se comparte**. Se
 * guarda **aparte** de la de ejecución a propósito: **si fueran la misma, la copia de `opener` la copiaría también**.*
 */
export function identidadPersistente(almacen, clave = "cuedigital.procesador") {
  try {
    const laGuardada = almacen && almacen.getItem ? almacen.getItem(clave) : null;
    if (laGuardada) return String(laGuardada);
    const laNueva = unIdDeComando();
    if (almacen && almacen.setItem) almacen.setItem(clave, laNueva);
    return laNueva;
  } catch (error) {
    return unIdDeComando();
  }
}

/**
 * ***El dueño del turno***: *la cuenta, la instalación, **la pestaña persistente** y **la ejecución**.*
 *
 * *Los dos últimos son los que separan dos ventanas que compartan la misma cuenta, la misma instalación **y el mismo
 * `sessionStorage`** —que es exactamente lo que pasa al abrir una con `opener`.*
 */
export function duenoDelTurno({ cuenta, instalacion, persistente, ejecucion }) {
  return `${cuenta || "sin-sesion"}:${instalacion || "sin-instalacion"}:${persistente || "sin-pestana"}:${
    ejecucion || "sin-ejecucion"
  }`;
}

/**
 * ***El turno para vaciar la cola: una pestaña a la vez*** (21/10/2026).
 *
 * *El encargo: «evitar dos procesadores concurrentes de la cola en eventos `online`, arranque y varias pestañas.
 * Bloqueo/lease con caducidad **y autoridad de idempotencia en el servidor, sin depender solo del bloqueo
 * local**».*
 *
 * *La segunda mitad ya estaba -cada apunte lleva su `clave_de_reenvio` y el servidor reconoce el reintento-, pero
 * **la primera no**: dos pestañas abiertas vaciaban a la vez, y aunque el servidor no duplicara, **se mandaban las
 * mismas peticiones dos veces** y el trabajo se repartía de forma impredecible.*
 *
 * ***Y el turno caduca***: *si una pestaña se cierra sin soltarlo -o el movil se apaga-, el turno **no se queda
 * bloqueado para siempre**; a los `duraMs` lo puede tomar otra. **Un cerrojo sin caducidad es una cola parada.***
 *
 * ***Si no se puede escribir el turno, se deja pasar***: *bloquear el envío porque el almacén no deja anotar quién
 * manda sería peor que mandar dos veces -y el servidor desduplica igualmente-.*
 */
export function pedirElTurno(
  almacen,
  { clave = "cuedigital.cola.turno", dueno, procesador, ahora = Date.now(), duraMs = 30000 } = {},
) {
  try {
    const bruto = almacen.getItem(clave);
    if (bruto) {
      const elTurno = JSON.parse(bruto);
      // ***El dueño compartido NO basta*** (22/10/2026, D01). *Lo reprodujo la revisión: **dos procesadores de la
      // misma cuenta e instalación recibían los dos `turno: true`**, porque el dueño era `cuenta:instalación` —el
      // mismo para dos pestañas— y el lease lo daba por reentrante.*
      //
      // *Se compara también el **procesador**, que es la identidad de la pestaña. Un turno sin procesador es de una
      // versión anterior y **no dice de qué pestaña es**: se trata como de otra y caduca solo.*
      const deOtroProcesador = elTurno.procesador !== procesador;
      const deOtroDueno = Boolean(elTurno.dueno) && elTurno.dueno !== dueno;
      if (Number(elTurno.caduca) > ahora && (deOtroDueno || deOtroProcesador)) {
        return {
          turno: false,
          dueno: elTurno.dueno,
          procesador: elTurno.procesador,
          caduca: Number(elTurno.caduca),
        };
      }
    }
    // *Se toma -o se renueva, si ya era nuestro-.*
    almacen.setItem(clave, JSON.stringify({ dueno, procesador, caduca: ahora + duraMs }));
    return { turno: true };
  } catch (error) {
    return { turno: true, sinAlmacen: true };
  }
}

/** ***Soltar el turno***, y **solo si es nuestro**: *no se le quita a otra pestaña lo que no es nuestro.* */
export function soltarElTurno(almacen, { clave = "cuedigital.cola.turno", dueno, procesador } = {}) {
  try {
    const bruto = almacen.getItem(clave);
    const elTurno = bruto ? JSON.parse(bruto) : null;
    // *Y solo el suyo: el mismo dueño **con otro procesador** es otra pestaña, y no se le quita.*
    if (elTurno && elTurno.dueno === dueno && elTurno.procesador === procesador) almacen.removeItem(clave);
  } catch (error) {
    // *Si no se puede soltar, **caduca solo**: no se queda bloqueada la cola.*
  }
}

export function loQueSePuedeMandar(cola, cuenta) {
  const suyos = [];
  const deOtraCuenta = [];
  const sinCuenta = [];
  for (const apunte of cola.leer()) {
    if (!apunte.cuenta) sinCuenta.push(apunte);
    else if (cuenta && apunte.cuenta === cuenta) suyos.push(apunte);
    else deOtraCuenta.push(apunte);
  }
  return { suyos, deOtraCuenta, sinCuenta };
}

// ---------------------------------------------------------------------------
// Repetir lo de la última vez
// ---------------------------------------------------------------------------

/**
 * Copia el último apunte cambiando solo la fecha.
 *
 * Es la función que más tiempo ahorra: el 80 % de los tratamientos son el mismo
 * producto, la misma dosis, la misma máquina y otra fecha. Dos toques y listo.
 */
export function repetirUltimo(apunte, fechaISO) {
  if (!apunte || !apunte.datos) return null;
  const copia = JSON.parse(JSON.stringify(apunte.datos));
  copia.fecha = fechaISO;
  return { tipo: apunte.tipo, datos: copia };
}

/**
 * El último tratamiento que hay apuntado en la finca, listo para repetirlo.
 *
 * POR QUÉ HACE FALTA. Hasta ahora «LO MISMO QUE LA ÚLTIMA VEZ» salía solo de lo que el móvil
 * recordaba (`localStorage`), y eso falla de tres maneras que el agricultor nota: estrena móvil,
 * entra desde el ordenador de casa, o el navegador le borra los datos por falta de espacio. En
 * los tres casos se encontraba con «todavía no has apuntado nada» **con el cuaderno lleno**, y
 * sin el atajo. Los apuntes no viven en el móvil: viven en el servidor, así que de ahí se sacan.
 *
 * Se devuelve con la misma forma que `cargaTratamiento()` en `app.js`, porque lo que se repite es
 * el borrador del asistente: si un nombre de campo cambia aquí y no allí, el asistente se abre
 * con campos vacíos y el agricultor apunta un tratamiento sin producto. Lo blinda una prueba.
 */
export function ultimoDeLaFinca(tratamientos) {
  const lista = (Array.isArray(tratamientos) ? tratamientos : []).filter(
    (apunte) => apunte && !apunte.anulado && apunte.fecha,
  );
  if (lista.length === 0) return null;
  // Se ordena por fecha, y no se da por hecho que vengan ordenados: esta función decide cuál es
  // «la última vez», y elegir mal significa repetir el tratamiento equivocado.
  const ultimo = lista.reduce((mejor, apunte) =>
    String(apunte.fecha) > String(mejor.fecha) ? apunte : mejor,
  );
  return { tipo: "tratamiento", datos: borradorDeTratamiento(ultimo) };
}

/**
 * Un tratamiento guardado, traducido al borrador del asistente.
 *
 * **Se usa para dos cosas, y por eso está separado**: para repetir el último tratamiento de la finca
 * (`ultimoDeLaFinca`) y para **corregir** uno ya apuntado (ronda 91, `corregirApunte` en `app.js`).
 * Las dos necesitan lo mismo —un tratamiento del servidor con los nombres de campo que leen los
 * pasos del asistente—, y tenerlo en dos sitios sería la forma más segura de que uno de los dos se
 * quedara viejo el día que se añada un dato.
 *
 * `deLaFinca` deja en `null` lo que no venga (`undefined`), porque el resumen del asistente escribiría
 * la palabra «undefined» delante del agricultor.
 */
export function borradorDeTratamiento(apunte) {
  if (!apunte) return null;
  const deLaFinca = (valor) => (valor === undefined ? null : valor);
  return {
    fecha: String(apunte.fecha),
    tipo: apunte.tipo || "parcela",
    parcela_id: deLaFinca(apunte.parcela_id),
    grupo_id: deLaFinca(apunte.grupo_id),
    instalacion_id: deLaFinca(apunte.instalacion_id),
    producto_cosechado: deLaFinca(apunte.producto_cosechado),
    lote_cosecha: deLaFinca(apunte.lote_cosecha),
    superficie_tratada_ha: deLaFinca(apunte.superficie_tratada_ha),
    justificacion: deLaFinca(apunte.justificacion),
    plaga: deLaFinca(apunte.plaga),
    producto_id: deLaFinca(apunte.producto_id),
    dosis: deLaFinca(apunte.dosis),
    unidad_dosis: apunte.unidad_dosis || "L/ha",
    aplicador_id: deLaFinca(apunte.aplicador_id),
    equipo_id: deLaFinca(apunte.equipo_id),
    medidas: Array.isArray(apunte.medidas) ? apunte.medidas : [],
    observaciones: deLaFinca(apunte.observaciones),
    hora_inicio: deLaFinca(apunte.hora_inicio),
    hora_fin: deLaFinca(apunte.hora_fin),
    estado_cultivo: deLaFinca(apunte.estado_cultivo),
    temperatura_c: deLaFinca(apunte.temperatura_c),
    humedad_pct: deLaFinca(apunte.humedad_pct),
    viento_kmh: deLaFinca(apunte.viento_kmh),
    viento_direccion: deLaFinca(apunte.viento_direccion),
    volumen_caldo_l_ha: deLaFinca(apunte.volumen_caldo_l_ha),
    operadores_expuestos: deLaFinca(apunte.operadores_expuestos),
    incidencias: deLaFinca(apunte.incidencias),
    franja_seguridad_respetada: deLaFinca(apunte.franja_seguridad_respetada),
    aplicado_a_mano: deLaFinca(apunte.aplicado_a_mano),
    eficacia: deLaFinca(apunte.eficacia),
    unidad_cantidad_aplicada: deLaFinca(apunte.unidad_cantidad_aplicada),
    plazo_reentrada_dias: deLaFinca(apunte.plazo_reentrada_dias),
    // Estos no los pregunta ninguna pantalla del asistente, y están aquí para que **corregir un
    // apunte no los borre**: el asistente los devuelve tal cual venían (ver `cargaTratamiento`).
    // Repetir un tratamiento también los copia, que es lo que se espera de «lo mismo que la última
    // vez»: el mismo asesoramiento y la misma variedad.
    cultivo: deLaFinca(apunte.cultivo),
    variedad: deLaFinca(apunte.variedad),
    lote_producto: deLaFinca(apunte.lote_producto),
    asesor_id: deLaFinca(apunte.asesor_id),
    asesor_fecha: deLaFinca(apunte.asesor_fecha),
    asesoramiento_validado: deLaFinca(apunte.asesoramiento_validado),
    asesoramiento_contrato: deLaFinca(apunte.asesoramiento_contrato),
  };
}

/**
 * Qué se puede repetir: lo que recuerda este aparato o, si no hay nada mejor, el último
 * tratamiento de la finca.
 *
 * Se comparan las fechas y gana la más nueva, porque «lo mismo que la última vez» quiere decir la
 * última de verdad. Si el agricultor apuntó ayer desde el ordenador y hace un mes desde el móvil,
 * lo correcto es ofrecerle lo de ayer.
 */
export function queSePuedeRepetir(deAqui, deLaFinca) {
  if (!deAqui || !deAqui.datos) return deLaFinca || null;
  if (!deLaFinca || !deLaFinca.datos) return deAqui;
  const fechaDeAqui = String(deAqui.datos.fecha || "");
  const fechaDeLaFinca = String(deLaFinca.datos.fecha || "");
  return fechaDeLaFinca > fechaDeAqui ? deLaFinca : deAqui;
}

// ---------------------------------------------------------------------------
// Comprobaciones que se pueden hacer sin preguntar al servidor
// ---------------------------------------------------------------------------

/** Campos que no pueden quedar vacíos, con el mensaje que corresponde a cada uno. */
const OBLIGATORIOS = {
  parcela_id: "V18_sin_parcela",
  justificacion: "V10_sin_justificacion",
  producto_id: "V1_sin_registro",
  kg_ha_producto: "F1_sin_cantidad",
  fertilizante_id: "F1_sin_cantidad",
};

function estaVacio(valor) {
  if (valor === null || valor === undefined) return true;
  if (typeof valor === "string") return valor.trim() === "";
  if (Array.isArray(valor)) return valor.length === 0;
  return false;
}

/**
 * Comprueba un campo antes de mandarlo. Devuelve el código del mensaje o null.
 *
 * Se comprueba en el móvil y no en el servidor para que el aviso salga al instante,
 * sin esperar a que responda. Con mala cobertura, esa espera es la diferencia entre
 * corregirlo y abandonar.
 */
export function validaPaso(campo, valor) {
  if (!(campo in OBLIGATORIOS)) return null;
  return estaVacio(valor) ? OBLIGATORIOS[campo] : null;
}

/** La superficie usada no puede pasar de la de la parcela. */
export function validaSuperficie(usada, disponible, esAbono = false) {
  if (estaVacio(usada) || estaVacio(disponible)) return null;
  const numeroUsada = aNumero(usada);
  const numeroDisponible = aNumero(disponible);
  if (numeroUsada === null || numeroDisponible === null) return null;
  // La misma tolerancia que en el servidor: 0,0001 ha es 1 m², y el SIGPAC da
  // cuatro decimales. Sin ella se bloquearía un apunte correcto por un redondeo.
  if (numeroUsada > numeroDisponible + 0.0001) {
    return esAbono ? "F2_superficie_excedida" : "V4_superficie_excedida";
  }
  return null;
}

/** Cuántos días de espera quedan. 0 o menos significa que ya se puede coger. */
export function diasDeEspera(fechaAplicacion, diasPlazo, hoyISO) {
  if (estaVacio(fechaAplicacion) || estaVacio(diasPlazo)) return null;
  const plazo = aNumero(diasPlazo);
  if (plazo === null) return null;
  return diasHasta(sumaDias(fechaAplicacion, plazo), hoyISO);
}

/**
 * Rellena una plantilla de texto con sus datos: "{cuantos} cosas" -> "3 cosas".
 *
 * Los mensajes están escritos en el servidor, en `textos.py`, para que el test que
 * garantiza que no hay jerga los cubra. Aquí solo se rellenan; la interfaz nunca
 * compone frases por su cuenta, que es como acaban apareciendo tecnicismos.
 *
 * Si falta un dato, se deja el hueco tal cual en vez de escribir "undefined": en
 * pantalla eso se ve y se corrige, mientras que un "undefined" asusta y no dice nada.
 */
export function rellena(plantilla, datos = {}) {
  if (!plantilla) return "";
  return String(plantilla).replace(/\{(\w+)\}/g, (hueco, clave) => {
    const valor = datos[clave];
    return valor === undefined || valor === null ? hueco : String(valor);
  });
}

/**
 * El texto de una cuenta, en singular o en plural (rediseño de la ronda 84).
 *
 * **Por qué existe.** Hay textos que llevan el número delante —«{cuantos} cosas apuntadas esperando a que
 * haya cobertura»— y con uno se leían fatal: «1 cosas apuntadas». El servidor manda el singular y el plural
 * (`_uno` y `_varios`, o el nombre de siempre para el plural) y aquí se elige, que es lo mismo que hace
 * `con_cuenta` en `textos.py` para los textos que compone el servidor.
 *
 * **Y también vale `_una`** (30/09/2026): cuando el sustantivo es femenino («1 venta apuntada», «1 tierra»),
 * el singular de `textos.py` está escrito con `_una` —que es como se lee— y esta función solo miraba `_uno`,
 * así que con una sola venta la frase salía en plural («1 ventas apuntadas»). Pasó dos veces: la primera con
 * los pies de las tablas (se arreglaron las claves) y la segunda al escribir el panel de mando. En vez de
 * volver a renombrar claves, aquí se prueban **las dos formas**: el que escribe el texto la pone como se lee.
 *
 * Si falta el singular se usa el plural de siempre: es lo que hacía antes, así que en pantalla nunca se
 * queda un hueco. Lo que impide que eso pase es la prueba `TestSingularYPlural`, que exige los dos.
 */
export function conCuenta(textos, base, cuantos) {
  const diccionario = textos || {};
  const singular = cuantos === 1 ? diccionario[`${base}_uno`] || diccionario[`${base}_una`] : "";
  const clave = cuantos === 1 ? `${base}_uno` : `${base}_varios`;
  const plantilla = singular || diccionario[clave] || diccionario[base] || "";
  // Los textos usan `{cuantos}` o `{cuantas}` según cómo esté escrita la frase.
  return rellena(plantilla, { cuantos, cuantas: cuantos });
}

/** Saca el primer aviso que impide guardar de una respuesta del servidor.
 *
 * El servidor contesta 422 con `{detail: {avisos: [...]}}` y los mensajes ya escritos.
 * La interfaz no compone frases: solo enseña la que le dan.
 */
export function primerAvisoBloqueante(respuesta) {
  const detalle = respuesta && respuesta.detail ? respuesta.detail : respuesta;
  if (!detalle || !Array.isArray(detalle.avisos)) return null;
  const bloqueante = detalle.avisos.find((aviso) => aviso.bloquea !== false);
  return bloqueante ? bloqueante.mensaje : null;
}

/**
 * Suma lo que se sabe **y cuenta lo que no**, en vez de convertir el hueco en un cero.
 *
 * POR QUÉ EXISTE (A14 de `docs/T02_VALORES_POR_DEFECTO.md`, 05/10/2026)
 * ====================================================================
 * Media aplicación sumaba así: `suma + (Number(lo_que_sea) || 0)`. Y eso hace dos cosas malas a la vez:
 * el hueco (`null`, que en este programa quiere decir **«no lo sé»**) **suma cero**, y una cifra que no
 * se puede leer (`"por ahí"` → `NaN`) también. El resultado es un total que **parece completo** cuando le
 * falta un dato: 60 tierras de las que 3 no traen su superficie dan una cifra que el agricultor lee como
 * la de su finca entera.
 *
 * Devuelve `{suma, sin_decir}`: la suma de lo que sí consta y **cuántos elementos no lo traen**, que es
 * lo que hace falta para poder decirlo en la pantalla («Sin hectáreas dichas: 3»). No devuelve solo la
 * suma a propósito: quien la use **tiene que poder decir lo que falta**, y para eso hay que contarlo.
 *
 * Qué cuenta como «no se sabe»: `null` (el hueco del programa), `undefined` (el campo que no vino) y la
 * cadena vacía (el campo en blanco). Todo lo demás se convierte a número, y si no es un número —`NaN`—
 * también cuenta como no sabido: **no se inventa un cero**.
 */
export function sumandoLoQueSeSabe(lista, deDonde = (uno) => uno) {
  return (lista || []).reduce(
    (cuenta, uno) => {
      const crudo = deDonde(uno);
      if (crudo === null || crudo === undefined || crudo === "") {
        cuenta.sin_decir += 1;
      } else {
        const valor = Number(crudo);
        if (Number.isFinite(valor)) cuenta.suma += valor;
        else cuenta.sin_decir += 1;
      }
      return cuenta;
    },
    { suma: 0, sin_decir: 0 },
  );
}

/**
 * El motivo que da el servidor cuando dice que no, **sea de las dos formas que usa este programa**.
 *
 * POR QUÉ HACÍA FALTA
 *
 * El servidor contesta de dos maneras, y las dos son frases que lee el agricultor:
 *
 *  · `{detail: {avisos: [{mensaje, bloquea}]}}` — las validaciones, con el aviso que bloquea primero.
 *  · `{detail: "…"}` — una frase suelta, que es como contestan las puertas que solo tienen un motivo:
 *    «Solo el titular de la finca puede decidir quién más entra», «Esa finca no es tuya o ya no tienes
 *    acceso a ella».
 *
 * La segunda **se perdía**: `primerAvisoBloqueante` solo entiende la primera, así que un 403 con su frase
 * acababa en «No se ha podido mandar», que no dice qué pasa ni qué hacer. Se vio al escribir la pantalla
 * de las fincas (ronda 89), donde todos los motivos son frases sueltas, y es justo lo contrario de la
 * regla del proyecto: **la interfaz no compone frases, pero tampoco puede tirar la que le dan**.
 */
export function avisoDelServidor(respuesta) {
  const bloqueante = primerAvisoBloqueante(respuesta);
  if (bloqueante) return bloqueante;
  const detalle = respuesta && respuesta.detail;
  // Un `detail` de la validación de FastAPI es una **lista** de fallos de formato («field required»), y eso
  // no es una frase para el agricultor: ahí se sigue usando el aviso general.
  if (typeof detalle === "string" && detalle.trim()) return detalle;
  return null;
}

/**
 * Un texto para poder compararlo: sin tildes, sin mayúsculas y sin espacios de más.
 *
 * **Por qué existe.** Buscar «prado» tiene que encontrar «El Prado», y buscar «penaranda» tiene que
 * encontrar «Peñaranda»: quien escribe con una mano y con guantes en el campo no pone tildes, y el
 * programa no puede castigarle por eso. Se hace con `normalize("NFD")`, que separa la tilde de la letra,
 * y quitando después esas tildes sueltas.
 */
export function sinTildes(texto) {
  return String(texto === undefined || texto === null ? "" : texto)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * **A qué lleva cada grupo** (07/10/2026, encargo: «convertir los resultados en accesos»).
 *
 * Un resultado que no lleva a ninguna parte no es un resultado: es un cartel. Esto es la decisión de **qué
 * abre cada cosa**, y va aquí —y no en la pantalla— porque así se prueba sin navegador:
 *
 *  · `tierras` → **la ficha de esa tierra**, con su historia (es la pantalla que el agricultor lee).
 *  · `gastos` → la ficha de ese gasto, con sus repartos y sus pagos.
 *  · `personas` → la ficha de esa persona o empresa.
 *  · `maquinas` → la ficha de esa máquina.
 *  · `papeles` → **su lista**, y no el fichero: abrir el fichero es **descargarlo**, y una descarga no se
 *    dispara sola al mirar unos resultados. Quien quiera el papel, lo abre desde su lista, que es donde
 *    están los botones de descargar.
 */
const ACCION_DE_CADA_GRUPO = {
  tierras: "tierra-historia",
  gastos: "gasto-abrir",
  personas: "contacto-abrir",
  maquinas: "maquina-ver",
  papeles: "papel-ver-todos",
};

/**
 * Lo que la pantalla de la búsqueda global tiene que enseñar, ya traducido.
 *
 * **Por qué está esto aquí y no en `app.js`.** Por el mismo motivo que el buscador de tierras: es la parte
 * con decisiones —cómo se llama cada grupo, qué se dice cuando no se ha buscado nada, qué se dice cuando
 * se ha cortado un grupo— y aquí se puede probar **sin navegador**. La pantalla que venga después solo
 * tiene que pintar lo que esto devuelve.
 *
 * Tres decisiones que van dentro, y ninguna es un adorno:
 *
 *  1. **Los grupos que el servidor no ha mandado no se pintan**, y si no ha mandado ninguno se dice que no
 *     hay nada. Un grupo vacío con su título haría creer que esa búsqueda se ha mirado y no hay nada de
 *     ese tipo, cuando puede que ni se haya mirado.
 *  2. **`cortado` se dice**: un grupo de diez resultados que en realidad son cuarenta, sin avisar, hace
 *     creer que solo hay diez.
 *  3. **«No se ha buscado» no es «no hay nada»**: son dos cosas distintas y se dicen distinto. Con menos de
 *     dos letras el servidor no busca (`buscado: false`) y eso no es un fracaso de la búsqueda.
 *
 * El nombre de cada grupo sale de los textos del servidor (`textos.buscar`), no de aquí: si un grupo nuevo
 * llega sin su nombre, se enseña su clave tal cual antes que dejar el hueco en blanco.
 */
export function losGruposDeLaBusqueda(respuesta, textos = {}) {
  const suyo = respuesta && typeof respuesta === "object" ? respuesta : {};
  const t = textos || {};
  const nombre = (clave) => t[`grupo_${clave}`] || clave;
  const grupos = (suyo.grupos || []).map((grupo) => ({
    clave: grupo.clave,
    titulo: nombre(grupo.clave),
    cuantos: grupo.cuantos,
    cortado: Boolean(grupo.cortado),
    aviso_cortado: grupo.cortado ? t.cortado || "" : "",
    lineas: (grupo.resultados || []).map((resultado) => ({
      etiqueta: resultado.etiqueta || "",
      // El detalle (el importe, la matrícula, el teléfono) puede no constar: entonces no se enseña nada,
      // ni un guion ni un cero.
      detalle: resultado.detalle || "",
      // **Y a dónde lleva**: su acción y su identificador, para que la pantalla solo tenga que pintarlos.
      accion: ACCION_DE_CADA_GRUPO[grupo.clave] || "",
      id: resultado.id,
    })),
  }));
  return {
    texto: suyo.texto || "",
    // **Tres estados, y son distintos**: no se ha buscado, se ha buscado y no hay nada, y hay resultados.
    se_busco: Boolean(suyo.buscado),
    grupos,
    mensaje: !suyo.buscado ? t.sin_buscar || "" : grupos.length ? "" : t.sin_resultados || "",
  };
}

/**
 * Las tierras que casan con lo que el agricultor ha escrito en el buscador.
 *
 * **Por qué está esto aquí y no en `app.js`.** Es la única forma de poder probarlo sin navegador: con
 * cincuenta y una tierras, el buscador es lo que evita recorrerlas todas, y una búsqueda que no
 * encontrara lo que hay que encontrar sería peor que no tener buscador. Aquí se prueba con datos
 * inventados, una por una.
 *
 * Mira tres cosas, que son las tres por las que el agricultor llama a una tierra: **su nombre, su pueblo
 * y el número del SIGPAC**. Las dos primeras, por lo que se escribe dentro (un trozo de «El Prado de
 * arriba» encuentra «prado»); la tercera, además, **por trozos de números en su orden**, porque en el
 * visor del SIGPAC la referencia se copia con guiones («37-70-0-0-503-51-1») y quien la escribe de
 * memoria teclea «37 70 503».
 *
 * Sin nada escrito devuelve la lista entera: un buscador vacío no esconde nada.
 */
export function tierrasQueCasen(parcelas, buscado) {
  const buscadas = sinTildes(buscado);
  if (!buscadas) return parcelas;
  return parcelas.filter((parcela) => {
    const texto = sinTildes([parcela.alias, parcela.municipio, parcela.ref_sigpac].join(" "));
    if (texto.includes(buscadas)) return true;
    return casaLaReferencia(parcela.ref_sigpac, buscadas);
  });
}

/**
 * ¿Los números que ha escrito son los de esta referencia del SIGPAC, y en su orden?
 *
 * Se comparan **trozos de dos cifras o más**: los ceros sueltos de la referencia («37-70-0-0-503-51-1»)
 * están en todas y no distinguen nada, así que escribirlos o no escribirlos tiene que dar igual. Un trozo
 * casa si aparece **dentro** de un trozo de la referencia y **después** del anterior: así «37 70 503»
 * encuentra la referencia de arriba aunque el agricultor se haya saltado los ceros de en medio.
 *
 * Sin ningún trozo de dos cifras devuelve `false` a propósito: buscar «5» no puede dar por buena
 * cualquiera de las cincuenta y una tierras. (Si acierta por el nombre o el pueblo, ya lo habrá visto
 * antes, en la comparación de texto.)
 */
function casaLaReferencia(referencia, buscadas) {
  if (!referencia) return false;
  const suyos = String(referencia)
    .split(/[^0-9]+/)
    .filter(Boolean);
  const trozos = buscadas.split(/[^0-9]+/).filter((trozo) => trozo.length >= 2);
  if (!trozos.length) return false;
  let desde = 0;
  for (const trozo of trozos) {
    const donde = suyos.findIndex((suyo, indice) => indice >= desde && suyo.includes(trozo));
    if (donde === -1) return false;
    desde = donde + 1;
  }
  return true;
}

/** Presentación de una métrica; conserva la magnitud de cálculo y no suma hectáreas distintas. */
export function presentarMetrica(metrica, textos = {}) {
  const unidad = textos.unidades?.[metrica.unidad] || textos.unidad_sin_indicar || "";
  const numero = formateaNumero(metrica.valor);
  const valor = numero || textos.no_se_sabe || "";
  return { ...metrica, texto_valor: `${valor} · ${unidad}`.trim() };
}

/**
 * ***Vaciar la cola de una cuenta, con los efectos por fuera*** (22/10/2026, D01).
 *
 * *El vaciado vivía dentro de `app.js`, soldado a `api`, al almacén y al aviso de la pantalla: **no se podía probar** el
 * éxito, el rechazo ni el almacenamiento fallido sin arrancar la aplicación entera. Y es donde estaban los dos
 * defectos que reprodujo la revisión independiente.*
 *
 * ***Aquí solo está la decisión***; *mandar, guardar y mirar la sesión se pasan desde fuera. **La interfaz obedece**, que
 * es la regla que ya sigue `decideQueHacer`.*
 *
 * ***Lo que NO cambia***: *el orden de los casos y sus consecuencias, tal como estaban —*
 *
 *   · **200** → *se quita de la cola;*
 *   · **401/403** → *paran el vaciado y **no** son rechazo: el permiso puede volver;*
 *   · **otro 4xx** → *se aparta como rechazo **con su identidad completa**, y **no se quita de la cola hasta
 *     comprobar leyendo que quedó guardado** — `guardar` se calla cuando el almacén falla, y antes eso dejaba el apunte
 *     **sin pendiente y sin rechazo**;*
 *   · **5xx o red caída** → *se para y se reintenta luego;*
 *   · **y si la sesión cambia a mitad**, *se para en el acto: los siguientes irían con otro dueño.*
 *
 * ***`claveRechazados` llega hecha***: *la captura quien llama **antes del primer `await`**, que es lo que impide que
 * un 422 de A acabe en la libreta de B.*
 */
export async function vaciarLaCola({
  suyos,
  cola,
  claveRechazados,
  api,
  leer,
  guardar,
  sesionDeAhora,
  sesionDelOrigen,
  motivoDelRechazo,
}) {
  const rechazados = leer(claveRechazados, []);
  let mandados = 0;
  let apartados = 0;
  let paradoPor = null;

  for (const apunte of suyos) {
    if (sesionDeAhora() !== sesionDelOrigen) {
      paradoPor = "cambio-de-cuenta";
      break;
    }
    let respuesta;
    try {
      respuesta = await api(apunte);
    } catch (error) {
      paradoPor = "sin-red";
      break;
    }
    if (respuesta.ok) {
      cola.quitar(apunte.id_local);
      mandados += 1;
      continue;
    }
    if (respuesta.status >= 400 && respuesta.status < 500) {
      // *401 y 403 NO son rechazos definitivos: el permiso puede volver.*
      if (respuesta.status === 401 || respuesta.status === 403) {
        paradoPor = "sin-permiso";
        break;
      }
      const cuerpo = await respuesta.json().catch(() => null);
      rechazados.push({
        id_local: apunte.id_local,
        cuenta: apunte.cuenta || null,
        tipo: apunte.tipo || null,
        ruta: apunte.ruta,
        datos: apunte.datos,
        motivo: motivoDelRechazo(cuerpo),
        estado: respuesta.status,
        cuando: apunte.apuntado_en,
      });
      // ***No se quita hasta comprobarlo leyendo***: *es lo único que dice si se guardó.*
      guardar(claveRechazados, rechazados);
      const losGuardados = leer(claveRechazados, []);
      if (!losGuardados.some((uno) => uno && uno.id_local === apunte.id_local)) {
        paradoPor = "no-se-pudo-apartar";
        break;
      }
      cola.quitar(apunte.id_local);
      apartados += 1;
      continue;
    }
    paradoPor = "servidor";
    break;
  }

  return { mandados, apartados, paradoPor };
}
