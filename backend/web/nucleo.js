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
    getItem: (clave) => (clave in datos ? datos[clave] : null),
    setItem: (clave, valor) => {
      datos[clave] = String(valor);
    },
    removeItem: (clave) => {
      delete datos[clave];
    },
  };
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

    /** Apunta algo para mandarlo. Devuelve el apunte con su identificador local. */
    apuntar(apunte) {
      const lista = leer();
      contador.n += 1;
      const conId = {
        ...apunte,
        id_local: apunte.id_local || `p${contador.n}-${reloj()}`,
        apuntado_en: apunte.apuntado_en || reloj(),
      };
      lista.push(conId);
      escribir(lista);
      return conId;
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
